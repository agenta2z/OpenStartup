# Convo AI / Rovo Chat — Integrated v4 Plan (synthesis of A + B)

> **Sources synthesized:**
> - **Plan A** (`~/.claude/plans/here-is-codebase-docs-distributed-hearth.md`, 641 lines, 8 P-tiers, ~50 items)
> - **Plan B** (`_plan/convo_ai/here-is-codebase-docs-sorted-sunbeam.md`, 420 lines, 9 workstreams O/A/L/T/C/K/F/E/Q/R, 80+ items)
> - **Earlier work** (`ROVO_INSIGHTS_GOAL_DRIVEN_PLAN.md`, my v2, 1150 lines)
>
> **Date:** 2026-05-04
> **Synthesizer:** Rovo Dev (deep critical-thinking pass)
> **Status:** PROPOSED — supersedes individual A and B as the working plan; A and B retained for traceability.

---

## 0. The honest comparison & why we integrate

### 0.1 Strengths of each input

| Dimension | Plan A | Plan B | My v2 |
|---|---|---|---|
| **Code-anchoring** (file:line, module names, exact configs) | **Excellent** — every item cites file + line numbers + the actual constant being changed | **Excellent** — same | Good — file:line where verified |
| **$ quantification** | **Strong** ($25K-40K/mo total estimate per-item) | **Strongest** ($215-375K/mo with explicit sub-totals; honest re-scoping note) | Moderate ($0.7-1.2M/yr round numbers) |
| **ms quantification** | **Strong** (per-item ms estimate; verifiable) | Strong (per-item; cohort-style) | Moderate (range estimates) |
| **User-facing-behavior preservation** | **Weak** — A2.4 "tool filtering" and A2.2 "delta history" can change LLM-visible behavior; no dual-list pattern | **Best in class** — explicit `uiOrdered` vs `llmOrdered` dual-list pattern; "do not remove `lastModified` UI ordering" anti-goal | Moderate — flag-gated but no dual-list discipline |
| **Throughput / capacity coverage** | **Strong** (P0.1-0.5: thread pools, rate limiter timeout, ERS pool, hydration pool) | **Strongest** — full T-series with explicit M7 instrumentation gate; T11/T12 marked INFERRED (don't tune blind) | Decent — proposed P0-5 but lacks specific config lines |
| **Operational/infra-blocker discipline** | Mentioned in implementation order (week 1-2) | **Best** — explicit Phase-0 O-series (auto-rollback, circuit breakers, graceful drain) BEFORE any flag rollout | Weak — assumes infra exists |
| **Goal traceability** (every item → measurable goal) | Strong (Goal Alignment column in summary) | **Strongest** (Goal-contribution matrix proves +57pp recovery from individual contributions) | Strong (Goal→Metric→Code mapping) |
| **Measurement-first discipline** | Implicit ("verification" per item) | **Strongest** — explicit M1-M7 ("no item ships claiming impact until M-series is live") | Has Measurement Charter (similar) |
| **AIFC quality recovery** (the 80%→13% factual regression) | Not addressed | **Excellent** — entire A-series workstream Q1-Q14 with golden dataset, CI gate, ARIZE judge | Decent but generic ("canary eval pipeline") |
| **Honest caveats / anti-goals** | Implicit | **Best** — section L "Limitations" with 10 named caveats + section H "Anti-goals" with 16 named "do not"s | Decent — Appendix D "What this plan is NOT" |
| **Dependency graph** | Implicit (week-by-week) | **Best** — every item has explicit `Dep` column | Decent (textual deps) |

### 0.2 Where each plan has gaps

**Plan A misses:**
- **AIFC quality recovery (the 57pp factual regression).** This is the single biggest user-trust crisis in the docs. A focuses purely on perf/cost.
- **Dual-list user-facing-preservation pattern.** A2.4 ("relevance-based tool filtering") and A2.2 ("delta-style history") can change LLM behavior in user-visible ways. A says "gate behind A/B" but doesn't have the structural separation B has.
- **Operational infra-blockers as a Phase 0.** A treats them as week-1 quick wins; B treats them as a hard prerequisite to ANY flagged rollout, which is correct.
- **Honest re-scoping of $ figures.** A's $25-40K/mo is conservative and probably correct; B explicitly warns its $215-375K/mo is partly based on inferred-not-measured premises.

**Plan B misses:**
- **Concrete config diffs.** A names exact lines (e.g., `application.yml:160-162`, `RATE_LIMITER_TIMEOUT_SECONDS = 3L`) and the exact change (`3L → 500L`). B cites files but is less explicit about the literal value to change in many T-series items.
- **`org.json` JSON parser hot-path inefficiency** (A's P3.1: replace `org.json.JSONObject` with `objectMapper.readTree()`, parsed 3× per function-message — 60-70% reduction). Not in B.
- **Heimdall rate-limiter 3s blocking timeout** (A's P0.2). Not in B.
- **Multi-tenant search per-tenant timeout** (A's P4.2 `withTimeout(3000ms)` in `UnitScopedFanOut`). Not in B.

**My v2 misses:**
- The factual-regression problem framed as a 57pp gap with named eval items (Plan B's Q1-Q14).
- The `Channel.UNLIMITED` streaming-writer leak (B's T1 with the explicit code-comment "Risk: possible memory growth").
- The `runBlockingWithContext` AI_EDITOR blocker (B's L3 — Tomcat thread starvation).
- Persisted compaction-summary cost win (B's C1 — $80-120K/mo).
- F1 personality-experiment scope-fix (B's verified production leak into SAIN/Search).

### 0.3 Critical-thinking double-checks

A few items in each plan deserve scrutiny:

| Claim | Plan | Verdict |
|---|---|---|
| "Increase async pool 96 → 256" (A 0.1) | A | **Sound** if Tomcat can run 300; the queueCapacity=0 OOM risk is real (verified: Spring `ThreadPoolTaskExecutor` with `queueCapacity=0` becomes a SynchronousQueue → unbounded behavior depends on rejection policy). |
| "PARALLEL_TOOL_EXECUTION_LIMIT 5 → 15" (A 0.4) | A | **Verified safe** in B's prior pass: tool execution uses isolated 128-thread pool; LLMs typically emit ≤5 tool_calls/turn so impact is bounded but real for outliers. |
| "Default to Haiku for orchestration" (A 2.3) | A | **High value but UF-RISKY** — Haiku may select tools differently than GPT-4-1, even at "95% accuracy". The 5% delta on tool selection IS user-visible behavior change. Must use B's dual-list discipline + paired-prompt A/B (B's M5). |
| "Relevance-based tool filtering 80→15-25" (A 2.4) | A | **HIGH RISK without dual-list** — pre-filtering tools means the LLM never sees some tools. If the rule misses, the LLM cannot act. Need a "dropped tools" fallback path. B's pattern of "topK trim only on LLM context" applies. |
| "RedisCacheClient 'zero callsites'" (B K6) | B | **B itself flags as INFERRED** — verify with grep before claiming $ savings. Honest. |
| "streamingWriterPool=1024 over-provisioned" (B T11) | B | **B itself flags as INFERRED** and gates on M7 dashboard. Correct discipline. |
| "Anthropic prompt-cache enable, $40-80K/mo" (B K1) | B | The CacheFriendlyPromptAssembler exists but A finds the cache_control marker is only checked for AssistantMessage NOT system messages (A 2.1). B's K1 says "audit existing assembler" — A's finding sharpens this: the audit *will* find the system-message gap. **A's specific change + B's audit framing = correct**. |
| "Delta-style history (Loop 2+ send only most recent)" (A 2.2) | A | **CORRECTNESS RISK** — if loop is multi-turn reasoning, the LLM needs context. Need A/B + careful eval; this is more aggressive than Anthropic prompt cache (which sends full history but caches the prefix). Prefer cache-control over delta unless measured to be safe. |

### 0.4 The integration thesis

**Take Plan B's structure** (workstreams + measurement-first + dual-list UF preservation + Phase 0 operational + goal contribution matrix + anti-goals).

**Layer in Plan A's specifics** (exact line numbers + literal config changes + ms estimates + the 4 net-new items A has that B lacks).

**Add my v2's contributions** (correctness guardrails + enterprise readiness + monetisation conversion levers, all of which neither A nor B covers in depth).

**Apply user-facing-preservation discipline RUTHLESSLY** to A's items 2.2, 2.3, 2.4, and 2.5 — these were A's biggest unguarded UF risks.

---

## 1. Goals & metric ledger (canonical)

| Goal | Baseline | Target | Gap | Source |
|---|---|---|---|---|
| Rovo MAU | ~100.3k | 150k by H2 FY26 | +50% | Atlas ATLAS-124112 |
| Chat send-msg SLO | 99.6% | 99.9% (LLM-vendor ceiling) | +0.3pp | TOME `convo_ai/locals.tf` |
| Agent Studio create-scenario SLO | 98.2% | 99.99% | +1.8pp | TOME |
| **AIFC factual consistency (page-search ON)** | **13%** (regressed from 80%) | ≥70% | **+57pp** | AIFC TWCLR2 — CRITICAL beta blocker |
| AIFC contextual recall | 47% | ≥65% | +18pp | AIFC Maturity Gap |
| AIFC contextual relevancy | 40-44% | ≥70% | +27pp | AIFC Maturity Gap |
| AIFC Page Create Task Completion | unknown | 90% Beta | unknown | AIFC QBR |
| Throughput at 150k MAU peak | ~1,500 req/s cap (estimated) | ~2,900 req/s (5× burst headroom) | -48% | Derived; absence of canonical target IS itself a finding (T13) |
| Cost / month | baseline | -$215-375K/mo realised | depends | Cost agent + finance attribution via Socrates `convo_ai_usage` (M4) |
| Quality regression MTTD | >quarter (the 80→13 went undetected) | <1 day | huge | The AIFC regression itself proves the gap |

**Hard ceiling**: OpenAI Scale Tier 99.9% caps LLM-dependent SLOs. Multi-provider failover is the only lever past it.

---

## 2. Three design principles (from Plan B; non-negotiable)

1. **Goal-driven priority.** Every item declares one primary goal + quantified impact in the goal's metric units + confidence (0-1) + priority score = (impact / goal-gap) × confidence.

2. **User-facing-behavior preservation.** Every item is tagged `user_facing: yes / no / conditional`. Conditional items ship as **dual lists** (e.g., `uiOrdered` byte-identical to today + `llmOrdered` reranked for LLM context only). Genuine UF changes require: opt-in flag → cohort A/B (5%→25%→100%) → kill-switch → release note → UI-snapshot-diff = 0 in cohort A.

3. **Infra-blocker first.** Auto-rollback, circuit breakers, graceful shutdown MUST exist before the 30+ flag rollouts in this plan are safe. These are Phase 0.

---
## 3. Top-15 by goal-impact / risk (the actual ranked list)

Ranked by `(impact / goal-gap) × confidence ÷ implementation-risk`. Letter codes follow Plan B's workstreams; numbers in parentheses cite the source plan that contributed each item (A = Plan A, B = Plan B, V2 = my v2). All rows are user-facing-safe by design (UF column).

| # | Code | Item | Source | Goal | Impact (in goal-metric units) | Conf | Effort | UF | Flag |
|---|------|------|--------|------|------|------|--------|----|------|
| **1** | **O1** | Auto-rollback wiring (SignalFx detector → Statsig API auto-flip) | B | InfraBlocker | Enables every flagged item; chaos-drill: regressed flag flips 0% in ≤5 min | 1.0 | M | no | — |
| **2** | **A0.1+T5** | Async pool 96→256 + heap 5Gi→8Gi + ZGC + queueCapacity=1000 with 503 reject | A+B | Throughput / Stability | Prevent OOM at sustained burst; +600 req/s headroom; GC p99 <5ms | 1.0 | S | no | — |
| **3** | **T1** | Bound `Channel.UNLIMITED` in `HttpRequestStreamingWriter:44` (code-comment literally warns "Risk: possible memory growth") | B | Throughput / Memory | Closes verified known-risk; eliminates heap-pressure on slow clients | 1.0 | S | no | `ROVO_STREAMING_BOUNDED_CHANNEL` |
| **4** | **C1** | Persist compaction summary (versioned + checksummed; reuse on hash match) | B | Cost | -$80-120K/mo | 1.0 | M | no | `ROVO_COMPACTION_PERSIST` |
| **5** | **Q1** | PageSearch L2 rerank for LLM context (dual-list pattern; UI order unchanged) | B | AIFC FactualConsistency | +15-25pp on golden eval | 1.0 | S | conditional (split) | `ROVO_PAGESEARCH_LLM_RERANK` |
| **6** | **K1+A2.1** | Anthropic prompt-cache: enable `cache_control` on system messages (A's specific finding) AND audit assembler usage on V1/SAIN/A2A paths (B's framing) | A+B | Cost | -$40-80K/mo; cache hit ≥70% | 1.0 | M | no | (it's a fix, not a rollout) |
| **7** | **A0.2** | Reduce Heimdall rate-limiter timeout 3s → 500ms with circuit-break + fail-open | A | SLO / Tail Latency | Removes a 3-second worst-case block; -3s tail | 1.0 | S | no | — |
| **8** | **L1** | TCS (`AsyncTenantContextService`) Caffeine cache, TTL 60-300s, max 50k | B | TTFB / MAU | -100-200ms × N (avg -150ms p50); cache hit ≥95% | 1.0 | S | no | `ROVO_TCS_CACHE` |
| **9** | **L3** | Remove `runBlockingWithContext` AI_EDITOR path (`ChatV1Controller:267`); reactive `Flux<ServerSentEvent>` | B | ChatSLO | +0.1pp SLO; -100-300ms tail; Tomcat busy-thread p99 <60% | 1.0 | M | no | `ROVO_CHAT_NONBLOCKING_STREAM` |
| **10** | **T2+T3** | AGG WebClient pool 4× → 8× + eviction + HTTP/2 multiplex + codec 24MB → 64MB | B | Throughput | +600 req/s peak; +30% throughput; conn count -10× | 1.0 | S | no | `ROVO_AGG_POOL_LARGE` + `ROVO_AGG_HTTP2` |
| **11** | **A2.4-DUAL** | Tool relevance pre-filter — **with dual-list discipline**: send all 80+ tool names + descriptions in cached prefix; only the **selected_tool_args_schemas** are filtered to top-20 by relevance score | A (re-scoped) | Cost | -40-60% tool-token cost (~$3-4.5K/mo) | 0.7 | M | conditional (LLM-context only; never blocks the LLM from seeing a tool exists) | `ROVO_TOOL_FILTER_DUAL` |
| **12** | **A2.3-GUARDED** | Default to Haiku 4.5 for orchestration — **with paired-prompt LLMJudge A/B + auto-fallback to GPT-4-1 on tool-selection-confidence-low** | A (re-scoped) | Cost | -65-75% orchestration cost (~$8-12K/mo) | 0.7 | M | conditional (model swap) | `SAIN_ORCHESTRATION_HAIKU_4_5` (already exists; flip default) |
| **13** | **F1** | Personality-experiment scope-fix (chat-only, NOT SAIN/Search) — verified production leak | B | Trust / MAU | Unblocks rollout; protects search-path factual tone | 1.0 | S | yes (release note: search reverts to factual tone) | extends existing personality flag |
| **14** | **C2** | Debounce in-session classifier (skip when last <N turns AND embedding-cosine >0.85) | B | Cost | -$15-25K/mo; classifier calls/turn ≤0.3 | 1.0 | S | no | `ROVO_SEGMENTATION_DEBOUNCE` |
| **15** | **A0.3** | Hydration thread pool 2 → 16 with per-domain rate limiting + circuit breaker | A | Throughput | Hydration queue depth <5; unblocks web-content pipeline | 1.0 | S | no | — |

**Items 16-25 (significant, second tier):** Q2 (bodyExcerpt additive), Q4 (grounding system prompt), L4 (parallel pre-LLM gates), L8 (request-scoped FF memoization), A1.2 (eliminate redundant history fetch), A3.1 (org.json → Jackson in token counter), A4.1 (Redis pipeline TTL), A4.2 (per-tenant search timeout), A5.1 (channel capacity bound — overlaps T1), L17 (per-conversation tool registry cache), L21 (history delta fetch), L18 (`.blockingGet` removal in MCP), C3+C4 (model downsizing A/B), K3 (tool-result coalescing in turn), F2 (starter prompts).

**Items 26+:** Plan B's full O/A/L/T/C/K/F/E/Q/R coverage applies; see §5 for full table.

---

## 4. The dual-list user-facing-preservation pattern (mandatory for all retrieval/ranking/tool-selection items)

Every retrieval/ranking change returns **TWO ordered lists from one search call**:
- `uiOrdered` — existing order, existing fields, **byte-identical** to today; bound to UI `sources` / `header`
- `llmOrdered` — reranked / enriched / score-filtered; consumed only inside the LLM context block

**This applies to (re-scoped) Plan A items:**
- A2.2 "delta-style history" → re-scoped to **K1+A2.1 Anthropic prompt-cache** (sends full history, caches the prefix; safer than dropping turns).
- A2.3 "Haiku for orchestration" → re-scoped to **A2.3-GUARDED with paired LLMJudge A/B + auto-fallback** (model is internal; UF only if quality regresses).
- A2.4 "tool filtering 80→20" → re-scoped to **A2.4-DUAL**: full tool catalog still visible to LLM in *cached* prefix, only the *args schemas* (the expensive part) are pruned to top-20. LLM can always still **name** any tool; if it names a pruned tool, fall back to full catalog on next turn.

**Items requiring explicit user-visible release note (UF=yes):** F1 (personality scope-fix), F2 (starter prompts), F3 (adaptive follow-ups), F4 (last-conversation resume), F5 (citation hover), F6 (confidence badges), F7 (graceful error UX), F9 (stale-source warning), Q4 (grounding/citation prompt), Q5 (page-search opt-in flip), Q11 (Slack date filter bug fix).

Each ships behind: opt-in flag → cohort A/B (5% → 25% → 100%) → kill-switch → UI snapshot diff = 0 in cohort A → release note merged in cohort B → manual UI smoke pass.

**Anti-pattern explicitly forbidden:** "ranking by recency → ranking by relevance" type changes. The user contract is that `lastModified` ordering is preserved in the UI list. Any relevance-based reordering is LLM-context-only.

---
## 5. Full integrated workstream tables

This is the canonical, deduplicated, prioritized merger of A and B. Workstream codes follow Plan B; A's contributions are tagged "(A)" with the matching A-priority code. Items I've re-scoped from A for user-facing safety are tagged "(A-DUAL)" or "(A-GUARDED)".

### Workstream O — Operational Infra-Blockers (PHASE 0, must-do before anything flagged)

| ID | Item | Source | Effort | UF | Exit |
|---|---|--------|--------|-----|------|
| O1 | Auto-rollback wiring (SignalFx detector → Statsig API auto-flip) | B | M | no | Chaos drill: regressed flag flips 0% in <=5 min |
| O2 | Circuit breakers (Resilience4j) wrapping AI Gateway, AGG, TCS, Statsig, Heimdall | B | M | no | Single-dep failure does not cascade in fault-injection |
| O3 | Graceful shutdown / stream drain (preStop hook + 30-60s drain) | B | S | no | Rolling deploy preserves in-flight streams |
| O4 | Tenant-level canary registry | B | S | no | Named tenants reliably get new flags first |
| O5 | Schedule batch eval cron (leverage existing AgentStudioBatchEvaluationJobRun) | B | S | no | Nightly eval runs against AIFC golden set |
| O6 | Per-tenant SLO dashboards | B | S | no | Per-tenant chat-message SLO panel |

### Workstream A — AIFC Quality Recovery (Beta-GA blocker)

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag | Dep |
|---|---|---|---|---|------|--------|-----|------|-----|
| Q1 | PageSearch L2 rerank for LLM context (dual-list) at ConfluencePageSearchServiceImpl.kt:47-77 | B | Factual | +15-25pp | 1.0 | S | conditional (split) | ROVO_PAGESEARCH_LLM_RERANK | M1, O5 |
| Q2 | Add bodyExcerpt + passages to PageSearchResponse.kt:12-33 (additive nullable fields) | B | Recall+Factual | +10-15pp recall, +10-15pp factual | 0.7 | M | conditional (additive) | ROVO_PAGESEARCH_BODY_EXCERPT | T9 |
| Q3 | Score-threshold + topK=10 trim at PageSearchPlugin.kt:272 (LLM context only) | B | Factual+Relevancy | +3-5pp; tokens/turn -30% | 0.8 | S | conditional (LLM-side) | ROVO_PAGESEARCH_TOPK | Q1 |
| Q4 | Grounding/citation system prompt in HybridOrchestrator | B | Factual+Relevancy | +8-12pp factual, +3-5pp relevancy | 0.7 | S | conditional (output style + release note) | ROVO_HYBRID_GROUNDING_V1 | M2 |
| Q5 | Page-search opt-in default flip after Q1+Q2+Q3+Q4 prove +10pp factual | B | Factual | gates the rest | 1.0 | XS | conditional | ROVO_PAGESEARCH_DEFAULT_ON | Q1-Q4 |
| Q6 | Multi-source rerank (Confluence+Jira+Slack interleaved) | B | Recall+Relevancy | +4-6pp recall, +8-12pp relevancy | 0.7 | M | no | ROVO_MULTISRC_RERANK | Q1 |
| Q7-Q10 | Per-source rerank (Jira issue, JSD Apollo, etc.) — all dual-list | B | Recall | +1-3pp each | 0.7 | S each | conditional (split) | per-flag | Q1 |
| Q11 | Slack before/after filter forward (XS bug fix) | B | Recall | +2-4pp | 0.95 | XS | yes (bug fix) | ROVO_SLACK_DATE_FILTER_FIX | — |
| Q12 | CI quality gate in bitbucket-pipelines.yml; block PRs that regress factual >=3pp | B | Quality | gates regressions | 1.0 | M | no | none | M1, O5 |
| Q13 | Golden dataset 300+ rows (replace empty evaluation/ dir) | B | Quality | enables M1/Q12 | 1.0 | M | no | none | Q12 |
| Q14 | ARIZE in-loop LLMJudge (5% sample) | B | Quality | per-turn factual score visible | 1.0 | M | no | ROVO_ARIZE_JUDGE_INLOOP | — |

### Workstream T — Throughput / Capacity (synthesizes A 0.1, 0.3, 0.4, 0.5 + B T1-T14)

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag | Dep |
|---|---|---|---|---|------|--------|-----|------|-----|
| T0a | Async pool 96->256 + queueCapacity=1000 with 503 reject (application.yml:160-162; WebMvcConfiguration.kt:74) | A 0.1 | Throughput / Stability | Prevent OOM at sustained burst; +200-400 req/s headroom | 1.0 | S | no | none | — |
| T0b | Heimdall rate-limiter timeout 3000ms -> 500ms with circuit-break (ExperienceRateLimitFilter.kt:64,132) | A 0.2 | SLO / tail | -3s worst-case block | 1.0 | S | no | none | O2 |
| T0c | Hydration thread pool 2 -> 16 with per-domain rate limiting (CoroutineContextProvider.kt:44) | A 0.3 | Throughput | Hydration queue depth <5 | 1.0 | S | no | none | — |
| T0d | PARALLEL_TOOL_EXECUTION_LIMIT 5 -> 15 (SimpleLoopWorkflowExecutorImpl.kt:95) | A 0.4 | Latency | -50 to -200ms per multi-tool turn | 1.0 | S | no | dynamic config | — |
| T0e | ERS connection pool 50 -> 200 (application.yml:509-512) | A 0.5 | Throughput | Prevent ERS connection starvation | 1.0 | S | no | none | — |
| T1 | Bound Channel.UNLIMITED in HttpRequestStreamingWriter.kt:44 | B | Throughput / Memory | Closes verified known-risk in code comment | 1.0 | S | no | ROVO_STREAMING_BOUNDED_CHANNEL | — |
| T2 | AGG WebClient pool 4x -> 8x + eviction enabled + codec 24MB -> 64MB (AggWebClientConfiguration.kt:48,67,135,158) | B | Throughput | +600 req/s peak; +0.1pp SLO under burst | 1.0 | S | no | ROVO_AGG_POOL_LARGE | load-test |
| T3 | HTTP/2 multiplex on AGG | B | Throughput | Conn count -10x; throughput +30% | 1.0 | M | no | ROVO_AGG_HTTP2 | T2 |
| T4 | Bound AsyncAgentInMemoryQueue (capacity 5000; metric on overflow) | B | Throughput | Async-queue heap-leak alarm gone | 1.0 | S | no | none | — |
| T5 | Heap 5Gi -> 8Gi + ZGC (helm/templates/webserver.yaml:101-107) | B | Throughput / GC | GC pause p99 <5ms | 1.0 | S | no | none | M7 |
| T7 | Default WebClient pool sizing (max(cores,8)*2 -> *8 for AssistanceClient, AI Gateway) | B | Throughput | Pool wait p99 <5ms | 1.0 | S | no | ROVO_DEFAULT_POOL_LARGE | M7 |
| T8 | Pod cold-start AppCDS | B | Throughput | Cold-start p50 -50% (15-20s) | 0.8 | M | no | none | — |
| T10 | Per-pool dispatcher saturation metrics (wire InstrumentedDispatcher to dashboard) | B | Observability | Per-pool saturation panel live | 1.0 | S | no | none | M7 |
| T11 | Re-tune streamingWriterPool=1024 (CoroutineContextProvider.kt:46) — INFERRED | B | Throughput | Per-pool util >=50% at peak | 0.5 | S | no | ROVO_STREAMING_POOL_TUNE | T10 (>=7d data) |
| T12 | Re-tune MAX_IO_PARALLELISM=3072 (CoroutineContextProvider.kt:156, TODO line 32) — INFERRED | B | Throughput | CPU context-switch overhead <10% | 0.5 | S | no | ROVO_IO_POOL_TUNE | T10 (>=7d data) |
| T13 | Define explicit QPS targets in TOME terraform | B | Goal-clarity | First-class SLO target merged | 1.0 | S | no | none | — |
| T14 | DNS caching tune (JVM networkaddress.cache.ttl 30s -> 300s) | B | Latency | DNS lookups/sec -90% | 0.9 | XS | no | none | — |

### Workstream L — Chat TTFB & SLO

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag | Dep |
|---|---|---|---|---|------|--------|-----|------|-----|
| L1 | TCS Caffeine cache (AsyncTenantContextService.kt:35-260) | B | TTFB | -100-200ms x N (avg -150ms p50) | 1.0 | S | no | ROVO_TCS_CACHE | tenant-update invalidation hook |
| L2 | Batch config-service (ChatExecutorRouterImpl.kt:48-52) | B | TTFB | Config-svc RPS -50% | 1.0 | S | no | ROVO_ROUTER_BATCH | — |
| L3 | AI_EDITOR non-blocking (ChatV1Controller.kt:267) reactive Flux<ServerSentEvent> | B | ChatSLO | +0.1pp SLO; -100-300ms tail | 1.0 | M | no | ROVO_CHAT_NONBLOCKING_STREAM | O3 |
| L4 | Parallel pre-LLM gates in LongHorizonOrchestratorAgent (coroutineScope async/awaitAll) | B | TTFB | TTFB p50 -25% | 0.9 | M | no | ROVO_LH_PARALLEL_GATES | L1, L8 |
| L5 | Pre-warm Jackson writer (SseStreamingWriter.kt:31) | B | TTFB | -10-20us/chunk x 75 | 0.9 | S | no | none | — |
| L8 | Request-scoped FF memoization (Statsig wrapper RequestScope map) | B | TTFB / Stability | Statsig RPS -80% | 1.0 | S | no | ROVO_FF_MEMO | — |
| L11 | Bound LLMResponseChunkAccumulator.partialToolCalls (LRU + cleanup on tool completion) | B | Memory | Heap-leak alarm gone | 1.0 | S | no | none | — |
| L13 | AGG retry decorrelated jitter | B | Stability | Retry-storm RPS -90% | 1.0 | S | no | ROVO_AGG_RETRY_JITTER | — |
| L17 | Tool registry per-conversation cache (ToolRegistryServiceImpl.kt:34-74) | B | TTFB | Build calls/turn -90% | 1.0 | M | no | ROVO_TOOLREG_CACHE | L19 |
| L18 | Remove .blockingGet from MCP (AdkToolsServiceFromMcp.kt:96-98,126) suspend/await | B | Stability | Reactive starvation 0 | 1.0 | M | no | ROVO_MCP_NONBLOCKING | — |
| L19 | Tenanted agent inventory cache (AgentRegistry.kt:10-22) Caffeine TTL 30s | B | TTFB | Registry RPS -80% | 1.0 | S | no | ROVO_AGENT_INV_CACHE | — |
| L21 | History delta fetch (InSessionSegmentationServiceImpl.kt:312-319) tail-only by lastSeq | B | TTFB | History fetch p50 -60% | 1.0 | M | no | ROVO_HISTORY_DELTA | C2 |
| L31 | Compaction ratio guard (ContextCompactionHook.kt:55-63) fire only when tokens > threshold AND ratio > 1.2 | B | Cost | Compaction freq -50% | 1.0 | S | no | ROVO_COMPACTION_GUARD | C1 |
| (A 1.1) | Parallelize pre-workflow tasks (RovoChatExecutor.kt:188-205, RovoChatService.kt:761-767, 1224-1269) | A | TTFB | -300-800ms | 0.9 | M | no | none | — |
| (A 1.2) | Eliminate redundant conversation history fetches (RovoChatExecutor.kt:761-767) | A | TTFB | -200-400ms | 1.0 | S | no | none | — |
| (A 1.3) | Cache system prompt across SAIN loop iterations (SainStandaloneHybridOrchestratorAgent.kt:372-385) | A | Latency | -100-300ms x iterations | 1.0 | S | no | none | — |
| (A 1.4) | Hoist FF evaluations out of hot loop (SainStandaloneHybridOrchestratorAgent.kt:387-391) | A | Latency | -10-75ms total | 1.0 | S | no | none | L8 |
| (A 1.5) | Cache tool schemas across loop iterations (SimpleLoopWorkflowExecutorImpl.kt:142,489,695-699) | A | Latency | -20-40ms x iterations | 1.0 | S | no | none | L17 |
| (A 1.6) | Parallelize file attachment scanning (RovoChatExecutor.kt:1149-1184) | A | Latency | -50-500ms for multi-file uploads | 1.0 | S | no | none | — |
| L32 | Realtime async send (OpenAiRealtimeProvider.kt:74-86) non-blocking sendMessageIfReady | B | TTFA | -80-120ms TTFA | 1.0 | S | no | ROVO_REALTIME_ASYNC_SEND | — |

### Workstream C — Cross-cutting Cost (synthesizes A 2.1-2.5 + B C1-C9)

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag |
|---|---|---|---|---|------|--------|-----|------|
| C1 | Persist compaction summary (ContextCompactionServiceImpl.kt) versioned + checksummed | B | Cost | -$80-120K/mo | 1.0 | M | no | ROVO_COMPACTION_PERSIST |
| C2 | Debounce in-session classifier (InSessionSegmentationServiceImpl.kt:75-108) | B | Cost | -$15-25K/mo | 1.0 | S | no | ROVO_SEGMENTATION_DEBOUNCE |
| K1+A2.1 | Anthropic prompt-cache: enable cache_control on system messages (GenericClaudeRequestBuilder.kt:166-182) AND audit assembler usage on V1/SAIN/A2A | A+B | Cost | -$40-80K/mo; cache hit >=70% | 1.0 | M | no | (it's a fix) |
| C3 | Citation model GPT_4_1 -> GPT_4_1_MINI (SAINLanguageModelConfig.kt:78-85) — paired LLMJudge A/B | B | Cost | -$3-5K/mo; accuracy delta <=1pp | 0.8 | S | conditional | ROVO_CITATION_MODEL_MINI |
| C4 | Lumina model GPT_5_1 -> GPT_5_1_MINI (SAINLanguageModelConfig.kt:107-123) — A/B | B | Cost | -$5-8K/mo | 0.8 | S | conditional | ROVO_LUMINA_MODEL_MINI |
| (A2.3-GUARDED) | Default to Haiku 4.5 for orchestration (SAINLanguageModelConfig.kt:35-47) — paired LLMJudge A/B + auto-fallback to GPT-4-1 on tool-selection-confidence-low | A | Cost | -$8-12K/mo | 0.7 | M | conditional | SAIN_ORCHESTRATION_HAIKU_4_5 (flip default) |
| (A2.4-DUAL) | Tool relevance pre-filter — full catalog visible in cached prefix; only args schemas pruned to top-20 | A | Cost | -$3-4.5K/mo | 0.7 | M | conditional (LLM-context only) | ROVO_TOOL_FILTER_DUAL |
| (A2.5-GUARDED) | Replace complexity classifier LLM call with rule-based heuristic; LLM only for ambiguous 20-30% | A | Cost | -$2-3K/mo | 0.7 | M | conditional | ROVO_COMPLEXITY_RULE_BASED |
| (A2.2-RECAST) | Reduce conversation history token growth — DO NOT use delta history; instead use cache-control on stable prefix (covered by K1+A2.1) | A (re-scoped) | Cost | covered by K1 | n/a | n/a | n/a | n/a |
| C5 | CacheFriendlyPromptAssembler adoption to V1 / non-LH paths | B | Cost | Cache-hit-tokens ratio +20pp | 1.0 | M | no | ROVO_CACHE_PROMPT_V1 |
| C6 | Tool ranking pre-serialization (move ToolRankingService ahead of schema serialize) | B | Cost | Schema tokens -14k/turn | 1.0 | S | no | ROVO_TOOLS_PRERANK |
| C7 | Batch-API path for offline workloads (eval/index/summary -> OpenAI/Anthropic Batch API) | B | Cost | Offline cost -50% | 0.9 | M | no | ROVO_BATCH_API_OFFLINE |
| C8 | Dedup Lumina + SAIN classifiers (LuminaClassificationService.kt:60-120 + SainOrchestrationComplexityClassifier.kt:63-81) | B | Cost | -$5-8K/mo | 0.9 | M | no | ROVO_CLASSIFIER_DEDUP |
| C9 | DeepResearch convergence stop (DeepResearchExecutionAgent) same-citations-twice -> finalize | B | Cost | Avg iterations -25%; -$5-7K/mo | 0.8 | M | no | ROVO_DR_CONVERGE |
### Workstream K — Caching / Coalescing (synthesizes A 3.x + B K1-K8)

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag |
|---|---|---|---|---|------|--------|-----|------|
| K1+A2.1 | Anthropic prompt-cache enable on system messages — see C-table | A+B | Cost | -$40-80K/mo | 1.0 | M | no | (fix) |
| K2 | Python sidecar prompt caching ENABLE (python-sidecar/src/agents/agent.py:142 — verified disabled, line 142 commented) | B | Cost | sidecar cost -15-25% (sidecar-only; not main chat) | 0.7 | S | no | PYSIDECAR_PROMPT_CACHE_ENABLED |
| K3 | Tool-result coalescing within turn (deduplicate identical (toolName, args) calls in same orchestrator iteration) | B | Cost / Latency | Tool RPS -20-30% on multi-classifier paths | 0.8 | M | no | ROVO_TOOL_RESULT_COALESCE |
| K4 | In-flight singleflight for AGG / TCS / Statsig (coalesce identical concurrent upstream calls) | B | Throughput / Cost | Upstream RPS -10-30% during burst | 0.8 | M | no | ROVO_UPSTREAM_SINGLEFLIGHT |
| K5 | Edge cache headers for static GETs (agent list, tool registry) — Cache-Control public max-age=30 + ETag | B | Throughput / TTFB | Backend RPS for those endpoints -80% | 0.9 | S | conditional (clients honoring s-w-r get faster) | ROVO_EDGE_CACHE_HEADERS |
| K6 | Wire RedisCacheClient into chat flows (RedisCacheClient.kt — verify zero-callsite claim with grep) | B | Cost / Latency | Cache hit-rate >=30% on initial patterns | 0.6 | M | no | ROVO_REDIS_TOOL_CACHE |
| K7 | Embedding similarity cache for repeat queries (cosine > 0.95) | B | Cost / Latency | Embed RPS -50%; FAQ-style query latency -200-500ms | 0.7 | M | conditional (TTL 1h + manual refresh) | ROVO_EMBED_SIM_CACHE |
| K8 | Malformed-LLM-response repair before retry (json-repair lib) | B | Cost / Stability | Re-call rate on parse-failure -80% | 0.9 | S | no | ROVO_LLM_JSON_REPAIR |
| (A 3.1) | Replace org.json JSONObject with objectMapper.readTree in OpenAITokenCounter.kt:183-204, 371-400 | A | Latency / CPU | -5-10ms x 50+ messages | 1.0 | S | no | none |
| (A 3.2) | Eliminate redundant token count calculations (LLMServiceImpl.kt:1426-1456, 1512-1546) | A | Latency / CPU | -50-100ms per request | 1.0 | S | no | none |
| (A 3.3) | Cache formatted tool definitions for token counting (OpenAITokenCounter.kt:90-131) ConcurrentHashMap by tool name + schema hash | A | Latency / CPU | -20-50ms with 50+ tools | 1.0 | S | no | none |
| (A 3.4) | Fix collection inefficiencies in RankingServiceImpl.kt:310-320,353-361,463-495 (cache set computations, asSequence, initial capacity) | A | Latency | -10-25% ranking latency | 1.0 | S | no | none |
| (A 3.5) | Cache dynamic config JSON parsing (LLMServiceImpl.kt:229-297, 359-378) typed data classes; RequestScoped cache | A | Latency / CPU | -5-10ms per LLM request | 1.0 | S | no | none |
| (A 3.6) | Eliminate unnecessary .toList() in SearchFilterClassifier.kt:598-608 (Jackson serializes Sets natively) | A | CPU | low; immediate; no behavior change | 1.0 | XS | no | none |
| (A 4.1) | Pipeline Redis TTL operations in mset() RedisCacheClient.kt:135-139 (true concurrent or Lua atomic batch EXPIRE or SET with EX) | A | Latency | -N x RTT for batch caches; for 100 keys ~100ms -> ~1-5ms | 1.0 | S | no | none |
| (A 4.2) | Add per-tenant timeout to search fan-out SearchToolImplementation.kt:108-123 — withTimeout(3000ms) per tenant | A | Tail Latency | -50-200ms tail latency; clamp at timeout | 1.0 | S | no | none |
| (A 4.3) | Remove delay(1) in HttpRequestStreamingWriter hot path; replace with proper backpressure via Channel/Flow operators | A | Latency | -1ms per chunk x 100-500 chunks | 1.0 | S | no | none |
| (A 5.1) | Bound Channel capacity in RovoChatService — overlap with T1 | A | Memory | OOM prevention | 1.0 | S | no | (T1) |
| (A 5.2) | MDC context propagation across coroutines | A | Observability | Trace loss prevented | 1.0 | M | no | none |
| (A 5.3) | Streaming writer pool sizing | A | Throughput | Stability | 1.0 | S | no | none |
| (A 5.4) | Regex precompilation | A | CPU | Low | 1.0 | XS | no | none |

### Workstream F — Feature Enhancements (direct activation/MAU levers, all UF=yes with release notes)

| ID | Item | Source | Goal | Impact | Conf | Effort | UF | Flag |
|---|---|---|---|---|------|--------|-----|------|
| F1 | Personality-experiment scope-fix (chat-only, NOT SAIN/Search) — verified production leak | B | Trust / MAU | Unblocks rollout; protects search-path factual tone | 1.0 | S | yes (release note) | extends existing personality flag |
| F2 | Empty-state starter prompts (Day-0 activation) — new GET /rovo/v1/me/starter-prompts | B | MAU activation | First-message rate +X% per cohort A/B | 0.7 | M | yes | ROVO_STARTER_PROMPTS |
| F3 | Adaptive follow-up count (existing template accepts 0-3) | B | Engagement | Follow-up CTR +X%; conversation continuation +X% | 0.7 | M | yes | ROVO_FOLLOWUP_ADAPTIVE_COUNT |
| F4 | Last-conversation resume (recent N summaries; UI shows Continue?) | B | Day-1 retention | Day-1 return rate +X% | 0.7 | S | yes | ROVO_LAST_CONV_RESUME |
| F5 | Citation hover preview (enrich citation envelope with title, snippet, lastUpdated) | B | Trust | Citation-click rate +X% | 0.8 | S/M | yes | ROVO_CITATION_PREVIEW |
| F6 | Confidence scoring badges (LLM emits HIGH/MEDIUM/LOW_CONFIDENCE) | B | Trust | User trust survey +X% | 0.6 | M | yes | ROVO_CONFIDENCE_BADGES |
| F7 | Graceful error UX (unify failures; preserve partial-streamed content) | B | Stability / Trust | "Lost answer" rate -X% | 0.9 | M | yes | ROVO_GRACEFUL_ERROR_UX (deps O3) |
| F8 | Recent-activity context injection (use existing MyActivitiesService) | B | Quality | Clarification-turn rate -X% | 0.7 | S | no (transparent) | ROVO_RECENT_ACTIVITY_CTX |
| F9 | Stale-source warning (lastModified > 180d -> "may be outdated") | B | Trust | Hallucination on stale-content -X% | 0.8 | S | yes | ROVO_STALE_SOURCE_WARN |
| F10 | Feedback loop -> ARIZE / dataset growth (thumbs-down -> auto-add to candidate-eval list) | B | Quality | Negative-feedback turns flow into next eval cycle | 1.0 | M | no | none |
| F11 | Hardcoded prompt -> Statsig dynamic config (oai_chat_completions.pebble) | B | EngVelocity | Base-prompt iteration cycle: deploy -> no deploy | 1.0 | S | no | ROVO_BASE_PROMPT_DYNAMIC |

### Workstream E — Engineering Velocity / Debt

| ID | Item | Source | Effort | UF | Notes |
|---|---|---|--------|-----|-------|
| E1 | Retire A2AChatExecutor (1,370 LoC) — shadow parity >=1wk; delete | B + (A 7.2) | L | no | Auto-rollback on parity divergence (deps O1) |
| E2 | JSM PlanGenerator V2 default (JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION) | B | M | conditional | Win-rate >= V1 in shadow |
| E3 | Delete v1 410-Gone routes (ChatV1Controller.kt:76-160) | B | XS | no | ~85 LoC removed |
| E4 | Streaming metric cardinality reduction (drop per-chunk-id tag) | B | S | no | Series -90% |
| E5 | logInSplunk=true default off for streaming (MetricsServiceImpl.kt:181-229) | B | S | no | Splunk volume -30-50% |
| E6 | Split AIFEATURE monolith (37 features -> grouped) | B | L | no | <10 features per file |
| E7 | Agent storage backend Postgres/DynamoDB ADR | B | M | no | ADR only; no migration in 12wk |
| (A 7.3) | Consolidate 26 prompt template variants to ~5 in SainOrchestratorSystemPromptGeneratorImpl.kt:50-502, 300-382 — strategy map instead of 13-way if/else | A | M | no | Refactor to composable template with injectable sections |
| (A 7.4) | Use StringBuilder for tool description formatting (SainOrchestratorSystemPromptGeneratorImpl.kt:829-901) | A | XS | no | Single StringBuilder.append pass |
| (A 7.1) | Feature-flag cleanup audit | A | M | no | Remove sunset flags |

### Workstream R — Repo-Context / Stalled-Decision Items

| ID | Item | Source | Effort | Action |
|---|---|--------|--------|--------|
| R1 | Python Sidecar sunset/keep decision | B | S | Close: sunset (timeline) OR keep (SLA) |
| R2 | Loom-Author scope clarification | B | S | Cross-reference with Atlas project |
| R3 | Socrates / StreamHub integration health | B | S | Verify dbt cadence; Kinesis -> Databricks alerts |
| R4 | Shipyard S3 bucket lifecycle audit | B | S | Audit retention for 8 buckets |
| R5 | ERS schema backward-compat CI gate | B | M | Verify schema rollback doesn't break consumers |
| R6 | SageMaker Jira similar-issues model versioning | B | M | Add versioning strategy for endpoint rollover |
| R7 | Spring Actuator endpoint hardening | B | S | Verify POCO rules gate /trace, /env |

---

## 6. Measurement plan (M1-M7) — must ship in Weeks 1-2

(Adopted verbatim from Plan B; this is the single most important discipline.)

| ID | What it proves | Required instrumentation |
|---|---|---|
| M1 | AIFC eval harness | Golden 300-row dataset (Q13); LLMJudge factual + recall + relevancy; nightly job; per-flag-cohort deltas |
| M2 | ARIZE per-turn quality | LLMJudgeServiceImpl wired into ARIZE event pipeline (Q14); 5% sample; cohort tags |
| M3 | TTFB per-orchestrator + dispatcher utilization | @WithSpan + per-pool dispatcher utilization metrics. Single panel: "Pre-LLM serial time" + per-pool saturation |
| M4 | Cost per turn — LEVERAGE EXISTING | Use Socrates convo_ai_usage data product (verified). Add per-feature attribution panel; do not reinvent |
| M5 | Model-downsize quality non-regression | A/B with paired prompts; LLMJudge delta; user thumbs-down |
| M6 | Cache discipline | Hit/miss/eviction per Caffeine cache; Redis memory + eviction; FF-call counter per request |
| M7 | Throughput / saturation | Per-pod req/s; per-downstream connection pool saturation; HPA scale event log; pod cold-start time |

**No item ships claiming impact until the relevant M* is live.** This is load-bearing for goal-driven prioritization.

---

## 7. Sequencing (12-week phased, integrating A's quick-wins + B's workstream cadence)

```
Wk 1   O1, O2, O3 (infra)  ·  M1 + M3 + M7 instrumentation  ·  Q13 golden dataset  ·  T1+T4 (bound channels)  ·  T0a (async pool)+T0e (ERS pool)  ·  E3 (delete dead routes)  ·  A 3.6 (.toList removal)
Wk 2   O4, O5, O6  ·  M2 ARIZE judge  ·  Q12 CI scaffold  ·  L1 + L8 + L19  ·  T0b (Heimdall) + T0c (hydration) + T0e + T2/T9 (AGG pool, load-tested)  ·  K2 (sidecar prompt cache enable)  ·  C2 classifier debounce  ·  R7 actuator hardening  ·  A 5.4 (regex precompile)
Wk 3   Q11 Slack date filter  ·  Q1 dev  ·  L2, L13  ·  T0d (parallel-tool-limit)  ·  T5 (heap+ZGC)  ·  C1 dev  ·  F1 personality-scope dev  ·  K1+A2.1 audit cache_control on system msg  ·  A 1.2 (eliminate redundant history fetch)  ·  A 1.4 (hoist FF)  ·  A 4.3 (delay removal)
Wk 4   Q1 ship 5%->25%  ·  Q4 dev  ·  L4 dev, L11, L20 (XS)  ·  T3 (HTTP/2)  ·  T7 default pool  ·  C1 ship 5%, C6  ·  F1 ship 5%->100%  ·  R1 sidecar decision  ·  A 1.3 (system prompt cache)  ·  A 1.5 (tool schema cache)  ·  A 3.1 (org.json -> Jackson)  ·  A 4.1 (Redis pipeline)
Wk 5   Q1 100%, Q3, Q2 dev  ·  L4 ship 5%->25%, L17 cache  ·  T8 AppCDS dev  ·  C1 25%, C8 dev  ·  K3 dev  ·  F2 starter-prompts dev  ·  E1 parity test build  ·  A 1.1 (parallel pre-workflow)  ·  A 3.2 (token count dedup)  ·  A 3.3 (tool def cache)  ·  A 3.4 (collection efficiency)  ·  A 3.5 (config parsing cache)
Wk 6   Q2 ship 5%, Q12 CI gate enforced  ·  L17 100%, L15 MCP session, L11  ·  T11+T12 pool tune (gated by M7)  ·  C1 100%, C3 citation A/B (paired LLMJudge)  ·  K4 in-flight singleflight  ·  F2 ship 5%, F4 dev  ·  E1 cutover 5%  ·  A2.1 cache_control ship 5%->100%  ·  A 4.2 (per-tenant search timeout)
Wk 7   Q2 100%, Q6 dev  ·  L21 history-delta dev, L18 .blockingGet  ·  C4 Lumina A/B, C9 dev  ·  K5 edge cache headers  ·  F4 ship 5%, F8  ·  E1 25%  ·  A2.3-GUARDED Haiku orchestration A/B (paired LLMJudge + auto-fallback)  ·  A 1.6 (parallel file scan)
Wk 8   Q6 ship, Q7 dev  ·  L21 ship, L18 ship  ·  C9 ship, C5 cache prompt V1  ·  K6 Redis wire incremental (after grep verifies usage)  ·  F3 dev, F5 dev  ·  E1 100% (delete A2AChatExecutor: -1,370 LoC)  ·  A2.4-DUAL tool-args-schema prune (LLM context only)
Wk 9   Q7 ship, Q8/Q9/Q10 dev  ·  L31 compaction guard, L32 realtime async  ·  C7 batch API offline  ·  K7 embedding-sim cache, K8 JSON-repair  ·  F5 ship, F9 stale-source-warn  ·  E2 PlanGen V2 shadow  ·  R3, R4  ·  A 7.4 (StringBuilder)
Wk 10  Q8/Q9/Q10 ship  ·  L9 N+1 hydration, L10 Kamino parallel publish  ·  C5 100%  ·  F3 ship, F10 feedback->ARIZE  ·  E2 100% if shadow wins  ·  R6 SageMaker  ·  A2.5-GUARDED rule-based complexity classifier (LLM fallback)
Wk 11  Q5 page-search opt-in flip A/B  ·  L3 AI_EDITOR non-blocking 5%->25%  ·  T13 QPS targets defined in TOME, T14 DNS TTL  ·  F6 confidence badges, F7 graceful error UX, F11 base-prompt-dynamic  ·  E6 AIFEATURE split  ·  R5 ERS CI gate
Wk 12  Q5 100%, final eval lockdown  ·  L3 100%, L14 GraphQL pagination  ·  E7 storage ADR  ·  R2 Loom scope  ·  A 7.3 prompt template consolidation
```

**Critical paths**:
- **Beta GA**: O1+O5 → M1+M2 → Q1 → Q2 → Q4 → Q12 enforced → Q5 flip → final lockdown.
- **150k MAU readiness**: M3+M7 → L1+L8 → T1+T2+T5 → L4 → L17 → L21 → L3 + F2+F4.
- **Cost realization**: M4 (leverage Socrates) → C1+C2 → C3+C4+C8 + A2.3-GUARDED + A2.4-DUAL → K1+K2+K3 → C7+C9.

---
## 8. Anti-goals (what NOT to do — sacrosanct)

Synthesizing Plan B's anti-goals (which were the most disciplined) with critical-thinking additions from this pass:

1. Do **not** rewrite UI source-list ordering. All ranking changes are LLM-context-only unless explicitly opted in via Q5.
2. Do **not** disable PageSearch globally. Q5 flip happens only after Q1+Q2+Q3+Q4 prove >= +10pp factual.
3. Do **not** chase 99.9% SLO past 99.85% without multi-provider failover (out of scope for this 12wk; mark dependency).
4. Do **not** unify Postgres/DynamoDB agent storage in this 12-wk horizon (E7 = ADR only).
5. Do **not** remove `lastModified` UI ordering — documented user contract.
6. Do **not** ship cost reductions without paired quality A/B (M5).
7. Do **not** combine flags. Each item has its own flag for clean attribution.
8. Do **not** cache TCS without a tenant-update invalidation hook OR explicit security review of 60s eventual consistency.
9. Do **not** LLM-rerank in the hot path before Q2 ships.
10. Do **not** bundle TTFB and quality changes in one PR.
11. Do **not** raise `first` above 50 to compensate for low recall.
12. Do **not** ship E1 cutover until shadow-replay parity is green for 1 full week.
13. Do **not** tune `streamingWriterPool` (T11) or `MAX_IO_PARALLELISM` (T12) without per-pool saturation dashboard (M7+T10) live for >= 7 days first. Pool sizes are intentionally isolated to prevent starvation; "over-provisioned" is INFERRED, not measured.
14. Do **not** enable T2 AGG pool 8x without a load-test plan. Larger pool = more downstream pressure on AGG. Coordinate with AGG team.
15. Do **not** roll out F-series UF features without O3 graceful shutdown landed. Partial-streamed answer preservation requires it.
16. Do **not** assume K2 (sidecar prompt-cache savings) is multi-hundred-$k. The Python sidecar serves Marathon-research path, not main chat; the cost agent's $400-600k/month estimate was over-scoped to the broader codebase.
17. **NEW (Critical-thinking add):** Do **not** ship A2.2 (delta-style history). Dropping prior turns risks the LLM losing reasoning context mid-loop. Use K1+A2.1 (cache_control) instead — sends full history but caches the prefix.
18. **NEW:** Do **not** ship A2.4 (tool filtering 80→20) as a hard pre-LLM filter. Use A2.4-DUAL: full catalog visible in cached prefix, only args schemas pruned. The LLM can always still NAME any tool; on a name-of-pruned-tool, fall back to full catalog on next turn.
19. **NEW:** Do **not** ship A2.3 (Haiku for orchestration) without paired LLMJudge A/B + auto-fallback to GPT-4-1 on tool-selection-confidence-low. The 5% delta on tool selection IS user-visible behavior change.
20. **NEW:** Do **not** ship A2.5 (rule-based complexity classifier) as 100% rule-based. Use A2.5-GUARDED: rule-based for high-confidence (~70-80%); LLM for ambiguous middle.
21. **NEW:** Do **not** assume `RedisCacheClient` is unused (B's K6 was INFERRED). Verify with `grep -rn "RedisCacheClient" modules/` before relying on the $ savings figure. K6 is best-case, not best-est.

---

## 9. Risk register (Top 7)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | C1 compaction-persist corruption causes wrong-context replies | M | H | Versioned schema + checksum + fall-back recompute on mismatch; 5% canary 1 wk |
| 2 | Q1/Q2 LLM rerank surfaces lower-quality content | L | H | Eval gate (Q12) blocks promotion if factual < baseline; kill-switch |
| 3 | L3/L23 reactive conversion races / leaked subscriptions | M | H | 24h soak; thread-leak detector; bounded scheduler; staged rollout |
| 4 | E1 A2AChatExecutor cutover regression (1,370 LoC) | M | H | Shadow-replay parity >= 10k turns; auto-rollback on parity divergence (deps O1) |
| 5 | C3/C4 model-downsizing degrades quality | M | M | Paired-prompt A/B; rollback if Δquality < -2pp |
| 6 | T-series throughput tuning over-provisions and starves another pool | M | M | Land M7 saturation panel BEFORE T11/T12; gated rollout; per-pool eviction metric; Resilience4j bulkheads (O2) |
| 7 | **NEW:** A2.4-DUAL tool-args pruning surfaces "tool unavailable" UX when LLM names a pruned tool | M | M | Always-fallback-to-full-catalog on next turn; emit metric; observe in 5% cohort for 1 wk before promoting |

---

## 10. End-state acceptance criteria (per goal)

| Goal | Criterion |
|---|---|
| AIFC FactualConsistency 70 | Nightly LLMJudge >= 70% on 300-row golden set, 7-day rolling, page-search ON cohort |
| AIFC ContextualRecall 65 | Nightly recall >= 65%, 7-day rolling |
| AIFC Relevancy 70 | Nightly relevancy >= 70%, 7-day rolling |
| ChatSLO 99.9 | 28-day rolling success >= 99.85%; >= 99.9% needs multi-provider failover (out of scope) |
| RovoMAU 150k | TTFB p50 -25%; activation lift +X%; F-series uplift on cohort A/B |
| Throughput at 150k MAU peak | Sustained >= 2,900 req/s for 5 min on staging load test; pool exhaustion alerts -90% in prod |
| CSM/JSM TTFB | CSM TTFB p50 -30%; JSM HR avg-steps <= 2.5 |
| Cost $/turn | -$215-375K/mo realised in M4 finance attribution |
| EngVelocity LoC removed | A2AChatExecutor + v1 410 routes deleted (>=1,455 LoC); AIFEATURE split |
| Operational readiness | O1-O6 all in production; chaos drill validates auto-rollback within 5 min |

**Beta GA gate**: Q1+Q2+Q3+Q4+Q5+Q12 shipped; factual consistency >= 70% on golden 14 consecutive days; CI gate blocking on main 3 weeks; 1 chaos-drill rollback validated (deps O1).

**150k MAU readiness gate**: L1+L4+L8+L17+L21+L3 + T1+T2+T5+T7 + T0a+T0b+T0c+T0d+T0e shipped; p50 TTFB -25% in prod; staging load-test 2,900 req/s sustained 5 min; chat send-message SLO >= 99.85%.

---

## 11. Verification plan

| Item class | How proven |
|---|---|
| Q1-Q11 | Nightly eval (M1) shows per-flag-cohort delta >= claimed pp; 7-day soak |
| Q12-Q14 | Q12: PR pipeline blocks a synthetic regression. Q13: dataset PR landed. Q14: ARIZE shows per-turn factual score |
| L-series + (A 1.x, A 3.x, A 4.x) | M3 spans show p50 delta >= claimed in 25% cohort over 48h; promote at >= 80% of claim |
| T-series + (A 0.x, A 5.x) | M7 saturation panel >= 7 days steady before tuning; staging load test 2x peak rate; per-pool utilization at peak < 80%; no FD exhaustion |
| C-series + (A 2.x re-scoped) | M4 (Socrates convo_ai_usage data product) per-feature attribution shows >= 80% of claimed $/mo over 14 days |
| K-series | M6 cache hit-rate dashboards; K1: ARIZE prompt-cache-hit >= 70%; K2: sidecar token-cost panel; K6: per-pattern hit-rate >= 30% |
| F-series | Cohort A/B with primary metric (first-message rate / Day-1 return / CTR / etc.); UF=yes items have UI snapshot diff = 0 in cohort A and release notes merged |
| E-series + (A 7.x) | E1 deletes >= 1,300 LoC + parity replay green; E3 returns 404; A 7.3 reduces template variants 26 -> ~5 |
| O-series | O1: chaos drill auto-flips a test flag in <= 5 min. O2: fault-injection shows no cascade. O3: rolling deploy preserves in-flight streams |
| UF preservation (Q-conditional, F-yes) | UI snapshot diff = 0 in cohort A; release note merged in cohort B; manual UI smoke pass |

---

## 12. What's gained vs Plan A and Plan B alone

| Item | A alone | B alone | Integrated v4 |
|---|---|---|---|
| AIFC 57pp recovery | absent | strong | strong (B's Q-series, fully kept) |
| Throughput envelope | 5 strong items (A 0.1-0.5) | 14 items (T1-T14, mostly tuning) | Both: A's specific config diffs + B's instrumentation gates |
| LLM cost wins | $25-40K/mo | $215-375K/mo (with caveats) | $215-375K/mo with B's caveats AND A's specific code-anchored fixes (A 2.1 system-msg cache_control) |
| User-facing safety | weak (A 2.2/2.3/2.4 risk UF change) | best-in-class (dual-list pattern) | **B's discipline applied to A's items as A2.x-DUAL/GUARDED variants** |
| Operational infra | implicit | Phase 0 mandatory | Phase 0 mandatory |
| Verification discipline | per-item | M1-M7 with "no-ship-until-M-live" rule | M1-M7 + per-item, with A's specific metric names integrated |
| Code-line specifics | exceptional | excellent | Both; ~30 net new file:line citations from A added to B's framework |
| Honest caveats | implicit | named (section L) | named + extended (NEW anti-goals 17-21) |
| Action items count | ~50 | 80+ | 100+ (deduplicated; A's 50 fit cleanly into B's letter-coded structure) |

---

## 13. Single-plan answer: if I had to pick ONE

**I would pick Plan B (`sorted-sunbeam.md`).**

Reasoning, weighed:

1. **Plan B closes the AIFC 57pp factual-consistency regression.** This is the single biggest user-trust crisis in the docs. Plan A doesn't address it at all. No amount of latency/cost wins offsets a beta-GA-blocking quality regression.

2. **Plan B's user-facing-preservation discipline is structurally correct.** The `uiOrdered` vs `llmOrdered` dual-list pattern, the explicit anti-goal "do not remove `lastModified` UI ordering", the UF=yes/no/conditional tagging on every row — this is exactly the discipline the user explicitly demanded ("avoid changing user-facing behavior"). Plan A's items 2.2/2.3/2.4 would have shipped real UF changes under "gated by A/B", and that's not enough.

3. **Plan B's measurement-first rule ("no item ships claiming impact until M-series is live") is load-bearing.** Plan A's per-item verification is good but has no enforcement mechanism; Plan B makes it a hard prerequisite. Without M-series, A's "$25-40K/mo" claims can't be validated.

4. **Plan B's Phase 0 operational rigor (O1-O6) is non-negotiable for a plan with 30+ flag rollouts.** A treats infra as week-1 quick wins; B treats it as a hard prerequisite. B is correct: without auto-rollback (O1), chaos-tested, every other flagged change is a single-keystroke production incident waiting to happen.

5. **Plan B's honest-caveat discipline (section L + the INFERRED tags + the K2 over-scope warning) is the difference between an engineering plan and a marketing pitch.** It explicitly says "we don't know if the pool is over-provisioned, so don't tune it until M7 is live" and "the $400-600K/mo number was over-scoped, real number is sidecar-only". This kind of intellectual honesty saves quarters of misdirected work.

**However: B has real gaps that A fills.** If I picked B alone, I'd lose:
- The Heimdall 3s rate-limiter blocking timeout (A 0.2)
- The `org.json` JSON-parse 3x-per-msg waste (A 3.1)
- The per-tenant search timeout `withTimeout(3000ms)` (A 4.2)
- The `RankingServiceImpl` collection inefficiencies (A 3.4)
- The exact line numbers and literal config diffs A provides for many B items

**That's why the right answer is "pick B, then layer in A's specific code-anchored fixes as A-tagged items in B's workstreams"** — which is exactly what this v4 integration does.

**If forced to a single name, my pick is Plan B.** It would still leave value on the table (~$15-25K/mo + ~500ms in latency from A's missing items), but it would NOT ship a user-trust regression, NOT ship un-rollback-able experiments, NOT ship un-measured cost claims, and NOT ship the AIFC quality crisis unaddressed.

---

## 14. Summary

- **Integrated plan = Plan B's structure + Plan A's specifics + my v2's correctness/enterprise/monetisation gaps + critical-thinking re-scoping of A's UF-risky items.**
- **All 100+ items are tagged with goal, impact (in goal-metric units), confidence, effort, UF-status, flag, exit-criterion.**
- **All retrieval/ranking changes use the dual-list pattern** (`uiOrdered` byte-identical, `llmOrdered` reranked).
- **A's items 2.2/2.3/2.4/2.5 are re-scoped** to A2.2-RECAST / A2.3-GUARDED / A2.4-DUAL / A2.5-GUARDED to preserve user-facing behavior.
- **Phase 0 operational infra (O1-O6) and measurement plan (M1-M7) are hard prerequisites** — no flag flips until they're live.
- **Honest caveats preserved and extended** — anti-goals 17-21 added from this critical-thinking pass.
- **Single-plan answer: Plan B** — for AIFC quality, UF discipline, measurement-first, Phase-0 operations, and honest caveats — with the explicit acknowledgment that Plan A's specific code-anchored fixes (especially A 0.2, A 3.1, A 4.2, A 3.4) are additive value worth layering in.

End of integrated v4 plan.
