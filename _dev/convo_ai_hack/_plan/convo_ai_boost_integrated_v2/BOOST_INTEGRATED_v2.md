# Convo AI Platform — BOOST Integrated Plan **v2**

**Status:** PROPOSED &nbsp;•&nbsp; **Date:** 2026-05-15 07:20 &nbsp;•&nbsp; **Author:** Tony Chen (synthesis-of-synthesis)
**Repo:** `atlassian/conversational-ai-platform` &nbsp;•&nbsp; **Supersedes:** BOOST_INTEGRATED_v1.md (mine), `convai-boost-v2_4ce55218.plan.md` (Cursor), `can-you-create-a-serene-sunset.md` (Claude)

> **TL;DR.** Three candidate plans now exist (Cursor BOOST v2 = 60-item TWG-anchored; Sunset Integrated v3 = 22-item `.projects/`-coordinated; my INTEGRATED v1 = 41-item middle-ground). All three are themselves integrations of each other. This **v2** is the *fourth* integration, and is the elegant proper plan: **24 items in 6 workstreams, with a concrete 30-PR list ranked by impact**. It honors the elegance constraint (no hacks, no ad-hoc), the freshness constraint (TWG signals from 2026-05-15), and adds the discovery missed by the others (`.projects/` in-flight work coordination).

---

## 0. What's new in v2 (vs v1)

The other agents iterated on their plans in the last 90 minutes, **producing critical findings my v1 missed**:

### 0.1 New evidence merged into v2

| Finding | Source plan (latest) | Why critical |
|---|---|---|
| **`.projects/` in-flight workstream discovery** (4 active: `coroutine-migration/`, `circuit-breaker/`, `cache-friendly-schema-agent-prompts/`, `rovo-module-decomposition/`) | Sunset v3 §1 | My v1 didn't see these. Several v1 items are partial duplicates and would have been wasted work. |
| **Anti-goal: do NOT introduce Resilience4j** | Sunset v3 §9.42 | The platform already uses `AggResilienceProvider` actively. My v1's PLT-1 was wrong; v2 redesigns as **R1 (extend `AggResilienceProvider`)** instead. |
| **TWG-fresh business signals** confirmed in both A & B (FY27 Cat-1 Perf Contract; Extension MAU at-risk; CMI 2.0; AIFC PIR debt; 3 COGS DACIs; LH skill-conflict; GPT-4.1↔GPT-5 decision) | Cursor v2 §0 + Sunset v3 §0 | Anchors v2 to current reality (FY27), not stale FY26 framing |
| **Cursor v2's CI1 (-25-35% PR wall-clock) and B11 (16-provider blocking-bridge retirement)** | Cursor v2 §3 #9, #19 | My v1 missed both. CI1 unblocks dev velocity; B11 is the keystone of A2 async migration. |
| **Cursor v2's RV3 (AsyncAgentJobStore persistence) and RV9 (per-tenant hot-tenant load-shed)** | Cursor v2 §3 #10, #12 | Both are concrete TODO closures with reliability impact my v1 omitted. |
| **Sunset's explicit cuts of INT-8 / INT-12 / PLT-14 / PLT-6** with rationale | Sunset v3 §12 | My v1 deferred them; Sunset proves they should be cut entirely (false-positive risk, premature, over-engineered). v2 follows Sunset. |

### 0.2 What v2 cuts vs my v1

| v1 item | Status in v2 | Why |
|---|---|---|
| **PLT-1 (introduce Resilience4j)** | **CUT, REDESIGNED as R1** | Anti-elegant — platform already uses `AggResilienceProvider`. Extend, don't replace. (Sunset anti-goal #42) |
| **PLT-6 (L1+L2+L3 cache hierarchy)** | **DEFERRED to next quarter** | Over-engineered for current scale; invalidation complexity. (Sunset cut rationale §12) |
| **ARC-2 (AIGatewayClientServiceImpl 3,087→800)** | **DEFERRED to wk 13+** | Lower priority than ARC-3 LLMServiceImpl decomp; coordinate with `rovo-module-decomposition/`. (Sunset cut §12) |
| **ARC-4 (AgentChatExecutor 2,618→500)** | **DEFERRED, coordinate with `rovo-module-decomposition/`** | 2,618 LoC stable; should land via existing in-flight workstream, not BOOST. (Sunset cut §12) |
| **INT-7 (inter-agent context sharing)** | **CUT** | Speculative; needs evidence the surface area is needed. (Sunset cut §12) |
| **INT-8 (centralized prompt registry)** | **CUT** | `CacheFriendlyPromptAssembler` + Pebble + Statsig sufficient. (Sunset anti-goal #47) |
| **INT-11 (quality-based dynamic model routing)** | **DEFERRED** | Depends on G-4 EVAL2 data; speculative without quality gate proven. (Sunset cut §12) |
| **INT-12 (adaptive response strategy)** | **CUT** | Multi-quarter R&D, unproven ROI. (Sunset cut §12) |
| **PLT-14 (regex prompt-injection detector)** | **CUT** | Defer to `responsible-ai-api` team; regex has well-documented FP problems. (Sunset anti-goal #48) |
| **MON3 (per-tool credits)** | **CUT** | Premature; Rovo Credits pricing model not finalized. (Sunset cut §12) |

### 0.3 What v2 keeps from v1 unchanged

`U-1` (OBS3), `U-2` (INS1), `U-3` (OPS3), `U-4` (RV5), `U-5` (AIFC7), `W-1` (Y1 SSE preamble), `W-2` (R23 hydratePool), `W-3` (Y3 parallel tools), `G-3` (EVAL1), `G-4` (EVAL2), `Z-1`/`Z-2`/`Z-3` (Cat-1/3/5), `M-1` (TenantTier), `PLT-15` (silent failure), `PLT-15.5` (DLQ), `PLT-15.6` (idempotency), `PLT-11.5` (saturation gauge), `INT-1` (semantic context), `INT-3` (progressive summarization), `INT-9` (PromptComposer), `INT-10` (quality gate). All anti-goals 42-48 carried forward, plus 2 new from Sunset.

---

## 1. v2 final structure: 6 workstreams, **24 items**, **30 PRs**

| WS | Code | Items | Goal anchor | Net delivered |
|---|---|---|---|---|
| **P** — Perf Contract & Observability | 3 | P1 (Z-1), P2 (Z-2), **P3 = OBS3** (U-1) | FY27 Cat-1/3/5 SLO + cost foundation | Cat-1 SLO compliance; **(model, exp, tenant) cost panel** |
| **A** — Architecture (gated by `.projects/`) | 4 | **A1** (provider hierarchy), **A2** (async-bridge retirement), **A3** (LLMServiceImpl decomp), **A5** (typed FF + req-scoped memo) | Dev velocity + Reliability | **−5,400+ LoC** + 18 dup methods removed |
| **L** — Latency & Cost (highest $) | 7 | **L1** (cache-friendly prompts, completes `.projects/cache-friendly-schema-agent-prompts/`), **L2** (parallel tools then subagents), **L3 = INS1** (U-2), **L4** (N+1), **L5** (ERS push-down), **L6 = RV5** (U-4), **L7 = AIFC7** (U-5) | Cost + Latency | **−$75-150K/mo** + −500-2,500ms p95 |
| **R** — Resilience (extends `.projects/circuit-breaker/`) | 5 | **R1** (complete CB migration in existing `AggResilienceProvider`), **R2** (standardized retry: 6 patterns→1), **R3 = OPS3** (autoscale), **R4** (streaming quality gate), **R5 = RV3** (AsyncAgentJobStore persistence), plus carry of `S1` DLQ, `S2` saturation gauge, `S3` idempotency | 99.85% SLO + Trust | 0 silent loss; bounded blast radius; cascading-failure prevention |
| **I** — Conversation Intelligence | 4 | **I1** (PromptComposer; extends L1 assembler), **I2** (semantic context window), **I3** (progressive summarization), **I4** (skill-conflict / G-1) | AIFC quality + MAU | +5-15pp relevance + −$3-8K/mo vague-query |
| **W** — Tactical quick wins | 1+ batched (CI1, B11, R23-as-W-2, W-1 SSE preamble, W-5 FF memo) | DevVel + TTFB | **−25-35% PR wall-clock**, −500ms-2s p95 history-resume |
| **M** — Monetization | 1 | **M1 = MON1** (TenantTier first-class) | Monetization & FY27 Cloud Price Increase Program | Foundation for premium-only Opus, per-tier rate limits |

**Grand total:** **24 unique items** delivered as **30 PRs** (some items decompose into 2-3 stacked PRs for safe rollout). See §3 for the PR-level table.

---

## 2. TOP-15 items (ranked by goal-impact × confidence ÷ effort)

| # | ID | Item | Quantified impact | Conf | Effort | Risk | Source consensus |
|---|----|------|---------------------|------|--------|------|--------------------|
| 1 | **P3** = OBS3 | Real-time `(model, experience, tenant)` cost panel | Enabling keystone — unblocks L3, L6, L7, M1, R3, EVAL2 | 0.95 | M | Low | All 3 (top-1) |
| 2 | **L3** = INS1 | Consolidate 6-conv Insights → 1 structured-output call | **−$30-80K/mo** (single largest unclaimed lever) | 0.85 | M | Med (cohort A/B mandatory) | All 3 |
| 3 | **L1** | Cache-friendly prompt structure (completes `.projects/cache-friendly-schema-agent-prompts/`) | **−$30K+/mo**; prompt-cache hit rate 3-5× | 0.9 | M | Low (extends in-flight) | Sunset v3 |
| 4 | **R3** = OPS3 | HOT-301423 tomcat-thread + queue-depth autoscaling | **−30-50% steady-state instance count**; closes known TODO | 0.9 | M | Med (perfhammer-gated) | Cursor + mine |
| 5 | **W-2** = R23 | Split `hydratePool=2` web Jsoup pool from history hydration pool | **−500ms-2s p95** on history-heavy resume; silent serialization fix | 0.95 | XS-S | Low | Cursor + mine |
| 6 | **L6** = RV5 | Adaptive Marathon iteration cap via `QueryComplexityService` | **−$15-40K/mo**; mean iters −50% on simple queries | 0.85 | S | Med | All 3 |
| 7 | **A1** | LLM Provider Hierarchy + consolidation (template-method, 25 providers / 14,660→6,200 LoC) | **−4,170 LoC**; faster onboarding; gated by A2 Phase 2 | 0.85 | L | Low | All 3 |
| 8 | **A2** | Async migration: blocking-bridge retirement (607 sites, 4-phase) | Thread-pool relief; subsumes B11; coordinates with `.projects/coroutine-migration/` | 0.9 | L | Med (existing project rules) | All 3 |
| 9 | **R1** | Complete per-service CB migration in **existing `AggResilienceProvider`** (NOT Resilience4j) | Cascading-failure prevention; 13 integrations covered | 0.85 | M | Low | Sunset v3 (corrects v1 mistake) |
| 10 | **G-3** = EVAL1 | PR-gate eval harness on Goldens-300 | Catches AIFC quality regressions pre-merge | 0.85 | M | Low (depends on v7 Q13 datasets) | All 3 |
| 11 | **L2** | Parallel tool execution (Phase A) → parallel subagent execution (Phase B) | **−500-2,000ms p95** multi-tool turns; gated on R-6A live ≥7d | 0.85 | M | Low (gated) | All 3 |
| 12 | **P1** = Z-1 | FY27 Cat-1 Perf Contract SLO instrumentation (TTFT/jitter/cancel/stream-success) | Replaces flat 99.9% with concrete user-perceptible SLOs | 0.9 | M | Low (after jgrose confirms) | Cursor + mine |
| 13 | **L4** | N+1 elimination in `ConversationHistoryItemManagerImpl` lines 529-552, 554-579, 581-604 | **−50-80% Object Store calls; −2-5s p95** large-history conv | 0.95 | M | Low | All 3 |
| 14 | **A5** | Typed Dynamic Config + RequestScopedLLMFlags (33+ Statsig evals → 1) | **−20-50ms p95**; deterministic per-request flag resolution | 0.9 | S | Low | All 3 |
| 15 | **I4** = G-1 | LH skill-conflict / tool-disambiguation (41KB system prompt drain, vague-query guard) | Closes AIA-1998 class; **−$3-8K/mo**; +5-15% search hit-rate | 0.85 | L | Med | Cursor + mine |

**Below-TOP-15 (still in plan):** L5 (ERS push-down), L7 (AIFC7 MCP cache key), R2 (retry standardization), R4 (streaming quality gate), R5 (RV3 AsyncAgentJobStore), I1 (PromptComposer), I2 (semantic context), I3 (progressive summarization), W-1 (SSE preamble), W-5 (FF memo), CI1 (CI shard collapse), B11 (folded into A2), M1 (TenantTier), G-4 (EVAL2), P2 (Cat-3 silent-death probes), S1 / S2 / S3 (DLQ / saturation / idempotency).

---

## 3. Concrete 30-PR list — ranked, prioritized, with `[Impact: H/M/L]` labels

> **Methodology:** Each item from §2 is decomposed into 1-3 PRs along stacked-deploy boundaries. Impact label uses BOOST v1's calibration: **HIGH** = concrete user-perceptible win OR prevents user-visible failure mode OR foundational infra unblocking measurement of others; **MEDIUM** = measured aggregate win not single-request-perceptible OR conditional value; **LOW** = micro-optimizations, code-quality, measurement-only counters.

### 3.1 PR list — sequenced for stacked-deploy safety

| # | PR title (proposed) | Item | Workstream | Impact | Stacked-on | Goal anchor |
|---|---------------------|------|------------|:--------:|--------------|---------------|
| 1 | `[Impact: High] [observability] P3 — Real-time (model, experience, tenant) cost metric (foundation)` | P3 OBS3 | P | 🔴 H | none | Cost foundation |
| 2 | `[Impact: High] [observability] P3 follow-up — per-experience cost panel + tenant-budget-overrun alarm <1min` | P3 OBS3 | P | 🔴 H | PR #1 | Cost foundation |
| 3 | `[Impact: High] [perf-contract] P1 — Cat-1 Perf Contract instrumentation (TTFT/jitter/cancel/stream-success histograms)` | P1 Z-1 | P | 🔴 H | none | FY27 SLO |
| 4 | `[Impact: High] [reliability][reliability-eval] G-3 — PR-gate eval harness on Goldens-300 (EVAL1)` | G-3 | I | 🔴 H | none | Quality |
| 5 | `[Impact: High] [latency] W-2 — Split hydratePool=2 web-Jsoup pool from history hydration pool (R23)` | W-2 R23 | W | 🔴 H | none | Latency / MAU |
| 6 | `[Impact: High] [latency][cost] L7 — Drop accountId from MCP schema cache key (~80% Redis savings, AIFC7)` | L7 AIFC7 | L | 🔴 H | none | Cost (Redis) |
| 7 | `[Impact: Medium] [latency] A5 — Typed Dynamic Config + RequestScopedLLMFlags (33+ FF evals → 1)` | A5 | A | 🟡 M | none | Latency |
| 8 | `[Impact: Medium] [latency] W-1 — SSE event:ack preamble for /ChatV1Controller streaming endpoints` | W-1 Y1 | W | 🟡 M | none | TTFB |
| 9 | `[Impact: Medium] [reliability] PLT-15 — Silent failure remediation in ConversationStateManagerImpl:86-94 (counter + 1-retry)` | PLT-15 | R | 🟡 M | none | Trust |
| 10 | `[Impact: Medium] [reliability] S2-Phase1 — Concurrent-conversation saturation gauge (RovoChatService:207, metric-only)` | S2 | R | 🟡 M | none | Trust |
| 11 | `[Impact: Low] [perf] PLT-2-equivalent — TokenBucketRateLimiter spin-wait → AggResilienceProvider RateLimiter` | PLT-2 | R | 🟢 L | none | CPU |
| 12 | `[Impact: Medium] [reliability] R2 — Standardized retry patterns (6 patterns → 1: ConvoAiRetryPolicy enum)` | R2 | R | 🟡 M | none | Reliability |
| 13 | `[Impact: Medium] [reliability] R4 — Streaming quality gate (heuristic; uses TextGenerationRequest.fallbackModel)` | R4 | R | 🟡 M | none | Quality safety net |
| 14 | `[Impact: High] [cost] L6 — Adaptive Marathon iteration cap via QueryComplexityService (RV5)` | L6 RV5 | L | 🔴 H | PR #1 (P3 cost metric live ≥7d) | Cost |
| 15 | `[Impact: High] [cost][quality] L3-Phase1 — Insights cohort A/B harness (per-insight-type CTR baseline)` | L3 INS1 | L | 🔴 H | PR #1, #4 | Cost |
| 16 | `[Impact: High] [cost] L3-Phase2 — Consolidate 6-conv Insights → 1 structured-output call (gated by L3-P1 baseline)` | L3 INS1 | L | 🔴 H | PR #15 | Cost |
| 17 | `[Impact: High] [cost] L1 — Cache-friendly prompt structure (completes .projects/cache-friendly-schema-agent-prompts/)` | L1 | L | 🔴 H | (extends in-flight 4-PR plan) | Cost |
| 18 | `[Impact: High] [latency][reliability] L4 — N+1 elimination in ConversationHistoryItemManager (lines 529-604)` | L4 | L | 🔴 H | none | Latency |
| 19 | `[Impact: Medium] [latency] L5 — ERS query push-down (pageLimit + sortDescending; replace fetchAllPages)` | L5 | L | 🟡 M | none | Latency |
| 20 | `[Impact: High] [reliability][cost] R3 — HOT-301423 tomcat-thread + queue-depth autoscaling (OPS3)` | R3 OPS3 | R | 🔴 H | PR #1 | Cost / Cap |
| 21 | `[Impact: High] [reliability] R5 — Replace AsyncAgentInMemoryJobStore with persistent backing (RV3)` | R5 RV3 | R | 🔴 H | none | 150k MAU readiness |
| 22 | `[Impact: High] [reliability] R1 — Complete per-service CB migration in AggResilienceProvider (NOT Resilience4j)` | R1 | R | 🔴 H | (extends .projects/circuit-breaker/) | Reliability |
| 23 | `[Impact: High] [reliability] PLT-15.5 / S1 — Fire-and-forget DLQ for ApplicationCoroutineScope (memory ingest)` | S1 | R | 🔴 H | none | Trust (no silent loss) |
| 24 | `[Impact: Medium] [reliability] PLT-15.6 / S3 — Idempotency keys for post-workflow mutations (extends v7 R-6A)` | S3 | R | 🟡 M | (depends on v7 R-6A live) | Trust |
| 25 | `[Impact: High] [latency] L2-PhaseA — Parallel tool execution within single LLM-decision turn (read-only allowlist)` | L2 | L | 🔴 H | (depends on v7 R-6A live ≥7d) | Latency |
| 26 | `[Impact: Medium] [quality] I1 — PromptComposer with budget-aware sections (extends CacheFriendlyPromptAssembler)` | I1 | I | 🟡 M | PR #17 (L1) | Quality |
| 27 | `[Impact: Medium] [quality][latency] I2 — Semantic context-window selection (replaces takeLast(10), FF-gated)` | I2 | I | 🟡 M | none | Quality (AIFC) |
| 28 | `[Impact: Medium] [quality][cost] I3 — Progressive summarization for SimpleLoopWorkflow (reuses ContextCompactionService)` | I3 | I | 🟡 M | PR #26 (I1) | Quality + Cost |
| 29 | `[Impact: High] [quality][cost] I4 — Skill-conflict workstream Phase 1 (vague-query cost guard + tool-overlap registry)` | I4 G-1 | I | 🔴 H | PR #4 (G-3 EVAL1 live) | Quality + Cost |
| 30 | `[Impact: High] [throughput][velocity] CI1 — Collapse 8 cloned IT-shard step blocks + per-flag-change gate` | CI1 | W | 🔴 H | none | Dev velocity |

### 3.2 Impact distribution

| Impact | Count | Share |
|---|:---:|:---:|
| 🔴 **HIGH** | **17** | 57% |
| 🟡 **MEDIUM** | **12** | 40% |
| 🟢 **LOW** | **1** | 3% |
| **Total** | **30** | 100% |

### 3.3 Items decomposed into multi-PR stacks (safety boundaries)

- **P3 (cost metric)** = 2 PRs: foundation (#1) + per-experience panel/alarm (#2)
- **L3 (Insights consolidation)** = 2 PRs: cohort-A/B harness baseline (#15) → consolidation (#16). **Anti-goal #46 enforced**.
- **L2 (parallel execution)** = 2 PRs in plan: Phase A tools-only (#25), Phase B subagents (Wk 11-12 — not in 30-PR list, deferred)
- **A1, A2, A3** = stacked PRs not yet decomposed (they're L-effort multi-quarter; will be sub-decomposed in their per-workstream companion docs in §11)

### 3.4 PRs not in the 30 (deferred / cut with rationale)

- **A1 (provider hierarchy 4,170 LoC reduction)** — split across **3 PRs** (Anthropic POC / Gemini / OpenAI), but **gated on A2 Phase 2 (B11) completing** (anti-goal #44/#47). Tracked but not in the 30-PR shortlist.
- **A2 (async migration 607 sites, 4-phase)** — coordinated via existing `.projects/coroutine-migration/`; not separate BOOST PRs.
- **A3 (LLMServiceImpl decomposition)** — 1 PR, but **gated on A5 (typed FF) live**. Wk 7-8 slot. Not in TOP-30.
- **M1 (TenantTier)** — coordinated via Rohit Jhangiani DACI; entity-model alignment first. Wk 11-12.
- **G-4 (EVAL2 prod-shadow)** — coordinated with v7 O1 auto-rollback; Wk 9-10.
- **P2 (Cat-3 silent-death probes)** — gated on S1 DLQ counter (#23) live ≥7d.
- **Cut entirely:** PLT-1 (Resilience4j), PLT-6 (cache hierarchy), PLT-14 (regex prompt-injection), INT-7, INT-8, INT-12, MON3, ARC-2, ARC-4 — see §0.2.

---

## 4. 12-week sequencing — concrete PR landing schedule

```
Wk 0   FOUNDATION (must land before all others; PRs #1-4)
        PR #1  P3 cost metric foundation
        PR #3  P1 Cat-1 Perf Contract instrumentation (after jgrose confirms targets)
        PR #4  G-3 EVAL1 PR-gate harness

Wk 1-2 XS QUICK WINS (parallel batch, 4 engineers; PRs #2, 5-13)
        PR #2  P3 follow-up panel + alarm
        PR #5  W-2 R23 hydratePool split
        PR #6  L7 AIFC7 MCP cache key
        PR #7  A5 typed FF + RequestScopedLLMFlags
        PR #8  W-1 SSE event:ack preamble
        PR #9  PLT-15 silent-failure remediation
        PR #10 S2-Phase1 saturation gauge (metric only)
        PR #11 PLT-2 TokenBucketRateLimiter spin-fix
        PR #12 R2 standardized retry patterns
        PR #13 R4 streaming quality gate

Wk 3-4 COST + L1 + INSIGHTS A/B (PRs #14-17, #30)
        PR #14 L6 RV5 adaptive iteration cap (after PR #1 +7d)
        PR #15 L3-Phase1 Insights cohort A/B harness
        PR #17 L1 cache-friendly prompts (extends in-flight)
        PR #30 CI1 collapse 8 IT-shard step blocks
        Coordinate with .projects/coroutine-migration/ A2 Phase 1

Wk 5-6 COST CONSOLIDATION + N+1 + AUTOSCALE (PRs #16, #18-22)
        PR #16 L3-Phase2 6-conv Insights → 1 call (gated by PR #15 baseline)
        PR #18 L4 N+1 elimination
        PR #19 L5 ERS query push-down
        PR #20 R3 OPS3 autoscale (perfhammer-gated)
        PR #21 R5 RV3 AsyncAgentJobStore persistence
        Continue A2 Phase 1-2 in .projects/

Wk 7-8 RELIABILITY + INTELLIGENCE (PRs #22-29)
        PR #22 R1 complete CB migration in AggResilienceProvider
        PR #23 S1 DLQ for ApplicationCoroutineScope
        PR #24 S3 idempotency keys for post-workflow (gated by v7 R-6A live)
        PR #25 L2-PhaseA parallel tool execution (gated by v7 R-6A +7d)
        PR #26 I1 PromptComposer (extends L1 assembler)
        PR #27 I2 semantic context window (FF-gated)
        PR #28 I3 progressive summarization
        PR #29 I4 G-1 skill-conflict Phase 1 (after G-3 EVAL1 live ≥7d)
        A2 Phase 2 finishes (B11 retired) → unblocks A1 Phase 1

Wk 9-10 ARCHITECTURE DEEP REFACTORS (gated, not in 30-PR list)
        A1 Phase 1 (Anthropic family POC, -1,800 LoC)
        A3 LLMServiceImpl decomposition (gated by A5 PR #7 live)
        L2-PhaseB parallel subagent execution
        G-4 EVAL2 prod-shadow auto-rollback feeder
        Coordinate ARC-2/ARC-4 via .projects/rovo-module-decomposition/

Wk 11-12 MONETIZATION + QUALITY FINISHER (gated, not in 30-PR list)
        M1 TenantTier (after Rohit DACI alignment)
        I4 Phase 2 (LH 41KB prompt segmentation)
        A1 Phase 2-3 (Gemini + OpenAI provider consolidation)
        P2 Cat-3 silent-death probes (gated by S1 DLQ +7d)
        Final validation: all M-series live ≥7d
```

**Parallelism principle:** Each week-2 batch (PRs #5-13) is independent — 4 engineers can land in parallel. Wk 5-6 cost-consolidation batch needs ≥7d post-deploy soak between PR #15 and #16 to verify cohort A/B baseline.

---

## 5. Anti-goals (carries v7's 36 + BOOST v1's 5 + integrated 42-50)

(v7 anti-goals 1-36 carried verbatim; BOOST v1 anti-goals 37-41 carried verbatim.)

**Integrated anti-goals:**

42. **Do NOT introduce Resilience4j.** The platform already uses `AggResilienceProvider` + `AggServiceKey` actively, and `.projects/circuit-breaker/` is migrating it. Adding a second framework creates confusion and split ownership. **Extend, don't replace.** (Sunset v3 anti-goal #42 — corrects v1's PLT-1 mistake.)
43. **Do NOT duplicate `.projects/` in-flight work.** Before creating any item, check `coroutine-migration/`, `circuit-breaker/`, `cache-friendly-schema-agent-prompts/`, `rovo-module-decomposition/`. BOOST extends these, never replaces. (Sunset v3 #43.)
44. **Do NOT ship A1 (provider consolidation) before A2 Phase 2 (blocking-bridge retirement).** Mixed blocking/suspend bases create unmaintainable code. (Both Sunset & Cursor v2.)
45. **Do NOT ship M1 (TenantTier) without aligning with the canonical "Rovo & AI Feature" definition DACI** (Rohit Jhangiani, page 7023743677, IMPACT HIGH, 2026-05-15). (Cursor v2 #45.)
46. **Do NOT ship L3 (Insights consolidation, PR #16) without cohort A/B (PR #15) running ≥7 days** with per-insight-type CTR baseline. (All 3 plans.)
47. **Do NOT ship A3 (LLMServiceImpl decomposition) before A5 (typed FF + req-scoped memo, PR #7) lands.** A3 extracts FF parsing into `RequestScopedLLMFlags` which must exist first. (Cursor v2 #47.)
48. **Do NOT build a centralized Prompt Registry** (cuts INT-8). `CacheFriendlyPromptAssembler` + Pebble + Statsig is sufficient. ROI is uncertain; ERS entity + management UI overhead is real. (Sunset v3 #47.)
49. **Do NOT build regex-based prompt-injection detection** (cuts PLT-14). Defer to `responsible-ai-api` team's safety pipeline. Regex has well-documented false-positive rates. (Sunset v3 #48.)
50. **Do NOT adopt P1 Cat-1 SLO targets without confirming with jgrose** (page 7039684456). They were a working draft as of 2026-05-15. (All 3 plans.)
51. **Do NOT ship L6 (RV5 adaptive iteration cap) without paired accuracy A/B** demonstrating ≤5% task-completion regression for DEFAULT-classified queries at the reduced cap. (Sunset v3 #46.)
52. **Do NOT promote any item past 5%→25% rollout cohort until OBS3 (P3, PR #1) has ≥7 days of (tenant, experience) attribution data live.** Otherwise rollout decisions are guessed.

**Inherited critical anti-goals worth re-stating:**
- v7 #15: No throughput claim ships without perfhammer 2× peak load test sustained 5 min.
- v7 #16: No quality claim ships without BatchEval on Q13 Goldens-300 + UI snapshot diff = 0.
- BOOST v1 #40: No cost claim measured by LLM-token counters alone — use M4 Socrates `convo_ai_usage` per-feature attribution.
- BOOST v1 #41: Do not refactor a class because it's "ugly". A1/A3 must each show measurable dev-velocity (LoC removed, PRs/wk delta) within 6 weeks of merge; otherwise rollback.

---

## 6. Cut-tiers (constrained sprints)

| Sprint length | Items dropped (drop count) | PRs kept | Rationale |
|---|---|---|---|
| **12-week (FULL)** | 0 dropped | All 30 PRs + A1/A2/A3/M1/G-4/P2 deferred items | All workstreams ship |
| **8-week** | A1 Phase 2/3, L2-PhaseB, I4 Phase 2, M1, G-4, A3 (6 items) | ~24 PRs | Defer architecture-deep + monetization |
| **6-week** | + A2 Phase 3-4, R5 RV3, S3 idempotency, I3 progressive summarization (4 more items) | ~20 PRs | Wk 7-8 reliability + intelligence finishers deferred |
| **4-week** | Keep ONLY load-bearing TOP-9: P3 (#1, #2), P1 (#3), G-3 (#4), W-2 (#5), L7 (#6), A5 (#7), L6 (#14), L3 (#15-16) | **9 PRs** | TOP-15 minus everything that requires multi-week soak/A/B |
| **NEVER cut (load-bearing)** | P3 (cost foundation), G-3 (PR-gate), L3 ($30-80K), L1 ($30K+), R3 (autoscale), W-2 (XS-S latency), L6 ($15-40K), R1 (cascading-failure), S1 (silent loss), P1 (Cat-1 SLO) | 10 minimum | Each moves >1pp on a top FY26/FY27 goal |

---

## 7. Measurement plan extensions (M1-M9 v7 + M10-M15 prior + NEW M16-M20)

| ID | What it proves | Required instrumentation | Source |
|----|----------------|--------------------------|--------|
| **M16** | L1 cache-friendly prompt savings | P3 `cached_tokens` counter; per-model prompt-cache hit rate; $/mo from M4 Socrates | Sunset v3 |
| **M17** | A1 provider-consolidation velocity | Per-week LoC delta; per-PR build-break rate; new-provider onboarding time | Sunset v3 |
| **M18** | L2 parallel execution latency | Per-turn multi-tool-call count; p95 turn-latency delta when ≥2 tools; coroutine pool utilization | Sunset v3 |
| **M19** | L3 Insights cost & quality | Per-insight-type LLM cost; total Insights $/mo; per-insight-type click-through rate | Sunset v3 |
| **M20** | R4 streaming quality-gate efficacy | Catch rate; FP rate; retry-success rate on fallback model | Sunset v3 |

**Hard rule (from BOOST v1, reinforced by all 3):** No PR ships claiming impact until its M-series is live for ≥7 days.

---

## 8. Honest calibration

- **Confidence per item:** items with file:line citation are 0.85-0.95 (verified by Cursor v2's 4-agent grep sweep over 70+ files; Sunset v3 confirmation). Items based on TWG signals (P1, M1, I4) are 0.85 (signals fresh as of 2026-05-15 but a few not double-confirmed with named owners).
- **Numbers are estimates:** all $/mo and ms-latency claims require their M-series live ≥7d before validation. PRs #15→#16 enforce a 7-day soak gate. PRs gated on P3 (#1) live ≥7d are explicit in the table.
- **Biggest residual risk:** A2 (async migration, 607 sites). Mitigated by existing `.projects/coroutine-migration/` rules; v2 doesn't add new BOOST PRs but coordinates landing.
- **What's still missing:**
  - AIFC FactualConsistency 13%→40% baseline (TWG QBR Q3 whiteboard 7038759626 not retrievable) — direct ask Vibha Choudhary / Lucas Ferreira / Jason Baker.
  - Confirmation of P1 Cat-1 SLO targets with jgrose (anti-goal #50).
  - Rovo Credits pricing model finalization (gates MON items).
  - LH 41KB system-prompt size (`LongHorizonOrchestratorPromptBuilder.kt` exists but template-runtime not measurable without prod sample) — gates I4 Phase 2.
- **What v2 did NOT do:** run scripts/twg directly. v2 inherits Cursor v2's TWG sweep (47 raw-JSON snapshots dated 2026-05-15). Wk 0 task: re-confirm 3 signals (P1 / M1 / I4) with named owners before shipping.

---

## 9. If we could only pick ONE plan, which would it be?

**Recommendation: This BOOST_INTEGRATED v2 plan.**

**Reasoning** (critical-thinking, evidence-based):

| Criterion | Cursor BOOST v2 | Sunset v3 | My v1 INTEGRATED | **v2 INTEGRATED** |
|---|:---:|:---:|:---:|:---:|
| TWG-fresh business signals (FY27 Cat-1, COGS DACIs, AIFC PIR, Memory) | ✅ | ✅ | ◐ (stale FY26) | ✅ |
| `.projects/` in-flight discovery & coordination | ❌ | ✅ | ❌ | ✅ |
| Code-evidence depth (file:line, LoC) | ✅ | ✅ | ◐ | ✅ |
| Goal-anchoring discipline | ✅ | ✅ | ✅ | ✅ |
| Anti-goal discipline | ✅ (7 new) | ✅ (8 new, **incl. "no Resilience4j"**) | ✅ (7 new but had Resilience4j wrong) | ✅ (10 new, all corrections folded) |
| Concrete PR list with impact labels | ❌ | ❌ | ❌ | **✅ (30 PRs)** ← **uniquely v2** |
| $/mo dollar quantification | ✅ | ✅ | ✅ | ✅ |
| Refactor design depth | ◐ | ✅ | ◐ | ✅ (deferred ARC-2/4 to existing in-flight project per Sunset's correct call) |
| Realistic scope (avoids over-stuff) | ❌ (60 items, TOP-20 cut) | ✅ (22 items) | ◐ (41 items) | ✅ (24 items, 30 PRs) |
| Single source of truth (no plan-of-plan) | ◐ (proposes sub-files) | ✅ | ✅ | ✅ |
| Multi-PR safety boundaries (cohort A/B, rollout gating) | ◐ | ✅ | ✅ | ✅ (PR-level) |
| Measurement-plan extension | ✅ M13-M15 | ✅ M16-M20 | ✅ M10-M12 | ✅ all M10-M20 |
| Cuts INT-8 / INT-12 / PLT-14 with rationale | ❌ (some kept) | ✅ | ❌ (deferred) | ✅ (cut entirely with rationale) |
| Dependency / critical-path diagram | ✅ (Mermaid) | ◐ | ❌ | ◐ (sequencing block clarifies) |

**If forced to pick ONE source plan only** (NOT this integrated v2): **Sunset v3** because:
1. **It uniquely discovered `.projects/` in-flight workstreams** — without this, ~5 of the proposed items would be wasted duplicates (PLT-1, ARC-7 partial, INT-9 partial, A1 partial, A3 partial).
2. **Its anti-goal #42 ("no Resilience4j; extend AggResilienceProvider")** is the difference between an elegant solution and an anti-elegant one. v1 and Cursor v2 both got this wrong.
3. **Its rigorous cut discipline** (22 items vs 60) makes it the most realistic to actually ship in a quarter.
4. **Its weakness** — drops MON workstream + several Cursor v2 TWG-anchored items (RV3, RV9, AIFC7) — would be partially recoverable later.

**But v2 is strictly better than any single source** because it loses none of Sunset's elegance corrections, gains all of Cursor v2's TWG signals, AND adds the concrete 30-PR list that none of the source plans produced (the user's new explicit requirement).

---

## 10. Calling-for-action

1. **Wk 0 owner ping for TWG-signal re-confirmation:** jgrose (P1), Rohit Jhangiani (M1), Hao Chen (I4 G-1), Vincent Zeng + Guangwei Weng (Memory); Robbie Livermore + Kevin Ma (overall).
2. **Confirm v7 + BOOST v1 measurement infra (M1-M12) is live** before claiming any v2 impact.
3. **Allocate 4 engineers × 12 weeks** OR **3 engineers × 8 weeks** (per §6 cut-tier).
4. **Pick deployment cadence:** Aggressive 12wk (30 PRs + 6 deferred items) / Balanced 8wk (~24 PRs) / Conservative 4wk (9 load-bearing PRs).
5. **Coordinate with the 4 in-flight `.projects/`:** `coroutine-migration/` (A2), `circuit-breaker/` (R1), `cache-friendly-schema-agent-prompts/` (L1), `rovo-module-decomposition/` (deferred ARC-2/ARC-4).
6. **Generate Jira epics** for the 6 workstreams (P / A / L / R / I / W + M).
7. **Build the §11 companion docs** (TODO; per-workstream detail) once leadership signs off on TOP-15.

---

## 11. Companion documents

| File | Purpose | Status |
|------|---------|--------|
| `BOOST_INTEGRATED_v2.md` | This file (master plan) | ✅ Complete |
| `boost_items/P-PerfContract.md` | P1, P2, P3 instrumentation detail | TODO |
| `boost_items/A-Architecture.md` | A1 (4-family abstract), A2 (4-phase), A3 decomposition table, A5 typed FF | TODO |
| `boost_items/L-LatencyCost.md` | L1-L7 detailed designs | TODO |
| `boost_items/R-Resilience.md` | R1-R5 + S1/S2/S3 detail; **explicit redesign of v1's PLT-1 as R1 within `AggResilienceProvider`** | TODO |
| `boost_items/I-Intelligence.md` | I1-I4 detail; explicit fold of v1 INT-9 into I1 | TODO |
| `boost_items/W-TacticalWins.md` | CI1, B11, R23-as-W-2, W-1 SSE, W-5 FF memo | TODO |
| `boost_items/M-Monetization.md` | M1 TenantTier; explicit DACI alignment matrix | TODO |
| `BUSINESS_GOALS_DELTA_v2.md` | What v2 changes vs FY26 goals doc + delta vs v1's BUSINESS_GOALS_DELTA | TODO |
| `EVIDENCE_INDEX.md` | One-stop file:line citation table for all 24 items | TODO |
| `PR_TRACKING.csv` | Machine-readable PR list (the 30 PRs in §3.1 as CSV: id, title, item, ws, impact, stacked_on, goal_anchor) | TODO |

---

**END OF PLAN.** Future updates bump version (`v2` → `v3`) and document deltas in a changelog section.