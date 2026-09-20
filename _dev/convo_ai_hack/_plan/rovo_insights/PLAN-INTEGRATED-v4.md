# Rovo Insights Improvement Plan — v4.0 (UX-FIRST REWRITE)

:Version: 4.0
:Status: ACTIVE — supersedes v3.x
:Date: 2026-05-03
:Triggering event: B0.1 PR #29064 was caught and closed mid-flight as a hidden UX regression that v3.x plan called "no quality risk"
:Author: Tony Chen

---

## 0. The North Star — and what we are NEVER allowed to do

> **We do not silently degrade user experience in the name of system efficiency. Period.**
>
> Every plan item is classified by its UX impact. Items that degrade UX are either:
>   (a) explicitly product-decided with PM sign-off, OR
>   (b) rejected outright in favor of UX-neutral alternatives.
>
> "Most users won't notice" is **NOT** a valid justification.
> "Acceptable tradeoff because cached data was already old" is **NOT** a valid justification.
> "−85% cost with no quality risk" is **NOT** a valid claim unless evidence-backed.

---

## 1. Why v4.0 exists

### 1.1 The B0.1 incident (2026-05-03)

| Step | What happened |
|---|---|
| v3 plan claimed | "B0.1 cache TTL 1d→7d: −85% LLM cost, no quality risk, the if-only-one-thing answer" |
| Engineer (me) implemented | Dynamic config, default 168h, full PR #29064 with tests, all green |
| User caught it | "Will user not able to get latest insights?" |
| Honest answer | YES — users would see up to 7-day-old data. Recognition received yesterday wouldn't appear for up to 6 days. Real UX regression. |
| Outcome | PR closed; v3.x plan retired; v4.0 written with UX-first audit |

### 1.2 What the v3.x plan got wrong

1. **B0.1's −85% cost claim** was marketing language, not evidence. There's no Splunk telemetry to support it.
2. **B0.1's "no quality risk" claim** was false. The plan conflated *"cache entries can be old"* (true) with *"users won't notice staleness increase"* (false).
3. **B6.1 (structured output)** depends on a feature (LLM `structuredOutputEnabled`) that the plan explicitly cannot verify works — should never have been marked ready.
4. **B7 (prompt caching −88%)** depends on a Gateway cache hit ratio of 70% that's pure speculation.
5. **B3 wall-clock budget = 180s** is a guess, not a measured p99 — risks truncating legitimate slow generations.
6. **B0.6 rate-limit 3/hour** is a feature removal disguised as security improvement.

### 1.3 The discipline we adopt going forward

| Rule | What it means |
|---|---|
| **UX-Neutral by default** | Items that touch user-visible behavior require PM sign-off and an A/B test, not just code review |
| **Evidence > intuition** | Cost/latency claims must cite a metric, not "we think most users…" |
| **No silent tradeoffs** | If a change has any UX impact, it must be in the title of the bundle, not buried in the risk section |
| **Test must prove the bug** | Every bug fix must include a test that FAILS on master pre-fix |
| **Telemetry first, optimization second** | Without B9 observability, no cost/latency claim is verifiable |

---

## 2. Bundle re-classification (the core of v4.0)

Every bundle from v3 has been re-audited by 4 independent agents. Here is the TRUE classification:

### 2.1 Three categories

| Category | Definition | Action |
|---|---|---|
| **A — UX-Neutral** | Pure waste-elimination. Same user-visible output, less work behind the scenes. | ✅ Ship freely. Highest priority. |
| **B — UX-Improving** | User-visible behavior gets *better* (e.g., partial results returned instead of all-fail). | ✅ Ship freely. Strong priority. |
| **C — UX-Affecting** | User-visible behavior changes — even subtly. Includes "user might wait longer," "user might see staler data," "user might lose a feature." | 🛑 Requires PM sign-off + A/B test + explicit "yes-I-know" approval. |

### 2.2 Re-classified bundle table

| Old ID | New ID | Title | Category | UX impact verdict | Evidence quality | Decision |
|---|---|---|---|---|---|---|
| B9 | **A1** | Observability foundational (metrics, dashboards) | A | NONE | Strong (telemetry only) | ✅ Ship FIRST |
| B0.2 | **A2** | Gate full-prompt logging behind flag | A | NONE | Strong | ✅ Ship |
| B0.3 | **A3** | Hoist Statsig flag eval to once per request | A | NONE | Strong | ✅ Ship |
| B0.4 | **A4** | `filter+map` → `mapNotNull` refactor | A | NONE | Strong | ✅ Ship |
| B1 | **A5** | `coroutineScope` → `supervisorScope` (cancellation isolation) | B | IMPROVES UX | Strong | ✅ Ship |
| B2 | **A6** | Hydration parallelization + dedup (NO TTL change, just dedup the existing fetch) | A | NONE | Weak claim, real fix | ✅ Ship |
| B4 | **A7** | Notification reliability (stop swallowing exceptions) | A | NONE | Strong | ✅ Ship |
| B5 | **A8** | Cache salt memoize (in-process, 30s TTL) | A | NONE (operator-facing only, not user-facing) | Weak claim, real fix | ✅ Ship |
| B0.5 | **A9** | Add exponential backoff to retries | A | NONE (only changes retry timing, not retry count) | Strong | ✅ Ship |
| B6.2 | **A10** | Partial JSON recovery (graceful degradation) | B | IMPROVES UX | Weak claim, real fix | ✅ Ship |
| **NEW** | **A11** | Person hydration deduplication across the 6 insight types (true waste — same person fetched 6×) | A | NONE | Strong (agent-confirmed) | ✅ Ship |
| B3 | **A12** | Handler idempotency via SETNX (just the dedup; NOT the wall-clock budget) | A | NONE | Strong | ✅ Ship |
| **NEW** | **A13** | Sweeper for orphaned tasks — but only AFTER B9 telemetry tells us what `stuck` looks like | A | NONE | Awaiting data | 🟡 Ship after A1+2 weeks data |
| B8 | **A14** | Cache stampede lock per user — but only AFTER B9 tells us actual cache-miss rate | A | NONE (when correctly designed) | Awaiting data | 🟡 Ship after A1+data |
| B6.3 | **A15** | Hoist conversation ID — but ONLY after verifying chat-service supports concurrency | A | NONE (when correctly designed) | Pre-gate unresolved | 🟡 BLOCKED on chat-service confirmation |
| B10 | **A16** | Platform-wide P1-P5 fixes (SAIN-LH etc.) | A | NONE | Strong | ✅ Ship (separate team) |
| --- | --- | --- | --- | --- | --- | --- |
| **B0.1** | **❌ REJECTED** | Cache TTL 1d→7d | C | DEGRADES UX | Marketing claim | ❌ NEVER SHIP |
| **B0.6** | **❌ REJECTED** | Rate-limit force-refresh 3/hour | C | REMOVES FEATURE | Disguised as security | ❌ NEVER SHIP without PM sign-off |
| **B6.1** | **❌ REJECTED** | LLM structured output | A (would be) | Depends on unverifiable LLM capability | Unfounded | ❌ DO NOT SHIP until chat-service owner confirms support + test proves it |
| **B7** | **❌ REJECTED as currently scoped** | Prompt dedup + caching for −88% | C | Risks LLM quality regression | Unfounded (70% cache hit assumption) | ❌ DO NOT SHIP cost claim; the dedup itself can ship as A18 below |
| **NEW** | **B0.1'** | Conditional regeneration via cheap source-poll OR event-driven invalidation | A | NONE (regen only when source actually changed) | Feasibility: 8-12 person-days per agent investigation | ✅ THIS replaces B0.1 — proper way to reduce LLM cost without UX impact |
| **NEW** | **A17** | Prompt-template dedup (Pebble template extraction, no reordering) — keeps 6 prompts semantically identical | A | NONE | Strong | ✅ Ship — separate from B7's risky reordering |
| **NEW** | **A18** | Prompt-cache enable at AI Gateway (infrastructure only, no prompt change) — measure actual hit rate before claiming savings | A | NONE | Awaiting measurement | 🟡 Ship A1 first, then measure |

### 2.3 Bundle count comparison

| | v3.x | v4.0 |
|---|---|---|
| Total bundles | 11 (with sub-items 17) | 18 (A1-A18) + 4 explicit rejections + 1 replacement |
| UX-Neutral (Cat A) | unclear | 16 |
| UX-Improving (Cat B) | unclear | 2 |
| UX-Degrading (Cat C) | mixed in | 0 (all rejected or replaced) |
| Bundles awaiting data before ship | unclear | 4 (A13, A14, A15, A18) |
| Bundles explicitly rejected | 0 | 4 (old B0.1, B0.6, B6.1, B7-as-scoped) |

---

## 3. The TRUE waste items that v3.x missed

Per the parallel agent audit, these are real, evidence-backed waste items in the current code:

### 3.1 Person hydration called 6× per regen (A11) — NEW

| Property | Value |
|---|---|
| File | `RovoInsightsServiceImpl.kt:484-496` (hydratePersonReferences) + `:650-679` (generateInsightForType) |
| Waste | Each of 6 insight types calls `hydratePersonReferences()` independently. Same `getUserProfile()` RPC happens 6× for users mentioned in multiple types. |
| Cost | ~6-12 redundant RPCs per regen, ~120-240ms of latency per regen |
| Confidence | HIGH (agent-confirmed pattern) |
| User impact | NONE — same data returned, just less work behind the scenes |
| Fix | Pre-fetch + cache user profiles once before the 6-type fan-out; pass cache as context |
| Effort | ~half day |

### 3.2 Retry without backoff costs unnecessary RPC (A9 — was B0.5)

| Property | Value |
|---|---|
| File | `Retryable.kt:12-28` |
| Waste | On transient LLM error, retries 3× with zero delay → 3× LLM call cost in rapid succession |
| Cost | ~2× wasted LLM calls per failed type, ~3-5s latency per wasted attempt |
| Fix | Exponential backoff (100ms → 500ms → 2s); log retry reason |
| User impact | NONE on success; on failure, user waits the same total time |

### 3.3 Cache salt fetched per cache op (A8 — was B5)

| Property | Value |
|---|---|
| File | `RovoInsightsCacheImpl.kt:74-80` |
| Waste | `rolloutService.getDynamicConfigField(ROVO_INSIGHTS_CACHE_SALT)` called on every cache get/put — Statsig RPC each time |
| Fix | In-process memoize with 30s TTL |
| User impact | NONE if salt unchanged; up to 30s lag for operator-flipped salt rotation (operators tolerate this; users never see it directly) |

### 3.4 Cancellation isolation (A5 — was B1)

| Property | Value |
|---|---|
| File | `RovoInsightsServiceImpl.kt:631-644` |
| Bug | `coroutineScope { ... .awaitAll() }` cancels all 5 sibling jobs when 1 fails. User sees ZERO insights instead of 5/6. |
| Fix | `supervisorScope { ... .awaitAll() }` + `runCatching` per type |
| User impact | **IMPROVES UX** — user sees 5 insight types instead of 0 when 1 type fails |

### 3.5 Hydration parallelization + dedup (A6 — was B2)

| Property | Value |
|---|---|
| File | `RovoInsightsServiceImpl.kt:322-334, 391-455` |
| Waste | User-profile hydration is sequential where it could be parallel; same person fetched multiple times |
| Cost (per agent estimate) | Variable — depends on dedup ratio. v3 claimed −5-9s p95 but agent flagged this as WEAK without baseline measurement |
| Fix | Parallel + dedup. Pair with A11 to fully eliminate the 6× duplication. |
| User impact | NONE — same data, just faster |

---

## 4. Replacing B0.1 with B0.1' (the right way to reduce LLM cost)

The cost-reduction goal is real. The v3.x approach (make cache stale longer) was wrong because it sacrificed freshness. The right approach: **only regenerate when source data actually changed**.

### 4.1 Two viable mechanisms

#### Option α — Cheap source-poll on `/status`

```
On /status:
  cheap_poll = jql("updated >= ${last_regen_time} AND assignee = ${user}")  // ~50-200ms
                + confluence_pages_modified_since(${last_regen_time}, ${user})
                + recognition_events_since(${last_regen_time}, ${user})
  if cheap_poll.has_any_changes():
    enqueue_full_regen()    // expensive LLM call
  else:
    serve_from_cache()      // free
```

| Property | Value |
|---|---|
| Cost win | ~70-90% (regen only when source changed; most days for most users → no change) |
| Freshness | ✅ User always sees latest insights when source data changed |
| Effort | ~3-5 person-days |
| Risk | "Cheap poll" must catch all material changes (need to define "material") |

#### Option β — Event-driven invalidation (gold standard)

```
Subscribe to: jira.issue.updated, confluence.page.updated, recognition.received
On event for user U:
  invalidate_cache(U)
On /status:
  if cache.exists():
    serve_from_cache()    // freshly invalidated by events
  else:
    enqueue_regen()
```

| Property | Value |
|---|---|
| Cost win | ~80-95% (regen only fires when something happened) |
| Freshness | ✅✅ BETTER than today (within seconds, not hours) |
| Effort | ~8-12 person-days (per agent investigation) |
| Risk | Need event subscriptions for each source; rate-limiting per user |

### 4.2 Recommendation

**Ship Option α (cheap source-poll) FIRST as B0.1'-α**, then evolve to Option β as B0.1'-β if Atlassian event infra makes it cheap.

Order:
1. A1 (observability) — foundational
2. A11 (person dedup) + A6 (parallel hydration) + A5 (cancellation isolation) — pure waste-eliminations
3. **B0.1'-α** (cheap source-poll) — replaces v3's B0.1 with a UX-safe approach
4. A9 (backoff), A8 (salt memoize), A7 (notification reliability) — mop-up
5. A13, A14 (sweeper, stampede lock) — only after A1 telemetry exists
6. **B0.1'-β** (event-driven) — only if A1 metrics show further savings are needed

---

## 5. The "if only ONE thing" answer for v4.0

| v3 said | "B0.1 — bump cache TTL 1d→7d" |
| v4 says | **"A1 — Observability first."** |

Without A1, no cost or latency claim is verifiable. We just shipped a PR (B0.1) where the claimed −85% had **zero supporting telemetry**. That cannot happen again.

After A1: the next cost win is **B0.1'-α** (cheap source-poll), NOT cache TTL extension.

---

## 5.5 IMPACT-RANKED Top 10 (the v4.5 update — NOT shipping-order, IMPACT-order)

### 5.5.1 Reading guide

| Question | Answer |
|---|---|
| **What is being ranked?** | Cat-A/B (UX-safe) bundles only. Cat-C is rejected, not ranked. |
| **What is the ranking criterion?** | Composite **business/technical impact** = (cost reduction × throughput gain × p95 reduction × p99 reduction × stability gain). UX is a HARD constraint (must NOT regress), but UX neutrality alone does not earn ranking — only impact does. |
| **Where does evidence come from?** | Code-verified by 3 independent agents + my independent verification. Items with WEAK evidence are flagged; not silently included. |
| **Why is this different from §5's "ship A1 first"?** | §5 is shipping-order (foundational items ship first to enable measurement). §5.5 is impact-order (where the biggest value lives, regardless of when it ships). Both views are needed. |

### 5.5.2 The IMPACT-RANKED Top 10

Notation: 🟢 STRONG evidence · 🟡 MEDIUM evidence · 🔴 WEAK evidence (still real, but quantification is unverified)

| Rank | ID | Item | Cost impact | Throughput impact | p95 impact | p99 impact | Stability impact | Compound? | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **A6 + A11 (paired)** ✅ SHIPPED-PENDING-MERGE PR #29074 (commit `3292d410234` after 4 review-feedback fixes incl. supervisorScope) | **Hydration parallelization + person dedup** — eliminates 6× duplicate person fetches AND parallelizes the sequential `mapNotNull` at `RovoInsightsServiceImpl.kt:484-496` | LLM cost: ~0 (no LLM saved). UserService RPC: **−~70-90%** (54 sequential calls → ~15 unique parallel) | **+10-30%** (sequential blocking → parallel; semaphore-bounded) | **−5s p95** (5.4s baseline → ~350ms) | **−5s p99** (same path) | NEUTRAL | **YES — A6 enables parallelism, A11 reduces work; multiply** | 🟢 **EMPIRICAL** (`HydrationBenchmarkTest.kt`, run via `ROVO_BENCHMARK=true ./gradlew ...`): REALISTIC PROD 6×10 60% overlap = **58.65× speedup** (3214ms→55ms); STRESS 6×20 50% overlap = **113× speedup** (6422ms→57ms); HEAVY OVERLAP / NO OVERLAP = ~29× each. v3's "−5s p95" claim VALIDATED + EXCEEDED. See `.ai_employee/projects/rovo_insights/tasks/A6-A11-hydration-paired.md` §4. |
| **2** | **A5** ✅ SHIPPED-PENDING-MERGE PR #29085 (commit `482f9abdae91`) | **Cancellation isolation** — `coroutineScope` → `supervisorScope` so 1 type failing doesn't cancel other 5 | UNCHANGED | UNCHANGED on success path; **+1.0×** on partial failure (5/6 succeed instead of 0/6) | UNCHANGED on success | **−12 min worst-case** (cascade eliminated) | **MAJOR** — eliminates "1-fails-cancels-all-5" → reduces 0-insight events by ~80% | NO — standalone | 🟢 EMPIRICAL: 4 unit tests in `RovoInsightsServiceImplTest`, including timing-based regression guard that PROVES siblings complete despite first failure (counter == 2 post-A5; would == 0 pre-A5). New metrics `ROVO_INSIGHTS_TYPE_FAILED` + `ROVO_INSIGHTS_PARTIAL_SUCCESS` wired for A1 dashboards. See `.ai_employee/projects/rovo_insights/tasks/A5-cancellation-isolation.md` |
| **3** | **B0.1'-α** | **Conditional regeneration via cheap source-poll** — replaces v3's rejected B0.1 with the right design | **−40% to −90% LLM regen** (only when source actually changed) | **+30-50%** (fewer LLM calls per second; same hardware serves more users) | UNCHANGED on cache miss | UNCHANGED on cache miss | **POSITIVE** — fewer "stuck" because fewer regens | NO but enables A18 prompt cache | 🟡 cost reduction depends on user visit-pattern × source-change-pattern; needs A1 to validate |
| **4** | **A1** | **Observability foundational** — metrics, dashboards, p50/p95/p99 latency, cache hit/miss, LLM-call rate | UNCHANGED directly; **enables ALL other items' validation** | UNCHANGED directly; **enables capacity planning** | UNCHANGED directly | UNCHANGED directly | UNCHANGED directly; **enables stuck-rate measurement** | **YES — multiplies confidence in every item below** | 🟢 verified: existing `MetricKey.ROVO_INSIGHTS_*` infra exists, just needs more dashboards |
| **5** | **A12** | **Handler idempotency via SETNX** — prevents duplicate generations from SQS at-least-once semantics | **−duplicate LLM calls** (estimated 0.5-2% of total regens are duplicates today) | UNCHANGED | UNCHANGED | UNCHANGED | **MAJOR** — closes "stuck generating" caused by handler crashes mid-flight | **YES** — required prerequisite for A7 SQS redrive (without A12, A7 causes duplicates) | 🟢 verified: SQS visibility 30s with auto-extend; crash gap exists |
| **6** | **A9** | **Exponential backoff on retries** — 100ms → 500ms → 2s with jitter | **−2× wasted LLM calls** per failed type during transient failures | **+~10%** during failure windows (no rate-limit cascade) | UNCHANGED on success | **−10s** (eliminates retry-burst exhausting timeout) | **MAJOR** during incidents | NO — standalone | 🟢 verified: `Retryable.kt:13-29` has zero delay |
| **7** | **A10** | **Partial JSON recovery** — graceful degradation when LLM returns malformed JSON | **−retry waste** (estimated 2-5% of regens hit this) | UNCHANGED | UNCHANGED | **−30s-4min** (per partially-broken response) | **MAJOR** — user sees 5/6 valid types instead of total failure | **YES** — pairs with A5 to maximize "user always sees something" | 🟡 frequency unverified — need A1 to know how often LLM returns bad JSON |
| **8** | **A17** | **Prompt-template dedup** (Pebble extraction, **NO reordering**) — pulls common boilerplate into shared template | **−40% input tokens per gen** (36k → ~22k, conservative; v3's 9-12k assumed Gateway cache which is now A18) | UNCHANGED | **−500ms-1s** (smaller prompts → faster LLM TTFT) | **−500ms-1s** (same) | NEUTRAL | **YES** — pairs with A18 (prompt cache) for compound savings | 🟡 v3 evidence: 118 KB total templates, dedup ratio plausible but unverified |
| **9** | **NEW (V4.5)** | **Telemetry .map() chain dedup** — `RovoInsightsServiceImpl.kt:227-301` does 8+ separate `.map()` over same lists in hot path | UNCHANGED | **+5-10%** (less hot-path CPU) | **−20-50ms p95** (per-request CPU) | **−20-50ms p99** | NEUTRAL | NO — standalone | 🟢 verified by me: 8+ `.map()` calls visible in `streamToolTelemetryLogContext` |
| **10** | **A8** | **Cache salt memoize** (in-process 30s TTL) — eliminates per-cache-op Statsig RPC | UNCHANGED | **+~30×** Statsig RPC reduction (cheap dependency) | **−5-10ms** per cache op (every request) | **−5-10ms** | **POSITIVE** — reduces Statsig timeout exposure | NO but reduces blast radius of Statsig outage | 🟢 verified: `RovoInsightsCacheImpl.kt:74-80` calls `getDynamicConfigField` per op |

### 5.5.3 Items that ALMOST made the top 10 (and why not)

| Item | Why not in top 10 | Where it ranks |
|---|---|---|
| **A7** (notification SQS redrive) | Real reliability win, but **requires A12 first** to avoid causing duplicates. Drops to rank 11 (ship after A12). | 11 |
| **A2** (gate full-prompt logging) | Trivial win (~50-200ms × 6). Worthwhile but small. Bundle into a "hygiene" PR with A3, A4. | 12 |
| **A3** (hoist Statsig flag eval) | Trivial pattern fix. <50ms win per request. Hygiene. | 13 |
| **A4** (`filter+map` → `mapNotNull`) | 20-50ms win. Hygiene. | 14 |
| **A13** (sweeper for stuck tasks) | DEFERRED — needs A1 telemetry to size correctly. Ship after 2 weeks of A1 data. | 15 |
| **A14** (cache stampede lock per user) | DEFERRED — premature without A1's actual cache-miss rate data. May not even be needed. | 16 |
| **A15** (hoist conversation ID) | BLOCKED on chat-service owner confirming concurrency support. Cannot ship without. | (blocked) |
| **A18** (enable AI Gateway prompt cache) | **Compounds with A17** but needs measurement first. Ship after A17 + A1 to measure actual hit rate. | 17 |
| **A16** (platform-wide P1-P5) | Different team. Tracked separately. | (other team) |

### 5.5.4 Critical thinking — why this ranking is different from v3's

| v3's ranking criterion | v4.5's ranking criterion | Difference |
|---|---|---|
| "Biggest single cost win" → put B0.1 (cache TTL) at #1 | "Biggest UX-safe impact" → A6+A11 (hydration) at #1 | v3 conflated cost with impact. B0.1 saves cost by degrading UX → net negative. A6+A11 saves cost AND latency AND throughput with zero UX impact → net positive. |
| "Sprint number" → B0 quick wins shipped together | "Compound impact" → pair items that multiply | A6 alone is good; A6+A11 is great. Ship them together as one PR. |
| Marketing language allowed: "−85%, no quality risk" | Evidence required: 🟢/🟡/🔴 confidence per item | 4 items in v3 had unverified claims. v4.5 requires telemetry citation. |
| Rank items by author's intuition | Rank items by composite metric × evidence quality | Forces the difficult conversation about which "biggest" win is real |

### 5.5.5 Compound effects (the items that multiply each other)

| Pair | Why they multiply | Combined impact |
|---|---|---|
| **A6 + A11** | A6 makes hydration parallel; A11 reduces what needs hydrating. Together: ~0.5s instead of 5.4s. | −5s p95 (vs −2s for either alone) |
| **A12 + A7** | A12 makes redrive safe; A7 enables redrive. Together: SQS at-least-once becomes exactly-once. | Stuck rate <0.1% (vs >0% for either alone) |
| **A5 + A10** | A5 isolates type failures; A10 recovers partial JSON. Together: user almost always sees ≥5 of 6 types. | Partial-success rate >99% (vs ~95% for either alone) |
| **A17 + A18** | A17 makes prompts dedup-able; A18 actually caches them at Gateway. Together: −80% effective tokens. | −80% LLM input cost (vs −40% for A17 alone) |
| **A1 + everything** | A1 makes every other item's impact measurable. | Confidence in every claim above |

### 5.5.6 The ONE-LINER answer for v4.5

> **"Ship A1 first (so you can measure), then immediately bundle A6+A11 as a single PR (the biggest UX-safe impact), then A5 (the biggest stability win)."**
>
> That's the first PR sequence that delivers maximum impact without UX regression.

---

## 6. Test discipline (carried forward from v3.5 §17, with corrections)

### 6.0 Per-task traceability requirement (NEW v4.5 — from B0.1 incident; format updated v4.6 from `responsible-ai-api/tasks/`)

**Every implementation task — proposed, in-progress, shipped, rejected, deferred, or blocked — MUST have a corresponding human-readable task file at:**

```
<repo-root>/.ai_employee/projects/rovo_insights/tasks/<ID>-<status?>-<kebab-title>.md
```

**Where `<repo-root>` = `atlassian_packages/conversational-ai-platform/`.**

#### Why this exists

The B0.1 incident (2026-05-03) had a complete plan (v3.5) and a complete PR (#29064 with passing tests, structured description, DoD checklist). What was missing was a **single document that tied "what we decided," "what we shipped," "what telemetry validated it," and "what the user/PM signed off on."** The PR description was forward-looking; the plan was abstract; nothing tracked the implementation specifically. v4.5 adds this discipline.

#### What every task file must contain (UPDATED v4.6 — integrated v2 format)

The v4.5 format was a 13-row markdown table header; learning from `responsible-ai-api/tasks/` patterns, v4.6 uses an **integrated v2 format** that combines the best of both:

**Header (lightweight + grep-able):** key:value lines, NOT a table. Enables `grep -l "^Status: in_progress" tasks/*.md`:

```
Status: in_progress | shipped-pending-merge | shipped | rejected | deferred | blocked | proposed
Priority: P0 | P1 | P2 | P3
UX-Class: A | B | C  (Cat C requires PM sign-off — see §2 of the file)
Plan: PLAN-INTEGRATED-v4.md §5.5 rank #N
PR: https://bitbucket.org/.../pull-requests/<NNNNN>  (or "_pending_" / "_n/a_")
Replaces: <prior-IDs>  (or "_none_")
Author: <name>
Date opened: YYYY-MM-DD
Date PR opened: YYYY-MM-DD  (or "_pending_")
Date merged: YYYY-MM-DD  (or "_pending_")
```

**Required sections:**

| § | Section | Why it matters |
|---|---|---|
| 1 | **Problem** (with `\| Issue \| Evidence \|` table — file:line + measurement) | Forces evidence-based motivation, not abstract assertion |
| 2 | **UX Classification rationale** (5-question form) | If any "YES" without PM sign-off → REJECT. **Catches B0.1-class incidents before code is written.** |
| 3 | **Approach** (separate from Problem; alternatives rejected with WHY) | Audit trail of design choices |
| 4 | **Impact: claimed vs measured** (table with claimed cell + measured cell + benchmark cite) | Forbids marketing language; benchmark or telemetry MUST back claim |
| 5 | **Tests added** (FAIL-on-master / PASS-on-PR proof; benchmark file path if applicable) | Same as v3.5 §17.5.2 + benchmark requirement |
| 6 | **TODOs** (executable checklist with `[ ]` items) | Action-oriented; reviewer can run each item |
| 7 | **Acceptance criteria** (each criterion is a runnable command) | Reviewer-runnable, e.g. `gradlew :module:test --tests "*X*" → BUILD SUCCESSFUL` |
| 8 | **Rollback plan** (table: trigger / action / ETA) | Pre-mortem |
| 9 | **Replaces** (prior IDs subsumed) | Visible supersession (e.g. A6+A11 replaces v3's B2 + new dedup) |
| 10 | **Work log** (chronological, dated entries — fill DURING) | Day-by-day diary; AI-Reviewer feedback gets logged here per §6.4 |
| 11 | **Lessons learned** (retrospective — fill AFTER merge) | Captures knowledge the plan didn't predict |
| 12 | **Cross-references** (compounds with, supersedes, linked tickets) | Enables tracing chains across items |

**Lifecycle (NEW v4.6):** when a task ships AND merges, `git mv tasks/<ID>-*.md tasks/done/`. The `done/` folder is the historical archive; live work is at the top level of `tasks/`. This makes "what's still live" a 1-second `ls tasks/*.md`.

#### Naming convention

| Pattern | Example |
|---|---|
| `<ID>-<kebab-title>.md` | `A5-cancellation-isolation.md` |
| `<ID>-<ID>-<kebab-title>.md` | `A6-A11-hydration-paired.md` (compound tasks) |
| `<ID>-REJECTED-<kebab-title>.md` | `B0.1-REJECTED-cache-ttl-extension.md` |
| `<ID>-DEFERRED-<kebab-title>.md` | `A13-DEFERRED-stuck-task-sweeper.md` |
| `<ID>-BLOCKED-<kebab-title>.md` | `A15-BLOCKED-conversation-id-hoist.md` |

#### The traceability chain (machine-followable)

```
Plan v4.0 (this document)
  ↓ §3 / §5.5 references item ID
Task file (.ai_employee/projects/rovo_insights/tasks/<ID>.md)
  ↓ References plan §, links to Jira ticket and PR
Jira ticket (CTSC-NNNN)
  ↓ Description links back to task file
Bitbucket PR (#NNNNN)
  ↓ Description copies §6.1 DoD checklist + links to task file
CI test run
  ↓ Test results captured
A1 telemetry dashboard
  ↓ Measured impact populated
Task file (re-opened post-merge)
  ↓ §4 Impact "Measured" populated; §7 Lessons populated
Plan v4.x update
  ↓ Bundle ID marked SHIPPED with citation to task file + dashboard
```

Any link in this chain that breaks = a B0.1-class incident waiting to happen.

#### Bootstrap state (already created 2026-05-03)

| File | Purpose |
|---|---|
| `.ai_employee/projects/rovo_insights/README.md` | Folder overview + naming convention |
| `.ai_employee/projects/rovo_insights/tasks/_TEMPLATE.md` | Canonical template — copy for every new task |
| `.ai_employee/projects/rovo_insights/tasks/B0.1-REJECTED-cache-ttl-extension.md` | Retroactive incident record |

### 6.1 Per-bundle DoD checklist (every PR copies this — UPDATED v4.6 with benchmark requirement)

**NEW v4.6 — benchmark-as-evidence rule:** if an item claims a latency, throughput, or cost improvement, the PR MUST include a local benchmark in the same module that empirically validates the claim. Worked example: `HydrationBenchmarkTest.kt` for A6+A11 — measured 58.65× speedup vs v3's predicted "−5s p95". Pattern:

| Aspect | Requirement |
|---|---|
| Location | Same module as the code change, in `src/test/kotlin/.../<X>BenchmarkTest.kt` |
| Gating | `assumeTrue(System.getenv("ROVO_BENCHMARK") == "true")` in `@BeforeEach` — does NOT slow down `unit-tests-rovo` shard |
| Methodology | ≥3 runs (warm-up + N measurements), report mean + 95% CI; old-vs-new in same test for fair comparison |
| Scenarios | At minimum: REALISTIC (matches expected prod load), EDGE (boundary cases), STRESS (worst-case) |
| Output | structured `appendLine` block with old/new wall time + speedup factor + saved ms |
| Citation | Task file `## Impact: claimed vs measured` table cites benchmark file + actual numbers |

**When NOT required:** items that are pure UX-improvements with no perf claim (e.g. A5 fixes 0-of-6-insights bug — measured by `ROVO_INSIGHTS_PARTIAL_SUCCESS` metric in prod, not by local benchmark).



```markdown
- [ ] Code change at <file>:<line> matches §3 spec
- [ ] **UX classification confirmed**: A / B / C
- [ ] **If C**: PM sign-off ticket linked (CTSC-XXX)
- [ ] **If C**: A/B test plan attached
- [ ] **Task file at `.ai_employee/projects/rovo_insights/tasks/<ID>-*.md` exists and is up-to-date** (NEW v4.5)
- [ ] **Task file §2 (UX Classification rationale) is filled in HONESTLY** (NEW v4.5)
- [ ] **PR description links to the task file** (NEW v4.5)
- [ ] Statsig flag <FLAG_NAME> wired correctly (if applicable)
- [ ] Unit test <TestClass.testName> added
- [ ] Test FAILS on master pre-fix (recorded in PR description AND task file §5)
- [ ] Test PASSES on PR HEAD post-fix (CI green)
- [ ] Cost/latency claim cited from telemetry (NOT marketing language) — recorded in task file §4
- [ ] §17.4 bug-vs-test mapping updated (NONE → ✅ <test name>)
- [ ] Metric from A1 emitted (if applicable)
- [ ] Risk + rollback steps documented in task file §6
- [ ] **Post-merge: return to task file §4 (Impact measured) and §7 (Lessons learned) within 7 days** (NEW v4.5)
- [ ] **Commit message follows §6.5 format** (WHY → WHAT → IMPACT → TESTS → ROLLBACK) (NEW v4.7)
- [ ] **PR description follows §6.5 format and matches commit message** (WHY → WHAT → IMPACT → TESTS → ROLLBACK) (NEW v4.7)
- [ ] **Test results show ✅ PASS markers explicitly** (per §6.5 test result format table) (NEW v4.7)
- [ ] **`./gradlew :<module>:ktlintFormat` run before push** (NEW v4.8 — see §6.6 incident retro) — CI fails on style violations even if tests pass
- [ ] **CI pipeline is GREEN on the latest commit** (NEW v4.8) — confirmed by checking Bitbucket pipeline status, not just local test pass
- [ ] **Reviewers added explicitly via PR `edit` API** (NEW v4.8) — CODEOWNERS auto-assignment is merge-time only, so PRs need manual reviewer add at create-time
```

### 6.2 22 mandatory tests carried forward (from v3.5 §17.5 + §17.5.1)

All test specifications from v3.5 §17.5 / §17.5.1 carry forward. Plus:
- **NEW T8** — `testNoUxRegressionOnDataFreshness` integration test that simulates "user opens app daily for 7 days" and asserts the data shown changes whenever source data changes.

### 6.4 NEW v4.6 — AI-Reviewer feedback discipline

**Source:** PR #29074 review experience — Rovo Dev posted 4 review comments; ALL 4 were correct (1 HIGH severity bug, 3 lower). 100% precision. Treating these as noise would have shipped a real bug (`coroutineScope` failure cascade in `prefetchPersonReferencesByAaid` — same bug-class as A5 itself).

**Rule:** Every PR MUST address all AI-Reviewer comments before merge. For each comment:

| Required action | Where it lives |
|---|---|
| 1. Triage (right / wrong / partial) — with evidence | PR thread reply |
| 2. If RIGHT → fix in same PR (don't defer) | Code change |
| 3. If WRONG → reply with concrete reason (not just "won't fix") | PR thread reply |
| 4. If PARTIAL → fix what's right, explain what's left + why | PR thread + code |
| 5. Capture in task file `## Work log` (chronological) | `.ai_employee/.../<ID>.md` |
| 6. Capture surprising lessons in task file `## Lessons learned` | `.ai_employee/.../<ID>.md` |

**Anti-pattern (forbidden):** "Resolved as not actionable" or "Will address in follow-up" without a Jira ticket link.

**Cite:** `.ai_employee/projects/rovo_insights/tasks/A6-A11-hydration-paired.md` §"Work log → 2026-05-03 (PR #29074 review feedback applied)" + `## Lessons learned` for the worked example.

---

### 6.3 New rule: cost claims must cite telemetry

| Forbidden | Required |
|---|---|
| "−85% LLM cost" | "−85% LLM cost per dashboard X over period Y, baseline Z" |
| "No quality risk" | "User-visible behavior change: NONE / SUBTLE / SERIOUS — see UX classification" |
| "Most users won't notice" | (forbidden phrase entirely) |

---

### 6.5 NEW v4.7 — Commit message + PR description format (from PR #29074, #29085 review feedback)

**Trigger:** During execution of items #1 and #2, three pieces of reviewer feedback emerged:
1. *"Why is the test result not obvious?"* — buried mid-message, no ✅/❌ markers, no PASS column
2. *"You should start the commit with overview (what + why), then impact, then tests"* — original order was TESTS → IMPACT → WHAT → WHY (i.e., conclusion-first), which forced reviewers to read backward to understand intent
3. *"Why am I not seeing updates in the PR overview?"* — only the commit message had been updated; the PR description on Bitbucket's "Overview" tab still had the old format. **The PR description and commit message are independent surfaces** and BOTH must follow the same mandatory order.

> 🚨 **The rule applies to BOTH surfaces equally:**
> - ✅ The commit message (what shows in `git log` / Bitbucket "Commits" tab)
> - ✅ The PR description (what shows on Bitbucket "Overview" tab — the page reviewers land on)
>
> A PR is NOT considered to follow the format until BOTH surfaces match the mandatory order below. Updating only one is non-compliant.

**Mandatory order for every PR commit message AND PR description:**

| # | Section | Header (use this exact emoji + label) | Content |
|---|---|---|---|
| 1 | **WHY** (motivation) | `📚 WHY (motivation)` | The problem being solved. What is broken? Why does it matter? Cite plan §. |
| 2 | **WHAT** (overview) | `🔧 WHAT (overview)` | High-level approach. UX classification (A/B/C). New metrics. New public API. |
| 3 | **IMPACT** (benchmarks/load) | `📊 IMPACT (empirical benchmark / measurable claims)` | Numbers. For perf: benchmark table OLD vs NEW. For non-perf (UX-improving): measurable claims with metric names. |
| 4 | **TESTS** (standard SOP) | `✅ TESTS (standard SOP — full Rovo Insights regression)` | Per-test ✅ PASS marker. Suite totals: prior tests + new tests = total/total. Build status. |
| 5 | **ROLLBACK** | `🔄 ROLLBACK` | git revert command + ETA + risk + trigger conditions. |

**Why this order is correct:**

| Aspect | Anti-pattern (TESTS-first) | Correct order (WHY-first) |
|---|---|---|
| Reviewer cognitive load | Read backward to find intent | Linear: motivation → solution → proof → safety |
| Skim path for PM/EM | Has to scroll past test details | First 60 lines tell the story |
| Skim path for engineer | Has to scroll past WHY (already known) | Engineer scrolls fast through WHY to WHAT/TESTS |
| Reads like | Postmortem | Explanation |

**Test result format (mandatory):**

| Format | Bad ❌ | Good ✅ |
|---|---|---|
| Test header | "Tests" | "✅ TESTS — ALL PASS (N/N)" with bold count |
| Per-test row | `Test \| What it asserts` | `Test \| Result \| What it proves` with `✅ **PASS**` in Result column |
| Suite summary | Buried in prose | Dedicated table: prior + new = total, all rows with ✅ |
| DoD checklist | `[x] Tests added` | `[x] N new tests; **✅ all N PASS**` and `[x] Full regression **✅ PASSES (X/X, time)**` |

**Worked examples in the wild:**
- A6+A11 PR #29074 commit `f5a3b9905c6` — perf-optimization with full benchmark table
- A5 PR #29085 commit `aaf2761665b` — UX-improvement (no benchmark, measurable claims instead)

**Box-drawing characters:** Use `══════` (Unicode U+2550) section dividers in commit messages — renders as visual rule in `git log` and Bitbucket commit view. Tables use `┌─┬─┐ │ │ └─┴─┘` (U+250C/2510/2514/2518/252C/2534/2502/2500/253C). Both are pure ASCII art (no markdown), so they render identically in terminal and web UIs.

**Skip exception:** when a PR is a 5-line typo fix or pure rename, the full 5-section format is over-engineered. Use 1-2 lines (`fix: typo in foo` + `## ROLLBACK: git revert`). Anything ≥1 file with logic change uses the full format.

**⚠️ CRITICAL — TWO surfaces to update (learned the hard way during PR #29074 review):**

| Surface | Where it shows | How to update |
|---|---|---|
| **Commit message** | `git log`, Bitbucket "Commits" tab, `git show <hash>` | `git commit --amend -m "..."` + `git push --force-with-lease` |
| **PR description** | Bitbucket "Overview" tab (the page reviewers land on) | Bitbucket API `bitbucketPullRequest action=edit` with `description` field, OR Bitbucket UI |

These are **independent** — updating one does NOT update the other. Bitbucket pre-fills the PR description with the commit message at PR creation time, but after that they diverge. **Both must be kept in sync** with the WHY → WHAT → IMPACT → TESTS → ROLLBACK order.

Workflow:
1. Write commit message in correct order, `git commit --amend`
2. `git push --force-with-lease`
3. **ALSO** update PR description via API/UI to match (or copy the commit message verbatim)
4. Verify both: `git log -1` for commit; refresh PR Overview tab for description

---


### 6.6 Pre-push checklist + CI-green policy (NEW v4.8 — from 2026-05-04 incident retro)

**Trigger:** After shipping the top-10 sprint (9 PRs), discovered ALL 9 PRs had RED CI builds despite tests passing locally. Two distinct issues:

1. **ktlint code style violations** — local `:test` task does NOT run ktlint. CI runs `lintRovoShard` and `lintTestsShard` which DO run ktlint. Detekt-flagged files: `RovoInsightsServiceImpl.kt`, `HydrationBenchmarkTest.kt`, etc.
2. **No reviewers assigned** — repo uses CODEOWNERS auto-assignment which only kicks in at merge-time, not at PR create-time. Result: PRs sat with 0 reviewers, no notifications, nobody knew to look.

**Policy (mandatory before declaring a PR "shipped"):**

```bash
# Step 1 — Run ktlintFormat to auto-fix style on every changed module BEFORE push
./gradlew :<module>:ktlintFormat
git diff  # review what got reformatted
git add -u && git commit --amend --no-edit  # or new commit if already pushed

# Step 2 — Verify ktlint clean
./gradlew :<module>:ktlintCheck

# Step 3 — After push, verify CI pipeline turned GREEN (not just running)
# Use Bitbucket pipeline list: targetBranch=<branch>, check latest result.name === "SUCCESSFUL"

# Step 4 — Add reviewers EXPLICITLY via API (don't rely on CODEOWNERS auto-assign)
# bitbucketPullRequest action=edit prId=<id> reviewers=[{uuid: "..."}]
```

**Lesson recorded as L7 in §7.0:** "PR shipped means CI green, NOT tests pass locally."

**Recovery cost (this incident):** ~30 min to investigate + auto-format + push 8 branches. Cheap, but would have been ~0 min if the pre-push checklist existed.


### 6.7 v4.9 amendment — detekt and ktlint are TWO different linters

**Trigger** (2026-05-04): User asked *"why do PRs still have build failures after my ktlint fix?"*

**Root cause discovery**:
- I ran `./gradlew ktlintFormat` and assumed it covered all linting.
- CI also runs `./gradlew detekt` (a SEPARATE linter for code quality, not formatting).
- detekt found 4 violations that ktlint cannot catch:
  - `SuspendFunSwallowedCancellation` (REAL semantic bug — `runCatching { deferred.await() }` swallows `CancellationException`, breaks cooperative cancellation)
  - `UnusedPrivateMember` (dead code)
  - `ForbiddenBlockCall` (`runBlocking` in test instead of `runTest`)
  - `RedundantQualifier` (`kotlin.math.abs` should be imported, not qualified inline)
- The first one was the SAME anti-pattern A5 fixes one level up — caught a genuine bug.

**Mandatory pre-push lint commands (updated)**:
```bash
# 1. Auto-format (ktlint)
./gradlew ktlintFormat

# 2. Code quality lint (detekt) — MUST be run with -Pdetekt.enabled=true
./gradlew :MODULE:detektMain :MODULE:detekt -Pdetekt.enabled=true

# 3. CI-equivalent shard tasks
./gradlew --build-cache -Pdetekt.enabled=true lintRovoShard detektAst
```

**Required DoD additions** (added to §6.1 below):
- ☐ `detekt -Pdetekt.enabled=true` passes locally for the changed module
- ☐ `lintRovoShard` AND `detektAst` BOTH pass locally before pushing

---



### 6.8 v4.10 amendment — distinguish "OUR" failures from "THEIRS" in CI

**Trigger** (2026-05-04, second hour of debugging): User asked *"now we have NEW failures in WidgetStoreIT and JiraAiSuggest..."*

**Root cause analysis**:
The CI at `convo-ai-test-integration` runs on EVERY PR (shared smoke-test). When an unrelated team breaks an integration test (e.g., ERS schema migration), it shows on YOUR PR's red ❌ even though YOUR code is fine.

**The 3 failure categories table**:

| Category | Example | Whose Fault | Action |
|---|---|---|---|
| **Code style (ktlint)** in YOUR file | `import-ordering` after Python script edit | YOUR fault | Run `ktlintFormat` |
| **Code quality (detekt)** in YOUR file | `SuspendFunSwallowedCancellation` | YOUR fault | Fix semantically |
| **Integration test in shared module** (`convo-ai-test-integration/widget/`, `aifeature/rest/`) | `WidgetStoreIT.containerType is encrypted` | NOT yours | Open #help-managed-builds ticket; mark "known infra issue" in PR description |

**How to triage in 30 seconds**:
```bash
# Check if YOUR PR touches the failing module
git diff origin/main...HEAD --name-only | grep <failing-module>
```
- If empty → "not yours" → escalate via Slack #help-managed-builds  
- If non-empty → debug locally, fix, push

**Why PR #29100 was green** (worked example):
PR #29100 contained only `.md` files. Pipeline `excludePaths: *paths-zero-risk-kotlin` skipped Lint/Test steps entirely. **Doc-only PRs cannot tell you if the code is broken.** Always validate with a code-touching PR.

**Required DoD addition** (added to §6.1):
- ☐ For any failing CI check, classified as YOURS or THEIRS using the table above
- ☐ "Theirs" classifications include link to #help-managed-builds ticket OR known-issue evidence

---


### 6.9 v4.11 amendment — End-to-end UX evaluation requirement (NEW v4.11 — formalises L8)

**Trigger** (2026-05-04): User noticed that PRs claiming perf improvements (e.g. `responsible-ai-api` PR #629 "−45.3% tokenization CPU" and `conversational-ai-platform` PRs #29101/#29097/#29103/#29099/#29114) shipped with **micro-benchmark numbers in the title and description** but **no end-to-end translation to user-perceived experience**. This is the exact failure mode that L8 (in §7.0) warned against — *"Component speedup ≠ user-perceived speedup"* — but L8 was a lesson, not an enforced rule.

**Quote (user, 2026-05-04)**: *"Be honest with our claim that it is local benchmarking, but also DO NOT undersell the end-to-end improvement for user."*

This amendment converts L8 from a lesson into an **enforced PR description requirement** (and a PR title naming requirement) for any PR claiming a perf or cost improvement.

#### 6.9.1 The two failure modes this rule prevents

| Failure mode | Symptom | Why bad |
|---|---|---|
| **Over-selling** (sugar-coating) | Title says "−58× wall time" but the user sees 0–7% improvement on the regen path and 0% on cache HIT | Erodes reviewer trust + future claims discounted |
| **Under-selling** (engineer-only framing) | Title says "−1.5 ms tokenization CPU" but at 83 RPS prod load this frees ~12.5% per-pod CPU headroom and meaningfully addresses a documented saturation problem | Hides genuine end-to-end wins behind a small-sounding component number; reviewers may close as "not worth the risk" |

**Both are dishonest in opposite directions.** The cure is the same: explicitly compute and present the **user-perceived** translation alongside the component number, with both honestly framed.

#### 6.9.2 PR title naming convention (mandatory for perf/cost claims)

| Bad ❌ | Good ✅ |
|---|---|
| `A8: cache salt memoize (95% Statsig fetch reduction)` | `A8: cache salt memoize (~95% upstream fetch reduction; ≤1ms per cache op end-to-end)` |
| `RAI-01: −45.3% tokenization CPU` | `RAI-01: −45.3% tokenization CPU (≈12.5% per-pod throughput headroom under 83 RPS prod load)` |
| `A6+A11: 58× wall time` | `A6+A11: 58× hydration speedup (3–7% user-perceived latency on cache MISS, 0% on cache HIT)` |

**Rule:** if the title contains a component-level percentage or speedup factor, it MUST also contain the user-perceived translation in the same parenthetical. If the user-perceived saving is small (< 5% or < 10ms wall-clock), the title MUST say so explicitly (e.g. "0% on cache HIT", "≤1ms per cache op").

#### 6.9.3 Required PR description subsection

Any PR that claims a latency, throughput, cost, or CPU improvement MUST include a section titled exactly **"End-to-End User Experience: honest framing"** placed immediately AFTER the `📊 IMPACT` section and BEFORE `✅ TESTS`. The section MUST contain ALL of the following sub-blocks (in order):

| # | Sub-block | What it shows |
|---|---|---|
| 1 | **What we measured vs. what we didn't** | A 4-column table: Aspect / Measured ✅ / NOT measured. Names the benchmark file and explicitly disclaims load-test/concurrency/I-O coverage. |
| 2 | **Where time goes in a real production request** | A table of production p50/p95/p99 from telemetry (Splunk, SignalFx, ERS, etc.) with source citation (`flask.micros.X.latency.hist.histogram`, etc.). If no production telemetry exists, state explicitly **"No production baseline available — claim is speculative until A1 ships."** and refuse to claim a wall-clock impact. |
| 3 | **Honest per-request translation** | A 4-column table: Percentile / Baseline / Estimated saving / % of latency. Use Amdahl's law math. Explicitly state whether a single user feels this on a single request. |
| 4 | **Where the real impact lives** (throughput / tail latency / cost) | The mechanism by which the small per-request saving aggregates into a meaningful end-to-end win. State the RPS, multiply, show the per-pod CPU/cost saving. Cite the team's documented saturation/cost bottleneck. |
| 5 | **Endpoint × request-type × cache-state matrix** (carryover from L8) | A table showing for each user scenario: (a) is this code in the user wait path? (b) what % of total request time is it? (c) what's the actual user-perceived saving in ms? |
| 6 | **What we are NOT claiming** | Bullet list of explicit anti-claims (e.g. "NOT a measured P95 reduction", "NOT a measured throughput uplift"). |
| 7 | **What we ARE claiming** | Bullet list, each item tagged with one of: **Measured** (with n=, source) / **Inferred** (with formula) / **Plausible** (with range, not point estimate) / **Speculative** (clearly flagged). |
| 8 | **Suggested follow-up validation** | The specific load test / A/B test / production observation that would convert "Plausible" → "Measured". |

**Worked example (canonical):** `responsible-ai-api` PR #629 description after 2026-05-04 enhancement (the prompt that triggered v4.11). Cite this PR in any rovo_insights PR that uses this template.

#### 6.9.4 Exceptions (when this rule does NOT apply)

| Exception | Why |
|---|---|
| **Pure UX-Improving items (Cat B)** that already use measurable user-perceived metrics (e.g. A5 `ROVO_INSIGHTS_PARTIAL_SUCCESS`) | The user-perceived metric IS the headline; no translation needed. Still include sub-blocks 6+7 (NOT/ARE claiming) for honesty. |
| **Reliability items** (e.g. A9 retry backoff, R-1B tool TIMEOUT surface) | Headline is reliability not perf. Still include sub-blocks 6+7. Skip sub-blocks 3+4+5. |
| **Pure refactors (Cat A) with NO perf claim** (e.g. RAI-08 helper extraction) | If the PR explicitly does not claim any wall-clock or throughput improvement, skip. The PR title MUST NOT contain any % or speedup number (or the rule applies). |
| **Typo / pure docs / pure rename** | Skip entirely. |

#### 6.9.5 DoD checklist additions (append to §6.1)

```markdown
- [ ] **PR title contains user-perceived translation** if it contains any % or speedup number (NEW v4.11 §6.9.2)
- [ ] **"End-to-End User Experience: honest framing" section present** in PR description (NEW v4.11 §6.9.3) — required for any perf/cost/latency/throughput claim
- [ ] **Section 1 (measured vs not measured) explicitly disclaims** the test-type used (micro-bench / unit-test / load-test) (NEW v4.11)
- [ ] **Section 2 (production baseline) cites telemetry source** OR explicitly states "no baseline available" (NEW v4.11)
- [ ] **Section 5 (endpoint × request-type × cache-state matrix) present** for any item with non-uniform impact across the user surface area (NEW v4.11 — formalises L8)
- [ ] **PR title MAY use the component number IFF the user-perceived translation is in the same parenthetical** (NEW v4.11 §6.9.2)
```

#### 6.9.6 Audit on existing PRs (2026-05-04)

Five `rovo_insights` PRs in flight at the time of this amendment:

| PR | Item | Title compliance | Description compliance | Action |
|---|---|---|---|---|
| #29101 | NEW telemetry .map() chain dedup | ⚠️ — claims "single-pass" but no user-perceived framing | ⚠️ — no e2e section | Add audit comment + e2e analysis comment |
| #29097 | A9 exponential backoff with jitter | ✅ — "opt-in" reliability framing, no perf claim in title | Skip 3+4+5 (reliability exception) | Add brief audit comment confirming compliance |
| #29103 | A8 cache salt memoize (~95% Statsig fetch reduction) | ❌ — "~95%" component number with no user-perceived translation | ⚠️ — no e2e section | **Edit title** + add full e2e analysis comment |
| #29099 | A10 partial JSON recovery (3-tier) | ✅ — UX-Improving, measurable claim is recovery rate not latency | Skip 3+4+5 (UX-improving exception) | Add brief audit comment confirming compliance |
| #29114 | R-1B surface tool TIMEOUT to LLM | ✅ — UX-Improving + reliability framing | Skip 3+4+5 (reliability + UX-improving) | Add brief audit comment confirming compliance |

Audit comments posted to all 5 PRs link back here.

## 7. The lessons (the only ones that matter)

### 7.0 Lessons from PR #29074 (A6+A11) execution (NEW v4.6)

These were learned IN-FLIGHT during the first executed top-10 item. They generalize:

| # | Lesson | Where it bit me | How to avoid |
|---|---|---|---|
| **1** | **Same bug-class can recur at different layers.** I built A5 to fix `coroutineScope`-cancels-siblings at the outer layer, then introduced the EXACT SAME bug at an inner layer (`prefetchPersonReferencesByAaid`). Caught only by AI-Reviewer. | A6+A11 inner parallel block | When introducing parallel coroutines, **default to `supervisorScope`** unless I can articulate WHY whole-batch cancellation is correct. Add to grep audit: `grep "coroutineScope.*async" src/main` |
| **2** | **`coerceAtLeast` after `%` is a bug-hider, not a bug-fix.** Kotlin's `%` keeps the sign of the dividend; `coerceAtLeast(0L)` silently masks negative jitter to 0, halving the effective range. | HydrationBenchmarkTest jitter generator | Always `kotlin.math.abs()` BEFORE `%` if non-negative is required. Add to grep audit: `grep "coerceAtLeast.*0.*%\\|%.*coerceAtLeast.*0"` |
| **3** | **AI-Reviewer (Rovo Dev) feedback is high-signal — 4/4 correct on PR #29074.** Treating it as noise would have shipped a real bug. | All 4 PR #29074 comments | New §6.4: every AI-Reviewer comment requires triage + response in PR thread + capture in task file `## Work log`. |
| **4** | **`asSequence().flatMap().associateBy()` is elegant but does N traversals.** For hot paths, single-pass `for` loop wins. | total_person_refs computation | Acknowledge style-vs-perf tradeoff explicitly. Hot-path = single-pass; cold-path = sequence chains OK. |
| **5** | **Local micro-benchmarks WORK and are CHEAP** (~30s end-to-end). The HydrationBenchmarkTest validated v3's "−5s p95" claim with 58.65× empirical evidence. Without it, the claim was just a number from v3. | A6+A11 impact validation | New rule (in §6.1 DoD): if item claims latency/throughput improvement, include a local benchmark — see worked example in `HydrationBenchmarkTest.kt`. |
| **L8** | **Component speedup ≠ user-perceived speedup.** Micro-benchmark of a subroutine in isolation (e.g. 58.65× on `prefetchPersonReferencesByAaid`) does NOT directly translate to user-visible latency improvement. The subroutine may run on only some endpoints, only some request types, or AFTER a much larger dominant cost (LLM call). Headlining the component number without the user-perceived translation is a form of sugar-coating — it sells a 58× win when the user actually sees 0% (cache HIT) to 3-7% (cache MISS regen path). | A6+A11 PR #29074 description "−58× wall time" claim — caught in review by user asking "how does this convert to user-perceived latency?" | **New rule (in §6.5)**: any PR description claiming a latency/throughput speedup MUST include a "Translation: COMPONENT speedup → USER-PERCEIVED latency" subsection that breaks impact down by **endpoint × request-type × cache-state** matrix. For each user scenario, state: (a) is this code in the user wait path? (b) what % of total request time is it? (c) what's the actual user-perceived saving in ms? Headline numbers in PR title/description MUST use the user-perceived number, not the component number. Worked example: PR #29074 description after user feedback. Cite: `.ai_employee/projects/rovo_insights/tasks/A6-A11-hydration-paired.md` §"Translation: COMPONENT speedup → USER-PERCEIVED latency". |
| **L9** | **Bundle-vs-split: only bundle when ONE feature flag controls both OR the intermediate state introduces a regression.** PR #29074 bundled A6 (parallelization) + A11 (dedup) into one PR. Reviewer @mdawson (correctly) flagged: *"I would have loved to see two pull requests, one for migrating sequential→parallel, and another to prevent duplicates."* My justification (single feature-flag `AIX_ROVO_INSIGHTS_USER_HYDRATION_ENABLED` controls both; parallel-without-dedup would *spike* AGG load) was valid but the lesson is broader: **default to small + flagged**; only bundle when there is an articulated safety reason. | A6+A11 paired in one PR | Source: PR #29074 review comment 2005484108. New rule (§6.1 DoD): if a PR bundles 2+ logically-distinct changes, the description MUST justify the bundling (single flag, ordering safety, or atomic rollback). Otherwise split. |
| **L10** | **Per-file consistency for imported types: prefer unqualified form once imported.** Mixing `import kotlin.coroutines.cancellation.CancellationException` at the top with a fully-qualified `kotlinx.coroutines.CancellationException` later in the same file LOOKS like two different types — even though on JVM they are the SAME (typealias). Reviewer asked "is this a different type?" — perfectly reasonable confusion. | RovoInsightsServiceImpl.kt line 528 | Rule: once imported, ALL references in the file use the unqualified form. Add to grep audit: `grep -E '(kotlinx?\|java)\.[a-z]+\.[A-Z]\w+' src/main` for fully-qualified type references in code that already imports them. Source: PR #29074 review comment 2005484151. |
| **L11** | **Function size + concern count is a reviewer signal — extract proactively.** `insightsToRovoInsightsResponse` was 138 lines and mixed (a) cross-type dedup collection, (b) parallel prefetch invocation, (c) metrics logging, (d) response construction. Reviewer @mdawson asked for extraction. | A6+A11 main response builder | Rule of thumb: if a function exceeds ~80 lines AND mixes 3+ logical concerns, extract DURING initial implementation, not in review iteration — saves a round-trip. Source: PR #29074 review comment 2005484309, addressed in commit 2638f679a1a (extracted `collectAndPrefetchPeople` helper, main fn now ~110 lines). |
| **L12** | **Search Bitbucket for in-flight related PRs BEFORE opening yours.** Opened PR #29110 (T0a, async pool bump) on 2026-05-04 11:32 UTC — discovered 4 hours later that Michal Huzevka had opened PR #29095 (`GAPF-1708 Tweak scaling rules`) at 07:07 UTC the same day, also touching `WebMvcConfiguration.kt` async pool sizing, with strictly broader and better scope (CPU-multiplier sizing, Tomcat threads, EC2 scaling, backed by 3 real prod incidents). Mine had to be DECLINED, wasting Michal's review time + risking a merge conflict. | T0a — superseded-by-#29095 | **Before opening any perf/scaling PR, run `bitbucketPullRequest action='list' state='OPEN'`** and grep for keywords matching the file you're about to edit (e.g. `pool`, `scaling`, `executor`, the file name itself). 30 seconds upfront saves 2+ hours downstream. Especially critical for "tuning"-class PRs where multiple engineers see the same Datadog/SignalFx graph and reach for the same fix. |



| Lesson | Why it matters |
|---|---|
| **L1 — UX-degrading optimization is anti-optimization** | A "−85% cost" win that makes users see week-old data is a NET LOSS, not a win. The cost saved is lost in user trust + churn. |
| **L2 — "No perceived regression" is a sugar-coating phrase** | Either you can prove no regression with an A/B test, or you can't. There is no middle ground. |
| **L3 — Marketing language has no place in engineering plans** | "−85%, no quality risk, the if-only-one-thing answer" sold an idea before it was scrutinized. v4.0 forbids unsupported claims. |
| **L4 — "Cached data was already old" ≠ "users won't see fresher data" ** | The cache mechanism's worst-case age (Redis TTL) is irrelevant to how often users see *newly-regenerated* data. Conflating them is dishonest. |
| **L5 — Telemetry must precede optimization** | A1 (observability) must ship before any other bundle. v3 had this listed as B9 (foundational) but allowed B0.1 to ship without it. |
| **L6 — Independent verification matters** | 4 parallel agents found 5 substantive issues in v3.x in one pass. Single-agent self-review missed them. Always cross-check before shipping. |

---

## 8. Action items right now (post-incident)

| # | Action | Status |
|---|---|---|
| 1 | Close PR #29064 | ✅ Done (title updated, comment posted, branch retained for audit trail) |
| 2 | Restore stashed pre-existing changes | ✅ Done |
| 3 | Update v3.x plan with v4 redirect at top | 🟡 In progress |
| 4 | Update doc rovo-insights.rst to remove the premature B0.1 ✅ entry | 🟡 In progress |
| 5 | Re-prioritize: ship A1 (observability) FIRST, not B0.1 | 🟡 Next item to start |
| 6 | Get PM input on whether ANY UX-Affecting (Category C) item is worth doing | 🟡 Pending |
| 7 | File 4 explicit Jira tickets for the 4 rejections (so the team knows NOT to revive these as-currently-scoped) | 🟡 Pending |

---

## 9. Critical thinking notes (for posterity)

1. **The B0.1 incident is the most important learning of this entire planning effort.** It confirms that even with a well-structured plan, a meticulous audit trail (v3.0 → v3.5), and full test coverage, **a flawed framing can produce a UX regression that "passes" all the gates we built.** The only effective gate was a user (Tony) asking the right question: "will user see latest insights?"

2. **The v3.x plan was internally consistent but externally wrong.** Every part of v3 supported every other part — the metrics, the tests, the DoD checklist, the audit trail. None of them caught the framing error. This is exactly why "DoD checklists pass on internally-consistent bad plans."

3. **The fix is not better DoD checklists. The fix is a UX-first principle baked into bundle classification.** Categories A/B/C make UX-degrading items impossible to ship without explicit sign-off. They're not in the same bucket as "ship freely" items.

4. **Agents are useful but require orchestration.** Three of four parallel agents in this audit produced strong, evidence-backed findings. The fourth (in an earlier round) confused CSM with Rovo Insights. **Always verify agent claims against source before integrating.**

5. **The planning system worked, eventually.** v1 → v2 → v3 → v3.1 → v3.2 → v3.3 → v3.4 → v3.5 → v4.0. Each iteration caught real bugs. The system that allowed B0.1 to almost ship is the same system that caught it before merge. **Iteration with adversarial review is the only working defense.**

6. **B0.1 was already prevented from causing harm.** PR was draft, never merged, no production impact. The system worked as a defense-in-depth: PR-as-draft → user review → catch → close. **This is the model going forward.** Never merge a UX-Affecting item without explicit user/PM sign-off.

---

## 10. References

- **Parallel agent audit results** (4 agents, 2026-05-03): see chat history for full per-bundle analysis
- **v3.5 plan (retired)**: `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/_plan/convo_ai_hack/_plan/rovo_insights/PLAN-INTEGRATED-v3.md`
- **Closed PR (audit trail)**: https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29064
- **Original code under audit**: `/Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/`
