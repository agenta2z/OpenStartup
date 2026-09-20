# AI/ML Program Risk Taxonomy & Category Reference

This knowledge block provides a comprehensive AI/ML risk taxonomy for use by the AI Technical Program Manager when categorizing risks in RAID registers. It maps internal categories to industry frameworks (NIST AI RMF, Google SAIF, ISO 42001) and provides keyword-based auto-detection guidance.

## Related Skills and Tools
- **Skill**: `ai-tpm-risk-dependency-review` — uses this taxonomy for risk categorization in Section 3.2 and 5.2
- **Knowledge**: `raid-register-data-model` — defines the `category_primary` and `category_secondary` fields

---

## 1. Primary Category Definitions

### 1.1 Model Quality & Safety

**Scope**: Risks arising from the AI/ML model's behavior, performance, and safety properties.

**Sub-categories**:
| Sub-category | Description | Example Risk |
|-------------|-------------|--------------|
| Accuracy & Reliability | Model produces incorrect, inconsistent, or unreliable outputs | "Summarization model hallucinates citations in 8% of outputs" |
| Robustness & Drift | Model degrades over time or under distribution shift | "Recommendation accuracy drops 15% after data schema migration" |
| Adversarial Robustness | Susceptibility to prompt injection, poisoning, model extraction | "Users can bypass content filters via indirect prompt injection" |
| Explainability | Inability to explain model decisions to users or auditors | "Cannot explain why model flagged customer transaction as fraudulent" |
| Safety & Harmful Output | Model produces harmful, biased, or dangerous content | "Model generates medical advice that contradicts clinical guidelines" |
| Model Artifact Integrity | Tampered checkpoints, supply chain attacks on model files | "Pre-trained model checkpoint downloaded from unverified source" |

**NIST AI RMF Mapping**: Validity & Reliability (MEASURE), Safety (MANAGE), Resilience (MANAGE)

**Auto-detection keywords**: `bias`, `fairness`, `hallucination`, `drift`, `accuracy`, `robustness`, `adversarial`, `jailbreak`, `safety`, `harmful`, `toxic`, `explainability`, `interpretability`, `model quality`, `evaluation`, `benchmark`

### 1.2 Data & Privacy

**Scope**: Risks related to data used in AI systems — training data, evaluation data, user data processed during inference, and data governance.

**Sub-categories**:
| Sub-category | Description | Example Risk |
|-------------|-------------|--------------|
| Training Data Quality | Incomplete, biased, or stale training data | "Training set lacks representation of non-English queries" |
| Unauthorized Training Data | Use of data without proper consent or licensing | "Model trained on customer data without explicit opt-in" |
| PII Exposure | Model memorizes or leaks personally identifiable information | "Model reproduces customer email addresses from training data" |
| Telemetry & Retention | Vendor logs prompts/responses beyond policy requirements | "LLM provider retains prompt data for 30 days vs our 0-day policy" |
| Data Residency | Data processed or stored in non-compliant jurisdictions | "EU customer data sent to US-based LLM API endpoint" |
| Data Pipeline Integrity | Corruption, schema changes, or gaps in data pipelines | "Feature store schema migration broke model input pipeline" |

**NIST AI RMF Mapping**: Privacy (GOVERN, MAP), Data Governance

**Auto-detection keywords**: `PII`, `data leak`, `training data`, `telemetry`, `retention`, `GDPR`, `data residency`, `logging`, `consent`, `data quality`, `labeling`, `annotation`

### 1.3 Infra, Performance & Cost

**Scope**: Risks from infrastructure limitations, performance degradation, and uncontrolled costs.

**Sub-categories**:
| Sub-category | Description | Example Risk |
|-------------|-------------|--------------|
| Compute & GPU Capacity | Insufficient compute for training or inference | "GPU allocation insufficient for fine-tuning within sprint" |
| Token & Cost Overruns | LLM API costs exceed budget due to usage spikes | "Prompt chaining causes 4x token usage vs estimates" |
| Latency & SLOs | Inference latency exceeds customer-facing SLOs | "RAG pipeline p99 latency exceeds 3s SLO during peak" |
| Scaling Limits | System cannot handle projected load growth | "Model serving infrastructure tops out at 500 QPS vs 2000 target" |
| Pipeline Reliability | ML pipeline failures causing training/deployment delays | "Nightly retraining job fails 3 of 7 days due to OOM" |

**NIST AI RMF Mapping**: Operational risk (cross-cutting)

**Auto-detection keywords**: `GPU`, `token`, `compute`, `latency`, `SLO`, `capacity`, `scaling`, `cost`, `quota`, `OOM`, `pipeline`, `throughput`, `availability`

### 1.4 Vendor & Third-Party

**Scope**: Risks from external AI/ML providers, models, plugins, and integrations.

**Sub-categories**:
| Sub-category | Description | Example Risk |
|-------------|-------------|--------------|
| Provider SLA & Reliability | Vendor API outages or degradation | "OpenAI API had 3 outages last month; no committed SLA" |
| Model Deprecation | Vendor deprecates model version without migration path | "GPT-4 variant being sunset with 60-day notice" |
| Plugin & Extension Risks | Third-party plugins executing unsafe actions | "Marketplace plugin makes unapproved external API calls" |
| Incident Transparency | Vendor doesn't share incident details or root causes | "Provider refused to share post-mortem for data processing incident" |
| API Rate Limits | Provider throttling impacts production workloads | "Rate limiting during peak hours causes request queuing" |
| Contractual Gaps | Missing data processing agreements or usage terms | "No DPA in place for new LLM provider processing EU data" |

**NIST AI RMF Mapping**: Security & Compliance (cross-cutting), GOVERN

**Auto-detection keywords**: `OpenAI`, `Anthropic`, `AWS`, `Azure`, `vendor`, `SLA`, `outage`, `plugin`, `third-party`, `API limit`, `rate limit`, `deprecation`, `provider`

### 1.5 Governance & Compliance

**Scope**: Risks from inadequate governance structures, missing documentation, and regulatory non-compliance.

**Sub-categories**:
| Sub-category | Description | Example Risk |
|-------------|-------------|--------------|
| Regulatory Non-Compliance | Violation of AI-specific regulations | "Feature classified as high-risk under EU AI Act without required conformity assessment" |
| Missing Risk Assessments | Required AI risk assessments not completed | "No DPIA completed for customer-facing AI feature processing personal data" |
| Documentation Gaps | Insufficient model cards, system cards, or use-case profiles | "No model card documenting training data, limitations, and intended use" |
| Ownership Gaps | Unclear accountability for AI system outcomes | "No defined owner for monitoring model fairness metrics post-launch" |
| Audit Readiness | Unable to demonstrate compliance to auditors | "Cannot reproduce model training run from 6 months ago" |
| Policy Misalignment | Internal AI policies not followed | "Team shipped AI feature without completing AI use-case intake form" |

**NIST AI RMF Mapping**: GOVERN (all sub-functions)

**Auto-detection keywords**: `DPIA`, `AI Act`, `EU AI Act`, `ISO42001`, `ISO 42001`, `documentation`, `risk assessment`, `intake`, `policy`, `audit`, `compliance`, `regulation`, `model card`, `system card`

### 1.6 GTM, Customer & Product Outcomes

**Scope**: Risks to business outcomes, customer experience, and market positioning from AI system behavior.

**Sub-categories**:
| Sub-category | Description | Example Risk |
|-------------|-------------|--------------|
| Customer Harm | AI outputs cause harm or significant inconvenience | "AI assistant gives incorrect tax advice to small business customers" |
| Support Volume Spikes | AI quality issues drive support ticket increases | "AI feature launch projected to increase Tier 1 tickets by 40%" |
| Adoption Failure | Users reject or distrust AI features | "Only 12% of beta users continue using AI suggestions after first week" |
| Reputation & Brand | AI incidents damage company reputation | "Social media backlash from biased AI-generated content" |
| Change Management | Insufficient preparation for AI-driven workflow changes | "Sales team not trained on AI-powered CRM; reverts to manual process" |
| Certification Risk | AI failures jeopardize existing certifications | "AI data handling may invalidate SOC 2 Type II certification" |

**NIST AI RMF Mapping**: MAP (use-case context), MANAGE (deployment monitoring)

**Auto-detection keywords**: `NPS`, `support volume`, `customer harm`, `reputation`, `launch`, `adoption`, `change management`, `certification`, `SOC2`, `brand`, `churn`, `satisfaction`

---

## 2. Cross-Category Mapping Rules

Some risks span multiple categories. Use these rules to assign primary and secondary:

| If Risk Involves... | Primary Category | Secondary Category |
|---------------------|-----------------|-------------------|
| Bias causing customer harm | Model Quality & Safety | GTM, Customer & Product |
| PII leak via model memorization | Data & Privacy | Governance & Compliance |
| Vendor outage causing latency SLO breach | Vendor & Third-Party | Infra, Performance & Cost |
| RAG data poisoning | Model Quality & Safety | Data & Privacy |
| Missing DPIA for AI feature | Governance & Compliance | Data & Privacy |
| GPU cost overrun from vendor API pricing | Infra, Performance & Cost | Vendor & Third-Party |
| AI feature launch without documentation | Governance & Compliance | GTM, Customer & Product |

---

## 3. Industry Framework Crosswalk

| Internal Category | NIST AI RMF | Google SAIF | ISO 42001 |
|---|---|---|---|
| Model Quality & Safety | MEASURE 2.5-2.8, MANAGE 2.1-2.4 | Secure AI supply chain, Automate defenses | A.6.2.4 (AI verification), A.6.2.6 (AI validation) |
| Data & Privacy | MAP 2.3, GOVERN 1.5 | Secure training data, Protect user data | A.6.2.3 (Data management), A.8 (Data for AI) |
| Infra, Performance & Cost | MANAGE 4.1-4.2 | Secure infrastructure | A.6.2.5 (AI development) |
| Vendor & Third-Party | GOVERN 6.1, MAP 3.4 | Vet third-party models | A.6.2.7 (Third-party), A.5.4 (Supplier) |
| Governance & Compliance | GOVERN 1.1-1.7, MAP 1.1-1.6 | Org-level security foundation | A.5 (Policy), A.6.1 (Org controls) |
| GTM, Customer & Product | MAP 2.1-2.2, MANAGE 3.1-3.2 | Understand business context | A.6.2.8 (AI system release), A.9 (Performance) |
