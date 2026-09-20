# TOPIC_INDEX.md — Topic / Keyword → Chapter

> **Purpose.** Alphabetical concept index. When you have a topic word
> but don't know which chapter discusses it, look it up here.
> Authored 2026-05-05 by direct chapter reads with explicit primary-owner designation.
>
> **Companion files:**
> - [`AGENTS.md`](AGENTS.md) — problem-routing for AI agents.
> - [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) — class/file → chapter.
> - [`PROBLEM_PLAYBOOKS.md`](PROBLEM_PLAYBOOKS.md) — long-form scenarios.
> - [`MANIFEST.json`](MANIFEST.json) — same data in JSON form.

## Conventions

* Each row lists the **primary** chapter first; comma-separated
  secondaries follow.
* Path roots: `arch/` = `architecture/`, `cc/` = `architecture/cross-cutting/`,
  `mod/` = `modules/`, `ov/` = `overviews/`.
* "—" means **no chapter covers this**. See the gap list at the end.

---

## A
| Topic | Chapter(s) |
|---|---|
| ADRs (decision records) | `cc/14-architectural-decisions` |
| `@JsonTypeInfo` polymorphism | `cc/06-async-tasks-and-sqs`, `mod/platform/task` |
| `@Conditional` (Spring) | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |
| AI Gateway (Atlassian) | `cc/07-ai-gateway-and-stratus`, `mod/platform/stratus`, `cc/11-metrics-catalog` Part 7 |
| AI invocations OKR | `cc/01-business-and-technical-goals`, `cc/10-vision-and-strategy` |
| AIX tickets | `cc/13-full-history-catalog` Part 4, `cc/02-development-history` |
| Alarms (CloudWatch / Tome) | `cc/11-metrics-catalog` Part 4, `cc/14-architectural-decisions` ADR-012 |
| `application.yml` | `cc/09-deployment-and-config`, `cc/11-metrics-catalog` |
| Async-task framework | `cc/06-async-tasks-and-sqs`, `mod/platform/task`, `cc/14-architectural-decisions` ADR-002/3/4 |
| Atlas Goal API (live OKR) | `cc/01-business-and-technical-goals` (note: **NOT retrievable today**) |
| AVI (Analytics Versioned Identifier) | `arch/00-glossary`, `mod/platform/sqs` |

## B
| Topic | Chapter(s) |
|---|---|
| Bitbucket pipelines | `cc/02-development-history`, `cc/09-deployment-and-config` |
| PR conventions | `cc/12-optimization-playbook` Part 8, `cc/02-development-history` §3.1 |
| Bot share (Renovate / autodev) | `cc/15-velocity-and-debt` Part 7 |
| Bug-fix ratio (9 %) | `cc/15-velocity-and-debt` Part 4 |
| Bus factor (RISK-001) | `cc/14-architectural-decisions` RISK-001, `cc/15-velocity-and-debt` Part 2 |

## C
| Topic | Chapter(s) |
|---|---|
| Caching (Redis) | `mod/platform/task`, `cc/14-architectural-decisions` ADR-010 |
| Canary endpoint (`/greeting`) | `mod/features/greeting` |
| Capacity (instance / pool sizing) | `cc/11-metrics-catalog` Part 6, `cc/14-architectural-decisions` ADR-011 |
| Circuit breaker | — (gap; mesh egress retries cover partially) |
| CloudWatch | `cc/11-metrics-catalog` Part 8 |
| Commits per month | `cc/15-velocity-and-debt` Part 1 |
| Compass (`compass.yaml`) | — (does NOT exist; recorded in `cc/11-metrics-catalog` Part 5) |
| Competitive landscape | `cc/10-vision-and-strategy` Part 6 |
| Concurrency tuning | `cc/11-metrics-catalog` Part 6, `cc/12-optimization-playbook` Levers 2.2/3.1 |
| Conditional beans | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |
| `continuous-verification.yml` | — (does NOT exist; `cc/11-metrics-catalog` Part 5) |
| Contributor distribution | `cc/15-velocity-and-debt` Part 2 |
| Controllers (REST) | `SYMBOL_INDEX.md` §1 |
| Coroutine context propagation | `cc/03-request-context-and-mdc`, `mod/platform/utility` |
| CORS / security headers | — (gap; SLAuth + Micros gateway handle) |
| Cross-lever interaction matrix | `cc/12-optimization-playbook` Part 6 |

## D
| Topic | Chapter(s) |
|---|---|
| `DataWorkspaceType` | `mod/platform/context` |
| Dependencies (egress) | `cc/11-metrics-catalog` Part 7 |
| Deploy (Nebulae / Spinnaker) | `cc/09-deployment-and-config` |
| Development history (narrative) | `cc/02-development-history` |
| Development history (catalog) | `cc/13-full-history-catalog` |
| `DispatcherMonitor` | `mod/platform/utility` |
| DLQ (Dead-Letter Queue) | `cc/06-async-tasks-and-sqs`, `cc/11-metrics-catalog` Part 4 |
| Docker / `Dockerfile` | `cc/09-deployment-and-config`, `cc/15-velocity-and-debt` Part 5 |

## E
| Topic | Chapter(s) |
|---|---|
| `ERS_CREATE` (NOT a `MetricKey`) | `cc/11-metrics-catalog` Part 1 (note about `ResultMetricBase`) |
| Egress timeouts | `cc/11-metrics-catalog` Part 7 |
| Environment type (LOCAL/STAGING/PROD) | `mod/platform/config`, `cc/14-architectural-decisions` ADR-007 |
| Error handling | partial — `cc/05-observability-and-metrics`, `mod/platform/client`; **no dedicated chapter** |
| `ExecutorServiceMetrics` | `mod/platform/config`, `cc/11-metrics-catalog` Part 6 |
| `Experience` (enum) | `mod/platform/context` |

## F
| Topic | Chapter(s) |
|---|---|
| Feature flags (Statsig) | `cc/04-feature-flags`, `mod/platform/featuregate`, `cc/14-architectural-decisions` ADR-006 |
| FIFO queue (potential migration) | `cc/12-optimization-playbook` Lever 3.3 |
| First commit date (2025-11-10) | `cc/13-full-history-catalog` Part 1 |
| First production deploy (PR #25) | `cc/13-full-history-catalog` Part 5 |
| FY26 H2 OKR | `cc/01-business-and-technical-goals` Part 1 |
| FY27+ direction | `cc/10-vision-and-strategy` Part 3 |

## G
| Topic | Chapter(s) |
|---|---|
| GDPR / data deletion | — (gap; no PII persisted today) |
| Glean (competitor) | `cc/10-vision-and-strategy` Part 6 |
| Glossary | `arch/00-glossary` |
| Graceful shutdown | — (gap; Spring Boot defaults) |

## H
| Topic | Chapter(s) |
|---|---|
| Health checks (`/healthcheck`, `/deepcheck`) | `mod/platform/config` (anonymous-paths bean), `cc/08-auth-and-tenant` |
| Heap (JVM) sizing | `cc/11-metrics-catalog` Part 6 |
| `HistogramBucket` / `HistogramMetric` | `cc/11-metrics-catalog` Parts 1–2 |

## I
| Topic | Chapter(s) |
|---|---|
| `IdGatekeeper` (service) | `mod/platform/client`, `cc/11-metrics-catalog` Part 7 |
| Idempotency convention | `cc/12-optimization-playbook` Lever 4.2 |
| Inflection points (history) | `cc/15-velocity-and-debt` Part 10 |
| Integration tests | `cc/13-full-history-catalog` (PR #101) |
| Interceptor chain (order 1, 2) | `mod/platform/interceptor`, `arch/02-request-lifecycle` |

## J
| Topic | Chapter(s) |
|---|---|
| Jackson polymorphism | `cc/06-async-tasks-and-sqs`, `mod/platform/task` |
| Jira tickets (AIX) | `cc/13-full-history-catalog` Part 4 |
| JVM thread / heap dump | — (gap; go/micros-runbook) |

## K
| Topic | Chapter(s) |
|---|---|
| Kafka (NOT used; SQS chosen) | `cc/14-architectural-decisions` ADR-002 |
| KPIs (acceptance/dismiss/Fans) | `cc/01-business-and-technical-goals` Part 4, `cc/10-vision-and-strategy` Part 4 |

## L
| Topic | Chapter(s) |
|---|---|
| `LaasLogger` / `LaasLoggerFactory` | `mod/platform/logging`, `cc/14-architectural-decisions` ADR-009 |
| Latency optimisation | `cc/12-optimization-playbook` Part 2 |
| Live OKR progress | `cc/01-business-and-technical-goals` (note: NOT retrievable), `AGENTS.md` §4 |
| Load testing | — (gap) |
| `LoggingContext` / `LoggingContextImpl` | `cc/03-request-context-and-mdc`, `mod/platform/requestcontext` |
| LongRun worker pool | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |

## M
| Topic | Chapter(s) |
|---|---|
| `MaxRAMPercentage=25.0` | `cc/11-metrics-catalog` Part 6 |
| `MaxReceiveCount` | `cc/11-metrics-catalog` Part 6, `cc/12-optimization-playbook` Lever 4.1 |
| MCP (Model Context Protocol) | `cc/07-ai-gateway-and-stratus`, `cc/14-architectural-decisions` ADR-005 |
| MDC (Mapped Diagnostic Context) | `cc/03-request-context-and-mdc`, `mod/platform/logging` |
| Memory profiling | — (gap) |
| `MessageQueueConsumerMiddleware` | `mod/platform/sqs`, `cc/03-request-context-and-mdc` |
| `MetricKey` enum (7 entries verified) | `cc/11-metrics-catalog` Part 1, `mod/platform/service-metric` |
| `MetricsService` API | `mod/platform/service-metric`, `cc/05-observability-and-metrics` |
| Micrometer | `cc/05-observability-and-metrics`, `mod/platform/service-metric`, `cc/11-metrics-catalog` |
| Micros (Atlassian platform) | `cc/09-deployment-and-config`, `arch/00-glossary` |
| `MicrosEnvironmentType` (enum) | `mod/platform/config`, `cc/14-architectural-decisions` ADR-007 |
| `MICROS_GROUP` env var | `mod/platform/config`, `cc/09-deployment-and-config` |
| Microsoft Copilot (competitor) | `cc/10-vision-and-strategy` Part 6 |
| Module catalog | `arch/03-module-catalog` |
| `MvcSecurityConfig` | `mod/platform/config`, `cc/08-auth-and-tenant` |

## N
| Topic | Chapter(s) |
|---|---|
| Nebulae | `cc/09-deployment-and-config` |
| `NoopLogger` | `mod/platform/logging` |
| Nudge (feature) | `mod/features/nudge`, `mod/nudge/nudge-throttle` |
| `NudgeType` | `mod/features/nudge` |

## O
| Topic | Chapter(s) |
|---|---|
| OKR (FY26 H2: 400K → 1.5M) | `cc/01-business-and-technical-goals` |
| `OnSHWorkerNodeOrLocalCondition` | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |
| `OnLongRunWorkerNodeOrLocalCondition` | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |
| Open vision questions (5) | `cc/10-vision-and-strategy` Part 8 |

## P
| Topic | Chapter(s) |
|---|---|
| p95 latency optimisation | `cc/12-optimization-playbook` Part 2 |
| `PermanentFeatureGates` | `mod/platform/featuregate` |
| POCO policy (Sauron) | `arch/03-module-catalog` §security |
| `PROACTIVE_HISTOGRAM_BUCKETS` | `cc/11-metrics-catalog` Part 2 |
| `proactive-ai.` metric prefix | `mod/platform/config`, `cc/05-observability-and-metrics` |
| Process gaps (no-ticket / declined / reverted PRs) | `cc/13-full-history-catalog` Part 7 |
| `Product` (enum) | `mod/platform/context` |
| First production deploy (AIX-2863) | `cc/13-full-history-catalog` Part 5 |

## R
| Topic | Chapter(s) |
|---|---|
| Rate limiting (per tenant/user) | — (gap; nudge throttle is related but different) |
| Redis (Valkey 7.x) | `cc/14-architectural-decisions` ADR-010, `cc/11-metrics-catalog` Part 4 |
| Renovate (bot) | `cc/15-velocity-and-debt` Parts 2 + 7 |
| Reproducibility commands | `cc/15-velocity-and-debt` Part 12, `AGENTS.md` §5 |
| Request context | `cc/03-request-context-and-mdc`, `mod/platform/requestcontext` |
| Request lifecycle (sync + async) | `arch/02-request-lifecycle` |
| `RequestContextInterceptor` | `mod/platform/interceptor` |
| Retry policy (5xx + 429) | `cc/11-metrics-catalog` Part 7, `cc/12-optimization-playbook` Lever 4.1 |
| Reverted PRs | `cc/13-full-history-catalog` Part 7 |
| Risk register | `cc/10-vision-and-strategy` Part 7, `cc/14-architectural-decisions` RISK-001 |
| Rovo Insights (feature) | `mod/features/rovo-insights`, `mod/rovo-insights/index` |
| Runbook (TBD on every alarm) | `cc/11-metrics-catalog` Part 4, `cc/14-architectural-decisions` ADR-012 |

## S
| Topic | Chapter(s) |
|---|---|
| `service-descriptor.sd.yml` | `cc/11-metrics-catalog` Parts 4–7, `cc/09-deployment-and-config` |
| SHWorkers worker pool | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |
| SignalFx | `cc/05-observability-and-metrics`, `cc/11-metrics-catalog` Part 8 |
| Single-author concentration | `cc/15-velocity-and-debt` Part 2, `cc/14-architectural-decisions` RISK-001 |
| Sizing (instance / pool) | `cc/11-metrics-catalog` Part 6 |
| SLAuth | `cc/08-auth-and-tenant`, `mod/platform/client` |
| SLO/SLI registration (NONE today) | `cc/11-metrics-catalog` Part 5 |
| Spinnaker | `cc/09-deployment-and-config` |
| Splunk | `cc/05-observability-and-metrics`, `cc/11-metrics-catalog` Part 8 |
| Spring Boot 7.10 | `arch/01-architecture-overview` |
| SQS consumer concurrency | `cc/11-metrics-catalog` Part 6, `cc/12-optimization-playbook` Lever 3.1 |
| Statsig SDK | `cc/04-feature-flags`, `mod/platform/featuregate`, `cc/14-architectural-decisions` ADR-006 |
| Stratus agents | `cc/07-ai-gateway-and-stratus`, `mod/platform/stratus` |
| StreamHub | `cc/05-observability-and-metrics`, `mod/platform/sqs` |
| `STREAMHUB_EVENT_*` metric keys | `cc/11-metrics-catalog` Part 1 |

## T
| Topic | Chapter(s) |
|---|---|
| t3a.medium (instance type) | `cc/11-metrics-catalog` Part 6, `cc/14-architectural-decisions` ADR-011 |
| TAP (throttle traits) | `mod/features/nudge`, `cc/12-optimization-playbook` Lever 1.2 |
| `TcsService` | `mod/platform/utility` |
| Tenant context | `mod/platform/context`, `cc/08-auth-and-tenant` |
| `TENANT_CONTEXT_BUILD_*` (WIRED, not LIVE) | `cc/11-metrics-catalog` Part 1 |
| Test : source ratio (27.1 %) | `cc/15-velocity-and-debt` Part 6 |
| Thread-pool sizing | `cc/11-metrics-catalog` Part 6, `mod/platform/config` |
| Three-horizon view | `cc/10-vision-and-strategy` Part 3 |
| Throughput optimisation | `cc/12-optimization-playbook` Part 3 |
| TLS / certificates | — (gap; mesh handles) |
| Tome (alarm priority routing) | `cc/11-metrics-catalog` Part 8 |
| Tool discovery (MCP) | `cc/07-ai-gateway-and-stratus`, `cc/14-architectural-decisions` ADR-005 |

## U
| Topic | Chapter(s) |
|---|---|
| `UseCase` (enum) | `mod/platform/context` |
| `User` / `UserImpl` | `mod/platform/utility` |
| `UserContextInterceptor` | `mod/platform/interceptor`, `cc/08-auth-and-tenant` |
| `User-Context` header | `cc/08-auth-and-tenant`, `mod/platform/interceptor` |

## V
| Topic | Chapter(s) |
|---|---|
| Velocity analytics | `cc/15-velocity-and-debt` |
| Vision (FY26→FY28) | `cc/10-vision-and-strategy` |
| Visibility extension (PR #103) | `cc/14-architectural-decisions` ADR-004, `mod/platform/task` |
| `VisibilityExtendingSQSQueueConsumer` | `mod/platform/task` |
| `VisibilityTimeout` (per queue) | `cc/11-metrics-catalog` Part 6 |

## W
| Topic | Chapter(s) |
|---|---|
| Walking tour | `ov/02-architectural-narrative` |
| WebServer pool | `mod/platform/config`, `cc/09-deployment-and-config` |
| `WebMvcConfiguration` | `mod/platform/config` |
| `WithUGCLogger` | `mod/platform/logging` |
| Worker groups (3) | `mod/platform/config`, `cc/14-architectural-decisions` ADR-001 |

## X / Y / Z
| Topic | Chapter(s) |
|---|---|
| `X-Forwarded-Host`/`-For` | `mod/platform/utility`, `mod/platform/interceptor` |
| `X-Slauth-Audience`/`-Egress` | `mod/platform/client` |

---

## Known gaps (topics NO chapter covers)

* Audit logging
* Circuit breaker pattern
* CORS / security headers
* GDPR / data deletion
* Graceful shutdown
* JVM heap / thread dump procedure
* Load testing
* Memory profiling
* Per-endpoint p95/p99 dashboard URLs
* Rate limiting (per tenant / per user)
* TLS / certificate management
* Live OKR progress %
* Runbook URLs (every alarm `Runbook: TBD`)

If your problem is one of these, **don't waste cycles searching this docset** — see `AGENTS.md` §4.

## Topics covered in MULTIPLE chapters by design

When a topic needs depth in multiple places, the **primary owner** is named first; secondaries provide context. Example: "Async-task framework" is owned by `cc/06-async-tasks-and-sqs` (the concept) but is implemented in `mod/platform/task` (the code) and discussed historically in `cc/14-architectural-decisions` ADRs 2–4. This is **intentional layering**: concept → implementation → decision-history. It is **not** redundancy.
