.. _pai-platform-task:

============================================================================
``task`` — Async-task envelope framework
============================================================================

:Date: 2026-05-04
:Files: 11 main / 3 test
:Importance: **P1 — every long-running feature uses it**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

JSON-polymorphic task envelopes submitted via ``AsyncTaskService`` to AWS SQS,
processed on LongRun pods by ``AsyncTaskHandler`` beans. This is the canonical
pattern for any PAI work that takes longer than an HTTP request should hold
open (>1–2 seconds).

The framework handles serialisation, routing, MDC replay, lifecycle hooks,
and queue registry — feature code only needs to define a task data class and
a handler.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``AsyncTask.kt`` (interface)
     - ~8
     - ``@JsonTypeInfo``-discriminated envelope marker
   * - ``AsyncTaskHandler.kt`` (interface)
     - ~25
     - ``handle(ctx, task)`` + lifecycle hooks + queue name
   * - ``AsyncTaskExecutionContext.kt``
     - ~10
     - Tenant/user/request-id triple for MDC replay
   * - ``AsyncTaskService.kt`` (interface)
     - ~12
     - Producer API: ``submit(ctx, task) → AsyncTaskId``
   * - ``AsyncTaskId.kt`` (inline class)
     - ~3
     - Type-safe task ID wrapper
   * - ``AsyncTaskQueueRegistry.kt``
     - ~20
     - Maps task type → queue name
   * - ``AsyncTaskDispatcher.kt``
     - ~70
     - Routes deserialised task to handler bean
   * - ``internal/AsyncTaskServiceImpl.kt``
     - ~50
     - Serialises task; builds SQS message attributes
   * - ``internal/AsyncTaskDispatcherImpl.kt``
     - ~40
     - Handler map + error handling
   * - ``internal/AsyncTaskMessageAttributes.kt``
     - ~15
     - Message attribute key constants

3. Key classes deep dive
===========================

``AsyncTask`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @JsonTypeInfo(use = JsonTypeInfo.Id.NAME, include = JsonTypeInfo.As.PROPERTY, property = "@type")
   interface AsyncTask

Marker interface with Jackson polymorphic type info. Concrete tasks use
``@JsonTypeName("discriminator_value")`` to register their type:

.. code-block:: kotlin

   @JsonTypeName("rovo_insights_generation")
   data class RovoInsightsGenerationTask(val cloudId: String) : AsyncTask

``AsyncTaskHandler<T : AsyncTask>`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface AsyncTaskHandler<T : AsyncTask> {
       val type: Class<T>           // task class for routing
       val queueName: String        // SQS queue name

       suspend fun handle(executionContext: AsyncTaskExecutionContext, task: T)
       suspend fun onSuccess(executionContext: AsyncTaskExecutionContext, task: T) {}
       suspend fun onFailure(executionContext: AsyncTaskExecutionContext, task: T, error: Throwable) {}
   }

Lifecycle hooks:

* ``handle()`` — main business logic (suspend function for coroutine support)
* ``onSuccess()`` — called after successful ``handle()`` (metrics, logging)
* ``onFailure()`` — called on exception (cleanup, alerting). If ``onFailure``
  itself throws, the error is swallowed and the original exception is re-thrown.

``AsyncTaskExecutionContext``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   data class AsyncTaskExecutionContext(
       val tenantId: String,
       val user: User,
       val requestId: String,
   )

Carried as SQS message attributes so the consumer can replay MDC context
on the worker pod (different JVM, different thread).

``AsyncTaskDispatcher``
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Component
   class AsyncTaskDispatcher(handlers: List<AsyncTaskHandler<*>>) {
       private val handlersByType: Map<Class<out AsyncTask>, AsyncTaskHandler<*>> =
           handlers.associateBy { it.type }

       suspend fun dispatch(executionContext: AsyncTaskExecutionContext, task: AsyncTask) {
           val handler = handlersByType[task.javaClass]
               ?: error("No AsyncTaskHandler registered for ${task.javaClass.name}")
           try {
               handler.handle(executionContext, task)
               handler.onSuccess(executionContext, task)
           } catch (e: Exception) {
               log.errorWithContext("Async task handler failed", ...)
               runCatching { handler.onFailure(executionContext, task, e) }
               throw e
           }
       }
   }

Key behaviours:

* Autowires all ``AsyncTaskHandler<*>`` beans at startup
* Routes on ``task.javaClass`` (which matches ``@JsonTypeName`` discriminator)
* Logs handler count and registered types at startup
* ``onFailure`` errors are caught and logged but do not mask the original error

``AsyncTaskService`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface AsyncTaskService {
       suspend fun submit(executionContext: AsyncTaskExecutionContext, task: AsyncTask): AsyncTaskId
   }

The ``submit()`` implementation:

1. Serialises the task as JSON (with ``@type`` discriminator)
2. Builds SQS message attributes from ``executionContext`` (tenant_id,
   account_id, request_id)
3. Sends to the queue registered for this task type
4. Returns ``AsyncTaskId`` (value class wrapping the message ID)

4. Adding a new async task
=============================

Step-by-step:

.. code-block:: kotlin

   // 1. Define the task
   @JsonTypeName("my_new_task")
   data class MyNewTask(val foo: String) : AsyncTask

   // 2. Define the handler
   @Component
   class MyNewTaskHandler : AsyncTaskHandler<MyNewTask> {
       override val type = MyNewTask::class.java
       override val queueName = "my-new-task-queue"

       override suspend fun handle(ctx: AsyncTaskExecutionContext, task: MyNewTask) {
           // business logic; MDC already has tenant_id/request_id
       }
   }

   // 3. Submit from a controller
   val ctx = AsyncTaskExecutionContext(tenantId = cloudId, user = user, requestId = requestId)
   asyncTaskService.submit(ctx, MyNewTask(foo = "bar"))

5. Visibility extension pattern
===================================

For long-running handlers (>30s), the consumer wraps the handler with a
visibility-extension heartbeat coroutine (demonstrated by
``RovoInsightsGenerationSqsQueueConsumer``):

* Schedule periodic ``ChangeMessageVisibility`` calls
* Cancel heartbeat in ``finally``
* Period < (visibility timeout / 3) for safety margin

This decouples handler duration from SQS redelivery timeout. Performance
impact: throughput from ~1.25 to ~10 generations/min/pod (≈ 8×).

6. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``AsyncTaskDispatcherTest``
     - Handler routing by type, missing handler error, onSuccess/onFailure hooks
   * - ``AsyncTaskQueueRegistryTest``
     - Queue-name mapping, duplicate detection
   * - ``AsyncTaskServiceImplTest``
     - SQS serialisation, message attribute building, submit contract

7. Design decisions
======================

1. **JSON polymorphism** — ``@JsonTypeInfo`` with ``@JsonTypeName`` enables
   type-safe routing without if-else chains. New task types are auto-discovered.
2. **Suspend functions** — ``handle()`` is ``suspend`` enabling coroutine-native
   handlers without blocking thread pool threads.
3. **Lifecycle hooks** — ``onSuccess``/``onFailure`` separate cross-cutting
   concerns (metrics, logging) from business logic.
4. **Context replay** — ``AsyncTaskExecutionContext`` is serialised as SQS
   message attributes so worker pods can rebuild MDC without the original
   HTTP request.
5. **Inline class for ID** — ``AsyncTaskId`` is a ``@JvmInline value class``
   preventing accidental mixing of task IDs with other strings.

8. See also
==============

* :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs` §1 — end-to-end
  story including visibility-extension (PR #103)
* :doc:`/modules/platform/sqs` — ``MessageQueueConsumerMiddleware`` shared
  with StreamHub consumer
* :doc:`/modules/features/rovo-insights` — defines
  ``RovoInsightsGenerationTask`` + handler
