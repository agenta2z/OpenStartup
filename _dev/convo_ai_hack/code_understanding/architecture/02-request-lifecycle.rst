.. _request-lifecycle:

============================
Request Lifecycle
============================

This page traces a single ``POST /chat/v1/channel/{conversationId}/message/stream``
request from ingress to LLM streaming response, with every step backed by
file:line citations.

Why pick this endpoint? It exercises **eight architectural concerns at once**:
authentication, tenant isolation, telemetry, feature flags, agent identity
preloading, AI Gateway streaming, MDC context propagation across coroutines, and
SSE wire-format encoding.

The path
========

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │ HTTP Client                                             │
   │ POST /chat/v1/channel/{uuid}/message/stream             │
   │ Headers: X-Slauth-Issuer, X-Tenant-Context, X-Cloud-Id  │
   │ Body: { agent_id, message_text, ... }                   │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Spring WebFlux entry: ChatV1Controller                  │
   │ modules/service/convo-ai-service/src/main/kotlin/       │
   │ io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt │
   │   line 164: @PostMapping(.../message/stream)            │
   │   line 167: suspend fun conversationChannelMessage...   │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ HeaderFilter / ExperienceRateLimitFilter (request scope)│
   │ modules/foundation/utilities/utilities-impl/src/main/   │
   │ kotlin/.../interceptors/HeaderFilter.kt                 │
   │ modules/foundation/.../ExperienceRateLimitFilter.kt     │
   │ Resolves: TenantContext, User, Experience               │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ withMdcContext { ... }     (line 173)                   │
   │ Wraps the whole flow so MDC keys (requestId, cloudId,   │
   │ agentId) survive coroutine suspensions                  │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Experience gating       (line 175-179)                  │
   │ Hardcoded allowlist: ISSUE_WORK_BREAKDOWN, UNIFIED_HELP │
   │ Any other experience -> GoneException (HTTP 410)        │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Agent deactivation check  (line 181-188)                │
   │ agentService.isDeactivated(tenantContext, user, agentId)│
   │ Throws AgentDeactivatedException if deactivated         │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Preload Rovo agent if needed   (line 190)               │
   │ preloadRovoAgentIfNeeded(body, tenantContext, user)     │
   │ Resolves agent metadata / permissions before streaming  │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Build streamLoggingContext   (line 192-201)             │
   │ Captures: conversationId, cloudId, experienceId,        │
   │           channelId, requestId, agentId, creatorType    │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ assistanceClient.conversationChannelMessageCreate       │
   │   StreamWithPassThroughHeaders(...)   (line 219)        │
   │ Hands off to platform/service tier; pass-through        │
   │ headers retain X-Slauth-Issuer for downstream calls     │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ AIGatewayClientServiceImpl.streamOpenaiClient(...)      │
   │ modules/platform/service/service-impl/src/main/kotlin/  │
   │ io/atlassian/micros/convoai/platform/service/llm/       │
   │ AIGatewayClientServiceImpl.kt (3,087 lines)             │
   │   - Adds attribution headers (USE_CASE_ID, CLOUD_ID,    │
   │     USER_ID, USER_CONTEXT)                              │
   │   - Selects provider (OpenAI/Anthropic/Bedrock/Google)  │
   │   - Returns Flow<ChatCompletionStreamResponse>          │
   │     wrapped with .withMetrics() extension               │
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Flow chunks wrapped as Flux<Any> for WebFlux            │
   │ Spring serializes each chunk as ndjson line             │
   │ Content-Type: application/x-ndjson                      │
   │   (declared at line 164 produces=["application/x-ndjson"])
   └────────────────────────┬────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │ HTTP Client (browser / SDK / Slack bot)                 │
   │ Receives streaming JSON chunks line-by-line             │
   └─────────────────────────────────────────────────────────┘

Critical implementation details
================================

The ``@CustomerAccountAllowed`` annotation
-------------------------------------------

At ``ChatV1Controller.kt:165``. This is a custom Spring annotation that **bypasses
the default service-account-only check**, allowing requests from real customer
ASAP issuers (not just internal services). Without it, all customer-originated
streaming would 403.

The ``@RequestAttribute(TENANT_CONTEXT)`` injection
----------------------------------------------------

At ``ChatV1Controller.kt:170``. ``TenantContext`` is NOT extracted from the
request headers in the controller — by the time the controller runs, ``HeaderFilter``
(at ``modules/foundation/utilities/utilities-impl/src/main/kotlin/io/atlassian/
micros/convoai/foundation/utilities/interceptors/HeaderFilter.kt``) has already
parsed the ``X-Tenant-Context`` header and stored the resolved object in the
request attributes.

This is a **performance-critical optimization**: the same ``TenantContext`` may
be referenced 8-12 times per request (across feature gate evaluations, audit
log entries, downstream service calls). Parsing once in the filter and
injecting via attribute keeps it cheap.

The ``withMdcContext { }`` wrapper
-----------------------------------

At ``ChatV1Controller.kt:173``. This is **not** a no-op — it's the bridge
between Spring's thread-local MDC (``Mapped Diagnostic Context``, used by
SLF4J for structured logging) and Kotlin coroutines (which can suspend on any
thread).

Without this wrapper, every log line emitted after the first ``suspend`` point
loses its MDC keys (cloudId, requestId, agentId), making logs impossible to
trace. AGENTS.md lines 35-36 explicitly call this out as a coroutine pattern
gotcha.

The Experience allowlist at line 175-179
-----------------------------------------

This streaming endpoint is **NOT a generic chat streamer**. It only allows
``ISSUE_WORK_BREAKDOWN`` and ``UNIFIED_HELP`` experiences — anything else
returns HTTP 410 Gone. Other use cases stream via different controllers (e.g.
``WhiteboardAITeammateStreamingNativeController`` for whiteboard generation,
``RovoChatController`` for general Rovo chat).

This narrowness is **intentional**: each streaming controller has its own
contract with the LLM (different prompt templates, different tool sets,
different output post-processors), so they don't share an endpoint.

The pass-through-headers pattern
---------------------------------

At ``ChatV1Controller.kt:219``:
``assistanceClient.conversationChannelMessageCreateStreamWithPassThroughHeaders(...)``

Why pass headers through? Because **downstream services** (AI Gateway, TCS,
Statsig, identity service) re-validate the SLAuth ASAP token. The original
``X-Slauth-Issuer`` header must propagate end-to-end, NOT be stripped at
each hop.

The ``RovoAgentForAssistanceService`` body injection
-----------------------------------------------------

At ``ChatV1Controller.kt:215-217``. If a Rovo agent was preloaded, the
controller mutates the request body to inject pre-resolved agent details
under ``AGENT_DETAILS_BODY_KEY``. This avoids the assistance client having to
re-resolve the agent (which would be a separate Statsig call + DB lookup).

This is a deliberate **N+1 prevention pattern** at the controller boundary.

Concurrency / threading model
==============================

The endpoint is a Kotlin ``suspend fun`` returning ``Flux<Any>``. Spring WebFlux
handles this via the Reactor + Kotlin Coroutines integration:

1. Initial request → Reactor allocates a worker thread.
2. ``suspend fun`` execution → coroutine context binds to the Reactor thread.
3. ``withMdcContext { }`` snapshots MDC.
4. ``assistanceClient.<...>()`` returns a ``Flow<*>`` → converted to ``Flux``.
5. As LLM chunks arrive, each is emitted as a Reactor signal.
6. Spring's ndjson encoder writes each emission to the HTTP response body.

If the LLM streams for 30 seconds and emits 200 chunks, the worker thread is
**not blocked for 30 seconds** — Reactor's non-blocking IO releases the thread
between chunks, allowing other requests to multiplex.

Other controllers
==================

For completeness, the chat controller exposes 13 other endpoints (verified via
``grep -n "@(Get|Post|Put|Delete)Mapping" ChatV1Controller.kt``):

============================================== ===== ===========================================
Method+Path                                    Line  Purpose
============================================== ===== ===========================================
``GET /v1/channel/{conversationId}``                 77    Get a single channel/conversation
``GET /v1/channel/{conversationId}/messages``        88    List messages in a conversation
``GET /v1/channels``                                 99    List user's channels
``POST /v1/channel``                                113    Create a new conversation channel
``POST /v1/channel/{id}/message``                   129    Post a non-streaming message
``POST /v1/channel/{id}/action``                    152    Execute a tool/action call
``POST /v1/channel/{id}/message/stream``            164    **Streaming SSE message** (this doc)
``POST /v1/invoke_agent/stream``                    254    Invoke agent without conversation
``POST /v1/invoke_agent``                           296    Same, non-streaming
``PUT /v1/channel/{id}``                            311    Update a conversation
``PUT /v1/channel/{id}/message/{mid}/feedback``     323    Submit thumbs-up/down on a message
``DELETE /v1/channel/{id}``                         336    Delete a conversation
============================================== ===== ===========================================

What this lifecycle doc is NOT
===============================

- **NOT exhaustive of all entry points.** ``ChatV1Controller`` is one of dozens of
  controllers. AgentStudio has its own GraphQL controllers; per-product
  controllers (jsm, csm, rovo, etc.) have their own paths.

- **NOT a description of the LLM's internal flow.** AI Gateway is a separate
  service with its own architecture — see :ref:`ai-gateway` for what
  ``AIGatewayClientServiceImpl`` actually does.

- **NOT a security audit.** The Experience-allowlist + ``@CustomerAccountAllowed``
  annotation are described as observed code patterns, not validated as
  sufficient protection.

