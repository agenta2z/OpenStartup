---
name: jira-program-ops
description: >
  Provides domain-specific workflow guidance for Technical Program Managers (TPMs) to operate
  Jira at scale — cross-project dependency tracking, sprint health monitoring, data hygiene
  audits, and program board management. Composes TWG CLI commands with Atlassian MCP tools
  to execute JQL queries, traverse issue hierarchies, detect blockers, and generate nudges
  for responsible teams.
labels:
  - tpm
  - jira
  - program-management
  - data-hygiene
metadata:
  tools:
    - twg
    - slack_send_message
    - slack_find_channel
    - search_jira_using_jql
    - get_jira_issue
    - create_jira_issue
    - update_jira_issue
---

# Jira Program Ops

## 1. Skill Overview

- **Name**: jira-program-ops
- **Description**: Orchestrates TPM-specific Jira operations — dependency scanning, sprint health analysis, data hygiene audits, and cross-project program tracking. Guides the AI through JQL pattern selection, tool routing (TWG CLI vs MCP), result aggregation, and stakeholder notification.
- **Leveraged Tools**:

| Tool | Capability Summary |
|------|-------------------|
|  (TWG CLI) | Individual issue CRUD (), sprint management (), project status listing (), cross-product context () |
|  (MCP) | Bulk JQL query execution — the primary tool for dependency scans, hygiene audits, and sprint health queries. TWG does not natively support JQL search. |
|  (MCP) | Rich single-issue detail retrieval including transitions, links, comments, and custom fields |
|  /  (MCP) | Issue creation and field updates when TWG workitem commands are insufficient (e.g., custom fields) |
|  | Deliver nudge messages, status summaries, and escalation alerts to team channels |
|  | Resolve team channel names to IDs for targeted nudge delivery |

## 2. Workflow Mappings

### 2.1 Workflow: Cross-Project Dependency Scan

**Trigger**: Continuous / on-demand — when the TPM needs to identify blockers, cross-team dependencies, or at-risk delivery chains across multiple projects.

**Step-by-step operational pattern**:

1. **Identify target projects** — Determine the set of project keys to scan:
   
   Run for each project to confirm valid statuses for JQL construction.

2. **Query cross-project blocking links** via MCP:
   
   > **Note**:  requires ScriptRunner. If unavailable, use the simpler pattern:
   

3. **Enrich blocking issues** — For each blocker found, get full context:
   

4. **Traverse dependency depth** — Use TWG context for cross-product perimeter:
   {
  "apiVersion": "v2",
  "command": "context.jira.workitem",
  "request": {
    "issueKey": "PROJ-123",
    "depth": 2,
    "slices": [
      "comments",
      "code",
      "docs",
      "hierarchy",
      "dependencies"
    ],
    "verbose": false
  },
  "data": {
    "centralIssue": {
      "ari": "ari:cloud:jira:a436116f-02ce-4520-8fbb-7301462a1674:issue/5783455",
      "key": "PROP-123",
      "summary": "Test Project",
      "status": "To Do",
      "issueType": "Idea",
      "priority": "Minor",
      "assignee": null
    },
    "depth1": {
      "commentsCount": 0,
      "linkedIssues": {
        "blockedBy": [],
        "blocks": [],
        "related": []
      },
      "code": {
        "prs": [
          {
            "id": "ari:cloud:graph::commit/activation/a04080b6-0834-11eb-b374-0a77f3f45304/7db9690c-cf21-428e-b340-8bb4214ebf32",
            "title": null,
            "url": null,
            "status": null,
            "linkage": {
              "scope": "DIRECT_OUTBOUND",
              "edgeType": "issue_associated_pr"
            },
            "signals": {
              "confidence": 100
            }
          }
        ],
        "commits": [],
        "branches": []
      },
      "docs": [],
      "hierarchy": {
        "parents": [],
        "children": []
      },
      "signal": {
        "totalIssues": 0,
        "totalArtifacts": 1,
        "relevanceScore": 20,
        "relevanceLabel": "Low"
      }
    },
    "depth2": {
      "siblings": [],
      "parentLinked": [],
      "grandparents": [],
      "neighborCode": {},
      "signal": {
        "totalIssues": 0,
        "totalArtifacts": 0,
        "relevanceScore": 0,
        "relevanceLabel": "Low"
      }
    },
    "overallSignal": {
      "totalIssues": 0,
      "totalArtifacts": 1,
      "relevanceScore": 14,
      "relevanceLabel": "Low"
    }
  },
  "meta": {
    "resourceClass": "projection",
    "sourceMode": "mixed",
    "resourceType": "context.jira.workitem",
    "depth": 2,
    "sourceProducts": [
      "jira",
      "bitbucket"
    ],
    "backend": "cypher",
    "resultCount": 1
  },
  "hints": [
    "Use --depth 3 to include semantic neighbours (when available).",
    "Comment fetching via GraphStore is a placeholder. INNER_DATA comments planned for next iteration."
  ]
}
   This reveals connected Confluence pages, PRs, and related issues.

5. **Classify results**:
   - **Critical**: Blocker in "In Progress" status with no assignee or stale >7 days
   - **High**: Cross-project blocker with due date in next 2 weeks
   - **Medium**: Dependency exists but work is progressing
   - **Low**: Informational link, no blocking relationship

6. **Report/escalate** — Based on classification:
   - Critical/High → Send Slack nudge to owning team channel
   - Medium/Low → Include in weekly status report

**Example scenario**: TPM monitors projects ATLAS, FORGE, and CONNECT. A dependency scan reveals FORGE-456 blocks ATLAS-789 (critical path). FORGE-456 has been in "In Progress" for 12 days with no recent updates. The AI sends a nudge to #team-forge: "⚠️ FORGE-456 is blocking ATLAS-789 (critical path). No updates in 12 days. Assignee: @jane. Can you provide a status update?"

---

### 2.2 Workflow: Sprint Health Monitor

**Trigger**: Daily check or on-demand — monitors active sprint health metrics.

**Step-by-step operational pattern**:

1. **Query active sprint issues**:
   

2. **Bucket by status category** — Parse results into:
   - To Do count
   - In Progress count
   - Done count
   - Total story points (if available via )

3. **Detect scope changes** — Find issues added after sprint start:
   

4. **Detect stalled work** — Issues in progress but not updated:
   

5. **Detect carryover risk** — Unfinished work in closing sprints:
   

6. **Synthesize sprint health**:
   - Completion rate: Done / Total
   - Scope creep indicator: newly added / original scope
   - Stall indicator: stalled count / in-progress count
   - Carryover rate: unfinished from last sprint / total last sprint

7. **Decision point**:
   - If completion rate < 50% AND sprint is >60% elapsed → flag as "At Risk"
   - If scope creep > 20% → flag scope change warning
   - If stall rate > 30% → flag stalled sprint warning

**Example scenario**: Project CORE sprint is 70% elapsed. Query shows 15 issues total: 3 Done, 8 In Progress, 4 To Do. 2 issues added mid-sprint. 3 issues in progress haven't been updated in 5 days. AI generates: "Sprint Health: 🟡 At Risk — 20% complete at 70% elapsed. 3 issues stalled >5 days. 2 issues added mid-sprint (13% scope creep)."

---

### 2.3 Workflow: Data Hygiene Audit

**Trigger**: Weekly scheduled run — detects data quality issues and nudges responsible teams.

**Autonomy**: 🟢 Fully autonomous (per role doc §2.6)

**Step-by-step operational pattern**:

1. **Run hygiene queries** — Execute each query pattern from the JQL pattern library:

   **a. Unmapped stories (no epic link)**:
   

   **b. Missing assignee on in-progress work**:
   

   **c. Stale epics (no updates in 30+ days)**:
   

   **d. Missing priority**:
   

   **e. Stories without story points**:
   

2. **Aggregate results** — Count issues per hygiene category:
   - unmapped_stories: count
   - missing_assignee: count
   - stale_epics: count
   - missing_priority: count
   - unestimated_stories: count

3. **Evaluate thresholds**:

   | Category | Warning | Violation |
   |----------|---------|-----------|
   | Unmapped stories | ≥ 3 | ≥ 10 |
   | Missing assignee (in progress) | ≥ 1 | ≥ 5 |
   | Stale epics | ≥ 2 | ≥ 5 |
   | Missing priority | ≥ 5 | ≥ 15 |
   | Unestimated stories (in sprint) | ≥ 3 | ≥ 8 |

4. **Construct nudge message** — For each category exceeding thresholds:
   

5. **Deliver via Slack**:
   

6. **Track hygiene trends** — Store weekly counts for trend analysis in subsequent reports.

**Example scenario**: Weekly audit of project PLATFORM finds 7 unmapped stories (warning threshold=3), 2 stale epics (at threshold), and 5 missing-priority issues (at threshold). AI sends nudge to #team-platform with specific issue keys and fix suggestions.

---

### 2.4 Workflow: Program Hierarchy Traversal (Advanced Roadmaps)

**Trigger**: On-demand — when TPM needs to understand full program scope or generate RAID views.

**Step-by-step operational pattern**:

1. **Expand program hierarchy** using :
   
   > **⚠️ Truncation risk**: Results may silently truncate at 1,000 issues. If count hits 1,000, slice by issue type or project.

2. **Generate RAID view** from hierarchy:
   

3. **Fallback for large programs** — If  returns 1,000 (truncation suspected):
   

4. **Alternative without Advanced Roadmaps** — Use epic-based traversal:
   

**Guardrails**:
- Always scope  to specific projects when possible
- Never use  without project filters on large instances (risk of >65k sprint IDs)
- Issue keys in  are case-sensitive — use exact case

---

### 2.5 Workflow: OKR Progress Roll-up

**Trigger**: Weekly — aggregate OKR/goal progress from Jira issue completion.

**Step-by-step operational pattern**:

1. **Fetch Atlas goals**:
   {
  "apiVersion": "v2",
  "command": "goals.query",
  "request": {
    "scope": "me",
    "role": "owner",
    "status": null,
    "statusAll": false,
    "resolvedStatusFilter": null,
    "tql": "phase = in_progress OR phase = pending",
    "tag": null,
    "rootAccountId": null,
    "rootName": null,
    "rootEmail": null,
    "updatedSince": null,
    "createdSince": null,
    "includeContributingProjects": false,
    "includeParentGoal": false,
    "limit": 100,
    "sqliteFile": null
  },
  "data": [],
  "meta": {
    "resourceClass": "entity",
    "sourceMode": "native",
    "resourceType": "goals",
    "count": 0,
    "scope": "me"
  }
}

2. **For each goal, find linked Jira work**:
   

3. **Calculate completion metrics**:
   - Issues completed this week per goal
   - Remaining open issues per goal
   - Velocity trend (comparison to prior weeks)

4. **Feed into status report** — Pass aggregated data to  skill for weekly status report ADF generation.

## 3. Domain Guidance

### 3.1 JQL Query Pattern Reference

The full JQL pattern library is maintained in the knowledge block . Key categories:

| Category | Pattern Count | Key Functions |
|----------|--------------|---------------|
| Dependency Tracking | 6 | , ,  |
| Sprint Health | 5 | , ,  |
| Data Hygiene | 8 | , ,  |
| Cross-Project | 4 | , cross-project link queries |
| Advanced Roadmaps | 3 | ,  |

### 3.2 Staleness Thresholds by Issue Type

| Issue Type | Warning (days since update) | Violation (days since update) |
|------------|---------------------------|------------------------------|
| Story / Task | 14 | 30 |
| Bug | 7 | 14 |
| Epic | 30 | 60 |
| Initiative | 60 | 90 |
| Sub-task | 7 | 14 |

### 3.3 Decision Criteria

- **When to escalate vs. nudge**: Escalate to program sponsor if a blocker has been unresolved for >2x the violation threshold. Nudge the owning team for warning-level issues.
- **When to create vs. update issues**: Create new tracking issues for risks/decisions discovered during scans. Update existing issues when new information surfaces.
- **Sprint health RAG classification**:
  - 🟢 **Green**: Completion rate ≥ 70% of elapsed %, scope creep < 10%, stall rate < 15%
  - 🟡 **Yellow**: Completion rate ≥ 40% of elapsed %, OR scope creep 10-25%, OR stall rate 15-30%
  - 🔴 **Red**: Completion rate < 40% of elapsed %, OR scope creep > 25%, OR stall rate > 30%

### 3.4 Nudge Message Tone Guidelines

- **Be specific**: Always include issue keys, assignee names, and concrete fix suggestions
- **Be actionable**: Every nudge must tell the recipient exactly what to do
- **Be respectful**: Use neutral language — "Can you provide a status update?" not "Why hasn't this been updated?"
- **Avoid fatigue**: Maximum 1 nudge per team per day for non-critical items. Batch hygiene findings into weekly reports.
- **Use emoji sparingly**: ⚠️ for warnings, 🔴 for critical, 📋 for reports, ✅ for resolved

### 3.5 Terminology

| Term | Definition |
|------|-----------|
| **Carryover** | Issues not completed in a sprint that roll into the next sprint |
| **Scope creep** | Issues added to an active sprint after sprint start |
| **Stale issue** | An issue that hasn't been updated within the staleness threshold for its type |
| **Unmapped story** | A story/task without an Epic Link, making it invisible in program rollups |
| **RAID** | Risks, Assumptions, Issues, Dependencies — the four categories tracked in a RAID log |
| **RAG status** | Red/Amber(Yellow)/Green traffic-light health indicator |
| **portfolioChildIssuesOf** | Advanced Roadmaps JQL function returning all hierarchy descendants of an issue |
| **Status category** | Jira's three meta-statuses: To Do, In Progress, Done — mapped from custom workflow statuses |

### 3.6 Cadence Patterns

| Activity | Cadence | Autonomous? |
|----------|---------|-------------|
| Dependency scan | Continuous / daily | 🟢 Yes |
| Sprint health check | Daily | 🟢 Yes |
| Data hygiene audit | Weekly (Monday) | 🟢 Yes |
| OKR progress roll-up | Weekly (Friday) | 🟢 Yes |
| Cross-system consistency check | Weekly | 🟢 Yes |
| Escalation to sponsor | As needed | 🟡 Propose only |

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
|  CLI | , , , , , ,  |
| MCP  | All JQL queries (dependency, hygiene, sprint health, hierarchy) |
| MCP  | Rich issue detail with links, transitions, comments |
| MCP  | Create risk/decision tracking issues |
| MCP  | Update issue fields, add comments, transition status |
|  | Deliver nudges, status summaries, escalation alerts |
|  | Resolve team channel names to Slack channel IDs |

### 4.2 Cross-Tool Patterns

1. **JQL Query → Issue Enrichment**: Run bulk JQL via  → enrich top results with  (for links, comments) or  (for cross-product context)
2. **Hygiene Audit → Slack Nudge**: Run hygiene JQL queries → aggregate by team → construct nudge per team →  → 
3. **Jira Data → Confluence Report**: Run sprint/dependency queries → aggregate metrics → pass to  skill for ADF generation and page update
4. **Status Discovery → JQL Construction**: Run {
  "apiVersion": "v2",
  "command": "jira.space.statuses",
  "request": {
    "idOrKey": "PROJ"
  },
  "data": {
    "statuses": [
      {
        "id": "53354",
        "name": "On Hold",
        "statusCategory": {
          "key": "new",
          "name": "To Do"
        }
      },
      {
        "id": "48265",
        "name": "Parking lot",
        "statusCategory": {
          "key": "new",
          "name": "To Do"
        }
      },
      {
        "id": "48284",
        "name": "Backlog",
        "statusCategory": {
          "key": "new",
          "name": "To Do"
        }
      },
      {
        "id": "48292",
        "name": "Ready for Release",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "52081",
        "name": "Secondment",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48291",
        "name": "Pilot Successful?",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48290",
        "name": "Monitoring Pilot",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48289",
        "name": "Planning Phase",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48288",
        "name": "Approved for Implementation",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "56933",
        "name": "In progress",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48285",
        "name": "Under Review",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48286",
        "name": "Need More Information",
        "statusCategory": {
          "key": "indeterminate",
          "name": "In Progress"
        }
      },
      {
        "id": "48263",
        "name": "Released/Done",
        "statusCategory": {
          "key": "done",
          "name": "Done"
        }
      },
      {
        "id": "48287",
        "name": "Won't Do",
        "statusCategory": {
          "key": "done",
          "name": "Done"
        }
      }
    ]
  },
  "meta": {
    "resourceClass": "entity",
    "sourceMode": "rest",
    "resourceType": "jira.status"
  }
} → use discovered status names in JQL queries to avoid invalid status references

### 4.3 Autonomy Levels

| Operation | Level | Notes |
|-----------|-------|-------|
| All read/query operations | 🟢 Autonomous | No restrictions on reading Jira data |
| Data hygiene nudge (Slack) | 🟢 Autonomous | Routine nudges are fully autonomous |
| Create tracking issues (risk, decision) | 🟢 Autonomous | AI can create new issues |
| Update issue fields | 🟢 Autonomous | AI can update summary, assignee, labels |
| Transition issue status | 🟡 Propose | Propose transition, confirm with human for critical path items |
| Escalation messages | 🟡 Propose | Draft escalation, human confirms before send |
| Modify program scope/milestones | 🔴 Human only | AI proposes, human decides |

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

- **NEVER** modify issue status on critical-path items without human confirmation
- **NEVER** send escalation messages to executives without human review
- **NEVER** use  or  without project filters on large instances (>65k sprint risk)
- **NEVER** delete Jira issues — only transition to cancelled/closed status
- **NEVER** modify issues in projects outside the TPM's assigned program scope
- **ALWAYS** scope JQL queries with  or  for performance
- **ALWAYS** use exact case for issue keys in  (case-sensitive)

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| Blocker unresolved > 2x violation threshold | Escalate to program sponsor |
| Sprint completion < 30% at 80% elapsed | Escalate to engineering manager |
| Data hygiene violation count doubles week-over-week | Escalate to team lead |
| JQL query returns 1,000 results (truncation suspected) | Warn user, suggest scoping refinement |
| Cross-project blocker with no owner | Escalate to both project leads |

### 5.3 Error Handling

| Error | Recovery Action |
|-------|----------------|
| JQL query timeout | Narrow scope: reduce project list or date range, retry |
| JQL syntax error | Check status names via , correct and retry |
| MCP tool rate limit | Exponential backoff: 1s → 2s → 4s, max 3 retries |
| Issue not found (404) | Verify issue key case and project, search by summary if needed |
|  returns 1,000 | Truncation likely — slice query by project or issue type |
| Slack channel not found | Search by alternative name patterns, ask user if unresolvable |
| Authentication failure | Verify TWG_TOKEN / TWG_SITE environment variables are set |
