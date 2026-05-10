.. _pai-platform-utility:

============================================================================
``utility`` — Threading, user, tenant helpers
============================================================================

:Date: 2026-05-04
:Files: 8 main / 0 test (gap; see §6)
:Importance: **P2 — coroutine context loss is hard to debug**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Three subpackages providing infrastructure that doesn't fit elsewhere:

* **``threading/``** — coroutine infrastructure for propagating Spring
  ``RequestAttributes`` and monitoring dispatcher health.
* **``user/``** — authenticated user abstraction.
* **``tenant/``** — Tenant Configuration Service (TCS) integration.

2. File inventory
====================

Threading (``utility/threading/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``RequestAttributesCoroutineContext.kt``
     - ~40
     - Propagates Spring RequestAttributes across coroutine boundary
   * - ``InstrumentedDispatcher.kt``
     - ~80
     - Coroutine dispatcher with ``DispatcherMonitor`` wrapping
   * - ``CoroutineMonitor.kt``
     - ~90
     - Periodic logging of active/running coroutines per dispatcher
   * - ``DispatcherMonitor.kt`` (enum in CoroutineMonitor.kt)
     - —
     - ``DEFAULT``, ``STREAMING_WRITER``, ``STREAMING_WRITER_OUTPUT_STREAM``
   * - ``ThreadConfig.kt``
     - ~10
     - Pool sizing constants

User (``utility/user/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``User.kt`` (interface)
     - ~10
     - Authenticated user model (``getAccountId()``, etc.)
   * - ``internal/UserImpl.kt``
     - ~30
     - Concrete user with ``ExtraContext`` (X-Forwarded-* fields)
   * - ``internal/ExtraContextImpl.kt``
     - ~10
     - Forwarded header values data class

Tenant (``utility/tenant/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``TcsService.kt``
     - ~10
     - Tenant Configuration Service integration (stub today)

3. Key classes deep dive
===========================

``DispatcherMonitor`` (enum)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   enum class DispatcherMonitor(val label: String) {
       DEFAULT("default"),
       STREAMING_WRITER("httpRequestStreamingWriter"),
       STREAMING_WRITER_OUTPUT_STREAM("httpRequestStreamingWriter.outputStream"),
       ;
       val active = AtomicInteger(0)
       val running = AtomicInteger(0)
   }

Each dispatcher tracks two atomic counters:

* ``active`` — coroutines that have been started but not completed
* ``running`` — coroutines currently executing (not suspended)

``CoroutineMonitor`` (object)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   object CoroutineMonitor {
       fun start() {
           // Launches a background coroutine that periodically logs:
           // "dispatcher=X active=N running=M"
           // Only logs dispatchers with non-zero counts
       }
       fun stop() { ... }
   }

Runs in a background coroutine, periodically (configurable by env type)
logging dispatcher metrics. This enables SRE visibility into coroutine
pool saturation without external tooling.

``InstrumentedDispatcher``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wraps a ``CoroutineDispatcher`` with ``DispatcherMonitor`` tracking:

.. code-block:: kotlin

   class InstrumentedDispatcher(
       private val delegate: CoroutineDispatcher,
       private val monitor: DispatcherMonitor,
   ) : CoroutineDispatcher() {
       override fun dispatch(context: CoroutineContext, block: Runnable) {
           monitor.active.incrementAndGet()
           delegate.dispatch(context, Runnable {
               monitor.running.incrementAndGet()
               try { block.run() }
               finally {
                   monitor.running.decrementAndGet()
                   monitor.active.decrementAndGet()
               }
           })
       }
   }

``RequestAttributesCoroutineContext``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Propagates Spring ``RequestAttributes`` (which are thread-local) across
coroutine context switches. Without this, a coroutine dispatched to
``Dispatchers.IO`` would lose access to ``@RequestAttribute(USER)`` and
other servlet-bound values.

Two modes:

* **Servlet-bound** — copies current ``RequestContextHolder`` attributes
* **Async-only** — creates standalone attributes for non-servlet contexts
  (e.g. SQS consumers)

Usage in controllers:

.. code-block:: kotlin

   suspend fun handle() = withContext(
       Dispatchers.IO
       + MDCContext()                                    // SLF4J MDC propagation
       + RequestAttributesCoroutineContext.fromCurrent() // Spring attrs propagation
   ) {
       // MDC and RequestAttributes are available here
   }

``User`` (interface) / ``UserImpl``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface User {
       fun getAccountId(): AccountId
       // ... additional user properties
   }

   class UserImpl(
       private val userContext: UserContext,  // from SLAuth
       private val extraContext: ExtraContext // X-Forwarded-* headers
   ) : User { ... }

Stored as request attribute via ``UserContextInterceptor``. Controllers
access it with ``@RequestAttribute(USER) user: User``.

``TcsService``
~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Service
   class TcsService {
       fun getOrganisationIdByCloudId(cloudId: String): String = "dummy-org-id"
   }

Stub implementation today — returns a dummy org ID. Will be replaced with
real TCS integration when org-level features ship.

4. Coroutine propagation recipe
====================================

When launching a coroutine from a controller, always include both context
elements:

.. code-block:: kotlin

   withContext(
       Dispatchers.IO
       + MDCContext()                                    // propagates MDC (request_id, tenant_id, etc.)
       + RequestAttributesCoroutineContext.fromCurrent() // propagates Spring RequestAttributes
   ) {
       // Safe to use logger (MDC intact) and @RequestAttribute values
   }

**Anti-pattern:** forgetting ``MDCContext()`` causes MDC keys to be empty in
coroutine-dispatched code, making logs unidentifiable.

**Anti-pattern:** forgetting ``RequestAttributesCoroutineContext`` causes
``@RequestAttribute(USER)`` to throw NPE when accessed from a coroutine.

5. Integration patterns
==========================

.. code-block:: text

   utility/
   ├── threading/
   │   ├── Used by → every controller that launches coroutines
   │   ├── Used by → AsyncTask handlers (coroutine-based)
   │   └── Monitored by → SRE via CoroutineMonitor logs
   ├── user/
   │   ├── Built by → UserContextInterceptor
   │   ├── Consumed by → every controller (@RequestAttribute(USER))
   │   └── Consumed by → AsyncTaskExecutionContext
   └── tenant/
       └── Used by → TenantContext construction (org ID lookup)

6. Test coverage
==================

**No dedicated tests.** This is an acknowledged gap:

* ``RequestAttributesCoroutineContext`` — untested; a coroutine propagation
  regression would be difficult to diagnose without tests.
* ``InstrumentedDispatcher`` — untested; counter bugs could cause monitoring
  blind spots.
* ``CoroutineMonitor`` — untested; relies on manual log inspection.

**Recommendation:** add tests as soon as a regression is caught.

7. Design decisions
======================

1. **Coroutine context elements over thread-local copying** — Kotlin's
   ``CoroutineContext`` is the idiomatic way to propagate data across
   suspension points. Direct ``ThreadLocal.copy()`` would break on dispatcher
   switches.
2. **Enum-based dispatcher monitors** — fixed set of dispatchers keeps
   monitoring overhead minimal (no dynamic registration).
3. **User as interface** — allows test doubles without mocking framework;
   ``UserImpl`` encapsulates SLAuth and HTTP details.
4. **TCS as stub** — ships the integration point early so dependent code can
   be written; real implementation lands when org-level features ship.

8. See also
==============

* :doc:`/architecture/cross-cutting/03-request-context-and-mdc` §5 — coroutine
  propagation usage examples
* :doc:`/modules/platform/interceptor` — ``UserContextInterceptor`` builds ``UserImpl``
* :doc:`/modules/platform/requestcontext` — MDC context that coroutines must propagate
