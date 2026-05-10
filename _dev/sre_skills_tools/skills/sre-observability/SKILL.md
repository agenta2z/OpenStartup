---
name: sre-observability
description: >
  Comprehensive domain guidance for an AI Site Reliability Engineer performing observability tasks:
  monitoring system health via Prometheus/Mimir metrics, managing Grafana dashboards and alerts,
  computing SLI/SLO/error budgets, detecting anomalies using statistical methods, coordinating
  incident response via Slack, and generating weekly SLO compliance reports.
labels:
  - sre
  - observability
  - incident-response
  - monitoring
metadata:
  tools:
    - prometheus_query
    - grafana_manage
    - slack_send_message
    - slack_find_channel
    - slack_react
    - slack_pin_message
    - slack_unpin_message
    - slack_get_thread
    - slack_search_messages
    - twg
---

# SRE Observability Skill

## 1. Skill Overview

- **Name**: `sre-observability`
- **Description**: Domain guidance for an AI SRE performing end-to-end observability workflows — from querying metrics and managing dashboards to computing error budgets, detecting anomalies, responding to incidents, and producing weekly compliance reports.
- **Leveraged Tools**:

| Tool | Capability Summary |
|------|-------------------|
| `prometheus_query` | Query Prometheus/Mimir APIs: instant queries, range queries, series/label discovery, metadata. Supports multi-tenant Mimir via `X-Scope-OrgID`. |
| `grafana_manage` | Manage Grafana dashboards (CRUD), annotations, alert rules (provisioning API), folders, and data source proxy queries. |
| `slack_send_message` | Send messages to Slack channels/threads for alert notifications and incident coordination. |
| `slack_find_channel` | Discover Slack channels by name for routing alerts and incident communications. |
| `slack_react` | Add emoji reactions to messages for incident status tracking (🔍 investigating, ✅ resolved). |
| `slack_pin_message` | Pin critical incident messages in channels for visibility. |
| `slack_unpin_message` | Unpin messages after incident resolution. |
| `slack_get_thread` | Read thread replies for incident context and status updates. |
| `slack_search_messages` | Search Slack history for past incidents, runbooks, and related discussions. |
| `twg` | Query Atlassian TeamWork Graph for Jira ticket creation/updates, Confluence runbook retrieval, and cross-product search. |

---

## 2. Workflow Mappings

### 2.1 Golden Signal Health Check

**Trigger**: User asks "How is service X doing?" or "Check health of service Y" or periodic health monitoring.

**Step-by-step operational pattern**:

1. **Identify the service**: Extract the service/job name from the request.
2. **Query all four golden signals** using `prometheus_query instant_query`:

   ```
   # LATENCY — P99
   prometheus_query instant_query --query 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="SERVICE"}[5m])) by (le))' --tenant_id TENANT

   # TRAFFIC — Request rate
   prometheus_query instant_query --query 'sum(rate(http_requests_total{job="SERVICE"}[5m]))' --tenant_id TENANT

   # ERRORS — Error ratio
   prometheus_query instant_query --query 'sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[5m])) / sum(rate(http_requests_total{job="SERVICE"}[5m]))' --tenant_id TENANT

   # SATURATION — CPU utilization
   prometheus_query instant_query --query '1 - avg(rate(node_cpu_seconds_total{mode="idle", job="SERVICE"}[5m]))' --tenant_id TENANT
   ```

3. **Assess results**: Compare each signal against baseline/SLO thresholds.
4. **Format response** using the standard SRE assessment template:

   ```
   Traffic is [normal/elevated/low] at ~X req/s.
   Error rate is [normal/elevated] at X% vs Y% baseline.
   P99 latency at Xs (Yx increase from baseline).
   CPU utilization at X% (from Y% baseline).
   Assessment: [summary of findings].
   Error budget: X% consumed this month. Burn rate: Yx.
   ```

**Example scenario**:
> User: "Check health of the api-gateway service"
> 1. Query four golden signals for `job="api-gateway"` with tenant `prod-us-east`
> 2. Results: Traffic 127 req/s (normal), Errors 0.8% (elevated from 0.1%), P99 2s (up from 118ms), CPU 95% (from 20%)
> 3. Response: "Traffic is normal at ~127 req/s. Error rate elevated at 0.8% vs 0.1% baseline. P99 latency at 2s (17x increase). CPU at 95%. Assessment: CPU spike causing latency degradation, errors are secondary. Recommend investigating recent deployments."

### 2.2 SLI/SLO Error Budget Computation

**Trigger**: User asks "What is the error budget for service X?" or "Compute SLI for capability Y" or weekly report generation.

**Step-by-step operational pattern**:

1. **Determine SLO parameters**: service name, SLO target (e.g., 99.9%), compliance period (default: 28 days).
2. **Query good and bad events over compliance window**:

   ```
   # Good events (e.g., HTTP 2xx + 3xx + 4xx, or latency < threshold)
   prometheus_query instant_query --query 'sum(increase(http_requests_total{job="SERVICE", code!~"5.."}[28d]))' --tenant_id TENANT

   # Total events
   prometheus_query instant_query --query 'sum(increase(http_requests_total{job="SERVICE"}[28d]))' --tenant_id TENANT
   ```

3. **Compute SLI**:
   ```
   SLI = good_events / total_events
   ```

4. **Compute error budget**:
   ```
   error_budget_pct = (SLI - SLO_target) / (1 - SLO_target) × 100
   ```

5. **Compute burn rate** (current):
   ```
   error_rate = 1 - SLI
   burn_rate = error_rate / (1 - SLO_target)
   ```

6. **Classify status**:
   - **HEALTHY**: budget > 70%, no active burns
   - **WATCHING**: budget 30-70%, declining trend
   - **BURNING**: budget change ≤ -5pp in current period
   - **BREACHED**: budget ≤ 0%
   - **RECOVERING**: budget negative but change strongly positive (≥ +5pp)

7. **Report**: "SLI is X%. Error budget: Y% remaining. Burn rate: Z. Status: [classification]. At this rate, budget exhausted in N hours."

**Example scenario**:
> SLO target: 99.9% over 28 days.
> Good events: 40,317. Total events: 40,318. Bad events: 1.
> SLI = 99.9975%. Error budget = (0.999975 - 0.999) / (1 - 0.999) × 100 = 97.5%.
> Burn rate = 0.000025 / 0.001 = 0.025 (well below 1).
> Status: HEALTHY. Budget exhausted in: never at this rate.

### 2.3 Multi-Window Multi-Burn-Rate Alert Evaluation

**Trigger**: Active burn rate alert fires, or user asks "Evaluate burn alerts for service X."

**Step-by-step operational pattern**:

1. **Query burn rates across three tiers** using `prometheus_query instant_query`:

   ```
   # STEEP BURN: 46-minute long window
   prometheus_query instant_query --query '(sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[46m])) / sum(rate(http_requests_total{job="SERVICE"}[46m]))) / (1 - 0.999)' --tenant_id TENANT

   # Steep short window verification (4 minutes)
   prometheus_query instant_query --query '(sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[4m])) / sum(rate(http_requests_total{job="SERVICE"}[4m]))) / (1 - 0.999)' --tenant_id TENANT

   # MODERATE BURN: 5.6-hour long window
   prometheus_query instant_query --query '(sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[336m])) / sum(rate(http_requests_total{job="SERVICE"}[336m]))) / (1 - 0.999)' --tenant_id TENANT

   # GRADUAL BURN: 2.8-day long window
   prometheus_query instant_query --query '(sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[4020m])) / sum(rate(http_requests_total{job="SERVICE"}[4020m]))) / (1 - 0.999)' --tenant_id TENANT
   ```

2. **Evaluate each tier** (28-day compliance period, SLO 99.9%):

   | Tier | Burn Rate Threshold | Long Window | Short Window | Budget Consumed | Severity |
   |------|-------------------|-------------|--------------|-----------------|----------|
   | Steep | 17.5 | 46m | 4m | 2% | Major (Page) |
   | Moderate | 6 | 336m (5.6h) | 28m | 5% | Major (Page) |
   | Gradual | 1 | 4020m (2.8d) | 300m (5h) | 10% | Minor (Ticket) |

3. **Both windows must fire**: Alert triggers only when BOTH long AND short window exceed the threshold for the same tier.

4. **Report findings**: Which tiers are active, burn rate values, estimated time to budget exhaustion.

### 2.4 Anomaly Detection Configuration

**Trigger**: User asks "Set up anomaly detection for metric X" or "Is this metric behavior anomalous?"

**Step-by-step operational pattern**:

1. **CLASSIFY the metric**:
   - Has seasonal patterns? → Check 2+ weeks of data
   - Concern is sudden spikes or gradual drift?
   - Daily event volume?
   - Distribution approximately normal?

2. **SELECT method per decision tree**:
   - Seasonal + sufficient data → **Holt-Winters**
   - Non-seasonal + sudden spikes → **Z-Score**
   - Non-seasonal + gradual drift → **CUSUM**
   - Low volume → prefer **CUSUM**
   - Skewed distribution → **Modified Z-Score (MAD)**

3. **Configure and query**:

   **Z-Score detection** (most common):
   ```
   prometheus_query instant_query --query '(avg_over_time(METRIC[10m]) - avg_over_time(METRIC[1h])) / stddev_over_time(METRIC[1h])' --tenant_id TENANT
   ```
   Threshold: |z| > 3.0 for fast detection, > 3.5 for reduced false positives.
   Add absolute guard: AND with 25% absolute drop check.

   **CUSUM detection** (gradual drift):
   ```
   prometheus_query range_query --query 'clamp_min(METRIC - avg_over_time(METRIC[6h]) - 0.5 * stddev_over_time(METRIC[6h]), 0)' --start START --end END --step 1m --tenant_id TENANT
   ```

   **Holt-Winters** (seasonal):
   ```
   prometheus_query instant_query --query 'METRIC - holt_winters(METRIC[7d], 0.3, 0.1)' --tenant_id TENANT
   ```

4. **Interpret results**: Compare against method-specific thresholds. Report confidence level.

**Metric Type → Recommended Method Mapping**:

| Metric Type | Method | Rationale |
|------------|--------|-----------|
| Request rate | Holt-Winters | Strong daily/weekly seasonality |
| Error rate (4xx/5xx) | Z-Score | Point anomalies, no strong seasonality |
| Latency (P50/P90/P99) | Z-Score + CUSUM | Z-Score for spikes, CUSUM for gradual degradation |
| CPU/Memory utilization | Z-Score | Relatively stationary, spike detection |
| Success rate (SLI) | CUSUM | Detects gradual reliability degradation |
| Queue depth | CUSUM | Accumulating backlog detection |
| Traffic volume (users) | Holt-Winters | Strong weekly seasonality |

### 2.5 Incident Response Coordination

**Trigger**: Alert fires, user reports an outage, or anomaly detected.

**Step-by-step operational pattern**:

1. **Find incident channel**:
   ```
   slack_find_channel --channel_name incident-response
   ```

2. **Send alert notification**:
   ```
   slack_send_message channel:{channel_id} "🚨 Incident: {summary}\nService: {service}\nSeverity: {sev}\nError rate: {rate}%\nP99 latency: {latency}s"
   ```

3. **Pin the alert message**:
   ```
   slack_pin_message {channel_id} {alert_ts}
   ```

4. **Mark as investigating**:
   ```
   slack_react {channel_id} {alert_ts} 🔍
   ```

5. **Create Jira ticket** (for Sev2+):
   ```
   twg jira workitem create --project SRE --type Bug --summary "Incident: {summary}" --description "{details}"
   ```

6. **Link Jira ticket in thread**:
   ```
   slack_send_message channel:{channel_id} "Jira ticket created: {ticket_id}" --thread_ts {alert_ts}
   ```

7. **Search for runbook**:
   ```
   twg confluence search query --cql "title ~ 'runbook {service}'"
   ```

8. **Share runbook in thread**:
   ```
   slack_send_message channel:{channel_id} "📋 Runbook: {runbook_url}" --thread_ts {alert_ts}
   ```

9. **On resolution — update status**:
   ```
   slack_remove_reaction {channel_id} {alert_ts} 🔍
   slack_react {channel_id} {alert_ts} ✅
   slack_unpin_message {channel_id} {alert_ts}
   twg jira workitem update --id {ticket_id} --status Done
   ```

### 2.6 Grafana Dashboard Investigation

**Trigger**: User asks "Show me the dashboard for service X" or investigating an incident via dashboards.

**Step-by-step operational pattern**:

1. **Search for relevant dashboards**:
   ```
   grafana_manage dashboard_search --query "{service_name}" --tags "production,sre"
   ```

2. **Get dashboard details**:
   ```
   grafana_manage dashboard_get --uid {dashboard_uid}
   ```

3. **Add incident annotation** (if investigating):
   ```
   grafana_manage annotation_create --dashboard_id {id} --text "Investigating: {incident_summary}" --tags "incident,{service}"
   ```

4. **Check active alerts**:
   ```
   grafana_manage alertmanager_alerts
   ```

5. **Export alert rules for review**:
   ```
   grafana_manage alert_rules_export --export_format yaml
   ```

### 2.7 Weekly SLO Compliance Report Generation

**Trigger**: Weekly cadence (every Monday), or user requests "Generate SLO report."

**Step-by-step operational pattern**:

1. **For each monitored service/SLO**, query 28-day good and bad events (see Workflow 2.2).

2. **Compute for each SLO**:
   - SLI (current 28-day)
   - Error budget remaining (%)
   - Error budget delta vs. previous week (⬆/⬇ direction + percentage points)
   - Burn status classification (HEALTHY / WATCHING / BURNING / BREACHED / RECOVERING)

3. **Build report** using the standard template:

   ```markdown
   # Weekly SLO Compliance Report — [DATE]

   ## What Needs Attention
   1. **[SLO Name]** — [Budget]% error budget. [Brief description]
   ...

   ## [Category] SLOs

   | SLO | SLI | Target | Goal | Gap | Error Budget | Status |
   |-----|-----|--------|------|-----|-------------|--------|
   | [Name] | [X.XXX%] | [Y%] | [Z%] | [gap] | [EB%] (⬆/⬇ Δ) | [emoji + text] |

   ## Investigation Priority

   | # | SLO | Budget | Issue | Action Needed |
   |---|-----|--------|-------|---------------|

   ## Breach/Burn History (Last 7 Days)

   | SLO | Event Type | Timestamp | Duration | Correlated Incident |
   |-----|-----------|-----------|----------|-------------------|

   ## Action Items

   | # | Owner | Task | Priority | Status |
   |---|-------|------|----------|--------|
   ```

4. **Publish** (requires human confirmation): Post to Confluence via `twg confluence page create` and notify via Slack.

**Status emoji mapping**:
- ✅ HEALTHY (budget > 70%)
- 👀 WATCHING (budget 30-70%)
- 🔥 BURNING (budget declining > 5pp/week)
- 🚨 BREACHED (budget ≤ 0%)
- 📈 RECOVERING (budget negative, trend positive)


---

## 3. Domain Guidance

### 3.1 PromQL Query Templates — Four Golden Signals

#### Latency (P99)
```promql
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{job="SERVICE"}[5m])) by (le)
)
```
**Critical rules**: Always `rate()` then `sum()` — never reverse. The `le` label must be preserved in `by (le)`.

#### Latency SLI (good/bad event model)
```promql
# Good events: requests under 500ms
sum(rate(http_request_duration_seconds_bucket{le="0.5", job="SERVICE"}[5m]))
/
sum(rate(http_request_duration_seconds_count{job="SERVICE"}[5m]))
```

#### Traffic (Request Rate)
```promql
sum(rate(http_requests_total{job="SERVICE"}[5m]))
```

#### Traffic by endpoint
```promql
sum(rate(http_requests_total{job="SERVICE"}[5m])) by (handler, method)
```

#### Error Ratio
```promql
sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[5m]))
/
sum(rate(http_requests_total{job="SERVICE"}[5m]))
```

#### Error Rate excluding client errors
```promql
sum(rate(http_requests_total{job="SERVICE", code=~"5.."}[5m]))
/
sum(rate(http_requests_total{job="SERVICE", code!~"4.."}[5m]))
```

#### Saturation — CPU
```promql
1 - avg(rate(node_cpu_seconds_total{mode="idle", instance=~"SERVICE.*"}[5m]))
```

#### Saturation — Memory
```promql
1 - (node_memory_MemAvailable_bytes{instance=~"SERVICE.*"} / node_memory_MemTotal_bytes{instance=~"SERVICE.*"})
```

### 3.2 Rate Window Sizing Guidance

| Use Case | Window | Rationale |
|----------|--------|-----------|
| Dashboards, visual trends | `5m` | Smooth, low-noise, standard |
| Alert rules | `5m` to `15m` | Balance speed vs. false positives |
| Burn rate (steep) | `4m` short / `46m` long | Fast detection, 2% budget |
| Burn rate (moderate) | `28m` short / `336m` long | Moderate, 5% budget |
| Burn rate (gradual) | `300m` short / `4020m` long | Slow drift, 10% budget |
| Recording rules | `5m` | Industry standard |
| Low-traffic services (< 1 req/s) | `15m` to `30m` | Avoid noisy rates |

**Rule**: `rate()` window must be ≥ 4× the scrape interval (typically 15-30s scrape → 1m minimum window).

### 3.3 Multi-Window Multi-Burn-Rate Configuration (TOME Standard)

**Standard three-tier burn event configuration (28-day compliance)**:

| Parameter | Steep | Moderate | Gradual |
|-----------|-------|----------|---------|
| Burn Rate Threshold | 17.5 | 6 | 1 |
| Short Window | 4m | 28m | 300m (5h) |
| Long Window | 46m | 336m (5.6h) | 4020m (~2.8d) |
| Budget Consumed per Alert | 2% | 5% | 10% |
| Time to Exhaust if Sustained | ~38h | ~4.6d | 28d |
| Alert Severity | Major (Page) | Major (Page) | Minor (Ticket) |
| Max Alerts Before Breach | 50 | 20 | 10 |

**Error rate required to trigger (by SLO)**:

| SLO | Steep (17.5×) | Moderate (6×) | Gradual (1×) |
|-----|---------------|---------------|--------------|
| 99.95% | 0.875% | 0.3% | 0.05% |
| 99.9% | 1.75% | 0.6% | 0.1% |
| 99% | 17.5% | 6% | 1% |

**Low-traffic guard**: If total request count in the long window < 100, suppress the alert. This prevents noisy alerts on low-volume services.

### 3.4 SLI / SLO / Error Budget Formulas

```
SLI = good_events / (good_events + bad_events)

error_budget_pct = (SLI - SLO) / (1 - SLO) × 100

burn_rate = (bad / (good + bad)) / (1 - SLO)

time_to_exhaust = compliance_period / burn_rate

error_budget_consumed = burn_rate × long_window / compliance_period
```

**Compliance period**: Rolling 28-day window (Atlassian standard).

### 3.5 Anomaly Detection Parameter Defaults

#### Z-Score Detection
| Parameter | Default | Notes |
|-----------|---------|-------|
| Sigma threshold | 3.0 (fast) / 3.5 (medium) | Below 3.0 requires human approval |
| Rolling window | 1h (fast) / 6h (medium) | Determines baseline period |
| Absolute guard | 25% drop | ANDed with z-score condition |
| Lasting clause | 10 minutes | Sustained violation required |
| Minimum events | 10,000/day | Below this, apply confidence damping |

#### CUSUM Detection
| Parameter | Default | Notes |
|-----------|---------|-------|
| Slack (k) | δ/2 where δ = shift to detect | |
| Decision threshold (h) | 4-5 × σ | Higher = fewer false positives |
| Baseline window | 6h | Computes reference mean |

#### Holt-Winters Detection
| Parameter | Default | Notes |
|-----------|---------|-------|
| Smoothing factor (α) | 0.3 | Level smoothing |
| Trend factor (β) | 0.1 | Trend smoothing |
| Season length | 24 (hourly) or 7 (daily) | Cycle length |
| Data requirement | ≥ 2 seasonal cycles | 2 weeks for daily, 14 days for weekly |

### 3.6 Decision Criteria

#### Severity Classification
| Severity | Criteria | Response SLA | Action |
|----------|----------|-------------|--------|
| Sev1 | Complete outage, SLO breach + steep burn | 5 minutes | Page on-call, incident channel, all hands |
| Sev2 | Significant degradation, moderate burn, budget < 30% | 15 minutes | Page on-call, Jira ticket |
| Sev3 | Minor degradation, gradual burn, budget declining | 4 hours | Jira ticket, Slack notification |
| Sev4 | Informational, no immediate impact | Next business day | Slack notification only |

#### Deployment Gate Decision Tree
1. **Check error budget**: Query current budget remaining
2. **Check active burns**: Query all three tier burn rates
3. **Apply decision**:
   - Budget > 50%, no active burns → **ALLOWED**
   - Budget 30-50%, no steep/moderate burns → **CAUTION** (proceed with monitoring)
   - Budget < 30% OR active moderate burn → **BLOCKED** (requires SRE approval)
   - Budget ≤ 0% OR active steep burn → **FROZEN** (no deployments until recovery)

### 3.7 Terminology

| Term | Definition |
|------|-----------|
| **SLI** | Service Level Indicator — measured ratio of good to total events |
| **SLO** | Service Level Objective — target SLI percentage over compliance period |
| **SLA** | Service Level Agreement — contractual commitment with consequences |
| **Error Budget** | `1 - SLO` — allowed failure proportion |
| **Burn Rate** | `observed_error_rate / error_budget` — speed of budget consumption |
| **Compliance Period** | Rolling window for SLO evaluation (typically 28 days) |
| **Recording Rule** | Pre-computed PromQL stored as new metric series |
| **`le` label** | "Less than or equal" — histogram bucket boundary label |
| **`histogram_quantile()`** | Prometheus function computing quantiles from histogram buckets |
| **`rate()`** | Per-second average increase of counter over time window |
| **Four Golden Signals** | Latency, Traffic, Errors, Saturation (Google SRE) |
| **RED** | Rate, Errors, Duration — request-oriented monitoring |
| **USE** | Utilization, Saturation, Errors — resource-oriented monitoring |
| **MWMBR** | Multi-Window, Multi-Burn-Rate alerting (Google SRE method #6) |
| **TOME** | Atlassian's Technical Observability & Monitoring Environment |
| **HOT** | High-priority Operational Ticket (incident) |
| **PIR** | Post-Incident Review |
| **Steep Burn** | 17.5× burn rate — exhausts budget in ~38h — pages immediately |
| **Moderate Burn** | 6× burn rate — exhausts budget in ~4.6d — pages or ticket |
| **Gradual Burn** | 1× burn rate — exhausts budget at end of period — ticket |
| **Capability Tier** | C1 (essential) through C3 (recommended) |
| **MAD** | Median Absolute Deviation — robust alternative to σ for skewed data |
| **Dual-Signal** | Requiring two independent signals to agree before alerting |

### 3.8 Cadence Patterns

| Activity | Frequency | Description |
|----------|-----------|-------------|
| Golden signal health check | On-demand / every 5m (automated) | Query four golden signals for each monitored service |
| Error budget computation | Daily (automated) / on-demand | Compute SLI, budget remaining, burn rate for all SLOs |
| Burn rate alert evaluation | Continuous (via recording rules) | Three-tier MWMBR evaluation |
| Weekly SLO compliance report | Weekly (Monday morning) | Full report with trends, breaches, action items |
| Dashboard annotation | Per-deployment / per-incident | Mark deployment and incident events on Grafana dashboards |
| Alert rule review | Monthly / after incidents | Review alert thresholds, tune false positives |
| Anomaly detection tuning | Quarterly | Review detection methods, adjust parameters |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
| `prometheus_query` | `instant_query`, `range_query`, `list_series`, `label_names`, `label_values`, `metadata` |
| `grafana_manage` | `dashboard_get`, `dashboard_search`, `annotation_create`, `annotation_list`, `alert_rules_list`, `alert_rules_get`, `alert_rules_export`, `alertmanager_alerts`, `folder_list` |
| `slack_send_message` | Send alert notifications, incident updates, report summaries |
| `slack_find_channel` | Locate incident-response, sre-alerts, team channels |
| `slack_react` | 🔍 (investigating), ✅ (resolved), 🚨 (escalated) |
| `slack_pin_message` | Pin active incident messages |
| `slack_unpin_message` | Unpin after resolution |
| `slack_get_thread` | Read incident thread for context |
| `slack_search_messages` | Find past incidents, runbooks, related discussions |
| `twg` | `jira workitem create`, `jira workitem update`, `confluence search query`, `confluence page create` |

### 4.2 Cross-Tool Patterns

**Pattern 1: Alert → Investigate → Report**
```
prometheus_query instant_query (detect anomaly)
  → grafana_manage dashboard_search (find relevant dashboard)
  → grafana_manage annotation_create (mark incident start)
  → slack_send_message (notify team)
  → twg jira workitem create (create ticket)
```

**Pattern 2: Metric Discovery → Dashboard**
```
prometheus_query list_series (discover available metrics)
  → prometheus_query label_values (enumerate dimensions)
  → prometheus_query range_query (validate query produces data)
  → grafana_manage dashboard_create (build dashboard with validated queries)
```

**Pattern 3: Weekly Report Pipeline**
```
prometheus_query instant_query × N (query all SLO metrics)
  → [compute SLI, budget, burn rate for each]
  → grafana_manage annotation_list (get breach/burn events)
  → twg confluence page create (publish report)
  → slack_send_message (notify stakeholders)
```

**Pattern 4: Incident Lifecycle**
```
slack_find_channel → slack_send_message → slack_pin_message → slack_react 🔍
  → twg jira workitem create → slack_send_message (thread: ticket link)
  → twg confluence search (runbook) → slack_send_message (thread: runbook)
  → [resolution]
  → slack_react ✅ → slack_unpin_message → twg jira workitem update (Done)
```

### 4.3 Autonomy Levels

| Operation | Autonomy Level | Rationale |
|-----------|---------------|-----------|
| Query golden signal metrics | **Autonomous** | Read-only, no side effects |
| Compute SLI/error budget | **Autonomous** | Mathematical computation |
| Search dashboards and folders | **Autonomous** | Read-only |
| List/get alert rules | **Autonomous** | Read-only |
| Export alert rules | **Autonomous** | Read-only |
| Create Grafana annotations | **Autonomous** | Low-risk, audit-logged |
| Send Slack alert notifications | **Autonomous** | Time-critical, predefined channels |
| Generate report content | **Autonomous** | Analysis and reporting |
| Add emoji reactions | **Autonomous** | Status tracking |
| Pin/unpin messages | **Autonomous** | Visibility management |
| Search Slack/Confluence | **Autonomous** | Read-only |
| Create Jira tickets (Sev2+) | **Autonomous** | Incident tracking, time-critical |
| Create/update dashboards | **Human confirmation** | Changes visualization infrastructure |
| Create/update/delete alert rules | **Human confirmation** | Changes alerting behavior |
| Modify SLO targets | **Human confirmation** | Business commitment |
| Silence/suppress alerts | **Human confirmation** | May mask real issues |
| Publish weekly reports | **Human confirmation** | Stakeholder communication |
| Cross-tenant Prometheus queries | **Human confirmation** | Performance implications |
| Delete dashboards/folders | **Human confirmation** | Destructive operation |
| Modify burn rate thresholds | **Human confirmation** | Changes detection sensitivity |
| Change anomaly detection sigma | **Human confirmation** | Below 3.0 especially |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries — What the AI MUST NOT Do Autonomously

1. **Never modify alert thresholds or SLO targets** without human confirmation — these are business commitments.
2. **Never silence or suppress active alerts** without human confirmation — this may mask genuine incidents.
3. **Never delete dashboards, folders, or alert rules** without human confirmation — destructive and irreversible.
4. **Never execute cross-tenant queries** involving more than 2 tenants without confirmation — performance risk.
5. **Never create recording rules** without human review — affects the metrics pipeline.
6. **Never publish reports externally** (Confluence, email) without human confirmation.
7. **Never change deployment gates** (ALLOWED → BLOCKED) without human confirmation.
8. **Never set anomaly detection sigma below 3.0** without human approval — high false positive risk.
9. **Never execute range queries estimated to return >10M data points** — system safety limit.
10. **Never modify Grafana data source configurations** — infrastructure-level change.

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| Error budget ≤ 0% (breached) | Escalate to team lead + on-call. Create Sev1/Sev2 Jira ticket. |
| Steep burn rate active (17.5×) | Page on-call immediately via Slack. |
| Multiple services burning simultaneously | Escalate to engineering leadership. Potential systemic issue. |
| Anomaly detected across >3 services | Escalate — possible infrastructure-level failure. |
| Query returns no data for expected metric | Investigate metric pipeline health. May indicate scrape failure. |
| Prometheus/Mimir API returns 503 | Retry with exponential backoff (1s, 2s, 4s, max 3 retries). Report persistent failures. |
| Dashboard creation fails with 412 | Version conflict — fetch latest version and retry. |
| SLO target change requested | Require sign-off from service owner + SRE lead. |
| Unknown metric name referenced | Use `prometheus_query list_series` and `label_values` to discover correct metric names. Report findings. |
| Alert rule provenance conflict | Cannot modify UI-provisioned rules via API or vice versa. Inform user of provenance status. |

### 5.3 Error Handling

| Error | Tool | Recovery Action |
|-------|------|----------------|
| Connection refused / timeout | `prometheus_query` | Retry with exponential backoff (3 attempts). Check `PROMETHEUS_URL` env var. |
| HTTP 400 (bad request) | `prometheus_query` | PromQL syntax error. Parse error message, suggest correction. |
| HTTP 422 (unprocessable) | `prometheus_query` | Expression cannot be executed. Simplify query or adjust time range. |
| HTTP 503 (timeout) | `prometheus_query` | Query too expensive. Reduce time range, increase step, or add label filters. |
| Non-JSON response | `prometheus_query` | Auth failure or proxy error. Check credentials and endpoint URL. |
| HTTP 401/403 | `grafana_manage` | Insufficient permissions. Check `GRAFANA_API_TOKEN` role (Viewer/Editor/Admin). |
| HTTP 412 (precondition failed) | `grafana_manage` | Dashboard version conflict. Fetch latest, merge changes, retry with correct version. |
| HTTP 404 | `grafana_manage` | Dashboard/resource not found. Verify UID. Use search to find correct identifier. |
| Empty result set | `prometheus_query` | Metric may not exist or time range has no data. Use `list_series` to verify metric existence. |
| Rate limiting (HTTP 429) | Any | Back off and retry. Respect `Retry-After` header. |
| Slack channel not found | `slack_find_channel` | Channel may be private or archived. Suggest alternative channels. |
| TWG Jira creation fails | `twg` | Verify project key and issue type. Fall back to Slack-only incident tracking. |

### 5.4 Data Volume Safety

For `prometheus_query range_query`:
- **Auto-step selection**: Tool automatically selects appropriate step based on time range.
- **Warning threshold**: > 1M estimated data points → warn and suggest larger step.
- **Hard limit**: > 10M estimated data points → reject and require modified parameters.
- **Estimation formula**: `data_points = num_series × ((end - start) / step)`.
- **Recommended approach**: Always start with instant queries for point-in-time checks. Use range queries only when time-series visualization or trend analysis is needed.

### 5.5 Multi-Tenant Safety

For Mimir multi-tenant deployments:
- **Single tenant**: Always include `--tenant_id` on every query. Default to configured tenant.
- **Cross-tenant** (pipe-delimited): Require human confirmation for > 2 tenants. Performance degrades linearly.
- **Tenant isolation**: Each tenant has independent rate limits, retention, and quotas. Cross-tenant queries span multiple limit domains.
- **Auth**: Mimir OSS trusts the `X-Scope-OrgID` header. Auth is handled by the proxy layer (SLAuth/ASAP). Ensure auth tokens are valid before making requests.
