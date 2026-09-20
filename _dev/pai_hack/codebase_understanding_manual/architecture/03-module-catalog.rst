.. _pai-module-catalog:

================================
Module Catalog
================================

:Date: 2026-05-04
:Audience: All developers
:Updated: 2026-05-05 with verified file counts and deep-dive references

File-level and package-level catalog of the entire PAI codebase (118 files, 7,765 LoC).
Use this to look up "what does module X do?", "what's the test coverage?", and find deep-dive documentation.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

0. Quick reference: Package statistics
=========================================

.. list-table:: Package-level summary (LoC verified via static analysis)
   :header-rows: 1
   :widths: 18 12 12 12 18 28

   * - Package
     - Files
     - LoC
     - Tests
     - Status
     - Key responsibility
   * - client
     - 7
     - 399
     - 0
     - Stable
     - IdGatekeeper + AsyncIdGatekeeper HTTP clients
   * - client/identity
     - 5
     - 373
     - 2
     - Stable
     - User identity lookups (sync/async)
   * - config
     - 6
     - 208
     - 0
     - Stable
     - Spring MVC, worker-node detection, environment config
   * - context
     - 9
     - 381
     - 0
     - Stable
     - TenantContext, Product/Experience enums, interface hierarchy
   * - exception
     - 1
     - 116
     - 0
     - Stable
     - RestClientException typed errors
   * - feature
     - 20
     - 730
     - —
     - Active
     - User-facing features (nudge, rovoinsights)
   * - feature/nudge
     - 4
     - 72
     - 1
     - Stable
     - Nudge throttle endpoint
   * - feature/rovoinsights
     - 16
     - 658
     - 2
     - Active
     - Rovo insights generation (async + stratus)
   * - featuregate
     - 8
     - 754
     - 1
     - Stable
     - Feature flag evaluation + experiments
   * - greeting
     - 1
     - 56
     - 1
     - Stable
     - Example controller (template)
   * - interceptor
     - 5
     - 295
     - 4
     - Stable
     - HTTP context interceptors (order 1, 2, 3)
   * - logging
     - 6
     - 568
     - 7
     - Stable
     - LaasLogger, MDC context, UGC flagging
   * - requestcontext
     - 14
     - 906
     - 2
     - Stable
     - RequestScopedValue<T>, LoggingContext, header constants
   * - service/metric
     - 5
     - 1,243
     - 2
     - Stable
     - Micrometer metrics, histogram bins, result tracking
   * - sqs
     - 8
     - 302
     - 1
     - Stable
     - Analytics events + message queue middleware
   * - stratus
     - 8
     - 587
     - 1
     - Active
     - AIGatewayService, MCP sessions, tools
   * - task
     - 11
     - 649
     - 4
     - Active
     - AsyncTaskService, dispatcher, SQS consumers
   * - utility
     - 8
     - 557
     - —
     - Stable
     - Threading utilities, user model, TCS integration
   * - utility/threading
     - 5
     - 454
     - 0
     - Stable
     - Coroutine context propagation, dispatchers
   * - utility/tenant
     - 1
     - 14
     - 0
     - Stable
     - TCS service stub
   * - utility/user
     - 2
     - 89
     - 0
     - Stable
     - User interface + implementation
   * - ROOT
     - 1
     - 14
     - 4
     - Stable
     - Top-level health check, example test
   * - **TOTAL**
     - **118**
     - **7,765**
     - **32**
     - —
     - —

**Test coverage by package:**

.. list-table:: Test file inventory (32 test files total)
   :header-rows: 1
   :widths: 25 10 65

   * - Package
     - Test count
     - Test files
   * - logging
     - 7
     - LoggingContextTest, LaasLoggerTest, UGCLoggerTest, + 4 more
   * - interceptor
     - 4
     - RequestContextInterceptorTest, UserContextInterceptorTest, + 2 more
   * - task
     - 4
     - AsyncTaskServiceTest, AsyncTaskDispatcherTest, VisibilityExtendingConsumerTest, + 1 more
   * - root-level
     - 4
     - ArchUnitTest, ExampleTest, HealthCheckIT, RovoInsightsControllerIT
   * - client/identity
     - 2
     - IdGatekeeperClientTest, AsyncIdGatekeeperClientTest
   * - service/metric
     - 2
     - MetricsServiceTest, HistogramBucketTest
   * - requestcontext
     - 2
     - RequestContextExtractorTest, LoggingContextImplTest
   * - featuregate
     - 1
     - FeatureServiceTest
   * - stratus
     - 1
     - AIGatewayServiceTest
   * - sqs
     - 1
     - SqsEventConsumerTest
   * - feature/nudge
     - 1
     - NudgeThrottleControllerTest
   * - feature/rovoinsights
     - 2
     - RovoInsightsControllerTest, RovoInsightsTaskHandlerTest
   * - greeting
     - 1
     - WebServiceControllerTest

----

1. ``feature/`` — vertical user-facing slices (20 files, 730 LoC)
==================================================================

User-facing features are organized as vertical slices: controller → DTO → domain logic → async handlers.

1.1 ``feature/rovoinsights/`` (16 files, 658 LoC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Rovo Insights generation—async background jobs that produce AI-powered summaries for Jira/Confluence.

**Key types:**

* ``RovoInsightsController`` (@RestController) — endpoints for status check, fetch
* ``RovoInsightsTestController`` (@RestController) — endpoint to trigger generation (202 Accepted)
* ``RovoInsightsGenerationTask`` (data class, implements AsyncTask) — SQS message type
* ``RovoInsightsGenerationTaskHandler`` (implements AsyncTaskHandler<RovoInsightsGenerationTask>) — main logic
* ``RovoInsightsGenerationSqsQueueConsumer`` (extends VisibilityExtendingSQSQueueConsumer) — SQS listener
* ``InsightType`` (enum: STALE_PAGES, AT_RISK_ISSUES, CYCLE_TIME, SPRINT_COMMITMENT, + 7 more)
* ``Strategy`` (enum: EVALUATE, SKIP)
* ``Color``, ``Glyph`` (enums for UI rendering)

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``RovoInsightsController.kt``
     - REST endpoints: status check, fetch insights
     - ~60
   * - ``RovoInsightsTestController.kt``
     - REST endpoint: trigger generation
     - ~50
   * - ``RovoInsightsGenerationTask.kt``
     - AsyncTask impl with @JsonTypeInfo discriminator
     - ~40
   * - ``RovoInsightsGenerationTaskHandler.kt``
     - Core logic: queries Jira/Confluence, LLM synthesis
     - ~120
   * - ``RovoInsightsGenerationSqsQueueConsumer.kt``
     - SQS listener with visibility extension
     - ~80
   * - ``api/rest/RovoInsightsTestController.kt``
     - Request/response handlers
     - ~20
   * - ``api/dto/RovoInsightsTestRequest.kt``
     - Empty request DTO
     - ~5
   * - ``api/dto/RovoInsightsTestResponse.kt``
     - ``{taskId: String}`` response
     - ~5
   * - ``api/status/RovoInsightsStatusRequest.kt``
     - Polling request DTO
     - ~10
   * - ``api/status/RovoInsightsStatusResponse.kt``
     - ``{insightsAvailable: Boolean}`` response
     - ~10
   * - ``api/fetch/RovoInsightsFetchRequest.kt``
     - Insight retrieval request DTO
     - ~15
   * - ``api/fetch/RovoInsightsFetchResponse.kt``
     - Complex response with insight groups
     - ~30
   * - ``domain/InsightType.kt``
     - Enum of insight categories (11 values)
     - ~20
   * - ``domain/Strategy.kt``
     - Enum: EVALUATE, SKIP
     - ~5
   * - ``system/RovoInsightsQueueConfiguration.kt``
     - SQS queue URL binding
     - ~15
   * - ``system/RovoInsightsEnvironmentProperties.kt``
     - Environment variable mapping
     - ~10

**Tests:** 2 files
- ``RovoInsightsControllerTest`` — controller integration test
- ``RovoInsightsTaskHandlerTest`` — handler logic test

**See also:** :doc:`/modules/features/rovo-insights` (feature deep-dive) and :doc:`/modules/rovo-insights/index` (multi-page system-types + API + generation deep-dive).

1.2 ``feature/nudge/`` (4 files, 72 LoC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Nudge throttling—rate-limiting user-facing hints/prompts.

**Key types:**

* ``NudgeThrottleController`` (@RestController) — POST /api/v1/nudge/throttle
* ``NudgeThrottleRequest`` (DTO: nudgeType)
* ``NudgeThrottleResponse`` (DTO: delaySeconds, suppress flag)
* ``NudgeType`` (enum: SUMMARISE_CHANGES, CONVERSATION_STARTER)

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``api/rest/NudgeThrottleController.kt``
     - REST endpoint: throttle check
     - ~30
   * - ``api/dto/NudgeThrottleRequest.kt``
     - Request DTO
     - ~5
   * - ``api/dto/NudgeThrottleResponse.kt``
     - Response DTO
     - ~10
   * - ``api/domain/NudgeType.kt``
     - Enum of nudge categories
     - ~27

**Tests:** 1 file
- ``NudgeThrottleControllerTest`` — endpoint test

**See also:** :doc:`/modules/features/nudge` (feature deep-dive) and :doc:`/modules/nudge/nudge-throttle` (endpoint-level contract).

1.3 ``feature/greeting/`` (1 file, 56 LoC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Example/template REST controller showing interceptor + context usage.

**Key types:**

* ``WebServiceController`` (@RestController) — GET /greetings/{name}

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``WebServiceController.kt``
     - Example endpoint (template)
     - 56

**Tests:** 1 file
- ``WebServiceControllerTest`` — basic endpoint test

**See also:** Refer to this when adding new REST endpoints.

----

2. ``requestcontext/`` — request-scoped state (14 files, 906 LoC)
==================================================================

**Purpose:** Manage request-scoped values (MDC, feature flags, logging context) that persist 
across interceptor → controller → async boundaries.

**Key types & interfaces:**

* ``LoggingContext`` (interface) — MDC management: ``setFromRequest()``, ``addTenantContext()``, ``asCoroutineContext()``
* ``RequestScopedValueService<T>`` (interface) — get/set holder per request
* ``RequestScopedValue<T>`` (interface) — typed holder (e.g., LoggingContext, FeatureFlagContextService)
* ``RequestScopedValueOwner`` (interface) — registers itself with holder
* ``RequestScopedValueKey`` (enum) — discriminates value types
* ``RequestContextExtractor`` (object) — static helpers to extract values from request
* ``HeaderConstants`` (object) — X-Slauth-*, atl-cloud-id, etc.
* ``MiscellaneousRequestContextVariablesService`` — misc context setup (feature flags in limited mode)
* ``RequestScopedValuesInitter`` (interface) — ``initBefore()`` / ``cleanupAfter()`` hooks
* ``SetContextUndo`` (interface) — RAII-style context unwinding

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``LoggingContext.kt`` (interface)
     - MDC context API + default impl
     - ~80
   * - ``RequestScopedValueService.kt``
     - Holder service interface
     - ~40
   * - ``RequestScopedValue.kt``
     - Typed holder interface
     - ~30
   * - ``RequestScopedValueOwner.kt``
     - Base interface for context owners
     - ~20
   * - ``RequestScopedValueKey.kt``
     - Enum: LOGGING_CONTEXT, FEATURE_FLAG_CONTEXT, etc.
     - ~15
   * - ``RequestContextExtractor.kt``
     - Static helpers for header extraction
     - ~50
   * - ``HeaderConstants.kt``
     - Header name constants
     - ~25
   * - ``MiscellaneousRequestContextVariablesService.kt``
     - Bootstraps limited-mode feature flags
     - ~35
   * - ``SetContextUndo.kt``
     - Context restoration interface
     - ~20
   * - ``impl/LoggingContextImpl.kt``
     - Concrete LoggingContext using SLF4J MDC
     - ~100
   * - ``impl/RequestContextExtractor.kt``
     - Implementation of header extraction
     - ~45
   * - ``impl/RequestScopedValueServiceImpl.kt``
     - ThreadLocal-based holder registry
     - ~60
   * - ``impl/RequestScopedValuesInitter.kt``
     - Lifecycle hooks (init/cleanup)
     - ~55
   * - ``impl/MiscellaneousVariablesService.kt``
     - Misc context setup impl
     - ~40

**Tests:** 2 files
- ``RequestContextExtractorTest`` — header parsing tests
- ``LoggingContextImplTest`` — MDC context tests

**See also:** :doc:`/modules/platform/requestcontext` (deep dive: context propagation rules, invariants)

----

3. ``interceptor/`` — HTTP request interceptors (5 files, 295 LoC)
==================================================================

**Purpose:** Three-stage HTTP request interception: (1) setup request-scoped values, (2) extract user, (3) clear context after response.

**Key types & interfaces:**

* ``RequestContextInterceptor`` — Order 1: init request-scoped values
* ``UserContextInterceptor`` — Order 2: extract User from SLAuth headers
* ``CommonContextSetter`` (interface) — abstraction for setting full context
* ``CommonContextSetterImpl`` — wires logging + feature-flag + misc context
* ``LoggingContextClearingFilter`` — post-response: MDC.clear()

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``RequestContextInterceptor.kt``
     - Order 1: init + cleanup
     - ~70
   * - ``UserContextInterceptor.kt``
     - Order 2: extract user
     - ~50
   * - ``CommonContextSetter.kt`` (interface)
     - Abstraction for full context setup
     - ~30
   * - ``internal/CommonContextSetterImpl.kt``
     - Wires logging + feature-flag + misc
     - ~60
   * - ``internal/LoggingContextClearingFilter.kt``
     - Post-response MDC cleanup
     - ~85

**Tests:** 4 files
- ``RequestContextInterceptorTest``
- ``UserContextInterceptorTest``
- ``CommonContextSetterTest``
- ``LoggingContextClearingFilterTest``

**See also:** :doc:`02-request-lifecycle` §1 (sync lifecycle), :doc:`/modules/platform/interceptor` (deep dive: order + interaction rules)

----

4. ``logging/`` — logging infrastructure (6 files, 568 LoC)
===============================================================

**Purpose:** Structured logging with automatic MDC merging, UGC redaction, and per-log metrics.

**Key types & interfaces:**

* ``LaasLogger`` — SLF4J wrapper auto-merging MDC + context map
* ``LaasLoggerFactory`` (object) — ``getLogger(class)`` factory
* ``InterceptedLogger`` — wrapper that emits a metric per log call
* ``WithUGCLogger`` — specialized logger that flags UGC fields for redaction
* ``NoopLogger`` — test double / disabled-feature placeholder
* ``LogKey`` (enum) — ~15 standard MDC keys (request_id, tenant_id, account_id, etc.)

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``LaasLogger.kt``
     - Core logger interface
     - ~120
   * - ``LaasLoggerFactory.kt``
     - Factory + object def
     - ~30
   * - ``impl/LaasLoggerImpl.kt``
     - SLF4J-based impl
     - ~150
   * - ``InterceptedLogger.kt``
     - Metrics-emitting wrapper
     - ~40
   * - ``WithUGCLogger.kt``
     - UGC redaction logger
     - ~80
   * - ``NoopLogger.kt``
     - No-op test double
     - ~30
   * - ``LoggerExtensions.kt``
     - Kotlin extension functions
     - ~118

**Tests:** 7 files
- ``LaasLoggerTest``
- ``LaasLoggerImplTest``
- ``InterceptedLoggerTest``
- ``WithUGCLoggerTest``
- ``LogKeyTest``
- ``LoggerExtensionsTest``
- ``LoggingIntegrationTest``

**See also:** :doc:`cross-cutting/05-observability-and-metrics` (MDC keys, logging standards)

----

5. ``service/metric`` — metrics and observability (5 files, 1,243 LoC)
=======================================================================

**Purpose:** Centralized metrics collection via Micrometer: histograms, counters, timers.

**Key types & interfaces:**

* ``MetricsService`` (interface) — high-level metrics API
* ``CoreMetricsService`` (interface) — core platform metrics
* ``MetricKey`` (enum) — ~12 standard metrics (p99_latency, error_rate, cache_hit_ratio, etc.)
* ``HistogramMetric`` (enum) — histogram definitions (request_duration, task_queue_depth, etc.)
* ``ResultMetricBase`` (enum) — outcomes: SUCCESS, FAILURE, SKIPPED, ERROR
* ``HistogramBucket`` (enum) — standard SLA boundaries (10ms, 50ms, 100ms, 500ms, 1s, 5s, 30s)
* ``Status`` (enum) — SUCCESS, FAILURE, SKIPPED, ERROR

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``MetricsService.kt`` (interface)
     - Public metrics API
     - ~100
   * - ``CoreMetricsService.kt`` (interface)
     - Platform-level metrics
     - ~150
   * - ``impl/MetricsServiceImpl.kt``
     - Micrometer impl
     - ~400
   * - ``impl/HistogramConfiguration.kt``
     - Histogram bin config
     - ~250
   * - ``model/`` (4 files)
     - Enums + data classes for metrics
     - ~343

**Tests:** 2 files
- ``MetricsServiceTest``
- ``HistogramBucketTest``

**See also:** :doc:`/modules/platform/service-metric` (deep dive: histogram bins, SLA definitions)

----

6. ``task/`` — async task dispatch (11 files, 649 LoC)
=======================================================

**Purpose:** Asynchronous task orchestration: submit tasks to SQS, dispatch to handlers, manage visibility timeouts.

**Key types & interfaces:**

* ``AsyncTaskService`` (interface) — ``submit(task, context)``, ``submitToLongRunQueue()``
* ``AsyncTaskHandler<T>`` (interface) — ``handle(task, context)`` for specific task type
* ``AsyncTask`` (interface) — base type with @JsonTypeInfo discriminator
* ``AsyncTaskDispatcher`` — routes task to correct handler by type
* ``AsyncTaskQueueRegistry`` — registry of available handlers
* ``AsyncTaskExecutionContext`` (data class) — tenantId, requestId, accountId, user
* ``VisibilityExtendingSQSQueueConsumer`` (abstract class) — SQS consumer with heartbeat

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``AsyncTaskService.kt`` (interface)
     - Submit API
     - ~50
   * - ``AsyncTaskHandler.kt`` (interface)
     - Handler base interface
     - ~40
   * - ``AsyncTask.kt`` (interface)
     - Task base type with @JsonTypeInfo
     - ~35
   * - ``impl/AsyncTaskServiceImpl.kt``
     - SQS submission impl
     - ~120
   * - ``impl/AsyncTaskDispatcher.kt``
     - Handler routing logic
     - ~60
   * - ``impl/AsyncTaskQueueRegistry.kt``
     - Handler registration
     - ~70
   * - ``consumer/VisibilityExtendingSQSQueueConsumer.kt``
     - SQS listener base with heartbeat
     - ~140
   * - ``context/AsyncTaskExecutionContext.kt``
     - Execution context DTO
     - ~30
   * - ``error/AsyncTaskException.kt``
     - Typed exceptions
     - ~40
   * - ``interceptor/AsyncTaskInterceptor.kt``
     - Handler pre/post hooks
     - ~50
   * - ``spring/AsyncTaskAutoConfiguration.kt``
     - Spring Boot auto-config
     - ~34

**Tests:** 4 files
- ``AsyncTaskServiceTest``
- ``AsyncTaskDispatcherTest``
- ``VisibilityExtendingConsumerTest``
- ``AsyncTaskContextTest``

**See also:** :doc:`02-request-lifecycle` §2 (async lifecycle), :doc:`/modules/platform/task` (deep dive: consumer architecture)

----

7. ``featuregate/`` — feature flags (8 files, 754 LoC)
======================================================

**Purpose:** Feature flag evaluation (limited vs. full context) and experiment tracking.

**Key types & interfaces:**

* ``FeatureService`` (interface) — ``checkGate(name, context)``, ``getExperiment()``, ``isInternalSite()``
* ``FeatureGate`` (interface) — individual gate definition
* ``AiFeatureGates`` (enum) — AI-specific gates
* ``PermanentFeatureGates`` (enum) — permanent gates (e.g., ENABLE_UGC_LOGGING)
* ``FeatureFlagContextService`` (interface) — ``setLimited()``, ``setFull(cloudId, orgId, accountId)``
* ``FeatureFlagEvaluationTracker`` — records gate evaluations for metrics

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``FeatureService.kt`` (interface)
     - Public gate API
     - ~100
   * - ``FeatureGate.kt`` (interface)
     - Gate definition interface
     - ~30
   * - ``AiFeatureGates.kt`` (enum)
     - AI feature gates
     - ~60
   * - ``PermanentFeatureGates.kt`` (enum)
     - Permanent gates
     - ~40
   * - ``FeatureFlagContextService.kt`` (interface)
     - Context setting API
     - ~50
   * - ``impl/FeatureServiceImpl.kt``
     - TAP integration
     - ~180
   * - ``impl/FeatureFlagEvaluationTracker.kt``
     - Evaluation metrics
     - ~140
   * - ``impl/FeatureFlagContextServiceImpl.kt``
     - Context management
     - ~154

**Tests:** 1 file
- ``FeatureServiceTest``

**See also:** :doc:`/modules/platform/featuregate` (deep dive: TAP trait integration, evaluation rules)

----

8. ``sqs/`` — SQS message processing (8 files, 302 LoC)
========================================================

**Purpose:** SQS queue consumers, message enrichment, and middleware for event processing.

**Key types & interfaces:**

* ``AnalyticsEventsSqsQueueConsumer`` — primary SQS listener
* ``AnalyticsEventsMessageQueueConsumer`` — message broker abstraction
* ``AnalyticsEnrichedEventHandler`` — event enrichment logic
* ``StreamHubEvent`` (data class) — event model from Streamhub
* ``SqsEventConsumerConfig`` — queue URL binding
* ``MessageQueueConsumerMiddleware`` — request/response interceptor pattern
* ``EventAVIs`` (object) — event type constants

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``AnalyticsEventsSqsQueueConsumer.kt``
     - SQS listener
     - ~70
   * - ``AnalyticsEventsMessageQueueConsumer.kt``
     - Abstraction layer
     - ~40
   * - ``AnalyticsEnrichedEventHandler.kt``
     - Event enrichment
     - ~50
   * - ``StreamHubEvent.kt``
     - Event model
     - ~45
   * - ``SqsEventConsumerConfig.kt``
     - Configuration
     - ~30
   * - ``MessageQueueConsumerMiddleware.kt``
     - Middleware base
     - ~25
   * - ``EventAVIs.kt``
     - Type constants
     - ~22
   * - ``exception/SqsException.kt``
     - Typed errors
     - ~20

**Tests:** 1 file
- ``SqsEventConsumerTest``

**See also:** :doc:`/modules/platform/sqs` (deep dive: event model, enrichment pipeline)

----

9. ``stratus/`` — LLM agent integration (8 files, 587 LoC)
===========================================================

**Purpose:** Stratus AI agent framework: runner, agent construction, MCP tool integration.

**Key types & interfaces:**

* ``AIGatewayService`` (interface) — ``runAgent(prompt, tools)``, ``chat()``, ``runAgentFlow()``
* ``AIGatewayServiceImpl`` — Stratus SDK integration
* ``IntegrationServiceMcpSessionManager`` — MCP WebSocket session pooling
* ``IntegrationServiceToolProvider`` — provides MCP tools (Jira, Confluence, etc.)
* ``IntegrationServiceMcpServerConfig`` (data class) — MCP server configuration
* ``AIGatewayClientConfiguration`` — client-side config (base URL, timeout, etc.)
* ``StratusTestController`` (@RestController) — test endpoint for agent runs

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``AIGatewayService.kt`` (interface)
     - Public agent API
     - ~80
   * - ``impl/AIGatewayServiceImpl.kt``
     - Stratus implementation
     - ~150
   * - ``impl/IntegrationServiceMcpSessionManager.kt``
     - MCP session pooling
     - ~120
   * - ``impl/IntegrationServiceToolProvider.kt``
     - Tool provision logic
     - ~100
   * - ``config/IntegrationServiceMcpServerConfig.kt``
     - MCP config DTO
     - ~50
   * - ``config/AIGatewayClientConfiguration.kt``
     - Client config
     - ~45
   * - ``api/StratusTestController.kt``
     - Test endpoint
     - ~30
   * - ``tool/WeatherTool.kt``
     - Example tool (stub)
     - ~12

**Tests:** 1 file
- ``AIGatewayServiceTest``

**See also:** :doc:`02-request-lifecycle` §3 (Stratus lifecycle), :doc:`/modules/platform/stratus` (deep dive: MCP integration, tool catalog)

----

10. ``context/`` — tenant and experience contexts (9 files, 381 LoC)
===================================================================

**Purpose:** Define tenant identity (cloud ID, org ID), product + experience enums, context interfaces.

**Key types & interfaces:**

* ``TenantContext`` (data class, implements PlatformTenantContext + AIGatewayContext + CloudIdContext + OrgIdContext) — **core context model**
* ``ProductContext`` — product-specific config
* ``DataContext`` — data classification
* ``ExperienceContext`` — UX variant config
* ``Product`` (enum: JIRA_PLATFORM, JIRA_SOFTWARE, JSM, JWM, JPD, CONFLUENCE, BITBUCKET) — 7 product lines
* ``Experience`` (enum) — UX variants (e.g., "power_user", "basic")
* ``UseCase`` (enum) — user workflow categories
* ``Branding`` (enum) — color/styling schemes
* ``HelpSeekerExperience`` (enum) — help-seeking UX variants
* ``AIGatewayContext``, ``CloudIdContext``, ``OrgIdContext``, ``PlatformTenantContext`` (interfaces) — context traits

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``TenantContext.kt`` (data class)
     - Core context model
     - ~100
   * - ``ProductContext.kt``
     - Product config
     - ~30
   * - ``DataContext.kt``
     - Data classification
     - ~25
   * - ``ExperienceContext.kt``
     - UX variant config
     - ~40
   * - ``Product.kt`` (enum)
     - Product enum (7 values)
     - ~60
   * - ``Experience.kt`` (enum)
     - Experience enum
     - ~40
   * - ``UseCase.kt`` (enum)
     - UseCase enum
     - ~30
   * - ``Branding.kt`` (enum)
     - Branding enum
     - ~35
   * - ``interfaces/`` (3 files)
     - Context interface traits
     - ~21

**Tests:** 0 files
(Context types are mostly data structures, tested via integration tests in other packages.)

**See also:** :doc:`02-request-lifecycle` (where TenantContext is set), :doc:`/modules/platform/context` (deep dive: context hierarchy)

----

11. ``client/`` — HTTP clients (7 files, 399 LoC)
=================================================

**Purpose:** HTTP clients for external services (IdGatekeeper for user identity, AI Gateway).

**Main package** (2 files, 26 LoC):

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``HttpClientCommons.kt``
     - Shared HTTP header constants
     - ~15
   * - ``Audiences.kt``
     - SLAuth audience identifiers (AI_GATEWAY, ID_GATEKEEPER)
     - ~11

**client/identity/** (5 files, 373 LoC):

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``PermissionRequest.kt``
     - Request DTO for permission checks
     - ~40
   * - ``PermissionResult.kt``
     - Response DTO
     - ~30
   * - ``IdentityClientException.kt``
     - Typed exception
     - ~20
   * - ``IdGatekeeperClient.kt`` (interface)
     - Sync client interface
     - ~50
   * - ``IdGatekeeperClientImpl.kt``
     - Sync impl (blocking future)
     - ~80
   * - ``internal/AsyncIdGatekeeperClientImpl.kt``
     - Coroutine-native async impl
     - ~100
   * - ``internal/IdGatekeeperClientExtensions.kt``
     - Helper extension functions
     - ~53

**Tests:** 2 files
- ``IdGatekeeperClientTest``
- ``AsyncIdGatekeeperClientTest``

**See also:** :doc:`/modules/platform/client` (deep dive: IdGatekeeper integration, permission model)

----

12. ``config/`` — Spring configuration (6 files, 208 LoC)
==========================================================

**Purpose:** Spring MVC setup, worker-node detection, environment binding.

**Key types:**

* ``MvcSecurityConfig`` — SLAuth + CORS configuration
* ``WebMvcConfiguration`` — async executor, ThreadLocalAccessor registration
* ``OnSHWorkerNodeOrLocalCondition`` — conditional bean for SHWorker nodes
* ``OnLongRunWorkerNodeOrLocalCondition`` — conditional bean for LongRun workers
* ``MicrosEnvironmentConfig`` — environment variable mapping
* ``MicrosEnvironmentType`` (enum) — PROD, STAGING, LOCAL

**File breakdown:**

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``MvcSecurityConfig.kt``
     - Security setup
     - ~40
   * - ``WebMvcConfiguration.kt``
     - Async + interceptor config
     - ~60
   * - ``OnSHWorkerNodeOrLocalCondition.kt``
     - SHWorker node detection
     - ~25
   * - ``OnLongRunWorkerNodeOrLocalCondition.kt``
     - LongRun worker detection
     - ~25
   * - ``MicrosEnvironmentConfig.kt``
     - Environment mapping
     - ~35
   * - ``MicrosEnvironmentType.kt`` (enum)
     - Environment enum
     - ~23

**Tests:** 0 files
(Configuration is tested via integration tests.)

**See also:** :doc:`/modules/platform/config` (deep dive: environment setup, worker node detection)

----

13. ``utility/`` — threading & user utilities (8 files, 557 LoC)
================================================================

**Purpose:** Coroutine context propagation, thread pool configuration, user model.

**utility/threading/** (5 files, 454 LoC):

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``RequestAttributesCoroutineContext.kt``
     - Spring RequestAttributes context element
     - ~70
   * - ``InstrumentedDispatcher.kt``
     - Coroutine dispatcher with monitoring
     - ~80
   * - ``CoroutineMonitor.kt``
     - Active coroutine counter
     - ~100
   * - ``ThreadConfig.kt``
     - Pool sizing constants
     - ~50
   * - ``DispatcherMonitor.kt``
     - Dispatcher snapshot API
     - ~154

**utility/user/** (2 files, 89 LoC):

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``User.kt`` (interface)
     - Authenticated user contract
     - ~40
   * - ``internal/UserImpl.kt``
     - Concrete user with X-Forwarded-* fields
     - ~49

**utility/tenant/** (1 file, 14 LoC):

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``TcsService.kt``
     - Tenant Configuration Service integration stub
     - 14

**Tests:** 0 files
(Utilities are tested via higher-level integration tests.)

**See also:** :doc:`/modules/platform/utility` (deep dive: context propagation, threading model)

----

14. ``exception/`` — typed exceptions (1 file, 116 LoC)
=========================================================

**Purpose:** Centralized exception types for HTTP client failures.

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``RestClientException.kt``
     - Typed exceptions for IdGatekeeper, AI Gateway HTTP calls; status codes, error messages
     - 116

**Tests:** 0 files
(Exception types tested via client integration tests.)

**See also:** :doc:`/modules/platform/client` (callers that raise ``RestClientException``) and :doc:`cross-cutting/05-observability-and-metrics` (exception logging standards). The ``exception/`` package itself is documented inline in the module catalogue above.

----

15. ROOT — Platform entry point (1 file, 14 LoC)
=================================================

.. list-table::
   :header-rows: 1
   :widths: 45 50 15

   * - File
     - Purpose
     - LoC
   * - ``PaiApplication.kt`` (or main entry)
     - Spring Boot application main
     - 14

**Tests:** 4 files
- ``ArchUnitTest`` — architecture validation tests
- ``ExampleTest`` — basic smoke test
- ``HealthCheckIT`` — health check endpoint IT
- ``RovoInsightsControllerIT`` — end-to-end integration test

**See also:** :doc:`01-architecture-overview` (system design)

----

16. Resources and configuration
=================================

**src/main/resources/**

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - File
     - Purpose
   * - ``application.yml``
     - SQS queue URLs (env-var binding), worker-group mapping (SHWorkers / LongRun), Micrometer histogram bins, observability sidecar prefix filter
   * - ``application-prod.yml``
     - Production-specific overrides
   * - ``application-staging.yml``
     - Staging-specific overrides
   * - ``policies/service/policy.json``
     - POCO service policy: compute-classification, retry policies, rate limits
   * - ``logback-spring.xml``
     - Log appender config (Splunk-friendly JSON layout + MDC fields)
   * - ``logback-spring-local.yml``
     - Local development logging config (console appender, DEBUG level)

----

17. File count verification by directory
==========================================

This section documents the exact file count per package (verified via ``find`` and ``wc``):

.. code-block:: text

   client/                           7 files, 399 LoC
   ├── client/identity/              5 files, 373 LoC
   ├── root files                    2 files, 26 LoC
   
   config/                           6 files, 208 LoC
   
   context/                          9 files, 381 LoC
   
   exception/                        1 file,  116 LoC
   
   feature/                          20 files, 730 LoC
   ├── feature/nudge/                4 files, 72 LoC
   ├── feature/rovoinsights/         16 files, 658 LoC
   
   featuregate/                      8 files, 754 LoC
   
   greeting/                         1 file, 56 LoC
   
   interceptor/                      5 files, 295 LoC
   
   logging/                          6 files, 568 LoC
   
   requestcontext/                   14 files, 906 LoC
   
   service/                          5 files, 1,243 LoC
   ├── service/metric/               5 files, 1,243 LoC
   
   sqs/                              8 files, 302 LoC
   
   stratus/                          8 files, 587 LoC
   
   task/                             11 files, 649 LoC
   
   utility/                          8 files, 557 LoC
   ├── utility/threading/            5 files, 454 LoC
   ├── utility/tenant/               1 file, 14 LoC
   ├── utility/user/                 2 files, 89 LoC
   
   ROOT/                             1 file, 14 LoC
   
   TOTAL: 118 files, 7,765 LoC

----

18. See also
=============

**Architecture documents:**

* :doc:`00-glossary` — Terminology (SLAuth, TAP, LLM, MCP, etc.)
* :doc:`01-architecture-overview` — System design, dependencies, data flow
* :doc:`02-request-lifecycle` — Detailed lifecycle walkthroughs (sync, async, Stratus)

**Cross-cutting:**

* :doc:`cross-cutting/01-business-and-technical-goals` — Roadmap, SLOs, observability targets
* :doc:`cross-cutting/05-observability-and-metrics` — MDC keys, metric catalog, Splunk dashboards

**Module deep-dives:**

* :doc:`/modules/platform/requestcontext` — Request-scoped value API
* :doc:`/modules/platform/logging` — LaasLogger architecture
* :doc:`/modules/platform/task` — AsyncTaskService + SQS consumer model
* :doc:`/modules/platform/featuregate` — Feature flag evaluation (TAP integration)
* :doc:`/modules/platform/stratus` — Stratus agent + MCP tool integration
* :doc:`/modules/platform/client` — HTTP client architecture (IdGatekeeper, AI Gateway)
* :doc:`/modules/platform/config` — Spring configuration, worker-node detection

