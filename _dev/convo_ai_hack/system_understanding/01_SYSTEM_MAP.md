# Convo-AI System Map — Topology, SLOs, Observability

> Verified against codebase at `atlassian_packages/conversational-ai-platform` (post-2026-05-15) and Terraform IaC under `operations/terraform/modules/`.

---

## 1. Service Topology — the 5-tier hexagonal architecture

From `code_understanding/architecture/01-architecture-overview.rst` (verified 2026-05-02):

```
┌─────────────────────────────────────────────────────────────────┐
│                  SERVICE TIER (Spring Boot entry)               │
│  convo-ai-docker-image • convo-ai-service-descriptor            │
│  Tomcat: 200 threads/node (per runbook gai/6192570939)          │
│  HTTP/SSE endpoints: /chat/v1/channel*, /api/rovo/v1/chat/*,    │
│                      /api/rovo/v1/agents*, /api/v1/plugin/*,    │
│                      /api/v2/configuration*, /api/v1/goal*,     │
│                      /api/rovo/v2/permissions*, /internal/...   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│           PRODUCT TIER (per-product orchestration)              │
│  rovo • jsm • jira • confluence • teamserve • bitbucket • ...   │
│  Experience.kt (rovo, 1752 LoC) — composite per product         │
│  AsyncAgentInMemoryJobStore (data-loss risk on shutdown)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│         PLATFORM TIER (agent runtime, conversation, tools)      │
│  RovoChatService (1500+ LoC) • MarathonRuntime • ConversationState│
│  AgentMarathon (long-horizon loop) • SimpleLoopWorkflow         │
│  ToolRegistry • MCP client • ContentHydrationService            │
│  AIGatewayClientServiceImpl (3,087 LoC) • LLMServiceImpl (1,831)│
│  4× Anthropic providers (~3,900 LoC total)                      │
│  ProactiveCacheKeyGenerator • CacheFriendlyPromptAssembler      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│        FOUNDATION TIER (auth, observability, persistence)       │
│  TenantContextRunnerImpl ⚠ MDC/suspend bug (HOT-300438 et al)   │
│  MetricsService + MetricKey enum (3,252 lines)                  │
│  CustomObservationConvention • ObservabilityContext             │
│  AsyncTaskRetryPolicy • Switcheroo FeatureGateService           │
│  Redis Stream (write/read SLO 99.5%)                            │
│  ConversationStateManagerImpl (sync_session_public risk)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│            CONTRIB TIER (shared utilities, generated code)      │
│  graphql-gateway generated • protobuf for triton grpc           │
└─────────────────────────────────────────────────────────────────┘
```

**84 Gradle modules total** (verified 2026-05-02).

---

## 2. Critical downstream dependencies (with active rate-limit alerts)

| Downstream | Purpose | RL detector (target) | Recent issue |
|---|---|---|---|
| **AI Gateway** | LLM provider routing | `convo-ai.llm_service_client.call.*` 4xx/5xx 99.5% | HOT-300215 DDOS 100k/min; HOT-300316 Gemini fallback; HOT-300918 / HOT-301437 80M TPM cap |
| **id-gatekeeper** | Identity / auth | Envoy 429 burn 90% | (alerts wired) |
| **ERS (ers-data-archetype)** | Entity Resolution | Envoy 429 burn 90% | (in plan PR #5 W-2 R23) |
| **tenant-context-service (TCS)** | Multi-tenant context | Envoy 429 burn 90% | Feb 3 — blocking sync TCS calls exhausted Tomcat; finished partial async migration |
| **assistance-service** | Agent invocation | Envoy 429 burn 90% | Detectors moved here from convo-ai |
| **responsible-ai-api** | Content moderation | Envoy 429 burn 90% | (active) |
| **ai-3p-connector** | 3P data connectors (SharePoint, Teams, Confluence Cloud) | (no detector found!) | HOT-300710 (Mar 23-26) SEV1 504 outage; amplified by `rovo_chat_control_3p_agent_load` FF |
| **AGG (Atlassian GraphQL Gateway)** | GraphQL federation | (single shared CB — flagged in HOT-300710 PIR) | HOT-300504/485/517 thread-exhaustion family caused by GraphQL not suspending |
| **AI 3P services (Teamserve gRPC)** | 3P AI ops | (none documented) | Apr 7-14 outage |
| **Redis Stream (streaming_task)** | SSE message delivery | Read/write 99.5% | Active SLO |
| **Pollinator (heartbeat)** | Synthetic checks | 99.99% (`check_uuid: c68b6eee-...`) | Active; PIR-29582 |

---

## 3. Production SLO Catalog (extracted from `operations/terraform/`)

### 3.1 Customer-facing SLOs (paged on breach)

| SLO | Target | Latency budget | Detector module | Notes |
|---|---|---|---|---|
| **Rovo Chat reliability — Customer** | 99.5% | — | `rovo_chat_reliability.tf:rovo_chat_error_rate_prod` | Automated HOT required |
| **Rovo Chat reliability — Hello (internal)** | 99.5% | — | `:rovo_chat_hello_error_rate_prod` | Automated HOT required |
| **Rovo Deep Research reliability** | 97% | — | `:rovo_deep_research_error_rate_prod` | Lower target acknowledges DR is less reliable |
| **Rovo Agents — Customer error rate** | 99% | — | `rovo_agents_reliability.tf:rovo_agents_error_rate_prod` | low_volume=10 |
| **Rovo Agents — Hello error rate** | 99% | — | `:rovo_agents_hello_error_rate_prod` | low_volume=200 (weekend dip protection) |
| **Rovo Agents — Resumption error rate** | 99% | — | `:rovo_agents_resumption_error_rate_prod` | Separate detector for tool-confirm flows |
| **Streaming message_create latency** | 90% | 10s | `streaming_latency.tf:streaming_message_create_latency_burn_rate` | low-pri only |
| **Streaming message_create reliability** | 98% | — | `streaming_errors.tf:streaming_message_create_reliability_burn_rate` | HOT-paging |
| **Streaming invoke_agent latency** | 98% | 20s | `:streaming_invoke_agent_latency_burn_rate` | DISABLED (moved to assistance-service) |
| **TTFB (Agent Stream)** | 90% | 60s | `rovo_agents_performance.tf:rovo_agents_ttfb_latency_prod` | 60-second budget is HUGE |
| **TTLB (Agent Stream)** | 90% | 40s | `:rovo_agents_ttlb_latency_prod` | Below TTFB — interpretation: time-to-last after first byte |
| **ELB availability** | 99.90% prod / 99.00% staging | — | `elb_errors.tf:elb_reliability_burn_rate_prod` | Active |
| **Heartbeat availability** | **99.99%** | — | `heartbeat_availability.tf:heartbeat_availability_prod` | Pollinator `c68b6eee-07b0-4bf0-9992-b54d8bbfc876`; AutoHOT |
| **Async tasks submit reliability** | **99.99%** | — | `async-tasks.tf:async_tasks_submit_reliability` | 4-nines bar (very high!) |

### 3.2 Endpoint-level SLOs

| Endpoint | Reliability target | Latency target | Status |
|---|---|---|---|
| `/api/rovo/v1/chat/conversation*` | 98% | 90% @ 20s | (foundation detector) |
| `/chat/v1/invoke_agent*` | 99.5% rel / 98% lat @ 20s | — | DISABLED — moved to assistance-service |
| `/api/rovo/v1/agents/*` (non-GET) | 99.5% rel / 99% lat @ 5s | — | Active |
| `/api/rovo/v1/agents` (GET) | 97% lat @ 10s | — | DEPRECATED endpoint, Hello has crazy number of agents |
| `/api/v1/plugin*` | 98% rel / 98% lat @ 20s | — | DISABLED |
| `/api/v2/configuration*` | 99.95% rel / 99.5% lat @ 500ms | — | DISABLED |
| `/api/rovo/v2/permissions*` | 99% rel & lat @ 5s | — | DISABLED |
| `/internal/smartlinks/resolver/v1*` | 99.5% rel / 99% lat @ 2s | — | DISABLED |
| `/api/v1/goal*` | 99% rel | — | DISABLED |
| `/api/rovo/v1/chat/conversation/{id}/action` | 98% rel | — | DISABLED |
| `/api/v1/plugin/execute` (JQL debug) | 99% lat @ 10s | — | Active (Gravity-owned, low_pri) |
| `convo-ai.forge.get-extensions` | — | 2000ms (prod) / 5000ms (staging) | Active; min_request_count=1000 prod |

### 3.3 Infrastructure / dependency SLOs

| SLO | Target | Detector |
|---|---|---|
| **AI Gateway client 4xx** | 99.5% | `ai_gateway_client_errors.tf` — group_by [env, provider, llm_call_mode, is_synthetic] |
| **AI Gateway client 5xx** | 99.5% | Same |
| **Tomcat thread saturation** | <50% (minor) / <75% (major) | `tomcat_thread_exhaustion.tf` |
| **Async API Threadpool exhaustion** | <75% (minor) / <90% (major) | `threadpool_exhaustion.tf` |
| **JVM threads utilization** | (varies) | `jvm_threads_utilization.tf` |
| **MCP client_initialize** | 99.95% | `mcp_client_errors.tf` — ⚠ DISABLED ("too many errors") |
| **MCP list_tool** | 99.95% | Same — ⚠ DISABLED |
| **MCP call_tool** | 95% | Same — only one still enabled; group_by [env, integration] |
| **Redis Stream write (streaming_task)** | 99.5% | `redis_stream.tf` |
| **Redis Stream read_latest** | 99.5% | Same |
| **Streaming client disconnect anomaly** | +40% deviation, 1h | `streaming_client_disconnect.tf` (timeshift detector) |
| **Convo-AI zero-traffic** | <1 req for 30 min → page | `convo_ai_zero_traffic.tf` (added after PIR-29582) |
| **Downstream 429 (id-gatekeeper, ERS, TCS, assistance, responsible-ai)** | 90% (2xx ratio) | `downstream_rate_limiting.tf` — Envoy metrics |
| **Logging quota dropped (staging)** | early-warning when staging logs drop at 80% quota | `logging_quota.tf` |
| **Logging quota dropped (prod)** | immediate-warning when prod logs drop | Same |
| **Feature gate reliability** | (varies) | `feature_gate_reliability.tf` |

---

## 4. Burn-rate-detector philosophy

From `operations/terraform/modules/detectors/locals.tf` + Confluence `CONVAI/4302911299 — On Burn Rate Detectors`:

| Target | Steep (Major) | Moderate (Major) | Slow (Minor) |
|---|---|---|---|
| **98%** | 9× burn / 46m + 4m, min 5 fail | 5× burn / 336m + 28m | 1× burn / 4032m + 336m |
| **95%** | 4× burn / 46m + 4m | 2× burn / 336m + 28m | 1× burn / 4032m + 336m |
| **99%+** | (default lib rules) | | |

Burn-rate detectors are the **dominant** alert class — used for ~80% of detectors above. Steep rules fire in **<50 minutes** for major outages; slow rules act as background quality checks.

---

## 5. Observability stack summary

| Layer | System | Coverage |
|---|---|---|
| **Metrics** | SignalFx (via Splunk Terraform provider 9.25.0) | 80+ detectors, 17 Tome SLO modules |
| **Logging** | Splunk `micros_convo-ai` index | Used by Tomcat-thread runbook (StuckThreadDetectionValve query) |
| **Tracing** | (none surfaced in IaC) — `ObservabilityContext` class is internal | Code-level only; no APM tool referenced |
| **Synthetic checks** | Pollinator (`c68b6eee-...` for heartbeat) | 1 main check + ts-checks dir |
| **SLO tracking** | Tome (via Terraform `observability/tome` provider) | 17 product modules (convo_ai, csm_ai, rovo_for_service, cc_ai, GAP foundation, AIFC, ADK extensions, etc.) |
| **Sauron (IaC state)** | `https://sauron.prod.atl-paas.net/terraform/atlassian/conversational-ai-platform` | Single state file for all observability |
| **Paging** | Opsgenie | Team ID via `var.signalfx.team_id`; AIX-team separate ops escalation |
| **Slack ops channels** | `#rovo-agents-ops` (Rovo Agents Backend), JSM-team channel | Per-product routing |
| **Splunk dashboards in repo** | **only 1** (`convo_ai_agent_permissions.xml`) | Dashboards live primarily in SignalFx, not Splunk |
| **Feature flags** | **Switcheroo** (via `AIGatewayFeatureFlags.kt`, `TeamworkFeatureFlags.kt`) | `featureService.checkGateWithLimitedContext()` and `checkGateWithTapTraits()` |
| **Dashboards by product** | Rovo, AIFC, ADK extensions, CSM, GAP foundation, etc. | 14+ dashboard groups |

---

## 6. Key code-level hotspots (verified against post-2026-05-15 checkout)

| Hotspot | LoC | Role | Risk surface |
|---|---|---|---|
| `RovoChatService.kt` | ~1500 | Streaming chat orchestration | concurrentConversations AtomicInteger gauge (lines ~207-1192); SSE response writer |
| `MarathonRuntime.kt` | 600+ | Long-horizon agent loop | `executeToolsInParallel()` at line 564 — already parallel; `takeLast(10)` history truncation |
| `AsyncAgentInMemoryJobStore.kt` | 110 | In-memory async job queue | **Data loss on JVM shutdown** (no persistence); PR-B #30309 added shutdown-loss metric |
| `ConversationStateManagerImpl.kt` | 138 | sync_session_public ERS calls | Silent failure path — PR-A #30308 added counter |
| `AIGatewayClientServiceImpl.kt` | 3,087 | LLM provider routing core | Mostly streaming infra; flagged for ARC-2 decomp |
| `LLMServiceImpl.kt` | 1,831 | LLM call dispatcher | ARC-3 decomp candidate |
| `Experience.kt` | 1,752 | Per-product orchestration composite | SVC1 decomp candidate (PR-F #30313) |
| `MetricKey.kt` | 3,252 | Central metric registry | Massive monolith — module-local extension pattern recommended |
| `ContentHydrationService.kt` | 600+ | Search/hydration aggregation | `runSearchHydrationQueries` exists; web-Jsoup pool size 2 (shared) |
| `4× Anthropic providers` | 3,900 total | Provider impl variations | ARC-1 dedup candidate (PR-I #30316) |
| `Tenant Context propagation` (TenantContextRunnerImpl) | (suspended state — bug HOT-300438) | Multi-tenant safety | ⚠ ACTIVE PRODUCTION BUG |
