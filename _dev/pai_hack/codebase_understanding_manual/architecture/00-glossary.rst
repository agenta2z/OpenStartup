.. _pai-glossary:

==========
Glossary
==========

.. glossary::

   Application
      Root Spring Boot entry point. Defined in ``Application.kt`` with
      ``@SpringBootApplication`` annotation. Calls ``SpringApplication.run()``
      to bootstrap the component scan of ``io.atlassian.micros.proactiveai.*``
      packages.

   PAI / Proactive AI Platform
      The team and the service. The service ID is ``proactive-ai-platform``;
      the team owns it via Slack channel ``#help-ai-experience``. Deployed
      as a Micros Spring Boot service with 118 source files totalling ~7,765 LoC.

   AI Gateway
      Atlassian's internal LLM gateway. PAI does **not** call OpenAI/Anthropic
      directly — every LLM call routes through AI Gateway via the Stratus SDK.
      Endpoint env var: ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL``.

   Stratus
      Atlassian's AI Gateway client SDK (Kotlin). Provides ``UnifiedLlmProvider``,
      agent builders, and MCP integration. Configured in ``stratus/StratusAIGatewayClientConfiguration.kt``.
      See :doc:`cross-cutting/07-ai-gateway-and-stratus`.

   WebMvcConfiguration
      Spring ``@Configuration`` bean that registers interceptors in the HTTP
      request pipeline. Defined in ``config/WebMvcConfiguration.kt``. Adds
      ``RequestContextInterceptor`` and ``UserContextInterceptor`` via
      ``addInterceptors()``.

   MvcSecurityConfig
      Spring security configuration with ``@EnableWebSecurity`` annotation.
      Defined in ``config/MvcSecurityConfig.kt``. Configures SLAuth (service-to-service
      JWT authentication) for incoming requests.

   MCP
      Model Context Protocol. PAI integrates MCP via
      ``IntegrationServiceMcpServerConfig`` / ``IntegrationServiceMcpSessionManager``
      / ``IntegrationServiceToolProvider`` to give Stratus agents access to
      Atlassian product tools.

   MetricKey
      Enum of all metric names emitted by PAI. Defined in ``service/metric/MetricKey.kt``.
      Values include histogram keys (``ROVO_INSIGHTS_LATENCY_MS``, ``LLM_CALL_LATENCY_MS``)
      and counter keys (``NUDGE_SHOWN_TOTAL``, ``INSIGHTS_GENERATED_TOTAL``).

   HistogramMetric
      A tagged metric with success/error Status and latency. Defined in
      ``service/metric/HistogramMetric.kt``. Extends ``ResultMetricBase`` and
      emits to Micrometer via SignalFx.

   ResultMetricBase
      Abstract base for metrics with a Status enum (SUCCESS, ERROR, etc.). Defined in
      ``service/metric/ResultMetricBase.kt``. Provides template for histogram
      and counter metrics to inherit common tagging logic.

   Status (metric enum)
      Enum in ``service/metric/Status.kt`` with values SUCCESS, ERROR, FAILURE,
      RATE_LIMITED, TIMEOUT, etc. Attached to every metric for routing and
      alerting in SignalFx.

   CoroutineMonitor
      Wrapper for Kotlin coroutine launch/async calls that injects metric
      recording and MDC propagation. Defined in ``utility/CoroutineMonitor.kt``.
      Used to instrument all coroutine work with observability context.

   InstrumentedDispatcher
      Custom coroutine ``CoroutineDispatcher`` that wraps a thread pool with
      Micrometer instrumentation. Defined in ``config/ThreadConfig.kt``. Provides
      queue-depth, active-thread, and latency metrics for async work.

   RequestAttributesCoroutineContext
      Custom coroutine context element that carries servlet request attributes
      through async boundaries. Defined in ``requestcontext/RequestAttributesCoroutineContext.kt``.
      Enables MDC and feature-gate context to flow from HTTP thread to coroutine workers.

   RequestContextExtractor
      Utility for extracting identity triples (request_id, tenant_id, account_id) from
      HTTP headers, SQS message attributes, or request attributes. Defined in
      ``requestcontext/RequestContextExtractor.kt``.

   HeaderConstants
      Constants for HTTP header names used throughout PAI. Defined in
      ``requestcontext/HeaderConstants.kt``. Includes ``X_REQUEST_ID``, ``X_TENANT_ID``,
      ``X_ACCOUNT_ID``, etc.

   CommonContextSetter
      Interceptor/handler that populates request scope with identity context before
      business logic runs. Defined in ``requestcontext/CommonContextSetter.kt``.
      Sets up MDC, servlet attributes, and coroutine context for downstream use.

   ExperienceContext
      Domain context model for a user's product experience (mobile/web/CLI). Defined in
      ``context/ExperienceContext.kt``. References Product, Experience, and UseCase enums.

   DataContext
      Domain context model for data workspace context. Defined in
      ``context/DataContext.kt``. References DataWorkspace and Product.

   ProductContext
      Aggregation of ExperienceContext + DataContext. Defined in
      ``context/ProductContext.kt``. Used by controllers to pass product shape to services.

   DataWorkspace
      Enum for workspace types (e.g., JIRA_WORKSPACE, CONFLUENCE_SPACE). Defined in
      ``context/DataWorkspace.kt``.

   Product (enum)
      Enum of Atlassian products (JIRA, CONFLUENCE, etc.). Defined in ``context/Product.kt``.
      Used to route insight generation and nudge logic.

   Experience (enum)
      Enum of user experience channels (WEB, MOBILE, CLI). Defined in ``context/Experience.kt``.
      Determines how nudges and insights are delivered.

   UseCase (enum)
      Enum of feature use cases (ISSUE_AT_RISK, STALE_PAGE, etc.). Defined in
      ``context/UseCase.kt``. Maps to Rovo Insights and nudge types.

   Branding (enum)
      Enum for UX branding variants (ROVO, NEUTRAL). Defined in ``context/Branding.kt``.
      Determines UI styling for nudges and insights.

   HelpSeekerExperience (enum)
      Enum for help-seeking modes (PROACTIVE, REACTIVE, COPILOT). Defined in
      ``context/HelpSeekerExperience.kt``. Controls nudge vs. on-demand behavior.

   FeatureFlagEvaluationTracker
      Service that records feature-flag evaluation events for analytics. Defined in
      ``featuregate/FeatureFlagEvaluationTracker.kt``. Emits to GASv3 via StreamHub.

   MiscellaneousRequestContextVariablesService
      Service that populates optional request-scoped variables (trace_id, org_id, etc.)
      from IdGatekeeper responses. Defined in ``requestcontext/MiscellaneousRequestContextVariablesService.kt``.

   RequestScopedValueOwners
      Registry of all classes that own request-scoped values (RequestContextInterceptor,
      UserContextInterceptor, etc.). Defined in ``requestcontext/RequestScopedValueOwners.kt``.
      Used to coordinate cleanup.

   SetContextUndo
      Functional interface for cleanup code. Defined in ``requestcontext/SetContextUndo.kt``.
      Each setter returns an ``() -> Unit`` undo function to clear context on request exit.

   ExceptionLogLevel
      Enum for log levels applied to exceptions. Defined in ``exception/ExceptionLogLevel.kt``.
      Values: ERROR (default), WARN, INFO, DEBUG. Used to suppress noise from expected failures.

   RestClientException
      Base exception type for REST client errors. Defined in ``exception/RestClientException.kt``.
      Subclasses: IdGatekeeperException, AIGatewayException, etc. Carries HTTP status and body.

   Rovo Insights
      A user-facing AI feature that produces actionable workspace-level insights
      (Jira issues at risk, stale Confluence pages, etc.) on demand. The
      ``feature/rovoinsights`` package is the implementation.

   Nudge
      A proactive UX prompt shown in product (e.g. "Summarise the changes in
      this Confluence page since you last viewed it"). The ``feature/nudge``
      package decides whether/when to show one — *not* the content itself.

   Conversation starter
      A specific kind of nudge surfaced in Rovo Chat ("Want to ask: …?"). Owned
      jointly by AIX and Confluence today; PAI provides the throttle decision.

   SLAuth / SlAuth
      Atlassian Service Authentication — service-to-service auth via signed JWT.
      Headers: ``X-Slauth-*``. PAI uses
      ``micros-spring-boot-starter-security-slauth-server``.

   ASAP
      Atlassian Service Authentication Protocol. JWT-based, used by SLAuth.

   IdGatekeeper
      Atlassian's identity service for user-context enrichment. Endpoint env var:
      ``MESH_DEPENDENCY_ID_GATEKEEPER_BASE_URL``. Wrapped by ``client/identity/``.

   Statsig
      Atlassian's feature-flag platform (gates, dynamic config, experiments).
      Wrapped by the ``featuregate`` package via the
      ``com.atlassian.spring.boot:featuregate-client-starter`` dependency.

   TAP / TAP traits
      Targeting & Personalisation platform. Used by the team's broader nudge
      strategy for fatigue control. PAI does not call TAP directly today; the
      hardcoded throttle in ``feature/nudge`` is the placeholder.

   GASv3
      Atlassian Generic Analytics Service v3. Event ingestion pipeline. PAI
      consumes ``StreamHubEvent`` instances from a downstream queue
      (``analytics_events``).

   StreamHub
      Atlassian's analytics event-streaming pipeline. Sits between GASv3 and PAI's
      SQS consumer. Events arrive as ``EventAVI`` (Analytics Enriched UI Created)
      payloads.

   Beacon
      Internal name used in some PAI design docs for the analytics-event
      capture path. Today's implementation is the StreamHub→SQS path described above.

   Async task / AsyncTask
      A serializable JSON envelope (``@JsonTypeInfo`` discriminated) submitted
      via ``AsyncTaskService`` to AWS SQS, processed by a worker JVM. See
      :doc:`cross-cutting/06-async-tasks-and-sqs`.

   AsyncTaskExecutionContext
      The tenant_id / request_id / account_id triple that travels with every
      async task as SQS message attributes so the worker can replay MDC.

   SHWorkers
      The Atlassian Micros worker group that drains the
      ``analytics_events`` SQS queue. Activated by
      ``OnSHWorkerNodeOrLocalCondition``.

   LongRun
      The Atlassian Micros worker group that drains long-running async-task
      queues (e.g. ``rovo-insights-generation-queue``). Activated by
      ``OnLongRunWorkerNodeOrLocalCondition``.

   Visibility extension
      An SQS message-lifecycle pattern: a long-running consumer periodically
      heartbeats the message's visibility timeout so it is *not* re-delivered
      while still being processed. PR #103 introduced this and reported an 8×
      throughput uplift.

   DLQ
      Dead-Letter Queue. An SQS-level fallback queue that receives messages
      after a configurable number of unsuccessful redeliveries. Used by all PAI
      task queues.

   Micros
      Atlassian's PaaS for service deployment. PAI is a Spring Boot Micros
      service (``id("io.atlassian.micros.springboot") version "7.10.0"`` in
      ``build.gradle.kts``).

   POCO
      Atlassian's service catalog / policy-of-controls system. PAI's policies
      live in ``src/main/resources/policies/service/``.

   Slauth audience
      A constant identifying the *callee* in a service-to-service call. PAI uses
      audiences ``AI_GATEWAY`` and ``ID_GATEKEEPER`` today
      (see ``client/Audiences.kt``).

   LoggingContextClearingFilter
      Servlet Filter that clears MDC between requests to prevent context leakage.
      Defined in ``config/LoggingContextClearingFilter.kt``. Registered as a Spring
      ``@Component`` and runs after each HTTP request completes.

   LaasLogger
      PAI's wrapper over SLF4J. Defined in ``logging/LaasLogger.kt``. Auto-merges MDC plus
      caller-supplied key-value pairs into every log call via
      ``infoWithContext()``, ``warnWithContext()``, ``errorWithContext()``.

   MDC
      Mapped Diagnostic Context — SLF4J's per-thread key-value store used for
      structured logging. PAI populates it with ``request_id``, ``tenant_id``,
      ``account_id``, ``org_id``, ``trace_id`` etc.

   SignalFx
      The metrics backend. Micrometer ``MeterRegistry`` emits to a Micros
      observability sidecar that filters by prefix (``proactive-ai.``) and
      forwards to SignalFx.

   Redisx / Valkey
      Atlassian's managed Redis (Valkey 7.x). Provisioned in
      ``service-descriptor.sd.yml`` as ``proactive-ai-cache``. Single-primary
      + 1 replica; used for general-purpose caching (e.g. throttle decisions,
      Rovo Insights de-duplication).

   Spinnaker
      The deployment platform. PAI deploys via
      ``default-pipelines.spinnaker.yaml``.

   Nebulae
      Atlassian's gradle plugin family for Micros services. PAI declares
      Nebulae plugins in ``nebulae.yml`` for staging configuration (PR #105).

   Tome
      Atlassian's SLO/SLI platform. (Not yet wired up for PAI; placeholder
      called out in ``service-descriptor.sd.yml`` runbook references.)

   Habitual AI usage
      The team's primary FY26 H2 verb — the OKR target is to grow monthly AI
      *invocations via proactive experiences* from 400K to 1.5M. See
      :doc:`cross-cutting/01-business-and-technical-goals`.
