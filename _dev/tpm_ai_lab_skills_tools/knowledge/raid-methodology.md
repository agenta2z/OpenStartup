# RAID Methodology for AI TPM

Reference material for managing Risks, Assumptions, Issues, and Dependencies (RAID) within AI TPM workflows. This knowledge block covers severity schemas, likelihood-impact matrices, register structure, and lifecycle management patterns.

## 1. RAID Register Structure

### 1.1 Entry Types

| Type | Definition | Example |
|------|-----------|---------|
| **Risk** | Uncertain event that, if it occurs, has a negative effect on objectives | "Key engineer may leave during critical phase" |
| **Assumption** | Factor considered true for planning purposes, not yet validated | "Partner API will support batch operations" |
| **Issue** | Current problem actively impacting the program | "Build pipeline failing intermittently since Monday" |
| **Dependency** | External deliverable or condition needed for program progress | "Auth service v2 from Platform team needed by Sprint 14" |

### 1.2 Register Fields

Each RAID entry should capture:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ID | String | Yes | Auto-generated: R-001, A-001, I-001, D-001 |
| Type | Enum | Yes | Risk, Assumption, Issue, Dependency |
| Title | String | Yes | Short descriptive title |
| Description | Text | Yes | Detailed description of the item |
| Category | Enum | No | Technical, Resource, Schedule, Scope, External, Compliance |
| Severity | Enum | Yes | Critical, High, Medium, Low |
| Likelihood | Enum | For Risks | Almost Certain, Likely, Possible, Unlikely, Rare |
| Impact Areas | Multi-select | Yes | Schedule, Scope, Quality, Cost, Reputation |
| Owner | Person | Yes | Individual accountable for managing this item |
| Status | Enum | Yes | Open, Mitigating, Monitoring, Closed, Accepted |
| Raised Date | Date | Yes | When the item was first identified |
| Due Date | Date | No | Target date for resolution or next review |
| Mitigation | Text | For Risks | Planned response actions |
| Resolution | Text | No | How the item was resolved (when closed) |
| Linked Jira | String | No | Associated Jira issue key(s) |
| Last Reviewed | Date | Yes | Date of most recent review |

## 2. Severity and Likelihood Matrices

### 2.1 Severity Classification

| Severity | Schedule | Scope | Quality | Cost | Reputation |
|----------|----------|-------|---------|------|------------|
| **Critical** | >4 weeks slip | Major feature/workstream dropped | Production outage or data loss | >20% budget overrun | Executive/customer visibility |
| **High** | 2-4 weeks slip | Feature significantly degraded | Significant defects in core flows | 10-20% budget overrun | Cross-team visibility |
| **Medium** | 1-2 weeks slip | Minor scope adjustment | Moderate defects, workarounds exist | 5-10% budget overrun | Team-level visibility |
| **Low** | <1 week slip | Cosmetic or nice-to-have change | Minor defects, low user impact | <5% budget overrun | Internal only |

### 2.2 Likelihood Scale

| Level | Probability | Indicators |
|-------|-------------|-----------|
| **Almost Certain** | >80% | Has happened before in similar context; preconditions already met |
| **Likely** | 60-80% | Strong signals present; more likely than not |
| **Possible** | 30-60% | Could go either way; some early signals |
| **Unlikely** | 10-30% | Not expected but plausible; weak signals |
| **Rare** | <10% | Exceptional circumstances only; no current signals |

### 2.3 Risk Score Matrix (Severity x Likelihood)

|  | Almost Certain | Likely | Possible | Unlikely | Rare |
|--|----------------|--------|----------|----------|------|
| **Critical** | 25 (Extreme) | 20 (Extreme) | 15 (High) | 10 (High) | 5 (Medium) |
| **High** | 20 (Extreme) | 16 (High) | 12 (High) | 8 (Medium) | 4 (Medium) |
| **Medium** | 15 (High) | 12 (High) | 9 (Medium) | 6 (Medium) | 3 (Low) |
| **Low** | 10 (High) | 8 (Medium) | 6 (Medium) | 4 (Low) | 2 (Low) |

**Response thresholds**:
- **Extreme (20-25)**: Immediate escalation (Tier 2 minimum), SteerCo notification required
- **High (12-16)**: Active mitigation required, weekly monitoring, TPM attention
- **Medium (4-9)**: Monitor and review at regular cadence, mitigation plan recommended
- **Low (2-3)**: Accept or monitor, review monthly

## 3. RAID Lifecycle Management

### 3.1 Risk Lifecycle

```
Identified -> Assessed -> [Mitigating | Accepted | Monitoring] -> [Closed | Realized -> Issue]
```

1. **Identified**: New risk detected (from signal scanning, stakeholder input, or dependency analysis)
2. **Assessed**: Severity and likelihood assigned, owner designated, mitigation planned
3. **Mitigating**: Active response underway (mitigation actions in progress)
4. **Accepted**: Risk acknowledged, no active mitigation (low severity or unavoidable)
5. **Monitoring**: Watching for trigger conditions, periodic review
6. **Closed**: Risk no longer relevant (avoided, expired, or mitigated)
7. **Realized**: Risk has occurred — convert to Issue

### 3.2 Dependency Lifecycle

```
Identified -> Tracked -> [On Track | At Risk | Blocked] -> [Delivered | Descoped]
```

- **Lead time tracking**: Calculate days between current date and needed-by date
- **Status signals**: Check linked Jira issue status, owner activity, blocker presence
- **Escalation trigger**: Lead time <= 14 days AND status not Done/Committed

### 3.3 Review Cadence

| Risk Level | Review Frequency | Review Actions |
|-----------|-----------------|----------------|
| Extreme | Daily | Update status, check mitigation progress, escalate if worsening |
| High | Every 2-3 days | Review mitigation, update likelihood based on new data |
| Medium | Weekly | Confirm status, update if conditions changed |
| Low | Bi-weekly or monthly | Quick scan, close if no longer relevant |

## 4. RAID in Jira — Convention Patterns

Since Jira lacks native RAID fields, use these conventions:

### 4.1 Naming Convention
- Issue summary prefix: `RISK:`, `ISSUE:`, `ASSUMPTION:`, `DEP:`
- Example: `RISK: [HIGH] API rate limiting may block data migration`

### 4.2 Label Convention
- Labels: `raid-risk`, `raid-issue`, `raid-assumption`, `raid-dependency`
- Severity labels: `severity-critical`, `severity-high`, `severity-medium`, `severity-low`

### 4.3 JQL Queries for RAID Management
- All open risks: `project = PROJ AND labels = raid-risk AND status != Done`
- Critical/High risks: `project = PROJ AND labels = raid-risk AND labels in (severity-critical, severity-high) AND status != Done`
- Dependencies due soon: `project = PROJ AND labels = raid-dependency AND due <= 14d AND status != Done`
- Stale RAID items: `project = PROJ AND labels in (raid-risk, raid-issue) AND updated <= -14d AND status != Done`

## 5. Related Skills and Tools

- **ai-tpm skill**: Uses RAID methodology in SOP 1 (Step 4: Initialize RAID Log), SOP 2 (Steps 1-5: Risk Management), and SOP 3 (Step 4: Gate Evidence)
- **twg tool**: `twg jira workitem create/update` for RAID item management in Jira
- **knowledge tool**: `kn add/search` for local RAID context persistence
- **confirmation tool**: Required for severity upgrades and critical risk escalations
