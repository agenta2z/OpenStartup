# Operational Signals — Production Truth (Feb 6 – May 18, 2026)

> Source-of-truth: Confluence `gai/6980681738` (HOT RCA Feb 6–May 6, 2026, generated 2026-05-06 by Rovo Dev for @Hajin Kim), 14 weekly oncall logs, 18 HOT tickets, recent Jira ticket sweep, current SignalFx detector states.

---

## A. The 18 HOT incidents — 3-month bird's-eye view

```
Deployment / Code Regression    ████████████████████ 5
Capacity / Thread Starvation    ████████████████ 4
Upstream / LLM Provider         ████████████████ 4
Feature Flag / Config Hygiene   ████████████ 3
Auth / Policy / MDC propagation ████████ 2
Observability / Pollinator      ████ 1
Networking / Infra              ████ 1
Async / Streaming               ████ 1
Data / Schema / ERS Limits      ████ 1 (long tail of singletons)
Misrouted (other team)          (multiple — noise)
```

**Headline:** 78% of HOTs cluster into 3 categories: code regression, thread starvation, upstream LLM. Tactical wins should target these.

---

## B. Individual incident roll-up

### B.1 Deployment / Code Regression (5)

| HOT | Date | Severity | One-line | Lesson |
|---|---|---|---|---|
| **HOT-300352** | Mar 3 | High | PR removed `baseUrl` → 722 CP workflows failed | ITAP tests not run; review didn't catch routing-path break |
| **HOT-300438** | Mar 4-5 | High | Coroutinisation PR-21668 broke streaming for confluence summary | EagerStreamCollectionRule added; **`TenantContextRunnerImpl` bug STILL OPEN** |
| **HOT-300395** | Mar 6-8 | Minor | Same family as -300438 — Concise Summary streaming broken | Same |
| **HOT-126912** | Mar 11 | (Slack) | Permission check change blocked batch eval viewing | Late-stage permissions review gap |
| **HOT-301898** | Apr 30 | High | Schema enum missing `number` type → all Solution Architect calls failed | Tool-definition schema lacks contract test |

### B.2 Capacity / Thread Starvation (4)

| HOT | Date | Severity | One-line | Lesson |
|---|---|---|---|---|
| **Feb 3-9 (no Jira)** | Feb 3-9 | (slack only) | Sync `TcsServiceImpl#getWebSearchAiSettingsForOrgId` exhausted Tomcat across 50 nodes | Async TCS migration started, not finished |
| **HOT-300449** | Mar 7-9 | (in-log) | **164 threads blocked**; only 16 reactor-http-epoll threads → deadlock + 502s | Avoid blocking inside suspend; `resolveOrgIdSafely` had hidden runBlocking |
| **HOT-300485 / -300504 / -300517** | Mar 10-17 | (dups) | Tomcat exhaustion family — tenantContext + GraphQL not suspending → PR-22983 | Same family as -300449; still open: more endpoints need suspend cleanup |
| **HOT-300655** | Mar 19 | High | Disk + memory exhaustion (organic growth) → unhealthy hosts → P2 | Capacity planning gap; needs auto-scale rules update |
| **HOT-300681** | Mar 20-26 | **SEV1** | Sharp reliability drop + thread starvation | Combination of above |
| **HOT-301151 / -301367 / -301423** | Apr | Various | Latency spikes from thread starvation | Tomcat exhaustion runbook + scale-first ordering proposed |

### B.3 Upstream / Dependency / LLM Provider (4)

| HOT | Date | Severity | One-line | Lesson |
|---|---|---|---|---|
| **HOT-300215** | Feb 24 | High | AI Gateway DDOS — 100k req/min (10× normal) from `ai-mate-glazer` | Upstream caller misbehaviour; we got collateral damage |
| **HOT-300710** | Mar 23-26 | **SEV1** | `ai-3p-connector` 504 → SAIN + Rovo Chat unknown error; `rovo_chat_control_3p_agent_load` FF amplified | Need cache for `/api/v1/third-party-configuration/connected-data-sources` + 3p agent graceful degradation |
| **HOT-300316** | Feb 24-Mar 3 | High | AI GW 4xx — Gemini fallback; 429s on Atlassian hosted Haiku | Fallback logic worked; no customer impact — proof that fallback patterns help |
| **HOT-300918 / HOT-301437** | Apr 2 / Apr 16 | High | Rovo Chat exceeded 80M TPM rate limit (multiple times) | Need TPM pre-flight + token-bucket smoothing |
| **HOT-301531** | (Apr) | (in-log) | GPT-5.2 branching complexity bumped failure modes | Per-model fallback strategies need explicit testing |
| **Apr 29-May 5** | — | (in-log) | Gemini 3 Flash schema drift | Schema-validation gap for streaming providers |

### B.4 Feature Flag / Configuration Hygiene (3)

| HOT | Date | Notes |
|---|---|---|
| **HOT-302069, -302111, -302118** | (May) | "Please flip a switch" / FE flag misrouted to convo-ai |
| **HOT-300753** | Mar 25 | Hotfix pipeline failed; rollback ordering issue |
| **HOT-301801** | (Apr-May) | FE flag noise |

### B.5 Auth / Policy / Context Propagation (2)

| HOT | Date | One-line |
|---|---|---|
| **HOT-300597, -300989, -301572** | Mar-Apr | All trace back to `TenantContextRunnerImpl` MDC/baggage loss — same family as -300438 |

### B.6 Observability / Pollinator / Auto-HOT noise

| HOT | Issue | Lesson |
|---|---|---|
| **PIR-29582** | SignalFX metrics disappeared from ConvAI Platform | Zero-traffic detector added in response |
| **HOT-302076** | Single-error auto-HOT triggered | Tune heartbeat SLO threshold |
| **HOT-301437 / -301585 / -301839 / -300961 / -302076** | Auto-HOTs lacking PIR owners | Process gap |

### B.7 Networking / Infra

| HOT | Date | Notes |
|---|---|---|
| **HOT-300710 (also above)** | Mar 23 | `ai-3p-connector` Redis scaling needed by that team |

### B.8 Async / Streaming / Consumer

| HOT | Notes |
|---|---|
| **Various** | Async/streaming consumer failures (CUDA crash INC-1149 surfaced 22k 500 errors on teamserve) |

### B.9 Misrouted HOTs (lots of these)

These got opened against convo-ai but actually belonged to Agents / Remix / Jira AI / App Switcher / Rovo Dev CLI / etc. **Process gap** — needs better service-picker hints in go/hot.

---

## C. The 7 cross-cutting recommendations (from the RCA's own conclusion)

### C.1 ⚠ The MDC / suspend / context-propagation footgun keeps biting

**Evidence:** HOT-300438, HOT-300449, HOT-300504/-300485/-300517, HOT-300597, HOT-300989, HOT-301572

**Quote (RCA):** *"The core bug in `TenantContextRunnerImpl` persists. Any endpoint converted to `withTenantContextSuspend` will crash. To unblock suspend migrations, `addTenantContext` must move inside the coroutine context carrying `RequestAttributes`."*

**Recommendation:** Treat suspend-conversion of any TCS / AGG / GraphQL client call as an **explicit risk class**. Require a propagation regression test, not just code review. Consider a **DI-time lint** that fails the build if a new suspend method exists in `*Client` without a context-propagation companion test.

→ **Opportunity #1 in `03_OPPORTUNITY_REPORT.md`**

### C.2 Thread starvation is recurring — the team is "playing whack-a-mole"

**Evidence:** Feb 3 Tomcat, HOT-300449 (16 reactor-http-epoll threads deadlocked), #hot-300485/-300504/-300517, HOT-300681 SEV1, HOT-301151/-301367/-301423, Apr 9-14 4pm JVM pattern

**Quote:** *"Synchronous calls inside reactor / runBlockingWithContext, single shared AGG circuit breaker, 16k+ deprecated agents endpoint, organic disk growth."*

**Recommendation:** Finish move to async TCS client; **split AGG circuit breaker per route**; add staging thread-saturation alarm; adopt "scaling-first then hotfix" runbook ordering already proposed in HOT-301151.

→ **Opportunities #2, #5, #9**

### C.3 Lack of graceful degradation against upstream LLM / 3P services

**Evidence:** HOT-300710, Apr 7-14 Teamserve gRPC, HOT-300918/-301437 OpenAI 80M TPM, Apr 29-May 5 Gemini 3 Flash schema drift, HOT-301531 GPT-5.2 branching, HOT-300316 AI GW 4xx fallback

**Quote:** *"Convo-ai amplifies upstream issues because there is no consistent circuit-breaker / cache / fallback pattern; FF rollouts (`rovo_chat_control_3p_agent_load`) increased coupling without bulkheads."*

**Recommendation:** Establish "graceful degradation pattern for Rovo Chat"; prioritize **circuit breakers for the gRPC client** per Corey Rogers' suggestion; add caches for `/v1/third-party-configuration/connected-data-sources` (NavX work started).

→ **Opportunities #3, #4**

### C.4 Rollback discipline is improving but still slow

**Evidence:**
- Feb 3 PIR: *"Emphasis on revert whenever possible. Rollbacks almost always win in this case."*
- Mar 25 HOT-300753: *"Our hotfix pipeline is too prone to failure, and takes too long. We should prioritize rollback first."*
- Mar 31-Apr 6 HOT-300989: *"builds have been broken for a few days so it has not been able to be rolled out"*
- Apr 15-21 HOT-301481: incident pipeline triggering & cancelling

**Recommendation:** Invest one cycle in fixing the hotfix/incident pipeline. Every multi-day blocker traces back to it. Also add an **"auto-revert candidate" detector** for PRs merged within N hours of a HOT.

→ **Opportunity #6**

### C.5 Feature-flag operations are creating HOT-volume noise

**Evidence:** HOT-302069, HOT-302111, HOT-302118, #300507, HOT-300753, HOT-301801 — many "please flip a switch" or FE-flag-misrouted-to-convo-ai HOTs.

**Recommendation:** Publish a clear "where to file FE / FG-only issues" runbook; document change-freeze MIM workflow; add a service-picker hint at go/hot.

→ **Opportunity #11** (process, not code)

### C.6 Pollinator / observability gaps

**Evidence:**
- Feb 3: *"Invest in a wider suite of pollinator checks → can't keep relying on the single AIFC Pollinator."*
- HOT-300508: *"Implement better pollinators to check GraphQL features."*
- Apr 7-14: *"Why wasn't this tested / caught in staging?"*
- HOT-302076: single-error auto-HOT triggered

**Recommendation:** Broaden pollinator coverage (GraphQL, X-Forwarded-Host on custom domains, suspend-context propagation, Confluence whiteboard SVG output). **Tune the heartbeat SLO** so a single 503 at the LB doesn't auto-page.

→ **Opportunities #7, #10**

### C.7 Auto-HOTs and historical HOTs need ownership

**Evidence:** HOT-300504 left open with no PIR owner; multiple auto-HOTs (HOT-301437, HOT-301585, HOT-301839, HOT-300961, HOT-302076) sparse in the log.

**Recommendation:** Every auto-HOT row in the weekly log should have at least a **PIR-owner field** assigned at on-call handover; otherwise the next on-call inherits ambiguity.

→ **Opportunity #12** (process)

---

## D. SignalFx Detector State — Quality-Debt Signal

### D.1 Detectors currently DISABLED (≈25 of 80)

| Module | Detector | Why disabled (from .tf comments) |
|---|---|---|
| `mcp_client_errors.tf` | `mcp_client_initialize_*` (prod + staging) | "Too many errors and too little traffic at the moment to provide any value" |
| `mcp_client_errors.tf` | `mcp_client_list_tools_*` (prod + staging) | Same |
| `streaming_errors.tf` | `streaming_invoke_agent_reliability_burn_rate` | "Should be moved to assistance-service and owned by Agents" |
| `streaming_latency.tf` | `streaming_invoke_agent_latency_burn_rate` | Same |
| `endpoint_errors.tf` (foundation) | `chat_v1_invoke_agent_reliability_burn_rate`, `api_v1_plugin_reliability_burn_rate`, `api_v2_configuration_reliability_burn_rate`, `api_rovo_v2_permissions_reliability_burn_rate`, `smartlinks_resolver_v1_reliability_burn_rate`, `api_v1_goal_reliability_burn_rate`, `api_rovo_v1_chat_convo_action_reliability_burn_rate` | (`disable_detector = true` hard-coded — no comment) |
| `endpoint_latency.tf` (foundation) | All paired endpoint latency detectors | Same pattern |
| `endpoint_errors.tf` (rovo) | Same pattern | Various |
| Multiple | `disable_detector = var.signalfx.disable_detectors` (toggle) | Used for staged enablement |

**⚠ Why this matters:** Disabled detectors mean **no proactive alerting** on these paths. When something breaks, we discover it via customer reports, not via SignalFx. **This is the silent SRE debt** that compounds.

### D.2 Detectors that EXIST but lack runbook URL

Spot check across detector files reveals several detectors with **no `runbook_url = ...` parameter set**. Each represents a future-3am-paging without a clear "what do I do" page.

### D.3 Detector duplication / dead code

`endpoint_errors.tf` exists in BOTH `modules/detectors/` and `modules/foundation/detectors/` — overlap; some duplicates / dead detectors.

---

## E. Confluence Operational Surface (15 active runbooks)

| Runbook | Page | Why it exists |
|---|---|---|
| Downstream Rate Limiting (Identity, ERS, TCS, AI Gateway, Jira) | gai | 429 handling for 5 critical deps |
| Confluence Search Provider Alert | gai | SAIN failures |
| Atlassian Sandbox Create Reliability | gai | ConvoAI Sandbox creation |
| Deploy a production hotfix | gai | Standard hotfix procedure |
| Blocking/Unblocking Deployment Pipelines | gai | Pause/resume |
| Agents Runbooks (index) | gai | Aggregator |
| Rovo Chat / Deep Research High Error Rate | gai | 6144691252 |
| Block account id from accessing convo-ai | gai | (compliance) |
| Rollback Traffic to Previous Deployment | gai | Instant rollback |
| Tomcat Busy Threads Exhaustion | gai/6192570939 | **HOT-301423 recurring** — see procedure |
| Threadpool Exhaustion | gai/6192606761 | Sister runbook |
| MCP Alerts | gai/6105378875 | (most detectors disabled; runbook stub) |
| AI Gateway Client Failure Rate | gai/6265841127 | 4xx/5xx detector |
| Streaming Client Disconnections | gai/6325571921 | Anomaly detector |
| Xping test alerts (×6) | gai | Synthetic test failures |
| Zero Traffic Alert | gai/6330551632 | PIR-29582 |
| Handle Hot Incidents (HOWTO) | gai | MinOR Handbook |
| External URL Access / Data Exfiltration (Rovo) | gai | PIR-28962 / HOT-122671 cybersecurity |
| Async Tasks Infra Submit Error Burn | gai/6453133435 | 99.99% SLO |

### Postmortems & RCAs

| Page | Coverage |
|---|---|
| HOT Incident RCA (Feb 6 – May 6, 2026) | gai/6980681738 — 14 weeklies, 18 HOTs, 10 categories, 7 cross-cutting recommendations |
| Incident Domain Analysis (Nov-Dec) | Prior 2-month window |
| Rate Limiter Incident | CONVAI — false positive on /agents/v1, 30000 RPM user limit |
| Suggestions to reduce # of incidents | gai — 13+ incidents in past week |

**Gap:** **NO SLO Confluence pages found** via CQL — the SLO definitions live in Terraform IaC only. WIP page `CONVAI/3506389920` referenced in heartbeat detector but not indexed.

---

## F. Capacity / Rate-limit hard numbers (real production reality)

| Limit | Value | Source |
|---|---|---|
| **Tomcat threads / node** | 200 | Runbook gai/6192570939 |
| **Reactor Netty event-loop threads** | 16 | HOT-300449 |
| **AI Gateway TPM cap (Rovo Chat)** | 80,000,000 | HOT-300918 / HOT-301437 |
| **Heimdall rate per asap_issuer** | 60K → raised to 100K | Feb 3-9 RCA |
| **convo-ai async API threadpool** | min-spare 50 / max 300 (application.yml) | PR-C #30310 spec |
| **Tomcat saturation alert** | 50% minor / 75% major | tomcat_thread_exhaustion.tf |
| **Async threadpool saturation alert** | 75% minor / 90% major | threadpool_exhaustion.tf |
| **StuckThreadDetectionValve** | 120s | Tomcat runbook |
| **Pollinator heartbeat low_pri_threshold** | (single 503 can auto-page — flagged as too sensitive) | HOT-302076 |
| **MCP call_tool SLO** | 95% (lowered — "errors from downstream MCP servers are outside our control") | mcp_client_errors.tf |
| **EC2 instance autoscale (convo-ai.ad.yml)** | min: 2-5, max: 10-15 (varies by env) — "Temporarily overprovision" | convo-ai.ad.yml (HOT-301423 comment) |

---

## G. Code Telemetry Inventory (verified via grep)

| Component | Logger calls | Metric emissions | FF gates | Notes |
|---|---|---|---|---|
| `RovoChatService.kt` | ~50 logger.error/warn | ~20+ MetricsService.count/gauge | 10+ checkGate | concurrentConversations gauge already exists |
| `ConversationStateManagerImpl.kt` | 4 logger.error in sync_session_public path | 1 (new — PR-A) | 0 | Silent-failure surface — needs more |
| `MarathonRuntime.kt` | 30+ logger.warn/error | 20+ metrics | Several FFs | Iteration cap, tool exec parallel |
| `AsyncAgentInMemoryJobStore.kt` | 6 logger.warn/error | 1 (new — PR-B) | 0 | Shutdown loss now metered |
| `MarathonMcpClient.kt` and family | Many MCP retries/logger.error | MCP detectors disabled | Tool-FF gated | 3 of 4 prod MCP detectors are off |
| `AIGatewayClientServiceImpl.kt` | Many | Has provider-grouped metrics | Many | 3,087 LoC — primary surface |
| `ContentHydrationService.kt` | Logging present | Has metrics | Several | Web-Jsoup pool size 2 (shared bottleneck) |
| `TenantContextRunnerImpl` | (varies) | (varies) | 0 | **Active bug** — see Cross-cutting #1 |
