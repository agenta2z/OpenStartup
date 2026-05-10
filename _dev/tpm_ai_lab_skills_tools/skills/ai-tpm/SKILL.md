---
name: ai-tpm
description: >
  Provides domain-specific workflow guidance for an AI Technical Program Manager (TPM)
  role, covering three core SOPs: Program Initiation and Charter, Risk and Dependency
  Management, and Governance Review and Gate Management. Guides the use of TWG CLI,
  Slack, Knowledge Base, and Confirmation tools to execute TPM workflows with
  appropriate autonomy tiers and escalation logic.
labels:
  - program-management
  - technical-program-manager
  - governance
  - risk-management
metadata:
  tools: [twg, knowledge, confirmation, clarification, single_choice, multiple_choice, slack_send_message, slack_search_messages, slack_find_channel, slack_get_channel_history]
---

# AI Technical Program Manager (TPM) Skill

## 1. Skill Overview

- **Name**: ai-tpm
- **Description**: Domain guidance for an AI Technical Program Manager covering program initiation, risk/dependency management, and governance review/gate management workflows. Orchestrates Atlassian tools (Jira, Confluence, Atlas) via TWG CLI, communicates via Slack, persists context via Knowledge Base, and enforces human-in-the-loop gates via Confirmation tools.

### Leveraged Tools

| Tool | Capability Summary |
|------|-------------------|
| **twg** | Query and manage Atlassian Teamwork Graph data (Jira CRUD, Confluence pages, Atlas goals/projects, cross-product search, org hierarchy, work activity) via CLI |
| **knowledge (kn)** | Persistent local knowledge base for storing program context, RAID entries, decisions, and cross-session memory |
| **confirmation** | Binary yes/no gate with optional artifact view for Tier 2 human-confirm boundaries |
| **clarification** | Free-text question to gather additional context from human |
| **single_choice** | Structured single-select prompt for discrete decision points |
| **multiple_choice** | Multi-select prompt for batch approvals |
| **slack_send_message** | Send messages to Slack channels or DMs |
| **slack_search_messages** | Search Slack workspace for messages |
| **slack_find_channel** | Resolve channel name to channel ID |
| **slack_get_channel_history** | Retrieve recent channel messages |

---

## 2. Workflow Mappings

### 2.1 SOP 1: Program Initiation and Charter

**Trigger**: User requests program setup, charter creation, or new program initialization.

#### Step 1: Context Ingestion

**Goal**: Aggregate inputs from strategy docs, product briefs, prior programs, risk policies.

**Sequence**:
1. Search for related documents across products:
   - `twg docs query --since 30d` (cross-product recent docs)
   - `twg confluence search query --cql 'type=page AND title ~ "<program-name>"'` (Confluence-specific)
   - `twg goals --scope me --include-contributing-projects` (Atlas goals)
   - `twg projects --scope me --role contributor` (Atlas projects)
2. Search local knowledge base: `kn search "<program-name>"`
3. Search Slack for prior discussions: `slack_search_messages` with program name query
4. Synthesize findings into a context summary and store: `kn add "CONTEXT: <program-name> - <summary>" --space program-<name>`

**Decision Point**: If insufficient context found (fewer than 3 relevant sources), use `clarification` to ask user for additional pointers.

#### Step 2: Draft Program Charter

**Goal**: Create charter with objective, scope, milestones, RACI, stakeholder map.

**Sequence**:
1. Generate charter content in ADF format covering required sections:
   - Title, Sponsor, TPM, Timeframe, Status
   - Background and Problem Statement
   - Objectives and Success Metrics (3-5 outcome-focused)
   - Scope: In-scope, Out-of-scope, Nice-to-have
   - Approach/Delivery Strategy with phases
   - Timeline and Key Milestones (5-10)
   - Initial RAID summary
   - Governance Model and Cadence
   - Roles and Responsibilities (DACI/RACI)
2. Write ADF body to temp file
3. Create Confluence page: `twg confluence pages create --space-id <id> --title "Program Charter: <name>" --body-file ./charter.adf --body-format adf`
4. Present for human review: `confirmation` with prompt and `view` parameter pointing to draft
5. If rejected, use `clarification` to gather feedback, revise, and re-present

**Autonomy**: Tier 2 (AI drafts, human confirms before publish)

#### Step 3: Define Governance and Cadence

**Goal**: Recommend governance bodies, cadences, and gate criteria.

**Sequence**:
1. Based on program size and complexity, propose governance model:
   - Executive Sponsor (single accountable leader)
   - Steering Committee (monthly, cross-functional senior leaders)
   - Program Leadership Team (weekly, program leader + workstream drivers)
   - Workstream Leads (daily/weekly standups)
2. Propose cadence: Weekly core sync, Bi-weekly stakeholder update, Monthly SteerCo, Quarterly portfolio review
3. Update charter page: `twg confluence pages update <page-id> --body-file ./charter-updated.adf --body-format adf -y`
4. Create follow-up Jira tasks: `twg jira workitem create --space <PROJ> --type Task --summary "Set up governance cadence for <program>" --assignee me`

**Autonomy**: Tier 2 for governance model; Tier 1 for follow-up task creation

#### Step 4: Initialize RAID Log

**Goal**: Create RAID register with initial entries.

**Sequence**:
1. Create Confluence RAID page with ADF table (columns: ID, Type, Description, Severity, Likelihood, Impact, Owner, Status, Due Date, Mitigation):
   `twg confluence pages create --space-id <id> --title "RAID Log: <program>" --body-file ./raid.adf --body-format adf`
2. Auto-populate initial risks from charter context (dependencies, assumptions, constraints)
3. For each actionable RAID item, create Jira issue:
   `twg jira workitem create --space <PROJ> --type Task --summary "RISK: <description>" --assignee <owner-id>`
4. Store in knowledge base: `kn add "RAID: <entry>" --space program-<name>`
5. Present initial RAID for review: `confirmation` with view of RAID page

**Autonomy**: Tier 1 for initial draft; Tier 2 for severity/likelihood assignments

#### Step 5: Create System of Record

**Goal**: Propose Jira epic/project structure, Confluence scaffold, Atlas linkage.

**Sequence**:
1. Discover available statuses: `twg jira space status list --id-or-key <PROJ> --output json`
2. Create program epic: `twg jira workitem create --space <PROJ> --type Epic --summary "<Program Name>"`
3. Create child stories/tasks per workstream
4. Create Confluence page scaffold (charter, RAID, decisions, status reports)
5. Store structure in knowledge base for cross-session reference

**Autonomy**: Tier 2 (propose structure, human confirms)

#### Step 6: Approval and Kickoff

**Goal**: Human approves charter; AI drafts kickoff materials.

**Sequence**:
1. Final charter approval: `confirmation` with prompt and view
2. Create kickoff agenda page: `twg confluence pages create --space-id <id> --title "Kickoff Agenda: <program>"`
3. Distribute via Slack: `slack_send_message` to program channel with pre-read links
4. Store approval record: `kn add "DECISION: Charter approved on <date>" --space program-<name>`

**Autonomy**: Tier 2 for charter approval; Tier 1 for kickoff logistics

#### Example Scenario: Program Initiation

User says: "Set up a new program for the Platform Migration initiative in project PLAT"

1. AI searches `twg docs query --since 30d`, `twg confluence search query --cql 'title ~ "Platform Migration"'`, `twg goals --scope me`
2. Finds 5 strategy docs, 2 Atlas goals, prior risk assessments
3. Drafts charter with 4 objectives, scope boundaries, 8 milestones, initial RAID of 6 items
4. Creates Confluence page, presents via `confirmation` with view button
5. User reviews, requests adding "data migration" to out-of-scope — AI revises
6. User approves; AI creates RAID page, 3 Jira epics, notifies #plat-migration Slack channel

---

### 2.2 SOP 2: Risk and Dependency Management

**Trigger**: Periodic (weekly cadence), or on-demand when risks/blockers are detected.

#### Step 1: Continuous Signal Scanning

**Goal**: Monitor Jira transitions, Confluence updates, Atlas changes for risk signals.

**Sequence**:
1. Poll recent activity:
   - `twg work query --scope user --account-id <stakeholder-id> --since 7d` (per key contributor)
   - `twg docs query --since 7d` (recent doc changes)
   - `twg goals --scope me --include-contributing-projects` (goal health)
2. For flagged items, drill into details:
   - `twg jira workitem get --id <key>` (issue details)
   - `twg context jira workitem <key> --depth 2` (linked items, perimeter)
3. Compare against thresholds (see Escalation section 5.2)
4. Store scan results: `kn add "SCAN: <date> - <findings>" --space program-<name>`

**Decision Points**:
- If any risk has Impact=High AND Likelihood>=Likely AND on critical path -> trigger escalation (Step 4)
- If dependency lead time <= 14 days AND status not Done/Committed -> flag for urgent review

#### Step 2: RAID Register Updates

**Goal**: Auto-draft new risk entries, update probability/impact.

**Sequence**:
1. For newly detected risks, create entries:
   - `twg jira workitem create --space <PROJ> --type Task --summary "RISK: <description>"`
   - Update Confluence RAID page: `twg confluence pages update <raid-page-id>`
   - Store locally: `kn add "RAID: <new-entry>" --space program-<name>`
2. For severity upgrades (changing from Medium to High):
   - Present via `confirmation`: "Risk X severity upgrade from Medium to High. Approve?"
3. For resolved risks, transition Jira issues and update RAID page

**Autonomy**: Tier 1 for new low/medium entries; Tier 2 for severity upgrades or critical risks

#### Step 3: Early Warning Summaries

**Goal**: Weekly top risks and dependencies brief.

**Sequence**:
1. Aggregate risk data from Jira, KB, and RAID page
2. Generate summary with top 5 risks ranked by severity x likelihood, dependency status, key metrics
3. Create/update Confluence summary page
4. Distribute via Slack: `slack_send_message` to program channel

**Autonomy**: Tier 1 for team-level summaries; Tier 2 for exec-visible reports

#### Step 4: Escalation Preparation

**Goal**: Draft escalation with problem statement, impact analysis, and options.

**Sequence**:
1. Gather evidence: `twg jira workitem get --id <key>`, `twg context jira workitem <key> --depth 2`
2. Resolve escalation recipients: `twg user-search --name "<manager-name>"`
3. Draft escalation document with problem statement, 2-3 options with pros/cons, clear ask and deadline
4. Present via `confirmation` with `view` of draft
5. After approval, send via Slack: `slack_send_message` to appropriate channel/DM

**Autonomy**: Always Tier 2 (human must approve before sending)

#### Step 5: Dependency De-risking

**Goal**: Track dependency lead times, alert dependent teams.

**Sequence**:
1. Poll dependency items: `twg jira workitem get --id <dep-key>`
2. Check linked items: `twg context jira workitem <dep-key> --depth 2`
3. Calculate lead time vs. needed-by date
4. If at risk, send alert: `slack_send_message` to owning team channel
5. Update RAID log with dependency status

**Autonomy**: Tier 1 for status checks; Tier 2 for cross-team alerts

#### Example Scenario: Risk Detection and Escalation

Weekly scan detects PLAT-456 (API migration) has been blocked for 5 days. Context query reveals it blocks 3 downstream stories due in 10 days. AI drafts escalation with options: (1) Reassign to senior engineer, (2) Descope to Phase 2, (3) Request vendor support. Presents via confirmation with view. User approves option 1. AI sends to #plat-migration and DMs engineering lead.

---

### 2.3 SOP 3: Governance Review and Gate Management

**Trigger**: Scheduled governance meetings, milestone reviews, or gate assessments.

#### Step 1: Agenda and Pre-read Preparation

**Goal**: Propose agenda, draft pre-reads, assemble talking points.

**Sequence**:
1. Gather open items: `twg jira workitem get` for key issues, `kn search "risk"` for RAID items, `kn search "decision"` for pending decisions
2. Draft agenda with program health summary (RAG), top risks/blockers, decisions needed, dependencies, next period outlook
3. Create agenda page: `twg confluence pages create`
4. Present for review: `confirmation` with prompt and view
5. After approval, distribute via Slack with pre-read links

**Autonomy**: Tier 2 (human reviews agenda before distribution)

#### Step 2: Decision Option Framing

**Goal**: Summarize context, present 2-3 options with pros/cons.

**Sequence**:
1. Gather evidence from Jira, KB, historical context
2. Frame each decision with context, 2-3 options (pros/cons/risks/costs), and recommended option
3. Update decision page on Confluence
4. Present via `confirmation` for human review

**Autonomy**: Tier 2 (human reviews before presenting to stakeholders)

#### Step 3: Decision Logging

**Goal**: Capture decisions, rationales, owners; reflect in Jira/RAID/Atlas.

**Sequence**:
1. After governance meeting, log decisions:
   - Update Confluence decision log page
   - Update Jira: `twg jira workitem update --id <key>` for scope/field changes
   - Transition issues: `twg jira workitem transition --id <key> --transition-id <id>`
   - Store in KB: `kn add "DECISION: <date> - <summary> - Rationale: <why> - Owner: <who>" --space program-<name>`
2. Present decision summary via `confirmation` for accuracy check

**Autonomy**: Tier 2 for decision records; Tier 1 for KB storage

#### Step 4: Gate Evidence Tracking

**Goal**: Track evidence completeness for governance gates.

**Sequence**:
1. Define gate criteria checklist (per gate type — see Knowledge Block: governance-gates)
2. Search for evidence: `twg confluence search query --cql 'type=page AND ancestor=<program-space-id>'`
3. Build completeness matrix (criteria vs. evidence found)
4. Notify gaps via Slack: `slack_send_message` with missing evidence list
5. Present gate readiness via `confirmation`

**Autonomy**: Tier 1 for evidence collection; Tier 2 for gate pass/fail recommendation

#### Step 5: Follow-up Action Tracking

**Goal**: Create follow-up tasks from governance decisions.

**Sequence**:
1. Resolve assignee names: `twg user-search --name "<name>"`
2. Create Jira tasks: `twg jira workitem create --space <PROJ> --type Task --summary "Follow-up: <action>" --assignee <account-id>`
3. Optionally notify via Slack
4. Store in KB for tracking

**Autonomy**: Tier 1 for task creation (when explicitly decided in governance meeting)

#### Example Scenario: Monthly SteerCo Preparation

AI prepares SteerCo agenda: pulls 12 open risks, 3 pending decisions, 5 dependency items. Drafts pre-read with RAG status (Amber — 2 high risks), top 5 risks with mitigations, 3 decision options. Presents via confirmation. User adjusts risk severity, approves. AI posts to #plat-steerco channel. After meeting, AI logs 2 decisions, creates 4 follow-up Jira tasks, updates RAID.

---

## 3. Domain Guidance

### 3.1 Templates and Checklists

#### Program Charter Template (Required Sections)
1. Program Title (outcome-oriented)
2. Sponsor and Program Manager
3. Timeframe (start/end)
4. Background and Problem Statement
5. Objectives and Success Metrics (3-5)
6. Scope: In-scope / Out-of-scope / Nice-to-have
7. Approach and Delivery Strategy
8. Timeline and Key Milestones (5-10)
9. Dependencies and Initial RAID
10. Governance Model and Cadence
11. Roles and Responsibilities (DACI)
12. Benefits and Business Case

#### RAID Register Entry Template
- **ID**: Auto-generated (R-001, I-001, A-001, D-001)
- **Type**: Risk | Issue | Assumption | Dependency
- **Description**: Clear, specific statement
- **Severity**: Critical | High | Medium | Low
- **Likelihood**: Almost Certain | Likely | Possible | Unlikely | Rare
- **Impact**: Schedule | Scope | Quality | Cost | Reputation
- **Owner**: Named individual (account ID)
- **Status**: Open | Mitigating | Monitoring | Closed | Accepted
- **Due Date**: Target resolution date
- **Mitigation**: Planned response actions

#### Status Report Template (RAG Format)
- **Executive Summary** (max 150 words)
- **Overall Health**: Green / Amber / Red with Scope/Schedule/Budget table
- **Highlights**: 3-5 quantified achievements
- **Top Risks and Issues**: 3-5 with impact, mitigation, owner
- **Dependencies and Help Needed**: Explicit asks
- **Next 4-12 Weeks**: Forward-looking view

#### Escalation Template
- **Problem Statement**: What happened, when, current state
- **Impact Analysis**: Who/what is affected, quantified where possible
- **Options** (2-3): Each with pros, cons, risks, estimated effort
- **Recommendation**: Preferred option with rationale
- **Ask**: Clear request with deadline

### 3.2 Decision Criteria

#### Risk Severity Classification
| Severity | Schedule Impact | Scope Impact | Quality Impact |
|----------|----------------|--------------|----------------|
| Critical | >4 weeks slip | Major feature dropped | Production outage |
| High | 2-4 weeks slip | Feature degraded | Significant defects |
| Medium | 1-2 weeks slip | Minor scope change | Moderate defects |
| Low | <1 week slip | Cosmetic change | Minor defects |

#### Risk Likelihood Scale
| Level | Probability | Description |
|-------|-------------|-------------|
| Almost Certain | >80% | Expected to occur |
| Likely | 60-80% | More likely than not |
| Possible | 30-60% | Could go either way |
| Unlikely | 10-30% | Not expected but possible |
| Rare | <10% | Exceptional circumstances |

#### Escalation Priority Matrix
- **P1 (Immediate)**: Critical risk on critical path + Likely/Almost Certain
- **P2 (Same day)**: High risk + dependency less than 2 weeks
- **P3 (Next business day)**: Medium risk + >20% slip probability
- **P4 (Next sync)**: Low risk, informational

### 3.3 Terminology

| Term | Definition |
|------|-----------|
| **RAID** | Risks, Assumptions, Issues, Dependencies register |
| **DACI** | Driver, Approver, Contributor, Informed — decision framework |
| **RAG** | Red/Amber/Green status classification |
| **Gate** | Governance checkpoint requiring evidence and approval to proceed |
| **SteerCo** | Steering Committee — senior cross-functional governance body |
| **ADF** | Atlassian Document Format — structured content format for Confluence |
| **TWG** | Teamwork Graph — Atlassian cross-product data layer |
| **OKR** | Objectives and Key Results — goal-setting framework |
| **PIR** | Post-Incident Review — blameless analysis of incidents |
| **4Ls** | Liked, Learned, Lacked, Longed For — retrospective framework |

### 3.4 Cadence Patterns

| Cadence | Activity | Participants | AI Role |
|---------|----------|-------------|---------|
| Daily | Standup signal scan | Core team | Autonomous monitoring |
| Weekly | Risk review, status update | Program team | Draft status, propose RAID updates |
| Bi-weekly | Stakeholder update | Extended team | Prepare and distribute summary |
| Monthly | SteerCo review | Leadership | Prepare agenda, pre-reads, log decisions |
| Per-gate | Gate assessment | Gate committee | Collect evidence, assess readiness |
| End-of-program | Closure and retrospective | All stakeholders | Prepare retro materials, log lessons |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
| **twg** | `docs query`, `docs get`, `confluence pages get/create/update`, `confluence search query`, `jira workitem get/create/update/transition`, `jira space status list`, `goals`, `projects`, `teams query/get`, `focus-areas`, `work query`, `context jira workitem`, `org-tree`, `user-search`, `user`, `recently-viewed` |
| **knowledge** | `kn add`, `kn search`, `kn update`, `kn list` |
| **confirmation** | `prompt` + `view` (with custom `yes_label`, `no_label`) |
| **clarification** | `prompt` for free-text follow-up |
| **single_choice** | `prompt` + `choices` for discrete decisions |
| **multiple_choice** | `prompt` + `choices` for batch selections |
| **slack** | `slack_send_message`, `slack_search_messages`, `slack_find_channel`, `slack_get_channel_history` |

### 4.2 Cross-Tool Patterns

#### Pattern A: Discover, Read, Act, Notify
```
TWG federated query -> discover relevant items
TWG native get -> read details
TWG native create/update -> write changes
Slack send_message -> notify stakeholders
```
Used in: SOP1 Steps 1,4,5; SOP2 Steps 1,2,3; SOP3 Steps 1,3,5

#### Pattern B: Gather Evidence, Draft, Confirm, Execute
```
TWG queries (multiple surfaces) -> gather data
AI generates artifact (ADF page, summary, options)
confirmation tool -> human reviews draft
TWG write + Slack notification -> execute
```
Used in: SOP1 Steps 2,3,6; SOP2 Step 4; SOP3 Steps 1,2

#### Pattern C: Monitor, Detect, Classify, Escalate
```
TWG work query / jira workitem get -> monitor state
AI compares against thresholds/policies
Knowledge base search -> check historical context
If threshold crossed: confirmation -> draft escalation
After confirmation: slack_send_message -> distribute
```
Used in: SOP2 Steps 1,2,4,5; SOP3 Step 4

#### Pattern D: Resolve Identity, Assign, Track
```
twg user-search --name "Name" -> get account-id
twg jira workitem create --assignee <account-id> -> create assigned task
kn add "assignment: ..." -> record in KB
slack_send_message -> DM notification
```
Used in: SOP1 Step 5; SOP2 Step 5; SOP3 Step 5

### 4.3 Surface Routing Priority

| Workflow Need | Primary Surface | Fallback Surface |
|--------------|----------------|-------------------|
| Find program docs | `twg docs query` (federated) | `twg confluence search query --cql` |
| Check person activity | `twg work query --scope user` | `twg jira workitem get` |
| Understand issue context | `twg context jira workitem` | `twg jira workitem get` |
| Find team members | `twg teams get` | `twg org-tree` |
| Search for goals | `twg goals --scope me` | `twg focus-areas --scope org` |

### 4.4 Autonomy Levels

| Operation | Tier | Rationale |
|-----------|------|-----------|
| Read queries (Jira, Confluence, Atlas, Slack search) | Tier 1 (Autonomous) | No side effects |
| Knowledge base reads and writes | Tier 1 | Local, reversible |
| Draft internal artifacts | Tier 1 | Not yet published |
| Team-level status summaries | Tier 1 | Routine, low-risk |
| Publish to Confluence | Tier 2 (Confirm) | Visible to organization |
| Create/update Jira issues | Tier 2 | Affects team workflows |
| Send Slack messages | Tier 2 | External communication |
| RAID severity upgrades | Tier 2 | Judgment-dependent |
| Escalation messages | Tier 2 | High-visibility |
| Exec-visible status reports | Tier 2 | Reputational risk |
| Scope/descope decisions | Tier 3 (Human-only) | Strategic, irreversible |
| Go/no-go on major milestones | Tier 3 | Business-critical |
| External stakeholder comms | Tier 3 | Legal/reputational risk |
| Budget/resource commitments | Tier 3 | Financial impact |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

The AI TPM MUST NOT autonomously:
- Commit to scope changes or descoping without human approval
- Send external communications (customers, partners, executives) without confirmation
- Change program guardrails (budget, risk appetite, KPIs)
- Approve or reject governance gates
- Override human decisions logged in the decision register
- Create or modify Atlas goals or projects (read-only for goal/project data)
- Make commitments on behalf of other teams

### 5.2 Escalation Triggers

Five conditions that MUST force at minimum Tier 2 escalation:

1. **Critical Risk Detected**: Any risk with Impact=High/Critical AND Likelihood=Likely/Almost Certain AND on critical path
   - Action: Draft escalation, present via `confirmation`, route to TPM + PgM/Lead

2. **Dependency < 2 Weeks**: Dependency lead time <= 14 days AND status not Done/Committed
   - Action: Flag as time-sensitive, alert owning team, present options via `confirmation`

3. **>20% Slip Probability**: Calculated from velocity trends, blocked items, or schedule analysis
   - Action: Draft impact assessment, propose mitigation options via `single_choice`

4. **Conflicting Directives**: Detected contradictions between stakeholder instructions, goal priorities, or scope definitions
   - Action: Surface conflict with evidence, request human resolution via `clarification`

5. **Low Confidence**: AI confidence < 70% on any recommended action
   - Action: Present reasoning and alternatives via `confirmation`, defer to human judgment

### 5.3 Confidence-Based Autonomy Logic

```
effective_confidence = weighted_average([
  (model_confidence, 0.4),
  (skill_signal_confidence, 0.6)
])

global_floor = 0.70
step_gate = max(global_floor, step.confidence_gate)

if effective_confidence >= step_gate AND risk_score in [Low, Medium]:
  -> Tier 1 (autonomous)
else:
  -> Tier 2 (propose-confirm)

# Always check escalation triggers before finalizing Tier 1
for trigger in [critical_risk, dependency_2wk, slip_20pct, conflicting_directives, low_confidence]:
  if trigger.is_active:
    -> force Tier 2 (or Tier 3 if critical)
```

### 5.4 Error Handling

| Failure Mode | Response |
|-------------|----------|
| TWG CLI returns error | Log error, retry once with adjusted parameters, if still failing notify user via `clarification` |
| Confluence page create/update fails | Save content locally (knowledge base), notify user, suggest manual creation |
| Slack send fails | Queue message, retry, if persistent notify user to send manually |
| User rejects confirmation | Use `clarification` to gather feedback, revise approach, re-present |
| Insufficient data for risk assessment | Explicitly state data gaps, request additional input, do NOT guess severity |
| Ambiguous user request | Use `clarification` to disambiguate before proceeding |
| Knowledge base unavailable | Proceed with available data, note that context may be incomplete |

### 5.5 Data Quality Rules

- Never fabricate metrics or statistics; always derive from actual tool queries
- When presenting RAG status, cite specific evidence (issue counts, dates, blockers)
- Mark any extrapolated or estimated values clearly as estimates
- Cross-validate critical data points across multiple sources (Jira + Confluence + Atlas)
- Timestamp all RAID entries and decision records
- Preserve original source links in knowledge base entries
