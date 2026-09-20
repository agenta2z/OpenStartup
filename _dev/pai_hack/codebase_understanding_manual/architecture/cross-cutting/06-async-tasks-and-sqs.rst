.. _pai-async-tasks-and-sqs:

============================================================================
Async Tasks and SQS
============================================================================

:Date: 2026-05-04

Two related topics: the **AsyncTask framework** (PAI-defined envelopes
consumed on LongRun pods) and the **StreamHub event consumer** (third-party
events consumed on SHWorkers pods).

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. AsyncTask framework
========================

1.1 Defining a new task type
-----------------------------

.. code-block:: kotlin

   @JsonTypeName("my_new_task")            // discriminator value
   data class MyNewTask(val foo: String) : AsyncTask

1.2 Defining a handler
------------------------

.. code-block:: kotlin

   @Component
   class MyNewTaskHandler(
       private val metricsService: MetricsService
   ) : AsyncTaskHandler<MyNewTask> {

       override val taskType = MyNewTask::class.java
       override val queueName = "my-new-task-queue"   // must match SQS env-var

       override suspend fun handle(ctx: AsyncTaskExecutionContext, task: MyNewTask) {
           // business logic; MDC already has tenant_id/request_id from replay
       }

       override fun onSuccess(ctx: AsyncTaskExecutionContext, task: MyNewTask) { ... }
       override fun onFailure(ctx: AsyncTaskExecutionContext, task: MyNewTask, t: Throwable) { ... }
   }

``AsyncTaskDispatcher`` autowires every ``AsyncTaskHandler<*>`` bean and routes
on the ``@JsonTypeName`` discriminator at deserialise time.

1.3 Submitting from a controller
----------------------------------

.. code-block:: kotlin

   @PostMapping("/api/v1/foo")
   fun foo(@RequestAttribute(USER) user: User,
           @RequestHeader("atl-cloud-id") cloudId: String): MyResponse {
       val task = MyNewTask(foo = "bar")
       val ctx  = AsyncTaskExecutionContext(
           tenantId  = cloudId,
           accountId = user.accountId,
           requestId = MDC.get("request_id"),
           user      = user)
       asyncTaskService.submit(task, ctx)
       return MyResponse(taskId = ctx.requestId)
   }

1.4 Visibility extension (PR #103, the 8× win)
-------------------------------------------------

For long-running handlers, wrap them with the visibility-extension pattern
that ``RovoInsightsGenerationSqsQueueConsumer`` demonstrates:

* Schedule a periodic ``ChangeMessageVisibility`` heartbeat on a side
  coroutine while the handler runs.
* Cancel the heartbeat in ``finally``.
* Pick a heartbeat period < (visibility timeout / 3) for safety margin.

This decouples "max time we'll spend on one message" from "how long until SQS
re-delivers a stuck message" — the previous coupling capped throughput at
~1.25 generations/min/pod; the visibility-extension uncoupling raised that to
~10/min/pod (≈ 8×).

1.5 DLQ
---------

Every queue PAI uses has a redrive policy (configured in service descriptor
or via terraform) that routes a message to a DLQ after N redeliveries
(typically 3-5). Monitor DLQ depth — non-zero is page-worthy.

2. StreamHub event consumer
==============================

2.1 The pipeline
-----------------

GASv3 → StreamHub → SQS (``analytics_events`` queue) → PAI's SHWorkers pods.

2.2 The consumer
-----------------

* ``AnalyticsEventsSqsQueueConsumer`` (gated on ``OnSHWorkerNodeOrLocalCondition``)
  receives ``EventAVI`` payloads.
* Wrapped by ``MessageQueueConsumerMiddleware`` (same middleware as AsyncTask
  consumer — common request-context lifecycle).
* Routed to ``AnalyticsEnrichedEventHandler`` for per-event business logic.
* Today: handler emits a metric and logs; production logic to land as nudge
  signal-ingestion ships.

3. Configuration
==================

Queue URLs are passed in via env vars (``SQS_*_QUEUE_URL``) read in
``application.yml``. The ``atlassian-spring-boot-sqs-starter`` does the
auto-wiring; PAI just provides the consumer beans.

4. See also
=============

* :doc:`/modules/platform/task` — per-file detail
* :doc:`/modules/platform/sqs` — middleware + StreamHub consumer
* :doc:`/modules/features/rovo-insights` — the canonical example user
