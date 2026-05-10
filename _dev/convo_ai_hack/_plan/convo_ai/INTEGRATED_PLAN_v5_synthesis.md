# Convo AI / Rovo Chat — Integrated v5 Plan (synthesis of A-v2 + B + v4)

> **Synthesis of three living plans (re-read 2026-05-04):**
> - **Plan A** (`~/.claude/plans/here-is-codebase-docs-distributed-hearth.md`, **334 lines, was 641** — Plan A's author re-wrote it into a meta-integration that compares 4 sub-plans: lazy-jellyfish, PLAN-INTEGRATED-v2, tingly-octopus, and original distributed-hearth)
> - **Plan B** (`_plan/convo_ai/here-is-codebase-docs-sorted-sunbeam.md`, 420 lines — unchanged)
> - **My v4** (`_plan/convo_ai/INTEGRATED_PLAN_v4_synthesis.md`, 497 lines — unchanged)
>
> **Status:** PROPOSED · supersedes v4. Date: 2026-05-04.
> **Method:** fresh re-read of all three; explicit diff vs my prior pass; critical-thinking integration; user-facing-preservation enforced ruthlessly.

---

## 0. What changed since v4 (this is the load-bearing observation)

**Plan A was completely rewritten.** It is no longer a single-author optimisation plan — it is now itself an **integration plan** comparing four Insights-focused sub-plans (lazy-jellyfish / PLAN-INTEGRATED-v2 / tingly-octopus / original distributed-hearth). It now has Tier 0–5 sequencing, an explicit single-plan answer, and an "architectural decisions" table where it defends specific choices over Plan B's and Plan C's alternatives (e.g., `enqueuedAt` over SETNX, retry+throw over fire-and-forget, 120s wall-clock).

**That changes the comparison materially:**

| What | Before (v4 read) | After (v5 read) |
|---|---|---|
| Plan A scope | Chat + Platform | **Chat + Platform + Insights** (NEW: full Insights coverage) |
| Plan A discipline | Per-item but no rollout flags | **Tier 0–5 sequencing + per-flag rollout for Insights items** |
| Plan A self-comparison | None | **Explicit cross-plan table + architectural-decisions table** |
| Plan A's single-plan answer | None | **"distributed-hearth + S7"** (well-reasoned: SLO is about Chat, not Insights) |
| Plan A AIFC coverage | None | **Still essentially none** (8 grep hits — only via "Plan B" mentions in the cross-plan table) |
| Plan A dual-list pattern | None | **Still none** — items 2.3 (Haiku default) and 2.4 (tool filtering) still listed as "A/B test required" without structural separation |

**Plan B unchanged.** Still has the strongest UF-preservation (uiOrdered/llmOrdered), AIFC quality recovery (Q1-Q14), measurement-first discipline (M1-M7), Phase-0 operational requirements (O1-O6).

**My v4 unchanged.** Still has the explicit re-scoping of A's UF-risky items (A2.3-GUARDED, A2.4-DUAL, A2.5-GUARDED, A2.2-RECAST).

---

## 1. The two genuine new contributions in Plan A v2

These are net-new items that v4 did NOT cover and that Plan B does NOT cover. v5 adopts them.

### 1.1 The Rovo Insights workstream (entire domain)

Plan A v2 brings the entire **Insights** code path (which is async, SQS-driven, separate from the Chat hot path):

| Insights item | What | Goal | Confidence |
|---|---|---|---|
| **S7 / Q1** | `CACHE_TIMEOUT=1d → 7d` (one-line fix at `RovoInsightsV1Controller.kt:193`) | -80%+ Insights LLM cost | High — **15-min implementation; spectacular ROI** |
| **L1** | N+1 person hydration (~54 sequential remote calls post-LLM) → batch with Semaphore(16) at `RovoInsightsServiceImpl.kt:322-334, 357-466` | -5–10s p95 on Insights | High |
| **L2** | `coroutineScope` cancels all 5 sibling insight types on 1 failure → `supervisorScope + runCatching` at `RovoInsightsServiceImpl.kt:468-485` | 12-min worst-case → 240s/type; partial delivery on failure | High |
| **S1** | No SQS idempotency guard → duplicate LLM generations → `enqueuedAt` timestamp comparison (NOT SETNX) | 0 duplicate generations; **Plan A's architectural decision is correct** — checking "is work done" vs "is lock held" | High |
| **S2** | Notification swallows errors silently → retry+throw → SQS redrive (NOT fire-and-forget) | Users no longer cached-but-not-notified | High |
| **E1** | 118KB prompt duplication across 6 types → byte-identical prefix for prompt cache | -72% input tokens (~$2.8M/yr at scale per A's math) | Medium — depends on prompt-cache hit landing first |
| **E3** | `structuredOutputEnabled=false` despite API support → toggle on | Eliminates parse-failure retries (30s-4min each) | High |
| **Q7** | Hoist Statsig hydration flag eval (50 evals/gen → 1) at `RovoInsightsServiceImpl.kt:327-333` | -1.25–2.5s per generation | High |
| **Q8** | Retry backoff + jitter at `Retryable.kt:13-29` | 3× burst-cost reduction | High |
| **S5** | Wall-clock budget `withTimeout(120_000)` around `supervisorScope` | <0.5% stuck-generating rate | High |

**These have ZERO file overlap with Plan B's Q-series (page-search) and L-series (chat).** Plan A v2 is right that they can be implemented in parallel by different engineers.

### 1.2 The architectural-decisions table

Plan A v2 documents three contested architectural choices with named alternatives and an explicit verdict:

| Issue | Alternative considered | Choice | Why |
|---|---|---|---|
| Idempotency | SETNX Redis lock (Plan B's choice) vs `enqueuedAt` timestamp (Plan C's choice) | **`enqueuedAt`** | SETNX checks "is lock held" — if handler 1 finishes + releases, SETNX lets handler 2 redo work. `enqueuedAt` checks "is work done" — sees fresh cache and short-circuits. **Correct.** |
| Notification on failure | Fire-and-forget on SupervisorJob (Plan B) vs retry+throw → SQS redrive (Plan C) | **retry+throw** | Fire-and-forget permanently loses notifications. Retry+throw + SQS redrive + idempotency = user eventually notified without double LLM cost. **Correct.** |
| Wall-clock budget | 90s (B) vs 120s (C) | **120s** | 90s too aggressive (current per-type timeout is 240s); 120s = ~3× p95 after B1+B2 wins. **Correct.** |

**These are real engineering decisions.** v5 adopts them verbatim for the Insights workstream.

---

## 2. The two structural weaknesses Plan A v2 STILL has

### 2.1 Plan A v2 still misses the AIFC factual-consistency 57pp crisis

Plan B's headline finding is that AIFC factual consistency regressed from **80% → 13%** (a 57pp gap to a beta-GA-blocking target of ≥70%). Plan A v2 does not address this at all. Its 8 grep-hits on "AIFC" / "factual" / "page-search" are all in the cross-plan summary table where it acknowledges Plan B exists.

**Why this matters:** Latency and cost wins do not compensate for a quality regression. If AIFC ships with 13% factual consistency, the beta GA is blocked regardless of how fast or cheap Chat is. **Plan B's Q1-Q14 workstream is non-negotiable.**

### 2.2 Plan A v2 still has weak user-facing-preservation

The "Constraint: NO user-facing behavior changes" line is a *statement of intent* but not a *structural mechanism*. A v2 still lists items **2.3 (Haiku 4.5 default for orchestration)** and **2.4 (relevance-based tool filtering)** under "A/B test required" — which is necessary but not sufficient.

These items can change LLM-visible behaviour:
- **A 2.3 Haiku default**: a different model picks tools differently, even at "95% accuracy". The 5% delta IS user-visible (a tool the user expects to be selected isn't).
- **A 2.4 tool filtering 80→20**: hard pre-LLM filtering means the LLM never sees pruned tools. If the rule misses, the LLM literally cannot act.

Plan B's structural answer — the **dual-list pattern** (`uiOrdered` byte-identical to today + `llmOrdered` for LLM context only) — and v4's re-scoping (A2.3-GUARDED, A2.4-DUAL) — are the correct fix. v5 keeps them.

---

## 3. Goals & metric ledger (canonical, unchanged from v4)

| Goal | Baseline | Target | Gap | Source |
|---|---|---|---|---|
| Rovo MAU | ~100.3k | 150k by H2 FY26 | +50% | Atlas ATLAS-124112 |
| Chat send-msg SLO | 99.6% | 99.9% (LLM-vendor ceiling) | +0.3pp | TOME `convo_ai/locals.tf` |
| Agent Studio create-scenario SLO | 98.2% | 99.99% | +1.8pp | TOME |
| **AIFC factual consistency** | **13%** (regressed from 80%) | ≥70% | **+57pp** (beta-GA blocker) | AIFC TWCLR2 |
| AIFC contextual recall | 47% | ≥65% | +18pp | AIFC Maturity Gap |
| AIFC contextual relevancy | 40-44% | ≥70% | +27pp | AIFC Maturity Gap |
| Throughput at 150k MAU peak | ~1,500 req/s cap | ~2,900 req/s (5× burst) | -48% | Derived |
| **Insights LLM cost** | baseline | -80% via Q1 (S7); -72% input tokens via E1 | huge | Plan A v2 (NEW DOMAIN) |
| Cost / month total | baseline | -$215-375K/mo (Chat workstream) | depends | Cost agent + Socrates `convo_ai_usage` |
| Quality regression MTTD | >quarter (the 80→13 went undetected) | <1 day | huge | The AIFC regression itself proves the gap |

**Hard ceiling:** OpenAI Scale Tier 99.9% caps LLM-dependent SLOs. Multi-provider failover is the only lever past it.

---
## 4. Three design principles (non-negotiable, all from Plan B; reinforced by Plan A v2's Tier 0 discipline)

1. **Goal-driven priority.** Every item declares one primary goal + quantified impact in the goal's metric units + confidence (0–1) + priority score = (impact / goal-gap) × confidence ÷ implementation-risk.
2. **User-facing-behavior preservation.** Every item is tagged `user_facing: yes / no / conditional`. Conditional items ship as **dual lists** (`uiOrdered` byte-identical to today + `llmOrdered` reranked for LLM context only). Genuine UF changes require: opt-in flag → cohort A/B (5%→25%→100%) → kill-switch → release note → UI-snapshot-diff = 0 in cohort A.
3. **Infra-blocker first.** Auto-rollback (O1), circuit breakers (O2), graceful shutdown (O3) MUST exist before the 30+ flag rollouts in this plan are safe. These are Phase 0.

---

## 5. Top-20 by goal-impact / risk (the actual ranked list, integrating all three plans)

| # | Code | Item | Source | Goal | Impact | Conf | Effort | UF | Flag |
|---|------|------|--------|------|------|------|--------|----|------|
| **1** | **O1** | Auto-rollback wiring (SignalFx detector → Statsig API auto-flip) | B | InfraBlocker | Enables all 30+ flagged items; chaos-drill: regressed flag flips 0% in ≤5min | 1.0 | M | no | — |
| **2** | **A.Q1 (S7)** | **Insights `CACHE_TIMEOUT=1d → 7d`** at `RovoInsightsV1Controller.kt:193` | A v2 | Insights Cost | **-80% Insights LLM cost in 1 line** | 1.0 | XS (15min) | no | dynamic config |
| **3** | **T0a / A.Q2** | Async pool 96→256 + queueCapacity=1000 with 503 reject | A v2 + B | Throughput / Stability | Prevent OOM at sustained burst; +200-400 req/s headroom | 1.0 | S | no | — |
| **4** | **T0b / A.Q3** | Heimdall rate-limiter timeout 3000ms→500ms with circuit-break | A v2 + B | SLO / Tail | -3s worst-case block | 1.0 | S | no | — |
| **5** | **T1** | Bound `Channel.UNLIMITED` in `HttpRequestStreamingWriter.kt:44` (code-comment literally warns "Risk: possible memory growth") | B | Throughput / Memory | Closes verified known-risk; eliminates heap-pressure on slow clients | 1.0 | S | no | `ROVO_STREAMING_BOUNDED_CHANNEL` |
| **6** | **A.L2** | **Insights cancellation isolation: `coroutineScope` → `supervisorScope + runCatching`** at `RovoInsightsServiceImpl.kt:468-485` | A v2 | Insights Stability | Tail latency 12-min worst → 240s/type; 5/6 types deliver on 1 failure | 1.0 | S | no | `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED` |
| **7** | **A.L1** | **Insights N+1 person hydration → batch with Semaphore(16)** at `RovoInsightsServiceImpl.kt:322-334, 357-466` | A v2 | Insights Latency | -5–8s p95 (54 sequential calls → ~4 batches) | 1.0 | M | no | `AIX_ROVO_INSIGHTS_HYDRATION_PARALLEL_ENABLED` |
| **8** | **A.S1** | **Insights idempotency: `enqueuedAt` timestamp comparison** (NOT SETNX lock — Plan A v2's correct architectural choice) | A v2 | Insights Stability | 0 duplicate generations; <0.5% stuck-generating rate | 1.0 | M | no | `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED` |
| **9** | **C1** | Persist compaction summary (versioned + checksummed) at `ContextCompactionServiceImpl.kt` | B | Cost | -$80-120K/mo | 1.0 | M | no | `ROVO_COMPACTION_PERSIST` |
| **10** | **Q1** | PageSearch L2 rerank for LLM context (dual-list pattern; UI order unchanged) at `ConfluencePageSearchServiceImpl.kt:47-77` | B | AIFC Factual | +15-25pp on golden eval | 1.0 | S | conditional (split) | `ROVO_PAGESEARCH_LLM_RERANK` |
| **11** | **K1+A2.1** | Anthropic prompt-cache: enable `cache_control` on system messages at `GenericClaudeRequestBuilder.kt:166-182` AND audit assembler usage | A+B | Cost | -$40-80K/mo; cache hit ≥70% | 1.0 | M | no | (it's a fix) |
| **12** | **L1** | TCS Caffeine cache at `AsyncTenantContextService.kt:35-260` | B | TTFB | -100-200ms × N (avg -150ms p50); cache hit ≥95% | 1.0 | S | no | `ROVO_TCS_CACHE` |
| **13** | **L3** | Remove `runBlockingWithContext` AI_EDITOR path at `ChatV1Controller.kt:267`; reactive `Flux<ServerSentEvent>` | B | ChatSLO | +0.1pp SLO; -100-300ms tail; Tomcat busy-thread p99 <60% | 1.0 | M | no | `ROVO_CHAT_NONBLOCKING_STREAM` |
| **14** | **A.S2** | **Insights notification: retry+throw → SQS redrive** (NOT fire-and-forget; Plan A v2's correct choice) | A v2 | Insights Trust | Users no longer cached-but-not-notified | 1.0 | S | no | (depends A.S1 idempotency) |
| **15** | **T2+T3** | AGG WebClient pool 4×→8× + eviction + HTTP/2 multiplex + codec 24MB→64MB | B | Throughput | +600 req/s peak; +30% throughput; conn count -10× | 1.0 | S | no | `ROVO_AGG_POOL_LARGE` + `ROVO_AGG_HTTP2` |
| **16** | **A2.4-DUAL** | Tool relevance pre-filter — full catalog visible in cached prefix; only **args schemas** pruned to top-20 (re-scoped from A 2.4 to preserve UF) | A (re-scoped) | Cost | -40-60% tool-token cost (~$3-4.5K/mo) | 0.7 | M | conditional | `ROVO_TOOL_FILTER_DUAL` |
| **17** | **A2.3-GUARDED** | Default to Haiku 4.5 for orchestration with paired LLMJudge A/B + auto-fallback to GPT-4-1 on tool-selection-confidence-low (re-scoped from A 2.3) | A (re-scoped) | Cost | -65-75% orchestration cost (~$8-12K/mo) | 0.7 | M | conditional | `SAIN_ORCHESTRATION_HAIKU_4_5` (flip default) |
| **18** | **F1** | Personality-experiment scope-fix (chat-only, NOT SAIN/Search) — verified production leak | B | Trust / MAU | Unblocks rollout; protects search-path factual tone | 1.0 | S | yes (release note) | extends existing personality flag |
| **19** | **C2** | Debounce in-session classifier at `InSessionSegmentationServiceImpl.kt:75-108` | B | Cost | -$15-25K/mo; classifier calls/turn ≤0.3 | 1.0 | S | no | `ROVO_SEGMENTATION_DEBOUNCE` |
| **20** | **A.E1** | **Insights prompt deduplication** at `Common.kt:32-116`, `templates/rovo/insights/v1/*.pebble` — 118KB → byte-identical prefix | A v2 | Cost | -72% input tokens for Insights (~$2.8M/yr at scale per A's math) | 0.7 | M | conditional | `ROVO_INSIGHTS_PROMPT_VERSION` |

**Items 21–40 (significant, second tier):** Q2 (bodyExcerpt additive), Q4 (grounding system prompt), L4 (parallel pre-LLM gates), L8 (request-scoped FF memoization), A.E3 (`structuredOutputEnabled=true` toggle), A.Q7 (hoist Insights Statsig hydration flag), A.Q8 (Insights retry backoff + jitter), A.S5 (Insights wall-clock budget 120s), L17 (per-conversation tool registry cache), L21 (history delta fetch), L18 (`.blockingGet` removal in MCP), C3+C4 (model downsizing A/B), K3 (tool-result coalescing in turn), F2 (starter prompts), A 3.1 (org.json → Jackson), A 4.1 (Redis pipeline TTL), A 4.2 (per-tenant search timeout), A 1.1-1.6 (chat critical path).

---

## 6. The dual-list user-facing-preservation pattern (mandatory; from Plan B)

Every retrieval/ranking/tool-selection change returns **TWO ordered lists from one search call**:
- `uiOrdered` — existing order, existing fields, **byte-identical** to today; bound to UI `sources` / `header`
- `llmOrdered` — reranked / enriched / score-filtered; consumed only inside the LLM context block

**This applies to (re-scoped) Plan A items:**
- **A 2.2** "delta-style history" → re-scoped to **K1+A2.1 Anthropic prompt-cache** (sends full history, caches the prefix; safer than dropping turns).
- **A 2.3** "Haiku for orchestration" → **A2.3-GUARDED** (paired LLMJudge A/B + auto-fallback).
- **A 2.4** "tool filtering 80→20" → **A2.4-DUAL** (full tool catalog still visible to LLM in cached prefix; only the args schemas pruned to top-20; LLM can always still NAME any tool; on a name-of-pruned-tool, fall back to full catalog on next turn).
- **A 2.5** "rule-based complexity classifier" → **A2.5-GUARDED** (rule-based for high-confidence ~70-80%; LLM for ambiguous middle).

**Items requiring explicit user-visible release note (UF=yes):** F1, F2, F3, F4, F5, F6, F7, F9, Q4, Q5, Q11.

**Anti-pattern explicitly forbidden:** "ranking by recency → ranking by relevance" type changes. The user contract is that `lastModified` ordering is preserved in the UI list. Any relevance-based reordering is LLM-context-only.

---

## 7. Workstream summary (deduplicated, with Plan A v2's Insights workstream added)

| Workstream | Item count | Source distribution | Status |
|---|---|---|---|
| **O — Operational infra-blockers** (O1-O6) | 6 | B | Phase 0 prerequisite |
| **N — Insights (NEW in v5)** | 11 | A v2 | NEW — see §8 |
| **A — AIFC Quality (Q1-Q14)** | 14 | B | Beta-GA blocker |
| **L — Chat TTFB & SLO** | ~25 | B (L*) + A v2 (1.1-1.6) | Combined |
| **T — Throughput / Capacity** | ~14 | B (T1-T14) + A v2 (Q2-Q6, 0.1-0.5) | Combined |
| **C — Cross-cutting Cost** | ~12 | B (C1-C9) + A v2 (2.1-2.5 re-scoped) | Combined |
| **K — Caching / Coalescing** | ~10 | B (K1-K8) + A v2 (3.1-3.6, 4.1-4.3) | Combined |
| **F — Feature Enhancements** | 11 | B | Direct MAU levers |
| **E — Eng Velocity / Debt** | ~10 | B (E1-E7) + A v2 (7.1-7.4) | Combined |
| **R — Repo-Context** | 7 | B | Stalled decisions |
| **TOTAL** | ~120 | | All deduplicated |

---
## 8. Workstream N — Rovo Insights (NEW in v5; from Plan A v2)

Rovo Insights is async, SQS-driven, separate from the Chat hot path. **Zero file overlap** with Plan B's Q-series and L-series. These items can be implemented in parallel by different engineers.

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag | Architectural decision |
|---|---|--------|------|------|------|--------|-----|------|----------------------|
| N1 (S7) | `CACHE_TIMEOUT=1d → 7d` at `RovoInsightsV1Controller.kt:193`; expose as dynamic config | A v2 | Insights Cost | -80%+ Insights LLM cost | 1.0 | XS | no | dynamic config | Aligns with MVP "weekly Mon-Tue" cadence; `forceCacheMiss` available as safety valve |
| N2 (L2) | Cancellation isolation: `coroutineScope` → `supervisorScope + runCatching` at `RovoInsightsServiceImpl.kt:468-485` | A v2 | Insights Stability | 12-min worst → 240s/type; 5/6 deliver on 1 failure | 1.0 | S | no | `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED` | One type's failure shouldn't kill 5 healthy siblings |
| N3 (S1+S5) | Idempotency guard via `enqueuedAt` timestamp + wall-clock budget `withTimeout(120_000)` around `supervisorScope` | A v2 | Insights Stability / Cost | 0 duplicate generations; <0.5% stuck-rate | 1.0 | M | no | `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED`, `ROVO_INSIGHTS_WALL_CLOCK_BUDGET_MS` | **`enqueuedAt` over SETNX** — checks "is work done", not "is lock held". 120s = 3× p95 after wins; tunable via dynamic config |
| N4 (L1) | N+1 person hydration: dedup across types + concurrent batch via Semaphore(16) at `RovoInsightsServiceImpl.kt:322-334, 357-466` | A v2 | Insights Latency | -5–8s p95 (54 sequential → ~4 batches) | 1.0 | M | no | `AIX_ROVO_INSIGHTS_HYDRATION_PARALLEL_ENABLED` | Dedup first (saves wasted batched calls), then batch |
| N5 (S2) | Notification reliability: retry+throw → SQS redrive (NOT fire-and-forget) at `RovoInsightsNotificationService.kt:88-98` | A v2 | Insights Trust | Users no longer cached-but-not-notified | 1.0 | S | no | (deps N3) | **retry+throw over fire-and-forget** — fire-and-forget permanently loses; retry+throw + SQS redrive + N3 idempotency = correct |
| N6 (Q7) | Hoist Statsig hydration flag eval (50 evals/gen → 1) at `RovoInsightsServiceImpl.kt:327-333` | A v2 | Insights Latency | -1.25–2.5s per generation | 1.0 | XS | no | none | Trivially correct hoist |
| N7 (Q8) | Retry backoff + jitter at `Retryable.kt:13-29` | A v2 | Insights Cost / Stability | 3× burst-cost reduction | 1.0 | XS | no | none | Standard exponential backoff with decorrelated jitter |
| N8 (E3) | `structuredOutputEnabled=true` toggle in Insights LLM client | A v2 | Insights Latency / Cost | Eliminates parse-failure retries (30s-4min each) | 1.0 | XS | no | per-flag toggle | API supports it; current value is a misconfiguration |
| N9 (L6) | Hoist `createConversationId()` above fan-out (6-18 → 1 conversation creates) | A v2 | Insights Latency | -0.6–1.8s per generation | 1.0 | S | no | none | Same conversation can be reused across all 6 insight types |
| N10 (E1) | Prompt deduplication: extract shared prompt content into byte-identical prefix; refactor 6 Pebble templates at `Common.kt:32-116`, `templates/rovo/insights/v1/*.pebble` | A v2 | Insights Cost | -72% input tokens (~$2.8M/yr at scale) | 0.7 | M | conditional | `ROVO_INSIGHTS_PROMPT_VERSION` (v1→v2; A/B with `Strategy.EVALUATE`) | Hold at 50% until `PROMPT_CACHE_HIT` confirms upstream caching works |
| N11 (Q9) | Drop full-prompt log (20KB×6) at `RovoInsightsServiceImpl.kt:168-185` | A v2 | Insights Latency | -50-200ms blocking I/O | 1.0 | XS | no | none | Sample at 1% if needed for debugging |

**Insights workstream owners:** can be a separate squad from Chat/Platform. Schedule Wk 1-6.

---

## 9. Measurement plan (M1-M7) — must ship in Weeks 1-2 (from Plan B; reinforced by Plan A v2's Tier 1D)

| ID | What it proves | Required instrumentation |
|---|---|---|
| M1 | AIFC eval harness | Golden 300-row dataset (Q13); LLMJudge factual + recall + relevancy; nightly job; per-flag-cohort deltas |
| M2 | ARIZE per-turn quality | LLMJudgeServiceImpl wired into ARIZE event pipeline (Q14); 5% sample; cohort tags |
| M3 | TTFB per-orchestrator + dispatcher utilization | @WithSpan + per-pool dispatcher utilization metrics. "Pre-LLM serial time" + per-pool saturation panel |
| M4 | Cost per turn — LEVERAGE EXISTING | Use Socrates `convo_ai_usage` data product (verified). Add per-feature attribution panel; do not reinvent |
| M5 | Model-downsize quality non-regression | A/B with paired prompts; LLMJudge delta; user thumbs-down |
| M6 | Cache discipline | Hit/miss/eviction per Caffeine cache; Redis memory + eviction; FF-call counter per request |
| M7 | Throughput / saturation | Per-pod req/s; per-downstream connection pool saturation; HPA scale event log; pod cold-start time |
| **M8 (NEW for Insights)** | Insights stability / cost | `_PER_TYPE_FAILURE{cause}`, `_IDEMPOTENCY_SHORT_CIRCUIT > 0`, `_GENERATION_LATENCY` p95, cache regen rate |

**No item ships claiming impact until the relevant M* is live.** This is load-bearing for goal-driven prioritization.

---

## 10. Sequencing (12-week phased; integrating Plan A v2's Tier 0-5 into Plan B's workstream cadence)

```
Wk 1   O1, O2, O3 (infra)  ·  M1+M3+M7 instrumentation  ·  M8 Insights metrics
       ·  N1 (Insights cache 1d→7d, 15-min XS)  ·  N7 (retry jitter)  ·  N8 (structuredOutputEnabled)  ·  N11 (drop full-prompt log)
       ·  T1+T4 (bound channels)  ·  T0a (async pool) + T0e (ERS pool)
       ·  E3 (delete dead routes)  ·  Q13 golden dataset start
Wk 2   O4, O5, O6  ·  M2 ARIZE judge  ·  Q12 CI scaffold
       ·  N2 (supervisorScope)  ·  N6 (hoist Statsig flag)  ·  N9 (hoist createConversationId)
       ·  L1 + L8 + L19  ·  T0b (Heimdall) + T0c (hydration) + T2/T9 (AGG pool, load-tested)
       ·  K2 (sidecar prompt cache)  ·  C2 classifier debounce  ·  R7 actuator hardening
Wk 3   N3 (Insights idempotency + wall-clock)  ·  N4 dev (person hydration batch)
       ·  Q11 Slack date filter  ·  Q1 dev  ·  L2, L13  ·  T0d (parallel-tool-limit)  ·  T5 (heap+ZGC)
       ·  C1 dev  ·  F1 personality-scope dev
       ·  K1+A2.1 audit cache_control on system msg
       ·  A 1.2 + A 1.4 + A 4.3 (chat critical path quick wins)
Wk 4   N4 ship 5%→25% (hydration batch)  ·  N5 (notification retry+throw)  ·  N10 dev (prompt dedup)
       ·  Q1 ship 5%→25%  ·  Q4 dev  ·  L4 dev, L11
       ·  T3 (HTTP/2)  ·  T7 default pool
       ·  C1 ship 5%, C6  ·  F1 ship 5%→100%
       ·  R1 sidecar decision  ·  A 1.3 + A 1.5 (system prompt + tool schema cache)
       ·  A 3.1 (org.json → Jackson)  ·  A 4.1 (Redis pipeline)
Wk 5   N4 ship 100%  ·  N10 ship 5%→50% (prompt dedup; HOLD at 50% until PROMPT_CACHE_HIT confirms)
       ·  Q1 100%, Q3, Q2 dev  ·  L4 ship 5%→25%, L17 cache  ·  T8 AppCDS dev
       ·  C1 25%, C8 dev  ·  K3 dev  ·  F2 starter-prompts dev  ·  E1 parity test build
       ·  A 1.1 (parallel pre-workflow)  ·  A 3.2-3.5 (token count dedup, tool def cache, collection efficiency, config parsing cache)
Wk 6   N10 ship 100% if cache-hit confirmed  ·  Q2 ship 5%, Q12 CI gate enforced
       ·  L17 100%, L15 MCP session  ·  T11+T12 pool tune (gated by M7)
       ·  C1 100%, C3 citation A/B (paired LLMJudge)  ·  K4 in-flight singleflight
       ·  F2 ship 5%, F4 dev  ·  E1 cutover 5%
       ·  A2.1 cache_control ship 5%→100%  ·  A 4.2 (per-tenant search timeout)
Wk 7   Q2 100%, Q6 dev  ·  L21 history-delta dev, L18 .blockingGet  ·  C4 Lumina A/B
       ·  K5 edge cache headers  ·  F4 ship 5%, F8  ·  E1 25%
       ·  A2.3-GUARDED Haiku orchestration A/B (paired LLMJudge + auto-fallback)  ·  A 1.6 (parallel file scan)
Wk 8   Q6 ship, Q7 dev  ·  L21 ship, L18 ship  ·  C9 ship, C5 cache prompt V1
       ·  K6 Redis wire incremental (after grep verifies usage)  ·  F3 dev, F5 dev
       ·  E1 100% (delete A2AChatExecutor: -1,370 LoC)
       ·  A2.4-DUAL tool-args-schema prune (LLM context only)
Wk 9   Q7 ship, Q8/Q9/Q10 dev  ·  L31 compaction guard, L32 realtime async
       ·  C7 batch API offline  ·  K7 embedding-sim cache, K8 JSON-repair
       ·  F5 ship, F9 stale-source-warn  ·  E2 PlanGen V2 shadow  ·  R3, R4
Wk 10  Q8/Q9/Q10 ship  ·  L9 N+1 hydration, L10 Kamino parallel publish
       ·  C5 100%  ·  F3 ship, F10 feedback→ARIZE
       ·  E2 100% if shadow wins  ·  R6 SageMaker
       ·  A2.5-GUARDED rule-based complexity classifier (LLM fallback)
Wk 11  Q5 page-search opt-in flip A/B  ·  L3 AI_EDITOR non-blocking 5%→25%
       ·  T13 QPS targets in TOME, T14 DNS TTL
       ·  F6 confidence badges, F7 graceful error UX, F11 base-prompt-dynamic
       ·  E6 AIFEATURE split  ·  R5 ERS CI gate
Wk 12  Q5 100%, final eval lockdown  ·  L3 100%, L14 GraphQL pagination
       ·  E7 storage ADR  ·  R2 Loom scope
```

**Critical paths**:
- **Beta GA**: O1+O5 → M1+M2 → Q1 → Q2 → Q4 → Q12 enforced → Q5 flip → final lockdown
- **150k MAU readiness**: M3+M7 → L1+L8 → T1+T2+T5 → L4 → L17 → L21 → L3 + F2+F4
- **Cost realisation**: M4 → C1+C2 → C3+C4+C8 + A2.3-GUARDED + A2.4-DUAL → K1+K2+K3 → C7+C9
- **Insights NEW critical path**: M8 → N1 (Wk1 quick win) → N2+N3 → N4 → N5 → N10 (gated on cache-hit confirmation)

---

## 11. Anti-goals (what NOT to do — sacrosanct, integrating B + critical-thinking from this pass)

1. Do **not** rewrite UI source-list ordering. All ranking changes are LLM-context-only unless explicitly opted in via Q5.
2. Do **not** disable PageSearch globally. Q5 flip happens only after Q1+Q2+Q3+Q4 prove ≥+10pp factual.
3. Do **not** chase 99.9% SLO past 99.85% without multi-provider failover (out of scope for this 12wk).
4. Do **not** unify Postgres/DynamoDB agent storage in this 12-wk horizon (E7 = ADR only).
5. Do **not** remove `lastModified` UI ordering — documented user contract.
6. Do **not** ship cost reductions without paired quality A/B (M5).
7. Do **not** combine flags. Each item has its own flag for clean attribution.
8. Do **not** cache TCS without a tenant-update invalidation hook OR explicit security review of 60s eventual consistency.
9. Do **not** LLM-rerank in the hot path before Q2 ships.
10. Do **not** bundle TTFB and quality changes in one PR.
11. Do **not** raise `first` above 50 to compensate for low recall.
12. Do **not** ship E1 cutover until shadow-replay parity is green for 1 full week.
13. Do **not** tune `streamingWriterPool` (T11) or `MAX_IO_PARALLELISM` (T12) without per-pool saturation dashboard (M7+T10) live ≥7 days first.
14. Do **not** enable T2 AGG pool 8× without a load-test plan.
15. Do **not** roll out F-series UF features without O3 graceful shutdown landed.
16. Do **not** assume K2 (sidecar prompt-cache) is multi-hundred-$k. Sidecar serves Marathon-research, not main chat.
17. Do **not** ship A 2.2 (delta-style history). Use K1+A2.1 (cache_control) instead.
18. Do **not** ship A 2.4 (tool filtering 80→20) as a hard pre-LLM filter. Use **A2.4-DUAL**.
19. Do **not** ship A 2.3 (Haiku for orchestration) without paired LLMJudge A/B + auto-fallback. Use **A2.3-GUARDED**.
20. Do **not** ship A 2.5 (rule-based complexity classifier) as 100% rule-based. Use **A2.5-GUARDED**.
21. Do **not** assume `RedisCacheClient` is unused (B's K6 was INFERRED). Verify with `grep -rn "RedisCacheClient" modules/` first.
22. **NEW for v5:** Do **not** use SETNX for Insights idempotency (Plan A v2 correctly identifies this is the wrong abstraction). Use **`enqueuedAt` timestamp comparison** — checks "is work done", not "is lock held".
23. **NEW for v5:** Do **not** use fire-and-forget for Insights notification (Plan A v2 correctly identifies this loses notifications permanently). Use **retry+throw → SQS redrive** with N3 idempotency to prevent double-LLM-cost on redrive.
24. **NEW for v5:** Do **not** ship Insights N10 (prompt deduplication) past 50% rollout until `PROMPT_CACHE_HIT` confirms upstream caching works. Otherwise the -72% input-token claim is unrealised and the refactor is pure churn.
25. **NEW for v5:** Do **not** treat Insights and Chat as competing for the same engineering capacity. They have **zero file overlap**; staff in parallel.

---
## 12. Risk register (Top 8; 2 new for v5)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | C1 compaction-persist corruption causes wrong-context replies | M | H | Versioned schema + checksum + fall-back recompute on mismatch; 5% canary 1wk |
| 2 | Q1/Q2 LLM rerank surfaces lower-quality content | L | H | Eval gate (Q12) blocks promotion if factual <baseline; kill-switch |
| 3 | L3/L23 reactive conversion races / leaked subscriptions | M | H | 24h soak; thread-leak detector; bounded scheduler; staged rollout |
| 4 | E1 A2AChatExecutor cutover regression (1,370 LoC) | M | H | Shadow-replay parity ≥10k turns; auto-rollback on parity divergence (deps O1) |
| 5 | C3/C4 model-downsizing degrades quality | M | M | Paired-prompt A/B; rollback if Δquality < -2pp |
| 6 | T-series throughput tuning over-provisions and starves another pool | M | M | Land M7 saturation panel BEFORE T11/T12; gated rollout; per-pool eviction metric |
| 7 | A2.4-DUAL tool-args pruning surfaces "tool unavailable" UX when LLM names a pruned tool | M | M | Always-fallback-to-full-catalog on next turn; emit metric; observe in 5% cohort 1wk |
| **8 (NEW)** | **N10 (Insights prompt dedup) ships before prompt-cache works → pure refactor churn with no -72% saving** | M | M | **HOLD at 50% rollout until `PROMPT_CACHE_HIT` confirms; if cache doesn't engage, REVERT N10 — refactor was a no-op** |
| **9 (NEW)** | **N1 (Insights cache 1d→7d) shows users stale insights** | L | M | `forceCacheMiss` available; dynamic config for tuning (try 7d → fall back to 3d if user complaints rise); `forceCacheMiss` rate-limit (Q10) prevents per-user DoS |

---

## 13. End-state acceptance criteria (per goal)

| Goal | Criterion |
|---|---|
| AIFC FactualConsistency 70 | Nightly LLMJudge ≥70% on 300-row golden set, 7-day rolling, page-search ON cohort |
| AIFC ContextualRecall 65 | Nightly recall ≥65%, 7-day rolling |
| AIFC Relevancy 70 | Nightly relevancy ≥70%, 7-day rolling |
| ChatSLO 99.9 | 28-day rolling success ≥99.85%; ≥99.9% needs multi-provider failover (out of scope) |
| RovoMAU 150k | TTFB p50 -25%; activation lift +X%; F-series uplift on cohort A/B |
| Throughput at 150k MAU peak | Sustained ≥2,900 req/s for 5 min on staging load test; pool exhaustion alerts -90% in prod |
| **Insights cost (NEW)** | **N1 verified -80% LLM cost via Socrates `convo_ai_usage` per-feature attribution; N10 verified -72% input tokens via PROMPT_CACHE_HIT metric** |
| **Insights stability (NEW)** | **N3 verified 0 duplicate generations; <0.5% stuck-generating rate; N5 verified user-notified rate ≥99.5% on transient failures** |
| Cost $/turn total | -$215-375K/mo Chat + -80% Insights LLM cost realised in M4/M8 finance attribution |
| EngVelocity LoC removed | A2AChatExecutor + v1 410 routes deleted (≥1,455 LoC); AIFEATURE split |
| Operational readiness | O1-O6 all in production; chaos drill validates auto-rollback within 5 min |

---

## 14. Honest comparison: which plan was best?

| Dimension | Plan A v2 (rewritten) | Plan B (sorted-sunbeam) | My v4 |
|---|---|---|---|
| Code-anchoring (file:line) | **Excellent** | Excellent | Excellent (synthesised) |
| **Rovo Insights coverage** | **Excellent (NEW; entire domain)** | Absent | Absent |
| **AIFC 57pp factual recovery** | Absent | **Excellent (Q1-Q14)** | Strong (kept B's Q-series) |
| Throughput coverage | Strong (5 quick wins) | **Strongest (T-series + M7 gates)** | Both combined |
| LLM cost wins | $25-40K/mo Chat + -80% Insights | $215-375K/mo (with caveats) | $215-375K/mo + Plan A's specifics |
| **User-facing-preservation** | Statement of intent only | **Best-in-class (dual-list pattern)** | B's discipline applied to A's risky items |
| Operational infra-blockers | Mentioned in Tier 0 | **Mandatory Phase 0** | Mandatory Phase 0 |
| Measurement-first discipline | Per-item verification | **"No item ships until M-series live" (M1-M7)** | M1-M7 + per-item |
| Honest caveats | Architectural-decisions table is excellent | **Best (section L Limitations + 16 anti-goals)** | Best + 5 new anti-goals |
| Architectural-decisions documented | **Best (3 named alternatives with verdicts)** | None | Adopted from A v2 in v5 |
| Cross-plan self-comparison | **Honest scorecard table** | None | Critical compare in §0 |
| Single-plan answer reasoning | **Honest and well-reasoned** | None | Detailed |

**Each plan is genuinely the best at something:**
- **Plan A v2** is the best on **Insights** (entire missing domain) and on **architectural-decisions documentation**.
- **Plan B** is the best on **AIFC quality**, **UF preservation**, **measurement-first**, and **operational rigor**.
- **My v4** is the best on **integrating B's discipline with A's specifics + my v2 contributions**.

---

## 15. Single-plan answer: if I had to pick ONE

**I would pick Plan B (`sorted-sunbeam.md`).**

This is the same answer as v4. The new evidence from Plan A v2 doesn't change it — it actually **strengthens** the case by demonstrating that even A's own author, when forced to pick, **picks "distributed-hearth + S7"**, not the rewritten meta-plan itself. That's a tell: the meta-plan is a **reading aid**, not a deployable plan.

Reasoning, weighed against Plan A v2 specifically:

1. **Plan B closes the AIFC 57pp factual-consistency regression.** This is a **beta-GA blocker**. Plan A v2 still doesn't address this. The gap is not "Plan A v2 should add Q-series" — the gap is that **without this work, AIFC ships at 13% factual consistency and the entire AIFC bet collapses**, regardless of how fast/cheap Chat is or how clean Insights is.

2. **Plan B's user-facing-preservation discipline is structural.** Plan A v2's "Constraint: NO user-facing behavior changes. … Items that could affect quality (model selection, tool filtering) must be A/B tested" is a *statement*, not a *mechanism*. The user explicitly said "avoid changing user-facing behavior, for example, ranking by recency → ranking by relevance, such change might break existing user experience." That is **exactly** what Plan A's items 2.3 (Haiku swap) and 2.4 (tool filter 80→20) risk doing. Plan B's `uiOrdered`/`llmOrdered` dual-list pattern + the explicit "do not remove `lastModified` UI ordering" anti-goal are the only structural guarantee against it.

3. **Plan B's measurement-first rule is enforced.** "No item ships claiming impact until the relevant M* is live." Plan A v2 has solid per-item verification (Section 4) but no enforcement mechanism. Without M-series gating, A's "$25-40K/mo" claims and v5's "-72% Insights tokens" cannot be validated.

4. **Plan B's Phase 0 operational rigor (O1-O6) is non-negotiable for 30+ flag rollouts.** Plan A v2 does treat infra in Tier 0 (Q2-Q6 are Day-1 quick wins) — but **does not include O1 auto-rollback**. This is the single biggest missing dependency for any flagged rollout. Without it, every flagged change is a single-keystroke production incident waiting to happen.

5. **Plan A v2's architectural decisions are excellent and v5 adopts them ALL** — but they apply to the **Insights** workstream, which Plan B doesn't cover. So the right answer is **"pick B as the structure; layer in Plan A v2's Insights workstream as N-series, with A v2's architectural decisions adopted verbatim"** — exactly what v5 does.

**Honest cost of picking B alone:**
- Loses the entire Insights workstream (N1-N11) → forfeits the **-80% Insights LLM cost** quick win (15 minutes of work) and the **5-10s p95** Insights latency improvement.
- Loses Plan A's specific code-anchored Chat critical-path items (A 1.1-1.6) and token-counter fixes (A 3.1-3.6).

**That's why the right answer is "B + Plan A v2's Insights N-series + Plan A v2's chat critical-path A 1.x + token-counter A 3.x"** — which is the v5 plan.

**If forced to a single name: Plan B.** It would still leave value on the table (~$15-25K/mo + ~500ms in Chat latency + the entire -80% Insights cost win), but it would NOT ship a user-trust regression, NOT ship un-rollback-able experiments, NOT ship un-measured cost claims, and NOT ship the AIFC quality crisis unaddressed.

**Compare with Plan A v2's own pick** ("distributed-hearth + S7"): A v2 picks against B because A v2 reads the SLO as "send-message" → so optimise Chat. That's correct **for the SLO goal alone**, but it's **wrong for the AIFC goal** (which is a separately-tracked beta-GA blocker, not part of the chat SLO). Plan B is the only plan that addresses both. The integrated answer (v5) gets all three: Chat SLO + Insights cost + AIFC quality.

---

## 16. Summary

- **v5 = Plan B's structure + Plan A v2's Insights N-series + Plan A v2's architectural decisions (enqueuedAt, retry+throw, 120s wall-clock) + my v4's re-scoping of A's UF-risky items + 4 new anti-goals (#22-#25).**
- **All ~120 items are tagged with goal, impact, confidence, effort, UF-status, flag, exit-criterion.**
- **All retrieval/ranking changes use the dual-list pattern.**
- **A's items 2.2/2.3/2.4/2.5 are re-scoped as A2.x-RECAST/GUARDED/DUAL/GUARDED.**
- **Phase 0 operational infra (O1-O6) and measurement plan (M1-M8 — M8 NEW for Insights) are hard prerequisites.**
- **Honest caveats preserved and extended; architectural decisions for Insights documented with verdicts.**
- **Single-plan answer: Plan B** — for AIFC quality, UF discipline, measurement-first, Phase-0 operations, and honest caveats — with explicit acknowledgment that Plan A v2's Insights N-series and architectural decisions are net-new value worth layering in.

---

## 17. What's gained vs each input plan

| Item | Plan A v2 alone | Plan B alone | v5 Integrated |
|---|---|---|---|
| AIFC 57pp recovery | absent | strong | strong (B's Q-series, fully kept) |
| Insights workstream | strong (NEW) | absent | strong (A v2's N-series, fully kept with B's discipline) |
| Insights architectural decisions | strong (3 named alternatives + verdicts) | n/a | strong (verbatim adoption) |
| Throughput envelope | 5 quick wins | 14 items + M7 gates | Both: A v2's Day-1 wins + B's instrumentation discipline |
| LLM cost (Chat) | $25-40K/mo | $215-375K/mo (with caveats) | $215-375K/mo + A v2's specific code-anchored fixes |
| LLM cost (Insights) | -80% in 1 line + -72% with prompt-cache | absent | both |
| User-facing safety | statement only | structural (dual-list) | structural |
| Operational infra | Tier 0 quick-wins | Phase 0 mandatory | Phase 0 mandatory |
| Measurement discipline | per-item | "no-ship-until-M-live" | "no-ship-until-M-live" + per-item |
| Code-line specifics | excellent | excellent | both; ~30 net new file:line citations |
| Honest caveats | architectural-decisions table | section L + anti-goals | named + extended (4 new for v5) |
| Action items count | ~50 | ~80 | ~120 (deduplicated) |

End of integrated v5 plan.
