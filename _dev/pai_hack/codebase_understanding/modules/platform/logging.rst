==========================================
Module: ``logging`` — Structured Logging
==========================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Provides a layered logging abstraction over SLF4J that adds:

* **Structured key-value context** via ``StructuredArguments``.
* **UGC-safe logging** — truncation and gating of user-generated content.
* **No-op logger** — for suppressing output in specific code paths.
* **Intercepted logger** — delegate pattern for wrapping/transforming log calls.
* **Extension functions** — Kotlin-idiomatic ``debugWithContext``,
  ``infoWithContext``, etc.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - File
     - LoC
     - Role
   * - ``InterceptedLogger.kt``
     - 401
     - Delegate wrapper implementing full SLF4J ``Logger``
   * - ``LaasLogger.kt``
     - 27
     - Extends ``InterceptedLogger``; adds ``withUGC()`` factory
   * - ``LaasLoggerFactory.kt``
     - 9
     - ``@Component`` / object — factory for ``LaasLogger``
   * - ``LoggerExtensions.kt``
     - 51
     - Extension fns: ``debugWithContext``, ``infoWithContext``, etc.
   * - ``NoopLogger.kt``
     - 21
     - All ``isXxxEnabled`` return false; silences output
   * - ``WithUGCLogger.kt``
     - 59
     - Overrides log methods to truncate UGC via ``truncateMessage``

**Total: 6 files, ~568 LoC**

Class / Interface / Enum Catalog
================================

Classes
-------

* ``InterceptedLogger`` — wraps an inner ``Logger``, delegating all 50+ SLF4J
  methods.  Subclasses override specific levels to add behaviour.  401 LoC
  due to full ``Logger`` interface coverage (trace×7, debug×6, info×6, warn×6,
  error×6, isXxxEnabled, getName).

* ``LaasLogger`` — extends ``InterceptedLogger``.

  - Constructor: ``LaasLogger(inner: Logger)`` via ``LaasLoggerFactory``.
  - ``withUGC(featureService: FeatureService): Logger`` — returns a
    ``WithUGCLogger`` if the ``ENABLE_UGC_LOGGING`` gate is open, else
    ``NoopLogger``.

* ``LaasLoggerFactory`` (``@Component``, also ``object``) —
  ``getLogger(clazz: Class<*>): LaasLogger``.

* ``NoopLogger`` — extends ``InterceptedLogger``; overrides all
  ``isTraceEnabled`` / ``isDebugEnabled`` / … to return ``false``, causing
  SLF4J to skip formatting entirely.

* ``WithUGCLogger`` — extends ``InterceptedLogger``; overrides ``info``,
  ``trace``, ``debug``, ``warn``, ``error`` to call ``truncateMessage(msg)``
  before delegating.  Truncation limit: hard-coded at 1000 chars.  Also puts
  ``ugc=true`` into MDC during the call.

Extension Functions (top-level)
-------------------------------

* ``Logger.debugWithContext(msg, vararg pairs)``
* ``Logger.infoWithContext(msg, vararg pairs)``
* ``Logger.warnWithContext(msg, vararg pairs)``
* ``Logger.errorWithContext(msg, throwable?, vararg pairs)``

Each uses ``StructuredArguments.keyValue`` to attach key-value pairs as
structured log fields.

Spring Component Annotations
=============================

========================= =============
Bean                       Annotation
========================= =============
``LaasLoggerFactory``      ``@Component``
========================= =============

Note: ``LaasLoggerFactory`` is both an ``object`` (for static access) and a
``@Component`` (for injection).  The ``@Component`` annotation on an ``object``
works because Kotlin objects are singletons.

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[Service / Controller code] -->|LaasLoggerFactory.getLogger| B[LaasLogger]
       B -->|.info, .debug, etc.| C[InterceptedLogger delegate]
       C --> D[SLF4J Logger]
       B -->|.withUGC featureService| E{FeatureService.checkGate
       ENABLE_UGC_LOGGING}
       E -->|true| F[WithUGCLogger]
       F -->|truncateMessage| D
       E -->|false| G[NoopLogger]
       G -->|silenced| H((discarded))

Configuration Knobs
===================

* **Feature gate** ``ENABLE_UGC_LOGGING`` (Statsig, via ``PermanentFeatureGates``)
  — controls whether ``withUGC()`` returns a live or noop logger.
* **Logback config** ``src/main/resources/logback-spring.xml`` — standard
  Spring Boot logback configuration.
* **Truncation limit** in ``WithUGCLogger`` — hard-coded to 1000 chars (no YAML
  override available).

Testing Coverage
================

================================ ============================
Test class                        Subjects
================================ ============================
``InterceptedLoggerTest``         Delegation fidelity
``LaasLoggerTest``                ``withUGC`` branching
``LaasLoggerFactoryTest``         Factory method
``LoggerExtensionsTest``          Extension fn structured args
``NoopLoggerTest``                All levels disabled
``WithUGCLoggerTest``             Truncation, MDC ugc flag
``LoggingContextTest``            (from requestcontext module)
================================ ============================

**Coverage: 6/6 files** — every class has a dedicated test.  This is the
best-tested module in the codebase.

Dependencies
============

Inbound (consumed by)
---------------------

* Every module that logs — ``LaasLoggerFactory.getLogger()`` is the standard
  logger factory across the service.
* ``requestcontext`` — ``LoggingContext`` is a sibling concern.

Outbound (depends on)
---------------------

* ``featuregate`` — ``FeatureService``, ``PermanentFeatureGates``.
* SLF4J — ``Logger``, ``Marker``, ``LoggerFactory``.
* Logstash / ``net.logstash.logback.argument.StructuredArguments``.

Open Questions / Ambiguities
=============================

1. ``InterceptedLogger`` at 401 LoC is boilerplate-heavy — could use
   Kotlin delegation (``by inner``) but SLF4J ``Logger`` is a Java interface
   with many methods that don't map cleanly.
2. ``WithUGCLogger`` truncation limit (1000 chars) is hard-coded — should be
   a ``@Value`` property for operational tuning.
3. ``LaasLoggerFactory`` being both ``object`` and ``@Component`` is unusual;
   the Spring bean is effectively unused if callers use the object directly.
4. ``LoggerExtensions.kt`` functions take ``vararg Pair<String, String>`` but
   the underlying ``StructuredArguments`` supports arbitrary types — narrowing
   to ``String`` may lose numeric/boolean fidelity.
