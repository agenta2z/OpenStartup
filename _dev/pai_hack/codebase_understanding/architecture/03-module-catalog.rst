.. _module-catalog:

==============================
Module Catalog
==============================

Comprehensive catalog of all 16 functional modules in the Proactive AI
Service, organized by the 15 top-level packages.

.. note::

   The service contains **15 top-level packages (16 functional modules)**.
   The ``feature`` package is counted as two functional modules (Nudge
   Throttle and Rovo Insights) because they have independent lifecycles,
   separate SQS queues, and distinct operational profiles.  This
   methodology is applied consistently throughout the documentation.

Catalog Summary
===============

.. list-table:: Module Catalog
   :header-rows: 1
   :widths: 18 8 8 8 8 8 42

   * - Module
     - Files
     - LoC
     - Ctrl
     - Svc
     - Comp
     - Purpose
   * - ``client``
     - 7
     - 399
     - 0
     - 0
     - 2
     - HTTP clients for external identity services
   * - ``config``
     - 6
     - 208
     - 0
     - 0
     - 3 (cfg)
     - Application-level Spring configuration
   * - ``context``
     - 9
     - 381
     - 0
     - 0
     - 0
     - Multi-tenancy context model classes
   * - ``exception``
     - 1
     - 116
     - 0
     - 0
     - 0
     - REST client exception hierarchy
   * - ``feature/nudge``
     - 5†
     - 180†
     - 1
     - 0
     - 0
     - Nudge throttle API
   * - ``feature/rovoinsights``
     - 15†
     - 550†
     - 2
     - 0
     - 2
     - Rovo Insights generation pipeline
   * - ``featuregate``
     - 8
     - 754
     - 0
     - 1 (svc)
     - 2
     - Feature flag evaluation and tracking
   * - ``greeting``
     - 1
     - 56
     - 1
     - 0
     - 0
     - Health/sample REST endpoint
   * - ``interceptor``
     - 5
     - 295
     - 0
     - 0
     - 4
     - HTTP request interceptors
   * - ``logging``
     - 6
     - 568
     - 0
     - 0
     - 1
     - Structured logging framework
   * - ``requestcontext``
     - 14
     - 906
     - 0
     - 1
     - 4
     - Request-scoped value management
   * - ``service/metric``
     - 5
     - 1,243
     - 0
     - 2 (svc)
     - 0
     - Metrics emission and key registry
   * - ``sqs``
     - 8
     - 370
     - 0
     - 0
     - 5
     - SQS consumer infrastructure
   * - ``stratus``
     - 8
     - 587
     - 1
     - 1
     - 1
     - AI Gateway integration
   * - ``task``
     - 11
     - 649
     - 1 (disp)
     - 1
     - 6
     - Async task framework
   * - ``utility``
     - 8
     - 557
     - 0
     - 1
     - 0
     - Threading, tenant service, user model
   * - **Totals**
     - **117**
     - **7,819**
     - **6**
     - **7**
     - **30**
     -

† Feature sub-module counts are estimates within the shared ``feature``
package (20 files, 730 LoC total).

Module Details
==============

client
------

:Package: ``io.atlassian.micros.proactiveai.client``
:Sub-packages: ``identity/``, ``identity/internal/``
:Key classes:
   - ``IdGatekeeperClient`` — synchronous identity resolution interface
   - ``AsyncIdGatekeeperClient`` — coroutine-based async variant
   - ``Audiences`` — audience definition constants
   - ``HttpClientCommons`` — shared HTTP client utilities

Provides HTTP clients for the ID Gatekeeper external service.  Both sync
and async variants follow the interface + ``internal/`` implementation
pattern.

config
------

:Package: ``io.atlassian.micros.proactiveai.config``
:Key classes:
   - ``MvcSecurityConfig`` — Spring Security + SLAUTH configuration
   - ``WebMvcConfiguration`` — MVC interceptor registration
   - ``MicrosEnvironmentConfig`` — environment detection (staging/prod)
   - ``OnLongRunWorkerNodeOrLocalCondition`` — conditional for LongRun nodes
   - ``OnSHWorkerNodeOrLocalCondition`` — conditional for SHWorker nodes

Configures Spring MVC, security, and worker-group conditional beans.

context
-------

:Package: ``io.atlassian.micros.proactiveai.context``
:Key classes:
   - ``TenantContext`` — tenant resolution and propagation
   - ``CloudIdContext`` — cloud site identifier
   - ``OrgIdContext`` — organization identifier
   - ``PlatformTenantContext`` — platform-level tenant info
   - ``AIGatewayContext`` — AI Gateway session context
   - ``Experience`` / ``Product`` — experience and product enums

Data model classes for multi-tenant context.  No Spring components — these
are pure Kotlin data classes and enums consumed by interceptors and services.

exception
---------

:Package: ``io.atlassian.micros.proactiveai.exception``
:Key classes:
   - ``RestClientException`` — base exception for REST client errors

Single-file module providing the exception hierarchy for HTTP client failures.

feature/nudge
-------------

:Package: ``io.atlassian.micros.proactiveai.feature.nudge``
:Sub-packages: ``api/domain/``, ``api/dto/``, ``api/rest/``
:Key classes:
   - ``NudgeThrottleController`` — REST endpoint for nudge throttle checks
   - ``NudgeType`` — enum of nudge categories
   - ``NudgeThrottleRequest`` / ``NudgeThrottleResponse`` — API DTOs

Implements the nudge throttling API that prevents notification fatigue by
rate-limiting proactive AI nudges per user and type.

feature/rovoinsights
--------------------

:Package: ``io.atlassian.micros.proactiveai.feature.rovoinsights``
:Sub-packages: ``api/``, ``api/dto/``, ``api/fetch/``, ``api/rest/``, ``api/status/``, ``internal/``, ``system/``
:Key classes:
   - ``RovoInsightsController`` — fetch and status REST endpoints
   - ``RovoInsightsTestController`` — test-mode generation endpoint
   - ``RovoInsightsGenerationTask`` — task definition for async generation
   - ``RovoInsightsGenerationTaskHandler`` — processes generation tasks
   - ``RovoInsightsGenerationSqsQueueConsumer`` — SQS consumer for LongRun
   - ``Config`` — Rovo Insights-specific configuration

The primary feature module.  Dispatches insight generation as async tasks
to the ``rovo_insights_generation`` SQS queue, consumed by LongRun worker
nodes.

featuregate
-----------

:Package: ``io.atlassian.micros.proactiveai.featuregate``
:Sub-packages: ``internal/``
:Key classes:
   - ``FeatureService`` — feature flag evaluation interface
   - ``FeatureServiceImpl`` — evaluation implementation with caching
   - ``FeatureFlagContextService`` — resolves evaluation context
   - ``FeatureFlagEvaluationTracker`` — tracks flag evaluations for analytics
   - ``AiFeatureGates`` — AI-specific feature gate definitions
   - ``PermanentFeatureGates`` — long-lived feature gate definitions

Wraps the Atlassian Feature Gate Client (Switcheroo) with service-specific
context resolution and evaluation tracking.

greeting
--------

:Package: ``io.atlassian.micros.proactiveai.greeting``
:Key classes:
   - ``WebServiceController`` — sample REST endpoint with ``SampleResponse``

Minimal health-check and sample endpoint.  Useful for deployment verification.

interceptor
-----------

:Package: ``io.atlassian.micros.proactiveai.interceptor``
:Sub-packages: ``internal/``
:Key classes:
   - ``RequestContextInterceptor`` — populates request context from headers
   - ``UserContextInterceptor`` — resolves authenticated user
   - ``CommonContextSetter`` — sets MDC and metric tags
   - ``CommonContextSetterImpl`` — implementation
   - ``LoggingContextClearingFilter`` — clears stale MDC on thread reuse

The interceptor chain that processes every inbound HTTP request.  See
:doc:`02-request-lifecycle` for the full flow.

logging
-------

:Package: ``io.atlassian.micros.proactiveai.logging``
:Key classes:
   - ``LaasLogger`` — primary structured logging interface
   - ``LaasLoggerFactory`` — factory for creating LaasLogger instances
   - ``WithUGCLogger`` — UGC-safe logging variant
   - ``InterceptedLogger`` — testable logging decorator
   - ``NoopLogger`` — null-object logger for testing
   - ``LoggerExtensions`` — Kotlin extension functions

Comprehensive structured logging framework built on SLF4J with LAAS
integration, UGC safety, and testing support.

requestcontext
--------------

:Package: ``io.atlassian.micros.proactiveai.requestcontext``
:Sub-packages: ``internal/``
:Key classes:
   - ``RequestScopedValuesInitter`` — initializes request-scoped values
   - ``RequestScopedValueOwner`` — interface for value lifecycle management
   - ``LoggingContext`` — logging MDC management
   - ``RequestContextValues`` — aggregated request context
   - ``MiscellaneousRequestContextVariablesService`` — miscellaneous values

The largest module by file count.  Manages the lifecycle of all
request-scoped values through a registration-based ownership model.

service/metric
--------------

:Package: ``io.atlassian.micros.proactiveai.service.metric``
:Sub-packages: ``internal/``
:Key classes:
   - ``MetricsService`` — business metric emission interface
   - ``MetricsServiceImpl`` — Micrometer-based implementation
   - ``CoreMetricsService`` — infrastructure metric emission
   - ``CoreMetricsServiceImpl`` — implementation
   - ``MetricKey`` — metric name and tag definitions

The largest module by LoC (1,243 lines).  Provides a type-safe metrics API
over Micrometer with predefined metric keys and tag sets.

sqs
---

:Package: ``io.atlassian.micros.proactiveai.sqs``
:Key classes:
   - ``AnalyticsEventsSqsQueueConsumer`` — raw SQS consumer for analytics
   - ``AnalyticsEventsMessageQueueConsumer`` — message-level consumer
   - ``AnalyticsEnrichedEventHandler`` — enriched event processor
   - ``MessageQueueConsumerMiddleware`` — processing middleware chain
   - ``SqsEventConsumerConfig`` — SQS consumer Spring configuration
   - ``StreamHubEvent`` — StreamHub event model
   - ``QueueNames`` — queue name constants

SQS consumer infrastructure for StreamHub analytics events.  Runs on
SHWorker nodes only.

stratus
-------

:Package: ``io.atlassian.micros.proactiveai.stratus``
:Sub-packages: ``internal/``
:Key classes:
   - ``AIGatewayService`` — AI Gateway orchestration interface
   - ``AIGatewayServiceImpl`` — implementation
   - ``AIGatewayClientConfiguration`` — Spring client configuration
   - ``IntegrationServiceMcpServerConfig`` — MCP server setup
   - ``IntegrationServiceMcpSessionManager`` — MCP session lifecycle
   - ``IntegrationServiceToolProvider`` — tool registration for MCP
   - ``StratusTestController`` — test endpoint
   - ``WeatherTool`` — sample MCP tool implementation

AI Gateway integration with MCP protocol support for tool-calling.

task
----

:Package: ``io.atlassian.micros.proactiveai.task``
:Sub-packages: ``internal/``
:Key classes:
   - ``AsyncTask`` — task definition base class
   - ``AsyncTaskHandler`` — task processing interface
   - ``AsyncTaskService`` — task dispatch interface
   - ``AsyncTaskServiceImpl`` — SQS-backed dispatch implementation
   - ``AsyncTaskDispatcher`` — routes tasks to handlers
   - ``AsyncTaskQueueRegistry`` — maps task types to SQS queues
   - ``VisibilityExtendingSQSQueueConsumer`` — auto-extending consumer

The async task framework.  Fully documented in the legacy
``ARCHITECTURE_INDEX.md`` (5★ maturity rating).

utility
-------

:Package: ``io.atlassian.micros.proactiveai.utility``
:Sub-packages: ``tenant/``, ``threading/``, ``user/``, ``user/internal/``
:Key classes:
   - ``TcsService`` — Tenant Context Service client
   - ``ThreadConfig`` — thread pool configuration
   - ``InstrumentedDispatcher`` — metrics-instrumented coroutine dispatcher
   - ``CoroutineMonitor`` — coroutine health monitoring
   - ``RequestAttributesCoroutineContext`` — Spring request attrs in coroutines
   - ``User`` — user model interface
   - ``UserImpl`` — implementation

Shared utilities for threading (coroutine infrastructure), tenant service
access, and user modeling.
