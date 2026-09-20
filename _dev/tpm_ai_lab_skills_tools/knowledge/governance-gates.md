# Governance Gates for Technical Programs

Reference material for governance gate models, gate criteria checklists, and decision-making frameworks used by the AI TPM role. Covers the standard 6-gate lifecycle, DACI decision framework, and SteerCo operating patterns.

## 1. Standard Gate Sequence (6-Gate Model)

### 1.1 Gate Overview

| Gate | Name | Purpose | Typical Timing |
|------|------|---------|----------------|
| G0 | **Initiation** | Authorize exploration; confirm strategic alignment | Program kickoff |
| G1 | **Discovery Complete** | Validate problem definition, feasibility, and approach | End of discovery phase |
| G2 | **Design Approved** | Approve solution architecture, scope commitment, resource plan | End of design phase |
| G3 | **Build/MVP Ready** | Confirm build readiness, pilot criteria, risk posture acceptable | Pre-build or pre-pilot |
| G4 | **Launch/GA Ready** | Validate launch criteria met, operational readiness confirmed | Pre-launch |
| G5 | **Closure** | Confirm benefits realized, lessons captured, resources released | Post-launch stabilization |

### 1.2 Gate Criteria Checklists

#### G0 — Initiation Gate
- [ ] Program charter drafted and reviewed
- [ ] Strategic alignment confirmed (linked to OKR or portfolio goal)
- [ ] Executive sponsor identified and committed
- [ ] Initial scope boundaries defined (in/out/nice-to-have)
- [ ] Key stakeholders identified
- [ ] Initial RAID log created with known risks and dependencies
- [ ] Governance model and cadence proposed
- [ ] Resource needs estimated at high level

#### G1 — Discovery Complete
- [ ] Problem statement validated with data/user research
- [ ] Feasibility assessment completed (technical, operational, financial)
- [ ] 2-3 solution approaches evaluated with pros/cons
- [ ] Recommended approach selected with rationale documented
- [ ] Detailed scope definition refined
- [ ] RAID log updated with discovery findings
- [ ] Success metrics finalized and measurable
- [ ] Dependency map created with timelines

#### G2 — Design Approved
- [ ] Solution architecture documented and reviewed
- [ ] Technical design artifacts complete (system design, API specs, data model)
- [ ] Scope committed — in-scope items locked, out-of-scope confirmed
- [ ] Resource plan finalized (team composition, allocation, timeline)
- [ ] Detailed project plan with milestones and sprint mapping
- [ ] RAID register fully populated with mitigations
- [ ] Integration points and contracts defined with dependent teams
- [ ] Quality criteria and test strategy defined

#### G3 — Build/MVP Ready
- [ ] Core functionality implemented and unit tested
- [ ] Integration testing complete for critical paths
- [ ] Pilot/MVP criteria defined and acceptance thresholds set
- [ ] Operational runbooks drafted
- [ ] Monitoring and alerting configured
- [ ] Security review completed (if applicable)
- [ ] Data migration plan validated (if applicable)
- [ ] Rollback plan documented

#### G4 — Launch/GA Ready
- [ ] All launch criteria met (functional, performance, security)
- [ ] Load/stress testing completed with acceptable results
- [ ] Documentation complete (user docs, API docs, ops runbooks)
- [ ] Support team trained and ready
- [ ] Communication plan executed (release notes, stakeholder notifications)
- [ ] Rollback procedure tested
- [ ] Monitoring dashboards operational
- [ ] Post-launch support plan in place

#### G5 — Closure Gate
- [ ] Benefits tracking data collected and analyzed
- [ ] Success metrics evaluated against targets
- [ ] Lessons learned / retrospective completed
- [ ] Outstanding RAID items resolved or transferred
- [ ] Knowledge artifacts archived (decision log, RAID, status history)
- [ ] Resources released and reallocated
- [ ] Improvement actions logged for future programs
- [ ] Final stakeholder communication sent

## 2. Gate Decision Outcomes

Each gate review produces one of four outcomes:

| Outcome | Meaning | Next Action |
|---------|---------|-------------|
| **Go** | All criteria met, proceed to next phase | Advance to next phase, communicate decision |
| **Conditional Go** | Most criteria met, minor gaps with clear remediation plan | Proceed with conditions; track remediation as action items |
| **No-Go** | Significant gaps or risks that must be addressed | Return to current phase, create remediation plan, re-schedule gate |
| **Kill** | Program no longer viable or strategically aligned | Initiate closure process, release resources, communicate decision |

**AI TPM Role**: The AI can collect evidence and assess completeness, but the Go/No-Go/Kill decision is always Tier 3 (human-only). The AI presents a gate readiness assessment with evidence matrix and recommendation.

## 3. DACI Decision Framework

### 3.1 Roles

| Role | Definition | Count | Responsibility |
|------|-----------|-------|----------------|
| **Driver** | Owns the decision process | Exactly 1 | Frames options, drives to resolution, documents outcome |
| **Approver** | Makes the final call | 1 (rarely 2) | Reviews options, selects decision, accountable for outcome |
| **Contributors** | Provide input and expertise | Multiple | Share data, analysis, recommendations; not decision-makers |
| **Informed** | Need to know the outcome | Multiple | Receive decision notification; no input required |

### 3.2 Decision Log Template

For each program decision, log:

| Field | Description |
|-------|-------------|
| Decision ID | Sequential: DEC-001, DEC-002, etc. |
| Date | When the decision was made |
| Title | Short descriptive title |
| Context | Background and why this decision was needed |
| Options Considered | 2-3 options with pros/cons |
| Decision | Which option was selected |
| Rationale | Why this option was chosen |
| Driver | Who drove the decision process |
| Approver | Who approved the decision |
| Contributors | Who provided input |
| Informed | Who was notified |
| Impact | What changes result from this decision |
| Reversibility | Easy / Hard / Irreversible |

### 3.3 AI TPM Decision Logging Workflow

1. Before governance meeting: AI frames decision with options (Tier 2 — confirm framing)
2. During/after meeting: AI captures decision outcome
3. Post-meeting: AI logs to Confluence decision page, updates Jira, stores in KB
4. Distribution: AI notifies Informed parties via Slack

## 4. Steering Committee (SteerCo) Operating Model

### 4.1 Composition
- Executive Sponsor (chair)
- Program Manager / TPM
- Workstream Leads (2-5)
- Key functional stakeholders (PM, Eng, Design, etc.)
- Guest SMEs as needed

### 4.2 Meeting Cadence and Agenda

**Frequency**: Monthly (or bi-weekly for high-risk programs)

**Standard Agenda**:
1. Program health summary — RAG status with evidence (5 min)
2. Progress against milestones — completed, in-progress, at-risk (10 min)
3. Top risks and issues — sorted by severity, with mitigation status (10 min)
4. Decisions needed — framed with options and recommendation (15 min)
5. Dependencies and help needed — explicit asks with owners (5 min)
6. Forward look — next 4-12 weeks key activities and milestones (5 min)
7. Action items — captured with owners and due dates (5 min)

### 4.3 AI TPM Preparation Workflow

1. **T-3 days**: Begin gathering data (Jira queries, RAID review, Atlas goal status)
2. **T-2 days**: Draft pre-read document with RAG summary, risks, decisions
3. **T-1 day**: Present pre-read via `confirmation` for TPM review and adjustments
4. **T-0**: Distribute pre-read via Slack to SteerCo channel
5. **T+0**: During/after meeting, capture decisions and action items
6. **T+1 day**: Log decisions, create follow-up Jira tasks, update RAID, send meeting notes

## 5. Related Skills and Tools

- **ai-tpm skill**: SOP 3 (Governance Review and Gate Management) implements gate tracking and SteerCo workflows
- **twg tool**: Confluence pages for gate evidence, Jira for action tracking, Atlas for goal alignment
- **confirmation tool**: Required for gate pass/fail recommendations and decision framing
- **Knowledge block: raid-methodology.md**: RAID register is primary input for gate evidence assessment
