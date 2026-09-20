.. _pai-platform-logging:

============================================================================
``logging`` — LaasLogger (SLF4J + MDC wrapper)
============================================================================

:Date: 2026-05-04
:Files: 6 main / 6 test (1:1 ratio — strongest in the codebase)
:Importance: **P1 — observability backbone**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Wrapper over SLF4J that auto-merges MDC context with caller-supplied ad-hoc
context maps. Use ``LaasLoggerFactory.getLogger(class)`` instead of
``LoggerFactory.getLogger(...)`` directly so every log line carries structured
request context automatically.

The package also provides specialised loggers for UGC (User-Generated Content)
handling, no-op suppression, and intercepted metric emission.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``LaasLogger.kt``
     - ~20
     - Primary logger: SLF4J wrapper + UGC logger access
   * - ``LaasLoggerFactory.kt``
     - ~8
     - Factory ``getLogger(class)`` returning ``LaasLogger``
   * - ``InterceptedLogger.kt``
     - ~20
     - Base class wrapping all SLF4J methods with an interceptor function
   * - ``WithUGCLogger.kt``
     - ~60
     - Specialised logger: sets ``env_suffix=unsafe`` MDC key + truncation
   * - ``NoopLogger.kt``
     - ~15
     - All ``isXxxEnabled()`` return ``false``; interceptor is no-op
   * - ``LoggerExtensions.kt``
     - ~30
     - Kotlin extension functions: ``infoWithContext()``, ``warnWithContext()``, ``errorWithContext()``

3. Class hierarchy
=====================

.. code-block:: text

   Logger (SLF4J interface)
   └── InterceptedLogger (open class)
       ├── LaasLogger — default interceptor (pass-through)
       │   ├── .withUGCLogger → WithUGCLogger instance
       │   └── .noopLogger → NoopLogger instance
       ├── WithUGCLogger — sets MDC "env_suffix" = "unsafe", truncates to 10K chars
       └── NoopLogger — all isXxxEnabled() = false, interceptor = {}

4. Key classes deep dive
===========================

``LaasLogger``
~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   class LaasLogger(log: Logger) : InterceptedLogger(log, { it() }) {
       private val withUGCLogger = WithUGCLogger(this)
       private val noopLogger = NoopLogger(this)

       fun withUGC(featureService: FeatureService): Logger =
           if (featureService.checkGate(PermanentFeatureGates.ENABLE_UGC_LOGGING)) {
               withUGCLogger
           } else {
               noopLogger
           }
   }

The ``withUGC()`` method checks the ``ENABLE_UGC_LOGGING`` feature gate at
call time. If UGC logging is disabled (the default), it returns the
``NoopLogger`` which silently discards the log call — no string formatting,
no allocation.

``InterceptedLogger``
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   open class InterceptedLogger(
       private val log: Logger,
       private val interceptor: (executeLog: () -> Unit) -> Unit,
   ) : Logger { ... }

Implements every SLF4J ``Logger`` method by wrapping the actual log call in the
``interceptor`` lambda. Subclasses control behaviour by providing different
interceptors.

``WithUGCLogger``
~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   class WithUGCLogger(log: Logger) : InterceptedLogger(log, WITH_UGC_INTERCEPTOR) {
       companion object {
           private const val MAX_LOG_MESSAGE_LENGTH = 10_000

           private val WITH_UGC_INTERCEPTOR = { log: () -> Unit ->
               try {
                   MDC.put("env_suffix", "unsafe")
                   log()
               } finally {
                   MDC.remove("env_suffix")
               }
           }
       }
   }

Key behaviours:

* Sets ``MDC["env_suffix"] = "unsafe"`` so Splunk routes UGC-containing logs
  to a separate, privacy-compliant index.
* Truncates messages to **10,000 characters** to prevent log explosion from
  large user content.
* ``finally`` block ensures MDC cleanup even if logging throws.

``NoopLogger``
~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   class NoopLogger(log: Logger) : InterceptedLogger(log, { _ -> }) {
       override fun isTraceEnabled() = false
       override fun isDebugEnabled() = false
       override fun isInfoEnabled() = false
       override fun isWarnEnabled() = false
       override fun isErrorEnabled() = false
   }

All level checks return ``false``, and the interceptor discards the log call.
This is cheaper than checking a gate per log call — the gate is checked once
in ``LaasLogger.withUGC()``.

``LaasLoggerFactory``
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Component
   object LaasLoggerFactory {
       fun getLogger(clazz: Class<*>): LaasLogger = LaasLogger(LoggerFactory.getLogger(clazz))
   }

Simple factory. All PAI code should use this instead of SLF4J's
``LoggerFactory`` to ensure MDC integration.

5. Extension functions (``LoggerExtensions.kt``)
=====================================================

Kotlin extensions on SLF4J ``Logger``:

* ``infoWithContext(msg: String, ctx: Map<String, Any?> = emptyMap())``
* ``warnWithContext(msg: String, ctx: Map<String, Any?> = emptyMap(), exception: Throwable? = null)``
* ``errorWithContext(msg: String, ctx: Map<String, Any?> = emptyMap(), exception: Throwable? = null)``

These merge the caller's context map into structured log fields alongside
the MDC context already present.

6. Test coverage
==================

All 6 main files have a corresponding test (1:1 ratio):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``LaasLoggerTest``
     - Factory creation, withUGC gate checking
   * - ``InterceptedLoggerTest``
     - Interceptor invocation for all log levels
   * - ``NoopLoggerTest``
     - All isXxxEnabled() return false
   * - ``WithUGCLoggerTest``
     - MDC env_suffix set/cleared, message truncation at 10K chars
   * - ``LaasLoggerFactoryTest``
     - Returns LaasLogger wrapping correct SLF4J logger
   * - ``LoggerExtensionsTest``
     - Context map merging, exception parameter handling

7. Design decisions
======================

1. **Interceptor pattern** — all SLF4J methods are wrapped, enabling
   cross-cutting concerns (UGC marking, metric emission) without modifying
   call sites.
2. **Gate-controlled UGC** — UGC logging is off by default; the
   ``PermanentFeatureGates.ENABLE_UGC_LOGGING`` gate enables it per-tenant
   for debugging without code changes.
3. **Truncation limit** — 10K characters prevents log pipeline overflow from
   large user content while preserving enough context for debugging.
4. **Privacy by design** — ``env_suffix=unsafe`` routes UGC logs to a
   privacy-compliant Splunk index, meeting data governance requirements.

8. See also
==============

* :doc:`/architecture/cross-cutting/05-observability-and-metrics` §2 — Splunk
  index conventions, ``infoWithContext()`` calling pattern
* :doc:`/modules/platform/requestcontext` — MDC context that auto-merges
* :doc:`/modules/platform/featuregate` — ``PermanentFeatureGates.ENABLE_UGC_LOGGING``
