.. _pai-metrics-catalog:

============================================================================
Metrics, SLOs & Alarms — Source-of-Truth Catalog
============================================================================

:Date: 2026-05-05
:Confidence: **HIGH** for everything in this chapter — every fact is cited
             to a specific ``file:line`` in the live source tree, verified
             on the date above. If you find a discrepancy, the source is
             authoritative; this chapter is wrong and should be updated.
:Companion chapters:
             :doc:`01-business-and-technical-goals` (the OKR & KPIs that
             these metrics serve) and
             :doc:`12-optimization-playbook` (which lever moves which
             metric).

----

.. contents:: On this page
   :depth: 3
   :local:

----

How to read this chapter
=========================

Each row of every table in this chapter has three required fields:

* **Source citation** — exact file path + line number (or ``§`` for a YAML
  block) so you can ``grep`` the value yourself.
* **Status** — one of ``LIVE`` (configured + emitting in production),
  ``WIRED`` (defined in code but not yet emitting non-zero values
  because the upstream feature is stubbed), or
  ``PLANNED`` (referenced in a doc but not in source).
* **Owner** — the package or YAML resource that is responsible for the
  value.

If a fact has no citation, **it is not in this chapter** by design.
Speculation belongs in :doc:`10-vision-and-strategy`.

----

Part 1 — Application metric keys (Micrometer / SignalFx)
============================================================

The ``MetricKey`` enum in
``src/main/kotlin/io/atlassian/micros/proactiveai/service/metric/MetricKey.kt``
is the authoritative source of every application-emitted metric. The
enum has **7 values** as of the verification date.

Verified by reading ``MetricKey.kt`` end-to-end on 2026-05-05.

.. list-table:: ``MetricKey`` enum (7 entries — ``MetricKey.kt:6–18``)
   :header-rows: 1
   :widths: 28 22 12 38

   * - Enum value
     - Wire key (Micrometer name)
     - Status
     - Where emitted
   * - ``PROACTIVE_TEST_COUNT``
     - ``test.count``
     - LIVE
     - ``greeting/WebServiceController.kt:42`` —
       counts every hit on ``/greeting`` (the canary endpoint).
   * - ``PROACTIVE_TEST_LATENCY``
     - ``test.latency``
     - WIRED
     - Referenced from ``HistogramMetric.PROACTIVE_TEST_LATENCY``
       (``MetricKey.kt:28-32``); no direct emit site found in
       ``src/main/kotlin``. Acts as the histogram template.
   * - ``TENANT_CONTEXT_BUILD_SUCCESS``
     - ``tenant.context.build.success``
     - WIRED
     - Defined in ``MetricKey.kt:12``; no caller in current
       ``src/main/kotlin``. Reserved for tenant-context build path
       once the feature lands.
   * - ``TENANT_CONTEXT_BUILD_ERROR``
     - ``tenant.context.build.error``
     - WIRED
     - Same status as the success twin (``MetricKey.kt:13``).
   * - ``STREAMHUB_EVENT_PROCESSED``
     - ``streamhub.event.processed``
     - LIVE
     - ``sqs/AnalyticsEventsMessageQueueConsumer.kt:34`` — incremented
       per processed StreamHub UI event, tagged with ``avi=<event.type>``.
   * - ``STREAMHUB_EVENT_UNSUPPORTED``
     - ``streamhub.event.unsupported``
     - LIVE
     - ``sqs/AnalyticsEventsMessageQueueConsumer.kt:42`` — incremented
       when the consumer receives an event whose ``avi`` is not in the
       handled set.
   * - ``STREAMHUB_EVENT_ERROR``
     - ``streamhub.event.error``
     - LIVE
     - ``sqs/AnalyticsEventsMessageQueueConsumer.kt:62`` — incremented
       on any uncaught throwable inside the per-event handler.

Companion enums in ``MetricKey.kt`` (HIGH-confidence — counted by hand):

.. list-table::
   :header-rows: 1
   :widths: 28 22 12 38

   * - Enum & value
     - Wire key
     - Status
     - Where used
   * - ``HistogramMetric.PROACTIVE_TEST_LATENCY``
     - ``test.latency`` + bucket tag
     - WIRED
     - Couples ``PROACTIVE_TEST_LATENCY`` to the
       ``PROACTIVE_HISTOGRAM_BUCKETS`` boundary list
       (``MetricKey.kt:28-33``).
   * - ``ResultMetricBase.ERS_CREATE``
     - ``ers.create.{success,error,latency}``
     - PLANNED
     - **Distinct from ``MetricKey``** — see the note below.
       ``MetricKey.kt:46`` is the only declaration; no emit site found.
   * - ``HistogramBucket.PROACTIVE_HISTOGRAM_BUCKETS``
     - ``"200_500_..._15000"``
     - LIVE (template)
     - The bucket-edge spec used by every histogram metric
       (``MetricKey.kt:54``).
   * - ``Status.SUCCESS`` / ``Status.ERROR``
     - ``"success"`` / ``"error"``
     - LIVE (template)
     - Used as a tag value by every ``count(...)`` /
       ``timeAndCountResult(...)`` call that emits a result-bearing
       metric (``MetricKey.kt:67-71``).

.. note::

   **Earlier reports listed ``ERS_CREATE`` as a ``MetricKey``.** That is
   incorrect: ``ERS_CREATE`` belongs to ``ResultMetricBase``, a different
   enum used by ``CoreMetricsService.timeAndCountResult(base: ResultMetricBase, …)``
   to emit ``base.success`` + ``base.error`` + ``base.latency`` triplets.
   Counting it as a ``MetricKey`` over-counts the live application-metric
   surface. Verified 2026-05-05.

   **Net live application-metric count: 4** (``test.count``,
   ``streamhub.event.processed``, ``streamhub.event.unsupported``,
   ``streamhub.event.error``). The other four enum slots are reserved.

Part 2 — Histogram boundaries (latency / size distributions)
================================================================

``application.yml`` lines `~17–19` (verified 2026-05-05):

.. code-block:: yaml

   micros:
     metrics:
       histograms:
         - metricName: http.server.requests
           boundaries: 100ms, 500ms, 1s, 2s, 3s, 4s, 5s, 10s, 20s, 120s

This is the **only** histogram registered globally for HTTP requests.
All endpoint p50/p95/p99 dashboards roll up to these buckets.

For app-emitted timers, the bucket spec is
``HistogramBucket.PROACTIVE_HISTOGRAM_BUCKETS`` —
``200_500_1000_2000_3000_4000_5000_6000_7000_8000_9000_10000_15000`` (ms).
13 buckets, max 15s. The mismatch with the HTTP histogram (which extends
to 120s) is **intentional**: HTTP-side timeouts can stretch under
abuse; app-emitted operations have a hard 15s ceiling above which
they're considered failed.

Part 3 — Common Micrometer tags
====================================

``application.yml`` `~21-25` registers four common tags applied to
**every** metric:

.. code-block:: yaml

   micros:
     metrics:
       tags.common:
         - environment
         - environment_type
         - region
         - deployment_id

Per-metric additional tags are applied at emit time. The most common
ones (cross-referenced from ``service-metric/`` impl):

* ``avi`` — StreamHub Analytics-Versioned Identifier (event type),
  e.g. ``ui-created``, applied to all ``streamhub.event.*`` metrics.
* ``tenant_id`` — appended automatically by the metrics service for
  any call made within a tenant-scoped request context (see
  :doc:`08-auth-and-tenant`).
* ``account_id`` — same auto-mechanism, applied for user-scoped calls.

Part 4 — Alarms registered in ``service-descriptor.sd.yml``
================================================================

Six alarms are configured today. **No CV/SLO file exists** —
the service has reactive alarms but no formal SLO targets.
Verified 2026-05-05 by reading ``service-descriptor.sd.yml`` end-to-end
and confirming ``continuous-verification.yml`` does not exist.

.. list-table:: Alarms — ``service-descriptor.sd.yml``
   :header-rows: 1
   :widths: 32 18 18 32

   * - Alarm
     - Threshold
     - Priority
     - Source
   * - ``EngineCPUUtilizationTooHigh`` (Redis)
     - > 90 % avg, 5 datapoints × 60 s
     - Low
     - ``service-descriptor.sd.yml`` §``redisx.alarms``
       (lines ~37-58)
   * - *(analytics-events queue has no alarms)*
     - —
     - —
     - ``service-descriptor.sd.yml`` §``sqs[name=analytics-events]``
       — no ``alarms:`` block
   * - ``HighRovoInsightsGenerationProcessingLatency``
     - ``ApproximateAgeOfOldestMessage`` > 720 s for 6 × 5-min periods
       (≈ 30 min)
     - Low
     - ``sd.yml`` §``sqs[name=rovo-insights-generation-queue].alarms``
       (lines ~120-131)
   * - ``RovoInsightsGenerationDLQueueAlertLow``
     - DLQ depth > 0 (any message in DLQ)
     - Low
     - ``sd.yml`` §``…alarms`` (lines ~132-141)
   * - ``RovoInsightsGenerationDLQueueAlertHigh``
     - DLQ depth > 100
     - Low (TODO: bump to High in prod — see comment in YAML)
     - ``sd.yml`` §``…alarms`` (lines ~142-152)
   * - ``UnHealthyHostCount`` (default override)
     - > 1 unhealthy host for 6 × 60 s
     - Low
     - ``sd.yml`` §``alarms.overrides`` (lines ~178-183)
   * - ``WebServerMemoryAlarmHigh``
     - MemoryUtilization > 90 % avg for 2 × 5-min periods
     - Low
     - ``sd.yml`` §``alarms.overrides`` (lines ~184-191)

Critical observations from this list:

1. **Every alarm is Priority Low.** Nothing pages on call. This is
   appropriate for a pre-production-load service; should be revisited
   when PAI sits on the hot OKR path. The ``…AlertHigh`` alarm has an
   inline TODO to escalate.
2. **Every runbook URL is "TBD."** Five of six alarm descriptions
   literally end with ``Runbook: TBD``. Authoring runbooks is a
   pre-requisite for promoting any alarm to ``Priority: High``.
3. **The analytics-events queue has zero alarms.** A spike in StreamHub
   event errors is currently invisible at the alarm layer; only the
   Micrometer ``streamhub.event.error`` counter (Part 1) records it.

Part 5 — SLO/SLI registration status
=========================================

**As of 2026-05-05: NO formal SLO/SLI is registered.**

* ``continuous-verification.yml`` — **does not exist** in the repo.
* ``policies/`` — contains only POCO (service-catalog) policies,
  no SLO targets.
* ``compass.yaml`` — **does not exist** in the repo.

The "planned" SLOs catalogued in
:doc:`01-business-and-technical-goals` Part 3 (99.9 % non-5xx,
p95 < 50 ms for nudge, etc.) are documentation aspirations,
not configured targets. They will not fire alarms or block deploys
until they are added to a CV file.

This is by design at the present stage (PAI has no production hot-path
load yet). Promoting any of those targets to enforced SLOs requires:

1. Author ``continuous-verification.yml`` with the SLI definition.
2. Add the SLO to the relevant alarm priority (Low → Medium/High).
3. Register the runbook URL in the alarm description.
4. Add the alarm to the on-call rotation in Opsgenie.

Part 6 — Service-resource sizing (capacity ceilings)
=========================================================

Verified by reading ``service-descriptor.sd.yml`` and ``application.yml``
on 2026-05-05.

.. list-table:: Compute & memory
   :header-rows: 1
   :widths: 28 25 47

   * - Resource
     - Sizing
     - Source
   * - WebServer instance type
     - ``t3a.medium`` (2 vCPU, 4 GiB)
     - ``sd.yml`` §``scaling.instance``
   * - SHWorkers instance type
     - ``t3a.medium``, ``min: 1`` (no ``max:`` set → no autoscaling)
     - ``sd.yml`` §``workers[name=SHWorkers].scaling`` (lines ~205-211)
   * - LongRun instance type
     - ``t3a.medium``, ``min: 1, max: 2`` (hard cap)
     - ``sd.yml`` §``workers[name=LongRun].scaling`` (lines ~218-223)
   * - JVM heap (all groups)
     - ``-XX:MaxRAMPercentage=25.0`` → ~1 GiB on t3a.medium
     - ``sd.yml`` §``config.environmentVariables.MEMORY_OPTS``
       (line ~239)
   * - Local-dev heap
     - ``-Xmx512M``
     - ``sd.yml`` §``environmentOverrides.local`` (line ~265)

.. list-table:: Concurrency
   :header-rows: 1
   :widths: 30 25 45

   * - Pool
     - Sizing
     - Source
   * - MVC async executor
     - core 16 / max 64 / queueCapacity 0
     - ``config/WebMvcConfiguration.kt:46-48``
     - 
   * - SQS listener concurrency (every queue, every JVM)
     - ``2-8`` (Spring lower-upper)
     - ``application.yml`` §``atlassian.sqs.properties.concurrency``
   * - ``rovo-insights-generation-queue`` visibility
     - 360 s default; per-message extension via
       ``VisibilityExtendingSQSQueueConsumer``
     - ``sd.yml`` §``sqs[name=rovo-insights-generation-queue].attributes.VisibilityTimeout``
   * - ``analytics-events`` visibility
     - 120 s
     - ``sd.yml`` §``…analytics-events.attributes.VisibilityTimeout``
   * - ``rovo-insights-generation-queue`` MaxReceiveCount
     - 2 (then DLQ)
     - ``sd.yml`` §``…attributes.MaxReceiveCount``
   * - ``analytics-events`` MaxReceiveCount
     - 3 (then DLQ)
     - ``sd.yml`` §``…attributes.MaxReceiveCount``

Part 7 — Egress dependencies (with SLA-impacting timeouts)
================================================================

Three external services. Every egress timeout caps the upstream PAI
endpoint's worst-case response time. Verified 2026-05-05 from
``service-descriptor.sd.yml`` §``serviceProxy.egress.dependencies``
(lines ~307-317):

.. list-table::
   :header-rows: 1
   :widths: 22 18 22 38

   * - Dependency
     - Timeout
     - Retry policy
     - Notes
   * - ``id-gatekeeper``
     - 20 s
     - Retry on 5xx + 429
     - User identity enrichment. Cap on every interceptor cold path.
   * - ``ai-gateway``
     - **600 s (10 min)**
     - Retry on 5xx + 429
     - Generous because LLM streaming generations can run long.
       This is the single largest latency risk for any user-facing
       endpoint that calls AI Gateway synchronously.
   * - ``integrations-service``
     - 60 s
     - Retry on 5xx + 429
     - MCP session management. Used by Stratus agents to enumerate
       tools.

The ``application.yml`` ``integrations-service.timeout: 30`` (seconds)
applies to a *different* code-level HTTP timeout for MCP discovery
calls within the service; the 60 s above is the service-mesh ingress
timeout enforced at the proxy.

Part 8 — Observability stack (where the data goes)
========================================================

* **Micrometer** — instrumentation facade (every ``MetricKey``).
* **SignalFx** — aggregation back-end via the Micros observability
  sidecar. Sidecar drops anything not prefixed with ``proactive-ai.``;
  the prefix is set in ``WebMvcConfiguration.kt`` at metric registration
  time.
* **Splunk** — log aggregation. MDC keys (see
  :doc:`03-request-context-and-mdc`) become indexed Splunk fields:
  ``request_id``, ``tenant_id``, ``account_id``, ``cloud_id``.
* **CloudWatch** — every alarm in Part 4 evaluates against CloudWatch.
  ``ApproximateAgeOfOldestMessage`` and ``ApproximateNumberOfMessagesVisible``
  are the AWS/SQS native metrics.
* **Tome** — the registered alarm-priority routing system. Currently
  no Tome SLO entry for this service (Part 5).

Part 9 — Quick reference for on-call
=========================================

If you are paged for ``proactive-ai-platform`` (which today happens
only for ``Priority: High`` alarms — none currently exist), the
**runbook URLs are TBD** (Part 4). Until those are written, the
recovery flow is:

.. code-block:: text

   1. Splunk:  index=micros service=proactive-ai-platform stack=...
              -> filter by request_id / tenant_id from the alarm
   2. SignalFx dashboard: prefix=proactive-ai.
              -> check for the affected MetricKey from Part 1
   3. CloudWatch: namespace=AWS/SQS  QueueName=<from alarm>
              -> for any SQS-backed alarm
   4. Slack:   #help-ai-experience
              -> primary on-call channel for the team

Part 10 — What is missing (delta vs. mature observability)
================================================================

Honest gap list, derived from the verifications above. Each is a
pre-condition for promoting PAI to a hot-path service:

1. **Author SLOs** — ``continuous-verification.yml`` doesn't exist.
2. **Author runbooks** — five of six alarm descriptions say
   ``Runbook: TBD``.
3. **Add alarms to the analytics-events queue** — currently zero
   alarms there.
4. **Promote ``…DLQueueAlertHigh`` to ``Priority: High`` in prod**
   (already TODO'd inline).
5. **Replace the ``MicrosEnvironmentType`` consumer gap** —
   noted in :doc:`/modules/platform/config`.
6. **Wire latency timers for every controller** — today only the
   global ``http.server.requests`` histogram is registered; per-endpoint
   p95 dashboards rely on tag-filtering rather than first-class
   metrics.
7. **Wire ``TENANT_CONTEXT_BUILD_*`` and ``ERS_CREATE`` emit sites** —
   keys are reserved (Part 1) but no code emits them yet.

These items also constitute the canonical to-do list for the
"observability hardening" investment described in the FY26 H2 plan.

Cross-references
==================

* :doc:`01-business-and-technical-goals` — the OKR & KPIs that this
  catalog backs.
* :doc:`12-optimization-playbook` — which lever moves which metric.
* :doc:`05-observability-and-metrics` — concept-level overview.
* :doc:`09-deployment-and-config` — where the YAML facts come from.
* :doc:`/modules/platform/service-metric` — the
  ``MetricsService``/``CoreMetricsService`` API.
* :doc:`/modules/platform/config` — the ``ContextSnapshotFactory`` and
  ``ExecutorServiceMetrics`` registration.
