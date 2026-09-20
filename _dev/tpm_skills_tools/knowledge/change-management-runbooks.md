# Change Management Runbook Patterns for AI/ML Systems

Parameterized change management runbook templates covering four AI/ML change types:
schema changes, model upgrades, prompt configuration changes, and feature store migrations.
Aligned with ITIL Change Enablement and NIST AI RMF expectations.

Related skill: `ai-tpm-program-management` (Workflow 2.5)

---

## 1. Universal Runbook Structure

All change runbooks share these common sections regardless of change type:

### 1.1 Runbook Metadata
```
| Field | Value |
|-------|-------|
| Runbook ID | CR-[NNNN] |
| Title | [Descriptive change title] |
| Status | Draft / Approved / In Progress / Complete / Rolled Back |
| Change Type | schema_change / model_upgrade / prompt_config_change / feature_store_migration |
| Risk Tier | Low / Medium / High / Critical |
| Change Category (ITIL) | Standard / Normal / Emergency |
| Environments | dev / stage / prod [+ regions] |
| Service(s) Affected | [service names and IDs] |
| Jira Change Key | [PROJ-NNN] |
| Related Incidents | [INC-NNN] (if applicable) |
| Owner | @[name] |
| Approver | @[name] |
| Planned Window | [Date/time range] |
| Last Reviewed | [Date] |
```

### 1.2 Scope & Objectives
- **What is changing**: Concrete description of the change
- **Why**: Business/technical justification
- **Success criteria**: How we know the change succeeded (specific metrics)
- **In-scope systems**: Components, data stores, models, agents affected
- **Out-of-scope**: What is explicitly NOT being changed

### 1.3 Pre-Change Readiness Checklist
```
- [ ] Change approved (CAB for High/Critical, service owner for Standard)
- [ ] Maintenance window confirmed and communicated
- [ ] Change freeze period checked (not in freeze)
- [ ] Access verified: credentials, VPN, DB roles, feature flag consoles
- [ ] Baselines captured: dashboards open, key metrics recorded
- [ ] Backups completed: DB snapshot / model registry version / config export
- [ ] Dependencies notified: upstream and downstream services
- [ ] Rollback plan reviewed and approved
- [ ] Communication plan ready: stakeholders, channels, escalation contacts
```

### 1.4 Risk Assessment
```
| Factor | Score (1-4) | Rationale |
|--------|-------------|-----------|
| Users affected | [1-4] | [Explain blast radius] |
| Reversibility | [1-4] | [Time to rollback] |
| Dependency impact | [1-4] | [Downstream systems] |
| Testing confidence | [1-4] | [Staging/eval coverage] |
| **Total Risk Score** | [4-16] | Tier: [Low/Med/High/Critical] |
```

### 1.5 Rollout Strategy

**By risk tier**:

| Risk Tier | Strategy | Phases |
|-----------|----------|--------|
| Low | All-at-once | dev → stage → prod (single phase) |
| Medium | Progressive | dev → stage → prod (gated, 30min soak) |
| High | Canary | dev → stage → canary (5%) → prod (25%/50%/100%) |
| Critical | Shadow/Dual-write | Shadow mode → canary (1%) → slow ramp with manual gates |

**Phase template**:
```
| Phase | Target | Traffic % | Soak Time | Gate Criteria |
|-------|--------|-----------|-----------|---------------|
| 1 | dev | 100% | 15 min | All tests pass, no errors |
| 2 | stage | 100% | 30 min | PDV pass, latency within bounds |
| 3 | canary | 5% | 60 min | Error rate <0.1%, p99 <target |
| 4 | prod | 100% | 120 min | All metrics within SLO bounds |
```

### 1.6 Verification & Monitoring Plan
```
Pre-change baselines:
- [ ] [Metric 1]: [current value]
- [ ] [Metric 2]: [current value]

During rollout:
- [ ] PDV checks passing
- [ ] Error rate < [threshold]
- [ ] Latency p99 < [target]ms
- [ ] No new alerts triggered

Post-change (heightened monitoring for [N] hours):
- [ ] All SLOs within bounds
- [ ] No degradation in downstream services
- [ ] "All clear" criteria met: [specific conditions]
```

### 1.7 Rollback Plan
```
Trigger conditions:
- Error rate exceeds [X]% for [Y] minutes
- Latency p99 exceeds [Z]ms for [Y] minutes
- Any Sev-1/Sev-2 incident attributed to the change
- Manual trigger by on-call engineer or change owner

Rollback steps:
1. [Step 1 — specific command or action]
2. [Step 2]
3. [Step 3]

Estimated rollback time: [N] minutes
Rollback verification: [How to confirm rollback succeeded]
```

### 1.8 Communication Plan
```
| When | Who | Channel | Message |
|------|-----|---------|---------|
| Before change | Affected teams | #[channel] | Change starting: [summary] |
| During rollout | On-call + owner | #[ops-channel] | Progress updates per phase |
| After success | Stakeholders | #[channel] | Change complete, metrics nominal |
| On rollback | All affected | #[channel] + incident | Rolled back: [reason] |
```

### 1.9 Post-Change Review
- Mandatory PIR within 24-72h for High/Critical risk changes
- Optional lightweight review for Standard/Low risk
- Document: success/failure, issues encountered, follow-up actions
- Update runbook with lessons learned

---

## 2. Type-Specific Sections

### 2.1 Schema Change Additions
```
Schema Details:
- Database: [name, engine, version]
- Migration tool: [Flyway/Liquibase/Alembic/raw SQL]
- Migration script location: [repo/path]
- Schema diff summary: [tables/columns added/modified/removed]

Compatibility:
- [ ] Forward-compatible (new schema works with old code)
- [ ] Backward-compatible (old schema works with new code)
- [ ] Dual-write period required: [Yes/No, duration]

Rollback specifics:
- Rollback migration script: [location]
- Data backfill required on rollback: [Yes/No]
- Estimated rollback data loss: [None/Partial/description]

Data validation:
- [ ] Row counts match expectations
- [ ] Constraint violations: none
- [ ] Index rebuild completed
- [ ] Query performance validated against baseline
```

### 2.2 Model Upgrade Additions
```
Model Details:
- Model name/ID: [name]
- Previous version: [v_old]
- New version: [v_new]
- Model registry: [location/URL]
- Training data changes: [description or "none"]

Evaluation Results:
| Metric | Baseline (v_old) | New (v_new) | Delta | Threshold |
|--------|------------------|-------------|-------|-----------|
| [metric1] | [value] | [value] | [+/-] | [min acceptable] |
| [metric2] | [value] | [value] | [+/-] | [min acceptable] |

A/B Test Configuration:
- Experiment ID: [ID]
- Control: [v_old] at [X]%
- Treatment: [v_new] at [Y]%
- Duration: [N days]
- Primary metric: [metric]
- Guardrail metrics: [list]

Responsible AI:
- [ ] Bias evaluation completed
- [ ] Safety evaluation completed
- [ ] RAI review board sign-off (if required)

Rollback specifics:
- Rollback model version: [v_old registry ID]
- Rollback command: [specific command to revert model serving]
- Cache invalidation required: [Yes/No]
```

### 2.3 Prompt Configuration Change Additions
```
Prompt Details:
- Prompt ID/name: [identifier]
- Registry/store: [location]
- Previous version: [v_old hash/ID]
- New version: [v_new hash/ID]
- Diff summary: [key changes in natural language]

Evaluation:
| Eval Suite | Baseline Score | New Score | Delta | Regression Threshold |
|-----------|---------------|-----------|-------|---------------------|
| [suite1] | [score] | [score] | [+/-] | [max allowed regression] |

Shadow Mode:
- Shadow period: [N hours/days]
- Shadow comparison metrics: [list]
- Shadow pass criteria: [specific thresholds]

Responsible AI:
- [ ] Content safety evaluation completed
- [ ] Hallucination rate within bounds
- [ ] Tone/voice consistency validated
- [ ] Edge case testing (adversarial inputs) completed

Rollback specifics:
- Rollback prompt version: [v_old ID]
- Rollback mechanism: [config update / feature flag / registry revert]
- Cache/CDN purge required: [Yes/No]
```

### 2.4 Feature Store Migration Additions
```
Feature Store Details:
- Feature views affected: [list]
- Feature store platform: [Feast/Tecton/custom]
- Migration type: [schema / backfill / platform migration]
- Affected consumers: [list of downstream models/services]

Data Quality:
- [ ] Feature distribution comparison (old vs new)
- [ ] Null rate within bounds
- [ ] Freshness SLO maintained
- [ ] Backfill completed and validated

Dual-Pipeline Period:
- Duration: [N days]
- Old pipeline: [status: active/standby]
- New pipeline: [status: active/standby]
- Comparison metrics: [feature value drift, latency, completeness]

Consumer Impact:
| Consumer | Impact | Migration Step | Verified |
|----------|--------|---------------|----------|
| [model/service] | [description] | [step] | [ ] |

Rollback specifics:
- Revert to old feature pipeline: [steps]
- Consumer rollback: [steps to point consumers back to old features]
- Data reconciliation: [steps if dual-write diverged]
```

---

## 3. Approval Matrix

| Risk Tier | Required Approvals |
|-----------|-------------------|
| Low (Standard) | Service owner |
| Medium (Normal) | Service owner + platform SME |
| High (Normal) | Service owner + platform SME + Change Manager |
| Critical (Emergency/Normal) | Service owner + CAB + Engineering leadership |

**Additional approvals by type**:
- Schema changes: DBA or database platform owner
- Model upgrades: ML platform owner + RAI reviewer (if customer-facing)
- Prompt changes: Product owner + RAI reviewer (if risky content)
- Feature store: ML platform owner + affected consumer owners

---

## 4. Integration with Jira Change Management

Every runbook should be linked to a Jira Change issue with:
- **Issue type**: Change (IT-003 or equivalent)
- **Change type field**: Standard / Normal / Emergency
- **Risk assessment field**: Populated from runbook risk score
- **Implementation plan**: Link to Confluence runbook page
- **Rollback plan**: Summarized in Jira, detailed in runbook
- **Test plan**: Link to evaluation results or staging test reports

The AI TPM skill can:
- Verify a change ticket exists before generating a runbook
- Suggest field values based on runbook parameters
- Comment on the ticket with the runbook link
- Track runbook completion status via Jira transitions
