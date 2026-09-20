# 02 — Core Platform Infrastructure

**Last Updated:** 2026-05-07
**Owner:** Proactive AI Platform Team
**Service:** `proactive-ai-platform`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Request Context — `requestcontext/`](#2-request-context)
3. [Logging — `logging/`](#3-logging)
4. [Interceptors — `interceptor/`](#4-interceptors)
5. [Context Models — `context/`](#5-context-models)
6. [Metrics — `service/metric/`](#6-metrics)
7. [Feature Gates — `featuregate/`](#7-feature-gates)
8. [Async Task Framework — `task/`](#8-async-task-framework)
9. [SQS Infrastructure — `sqs/`](#9-sqs-infrastructure)
10. [Configuration — `config/`](#10-configuration)
11. [HTTP Clients — `client/`](#11-http-clients)
12. [Utilities — `utility/`](#12-utilities)
13. [Exception Handling — `exception/`](#13-exception-handling)
14. [Design Patterns Summary](#14-design-patterns-summary)

---

## 1. Overview

The platform layer comprises **12 packages** totaling **~6,446 lines of Kotlin** across **88 source files**. These packages provide the cross-cutting infrastructure that all feature code depends on.

| # | Package | Files | LoC | Responsibility |
|---|---------|-------|-----|----------------|
| 1 | `requestcontext/` | 14 | 906 | Request-scoped value storage, logging context, MDC management |
| 2 | `service/metric/` | 5 | 1,243 | Metrics abstraction (counters, gauges, histograms, timers) |
| 3 | `featuregate/` | 8 | 754 | Feature flags via Statsig, experiment tracking |
| 4 | `task/` | 11 | 649 | Async task framework — SQS-backed, visibility-extending |
| 5 | `logging/` | 6 | 568 | Structured logging, UGC-safe logging, MDC extensions |
| 6 | `utility/` | 8 | 557 | User model, coroutine infra, tenant context service |
| 7 | `client/` | 7 | 399 | HTTP client abstractions, IdGatekeeper integration |
| 8 | `context/` | 9 | 381 | Tenant context, product/experience enums, AI gateway context |
| 9 | `sqs/` | 8 | 370 | StreamHub event consumption, SQS consumer config |
| 10 | `interceptor/` | 5 | 295 | HTTP request interceptors, context initialization |
| 11 | `config/` | 6 | 208 | Spring config, worker node conditions, MVC security |
| 12 | `exception/` | 1 | 116 | REST client exception hierarchy |

### Spring Component Count

**55 total Spring-managed components**: 43 class-level annotations (`@Component`, `@Service`, `@Configuration`, `@RestController`) + 12 `@Bean` factory methods.

> **Correction note:** Doc 01 claims "~53" Spring components. The verified count is **55**.

---

## 2. Request Context

**Package:** `io.atlassian.micros.proactiveai.requestcontext`
**Files:** 14 | **LoC:** 906

### 2.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `RequestScopedValueKey.kt` | ~15 | Enum | Defines the 3 scoped value keys |
| `RequestScopedValueOwner.kt` | ~25 | Interface | Typed owner for a request-scoped value |
| `RequestScopedValueOwners.kt` | ~20 | Interface+Impl | Aggregates all owners via Spring DI |
| `RequestContextValues.kt` | ~30 | Interface | `RequestScopedValueService` — get/set/update scoped values |
| `RequestScopedValuesInitter.kt` | ~15 | Interface | Initializes all scoped values at request start |
| `SetContextUndo.kt` | ~10 | Fun interface | Undo handle for context changes |
| `RequestAttributes.kt` | ~15 | — | Request attribute extraction utilities |
| `HeaderConstants.kt` | ~5 | Object | `GEO_IP = "Atl-Edge-Geoip"` |
| `LoggingContext.kt` | ~75 | Interface | MDC context management (9 methods) |
| `LoggingContextExtensions.kt` | ~20 | Extensions | Kotlin-friendly `withContext` helpers |
| `MiscellaneousRequestContextVariablesService.kt` | ~90 | Service | X-Forwarded-For/Host, request ID extraction |
| `internal/LoggingContextImpl.kt` | ~200 | `@Service` | Full MDC implementation |
| `internal/RequestScopedValueServiceImpl.kt` | ~180 | `@Service` | Request-attribute-backed value store |
| `internal/RequestScopedValuesInitterImpl.kt` | ~35 | `@Component` | Iterates owners, sets initial values |

### 2.2 RequestScopedValueKey Enum

Exactly **3 values** — each paired with a `RequestScopedValueOwner`:

| Key | Owner Component | Value Type |
|-----|----------------|------------|
| `FEATURE_FLAG_CONTEXT` | `FeatureFlagContextService` (featuregate pkg) | Feature flag user context data |
| `FEATURE_FLAG_EVALUATION_TRACKER` | `FeatureFlagEvaluationTracker` (featuregate pkg) | List of flag evaluations for the request |
| `MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES` | `MiscellaneousRequestContextVariablesService` | X-Forwarded-For, X-Forwarded-Host, Request ID |

### 2.3 The Initter Pattern

The initter pattern ensures all request-scoped values are initialized before any request processing:

1. **`RequestScopedValueOwners`** — Spring-injected list of all `RequestScopedValueOwner<*>` beans
2. **`RequestScopedValuesInitterImpl.setupRequestScopedValues()`** — Iterates owners, calls `setInitialValue()` for each
3. **`RequestContextInterceptor.preHandle()`** — Calls initter at the start of each HTTP request
4. **`initRequestScopedValuesAndRun()`** — For non-HTTP contexts (SQS consumers), creates `RequestAttributesForAsyncProcessing`, sets up scoped values, runs the task, then cleans up

### 2.4 LoggingContext Interface (9 methods)

| Method | Description |
|--------|-------------|
| `runWithContext(Supplier<T>, Map)` | Execute block with temporary MDC entries |
| `runWithContext(Map, () -> T)` | Kotlin trailing-lambda variant |
| `runWithContextAsync(suspend () -> T, Map)` | Coroutine-aware MDC propagation |
| `addTenantContext(TenantContext)` | Add tenant ID to MDC, returns undo handle |
| `addStreamHubEventInfo(...)` | Add event ID, type, source, timestamps to MDC |
| `addAsyncTaskContext(tenantId, requestId, accountId)` | MDC setup for SQS-consumed async tasks |
| `setFromRequest(requestId, accountId)` | MDC setup from HTTP request |
| `getRequestId()` | Returns request ID (or `"request-id-missing"`) |
| `clear()` | Clears all MDC entries |

### 2.5 RequestScopedValueServiceImpl — Fallback Mechanism

When request attributes are accessed after the HTTP lifecycle completes (e.g., in async callbacks), the implementation catches `IllegalStateException` ("request is not active anymore") and transparently falls back to `RequestAttributesForAsyncProcessing` — a thread-local attribute store that survives beyond the servlet lifecycle.

### 2.6 Data Flow — Request Context Initialization

```
HTTP Request arrives
  → RequestContextInterceptor.preHandle()
    → RequestScopedValuesInitterImpl.setupRequestScopedValues()
      → For each RequestScopedValueOwner:
          → RequestScopedValueServiceImpl.setInitialValue(owner)
            → owner.newEmptyValue() → setAttribute(key, value, SCOPE_REQUEST)
    → CommonContextSetterImpl.setContext(request, response)
      → LoggingContext.setFromRequest(requestId, accountId)
      → MiscellaneousRequestContextVariablesService.setFromRequest(request)
      → FeatureFlagContextService.setFromRequest(request)
```

---

## 3. Logging

**Package:** `io.atlassian.micros.proactiveai.logging`
**Files:** 6 | **LoC:** 568

### 3.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `LaasLogger.kt` | ~30 | Class | Main logger — wraps SLF4J, provides UGC-safe logging |
| `LaasLoggerFactory.kt` | ~10 | Object | Factory: `getLogger(Class)` → `LaasLogger` |
| `InterceptedLogger.kt` | ~300 | Class | SLF4J Logger wrapper with interception hooks |
| `LoggerExtensions.kt` | ~80 | Extensions | `debugWithContext`, `infoWithContext`, `warnWithContext`, `errorWithContext` |
| `WithUGCLogger.kt` | ~30 | Class | Logger that emits UGC content (when gate enabled) |
| `NoopLogger.kt` | ~30 | Class | Silent logger (when UGC gate disabled) |

### 3.2 Structured Logging Extensions

All extension functions add a `ctx.` prefix to keys and use `StructuredArguments.entries()` for Logstash-compatible structured logging:

```kotlin
fun Logger.infoWithContext(message: String, ctx: Map<String, Any?>, exception: Throwable?)
fun Logger.warnWithContext(message: String, ctx: Map<String, Any?>, exception: Throwable?)
fun Logger.errorWithContext(message: String, ctx: Map<String, Any?>, exception: Throwable?)
fun Logger.debugWithContext(message: String, ctx: Map<String, Any?>, exception: Throwable?)
```

### 3.3 UGC-Safe Logging Pattern

`LaasLogger.withUGC(featureService)` checks the `ENABLE_UGC_LOGGING` permanent feature gate:
- **Gate ON** → returns `WithUGCLogger` (logs normally)
- **Gate OFF** → returns `NoopLogger` (silently drops)

This ensures User-Generated Content is never logged in production unless explicitly enabled via feature flag.

### 3.4 InterceptedLogger

A full SLF4J `Logger` implementation that wraps every logging method with an interceptor lambda. The `LaasLogger` extends this with a pass-through interceptor (`{ log -> log() }`), making it a transparent wrapper that can be extended for custom behavior.

---

## 4. Interceptors

**Package:** `io.atlassian.micros.proactiveai.interceptor`
**Files:** 5 | **LoC:** 295

### 4.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `CommonContextSetter.kt` | ~15 | Interface | Contract for request context setup |
| `internal/CommonContextSetterImpl.kt` | ~80 | `@Service` | Sets logging ctx, misc vars, feature flag ctx from request |
| `RequestContextInterceptor.kt` | ~60 | `@Component` | `HandlerInterceptor` — calls initter + context setter |
| `UserContextInterceptor.kt` | ~80 | `@Component` | Extracts `UserContext` from SLAuth headers |
| `LoggingContextClearingFilter.kt` | ~60 | `@Component` | Servlet filter that clears MDC after request |

### 4.2 Request Processing Chain

```
Request → LoggingContextClearingFilter (outermost, clears MDC in finally)
  → RequestContextInterceptor.preHandle()
    → setupRequestScopedValues()
    → CommonContextSetterImpl.setContext()
  → UserContextInterceptor.preHandle()
    → Extracts User from UserContext headers
  → Controller method execution
  → RequestContextInterceptor.afterCompletion()
```

---

## 5. Context Models

**Package:** `io.atlassian.micros.proactiveai.context`
**Files:** 9 | **LoC:** 381

### 5.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `Product.kt` | ~90 | Enum | 7 Atlassian products with IDs and legacy mappings |
| `Experience.kt` | ~100 | Enums | HelpSeekerExperience, UseCase, Branding, Experience |
| `Types.kt` | ~20 | Typealiases | CloudId, OrgId, TenantId, AccountId, ActivationId |
| `TenantContext.kt` | ~30 | Interface | Tenant identity (cloudId, orgId, product, experience) |
| `TenantContextModels.kt` | ~40 | Data classes | `PlatformTenantContextImpl` implementation |
| `PlatformTenantContext.kt` | ~30 | Interface | Extended tenant context with sharding |
| `CloudIdContext.kt` | ~15 | Interface | Cloud ID accessor |
| `OrgIdContext.kt` | ~15 | Interface | Org ID accessor |
| `AIGatewayContext.kt` | ~40 | Data class | Context for AI Gateway calls |

### 5.2 Product Enum (7 values)

| Value | ID | Description |
|-------|----|-------------|
| `JIRA_PLATFORM` | `jira` | Jira family (shared experiences) |
| `JIRA_SOFTWARE` | `jira-software` | Jira Software |
| `JIRA_SERVICE_MANAGEMENT` | `jsm` | JSM (legacy: `jira-servicedesk`, `jira-service-management`) |
| `JIRA_WORK_MANAGEMENT` | `jira-core` | JWM (legacy: `jira-work-management`) |
| `JIRA_PRODUCT_DISCOVERY` | `jpd` | JPD (legacy: `jira-product-discovery`) |
| `CONFLUENCE` | `confluence` | Confluence |
| `BITBUCKET` | `bitbucket` | Bitbucket |

Helper: `ALL_JIRA_PRODUCTS` set for Jira-family checks.

### 5.3 Experience & Branding Enums

- **UseCase:** `ROVO_BUTTON("rovo-button")`, `ROVO_INSIGHTS("rovo-insights")`
- **Branding:** `ROVO`, `ATLASSIAN_INTELLIGENCE`
- **HelpSeekerExperience:** `HELPSEEKER_EXPERIENCE`, `NON_HELPSEEKER_EXPERIENCE`

### 5.4 Type Aliases

```kotlin
typealias CloudId = String
typealias OrgId = String
typealias TenantId = String
typealias AccountId = String
typealias ActivationId = String
```

---

## 6. Metrics

**Package:** `io.atlassian.micros.proactiveai.service.metric`
**Files:** 5 | **LoC:** 1,243 (largest package)

### 6.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `MetricKey.kt` | ~60 | Enums | `MetricKey` (7 values), `MetricKeyLike` interface, `HistogramMetric`, `HistogramBucket`, `ResultMetricBase` |
| `CoreMetricsService.kt` | ~130 | Interface | Low-level metrics: count, gauge, summarize, histogram (14 method signatures) |
| `MetricsService.kt` | ~100 | Interface | High-level: time, countResult, timeAndCountResult (10+ methods) |
| `internal/CoreMetricsServiceImpl.kt` | ~250 | `@Service` | Micrometer-backed implementation |
| `internal/MetricsServiceImpl.kt` | ~700 | `@Service` | Delegates to CoreMetricsService, adds timing/result-counting |

### 6.2 Two-Layer Abstraction

```
Feature Code → MetricsService (high-level: time, countResult, timeAndCountResult)
                  → CoreMetricsService (low-level: count, gauge, summarize, histogram)
                      → Micrometer MeterRegistry (actual metric emission)
```

### 6.3 MetricKey Enum (7 values)

| Key | Metric Name | Purpose |
|-----|-------------|---------|
| `PROACTIVE_TEST_COUNT` | `test.count` | Test counter |
| `PROACTIVE_TEST_LATENCY` | `test.latency` | Test latency |
| `TENANT_CONTEXT_BUILD_SUCCESS` | `tenant.context.build.success` | Tenant context build success |
| `TENANT_CONTEXT_BUILD_ERROR` | `tenant.context.build.error` | Tenant context build failure |
| `STREAMHUB_EVENT_PROCESSED` | `streamhub.event.processed` | StreamHub event processed |
| `STREAMHUB_EVENT_UNSUPPORTED` | `streamhub.event.unsupported` | Unsupported event type |
| `STREAMHUB_EVENT_ERROR` | `streamhub.event.error` | StreamHub event processing error |

All metrics are prefixed with `proactive-ai.` by `MetricsServiceImpl.METRIC_PREFIX`.

### 6.4 CoreMetricsService Interface (14 methods)

| Method | Signature | Description |
|--------|-----------|-------------|
| `count(metricKey)` | `count(MetricKeyLike)` | Increment by 1 |
| `count(metricKey, amount: Int)` | — | Increment by int |
| `count(metricKey, amount: Double)` | — | Increment by double |
| `count(metricKey, tags: List)` | — | Count with tag list |
| `countWithoutLogging(metricKey, tags)` | — | Count without log emission |
| `count(metricKey, tag: Pair)` | — | Count with single tag |
| `count(metricKey, vararg tags)` | — | Count with vararg tags |
| `count(metricKey, amount, vararg tags)` | — | Count amount with tags |
| `count(metricKey, amount, tags: Iterable)` | — | Count with iterable tags |
| `count(success, failure, ...)` | `count(successKey, failureKey, tags, includeResultTag, resultTransformer, exceptionCountsAsFailure, function)` | Success/failure counter with result tag |
| `summarize(metricKey, size, tags)` | — | Distribution summary |
| `histogram(metricKey, tags, function)` | — | Histogram with function timing |
| `gauge(metricKey, amount)` | — | Set gauge value |
| `gauge(metricKey, amount, tags)` | — | Gauge with tags |

### 6.5 MetricsService Interface (additional methods)

| Method | Description |
|--------|-------------|
| `time(metricKey, tags, function)` | Time a function, record duration |
| `timeFunction(metricBase, tags, function)` | Time with ResultMetricBase (adds `.latency` suffix) |
| `countResult(metricBase, tags, ...)` | Count success (`.success`) or failure (`.error`) |
| `timeAndCountResult(metricBase, tags, ...)` | Combined timing + result counting |
| `countWithErrors(metricKey, tags, ...)` | Count with error tracking |

### 6.6 Metric Suffixes (MetricsServiceImpl)

| Constant | Value | Usage |
|----------|-------|-------|
| `METRIC_PREFIX` | `proactive-ai.` | Prepended to all metric names |
| `SUFFIX_LATENCY` | `.latency` | Appended for timing metrics |
| `SUFFIX_SUCCESS` | `.success` | Appended for success counters |
| `SUFFIX_ERROR` | `.error` | Appended for error counters |
| `SUCCESS_TAG` | `success=true` | Tag for successful operations |
| `FAILURE_TAG` | `success=false` | Tag for failed operations |

---

## 7. Feature Gates

**Package:** `io.atlassian.micros.proactiveai.featuregate`
**Files:** 8 | **LoC:** 754

### 7.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `FeatureGate.kt` | ~12 | Interface | `statsigKey: String` property |
| `AiFeatureGates.kt` | ~10 | Enum | 2 AI-specific gates |
| `PermanentFeatureGates.kt` | ~8 | Enum | 1 permanent gate |
| `FeatureFlagContextService.kt` | ~35 | Interface+Enum | Context management, `FeatureFlagContextContextType` |
| `FeatureFlagEvaluationTracker.kt` | ~120 | Component | Tracks flag evaluations per request |
| `FeatureService.kt` | ~100 | Interface | 9 methods for gate checking |
| `internal/FeatureFlagContextServiceImpl.kt` | ~170 | `@Service` | Builds `FeatureGateUser` from tenant/request context |
| `internal/FeatureServiceImpl.kt` | ~300 | `@Service` | Statsig-backed implementation with evaluation recording |

### 7.2 FeatureGate Interface

```kotlin
interface FeatureGate {
    val statsigKey: String
}
```

Implemented by two enums:

**AiFeatureGates** (2 values):
| Gate | Statsig Key | Purpose |
|------|-------------|---------|
| `TEST_GATE` | `aix_proactive_test_gate` | Test gate for validation |
| `FEATURE_FLAG_EVALUATION_LOGGING_ENABLED` | `aix_feature_flag_evaluation_logging_enabled` | Controls evaluation tracking |

**PermanentFeatureGates** (1 value):
| Gate | Statsig Key | Purpose |
|------|-------------|---------|
| `ENABLE_UGC_LOGGING` | `proactive_ai_enable_ugc_logging` | Controls UGC content logging |

### 7.3 FeatureService Interface (9 methods)

| Method | Description |
|--------|-------------|
| `checkGate(featureGate, defaultValue)` | Full-context gate check (requires tenant) |
| `checkHelloOnlyGate(featureGate, defaultValue)` | Gate check restricted to Hello tenant |
| `checkGateWithLimitedContext(featureGate, defaultValue)` | Gate check without tenant (no % rollout) |
| `getExperiment(featureGate)` | Get experiment config with exposure logging |
| `getDynamicConfigWithoutExperimentExposureLogging(featureGate)` | Get config without exposure logging |
| `getStringConfigValue(featureGate, defaultValue)` | Extract string from dynamic config |
| `getStringConfigValueWithoutExposureLogging(featureGate, defaultValue)` | String config without exposure |
| `getIntConfigValue(featureGate, defaultValue)` | Extract int from dynamic config |
| `checkGateForTenantContext(featureGate, tenantId, organisationId, defaultValue)` | Gate check with explicit tenant |

### 7.4 FeatureFlagContextContextType Enum

| Value | Description |
|-------|-------------|
| `FULL` | Full context including tenant ID (for % rollout, dogfood targeting) |
| `LIMITED_CONTEXT` | Limited context — tenant may not be initialized yet |

### 7.5 FeatureFlagEvaluationTracker

Tracks all feature flag evaluations during a request for downstream analytics:

- **`FeatureFlagEvaluation`** — Sealed class with two subtypes:
  - `GateCheck(flagName, result: Boolean)` — Boolean gate evaluation
  - `Experiment(flagName, result: Map<String, Any>)` — Experiment config evaluation
- **`FeatureFlagEvaluationTrackerData`** — Request-scoped value holding a thread-safe `MutableList<FeatureFlagEvaluation>` and a `loggingEnabled` cache flag
- Logging is itself gated by `FEATURE_FLAG_EVALUATION_LOGGING_ENABLED` — lazy-evaluated and cached per request

### 7.6 FeatureServiceImpl — Evaluation Recording

After each gate check or experiment fetch, `FeatureServiceImpl` calls `recordGateCheck()` or `recordExperiment()` which:
1. Checks if logging is enabled (lazy, cached per request)
2. If enabled, records the evaluation via `FeatureFlagEvaluationTracker`
3. Failures in recording are caught and logged as warnings (never fail the gate check)

---

## 8. Async Task Framework

**Package:** `io.atlassian.micros.proactiveai.task`
**Files:** 11 | **LoC:** 649

### 8.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `AsyncTask.kt` | ~25 | Interface | Jackson-polymorphic task envelope |
| `AsyncTaskHandler.kt` | ~55 | Interface | Handler contract: `handle`, `onSuccess`, `onFailure` |
| `AsyncTaskDispatcher.kt` | ~80 | `@Component` | Routes tasks to handlers via type registry |
| `AsyncTaskExecutionContext.kt` | ~15 | Data class | tenantId + User + requestId |
| `AsyncTaskQueueRegistry.kt` | ~20 | `@Component` | Maps task types to queue names |
| `AsyncTaskService.kt` | ~15 | Interface | `submit(task)` — enqueue for async processing |
| `internal/AsyncTaskServiceImpl.kt` | ~100 | `@Service` | Serializes task+context to SQS |
| `internal/AsyncTaskMessage.kt` | ~15 | Data class | Wire format: context + task |
| `internal/AsyncTaskMessageAttributes.kt` | ~15 | Object | SQS message attribute constants |
| `internal/AsyncTaskExecutionContextWire.kt` | ~30 | Data class | Serializable context (tenantId, accountId, requestId, userContextJwt) |
| `internal/VisibilityExtendingSQSQueueConsumer.kt` | ~100 | Abstract class | SQS consumer with visibility heartbeat |

### 8.2 Task Lifecycle

```
Producer (HTTP handler)                          Consumer (LongRun worker)
┌──────────────────────┐                        ┌──────────────────────────────┐
│ AsyncTaskService     │   SQS Queue            │ VisibilityExtendingSQS-      │
│   .submit(task)      │──────────────────────→ │   QueueConsumer              │
│                      │  AsyncTaskMessage       │     ↓                        │
│ Serializes:          │  (JSON)                 │ Deserialize AsyncTaskMessage │
│ - ExecutionContext   │                        │     ↓                        │
│   (tenant, user,     │                        │ AsyncTaskDispatcher          │
│    requestId)        │                        │   .dispatch(context, task)   │
│ - AsyncTask          │                        │     ↓                        │
│   (@type polymorphic)│                        │ AsyncTaskHandler<T>          │
└──────────────────────┘                        │   .handle(context, task)     │
                                                │   .onSuccess() or .onFailure │
                                                └──────────────────────────────┘
```

### 8.3 AsyncTaskDispatcher — Registry Pattern

At startup, Spring autowires all `AsyncTaskHandler<*>` beans into a list. The dispatcher builds a `Map<Class<out AsyncTask>, AsyncTaskHandler<*>>` keyed by each handler's `type` property. On dispatch:
1. Looks up handler by `task.javaClass`
2. If not found → `IllegalStateException` → SQS NACK → eventual DLQ
3. Calls `handler.handle(context, task)`
4. On success → `handler.onSuccess()`
5. On failure → logs error, calls `handler.onFailure()` (swallows hook errors), rethrows original

### 8.4 VisibilityExtendingSQSQueueConsumer — Heartbeat Mechanism

Prevents SQS message redelivery during long-running LLM tasks:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DURATION` | **30 seconds** | Visibility timeout set on each heartbeat |
| `PERIOD` | **25 seconds** | Interval between heartbeats |
| `BUFFER` | **5 seconds** | `PERIOD = DURATION - BUFFER` safety margin |

**How it works:**
1. `acceptMessage()` is called when SQS delivers a message
2. A `ScheduledFuture` is created via `taskScheduler.scheduleAtFixedRate(PERIOD)` that calls `changeMessageVisibility(DURATION)` on each tick
3. While the handler runs, visibility is continuously refreshed every 25s
4. When handler completes (success or failure), heartbeat is cancelled in `finally`
5. If JVM crashes, last visibility extension expires in ≤30s, message becomes visible for retry

### 8.5 AsyncTaskMessage (Wire Format)

```kotlin
data class AsyncTaskMessage(
    val executionContext: AsyncTaskExecutionContextWire,  // tenantId, accountId, requestId, userContextJwt
    val task: AsyncTask,                                   // @type polymorphic Jackson
)
```

The `AsyncTaskExecutionContextWire` carries the user's JWT so the consumer can reconstruct a `User` object on the worker node.

### 8.6 AsyncTaskHandler Interface

```kotlin
interface AsyncTaskHandler<T : AsyncTask> {
    val type: Class<T>           // Concrete AsyncTask subtype
    val queueName: String        // SQS queue name
    suspend fun handle(ctx: AsyncTaskExecutionContext, task: T)
    suspend fun onSuccess(ctx: AsyncTaskExecutionContext, task: T) {}
    suspend fun onFailure(ctx: AsyncTaskExecutionContext, task: T, error: Throwable) {}
}
```

Implementations should be **idempotent** — SQS may redeliver until `MaxReceiveCount`.

---

## 9. SQS Infrastructure

**Package:** `io.atlassian.micros.proactiveai.sqs`
**Files:** 8 | **LoC:** 370

### 9.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `QueueNames.kt` | ~20 | Constants | `ANALYTICS_EVENTS_QUEUE`, `ROVO_INSIGHTS_GENERATION_QUEUE` |
| `EventAVIs.kt` | ~12 | Object | `ANALYTICS_ENRICHED_UI_CREATED` AVI constant |
| `StreamHubEvent.kt` | ~40 | Data class | Generic StreamHub event model (type, payload, timestamps) |
| `AnalyticsEventsMessageQueueConsumer.kt` | ~40 | Interface | Consumer contract for analytics events |
| `AnalyticsEventsSqsQueueConsumer.kt` | ~60 | `@Component` | SQS consumer on SHWorkers group, processes StreamHub events |
| `AnalyticsEnrichedEventHandler.kt` | ~50 | `@Component` | Handles `analytics-enriched:created:ui` events |
| `MessageQueueConsumerMiddleware.kt` | ~80 | `@Component` | Middleware: request context init, logging context, metrics |
| `SqsEventConsumerConfig.kt` | ~70 | `@Configuration` | `prefetch=0` config, `NopDuplicateHandler` |

### 9.2 Queue Names

| Constant | Value | Worker Group | Purpose |
|----------|-------|--------------|---------|
| `ANALYTICS_EVENTS_QUEUE` | `analytics_events` | SHWorkers | StreamHub analytics event processing |
| `ROVO_INSIGHTS_GENERATION_QUEUE` | `rovo_insights_generation_queue` | LongRun | Async Rovo Insights generation |

### 9.3 SQS Prefetch Configuration

`SqsEventConsumerConfig` sets `prefetch=0` to prevent the documented anti-pattern where a slow listener holds a prefetched message while fast listeners sit idle. This is critical for LLM-handler workloads with high latency variance (5–60s).

### 9.4 MessageQueueConsumerMiddleware

Wraps every SQS message processing with:
1. Request context initialization (`RequestScopedValuesInitter.initRequestScopedValuesAndRun`)
2. Logging context setup (`LoggingContext.addStreamHubEventInfo`)
3. Metrics emission (processed/unsupported/error counters)

---

## 10. Configuration

**Package:** `io.atlassian.micros.proactiveai.config`
**Files:** 6 | **LoC:** 208

### 10.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `MicrosEnvironmentConfig.kt` | ~25 | `@Configuration` | Bean for `MicrosEnvironmentType` from `micros.environment.type` |
| `MicrosEnvironmentType.kt` | ~30 | Enum | `LOCAL`, `STAGING`, `PROD` with helpers |
| `MvcSecurityConfig.kt` | ~15 | `@Configuration` | Anonymous paths: `/healthcheck`, `/deepcheck` |
| `OnLongRunWorkerNodeOrLocalCondition.kt` | ~20 | Condition | Matches `MICROS_GROUP=LongRun` OR `local` profile |
| `OnSHWorkerNodeOrLocalCondition.kt` | ~20 | Condition | Matches `MICROS_GROUP=SHWorkers` OR `local` profile |
| `WebMvcConfiguration.kt` | ~100 | `@Configuration` | Registers interceptors, enables scheduling |

### 10.2 MicrosEnvironmentType Enum

| Value | `isNonProduction()` | `isProduction()` |
|-------|--------------------|--------------------|
| `LOCAL` | `true` | `false` |
| `STAGING` | `true` | `false` |
| `PROD` | `false` | `true` |

### 10.3 Worker Node Conditions

Used with `@Conditional` to restrict bean creation to specific worker groups:

- **`OnLongRunWorkerNodeOrLocalCondition`**: Checks `MICROS_GROUP=LongRun` env var OR `local` profile
- **`OnSHWorkerNodeOrLocalCondition`**: Checks `MICROS_GROUP=SHWorkers` env var OR `local` profile

Both conditions allow local development to run all beans regardless of worker group.

---

## 11. HTTP Clients

**Package:** `io.atlassian.micros.proactiveai.client`
**Files:** 7 | **LoC:** 399

### 11.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `Audiences.kt` | ~8 | Object | Service audience constants for ASAP auth |
| `HttpClientCommons.kt` | ~20 | Object | Common HTTP header constants |
| `identity/IdGatekeeperClient.kt` | ~10 | Interface | Sync permission checking (deprecated) |
| `identity/AsyncIdGatekeeperClient.kt` | ~30 | Interface | Async permission checking with ARM filters |
| `identity/IdGatekeeperModels.kt` | ~80 | Data classes | `PermissionRequest`, `PermissionResult`, `PermissionsCheckPayload` |
| `identity/internal/IdGatekeeperClientImpl.kt` | ~100 | `@Service` | Sync implementation via RestTemplate |
| `identity/internal/AsyncIdGatekeeperClientImpl.kt` | ~150 | `@Service` | Async implementation via coroutines |

### 11.2 Audience Constants

| Constant | Value | Target Service |
|----------|-------|----------------|
| `AI_GATEWAY` | `ai-gateway` | AI Gateway |
| `CONVO_AI` | `convo-ai` | Conversational AI |
| `INTEGRATIONS_SERVICE` | `integrations-service` | Integration Service |
| `IDENTITY_PLATFORM` | `identity-platform` | Identity Platform |

### 11.3 IdGatekeeper Client

Checks RBAC permissions via the Identity Gatekeeper service:

- **`checkPermission(request)`** — Single permission check
- **`checkPermissionBulk(requests)`** — Batch permission check
- **`PrincipalFilter`** enum: `USER("arm:cloud:identity::user/.+")`, `GROUP("arm:cloud:identity::group/.+")`
- **Key permission:** `GENERATIVE_AI_RBAC_PERMISSION = "read:features:ai"`

---

## 12. Utilities

**Package:** `io.atlassian.micros.proactiveai.utility`
**Files:** 8 | **LoC:** 557

### 12.1 File Inventory

| File | LoC | Type | Description |
|------|-----|------|-------------|
| `tenant/TcsService.kt` | ~50 | `@Service` | Tenant Context Service client (stub) |
| `threading/ThreadConfig.kt` | ~50 | `@Configuration` | Coroutine dispatcher configuration |
| `threading/InstrumentedDispatcher.kt` | ~80 | Class | Metered coroutine dispatcher |
| `threading/CoroutineMonitor.kt` | ~60 | `@Component` | Monitors coroutine pool health via gauges |
| `threading/RequestAttributesCoroutineContext.kt` | ~40 | Class | Propagates request attributes into coroutines |
| `threading/RequestAttributesForAsyncProcessing.kt` | ~100 | Class | Thread-local request attribute store for async contexts |
| `user/User.kt` | ~50 | Interface | User model: accountId, orgId, userContext, extraContext |
| `user/internal/UserImpl.kt` | ~50 | Class | User implementation wrapping `UserContext` |

### 12.2 User Interface

```kotlin
interface User {
    fun getUserContextHeaderValue(): UserContextHeaderValue  // Signed JWT
    fun getAccountId(): AccountId
    fun getUserOrgId(): OrgId?
    fun getExtraContext(): ExtraContext
}
```

**ExtraContext** carries: `ForwardedForHeaderValue`, `GeoLocation(countryName)`, `ForwardedHostHeaderValue`, `isIpAllowListExempted`.

### 12.3 Coroutine Infrastructure

- **`InstrumentedDispatcher`** — Wraps a `CoroutineDispatcher` with Micrometer metrics (active/queued task gauges)
- **`CoroutineMonitor`** — Scheduled component that emits coroutine pool health metrics
- **`RequestAttributesCoroutineContext`** — `CoroutineContext.Element` that copies `RequestAttributes` from the launching thread into the coroutine
- **`RequestAttributesForAsyncProcessing`** — Simple `RequestAttributes` implementation backed by a `ConcurrentHashMap` for use outside the servlet request lifecycle

---

## 13. Exception Handling

**Package:** `io.atlassian.micros.proactiveai.exception`
**Files:** 1 | **LoC:** 116

### 13.1 RestClientException Hierarchy

```
RestClientException (abstract)
├── BadRequestException (400)
├── UnauthorizedException (401)
├── ForbiddenException (403)
├── NotFoundException (404)
├── ConflictException (409)
├── InternalServerException (500)
└── ServiceUnavailableException (503)
```

Each exception carries: `httpStatus: HttpStatus`, `message: String`, `cause: Throwable?`.

Factory method: `RestClientException.fromStatusCode(statusCode, message, cause)` maps HTTP status codes to the appropriate exception subclass.

---

## 14. Design Patterns Summary

| Pattern | Where Used | Description |
|---------|-----------|-------------|
| **Interface + Internal Impl** | All major services | Public interface in package root, `@Service` impl in `internal/` subpackage |
| **Request-Scoped Value Store** | `requestcontext/` | Thread-safe, request-lifecycle-bound value storage |
| **Owner-Initter** | `requestcontext/` | Owners define scoped values; initter initializes them at request start |
| **Undo Handle** | `SetContextUndo` | Context changes return a revert function |
| **Registry/Dispatcher** | `task/AsyncTaskDispatcher` | Autowired handlers mapped by type for runtime dispatch |
| **Visibility Heartbeat** | `task/VisibilityExtendingSQSQueueConsumer` | Periodic SQS visibility extension for long tasks |
| **Two-Layer Metrics** | `service/metric/` | CoreMetricsService (primitives) → MetricsService (composed operations) |
| **UGC-Safe Logging** | `logging/` | Feature-gated logger swap (WithUGC vs Noop) |
| **Structured Logging** | `logging/LoggerExtensions` | `ctx.`-prefixed structured arguments via Logstash |
| **Worker Node Conditions** | `config/` | `@Conditional` beans for worker group isolation |
| **Interceptor Chain** | `interceptor/` | Spring HandlerInterceptor for request context setup |
| **Jackson Polymorphism** | `task/AsyncTask`, `featuregate/FeatureFlagEvaluation` | `@JsonTypeInfo` for type-safe SQS serialization |

---

*This document was generated on 2026-05-07 by reading all 88 source files across 12 platform packages. For the most current state, refer to the actual source code.*
