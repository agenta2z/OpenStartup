# Evidence Index — Citation Table

> Every claim in `00_INDEX.md`, `01_SYSTEM_MAP.md`, `02_OPERATIONAL_SIGNALS.md`, `03_OPPORTUNITY_REPORT.md` should be traceable here.

## A. SignalFx Detector Files (Terraform IaC under `operations/terraform/modules/`)

| File | Detector(s) | Verified |
|---|---|---|
| `foundation/detectors/tomcat_thread_exhaustion.tf` | tomcat saturation 50%/75% | ✅ |
| `foundation/detectors/threadpool_exhaustion.tf` | async API threadpool 75%/90% | ✅ |
| `foundation/detectors/jvm_threads_utilization.tf` | JVM thread util | ✅ |
| `foundation/detectors/mcp_client_errors.tf` | initialize/list_tools (disabled), call_tool (95%) | ✅ |
| `foundation/detectors/streaming_client_disconnect.tf` | SSE timeshift +40% | ✅ |
| `foundation/detectors/ai_gateway_client_errors.tf` | 4xx/5xx 99.5% by provider/llm_call_mode | ✅ |
| `foundation/detectors/rovo_chat_reliability.tf` | Customer 99.5%, Hello 99.5%, Deep Research 97% | ✅ |
| `foundation/detectors/rovo_agents_reliability.tf` | Customer/Hello/Resumption 99% | ✅ |
| `foundation/detectors/downstream_rate_limiting.tf` | id-gatekeeper, ERS, TCS, assistance-service, responsible-ai 429 burn | ✅ |
| `foundation/detectors/heartbeat_availability.tf` | 99.99% pollinator c68b6eee-... | ✅ |
| `foundation/detectors/redis_stream.tf` | streaming_task write/read 99.5% | ✅ |
| `foundation/detectors/feature_gate_reliability.tf` | Switcheroo FF reliability | ✅ |
| `foundation/detectors/convo_ai_zero_traffic.tf` | <1 req/30min → page (PIR-29582) | ✅ |
| `foundation/detectors/service_proxy_dependencies.tf` | (proxied deps) | ✅ |
| `foundation/detectors/endpoint_errors.tf` | per-endpoint reliability burn (many disabled) | ✅ |
| `foundation/detectors/endpoint_latency.tf` | per-endpoint latency burn (many disabled) | ✅ |
| `foundation/detectors/elb_errors.tf` | ELB reliability 99.90%/99.00% | ✅ |
| `foundation/detectors/elb_latency.tf` | ELB latency | ✅ |
| `foundation/detectors/logging_quota.tf` | Splunk logging quota dropped (early/immediate) | ✅ |
| `foundation/detectors/orphaned_blob_cleanup.tf` | (cleanup detector) | ✅ |
| `foundation/detectors/tenant_context_errors.tf` | (matches TenantContextRunnerImpl bug class) | ✅ |
| `foundation/detectors/rollout_service_alerts.tf` | (rollout pipeline) | ✅ |
| `foundation/detectors/skill_error.tf` | skill execution errors | ✅ |
| `foundation/detectors/agg_client_errors.tf` | AGG client error rates | ✅ |
| `foundation/detectors/integrations_service_errors.tf` | (3P integrations) | ✅ |
| `rovo/detectors/rovo_agents_performance.tf` | TTFB 60s @ 90%, TTLB 40s @ 90% | ✅ |
| `rovo/detectors/streaming_latency.tf` | message_create 10s @ 90%, invoke_agent 20s @ 98% (DISABLED) | ✅ |
| `rovo/detectors/streaming_errors.tf` | message_create 98%, invoke_agent 99.5% (DISABLED) | ✅ |
| `rovo/detectors/endpoint_latency.tf` | /api/rovo/v1/* latency | ✅ |
| `rovo/detectors/endpoint_errors.tf` | /api/rovo/v1/* errors | ✅ |
| `rovo/detectors/forge_endpoint_latency.tf` | forge.get-extensions 2000ms prod / 5000ms staging | ✅ |
| `rovo/detectors/forge_endpoint_errors.tf` | forge.get-extensions errors | ✅ |
| `rovo/detectors/rovo_chat_async_tasks.tf` | async tasks submit 99.99% | ✅ |
| `convo-ai-platform/detectors/jira_jql_debug.tf` | /api/v1/plugin/execute 99% lat @ 10s (Gravity-owned, low_pri) | ✅ |

## B. Confluence Pages (verified via CQL on `gai` and `CONVAI` spaces)

| Page ID | Title | Purpose |
|---|---|---|
| 6980681738 | HOT Incident Root-Cause Analysis (Feb 6 – May 6, 2026) | **PRIMARY SOURCE** — 18 HOTs, 7 cross-cutting recommendations |
| 6192570939 | Runbook: Convo-ai Tomcat busy threads exhaustion | HOT-301423 procedure |
| 6192606761 | Runbook: Convo-ai Threadpool Exhaustion | Sister to above |
| 6325571921 | Runbook: Convo-ai Streaming Client Disconnections | SSE timeshift detector |
| 6105378875 | Runbook: Convo-ai MCP Alerts | (mostly disabled detectors) |
| 6265841127 | Runbook: AI Gateway Client Failure Rate | 4xx/5xx |
| 6144691252 | Runbook: Rovo Chat / Deep Research High Error Rate | 99.5%/97% |
| 6453133435 | Runbook: Convo-ai Async Tasks Infra Submit Error Burn | 99.99% |
| 6330551632 | Runbook: Zero Traffic Alert | PIR-29582 |
| 6186191509 | Runbook: convo-ai Rovo Agents BE Detectors Debugging | TTFB/TTLB |
| 4302911299 | CONVAI — On Burn Rate Detectors | Detector philosophy |
| 3506389920 | CONVAI — On-call SLOs (WIP) | Referenced in heartbeat detector |
| (multiple) | Confluence Search Provider Alert, Sandbox Create Reliability, Deploy Hotfix, Blocking/Unblocking Pipelines, Agents Runbooks, Block account, Rollback Traffic, Xping × 6, HOT Handbook, External URL Access | Operational runbooks |

## C. Jira HOT Tickets (18 from RCA + follow-ups)

| Ticket | Summary | Date | Category |
|---|---|---|---|
| HOT-300352 | Convo AI activate failing — 722 CP workflows | Mar 3 | Deployment regression |
| HOT-300438 | Streaming broken (coroutinisation PR-21668) | Mar 4-5 | Deployment + MDC/suspend |
| HOT-300395 | Concise Summary streaming broken (same family) | Mar 6-8 | Same |
| HOT-126912 | Permission check blocked batch eval | Mar 11 | Deployment regression |
| HOT-301898 | Solution Architect tool failed (number type missing) | Apr 30 | Deployment + schema |
| (no-Jira) | Tomcat threads exhausted (TCS sync) | Feb 3-9 | Thread starvation |
| HOT-300449 | 164 threads blocked / reactor deadlock | Mar 7-9 | Thread starvation |
| HOT-300485 / -300504 / -300517 | Tomcat exhaustion family | Mar 10-17 | Thread starvation |
| HOT-300655 | Disk + memory exhaustion | Mar 19 | Capacity |
| HOT-300681 | SEV1 sharp reliability drop | Mar 20-26 | Thread starvation |
| HOT-301151 / -301367 / -301423 | Latency spikes | Apr | Thread starvation |
| HOT-300215 | AI GW DDOS 100k/min from ai-mate-glazer | Feb 24 | Upstream |
| HOT-300710 | SAIN + Rovo Chat 504 (ai-3p-connector) | Mar 23-26 | Upstream (SEV1) |
| HOT-300316 | Multiple AI GW 4xx; Gemini fallback | Feb 24-Mar 3 | Upstream/LLM |
| HOT-300918 / HOT-301437 | 80M TPM cap exceeded | Apr 2 / Apr 16 | Upstream/LLM |
| HOT-301531 | GPT-5.2 branching complexity | Apr | Upstream/LLM |
| (no-Jira) | Gemini 3 Flash schema drift | Apr 29-May 5 | Upstream/LLM |
| HOT-300597 / -300989 / -301572 | MDC/baggage loss family | Mar-Apr | Context propagation |
| HOT-302069 / -302111 / -302118 | "Please flip a switch" | May | FF noise |
| HOT-300753 | Hotfix pipeline broken | Mar 25 | Process |
| HOT-301801 | FE flag misrouted | Apr-May | FF noise |
| HOT-302076 | Single-error auto-HOT | (recent) | Pollinator noise |
| HOT-301437 / -301585 / -301839 / -300961 | Auto-HOTs no owner | various | Ownership gap |
| HOT-301481 | Incident pipeline triggering/cancelling | Apr 15-21 | Process |
| INC-1149 | CUDA runtime crash teamserve (22k 500s) | (recent) | External |
| GAPF-1743 | Rate limiting added for convo-ai | May 2026 | Follow-up to HOT-301423 |
| GAPF-1708 | EC2 scaling rules after thread starvation | Apr 2026 | Follow-up |
| FD-188275 | Feature flag to mitigate HOT-301423 | Apr 2026 | Follow-up |
| PIR-29582 | SignalFX metrics outage | (referenced) | Observability |

## D. Code Files (post-2026-05-15 verified by grep/wc)

| File path | LoC | Verified hooks |
|---|---|---|
| `modules/platform/service/service-impl/.../RovoChatService.kt` | ~1500 | concurrentConversations AtomicInteger:207, gauge calls:1075-1192 |
| `modules/platform/agent/agent-runtime/.../MarathonRuntime.kt` | 600+ | executeToolsInParallel:564, takeLast(10):various |
| `modules/foundation/.../AsyncAgentInMemoryJobStore.kt` | 110 → +metric | PR-B #30309 PR'd shutdown-loss metric |
| `modules/platform/service/service-impl/.../ConversationStateManagerImpl.kt` | 138 → +metric | PR-A #30308 PR'd sync_session_public counter |
| `modules/platform/ai-gateway-client/.../AIGatewayClientServiceImpl.kt` | 3,087 | ARC-2 decomp target |
| `modules/platform/llm-service/impl/.../LLMServiceImpl.kt` | 1,831 | ARC-3 decomp target |
| `modules/foundation/observability/.../MetricKey.kt` | 3,252 | Module-local extension migration candidate |
| `modules/platform/.../ContentHydrationService.kt` | 600+ | runSearchHydrationQueries:N, web-Jsoup pool:size 2 |
| `modules/product/rovo/.../Experience.kt` | 1,752 | SVC1 decomp target (PR-F #30313) |
| `modules/platform/llm/anthropic/.../*AnthropicLanguageModelProvider.kt` (4 files) | ~3,900 total | ARC-1 dedup target (PR-I #30316) |
| `modules/foundation/auth/.../TenantContextRunnerImpl.kt` | (LoC tbd) | **ACTIVE BUG** — OPP-01 target |
| `convo-ai-docker-image/.../application.yml` | — | tomcat threads max:300 min-spare:50 (per PR-C #30310 audit); runbook says 200/node |
| `convo-ai.ad.yml` | — | EC2 autoscale min/max; "Temporarily overprovision" (HOT-301423 comment) |
| `modules/foundation/.../MarathonMcpSchemaRedisCache.kt` | — | Lines 36-40 (per PR-E #30312 audit, NOT 29-34 as Sauron claimed) |

## E. Configuration constants surfaced from production runbooks

| Constant | Value | Source |
|---|---|---|
| Tomcat threads per node | 200 | Runbook gai/6192570939 |
| Reactor Netty event loops | 16 | HOT-300449 |
| AI Gateway TPM cap | 80,000,000 | HOT-300918 / HOT-301437 |
| Heimdall asap_issuer (raised) | 100,000 | Feb 3-9 RCA |
| StuckThreadDetectionValve | 120s | Tomcat runbook |
| Heartbeat pollinator UUID | c68b6eee-07b0-4bf0-9992-b54d8bbfc876 | heartbeat_availability.tf |
| Async API min-spare / max | 50 / 300 | application.yml (PR-C audit) |
| Burn-rate 9× steep window | 46m+4m, min 5 fail | locals.tf |

## F. PR Reference Links (the 20 PRs I shipped, for cross-reference)

| PR | Title | Branch | Status |
|---|---|---|---|
| #30308 | PLT-15 silent failure remediation | tchen7/PLT-15-* | merged-ready |
| #30309 | RV3 AsyncAgentInMemoryJobStore deprecation | tchen7/RV3-* | open |
| #30310 | OPS3 Tomcat autoscale revisit | tchen7/OPS3-* | spec + metric key |
| #30311 | ARC-2 AIGatewayClientServiceImpl decomp | tchen7/ARC-2-* | spec + metric key |
| #30312 | AIFC7 MCP cache-key entitlement-hash | tchen7/AIFC7-* | spec + metric key |
| #30313 | SVC1 Experience.kt decomp | tchen7/SVC1-* | spec + metric key |
| #30314 | OPS1 Helm worker dedup | tchen7/OPS1-* | spec + Helm template |
| #30315 | ARC-3 LLMServiceImpl decomp | tchen7/ARC-3-* | spec + metric key |
| #30316 | ARC-1 Anthropic provider dedup | tchen7/ARC-1-* | spec + metric key |
| #30317 | INS1 Insights 6-call batching | tchen7/INS1-* | spec + metric key |
| #30334-#30343 | Round-2 Top-15 plan items | tchen7/* | code + metric keys |

## G. Important caveats & open questions

1. **Page id `3506389920` (On-call SLOs WIP)** is referenced in heartbeat detector but appears NOT to have been indexed in the CQL search — should be located/updated.
2. **`tenant_context_errors.tf` exists but unread** — needs deeper inspection for OPP-01 (this should fire on the very bug class we're proposing to fix).
3. **`agg_client_errors.tf` and `service_proxy_dependencies.tf` exist** — for OPP-02 (per-route AGG CB), the current metric grouping needs inspection to confirm whether per-route circuit-breaker telemetry would even surface.
4. **The 80M TPM cap is for Rovo Chat collectively** — open question whether per-tenant fairness should be in convo-ai (OPP-03) or pushed up into AI Gateway. Should be discussed with AI Gateway team.
5. **`ai-3p-connector` has NO detector in our repo** — implicit dependency. OPP-04 should include adding a `downstream_3p_connector.tf` clone of the existing rate-limit detector template.
6. **`AsyncAgentInMemoryJobStore` data loss has unknown impact volume** — PR-B #30309 added a shutdown-loss counter; need 1 month of data before OPP-15 prioritization is finalized.
7. **The 3,252-line MetricKey.kt** has been growing for years; OPP-13 should include a migration playbook + automation, not just "go split it manually".
8. **Suspend-context lint (OPP-01)** requires inventorying ALL `*Client.kt` suspend methods — quick `grep` will surface the candidate set.
