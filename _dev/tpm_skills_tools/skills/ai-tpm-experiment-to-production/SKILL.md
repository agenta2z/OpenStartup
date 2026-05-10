---
name: ai-tpm-experiment-to-production
description: >
  Guides the AI Technical Program Manager through SOP 3: AI Experiment-to-Production
  Lifecycle management. Covers the 5-stage lifecycle (Ideation, Sandbox, Pre-Production,
  Progressive Rollout, General Availability) with gate criteria at each transition,
  monitoring signal verification, hold/rollback triggers, and post-GA steady-state
  operations. Leverages twg, slack_send_message, and confirmation tools with clear
  autonomy boundaries.
labels:
  - ai-tpm
  - experiment-lifecycle
  - production-readiness
  - progressive-rollout
metadata:
  requires:
    env: [TWG_USER, TWG_SITE, TWG_TOKEN, TWG_BBC_TOKEN, SLACK_BOT_TOKEN]
  tools:
    - twg
    - slack_send_message
    - confirmation
    - single_choice
---

# AI TPM Experiment-to-Production Lifecycle Skill

## 1. Skill Overview

- **Name**: ai-tpm-experiment-to-production
- **Description**: Encodes the complete SOP 3 (AI Experiment-to-Production Lifecycle) workflow for the AI Technical Program Manager role. This skill guides the AI TPM through a 5-stage lifecycle — from Ideation & Intake through Sandbox development, Pre-Production validation, Progressive Rollout, to General Availability — with gate criteria at each stage transition, monitoring verification, hold/rollback triggers, and post-GA steady-state monitoring and lifecycle management.
- **Leveraged Tools**:
  - **twg** — Query and manage Atlassian Teamwork Graph data. Used for Jira workitem CRUD (create stage-tracking issues, gate checklist items, lifecycle tickets), Confluence page operations (create/update stage gate documents, experiment logs, monitoring specs), cross-product queries for experiment artifacts, and identity/team resolution.
  - **slack_send_message** — Send messages to Slack channels and DMs. Used for stage transition announcements, canary health alerts, rollback notifications, and weekly lifecycle status updates.
  - **confirmation** — Human-in-the-loop gating with artifact preview. Used for stage transition approvals, rollback decisions, and governance board escalations.
  - **single_choice** — Present multiple options for selection. Used for stage transition decisions (Advance / Hold / Rollback) and risk tier confirmation.

## 2. Workflow Mappings

### Workflow: SOP 3 — AI Experiment-to-Production Lifecycle

**Trigger**: A new AI/ML use case, model improvement, or experiment is initiated.

**Purpose**: Ensure AI/ML systems progress through a structured lifecycle with appropriate gates, evidence, and approvals at each stage before reaching production.

---

#### Stage 1: Ideation & Intake (Autonomy: mixed 🟢/🟡)

**1a. Use Case Registration (🟢 Autonomous)**

Create a tracking issue for the new AI initiative:

```bash
scripts/twg jira workitem create --space <PROJECT-KEY> --type Epic \
  --summary "[AI Lifecycle] <use-case-name> — Ideation" \
  --assignee me
```

**1b. Risk Tier Classification (🟢 Autonomous)**

Apply the same 4-dimensional risk matrix as SOP 1 (see ai-tpm-launch-readiness-gate skill):
- Model type, Data sensitivity, Customer exposure, Regulatory scope
- Composite rule: Overall tier = max(individual factor tiers)

**1c. Intake Checklist Generation (🟢 Autonomous)**

Auto-generate intake checklist items as sub-tasks:
- Business justification documented
- Data requirements identified
- Success criteria defined
- Privacy/compliance needs assessed
- Resource requirements estimated

```bash
scripts/twg jira workitem create --space <PROJECT-KEY> --type Task \
  --summary "[Intake] Business justification for <use-case-name>"
```

**1d. High-Risk Governance Escalation (🟡 Confirm Before Action)**

If risk tier is High, flag for governance board review before proceeding:

```
confirmation(
  prompt: "High-risk AI use case identified: <use-case-name>. Risk factors: <factors>. This requires governance board review before proceeding to Sandbox stage. Confirm escalation?",
)
```

**Gate Criteria to Exit Ideation**:
- [ ] Business justification approved
- [ ] Risk tier classified and confirmed
- [ ] Data requirements identified
- [ ] Success criteria defined
- [ ] High-risk cases reviewed by governance board

---

#### Stage 2: Sandbox / Offline Experiment (Autonomy: 🟢 Autonomous monitoring, 🟡 Confirm transitions)

**2a. Experiment Tracking (🟢 Autonomous)**

Monitor experiment progress by querying related artifacts:

```bash
# Check experiment tracking issues
scripts/twg context jira workitem <EPIC-KEY> --depth 2

# Search for experiment documentation
scripts/twg confluence search query --cql 'type=page AND title ~ "<use-case-name> experiment"'
```

**2b. Offline Evaluation Gate Checks (🟢 Autonomous)**

Verify that offline evaluation requirements are met:

| Check | Verification Method | Pass Criteria |
|---|---|---|
| Code & data quality CI | CI pipeline status | All CI checks pass (lint, tests, security scans) |
| Data validation | Great Expectations / pandera reports | Schema validation passes, no data quality issues |
| Offline metrics | MLflow / evaluation framework | Core metrics meet defined thresholds |
| Baseline comparison | Experiment tracking | New approach meets or exceeds baseline |
| Reproducibility | Experiment artifacts | Training is reproducible with documented configs |

**2c. Stage Transition Decision (🟡 Confirm)**

Present evaluation summary and request transition approval:

```
single_choice(
  prompt: "Sandbox evaluation complete for <use-case-name>. Offline metrics: <summary>. Recommend transition to Pre-Production?",
  choices: ["Advance to Pre-Production", "Continue in Sandbox (more experiments needed)", "Terminate experiment"]
)
```

**Gate Criteria to Exit Sandbox**:
- [ ] Offline metrics meet thresholds
- [ ] Data validation passes
- [ ] Code quality CI passes
- [ ] Baseline comparison favorable
- [ ] Experiment documented (model card draft, training config, data lineage)

---

#### Stage 3: Pre-Production / Staging (Autonomy: 🟢 Checks, 🟡 Confirm transitions)

**3a. Integration Testing Verification (🟢 Autonomous)**

Verify pre-production environment readiness:

| Check | Verification Method | Pass Criteria |
|---|---|---|
| Integration tests | CI/CD pipeline | All integration tests pass in staging |
| Load/performance tests | Performance test artifacts | Meets SLO targets under expected load |
| Cost estimation | Cloud cost analysis | Within budget per 1K inferences |
| Model serving config | Deployment descriptor review | Serving configuration matches production specs |
| Feature flag setup | Feature flag platform | Feature gate configured for progressive rollout |

**3b. SOP 1 Launch Readiness Gate (🔴 Human Required for decision)**

At this point, trigger the full SOP 1 Launch Readiness Gate process (see ai-tpm-launch-readiness-gate skill). The launch gate must PASS or CONDITIONAL PASS before proceeding to Progressive Rollout.

```bash
# Create launch readiness gate tracking issue
scripts/twg jira workitem create --space <PROJECT-KEY> --type Task \
  --summary "[Launch Gate] <use-case-name> — Pre-Production Readiness"
```

**Gate Criteria to Exit Pre-Production**:
- [ ] Integration tests pass in staging
- [ ] Load/performance tests meet SLOs
- [ ] Cost within budget
- [ ] Feature flag configured
- [ ] SOP 1 Launch Readiness Gate: GO or CONDITIONAL GO
- [ ] Deployment runbook documented and reviewed

---

#### Stage 4: Progressive Rollout / Canary (Autonomy: 🟢 Monitor, 🔴 Rollback requires human)

**4a. Rollout Plan Generation (🟡 Confirm Before Execution)**

Generate a progressive rollout plan based on service throughput:

**Low throughput (<5,000 peak RPM):**
- Rollout percentages: [1%, 30%, 65%, 100%]
- Stage interval: 10 minutes minimum
- Sequential regions: 2 regions, then remaining in parallel

**High throughput (>5,000 peak RPM):**
- Rollout percentages: [1%, 5%, 10%, 20%, 40%, 60%, 80%, 100%]
- Stage interval: 10 minutes minimum
- Sequential regions: 3 regions, then remaining in parallel

**Common parameters:**
- Pre-prod soak: minimum 30 minutes
- First prod region soak: minimum 60 minutes
- Old stack retention: minimum 60 minutes after rollout completes

Present the plan for approval:

```
confirmation(
  prompt: "Progressive rollout plan for <use-case-name>:\n- Percentages: <percentages>\n- Stage interval: <interval>min\n- First region: <region>\n- Soak time: 60min\nApprove rollout plan?",
)
```

**4b. Canary Health Monitoring (🟢 Autonomous)**

During rollout, continuously monitor canary health metrics:

| Metric Category | Signals | Alert Threshold |
|---|---|---|
| Latency | P50, P95, P99 response time | >10% degradation vs baseline |
| Error rate | 5xx rate, timeout rate | >0.1% increase |
| Model quality | Online metrics (CTR, engagement) | >5% degradation |
| Safety | Content filter trigger rate | >2x baseline |
| Resource | CPU/GPU utilization, memory | >80% utilization |
| Business | Conversion, task completion | >3% degradation |

**4c. Canary Analysis Decision Points**

At each rollout stage, evaluate canary metrics:

- **PASS** (all metrics within thresholds): Proceed to next percentage
- **MARGINAL** (minor degradation, within tolerance): Hold current percentage, extend soak time, alert team
- **FAIL** (any metric exceeds threshold): Halt rollout, alert team, recommend rollback

```
# On MARGINAL or FAIL
slack_send_message(
  to: "channel:<TEAM-CHANNEL-ID>",
  content: "⚠️ Canary alert for <use-case-name> at <percentage>%: <metric> showing <value> (threshold: <threshold>). Status: <MARGINAL|FAIL>. Action required."
)
```

**4d. Rollback Decision (🔴 Human Required)**

The AI TPM MUST NOT autonomously roll back. On canary failure:

1. Create incident ticket
2. Alert on-call and engineering lead
3. Present rollback recommendation to human decision-maker

```
confirmation(
  prompt: "Canary FAIL for <use-case-name> at <percentage>%. Metric: <metric> = <value> (threshold: <threshold>). Recommend rollback to previous version. Approve rollback?",
)
```

**Gate Criteria to Complete Progressive Rollout**:
- [ ] All canary stages pass health checks
- [ ] 60-minute soak in first prod region complete
- [ ] No P0/P1 incidents during rollout
- [ ] Online metrics stable at 100% traffic
- [ ] Old stack retained for minimum 60 minutes post-completion

---

#### Stage 5: General Availability & Steady-State (Autonomy: 🟢 Monitor, 🟡/🔴 Actions)

**5a. GA Declaration (🟡 Confirm)**

After successful progressive rollout, formally declare GA:

```bash
# Update tracking epic to GA status
scripts/twg jira workitem update --id <EPIC-KEY> \
  --summary "[AI Lifecycle] <use-case-name> — General Availability"

# Create GA announcement
slack_send_message(
  to: "channel:<TEAM-CHANNEL-ID>",
  content: "🎉 <use-case-name> has reached General Availability! All launch gates passed, progressive rollout complete. Monitoring active."
)
```

**5b. Post-GA Monitoring Spec Verification (🟢 Autonomous)**

Verify that steady-state monitoring is configured:

| Monitoring Asset | Verification | Required |
|---|---|---|
| Quality metrics dashboard | Dashboard URL accessible | All tiers |
| Drift detection pipeline | Pipeline status active | Medium/High |
| Safety monitoring | Alert rules configured | Medium/High |
| Cost tracking | Budget alerts set | All tiers |
| Fairness monitoring | Slice-level metrics tracked | High only |
| Incident runbook | Confluence page exists | All tiers |
| Retraining trigger | Criteria documented | Medium/High |

```bash
scripts/twg confluence search query --cql 'type=page AND title ~ "<use-case-name> monitoring"'
scripts/twg confluence search query --cql 'type=page AND title ~ "<use-case-name> runbook"'
```

**5c. Recurring Lifecycle Checks (🟢 Autonomous analysis, 🟡 Confirm actions)**

On a recurring cadence, perform lifecycle health checks:

| Check | Cadence | Action on Breach |
|---|---|---|
| Offline quality metrics | Weekly | Create Jira ticket if >15% drop vs 30-day average |
| Online business metrics | Daily for 30 days, then weekly | Alert if guardrail metric degrades >5% |
| Drift detection | Weekly | Create Jira ticket if feature/output drift exceeds threshold |
| Cost review | Monthly | Alert if cost per 1K inferences exceeds budget by >10% |
| Safety incident review | Weekly | Escalate if incident rate increases |
| Model staleness | Quarterly | Flag for retraining evaluation if data age > threshold |

**5d. Retraining & Deprecation Triggers**

When lifecycle checks indicate degradation:

```bash
# Create retraining ticket
scripts/twg jira workitem create --space <PROJECT-KEY> --type Task \
  --summary "[Lifecycle] Retraining required: <use-case-name> — <reason>"

# For deprecation
scripts/twg jira workitem create --space <PROJECT-KEY> --type Task \
  --summary "[Lifecycle] Deprecation review: <use-case-name> — <reason>"
```

Retraining triggers re-entry at Stage 2 (Sandbox) with the updated model.
Deprecation requires human approval and a documented sunset plan.

---

### Example Scenario: Recommendation Model from Experiment to Production

1. **Ideation**: Data scientist proposes improved recommendation model using customer interaction patterns. AI TPM creates epic PROJ-100, classifies as Medium risk (internal data, limited beta initially). Generates intake checklist.

2. **Sandbox**: Over 3 weeks, model is trained and evaluated offline. AI TPM monitors experiment artifacts, verifies offline metrics (nDCG@10 improved 12% over baseline). Presents results, stakeholder approves advancement to Pre-Production.

3. **Pre-Production**: Integration tests pass in staging. Load test confirms P95 latency within 200ms budget. Feature flag configured for progressive rollout. AI TPM triggers SOP 1 launch gate — all checks pass, gate result: GO.

4. **Progressive Rollout**: Rollout plan: [1%, 5%, 10%, 20%, 40%, 60%, 80%, 100%] with 10-min intervals. First region (eu-west-1) deployed, 60-min soak passes. At 20%, slight latency increase detected (P95 +8%, within 10% threshold) — MARGINAL. Team notified, extended soak. Metrics stabilize. Rollout continues to 100%.

5. **GA**: All regions at 100%, 7-day stability period passes. GA declared. Monitoring spec verified: quality dashboard live, drift detection active, runbook documented. Weekly lifecycle checks begin.

6. **Steady-State**: At week 6, offline quality metrics show 5% nDCG drop in APAC segment. AI TPM creates retraining ticket PROJ-150. Data team investigates, identifies data distribution shift. Retraining initiated (re-enters Stage 2).

## 3. Domain Guidance

### Templates and Checklists

#### Stage Transition Checklist Template

```
## Stage Transition: <from-stage> → <to-stage>

**System**: <use-case-name>
**Risk Tier**: <Low | Medium | High>
**Date**: <transition-date>
**Requested By**: <requestor>

### Gate Criteria
| # | Criterion | Status | Evidence | Notes |
|---|-----------|--------|----------|-------|
| 1 | <criterion> | ✅/❌/⏳ | <link> | <notes> |

### Approvals
| Role | Person | Decision | Date |
|------|--------|----------|------|
| <role> | <name> | Approved/Rejected | <date> |

### Conditions (if any)
| Condition | Owner | Due Date |
|-----------|-------|----------|
```

#### Progressive Rollout Plan Template

```
## Progressive Rollout Plan

**Service**: <service-name>
**Model Version**: <version>
**Peak RPM**: <rpm> (<Low|High> throughput)
**Date**: <planned-date>

### Rollout Schedule
| Stage | Percentage | Region | Min Soak | Status |
|-------|-----------|--------|----------|--------|
| 1 | 1% | <first-region> | 60 min | ⏳ |
| 2 | <next>% | <region> | 10 min | ⏳ |
| ... | ... | ... | ... | ... |
| N | 100% | All | — | ⏳ |

### Health Metrics
| Metric | Baseline | Threshold | Current |
|--------|----------|-----------|---------|
| P95 Latency | <baseline> | <+10%> | — |
| Error Rate | <baseline> | <+0.1%> | — |

### Rollback Plan
- Rollback mechanism: <blue-green / canary / feature flag>
- Old stack retention: 60 minutes
- Rollback approver: <name>
```

#### Post-GA Monitoring Spec Template

```
## Steady-State Monitoring Specification

**System**: <use-case-name>
**Model Version**: <version>
**GA Date**: <date>
**Risk Tier**: <tier>

### Offline Quality Metrics
| Metric | Baseline | Alert Threshold | Evaluation Cadence |
|--------|----------|-----------------|--------------------|
| <metric> | <value> | <threshold> | Daily/Weekly |

### Online Business Metrics
| Metric | Baseline | Guardrail Threshold | Source |
|--------|----------|---------------------|--------|
| <metric> | <value> | <threshold> | <dashboard> |

### Drift Detection
| Signal | Method | Alert Threshold |
|--------|--------|-----------------|
| Feature drift | PSI/KL divergence | >0.2 |
| Output drift | Distribution comparison | >0.15 |

### Lifecycle Rules
| Trigger | Action | Approver |
|---------|--------|----------|
| Quality drop >15% for 7 days | Retraining | ML Lead |
| Safety incident rate >2x | Kill switch review | Eng Lead |
| Model age >6 months | Staleness review | TPM |
| Cost >20% over budget for 30 days | Optimization review | Eng Manager |
```

### Decision Criteria

#### Stage Transition Decision Matrix

| Current Stage | Advance Criteria | Hold Criteria | Rollback/Terminate Criteria |
|---|---|---|---|
| Ideation → Sandbox | Business case approved, risk tier classified | Missing justification or data requirements | Governance board rejects (High risk) |
| Sandbox → Pre-Prod | Offline metrics meet thresholds, baseline exceeded | Metrics marginal, more experiments needed | Approach fundamentally flawed |
| Pre-Prod → Rollout | SOP 1 gate PASS, integration tests pass | Gate CONDITIONAL with open items | Gate NO-GO, critical failures |
| Rollout → GA | All canary stages pass, 7-day stability | Canary marginal, extended soak needed | Canary FAIL, metric degradation |
| GA → Deprecation | Model staleness, better replacement available | Under evaluation | Critical safety/quality failure |

#### Canary Analysis Thresholds

| Metric | PASS | MARGINAL | FAIL |
|---|---|---|---|
| Latency (P95) | <5% increase | 5-10% increase | >10% increase |
| Error rate | No increase | <0.05% increase | >0.1% increase |
| Online quality | <2% degradation | 2-5% degradation | >5% degradation |
| Safety triggers | <1.5x baseline | 1.5-2x baseline | >2x baseline |
| Resource utilization | <70% | 70-80% | >80% |

### Terminology

| Term | Definition |
|---|---|
| **Sandbox** | Isolated development environment for offline experimentation and model training |
| **Pre-Production** | Staging environment that mirrors production for integration and load testing |
| **Progressive Rollout** | Gradual traffic shift to new version using percentage-based stages |
| **Canary** | Small percentage of traffic routed to new version for health validation |
| **Soak Time** | Minimum duration at a rollout percentage to accumulate sufficient signal |
| **Old Stack Retention** | Period after rollout completion where previous version remains available for rollback |
| **Feature Gate** | Feature flag mechanism controlling which users see the new AI feature |
| **PCV** | Post-Change Verification — automated health check after deployment changes |
| **ACA** | Automated Canary Analysis — statistical comparison of canary vs baseline metrics |
| **Drift** | Statistical change in feature distributions or model output distributions over time |
| **Model Staleness** | Degradation due to time-based data distribution shifts |
| **Retraining Trigger** | Defined condition (metric breach, time elapsed) that initiates model retraining |

### Cadence Patterns

| Activity | Frequency | Stage |
|---|---|---|
| Experiment progress check | Weekly | Sandbox |
| Pre-prod integration verification | Per deployment | Pre-Production |
| Canary health monitoring | Continuous (every 10 min) | Progressive Rollout |
| Post-GA quality metrics review | Daily (first 30 days), then weekly | GA |
| Drift detection | Weekly | GA |
| Cost review | Monthly | GA |
| Model staleness assessment | Quarterly | GA |
| Full lifecycle re-assessment | Semi-annually | GA |

## 4. Integration Metadata

### Tools Referenced

| Tool | Operations Used | Purpose |
|---|---|---|
| `twg` | `jira workitem create/get/update/transition`, `confluence pages create/update/get`, `confluence search query`, `context jira workitem`, `docs query`, `work query`, `user-search`, `teams query`, `projects` | Lifecycle tracking, gate documents, evidence collection, identity resolution |
| `slack_send_message` | Send to channel, send DM, thread reply | Stage transition announcements, canary alerts, rollback notifications, status updates |
| `confirmation` | Prompt with optional view | Stage transition approvals, rollback decisions, governance escalations |
| `single_choice` | Multi-option selection | Advance/Hold/Rollback decisions, risk tier confirmation |

### Cross-Tool Patterns

| Pattern | Tools Involved | Flow |
|---|---|---|
| **Experiment → Gate Document** | `twg` (read) → `twg` (write Confluence) | Query experiment artifacts → Generate stage gate document → Create Confluence page |
| **Canary Alert → Rollback Decision** | `slack_send_message` → `confirmation` | Alert team of canary issue → Present rollback recommendation to human |
| **Lifecycle Check → Ticket Creation** | `twg` (read) → `twg` (create Jira) | Check monitoring metrics → Create retraining/deprecation ticket |
| **Stage Transition → Announcement** | `confirmation` → `twg` (update Jira) → `slack_send_message` | Get approval → Update epic status → Announce transition |
| **SOP 3 → SOP 1 Handoff** | This skill → ai-tpm-launch-readiness-gate | At Pre-Production stage, trigger full SOP 1 launch readiness gate |

### Autonomy Levels

| Operation | Autonomy | Notes |
|---|---|---|
| Read experiment artifacts, monitoring data | 🟢 Fully Autonomous | All read operations safe |
| Risk tier classification | 🟢 Fully Autonomous | Based on defined matrix |
| Create intake/tracking Jira tickets | 🟢 Fully Autonomous | Standard lifecycle management |
| Generate stage gate document drafts | 🟢 Fully Autonomous | Draft creation safe |
| Monitor canary health metrics | 🟢 Fully Autonomous | Continuous monitoring safe |
| Create retraining/lifecycle Jira tickets | 🟢 Fully Autonomous | Proactive lifecycle management |
| Stage transition decisions | 🟡 Confirm Before Action | Human must approve each transition |
| Create/update Confluence pages | 🟡 Confirm Before Write | State intent, confirm before write |
| Rollout plan approval | 🟡 Confirm Before Action | Human reviews plan parameters |
| Production rollback | 🔴 Human Required | NEVER autonomously roll back |
| Go/No-Go gate decision (SOP 1) | 🔴 Human Required | Delegated to launch readiness gate skill |
| Deprecation/sunset decision | 🔴 Human Required | Business decision requiring human judgment |
| Governance board escalation | 🔴 Human Required | Requires human routing and approval |

## 5. Guardrails and Escalation

### Safety Boundaries — What the AI TPM MUST NOT Do

- **NEVER** autonomously approve a stage transition without human confirmation
- **NEVER** autonomously roll back a production deployment
- **NEVER** skip the SOP 1 Launch Readiness Gate at Pre-Production stage
- **NEVER** proceed to Progressive Rollout without SOP 1 gate approval
- **NEVER** override canary failure thresholds
- **NEVER** extend a progressive rollout beyond approved percentages without confirmation
- **NEVER** autonomously deprecate or sunset a model
- **NEVER** modify experiment data, training configs, or model artifacts

### Escalation Triggers

| Condition | Action | Target |
|---|---|---|
| High-risk use case at Ideation | Flag for governance board review | Governance board |
| Offline metrics below threshold after 3 experiment cycles | Recommend approach re-evaluation | ML Lead + Product Owner |
| Canary FAIL at any rollout stage | Halt rollout, alert team, recommend rollback | On-call + Engineering Lead |
| Canary MARGINAL for >2 consecutive stages | Alert team, recommend extended soak or rollback | Engineering Lead |
| Post-GA quality drop >15% sustained for 7+ days | Create P1 retraining ticket | ML Lead |
| Post-GA safety incident rate >2x baseline | Recommend kill-switch review | Engineering Lead + Safety Team |
| Cost exceeds budget by >20% for 30+ days | Alert engineering manager | Engineering Manager |
| Model age exceeds 6 months without re-evaluation | Flag staleness review | TPM + ML Lead |
| Stage transition blocked for >2 weeks | Escalate to program leadership | TPM Manager |

### Error Handling

| Error | Response |
|---|---|
| TWG command fails | Retry once after 30 seconds. Log error and notify user if persistent. |
| Experiment artifacts not found | Mark check as PENDING. Create search-expansion query with broader CQL. |
| Canary metrics unavailable | Alert team that monitoring may be misconfigured. Do NOT proceed with rollout. |
| Stage gate document creation fails | Validate ADF structure, fix common issues (empty text nodes, missing attrs), retry. |
| Rollout plan parameters conflict | Flag conflict to human (e.g., soak time below minimum). Do not proceed. |
| Post-GA monitoring gaps detected | Create Jira ticket for monitoring gap. Alert team. |
| Slack notification fails | Log content locally. Retry once. Include in next gate document update. |

### Audit Trail

Every lifecycle stage transition MUST produce:
1. **Confluence gate document** — Evidence, gate criteria status, and decision record
2. **Jira epic update** — Status reflects current lifecycle stage
3. **Jira sub-tasks** — For all gate criteria, remediation items, and conditions
4. **Slack announcement** — Stage transition notification with key details
5. **Decision log** — Who approved the transition, when, with what conditions
