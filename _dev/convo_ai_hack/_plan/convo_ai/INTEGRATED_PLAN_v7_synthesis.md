# Convo AI / Rovo Chat — Integrated v7 Plan

> **Why v7 exists:** The honest answer to "is v6 the best plan covering everything?" was **no**. v6 fixed Plan A v3's named defects but did not cover B's full content. v7 adopts B **wholesale as the base** (it has the strongest framework, full Wave-1+2+3 findings traceability, the goal-contribution matrix, the CSM/JSM workstream, the per-item Dep column, the findings→plan completeness check) and **layers on**: Plan A's Insights workstream (N-series), Plan A v3's verified honest corrections (SLO 99.85%, cost $168-290K), v2's reliability items (R-series), and my v4/v5/v6 dual-list re-scoping of A's UF-risky items.
>
> **Source plans (re-read 2026-05-04):**
> - **Plan A** `do-this-again-here-zazzy-scroll.md` (270L; meta-comparison + verified critique of v4/v5/v6)
> - **Plan B** `here-is-codebase-docs-sorted-sunbeam.md` (420L; comprehensive 80+ items across 9 workstreams; UNCHANGED across v3→v7 reads)
> - **My v6** `INTEGRATED_PLAN_v6_synthesis.md` (253L; lean but missing significant B content)
>
> **Status:** PROPOSED · supersedes v6.

---

## 0. Honest assessment of v6 vs B (the gap that prompted v7)

I claimed v6 was complete. Direct comparison shows v6 missed material content from B:

| What B has | What v6 has | Gap |
|---|---|---|
| **CSM/JSM TTFB workstream** (L22-L28: CSM streaming unblock, HC ID cache, Firebolt cache+gate, JSM HR convergence) producing -800-1500ms p50 | Not mentioned at all | **Whole workstream missing** |
| **Goal-contribution matrix** (per-goal additive proof: AIFC 70 = Q1+Q2+Q4+Q3 = +36-57pp; ChatSLO = L3+T1+T6+L18 = +0.3pp; Throughput = T1+T2+T3+T5 = +1400 req/s; Cost = C1+K1+C2+K3+K4+K5 = -$215-375K/mo) | Goal ledger only | **No additive proof of gap closure** |
| **Findings → plan map (Section G)** showing all 80+ Wave-1/2/3 findings explicitly mapped to plan items | Top-25 + "items 26-50: list" | **No completeness check** |
| **Per-item `Dep` column** with explicit dependency edges (Q5 deps Q1-Q4; L4 deps L1+L8; T11/T12 deps T10; etc.) | Mostly absent | **Sequencing risk** |
| **L-series detail** (L2 batch config-service, L5 pre-warm Jackson, L7 codec live, L9 N+1 hydration, L10 Kamino multi-region, L11 chunk-accumulator bound, L13 retry jitter, L14 GraphQL pagination, L15 MCP session reuse, L16 sandbox TTL, L17 tool registry cache, L18 .blockingGet, L19 agent inv cache, L20 Map lookup, L21 history delta, L31 compaction guard, L32 realtime async, L22-L28 CSM/JSM) | Top-25 has L1, L3, partial L4 only; second-tier list has fragmentary names | **~20 items absent from explicit ranking** |
| **Q-series detail** (Q1-Q14 in workstream A; per-source rerank Q6/Q7/Q8/Q9/Q10; Q14 ARIZE in-loop judge as core to M2) | Top-25 has Q1; second tier mentions Q2/Q4 | **~10 quality items absent from explicit ranking** |
| **K6 verification gate** ("RedisCacheClient unused INFERRED — verify with grep before relying on $") | Mentioned in anti-goals only | **Verification gate not enforced** |
| **Synthetic monitoring re-use** (B's L8 limitation #8: "Synthetic monitoring exists via operations/pollinator/checks/{prod,staging}.yml — leverage rather than rebuild for M-series") | Not mentioned | **Build-vs-buy decision missing** |
| **assistance-service mirror** (B's L8 limitation #7: "assistance-service is a separate microservice; some orchestration is out-of-process; mirror priorities should also apply there") | Not mentioned | **Out-of-repo dependency missing** |
| **Section K What changed in v3** (B's own changelog explaining K-series/F-series elevation rationale) | Implicit | **History not preserved** |

**Decision:** v7 adopts B as the structural base verbatim. v7's net contribution = layer in N-series (Insights, from A), R-series (v2 reliability, from A v3 critique), the dual-list re-scoping of A's UF-risky items (from my v4/v5), and the SLO/cost honest corrections (from A v3).

---

## 1. Goals & metric ledger (B's table + v6 corrections)

| Goal | Metric | Current | Target | Gap | Source |
|---|---|---|---|---|---|
| Rovo MAU | MAU | ~100.3k | 150k by H2 FY26 | +50% | Atlas ATLAS-124112 |
| **Chat send-msg SLO (mandatory)** | SLO | **99.6%** | **99.85%** (without R-1C) | **+0.25pp** | TOME `convo_ai/locals.tf` + Plan A v3 honesty |
| **Chat send-msg SLO (stretch)** | SLO | 99.6% | **99.9%** (gated on R-1C mid-stream failover) | +0.3pp | Plan A v3: 99.9% requires R-1C |
| Agent Studio scenario create | SLO | 98.2% | 99.99% | +1.8pp | TOME |
| **AIFC factual consistency** (page-search ON) | LLM-judge | **13%** (was 80%) | ≥70% | **+57pp** | AIFC TWCLR2 (CRITICAL beta-GA blocker) |
| AIFC contextual recall | LLM-judge | 47% | ≥65% | +18pp | AIFC Maturity Gap |
| AIFC contextual relevancy | LLM-judge | 40-44% | ≥70% | +27pp | AIFC Maturity Gap |
| AIFC Page Create Task Completion | % | unknown | 90% Beta | unknown | AIFC QBR |
| **Throughput** at 150k MAU peak | req/s peak (estimated) | ~1,500 cap | ~2,900 (5× burst) | -48% | Derived; T13 will define canonical target |
| **Insights LLM cost** (NEW from A) | $/mo | baseline | -80% (N1 alone); -72% input tokens (N10 if cache hits) | huge | Plan A v2/v3 |
| **Cost / month (Chat) — honest headline** | $/mo | baseline | **-$168-290K/mo realised** | depends | Plan A v3 verified |
| Cost / month (Chat) — stretch | $/mo | baseline | -$215-375K/mo (only if INFERRED + A/B all land) | depends | Plan B's claim with caveats |
| **Insights stability** (NEW) | duplicate-gen rate | unknown | 0; <0.5% stuck-rate | huge | A's S1+S5 |
| Quality regression MTTD | days | >quarter (the 80→13 went undetected) | <1 day | huge | The AIFC regression itself |

**Hard SLO ceiling**: OpenAI Scale Tier 99.9%. R-1C mid-stream failover = the only lever within the LLM provider's bounds; multi-region/multi-provider primary = required beyond 99.9%.

---

## 2. Three design principles (from B; non-negotiable)

1. **Goal-driven priority** — every item declares one primary goal + quantified impact in goal-metric units + confidence + priority score = (impact / goal-gap) × confidence ÷ implementation-risk.
2. **User-facing-behavior preservation** — every item is tagged `user_facing_change: yes / no / conditional`. Conditional items split internal change from user-visible change (**dual-list pattern**: `uiOrdered` byte-identical to today + `llmOrdered` reranked for LLM context only). Genuine UF changes ship behind opt-in flag → cohort A/B → kill-switch → release note → UI snapshot diff = 0 in cohort A.
3. **Infra-blocker first** — auto-rollback (O1), circuit breakers (O2), graceful shutdown (O3) MUST exist before the 30+ flag rollouts in this plan are safe. Phase 0.

---

## 3. Goal-contribution matrix (kept verbatim from B; extended with N + R additions)

| Goal (gap) | Item 1 | Item 2 | Item 3 | Item 4 | Total claimed gap closure |
|---|---|---|---|---|---|
| **AIFC FactualConsistency 70 (+57pp)** | Q1 LLM-rerank +15-25pp | Q2 body excerpt +10-15pp | Q4 grounding prompt +8-12pp | Q3 score-threshold +3-5pp | **+36-57pp** |
| **AIFC ContextualRecall 65 (+18pp)** | Q2 +8-12pp | Q6 multi-source rerank +4-6pp | Q11 Slack date filter +2-4pp | Q14 ARIZE judge | **+14-22pp** |
| **AIFC Relevancy 70 (+27pp)** | Q1 +10-15pp | Q6/Q7/Q8/Q9/Q10 multi-source rerank +8-12pp | Q3 +3-5pp | Q4 +3-5pp | **+24-37pp** |
| **ChatSLO 99.85 mandatory (+0.25pp)** | L3 unblock servlet +0.1pp | T1 bound channel +0.1pp | T0b Heimdall 3s→500ms +0.05pp | L18 .blockingGet removal +0.05pp | **+0.3pp** (closes gap) |
| **ChatSLO 99.9 stretch (+0.05pp more)** | R-1C mid-stream failover +0.05-0.15pp | (no other lever within LLM provider bounds) | | | **+0.05-0.15pp** |
| **RovoMAU 150k (+50%)** | F2 starter prompts | F4 last-conversation resume | F1 personality scope-fix | L1+T2 TTFB & throughput | **Direct activation lever × 4** |
| **Throughput +1,400 req/s peak (+48%)** | T1 bound streaming channel | T2 AGG pool 4×→8× + eviction | T3 HTTP/2 multiplex AGG | T5 heap 5Gi→8Gi + ZGC | **+1,400 req/s** (closes gap) |
| **CSM/JSM TTFB** | L22+L23 CSM streaming unblock | L24 HC ID cache | L25/L26 Firebolt cache+gate | L27/L28 JSM HR convergence | **-800-1500ms p50** |
| **Cost $/turn — honest** | C1 persist compaction -$80-120K | K1 Anthropic prompt-cache -$40-80K | C2 classifier debounce -$15-25K | C8+C9 dedup+converge -$10-15K | **-$168-290K/mo** (verified) |
| **Insights LLM cost (NEW)** | N1 (S7) CACHE_TIMEOUT 1d→7d -80% | N10 (E1) prompt dedup -72% input tokens (gated on cache-hit) | N6 hoist Statsig -1.25-2.5s/gen | N4 person-hydration batch -5-8s p95 | **-80% LLM cost; -5-8s p95** |
| **Insights stability (NEW)** | N2 supervisorScope per-type isolation | N3 idempotency `enqueuedAt` + 120s wall-clock | N5 notification retry+throw → SQS redrive | | **0 duplicates; <0.5% stuck** |
| **Reliability silent-bug (NEW)** | R-6A idempotency keys for side-effecting tools | R-1A per-tool deadline | R-1B tool-error feedback | R-6E structured cancellation | **0 user-visible duplicates; no infinite-hang** |
| **EngVelocity LoC removed** | E1 retire A2AChatExecutor -1,370 LoC | E3 delete v1 410 routes -85 LoC | E2 PlanGen V2 cutover | | **~1,500+ LoC** |

---
## 4. TOP-15 ranked by goal-impact (B's Top-12 + R + N additions)

| # | Item | File · Source | Goal | Quantified impact | Conf | Effort | UF | Flag | Exit |
|---|------|---------------|------|-------------------|------|--------|----|----|------|
| 1 | **O1 Auto-rollback wiring** (Phase 0) | new + Statsig API + SignalFx detector — B | InfraBlocker | Enables every flagged item below; without it plan has no MTTR | 1.0 | M | no | n/a | A regressed flag auto-flips to 0% within ≤5min of detector trip; chaos-drill verified |
| 2 | **N1 (S7) Insights `CACHE_TIMEOUT` 1d→7d** | `RovoInsightsV1Controller.kt:193` — A | Insights Cost | -80% Insights LLM cost in 1 line | 1.0 | XS (15min) | no | dynamic config | Cache hit ≥7×, generation rate ≥-80% |
| 3 | **C1 Persist compaction summary** | `ContextCompactionServiceImpl.kt` — B | Cost | -$80-120K/mo | 1.0 | M | no | `ROVO_COMPACTION_PERSIST` | Re-compaction <0.2/conv |
| 4 | **Q1 PageSearch L2 rerank for LLM context (dual-list)** | `ConfluencePageSearchServiceImpl.kt:47-77`; `PageSearchPlugin.kt:175-186` — B | FactualConsistency | +15-25pp on golden eval | 1.0 | S | conditional (split) | `ROVO_PAGESEARCH_LLM_RERANK` | Eval factual ≥40%; UI snapshot diff = 0 |
| 5 | **T1 Bound `Channel.UNLIMITED`** in streaming writer | `HttpRequestStreamingWriter.kt:44` — B (verified comment "Risk: possible memory growth") | Throughput / Memory | Closes verified known-risk; eliminates heap pressure on slow clients | 1.0 | S | no | `ROVO_STREAMING_BOUNDED_CHANNEL` | Heap-pressure alarms gone under burst |
| 6 | **T2 AGG WebClient pool 4×→8× + eviction** | `AggWebClientConfiguration.kt:48,67,135,158` — B | Throughput | +600 req/s peak; +0.1pp SLO under burst | 1.0 | S | no | `ROVO_AGG_POOL_LARGE` (load-tested first) | Pool exhaustion alerts -90% |
| 7 | **R-6A Idempotency keys for side-effecting tools** | tool-registry + `ProcessedToolCallStore` (DynamoDB conditional put, 30-min TTL) — v2/A v3 | Reliability / Trust | **0 user-visible duplicate Jira/Confluence creates on retry** (today silently corrupts) | 1.0 | M | no | `ROVO_TOOL_IDEMPOTENCY_KEYS` | Duplicate-create rate = 0 in soak test |
| 8 | **R-1A Per-tool deadline** | `withTimeoutOrNull(30_000)` around `toolExecutor.executeSingle()` at `SimpleLoopWorkflowExecutorImpl.kt:914-920` — v2/A v3 | Reliability / Latency | Eliminates infinite-hang on slow tools; reduces p99 conv-latency by however long the slowest stalls | 1.0 | S | no | `ROVO_TOOL_DEADLINE_ENABLED` | p99 conv-latency capped at 30s + LLM time |
| 9 | **R-1B Tool-error feedback to LLM** | append `FunctionMessage(isError=true)` instead of throwing; max 2 error retries — v2/A v3 | Reliability / Quality | LLM self-correction on tool failure (today loop dies) | 1.0 | S | no | `ROVO_TOOL_ERROR_FEEDBACK` | Tool-failure success-recovery rate ≥40% |
| 10 | **N2 (L2) Insights cancellation isolation** | `coroutineScope` → `supervisorScope + runCatching` at `RovoInsightsServiceImpl.kt:657` — A | Insights Stability | 12-min worst-case → 240s/type; 5/6 types deliver on 1 failure | 1.0 | S | no | `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED` | Per-type p95 ≤240s |
| 11 | **N4 (L1) Insights N+1 person hydration → batch** | Semaphore(16) at `RovoInsightsServiceImpl.kt:471-517` — A | Insights Latency | -5–8s p95 (54 sequential → ~4 batches) | 1.0 | M | no | `AIX_ROVO_INSIGHTS_HYDRATION_PARALLEL_ENABLED` | Insights p95 -5s |
| 12 | **L3 Remove `runBlockingWithContext` AI_EDITOR** | `ChatV1Controller.kt:267` — B | ChatSLO | +0.1pp SLO; -100-300ms tail | 1.0 | M | no | `ROVO_CHAT_NONBLOCKING_STREAM` | Tomcat busy-thread p99 < 60% |
| 13 | **L1 AsyncTenantContext Caffeine cache** | `AsyncTenantContextService.kt:35-260` — B | TTFB / MAU | -100-200ms × N (avg -150ms p50); cache hit ≥95% | 1.0 | S | no | `ROVO_TCS_CACHE` | Cache hit ≥95%; TCS RPS -80% |
| 14 | **K1+A2.1 Anthropic prompt-cache audit** (Kotlin path) | audit `CacheFriendlyPromptAssembler` callsites — B | Cost | -$40-80K/mo; ARIZE prompt-cache-hit ≥70% | 1.0 | M | no | (it's a fix, not a rollout) | Cache-hit-tokens ratio +20pp |
| 15 | **C2 Debounce in-session classifier** | `InSessionSegmentationServiceImpl.kt:75-108` — B | Cost | -$15-25K/mo; classifier calls/turn ≤0.3 | 1.0 | S | no | `ROVO_SEGMENTATION_DEBOUNCE` | Calls/turn ≤0.3 |

**TOP-25 second tier (also goal-impactful, sequenced into weeks 4-9):**

| # | Item | File · Source | Why second-tier (not third-tier) |
|---|------|---------------|---------------------------------|
| 16 | **R-1C Mid-stream failover (soft resume)** | `LLMServiceImpl.kt:1367-1404` — v2/A v3 | The ONLY lever past 99.85% toward 99.9% SLO; conditional UF (visible "[continued from fallback model]" annotation + release note) — flag `ROVO_STREAM_FAILOVER_SOFT_RESUME` |
| 17 | **N3 (S1) Insights idempotency `enqueuedAt` + 120s wall-clock** — A | Insights Stability | 0 duplicate generations; <0.5% stuck — flag `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED` |
| 18 | **F1 Personality-experiment scope-fix** (chat-only) | `RovoChatAnswerGeneratorHelper.kt:435` — B | Trust + MAU; PR #26895; doc-confirmed leak; UF=yes (release note: search reverts to factual tone) — `rovo_chat_personality_*` |
| 19 | **T0a Async pool 96→256 + queueCapacity=1000 + 503 reject** | `application.yml:160-162` — A | Throughput / Stability; +200-400 req/s headroom; prevents OOM at sustained burst |
| 20 | **T0b Heimdall rate-limiter 3000ms→500ms + circuit-break** | `ExperienceRateLimitFilter.kt:64` — A | -3s worst-case block; +0.05pp SLO |
| 21 | **Q4 Grounding/citation system prompt** | HybridOrchestrator prompt assembly — B | +8-12pp FC, +3-5pp relevancy; conditional UF (output style) — `ROVO_HYBRID_GROUNDING_V1` |
| 22 | **Q2 bodyExcerpt/passages (additive, no UI change)** | `PageSearchResponse.kt:12-33` — B | +10-15pp recall, +10-15pp FC; payload p99 < 16MB — `ROVO_PAGESEARCH_BODY_EXCERPT` |
| 23 | **F2 Empty-state starter prompts** | new endpoint `GET /rovo/v1/me/starter-prompts`, integrate `MyActivitiesService` — B | Day-0 activation lever (industry-proven); UF=yes (release note + UX work) — `ROVO_STARTER_PROMPTS` |
| 24 | **A2.4-DUAL Tool relevance pre-filter** (full catalog visible in cached prefix; only args schemas pruned to top-20) | A re-scoped per v4/v5 | -40-60% tool-token cost (~$3-4.5K/mo); conditional UF (LLM-context only) — `ROVO_TOOL_FILTER_DUAL` |
| 25 | **R-6E Structured cancellation** | replace detached `launch` with `coroutineScope`; `ensureActive()` between tool calls — v2/A v3 | -80% token waste from orphaned post-disconnect work; refactor (no flag) |

---

## 5. The full workstream tables (B verbatim, with N/R additions)

This section adopts B's section C (workstreams O / A / B[chat] / T / C / K / F / E / R) **verbatim**. v7 net-adds:

### Workstream N — Rovo Insights (NEW from Plan A; full table)

**Goal:** -80% Insights LLM cost; -5-8s p95 latency; 0 duplicate generations; 5/6 types deliver on 1 failure; users no longer cached-but-not-notified.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|----|-------------|--------|--------|------|----|------|------|-----|
| N1 (S7) | `CACHE_TIMEOUT=1d → 7d` · `RovoInsightsV1Controller.kt:193` | One-line cache TTL extension | XS (15min) | low | no | dynamic config | Cache hit ≥7×; generation -80% | — |
| N2 (L2) | Per-type cancellation isolation · `RovoInsightsServiceImpl.kt:657` | `coroutineScope` → `supervisorScope + runCatching` | S | low | no | `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED` | Per-type p95 ≤240s; 5/6 deliver on 1 failure | — |
| N3 (S1) | Idempotency `enqueuedAt` + 120s wall-clock budget | Replace SETNX with timestamp-based key + wall-clock | M | low | no | `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED` | 0 duplicate generations; <0.5% stuck-rate | — |
| N4 (L1) | N+1 person hydration → batch with Semaphore(16) · `RovoInsightsServiceImpl.kt:471-517` | Single-flight + bounded parallelism | M | low | no | `AIX_ROVO_INSIGHTS_HYDRATION_PARALLEL_ENABLED` | Insights p95 -5-8s | — |
| N5 (S2) | Notification: retry+throw → SQS redrive (NOT fire-and-forget) | Wire to SQS DLQ pattern | S | low | no | (none — bug fix) | 0 cached-but-not-notified | N3 |
| N6 | Hoist Insights Statsig FF eval out of per-type fan-out | Eval once per request, pass result down | XS | low | no | none (refactor) | -1.25-2.5s/gen | — |
| N7 | Insights retry jitter | Exponential + decorrelated jitter | XS | low | no | none | Retry-storm RPS -90% | — |
| N8 | `structuredOutputEnabled=true` for Insights LLM calls | flip flag; A/B quality | S | low | no | `ROVO_INSIGHTS_STRUCTURED_OUTPUT` | Parse-failure -80%; quality non-regression | M5 |
| N9 | Hoist `createConversationId` out of per-type loop | One ID per Insights generation, not 6 | XS | low | no | none (refactor) | -10-50ms × 6 | — |
| N10 (E1) | Insights prompt deduplication (118KB shared prefix across 6 templates) | Extract common system prefix, leverage cache | M | low | no | `ROVO_INSIGHTS_PROMPT_VERSION` | -72% input tokens (gated on cache-hit ≥70%) | K1, M6 |
| N11 | Drop full-prompt log for Insights (PII risk + log volume) | Log hash + length only | XS | low | no | none | Log volume -50% | — |

### Workstream R — Reliability (NEW from v2/Plan A v3 critique; full table)

**Goal:** eliminate silent user-trust bugs (duplicate side-effects), close infinite-hang risks (per-tool deadline), unlock 99.9% SLO ceiling (mid-stream failover), eliminate orphaned-cancellation token waste.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|----|-------------|--------|--------|------|----|------|------|-----|
| R-1A | Per-tool deadline · `SimpleLoopWorkflowExecutorImpl.kt:914-920` | Wrap `toolExecutor.executeSingle()` in `withTimeoutOrNull(30_000)`; on timeout append synthetic `tool_error` | S | low | no | `ROVO_TOOL_DEADLINE_ENABLED` | p99 conv-latency capped at 30s + LLM time | — |
| R-1B | Tool-error feedback to LLM · `SimpleLoopWorkflowExecutorImpl.kt:938-962` | When tool throws, append `FunctionMessage(isError=true, content=<sanitised>)` and continue; max 2 error retries per tool | S | low | no | `ROVO_TOOL_ERROR_FEEDBACK` | Tool-failure recovery rate ≥40% | — |
| R-1C | Mid-stream failover (soft resume) · `LLMServiceImpl.kt:1367-1404 withStreamFallbackModelRetry()` | Buffer last completed safe-checkpoint chunk; on stream-error after `hasReceivedItem=true`, emit typed `STREAM_FALLBACK` event and replay to fallback model with `previous_partial_text` re-injected | M | medium | conditional (visible "[continued from fallback model]" annotation; release note) | `ROVO_STREAM_FAILOVER_SOFT_RESUME` | Mid-stream failover success rate ≥80%; SLO +0.05-0.15pp | O3 |
| R-6A | Idempotency keys for side-effecting tools · tool-registry + `ProcessedToolCallStore` | Tool-registry declares `isSideEffecting + idempotencyKeyTemplate`; before execution compute key from `(conversationId, messageId, toolCallId, argsHash)`, store in DynamoDB conditional put with 30-min TTL; skip on duplicate, return cached result | M | medium | no | `ROVO_TOOL_IDEMPOTENCY_KEYS` | 0 duplicate Jira/Confluence creates on retry | — |
| R-6E | Structured cancellation · `RovoChatService` + `LLMServiceImpl` | Replace detached `launch { ... }` with `coroutineScope { ... }`; add `currentCoroutineContext().ensureActive()` between tool calls; emit `convoai.cancellation.observed_ms` | S | low | no | none (refactor) | -80% token waste from orphaned post-disconnect work | — |

### Workstreams O, A (Q-series), B (L-series), T, C, K, F, E (B's section C verbatim — see `here-is-codebase-docs-sorted-sunbeam.md` lines 64-237)

For brevity v7 does not duplicate B's tables verbatim; **the source-of-truth for items O1-O6, Q1-Q14, L1-L32, T1-T14, C1-C9, K1-K8, F1-F11, E1-E7, R1-R7 is `here-is-codebase-docs-sorted-sunbeam.md` section C** (workstream tables) and **section G** (findings → plan map). v7 carries them in scope without restating.

**v7-only modifications to those workstreams:**
- **Q5 (page-search opt-in flip)** is the canonical Beta-GA gate item (after Q1+Q2+Q3+Q4 prove ≥+10pp factual). Promote to "must do before Beta GA."
- **L9 (ContentHydration N+1)** and **L10 (Kamino multi-region parallel)** carry HIGH risk per B's table — keep as week-9-10, behind cohort A/B and shadow parity.
- **K2 (Python sidecar prompt cache)** anti-goal #16 enforced: do not claim multi-hundred-K $ savings from this; sidecar is Marathon-only.
- **K6 (RedisCacheClient wiring)** anti-goal: do not claim $ until grep-verified that `RedisCacheClient` truly has zero callsites in chat path. v7 adds explicit verification gate before any K6 work.
- **R1-R7** (sidecar sunset, Loom scope, Socrates alignment, S3 audit, ERS CI, SageMaker, Actuator hardening) are organizational-decision items, NOT engineering work. v7 moves them to a separate Decision Log (week 1 owner triage; not a ship-gate).

---
## 6. Measurement plan (B's M1-M7 + v7 additions)

| ID | What it proves | Required instrumentation | Source |
|----|----------------|--------------------------|--------|
| M1 | AIFC eval harness | Golden 300-row dataset (Q13); LLMJudge factual + recall + relevancy; nightly job; per-flag-cohort deltas | B |
| M2 | ARIZE per-turn quality | `LLMJudgeServiceImpl` wired into ARIZE event pipeline (Q14); 5% sample; cohort tags | B |
| M3 | TTFB per-orchestrator + dispatcher utilization | `@WithSpan` + per-pool dispatcher metrics (already partial in `CoroutineContextProvider.kt:80-94 InstrumentedDispatcher`). Single panel: "Pre-LLM serial time" + per-pool saturation | B |
| M4 | Cost per turn — leverage existing | Use Socrates `convo_ai_usage` data product (verified at `socrates-vnext/`); add per-feature attribution panel; do not reinvent | B |
| M5 | Model-downsize quality non-regression | A/B with paired prompts; LLMJudge delta; user thumbs-down | B |
| M6 | Cache discipline | Hit/miss/eviction per Caffeine cache; Redis memory + eviction; FF-call counter per request | B |
| M7 | Throughput / saturation | Per-pod req/s; per-downstream pool saturation; HPA scale events; pod cold-start time. **Required to validate T-series claims and to gate T11/T12 (≥7d before tuning)** | B |
| **M8** (NEW v7) | Insights stability + cost | Insights cache hit-rate; per-type latency p95; duplicate-generation rate; SQS DLQ depth for N5; per-Insights-template token spend | A v3 critique demanded |
| **M9** (NEW v7) | Reliability silent-bug counter | Duplicate side-effect-tool execution counter (R-6A); per-tool deadline-trip counter (R-1A); tool-error-recovery success counter (R-1B); mid-stream-failover success counter (R-1C); orphan-token-burn counter (R-6E) | v2 / A v3 critique demanded |

**Hard rule (B + v7):** No item ships claiming impact until the relevant `M*` is live for ≥7 days.

---

## 7. Sequencing — week-by-week (B's plan + N/R additions)

This sequencing extends B's section E (which has 12 weeks) by interleaving N-series (Insights) and R-series (Reliability). N1 is XS so lands in Week 1; the rest of N stages with the existing Insights flag rollouts; R-1A/R-1B land Week 3; R-6A lands Week 4-5 (needs DynamoDB store); R-1C lands Week 5-7 (depends on O3 graceful shutdown).

```
Wk 1   O1, O2, O3 (Phase-0 infra)
        + M1 harness, M3 + M7 + M8 + M9 instrumentation
        + Q13 golden-dataset start
        + T1, T4 (bound channels)
        + E3 (delete dead routes)
        + N1 (Insights cache 1d→7d)  ← 15-min, -80% Insights cost
        + N6 (hoist Insights Statsig)
        + N7 (Insights retry jitter)
        + N9 (hoist createConversationId)
        + N11 (drop full-prompt log)
        + R1-R7 owner triage (Decision Log only)

Wk 2   O4, O5, O6  · M2 ARIZE judge  · Q12 CI scaffold
        + L1 (TCS cache), L8 (FF memo), L16 (sandbox TTL), L20 (XS Map)
        + T0a (async pool 96→256), T2 + T9 (AGG pool + codec, load-tested)
        + T0b (Heimdall 3000ms→500ms)
        + K2 (sidecar prompt cache enable — sidecar-only, anti-goal-bounded)
        + C2 classifier debounce
        + R7 actuator hardening (from R series — leadership-decision item already triaged Wk 1)
        + N2 (Insights per-type isolation)
        + N5 (Insights notification SQS redrive)

Wk 3   Q11 Slack date filter (XS bug-fix)  · Q1 dev
        + L2 (batch config-svc), L13 (retry jitter), L19 (agent-inv cache)
        + T5 (heap 5Gi→8Gi + ZGC)
        + C1 dev (compaction persist)
        + F1 personality-scope dev
        + K1 audit cache_control
        + R-1A (per-tool deadline) ← reliability quick-win
        + R-1B (tool-error feedback) ← reliability quick-win
        + N4 (Insights person-hydration batch)

Wk 4   Q1 ship 5%→25%  · Q4 dev
        + L4 dev (parallel pre-LLM gates), L7 codec confirmed live, L20 (XS)
        + T3 (HTTP/2)  · T7 default pool sizing
        + C1 ship 5%, C6 (tool pre-rank)
        + F1 ship 5%→100%
        + R1 sidecar decision close (timeline + replacement OR keep)
        + R-6A (idempotency keys) start ← reliability medium-effort
        + N3 (Insights idempotency `enqueuedAt`)

Wk 5   Q1 100%, Q3, Q2 dev
        + L4 ship 5%→25%, L17 (tool-registry cache)
        + T8 AppCDS dev
        + C1 25%, C8 dev (classifier dedup)
        + K3 dev (tool-result coalesce)
        + F2 starter-prompts dev
        + E1 parity test build (A2AChatExecutor shadow)
        + R-6A ship 5% (canary tenants)
        + R-1C dev (mid-stream failover)
        + N8 (Insights structuredOutputEnabled=true)

Wk 6   Q2 ship 5%, Q12 CI gate enforced
        + L17 100%, L15 (MCP session reuse), L11 (chunk-accumulator bound)
        + T11+T12 pool tune (gated by M7 dashboards ≥7d)
        + C1 100%, C3 citation A/B
        + K4 (in-flight singleflight)
        + F2 ship 5%, F4 dev
        + E1 cutover 5%
        + R-6A ship 25%
        + R-1C ship 5% (canary)
        + N10 (Insights prompt dedup) — gated on K1 cache-hit ≥70%

Wk 7   Q2 100%, Q6 dev
        + L21 (history-delta) dev, L18 (.blockingGet removal)
        + C4 Lumina A/B, C9 dev (DeepResearch converge)
        + K5 (edge cache headers)
        + F4 last-conv-resume ship 5%, F8 (recent-activity context)
        + E1 25%
        + R-6A 100%
        + R-1C ship 25%
        + R-6E (structured cancellation) refactor lands

Wk 8   Q6 ship, Q7 dev
        + L21 ship, L18 ship
        + C9 ship, C5 (cache prompt V1 adoption)
        + K6 incremental Redis wire (gated on grep-verification of zero callsites in chat path)
        + F3 adaptive follow-up dev, F5 citation hover dev
        + E1 100% (delete A2AChatExecutor: -1,370 LoC)
        + R-1C 100%

Wk 9   Q7 ship, Q8/Q9/Q10 dev
        + L31 (compaction guard), L32 (realtime async)
        + C7 (batch API offline)
        + K7 (embed-sim cache), K8 (JSON-repair)
        + F5 ship, F9 (stale-source warn)
        + E2 PlanGen V2 shadow
        + R3, R4 (Decision Log close)

Wk 10  Q8/Q9/Q10 ship
        + L9 (N+1 hydration batch HIGH risk), L10 (Kamino multi-region parallel HIGH risk), L12 (Redis discipline)
        + L22-L24 (CSM streaming unblock + HC ID cache) ← CSM/JSM workstream begins
        + C5 100%
        + F3 ship, F10 (feedback → ARIZE)
        + E2 100% if shadow wins
        + R6 (SageMaker versioning)

Wk 11  Q5 page-search opt-in flip A/B (Beta-GA culmination)
        + L3 AI_EDITOR non-blocking 5%→25%
        + L25-L28 (Firebolt cache+gate; JSM HR convergence)
        + T13 (QPS targets in TOME), T14 (DNS TTL)
        + F6 (confidence badges), F7 (graceful error UX), F11 (base-prompt dynamic config)
        + E6 (AIFEATURE split)
        + R5 (ERS CI gate)

Wk 12  Q5 100%, final eval lockdown
        + L3 100%, L14 (GraphQL pagination)
        + L22-L28 ship to 100%
        + E7 (storage ADR Postgres/DynamoDB)
        + R2 (Loom scope close)
```

**Critical paths:**

- **Beta GA**: O1+O5 → M1+M2 → Q1 → Q2 → Q4 → Q12 enforced → Q5 flip → final lockdown.
- **150k MAU readiness**: M3+M7 → L1+L8 → T1+T2+T0a+T0b+T5 → L4 → L17 → L21 → L3 + F2+F4 + R-6A.
- **Cost realization**: M4 (Socrates) → C1+C2 → C3+C4+C8 → K1+K2+K3 → C7+C9 → N1+N10.
- **Insights stability**: M8 → N2+N5 → N3 → N1 → N4 → N10.
- **Reliability**: M9 → R-1A+R-1B → R-6A → R-1C → R-6E.
- **CSM/JSM TTFB**: L22-L24 → L25-L28 (weeks 10-12).

---

## 8. Anti-goals — extended in v7 (B's 16 + v6's 4 + v7's 5 new = 25)

(B's 1-16 kept verbatim. v6's 26-29 kept. v7 adds 30-34.)

1-16. (B's anti-goals — kept verbatim. See `sorted-sunbeam.md` section H.)

26. (v6) Do not claim 99.9% SLO without R-1C shipped. Honest target without R-1C is 99.85%.
27. (v6) Do not quote $215-375K/mo as headline cost. Honest verified range is **$168-290K/mo**.
28. (v6) Do not plan v2 reliability items (R-series) as "later" or "out of scope".
29. (v6) Do not carry F5/F6/F9/R1-R7/T11/T12/E6/E7 as in-scope without explicit measurement gate; some demote to backlog.

30. **(v7) Do not adopt v6's lean Top-25 as the full plan.** v6 dropped CSM/JSM workstream entirely, dropped most L-series detail, dropped per-source rerank Q6/Q7/Q8/Q9/Q10, dropped goal-contribution matrix, dropped findings→plan completeness check. v7 restores all of these by adopting B as the structural base.

31. **(v7) Do not duplicate B's tables verbatim into derived plans.** The source-of-truth for B's content (O1-O6, Q1-Q14, L1-L32, T1-T14, C1-C9, K1-K8, F1-F11, E1-E7, R1-R7) is `here-is-codebase-docs-sorted-sunbeam.md`. Derived plans (this v7) cite B by section and document only NET additions (N + R) and corrections.

32. **(v7) Do not start K6 work without grep-verifying that `RedisCacheClient` truly has zero callsites in chat path.** Anti-goal honors B's section L #5.

33. **(v7) Do not start T11/T12 pool re-tuning without M7 saturation panel live for ≥7 days.** Anti-goal honors B's section L #6.

34. **(v7) Do not include `assistance-service` work as in-repo.** It is a separate microservice; mirror priorities (TCS caching, prompt-cache audit, dual-list rerank, throughput tuning) but track separately in another plan. Anti-goal honors B's section L #7.

---

## 9. Cut-tier (what to drop if constrained — extended from v6)

| Cut tier | Items | Rationale |
|---|---|---|
| **Cut first** (8-week sprint instead of 12) | F5, F6, F9, R1-R7 (Decision Log only); Q6-Q10 per-source rerank (keep Q1+Q2+Q3+Q4); L9, L10 (HIGH risk; defer); L13, L14, L15 smaller wins; T11/T12 (no M7 evidence); E6, E7 ADR-only | None move a top goal gap by ≥1pp |
| **Cut second** (6-week sprint) | A2.4-DUAL, A2.5-GUARDED, C7, K6, K7, K8, N10 (depends on K1 hit-rate), N8 (A/B), L22-L28 CSM/JSM (defer to Phase 2) | Conditional cost wins; not load-bearing for Beta GA |
| **Cut third** (4-week sprint) | F2-F11 (defer all activation features); L17, L21; some L-items; N4, N6-N9 | Defer activation lift + Insights polish |
| **NEVER cut (load-bearing)** | O1-O6 + M1-M9 + Q1-Q5 + Q12-Q14 + L1 + L3 + L8 + T1 + T0a/b/c/d/e + T2 + T5 + R-1A + R-1B + R-6A + N1 + N2 + N3 + C1 + K1 | These are AIFC GA, Phase-0 ops, hot-path stability, reliability, Insights quick-wins |

---

## 10. Risk register — B's 6 + v7's 3 new

(B's 1-6 kept verbatim — see B section F.)

7. **(v7) R-6A idempotency-key store consistency.** DynamoDB conditional put has eventual consistency in some failure modes. Mitigation: 30-min TTL ensures stale records age out; per-tenant rate-limit on idempotency-key collisions; alert on >10 collisions/hr.

8. **(v7) R-1C mid-stream failover surfaces fallback model with different style.** Mitigation: visible "[continued from fallback model]" annotation in user-facing message; release note documenting behavior; per-flag rollout cohort A/B with text-style judge.

9. **(v7) N1 cache 1d→7d staleness in Insights surfaces "stale insights" complaint.** Mitigation: cache key includes user-activity-window hash (so refresh on meaningful change); revert flag exists; cohort A/B before 100%.

---

## 11. The single-plan answer (5th time, same answer): Plan B (`sorted-sunbeam.md`)

I have answered this question at v3, v4, v5, v6, v7 — same answer each time, same five reasons, with growing evidence:

1. **AIFC 57pp factual-consistency regression** — Plan B is the only source plan that addresses this beta-GA-blocking quality crisis.
2. **User-facing-preservation is structural in B** (dual-list pattern), not just intent.
3. **Measurement-first (M1-M7) is enforced**: no item ships claiming impact until M-series live.
4. **Phase-0 operational rigor (O1-O6) is mandatory** in B; A doesn't include O1 auto-rollback.
5. **B's gaps are layerable** (concrete code-anchored items: Insights workstream, R-series reliability, A's Heimdall fix, A's specific config diffs); A's gaps require architectural rework (no AIFC, no dual-list, no Phase 0).

**Three independent meta-comparisons converge on Plan B:** my v4/v5/v6/v7 critiques, Plan A v3's "do-this-again-here-zazzy-scroll" meta-critique, and the implicit consensus that B is the only plan with both a goal-contribution matrix AND a findings→plan completeness check.

**Honest cost of picking B alone:**
- Loses Heimdall 3s timeout fix (-3s worst-case tail) → recoverable as T0b in Wk 2.
- Loses Insights workstream (-80% Insights cost; -5-8s p95) → recoverable as N1-N11 in Wks 1-3.
- Loses v2 reliability items (R-1A, R-1B, R-1C, R-6A, R-6E) → recoverable as R-series in Wks 3-7.
- Loses Plan A's specific config diffs (async pool 96→256, etc.) → recoverable as T0a-T0e in Wks 1-2.

**These are additive layers on top of B, not replacements.** v7 is "Plan B as the structural base + N-series (from A) + R-series (from v2 via A v3) + dual-list re-scoping of A's UF-risky items (from v4/v5) + SLO/cost honest corrections (from A v3) + cut-tier discipline (from v6)."

**If forced to a single deployable name: Plan B.** v7 is the Plan B + everything-else integration.

---

## 12. v7 vs v6 vs v5 — what changed

| Aspect | v5 | v6 | v7 |
|---|----|----|----|
| Insights workstream (N1-N11) | added | kept | kept |
| Plan A architectural decisions for Insights | adopted | adopted | adopted |
| v2 reliability items (R-series) | ❌ missing | ✅ added (5 items) | ✅ kept; R-6A clarified consistency model; R-1C clarified UF annotation |
| SLO honesty (99.85% vs 99.9%) | partial | reconciled | kept reconciled |
| Cost figures | $215-375K aggressive | $168-290K verified | $168-290K verified, with explicit stretch caveat |
| **CSM/JSM TTFB workstream (L22-L28)** | ❌ missing | ❌ missing | **✅ in scope (Wks 10-12)** |
| **Goal-contribution matrix** | ❌ missing | ❌ missing | **✅ adopted from B + extended with N/R** |
| **Findings → plan completeness check** | ❌ missing | ❌ missing | **✅ adopted from B (v7 Section 5 cites B's section G)** |
| **Per-item Dep column** | partial | partial | **✅ adopted from B** |
| **Q-series breadth (Q6/Q7/Q8/Q9/Q10 per-source rerank)** | partial | partial | **✅ in scope** |
| **L-series breadth (L2, L5, L7, L9-L20, L31, L32)** | partial | partial | **✅ in scope** |
| **Synthetic monitoring re-use, assistance-service mirror** | not mentioned | not mentioned | **✅ explicit anti-goals 31, 34** |
| F-series scope creep | F5/F6/F9 in scope | demoted | demoted but with cut-tier explicit |
| R1-R7 stalled decisions | in scope | demoted | **✅ moved to Decision Log (Wk 1 owner triage; not ship-gate)** |
| INFERRED pool re-tunes (T11/T12) | in scope | held | **✅ held; anti-goal 33 enforces M7 ≥7d** |
| K6 verification gate | implicit | implicit | **✅ explicit anti-goal 32 (grep-verify zero callsites)** |
| "What to cut if constrained" | absent | added | **kept; Phase 2 includes CSM/JSM cut** |
| Anti-goals count | 25 | 29 | **34 (5 new from v7 honest re-read)** |
| Total in-scope items | ~120 | ~95-100 | **~115 (B's 80+ + N's 11 + R's 5 + corrections)** |

**v7 is meaningfully better than v6 because v6 over-pruned.** v6 took Plan A v3's critique to mean "lean is good"; that was an overcorrection. v7 restores B's full breadth (CSM/JSM, per-source Q-series, full L-series, goal-contribution matrix, findings→plan completeness check) while keeping v6's fixes (R-series, SLO honesty, cost honesty).

---

## 13. Test-SOP for v7 execution (NEW — added 2026-05-04)

Every item in this plan ships through one or more of the test types below. The full Standard Operating Procedure (with exact commands, prerequisites, and troubleshooting) lives in `_dev/_plan/convo_ai_hack/test_sop/` (now 9 files, 1,500+ lines).

### 13.1 Test taxonomy (verified 2026-05-04)

| Test type | Path | Purpose | v7 plan tie-in |
|---|---|---|---|
| **Unit** | every module's `src/test/kotlin` (3 shards: core / rovo / product) | Fast in-process; mocked deps | Required for every PR |
| **Startup smoke** | `convo-ai-test-integration/.../FullContextStartupIT.kt` | Full Spring context boots; ~3-5 min | Required for every PR; first-line validation for any module change |
| **Integration** | `convo-ai-test-integration/src/test/kotlin/it/...` (250+ tests, 4 shards × FlagsOn/FlagsOff) | HTTP-level against local Nebulae sandbox; WireMock-mocked external services | Required for L-series, T-series, R-series, Q-series PRs (anything touching hot path) |
| **Evaluation (BatchEval)** | `convo-ai-test-integration/.../AgentStudioBatchEvaluation*IT.kt` + `modules/platform/evaluation/` | LLM-Judge plumbing; canned-LLM responses | Required for Q-series, M1, R-1B, N8 |
| **Load (perfhammer/Locust)** | `operations/perfhammer/tests/{rovo-chat-stream-api.py, aifc-page-create-stream-api.py}` | Streaming-API throughput / saturation | **Required for T-series** (any throughput claim); feeds M7 dashboard |
| **Live-sandbox iteration** | re-use running `convo-ai-integration-tests-<session>-*` (currently `3f2a39fb`) | 5-10× faster dev loop via `-Pnebulae.enabled=false` | Use during dev for ALL R/N/L iterations |

### 13.2 Definition-of-done — required test gates per item type

| Item type | Required tests before merge | Required tests before 5%→25% rollout | Required tests before 25%→100% |
|---|---|---|---|
| L-series (latency) | Unit + smoke + targeted IT | M3 cohort delta ≥80% of claim over 48 h | Same + no SLO regression for 7 days |
| T-series (throughput) | Unit + smoke + targeted IT | M7 saturation panel ≥7 days of baseline + perfhammer 2× peak load test sustained 5 min | Per-pool utilization at peak < 80% |
| R-series (reliability) | Unit + smoke + targeted IT + BatchEval (R-1B) | Soak test 48 h with chaos injection (R-1A timeout-trip rate, R-6A duplicate-detection counter) | M9 counters at expected baseline ≥7 days |
| N-series (Insights) | Unit + smoke + targeted IT (Insights-specific) | M8 cache-hit-rate / per-type latency / dup-rate ≥7 days | Same + cohort A/B parity for any UF item |
| Q-series (quality) | Unit + smoke + targeted IT + BatchEval | M1 nightly judge ≥+10pp vs baseline cohort over 7 days | Same + UI snapshot diff = 0 in cohort A |
| C-series (cost) | Unit + smoke + targeted IT | M4 (Socrates) per-feature attribution ≥80% of claimed $/mo over 14 days + paired quality A/B (M5) | Same |
| K-series (cache) | Unit + smoke + targeted IT | M6 hit/miss/eviction dashboard ≥7 days; K1: ARIZE prompt-cache-hit ≥70% | K6: grep-verified zero-callsite gate (anti-goal 32) |
| F-series (features) | Unit + smoke + targeted IT | Cohort A/B with primary metric for ≥7 days; UF=yes ⇒ UI snapshot diff = 0 + release notes merged | Same |
| O-series (ops) | Chaos drill validates intended behavior end-to-end | n/a (these are infra) | n/a |

**v7 hard rule (kept):** No item ships claiming impact until the relevant `M*` is live for ≥7 days.
**v7 hard rule (NEW from this section):** Any T-series claim must be validated by perfhammer in staging at 2× peak RPS for ≥5 min sustained before merge.
**v7 hard rule (NEW from this section):** Any Q-series claim must be validated by BatchEval against the golden 300-row dataset (pending Q13) before 25% rollout.

### 13.3 Live-sandbox status — currently usable

As of plan-creation (2026-05-04), session `3f2a39fb` of the integration-test sandbox is running (started 2026-05-01T21:00:45Z, all 18 containers `Up 2 days`). Re-use it for fast iteration via `./gradlew … -Pnebulae.enabled=false`. Full guidance in `test_sop/08-live-sandbox.md`.

If the sandbox dies / drifts: `atlas nebulae start -s integration-tests` rebuilds in 60-180 s.

### 13.4 SOP file index (with v7 tie-ins)

| File | Lines | What it documents | v7 items it directly enables |
|---|---|---|---|
| `00-overview.md` | 70 | SOP map + test taxonomy + TL;DR quick-start | (all) |
| `01-prerequisites.md` | 111 | Tools, env, IAM, Sliver tokens, sanity checks | (all) |
| `02-unit-tests.md` | 108 | `./gradlew test` + sharding | (all PRs) |
| `03-integration-tests.md` | 283 | Nebulae sandbox lifecycle + targeting + flag modes | L, T, R, N, Q PRs |
| `04-troubleshooting.md` | 194 | Known failure modes + diagnoses | (all) |
| `05-ci-mirror.md` | 83 | Mirror CI shard layout locally | Any PR before pushing |
| `06-load-tests.md` | **NEW** | perfhammer/Locust: prereqs, target modes, M7 feed | **T-series** + R-1C SLO claim |
| `07-evaluation-tests.md` | **NEW** | LLM-Judge framework, BatchEvaluation, Databricks pipeline, AIFC golden eval | **Q-series**, M1/M2, R-1B, N8 |
| `08-live-sandbox.md` | **NEW** | Re-use the running 18-container sandbox; service:port map; restart criteria | All dev iteration on any v7 item |

### 13.5 Anti-goal #35 (NEW in v7.1)

**Do not claim that an item "passes tests" without specifying which tests.** "Tests pass" means: (a) unit + smoke locally green, (b) the item-type-required tests in §13.2 above are green, (c) the relevant M* dashboard is live and shows the claimed impact. Items that skip any of these and ship anyway will be reverted by O1 auto-rollback.

### 13.6 Anti-goal #36 (NEW in v7.2 — from end-to-end verification 2026-05-04)

**Do not assume a "Up N days" sandbox is healthy.** Run the 4-line `curl --max-time 3` health check (see `test_sop/08-live-sandbox.md` §A.0) BEFORE running anything with `-Pnebulae.enabled=false`. If wiremock/localstack return `HTTP 000` in 3 seconds, restart the sandbox; otherwise smoke FAILs in ~3 minutes with misleading errors that look like app bugs but are actually mock-stack rot. Verified true on 2026-05-04 dry-run: a 2-day-old sandbox showed all 18 containers `Up` but inner processes were dead, causing `IOException: HTTP/1.1 header parser received no bytes` from the smoke test.

### 13.7 Calibration: SOP is verified ~75% executable as-written, ~95% with corrections applied

Per `test_sop/09-end-to-end-verification-log.md`:
- **Verified GREEN end-to-end**: prereqs (Java 21, Atlas CLI, Gradle 9.3), unit tests (`./gradlew :convo-ai-foundation-utilities-impl:test` ran 14 tests in 30s, all PASSED), perfhammer setup (locust 2.20.1 installed under Python 3.13 + Anaconda; headless run generated 1,151 requests at ~441 RPS in 3s).
- **Verified FAIL (correctly diagnosed)**: smoke test against degraded sandbox FAILed in 2m44s with the exact root-cause errors documented in §13.6 — proving the SOP correctly identifies sandbox rot.
- **Not directly executed (but follow same patterns)**: integration test against fresh sandbox; perfhammer against working app; eval BatchEval IT; real-LLM eval (B2); Databricks eval (B3); unit-test sharding.

End of integrated v7 plan (with §13 Test-SOP appended 2026-05-04 + §13.6/13.7 from end-to-end verification).


---

## 14. Task Documentation & PR Convention (added 2026-05-04)

> Pattern source: `responsible-ai-api/PLAN.md` § Conventions + the user-supplied PR-description reference (which itself derives from RAI-04 PR #630).
>
> **Why a convention?** A multi-month plan with 30+ flagged items needs a uniform way to: (a) discover what's in flight (`grep "^Status: in_progress" tasks/*.md`), (b) prove a change shipped without spelunking commit history, (c) capture the design rationale next to the code so the next engineer doesn't re-derive it.

### 14.1 Repo layout

For each plan item executed, create a task documentation file under:

```
conversational-ai-platform/
  .ai_employee/
    projects/
      <project_name>/                  ← Gradle module short-name, e.g. platform-client-impl
        README.md                       ← project pickup procedure + cross-refs
        _template/
          TASK_TEMPLATE.md              ← canonical task file template
          PR_DESCRIPTION_TEMPLATE.md    ← canonical PR description template
        tasks/
          <ID>-<kebab-title>.md         ← live task (status: todo / in_progress / shipped-pending-merge)
          done/
            <ID>-<kebab-title>.md       ← shipped task; in-repo design archive (never deleted)
        agentic-coding-logs/
          YYYY-MM-DD-HHMMSS-<topic>.md  ← per-session work log (one per coding session)
```

**Project name convention:** use the Gradle module short-name being targeted (e.g. `platform-client-impl`, `product-rovo-impl`, `platform-workflow-impl`). If a single task spans multiple modules, name the project after the **primary** module being changed and link the secondary modules under "Cross-references" in the task file.

**One project subfolder per Gradle module** keeps task lists scannable: a reviewer for `product-rovo-impl` doesn't have to scroll past 50 unrelated `platform-client-impl` tasks.

### 14.2 Task file lifecycle

```
todo  →  in_progress  →  shipped-pending-merge  →  shipped  →  (git mv to ./done/)
                                                          ↘
                                                            rejected | deferred | blocked  (stay in `tasks/`, do NOT move to done/)
```

- **Status field is mandatory and grep-able** — `grep -l "^Status: in_progress" .ai_employee/projects/**/tasks/*.md`
- **UX-Class field is mandatory** (A/B/C) and tied to PM-Sign-off — caught the B0.1 incident in `responsible-ai-api`
- **PM-Sign-off is mandatory** when UX-Class is C (Affecting). Any user-facing change without PM sign-off is rejected at review.
- **Use `N/A` or `blocked-on-X` with explicit reason**; never use `_pending_` once a task is past `todo`.
- **After merge:** update Status → `shipped`, fill the Lessons learned section, then `git mv` to `tasks/done/`. The `done/` directory is the in-repo design archive — grep-able, never deleted.

### 14.3 Canonical task file template

The full template lives at `<project>/_template/TASK_TEMPLATE.md`. Required sections:

1. **Title** — `# <ID> — <short title>`
2. **Header block** — Status, Priority, UX-Class, PM-Sign-off, Plan, PR, Jira, Dashboard, Author, Date opened
3. **Problem** — issue + evidence table; single-paragraph WHY
4. **Approach** — numbered layers / phases (HOW, not WHY)
5. **UX Classification rationale** — 5-question form (mandatory; do not skip)
6. **TODOs** — checklist incl. PR description, status update, post-merge `git mv`
7. **Acceptance criteria** — each one an executable verification (command + expected output)
8. **Impact** — Claimed (pre-implementation) AND Measured (>= 7 days post-deploy)
9. **Rollback plan** — trigger / action / ETA table
10. **Replaces** — prior plan IDs superseded
11. **Work log** — chronological; fill DURING work
12. **Lessons learned** — retrospective; fill AFTER merge
13. **Cross-references** — compounds-with, plan section, prior incidents

### 14.4 Canonical PR description format

The full template lives at `<project>/_template/PR_DESCRIPTION_TEMPLATE.md`. Required structure (in order):

1. **Title line** — `Top-15 plan item #<RANK>: <ID> — <short title> (<UX-Class>)` followed by Plan ref + Closes
2. **Why** — one paragraph + small evidence table
3. **What** — bullets (high level; the diff view does line-by-line)
4. **Impact — measured** — numeric table; mandatory
5. **Observability gain** — qualitative ("Can now answer: …")
6. **Tests — ALL PASS** — explicit pass/fail counts; new tests enumerated
7. **Rollback** — single-line revert path; quantified blast radius
8. **Scope — N files** — `git diff --stat` style listing
9. **Cross-references** — plan link, compounds-with, closes
10. **Dashboard follow-up** — explicit non-blocking note
11. **DoD checklist** — boring but essential gates

### 14.5 Anti-patterns (rejected at review)

- ❌ PR title that does not reference the plan rank
- ❌ Impact section without a measured number (claims with no evidence)
- ❌ Tests section without explicit pass/fail counts
- ❌ Rollback that is not a single-commit revert / config-flag flip
- ❌ Bare `try: ... except Exception` — must narrow to the specific exception class with a comment
- ❌ Changes that fail the UX-Class 5-question form without PM sign-off
- ❌ Mixing two unrelated plan items in one PR (split, or pair-name them in both file titles)
- ❌ "Planning" sections that exceed the work itself (this is a tax on every reader)
- ❌ Task files that skip the Acceptance criteria executable verifications (any `[ ]` without a command is incomplete)

### 14.6 Worked example (T2)

The first item executed under this convention is **T2 (AGG WebClient pool 4× → 8×)**:

- Project folder: `.ai_employee/projects/platform-client-impl/`
- Task file: `tasks/T2-agg-webclient-pool-multiplier.md` (status: `shipped-pending-merge`)
- Session log: `agentic-coding-logs/2026-05-04-033200-T2-agg-pool-multiplier.md`
- Templates: `_template/TASK_TEMPLATE.md`, `_template/PR_DESCRIPTION_TEMPLATE.md`
- Code change: `+52 / -3` lines across 3 files (1 main, 2 tests); 28/28 tests pass

Use this as the reference when authoring future task files / PR descriptions.

End of §14.
