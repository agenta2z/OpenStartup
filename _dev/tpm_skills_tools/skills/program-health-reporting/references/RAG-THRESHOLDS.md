# RAG Thresholds Reference

Complete threshold definitions for computing Red/Amber/Green health status across all program dimensions.

## 1. Schedule / Time

### Qualitative Rules
- **Green**: All key milestones on track; no critical-path impact
- **Amber**: 1-2 milestones slipping ≤1 week; mitigation plan exists and is being executed
- **Red**: Critical milestones missed by >1 week; critical path impacted; no viable recovery plan

### Numeric Thresholds
- **Schedule Performance Index (SPI) = EV / PV**
  - Green: SPI ≥ 0.95
  - Amber: 0.85 ≤ SPI < 0.95
  - Red: SPI < 0.85

### JQL Signals
```
# Count of slipping milestones
project in (<projects>) AND type = Epic AND duedate <= 7d AND status != Done

# Overdue items
project in (<projects>) AND duedate < now() AND status != Done
```

### Scoring Rules
- 0 slipping milestones → Green
- 1-2 slipping milestones with mitigation → Amber
- ≥3 slipping milestones OR any critical-path milestone slipping → Red

---

## 2. Scope / Delivery Progress

### Qualitative Rules
- **Green**: Scope stable; planned vs actual delivery within 5%; <5% unestimated work
- **Amber**: 5-15% scope change this sprint; some unestimated work; minor scope creep
- **Red**: >15% scope change; significant unplanned work displacing planned items

### JQL Signals
```
# Unestimated work in active sprint
project in (<projects>) AND sprint in openSprints() AND originalEstimate is EMPTY

# Scope additions this sprint (created after sprint start)
project in (<projects>) AND sprint in openSprints() AND created >= "<sprint_start_date>"

# Carry-over from previous sprint
project in (<projects>) AND sprint in closedSprints() AND status != Done AND resolution = Unresolved
```

### Scoring Rules
- Unestimated ratio = unestimated / total sprint items
  - <5% → Green, 5-15% → Amber, >15% → Red
- Scope change ratio = items added after sprint start / total sprint items
  - <10% → Green, 10-20% → Amber, >20% → Red
- Take worst of the two ratios

---

## 3. Budget / Cost

### Qualitative Rules
- **Green**: Variance within agreed threshold; no forecast overrun
- **Amber**: Early signs of variance; some scenarios show overrun but with clear mitigation
- **Red**: Confirmed or highly likely overrun vs approved budget

### Numeric Thresholds (EVM-based)
- **Cost Variance (CV%) = (EV - AC) / EV**
- **Cost Performance Index (CPI) = EV / AC**

| Status | CV% | CPI |
|--------|-----|-----|
| Green | |CV%| ≤ 5% | 0.95 ≤ CPI ≤ 1.05 |
| Amber | 5% < |CV%| ≤ 10% | 0.90 ≤ CPI < 0.95 |
| Red | |CV%| > 10% | CPI < 0.90 |

### Notes
- Budget data typically comes from external systems (Cognos, finance tools)
- If budget data unavailable, mark dimension as "Not assessed" with confidence: low
- Any Red budget status requires human confirmation before reporting

---

## 4. Quality / Reliability

### Qualitative Rules
- **Green**: Bug escape rate within target; SLOs met; test coverage stable or improving
- **Amber**: Bug rate trending up; coverage declining; SLO at risk but not breached
- **Red**: Critical bugs in production; SLO breached; error budget exhausted

### Numeric Thresholds
- **SLO Error Budget**:
  - Green: Error budget > 25% remaining
  - Amber: 0% < Error budget ≤ 25% remaining, or high burn rate (>3x normal)
  - Red: Error budget exhausted (≤0%) or steep burn (>17x) sustained

- **Bug Escape Rate** (bugs found in production / total bugs):
  - Green: ≤ 5%
  - Amber: 5-15%
  - Red: > 15% or any Sev-1 production bug

### Notes
- Quality signals may come from monitoring tools, CI/CD pipelines, or manual reporting
- Combine automated signals (if available) with Jira bug ticket analysis

---

## 5. Resources / WIP / Flow

### Qualitative Rules
- **Green**: WIP at or below limits; blocked items ≤ threshold; cycle time stable
- **Amber**: WIP over limit in 1-2 columns for >1 week; blocked items > threshold but mitigation active
- **Red**: Chronic WIP breach across multiple columns; many items blocked >48h; key people unavailable

### Numeric Thresholds
- **WIP Limit**: Target N per column (where N ≈ active team members)
  - Green: WIP ≤ limit in all columns
  - Amber: WIP > limit in 1-2 columns for >1 week
  - Red: WIP > limit in ≥3 columns or >2x limit in any column

- **Blocked Items**:
  - Green: ≤ 2 blocked items, none older than 48h
  - Amber: 3-5 blocked items, or any blocked > 48h with mitigation
  - Red: > 5 blocked items, or any blocked > 5 days without mitigation

### JQL Signals
```
# Current WIP
project in (<projects>) AND status = "In Progress"

# Blocked items with age
project in (<projects>) AND status = Blocked

# Items blocked > 48h
project in (<projects>) AND status = Blocked AND status changed TO Blocked BEFORE -2d
```

---

## 6. Stakeholder / Customer Satisfaction

### Qualitative Rules
- **Green**: Sentiment ≥ 4/5 and stable/improving; no escalations
- **Amber**: Sentiment 3/5 or declining ≥1 point; minor escalations
- **Red**: Sentiment ≤ 2/5; repeated severe escalations; open Sev-1 incident

### Notes
- Stakeholder sentiment typically comes from surveys, meeting notes, or CX systems
- If sentiment data unavailable, assess qualitatively from recent communications
- Any Red stakeholder status for a strategic customer requires human confirmation

---

## 7. Overall RAG Computation

### Algorithm
```
1. Compute individual RAG for each assessed dimension
2. overall_status = max(all_dimensions) where Red > Amber > Green
3. EXCEPTION: If exactly ONE dimension is Amber AND:
   - Documented mitigation exists AND
   - All other dimensions are Green AND
   - Amber dimension is not worsening
   → overall_status may be Green with confidence: "medium"
4. Set confidence based on data completeness:
   - All sources returned data → "high"
   - Some sources missing/stale → "medium"
   - Major data gaps → "low"
```

### Output Schema
```json
{
  "program_id": "<program_key>",
  "timestamp": "<ISO8601>",
  "status_overall": "green|amber|red",
  "status_schedule": "green|amber|red",
  "status_scope": "green|amber|red",
  "status_budget": "green|amber|red|not_assessed",
  "status_quality": "green|amber|red|not_assessed",
  "status_resources": "green|amber|red",
  "status_stakeholder": "green|amber|red|not_assessed",
  "confidence": "high|medium|low",
  "rationale": "<2-3 sentence summary>",
  "exceptions": [
    {
      "type": "state_change|new_blocker|milestone_slip|wip_overload",
      "dimension": "<dimension>",
      "description": "<what changed>",
      "severity": "high|medium|low"
    }
  ]
}
```

## 8. Alert Filtering (Exception-Based)

To prevent alert fatigue, only surface exceptions that represent meaningful change:

### Alert Rules
- **Alert immediately**: Any transition TO Red
- **Include in next digest**: Any transition Green↔Amber, or new blockers
- **Do NOT alert**: Stable state (same RAG as previous scan), minor metric fluctuations within threshold band
- **Cooldown**: After alerting on a Red status, do not re-alert for same dimension for 4 hours unless status worsens further
- **Batch**: If >3 exceptions in one scan, batch into a single digest message rather than individual alerts
