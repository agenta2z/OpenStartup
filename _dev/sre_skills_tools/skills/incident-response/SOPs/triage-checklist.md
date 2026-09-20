# SOP: Triage checklist (5-min cap)

**Trigger:** kickoff message posted (per `incident-onboarding.md`).

**Goal:** within 5 more minutes, gather enough evidence to either (a) propose a mitigation, or (b) define the next investigative step.

The agent runs the following queries IN PARALLEL (not sequentially) and posts results to the incident channel.

## Parallel data-gathering

### Q1 — Error rate trend (last 1h)
```
prometheus_query action=query_range
  --query 'sum(rate(http_requests_total{service="<svc>",status=~"5.."}[5m])) / sum(rate(http_requests_total{service="<svc>"}[5m]))'
  --since 1h
  --step 30s
```
Look for: a clear inflection point. Note the timestamp.

### Q2 — Latency trend (last 1h)
```
prometheus_query action=query_range
  --query 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="<svc>"}[5m])) by (le))'
  --since 1h
  --step 30s
```

### Q3 — Recent error logs (last 15 min)
```
log_query action=query_range
  --query '{service="<svc>",level="error"} | json'
  --since 15m
  --limit 100
  --direction backward
```
Group by error message; report top-3 distinct messages with counts.

### Q4 — Related alerts (currently firing)
```
alertmanager_query action=list_alerts
  --filter '{service="<svc>",alertstate="firing"}'
```
Look for: cascading downstream alerts that may share a root cause.

### Q5 — Recent deploys for this service
```
runbook_search action=search --query "<svc> deploy" --label "deploy-history" --limit 5
# AND
rovodev_get_pr_links_from_issue_link --issue_url <linked Jira issue>
```
Look for: a deploy timestamp within ±15 min of the inflection point in Q1/Q2.

### Q6 — Existing runbook for this alert
```
runbook_search action=search --query "<alert name> runbook"
```
Look for: a step-by-step mitigation. If found, link it in the channel BEFORE proposing the steps.

## Triage post-message format

Post in the incident channel:
```
[TRIAGE — 5 min]
Service: <svc>
Inflection point: <timestamp> (Q1)
Top error msg: <msg> (Q3, count=<N>)
Related alerts: <list> (Q4)
Recent deploy candidate: <pr-url> at <ts> (Q5) — Δ <minutes> from inflection
Runbook found: <url> (Q6) | "no runbook found"

Hypothesis (best-guess): <one sentence>
Next step proposal: <one sentence — needs human OK>
```

## Done criteria

- All 6 queries returned (or explicitly failed with reason)
- A `[TRIAGE]` message is posted
- A "Hypothesis" line is posted (even if it's "no clear cause yet")
- A "Next step proposal" is posted

## Failure modes

- **Service name has no metric series**: report `Q1/Q2 returned empty — service '<svc>' may have a different metric label. Try '<guess1>' or '<guess2>'?` and ask the human
- **Log query times out**: narrow the query to 5 min (instead of 15) and add a more specific filter
- **>3 distinct top errors**: report all 3 with counts; let the human pick the dominant one
