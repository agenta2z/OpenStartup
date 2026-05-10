# User-Experience Impact Map

> **Purpose.** For every initiative in
> [`01-PRIORITISED-INITIATIVES.md`](01-PRIORITISED-INITIATIVES.md),
> trace the **causal chain from the technical change to what an end
> user actually perceives**, and classify it honestly.
>
> **Why this file exists.** A previous review caught that only 1 of 9
> P0/P1/P2 initiatives mentioned "user" at all. The rest were
> framework-internal (LoC, throughput, queue depth) without any link
> to user perception. **That is a real planning defect**, not just a
> documentation gap. This file fixes it by being honest about who
> sees what — including the uncomfortable truth that **0 of the 12
> initiatives have direct user-perceived impact today**.
>
> **Why "0" today is OK.** The Rovo Insights generation handler is a
> stub (verified). There is no live LLM-produced user content. So
> "user-perceived impact" is necessarily *future-conditional* — the
> question is not *"will users feel it now?"* but *"will users feel
> it the day the handler ships?"*.

---

## Section 1 — User touchpoints (what surfaces actually consume PAI)

This section grounds everything below. Verified via:

* `grep -rln "@RestController" --include="*.kt" src/main/kotlin/` → 5 controllers (2026-05-05).
* `cc/01-business-and-technical-goals` Part 3.2 (UX metric inventory).
* Touchpoints sub-agent investigation (4 surfaces with confirmed product host; 4 marked "unknown / planned").

### 1.1 — Confirmed (in the codebase today)

| Surface | Host product | PAI endpoint (file:line) | Sync vs async | User-perceived metric | Latency budget the user feels |
|---|---|---|---|---|---|
| **Conversation Starter Nudge** | Rovo Chat | `feature/nudge/api/rest/NudgeThrottleController.kt` (`/api/v1/nudge/throttle`) | **SYNC** in render path | Acceptance rate, dismiss rate | **p95 < 50 ms** (blocks chip render) |
| **Summarise Changes Nudge** | Confluence inline | Same endpoint above | **SYNC** in render path | Acceptance rate (GA Dec '25) | **p95 < 50 ms** |
| **Rovo Insights generation submit** | Confluence/Jira dashboard widget | `feature/rovoinsights/api/RovoInsightsController.kt` (`/api/v1/rovo-insights/generate\|status\|fetch`) | Submit-sync, **handler async** via SQS | **TTI (time-to-insight)** = end-to-end | Submit < 200 ms; **end-to-end TTI < 30 s** under burst |
| **Greeting (probe)** | n/a (smoke test) | `greeting/WebServiceController.kt` | Sync | n/a | n/a (not user-facing) |

### 1.2 — Planned / not-yet-coded (called out for honesty)

* **Rovo Button CTA ranking** — referenced in goal docs; **no PAI endpoint found in source today**. May live in another service.
* **Search-based proactive suggestions** — planned per goal docs; not in PAI today.
* **Home Threads / Tasks** — planned; not in PAI today.

### 1.3 — Critical truth about user-perceived metrics

**No PAI endpoint emits a histogram for any of the user-facing
endpoints in §1.1 today.** Only the global `http.server.requests`
exists (per
[`cc/11-metrics-catalog`](../../codebase_understanding/architecture/cross-cutting/11-metrics-catalog.rst) Part 1).
**Until P0-2 ships, no PR in this plan can quantitatively prove a
user-felt latency improvement.** That alone makes P0-2's UX value
"meta" — it's the prerequisite for proving any other initiative's
UX claim.

---

## Section 2 — UX-impact classification of each initiative

Categories (calibrated against the red-team agent's framework, then
**corrected** by my own verification):

* **A** — Direct user-perceived improvement (real user feels it)
* **B** — User-perceived improvement only on failure paths (silent
  unless something breaks; then matters)
* **C** — Enables a future direct user-perceived improvement
  (instrumentation, capacity, framework support)
* **D** — Engineer / operator UX only (developer / on-call benefit)
* **E** — Pure technical hygiene (no UX impact direct or indirect)

### 2.1 — Classification table (verified, honest)

| ID | Title | Category | Direct user UX delta? | Why this category (1-line) |
|---|---|---|---|---|
| P0-1 | SLO file + runbooks | **B** | Only when on-call needs to recover an outage | Silent on happy path; the day a real incident happens, MTTR drops from "hours of confused investigation" to "minutes of runbook execution" — the user perceives a **shorter outage**. |
| P0-2 | Per-endpoint p95 histograms | **C** | Zero today; *unblocks* every other UX claim | No user can perceive a histogram. But **without it, no future PR in this plan can prove its own UX delta**. The instrumentation is the prerequisite for closed-loop optimisation. |
| P0-3 | Wire/remove dead `MetricKey` | **E** | Zero | Pure dead-code cleanup. Justified only by "reviewer confusion" cost. No user impact direct or indirect. |
| P1-1 | Lift `LongRun.scaling.max: 2 → 6` | **C** | Zero today; **A on the day the real handler ships AND OKR-load arrives** | Today the handler is a stub: there is **no production load** to throttle. The day the real handler ships under burst load, this lever is what keeps Rovo Insights TTI < 30 s instead of stretching to minutes. **Conditional UX win**, not a "today" win. |
| P1-2 | Per-queue SQS concurrency | **C** | Same as P1-1 | Same conditionality as P1-1; a tactical multiplier on top of P1-1. |
| P1-3 | E2E synthetic canary | **B** | On failure paths only | Detects "request silently dies between web and worker" — a class of bug that produces "I clicked Generate and… nothing happened" UX. **Without this, the user has no recourse and the team has no signal**. |
| P1-4 | Idempotency-key contract | **B** (**A** for *some* users) | Failure-path; **but on cost-sensitive flows, the user perceives "I clicked once and was charged once"** | Today: stub handler → zero user impact. Day-one of real handler: SQS at-least-once delivery + double-AI-Gateway-call risk → **user might see two insights generated for one request** (confusing) **and team might double-charge** (cost). |
| P2-1 | Drop 4 `.blockingGet()` calls | **C** *(not A as the red-team agent claimed)* | Verified: **all 4 sites are in `stratus/` test/internal paths**; not on the live nudge/insights user paths today | Honest re-verification (2026-05-05): the 4 sites are 2× in `StratusTestController` (a test controller), 1× in `IntegrationServiceToolProvider` (only called from `StratusTestController`), 1× in `AIGatewayServiceImpl` (called from `StratusTestController`). **These do NOT run on the live user-facing nudge/insights endpoints today.** The change is structurally correct and would matter when AI-Gateway is wired into a real generation handler — but until then, **no current user perceives a difference**. Re-classified as **C**, not A. |
| P2-2 | MCP tool-discovery cache | **C** *(same correction)* | Same as P2-1 — `IntegrationServiceToolProvider` is only called from `StratusTestController` today | Same honest re-verification. The cache will matter when MCP is on a real generation hot-path. Today: zero user impact. |
| P2-3 | Detekt rule for `LaasLogger` | **D** | Zero direct, but **B-ish on the failure path** because better MDC = faster on-call diagnosis | Engineer UX primarily (cuts review-comment churn). A small failure-path UX benefit because logs without MDC slow post-incident analysis. |
| P3-1 | ADR-008 migration | **E** | Zero | Pure hygiene. |
| P3-2 | Controller test-coverage | **D** | Zero direct, but **B-ish** because regressions caught in CI never reach users | Developer-velocity UX primarily. Indirect user-benefit because future UX-regressing PRs are caught before deploy. |

### 2.2 — Aggregate (corrected)

| Category | Count | % | Notes |
|---|---|---|---|
| A — Direct user-perceived | **0** | 0 % | The honest truth: no initiative produces a user-perceivable change *today* because no user-facing PAI endpoint produces real LLM-generated content yet (handler is a stub). |
| B — Failure-path UX | 3 (P0-1, P1-3, P1-4) | 25 % | Real user benefit, only when something goes wrong. |
| C — Enables future user UX | 5 (P0-2, P1-1, P1-2, P2-1, P2-2) | 42 % | All gated on the real handler shipping. |
| D — Engineer/operator UX | 2 (P2-3, P3-2) | 17 % | Velocity / on-call benefit. |
| E — Pure hygiene | 2 (P0-3, P3-1) | 17 % | Zero UX impact. |

**Honest conclusion.** The red-team agent claimed 16.7 % Category A;
my verification shows it's **actually 0 %** (because the agent
incorrectly classified P2-1 and P2-2 as A without checking that
their call-sites are test controllers). The team is in a **pre-load,
pre-handler posture**. Every "user-perceived" win is *conditional* on
either a future incident (Category B) or future load arriving
(Category C).

### 2.3 — What would a "Category A" initiative look like?

The red-team agent suggested adding a **generation-status visibility
endpoint** so that users have something to see while a generation is
running. **I am classifying that as a strong candidate** but flagging
honestly: **it is a product-owned UX decision, not an engineering
optimisation.** Engineering can build the back-end (`/generations/{id}/status`
+ poll-or-push), but the team needs a product designer to specify the
front-end behaviour (modal? toast? inline progress? ETA?). Without
that spec, building the back-end risks shipping the wrong shape.

I therefore **propose** initiative **P1-5** (new) but with a
prerequisite of "Product designer signs off on the user surface
before engineering starts". See Section 4 below.

---

## Section 3 — Causal chains (technical → perceived)

For each initiative, the chain from "merged code" to "user feels it".
Where a chain is weak or speculative, I say so.

### P0-1 — SLO file + runbooks

```
Technical change         : Author continuous-verification.yml + 2 runbooks
   ↓
Component metric         : SLO breach signals visible in Tome
   ↓
System metric            : MTTD for queue back-up: ∞ → ≤30 min;
                           MTTR for first incident: measurable for the first time
   ↓
User-observable metric   : Outage duration (when one happens)
   ↓
User-perceived           : Shorter "Rovo Insights is unavailable" window
                           (e.g., 4 hours → 45 min) — user retries successfully sooner
```

* **Will users actually notice?** Only on failure paths (Category B).
* **Conditional on:** A real incident happens. (Pre-launch, this is
  a "free option".)
* **Counter-effect:** False-positive page wakes engineer at 3am,
  who then rolls back something that wasn't broken. Mitigation:
  conservative thresholds at first.

### P0-2 — Per-endpoint p95 histograms

```
Technical change         : Add 4 HistogramMetric values + wire into 5 controllers
   ↓
Component metric         : SignalFx series count: +4 per controller
   ↓
System metric            : per-endpoint p95 visible in dashboards
   ↓
User-observable metric   : NONE directly; this is a measurement instrument
   ↓
User-perceived           : Indirectly — every future PR in this plan can
                           now quote "p95 was X, is now Y" and prove the
                           UX claim is real
```

* **Will users actually notice?** No (Category C). But every
  *future* perf PR cites these histograms in its acceptance
  criteria — without them, "I made it faster" is hand-waving.
* **Conditional on:** Future PRs targeting these endpoints.
* **Counter-effect:** Cardinality explosion if a `tenant_id` tag
  is carelessly added (P0-2's own risk note covers this).

### P0-3 — Wire/remove dead `MetricKey` enum values

```
Technical change         : Delete 3 dead enum values; wire 1
   ↓
Component metric         : 4 fewer dead enum entries
   ↓
System metric            : Catalog accuracy rises from 57% LIVE → 100% LIVE
   ↓
User-observable metric   : NONE
   ↓
User-perceived           : NONE
```

* **Will users actually notice?** No (Category E). Justified
  *only* by reviewer-time cost, not user value.

### P1-1 — Lift `LongRun.scaling.max: 2 → 6`

```
Technical change         : YAML max: 2 → 6 + queue-depth scaling rule
   ↓
Component metric         : Cluster-max in-flight gens: 16 → 48
   ↓
System metric            : rovo-insights-generation-queue depth stays low
                           under 3× burst (instead of growing unboundedly)
   ↓
User-observable metric   : TTI (time-to-insight) — submit-to-render time
                           for a Rovo Insights nudge — stays < 30 s
                           even when many users in same org request
                           simultaneously
   ↓
User-perceived           : Insight 'feels available' under peak;
                           no "still loading…" state lasting minutes;
                           no DLQ-driven outright failures
```

* **Will users actually notice?** Yes — **but only when load is high
  AND the real handler is live**. Pre-handler: zero user impact.
  Post-handler at low load: zero user impact (max=2 is sufficient).
  Post-handler at OKR-scale load: significant UX win.
* **Conditional on:** (1) real handler ships; (2) OKR-scale load
  arrives; (3) AI-Gateway quota is *not* the bottleneck (else the
  cap moves and this lever is wasted).
* **Counter-effect:** Cost spikes (3× LongRun compute). Mitigation:
  the hard `max: 6` cap and queue-depth alarm bound the spend.

### P1-2 — Per-queue SQS concurrency

```
Technical change         : Per-listener concurrency override
   ↓
Component metric         : analytics queue: 2-8 → 1-4 (saves threads);
                           generation queue: 2-8 → 4-12 (more parallelism)
   ↓
System metric            : Cluster-max in-flight gens (with P1-1): 48 → 72
   ↓
User-observable metric   : Same as P1-1: TTI under burst
   ↓
User-perceived           : Same as P1-1, slightly stronger
```

* Same conditionality as P1-1.

### P1-3 — E2E synthetic canary

```
Technical change         : Submit a CanaryTask every 5 min; assert request_id
                           round-trip
   ↓
Component metric         : New CANARY_E2E_SUCCESS counter
   ↓
System metric            : MTTD for "silent message loss" / "context-replay
                           regression" from "never" → ≤ 15 min
   ↓
User-observable metric   : "I clicked Generate and… nothing happened"
                           failure rate
   ↓
User-perceived           : Confidence that "submit succeeded" actually
                           means "result will arrive"; failures get
                           investigated (and ideally fixed) before many
                           users hit them
```

* **Will users actually notice?** Only on failure paths
  (Category B). But the failure mode this prevents is one of the
  worst possible UX patterns: silent disappearance.
* **Conditional on:** Real handler arrives; canary path mirrors the
  real path.
* **Counter-effect:** Canary itself becomes noise. Mitigation:
  loose threshold (90 % over 15 min) at first.

### P1-4 — Idempotency-key contract

```
Technical change         : AsyncTaskHandler.idempotencyKey() opt-in;
                           dispatcher SETNX check
   ↓
Component metric         : ASYNC_TASK_IDEMPOTENT_SKIP rate (today: 0)
   ↓
System metric            : Eliminates duplicate handler invocations from
                           SQS at-least-once delivery
   ↓
User-observable metric   : "Why did my request generate two insights?"
                           confusion rate;
                           cost-side: AI-Gateway double-charge rate
   ↓
User-perceived           : "I clicked once, got one result" — the
                           default user expectation actually holds
```

* **Will users actually notice?** Mostly Category B (only when SQS
  redelivers). On rare events: a category-A "I see two of the same
  insight" experience that this prevents.
* **Conditional on:** Real handler ships AND opts in (P1-4 PR-2).
* **Counter-effect:** Redis dependency in dispatcher hot path —
  fail-open mitigates.

### P2-1 — Drop 4 `.blockingGet()` calls

```
Technical change         : Convert rxjava .blockingGet() → coroutine .await()
                           in 3 files
   ↓
Component metric         : Fewer blocked servlet threads on Stratus path
   ↓
System metric            : Web-tier thread-pool exhaustion under burst
                           moves out further
   ↓
User-observable metric   : NONE today (the 4 sites are in test/internal
                           paths, not on user-facing nudge/insight endpoints)
   ↓
User-perceived           : NONE today; the change is structurally correct
                           and would matter when AI-Gateway is wired into
                           a real user-facing generation handler
```

* **Will users actually notice?** No today. **Honest correction**
  to the red-team agent's claim of Category A.
* **Conditional on:** A real user-facing path adopts the converted
  callsites.
* **Counter-effect:** Different cancellation semantics — covered
  in the PR's acceptance criteria.

### P2-2 — MCP tool-discovery cache

```
Technical change         : Caffeine 5-min TTL cache around getTools(...)
   ↓
Component metric         : Integrations Service egress call rate: -90 %
                           (only on the path that actually uses it)
   ↓
System metric            : Lower load on Integrations Service (helps THEM,
                           not us)
   ↓
User-observable metric   : NONE on the live nudge/insights paths today
                           (the only caller is StratusTestController)
   ↓
User-perceived           : NONE today
```

* **Will users actually notice?** No today. Same honest correction
  as P2-1.
* **Conditional on:** A real user-facing path calls
  `IntegrationServiceToolProvider`.

### P2-3 — Detekt rule for `LaasLogger`

```
Technical change         : Custom detekt rule + first cleanup pass
   ↓
Component metric         : LaasLogger adoption: 85% → 100%
   ↓
System metric            : Every log line carries MDC (tenant_id, request_id)
   ↓
User-observable metric   : Post-incident diagnosis time (engineer-only)
   ↓
User-perceived           : Indirectly faster outage resolution
                           (Category B-ish)
```

* **Will users actually notice?** Mostly D (engineer UX); slight B
  on failure paths.
* **Counter-effect:** CI run-time rises slightly (~30 s for detekt).

### P3-1 — ADR-008 migration

```
Technical change         : Replace 1 raw @Value with typed bean
   ↓
... → ... → NONE for users
```

* Pure hygiene (Category E).

### P3-2 — Controller test-coverage

```
Technical change         : 5 SpringMvcTest files
   ↓
Component metric         : Test:source ratio 27.1% → ~31%
   ↓
System metric            : Future controller regressions caught in CI
   ↓
User-observable metric   : Production regression count (lower)
   ↓
User-perceived           : Indirectly — fewer post-deploy hotfixes that
                           change behaviour mid-session
```

* Mostly D (developer velocity) with B-ish flavor.

---

## Section 4 — What's MISSING from the plan (proposed additions)

The honest aggregate (0 % Category A) reveals the plan is
**necessary infrastructure but insufficient for user-perceived
improvement**. To close the gap, we propose **two new initiatives**:

### P1-5 (new, PROPOSED) — Generation-status visibility endpoint

* **Why now.** Today a user submits a generation request and… sees
  nothing. The async architecture (good for back-end resilience) is
  bad for user perception unless paired with a status surface. **The
  red-team agent flagged this as the single biggest user-experience
  gap in the plan.**
* **Proposed change.**
  * Add `GET /api/v1/rovo-insights/{generationId}/status` returning
    `{state, eta_seconds, attempt_count}`.
  * Persist task lifecycle in Redis (already provisioned per ADR-010);
    write `(submitted, queued, in_progress, completed, failed)`
    transitions from `MessageQueueConsumerMiddleware` and
    `RovoInsightsGenerationTaskHandler`.
  * Add `state` and `attempt_count` log-fields so on-call also wins.
* **Expected UX delta (Category A — *direct* user-perceived).**
  * Today: silent submit-then-wait → user reloads or gives up.
  * After: progress visible; user has confidence and can plan.
  * **Acceptance metric:** "Generation request accepted and never
    polled" rate. Should fall as users learn the endpoint exists.
* **PR series.** 3 PRs:
  1. PR-1: Add status persistence to the task lifecycle (back-end
     only; no endpoint yet).
  2. PR-2: Add `/status` endpoint + tests.
  3. PR-3: Wire metric for "polled-after-submit" rate.
* **Hard prerequisite.** Product designer signs off on the user
  surface (modal? polling cadence? ETA presentation?). **Without
  this, engineering risks shipping the wrong shape.**
* **Risk + counter-metric.** Polling-storm if cadence is too
  aggressive. Mitigation: include `Retry-After` header; emit
  `polling.rate` metric.

### P1-6 (new, PROPOSED) — Graceful-degradation messaging when AI Gateway 429s

* **Why now.** Today, an AI-Gateway 429 propagates as a generic
  5xx to the front-end. The user sees "something went wrong". A
  better experience: distinguish "we're busy, try again in 30s"
  (recoverable) from "your tenant lacks the entitlement"
  (non-recoverable).
* **Proposed change.**
  * In `AIGatewayServiceImpl`, distinguish 429 vs 4xx-other vs 5xx.
  * Map to a small Problem-Details JSON shape that includes
    `retry_after_seconds` and `code`.
  * Document the contract in OpenAPI so front-ends can render
    it consistently.
* **Expected UX delta (Category A).**
  * "Something went wrong" → "Servers are busy, retry in 30s" or
    "AI feature not enabled for your workspace".
  * **Acceptance metric:** retry-success rate after a 429 (should
    be > 80 %); confusion-driven support tickets (should fall).
* **PR series.** 2 PRs:
  1. PR-1: Add error-classification + Problem-Details mapping.
  2. PR-2: Add OpenAPI documentation + integration tests.
* **Hard prerequisite.** Front-end teams (Confluence inline,
  Rovo Chat) commit to honoring the new shape.

### Re-prioritization recommendation

If the team adopts P1-5 + P1-6, the new aggregate is:

| Category | Before | After (with P1-5, P1-6) |
|---|---|---|
| A — Direct user-perceived | 0 (0%) | **2 (14%)** |
| B — Failure-path UX | 3 (25%) | 3 (21%) |
| C — Enables future user UX | 5 (42%) | 5 (36%) |
| D — Engineer/operator UX | 2 (17%) | 2 (14%) |
| E — Pure hygiene | 2 (17%) | 2 (14%) |

Still not "user-experience first" (the team's stage is
infrastructure-first), but **honest** about where the user-perceived
deltas live.

---

## Section 5 — How to use this when authoring a PR

Every PR description should now answer **all five** of these
questions (extending the checklist in
[`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md)
"Cross-cutting PR hygiene"):

1. **What metric does this move?** (with name + current value)
2. **What's the expected delta?**
3. **What category of user-impact is this?** (A/B/C/D/E from §2.1)
4. **Under what condition does the user-perceived delta materialise?**
   (e.g., "only when real handler ships", "only on failure paths")
5. **What's the counter-metric to watch?**

Example (good PR description, P1-1 PR-1):

> Title: `[P1-1 / AIX-XXXX] Lift LongRun.scaling.max: 2 → 6`
>
> * **Metric:** `rovo-insights-generation-queue` `ApproximateNumberOfMessagesVisible`,
>   currently bounded by `max: 2 × concurrency 8 = 16` in-flight.
> * **Expected delta:** in-flight ceiling 16 → 48 concurrent gens.
> * **User-impact category:** **C** — enables future direct user UX
>   (TTI < 30 s under burst).
> * **Materialisation condition:** *Only* matters when (a) real
>   Rovo Insights handler is live and (b) burst traffic exceeds
>   16 concurrent gens. Until then this PR is a "free option".
> * **Counter-metric:** AI-Gateway egress 4xx rate (if quota
>   bottlenecks before LongRun does, this PR was wasted).

Example (bad PR description — to flag in review):

> "Improves throughput by 3x."

— missing user-impact category, missing materialisation condition,
missing counter-metric. **Reviewer should reject** until §2.1
classification is provided.

---

## Section 6 — Open questions for the team

These are questions this analysis surfaced that **a human (not an
AI) needs to answer**:

1. Is there a product spec for "what should users see while their
   Rovo Insights generation is running"? **Without it, P1-5 is
   premature.**
2. Are the Conversation Starter Nudge and Summarise Changes Nudge
   really both calling `/api/v1/nudge/throttle`, or is one of them
   bypassing PAI? (Sub-agent couldn't fully verify.)
3. What's the actual current p95 of the nudge-throttle endpoint?
   (Need P0-2 to answer.)
4. Does the front-end gracefully degrade when the nudge-throttle
   endpoint 5xx's, or does the user see a broken UI? (Need to
   ask Confluence + Rovo Chat front-end teams.)
5. Is there an existing Problem-Details / RFC-7807 contract in
   Atlassian's mesh that PAI should adopt, or do we invent our own?
   (P1-6 prerequisite.)

---

## Cross-references

* [`00-INDEX.md`](00-INDEX.md) — priority dashboard.
* [`01-PRIORITISED-INITIATIVES.md`](01-PRIORITISED-INITIATIVES.md) — full initiative detail (will be patched to add UX category).
* [`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md) — PR-authoring checklist (will be extended with the 5 questions above).
* [`03-RISKS-AND-NON-GOALS.md`](03-RISKS-AND-NON-GOALS.md) — explicit non-goals with historical context.
* `../../codebase_understanding/architecture/cross-cutting/01-business-and-technical-goals.rst` Part 3.2 — the source of UX-metric truth.
* `../../codebase_understanding/architecture/cross-cutting/11-metrics-catalog.rst` — current metric inventory (the prerequisite for proving any UX claim).
