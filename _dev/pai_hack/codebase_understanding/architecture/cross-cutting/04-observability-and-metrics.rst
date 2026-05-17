=====================================
04 — Observability & Metrics
=====================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

Proactive-AI-Platform employs a layered observability stack:

1. **Structured metrics** via Micrometer → SignalFX, accessed through a
   two-tier service (``CoreMetricsService`` → ``MetricsService``).
2. **Structured logging** via SLF4J / Logback with the LAAS (Logging-As-A-
   Service) pipeline, wrapped by the custom ``LaasLogger`` hierarchy.
3. **Distributed tracing** via OpenTelemetry, with trace/span IDs injected
   into the MDC by ``LoggingContextClearingFilter``.

Metric Key Inventory
--------------------

The ``MetricKey`` enum defines **7 entries** (6 pure counters + 1 dual-use
counter/histogram):

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - MetricKey
     - Stat Type
     - Description
   * - ``PROACTIVE_TEST_COUNT``
     - Counter
     - Incremented by the ``/greetings`` test endpoint to verify the metrics
       pipeline.  Key: ``test.count``.
   * - ``PROACTIVE_TEST_LATENCY``
     - **Dual-use** (counter + histogram)
     - Recorded as a timing metric *and* registered in ``HistogramMetric``
       with ``PROACTIVE_HISTOGRAM_BUCKETS``.  Key: ``test.latency``.
   * - ``TENANT_CONTEXT_BUILD_SUCCESS``
     - Counter
     - Emitted when tenant-context hydration completes successfully.
       Key: ``tenant.context.build.success``.
   * - ``TENANT_CONTEXT_BUILD_ERROR``
     - Counter
     - Emitted when tenant-context hydration fails.
       Key: ``tenant.context.build.error``.
   * - ``STREAMHUB_EVENT_PROCESSED``
     - Counter
     - Emitted for every StreamHub event received, tagged with ``avi``.
       Key: ``streamhub.event.processed``.
   * - ``STREAMHUB_EVENT_UNSUPPORTED``
     - Counter
     - Emitted when a StreamHub event has an unrecognised AVI type.
       Key: ``streamhub.event.unsupported``.
   * - ``STREAMHUB_EVENT_ERROR``
     - Counter
     - Emitted when StreamHub event processing throws, tagged with ``avi``
       and ``error``.  Key: ``streamhub.event.error``.

Supporting Metric Types
^^^^^^^^^^^^^^^^^^^^^^^

``ResultMetricBase``
    Convention enum for operation-result metrics that auto-generate
    ``.latency``, ``.success``, and ``.error`` suffixed keys.  Currently
    contains one entry: ``ERS_CREATE`` (``ers.create``).

``HistogramMetric``
    Maps a ``MetricKey`` to a ``HistogramBucket``.  Currently only
    ``PROACTIVE_TEST_LATENCY`` is registered, with buckets at 200, 500,
    1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000 ms.
    Histogram metrics are emitted with a ``.hist`` suffix and the
    ``gsd_histogram`` tag.

``Status``
    Two-valued enum (``SUCCESS`` / ``ERROR``) used as a tag value for
    result-counting wrappers.

Metrics Service Architecture
-----------------------------

Two-tier design
^^^^^^^^^^^^^^^

.. code-block:: text

   ┌────────────────────┐
   │   MetricsService   │  ← feature-level API (adds rovo/product tags)
   │  (MetricsServiceImpl)│
   └────────┬───────────┘
            │ delegates
   ┌────────▼───────────┐
   │ CoreMetricsService │  ← low-level API (direct MeterRegistry calls)
   │(CoreMetricsServiceImpl)│
   └────────────────────┘

**CoreMetricsService** (17 method overloads):
   Direct wrapper around Micrometer's ``MeterRegistry``.  Provides:
   ``count``, ``countWithoutLogging``, ``summarize``, ``gauge``, ``time``,
   ``histogram``, ``status``, ``timeAndCountResult``, ``timeFunction``.
   All methods accept ``MetricKeyLike`` (interface with a ``key: String``
   property) plus optional tags.

**MetricsService** (14 method overloads):
   Higher-level API that enriches tags with product/tenant context before
   delegating to ``CoreMetricsService``.  Adds convenience wrappers like
   ``timeAndHistogram`` (records both a timing metric and a histogram in a
   single call) and ``countResult`` (wraps a function, emitting separate
   success/failure counters).

Common Tags (application.yml)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   micros.metrics.tags.common:
     - environment
     - environment_type
     - region
     - deployment_id

HTTP server request histogram boundaries are configured at:
100 ms, 500 ms, 1 s, 2 s, 3 s, 4 s, 5 s, 10 s, 20 s, 120 s.

Thread-Pool Monitoring
^^^^^^^^^^^^^^^^^^^^^^

``WebMvcConfiguration`` registers an ``ExecutorServiceMetrics`` monitor for the
async WebMVC executor with prefix ``proactive-ai.async.webmvc-exc`` and
tag ``threadPoolType=async.webmvc-exc``.

Instrumentation Patterns
------------------------

Count-and-rethrow
^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   metricsService.count(MetricKey.STREAMHUB_EVENT_PROCESSED, "avi" to event.type)
   // … processing …
   metricsService.count(MetricKey.STREAMHUB_EVENT_ERROR,
       listOf("avi" to event.type, "error" to e.javaClass.simpleName))
   throw e

Used in ``AnalyticsEventsMessageQueueConsumer``.  The error counter includes
the exception class name for SignalFX grouping.

Time-and-count-result
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   coreMetricsService.timeAndCountResult(metricBase, tags) {
       riskyOperation()
   }

Automatically records ``<base>.latency``, ``<base>.success``, or
``<base>.error`` depending on the outcome.

Status wrapper
^^^^^^^^^^^^^^

.. code-block:: kotlin

   coreMetricsService.status(metricKey, { listOf("tag" to "value") }) {
       operation()
   }

Emits a status tag (``success`` / ``error``) on the given metric key,
driven by whether the supplier throws.

Logging Architecture
--------------------

Class Hierarchy
^^^^^^^^^^^^^^^

.. code-block:: text

   org.slf4j.Logger
       └── InterceptedLogger          (abstract, wraps SLF4J Logger with an interceptor lambda)
               ├── LaasLogger          (identity interceptor — pass-through logging)
               │       ├── .withUGC()  → WithUGCLogger  (sets MDC env_suffix=unsafe, truncates at 10 000 chars)
               │       └── .withUGC()  → NoopLogger     (all isXxxEnabled() → false, interceptor = no-op)
               └── WithUGCLogger       (MDC-setting interceptor for UGC-containing log lines)

**LaasLogger**
   Created via ``LaasLoggerFactory.getLogger(clazz)``.  The main logger used
   throughout the codebase.  Provides a ``.withUGC(featureService)`` method
   that returns either ``WithUGCLogger`` (when ``ENABLE_UGC_LOGGING`` gate is
   on) or ``NoopLogger`` (when off).

**WithUGCLogger**
   Intercepts every log call to:

   1. Set ``MDC["env_suffix"] = "unsafe"`` before the log call.
   2. Truncate messages exceeding 10 000 characters.
   3. Remove the MDC key in a ``finally`` block.

   This ensures UGC-containing lines are routed to the ``unsafe`` LAAS
   environment, satisfying Atlassian privacy policy.

**NoopLogger**
   Returns ``false`` for all ``isXxxEnabled()`` checks, causing SLF4J callers
   to skip message formatting entirely — zero overhead when UGC logging is
   disabled.

Structured Logging Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``LoggerExtensions.kt`` provides four extension functions on ``Logger``:

- ``debugWithContext(message, ctx, exception?)``
- ``infoWithContext(message, ctx, exception?)``
- ``warnWithContext(message, ctx, exception?)``
- ``errorWithContext(message, ctx, exception?)``

Each wraps the ``ctx: Map<String, Any?>`` into Logstash
``StructuredArguments.entries()`` with a ``ctx.`` key prefix, producing
JSON-structured log fields for downstream querying.

MDC / Logging Context
^^^^^^^^^^^^^^^^^^^^^

``LoggingContextClearingFilter`` (order ``HIGHEST_PRECEDENCE + 4``):

- Extracts ``experimentId`` from OpenTelemetry Baggage into MDC.
- Injects ``trace_id``, ``span_id``, ``trace_sampled`` from the current
  ``Span``.
- Clears the entire ``LoggingContext`` in its ``finally`` block, ensuring no
  request state leaks across pooled threads.
