# Program Charter Templates for AI/ML Programs

Reference templates and structural guidance for creating program charters in an AI/ML context.
This knowledge block provides ready-to-use templates, ADF patterns, and AI/ML-specific
adaptations sourced from PMI, SAFe, and Atlassian internal best practices.

Related skill: `ai-tpm-program-management` (Workflow 2.1)

---

## 1. Canonical Program Charter Structure

Every program charter should contain these 10 sections in order:

### Section 1: Program Meta
```
| Field | Value |
|-------|-------|
| Program Title | [Name] |
| Sponsor(s) | [Executive sponsor name(s)] |
| Program Manager | [TPM/PgM name] |
| Timeframe | [Start] — [End] or [FY/Quarter range] |
| Current Status | Draft / Active / Complete / On Hold |
| Charter Approval Date | [Date] |
| Last Updated | [Date] |
```

### Section 2: Background & Context
- Short narrative (2-3 paragraphs) covering:
  - Current environment and prior work
  - Problem statement: who is affected, what's the impact
  - "Why now": urgency drivers, market context, strategic alignment
  - Link to strategy/thesis documents

### Section 3: Objectives, Goals & Success Metrics
- 3-5 outcome-focused objectives (not output-focused)
- Each objective paired with:
  - Measurable success metric
  - Current baseline
  - Target value and timeline
- Example format:
  ```
  Objective: Reduce AI Gateway p99 latency
  Metric: p99 latency (ms)
  Baseline: 450ms
  Target: <200ms by end of Q3
  ```

### Section 4: Scope
- **In Scope**: High-level deliverables, workstreams, target experiences
  - Group by quarter if timeline is known
- **Out of Scope**: Explicitly excluded capabilities, teams, or systems
- **Nice-to-Have**: Items addressed only if capacity allows

### Section 5: Timeline & Key Milestones
- 5-10 milestones with:
  - Milestone name
  - Target date
  - Definition of done (concrete, verifiable criteria)
  - Dependencies (if any)

### Section 6: Stakeholders, Roles & Responsibilities
```
| Role | Person | Responsibilities |
|------|--------|------------------|
| Sponsor | [Name] | Strategic direction, escalation, funding |
| Program Manager | [Name] | Day-to-day execution, coordination, reporting |
| Product Lead | [Name] | Requirements, prioritization, customer voice |
| Engineering Lead | [Name] | Technical direction, architecture, delivery |
| Data Science Lead | [Name] | Model development, evaluation, MLOps |
| Design Lead | [Name] | UX research, design specs, accessibility |
| Contributors | [Names] | Domain expertise, implementation |
| Informed | [Names/Groups] | Status updates, outcome communication |
```

### Section 7: Dependencies
```
| Dependency | Owner Team | What We Need | By When | Status |
|-----------|-----------|-------------|---------|--------|
| [System/Team] | [Team] | [Specific need] | [Date] | At Risk / On Track / Blocked |
```

### Section 8: Risks & Issues
```
| # | Risk Description | Severity | Probability | Mitigation | Owner |
|---|-----------------|----------|-------------|------------|-------|
| R1 | [Description] | High/Med/Low | High/Med/Low | [Plan] | [Name] |
```

### Section 9: Operating Model
- **Cadences**: List of recurring rituals with frequency, audience, and purpose
- **Communication**: Primary channels (Slack, Confluence, Atlas)
- **Decision-Making**: DACI framework reference, decision log location
- **Status Reporting**: Format, frequency, audience
- **Escalation Path**: When and how to escalate blockers

### Section 10: References & Links
- Strategy/thesis documents
- DACI decision register
- Jira project/epic links
- Atlas project link
- Related program charters
- Go/No-Go checklist (if applicable)

---

## 2. AI/ML-Specific Charter Additions

When chartering an AI/ML program, add these sections after the standard structure:

### Section 11: AI/ML Governance
- **Responsible AI**: Fairness, bias, transparency considerations
- **Model governance**: Review and approval process for model deployments
- **Data governance**: Privacy, lineage, retention policies
- **Evaluation framework**: Benchmark datasets, eval metrics, regression thresholds

### Section 12: MLOps & Infrastructure
- **Training infrastructure**: Compute requirements, training pipeline
- **Serving infrastructure**: Latency requirements, scaling strategy
- **Feature store**: Feature dependencies, data freshness requirements
- **Monitoring**: Model performance metrics, data drift detection

### Section 13: AI Risk Assessment
- **Model risk**: Hallucination, bias, safety concerns
- **Data risk**: Quality, availability, privacy compliance
- **Operational risk**: Model degradation, dependency on third-party models
- **Regulatory risk**: Compliance requirements (GDPR, AI Act, etc.)

---

## 3. SAFe Lean Business Case Integration

For portfolio-level AI initiatives, complement the charter with a Lean Business Case:

- **Hypothesis**: "We believe that [capability] will result in [outcome] for [users]"
- **Leading Indicators**: Early signals that validate the hypothesis (within 1-2 sprints)
- **MVP Definition**: Minimum viable scope to test the hypothesis
- **Analysis Summary**: Technical feasibility, data availability, model approach
- **Go/No-Go Criteria**: Explicit thresholds for continuing vs. pivoting

---

## 4. Auto-Population Mapping

When using TWG CLI to auto-populate charter fields:

| Charter Field | TWG Source | Command |
|--------------|-----------|---------|
| Title | Atlas project name or Jira epic summary | `twg projects get <id>` or `twg jira workitem get --id <KEY>` |
| Sponsor | Atlas project owner | `twg projects get <id>` → owner field |
| Timeframe | Atlas target dates or Jira fix version dates | `twg projects get <id>` → target dates |
| Goals | Linked Atlas goals/OKRs | `twg goals get <goal-id>` |
| Stakeholders | Atlas team members + Jira assignees | `twg teams get <team-id>` |
| Milestones | Jira epic target dates and versions | `twg context jira workitem <KEY> --depth 2` |
| Dependencies | Jira linked issues (blocks/blocked-by) | `twg context jira workitem <KEY> --depth 2` |
| Scope items | Child epics/stories under program | `twg context jira workitem <KEY> --depth 2` |

**Fields requiring human input** (cannot be auto-populated):
- Background & Context narrative
- Problem statement and "why now"
- Out-of-scope decisions
- Risk appetite statements
- Success metric baselines and targets
