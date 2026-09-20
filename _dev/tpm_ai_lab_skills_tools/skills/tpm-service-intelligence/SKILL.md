---
name: tpm-service-intelligence
description: >
  Provides domain-specific workflow guidance for an AI Technical Program Manager (TPM)
  to perform service ownership lookups, dependency graph construction, impact analysis,
  dependency lead-time tracking, team topology mapping, and escalation routing using
  Compass, Teamwork Graph (TWG), Jira, and Atlassian Team tools.
labels:
  - tpm
  - service-catalog
  - dependency-management
  - incident-response
  - program-management
metadata:
  tools:
    - compass_compass_atlassian_component_search
    - compass_compass_atlassian_component_get_package_dependencies
    - compass_compass_atlassian_component_get_documentation
    - compass_compass_atlassian_component_get_event_sources
    - compass_compass_atlassian_component_get_api_changelogs
    - compass_compass_atlassian_component_get_custom_field_definitions
    - twg_twg_atlassian_graph_get_team_users_v2
    - twg_twg_atlassian_graph_get_user_teams_v2
    - twg_twg_atlassian_graph_get_user_report_chain_v2
    - twg_twg_atlassian_graph_get_user_direct_reports_v2
    - twg_twg_atlassian_graph_get_user_manager_v2
    - twg_twg_atlassian_graph_get_user_org_hierarchy
    - twg_twg_atlassian_graph_get_team_spaces
    - twg_twg_atlassian_graph_get_context_for_work_item
    - twg_twg_atlassian_graph_get_project_context_v2
    - twg_twg_atlassian_graph_get_team_projects_v2
    - twg_twg_atlassian_graph_get_user_active_projects_v2
    - atlassian_team_atlassian_team_atlassian_team_search
    - atlassian_team_atlassian_team_atlassian_team_get_team
    - atlassian_team_atlassian_team_atlassian_team_get_hierarchy
    - get_jira_issue
    - search_jira_using_jql
    - search_confluence_using_cql
---

# TPM Service Intelligence Skill

## 1. Skill Overview

### Name


### Description
This skill provides an AI Technical Program Manager (TPM) with structured workflows to:
- **Look up component/service ownership** — find who owns a service, which team, and current on-call
- **Build dependency graphs** — construct and traverse service dependency maps for a program
- **Run impact analysis** — determine blast radius of planned changes or incidents
- **Track dependency lead time** — measure and report on dependency resolution timelines
- **Map team topology** — understand team structures, org hierarchy, and cross-team relationships for a program
- **Route escalations** — find the right person to contact via on-call, team owner, and manager chain

### Leveraged Tools

| Tool | Capability Summary |
|------|--------------------|
|  | Search Compass component catalog with optional dependency, on-call, and custom field enrichment |
|  | Retrieve package-level dependencies and versions for a component |
|  | Fetch documentation links for a Compass component |
|  | Get deployment and event source data for a component |
|  | Track API changes for a component |
|  | Retrieve custom field definitions for the Compass instance |
|  | List members of a team by team ID |
|  | Find which teams a user belongs to |
|  | Fetch management chain up to 10 levels |
|  | Get direct reports for a user |
|  | Get a user's immediate manager |
|  | Fetch full org hierarchy under a user |
|  | Retrieve Confluence spaces and Jira projects associated with a team |
|  | Get comprehensive context for a Jira issue including PRs, commits, pages |
|  | Get project details including team members, contributors, owners |
|  | Retrieve projects and goals associated with a team |
|  | Search for teams by name with pagination |
|  | Get detailed team info including members |
|  | Get team parent/child hierarchy |
|  | Fetch Jira issue details including links, transitions, comments |
|  | Search Jira issues using JQL |
|  | Search Confluence pages using CQL |
| TWG CLI 
  1. eng-p60-all  ACTIVE (you)
     Members: 1124    ARI: ari:cloud:identity::team/0d5330d4-3ab3-4874-931c-ce3b3e8b22aa
     https://home.atlassian.com/o/2346a038-3c8c-498b-a79b-e7847859868d/people/team/0d5330d4-3ab3-4874-931c-ce3b3e8b22aa?cloudId=a436116f-02ce-4520-8fbb-7301462a1674

  2. Eng - Product AI (Puyang Xu)  ACTIVE (you)
     Members: 4    ARI: ari:cloud:identity::team/11e6c38d-8c0d-4ff8-943b-a432d753095f
     https://home.atlassian.com/o/2346a038-3c8c-498b-a79b-e7847859868d/people/team/11e6c38d-8c0d-4ff8-943b-a432d753095f?cloudId=a436116f-02ce-4520-8fbb-7301462a1674

  3. AI Lab  ACTIVE (you)
     Members: 7    ARI: ari:cloud:identity::team/aa909a9d-7679-4060-bd10-a181951a5dc2
     https://home.atlassian.com/o/2346a038-3c8c-498b-a79b-e7847859868d/people/team/aa909a9d-7679-4060-bd10-a181951a5dc2?cloudId=a436116f-02ce-4520-8fbb-7301462a1674 | Search/list teams with member counts and ARIs |
| TWG CLI  | Get single team details with full member list |
| TWG CLI 
  Organizational Hierarchy for Tony Chen
  5 ancestor(s), 0 descendant(s)

  Mike Cannon-Brookes
  └── Taroon Mandhana
      └── Guihong Cao
          └── Kang Li
              └── Puyang Xu
                  └── Tony Chen ◀ YOU ARE HERE | Navigate management chains and reporting trees |

---

## 2. Workflow Mappings

### 2.1 Workflow: Component Ownership Lookup

**Trigger Conditions:**
- User asks "who owns service X?", "owner of component Y", "which team is responsible for Z"
- During incident triage when affected component owners need identification
- During program dependency mapping to confirm service owners
- During governance reviews to verify Tier 0/1/2 services have valid owners

**Step-by-Step Operational Pattern:**

**Step 1 — Resolve Component in Compass**

- If multiple components returned, disambiguate by presenting top matches (name, type, tier) and asking user to confirm
- If zero results, try alternate names/aliases, or ask user for clarification
- Extract from response: , , , , 

**Step 2 — Resolve Owner Team Details via TWG**

- Extract team members with roles (Member vs Admin/Lead)
- Identify team lead or engineering manager if role data is available

**Step 3 — Get Team Hierarchy (optional, if user wants org context)**

- Shows parent team and child teams for organizational context

**Step 4 — Present Results**
Format output as:


**Example Scenario:**
> User: "Who owns the payments-gateway service?"
> 1. Search Compass for "payments-gateway" with on-call → finds component with ownerId 
> 2. Fetch team members via TWG → "Payments Platform" team, 8 members, lead is Jane Smith
> 3. On-call data shows Bob Johnson is current on-call via "Payments On-call - Business Hours" schedule
> 4. Present structured ownership report

---

### 2.2 Workflow: Build Dependency Graph for a Program

**Trigger Conditions:**
- User asks "build dependency graph for <program/services>", "map dependencies for <service list>"
- During Program Increment planning to understand upstream technical dependencies
- For architecture/readiness reviews
- When assessing change impact at program scope

**Step-by-Step Operational Pattern:**

**Step 1 — Identify Root Components**
If user provides explicit component names:

Repeat for each named service. Select the best match from results.

If user provides a program/project but not components:

Then use team/project context to identify related Compass components via labels or naming conventions.

**Step 2 — Fetch Dependencies (BFS Traversal)**
For each root component, extract  with type  from the search results.

Initialize:
- 
- 
- 
- ,  (configurable, default 2)

**Step 3 — Recursive Traversal**
While  is non-empty AND :


**Cycle detection**: Skip any component already in .

**Step 4 — Enrich with Metadata**
For each node in the graph, ensure we have:
- , , , , , 

**Step 5 — Fetch Package Dependencies (optional)**

Identifies shared packages across services (potential single points of failure).

**Step 6 — Present Results**


---

### 2.3 Workflow: Impact Analysis for Planned Change

**Trigger Conditions:**
- User asks "what is the blast radius of changing <service>?", "impact analysis for <component>"
- Before deploying changes to a shared service
- During incident response to understand affected downstream services
- Change Advisory Board (CAB) preparation

**Step-by-Step Operational Pattern:**

**Step 1 — Resolve the Changed Component**


**Step 2 — Traverse Downstream Dependents (Blast Radius)**
The impact analysis needs **who depends ON this component** (reverse direction).

Since Compass search returns  (what this component depends on), for downstream dependents we need to search for components that depend on the changed component:


BFS traversal outward from changed component:
- Track:  with hop distance, tier, type, owner team
- Stop at  (default: 2) or when node count exceeds 500 (safety threshold)
- Record relationship type:  (horizontal) and  (vertical)

**Step 3 — Classify Blast Radius**
For each affected component, record:
- Hop distance from changed component
- Service tier (0-4)
- Component type (SERVICE, APPLICATION, LIBRARY, etc.)
- Owner team
- On-call status (has active on-call? yes/no)

Classify overall blast radius:
- **GLOBAL**: Multi-region, affects Tier 0-1 services across multiple teams
- **REGIONAL**: Limited to one region or segment
- **PROGRESSIVE**: Can be mitigated with feature flags, canary deployments

**Step 4 — Identify Active Jira Work Items**
For each affected component's owner team:

This surfaces active work that might be disrupted by the change.

**Step 5 — Resolve Team Context via TWG**
For each unique owner team in the blast radius:

Get team members for notification and coordination.

**Step 6 — Present Impact Report**


---

### 2.4 Workflow: Dependency Lead Time Tracking

**Trigger Conditions:**
- User asks "what's the lead time on our dependencies?", "dependency lead time report for <project>"
- During quarterly planning to assess dependency health
- When tracking cross-team dependency resolution velocity
- Sprint retrospectives focused on blockers

**Step-by-Step Operational Pattern:**

**Step 1 — Identify Dependency Issues in Scope**
```
Tool: search_jira_using_jql
Parameters:
  jql: "project = <PROJECT> AND issueLinkType in ('Blocks', 'is blocked by') AND created >= '<start-date>' ORDER BY created DESC"
  limit: 50
```
Alternative for cross-project scope:
```
Tool: search_jira_using_jql
Parameters:
  jql: "labels = '<program-label>' AND issueLinkType = 'Blocks' AND status changed during ('<start>', '<end>')"
  limit: 100
```

**Step 2 — For Each Issue, Extract Dependency Links**
```
Tool: get_jira_issue
Parameters:
  issue_url: "<issue-url>"
  show_links: true
  get_comments: false
```
From the response, extract `issuelinks[]` where:
- `type.name` matches configured dependency types (default: "Blocks", "Depends")
- Normalize direction:
  - Outward `blocks` → this issue is the **blocker**
  - Inward `is blocked by` → this issue is the **blocked**

**Step 3 — Determine Effective Dates**
For each dependency pair (A blocks B):

Date resolution priority order:
1. **Advanced Roadmaps schedule fields** (target start, target end) — if available
2. **Status transition timestamps** — from issue changelog:
   - `blockingEnd` = timestamp when blocking issue moved to Done status category
   - `blockedStart` = timestamp when blocked issue first moved to In Progress status category
3. **System fields fallback**:
   - `blockingEnd` = `resolutiondate` if set, else `updated`
   - `blockedStart` = `created` date of blocked issue

**Step 4 — Compute Lead Time**
```
leadTimeDays = blockedStart - blockingEnd  (in calendar days)
```

Classify each dependency:
- `leadTimeDays >= 0` → **on-track** (blocking work finished before blocked work started)
- `leadTimeDays < 0` → **at-risk/conflict** (blocked work started before blocker was resolved)
- Missing dates → **date-incomplete** (flag for human review)

**Step 5 — Aggregate Metrics**
Compute across all dependency pairs in scope:
- **Average lead time** (days)
- **Median lead time** (P50)
- **P90 lead time** — 90th percentile
- **Count of at-risk dependencies** (negative lead time)
- **Count of date-incomplete dependencies**

Optionally group by:
- Owner team (via Compass component lookup)
- Project/program
- Dependency type

**Step 6 — Present Report**
```
## Dependency Lead Time Report
### Scope: <project/program> | Period: <start> to <end>

### Summary Metrics:
- Total dependency pairs analyzed: <N>
- Average lead time: <X> days
- Median (P50): <Y> days
- P90: <Z> days
- At-risk (negative lead time): <count> (<percentage>%)
- Date-incomplete: <count>

### At-Risk Dependencies (negative lead time):
| Blocker | Blocked | Lead Time | Blocker Status | Team |
|---------|---------|-----------|----------------|------|
...

### Lead Time by Team:
| Team | Avg Lead Time | P50 | # Dependencies |
|------|--------------|-----|----------------|
...

### Recommendations:
- [If P90 > 5 days] Consider adding SLA commitments for cross-team dependencies
- [If many date-incomplete] Improve date hygiene — ensure start/end dates are set
- [If negative lead time clusters] Schedule dependency sync with affected teams
```

---

### 2.5 Workflow: Team Topology for a Program

**Trigger Conditions:**
- User asks "show me the team topology for <program>", "what teams are involved in <initiative>"
- During program kickoff to map stakeholders
- For organizational alignment reviews
- When onboarding to a new program

**Step-by-Step Operational Pattern:**

**Step 1 — Identify Program Components**
If user provides service names:
```
Tool: compass_compass_atlassian_component_search
Parameters:
  queryString: "<service-name>"
  includeDependsOn: true
  includeCustomFields: true
```

If user provides a project/goal:
```
Tool: twg_twg_atlassian_graph_get_project_context_v2
Parameters:
  projectId: "<project-ari>"
```
Extract associated teams and components from the project context.

**Step 2 — Collect Unique Owner Teams**
From all components discovered in Step 1, collect unique `ownerId` values (team ARIs).

**Step 3 — Resolve Team Details**
For each unique team:
```
Tool: twg_twg_atlassian_graph_get_team_users_v2
Parameters:
  teamId: "<team-ari>"
```
And optionally:
```
Tool: atlassian_team_atlassian_team_atlassian_team_get_hierarchy
Parameters:
  teamId: "<team-uuid>"
```

**Step 4 — Get Team Workspaces**
For each team:
```
Tool: twg_twg_atlassian_graph_get_team_spaces
Parameters:
  teamId: "<team-ari>"
```
Returns associated Confluence spaces and Jira projects.

**Step 5 — Build Topology Map**
Construct a hierarchical view:
```
Org Unit (from team hierarchy)
└── Parent Team
    ├── Team A (owns: service-1, service-2)
    │   ├── Members: ...
    │   ├── Spaces: CONF-SPACE-A, JIRA-PROJ-A
    │   └── On-call: configured ✓
    └── Team B (owns: service-3)
        ├── Members: ...
        ├── Spaces: CONF-SPACE-B
        └── On-call: not configured ⚠
```

**Step 6 — Present Report**
```
## Team Topology: <program-name>

### Teams Involved: <count>
### Total Engineers: <count>
### Cross-Team Dependencies: <count>

### Team Map:
<hierarchical topology from Step 5>

### Cross-Team Dependency Matrix:
| Consuming Team | Providing Team | # Dependencies |
|---------------|----------------|----------------|
...

### Communication Channels:
| Team | Slack | Confluence Space | Jira Project |
|------|-------|------------------|--------------|
...

### Gaps & Risks:
- [If team has no on-call] ⚠ <team> owns Tier <N> services but has no on-call
- [If orphan components] ⚠ <component> has no owner team assigned
- [If deep hierarchy] Note: <team> is 4+ levels deep in org — escalation path may be long
```

---

### 2.6 Workflow: Escalation Routing

**Trigger Conditions:**
- User asks "who should I escalate to for <service>?", "escalation path for <component>"
- During incident response when on-call is unresponsive
- When a dependency blocker needs management attention
- For cross-team coordination requiring leadership alignment

**Step-by-Step Operational Pattern:**

**Step 1 — Resolve Service and Owner Team**
```
Tool: compass_compass_atlassian_component_search
Parameters:
  queryString: "<service-name>"
  includeOnCallSchedules: true
```
If no component found, route to a configured triage/catch-all team.

**Step 2 — Check On-Call (Level 1)**
From the Compass component response, check `onCallSchedules`:
- If on-call data is present and has current responders:
  - **Level 1 = Current On-Call Person**
  - Record: name, accountId, schedule name, schedule link
- If no on-call configured:
  - Skip to Step 3 (team owner fallback)

**Step 3 — Team Owner / EM (Level 2)**
```
Tool: twg_twg_atlassian_graph_get_team_users_v2
Parameters:
  teamId: "<owner-team-ari>"
```
Identify the team admin/lead from the members list (role = "Admin" or designated lead).
- **Level 2 = Team Owner / Engineering Manager**

If no admin/lead is identifiable, use the full team as Level 2 (broadcast via team Slack channel).

**Step 4 — Manager Chain (Level 3+)**
Starting from the Level 1 or Level 2 person:
```
Tool: twg_twg_atlassian_graph_get_user_report_chain_v2
Parameters:
  userId: "<base-person-account-id>"
```
Walk up the management chain, adding each manager as a subsequent escalation level.
Stop when:
- Reached VP/GM level (org ceiling)
- No further manager found
- Manager already appeared (loop detection)

**Step 5 — Present Escalation Chain**
```
## Escalation Chain: <service-name>

### Service: <name> (Tier: <tier>, Owner: <team-name>)

### Escalation Levels:
| Level | Type | Person | Contact |
|-------|------|--------|---------|
| 1 | On-Call | <name> | Slack: @handle, Schedule: <link> |
| 2 | Team Owner | <name> | Slack: @handle, #team-channel |
| 3 | Manager | <name> | Slack: @handle |
| 4 | Director | <name> | Slack: @handle |

### Team Channels:
- Slack: #team-<name>
- Email: <team-email>

### Notes:
- [If no on-call] ⚠ No on-call schedule configured — escalate directly to team owner
- [If owner team != responder team] ⚠ Compass owner team differs from JSM responder team — verify routing
```

---

## 3. Domain Guidance

### 3.1 Templates and Checklists

#### Program Dependency Review Checklist
- [ ] All program services identified in Compass
- [ ] Dependency graph built (depth >= 2)
- [ ] All Tier 0-1 services have owner teams assigned
- [ ] All Tier 0-1 services have on-call configured
- [ ] Cross-team dependencies identified and documented
- [ ] Dependency lead times computed for current quarter
- [ ] At-risk dependencies (negative lead time) reviewed with teams
- [ ] Escalation paths verified for critical services
- [ ] Team topology map shared with program stakeholders

#### Impact Analysis Template
```
# Impact Analysis: [Change Description]
**Date**: [date]  |  **Author**: [TPM name]  |  **Status**: Draft/Reviewed/Approved

## Changed Component
- Name: [component]
- Tier: [0-4]
- Owner: [team]

## Blast Radius
- Classification: [GLOBAL/REGIONAL/PROGRESSIVE]
- Services affected: [count]
- Teams affected: [count]

## Affected Services
[table from workflow 2.3]

## Risk Assessment
- Highest tier affected: [tier]
- Cross-region impact: [yes/no]
- Customer-facing impact: [yes/no]

## Mitigation Plan
- Rollout strategy: [canary/blue-green/progressive]
- Rollback plan: [description]
- Monitoring: [dashboards/alerts]

## Approvals Required
- [ ] Owner team lead
- [ ] Affected team leads (for Tier 0-1)
- [ ] Change Advisory Board (for GLOBAL changes)
```

### 3.2 Decision Criteria

#### Blast Radius Classification
| Criterion | GLOBAL | REGIONAL | PROGRESSIVE |
|-----------|--------|----------|-------------|
| Regions affected | Multi-region | Single region | Sub-region/canary |
| Tier 0-1 services in blast radius | >= 3 | 1-2 | 0 |
| Teams affected | >= 5 | 2-4 | 1 |
| Expected severity if failure | SEV1-2 | SEV2-3 | SEV3+ |

#### Dependency Lead Time Health Thresholds
| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| P50 lead time | >= 2 days | 0-2 days | < 0 days |
| P90 lead time | >= 5 days | 2-5 days | < 2 days |
| At-risk percentage | < 10% | 10-25% | > 25% |
| Date-incomplete rate | < 5% | 5-15% | > 15% |

#### Escalation Trigger Criteria
| Condition | Action |
|-----------|--------|
| Tier 0 service affected | Immediate escalation to Level 2+ |
| On-call unresponsive (15 min) | Escalate to Level 2 |
| Cross-team blocker unresolved (48h) | Escalate to Level 3 (manager) |
| GLOBAL blast radius change | Require CAB approval before deployment |

### 3.3 Terminology

| Term | Definition |
|------|-----------|
| **Component** | A software entity in Compass (SERVICE, APPLICATION, LIBRARY, CAPABILITY, CLOUD_RESOURCE, etc.) |
| **ARI** | Atlassian Resource Identifier — unique ID format: `ari:cloud:<product>:<cloudId>:<type>/<id>` |
| **Team ARI** | Identity team identifier: `ari:cloud:identity::team/<uuid>` — used as Compass `ownerId` |
| **Tier** | Service criticality level (0=most critical, 4=least). Tier 0-1 require on-call and full metadata |
| **Lifecycle** | Component state: Pre-release, Active, Deprecated |
| **Blast Radius** | Set of services/components affected by a change or incident |
| **Lead Time** | Days between blocking issue end and blocked issue start (Advanced Roadmaps definition) |
| **DEPENDS_ON** | Horizontal dependency relationship in Compass — directional: source depends on target |
| **CONTAINS/CONTAINED_BY** | Vertical/hierarchical relationship in Compass (platform → services) |
| **TWG** | Teamwork Graph — Atlassian's unified graph of people, teams, projects, and content |
| **On-Call** | Current responder for a service, sourced from Opsgenie/JSM/PagerDuty via Compass |
| **DRI** | Directly Responsible Individual — the person accountable for a component or decision |

### 3.4 Cadence Patterns

| Activity | Frequency | Workflow Used |
|----------|-----------|---------------|
| Dependency graph refresh | Quarterly (PI planning) | 2.2 Build Dependency Graph |
| Dependency lead time report | Bi-weekly or monthly | 2.4 Dependency Lead Time |
| Team topology update | Quarterly or on reorg | 2.5 Team Topology |
| Impact analysis | Per change (ad-hoc) | 2.3 Impact Analysis |
| Ownership audit | Monthly | 2.1 Ownership Lookup (batch) |
| Escalation path verification | Monthly | 2.6 Escalation Routing |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool Name | Operations Used |
|-----------|----------------|
| `compass_compass_atlassian_component_search` | Search components, get dependencies, on-call, custom fields |
| `compass_compass_atlassian_component_get_package_dependencies` | Get package-level dependencies |
| `compass_compass_atlassian_component_get_documentation` | Get component documentation links |
| `compass_compass_atlassian_component_get_event_sources` | Get deployment events |
| `twg_twg_atlassian_graph_get_team_users_v2` | List team members |
| `twg_twg_atlassian_graph_get_user_report_chain_v2` | Get management chain |
| `twg_twg_atlassian_graph_get_user_manager_v2` | Get immediate manager |
| `twg_twg_atlassian_graph_get_user_direct_reports_v2` | Get direct reports |
| `twg_twg_atlassian_graph_get_user_org_hierarchy` | Full org tree traversal |
| `twg_twg_atlassian_graph_get_team_spaces` | Get team workspaces |
| `twg_twg_atlassian_graph_get_project_context_v2` | Get project context |
| `twg_twg_atlassian_graph_get_context_for_work_item` | Get Jira issue context |
| `atlassian_team_atlassian_team_atlassian_team_search` | Search teams by name |
| `atlassian_team_atlassian_team_atlassian_team_get_team` | Get team details |
| `atlassian_team_atlassian_team_atlassian_team_get_hierarchy` | Get team hierarchy |
| `get_jira_issue` | Fetch issue details with links |
| `search_jira_using_jql` | Query Jira issues |
| `search_confluence_using_cql` | Query Confluence pages |
| TWG CLI `twg teams query` | Search teams (bash) |
| TWG CLI `twg teams get` | Get team by name/ARI (bash) |
| TWG CLI `twg org-tree` | Navigate org hierarchy (bash) |

### 4.2 Cross-Tool Patterns

**Pattern 1: Compass → TWG Team Resolution**
1. Search Compass for component → get `ownerId` (team ARI)
2. Use TWG `get_team_users_v2` with team ARI → get team members
3. Use TWG `get_user_manager_v2` on team lead → get escalation chain

**Pattern 2: Compass → Jira Active Work**
1. Search Compass for component → get component name, labels
2. Search Jira using JQL with component labels → find active issues
3. Use TWG `get_context_for_work_item` → enrich with PRs, branches

**Pattern 3: Jira Dependencies → Compass Ownership**
1. Search Jira for dependency links → get blocking/blocked issues
2. Extract component references from issue labels or Compass links
3. Search Compass for those components → get owner teams
4. Aggregate lead time metrics by team

**Pattern 4: Program → Full Topology**
1. Get project context via TWG → identify teams
2. For each team, get Compass components (via `ownerIds` filter)
3. Build dependency graph across all components
4. Resolve team hierarchy via `get_hierarchy`
5. Get team workspaces via `get_team_spaces`

### 4.3 Autonomy Levels

| Operation | Autonomy Level | Notes |
|-----------|---------------|-------|
| Component search (Compass) | **Fully Autonomous** | Read-only catalog lookup |
| Dependency graph traversal | **Fully Autonomous** | Read-only graph traversal |
| Team/people resolution (TWG) | **Fully Autonomous** | Read-only identity queries |
| Jira issue search | **Fully Autonomous** | Read-only issue queries |
| Confluence search | **Fully Autonomous** | Read-only content search |
| Org hierarchy traversal | **Fully Autonomous** | Read-only org data |
| Impact analysis computation | **Fully Autonomous** | Computation on fetched data |
| Lead time computation | **Fully Autonomous** | Computation on fetched data |
| Sending Slack notifications | **Requires Confirmation** | Outbound communication |
| Modifying Compass components | **Requires Confirmation** | Write operation |
| Creating/updating Jira issues | **Requires Confirmation** | Write operation |
| Depth traversal > 2 hops | **Requires Confirmation** | May produce very large graphs |
| Classifying change as GLOBAL | **Requires Confirmation** | Has policy implications |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

**The AI TPM MUST NOT autonomously:**
- Modify Compass component metadata, dependencies, or ownership
- Send notifications to teams or individuals without user confirmation
- Create or update Jira issues (including comments) without confirmation
- Make SLA commitments or label teams as "outliers" in reports
- Classify a change as GLOBAL (which carries policy implications) without confirmation
- Traverse dependency graphs beyond depth 3 without confirmation (risk of excessive API calls)
- Exceed 500 nodes in a single graph traversal (implement hard safety limit)
- Access or display PII beyond what's needed for escalation routing

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| Compass search returns 0 results | Ask user to clarify component name or provide Compass URL |
| Multiple ambiguous component matches | Present top 5 matches with metadata, ask user to select |
| Team ARI from Compass doesn't resolve in TWG | Flag as "team not found in TWG" — may indicate stale data |
| Dependency graph exceeds 100 nodes at depth 2 | Warn user and ask whether to continue or apply filters |
| On-call data missing for Tier 0-1 service | Flag prominently in output as a risk |
| Owner team != JSM responder team | Flag mismatch for human investigation |
| Negative lead time detected on > 25% of dependencies | Flag as critical program risk, suggest immediate team sync |
| Tool call returns 403/401 | Report permission issue, suggest checking access scopes |

### 5.3 Error Handling

| Error | Handling |
|-------|----------|
| Compass MCP session error | Retry once after 5 seconds. If persistent, report "Compass is temporarily unavailable" and suggest retrying later |
| TWG API 403 Forbidden | Report "Insufficient permissions for TWG query" — user may need to request access |
| Jira search returns no results | Verify JQL syntax, broaden search, or ask user to check project key |
| Team ARI format mismatch | Validate ARI format (`ari:cloud:identity::team/<uuid>`). If invalid, attempt name-based search via `atlassian_team_search` |
| Rate limiting (429) | Implement exponential backoff: wait 2s, 4s, 8s. Max 3 retries |
| Graph cycle detected | Skip already-visited nodes (tracked via `visited` set). Report cycles in output |
| Missing date fields for lead time | Mark dependency as "date-incomplete", include in report but exclude from aggregate stats |
| Component has no ownerId | Report as "unowned component" — flag for governance review |
| Large result sets (>100 items) | Paginate and summarize. Ask user if they want full details |
