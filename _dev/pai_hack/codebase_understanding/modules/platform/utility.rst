==============================================
Module: ``utility`` — Threading, Tenant & User
==============================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Houses cross-cutting utilities that don't belong in a specific domain module:

* **Threading / Coroutines** — instrumented dispatchers, coroutine-context
  propagation of Spring ``RequestAttributes``, and coroutine monitoring.
* **Tenant** — lightweight tenant-context-service (TCS) client.
* **User** — user identity model and implementation.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``threading/CoroutineMonitor.kt``
     - 91
     - Coroutine-dispatcher health monitoring
   * - ``threading/InstrumentedDispatcher.kt``
     - 107
     - ``ContinuationInterceptor`` with metrics
   * - ``threading/RequestAttributesCoroutineContext.kt``
     - 67
     - ``ThreadContextElement`` for ``RequestAttributes``
   * - ``threading/RequestAttributesForAsyncProcessing.kt``
     - 67
     - ``AbstractRequestAttributes`` impl for async threads
   * - ``threading/ThreadConfig.kt``
     - 122
     - ``@Configuration`` — dispatcher beans + helpers
   * - ``tenant/TcsService.kt``
     - 14
     - ``@Service`` — org-id lookup by cloud-id
   * - ``user/User.kt``
     - 50
     - Interface: ``User``, ``ExtraContext``
   * - ``user/internal/UserImpl.kt``
     - 39
     - Implementation: ``UserImpl``, ``ExtraContextImpl``

**Total: 8 files, ~557 LoC**

Class / Interface / Enum Catalog
================================

Threading Sub-module
--------------------

* ``CoroutineMonitor`` (object) — registers Micrometer gauges tracking active
  coroutines per dispatcher.

  - ``fun start()`` — begins periodic metric collection.
  - ``fun stop()`` — cancels collection.

* ``DispatcherMonitor`` (enum) — ``DEFAULT``, ``STREAMING_WRITER``,
  ``STREAMING_WRITER_OUTPUT_STREAM``.  Labels for instrumented dispatchers.

* ``InstrumentedDispatcher`` — implements ``ContinuationInterceptor`` (a
  ``CoroutineContext.Element``); wraps continuations to track dispatch latency
  and queue depth via Micrometer.

  - ``interceptContinuation(continuation): Continuation<T>``
  - ``releaseInterceptedContinuation(continuation)``

* ``RequestAttributesCoroutineContext`` — implements
  ``ThreadContextElement<RequestAttributes?>``; propagates Spring
  ``RequestAttributes`` from the launching thread into coroutine continuations.

  - ``updateThreadContext(context): RequestAttributes?``
  - ``restoreThreadContext(context, oldState)``

* ``RequestAttributesForAsyncProcessing`` — extends
  ``AbstractRequestAttributes``; a detached, non-servlet-bound attribute store
  used in async / SQS-consumer threads where no ``HttpServletRequest`` exists.

  - Full ``getAttribute`` / ``setAttribute`` / ``removeAttribute`` /
    ``getAttributeNames`` / ``getSessionId`` implementation.

* ``ThreadConfig`` (``@Configuration``) — defines coroutine dispatcher beans:

  - ``@Bean @Qualifier("ioDispatcher")`` — IO-optimised limited-parallelism.
  - ``@Bean @Qualifier("defaultDispatcher")`` — CPU-bound work.
  - ``@Bean @Qualifier("mainDispatcher")`` — main-thread scoped.
  - ``@Bean @Qualifier("redisDispatcher")`` — Redis I/O isolation.

  Top-level helpers:

  - ``fun defaultContext(isAsync, monitor?): CoroutineContext``
  - ``fun <T> runBlockingWithContext(context, block): T``
  - ``val writeOutputStreamDispatchersIO: InstrumentedDispatcher``
  - ``const val LIMITED_PARALLELISM: Int``

Tenant Sub-module
-----------------

* ``TcsService`` (``@Service``) — single method:
  ``fun getOrganisationIdByCloudId(cloudId: String): String``.
  Wraps an upstream call to the Tenant Context Service.

User Sub-module
---------------

* ``User`` (interface) — represents the authenticated user:

  - ``getUserContextHeaderValue(): UserContextHeaderValue``
  - ``getAccountId(): AccountId``
  - ``getUserOrgId(): OrgId?``
  - ``getExtraContext(): ExtraContext``

* ``ExtraContext`` (interface, nested in ``User.kt``) — supplementary request
  metadata:

  - ``getForwardedForHeaderValue(): ForwardedForHeaderValue?``
  - ``getGeoLocation(): GeoLocation?``
  - ``getForwardedHostHeaderValue(): ForwardedHostHeaderValue?``
  - ``isIpAllowListExempted(): Boolean``
  - Data class: ``GeoLocation(countryName: String)``

* ``UserImpl`` — implements ``User`` with constructor parameters.
* ``ExtraContextImpl`` — data class implementing ``ExtraContext``.

Type Aliases (in ``User.kt``)
------------------------------

* ``ForwardedForHeaderValue = String``
* ``ForwardedHostHeaderValue = String``
* ``UserContextHeaderValue = String``
* ``OrgId = String``

Spring Component Annotations
=============================

==================== ========================
Bean                  Annotation
==================== ========================
``ThreadConfig``      ``@Configuration``
``TcsService``        ``@Service``
==================== ========================

Dispatcher beans: ``ioDispatcher``, ``defaultDispatcher``, ``mainDispatcher``,
``redisDispatcher`` (all ``@Bean @Qualifier``).

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["Controller thread (HTTP request)
       RequestAttributes = HttpServletRequest
       User = UserImpl"] -->|launch coroutine on ioDispatcher| B[Coroutine continuation]
       B --> C["RequestAttributesCoroutineContext
       copies RequestAttributes to new thread"]
       B --> D["InstrumentedDispatcher
       records dispatch latency metric"]
       B --> E["CoroutineMonitor
       tracks active coroutine count"]
       C & D & E --> F["Async / SQS consumer thread"]
       F --> G["RequestAttributesForAsyncProcessing
       standalone attribute store (no servlet)"]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Property / Constant
     - Default
     - Description
   * - ``LIMITED_PARALLELISM``
     - (compile-time)
     - Max concurrent coroutines per instrumented dispatcher
   * - Dispatcher ``@Qualifier`` names
     - ``ioDispatcher``, ``defaultDispatcher``, ``mainDispatcher``, ``redisDispatcher``
     - Named beans for injection

No YAML-driven configuration for dispatchers — parallelism is set at
compile time.

Testing Coverage
================

No dedicated test files exist for this module.

**Gaps:**

* ``InstrumentedDispatcher`` and ``RequestAttributesCoroutineContext`` are
  critical concurrency primitives with no unit tests.
* ``TcsService`` has no test — upstream call is not mocked.
* ``UserImpl`` / ``ExtraContextImpl`` are trivial data holders — low
  test priority.

Dependencies
============

Inbound (consumed by)
---------------------

* ``interceptor`` — ``UserImpl``, ``ExtraContextImpl`` created in
  ``UserContextInterceptor``.
* ``requestcontext`` — ``RequestAttributesForAsyncProcessing`` used by
  ``RequestScopedValuesInitterImpl``.
* ``integration/task`` — async task handlers use coroutine dispatchers.
* ``integration/stratus`` — AI Gateway calls run on instrumented dispatchers.
* ``feature/rovoinsights`` — generation task uses coroutine context.

Outbound (depends on)
---------------------

* Kotlin Coroutines — ``CoroutineDispatcher``, ``ContinuationInterceptor``,
  ``ThreadContextElement``.
* Spring Framework — ``RequestAttributes``, ``AbstractRequestAttributes``,
  ``RequestContextHolder``.
* Micrometer — gauge/counter registration in ``CoroutineMonitor`` and
  ``InstrumentedDispatcher``.

Open Questions / Ambiguities
=============================

1. ``ThreadConfig`` defines 4 dispatcher beans but usage across the codebase
   may not be balanced — profile which dispatchers are actually injected.
2. ``RequestAttributesForAsyncProcessing.getSessionId()`` returns a fixed
   string — any code path that relies on real session semantics will break.
3. ``TcsService`` at 14 LoC is a thin wrapper — its value is primarily as a
   seam for testing; confirm whether the upstream TCS client is injected or
   inline.
4. ``CoroutineMonitor.start()`` / ``stop()`` lifecycle is not managed by
   Spring — verify it's called from ``@PostConstruct`` / ``@PreDestroy``
   somewhere.
5. ``LIMITED_PARALLELISM`` is compile-time — consider making it a ``@Value``
   property for runtime tuning without redeployment.
