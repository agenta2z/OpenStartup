# Compass and TWG Data Model Reference

This knowledge block captures the data model, ARI formats, relationship types, and integration patterns
between Atlassian Compass (service catalog) and Teamwork Graph (TWG) that are essential for the AI TPM role.

## 1. Compass Component Data Model

### Component Types
| Type ID | Description | Example |
|---------|-------------|---------|
| `SERVICE` | A backend or API service | payments-gateway, auth-service |
| `APPLICATION` | A user-facing application | jira-frontend, confluence-web |
| `LIBRARY` | A shared code library | common-utils, auth-sdk |
| `CAPABILITY` | A business capability grouping | payment-processing, user-management |
| `CLOUD_RESOURCE` | Cloud infrastructure resource | S3 bucket, RDS instance |
| `DATA_PIPELINE` | Data processing pipeline | analytics-etl, event-stream |
| `MACHINE_LEARNING_MODEL` | ML model | recommendation-engine |
| `UI_ELEMENT` | Reusable UI component | design-system-button |
| `WEBSITE` | Public website | atlassian.com, developer.atlassian.com |
| `OTHER` | Anything else | documentation-site |

### Core Fields (compass.yml)
```yaml
configVersion: 1
name: 'my-service'
id: 'ari:cloud:compass:<cloudId>:component/<workspaceId>/<componentId>'
ownerId: 'ari:cloud:identity::team/<team-uuid>'
typeId: SERVICE
fields:
  tier: 1          # 1-4 (1 = most critical)
  lifecycle: Active  # Pre-release | Active | Deprecated
labels:
  - payment
  - backend
links:
  - name: Slack Channel
    type: CHAT_CHANNEL
    url: https://slack.com/...
  - name: On-call schedule
    type: ON_CALL
    url: https://...
  - name: Runbooks
    type: DOCUMENT
    url: https://...
  - name: Repository
    type: REPOSITORY
    url: https://bitbucket.org/...
  - name: Dashboard
    type: DASHBOARD
    url: https://...
  - name: JSM Service
    type: PROJECT
    url: https://...
relationships:
  DEPENDS_ON:
    - '<upstream-compass-component-ari>'
customFields:
  - name: Technical Owner
    type: user
    value: 'ari:cloud:identity::user/<userId>'
  - name: Department
    type: text
    value: 'Eng - Platform'
```

### Metadata Standards (Required for Tier 0-2)
All components MUST have:
- **Lifecycle state**: Pre-release, Active, or Deprecated
- **Valid team ownership**: Atlas/managed team via `ownerId`
- **Description and help links**

Service components additionally require:
- Repository links
- On-call schedule link
- Dashboard link
- Dependency relationships populated

### Relationship Types

| Relationship | Direction | Meaning |
|-------------|-----------|---------|
| `DEPENDS_ON` | Horizontal | Source service depends on target service at runtime |
| `DEPENDED_ON_BY` | Horizontal (reverse) | Target service is depended on by source (reverse of DEPENDS_ON) |
| `CONTAINS` | Vertical | Platform/capability contains a sub-component |
| `CONTAINED_BY` | Vertical (reverse) | Component is part of a larger platform/capability |

**Limits:**
- A component can depend on up to **25 upstream** components
- A component can have up to **100 downstream** dependents

### Link Types
| Type | Purpose |
|------|---------|
| `REPOSITORY` | Source code repository |
| `DASHBOARD` | Monitoring dashboard |
| `PROJECT` | Associated Jira/JSM project |
| `CHAT_CHANNEL` | Team Slack/chat channel |
| `ON_CALL` | On-call schedule link |
| `DOCUMENT` | Runbook, DR plan, go-live doc |
| `OTHER_LINK` | Any other link |

---

## 2. ARI (Atlassian Resource Identifier) Formats

### Common ARI Patterns
| Entity | ARI Format | Example |
|--------|-----------|---------|
| Compass Component | `ari:cloud:compass:<cloudId>:component/<workspaceId>/<componentId>` | `ari:cloud:compass:abc123:component/ws1/comp1` |
| Identity Team | `ari:cloud:identity::team/<teamUuid>` | `ari:cloud:identity::team/00000000-0000-0000-0000-000000000000` |
| Identity User | `ari:cloud:identity::user/<userId>` | `ari:cloud:identity::user/712020:5cf4b2db...` |
| Organization | `ari:cloud:platform::org/<orgUuid>` | `ari:cloud:platform::org/abc-123-def` |
| Jira Issue | `ari:cloud:jira:<cloudId>:issue/<issueId>` | `ari:cloud:jira:abc123:issue/10001` |
| Confluence Page | `ari:cloud:confluence:<cloudId>:page/<pageId>` | `ari:cloud:confluence:abc123:page/12345` |

### Key Integration Point: Team ARI
The **team ARI** (`ari:cloud:identity::team/<uuid>`) is the critical join key between:
- **Compass** `ownerId` field → identifies which team owns a component
- **TWG** team queries → resolves team members, hierarchy, workspaces
- **Atlassian Team MCP** tools → searches, details, hierarchy operations

When a Compass component returns `ownerId`, that value can be used directly as the `teamId` parameter
in TWG and Atlassian Team MCP tools.

---

## 3. Teamwork Graph (TWG) Entity Model

### Core Entities
| Entity | Description | Source |
|--------|-------------|--------|
| `IdentityUser` | A person with an Atlassian account | Identity service |
| `IdentityTeam` / `TeamsTeam` | An organizational team | Atlassian Teams |
| `OpsgenieTeam` | An on-call/operations team | Opsgenie/JSM Ops |
| `JiraWorkItem` | A Jira issue, epic, story, task | Jira |
| `ConfluencePage` | A Confluence page or blog post | Confluence |
| `AtlasProject` | An Atlas/Townsquare project | Atlas |
| `AtlasGoal` | An organizational goal | Atlas |
| `CompassComponent` | A software component (via DX migration) | Compass |

### Key Relationships
| Relationship | From | To | Meaning |
|-------------|------|----|---------|
| `user_is_in_team` | User | Team | User is a member of the team |
| `team_has_parent_team` | Team | Team | Hierarchical team nesting |
| `user_assigned_issue` | User | JiraWorkItem | User is assigned to the issue |
| `atlas_project_has_owner` | AtlasProject | User | Project ownership |
| `atlas_project_contributes_to_atlas_goal` | AtlasProject | AtlasGoal | Project-goal alignment |
| `atlas_project_is_tracked_on_jira_epic` | AtlasProject | JiraWorkItem | Project tracking |
| `parent_issue_has_child_issue` | JiraWorkItem | JiraWorkItem | Issue hierarchy |

### TWG Access Channels

| Channel | Best For | Format |
|---------|----------|--------|
| **TWG CLI** (`twg` command) | Human-readable team/org queries, fuzzy name matching | Formatted text or JSON |
| **TWG MCP Tools** (`mcp__teamwork_graph__`) | Programmatic access to graph data | Structured JSON |
| **Atlassian Team MCP** (`mcp__atlassian_team__`) | Team identity CRUD operations, hierarchy | Structured JSON |
| **GraphQL (AGG)** | Complex multi-hop queries | GraphQL response |
| **Cypher (Flock)** | Advanced graph traversals | Cypher query results |

### TWG CLI Key Commands

**Teams:**
- `twg teams query -q "<name>" --all` — Search all teams by name
- `twg teams query -m <accountId>` — List teams for a specific user
- `twg teams get "<team-name>"` — Get team details by name (fuzzy match)
- `twg teams get "ari:cloud:identity::team/<uuid>"` — Get team by ARI

**Org Tree:**
- `twg org-tree --name "<person-name>"` — Show org hierarchy for a person
- `twg org-tree --email "<email>" --depth 5` — Show deep hierarchy
- `twg org-tree <accountId> --up-only` — Show only ancestors (management chain)
- `twg org-tree <accountId> --down-only` — Show only direct reports tree

---

## 4. On-Call Data Model

### Compass On-Call Integration
On-call data is surfaced on Compass components through integrations with:
- **Opsgenie** (native Atlassian)
- **JSM Operations** (shared platform with Compass)
- **PagerDuty** (third-party integration)

### On-Call Data Structure (from Compass Component Search)
When `includeOnCallSchedules: true` is passed to component search:
```json
{
  "onCallSchedules": {
    "nodes": [
      {
        "scheduleId": "...",
        "scheduleName": "Payments On-call - Business Hours",
        "scheduleLink": "https://...",
        "currentResponders": [
          {
            "name": "Jane Smith",
            "accountId": "712020:..."
          }
        ]
      }
    ]
  }
}
```

### Escalation Policy Structure
Escalation policies follow a tiered approach:
```
High Priority Escalation:
  0m  → Page on-call (Business Hours schedule)
  0m  → Page on-call (PAID/24x7 schedule)
  15m → Page next on-call in rotation
  20m → Page MIM (Major Incident Manager)
```

### Key Principle: Team-Based Ownership
- Each service has a **single owning team** (Atlas team)
- On-call schedules are typically owned by the same team
- If **JSM Responder Team ≠ Compass Owner Team**, this is a data quality issue to flag

---

## 5. Jira Issue Link Model (for Dependencies)

### Issue Link Types
```json
{
  "id": "10000",
  "name": "Blocks",
  "inward": "is blocked by",
  "outward": "blocks"
}
```

### Link Directionality for Dependencies
- **Outward** (`blocks`, `depends on`) → this issue is the **blocker/provider**
- **Inward** (`is blocked by`, `is depended on by`) → this issue is the **blocked/consumer**

### Advanced Roadmaps Treatment
- All dependency links are treated as `blocks / is blocked by` for scheduling
- Lead time = `start(blocked) - end(blocking)` in calendar days
- Negative lead time = conflict (blocked work starts before blocker finishes)

### Common Dependency Link Types
| Link Name | Outward | Inward |
|-----------|---------|--------|
| Blocks | blocks | is blocked by |
| Depends | depends on | is depended on by |
| Cloners | clones | is cloned by |
| Relates | relates to | relates to |

For dependency tracking, focus on `Blocks` and any custom `Depends` type links.

---

## 6. Cross-System Join Patterns

### Pattern: Component → Team → People
```
Compass Component
  └── ownerId (team ARI)
       └── TWG get_team_users_v2(teamId)
            └── Team members (accountId, name, role)
                 └── TWG get_user_manager_v2(userId)
                      └── Manager (for escalation)
```

### Pattern: Component → Dependencies → Impact
```
Compass Component (changed)
  └── Search for components that DEPEND_ON this component
       └── For each dependent:
            ├── Tier, Type, Lifecycle (from Compass)
            ├── Owner Team (from ownerId)
            ├── On-Call (from onCallSchedules)
            └── Active Jira Work (from JQL search)
```

### Pattern: Jira Issue → Component → Team
```
Jira Issue (with dependency links)
  └── Extract component reference (label, Compass link)
       └── Compass Component Search
            └── Owner Team (ownerId)
                 └── TWG Team Details
```

### Pattern: Program → Teams → Components → Dependencies
```
Atlas Project / Jira Epic (program scope)
  └── TWG get_project_context_v2 → teams involved
       └── For each team:
            ├── Compass search by ownerIds → components owned
            └── For each component:
                 └── Dependencies (DEPENDS_ON)
```
