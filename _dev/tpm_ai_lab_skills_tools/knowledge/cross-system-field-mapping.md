# Cross-System Field Mapping Reference

A comprehensive reference mapping canonical program management fields across Jira, Atlas Goals, Atlas Projects, and Confluence. Use this when building cross-system queries, reconciliation rules, or data normalization logic.

## 1. Date Fields

### Target / Due Date

| System | Field Name | Field ID / Path | Type | Semantics |
|--------|-----------|-----------------|------|-----------|
| Jira (Issue) | Due Date | `duedate` | date | When a work item is expected to be done. Should be kept current — overdue is an alert, not permanent |
| Jira (Issue) | Start Date | `startDate` | date | When work is expected to begin |
| Jira (Issue) | Target Start | `targetStart` | date | Plans/roadmap target start date |
| Jira (Issue) | Target End | `targetEnd` | date | Plans/roadmap target end date |
| Jira (Fix Version) | Release Date | `releaseDate` | date | When a version/release is planned to ship |
| Jira (Fix Version) | Start Date | `startDate` | date | When version work begins |
| Atlas Project | Target Date | `dueDate` / `targeted_at` | date | Communicated outcome date for the project |
| Atlas Project | Start Date | `startDate` / `started_at` | date | When the project started |
| Atlas Project | Due Date Confidence | `dueDateConfidence` | enum | high / medium / low confidence in target date |
| Atlas Goal | Target Date | `targeted_at` | date | When the goal/OKR is targeted for completion |
| Confluence | Page Properties date | varies by template | date | Stored in Page Properties macro tables (e.g., "Target Date", "Due Date", "Go-live") |

### Canonical Mapping Rules

```
program_target_date ←
  PRIMARY: Atlas Project.dueDate (strategic/communicated date)
  SECONDARY: Jira Epic.duedate (delivery date)
  TERTIARY: Jira Fix Version.releaseDate (release date)

program_start_date ←
  PRIMARY: Atlas Project.startDate
  SECONDARY: Jira Epic.startDate

milestone_dates[] ←
  Jira Fix Version.releaseDate (per version)
  Confluence Page Properties "Target Date" / "Due Date" rows
  Jira Milestone issue type duedate (if using MILE project pattern)

goal_target_date ←
  Atlas Goal.targeted_at
```

### Date Reconciliation Tolerance
- **Within 7 calendar days**: Considered aligned (acceptable drift)
- **8–14 days apart**: MEDIUM discrepancy — flag for review
- **>14 days apart**: HIGH discrepancy — likely stale data in one system

---

## 2. Status Fields

### Status / Health / Phase

| System | Field Name | Field ID / Path | Values | Semantics |
|--------|-----------|-----------------|--------|-----------|
| Jira (Issue) | Status | `status` | Workflow-specific (e.g., To Do, In Progress, Done) | Current workflow state |
| Jira (Issue) | Status Category | `statusCategory` | `To Do`, `In Progress`, `Done` | Normalized category across workflows |
| Jira (Fix Version) | Status | `released` / `archived` | boolean flags | Whether version is released |
| Atlas Project | Phase | `phase` | Wonder, Explore, Make, Impact, Cleanup | Project lifecycle phase |
| Atlas Project | Status | `status` | On Track, At Risk, Off Track, Paused, Done | Health status |
| Atlas Goal | Status Phase | `status.phase` | On Track, At Risk, Off Track | Goal health status |
| Atlas Goal | Score | `score` | 0.0 – 1.0 | Quantitative goal progress score |
| Confluence | Page status | `content-state` | Draft, Current, Archived (if enabled) | Page lifecycle state |

### Status Compatibility Matrix

| Jira StatusCategory | Atlas Project Status | Compatibility | Notes |
|--------------------|---------------------|---------------|-------|
| To Do | On Track | ✅ Compatible | Work not yet started, still on schedule |
| To Do | At Risk | ⚠️ Check | May indicate delayed start |
| To Do | Off Track | ⚠️ Check | Work should have started but hasn't |
| In Progress | On Track | ✅ Compatible | Normal state |
| In Progress | At Risk | ✅ Compatible | Work ongoing but has risks |
| In Progress | Off Track | ✅ Compatible | Work ongoing but significantly behind |
| Done | On Track | ⚠️ Flag | Project may need status update to Done |
| Done | Off Track | ❌ Mismatch | Jira says done but Atlas says off track |
| Done | Done | ✅ Compatible | Aligned completion |

### Goal Score to Status Mapping

```
Score 0.7 – 1.0  → On Track
Score 0.4 – 0.69 → At Risk
Score 0.0 – 0.39 → Off Track
```

---

## 3. Owner / Assignee Fields

| System | Field Name | Field ID / Path | Type | Semantics |
|--------|-----------|-----------------|------|-----------|
| Jira (Issue) | Assignee | `assignee` / `assigneeAri` | user | Person responsible for the work item |
| Jira (Issue) | Reporter | `reporter` / `reporterAri` | user | Person who created/reported the issue |
| Atlas Project | Owner | `owner` | user | Person accountable for the project outcome |
| Atlas Project | Contributors | `contributors` | user[] | People contributing to the project |
| Atlas Goal | Owner | `owner` | user | Person accountable for achieving the goal |
| Atlas Goal | Contributors | `contributors` | user[] | People contributing to the goal |
| Confluence | Creator | `creator` | user | Page author |
| Confluence | Last Modifier | `lastModifier` | user | Last person to edit the page |

### Owner Mapping Notes
- Jira assignee and Atlas owner are **not necessarily the same person** — Jira tracks execution, Atlas tracks accountability
- Both being empty is a HIGH severity finding (no clear ownership)
- Mismatch alone is LOW severity (different roles are legitimate)

---

## 4. Linking Fields (Cross-System References)

| System | Field Name | Links To | How It Works |
|--------|-----------|----------|-------------|
| Jira Epic | Linked Goals | Atlas Goal | `Goal key` and `Goal status` custom fields added when linked |
| Jira Epic | Project overview | Atlas Project | `Project overview key` and `Project overview status` custom fields |
| Jira Epic | Parent Link | Jira Issue | Hierarchy parent (epic → initiative) |
| Atlas Project | Where is work tracked? | Jira Epic | Links Atlas project to Jira epics; syncs name, dates, tags |
| Atlas Goal | Contributing Projects | Atlas Project | Links goals to projects that contribute to achieving them |
| Atlas Goal | Parent Goal | Atlas Goal | Goal hierarchy (KR → Objective → Strategic Goal) |
| Confluence Page | Jira Issue Macro | Jira Issue | Embedded Jira issue references in page content |

### JQL for Finding Linked/Unlinked Entities

```sql
-- Epics linked to Atlas goals
project = <KEY> AND issuetype = Epic AND "Goal key" is not EMPTY

-- Epics NOT linked to any Atlas goal
project = <KEY> AND issuetype = Epic AND "Goal key" is EMPTY AND statusCategory != Done

-- Epics linked to Atlas projects
project = <KEY> AND issuetype = Epic AND "Project overview key" is not EMPTY

-- Issues linked to a specific goal
"Goal key" = <GOAL-KEY>
```

---

## 5. Metric / Progress Fields

| System | Field Name | Type | Semantics |
|--------|-----------|------|-----------|
| Jira (Issue) | Story Points | number | Effort estimate for a work item |
| Jira (Issue) | Time Estimate | seconds | Original time estimate |
| Jira (Issue) | Time Spent | seconds | Logged work time |
| Jira (Sprint) | Velocity | derived | Story points completed per sprint (from velocity chart) |
| Atlas Goal | Score | 0.0–1.0 | Overall goal progress score |
| Atlas Goal | KR/Success Measure Score | 0.0–1.0 | Individual key result score |
| Atlas Project | Completion % | derived | Not auto-computed — set via updates |

### Derived Metrics for TPM Use

```
Milestone Completion % (by count) = Done issues / Total issues under milestone
Milestone Completion % (by points) = Done story points / Total story points under milestone
Sprint Velocity = Average(story points completed) over last N sprints
Bug Density = Open bugs / Total issues in project
Risk Count = Open risks (unresolved, High/Critical priority)
```

---

## 6. Source of Truth Rules

When the same conceptual field exists in multiple systems, use these precedence rules:

| Field Category | Source of Truth | Rationale |
|---------------|----------------|-----------|
| Delivery status (is work done?) | **Jira** | Jira tracks actual execution |
| Goal/outcome health | **Atlas Goals** | Goals are human-curated, outcome-focused |
| Project strategic status | **Atlas Projects** | Projects represent strategic communication |
| Target dates (strategic) | **Atlas Projects** | Communicated outcome dates |
| Target dates (delivery) | **Jira Fix Versions** | Release-level commitments |
| Technical documentation | **Confluence** | Long-form documentation home |
| Risk register | **Jira** (Risk issue type) or **Atlas Projects** (risks) | Depends on team convention |

### Important Design Principle
Atlas deliberately avoids auto-setting goal health from Jira % complete. Goals are updated via narrative + explicit metrics. Jira is one of several execution signals (others: hiring, contracts, compliance, user metrics). The AI TPM should treat Jira metrics as **inputs for recommendations**, while leaving final Atlas health and score to human confirmation.

---

## 7. Related Skills and Tools

- **Skill: `program-health-scoring`** — Uses these field mappings to compute health scorecards and OKR roll-ups
- **Skill: `cross-system-reconciliation`** — Uses these field mappings to detect and report discrepancies
- **Tool: `twg`** — Primary tool for querying Jira, Atlas, and Confluence data
- **Tool: MCP Atlassian tools** — Alternative/complementary tools for individual entity lookups
