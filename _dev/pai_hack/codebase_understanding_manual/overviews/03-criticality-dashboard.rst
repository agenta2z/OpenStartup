.. _overview-criticality-dashboard:

==========================================================
Criticality dashboard — blast radius + on-call runbook
==========================================================

:Date: 2026-05-04
:Audience: SRE, on-call engineers, change-approval reviewers

This page ranks every package by **blast radius** — how many users / requests / external
systems are affected by a regression in that package. Use it to (a) prioritize incident
investigations, (b) decide whether a PR needs extra scrutiny, (c) sequence canary
rollouts.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Tiered ranking by blast radius
==================================

.. list-table::
   :header-rows: 1
   :widths: 10 25 12 53

   * - Tier
     - Package
     - Blast radius
     - Why
   * - 🔴 **P0**
     - ``Application.kt`` (ROOT, 1 file, 14 LoC)
     - Service startup
     - Missing ``@SpringBootApplication`` → entire JAR fails to bootstrap. Every instance down = 100% unavailability.
   * - 🔴 **P0**
     - ``config`` (6 files, 208 LoC)
     - Service-wide
     - WebMvcConfiguration registers interceptor chain + async executor + context propagation. Misconfig → silent context loss across all requests/tasks. Missing interceptor → MDC uninitialized.
   * - 🔴 **P0**
     - ``interceptor`` (5 files, 295 LoC)
     - Every request
     - RequestContextInterceptor + UserContextInterceptor are the first two stages of the middleware chain. A NPE/RuntimeException here breaks every endpoint (HTTP 500 for all tenants).
   * - 🔴 **P0**
     - ``requestcontext`` (14 files, 906 LoC)
     - Every request
     - MDC propagation hub. A bug here drops tenant_id → logs unattributable, metrics untagged, feature-flag decisions degenerate to defaults. All tenant visibility lost.
   * - 🔴 **P0**
     - ``stratus`` (8 files, 587 LoC)
     - All AI features
     - Every LLM call in Rovo Insights goes through ``AIGatewayService → UnifiedLlmProvider``. Stratus SDK crash = task handler failures = all insight generation fails (feature outage).
   * - 🟠 **P1**
     - ``task`` (11 files, 649 LoC)
     - All async work
     - Rovo Insights submission + handler lifecycle depends on AsyncTaskServiceImpl + AsyncTaskDispatcher. A serialization bug = silent task loss (tasks enqueued but never executed).
   * - 🟠 **P1**
     - ``sqs`` (8 files, 302 LoC)
     - All async work
     - SQS consumer middleware + visibility extension. Consumer crash = messages not drained; visibility-extension regression = messages re-delivered mid-execution.
   * - 🟠 **P1**
     - ``logging`` (6 files, 568 LoC)
     - Observability
     - LaasLoggerFactory + MDC wrapper backs every log line. Bug → blind on-call investigations (structured logs lost, debugging impossible).
   * - 🟠 **P1**
     - ``service/metric`` (5 files, 1,243 LoC)
     - Observability + alerting
     - SignalFx-fed dashboards + PagerDuty alerts depend on metric emission. A bug silences alerts or emits wrong cardinality → SRE can't detect outages.
   * - 🟠 **P1**
     - ``featuregate`` (8 files, 754 LoC)
     - Per-feature controls
     - Statsig gate defaults. Wrong default → feature on for tenants that should not have it (data loss risk). Statsig outage handled with default-value fallbacks.
   * - 🟡 **P2**
     - ``client`` (7 files, 399 LoC)
     - IdGatekeeper-dependent features
     - AsyncIdGatekeeperClient enrichment failure degrades but rarely breaks. Request proceeds with limited user context.
   * - 🟡 **P2**
     - ``context`` (9 files, 381 LoC)
     - Per-feature domain modeling
     - TenantContext, ProductContext, Experience data classes. Mostly caught by Kotlin type system at compile time.
   * - 🟡 **P2**
     - ``utility/threading`` (5 files, 454 LoC)
     - Coroutine-using code paths
     - RequestAttributesCoroutineContext propagation. Loss → MDC drops *only on the affected coroutine path*. Detectable via missing tenant_id in task logs.
   * - 🟢 **P3**
     - ``feature/rovoinsights`` (16 files, 658 LoC)
     - Rovo Insights tenants only
     - Feature isolated by product flag. Outage doesn't affect nudge or greeting endpoints. Blast limited to users with feature enabled.
   * - 🟢 **P3**
     - ``feature/nudge`` (4 files, 72 LoC)
     - Nudge-callers only
     - Synchronous endpoint; failure has tight blast radius. No async retry queue.
   * - 🟢 **P3**
     - ``feature/greeting`` (1 file, 56 LoC)
     - None (template)
     - Reference implementation, not exposed externally. Safe to break without customer impact.

2. Top 5 incident playbook entries
====================================

2.1 "All requests returning 500"
----------------------------------

**Symptom:** Every endpoint (Rovo Insights, Nudge, etc.) returns HTTP 500. Repeated across all tenants.

* **Suspect #1 (most likely):** ``RequestContextInterceptor`` or ``UserContextInterceptor`` NPE on header parsing
  → See ``interceptor/`` package (5 files, 295 LoC)
* **Suspect #2:** ``LoggingContextClearingFilter`` or ``LaasLoggerFactory`` initialization failure
  → See ``logging/`` package (6 files, 568 LoC)
* **Suspect #3:** Spring config error in ``WebMvcConfiguration`` (interceptor registration, async executor wiring)
  → See ``config/`` package (6 files, 208 LoC)

* **Diagnostic step 1:** Check CloudWatch/Splunk for exception stack trace. Filter for ``RequestContextInterceptor`` or ``UserContextInterceptor``
* **Diagnostic step 2:** Check ``X-Slauth-User-Context`` header presence in failing requests. If missing, SLAuth filter failed upstream.
* **Diagnostic step 3:** Verify ``ATL_MICROS_GROUP=WebServer`` JVM is running (not terminated OOM or segfault)

* **Mitigation:** Roll back the most recent PR touching ``interceptor/``, ``requestcontext/``, ``config/``, or ``logging/``
* **Files to ``git blame``:** ``RequestContextInterceptor.kt``, ``UserContextInterceptor.kt``, ``LoggingContextClearingFilter.kt``, ``WebMvcConfiguration.kt``

2.2 "Logs missing tenant_id (all logs unattributable)"
---------------------------------------------------------

**Symptom:** Logs from WebServer JVM show all requests with missing ``tenant_id`` in MDC. Dashboards show "unknown tenant" spike.

* **Suspect #1:** ``RequestScopedValuesInitter.setupRequestScopedValues()`` not called or throwing exception
  → See ``requestcontext/`` package (14 files, 906 LoC)
* **Suspect #2:** Controller not calling ``CommonContextSetter.setTenant()`` early enough
  → Check feature controller implementations
* **Suspect #3:** Coroutine context lost: ``RequestAttributesCoroutineContext`` not on the async executor context
  → See ``utility/threading/`` (5 files, 454 LoC)

* **Diagnostic step 1:** Search Splunk: ``service=proactive-ai-platform AND missing tenant_id``
  - If count > 0: MDC propagation broken on WebServer side
* **Diagnostic step 2:** Check worker logs: search for ``LongRun worker`` AND ``missing tenant_id``
  - If count > 0: async context not replayed by ``MessageQueueConsumerMiddleware``
* **Diagnostic step 3:** Inspect ``RequestScopedValue<TenantContext>`` in thread-local: add debug logging to CommonContextSetterImpl

* **Mitigation:** Confirm every controller calls ``commonContextSetter.setTenant()`` in the first 3 lines. Check ``RequestAttributesCoroutineContext`` is wired in async executor config.
* **Reference:** :doc:`/architecture/cross-cutting/03-request-context-and-mdc`

2.3 "Rovo Insights tasks stuck in queue"
------------------------------------------

**Symptom:** ``rovo-insights-generation-queue`` message count is growing. Status endpoint hangs or returns no results.

* **Suspect #1:** LongRun worker JVM is down or unhealthy (OOM, segfault, deployment in progress)
* **Suspect #2:** SQS visibility-extension heartbeat regression: messages being re-delivered before handler completes
  → See ``sqs/`` package (8 files, 302 LoC) and ``task/`` package (11 files, 649 LoC)
* **Suspect #3:** Task handler crash: ``RovoInsightsGenerationTaskHandler.handle()`` throwing uncaught exception
  → See ``feature/rovoinsights/`` package (16 files, 658 LoC)

* **Diagnostic step 1:** AWS SQS console → check message count in queue vs DLQ
  - If DLQ growing: tasks exhausted retries → handler consistently crashes
  - If queue growing, DLQ empty: LongRun JVM not draining
* **Diagnostic step 2:** Check Splunk for LongRun logs: ``service=proactive-ai-platform AND ATL_MICROS_GROUP=LongRun``
  - Look for visibility-extension errors: ``VisibilityExtendingSQSQueueConsumer``
  - Look for handler exceptions: ``RovoInsightsGenerationTaskHandler``
* **Diagnostic step 3:** Check Prometheus/SignalFx: metric ``proactive-ai.task.handler.duration_ms`` for P99 latency spike

* **Mitigation:** 
  - If LongRun down: page on-call, trigger deployment rollback
  - If visibility-extension issue: check PR #103 or later; verify heartbeat interval config
  - If handler crash: grep DLQ message for exception; add defensive null-checks
* **Reference:** :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs`

2.4 "Statsig feature flag returning wrong value"
--------------------------------------------------

**Symptom:** A feature is on for a tenant that should have it disabled, or vice versa. User sees feature they shouldn't.

* **Suspect:** ``FeatureFlagContextService`` building incomplete user context → Statsig defaults to fallback rule
  → See ``featuregate/`` package (8 files, 754 LoC)

* **Diagnostic step 1:** Enable Statsig exposure logging in ``FeatureService.checkGate()`` (add debug flag or env var)
  - Log the exact ``user_id``, ``account_id``, ``tenant_id``, ``hostname`` sent to Statsig
  - Cross-check against expected cohort rules in Statsig console
* **Diagnostic step 2:** Check Statsig SDK logs: is the API call succeeding? Check error count
* **Diagnostic step 3:** Check for network issue: Statsig SDK may be timing out and returning default value

* **Mitigation:** ``FeatureService.checkGate()`` **always** has a `defaultValue` parameter. Service degrades gracefully:
  - If Statsig times out or crashes: gate uses default value (e.g., ``defaultValue=false`` → feature off)
  - No full outage, just potential under/over-delivery to cohorts
* **Fallback:** Temporarily hardcode feature flag in code if Statsig is down (revert in next build)

2.5 "AI Gateway latency spike (Rovo Insights slow)"
----------------------------------------------------

**Symptom:** Rovo Insights endpoints hanging. ``/api/v1/rovo-insights/generate`` returns 504 or 202 but with task stuck in "processing" for hours.

* **Suspect #1:** AI Gateway upstream is slow or down
  → See ``stratus/`` package (8 files, 587 LoC) and :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus`
* **Suspect #2:** Our ``IntegrationServiceMcpSessionManager`` has a thread/connection leak
  → See ``stratus/`` package implementation
* **Suspect #3:** LLM model service (OpenAI, Claude) is experiencing issues

* **Diagnostic step 1:** SignalFx dashboard: check ``proactive-ai.stratus.ai_gateway.latency_ms`` (P50, P99)
  - If P99 > 30s: downstream AI Gateway degradation
  - If flat: our side is healthy
* **Diagnostic step 2:** Check AI Gateway status page / Slack #help-ai-gateway (they have dedicated SRE)
  - If AI Gateway reports degradation: they own the incident
  - If they report healthy: issue is in our ``stratus`` client code
* **Diagnostic step 3:** Check for connection/thread leaks: ``jstack`` LongRun JVM, look for blocked threads on AI Gateway socket

* **Mitigation:** 
  - AI Gateway has its own SRE rotation — page #help-ai-gateway if their status page shows red
  - PAI side: circuit-breaker (not yet implemented, but recommended) would fail fast instead of hanging
  - Restart LongRun JVM if connection leak suspected
* **Reference:** :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus`

3. Change-management heuristics
==================================

When reviewing a PR, use this rule of thumb:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - PR touches…
     - Required reviewer pattern
   * - Only ``feature/<x>``
     - 1 feature owner
   * - ``feature/<x>`` + a single platform package
     - 1 feature owner + 1 platform owner
   * - Any P0 package (``requestcontext``, ``interceptor``, ``config``, ``stratus``)
     - 2 platform owners + canary rollout flagged
   * - ``logging`` or ``service/metric``
     - 1 SRE-tagged reviewer (alert + dashboard impact must be assessed)
   * - Async-task definition (``task/`` + new handler)
     - 1 platform owner + a check that the producer & consumer JVMs deploy compatibly (no schema drift)

4. Test-coverage gaps that increase blast risk
=================================================

See also :doc:`01-multi-axis-matrix` §4 for full per-package test metrics (32 test files + 4 integration tests).

**Critical gaps (P0/P1 packages with low test coverage):**

**4.1 — ``feature/rovoinsights`` (16 files, 658 LoC) — RovoInsightsController testing**

* **Gap:** Only **RovoInsightsControllerIT** (integration test); **0 dedicated unit tests** for the controller REST endpoints.
  - Endpoints: ``POST /api/v1/rovo-insights/generate``, ``POST /api/v1/rovo-insights/status``, ``POST /api/v1/rovo-insights/fetch``
  - No unit tests for parameter validation, error response shapes, or feature-flag integration
* **Risk:** A bug in controller routing (e.g., typo in @PostMapping path) could break entire feature without compile-time detection.
* **Impact:** Rovo Insights is the **strategic FY26 H2 feature**. Regression here affects all insight-dependent Jira/Confluence workspaces.
* **Mitigation (owner: Rovo Insights feature lead):**
  - Add unit tests for RovoInsightsController (test request parsing, error cases)
  - Add unit tests for task serialization (RovoInsightsGenerationTask → JSON → back)
  - Cover feature flag disable case (verify endpoint returns 403 or no-op when flag off)
  - Minimum target: 1 test file, 10 test cases

**4.2 — ``feature/nudge`` (4 files, 72 LoC) — NudgeThrottleController testing**

* **Gap:** Only **NudgeThrottleControllerTest** exists; only 1 test file covering a 4-file feature. Current coverage: throttle stub logic only.
  - Endpoints: ``POST /api/v1/nudge/throttle``
  - Once real throttle logic ships (TAP traits, GASv3 signals), test coverage must expand
* **Risk:** If real logic is added without tests, a regression could suppress nudges for entire cohorts undetected.
* **Impact:** P3 feature (synchronous, tight blast radius), but throttling logic is critical for user experience (false positives = spam, false negatives = under-engagement).
* **Mitigation (owner: Nudge feature lead):**
  - Add tests for each throttle decision path (suppress=true, suppress=false, delaySeconds variants)
  - Add tests for TAP trait evaluation (mock TAP service calls)
  - Add error-path tests (TAP unavailable, GASv3 timeout, etc.)
  - Minimum target: same coverage ratio as Rovo Insights (1+ test files per feature)

**4.3 — ``utility/threading`` (5 files, 454 LoC) — Coroutine context propagation**

* **Gap:** **0 dedicated unit tests** for ``RequestAttributesCoroutineContext`` and ``InstrumentedDispatcher``.
  - These classes are the trickiest in the codebase to debug
  - Context loss in coroutines manifests as MDC drops only on specific async paths (very hard to diagnose)
* **Risk:** A regression here drops tenant_id in worker logs silently. On-call investigations become blind.
* **Impact:** Affects all async task handlers (Rovo Insights, future generators). P1 blast radius.
* **Mitigation (owner: Platform / async-task owners):**
  - Add unit tests for RequestAttributesCoroutineContext.apply() and .get()
  - Add integration tests for coroutine launch {} blocks: verify MDC propagates to launched task
  - Add test for InstrumentedDispatcher: verify metrics emitted + context preserved across executor boundaries
  - Minimum target: 2 test files, 15 test cases

**4.4 — ``stratus`` (8 files, 587 LoC) — AIGatewayService and tool provisioning**

* **Gap:** Only **StratusTestController** (test endpoint with WeatherTool); **0 dedicated tests** for AIGatewayService.generateInsights() or tool provider logic.
  - IntegrationServiceToolProvider.getTools() not tested
  - MCP session creation/teardown not tested
  - Tool filtering by tenant/product not tested
* **Risk:** A bug in tool provider could leak tools across tenants (security) or filter too aggressively (feature breakage).
* **Impact:** P0 for Rovo Insights generation. AI features depend on correct tool provisioning.
* **Mitigation (owner: Stratus / AI Gateway integration owner):**
  - Add unit tests for IntegrationServiceToolProvider.getTools() with mocked tenant contexts
  - Add tests for tool filtering: verify Jira tools only in Jira context, Confluence tools in Confluence context
  - Add tests for AIGatewayService.generateInsights() with mocked MCP session + LLM response
  - Minimum target: 1 test file, 10 test cases

**Summary: test-coverage debt by priority**

.. list-table::
   :header-rows: 1
   :widths: 25 15 40 20

   * - Package
     - Current coverage
     - Priority to add tests
     - Estimated effort
   * - ``feature/rovoinsights``
     - Integration only
     - **HIGH** (strategic feature)
     - 1 week (10 test cases)
   * - ``feature/nudge``
     - 1 test file
     - **HIGH** (before real logic ships)
     - 3 days (8 test cases)
   * - ``utility/threading``
     - None
     - **CRITICAL** (hard to debug)
     - 1 week (15 test cases)
   * - ``stratus``
     - None
     - **HIGH** (security + feature risk)
     - 1 week (10 test cases)
