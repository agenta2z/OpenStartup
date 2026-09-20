.. _pai-platform-sqs:

============================================================================
``sqs`` — StreamHub event consumer + middleware
============================================================================

:Date: 2026-05-04
:Files: 8 main / 1 test
:Importance: **P1 — feeds nudge-throttle inputs**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Drains the ``analytics_events`` SQS queue (StreamHub events from GASv3) on
SHWorkers pods and provides the common ``MessageQueueConsumerMiddleware``
reused by both StreamHub consumers and AsyncTask queue consumers.

Two responsibilities:

1. **StreamHub event pipeline** — receives enriched analytics events, routes
   them to handlers, emits processing metrics.
2. **Consumer middleware** — wraps every SQS consumer with request-scoped
   value setup/teardown and MDC clearing.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``StreamHubEvent.kt``
     - ~30
     - JSON-deserialisable event envelope
   * - ``EventAVIs.kt``
     - ~5
     - AVI (Analytics Versioned Identifier) constants
   * - ``MessageQueueConsumerMiddleware.kt``
     - ~25
     - Common request-context lifecycle for all SQS consumers
   * - ``SqsEventConsumerConfig.kt``
     - ~10
     - ``@EnableSqsQueues`` bean
   * - ``AnalyticsEventsMessageQueueConsumer.kt``
     - ~40
     - Routes incoming ``StreamHubEvent`` to handler; emits metrics
   * - ``AnalyticsEventsSqsQueueConsumer.kt``
     - ~25
     - SQS listener; activated by ``OnSHWorkerNodeOrLocalCondition``
   * - ``AnalyticsEnrichedEventHandler.kt``
     - ~30
     - Per-event handler (today: log + metric)
   * - ``internal/`` (1 file)
     - ~20
     - Helpers

3. Key classes deep dive
===========================

``StreamHubEvent`` (data class)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @JsonIgnoreProperties(ignoreUnknown = true)
   data class StreamHubEvent(
       val type: String,
       val schema: String?,
       val schemaAri: String?,
       val resource: String?,
       val eventId: String,
       val ingestionSource: String?,
       val ingestionTime: ZonedDateTime?,
       @JsonProperty("time") val occurrenceTime: ZonedDateTime?,
       val eventProducer: String?,
       val payload: JsonNode,           // opaque — handler interprets
   )

Generic event envelope from StreamHub. The ``payload`` is a raw ``JsonNode``
because different event types carry different schemas — the handler parses it.

``EventAVIs`` (object)
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   object EventAVIs {
       const val ANALYTICS_ENRICHED_UI_CREATED = "avi:analytics-enriched:created:ui"
   }

AVI constants for routing. New event types require a new constant here.

``MessageQueueConsumerMiddleware``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Component
   class MessageQueueConsumerMiddleware(
       private val requestScopedValuesInitter: RequestScopedValuesInitter,
       private val loggingContext: LoggingContext,
   ) {
       fun <T> consume(event: T, consumer: (T) -> Unit) {
           try {
               requestScopedValuesInitter.initRequestScopedValuesAndRun {
                   consumer(event)
               }
           } finally {
               loggingContext.clear()
           }
       }
   }

This middleware is the **SQS equivalent** of the HTTP interceptor chain:

1. Sets up request-scoped values (same as ``RequestContextInterceptor``)
2. Runs the consumer with those values available
3. Clears MDC in ``finally`` (same as ``LoggingContextClearingFilter``)

Both StreamHub consumers and AsyncTask consumers use this middleware, ensuring
consistent context lifecycle regardless of entry point.

4. StreamHub pipeline
========================

::

   GASv3 → StreamHub → SQS (analytics_events queue)
     │
     ▼
   AnalyticsEventsSqsQueueConsumer
     │  [SHWorkers pod only — OnSHWorkerNodeOrLocalCondition]
     │
     ▼
   MessageQueueConsumerMiddleware.consume()
     │  • requestScopedValuesInitter.initRequestScopedValuesAndRun {}
     │  • finally { loggingContext.clear() }
     │
     ▼
   AnalyticsEventsMessageQueueConsumer
     │  • Parse StreamHubEvent from SQS message
     │  • loggingContext.addStreamHubEventInfo(eventId, type, ...)
     │  • Route to handler by event type
     │  • Emit MetricKey.STREAMHUB_EVENT_PROCESSED / _UNSUPPORTED / _ERROR
     │
     ▼
   AnalyticsEnrichedEventHandler
     │  • Today: log event + emit metric
     │  • Planned: write nudge signal to Redis for throttle consumption

5. Configuration
==================

Queue URLs are passed via environment variables (``SQS_*_QUEUE_URL``) and read
in ``application.yml``. The ``atlassian-spring-boot-sqs-starter`` handles
auto-wiring; PAI just provides the consumer beans and the
``@EnableSqsQueues`` annotation in ``SqsEventConsumerConfig``.

6. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``AnalyticsEventsMessageQueueConsumerTest``
     - Event routing, middleware integration, metric emission, error handling

7. Design decisions
======================

1. **Conditional activation** — ``OnSHWorkerNodeOrLocalCondition`` ensures
   consumers only run on SHWorkers pods (or local dev). WebServer pods never
   activate the consumer bean, preventing resource contention.
2. **Shared middleware** — ``MessageQueueConsumerMiddleware`` is used by both
   StreamHub and AsyncTask consumers, ensuring consistent MDC lifecycle.
3. **Opaque payload** — ``StreamHubEvent.payload`` is ``JsonNode`` rather than
   a typed class because different event types carry different schemas.
4. **Metric-per-event** — every processed event emits a metric
   (``STREAMHUB_EVENT_PROCESSED`` / ``_UNSUPPORTED`` / ``_ERROR``) enabling
   SRE monitoring of event pipeline health.

8. See also
==============

* :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs` §2 — StreamHub
  consumer pipeline detail
* :doc:`/modules/platform/task` — AsyncTask consumer (shares middleware)
* :doc:`/modules/platform/requestcontext` — request-scoped values and MDC API
* :doc:`/modules/features/nudge` — downstream consumer of StreamHub signals
