.. _pai-platform-config:

============================================================================
Platform Layer: ``config/`` — Spring Configuration & Worker Profiling
============================================================================

:Package: ``io.atlassian.micros.proactiveai.config``
:Files: 6 Kotlin source files (208 LoC total)
:Tests: Tested indirectly via ``WebMvcConfigurationTest``-style integration tests
        in the interceptor + service-metric layers (no dedicated test file in this package)
:Source: ``src/main/kotlin/io/atlassian/micros/proactiveai/config/``

Purpose
========

The ``config/`` package is the **Spring Boot bootstrap layer** for the
``proactive-ai-platform`` service. It contains:

1. The ``@Configuration`` classes that wire Spring MVC, register interceptors,
   construct the async ``ThreadPoolTaskExecutor`` used by ``MvcAsync``
   request handlers, and propagate request-scoped context to worker threads.
2. The ``Condition`` classes used by ``@Conditional`` bean declarations
   elsewhere in the codebase to selectively register beans **only** on a
   particular Micros worker group (``SHWorkers``, ``LongRun``) or in
   ``local`` development.
3. A typed ``MicrosEnvironmentType`` enum (``LOCAL``/``STAGING``/``PROD``)
   exposed as a Spring bean so that downstream code can branch on
   environment without parsing strings.
4. A small ``MvcSecurityConfig`` whitelist that exempts ``/healthcheck``
   and ``/deepcheck`` from the Micros SLAuth security starter.

This is one of the smallest packages by line count (208 LoC) but one of the
**highest-impact** packages by blast-radius — every interceptor, async
dispatch, and worker-conditional bean in the service depends on it.
See :doc:`../../overviews/03-criticality-dashboard` for the rationale.

File-by-file Catalog
=====================

.. list-table::
   :header-rows: 1
   :widths: 35 8 57

   * - File
     - LoC
     - Purpose
   * - ``WebMvcConfiguration.kt``
     - 103
     - The brains of the package. Implements ``WebMvcConfigurer``;
       registers the two HTTP interceptors in order (1, 2), builds and
       configures the async ``ThreadPoolTaskExecutor``, wires Micrometer
       ``ContextRegistry`` thread-local accessors for ``Slf4j`` MDC and
       Spring ``RequestAttributes``, and registers the executor with
       ``ExecutorServiceMetrics`` for SignalFx monitoring.
   * - ``MicrosEnvironmentType.kt``
     - 27
     - Sealed-style enum (``LOCAL``, ``STAGING``, ``PROD``) with
       ``isProduction()``/``isNonProduction()`` predicates and a
       ``fromString(String)`` parser. Throws
       ``IllegalArgumentException`` on unknown values (fail-fast).
   * - ``MicrosEnvironmentConfig.kt``
     - 21
     - Spring ``@Configuration`` that produces a ``MicrosEnvironmentType``
       bean by reading ``${micros.environment.type}`` from
       ``application.yml`` and parsing through ``fromString``. Logs
       the resolved environment via ``LaasLoggerFactory`` at startup.
   * - ``OnSHWorkerNodeOrLocalCondition.kt``
     - 21
     - Spring ``Condition`` matching ``MICROS_GROUP=SHWorkers`` **OR**
       ``local`` profile. **One direct consumer (verified 2026-05-05)**:
       ``sqs/AnalyticsEventsSqsQueueConsumer``. Ensures the StreamHub
       analytics-events SQS listener is only registered on the SH worker
       pool, not on web servers or LongRun workers.
   * - ``OnLongRunWorkerNodeOrLocalCondition.kt``
     - 21
     - Twin of the above for ``MICROS_GROUP=LongRun``. **Two direct
       consumers (verified 2026-05-05)**:
       ``feature/rovoinsights/internal/RovoInsightsGenerationSqsQueueConsumer``
       (drains the generation queue) and
       ``task/internal/VisibilityExtendingSQSQueueConsumer`` (extends
       SQS message-visibility for long-running tasks). Ensures generation
       tasks (which can take many seconds of LLM time) never block web
       request threads.
   * - ``MvcSecurityConfig.kt``
     - 15
     - Declares the ``CUSTOM_ANONYMOUS_PATHS`` bean (a ``List<String>``)
       containing ``"/healthcheck"`` and ``"/deepcheck"``. Picked up by
       the ``com.atlassian.micros.config`` security starter to bypass
       SLAuth authentication on those endpoints.

Key Component Deep-Dive: ``WebMvcConfiguration``
=================================================

This class deserves its own deep-dive because it is the single most
important Spring config in the service. It performs **four** distinct
responsibilities, and a bug in any of them silently breaks observability
or context propagation across the entire application.

Responsibility 1: Interceptor Ordering
---------------------------------------

.. code-block:: kotlin

   override fun addInterceptors(registry: InterceptorRegistry) {
       registry.addInterceptor(requestContextInterceptor).order(1)
       registry.addInterceptor(userContextInterceptor).order(2)
   }

The order is **load-bearing**: ``RequestContextInterceptor`` (order 1)
initializes the request-scoped value containers, populates the
"limited" feature-flag context, and seeds MDC with ``request_id``
*before* ``UserContextInterceptor`` (order 2) extracts the
``User-Context`` SLAuth header and registers the authenticated user
as a request attribute. Reversing this order means MDC
context is missing when ``UserContextInterceptor`` logs anything.

See :doc:`../../architecture/cross-cutting/03-request-context-and-mdc`
for the full lifecycle.

Responsibility 2: Async Executor Construction
----------------------------------------------

.. code-block:: kotlin

   executor.corePoolSize = 16
   executor.maxPoolSize  = 64
   executor.queueCapacity = 0
   executor.threadNamePrefix = "ProactiveAIAsyncExc-"

Notice ``queueCapacity = 0``: this is **not** a buffered queue. Tasks
either get a thread immediately, or new threads are spun up to the
``maxPoolSize`` ceiling, or the caller is rejected. The choice avoids
unbounded queueing of slow LLM-bound tasks — slow downstream calls
back-pressure into the request thread rather than silently piling up.

The single ``@Volatile`` ``asyncExecutor`` companion property is held
**only** to support metric introspection from outside; the executor
itself is registered via ``configurer.setTaskExecutor(executor)``.

Responsibility 3: Thread-local Context Propagation
---------------------------------------------------

This is the **most subtle** part. The async executor would, by default,
spawn fresh threads with empty MDC and empty ``RequestAttributes`` —
breaking all logging context, all tenant-scoped feature flags, and any
``@RequestAttribute`` injection in async paths.

The fix uses Micrometer's ``ContextRegistry`` + ``ContextSnapshotFactory``:

.. code-block:: kotlin

   val registry = ContextRegistry.getInstance()
   registry.registerThreadLocalAccessor(Slf4jThreadLocalAccessor())
   registry.registerThreadLocalAccessor(RequestAttributesThreadLocalAccessor())

   val threadLocalTaskDecorator = TaskDecorator { runnable ->
       ContextSnapshotFactory.builder().build()
           .captureAll()
           .wrap(runnable)
   }
   threadPoolTaskExecutor.setTaskDecorator(
       CompositeTaskDecorator(listOf(threadLocalTaskDecorator)),
   )

What this does, in plain English: every time the executor is about to
hand a ``Runnable`` off to a worker thread, the decorator first snapshots
**all** registered thread-locals on the calling thread (MDC + Spring
``RequestAttributes``), wraps the runnable so the snapshot is restored
on the worker side, then runs the original task, then restores the
worker thread's prior state on exit.

This is the Spring Boot 3 / Micrometer 1.10+ replacement for the older
``MDCTaskDecorator`` pattern. See
:doc:`../../architecture/cross-cutting/03-request-context-and-mdc`
for how this composes with the coroutine-based propagation in
``utility/threading/RequestAttributesCoroutineContext``.

Responsibility 4: Executor Metric Registration
-----------------------------------------------

.. code-block:: kotlin

   val metricPrefix = "proactive-ai.$executorName"   // e.g., "proactive-ai.async.webmvc-exc"
   val tags = Tags.of("threadPoolType", executorName)
   ExecutorServiceMetrics.monitor(
       meterRegistry, executor.threadPoolExecutor,
       executorName, metricPrefix, tags,
   )

The ``proactive-ai.`` prefix is **required**, not cosmetic — the
observability sidecar's ``metrics-droplist.yml`` filters out anything
not matching a service-specific prefix. Without it, executor metrics
(``active``, ``idle``, ``queued``, ``rejected``) silently never reach
SignalFx. The PR review for ``WebMvcConfiguration.kt`` (PR #103,
``e2de3cc``) explicitly called this out.

See :doc:`../../architecture/cross-cutting/05-observability-and-metrics`
for the full metrics architecture.

Conditional Beans: Worker-Group Gating
=======================================

The two ``Condition`` classes encode the deployment topology
described in :doc:`../../architecture/cross-cutting/09-deployment-and-config`:

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Condition class
     - Matches when
     - Direct consumers (verified 2026-05-05)
   * - ``OnSHWorkerNodeOrLocalCondition``
     - ``MICROS_GROUP=SHWorkers`` OR ``local`` profile
     - ``sqs/AnalyticsEventsSqsQueueConsumer`` — the StreamHub
       analytics-events SQS listener.
   * - ``OnLongRunWorkerNodeOrLocalCondition``
     - ``MICROS_GROUP=LongRun`` OR ``local`` profile
     - ``feature/rovoinsights/internal/RovoInsightsGenerationSqsQueueConsumer``
       (drains the ``rovo-insights-generation-queue``) and
       ``task/internal/VisibilityExtendingSQSQueueConsumer``
       (the in-flight visibility-timeout extender for long async tasks).

Both conditions read the environment variable directly via
``System.getenv().getOrDefault("MICROS_GROUP", "WebServer")``. Defaulting
to ``"WebServer"`` is significant: any node that is **not** explicitly
labelled ``SHWorkers`` or ``LongRun`` is treated as a web server, and
neither of the worker-conditional consumer beans is created. This is
the mechanism that prevents web pods from accidentally pulling
LLM-generation jobs out of the queue.

Both conditions also short-circuit to ``true`` when the ``local``
Spring profile is active, so a developer running the application
locally gets the full set of consumer beans (and can therefore
exercise the entire request → SQS → worker round-trip on a single JVM).

Environment Modelling
======================

``MicrosEnvironmentType`` is intentionally a closed enum (Kotlin
``enum class``) rather than a string property. The ``fromString``
factory **throws on unknown values**:

.. code-block:: kotlin

   fun fromString(value: String): MicrosEnvironmentType =
       when (value.lowercase()) {
           "local"   -> LOCAL
           "staging" -> STAGING
           "prod"    -> PROD
           else      -> throw IllegalArgumentException("Unknown environment type: $value")
       }

This is consumed by ``MicrosEnvironmentConfig`` at bean-creation time,
so a typo in ``application.yml``'s ``micros.environment.type`` causes
the application to fail to start (rather than silently mis-tagging
metrics or routing to the wrong feature-flag environment). This is
a **deliberate fail-fast design**.

The ``NON_PRODUCTION_ENVIRONMENTS = setOf(LOCAL, STAGING)`` set is
held as a private static (companion) field rather than recomputed per
call — a small but deliberate hot-path optimisation.

.. note::

   **Verified 2026-05-05**: As of this writing, the ``MicrosEnvironmentType``
   bean produced by ``MicrosEnvironmentConfig`` is **not** consumed by any
   other class in the source tree. The ``isProduction()`` /
   ``isNonProduction()`` predicates are defined but currently have **zero**
   call sites outside of the ``config/`` package. The bean is registered
   eagerly and the startup-time logging line in ``MicrosEnvironmentConfig``
   provides operational confirmation of the resolved environment.

   Other code that needs environment information today reads the
   ``MICROS_ENV`` environment variable directly as a ``String`` — for
   example ``featuregate/internal/FeatureFlagContextServiceImpl`` injects
   ``@Value("\${MICROS_ENV:}")`` and assigns it to the Statsig
   ``customAttributes["environment"]`` key. Migrating these sites to
   consume ``MicrosEnvironmentType`` instead would be a small but
   consistency-improving refactor and is a good first-PR candidate for
   new contributors.

Security Bypass Surface
========================

``MvcSecurityConfig`` is a single bean:

.. code-block:: kotlin

   @Bean(name = [MicrosSecurityConstants.CUSTOM_ANONYMOUS_PATHS])
   fun anonymousPaths(): List<String> = listOf("/healthcheck", "/deepcheck")

The Micros security starter looks up beans by the well-known name
``MicrosSecurityConstants.CUSTOM_ANONYMOUS_PATHS`` and exempts each
listed path from SLAuth. This is the **complete** unauthenticated
surface of the service — every other endpoint requires either a valid
SLAuth token (machine-to-machine) or a forwarded ``User-Context``
header (end-user request via the gateway).

Adding a new anonymous path here is a security-sensitive change and
should be reviewed by the ``ai-experience`` team plus AppSec.

Cross-references
=================

* :doc:`../../architecture/cross-cutting/03-request-context-and-mdc`
  — How the ``ContextSnapshotFactory`` decorator integrates with MDC
  and feature-flag context propagation.
* :doc:`../../architecture/cross-cutting/05-observability-and-metrics`
  — Why the ``proactive-ai.`` metric prefix is mandatory.
* :doc:`../../architecture/cross-cutting/06-async-tasks-and-sqs`
  — How ``OnLongRunWorkerNodeOrLocalCondition`` gates the
  ``AsyncTaskDispatcher`` consumer.
* :doc:`../../architecture/cross-cutting/09-deployment-and-config`
  — The ``MICROS_GROUP`` deployment topology.
* :doc:`interceptor` — The two interceptors registered here.
* :doc:`service-metric` — The ``MeterRegistry`` injected here.
* :doc:`logging` — The ``LaasLoggerFactory`` used by
  ``MicrosEnvironmentConfig``.

Operational Notes
==================

* **Changing ``corePoolSize`` / ``maxPoolSize``** in
  ``WebMvcConfiguration`` is a hot-path tuning parameter. Current
  values (16/64) were sized for the CPU/memory profile of the
  ``WebServer`` Micros group; LongRun workers do **not** use this
  executor (they have a separate SQS-listener thread pool managed by
  the ``atlassian-spring-boot-sqs-starter``).
* **Adding a new worker group** (e.g., a third pool for batch
  back-fills) requires: (a) a new ``On…NodeOrLocalCondition`` class
  here, (b) a ``MICROS_GROUP=…`` mapping in ``nebulae.yml`` /
  ``application.yml``, (c) ``@Conditional(...)`` on the new consumer
  bean.
* **Adding a new anonymous endpoint** requires updating
  ``MvcSecurityConfig.anonymousPaths()`` *and* coordinating with the
  Micros security starter version pinned in ``build.gradle.kts``
  (older versions of the starter looked up a different bean name).
* **Local development**: the ``local`` profile short-circuits both
  worker-group conditions, so you get the full bean graph on a single
  JVM. Set ``micros.environment.type=local`` in
  ``application-local.yml`` to also short-circuit the environment check.
