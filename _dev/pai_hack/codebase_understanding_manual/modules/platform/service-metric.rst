.. _pai-platform-service-metric:

============================================================================
``service/metric`` — Micrometer-based metrics API
============================================================================

:Date: 2026-05-04
:Files: 5 main / 2 test
:Importance: **P1 — observability backbone**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Provides ``MetricsService`` (the rich verb-API) on top of ``CoreMetricsService``
(the Micrometer-facing thin adapter). All emits auto-tag with tenant/account/
request_id from MDC so callers never need to manually add request context.

Two-layer design:

* **``CoreMetricsService``** — low-level Micrometer operations (count, gauge,
  histogram, time). Platform-only consumers use this.
* **``MetricsService``** — higher-level convenience methods
  (``timeAndHistogram``, ``timeAndCountResult``, ``summarize``). Feature code
  uses this.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``MetricKey.kt``
     - ~70
     - Metric key enums + histogram bucket definitions + status enum
   * - ``CoreMetricsService.kt`` (interface)
     - ~75
     - Low-level Micrometer facade
   * - ``MetricsService.kt`` (interface)
     - ~75
     - High-level convenience verbs
   * - ``internal/MetricsServiceImpl.kt``
     - ~80
     - Wraps CoreMetricsService with auto tag injection
   * - ``internal/CoreMetricsServiceImpl.kt``
     - ~100
     - Direct Micrometer adapter

3. Key types deep dive
=========================

``MetricKey`` (enum)
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   enum class MetricKey(override val key: String) : MetricKeyLike {
       PROACTIVE_TEST_COUNT("test.count"),
       PROACTIVE_TEST_LATENCY("test.latency"),
       TENANT_CONTEXT_BUILD_SUCCESS("tenant.context.build.success"),
       TENANT_CONTEXT_BUILD_ERROR("tenant.context.build.error"),
       STREAMHUB_EVENT_PROCESSED("streamhub.event.processed"),
       STREAMHUB_EVENT_UNSUPPORTED("streamhub.event.unsupported"),
       STREAMHUB_EVENT_ERROR("streamhub.event.error"),
   }

All metric keys are centralised here. Adding a new metric means adding an enum
value — prevents typos and enables IDE navigation.

``HistogramMetric`` — links a ``MetricKey`` to a ``HistogramBucket``:

.. code-block:: kotlin

   enum class HistogramMetric(val metricKey: MetricKey, val histogramBucket: HistogramBucket) {
       PROACTIVE_TEST_LATENCY(MetricKey.PROACTIVE_TEST_LATENCY, HistogramBucket.PROACTIVE_HISTOGRAM_BUCKETS),
   }

``HistogramBucket`` — defines custom bucket boundaries:

.. code-block:: kotlin

   PROACTIVE_HISTOGRAM_BUCKETS("200_500_1000_2000_3000_4000_5000_6000_7000_8000_9000_10000_15000")

Bucket boundaries in milliseconds: 200, 500, 1s, 2s, 3s, 4s, 5s, 6s, 7s, 8s,
9s, 10s, 15s — tuned for AI/LLM response latencies.

``ResultMetricBase`` — base names for success/failure metric pairs:

.. code-block:: kotlin

   enum class ResultMetricBase(val base: String) {
       ERS_CREATE("ers.create"),
   }

``Status`` — standard success/error enum for metric tags.

``CoreMetricsService`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Low-level Micrometer facade with overloaded methods:

* ``count(metricKey)`` — simple counter increment
* ``count(metricKey, tags)`` — counter with tag pairs
* ``count(successKey, failureKey, function)`` — wraps a function, counting
  success/failure automatically
* ``summarize(metricKey, size, tags)`` — distribution summary
* ``histogram(metricKey, tags, function)`` — wraps a function, recording
  histogram of execution time
* ``gauge(metricKey, amount, tags)`` — gauge value
* ``time(metricKey, duration, tags)`` — record duration
* ``timeAndCountResult(metricBase, tags, function)`` — time + count with
  result transformation
* ``status(metricKey, function)`` — wraps with success/error status tag

``MetricsService`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Higher-level convenience methods building on ``CoreMetricsService``:

* ``time(metricKey: MetricKey, duration: Duration)`` — simple timer
* ``timeAndHistogram(histogramMetric, duration, tags)`` — timer +
  histogram with custom buckets
* ``timeAndCountResult(metricBase: ResultMetricBase, ...)`` — timed
  execution with result-based counting
* ``histogram(histogramMetric, tags, function)`` — wraps function with
  histogram recording

4. Auto-tagging
==================

``MetricsServiceImpl`` automatically injects MDC context as tags:

* ``tenant_id`` — from MDC
* ``account_id`` — from MDC
* ``request_id`` — from MDC

This means callers never need to manually pass request context — it is
always present in the metric tags if MDC has been populated by the
interceptor chain.

5. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``MetricsServiceImplTest``
     - Verb contract, auto-tag injection, tag merging with caller tags
   * - ``CoreMetricsServiceImplTest``
     - Micrometer adapter: counter increment, gauge setting, histogram recording

6. Design decisions
======================

1. **Two-layer API** — ``CoreMetricsService`` for platform (direct Micrometer
   control), ``MetricsService`` for features (convenience verbs). Prevents
   feature code from needing Micrometer knowledge.
2. **Enum-based metric keys** — compile-time safety, IDE navigation, prevents
   string typos that would create orphan metrics.
3. **Auto-tagging from MDC** — eliminates boilerplate and ensures every metric
   has request context for correlation.
4. **Custom histogram buckets** — tuned for AI workload latencies (200ms–15s)
   rather than default Micrometer buckets.
5. **GSD histogram tag** — ``gsd_histogram`` tag enables Atlassian's Global
   Service Dashboard to render custom bucket boundaries.

7. See also
==============

* :doc:`/architecture/cross-cutting/05-observability-and-metrics` §1 — emit-verb
  examples, histogram bin configuration
* :doc:`/modules/platform/logging` — structured logging companion
* :doc:`/modules/platform/requestcontext` — MDC context source
