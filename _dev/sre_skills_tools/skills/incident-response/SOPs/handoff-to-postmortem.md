# SOP: Handoff to postmortem

**Trigger:** symptom verified recovered for 10+ consecutive minutes.

**Goal:** capture the state needed for a thorough postmortem WITHOUT delaying the IC's next priority.

## Step-by-step

### 1. Verify the recovery (don't skip)

Run the symptom queries from `triage-checklist.md` Q1/Q2 over the last 30 min. Look for: error rate / latency / saturation back to within ±10% of pre-incident baseline for 10+ consecutive minutes.

Post:
```
[RECOVERY VERIFIED]
<svc> <metric> recovered to baseline at <ts>.
Sustained recovery: <N> min.
```

### 2. Capture the state snapshot

Take screenshots / save query results for:
- Error-rate graph spanning [start - 30min] → [now + 10min]
- Latency p99 same window
- Top-5 error log lines during the incident window
- Any related alerts that fired

Save these as comments on the incident ticket:
```
atlassian_update_jira_issue
  issue_url: <ticket-url>
  comment_html: |
    [POSTMORTEM ARTIFACTS]
    Error rate graph: <grafana-snapshot-url>
    Latency p99: <grafana-snapshot-url>
    Top errors: <top-3-with-counts>
    Related alerts: <list>
    Mitigation: <what was done>
    Hypothesis (best as of mitigation): <one sentence>
```

### 3. Search for related historical incidents

The agent runs:
```
runbook_search action=search --query "<service> <symptom>" --label "postmortem"
```
Plus:
```
twg_twg_atlassian_graph_get_similar_jira_issues --issueAri <incident-ticket-ari>
```

If hits are found, list them in the postmortem-prep ticket comment so the human-led RCA can compare patterns.

### 4. Suggest a postmortem owner

The owner SHOULD be the person who proposed the mitigation that worked, OR the service owner (the team-level owner from `twg_twg_atlassian_graph_get_user_owned_entities`), whichever the IC prefers.

Post in the incident channel:
```
[POSTMORTEM PREP]
Suggested owner: @<person>
Suggested deadline: <T+5 business days>
Template: <link to your postmortem template>
Artifacts captured: see ticket <link>
```

### 5. Hand off the channel

```
[HANDOFF]
Incident channel will remain open until the postmortem is published.
The agent (Rovo Dev) is stepping back. Ping me to resume.
Thank you to everyone who responded.
```

## Done criteria

- Recovery verified
- Artifacts comment posted to incident ticket
- Suggested postmortem owner + deadline announced
- Handoff message posted

## Anti-patterns

- ❌ Closing the channel before the postmortem (postmortem prep happens in the channel)
- ❌ Auto-creating the postmortem doc (the human owns the narrative)
- ❌ Skipping the recovery verification (premature de-escalation has bitten teams before)
- ❌ Forgetting to capture screenshots (graphs change after recovery; capture before they do)
