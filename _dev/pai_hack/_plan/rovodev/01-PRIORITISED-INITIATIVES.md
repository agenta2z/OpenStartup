# Prioritised Initiatives

> 12 initiatives, ranked by **OKR contribution** (not by speculative
> $-savings). Each entry follows a fixed schema:
>
> * **Why now** — the OKR-grounded rationale.
> * **Current state** — verified file:line evidence.
> * **Proposed change** — the smallest defensible change.
> * **Expected metric delta** — calibrated; medium-confidence.
> * **PR series** — how to ship without a big-bang PR.
> * **Risk + counter-metric** — what gets worse, what to watch.
> * **Historical context** — was this tried before? Why is it safe now?
> * **Cross-references** — chapters in
>   [`../../codebase_understanding/`](../../codebase_understanding).

---

## P0 initiatives (OKR-blocking)

These are not improvements; they are the **preconditions** for safe
ramp. Without them, hitting 1.5M is either invisible or unsafe.

---

### P0-1 — Wire SLO file + minimum runbooks for the 6 alarms

**Why now.** Every alarm in `service-descriptor.sd.yml` is
`Priority: Low` with `Runbook: TBD`. When the real Rovo Insights
handler ships and load arrives, **no alarm wakes anyone, and no
runbook exists**. This is the single biggest ramp-blocker.

**Current state.**

* No `continuous-verification.yml` at the repo root (verified by
  directory listing 2026-05-05).
* 6 alarms in `service-descriptor.sd.yml` (lines ~37-191), each
  `Priority: Low`, each with `Runbook: TBD`.
* See [`cc/11-metrics-catalog`](../../codebase_understanding/architecture/cross-cutting/11-metrics-catalog.rst) Part 4 for the full catalog.

**Proposed change.**

1. Author a **starter** `continuous-verification.yml` with **two**
   conservative SLOs (don't try to be perfect — be present):
   * Web availability ≥ 99.5 % (non-5xx) on `http.server.requests`
     (will tighten when production load arrives).
   * `rovo-insights-generation-queue` `ApproximateAgeOfOldestMessage`
     p99 < 600 s (matches `VisibilityTimeout`).
2. Author **two minimum runbooks** in Confluence (`go/proactive-ai-platform-runbook`):
   * "Rovo Insights generation queue is backing up" — covers DLQ
     drain procedure + capacity scaling.
   * "Web service 5xx spike" — covers Splunk pivot + AI-Gateway
     egress check.
3. Promote `RovoInsightsGenerationDLQueueAlertHigh` to
   `Priority: Medium` (the YAML has an inline TODO to do exactly
   this).

**Expected metric delta.**

* Mean Time To Detect (MTTD) for queue-back-up: from "never (no
  alarm escalation)" → ≤ 30 min.
* MTTR for first incident: starts measurable; baselines for
  improvement.
* SLO breaches now visible in Tome dashboards.

**PR series.** See **PR-SEQ-P0-1** in
[`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md). 3 PRs:

1. PR-1: Author `continuous-verification.yml` (minimum 2 SLOs).
2. PR-2: Author runbook URLs + update alarm `Description:` to point
   at them.
3. PR-3: Promote one DLQ alarm to `Priority: Medium`.

**Risk + counter-metric.**

* Risk: false-positive page if the SLO threshold is too tight.
  Mitigation: start with conservative thresholds (99.5 %, not
  99.9 %); tighten only after a month of zero false-positive
  history.
* Counter-metric: track pager-fire count weekly for the first
  month; if > 0 false positives, loosen the threshold rather than
  ignore the alarm.

**Historical context.** Per ADR-012 in
[`cc/14-architectural-decisions`](../../codebase_understanding/architecture/cross-cutting/14-architectural-decisions.rst),
the team **deliberately** kept everything `Priority: Low` because
PAI was pre-load. That was correct then; it is no longer correct
the day the real handler ships.

**Cross-references.**

* `cc/11-metrics-catalog` Parts 4-5
* `cc/14-architectural-decisions` ADR-012, ADR-013
* `cc/12-optimization-playbook` Levers 4.3, 5.1, 5.2

---

### P0-2 — Per-endpoint p95 histograms (5 controllers)

**Why now.** Today only the global `http.server.requests` histogram
is registered (`application.yml` lines ~17-19). To meet
endpoint-level SLOs (e.g., "nudge throttle p95 < 50 ms" per
`cc/01-business-and-technical-goals` Part 3.2), each user-facing
endpoint needs its own histogram. Without it, **no PR can
demonstrate p95 impact** (see `cc/12-optimization-playbook` Part 8
PR checklist) and on-call can't see per-endpoint regressions.

**Current state.**

* 5 controllers in source (verified 2026-05-05; see
  [`SYMBOL_INDEX.md`](../../codebase_understanding/SYMBOL_INDEX.md) §1):
  `WebServiceController`, `RovoInsightsController`,
  `RovoInsightsTestController`, `NudgeThrottleController`,
  `StratusTestController`.
* Only one `MetricKey` LIVE today is `PROACTIVE_TEST_COUNT` (canary).
* `HistogramMetric.PROACTIVE_TEST_LATENCY` is WIRED but has no
  emit site.

**Proposed change.**

1. Add 4 new entries to `HistogramMetric`:
   * `ROVO_INSIGHTS_GENERATE_LATENCY` ("rovo-insights.generate.latency")
   * `NUDGE_THROTTLE_DECISION_LATENCY` ("nudge.throttle.decision.latency")
   * `STRATUS_TEST_LATENCY` ("stratus.test.latency")
   * `MCP_TOOL_DISCOVERY_LATENCY` ("mcp.tool-discovery.latency")
2. Wire `metricsService.timeAndCountResult(...)` into each
   controller's main path.
3. Add the new histograms to `application.yml` `histograms:` block
   with the standard `PROACTIVE_HISTOGRAM_BUCKETS` ranges.
4. **In the same PR**, register the `PROACTIVE_TEST_LATENCY` as
   well — it's been WIRED-not-LIVE since the framework was added.

**Expected metric delta.**

* SignalFx dashboards gain per-endpoint p95/p99 within 1 deploy.
* Future PRs can quote exact deltas in their descriptions.
* No change to user-perceived behaviour.

**PR series.** See **PR-SEQ-P0-2**. 2 PRs:

1. PR-1: Add `HistogramMetric` enum entries + wire into
   `MetricsService` + `application.yml` registration. (Tests
   verify metric names.)
2. PR-2: Wire emit calls into the 5 controllers. (Tests verify
   counter increments per call.)

**Risk + counter-metric.**

* Risk: histogram cardinality explosion if a tag like `tenant_id`
  is added carelessly. Mitigation: use only the 4 common tags from
  `application.yml` (`environment`, `environment_type`, `region`,
  `deployment_id`); leave `tenant_id` to log-MDC, not metric tags.
* Counter-metric: SignalFx datapoint-rate per series before/after.

**Historical context.** None — this is new instrumentation, not a
removal.

**Cross-references.**

* `cc/11-metrics-catalog` Parts 1-3
* `mod/platform/service-metric`
* `SYMBOL_INDEX.md` §1, §9

---

### P0-3 — Wire (or remove) the 4 dead `MetricKey` enum values

**Why now.** Per `cc/11-metrics-catalog` Part 1: 4 of the 7 enum
values (`TENANT_CONTEXT_BUILD_SUCCESS/ERROR`,
`PROACTIVE_TEST_LATENCY`, plus `ResultMetricBase.ERS_CREATE`) are
WIRED but never emitted. Dead code confuses reviewers and inflates
the apparent metric surface. Either wire them or delete them.

**Current state.**

* Enum values exist in `service/metric/MetricKey.kt` but
  `grep -rn "TENANT_CONTEXT_BUILD"` etc. in `src/main/kotlin/`
  returns 0 emit sites (verified 2026-05-05).

**Proposed change.**

1. **Delete** `TENANT_CONTEXT_BUILD_SUCCESS` and
   `TENANT_CONTEXT_BUILD_ERROR` if no caller is planned in the next
   90 days. (Pragmatic: they're easy to re-add.)
2. **Wire** `PROACTIVE_TEST_LATENCY` as part of P0-2 above
   (consolidates with the histogram work).
3. **Delete** `ResultMetricBase.ERS_CREATE` if no caller is
   planned. (Per the "Open question" section of
   `cc/11-metrics-catalog`, this is a `ResultMetricBase` orphan.)

**Expected metric delta.** 4 fewer dead enum values; `MetricKey`
catalog accuracy from "57 % live" → "100 % live".

**PR series.** **PR-SEQ-P0-3.** 1 PR (consolidates with P0-2 PR-1
naturally).

**Risk + counter-metric.**

* Risk: a future PR re-introduces the value with a different name.
  Mitigation: comment in the PR description naming the planned
  feature; reviewer can flag.
* Counter-metric: none directly.

**Historical context.** The 4 values were added in PR #97 (async
task framework, ``393a5f8``) as scaffolding. They remained dead
through 100+ subsequent PRs. The team-by-convention decision was
"leave for future use"; the cost is the reader confusion noted in
multiple agent investigations during this docs effort.

---

## P1 initiatives (OKR-enabling)

---

### P1-1 — Lift `LongRun.scaling.max` from 2 → 6 with queue-depth scaling

**Why now.** `LongRun.scaling.max: 2` is a **hard ceiling**
hardcoded in `service-descriptor.sd.yml` (verified 2026-05-05;
inline comment: *"Kept minimal (1-2 nodes) for now since PAI has
no production workload yet"*). At Stage-2 ramp, this is the
**single biggest cap** on Rovo Insights generation throughput.

**Current state.** `service-descriptor.sd.yml` lines ~218-224:
```yaml
- name: LongRun
  scaling:
    min: 1
    max: 2
    instance:
      - t3a.medium
```

No autoscaling rules. SQS concurrency is `2-8` per JVM, so total
in-flight = `2 nodes × 8 consumers = 16 max concurrent generations`.

**Proposed change.**

1. Lift `max: 2` → `max: 6` (3× headroom, leaves cost-cap room).
2. Add a `Scale` rule on `ApproximateNumberOfMessagesVisible` for
   `rovo-insights-generation-queue` (scale up when > 50, scale
   down when < 5).
3. Add a Tome alarm on `ApproximateNumberOfMessagesVisible > 500`
   so on-call sees runaway depth even if scaling can't keep up.

**Expected metric delta.**

* Throughput ceiling: `16 → 48` concurrent generations per cluster
  (3×); enough for ~50K gens/day at 30-second average.
* Cost: max 3× LongRun compute when at peak (~$Y/month additional;
  ops should sign off on budget before merge).
* Counter-metric: AI-Gateway quota usage; if it caps before
  LongRun does, the bottleneck moves and this lever was wasted.

**PR series.** **PR-SEQ-P1-1.** 1 PR (config-only, but reviewed by
ops).

**Risk + counter-metric.**

* Risk: AI-Gateway 429s under burst. Mitigation: coordinate with
  AI Gateway team on quota.
* Risk: LongRun cost spikes if a runaway producer floods the queue.
  Mitigation: the `>500` alarm + max-cap means cost is bounded.
* Counter-metric: `STREAMHUB_EVENT_ERROR` rate (proxies for
  downstream pressure); AI-Gateway egress 4xx rate.

**Historical context.** The `max: 2` was set deliberately
**because** the handler is a stub (per the inline YAML comment).
The right time to lift this is **just before** the real handler
ships, not before. If shipping the handler is delayed, **defer
this PR** rather than over-provisioning.

**Cross-references.**

* `cc/11-metrics-catalog` Part 6
* `cc/12-optimization-playbook` Lever 3.2
* ADR-001 + ADR-011 in `cc/14-architectural-decisions`

---

### P1-2 — Per-queue SQS consumer concurrency

**Why now.** `application.yml` `concurrency: "2-8"` is applied
**uniformly** to every JMS listener container (= one per SQS queue
per JVM). The two queues have very different shapes:

* `analytics-events` (StreamHub UI events) — high message rate,
  cheap per-message work, on `SHWorkers`. `2-8` is over-provisioned.
* `rovo-insights-generation-queue` — low message rate, expensive
  per-message work, on `LongRun`. `2-8` may be the right *floor*
  but the upper bound caps Stage-2 throughput when paired with
  P1-1.

**Current state.** Single global `concurrency: "2-8"` in
`application.yml` §`atlassian.sqs.properties.concurrency`.

**Proposed change.** Use Spring property overrides per listener
container (the `atlassian.sqs.properties` property supports
per-listener override via `containerFactory` naming). Concretely:

* `analytics-events` → `1-4` (sufficient for current StreamHub
  traffic; saves a JVM thread per worker).
* `rovo-insights-generation-queue` → `4-12` (matches Stage-2
  expected load with P1-1's 6-node ceiling).

**Expected metric delta.**

* Maximum concurrent generations: `48 → 72` (P1-1 + P1-2
  together).
* SHWorkers JVM heap: small headroom recovered.
* Counter-metric: `streamhub.event.processed` rate to confirm no
  StreamHub backpressure.

**PR series.** **PR-SEQ-P1-2.** 1 PR (config-only).

**Risk + counter-metric.**

* Risk: misconfigured property name silently leaves global default
  in place. Mitigation: add a startup-log check that asserts the
  per-container config is loaded.
* Counter-metric: `ApproximateNumberOfMessagesVisible` for both
  queues.

**Historical context.** The uniform `2-8` was chosen at framework
introduction (PR #97). Per-queue tuning was deferred under
"pre-load posture".

---

### P1-3 — End-to-end synthetic canary (request-id assertion)

**Why now.** Per ADR-003 in `cc/14-architectural-decisions`,
`request_id` propagates via SQS message attributes from the
WebServer to the LongRun worker. **There is no test that asserts
this works in production.** A silent failure in
`MessageQueueConsumerMiddleware`'s context replay would mean
"requests succeed at the producer side, never produce a final
log line, never raise an alarm".

**Current state.** No e2e canary. The `WebServiceController`
`/greeting` endpoint exists but is sync-only.

**Proposed change.**

1. Add a new `AsyncTask` subclass `CanaryTask`.
2. Add a Spring `@Scheduled` job (every 5 min, on WebServer pool)
   that submits a `CanaryTask` via `AsyncTaskService`.
3. The handler (on LongRun) increments
   `metricsService.count(CANARY_E2E_SUCCESS, ...)` with the
   producer's `request_id` as a tag, then asserts the
   `request_id` matches what was sent.
4. Add a Tome alarm on `CANARY_E2E_SUCCESS` rate falling below 90 %
   over 15 min.

**Expected metric delta.**

* Detection of "silent message loss" or "context-replay regression"
  within ≤ 15 min (currently: never).
* Adds ~288 SQS messages/day at production scale (negligible cost).

**PR series.** **PR-SEQ-P1-3.** 2 PRs:

1. PR-1: Add `CanaryTask` + handler + `@Scheduled` job +
   metric (no alarm yet — bake-in period).
2. PR-2: Add Tome alarm + runbook entry (after 7 days of clean
   metric data).

**Risk + counter-metric.**

* Risk: canary itself becomes a noise source. Mitigation: alarm
  threshold loose (90 %) at first; tighten after a month.
* Counter-metric: SQS message count for
  `rovo-insights-generation-queue` (canary doesn't need its own
  queue; can share since payload is tiny).

**Historical context.** None. This is new tooling.

---

### P1-4 — Idempotency keys on `AsyncTaskHandler`

**Why now.** Per ADR-002 in `cc/14-architectural-decisions`, SQS
delivers at-least-once. Per `cc/12-optimization-playbook`
Lever 4.2, idempotency is "enforced by convention, not by code".
**The day the real Rovo Insights handler writes to Redis or AI
Gateway, a duplicate delivery causes a duplicate write or a
duplicate AI-Gateway call (which double-charges).** Build the
convention into the framework before that day.

**Current state.** `AsyncTaskHandler<T>` interface defined in
`task/AsyncTaskHandler.kt`; **today there is exactly one
production implementer** (`RovoInsightsGenerationTaskHandler`,
verified 2026-05-05 by `grep -rln "AsyncTaskHandler<"
src/main/kotlin/` returning 4 files: the interface, the dispatcher,
the registry, and the one impl). The impl is currently a stub.
The framework support is the right place to add the contract —
*before* the second implementer arrives.

**Proposed change.**

1. Add an **optional** abstract method to `AsyncTaskHandler<T>`:
   `fun idempotencyKey(task: T): String?` (default `null` =
   opt-in).
2. In `AsyncTaskDispatcher.dispatch(...)`, if `idempotencyKey != null`,
   check Redis SETNX with TTL = task's expected max duration; skip
   handler invocation if key already exists.
3. Document the convention in `mod/platform/task.rst` and add a
   detekt rule (or PR-template line) prompting authors to consider it.

**Expected metric delta.**

* Eliminates the *category* of "double generation / double charge"
  bugs at zero cost when the real handler ships.
* New metric `ASYNC_TASK_IDEMPOTENT_SKIP` to track skip rate.

**PR series.** **PR-SEQ-P1-4.** 2 PRs:

1. PR-1: Add interface method (default `null`); add Redis check in
   dispatcher; add metric. **No handler changes** — purely
   opt-in.
2. PR-2: When the real Rovo Insights handler ships, override
   `idempotencyKey()` returning the deterministic gen-request hash.

**Risk + counter-metric.**

* Risk: Redis dependency in dispatcher hot path. Mitigation: only
  invoked when `idempotencyKey != null`; fail-open on Redis errors
  (treat as "not seen before") with a metric for that fail mode.
* Counter-metric: `ASYNC_TASK_IDEMPOTENT_SKIP` rate (should be
  near-zero; non-zero = duplicate delivery happening).

**Historical context.** Redis was provisioned in PR #96 expressly
for "caching" that hasn't been wired yet (per ADR-010 — "Real
generation handler is still a stub"). This is a sensible **first
use** of the cache, on a contract that doesn't depend on the
generation algorithm.

---

## P2 initiatives (OKR-accelerating)

---

### P2-1 — Convert remaining `.blockingGet()` calls to suspending equivalents

**Why now.** Verified 4 remaining `.blockingGet()` sites in
`src/main/kotlin/`:

* `stratus/internal/AIGatewayServiceImpl.kt:73`
* `stratus/StratusTestController.kt:78`, `:158`
* `stratus/IntegrationServiceToolProvider.kt:51`

Each blocks a thread for the duration of an external call. On the
Stratus / AI-Gateway hot path this caps web-tier throughput
unnecessarily.

**Current state.** All 4 sites use rxjava3's `.blockingGet()`
against `Single`/`Flowable` returned by adk / mlp clients.

**Proposed change.** Use kotlinx-coroutines-rx3's
`.await()` / `.asFlow().toList()` extensions to convert each
blocking site into a coroutine suspend point. The callers (Spring
controllers) already run on the MVC async executor; they just need
to be marked `suspend`.

**Expected metric delta.**

* Frees ~4 servlet threads per concurrent request through the
  Stratus path.
* p95 latency on the Stratus test endpoint: not directly improved
  (the underlying call is still the same duration), but at high
  RPS the executor exhausts later.
* **Honest caveat:** this is a "structural" improvement; the
  measurable impact only appears under load.

**PR series.** **PR-SEQ-P2-1.** 1 PR (atomic — all 4 sites or
none, to keep the conversion consistent).

**Risk + counter-metric.**

* Risk: error-handling semantics differ between rx3 and coroutines.
  Mitigation: tests for both happy path and error path before
  merge.
* Counter-metric: `ProactiveAIAsyncExc-` executor active-thread
  count.

**Historical context.** No previous attempt; the rxjava style is
historical baggage from the adk/mlp client APIs.

---

### P2-2 — MCP tool-discovery cache

**Why now.** `IntegrationServiceToolProvider:51` calls
`toolset.getTools(null).toList().blockingGet()` **per request**.
Tool definitions change rarely (release-cadence of the
Integrations Service team). A 5-minute in-process cache eliminates
~hundreds of redundant calls per minute at OKR scale.

**Current state.** No cache. Verified 2026-05-05 by reading the
file.

**Proposed change.** Wrap `getTools(...)` in a Caffeine cache
(already a transitive dep of Spring Boot 7.10 — verify in
`build.gradle.kts`). 5-min TTL, refresh-after-write so reads never
block on stale-key refresh.

**Expected metric delta.**

* `integrations-service` egress call rate: -90 % at OKR scale
  (assuming hundreds of generations per minute, each currently
  triggers a discovery call).
* Adds ~few KB heap per cluster.
* Counter-metric: cache-hit ratio metric; tool-list staleness
  alarm (if Integrations Service changes a tool, expect 5-min
  delay before PAI sees it).

**PR series.** **PR-SEQ-P2-2.** 1 PR.

**Risk + counter-metric.**

* Risk: stale tool list during an Integrations Service tool
  change. Mitigation: 5-min TTL cap; add an admin endpoint to
  invalidate.
* Counter-metric: `integrations-service.tool-discovery.calls`
  rate.

**Historical context.** None — fresh optimisation.

---

### P2-3 — Detekt rule banning direct `LoggerFactory.getLogger`

**Why now.** Per ADR-009 in `cc/14-architectural-decisions`,
`LaasLoggerFactory` is mandatory but enforced **by reviewer
vigilance**. Code-quality agent measured ~85 % adoption — meaning
~15 % of loggers don't carry MDC enrichment (and on-call relies
on it).

**Current state.** No detekt rule; convention-only.

**Proposed change.** Add a custom detekt rule under a new
`detekt-rules-pai/` module:
* Forbid `org.slf4j.LoggerFactory.getLogger(...)` outside the
  `logging/` package.
* Warn on `private val log = ...` not constructed via
  `LaasLoggerFactory`.

Wire into `bitbucket-pipelines.yml` as a non-blocking warning
first (one sprint), then promote to blocking.

**Expected metric delta.**

* LaasLogger adoption: 85 % → 100 % within one sprint.
* Reviewer-comment count for "use LaasLogger" → 0.

**PR series.** **PR-SEQ-P2-3.** 1 PR (rule + first cleanup pass
combined; one new file ≤ 100 LoC).

**Risk + counter-metric.**

* Risk: detekt false-positives in test code. Mitigation: scope
  rule to `src/main/kotlin/`.
* Counter-metric: detekt `failedRules` count.

**Historical context.** Convention has been recurrent reviewer
comment; promoting it to a rule is a long-overdue maturation.

---

## P3 initiatives (Hygiene)

---

### P3-1 — Complete ADR-008 migration

**Why now.** Per
[`cc/14-architectural-decisions`](../../codebase_understanding/architecture/cross-cutting/14-architectural-decisions.rst)
ADR-007 (status: temporary) + ADR-008 (status: PROPOSED), the
typed `MicrosEnvironmentType` bean has zero consumers; the only
user (`FeatureFlagContextServiceImpl`) reads
`@Value("\${MICROS_ENV:}")` as a raw string. A trivial migration
closes the open question.

**Current state.** 1 raw-string consumer, 0 typed-bean consumers.

**Proposed change.** Replace the `@Value` with constructor-inject
of `MicrosEnvironmentType`. ~5-line change.

**Expected metric delta.** None observable; ADR-008 closed; 1 fewer
"how do I read environment?" stack-overflow question for new
contributors.

**PR series.** **PR-SEQ-P3-1.** 1 PR. Best first-PR for new contributor.

**Risk.** None of substance.

---

### P3-2 — Controller test-coverage lift (5 controllers)

**Why now.** Per code-quality agent verification, 0/5 controllers
have unit tests. Per `cc/15-velocity-and-debt` Part 6, the test:
source ratio is 27.1 %. Lifting controllers raises confidence in
the most user-facing surface.

**Current state.** Integration tests exist (PR #101), but no
controller-level unit tests.

**Proposed change.** One PR per controller; each adds a
SpringMvcTest using `MockMvc` plus mocks for downstream services.
Target: 1 happy-path test + 1 error-path test per endpoint.

**Expected metric delta.**

* Test files: 32 → 37.
* Test:source ratio: 27.1 % → ~31 %.
* Catches future controller regressions in CI.

**PR series.** **PR-SEQ-P3-2.** 5 small PRs (one per controller),
each ≤ 100 LoC, mergeable in any order.

**Risk.** None of substance; controller tests are well-trodden.

---

## Newly-proposed initiatives (added 2026-05-05 to address UX-gap)

These two initiatives close the gap surfaced by the UX-impact audit
(see [`04-USER-EXPERIENCE-IMPACT.md`](04-USER-EXPERIENCE-IMPACT.md)
§4). Both are **Category A (direct user-perceived)** — the only
two such in the entire plan.

---

### P1-5 (NEW) — Generation-status visibility endpoint

**Why now.** Today a user submits a generation request and **sees
nothing** until the result arrives (or doesn't). The async-via-SQS
architecture is the right back-end choice (per ADR-010) but creates
a *user-perception cliff*: from the user's point of view, the system
is silent. **The single biggest user-experience gap surfaced by the
red-team audit.**

**Hard prerequisite.** A product designer signs off on the user
surface (modal? polling cadence? ETA visualisation?). **Engineering
should not start without this**, or it risks shipping the wrong
shape and discarding the work.

**Current state (verified 2026-05-05 by direct grep).**

* `RovoInsightsController` exposes **only two endpoints**:
  `POST /api/v1/rovo/insights/status` and
  `POST /api/v1/rovo/insights/fetch`. (There is **no** dedicated
  `/generate` endpoint in the controller — generation is triggered
  via a different surface, likely an internal SQS-producer path
  rather than a user-facing HTTP call. **This itself is a discovery
  worth confirming with the team before P1-5's scope is finalised.**)
* The existing `/status` endpoint exists but does **not** expose
  the per-task lifecycle (`submitted → queued → in_progress →
  completed → failed`) with `eta_seconds` / `attempt_count` —
  verified by reading the controller (delegates to a stub-handler-backed
  `AsyncTaskService`).
* No `Retry-After` header on async submit (no async submit endpoint
  found in this controller; whichever surface triggers generation
  needs the header added).
* No "ETA" or "attempt_count" fields anywhere.

**Open question for the team (before PR-1).** Where does the user
*actually* trigger a Rovo Insights generation? If it's from a
sibling product (e.g., Confluence dashboard widget) calling a
different PAI endpoint or a different service entirely, P1-5 must
be re-scoped. Investigating this is **part of PR-1's prep work**.

**Proposed change.**

1. Persist task lifecycle transitions in Redis (already provisioned
   per ADR-010). Write transitions from `MessageQueueConsumerMiddleware`
   (queued → in_progress) and `RovoInsightsGenerationTaskHandler`
   (in_progress → completed/failed).
2. Add `GET /api/v1/rovo-insights/{generationId}/status` returning
   `{state, eta_seconds, attempt_count, last_update_ts}`. The `eta`
   is a rolling p50 of recent generations (from the histogram added
   in P0-2).
3. Include `Retry-After` header on the `generate` 202 response
   pointing the front-end at a sensible polling cadence
   (e.g., 5 s).

**Expected metric delta (Category A — direct user-perceived).**

* Today: silent submit-then-wait. Users who don't see a result
  reload the page or give up.
* After: generation has a visible state. Front-end can render
  "Generating… ~25 s remaining" instead of nothing.
* New metric `generation.polled-after-submit.rate` (target: > 70 %
  once the surface is live and the front-end has wired the call).
* New metric `generation.user-abandoned-before-complete.rate`
  (target: significant drop vs no-status baseline).

**PR series.** **PR-SEQ-P1-5.** 3 PRs:

1. **PR-1**: Add lifecycle persistence in Redis (back-end only;
   no endpoint yet). Reviewable as pure infrastructure.
   ≤ 200 LoC.
2. **PR-2**: Add `/status` endpoint + tests + OpenAPI doc.
   ≤ 200 LoC.
3. **PR-3**: Add `Retry-After` header + the two new metrics.
   ≤ 100 LoC.

**Risk + counter-metric.**

* Risk: polling-storm if the front-end honours `Retry-After`
  too aggressively. Mitigation: floor `Retry-After` at 5 s in
  the Spring controller.
* Risk: Redis write on every state change adds load. Mitigation:
  the volume is bounded by generation rate (1 write per
  transition × ~3-4 transitions per generation). Negligible.
* Counter-metric: `redis.command.rate` and `polling.rate`.

**Historical context.** Async generation is intentional (ADR-010 +
PR #97). The team **deferred status visibility** because the real
handler isn't shipping yet. This initiative says: **build the status
surface in parallel with the real handler**, not after.

**Cross-references.**

* `cc/14-architectural-decisions` ADR-010 (async-first)
* `cc/01-business-and-technical-goals` Part 3.1 (UX metrics)
* `04-USER-EXPERIENCE-IMPACT.md` §4 (proposal rationale)
* `mod/features/rovo-insights`

---

### P1-6 (NEW) — Graceful-degradation messaging (Problem-Details for AI Gateway 429 / 4xx)

**Why now.** Today, an AI-Gateway 429 (rate-limited) propagates as
a generic 5xx to the front-end. The user sees "Something went
wrong". A better experience: **distinguish recoverable from
non-recoverable failures**, with machine-actionable error codes
the front-end can render meaningfully.

**Hard prerequisite.** Confluence + Rovo Chat front-end teams
commit to honouring the new error contract. Without that, the
back-end change is invisible.

**Current state.**

* `AIGatewayServiceImpl` (verified 2026-05-05): wraps adk
  client calls; on 4xx/5xx, the underlying adk exception
  propagates and Spring renders a generic 5xx.
* No mapping to Atlassian's mesh Problem-Details / RFC-7807
  shape.
* No distinction between rate-limit (`retry_after_seconds`),
  entitlement (`feature_not_enabled`), or transient infra
  failure.

**Proposed change.**

1. In `AIGatewayServiceImpl`, classify exceptions:
   * `429` → `ProblemDetail("rate_limited", retry_after_seconds)`
   * `403` → `ProblemDetail("not_entitled")`
   * `404` → `ProblemDetail("model_unavailable")`
   * other 4xx → `ProblemDetail("invalid_request")`
   * 5xx → `ProblemDetail("temporary_failure")`
2. Wire a Spring `@ControllerAdvice` that translates to the
   RFC-7807 Problem-Details JSON shape.
3. Document the contract in OpenAPI so front-ends can render
   it consistently.

**Expected metric delta (Category A).**

* User experience after a 429: "Servers busy, retrying in 30s"
  with optional "Cancel" CTA — instead of a generic error toast.
* User experience after a 403: "Rovo Insights not enabled for
  your workspace; contact admin" — actionable.
* New metric `gen.error.classification` tagged by code; today
  this aggregation is impossible.

**PR series.** **PR-SEQ-P1-6.** 2 PRs:

1. **PR-1**: Add error-classification + Problem-Details mapping
   + `@ControllerAdvice`. Existing tests updated; new
   classification tests added. ≤ 250 LoC.
2. **PR-2**: Add OpenAPI documentation + integration tests
   that assert the JSON shape. ≤ 150 LoC.

**Risk + counter-metric.**

* Risk: front-end teams don't adopt and the back-end work is
  invisible. Mitigation: hard prerequisite above; coordinate
  before merging.
* Risk: leaks information in error messages (e.g., model name,
  internal IDs). Mitigation: explicit allowlist of fields in
  the `ProblemDetail` mapping; security review for PR-1.
* Counter-metric: % of 5xx responses that carry a structured
  Problem-Details body (target: > 95 %).

**Historical context.** PAI uses the Atlassian-blessed adk
exceptions; Atlassian's mesh has Problem-Details guidance but
PAI has not adopted it because nothing user-facing produces
errors yet (handler is a stub).

**Cross-references.**

* `cc/14-architectural-decisions` ADR-010 (the stub)
* `mod/platform/exception` (where ``RestClientException`` lives)
* `cc/12-optimization-playbook` Lever 4 (reliability)
* `04-USER-EXPERIENCE-IMPACT.md` §4

---

## Summary table (cross-reference)

| ID | Title | Tier | Effort | PRs | OKR-impact | UX-Cat |
|---|---|---|---|---|---|---|
| P0-1 | SLO file + runbooks | P0 | S | 3 | 5 | **B** |
| P0-2 | Per-endpoint p95 histograms | P0 | S | 2 | 5 | **C** |
| P0-3 | Wire/remove dead `MetricKey`s | P0 | XS | 1 | 3 | **E** |
| P1-1 | Lift `LongRun.max` 2→6 + autoscale | P1 | S | 1 | 5 | **C** |
| P1-2 | Per-queue SQS concurrency | P1 | XS | 1 | 4 | **C** |
| P1-3 | E2E canary task + alarm | P1 | M | 2 | 4 | **B** |
| P1-4 | Idempotency-key contract | P1 | M | 2 | 4 | **B** |
| **P1-5** ⭐ | **Generation-status visibility endpoint** | P1 | M | 3 | 4 | **A** |
| **P1-6** ⭐ | **Graceful-degradation Problem-Details messaging** | P1 | S | 2 | 3 | **A** |
| P2-1 | Drop `.blockingGet()` (4 sites) | P2 | S | 1 | 3 | **C** *(corrected from agent-claimed A)* |
| P2-2 | MCP tool-discovery cache | P2 | S | 1 | 3 | **C** *(corrected from agent-claimed A)* |
| P2-3 | Detekt rule for `LaasLogger` | P2 | XS | 1 | 2 | **D** |
| P3-1 | ADR-008 migration | P3 | XS | 1 | 1 | **E** |
| P3-2 | Controller test-coverage | P3 | M | 5 | 2 | **D** |

**Total:** **14 initiatives, 26 PRs**, ~7-9 weeks of focused
engineering work for one developer or 3-4 weeks for a 3-person
team working in parallel. **2 of the 14 are Category A**
(direct user-perceived).

For the per-initiative causal chain (technical change → user
perception), see
[`04-USER-EXPERIENCE-IMPACT.md`](04-USER-EXPERIENCE-IMPACT.md) §3.

---

## Cross-references

* [`00-INDEX.md`](00-INDEX.md) — priority dashboard at a glance.
* [`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md) — how to ship each as small PRs.
* [`03-RISKS-AND-NON-GOALS.md`](03-RISKS-AND-NON-GOALS.md) — what we will NOT do.
