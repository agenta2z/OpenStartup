---
name: ai-tpm-risk-dependency-review
description: >
  Guides the AI Technical Program Manager through SOP 2: AI Program Risk & Dependency Review.
  Covers signal aggregation from Jira/Atlas/Confluence, RAID register maintenance with structured
  risk statements and 5x5 scoring, dependency graph refresh with critical path analysis, weekly
  risk delta reporting, review facilitation, and tiered escalation. Leverages TWG CLI, Jira MCP,
  Confluence MCP, Atlas MCP, and Slack tools with clear autonomy boundaries.
labels:
  - ai-tpm
  - risk-management
  - dependency-tracking
metadata:
  requires:
    env: [TWG_USER, TWG_SITE, TWG_TOKEN, TWG_BBC_TOKEN, SLACK_BOT_TOKEN]
  tools:
    - twg
    - slack_send_message
    - confirmation
    - single_choice
---

# AI TPM SOP 2 — AI Program Risk & Dependency Review

## 1. Skill Overview

- **Name**: ai-tpm-risk-dependency-review
- **Description**: Operational guidance for executing SOP 2 of the AI Technical Program Manager role — a recurring (weekly) review cycle that aggregates risk and dependency signals across an AI program, maintains a RAID register, performs dependency graph analysis, generates risk delta reports, facilitates review meetings, and manages escalations.
- **Leveraged Tools**:
  - **twg** — Teamwork Graph CLI for Jira workitem CRUD, Confluence page read/create/update (ADF), Atlas projects/goals queries, dependency context perimeter analysis, user/team resolution, and cross-product work queries
  - **slack_send_message** — Post review summaries, escalation messages, and action item notifications to Slack channels
  - **confirmation** — Request human confirmation before write operations, risk acceptance, and escalation decisions
  - **single_choice** — Present options to the user (e.g., select escalation channel, choose mitigation strategy)

## 2. Workflow Mappings

### 2.1 Weekly Risk & Dependency Review Cycle (Primary Workflow)

**Trigger**: Weekly cadence (e.g., every Monday) or on-demand when risk landscape changes materially.

#### Step 1: Signal Aggregation (🟢 Autonomous)

Collect risk and dependency signals from multiple sources.

**1a. Jira Dependency Scan**


**1b. Dependency Context Perimeter (for key epics)**

Parse response for: linked issues (blocks/is-blocked-by), related PRs, parent hierarchy, cross-project links.

**1c. Atlas Project Status Scan**


**1d. Confluence RAID Register Lookup**


**1e. Duplicate Work Detection**


**Decision point**: If any data source returns empty, apply the **surface pivot pattern** — try alternative surfaces (federated → native → projection → Cypher) before concluding data is unavailable. Do NOT retry the same empty surface.

#### Step 2: Risk Delta Computation (🟢 Autonomous)

Compare current signals against previous RAID register snapshot.

**2a. Load Previous Snapshot**


**2b. Compute Deltas**
For each risk in current state vs previous snapshot:
- **New risks**: Present in current signals, absent in previous snapshot
- **Resolved risks**: Present in previous snapshot, now resolved/closed in Jira or marked resolved
- **Changed risks**: Material changes in any of:
  - Likelihood or Impact changed by ≥1 level
  - Combined rating changed (e.g., Medium → High)
  - Status changed (e.g., Investigating → Blocked)
  - Due date slipped by >7 days
  - Owner changed
  - Mitigation status changed

**2c. Generate Delta Summary**
Produce structured output:


#### Step 3: RAID Register Update (🟡 Confirm Before Write)

**3a. Draft Updated Register**
For each new risk detected, create a structured entry:
- **Risk ID**: Auto-generated (R-NNN)
- **Title**: Short, impact-focused name
- **Risk Statement**: If–Then–Because format:
  > If [cause/event/condition], then [impact on objective], because [driver/mechanism].
- **Category**: One of: Model Quality & Safety | Data & Privacy | Infra, Performance & Cost | Vendor & Third-Party | Governance & Compliance | GTM, Customer & Product Outcomes
- **Likelihood (1-5)**: Rare / Unlikely / Possible / Likely / Almost Certain
- **Impact (1-5)**: Insignificant / Low / Medium / High / Critical
- **Score**: Likelihood × Impact
- **Rating**: Insignificant (1) / Low (2-4) / Medium (5-9) / High (10-16) / Critical (17-25)
- **Status**: Identified / Assessed / In Mitigation / Accepted / Mitigated / Closed
- **Response**: Accept / Avoid / Reduce / Transfer / Watch
- **Owner**: Named individual
- **Mitigation Plan**: Linked actions and narrative
- **Due Date**: Target remediation date

**3b. Score Validation**
- Auto-calculate Score = Likelihood × Impact
- Map to Rating using 5×5 matrix thresholds
- For **High (10-16)**: Flag as requiring treatment plan
- For **Critical (17-25)**: Flag as requiring executive acceptance; DO NOT mark as "Accepted" autonomously

**3c. Confirm and Write**


On confirmation, update Confluence page:


#### Step 4: Dependency Graph Refresh (🟢 Autonomous Analysis, 🟡 Confirm Escalations)

**4a. Build Dependency Graph**
Aggregate all linked issues and dependency records from Step 1. For each dependency:
- Normalize to schema: ID, Title, Type (Inbound/Outbound), Requesting Team, Responding Team, Needed-By Date, Committed-By Date, Status, Risk Level, Blocker State
- Compute slack: (Committed-By Date) − (Needed-By Date)

**4b. Critical Path Analysis**
Identify:
- Dependencies with zero or negative slack (critical path)
- Dependencies where provider is At Risk or Missed
- Teams with inbound dependency count exceeding threshold (WIP overload)
- Dependencies with unestimated underlying work items

**4c. Generate Top-N At-Risk Dependencies**


**4d. Escalation Decision**
For each at-risk dependency:
- **Tier 1 (Auto-handle)**: Slack ≥ 5 days, provider on-track → Log and monitor
- **Tier 2 (Confirm)**: Slack < 5 days OR provider at-risk → Propose action via confirmation tool
- **Tier 3 (Escalate)**: Slack negative AND critical path AND no mitigation → Draft escalation message for human review

#### Step 5: Archive Weekly Snapshot (🟡 Confirm Before Write)

**5a. Create Snapshot Child Page**

Snapshot content includes: full RAID register state, risk delta summary, dependency health summary, active High/Critical counts.

#### Step 6: Review Facilitation (🟡 Confirm Before Send)

**6a. Generate Review Agenda**
Compile from Steps 2-4:
- Risk delta highlights (new/changed/resolved)
- Top at-risk dependencies
- Decisions needed this week
- Action items from previous review

**6b. Post to Slack**


**6c. Create Action Items in Jira**
For each agreed action from the review:


#### Step 7: Escalation Routing (Tiered)

Apply the tiered escalation model:

| Criterion | Tier 1 (Auto) | Tier 2 (Confirm) | Tier 3 (Escalate) |
|-----------|---------------|-------------------|---------------------|
| Risk Rating | Low/Medium | High | Critical |
| Dependency Slack | ≥5 days | 1-4 days | ≤0 days on critical path |
| Duration Blocked | <2 days | 2-5 days | >5 days |
| Decision Ownership | Within team | Cross-team | Cross-org / exec |
| Ambiguity | Clear playbook | Some judgment needed | No clear next steps |

**Tier 3 Escalation Message Template**:


### 2.2 First-Run Initialization Workflow

**Trigger**: RAID register page does not exist for the program.

1. Search Confluence for existing RAID pages: 
2. If not found, create initial RAID register page using ADF template (see Reference Section 5.1)
3. Populate with initial risk brainstorm from Jira signals
4. Score all initial risks using 5×5 matrix
5. Confirm with user before creating page

### 2.3 Ad-Hoc Risk Intake Workflow

**Trigger**: User reports a new risk outside the weekly cycle.

1. Parse free-form input into structured risk fields
2. Generate If–Then–Because statement from description
3. Suggest category based on keyword matching (see Reference Section 5.3)
4. Propose Likelihood/Impact scores with rationale
5. Confirm with user
6. Add to RAID register and notify via Slack if High/Critical

---

## 3. Domain Guidance

### 3.1 Risk Statement Templates

**Primary Pattern — If–Then–Because**:
> If [cause/event/condition], then [impact on objective], because [driver/mechanism].

**Example**:
> If we deploy the AI summarization model to 100% of enterprise tenants without production shadow testing, then we risk a spike in critical support tickets and NPS drop for enterprise admins, because the current evaluation set under-samples long documents and we have no on-call playbooks for AI misbehavior.

**Alternative Pattern — Condition–Event–Impact**:
> There is a risk that [event] occurs due to [condition/driver], resulting in [impact on objectives].

**Validation Rules**:
-  MUST contain a condition or timeframe
-  MUST reference an objective (timeline, OKR, SLA, safety KPI)
-  MUST reference drivers (e.g., "limited eval coverage", "3rd-party SLA")
- REJECT statements that only describe cause OR only impact with no causal chain

### 3.2 Risk Scoring Quick Reference

**5×5 Matrix (Default)**:

| | Impact 1 (Insignificant) | Impact 2 (Low) | Impact 3 (Medium) | Impact 4 (High) | Impact 5 (Critical) |
|---|---|---|---|---|---|
| **Likelihood 5 (Almost Certain)** | 5 Med | 10 High | 15 High | 20 Crit | 25 Crit |
| **Likelihood 4 (Likely)** | 4 Low | 8 Med | 12 High | 16 High | 20 Crit |
| **Likelihood 3 (Possible)** | 3 Low | 6 Med | 9 Med | 12 High | 15 High |
| **Likelihood 2 (Unlikely)** | 2 Low | 4 Low | 6 Med | 8 Med | 10 High |
| **Likelihood 1 (Rare)** | 1 Insig | 2 Low | 3 Low | 4 Low | 5 Med |

**Rating Bands**: 1 = Insignificant | 2-4 = Low | 5-9 = Medium | 10-16 = High | 17-25 = Critical

**Acceptance Rules**:
- **Insignificant/Low (0-4)**: Accepted by Risk Owner; monitor only
- **Medium (5-9)**: Treatment plan recommended; Risk Owner can accept
- **High (10-16)**: Treatment plan required; must be accepted by Risk Group Owner
- **Critical (17-25)**: Must be treated or accepted by Accountable Executive; AI MUST NOT accept autonomously

### 3.3 Lightweight 3×3 Mode (Workshop/Brainstorm)

For early-stage risk capture, use simplified scoring:
- Likelihood: Low (1) / Medium (2) / High (3)
- Impact: Low (1) / Medium (2) / High (3)
- Bands: 1-3 = Low | 4-6 = Medium | 7-9 = High

When upgrading from 3×3 to 5×5: Low→1-2, Medium→3, High→4-5. Require human confirmation.

### 3.4 Mitigation Strategy Options

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Avoid** | Eliminate the risk by removing the cause | Risk is unacceptable and cause is controllable |
| **Reduce** | Lower likelihood or impact through controls | Most common; specific actions reduce exposure |
| **Transfer** | Shift impact to third party (insurance, vendor SLA) | Financial or operational risk with available transfer mechanism |
| **Accept** | Acknowledge and monitor without active treatment | Low residual risk within appetite; cost of treatment exceeds benefit |
| **Watch** | Monitor with defined triggers for re-evaluation | Uncertain risks that may materialize later |

For each mitigation, document: Description | Impact on Risk | Benefits | Drawbacks | Linked Actions

### 3.5 Dependency Health Terminology

- **Slack**: Time between committed-by date and needed-by date. Negative = overdue.
- **Critical Path**: Dependency chain where delay in any node shifts a key milestone.
- **WIP Overload**: Team has more inbound dependencies than capacity allows.
- **Blocker State**: Not Blocking / Soft Blocker / Hard Blocker.
- **Commitment State**: Proposed / Committed / At Risk / Missed.

### 3.6 Cadence Patterns

| Activity | Frequency | Description |
|----------|-----------|-------------|
| Full Risk & Dependency Review | Weekly | Complete SOP 2 execution |
| Risk Delta Snapshot | Weekly | Archived after each review |
| RAID Register Update | Weekly + ad-hoc | After review and on new risk intake |
| Dependency Graph Refresh | Daily (lightweight) / Weekly (full) | Daily: check critical path items. Weekly: full graph rebuild |
| Escalation Check | Daily | Scan for overdue actions and breached thresholds |
| Quarterly Risk Appetite Review | Quarterly | Review and adjust risk appetite thresholds |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
| **twg** | , , , , , , , , , ,  |
| **slack_send_message** | Post review summaries, escalation messages, action item notifications |
| **confirmation** | Confirm RAID register writes, risk acceptance (High/Critical), escalation sends, snapshot creation |
| **single_choice** | Select escalation channel, choose mitigation strategy, select risk category |

### 4.2 MCP Tools Referenced

| MCP Toolset | Tool | Purpose |
|-------------|------|---------|
| **atlassian** |  | Structured Jira queries for blockers, WIP, missing estimates |
| **atlassian** |  | Detailed issue data with transitions and links |
| **atlassian** |  | Find RAID register and snapshot pages |
| **atlassian** |  | Read page content for delta comparison |
| **atlassian** |  | Create snapshot child pages |
| **atlassian** |  | Update RAID register |
| **atlassian_project** |  | Find at-risk/off-track Atlas projects |
| **atlassian_project** |  | Cross-project dependency graph |
| **atlassian_project** |  | Unresolved project risks |
| **atlassian_project** |  | Status narratives and RAG changes |
| **teamwork_graph** |  | Issue perimeter with PRs, commits, hierarchy |
| **teamwork_graph** |  | Duplicate work detection via semantic similarity |
| **teamwork_graph** |  | Code-level dependency identification |
| **teamwork_graph** |  | Team WIP detection |

### 4.3 Cross-Tool Patterns

**Pattern 1: Signal → Register → Report**
1. Query Jira via  → collect blocking issues
2. Query Atlas via  → collect project dependencies
3. Read RAID register via  → load current state
4. Compute deltas locally → generate structured diff
5. Update register via  → persist changes
6. Post summary via  → notify stakeholders

**Pattern 2: Detect → Score → Escalate**
1. Detect new risk signal from Jira/Atlas data
2. Generate If–Then–Because statement
3. Score using 5×5 matrix
4. If High/Critical → use  tool → on confirm →  to escalation channel

**Pattern 3: Dependency Scan → Graph → Critical Path**
1.  → get dependency perimeter
2.  → get blocker details
3.  → get Atlas-level dependencies
4. Build internal dependency graph → compute slack and critical path
5. Flag at-risk dependencies → propose escalations via 

### 4.4 Autonomy Levels

| Operation | Level | Notes |
|-----------|-------|-------|
| Read Jira issues, search JQL | 🟢 Fully Autonomous | All read operations |
| Read Confluence pages, CQL search | 🟢 Fully Autonomous | |
| Read Atlas projects, dependencies, risks | 🟢 Fully Autonomous | |
| TWG context/work queries | 🟢 Fully Autonomous | |
| Compute risk scores and deltas | 🟢 Fully Autonomous | Math operations |
| Draft risk statements and reports | 🟢 Fully Autonomous | Drafting only |
| Update RAID register (Confluence write) | 🟡 Confirm First | Show changes before writing |
| Create snapshot pages | 🟡 Confirm First | Show content summary |
| Create Jira action items | 🟡 Confirm First | Show issue details |
| Post Slack messages | 🟡 Confirm First | Show message content and target |
| Accept High/Critical risks | 🔴 Human Required | AI MUST NOT accept autonomously |
| Transition Jira issue status | 🔴 Human Required | Status changes need explicit approval |
| Mark dependency as "Missed" | 🔴 Human Required | Impacts cross-team accountability |

---

## 5. Reference Tables

### 5.1 RAID Register ADF Field Mapping

| Field | ADF Cell Type | Notes |
|-------|---------------|-------|
| Risk ID | Plain text (R-NNN) | Auto-incremented |
| Title | Plain text | Short, impact-focused |
| Risk Statement | Paragraph with If/Then/Because | Structured narrative |
| Category | Status lozenge (colored) | Maps to 6 AI categories |
| Likelihood | Number (1-5) | With descriptor text |
| Impact | Number (1-5) | With descriptor text |
| Score | Number (calculated) | L × I |
| Rating | Status lozenge | Color-coded: green/yellow/orange/red |
| Status | Status lozenge | Lifecycle status |
| Response | Plain text | Accept/Avoid/Reduce/Transfer/Watch |
| Owner | Mention (@user) | Named individual |
| Mitigation Plan | Rich text with links | Linked Jira issues |
| Due Date | Date | Target remediation |
| Last Updated | Date | Auto-set on change |

### 5.2 Category Auto-Detection Keywords

| Category | Trigger Keywords |
|----------|-----------------|
| Model Quality & Safety | bias, fairness, hallucination, drift, accuracy, robustness, adversarial, jailbreak, safety, harmful output |
| Data & Privacy | PII, data leak, training data, telemetry, retention, GDPR, data residency, logging |
| Infra, Performance & Cost | GPU, token, compute, latency, SLO, capacity, scaling, cost overrun, quota |
| Vendor & Third-Party | OpenAI, Anthropic, AWS, vendor, SLA, outage, plugin, third-party, API limit |
| Governance & Compliance | DPIA, AI Act, ISO42001, documentation, risk assessment, intake, policy, audit |
| GTM, Customer & Product | NPS, support volume, customer harm, reputation, launch, adoption, change management |

### 5.3 JQL Patterns for Dependency Scanning



### 5.4 CQL Patterns for Confluence



---

## 6. Guardrails and Escalation

### 6.1 Safety Boundaries — What NOT To Do Autonomously

- **NEVER** mark a Critical or High risk as "Accepted" without explicit human approval
- **NEVER** close a risk that still has a residual score ≥ Medium without confirmation
- **NEVER** transition Jira issue status without human approval
- **NEVER** send escalation Slack messages to executive channels without confirmation
- **NEVER** delete or overwrite RAID register content without showing a diff first
- **NEVER** mark a dependency as "Missed" — this impacts cross-team accountability
- **NEVER** modify risk scores downward for High/Critical risks without human review
- **NEVER** auto-accept risks above configured appetite threshold

### 6.2 Escalation Triggers

| Trigger | Action |
|---------|--------|
| New Critical risk detected (score 17-25) | Immediately flag to user; draft Tier 3 escalation |
| Risk rating increased to High or Critical | Confirm with user; draft escalation if no mitigation plan |
| Dependency slack ≤ 0 on critical path | Flag as Tier 2 minimum; Tier 3 if blocked >2 days |
| 3+ High risks in same category | Pattern alert — suggest systemic review |
| Mitigation action overdue >7 days | Notify risk owner; escalate to Tier 2 if >14 days |
| Team WIP exceeds threshold | Alert team lead; suggest scope/sequencing review |
| Risk owner unresponsive >2 review cycles | Escalate to their manager via Slack |

### 6.3 Error Handling

| Error Scenario | Recovery Action |
|----------------|-----------------|
| TWG command returns empty/error | Apply surface pivot pattern: try alternative surface family. If all surfaces fail, log gap and continue with available data |
| Confluence page not found (first run) | Trigger First-Run Initialization workflow (Section 2.2) |
| RAID register ADF parse fails | Fall back to Confluence MCP  (HTML format); parse HTML instead |
| Jira JQL returns 0 results | Verify project key and status names via ; retry with corrected JQL |
| Slack send fails | Retry once; if still fails, log error and present message content to user for manual posting |
| Atlas project search returns empty | Broaden search (remove status filter); if still empty, skip Atlas layer and note in report |
| Snapshot child page creation fails | Try creating as sibling page instead; if still fails, embed snapshot in RAID register page body |
| Risk score calculation produces unexpected value | Validate L and I are in 1-5 range; recalculate; if inputs invalid, ask user to re-score |

### 6.4 Audit Trail

All write operations MUST be logged with:
- **Timestamp**: ISO 8601 format
- **Operation**: What was changed (risk created/updated/resolved, dependency status changed, escalation sent)
- **Before/After**: For updates, capture previous and new values
- **Actor**: "AI TPM Agent" for autonomous actions; user identity for confirmed actions
- **Rationale**: Why the change was made (e.g., "Score increased due to dependency slack reducing to -2 days")

Append audit entries as dated notes in the RAID register and/or as Jira comments on affected issues.
