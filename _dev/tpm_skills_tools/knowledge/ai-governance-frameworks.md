# AI Governance Frameworks Reference

This knowledge block provides reference material on the key AI governance frameworks that underpin the AI TPM's launch readiness and lifecycle management skills. It covers NIST AI RMF, ISO/IEC 42001 (AIMS), EU AI Act risk classifications, and their practical mapping to launch gate checklist items.

## 1. NIST AI Risk Management Framework (AI RMF 1.0)

### Overview

The NIST AI RMF provides a voluntary framework for managing risks in AI systems across four core functions: **Govern, Map, Measure, Manage**. It is not prescriptive about specific controls but establishes trustworthiness characteristics that AI systems should exhibit.

### Core Functions

#### GOVERN — Policies, Processes, and Accountability
- Establish AI risk management policies and governance structures
- Define roles, responsibilities, and accountability for AI systems
- Set organizational risk appetite and risk tolerance thresholds
- Ensure workforce diversity and AI literacy for oversight roles
- Document and maintain AI system inventory

**Launch Gate Mapping:**
- AI policy and scope confirmed
- AI System Owner and governance routing defined
- Risk tier assigned and aligned with risk appetite
- AI system inventoried; system card/use-case profile exists
- Required reviews (SBCR, privacy, responsible tech) completed

#### MAP — Context, Use Cases, and Risk Identification
- Document intended purpose, context of use, and target populations
- Identify potential impacts on individuals, groups, and society
- Catalog data sources, classifications, and sensitivity levels
- Map third-party and supply-chain components
- Identify key risks using AI risk taxonomy with likelihood/impact ratings

**Launch Gate Mapping:**
- Use-case purpose, scope, and actors documented
- Impacts on individuals/groups/society identified
- Data sources, classifications, PII, residency, retention documented
- Third-party/supply-chain components listed
- Key risks identified with likelihood/impact ratings

#### MEASURE — Metrics, Testing, and Evaluation
- Define trustworthiness metrics and TEVV (Test, Evaluation, Verification, Validation) plan
- Conduct safety, security, privacy, and fairness evaluations
- Ensure evaluation reflects deployment context (not just lab conditions)
- Specify monitoring metrics and user feedback channels
- Implement independent review for higher-risk systems

**Launch Gate Mapping:**
- Trustworthiness metrics and TEVV plan documented
- Safety, security, privacy, fairness evaluations present (tier-appropriate)
- Evaluation reflects production deployment context
- Monitoring metrics and feedback channels specified

#### MANAGE — Risk Treatment, Controls, and Operations
- Prioritize risks based on MAP/MEASURE outputs
- Implement risk response strategies (avoid, mitigate, transfer, accept)
- Establish incident response and recovery procedures
- Implement continuous improvement and control adjustment
- Plan for lifecycle reviews and decommissioning

**Launch Gate Mapping:**
- Risk treatment plan with controls and owners
- Platform guardrails configured (moderation, sandboxing, RBAC, quotas)
- Incident playbooks, kill-switches, rollback plans documented
- Lifecycle plan for re-assessment and decommissioning defined

### Trustworthiness Characteristics

The NIST AI RMF defines seven trustworthiness characteristics:

| Characteristic | Description | Launch Gate Evidence |
|---|---|---|
| **Valid & Reliable** | System performs as intended across conditions | Offline/online metrics, baseline comparison |
| **Safe** | System does not endanger human life, health, or environment | Safety testing, red-team results |
| **Secure & Resilient** | System resists attacks and recovers from failures | Threat model, SBCR, failover testing |
| **Accountable & Transparent** | Clear ownership and disclosure of AI use | Model card, system documentation, disclosure plan |
| **Explainable & Interpretable** | Users can understand AI outputs and reasoning | Explainability documentation, user-facing explanations |
| **Privacy-Enhanced** | System protects personal data and user autonomy | DPIA, privacy review, data minimization |
| **Fair (Bias Managed)** | System treats all groups equitably | Fairness evaluation, slice analysis, bias testing |

## 2. ISO/IEC 42001:2023 — AI Management System (AIMS)

### Overview

ISO/IEC 42001 specifies requirements for establishing, implementing, maintaining, and continually improving an AI Management System (AIMS). It follows the ISO management system structure (Plan-Do-Check-Act) and includes Annex A controls specific to AI.

### Key Clauses Relevant to Launch Gates

| Clause | Topic | Launch Gate Relevance |
|---|---|---|
| 4.1-4.2 | Context and interested parties | Stakeholder identification in system card |
| 5.1-5.3 | Leadership, policy, roles | AI policy, system ownership |
| 6.1.2 | AI risk assessment | Risk tier classification, risk register |
| 6.1.3 | AI risk treatment | Treatment plans, control selection |
| 6.1.4 | AI system impact assessment | AIIA for Medium/High risk systems |
| 8.1-8.4 | Operational planning and control | Lifecycle management, change control |
| 9.1-9.3 | Performance evaluation | Monitoring, measurement, management review |
| 10.1-10.2 | Improvement | Incident response, corrective actions |

### Annex A Controls

Key Annex A controls mapped to launch gates:

| Control | Domain | Gate Check |
|---|---|---|
| A.2 | AI policies | Policy compliance verified |
| A.3 | Internal organization | Roles and responsibilities assigned |
| A.4 | Resources for AI systems | Compute, data, and human resources adequate |
| A.5 | AI system impact assessment | AIIA completed (Medium/High tier) |
| A.6 | AI system lifecycle | Lifecycle stages documented |
| A.7 | Data for AI systems | Data governance, quality, lineage documented |
| A.8 | Information for interested parties | Transparency, disclosure, appeals mechanisms |
| A.9 | Use of AI systems | Usage guidelines, limitations documented |
| A.10 | Third-party relationships | Vendor/supplier AI components assessed |

## 3. EU AI Act Risk Classifications

### Risk Tiers

The EU AI Act classifies AI systems into four risk levels:

| Tier | Description | Obligations | Internal Mapping |
|---|---|---|---|
| **Unacceptable** | Social scoring, manipulative behavior exploiting vulnerabilities, biometric categorization for protected traits, workplace emotion recognition | Prohibited | Tier 0 — Block intake, legal escalation |
| **High Risk** | AI in: employment/HR, credit, access to public services, law enforcement, health/safety, education, democratic processes | Full compliance: risk management, data governance, transparency, human oversight, accuracy, robustness, cybersecurity | Tier 1 — Full governance path |
| **Limited Risk** | Chatbots, deepfake generators, emotion recognition (non-prohibited) | Transparency obligations (disclosure that AI is being used) | Tier 2 — Standard governance |
| **Minimal Risk** | Spam filters, AI in video games, inventory management | No specific obligations | Tier 3 — Light-touch governance |

### High-Risk Sector Checklist

When classifying risk tier, check if the AI system operates in these sectors:
- Biometric identification and categorization
- Management and operation of critical infrastructure
- Education and vocational training (access, assessment)
- Employment, worker management, recruitment
- Access to essential services (credit, insurance, social benefits)
- Law enforcement (crime prediction, evidence evaluation)
- Migration, asylum, and border control
- Administration of justice and democratic processes

If **yes** to any: minimum **High** risk tier, regardless of other factors.

## 4. Framework Cross-Reference Matrix

| Launch Gate Check | NIST AI RMF | ISO 42001 | EU AI Act |
|---|---|---|---|
| System documentation | MAP 1.1-1.6 | A.6, A.9 | Art. 11 (Technical Documentation) |
| Risk assessment | MAP 5.1-5.2 | 6.1.2 | Art. 9 (Risk Management) |
| Data governance | MAP 2.1-2.3 | A.7 | Art. 10 (Data Governance) |
| Impact assessment | MAP 2.3, 5.1 | A.5, 6.1.4 | Art. 27 (Fundamental Rights Impact) |
| Performance metrics | MEASURE 1-2 | 9.1 | Art. 15 (Accuracy, Robustness) |
| Fairness evaluation | MEASURE 2.6-2.11 | A.8 | Art. 10 (Bias Prevention) |
| Security controls | MANAGE 2.3-2.4 | A.4 | Art. 15 (Cybersecurity) |
| Transparency | GOVERN 1.2, MAP 1.6 | A.8 | Art. 13 (Transparency) |
| Human oversight | GOVERN 1.3-1.4 | A.3 | Art. 14 (Human Oversight) |
| Incident response | MANAGE 4.1-4.2 | 10.2 | Art. 62 (Reporting) |
| Post-market monitoring | MANAGE 1-4 | 9.1, 10.1 | Art. 72 (Post-Market Monitoring) |

## 5. Practical Application for AI TPM Skills

### How Frameworks Map to Autonomy Tiers

| Framework Activity | AI TPM Autonomy | Rationale |
|---|---|---|
| Check artifact existence | 🟢 Autonomous | Factual verification, no judgment |
| Populate checklists from discovered data | 🟢 Autonomous | Data assembly, no decision |
| Suggest risk tier based on rubric | 🟢 Autonomous | Rules-based classification |
| Draft compliance summary | 🟢 Autonomous | Synthesis, no commitment |
| Approve risk tier assignment | 🟡 Confirm | Classification affects governance rigor |
| Accept residual risk | 🔴 Human Required | Legal/business accountability |
| Approve launch decision | 🔴 Human Required | Organizational accountability |
| Override framework requirements | 🔴 Human Required | Exception requires human judgment |
| Waive missing evidence | 🔴 Human Required | Compliance decision |

### Related Skills and Tools

- **ai-tpm-launch-readiness-gate**: Primary consumer — uses framework checklists for gate evidence collection
- **ai-tpm-experiment-to-production**: Uses framework requirements to set gate criteria at each lifecycle stage
- **risk-tier-classification**: Detailed classification logic informed by these frameworks
- **twg**: Tool for querying and creating governance artifacts in Jira/Confluence
- **confirmation**: Tool for human approval of framework-mandated decisions
