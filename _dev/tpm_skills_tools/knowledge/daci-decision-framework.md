# DACI Decision Framework for AI/ML Programs

Comprehensive reference for implementing the DACI (Driver, Approver, Contributor, Informed)
decision-making framework in AI/ML program contexts. Includes templates, anti-patterns,
and integration guidance for Confluence-based decision logs.

Related skill: `ai-tpm-program-management` (Workflow 2.2)

---

## 1. DACI Role Definitions

| Role | Symbol | Count | Responsibility |
|------|--------|-------|---------------|
| **Driver** | D | Exactly 1 | Drives the decision to resolution. Frames the problem, gathers input from Contributors, synthesizes options, ensures the Approver has what they need to decide, and communicates the outcome to Informed. |
| **Approver** | A | Exactly 1 | Has final decision authority. Reviews options, makes the call, and is accountable for the outcome. Should be the person with the most relevant context and authority. |
| **Contributor** | C | 2-6 typical | Provides expertise, analysis, and input. May advocate for options but does not have decision authority. Should represent diverse perspectives (technical, product, design, ops). |
| **Informed** | I | As needed | Needs to know the decision outcome and rationale. Does not participate in the decision process but may be impacted by the result. |

---

## 2. When to Use DACI

**Always use DACI for**:
- Cross-team architectural decisions (e.g., "which database for the feature store?")
- Scope changes affecting multiple teams or timelines
- Technology selection (vendor, framework, model provider)
- Process or SOP changes affecting multiple teams
- Resource allocation decisions (headcount, compute, budget)
- Go/No-Go decisions for launches or migrations
- AI/ML-specific: model selection, training data decisions, evaluation criteria changes

**Skip DACI for**:
- Day-to-day implementation choices within a single team
- Decisions already covered by established SOPs or policies
- Trivial or easily reversible decisions
- Decisions with a single obvious owner and no cross-team impact

---

## 3. Decision Record Template

### Confluence Page Structure

```
# DACI: [Decision Title]

## Status: [Proposed | In Progress | Decided | Revisit]

## Meta
| Field | Value |
|-------|-------|
| Decision ID | DACI-[NNN] |
| Date Opened | [YYYY-MM-DD] |
| Decision Due | [YYYY-MM-DD] |
| Date Decided | [YYYY-MM-DD] |
| Program | [Program name] |
| Related Jira | [PROJ-123] |

## DACI Roles
| Role | Person |
|------|--------|
| Driver (D) | @[name] |
| Approver (A) | @[name] |
| Contributors (C) | @[name1], @[name2], @[name3] |
| Informed (I) | @[name1], @[name2], [team-name] |

## Context
[2-3 paragraphs: What is the decision about? Why does it matter?
What is the impact of not deciding? What constraints exist?]

## Options Considered

### Option 1: [Name]
- **Description**: [What this option entails]
- **Pros**: [Benefits]
- **Cons**: [Drawbacks]
- **Cost/Effort**: [Estimate]
- **Risk**: [Key risks]

### Option 2: [Name]
- **Description**: ...
- **Pros**: ...
- **Cons**: ...
- **Cost/Effort**: ...
- **Risk**: ...

### Option 3: [Name] (if applicable)
...

## Recommendation
[Driver's recommendation with rationale, based on Contributor input]

## Decision
[Approver's final decision with rationale. Filled in after decision is made.]

## Action Items
| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
| 1 | [Next step] | @[name] | [date] | To Do |
| 2 | [Next step] | @[name] | [date] | To Do |
```

---

## 4. DACI Process Flow

```
1. IDENTIFY    → Driver identifies need for decision, creates DACI page
2. FRAME       → Driver defines options, gathers initial data
3. CONSULT     → Driver solicits input from Contributors (async or sync)
4. SYNTHESIZE  → Driver synthesizes options, writes recommendation
5. DECIDE      → Approver reviews and makes the call
6. COMMUNICATE → Driver communicates outcome to Informed parties
7. EXECUTE     → Action items are assigned and tracked
8. ARCHIVE     → Decision record is finalized and stored in knowledge base
```

**Recommended timeline by urgency**:
- Routine decisions: 1-2 weeks
- Important decisions: 1 week
- Urgent decisions: 24-48 hours
- Emergency decisions: Same day (can skip Contributor phase, document retroactively)

---

## 5. Anti-Patterns and Mitigations

| Anti-Pattern | Problem | Mitigation |
|-------------|---------|------------|
| **Multiple Approvers** | Decision by committee; no one is accountable | Enforce single Approver rule; if consensus needed, make it explicit in process |
| **Driver = Approver** | Conflicts of interest; rubber-stamping | Separate roles; Driver recommends, Approver decides |
| **No deadline** | Decision drifts indefinitely | Always set a "decide by" date; escalate if missed |
| **Skipping options analysis** | Poor decision quality; hindsight regret | Require minimum 2 options with pros/cons |
| **Phantom Contributors** | Listed but never consulted | Set explicit input deadline; follow up with Contributors |
| **Invisible decisions** | Made in Slack DMs, never documented | Enforce "if it's not in the decision log, it's not decided" |
| **Revisit without trigger** | Re-litigating decided issues | Define explicit "revisit triggers" (new data, context change) |

---

## 6. AI/ML-Specific Decision Considerations

When DACI is used for AI/ML decisions, add these evaluation criteria:

### Model Selection Decisions
- Accuracy/performance benchmarks across evaluation datasets
- Latency and throughput requirements
- Cost per inference/training
- Responsible AI assessment (bias, fairness, safety)
- Licensing and data usage restrictions
- Vendor lock-in risk

### Data Decisions
- Privacy and compliance implications (GDPR, CCPA)
- Data quality and freshness requirements
- Labeling costs and timeline
- Bias in training/evaluation data
- Data lineage and provenance

### Infrastructure Decisions
- Scalability requirements (current and projected)
- Operational complexity and team capability
- Cost trajectory (especially GPU/compute)
- Migration effort from current state
- Integration with existing MLOps pipeline

---

## 7. Harvesting Decisions from Slack

When a decision is made informally in Slack, use this workflow to formalize it:

1. **Search** for decision signals:
   ```
   slack_search_messages "decided OR approved OR agreed OR go with in:#<channel>" --count 20
   ```

2. **Expand** the decision thread:
   ```
   slack_get_thread <channel-id> <message-ts>
   ```

3. **Extract** key elements:
   - Who proposed? (Driver candidate)
   - Who approved or gave final word? (Approver candidate)
   - Who provided input? (Contributors)
   - What options were discussed?
   - What was the final decision?

4. **Create** a retroactive DACI record in Confluence with the template above.

5. **Persist** in knowledge base:
   ```
   kn add "DACI: <title>. Decision: <outcome>. Source: <slack-permalink>." --space decisions --tags daci
   ```

---

## 8. Decision Log Index Page

Maintain a parent page in Confluence as a decision log index:

```
# Decision Log: [Program Name]

| ID | Decision | Status | Approver | Date | Link |
|----|----------|--------|----------|------|------|
| DACI-001 | Database selection for feature store | Decided | @CTO | 2026-03-15 | [Link] |
| DACI-002 | Model serving architecture | In Progress | @Eng Lead | TBD | [Link] |
| DACI-003 | Evaluation framework v2 | Proposed | @ML Lead | 2026-04-30 | [Link] |
```

This index should be:
- Linked from the program charter (Section 9: Operating Model)
- Updated automatically when new DACI pages are created
- Reviewed in monthly program reviews
