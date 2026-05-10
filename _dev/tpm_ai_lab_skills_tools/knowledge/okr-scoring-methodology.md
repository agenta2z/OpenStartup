# OKR Scoring Methodology Reference

A reference guide for OKR (Objectives and Key Results) scoring methodology as implemented in Atlassian's Atlas/Goals platform. Covers scoring scales, rollup methods, status thresholds, and scoring patterns for different KR types.

## 1. KR Scoring Scale

All Key Results (called "Success Measures" in Atlas) are scored on a **0.0 to 1.0 scale**:

| Score Range | Status | Visual | Meaning |
|-------------|--------|--------|---------|
| 0.7 – 1.0 | On Track | 🟢 Green | Expected to achieve the KR |
| 0.4 – 0.69 | At Risk | 🟡 Yellow | Some risk, needs attention |
| 0.0 – 0.39 | Off Track | 🔴 Red | Significant risk of missing the KR |

### Sources
- Focus goal scoring documentation
- Atlassian OKR Foundations guide
- "Use goal status to track objectives and key results" documentation

---

## 2. Rollup Methods

### 2.1 Equal-Weighted Average (Default)

The canonical and recommended rollup method per Atlassian's DACI on goal rollups:

```
Objective Score = (KR₁ score + KR₂ score + ... + KRₙ score) / n
```

**Key rules:**
- Only **directly attached** KRs/success measures roll into the score
- **Sub-goals/child goals are NOT used** for numeric rollup by default
- This aligns with Atlassian's DACI recommendation: "rollup direct KRs only" with equal weighting

**When to use:** Default for all goals unless explicit weights are configured.

### 2.2 Weighted Average

Some organizations assign different importance to KRs:

```
Objective Score = Σ (weight_i × KR_i score)
where Σ weight_i = 1.0
```

**Weight types:**
- **Ratio weights**: Direct fractional weights (e.g., 0.4, 0.3, 0.3)
- **Point weights**: Points per KR, normalized to ratios (e.g., 40/30/30 points → 0.4/0.3/0.3)

**When to use:** Only when explicit weights are defined in the goal configuration. Never infer or assign weights autonomously.

**Handling missing weights:**
If some KRs have weights but others don't:
1. Option A: Prompt the user to supply missing weights
2. Option B: Normalize known weights and distribute remaining weight equally across unweighted KRs — **requires human confirmation**

### 2.3 Portfolio/PI Roll-Up

For aggregating across multiple objectives (e.g., for a portfolio view or PI review):

```
Portfolio Score = average(Objective₁ score, Objective₂ score, ..., Objectiveₙ score)
```

This matches Jira Align's OKR heatmap calculation: objective score = average of KR scores, portfolio score = average of objective scores.

---

## 3. KR Scoring Patterns by Type

### 3.1 Metric-Backed KRs (Quantitative)

KRs with measurable targets (e.g., "Improve latency by 20%", "Reach 1000 DAUs"):

```
KR Score = min(1.0, current_value / target_value)
```

**For improvement targets** (e.g., "Reduce by X%"):
```
KR Score = min(1.0, actual_improvement / target_improvement)
```

**For composite metrics** (e.g., Weighted QSR):
```
Composite Score = Σ (component_metric × component_weight)
KR Score = min(1.0, composite_score / target_composite_score)
```

### 3.2 Milestone-Backed KRs (Delivery)

KRs tied to delivery milestones:

```
KR Score = completed_milestones / total_milestones
```

**With time-weighting** (accounts for whether milestones are on schedule):
```
on_time_bonus = 0.1 if all completed milestones were on time
KR Score = min(1.0, (completed / total) + on_time_bonus)
```

### 3.3 Binary KRs (Yes/No)

KRs that are either achieved or not (e.g., "Launch feature X"):

```
KR Score = 1.0 if achieved, 0.0 if not achieved
```

**Mid-cycle scoring for binary KRs:**
- Use milestone progress toward the binary outcome
- Or use judgment mapping: On Track = 0.8, At Risk = 0.5, Off Track = 0.2

### 3.4 Judgment-Backed KRs (Qualitative)

KRs without quantitative targets that rely on human assessment:

```
On Track   → 0.8
At Risk    → 0.5
Off Track  → 0.2
Not Started → 0.0
```

These scores are **recommendations** — the human owner should confirm or adjust.

---

## 4. Scorecard-to-KR Mapping

When program health scorecard dimensions (schedule, scope, quality, risk) map to specific KRs:

### Mapping Pattern

```yaml
kr_mappings:
  - kr_id: "KR-1: Deliver milestone on time"
    scorecard_dimensions: [schedule]
    scoring_rule: "Use schedule_score / 100"

  - kr_id: "KR-2: Maintain quality bar"
    scorecard_dimensions: [quality]
    scoring_rule: "Use quality_score / 100"

  - kr_id: "KR-3: Ship all planned scope"
    scorecard_dimensions: [scope]
    scoring_rule: "Use scope_score / 100"
```

### Health Score to KR Score Conversion

```
health_dimension_score (0-100) → KR score (0.0-1.0):
  KR Score = health_dimension_score / 100
```

---

## 5. Atlas Update Structures

### 5.1 Tweet-Length Update (≤280 characters)

The primary Atlas update field. Must be concise and actionable:

```
[STATUS_EMOJI] [Program/Goal Name]: [One-line health summary]

Examples:
🟢 Platform Migration: On track — Phase 2 data migration complete, Phase 3 starting next week
🟡 Auth Redesign: At risk — dependency on IdP team delayed 1 week. Mitigation plan in place
🔴 Search Quality: Off track — P0 regression in ranking. Go-to-green: hotfix ETA Wed
```

### 5.2 Detailed Update Structure

The "More details" section follows this canonical structure:

```markdown
## Progress & Accomplishments
- [Completed item with link to Jira issue/epic]
- [Key metric change: "Latency improved from Xms to Yms (target: Zms)"]

## Risks & Constraints
- [SEVERITY] [Risk description] — Owner: [name], Mitigation: [action], ETA: [date]

## Next Steps (Next 1-2 Weeks)
- [Planned deliverable with target date]
- [Dependency that needs resolution]

## Scorecard Summary (optional, for programs)
| Dimension | Score | Status | Trend |
|-----------|-------|--------|-------|
| Schedule  | N/100 | 🟢/🟡/🔴 | ↑/→/↓ |
| ...       | ...   | ...    | ...   |

## Go-To-Green Actions (required if At Risk / Off Track)
1. [Specific action] — Owner: [name], Target: [date]
2. [Specific action] — Owner: [name], Target: [date]
```

### 5.3 Update Frequency Guidelines

| Context | Recommended Frequency | Notes |
|---------|----------------------|-------|
| Active program (Make phase) | Weekly | During active development |
| Planning phase (Wonder/Explore) | Bi-weekly | Less frequent during discovery |
| Stable/maintenance (Impact/Cleanup) | Monthly | Lower cadence when stable |
| At Risk or Off Track | Weekly minimum | Increased visibility needed |
| Quarterly OKR review | End of quarter | Comprehensive scoring and narrative |

---

## 6. Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Correct Approach |
|-------------|---------------|-----------------|
| Auto-computing goal status from Jira % complete | Atlas separates delivery from outcomes. A 100% complete epic doesn't mean the goal is achieved | Use Jira data as signal, human confirms goal status |
| Rolling up sub-goal scores into parent goals | DACI recommendation is KR-only rollup | Only aggregate direct KRs/success measures |
| Assigning KR weights without explicit config | Weights affect scoring methodology | Default to equal-weighted; require human confirmation for weighted |
| Scoring binary KRs as 0 until complete | Provides no mid-cycle visibility | Use milestone progress or judgment mapping |
| Averaging scores when KR data is missing | Distorts the aggregate | Exclude missing KRs, report "N of M KRs scored", flag gaps |
| Publishing scores without human review | Goal scores are human-curated in Atlas | Always present as recommendation, confirm before writing |

---

## 7. Related Skills and Tools

- **Skill: `program-health-scoring`** — Implements these scoring methods in operational workflows
- **Skill: `cross-system-reconciliation`** — Validates score consistency across systems
- **Knowledge: `cross-system-field-mapping`** — Maps the underlying fields used for scoring
- **Tool: `twg`** — Primary tool for fetching goal and KR data
- **Tool: MCP Atlas Goal tools** — For individual goal/KR lookups and update retrieval
