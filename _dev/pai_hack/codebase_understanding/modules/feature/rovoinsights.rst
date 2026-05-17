=====================================================
Module: ``rovoinsights`` — Rovo Insights Generation
=====================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Implements the **Rovo Insights** feature — AI-generated summaries, follow-ups,
and team activity insights delivered proactively to users.  The module covers:

* REST API for querying insight status and fetching generated insights.
* Async task submission for insight generation.
* SQS consumer for long-running generation jobs.
* Domain model for insight types, colours, glyphs, and prompt configuration.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``Config.kt``
     - 45
     - Default prompt versions and config map
   * - ``RovoInsightsGenerationTask.kt``
     - 9
     - ``AsyncTask`` data class for SQS dispatch
   * - ``RovoInsightsGenerationTaskHandler.kt``
     - 62
     - ``@Component`` — handles generation task execution
   * - ``api/RovoInsightsController.kt``
     - 50
     - ``@RestController`` — status & fetch endpoints
   * - ``api/dto/RovoInsightsTestRequest.kt``
     - 3
     - Empty request DTO for test endpoint
   * - ``api/dto/RovoInsightsTestResponse.kt``
     - 5
     - Response DTO with ``taskId``
   * - ``api/fetch/RovoInsightsFetchRequest.kt``
     - 14
     - Fetch request: ``generate``, ``debugInfo``, ``promptConfig``
   * - ``api/fetch/RovoInsightsFetchResponse.kt``
     - 77
     - Response: insights, groups, debug info
   * - ``api/rest/RovoInsightsTestController.kt``
     - 82
     - ``@RestController`` — test/trigger endpoint (conditional)
   * - ``api/status/RovoInsightsStatusRequest.kt``
     - 14
     - Status request: ``promptConfig``, ``forceCacheMiss``
   * - ``api/status/RovoInsightsStatusResponse.kt``
     - 9
     - Status response: ``insightsAvailable: Boolean``
   * - ``internal/RovoInsightsGenerationSqsQueueConsumer.kt``
     - 122
     - ``@Component`` — SQS consumer extending ``VisibilityExtendingSQSQueueConsumer``
   * - ``system/Color.kt``
     - 34
     - Enum: 20 colour constants for insight rendering
   * - ``system/Glyph.kt``
     - 49
     - Enum: 35 glyph/icon constants
   * - ``system/InsightType.kt``
     - 52
     - Enum: 6 insight categories with icon/colour/title
   * - ``system/RovoInsightsRequest.kt``
     - 31
     - ``Strategy`` enum, ``RovoInsightsPromptConfig`` data class, ``PromptConfig`` type alias

**Total: 16 files, ~658 LoC**

Class / Interface / Enum Catalog
================================

REST Controllers
----------------

* ``RovoInsightsController`` (``@RestController``,
  ``@RequestMapping("/api/v1/rovo/insights")``) — production endpoints:

  - ``POST /status`` → ``postRovoInsightsStatus(RovoInsightsStatusRequest): RovoInsightsStatusResponse``
  - ``POST /fetch`` → ``postRovoInsightsFetch(RovoInsightsFetchRequest): RovoInsightsFetchResponse``

* ``RovoInsightsTestController`` (``@RestController``,
  ``@RequestMapping("/api/v1/rovo-insights")``,
  ``@ConditionalOnProperty("proactive-ai.sqs.enabled")``) — test/trigger:

  - ``POST /`` → ``generate(cloudId, requestId?, user, body?): RovoInsightsTestResponse``
    (``@ResponseStatus(ACCEPTED)``)

Task Classes
------------

* ``RovoInsightsGenerationTask`` (``@JsonTypeName("rovo_insights_generation")``,
  ``data class``) — implements ``AsyncTask``; carries ``cloudId: String``.

* ``RovoInsightsGenerationTaskHandler`` (``@Component``) — implements
  ``AsyncTaskHandler<RovoInsightsGenerationTask>``:

  - ``val queueName = ROVO_INSIGHTS_GENERATION_QUEUE``
  - ``suspend fun handle(context, task)`` — executes insight generation.
  - ``suspend fun onSuccess(context, task)`` — post-generation cleanup.
  - ``suspend fun onFailure(context, task, error)`` — error handling.

SQS Consumer
-------------

* ``RovoInsightsGenerationSqsQueueConsumer`` (``@Component``,
  ``@Conditional(OnLongRunWorkerNodeOrLocalCondition)``,
  ``@ConditionalOnProperty("SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL")``,
  ``@ManagedQueueConsumer(ROVO_INSIGHTS_GENERATION_QUEUE)``) — extends
  ``VisibilityExtendingSQSQueueConsumer<JsonNode>``:

  - ``getConsumerDescription(): String``
  - ``internal fun processMessage(jsonNode: JsonNode)`` — deserialises and
    dispatches to ``AsyncTaskDispatcher``.

Domain Model (``system/``)
--------------------------

* ``Color`` (enum, 20 entries) — ``GRAY``, ``BLUE``, ``TEAL``, ``GREEN``,
  ``LIME``, ``YELLOW``, ``ORANGE``, ``RED``, ``MAGENTA``, ``PURPLE``, plus
  ``*_BOLD`` variants.  Uses ``@JsonValue`` for serialisation.

* ``Glyph`` (enum, 35 entries) — icon identifiers: ``ALERT``, ``AUTOMATION``,
  ``BOOK_WITH_BOOKMARK``, ``BRIEFCASE``, ``CALENDAR``, ``CHART_BAR``,
  ``CHART_TREND``, ``CHART_TREND_UP``, ``CHECK_CIRCLE``, ``CLOCK``,
  ``COMMENT``, ``COMPASS``, ``DASHBOARD``, ``DEPARTMENT``, ``EYE_OPEN``,
  ``FLAG``, ``GLOBE``, ``GOAL``, ``LIGHTBULB``, ``LINK``, ``MEGAPHONE``,
  ``OFFICE_BUILDING``, ``PEOPLE_GROUP``, ``PERSON``, ``PRIORITY_HIGH``,
  ``QUESTION_CIRCLE``, ``SPRINT``, ``STAR_STARRED``, ``STATUS_WARNING``,
  ``STOPWATCH``, ``TARGET``, ``TASK``, ``TEAMS``, ``THUMBS_UP``, ``WARNING``.

* ``InsightType`` (enum, 6 entries) — each carries ``value``, ``icon`` (Glyph),
  ``color`` (Color), ``groupTitle``:

  - ``FOLLOW_UP_INSIGHTS``
  - ``EMERGING_WITH_YOUR_TEAM``
  - ``COMPANY_INSIGHTS``
  - ``YOUR_TRENDING_WORK``
  - ``RECOGNITION_INSIGHTS``
  - ``MEETING_INSIGHTS``

* ``Strategy`` (enum) — ``EVALUATE``, ``SKIP`` — controls prompt evaluation.

* ``RovoInsightsPromptConfig`` (data class) — ``strategy``, prompt parameters.

* ``PromptConfig`` (type alias) — ``Map<InsightType, RovoInsightsPromptConfig>``.

Response Models (``api/fetch/``)
--------------------------------

* ``PersonReference`` — ``accountId``, ``name``.
* ``RovoInsight`` — individual insight with ``title``, ``body``, ``type``,
  ``personReferences``, etc.
* ``DebugInfo`` — generation metadata for debugging.
* ``RovoInsightsGroup`` — group of insights with ``type``, ``title``, ``insights``.
* ``RovoInsightsFetchResponse`` — ``groups: List<RovoInsightsGroup>``,
  ``debugInfo?``.  Companion: ``const val DATA_SCHEMA_VERSION = 3``.

Spring Component Annotations
=============================

=========================================== =====================================
Bean                                         Annotation
=========================================== =====================================
``RovoInsightsController``                   ``@RestController``
``RovoInsightsTestController``               ``@RestController @ConditionalOnProperty``
``RovoInsightsGenerationTaskHandler``        ``@Component``
``RovoInsightsGenerationSqsQueueConsumer``   ``@Component @Conditional @ManagedQueueConsumer``
=========================================== =====================================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       subgraph Test Path
           A1["Client (test trigger)
           POST /api/v1/rovo-insights"] --> B1[RovoInsightsTestController]
           B1 -->|AsyncTaskService.enqueueTask| C1[SQS: rovo_insights_generation_queue]
       end
       subgraph Production Path
           A2["Client (production)
           POST /api/v1/rovo/insights/status or fetch"] --> B2[RovoInsightsController]
           B2 -->|check cache| D2[Return status/fetch response]
       end
       C1 --> E["RovoInsightsGenerationSqsQueueConsumer
       (LongRun worker node)"]
       E -->|deserialise JSON| F[AsyncTaskDispatcher.dispatch]
       F --> G[RovoInsightsGenerationTaskHandler.handle]
       G -->|generate insights via AI Gateway| H[Store results]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 45 20 35

   * - Property
     - Default
     - Description
   * - ``proactive-ai.sqs.enabled``
     - ``true``
     - Gates ``RovoInsightsTestController`` activation
   * - ``SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL``
     - env var
     - SQS queue URL; gates consumer activation
   * - ``SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_NAME``
     - env var
     - SQS queue name for Micros SQS framework

Testing Coverage
================

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - Test class
     - Lines
     - Subjects
   * - ``RovoInsightsGenerationTaskHandlerTest``
     - —
     - Task handler lifecycle
   * - ``RovoInsightsGenerationSqsQueueConsumerTest``
     - 201
     - Message processing, dispatch
   * - ``RovoInsightsControllerIT``
     - —
     - Integration test for REST API

**Coverage: 3 test files** covering handler, consumer, and REST API.

Dependencies
============

Inbound (consumed by)
---------------------

* External clients (Rovo UI) call the REST endpoints.

Outbound (depends on)
---------------------

* ``integration/task`` — ``AsyncTask``, ``AsyncTaskHandler``,
  ``AsyncTaskService``, ``AsyncTaskDispatcher``.
* ``integration/sqs`` — ``VisibilityExtendingSQSQueueConsumer``,
  ``QueueNames.ROVO_INSIGHTS_GENERATION_QUEUE``.
* ``config`` — ``OnLongRunWorkerNodeOrLocalCondition`` for consumer gating.
* ``utility/user`` — ``User`` interface for task execution context.
* ``context`` — cloud-id from ``TenantContext``.
* Jackson — ``@JsonTypeName``, ``@JsonProperty``, ``@JsonValue``,
  ``@JsonInclude``.
* Swagger — ``@Operation``, ``@Schema`` annotations.

Open Questions / Ambiguities
=============================

1. ``RovoInsightsTestController`` is conditionally activated by
   ``proactive-ai.sqs.enabled`` — if SQS is disabled in an environment,
   the test trigger endpoint is unavailable, but the production
   status/fetch endpoints remain active.
2. ``DATA_SCHEMA_VERSION = 3`` in ``RovoInsightsFetchResponse`` — no
   migration path documented for schema version changes.
3. ``Config.kt`` defines ``DEFAULT_ROVO_INSIGHTS_PROMPT_CONFIG`` as a
   compile-time map — prompt configuration changes require redeployment.
4. ``RovoInsightsGenerationSqsQueueConsumer`` processes ``JsonNode`` rather
   than typed messages — deserialization failures are handled at runtime
   rather than compile time.
5. The ``/status`` and ``/fetch`` endpoints share the same base path but
   have different semantics — ``/status`` is idempotent, ``/fetch`` may
   trigger generation; the naming could be clearer.
