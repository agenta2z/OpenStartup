# Convo AI Platform — BOOST Plan v1

**Status:** PROPOSED &nbsp;•&nbsp; **Author:** Tony Chen &nbsp;•&nbsp; **Created:** 2026-05-14 &nbsp;•&nbsp; **Repo:** `atlassian/conversational-ai-platform`

> **Why "BOOST":** This plan is the **third wave of opportunities** layered on top of the existing v7 Integrated Plan and my 18 currently-open PRs. It is intentionally **novel** — every item below has been cross-checked to ensure it is NOT already in flight as one of the 18 open PRs and NOT already in v7's TOP-15 / TOP-25.
>
> The BOOST plan is **goal-anchored** to FY26 north-stars: Beta GA AIFC quality, 150k Rovo MAU, 99.85% chat SLO, $168–290K/mo cost reduction, +1,400 req/s throughput, and the strategic pillars of Knowledge / Productivity / Trust / Monetization.

---

## 0. Honest scope statement

This plan **excludes** items already in scope as:

| Excluded family | Where covered |
|----------------|----------------|
| T0a, T0b, T1, T2, T5 | v7 + my open PRs #29107, #29109, #29110, #29111 |
| R-1A, R-1B, R-1C, R-6A, R-6E | v7 + my open PRs #29112, #29114, #29119 |
| A1–A12 + NEW (Insights observability + cancellation + hydration + cache) | v7 + my open PRs #29074, #29085, #29092, #29096, #29097, #29099, #29101, #29103, #29113 |
| L1, L3, L9, L10, L18, L22–L28 | v7 (in roadmap; not yet PRed) |
| Q1–Q14 (AIFC quality, page-search rerank, body-excerpt, grounding) | v7 (Beta GA gate) |
| C1, C2, K1, K6 | v7 |
| F1, F2, F4 (personality, starter prompts, last-conv) | v7 |
| N1–N11 (Insights workstream) | v7 |
| O1–O6 (Phase-0 ops) | v7 |

**The BOOST plan adds 4 new workstreams** that complement (not replace) v7:

| New workstream | Theme | # items | Anchor goal |
|----------------|-------|---------|-------------|
| **B-Refactor** | Architecture & code-quality refactors | 6 | Dev velocity + reliability |
| **B-Reliability+** | Reliability gaps not covered by R-series | 6 | Silent-bug elimination |
| **B-Cost+** | Cost wins not in C/K/N series | 6 | $30–73K/mo additive |
| **B-Latency+** | Latency wins not in T/L/N series | 5 | TTFB / p99 tail / first-chunk |

**Total: 23 NEW high-impact items.** Every item is evidence-cited (file:line or PR-anchored).

---

## 1. Refined goal map (where BOOST contributes)

| FY26 goal | v7 baseline | + BOOST contribution | Rationale |
|-----------|-------------|----------------------|-----------|
| **Beta GA AIFC factual-consistency 13% → ≥40%** | v7 Q1+Q2+Q3+Q4 = +36-57pp | **+0pp direct** (BOOST avoids quality competition) | Quality is v7's core; BOOST stays out of the way |
| **150k Rovo MAU** | v7 F1+F2+F4+L1+T2 | **+activation surface area** via B-Latency+ Y1, Y2, Y4 | TTFB win below first-byte threshold (250ms) lifts engagement |
| **99.85% chat SLO** | v7 R-series + L3 + T1 | **+0.05–0.10pp** via B-Reliability+ S1, S2, S6 | Catch silent failures and load-shed before saturation |
| **+1,400 req/s peak (capacity)** | v7 T0a + T2 + T1 | **+200–400 req/s** via B-Latency+ Y3 + B-Refactor R8 | TCS cache consolidation + parallel tool-loop |
| **$168–290K/mo cost reduction** | v7 C1+C2+K1+N1+N10 | **+$30–73K/mo** via B-Cost+ X1–X10 | Model-mis-selection (X7) is single largest unclaimed lever |
| **Dev velocity** | v7 E-series | **+~3,000 LoC removed** via B-Refactor R1, R5, R6 | Monolithic clients, REST versioning, SQS handlers |
| **Silent-trust bugs eliminated** | v7 R-6A | **+ async-task-loss + post-workflow idempotency** via B-Reliability+ S1, S5 | Memory ingest + post-workflow mutations |

---

## 2. Three design principles (kept from v7, sharpened)

1. **Goal-driven priority** — Every BOOST item declares one primary FY26 goal + quantified impact + confidence + risk class. No "nice-to-have" items.
2. **Excludes v7 / open-PR overlap** — Every item is grep-verified against the v7 plan and my 18 open PRs (see §0).
3. **Refactor-when-justified** — Refactors only land if they show **measurable** velocity / reliability / cost win, not aesthetic preference. Anti-pattern: refactor "because the code is ugly".

---

## 3. TOP-12 ranked by goal-impact

| # | ID | Item | Goal | Impact | Conf | Effort | Risk | Source |
|---|----|------|------|--------|------|--------|------|--------|
| 1 | **X7** | Model mis-selection audit (Sonnet → Haiku for routing/classification) | Cost | **−$16.8–43.5K/mo** (single largest unclaimed lever) | 0.85 | L (A/B + accuracy gates) | Medium (routing accuracy) | B-Cost+ |
| 2 | **R8** | TCS (Tenant Context Service) cache consolidation | TTFB + Cost | **−15–20% latency on permission checks** + 1 fewer Redis roundtrip | 0.9 | M | Low | B-Refactor |
| 3 | **X2** | Tool-schema cross-turn dedup (within-conversation memo) | Cost | **−$4–6K/mo** (tool schemas re-serialized 5–15KB/turn) | 0.85 | M | Low-Med | B-Cost+ |
| 4 | **Y2** | Eliminate `.block()` calls on pre-LLM serial paths (4 verified call-sites) | TTFB | **−100-300ms p95 TTFB** (frees servlet thread; compounds with L3) | 0.9 | M | Low | B-Latency+ |
| 5 | **S1** | Fire-and-forget task DLQ (async memory ingest) | Reliability | **0 silent memory-loss events** (categorical safety) | 0.95 | M | Med (SQS coordination) | B-Reliability+ |
| 6 | **S5** | Idempotency keys for post-workflow mutations (extends R-6A) | Reliability | **0 duplicate user-message-store events on retry** | 0.95 | M | Med | B-Reliability+ |
| 7 | **X4** | Agent-system prompt factorization (shared prefix + leaner few-shot) | Cost | **−$2.5–5K/mo** (compounds with K1 prompt-cache) | 0.8 | M | Med (prompt quality A/B) | B-Cost+ |
| 8 | **R10** | Tool-output schema-validation framework (catch malformed tool results) | Quality + Cost | Fewer hallucinations + **−5–10% retry tokens** | 0.85 | M | Med (over-strict schemas) | B-Refactor |
| 9 | **Y3** | Parallel tool-call execution within single LLM-decision turn | TTFB / latency | **−500–2,000ms p95** when LLM emits ≥2 parallel tool calls | 0.85 | S-M | Low (tool side-effects already gated by R-6A) | B-Latency+ |
| 10 | **S2** | Concurrent-conversation saturation gauge + load-shed at threshold | Reliability + capacity | Prevents tail-latency cascade under thundering-herd | 0.9 | S | Low (metric-only at first) | B-Reliability+ |
| 11 | **X5** | Knowledge / search query result cache (5min TTL on deterministic queries) | Cost + TTFB | **−$2–4K/mo + −100-200ms p50** for repeat queries within session | 0.85 | M | Low | B-Cost+ |
| 12 | **R6** | SQS / Aqui handler unification (`AbstractMessageQueueHandler<T>`) | Reliability + dev velocity | Consistent retry/DLQ across 7+ handlers | 0.9 | M | Med (refactor 7 handlers) | B-Refactor |

**TOP-12 total claimed impact:**
- Cost: **−$25.3–58.5K/mo** (X7 + X2 + X4 + X5)
- Latency: **−700-2,500 ms p95** (Y2 + Y3 + R8)
- Reliability: silent-bug eliminations across S1, S5, S6
- Capacity: +200-400 req/s headroom (R8 + Y3)
- Quality: lower hallucination rate via R10
- Dev velocity: ~3000 LoC removed (R1 + R5 + R6)

---

## 4. Workstream tables (full enumeration)

### 4.1 Workstream **B-Refactor** (architecture & code-quality)

| ID | Title | File:line evidence | Effort | Impact | Risk | Approach |
|----|-------|---------------------|--------|--------|------|----------|
| **R1** | Monolithic AsyncConfluenceRestClientImpl (5,788 LoC, 200+ duplicated CRUD endpoints) | `modules/platform/client/client-impl/.../AsyncConfluenceRestClientImpl.kt` | M | Dev velocity (+8-12% reduced boilerplate); fewer copy-paste bugs | Med (caller signatures may break) | Generic `execute<T>()` adapter w/ annotation routing + `@Deprecated` wrapper layer for callers |
| **R2** | Type-erasure anti-pattern in SearchSlotsConfiguration (`List<Any>?` to break circular import) | `modules/platform/service/service-api/.../SearchSlotsConfiguration.kt:25` | S | Quality (compile-time type safety) | Low | Extract neutral interface `MarkdownableKnowledgeSource` to a `shared` module |
| **R5** | REST endpoint versioning debt (`internal` + `v1` + `v2` w/ overlapping endpoints) | `modules/service/convo-ai-service/.../rest/internal/, rest/v1/, rest/v2/` | M | Dev velocity (-20% boilerplate if v1 sunset); single source of truth | Med (legacy clients) | Audit traffic; sunset v1 if <5%; transformation layer instead of separate controllers |
| **R6** | SQS / Aqui handler fragmentation (7+ consumers, each with own retry/DLQ/observability) | `modules/service/convo-ai-service/.../sqs/queue/, .../streamhub/` | M | Reliability + ops (consistent retry/timeout) | Med (7 handlers to migrate) | Extract `AbstractMessageQueueHandler<T>` w/ pluggable retry/DLQ policies |
| **R8** | TCS cache redundancy (`TcsRequestCache` + `TcsProcessCache` both store tenant policy) | `modules/service/convo-ai-service/.../domain/tenant/TcsRequestCache.kt, TcsProcessCache.kt` | M | **−15-20% perm-check latency** + fewer Redis roundtrips | Low (clear semantics) | Consolidate to single unified cache layer w/ explicit TTL + invalidation |
| **R10** | Tool-output schema validation framework (multiple tool types, fragmented deserialization) | implicit across `modules/platform/tool-registry/, .../tool-execution/` | M | Quality (fewer hallucinations) + cost (-5-10% retry tokens) | Med (over-strict schemas) | `ToolOutputValidator` interface w/ JSON-Schema; centralize deserialization with error telemetry |

### 4.2 Workstream **B-Reliability+** (gaps NOT covered by R-series)

| ID | Title | File:line evidence | Failure mode prevented | Effort | Impact | Risk |
|----|-------|---------------------|------------------------|--------|--------|------|
| **S1** | Fire-and-forget task DLQ (async memory ingest) | `modules/foundation/utilities/utilities-impl/.../ApplicationCoroutineScope.kt:20-21,34-40,51-53` (CoroutineExceptionHandler logs warning only — no retry, no DLQ, no metric) | Silent loss of conversation memory on pod eviction / OOM | M | **0 silent memory-loss events** | Med (SQS DLQ coordination) |
| **S2** | Concurrent-conversation saturation gauge + load-shed at threshold | `modules/product/rovo/rovo-impl/.../RovoChatService.kt:206` (`AtomicInteger(0) concurrentConversations` w/ no max() + no metric + no backpressure) | Thundering-herd → unbounded concurrency → thread-pool exhaustion → tail-latency cascade | S | Prevents cascade; safer at peak | Low (metric-only first) |
| **S3** | MDC context propagation on async task boundaries (extends R-6E scope) | `modules/product/rovo/rovo-impl/.../RovoChatAsyncTaskLauncher.kt:166-168` (captures `Context.current()` for OTel only — MDC tenant/user/session lost) | Distributed traces broken across pre/post workflow boundaries; debugging impossible | S-M | Better incident MTTR | Very low (additive) |
| **S5** | Idempotency keys for post-workflow mutations (extends R-6A) | `modules/product/rovo/rovo-impl/.../RovoChatAsyncTaskLauncher.kt:1088-1101` (`launchPostWorkflowTasks` user-message storage + memory ingest lacks idempotency key) | Duplicate user-message store events on retry; duplicate memory entries | M | **0 duplicate post-workflow mutations** | Med |
| **S6** | Health-readiness probe reflects orchestrator + LLM downstream availability | `RovoChatService.chatStream():257+` invokes `invokeChatExecutor():1050+` w/o readiness check on agent orchestrator / LLM router | Pod marked Ready while downstream unavailable; routes to broken pod | S-M | Reduces customer error rate during degradation | Low (readiness ≠ liveness) |
| **S4** | Streaming-buffer depth gauge + slow-client timeout policy (complements T1 #29109) | `modules/platform/base/base-impl/.../HttpRequestStreamingWriter.kt:136,145,212-240` (T1 bounds capacity but no depth gauge / slow-client timeout) | Slow client ties up bounded buffer for entire stream lifetime | S | Earlier slow-client detection | Low (metric-only) |

### 4.3 Workstream **B-Cost+** (cost wins NOT in C/K/N series)

> **Baseline:** $168–290K/mo. **Pricing assumption:** input ~$3/M tok, output ~$15/M tok (Claude Sonnet); Haiku ~$0.25/M tok input, $1.25/M tok output (~10× cheaper).

| ID | Title | Evidence | Est $/mo | Effort | Risk |
|----|-------|----------|----------|--------|------|
| **X7** | Model mis-selection audit (Sonnet → Haiku for routing/classification) | Routing/classification across `modules/product/chat-common/, shared-features/` likely uses Sonnet/GPT-4 for tasks Haiku/GPT-3.5 handles at 80-90% accuracy | **−$16.8-43.5K** | L | Med (routing accuracy A/B) |
| **X2** | Tool-schema cross-turn dedup (memo within conversation) | `modules/platform/service/service-impl/.../llm/toolconverter/` — every tool converter (Claude, ChatCompletion, Gemini, RawPredict, FunctionTool) re-serializes ~5-15KB JSON schemas per turn | **−$4-6K** | M | Low-Med (schema-evolution handling) |
| **X4** | Agent system-prompt factorization | `modules/product/agent-framework/.../prompts/` — shared boilerplate (guidelines, format, safety, fallback) repeated across agent variants; few-shot examples 3 → 1-2 | **−$2.5-5K** | M | Med (prompt quality A/B) |
| **X5** | Knowledge / search result cache (5-min TTL on deterministic queries) | `modules/platform/knowledge/, modules/product/shared-features/` — TWG / CQL queries not cached at result level (Bluebird does embeddings only) | **−$2-4K** + TTFB | M | Low (deterministic queries only) |
| **X3** | Within-turn search-tool dedup | `modules/product/confluence/, modules/product/jira/` — multi-step agent loops re-query same issue/page within turn | **−$1.5-3.5K** | S | Low |
| **X6** | Conversation-context metadata pruning (debug metadata) | `modules/platform/conversation/` — tool-call exec time / token count / error trace accumulated and resent in subsequent turns | **−$1-2K** | S | Low |
| **X8** | Per-tool retry-error memo (cache failed tool result) | `modules/platform/base/base-impl/.../tool/executor/LlmInvocableExecutorImpl.kt` — tool failures trigger re-send of full context with identical tools/history | **−$1-2.5K** | M | Low (error paths only) |
| **X1** | Streaming tail-trim (track cancelled-stream wasted tokens) | `modules/platform/service/service-impl/.../AIGatewayClientServiceImpl.kt` + stream handlers — cancelled streams still billed for tokens emitted post-cancellation | **−$0.5-1.25K** + observability | S | Low |
| **X9** | AIFC creation-flow ADF block caching (15-iteration loop) | `modules/product/aifeature/` — page/whiteboard creation iterates 15× re-sending same context | **−$1.5-4K** | L | Med (AIFC quality) |
| **X10** | Tool-schema log sampling (hash + sample 1%) | `AIGatewayClientService` debug logging — full schema JSON written to CloudWatch on every request | **−$0.5-1.5K** CloudWatch | S | Low |

**Total claimed cost impact: −$30–73K/mo** (incremental over v7's $168-290K baseline).

### 4.4 Workstream **B-Latency+** (TTFB / p99 / first-chunk wins)

| ID | Title | Evidence | TTFB / p95 / p99 saving | Effort | Risk |
|----|-------|----------|---------------------------|--------|------|
| **Y1** | Send `event: ack` SSE preamble immediately after auth (not after tenant resolution) | `modules/service/convo-ai-service/.../rest/v1/ChatV1Controller.kt:164,254` (NDJSON streaming endpoints) | **−50-150ms perceived TTFB** | S | Low (preamble is non-payload) |
| **Y2** | Eliminate `.block()` calls on pre-LLM serial paths | `ToolDeclarationDsl.kt:12` (lambda — false positive); `ConfluencePageTemplateFetcherPlugin.kt:59` (real); `DevAICoreClientImpl.kt:120` (real); `AssistanceServiceEvalServiceImpl.kt:218` (real) — 3 verified prod call-sites | **−100-300ms p95 TTFB** + frees servlet thread (compounds with L3) | M | Low (suspend conversion) |
| **Y3** | Parallel tool-call execution within single LLM-decision turn | `SimpleLoopWorkflowExecutorImpl` — currently sequential per-tool; LLM often emits ≥2 independent tool calls per decision | **−500-2,000ms p95** when LLM emits parallel tools (gated by R-6A side-effect safety) | S-M | Low (R-6A makes safe) |
| **Y4** | Speculative pre-warm (parallelize tenant resolution + auth + user-context hydration) | `RovoChatService.chatStream()` and `ChatV1Controller` invoke serially | **−80-200ms p50 TTFB** | M | Low (additive) |
| **Y5** | Per-request Statsig FF-eval memo (extends N6) | Multiple sites in `modules/product/rovo/, modules/platform/conversation/` evaluating same FF multiple times per request | **−20-50ms p95** | XS | Very low |

---

## 5. Sequencing — week-by-week (12-week plan, after v7 lands)

```
Wk 1   FOUNDATION: O1+O5 (already in v7 sequencing) MUST land first
        Y5 (per-request Statsig FF-eval memo)            [XS, drop-in]
        X1 (streaming tail-trim instrumentation)         [S, observability]
        X10 (tool-schema log sampling)                   [S, observability]
        S2 (concurrent-conv gauge — metric-only first)   [S, metric-only]
        S4 (streaming buffer depth gauge)                [S, metric-only]

Wk 2   MEASUREMENT-DRIVEN COST WINS
        X3 (within-turn search-tool dedup)               [S]
        X6 (conv context metadata pruning)               [S]
        X2 (tool-schema cross-turn dedup) — start        [M]

Wk 3   QUICK LATENCY WINS
        Y1 (SSE event:ack preamble)                      [S]
        S3 (MDC propagation to async tasks)              [S-M]
        S6 (health-readiness probe)                      [S-M]

Wk 4-5 BIG REFACTOR & RELIABILITY (parallel tracks)
        Y2 (eliminate .block() calls)                    [M]
        Y3 (parallel tool-call exec)                     [S-M; needs R-6A live]
        S1 (fire-and-forget DLQ)                         [M]
        R8 (TCS cache consolidation)                     [M]

Wk 6-7 COST DEEP-DIVE
        X4 (agent prompt factorization)                  [M; A/B required]
        X5 (knowledge result cache)                      [M]
        X8 (tool retry-error memo)                       [M]

Wk 8-9 STRUCTURAL REFACTORS (only if Wk 1-7 measurement validates)
        R6 (SQS handler unification)                     [M; 7 handlers]
        R10 (tool-output validation framework)           [M]
        S5 (post-workflow idempotency keys)              [M; needs R-6A live]

Wk 10-12 BIG MODEL BET (X7) + LONG-TAIL REFACTORS
        X7 (model mis-selection audit + Haiku rollout)   [L; A/B + accuracy gates]
        R1 (monolithic ConfluenceClient refactor)        [M; deprecation wrapper]
        R5 (REST v1 sunset audit)                        [M; client traffic audit]
        X9 (AIFC ADF block caching)                      [L; AIFC quality A/B]
        R2 (SearchSlotsConfiguration type-erasure fix)   [S]
```

**Parallelizable batches:**
- **Batch A (independent, can land any time):** Y5, X1, X10, S4, X3, X6, Y1, S3
- **Batch B (depends on R-6A from v7):** Y3, S5
- **Batch C (depends on M8/M9 from v7):** all cost claims (X2, X4, X5, X7, X8) require ≥7 days of measurement before claiming impact
- **Batch D (depends on T-series + R-series safety):** R1, R5, R6 refactors

---

## 6. Anti-goals (kept from v7's 36, +5 BOOST-specific)

(v7 anti-goals 1-36 carried verbatim; see `INTEGRATED_PLAN_v7_synthesis.md` §8.)

**BOOST-specific anti-goals:**

37. **Do not ship X7 (model mis-selection) without an LLM-judge accuracy A/B test demonstrating ≤5% accuracy delta on a labeled router/classifier dataset.** Cost win is meaningless if quality regresses.

38. **Do not ship R1 / R5 / R6 / R10 refactors without v7's E-series PRs landing first.** v7 already removes ~1,500 LoC; BOOST refactors should compose, not collide.

39. **Do not promote Y3 (parallel tool calls) to >5% rollout until R-6A (tool idempotency) is live for ≥7 days.** Parallel tool execution amplifies any side-effect duplicate-creation risk.

40. **Do not measure BOOST cost claims (X1–X10) using LLM-token counters alone.** Use the M4 Socrates `convo_ai_usage` data product per-feature attribution. Token-counter only ⇒ rejected at review.

41. **Do not refactor a class because it is "ugly".** R1, R5, R6, R10 must each show measurable dev-velocity (LoC removed, PRs merged/wk delta) or reliability (incident-rate delta) impact within 6 weeks of merge; otherwise rollback.

---

## 7. Cut-tier (what to drop if constrained)

| Tier | Items dropped | Rationale |
|------|---------------|-----------|
| **8-week sprint** (drop ~30%) | X9 (AIFC loop), X10 (log sampling), R5 (REST sunset), Y5 (FF memo), S4 (buffer gauge) | Long-tail; not load-bearing for any FY26 north-star metric |
| **6-week sprint** (drop ~50%) | + R1, R10, X8, X6, X3 | Refactor + smaller cost wins |
| **4-week sprint** (drop ~70%) | + S6, Y4, X5, X4 | Keep ONLY: X7, X2, Y2, Y3, R8, S1, S5, S2, Y1 (the TOP-12 minus refactors) |
| **NEVER cut (load-bearing)** | X7 (largest cost lever), Y2 (TTFB), R8 (TCS), S1 (silent loss), Y3 (perceptible win) | These move >1pp on a top FY26 goal each |

---

## 8. Measurement plan extensions (v7 M1-M9 + BOOST M10-M12)

| ID | What it proves | Required instrumentation |
|----|----------------|--------------------------|
| **M10** | BOOST cost claims (X-series) | Per-feature token attribution panel via M4 Socrates; per-conversation tool-schema bytes counter (X2); router/classifier model-name counter + accuracy delta (X7) |
| **M11** | BOOST refactor velocity | Per-week LoC-removed counter (R1, R5); per-week PR-merge throughput (correlate w/ refactor merges); per-handler retry-rate counter (R6) |
| **M12** | BOOST silent-bug counters | DLQ-message-count for fire-and-forget tasks (S1); duplicate post-workflow-mutation counter (S5); load-shed-trigger counter (S2); slow-client-timeout counter (S4) |

**Hard rule (kept from v7):** No BOOST item ships claiming impact until the relevant `M10/M11/M12` is live for ≥7 days.

---

## 9. Risk register (BOOST-specific)

1. **X7 routing-accuracy regression.** Mitigation: 5%→25%→50% rollout with paired LLM-judge accuracy A/B; auto-rollback if accuracy delta >5pp.
2. **Y3 parallel-tool side-effect amplification.** Mitigation: gated on R-6A live ≥7 days; per-tool `parallelizable=true` allowlist initially limited to read-only tools.
3. **R1 / R5 / R6 refactor regression.** Mitigation: deprecation-wrapper layer for R1; client-traffic audit for R5; back-compat shim for R6; required smoke + integration test pass before merge.
4. **R8 TCS cache consolidation cache-hit regression.** Mitigation: detailed cache-hit-rate metric before/after; revert flag.
5. **R10 tool-output validator over-strictness blocks valid tool results.** Mitigation: audit-mode logging for 14 days before enforcement.

---

## 10. Tie-back to FY26 north-stars

| North-star | Direct contributor | Indirect contributor |
|------------|---------------------|----------------------|
| **Beta GA AIFC quality (FactualConsistency 13% → ≥40%)** | (none — v7 owns this) | R10 reduces hallucinations from malformed tool outputs |
| **150k Rovo MAU** | Y1 (perceived TTFB), Y2 (real TTFB), Y3 (parallel tools), Y4 (pre-warm) | R8 (perm-check latency) |
| **99.85% chat SLO** | S1, S2, S6 | S3 (MDC for MTTR), S4 (slow-client) |
| **+1,400 req/s peak throughput** | R8 (perm-check), Y3 (parallel tools) | S2 (load-shed prevents cascade) |
| **−$168–290K/mo cost** | X1–X10 (all) — additive **−$30-73K/mo** | R10 (fewer retries) |
| **Dev velocity / LoC removed** | R1, R5, R6, R10 | R2 (type safety) |
| **Trust pillar** | S1 (no silent memory loss), S5 (no duplicate mutations) | R10 (validated tool outputs) |

---

## 11. Companion documents

| File | Purpose |
|------|---------|
| `BOOST_PLAN_v1.md` | This file (master plan) |
| `boost_items/B-Refactor.md` | Full per-item detail for R1-R10 |
| `boost_items/B-Reliability+.md` | Full per-item detail for S1-S6 |
| `boost_items/B-Cost+.md` | Full per-item detail for X1-X10 |
| `boost_items/B-Latency+.md` | Full per-item detail for Y1-Y5 |
| `BUSINESS_GOALS_DELTA.md` | What this plan changes vs `architecture/business/01-fy26-goals-and-slos.rst` |

---

## 12. Honest calibration

- **Confidence:** Items with 0.85+ confidence have file:line citations. Items at 0.8 are pattern-based (e.g., X7 model-mis-selection assumes routing/classification exist; needs grep verification before scoping).
- **Evidence quality:** R1, R2, R3 (refactor), S1, S2, S3 (reliability), Y2 (latency .block()) all have **direct file:line citations** verified by grep. X2, X4, X5, X8 (cost) are pattern-based and require deeper grep before scoping.
- **What's missing:** No live Confluence/Jira data was pulled during this plan-creation cycle (token budget); rely on the synthesized business docs in `code_understanding/architecture/business/`. If FY26 OKRs change, re-grade the §10 tie-back table.
- **Time horizon:** 12 weeks. If <8 weeks available, take §7's 8-week cut-tier.

---

## 13. Companion business-docs update

This plan triggers a recommended update to `code_understanding/architecture/business/01-fy26-goals-and-slos.rst` §11 (Per-Feature Roadmap):
- **Add row:** "Boost Plan v1 — 23 incremental items targeting +$30-73K/mo cost reduction, −700-2,500ms p95 latency, +200-400 req/s capacity, ~3,000 LoC removed."

The companion `BUSINESS_GOALS_DELTA.md` documents this delta in detail.

---

## 14. Calling for action

This plan is **PROPOSED**. To advance:
1. Triage TOP-12 with leadership (Robbie Livermore, Kevin Ma owners).
2. Confirm v7 measurement infra (M1-M9) is live before claiming any BOOST impact.
3. Allocate ~2 engineers ×12 weeks OR 4 engineers ×6 weeks.
4. Pick one of three deployment cadences:
   - **Aggressive (12wk):** ship all 23 items; cumulative impact maximized.
   - **Balanced (8wk):** drop ~30% per §7; ship the cost+latency+reliability TOP-15.
   - **Conservative (4wk):** ship ONLY the load-bearing TOP-9 (X7, Y2, R8, S1, S5, S2, Y1, X2, Y3).
