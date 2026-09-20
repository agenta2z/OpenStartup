---
name: ai-tpm-program-management
description: >
  Comprehensive domain guidance for an AI Technical Program Manager (AI TPM) role,
  covering program charter auto-assembly, DACI decision log creation, data-driven
  retrospectives, operating cadence design with auto-generated agendas, and change
  management runbook generation for AI/ML systems. Leverages TWG CLI for Jira/Confluence/Atlas
  data, Slack tools for decision harvesting, and the knowledge tool for persistent
  organizational memory.
labels:
  - program-management
  - ai-ml
  - retrospectives
  - change-management
  - decision-frameworks
  - operating-cadence
metadata:
  tools:
    - twg
    - slack_search_messages
    - slack_find_channel
    - slack_send_message
    - slack_get_thread
    - knowledge
---

# AI TPM Program Management Skill

## 1. Skill Overview

- **Name**: `ai-tpm-program-management`
- **Description**: Domain guidance for AI Technical Program Managers covering five core
  workflows: (1) auto-assembling program charters from live Jira/Atlas data, (2) creating
  and maintaining DACI decision logs in Confluence, (3) running data-driven retrospectives
  with automated metric collection, (4) designing operating cadences with auto-generated
  agendas, and (5) generating change management runbooks for AI/ML system changes.
- **Leveraged Tools**:
  - `twg` — Query and manage Jira work items, Atlas goals/projects, Confluence pages,
    teams, org-tree, and cross-product work activity via TWG CLI. Single `command` string parameter.
  - `slack_search_messages` — Search Slack messages using full query syntax (channel, user,
    date filters). Returns message objects with channel, text, permalink, and context.
  - `slack_find_channel` — Resolve Slack channel names to IDs.
  - `slack_send_message` — Post messages, summaries, and notifications to Slack channels.
  - `slack_get_thread` — Retrieve full thread context for a specific Slack message.
  - `knowledge` — Persistent knowledge base with 15 subcommands: add, search, get, update,
    delete, list, spaces, tags, export, import, rollback, history, status, review, migrate.

---

## 2. Workflow Mappings

### 2.1 Workflow: Auto-Assemble Program Charter

**Trigger**: User says "create a program charter", "set up charter for X", "draft a charter
for the AI platform initiative", or a new Atlas project is created that lacks a charter page.

**Step-by-step**:

1. **Gather program identity**
   - Ask user for: program name, sponsoring team/org, target timeframe (FY/quarter).
   - If an Atlas project or Jira epic key is provided, fetch context:
   ```
   twg projects get <project-id>
   twg jira workitem get --id <EPIC-KEY>
   twg context jira workitem <EPIC-KEY> --depth 2
   ```

2. **Auto-populate from systems**
   - **Title & Meta**: Extract from Atlas project name or Jira epic summary.
   - **Sponsor/Owner**: From Atlas project owner or Jira epic reporter.
   - **Timeframe**: From Atlas target dates or epic fix versions.
   - **Goals & Success Metrics**: Pull linked OKRs/KRs:
   ```
   twg goals get <goal-id>
   ```
   - **Stakeholders**: Extract from Atlas team members and Jira assignees:
   ```
   twg teams get <team-id>
   twg work query --scope user --account-id <id> --since 90d
   ```

3. **Generate scope from Jira structure**
   - List child epics/stories under the program:
   ```
   twg context jira workitem <EPIC-KEY> --depth 2
   ```
   - Group by component or label → propose In-Scope deliverables.
   - Ask user to confirm Out-of-Scope items.

4. **Draft milestones**
   - Extract target dates from Jira epics/versions.
   - Propose 5-10 milestones with definitions of done.

5. **Generate risks section**
   - Search for existing risk discussions:
   ```
   slack_search_messages "risk OR blocker in:#<program-channel> after:<start-date>" --count 30
   ```
   - Search knowledge base for historical patterns:
   ```
   kn search "risks <program-domain>" --space risk-patterns --limit 5
   ```

6. **Draft operating model**
   - Propose default cadences based on team size and criticality (see Section 2.4).
   - Include decision-making approach (DACI reference).

7. **Create Confluence page**
   ```
   twg confluence page create --space <SPACE> --parent <PARENT-PAGE-ID> --title "Program Charter: <Name>" --body-adf <charter-adf>
   ```
   Use the Program Charter ADF template (see knowledge block: `program-charter-templates`).

8. **Link and notify**
   - Link charter to Atlas project and Jira epic.
   - Post summary to program Slack channel:
   ```
   slack_send_message channel:<channel-id> "Program Charter created for <Name>: <confluence-link>"
   ```

9. **Persist in knowledge base**
   ```
   kn add "Program charter created for <Name>. Key goals: <goals>. Timeline: <dates>." --space program-planning --tags charter,<program-name>
   ```

**Human checkpoints**: Steps 3 (scope confirmation), 5 (risk validation), 6 (cadence approval),
7 (final review before publish).

**Example scenario**: User says "Create a program charter for the AI Gateway Reliability program,
epic key AIGW-100." The skill fetches the epic context and child stories, discovers 3 workstreams
(latency optimization, SLO alerting, failover automation), pulls team members from the Atlas
project, generates a draft charter in Confluence with auto-filled milestones from sprint target
dates, and posts a summary to #ai-gateway-team.

---

### 2.2 Workflow: Create DACI Decision Log

**Trigger**: User says "create a DACI for X", "log this decision", "we need to document
the decision about Y", or a significant decision is detected in Slack.

**Step-by-step**:

1. **Identify the decision context**
   - Ask user for: decision title, program/project context, decision date.
   - If harvesting from Slack:
   ```
   slack_search_messages "decided OR approved OR agreed in:#<channel> after:<date>" --count 30
   ```
   - Expand relevant threads:
   ```
   slack_get_thread <channel-id> <message-ts>
   ```

2. **Assign DACI roles**
   - **Driver (D)**: Person driving the decision to resolution (typically the PM or TPM).
   - **Approver (A)**: Single person with final authority (typically engineering lead or sponsor).
   - **Contributors (C)**: People providing input (SMEs, affected team leads).
   - **Informed (I)**: Stakeholders who need to know but don't decide.
   - Auto-suggest from Jira assignees and Atlas team members:
   ```
   twg teams get <team-id>
   ```

3. **Structure the decision record**
   Use the DACI template structure:
   - **Decision Title**: Clear, specific statement
   - **Status**: Proposed | In Progress | Decided | Revisit
   - **Due Date**: When decision must be made
   - **DACI Roles**: D, A, C, I with names
   - **Context**: Background and why this decision matters
   - **Options Considered**: 2-4 options with pros/cons
   - **Decision**: Final choice and rationale
   - **Action Items**: Next steps with owners and dates

4. **Create Confluence page**
   ```
   twg confluence page create --space <SPACE> --parent <DECISION-LOG-PARENT> --title "DACI: <Decision Title>" --body-adf <daci-adf>
   ```

5. **Persist and notify**
   - Add to knowledge base:
   ```
   kn add "DACI: <title>. Decision: <outcome>. Approver: <name>. Date: <date>. Link: <url>" --space decisions --tags daci,<program>
   ```
   - Notify Informed stakeholders:
   ```
   slack_send_message channel:<channel-id> "Decision logged: <title> — <outcome>. Details: <link>"
   ```

**Autonomy**: Steps 1-2 (data gathering) are fully autonomous. Steps 3-4 (structuring and
publishing) require human review of the decision record before creation.

---

### 2.3 Workflow: Data-Driven Retrospective

**Trigger**: User says "run a retro", "generate retrospective for sprint X", "create a
monthly retrospective", or a sprint/cadence boundary is reached.

**Step-by-step**:

1. **Define retro scope**
   - Ask: time window (sprint dates, month, quarter), team/project, retro type
     (sprint, monthly ops, quarterly).
   - Resolve team members:
   ```
   twg teams get <team-id>
   ```

2. **Collect quantitative data**
   - **Velocity & throughput**:
   ```
   twg work query --scope user --account-id <id> --since <period>
   ```
   For each team member, aggregate completed stories/points.
   - **Cycle time / lead time**: Extract from Jira transition timestamps via work queries.
   - **SLO/SLA metrics**: Search for SLO dashboards and recent burns:
   ```
   slack_search_messages "SLO OR error budget in:#<ops-channel> after:<start>" --count 20
   ```
   - **Deployment frequency**: Search for deployment notifications:
   ```
   slack_search_messages "deployed OR released in:#<deploy-channel> after:<start>" --count 30
   ```

3. **Collect qualitative signals**
   - **Blockers and escalations**:
   ```
   slack_search_messages "blocked OR blocker OR escalat in:#<team-channel> after:<start>" --count 30
   ```
   - **Wins and celebrations**:
   ```
   slack_search_messages "shipped OR launched OR milestone in:#<team-channel> after:<start>" --count 20
   ```
   - **Incident/PIR data**: Search for post-incident reviews:
   ```
   slack_search_messages "PIR OR postmortem OR incident in:#<incidents-channel> after:<start>" --count 20
   ```

4. **Search for recurring patterns**
   ```
   kn search "<current issues>" --space retro-insights --limit 10
   ```
   If similar issues found in past retros → flag as recurring pattern.

5. **Generate retro document**
   Structure into standard sections:
   - **Overview**: Period, team, participants
   - **What Worked**: Evidence-backed wins with metrics
   - **What Didn't Work**: Issues with root cause analysis
   - **Metrics Deltas**: Sprint-over-sprint or month-over-month changes
   - **Risk Surprises**: Unexpected issues or emerging risks
   - **Action Plan**: Prioritized actions with owners and timelines
   - **SOP Update Suggestions**: If recurring patterns detected (see Section 3.2)

6. **Create Confluence page** (in preview/draft mode first)
   ```
   twg confluence page create --space <SPACE> --parent <RETRO-PARENT> --title "Retrospective: <Team> — <Period>" --body-adf <retro-adf>
   ```

7. **Persist insights**
   ```
   kn add "Retro insight: <key finding>. Action: <action>. Period: <dates>." --space retro-insights --tags retro,<team>,<period>
   ```

8. **Post summary to Slack**
   ```
   slack_send_message channel:<channel-id> "Retrospective ready for review: <link>\nKey highlights: <summary>"
   ```

**Human checkpoints**: Step 5 (review generated document), Step 6 (approve before publish),
Step 7 (validate SOP suggestions before acting on them).

**SOP Update Detection Triggers** (from recurring pattern analysis):
- Same issue category appears in ≥2 consecutive retros
- Same SLO/SLA breach pattern repeats within 3 months
- Same dependency blocker recurs across teams
- Action item from previous retro was not completed

---

### 2.4 Workflow: Operating Cadence Design & Auto-Generated Agendas

**Trigger**: User says "set up team cadence", "generate agenda for our weekly sync",
"propose operating rhythm for <team>", or a recurring meeting approaches.

**Step-by-step for cadence design**:

1. **Assess team context**
   - Team size, distribution (time zones), maturity, criticality.
   - Query current team structure:
   ```
   twg teams get <team-id>
   twg org-tree --name "<manager>" --depth 2
   ```

2. **Propose default cadence**
   Use the canonical AI/ML team cadence pattern:
   | Frequency | Ritual | Duration | Purpose |
   |-----------|--------|----------|---------|
   | 2-4x/week | Standup (async or sync) | 15 min | Progress, blockers, dependencies |
   | Weekly | Planning / Execution Review | 30-60 min | Backlog grooming, sprint health |
   | Bi-weekly | Demo / Show & Tell | 30-45 min | Share completed work |
   | Bi-weekly | Team Retrospective | 45-60 min | Continuous improvement |
   | Monthly | Ops / Health Deep Dive | 60 min | SLO review, capacity, cost |
   | Monthly | Program / Portfolio Review | 60 min | OKR progress, roadmap alignment |
   | Quarterly | Planning & Roadmap | Half-day | Big rocks, dependencies, goals |
   | Quarterly | Retrospective (extended) | 90 min | Systemic improvement themes |

3. **Adjust based on maturity**
   - New teams: more frequent syncs (daily standup, weekly retro).
   - Mature teams: shift to async standups, bi-weekly syncs.
   - High-criticality services: add weekly TechOps/Health review.

4. **Create cadence page in Confluence**
   ```
   twg confluence page create --space <SPACE> --title "<Team> Operating Cadence & Rituals" --body-adf <cadence-adf>
   ```

**Step-by-step for auto-generated agendas**:

1. **Determine meeting type** from calendar or user request.

2. **Pull live data based on meeting type**:

   **For Weekly Sync / Standup**:
   ```
   twg work query --scope me --since 7d
   twg jira workitem get --id <sprint-epic>
   ```
   Generate sections: Progress Since Last Sync, Current Blockers, This Week's Priorities.

   **For Sprint Review / Demo**:
   ```
   twg work query --scope user --account-id <id> --since 14d
   ```
   Generate: Completed Items, Demo Queue, Carry-Over Items, Sprint Metrics.

   **For Monthly Ops Review**:
   ```
   slack_search_messages "SLO OR incident OR alert in:#<ops-channel> after:<30d-ago>" --count 30
   twg work query --scope me --since 30d
   ```
   Generate: SLO Status, Incident Summary, Capacity & Cost, Action Item Review.

   **For Quarterly Planning**:
   ```
   twg goals get <goal-id>
   twg projects get <project-id>
   twg work query --scope me --since 90d
   ```
   Generate: OKR Progress, Roadmap Review, Big Rocks Next Quarter, Dependency Map.

3. **Create agenda as Confluence page**
   ```
   twg confluence page create --space <SPACE> --parent <MEETING-NOTES-PARENT> --title "<Meeting> Agenda — <Date>" --body-adf <agenda-adf>
   ```

4. **Share in Slack**
   ```
   slack_send_message channel:<channel-id> "Agenda ready for <meeting>: <link>"
   ```

---

### 2.5 Workflow: Change Management Runbook Generation

**Trigger**: User says "create a change runbook", "document the deployment plan for X",
"generate a runbook for the model upgrade", or a change ticket is created in Jira.

**Step-by-step**:

1. **Determine change type and risk**
   - Ask or infer change type: `schema_change`, `model_upgrade`, `prompt_config_change`,
     `feature_store_migration`.
   - Assess risk factors:
     - Users/tenants affected (blast radius)
     - Reversibility time and complexity
     - Dependency impact (downstream systems, models, agents)
     - Testing confidence (staging coverage, evals, PDVs)
   - Compute risk tier: Low / Medium / High / Critical.
   - Propose ITIL change category: Standard / Normal / Emergency.

2. **Gather system context**
   ```
   twg jira workitem get --id <CHANGE-TICKET>
   twg context jira workitem <CHANGE-TICKET> --depth 2
   ```
   Extract: affected services, environments, related PRs, linked incidents.

3. **Instantiate runbook template**
   Fill in the parameterized template (see knowledge block: `change-management-runbooks`):
   - **Metadata**: runbook ID, title, change type, risk tier, environments, service IDs,
     Jira issue keys, owner, approver.
   - **Scope & Objectives**: What is changing, why, success criteria.
   - **Pre-Change Checklist**: Approvals, timing, access, baselines, backups, dependencies.
   - **Risk Assessment**: Change category, risk matrix, computed risk score.
   - **Type-specific sections**:
     - Schema: migration scripts, rollback SQL, dual-write strategy
     - Model: model version, eval benchmarks, A/B config, rollback model ID
     - Prompt: prompt ID, diff, eval results, shadow mode config
     - Feature store: feature views, backfill plan, data quality checks

4. **Generate rollout strategy**
   Based on risk tier:
   - Low: all-at-once with monitoring
   - Medium: progressive rollout (dev → stage → prod)
   - High: canary deployment with explicit gates
   - Critical: shadow/dual-write with manual gates at each phase

5. **Add verification & monitoring plan**
   - Pre-change baselines (metrics, dashboards)
   - During-rollout checks (PDV, canary analysis, DQ)
   - Post-change monitoring window and "all clear" criteria.

6. **Add rollback plan**
   - Concrete rollback steps for each change type.
   - Rollback triggers (error rate threshold, latency spike, eval regression).
   - Time-to-rollback estimate.

7. **Create Confluence page**
   ```
   twg confluence page create --space <SPACE> --parent <RUNBOOKS-PARENT> --title "Change Runbook: <Title>" --body-adf <runbook-adf>
   ```

8. **Link to Jira and notify**
   - Comment on the change ticket with runbook link.
   - Suggest appropriate Change Type and Risk Assessment field values.
   - Notify stakeholders:
   ```
   slack_send_message channel:<channel-id> "Change runbook ready for review: <link>"
   ```

**Human checkpoints**: Steps 1 (risk tier confirmation), 4 (rollout strategy approval),
6 (rollback plan validation), 7 (final review before publish).

---

## 3. Domain Guidance

### 3.1 Program Charter Template Structure

The canonical AI program charter follows this structure (sourced from PMI, SAFe, and
Atlassian internal templates):

1. **Program Meta**: Title, Sponsor, Program Manager, Timeframe, Status, Approval Date
2. **Background & Context**: Environment, prior work, "why now"
3. **Objectives, Goals & Success Metrics**: 3-5 outcome-focused objectives with baselines/targets
4. **Scope**: In-Scope deliverables, Out-of-Scope exclusions, Nice-to-Have
5. **Timeline & Key Milestones**: 5-10 milestones with target dates and definitions of done
6. **Stakeholders, Roles & Responsibilities**: Sponsor, PgM, Core team, Contributors, Informed
7. **Dependencies**: External teams/systems with what's needed and by when
8. **Risks & Issues**: Top risks with severity, probability, mitigations
9. **Operating Model**: Cadences, status channels, decision-making approach (DACI)
10. **References & Links**: Strategy docs, decision registers, runbooks

**AI/ML-specific additions**:
- Model governance and responsible AI considerations
- Data lineage and privacy requirements
- Evaluation framework and success metrics for AI components
- MLOps infrastructure dependencies

### 3.2 SOP Update Detection Criteria

When retrospective findings should trigger SOP updates (not just one-off action items):

| Trigger Pattern | Detection Method | Urgency |
|-----------------|------------------|---------|
| Same issue in ≥2 consecutive retros | Knowledge base search for recurring themes | High |
| Same SLO breach type ≥3 times in quarter | Slack search for SLO alerts + PIR references | High |
| Action item not completed from prior retro | Knowledge base check for unresolved actions | Medium |
| New failure mode not covered by any runbook | Gap analysis against existing runbooks | Medium |
| Escalation path unclear in ≥2 incidents | PIR analysis for "ownership unclear" patterns | High |
| Same dependency blocker across teams | Cross-team retro pattern matching | Medium |

### 3.3 DACI Decision Framework Quick Reference

| Role | Responsibility | Count |
|------|---------------|-------|
| **Driver (D)** | Drives decision to resolution, frames options, gathers input | Exactly 1 |
| **Approver (A)** | Has final authority, makes the call | Exactly 1 |
| **Contributors (C)** | Provide input, expertise, options analysis | 2-6 typically |
| **Informed (I)** | Need to know the outcome, no decision input | As needed |

**When to use DACI**: Cross-team decisions, architectural choices, scope changes, resource
allocation, vendor selection, process changes, and any decision affecting >1 team.

**Anti-patterns to avoid**:
- Multiple approvers (decision by committee)
- Driver who is also the Approver (conflicts of interest)
- No explicit deadline (decisions drift)
- Skipping the "options considered" section

### 3.4 Risk Tier Classification Matrix

| Factor | Low (1) | Medium (2) | High (3) | Critical (4) |
|--------|---------|------------|----------|---------------|
| Users affected | <100 | 100-10K | 10K-1M | >1M |
| Reversibility | <5 min | 5-60 min | 1-24 hrs | >24 hrs or irreversible |
| Dependencies | None | 1-2 services | 3-5 services | >5 or customer-facing |
| Test confidence | Full staging + evals | Staging only | Partial testing | Minimal testing |

**Risk score** = sum of factors. Tier mapping: 4-6 = Low, 7-9 = Medium, 10-12 = High, 13-16 = Critical.

### 3.5 Terminology

| Term | Definition |
|------|-----------|
| **ADF** | Atlassian Document Format — JSON-based rich document format for Confluence pages |
| **PDV** | Post-Deployment Verification — automated checks after deployment |
| **PIR** | Post-Incident Review — blameless analysis of incidents |
| **SLO** | Service Level Objective — target reliability metric |
| **TTD/TTR** | Time to Detect / Time to Resolve |
| **DACI** | Decision framework: Driver, Approver, Contributor, Informed |
| **CAB** | Change Advisory Board — reviews high-risk changes |
| **Canary** | Deployment strategy exposing change to small traffic subset first |
| **Dual-write** | Writing to both old and new systems during migration |
| **Feature store** | Centralized repository for ML feature definitions and serving |
| **Eval** | Model or prompt evaluation against benchmark datasets |

### 3.6 Cadence Patterns by Team Maturity

**New team (0-3 months)**:
- Daily sync standup, weekly retro, weekly planning
- Focus on establishing norms and building trust

**Growing team (3-12 months)**:
- 2-3x/week async standup, bi-weekly retro, weekly planning
- Add monthly ops review and quarterly planning

**Mature team (12+ months)**:
- Async standup, bi-weekly planning, bi-weekly retro
- Monthly portfolio review, quarterly extended retro
- Shift to exception-based sync meetings

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used | Purpose |
|------|----------------|---------|
| `twg` | `jira workitem get/create/update`, `context jira workitem`, `work query`, `teams get`, `goals get`, `projects get`, `confluence page create`, `org-tree`, `spaces query` | Primary data source and content creation |
| `slack_search_messages` | `query` with channel/user/date filters | Decision harvesting, blocker detection, metric signals |
| `slack_find_channel` | Channel name → ID resolution | Target channels for notifications |
| `slack_send_message` | Post to channels/threads | Notifications, summaries, agenda sharing |
| `slack_get_thread` | Retrieve full thread by channel + timestamp | Expand decision context from Slack |
| `knowledge` | `add`, `search`, `get`, `list`, `update`, `spaces`, `tags`, `export` | Persistent organizational memory |

### 4.2 Cross-Tool Patterns

**Search-Expand-Persist (SEP)**:
1. `slack_search_messages` → find relevant messages
2. `slack_get_thread` → expand full thread context
3. `knowledge add` → persist synthesized insights

**Context-Enrich-Draft (CED)**:
1. `slack_search_messages` + `slack_get_thread` → gather Slack context
2. `knowledge search` → find historical patterns
3. `twg jira/context/goals` → get structured work data
4. Synthesize into document (charter, DACI, retro)
5. `twg confluence page create` → publish to Confluence
6. `knowledge add` → store in knowledge base

**Pattern-Match-Escalate (PME)**:
1. `knowledge search` → find past similar issues
2. Compare current data with historical patterns
3. If recurring → flag for SOP update with evidence
4. `knowledge add` → persist pattern analysis

### 4.3 Autonomy Levels

| Operation | Autonomy | Rationale |
|-----------|----------|-----------|
| Read Jira/Atlas/Confluence data | 🟢 Fully Autonomous | Read-only queries |
| Search Slack messages | 🟢 Fully Autonomous | Read-only search |
| Search/read knowledge base | 🟢 Fully Autonomous | Read-only queries |
| Add to knowledge base | 🟢 Fully Autonomous | Internal persistence |
| Generate draft documents | 🟢 Fully Autonomous | Draft generation |
| Create Confluence pages | 🟡 Semi-Autonomous | Requires preview + approval |
| Post to Slack channels | 🟡 Semi-Autonomous | Stakeholder communication |
| Propose risk tier / change category | 🟡 Semi-Autonomous | Human confirms assessment |
| Modify Jira issue fields | 🟡 Semi-Autonomous | Requires confirmation |
| Publish SOP updates | 🔴 Human Required | Process changes need approval |
| Approve change rollout | 🔴 Human Required | Production impact decisions |
| Set scope exclusions in charters | 🔴 Human Required | Business decisions |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

The AI TPM should **NOT** autonomously:
- Publish program charters without human review of scope and success metrics
- Execute change management runbooks (only generate them)
- Approve or reject changes in production environments
- Modify SLO targets or error budgets
- Make resourcing or staffing decisions
- Override DACI Approver decisions
- Delete or archive knowledge base entries without confirmation
- Post decision outcomes to external (customer-facing) channels
- Transition Jira issues to "Done" or "Closed" without confirmation
- Modify sprint boundaries or release dates

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| Risk tier computed as Critical | Escalate to engineering leadership and CAB |
| SOP update suggested | Flag for human review with evidence summary |
| Recurring pattern detected (≥3 occurrences) | Create escalation summary for team lead |
| Conflicting data between systems | Present both versions, ask human to resolve |
| Change window conflicts with freeze period | Block and notify change manager |
| Decision has no Approver assigned | Flag as incomplete, suggest candidates |
| Retro action item overdue >2 sprints | Escalate to team lead with context |
| Knowledge base contains contradictory entries | Flag for review and reconciliation |

### 5.3 Error Handling

| Failure Mode | Recovery Action |
|-------------|----------------|
| TWG CLI command fails | Retry once; if persistent, fall back to direct Jira/Confluence MCP tools |
| Slack search returns 0 results | Broaden query (remove date filters, use synonyms); report gap to user |
| Knowledge base search finds no matches | Note "no historical precedent found"; proceed without pattern matching |
| Confluence page creation fails | Check space permissions; retry with simplified ADF; report error |
| Rate limiting on Slack API | Back off and retry; batch queries where possible |
| Jira workitem not found | Verify key format; search by summary; ask user to confirm |
| Thread retrieval fails | Fall back to search result context messages (previous/next) |
| Knowledge add fails | Retry; check for content size limits; truncate if necessary |

### 5.4 Knowledge Base Space Taxonomy

Pre-create these spaces during role onboarding for organized persistence:

| Space | Purpose | Example Content |
|-------|---------|-----------------|
| `program-planning` | Charter artifacts, program context | "Charter created for AI Gateway. Goals: ..." |
| `decisions` | DACI decision records | "DACI: Chose Spanner over DynamoDB. Approver: CTO." |
| `retro-insights` | Retrospective findings and patterns | "Recurring: SLO burns without PIR trigger" |
| `risk-patterns` | Historical risk data and mitigations | "Schema migration risk: always test rollback first" |
| `sop-library` | Process documentation and updates | "SOP v2: Added canary gate for model deployments" |
| `templates` | Reusable document templates | "Charter template v3", "DACI template" |
| `org-norms` | Team conventions and operating agreements | "Async-first policy", "Slack channel naming" |
