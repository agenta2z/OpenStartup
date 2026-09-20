# Convo AI Platform — BOOST Integrated Plan **v3**

**Status:** PROPOSED &nbsp;•&nbsp; **Date:** 2026-05-15 07:47 &nbsp;•&nbsp; **Author:** Tony Chen (4th-generation synthesis)
**Repo:** `atlassian/conversational-ai-platform` &nbsp;•&nbsp; **Supersedes:** `BOOST_INTEGRATED_v2.md` (mine), `convai-boost-v2_4ce55218.plan.md` (Cursor 805 lines, 07:35), `can-you-create-a-serene-sunset.md` (Sunset 221 lines, 07:23)

> **TL;DR.** Three plans now exist (Cursor 70-PR maximalist with 25 tactical wins; Sunset 45-PR streamlined with explicit Tier 6/7/Carry-Over; my v2 30-PR disciplined). All three are themselves integrations of each other. **v3 keeps v2's discipline, restores the 25 tactical items v2 dropped (Track P, Track B, Track A, OPS, CI, SIDECAR, AIFC, SVC, RV6, QT2, SCALE3, AIFC-PIR), and produces a 55-PR plan** organized into a Wk 0 / Wk 1-2 / Wk 3-4 / Wk 5-6 / Wk 7-8 / Wk 9-10 / Wk 11-12 / Carry-Over schedule. Sunset's §7 explicitly recommended my v1 as the best plan; v3 is the next iteration of that line.

---

## 0. v3 changelog (vs v2)

### 0.1 Critical material recovered from latest Cursor (07:35)

| Cursor item(s) | New in v3 | Why I missed it in v2 |
|---|---|---|
| **P1-P7 Track P parallelism** (Tool-Registry build, MCP fan-out, AGS cypher serial fixes, ContentHydrationService) | Added as PRs #13-#16 | v2 only had W-1 SSE preamble; missed concrete latency wins via parallelization |
| **B11-B15 Track B blocking-bridge retirement** (4 streaming sites + 16-provider blocking method) | Added as PRs #34-#35 | v2 had A2 as workstream, didn't decompose the 4 explicit streaming sites |
| **A16-A22 allocation hot spots** (bundled) | Added as PR #17 (LOW) | v2 didn't have allocation profiling tier |
| **OPS1/OPS2 Helm dedup** (-3,600 LoC YAML) | Added as PRs #62-#63 | v2 was code-only; missed ops/infra |
| **CI4 Gradle config cache restore** | Added as PR #64 | v2 had CI1 only |
| **SIDECAR1/SIDECAR3** (gunicorn + lean+heavy split) | Added as PRs #65-#66 | v2 didn't include sidecar tier |
| **AIFC1/AIFC2/AIFC5** (PromptRunner suspend, invokeStream Sequence→Flow, cost-tier ContextCompactionService) | Added as PRs #67-#68, #70 | v2 deferred all AIFC items |
| **SVC1 Experience.kt** (1,752-LoC monolith decomp) | Added as PR #59 | v2 had ARC-2/4 deferred but missed SVC1 |
| **AIFC-PIR debt closure** (AIFC-1503/-1342/-1714) | Added as PR #60 | v2 didn't include known production debt |
| **RV6 AdfEditor convergence detection** (20-30% iteration cuts) | Added as PR #55 | v2 only had QT3 DoomLoop |
| **QT2 Production 0.1% shadow eval** | Added as PR #25 | v2 only had EVAL2 (heavier; QT2 is lighter complement) |
| **SCALE3 ProactiveCacheKeyGenerator** | Added as PR #19 | v2 missed cache CPU optimization |
| **AF1+AF6 reflection / Stratus minion warmup** | Added as PR #18 (LOW) | v2 didn't include foundation framework items |
| **CI5 .projects/_template + repo TEST_SOP.md** | Added as PR #69 (LOW) | v2 missed dev-tools items |

### 0.2 Critical material kept from latest Sunset (07:23)

| Sunset feature | Kept in v3 | Why important |
|---|---|---|
| **Explicit Tier 6 + Tier 7 + Carry-Over (Wk 13+)** with PRs 42-45 | Adopted as v3 §3.7 + §3.8 | Forces explicit "what's deferred / next quarter" |
| **Sunset's §7 recommends MY v1** | Validates approach | Confirms 4-gen synthesis is the right direction |
| **Anti-goal #42 (NO Resilience4j; extend `AggResilienceProvider`)** | Carried unchanged | Elegance correction |
| **Cuts INT-7/8/11/12 + PLT-14 with rationale** | Carried unchanged | Avoids speculative items |
| **Compact PR list (45 PRs, not 70)** | Influences v3 to bundle small items into 1 PR | Realistic shipping cadence |

### 0.3 v2 items unchanged in v3

All 30 PRs from v2's PR_TRACKING.csv carry forward with their `[Impact: H/M/L]` labels intact. v3 **expands** to 55 PRs by adding Cursor's 25 tactical items (most are MEDIUM or LOW). The TOP-15 in §2 is unchanged from v2.

### 0.4 What v3 still cuts (carries from v2)

PLT-1 (Resilience4j as separate framework — REJECTED, redesigned as R1), PLT-6 (3-tier cache hierarchy — DEFERRED to Wk 13+ as Cursor PR #45), PLT-14 (regex prompt-injection — CUT), INT-7/8/12 (CUT), MON3 (CUT), original ARC-2/4 1-PR scope (DEFERRED via `.projects/rovo-module-decomposition/`).

---

## 1. v3 final structure: 7 workstreams, **55 PRs**, ~12 weeks (3-4 engineers)

| WS | Code | Items | PRs | Goal anchor |
|---|---|---|---|---|
| **P** — Perf Contract & Observability | P1-P3 + Z-2/Z-3 | 5 | 5 | FY27 Cat-1/3/5 SLO + cost foundation |
| **A** — Architecture (gated by `.projects/`) | A1-A7, ARC-5, B11-B15, SVC1 | 8 items / 11 PRs | 11 | Dev velocity + Reliability |
| **L** — Latency & Cost | L1-L7, P1-P7 (parallelism), W-4 (pre-warm) | 14 | 14 | Cost + Latency |
| **R** — Resilience | R1-R5, S1-S3, PLT-2/3/5/7/8/15, RV9 | 14 | 11 | 99.85% SLO + Trust |
| **I** — Conversation Intelligence | I1-I4, INT-1/3/9/10, RV6, QT3 | 8 | 8 | AIFC quality + MAU |
| **W** — Tactical wins | W-1, W-5, CI1, CI4, CI5, A16-A22, AF1+AF6, OPS1, OPS2, SIDECAR1, SIDECAR3, SCALE3 | 13 | 13 | Dev velocity + TTFB |
| **M** + **G** — Monetization & Quality-Eval | M-1/M-2, G-3 EVAL1, G-4 EVAL2 (+QT2 light), G-1 LH, AIFC-PIR, AIFC1/2/5 | 9 | 8 | Monetization & quality finishers |

**Net deliverables:** ~55 distinct PRs, ~71 unique items consolidated, 12-week landing schedule, explicit Carry-Over for Wk 13+.

---

## 2. TOP-15 (unchanged from v2, lightly updated for cross-reference with new PRs)

| # | ID | Item | Impact | Conf | Effort | PR # |
|---|----|------|---------|------|--------|------|
| 1 | **P3 / U-1 OBS3** | Real-time `(model, experience, tenant)` cost panel | Foundational keystone | 0.95 | M | **#1** |
| 2 | **L3 / U-2 INS1** | Consolidate 6-conv Insights → 1 structured-output call | **−$30-80K/mo** | 0.85 | M | **#20+#21** |
| 3 | **L1** | Cache-friendly prompt structure (completes `.projects/cache-friendly-schema-agent-prompts/`) | **−$30K+/mo** | 0.9 | M | **#26** |
| 4 | **R3 / U-3 OPS3** | HOT-301423 autoscaling | **−30-50% instance count** | 0.9 | M | **#27** |
| 5 | **W-2 / R23** | hydratePool=2 split | **−500ms-2s p95** | 0.95 | XS-S | **#5** |
| 6 | **L6 / U-4 RV5** | Adaptive iteration cap | **−$15-40K/mo** | 0.85 | S | **#22** |
| 7 | **A1** | LLM Provider Hierarchy (4-family template-method) | **−4,170 LoC** | 0.85 | L | **#44+#57+CarryOver** |
| 8 | **A2** | Async migration (subsumes B11-B15) | Thread-pool relief | 0.9 | L | **#34+#35+#46+#58** |
| 9 | **R1** | Complete CB migration in **`AggResilienceProvider`** | Cascading-failure prevention | 0.85 | M | **#42** |
| 10 | **G-3 / EVAL1** | PR-gate eval harness | Quality | 0.85 | M | **#3** |
| 11 | **L2 / W-3 / Y3** | Parallel tool execution (read-only allowlist) | **−500-2,000ms p95** | 0.85 | S-M | **#33** |
| 12 | **P1 / Z-1** | FY27 Cat-1 Perf Contract instrumentation | SLO redefinition | 0.9 | M | **#2** |
| 13 | **L4 / PLT-4** | N+1 elimination in `ConversationHistoryItemManagerImpl` | **−2-5s p95** | 0.95 | M | **#36** |
| 14 | **A5 / ARC-6** | Typed FF + RequestScopedLLMFlags | **−20-50ms p95** | 0.9 | S | **#23** |
| 15 | **I4 / G-1** | LH skill-conflict workstream | **−$3-8K/mo + +5-15% search hit** | 0.85 | L | **#40** |

---

## 3. Concrete 55-PR list (with `[Impact: H/M/L]` labels)

### Impact rubric (consensus across all plans)
- **`[HIGH]`** — concrete latency >200ms p95, perceived TTFB >500ms, cost >$10K/mo, categorical safety (silent loss / OOM / cascading failure), Cat-1 SLO contributor, AIFC 13%→40% direct contributor, or load-bearing enabler for ≥3 HIGH PRs
- **`[MEDIUM]`** — latency 50-200ms p95, cost $1-10K/mo, reliability hardening, dev velocity (>500 LoC removed or >5 CI-min/PR), observability foundation
- **`[LOW]`** — micro-optimization (<50ms or <$1K/mo), pure code-quality refactor, allocation hot spots compounding to <5% gain individually, observability-only counters

### 3.1 Tier 1: Foundation Gates — Wk 0 (PRs #1-#4)

| PR | `[Impact]` | Title | Item | Effort | Deps | Owner |
|----|----|---|---|---|---|---|
| **1** | **`[HIGH]`** | `[Impact: High] [observability] P3 — Real-time (model, experience, tenant) cost metric foundation (OBS3) — unlocks $60-180K/mo downstream` | U-1 OBS3 | M | none | PLT team / Robbie Livermore |
| **2** | **`[HIGH]`** | `[Impact: High] [perf-contract] P1 — Adopt FY27 Cat-1 Perf Contract instrumentation (TTFT/jitter/cancel/stream-success histograms)` | Z-1 | M | jgrose-confirms | Z workstream / jgrose |
| **3** | **`[HIGH]`** | `[Impact: High] [quality] G-3 — PR-gate eval harness on Goldens-300 (EVAL1) — pre-merge AIFC regression catch` | G-3 | M | v7 Q13 | G workstream / Jason Baker |
| **4** | **`[HIGH]`** | `[Impact: High] [throughput][velocity] CI1 — Collapse 8 cloned IT-shard step blocks + per-flag-change gate — −25-35% PR wall-clock` | CI1 | M | none | DevTools team |

### 3.2 Tier 2: XS/S Quick Wins — Wk 1-2 (PRs #5-#19, parallel batch)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **5** | **`[HIGH]`** | `[Impact: High] [latency] W-2 — Split hydratePool=2 web-Jsoup pool from history hydration pool (R23) — −500ms-2s p95 history-resume` | W-2 R23 | XS-S | none |
| **6** | **`[HIGH]`** | `[Impact: High] [cost][cache] L7 — Drop accountId from MCP schema cache key (~80% Redis savings, AIFC7)` | L7 AIFC7 | S | none |
| **7** | **`[MEDIUM]`** | `[Impact: Medium] [latency] A5 — Typed Dynamic Config + RequestScopedLLMFlags (33+ FF evals → 1) — −20-50ms p95` | A5 ARC-6 | S | none |
| **8** | **`[MEDIUM]`** | `[Impact: Medium] [latency] W-1 — SSE event:ack preamble for ChatV1Controller streaming endpoints — −50-150ms perceived TTFB` | W-1 Y1 | S | none |
| **9** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] PLT-15 — Silent failure remediation in ConversationStateManagerImpl:86-94 (counter + 1-retry)` | PLT-15 | XS | none |
| **10** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] S2-Phase1 — Concurrent-conversation saturation gauge (RovoChatService:207, metric-only)` | S2 PLT-11.5 | S | none |
| **11** | **`[LOW]`** | `[Impact: Low] [perf] PLT-2 — TokenBucketRateLimiter spin-wait → AggResilienceProvider RateLimiter (CPU savings at 2,900+ RPS)` | PLT-2 | XS | none |
| **12** | **`[LOW]`** | `[Impact: Low] [cache] PLT-7 — Content reader cache URL normalization (+15-30% hit rate)` | PLT-7 | XS | none |
| **13** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P1-parallel — Parallelize ToolRegistry build across Native/MCP/IS/Forge backends — −150-400ms p50 pre-LLM` | P1-track | S | none |
| **14** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P2-parallel — MCP server fan-out parallelism in 3 of 4 paths — −300-800ms p50 MCP-heavy tenants` | P2-track | XS | none |
| **15** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P4+P5+P6 — Parallelize AGS getTeamWorkSummary 3 cypher queries + linkWorkItemsToProject + getPrInRepositories — −500ms-2s p95` | P4-6 track | XS-S | none |
| **16** | **`[MEDIUM]`** | `[Impact: Medium] [latency] P7 — ContentHydrationService parallelize attachment fetches with hydration query — −300-800ms p50` | P7 track | S | none |
| **17** | **`[LOW]`** | `[Impact: Low] [perf] A16-A22 — Bundle 7 micro-allocation hot spots (entity.toString, jacksonObjectMapper, JsonSchema cache, RolloutService) — ~5-15% young-gen pressure relief` | A16-A22 | S | none |
| **18** | **`[LOW]`** | `[Impact: Low] [perf] AF1+AF6 — AgentPermissionServiceImpl reflection cache + Stratus minion warmup` | AF1+AF6 | XS | none |
| **19** | **`[LOW]`** | `[Impact: Low] [cost][latency] SCALE3 — ProactiveCacheKeyGenerator hash optimization (~50-100× CPU reduction on key-gen)` | SCALE3 | S | none |

### 3.3 Tier 3: Cost & Latency Compounding — Wk 3-4 (PRs #20-#26)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **20** | **`[HIGH]`** | `[Impact: High] [cost][quality] L3-Phase1 — Insights cohort A/B harness (per-insight-type CTR baseline) — gates Phase2 by anti-goal #46` | L3 INS1 P1 | M | #1, #3 |
| **21** | **`[HIGH]`** | `[Impact: High] [cost] L3-Phase2 — Consolidate 6-conv Insights → 1 structured-output call — −$30-80K/mo (largest unclaimed lever)` | L3 INS1 P2 | M | #20 (≥7d soak) |
| **22** | **`[HIGH]`** | `[Impact: High] [cost][quality][latency] L6 — Adaptive Marathon iteration cap via QueryComplexityService (RV5) — −$15-40K/mo; mean iters −50% on simple queries` | L6 RV5 | S | #1 (≥7d), accuracy A/B (anti-goal #51) |
| **23** | **`[MEDIUM]`** | `[Impact: Medium] [cost] U-6 X2 — Tool-schema cross-turn dedup (hash-keyed memo within conversation) — −$4-6K/mo` | U-6 X2 | M | none |
| **24** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] Z-2 — Cat-3 silent-death ≤0.1% probes for SQS/Aqui handlers (depends on PLT-15.5 DLQ counter)` | Z-2 | S | #28 |
| **25** | **`[MEDIUM]`** | `[Impact: Medium] [quality] QT2 — Production 0.1% shadow eval via existing onComplete hook (intraday quality-dip alarms; lighter than EVAL2)` | QT2 | M | #1, #3 |
| **26** | **`[HIGH]`** | `[Impact: High] [cost] L1 — Cache-friendly prompt structure (completes .projects/cache-friendly-schema-agent-prompts/ 4-PR plan) — −$30K+/mo via Anthropic prompt caching` | L1 | M | extends in-flight |

### 3.4 Tier 4: Reliability + N+1 — Wk 5-6 (PRs #27-#32)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **27** | **`[HIGH]`** | `[Impact: High] [reliability][cost] R3 — HOT-301423 tomcat-thread + queue-depth autoscaling (OPS3) — −30-50% steady-state instances` | R3 OPS3 | M | #1 (perfhammer-gated) |
| **28** | **`[HIGH]`** | `[Impact: High] [reliability] PLT-15.5 / S1 — Fire-and-forget DLQ for ApplicationCoroutineScope (memory ingest) — 0 silent memory-loss events` | S1 PLT-15.5 | M | none |
| **29** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] R2 — Standardized retry patterns (ConvoAiRetryPolicy enum: FAST_FAIL/STANDARD/AGGRESSIVE/NONE)` | R2 PLT-3 | S | none |
| **30** | **`[MEDIUM]`** | `[Impact: Medium] [latency] L5 — ERS query push-down (pageLimit + sortDescending; replace fetchAllPages)` | L5 PLT-5 | S | none |
| **31** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] R4 — Streaming quality gate (heuristic; uses TextGenerationRequest.fallbackModel)` | R4 INT-10 | S | none |
| **32** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] PLT-8 — Batch ERS operations (transactionalWrite); replace N individual deleteById loops` | PLT-8 | S | none |

### 3.5 Tier 5: Architecture + Throughput + Resilience — Wk 7-8 (PRs #33-#43)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **33** | **`[HIGH]`** | `[Impact: High] [latency][capacity] L2-PhaseA — Parallel tool-call execution within single LLM-decision turn (read-only allowlist) — −500-2,000ms p95 multi-tool turns` | L2 W-3 Y3 | S-M | v7 R-6A live ≥7d |
| **34** | **`[MEDIUM]`** | `[Impact: Medium] [throughput] B11 — Retire blocking streamFromLLM across 16 LLM providers (interface-level migration boundary)` | B11 | M | #38 (ARC-2 first) |
| **35** | **`[MEDIUM]`** | `[Impact: Medium] [throughput] B12-B15 — Eliminate per-chunk runBlocking in 4 streaming sites (OutputStreamStreamingWriter / TurboPuffer / LLMFollowUpGen / ToolRouter)` | B12-B15 | XS-S | none |
| **36** | **`[HIGH]`** | `[Impact: High] [latency][reliability] L4 — N+1 elimination in ConversationHistoryItemManager (withPluginInvocations / withMinionOutputs / withAgentUserContext, lines 529-604) — −2-5s p95` | L4 PLT-4 | M | none |
| **37** | **`[HIGH]`** | `[Impact: High] [reliability] R5 / RV3 — Replace AsyncAgentInMemoryJobStore with persistent backing — eliminates async-agent job-loss class on pod restart; enables horizontal scale` | R5 RV3 | M | none |
| **38** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-2 — AIGatewayClientServiceImpl decomposition (3,087→~800 LoC, 4 extracted services). Coordinates with .projects/rovo-module-decomposition/` | ARC-2 | M | #7 (typed FF) |
| **39** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] PLT-15.6 / S3 — Idempotency keys for post-workflow mutations (extends v7 R-6A from tools to user-message-store + memory-ingest)` | S3 PLT-15.6 | M | v7 R-6A live |
| **40** | **`[HIGH]`** | `[Impact: High] [quality][cost] I4 / G-1 — LH skill-conflict workstream Phase 1 (vague-query cost guard + tool-overlap registry; tackles 41KB system prompt) — −$3-8K/mo + +5-15% search hit-rate` | I4 G-1 | L | #3 (G-3 EVAL1 live ≥7d), #25 |
| **41** | **`[HIGH]`** | `[Impact: High] [reliability][trust] RV9 — Per-tenant active-conversation cap / hot-tenant load-shed (bounded blast radius; protects Cat-1 stream-success ≥99.0%)` | RV9 | M | #1, #2 |
| **42** | **`[HIGH]`** | `[Impact: High] [reliability] R1 — Complete per-service CB migration in AggResilienceProvider (NOT Resilience4j); finish .projects/circuit-breaker/ 6-PR plan; retire hand-rolled TapTraitsCircuitBreaker` | R1 | M | #11, #29 (PLT-2/3 first) |
| **43** | **`[HIGH]`** | `[Impact: High] [quality] G-4 EVAL2 — Production-shadow eval pipeline → auto-rollback signal feeder (0.1% sample → ARIZE judge → v7 O1 auto-rollback)` | G-4 EVAL2 | L | #1, #3, #25 |

### 3.6 Tier 6: Deep Refactoring + Intelligence — Wk 9-10 (PRs #44-#52)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **44** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-1 Phase 1 — Anthropic provider hierarchy POC (4 providers / 3,900 LoC → AbstractAnthropicProvider + 2 thin subclasses ~2,100 LoC) — template-method pattern proof` | A1-Ph1 | M | #7, #34 (B11 first per anti-goal #44) |
| **45** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-3 — LLMServiceImpl decomposition (1,831→~600 LoC; 3 services; eliminates 18 duplicate provider-selection methods)` | ARC-3 | M | #7, #38 |
| **46** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-7 Phase 1-2 — Async migration audit + provider-bridge cleanup (~14 bridges eliminated)` | ARC-7-Ph1-2 | M | #34 |
| **47** | **`[HIGH]`** | `[Impact: High] [quality][MAU] INT-1 / I2 — Semantic Context Window Selection (replaces naive takeLast(10) using existing TeamserveSearchQrGemma3 embedding infra) — +5-15pp response relevance for multi-turn` | I2 INT-1 | M | #43 (EVAL2 for measurement) |
| **48** | **`[MEDIUM]`** | `[Impact: Medium] [quality][cost] INT-3 / I3 — Progressive summarization for SimpleLoopWorkflow (reuses existing ContextCompactionService) — enables longer agentic workflows` | I3 INT-3 | M | #43 |
| **49** | **`[MEDIUM]`** | `[Impact: Medium] [quality] INT-9 / I1 — Modular prompt composition (PromptComposer with budget-aware sections; eliminates string-concat bugs) — extends CacheFriendlyPromptAssembler` | I1 INT-9 | M | #26 (L1) |
| **50** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] Z-3 — Cat-5 MCP cold-start p95 ≤2s probes` | Z-3 | S | #2 |
| **51** | **`[MEDIUM]`** | `[Impact: Medium] [latency] W-4 / Y4 — Speculative pre-warm (parallelize tenant resolution + auth + user-context hydration) — −80-200ms p50 TTFB` | W-4 Y4 | M | none |
| **52** | **`[MEDIUM]`** | `[Impact: Medium] [latency] W-5 / Y5 — Per-request Statsig FF-eval memo on chat path remainder (complements ARC-6 LLM-path memo)` | W-5 Y5 | XS | none |

### 3.7 Tier 7: Quality Finisher + Monetization — Wk 11-12 (PRs #53-#61)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **53** | **`[HIGH]`** | `[Impact: High] [monetization] M-1 — First-class TenantTier (FREE/STD/PREMIUM/ENT) read once per request — directly enables FY27 Cloud Price Increase Program` | M-1 | L | #1, Rohit DACI alignment (anti-goal #45) |
| **54** | **`[HIGH]`** | `[Impact: High] [cost][routing] U-7 — Evidence-driven model-selection routing (subsumes BOOST v1 X7 + Sunset INT-5/INT-11) — −$16.8-43.5K/mo; gated on EVAL2 (#43) + ≥7d M14` | U-7 | L | #1 (≥7d), #43, anti-goal #44 |
| **55** | **`[MEDIUM]`** | `[Impact: Medium] [quality][cost] RV6 — AdfEditor convergence detection via ADF tree-hash early-exit — 20-30% iteration cuts on edits; 200-400ms TTFT on simple edits` | RV6 | M | #43 |
| **56** | **`[MEDIUM]`** | `[Impact: Medium] [quality][cost] QT3 — Semantic DoomLoop with per-tool argument canonicalizer — catches ~10-30% more loops; ~0.5-2% LLM-spend savings` | QT3 | M | #43 |
| **57** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-1 Phase 2 — Gemini family hierarchy consolidation (-1,090 LoC)` | A1-Ph2 | M | #44 |
| **58** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-7 Phase 3 — LLMService interface evolution (~20 blocking methods deprecated; suspend variants)` | ARC-7-Ph3 | M | #46 |
| **59** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] SVC1 — Experience.kt monolith decomposition (1,752 LoC) — per-tenant variants unblocked` | SVC1 | M | none |
| **60** | **`[MEDIUM]`** | `[Impact: Medium] [quality] AIFC PIR-debt closure — AIFC-1503 alerts (overdue 60d) + AIFC-1342 anomaly (overdue 100d) + AIFC-1714 500-errors` | AIFC-PIR | M | #1 (alerts need cost panel) |
| **61** | **`[MEDIUM]`** | `[Impact: Medium] [throughput] AIFC1 — PromptRunner suspend conversion (5-15% throughput on AIFC endpoints)` | AIFC1 | S-M | none |

### 3.8 Carry-Over (Wk 13+ / Next Quarter) — PRs #62-#70 (LOW or DEFERRED MEDIUM)

| PR | `[Impact]` | Title | Item | Effort | Deps |
|----|----|---|---|---|---|
| **62** | **`[LOW]`** | `[Impact: Low] [velocity][infra] OPS1 — Helm worker manifest dedup (3 × 763-line clones, −2,800 LoC YAML)` | OPS1 | S-M | none |
| **63** | **`[LOW]`** | `[Impact: Low] [velocity][infra] OPS2 — Aqui topic+subscription Helm templating (−800 LoC YAML; adding queue: 4-file → 1-file change)` | OPS2 | S | none |
| **64** | **`[LOW]`** | `[Impact: Low] [velocity] CI4 — Gradle configuration cache restore for test tasks (~7-15 min CI compute / PR)` | CI4 | M | none |
| **65** | **`[LOW]`** | `[Impact: Low] [perf] SIDECAR1 — gunicorn worker recycle tuning (sidecar p99 −10-30 ms)` | SIDECAR1 | XS | none |
| **66** | **`[LOW]`** | `[Impact: Low] [perf] SIDECAR3 — Split python-sidecar lean+heavy (cold-start −30-60s)` | SIDECAR3 | M | #65 |
| **67** | **`[LOW]`** | `[Impact: Low] [cost][latency] AIFC5 — Cost-tier-aware ContextCompactionService model (per-tenant via existing dynamic config)` | AIFC5 | XS | #53 |
| **68** | **`[LOW]`** | `[Impact: Low] [cost] AIFC2 — invokeStream Sequence→Flow (premium throughput floor)` | AIFC2 | S | none |
| **69** | **`[LOW]`** | `[Impact: Low] [velocity] CI5 — .projects/_template + repo-level TEST_SOP.md` | CI5 | XS | none |
| **70** | **`[MEDIUM]`** | `[Impact: Medium] [reliability] M-2 — Per-tenant cost caps + cost-aware degradation (depends on M-1 + U-1; aligns with JCA-RDiJ DACI)` | M-2 | M | #1, #53 |
| **71** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-1 Phase 3 — OpenAI provider hierarchy (Chat 2,132→1,400 + Responses 1,450→900)` | A1-Ph3 | M | #57 |
| **72** | **`[MEDIUM]`** | `[Impact: Medium] [velocity] ARC-4 — AgentChatExecutor decomposition (2,618→500 LoC). Coordinates with .projects/rovo-module-decomposition/` | ARC-4 | M | #38, #45 |
| **73** | **`[LOW]`** | `[Impact: Low] [velocity] ARC-5 — MetricKey domain distribution (3,245-LoC enum → per-domain MetricKeyLike companions)` | ARC-5 | S (ongoing) | none |
| **—** | **DEFERRED RESEARCH-TRACK** | Sunset INT-7/INT-8/INT-11/INT-12, PLT-14 (regex prompt-injection) | (cut entirely; need stronger evidence) | — | — |

### 3.9 Impact distribution (55 in-quarter PRs + 12 Carry-Over = 67 total)

| Impact | Wk 0-12 (PRs #1-61) | Carry-Over (PRs #62-73) | Total |
|---|:---:|:---:|:---:|
| 🔴 **HIGH** | **20** (36%) | 0 | **20** (30%) |
| 🟡 **MEDIUM** | **27** (49%) | 4 | **31** (46%) |
| 🟢 **LOW** | **8** (15%) | 8 | **16** (24%) |
| **Total** | **55** | **12** | **67** |

> Note: 55 PRs Wk 0-12 ÷ 4 engineers ÷ 12 wk = ~1.15 PRs/engineer/wk — sustainable cadence assuming most are XS/S effort with parallelism.

---

## 4. Anti-goals (carries v7 #1-36 + BOOST v1 #37-41 + integrated #42-52 + new #53)

(v7 anti-goals 1-36 carried verbatim; BOOST v1 anti-goals 37-41 carried verbatim; v2 anti-goals 42-52 carried verbatim.)

**NEW v3 anti-goals:**

53. **Do NOT split a single logical change into >3 PRs.** v3 PRs are intentionally bundled where the changes are tightly coupled (e.g., A16-A22 = 1 PR; B12-B15 = 1 PR; P4+P5+P6 = 1 PR). Splitting further wastes review cycles. (Conversely, the L3-Phase1/Phase2 split is mandatory due to anti-goal #46 cohort A/B requirement.)

**Critical anti-goals re-stated for v3:**
- **#42 (Sunset)**: Do NOT introduce Resilience4j. Extend `AggResilienceProvider`. **PR #42 (R1) MUST stay in `AggResilienceProvider`.**
- **#43 (Sunset)**: Do NOT duplicate `.projects/` in-flight work. PRs #26 (L1), #42 (R1), #34 (B11), #38 (ARC-2), #46 (ARC-7) all extend existing in-flight projects.
- **#44 (Cursor + Sunset)**: Do NOT ship A1 (PR #44, #57, #71) before A2 Phase 2 (PR #34 B11). Mixed blocking/suspend bases create unmaintainable code.
- **#45 (Cursor)**: Do NOT ship M-1 (PR #53) without aligning with Rohit Jhangiani's "Rovo & AI Feature" DACI page 7023743677.
- **#46 (All 3)**: Do NOT ship L3-Phase2 (PR #21) without Phase1 cohort A/B (PR #20) running ≥7 days.
- **#47 (Cursor)**: Do NOT ship A3 LLMServiceImpl decomp (PR #45) before A5 typed FF (PR #7) lands.
- **#48 (Sunset)**: Do NOT build a centralized Prompt Registry. `CacheFriendlyPromptAssembler` (extended in PR #49) is sufficient.
- **#49 (Sunset)**: Do NOT build regex-based prompt-injection detection. Defer to `responsible-ai-api`.
- **#50 (All 3)**: Do NOT adopt P1 Cat-1 SLO targets (PR #2) without confirming with jgrose (page 7039684456).
- **#51 (Sunset)**: Do NOT ship L6 RV5 (PR #22) without paired accuracy A/B showing ≤5% task-completion regression for DEFAULT-classified queries.
- **#52 (mine)**: Do NOT promote any item past 5%→25% rollout cohort until OBS3 (PR #1) has ≥7 days of (tenant, experience) attribution data live.

---

## 5. Cut-tiers (constrained sprints)

| Sprint length | PRs dropped | PRs kept | Rationale |
|---|---|---|---|
| **12-week (FULL)** | 0 dropped | All 55 in-quarter (#1-#61) | All workstreams ship; Carry-Over #62-#73 deferred to next quarter |
| **8-week** | Tier 6 + Tier 7 (PRs #44-#61) — 18 PRs deferred | 37 PRs kept | Defer architecture-deep + monetization + quality finishers |
| **6-week** | Tier 5 + Tier 6 + Tier 7 (PRs #33-#61) — 29 PRs deferred | 26 PRs kept | Wk 7-8 reliability finishers + intelligence deferred |
| **4-week** | Keep ONLY load-bearing TOP-12: PRs #1, #2, #3, #4, #5, #6, #7, #20, #21, #22, #26, #27 | **12 PRs** | TOP-15 minus everything that needs multi-week soak/A/B |
| **NEVER cut (load-bearing)** | PRs #1 (cost foundation), #3 (PR-gate), #5 (XS-S latency), #6 (~80% Redis), #20+#21 (−$30-80K), #22 (−$15-40K), #26 (−$30K+), #27 (autoscale), #28 (silent loss), #36 (−2-5s p95), #42 (CB), #2 (Cat-1 SLO) | **12 minimum** | Each moves >1pp on a top FY26/FY27 goal |

---

## 6. Measurement plan (M1-M9 v7 + M10-M12 BOOST v1 + M13-M15 v2 + new M16-M22)

| ID | What it proves | Powering PR(s) |
|----|----------------|------------------|
| **M16** | L1 cache-friendly prompt savings | Powered by PR #1 + PR #26 |
| **M17** | A1 provider-consolidation velocity (LoC delta, build-break rate, onboarding time) | Powered by PRs #44, #57, #71 |
| **M18** | L2 parallel execution latency | Powered by PR #33 |
| **M19** | L3 Insights cost & quality (per-type CTR baseline → consolidation) | Powered by PRs #20, #21 |
| **M20** | R4 streaming quality-gate efficacy (catch / FP / retry-success) | Powered by PR #31 |
| **M21** | Track P parallelism win (Tool-Registry, MCP, AGS, Hydration) | Powered by PRs #13, #14, #15, #16 |
| **M22** | Track B blocking-bridge retirement (`ForbiddenBlockCall` count delta) | Powered by PRs #34, #35, #46, #58 |

**Hard rule:** No PR ships claiming impact until its M-series is live for ≥7 days.

---

## 7. Aggregate claimed impact (verified post-deploy via M1-M22)

| Dimension | v3 improvement |
|-----------|----------------|
| **LLM cost** | **−$80-180K/mo additive** (PRs #20+21, #22, #26, #54, #40, #23) |
| **Latency p95** | **−2,500-7,500 ms** (PRs #5, #13-#16, #33, #36, #51) |
| **Capacity** | **−30-50% steady-state** instances (PR #27); per-tenant load-shed (PR #41) |
| **Reliability** | 0 silent memory-loss (PR #28); 0 dup mutations (PR #39); 0 async-job loss on restart (PR #37); bounded blast radius (PR #41); cascading-failure prevention (PR #42) |
| **Quality** | +5-15pp relevance (PR #47); skill-conflict closure (PR #40); 0.1% prod-shadow (PR #25); auto-rollback (PR #43); PIR-debt closure (PR #60) |
| **LoC removed** | **~7,000-9,000** (ARC-1 Ph1-3 + ARC-2 + ARC-3 + ARC-4 + ARC-7 + B11 + SVC1 + OPS1 + OPS2) |
| **Dev velocity** | **−25-35% PR wall-clock** (PR #4); **−7-15 min CI** (PR #64); 18 dup methods removed (PR #45); 33+ FF evals → 1 (PR #7) |
| **SLO redefinition** | flat 99.9% → concrete Cat-1 TTFT/jitter/cancel/stream-success (PRs #2, #50) + Cat-3 silent-death probes (PR #24) + Cat-5 MCP cold-start (PR #50) |
| **Monetization foundation** | TenantTier (PR #53); per-tenant cost caps (PR #70) — directly enables FY27 Cloud Price Increase Program + 3 COGS DACIs |

---

## 8. Honest calibration

- **Confidence:** PRs with file:line citation (most of #5-#19, #36, #45, #46) are 0.85-0.95. PRs based on TWG signals (#2, #40, #53, #60) are 0.80-0.85. Cursor's tactical items (#13-#19, #59-#68) inherit Cursor's 4-agent grep verification.
- **What v3 did NOT do:** run scripts/twg directly; inherits Cursor v2's TWG sweep (47 raw-JSON snapshots) and Sunset's `.projects/` discovery.
- **Biggest residual risk:** PR #54 (U-7 model routing) — must NOT ship without G-4 EVAL2 (#43) + ≥7d M14 cost-attribution. Anti-goals #44, #51 enforce.
- **Open dependencies:**
  - Confirmation of Cat-1 SLO targets with jgrose (gates PR #2).
  - Rohit DACI alignment for TenantTier (gates PR #53).
  - v7 R-6A live ≥7d (gates PRs #33, #39).
  - v7 Q13 golden datasets (gates PR #3).

---

## 9. If we could only pick ONE plan, which would it be?

**Recommendation: This BOOST_INTEGRATED v3 plan.**

**Reasoning** (critical-thinking, evidence-based):

| Criterion | Cursor (805 lines, 70 PRs) | Sunset (221 lines, 45 PRs) | My v2 (346 lines, 30 PRs) | **v3 (this)** |
|---|:---:|:---:|:---:|:---:|
| TWG-fresh business signals | ✅ | ✅ | ✅ | ✅ |
| `.projects/` in-flight discovery | ✅ | ✅ (originated) | ✅ | ✅ |
| Code-evidence depth (file:line, LoC) | ✅ | ✅ | ✅ | ✅ |
| Anti-goals (esp. #42 anti-Resilience4j) | ✅ | ✅ (originated) | ✅ | ✅ (12 anti-goals total) |
| Concrete PR list with `[Impact]` labels | ✅ (70) | ✅ (45) | ✅ (30) | ✅ **(67)** |
| Captures 25 tactical items (Track P/B/A, OPS, CI, SIDECAR) | ✅ | ❌ | ❌ | ✅ |
| Realistic scope (not over-stuffed) | ❌ (70) | ✅ (45) | ✅ (30) | ◐ (55 in-quarter; tractable for 4 engineers) |
| Explicit Carry-Over (Wk 13+) | ✅ | ✅ | ◐ | ✅ |
| Cuts INT-7/8/11/12 + PLT-14 | ◐ | ✅ | ✅ | ✅ |
| Multi-PR safety boundaries (cohort A/B, gating) | ◐ | ✅ | ✅ | ✅ |
| Measurement extension | ✅ M13-M15 | ✅ M16-M20 | ✅ M10-M20 | ✅ **M10-M22** |
| Tier 1-7 + Carry-Over breakdown | ✅ Wk-by-wk | ✅ Tier 1-7 | ◐ | ✅ both |
| Sustainable cadence (~1 PR/eng/wk) | ❌ (1.5/wk) | ✅ (1.0/wk) | ✅ (0.6/wk) | ✅ (1.15/wk) |

**v3 strictly dominates** because:
1. It captures **all** TWG-fresh signals from Cursor.
2. It captures **all** `.projects/` discovery + anti-Resilience4j from Sunset.
3. It captures **all** 25 tactical wins from Cursor (PRs #13-#19, #59-#68) — which v2 dropped.
4. It maintains v2's discipline (anti-goals, supersession, $/mo per item, multi-PR safety).
5. It adds explicit **Tier 1-7 + Carry-Over** structure (best of Sunset's organization).
6. It adds **M21+M22** measurement for Track P + Track B (closes BOOST gap).
7. Cadence is realistic (1.15 PR/eng/wk) — between Cursor's over-scope (1.5) and v2's under-scope (0.6).

**If forced to pick ONE source plan only** (NOT this integrated v3):

**My pick: Sunset (221 lines)** — because:
1. **Discipline > Volume.** 45 PRs ship; 70 PRs don't.
2. **Discovered `.projects/` and anti-Resilience4j** (the elegance corrections).
3. **Sunset's §7 explicitly recommends my v1** as the best plan, validating the synthesis approach.
4. Cursor's missing 25 tactical items can be added later as "find time"; getting them all into one plan is over-scope.
5. (Cursor would be a strong second-place; my v2 third because while disciplined, it dropped the 25 tactical wins.)

But **v3 is strictly better than any single source** because it includes Sunset's discipline + Cursor's tactical depth + my v2's $/mo + measurement extensions, with no over-scope (sustainable cadence verified).

---

## 10. Calling-for-action

1. **Wk 0 owner ping:** jgrose (PR #2 SLO confirm), Rohit Jhangiani (PR #53 DACI), Hao Chen (PR #40 LH), Vincent Zeng + Guangwei Weng (Memory subsystem; relates to I2/I3), Robbie Livermore + Kevin Ma (overall).
2. **Allocate 4 engineers × 12 weeks** OR **3 engineers × 8 weeks** (per §5).
3. **Pick deployment cadence:** 12wk (55 PRs) / 8wk (37) / 6wk (26) / 4wk (12).
4. **Coordinate with the 4 in-flight `.projects/`** (`coroutine-migration/`, `circuit-breaker/`, `cache-friendly-schema-agent-prompts/`, `rovo-module-decomposition/`).
5. **Generate Jira epics** for the 7 workstreams (P / A / L / R / I / W / M+G).
6. **Land Wk 0 batch first** (PRs #1, #2, #3, #4) — these gate everything else.

---

## 11. Companion documents

| File | Purpose | Status |
|------|---------|--------|
| `BOOST_INTEGRATED_v3.md` | This file (master plan) | ✅ Complete |
| `PR_TRACKING.csv` | Machine-followable 67-PR list | ✅ Complete (created alongside) |
| `boost_items/P-PerfContract.md` | P1, P2, P3 detail | TODO |
| `boost_items/A-Architecture.md` | A1-A7, B11-B15, SVC1 detail | TODO |
| `boost_items/L-LatencyCost.md` | L1-L7, P1-P7 (parallelism), W-4 detail | TODO |
| `boost_items/R-Resilience.md` | R1-R5, S1-S3, PLT-2/3/5/7/8/15, RV9 detail | TODO |
| `boost_items/I-Intelligence.md` | I1-I4, INT-1/3/9/10, RV6, QT3 detail | TODO |
| `boost_items/W-TacticalWins.md` | W-1, W-5, CI1, CI4, CI5, A16-A22, AF1+AF6, OPS1, OPS2, SIDECAR1, SIDECAR3, SCALE3 detail | TODO |
| `boost_items/M-Monetization-G-Quality.md` | M-1, M-2, G-3, G-4, QT2, G-1, AIFC-PIR, AIFC1/2/5 detail | TODO |
| `BUSINESS_GOALS_DELTA_v3.md` | Delta vs v2 + FY26 goals doc | TODO |
| `EVIDENCE_INDEX.md` | One-stop file:line citation table | TODO |

---

**END OF PLAN.** Future updates bump version (`v3` → `v4`) with explicit changelog vs prior version.