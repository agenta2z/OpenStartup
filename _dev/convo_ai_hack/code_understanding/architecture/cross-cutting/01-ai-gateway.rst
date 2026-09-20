.. _ai-gateway:

============================
AI Gateway Integration
============================

This page documents how the platform calls Atlassian's internal AI Gateway service to reach LLM providers (OpenAI, Anthropic, Google, DeepSeek). It is the **single most important cross-cutting concern** in the codebase.

The 3,087-line service
=======================

**File** :sup:`(verified)`: ``modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/AIGatewayClientServiceImpl.kt``

Verified via ``wc -l``: **3,087 lines**.

Class declaration (lines 110-114, verified):

.. code-block:: kotlin

   @ExcludeFromCoverage("AI Gateway client implementation")
   @Primary
   @Suppress("UNUSED_PARAMETER")
   @Component
   class AIGatewayClientServiceImpl(...)

Why ``@ExcludeFromCoverage``? This class is **integration-tested** against a wiremocked AI Gateway, but the code paths are too numerous and too provider-specific to unit test exhaustively. Coverage measurement is excluded so it doesn't degrade module-level metrics.

Why ``@Primary``? Multiple ``AIGatewayClientService`` beans may exist (mock and real); ``@Primary`` ensures the real one wins in production.

Provider matrix (15+ public methods)
======================================

The class exposes overloaded methods for each (provider × suspend|stream × variant) combination:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Method
     - Line
     - Purpose
   * - ``callOpenaiClientSuspend``
     - 883
     - Synchronous OpenAI completion
   * - ``callOpenaiClientForDeepResearchSuspend``
     - 952
     - Sync deep-research variant
   * - ``callOpenAiClientResponsesSuspend``
     - 1010
     - Sync via Responses API
   * - ``streamOpenaiClient``
     - 1061
     - Streaming OpenAI completion
   * - ``streamOpenaiClientResponses``
     - 1103
     - Streaming via Responses API
   * - ``streamOpenaiClientForDeepResearch``
     - 1160
     - Streaming deep-research
   * - ``streamOpenaiClientForDeepResearchResponses``
     - 1204
     - Streaming deep-research Responses API
   * - ``streamAnthropicAIClient``
     - 1253
     - Streaming Anthropic
   * - ``callGoogleAIClientSuspend``
     - 1308
     - Sync Google
   * - ``streamGoogleAIClient``
     - 1360
     - Streaming Google
   * - ``callGoogleAIClientRawPredictSuspend``
     - 1407
     - Sync Google rawPredict
   * - ``streamGoogleAIClientRawPredict``
     - 1459
     - Streaming Google rawPredict
   * - ``callAnthropicAIClientSuspend``
     - 1503
     - Sync Anthropic
   * - ``callDeepSeekClientSuspend``
     - 1571
     - Sync DeepSeek
   * - ``streamDeepSeekClient``
     - 1629
     - Streaming DeepSeek (note: ``override fun``, not ``suspend fun``)

Pattern: **call vs stream** suffix; **Suspend** suffix marks the suspend variant.

Attribution headers :sup:`(verified)`
=======================================

Every outbound call to AI Gateway sets attribution headers (lines 654-658, verified):

.. code-block:: kotlin

   .header(AIGatewayHeaders.USE_CASE_ID, useCaseManager.getAiGatewayUseCaseId(aiGatewayContext))
   .header(AIGatewayHeaders.CLOUD_ID, aiGatewayContext.getAiGatewayCloudId())
   // Always attribute LLM usage to the invoking human user, even if executing with an AgentPrincipal
   .header(AIGatewayHeaders.USER_ID, user.getInvokingUser().getAccountId().value())
   .header(AIGatewayHeaders.USER_CONTEXT, user.getInvokingUser().getUserContextHeaderValue())

Why the comment about "AgentPrincipal"? Because some flows execute as a service identity (an agent acting on the user's behalf), but billing and quota MUST attribute to the original human user. Hence ``user.getInvokingUser()`` not ``user.getAccountId()``.

These four headers feed:

- ``USE_CASE_ID`` → AI Gateway routing (different use cases get different model defaults, retry policies, prompt caching strategies)
- ``CLOUD_ID`` → multi-tenant attribution; per-tenant rate limits
- ``USER_ID`` → individual quota tracking; auditing
- ``USER_CONTEXT`` → arbitrary additional context (consent state, locale, etc.)

The attribution headers ALSO appear at line 2266+ — confirming the pattern is repeated across multiple call sites within the same file.

Use-case management
====================

The ``useCaseManager`` (a constructor-injected dependency) maps an ``aiGatewayContext`` (which encodes product, experience, agent ID) to a stable use-case identifier. This is what AI Gateway uses to route to the right model defaults.

Examples (inferred):

- ``AiGatewayContext(product=jira, experience=ISSUE_WORK_BREAKDOWN)`` → use_case_id ``jira-issue-work-breakdown``
- ``AiGatewayContext(product=rovo, agent=customer-support-v3)`` → use_case_id ``rovo-customer-support-v3``

Use-case IDs are likely defined in product-tier configuration and registered with AI Gateway out-of-band.

Streaming flow
===============

For a ``streamOpenaiClient(...)`` call (line 1061):

1. Build OpenAI request payload (model, messages, tools, stream=true)
2. Add attribution headers (lines 654-658 pattern)
3. POST to AI Gateway streaming endpoint
4. AI Gateway proxies to upstream OpenAI
5. Response is SSE; each chunk is parsed into a typed ``ChatCompletionStreamResponse``
6. Returned as ``Flow<ChatCompletionStreamResponse>`` to caller

The caller (e.g. ``ChatV1Controller.conversationChannelMessageCreateStream``) wraps this Flow as a ``Flux<Any>`` for Spring WebFlux's ndjson encoder.

Backpressure: Reactor's default is to back-pressure upstream (request items as the consumer can keep up). For LLM streaming this means: if the HTTP client is slow to consume chunks, the upstream OpenAI fetch is paused. **No buffer-overrun risk** even with very long generations.

Provider-specific quirks
=========================

Each provider has subtle differences:

- **OpenAI:** Uses standard chat/completions API. Has a "Responses" variant (newer streaming API) and a "deepResearch" variant (multi-step research mode).
- **Anthropic:** Uses Messages API (not chat/completions). Different streaming SSE format.
- **Google (Gemini):** Two variants — standard predict, and rawPredict (lower-level, fewer transformations).
- **DeepSeek:** Compatible with OpenAI shape but routed differently. Notable: ``streamDeepSeekClient`` is NOT a suspend fun — likely returns a Flow directly without suspending the caller.

The class normalizes all providers to a common return type (``ChatCompletionStreamResponse``) but the internal request building is provider-specific.

Error handling :sup:`(inferred)`
=================================

Without reading the entire 3,087-line file, the typical pattern is:

1. **HTTP errors** (4xx from AI Gateway) → wrapped in ``AIGatewayResponseException`` with status code
2. **Network timeouts** → wrapped in ``AIGatewayTimeoutException``
3. **Provider-specific errors** (rate limit, content policy, malformed output) → wrapped in typed exceptions
4. **Retry policy** → likely circuit-breaker + exponential backoff via Resilience4j (common Atlassian pattern)

The integration test results (``hack_states/02-integrationTest-result.md``) show ``AIGatewayResponseException`` thrown by SAINStandaloneHybridOrchestratorIT — confirming this exception type is real and surfaces to higher layers when the wiremock returns unexpected payloads.

Token counting / metrics
=========================

After each call, the response includes token usage (prompt tokens, completion tokens, total). This is emitted as metrics tagged by use_case_id, cloud_id, model, and provider. See :ref:`telemetry` for the metric schema.

Patterns specific to AI Gateway integration
=============================================

1. **Always attribute to invoking human, not service.** The ``user.getInvokingUser()`` pattern (line 657) is mandatory to keep billing/quota correct.

2. **Use case ID is the primary routing key.** AI Gateway makes most decisions based on USE_CASE_ID, not on the request body. Choose a stable use_case_id per product feature.

3. **Provider differences are local to this file.** The 3,087 lines exist precisely so the rest of the codebase doesn't have to know about Anthropic vs Google vs OpenAI quirks. Keep that abstraction tight.

4. **Suspend for sync; Flow for stream.** The file uses suspend fun for "wait for full completion" calls and Flow for "stream chunks". Do not mix.

5. **Don't bypass this client.** Direct calls to provider SDKs would skip attribution, metrics, and retry. Always go through ``AIGatewayClientServiceImpl``.

What you would change here
===========================

- **Add a new provider** → add new ``call`` and ``stream`` methods at the bottom of the class
- **Change attribution semantics** → modify the header-building section (lines 654-658 + 2266-2268)
- **Adjust retry policy** → find the retry configuration (likely a constructor parameter or builder)
- **Add a new use-case** → register in ``UseCaseManager`` (separate class, not in this file)

What you would NOT change here
===============================

- Per-request prompt template rendering (lives in product/<name>/templates/)
- Per-request tool selection (lives in tool-registry/)
- Per-tenant rate limiting (lives in foundation/utilities/featureflag/)

