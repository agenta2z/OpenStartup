# SOP: Incident onboarding (first 5 min)

**Trigger:** alert payload received OR human said "this is an incident, help".

**Goal:** within 5 minutes, have (a) a dedicated channel, (b) a tracking ticket, (c) the right humans paged, (d) initial context posted.

## Step-by-step

### 1. Acknowledge the page

If the alert came from Opsgenie / PagerDuty:
```
opsgenie_manage action=ack_alert --alert_id <id> --user "rovo-dev-on-behalf-of-<user>"
```

If only Alertmanager fires (no oncall integration):
```
alertmanager_query action=acknowledge --alert_name <name> --comment "Investigating, will update in 15 min"
```

### 2. Identify the affected service

Try in this order until one yields a service name:

a. The alert payload's `service`/`namespace`/`labels.app` field
b. The alert's source dashboard's title
c. `runbook_search action=search --query "<alert name>"` and read the linked runbook's affected-service line
d. `twg_twg_atlassian_graph_get_user_owned_entities --userId <pager>` to find what the paged human owns

If steps a-d all fail → ASK THE HUMAN. Never guess.

### 3. Spin up the incident channel

Naming convention: `inc-YYYY-MM-DD-<short-service>-<short-symptom>`
Example: `inc-2026-04-30-checkout-api-5xx-spike`

Tool call:
```
slack_slack_atlassian_workspace_create_channel_with_members
  channelName: "inc-2026-04-30-checkout-api-5xx-spike"
  isPrivate: false
  usersIds: [<paged-oncall>, <service-owner>, <#incidents-channel-monitor>]
```

**If channel creation fails** (rate limit, name conflict): post in the existing #incidents channel with the alert summary; tag the on-call.

### 4. Post the kickoff message

In the new channel:
```
slack_slack_atlassian_channel_create_message
  channelId: <new-channel-id>
  text: |
    [INCIDENT START] <service> — <one-line symptom>
    Severity: <P1/P2/P3 — best guess>
    Page link: <opsgenie/PD URL>
    Affected dashboards:
      - <grafana url>
    On-call: @<paged-user>
    Service owner: @<owner-or-team>
    Status: investigating — first update in 10 min
```

### 5. Open the incident Jira ticket

```
atlassian_create_jira_issue
  project_url: "<incident project URL>"
  issue_type: "Incident"
  summary: "<service> — <one-line symptom>"
  description_html: "<HTML rendering of the kickoff message + alert payload>"
  fields:
    severity: "<P1/P2/P3>"
    affected_service: "<service>"
```

### 6. Pin context to the channel

⚠️ Slack pin is NOT exposed in Rovo Dev's Slack MCP today. Workaround:
- Post a STATUS message with a `[STATUS]` prefix at the top of the channel
- Edit that message as state changes (use the same MCP `channel_create_message` action; `threadTs` not required for top-level edits — but edit-in-place is also not exposed; if not available, post a new STATUS message and reference it via permalink)

Honest limitation: without pin/edit, the channel order will show STATUS messages chronologically, not at top. Document this in the kickoff message: `(Note: latest STATUS message is the source of truth — see thread.)`

## Done criteria

- Channel exists with the right people in it
- Jira ticket exists and is linked from the channel
- Kickoff message posted with severity + affected dashboards + ETA for next update
- Page is acknowledged in Opsgenie

## Failure modes

- **No Slack channel rights**: post in the user's DM with the same kickoff content; instruct them to create the channel manually
- **No Jira project visible**: ask the human for the project key
- **No service owner found**: post the kickoff message with `Service owner: TBD — please claim by reacting :hand:` (note: react not exposed in Slack MCP — use a thread reply with `[CLAIM]` prefix instead)
