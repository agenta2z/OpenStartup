# RAID Register Data Model for AI Programs

This knowledge block defines the canonical data model for RAID (Risks, Assumptions, Issues, Dependencies) register entries used by the AI Technical Program Manager. It covers field definitions, lifecycle states, scoring mechanics, and the structured risk statement format.

## Related Skills and Tools
- **Skill**: `ai-tpm-risk-dependency-review` — uses this model for RAID register maintenance
- **Tool**: `twg` — Confluence page CRUD for persisting RAID register as ADF tables

---

## 1. RAID Entry Types

| Type | Code | Description | Example |
|------|------|-------------|---------|
| **Risk** | R | An uncertain event that, if it occurs, impacts program objectives | "Model drift causes degraded recommendations post-launch" |
| **Assumption** | A | Something taken as true for planning that, if wrong, becomes a risk | "Vendor API will maintain <200ms p99 latency" |
| **Issue** | I | A realized risk or current problem requiring resolution | "Training pipeline failed due to data schema change" |
| **Dependency** | D | An external input, deliverable, or decision needed from another party | "Platform team must deliver model serving API by May 15" |
| **Decision** | DEC | A choice made that affects program direction and may create or retire risks | "Decided to use vendor X model instead of in-house" |

---

## 2. Core Field Schema

### 2.1 Required Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | string | Unique identifier | Format: `{TYPE}-{NNN}` (e.g., R-001, D-015) |
| `title` | string | Short, impact-focused name | Max 120 characters; lead with impact area |
| `type` | enum | RAID entry type | R \| A \| I \| D \| DEC |
| `description` | structured text | Full risk/issue description | See Section 3 for structured statement format |
| `category_primary` | enum | Primary AI risk category | See Section 4 |
| `likelihood` | integer (1-5) | Probability of occurrence | 1=Rare, 2=Unlikely, 3=Possible, 4=Likely, 5=Almost Certain |
| `impact` | integer (1-5) | Severity if it occurs | 1=Insignificant, 2=Low, 3=Medium, 4=High, 5=Critical |
| `score` | integer (1-25) | Calculated risk score | `likelihood × impact` (auto-calculated) |
| `rating` | enum | Risk rating band | Insignificant \| Low \| Medium \| High \| Critical |
| `status` | enum | Lifecycle status | See Section 5 |
| `owner` | string | Accountable individual | Atlassian account ID or display name |
| `response` | enum | Treatment strategy | Accept \| Avoid \| Reduce \| Transfer \| Watch |
| `date_identified` | date | When first logged | ISO 8601 |

### 2.2 Recommended Fields

| Field | Type | Description |
|-------|------|-------------|
| `category_secondary` | enum | Secondary AI risk category (optional) |
| `mitigation_plan` | rich text | Detailed mitigation actions with linked Jira issues |
| `contingency_plan` | rich text | What to do if risk materializes |
| `due_date` | date | Target remediation date |
| `linked_work_items` | array of strings | Jira issue keys for related epics/stories/tasks |
| `linked_dependencies` | array of strings | IDs of related dependency entries |
| `linked_decisions` | array of strings | IDs of related decision entries |
| `reporter` | string | Who identified the risk |
| `proximity` | enum | Near (<2 weeks) \| Mid (2-8 weeks) \| Long (>8 weeks) |
| `triggers` | text | Early warning indicators |
| `last_reviewed` | date | Date of most recent review |
| `notes` | text | Date-stamped update log |

### 2.3 Inherent vs. Residual Risk Fields (Enterprise Mode)

For programs requiring formal inherent/residual tracking:

| Field | Type | Description |
|-------|------|-------------|
| `inherent_likelihood` | integer (1-5) | Likelihood before any controls |
| `inherent_impact` | integer (1-5) | Impact before any controls |
| `inherent_score` | integer | `inherent_likelihood × inherent_impact` |
| `inherent_rating` | enum | Rating band for inherent risk |
| `residual_likelihood` | integer (1-5) | Likelihood after current controls |
| `residual_impact` | integer (1-5) | Impact after current controls |
| `residual_score` | integer | `residual_likelihood × residual_impact` |
| `residual_rating` | enum | Rating band for residual risk |
| `risk_appetite` | enum | Acceptable residual rating threshold |
| `above_appetite` | boolean | `true` if residual_rating > risk_appetite |

---

## 3. Structured Risk Statement Format

Every risk entry MUST include a structured statement using one of these patterns:

### 3.1 If-Then-Because (Primary)

```
If [cause/event/condition],
then [impact on program objective],
because [underlying driver/mechanism].
```

**Example**:
> If we deploy the AI summarization model to 100% of enterprise tenants without shadow testing,
> then we risk a spike in critical support tickets and NPS drop,
> because the evaluation set under-samples long documents and we have no AI-specific on-call playbooks.

### 3.2 Condition-Event-Impact (Alternative)

```
There is a risk that [event] occurs
due to [condition/driver],
resulting in [impact on objectives].
```

### 3.3 ERM Quarterly Format (For Program-Level Risks)

```
In Q{X} FY{YY}, the {Domain} domain has a {current_rating} risk
that {short scenario},
with a target of {target_rating} by {date}.
Drivers & controls: {summary}
Impact & trajectory: {summary}
Change & ask: {what changed and what is needed}
```

### 3.4 Validation Rules

A valid risk statement must satisfy:
1. **Causal clause present**: Contains a triggering condition, event, or timeframe
2. **Impact references an objective**: Timeline, OKR, SLA, safety KPI, customer metric, or financial target
3. **Driver specified**: References underlying causes (e.g., "limited eval coverage", "vendor SLA gap", "no monitoring")
4. **Reject if**: Only describes cause OR only describes impact without connecting them

---

## 4. AI Risk Category Taxonomy

Six primary categories optimized for AI/ML program risk management, mapped to NIST AI RMF dimensions:

| # | Category | NIST AI RMF Mapping | Scope |
|---|----------|---------------------|-------|
| 1 | **Model Quality & Safety** | Validity & Reliability, Safety, Resilience | Accuracy, robustness, drift, adversarial attacks, hallucination, jailbreak, harmful output, explainability |
| 2 | **Data & Privacy** | Privacy, Data Governance | Training/eval data quality, PII exposure, telemetry retention, data residency, GDPR, unauthorized training data |
| 3 | **Infra, Performance & Cost** | (Operational risk) | GPU/compute capacity, token cost overruns, latency SLOs, scaling limits, pipeline reliability |
| 4 | **Vendor & Third-Party** | (Security & Compliance overlap) | LLM provider SLAs, plugin risks, incident sharing gaps, API rate limits, model deprecation |
| 5 | **Governance & Compliance** | Govern (NIST AI RMF) | Missing risk assessments, EU AI Act, ISO42001, documentation gaps, unclear ownership, audit readiness |
| 6 | **GTM, Customer & Product** | (People/Brand/Financial overlap) | Customer harm from AI errors, NPS impact, support volume spikes, adoption failure, reputation risk |

---

## 5. Lifecycle States

### 5.1 Risk Lifecycle

```
Identified → Assessed → In Mitigation → [Mitigated | Accepted | Closed]
                                    ↗ Escalated (at any point)
```

| Status | Description | Who Can Set |
|--------|-------------|-------------|
| **Identified** | Risk logged but not yet scored or assessed | AI (autonomous) |
| **Assessed** | Scored with likelihood/impact; category assigned | AI (autonomous for scoring) |
| **In Mitigation** | Active treatment plan in progress | AI (with confirmation) |
| **Mitigated** | Controls in place; residual risk at acceptable level | Human required |
| **Accepted** | Risk acknowledged; no further treatment planned | Human required (especially for High/Critical) |
| **Closed** | Risk no longer applicable (expired, avoided, resolved) | Human required |
| **Escalated** | Raised to higher tier for decision | AI proposes; human confirms |

### 5.2 Dependency Lifecycle

```
Draft → Logged → Committed → [Resolved | At Risk → Missed]
                                         → Closed
```

| Status | Description |
|--------|-------------|
| **Draft** | Dependency identified but not yet communicated |
| **Logged** | Formally recorded; awaiting commitment from responding team |
| **Committed** | Responding team has committed to a delivery date |
| **At Risk** | Commitment is in jeopardy (slippage signals) |
| **Missed** | Committed date has passed without delivery |
| **Resolved** | Dependency satisfied |
| **Closed** | No longer needed |

---

## 6. Scoring Mechanics

### 6.1 Score Calculation

```
score = likelihood × impact
```

### 6.2 Rating Band Mapping (5×5 Matrix)

| Score Range | Rating | Color | Action Required |
|-------------|--------|-------|-----------------|
| 1 | Insignificant | Grey | Monitor only |
| 2-4 | Low | Green | Monitor; no formal treatment needed |
| 5-9 | Medium | Yellow | Treatment plan recommended; owner can accept |
| 10-16 | High | Orange | Treatment plan required; Risk Group Owner must approve acceptance |
| 17-25 | Critical | Red | Must be treated or accepted by Accountable Executive |

### 6.3 Qualitative Descriptors

**Likelihood Scale**:
| Value | Label | Guidance |
|-------|-------|----------|
| 1 | Rare | Unlikely to occur; no recent precedent |
| 2 | Unlikely | Could occur but not expected; infrequent precedent |
| 3 | Possible | May occur; some evidence or precedent exists |
| 4 | Likely | Expected to occur; strong evidence or recent precedent |
| 5 | Almost Certain | Will almost certainly occur; currently manifesting |

**Impact Scale**:
| Value | Label | Timeline Impact | Customer Impact | Financial Impact |
|-------|-------|----------------|-----------------|------------------|
| 1 | Insignificant | <1 day delay | No noticeable effect | Negligible |
| 2 | Low | 1-3 day delay | Minor inconvenience | <$10K |
| 3 | Medium | 1-2 week delay | Degraded experience | $10K-$100K |
| 4 | High | 2-4 week delay | Significant disruption | $100K-$1M |
| 5 | Critical | >1 month delay or missed milestone | Major outage or safety concern | >$1M |

---

## 7. Snapshot Schema for Trend Tracking

Each weekly snapshot captures the full register state for delta computation:

```json
{
  "snapshot_date": "2026-04-27",
  "program": "AI Search Recommendations",
  "total_risks": 15,
  "by_rating": {"Critical": 1, "High": 3, "Medium": 7, "Low": 4},
  "by_category": {"Model Quality & Safety": 4, "Data & Privacy": 3, ...},
  "by_status": {"Identified": 2, "Assessed": 3, "In Mitigation": 6, ...},
  "risks": [
    {
      "id": "R-001",
      "title": "Model drift post-launch",
      "category_primary": "Model Quality & Safety",
      "likelihood": 4,
      "impact": 4,
      "score": 16,
      "rating": "High",
      "status": "In Mitigation",
      "owner": "jane.doe",
      "mitigation_summary": "Automated drift detection pipeline in progress",
      "due_date": "2026-05-15"
    }
  ],
  "dependencies": [...],
  "delta_vs_previous": {
    "new_risks": ["R-015"],
    "resolved_risks": ["R-003"],
    "changed_risks": [{"id": "R-007", "field": "rating", "before": "Medium", "after": "High"}],
    "active_high_critical_count": 4,
    "previous_high_critical_count": 3,
    "delta": "+1"
  }
}
```
