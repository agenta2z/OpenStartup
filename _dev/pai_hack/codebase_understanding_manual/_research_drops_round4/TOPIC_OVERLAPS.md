# TOPIC OVERLAPS — 29 Topics Covered in 3+ Chapters

These topics appear across multiple chapters without clear primary ownership.
**Action**: Designate a PRIMARY chapter; other chapters should reference it.


## AI Gateway (14 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/client.rst`
- `modules/platform/stratus.rst`
- `modules/stratus/ai-gateway.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Async task handler (14 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/task.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Audit logging (4 chapters)

**Suggested Primary Owner**: `architecture/cross-cutting/01-business-and-technical-goals.rst`

**All chapters**:
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/08-auth-and-tenant.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`

## Context propagation (16 chapters)

**Suggested Primary Owner**: `architecture/02-request-lifecycle.rst`

**All chapters**:
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/platform/client.rst`
- `modules/platform/config.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/stratus.rst`
- `modules/platform/utility.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Coroutine propagation (19 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/08-auth-and-tenant.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/client.rst`
- `modules/platform/config.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/rovo-insights/rovo-insights-api.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Docker deployment (4 chapters)

**Suggested Primary Owner**: `architecture/cross-cutting/09-deployment-and-config.rst`

**All chapters**:
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/platform/config.rst`

## GDPR data deletion (3 chapters)

**Suggested Primary Owner**: `architecture/02-request-lifecycle.rst`

**All chapters**:
- `architecture/02-request-lifecycle.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`

## Graceful shutdown (5 chapters)

**Suggested Primary Owner**: `architecture/02-request-lifecycle.rst`

**All chapters**:
- `architecture/02-request-lifecycle.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/platform/interceptor.rst`
- `overviews/03-criticality-dashboard.rst`

## Greeting feature (7 chapters)

**Suggested Primary Owner**: `architecture/01-architecture-overview.rst`

**All chapters**:
- `architecture/01-architecture-overview.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `modules/features/greeting.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Incident response (11 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/platform/task.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Integration tests (9 chapters)

**Suggested Primary Owner**: `architecture/03-module-catalog.rst`

**All chapters**:
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/03-criticality-dashboard.rst`

## JVM tuning (23 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/greeting.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/logging.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/sqs.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Kotlin (38 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/08-auth-and-tenant.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/nudge/nudge-throttle.rst`
- `modules/platform/client.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/logging.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/service-metric.rst`
- `modules/platform/sqs.rst`
- `modules/platform/stratus.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/rovo-insights/rovo-insights-api.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `modules/stratus/ai-gateway.rst`
- `modules/stratus/mcp-integration.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Micrometer metrics (27 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/logging.rst`
- `modules/platform/service-metric.rst`
- `modules/platform/sqs.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/stratus/ai-gateway.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Nudge feature (34 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/nudge/nudge-throttle.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/service-metric.rst`
- `modules/platform/sqs.rst`
- `modules/platform/stratus.rst`
- `modules/rovo-insights/rovo-insights-api.rst`
- `modules/stratus/ai-gateway.rst`
- `modules/stratus/mcp-integration.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Rate limiting (5 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `modules/nudge/nudge-throttle.rst`

## Redis integration (18 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/sqs.rst`
- `modules/platform/stratus.rst`
- `overviews/02-architectural-narrative.rst`

## Rovo Insights (25 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/stratus.rst`
- `modules/platform/task.rst`
- `modules/rovo-insights/rovo-insights-api.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## SLAuth (40 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/08-auth-and-tenant.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/nudge/nudge-throttle.rst`
- `modules/platform/client.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/logging.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/service-metric.rst`
- `modules/platform/stratus.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/rovo-insights/rovo-insights-api.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `modules/stratus/ai-gateway.rst`
- `modules/stratus/mcp-integration.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## SQS queue (21 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/sqs.rst`
- `modules/platform/task.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## SQS visibility timeout (10 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/task.rst`

## Splunk logging (28 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/greeting.rst`
- `modules/nudge/nudge-throttle.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/logging.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/service-metric.rst`
- `modules/platform/sqs.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Stability patterns (18 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/task.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `modules/stratus/mcp-integration.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Statsig context (17 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/requestcontext.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Stratus integration (23 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/08-auth-and-tenant.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `architecture/cross-cutting/15-velocity-and-debt.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/context.rst`
- `modules/platform/stratus.rst`
- `modules/stratus/ai-gateway.rst`
- `modules/stratus/mcp-integration.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## TLS certificates (7 chapters)

**Suggested Primary Owner**: `architecture/02-request-lifecycle.rst`

**All chapters**:
- `architecture/02-request-lifecycle.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/interceptor.rst`
- `overviews/02-architectural-narrative.rst`

## Tenant isolation (38 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/04-feature-flags.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/07-ai-gateway-and-stratus.rst`
- `architecture/cross-cutting/08-auth-and-tenant.rst`
- `architecture/cross-cutting/09-deployment-and-config.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/11-metrics-catalog.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/greeting.rst`
- `modules/features/nudge.rst`
- `modules/features/rovo-insights.rst`
- `modules/nudge/nudge-throttle.rst`
- `modules/platform/client.rst`
- `modules/platform/config.rst`
- `modules/platform/context.rst`
- `modules/platform/featuregate.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/logging.rst`
- `modules/platform/requestcontext.rst`
- `modules/platform/service-metric.rst`
- `modules/platform/stratus.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/rovo-insights/rovo-insights-api.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `modules/stratus/ai-gateway.rst`
- `modules/stratus/mcp-integration.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Thread pools (17 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/03-request-context-and-mdc.rst`
- `architecture/cross-cutting/06-async-tasks-and-sqs.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/rovo-insights.rst`
- `modules/platform/config.rst`
- `modules/platform/interceptor.rst`
- `modules/platform/task.rst`
- `modules/platform/utility.rst`
- `modules/rovo-insights/rovo-insights-generation.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`

## Throttling (17 chapters)

**Suggested Primary Owner**: `architecture/00-glossary.rst`

**All chapters**:
- `architecture/00-glossary.rst`
- `architecture/01-architecture-overview.rst`
- `architecture/02-request-lifecycle.rst`
- `architecture/03-module-catalog.rst`
- `architecture/cross-cutting/01-business-and-technical-goals.rst`
- `architecture/cross-cutting/02-development-history.rst`
- `architecture/cross-cutting/05-observability-and-metrics.rst`
- `architecture/cross-cutting/10-vision-and-strategy.rst`
- `architecture/cross-cutting/12-optimization-playbook.rst`
- `architecture/cross-cutting/13-full-history-catalog.rst`
- `architecture/cross-cutting/14-architectural-decisions.rst`
- `modules/features/nudge.rst`
- `modules/nudge/nudge-throttle.rst`
- `modules/platform/sqs.rst`
- `overviews/01-multi-axis-matrix.rst`
- `overviews/02-architectural-narrative.rst`
- `overviews/03-criticality-dashboard.rst`
