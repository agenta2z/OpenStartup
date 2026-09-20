# SYMBOL_INDEX.md — Class/File → Chapter Reverse Map

> **Purpose.** When you (human or agent) encounter a class name or file
> path in the source, this index tells you which chapter to read for
> deeper context. Built 2026-05-05 from `grep -rEn '^(class|interface|object|enum class|sealed )'`
> against `src/main/kotlin/`.
>
> **Verified totals (re-derive with the grep above):**
> 121 type declarations · 5 controllers · 27 Spring components ·
> 4 AsyncTaskHandler files · 2 Spring Conditions · 23 enums.
>
> **How to use.** `Cmd-F` for the symbol or for a path fragment, then
> click the linked chapter.

---

## 1. Controllers (5 total) — REST entry points

| Symbol | File | Chapter |
|---|---|---|
| `WebServiceController` | `greeting/WebServiceController.kt` | [modules/features/greeting.rst](modules/features/greeting.rst) |
| `RovoInsightsController` | `feature/rovoinsights/api/RovoInsightsController.kt` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |
| `RovoInsightsTestController` | `feature/rovoinsights/api/rest/RovoInsightsTestController.kt` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |
| `NudgeThrottleController` | `feature/nudge/api/rest/NudgeThrottleController.kt` | [modules/features/nudge.rst](modules/features/nudge.rst) + [modules/nudge/nudge-throttle.rst](modules/nudge/nudge-throttle.rst) |
| `StratusTestController` | `stratus/StratusTestController.kt` | [modules/platform/stratus.rst](modules/platform/stratus.rst) |

## 2. Spring Configurations (`@Configuration` classes)

| Symbol | File | Chapter |
|---|---|---|
| `WebMvcConfiguration` | `config/WebMvcConfiguration.kt` | [modules/platform/config.rst](modules/platform/config.rst) |
| `MicrosEnvironmentConfig` | `config/MicrosEnvironmentConfig.kt` | [modules/platform/config.rst](modules/platform/config.rst) |
| `MvcSecurityConfig` | `config/MvcSecurityConfig.kt` | [modules/platform/config.rst](modules/platform/config.rst) + [architecture/cross-cutting/08-auth-and-tenant.rst](architecture/cross-cutting/08-auth-and-tenant.rst) |
| `AIGatewayClientConfiguration` | `stratus/AIGatewayClientConfiguration.kt` | [modules/platform/stratus.rst](modules/platform/stratus.rst) |
| `IntegrationServiceMcpServerConfig` | `stratus/IntegrationServiceMcpServerConfig.kt` | [modules/platform/stratus.rst](modules/platform/stratus.rst) + [ADR-005](architecture/cross-cutting/14-architectural-decisions.rst) |
| `SqsEventConsumerConfig` | `sqs/SqsEventConsumerConfig.kt` | [modules/platform/sqs.rst](modules/platform/sqs.rst) |

## 3. Spring Conditions (worker-group gating)

| Symbol | File | Chapter |
|---|---|---|
| `OnSHWorkerNodeOrLocalCondition` | `config/OnSHWorkerNodeOrLocalCondition.kt` | [modules/platform/config.rst](modules/platform/config.rst) + [ADR-001](architecture/cross-cutting/14-architectural-decisions.rst) |
| `OnLongRunWorkerNodeOrLocalCondition` | `config/OnLongRunWorkerNodeOrLocalCondition.kt` | [modules/platform/config.rst](modules/platform/config.rst) + [ADR-001](architecture/cross-cutting/14-architectural-decisions.rst) |

## 4. Async-task framework

| Symbol | File | Chapter |
|---|---|---|
| `AsyncTask` (interface) | `task/AsyncTask.kt` (parent) | [modules/platform/task.rst](modules/platform/task.rst) + [ADR-002, ADR-003](architecture/cross-cutting/14-architectural-decisions.rst) |
| `AsyncTaskHandler<T>` (interface) | `task/AsyncTaskHandler.kt` | [modules/platform/task.rst](modules/platform/task.rst) |
| `AsyncTaskService` (interface) | `task/AsyncTaskService.kt` | [modules/platform/task.rst](modules/platform/task.rst) |
| `AsyncTaskServiceImpl` | `task/internal/AsyncTaskServiceImpl.kt` | [modules/platform/task.rst](modules/platform/task.rst) |
| `AsyncTaskDispatcher` | `task/AsyncTaskDispatcher.kt` | [modules/platform/task.rst](modules/platform/task.rst) |
| `AsyncTaskQueueRegistry` | `task/AsyncTaskQueueRegistry.kt` | [modules/platform/task.rst](modules/platform/task.rst) |
| `AsyncTaskExecutionContext` | `task/AsyncTaskExecutionContext.kt` | [architecture/cross-cutting/03-request-context-and-mdc.rst](architecture/cross-cutting/03-request-context-and-mdc.rst) + [ADR-003](architecture/cross-cutting/14-architectural-decisions.rst) |
| `VisibilityExtendingSQSQueueConsumer` | `task/internal/VisibilityExtendingSQSQueueConsumer.kt` | [modules/platform/task.rst](modules/platform/task.rst) + [ADR-004](architecture/cross-cutting/14-architectural-decisions.rst) |
| `RovoInsightsGenerationTaskHandler` | `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |
| `RovoInsightsGenerationSqsQueueConsumer` | `feature/rovoinsights/internal/RovoInsightsGenerationSqsQueueConsumer.kt` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |

## 5. SQS / StreamHub consumers

| Symbol | File | Chapter |
|---|---|---|
| `MessageQueueConsumerMiddleware` | `sqs/MessageQueueConsumerMiddleware.kt` | [modules/platform/sqs.rst](modules/platform/sqs.rst) + [request-context chapter](architecture/cross-cutting/03-request-context-and-mdc.rst) |
| `AnalyticsEventsSqsQueueConsumer` | `sqs/AnalyticsEventsSqsQueueConsumer.kt` | [modules/platform/sqs.rst](modules/platform/sqs.rst) |
| `AnalyticsEventsMessageQueueConsumer` | `sqs/AnalyticsEventsMessageQueueConsumer.kt` | [modules/platform/sqs.rst](modules/platform/sqs.rst) |
| `AnalyticsEnrichedEventHandler` | `sqs/AnalyticsEnrichedEventHandler.kt` | [modules/platform/sqs.rst](modules/platform/sqs.rst) |

## 6. Interceptors (HTTP filter chain)

| Symbol | File | Chapter |
|---|---|---|
| `RequestContextInterceptor` | `interceptor/RequestContextInterceptor.kt` | [modules/platform/interceptor.rst](modules/platform/interceptor.rst) |
| `UserContextInterceptor` | `interceptor/UserContextInterceptor.kt` | [modules/platform/interceptor.rst](modules/platform/interceptor.rst) + [auth chapter](architecture/cross-cutting/08-auth-and-tenant.rst) |
| `CommonContextSetter` (interface) | `interceptor/CommonContextSetter.kt` | [modules/platform/interceptor.rst](modules/platform/interceptor.rst) |
| `CommonContextSetterImpl` | `interceptor/CommonContextSetterImpl.kt` | [modules/platform/interceptor.rst](modules/platform/interceptor.rst) |
| `CommonContextSetterForInterceptors` | `interceptor/CommonContextSetterForInterceptors.kt` | [modules/platform/interceptor.rst](modules/platform/interceptor.rst) |

## 7. Request-context layer

| Symbol | File | Chapter |
|---|---|---|
| `RequestScopedValueService` (interface) | `requestcontext/RequestScopedValueService.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |
| `RequestScopedValueServiceImpl` | `requestcontext/internal/RequestScopedValueServiceImpl.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |
| `RequestScopedValuesInitter` (interface) | `requestcontext/RequestScopedValuesInitter.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |
| `RequestScopedValuesInitterImpl` | `requestcontext/internal/RequestScopedValuesInitterImpl.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |
| `LoggingContext` (interface) | `requestcontext/LoggingContext.kt` | [03-request-context-and-mdc.rst](architecture/cross-cutting/03-request-context-and-mdc.rst) |
| `LoggingContextImpl` | `requestcontext/internal/LoggingContextImpl.kt` | [03-request-context-and-mdc.rst](architecture/cross-cutting/03-request-context-and-mdc.rst) |
| `MiscellaneousRequestContextVariablesService` | `requestcontext/MiscellaneousRequestContextVariablesService.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |
| `RequestScopedValueOwners` | `requestcontext/RequestScopedValueOwners.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |
| `RequestScopedValueKey` (enum) | `requestcontext/RequestScopedValueKey.kt` | [modules/platform/requestcontext.rst](modules/platform/requestcontext.rst) |

## 8. Stratus / AI Gateway / MCP

| Symbol | File | Chapter |
|---|---|---|
| `AIGatewayServiceImpl` | `stratus/internal/AIGatewayServiceImpl.kt` | [modules/platform/stratus.rst](modules/platform/stratus.rst) + [07-ai-gateway-and-stratus.rst](architecture/cross-cutting/07-ai-gateway-and-stratus.rst) |
| `IntegrationServiceMcpSessionManager` | `stratus/IntegrationServiceMcpSessionManager.kt` | [modules/platform/stratus.rst](modules/platform/stratus.rst) + [ADR-005](architecture/cross-cutting/14-architectural-decisions.rst) |
| `IntegrationServiceToolProvider` | `stratus/IntegrationServiceToolProvider.kt` | [modules/platform/stratus.rst](modules/platform/stratus.rst) |

## 9. Metrics layer

| Symbol | File | Chapter |
|---|---|---|
| `MetricsService` (interface) | `service/metric/MetricsService.kt` | [modules/platform/service-metric.rst](modules/platform/service-metric.rst) |
| `MetricsServiceImpl` | `service/metric/internal/MetricsServiceImpl.kt` | [modules/platform/service-metric.rst](modules/platform/service-metric.rst) |
| `CoreMetricsService` (interface) | `service/metric/CoreMetricsService.kt` | [modules/platform/service-metric.rst](modules/platform/service-metric.rst) |
| `MetricKey` (enum) | `service/metric/MetricKey.kt:7` | [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Part 1 |
| `HistogramMetric` (enum) | `service/metric/MetricKey.kt:24` | [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Part 1 |
| `ResultMetricBase` (enum) | `service/metric/MetricKey.kt:42` | [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Part 1 |
| `HistogramBucket` (enum) | `service/metric/MetricKey.kt:52` | [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Part 2 |
| `Status` (enum) | `service/metric/MetricKey.kt:65` | [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Part 1 |

## 10. Feature flags (Statsig)

| Symbol | File | Chapter |
|---|---|---|
| `FeatureService` (interface) | `featuregate/FeatureService.kt` | [04-feature-flags.rst](architecture/cross-cutting/04-feature-flags.rst) + [ADR-006](architecture/cross-cutting/14-architectural-decisions.rst) |
| `FeatureGate` (interface) | `featuregate/FeatureGate.kt` | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |
| `FeatureFlagContextService` | `featuregate/FeatureFlagContextService.kt` | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |
| `FeatureFlagEvaluationTracker` | `featuregate/FeatureFlagEvaluationTracker.kt` | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |
| `FeatureFlagContextContextType` (enum) | `featuregate/FeatureFlagContextService.kt:8` | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |
| `AiFeatureGates` (enum) | `featuregate/AiFeatureGates.kt` | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |
| `PermanentFeatureGates` (enum) | `featuregate/PermanentFeatureGates.kt` | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |

## 11. Logging (LaasLogger family)

| Symbol | File | Chapter |
|---|---|---|
| `LaasLogger` | `logging/LaasLogger.kt` | [modules/platform/logging.rst](modules/platform/logging.rst) + [ADR-009](architecture/cross-cutting/14-architectural-decisions.rst) |
| `LaasLoggerFactory` | `logging/LaasLoggerFactory.kt` | [modules/platform/logging.rst](modules/platform/logging.rst) + [ADR-009](architecture/cross-cutting/14-architectural-decisions.rst) |
| `InterceptedLogger` | `logging/InterceptedLogger.kt` | [modules/platform/logging.rst](modules/platform/logging.rst) |
| `WithUGCLogger` | `logging/WithUGCLogger.kt` | [modules/platform/logging.rst](modules/platform/logging.rst) |
| `NoopLogger` | `logging/NoopLogger.kt` | [modules/platform/logging.rst](modules/platform/logging.rst) |

## 12. Client (HTTP / IdGatekeeper)

| Symbol | File | Chapter |
|---|---|---|
| `HttpClientCommons` | `client/HttpClientCommons.kt` | [modules/platform/client.rst](modules/platform/client.rst) |
| `Audiences` | `client/Audiences.kt` | [modules/platform/client.rst](modules/platform/client.rst) |
| `IdGatekeeperClient` (interface) | `client/identity/IdGatekeeperClient.kt` | [modules/platform/client.rst](modules/platform/client.rst) |
| `IdGatekeeperClientImpl` | `client/identity/IdGatekeeperClientImpl.kt` | [modules/platform/client.rst](modules/platform/client.rst) |
| `AsyncIdGatekeeperClientImpl` | `client/identity/internal/AsyncIdGatekeeperClientImpl.kt` | [modules/platform/client.rst](modules/platform/client.rst) |

## 13. Tenant / domain context

| Symbol | File | Chapter |
|---|---|---|
| `Product` (enum) | `context/Product.kt` | [modules/platform/context.rst](modules/platform/context.rst) |
| `DataWorkspaceType` (enum) | `context/TenantContextModels.kt:63` | [modules/platform/context.rst](modules/platform/context.rst) |
| `HelpSeekerExperience` (enum) | `context/Experience.kt:5` | [modules/platform/context.rst](modules/platform/context.rst) |
| `UseCase` (enum) | `context/Experience.kt:10` | [modules/platform/context.rst](modules/platform/context.rst) |
| `Branding` (enum) | `context/Experience.kt:20` | [modules/platform/context.rst](modules/platform/context.rst) |
| `Experience` (enum) | `context/Experience.kt:35` | [modules/platform/context.rst](modules/platform/context.rst) |

## 14. Utility (threading / user / tenant)

| Symbol | File | Chapter |
|---|---|---|
| `RequestAttributesCoroutineContext` | `utility/threading/RequestAttributesCoroutineContext.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) + [03-request-context-and-mdc.rst](architecture/cross-cutting/03-request-context-and-mdc.rst) |
| `InstrumentedDispatcher` | `utility/threading/InstrumentedDispatcher.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) |
| `CoroutineMonitor` | `utility/threading/CoroutineMonitor.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) |
| `DispatcherMonitor` (enum) | `utility/threading/CoroutineMonitor.kt:18` | [modules/platform/utility.rst](modules/platform/utility.rst) |
| `ThreadConfig` | `utility/threading/ThreadConfig.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) |
| `User` (interface) | `utility/user/User.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) |
| `UserImpl` | `utility/user/UserImpl.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) |
| `TcsService` | `utility/tenant/TcsService.kt` | [modules/platform/utility.rst](modules/platform/utility.rst) |

## 15. Config (environment / security)

| Symbol | File | Chapter |
|---|---|---|
| `MicrosEnvironmentType` (enum) | `config/MicrosEnvironmentType.kt:3` | [modules/platform/config.rst](modules/platform/config.rst) + [ADR-007](architecture/cross-cutting/14-architectural-decisions.rst) |

## 16. Exception

| Symbol | File | Chapter |
|---|---|---|
| `RestClientException` | `exception/RestClientException.kt` | [03-module-catalog.rst](architecture/03-module-catalog.rst) §exception (no dedicated module page) |
| `ExceptionLogLevel` (enum) | `exception/RestClientException.kt:108` | [03-module-catalog.rst](architecture/03-module-catalog.rst) §exception |

## 17. Feature: Rovo Insights system types

| Symbol | File | Chapter |
|---|---|---|
| `InsightType` (enum) | `feature/rovoinsights/system/InsightType.kt:10` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) + [modules/rovo-insights/index.rst](modules/rovo-insights/index.rst) |
| `Strategy` (enum) | `feature/rovoinsights/system/RovoInsightsRequest.kt:10` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |
| `Color` (enum) | `feature/rovoinsights/system/Color.kt:11` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |
| `Glyph` (enum) | `feature/rovoinsights/system/Glyph.kt:11` | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |

## 18. Feature: Nudge

| Symbol | File | Chapter |
|---|---|---|
| `NudgeType` (enum) | `feature/nudge/api/domain/NudgeType.kt:3` | [modules/features/nudge.rst](modules/features/nudge.rst) |

---

## File-path → chapter quick map (top-level package roots)

| Source path prefix | Primary chapter |
|---|---|
| `config/` | `modules/platform/config.rst` |
| `interceptor/` | `modules/platform/interceptor.rst` |
| `requestcontext/` | `modules/platform/requestcontext.rst` |
| `logging/` | `modules/platform/logging.rst` |
| `service/metric/` | `modules/platform/service-metric.rst` |
| `featuregate/` | `modules/platform/featuregate.rst` |
| `task/` | `modules/platform/task.rst` |
| `sqs/` | `modules/platform/sqs.rst` |
| `stratus/` | `modules/platform/stratus.rst` |
| `client/` | `modules/platform/client.rst` |
| `context/` | `modules/platform/context.rst` |
| `utility/` | `modules/platform/utility.rst` |
| `exception/` | `architecture/03-module-catalog.rst` (§exception) |
| `greeting/` | `modules/features/greeting.rst` |
| `feature/nudge/` | `modules/features/nudge.rst` (+ `modules/nudge/nudge-throttle.rst`) |
| `feature/rovoinsights/` | `modules/features/rovo-insights.rst` (+ `modules/rovo-insights/index.rst`) |

## YAML / config-file → chapter quick map

| Config file | Primary chapter |
|---|---|
| `service-descriptor.sd.yml` | [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Parts 4–7 + [09-deployment-and-config.rst](architecture/cross-cutting/09-deployment-and-config.rst) |
| `application.yml` / `application-local.yml` | [09-deployment-and-config.rst](architecture/cross-cutting/09-deployment-and-config.rst) + [11-metrics-catalog.rst](architecture/cross-cutting/11-metrics-catalog.rst) Parts 2–3 |
| `nebulae.yml` | [09-deployment-and-config.rst](architecture/cross-cutting/09-deployment-and-config.rst) |
| `bitbucket-pipelines.yml` | [02-development-history.rst](architecture/cross-cutting/02-development-history.rst) §CI |
| `default-pipelines.spinnaker.yml` | [09-deployment-and-config.rst](architecture/cross-cutting/09-deployment-and-config.rst) |
| `Dockerfile` | [09-deployment-and-config.rst](architecture/cross-cutting/09-deployment-and-config.rst) |
| `policies/service/policy.json` | [03-module-catalog.rst](architecture/03-module-catalog.rst) §security |
| `build.gradle.kts` | (not deep-documented — top-churn file per [15-velocity-and-debt.rst](architecture/cross-cutting/15-velocity-and-debt.rst) Part 5) |

## How to add a symbol
1. Find the canonical declaration via `grep -rn 'class FooBar' src/main/kotlin/`.
2. Add a row in the section that matches its role (controller, service, etc.).
3. If no chapter covers it well, that's a coverage gap — open a PR adding a section to the relevant `modules/platform/<package>.rst` first, then add the symbol here.
