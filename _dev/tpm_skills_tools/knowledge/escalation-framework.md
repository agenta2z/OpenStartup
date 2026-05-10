# Tiered Escalation Framework for AI Program Management

This knowledge block defines the three-tier escalation model used by the AI Technical Program Manager for risk and dependency escalation decisions. It covers escalation criteria, routing rules, message templates, and decision boundaries.

## Related Skills and Tools
- **Skill**: `ai-tpm-risk-dependency-review` — uses this framework in Step 7 (Escalation Routing) and Section 6.2 (Escalation Triggers)
- **Tool**: `slack_send_message` — delivers escalation messages to appropriate channels
- **Tool**: `confirmation` — gates escalation decisions that require human approval

---

## 1. Three-Tier Model Overview

| Tier | Name | Autonomy | Target | Response Time |
|------|------|----------|--------|---------------|
| **Tier 1** | Auto-Handle | AI executes autonomously | Internal logging, team-level monitoring | Immediate |
| **Tier 2** | Confirm & Act | AI proposes action; human confirms | Team leads, peer TPMs, risk owners | Same day |
| **Tier 3** | Human Escalation | AI drafts; human reviews and sends | Senior leadership, cross-org stakeholders, executives | Urgent (within hours) |

---

## 2. Escalation Criteria Matrix

### 2.1 Risk-Based Escalation

| Criterion | Tier 1 (Auto) | Tier 2 (Confirm) | Tier 3 (Escalate) |
|-----------|---------------|-------------------|---------------------|
| Risk Rating | Insignificant / Low | Medium / High | Critical |
| Residual Score | 1-4 | 5-16 | 17-25 |
| Rating Change | Stable or improving | Increased by 1 band | Increased to Critical OR jumped 2+ bands |
| Mitigation Status | On track | Overdue 1-7 days | Overdue >7 days with no plan |
| Risk Appetite | Within appetite | At appetite boundary | Above appetite with no acceptance |

### 2.2 Dependency-Based Escalation

| Criterion | Tier 1 (Auto) | Tier 2 (Confirm) | Tier 3 (Escalate) |
|-----------|---------------|-------------------|---------------------|
| Dependency Slack | >= 5 working days | 1-4 working days | <= 0 days (overdue) |
| Critical Path | Not on critical path | On critical path, provider on track | On critical path, provider at risk/missed |
| Blocker Duration | < 2 days | 2-5 days | > 5 days |
| Blocker State | Not blocking | Soft blocker | Hard blocker on critical path |
| Cross-Team Impact | Single team | 2 teams | 3+ teams or cross-org |

### 2.3 Decision & Governance Escalation

| Criterion | Tier 1 (Auto) | Tier 2 (Confirm) | Tier 3 (Escalate) |
|-----------|---------------|-------------------|---------------------|
| Decision Scope | Within team authority | Cross-team coordination needed | Cross-org or executive decision |
| Ambiguity | Clear playbook exists | Some judgment needed | No clear next steps |
| Stakeholder Response | Responsive within SLA | Unresponsive 1-2 cycles | Unresponsive 3+ review cycles |
| Financial Impact | < $10K | $10K - $100K | > $100K |

---

## 3. Tier 1: Auto-Handle Operations

### What the AI Does Autonomously
- Log risk/dependency in RAID register with all structured fields
- Calculate and update risk scores
- Update dependency slack calculations
- Generate risk delta reports
- Monitor and flag threshold breaches
- Append dated notes to risk entries
- Link related Jira issues to RAID entries

### What the AI Logs
For each Tier 1 action:
```
[TIER-1] [YYYY-MM-DD HH:MM] Action: <description>
  Risk/Dep: <ID> - <Title>
  Trigger: <what triggered this action>
  Result: <outcome>
```

### Constraints
- No write operations to production systems without confirmation
- No external communications (Slack, email)
- No status transitions on Jira issues
- No risk acceptance decisions

---

## 4. Tier 2: Confirm & Act Operations

### Process
1. AI detects escalation trigger
2. AI drafts proposed action with evidence
3. AI presents to user via `confirmation` tool
4. User reviews and approves/rejects
5. If approved: AI executes action and logs
6. If rejected: AI logs rejection reason and suggests alternatives

### Confirmation Template
```
⚠️ TIER 2 ESCALATION PROPOSED

Risk/Dependency: [{ID}] {Title}
Current Rating: {rating} (Score: {score})
Trigger: {what triggered escalation}

Evidence:
- {evidence_point_1}
- {evidence_point_2}

Proposed Action: {action_description}
Target: {who will be notified/affected}

Approve this action?
```

### Common Tier 2 Actions
| Action | Tool | Parameters |
|--------|------|------------|
| Notify risk owner of rating change | `slack_send_message` | channel: DM to owner |
| Update RAID register with new High risk | `twg confluence pages update` | RAID page with new entry |
| Create action item for mitigation | `twg jira workitem create` | Type: Task, linked to risk |
| Post dependency alert to team channel | `slack_send_message` | channel: team channel |
| Request status update from provider team | `slack_send_message` | channel: provider team channel |

---

## 5. Tier 3: Human Escalation Operations

### Process
1. AI detects critical escalation trigger
2. AI drafts escalation message with full context
3. AI presents draft to user via `confirmation` tool
4. User reviews, edits if needed, and approves
5. AI sends via `slack_send_message`
6. AI logs escalation with timestamp and recipients

### Escalation Message Template

```
:rotating_light: ESCALATION: [{ID}] — {Title}

Program: {Program Name}
Rating: {Rating} (Score: {Score})
Category: {Category}
Status: {Status}
Duration: Blocked for {N} days

Impact Statement:
{if_then_because statement from risk entry}

Current Situation:
- {situation_point_1}
- {situation_point_2}

What Has Been Tried:
- {attempted_mitigation_1}
- {attempted_mitigation_2}

Requested Decision/Action:
{specific_ask}

Timeline: Decision needed by {date}

Risk Owner: @{owner}
TPM: @{tpm}
Program Lead: @{program_lead}
```

### Escalation Routing

| Risk Category | Primary Channel | Secondary Contact |
|---------------|----------------|-------------------|
| Model Quality & Safety | #ai-safety-escalations | ML Engineering Lead |
| Data & Privacy | #privacy-escalations | Privacy Engineering Lead, DPO |
| Infra, Performance & Cost | #platform-escalations | Infrastructure Lead |
| Vendor & Third-Party | #vendor-management | Procurement Lead, Legal |
| Governance & Compliance | #compliance-escalations | GRC Lead, Legal |
| GTM, Customer & Product | #product-escalations | Product Lead, Customer Success Lead |
| Cross-category / Critical | #program-leadership | Program Director, VP Engineering |

### De-escalation Criteria
An escalation can be de-escalated when:
- Risk rating drops below the escalation threshold
- Dependency slack returns to >= 5 days
- Blocker is resolved
- Decision is made by appropriate authority
- Mitigation plan is in place and on track

---

## 6. Escalation Anti-Patterns

Avoid these common mistakes:

| Anti-Pattern | Why It's Bad | Correct Approach |
|-------------|--------------|------------------|
| Escalating without evidence | Wastes leadership time; erodes trust | Always include quantified impact and timeline |
| Skipping Tier 2 straight to Tier 3 | Bypasses team-level resolution | Follow the tier progression unless severity warrants immediate Tier 3 |
| Escalating without a specific ask | Recipients don't know what action to take | Always include "Requested Decision/Action" with a concrete ask |
| Repeated escalation of same issue | Indicates broken process, not just broken risk | After 2 escalations, flag as systemic issue requiring process change |
| Escalating resolved issues | Creates confusion and alert fatigue | Always check current status before escalating |
| Broadcasting to all channels | Dilutes urgency; creates noise | Route to specific channel per category (see Section 5) |

---

## 7. Escalation Tracking

All escalations should be tracked with:

| Field | Description |
|-------|-------------|
| `escalation_id` | Unique ID (ESC-NNN) |
| `source_id` | Risk or dependency ID that triggered escalation |
| `tier` | 1, 2, or 3 |
| `trigger` | What criterion was met |
| `proposed_action` | What was proposed |
| `decision` | Approved / Rejected / Modified |
| `decision_maker` | Who approved/rejected |
| `timestamp_proposed` | When AI proposed escalation |
| `timestamp_decided` | When human decided |
| `timestamp_resolved` | When escalation was de-escalated |
| `outcome` | What happened as a result |
| `days_to_resolve` | Duration from escalation to resolution |
