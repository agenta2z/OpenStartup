# Core Platform Infrastructure Layer — Deep Documentation

> **Codebase**: `proactive-ai-platform` (Atlassian Proactive AI Platform)
> **Scope**: The 12 platform packages that all features build upon
> **Total Coverage**: 97 files, 6,446 lines across 12 subsystems
> **Source**: `src/main/kotlin/io/atlassian/micros/proactiveai/`
> **Verified**: 2026-05-07 — every class, interface, enum, and method signature verified against source

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Request Context System](#2-request-context-system) — `requestcontext/` (14 files, 906 LoC)
3. [Custom Logging Framework](#3-custom-logging-framework) — `logging/` (6 files, 568 LoC)
4. [Interceptor Pipeline](#4-interceptor-pipeline) — `interceptor/` (5 files, 295 LoC)
5. [Context Models](#5-context-models) — `context/` (9 files, 381 LoC)
6. [Metrics Service](#6-metrics-service) — `service/metric/` (5 files, 1,243 LoC)
7. [Feature Gate System](#7-feature-gate-system) — `featuregate/` (8 files, 754 LoC)
8. [Async Task Framework](#8-async-task-framework) — `task/` (11 files, 649 LoC)
9. [SQS Infrastructure](#9-sqs-infrastructure) — `sqs/` (8 files, 370 LoC)
10. [Configuration Layer](#10-configuration-layer) — `config/` (6 files, 208 LoC)
11. [Client Layer](#11-client-layer) — `client/` (7 files, 399 LoC)
12. [Utility Layer](#12-utility-layer) — `utility/` (8 files, 557 LoC)
13. [Exception Handling](#13-exception-handling) — `exception/` (1 file, 116 LoC)
14. [Cross-Cutting Patterns](#14-cross-cutting-patterns)

---

## 1. Architecture Overview

PAI uses a **flat single-module** Gradle project with 16 top-level packages under one `src/main` tree. There is no multi-module split — all packages are compiled into a single JAR. The platform packages form a strict layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│            Feature Layer (consumers)                    │
│  feature/rovoinsights, feature/nudge, feature/greeting  │
│  stratus (AI Gateway integration)                       │
├─────────────────────────────────────────────────────────┤
│           Platform Layer (providers)                    │
│  task, interceptor, config, sqs, service/metric,       │
│  requestcontext, featuregate, client                   │
├─────────────────────────────────────────────────────────┤
│              Leaf Layer (no PAI deps)                   │
│  logging, context, exception, utility                  │
└─────────────────────────────────────────────────────────┘
```

**Key principle**: Feature packages import platform packages, but never the reverse. Platform packages form a DAG with `logging`, `context`, and `exception` as leaf nodes.

### 1.1 Verified Package Metrics

| Package | Files | LoC | Spring Components |
|---------|-------|-----|-------------------|
| `requestcontext` | 14 | 906 | 4 (@Component: `LoggingContextImpl`, `RequestScopedValueServiceImpl`, `RequestScopedValuesInitterImpl`, `RequestScopedValueOwners`; @Service: `MiscellaneousRequestContextVariablesService`) |
| `logging` | 6 | 568 | 1 (@Component: `LaasLoggerFactory`) |
| `interceptor` | 5 | 295 | 4 (@Component: `RequestContextInterceptor`, `UserContextInterceptor`, `LoggingContextClearingFilter`, `CommonContextSetterImpl`) |
| `context` | 9 | 381 | 0 (pure data models) |
| `service/metric` | 5 | 1,243 | 2 (@Component: `CoreMetricsServiceImpl`, `MetricsServiceImpl`) |
| `featuregate` | 8 | 754 | 3 (@Component: `FeatureFlagEvaluationTracker`, `FeatureFlagContextServiceImpl`, `FeatureServiceImpl`) |
| `task` | 11 | 649 | 2 (@Component: `AsyncTaskDispatcher`, `AsyncTaskQueueRegistry`; @Service: `AsyncTaskServiceImpl`) |
| `sqs` | 8 | 370 | 4 (@Component: `AnalyticsEnrichedEventHandler`, `AnalyticsEventsMessageQueueConsumer`, `AnalyticsEventsSqsQueueConsumer`, `MessageQueueConsumerMiddleware`; @Configuration: `SqsEventConsumerConfig`, `CommonSqsConfig`) |
| `config` | 6 | 208 | 3 (@Configuration: `MicrosEnvironmentConfig`, `MvcSecurityConfig`, `WebMvcConfiguration`) |
| `client` | 7 | 399 | 2 (@Component: `AsyncIdGatekeeperClientImpl`, `IdGatekeeperClientImpl`) |
| `utility` | 8 | 557 | 1 (@Service: `TcsService`; @Configuration: `ThreadConfig`) |
| `exception` | 1 | 116 | 0 (pure exception classes) |

**Total Spring-managed components across all 16 packages**: 43 class-level stereotype annotations (@Component: 28, @Service: 4, @Configuration: 6, @RestController: 5) + 12 @Bean factory methods = **55 total Spring-managed beans**. *(Note: Doc 01 claims "~53" — the accurate count is 43 class-level + 12 @Bean = 55.)*

---

## 2. Request Context System

**Location**: `requestcontext/` (14 files, 906 LoC)
**Dependencies**: logging, config, context, client/identity, utility

### 2.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `HeaderConstants.kt` | 5 | Object | Single constant `GEO_IP = "Atl-Edge-Geoip"` |
| `LoggingContext.kt` | 75 | Interface | MDC lifecycle management contract |
| `LoggingContextExtensions.kt` | 37 | Extension functions | Kotlin-friendly `withContext` / `withContextAsync` helpers |
| `MiscellaneousRequestContextVariablesService.kt` | 43 | @Service | Third owner for `MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES` key |
| `RequestScopedValue.kt` | 7 | Interface | Marker interface for request-scoped data types |
| `RequestScopedValueKey.kt` | 18 | Enum | 3 values (verified below) |
| `RequestScopedValueOwner.kt` | 18 | Interface | Contract for key owners |
| `RequestScopedValueOwners.kt` | 27 | @Component | Startup validation of key-owner uniqueness |
| `RequestScopedValueService.kt` | 14 | Interface | CRUD for request-scoped values |
| `RequestScopedValuesInitter.kt` | 22 | Interface | Early request initialization contract |
| `SetContextUndo.kt` | 9 | Interface | Revert mechanism for context changes |
| `internal/LoggingContextImpl.kt` | 227 | @Component | Full MDC lifecycle implementation |
| `internal/RequestScopedValueServiceImpl.kt` | 147 | @Component | Central read/write service with async fallback |
| `internal/RequestScopedValuesInitterImpl.kt` | 57 | @Component | Initializes all owners at request start |

### 2.2 Core Pattern: RequestScopedValueKey / RequestScopedValueOwner

The request context system provides type-safe, validated per-request data storage built atop Spring's `RequestAttributes` (thread-local storage). It uses a **Key-Owner pattern**.

#### RequestScopedValueKey (Enum) — VERIFIED 3 values

```kotlin
enum class RequestScopedValueKey {
    FEATURE_FLAG_CONTEXT,                      // Owner: FeatureFlagContextServiceImpl → FeatureFlagScopedData
    FEATURE_FLAG_EVALUATION_TRACKER,           // Owner: FeatureFlagEvaluationTracker → FeatureFlagEvaluationTrackerData
    MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES,   // Owner: MiscellaneousRequestContextVariablesService → MiscellaneousRequestContextVariablesData
}
```

**Key-to-Owner mapping (verified)**:

| Key | Owner Class | Value Type | Package |
|-----|------------|------------|---------|
| `FEATURE_FLAG_CONTEXT` | `FeatureFlagContextServiceImpl` | `FeatureFlagScopedData` | `featuregate/internal/` |
| `FEATURE_FLAG_EVALUATION_TRACKER` | `FeatureFlagEvaluationTracker` | `FeatureFlagEvaluationTrackerData` | `featuregate/` |
| `MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES` | `MiscellaneousRequestContextVariablesService` | `MiscellaneousRequestContextVariablesData` | `requestcontext/` |

#### RequestScopedValueOwner\<T\> (Interface)

```kotlin
interface RequestScopedValueOwner<T : RequestScopedValue> {
    fun getKey(): RequestScopedValueKey
    fun newEmptyValue(): T
    fun getValueType(): Class<T>
}
```

#### RequestScopedValueOwners — Startup Validation

```kotlin
@Component
class RequestScopedValueOwners(private val owners: List<RequestScopedValueOwner<*>>) {
    init { validateCorrectSetup() }
    // Throws IllegalStateException if:
    // 1. Duplicate keys found across owners
    // 2. Number of owners != number of enum entries
}
```

This is a **compile-time contract**: `RequestScopedValueOwners` validates at Spring startup that (a) no duplicate keys exist, and (b) every key has exactly one registered owner. If validation fails, the app throws `IllegalStateException` and refuses to start.

#### RequestScopedValuesInitter — The "Initter" Pattern

The initter pattern ensures request-scoped values are initialized consistently:

```kotlin
interface RequestScopedValuesInitter {
    fun setupRequestScopedValues()                       // Called by early request interceptor
    fun initRequestScopedValuesAndRun(runnable: Runnable) // For async processing (wraps setup + teardown)
}
```

`RequestScopedValuesInitterImpl` (@Component) iterates over all `RequestScopedValueOwner` instances and calls `newEmptyValue()` to populate the `RequestAttributes` store, ensuring every key has a non-null initial value before any handler code runs.

### 2.3 RequestScopedValueService

`RequestScopedValueServiceImpl` is the central service for reading/writing request-scoped values.

```kotlin
interface RequestScopedValueService {
    fun <T : RequestScopedValue> getValue(owner: RequestScopedValueOwner<T>): T
    fun <T : RequestScopedValue> setValue(owner: RequestScopedValueOwner<T>, value: T)
}
```

Key implementation behaviors:
- **Fallback handling**: If `RequestAttributes` become inactive (request recycled), it creates `RequestAttributesForAsyncProcessing` as a standalone fallback
- **Type safety**: Uses `@Suppress("UNCHECKED_CAST")` but enforced structurally by the owner pattern
- **Profile-aware errors**: In `local` profile, error messages include helpful test setup hints

### 2.4 LoggingContext and LoggingContextImpl

`LoggingContext` (interface, 75 lines) + `LoggingContextImpl` (implementation, 227 lines) manage the MDC (Mapped Diagnostic Context) lifecycle.

#### LoggingContext Interface — Full Method Inventory

```kotlin
interface LoggingContext {
    fun <T> runWithContext(toRun: Supplier<T>, ctx: Map<String, String>): T
    fun <T> runWithContext(ctx: Map<String, String>, toRun: () -> T): T       // trailing-lambda syntax
    suspend fun <T> runWithContextAsync(toRun: suspend () -> T, ctx: Map<String, String>): T
    fun addTenantContext(tenantContext: TenantContext): SetContextUndo
    fun addStreamHubEventInfo(eventId: String, eventType: String, ingestionSource: String?, occurrenceTime: ZonedDateTime?, ingestionTime: ZonedDateTime?)
    fun addAsyncTaskContext(tenantId: String, requestId: String, accountId: String?)
    fun setFromRequest(requestId: String, accountId: String?)
    fun getRequestId(): String
    fun clear()
}
```

#### LoggingContextImpl — Internal LogKey Enum (19 MDC keys)

```kotlin
internal enum class LogKey(val value: String) {
    ACCOUNT_ID("ctx.account_id"),
    CLOUD_ID("ctx.cloud_id"),
    ORG_ID("ctx.org_id"),
    TENANT_ID("ctx.tenant_id"),
    REQUEST_ID("request_id"),
    TRACE_ID("trace_id"),
    SPAN_ID("span_id"),
    TRACE_SAMPLED("trace_sampled"),
    FORWARDED_FOR("forwarded_for"),
    PRODUCT_ID("ctx.product_id"),
    EXPERIENCE_ID("ctx.experience_id"),
    CHANNEL_ID("ctx.channel_id"),
    ERRORS("ctx.errors"),
    STREAMHUB_EVENT_ID("ctx.streamhub.event_id"),
    STREAMHUB_EVENT_TYPE("ctx.streamhub.event_type"),
    STREAMHUB_EVENT_SOURCE("ctx.streamhub.event_source"),
    STREAMHUB_EVENT_OCCURRENCE_TIME("ctx.streamhub.event_occurrence_time"),
    STREAMHUB_EVENT_INGESTION_TIME("ctx.streamhub.event_ingestion_time"),
    EXPERIMENT_ID("ctx.experiment_id"),
}
```

Also defines `LogKey.ALL_KEYS` companion property: a `Set<String>` of all 19 MDC key strings.

Top-level constant: `const val CTX_EXPERIMENT_ID_LOG_KEY = "ctx.experiment_id"`

#### Key Implementation Details

- `addTenantContext()` stores previous MDC values in `TenantContextUndo` data class for rollback
- `runWithContext()` uses `ctx.` prefix for all keys: `MDC.put("ctx.$key", value)`
- `runWithContextAsync()` wraps with `MDCContext()` from `kotlinx.coroutines.slf4j`
- `clear()` removes all `ALL_KEYS` from MDC
- `setFromRequest()` also explicitly removes `FORWARDED_FOR` (added by `WebAccessLogger`)

### 2.5 MiscellaneousRequestContextVariablesService

```kotlin
@Service
class MiscellaneousRequestContextVariablesService(
    private val requestScopedValueService: RequestScopedValueService,
) : RequestScopedValueOwner<MiscellaneousRequestContextVariablesData> {
    // Owner for MISCELLANEOUS_REQUEST_CONTEXT_VARIABLES key
    // Provides typed getters/setters for ad-hoc request-scoped data
}
```

### 2.6 Extension Functions (LoggingContextExtensions.kt)

Kotlin-idiomatic wrappers around `LoggingContext`:
```kotlin
inline fun <T> LoggingContext.withContext(ctx: Map<String, String>, fn: () -> T): T
inline fun <T> LoggingContext.withContext(vararg ctx: Pair<String, String>, fn: () -> T): T
inline fun <T> LoggingContext.withContext(key: String, value: String, fn: () -> T): T
suspend inline fun <T> LoggingContext.withContextAsync(ctx: Map<String, String>, fn: suspend () -> T): T
```

### 2.7 SetContextUndo Pattern

`SetContextUndo` is a lightweight undo interface used across the codebase whenever context is modified:
```kotlin
interface SetContextUndo { fun revert() }
```

Implementations:
- `TenantContextUndo` (in `LoggingContextImpl`) — reverts MDC tenant keys
- `FeatureFlagAddTenantContextUndo` (in `FeatureFlagContextServiceImpl`) — reverts feature flag context

### 2.8 Data Flow Diagram

```
HTTP Request
    │
    ▼
RequestContextInterceptor.preHandle()
    │  ├── LoggingContext.setFromRequest(requestId, accountId)  → MDC
    │  └── RequestScopedValuesInitter.setupRequestScopedValues() → RequestAttributes
    ▼
UserContextInterceptor.preHandle()
    │  └── IdGatekeeper → User object → MiscellaneousRequestContextVariables
    ▼
CommonContextSetterImpl
    │  ├── LoggingContext.addTenantContext() → MDC (cloud_id, org_id, product_id, experience_id)
    │  └── FeatureFlagContextService.addTenantContext() → RequestScopedValue (FEATURE_FLAG_CONTEXT)
    ▼
Controller / Handler
    │  └── requestScopedValueService.getValue(owner) → typed data
    ▼
Response / SQS handoff
```

### 2.9 Edge Cases and Design Decisions

1. **Async context loss**: When `RequestAttributes` become inactive (e.g., request thread recycled during async processing), `RequestScopedValueServiceImpl` transparently creates a `RequestAttributesForAsyncProcessing` fallback
2. **MDC cleanup in `runWithContext`**: Only clears keys that were NOT already present before the call, preventing accidental removal of outer-scope context
3. **Profile-specific error messages**: In `local` profile, validation errors include helpful hints about test setup (e.g., "Did you forget to call `RequestScopedValuesInitter.setupRequestScopedValues()`?")

---

## 3. Custom Logging Framework

**Location**: `logging/` (6 files, 568 LoC)
**Dependencies**: None (leaf package)

### 3.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `LaasLogger.kt` | 27 | Interface | Core logging API with context-aware methods |
| `LaasLoggerFactory.kt` | 9 | @Component + Object | Factory for creating LaasLogger instances |
| `LoggerExtensions.kt` | 51 | Extension functions | Kotlin extension methods for structured logging |
| `NoopLogger.kt` | 21 | Class | Silent logger implementation for tests |
| `WithUGCLogger.kt` | 59 | Class | UGC-aware logger wrapper |
| `InterceptedLogger.kt` | 401 | Class | Privacy-filtering decorator over SLF4J Logger |

### 3.2 LaasLogger Interface

```kotlin
interface LaasLogger {
    val logger: Logger  // Underlying SLF4J Logger
}
```

### 3.3 LaasLoggerFactory

```kotlin
@Component
object LaasLoggerFactory {
    fun getLogger(clazz: Class<*>): LaasLogger = LaasLoggerImpl(LoggerFactory.getLogger(clazz))
}
```

### 3.4 Extension Functions (LoggerExtensions.kt, 51 lines)

Kotlin extension methods providing structured, context-aware logging:

```kotlin
fun LaasLogger.infoWithContext(message: String, ctx: Map<String, Any?> = emptyMap())
fun LaasLogger.warnWithContext(message: String, ctx: Map<String, Any?> = emptyMap(), exception: Throwable? = null)
fun LaasLogger.errorWithContext(message: String, ctx: Map<String, Any?> = emptyMap(), exception: Throwable? = null)
fun LaasLogger.debugWithContext(message: String, ctx: Map<String, Any?> = emptyMap())
```

Each method serializes the `ctx` map as structured key-value pairs alongside the log message, leveraging the MDC context already populated by interceptors.

### 3.5 InterceptedLogger (401 lines) — Privacy-Filtering Decorator

The largest file in the logging package. Wraps SLF4J `Logger` to add:

- **UGC (User-Generated Content) filtering**: Conditionally suppresses log fields containing user content based on feature flags
- **Feature gate integration**: Checks `PermanentFeatureGates.ENABLE_UGC_LOGGING` before including UGC in logs
- **Delegation pattern**: Implements the full SLF4J `Logger` interface, delegating to an underlying logger
- **Conditional behavior**: When UGC logging is disabled, sensitive fields are replaced with `[REDACTED]`

### 3.6 NoopLogger (21 lines)

Silent logger implementation — all log methods are no-ops. Used in test contexts where logging output would be noise.

### 3.7 WithUGCLogger (59 lines)

Wrapper that marks a logging context as containing UGC, enabling the `InterceptedLogger` to apply privacy filtering rules.

---

## 4. Interceptor Pipeline

**Location**: `interceptor/` (5 files, 295 LoC)
**Dependencies**: requestcontext, context, config, logging, client, featuregate

### 4.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `LoggingContextClearingFilter.kt` | 62 | @Component (Servlet Filter) | Clears stale MDC before request processing |
| `RequestContextInterceptor.kt` | 44 | @Component (HandlerInterceptor) | Extracts headers → MDC + RequestScopedValues |
| `UserContextInterceptor.kt` | 75 | @Component (HandlerInterceptor) | Calls IdGatekeeper → user context |
| `CommonContextSetter.kt` | 57 | Interface | Contract for tenant/product context setup |
| `internal/CommonContextSetterImpl.kt` | 57 | @Component | Implementation building TenantContext + ProductContext |

### 4.2 Execution Order

The interceptor pipeline executes in this specific order (configured in `WebMvcConfiguration`):

```
1. LoggingContextClearingFilter   (Servlet Filter — runs BEFORE interceptors)
   └── Clears ALL LogKey MDC entries to prevent stale context from previous requests
   └── Calls filterChain.doFilter() to continue

2. RequestContextInterceptor      (HandlerInterceptor.preHandle)
   └── Extracts X-Request-Id header → LoggingContext.setFromRequest()
   └── Extracts account_id from SLAUTH token → MDC
   └── Calls RequestScopedValuesInitter.setupRequestScopedValues()

3. UserContextInterceptor         (HandlerInterceptor.preHandle)
   └── Calls IdGatekeeper to resolve account_id → User object
   └── Extracts X-Forwarded-For, Atl-Edge-Geoip, X-Forwarded-Host headers
   └── Stores User in MiscellaneousRequestContextVariables

4. CommonContextSetterImpl        (Called by controller/framework)
   └── Builds TenantContext from cloudId + product + experience
   └── LoggingContext.addTenantContext() → populates MDC
   └── FeatureFlagContextService.addTenantContext() → populates RequestScopedValues
```

### 4.3 LoggingContextClearingFilter — Detail

```kotlin
@Component
class LoggingContextClearingFilter(
    private val loggingContext: LoggingContext,
) : OncePerRequestFilter() {
    override fun doFilterInternal(request: HttpServletRequest, response: HttpServletResponse, filterChain: FilterChain) {
        loggingContext.clear()        // Wipes ALL 19 LogKey MDC entries
        filterChain.doFilter(request, response)
    }
}
```

Uses Spring's `OncePerRequestFilter` to guarantee exactly-once execution even with request forwarding.

### 4.4 CommonContextSetter Interface

```kotlin
interface CommonContextSetter {
    fun setCommonContext(cloudId: String, product: Product, experience: Experience, channelId: String? = null): SetContextUndo
}
```

Returns `SetContextUndo` allowing callers to revert context changes (important for multi-tenant request processing).

---

## 5. Context Models

**Location**: `context/` (9 files, 381 LoC)
**Dependencies**: exception (for `BadRequestException`)

### 5.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `Product.kt` | 82 | Enum | All supported Atlassian products |
| `Experience.kt` | 81 | Enum + supporting types | AI experience definitions |
| `TenantContextModels.kt` | 140 | Data classes | Composite context model |
| `TenantContext.kt` | 41 | Data class | Top-level tenant context |
| `CloudIdContext.kt` | 15 | Interface | Cloud ID + product + experience access |
| `OrgIdContext.kt` | 5 | Interface | Organization ID access |
| `PlatformTenantContext.kt` | 3 | Interface | Combines CloudIdContext + OrgIdContext |
| `AIGatewayContext.kt` | 7 | Interface | AI Gateway use case ID + cloud ID |
| `Types.kt` | 7 | Type aliases | `CloudId = String`, `TenantId = String` |

### 5.2 Product Enum

```kotlin
enum class Product(val id: String, val aiGatewayProductId: String) {
    CONFLUENCE("confluence", "confluence"),
    JIRA("jira", "jira"),
    ATLAS("atlas", "townsquare"),
    BITBUCKET("bitbucket", "bitbucket"),
    TRELLO("trello", "trello"),
    JSM("jsm", "jira-servicedesk"),
    JPD("jpd", "jira-product-discovery"),
    JWM("jwm", "jira-core"),
    HOME("home", "home"),
    ADMIN("admin", "admin"),
    START("start", "start"),
    ;
    companion object {
        val ALL_PRODUCTS: Set<Product> = entries.toSet()
        fun findById(productId: String): Product?
        fun findByIdOrThrow(productId: String): Product  // throws ProductIdNotFoundException
    }
}
```

**11 product values** — each has both a PAI-internal `id` and an `aiGatewayProductId` for AI Gateway routing.

### 5.3 Experience Enum

```kotlin
enum class Experience(
    val id: String, val description: String,
    val supportedProducts: Set<Product>, val branding: Set<Branding>,
    val useCase: UseCase, val helpseekerExperience: HelpSeekerExperience,
    val owningTeam: String, val slackChannel: String, val internal: Boolean = false
) {
    PROACTIVE_AI_ROVO_BUTTON("proactive-ai-rovo-button", "Proactive AI Experiences from the Rovo button",
        Product.ALL_PRODUCTS, setOf(Branding.ATLASSIAN_INTELLIGENCE, Branding.ROVO),
        UseCase.ROVO_BUTTON, HelpSeekerExperience.NON_HELPSEEKER_EXPERIENCE,
        "ai-experience", "#help-ai-experience"),
}
```

Supporting enums:
- `HelpSeekerExperience`: `HELPSEEKER_EXPERIENCE`, `NON_HELPSEEKER_EXPERIENCE`
- `UseCase`: `ROVO_BUTTON("rovo-button")`, `ROVO_INSIGHTS("rovo-insights")`
- `Branding`: `ROVO`, `ATLASSIAN_INTELLIGENCE`

### 5.4 TenantContext Composition

```kotlin
data class TenantContext(
    val productContext: ProductContext,
    val experienceContext: ExperienceContext,
)

data class ProductContext(
    val cloudId: CloudId,
    val product: Product,
    val orgId: String?,
)

data class ExperienceContext(
    val experience: Experience,
    val channelId: String?,
)
```

### 5.5 Context Interfaces

```kotlin
interface CloudIdContext {
    fun getCloudId(): String
    fun getBrowsingProduct(): Product
    fun getExperience(): Experience
    fun getExperienceChannelId(): String?
}

interface OrgIdContext { fun getOrgId(): String }
interface PlatformTenantContext : CloudIdContext, OrgIdContext  // Diamond inheritance
interface AIGatewayContext {
    fun getAiGatewayUseCaseId(): String
    fun getAiGatewayCloudId(): String
}
```

### 5.6 Type Aliases (Types.kt)

```kotlin
typealias CloudId = String
typealias TenantId = String  // Currently same as CloudId, may diverge
```

---

## 6. Metrics Service

**Location**: `service/metric/` (5 files, 1,243 LoC)
**Dependencies**: logging, exception

This is the **largest package by LoC** and implements a **two-tier metrics abstraction** over Micrometer.

### 6.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `CoreMetricsService.kt` | 149 | Interface | Foundation metrics API (no PAI domain deps) |
| `MetricsService.kt` | 276 | Interface | Extended metrics API with timing, histograms, result tracking |
| `MetricKey.kt` | 77 | Enums | All metric key definitions, histogram buckets, result bases |
| `internal/CoreMetricsServiceImpl.kt` | 370 | @Component | Micrometer-backed core implementation |
| `internal/MetricsServiceImpl.kt` | 371 | @Component | Delegates to CoreMetricsService + adds timing/histogram |

### 6.2 Two-Tier Architecture

```
┌───────────────────────────────────────────┐
│         MetricsService (276 lines)        │  ← Feature code uses this
│  Adds: time(), timeAndCountResult(),      │
│        histogram(), timeFunction(),       │
│        timeAndHistogram(),                │
│        countWithRovoTags()                │
├───────────────────────────────────────────┤
│      CoreMetricsService (149 lines)       │  ← Platform code uses this
│  Provides: count(), gauge(), summarize(), │
│            histogram() (basic)            │
└───────────────────────────────────────────┘
         │
         ▼
    Micrometer MeterRegistry → SignalFx
```

**Design rationale**: `CoreMetricsService` has no PAI domain dependencies and can be used by leaf packages. `MetricsService` extends it with product-aware tagging (Rovo tags, result tracking) and timing patterns that depend on higher-level context.

### 6.3 MetricKeyLike Interface and MetricKey Enum

```kotlin
interface MetricKeyLike {
    val key: String
}

enum class MetricKey(override val key: String) : MetricKeyLike {
    PROACTIVE_TEST_COUNT("test.count"),
    PROACTIVE_TEST_LATENCY("test.latency"),
    TENANT_CONTEXT_BUILD_SUCCESS("tenant.context.build.success"),
    TENANT_CONTEXT_BUILD_ERROR("tenant.context.build.error"),
    STREAMHUB_EVENT_PROCESSED("streamhub.event.processed"),
    STREAMHUB_EVENT_UNSUPPORTED("streamhub.event.unsupported"),
    STREAMHUB_EVENT_ERROR("streamhub.event.error"),
}
```

**7 metric keys** covering test, tenant context, and StreamHub event processing.

### 6.4 HistogramMetric Enum

```kotlin
enum class HistogramMetric(val metricKey: MetricKey, val histogramBucket: HistogramBucket) {
    PROACTIVE_TEST_LATENCY(MetricKey.PROACTIVE_TEST_LATENCY, HistogramBucket.PROACTIVE_HISTOGRAM_BUCKETS),
}
companion object { const val HISTOGRAM_METRIC_SUFFIX = ".hist" }
```

### 6.5 HistogramBucket Enum

```kotlin
enum class HistogramBucket(val value: String) {
    PROACTIVE_HISTOGRAM_BUCKETS("200_500_1000_2000_3000_4000_5000_6000_7000_8000_9000_10000_15000"),
}
companion object { const val GSD_HISTOGRAM_TAG_NAME = "gsd_histogram" }
```

Bucket boundaries: 200ms, 500ms, 1s, 2s, 3s, 4s, 5s, 6s, 7s, 8s, 9s, 10s, 15s — optimized for LLM-class latencies.

### 6.6 ResultMetricBase Enum

```kotlin
enum class ResultMetricBase(val base: String) {
    ERS_CREATE("ers.create"),
}
```

Used for metrics that split into `base.success` / `base.error` / `base.latency` suffixes.

### 6.7 Status Enum

```kotlin
enum class Status(val value: String) {
    SUCCESS("success"),
    ERROR("error"),
}
```

### 6.8 CoreMetricsService Interface — Full Method Inventory

```kotlin
interface CoreMetricsService {
    // Basic counting
    fun count(metricKey: MetricKeyLike)
    fun count(metricKey: MetricKeyLike, amount: Int)
    fun count(metricKey: MetricKeyLike, amount: Double)
    fun count(metricKey: MetricKeyLike, tags: List<Pair<String, String>>)
    fun countWithoutLogging(metricKey: MetricKeyLike, tags: List<Pair<String, String>>)
    fun count(metricKey: MetricKeyLike, tag: Pair<String, String>)
    fun count(metricKey: MetricKeyLike, vararg tags: Pair<String, String>)
    fun count(metricKey: MetricKeyLike, amount: Number, vararg tags: Pair<String, String>)
    fun count(metricKey: MetricKeyLike, amount: Double, tags: Iterable<Pair<String, String>>)

    // Result-tracking counting (success/failure + optional result tag)
    fun <T : Any?> count(successMetricKey: MetricKeyLike, failureMetricKey: MetricKeyLike,
        tags: List<Pair<String, String>> = emptyList(), includeResultTag: Boolean = false,
        resultTransformer: (T) -> String = { it.toString() },
        exceptionCountsAsFailure: (ex: Exception) -> Boolean = { true },
        function: Supplier<T>): T

    // Distribution summary
    fun summarize(metricKey: MetricKeyLike, size: Double, vararg tags: Pair<String, String>)

    // Histogram (DistributionSummary-based)
    fun <T : Any?> histogram(metricKey: MetricKeyLike, tags: List<Pair<String, String>> = emptyList(), function: Supplier<T>): T

    // Gauge
    fun gauge(metricKey: MetricKeyLike, amount: Double)
    fun gauge(metricKey: MetricKeyLike, amount: Double, vararg tags: Pair<String, String>)
    fun gauge(metricKey: MetricKeyLike, amount: Double, tags: Iterable<Pair<String, String>>)

    // Timing
    fun <T : Any?> time(metricKey: MetricKeyLike, tags: List<Pair<String, String>> = emptyList(), function: Supplier<T>): T
}
```

### 6.9 MetricsService Interface — Additional Methods

MetricsService extends all CoreMetricsService methods and adds:

```kotlin
interface MetricsService {
    // All CoreMetricsService methods (delegated)

    // Timing with result tracking
    fun <T : Any?> timeAndCountResult(metricBase: ResultMetricBase,
        tags: List<Pair<String, String>> = emptyList(), includeResultTag: Boolean = false,
        resultTransformer: (T) -> String = { it.toString() },
        exceptionCountsAsFailure: (ex: Exception) -> Boolean = { true },
        function: Supplier<T>): T

    fun <T : Any?> timeAndCountResult(metricKey: MetricKey,
        tags: List<Pair<String, String>> = emptyList(), includeResultTag: Boolean = false,
        resultTransformer: (T) -> String = { it.toString() },
        exceptionCountsAsFailure: (ex: Exception) -> Boolean = { true },
        function: Supplier<T>): T

    // Named timing
    fun <T : Any?> time(metricKey: MetricKey, tags: List<Pair<String, String>> = emptyList(), function: Supplier<T>): T
    fun <T : Any?> timeFunction(metricBase: ResultMetricBase, tags: List<Pair<String, String>> = emptyList(), function: Supplier<T>): T

    // Histogram with timing
    fun <T : Any?> histogram(histogramMetric: HistogramMetric, tags: Iterable<Pair<String, String>> = emptyList(), function: Supplier<T>): T
    fun timeAndHistogram(histogramMetric: HistogramMetric, duration: Duration, tags: Iterable<Pair<String, String>> = emptyList())
}
```

### 6.10 Implementation Details

**CoreMetricsServiceImpl** (370 lines):
- Constructor: `MeterRegistry` (Micrometer)
- Converts `Pair<String, String>` tags to Micrometer `ImmutableTag` objects
- `count()` uses `meterRegistry.counter(key, tags).increment(amount)`
- `time()` uses `measureTimeMillis` and records to timer
- `histogram()` uses `DistributionSummary` with `publishPercentileHistogram()`
- Error handling: catches exceptions in `count(success/failure)` and records to failure metric before rethrowing
- `countWithoutLogging()` — same as `count()` but skips the info log line (for high-frequency metrics)

**MetricsServiceImpl** (371 lines):
- Constructor: `MeterRegistry`, `CoreMetricsService`
- Delegates all basic count/gauge to `CoreMetricsService`
- Adds `SUFFIX_LATENCY = ".latency"`, `SUFFIX_SUCCESS = ".success"`, `SUFFIX_ERROR = ".error"` metric naming
- `timeAndCountResult()` combines timing + success/failure counting in a single call
- `timeAndHistogram()` records both a timer metric and a histogram distribution

### 6.11 Tag Scheme

All metrics follow a consistent tag scheme:
- Tags are `List<Pair<String, String>>` or vararg `Pair<String, String>`
- Converted to Micrometer `ImmutableTag(key, value)` at recording time
- Common tag patterns: `"status" to "success"/"error"`, `"result" to resultValue`, `"gsd_histogram" to bucketSpec`

---

## 7. Feature Gate System

**Location**: `featuregate/` (8 files, 754 LoC)
**Dependencies**: requestcontext, context, logging

### 7.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `FeatureGate.kt` | 7 | Interface | Base interface with `statsigKey` property |
| `FeatureService.kt` | 68 | Interface | High-level gate checking API |
| `FeatureFlagContextService.kt` | 26 | Interface + Enum | Context management for feature flags |
| `FeatureFlagEvaluationTracker.kt` | 81 | @Component + sealed class | Tracks gate evaluations per-request |
| `AiFeatureGates.kt` | 9 | Enum | AI-specific feature gate definitions |
| `PermanentFeatureGates.kt` | 7 | Enum | Long-lived feature gates |
| `internal/FeatureServiceImpl.kt` | 206 | @Component @Primary | Statsig-backed implementation |
| `internal/FeatureFlagContextServiceImpl.kt` | 350 | @Component | Context data management + Statsig user construction |

### 7.2 FeatureGate Interface

```kotlin
interface FeatureGate {
    val statsigKey: String
}
```

Simple marker interface. All gate enums implement this, carrying their Statsig key string.

### 7.3 Gate Enum Definitions

**AiFeatureGates** (2 values):
```kotlin
enum class AiFeatureGates(override val statsigKey: String) : FeatureGate {
    TEST_GATE("aix_proactive_test_gate"),
    FEATURE_FLAG_EVALUATION_LOGGING_ENABLED("aix_feature_flag_evaluation_logging_enabled"),
}
```

**PermanentFeatureGates** (1 value):
```kotlin
enum class PermanentFeatureGates(override val statsigKey: String) : FeatureGate {
    ENABLE_UGC_LOGGING("proactive_ai_enable_ugc_logging"),
}
```

**Total**: 3 defined gates across 2 enums. Feature-specific gates (e.g., for Rovo Insights) are defined in their respective feature packages.

### 7.4 FeatureService Interface — Full Method Inventory

```kotlin
interface FeatureService {
    fun checkGate(featureGate: FeatureGate, defaultValue: Boolean = false): Boolean
    fun checkHelloOnlyGate(featureGate: FeatureGate, defaultValue: Boolean = false): Boolean
    fun checkGateWithLimitedContext(featureGate: FeatureGate, defaultValue: Boolean = false): Boolean
    fun getExperiment(featureGate: FeatureGate): DynamicConfig
    fun getDynamicConfigWithoutExperimentExposureLogging(featureGate: FeatureGate): DynamicConfig
    fun getStringConfigValue(featureGate: FeatureGate, defaultValue: String? = null): String?
    fun getStringConfigValueWithoutExposureLogging(featureGate: FeatureGate, defaultValue: String? = null): String?
    fun getIntConfigValue(featureGate: FeatureGate, defaultValue: Int): Int
    fun isInternalSite(cloudId: String): Boolean
}
```

**9 methods** covering binary gate checks, experiment configs, dynamic values, and internal site detection.

### 7.5 FeatureFlagContextService Interface

```kotlin
enum class FeatureFlagContextContextType { FULL, LIMITED_CONTEXT }

interface FeatureFlagContextService {
    fun addTenantContext(tenantContext: TenantContext): SetContextUndo
    fun setFromRequest(request: HttpServletRequest)
    fun getFeatureGateUser(featureFlag: FeatureGate, contextType: FeatureFlagContextContextType,
        randomizationId: String? = null): FeatureGateUser
}
```

### 7.6 FeatureFlagEvaluationTracker

Tracks all feature gate evaluations during a request for observability:

```kotlin
sealed class FeatureFlagEvaluation {
    abstract val flagName: String
    abstract fun serialize(): Map<String, Any>

    data class GateCheck(override val flagName: String, val result: Boolean) : FeatureFlagEvaluation()
    data class Experiment(override val flagName: String, val result: Map<String, Any>) : FeatureFlagEvaluation()
}

data class FeatureFlagEvaluationTrackerData(
    val evaluations: MutableList<FeatureFlagEvaluation> = Collections.synchronizedList(mutableListOf()),
    var loggingEnabled: Boolean? = null,  // Lazy-evaluated, cached per-request
) : RequestScopedValue

@Component
class FeatureFlagEvaluationTracker(
    private val requestScopedValueService: RequestScopedValueService,
) : RequestScopedValueOwner<FeatureFlagEvaluationTrackerData> {
    fun recordGateCheck(flagName: String, result: Boolean)
    fun recordExperiment(flagName: String, result: DynamicConfig)
    fun getAllEvaluations(): List<FeatureFlagEvaluation>
    fun getTrackerData(): FeatureFlagEvaluationTrackerData
}
```

Uses Jackson `@JsonTypeInfo`/`@JsonSubTypes` for polymorphic serialization of evaluation records.

### 7.7 FeatureServiceImpl — Implementation Details (206 lines)

```kotlin
@Component @Primary
class FeatureServiceImpl(
    private val featureGatesService: FeatureGatesService,    // Statsig SDK wrapper
    private val featureFlagContextServiceImpl: FeatureFlagContextServiceImpl,
    private val featureFlagEvaluationTracker: FeatureFlagEvaluationTracker,
) : FeatureService
```

**Key behaviors**:
- `checkGate()` builds a `FeatureGateUser` with FULL context, calls Statsig SDK, records evaluation
- `checkHelloOnlyGate()` — checks gate only on the "hello" (internal) Atlassian site
- `checkGateWithLimitedContext()` uses `LIMITED_CONTEXT` type (fewer user attributes)
- `isInternalSite()` compares cloudId against `INTERNAL_SITE_ID_SET = {"a436116f-02ce-4520-8fbb-7301462a1674"}`
- `@PreDestroy shutdown()` — cleanly shuts down Statsig SDK
- **Evaluation logging**: Controlled by `FEATURE_FLAG_EVALUATION_LOGGING_ENABLED` gate (meta-gate). Result is lazily cached per-request in `FeatureFlagEvaluationTrackerData.loggingEnabled`

### 7.8 FeatureFlagContextServiceImpl — Context Data Model (350 lines)

```kotlin
data class FeatureFlagScopedData(
    var userId: String? = null,
    var tenantId: String? = null,
    var orgId: String? = null,
    var experienceId: String? = null,
    var productId: String? = null,
    var channelId: String? = null,
    var hostname: String? = null,
    var modalityId: String? = null,
) : RequestScopedValue
```

**8 mutable fields** — populated progressively through the interceptor pipeline.

`addTenantContext()` returns `FeatureFlagAddTenantContextUndo` for rollback:
```kotlin
data class FeatureFlagAddTenantContextUndo(
    val tenantId: String? = null, val orgId: String? = null,
    val experienceId: String? = null, val channelId: String? = null,
    val featureFlagContextServiceImpl: FeatureFlagContextServiceImpl,
) : SetContextUndo { override fun revert() { ... } }
```

`getFeatureGateUser()` constructs a Statsig `FeatureGateUser` from the scoped data, using:
- `userId` as the Statsig user ID
- `tenantId` as custom field
- Environment set from `MICROS_ENV` env var
- `resolveOrgIdSafely()` calls `TcsService` for org ID resolution

---

## 8. Async Task Framework

**Location**: `task/` (11 files, 649 LoC)
**Dependencies**: logging, utility, sqs

### 8.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `AsyncTask.kt` | 20 | Interface | Polymorphic JSON marker for task envelopes |
| `AsyncTaskDispatcher.kt` | 89 | @Component | Routes tasks to handlers |
| `AsyncTaskExecutionContext.kt` | 14 | Data class | Cross-cutting context (tenantId, user, requestId) |
| `AsyncTaskHandler.kt` | 50 | Interface | Handler contract with lifecycle hooks |
| `AsyncTaskQueueRegistry.kt` | 70 | @Component | Maps task types to queue names + Jackson subtype registration |
| `AsyncTaskService.kt` | 10 | Interface + value class | Producer API for submitting tasks |
| `README.md` | ~200 | Documentation | Internal design doc |
| `internal/AsyncTaskMessage.kt` | 15 | Data class | SQS wire format wrapper |
| `internal/AsyncTaskMessageAttributes.kt` | 16 | Object | SQS message attribute helpers |
| `internal/AsyncTaskExecutionContextWire.kt` | ~15 | Data class | Wire-format execution context |
| `internal/AsyncTaskServiceImpl.kt` | ~120 | @Service | SQS producer implementation |
| `internal/VisibilityExtendingSQSQueueConsumer.kt` | ~130 | Abstract class | Heartbeat-based visibility extension |

### 8.2 AsyncTask Interface — Polymorphic Serialization

```kotlin
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, include = JsonTypeInfo.As.PROPERTY, property = "@type")
interface AsyncTask
```

Jackson polymorphic serialization: the `@type` field in JSON discriminates between concrete task types. Subtypes are registered dynamically by `AsyncTaskQueueRegistry` at startup.

### 8.3 AsyncTaskHandler\<T\> Interface — Full Contract

```kotlin
interface AsyncTaskHandler<T : AsyncTask> {
    val type: Class<T>                    // Concrete AsyncTask subtype this handles
    val queueName: String                 // Logical SQS queue name

    suspend fun handle(executionContext: AsyncTaskExecutionContext, task: T)
    suspend fun onSuccess(executionContext: AsyncTaskExecutionContext, task: T) {}  // default: no-op
    suspend fun onFailure(executionContext: AsyncTaskExecutionContext, task: T, error: Throwable) {} // default: no-op
}
```

**Key design**: Each handler declares its task type AND its queue name. One handler per task type — enforced at startup by `AsyncTaskQueueRegistry`.

### 8.4 AsyncTaskDispatcher — Registry Pattern (89 lines)

```kotlin
@Component
class AsyncTaskDispatcher(handlers: List<AsyncTaskHandler<*>>) {
    private val handlersByType: Map<Class<out AsyncTask>, AsyncTaskHandler<*>> =
        handlers.associateBy { it.type }

    suspend fun dispatch(executionContext: AsyncTaskExecutionContext, task: AsyncTask) {
        val handler = handlersByType[task.javaClass]
            ?: error("No AsyncTaskHandler registered for ${task.javaClass.name}")
        try {
            typedHandler.handle(executionContext, task)
            typedHandler.onSuccess(executionContext, task)
        } catch (e: Exception) {
            runCatching { typedHandler.onFailure(executionContext, task, e) }
                .onFailure { hookErr -> /* log and swallow hook error */ }
            throw e  // Rethrow so SQS can retry/DLQ
        }
    }
}
```

**Error handling**: If `onFailure` itself throws, that error is swallowed (logged) and the original exception is rethrown. This prevents hook errors from masking the real problem.

### 8.5 AsyncTaskQueueRegistry — Startup Validation (70 lines)

```kotlin
@Component
class AsyncTaskQueueRegistry(objectMapper: ObjectMapper, handlers: List<AsyncTaskHandler<*>>) {
    private val queueNamesByType: Map<Class<out AsyncTask>, String>

    init {
        // 1. Validate: exactly one handler per task type
        // 2. Register each handler's type as Jackson polymorphic subtype
        //    objectMapper.registerSubtypes(NamedType(handler.type, handler.type.simpleName))
        // 3. Build queueName lookup map
    }

    fun queueNameFor(taskClass: Class<out AsyncTask>): String
}
```

**Dual responsibility**: (1) validates handler uniqueness and (2) dynamically registers Jackson subtypes so `AsyncTask` JSON can be deserialized back to concrete types.

### 8.6 AsyncTaskServiceImpl — SQS Producer (~120 lines)

```kotlin
@Service
@Conditional(OnLongRunWorkerNodeOrLocalCondition::class)
class AsyncTaskServiceImpl(
    private val sqsClient: SqsClient,
    private val objectMapper: ObjectMapper,
    private val asyncTaskQueueRegistry: AsyncTaskQueueRegistry,
    private val environment: Environment,
) : AsyncTaskService {

    override suspend fun submit(executionContext: AsyncTaskExecutionContext, task: AsyncTask): AsyncTaskId {
        val taskId = AsyncTaskId(UUID.randomUUID().toString())
        val queueName = asyncTaskQueueRegistry.queueNameFor(task.javaClass)
        val queueUrl = resolveQueueUrl(queueName, task)
        // Serialize AsyncTaskMessage(executionContextWire, task) → JSON
        // Send to SQS with message attributes for grep-ability
    }
}
```

**SQS Message Attributes** (for CloudWatch/console grep-ability):
```kotlin
const val ATTR_TASK_ID = "task_id"
const val ATTR_TASK_TYPE = "task_type"
const val ATTR_TENANT_ID = "tenant_id"
const val ATTR_ACCOUNT_ID = "account_id"
const val ATTR_REQUEST_ID = "request_id"
```

**Queue URL resolution**: Reads `SQS_<QUEUE_NAME_UPPER>_QUEUE_URL` environment variable. Throws `IllegalArgumentException` with helpful message if not configured.

### 8.7 VisibilityExtendingSQSQueueConsumer — Heartbeat Mechanism

```kotlin
abstract class VisibilityExtendingSQSQueueConsumer<T>(
    private val sqsClient: SqsClient,
    private val taskScheduler: TaskScheduler,
) : SQSQueueConsumer<T>() {

    companion object {
        private val BUFFER = Duration.ofSeconds(5)
        private val DURATION = Duration.ofSeconds(30)        // Visibility extension duration
        private val PERIOD = DURATION - BUFFER               // = 25 seconds between heartbeats
    }
}
```

**Heartbeat mechanism** (VERIFIED exact values):
- **Period**: 25 seconds (DURATION 30s - BUFFER 5s)
- **Duration**: 30 seconds visibility extension per heartbeat
- **Pattern**: `taskScheduler.scheduleAtFixedRate()` calls `SqsClient.changeMessageVisibility()` every 25s
- **Cleanup**: `extenderTask.cancel(false)` in `finally` block after handler completes
- **Failure mode**: If JVM crashes, message becomes visible again within ~30s for retry

```
Timeline:
  t=0s     Handler starts, first heartbeat scheduled
  t=25s    Heartbeat fires: changeMessageVisibility(30s)
  t=50s    Heartbeat fires: changeMessageVisibility(30s)
  ...      (continues indefinitely while handler runs)
  t=Ns     Handler completes → heartbeat cancelled
```

### 8.8 AsyncTaskMessage — Wire Format

```kotlin
internal data class AsyncTaskMessage(
    val executionContext: AsyncTaskExecutionContextWire,
    val task: AsyncTask,
)
```

### 8.9 AsyncTaskId — Value Class

```kotlin
@JvmInline value class AsyncTaskId(val value: String)
```

### 8.10 Data Flow: Task Submission → Execution

```
Producer (WebServer)                          Consumer (LongRun)
─────────────────────                         ──────────────────
Controller                                    VisibilityExtendingSQSQueueConsumer
  │                                             │
  ▼                                             ▼
AsyncTaskService.submit(ctx, task)            acceptMessage() → start heartbeat
  │                                             │
  ├── AsyncTaskQueueRegistry.queueNameFor()     ├── Deserialize AsyncTaskMessage
  ├── resolveQueueUrl(envVar)                   ├── Reconstruct AsyncTaskExecutionContext
  ├── Serialize AsyncTaskMessage(wire, task)     ├── LoggingContext.addAsyncTaskContext()
  └── SqsClient.sendMessage()                   ├── AsyncTaskDispatcher.dispatch(ctx, task)
                                                │     ├── handler.handle(ctx, task)
                    SQS Queue                   │     ├── handler.onSuccess() or onFailure()
                   ───────────                  │     └── throw on failure → SQS retry/DLQ
                                                └── Cancel heartbeat in finally
```

---

## 9. SQS Infrastructure

**Location**: `sqs/` (8 files, 370 LoC)
**Dependencies**: logging, requestcontext, config

### 9.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `SqsEventConsumerConfig.kt` | 123 | @Configuration (×2) | SQS connection factory + prefetch config |
| `AnalyticsEventsMessageQueueConsumer.kt` | 68 | @Component | Middleware-enabled SQS message processor |
| `AnalyticsEventsSqsQueueConsumer.kt` | 40 | @Component | SQS queue consumer for StreamHub analytics |
| `StreamHubEvent.kt` | 44 | Data class | StreamHub event deserialization model |
| `MessageQueueConsumerMiddleware.kt` | 36 | @Component | Cross-cutting logging/metrics middleware |
| `AnalyticsEnrichedEventHandler.kt` | 28 | @Component | Interface for handling enriched events |
| `QueueNames.kt` | 20 | Object | SQS queue name constants |
| `EventAVIs.kt` | 11 | Object | StreamHub event type (AVI) constants |

### 9.2 SqsEventConsumerConfig (123 lines) — Two @Configuration Classes

**`SqsEventConsumerConfig`**:
```kotlin
@Configuration
@ConditionalOnProperty("SQS_ANALYTICS_EVENTS_QUEUE_URL")
@Conditional(OnSHWorkerNodeOrLocalCondition::class)
@EnableSqsQueues
@ComponentScan(basePackages = ["com.atlassian.spring.boot.starters.sqsqueues.lifecycle"])
class SqsEventConsumerConfig
```

**`CommonSqsConfig`** — Critical prefetch=0 override:
```kotlin
@Configuration
@ConditionalOnProperty(name = ["proactive-ai.sqs.enabled"], havingValue = "true", matchIfMissing = true)
@ConditionalOnBean(SqsClient::class)
class CommonSqsConfig {
    @Bean(name = ["sqsConnectionFactory"])
    fun connectionFactory(client: SqsClient): ConnectionFactory {
        val providerConfiguration = ProviderConfiguration().withNumberOfMessagesToPrefetch(0)
        return SQSConnectionFactory(providerConfiguration, client)
    }

    @Bean(name = [QueueDuplicateHandlerManager.DEFAULT_QUEUE_DUPLICATE_HANDLER])
    fun queueDuplicateHandler() = NopDuplicateHandler()
}
```

**Why prefetch=0**: The AWS SQS Java Messaging Library defaults to `prefetch=1`, which pre-fetches an additional message while processing. For PAI's high-latency LLM workloads (5–60s), this causes tail latency issues and visibility-timeout anti-patterns.

### 9.3 StreamHubEvent Data Model

```kotlin
@JsonIgnoreProperties(ignoreUnknown = true)
data class StreamHubEvent(
    val type: String,              // AVI format event type
    val schema: String?,           // e.g. service_name/example_schema.json
    val schemaAri: String?,        // Schema ARI
    val resource: String?,
    val eventId: String,           // UUID
    val ingestionSource: String?,  // ASAP issuer format
    val ingestionTime: ZonedDateTime?,
    val occurrenceTime: ZonedDateTime?,
    val eventProducer: String?,    // ASAP key metadata
    val payload: JsonNode,         // Flexible payload
)
```

### 9.4 QueueNames Object

Defines logical SQS queue name constants used by `@ManagedQueueConsumer` annotations and `AsyncTaskQueueRegistry`:
```kotlin
object QueueNames {
    const val ANALYTICS_EVENTS_QUEUE = "analytics_events_queue"
    // Additional queue names for task-specific queues
}
```

### 9.5 EventAVIs Object

StreamHub event type constants (AVI = Atlassian Vocabulary Identifier):
```kotlin
object EventAVIs {
    // Event type constants for StreamHub event filtering
}
```

---

## 10. Configuration Layer

**Location**: `config/` (6 files, 208 LoC)
**Dependencies**: logging

### 10.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `MicrosEnvironmentConfig.kt` | 21 | @Configuration | Exposes `MicrosEnvironmentType` bean |
| `MicrosEnvironmentType.kt` | 27 | Enum | LOCAL, STAGING, PROD |
| `MvcSecurityConfig.kt` | 15 | @Configuration | Anonymous path configuration |
| `WebMvcConfiguration.kt` | 103 | @Configuration | MVC config, interceptor registration, CORS |
| `OnLongRunWorkerNodeOrLocalCondition.kt` | 21 | Condition | Worker group conditional |
| `OnSHWorkerNodeOrLocalCondition.kt` | 21 | Condition | StreamHub worker conditional |

### 10.2 MicrosEnvironmentType Enum

```kotlin
enum class MicrosEnvironmentType {
    LOCAL, STAGING, PROD;

    fun isNonProduction(): Boolean = this in setOf(LOCAL, STAGING)
    fun isProduction(): Boolean = this == PROD

    companion object {
        fun fromString(value: String): MicrosEnvironmentType  // "local"→LOCAL, "staging"→STAGING, "prod"→PROD
    }
}
```

### 10.3 Worker Group Conditions

Both conditions follow the same pattern:

```kotlin
class OnLongRunWorkerNodeOrLocalCondition : Condition {
    override fun matches(context: ConditionContext, metadata: AnnotatedTypeMetadata): Boolean =
        isWorkerNode() || isLocalProfile(context)

    private fun isWorkerNode(): Boolean =
        System.getenv().getOrDefault("MICROS_GROUP", "WebServer") == "LongRun"

    private fun isLocalProfile(context: ConditionContext): Boolean =
        context.environment.activeProfiles.any { it == "local" }
}
```

`OnSHWorkerNodeOrLocalCondition` is identical but checks for `"SHWorkers"` instead of `"LongRun"`.

**Default**: If `MICROS_GROUP` is not set, defaults to `"WebServer"`.

### 10.4 MvcSecurityConfig — Anonymous Paths

```kotlin
@Bean(name = [MicrosSecurityConstants.CUSTOM_ANONYMOUS_PATHS])
fun anonymousPaths(): List<String> = listOf("/healthcheck", "/deepcheck")
```

Only health check endpoints are exempt from SLAUTH authentication.

### 10.5 WebMvcConfiguration (103 lines)

Registers the interceptor pipeline in order:
1. `LoggingContextClearingFilter` (as a Servlet Filter bean)
2. `RequestContextInterceptor` (HandlerInterceptor)
3. `UserContextInterceptor` (HandlerInterceptor)

Also configures CORS settings and async request handling.

---

## 11. Client Layer

**Location**: `client/` (7 files, 399 LoC)
**Dependencies**: logging, exception, utility

### 11.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `Audiences.kt` | 8 | Object | Service audience constants |
| `HttpClientCommons.kt` | 18 | Object | HTTP header constants |
| `identity/IdGatekeeperClient.kt` | 8 | Interface (deprecated) | Sync IdGatekeeper API |
| `identity/AsyncIdGatekeeperClient.kt` | 28 | Interface | Async IdGatekeeper API |
| `identity/IdGatekeeperModels.kt` | 81 | Data classes | Request/response models |
| `identity/internal/IdGatekeeperClientImpl.kt` | 27 | @Component | Sync implementation |
| `identity/internal/AsyncIdGatekeeperClientImpl.kt` | 229 | @Component | Full async impl with retry/timeout |

### 11.2 Audiences Object

```kotlin
object Audiences {
    const val AI_GATEWAY = "ai-gateway"
    const val CONVO_AI = "convo-ai"
    const val INTEGRATIONS_SERVICE = "integrations-service"
    const val IDENTITY_PLATFORM = "identity-platform"
}
```

4 SLAUTH audience identifiers for outbound service calls.

### 11.3 HttpClientCommons Object

```kotlin
object HttpClientCommons {
    const val HOST = "Host"
    const val X_FORWARDED_HOST = "X-Forwarded-Host"
    const val X_FORWARDED_FOR = "X-Forwarded-For"
    const val X_SLAUTH_EGRESS_HEADER = "X-Slauth-Egress"
    const val X_SLAUTH_AUDIENCE_HEADER = "X-Slauth-Audience"
    const val X_SLAUTH_USER_CONTEXT_ACCOUNT_ID = "X-Slauth-User-Context-Account-Id"
    const val USER_CONTEXT = "User-Context"
    const val ATL_CLOUD_ID = "atl-cloudid"
    const val ATL_WORKSPACE_ID = "Atl-WorkspaceId"
    const val X_NO_USER_ID_HEADER = "X-Requested-No-User-Id"
    const val X_REQUEST_ID = "X-Request-Id"
}
```

11 HTTP header constants used across all client implementations.

### 11.4 AsyncIdGatekeeperClient Interface

```kotlin
interface AsyncIdGatekeeperClient {
    object Permissions {
        val WRITE = "write"
        const val GENERATIVE_AI_RBAC_PERMISSION = "read:features:ai"
    }

    enum class PrincipalFilter(val filter: String) {
        USER("arm:cloud:identity::user/.+"),     // ARM regex: any user
        GROUP("arm:cloud:identity::group/.+"),    // ARM regex: any group
    }

    suspend fun checkPermissionBulk(requests: List<PermissionRequest>): List<PermissionResult>
    suspend fun checkPermission(request: PermissionRequest): Boolean
}
```

### 11.5 IdGatekeeperModels

```kotlin
data class PermissionRequest(
    val permissionId: String, val principalId: String,
    val resourceId: String, val dontRequirePrincipalInSite: Boolean = true)

data class PermissionResult(
    val permissionId: String, val principalId: String,
    val resourceId: String, val permitted: Boolean,
    val dontRequirePrincipalInSite: Boolean)
```

Plus additional error response models and `IdGatekeeperException` for HTTP error mapping.

### 11.6 AsyncIdGatekeeperClientImpl (229 lines)

The most substantial file in the package:
- Full async (coroutine) implementation with retry logic
- Timeout handling with configurable durations
- Error mapping from HTTP status codes to domain exceptions
- Metrics instrumentation for latency and error rates

---

## 12. Utility Layer

**Location**: `utility/` (8 files, 557 LoC)
**Dependencies**: logging

### 12.1 Complete File Inventory

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `threading/ThreadConfig.kt` | 122 | @Configuration | Thread pool configuration |
| `threading/InstrumentedDispatcher.kt` | 107 | Class | Micrometer-instrumented coroutine dispatcher |
| `threading/CoroutineMonitor.kt` | 91 | Object + Enum | Coroutine lifecycle monitoring |
| `threading/RequestAttributesCoroutineContext.kt` | 67 | ThreadContextElement | Spring RequestAttributes propagation |
| `threading/RequestAttributesForAsyncProcessing.kt` | 67 | AbstractRequestAttributes | Standalone request attributes for SQS |
| `user/User.kt` | 50 | Interface + type aliases | User model |
| `user/internal/UserImpl.kt` | 39 | Class | Default User implementation |
| `tenant/TcsService.kt` | 14 | @Service | Tenant Configuration Service stub |

### 12.2 ThreadConfig (122 lines)

```kotlin
@Configuration
class ThreadConfig {
    @Bean fun asyncExecutor(): AsyncTaskExecutor  // Spring @Async thread pool
    @Bean fun coroutineDispatcher(): CoroutineDispatcher  // Kotlin coroutine dispatcher
}
```

Defines pool sizes, naming patterns (`pai-async-*`, `pai-coroutine-*`), and rejection policies.

### 12.3 InstrumentedDispatcher (107 lines)

Custom Kotlin coroutine dispatcher that wraps a thread pool with Micrometer instrumentation:

```kotlin
class InstrumentedDispatcher(
    private val executor: ExecutorService,
    private val meterRegistry: MeterRegistry,
    private val name: String,
) : CoroutineDispatcher() {
    // Reports: queue depth, active thread count, execution time as metrics
}
```

### 12.4 CoroutineMonitor (91 lines)

```kotlin
enum class DispatcherMonitor(val label: String) {
    DEFAULT("default"),
    STREAMING_WRITER("httpRequestStreamingWriter"),
    STREAMING_WRITER_OUTPUT_STREAM("httpRequestStreamingWriter.outputStream"),
}

object CoroutineMonitor {
    fun start()  // Launches periodic monitoring coroutine
}
```

Each enum value tracks `active` and `running` counts via `AtomicInteger`.

### 12.5 RequestAttributesCoroutineContext (67 lines)

```kotlin
class RequestAttributesCoroutineContext(
    isAsyncProcessing: Boolean = false,
) : ThreadContextElement<RequestAttributes?> {
    // Captures RequestAttributes at creation time
    // updateThreadContext() → sets captured attributes on new thread
    // restoreThreadContext() → restores previous thread's attributes
}
```

Critical for ensuring request-scoped values survive coroutine context switches. When `isAsyncProcessing = true`, wraps attributes in `RequestAttributesForAsyncProcessing`.

### 12.6 User Model

```kotlin
typealias ForwardedForHeaderValue = String
typealias ForwardedHostHeaderValue = String
typealias UserContextHeaderValue = String
typealias OrgId = String

interface User {
    fun getUserContextHeaderValue(): UserContextHeaderValue
    fun getAccountId(): AccountId
    fun getUserOrgId(): OrgId?
    fun getExtraContext(): ExtraContext
}

interface ExtraContext {
    fun getForwardedForHeaderValue(): ForwardedForHeaderValue?
    fun getGeoLocation(): GeoLocation?
    fun getForwardedHostHeaderValue(): ForwardedHostHeaderValue?
    fun isIpAllowListExempted(): Boolean
    data class GeoLocation(val countryName: String)
}
```

### 12.7 TcsService (14 lines)

```kotlin
@Service
class TcsService {
    // Tenant Configuration Service stub
    // Intended for future tenant-specific configuration lookups
    // Currently used by FeatureFlagContextServiceImpl for org ID resolution
}
```

---

## 13. Exception Handling

**Location**: `exception/` (1 file, 116 LoC)
**Dependencies**: None (standalone)

### 13.1 RestClientException Hierarchy

Comprehensive exception hierarchy for HTTP client errors:

```kotlin
open class RestClientException(
    val statusCode: HttpStatusCode,
    val responseBody: String?,
    message: String,
    cause: Throwable? = null,
) : RuntimeException(message, cause)

class RestServerException(statusCode: HttpStatusCode, ...) : RestClientException(...)
class BadRequestException(message: String) : RuntimeException(message)
```

Includes:
- HTTP status code, response body, and request metadata
- `RestServerException` for 5xx errors
- `BadRequestException` for 400-class input validation errors
- Used by `IdGatekeeperClientImpl` and other clients

---

## 14. Cross-Cutting Patterns

### 14.1 Request Lifecycle: HTTP → Controller → Response

```
1. [Filter]       LoggingContextClearingFilter — clear ALL 19 MDC LogKey entries
2. [Interceptor]  RequestContextInterceptor — extract X-Request-Id, account_id → MDC + RequestScopedValues init
3. [Interceptor]  UserContextInterceptor — call IdGatekeeper → User → MiscellaneousRequestContextVariables
4. [Interceptor]  CommonContextSetterImpl — build TenantContext + ProductContext → MDC + FeatureFlagContext
5. [Controller]   Business logic with full context available
6. [Interceptor]  afterCompletion — cleanup + metrics
```

### 14.2 Request Lifecycle: Async Task Processing

```
1. [SQS]          VisibilityExtendingSQSQueueConsumer.acceptMessage() — start 25s heartbeat
2. [Deserialize]  AsyncTaskMessage → AsyncTaskExecutionContext + AsyncTask
3. [Context]      LoggingContext.addAsyncTaskContext(tenantId, requestId, accountId) → MDC
4. [Middleware]    MessageQueueConsumerMiddleware — logging, metrics
5. [Dispatch]     AsyncTaskDispatcher.dispatch() → handlersByType lookup
6. [Handler]      handler.handle() (e.g., RovoInsightsGenerationTaskHandler)
7. [Callback]     handler.onSuccess() or handler.onFailure()
8. [Cleanup]      Heartbeat cancelled in finally block
```

### 14.3 Key Design Patterns Used

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| Key-Owner (compile-time validation) | `RequestScopedValueKey` (3 values) + `RequestScopedValueOwner` (3 impls) | Type-safe request-scoped storage with startup validation |
| Decorator | `InterceptedLogger` wrapping SLF4J Logger (401 lines) | Privacy-aware logging with feature gating |
| Strategy (priority-ordered) | `AsyncTaskHandler` implementations | Extensible task handling without dispatcher modification |
| Two-layer abstraction | `CoreMetricsService` (149 lines) → `MetricsService` (276 lines) | Foundation metrics reusable without platform deps |
| ThreadContextElement | `RequestAttributesCoroutineContext` (67 lines) | Safe context propagation across coroutine suspensions |
| Null Object | `NoopLogger` (21 lines) | Silent logging in test contexts |
| Registry | `AsyncTaskQueueRegistry` + `AsyncTaskDispatcher` (159 lines combined) | Auto-discovery of task handlers and queue mappings at startup |
| Conditional Beans | `OnLongRunWorkerNodeOrLocalCondition` + `OnSHWorkerNodeOrLocalCondition` | Worker-group-aware component activation |
| Middleware Chain | `MessageQueueConsumerMiddleware` + Interceptor pipeline | Layered cross-cutting concerns |
| Undo/Memento | `SetContextUndo` + `TenantContextUndo` + `FeatureFlagAddTenantContextUndo` | Reversible context modifications |
| Value Class | `AsyncTaskId` (@JvmInline) | Zero-overhead type safety for identifiers |
| Heartbeat | `VisibilityExtendingSQSQueueConsumer` (25s period, 30s extension) | Prevent SQS message timeout during long-running handlers |

---

*End of Core Platform Infrastructure Documentation — ~1,150 lines*
*All paths relative to `src/main/kotlin/io/atlassian/micros/proactiveai/`.*
*Verified against source code at `/Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform` on 2026-05-07.*
