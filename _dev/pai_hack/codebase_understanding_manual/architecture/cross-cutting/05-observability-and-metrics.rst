.. _pai-observability-and-metrics:

============================================================================
Observability — Metrics, Logging, Tracing
============================================================================

:Date: 2026-05-04

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Metrics (``service/metric/``)
===================================

PAI uses Micrometer 1.16.4 fronted by ``MetricsService`` (interface) and
``MetricsServiceImpl`` (impl). The bean wraps the Spring-injected ``MeterRegistry``
so every emit auto-tags with ``tenant_id``, ``account_id``, ``request_id``,
``environment``, ``deployment``.

The Micros observability sidecar ingests by prefix: only metrics named
``proactive-ai.*`` are forwarded to SignalFx. This is enforced in
``application.yml``.

1.1 The 5 emit verbs
----------------------

.. code-block:: kotlin

   metricsService.count(MetricKey.STREAMHUB_EVENT_PROCESSED, mapOf("event_type" to t))
   metricsService.time(MetricKey.LLM_LATENCY) { stratus.run(agent) }
   metricsService.timeAndHistogram(MetricKey.LLM_LATENCY) { ... }
   metricsService.timeAndCountResult(MetricKey.NUDGE_THROTTLE) { computeDecision() }
   metricsService.summarize(MetricKey.PAYLOAD_SIZE_BYTES, payload.size.toLong())

1.2 Histogram boundaries
--------------------------

Configured per-metric in ``application.yml`` (lines 17-19). Today the team uses
SignalFx's default boundary set; custom boundaries are added per-metric only when
the default set produces useless percentiles.

2. Logging (``logging/``)
============================

Every class should obtain its logger via ``LaasLoggerFactory.getLogger(class)``,
*not* SLF4J directly. The wrapper:

* Auto-merges MDC content with caller-supplied key-value pairs.
* Provides ``infoWithContext()``, ``warnWithContext()``, ``errorWithContext()``.
* Supports the ``WithUGCLogger`` flavour for fields known to contain
  user-generated content (Splunk-side redaction hooks).

2.1 Splunk index conventions
-------------------------------

Service logs go to the standard Atlassian micros Splunk index. Useful searches:

* ``index=micros service=proactive-ai-platform tenant_id=...``
* ``index=micros service=proactive-ai-platform request_id=...``
* ``... event_type=ROVO_INSIGHTS_GENERATION result=ERROR``

3. Tracing (Stratus + Micros sidecar)
========================================

PAI does not directly emit OpenTelemetry spans. Two indirect tracing sources:

* **Stratus SDK** — emits its own observability events via
  ``ObservabilityContext`` (registered in ``AIGatewayClientConfiguration.kt``)
  with namespace ``"proactive-ai"``. AI Gateway-side trace IDs propagate.
* **Micros sidecar** — every HTTP request gets an Atlassian trace_id which
  appears in MDC and in metric tags.

4. Test hooks
================

* ``InterceptedLogger`` lets tests assert which messages were logged with which
  context, without diving into Logback test appenders.
* ``MetricsServiceImplTest`` + ``CoreMetricsServiceImplTest`` verify the
  Micrometer adapter contract.

See :doc:`/modules/platform/service-metric` and :doc:`/modules/platform/logging`
for per-file detail.
