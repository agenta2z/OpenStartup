.. _diag-streaming-sequence:

==============================================
Diagram 2 — Streaming Chat Request Sequence
==============================================

Trace one ``POST /chat/v1/channel/{conversationId}/message/stream`` from HTTP ingress to the first ndjson chunk emitted to the client. This is the **most exercised path** in the codebase.

Top-level sequence
===================

.. mermaid::

   %%{init: {'theme': 'neutral', 'sequence': {'showSequenceNumbers': true, 'mirrorActors': false}}}%%
   sequenceDiagram
       autonumber
       actor Client as HTTP Client<br/>(SDK / Slack bot / browser)
       participant SF as Spring Filter Chain<br/>HeaderFilter
       participant CTL as ChatV1Controller<br/>:164-219
       participant AS as agentService<br/>(deactivation check)
       participant AC as AssistanceClient<br/>(platform-tier facade)
       participant AGS as AIGatewayClientServiceImpl<br/>:1061 streamOpenaiClient
       participant AGW as AI Gateway<br/>(external service)
       participant LLM as OpenAI / Anthropic / etc.<br/>(via AI Gateway)

       Client->>SF: POST .../message/stream<br/>headers: X-Slauth-Issuer,<br/>X-Tenant-Context, X-Cloud-Id<br/>body: { agent_id, message_text }

       Note over SF: Parse + validate headers ONCE
       SF->>SF: Resolve TenantContext,<br/>User, Experience<br/>→ stash in request attributes

       SF->>CTL: forward (suspend fun)<br/>@RequestAttribute injected

       Note over CTL: Wrap entire body in<br/>withMdcContext { } :173<br/>→ MDC survives suspension

       CTL->>CTL: Experience allowlist check :175<br/>{ISSUE_WORK_BREAKDOWN, UNIFIED_HELP}<br/>else throw GoneException (HTTP 410)

       CTL->>AS: isDeactivated(tenantContext, user, agentId)
       alt agent deactivated
           AS-->>CTL: true
           CTL-->>Client: HTTP 410 — AgentDeactivatedException
       end
       AS-->>CTL: false

       CTL->>CTL: preloadRovoAgentIfNeeded(...) :190<br/>resolves agent metadata + perms

       CTL->>CTL: build streamLoggingContext :192<br/>(conversationId, cloudId, agentId, ...)

       CTL->>AC: conversationChannelMessageCreate<br/>StreamWithPassThroughHeaders(...) :219

       Note over AC: PassThroughHeaders pattern<br/>retains X-Slauth-Issuer downstream

       AC->>AGS: streamOpenaiClient(request, ctx, user)

       Note over AGS: getBaseRequestWrapperBuilder()<br/>:1067 — set headers:<br/>USE_CASE_ID, CLOUD_ID,<br/>USER_ID, USER_CONTEXT

       AGS->>AGW: HTTP POST /v1/chat/completions<br/>(streaming via SDK)
       AGW->>LLM: route to provider

       loop for each generated token chunk
           LLM-->>AGW: SSE chunk
           AGW-->>AGS: chunk emitted to Flux<T>
           AGS-->>AC: Flow<ChatCompletionStreamResponse><br/>via .asFlowSafe()
           AC-->>CTL: Flow → Flux<Any>
           CTL-->>Client: ndjson line<br/>(written to HTTP response body)
       end

       Note over AGS: withMetrics() wrapper :1096-1099<br/>records per-call metrics<br/>on Flow completion

       LLM-->>AGW: stream complete (DONE)
       AGW-->>AGS: Flux completes
       AGS-->>AC: Flow completes
       AC-->>CTL: Flux completes
       CTL-->>Client: HTTP response body closed

How to read it
---------------

* **Numbered arrows** = sequential events (Mermaid auto-numbers).
* **Solid arrows** (``->>``) = synchronous suspend call.
* **Dashed arrows** (``-->>``) = return / response.
* **Notes** describe what happens *at* a step (not a separate participant).
* **alt blocks** = conditional branching.
* **loop blocks** = repeated emission (the streaming loop).

Hot spots highlighted
======================

The diagram emphasizes 3 critical spots that aren't obvious from prose:

1. **MDC wrapping happens ONCE at the top** (step ~5 in numbering). Without it, every log line after the first ``suspend`` loses its keys.

2. **PassThroughHeaders is the propagation contract** (~step 14). The original ``X-Slauth-Issuer`` header from the client must reach AI Gateway — NOT a re-minted service token.

3. **The streaming loop is real backpressure** (the ``loop`` block). Reactor/Flow propagates "I want N more items" upstream; if the client is slow, the LLM is paused, not buffered.

What's NOT shown
=================

For diagram readability, these were omitted:

* Authentication (Spring Security ASAP validation) — happens before HeaderFilter; assumed valid for this diagram.
* OTel span lifecycle — every step opens/closes spans; would clutter.
* Metrics emissions — happen on completion, shown as a Note rather than separate participant.
* Error paths beyond the deactivation alt — circuit breaker, timeout, malformed output all have their own flows.
* Conversation persistence — the chunks are also written to Kamino in parallel; not shown to keep focus.
* Tool calls within the LLM response — if the LLM emits a ``tool_call``, the platform pauses streaming, executes the tool, and resumes. Separate diagram needed.

A separate "with tool calls" diagram would show steps like:

::

   LLM emits tool_call →
       Platform pauses stream →
       Platform calls ActionExecutor (platform/action/) →
       Result fed back to LLM →
       LLM resumes generation →
       Platform resumes stream

The error-paths overlay
========================

When something goes wrong, the flow forks. Showing all forks in one diagram is unreadable; here's the overlay separately:

.. mermaid::

   stateDiagram-v2
       [*] --> RequestReceived

       RequestReceived --> ExperienceValidated: experience in allowlist
       RequestReceived --> HTTP_410_Gone: experience NOT in allowlist
       HTTP_410_Gone --> [*]

       ExperienceValidated --> AgentChecked
       AgentChecked --> Streaming: agent active
       AgentChecked --> HTTP_410_AgentDeactivated: agent deactivated
       HTTP_410_AgentDeactivated --> [*]

       Streaming --> CompletedSuccessfully: LLM stream done
       Streaming --> RateLimited: HTTP 429 from AI Gateway
       Streaming --> CircuitBreakerOpen: too many failures
       Streaming --> Timeout: AI Gateway timeout
       Streaming --> MalformedOutput: parser fails

       RateLimited --> RetryWithBackoff
       RetryWithBackoff --> Streaming: under retry limit
       RetryWithBackoff --> ClientError429: retry exhausted

       CircuitBreakerOpen --> FailOpen: feature gate enabled
       CircuitBreakerOpen --> Client5xx: feature gate disabled

       Timeout --> FailOpen
       MalformedOutput --> FailOpen: feature gate enabled
       MalformedOutput --> Client5xx: feature gate disabled

       FailOpen --> [*]
       Client5xx --> [*]
       ClientError429 --> [*]
       CompletedSuccessfully --> [*]

How to read this state diagram
-------------------------------

Each LLM call passes through ``Streaming`` — the long-lived state during chunk emission. From there, 5 outcomes are possible:

* **CompletedSuccessfully** — happy path
* **RateLimited (429)** — soft retry
* **CircuitBreakerOpen** — too many recent failures
* **Timeout** — wall-clock timeout from AI Gateway
* **MalformedOutput** — model returned unparseable response (e.g. truncated reasoning)

The last 3 are gated by **feature flags** that decide between "fail open with a default response" vs "return 5xx to client". This is the pattern the responsible-ai-api work mirrored (PR #620's fail-open-on-malformed-output gate).

