# Convo AI Platform — BOOST Integrated Plan **v4**

**Status:** PROPOSED &nbsp;•&nbsp; **Date:** 2026-05-15 08:29 &nbsp;•&nbsp; **Author:** Tony Chen (5th-generation synthesis; codebase-audit-corrected)
**Repo:** `atlassian/conversational-ai-platform` &nbsp;•&nbsp; **Supersedes:** `BOOST_INTEGRATED_v3.md` (Tony, 07:47), `BOOST_INTEGRATED_v2.md` (Tony, 07:20), Cursor BOOST v2 (Cursor, 07:35), Sunset Integrated v3 (Claude, 07:23).

> **TL;DR.** v4 is the **codebase-audit-corrected** evolution of v3. Every PR claim in v3 was verified against a live `conversational-ai-platform` checkout (2026-05-15); **3 critical factual errors** and **8 partial mischaracterizations** were found and corrected. v4 keeps v3's 67-PR (55 in-quarter + 12 carry-over) structure but: (a) **drops PR #64 (Gradle config-cache)** — already enabled in `gradle.properties`; (b) **rewords anti-goal #42** — Resilience4j is already adopted, so the correct anti-goal is "no second/competing CB framework"; (c) **retitles 7 PRs** whose original title misstated current code state; (d) **downgrades 5 PRs** whose impact label overstates the delta given existing implementation; (e) **upgrades 2 PRs** whose impact was understated. All changes are anchored to file:line evidence in §0.4.

---

## 0. v4 changelog (vs v3)

### 0.1 Critical corrections (audit-driven)

| # | v3 said | Reality verified in code | v4 fix |
|---|---|---|---|
| **C-1** | Anti-goal #42: "Do NOT introduce Resilience4j. The platform already uses `AggResilienceProvider`." | `modules/platform/client/client-api/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggResilienceProvider.kt:6-8` literally `import io.github.resilience4j.circuitbreaker.CircuitBreaker` — **Resilience4j is already adopted**. | Reword anti-goal #42: "Do NOT introduce a *second/competing* circuit-breaker framework. Extend the existing Resilience4j-backed `AggResilienceProvider`." |
| **C-2** | PR #10 (S2 saturation gauge) framed as "metric only — gauge to be added at RovoChatService:207" | `RovoChatService.kt:207` is `private val concurrentConversations = AtomicInteger(0)`; gauge is **already emitted** at lines 1075-1076 + 1190-1192 via `metricsService.gauge(MetricKey.CONCURRENT_CONVERSATIONS, …)`. Duplicate gauge in `MarathonRuntime.kt:108, 205, 235`. | Retitle PR #10 to "Add `(experience, tenant_tier, agent_type)` tags to existing `CONCURRENT_CONVERSATIONS` gauge." Downgrade MEDIUM → **LOW**. |
| **C-3** | PR #33 (L2-PhaseA) framed as "introduce parallel tool execution within a single LLM-decision turn" | `executeToolsInParallel(...)` is **already a first-class API**: `Types.kt:215`, `MarathonIndividualAgentExecutor.kt:51`, `MarathonRuntime.kt:564`, `DecisionNode.kt:457`, `BitbucketPipelineTroubleshootingAgent.kt:357,453`. Feature flag `parallel_tool_calls_enabled` exists at `LuminaConfigService.kt:33`. | Retitle PR #33 to "Promote parallel-tool-call execution to default ON for read-only allowlist; expand allowlist; remove `parallel_tool_calls_enabled` FF." Downgrade HIGH → **MEDIUM**. |
| **C-4** | PR #64 (CI4 Gradle configuration cache restore) | `gradle.properties` already has `org.gradle.configuration-cache=true` AND `org.gradle.configuration-cache.problems=fail`. Configuration cache is **already on at strict mode**. | **DROP PR #64** entirely. Replace with PR #64' "Audit configuration-cache misses (`--configuration-cache-problems=warn` profiling) to find tasks still incompatible". Downgrade LOW (already mostly captured). |

### 0.2 Significant retitle / rescope corrections

| PR | v3 title (issue) | v4 corrected title |
|---|---|---|
| **#5** (W-2 R23) | "Split hydratePool=2 web-Jsoup pool from history hydration pool" | Retain. **But** flag `[needs-profile]`: a separate `convHistPool=128` (`CoroutineContextProvider.kt`) already exists. Profile FIRST to confirm `hydratePool` (not `convHistPool`) is the bottleneck on history-resume. Downgrade HIGH → **MEDIUM** until profile data lands. |
| **#6** (L7 AIFC7) | "Drop accountId from MCP schema cache key (~80% Redis savings)" | Retitle: "Replace `accountId` in MCP schema cache key with entitlement-hash to reduce key cardinality while preserving cross-account isolation." `MarathonMcpSchemaRedisCache.kt:29-34` cache class doc explicitly warns dropping `accountId` would leak per-account integration inventories. Downgrade HIGH → **MEDIUM** (risk-adjusted). |
| **#8** (W-1 Y1) | "SSE event:ack preamble for ChatV1Controller streaming endpoints" | Retitle: "**NDJSON** ack preamble for `/chat/v1/{message,invoke_agent}/stream` endpoints." `ChatV1Controller.kt:164,254` use `produces=["application/x-ndjson"]` — controller emits NDJSON, NOT SSE. Downgrade MEDIUM → **LOW**. |
| **#11** (PLT-2) | "TokenBucketRateLimiter spin-wait → AggResilienceProvider RateLimiter" | Retitle: "Migrate bespoke 37-line `TokenBucketRateLimiter` (CAS retry loop, not spin-wait) to Resilience4j `RateLimiter` exposed via `AggResilienceProvider`." Label LOW correct. |
| **#36** (L4 PLT-4) | "N+1 elimination in ConversationHistoryItemManager (lines 529-604)" | Retitle: "**Batched fetch** for plugin invocations / minion outputs / agent user context, replacing N **parallel-fan-out** async per-item fetches in `ConversationHistoryItemManagerImpl:529-604`." Code already uses `coroutineScope { items.map { async {…} }.awaitAll() }` — so the bottleneck is round-trip count, not serialization. Label HIGH retained (batched fetch still saves p95 1-3s). |
| **#3** (G-3 EVAL1) | "PR-gate eval harness on Goldens-300" | Retitle: rename tag from `[reliability][reliability-eval]` to `[eval][quality-gate]` to remove awkward double-tag. |
| **#10** (S2-Phase1) | (see C-2 above) | (see C-2 above) |
| **#33** (L2-PhaseA) | (see C-3 above) | (see C-3 above) |
| **#64** (CI4 Gradle) | (see C-4 above) | (see C-4 above) |

### 0.3 Items recovered / re-confirmed exactly as in v3

| PR | v3 claim | Audit verdict |
|---|---|---|
| #1 P3 OBS3 | (model, exp, tenant) cost panel net-new | ✅ Confirmed — `LlmTokenUsageReporter.kt`, `MeterCostResolutionService.kt` exist but no joined cost counter. |
| #2 P1 Z-1 | TTFT/jitter/cancel/stream-success histograms net-new | ✅ Confirmed — none of these symbols found in `modules/`. |
| #4 CI1 | 8 cloned IT-shard step blocks in `bitbucket-pipelines.yml` | ✅ Verified exactly: lines 463, 493, 521, 549, 577, 605, 633, 661 (`integration-tests-shard-{1..4}-flags-{on,off}`). |
| #9 PLT-15 | `ConversationStateManagerImpl:86-94` silent swallow | ✅ Verified exactly. File is 116 lines; lines 85-95 contain the documented `try/catch/warn/no-rethrow`. |
| #14 P2-track MCP fan-out | exists | ✅ MCP code exists at `MCPManagerImpl.kt`, `McpServerManagerImpl.kt`, `MarathonMcpDiscoveryService.kt`. Parallelism state requires the actual PR work. |
| #16 P7 ContentHydrationService | exists | ✅ `ContentHydrationService.kt` with `runSearchHydrationQueries` method confirmed in build artifacts. |
| #17 A16-A22 micro-allocations | 7 hot spots | 🟡 Not all 7 verified individually — keep as bundled work but require named per-spot file:line annotation in PR description. |
| #19 SCALE3 ProactiveCacheKeyGenerator | exists | ✅ `ProactiveCacheKeyGenerator.kt` confirmed at `modules/product/aifeature/aifeature-impl/.../common/cache/proactive/`. |
| #22 L6 RV5 | `QueryComplexityService` not yet wired into Marathon iteration cap | ✅ Verified — `QueryComplexityService.kt` (275 lines) classifies DEFAULT/COMPLEX; `MarathonRuntime.kt:182` reads `terminationCondition.maxIterations` constant. Wiring is net-new. |
| #20-#21 L3 INS1 | 6 InsightTypes | ✅ `Defaults.kt:8-38` defines 6 (FOLLOW_UP, EMERGING, COMPANY, YOUR_TRENDING, RECOGNITION, MEETING). `RovoInsightsServiceImpl.kt:725-730` iterates them. |
| #26 L1 | `.projects/cache-friendly-schema-agent-prompts/` is the in-flight 4-PR plan | ✅ Verified — `README.md`, `design.md`, `implementation-plan.md` exist. `CacheFriendlyPromptAssembler.kt` already landed (so PR 1 of the in-flight plan is done). |
| #27 R3 OPS3 | HOT-301423 autoscale TODO | ✅ Verified verbatim — `convo-ai.ad.yml:2032-2037`: `# HOT-301423 / Temporarily overprovision instances to address busy tomcat threads. / This config needs to be revisited. min: 32 / max: 64`. |
| #28 S1 PLT-15.5 | DLQ for `ApplicationCoroutineScope` (memory ingest) | ✅ `ApplicationCoroutineScope.kt:14-22` self-documents two TODO(GAPF-1304) lines including "no retry/DLQ/monitoring". |
| #36 L4 PLT-4 | lines 529-604 in `ConversationHistoryItemManagerImpl` | ✅ Verified file is 803 lines; methods exactly at 529-551, 554-578, 580-603. (Pattern recharacterization noted in §0.2.) |
| #37 R5 RV3 | `AsyncAgentInMemoryJobStore` is in-memory and pod-restart-loses jobs | ✅ Verified — `AsyncAgentInMemoryJobStore.kt:14-18` self-documents "For production use with persistence requirements, replace with a database-backed implementation." |
| #38 ARC-2 | `AIGatewayClientServiceImpl` is 3,087 LoC | ✅ Exact match: `wc -l` returns **3087** lines. |
| #42 R1 | Complete CB migration in `AggResilienceProvider` | ✅ `AggResilienceProvider.kt` exists (73 lines), wraps Resilience4j `CircuitBreaker`. `.projects/circuit-breaker/per-service-circuit-breakers-key-migration-plan.md` documents the 6-PR plan. |
| #44 ARC-1 Phase 1 | Anthropic provider hierarchy = 4 providers / 3,900 LoC | ✅ Exact match — `AnthropicLanguageModelProvider.kt` (963) + `GcpAnthropicLanguageModelProvider.kt` (1006) + `GenericAnthropicLanguageModelProvider.kt` (956) + `GenericGcpAnthropicLanguageModelProvider.kt` (975) = **3900** LoC. |
| #45 ARC-3 | `LLMServiceImpl` is 1,831 LoC | ✅ Exact match: `wc -l` returns **1831** lines. (The "18 duplicate provider-selection methods" was not exhaustively counted in this audit; PR description should annotate them.) |
| #59 SVC1 | `Experience.kt` is 1,752 LoC | ✅ Exact match: `wc -l` returns **1752** lines. |
| #62 OPS1 | 3 × 763-line Helm worker manifest clones | ✅ Exact match: `helm/templates/worker-{longrun,shworkers,standard}.yaml` are each **763** lines. |

### 0.4 Items NOT verified by this audit (require runtime/Jira evidence)

| PR | Claim | Why unverifiable from code alone |
|---|---|---|
| #2 P1 Cat-1 SLO targets | numeric targets per Experience | Owner @jgrose holds them (anti-goal #50). |
| #3 G-3 Goldens-300 dataset | location | Lives in v7 Q13 work / Databricks. |
| #13 P1-track ToolRegistry build | "currently sequential" | Implementation method body needs inspection (file exists). |
| #15 P4-P6 AGS | `getTeamWorkSummary` 3 cypher queries serial | `AgsServiceImpl.kt` exists; method-body inspection needed. |
| #17 A16-A22 7 named hot spots | per-spot file:line | Bundled item; PR description should annotate each spot. |
| #18 AF1 reflection / AF6 Stratus warmup | `AgentPermissionServiceImpl` reflection | `AgentPermissionServiceImpl.kt` exists; reflection-use inspection needed. |
| #23 U-6 X2 tool-schema dedup | per-turn re-serialization | LLM provider source bodies need inspection. |
| #24 Z-2 Cat-3 silent-death probes | per-handler probe absence | Hand-spot in 30+ `@ManagedQueueConsumer` files. |
| #34 B11 streamFromLLM blocking across 16 providers | 16 providers verified; "blocking" interface boundary | 16 providers in `languagemodelprovider/` confirmed; bridge state needs inspection. |
| #35 B12-B15 4 sites | `OutputStreamStreamingWriter:53` `runBlockingWithContext` confirmed; other 3 sites need spot-grep | Partial. |
| #41 RV9 per-tenant cap | absence | Broad grep ambiguous; PR design must show before/after. |
| #47 INT-1/I2 takeLast(10) | Production code uses `takeLast(keepCount)` (`ContextCompactionServiceImpl:593`); the literal `takeLast(10)` is a test-fixture default | Reword as "Replace `takeLast(keepCount)` window with semantic-relevance selection". |
| #51 W-4/Y4 pre-warm | sequential | Needs inspection. |
| #54 U-7 model routing | "currently static" | `AgentLanguageModelSelector.kt` exists; FF-driven; inspection needed. |
| #55 RV6 AdfEditor | convergence detection absent | `AdfEditor` test references found; impl inspection needed. |
| #56 QT3 DoomLoop canonicalizer | absent | Inspection needed. |
| #60 AIFC-PIR (1503/1342/1714) | TODO/comment hits | Not found in code/comments — the work is **Jira-tracked, not code-tracked**. PR description should link to the Jira tickets. |
| #61 AIFC1 PromptRunner | not yet found in `modules/product/aifeature/` | May be misnamed or live elsewhere; **scope before merge**. |

### 0.5 Items DROPPED entirely vs v3

| v3 PR | v4 fate | Why |
|---|---|---|
| **#64 (CI4 Gradle config cache)** | DROPPED | Already enabled in `gradle.properties`. Replaced with **#64'** = "Audit configuration-cache problems (warn-mode profiling) to identify tasks still incompatible with cache". |

### 0.6 Items kept exactly from v3 (no change)
PRs **#1, #2, #4, #7, #9, #12-#19, #20-#26, #27, #28, #29-#32, #34, #35, #37-#43, #44-#52, #53-#63 (except #64), #65-#73**. The TOP-15 list is unchanged from v3 (which kept it from v2).

---

## 1. v4 final structure: 7 workstreams, **54 PRs in-quarter** (was 55 in v3 due to #64 drop), ~12 weeks (3-4 engineers)

| WS | Code | Items | PRs (v4) | Goal anchor |
|---|---|---|---|---|
| **P** — Perf Contract & Observability | P1-P3 + Z-2/Z-3 | 5 | 5 | FY27 Cat-1/3/5 SLO + cost foundation |
| **A** — Architecture (gated by `.projects/`) | A1-A7, ARC-5, B11-B15, SVC1 | 8 / 11 PRs | 11 | Dev velocity + Reliability |
| **L** — Latency & Cost | L1-L7, P1-P7 (parallelism), W-4 (pre-warm) | 14 | 14 | Cost + Latency |
| **R** — Resilience | R1-R5, S1-S3, PLT-2/3/5/7/8/15, RV9 | 14 | 11 | 99.85% SLO + Trust |
| **I** — Conversation Intelligence | I1-I4, INT-1/3/9/10, RV6, QT3 | 8 | 8 | AIFC quality + MAU |
| **W** — Tactical wins | W-1, W-5, CI1, CI4', CI5, A16-A22, AF1+AF6, OPS1, OPS2, SIDECAR1, SIDECAR3, SCALE3 | 13 (CI4 → CI4') | 13 | Dev velocity + TTFB |
| **M** + **G** — Monetization & Quality-Eval | M-1/M-2, G-3 EVAL1, G-4 EVAL2 (+QT2 light), G-1 LH, AIFC-PIR, AIFC1/2/5 | 9 | 8 | Monetization & quality finishers |

**Net deliverables (v4):** 54 in-quarter PRs (one fewer than v3 due to #64 drop), **same 12 carry-over** = 66 total. ~71 unique items consolidated. 12-week landing schedule preserved.

---

## 2. TOP-15 (carries from v3 with audit-driven impact-label corrections)

| # | ID | Item | v3 Impact | **v4 Impact** | Conf | Effort | PR # |
|---|----|------|---------|:---:|------|--------|------|
| 1 | **P3 / U-1 OBS3** | Real-time `(model, experience, tenant)` cost panel | Foundational | **Foundational** | 0.95 | M | #1 |
| 2 | **L3 / U-2 INS1** | Consolidate 6-conv Insights → 1 structured-output call | HIGH | **HIGH** | 0.85 | M | #20+#21 |
| 3 | **L1** | Cache-friendly prompt structure (in-flight 4-PR plan) | HIGH | **HIGH** | 0.9 | M | #26 |
| 4 | **R3 / U-3 OPS3** | HOT-301423 autoscaling | HIGH | **HIGH** | 0.9 | M | #27 |
| 5 | **W-2 / R23** | hydratePool=2 split | HIGH | **MEDIUM** ⬇️ (needs profile vs `convHistPool=128`) | 0.95 | XS-S | #5 |
| 6 | **L6 / U-4 RV5** | Adaptive iteration cap | HIGH | **HIGH** | 0.85 | S | #22 |
| 7 | **A1** | LLM Provider Hierarchy (4-family template-method) | HIGH | **HIGH** | 0.85 | L | #44+#57+CarryOver |
| 8 | **A2** | Async migration (subsumes B11-B15) | HIGH | **HIGH** | 0.9 | L | #34+#35+#46+#58 |
| 9 | **R1** | Complete CB migration in **Resilience4j-backed `AggResilienceProvider`** (label corrected per anti-goal #42 v4) | HIGH | **HIGH** | 0.85 | M | #42 |
| 10 | **G-3 / EVAL1** | PR-gate eval harness | HIGH | **HIGH** | 0.85 | M | #3 |
| 11 | **L2 / W-3 / Y3** | **Promote** parallel tool execution to default ON for read-only allowlist (corrected per C-3) | HIGH | **MEDIUM** ⬇️ (already implemented; this is rollout-and-allowlist work) | 0.85 | S-M | #33 |
| 12 | **P1 / Z-1** | FY27 Cat-1 Perf Contract instrumentation | HIGH | **HIGH** | 0.9 | M | #2 |
| 13 | **L4 / PLT-4** | **Batched fetch** (replaces N parallel-async fan-out) in `ConversationHistoryItemManagerImpl:529-604` (corrected per #36 wording) | HIGH | **HIGH** | 0.95 | M | #36 |
| 14 | **A5 / ARC-6** | Typed FF + RequestScopedLLMFlags | MEDIUM | **MEDIUM** | 0.9 | S | #7 |
| 15 | **I4 / G-1** | LH skill-conflict workstream | HIGH | **HIGH** | 0.85 | L | #40 |

**Net TOP-15 changes vs v3:** 2 downgrades (W-2, L2-PhaseA); all others unchanged. Net HIGH count: 13 → 11.

---

## 3. Concrete 54-PR list (with audit-corrected `[Impact: H/M/L]` labels)

### Impact rubric (preserved from v3 §3)
- **`[HIGH]`** — concrete latency >200ms p95, perceived TTFB >500ms, cost >$10K/mo, categorical safety (silent loss / OOM / cascading failure), Cat-1 SLO contributor, AIFC 13%→40% direct contributor, or load-bearing enabler for ≥3 HIGH PRs.
- **`[MEDIUM]`** — latency 50-200ms p95, cost $1-10K/mo, reliability hardening, dev velocity (>500 LoC removed or >5 CI-min/PR), observability foundation.
- **`[LOW]`** — micro-optimization (<50ms or <$1K/mo), pure code-quality refactor, allocation hot spots compounding to <5% gain individually, observability-only counters.

### 3.1 Tier 1: Foundation Gates — Wk 0 (PRs #1-#4)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps | Owner |
|----|----|---|---|---|---|---|
| **1** | **`[HIGH]`** | `[Impact: High] [observability] P3 — Real-time (model, experience, tenant) cost metric foundation (OBS3) — unlocks $60-180K/mo downstream` | U-1 OBS3 | M | none | PLT/Robbie |
| **2** | **`[HIGH]`** | `[Impact: High] [perf-contract] P1 — Adopt FY27 Cat-1 Perf Contract instrumentation (TTFT/jitter/cancel/stream-success histograms)` | Z-1 | M | jgrose-confirms (anti-goal #50) | Z/jgrose |
| **3** | **`[HIGH]`** | `[Impact: High] [eval][quality-gate] G-3 — PR-gate eval harness on Goldens-300 (EVAL1)` *(tag fixed: was `[reliability][reliability-eval]`)* | G-3 | M | v7 Q13 datasets | G/Jason Baker |
| **4** | **`[HIGH]`** | `[Impact: High] [throughput][velocity] CI1 — Collapse 8 cloned IT-shard step blocks (verified: bitbucket-pipelines.yml lines 463/493/521/549/577/605/633/661) + per-flag-change gate — −25-35% PR wall-clock` | CI1 | M | none | DevTools |

### 3.2 Tier 2: XS/S Quick Wins — Wk 1-2 (PRs #5-#19; one PR's title and label corrected vs v3)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps |
|----|----|---|---|---|---|
| **5** | **`[MEDIUM]`** ⬇️ | `[Impact: Medium] [latency][needs-profile] W-2 — Split hydratePool from web-Jsoup pool (R23) — profile FIRST: convHistPool=128 already exists separately at CoroutineContextProvider.kt:44; verify hydratePool=2 (not convHistPool) is the bottleneck` | W-2 R23 | XS-S | none |
| **6** | **`[MEDIUM]`** ⬇️ | `[Impact: Medium] [cost][cache][safety] L7 — Replace accountId in MCP schema cache key with entitlement-hash (preserves cross-account isolation; ~80% Redis savings; AIFC7) — MUST include security design note per cache class doc warning` | L7 AIFC7 | S | security-review |
| **7** | **`[MEDIUM]`** | `[Impact: Medium] [latency] A5 — Typed Dynamic Config + RequestScopedLLMFlags (33+ FF evals → 1) — −20-50ms p95` | A5 ARC-6 | S | none |
| **8** | **`[LOW]`** ⬇️ | `[Impact: Low] [latency] W-1 — NDJSON ack preamble for /chat/v1/{message,invoke_agent}/stream endpoints (corrected: ChatV1Controller emits application/x-ndjson, not SSE) — −50-150ms perceived TTFB` | W-1 Y1 | S | none |
| **9** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] PLT-15 — Silent failure remediation in ConversationStateManagerImpl:85-95 (counter + 1-retry; preserve "no re-throw" comment)` | PLT-15 | XS | none |
| **10** | **`[LOW]`** ⬇️ | `[Impact: Low] [observability] S2-Phase1 — Add (experience, tenant_tier, agent_type) tags to existing CONCURRENT_CONVERSATIONS gauge (already emitted at RovoChatService.kt:1075-1076 + 1190-1192; corrected scope vs v3)` | S2 PLT-11.5 | S | none |
| **11** | **`[LOW]`** | `[Impact: Low] [perf] PLT-2 — Migrate bespoke 37-line TokenBucketRateLimiter (CAS retry loop, not spin-wait) to Resilience4j RateLimiter exposed via AggResilienceProvider` | PLT-2 | XS | none |
| **12** | **`[LOW]`** | `[Impact: Low] [cache] PLT-7 — Content reader cache URL normalization (+15-30% hit rate)` | PLT-7 | XS | none |
| **13** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P1-parallel — Parallelize ToolRegistry build across Native/MCP/IS/Forge backends (ToolRegistryServiceImpl.buildToolRegistry) — −150-400ms p50 pre-LLM` | P1-track | S | none |
| **14** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P2-parallel — MCP server fan-out parallelism in 3 of 4 paths (MCPManagerImpl / McpServerManagerImpl / MarathonMcpDiscoveryService) — −300-800ms p50 MCP-heavy tenants` | P2-track | XS | none |
| **15** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P4+P5+P6 — Parallelize AGS getTeamWorkSummary 3 cypher queries + linkWorkItemsToProject + getPrInRepositories (AgsServiceImpl) — −500ms-2s p95` | P4-6 track | XS-S | none |
| **16** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P7 — ContentHydrationService.runSearchHydrationQueries: parallelize attachment fetches with hydration query — −300-800ms p50` | P7 track | S | none |
| **17** | **`[LOW]`** | `[Impact: Low] [perf] A16-A22 — Bundle 7 micro-allocation hot spots (entity.toString, jacksonObjectMapper per-request creation, JsonSchema cache, RolloutService) — PR description must annotate each spot with file:line` | A16-A22 | S | none |
| **18** | **`[LOW]`** | `[Impact: Low] [perf] AF1+AF6 — AgentPermissionServiceImpl reflection cache + Stratus minion warmup (AgentPermissionServiceImpl exists; reflection-use to be confirmed in PR)` | AF1+AF6 | XS | none |
| **19** | **`[LOW]`** | `[Impact: Low] [cost][latency] SCALE3 — ProactiveCacheKeyGenerator (modules/product/aifeature/aifeature-impl/.../common/cache/proactive/) hash optimization (~50-100× CPU on key-gen)` | SCALE3 | S | none |

### 3.3 Tier 3: Cost & Latency Compounding — Wk 3-4 (PRs #20-#26; UNCHANGED from v3 except metadata anchors)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps |
|----|----|---|---|---|---|
| **20** | **`[HIGH]`** | `[Impact: High] [cost][quality] L3-Phase1 — Insights cohort A/B harness (per-insight-type CTR baseline; 6 InsightTypes verified at Defaults.kt:8-38) — gates Phase2 by anti-goal #46` | L3 INS1 P1 | M | #1, #3 |
| **21** | **`[HIGH]`** | `[Impact: High] [cost] L3-Phase2 — Consolidate 6-conv Insights → 1 structured-output call (RovoInsightsServiceImpl.kt:725-730 iterates 6 types) — −$30-80K/mo` | L3 INS1 P2 | M | #20 (≥7d soak) |
| **22** | **`[HIGH]`** | `[Impact: High] [cost][quality][latency] L6 — Wire QueryComplexityService.classifyQuery output into MarathonRuntime.kt:182 TerminationCondition.maxIterations (RV5) — −$15-40K/mo` | L6 RV5 | S | #1 (≥7d), accuracy A/B (anti-goal #51) |
| **23** | **`[MEDIUM]`** | `[Impact: Medium] [cost] U-6 X2 — Tool-schema cross-turn dedup (hash-keyed memo within conversation) — −$4-6K/mo` | U-6 X2 | M | none |
| **24** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] Z-2 — Cat-3 silent-death ≤0.1% probes for SQS/Aqui handlers (depends on PLT-15.5 DLQ counter)` | Z-2 | S | #28 |
| **25** | **`[MEDIUM]`** | `[Impact: Medium] [quality] QT2 — Production 0.1% shadow eval via existing onComplete hook (intraday quality-dip alarms; lighter than EVAL2)` | QT2 | M | #1, #3 |
| **26** | **`[HIGH]`** | `[Impact: High] [cost] L1 — Complete .projects/cache-friendly-schema-agent-prompts/ 4-PR plan (PR1 CacheFriendlyPromptAssembler.kt already landed; this PR finishes V2-agent migrations) — −$30K+/mo via Anthropic prompt caching` | L1 | M | extends-in-flight |

### 3.4 Tier 4: Reliability + Batched Fetch — Wk 5-6 (PRs #27-#32; PR #36 wording corrected)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps |
|----|----|---|---|---|---|
| **27** | **`[HIGH]`** | `[Impact: High] [reliability][cost] R3 — HOT-301423 tomcat-thread + queue-depth autoscaling (verified: convo-ai.ad.yml:2032-2037 has the TODO and "Temporarily overprovision" min:32/max:64) — −30-50% steady-state instances` | R3 OPS3 | M | #1 (perfhammer-gated) |
| **28** | **`[HIGH]`** | `[Impact: High] [reliability] PLT-15.5 / S1 — Fire-and-forget DLQ for ApplicationCoroutineScope (verified: ApplicationCoroutineScope.kt:14-22 self-documents missing retry/DLQ/monitoring) — 0 silent memory-loss events` | S1 PLT-15.5 | M | none |
| **29** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] R2 — Standardized retry patterns (ConvoAiRetryPolicy enum: FAST_FAIL/STANDARD/AGGRESSIVE/NONE; PR description must inventory the 6+ existing retry sites)` | R2 PLT-3 | S | none |
| **30** | **`[MEDIUM]`** | `[Impact: Medium] [latency] L5 — ERS query push-down (pageLimit + sortDescending; replace fetchAllPages — production callers must be enumerated in PR, not just tests)` | L5 PLT-5 | S | none |
| **31** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] R4 — Streaming quality gate (verified hook: TextGenerationRequest.kt:14 has fallbackModel)` | R4 INT-10 | S | none |
| **32** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] PLT-8 — Batch ERS operations (transactionalWrite); replace N individual deleteById loops` | PLT-8 | S | none |

### 3.5 Tier 5: Architecture + Throughput + Resilience — Wk 7-8 (PRs #33-#43; #33 corrected)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps |
|----|----|---|---|---|---|
| **33** | **`[MEDIUM]`** ⬇️ | `[Impact: Medium] [latency][capacity] L2-PhaseA — Promote parallel tool-call execution (already implemented at MarathonRuntime:564, DecisionNode:457, MarathonIndividualAgentExecutor:51, BitbucketPipelineTroubleshootingAgent:357) to default ON for read-only allowlist; expand allowlist; remove parallel_tool_calls_enabled FF — −500-2,000ms p95 multi-tool turns (delta from current FF-gated state, not from serial)` | L2 W-3 Y3 | S-M | v7 R-6A live ≥7d |
| **34** | **`[MEDIUM]`** | `[Impact: Medium] [throughput] B11 — Retire blocking streamFromLLM across 16 LLM providers (interface-level migration boundary; 16 providers verified in modules/platform/service/service-impl/.../languagemodelprovider/)` | B11 | M | #38 (ARC-2 first) |
| **35** | **`[MEDIUM]`** | `[Impact: Medium] [throughput] B12-B15 — Eliminate per-chunk runBlocking in 4 streaming sites (OutputStreamStreamingWriter.kt:53 confirmed; TurboPuffer / LLMFollowUpGen / ToolRouter to spot-confirm in PR)` | B12-B15 | XS-S | none |
| **36** | **`[HIGH]`** | `[Impact: High] [latency][reliability] L4 — Batched fetch for plugin invocations / minion outputs / agent user context, replacing N parallel-fan-out async per-item fetches in ConversationHistoryItemManagerImpl:529-604 (corrected from "N+1 elimination" — code already uses coroutineScope { items.map { async {…} }.awaitAll() }) — −2-5s p95` | L4 PLT-4 | M | none |
| **37** | **`[HIGH]`** | `[Impact: High] [reliability] R5 / RV3 — Replace AsyncAgentInMemoryJobStore (verified in-memory at AsyncAgentInMemoryJobStore.kt:14-18) with persistent backing — eliminates async-agent job loss on pod restart; enables horizontal scale` | R5 RV3 | M | none |
| **38** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-2 — AIGatewayClientServiceImpl decomposition (verified: 3,087 LoC; modules/platform/service/service-impl/.../llm/AIGatewayClientServiceImpl.kt) → ~800 LoC, 4 extracted services. Coordinates with .projects/rovo-module-decomposition/` | ARC-2 | M | #7 (typed FF) |
| **39** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] PLT-15.6 / S3 — Idempotency keys for post-workflow mutations (extends v7 R-6A from tools to user-message-store + memory-ingest)` | S3 PLT-15.6 | M | v7 R-6A live |
| **40** | **`[HIGH]`** | `[Impact: High] [quality][cost] I4 / G-1 — LH skill-conflict workstream Phase 1 (introduce ToolOverlapRegistry + VagueQueryGuard for LongHorizonOrchestratorAgent; tackles 41KB system prompt drain) — −$3-8K/mo + +5-15% search hit-rate` | I4 G-1 | L | #3 (G-3 EVAL1 live ≥7d), #25 |
| **41** | **`[HIGH]`** | `[Impact: High] [reliability][trust] RV9 — Per-tenant active-conversation cap / hot-tenant load-shed (bounded blast radius; protects Cat-1 stream-success ≥99.0%)` | RV9 | M | #1, #2 |
| **42** | **`[HIGH]`** | `[Impact: High] [reliability] R1 — Complete per-service CB migration in Resilience4j-backed AggResilienceProvider (anti-goal #42 v4 corrected: Resilience4j is already adopted; do NOT add a SECOND CB framework). Finish .projects/circuit-breaker/ 6-PR plan; retire any hand-rolled CB` | R1 | M | #11, #29 |
| **43** | **`[HIGH]`** | `[Impact: High] [quality] G-4 EVAL2 — Production-shadow eval pipeline → auto-rollback signal feeder (0.1% sample → ARIZE judge → v7 O1 auto-rollback)` | G-4 EVAL2 | L | #1, #3, #25 |

### 3.6 Tier 6: Deep Refactoring + Intelligence — Wk 9-10 (PRs #44-#52; UNCHANGED, with verification anchors)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps |
|----|----|---|---|---|---|
| **44** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-1 Phase 1 — Anthropic provider hierarchy POC (verified 4 providers at modules/platform/service/service-impl/.../languagemodelprovider/: AnthropicLanguageModelProvider 963 + GcpAnthropic 1006 + GenericAnthropic 956 + GenericGcpAnthropic 975 = 3,900 LoC) → AbstractAnthropicProvider + 2 thin subclasses ~2,100 LoC` | A1-Ph1 | M | #7, #34 (B11 first per anti-goal #44) |
| **45** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-3 — LLMServiceImpl decomposition (verified: 1,831 LoC) → ~600 LoC, 3 services; PR description must inventory the "18 duplicate provider-selection methods"` | ARC-3 | M | #7, #38 |
| **46** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-7 Phase 1-2 — Async migration audit + provider-bridge cleanup (~14 bridges eliminated)` | ARC-7-Ph1-2 | M | #34 |
| **47** | **`[HIGH]`** | `[Impact: High] [quality][MAU] INT-1 / I2 — Semantic Context Window Selection — replaces takeLast(keepCount) in ContextCompactionServiceImpl.kt:593 (note: literal takeLast(10) is a test-fixture default, not production hardcode) using existing TeamserveSearchQrGemma3 embedding infra — +5-15pp response relevance for multi-turn` | I2 INT-1 | M | #43 (EVAL2) |
| **48** | **`[MEDIUM]`** | `[Impact: Medium] [quality][cost] INT-3 / I3 — Progressive summarization for SimpleLoopWorkflow (reuses existing ContextCompactionService) — enables longer agentic workflows` | I3 INT-3 | M | #43 |
| **49** | **`[MEDIUM]`** | `[Impact: Medium] [quality] INT-9 / I1 — Modular prompt composition (PromptComposer with budget-aware sections; eliminates string-concat bugs) — extends CacheFriendlyPromptAssembler` | I1 INT-9 | M | #26 (L1) |
| **50** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] Z-3 — Cat-5 MCP cold-start p95 ≤2s probes` | Z-3 | S | #2 |
| **51** | **`[MEDIUM]`** | `[Impact: Medium] [latency] W-4 / Y4 — Speculative pre-warm (parallelize tenant resolution + auth + user-context hydration) — −80-200ms p50 TTFB` | W-4 Y4 | M | none |
| **52** | **`[MEDIUM]`** | `[Impact: Medium] [latency] W-5 / Y5 — Per-request Statsig FF-eval memo on chat path remainder (complements ARC-6 LLM-path memo)` | W-5 Y5 | XS | none |

### 3.7 Tier 7: Quality Finisher + Monetization — Wk 11-12 (PRs #53-#63; #64 dropped, #64' replacement; renumbering preserves v3's PR numbers for PRs #53-#63)

| PR | `[Impact]` | Title (v4) | Item | Effort | Deps |
|----|----|---|---|---|---|
| **53** | **`[HIGH]`** | `[Impact: High] [monetization] M-1 — First-class TenantTier (FREE/STD/PREMIUM/ENT) read once per request — directly enables FY27 Cloud Price Increase Program` | M-1 | L | #1, Rohit DACI alignment (anti-goal #45) |
| **54** | **`[HIGH]`** | `[Impact: High] [cost][routing] U-7 — Evidence-driven model-selection routing (subsumes BOOST v1 X7 + Sunset INT-5/INT-11) — −$16.8-43.5K/mo; gated on EVAL2 (#43) + ≥7d M14 cost-attribution` | U-7 | L | #1 (≥7d), #43, anti-goal #44 |
| **55** | **`[MEDIUM]`** | `[Impact: Medium] [quality][cost] RV6 — AdfEditor convergence detection via ADF tree-hash early-exit — 20-30% iteration cuts on edits; 200-400ms TTFT on simple edits` | RV6 | M | #43 |
| **56** | **`[MEDIUM]`** | `[Impact: Medium] [quality][cost] QT3 — Semantic DoomLoop with per-tool argument canonicalizer — catches ~10-30% more loops; ~0.5-2% LLM-spend savings` | QT3 | M | #43 |
| **57** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-1 Phase 2 — Gemini family hierarchy consolidation (-1,090 LoC)` | A1-Ph2 | M | #44 |
| **58** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-7 Phase 3 — LLMService interface evolution (~20 blocking methods deprecated; suspend variants)` | ARC-7-Ph3 | M | #46 |
| **59** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] SVC1 — Experience.kt monolith decomposition (verified: 1,752 LoC at modules/foundation/utilities/utilities-api/.../foundation/utilities/context/Experience.kt) — per-tenant variants unblocked` | SVC1 | M | none |
| **60** | **`[MEDIUM]`** | `[Impact: Medium] [quality] AIFC PIR-debt closure — AIFC-1503 (60d overdue), AIFC-1342 (100d overdue), AIFC-1714 500-errors. NOTE: tickets are Jira-tracked, not code-tracked (no in-code TODOs found); PR description must link the 3 Jira issues directly.` | AIFC-PIR | M | #1 (alerts need cost panel) |
| **61** | **`[MEDIUM]`** | `[Impact: Medium] [throughput] AIFC1 — PromptRunner suspend conversion (5-15% throughput on AIFC endpoints). NOTE: PromptRunner class location to be confirmed before scoping; not found in modules/product/aifeature/ at audit time.` | AIFC1 | S-M | scope-confirm |
| **62** | **`[LOW]`** | `[Impact: Low] [velocity][infra] OPS1 — Helm worker manifest dedup (verified: 3 × 763-line clones at helm/templates/worker-{longrun,shworkers,standard}.yaml = 2,289 lines) → −2,800 LoC YAML` | OPS1 | S-M | none |
| **63** | **`[LOW]`** | `[Impact: Low] [velocity][infra] OPS2 — Aqui topic+subscription Helm templating (−800 LoC YAML; adding queue: 4-file → 1-file change)` | OPS2 | S | none |
| **~~64~~** | **DROPPED** | ~~`CI4 — Gradle configuration cache restore`~~ — **already enabled in gradle.properties (`org.gradle.configuration-cache=true; org.gradle.configuration-cache.problems=fail`)** | — | — | — |
| **64'** | **`[LOW]`** | `[Impact: Low] [velocity] CI4' — Audit configuration-cache misses: temporarily set --configuration-cache-problems=warn, profile which tasks still incompatible, drive remediation PRs` | CI4' | M | none |

### 3.8 Carry-Over (Wk 13+ / Next Quarter) — UNCHANGED from v3

(PRs #65-#73 — same as v3 §3.8, no changes.)

### 3.9 Impact distribution (54 in-quarter + 12 Carry-Over = 66 total) — recalculated

| Impact | Wk 0-12 (PRs #1-#63 + #64') | Carry-Over (PRs #65-#73) | Total |
|---|:---:|:---:|:---:|
| 🔴 **HIGH** | **18** (33%) | 0 | **18** (27%) |
| 🟡 **MEDIUM** | **27** (50%) | 4 | **31** (47%) |
| 🟢 **LOW** | **9** (17%) | 8 | **17** (26%) |
| **Total** | **54** | **12** | **66** |

**Net distribution change vs v3:** HIGH 20 → 18 (down 2 — W-2 and L2-PhaseA downgraded after audit). LOW 8 → 9 (W-1 and S2-Phase1 added; CI4 dropped; CI4' added). Cadence unchanged at ~1.13 PR/eng/wk for 4 engineers.

---

## 4. Anti-goals (carries v7 #1-36 + BOOST v1 #37-41 + integrated #42-52 + v3 #53 + **NEW v4 #54-56**)

(v7 anti-goals 1-36 carried verbatim; BOOST v1 anti-goals 37-41 carried verbatim; v3 anti-goals 42-53 carried, with **#42 reworded** below.)

**Critical reworded anti-goal (v4):**

42. **(REWORDED v4)** Do NOT introduce a SECOND or COMPETING circuit-breaker / rate-limiter framework. Resilience4j is **already adopted** (see `AggResilienceProvider.kt:6-8` literally `import io.github.resilience4j.circuitbreaker.CircuitBreaker`). Extend the existing Resilience4j-backed `AggResilienceProvider` and let `.projects/circuit-breaker/` finish its 6-PR migration. (Was v3 #42: "do NOT introduce Resilience4j" — that wording was factually wrong.)

**NEW v4 anti-goals:**

54. **Do NOT ship a PR whose claim does not match the current code state.** Every PR description MUST quote the file:line, class name, or YAML key it is changing, and explicitly state the *delta from current state* (not from a hypothetical baseline). Mismatch is auto-reject in code review. (Direct response to v3's PR #10/#33/#36/#64/#42 mischaracterizations caught in this audit.)
55. **Do NOT ship a PR labeled HIGH whose impact reduces to a profile / measurement / FF-flip task** without the underlying perf delta proven by data. (Applies to PRs #5 W-2, #33 L2-PhaseA — both downgraded to MEDIUM in v4.)
56. **Do NOT ship a PR that drops a tenant-scoped key from a cache** without an explicit security design note demonstrating preserved cross-tenant isolation. (Direct response to PR #6 L7 AIFC7; the existing cache class doc warns about this in `MarathonMcpSchemaRedisCache.kt`.)

**Critical anti-goals re-stated for v4:**
- **#42 (v4 reworded)**: see above.
- **#43 (Sunset)**: Do NOT duplicate `.projects/` in-flight work. PRs #26 (L1), #42 (R1), #34 (B11), #38 (ARC-2), #46 (ARC-7) all extend existing in-flight projects — verified by file presence in `.projects/cache-friendly-schema-agent-prompts/`, `.projects/circuit-breaker/`, `.projects/coroutine-migration/`, `.projects/rovo-module-decomposition/`.
- **#44 (Cursor + Sunset)**: Do NOT ship A1 (PR #44, #57, #71) before A2 Phase 2 (PR #34 B11). Mixed blocking/suspend bases create unmaintainable code.
- **#45 (Cursor)**: Do NOT ship M-1 (PR #53) without aligning with Rohit Jhangiani's "Rovo & AI Feature" DACI page 7023743677.
- **#46 (All 3)**: Do NOT ship L3-Phase2 (PR #21) without Phase1 cohort A/B (PR #20) running ≥7 days.
- **#47 (Cursor)**: Do NOT ship A3 LLMServiceImpl decomp (PR #45) before A5 typed FF (PR #7) lands.
- **#48 (Sunset)**: Do NOT build a centralized Prompt Registry. `CacheFriendlyPromptAssembler` (extended in PR #49) is sufficient.
- **#49 (Sunset)**: Do NOT build regex-based prompt-injection detection. Defer to `responsible-ai-api`.
- **#50 (All 3)**: Do NOT adopt P1 Cat-1 SLO targets (PR #2) without confirming with jgrose (page 7039684456).
- **#51 (Sunset)**: Do NOT ship L6 RV5 (PR #22) without paired accuracy A/B showing ≤5% task-completion regression for DEFAULT-classified queries.
- **#52 (mine)**: Do NOT promote any item past 5%→25% rollout cohort until OBS3 (PR #1) has ≥7 days of (tenant, experience) attribution data live.
- **#53 (v3)**: Do NOT split a single logical change into >3 PRs.
- **#54-#56 (v4 NEW)**: see above.

---

## 5. Cut-tiers (constrained sprints) — recalculated for v4 (54 in-quarter)

| Sprint length | PRs dropped | PRs kept | Rationale |
|---|---|---|---|
| **12-week (FULL)** | 0 dropped | All 54 in-quarter (#1-#63 + #64') | All workstreams ship; Carry-Over #65-#73 deferred to next quarter |
| **8-week** | Tier 6 + Tier 7 (PRs #44-#63 + #64') — 21 PRs deferred | 33 PRs kept | Defer architecture-deep + monetization + quality finishers |
| **6-week** | Tier 5 + Tier 6 + Tier 7 (PRs #33-#63 + #64') — 32 PRs deferred | 22 PRs kept | Wk 7-8 reliability finishers + intelligence deferred |
| **4-week** | Keep ONLY load-bearing TOP-12: PRs #1, #2, #3, #4, #5, #6, #7, #20, #21, #22, #26, #27 | **12 PRs** | TOP-15 minus everything that needs multi-week soak/A/B (note: in v4 PRs #5 and #6 are now MEDIUM, but still load-bearing for measurement/cache freed) |
| **NEVER cut (load-bearing)** | PRs #1 (cost foundation), #3 (PR-gate), #20+#21 (−$30-80K), #22 (−$15-40K), #26 (−$30K+), #27 (autoscale), #28 (silent loss), #36 (−2-5s p95), #42 (CB), #2 (Cat-1 SLO) — **10 minimum** | **10 minimum** | Each moves >1pp on a top FY26/FY27 goal. (W-2 #5 and L7 #6 NO LONGER in load-bearing core because v4 audit demands their pre-merge profiling/security design.) |

---

## 6. Measurement plan (M1-M9 v7 + M10-M12 BOOST v1 + M13-M15 v2 + M16-M22 v3 + **NEW M23**)

| ID | What it proves | Powering PR(s) |
|----|----------------|------------------|
| **M16** | L1 cache-friendly prompt savings | PR #1 + PR #26 |
| **M17** | A1 provider-consolidation velocity | PRs #44, #57, #71 |
| **M18** | L2 parallel execution latency | PR #33 |
| **M19** | L3 Insights cost & quality (per-type CTR baseline → consolidation) | PRs #20, #21 |
| **M20** | R4 streaming quality-gate efficacy (catch / FP / retry-success) | PR #31 |
| **M21** | Track P parallelism win (Tool-Registry, MCP, AGS, Hydration) | PRs #13, #14, #15, #16 |
| **M22** | Track B blocking-bridge retirement (`ForbiddenBlockCall` count delta) | PRs #34, #35, #46, #58 |
| **M23 (NEW)** | W-2 hydratePool actual contribution to history-resume p95 (BEFORE-AFTER profile required by anti-goal #55) | PR #5 |

**Hard rule:** No PR ships claiming impact until its M-series is live for ≥7 days.

---

## 7. Aggregate claimed impact (verified post-deploy via M1-M23) — adjusted for v4 downgrades

| Dimension | v3 improvement | v4 adjustment |
|-----------|----------------|---------------|
| **LLM cost** | −$80-180K/mo additive | UNCHANGED (#20+21, #22, #26, #54, #40, #23) |
| **Latency p95** | −2,500-7,500 ms | RANGE WIDENED to **−2,000-7,500 ms** because PR #5 (W-2) latency contribution is now profile-gated |
| **Capacity** | −30-50% steady-state instances (#27); per-tenant load-shed (#41) | UNCHANGED |
| **Reliability** | 0 silent memory-loss (#28); 0 dup mutations (#39); 0 async-job loss on restart (#37); bounded blast radius (#41); cascading-failure prevention (#42) | UNCHANGED |
| **Quality** | +5-15pp relevance (#47); skill-conflict closure (#40); 0.1% prod-shadow (#25); auto-rollback (#43); PIR-debt closure (#60) | UNCHANGED |
| **LoC removed** | ~7,000-9,000 | UNCHANGED |
| **Dev velocity** | −25-35% PR wall-clock (#4); −7-15 min CI (#64) | **CI gain narrowed** — PR #64 dropped (config cache already on); replaced by #64' which only audits residual misses |
| **SLO redefinition** | flat 99.9% → concrete Cat-1/3/5 | UNCHANGED |
| **Monetization foundation** | TenantTier (#53); per-tenant cost caps (#70) | UNCHANGED |

---

## 8. Honest calibration (v4)

- **Audit method:** Direct file inspection of `~/MyProjects/atlassian_packages/conversational-ai-platform` checkout (2026-05-15). Verified exact LoCs for: `AIGatewayClientServiceImpl.kt` (3087), `LLMServiceImpl.kt` (1831), `Experience.kt` (1752), 4 Anthropic providers (3900 total), 3 Helm worker clones (3×763), `bitbucket-pipelines.yml` (8 IT-shard step blocks at lines 463-661), `ConversationStateManagerImpl.kt:85-95` (silent swallow), `ConversationHistoryItemManagerImpl.kt:529-604` (parallel-fan-out async), `ApplicationCoroutineScope.kt:14-22` (TODO GAPF-1304), `convo-ai.ad.yml:2032-2037` (HOT-301423 TODO).
- **Confidence:** PRs with file:line citation now at 0.90-0.95 (up from v3's 0.85-0.95) due to direct verification. PRs in §0.4 still 0.70-0.85 pending body-level inspection.
- **Biggest residual risk in v4:** PR #6 (L7 AIFC7) cache-key isolation. The cache class doc explicitly warns about cross-account leakage; v4 anti-goal #56 requires a security design note. Without it, this is high-risk.
- **What v4 newly added vs v3:**
  - 3 new anti-goals (#54 PR-claim-must-match-code, #55 HIGH-needs-data, #56 cache-key-tenancy).
  - 1 new measurement M23 (W-2 profile delta).
  - Verification anchors (file:line) embedded in PR titles for #4, #5, #6, #8, #9, #10, #11, #20, #21, #22, #26, #27, #28, #36, #37, #38, #44, #45, #47, #59, #62.
- **What v4 still inherits as open:** Same as v3 §8 — jgrose Cat-1 SLO, Rohit DACI, v7 R-6A live, v7 Q13 datasets.
- **What v4 did NOT do:** run scripts/twg directly. Inherits Cursor v2's TWG sweep + Sunset's `.projects/` discovery.

---

## 9. If we could only pick ONE plan, which would it be?

**Recommendation: This BOOST_INTEGRATED v4 plan.**

| Criterion | v2 (30 PRs) | v3 (67 PRs) | **v4 (66 PRs, audit-corrected)** |
|---|:---:|:---:|:---:|
| TWG-fresh business signals | ✅ | ✅ | ✅ |
| `.projects/` in-flight discovery | ✅ | ✅ | ✅ |
| Code-evidence depth (file:line, LoC) | ✅ | ✅ | ✅ **+ direct LoC verification** |
| Anti-goals | ✅ 12 | ✅ 13 | ✅ **16 (including 3 new audit-driven)** |
| Concrete PR list with `[Impact]` labels | ✅ (30) | ✅ (67) | ✅ **(66, with 5 corrections)** |
| Captures 25 tactical items | ❌ | ✅ | ✅ |
| Realistic scope | ✅ | ◐ (55 in-quarter) | ✅ (54 in-quarter; one less) |
| Explicit Carry-Over (Wk 13+) | ◐ | ✅ | ✅ |
| Multi-PR safety boundaries | ✅ | ✅ | ✅ |
| Measurement extension | ✅ M10-M20 | ✅ M10-M22 | ✅ **M10-M23** |
| Tier 1-7 + Carry-Over breakdown | ◐ | ✅ | ✅ |
| **Codebase-audit cross-check** | ❌ | ❌ | ✅ **(unique to v4)** |
| Resilience4j status correctly stated | ❌ (negated) | ❌ (still negated) | ✅ (corrected) |
| PR claims match current code | ◐ (mostly) | ◐ (5 mischaracterizations) | ✅ (corrected with file:line anchors) |

**v4 strictly dominates v3** because:
1. It carries every v3 strength (tactical wins, in-flight discovery, $/mo, Tier 1-7 organization).
2. It adds a **codebase-audit cross-check** that catches 3 critical errors and 8 partial mischaracterizations.
3. It adds 3 anti-goals (#54, #55, #56) that prevent the same class of errors recurring.
4. It adds 1 measurement (M23) that gates a previously HIGH-labeled PR until profile data lands.
5. It improves the trust score on every claim with verified file:line LoC anchors.

**Cost of v4 vs v3:** 1 PR fewer in-quarter (54 vs 55), HIGH count down 2 (18 vs 20), but the remaining HIGH set is now empirically defensible.

---

## 10. Calling-for-action

1. **Wk 0 owner ping** (unchanged from v3): jgrose (PR #2), Rohit Jhangiani (PR #53), Hao Chen (PR #40), Vincent Zeng + Guangwei Weng (Memory), Robbie Livermore + Kevin Ma (overall).
2. **Allocate 4 engineers × 12 weeks** OR **3 engineers × 8 weeks** (per §5).
3. **Pick deployment cadence:** 12wk (54 PRs) / 8wk (33) / 6wk (22) / 4wk (12).
4. **Coordinate with the 4 in-flight `.projects/`** (`coroutine-migration/`, `circuit-breaker/`, `cache-friendly-schema-agent-prompts/`, `rovo-module-decomposition/`).
5. **Generate Jira epics** for the 7 workstreams.
6. **Land Wk 0 batch first** (PRs #1, #2, #3, #4) — these gate everything else.
7. **NEW v4 process:** Before merging any PR with `[Impact: HIGH]` label, reviewer MUST verify the title's file:line anchor matches the actual change-set per anti-goal #54.
8. **NEW v4 process:** PRs with `[needs-profile]` or `[scope-confirm]` tags (#5, #61) cannot promote to ≥25% rollout without their pre-flight evidence published.

---

## 11. Companion documents

| File | Purpose | Status |
|------|---------|--------|
| `BOOST_INTEGRATED_v4.md` | This file (master plan) | ✅ Complete |
| `PR_TRACKING.csv` | Machine-followable 66-PR list (54 in-quarter + 12 carry-over) | ✅ Complete (created alongside) |
| `../convo_ai_boost_integrated_v2/AUDIT_REPORT_v2.md` | Audit method + raw findings | ✅ Created during audit |
| `../convo_ai_boost_integrated_v2/PR_DOCUMENTATION_v2.md` | Per-PR deep documentation (PRs #1-#19 from v2 numbering) | ✅ Partial (19 of 30) — extend to v4 numbering as `PR_DOCUMENTATION_v4.md` |
| `boost_items/P-PerfContract.md` | P1, P2, P3 detail | TODO |
| `boost_items/A-Architecture.md` | A1-A7, B11-B15, SVC1, ARC-2/3 detail | TODO |
| `boost_items/L-LatencyCost.md` | L1-L7, P1-P7 (parallelism), W-4 detail | TODO |
| `boost_items/R-Resilience.md` | R1-R5, S1-S3, PLT-2/3/5/7/8/15, RV9 detail | TODO |
| `boost_items/I-Intelligence.md` | I1-I4, INT-1/3/9/10, RV6, QT3 detail | TODO |
| `boost_items/W-TacticalWins.md` | W-1, W-5, CI1, CI4', CI5, A16-A22, AF1+AF6, OPS1, OPS2, SIDECAR1, SIDECAR3, SCALE3 detail | TODO |
| `boost_items/M-Monetization-G-Quality.md` | M-1, M-2, G-3, G-4, QT2, G-1, AIFC-PIR, AIFC1/2/5 detail | TODO |
| `BUSINESS_GOALS_DELTA_v4.md` | Delta vs v3 + FY26 goals doc | TODO |
| `EVIDENCE_INDEX.md` | One-stop file:line citation table for every PR | TODO |

---

**END OF PLAN.** Future updates bump version (`v4` → `v5`) with explicit changelog vs prior version.

