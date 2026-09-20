.. _overview-architectural-narrative:

==========================================================
Architectural narrative — a walking tour of PAI
==========================================================

:Date: 2026-05-04

This page tells the story of the codebase end-to-end. Read it once before diving
into per-module documentation.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. The system at a glance
============================

``proactive-ai-platform`` is a **single-module Spring Boot 7.10 / Kotlin** micros service
that mediates *proactive AI experiences* across Atlassian products (Jira, Confluence, Rovo).
It is the youngest of the three "AI plumbing" services in Engineering-AI; the codebase was
bootstrapped from the **Atlassian Spring Boot template** in late 2025 and entered active
feature development in Q1 2026 (see :doc:`/architecture/cross-cutting/02-development-history`).

What makes it different from a generic Spring Boot service:

* It speaks **JVM async** (Kotlin coroutines) end-to-end — Reactor + coroutines mixed.
* Two distinct runtime topologies in the same JAR: **WebServer** (handles HTTP) and
  **LongRun worker** (drains SQS queues for async tasks). Determined by env var
  ``ATL_MICROS_GROUP``.
* Every request crosses **at least 4 cross-cutting middlewares** before reaching a
  controller (see §3 below).
* The service does not own any LLM or model — it composes **Atlassian's AI Gateway**
  via the **Stratus SDK** and routes inference through it.

**Mental model — Spring Boot wiring:**

The service bootstrap starts in ``Application.kt`` (1 file, 14 LoC) with a minimal ``@SpringBootApplication`` entry point.
Spring Boot auto-configures via classpath starters (Micros v7.10.0 + Statsig + SQS + Analytics). 

The critical wiring lives in ``config/WebMvcConfiguration.kt``:

.. code-block:: kotlin

    @Configuration
    class WebMvcConfiguration : WebMvcConfigurer {
        override fun addInterceptors(registry: InterceptorRegistry) {
            registry.addInterceptor(RequestContextInterceptor(...))
            registry.addInterceptor(UserContextInterceptor(...))
            // CommonContextSetterImpl wired as bean
        }
        // configures async executor + RequestAttributesForAsyncProcessing
    }

Every HTTP request follows this **4-stage wire path**:

.. code-block:: text

    HTTP request → WebServer JVM
      [1] LoggingContextClearingFilter (setup MDC)
      [2] RequestContextInterceptor (extract tenant_id, request_id, account_id from headers)
      [3] UserContextInterceptor (call IdGatekeeper to enrich user context)
      [4] CommonContextSetterImpl (set TenantContext, ProductContext in RequestScopedValue)
      → @Controller endpoint method
      → (if sync) write response
      → (if async) AsyncTaskService.submit() → SQS enqueue
      [1] LoggingContextClearingFilter (wipe MDC, allow thread pool reuse)
      → HTTP 200 OK sent

2. System boundary diagram
============================

::

   +-------------+       HTTP+SLAuth        +--------------------------------+
   | Atlassian   |  ─────────────────────►  | proactive-ai-platform          |
   | products    |                          |  WebServer JVM (Spring Boot)   |
   | (Jira/Conf) |  ◄───── responses ─────  |                                |
   +-------------+                          |  ┌──────────────┐              |
                                            |  │ Controller   │              |
                                            |  │ (REST)       │              |
                                            |  └──────┬───────┘              |
                                            |         │                      |
                                            |  ┌──────▼───────┐              |
                                            |  │ AsyncTaskSvc │  serialize   |
                                            |  └──────┬───────┘              |
                                            |         │                      |
                                            |   ┌─────▼────┐                 |
                                            |   │ AWS SQS  │ ◄── DLQ on max  |
                                            |   └─────┬────┘     retries     |
                                            +─────────┼──────────────────────+
                                                      │
                                            +─────────▼──────────────────────+
                                            | proactive-ai-platform          |
                                            |  LongRun worker JVM            |
                                            |  ┌──────────────┐              |
                                            |  │ SqsConsumer  │              |
                                            |  └──────┬───────┘              |
                                            |  ┌──────▼───────┐              |
                                            |  │ TaskHandler  │              |
                                            |  └──────┬───────┘              |
                                            +─────────┼──────────────────────+
                                                      │
              ┌───────────────────────────────────────┼───────────────────────────┐
              ▼                          ▼            ▼              ▼            ▼
       ┌────────────┐         ┌──────────────┐  ┌─────────┐  ┌────────────┐  ┌─────────┐
       │ AI Gateway │         │IdGatekeeper  │  │ Statsig │  │ StreamHub  │  │ SignalFx│
       │ (Stratus)  │         │  (identity)  │  │   (FF)  │  │ (analytics)│  │ (metrics)│
       └────────────┘         └──────────────┘  └─────────┘  └────────────┘  └─────────┘

3. The four middleware lanes every HTTP request crosses
==========================================================

When an HTTP request hits the WebServer JVM, it passes through **four ordered
interceptors/filters** before the controller method runs. This chain is registered in
``config/WebMvcConfiguration.kt`` (see :doc:`/modules/platform/requestcontext`):

.. list-table::
   :header-rows: 1
   :widths: 8 30 22 40

   * - Order
     - Component
     - Package
     - What it does
   * - 0
     - SlAuth filter (Micros-provided)
     - external
     - Validates ASAP/SLAuth signature; populates ``X-Slauth-*`` headers with tenant_id, user_id, signature
   * - 1
     - ``LoggingContextClearingFilter``
     - ``logging``
     - Calls ``LaasLoggerFactory.clearMdc()`` to wipe any stale MDC from thread pool reuse
   * - 2
     - ``RequestContextInterceptor``
     - ``interceptor``
     - Extracts headers: ``X-Forwarded-Request-Id``, ``X-Slauth-User-Context``, ``X-Atlassian-Tenant-Id``; calls ``RequestScopedValuesInitter.setupRequestScopedValues()`` to populate thread-local MDC with request-id, account-id, host
   * - 3
     - ``UserContextInterceptor``
     - ``interceptor``
     - Parses ``X-Slauth-User-Context`` → ``UserImpl`` bean; stores as request attribute (injectable as ``@RequestAttribute User``)
   * - 4
     - **Controller calls** ``CommonContextSetterImpl.setTenant()``
     - ``requestcontext``, ``feature/*``
     - Sets tenant_id, org_id, cloud_id into ``RequestScopedValue<TenantContext>`` and ``RequestScopedValue<ProductContext>``; enables ``LaasLogger.infoWithContext()`` to emit telemetry

After the controller returns and response is written, ``LoggingContextClearingFilter``
wipes the MDC so the **next** request on the same thread does not inherit stale tenant/user context.
This is critical for thread-pool reuse in high-throughput scenarios.

**Key code paths:**

.. code-block:: kotlin

    // From RequestContextInterceptor
    override fun preHandle(request: HttpServletRequest, ...) : Boolean {
        requestScopedValuesInitter.setupRequestScopedValues(request)
        return true
    }

    // From UserContextInterceptor
    override fun postHandle(request: HttpServletRequest, response: HttpServletResponse, ...) {
        val userImpl = parseUserFromHeader(request)
        request.setAttribute(USER, userImpl)
    }

    // From a @Controller endpoint (e.g., RovoInsightsController)
    @PostMapping("/api/v1/rovo-insights/generate")
    fun generate(@RequestAttribute user: User) : ResponseEntity<...> {
        commonContextSetter.setTenant(user.tenant_id, user.org_id)
        // Now LaasLogger.infoWithContext() will emit tenant_id in every log
        asyncTaskService.submit(RovoInsightsGenerationTask(...))
    }

4. The async-task lifecycle
==============================

Long-running work (e.g. Rovo Insights generation) is **never** done synchronously inside
the HTTP request thread. The pattern is:

::

   ┌─────────────────────────── WebServer JVM ───────────────────────────┐
   │                                                                     │
   │  Controller                                                         │
   │     │                                                               │
   │     │  asyncTaskService.submit(                                     │
   │     │    task = RovoInsightsGenerationTask(cloudId),                │
   │     │    context = AsyncTaskExecutionContext(tenant_id,             │
   │     │                                        request_id,            │
   │     │                                        account_id))           │
   │     ▼                                                               │
   │  AsyncTaskServiceImpl                                               │
   │     │  Jackson @JsonTypeInfo serialize task → JSON                  │
   │     │  Pack context into SQS message attributes                     │
   │     ▼                                                               │
   │   AWS SQS  (rovo-insights-generation-queue)                         │
   │                                                                     │
   └────────────────────────────────│────────────────────────────────────┘
                                    │ (visible in queue)
   ┌────────────────────────────────▼────────────────────────────────────┐
   │                              LongRun worker JVM                     │
   │                                                                     │
   │  RovoInsightsGenerationSqsQueueConsumer                             │
   │     │  Receive message                                              │
   │     │  Visibility-extension (heartbeat to prevent re-delivery)      │
   │     ▼                                                               │
   │  MessageQueueConsumerMiddleware                                     │
   │     │  setupRequestScopedValues()                                   │
   │     │  loggingContext.addAsyncTaskContext()  ← MDC restored         │
   │     ▼                                                               │
   │  AsyncTaskDispatcher                                                │
   │     │  type discriminator → handler lookup                          │
   │     ▼                                                               │
   │  RovoInsightsGenerationTaskHandler.handle()                         │
   │     │  (today: stub; real logic being ported)                       │
   │     ▼                                                               │
   │  onSuccess / onFailure callbacks                                    │
   │  finally { LoggingContextClearingFilter.clear() }                   │
   │                                                                     │
   └─────────────────────────────────────────────────────────────────────┘

Key invariants enforced by the framework:

**How context survives the async boundary:**

The key is that ``AsyncTaskExecutionContext`` (from ``task`` package) embeds tenant_id, request_id, account_id
as **SQS message attributes** (not in the message body). The ``MessageQueueConsumerMiddleware`` on the worker JVM
reconstructs these into the thread-local MDC **before** the handler runs (see :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs`):

.. code-block:: kotlin

    // In AsyncTaskServiceImpl.submit() [WebServer JVM]
    val context = AsyncTaskExecutionContext(
        tenantId = commonContextSetter.tenant_id,
        requestId = requestScopedValue.request_id,
        accountId = requestScopedValue.account_id
    )
    val message = SqsMessage(
        body = jackson.writeValueAsString(task),
        attributes = mapOf(
            "tenant_id" to context.tenantId,
            "request_id" to context.requestId,
            "account_id" to context.accountId
        )
    )
    sqsClient.send(message)

    // In MessageQueueConsumerMiddleware [LongRun worker JVM]
    override fun handle(message: SqsMessage, next: Consumer) {
        val context = AsyncTaskExecutionContext(
            tenantId = message.attributes["tenant_id"],
            requestId = message.attributes["request_id"],
            accountId = message.attributes["account_id"]
        )
        requestScopedValuesInitter.setupRequestScopedValues(context)
        loggingContext.addAsyncTaskContext()  // restores MDC
        try {
            next.handle(message)  // invoke handler
        } finally {
            LoggingContextClearingFilter.clear()
        }
    }

**Task handler registration:**

Handlers implement ``AsyncTaskHandler<T>`` and are discovered via Spring classpath scanning (see ``task`` package).
Each handler is responsible for deserializing the JSON body, validating the context, and invoking domain logic.
For Rovo Insights, the handler is ``RovoInsightsGenerationTaskHandler`` (16 files, 658 LoC in ``feature/rovoinsights``),
currently a stub but will invoke ``AIGatewayService`` for LLM calls.
  and are reconstructed on the worker side. A log line on the worker has the *same*
  ``request_id`` MDC tag as the originating HTTP request.
* **DLQ on max retries**: SQS-level redrive policy moves poison messages to a dead-letter
  queue after a configurable retry count (env-driven; see ``application.yml``).
* **Visibility extension**: a long-running handler periodically heartbeats so the message
  is not redelivered while the work is still in flight (see PR #103 for the 8× throughput
  win this enabled).

5. The Stratus/AI Gateway integration path
=============================================

When a feature needs to call an LLM (e.g., for Rovo Insights), the task handler invokes ``AIGatewayService``
(8 files, 587 LoC in ``stratus`` package). This service is a thin adapter over the **Stratus SDK**, which
manages MCP agent sessions, tool provisioning, and unified LLM inference (see :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus`):

.. code-block:: text

    RovoInsightsGenerationTaskHandler
      → AIGatewayService.generateInsights(input)
           → IntegrationServiceMcpSessionManager.createSession(agentId)
                → OpenAI/Claude LLM client
           → IntegrationServiceToolProvider.getTools(context)
                → Jira API client (to fetch issue content)
                → Confluence API client (to fetch page content)
           → UnifiedLlmProvider.callLlm(prompt, tools, model)
                → AI Gateway HTTP API (routed to Claude/OpenAI)
           → Parse response
           → Store result in cache/database
      ← Return to task handler

**Key invariants:**

* **Tools are provided per-context**: the tool provider filters available tools based on tenant_id,
  product (Jira vs Confluence), and user permissions.
* **MCP sessions are transient**: a session is created per request and torn down after the LLM call completes.
  This ensures tenant isolation and prevents cross-tenant tool leakage.
* **AI Gateway latency is observed**: every LLM call is wrapped with ``service/metric`` counters
  (``ai.gateway.latency_ms``, ``ai.gateway.errors``) for dashboards and alerting.
* **Feature flags gate AI calls**: ``FeatureService.checkGate(AiFeatureGates.ROVO_INSIGHTS_ENABLED, user)``
  wraps the AIGatewayService invocation. A disabled feature defaults to no-op.

**Code example:**

.. code-block:: kotlin

    // In RovoInsightsGenerationTaskHandler (stub today, production in progress)
    override suspend fun handle(task: RovoInsightsGenerationTask) {
        val context = AsyncTaskExecutionContext(...)
        val insightType = featureService.checkGate(AiFeatureGates.ROVO_INSIGHTS_ENABLED, context.user)
                         .takeIf { it } ?: return  // feature disabled, no-op

        val result = aiGatewayService.generateInsights(
            input = RovoInsightsInput(
                issueKey = task.issueKey,
                workspaceId = task.workspaceId
            ),
            metricsService = metricsService  // for instrumentation
        )
        // store result, update UI polling endpoints
    }

6. The two features that exist today
======================================

6.1 ``rovoinsights`` — async insight generation
--------------------------------------------------

REST: ``POST /api/v1/rovo-insights/generate`` accepts ``{cloud_id}``, returns
``{taskId}`` immediately (HTTP 202). Two polling endpoints:
``POST /api/v1/rovo/insights/status`` and ``POST /api/v1/rovo/insights/fetch``
return the result once the SQS-driven worker has produced it.

The handler is currently a **stub** (commit 393a5f8); the production logic is being
ported from the convo-ai/Confluence side. Strategic context: this feature is the
primary vehicle for the FY26 H2 OKR (see
:doc:`/architecture/cross-cutting/01-business-and-technical-goals`).

Deep-dive: :doc:`/modules/features/rovo-insights`.

6.2 ``nudge`` — throttle decisions for proactive notifications
------------------------------------------------------------------

REST: ``POST /api/v1/nudge/throttle`` accepts ``{nudgeType}``, returns
``{delaySeconds, suppress}``. Synchronous (no SQS).

Currently returns a hardcoded ``{delaySeconds: 10, suppress: false}`` — the real
throttle logic (TAP traits, GASv3 signals) is in the **next sprint**. Deep-dive:
:doc:`/modules/features/nudge`.

6.3 ``greeting`` — example/template
-------------------------------------

REST: ``GET /greetings/{name}`` returns a ``SampleResponse``. Kept as a working
reference for new feature authors. Deep-dive: :doc:`/modules/features/greeting`.

7. Where to go next
=====================

**Next: criticality & blast-radius analysis** → :doc:`03-criticality-dashboard`

**Related overview docs:**

* :doc:`01-multi-axis-matrix` — per-package size breakdown (118 files, 7,765 LoC)
* :doc:`03-criticality-dashboard` — incident playbooks, change-management heuristics, test-coverage gaps

**Architecture deep-dives:**

* :doc:`/architecture/cross-cutting/01-business-and-technical-goals` — FY26 H2 OKR + KPIs
* :doc:`/architecture/cross-cutting/02-development-history` — chronology and key commits
* :doc:`/architecture/cross-cutting/03-request-context-and-mdc` — how MDC propagation works
* :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs` — task serialization + durability guarantees
* :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus` — MCP session management + tool provisioning

**Module deep-dives (by package):**

* :doc:`/modules/platform/requestcontext` (14 files, 906 LoC) — request-scoped value service
* :doc:`/modules/platform/task` (11 files, 649 LoC) — async task framework
* :doc:`/modules/features/rovo-insights` (16 files, 658 LoC) — the strategic feature
