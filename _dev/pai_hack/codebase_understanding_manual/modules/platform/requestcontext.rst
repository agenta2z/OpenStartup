.. _pai-platform-requestcontext:

============================================================================
``requestcontext`` — Request-scoped values & MDC API
============================================================================

:Date: 2026-05-04
:Files: 14 main / 2 test
:Importance: **P0 — blast radius: every request + every async task**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Provides per-request thread-locals (``RequestScopedValue<T>``), the
``LoggingContext`` API for MDC manipulation, and the lifecycle pieces that
wire them into both HTTP and SQS request paths. This is the foundation
layer that makes structured logging, feature-flag evaluation, and tenant
tracking work across threads and coroutines.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``LoggingContext.kt`` (interface)
     - ~40
     - MDC API: ``runWithContext``, ``addTenantContext``, ``addAsyncTaskContext``, ``clear``
   * - ``HeaderConstants.kt``
     - ~5
     - ``GEO_IP = "Atl-Edge-Geoip"``
   * - ``RequestScopedValueKey.kt`` (enum)
     - ~8
     - Keys: ``FEATURE_FLAG_CONTEXT``, ``FEATURE_FLAG_EVALUATION_TRACKER``, ``MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES``
   * - ``RequestContextValues.kt``
     - ~30
     - ``RequestScopedValueService<T>`` — generic thread-local storage
   * - ``RequestScopedValueOwner.kt``
     - ~15
     - Each owner registers its key + factory
   * - ``RequestScopedValueOwners.kt``
     - ~25
     - Spring component aggregating all owners; validates at startup
   * - ``RequestScopedValuesInitter.kt`` (interface)
     - ~10
     - Per-request setup/teardown lifecycle
   * - ``RequestAttributes.kt``
     - ~5
     - ``const val USER = "user"`` attribute name
   * - ``RequestContextExtractor.kt``
     - ~20
     - Static helpers for extracting forwarded headers
   * - ``MiscellaneousRequestContextVariablesService.kt``
     - ~25
     - X-Forwarded-For/Host, X-Request-ID capture
   * - ``internal/LoggingContextImpl.kt``
     - ~60
     - SLF4J MDC adapter implementation
   * - ``internal/RequestScopedValuesInitterImpl.kt``
     - ~40
     - Init/teardown implementation

3. Key classes deep dive
===========================

``LoggingContext`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface LoggingContext {
       fun <T> runWithContext(toRun: () -> T, ctx: Map<String, String>): T
       suspend fun <T> runWithContextAsync(toRun: suspend () -> T, ctx: Map<String, String>): T
       fun addTenantContext(tenantContext: TenantContext): SetContextUndo
       fun addStreamHubEventInfo(eventId, eventType, ingestionSource, ...)
       fun addAsyncTaskContext(tenantId, requestId, accountId)
       fun setFromRequest(requestId, accountId)
       fun getRequestId(): String
       fun clear()
   }

Three context-setting paths:

1. **HTTP requests** — ``setFromRequest()`` called by ``CommonContextSetterImpl``
2. **Async tasks** — ``addAsyncTaskContext()`` called by ``MessageQueueConsumerMiddleware``
3. **StreamHub events** — ``addStreamHubEventInfo()`` called by event handler

The ``clear()`` method is called in ``finally`` blocks by both
``LoggingContextClearingFilter`` (HTTP) and ``MessageQueueConsumerMiddleware``
(SQS).

``RequestScopedValueKey`` (enum)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   enum class RequestScopedValueKey {
       FEATURE_FLAG_CONTEXT,
       FEATURE_FLAG_EVALUATION_TRACKER,
       MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES,
   }

Each key maps to a thread-local slot. Values are set during
``setupRequestScopedValues()`` and cleared during teardown.

``RequestScopedValueOwner``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Registration pattern — each module that needs a request-scoped value implements
``RequestScopedValueOwner`` and registers its key + factory function.
``RequestScopedValueOwners`` (a Spring ``@Component``) collects all owners at
startup and validates:

* No duplicate keys
* No missing required keys
* All owners are Spring-managed beans

``MiscellaneousRequestContextVariablesService``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Captures HTTP headers at request entry:

* ``X-Forwarded-For`` — client IP chain (for geo-IP logging)
* ``X-Forwarded-Host`` — original hostname (for Statsig context)
* ``X-Request-Id`` — request correlation ID (generated if absent)

4. MDC keys populated
========================

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - MDC Key
     - Set by
     - Value
   * - ``request_id``
     - ``setFromRequest()``
     - UUID from ``X-Request-Id`` or generated
   * - ``tenant_id``
     - ``addTenantContext()``
     - Cloud ID from ``atl-cloud-id``
   * - ``account_id``
     - ``setFromRequest()``
     - From SLAuth user context
   * - ``org_id``
     - ``addTenantContext()``
     - Organisation ID
   * - ``trace_id``
     - ``LoggingContextClearingFilter``
     - OpenTelemetry trace ID
   * - ``span_id``
     - ``LoggingContextClearingFilter``
     - OpenTelemetry span ID
   * - ``experiment_id``
     - ``LoggingContextClearingFilter``
     - From OTel Baggage (if present)

5. Lifecycle flow
====================

::

   HTTP Request
     │
     ▼
   RequestContextInterceptor.preHandle()
     │  requestScopedValuesInitter.setupRequestScopedValues()
     │     → iterates all RequestScopedValueOwner beans
     │     → seeds each thread-local from factory
     │  commonContextSetter.setRequest()
     │     → loggingContext.setFromRequest(requestId, accountId)
     │
     ▼
   Controller
     │  commonContextSetter.setTenant(tenantContext)
     │     → loggingContext.addTenantContext(tenantContext)
     │
     ▼
   Response committed
     │
     ▼
   LoggingContextClearingFilter.finally
     │  loggingContext.clear()  // MDC.clear() + thread-local teardown

6. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Test
     - Validates
   * - ``RequestScopedValuesInitterTest``
     - Startup-time validation, duplicate key detection, setup/teardown lifecycle
   * - ``MiscellaneousRequestContextVariablesServiceTest``
     - Header capture, missing header handling, request-ID generation

7. Design decisions
======================

1. **Owner registration pattern** — each module registers its own
   request-scoped value rather than a central registry, keeping modules
   decoupled.
2. **Startup validation** — ``RequestScopedValueOwners`` fails fast on
   duplicates/gaps, catching wiring errors before traffic arrives.
3. **Separate HTTP vs SQS context paths** — ``setFromRequest()`` for HTTP,
   ``addAsyncTaskContext()`` for SQS, ensuring MDC is correctly populated
   regardless of entry point.
4. **``SetContextUndo``** — ``addTenantContext()`` returns an undo handle so
   callers can restore previous MDC state (useful in test utilities).

8. See also
==============

* :doc:`/architecture/cross-cutting/03-request-context-and-mdc` — end-to-end
  story including limited vs full context and coroutine propagation
* :doc:`/modules/platform/interceptor` — consumes ``RequestScopedValuesInitter``
* :doc:`/modules/platform/logging` — consumes MDC context
* :doc:`/modules/platform/sqs` — ``MessageQueueConsumerMiddleware`` uses ``LoggingContext``
