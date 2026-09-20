---
name: program-health-reporting
description: >
  Monitor AI/ML program health across Jira, Atlas, Confluence, and ML observability tools.
  Generate status reports, executive briefings, and daily digests with RAG (Red/Amber/Green)
  ratings, risk summaries, and calls to action. Supports five reporting workflows:
  Pulse Scan, Weekly Status Report, Executive Briefing, Daily Digest, and Weekly Async Status.
labels:
  - ai-tpm
  - program-management
  - reporting
  - status
  - rag-health
metadata:
  requires:
    env: [TWG_USER, TWG_SITE, TWG_TOKEN, SLACK_BOT_TOKEN]
    env_optional: [SLACK_USER_TOKEN, TWG_BBC_TOKEN]
  tools:
    - twg
    - slack_send_message
    - slack_find_channel
    - slack_search
    - task
---

# Program Health & Status Reporting

## Overview

This skill enables an AI Technical Program Manager (AI TPM) to continuously monitor program health across Atlassian tools (Jira, Atlas Goals/Projects, Confluence) and generate structured reports with RAG (Red/Amber/Green) ratings. It covers five reporting workflows — from real-time pulse scans to executive briefings — each with clear autonomy levels, output formats, and escalation rules.

The skill leverages the TWG CLI for cross-product data collection, Jira MCP tools for JQL-based queries, Slack tools for digest delivery, and Confluence for structured report publishing.

## Prerequisites

### Runtime Requirements
- macOS (arm64/x64) or Linux (x64)
- TWG CLI installed and authenticated (`twg login` or env vars)
- Slack bot token with channel posting permissions

### Authentication
- **TWG**: `TWG_USER` + `TWG_TOKEN` env vars (or `twg login`)
- **Slack**: `SLACK_BOT_TOKEN` for posting messages
- **Bitbucket** (optional): `TWG_BBC_TOKEN` for PR/pipeline signals

### Program Configuration (required per program)

Before first use, configure the following for each AI program:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `program_id` | Atlas project ARI or Jira project key | `MLPLAT` |
| `jira_projects` | Jira project keys in scope | `["MLPLAT", "MLOPS", "AIENG"]` |
| `slack_channels.status` | Channel for status updates | `#ml-platform-status` |
| `slack_channels.alerts` | Channel for critical alerts | `#ml-platform-alerts` |
| `slack_channels.exec` | Channel for exec briefings | `#ml-platform-exec` |
| `stakeholder_groups` | Audience definitions for routing | `{"exec": [...], "eng": [...]}` |
| `rag_thresholds` | Override default thresholds (optional) | See `references/RAG-THRESHOLDS.md` |
| `risk_tier` | Program risk tier: standard or high-stakes | `high-stakes` |

## Required Reading — Load Before Executing

Before running any reporting workflow, read the following reference files in order:

1. **`references/RAG-THRESHOLDS.md`** — RAG rating definitions, scoring rubrics, and threshold values for all dimensions (Schedule, Scope, Budget, Quality, Resources, Stakeholder). Read first to understand how health signals map to Red/Amber/Green.
2. **`references/JQL-PATTERNS.md`** — Jira query patterns for extracting milestones, blockers, dependencies, velocity, and sprint health across AI program projects.
3. **`references/REPORT-TEMPLATES.md`** — Output templates for each workflow: Confluence ADF structures and Slack message formats.
4. **`references/ESCALATION-MATRIX.md`** — Routing rules for escalations, audience-specific delivery channels, and approval requirements by report type.

Then load the reference matching your workflow:

| Workflow | Additional Reference |
|----------|---------------------|
| Pulse Scan | (core references sufficient) |
| Weekly Report | `references/REPORT-TEMPLATES.md` §Weekly |
| Executive Briefing | `references/REPORT-TEMPLATES.md` §Executive |
| Daily Digest | (core references sufficient) |
| Weekly Async | `references/REPORT-TEMPLATES.md` §Async |

## Shared Data Collection Patterns

All workflows begin with data collection from the same sources. Scope and depth vary per workflow.

### Signal Sources (in collection order)

| Source | Command | Signal Type |
|--------|---------|-------------|
| Jira milestones & epics | `twg jira workitem get --id <key>` | Delivery status, due dates, blockers |
| Jira sprint health | `twg jira space status list --space <project>` | Velocity, scope changes, carry-over |
| Atlas project status | `twg projects --scope me --role contributor` | OKR progress, goal alignment |
| Atlas goals | `twg goals --scope me --include-contributing-projects` | Strategic alignment |
| Confluence pages | `twg confluence search query --cql '...'` | Documentation freshness |
| Cross-product activity | `twg work query --scope user --account-id <id> --since <period>` | Team activity patterns |
| Dependency graph | `twg context jira workitem <key> --depth 2` | Cross-team dependency health |

### Common JQL Patterns

```bash
# Slipping milestones (due in next 7 days, not Done)
twg jira workitem get --jql "project in (<projects>) AND type = Epic AND duedate <= 7d AND status != Done"

# Blocked items
twg jira workitem get --jql "project in (<projects>) AND status = Blocked"

# Unestimated work in active sprint
twg jira workitem get --jql "project in (<projects>) AND sprint in openSprints() AND originalEstimate is EMPTY"

# Recently resolved (for accomplishments)
twg jira workitem get --jql "project in (<projects>) AND resolved >= -7d ORDER BY resolved DESC"

# High-priority items not progressing
twg jira workitem get --jql "project in (<projects>) AND priority in (Highest, High) AND status = 'In Progress' AND updated <= -3d"

# WIP overload detection
twg jira workitem get --jql "project in (<projects>) AND status = 'In Progress' AND assignee is not EMPTY"
```

### Pivot Strategy

Follow TWG routing conventions:
1. Start with projection surfaces (`work query`) for broad activity scanning
2. Pivot to native surfaces (`jira`, `confluence`) for specific detail
3. Use context surfaces for dependency analysis
4. If a surface returns empty, pivot — do not retry the same surface

## Workflow Index

| # | Workflow | Trigger | Cadence | Autonomy | Primary Output |
|---|---------|---------|---------|----------|----------------|
| 1 | **Pulse Scan** | On-demand / scheduled | Real-time / daily | 🟢 Fully autonomous | Internal data structure |
| 2 | **Weekly Report** | Monday morning | Weekly | 🟢 Draft auto; 🔴 Exec needs approval | Confluence + Slack |
| 3 | **Executive Briefing** | Monthly / quarterly | Monthly | 🟡 Draft auto; 🔴 Human approval required | Confluence page |
| 4 | **Daily Digest** | End of business | Daily | 🟢 Fully autonomous | Slack message |
| 5 | **Weekly Async** | Friday afternoon | Weekly | 🟢 Auto; 🔴 High-stakes needs confirm | Confluence + Slack |

## Workflow 1: Pulse Scan

### Trigger & Cadence
- **Trigger:** On-demand or scheduled (e.g., every 4 hours)
- **Cadence:** Real-time / daily
- **Scope:** All configured programs

### Autonomy Level
🟢 Fully autonomous — collects and processes data without human intervention.

### Steps

1. **Enumerate programs** — Load program configuration to get `jira_projects` list and `program_id`.

2. **Collect Jira signals** — For each program, run JQL queries:
   ```bash
   # Slipping milestones
   twg jira workitem get --jql "project in (<projects>) AND type = Epic AND duedate <= 7d AND status != Done"
   
   # Blocked items
   twg jira workitem get --jql "project in (<projects>) AND status = Blocked"
   
   # WIP status
   twg jira workitem get --jql "project in (<projects>) AND status = 'In Progress'"
   
   # Recently completed
   twg jira workitem get --jql "project in (<projects>) AND resolved >= -1d ORDER BY resolved DESC"
   ```

3. **Collect Atlas signals** — Fetch goal and project health:
   ```bash
   twg goals --scope me --include-contributing-projects
   twg projects --scope me --role contributor
   ```

4. **Collect activity signals** — Scan cross-product work:
   ```bash
   twg work query --scope me --since 1d
   ```

5. **Compute per-dimension RAG** — Apply thresholds from `references/RAG-THRESHOLDS.md`:
   - Schedule: based on milestone slip count and severity
   - Scope: based on unestimated work ratio and scope change velocity
   - Resources: based on WIP counts, blocked item age, team utilization
   - Quality: based on bug escape rate, test coverage signals (if available)
   - For each dimension, produce: `{status: "green"|"amber"|"red", confidence: "high"|"medium"|"low", rationale: "..."}`

6. **Compute overall RAG** — Use worst-dimension rule:
   - Overall = worst individual dimension status
   - Exception: single Amber with strong mitigation + all others Green → Overall can be Green with medium confidence
   - Always include confidence level and rationale

7. **Detect exceptions** — Flag items where:
   - RAG status changed since last scan (state transition)
   - New blockers appeared (age < 24h)
   - Milestones slipped that were previously on track
   - WIP exceeded threshold for any column

8. **Store pulse data** — Persist structured result for downstream workflows:
   ```json
   {
     "program_id": "MLPLAT",
     "timestamp": "2026-04-27T16:00:00Z",
     "status_overall": "amber",
     "status_schedule": "green",
     "status_scope": "green",
     "status_resources": "amber",
     "status_quality": "green",
     "confidence": "medium",
     "exceptions": [...],
     "rationale": "WIP overload in 2 columns; 3 items blocked >48h"
   }
   ```

### Output
- Internal structured data (JSON) consumed by downstream workflows
- No external publication — this is a data-gathering workflow

### Fallback & Escalation
- If TWG CLI returns errors: retry once, then log warning and proceed with partial data
- If Atlas goals/projects return empty: note "Atlas data unavailable" in rationale
- If >50% of data sources fail: escalate to human with "Pulse Scan degraded — manual review needed"

---

## Workflow 2: Weekly Status Report

### Trigger & Cadence
- **Trigger:** Monday morning (automated)
- **Cadence:** Weekly
- **Scope:** Per-program

### Autonomy Level
🟢 Auto-generate draft. 🔴 Executive-audience versions require human approval before distribution.

### Steps

1. **Run Pulse Scan** (Workflow 1) — If not run in last 4 hours, trigger fresh scan.

2. **Collect extended signals** — Beyond pulse data, gather:
   ```bash
   # Sprint metrics
   twg jira space status list --space <project>
   
   # Accomplishments (last 7 days)
   twg jira workitem get --jql "project in (<projects>) AND resolved >= -7d ORDER BY resolved DESC"
   
   # Dependency analysis for blocked items
   twg context jira workitem <blocked-key> --depth 2
   ```

3. **Synthesize narrative** — For each section of the report:
   - **Overall Status**: RAG badge + 2-3 sentence summary
   - **Key Accomplishments**: Top 5 completed items with impact notes
   - **Risks & Blockers**: Each with RAG, owner, mitigation, and ETA
   - **Upcoming Milestones**: Next 2 weeks, with confidence assessment
   - **Metrics Dashboard**: Velocity trend, WIP, cycle time, bug count
   - **Dependencies**: Cross-team items with status and owners
   - **Asks / Help Needed**: Concrete asks with audience routing

4. **Generate Confluence page** — Use ADF template from `references/REPORT-TEMPLATES.md`:
   ```bash
   twg confluence pages create --space <space-key> --title "Weekly Status: <program> — Week of <date>" --body-adf '<adf_json>'
   ```
   - If page for this week exists, update instead:
   ```bash
   twg confluence pages update --id <page-id> --body-adf '<adf_json>'
   ```

5. **Post Slack summary** — Compact digest pointing to full Confluence page:
   ```bash
   slack_send_message channel:<status-channel> "<weekly_summary_mrkdwn>"
   ```
   Format: RAG emoji + program name + 1-line summary + link to Confluence page

6. **Check audience routing**
   - → If audience includes executives: hold for human approval before cross-posting
   - → If team-only: post directly

### Output Format
- **Confluence page**: Structured ADF with status panels, tables, and expand sections
- **Slack**: Compact summary message with link to full report

### Fallback & Escalation
- If Confluence create/update fails: post full report content to Slack as fallback
- If data is incomplete: clearly mark sections as "Data pending — will update"
- If overall RAG is Red: auto-escalate notification to program leader

---

## Workflow 3: Executive Briefing

### Trigger & Cadence
- **Trigger:** Monthly or quarterly (scheduled or on-demand)
- **Cadence:** Monthly
- **Scope:** Portfolio-level (multiple programs)

### Autonomy Level
🟡 Auto-generate draft. 🔴 **Human approval required before any distribution** — this is a hard constraint.

### Steps

1. **Aggregate pulse data** — Collect latest Pulse Scan results across all programs in portfolio.

2. **Collect strategic signals**:
   ```bash
   twg goals --scope org --include-contributing-projects
   twg projects --scope me --role contributor
   ```

3. **Cross-program dependency analysis** — For each blocked or at-risk item:
   ```bash
   twg context jira workitem <key> --depth 2
   ```

4. **Synthesize executive narrative**:
   - **Portfolio Health Dashboard**: Table with program × dimension RAG grid
   - **Top 3 Risks**: Highest-impact risks across all programs with mitigation status
   - **Strategic Alignment**: Goal progress vs. quarterly targets
   - **Resource Concerns**: Cross-program resource contention
   - **Decisions Needed**: Concrete decision items for exec audience
   - Tone: decision-oriented, narrative-light, evidence-linked
   - Maximum 2 pages / 5 minutes reading time

5. **Generate Confluence page**:
   ```bash
   twg confluence pages create --space <exec-space> --title "Executive Briefing: <portfolio> — <month> <year>" --body-adf '<adf_json>'
   ```

6. **Route for human approval**:
   ```bash
   slack_send_message user:<program-leader-id> "Executive briefing draft ready for review: <confluence_link>"
   ```
   - ⚠️ DO NOT distribute to executive audience until explicit human approval

### Output Format
- **Confluence page**: Executive briefing with dashboard tables, trend indicators, and decision boxes
- **Slack**: Notification to reviewer only (not to exec audience)

### Delivery
Draft → human reviewer → approved version → exec distribution channel

### Fallback & Escalation
- If human reviewer does not respond within 24h: send reminder
- If data gaps exist: clearly mark "Data unavailable — manual input needed" sections
- **Never distribute exec briefing without human approval** — this is a hard constraint

---

## Workflow 4: Daily Digest

### Trigger & Cadence
- **Trigger:** End of business (automated)
- **Cadence:** Daily
- **Scope:** All active programs

### Autonomy Level
🟢 Fully autonomous — post directly to team channels.

### Steps

1. **Quick pulse scan** — Lightweight version of Workflow 1, focused on exceptions only:
   ```bash
   twg jira workitem get --jql "project in (<projects>) AND status changed TO Blocked AFTER -1d"
   twg jira workitem get --jql "project in (<projects>) AND duedate < now() AND status != Done AND status changed AFTER -1d"
   ```

2. **Activity summary**:
   ```bash
   twg work query --scope me --since 1d
   ```
   Count: items completed, items started, items blocked.

3. **Compose daily digest** — Exception-based format:
   - If no exceptions: post "All programs nominal ✅" (or skip if configured for silence)
   - If exceptions exist: one bullet per exception, max 5 items
   - If >5 exceptions: show top 5 by severity + "+N more — see dashboard"
   - Keep under 10 lines total

4. **Post to Slack**:
   ```bash
   slack_send_message channel:<daily-digest-channel> "<daily_digest>"
   ```

### Output Format
- **Slack only**: Compact message using mrkdwn formatting

### Slack Message Template
```
📡 Daily Program Pulse — <date>

*Exceptions in the last 24h:*
• 🔴 *<program/stream>* — <short description>
• 🟡 *<program/stream>* — <short description>

_<N> programs nominal ✅ · Updated <time> · <dashboard_link>_
```

### Fallback & Escalation
- If critical blocker detected (Red status): also post to alerts channel
- If all-nominal for 5+ consecutive days: include "steady state" note to confirm monitoring is active
- If Slack post fails: retry once, then log error

---

## Workflow 5: Weekly Async Status

### Trigger & Cadence
- **Trigger:** Friday afternoon (automated)
- **Cadence:** Weekly
- **Scope:** Per-program

### Autonomy Level
🟢 Auto-generate and post for standard programs. 🔴 High-stakes programs require human confirmation.

### Steps

1. **Pull weekly data** — Reuse Workflow 2 data if available this week:
   - If Weekly Report ran: reference its data
   - If not: run abbreviated data collection (Pulse Scan + accomplishments query)

2. **Compose async status update** — Follow template:
   - **RAG Status**: Overall + per-dimension badges
   - **This Week**: Top accomplishments (3-5 items)
   - **Next Week**: Key planned items
   - **Risks**: Active risks with owners
   - **Help Needed**: Concrete asks
   - Tone: concise, action-oriented, team-facing (not exec)
   - Maximum 15 lines in Slack format

3. **Check program risk tier**:
   - → If `risk_tier == "high-stakes"`: hold for human confirmation
   - → If `risk_tier == "standard"`: post directly

4. **Publish to Confluence**:
   ```bash
   twg confluence pages create --space <space-key> --title "Weekly Async: <program> — <date>" --body-adf '<adf_json>'
   ```

5. **Post to Slack** — Compact version pointing to Confluence:
   ```bash
   slack_send_message channel:<status-channel> "<async_summary>"
   ```

### Output Format
- **Confluence page**: Structured async update
- **Slack**: Compact summary with RAG badges and link

### Slack Message Template
```
📊 Weekly Async Status — <program> (<date>)

🟢 Overall: On Track | Schedule 🟢 | Scope 🟢 | Resources 🟡

*This Week:*
• Completed migration of data pipeline to v2
• Resolved 3 critical blockers in inference service

*Next Week:*
• Launch readiness review (Wed)
• Performance benchmarking sprint

*Risks:* 🟡 GPU allocation timeline uncertain — escalated to infra

<confluence_link>
```

### Fallback & Escalation
- If Confluence publish fails: post full content to Slack as fallback
- If program is high-stakes and no human confirms within 4h: send reminder

## RAG Rating Logic

### Dimension Definitions

| Dimension | Green (On Track) | Amber (At Risk) | Red (Off Track) |
|-----------|-----------------|-----------------|-----------------|
| **Schedule** | All milestones on track; no critical-path impact | 1-2 milestones slipping ≤1 week; mitigation in progress | Critical milestones missed by >1 week; critical path impacted |
| **Scope** | Scope stable; <5% unestimated work in sprint | 5-15% scope change this sprint; some unestimated work | >15% scope change; significant unplanned work; scope creep |
| **Budget** | Cost variance ≤5%; CPI 0.95-1.05 | Cost variance 5-10%; CPI 0.90-0.95 | Cost variance >10%; CPI <0.90 |
| **Quality** | Bug escape rate within target; test coverage stable | Bug rate trending up; coverage declining | Critical bugs in production; SLO breached |
| **Resources** | WIP within limits; no chronic blockers | WIP over limit in 1-2 columns >1 week; some blockers >48h | Chronic WIP breach; many items blocked >48h; key people unavailable |
| **Stakeholder** | Sentiment ≥4/5; no escalations | Sentiment 3/5 or declining; minor escalations | Sentiment ≤2/5; repeated severe escalations; Sev-1 incidents |

### Overall RAG Computation

1. Compute individual dimension RAG status using thresholds above
2. Apply worst-dimension rule: `overall = max(all_dimensions)` where Red > Amber > Green
3. Exception: if only ONE dimension is Amber with documented mitigation AND all others Green → Overall may be Green with `confidence: "medium"`
4. Always include `confidence` (high/medium/low) and `rationale` in output

### Confidence Levels

| Level | Criteria |
|-------|----------|
| **High** | All data sources returned complete data; thresholds clearly met/exceeded |
| **Medium** | Some data sources partial or stale (>24h old); borderline threshold values |
| **Low** | Major data gaps; assessment based on limited signals; manual override applied |

### State Transition Alerts

Only alert on **meaningful state changes**, not on every data refresh:
- **Green → Amber**: Log, include in next digest
- **Amber → Red**: Alert immediately to alerts channel + program leader
- **Red → Amber**: Log, include in next digest (positive signal)
- **Amber → Green**: Log, include in weekly report (recovery)
- **Stable state**: No alert — include in regular cadence reports only

## Output Formatting Guidelines

### Slack Message Conventions

- Always pair RAG emoji with textual label — do not rely on color alone
- RAG emoji mapping: 🟢 = On Track, 🟡 = At Risk, 🔴 = Off Track
- Use `*bold*` for program/stream names and key metrics
- Use bullet lists (`•`) for exception items, one per line
- Keep daily digests under 10 lines; weekly summaries under 15 lines
- Include timestamp and dashboard/Confluence link in `_italic_` context line
- For >5 exception items, show top 5 by severity + "+N more" with link

### Confluence Report Conventions

- Use ADF (Atlassian Document Format) for structured pages
- Include status panels with colored backgrounds for RAG sections
- Use tables for metrics dashboards and milestone tracking
- Use expand/collapse sections for detailed data (keep summary scannable)
- Title format: `<Report Type>: <Program> — <Date/Period>`
- Always include "Last Updated" timestamp at top of page

## Integration Metadata

### Tools Referenced

| Tool | Operations Used | Purpose |
|------|----------------|---------|
| `twg` | `jira workitem get`, `jira space status list`, `goals`, `projects`, `work query`, `context jira workitem`, `confluence pages create/update`, `confluence search query` | Primary data collection and Confluence publishing |
| `slack_send_message` | `channel:<id> "<message>"` | Post digests, alerts, and summaries to Slack |
| `slack_find_channel` | Search by channel name | Resolve channel names to IDs |
| `slack_search` | `query:<terms>` | Find previous status messages for threading |
| `task` | Create/manage subtasks | Orchestrate multi-step workflows |

### Cross-Tool Patterns

1. **Data → Analysis → Publish**: TWG (collect Jira/Atlas data) → compute RAG → TWG (publish Confluence) + Slack (post digest)
2. **Exception Detection → Alert**: TWG (pulse scan) → detect state change → Slack (post to alerts channel)
3. **Draft → Review → Distribute**: TWG (generate report) → Slack (notify reviewer) → human approval → Slack (distribute to audience)
4. **Reuse Pattern**: Weekly Async (Workflow 5) reuses Weekly Report (Workflow 2) data when available to avoid redundant queries

### Autonomy Levels

| Operation | Autonomy | Notes |
|-----------|----------|-------|
| Data collection (all sources) | 🟢 Autonomous | Always safe to read |
| RAG computation | 🟢 Autonomous | Rule-based, deterministic |
| Daily digest posting | 🟢 Autonomous | Team-facing, low risk |
| Weekly report draft | 🟢 Autonomous | Draft generation is safe |
| Weekly report distribution (team) | 🟢 Autonomous | Team-facing, standard |
| Weekly report distribution (exec) | 🔴 Human approval | Exec-facing content |
| Executive briefing (any) | 🔴 Human approval | Always requires approval |
| Weekly async (standard programs) | 🟢 Autonomous | Standard risk tier |
| Weekly async (high-stakes) | 🔴 Human approval | High-stakes programs |
| RAG override (Red → lower) | 🔴 Human approval | Safety-critical transition |
| Escalation notifications | 🟢 Autonomous | Alert routing is safe |

## Guardrails and Escalation

### Safety Boundaries — What NOT To Do Autonomously

1. **Never distribute executive briefings without human approval** — this is a hard constraint
2. **Never override a Red RAG to Amber/Green** without human confirmation and documented rationale
3. **Never post to external/customer-facing channels** — all outputs go to internal team channels only
4. **Never delete or modify existing Confluence pages** created by humans — only create new pages or update AI-generated pages
5. **Never fabricate metrics** — if data is unavailable, report "Data unavailable" rather than estimating
6. **Never suppress Red alerts** — all Red status transitions must be surfaced regardless of alert fatigue settings

### Escalation Triggers

| Trigger | Action | Channel |
|---------|--------|---------|
| Any dimension transitions to Red | Immediate alert to program leader | `slack_channels.alerts` |
| Overall status is Red for >48h | Escalate to skip-level leader | `slack_channels.exec` |
| >50% of data sources fail | Alert: "Pulse Scan degraded" | `slack_channels.alerts` |
| Human approval not received within 24h | Send reminder notification | DM to approver |
| Blocked items aged >5 days with no update | Flag in daily digest + alert | `slack_channels.status` |
| Multiple programs simultaneously Red | Portfolio-level escalation | `slack_channels.exec` |

### Error Handling

| Error | Response |
|-------|----------|
| TWG CLI timeout/error | Retry once; if still failing, proceed with partial data and note in report |
| Atlas goals/projects empty | Mark "Atlas data unavailable" in rationale; do not block report |
| Slack post fails | Retry once; if still failing, log error and attempt alternate channel |
| Confluence page create fails | Post full report content to Slack as fallback |
| JQL returns no results | Distinguish between "no items match" (valid) vs. "query error" (log warning) |
| Authentication expired | Log error; do not retry — alert human to re-authenticate |

## Common Patterns

### Quick Health Check (Single Program)
```bash
# 1. Get blocked items
twg jira workitem get --jql "project = MLPLAT AND status = Blocked"

# 2. Get slipping milestones
twg jira workitem get --jql "project = MLPLAT AND type = Epic AND duedate <= 7d AND status != Done"

# 3. Get Atlas project health
twg projects --scope me --role contributor

# 4. Compute RAG per references/RAG-THRESHOLDS.md
# 5. Post result to Slack
slack_send_message channel:#ml-platform-status "🟢 MLPLAT: All systems nominal. 0 blockers, milestones on track."
```

### Cross-Program Portfolio Scan
```bash
# Scan all programs
for project in MLPLAT MLOPS AIENG; do
  twg jira workitem get --jql "project = $project AND status = Blocked"
  twg jira workitem get --jql "project = $project AND type = Epic AND duedate <= 7d AND status != Done"
done

# Aggregate RAG across programs
# Generate portfolio dashboard table
```

### Dependency Investigation
```bash
# Deep-dive on a blocked item
twg context jira workitem MLPLAT-456 --depth 2

# Check cross-team dependencies
twg jira workitem get --jql "issue in linkedIssues(MLPLAT-456) AND project != MLPLAT"
```

## References

| File | Description |
|------|-------------|
| `references/RAG-THRESHOLDS.md` | Complete RAG threshold definitions for all dimensions with numeric and qualitative rules |
| `references/JQL-PATTERNS.md` | Jira query patterns for all signal types: milestones, blockers, velocity, WIP, dependencies |
| `references/REPORT-TEMPLATES.md` | Output templates: Confluence ADF structures, Slack message formats for all 5 workflows |
| `references/ESCALATION-MATRIX.md` | Escalation routing rules, approval requirements, and audience definitions |
