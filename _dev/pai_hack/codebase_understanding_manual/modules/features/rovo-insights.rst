.. _pai-feature-rovo-insights:

============================================================================
``feature/rovoinsights`` — Async insight generation
============================================================================

:Date: 2026-05-04
:Files: 12 main + (planned) tests
:Importance: **P0 — highest-impact contributor to the FY26 H2 OKR**
:Strategic role: User-facing AI feature; async generation pipeline

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

A user-facing AI feature that produces actionable workspace-level insights
(Jira issues at risk, stale Confluence pages, etc.). The interaction model
is **async submit-poll-fetch**:

1. User clicks a button → PAI returns immediately with a ``taskId`` (HTTP 202).
2. User polls ``/status`` until ``insightsAvailable == true`` (typically 5–30 s).
3. User fetches the insight bundle via ``/fetch``.

This is the most complex feature in the codebase. It exercises the full platform
stack: REST controllers, async task framework, SQS queues, visibility-extension
pattern, Stratus/AI Gateway agent, MCP tool discovery, and Redis caching.

2. Public API
================

Three REST endpoints:

.. list-table::
   :header-rows: 1
   :widths: 10 38 52

   * - HTTP
     - Path
     - Purpose
   * - POST
     - ``/api/v1/rovo-insights/generate``
     - Submit generation request → ``{taskId}`` (HTTP 202)
   * - POST
     - ``/api/v1/rovo/insights/status``
     - Poll availability → ``{insightsAvailable: Boolean}``
   * - POST
     - ``/api/v1/rovo/insights/fetch``
     - Retrieve insight bundle once ready

2.1 ``/generate``
-------------------

* **Headers** (required): ``atl-cloud-id``, SLAuth user-context
* **Headers** (optional): ``x-request-id`` (PAI generates one if absent)
* **Body**: ``RovoInsightsTestRequest`` (currently empty — cloud_id from header)
* **Response**: ``202 ACCEPTED``

.. code-block:: json

   { "taskId": "uuid-string" }

2.2 ``/status``
-----------------

* **Body**: ``RovoInsightsStatusRequest``
* **Response**: ``200 OK``

.. code-block:: json

   { "insightsAvailable": true }

2.3 ``/fetch``
----------------

* **Body**: ``RovoInsightsFetchRequest``
* **Response**: ``200 OK``

.. code-block:: json

   {
     "schemaVersion": "1.0",
     "generatedAt": "2026-05-04T12:00:00Z",
     "count": 5,
     "summary": "5 insights generated for your workspace",
     "insightGroups": [
       {
         "title": "Issues at Risk",
         "insights": [
           { "title": "PROJ-123 overdue", "severity": "HIGH" }
         ]
       }
     ]
   }

3. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``api/rest/RovoInsightsTestController.kt``
     - ~60
     - ``/generate`` endpoint; submits to SQS
   * - ``api/RovoInsightsController.kt``
     - ~50
     - ``/status`` and ``/fetch``; reads from Redis
   * - ``api/dto/RovoInsightsTestRequest.kt``
     - ~5
     - Empty request DTO for ``/generate``
   * - ``api/dto/RovoInsightsTestResponse.kt``
     - ~5
     - ``taskId`` response DTO
   * - ``api/status/RovoInsightsStatusRequest.kt``
     - ~5
     - Status poll request
   * - ``api/status/RovoInsightsStatusResponse.kt``
     - ~5
     - ``insightsAvailable`` response
   * - ``api/fetch/RovoInsightsFetchRequest.kt``
     - ~5
     - Fetch request
   * - ``api/fetch/RovoInsightsFetchResponse.kt``
     - ~20
     - Full insight bundle (schema version, groups, summary)
   * - ``internal/RovoInsightsGenerationSqsQueueConsumer.kt``
     - ~80
     - SQS consumer with visibility-extension
   * - ``internal/RovoInsightsGenerationTaskHandler.kt``
     - ~40
     - Task handler (stub today)
   * - ``system/RovoInsightsGenerationTask.kt``
     - ~10
     - ``@JsonTypeName("rovo_insights_generation")``
   * - ``system/RovoInsightsConfig.kt``
     - ~15
     - Queue URL + configuration properties

4. Internal data flow
========================

::

   POST /api/v1/rovo-insights/generate
     │
     ▼
   RovoInsightsTestController                        (api/rest/)
     │  • @RequestAttribute(USER) user
     │  • @RequestHeader("atl-cloud-id") cloudId
     │  • CommonContextSetter.setTenant(cloudId, ...)
     │  • build AsyncTaskExecutionContext(tenantId, user, requestId)
     │
     ▼
   AsyncTaskService.submit(
       task    = RovoInsightsGenerationTask(cloudId),
       context = AsyncTaskExecutionContext(...))
     │  • Serialise task as JSON with @JsonTypeName discriminator
     │  • Build SQS message attributes (tenant_id, account_id, request_id)
     │  • Send to rovo-insights-generation-queue
     │
     ▼
   AWS SQS (rovo-insights-generation-queue)
     │
     ▼
   RovoInsightsGenerationSqsQueueConsumer            (internal/)
     │  [LongRun pod only — OnLongRunWorkerNodeOrLocalCondition]
     │  • Visibility-extension heartbeat coroutine started
     │  • MessageQueueConsumerMiddleware:
     │       - Rebuild MDC from message attributes
     │       - Setup request-scoped values
     │       - Dispatch to handler
     │
     ▼
   RovoInsightsGenerationTaskHandler.handle()        (today: stub)
     │  (production target):
     │    • Build Stratus agent via AIGatewayService.buildAgent()
     │    • Configure MCP tool provider (Atlassian Integrations Service)
     │    • Run agent → JSON insight bundle
     │    • Write bundle to Redis keyed by (tenant_id, generated_at)
     │
     ▼
   onSuccess() — emit metric, log completion
   finally — clear MDC, cancel visibility scheduler

   ────────────────────────────────────────────────────

   POST /api/v1/rovo/insights/status
     ▼
   RovoInsightsController.status()
     │  • Read Redis key (tenant_id, latest)
     │  • Return insightsAvailable = (key exists)

   POST /api/v1/rovo/insights/fetch
     ▼
   RovoInsightsController.fetch()
     │  • Read Redis bundle → RovoInsightsFetchResponse

5. DTOs and domain types
============================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Type
     - Fields / purpose
   * - ``RovoInsightsTestRequest``
     - Empty; placeholder (cloud_id from header)
   * - ``RovoInsightsTestResponse``
     - ``taskId: String``
   * - ``RovoInsightsStatusRequest``
     - Polling request (tenant scoped)
   * - ``RovoInsightsStatusResponse``
     - ``insightsAvailable: Boolean``
   * - ``RovoInsightsFetchRequest``
     - Fetch request (tenant scoped)
   * - ``RovoInsightsFetchResponse``
     - ``schemaVersion``, ``generatedAt``, ``count``, ``summary``, ``insightGroups``
   * - ``RovoInsightsGenerationTask``
     - ``cloudId: String`` — ``@JsonTypeName("rovo_insights_generation")``

6. SQS consumer deep dive
============================

``RovoInsightsGenerationSqsQueueConsumer`` implements the
**visibility-extension pattern** (PR #103):

.. code-block:: kotlin

   class RovoInsightsGenerationSqsQueueConsumer(
       private val middleware: MessageQueueConsumerMiddleware,
       private val dispatcher: AsyncTaskDispatcher,
       private val sqsClient: SqsAsyncClient
   ) {
       suspend fun consume(message: Message) {
           val heartbeat = launchVisibilityHeartbeat(message)
           try {
               middleware.wrap(message) {
                   dispatcher.dispatch(message)
               }
           } finally {
               heartbeat.cancel()
               clearMdc()
           }
       }
   }

The heartbeat coroutine periodically calls ``ChangeMessageVisibility`` with
a period < (visibility timeout / 3) for safety margin. This decouples handler
duration from SQS redelivery timeout.

**Performance impact**: throughput increased from ~1.25 to ~10
generations/min/pod (≈ 8× improvement).

7. External system integrations
==================================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - System
     - Integration purpose
   * - **AWS SQS**
     - ``rovo-insights-generation-queue`` (env var ``SQS_ROVO_INSIGHTS_GENERATION_QUEUE_URL``)
   * - **AI Gateway / Stratus**
     - LLM inference via ``AIGatewayService.buildAgent()`` / ``runAgent()``
   * - **Redis (Valkey)**
     - Result cache keyed by ``(tenant_id, generated_at)``
   * - **Integrations Service (MCP)**
     - Tool provider for Stratus agent (workspace data access)
   * - **MetricsService**
     - Task completion/failure metrics, latency histograms

8. Feature flags
==================

Gated by ``AiFeatureGates.ROVO_INSIGHTS_ENABLED`` (Statsig). Evaluated
**before** task submission so the controller can return early:

.. code-block:: kotlin

   if (!featureService.checkGate(AiFeatureGates.ROVO_INSIGHTS_ENABLED)) {
       return ResponseEntity.status(HttpStatus.FORBIDDEN)
           .body(ErrorResponse("Feature not enabled"))
   }

9. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Test
     - Status
     - Validates
   * - ``RovoInsightsGenerationSqsQueueConsumerTest``
     - ✅ Exists
     - SQS consumer routing, middleware lifecycle, visibility heartbeat
   * - ``RovoInsightsTestControllerTest``
     - ❌ Gap
     - Controller request parsing, task submission, 202 response
   * - ``RovoInsightsGenerationTaskHandlerTest``
     - ❌ Gap
     - Handler business logic (blocked on real implementation)

10. Production-readiness gaps
================================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Gap
     - Impact / status
   * - ``RovoInsightsGenerationTaskHandler`` is a stub
     - Real generation logic being ported from convo-ai/Confluence
   * - No production Stratus agent definition
     - Agent config + MCP tool registration needed
   * - No SLO registered in Tome
     - Generation latency + availability targets undefined
   * - No production dashboard
     - No Splunk/SignalFx dashboard for generation metrics
   * - Controller tests missing
     - PR #98 reviewer feedback — planned

See :doc:`/architecture/cross-cutting/01-business-and-technical-goals` for the
roadmap that lands these gaps.

11. Design decisions
=======================

1. **Async over sync** — insight generation requires LLM inference (5–30 s);
   holding an HTTP connection open that long is fragile. Submit-poll-fetch
   lets the web tier scale independently.

2. **SQS as the task bus** — decouples web pods from LongRun worker pods.
   WebServer pods never run the consumer (gated by
   ``OnLongRunWorkerNodeOrLocalCondition``).

3. **Visibility-extension over short timeouts** — allows long-running handlers
   without SQS redelivering mid-generation (PR #103).

4. **Redis for result caching** — fast reads for poll/fetch; TTL-based
   expiration prevents unbounded storage.

5. **JSON-typed task envelope** — ``@JsonTypeName("rovo_insights_generation")``
   lets ``AsyncTaskDispatcher`` route to the correct handler without if-else.

6. **Empty request DTO** — future fields (scope filters, etc.) will be added
   without breaking the API contract.

12. See also
===============

* :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs` — the framework
* :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus` — LLM surface
* :doc:`/architecture/02-request-lifecycle` §2 — async lifecycle
* :doc:`/modules/platform/task` — AsyncTask framework detail
* :doc:`/modules/platform/sqs` — SQS consumer infrastructure
* :doc:`/modules/platform/stratus` — AI Gateway integration
* :doc:`/modules/features/nudge` — sibling feature (sync pattern)
