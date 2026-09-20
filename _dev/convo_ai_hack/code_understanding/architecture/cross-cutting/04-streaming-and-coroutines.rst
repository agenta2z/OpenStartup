.. _streaming:

============================
Streaming & Coroutines
============================

Streaming is fundamental to the platform — most chat endpoints stream LLM responses chunk-by-chunk over SSE/ndjson. This page documents the patterns and pitfalls.

Why streaming?
===============

- LLMs generate tokens one at a time; total latency for a 500-token response can be 5-30 seconds
- A user sees the first chunk in 200ms-1s — the rest streams as it's generated
- Without streaming, the whole response must finish before the user sees anything (terrible UX)

The wire format: ndjson over HTTP
==================================

Verified at ``ChatV1Controller.kt:164``:

.. code-block:: kotlin

   @PostMapping(
       "/v1/channel/{conversationId}/message/stream",
       produces = ["application/x-ndjson"]
   )

Each chunk is one JSON object on its own line. The HTTP connection stays open until the LLM finishes generating.

Why ndjson and not SSE? Both work; ndjson is slightly easier to parse (no ``data:`` prefix, no event-name framing) and works better with some HTTP clients.

The Kotlin types involved
==========================

- **``Flow<ChatCompletionStreamResponse>``** — the type returned by ``AIGatewayClientServiceImpl.streamOpenaiClient(...)``. This is a Kotlin coroutines cold flow.
- **``Flux<Any>``** — what the controller returns (Spring WebFlux's reactive streams type).

The controller converts ``Flow → Flux`` (via ``flow.asFlux()`` or kotlinx-coroutines-reactor's interop).

The MDC + coroutine pitfall :sup:`(critical)`
==============================================

AGENTS.md lines 35-36 warn about the **#1 source of subtle bugs** in this codebase:

  *Standard SLF4J MDC is thread-local. Kotlin coroutines suspend across threads. After the first suspend point, MDC is empty unless you snapshot+restore it.*

**Wrong** (loses MDC after first suspend):

.. code-block:: kotlin

   suspend fun streamMessages(): Flow<Message> {
       log.info("Starting stream")  // has MDC
       val result = downstreamCall()  // suspends, drops MDC
       log.info("Result: ${result}")  // ❌ NO MDC — debugging nightmare
       return result.asFlow()
   }

**Right** (using ``withMdcContext { }``):

.. code-block:: kotlin

   suspend fun streamMessages(): Flow<Message> = withMdcContext {
       log.info("Starting stream")
       val result = downstreamCall()  // MDC preserved across suspension
       log.info("Result: ${result}")  // ✅ MDC restored
       result.asFlow()
   }

Verified usage at ``ChatV1Controller.kt:173``: the streaming endpoint wraps its ENTIRE body in ``withMdcContext { }``.

The GraphQL + suspend pitfall :sup:`(critical)`
================================================

AGENTS.md lines 31-33 document the GraphQL equivalent:

  *Suspend ``@QueryMapping``, ``@MutationMapping``, etc., must wrap their bodies in ``withRequestAttributesContext { }`` before any suspension.*

Spring's ``RequestContextHolder`` is also thread-local. Without the wrapper, the first ``downstreamCall()`` suspension causes ``RequestContextHolder.currentRequestAttributes()`` to throw ``IllegalStateException`` afterward.

Forbidden: raw ``Dispatchers.IO`` :sup:`(verified per AGENTS.md)`
==================================================================

AGENTS.md line 39: "Raw ``Dispatchers.IO`` and ``Dispatchers.Default`` are forbidden in business code."

Why? They produce coroutine contexts that LACK:
- The current MDC keys
- The current OTel trace context
- The current request attributes (TenantContext, User)

Correct alternative: inject ``CoroutineContextProvider`` (in ``foundation/utilities/threading/``) and use the providers it returns. They wrap ``Dispatchers.IO`` with the necessary context plumbing.

Backpressure
=============

Reactor ``Flux`` and Kotlin ``Flow`` both support backpressure. For LLM streaming:

- The HTTP client requests chunks at its own pace (e.g. browser SSE consumer)
- The ``Flux`` propagates "I want N more items" upstream
- The ``Flow`` (via reactor interop) respects this and doesn't fetch more from AI Gateway than needed

In practice, LLMs generate faster than slow clients consume. Backpressure prevents memory blowup when a slow client connects to a fast model.

What you would change here
===========================

- **Add a new streaming endpoint** → return ``Flux<Any>``; produce ndjson
- **Add a non-streaming endpoint** → return ``Mono<T>`` or just ``T`` (suspend fun)
- **Cross suspension boundaries** → ALWAYS wrap with ``withMdcContext { }`` (or ``withRequestAttributesContext { }`` for GraphQL)
- **Need IO-bound work** → inject ``CoroutineContextProvider``, never use ``Dispatchers.IO`` directly

What you would NOT change here
===============================

- The MDC restoration mechanism (foundation responsibility)
- The OTel context propagation (Application.kt + ContextPropagationInitializer)

