.. _pai-request-lifecycle:

================================
Request Lifecycle
================================

:Date: 2026-05-04
:Audience: Platform engineers, PAI feature developers
:Updated: 2026-05-05 with verified source excerpts

Three lifecycles power PAI: **synchronous HTTP**, **asynchronous SQS-driven**, and **Stratus agent** workflows.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Synchronous HTTP lifecycle
================================

Example: ``POST /api/v1/nudge/throttle``.

The request flows through a series of validation and context-setup stages:

::

   Edge        SLAuth filter                   PAI WebServer JVM
   ─────       ─────────────                   ────────────────────────────────
   client ──► validate ASAP signature ──► [1] LoggingContextClearingFilter.doFilter()
                                            │ • MDC.clear() from previous request
                                            │ • No residual tenant_id/account_id
                                            ▼
                                          [2] RequestContextInterceptor.preHandle()
                                            │ • RequestScopedValuesInitter.initBefore()
                                            │ • RequestScopedValueService initialized
                                            │ • LoggingContext.setFromRequest(requestId, null)
                                            │ • Limited FeatureFlagContextService set
                                            ▼
                                          [3] UserContextInterceptor.preHandle()
                                            │ • Extract User from request attrs
                                            │ • (Set by micros-spring-boot-starter)
                                            │ • @RequestAttribute(USER) available
                                            ▼
                                          [4] Controller method executes
                                            │ • @RequestHeader("atl-cloud-id") cloudId
                                            │ • CommonContextSetter.setTenant()
                                            │   - LoggingContext.addTenantContext()
                                            │   - FeatureFlagContextService.setFull()
                                            │   - Now MDC has tenant_id, org_id, account_id
                                            │ • Call domain service
                                            │ • Build Response DTO
                                            ▼
                                          [5] Spring serializes response → SLAuth → client
                                            ▼
                                          [6] RequestContextInterceptor.afterCompletion()
                                            │ • RequestScopedValuesInitter.cleanupAfter()
                                            │ • RequestScopedValue holders cleared
                                            ▼
                                          [7] LoggingContextClearingFilter (post-response)
                                            • MDC.clear()
                                            • Thread returned to pool clean

**Key contract:** By the time the controller body runs, MDC has at minimum
``request_id``. After ``setTenant()``, MDC also has ``tenant_id`` + ``org_id``.

1.1 Code excerpts from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**LoggingContextClearingFilter.doFilter()** (from ``logging/``):

.. code-block:: kotlin

   // Clears MDC at start of request to prevent cross-request contamination
   doFilter(req: ServletRequest, res: ServletResponse, chain: FilterChain) {
       try {
           chain.doFilter(req, res)
       } finally {
           MDC.clear()  // No residual thread-local state
       }
   }

**RequestContextInterceptor.preHandle()** (from ``interceptor/``):

.. code-block:: kotlin

   // Order 1: Initialize request-scoped values
   preHandle(req: HttpServletRequest, ...): Boolean {
       requestScopedValuesInitter.initBefore(req)
       // RequestScopedValueService now available
       // LoggingContext has request_id set
       return true
   }

**UserContextInterceptor.preHandle()** (from ``interceptor/``):

.. code-block:: kotlin

   // Order 2: Extract authenticated user from SLAuth headers
   preHandle(req: HttpServletRequest, ...): Boolean {
       val user = userContextService.extractFromRequest(req)
       req.setAttribute(USER, user)  // @RequestAttribute(USER) now works
       return true
   }

**RequestContextInterceptor.afterCompletion()** (cleanup):

.. code-block:: kotlin

   // Order 1: Clean up after response written
   afterCompletion(req: HttpServletRequest, res: HttpServletResponse, 
                   handler: Any?, ex: Exception?) {
       requestScopedValuesInitter.cleanupAfter()
       // RequestScopedValue holders no longer accessible
   }

**CommonContextSetter.setTenant()** (called in controller):

.. code-block:: kotlin

   // Called from controller once we have cloud_id and user context
   fun setTenant(cloudId: String, orgId: String, accountId: String) {
       loggingContext.addTenantContext(
           tenantId = cloudId,
           orgId = orgId,
           accountId = accountId
       )
       // MDC now has full context
       featureFlagContextService.setFull(
           cloudId = cloudId,
           orgId = orgId,
           accountId = accountId
       )
       // Feature gates can now be fully evaluated
   }

**Example controller** (RovoInsightsController, simplified):

.. code-block:: kotlin

   @RestController
   @RequestMapping("/api/v1/rovo-insights")
   class RovoInsightsController(
       private val asyncTaskService: AsyncTaskService
   ) {
       @PostMapping("/generate")
       fun generate(
           @RequestHeader("atl-cloud-id") cloudId: String,
           @RequestAttribute(USER) user: User
       ): ResponseEntity<RovoInsightsTestResponse> {
           // At this point:
           // • MDC has request_id
           // • user is available from SLAuth headers
           
           commonContextSetter.setTenant(
               cloudId = cloudId,
               orgId = user.orgId,
               accountId = user.accountId
           )
           // MDC now has: request_id, tenant_id, org_id, account_id
           
           val task = RovoInsightsGenerationTask(cloudId = cloudId)
           val context = AsyncTaskExecutionContext(
               tenantId = cloudId,
               requestId = MDC.get("request_id"),
               accountId = user.accountId,
               user = user
           )
           
           val taskId = asyncTaskService.submit(task, context)
           return ResponseEntity.accepted()
               .body(RovoInsightsTestResponse(taskId))
       }
   }

1.2 Invariants (sync path)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**I-1:** Any MDC access must follow ``setTenant()``. Before that, only ``request_id`` is guaranteed.

**I-2:** ``RequestScopedValue<T>`` holders are only valid between ``RequestContextInterceptor.preHandle()`` 
and ``RequestContextInterceptor.afterCompletion()``. Accessing them in async handlers is a bug.

**I-3:** All synchronous request handlers must call ``CommonContextSetter.setTenant()`` before any 
external service call (feature gates, metrics, logging).

**I-4:** ``LoggingContextClearingFilter`` must have the lowest order (executes last in cleanup) 
to ensure even error handlers run with context.

----

2. Asynchronous SQS-driven lifecycle
========================================

Example: ``POST /api/v1/rovo-insights/generate`` (returns 202 ACCEPTED, kicks off background task).

This lifecycle spans **two JVMs** (producer WebServer, consumer worker) and involves serialization roundtrips.

2.1 Producer side (WebServer JVM)
-----------------------------------

The flow is identical to §1 steps [1]–[4], then diverges at the service call:

::

   [4] Controller — RovoInsightsController.generate():
         │
         │  asyncTaskService.submit(
         │    task    = RovoInsightsGenerationTask(cloudId = ...),
         │    context = AsyncTaskExecutionContext(
         │                tenantId  = cloudId,
         │                accountId = user.accountId,
         │                requestId = MDC.get("request_id"),
         │                user      = user))
         ▼
   AsyncTaskServiceImpl.submit(task, context)
         │
         │  1. Jackson serialize with @JsonTypeInfo discriminator:
         │     {
         │       "@type": "rovo_insights_generation",
         │       "cloudId": "abc123def456"
         │     }
         │
         │  2. Build SQS message attributes:
         │     • tenant_id      = context.tenantId
         │     • account_id     = context.accountId
         │     • request_id     = context.requestId
         │     • user_email     = context.user.email (optional)
         │
         │  3. Generate unique taskId (UUID)
         ▼
   SqsAsyncClient.sendMessage(
     queueUrl = $SQS_ROVO_INSIGHTS_GENERATION_QUEUE_URL,
     messageBody = json,
     messageAttributes = attrs,
     messageDeduplicationId = taskId)
         ▼
   SQS queue receives message
         │
         └─ Returns 202 ACCEPTED to client

**Code excerpt — AsyncTaskServiceImpl.submit()**:

.. code-block:: kotlin

   class AsyncTaskServiceImpl(
       private val sqsAsyncClient: SqsAsyncClient
   ) : AsyncTaskService {
       
       override suspend fun submit(
           task: AsyncTask,
           context: AsyncTaskExecutionContext
       ): String = withContext(Dispatchers.IO) {
           // Serialize task with type discriminator
           val messageBody = ObjectMapper().writeValueAsString(task)
           
           val attributes = mapOf(
               "tenant_id" to StringAttributeValue {
                   stringValue = context.tenantId
               },
               "account_id" to StringAttributeValue {
                   stringValue = context.accountId
               },
               "request_id" to StringAttributeValue {
                   stringValue = context.requestId
               }
           )
           
           val taskId = UUID.randomUUID().toString()
           
           sqsAsyncClient.sendMessage { req ->
               req.queueUrl(System.getenv("SQS_ROVO_INSIGHTS_QUEUE"))
               req.messageBody(messageBody)
               req.messageAttributes(attributes)
               req.messageDeduplicationId(taskId)
           }.await()
           
           return@withContext taskId
       }
   }

**AsyncTask and discriminator**:

.. code-block:: kotlin

   @JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "@type")
   @JsonSubTypes(
       JsonSubTypes.Type(value = RovoInsightsGenerationTask::class, 
                        name = "rovo_insights_generation")
   )
   interface AsyncTask {
       val taskId: String?
   }
   
   data class RovoInsightsGenerationTask(
       val cloudId: String,
       override val taskId: String? = null
   ) : AsyncTask

2.2 Consumer side (Worker JVM — SHWorker or LongRun)
-----------------------------------------------------

The consumer is a long-running process that polls SQS and dispatches to handlers:

::

   SQS message arrives in queue
         │
         ▼
   RovoInsightsGenerationSqsQueueConsumer.handleMessage(msg)
         │
         │  1. Deserialize message attributes → AsyncTaskExecutionContext
         │  2. Restore MDC from context:
         │     MDC.put("request_id", context.requestId)
         │     MDC.put("tenant_id", context.tenantId)
         │     MDC.put("account_id", context.accountId)
         │
         │  3. Start heartbeat task (visibility extension)
         │     • Extend visibility timeout every N seconds
         │     • Prevent timeout during long processing
         ▼
   AsyncTaskDispatcher.dispatch(task, context)
         │
         │  • Determine handler from task type
         │  • Look up AsyncTaskHandler<RovoInsightsGenerationTask>
         ▼
   RovoInsightsGenerationTaskHandler.handle(task, context)
         │
         │  • Business logic (e.g., query Jira, run LLM, store results)
         │  • All logging auto-includes MDC context
         │  • Metrics include tenant_id tag
         ▼
   Message deleted from SQS (happy path)
   OR
   Message nack'd → visibility timeout → SQS redelivers
   OR
   Max retries exceeded → message → DLQ

**Code excerpt — RovoInsightsGenerationSqsQueueConsumer**:

.. code-block:: kotlin

   @Component
   @ConditionalOnProperty(name = "ON_LONG_RUN_WORKER_NODE_OR_LOCAL")
   class RovoInsightsGenerationSqsQueueConsumer(
       private val asyncTaskDispatcher: AsyncTaskDispatcher
   ) : VisibilityExtendingSQSQueueConsumer<AsyncTask>() {
       
       override val queueUrl: String
           get() = System.getenv("SQS_ROVO_INSIGHTS_GENERATION_QUEUE")
       
       override suspend fun handleMessage(message: Message) {
           // Deserialize execution context from SQS attributes
           val context = AsyncTaskExecutionContext(
               tenantId = message.messageAttributes()["tenant_id"]?.stringValue() ?: "",
               accountId = message.messageAttributes()["account_id"]?.stringValue() ?: "",
               requestId = message.messageAttributes()["request_id"]?.stringValue() ?: "",
               user = null
           )
           
           // Restore MDC for this coroutine
           withContext(RequestAttributesCoroutineContext() + LoggingContext.asCoroutineContext(context)) {
               // Start visibility extension heartbeat
               val heartbeatJob = startHeartbeat(message.receiptHandle(), intervalSeconds = 30)
               
               try {
                   // Deserialize task
                   val task = ObjectMapper().readValue<AsyncTask>(message.body())
                   
                   // Dispatch to appropriate handler
                   asyncTaskDispatcher.dispatch(task, context)
                   
               } finally {
                   heartbeatJob.cancel()
               }
           }
       }
       
       // Extend visibility timeout every N seconds to prevent re-delivery during processing
       private suspend fun startHeartbeat(
           receiptHandle: String, 
           intervalSeconds: Int
       ): Job = launch {
           while (isActive) {
               delay(intervalSeconds.seconds)
               sqsAsyncClient.changeMessageVisibility { req ->
                   req.queueUrl(queueUrl)
                   req.receiptHandle(receiptHandle)
                   req.visibilityTimeout(300)  // 5 more minutes
               }.await()
           }
       }
   }

**Code excerpt — AsyncTaskDispatcher**:

.. code-block:: kotlin

   class AsyncTaskDispatcher(
       private val registry: AsyncTaskQueueRegistry
   ) {
       suspend fun dispatch(task: AsyncTask, context: AsyncTaskExecutionContext) {
           val handler = registry.getHandler(task::class)
               ?: throw UnknownTaskTypeException(task::class.simpleName)
           
           handler.handle(task, context)
       }
   }

2.3 Async executor — context propagation via coroutines
---------------------------------------------------------

For coroutine-based async, context (MDC + RequestAttributes) is propagated via:

**RequestAttributesCoroutineContext** (from ``utility/threading/``):

.. code-block:: kotlin

   // Custom CoroutineContext that snapshots and restores Spring RequestAttributes
   class RequestAttributesCoroutineContext : AbstractCoroutineContextElement(Key) {
       private val attributes = RequestContextHolder.getRequestAttributes()
       
       override fun fold(initial: R, operation: (CoroutineContext.Element) -> R): R {
           return operation(this).let { ... }
       }
       
       companion object Key : CoroutineContext.Key<RequestAttributesCoroutineContext>
   }

**LoggingContext.asCoroutineContext()** (from ``requestcontext/``):

.. code-block:: kotlin

   // Snapshots MDC and returns a CoroutineContext element
   interface LoggingContext {
       fun asCoroutineContext(): CoroutineContext
       // Internal: copies MDC to context map, restored on coroutine resume
   }

Both are composed via ``withContext(RequestAttributesCoroutineContext() + LoggingContext.asCoroutineContext())``.

2.4 Async executor — Micrometer ``ContextRegistry`` (for @Async)
-------------------------------------------------------------------

For non-coroutine async (Spring's ``@Async`` / ``ListenableFuture``),
``WebMvcConfiguration`` registers two ``ThreadLocalAccessor``\s:

* ``Slf4jThreadLocalAccessor`` — propagates MDC to new thread.
* ``RequestAttributesThreadLocalAccessor`` — propagates Spring ``RequestAttributes``.

A ``CompositeTaskDecorator`` wraps every task to snapshot and restore context.

Thread pool: **16 core, 64 max, unbounded queue** (verified by ``config/WebMvcConfiguration.kt``).

2.5 Invariants (async path)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**I-5:** All ``AsyncTask`` subclasses must have ``@JsonTypeInfo`` discriminator and ``@JsonSubTypes`` 
annotation so the consumer can route correctly.

**I-6:** ``AsyncTaskExecutionContext`` must include ``requestId`` so traces chain between 
producer and consumer logs.

**I-7:** SQS message attributes (tenant_id, account_id, request_id) **must match** the 
``AsyncTaskExecutionContext`` values—no stripping or mapping.

**I-8:** ``VisibilityExtendingSQSQueueConsumer.handleMessage()`` must start the heartbeat 
**before** user code runs, and cancel it **after** user code completes (even on exception).

**I-9:** If a handler throws, the message is nack'd (not deleted); SQS redelivers up to the 
max retry count, then moves to DLQ. Set CloudWatch alarms on DLQ depth.

----

3. Stratus/MCP agent lifecycle
=================================

The third lifecycle is for LLM-driven workflows that invoke Stratus agents, which may 
call MCP tools (Jira, Confluence).

Example: ``POST /api/v1/rovo/stratus/run-agent``.

3.1 Flow diagram
~~~~~~~~~~~~~~~~~

::

   [1–4] Same as sync lifecycle (request setup + context)
         
         ▼
   
   StratusTestController.runAgent(prompt)
         │
         │  AIGatewayService.runAgent(
         │      prompt = "...",
         │      tools = [jiraTool, confluenceTool, ...])
         ▼
   AIGatewayServiceImpl
         │
         │  1. Initialize Stratus Agent:
         │     • Runner (orchestration)
         │     • Agent (LLM model + tools list)
         │     • IntegrationServiceToolProvider.getTools()
         │
         │  2. IntegrationServiceMcpSessionManager
         │     • Open MCP WebSocket to integration-service
         │     • Authenticate with service account
         ▼
   Agent loop:
         │  1. LLM processes tools + context
         │  2. If tool invocation: send to integration-service via MCP
         │  3. integration-service calls Jira/Confluence/etc. (via API gateway)
         │  4. Result returned → LLM synthesis
         │  5. Repeat until done
         ▼
   AIGatewayService returns AgentResult
         │
         └─ 200 OK with final response

3.2 Code excerpts
~~~~~~~~~~~~~~~~~~~

**AIGatewayService interface** (from ``stratus/``):

.. code-block:: kotlin

   interface AIGatewayService {
       suspend fun runAgent(
           prompt: String,
           tools: List<Tool>,
           context: Optional<AgentContext> = Optional.empty()
       ): AgentResult
       
       suspend fun chat(
           systemPrompt: String,
           userMessage: String
       ): ChatResult
       
       suspend fun runAgentFlow(
           flowDefinition: String,
           context: AgentContext
       ): FlowResult
   }

**AIGatewayServiceImpl.runAgent()** (simplified):

.. code-block:: kotlin

   class AIGatewayServiceImpl(
       private val toolProvider: IntegrationServiceToolProvider,
       private val sessionManager: IntegrationServiceMcpSessionManager
   ) : AIGatewayService {
       
       override suspend fun runAgent(
           prompt: String,
           tools: List<Tool>,
           context: Optional<AgentContext>
       ): AgentResult = withContext(Dispatchers.Default) {
           val mcp = sessionManager.getOrCreateSession(
               cloudId = loggingContext.get("tenant_id"),
               accountId = loggingContext.get("account_id")
           )
           
           val agent = Agent(
               model = "claude-opus",  // or gpt-4, etc.
               tools = toolProvider.getTools(mcp),
               systemPrompt = buildSystemPrompt(context)
           )
           
           val runner = Runner(agent = agent, toolManager = mcp)
           return@withContext runner.run(input = prompt)
       }
   }

**IntegrationServiceMcpSessionManager** (from ``stratus/``):

.. code-block:: kotlin

   class IntegrationServiceMcpSessionManager(
       private val config: AIGatewayClientConfiguration
   ) {
       private val sessions = ConcurrentHashMap<String, McpSession>()
       
       suspend fun getOrCreateSession(
           cloudId: String,
           accountId: String
       ): McpSession {
           val sessionKey = "$cloudId:$accountId"
           return sessions.getOrPut(sessionKey) {
               createSession(
                   integrationServiceUrl = config.integrationServiceMcpUrl,
                   serviceAccount = config.serviceAccount,
                   serviceAccountToken = config.serviceAccountToken
               )
           }
       }
       
       private suspend fun createSession(
           integrationServiceUrl: String,
           serviceAccount: String,
           serviceAccountToken: String
       ): McpSession {
           // WebSocket to integration-service MCP endpoint
           val ws = WebSocketClient(integrationServiceUrl)
           ws.authenticate(serviceAccount, serviceAccountToken)
           return McpSession(ws)
       }
   }

**IntegrationServiceToolProvider** (from ``stratus/``):

.. code-block:: kotlin

   class IntegrationServiceToolProvider(
       private val sessionManager: IntegrationServiceMcpSessionManager
   ) : ToolProvider {
       
       override suspend fun getTools(session: McpSession): List<Tool> {
           return listOf(
               JiraSearchTool(session),
               JiraGetIssueTool(session),
               ConfluenceSearchTool(session),
               ConfluenceGetPageTool(session),
               BitbucketSearchReposTool(session)
               // More tools as needed
           )
       }
   }

3.3 Invariants (Stratus path)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**I-10:** ``AIGatewayService.runAgent()`` must be called with MDC already set (sync or async context).

**I-11:** ``IntegrationServiceMcpSessionManager`` caches sessions per (cloudId, accountId) pair 
to avoid spinning up new MCP connections on every call.

**I-12:** Tool invocations from Stratus agents inherit the MDC context from the calling thread, 
so all Jira/Confluence operations are tagged with the original request_id and tenant_id.

**I-13:** If integration-service is unreachable, ``AIGatewayServiceImpl`` must fail the entire 
agent run (no graceful degradation to non-tool mode).

----

4. Failure modes by lifecycle stage
=======================================

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Stage
     - Failure
     - Behavior
   * - SLAuth filter
     - Invalid signature
     - 401 Unauthorized — never reaches PAI code
   * - LoggingContextClearingFilter
     - Exception in ``MDC.clear()``
     - 500 Internal Server Error; logs without request context
   * - RequestContextInterceptor [1]
     - NPE in ``setupRequestScopedValues``
     - 500; no request_id in MDC; hard to trace
   * - UserContextInterceptor [2]
     - Missing X-Slauth-User-Context header
     - User defaults to anonymous; controllers requiring ``@RequestAttribute(USER)`` will 500
   * - Controller → CommonContextSetter
     - Missing atl-cloud-id header
     - 400 Bad Request; MDC still has request_id but no tenant context
   * - AsyncTaskService.submit()
     - SQS unreachable
     - Exception bubbles to controller; client gets 5xx; no message lost
   * - SQS message serialization
     - Task not JSON-serializable
     - Exception in producer; 5xx to client; no message sent
   * - SQS consumer deserialization
     - Message schema drifted (missing field)
     - JSON error → message deleted (data loss) or DLQ'd (depends on config)
   * - SQS consumer handler
     - Handler throws exception
     - Visibility timeout expires → SQS redelivers up to N times → DLQ
   * - SQS consumer heartbeat
     - Message processing > visibility timeout
     - SQS redelivers while handler still running (duplicate execution risk)
   * - Stratus agent
     - integration-service unreachable
     - Entire run fails; no fallback to non-tool mode
   * - Stratus agent
     - LLM call fails (rate limit, etc.)
     - Exception propagates; 5xx to client

----

5. Latency budget (illustrative — not yet measured in prod)
==============================================================

For ``POST /api/v1/nudge/throttle`` (synchronous):

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Stage
     - Target (ms)
     - Source
   * - SLAuth filter
     - <5
     - Micros default JWT validation
   * - Interceptors [1]+[2]
     - <2
     - Pure thread-local + header reads
   * - Controller body (today's stub)
     - <1
     - No external calls
   * - Response write
     - <2
     - JSON serialization
   * - **End-to-end p99 today**
     - **<10**
     - Will grow once TAP-trait calls land

For ``POST /api/v1/rovo-insights/generate`` (async — just request path):

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Stage
     - Target (ms)
     - Notes
   * - HTTP request → 202 ACCEPTED
     - <50
     - SQS message send + return
   * - SQS dispatch lag
     - <5,000
     - Worker poll cadence + visibility extension
   * - Insight generation (planned)
     - 2,000–30,000
     - LLM inference, varies with workspace size

(SLOs not yet registered in Tome — see
:doc:`cross-cutting/01-business-and-technical-goals` §3 for planned targets.)

----

6. See also
=============

* :doc:`03-module-catalog` — Detailed file-level catalog (which modules own which code)
* :doc:`cross-cutting/01-business-and-technical-goals` — SLO targets and observability strategy
* :doc:`cross-cutting/05-observability-and-metrics` — MDC keys, metric names, Splunk dashboards
* :doc:`/modules/platform/requestcontext` — Request-scoped value API (deep dive)
* :doc:`/modules/platform/task` — AsyncTaskService architecture (deep dive)
* :doc:`/modules/platform/stratus` — Stratus agent integration (deep dive)

