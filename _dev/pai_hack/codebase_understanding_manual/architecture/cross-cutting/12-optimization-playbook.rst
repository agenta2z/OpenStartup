.. _pai-optimization-playbook:

============================================================================
Optimization Playbook — Which Lever Moves Which Metric
============================================================================

:Date: 2026-05-05
:Confidence: Levers and code paths are **HIGH** confidence (cited to source).
             "Expected impact" columns are **MEDIUM** confidence — they are
             best-judgement engineering estimates, not benchmarked deltas.
             Re-validate with a real load test before committing to any
             impact claim in a PR description.
:Companion chapters:
             :doc:`11-metrics-catalog` (the metrics being moved) and
             :doc:`01-business-and-technical-goals` (the OKR being served).

----

.. contents:: On this page
   :depth: 3
   :local:

----

How to use this chapter
========================

This chapter answers, for an engineer arriving Monday morning: **"what
should I change to move metric X?"** Each section follows the pattern:

1. **Metric** — the thing you want to move (linked to its catalog row).
2. **Levers** — the code/config knobs available, in priority order.
3. **Where to change it** — exact ``file:line`` or YAML key.
4. **Expected impact** — engineering estimate (calibrate with a load
   test before quoting in a PR).
5. **Risks / counter-metrics** — what gets worse if you push too far.

If you find yourself wanting to move a metric that isn't listed,
**add a row** rather than guessing — this chapter should grow as the
service matures.

----

Part 1 — Move "monthly proactive AI invocations" (the OKR)
=================================================================

This is the FY26 H2 north star (400K → 1.5M / month). Every other
section in this chapter is downstream of this one. See
:doc:`01-business-and-technical-goals` Part 1 for the OKR contract.

Lever 1.1 — Ship the real Rovo Insights generation handler
------------------------------------------------------------

* **Where:** ``feature/rovoinsights/internal/`` — the
  ``RovoInsightsGenerationTaskHandler`` is currently a stub. The
  full convo-ai port is Stage-2 work in the H2 plan.
* **Why it moves the metric:** Rovo Insights is the single largest
  invocation lift in the FY26 plan
  (:doc:`01-business-and-technical-goals` Part 6).
* **Expected impact:** **highest** of any single lever. The team's
  growth model attributes ~3× of the 4× OKR lift to this surface.
* **Risks / counter-metrics:** raises ``ai-gateway`` cost per request;
  forces ``LongRun`` worker count up (currently capped ``max: 2`` in
  ``service-descriptor.sd.yml`` — see :doc:`11-metrics-catalog` Part 6).
  *Plan a ``max:`` bump in the same PR.*

Lever 1.2 — Wire real TAP-trait throttling into nudge
-------------------------------------------------------

* **Where:** ``feature/nudge/`` — controller currently returns a stub
  decision. Real path needs a TAP-sidecar call (sidecar URL set via
  ``TAP_SIDECAR_BASE_URL`` env var, see ``nebulae.yml``).
* **Why it moves the metric:** unlocks Stage-2 use-case launches
  (Conversation Starter ramp + new surfaces). The OKR Part 4 calls
  out throttle effectiveness as the gate.
* **Expected impact:** **high** — but indirect; the throttle is the
  permission slip for new surfaces, not the surface itself.
* **Risks:** an over-tight throttle suppresses invocations directly;
  watch acceptance rate vs. dismiss rate
  (:doc:`11-metrics-catalog` Part 1 will need new keys for this).

Lever 1.3 — Add a new proactive surface
-----------------------------------------

* **Where:** create a new ``feature/<surface>/`` package + controller +
  ``AsyncTask`` if generation is async. Follow the
  :doc:`/modules/features/rovo-insights` template.
* **Why it moves the metric:** new surfaces add raw invocations.
* **Expected impact:** **medium** — surface adoption is gated by AIX UX
  rollout, not just backend availability.
* **Risks:** invocation noise — without paired quality metrics, a new
  surface can inflate the OKR and degrade Proactive Fans %. Always
  ship a new surface with its acceptance/dismiss tracking wired.

Part 2 — Move p95 latency on a user-facing endpoint
=========================================================

The most-watched latency is on ``POST /api/v1/nudge/throttle`` (the
nudge-render path; aspirational target < 50 ms p95 — see
:doc:`01-business-and-technical-goals` Part 3.2).

Lever 2.1 — Push generation off the request path
--------------------------------------------------

* **Where:** any controller that calls AI Gateway synchronously.
  Convert to ``AsyncTaskService.submit(...)`` + Redis-result-poll
  pattern (template in ``feature/rovoinsights/``).
* **Why it moves the metric:** the ``ai-gateway`` egress timeout is
  **600 s** (:doc:`11-metrics-catalog` Part 7). Any sync call inherits
  that worst case. Async-first hides AI-Gateway latency entirely.
* **Expected impact:** **highest** for any LLM-touching endpoint —
  drops p95 from "AI Gateway p95 + your overhead" to just your
  overhead (~5 ms).
* **Risks:** front-end has to poll; user-perceived latency is now
  poll cadence × Redis p99. Cache the result aggressively
  (Redis ``proactive-ai-cache``, see ``service-descriptor.sd.yml``).

Lever 2.2 — Increase MVC async-executor parallelism
-----------------------------------------------------

* **Where:** ``config/WebMvcConfiguration.kt:46-48`` —
  ``corePoolSize`` (16), ``maxPoolSize`` (64), ``queueCapacity`` (0).
* **Why it moves the metric:** if requests are queueing on thread
  starvation, raising ``maxPoolSize`` reduces queue-wait p95.
* **Expected impact:** **low-medium** at current load (no production
  hot path yet); becomes **high** when LongRun/SHWorker generation
  load arrives.
* **Risks:** thread context switches at very high counts; JVM heap
  pressure (each thread = ~1 MiB stack). Pair any bump above 128 with
  an instance-type change (currently ``t3a.medium`` →
  ``t3a.large``).
* **Counter-metric:** watch the ``proactive-ai.ProactiveAIAsyncExc-*``
  Micrometer ``ExecutorServiceMetrics`` family
  (``WebMvcConfiguration.kt`` registers it via ``ExecutorServiceMetrics.monitor(...)``).

Lever 2.3 — Tighten the ``ai-gateway`` timeout
------------------------------------------------

* **Where:** ``service-descriptor.sd.yml`` §``serviceProxy.egress.dependencies``
  for ``ai-gateway`` (line ~313).
* **Why it moves the metric:** caps the worst-case sync request.
* **Expected impact:** **medium** — only matters for any remaining
  sync paths. Most paths should be async (Lever 2.1).
* **Risks:** legitimate long generations get cut off → 504s →
  retry storm via ``retryOn5xxAnd429Policy``. Coordinate with the AI
  Gateway team on what timeout their p99 actually is before tightening.

Part 3 — Move throughput (RPS / events-per-sec)
=====================================================

Lever 3.1 — Raise SQS listener concurrency
--------------------------------------------

* **Where:** ``application.yml`` §``atlassian.sqs.properties.concurrency``
  — currently ``"2-8"``.
* **Why it moves the metric:** linearly increases parallel in-flight
  messages per JVM per queue.
* **Expected impact:** **high** for the
  ``rovo-insights-generation-queue`` consumer; **medium** for
  ``analytics-events`` (latter is bounded upstream by StreamHub).
* **Risks:** raises memory pressure (each handler holds the message
  in memory); raises pressure on the AI Gateway downstream. Bump
  ``LongRun.scaling.max`` (``service-descriptor.sd.yml`` line ~221)
  in lockstep.

Lever 3.2 — Raise the LongRun pool ``max:``
---------------------------------------------

* **Where:** ``service-descriptor.sd.yml`` §``workers[name=LongRun].scaling.max``
  — currently ``2``.
* **Why it moves the metric:** caps total cluster generation
  parallelism today. Already flagged by the team as the bottleneck for
  Rovo Insights production rollout.
* **Expected impact:** **high** — was the unblocker theme of PR #103
  (visibility extension).
* **Risks:** AWS cost (each ``t3a.medium`` ≈ small but not free);
  AI Gateway quota.

Lever 3.3 — Switch ``rovo-insights-generation-queue`` to a FIFO group
-----------------------------------------------------------------------

* **Where:** ``service-descriptor.sd.yml`` §``sqs[name=rovo-insights-generation-queue].attributes`` —
  add ``FifoQueue: true`` (the YAML comment already calls this out).
* **Why it moves the metric:** FIFO with per-tenant message-group-id
  gives per-tenant fairness — one noisy tenant can't starve others.
* **Expected impact:** **medium** at current load; **high** when
  multi-tenant generation is hot.
* **Risks:** FIFO has a per-group-id 300-msg/sec cap; group sizing
  must be plausible. This is a one-way migration in some senses
  (queue-name rename + DLQ rename).

Part 4 — Move reliability (fewer 5xx, fewer DLQ messages)
=================================================================

Lever 4.1 — Tune ``MaxReceiveCount`` per queue
------------------------------------------------

* **Where:**
  ``service-descriptor.sd.yml`` §``sqs[*].attributes.MaxReceiveCount``
  — analytics-events: ``3``; rovo-insights-generation: ``2``.
* **Why it moves the metric:** more retries → fewer DLQ messages →
  ``RovoInsightsGenerationDLQueueAlert*`` fires less.
* **Expected impact:** **low** if upstream errors are deterministic;
  **medium** if errors are transient (network blips, AI Gateway 429s).
* **Risks:** retries amplify load on the failing downstream. If
  AI Gateway is rate-limiting, retrying more makes it worse.

Lever 4.2 — Make ``AsyncTaskHandler`` idempotent
--------------------------------------------------

* **Where:** every concrete ``AsyncTaskHandler<T>`` implementation
  (template:
  ``feature/rovoinsights/internal/RovoInsightsGenerationTaskHandler``).
* **Why it moves the metric:** SQS at-least-once delivery means the
  same task can run twice; without idempotency the second run causes
  user-visible duplication or DB-level errors.
* **Expected impact:** **high** for any handler that mutates external
  state (writes to Redis, calls AI Gateway with side-effects).
* **Risks:** none — this is an unconditional best-practice.

Lever 4.3 — Move alarm priority (today all Low)
-------------------------------------------------

* **Where:** ``service-descriptor.sd.yml`` §``sqs[*].alarms[*].Priority``
  and ``alarms.overrides.*.Priority``.
* **Why it moves the metric:** Low alarms don't page → on-call doesn't
  intervene → DLQ depth grows. Promoting to Medium/High makes
  reliability a first-class concern.
* **Expected impact:** **operational** (changes who notices the
  problem) — does not directly move a Micrometer metric.
* **Risks:** pager fatigue if thresholds are wrong. Author runbooks
  first (currently five of six alarms have ``Runbook: TBD`` —
  :doc:`11-metrics-catalog` Part 4).

Part 5 — Move developer velocity
=====================================

Lever 5.1 — Author runbooks for each Priority-Low alarm
---------------------------------------------------------

* **Where:** Confluence space ``proai`` or ``AM3``; link from
  alarm ``Description:`` field.
* **Why it moves the metric:** unblocks promoting alarms to
  ``Priority: High`` (Lever 4.3); reduces MTTR.
* **Expected impact:** **medium-high** on incident MTTR.
* **Risks:** runbook drift if not maintained; assign an owner.

Lever 5.2 — Author ``continuous-verification.yml``
----------------------------------------------------

* **Where:** new file at the repo root.
* **Why it moves the metric:** registers the aspirational SLOs
  (:doc:`01-business-and-technical-goals` Part 3) as enforced targets.
  Without it, no deploy gate can fail on regression.
* **Expected impact:** **high** on long-run reliability — gates
  prevent regression, runbooks contain it.
* **Risks:** false-positive deploy blocks if SLI is poorly defined.
  Start with low-bar SLOs (e.g. p95 < 1 s) and tighten.

Lever 5.3 — Adopt the End-to-End UX Impact PR section
-------------------------------------------------------

* **Where:** PR template (currently no enforced template; convention
  observed in convo-ai-platform PR descriptions per
  :doc:`02-development-history` §3.2).
* **Why it moves the metric:** every PR forces the author to think
  about which OKR/KPI moves. Aligns reviewer attention.
* **Expected impact:** **medium-high** on long-run prioritisation
  quality.
* **Risks:** template fatigue if the section is boilerplate. Make it
  required only for PRs that touch ``feature/``.

Part 6 — Cross-lever interaction matrix
==============================================

Some levers move two metrics in opposite directions. This matrix
flags the most important interactions.

.. list-table::
   :header-rows: 1
   :widths: 28 14 14 44

   * - Lever
     - Helps
     - Hurts
     - Mitigation
   * - 1.3 New surface
     - Invocations
     - Acceptance rate
     - Pair launch with quality metric review
   * - 2.2 Raise async pool
     - p95
     - Heap pressure
     - Bump instance type in same PR
   * - 2.3 Tighten ai-gateway timeout
     - p95
     - Reliability (504 storms)
     - Coordinate with AI Gateway team on real p99
   * - 3.1 SQS concurrency
     - Throughput
     - AI Gateway quota; heap
     - Bump LongRun ``max:`` + watch quota dashboard
   * - 3.2 LongRun ``max:``
     - Throughput
     - AWS cost
     - Match to forecast OKR ramp; sunset at next H1
   * - 4.1 MaxReceiveCount up
     - DLQ depth
     - Downstream load on transient failures
     - Set DLQ alarm threshold proportionally
   * - 4.3 Promote alarm priority
     - MTTR
     - Pager fatigue
     - Runbook authoring is the precondition

Part 7 — Levers explicitly NOT recommended
================================================

Anti-patterns observed when reviewing past PRs and the corporate
strategic notes:

* **Pre-warming Stratus agents on web threads.** Tempting for p95;
  in practice destabilises the executor pool and starves real
  requests. If pre-warm matters, do it on a dedicated worker.
* **Polling instead of webhooks for cross-service state.** Cheap
  to ship; expensive at scale. Default to event-driven via SQS.
* **Bypassing ``LaasLoggerFactory``.** Caught repeatedly in code
  review (:doc:`02-development-history` §5). Direct
  ``LoggerFactory.getLogger(...)`` calls drop the MDC enrichment that
  the on-call relies on.
* **Speculatively widening Statsig flag scopes.** Each flag adds
  evaluation latency to ``RequestContextInterceptor``. Keep the flag
  set tight; retire dead flags.
* **Adding metrics to ``MetricKey`` without an emit site in the same
  PR.** Currently 3 of 7 enum values are ``WIRED``-but-not-emitting
  (:doc:`11-metrics-catalog` Part 1) — that's already too many
  zombie keys.

Part 8 — How to author a PR that moves a metric
=====================================================

Drawn from the conventions in :doc:`02-development-history` §3.1
(the "exemplary" PRs #103 and #105 are the templates):

1. **Name the metric** in the PR title. e.g.,
   ``[AIX-3xxx] Move RovoInsights p95 -25 % via async path conversion``.
2. **Quote the baseline** in the description. Run ``signalfx-cli`` or
   take a screenshot. No baseline → the change is a guess.
3. **Quote the expected delta** with a short rationale tied to a row
   in this chapter.
4. **List the counter-metric** you watched. If you raised throughput,
   confirm reliability stayed flat.
5. **Link the alarm** that would catch a regression. If no alarm
   exists for what you're changing, **first PR is the alarm**, second
   PR is the change.

Cross-references
==================

* :doc:`01-business-and-technical-goals` — the OKR these levers serve.
* :doc:`10-vision-and-strategy` — why moving these metrics matters
  beyond the current half.
* :doc:`11-metrics-catalog` — the full catalog of metrics that get moved.
* :doc:`02-development-history` — historical examples of PRs that moved
  metrics well.
* :doc:`/modules/platform/config` — the executor & condition machinery.
* :doc:`/modules/platform/sqs` and :doc:`/modules/platform/task` — the
  async pipeline being tuned.
