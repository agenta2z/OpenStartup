=====================================================
Module: ``sqs`` — SQS Event Consumption
=====================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Handles **inbound SQS message consumption** for analytics events from
StreamHub.  Provides:

* SQS queue consumer with conditional activation per worker-node type.
* Message routing by event type to specialised handlers.
* Middleware for consistent error handling and logging.
* Queue name constants and Spring configuration for the SQS framework.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``AnalyticsEnrichedEventHandler.kt``
     - 28
     - ``@Component`` — handles enriched analytics events
   * - ``AnalyticsEventsMessageQueueConsumer.kt``
     - 68
     - ``@Component`` — routes events to handlers by type
   * - ``AnalyticsEventsSqsQueueConsumer.kt``
     - 40
     - ``@Component`` — SQS consumer entry point
   * - ``EventAVIs.kt``
     - 11
     - Constants: analytics event AVI identifiers
   * - ``MessageQueueConsumerMiddleware.kt``
     - 36
     - ``@Component`` — error handling / logging wrapper
   * - ``QueueNames.kt``
     - 20
     - Constants: SQS queue name definitions
   * - ``SqsEventConsumerConfig.kt``
     - 123
     - ``@Configuration`` — SQS framework setup
   * - ``StreamHubEvent.kt``
     - 44
     - Data class: StreamHub event envelope

**Total: 8 files, ~370 LoC**

Class / Interface / Enum Catalog
================================

Configuration Classes
---------------------

* ``SqsEventConsumerConfig`` (``@Configuration``,
  ``@ConditionalOnProperty("proactive-ai.sqs.enabled")``,
  ``@EnableSqsQueues``, ``@ComponentScan``) — activates the SQS queue
  framework when SQS is enabled.

* ``CommonSqsConfig`` (``@Configuration``) — provides common beans:

  - ``@Bean fun appContextUtils(): AppContextUtils``
  - ``@Bean fun devLoggingUtils(): DevLoggingUtils``
  - ``@Bean @ConditionalOnMissingBean fun connectionFactory(client: SqsClient): ConnectionFactory``
    — **prefetch = 0** (critical for fair message distribution).
  - ``@Bean @ConditionalOnMissingBean fun queueDuplicateHandler(): NopDuplicateHandler``

Consumer Classes
----------------

* ``AnalyticsEventsSqsQueueConsumer`` (``@Component``,
  ``@Conditional(OnSHWorkerNodeOrLocalCondition)``,
  ``@ConditionalOnProperty("SQS_ANALYTICS_EVENTS_QUEUE_URL")``,
  ``@ManagedQueueConsumer(ANALYTICS_EVENTS_QUEUE)``) — extends
  ``SQSQueueConsumer<StreamHubEvent>``:

  - ``getConsumerDescription(): String``
  - Receives raw ``StreamHubEvent`` messages from SQS.

* ``AnalyticsEventsMessageQueueConsumer`` (``@Component``) — message router:

  - ``fun consume(event: StreamHubEvent)`` — routes by ``event.type``:
    - ``EventAVIs.ANALYTICS_ENRICHED_UI_CREATED`` → ``AnalyticsEnrichedEventHandler``

* ``AnalyticsEnrichedEventHandler`` (``@Component``) — processes enriched
  analytics events:

  - ``fun handle(event: StreamHubEvent)``

Middleware
----------

* ``MessageQueueConsumerMiddleware`` (``@Component``) — generic wrapper:

  - ``fun <T> consume(event: T, consumer: (T) -> Unit)`` — wraps consumer
    invocation with error handling and structured logging.

Data Classes
------------

* ``StreamHubEvent`` (``@JsonIgnoreProperties(ignoreUnknown = true)``) —
  event envelope:

  - ``type: String`` — event type AVI.
  - ``schema: String?`` — schema identifier.
  - ``schemaAri: String?`` — schema ARI.
  - ``resource: String?`` — resource identifier.
  - ``eventId: String?`` — unique event ID.
  - ``ingestionSource: String?`` — source system.
  - ``ingestionTime: String?`` — ingestion timestamp.
  - ``occurrenceTime: String?`` — event occurrence time.
  - ``eventProducer: String?`` — producer identifier.
  - ``payload: JsonNode?`` — raw event payload.

Constants
---------

* ``EventAVIs`` (object):

  - ``ANALYTICS_ENRICHED_UI_CREATED = "avi:analytics-enriched:created:ui"``

* ``QueueNames`` (package-level constants):

  - ``ANALYTICS_EVENTS_QUEUE = "analytics_events"``
  - ``ROVO_INSIGHTS_GENERATION_QUEUE = "rovo_insights_generation_queue"``

Spring Component Annotations
=============================

========================================= =====================================
Bean                                       Annotation
========================================= =====================================
``SqsEventConsumerConfig``                 ``@Configuration @EnableSqsQueues``
``CommonSqsConfig``                        ``@Configuration``
``AnalyticsEventsSqsQueueConsumer``        ``@Component @Conditional @ManagedQueueConsumer``
``AnalyticsEventsMessageQueueConsumer``    ``@Component``
``AnalyticsEnrichedEventHandler``          ``@Component``
``MessageQueueConsumerMiddleware``         ``@Component``
========================================= =====================================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["StreamHub (upstream)"] -->|publishes analytics events| B["SQS: analytics_events queue
       (prefetch = 0)"]
       B --> C["AnalyticsEventsSqsQueueConsumer
       (SH worker node only)"]
       C -->|deserialise StreamHubEvent| D[MessageQueueConsumerMiddleware]
       D -->|try/catch + structured logging| E[AnalyticsEventsMessageQueueConsumer]
       E -->|route by event.type| F{event.type?}
       F -->|"avi:...created:ui"| G[AnalyticsEnrichedEventHandler.handle]
       F -->|unknown type| H[Log + skip]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 45 20 35

   * - Property
     - Default
     - Description
   * - ``proactive-ai.sqs.enabled``
     - (not set → true)
     - Gates entire SQS consumer framework
   * - ``SQS_ANALYTICS_EVENTS_QUEUE_URL``
     - env var
     - Queue URL; gates consumer activation
   * - ``SQS_ANALYTICS_EVENTS_QUEUE_NAME``
     - env var
     - Queue name for Micros SQS framework
   * - ``atlassian.sqs.properties.concurrency``
     - ``2-8``
     - Consumer thread pool range
   * - ``atlassian.sqs.properties.auto-lifecycle-management-disabled``
     - ``false``
     - Disables auto-start/stop
   * - ``atlassian.sqs.properties.enable-auto-startup``
     - ``false``
     - Disables auto-startup on context refresh
   * - ``atlassian.sqs.region``
     - ``${MICROS_AWS_REGION:us-east-1}``
     - AWS region for SQS

Testing Coverage
================

============================================= ====== ============================
Test class                                     Lines  Subjects
============================================= ====== ============================
``AnalyticsEventsMessageQueueConsumerTest``     116   Event routing, unknown types
``CommonSqsConfigTest``                         65    Bean creation, prefetch=0
============================================= ====== ============================

**Coverage: 2 test files** covering the router and config.

**Gaps:**

* ``AnalyticsEnrichedEventHandler`` — no dedicated test.
* ``MessageQueueConsumerMiddleware`` — no test for error handling paths.
* ``AnalyticsEventsSqsQueueConsumer`` — no test for deserialization.

Dependencies
============

Inbound (consumed by)
---------------------

* ``feature/rovoinsights`` — imports ``QueueNames.ROVO_INSIGHTS_GENERATION_QUEUE``
  and ``VisibilityExtendingSQSQueueConsumer`` (from ``task`` module, related).

Outbound (depends on)
---------------------

* Atlassian SQS Starter — ``@EnableSqsQueues``, ``@ManagedQueueConsumer``,
  ``SQSQueueConsumer``, ``ConnectionFactory``, ``NopDuplicateHandler``.
* ``config`` — ``OnSHWorkerNodeOrLocalCondition`` for consumer gating.
* ``requestcontext`` — ``LoggingContext`` for structured logging in middleware.
* Jackson — ``@JsonIgnoreProperties``, ``JsonNode`` for event payload.
* AWS SDK — ``SqsClient`` for connection factory.

Open Questions / Ambiguities
=============================

1. ``connectionFactory`` sets **prefetch = 0** — this is critical for fair
   message distribution but may impact throughput; document the trade-off
   and link to the related pipeline task (OPP9).
2. ``enable-auto-startup = false`` — consumers must be started manually or
   by Micros lifecycle management; verify that ``auto-lifecycle-management-disabled = false``
   handles this correctly.
3. Only one event type (``ANALYTICS_ENRICHED_UI_CREATED``) is handled —
   the router silently drops unknown types; add metrics for dropped events.
4. ``StreamHubEvent.payload`` is ``JsonNode?`` — no type-safe deserialization
   of the payload; each handler must parse it independently.
5. ``QueueNames.kt`` defines both ``ANALYTICS_EVENTS_QUEUE`` and
   ``ROVO_INSIGHTS_GENERATION_QUEUE`` — the latter is consumed by the
   ``task`` module, creating a cross-module dependency through constants.
