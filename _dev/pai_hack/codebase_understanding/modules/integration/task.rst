=====================================================
Module: ``task`` — Async Task Framework
=====================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Provides a **generic async task dispatch framework** built on SQS.  Allows
feature modules to define typed tasks, submit them to SQS queues, and have
them executed on worker nodes with proper context propagation (tenant, user,
request-id).  The framework handles:

* Task serialization/deserialization with Jackson polymorphism.
* Queue routing via a task-type → queue-name registry.
* SQS message visibility extension for long-running tasks.
* Execution context wiring (tenant, user, request-id).

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``AsyncTask.kt``
     - 20
     - Interface: base task envelope with ``@JsonTypeInfo``
   * - ``AsyncTaskDispatcher.kt``
     - 89
     - ``@Component`` — routes tasks to handlers
   * - ``AsyncTaskExecutionContext.kt``
     - 13
     - Data class: tenant, user, request-id context
   * - ``AsyncTaskHandler.kt``
     - 47
     - Interface: handler contract with lifecycle hooks
   * - ``AsyncTaskQueueRegistry.kt``
     - 72
     - ``@Component`` — task-type → queue-name mapping
   * - ``AsyncTaskService.kt``
     - 32
     - Interface: task submission API
   * - ``internal/AsyncTaskExecutionContextWire.kt``
     - 76
     - ``@Component`` — serialises/deserialises execution context
   * - ``internal/AsyncTaskMessage.kt``
     - 13
     - Data class: SQS message wrapper
   * - ``internal/AsyncTaskMessageAttributes.kt``
     - 16
     - Data class: SQS message attribute fields
   * - ``internal/AsyncTaskServiceImpl.kt``
     - 141
     - ``@Service`` — SQS-backed task submission
   * - ``internal/VisibilityExtendingSQSQueueConsumer.kt``
     - 130
     - Abstract class: SQS consumer with auto-visibility extension

**Total: 11 files, ~649 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``AsyncTask`` — base interface for all async tasks:

  - Annotated with ``@JsonTypeInfo(use = NAME, property = "type")`` for
    polymorphic JSON serialization.
  - Implementations use ``@JsonTypeName("...")`` to declare their type
    discriminator.

* ``AsyncTaskHandler<T : AsyncTask>`` — handler contract:

  - ``val type: Class<T>`` — the task class this handler processes.
  - ``val queueName: String`` — the SQS queue this handler consumes from.
  - ``suspend fun handle(executionContext: AsyncTaskExecutionContext, task: T)``
    — main processing logic.
  - ``suspend fun onSuccess(executionContext: AsyncTaskExecutionContext, task: T)``
    — post-success hook (default no-op).
  - ``suspend fun onFailure(executionContext: AsyncTaskExecutionContext, task: T, error: Throwable)``
    — post-failure hook (default no-op).

* ``AsyncTaskService`` — submission API:

  - ``suspend fun enqueueTask(tenantId: String, user: User, task: AsyncTask)``

Data Classes
------------

* ``AsyncTaskExecutionContext`` — execution metadata:

  - ``tenantId: String``
  - ``user: User``
  - ``requestId: String``

* ``AsyncTaskMessage`` (internal) — SQS message body:

  - ``task: AsyncTask``
  - ``attributes: AsyncTaskMessageAttributes``

* ``AsyncTaskMessageAttributes`` (internal) — SQS message attributes:

  - ``tenantId: String``
  - ``userId: String``
  - ``requestId: String``

Component Classes
-----------------

* ``AsyncTaskDispatcher`` (``@Component``) — receives deserialized tasks and
  routes to the correct ``AsyncTaskHandler``:

  - ``suspend fun dispatch(executionContext: AsyncTaskExecutionContext, task: AsyncTask)``
  - Iterates registered handlers, matches by ``handler.type``, invokes
    ``handle()``, then ``onSuccess()`` or ``onFailure()``.

* ``AsyncTaskQueueRegistry`` (``@Component``) — auto-registers all
  ``AsyncTaskHandler`` beans and maps ``taskType → queueName``:

  - ``fun getQueueName(taskType: Class<out AsyncTask>): String``
  - ``fun register(taskType: Class<out AsyncTask>, queueName: String)``

* ``AsyncTaskExecutionContextWire`` (``@Component``) — converts between
  ``AsyncTaskExecutionContext`` and ``AsyncTaskMessageAttributes``:

  - ``fun wire(message: AsyncTaskMessage): AsyncTaskExecutionContext``
  - ``fun unwire(context: AsyncTaskExecutionContext): AsyncTaskMessageAttributes``

* ``AsyncTaskServiceImpl`` (``@Service``,
  ``@ConditionalOnBean(ConnectionFactory::class)``) — SQS-backed
  implementation:

  - ``suspend fun enqueueTask(tenantId, user, task)`` — serializes task +
    attributes, sends to the appropriate SQS queue.
  - Private: ``suspend fun sendMessage(queueUrl, message)`` — SQS send.

* ``VisibilityExtendingSQSQueueConsumer<T>`` (abstract, extends
  ``SQSQueueConsumer<T>``) — automatically extends SQS message visibility
  timeout during long-running task processing:

  - Launches a background coroutine that periodically calls
    ``changeMessageVisibility`` to prevent message re-delivery.
  - Used by ``RovoInsightsGenerationSqsQueueConsumer``.

Spring Component Annotations
=============================

======================================= =====================================
Bean                                     Annotation
======================================= =====================================
``AsyncTaskDispatcher``                  ``@Component``
``AsyncTaskQueueRegistry``              ``@Component``
``AsyncTaskExecutionContextWire``        ``@Component``
``AsyncTaskServiceImpl``                 ``@Service @ConditionalOnBean``
======================================= =====================================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["Feature code (e.g. RovoInsightsTestController)"] -->|"enqueueTask(tenantId, user, task)"| B[AsyncTaskServiceImpl]
       B --> C["AsyncTaskQueueRegistry.getQueueName(task.class)"]
       C -->|queue name| B
       B -->|"serialize AsyncTaskMessage
       {task, attributes}"| D["SQS.sendMessage(queueUrl, body)"]
       D --> E[SQS Queue]
       E --> F["VisibilityExtendingSQSQueueConsumer
       (worker node)"]
       F -->|deserialize JsonNode| G[Start visibility-extension coroutine]
       F --> H[AsyncTaskExecutionContextWire.wire]
       H -->|build AsyncTaskExecutionContext| I[AsyncTaskDispatcher.dispatch]
       I -->|match handler by task type| J["handler.handle(context, task)"]
       J -->|success| K[handler.onSuccess]
       J -->|failure| L[handler.onFailure]
       K & L --> M[Cancel visibility-extension coroutine]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 45 20 35

   * - Property
     - Default
     - Description
   * - ``SQS_*_QUEUE_URL``
     - env var per queue
     - SQS queue URL for each task type
   * - ``SQS_*_QUEUE_NAME``
     - env var per queue
     - SQS queue name for each task type
   * - ``atlassian.sqs.properties.concurrency``
     - ``2-8``
     - Worker thread pool range
   * - ``atlassian.sqs.region``
     - ``${MICROS_AWS_REGION:us-east-1}``
     - AWS region

The visibility extension interval and maximum extensions are configured
within ``VisibilityExtendingSQSQueueConsumer`` (likely hard-coded; verify
source).

Testing Coverage
================

======================================= ====== ============================
Test class                               Lines  Subjects
======================================= ====== ============================
``AsyncTaskDispatcherTest``               66    Handler routing, lifecycle
``AsyncTaskQueueRegistryTest``           103    Registration, lookup
``AsyncTaskServiceImplTest``             145    Enqueue, serialization, send
``TestUsers.kt``                          32    Test utilities
======================================= ====== ============================

**Coverage: 3/5 implementation classes** have dedicated unit tests.

**Gaps:**

* ``AsyncTaskExecutionContextWire`` — no test for wire/unwire.
* ``VisibilityExtendingSQSQueueConsumer`` — no test for visibility extension
  logic (critical concurrency code).

Dependencies
============

Inbound (consumed by)
---------------------

* ``feature/rovoinsights`` — ``RovoInsightsGenerationTask`` implements
  ``AsyncTask``; ``RovoInsightsGenerationTaskHandler`` implements
  ``AsyncTaskHandler``; ``RovoInsightsGenerationSqsQueueConsumer`` extends
  ``VisibilityExtendingSQSQueueConsumer``.

Outbound (depends on)
---------------------

* ``sqs`` — ``QueueNames`` constants, ``CommonSqsConfig`` for
  ``ConnectionFactory``.
* ``utility/user`` — ``User`` interface for execution context.
* ``utility/threading`` — coroutine dispatchers for visibility extension.
* ``requestcontext`` — ``LoggingContext`` for async context setup.
* Atlassian SQS Starter — ``SQSQueueConsumer``, ``@ManagedQueueConsumer``.
* Jackson — ``@JsonTypeInfo``, ``@JsonTypeName``, ``ObjectMapper``.
* AWS SDK — ``SqsClient`` for message send/visibility operations.
* Kotlin Coroutines — ``launch``, ``delay`` for visibility extension loop.

Open Questions / Ambiguities
=============================

1. ``AsyncTask`` uses ``@JsonTypeInfo(use = NAME)`` — all task implementations
   must be registered with Jackson for polymorphic deserialization.  No
   explicit registration code is visible; likely relies on classpath scanning
   via ``@JsonTypeName``.
2. ``AsyncTaskServiceImpl`` is ``@ConditionalOnBean(ConnectionFactory)`` —
   in environments without SQS (e.g., local without Docker), task submission
   silently fails because no ``AsyncTaskService`` bean exists.
3. ``VisibilityExtendingSQSQueueConsumer`` visibility extension interval
   appears hard-coded — should be configurable for different task durations.
4. ``AsyncTaskDispatcher`` iterates all handlers to find a match — O(n) per
   dispatch; consider a ``Map<Class, Handler>`` for O(1) lookup.
5. Error handling in ``onFailure`` is handler-defined — no framework-level
   dead-letter-queue (DLQ) integration for unrecoverable failures.
6. The ``README.md`` in the task directory may contain additional design
   documentation — cross-reference for authoritative design decisions.
