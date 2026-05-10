# SOP: Communication cadence

**Trigger:** active incident (channel + ticket exist).

**Goal:** keep stakeholders informed without overloading the incident channel or the IC.

## Cadence rules

| Severity | First update | Subsequent updates | Where |
|---|---|---|---|
| P1 (full outage / data loss risk) | Within 5 min of kickoff | Every 15 min | Incident channel + #incidents (announce-only) |
| P2 (major feature broken) | Within 10 min | Every 30 min | Incident channel only |
| P3 (degraded but workable) | Within 15 min | Every 60 min | Incident channel only |

The agent SHOULD volunteer to draft each update. The IC posts.

## Update message format

```
[STATUS — <HH:MM PT> | <Δ from start>]
Current state: <one sentence>
Latest evidence: <one sentence — link to graph or log query>
Next step: <one sentence — what's being tried, by whom, ETA>
ETA to mitigation: <best guess or "unknown — investigating">
```

## When to escalate

The agent SHOULD propose escalating (paging next-tier on-call, paging the engineering manager, paging the comms team) if any of:

- 30 min elapsed at P1 with no mitigation
- 60 min elapsed at P2 with no mitigation
- The hypothesis has changed 3 times (we don't know what's wrong)
- Customer impact has worsened despite an attempted mitigation
- Data-loss risk is identified at any point (escalate immediately)

The escalation is proposed via:
```
slack_slack_atlassian_channel_create_message
  channelId: <incident channel>
  text: "[ESCALATION PROPOSAL] We've been at this for <N> min with no mitigation; recommend paging <role>. @IC — your call."
```
The agent does NOT page the next tier itself.

## When to de-escalate

When mitigation is verified (10+ consecutive minutes of recovery on the primary symptom metric):
```
[STATUS — DE-ESCALATING]
Mitigation verified at <ts>. Symptom <X> back to baseline for 10+ min.
Channel will stay open for postmortem prep. Next update: postmortem draft within 24h.
```

## Anti-patterns

- ❌ "Still looking" with no detail (gives no signal)
- ❌ Speculation in the channel without flagging it as such (use `[HYPOTHESIS]` prefix)
- ❌ Tagging customers or executives until the IC explicitly approves (the agent NEVER does this on its own)
- ❌ Reaction-only updates (the Slack MCP doesn't expose reactions; even if it did, reactions don't carry signal across timezones)
