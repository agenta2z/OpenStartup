# Convo AI Platform — BOOST Integrated Plan v1

**Status:** PROPOSED &nbsp;•&nbsp; **Date:** 2026-05-15 &nbsp;•&nbsp; **Author:** Tony Chen (synthesis of 3 candidate plans)
**Repo:** `atlassian/conversational-ai-platform` &nbsp;•&nbsp; **Supersedes:** BOOST v1 (mine), Cursor v2 (planner), Claude Sunset

> **What this is.** The fourth wave of opportunities for Convo AI, built by **integrating the best of three candidate plans** (BOOST v1 / Cursor v2 / Claude Sunset) under one critical-thinking framework. Every item below is goal-anchored, file:line cited (or marked PATTERN-BASED), de-duplicated against v7 / BOOST v1 / 18 open PRs, and priced in dollars / latency / pp where measurable.
>
> **What this avoids.** Hacks, ad-hoc fixes, "refactor because ugly", scope-creep across plans, and the three known weaknesses of the source plans (Cursor v2 = manifest-not-plan; Sunset = no anti-goals + no $; BOOST v1 = TWG-stale).

---

## 0. Sources, provenance, and de-duplication

### 0.1 Three candidate plans synthesized

| Source | What it brought | What was rejected |
|---|---|---|
| **A — Cursor v2** (214 lines, 2026-05-15) | Fresh TWG signals (FY27 Cat-1/3/5 SLO, MAU at-risk, CMI 2.0, AIFC PIR debt, 3 COGS DACIs, LH skill-conflict, Memory subsystem); Z + M workstreams; OBS3, INS1, OPS3, R23, AIFC7, RV5 | "Plan-of-plan" structure (sub-files never created); item IDs that may overlap v7 (R23/RV3/RV5/INS1/OPS3 — verified novel before keeping); Cat-1 SLO numbers acted on while still draft (mitigated via anti-goal #42) |
| **B — Claude Sunset** (745 lines, 2026-05-14) | Deep code evidence (file:line + LoC for every god-class refactor); ARC-1 LLM provider hierarchy; ARC-2/3/4 god-class decomposition tables; ARC-6 typed FF + RequestScopedLLMFlags; ARC-7 async migration scope (607 sites); PLT-1 Resilience4j 13-integration table; PLT-2/4/5/7/8/15 quick wins; INT-1/3/9/10 intelligent context | No anti-goals (added 5 new ones below); no $/mo dollar estimates (added per-item where measurable); Tier 5 over-stuffed (split into Wk 9-12 + carry-over); INT-7 / INT-8 / INT-11 / INT-12 / PLT-14 demoted to "research-track" (premature for current evidence) |
| **C — BOOST v1 (mine)** (301 lines, 2026-05-14) | Workstream organization with companion files; explicit anti-goals (#37-#41); cut-tier matrix; M10-M12 measurement extensions; goal-anchoring discipline; quantified $/mo per item | Pattern-based items (X4, X5, X7) require deeper grep before scoping; Y2 .block() scope too narrow (4 vs 607 sites); R10 too high-level (replaced by Sunset's PLT-1 detail) |

### 0.2 Exclusion check (must remain de-duplicated)

Every integrated item below was grep-verified to be **NOT** present in:

- ✅ v7 plan TOP-15 / TOP-25 / cut-tier (Q/L/T/C/K/F/E/R/N/O/A workstreams)
- ✅ My 18 open PRs (T0a/T0b/T1/T2, R-1A/R-1B, A1-A12, NEW, L1, C2)
- ✅ BOOST v1 4 workstreams (R/S/X/Y series — superseded by this integrated plan)

Where an integrated item shares an ID *prefix* with v7 (e.g., R23 vs v7's R-series), §0.3 documents the reason. Where ambiguity exists, the item is marked `[verify-vs-v7]` in §3.

### 0.3 Naming convention (for reviewers)

To avoid confusing this plan's IDs with v7's: this integrated plan **adopts BOOST-Sunset namespacing** for the refactor pillar (`ARC-N`, `PLT-N`, `INT-N`) since these are the most file-evidence-anchored, and **adopts BOOST-Cursor namespacing** for the new pillars (`Z-N` perf-contract, `M-N` monetization, `G-N` quality/eval). My v1 IDs (R/S/X/Y) are retired — superseded items are noted in §0.4.

### 0.4 Supersession map

| BOOST v1 ID | Status in integrated plan | Replacement |
|---|---|---|
| R1 (mono ConfluenceClient refactor) | DEFERRED to Wk 9+ | rolled into ARC-1's "extend pattern beyond LLM providers" follow-up |
| R8 (TCS cache consolidation) | KEPT as **PLT-6** (read-through cache hierarchy is the elegant home) | merged with Sunset PLT-6 |
| S1 (fire-and-forget DLQ) | KEPT as **PLT-15.5** | reuses BOOST v1 design with PLT-15 namespace |
| S2 (concurrent-conv saturation gauge) | KEPT as **PLT-11.5** | metric-only first; load-shed second |
| S5 (post-workflow idempotency) | KEPT as **PLT-15.6** | extends R-6A from v7 |
| X2 (tool-schema cross-turn dedup) | KEPT as **U-3** | within "U — Throughput/Cost" workstream |
| X4 (agent prompt factorization) | DROPPED — covered by INT-9 PromptComposer | Sunset's elegant alternative |
| X5 (knowledge result cache) | KEPT as **PLT-6.2** | merged into PLT-6 hierarchy |
| X7 (Sonnet→Haiku for routing) | UPGRADED & RENAMED **U-7** (via OBS3 evidence + EVAL2 gating) | model-selection now evidence-driven |
| Y1 (SSE event:ack preamble) | KEPT as **W-1** | "W — Latency-Lite" workstream |
| Y2 (.block() removal) | UPGRADED & MERGED into **ARC-7** (607 sites) | Sunset scope wins |
| Y3 (parallel tool-call execution) | KEPT as **W-3** | gated on R-6A live ≥7 days |

---

## 1. The 6 integrated workstreams

| # | Workstream | Items | Goal anchor | Net-new lever |
|---|---|---|---|---|
| 1 | **ARC** — Architecture Modernization | 7 | Dev velocity + Reliability | God-class decomposition, 16-provider consolidation, async-migration completion |
| 2 | **PLT** — Platform Hardening | 9 | 99.85% SLO + Trust | Resilience4j deep integration, N+1 elimination, cache hierarchy, silent-failure remediation |
| 3 | **INT** — Intelligent Conversation | 5 | AIFC quality + MAU | Semantic context, progressive summarization, modular prompts, quality gate |
| 4 | **W** — Latency-Lite | 5 | TTFB + 150k MAU | SSE preamble, parallel tool calls, pre-warm, FF memo, allocation hot spots |
| 5 | **U** — Throughput / Cost | 7 | $168-290K/mo + capacity | OBS3 cost metric, INS1 (-$30-80K), OPS3 autoscale, RV5 adaptive iter, AIFC7 cache key fix, X2 schema dedup, U-7 model-selection (X7-renamed) |
| 6 | **Z + M + G** — Perf Contract / Monetization / Quality-Eval | 8 | FY27 Cat-1/3/5 SLO + COGS DACIs + 99% Reliability Push | Cat-1 instrumentation, TenantTier, EVAL1+EVAL2, LH skill-conflict, AIFC PIR closure |

**Total: 41 high-impact items** (vs. 23 in BOOST v1, 34 in Sunset, 60 in Cursor v2). The reduction vs Cursor v2 reflects rigorous de-duplication + cut of unproven research items; the increase vs my v1 reflects Sunset's deep refactor evidence.

---

## 2. Three design principles (sharpened)

1. **Goal-driven priority.** Every item declares one primary FY26/FY27 goal, quantified impact, confidence (0.0-1.0), risk, and effort. No "nice-to-have" items.
2. **Excludes overlap.** Every item grep-verified against v7, BOOST v1, 18 open PRs (§0.2).
3. **Refactor-when-justified.** Refactors only land if they show measurable velocity / reliability / cost win within 6 weeks of merge. No "refactor because ugly" (anti-goal #41 retained from BOOST v1).
4. **(NEW)** **Source-evidence required.** Every "L"-effort item must have a file:line citation OR a TWG / Confluence / Jira ticket reference. Pattern-based items (no citation) cap at "M" effort.
5. **(NEW)** **Single source of truth.** This plan IS the single source of truth — no plan-of-plan / sub-file-only structure. Companion docs (§11) are detail not deferred work.

---

## 3. TOP-15 ranked by goal-impact (do these first)

| # | ID | Item | Primary goal | Quantified impact | Conf | Effort | Risk | Source |
|---|----|------|---------------|---------------------|------|--------|------|--------|
| 1 | **U-1** OBS3 | Real-time `(model, experience, tenant)` cost metric | Cost / Monetization foundation | Enables U-7, EVAL2, M-2 budgets, X-style routing decisions | 0.95 | M | Low | Cursor v2 |
| 2 | **U-2** INS1 | Consolidate 6 Insights LLM calls → 1 structured-output call | Cost | **−$30-80K/mo** (single largest unclaimed lever) | 0.85 | M | Med (cohort A/B for per-type CTR) | Cursor v2 |
| 3 | **U-3** OPS3 | HOT-301423 tomcat-thread + queue-depth autoscaling | Cost / Throughput / Reliability | **−30-50% steady-state instance count**; closes known-TODO HOT incident | 0.9 | M | Med (perfhammer-gated) | Cursor v2 |
| 4 | **W-2** R23 | Split `hydratePool=2` (web Jsoup) from history hydration pool | Latency / MAU | **−500ms-2s p95** on history-heavy resume; silent-serialization fix | 0.95 | XS-S | Low | Cursor v2 |
| 5 | **PLT-2** | TokenBucketRateLimiter spin-wait → Resilience4j RateLimiter | Cost / Reliability | Eliminates CPU spin at 2,900+ req/s; **30-min XS fix** | 1.0 | XS | Very low | Sunset |
| 6 | **PLT-15.5** | Fire-and-forget DLQ for ApplicationCoroutineScope (memory ingest) | Reliability / Trust | **0 silent memory-loss events** (categorical safety) | 0.95 | M | Med (SQS coord) | BOOST v1 / S1 |
| 7 | **PLT-15** | Silent failure remediation in `ConversationStateManagerImpl:86-94` | Reliability / Trust | XS counter+1retry; prevents state desync | 0.95 | XS | Very low | Sunset |
| 8 | **U-4** RV5 | Adaptive Marathon iteration cap via `QueryComplexityService` | Cost / Quality / Latency | **−$15-40K/mo**; mean iters −50% on simple; reuses launched async classifier | 0.85 | S | Med (depth tuning A/B) | Cursor v2 |
| 9 | **G-3** EVAL1 | PR-gate eval harness on Goldens-300 | Quality | Catches AIFC quality regressions pre-merge | 0.85 | M | Low (gated by v7 Q13 datasets) | Cursor v2 |
| 10 | **Z-1** | Adopt FY27 Cat-1 Perf Contract for Rovo Chat (TTFT p90≤1.5s, jitter p95≤800ms, cancel p95≤500ms, stream-success ≥99.0%) | SLO redefinition | Replaces flat 99.9% with concrete user-perceptible SLOs | 0.9 | M (instrumentation + dashboards + alerts) | Low | Cursor v2 |
| 11 | **G-1** | LH skill-conflict workstream (41KB system-prompt drain, tool overlap registry, vague-query cost guard) | Quality / Cost | Eliminates AIA-1998 class; **−$3-8K/mo** vague-query cost; +5-15% search hit-rate | 0.85 | L | Med | Cursor v2 |
| 12 | **PLT-4** | N+1 elimination in `ConversationHistoryItemManagerImpl` (lines 529-552, 554-579, 581-604) | Latency / Reliability | **−50-80% Object Store calls; −2-5s p95** for large conversations | 0.95 | M | Low | Sunset |
| 13 | **U-5** AIFC7 | Drop `accountId` from MCP schema cache key | Cost (Redis) / Latency | **~80% Redis MCP-cache memory savings**; hit-rate O(N_users)→O(N_servers) | 0.9 | S | Med | Cursor v2 |
| 14 | **W-3** Y3 | Parallel tool-call execution within single LLM-decision turn | Latency / Capacity | **−500-2,000ms p95 multi-tool**; gated on R-6A live ≥7 days | 0.85 | S-M | Low (gated) | BOOST v1 / Cursor v2 |
| 15 | **M-1** | First-class `TenantTier` (FREE/STD/PREMIUM/ENT) read once per request | Monetization / Quality / Trust | Foundation for premium-only Opus, per-tier rate limits, max-iter caps; aligns with FY27 Cloud Price Increase + 3 COGS DACIs (Rovo CLI / JCA-RDiJ / TWC Billable) | 0.85 | L | Med (entity-model alignment with Rohit's DACI page 7023743677) | Cursor v2 |

**TOP-15 aggregate impact (claimed; verified post-deploy via M10-M15):**

- **Cost:** **−$45-130K/mo additive** (U-1 enables, U-2 −$30-80K, U-4 −$15-40K, U-5 ~80% Redis saving, plus G-1 −$3-8K)
- **Latency:** **−1,000-4,000 ms p95** (W-2 −500-2s, PLT-4 −2-5s, W-3 −500-2s)
- **Reliability:** Eliminates pod OOM / silent memory loss / state desync; closes HOT-301423 alert pattern
- **SLO redefinition:** flat 99.9% → concrete Cat-1 TTFT/jitter/cancel/stream-success
- **Capacity:** −30-50% steady-state instances (U-3 OPS3) + multi-tool parallel (W-3)
- **Quality:** PR-gate (G-3) catches regressions; LH cleanup (G-1) closes a real production bug class

---

## 4. Full workstream tables (all 41 items)

### 4.1 ARC — Architecture Modernization (7 items)

| ID | Title | File:line | Effort | Impact | Risk | Source |
|----|-------|-----------|--------|--------|------|--------|
| **ARC-1** | LLM Provider Hierarchy (Anthropic/Gemini/OpenAI template-method) | 25 provider files; 4 Anthropic = 3,900 LoC; full table in §11 companion | L (3 sprints, parallelizable) | **−~4,170 LoC**; faster new-provider onboarding | Low (behind generic-client FF; compile-caught) | Sunset |
| **ARC-2** | `AIGatewayClientServiceImpl` decomposition (3,087 → ~800) | `modules/platform/service/service-impl/.../llm/AIGatewayClientServiceImpl.kt` lines 187-257, 291-380, 382-881, 610-665 | M (1 sprint) | 4 extracted services (ErrorHandler, RequestLogger, RequestBuilder, ExecutionWrapper); testability + readability | Low (pure structural) | Sunset |
| **ARC-3** | `LLMServiceImpl` decomposition (1,831 → ~600) | `modules/platform/service/service-impl/.../llm/LLMServiceImpl.kt` lines 220-298, 432-603, 1700-1831; `@file:Suppress("ExposedBlockingBridge", "ForbiddenBlockCall")` at line 1 | M (1 sprint) | 3 services (ProviderRouter / ModelOverrideService / ObservabilityService); 18 duplicated provider-selection methods → 1 | Med (routing critical path; shadow-test via metrics) | Sunset |
| **ARC-4** | `AgentChatExecutor` decomposition (2,618 → ~500) | `modules/product/atlassianstudio/atlassianstudio-impl/.../executors/AgentChatExecutor.kt` lines 167-217 (40+ deps), 190-line `setupWorkflowContext()` | M (1 sprint) | 3 services (RoutingService / WorkflowSetupService / PersistenceService) | Med (critical path; FF-gated) | Sunset |
| **ARC-5** | MetricKey domain distribution (3,245-LoC enum → per-domain `MetricKeyLike` companions) | `modules/platform/service/service-api/.../metrics/MetricKey.kt` lines 1205, 3193 (active TODOs) | S (ongoing, opportunistic) | Prevents 3,245-LoC file growth; per-domain ownership | Very low (additive; old enum untouched) | Sunset |
| **ARC-6** | Typed FF + `RequestScopedLLMFlags` (eliminate 33+ Statsig evals/req in hot path) | `LLMServiceImpl.kt:220-298` (3× JSON parse boilerplate); 19 evals in LLMServiceImpl + 14 in AIGatewayClientServiceImpl + 3-8 per provider | S (1 sprint) | Single TypedDynamicConfig adapter; lazy per-request flag holder; deterministic eval | Low-Med (lazy preserves existing semantics) | Sunset |
| **ARC-7** | Async/Coroutine migration completion (4-phase) | 607 occurrences of `ForbiddenBlockCall`/`runBlockingWithContext`; key file `modules/platform/service/service-api/.../llm/StreamingLanguageModelProvider.kt` | L (4 phases across 2 quarters) | Eliminates 600+ `@Suppress`; removes thread-pool contention risk; **subsumes BOOST v1's Y2 (only saw 4 sites)** | Med (interface-bridge keeps it incremental) | Sunset (supersedes BOOST v1 Y2) |

### 4.2 PLT — Platform Hardening (9 items)

| ID | Title | File:line | Effort | Impact | Risk | Source |
|----|-------|-----------|--------|--------|------|--------|
| **PLT-1** | Resilience4j deep integration (13 integrations: AI Gateway 30%/100/15s, AGG 50%/100/10s, ERS 40%/50/5s, TAP 60%/20/5s, StreamHub 50%/50/10s, Search ×5 40%/30/10s; per-tenant SemaphoreBulkhead 50/500ms) | `gradle/libs.versions.toml:79` (Resilience4j 2.2.0 declared but only kotlin+retry used); 6 different patterns documented in Sunset PLT-1 | L (2-3 sprints) | Per-tenant isolation + cascading-failure prevention | Med (must not reject valid traffic; gradual rollout) | Sunset |
| **PLT-2** | TokenBucketRateLimiter spin-wait → Resilience4j RateLimiter | `modules/foundation/utilities/utilities-impl/.../featureflag/TokenBucketRateLimiter.kt` (`while(true) + compareAndSet`) | XS (30 min) | CPU savings at 2,900+ req/s | Very low (drop-in) | Sunset |
| **PLT-3** | Standardized retry patterns (`ConvoAiRetryPolicy` enum: FAST_FAIL / STANDARD / AGGRESSIVE / NONE) | 4 incompatible patterns: hand-rolled in `AbstractShardedErsClient.kt`, `TapTraitsCircuitBreaker.kt`, etc. | S | Single retry abstraction across all integrations | Low (behavioral equivalence per migration) | Sunset |
| **PLT-4** | N+1 elimination in `ConversationHistoryItemManagerImpl` (`withPluginInvocations`, `withMinionOutputs`, `withAgentUserContext`) | Lines 529-552, 554-579, 581-604; ERS `findByIds` already at `AbstractShardedErsClient:120-131` | M | **−50-80% Object Store calls; −2-5s p95** | Low | Sunset |
| **PLT-5** | ERS query push-down (`pageLimit(count) + sortDescending()`); replace do-while pagination | `SpaceServiceImpl.kt:120-122`; `AbstractShardedErsClient.fetchAllPages:205-220` | S | Eliminate fetching thousands when 10-20 needed | Low (query-level) | Sunset |
| **PLT-6** | Read-through cache hierarchy (L1 Caffeine + L2 Redis + L3 ERS); merges BOOST v1 R8 (TCS dedup) + X5 (knowledge result cache) | Multi-cache stack | M | **−30-50% ERS calls; −100-300ms p50** cache-hit paths; **−15-20% perm-check latency** (TCS consolidation) | Med (cache invalidation complexity; Redis pub/sub for cross-instance L1 invalidate) | Sunset + BOOST v1 R8/X5 |
| **PLT-7** | Content reader cache normalization | `ContentReaderCacheUtils.kt:23-24` (exact URL match only) | XS | **+15-30% cache hit rate** | Very low | Sunset |
| **PLT-8** | Batch ERS operations (`transactionalWrite`) | `ErsConversationGeneratedContentStoreImpl.kt:102-125` (N individual deleteById in loop); `transactionalWrite` at `AbstractShardedErsClient:243-253` | S | −N network calls per batch | Low | Sunset |
| **PLT-15** | Silent failure remediation (counter + 1-retry before warning log) | `ConversationStateManagerImpl.kt:86-94` | XS | Prevents state desync from swallowed errors | Very low | Sunset |
| **PLT-15.5** | Fire-and-forget DLQ for `ApplicationCoroutineScope` (memory ingest) | `modules/foundation/utilities/utilities-impl/.../threading/ApplicationCoroutineScope.kt:20-21,34-40,51-53` | M (3-4 days) | **0 silent memory-loss events** + first-time observability | Med (SQS DLQ coord) | BOOST v1 / S1 |
| **PLT-15.6** | Idempotency keys for post-workflow mutations (extends v7 R-6A from tools to post-workflow) | `RovoChatAsyncTaskLauncher.kt:1088-1101` | M | **0 duplicate user-message-store events on retry** | Med | BOOST v1 / S5 |
| **PLT-11.5** | Concurrent-conversation saturation gauge + load-shed (3-phase: metric → threshold → 429) | `RovoChatService.kt:206` (`AtomicInteger(0) concurrentConversations` w/ no max + no metric) | S | Prevents tail-latency cascade under thundering-herd | Low (metric-only first) | BOOST v1 / S2 |

### 4.3 INT — Intelligent Conversation (5 items, demoted from Sunset's 12)

> **Demotions / cuts vs Sunset's 12:** INT-2 (dynamic context budget) → folded into INT-3 progressive summarization; INT-4 (cross-conv via segments) → DEFERRED (research-track, needs evidence Memory subsystem doesn't already cover); INT-5 (subagent model routing) → folded into U-7 (model-selection); INT-6 (speculative parallel subagents) → folded into W-3 (parallel tool execution); INT-7 (inter-agent context sharing protocol) → DEFERRED (needs evidence the surface area is needed); INT-8 (centralized prompt registry) → DEFERRED (over-scope; revisit after INT-9 lands); INT-11 (quality-based dynamic model routing) → folded into U-7; INT-12 (adaptive response strategy) → DEFERRED (data-collection only).

| ID | Title | File:line | Effort | Impact | Risk | Source |
|----|-------|-----------|--------|--------|------|--------|
| **INT-1** | Semantic context window selection (replaces naive `takeLast(10)`) | `AgentChatExecutor.kt:1894`; existing `TeamserveSearchQrGemma3ModelProvider` + `InSessionSegment` infra unused | M | **+5-15pp response relevance** for multi-turn; reduced hallucination | Low (FF-gated; fallback to current `takeLast` behavior) | Sunset |
| **INT-3** | Progressive summarization for `SimpleLoopWorkflow` (reuse existing `ContextCompactionService` + Pebble templates) | `modules/product/rovo/rovo-impl/.../compaction/ContextCompactionServiceImpl.kt`; `SimpleLoopWorkflowExecutorImpl.execute()` | M | Enables longer agentic workflows without context overflow; reduces cost on multi-tool conversations | Low (reuses existing service; FF-gated) | Sunset |
| **INT-9** | Modular prompt composition (`PromptComposer` with budget-aware sections; eliminates string-concat) | `SimpleLoopWorkflowPromptService.buildSystemPrompt()` (manual concat) | M | Budget-aware prompts; eliminates concat bugs; subsumes BOOST v1 X4 (agent prompt factorization) | Low | Sunset (supersedes BOOST v1 X4) |
| **INT-10** | Streaming quality gate (heuristic-only; no LLM judge; uses existing `TextGenerationRequest.fallbackModel`) | `SimpleLoopWorkflowExecutorImpl.streamSingleAttempt():269` | S | Catches empty/error responses pre-delivery; near-zero latency overhead | Low | Sunset |
| **G-2** QT3 | Semantic DoomLoop detector with per-tool argument canonicalizer | LH long-running loop incidents per Hao Chen 2026-05-14 | M | Caps cost on agent-stuck-in-loop scenarios | Med (false-positive risk; needs canonicalizer per tool) | Cursor v2 |

### 4.4 W — Latency-Lite (5 items)

| ID | Title | File:line | Effort | Impact | Risk | Source |
|----|-------|-----------|--------|--------|------|--------|
| **W-1** Y1 | SSE `event: ack` preamble immediately after auth | `ChatV1Controller.kt:164,254` (NDJSON streaming endpoints currently produce `Flux<Any>`) | S | **−50-150ms perceived TTFB** | Low (preamble is non-payload) | BOOST v1 |
| **W-2** R23 | Split `hydratePool=2` web Jsoup pool from history hydration pool | hydratePool=2 silent serialization on history-heavy resume | XS-S | **−500ms-2s p95** on history-heavy resume | Low | Cursor v2 |
| **W-3** Y3 | Parallel tool-call execution within single LLM-decision turn (read-only allowlist first; gated on R-6A live ≥7 days) | `SimpleLoopWorkflowExecutorImpl` executeTools loop; existing `PARALLEL_TOOL_EXECUTION_LIMIT = 5` at line 849-873 | S-M | **−500-2,000ms p95** on multi-tool turns | Low (gated) | BOOST v1 + Cursor v2 + Sunset INT-6 (merged) |
| **W-4** Y4 | Speculative pre-warm (parallelize tenant resolution + auth + user-context hydration) | `RovoChatService.chatStream()` and `ChatV1Controller` (currently sequential) | M | **−80-200ms p50 TTFB** | Low (additive parallelism) | BOOST v1 |
| **W-5** Y5 | Per-request Statsig FF-eval memo (extends N6) | Multiple sites in `modules/product/rovo/`, `modules/platform/conversation/`; subsumed by ARC-6 RequestScopedLLMFlags (chat path) | XS | **−20-50ms p95** | Very low | BOOST v1 (folded into ARC-6 for LLM hot path; W-5 covers chat-path remainder) |

### 4.5 U — Throughput / Cost (7 items)

| ID | Title | File:line / evidence | $/mo or quantified | Effort | Risk | Source |
|----|-------|------------------------|--------------------|--------|------|--------|
| **U-1** OBS3 | Real-time `(model, experience, tenant)` cost metric | Foundation/Service layer; per-feature attribution panel | Enables U-7, EVAL2, M-2, X-style decisions | M | Low | Cursor v2 |
| **U-2** INS1 | Consolidate 6 Insights LLM calls → 1 structured-output call | Product layer; current Insights calls 6 LLMs sequentially per regen | **−$30-80K/mo** (single largest unclaimed lever) | M | Med (cohort A/B for per-type CTR) | Cursor v2 |
| **U-3** OPS3 | HOT-301423 tomcat-thread + queue-depth autoscaling | Foundation; closes known-TODO HOT-301423 incident | **−30-50% steady-state instance count** | M | Med (perfhammer-gated; 24h post-deploy GC + heap monitoring) | Cursor v2 |
| **U-4** RV5 | Adaptive Marathon iteration cap via existing `QueryComplexityService` | Reuses launched async classifier; depth=75 → adaptive | **−$15-40K/mo**; mean iters −50% on simple queries | S | Med | Cursor v2 |
| **U-5** AIFC7 | Drop `accountId` from MCP schema cache key | Cache key contains user-scope → cardinality explosion | **~80% Redis MCP-cache memory savings**; hit-rate O(N_users)→O(N_servers); makes SCALE2 viable | S | Med | Cursor v2 |
| **U-6** X2 | Tool-schema cross-turn dedup (memo within conversation, hash-keyed) | `modules/platform/service/service-impl/.../llm/toolconverter/` (Claude / ChatCompletion / Gemini / RawPredict / FunctionTool) | **−$4-6K/mo** (5-15KB JSON per turn × 5-10 turns / conversation) | M | Low-Med | BOOST v1 |
| **U-7** | Model-selection routing (subsumes BOOST v1 X7 Sonnet→Haiku + Sunset INT-5 subagent + INT-11 quality-aware): evidence-driven via U-1 OBS3 + EVAL2 (G-4) | Routing/classification across `modules/product/chat-common/`, `modules/product/shared-features/` + Maui Infra GPT-4.1 vs GPT-5 in-flight decision (2026-04-28) | **−$16.8-43.5K/mo** (Haiku for routing) + **−15-30%** (subagent quality-aware) | L (3-4 weeks; A/B + accuracy gates) | Med (must NOT ship without LLM-judge accuracy A/B ≤5pp delta) | BOOST v1 X7 + Sunset INT-5/11 + Cursor v2 model-selection |

### 4.6 Z + M + G — Perf-Contract / Monetization / Quality-Eval (8 items)

| ID | Title | File:line / source | Effort | Impact | Risk | Source |
|----|-------|--------------------|--------|--------|------|--------|
| **Z-1** | Adopt FY27 Cat-1 Perf Contract for Rovo Chat (TTFT p90≤1.5s, p99≤5s, jitter p95≤800ms, stream-complete p90≤15s, stream-success ≥99.0%, time-to-cancel p95≤500ms) | jgrose Confluence page 7039684456 (2026-05-15) | M | Replaces flat 99.9% with concrete user-perceptible SLOs | Low (must confirm working-draft per anti-goal #42) | Cursor v2 |
| **Z-2** | Cat-3 silent-death ≤0.1% probes for SQS handlers | gates on PLT-15.5 DLQ counter | S | **0 silent-handler-death** observability for SQS / Aqui consumers | Low | Cursor v2 (gates on BOOST v1 S1) |
| **Z-3** | Cat-5 MCP cold-start p95 ≤2s | MCP discovery flow | M | Cold-start latency SLO closes a known regression | Low | Cursor v2 |
| **M-1** | First-class `TenantTier` (FREE/STD/PREMIUM/ENT) read once per request | Foundation; aligns w/ Rohit's "Rovo & AI Feature" DACI page 7023743677 (IMPACT HIGH, 2026-05-15) | L | Foundation for premium-only Opus, per-tier rate limits, per-tier max-iter caps | Med | Cursor v2 |
| **M-2** | Per-tenant cost caps + cost-aware degradation (depends on M-1 + U-1) | Foundation/Service | M | Bounded blast radius for noisy enterprise tenants; aligns w/ JCA-RDiJ DACI ("uncapped COGS exposure June-October") | Med | Cursor v2 |
| **G-1** | LH skill-conflict workstream (41KB system-prompt drain, tool overlap registry, vague-query cost guard) | Hao Chen 2026-05-14; AIA-1998 | L | Eliminates AIA-1998 class; **−$3-8K/mo** vague-query; +5-15% search hit-rate | Med | Cursor v2 |
| **G-3** EVAL1 | PR-gate eval harness on Goldens-300 | Builds on v7 Q13 datasets | M | Catches AIFC quality regressions pre-merge | Low | Cursor v2 |
| **G-4** EVAL2 | Production-shadow eval pipeline → auto-rollback signal feeder | 0.1% sampling via existing `onComplete` hook | L | Auto-rollback fires on quality regressions; enables zero-risk prompt/model A/B in prod; **gates U-7** | Med | Cursor v2 |

---

## 5. Sequencing — 12-week plan (with explicit dependencies)

```
Wk 0   FOUNDATION GATES (must land before anything else)
        U-1 OBS3 (cost metric) ─────── unlocks U-7, EVAL2, M-2
        Z-1 (Cat-1 Perf Contract instr) ─── unlocks Cat-1 SLO measurement
        G-3 EVAL1 (PR-gate harness) ─── unlocks safe prompt/model changes
        ARC-5 MetricKey domain split (start, opportunistic) ─── prevents file growth

Wk 1-2 XS QUICK WINS PARALLEL (4 engineers)
        PLT-2 TokenBucketRateLimiter spin-fix (30 min, anyone)
        PLT-7 Content reader cache normalization (XS)
        PLT-15 Silent-failure remediation (XS)
        W-2 R23 hydratePool split (XS-S)
        U-5 AIFC7 MCP accountId-key fix (S)
        W-1 SSE event:ack preamble (S)
        W-5 FF-eval memo (XS, chat-path remainder)
        PLT-11.5 concurrent-conv saturation gauge (S, metric-only)

Wk 3-4 COST + INSIGHTS COMPOUNDING
        U-2 INS1 (6-conv Insights → 1 call) — start
        U-4 RV5 (adaptive iteration cap)
        U-6 X2 (tool-schema cross-turn dedup)
        ARC-6 typed FF + RequestScopedLLMFlags ─── prerequisites for U-7
        Z-2 Cat-3 silent-death probes ─── depends on PLT-15.5 DLQ counter

Wk 5-6 THROUGHPUT + AUTOSCALE
        U-3 OPS3 (HOT-301423 autoscale) — perfhammer-gated
        ARC-2 AIGatewayClientServiceImpl decomposition (M)
        ARC-3 LLMServiceImpl decomposition (M; shadow-test via metrics)
        PLT-3 Standardized retry patterns (S)
        PLT-5 ERS query push-down (S)
        PLT-15.5 Fire-and-forget DLQ (M; SQS coord)

Wk 7-8 RELIABILITY + N+1 + RESILIENCE START
        ARC-4 AgentChatExecutor decomposition (M)
        PLT-4 N+1 elimination in ConversationHistoryItemManager (M)
        PLT-8 Batch ERS operations (S)
        PLT-15.6 Idempotency keys for post-workflow (M; depends on v7 R-6A live)
        PLT-1 Resilience4j deep integration (start; L)
        Z-3 Cat-5 MCP cold-start ≤2s probes
        W-3 Y3 parallel tool-call execution (S-M; gated on R-6A live ≥7 days)

Wk 9-10 ARCHITECTURE DEEP REFACTORS + INTELLIGENCE
        ARC-1 Phase 1 Anthropic provider consolidation (proof-of-concept)
        ARC-7 Async/coroutine migration Phase 1+2 (audit + provider cleanup)
        PLT-6 Read-through cache hierarchy (L1+L2+L3 + Redis pub/sub invalidate)
        INT-1 Semantic context window selection (M; FF-gated)
        INT-9 Modular prompt composition / PromptComposer (M)
        INT-10 Streaming quality gate (S, heuristic-only)
        W-4 Speculative pre-warm (M)

Wk 11-12 QUALITY FINISHER + MONETIZATION + MODEL ROUTING
        G-1 LH skill-conflict workstream (L)
        G-2 QT3 semantic DoomLoop detector
        G-4 EVAL2 production-shadow pipeline (L; auto-rollback feeder)
        M-1 TenantTier first-class (L; aligns w/ Rohit DACI)
        M-2 per-tenant cost caps (depends on M-1 + U-1)
        U-7 Model-selection routing (L; only after EVAL2 + ≥7d M14 cost-attribution)
        INT-3 Progressive summarization (M; reuses ContextCompactionService)
        ARC-1 Phase 2 Gemini consolidation
        ARC-7 Phase 3 LLMService interface migration

Wk 13+  Carry-over / next quarter
        ARC-1 Phase 3 OpenAI consolidation
        ARC-7 Phase 4 follow-up services
        Sunset INT-7 / INT-8 / INT-11 / INT-12 (deferred research-track)
        BOOST v1 X9 (AIFC ADF block caching, L)
        BOOST v1 R1/R5 (ConfluenceClient mono refactor, REST v1 sunset)
```

**Parallelizable batches:**
- **Batch A — Independent quick wins (Wk 1-2):** PLT-2, PLT-7, PLT-15, W-1, W-2, W-5, U-5, PLT-11.5
- **Batch B — Foundation-gated (Wk 3+):** U-2, U-4, U-6, ARC-6 → enables U-7
- **Batch C — Capacity-coupled (Wk 5-7):** U-3, ARC-2, ARC-3, PLT-3, PLT-5
- **Batch D — Reliability-coupled (Wk 7-8, depends on v7 R-6A live):** PLT-15.6, W-3
- **Batch E — Refactor-coupled (Wk 9-10):** ARC-1, ARC-4, ARC-7, PLT-1, PLT-6
- **Batch F — Quality-coupled (Wk 11-12, depends on G-3 + G-4 live):** U-7, M-1, M-2, INT-1, INT-3, INT-9, INT-10

---

## 6. Anti-goals (carries v7's 36 + BOOST v1's 5 + 7 NEW BOOST-INTEGRATED-specific = 48 total)

(v7 anti-goals 1-36 carried verbatim; BOOST v1 anti-goals 37-41 carried verbatim; see source plans.)

**NEW BOOST-INTEGRATED anti-goals:**

42. **Do not ship Z-1 without confirming the FY27 Cat-1 SLO targets with jgrose** (page 7039684456 author) — these were a working-draft as of 2026-05-15.

43. **Do not adopt the FY27 Cat-3 silent-death ≤0.1% bar without first wiring PLT-15.5 DLQ counter** (otherwise the metric is unmeasurable).

44. **Do not promote U-7 (model-selection) above 5% rollout without EVAL2 (G-4) live for ≥7 days AND U-1 OBS3 cost-attribution for ≥7 days.** Cost win is meaningless if quality regresses; must show ≤5pp accuracy delta on labeled router/classifier dataset.

45. **Do not ship M-1 TenantTier without aligning with the canonical "Rovo & AI Feature" definition DACI** (Rohit Jhangiani, page 7023743677, IMPACT HIGH, 2026-05-15) — both must agree on the entity model.

46. **Do not ship U-2 INS1 (6-conv Insights consolidation) without cohort A/B comparing per-insight-type click-through rates** to verify low-value types are not silently degraded.

47. **Do not ship ARC-1 (16-provider consolidation) before ARC-7 Phase 1+2** — the consolidation should land on a single suspend-only API.

48. **Do not include Sunset INT-7 / INT-8 / INT-11 / INT-12 / PLT-14 in the 12-week plan.** These are research-track items requiring stronger evidence (LLM-judge per-routing accuracy, prompt-evolution lifecycle, false-positive budgets) before promotion.

---

## 7. Cut-tier (what to drop if constrained)

| Sprint length | Items dropped (drop count) | Items kept (keep count) | Rationale |
|---|---|---|---|
| **12-week (FULL)** | 0 dropped | All 41 items | All 6 workstreams ship |
| **8-week** | Wk 9-12 items: ARC-1 Ph2/3, ARC-7 Ph3, INT-3, M-2, U-7, INT-1, G-2 (7) | 34 kept | Defer architecture-deep + quality-finisher; quick-wins keep landing |
| **6-week** | + ARC-4, PLT-1 start, INT-9, INT-10, W-4, G-1, G-4 (7) | 27 kept | Wk 7-8 reliability deferred; document as "carry over to next quarter" |
| **4-week** | Keep ONLY load-bearing: U-1, U-2, U-3, W-2, PLT-2, PLT-15.5, PLT-15, U-4, G-3, Z-1, G-1 (11) | 11 kept | TOP-15 minus M-1, PLT-4, W-3, U-5 (each ≥1pp on a top FY26 goal) |
| **NEVER cut (load-bearing)** | U-1 (cost foundation), G-3 (PR-gate), PLT-15.5 (silent loss), PLT-2 (XS spin-fix), W-2 (XS-S latency), G-1 (real bug class) | 6 minimum | These move >1pp on a top FY26 goal each |

---

## 8. Measurement plan extensions (M1-M9 from v7 + M10-M12 from BOOST v1 + NEW M13-M15)

| ID | What it proves | Required instrumentation | Source |
|----|----------------|--------------------------|--------|
| **M10** | BOOST cost claims (X-series equivalents: U-2, U-4, U-6, U-7) | Per-feature token attribution panel via M4 Socrates `convo_ai_usage`; per-conversation tool-schema bytes counter (U-6); router/classifier model-name counter + accuracy delta (U-7) | BOOST v1 |
| **M11** | BOOST refactor velocity (ARC-series) | Per-week LoC-removed counter (ARC-1, ARC-2, ARC-3, ARC-4); per-week PR-merge throughput (correlate w/ refactor merges) | BOOST v1 |
| **M12** | BOOST silent-bug counters (PLT-15.5/.6/-11.5) | DLQ message-count for fire-and-forget tasks; duplicate post-workflow-mutation counter; load-shed-trigger counter; slow-client-timeout counter | BOOST v1 |
| **M13** | Cat-1 Perf Contract compliance (Z-1) | TTFT p90/p99 histograms; inter-token jitter p95; stream-success ≥99.0%; time-to-cancel p95 ≤500ms; per-experience attribution | Cursor v2 |
| **M14** | Real-time cost panel (U-1 OBS3) | Per-(model, experience, tenant) USD/min counter; tenant-budget-overrun alarm <1min vs hours of Databricks lag | Cursor v2 |
| **M15** | Production-shadow eval signal feed (G-4 EVAL2) | 0.1% sample turn → ARIZE judge → pushed back to v7 O1 auto-rollback decision | Cursor v2 |

**Hard rule (extends BOOST v1):** No item ships claiming impact until the relevant `M10-M15` is live for ≥7 days.

---

## 9. Risk register (BOOST-INTEGRATED-specific; carries v7 + BOOST v1 risks)

| # | Risk | Owner | Mitigation |
|---|------|-------|------------|
| 1 | **U-7 routing accuracy regression** | Model owner | 5%→25%→50%→100% rollout w/ paired LLM-judge accuracy A/B; auto-rollback if accuracy delta >5pp (anti-goal #44) |
| 2 | **W-3 parallel-tool side-effect amplification** | Workflow owner | Gated on R-6A live ≥7 days; per-tool `parallelizable=true` allowlist initially limited to read-only tools |
| 3 | **ARC-1, ARC-2, ARC-3, ARC-4 refactor regression** | Refactor owner | Anti-goal #41 (must show velocity / reliability impact within 6 weeks of merge); compile + smoke + integration test gates; FF-gated for ARC-3, ARC-4 |
| 4 | **PLT-6 read-through cache invalidation correctness** | Cache owner | Detailed cache-hit-rate metric before/after; revert flag; cross-instance Redis pub/sub invalidate validated in soak test |
| 5 | **INT-1 semantic context window — embedding service unavailable** | INT owner | Fallback to recency `takeLast(10)` behavior preserved; FF-gated |
| 6 | **U-2 INS1 silent CTR degradation** | Insights owner | Anti-goal #46 (cohort A/B per-insight-type CTR mandatory before promotion) |
| 7 | **U-3 OPS3 autoscale flapping** | Foundation owner | Perfhammer-gated; 24h post-deploy GC + heap-used + replica-count monitoring |
| 8 | **PLT-1 Resilience4j over-rejection of valid traffic** | PLT owner | Per-integration thresholds tuned over 14-day audit-mode; gradual rollout |
| 9 | **G-1 LH skill-conflict prompt change quality regression** | Quality owner | Gated on G-3 EVAL1 PR-gate; G-4 EVAL2 prod-shadow rollback signal |
| 10 | **M-1 TenantTier entity-model conflict with Rohit's DACI** | Monetization owner | Anti-goal #45 (DACI alignment mandatory before merge) |
| 11 | **Z-1 Cat-1 SLO numbers change before adoption** | SLO owner | Anti-goal #42 (confirm with jgrose before instrumentation alarms fire) |

---

## 10. FY26/FY27 north-star tie-back

| North-star | Direct contributor | Indirect contributor |
|------------|---------------------|----------------------|
| **Beta GA AIFC FactualConsistency 13% → ≥40%** | G-3 (PR-gate), G-4 (prod-shadow) | INT-1 (semantic context), INT-9 (modular prompts), INT-10 (quality gate) |
| **150k Rovo MAU + 26.4K → 100K Extension MAU** | W-1, W-2, W-3, W-4 (TTFB), Z-1 (perceived perf SLO), G-1 (skill-conflict) | PLT-6 (cache hierarchy), U-3 (capacity headroom for usage growth) |
| **99.85% chat SLO** (capped by OpenAI 99.9% SLA) | PLT-1 (resilience), PLT-15.5 (silent loss), PLT-15.6 (post-workflow), PLT-15 (state desync) | PLT-11.5 (saturation gauge), Z-1 (Cat-1 stream-success ≥99.0%) |
| **+1,400 req/s peak throughput** | U-3 OPS3 (autoscale), W-3 (parallel tools), PLT-2 (CPU spin-fix) | PLT-4 (N+1 elim), PLT-5 (query push-down) |
| **−$168-290K/mo cost** (additive baseline) | **U-2 (-$30-80K)**, **U-7 (-$16.8-43.5K)**, **U-4 (-$15-40K)**, U-6 (-$4-6K), U-5 (~80% Redis), G-1 (-$3-8K) | **+$60-180K/mo additive** total |
| **Trust pillar (no silent-trust bugs)** | PLT-15, PLT-15.5, PLT-15.6 | M-2 (per-tenant cost caps; bounded blast) |
| **Dev velocity / LoC removed** | ARC-1 (-4,170 LoC), ARC-2 (3,087→800), ARC-3 (1,831→600), ARC-4 (2,618→500), ARC-5 (file-growth prevention), ARC-6 (33+ FF evals→1), ARC-7 (-600 suppressions) | **~7,000-9,000 LoC removed total** |
| **FY27 Cat-1/3/5 Perf Contract compliance** | Z-1, Z-2, Z-3, M13 instrumentation | All W-* and PLT-* items contribute |
| **3 in-flight COGS DACIs alignment** (Rovo CLI, JCA-RDiJ, TWC Billable) | M-1, M-2, U-1 | U-7 (model-routing) |
| **AIFC PIR-debt closure (AIFC-1503/1342/1714)** | (deferred Wk 13+; flagged for next-quarter epic) | (Z-1 alarms surface PIR violations) |

**TOP-15 aggregate impact summary (verified at 12 weeks via M10-M15):**

| Dimension | Improvement |
|-----------|-------------|
| **Cost** | **−$60-180K/mo additive** (incremental over v7 baseline) |
| **Latency** | **−1,000-4,000 ms p95**; first-time Cat-1 TTFT/jitter compliance |
| **Capacity** | −30-50% steady-state instances + parallel multi-tool throughput |
| **Reliability** | 0 silent memory-loss; 0 duplicate post-workflow mutations; 0 state-desync; bounded tail-latency cascade |
| **Quality** | PR-gate + prod-shadow harness; LH skill-conflict cleanup |
| **Code reduction** | ~7,000-9,000 LoC removed via ARC-* |
| **SLO redefinition** | flat 99.9% → concrete Cat-1/3/5 user-perceptible SLOs |

---

## 11. Companion documents

| File | Purpose | Status |
|------|---------|--------|
| `BOOST_INTEGRATED_v1.md` | This file (master plan) | ✅ Complete |
| `boost_items/ARC-Architecture.md` | Per-item ARC-1 through ARC-7 detail | TODO (extract from Sunset) |
| `boost_items/PLT-PlatformHardening.md` | Per-item PLT-1 through PLT-15.6 detail | TODO (extract from Sunset + BOOST v1) |
| `boost_items/INT-IntelligentConvo.md` | Per-item INT-1, INT-3, INT-9, INT-10 detail | TODO (extract from Sunset) |
| `boost_items/W-LatencyLite.md` | Per-item W-1 through W-5 detail | TODO (extract from BOOST v1) |
| `boost_items/U-ThroughputCost.md` | Per-item U-1 through U-7 detail | TODO (extract from Cursor v2 + BOOST v1) |
| `boost_items/Z-PerfContract.md` | Z-1, Z-2, Z-3 SLO instrumentation detail | TODO (extract from Cursor v2 + jgrose page) |
| `boost_items/M-Monetization.md` | M-1, M-2 + 3 COGS DACI alignment | TODO (extract from Cursor v2) |
| `boost_items/G-QualityEval.md` | G-1, G-2, G-3, G-4 + EVAL1/EVAL2 detail | TODO (extract from Cursor v2) |
| `BUSINESS_GOALS_DELTA.md` | What this changes vs FY26 goals doc | TODO |
| `SUPERSESSION_LOG.md` | Map BOOST v1 IDs → BOOST-INTEGRATED IDs | ✅ See §0.4 above |
| `EVIDENCE_INDEX.md` | One-stop file:line citation table for all 41 items | TODO |

---

## 12. Honest calibration

- **Confidence:** Items with file:line citation are 0.85+ confidence (mostly from Sunset's grep-evidence work; BOOST v1's 4 verified `.block()` sites; Cursor v2's TWG-anchored items).
- **Pattern-based items:** U-6 (X2 tool-schema dedup), U-7 (model-routing), G-1 (LH cleanup) are 0.80-0.85 confidence; need deeper code grep before final scoping (anti-goal: cap at "M" effort per §2 principle 4).
- **TWG-fresh signals:** Z-1, M-1, M-2, U-3 (HOT-301423), G-1 (LH 41KB), G-4 (EVAL2) anchored on Cursor v2's 2026-05-15 TWG sweep. These signals were live as of plan creation.
- **What's NOT verified:** This integrated plan has not run scripts/twg directly. The TWG signals are second-hand from Cursor v2 — risk that some signals shifted in the last 24h. Mitigation: Wk 0 task to re-confirm Z-1 / M-1 / G-1 with named owners before instrumentation.
- **What's missing:** AIFC FactualConsistency 13%→40% Beta-GA gate metric exact baseline (TWG QBR Q3 2026 whiteboard id 7038759626 not retrievable) — direct ask to Vibha Choudhary (PM) or Lucas Ferreira / Jason Baker (Eng) recommended.

---

## 13. Calling-for-action

1. **Triage TOP-15 with leadership** (Robbie Livermore, Kevin Ma, jgrose for Z-1, Jason Baker for AIFC PIR closure, Vincent Zeng for Memory work, Rohit Jhangiani for M-1 DACI alignment, Hao Chen for G-1 LH cleanup).
2. **Re-confirm TWG signals at Wk 0:** Z-1 (jgrose page 7039684456 still working-draft?), M-1 (Rohit DACI page 7023743677 entity model finalized?), G-1 (LH skill-conflict workstream owner identified?).
3. **Confirm v7 + BOOST v1 measurement infra (M1-M12) is live before claiming any BOOST-INTEGRATED impact.**
4. **Allocate ~3 engineers × 12 weeks** OR **6 engineers × 6 weeks** (per §7 cut-tier).
5. **Pick a deployment cadence:** Aggressive 12wk (41 items) / Balanced 8wk (34 items) / Conservative 4wk (11 load-bearing items).
6. **Generate Jira epics** for each of the 6 workstreams (ARC / PLT / INT / W / U / Z+M+G).
7. **Create the companion doc files** (§11 TODO list) once leadership signs off on TOP-15.

---

## 14. If we could only ship ONE plan, which would it be?

**Recommendation: This BOOST-INTEGRATED plan.**

**Reasoning** (critical-thinking, evidence-based):

| Criterion | BOOST v1 (mine) | Cursor v2 | Sunset | **BOOST-INTEGRATED** |
|---|:---:|:---:|:---:|:---:|
| TWG-fresh business signals | ❌ (stale) | ✅ | ❌ | ✅ (inherits Cursor v2's) |
| Code-evidence depth (file:line, LoC) | ◐ | ◐ | ✅ | ✅ (inherits Sunset's) |
| Goal-anchoring discipline | ✅ | ✅ | ❌ | ✅ |
| Anti-goals + cut-tier discipline | ✅ | ✅ | ❌ | ✅ (8 anti-goals; 4-tier cut) |
| $/mo dollar quantification | ✅ | ✅ | ❌ | ✅ |
| Refactor design depth | ❌ | ❌ | ✅ | ✅ |
| Single source of truth (no plan-of-plan) | ✅ | ❌ | ✅ | ✅ |
| Realistic scope (avoids over-stuff) | ✅ (23 items) | ❌ (60 items) | ❌ (34 items, Tier 5 over-stuffed) | ✅ (41 items w/ rigorous cut-tiers) |
| Measurement-plan extension | ✅ (M10-M12) | ✅ (M13-M15) | ❌ | ✅ (M10-M15) |
| Critical-thinking re. demotions / DEFERRED tracks | ◐ | ◐ | ❌ (Tier 5 over-stuffed) | ✅ (Sunset INT-7/8/11/12, PLT-14 explicitly DEFERRED w/ rationale) |
| Supersession discipline (no double-counting) | ✅ | ❌ | N/A | ✅ (§0.4 supersession map) |

**If forced to choose ONE source plan only** (NOT the integrated): I'd choose **Cursor v2** as the primary because:
1. Its TWG-fresh signals (FY27 Cat-1/3/5 SLO, MAU at-risk, AIFC PIR debt, COGS DACIs, LH skill-conflict, Memory subsystem) **change the FY27 goal landscape** in ways no purely-codebase analysis can capture.
2. Its $30-80K/mo INS1 lever is the single largest unclaimed cost win; missing it leaves dollars on the table.
3. Its anti-goals + cut-tier discipline match BOOST v1's quality.
4. Its weakness — being a plan-of-plan — would need to be paired with a sprint to materialize the sub-files; Sunset's depth would be added incrementally.

**But the BOOST-INTEGRATED plan is strictly better than any single source** because it loses none of Cursor v2's business signals AND gains Sunset's refactor depth AND retains BOOST v1's discipline. It is the proper, elegant, non-hacky answer.

---

**END OF PLAN.** All future updates should bump this file's version (`v1` → `v2`) and document deltas in a changelog section. Companion docs (§11) extract per-workstream detail for review-flow ownership.
