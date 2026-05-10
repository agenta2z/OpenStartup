# Data-Driven Retrospectives & Operating Cadence for AI/ML Teams

Reference patterns for running data-driven retrospectives with automated metric collection,
and designing operating cadences with auto-generated agendas for AI/ML teams.

Related skill: `ai-tpm-program-management` (Workflows 2.3 and 2.4)

---

## 1. Retrospective Document Structure

Every data-driven retrospective should follow this Confluence page layout:

### Section 1: Overview
```
| Field | Value |
|-------|-------|
| Period | [Start date] — [End date] |
| Team | [Team name] |
| Facilitator | [Name] |
| Participants | [Names] |
| Retro Type | Sprint / Monthly Ops / Quarterly |
| Previous Retro | [Link to prior retro page] |
```

### Section 2: What Worked
- Evidence-backed wins (not just feelings)
- Each item paired with supporting metric or artifact
- Example: "Cycle time improved by 0.7 days p50 due to smaller batch sizes and clearer acceptance criteria."

### Section 3: What Didn't Work
- Issues with root cause analysis (not blame)
- Categorize: Process | Technical | Communication | Dependency | Capacity
- Flag if this is a recurring issue (link to prior retro where it appeared)

### Section 4: Metrics Deltas
```
| Metric | Previous Period | Current Period | Delta | Trend |
|--------|----------------|----------------|-------|-------|
| Velocity (story points) | [N] | [N] | [+/-] | ↑/↓/→ |
| Cycle time (p50, days) | [N] | [N] | [+/-] | ↑/↓/→ |
| Deployment frequency | [N/week] | [N/week] | [+/-] | ↑/↓/→ |
| Error budget remaining | [N%] | [N%] | [+/-] | ↑/↓/→ |
| Incident count (Sev 1-2) | [N] | [N] | [+/-] | ↑/↓/→ |
| Model eval score | [N] | [N] | [+/-] | ↑/↓/→ |
```

### Section 5: Risk Surprises
- Unexpected issues not previously tracked
- Emerging risks that need proactive attention
- Each with: description, evidence, suggested risk type (emerging/escalating/new)

### Section 6: Action Plan
```
| # | Action | Owner | Priority | Evidence | Target Sprint |
|---|--------|-------|----------|----------|---------------|
| 1 | [Action] | @[name] | High/Med/Low | [What data supports this] | [Sprint N] |
```

### Section 7: SOP Update Suggestions
- Only when recurring patterns are detected
- Each with: SOP area, current gap, evidence, proposed change, urgency, human review flag

---

## 2. Data Sources for Automated Collection

### Quantitative Sources
| Data Point | Source | TWG Command |
|-----------|--------|-------------|
| Completed stories/points | Jira work queries | `twg work query --scope user --account-id <id> --since <period>` |
| Jira issue transitions | Issue context | `twg context jira workitem <KEY> --depth 2` |
| Sprint data | Jira sprints | `twg jira workitem get --id <sprint-epic>` |
| Atlas goal progress | Atlas goals | `twg goals get <goal-id>` |

### Qualitative Sources (via Slack)
| Signal | Slack Query |
|--------|------------|
| Blockers | `"blocked OR blocker in:#<channel> after:<start>"` |
| Wins | `"shipped OR launched OR milestone in:#<channel> after:<start>"` |
| Decisions | `"decided OR approved in:#<channel> after:<start>"` |
| Incidents | `"PIR OR incident OR outage in:#<ops-channel> after:<start>"` |
| SLO burns | `"SLO OR error budget in:#<ops-channel> after:<start>"` |
| Deployments | `"deployed OR released in:#<deploy-channel> after:<start>"` |

### Historical Patterns (via Knowledge Base)
```
kn search "<issue description>" --space retro-insights --limit 10
```

---

## 3. SOP Update Detection Logic

### When to Suggest SOP Updates (Not Just Action Items)

| Trigger | Detection Method | Urgency |
|---------|-----------------|---------|
| Same issue in ≥2 consecutive retros | Knowledge search for recurring themes | High |
| Same SLO breach type ≥3x in quarter | Slack search for SLO alerts + PIRs | High |
| Prior retro action item incomplete | Knowledge check for unresolved actions | Medium |
| New failure mode with no runbook coverage | Gap analysis against runbook library | Medium |
| Unclear escalation path in ≥2 incidents | PIR analysis for ownership gaps | High |
| Same dependency blocker across teams | Cross-team retro pattern matching | Medium |

### Structured SOP Suggestion Format
```json
{
  "sopNameOrArea": "SLO Runbook / TechOps",
  "currentGapSummary": "No trigger to require PIR when error budget trend deteriorates",
  "evidence": ["SLO burn events without PIR", "PIR notes on ignored trends"],
  "proposedChange": "Add section for SLO burn investigation threshold",
  "urgency": "High",
  "requiresHumanReview": true
}
```

---

## 4. Operating Cadence Reference

### Default AI/ML Team Cadence

| Frequency | Ritual | Duration | Audience | Data Inputs | Outputs |
|-----------|--------|----------|----------|-------------|---------|
| 2-4x/week | Standup | 15 min | Core team | Jira board, blockers | Status update, blocker list |
| Weekly | Planning/Review | 30-60 min | Core team + PM | Backlog, sprint metrics | Sprint plan, priorities |
| Bi-weekly | Demo | 30-45 min | Extended team | Completed work | Demo recordings, feedback |
| Bi-weekly | Retrospective | 45-60 min | Core team | Metrics, Slack signals | Retro page, action items |
| Bi-weekly | TechOps Review | 30 min | Eng + SRE | SLOs, incidents, alerts | Health status, actions |
| Monthly | Ops Deep Dive | 60 min | Leads + SRE | SLOs, capacity, cost | Ops report, investments |
| Monthly | Program Review | 60 min | Leads + sponsor | Atlas goals, roadmap | Status update, decisions |
| Quarterly | Planning | Half-day | All | Goals, roadmap, deps | Quarter plan, OKRs |
| Quarterly | Extended Retro | 90 min | All | Quarter metrics | Systemic improvements |

### Cadence Adjustment by Maturity

**New team (0-3 months)**: Daily sync standup, weekly retro, weekly planning. Focus on norms.

**Growing team (3-12 months)**: 2-3x/week async standup, bi-weekly retro, weekly planning. Add monthly ops review.

**Mature team (12+ months)**: Async standup, bi-weekly planning, bi-weekly retro. Monthly portfolio review. Exception-based sync.

---

## 5. Auto-Generated Agenda Templates

### Weekly Sync Agenda
```
# [Team] Weekly Sync — [Date]

## Progress Since Last Sync
[Auto-generated from: twg work query --since 7d]
- Completed: [list of completed items]
- In Progress: [list of active items]

## Current Blockers
[Auto-generated from: Slack search for "blocker" + Jira blocked issues]
- [Blocker 1]: [context]
- [Blocker 2]: [context]

## This Week's Priorities
[Auto-generated from: Jira sprint backlog, sorted by priority]
1. [Priority item]
2. [Priority item]

## Discussion Topics
[Placeholder for human-added items]

## Action Items from Last Week
[Auto-generated from: knowledge base search for prior week's actions]
- [ ] [Action]: [owner] — [status]
```

### Monthly Ops Review Agenda
```
# [Team] Monthly Ops Review — [Month Year]

## SLO Status
[Auto-generated from: Slack SLO channel search + dashboard links]
| SLO | Target | Actual | Status |
|-----|--------|--------|--------|

## Incident Summary
[Auto-generated from: Slack incident channel search]
| Date | Severity | Title | TTD | TTR | PIR Link |

## Deployment Summary
[Auto-generated from: Slack deploy channel search]
- Total deployments: [N]
- Rollbacks: [N]
- Failed deployments: [N]

## Capacity & Cost
[Placeholder — requires manual input or dashboard links]

## Action Item Review
[Auto-generated from: knowledge base + prior month's actions]

## Discussion & Decisions Needed
[Placeholder for human-added items]
```

### Quarterly Planning Agenda
```
# [Team] Quarterly Planning — [Quarter Year]

## OKR Progress Review
[Auto-generated from: twg goals get]
| Objective | Key Result | Target | Current | Status |

## Completed Initiatives
[Auto-generated from: twg work query --since 90d]

## Roadmap Review
[Auto-generated from: twg projects get + Jira epics]

## Big Rocks Next Quarter
[Placeholder — requires human input]

## Cross-Team Dependencies
[Auto-generated from: Jira linked issues + context queries]
| Dependency | Owner | What We Need | By When |

## Risks & Concerns
[Auto-generated from: knowledge base risk-patterns + recent retros]

## Team Health & Capacity
[Placeholder — requires human input]
```

---

## 6. Async-First Principles

When designing cadences, apply these async-first principles:

1. **"Write it down or it didn't happen"**: Decisions live in Confluence/Jira, not ephemeral Slack
2. **Async standups**: Use Slack threads or Confluence for status; sync only for blockers
3. **Pre-work for sync meetings**: Distribute agenda + data 24h before; sync time for discussion only
4. **Mandatory notes**: Every sync meeting produces a Confluence summary with decisions and action items
5. **Loom for demos**: Record demos async; sync time for Q&A only
6. **Retro pre-work**: Sticky notes / comments collected async; sync time for clustering and voting
