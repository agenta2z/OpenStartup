==========================================
Module: ``metrics`` — Observability Layer
==========================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Provides a **type-safe, dual-layer metrics API** for emitting counters, timers,
histograms, gauges, and summary distribution statistics to Micrometer.  The
two-layer design separates a low-level ``CoreMetricsService`` (accepts any
``MetricKeyLike``) from a higher-level ``MetricsService`` (works with typed
``MetricKey`` / ``HistogramMetric`` / ``ResultMetricBase`` enums).

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``CoreMetricsService.kt``
     - 149
     - Interface — low-level metrics facade (``MetricKeyLike``)
   * - ``MetricKey.kt``
     - 73
     - Enums & types: ``MetricKey``, ``MetricKeyLike``, ``HistogramMetric``, ``ResultMetricBase``, ``HistogramBucket``, ``Status``
   * - ``MetricsService.kt``
     - 227
     - Interface — high-level typed metrics facade
   * - ``internal/CoreMetricsServiceImpl.kt``
     - 436
     - ``@Component`` — Micrometer-backed implementation
   * - ``internal/MetricsServiceImpl.kt``
     - 358
     - ``@Component`` — delegates to ``CoreMetricsService``

**Total: 5 files, ~1,243 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``MetricKeyLike`` — single property ``val key: String``.  Allows both enum
  constants and ad-hoc metric keys.

* ``CoreMetricsService`` — 18+ method overloads:

  - ``count(metricKey, amount?, tags?)`` — increment a counter.
  - ``countWithoutLogging(metricKey, tags)`` — counter without debug log.
  - ``count(successKey, failureKey, tags, function)`` — count success/failure
    of a ``Supplier<T>`` invocation.
  - ``summarize(metricKey, size, tags)`` — distribution summary.
  - ``histogram(metricKey, tags, function)`` — timed histogram.
  - ``gauge(metricKey, amount, tags)`` — set a gauge.
  - ``status(metricKey, tagsBuilder, function)`` — record status tag on outcome.
  - ``time(metricKey, duration, tags)`` — record a pre-measured duration.
  - ``timeAndCountResult(metricBase, tags, function)`` — time + success/fail
    counter.
  - ``timeFunction(metricBase, tags, function)`` — time a ``Supplier<T>``.

* ``MetricsService`` — 15+ typed overloads mirroring ``CoreMetricsService``
  but accepting ``MetricKey``, ``HistogramMetric``, ``ResultMetricBase``
  instead of raw ``MetricKeyLike``:

  - ``time(metricKey, duration, tags)``
  - ``timeAndHistogram(histogramMetric, duration, tags)``
  - ``timeFunction(resultMetricBase, tags, function)``
  - ``timeAndCountResult(resultMetricBase/metricKey, tags, function)``
  - ``histogram(histogramMetric, tags, function)``
  - ``gauge(metricKey, amount, tags)``

Enums & Value Types
-------------------

* ``MetricKey(val key: String) : MetricKeyLike`` — service-specific metric
  enum entries (extensible per-module).
* ``HistogramMetric(val metricKey: MetricKey, val histogramBucket: HistogramBucket)``
  — pairs a key with a bucket definition.
* ``ResultMetricBase(val base: String)`` — base name for ``.success`` /
  ``.failure`` suffixed metrics.
* ``HistogramBucket(val value: String)`` — bucket boundary label;
  ``metricTag(): Pair<String, String>``.
* ``Status(val value: String)`` — tag value for status-based metrics.

Implementation Classes
----------------------

* ``CoreMetricsServiceImpl`` (``@Component``, 436 LoC) — uses Micrometer
  ``MeterRegistry`` directly.  Handles:

  - Counter creation with tags.
  - ``Timer.record(duration)`` with tag lists.
  - ``DistributionSummary.record(size)`` for summarize.
  - ``Gauge.builder()`` for gauge registration.
  - ``Supplier<T>`` wrapping with try/catch for success/failure counting.
  - Debug-level logging of every metric emission (gated by logger level).

* ``MetricsServiceImpl`` (``@Component``, 358 LoC) — delegates all calls to
  ``CoreMetricsService``, translating typed keys to ``MetricKeyLike``.

Spring Component Annotations
=============================

=========================== =============
Bean                         Annotation
=========================== =============
``CoreMetricsServiceImpl``   ``@Component``
``MetricsServiceImpl``       ``@Component``
=========================== =============

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[Feature / Integration code] -->|metricsService.count, time, gauge| B["MetricsServiceImpl (typed facade)"]
       B -->|translates MetricKey to MetricKeyLike| C["CoreMetricsServiceImpl (raw facade)"]
       C --> D[MeterRegistry.counter]
       C --> E[MeterRegistry.timer]
       C --> F[MeterRegistry.summary]
       C --> G[MeterRegistry.gauge]
       D & E & F & G --> H["Micrometer backend
       (Datadog / Prometheus)"]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 50 20 30

   * - Property (application.yml)
     - Default
     - Description
   * - ``management.metrics.distribution.percentiles-histogram.http.server.requests``
     - ``true``
     - Enable percentile histograms
   * - ``management.metrics.distribution.slo.http.server.requests``
     - ``100ms,500ms,1s,2s,3s,4s,5s,10s,20s,120s``
     - SLO bucket boundaries
   * - ``management.metrics.tags.environment``
     - ``${MICROS_ENVTYPE}``
     - Common tag: environment type
   * - ``management.metrics.tags.region``
     - ``${MICROS_AWS_REGION}``
     - Common tag: AWS region
   * - ``management.metrics.tags.deployment_id``
     - ``${MICROS_DEPLOYMENT_ID}``
     - Common tag: deployment identifier

Testing Coverage
================

================================== ============================
Test class                          Subjects
================================== ============================
``CoreMetricsServiceImplTest``      Counter, timer, gauge, histogram operations
``MetricsServiceImplTest``          Delegation and key translation
================================== ============================

**Coverage: 2/2 implementation files** have dedicated unit tests.

**Precision note (fix 0-7):** Tests verify that metric values are recorded
with exact ``Double`` precision (e.g., ``amount = 1.5`` not truncated to
``1``).  The ``summarize`` and ``gauge`` methods accept ``Double`` parameters
throughout the chain, preserving sub-integer precision from call site to
Micrometer recording.

Dependencies
============

Inbound (consumed by)
---------------------

* ``interceptor`` — timing of request processing.
* ``client/identity`` — timing and counting of gatekeeper calls.
* ``feature/rovoinsights`` — insight generation metrics.
* ``integration/stratus`` — AI Gateway call metrics.
* ``integration/sqs`` — message processing metrics.
* ``integration/task`` — async task dispatch metrics.

Outbound (depends on)
---------------------

* Micrometer — ``MeterRegistry``, ``Counter``, ``Timer``,
  ``DistributionSummary``, ``Gauge``.
* ``logging`` — ``LaasLoggerFactory`` for debug-level metric logging.

Open Questions / Ambiguities
=============================

1. ``CoreMetricsService`` (149 LoC) and ``MetricsService`` (227 LoC) have
   significant API surface overlap — the two-layer design adds 580 LoC of
   delegation boilerplate.  Consider whether the typed layer provides
   sufficient value.
2. ``MetricKey`` is an enum but modules cannot add entries without modifying
   this file — sealed interface with per-module implementations would be
   more extensible.
3. ``CoreMetricsServiceImpl`` logs every metric emission at ``DEBUG`` level —
   in high-throughput paths this may impact performance even when debug
   logging is disabled (string formatting still occurs).
4. Histogram bucket definitions are embedded in ``HistogramBucket`` enum
   constants — no YAML override path for runtime tuning.
