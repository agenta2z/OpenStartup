# 01 — Architecture Overview: Proactive AI Platform

> **Purpose**: Landing page for engineers new to the `proactive-ai-platform` codebase.  
> **Audience**: New team members, on-call engineers, AI agents.  
> **Last verified**: 2026-05-07  
> **Source repo**: `/Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform`

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Technology Stack](#2-technology-stack)
3. [Repository Layout](#3-repository-layout)
4. [Application Bootstrap](#4-application-bootstrap)
5. [Worker Group Topology](#5-worker-group-topology)
6. [Module-by-Module Summary](#6-module-by-module-summary)
7. [Internal Module Dependency Graph](#7-internal-module-dependency-graph)
8. [External Service Dependencies](#8-external-service-dependencies)
9. [Key Architectural Invariants](#9-key-architectural-invariants)
10. [Reading Guide & Further Documentation](#10-reading-guide--further-documentation)

---

## 1. What Is This Project?

`proactive-ai-platform` (PAI) is a **Kotlin Spring Boot microservice** deployed on **Atlassian Micros** that powers the *proactive AI experiences* layer across Atlassian products (Jira, Confluence, Rovo). It is owned by the Engineering-AI team (Slack: `#help-ai-experience`).

### What It Does

PAI serves as the backend orchestration layer for three categories of proactive AI features:

| Feature | Endpoint | Behavior |
|---------|----------|----------|
| **Rovo Insights** | `POST /api/v1/rovo-insights/generate` | Accepts a workspace context, returns a `taskId` (HTTP 202), then asynchronously generates AI-powered insights via SQS worker + AI Gateway. Polling via `/status` and `/fetch`. |
| **Nudge Throttling** | `POST /api/v1/nudge/throttle` | Synchronous throttle decision for proactive notifications. Returns `{score, throttled}`. Currently returns hardcoded `score=10, throttled=false`; real throttling (TAP traits, GASv3) is planned. |
| **Greeting (Template)** | `GET /greetings/{name}` | Example/template controller kept as a working reference for new feature authors. |

### What Makes It Different from a Generic Spring Boot Service

- **JVM async end-to-end**: Kotlin coroutines + Reactor mixed throughout, with `InstrumentedDispatcher` for observability.
- **Two runtime topologies in one JAR**: `WebServer` (handles HTTP) and `LongRun` (drains SQS queues), selected by env var `MICROS_GROUP`. A third group, `SHWorkers`, handles StreamHub analytics events.
- **No direct LLM access**: All model inference routes through Atlassian's **AI Gateway** via the **Stratus SDK** — direct OpenAI/Anthropic SDK usage is forbidden.
- **4-stage HTTP middleware pipeline**: Every request crosses `LoggingContextClearingFilter` → `RequestContextInterceptor` → `UserContextInterceptor` → `CommonContextSetterImpl` before reaching a controller.

### Quick Stats

| Metric | Value |
|--------|-------|
| Source files (main) | 118 `.kt` files |
| Source files (test) | 33 `.kt` files |
| Total main LoC | ~7,833 |
| Total test LoC | ~6,378 |
| Test/main LoC ratio | 0.81× |
| Packages | 15 top-level (3 feature + 12 platform) |
| Spring components (all stereotypes) | ~50 annotations in 43 files (+12 @Bean) |
| Controllers | 5 |
| Async task handlers | 1 |
| Enums | 23 |
| Service tier | Tier 3 (Micros) |

---

## 2. Technology Stack

Derived from `build.gradle.kts`, `settings.gradle.kts`, and `service-descriptor.sd.yml`.

### Core Platform

| Concern | Technology | Version / Detail |
|---------|-----------|-----------------|
| **Language** | Kotlin | 2.3.20 (JVM target 21) |
| **JDK** | OpenJDK | 21 (Docker base: `micros-java-21:1.5.0`) |
| **Build system** | Gradle with Kotlin DSL | Gradle 9.4.1 (`build.gradle.kts` + `settings.gradle.kts`) |
| **Framework** | Spring Boot via Micros | `io.atlassian.micros.springboot:7.10.0` plugin |
| **HTTP layer** | Spring MVC | `micros-spring-boot-starter-rest-spring-mvc` |
| **Authentication** | SLAuth (service-to-service JWT) | `micros-spring-boot-starter-security-slauth-server` |
| **Authorization** | POCO (policy-based) | Enforced via `poco-enabled: true` in `application.yml` |

### Async & Reactive

| Concern | Technology | Version |
|---------|-----------|---------|
| **Coroutines** | `kotlinx-coroutines-core` | 1.10.2 |
| **Coroutine SLF4J bridge** | `kotlinx-coroutines-slf4j` | 1.10.2 (MDC propagation across coroutines) |
| **Coroutine Reactor bridge** | `kotlinx-coroutines-reactor` | 1.10.2 |
| **OpenTelemetry Kotlin** | `opentelemetry-extension-kotlin` | 1.61.0 |

### Observability & Feature Flags

| Concern | Technology | Version |
|---------|-----------|---------|
| **Metrics** | Micrometer → SignalFx | `micrometer-bom:1.16.4` |
| **Feature flags** | Statsig | `featuregate-client-starter:10.4.0` |
| **Logging** | SLF4J + Logback + LaasLogger | Custom MDC wrapper in `logging/` package |
| **Analytics** | Atlassian Analytics | `analytics-spring-boot:7.1.0` |

### Data & Messaging

| Concern | Technology | Detail |
|---------|-----------|--------|
| **Cache** | Redis (Valkey 7.x) | `cache.t4g.small`, single primary + 1 replica, transit encryption enabled |
| **Messaging** | AWS SQS | `sqs-queues-starter-aws-sdkv2:9.24.5` with DLQ actuator |
| **Serialization** | Jackson Kotlin | `jackson-module-kotlin:2.21.3` |

### AI Integration

| Concern | Technology | Detail |
|---------|-----------|--------|
| **LLM client** | Stratus SDK | Routes through AI Gateway via `UnifiedLlmProvider` |
| **Agent framework** | ADK Extensions | `adk-extensions-java:1.0.0` |
| **MCP integration** | Integrations Service | MCP sessions for tool provisioning to Stratus agents |
| **Tenant context** | TCS Client | `tcs-client-starter:10.4.0` |
| **Sharding** | PaaS Sharding | `paas-sharding-context-java:2.0.7` |

### Quality & Testing

| Concern | Technology | Version |
|---------|-----------|---------|
| **Unit testing** | JUnit 5 + MockK | `mockk:1.14.9` |
| **Integration testing** | WireMock | `wiremock-standalone:3.13.2` |
| **Assertions** | AssertJ | `assertj-core:3.27.7` |
| **Architecture tests** | ArchUnit | `archunit:1.4.1` |
| **Coverage** | JaCoCo | `0.8.14` |
| **Lint** | ktlint | `ktlint-gradle:14.2.0` |
| **Static analysis** | Detekt + SonarQube | Configured via `sonar-project.properties` |
| **HTTP test client** | Apache HttpClient 5 | `httpclient5:5.6` |

### Gradle Plugins

| Plugin | Version | Purpose |
|--------|---------|---------|
| `io.atlassian.micros.springboot` | 7.10.0 | Micros Spring Boot integration (starters, packaging) |
| `com.atlassian.gradle.plugins.revealer` | 18.1.0 | Dependency visibility and analysis |
| `io.spring.dependency-management` | 1.1.7 | BOM-based dependency version management |
| `org.jlleitschuh.gradle.ktlint` | 14.2.0 | Kotlin code style linter |
| `kotlin("jvm")` | 2.3.20 | Kotlin JVM compilation |
| `kotlin("plugin.spring")` | 2.3.20 | Makes Spring-annotated classes `open` |
| `jacoco` | 0.8.14 | Code coverage reporting |

---

## 3. Repository Layout

The repository is a **single-module Gradle project** (no multi-module subprojects). All source lives under one `src/` tree.

```
proactive-ai-platform/
├── build.gradle.kts                    # Single-module Gradle build (all deps, tasks, plugins)
├── settings.gradle.kts                 # Kotlin 2.3.20 plugin versions, rootProject name
├── gradle.properties                   # Gradle daemon settings
├── gradlew / gradlew.bat              # Gradle wrapper scripts
│
├── service-descriptor.sd.yml           # Micros service descriptor: worker groups, resources
│                                       #   (Redis, SQS queues), alarms, scaling, egress deps
├── component-descriptor.yml            # Compass catalog metadata (tier 3, Java 21)
├── project-descriptor.yml              # Build commands for Docker image creation
├── nebulae.yml                         # Nebulae local dev environment config
├── default-pipelines.spinnaker.yaml    # Spinnaker deployment pipeline definition
├── bitbucket-pipelines.yml             # CI pipeline (build, test, quality gates, deploy)
├── canary-config.yml                   # Canary deployment rules
├── service-proxy-alias-descriptor.yml  # Service mesh proxy aliases
├── renovate.json5                      # Automated dependency update config
├── sonar-project.properties            # SonarQube analysis settings
├── checkstyle.xml                      # Java/Kotlin checkstyle rules
├── open-rewrite.gradle                 # OpenRewrite automated refactoring
├── Dockerfile                          # FROM micros-java-21:1.5.0, copies fat JAR
│
├── src/
│   ├── main/
│   │   ├── kotlin/io/atlassian/micros/proactiveai/
│   │   │   ├── Application.kt              # Spring Boot entry point (@SpringBootApplication)
│   │   │   ├── client/                      # HTTP client commons + IdGatekeeper integration
│   │   │   ├── config/                      # Spring beans: WebMVC, security, async executor
│   │   │   ├── context/                     # Domain models: TenantContext, ProductContext, Experience
│   │   │   ├── exception/                   # REST client exception hierarchy
│   │   │   ├── feature/
│   │   │   │   ├── greeting/                # Template/example feature
│   │   │   │   ├── nudge/                   # Throttle decision API
│   │   │   │   └── rovoinsights/            # Async insight generation (largest feature)
│   │   │   ├── featuregate/                 # Statsig feature flags wrapper
│   │   │   ├── interceptor/                 # HTTP interceptor chain (4-stage pipeline)
│   │   │   ├── logging/                     # LaasLogger (SLF4J + MDC context wrapper)
│   │   │   ├── requestcontext/              # Request-scoped values + MDC helpers
│   │   │   ├── service/metric/              # Micrometer-based metrics API
│   │   │   ├── sqs/                         # SQS consumer middleware + StreamHub events
│   │   │   ├── stratus/                     # AI Gateway / Stratus SDK integration
│   │   │   ├── task/                        # Async-task envelope framework
│   │   │   └── utility/                     # Threading, user model, tenant helpers
│   │   └── resources/
│   │       ├── application.yml              # SQS queues, metrics config, worker group routing
│   │       ├── policies/service/policy.json # POCO authorization policy
│   │       └── logback-spring.xml           # Log appenders config
│   └── test/kotlin/…                        # 33 test files mirroring main packages
│
├── docs/                               # Operational documentation (16 files)
│   ├── micros.md                       # Micros deployment guide
│   ├── slauth.md                       # SLAuth authentication setup
│   ├── sonarqube.md                    # SonarQube integration
│   ├── spinnaker.md                    # Spinnaker pipeline docs
│   ├── poco.md                         # POCO policy authoring
│   ├── nebulae.md                      # Local dev with Nebulae
│   ├── bitbucket-pipelines.md          # CI pipeline reference
│   ├── security-checklist.md           # ProdSec checklist
│   └── … (8 more operational guides)
│
├── streamhub/                          # StreamHub event-schema configuration
│   ├── shipyard-specs/                 # Event schema definitions
│   └── subscriptions/                  # SQS subscription mappings
│
├── bin/                                # Operational scripts (11 files)
│   ├── build-include.sh               # Build helper
│   ├── manual-deploy.sh               # Manual deployment
│   ├── poco-policy-upload.sh           # POCO policy management
│   ├── spinnaker-deploy.sh             # Spinnaker deployment trigger
│   ├── get-deployment-access.sh        # Access provisioning
│   └── … (6 more scripts)
│
└── .ai_employee/                       # AI assistant config
    .rovodev/                           # Rovo Dev agent config
```

### Key Observations

- **Single module**: Unlike many Atlassian services, PAI uses a flat single-module Gradle layout — no `:core`, `:api`, `:worker` subprojects. All 15 packages live under one `src/main`.
- **Config-as-code**: The repo contains 8+ descriptor/config files at the root level that define deployment, CI, security, and service mesh behavior.
- **`docs/` is operational**: The `docs/` directory contains deployment and tooling guides, not feature documentation. Feature/architecture docs are maintained separately.
- **`streamhub/` for events**: StreamHub integration uses a declarative subscription model — event schemas in `shipyard-specs/` are mapped to SQS queues via `subscriptions/`.

---

## 4. Application Bootstrap

### Entry Point: `Application.kt`

The application starts from a minimal 14-line entry point:

```kotlin
package io.atlassian.micros.proactiveai

@SpringBootApplication
class Application {
    companion object {
        @JvmStatic
        fun main(args: Array<String>) {
            SpringApplication.run(Application::class.java)
        }
    }
}
```

### Bootstrap Sequence

1. **`SpringApplication.run()`** triggers Spring Boot auto-configuration via classpath starters.
2. **Micros starters** (`micros-spring-boot-starter-base`, `-rest-spring-mvc`, `-security-slauth-server`, `-lifecycle`) register health checks, SLAuth filters, and lifecycle hooks.
3. **`config/WebMvcConfiguration.kt`** registers the HTTP interceptor chain:
   - `RequestContextInterceptor` (order 1): Extracts `tenant_id`, `request_id`, `account_id` from headers into MDC.
   - `UserContextInterceptor` (order 2): Calls IdGatekeeper to enrich user context.
   - `CommonContextSetterImpl` (order 3): Sets `TenantContext` and `ProductContext` in `RequestScopedValue`.
4. **`config/MvcSecurityConfig.kt`** enables SLAuth (JWT-based service-to-service auth) and POCO (policy-based authorization).
5. **`config/ThreadConfig.kt`** creates the `InstrumentedDispatcher` — a custom coroutine dispatcher wrapping a thread pool with Micrometer instrumentation.
6. **SQS auto-configuration** wires queue consumers based on `MICROS_GROUP` env var:
   - `SHWorkers` group → `AnalyticsEventsMessageQueueConsumer`
   - `LongRun` group → `RovoInsightsGenerationSqsQueueConsumer`
7. **Statsig** initializes via `featuregate-client-starter` for feature flag evaluation.
8. **Lifecycle events** use SQS-based delivery (`source: queue` in service descriptor) to coordinate progressive rollouts.

### How the Worker Group is Determined

The env var `MICROS_GROUP` controls which runtime topology the JVM runs:

```
MICROS_GROUP=WebServer  → HTTP server mode (Spring MVC, interceptors, REST controllers)
MICROS_GROUP=SHWorkers  → StreamHub analytics event consumer
MICROS_GROUP=LongRun    → Async task SQS consumer (Rovo Insights generation)
```

All three topologies share the same JAR and Spring context — the `WorkerNodeDetector` bean (in `config/`) inspects `MICROS_GROUP` to conditionally enable/disable components.

---

## 5. Worker Group Topology

PAI deploys as three distinct worker groups from the same Docker image. This is defined in `service-descriptor.sd.yml` under the `workerGroups` key.

### Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │          proactive-ai-platform JAR          │
                    │   (single Docker image, three topologies)   │
                    └─────────────────────────────────────────────┘
                                        │
              ┌─────────────────────────┼──────────────────────────┐
              ▼                         ▼                          ▼
   ┌──────────────────┐    ┌──────────────────┐     ┌──────────────────┐
   │   WebServer       │    │   SHWorkers       │     │   LongRun        │
   │                   │    │                   │     │                  │
   │ • HTTP endpoints  │    │ • StreamHub       │     │ • Async tasks    │
   │ • REST controllers│    │   analytics event │     │ • Rovo Insights  │
   │ • Interceptor     │    │   consumption     │     │   generation     │
   │   pipeline        │    │ • SQS queue:      │     │ • SQS queue:     │
   │ • Sync features   │    │   analytics_events│     │   rovo_insights_ │
   │   (nudge, greet)  │    │                   │     │   generation_    │
   │ • Async task      │    │                   │     │   queue          │
   │   submission      │    │                   │     │                  │
   │   (→ SQS enqueue) │    │                   │     │ • AI Gateway     │
   │                   │    │                   │     │   calls via      │
   │ Scale: 2–4        │    │ Scale: 1–2        │     │   Stratus SDK    │
   │ Instance: t3a.med │    │ Instance: t3a.med │     │                  │
   └──────────────────┘    └──────────────────┘     │ Scale: 1–2       │
                                                     │ Instance: t3a.med│
                                                     └──────────────────┘
```

### Worker Group Details

| Group | `MICROS_GROUP` | Scaling (min–max) | Instance | Purpose |
|-------|-------------------|-------------------|----------|---------|
| **WebServer** | `WebServer` | 2–4 | `t3a.medium` | Serves HTTP traffic. Runs Spring MVC with interceptor chain. Handles sync features (nudge, greeting) and submits async tasks to SQS. Exposes health/deep check on port 8080. |
| **SHWorkers** | `SHWorkers` | 1–2 | `t3a.medium` | Consumes StreamHub analytics events from the `analytics_events` SQS queue. Processes usage/action events for proactive AI signal ingestion. |
| **LongRun** | `LongRun` | 1–2 | `t3a.medium` | Drains the `rovo_insights_generation_queue` SQS queue. Runs `AsyncTaskDispatcher` → `RovoInsightsGenerationTaskHandler`. Makes long-running AI Gateway calls (up to 600s timeout). |

### SQS Queue Configuration (from `application.yml`)

```yaml
worker:
  SHWorkers:
    analytics_events:
      name: ${SQS_ANALYTICS_EVENTS_QUEUE_NAME}
      url: ${SQS_ANALYTICS_EVENTS_QUEUE_URL}
  LongRun:
    rovo_insights_generation_queue:
      name: ${SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_NAME}
      url: ${SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL}
```

- **Concurrency**: `2-8` threads per queue per JVM (auto-scales based on queue depth).
- **Visibility timeout**: 120s (`analytics_events`) / 360s (`rovo_insights_generation_queue`) — SQS-level, with in-application visibility extension for long-running tasks.
- **DLQ**: Automatic after failed receive attempts (`MaxReceiveCount: 3` for analytics_events, `2` for rovo_insights_generation_queue).
- **Message retention**: 1 hour (3600s).
- **Lifecycle**: `auto-lifecycle-management-disabled: false` — Micros lifecycle events coordinate consumer startup during progressive rollouts.

### Request Flow: WebServer → LongRun

```
Client (Jira/Confluence) 
  → HTTP POST /api/v1/rovo-insights/generate
  → [WebServer] Controller extracts DTO + User
  → [WebServer] AsyncTaskService.submit() serializes task envelope to JSON
  → [WebServer] SQS SendMessage to rovo_insights_generation_queue
  → HTTP 202 {taskId} returned immediately

  … (async, on LongRun JVM) …

  → [LongRun] SQS consumer receives message
  → [LongRun] AsyncTaskDispatcher routes by task type
  → [LongRun] RovoInsightsGenerationTaskHandler.handle()
  → [LongRun] Stratus SDK → AI Gateway → LLM inference
  → [LongRun] Result cached/stored
  → Client polls /status and /fetch
```

---

## 6. Module-by-Module Summary

All Kotlin files live under `io.atlassian.micros.proactiveai.<package>`. The table below covers every package, ranked by file count (descending), with verified file counts and line counts.

### Feature Packages (3 packages — user-facing business logic)

| Package | Files | LoC | Test Files | Status | Purpose |
|---------|-------|-----|------------|--------|---------|
| `feature/rovoinsights` | 16 | 658 | 2 | **Active** | Async AI-powered insight generation for Jira/Confluence workspaces. Largest feature package. Contains REST controller (`/api/v1/rovo-insights/*`), DTOs, task handler, SQS queue consumer, and internal orchestration. Subpackages: `api/` (controller, DTOs, fetch, status), `internal/` (SQS consumer), `system/` (task handler, service). |
| `feature/nudge` | 4 | 72 | 1 | Stable | Nudge throttle decision endpoint (`POST /api/v1/nudge/throttle`). Synchronous — no SQS. Currently returns hardcoded `{score: 10, throttled: false}`. Subpackages: `api/domain/`, `api/dto/`, `api/rest/`. |
| `feature/greeting` | 1 | 56 | 1 | Stable | Template/example feature (`GET /greetings/{name}`). Returns a `SampleResponse`. Kept as a reference implementation for new feature authors. |

### Platform Packages (12 packages — shared infrastructure)

| Package | Files | LoC | Test Files | Status | Purpose |
|---------|-------|-----|------------|--------|---------|
| `requestcontext` | 14 | 906 | 2 | Stable | Request-scoped MDC state management. `RequestScopedValue<T>` generic container, logging context builder, header constant definitions, MDC helpers. Subpackages: `internal/` (3 files, 382 LoC). The backbone of the identity-context system. |
| `service/metric` | 5 | 1,243 | 2 | Stable | Micrometer + SignalFx metrics API. `MetricKey` enum of all metric names, `HistogramMetric` for latency tracking, `ResultMetricBase` for success/error counters, `Status` enum (SUCCESS, ERROR, TIMEOUT, RATE_LIMITED). Highest LoC of any platform package. Subpackages: `internal/` (2 files, 794 LoC). |
| `featuregate` | 8 | 754 | 1 | Stable | Statsig feature flag wrapper. `AiFeatureGates` enum of all feature flags, `FeatureService.checkGate(gate, defaultValue)` enforces mandatory defaults at call site. Dynamic config support for runtime parameters. Subpackages: `internal/` (2 files, 506 LoC). |
| `task` | 11 | 649 | 4 | **Active** | Async-task envelope framework. `AsyncTaskService` serializes task objects to JSON and sends to SQS. `AsyncTaskDispatcher` routes received messages by task type to the correct `AsyncTaskHandler`. `VisibilityExtendingConsumer` extends SQS visibility for long-running tasks. Subpackages: `internal/` (5 files, 376 LoC). |
| `stratus` | 8 | 587 | 1 | **Active** | AI Gateway / Stratus SDK integration. `AIGatewayService` orchestrates LLM calls, `IntegrationServiceMcpSessionManager` creates per-request MCP sessions, `IntegrationServiceToolProvider` provisions tools based on tenant/product context. `AIGatewayClientConfiguration` wires the `UnifiedLlmProvider`. Subpackages: `internal/` (1 file, 120 LoC). |
| `logging` | 6 | 568 | 7 | Stable | SLF4J + MDC logging wrapper. `LaasLogger` and `LaasLoggerFactory` provide structured logging with automatic MDC enrichment. `InterceptedLogger` for log interception, `WithUGCLogger` for UGC-flagged logging, `NoopLogger` for testing. Best-tested package (7 test files, 1.17 test/main ratio). |
| `utility` | 8 | 557 | 0 | Stable | Threading, user model, and tenant utilities. `utility/threading/` (5 files, 454 LoC): `RequestAttributesCoroutineContext`, `InstrumentedDispatcher`, `CoroutineMonitor`, `DispatcherMonitor`. `utility/user/` (2 files, 89 LoC): `User` interface + `UserImpl`. `utility/tenant/` (1 file, 14 LoC): `TcsService` stub. |
| `client` | 7 | 399 | 2 | Stable | HTTP client commons + IdGatekeeper integration. `client/identity/` (5 files, 373 LoC): `IdGatekeeperClient` (sync) and `AsyncIdGatekeeperClient` (async) for user identity lookups. `client/` root (2 files, 26 LoC): shared HTTP client configuration. |
| `context` | 9 | 381 | 0 | Stable | Domain context models. `TenantContext`, `ProductContext`, `Experience` enum (7 Atlassian products), interface hierarchy for request context. Foundation types used by nearly every other package. |
| `sqs` | 8 | 302 | 2 | Stable | SQS consumer middleware + StreamHub event consumption. `AnalyticsEventsMessageQueueConsumer` processes StreamHub analytics events. `CommonSqsConfig` provides shared SQS configuration. Message attribute extraction for MDC replay on worker threads. |
| `interceptor` | 5 | 295 | 4 | Stable | HTTP request interceptor chain. `LoggingContextClearingFilter` (setup/teardown MDC), `RequestContextInterceptor` (extract identity from headers), `UserContextInterceptor` (call IdGatekeeper), `CommonContextSetterImpl` (set domain context). Executed in order 1→2→3 on every HTTP request. |
| `config` | 6 | 208 | 0 | Stable | Spring configuration beans. `WebMvcConfiguration` (interceptor registration), `MvcSecurityConfig` (SLAuth + POCO), `ThreadConfig` (instrumented dispatcher), `WorkerNodeDetector` (MICROS_GROUP inspection), environment config. |
| `exception` | 1 | 116 | 0 | Stable | REST client exception types. `RestClientException` hierarchy with typed error variants for downstream service call failures. |

### Root Level

| File | LoC | Test Files | Purpose |
|------|-----|------------|---------|
| `Application.kt` | 14 | 4 (root-level) | Spring Boot entry point. Root-level tests: `ArchUnitTest`, `ExampleTest`, `HealthCheckIT`, `RovoInsightsControllerIT`. |

### Totals

| Layer | Files | LoC (≈) | Notes |
|-------|-------|---------|-------|
| **Features** (3 packages) | 21 | 786 | rovoinsights dominates (16 files, 658 LoC) |
| **Platform** (12 packages) | 97 | 6,965 | service/metric is largest by LoC (1,243) |
| **Root** | 1 | 14 | Application.kt |
| **Tests** | 33 | ~6,400 | 0.81× test/main ratio |
| **TOTAL** | **152** | **14,078** | 118 main + 33 test + 1 root |

---

## 7. Internal Module Dependency Graph

The dependency graph follows a strict **layered architecture** — feature packages depend on platform packages, but never the reverse. Platform packages form a DAG with `logging` and `context` as leaf nodes.

### Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FEATURE LAYER (consumers)                     │
│                                                                  │
│  ┌──────────────────┐  ┌────────────┐  ┌───────────────────┐    │
│  │  rovoinsights     │  │   nudge    │  │     greeting      │    │
│  │  (16 files)       │  │  (4 files) │  │    (1 file)       │    │
│  └────────┬──────────┘  └─────┬──────┘  └───────────────────┘    │
│           │                   │                                   │
│   depends on:          depends on:                                │
│   requestcontext       featuregate                                │
│   task                 requestcontext                             │
│   sqs                  logging                                    │
│   logging              context                                    │
│   service/metric                                                  │
│   featuregate                                                     │
│   stratus                                                         │
│   client                                                          │
│   context                                                         │
│   utility                                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PLATFORM LAYER (providers)                     │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │   task    │  │  stratus │  │interceptor│  │   config     │    │
│  │(11 files) │  │ (8 files)│  │ (5 files) │  │  (6 files)   │    │
│  └────┬─────┘  └────┬─────┘  └────┬──────┘  └──────┬───────┘    │
│       │              │             │                │             │
│   sqs            client        requestcontext    logging         │
│   requestcontext utility/user  logging           requestcontext  │
│   logging        context       featuregate                       │
│                                context                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │requestcontext│  │service/metric│  │  featuregate  │           │
│  │ (14 files)   │  │  (5 files)   │  │   (8 files)   │           │
│  └────┬─────────┘  └────┬─────────┘  └────┬──────────┘           │
│       │                  │                 │                      │
│   logging            requestcontext     logging                  │
│   config             logging              (leaf consumer)        │
│   context                                                        │
│   client/identity                                                │
│   utility                                                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  client   │  │   sqs    │  │ exception│  │   utility     │    │
│  │ (7 files) │  │ (8 files)│  │ (1 file) │  │  (8 files)    │    │
│  └────┬─────┘  └────┬─────┘  └──────────┘  └────┬──────────┘    │
│       │              │                           │               │
│   logging        requestcontext              logging             │
│   context        logging                                         │
│   utility        service/metric                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LEAF LAYER (no PAI deps)                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                              │
│  │   logging     │  │   context    │                              │
│  │  (6 files)    │  │  (9 files)   │                              │
│  │  Uses: SLF4J  │  │  Uses: none  │                              │
│  │  + Micrometer │  │  (pure models)│                             │
│  └──────────────┘  └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Table (Compact)

| Package | Depends On (within PAI) |
|---------|------------------------|
| `feature/rovoinsights` | requestcontext, task, sqs, logging, service/metric, featuregate, stratus, client, context, utility |
| `feature/nudge` | featuregate, requestcontext, logging, context |
| `feature/greeting` | (minimal — Spring MVC only) |
| `task` | sqs, requestcontext, logging |
| `stratus` | client, utility/user, context |
| `interceptor` | requestcontext, logging, featuregate, context |
| `requestcontext` | logging, config, context, client/identity, utility |
| `service/metric` | requestcontext, logging |
| `sqs` | requestcontext, logging, service/metric |
| `featuregate` | logging |
| `config` | logging, requestcontext |
| `client` | logging, context, utility |
| `context` | *(no PAI dependencies — pure domain models)* |
| `logging` | *(no PAI dependencies — uses SLF4J + Micrometer)* |
| `utility` | logging |
| `exception` | *(no PAI dependencies — standalone types)* |

### Invariant

**No downward dependencies.** Feature packages never import from each other. Platform packages form a DAG. `logging`, `context`, `exception`, and `utility` are leaf nodes with minimal or no internal dependencies.

---

## 8. External Service Dependencies

PAI communicates with three external Atlassian services, all routed through the **service proxy mesh** (egress authentication enabled). These are declared in `service-descriptor.sd.yml` under `serviceProxy.egress.dependencies`.

### Dependency Overview

```
                         ┌─────────────────────┐
                         │  proactive-ai-       │
                         │  platform            │
                         └─────────┬────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
              ▼                    ▼                     ▼
   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
   │  id-gatekeeper   │ │   ai-gateway     │ │ integrations-service │
   │                  │ │                  │ │                      │
   │ Identity lookups │ │ LLM inference    │ │ MCP tool provider    │
   │ User context     │ │ (Claude, OpenAI) │ │ (Jira, Confluence    │
   │ enrichment       │ │ Agent execution  │ │  API access)         │
   │                  │ │                  │ │                      │
   │ Timeout: 20s     │ │ Timeout: 600s    │ │ Timeout: 60s         │
   │ Retry: 5xx, 429  │ │ Retry: 5xx, 429  │ │ Retry: 5xx, 429     │
   └──────────────────┘ └──────────────────┘ └──────────────────────┘
```

### Detailed Service Dependencies

#### 1. `id-gatekeeper` — Identity & User Context

| Aspect | Detail |
|--------|--------|
| **Purpose** | User identity resolution. Called by `UserContextInterceptor` on every HTTP request to enrich the user context (account ID → user details: name, email, locale, permissions). |
| **PAI client** | `client/identity/IdGatekeeperClient` (sync) and `AsyncIdGatekeeperClient` (async) |
| **Base URL** | `${MESH_DEPENDENCY_ID_GATEKEEPER_BASE_URL}` (service mesh injected) |
| **Timeout** | 20,000ms (20 seconds) |
| **Retry policy** | Retries on 5xx and 429 (rate limited) |
| **Called by** | `interceptor/UserContextInterceptor` (every HTTP request), `requestcontext/` (async context enrichment) |
| **Failure impact** | Degraded user context — requests proceed with minimal identity info |

#### 2. `ai-gateway` — LLM Inference & Agent Execution

| Aspect | Detail |
|--------|--------|
| **Purpose** | Atlassian's centralized LLM gateway. Routes inference requests to Claude, OpenAI, or other model providers. Provides the `UnifiedLlmProvider` API via Stratus SDK. All LLM calls must go through this gateway — direct model SDK usage is forbidden. |
| **PAI client** | `stratus/AIGatewayService` → Stratus SDK → `UnifiedLlmProvider` |
| **Base URL** | `${MESH_DEPENDENCY_AI_GATEWAY_BASE_URL}` (service mesh injected) |
| **Timeout** | 600,000ms (10 minutes) — reflects long-running LLM inference |
| **Retry policy** | Retries on 5xx and 429 |
| **Called by** | `stratus/AIGatewayService` from `LongRun` worker group during Rovo Insights generation |
| **Failure impact** | Insight generation fails — task retried via SQS (up to 3 times before DLQ) |

#### 3. `integrations-service` — MCP Tool Provider

| Aspect | Detail |
|--------|--------|
| **Purpose** | Provides MCP (Model Context Protocol) sessions for Stratus agents. Gives AI agents access to Atlassian product tools (Jira issue queries, Confluence page reads, etc.) scoped by tenant and user permissions. |
| **PAI client** | `stratus/IntegrationServiceMcpSessionManager` + `IntegrationServiceToolProvider` |
| **Base URL** | `${MESH_DEPENDENCY_INTEGRATIONS_SERVICE_BASE_URL}` |
| **Endpoint** | `/mcp` (configured in `application.yml`) |
| **Timeout** | 60,000ms (60 seconds) for mesh; 30s application-level (`integrations-service.timeout: 30`) |
| **Retry policy** | Retries on 5xx and 429 |
| **Called by** | `stratus/IntegrationServiceMcpSessionManager` — creates per-request MCP sessions |
| **Failure impact** | AI agents cannot access product data — insights generation degrades to no-tool mode |

### Additional Infrastructure Dependencies

| Dependency | Type | Detail |
|------------|------|--------|
| **Redis (Valkey 7.x)** | Resource | General-purpose cache. Provisioned as `proactive-ai-cache` in service descriptor. Single primary + 1 replica, `cache.t4g.small`. Used for caching insight results and task state. |
| **AWS SQS** | Resource | Two queues: `analytics-events` (StreamHub) and `rovo-insights-generation-queue` (async tasks). Both with DLQ. |
| **StreamHub** | Event source | Delivers analytics events to the `analytics-events` SQS queue. Write access restricted to `streamhub-demux` service via IAM policy. |
| **Statsig** | SaaS | Feature flag evaluation service. Accessed via `featuregate-client-starter`. |
| **TAP Sidecar** | Sidecar | Targeting & Personalization sidecar at `http://tap-sidecar:8083`. Used for trait evaluation in nudge throttling (future). |
| **SignalFx** | SaaS | Metrics backend. Micrometer metrics are exported via the Micros observability sidecar. |

---

## 9. Key Architectural Invariants

These are the design rules the codebase enforces. Breaking them will cause issues:

### I-1: Every Request Has an MDC-Restorable Identity Triple

`request_id` + `tenant_id` + `account_id` are populated **before** any business logic runs:
- **HTTP**: By `RequestContextInterceptor` (extracts from headers).
- **SQS**: By message-attribute replay in the SQS consumer middleware.

This enables structured logging, metrics tagging, and distributed tracing across both sync and async paths.

### I-2: No Business Logic in Controllers

Controllers extract DTOs + the authenticated `User` and delegate to a Spring service. This makes business logic testable without spinning up the full Spring context. Verified by inspection of all 3 feature controllers.

### I-3: Long-Running Work Goes to SQS

No HTTP request should hold a thread for >1 second of business work. Anything slower (LLM inference, multi-stage analysis) lives behind `AsyncTaskService.submit()` → SQS → `LongRun` worker. The task envelope pattern ensures serialization, retry, and DLQ guarantees.

### I-4: All LLM/Agent Inference Goes Through Stratus

Direct OpenAI/Anthropic/etc. SDKs are **forbidden**. Stratus's `UnifiedLlmProvider` enforces tenant/audience/observability context per call. This centralizes model routing, cost tracking, and compliance.

### I-5: All Feature Flags Carry a Default Value

`FeatureService.checkGate(featureGate, defaultValue)` makes the default **mandatory** at the call site. If Statsig is unavailable, the service degrades to defaults rather than throwing exceptions.

---


## 10. Documentation Structure & Development Trajectory

### Documentation Set

This documentation consists of four files. See **INDEX.md** for a master navigation guide, cross-cutting concerns, and glossary.

| Document | Purpose |
|----------|---------|
| **INDEX.md** | Master navigation, cross-cutting concerns, package coverage matrix, glossary of 25+ terms |
| **01_ARCHITECTURE_OVERVIEW.md** | This document — system-level overview, tech stack, worker groups, dependency graph |
| **02_CORE_PLATFORM_INFRASTRUCTURE.md** | Deep dive into all 12 platform packages (requestcontext, logging, interceptor, context, metrics, featuregate, task, sqs, config, client, utility, exception) |
| **03_FEATURE_IMPLEMENTATIONS.md** | Deep dive into business logic (Rovo Insights, Nudge Throttle, Stratus/AI Gateway) |

### Development Trajectory

Based on verified PR history (#96–#108) and OKR analysis:

| Period | Milestone | Key Changes |
|--------|-----------|-------------|
| **Q1 2026** | Bootstrap | Kotlin migration, feature service, logging framework |
| **Q2 2026** | Feature push | Async tasks, visibility extension, MCP integration, REST controllers, Redis cache |
| **Q3–Q4 2026** (planned) | Production hardening | Real Rovo Insights logic, TAP-trait throttling, GASv3 signal ingestion, quality/latency uplift |
| **Q1 2027** (planned) | Scale | 1P + 3P proactive interactions |

---

*Document generated 2026-05-07 from direct analysis of the `proactive-ai-platform` codebase at `/Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform`.*
