# Convo AI / Rovo Chat — Integrated v6 Plan

> **Synthesis of three living plans (re-read 2026-05-04):**
> - **Plan A** (`~/.claude/plans/do-this-again-here-zazzy-scroll.md`, **270 lines** — itself a brutally honest meta-comparison; new file replaces the prior `distributed-hearth.md`)
> - **Plan B** (`_plan/convo_ai/here-is-codebase-docs-sorted-sunbeam.md`, 420 lines — unchanged)
> - **My v5** (`_plan/convo_ai/INTEGRATED_PLAN_v5_synthesis.md`, 427 lines)
>
> **Status:** PROPOSED · supersedes v5. Date: 2026-05-04.
> **Method:** verified Plan A v3's critique of v5; confirmed 3 of its 5 named blind spots are real; v6 fixes them.

---

## 0. The headline finding: Plan A v3 caught real defects in my v5

Plan A is now `do-this-again-here-zazzy-scroll.md` — and it is the **most useful plan in the corpus**, because it is **itself a critique** that verified every key claim with code-reading and named specific defects in my v4. I re-verified its critique against my v5 just now:

| Plan A v3's critique of my v4/v5 | Verdict (re-checked against v5) |
|---|---|
| **"v4 dropped Insights items"** | ✅ Already fixed in v5 (N1–N11 workstream added) |
| **"v4 dropped v2's reliability items"** (per-tool deadline, mid-stream failover, idempotency, tool-error feedback, structured cancellation) | ❌ **STILL TRUE in v5** (grep returns 0 hits on `per-tool deadline`, `withTimeoutOrNull`, `mid-stream failover`, `tool-error feedback`, `idempotency key`, `structured cancellation`) — **v6 fixes** |
| **"v4 inherits B's contradictory 99.9% SLO claim"** | ⚠️ **PARTIALLY fixed in v5** — anti-goal #3 says 99.85% honestly, but the goal-ledger row 96 still claims 99.9% as "target". **v6 reconciles** |
| **"B's F5/F6/F9 + R-series are scope creep"** | ❌ **Not addressed in v5** — v6 deprioritizes them |
| **"B's $215-375K/mo is aggressive; honest is $168-290K"** | ❌ **Not corrected in v5** — v6 uses Plan A v3's honest range |

**This means v6 is a real, material improvement on v5, not a cosmetic re-shuffle.** The 5 fixes below close concrete user-trust risks (idempotency, mid-stream failover, per-tool deadline) and cost-credibility risks (honest $ figures).

**v6 also reaffirms what v5 got right** and keeps it intact.

---

## 1. The 5 net-new fixes in v6 (vs v5)

### Fix 1 — Reliability axis (R-series): the missing v2 items

These items address **silent user-trust bugs and the 99.9% SLO ceiling**. Plan A v3 is right that they are higher-leverage than the F-series feature requests. v6 promotes them into the **Top-20 ranked list** alongside O / N / Q / T items.

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag |
|---|---|---|---|---|------|--------|-----|------|
| **R-1A** | **Per-tool deadline:** wrap `toolExecutor.executeSingle()` in `withTimeoutOrNull(30_000)` at `SimpleLoopWorkflowExecutorImpl.kt:914-920`; on timeout, append synthetic `tool_error` to `functionMessages` (configurable per-tool override via tool-registry) | v2 (verified) | Reliability / Latency | Eliminates infinite-hang on a slow tool; reduces p99 conversation latency by however long the slowest tool stalls | 1.0 | S | no | `ROVO_TOOL_DEADLINE_ENABLED` |
| **R-1B** | **Tool-error feedback to LLM:** when a tool throws, append a structured `FunctionMessage(role=tool, isError=true, content=<sanitised>)` and let the loop continue (max 2 error retries per tool) at `SimpleLoopWorkflowExecutorImpl.kt:938-962` | v2 (verified) | Reliability / Quality | LLM can self-correct on tool failure (today it gets an exception and the loop dies) | 1.0 | S | no | `ROVO_TOOL_ERROR_FEEDBACK` |
| **R-1C** | **Mid-stream failover (soft resume):** in `LLMServiceImpl.kt:1367-1404 withStreamFallbackModelRetry()`, buffer last completed safe-checkpoint chunk; on stream-error after `hasReceivedItem=true`, emit typed `STREAM_FALLBACK` event and replay to fallback model with `previous_partial_text` re-injected | v2 (verified gap) | Reliability / SLO | **The ONLY lever to push past 99.85% SLO** toward 99.9% (today's failover only fires pre-emission) | 1.0 | M | conditional (visible "[continued from fallback model]" annotation; release note) | `ROVO_STREAM_FAILOVER_SOFT_RESUME` |
| **R-6A** | **Idempotency keys for side-effecting tools:** tool-registry declares `isSideEffecting + idempotencyKeyTemplate`; before executing, compute key from `(conversationId, messageId, toolCallId, argsHash)`, store in `ProcessedToolCallStore` (DynamoDB conditional put, 30-min TTL); skip on duplicate, return cached result | v2 (verified gap) | Reliability / Trust | **Eliminates duplicate Jira tickets / Confluence pages on retry** — a user-visible silent corruption today | 1.0 | M | no | `ROVO_TOOL_IDEMPOTENCY_KEYS` |
| **R-6E** | **Structured cancellation:** replace detached `launch { ... }` in `RovoChatService` and `LLMServiceImpl` with `coroutineScope { ... }`; add `currentCoroutineContext().ensureActive()` checkpoints between tool calls | v2 (verified) | Cost / Stability | -80% token waste from orphaned post-disconnect work; emit `convoai.cancellation.observed_ms` metric | 1.0 | S | no | none (refactor) |

**Why these were dropped from v4/v5 and need to come back now:** v4 said it integrated v2 but did not actually populate v2 items into the workstream tables (Plan A v3's grade: F). v5 added Insights but still missed v2 reliability. v6 adds them as the **R-series** (Reliability), parallel to Plan B's other letter-coded workstreams. Each item is verified-absent in current code (Plan A v3 cited the exact line numbers and confirmed via reading).

---

### Fix 2 — SLO honesty: 99.85% is the achievable target without R-1C; 99.9% requires R-1C

| State | Achievable SLO | What gets you there |
|---|---|---|
| Today | 99.6% | (baseline) |
| After L3 + T1 + T0b + L18 + R-1A + R-1B (no mid-stream failover) | **99.85%** | Eliminate the ~0.25pp of failures from blocking calls + Heimdall stalls + tool hangs + tool-error throws |
| After R-1C ships | **99.9%** | Mid-stream failover lets surviving providers handle the last 0.05pp |
| Beyond 99.9% | requires multi-region / multi-provider primary | (out of scope for 12wk) |

**v6 corrects the goal ledger:**
- Row 4 (Chat send-msg SLO): target = **99.85% (without R-1C) → 99.9% (with R-1C)**, NOT a flat 99.9%.
- Acceptance criterion: 28-day rolling success ≥99.85% as **mandatory**, ≥99.9% as **stretch (gated on R-1C)**.

This single correction matters because it stops the team from over-promising on the canonical SLO target.

---

### Fix 3 — Cost honesty: $168-290K/mo (Plan A v3's verified range), not $215-375K/mo

| Source | Range | Why |
|---|---|---|
| Plan B claimed | $215-375K/mo | Aggressive; bundles INFERRED + over-scoped + A/B-required items |
| Plan A v3 verified | **$168-290K/mo** | Only verified items; excludes K2 sidecar (Marathon-only), K6 RedisCacheClient (INFERRED unverified), and conditional-on-A/B items |
| v6 adopts | **$168-290K/mo** as the headline; $215-375K/mo only with explicit "if A/B + INFERRED items all land" caveat |

**Breakdown (Plan A v3's table, adopted verbatim):**

| Category | Items | Honest range |
|---|---|---|
| Compaction persist (C1) | Verified | $80-120K/mo |
| Prompt cache enable (K1+A2.1) | Verified gap | $40-80K/mo |
| Insights CACHE_TIMEOUT (N1/S7) | Verified, 1-line | $15-30K/mo |
| Classifier debounce (C2) | Verified | $15-25K/mo |
| Model downsizing (C3+C4) | Requires A/B | $8-13K/mo (if quality holds) |
| Smaller items (C6, C8, C9) | Mixed confidence | $10-22K/mo |
| **Total honest range** | | **$168-290K/mo** |

Items NOT counted: K2 (~$5-10K/mo Marathon-only), K6 (INFERRED), A2.3-GUARDED + A2.4-DUAL + A2.5-GUARDED (require A/B + dual-list).

---

### Fix 4 — Deprioritize F-series scope creep + R-series stalled-decisions to the "post-12wk" pile

Plan A v3 is right: in 12 weeks with 6-8 engineers, every item that doesn't move a top goal gap is engineering bandwidth stolen from items that do. Demote:

| Item | Why demoted | Where it goes |
|---|---|---|
| F5 (citation hover preview) | Feature request; doesn't close any goal gap | Post-12wk feature backlog |
| F6 (confidence badges) | Speculative UX; medium effort; low evidence | Post-12wk feature backlog |
| F9 (stale-source warning) | Low impact | Post-12wk feature backlog |
| R1-R7 (sidecar sunset, Loom scope, Socrates alignment, S3 audit, ERS CI, SageMaker, Actuator hardening) | Organizational decisions, not engineering work | Separate decision log |
| T11 (`streamingWriterPool=1024` re-tune) | INFERRED; unsupported | Hold for ≥7d M7 data |
| T12 (`MAX_IO_PARALLELISM=3072` re-tune) | INFERRED; unsupported | Hold for ≥7d M7 data |
| E6 (AIFEATURE monolith split) | Large effort, low goal-impact | Post-12wk velocity backlog |
| E7 (storage ADR Postgres/DynamoDB) | Decision, not engineering; ADR-only in 12wk anyway | Decision log |

**Items that STAY in the F-series** because they directly close goal gaps:
- **F1** (personality-experiment scope-fix) — verified production leak; trust + MAU
- **F2** (starter prompts) — Day-0 activation lever
- **F4** (last-conversation resume) — Day-1 retention lever
- **F7** (graceful error UX) — directly addresses "lost answer" trust loss
- **F8** (recent-activity context injection) — quality / clarification-turn-rate
- **F10** (feedback → ARIZE) — **load-bearing for M2** (no shortcut)
- **F11** (base-prompt dynamic config) — eng velocity (deploy-free prompt iteration)

The cut is ~7 items, freeing ~6-8 eng-weeks for R-series reliability work.

---

### Fix 5 — Add a "What to cut if constrained" section (sequenced de-scope plan)

Plan A v3 noted v4 has 100+ items with no contingency. Real teams deliver 60-70%. v6 adds an explicit cut-order:

| Cut tier | Items | Rationale |
|---|---|---|
| **Cut first** (if 8-week sprint instead of 12) | All deprioritized items above + Q6-Q10 (per-source rerank) + L9, L10, L13, L14, L15 (smaller latency wins) | None move a top goal gap by ≥1pp |
| **Cut second** (if 6-week sprint) | A2.4-DUAL + A2.5-GUARDED + C7 + K6 + K7 + K8 | Conditional cost wins; not load-bearing |
| **Cut third** (if 4-week sprint) | F2-F11 + N10 + L17 + L21 | Defer activation lift + Insights prompt dedup + some L-items |
| **NEVER cut** | O1-O6 + M1-M8 + Q1-Q5 + Q12-Q14 + L1 + L3 + L8 + T1 + T0a/b/c/d/e + R-1A + R-1B + R-6A + N1 + N2 + N3 + C1 + K1 | These are the load-bearing items: AIFC GA, Phase-0 ops, hot-path stability, reliability, Insights quick-wins |

---

## 2. The two principles v5 already got right (kept verbatim)

1. **Plan B's framework wholesale** — workstream codes (O/Q/L/T/C/K/F/E + new N + new R), Phase 0 operational blockers, M1-M8 measurement-first, dual-list UF-preservation pattern, anti-goals as enforcement.
2. **Re-scoping of Plan A's UF-risky items** — A2.2-RECAST, A2.3-GUARDED, A2.4-DUAL, A2.5-GUARDED.

---
## 3. Goals & metric ledger (corrected per Fix 2 + Fix 3)

| Goal | Baseline | Target | Gap | Source |
|---|---|---|---|---|
| Rovo MAU | ~100.3k | 150k by H2 FY26 | +50% | Atlas ATLAS-124112 |
| **Chat send-msg SLO (mandatory)** | **99.6%** | **99.85%** (without R-1C) | **+0.25pp** | TOME `convo_ai/locals.tf` + Plan A v3 honesty |
| **Chat send-msg SLO (stretch)** | 99.6% | **99.9%** (gated on R-1C mid-stream failover) | +0.3pp | Per Plan A v3: 99.9% requires R-1C |
| Agent Studio create-scenario SLO | 98.2% | 99.99% | +1.8pp | TOME |
| **AIFC factual consistency** | **13%** (regressed from 80%) | **≥70%** | **+57pp** (beta-GA blocker) | AIFC TWCLR2 |
| AIFC contextual recall | 47% | ≥65% | +18pp | AIFC Maturity Gap |
| AIFC contextual relevancy | 40-44% | ≥70% | +27pp | AIFC Maturity Gap |
| Throughput at 150k MAU peak | ~1,500 req/s | ~2,900 req/s (5× burst) | -48% | Derived |
| **Insights LLM cost** | baseline | -80% (N1 alone) + -72% input tokens (N10 if cache hits) | huge | Plan A v2/v3 |
| **Cost / month (Chat) — honest** | baseline | **-$168-290K/mo realised** (per Plan A v3 verified range) | depends | Plan A v3 verified |
| Cost / month (Chat) — stretch | baseline | -$215-375K/mo (only if INFERRED + A/B items all land) | depends | Plan B's claim with caveats |
| Quality regression MTTD | >quarter (the 80→13 went undetected) | <1 day | huge | The AIFC regression itself proves the gap |

**Hard SLO ceiling:** OpenAI Scale Tier 99.9%. R-1C mid-stream failover is the only lever past it within the LLM provider's bounds; multi-region/multi-provider primary is required beyond 99.9%.

---

## 4. Top-25 by goal-impact / risk (corrected v6 ranking)

Re-ranked with the R-series and Plan A v3's deprioritization applied. Items 21-25 NEW in v6 promote v2 reliability items.

| # | Code | Item | Source | Goal | Impact | Conf | Effort | UF | Flag |
|---|------|------|--------|------|------|------|--------|----|------|
| 1 | O1 | Auto-rollback wiring (SignalFx → Statsig API auto-flip) | B | InfraBlocker | Enables every flagged item; chaos-drill: regressed flag flips 0% in ≤5min | 1.0 | M | no | — |
| 2 | N1 (S7) | Insights `CACHE_TIMEOUT=1d → 7d` at `RovoInsightsV1Controller.kt:193` | A | Insights Cost | -80% Insights LLM cost in 1 line | 1.0 | XS (15min) | no | dynamic config |
| 3 | T0a | Async pool 96→256 + queueCapacity=1000 with 503 reject (`application.yml:160-162`) | A+B | Throughput / Stability | Prevent OOM at sustained burst; +200-400 req/s headroom | 1.0 | S | no | — |
| 4 | T0b | Heimdall rate-limiter timeout 3000ms→500ms with circuit-break (`ExperienceRateLimitFilter.kt:64`) | A | SLO / Tail | -3s worst-case block | 1.0 | S | no | — |
| 5 | T1 | Bound `Channel.UNLIMITED` in `HttpRequestStreamingWriter.kt:44` | B | Throughput / Memory | Closes verified known-risk; eliminates heap-pressure on slow clients | 1.0 | S | no | `ROVO_STREAMING_BOUNDED_CHANNEL` |
| 6 | N2 (L2) | Insights cancellation isolation: `coroutineScope` → `supervisorScope + runCatching` at `RovoInsightsServiceImpl.kt:657` | A | Insights Stability | 12-min worst → 240s/type; 5/6 deliver on 1 failure | 1.0 | S | no | `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED` |
| 7 | **R-6A** (NEW in v6) | **Idempotency keys for side-effecting tools** — eliminates duplicate Jira/Confluence creates on retry | v2 | Reliability / Trust | 0 user-visible duplicates; conditional put with 30-min TTL | 1.0 | M | no | `ROVO_TOOL_IDEMPOTENCY_KEYS` |
| 8 | **R-1A** (NEW in v6) | **Per-tool deadline:** `withTimeoutOrNull(30_000)` around `toolExecutor.executeSingle()` at `SimpleLoopWorkflowExecutorImpl.kt:914-920` | v2 | Reliability / Latency | Eliminates infinite-hang on slow tools; reduces p99 conversation latency | 1.0 | S | no | `ROVO_TOOL_DEADLINE_ENABLED` |
| 9 | **R-1B** (NEW in v6) | **Tool-error feedback to LLM** — append structured `FunctionMessage(isError=true)` instead of throwing | v2 | Reliability / Quality | LLM self-correction on tool failure | 1.0 | S | no | `ROVO_TOOL_ERROR_FEEDBACK` |
| 10 | N4 (L1) | Insights N+1 person hydration → batch with Semaphore(16) at `RovoInsightsServiceImpl.kt:471-517` | A | Insights Latency | -5–8s p95 (54 sequential → ~4 batches) | 1.0 | M | no | `AIX_ROVO_INSIGHTS_HYDRATION_PARALLEL_ENABLED` |
| 11 | N3 (S1) | Insights idempotency via `enqueuedAt` timestamp + 120s wall-clock budget | A | Insights Stability | 0 duplicate generations; <0.5% stuck-rate | 1.0 | M | no | `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED` |
| 12 | C1 | Persist compaction summary (versioned + checksummed) at `ContextCompactionServiceImpl.kt` | B | Cost | -$80-120K/mo | 1.0 | M | no | `ROVO_COMPACTION_PERSIST` |
| 13 | Q1 | PageSearch L2 rerank for LLM context (dual-list pattern; UI order unchanged) at `ConfluencePageSearchServiceImpl.kt:60` | B | AIFC Factual | +15-25pp on golden eval | 1.0 | S | conditional (split) | `ROVO_PAGESEARCH_LLM_RERANK` |
| 14 | K1+A2.1 | Anthropic prompt-cache: enable `cache_control` on system messages + audit assembler usage | A+B | Cost | -$40-80K/mo; cache hit ≥70% | 1.0 | M | no | (it's a fix) |
| 15 | L1 | TCS Caffeine cache at `AsyncTenantContextService.kt:35-260` | B | TTFB | -100-200ms × N (avg -150ms p50); cache hit ≥95% | 1.0 | S | no | `ROVO_TCS_CACHE` |
| 16 | L3 | Remove `runBlockingWithContext` AI_EDITOR path at `ChatV1Controller.kt:267`; reactive Flux | B | ChatSLO | +0.1pp SLO; -100-300ms tail | 1.0 | M | no | `ROVO_CHAT_NONBLOCKING_STREAM` |
| 17 | N5 (S2) | Insights notification: retry+throw → SQS redrive (NOT fire-and-forget) | A | Insights Trust | Users no longer cached-but-not-notified | 1.0 | S | no | (deps N3) |
| 18 | T2+T3 | AGG WebClient pool 4×→8× + eviction + HTTP/2 multiplex + codec 24MB→64MB | B | Throughput | +600 req/s peak; +30% throughput | 1.0 | S | no | `ROVO_AGG_POOL_LARGE` + `ROVO_AGG_HTTP2` |
| 19 | **R-1C** (NEW in v6) | **Mid-stream failover (soft resume)** — buffer last checkpoint; on stream-error post-first-chunk, restart on fallback model | v2 | Reliability / SLO | **The ONLY lever past 99.85% toward 99.9%** | 1.0 | M | conditional (visible annotation; release note) | `ROVO_STREAM_FAILOVER_SOFT_RESUME` |
| 20 | A2.4-DUAL | Tool relevance pre-filter — full catalog visible in cached prefix; only **args schemas** pruned to top-20 | A re-scoped | Cost | -40-60% tool-token cost (~$3-4.5K/mo) | 0.7 | M | conditional (LLM-context only) | `ROVO_TOOL_FILTER_DUAL` |
| 21 | A2.3-GUARDED | Default to Haiku 4.5 for orchestration with paired LLMJudge A/B + auto-fallback to GPT-4-1 on tool-selection-confidence-low | A re-scoped | Cost | -65-75% orchestration cost (~$8-12K/mo) | 0.7 | M | conditional | `SAIN_ORCHESTRATION_HAIKU_4_5` (flip default) |
| 22 | F1 | Personality-experiment scope-fix (chat-only, NOT SAIN/Search) — verified production leak at `RovoChatAnswerGeneratorHelper.kt:435` | B | Trust / MAU | Unblocks rollout; protects search-path factual tone | 1.0 | S | yes (release note) | extends existing personality flag |
| 23 | C2 | Debounce in-session classifier at `InSessionSegmentationServiceImpl.kt:75-108` | B | Cost | -$15-25K/mo; classifier calls/turn ≤0.3 | 1.0 | S | no | `ROVO_SEGMENTATION_DEBOUNCE` |
| 24 | **R-6E** (NEW in v6) | **Structured cancellation** — replace detached `launch` with `coroutineScope`; `ensureActive()` between tool calls | v2 | Cost / Stability | -80% token waste from orphaned post-disconnect work | 1.0 | S | no | none (refactor) |
| 25 | N10 (E1) | Insights prompt deduplication: 118KB shared prefix across 6 templates | A | Insights Cost | -72% input tokens (~$2.8M/yr at scale) — gated on PROMPT_CACHE_HIT | 0.7 | M | conditional | `ROVO_INSIGHTS_PROMPT_VERSION` |

**Items 26-50** (significant, second tier): Q2 (bodyExcerpt additive), Q4 (grounding system prompt), L4 (parallel pre-LLM gates), L8 (request-scoped FF memoization), N6 (hoist Insights Statsig), N7 (Insights retry jitter), N8 (`structuredOutputEnabled=true`), N9 (hoist `createConversationId`), N11 (drop full-prompt log), C8 (classifier dedup), C9 (DeepResearch convergence), K1 audits, F2 (starter prompts), F4 (last-conversation resume), F7 (graceful error UX), F8 (recent-activity context), F10 (feedback → ARIZE), F11 (base-prompt dynamic config), Plan A's L-A1.1-1.6 + K-A3.1-3.6 + K-A4.1-4.3.

---

## 5. Anti-goals (extended in v6 with 4 new ones from Plan A v3's critique)

(Items 1-25 unchanged from v5. New items 26-29 below.)

26. **NEW (Fix 2):** Do **not** claim 99.9% SLO without R-1C (mid-stream failover) shipped. Honest target without R-1C is 99.85%. Plan B's contradictory "+0.3pp full gap" claim must be corrected.
27. **NEW (Fix 3):** Do **not** quote $215-375K/mo as the headline cost saving. Honest verified range is **$168-290K/mo**. The higher figure is only achievable IF every INFERRED + A/B-conditional item lands AND retains quality.
28. **NEW (Fix 1):** Do **not** plan v2's reliability items (R-1A, R-1B, R-1C, R-6A, R-6E) as "later" or "out of scope." They are higher-leverage than F-series feature requests because they close user-trust silent-bug risks AND the SLO ceiling.
29. **NEW (Fix 4):** Do **not** carry F5 (citation hover), F6 (confidence badges), F9 (stale-source warning), R1-R7 (stalled decisions), T11/T12 (INFERRED pool re-tunes), E6 (AIFEATURE split), E7 (storage ADR) as in-scope for the 12wk plan. Move to post-12wk backlog. They consume bandwidth needed for the load-bearing items.

---

## 6. Single-plan answer (re-affirmed in v6): **Plan B (`sorted-sunbeam.md`)**

This is the **fourth** time I've answered this question (v3, v4, v5, v6) and the answer is **the same — Plan B** — but the reasoning has now been **independently verified by Plan A v3** (which is itself a meta-comparison from a different investigator). Two independent honest critiques converging on the same answer is strong evidence.

**Why Plan B remains the right pick (Plan A v3's reasoning, adopted):**

1. **AIFC 57pp factual-consistency regression.** Plan B is the only plan that addresses this beta-GA-blocking quality crisis. Plan A doesn't address AIFC quality at all. v4/v5/v6 all inherit B's coverage.

2. **User-facing-preservation is structural in B (dual-list pattern).** The user explicitly warned "avoid changing user-facing behavior, for example, ranking by recency → ranking by relevance." Plan B's `uiOrdered`/`llmOrdered` dual-list pattern IS that structural guarantee. Plan A's items 2.3 (Haiku swap) and 2.4 (tool filter 80→20) would silently change LLM-visible behavior under "gated by A/B" — that's not enough.

3. **Measurement-first (M1-M7) is enforced.** "No item ships claiming impact until the relevant M* is live." Plan A has solid per-item verification but no enforcement mechanism. Without M-series gating, claimed savings can't be validated.

4. **Phase-0 operational rigor (O1-O6) is non-negotiable.** Plan A doesn't include O1 auto-rollback as a hard prerequisite. Without it, every flagged change is a single-keystroke production incident.

5. **Plan B is the only plan whose gaps are layerable.** The gaps are concrete, code-anchored items (Insights workstream, v2 reliability items, A's specific config diffs). They can be added as new workstreams without restructuring B. Plan A's gaps (no AIFC, no dual-list, no Phase 0) require architectural rework to fix.

**Honest cost of picking B alone (Plan A v3's table, adopted):**
- Loses Heimdall 3s timeout fix (-3s worst-case tail) → recoverable as T0b in week 2
- Loses Insights workstream (-80% Insights cost; -5-8s p95) → recoverable as N1-N11 in weeks 1-3
- Loses org.json triple-parse fix (-5-10ms × 50+ msgs) → recoverable as K-A3.1 in week 4
- Loses v2's per-tool deadline (R-1A) → recoverable as Top-8 item in week 3
- Loses v2's tool-error feedback (R-1B) → recoverable as Top-9 item in week 3
- Loses v2's mid-stream failover (R-1C) → recoverable as Top-19 item in week 5-7

**These are additive layers on top of B, not replacements** — which is exactly what v6 does.

**Compare with Plan A v3's own pick** (also Plan B): we converge. The v6 plan is "Plan B as the structure + A's specifics + A's Insights workstream + v2's reliability items + my v4/v5 dual-list re-scoping + Plan A v3's honest SLO and cost corrections."

---

## 7. Summary of v6 vs v5

| Aspect | v5 | v6 | Change |
|---|----|----|--------|
| Insights workstream (N1-N11) | ✅ added | ✅ kept | No change |
| Plan A architectural decisions for Insights | ✅ added | ✅ kept | No change |
| v2 reliability items (R-series) | ❌ missing | ✅ **added (R-1A, R-1B, R-1C, R-6A, R-6E)** | **NEW** — Top-7, Top-8, Top-9, Top-19, Top-24 |
| SLO honesty (99.85% vs 99.9%) | ⚠️ partial (anti-goal said 99.85% but goal table said 99.9%) | ✅ **reconciled** | **CORRECTED** |
| Cost figures | $215-375K/mo (B's aggressive range) | **$168-290K/mo (Plan A v3's verified range)** | **CORRECTED** |
| F-series scope creep | F5/F6/F9 in scope | F5/F6/F9 deprioritized to post-12wk | **DEMOTED** |
| R-series stalled decisions | R1-R7 in scope | Moved to decision log | **DEMOTED** |
| INFERRED pool re-tunes (T11/T12) | In Phase 6 | Moved to "hold for ≥7d M7 data" | **DEMOTED** |
| "What to cut if constrained" | absent | ✅ explicit cut-tier | **NEW** |
| Anti-goals count | 25 | 29 (4 new from Plan A v3's critique) | **+4** |
| Total in-scope items | ~120 | **~95-100 (after deprioritizations)** | **-20** |

**v6 is meaningfully better than v5** because Plan A v3 gave a real, honest critique that I verified line-by-line against v5's actual content. The Top-25 list is materially different: 5 new R-series items entered the top tier, 7 F/R/T items left scope.

End of integrated v6 plan.
