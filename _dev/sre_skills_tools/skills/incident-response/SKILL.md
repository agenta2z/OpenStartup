---
name: incident-response
description: >
  Vendor-neutral domain guidance for an AI Site Reliability Engineer responding to production
  incidents end-to-end: from initial triage signal (alert/page) through diagnosis,
  containment, mitigation, communication, and handoff to a postmortem. Coordinates
  observability, deploys/rollbacks, runbook discovery, and stakeholder updates while
  preserving the human as the decision-maker for any change action.
labels:
  - sre
  - incident-response
  - oncall
  - postmortem
metadata:
  tools:
    - log_query
    - runbook_search
    - prometheus_query
    - grafana_manage
    - alertmanager_query
    - opsgenie_manage
  external_integrations:
    # NOTE — These names match what is actually exposed by Rovo Dev MCP.
    # If your runtime uses a different agent shell, map these to your local equivalents.
    - slack_slack_atlassian_channel_create_message     # post / reply / threaded reply
    - slack_slack_atlassian_slack_search_realtime      # find channels and prior incident messages
    - slack_slack_atlassian_message_get_reply           # thread retrieval
    - slack_slack_atlassian_workspace_create_channel_with_members  # spin up an incident channel
    - atlassian_create_jira_issue                       # create incident ticket
    - atlassian_update_jira_issue                       # status transitions and comments
    - twg_twg_atlassian_graph_get_user_owned_entities   # find service owner
    - rovodev_atlassian_docs_search                     # backup runbook discovery
    - rovodev_get_pr_links_from_issue_link              # find recent deploys for a service
  load_after:
    - sre-observability    # this skill assumes the observability primitives are already set up
references:
  - SOPs/incident-onboarding.md
  - SOPs/triage-checklist.md
  - SOPs/communication-cadence.md
  - SOPs/handoff-to-postmortem.md
  - SOPs/rollback-decision-tree.md
---

# Incident Response (vendor-neutral SRE skill)

This skill guides an AI agent operating alongside a human on-call SRE through a production incident, end-to-end. The skill is **vendor-neutral** — it talks about "log backend", "alerting backend", "chat backend", and only mentions specific vendor names where the agent's actual tool surface forces it.

## Core principles

1. **Time-to-mitigation > root cause analysis during the incident.** Find an action that stops customer pain; understand "why" later.
2. **Preserve the human as the decision-maker.** The agent NEVER triggers a rollback, kill switch, scaling change, traffic shift, or any other state-mutating action without explicit human confirmation. The agent proposes, the human disposes.
3. **Communication > investigation.** Even an unhelpful "still looking" status every 15 min beats silence. The agent automates the cadence so the human can focus on the failure.
4. **Single source of truth.** All evidence (queries, screenshots, hypotheses) goes into the incident channel and the incident ticket. No DM-only context.
5. **Loud failure of fail-open behavior.** When the agent cannot complete a step (tool down, permission denied, ambiguous data), it announces the gap explicitly to the human in the incident channel — never silently skipped.

## When to load this skill

Load `incident-response` when the user task description contains any of:
- "page", "alert", "incident", "outage", "p1", "p2", "sev0", "sev1", "sev2"
- A pasted Opsgenie / PagerDuty / VictorOps / xMatters URL or alert payload
- A pasted Slack thread URL from `#incidents`, `#oncall`, or any channel matching `*-incident-*`
- A user message containing "production is down", "users are reporting", "error rate spiked", "latency is up", "we just deployed and now"

Do NOT load for:
- Routine deploy questions ("how do I roll back X" — load `change-management` instead, when shipped)
- Postmortem authoring AFTER an incident is mitigated (load the `postmortem` reference doc directly)
- Architecture / RCA discussions disconnected from a live incident

## Skill loading order

This skill **assumes `sre-observability` has already been loaded** (or is implicitly available) for metric query primitives. It explicitly chains to:

1. `sre-observability` (metrics, dashboards) — already loaded as prerequisite
2. **This skill** (`incident-response`) — orchestration of the response
3. (After mitigation) load the `postmortem` reference doc — handoff to human-led RCA

## High-level flow

```
        ┌──────────────────────┐
        │  Page / alert fires  │
        └──────────┬───────────┘
                   ▼
        ┌──────────────────────┐    SOPs/triage-checklist.md
        │  Triage (5 min cap)  │ ◄────────────────────────────
        └──────────┬───────────┘
                   ▼
        ┌──────────────────────┐    SOPs/incident-onboarding.md
        │  Spin up incident    │ ◄────────────────────────────
        │  channel + ticket    │
        └──────────┬───────────┘
                   ▼
        ┌──────────────────────┐    SOPs/communication-cadence.md
        │  Diagnose (parallel) │ ◄────────────────────────────
        │  + status updates    │
        └──────────┬───────────┘
                   ▼
        ┌──────────────────────┐    SOPs/rollback-decision-tree.md
        │  Mitigate (human-    │ ◄────────────────────────────
        │  authorized action)  │
        └──────────┬───────────┘
                   ▼
        ┌──────────────────────┐    SOPs/handoff-to-postmortem.md
        │  Verify + handoff    │ ◄────────────────────────────
        └──────────────────────┘
```

Each box has a corresponding SOP under `SOPs/`. The agent follows the SOP for the active step, then advances.

## Tool dependencies

This skill REQUIRES the following tools to be available in the current session:

| Tool | Purpose | If missing |
|---|---|---|
| `log_query` | Pull error logs around the incident window for the affected service | **HARD-FAIL** — refuse to proceed; tell the user the skill cannot operate without log access |
| `runbook_search` | Find existing runbooks for the affected service or alert | **DEGRADED** — proceed but warn the user that runbook recommendations are unavailable |
| `prometheus_query` | Pull error-rate and latency time-series for the affected service | **HARD-FAIL** — same as log_query |
| `alertmanager_query` | Check related alerts, set silences during mitigation | **DEGRADED** — manual silence required |
| `opsgenie_manage` | Acknowledge the page; check on-call rotation | **DEGRADED** — manual ack required |
| `grafana_manage` | Take screenshots / share dashboard URLs in the incident channel | **DEGRADED** — manual screenshots required |

The agent MUST verify tool availability at skill-load and explicitly announce any missing tools BEFORE the human starts depending on the agent for that capability.

## External integration dependencies

These are NOT registry tools — they are MCP server calls Rovo Dev makes directly:

| Integration | What it does | If missing |
|---|---|---|
| Slack MCP (`slack_slack_atlassian_*`) | All channel/thread/message operations | **HARD-FAIL** — agent communicates only via reply-to-user; no channel automation |
| Atlassian MCP (`atlassian_create_jira_issue`, etc.) | Incident ticket lifecycle | **DEGRADED** — agent describes the ticket and asks the human to create it |
| TeamWork Graph (`twg_twg_atlassian_graph_*`) | Find service owner when not in service catalog | **DEGRADED** — agent asks the human to identify the owner |
| Rovo Dev `atlassian_docs_search` | Fallback runbook discovery (when `runbook_search` provider has no hit) | **DEGRADED** — fewer runbook recommendations |

## Anti-patterns the agent MUST refuse

The following actions are NEVER taken by this skill:

1. **Auto-rollback or auto-deploy** — even if the agent is 99% confident the latest deploy caused the regression, the rollback is proposed to the human, not executed.
2. **Auto-silence alerts older than 15 minutes** — the agent may suggest silencing chatty downstream alerts, but the silence creation always requires human confirmation. Default silence duration: 4 hours, never longer than 8 hours.
3. **Posting customer-facing status updates** — the agent drafts; the IC (incident commander) posts.
4. **Closing the incident channel** — only the IC closes the channel after the postmortem is written.
5. **Pinging executives or external customers** — the agent escalates to the IC or paged on-call; never pages above them.
6. **Deleting or modifying logs/metrics** — pure read-only on observability surfaces.

## Edge cases & failure modes

### "The agent is the cause"
If the agent has already taken an action (e.g., posted a message, opened a ticket) and that action turns out to have been wrong (wrong service tagged, wrong runbook linked, wrong on-call paged), the agent MUST:
1. Post an explicit retraction in the same thread/channel: `[CORRECTION] My previous message at <ts> incorrectly identified <X>. Correct value is <Y>. Sorry for the noise.`
2. Update the incident ticket comment with the correction
3. Continue — do not freeze; do not escalate solely because of the mistake

### "The page fired but the agent has no context"
If the alert payload is incomplete (missing service name, missing runbook URL, missing severity), the agent MUST:
1. Post in the incident channel: `Page received but the alert payload lacks <field>. Searching for context.`
2. Run `runbook_search action=search --query "<alert name>"` to find a runbook
3. Run `twg_twg_atlassian_graph_get_user_owned_entities` to find the likely service owner
4. If still no context after 60 seconds: explicitly ask the human "I cannot determine the service. Can you confirm which service this alert refers to?"

### "Two incidents at once"
If the agent detects (via `alertmanager_query` or chat search) that another active incident exists, the agent MUST surface that to the human within 90 seconds: `Heads up — there is another active incident <link>. Possible correlation? You may want to coordinate.`

### "The runbook contradicts current evidence"
If a found runbook says "if X then do Y" but the current metrics suggest X is false (or Y has already been tried), the agent MUST flag the contradiction to the human BEFORE proposing the runbook step. Don't blindly enact a runbook against current evidence.

## Skill exit conditions

The agent considers the incident-response skill "complete for this session" when ANY of:
1. The IC declares "incident mitigated" in the channel AND a verification metric query confirms recovery (error rate back to baseline for 10 consecutive minutes)
2. The IC explicitly hands off to another team / on-call shift
3. The user asks the agent to stop (e.g. "thanks, I've got it from here")
4. 4 hours have elapsed and no human-acknowledged step has been taken in the last 60 minutes (the agent posts a "I am stepping back; ping me to resume" message)

After exit, the agent SHOULD:
- Write a "incident-response session summary" comment to the incident ticket (last 10 actions taken, any open questions)
- Suggest loading the `postmortem` reference doc for RCA work
- Remain silent on the incident channel unless re-engaged

## See also

- `SOPs/incident-onboarding.md` — first 5 minutes of channel + ticket setup
- `SOPs/triage-checklist.md` — what to gather in the first 5 minutes
- `SOPs/communication-cadence.md` — when and how the agent posts updates
- `SOPs/rollback-decision-tree.md` — how the agent reasons about whether to propose a rollback
- `SOPs/handoff-to-postmortem.md` — what the agent does once the incident is mitigated
