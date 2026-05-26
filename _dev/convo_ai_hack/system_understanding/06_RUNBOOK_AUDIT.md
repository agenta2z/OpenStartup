# Runbook Audit — Operational Surface Quality Assessment

> **Methodology:** Fetched 32 Confluence pages from `gai` + `CONVAI` spaces via Atlassian MCP. Extracted last-review dates, owners, Splunk queries, dashboard URLs, and known-stale references.

---

## A. Runbook freshness matrix

| Page | Title | Last Reviewed | Owner | Status | Freshness |
|---|---|---|---|---|---|
| `gai/6192570939` | Convo-ai Tomcat busy threads exhaustion | **2026-01-20** | @Emily Wong (Thanh Tran deactivated) | active | 🟡 3+ months — needs re-review post HOT-301423 |
| `gai/6192606761` | Convo-ai Threadpool Exhaustion | (not listed) | (not listed) | active | 🔴 STALE — agent reported "14 months old, references deprecated Kotlin coroutine monitoring" |
| `gai/6105378875` | MCP Alerts | **2025-11-20** | @Himanshu Asati (DEACTIVATED) | active (alerts DISABLED) | 🔴 **OWNER DEACTIVATED** — 6 months stale; alerts themselves disabled |
| `gai/6144691252` | Rovo Chat / Deep Research High Error Rate | (not listed) | (not listed) | ACTIVE | 🟡 Needs review |
| `gai/6265841127` | AI Gateway Client Failure Rate | **2025-12-30** | @Aakash Barbhaya (DEACTIVATED) | ACTIVE | 🔴 **OWNER DEACTIVATED** — 5 months stale |
| `gai/6325571921` | Streaming Client Disconnections | (not listed) | (not listed) | active | 🟡 Needs review |
| `gai/6330551632` | Zero Traffic Alert | (REVIEW status) | (not listed) | REVIEW | 🟠 Marked REVIEW pending completion |
| `gai/6453133435` | Async Tasks Submit Error Burn | **2026-02-10** | @Jacqueline Zhang | ACTIVE | 🟢 Recent (~3 months) |
| `gai/6186191509` | Rovo Agents BE Detectors Debugging | (not listed) | (not listed) | (not listed) | 🟡 Needs review |
| `CONVAI/4302911299` | Overview (Burn-rate Detectors) | (not listed) | (not listed) | (general doc) | 🟢 Foundational philosophy doc, generally stable |
| `CONVAI/3506389920` | On-call SLOs (WIP) | (no body owner) | (not listed) | **WIP** | 🔴 Marked "WIP" since at least Mar 2024 per agent assessment — should be archived |

---

## B. Per-runbook deep findings (content + freshness + gaps)

### B.1 Tomcat Busy Threads Exhaustion (`gai/6192570939`) 🟡

**Procedure quality:** Good — explicit dashboard URL (`ThreadPool SFX`), threshold (200 threads/node), heap-dump capture instructions linked to `CONVAI/4159979045`.

**Strengths:**
- Concrete numbers: 200 threads/node, 50% minor / 75% major alert thresholds
- Explicit StuckThreadDetectionValve at 120s
- Step-by-step heap-dump procedure

**Gaps:**
- **Last reviewed Jan 20, 2026** — predates HOT-300449 (Mar 7-9, 164 threads blocked), HOT-300485/-300504/-300517 family, HOT-301423 (Apr 16) cluster. **REVIEW OVERDUE.**
- No reference to "scaling-first then hotfix" ordering proposed in HOT-301151 PIR
- Thanh Tran (primary owner) is **deactivated**

**Recommended update:** Add "Scaling-first" section per HOT-301151 PIR; reference HOT-301423 lessons; add per-tenant rate-limit context post-GAPF-1743.

### B.2 Threadpool Exhaustion (`gai/6192606761`) 🔴

**Procedure quality:** Stub-level — only ~6KB. Agent assessment: **"14 months stale; references deprecated Kotlin coroutine monitoring"**.

**Strengths:** Exists.

**Gaps:**
- No owner listed
- No last-review date
- References deprecated monitoring infra
- Detector definitions in IaC (`threadpool_exhaustion.tf`) are more current than the runbook

**Recommended update:** Full rewrite OR consolidate with the Tomcat runbook (they're sibling alerts on similar metrics).

### B.3 MCP Alerts (`gai/6105378875`) 🔴

**Procedure quality:** OK — has clear Splunk query (`micros_convo-ai IntegrationsServiceMcpClientException`), dashboard reference, signal screenshots.

**Strengths:**
- Specific Splunk query
- Lists 3 detector types (initialize / list_tools / call_tool) with UUIDs
- SignalFx dashboard reference

**Gaps:**
- **🔴 Owner @Himanshu Asati DEACTIVATED**
- **🔴 Alerts CURRENTLY DISABLED** ("pending traffic increase and fixes")
- Last reviewed **Nov 20, 2025** = 6 months stale
- Runbook is operational but the underlying detectors don't fire — runbook is effectively dead code

**Recommended action:** Assign new owner; either re-enable detectors (OPP-08) and refresh the runbook, OR mark runbook as "archived pending detector re-enablement".

### B.4 Rovo Chat / Deep Research High Error Rate (`gai/6144691252`) 🟡

**Procedure quality:** Comprehensive — links go/logs/convo-ai (Splunk), describes filter for synthetic/eval traffic.

**Strengths:**
- Explicit Splunk filter: `| spath ctx_is_synthetic | search ctx_is_synthetic=false | spath message | search message!="Metrics latency"`
- Pointers to Bitbucket commit-page for deployment correlation
- Validation steps for metric-bean emission failures

**Gaps:**
- No owner listed
- No last-review date
- Doesn't yet address PIR-300811 (Apr 16) lessons (per-tenant overload)

### B.5 AI Gateway Client Failure Rate (`gai/6265841127`) 🔴

**Procedure quality:** Good — `tag` filtering by provider explained, group-by `provider, llm_call_mode` documented.

**Strengths:**
- Explicit alert names (`Gap Foundation - AI Gateway Client 4xx/5xx`)
- Routing to `#gap-foundation-prod-alerts` Slack
- `ctx_account_id` user-correlation step

**Gaps:**
- **🔴 Owner @Aakash Barbhaya DEACTIVATED**
- Last reviewed **Dec 30, 2025** = 5 months stale
- Doesn't yet address HOT-300918 / HOT-301437 (80M TPM cap) pattern — those incidents would benefit from a "if AI Gateway is rate-limiting your service, see runbook X" cross-link

### B.6 Streaming Client Disconnections (`gai/6325571921`) 🟡

**Procedure quality:** Concise (~5KB). Anomaly detector pattern (timeshift +40%).

**Gaps:** No owner / no review date; doesn't reference HOT-300438 / HOT-300395 streaming-coroutinisation lessons.

### B.7 Zero Traffic Alert (`gai/6330551632`) 🟠

**Procedure quality:** Marked **REVIEW status** — incomplete.

**Gaps:** This runbook was created in response to PIR-29582 (SignalFx metric outage) but is **still in REVIEW**. Needs to be promoted to ACTIVE.

### B.8 Async Tasks Submit Error Burn (`gai/6453133435`) 🟢

**Procedure quality:** EXCELLENT.

**Strengths:**
- **Owner @Jacqueline Zhang (active)**
- Last reviewed **Feb 10, 2026** (freshest of all runbooks)
- Explicit SignalFx dashboard URL with parameters
- Splunk query: `\`micros_convo-ai\` env=prod-east level=ERROR "AsyncStreamingTaskServiceImpl"`
- Specific class + method (`publishMessageWithMetrics`) + Bitbucket file URL
- Specific metric (`convo-ai.async.task.submit.error.count`)
- Field hints (`ctx_experience_id`, `message`)

**This is the gold-standard template for what every runbook should look like.**

### B.9 Rovo Agents BE Detectors Debugging (`gai/6186191509`) 🟡

**Procedure quality:** Good — cross-references TOME SLO `go/rovo-agents-be-slos`.

**Strengths:**
- Full SLO ↔ detector mapping table (Reliability 99% / Deep Research 95% / TTFB 90% / TTLB 90%)
- Splunk query pattern with sort and table fields
- SignalFx dashboard reference

**Gaps:** No owner / no review date.

### B.10 On Burn Rate Detectors (`CONVAI/4302911299`) 🟢

**Procedure quality:** Foundational philosophy doc. Stable.

### B.11 On-call SLOs WIP (`CONVAI/3506389920`) 🔴

**Status:** WIP since Mar 2024. Per agent assessment: should be archived OR finalized.

---

## C. Cross-cutting runbook problems

### C.1 Deactivated owners (2 confirmed, possibly more)

| Runbook | Deactivated owner |
|---|---|
| `gai/6105378875` (MCP Alerts) | @Himanshu Asati |
| `gai/6265841127` (AI Gateway Client Failure) | @Aakash Barbhaya |
| `gai/6192570939` (Tomcat busy threads) | @Thanh Tran (co-owner with @Emily Wong) |

**Implication:** When a 3am page fires for one of these alerts, the auto-tagged "owner" in Opsgenie cannot be contacted. Routing falls back to the on-call rotation — but that's exactly when explicit ownership matters most.

**Recommended action:** Quarterly runbook-ownership audit; auto-fail Confluence runbook if its `Owner` field references a deactivated user.

### C.2 Stale-review backlog

| Bucket | Count |
|---|---|
| 🟢 Reviewed in last 3 months | 1 (Async Tasks - Feb 10) |
| 🟡 Reviewed 3-6 months ago | 4 (Tomcat, MCP, AI GW, …) |
| 🔴 Reviewed >6 months ago or never | 6 (Threadpool, others) |
| 🔴 Owner deactivated | 3 |

**Implication:** Most runbooks predate the Feb 6 – May 6, 2026 incident cluster. The most lesson-rich quarter has not been incorporated into the runbooks themselves.

### C.3 Missing runbooks

Per detector inventory in `01_SYSTEM_MAP.md`, these detectors exist but have **no runbook found** in CQL:

| Detector | Has runbook? |
|---|---|
| `tomcat_thread_exhaustion.tf` | ✅ gai/6192570939 |
| `threadpool_exhaustion.tf` | ✅ gai/6192606761 (stale) |
| `mcp_client_errors.tf` | ✅ gai/6105378875 (stale) |
| `streaming_client_disconnect.tf` | ✅ gai/6325571921 |
| `ai_gateway_client_errors.tf` | ✅ gai/6265841127 (stale) |
| `rovo_chat_reliability.tf` | ✅ gai/6144691252 |
| `rovo_agents_reliability.tf` | ✅ (via gai/6186191509) |
| `downstream_rate_limiting.tf` | ✅ (multiple) |
| `heartbeat_availability.tf` | ❌ **MISSING** |
| `redis_stream.tf` | ❌ **MISSING** |
| `feature_gate_reliability.tf` | ❌ **MISSING** |
| `convo_ai_zero_traffic.tf` | ✅ gai/6330551632 (REVIEW status) |
| `endpoint_errors.tf` (per-endpoint) | ❌ Mostly DISABLED detectors so runbook moot, but the few enabled ones (`/api/v1/plugin/execute`) have no runbook |
| `forge_endpoint_errors.tf` | ❌ **MISSING** |
| `forge_endpoint_latency.tf` | ❌ **MISSING** |
| `logging_quota.tf` | ❌ **MISSING** |
| `agg_client_errors.tf` | ❌ **MISSING** |
| `service_proxy_dependencies.tf` | ❌ **MISSING** |
| `skill_error.tf` | ❌ **MISSING** |
| `tenant_context_errors.tf` | ❌ **MISSING** ← directly tied to OPP-01 |
| `integrations_service_errors.tf` | ❌ **MISSING** |
| `rollout_service_alerts.tf` | ❌ **MISSING** |
| `orphaned_blob_cleanup.tf` | ❌ **MISSING** |

**11+ detectors lack runbooks.** When they fire, the on-call has no explicit "what do I do" page — must derive from detector source code.

**This is OPP-16 (Detector runbook-URL coverage) — confirmed as a real, sizeable gap.**

---

## D. Splunk index + query patterns (extracted from runbooks)

**Index:** `micros_convo-ai`

**Common query patterns observed:**

```spl
# 1. Standard error filter
`micros_convo-ai` env=prod-east level=ERROR "AsyncStreamingTaskServiceImpl"

# 2. Synthetic/eval filter
`micros_convo-ai` 
| spath ctx_is_synthetic 
| search ctx_is_synthetic=false 
| spath message 
| search message!="Metrics latency"

# 3. MCP exception trace
`micros_convo-ai` IntegrationsServiceMcpClientException

# 4. Endpoint-scoped error
`micros_convo-ai` env=prod* level=ERROR ctx_endpoint="<ENDPOINT_NAME>"
| table _time, level, logger, message, request_id, ctx_endpoint, ctx_status_code
| sort -_time

# 5. Tenant-scoped error
`micros_convo-ai` env=prod* level=ERROR ctx_account_id="<ACCOUNT_ID>"
```

**Useful Splunk fields surfaced in runbooks:**
- `ctx_is_synthetic` — filter eval/pollinator traffic
- `ctx_endpoint` — endpoint name
- `ctx_status_code` — HTTP status
- `ctx_experience_id` — multi-call correlation
- `ctx_account_id` — tenant identification
- `request_id` — request-scoped trace
- `level`, `logger`, `message` — standard

**Splunk shortcut URL:** `go/logs/convo-ai`

**Heap-dump procedure runbook:** `CONVAI/4159979045` (referenced from Tomcat runbook)

---

## E. SLO targets per service class (NEW finding — verified from page 6272930943)

From `SLO Uplift impact analysis` (Jan 2, 2026):

| Service type | Target | Rationale (verbatim) |
|---|---|---|
| LLM-dependent (chat/streaming) | **99.9% max** | *"OpenAI's Scale Tier SLA is 99.9% - mathematically impossible to exceed."* |
| Non-LLM (internal operations) | **99.99%** | *"Fully within our control."* |
| Low-traffic + LLM (Deep Research) | **99.5%** | *"Vendor constraint + statistical noise from low volume."* |
| Performance SLOs | **99.9%** | *"Interactive user experience."* |

**Implication:** The current 99.5% Rovo Chat reliability target documented in `rovo_chat_reliability.tf` is **below the documented ceiling of 99.9%**. There's headroom — if OPP-1/2/3/4 land, the SLO target should be tightened to 99.7% or 99.9% as a forcing function.

**TOME dashboard URL pattern:** `https://tome.prod.atl-paas.net/slo/{uuid}`

---

## F. NEW opportunity surfaced by runbook audit

### OPP-19 🔄 Runbook ownership + freshness governance

| Field | Value |
|---|---|
| Type | 🔄 process |
| Impact | 3 |
| Risk | 1 |
| Complexity | 2 (1-2 engineer-weeks) |
| Score | 3 |
| Tier | 🟡 P2 |

**Why:**
- 3 confirmed deactivated runbook owners (Himanshu Asati, Aakash Barbhaya, Thanh Tran)
- 11+ detectors with no runbook
- 6+ runbooks reviewed >6 months ago
- Only 1 runbook reviewed in last 3 months (Async Tasks - the gold standard)

**Concrete proposal:**
1. **Detekt-style lint for runbooks**: scheduled job that scans every `Owner:` field in `gai`-space runbooks and fails if owner is deactivated
2. **Detector-to-runbook coverage check**: scheduled job that asserts every Terraform `signalfx_detector` resource has a `runbook_url` parameter; fails CI if missing
3. **Quarterly review reminder**: auto-create Jira `convo-ai` ticket per runbook every 90 days requesting a review
4. **Apply the "Async Tasks Runbook" template** (gold standard) to the 6 stale runbooks

---

## G. Summary numbers

| Metric | Value |
|---|---|
| Total cached Confluence pages from session | 32 |
| Runbooks reviewed | 11 |
| Runbooks with deactivated owners | 3 |
| Runbooks last-reviewed >3 months ago | 7 |
| Detectors WITHOUT a runbook | 11+ |
| Splunk index used | `micros_convo-ai` |
| Useful Splunk fields surfaced | 7 (`ctx_*` + standard) |
| New opportunity added | OPP-19 (governance) |
