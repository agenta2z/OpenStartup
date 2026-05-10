---
name: infrastructure-ops
description: >
  Comprehensive operational skill for AI SRE infrastructure management. Provides domain-specific
  workflow guidance for composing kubernetes_ops, cloud_ops, and terraform_ops tools with enforced
  safety guardrails, self-healing automation SOPs, capacity forecasting methodologies, CI/CD pipeline
  health monitoring, auto-scaling decision frameworks, and structured escalation procedures. Every
  infrastructure action flows through a mandatory pre-execution validation checklist that enforces
  hard guardrails (absolute prohibitions) and soft guardrails (configurable limits) before execution.
labels:
  - infrastructure
  - sre
  - operations
  - reliability
metadata:
  tools:
    - kubernetes_ops
    - cloud_ops
    - terraform_ops
---

# Infrastructure Operations Skill

## 1. Skill Overview

- **Name**: infrastructure-ops
- **Description**: Composition layer for kubernetes_ops, cloud_ops, and terraform_ops that enforces safety guardrails, executes self-healing automation, monitors CI/CD health, manages capacity forecasting, and provides structured escalation procedures for AI SRE operations.
- **Leveraged Tools**:
  - **kubernetes_ops**: Execute kubectl commands for cluster management, workload inspection, debugging, rollout management, and supervised mutations (scale, apply, delete).
  - **cloud_ops**: Execute AWS CLI commands for EC2 instance management, RDS monitoring, ELB/ALB health checks, CloudWatch alarms/metrics, and SQS queue monitoring.
  - **terraform_ops**: Execute Terraform CLI commands for infrastructure-as-code with mandatory plan-apply safety gates, state management, and drift detection.

---

## 2. Workflow Mappings

### 2.1 Tool Routing Decision Tree

Before executing ANY infrastructure operation, determine which tool to use:

- Is the operation about Kubernetes resources (pods, deployments, services, nodes, HPA, VPA)? → **kubernetes_ops**
- Is the operation about AWS cloud resources (EC2, RDS, ELB, CloudWatch, SQS)? → **cloud_ops**
- Is the operation about infrastructure-as-code (Terraform plans, state, apply)? → **terraform_ops**
- None of the above? → Escalate to human — operation type not supported

### 2.2 Workflow: Investigate Infrastructure Health

**Trigger**: User asks about system health, an alert fires, or proactive health check is due.

**Steps**:

1. **Kubernetes cluster health**:
   - `kubernetes_ops get nodes -o wide`
   - `kubernetes_ops top nodes`
   - `kubernetes_ops get pods --all-namespaces --field-selector=status.phase!=Running`
   - `kubernetes_ops get events --all-namespaces --sort-by=.lastTimestamp`

2. **AWS infrastructure health**:
   - `cloud_ops ec2 describe-instance-status --output json`
   - `cloud_ops cloudwatch describe-alarms --state-value ALARM --output json`
   - `cloud_ops elbv2 describe-target-health --target-group-arn <arn> --output json`

3. **Terraform drift detection**:
   - `terraform_ops plan -out=drift-check.tfplan -input=false -no-color -detailed-exitcode`
   - `terraform_ops show -json drift-check.tfplan`
   - Exit code 2 = drift detected. Report drift but do NOT auto-apply.

4. **Synthesize findings**: Produce a health summary with status (Healthy/Degraded/Critical) for each layer.

**Example scenario**: Alert fires for high API latency.
- Run `kubernetes_ops get pods -n production -l app=api-server -o wide` to check pod health
- Run `kubernetes_ops top pods -n production -l app=api-server` to check resource usage
- Run `cloud_ops elbv2 describe-target-health --target-group-arn <arn>` to check LB targets
- Run `cloud_ops cloudwatch get-metric-data ...` to pull API latency metrics
- Synthesize: "3/5 pods running, 2 in CrashLoopBackOff. Target group shows 2 unhealthy targets. CPU at 92% on running pods."
- Escalate or trigger self-healing SOP based on findings.

### 2.3 Workflow: Pod CrashLoopBackOff Remediation (SOP-001)

**Trigger**: Pods detected in CrashLoopBackOff state.

**Steps**:

1. **Detect**: Identify crash-looping pods
   - `kubernetes_ops get pods -n <namespace> --field-selector=status.phase!=Running -o json`
   - Parse JSON to find pods with `containerStatuses[].state.waiting.reason == "CrashLoopBackOff"`

2. **Diagnose**: Collect diagnostic information
   - `kubernetes_ops logs pod/<pod-name> -n <namespace> --tail=200`
   - `kubernetes_ops logs pod/<pod-name> -n <namespace> --previous --tail=200`
   - `kubernetes_ops describe pod <pod-name> -n <namespace>`
   - `kubernetes_ops get events -n <namespace> --field-selector=involvedObject.name=<pod-name>`

3. **Classify severity**:
   - restartCount 1-3: LOW — likely transient, monitor for 10 minutes
   - restartCount 4-10: MEDIUM — investigate, prepare remediation
   - restartCount > 10: HIGH — sustained failure, act immediately

4. **Assess recent changes**: Check if a recent deployment caused the crash
   - `kubernetes_ops rollout history deployment/<deployment-name> -n <namespace>`

5. **Remediate** (choose based on diagnosis):
   - **Rollback** (if crash started after recent deployment): `kubernetes_ops rollout undo deployment/<deployment-name> -n <namespace>` — Autonomy: L2
   - **Scale up healthy replicas**: `kubernetes_ops scale deployment/<deployment-name> --replicas=<current+2> -n <namespace>` — Autonomy: L2
   - **Delete crashing pod** (stateless workloads only): `kubernetes_ops delete pod <pod-name> -n <namespace>` — Autonomy: L2

6. **Verify**: Confirm remediation succeeded
   - `kubernetes_ops rollout status deployment/<deployment-name> -n <namespace> --timeout=120s`
   - `kubernetes_ops get pods -n <namespace> -l app=<app-label> -o wide`

7. **Report**: Log the incident, diagnosis, action taken, and outcome.

### 2.4 Workflow: Deployment Rollout Management

**Trigger**: New deployment requested, or rollout issue detected.

**Steps**:

1. **Monitor rollout progress**: `kubernetes_ops rollout status deployment/<name> -n <namespace> --timeout=300s`
2. **Detect failed rollout**: `kubernetes_ops get deployment <name> -n <namespace> -o json` — Parse `.status.conditions` for `type: Progressing` with `status: "False"` and `reason: ProgressDeadlineExceeded`.
3. **Rollback on failure**: `kubernetes_ops rollout undo deployment/<name> -n <namespace>` — Autonomy: L2
4. **Verify rollback**: `kubernetes_ops rollout status deployment/<name> -n <namespace> --timeout=120s`

### 2.5 Workflow: Terraform Change Management

**Trigger**: Infrastructure change requested via Terraform.

**Steps**:

1. **Initialize** (if needed): `terraform_ops init -input=false -no-color`
2. **Plan** (autonomous): `terraform_ops plan -out=plan-<timestamp>.tfplan -input=false -no-color`
3. **Review plan** (autonomous analysis): `terraform_ops show -json plan-<timestamp>.tfplan` — Parse JSON to extract resource_changes and action types (create, update, delete, replace)
4. **Classify blast radius**:
   - **Low**: Only creates, or updates < 5 resources, no deletes
   - **Medium**: Updates 5-20 resources, or deletes non-critical resources
   - **High**: Deletes > 3 resources, or modifies critical resources (databases, load balancers, DNS)
   - **Critical**: Any destroy operation, or changes to IAM, networking, encryption
5. **Present for approval**: Show summary — "Plan: X to create, Y to update, Z to delete" with blast radius classification
6. **Apply** (ONLY after human approval): `terraform_ops apply -input=false -no-color plan-<timestamp>.tfplan` — NEVER run apply without referencing the exact saved plan file.
7. **Verify**: `terraform_ops state list` and `terraform_ops output -json` — Cross-verify with cloud_ops or kubernetes_ops as appropriate.

### 2.6 Workflow: AWS CloudWatch Alarm Investigation

**Trigger**: CloudWatch alarm enters ALARM state.

**Steps**:

1. **List active alarms**: `cloud_ops cloudwatch describe-alarms --state-value ALARM --output json`
2. **Get alarm details**: Extract MetricName, Namespace, Threshold, ComparisonOperator, and Dimensions.
3. **Query underlying metrics**: `cloud_ops cloudwatch get-metric-data --metric-data-queries file://query.json --start-time <1h-ago> --end-time <now> --output json`
4. **Correlate with resource health**:
   - EC2: `cloud_ops ec2 describe-instance-status --instance-ids <id> --output json`
   - RDS: `cloud_ops rds describe-db-instances --db-instance-identifier <id> --output json`
   - ELB: `cloud_ops elbv2 describe-target-health --target-group-arn <arn> --output json`
5. **Determine root cause and recommend action**.

### 2.7 Workflow: Capacity Forecasting (30/60/90-Day)

**Trigger**: Scheduled weekly review, or capacity concern raised.

**Steps**:

1. **Collect current utilization**: `kubernetes_ops top nodes`, `kubernetes_ops top pods -n <namespace> --sort-by=cpu`, `cloud_ops cloudwatch get-metric-data` (CPU, memory, disk over 30 days)
2. **Analyze trends**: Calculate average, P50, P95, P99 utilization. Apply linear regression on rolling 30-day window.
3. **Generate forecasts**:
   - 30-day (high confidence): Will resource exceed 80% utilization?
   - 60-day (medium confidence): Will resource exceed 70% utilization?
   - 90-day (directional): Is utilization trending up, stable, or down?
4. **Recommend actions**: Immediate (30-day breach), planned (60-day breach), or quarterly (90-day breach).
5. **Produce capacity report** with data, forecasts, and recommendations.

### 2.8 Workflow: Auto-Scaling Decision

**Trigger**: Resource utilization exceeds threshold, or scaling recommendation requested.

**Steps**:

1. **Assess current autoscaler state**: `kubernetes_ops get hpa -n <namespace> -o json`, `cloud_ops autoscaling describe-auto-scaling-groups --output json`
2. **Scale-Up vs. Scale-Out decision**:
   - CPU high, memory OK → Scale OUT (add replicas via HPA)
   - Memory high, CPU OK → Scale UP (increase resource limits via VPA)
   - Both high → Scale OUT first, then evaluate Scale UP
   - Stateless app → Prefer horizontal scaling
   - Stateful app → Prefer vertical scaling
   - HPA at maxReplicas → Increase maxReplicas or consider vertical scaling
3. **Execute scaling** (with confirmation): `kubernetes_ops scale deployment/<name> --replicas=<new-count> -n <namespace>` — Autonomy: L2
4. **Verify**: Monitor scaling progress and confirm new capacity is healthy.

---

## 3. Domain Guidance

### 3.1 Pre-Execution Validation Checklist (MANDATORY — NEVER SKIP)

Before executing ANY infrastructure mutation, complete ALL checks in order:

#### Step 1: Absolute Prohibition Check (Hard Guardrails)

Verify the action does NOT involve:
- DNS record creation, modification, or deletion
- IAM role, policy, or user modifications
- Production database deletion
- Encryption key modifications
- Backup policy disabling
- Security group rule deletion in production

**If ANY prohibition is matched → STOP. Report: "Action prohibited by hard guardrail. Escalating to human operator." Do NOT proceed.**

#### Step 2: Instance Termination Limit

If the action involves instance or pod termination:
- Count target instances/pods
- If count > 3 → STOP. Report: "Hard limit: max 3 instances per action."

#### Step 3: Cost Limit Check

- If estimated cost > $500 per action → STOP.
- If cumulative daily cost + estimated > $5,000 → STOP.

#### Step 4: Soft Guardrail Validation

| Guardrail | Default | Max | Override Requires |
|-----------|---------|-----|-------------------|
| Batch size (resources per action) | 5 | 20 | L2 approval |
| Traffic shift per rollout step | 10% | 25% | L2 approval |
| Actions per hour | 10 | 30 | L2 approval |
| Cooldown between actions | 5 min | — | L2 approval |
| Confidence threshold | 0.85 | — | Cannot lower below 0.7 |

If any soft guardrail would be exceeded → Pause and request approval before proceeding.

#### Step 5: Autonomy Level Classification

| Level | Criteria | Requirement |
|-------|----------|-------------|
| L3 — Fully Autonomous | Known pattern, low blast radius, reversible, confidence > 0.95 | Execute immediately, log action |
| L2 — Supervised | Known pattern but elevated risk, or confidence 0.85-0.95 | Notify human, execute after confirmation |
| L1 — Human Approval | Unknown pattern, high blast radius, irreversible, or confidence < 0.85 | Generate action proposal, wait for explicit approval |

**Classification algorithm**:
1. Is this pattern in the known-pattern database? NO → L1
2. Is blast radius > 1 service? YES → downgrade to L1
3. Is estimated cost > $200? YES → downgrade to minimum L2
4. Is confidence > 0.85? NO → downgrade by 1 level
5. Is action reversible within 5 minutes? NO → downgrade by 1 level

#### Step 6: Proceed

All checks passed. Execute the action according to its autonomy level.

### 3.2 Risk Classification by Command

#### kubernetes_ops Commands

| Risk Level | Commands | Autonomy |
|------------|----------|----------|
| READ (none) | get, describe, logs, top, explain, api-resources, events, cluster-info, version | L3 |
| LOW | scale (within bounds), rollout status, rollout history | L3 reads, L2 scale |
| MEDIUM | rollout restart, rollout undo, cordon, uncordon, label, annotate | L2 |
| HIGH | apply, patch, create, replace, set | L1 |
| BLOCKED | delete namespace, delete --all, drain, taint | NEVER — escalate |

#### cloud_ops Commands

| Risk Level | Commands | Autonomy |
|------------|----------|----------|
| READ (none) | describe-*, get-*, list-* | L3 |
| LOW | start-instances, reboot-instances | L2 |
| MEDIUM | stop-instances, set-desired-capacity | L2 |
| HIGH | terminate-instances, delete-db-instance | L1 |
| BLOCKED | iam *, route53 *, kms delete-key | NEVER — escalate |

#### terraform_ops Commands

| Risk Level | Commands | Autonomy |
|------------|----------|----------|
| READ (none) | plan, show, state list, state show, output, validate, fmt, version | L3 |
| MEDIUM | import, state mv, force-unlock | L1 |
| HIGH | apply (with saved plan file) | L1 — ALWAYS |
| BLOCKED | destroy, apply -auto-approve, apply -destroy | NEVER — escalate |

### 3.3 Terminology

| Term | Definition |
|------|------------|
| **Blast radius** | Number of services, users, or resources affected by an action |
| **CrashLoopBackOff** | Kubernetes pod state where a container repeatedly crashes and restarts with exponential backoff |
| **Drift** | Difference between Terraform-managed desired state and actual infrastructure state |
| **HPA** | Horizontal Pod Autoscaler — scales pod replicas based on metrics |
| **VPA** | Vertical Pod Autoscaler — adjusts pod resource requests/limits |
| **KEDA** | Kubernetes Event-Driven Autoscaler — scales based on external event sources |
| **Plan file** | Binary Terraform artifact (.tfplan) capturing point-in-time change snapshot |
| **Rollout** | Kubernetes progressive deployment update strategy |
| **Soak time** | Observation period after a change to confirm stability |
| **Target group** | AWS ELB concept — set of targets receiving traffic |
| **DORA metrics** | Deployment frequency, lead time, change failure rate, MTTR |

### 3.4 Cadence Patterns

| Activity | Frequency | Tool(s) Used |
|----------|-----------|--------------|
| Cluster health check | Every 15 minutes | kubernetes_ops |
| CloudWatch alarm review | Every 5 minutes (event-driven) | cloud_ops |
| Capacity utilization snapshot | Daily | kubernetes_ops, cloud_ops |
| Capacity forecast report | Weekly | kubernetes_ops, cloud_ops |
| Terraform drift detection | Daily | terraform_ops |
| DORA metrics review | Weekly | kubernetes_ops, cloud_ops |
| Full infrastructure health report | Weekly | All three tools |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Key Operations |
|------|----------------|
| **kubernetes_ops** | get, describe, logs, top, events, rollout status/restart/undo/history, scale, apply, delete, get hpa, get vpa |
| **cloud_ops** | ec2 describe-instances/describe-instance-status/start/stop, rds describe-db-instances, elbv2 describe-target-health, cloudwatch describe-alarms/get-metric-data, sqs get-queue-attributes, autoscaling describe/set-desired-capacity |
| **terraform_ops** | init, plan -out, show -json, state list/show, output, validate, apply, import, state mv/rm, force-unlock |

### 4.2 Cross-Tool Patterns

**Pattern A: Alert Investigation** (cloud_ops → kubernetes_ops)
1. `cloud_ops cloudwatch describe-alarms --state-value ALARM` — identify alarms
2. Parse alarm dimensions to identify affected resources
3. `kubernetes_ops get pods -n <namespace> -l <label>` — check K8s workload health
4. `kubernetes_ops logs pod/<pod> -n <namespace> --tail=100` — get logs
5. Synthesize findings across layers

**Pattern B: Deployment Verification** (terraform_ops → cloud_ops → kubernetes_ops)
1. `terraform_ops apply ... plan.tfplan` — apply infrastructure changes
2. `cloud_ops ec2 describe-instances --filters ...` — verify new resources
3. `kubernetes_ops rollout status deployment/<name>` — verify K8s workloads
4. Report deployment success/failure

**Pattern C: Capacity Planning** (kubernetes_ops + cloud_ops → analysis)
1. `kubernetes_ops top nodes` + `kubernetes_ops top pods` — current utilization
2. `cloud_ops cloudwatch get-metric-data ...` — historical trends
3. Apply forecasting model to combined data
4. Generate capacity report

**Pattern D: Self-Healing** (kubernetes_ops → cloud_ops)
1. `kubernetes_ops get pods --field-selector=status.phase!=Running` — detect unhealthy
2. `kubernetes_ops describe pod <pod>` — diagnose
3. If node issue: `cloud_ops ec2 describe-instance-status` — check EC2 health
4. Execute remediation based on diagnosis

### 4.3 Autonomy Levels Summary

| Operation Type | Autonomy | Notes |
|----------------|----------|-------|
| All read operations | L3 — Fully autonomous | No confirmation needed |
| Known self-healing patterns | L2 — Supervised | Brief confirmation window |
| Scaling within bounds | L2 — Supervised | Confirm target count |
| Terraform plan | L3 — Fully autonomous | Plan is always safe |
| Terraform apply | L1 — Human required | ALWAYS requires approval |
| Instance termination | L1 — Human required | ALWAYS requires approval |
| Unknown failure patterns | L1 — Human required | Generate proposal, await approval |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries — What the AI Should NOT Do

**ABSOLUTE PROHIBITIONS (Hard Guardrails — NEVER bypass)**:
1. NEVER modify DNS records (Route53 or any DNS provider)
2. NEVER modify IAM roles, policies, or users
3. NEVER delete production databases
4. NEVER modify or delete encryption keys
5. NEVER disable backup policies
6. NEVER run `terraform destroy`
7. NEVER run `terraform apply -auto-approve` without a saved plan file
8. NEVER run `kubectl delete namespace` or `kubectl delete --all`
9. NEVER drain Kubernetes nodes without human approval
10. NEVER expose secrets, credentials, or tokens in logs or output
11. NEVER modify security group rules in production without human approval
12. NEVER terminate more than 3 instances in a single action

### 5.2 Escalation Triggers

Immediately escalate to a human operator when:

| Trigger | Reason |
|---------|--------|
| Any hard guardrail would be violated | Absolute safety boundary |
| Confidence score < 0.7 | Too uncertain to act or propose |
| Blast radius > 1 service | Cross-service impact requires human judgment |
| Same failure recurs > 3 times in 1 hour | Automated remediation not working |
| Cost impact > $500 per action | Financial risk threshold |
| Data loss risk detected | Irreversible impact |
| Production database state changes | Critical data path |
| Unknown error from tool execution | Cannot diagnose autonomously |
| Cascading failure (multiple services) | Requires coordinated response |
| Customer-facing service fully down | Sev-1 — human incident commander needed |

### 5.3 Error Handling

**Tool Call Failures:**

| Error Type | Action |
|------------|--------|
| Non-zero exit code | Log error, parse message, retry once after 10s |
| Timeout (>60s) | Log, retry once with 120s timeout |
| Authentication failure | DO NOT retry, escalate (credentials may have rotated) |
| Permission denied (RBAC/IAM) | DO NOT retry, escalate (insufficient permissions) |
| Resource not found (404) | Verify resource name/namespace, report to user |
| Rate limiting (429) | Exponential backoff (10s, 20s, 40s), max 3 retries |
| Network failure | Retry after 30s, max 2 retries, then escalate |

**Unexpected Results:**

| Situation | Action |
|-----------|--------|
| Command succeeds but empty output | Verify parameters, retry once, report if still empty |
| State doesn't match expected | Log discrepancy, do NOT retry mutation, report to human |
| Terraform plan shows unexpected deletions | STOP, do NOT apply, flag for human review |
| Rollout stuck (no progress for 5 min) | Check events, collect logs, report with diagnosis |
| Anomalous metric spike | Investigate cause before acting, avoid reactive scaling |

### 5.4 Audit Trail Requirements

Every infrastructure action MUST be logged with the following fields:
- **timestamp**: ISO-8601 format
- **action**: tool_name + command executed
- **target_resources**: list of resource identifiers affected
- **autonomy_level**: L1, L2, or L3
- **guardrail_checks**: hard guardrails (PASSED/BLOCKED), soft guardrails (PASSED/OVERRIDE_APPROVED), cost estimate
- **result**: SUCCESS, FAILURE, or ESCALATED
- **error_message**: details if failure occurred
- **human_approver**: identity if L1 approval was required
- **rollback_available**: whether the action can be reversed

---

## Self-Healing SOPs Quick Reference

| SOP | Trigger | Tool | Key Command | Autonomy |
|-----|---------|------|-------------|----------|
| SOP-001: CrashLoopBackOff | Pod restart count > 10 | kubernetes_ops | rollout undo / delete pod | L2 |
| SOP-002: Failed Rollout | ProgressDeadlineExceeded | kubernetes_ops | rollout undo | L2 |
| SOP-003: Unhealthy LB Targets | Target health = unhealthy | cloud_ops + kubernetes_ops | Diagnose pod/instance | L2 |
| SOP-004: CloudWatch Alarm | Alarm state = ALARM | cloud_ops | Investigate metrics | L3 (read) |
| SOP-005: DLQ Buildup | SQS DLQ depth > threshold | cloud_ops | Alert + investigate | L1 |
| SOP-006: Node Not Ready | Node condition = NotReady | kubernetes_ops + cloud_ops | Cordon + investigate | L2 |
| SOP-007: Terraform Drift | Plan exit code 2 | terraform_ops | Report drift | L3 (report only) |
