# Risk Tier Classification Logic

This knowledge block documents the complete risk tier classification system used by the AI TPM for intake classification in both SOP 1 (AI Launch Readiness Gate) and SOP 3 (AI Experiment-to-Production Lifecycle). It provides the decision matrix, scoring rules, governance-rigor mapping, and integration patterns.

## 1. Overview

Risk tier classification is the foundational decision point that gates nearly every downstream workflow in the AI TPM role. It determines:
- **Governance rigor**: Light-touch vs. standard vs. full governance path
- **Evidence collection depth**: Which checklist categories are mandatory
- **Approval routing**: Whether governance board review is required
- **Monitoring intensity**: Post-launch monitoring cadence and scope
- **Remediation urgency**: How quickly gaps must be addressed

The classification is performed autonomously (🟢) by the AI TPM based on a defined rules matrix, though humans may override the classification with justification.

## 2. Four-Dimensional Classification Matrix

### Input Dimensions

Each AI system or change is scored across four dimensions:

#### Dimension 1: Model Type

| Value | Score | Examples |
|---|---|---|
| **Prompt config change** | Low | Prompt template updates, system instruction tweaks |
| **Hyperparameter tuning** | Low | Learning rate adjustment, regularization changes |
| **Model version update (same architecture)** | Medium | Retrained model with updated data, fine-tuned variant |
| **New model class / architecture** | High | Switching from classification to generative, new transformer architecture |
| **Agentic system** | High | AI agents with tool use, autonomous actions, multi-step workflows |

#### Dimension 2: Data Sensitivity

| Value | Score | Examples |
|---|---|---|
| **Public / synthetic data** | Low | Open datasets, synthetic test data, aggregated public statistics |
| **Internal data, no PII** | Medium | Internal telemetry, product usage metrics (anonymized), internal docs |
| **PII-containing** | High | User names, emails, account data, behavioral profiles |
| **Regulated data** | High | HIPAA health data, financial data, special categories (biometric, political, racial) |
| **Secret / highly confidential** | High | Security credentials, unreleased strategy, legal privilege |

#### Dimension 3: Customer Exposure

| Value | Score | Examples |
|---|---|---|
| **Internal-only / dev/staging** | Low | Internal tools, developer environments, test instances |
| **Limited beta / internal users** | Medium | Dogfooding, early access program, pilot tenants (<100) |
| **Broad customer-facing (GA)** | High | Available to all cloud customers, production feature |
| **Safety-critical application** | High | Features affecting access control, permissions, financial calculations |

#### Dimension 4: Regulatory Scope

| Value | Score | Examples |
|---|---|---|
| **None** | Low | No regulatory requirements applicable |
| **Standard compliance (SOC2, etc.)** | Medium | Standard security frameworks, general privacy regulations |
| **AIMS medium/high-risk** | High | Internal AIMS classification as medium or high risk |
| **Regulated domain** | High | HIPAA, GDPR Article 22, financial regulations, EU AI Act high-risk |
| **Sector-specific regulation** | High | Healthcare AI, autonomous vehicles, critical infrastructure |

### Composite Scoring Rule

**Overall risk tier = max(individual dimension scores)**

This means: Any single "High" score in any dimension results in an overall **High** risk tier. This is deliberately conservative — it ensures that a system processing PII (High data sensitivity) is treated as High risk even if it's only an internal tool (Low exposure).

| Scenario | Model Type | Data Sensitivity | Customer Exposure | Regulatory Scope | **Overall Tier** |
|---|---|---|---|---|---|
| Prompt tweak on internal tool | Low | Low | Low | Low | **Low** |
| Model retrain with internal data for beta | Medium | Medium | Medium | Medium | **Medium** |
| New model with PII for GA | High | High | High | Medium | **High** |
| Prompt change but touches PII | Low | High | Low | Low | **High** |
| Internal tool in regulated domain | Low | Medium | Low | High | **High** |

## 3. Special Classification: Tier 0 (Prohibited / Unacceptable)

Before applying the standard 3-tier matrix, check for Tier 0 patterns that are outright prohibited:

| Pattern | Source | Action |
|---|---|---|
| Social scoring of individuals | EU AI Act | Block intake, legal escalation |
| Manipulative behavior exploiting vulnerabilities | EU AI Act | Block intake, legal escalation |
| Biometric categorization for protected traits | EU AI Act | Block intake, legal escalation |
| Real-time remote biometric identification in public spaces | EU AI Act | Block intake, legal escalation |
| Workplace emotion recognition | EU AI Act | Block intake, legal escalation |
| Predictive policing based solely on profiling | EU AI Act | Block intake, legal escalation |

**AI TPM behavior for Tier 0:**
1. Immediately halt the intake process
2. Create a Jira ticket: "[BLOCKED] Prohibited AI pattern — design change required"
3. Escalate to Legal and AI Governance team
4. Human confirmation required from Legal before any further work proceeds

## 4. Governance Rigor by Tier

### Low Risk — Light-Touch Governance

| Requirement | Required? | Details |
|---|---|---|
| Risk tier classification | ✅ | Automated, no board review |
| Basic checklist | ✅ | Metrics meet thresholds, deployment configured, basic monitoring |
| Model card | ✅ | Lightweight documentation |
| SBCR/security review | ❌ | Not required unless flagged |
| Privacy review / DPIA | ❌ | Not required for non-PII |
| AI Impact Assessment | ❌ | Not required |
| Threat model | ❌ | Not required |
| Governance board review | ❌ | Not required |
| Fairness evaluation | ❌ | Not required |
| Post-launch monitoring | ✅ | Basic monitoring, monthly review |

### Medium Risk — Standard Governance

| Requirement | Required? | Details |
|---|---|---|
| Risk tier classification | ✅ | Automated, confirmed by risk owner |
| Full checklist (4 categories) | ✅ | All evidence categories |
| Model card | ✅ | Comprehensive documentation |
| SBCR/security review | ✅ | Standard security review |
| Privacy review / DPIA | ✅ | If PII involved |
| AI Impact Assessment | ✅ | Streamlined version |
| Threat model | ✅ | Lightweight review |
| Governance board review | ❌ | Not required |
| Fairness evaluation | ✅ | If user-facing with demographic variation |
| Post-launch monitoring | ✅ | Weekly review, drift detection |

### High Risk — Full Governance

| Requirement | Required? | Details |
|---|---|---|
| Risk tier classification | ✅ | Automated, confirmed by governance board |
| Full checklist (4 categories) | ✅ | All evidence categories, all checks |
| Model card | ✅ | Comprehensive with limitations and biases |
| SBCR/security review | ✅ | Full security review |
| Privacy review / DPIA | ✅ | Full DPIA |
| AI Impact Assessment | ✅ | Full AIIA with mitigations |
| Threat model | ✅ | Full threat model with AI-specific threats |
| Governance board review | ✅ | Required before proceeding |
| Fairness evaluation | ✅ | Comprehensive fairness analysis across protected groups |
| Post-launch monitoring | ✅ | Daily review (first 30 days), drift detection, safety monitoring |

## 5. Integration with AI TPM Skills

### In SOP 1 (Launch Readiness Gate)

Risk tier classification occurs at **Step 1: Intake & Classification** (🟢 Autonomous):

1. AI TPM collects the four dimension values from the change request and context
2. Applies the composite scoring rule
3. Checks for Tier 0 prohibited patterns
4. Determines the governance rigor path
5. Auto-populates the appropriate checklist based on tier
6. Creates gap tickets for missing required evidence

### In SOP 3 (Experiment-to-Production Lifecycle)

Risk tier classification occurs at **Stage 1: Ideation & Intake** (🟡 Semi-Autonomous):

1. AI TPM classifies the use case based on initial description
2. If High risk: flags for governance board review before proceeding to Sandbox
3. Risk tier may be re-evaluated at Stage 3 (Pre-Production) if scope changes
4. Tier determines monitoring intensity during Progressive Rollout and GA

### Tool Commands for Classification Support

```bash
# Search for existing governance records that may inform classification
scripts/twg confluence search query --cql 'type=page AND title ~ "<system-name> risk assessment"'

# Check for privacy-relevant data classifications
scripts/twg confluence search query --cql 'type=page AND title ~ "<system-name> DPIA"'

# Look up regulatory requirements
scripts/twg confluence search query --cql 'type=page AND title ~ "AI legal regulatory register"'

# Get context on the system being classified
scripts/twg context jira workitem <ISSUE-KEY> --depth 2
```

## 6. Override and Re-Classification

### Override Process

Stakeholders may request a risk tier override (e.g., downgrading from High to Medium). This requires:

1. **Written justification** explaining why the standard classification is inappropriate
2. **Human approval** from the designated risk owner (🔴 Human Required)
3. **Documentation** of the override in the gate assessment document
4. **Conditions** if any (e.g., "Medium tier approved with condition that PII is removed before GA")

The AI TPM MUST NOT autonomously override a risk tier classification. It may present evidence supporting a potential reclassification, but the decision is always human.

### Re-Classification Triggers

Risk tier should be re-evaluated when:
- Scope of the AI system changes significantly
- Data sources change (e.g., adding PII data)
- Customer exposure changes (e.g., expanding from beta to GA)
- Regulatory landscape changes (e.g., new regulations apply)
- Incident occurs that reveals previously unknown risks

## 7. Related Resources

- **ai-tpm-launch-readiness-gate** skill: Consumes risk tier for checklist generation and gate criteria
- **ai-tpm-experiment-to-production** skill: Uses risk tier for stage gate rigor and monitoring intensity
- **ai-governance-frameworks** knowledge block: Framework details underlying the classification logic
