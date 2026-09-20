# JQL Patterns Reference

Jira Query Language patterns for the AI TPM's data collection workflows. All queries use TWG CLI or Jira MCP tools.

## Usage

Replace `<projects>` with comma-separated project keys from program configuration (e.g., `MLPLAT, MLOPS, AIENG`).

## 1. Milestone & Epic Tracking

```sql
-- Slipping milestones (due within 7 days, not complete)
project in (<projects>) AND type = Epic AND duedate <= 7d AND status != Done

-- Overdue milestones (past due date)
project in (<projects>) AND type = Epic AND duedate < now() AND status != Done

-- Upcoming milestones (next 14 days)
project in (<projects>) AND type = Epic AND duedate >= now() AND duedate <= 14d ORDER BY duedate ASC

-- Milestones completed this week
project in (<projects>) AND type = Epic AND resolved >= -7d ORDER BY resolved DESC
```

## 2. Blocker Detection

```sql
-- Currently blocked items
project in (<projects>) AND status = Blocked

-- Newly blocked (last 24h)
project in (<projects>) AND status changed TO Blocked AFTER -1d

-- Long-standing blockers (>48h)
project in (<projects>) AND status = Blocked AND status changed TO Blocked BEFORE -2d

-- Long-standing blockers (>5 days) — escalation trigger
project in (<projects>) AND status = Blocked AND status changed TO Blocked BEFORE -5d

-- Items with blocking links
project in (<projects>) AND issueFunction in linkedIssuesOf("status = Blocked", "is blocked by")
```

## 3. Sprint Health

```sql
-- Unestimated work in active sprint
project in (<projects>) AND sprint in openSprints() AND originalEstimate is EMPTY

-- Scope additions (items added after sprint start)
project in (<projects>) AND sprint in openSprints() AND created >= "<sprint_start_date>"

-- Sprint carry-over (incomplete from closed sprints)
project in (<projects>) AND sprint in closedSprints() AND status != Done AND resolution = Unresolved

-- Current sprint items by status
project in (<projects>) AND sprint in openSprints() ORDER BY status ASC
```

## 4. WIP & Flow Analysis

```sql
-- Current work in progress
project in (<projects>) AND status = "In Progress"

-- WIP per assignee (for overload detection)
project in (<projects>) AND status = "In Progress" AND assignee is not EMPTY

-- Stale in-progress items (no update in 3+ days)
project in (<projects>) AND status = "In Progress" AND updated <= -3d

-- High-priority items not progressing
project in (<projects>) AND priority in (Highest, High) AND status = "In Progress" AND updated <= -3d
```

## 5. Accomplishments & Velocity

```sql
-- Resolved items (last 7 days)
project in (<projects>) AND resolved >= -7d ORDER BY resolved DESC

-- Resolved items (last 24h) — for daily digest
project in (<projects>) AND resolved >= -1d ORDER BY resolved DESC

-- Resolved items by type (for velocity breakdown)
project in (<projects>) AND resolved >= -7d AND type in (Story, Bug, Task) ORDER BY type ASC
```

## 6. Risk & Quality Signals

```sql
-- Open bugs by priority
project in (<projects>) AND type = Bug AND status != Done ORDER BY priority ASC

-- Critical/blocker bugs
project in (<projects>) AND type = Bug AND priority in (Highest, High) AND status != Done

-- Bug escape rate proxy (bugs created in last 7d marked as production)
project in (<projects>) AND type = Bug AND created >= -7d AND labels in (production, prod-bug, escape)

-- Security vulnerabilities
project in (<projects>) AND type in (Bug, "Security Vulnerability") AND labels in (security, vulnerability) AND status != Done
```

## 7. Dependency Analysis

```sql
-- Cross-project dependencies (items linked to other projects)
issue in linkedIssues(<key>) AND project != <source_project>

-- Items depending on external teams
project in (<projects>) AND status = "Waiting for External" OR labels in (external-dependency, cross-team)
```

## 8. TWG-Specific Commands

For queries that go beyond JQL, use TWG's native and projection surfaces:

```bash
# Cross-product activity scan
twg work query --scope me --since 7d

# Dependency context for a specific item
twg context jira workitem <KEY> --depth 2

# Atlas goal health
twg goals --scope me --include-contributing-projects

# Atlas project status
twg projects --scope me --role contributor

# Team member activity
twg work query --scope user --account-id <id> --since 7d
```

## Notes

- JQL queries via TWG CLI: `twg jira workitem get --jql "<query>"`
- JQL queries via Jira MCP: `search_jira_using_jql` with `jql` parameter
- For large result sets, use TWG pagination: `--first 50 --after <cursor>`
- Always handle empty results gracefully — distinguish "no matches" from "query error"
