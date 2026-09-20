# AI TPM RAG Health Framework

Domain knowledge for implementing Red/Amber/Green (RAG) health status reporting in AI/ML program management contexts.

## What This Covers

This knowledge block captures the domain conventions, terminology, and decision frameworks that an AI Technical Program Manager needs when assessing and reporting program health. It complements the `program-health-reporting` skill by providing background context rather than operational procedures.

## RAG Status Semantics

Across Atlassian tools and industry practice, RAG status follows consistent semantics:

| Status | Label | Meaning |
|--------|-------|---------|
| 🟢 Green | On Track | Within agreed thresholds; no material risk to objectives |
| 🟡 Amber | At Risk | Emerging or contained risk; recoverable without major re-plan if acted on |
| 🔴 Red | Off Track | Objectives not achievable under current plan without major change |
| ⚪ Grey | Not Assessed | Insufficient data or dimension not applicable |

### Atlassian-Specific Implementations
- **Jira**: RAG implemented as single-select custom fields (`On track`, `At risk`, `Off track`) on epics and initiatives
- **Atlas Goals**: Built-in status phases: `On Track`, `At Risk`, `Off Track`, `Done`, `Paused`, `Pending`
- **Atlas Projects**: Same status phases as goals, with phase-transition tracking
- **Jira Align**: RAG status on portfolio features, capabilities, and themes with "color by health" display

## AI/ML-Specific Health Dimensions

Beyond standard program management dimensions, AI/ML programs require additional health signals:

### Model Health
- **Training pipeline stability**: Training runs completing successfully, convergence within expected bounds
- **Model performance drift**: Production model metrics (accuracy, latency, throughput) vs. baseline
- **Data quality**: Input data freshness, schema drift, distribution shift detection
- **Feature store health**: Feature computation pipeline status, freshness guarantees

### ML Infrastructure
- **GPU/compute utilization**: Resource allocation vs. demand, queue wait times
- **Pipeline orchestration**: DAG completion rates, retry frequencies, SLA adherence
- **Model serving**: Inference latency p50/p95/p99, error rates, throughput
- **Experiment tracking**: Experiment completion rates, reproducibility scores

### AI Safety & Compliance
- **Bias monitoring**: Fairness metrics across protected attributes
- **Hallucination rate**: For generative AI applications
- **Content safety**: Flagged output rates, human review queue depth
- **Regulatory compliance**: Audit trail completeness, policy adherence

## Exception-Based Reporting Philosophy

The AI TPM should follow exception-based reporting principles derived from SRE and ITIL practices:

### Core Principles
1. **Alert on symptoms, not causes** — Report what's broken, not every contributing factor
2. **Threshold-based triggering** — Only alert when metrics exceed meaningful thresholds
3. **State-change focus** — Alert on transitions (Green→Amber), not on stable states
4. **Deduplication** — Don't re-alert on known issues within cooldown windows
5. **Batching** — Group related exceptions into digestible summaries

### When to Be Silent
- Metrics fluctuating within normal range
- Stable Amber status with active mitigation (already known)
- Minor metric improvements that don't change RAG status
- Informational data refreshes with no material change

### When to Alert
- Any transition TO Red (immediate)
- New blockers appearing (next digest)
- Milestones slipping from On Track to At Risk (next digest)
- Data source failures degrading monitoring capability (immediate)

## Confidence Assessment Framework

Every RAG assessment should include a confidence level:

| Level | Data Quality | Appropriate Action |
|-------|-------------|-------------------|
| **High** | All data sources responsive; metrics within clear threshold bands | Report with confidence; act on results |
| **Medium** | Some sources stale (>24h); borderline values near thresholds | Report with caveat; flag for human review if actionable |
| **Low** | Major data gaps; qualitative assessment only; manual override applied | Report as preliminary; require human confirmation before action |

## Composite RAG Computation

### Worst-Dimension Rule
The standard approach: overall status = worst individual dimension. This is conservative and appropriate for programs where any single dimension failure can block delivery.

### Weighted Approach (Advanced)
For mature programs, dimensions can be weighted by current phase:
- **Planning phase**: Schedule weight ↑, Quality weight ↓
- **Development phase**: Scope weight ↑, Resources weight ↑
- **Launch phase**: Quality weight ↑, Schedule weight ↑↑
- **Maintenance phase**: Quality weight ↑, Stakeholder weight ↑

### Override Protocol
When human judgment differs from computed RAG:
1. Document the override rationale
2. Record both computed and overridden values
3. Require manager-level approval for Red→Green overrides
4. Time-box overrides — they expire after 1 reporting cycle unless renewed

## Related Skills and Tools

- **Skill**: `program-health-reporting` — Operational workflows that use this framework
- **Tool**: `twg` — Primary data collection tool for Jira, Atlas, Confluence signals
- **Tool**: `slack_send_message` — Delivery channel for digests and alerts
- **Skill**: `slack_actions` — Slack interaction patterns for message formatting
- **Skill**: `slack_search` — Finding previous status messages for threading and context
