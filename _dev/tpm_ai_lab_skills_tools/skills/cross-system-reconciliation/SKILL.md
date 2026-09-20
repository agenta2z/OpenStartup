---
name: cross-system-reconciliation
description: >
  Guides the AI TPM in detecting and reporting data inconsistencies across Jira, Atlas Goals,
  Atlas Projects, and Confluence. Covers weekly data hygiene audits, cross-system field comparison,
  discrepancy classification, and correction proposal workflows with human-in-the-loop approval.
labels:
  - tpm
  - data-quality
  - reconciliation
  - cross-system
metadata:
  tools: [twg, mcp__atlassian__invoke_tool, mcp__atlassian_goal__invoke_tool, mcp__atlassian_project__invoke_tool]
---

# Cross-System Reconciliation

## 1. Skill Overview

- **Name**: `cross-system-reconciliation`
- **Description**: Domain guidance for detecting, classifying, and reporting data inconsistencies across Jira, Atlas Goals, Atlas Projects, and Confluence. This skill orchestrates multi-system data collection, field-level comparison, discrepancy severity classification, and correction proposal generation — always routing proposed fixes to human owners for approval.

### Leveraged Tools

| Tool | Capability Summary |
|------|-------------------|
| `twg` | Batch query Jira work items, Atlas goals/projects, Confluence pages, and cross-product context via TWG CLI |
| `mcp__atlassian__invoke_tool` (Jira) | Get/search Jira issues via JQL, read issue fields (status, dates, assignees, links) |
| `mcp__atlassian__invoke_tool` (Confluence) | Get/search Confluence pages via CQL, read page content and metadata |
| `mcp__atlassian_goal__invoke_tool` | Search/get Atlas goals with status, phase, owners, target dates |
| `mcp__atlassian_project__invoke_tool` | Search/get Atlas projects with status, dates, risks, dependencies |
| `mcp__teamwork_graph__invoke_tool` | Cross-product context, entity relationships, linked artifacts |

---

## 2. Workflow Mappings

### 2.1 Workflow: Weekly Data Hygiene Audit

**Trigger**: Weekly cadence (e.g., Monday morning), or on-demand request from TPM.

**Step-by-step operational pattern:**

#### Step 1 — Define Audit Scope
Identify the program's entities across systems:

```bash
# Get program's Jira projects
twg jira workitem search --jql "project = <KEY> AND issuetype = Epic ORDER BY updated DESC"

# Get Atlas goals linked to program
twg goals --scope me --include-contributing-projects

# Get Atlas projects
twg projects --scope me --role contributor
```

#### Step 2 — Jira Hygiene Checks
Run targeted JQL queries for common data quality issues:

```bash
# Unmapped stories (stories without a parent epic)
twg jira workitem search --jql "project = <KEY> AND issuetype = Story AND 'Parent Link' is EMPTY"

# Stale epics (no updates in 30+ days, still open)
twg jira workitem search --jql "project = <KEY> AND issuetype = Epic AND statusCategory != Done AND updated < -30d"

# Missing assignees on in-progress work
twg jira workitem search --jql "project = <KEY> AND statusCategory = 'In Progress' AND assignee is EMPTY"

# Missing due dates on epics
twg jira workitem search --jql "project = <KEY> AND issuetype = Epic AND statusCategory != Done AND duedate is EMPTY"

# Overdue items not updated
twg jira workitem search --jql "project = <KEY> AND duedate < now() AND statusCategory != Done AND updated < -7d"
```

#### Step 3 — Atlas Hygiene Checks

```bash
# Stale goals (no update in 30+ days)
# Via MCP - search goals and check update timestamps
mcp__atlassian_goal__invoke_tool("atlassian_goal_search_goals", {search: "<program>"})
# Then for each goal, check last update date
mcp__atlassian_goal__invoke_tool("atlassian_goal_get_goal_updates", {goalId: "<ari>", first: 1})

# Goals without owners
# Check owner field in goal response - flag if null/empty

# Projects without team assignment
mcp__atlassian_project__invoke_tool("atlassian_project_get_project", {projectId: "<ari>"})
# Check team/owner fields
```

#### Step 4 — Confluence Hygiene Checks

```bash
# Orphaned program pages (pages not updated in 60+ days)
# Via CQL search
mcp__atlassian__invoke_tool("search_confluence_using_cql", {
  site_url: "https://hello.atlassian.net",
  cql: "space = <SPACE> AND ancestor = <PAGE_ID> AND lastModified < now('-60d')"
})
```

#### Step 5 — Classify and Report Findings

Classify each finding by severity:

| Severity | Criteria | Example |
|----------|----------|---------|
| **Critical** | Blocks reporting or decision-making | Epic has no due date but is in current PI |
| **High** | Data quality issue affecting accuracy | Stale goal with no update in 30+ days |
| **Medium** | Inconsistency that could cause confusion | Story without parent epic |
| **Low** | Minor hygiene issue | Missing description on a completed item |

Generate structured report:

```markdown
# Weekly Data Hygiene Report — <Program Name>
**Generated**: <timestamp>
**Period**: <date range>

## Summary
- Critical: <N> findings
- High: <N> findings
- Medium: <N> findings
- Low: <N> findings

## Critical Findings
| # | System | Issue | Details | Suggested Action | Owner |
|---|--------|-------|---------|-----------------|-------|
| 1 | Jira | PROJ-123 has no due date | Epic in current PI | Set due date to PI end | @assignee |

## High Findings
...

## Trend
- New findings this week: <N>
- Resolved since last week: <N>
- Carry-over: <N>
```

**Decision Point:** Present report to TPM. Corrections require human approval.

---

### 2.2 Workflow: Cross-System Consistency Check

**Trigger**: Weekly cadence (after hygiene audit), or on-demand when discrepancies are suspected.

**Step-by-step operational pattern:**

#### Step 1 — Collect Canonical Fields from Each System

For each program entity, fetch the overlapping fields from all systems where it exists.

**Date fields:**
```bash
# Jira: Epic due dates, Fix Version release dates
twg jira workitem get --id <EPIC-KEY>
# Extract: duedate, fixVersions[].releaseDate, startDate

# Atlas Project: target dates
mcp__atlassian_project__invoke_tool("atlassian_project_get_project", {projectId: "<ari>"})
# Extract: startDate, dueDate (targeted_at), dueDateConfidence

# Atlas Goal: target dates
mcp__atlassian_goal__invoke_tool("atlassian_goal_get_goal", {goalId: "<ari>"})
# Extract: targeted_at, phase
```

**Status fields:**
```bash
# Jira: statusCategory (To Do / In Progress / Done)
# Atlas Project: phase (Wonder / Explore / Make / Impact / Cleanup) + status (On Track / At Risk / Off Track)
# Atlas Goal: status phase + score
```

**Owner/assignee fields:**
```bash
# Jira: assignee on program epic
# Atlas Project: owner
# Atlas Goal: owner
```

#### Step 2 — Normalize and Compare

Apply field-level comparison rules:

**Date Reconciliation Rules:**
```
Rule 1: Atlas project.dueDate vs Jira epic.duedate
  - Match if: within 7 calendar days
  - Mismatch if: >7 days apart
  - Severity: HIGH if >14 days, MEDIUM if 7-14 days

Rule 2: Atlas project.dueDate vs Jira fixVersion.releaseDate
  - Match if: within 7 calendar days
  - Mismatch if: >7 days apart
  - Severity: HIGH (release dates drive external commitments)

Rule 3: Atlas goal.targeted_at vs Atlas project.dueDate
  - Goal target should be >= project target (goals are outcomes, projects are delivery)
  - Mismatch if: goal target < project target
  - Severity: HIGH (indicates misalignment)
```

**Status Reconciliation Rules:**
```
Rule 1: Jira epic statusCategory vs Atlas project status
  - Jira "Done" + Atlas "On Track/At Risk" → MEDIUM (project may need closing)
  - Jira "To Do" + Atlas "On Track" with passed start date → HIGH (work hasn't started)
  - Jira "In Progress" + Atlas "Off Track" → LOW (expected alignment)

Rule 2: Atlas goal status vs Atlas project status
  - Goal "On Track" but all contributing projects "Off Track" → CRITICAL
  - Goal "Off Track" but all projects "On Track" → HIGH (goal may need update)

Rule 3: Jira completion % vs Atlas goal score
  - If Jira epic is 80%+ done but goal score is < 0.4 → MEDIUM (possible stale goal)
  - If Jira epic is < 20% done but goal score is > 0.7 → MEDIUM (overly optimistic)
```

**Owner Reconciliation Rules:**
```
Rule 1: Jira epic assignee vs Atlas project owner
  - Mismatch → LOW (different people may legitimately own different views)
  - Both empty → HIGH (no clear ownership)

Rule 2: Atlas goal owner vs Atlas project owner
  - Mismatch → LOW (goals and projects can have different owners)
  - Goal owner empty → HIGH
```

#### Step 3 — Generate Discrepancy Report

```markdown
# Cross-System Consistency Report — <Program Name>
**Generated**: <timestamp>

## Discrepancy Summary
| Severity | Count | Systems Involved |
|----------|-------|-----------------|
| Critical | <N> | <systems> |
| High | <N> | <systems> |
| Medium | <N> | <systems> |
| Low | <N> | <systems> |

## Discrepancies

### Critical
| # | Field | Jira Value | Atlas Value | Confluence Value | Rule Violated | Proposed Fix |
|---|-------|-----------|-------------|-----------------|---------------|-------------|
| 1 | Status | Epic: Done | Goal: On Track | — | Goal status stale | Update Atlas goal status to reflect completion |

### High
...

## Proposed Corrections
Each correction requires human approval before execution.

| # | System | Entity | Field | Current | Proposed | Approver |
|---|--------|--------|-------|---------|----------|---------|
| 1 | Atlas | Goal X | status | On Track | Done | @owner |
```

**Decision Point:** All proposed corrections must be approved by human owner before execution.

#### Step 4 — Execute Approved Corrections

After human approval, apply corrections:

```bash
# Update Atlas goal status (requires human confirmation per guardrails)
# This is a WRITE operation — always confirm before executing

# Update Jira issue fields
twg jira workitem update --id <KEY> --field duedate=<date>

# Update Atlas project
# Via MCP or TWG as appropriate
```

---

### 2.3 Workflow: Unlinked Entity Detection

**Trigger**: Part of weekly audit, or when new epics/goals are created.

#### Step 1 — Find Jira Epics Without Atlas Links

```bash
# Epics without linked Atlas goals
twg jira workitem search --jql "project = <KEY> AND issuetype = Epic AND 'Linked Goals' is EMPTY AND statusCategory != Done"

# Epics without linked Atlas projects
twg jira workitem search --jql "project = <KEY> AND issuetype = Epic AND 'Project overview key' is EMPTY AND statusCategory != Done"
```

#### Step 2 — Find Atlas Goals Without Jira Links

```bash
# Get all goals, check for linked work items
mcp__atlassian_goal__invoke_tool("atlassian_goal_search_goals", {search: "<program>"})
# For each goal, use TWG context to check linked Jira items
twg context jira workitem <LINKED-KEY> --depth 1
```

#### Step 3 — Suggest Linkages

For each unlinked entity, suggest the most likely link:
- Match by name/title similarity
- Match by owner/assignee overlap
- Match by date range overlap

Present suggestions for human approval.

---

### 2.4 Workflow: Anomaly-Triggered Reconciliation

**Trigger**: When program-health-scoring skill detects score anomalies or unexpected changes.

#### Step 1 — Identify Anomaly Source
When a health score drops unexpectedly:
- Check if the drop correlates with a data inconsistency (e.g., dates changed in one system but not another)
- Check if new risks appeared in one system but aren't reflected in others

#### Step 2 — Run Targeted Reconciliation
Focus only on the fields related to the anomaly (don't run full audit).

#### Step 3 — Report Findings
Include anomaly context in the reconciliation report, linking back to the health score change.

---

## 3. Domain Guidance

### 3.1 Templates and Checklists

#### Weekly Reconciliation Checklist
- [ ] Run Jira hygiene queries (unmapped stories, stale epics, missing owners/dates)
- [ ] Run Atlas hygiene checks (stale goals, missing owners)
- [ ] Run Confluence hygiene checks (orphaned pages)
- [ ] Collect canonical fields from all systems for cross-comparison
- [ ] Apply date reconciliation rules
- [ ] Apply status reconciliation rules
- [ ] Apply owner reconciliation rules
- [ ] Detect unlinked entities
- [ ] Classify all findings by severity
- [ ] Generate discrepancy report
- [ ] Present to TPM for review and approval
- [ ] Execute approved corrections
- [ ] Log corrections for audit trail

#### Reconciliation Configuration Template
```yaml
program:
  name: "<Program Name>"
  jira_projects: ["PROJ1", "PROJ2"]
  atlas_project_ids: ["<ari-1>"]
  atlas_goal_ids: ["<goal-ari-1>"]
  confluence_spaces: ["SPACE1"]

reconciliation:
  date_tolerance_days: 7
  stale_threshold_days: 30
  orphan_threshold_days: 60

  severity_rules:
    date_mismatch_gt_14d: HIGH
    date_mismatch_7_14d: MEDIUM
    status_contradiction: CRITICAL
    missing_owner: HIGH
    unlinked_entity: MEDIUM
    stale_update: HIGH
```

### 3.2 Decision Criteria

| Decision | Criteria | Action |
|----------|----------|--------|
| Flag date mismatch | >7 calendar days between systems | Report with severity based on gap size |
| Flag status contradiction | Logically incompatible statuses | Report as CRITICAL if goal says On Track but all projects Off Track |
| Flag stale entity | No update in >30 days | Report as HIGH |
| Propose date correction | Clear source of truth identifiable | Propose updating the stale system to match the recently updated one |
| Propose status correction | One system clearly outdated | Propose updating to match reality, with evidence |
| Skip comparison | Entity exists in only one system | Not a discrepancy — may flag as "unlinked" if expected to exist elsewhere |

### 3.3 Terminology

| Term | Definition |
|------|-----------|
| **Discrepancy** | A mismatch between the same conceptual field across two or more systems |
| **Hygiene Issue** | A data quality problem within a single system (missing field, stale record) |
| **Canonical Field** | A field that represents the same concept across systems (e.g., target date, status, owner) |
| **Source of Truth** | The system designated as authoritative for a given field. Atlas for goal status, Jira for delivery status |
| **Reconciliation** | The process of identifying and resolving discrepancies across systems |
| **Correction Proposal** | A suggested fix for a discrepancy, requiring human approval |
| **Tolerance Window** | Acceptable variance between systems (e.g., 7 days for dates) |

### 3.4 Cadence Patterns

| Activity | Frequency | Description |
|----------|-----------|-------------|
| Data hygiene audit | Weekly | Check each system for internal quality issues |
| Cross-system consistency check | Weekly | Compare canonical fields across Jira, Atlas, Confluence |
| Unlinked entity detection | Weekly | Find entities missing expected cross-system links |
| Anomaly-triggered reconciliation | On-demand | Deep-dive when health scores show unexpected changes |
| Full program reconciliation | Monthly | Comprehensive audit across all program entities |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
| `twg` | `jira workitem search`, `jira workitem get`, `jira workitem update`, `goals --scope me/org`, `projects --scope me`, `context jira workitem`, `confluence search query` |
| `mcp__atlassian__invoke_tool` | `search_jira_using_jql`, `get_jira_issue`, `search_confluence_using_cql`, `get_confluence_page` |
| `mcp__atlassian_goal__invoke_tool` | `atlassian_goal_get_goal`, `atlassian_goal_search_goals`, `atlassian_goal_get_goal_updates` |
| `mcp__atlassian_project__invoke_tool` | `atlassian_project_get_project`, `atlassian_project_search_projects`, `atlassian_project_get_project_updates`, `atlassian_project_get_project_risks` |
| `mcp__teamwork_graph__invoke_tool` | `twg_twg_atlassian_graph_get_context_for_work_item`, `twg_twg_atlassian_graph_get_project_context` |

### 4.2 Cross-Tool Patterns

**Pattern 1: Multi-System Field Collection**
1. Query Jira via TWG for batch efficiency (epic details, dates, statuses)
2. Query Atlas Goals via MCP for goal status, scores, target dates
3. Query Atlas Projects via MCP for project status, dates, risks
4. Query Confluence via MCP for page metadata and update timestamps
5. Normalize all fields into a common comparison structure

**Pattern 2: Discrepancy Detection Pipeline**
1. Collect canonical fields (Pattern 1)
2. Apply comparison rules (date tolerance, status compatibility, owner matching)
3. Classify discrepancies by severity
4. Generate structured report with proposed corrections
5. Present to human for approval

**Pattern 3: Correction Execution Pipeline**
1. Receive approved corrections from human
2. For Jira updates: use `twg jira workitem update`
3. For Atlas updates: route through appropriate MCP tool
4. For Confluence updates: use `mcp__atlassian__invoke_tool` with `update_confluence_page`
5. Log all corrections with before/after values

**Pattern 4: TWG-First with MCP Fallback**
1. Attempt data collection via TWG (more efficient for batch queries)
2. If TWG fails (timeout, error), fall back to individual MCP tool calls
3. If MCP also fails, report partial results with clear labels for missing data

### 4.3 Autonomy Levels

| Operation | Autonomy | Rationale |
|-----------|----------|-----------|
| Query all systems for data | 🟢 Fully Autonomous | Read-only operations |
| Run hygiene checks | 🟢 Fully Autonomous | Detection only |
| Compare fields across systems | 🟢 Fully Autonomous | Computation only |
| Classify discrepancies | 🟢 Fully Autonomous | Rule-based classification |
| Generate discrepancy reports | 🟢 Fully Autonomous | Report generation |
| Propose corrections | 🟡 AI Proposes | Suggestions only |
| Execute corrections in any system | 🔴 Human Required | All writes need approval |
| Change reconciliation rules/thresholds | 🔴 Human Required | Policy change |
| Override human-set statuses | 🔴 Never | Explicit prohibition |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

**The AI MUST NOT:**
- Execute any correction without explicit human approval
- Override human-set statuses or scores in any system
- Assume one system is "wrong" — discrepancies are findings, not errors
- Auto-resolve conflicts by picking a "winner" system
- Delete or archive entities in any system
- Change reconciliation rules or thresholds without approval
- Suppress or downgrade discrepancy severity to reduce noise
- Access or modify entities outside the defined program scope

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| CRITICAL discrepancy found (e.g., goal On Track but all projects Off Track) | Immediately flag to TPM |
| >10 new discrepancies in a single week | Flag potential systemic issue to TPM |
| Same discrepancy persists for >3 consecutive weeks | Escalate — correction may be blocked or ignored |
| System unavailable during audit | Complete audit with available systems, clearly label gaps |
| Proposed correction rejected by human >2 times | Stop proposing that correction, ask for guidance |
| Cross-system links broken (entity deleted in one system) | Flag as CRITICAL, do not attempt to recreate |

### 5.3 Error Handling

| Error | Response |
|-------|----------|
| Jira query timeout | Retry once with TWG. If still failing, try MCP `search_jira_using_jql`. Report partial results |
| Atlas API returns 404 for a goal | Entity may have been deleted or archived. Flag as finding, do not fabricate |
| Confluence page not found | Page may have moved or been deleted. Check via CQL search. Flag if missing |
| Rate limiting (429) on any system | Wait and retry with exponential backoff. Continue with other systems in the meantime |
| TWG binary not available | Fall back entirely to MCP tools for all queries |
| Ambiguous field mapping | Flag as "Unable to compare" rather than guessing. Include raw values for human review |
| Partial data from one system | Complete comparisons where possible, mark affected comparisons as "Incomplete" |
