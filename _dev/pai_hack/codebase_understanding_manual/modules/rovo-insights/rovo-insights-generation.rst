.. _mod-rovo-insights-generation:

==================================
Rovo Insights — Generation Pipeline
==================================

:Files: ``feature/rovoinsights/RovoInsightsGenerationTask.kt``, ``feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt``, ``feature/rovoinsights/internal/RovoInsightsGenerationSqsQueueConsumer.kt``
:Tests: ``RovoInsightsGenerationTaskHandlerTest.kt``, ``RovoInsightsGenerationSqsQueueConsumerTest.kt``
:Importance: **P0 — async insight generation backbone**

Task Envelope
=============

``RovoInsightsGenerationTask`` is a concrete ``AsyncTask`` subtype carrying
a single field ``cloudId: String``. Its Jackson ``@JsonTypeName`` is
``"rovo_insights_generation"``, which the ``AsyncTaskQueueRegistry``
registers as a polymorphic subtype on the shared ``ObjectMapper`` at startup.

.. code-block:: kotlin

   @JsonTypeName("rovo_insights_generation")
   data class RovoInsightsGenerationTask(
       val cloudId: String,
   ) : AsyncTask

Task Handler
============

``RovoInsightsGenerationTaskHandler`` implements ``AsyncTaskHandler<RovoInsightsGenerationTask>``
and is the single registered handler for this envelope type.

:Queue: ``ROVO_INSIGHTS_GENERATION_QUEUE`` (``rovo_insights_generation_queue``)
:Lifecycle hooks:
   - ``handle()`` — currently a stub; logs the task context. Real generation
     logic (LLM calls, data gathering) will be ported here.
   - ``onSuccess()`` — logs completion with tenant/account/request IDs.
   - ``onFailure()`` — logs the error with full context for Splunk correlation.

SQS Queue Consumer
==================

``RovoInsightsGenerationSqsQueueConsumer`` extends
``VisibilityExtendingSQSQueueConsumer<JsonNode>`` to drain the
``rovo-insights-generation-queue`` on ``LongRun`` worker nodes.

Activation Conditions
---------------------

Two conditions must both be met (AND):

1. ``OnLongRunWorkerNodeOrLocalCondition`` — JVM is a LongRun worker or local dev.
2. ``@ConditionalOnProperty("SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL")`` —
   the queue URL env var is set.

Message Processing Flow
-----------------------

::

   SQS Message (JsonNode)
     │
     ▼
   RovoInsightsGenerationSqsQueueConsumer.processMessage()
     ├── 1. Deserialise JsonNode → AsyncTaskMessage (wire format)
     │      └── Contains: AsyncTaskExecutionContextWire + AsyncTask envelope
     ├── 2. Enter MessageQueueConsumerMiddleware.consume()
     │      └── Initialises request-scoped thread locals
     ├── 3. Populate MDC (tenant_id, request_id, account_id)
     ├── 4. Validate user-context token via UserContextService
     │      └── wire.toContext(userContextService) → AsyncTaskExecutionContext
     └── 5. AsyncTaskDispatcher.dispatch(executionContext, task)
            └── Routes to RovoInsightsGenerationTaskHandler.handle()

The consumer uses ``VisibilityExtendingSQSQueueConsumer`` to heartbeat the
SQS message visibility every 25 seconds, preventing spurious redelivery
during long-running generation tasks.

Visibility Extension
--------------------

Inherited from ``VisibilityExtendingSQSQueueConsumer``:

- Schedules ``changeMessageVisibility`` every **25s** (``PERIOD = DURATION - BUFFER``)
- Resets visibility to **30s** on each heartbeat
- Cancels the heartbeat in ``finally`` when the handler completes
- A crashed JVM's messages become visible again within ~30s for retry

Test Coverage
=============

``RovoInsightsGenerationTaskHandlerTest``
   Verifies handler metadata: ``type`` matches ``RovoInsightsGenerationTask::class.java``,
   ``queueName`` matches ``ROVO_INSIGHTS_GENERATION_QUEUE``, and ``handle()``
   completes without exception.

``RovoInsightsGenerationSqsQueueConsumerTest``
   Tests the ``processMessage()`` internal method with:

   - Valid messages dispatched successfully to ``AsyncTaskDispatcher``
   - Logging context populated with correct tenant/request/account IDs
   - User-context validation failures cause exceptions (message retried by SQS)
   - Malformed JSON causes deserialization errors (logged, message fails)
