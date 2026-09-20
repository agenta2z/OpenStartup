# Quality Metrics for TPM Artifacts

Reference material for measuring the quality of AI-generated TPM artifacts (status reports, charters, escalations, RAID entries). Covers rubric-based evaluation, composite scoring, and feedback loop patterns.

## 1. Artifact Quality Evaluation Framework

### 1.1 Core Pattern: Multi-Dimension Rubric Scoring

Every TPM artifact is evaluated against orthogonal quality dimensions using a 0-10 scale. This avoids subjective single-score assessments and enables targeted improvement.

**Principle**: Break "quality" into 3-5 measurable dimensions per artifact type. Score each independently, then compute a weighted composite.

### 1.2 Per-Artifact Rubric Definitions

#### Status Report Quality Score

| Dimension | Weight | 0-3 (Poor) | 4-6 (Adequate) | 7-9 (Good) | 10 (Excellent) |
|-----------|--------|-----------|----------------|------------|----------------|
| **Relevance** | 0.25 | Covers wrong period or irrelevant topics | Mostly relevant with some tangents | Focused on current period and goals | Precisely targeted to audience and timeframe |
| **Completeness** | 0.25 | Missing major sections or workstreams | Key sections present but thin | All required sections with substantive content | Comprehensive coverage with supporting data |
| **Risk Clarity** | 0.25 | Risks vague or missing | Risks listed but lacking detail | Risks specific with owners and mitigation | Risks time-bounded, quantified, with clear escalation path |
| **Decision-Readiness** | 0.25 | No clear asks or next steps | Asks present but ambiguous | Clear asks with options and deadlines | Fully actionable with recommendation and evidence |

**Composite**: StatusQuality = 0.25*Relevance + 0.25*Completeness + 0.25*RiskClarity + 0.25*DecisionReadiness

**Target**: Team-level >= 6.0; Exec-level >= 7.5

#### Charter Quality Score

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Strategic Alignment** | 0.20 | Objectives clearly linked to OKRs/strategy |
| **Scope Precision** | 0.25 | In/out/nice-to-have boundaries are clear and specific |
| **Measurability** | 0.20 | Success metrics are quantitative and verifiable |
| **Completeness** | 0.20 | All required charter sections present and substantive |
| **Governance Clarity** | 0.15 | Decision framework, cadence, and escalation paths defined |

**Target**: >= 7.0 before approval gate

#### Escalation Quality Score

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Context Sufficiency** | 0.25 | Problem clearly stated with timeline and evidence |
| **Impact Quantification** | 0.25 | Impact measured in concrete terms (days, users, dollars) |
| **Options and Tradeoffs** | 0.30 | 2-3 options with pros/cons and feasibility assessment |
| **Clear Ask** | 0.20 | Specific request with deadline and decision-maker identified |

**Target**: >= 8.0 (escalations are high-stakes)

#### RAID Entry Quality Score

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Specificity** | 0.30 | Entry describes a concrete, distinct item (not vague category) |
| **Completeness** | 0.30 | All required fields populated (severity, likelihood, owner, mitigation) |
| **Actionability** | 0.25 | Mitigation or response is concrete with timeline |
| **Data Linkage** | 0.15 | Connected to evidence (Jira issues, Confluence pages, metrics) |

**Target**: >= 6.0 for all entries; >= 8.0 for Critical/High severity

## 2. Planning Hygiene Index (PHI)

### 2.1 Purpose

A single composite score (0-100) that captures planning quality across a program or portfolio. Used for trend monitoring and cross-program comparison.

### 2.2 Dimensions and Weights

| Dimension | Weight | Measurement |
|-----------|--------|-------------|
| **Dependency Coverage** | 0.25 | % of identified dependencies with owners and due dates |
| **Milestone Coherence** | 0.20 | % of milestones with clear criteria, realistic dates, and no conflicts |
| **Resource Alignment** | 0.15 | % of workstreams with confirmed resource allocation |
| **RAID Linkage** | 0.20 | % of RAID items linked to Jira issues with active mitigation |
| **Status Currency** | 0.20 | % of tracked items updated within defined cadence (7 days) |

### 2.3 Calculation

```
PHI = (
  0.25 * (deps_with_owners / total_deps) +
  0.20 * (coherent_milestones / total_milestones) +
  0.15 * (resourced_workstreams / total_workstreams) +
  0.20 * (linked_raid_items / total_raid_items) +
  0.20 * (recently_updated / total_tracked)
) * 100
```

### 2.4 Thresholds

| PHI Score | Health | Action |
|-----------|--------|--------|
| 80-100 | Green | Maintain cadence |
| 60-79 | Amber | Review gaps, assign remediation owners |
| 40-59 | Red | Escalate to SteerCo, dedicated planning sprint |
| 0-39 | Critical | Program pause for re-planning recommended |

## 3. Structural Validation Checks

Before applying rubric scoring, validate structural requirements:

### 3.1 Status Report Structural Checks
- [ ] Executive summary present and <= 150 words
- [ ] RAG status explicitly stated (Green/Amber/Red)
- [ ] At least 3 highlights with quantified impact
- [ ] At least 3 risks with owner and mitigation
- [ ] Forward-looking section present
- [ ] No more than 7 bullets per section
- [ ] All dates are valid and in the future (for forward-look)

### 3.2 Charter Structural Checks
- [ ] All 12 required sections present (per charter template)
- [ ] 3-5 objectives with measurable success criteria
- [ ] In-scope, out-of-scope, and nice-to-have sections non-empty
- [ ] At least 5 milestones with target dates
- [ ] DACI/RACI table populated
- [ ] Governance cadence defined with frequencies

### 3.3 RAID Entry Structural Checks
- [ ] Type field is one of: Risk, Issue, Assumption, Dependency
- [ ] Severity assigned from allowed values
- [ ] Likelihood assigned (for Risks)
- [ ] Owner is a named individual (not a team)
- [ ] Status is a valid lifecycle state

## 4. Feedback Loop Patterns

### 4.1 Risk Flag Precision/Recall Tracking

For AI-generated risk flags, track accuracy over time:

| Metric | Definition | Target |
|--------|-----------|--------|
| **True Positive (TP)** | AI flagged risk, human confirmed as valid | Maximize |
| **False Positive (FP)** | AI flagged risk, human determined not valid | Minimize (<20%) |
| **False Negative (FN)** | AI missed risk, human identified later | Minimize (<10%) |
| **Precision** | TP / (TP + FP) | >= 0.80 |
| **Recall** | TP / (TP + FN) | >= 0.90 |

**Feedback workflow**:
1. AI flags risk -> human reviews via `confirmation`
2. If human rejects: log as FP with reason -> AI learns adjustment
3. If human identifies missed risk: log as FN -> AI adjusts scanning thresholds
4. Weekly: compute precision/recall from recent 30-day window
5. If precision < 0.80: tighten detection thresholds (reduce false alarms)
6. If recall < 0.90: broaden scanning scope (catch more true risks)

### 4.2 Artifact Revision Tracking

Track how often human modifies AI-generated artifacts:

| Metric | Description | Target |
|--------|-------------|--------|
| **First-pass acceptance rate** | % of artifacts approved without changes | >= 60% |
| **Average revision rounds** | Mean number of confirmation rejections before approval | <= 1.5 |
| **Section-level edit rate** | Which sections humans modify most often | Use to prioritize improvement |

### 4.3 Continuous Improvement Cycle

1. **Collect**: Track confirmation outcomes, human edits, risk flag accuracy
2. **Analyze**: Monthly review of quality metrics and feedback data
3. **Adjust**: Update templates, scoring thresholds, scanning parameters
4. **Validate**: Compare metrics before/after adjustments

## 5. Persona-Specific Quality Expectations

| Persona | Primary Artifact | Key Quality Dimension | Minimum Score |
|---------|-----------------|----------------------|---------------|
| **Team/Squad** | Task-level updates, sprint status | Clarity, Actionability | 6.0 |
| **Program/Portfolio** | Weekly status, RAID register | Completeness, Risk Clarity | 7.0 |
| **Executive** | SteerCo pre-read, escalation | Decision-Readiness, Impact Quantification | 8.0 |

## 6. Related Skills and Tools

- **ai-tpm skill**: Quality metrics apply to all artifact generation in SOPs 1-3
- **Knowledge block: raid-methodology.md**: RAID entry quality scoring uses severity/likelihood from RAID methodology
- **Knowledge block: governance-gates.md**: Gate evidence completeness feeds into Planning Hygiene Index
- **confirmation tool**: Primary mechanism for collecting human feedback on artifact quality
