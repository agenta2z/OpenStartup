.. _diag-ai-gateway:

==================================================
Diagram 3 — AI Gateway Provider Topology
==================================================

The 3,087-line ``AIGatewayClientServiceImpl`` exposes 15+ public methods spanning 4 providers and 3 axes (call vs stream, sync vs suspend, raw vs Responses-API). This diagram makes the matrix visible.

The provider × variant matrix
==============================

.. mermaid::

   flowchart LR
       %% Caller side
       CTL["Controllers / AssistanceClient<br/>(via platform/service-api)"]

       %% The orchestrator
       AGSI["**AIGatewayClientServiceImpl**<br/>(3,087 lines)<br/>@Primary @Component<br/>line 113"]

       %% Helper inside AGSI
       HDR["getBaseRequestWrapperBuilder()<br/>line 1067<br/><br/>Sets headers:<br/>USE_CASE_ID :654<br/>CLOUD_ID :655<br/>USER_ID :656<br/>USER_CONTEXT :657"]

       ERR["executeStreamingWithErrorCategorization()<br/>line 356-363<br/><br/>Wraps with:<br/>• logging context<br/>• exception type mapping<br/>• 429 rate-limit detection"]

       MTR["withMetrics()<br/>line 2620+<br/><br/>Records on completion:<br/>• success / error count<br/>• status code mapping<br/>• provider tag"]

       %% AI Gateway
       AGW["**AI Gateway**<br/>(external service)"]

       %% Provider methods grouped
       subgraph OAI["OpenAI methods"]
           OAI1["callOpenaiClientSuspend :883"]
           OAI2["callOpenAiClientResponsesSuspend :1010"]
           OAI3["streamOpenaiClient :1061"]
           OAI4["streamOpenaiClientResponses :1103"]
           OAI5["streamOpenaiClient<br/>ForDeepResearch :1160"]
       end

       subgraph ANT["Anthropic methods"]
           ANT1["callAnthropicAIClientSuspend :1503"]
           ANT2["streamAnthropicAIClient :1253"]
       end

       subgraph GOO["Google methods"]
           GOO1["callGoogleAIClientSuspend :1308"]
           GOO2["streamGoogleAIClient :1360"]
           GOO3["callGoogleAIClient<br/>RawPredictSuspend :1407"]
           GOO4["streamGoogleAIClient<br/>RawPredict :1459"]
       end

       subgraph DSK["DeepSeek methods"]
           DSK1["callDeepSeekClientSuspend :1571"]
           DSK2["streamDeepSeekClient :1629"]
       end

       %% Wiring
       CTL --> AGSI
       AGSI --> OAI
       AGSI --> ANT
       AGSI --> GOO
       AGSI --> DSK

       OAI -.uses.-> HDR
       ANT -.uses.-> HDR
       GOO -.uses.-> HDR
       DSK -.uses.-> HDR

       OAI -.wraps with.-> ERR
       OAI -.wraps with.-> MTR

       OAI --> AGW
       ANT --> AGW
       GOO --> AGW
       DSK --> AGW

       AGW -->|routes by USE_CASE_ID| OpenAI[(OpenAI)]
       AGW --> Anthropic[(Anthropic)]
       AGW --> Google[(Google Gemini)]
       AGW --> DeepSeek[(DeepSeek)]

       %% Style
       style AGSI fill:#fff8e1,stroke:#f57c00,stroke-width:3px
       style HDR fill:#e1f5ff,stroke:#0277bd
       style ERR fill:#fce4ec,stroke:#c2185b
       style MTR fill:#f1f8e9,stroke:#558b2f
       style AGW fill:#ede7f6,stroke:#5e35b1,stroke-width:2px

How to read it
---------------

* The **central orange box** is ``AIGatewayClientServiceImpl`` — the single entry point for all LLM calls.
* The **15 colored sub-method boxes** are the public methods the rest of the codebase invokes; each is named ``<provider><call|stream>...`` with its line number.
* **3 helper boxes** (blue/pink/green) show the cross-cutting concerns each method routes through: header building, error wrapping, metrics.
* The **purple box** (AI Gateway) is the external service all methods proxy through.
* The **right-edge databases** are the actual LLM providers AI Gateway routes to based on the ``USE_CASE_ID`` header.

The 3 axes
===========

Each method is a point in this 3D space:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Axis
     - Values
     - Meaning
   * - Provider
     - OpenAI / Anthropic / Google / DeepSeek
     - Which provider's SDK and request shape
   * - Call mode
     - Suspend (one shot) / Stream (chunked)
     - Whether to wait for full response or emit chunks
   * - API variant
     - Standard / Responses / DeepResearch / RawPredict
     - Provider-specific API surface variation

There are 4 × 2 × 4 = 32 combinations, but only ~15 are actually implemented (not every combination is meaningful — e.g. DeepSeek doesn't have a "DeepResearch" variant).

The "happy-path" inside one method
====================================

Verified call sequence for ``streamOpenaiClient(...)`` (line 1061):

.. mermaid::

   sequenceDiagram
       autonumber
       participant CALLER as Caller
       participant AGS as streamOpenaiClient<br/>:1061
       participant HDR as getBaseRequestWrapperBuilder<br/>:1067
       participant SDK as openAiClient()<br/>(SDK instance)
       participant ERR as executeStreaming<br/>WithErrorCategorization<br/>:356-363
       participant FLOW as Flow / Flux<T>

       CALLER->>AGS: streamOpenaiClient(request, ctx, user)
       AGS->>HDR: build request wrapper
       HDR-->>AGS: requestWrapper with headers<br/>USE_CASE_ID, CLOUD_ID,<br/>USER_ID, USER_CONTEXT
       AGS->>AGS: logLLMRequest("streamOpenaiClient", request) :1071
       AGS->>ERR: wrap call (provider="OpenAI",<br/>endpoint="chat_completions_stream") :1073
       ERR->>SDK: v1ChatCompletionsStream(...)<br/>.awaitWithContext() :1079
       SDK-->>ERR: Mono<ResponseWrapper<Flux<T>>>
       ERR-->>AGS: response

       alt HTTP 429 (rate limit)
           AGS->>AGS: extract RATE_LIMIT_TYPE_HEADER :1082-1089
           AGS->>CALLER: throw OpenAIRateLimitException
       end

       alt Non-2xx response
           AGS->>AGS: logAIGatewayError() :1091-1093
       end

       AGS->>FLOW: emitAll(response.bodyOrThrow...asFlowSafe()) :1095
       Note over FLOW: Convert Flux → Flow<br/>with UninitializedPropertyAccessException<br/>handling :2383-2407
       FLOW-->>CALLER: Flow<ChatCompletionStreamResponse>

       Note over AGS,FLOW: .withMetrics() wraps the Flow :1096-1099<br/>records metrics on completion

Why such a giant file?
=======================

The 3,087-line size is **intentional**. Each provider has subtle wire-format differences (request shape, streaming chunk format, error code semantics, rate-limit header conventions). Centralizing these in ONE file means the rest of the codebase (12,989 other files) can stay provider-agnostic.

Splitting the file into per-provider classes was considered (per the agent investigation); rejected because the cross-provider concerns (attribution headers, error categorization, metrics, retry policy) would have to be duplicated 4×.

Trade-off accepted: one large class for correctness of cross-cutting concerns; readability hit absorbed.

Patterns visible in this diagram
==================================

1. **Single entry point.** All LLM calls go through ``AIGatewayClientServiceImpl``. No bypass paths exist (and reviewers should reject any).

2. **Identical attribution for all providers.** Whether OpenAI or DeepSeek, the same 4 attribution headers are set. Billing/quota cannot be skewed by provider choice.

3. **Provider differences are local.** Adding a 5th provider means adding a new ``call`` and ``stream`` method to this file — but no other file changes.

4. **Sync vs streaming is symmetric.** Every provider has both a ``call*Suspend`` (sync) and a ``stream*`` (async) method; there's no asymmetric capability.

