# 05 — Configuration & Testing

**Last Updated:** 2026-05-07
**Owner:** Proactive AI Platform Team
**Service:** `proactive-ai-platform`

---

## Table of Contents

### Part A — Application Configuration
1. [Configuration Overview](#configuration-overview)
2. [application.yml — Base Configuration](#applicationyml--base-configuration)
3. [application-local.yml — Local Development](#application-localyml--local-development)
4. [application-staging.yml — Staging](#application-stagingyml--staging)
5. [application-prod.yml — Production](#application-prodyml--production)
6. [Cross-Environment Diff Table](#cross-environment-diff-table)
7. [SQS Queue Configuration Mapping](#sqs-queue-configuration-mapping)
8. [Logging — logback-spring.xml](#logging--logback-springxml)

### Part B — Test Strategy & Patterns
9. [Test Suite Overview](#test-suite-overview)
10. [ArchUnit — Architectural Constraints](#archunit--architectural-constraints)
11. [Integration Tests (*IT)](#integration-tests-it)
12. [Acceptance Tests (@SpringBootTest)](#acceptance-tests-springboottest)
13. [Unit Tests (MockK + AssertJ)](#unit-tests-mockk--assertj)
14. [Test Utilities](#test-utilities)
15. [Test Coverage Matrix](#test-coverage-matrix)

---

# Part A — Application Configuration

## Configuration Overview

The service uses Spring Boot's profile-based configuration with 4 YAML files. Configuration inheritance follows Spring's standard layering: `application.yml` provides defaults, then profile-specific files override selectively.

| File | Profile | Purpose |
|------|---------|---------|
| `application.yml` | (all) | Base configuration — security, SQS, metrics, egress URLs |
| `application-local.yml` | `local` | Local dev overrides — mock endpoints, devtools, Statsig local mode |
| `application-staging.yml` | `staging` | Staging — real Statsig SDK key |
| `application-prod.yml` | `prod` | Production — real Statsig SDK key |

**Profile activation:** Profiles are activated by the `MICROS_ENVTYPE` environment variable set by the Micros platform (mapped via `micros.environment.type`).

---

## application.yml — Base Configuration

**~90 lines.** Defines all runtime behavior for the service.

### 1. Micros Platform Settings

| Key | Default Value | Purpose |
|-----|---------------|---------|
| `micros.rest.asap.enabled` | `false` | Disable legacy ASAP REST support |
| `micros.rest.asap.client.enabled` | `true` | Enable ASAP client for outbound calls |
| `micros.rest.asap.server.enabled` | `false` | Disable ASAP server-side (use SLAuth instead) |
| `micros.environment.type` | `${MICROS_ENVTYPE}` | Environment type from Micros platform |

### 2. Security — SLAuth

| Key | Value | Purpose |
|-----|-------|---------|
| `micros.security.enabled` | `true` | Enable security globally |
| `micros.security.slauth.poco-enabled` | `true` | Enable POCO policy enforcement |
| `micros.security.slauth.poco.enforce-enabled` | `true` | Enforce POCO policies (not just audit) |
| `micros.security.slauth.default-granted-role` | `access` | Default role granted to authenticated principals |
| `micros.security.slauth.ingress.enabled` | `true` | Enable SLAuth ingress authentication |

### 3. Metrics — Micrometer Histograms

| Key | Value | Purpose |
|-----|-------|---------|
| `micros.metrics.histograms[0].metricName` | `http.server.requests` | HTTP request latency histogram |
| `micros.metrics.histograms[0].boundaries` | `100ms, 500ms, 1s, 2s, 3s, 4s, 5s, 10s, 20s, 120s` | 10 latency buckets |
| `micros.metrics.tags.common` | `environment, environment_type, region, deployment_id` | 4 common metric tags |

### 4. Egress Service URLs

| Key | Env Var Source | Purpose |
|-----|---------------|---------|
| `id-gatekeeper.target-url` | `${MESH_DEPENDENCY_ID_GATEKEEPER_BASE_URL}` | Identity Gatekeeper service URL |
| `ai-gateway.target-url` | `${MESH_DEPENDENCY_AI_GATEWAY_BASE_URL}` | AI Gateway service URL |
| `integrations-service.url` | `${MESH_DEPENDENCY_INTEGRATIONS_SERVICE_BASE_URL}` | Integrations Service URL |
| `integrations-service.endpoint` | `/mcp` | MCP endpoint path |
| `integrations-service.timeout` | `30` | Timeout in seconds |

### 5. Analytics Client

| Key | Value | Purpose |
|-----|-------|---------|
| `analytics-client.product` | `proactive-ai` | Product identifier for analytics events |

### 6. SQS Configuration

| Key | Value | Purpose |
|-----|-------|---------|
| `atlassian.sqs.properties.auto-lifecycle-management-disabled` | `false` | Use SQS lifecycle management from sqs-starter |
| `atlassian.sqs.properties.enable-auto-startup` | `false` | Don't auto-start consumers; wait for Micros lifecycle event |
| `atlassian.sqs.properties.concurrency` | `2-8` | Per-listener thread range (2 idle, scales to 8 under load) |

### 7. Worker Group Queue Bindings

| Key | Env Var Source | Purpose |
|-----|---------------|---------|
| `worker.SHWorkers.analytics_events.name` | `${SQS_ANALYTICS_EVENTS_QUEUE_NAME}` | Analytics events queue name |
| `worker.SHWorkers.analytics_events.url` | `${SQS_ANALYTICS_EVENTS_QUEUE_URL}` | Analytics events queue URL |
| `worker.LongRun.rovo_insights_generation_queue.name` | `${SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_NAME}` | Rovo insights generation queue name |
| `worker.LongRun.rovo_insights_generation_queue.url` | `${SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL}` | Rovo insights generation queue URL |

### 8. SQS Region & Ignore Missing

| Key | Value | Purpose |
|-----|-------|---------|
| `sqs.region` | `${MICROS_AWS_REGION:us-east-1}` | AWS region (default us-east-1) |
| `sqs.ignore-missing-config` | `[analytics_events, rovo_insights_generation_queue]` | Tolerate missing queue config at startup |

### 9. Server

| Key | Value | Purpose |
|-----|-------|---------|
| `server.error.include-message` | `always` | Always include error messages in responses |

### 10. Application Info

| Key | Value | Purpose |
|-----|-------|---------|
| `axe.emit-access-logs` | `false` | Disable access log emission |
| `info.app.name` | `proactive-ai-platform` | Application name for info endpoint |
| `spring.application.name` | `proactive-ai-platform` | Spring application name |

---

## application-local.yml — Local Development

**~16 lines.** Overrides for local development only (profile `local`).

| Key | Value | Purpose |
|-----|-------|---------|
| `server.port` | `8090` | Use 8090 — port 8080 is used by nebulae-proxy |
| `micros.environment.type` | `local` | Hardcode environment to local |
| `spring.devtools.restart.enabled` | `true` | Enable Spring DevTools hot-reload |
| `error.include-stacktrace` | `on-trace-param` | Show stack traces when `trace` param present |
| `statsig.micros-environment-type` | `local` | Statsig local environment |
| `statsig.secret` | `secret-not-a-real-key-...` | Dummy Statsig key (not real) |
| `statsig.local-mode` | `true` | Run Statsig in local/offline mode |
| `id-gatekeeper.target-url` | `${...BASE_URL:http://localhost/}` | Fallback to localhost when not in Nebulae |
| `ai-gateway.target-url` | `${...BASE_URL:http://localhost:8080}` | Fallback to localhost when not in Nebulae |
| `integrations-service.url` | `${...BASE_URL:http://localhost/}` | Fallback to localhost when not in Nebulae |

---

## application-staging.yml — Staging

**3 lines.** Minimal staging overrides.

| Key | Value | Purpose |
|-----|-------|---------|
| `statsig.micros-environment-type` | `staging` | Statsig staging environment |
| `statsig.secret` | `${STATSIG_SDK_KEY:-}` | Real Statsig SDK key from env var |
| `statsig.local-mode` | `false` | Connect to real Statsig service |

---

## application-prod.yml — Production

**3 lines.** Minimal production overrides.

| Key | Value | Purpose |
|-----|-------|---------|
| `statsig.micros-environment-type` | `prod` | Statsig production environment |
| `statsig.secret` | `${STATSIG_SDK_KEY:-}` | Real Statsig SDK key from env var |
| `statsig.local-mode` | `false` | Connect to real Statsig service |

---

## Cross-Environment Diff Table

| Configuration | Local | Staging | Prod |
|--------------|-------|---------|------|
| **Server port** | 8090 | 8080 (default) | 8080 (default) |
| **Environment type** | `local` | `staging` (from MICROS_ENVTYPE) | `prod` (from MICROS_ENVTYPE) |
| **DevTools** | Enabled | Disabled | Disabled |
| **Stack traces** | On trace param | Default | Default |
| **Statsig mode** | Local (offline) | Real (remote) | Real (remote) |
| **Statsig secret** | Dummy key | `${STATSIG_SDK_KEY}` | `${STATSIG_SDK_KEY}` |
| **Egress URLs** | Localhost fallbacks | Mesh dependency URLs | Mesh dependency URLs |
| **SQS queues** | From Nebulae env | From Micros platform | From Micros platform |
| **Log level** | DEBUG | INFO | INFO |
| **Log output** | CONSOLE + JSON_FILE | CONSOLE only | CONSOLE only |
| **SLAuth/POCO** | Enforced (via mock) | Enforced | Enforced |

---

## SQS Queue Configuration Mapping

Shows how SQS queues defined in `service-descriptor.sd.yml` connect to application config:

| Queue (SD) | Visibility | DLQ | Worker Group | Config Key | Env Var (Name) | Env Var (URL) |
|------------|-----------|-----|-------------|------------|----------------|---------------|
| `analytics-events` | 120s | MaxReceive=3 | SHWorkers | `worker.SHWorkers.analytics_events` | `SQS_ANALYTICS_EVENTS_QUEUE_NAME` | `SQS_ANALYTICS_EVENTS_QUEUE_URL` |
| `rovo-insights-generation-queue` | 360s | MaxReceive=2 | LongRun | `worker.LongRun.rovo_insights_generation_queue` | `SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_NAME` | `SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL` |

**Env var naming convention:** Micros auto-generates env vars from `service-descriptor.sd.yml` queue names:
- Queue name `analytics-events` → `SQS_ANALYTICS_EVENTS_QUEUE_URL` / `SQS_ANALYTICS_EVENTS_QUEUE_NAME`
- Queue name `rovo-insights-generation-queue` → `SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL` / `SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_NAME`

**Concurrency:** All queues use `2-8` thread range per listener per JVM. Consumers don't auto-start — they wait for Micros lifecycle events (progressive rollout safety).

---

## Logging — logback-spring.xml

### Structure

```
┌────────────────────────────────────────────────┐
│ Includes: Spring Boot defaults.xml             │
│ Includes: Spring Boot console-appender.xml     │
│                                                │
│ Suppress: autoconfigure logging → WARN         │
│                                                │
│ Root: INFO → CONSOLE (all environments)        │
│                                                │
│ Profile "local | default":                     │
│   Root: DEBUG → CONSOLE                        │
│   Root: DEBUG → JSON_FILE (rolling)            │
└────────────────────────────────────────────────┘
```

### Appenders

| Appender | Type | Environments | Details |
|----------|------|-------------|---------|
| `CONSOLE` | ConsoleAppender | All | Standard Spring Boot console output, INFO level (DEBUG in local) |
| `JSON_FILE` | RollingFileAppender | local/default only | Structured JSON logs to `logs/application.json.log` |

### JSON_FILE Rolling Policy

| Property | Value |
|----------|-------|
| Pattern | `logs/application.json.%d{yyyy-MM-dd}.%i.log.gz` |
| Max File Size | 100MB |
| Max History | 7 days |
| Total Size Cap | 1GB |
| Encoder | LogstashEncoder (structured JSON) |
| Timezone | UTC |
| Timestamp | `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` |
| Caller Data | Excluded (performance) |

### MDC Keys Included

| MDC Key | Purpose |
|---------|---------|
| `traceId` | Distributed trace identifier (OpenTelemetry) |
| `spanId` | Span identifier within a trace |

### Logger Overrides

| Logger | Level | Reason |
|--------|-------|--------|
| `org.springframework.boot.autoconfigure.logging` | WARN | Suppress auto-configuration conditions report |

---

# Part B — Test Strategy & Patterns

## Test Suite Overview

**33 test files** totaling **~6,378 lines of code** across 4 test pattern categories:

| Category | Pattern | Files | Total LoC | Key Annotations |
|----------|---------|-------|-----------|-----------------|
| **Architecture** | ArchUnit constraint checking | 1 | 42 | `@Test` |
| **Integration** | Sandbox HTTP smoke tests | 2 | 132 | `@Test`, `@BeforeAll` |
| **Acceptance** | `@SpringBootTest` with SLAuth | 2 | 226 | `@SpringBootTest`, `@ActiveProfiles("local")` |
| **Unit** | MockK + AssertJ isolated tests | 28 | ~5,978 | `@Test`, `@BeforeEach` |
| **Total** | | **33** | **~6,378** | |

### Test File Inventory

| # | File | LoC | Category | Package |
|---|------|-----|----------|---------|
| 1 | ArchUnitTest.kt | 42 | Architecture | (root) |
| 2 | ExampleTest.kt | 14 | Unit | (root) |
| 3 | HealthCheckIT.kt | 71 | Integration | (root) |
| 4 | RovoInsightsControllerIT.kt | 61 | Integration | (root) |
| 5 | WebServiceAcceptanceTest.kt | 68 | Acceptance | greeting |
| 6 | NudgeThrottleControllerAcceptanceTest.kt | 158 | Acceptance | feature/nudge/api/rest |
| 7 | AsyncIdGatekeeperClientTest.kt | 541 | Unit | client/identity |
| 8 | IdGatekeeperClientTest.kt | 59 | Unit | client/identity |
| 9 | RovoInsightsGenerationSqsQueueConsumerTest.kt | 201 | Unit | feature/rovoinsights/internal |
| 10 | RovoInsightsGenerationTaskHandlerTest.kt | 65 | Unit | feature/rovoinsights |
| 11 | FeatureFlagContextServiceImplTest.kt | 257 | Unit | featuregate |
| 12 | CommonContextSetterTest.kt | 89 | Unit | interceptor |
| 13 | LoggingContextClearingFilterTest.kt | 144 | Unit | interceptor |
| 14 | RequestContextInterceptorTest.kt | 202 | Unit | interceptor |
| 15 | UserContextInterceptorTest.kt | 102 | Unit | interceptor |
| 16 | InterceptedLoggerTest.kt | 552 | Unit | logging |
| 17 | LaasLoggerFactoryTest.kt | 184 | Unit | logging |
| 18 | LaasLoggerTest.kt | 200 | Unit | logging |
| 19 | LoggerExtensionsTest.kt | 287 | Unit | logging |
| 20 | LoggingContextTest.kt | 278 | Unit | logging |
| 21 | NoopLoggerTest.kt | 205 | Unit | logging |
| 22 | WithUGCLoggerTest.kt | 409 | Unit | logging |
| 23 | MiscellaneousRequestContextVariablesServiceTest.kt | 164 | Unit | requestcontext |
| 24 | RequestScopedValuesInitterTest.kt | 114 | Unit | requestcontext |
| 25 | CoreMetricsServiceImplTest.kt | 692 | Unit | service/metric |
| 26 | MetricsServiceImplTest.kt | 550 | Unit | service/metric |
| 27 | AnalyticsEventsMessageQueueConsumerTest.kt | 116 | Unit | sqs |
| 28 | CommonSqsConfigTest.kt | 65 | Unit | sqs |
| 29 | AIGatewayServiceImplTest.kt | 142 | Unit | stratus/internal |
| 30 | AsyncTaskDispatcherTest.kt | 66 | Unit | task |
| 31 | AsyncTaskQueueRegistryTest.kt | 103 | Unit | task |
| 32 | AsyncTaskServiceImplTest.kt | 145 | Unit | task/internal |
| 33 | TestUsers.kt | 32 | Utility | task |

---

## ArchUnit — Architectural Constraints

**File:** `ArchUnitTest.kt` (42 LoC)

### Constraints Enforced

1. **No circular package dependencies** — Ensures the package graph under `io.atlassian.micros.proactiveai` is acyclic.

### How It Works

```
ClassFileImporter (excludes archives, JARs, test classes)
       ↓
Import all classes under ROOT_PACKAGE
       ↓
SoftAssertions: verify at least one class found
       ↓
slices().matching("io.atlassian.micros.proactiveai.(**)").should().beFreeOfCycles()
```

- Uses `ImportOption.Predefined` to exclude archives, JARs, and test classes
- `allowEmptyShould(true)` prevents false failures when packages have no interdependencies
- Runs as a standard JUnit 5 test during `./gradlew test`

---

## Integration Tests (*IT)

**2 files, 132 LoC.** Run against a live Nebulae sandbox via the `intTest` Gradle task.

### Pattern

Integration tests use raw HTTP clients (Apache HttpClient5) to hit the running service. They read connection details from `envs.json` exported by Nebulae.

```
Nebulae sandbox starts (startNebulae task)
       ↓
envs.json exported with MICROS_SERVICE_* vars
       ↓
@BeforeAll reads envs.json → protocol://domainName:port
       ↓
HttpClient sends real HTTP requests to running service
       ↓
Assert HTTP status codes
       ↓
Nebulae stops (stopNebulae task)
```

### HealthCheckIT.kt (71 LoC)
- **Tests:** `serviceStartsInSandboxSuccessfully` — GET `/healthcheck` → expects 200 OK
- **Setup:** `@BeforeAll` reads `./envs.json` for service URL (fallback to localhost:8080)
- **HTTP Client:** Apache HttpClient5 with `setProtocolUpgradeEnabled(false)`

### RovoInsightsControllerIT.kt (61 LoC)
- **Tests:** `statusEndpointReturnsSuccess` — POST `/api/v1/rovo/insights/status` → expects 200 OK
- **Setup:** Same `envs.json` pattern as HealthCheckIT

### Key Characteristics
- Tests are suffixed with `*IT` and excluded from the `test` task, only run by `intTest`
- Depend on Nebulae being started (`dependsOn("startNebulae")`)
- No Spring context — pure HTTP client tests against a running instance
- No JaCoCo coverage — integration tests are excluded from coverage reports

---

## Acceptance Tests (@SpringBootTest)

**2 files, 226 LoC.** Run with a full Spring Boot context in-process.

### Pattern

```kotlin
@ExtendWith(SpringExtension::class)
@ActiveProfiles("local")
@SpringBootTest(
    webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
    properties = ["proactive-ai.sqs.enabled=false"],
)
class SomeAcceptanceTest {
    @Autowired
    private lateinit var restTemplate: TestRestTemplate
    // ... test methods using restTemplate
}
```

### Key Characteristics
- **Profile:** `local` — uses local config overrides
- **SQS disabled:** `proactive-ai.sqs.enabled=false` — no real SQS needed
- **Random port:** Avoids port conflicts
- **TestRestTemplate:** Spring-provided HTTP client for in-process testing

### WebServiceAcceptanceTest.kt (68 LoC)
Tests the `/greetings/charlie` endpoint with 3 scenarios:
1. **Missing auth** → 401 UNAUTHORIZED
2. **Auth present** (X-Slauth-Authorization header) → 200 OK with `"Hello charlie"`
3. **Missing POCO** → 401 UNAUTHORIZED

### NudgeThrottleControllerAcceptanceTest.kt (158 LoC)
Tests the `/api/v1/nudge/throttle` endpoint:
1. **Unauthenticated** → 401 UNAUTHORIZED
2. **Authenticated POST** → 200 OK with NudgeThrottleResponse
3. **Parameterized tests** (`@ParameterizedTest @EnumSource`) across all NudgeType values

---

## Unit Tests (MockK + AssertJ)

**28 files, ~5,978 LoC.** The dominant test pattern.

### Standard Structure

```kotlin
class SomeServiceTest {
    // 1. Declare mocks
    private val dependency1 = mockk<Dependency1>()
    private val metricsService = mockk<MetricsService>(relaxed = true)

    // 2. System under test
    private lateinit var sut: SomeService

    // 3. Setup
    @BeforeEach
    fun setUp() {
        sut = SomeService(dependency1, metricsService)
    }

    // 4. Test with descriptive name
    @Test
    fun `should do something when condition met`() {
        // Arrange
        every { dependency1.doSomething() } returns expected
        // Act
        val result = sut.invoke()
        // Assert
        assertThat(result).isEqualTo(expected)
        verify { dependency1.doSomething() }
    }
}
```

### MockK Patterns Used

| Pattern | Usage | Example |
|---------|-------|---------|
| `mockk<T>()` | Strict mock (fails on unexpected calls) | `mockk<IdGatekeeperClient>()` |
| `mockk<T>(relaxed = true)` | Lenient mock (returns defaults) | `mockk<MetricsService>(relaxed = true)` |
| `every { ... } returns value` | Stub return value | `every { client.getUser(id) } returns user` |
| `every { ... } just runs` | Stub void function | `every { handler.handle(event) } just runs` |
| `every { ... } throws ex` | Stub exception | `every { client.call() } throws IOException()` |
| `coEvery { ... }` | Stub suspend function | `coEvery { handler.handle(ctx, task) } returns result` |
| `verify { ... }` | Verify invocation | `verify { metricsService.count(MetricKey.X) }` |
| `coVerify { ... }` | Verify suspend function | `coVerify(exactly = 1) { handler.handle(ctx, task) }` |

### Assertion Patterns (AssertJ)

| Pattern | Example |
|---------|---------|
| `assertThat(x).isEqualTo(y)` | Value equality |
| `assertThat(x).isNotNull()` | Null check |
| `assertThat(x).hasFieldOrPropertyWithValue(...)` | Object property check |
| `assertThatThrownBy { ... }.isInstanceOf(...)` | Exception assertion |
| `assertThrows<T> { ... }` | JUnit 5 exception assertion |

### Coroutine Testing

Tests for async code use `kotlinx-coroutines-test`:
```kotlin
@Test
fun `dispatch invokes handler and onSuccess`() = runTest {
    val handler = mockk<TaskHandler>(relaxed = true)
    coEvery { handler.handle(any(), any()) } returns result
    dispatcher.dispatch(ctx, task)
    coVerify(exactly = 1) { handler.handle(ctx, task) }
}
```

### Largest Unit Test Files

| File | LoC | What It Tests |
|------|-----|--------------|
| CoreMetricsServiceImplTest.kt | 692 | Micrometer counter, timer, gauge, distribution summary operations |
| InterceptedLoggerTest.kt | 552 | Logger interception/decoration for all log levels + markers |
| MetricsServiceImplTest.kt | 550 | High-level metrics service wrapper with tags, timing, error counting |
| AsyncIdGatekeeperClientTest.kt | 541 | Async identity gatekeeper client with WireMock HTTP stubs |
| WithUGCLoggerTest.kt | 409 | UGC-safe logger that redacts user-generated content |

---

## Test Utilities

### TestUsers.kt (32 LoC)

Factory function for creating stubbed `User` objects in tests:

```kotlin
internal fun testUser(
    accountId: String = "user-1",
    userContextHeaderValue: String = "uct-test-token",
    orgId: String? = null,
): User
```

- Provides meaningful defaults so test bodies stay focused on behavior
- Returns an anonymous `User` implementation with:
  - `AccountId.of(accountId)`
  - Configurable UCT header value
  - Optional org ID
  - Null-returning `ExtraContext` (forwarded-for, geo, forwarded-host)

### ExampleTest.kt (14 LoC)

Minimal scaffold test verifying two strings are not equal. Serves as a template for new tests.

---

## Test Coverage Matrix

Coverage analysis of source packages vs. test files:

| Source Package | Test File(s) | Test LoC | Coverage Status |
|---------------|-------------|----------|-----------------|
| `(root)` | ArchUnitTest, ExampleTest, HealthCheckIT, RovoInsightsControllerIT | 188 | ✅ Covered |
| `client/identity` | AsyncIdGatekeeperClientTest, IdGatekeeperClientTest | 600 | ✅ Covered |
| `client/identity/internal` | — | — | ⚠️ No direct tests |
| `config` | — | — | ⚠️ No direct tests |
| `context` | — | — | ⚠️ No direct tests |
| `exception` | — | — | ⚠️ No direct tests |
| `feature/nudge/api/rest` | NudgeThrottleControllerAcceptanceTest | 158 | ✅ Covered |
| `feature/nudge/api/domain` | — | — | ⚠️ No direct tests |
| `feature/nudge/api/dto` | — | — | ⚠️ No direct tests (DTOs) |
| `feature/rovoinsights` | RovoInsightsGenerationTaskHandlerTest | 65 | ✅ Covered |
| `feature/rovoinsights/internal` | RovoInsightsGenerationSqsQueueConsumerTest | 201 | ✅ Covered |
| `feature/rovoinsights/api/rest` | — | — | ⚠️ No direct tests |
| `feature/rovoinsights/api/dto` | — | — | ⚠️ No direct tests (DTOs) |
| `feature/rovoinsights/api/fetch` | — | — | ⚠️ No direct tests |
| `feature/rovoinsights/api/status` | — | — | ⚠️ No direct tests |
| `feature/rovoinsights/system` | — | — | ⚠️ No direct tests |
| `featuregate` | FeatureFlagContextServiceImplTest | 257 | ✅ Covered |
| `featuregate/internal` | — | — | ⚠️ No direct tests |
| `greeting` | WebServiceAcceptanceTest | 68 | ✅ Covered |
| `interceptor` | CommonContextSetterTest, LoggingContextClearingFilterTest, RequestContextInterceptorTest, UserContextInterceptorTest | 537 | ✅ Covered |
| `interceptor/internal` | — | — | ⚠️ No direct tests |
| `logging` | InterceptedLoggerTest, LaasLoggerFactoryTest, LaasLoggerTest, LoggerExtensionsTest, LoggingContextTest, NoopLoggerTest, WithUGCLoggerTest | 2,115 | ✅ Covered (strongest) |
| `requestcontext` | MiscellaneousRequestContextVariablesServiceTest, RequestScopedValuesInitterTest | 278 | ✅ Covered |
| `requestcontext/internal` | — | — | ⚠️ No direct tests |
| `service/metric` | CoreMetricsServiceImplTest, MetricsServiceImplTest | 1,242 | ✅ Covered |
| `service/metric/internal` | — | — | ⚠️ No direct tests |
| `sqs` | AnalyticsEventsMessageQueueConsumerTest, CommonSqsConfigTest | 181 | ✅ Covered |
| `stratus/internal` | AIGatewayServiceImplTest | 142 | ✅ Covered |
| `stratus` | — | — | ⚠️ No direct tests |
| `task` | AsyncTaskDispatcherTest, AsyncTaskQueueRegistryTest, TestUsers | 201 | ✅ Covered |
| `task/internal` | AsyncTaskServiceImplTest | 145 | ✅ Covered |
| `utility` | — | — | ⚠️ No direct tests |
| `utility/tenant` | — | — | ⚠️ No direct tests |
| `utility/threading` | — | — | ⚠️ No direct tests |
| `utility/user` | — | — | ⚠️ No direct tests |
| `utility/user/internal` | — | — | ⚠️ No direct tests |

### Coverage Summary

| Metric | Value |
|--------|-------|
| Total source packages | 37 |
| Packages with direct tests | 16 (43%) |
| Packages without direct tests | 21 (57%) |
| Total test LoC | ~6,378 |
| Strongest coverage | `logging` (7 test files, 2,115 LoC) |
| Second strongest | `service/metric` (2 test files, 1,242 LoC) |
| Untested categories | config, context, exception, DTOs, utility, some internal packages |

**Note:** Packages without direct tests may still have indirect coverage through acceptance and integration tests (e.g., `config` is exercised by `@SpringBootTest` acceptance tests). The `internal` sub-packages typically contain implementations tested through their public-facing parent package tests. DTO and domain packages often contain simple data classes that don't require dedicated tests.

---

*Auto-generated on 2026-05-07 from repository source files.*
