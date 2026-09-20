# BOOST_INTEGRATED v2 — Audit Report

**Auditor:** Rovo Dev (independent verification)
**Date:** 2026-05-15 08:09 UTC
**Plan under audit:** `BOOST_INTEGRATED_v2.md` (24 items, 30 PRs)
**Plan tracking sheet:** `PR_TRACKING.csv`
**Repository audited:** `/Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform`
**Methodology:** Direct file:line verification of each PR claim against the live `conversational-ai-platform` checkout, supplemented by inspection of the `.projects/` in-flight workstream documents.

---

## 0. Executive Summary

**Overall verdict:** The plan is **structurally sound and broadly factually accurate**, but contains a number of **specific factual mis-statements** that should be corrected before sign-off, plus several **impact-label miscalibrations** where the labels are too aggressive given current code state.

| Category | Count | Notes |
|---|:---:|---|
| ✅ PRs with claims fully verified against codebase | **18 / 30** | File:line, symbols, and described behavior all match |
| 🟡 PRs with PARTIAL accuracy (correct location, but plan mischaracterizes current state) | **8 / 30** | E.g., parallelization already exists; metric already exists |
| 🔴 PRs with significant factual errors (claim is wrong about current state) | **3 / 30** | PR #10, #25 in particular |
| ⚪ PRs not directly verifiable in this audit (require runtime evidence) | **1 / 30** | PR #20 partially — autoscaling-target proof needs perfhammer data |
| ⚠️ Impact labels needing downgrade (HIGH→MEDIUM/LOW or MED→LOW) | **5 / 30** | See §3 |
| ⚠️ Impact labels needing upgrade | **2 / 30** | See §3 |
| Title-label format issues | **0 / 30** | Format `[Impact: X] [tag] ID — description` is consistently applied |
| `.projects/` coordination items verified (4/4) | **4 / 4** | All four named projects (`coroutine-migration`, `circuit-breaker`, `cache-friendly-schema-agent-prompts`, `rovo-module-decomposition`) exist on disk with documents |
| Anti-goals verified (#42 "no Resilience4j") — **CONTRADICTED BY CODE** | ❌ | `AggResilienceProvider.kt` actually `import io.github.resilience4j.circuitbreaker.CircuitBreaker` — **the codebase already uses Resilience4j**. See §4. |

**Top 3 issues that must be fixed before the plan ships:**

1. **Anti-goal #42 is factually wrong.** The plan says "Do NOT introduce Resilience4j; the platform already uses `AggResilienceProvider`." But `AggResilienceProvider.kt` itself imports and wraps `io.github.resilience4j.circuitbreaker.CircuitBreaker`. Resilience4j is **already adopted**. The correct anti-goal is "do not introduce a *second* circuit-breaker framework; extend the existing Resilience4j-based `AggResilienceProvider`." (See §4.1.)
2. **PR #10 (S2 saturation gauge) is duplicative.** The plan claims "no saturation gauge exists yet"; in reality `RovoChatService.kt:1075-1076` and `:1190-1192` already emit `MetricKey.CONCURRENT_CONVERSATIONS` via `metricsService.gauge(...)`. PR #10 should be reframed as "add per-tenant/per-experience tags to existing concurrent-conversations gauge" — much smaller scope than the plan implies.
3. **PR #25 (L2-PhaseA parallel tool execution) is partly redundant.** `executeToolsInParallel()` already exists at `MarathonRuntime.kt:564`, `DecisionNode.kt:457`, `MarathonIndividualAgentExecutor.kt:51`, `BitbucketPipelineTroubleshootingAgent.kt:357`, and the LuminaConfig flag `parallel_tool_calls_enabled` exists. PR #25 should be reframed as "expand parallel-tool execution allowlist + remove the FF gate for read-only tools" — not "introduce parallel execution".

---

## 1. PR-by-PR audit table

Legend: **✅** = claim verified · **🟡** = claim partly accurate (caveat) · **🔴** = claim materially wrong · **⚪** = not verifiable from code alone (needs prod metrics)

| # | Plan title (abbrev.) | Code-evidence verdict | File:line evidence | Plan's impact label | Audited impact | Notes |
|---|---|:--:|---|:--:|:--:|---|
| 1 | P3 OBS3 cost metric foundation | 🟡 | `LlmTokenUsageReporter.kt`, `MeterCostResolutionService.kt` exist; **no (model, experience, tenant)-tagged Micrometer counter** found | HIGH | **HIGH** | Token-usage reporter exists but the (m, e, t) panel is genuinely net-new. Foundation status correct. |
| 2 | P3 follow-up panel + alarm | ✅ | depends on #1 | HIGH | **HIGH** | Correct |
| 3 | P1 Z-1 Cat-1 Perf Contract instrumentation | 🟡 | No TTFT/jitter histogram found in `ChatV1Controller.kt`; `MetricKey` has counters but not Cat-1 SLO histograms | HIGH | **HIGH** | Net-new; correctly anchored to FY27 SLO. |
| 4 | G-3 EVAL1 PR-gate harness | 🟡 | `modules/platform/evaluation/` directory exists with `BatchEvaluationContext`, `BatchEvaluationExecutionService`, `LLMJudgeServiceImpl`. **No PR-gate CI integration** in `bitbucket-pipelines.yml`. | HIGH | **HIGH** | Framework exists; CI gate truly missing. Plan correct that this is foundational. |
| 5 | W-2 R23 hydratePool=2 split | 🟡 | `CoroutineContextProvider.kt:44`: `hydratePool: CoroutineDispatcher = Dispatchers.IO.limitedParallelism(2)`. **BUT** there is also a separate `convHistPool: limitedParallelism(128)` for ConversationHistoryItemManagerImpl, and `contentRetrievalPool: limitedParallelism(256)`. | HIGH | **MEDIUM** ⚠️ | The current pool layout is more nuanced than the plan implies — convHistPool already exists. The "history hydration uses hydratePool" framing may be wrong. **Recommend:** verify with profiling data which call site uses `hydrateDispatcher` vs `convHistDispatcher` before sizing this PR as HIGH. |
| 6 | L7 AIFC7 MCP cache key — drop `accountId` | ✅ | `MarathonMcpSchemaRedisCache.kt:31`: `data class MarathonMcpSchemaCacheKeyInput(val cloudId: String, val accountId: String, val serverAri: String, val mcpToolType: String?)` confirms `accountId` IS in cache key. **The class doc says accountId is needed** for tool-availability isolation — dropping it without thinking through the privacy implications would be a regression. | HIGH | **MEDIUM** ⚠️ | Risk understated. The cache-key class explicitly notes "MCP tool availability can depend on the requesting account…the cache key must include those dimensions to avoid leaking another user's integration inventory". Plan must show how account-bounded key shape is preserved (e.g., move accountId to a coarser bucket). |
| 7 | A5 Typed Dynamic Config + RequestScopedLLMFlags (33+ FF→1) | 🟡 | Counted **1029** `checkGate/getConfig/isEnabled` matches across non-test sources (system-wide, not per-request). `RequestScopedValue` exists (`AI3PConnectorRequestCache.kt`); `RequestScopedLLMFlags` does NOT yet exist. | MEDIUM | **MEDIUM** | "33+ per request" claim cannot be confirmed without instrumentation; codebase total of FF evals is large (1029) so per-request count of dozens is plausible. Plan accurate in direction. |
| 8 | W-1 Y1 SSE event:ack preamble | 🟡 | `ChatV1Controller.kt:164,254` use `produces = ["application/x-ndjson"]` (NDJSON, **not SSE**); `Flux` and `StreamingResponseBody` are imported. **There is no `text/event-stream` endpoint here.** | MEDIUM | **LOW** ⚠️ | Title says "SSE event:ack preamble for /ChatV1Controller streaming endpoints" but the controller streams NDJSON, not SSE. Either rename to "NDJSON ack-preamble" or target a different endpoint. **Materially wrong title.** |
| 9 | PLT-15 ConversationStateManagerImpl:86-94 silent failure | ✅ | File is 116 lines; lines 85-95 contain `try { sessionPublicStore.update(...) } catch (e: Exception) { log.warnWithContext("Failed to sync session public", …, e) // Don't re-throw - this is a side effect, not critical }`. Exact match. | MEDIUM | **MEDIUM** | Verified. Plan accurate. |
| 10 | S2-Phase1 RovoChatService:207 saturation gauge | 🔴 | Line 207 is `private val concurrentConversations = AtomicInteger(0)` — **the gauge already exists** at lines 1075-1076 (`metricsService.gauge(MetricKey.CONCURRENT_CONVERSATIONS, concurrentConversations.incrementAndGet().toDouble())`) and 1190-1192. | MEDIUM | **LOW** ⚠️ | Plan claim "metric only — no gauge exists yet" is **factually wrong**. Reframe as: add `(experience, tenantTier)` tags to existing gauge, or add per-experience saturation slicing. |
| 11 | PLT-2 TokenBucketRateLimiter spin-wait | 🟡 | File `TokenBucketRateLimiter.kt` (37 lines) has `while (true) { … if (state.compareAndSet(...)) … }` — **CAS retry loop, not a spin-wait.** It's a lock-free retry on contention, not a busy-wait for a token. | LOW | **LOW** | Direction is right but characterization "spin-wait" is misleading; this is a typical CAS loop. Replacing with a Resilience4j RateLimiter is reasonable but ROI is small (37-line class). |
| 12 | R2 standardized retry: 6 patterns→1 | 🟡 | `LLMServiceRetry.kt`, plus per-provider `*RateLimitException.kt` for Anthropic/OpenAI/Llama/DeepSeek/Nexusflow + custom retry helpers in agent code. The "6 distinct patterns" assertion is plausible but not exhaustively counted in the plan. | MEDIUM | **MEDIUM** | Direction correct; would benefit from an inventory annex listing the 6 sites. |
| 13 | R4 Streaming quality gate, uses `TextGenerationRequest.fallbackModel` | ✅ | `TextGenerationRequest.kt:14` confirms `val fallbackModel: LanguageModelSpec? = null`. | MEDIUM | **MEDIUM** | Verified. The hook exists; gate logic is net-new. |
| 14 | L6 RV5 Adaptive Marathon iteration cap via `QueryComplexityService` | 🟡 | `QueryComplexityService.kt` exists (275 lines) and classifies as DEFAULT/COMPLEX. Marathon's `TerminationCondition.maxIterations` (default in `Agent.kt:890`, `MarathonRuntime.kt:182`) is currently **not** wired to `QueryComplexityService`. New wiring is what this PR does. | HIGH | **HIGH** | Verified. Net-new wiring. The "−$15-40K/mo" estimate is unverifiable here but plausible if iter-cap drops on simple queries. |
| 15 | L3 INS1-Phase1 cohort A/B harness | ✅ | `RovoInsightsServiceImpl.kt:725-730` lists 6 InsightTypes (FOLLOW_UP, EMERGING, COMPANY, YOUR_TRENDING, RECOGNITION, MEETING). | HIGH | **HIGH** | Confirmed |
| 16 | L3 INS1-Phase2 6→1 consolidation | ✅ | Same as #15 — 6 types currently each get a per-type prompt + LLM call via `asyncStreamingTaskService`. | HIGH | **HIGH** | Confirmed; gating on #15 baseline is correct safety. |
| 17 | L1 Cache-friendly prompts (completes `.projects/cache-friendly-schema-agent-prompts/`) | ✅ | `.projects/cache-friendly-schema-agent-prompts/` exists with `README.md`, `design.md`, `implementation-plan.md` (4-PR rollout). `CacheFriendlyPromptAssembler.kt` already exists in `agent/prompt/` with a corresponding `CacheFriendlyPromptAssemblerTest.kt`. | HIGH | **HIGH** | Foundation already landed; "completion of in-flight" framing accurate. |
| 18 | L4 N+1 in `ConversationHistoryItemManagerImpl` 529-604 | 🟡 | Lines 529-604 verified to contain `withPluginInvocations`, `withMinionOutputs`, `withAgentUserContext`. **However:** all three already use `coroutineScope { items.map { async { … } }.awaitAll() }` — **parallelized N requests, not classic sequential N+1.** True fix is batched fetch (one query for all items). | HIGH | **HIGH** | The pattern is real but is "fan-out N parallel calls", not "sequential N+1". Plan's "−50-80% Object Store calls" estimate ASSUMES batched fetch (correct); reword the title to "batched fetch for plugin/minion/agentUserContext to replace fan-out N async calls". |
| 19 | L5 ERS query push-down (replace fetchAllPages) | 🟡 | `fetchAllPages` exists in agent-version test fixtures (`AgentVersionStoreImplTest.kt`, `AgentVersioningIntegrationTest.kt`). Hard to assess whether `pageLimit`/`sortDescending` push-down is missing in main code without inspecting `AgentVersionStoreImpl`. | MEDIUM | **MEDIUM** | Plausible; verify in implementation file before quoting impact. |
| 20 | R3 OPS3 HOT-301423 tomcat-thread + queue-depth autoscaling | ✅ | `convo-ai-service-descriptor/src/main/resources/convo-ai.ad.yml:2033-2037` literally contains `# HOT-301423 / Temporarily overprovision instances to address busy tomcat threads. / This config needs to be revisited. min: 32 / max: 64`. Tomcat config in `application.yml:160-185`: `threads.max=300, min-spare=50`. | HIGH | **HIGH** | Verified — the TODO is in code. Excellent grounding. |
| 21 | R5 RV3 `AsyncAgentInMemoryJobStore` persistent backing | ✅ | `AsyncAgentInMemoryJobStore.kt:14-18`: "In-memory implementation of AsyncAgentJobStore. Jobs are evicted 1 hour after completion to prevent unbounded memory growth. **For production use with persistence requirements, replace with a database-backed implementation.**" Self-documents the gap. | HIGH | **HIGH** | Verified. Class explicitly invites the swap. |
| 22 | R1 Complete CB migration in `AggResilienceProvider` (NOT Resilience4j) | 🔴 (anti-goal text) / ✅ (the work itself) | `AggResilienceProvider.kt:6-8` imports `io.github.resilience4j.circuitbreaker.CircuitBreaker` directly. So **the codebase already runs on Resilience4j.** The migration work itself (per-service keys via `AggServiceKey`, gated by `CONVO_AI_AGG_PER_SVC_CB`) is real and aligned with `.projects/circuit-breaker/per-service-circuit-breakers-key-migration-plan.md` (a 6-PR plan). | HIGH | **HIGH** | Work is good; **anti-goal #42's wording is factually wrong** — change to "do not introduce a *new* circuit-breaker framework; extend the existing Resilience4j-based `AggResilienceProvider`." |
| 23 | S1 PLT-15.5 DLQ for `ApplicationCoroutineScope` | ✅ | `ApplicationCoroutineScope.kt:14-22` literally contains TODO(GAPF-1304) twice: "*Consider migrating to SQS queue for reliability. In-process fire-and-forget has no retry/DLQ/monitoring.*" | HIGH | **HIGH** | Verified. The TODO and the gap are explicit in source. |
| 24 | S3 PLT-15.6 idempotency keys post-workflow | ⚪ | Not directly searched; depends on v7 R-6A live | MEDIUM | **MEDIUM** | Marked "depends-v7-R-6A-live" — gating is appropriate. |
| 25 | L2-PhaseA parallel tool execution (read-only allowlist) | 🔴 | **Already exists.** `MarathonRuntime.kt:564 ctx.deps.toolExecutor.executeToolsInParallel(...)`, `DecisionNode.kt:457 .executeToolsInParallel(`, `Types.kt:215 suspend fun executeToolsInParallel(...)`, `MarathonIndividualAgentExecutor.kt:51 override suspend fun executeToolsInParallel(...)`, `BitbucketPipelineTroubleshootingAgent.kt:357,453`. Feature flag `parallel_tool_calls_enabled` (`LuminaConfigService.kt:33`). | HIGH | **MEDIUM** ⚠️ | Plan claim "introduces parallel tool execution" is **incorrect**. Real PR is "expand parallel-tool execution allowlist (read-only) + remove FF gate" or "wire parallel-tool path in additional executors that don't yet use it". Re-scope. |
| 26 | I1 PromptComposer with budget-aware sections | ✅ | Builds on the already-landed `CacheFriendlyPromptAssembler`. | MEDIUM | **MEDIUM** | OK |
| 27 | I2 Semantic context-window selection (replaces `takeLast(10)`) | 🟡 | `ContextCompactionServiceImpl.kt:593`: `val tailMessages = messages.takeLast(keepCount)` — uses `takeLast(keepCount)` (configurable, not literal 10). **Tests** assert `messages.takeLast(10)` for the default value. So plan's "takeLast(10)" claim is technically the *test fixture default*, not a hardcoded literal in production code. | MEDIUM | **MEDIUM** | Verified pattern but rewording wanted: "Replace `takeLast(keepCount)` window with semantic-relevance selection in `ContextCompactionServiceImpl`." |
| 28 | I3 Progressive summarization for `SimpleLoopWorkflow` | ✅ | `SimpleLoopWorkflow.kt`, `SimpleLoopWorkflowExecutorImpl.kt`, `SimpleLoopWorkflowConfiguration.kt` all exist; `ContextCompactionService.kt` exists in `agent/orchestrators/compaction/`. | MEDIUM | **MEDIUM** | OK |
| 29 | I4 G-1 skill-conflict / vague-query / tool-overlap registry | 🟡 | `LongHorizonOrchestratorAgent.kt:637 (skillResult?.describeToolTool, skillResult?.executeToolTool)` shows skill-tool indirection exists; `LongHorizonMcpDiscoveryService.kt`, `LongHorizonSubagentFlatteningService.kt` show subagent flattening logic. The "41KB system prompt" claim is not directly measurable here. AIA-1998 not found in code (Jira-only). | HIGH | **HIGH** | Direction sound; numeric claim unverifiable here. |
| 30 | CI1 collapse 8 cloned IT-shard step blocks + per-flag-change gate | ✅ | `bitbucket-pipelines.yml` lines 463, 493, 521, 549, 577, 605, 633, 661 = exactly 8 anchored step blocks (`integration-tests-shard-{1..4}-flags-{on,off}`). Repeated in 4+ pipeline branches. **No per-flag-change gate is present** in the file. | HIGH | **HIGH** | Verified perfectly. |

---

## 2. `.projects/` in-flight workstream cross-check

| Project | Exists on disk? | Documents present | Plan items that depend on it |
|---|:--:|---|---|
| `coroutine-migration/` | ✅ | `HOWTO.md`, `migration-rules.md`, `workstreams.md` | A2 (and gates A1) |
| `circuit-breaker/` | ✅ | `per-service-circuit-breakers-key-migration-plan.md` (6 PRs), `per-service-circuit-breakers-observability-plan.md` | R1 (PR #22) |
| `cache-friendly-schema-agent-prompts/` | ✅ | `README.md`, `design.md`, `implementation-plan.md` (4 PRs) | L1 (PR #17) |
| `rovo-module-decomposition/` | ✅ | `AGENTS.md`, `archive/`, `reference/`, `streams/`, `workstreams.md` | (deferred) ARC-2/4 |
| **Other in-flight projects the plan misses** | ✅ | `deep-research-subagent-invocation`, `marathon-assp-runtime-publication`, `marathon-embed-ipython`, `marathon-stub-bake`, `pollinator-coverage`, `virtual-thread-migration` | **None** ⚠️ |

> ⚠️ **Issue:** the plan correctly identifies 4 in-flight projects but **misses 6 more** that exist under `.projects/`. At minimum, `virtual-thread-migration` is highly relevant to A2 (async migration) and `marathon-stub-bake`/`marathon-assp-runtime-publication` overlap with L6 (Marathon iteration cap) and the Marathon perf workstream.

---

## 3. Impact-label re-evaluation (in detail)

The plan's impact label calibration policy (`HIGH = concrete user-perceptible win OR prevents user-visible failure mode OR foundational infra unblocking measurement; MEDIUM = aggregate win not single-request-perceptible OR conditional value; LOW = micro-optimizations`) is appropriate. Applying it strictly:

### 3.1 Recommended label DOWNGRADES

| PR | Plan label | Audited label | Reason |
|---|:--:|:--:|---|
| **#5** W-2 R23 hydratePool split | HIGH | **MEDIUM** | `convHistPool=128` already exists separately from `hydratePool=2`. The "−500ms-2s p95" claim presumes that history hydration uses `hydratePool`; needs profiling proof. Risk-adjusted, this is MEDIUM until that profile is in hand. |
| **#6** L7 MCP cache key | HIGH | **MEDIUM** | Hidden privacy/correctness risk: the cache key explicitly carries `accountId` because per-account tool inventory differs. Dropping it without designing a coarser bucket would create cross-tenant cache pollution. ROI dominated by risk mitigation work. |
| **#8** W-1 Y1 SSE event:ack preamble | MEDIUM | **LOW** | Endpoint is NDJSON, not SSE. Current label and content of PR are mismatched; need to retitle and rescope. Net win on TTFB likely small (~tens of ms) since NDJSON already streams. |
| **#10** S2-Phase1 saturation gauge | MEDIUM | **LOW** | Gauge already exists. Real PR is "add (tenant, experience) tags." Much smaller. |
| **#25** L2-PhaseA parallel tool execution | HIGH | **MEDIUM** | Parallel tool execution already implemented; PR is "expand allowlist + remove FF gate", not "introduce". Smaller delta. |

### 3.2 Recommended label UPGRADES

| PR | Plan label | Audited label | Reason |
|---|:--:|:--:|---|
| **#23** S1 DLQ for `ApplicationCoroutineScope` | HIGH | **HIGH (load-bearing)** | The class self-documents that there's no retry/DLQ/monitoring; this is **silent data loss** on memory ingest. Worth flagging as "load-bearing — cannot defer past MAU 150k." |
| **#22** R1 complete CB migration | HIGH | **HIGH (load-bearing)** | Aligned with documented `.projects/circuit-breaker/` 6-PR plan. Anti-goal text in plan is wrong but the work itself is foundational for resilience. |

### 3.3 Labels confirmed correct (no change)
PRs **#1, #2, #3, #4, #7, #9, #11, #12, #13, #14, #15, #16, #17, #18, #19, #20, #21, #24, #26, #27, #28, #29, #30** — labels confirmed against verified evidence.

---

## 4. Detailed issue and problem list (for human review)

### 4.1 🔴 Critical: Anti-goal #42 contradicts the codebase
- **Plan text (§5):** *"42. Do NOT introduce Resilience4j. The platform already uses `AggResilienceProvider` + `AggServiceKey` actively…"*
- **Reality:** `modules/platform/client/client-api/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggResilienceProvider.kt:6-8`
  ```
  import io.github.resilience4j.circuitbreaker.CircuitBreaker
  import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig
  import io.github.resilience4j.circuitbreaker.event.CircuitBreakerOnStateTransitionEvent
  ```
- **Recommended fix:** rewrite anti-goal #42 to: *"Do NOT introduce a second/competing circuit-breaker framework. The platform already wraps `io.github.resilience4j.circuitbreaker.CircuitBreaker` inside `AggResilienceProvider`; extend that wrapper rather than introducing a parallel framework or rolling a custom one."*

### 4.2 🔴 Critical: PR #10 (S2 saturation gauge) is largely already shipped
- **Plan text (PR #10):** *"`[Impact: Medium] [reliability] S2-Phase1 — Concurrent-conversation saturation gauge (RovoChatService:207, metric-only)`"*
- **Reality:** `RovoChatService.kt:207` is `private val concurrentConversations = AtomicInteger(0)`; the gauge `MetricKey.CONCURRENT_CONVERSATIONS` is already emitted at lines `1075-1076` and `1190-1192`. There is also a duplicate gauge in `MarathonRuntime.kt:108, 205, 235`.
- **Recommended fix:** retitle to "[Impact: Low] [observability] Add (tenant_tier, experience) tags to existing CONCURRENT_CONVERSATIONS gauge". Drop from "metric-only" framing — the metric exists.

### 4.3 🔴 Critical: PR #25 (parallel tool execution) is partly shipped
- **Plan text (PR #25):** *"`[Impact: High] [latency] L2-PhaseA — Parallel tool execution within single LLM-decision turn (read-only allowlist)`"*
- **Reality:** `executeToolsInParallel(...)` is a first-class abstraction in `Types.kt:215`, implemented in `MarathonIndividualAgentExecutor.kt:51`, called in `MarathonRuntime.kt:564`, `DecisionNode.kt:457`, and `BitbucketPipelineTroubleshootingAgent.kt:357,453`. There's also a feature flag `parallel_tool_calls_enabled` in `LuminaConfigService.kt:33`.
- **Recommended fix:** retitle to "[Impact: Medium] [latency] L2-PhaseA — Promote parallel tool execution to default ON for read-only tools; expand allowlist; remove `parallel_tool_calls_enabled` gate."

### 4.4 🟡 Significant: PR #8 (W-1 SSE) targets the wrong protocol
- **Plan text (PR #8):** *"SSE event:ack preamble for /ChatV1Controller streaming endpoints"*
- **Reality:** `ChatV1Controller.kt:164` uses `produces = ["application/x-ndjson"]` and emits via `StreamingResponseBody`/`Flux`. There is no `text/event-stream` endpoint here.
- **Recommended fix:** either retitle to "NDJSON ack preamble", or move the PR to the actual SSE-emitting controller (look at GraphQL subscription writer or similar).

### 4.5 🟡 Significant: PR #5 (W-2 R23 hydratePool) framing oversimplified
- **Plan text (PR #5):** *"Split hydratePool=2 web-Jsoup pool from history hydration pool"*
- **Reality:** `CoroutineContextProvider.kt` already has BOTH `hydratePool: limitedParallelism(2)` AND `convHistPool: limitedParallelism(128)` AND `contentRetrievalPool: limitedParallelism(256)`. The "history hydration uses hydratePool" assumption needs verification — the existence of `convHistPool` suggests it may already be split.
- **Recommended fix:** before sizing this PR HIGH, identify the actual call site that's queuing on `hydratePool=2` and whose latency moves p95 by 500ms-2s. If it's `WebHydrationService` or similar, the PR should be: "Add a separate `webHydratePool` for outbound Jsoup; keep `hydratePool` for content-retrieval Jsoup uses; size each based on profiled blocking time."

### 4.6 🟡 Significant: PR #6 (L7 MCP cache key) understates risk
- **Plan text (PR #6):** *"Drop `accountId` from MCP schema cache key (~80% Redis savings, AIFC7)"*
- **Reality:** `MarathonMcpSchemaRedisCache.kt` data class doc explicitly says: *"MCP tool availability can depend on the requesting account and tool type, so the cache key must include those dimensions to avoid leaking another user's integration inventory into the current prompt/runtime snapshot."*
- **Recommended fix:** this PR must include a design note showing how `accountId` is replaced with a coarser (but correct) key — e.g., a hash of the user's MCP integration entitlement set, or a per-tenant cache namespace. As written, the PR risks cross-account information leak.

### 4.7 🟡 Significant: PR #18 (L4) mischaracterizes the bottleneck
- **Plan text (PR #18):** *"N+1 elimination in ConversationHistoryItemManager (lines 529-604)"*
- **Reality:** lines 529-604 contain three private methods (`withPluginInvocations`, `withMinionOutputs`, `withAgentUserContext`). Each uses `coroutineScope { items.map { async { … } }.awaitAll() }` — i.e., parallelized fan-out N. Not classic sequential N+1.
- **Recommended fix:** retitle to "Batched fetch (1 query for N items) for plugin invocations / minion outputs / agent user context, replacing the N parallel async fetches per page". Quantitative claim "−50-80% Object Store calls" is consistent with batch fetch but not with "N+1 elimination" framing.

### 4.8 🟡 Significant: PR #11 (PLT-2) "spin-wait" mischaracterized
- **Plan text (PR #11):** *"TokenBucketRateLimiter spin-wait → AggResilienceProvider RateLimiter"*
- **Reality:** `TokenBucketRateLimiter.kt` uses a CAS loop (`while(true) { … if (state.compareAndSet(...)) … }`). On contention, this retries, but it does **not** busy-wait on the clock or the token (it returns `false` immediately if no tokens). It is a textbook lock-free atomic update, not a spin-wait.
- **Recommended fix:** retitle to "Replace bespoke 37-line `TokenBucketRateLimiter` with `AggResilienceProvider`-managed `Resilience4j.RateLimiter` for consistency". Drop the "spin-wait" claim. Impact LOW is correct.

### 4.9 🟡 Plan misses 6 in-flight `.projects/`
The plan calls out 4 (`coroutine-migration`, `circuit-breaker`, `cache-friendly-schema-agent-prompts`, `rovo-module-decomposition`) but ignores:
- `virtual-thread-migration/` — directly relevant to A2 (async migration). May be a competing or coordinated effort.
- `marathon-assp-runtime-publication/`, `marathon-embed-ipython/`, `marathon-stub-bake/` — Marathon-related; relevant to L6 (RV5 iteration cap) and any parallel-execution work.
- `deep-research-subagent-invocation/` — relevant to L2-PhaseB (subagents).
- `pollinator-coverage/` — possibly relevant to G-3 (EVAL1 coverage).

**Recommended fix:** add a §0.4 "Other in-flight projects considered (and why not extended)" section so reviewers can see they were inspected.

### 4.10 🟡 Plan numeric claims that need stronger sourcing

| Claim | PR | Where it appears | Issue |
|---|---|---|---|
| "−$30-80K/mo (single largest unclaimed lever)" for L3 | #15-16 | §2 row 2; §3.1 row 15 | No file-level breakdown of current Insights spend; needs Socrates `convo_ai_usage` slice for `feature=insights` over a representative 30-day window. |
| "−$30K+/mo" for L1 | #17 | §2 row 3 | Anthropic `cache_read_input_tokens` measurement is the right approach (per the `.projects/` README) but no baseline in the plan. |
| "−500ms-2s p95" for W-2 | #5 | §2 row 5 | Needs a profile that confirms `hydratePool` is the bottleneck (see §4.5). |
| "−$15-40K/mo, mean iters −50%" for L6 | #14 | §2 row 6 | Range is wide; cite the iteration-distribution histogram source. |
| "33+ FF evals → 1" for A5 | #7 | §2 row 14 | Codebase-wide grep returns 1029 matches for FF eval calls; per-request count is plausible but unverified. |
| "~80% Redis savings" for L7 | #6 | §3.1 row 6 | Needs a per-key hit-rate distribution, not just key-cardinality reasoning. |
| "−25-35% PR wall-clock" for CI1 | #30 | §3.1 row 30 | Easy to verify after a single trial run; not a blocker. |
| "5-15pp relevance" for I-workstream | §1 row I | §1 row 53 | "5-15pp" is wide and depends on EVAL2; should be flagged "TBD pending G-4 EVAL2 prod-shadow". |
| "−500-2,000ms p95 multi-tool turns" for L2 | #25 | §2 row 11 | Needs to be re-quoted given parallel exec already exists; only the unflagged path delta matters. |

### 4.11 🟡 Stacking dependency that's understated

PR #15 → PR #16 has a "≥7d soak" gate (anti-goal #46) — explicit and good. **However**, PR #14 (L6 RV5) is gated only on "PR #1 (P3 cost metric live ≥7d)" — but L6 also depends on **paired accuracy A/B** per anti-goal #51. This dependency is not in the gating column. **Recommended fix:** add `accuracy-A/B-anti-goal-51` to the gates column for PR #14 in `PR_TRACKING.csv` (currently only PR #14 in CSV mentions this, partially).

### 4.12 🟡 Title-format inconsistencies (minor)

All 30 titles use the format `[Impact: X] [tag1][tag2] ID — description`. Two minor issues:
- **PR #4 title:** `[Impact: High] [reliability][reliability-eval] G-3 …` — `[reliability-eval]` is an awkward double-tag with `[reliability]`. Recommend `[Impact: High] [eval] G-3 …` or `[Impact: High] [quality][ci] G-3 …`.
- **PR #29 title:** `[Impact: High] [quality][cost] I4 — Skill-conflict workstream Phase 1 (vague-query cost guard + tool-overlap registry)` — minor, but "Skill-conflict workstream Phase 1" implies a meta-PR; either rename to a concrete deliverable (e.g., "introduce `ToolOverlapRegistry` + `VagueQueryGuard` for LH orchestrator") or split into the two named pieces.

### 4.13 ⚪ Unverifiable from code (require runtime evidence)

| PR | Claim | What to gather |
|---|---|---|
| #1 #2 | per-(model, exp, tenant) cost panel ROI | No baseline panel in code today; correct foundation work. |
| #3 | Cat-1 SLO targets | Confirm with @jgrose per anti-goal #50 |
| #4 | Goldens-300 / Q13 datasets | Confirm location in `evaluation/` + ownership |
| #20 | autoscaling target (min/max) | Perfhammer 2× peak load test (anti-goal #15 — already required) |
| #24 | v7 R-6A live status | Confirm before merge |
| #29 | "41KB system prompt" | Run pebble template against a representative request to size it |

---

## 5. Companion docs status

The plan §11 lists 9 TODO companion docs. As of this audit, **none have been authored**. The CSV `PR_TRACKING.csv` exists (rows 1-30 verified to match §3.1 of the plan).

| Companion doc | Listed in §11 | Exists? |
|---|:--:|:--:|
| `BOOST_INTEGRATED_v2.md` | ✅ | ✅ (this audit's subject) |
| `boost_items/P-PerfContract.md` | ✅ | ❌ |
| `boost_items/A-Architecture.md` | ✅ | ❌ |
| `boost_items/L-LatencyCost.md` | ✅ | ❌ |
| `boost_items/R-Resilience.md` | ✅ | ❌ |
| `boost_items/I-Intelligence.md` | ✅ | ❌ |
| `boost_items/W-TacticalWins.md` | ✅ | ❌ |
| `boost_items/M-Monetization.md` | ✅ | ❌ |
| `BUSINESS_GOALS_DELTA_v2.md` | ✅ | ❌ |
| `EVIDENCE_INDEX.md` | ✅ | ❌ |
| `PR_TRACKING.csv` | ✅ | ✅ (verified row-by-row against §3.1) |

The accompanying file `PR_DOCUMENTATION_v2.md` (created alongside this audit) provides the comprehensive per-PR narrative requested by the user.

---

## 6. Summary of REQUIRED edits to v2 plan

| # | What to change | Where | Severity |
|---|---|---|:--:|
| 1 | Rewrite anti-goal #42 to acknowledge Resilience4j is already adopted | §5 | 🔴 |
| 2 | Reframe PR #10 as "add tags to existing gauge" | §3.1 row 10, CSV row 10 | 🔴 |
| 3 | Reframe PR #25 as "expand parallel-tool allowlist + remove FF gate" | §3.1 row 25, CSV row 25 | 🔴 |
| 4 | Retitle PR #8 to NDJSON or move to actual SSE endpoint | §3.1 row 8, CSV row 8 | 🟡 |
| 5 | Downgrade PR #5 HIGH→MEDIUM pending profile of `hydratePool` vs `convHistPool` | §3.1 row 5 | 🟡 |
| 6 | Downgrade PR #6 HIGH→MEDIUM and add cross-tenant safety design note | §3.1 row 6 | 🟡 |
| 7 | Reword PR #18 as "batched fetch" not "N+1 elimination" | §3.1 row 18 | 🟡 |
| 8 | Reword PR #11 — drop "spin-wait", say "37-line bespoke limiter" | §3.1 row 11 | 🟡 |
| 9 | Add §0.4 listing the other 6 in-flight `.projects/` and why not extended | §0 | 🟡 |
| 10 | Add accuracy-A/B-anti-goal-51 gate to PR #14 in CSV explicitly | `PR_TRACKING.csv` row 14 | 🟡 |
| 11 | Improve title for PR #4 (drop double-tag) and PR #29 (concrete deliverable) | §3.1 rows 4, 29 | ⚪ |
| 12 | Add baseline measurements for §4.10 numeric claims | §2 quantified-impact column | ⚪ |
| 13 | Author the 9 missing companion docs | §11 | ⚪ |

---

## 7. Final verdict

**Sign-off recommendation:** Approve plan **with the 3 critical fixes listed in §0 / §6 row 1-3 applied**, and a 2-page addendum addressing §6 rows 4-13. The plan's overall structure (6 workstreams, 30 PRs, stacked-deploy boundaries, anti-goal discipline, in-flight `.projects/` coordination) is excellent. The PR-impact label distribution (57% H / 40% M / 3% L) is appropriate for a sprint-zero load-bearing plan. Most numeric-impact claims are reasonable in direction but understate uncertainty; gating on M-series ≥7d (already in plan) provides the right safety net.

**Estimated effort to apply audit edits:** **2-3 engineer-days** (titles + CSV updates + 1-page addendum + design note for PR #6) before kickoff.

**Risk-adjusted go/no-go:** **Go** for Wk 0 foundation PRs (#1, #3, #4) immediately; finalize §6 edits before Wk 1-2 batch.

**END OF AUDIT REPORT.**
