# INDEX.md — Proactive AI Platform Documentation

> **Landing page for the `proactive-ai-platform` (PAI) codebase documentation.**
> Start here, then follow the recommended reading order.

---

## Documentation Map

| Order | Document | Size | What You'll Learn |
|-------|----------|------|-------------------|
| **1** | **INDEX.md** (this file) | ~127 lines | Navigation, cross-cutting themes, glossary |
| **2** | **01_ARCHITECTURE_OVERVIEW.md** | ~654 lines | System boundary, tech stack, 3 worker groups, package dependency graph, external service deps |
| **3** | **02_CORE_PLATFORM_INFRASTRUCTURE.md** | ~1,528 lines | Deep dive into all platform packages: request context, logging, interceptors, metrics, feature gates, async tasks, SQS, config, clients, utilities |
| **4** | **03_FEATURE_IMPLEMENTATIONS.md** | ~551 lines | Deep dive into 3 feature areas: Rovo Insights (async AI generation), Nudge Throttling, Stratus/AI Gateway |
| **5** | **04_BUILD_DEPLOY_OPS.md** | ~500 lines | Build system (Gradle plugins, 28 deps), service descriptor (SQS, Redis, worker groups), CI pipeline (13 steps), Dockerfile, Spinnaker, Nebulae, POCO policies |
| **6** | **05_CONFIGURATION_AND_TESTING.md** | ~596 lines | Application config (4 YAML profiles, cross-env diff table, SQS mapping, logback), test strategy (33 files, 4 patterns), MockK/AssertJ patterns, 37-package coverage matrix |

### Recommended Reading Strategy

- **Quick onboarding (30 min)**: Read INDEX.md → 01_ARCHITECTURE_OVERVIEW.md Sections 1–5 → 03_FEATURE_IMPLEMENTATIONS.md Section 1 (Rovo Insights)
- **Full onboarding (3 hours)**: All six documents in order
- **"I need to add a new feature"**: 01 Sections 3, 7, 9 → 02 Sections 2, 3, 6 → 03 (any feature as template)
- **"I'm on-call and something broke"**: 01 Section 5 (worker groups) → 01 Section 8 (external deps) → 02 Section 4 (interceptor pipeline) → 02 Section 7 (async tasks)

---

## Cross-Cutting Concerns

These themes bridge multiple documents. Understanding them is critical for working effectively in PAI.

### 1. Request Context Flow: HTTP → SQS → AI Gateway

The request context system (Doc 02 §2) is the backbone that connects the HTTP layer (Doc 02 §4) to feature implementations (Doc 03). Here's the end-to-end flow:

1. **HTTP arrives** → `LoggingContextClearingFilter` wipes stale MDC (Doc 02 §4.1)
2. **Context extraction** → `RequestContextInterceptor` pulls `tenant_id`, `request_id`, `account_id` from headers into MDC and `RequestScopedValue` store (Doc 02 §4.2)
3. **User enrichment** → `UserContextInterceptor` calls IdGatekeeper to resolve the user identity (Doc 02 §4.3, §11)
4. **Platform context** → `CommonContextSetterImpl` constructs `TenantContext` and `ProductContext` (Doc 02 §4.4, §5)
5. **Feature logic** → Controllers use enriched context to process requests (Doc 03)
6. **Async handoff** → `AsyncTaskService` serializes context into SQS message attributes (Doc 02 §8)
7. **Worker pickup** → `AsyncTaskDispatcher` on `LongRun` worker deserializes context and re-populates MDC via `LoggingContext.addAsyncTaskContext()` (Doc 02 §2.3, §8)
8. **AI Gateway call** → `AIGatewayService` uses context for LLM inference via Stratus SDK (Doc 03 §3)

### 2. Observability Pipeline

Every layer participates in observability:
- **Logging**: `LaasLogger` (Doc 02 §3) wraps SLF4J with structured context. `InterceptedLogger` adds privacy-filtering for UGC. Every log line carries MDC keys set by interceptors.
- **Metrics**: `CoreMetricsService` → `MetricsService` two-tier hierarchy (Doc 02 §6). Features use `MetricsService.countWithRovoTags()` for product-aware metrics. Async tasks are instrumented via `InstrumentedDispatcher` (Doc 02 §12.1).
- **Feature flags**: `FeatureService` wraps Statsig SDK (Doc 02 §7) and is checked in interceptors, task handlers, and controllers.

### 3. Worker Group Routing

The single JAR deploys as three worker groups (Doc 01 §5), controlled by env var `MICROS_GROUP`:
- **WebServer**: HTTP endpoints + interceptor pipeline → serves Rovo Insights API, Nudge API (Doc 03 §1, §2)
- **LongRun**: SQS consumer → `AsyncTaskDispatcher` → `RovoInsightsGenerationTaskHandler` (Doc 02 §8, Doc 03 §1)
- **SHWorkers**: StreamHub analytics events → `AnalyticsEventsMessageQueueConsumer` (Doc 02 §9)

Conditional bean activation uses `OnLongRunWorkerNodeOrLocalCondition` and `OnSHWorkerNodeOrLocalCondition` (Doc 02 §10.3).

### 4. Feature Flag Integration

Feature flags are pervasive:
- `FeatureFlagContextService` initializes Statsig context per-request (Doc 02 §7.2)
- `FeatureFlagEvaluationTracker` tracks which gates were checked (Doc 02 §7.3)
- `InterceptedLogger` can conditionally suppress log fields based on feature gates (Doc 02 §3.2)
- Rovo Insights generation is gated behind feature flags (Doc 03 §1)
- Nudge throttle behavior is planned to be gated (Doc 03 §2)

---

## Package Coverage Matrix

PAI has 16 top-level source packages (15 under the main `proactiveai` namespace plus `stratus` as a peer-level AI Gateway integration layer). All are documented:

| Package | Files | LoC | Primary Document | Section |
|---------|-------|-----|-----------------|---------|
| `feature/rovoinsights` | 16 | ~658 | 03_FEATURE_IMPLEMENTATIONS | §1 |
| `feature/nudge` | 4 | ~128 | 03_FEATURE_IMPLEMENTATIONS | §2 |
| `feature/greeting` | 1 | ~14 | 01_ARCHITECTURE_OVERVIEW | §6 |
| `stratus` | 8 | ~587 | 03_FEATURE_IMPLEMENTATIONS | §3 |
| `requestcontext` | 14 | ~906 | 02_CORE_PLATFORM_INFRASTRUCTURE | §2 |
| `logging` | 6 | ~568 | 02_CORE_PLATFORM_INFRASTRUCTURE | §3 |
| `interceptor` | 5 | ~295 | 02_CORE_PLATFORM_INFRASTRUCTURE | §4 |
| `context` | 9 | ~381 | 02_CORE_PLATFORM_INFRASTRUCTURE | §5 |
| `service/metric` | 5 | ~1,243 | 02_CORE_PLATFORM_INFRASTRUCTURE | §6 |
| `featuregate` | 8 | ~754 | 02_CORE_PLATFORM_INFRASTRUCTURE | §7 |
| `task` | 11 | ~649 | 02_CORE_PLATFORM_INFRASTRUCTURE | §8 |
| `sqs` | 8 | ~370 | 02_CORE_PLATFORM_INFRASTRUCTURE | §9 |
| `config` | 6 | ~208 | 02_CORE_PLATFORM_INFRASTRUCTURE | §10 |
| `client` | 7 | ~399 | 02_CORE_PLATFORM_INFRASTRUCTURE | §11 |
| `utility` | 8 | ~557 | 02_CORE_PLATFORM_INFRASTRUCTURE | §12 |
| `exception` | 1 | ~116 | 02_CORE_PLATFORM_INFRASTRUCTURE | §13 |

---

## Glossary of Key Terms

| Term | Definition |
|------|-----------|
| **PAI** | Proactive AI Platform — the microservice documented here (`proactive-ai-platform`) |
| **Micros** | Atlassian's internal platform-as-a-service for deploying JVM microservices. Provides starters, health checks, lifecycle management, service mesh. |
| **SLAUTH** | Service-Level AUTHentication — Atlassian's JWT-based service-to-service authentication. Incoming requests carry SLAUTH tokens verified by the `micros-spring-boot-starter-security-slauth-server` starter. |
| **POCO** | Policy-based authorization framework. PAI uses a POCO policy file (`policies/service/policy.json`) to control which services/users can call which endpoints. |
| **StreamHub** | Atlassian's event streaming platform. Delivers analytics events to PAI via SQS subscriptions defined in `streamhub/subscriptions/`. |
| **MCP** | Model Context Protocol — a protocol for providing AI agents with tool access. PAI uses `IntegrationServiceMcpSessionManager` to create MCP sessions against `integrations-service`. |
| **TAP** | Targeting & Personalization — Atlassian's trait-based user targeting platform. PAI plans to use TAP traits for nudge throttle decisions via a sidecar at `http://tap-sidecar:8083`. |
| **LaasLogger** | Logging-as-a-Service Logger — PAI's custom SLF4J wrapper that automatically attaches structured MDC context to every log line. Created via `LaasLoggerFactory.getLogger()`. |
| **Stratus SDK** | Atlassian's SDK for interacting with the AI Gateway. Provides `UnifiedLlmProvider` for LLM calls, agent execution, and tool management. |
| **AI Gateway** | Atlassian's centralized LLM inference service. All model calls must route through it — direct OpenAI/Anthropic SDK usage is forbidden. Accessed via Stratus SDK. |
| **SQS** | Amazon Simple Queue Service — used for async task delivery between WebServer and LongRun worker groups, and for StreamHub event ingestion. |
| **DLQ** | Dead Letter Queue — SQS queue where messages are sent after exceeding `MaxReceiveCount`. Each PAI SQS queue has a corresponding DLQ. |
| **IdGatekeeper** | Atlassian identity service. PAI calls it to resolve `account_id` → user details (name, email, locale, permissions). |
| **Statsig** | Third-party feature flag service. PAI uses it via `featuregate-client-starter` for gate checks and experiment configs. |
| **Micrometer** | JVM metrics facade. PAI uses Micrometer to emit counters, timers, gauges, and summaries to SignalFx. |
| **SignalFx** | Metrics backend (SaaS). Micrometer metrics are exported via the Micros observability sidecar. |
| **MDC** | Mapped Diagnostic Context (SLF4J) — thread-local key-value store for structured logging. PAI's interceptors populate MDC with request/tenant/user context. |
| **RequestScopedValue** | PAI's type-safe request-scoped storage pattern. Uses `RequestScopedValueKey` enum + `RequestScopedValueOwner` interface to manage per-request state in Spring's `RequestAttributes`. |
| **Worker Group** | A Micros deployment topology. PAI deploys three groups (`WebServer`, `LongRun`, `SHWorkers`) from the same Docker image, each running different components controlled by `MICROS_GROUP` env var. |
| **InstrumentedDispatcher** | PAI's custom Kotlin coroutine dispatcher that wraps a thread pool with Micrometer instrumentation for queue depth, active threads, and execution time. |
| **Nebulae** | Atlassian's local development environment tool. Configured via `nebulae.yml` at the repo root. |
| **Spinnaker** | CD pipeline tool. PAI's deployment pipeline is defined in `default-pipelines.spinnaker.yaml`. |
| **Compass** | Atlassian's service catalog. PAI is registered as a Tier 3 Java 21 service via `component-descriptor.yml`. |

---

*Master navigation document for PAI codebase documentation. Generated 2026-05-07.*
