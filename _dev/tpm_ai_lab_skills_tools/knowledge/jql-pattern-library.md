# JQL Pattern Library for TPM Operations

Reference library of JQL query patterns organized by TPM use case. These patterns are designed
for use with the `search_jira_using_jql` MCP tool or any JQL-capable interface. All patterns
target Jira Cloud and use standard JQL operators unless otherwise noted.

Related skills: `jira-program-ops`

---

## 1. Dependency Tracking Patterns

### 1.1 All Issues Linked to a Specific Issue (Any Link Type)

```jql
issue in linkedIssues("PROJ-123")
```

**Use case**: Quick discovery of all related work for a given issue.
**Notes**: Returns issues with any link type (blocks, is blocked by, relates to, etc.).

### 1.2 Downstream Blocking Dependencies

```jql
project in (PROJ1, PROJ2, PROJ3)
  AND issueLinkType = "Blocks"
  AND statusCategory != Done
  ORDER BY priority DESC
```

**Use case**: Find all active blocking relationships across program projects.
**Notes**: `issueLinkType` is a native JQL field — no plugins required.

### 1.3 Cross-Project Blockers (ScriptRunner Required)

```jql
issueFunction in linkedIssuesOf("project = PROJ1 AND statusCategory != Done", "is blocked by")
  AND project != PROJ1
  AND statusCategory != Done
```

**Use case**: Find issues in other projects that block PROJ1's active work.
**Notes**: `issueFunction` / `linkedIssuesOf()` requires ScriptRunner plugin. If unavailable, use pattern 1.2 instead.

### 1.4 Unlinked Epics (No Dependencies Declared)

```jql
project = PROJ
  AND issuetype = Epic
  AND statusCategory != Done
  AND issueFunction NOT IN hasLinks()
```

**Use case**: Find epics with no issue links — potential undeclared dependencies.
**Notes**: Requires ScriptRunner. Fallback: manually inspect epics.

### 1.5 Portfolio Hierarchy Descendants (Advanced Roadmaps)

```jql
issuekey in portfolioChildIssuesOf(PROGRAM-123)
  ORDER BY issuetype ASC, priority DESC
```

**Use case**: Expand an initiative/program issue to all descendant work items.
**Notes**:
- Requires Advanced Roadmaps (Jira Plans)
- **Truncation risk**: Results may silently truncate at 1,000 issues
- Issue keys are **case-sensitive** — use exact case
- For large programs, slice by project: `AND project = PROJ1`

### 1.6 RAID View from Portfolio Hierarchy

```jql
-- Risks under a program
issuekey in portfolioChildIssuesOf(PROGRAM-123) AND issuetype = Risk
  ORDER BY status DESC

-- Dependencies under a program
issuekey in portfolioChildIssuesOf(PROGRAM-123) AND issuetype = Dependency
  ORDER BY priority DESC
```

**Use case**: Generate RAID-style views from Advanced Roadmaps hierarchy.

---

## 2. Sprint Health Patterns

### 2.1 All Issues in Active Sprints

```jql
project = PROJ AND sprint in openSprints()
  ORDER BY status ASC
```

**Use case**: Get the full sprint backlog for health analysis.
**Performance note**: Always scope with `project = X` — unscoped `openSprints()` can be slow on large instances.

### 2.2 Sprint Issues by Status Category

```jql
-- To Do
project = PROJ AND sprint in openSprints() AND statusCategory = "To Do"

-- In Progress
project = PROJ AND sprint in openSprints() AND statusCategory = "In Progress"

-- Done
project = PROJ AND sprint in openSprints() AND statusCategory = "Done"
```

**Use case**: Bucket sprint issues for completion rate calculation.

### 2.3 Scope Change Detection (Mid-Sprint Additions)

```jql
project = PROJ
  AND sprint in openSprints()
  AND created >= -7d
  AND statusCategory = "To Do"
```

**Use case**: Detect issues added to the sprint after it started (scope creep).
**Notes**: Adjust the `-7d` window to match sprint length. For 2-week sprints, use `-14d` to catch all mid-sprint additions.

### 2.4 Stalled Work (In Progress but Not Updated)

```jql
project = PROJ
  AND sprint in openSprints()
  AND statusCategory = "In Progress"
  AND updated <= -3d
```

**Use case**: Find work items that are nominally "in progress" but have gone stale.
**Thresholds**: 3 days = warning, 5 days = concern, 7+ days = escalation.

### 2.5 Sprint Carryover (Unfinished from Closed Sprints)

```jql
project = PROJ
  AND sprint in closedSprints()
  AND statusCategory != Done
  AND resolution = Unresolved
```

**Use case**: Identify issues that were not completed when their sprint closed.
**Performance note**: Always scope `closedSprints()` by project. On instances with >65,000 closed sprints, unscoped queries can fail.

### 2.6 Bugs in Active Sprint

```jql
project = PROJ
  AND sprint in openSprints()
  AND issuetype = Bug
  AND statusCategory != Done
  ORDER BY priority DESC
```

**Use case**: Monitor bug count in active sprints — high bug count is a sprint health signal.

### 2.7 Future Sprint Planning

```jql
project = PROJ
  AND sprint in futureSprints()
  ORDER BY priority DESC, created ASC
```

**Use case**: Review what's planned for upcoming sprints.

---

## 3. Data Hygiene Patterns

### 3.1 Unmapped Stories (No Epic Link)

```jql
project = PROJ
  AND issuetype in (Story, Task)
  AND "Epic Link" is EMPTY
  AND statusCategory != Done
  AND sprint in openSprints()
```

**Use case**: Stories in active sprints without an epic — invisible in program rollups.
**Thresholds**: Warning ≥ 3, Violation ≥ 10.

### 3.2 Missing Assignee on In-Progress Work

```jql
project = PROJ
  AND assignee is EMPTY
  AND statusCategory = "In Progress"
```

**Use case**: Work actively in progress with no owner.
**Thresholds**: Warning ≥ 1, Violation ≥ 5.

### 3.3 Stale Epics (No Updates)

```jql
project = PROJ
  AND issuetype = Epic
  AND statusCategory != Done
  AND updated <= -30d
```

**Use case**: Epics that may be abandoned or forgotten.
**Thresholds**: Warning ≥ 2 (30d stale), Violation ≥ 5 or any 60d+ stale.

### 3.4 Stale Stories/Tasks

```jql
project = PROJ
  AND issuetype in (Story, Task)
  AND statusCategory != Done
  AND resolution = Unresolved
  AND updated <= -14d
```

**Use case**: Stories/tasks not updated in 14+ days.

### 3.5 Stale Bugs (Urgent)

```jql
project = PROJ
  AND issuetype = Bug
  AND statusCategory != Done
  AND updated <= -7d
```

**Use case**: Bugs should have shorter staleness thresholds.

### 3.6 Missing Priority

```jql
project = PROJ
  AND priority is EMPTY
  AND statusCategory != Done
```

**Use case**: Issues without priority cannot be properly triaged.
**Thresholds**: Warning ≥ 5, Violation ≥ 15.

### 3.7 Unestimated Stories in Sprint

```jql
project = PROJ
  AND issuetype = Story
  AND cf[10016] is EMPTY
  AND sprint in openSprints()
```

**Use case**: Stories in active sprints without story points — undermines velocity tracking.
**Notes**: `cf[10016]` is the common custom field ID for story points. Verify with your instance.
**Thresholds**: Warning ≥ 3, Violation ≥ 8.

### 3.8 Missing Fix Version

```jql
project = PROJ
  AND fixVersion is EMPTY
  AND statusCategory != Done
  AND issuetype in (Story, Bug, Task)
```

**Use case**: Issues not assigned to a release version.

### 3.9 Missing Component

```jql
project = PROJ
  AND component is EMPTY
  AND statusCategory != Done
```

**Use case**: Issues without component assignment — makes ownership unclear.

### 3.10 Resolved but Not Closed

```jql
project = PROJ
  AND resolution is not EMPTY
  AND statusCategory != Done
```

**Use case**: Issues that have been resolved but not moved to Done status.

---

## 4. Cross-Project Patterns

### 4.1 Multi-Project Overview

```jql
project in (PROJ1, PROJ2, PROJ3)
  AND statusCategory != Done
  ORDER BY project ASC, priority DESC
```

**Use case**: Overview of all active work across program projects.

### 4.2 Cross-Project Assigned to Specific User

```jql
project in (PROJ1, PROJ2, PROJ3)
  AND assignee = "<account_id>"
  AND statusCategory != Done
  ORDER BY priority DESC
```

**Use case**: Find all active work for a specific team member across projects.

### 4.3 Recently Resolved Across Projects

```jql
project in (PROJ1, PROJ2, PROJ3)
  AND resolved >= -7d
  ORDER BY resolved DESC
```

**Use case**: Weekly summary of completed work across the program.

### 4.4 High-Priority Unresolved Across Projects

```jql
project in (PROJ1, PROJ2, PROJ3)
  AND priority in (Highest, High)
  AND statusCategory != Done
  ORDER BY priority DESC, updated ASC
```

**Use case**: Focus attention on the most important unresolved issues.

---

## 5. Staleness Thresholds Reference

| Issue Type | Warning Threshold | Violation Threshold | JQL Operator |
|-----------|-------------------|---------------------|--------------|
| Story | 14 days | 30 days | `updated <= -14d` / `updated <= -30d` |
| Task | 14 days | 30 days | `updated <= -14d` / `updated <= -30d` |
| Bug | 7 days | 14 days | `updated <= -7d` / `updated <= -14d` |
| Epic | 30 days | 60 days | `updated <= -30d` / `updated <= -60d` |
| Initiative | 60 days | 90 days | `updated <= -60d` / `updated <= -90d` |
| Sub-task | 7 days | 14 days | `updated <= -7d` / `updated <= -14d` |

---

## 6. Performance and Safety Notes

1. **Always scope sprint functions by project**: `project = X AND sprint in openSprints()` — never use unscoped sprint functions on large instances.
2. **`closedSprints()` limit**: Instances with >65,536 closed sprints may fail. Always add project scope.
3. **`portfolioChildIssuesOf()` truncation**: Results silently truncate at ~1,000 issues. If you hit 1,000, slice by project or issue type.
4. **Case sensitivity**: Issue keys in `portfolioChildIssuesOf()` are case-sensitive. Use exact case (e.g., `WFM-123` not `wfm-123`).
5. **Custom field IDs**: Story points (`cf[10016]`), Epic Link, and other custom fields may have different IDs on different instances. Verify with your admin.
6. **JQL result limit**: The MCP `search_jira_using_jql` tool has a `limit` parameter. Default varies by implementation. Set explicitly for large result sets.
7. **Date operators**: `-Nd` format means "N days ago from now". Supports `-Nw` (weeks), `-Nm` (months) as well.
