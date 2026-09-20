.. _telemetry:

============================
Observability & Telemetry
============================

The platform emits **structured logs**, **metrics**, and **OTel traces**. All three integrate with Atlassian's internal observability stack (LaaS for logs, SignalFx for metrics, ZipKin/Jaeger for traces).

Three pillars
==============

Logs
-----

- **Library:** SLF4J + Logback
- **Factory:** ``LaasLoggerFactory`` (in ``foundation/utilities/logging/``)
- **Format:** Structured JSON (LaaS-native format)
- **MDC keys:** cloud_id, requestId, agentId, experienceId, channelId, traceId
- **Coroutine-safe:** via ``MdcLoggingContext`` (snapshots MDC, restores after suspend)

Verified pattern at ``ChatV1Controller.kt:209-212``:

.. code-block:: kotlin

   log.infoWithContext(
       "Received /chat/v1/channel/{channelId}/message/stream request",
       streamLoggingContext,
   )

The ``infoWithContext`` extension augments MDC with the per-call context map for that one log line.

Metrics
--------

- **Library:** Micrometer + OTel
- **Tag service:** ``PlatformMetricTagsService`` (in ``foundation/utilities/metrics/``)
- **Standard tags:** cloud_id, product, experience_id, use_case_id, model, provider
- **Cardinality controls:** built into the tag service (drops or buckets high-cardinality values)

Per AGENTS.md context, every LLM call emits at minimum:
- ``llm.request.count`` (incr)
- ``llm.request.duration`` (histogram)
- ``llm.tokens.prompt`` (gauge/counter)
- ``llm.tokens.completion`` (gauge/counter)
- ``llm.error.count`` (incr, tagged by error type)

Traces
-------

- **Library:** OpenTelemetry SDK
- **Setup:** ``ContextPropagationInitializer`` (in ``modules/service/convo-ai-docker-image``) installs OTel context propagation hooks at app start
- **Coroutine-safe:** the initializer ensures coroutine context carries OTel trace
- **Export:** OTel agent (running as a Java agent or as a sidecar) ships spans to the central collector

Span attributes typically include:
- ``http.method``, ``http.url``
- ``cloud.id``, ``user.id`` (when present)
- ``llm.model``, ``llm.provider``
- ``conversation.id``, ``message.id``

Per ``AIGatewayClientServiceImpl.kt:755`` (verified): ``"Extracts span attributes using the provided extractor function."`` — confirms OTel span attributes are extracted from request context.

Patterns
=========

1. **Structured logging.** Never use string interpolation for log messages — use ``log.info("event", contextMap)`` form so LaaS can index the keys.

2. **MDC over per-line context when possible.** If a value applies to many log lines, set it via MDC once instead of passing in every map.

3. **Span-per-LLM-call.** Every AI Gateway call gets its own span with attributes (model, tokens, latency). This is the primary tool for diagnosing slow conversations.

4. **Per-tenant cardinality control.** Cloud IDs are bounded (millions, but accepted). User IDs and message IDs are NOT tagged on metrics (cardinality blowup risk).

5. **Trace propagation via headers.** When calling AI Gateway, OTel injects ``traceparent`` and ``tracestate`` headers so the gateway and provider can continue the trace.

What you would change here
===========================

- **Add a metric** → register MetricDef in the relevant module's ``...Metrics.kt``; emit via Micrometer Registry
- **Add a span** → wrap the work in a ``tracer.spanBuilder("name").startSpan()`` or use ``@WithSpan`` annotation
- **Add an MDC key** → modify ``MdcLoggingContext`` snapshot list AND set it at the appropriate filter/controller

What you would NOT change here
===============================

- LaaS logger configuration (managed by the deploy descriptor + LaaS team)
- OTel exporter (managed by the OTel agent + Atlassian observability platform)

