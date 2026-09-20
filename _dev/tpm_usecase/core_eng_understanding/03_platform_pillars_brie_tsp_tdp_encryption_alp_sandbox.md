# Core Engineering Pillars: Comprehensive Research Report
**Date Generated:** May 1, 2026  
**Status:** FY26 Planning & Execution Phase

---

## EXECUTIVE SUMMARY

This report documents six critical Core Engineering pillars at Atlassian that form the foundation for enterprise customer capabilities around data management, security, and infrastructure:

1. **BRIE (Backup/Restore)** - Full tenant backup/restore for Jira, Confluence, JSM
2. **TSP (Tenant Service Platform)** - Owns Sandbox, Flip2Prod, Deep Clone, testing infrastructure
3. **TDP (Tenant Data Platform)** - Media/attachment handling, BRIE media dependencies, data movement
4. **Encryption Platform (BYOK/CMK)** - Customer Managed Keys, AWS-XKS integration, data encryption
5. **ALP (Atlassian Logging Platform)** - Audit log infrastructure, embeddable audit logs, retention
6. **Sandbox/Flip2Prod** - Sandbox creation, flip-to-production workflows for enterprise

---

## 1. BRIE (BACKUP/RESTORE INFRASTRUCTURE ENTERPRISE)

### Team Identity
- **DRI/Primary Owner:** Lakshmi Behl (Owner of roadmap)
- **Creator/Maintainer:** Viswanathan Puthukode Venkateswaran (Vishy)
- **Space:** Project BRIE (Confluence key: `BRIE`)
- **Key Contacts:** Branimir Kain (Recent contributor)

### Mission & Charter
BRIE provides full tenant backup and restore capabilities for enterprise customers across Jira, Confluence, and JSM. The platform enables large enterprises to extract their Atlassian data on their terms at enterprise scale, to preferred storage, encrypted with their own keys, in compliance-readable formats.

### FY26 Roadmap & Deliverables
**Key Page:** "BRIE High level scope and roadmap" (Page ID: 4528149004, v239)

#### Major Initiatives:
1. **Large-Scale Attachment Support** 
   - ENT-1929: "Support full backups with attachments for instances with large storage usage (>3TB)" - **SHIPPED**
   - BMW customer use case: 38M+ attachments in Confluence

2. **Data Export Capability** (Crawl-Walk-Run approach)
   - Enterprise-scale data extraction (Page: 6385501028)
   - Multi-cloud backup and restore capabilities
   - Cost efficiency for cross-cloud operations

3. **Configuration Promotion** (Sandbox Integration)
   - ENT-50: "EAP for the Ability to push (promote) Jira and JSM config data from sandbox to production"
   - Status: Public Roadmap
   - Enables config testing in Sandbox before production deployment

4. **Apps Backup & Restore**
   - ENT-311: "Apps backup and restore with 30 days retention"
   - Status: Roadmap (Internal Only)

5. **Open Beta Launch** (May 2025)
   - Review date: 2025-05-28
   - Team: Asvini, Lakshmi Behl, Piya Belhe, Ankita Murali, Branimir Kain, Tarun Jadhwani, Avishekh Das, Tanay Soley, Sukhwant Prafullit
   - Reviewers: Atul Setlur, Varun Shingal, Tobias Ladewig

6. **BMW Phase Response**
   - Proposed customer response tracking (Page: 6896839948)
   - Data residency considerations
   - Confluence backup scale support
   - Note: Only Phase 1 currently planned

### FY26 Scope Alignment
- **Squad Sign-off Status:** 12/12 incomplete (as of latest tracking)
- **CT/LT Alignment:** In progress

### Known Jira Tickets
- **ENT-1929:** Support full backups >3TB (Shipped)
- **ENT-50:** Config promotion EAP (Public Roadmap)
- **ENT-311:** Apps backup/restore 30-day retention (Internal Roadmap)

### Dependencies
- **TDP (Tenant Data Platform):** Media/attachment handling and backup support
- **Sandbox/TSP:** Config promotion and testing workflows
- **Encryption Platform:** Customer-managed key encryption for backup data

### Current Status
- **Open Beta:** Launched/In-flight (May 2025)
- **Large customer engagements:** BMW (major attachment scale), others TBD
- **Page Version Tracking:** 239 versions - highly active collaboration

### Capacity/Headcount Signals
- Large cross-functional team indicated by review panel
- Active ongoing development and customer engagement
- Regular stakeholder updates and scope reviews

---

## 2. TSP (TENANT SERVICE PLATFORM) & SANDBOX

### Team Identity
- **DRI/Primary Owner:** Harpreet Singh Juneja (FY26 Investments owner)
- **Sandbox DRI:** Sirisha Pendem
- **Space:** Tenant and Sharding Platform (Confluence key: `TENSHARDPLAT`)
- **Sandbox Space:** (Confluence key: `TESTIN`)

### Mission & Charter
TSP is the foundational platform for Atlassian's multi-tenant cloud infrastructure. Owns:
- **Sandbox/Flip2Prod:** Isolated testing environments with flip-to-production workflows
- **Deep Clone (DSAN):** Tenant data cloning for testing
- **Automation/Regression Testing:** Infrastructure for comprehensive test coverage
- **Multi-product Onboarding:** Loom, other enterprise products on shared infrastructure

### FY26 Roadmap & Deliverables

**Key Pages:**
- "TSP - FY26 Investments" (Page ID: 5477009716)
- "Sandbox Engineering Roadmap & Planning - H2FY26" (Page ID: 5822827719)
- "Sandbox Strategy & Release Plan - FY26" (Page ID: 5607997476)

#### Major Initiatives:

**1. Customer Onboarding & Scale**
- Loom: ~750K/month workspaces supported starting July 2025
- Actual as of last tracking: 93.06K workspaces
- Cost attribution and ramp tracking
- TPM coordination for each customer

**2. Sandbox Reliability & Stability (H2FY26)**
- **P0 Priority:** 98% reliability goal by end of FY26
- **Isolated Cloud Presence:** Sandbox deployment to Isolated Cloud environments
- **Config Promotion Open Beta:** Enable configuration testing workflows
- **EPM Integration:** Enterprise Product Manager integration for new product onboarding

**3. Sandbox Units & Features**
- **P0:** Sandbox Units - unblock Units GA (General Availability)
- **P1 Explore:** Dev Sandboxes, App Data Support for Sandbox FDC (if BRIE solution can be reused)

**4. Team Allocation (H2FY26)**
- **RTB (Runtime Behavior):** 15% capacity
- **DevProd (Developer Productivity):** 10% capacity  
- **CTB (Customer Trust & Business):** 75% capacity

**5. Advanced Features (Future)**
- Sandbox presence in Isolated Cloud
- Config promotion workflows
- Dev Sandboxes exploration
- App data support (pending BRIE solution)

### FY26 Scope Alignment
- Multiple roadmap pages updated April 29-May 1, 2026
- H1FY26 planning complete, H2FY26 in flight
- Strong focus on reliability and enterprise scale

### Known Jira Tickets
- **ENT-50:** Config data promotion EAP (References sandbox-to-prod capability)
- Multiple COMMIT tickets for TSP projects identified

### Dependencies
- **BRIE:** App data support and configuration backup for sandboxes
- **TDP:** Deep clone data capabilities
- **Encryption Platform:** CMK support for isolated/sandboxed environments

### Current Status
- **H2FY26:** Active planning and execution
- **Reliability Tracking:** Target 98% by FY26 end
- **Customer Onboarding:** Ongoing with Loom and other products
- **Multiple Infrastructure Initiatives:** Isolated Cloud, Units GA, EPM integration

### Capacity/Headcount Signals
- Multiple rolling roadmap pages (H1, H2, quarterly planning)
- Cross-team coordination (CTB 75%, DevProd 10%, RTB 15%)
- Active innovation projects registry

---

## 3. TDP (TENANT DATA PLATFORM)

### Team Identity
- **DRI/Primary Owner:** Alex Grach (Cost Saving Projects lead)
- **Sub-teams:** 
  - TDP SQL team (Q4 FY26 planning)
  - TDP ERS team (Entity Resolution Service)
- **Internal Space:** TDP - Internal Space (Confluence key: `DAP`)
- **Public Space:** Trusted Data Platform (TDP) (Confluence key: `TDP`)
- **Core Data Platform Space:** (Confluence key: `CDATS`)

### Mission & Charter
TDP manages enterprise-scale data platforms:
- **Media/Attachment Handling:** Central platform for managing attachments across products
- **Entity Resolution Service (ERS):** Data consistency and resolution
- **SQL Query Layer:** Queryable data access patterns
- **BRIE Media Dependencies:** Critical path for backup/restore media support
- **Data Movement & Migration:** Tenant data lifecycle management

### FY26 Roadmap & Deliverables

**Key Pages:**
- "[FY26] TDP Cost Saving Projects" (Page ID: 5636006536)
- "TDP SQL - Q4'FY26 Prep" (Page ID: 6480632149)
- "TDP ERS - Q4'FY26 Prep" (Page ID: 6478818897)
- "TDP APEX - FY26 H2 Timeline" (Page ID: 4532605605)

#### Major Initiatives:

**1. Cost Optimization (FY26 Goal)**
- **Big Goal:** $3M cost savings by cost reduction, cost avoidance, or cost attribution
- **Budget Discipline:** Stay within 5% of allocated budget quarter-over-quarter
- **Cost Efficiency Projects:** Cross-cloud backup/restore cost efficiency
- **Budget Transfers:** WIP for FY26 Q3 (Page: 5772642460)

**2. TDP SQL - Q4 FY26 Prep**
- **Planned Capacity:** 13 engineers
- **On-call Overhead:** 1.5 engineers
- **Raw Dev Weeks:** ~12 per quarter
- **Status:** Q3 major wins documented; Q4 planning in progress

**3. TDP ERS (Entity Resolution Service) - Q4 FY26 Prep**
- **Planned Capacity:** 14 engineers
- **On-call Overhead:** 2 engineers
- **Raw Dev Weeks:** ~12 per quarter
- **Total Capacity:** 109 dev weeks in Q4
- **Q3 Wins:** Major achievements documented

**4. Platform Dependencies**
- **TiDB Migration:** Moving ERS to TiDB (VLE vs ALE decision made - decided: VLE)
- **TDP Timelines:** Coordinated with Encryption Platform funding

**5. Ecosystem & JSM/O Integration**
- JSM/O TDP ERS Product roadmap coordination
- Cross-product data handling

### Q3 Planning Status
- Multiple Q3 priorities pages tracked
- Q2 priorities completed and documented
- Regular budget review and cost efficiency tracking

### Known Jira Tickets
- Cross-referenced in Confluence with COMMIT project priorities
- Integration with BRIE roadmap for media support

### Dependencies
- **BRIE:** Media backup/restore capabilities depend on TDP infrastructure
- **Encryption Platform:** Coordinate TiDB migration with encryption requirements
- **TSP:** Data movement for sandbox and deep clone operations

### Current Status
- **FY26 H2:** Active planning and execution
- **Cost Tracking:** Quarterly reviews underway
- **Capacity Planning:** Detailed engineering week allocations by Q
- **Infrastructure Evolution:** TiDB migration in progress

### Capacity/Headcount Signals
- **SQL Team:** 13 engineers
- **ERS Team:** 14 engineers  
- **Total ~27 engineers** dedicated to core TDP work
- Significant on-call and overhead allocation

---

## 4. ENCRYPTION PLATFORM (BYOK/CMK - CRYPTOR)

### Team Identity
- **DRI/Primary Owner:** Greg Zaney
- **Team Name (Internal):** Coral team (also referred to as Kelpies, Cryptor)
- **Space:** Encryption Pillar (Confluence key: `ENCRYPT`)
- **Sub-teams:** Cloud Agnostic, Ref Client, others indicated by "Coral" standup registry

### Mission & Charter
The Encryption Platform team delivers:
- **BYOK v2 (Bring Your Own Key):** Customer-managed key infrastructure
- **CMK (Customer Managed Keys):** Enterprise-grade key management
- **AWS-XKS Integration:** AWS external key store connectivity
- **Unit Creation & Policy Management:** CMK SKU and lifecycle
- **Cross-cloud Encryption:** Support for multiple cloud providers
- **Commercial & FedRamp:** Compliance variants

### FY26 Roadmap & Deliverables

**Key Page:** "Encryption Pillar FY26: CMK Planned work" (Page ID: 4929883349, v130)

#### FY26 Prioritization Challenge
Page indicates critical prioritization challenge for encryption platform in FY26.

**Top Priority Projects:**

**1. Golden Path for Internal Partner Onboarding to CMK**
- Enable internal teams (Forge, others) to self-serve CMK
- RFC: CMK Unit Creation (Page: 6556590202)
- Discussion on org lifecycle and PLS package for CMK SKU

**2. CMK Forge Scope** (Page ID: 5564211172)
- **First Priority:** CMK on Isolated Cloud (IC)
- **Later Phases:** Commercial, FedRamp
- **Status:** Atlas tracking active (last update 2025-10-23)
- **Funding:** Encryption pillar budgets approved
- **Infrastructure Decisions:** 
  - VLE vs ALE decision made (chose VLE)
  - TDP timelines for ERS migration to TiDB due to VLE decision
  - Coordination with TSP RFCs

**3. Policy Management & Verification**
- UI Design mockups completed
- On-demand policy verification workflows
- Policy validation components

**4. Encryption Inventory & Dashboard**
- Coral operational dashboard tracking
- Encryption inventory genie (ML/AI assisted)
- Runbook: Committing to Encryption Inventory Dashboard

**5. Key Shard Redesign**
- Kelpies team working on key shard optimization
- Sparring sessions documented

### FY26 Funded Projects List
(Detailed in page content)
- Multiple strategic initiatives with funding allocated
- Clear prioritization of highest-value work

### Known Jira Tickets
- Cross-referenced in roadmap and planning documents
- Integration points with TSP and TDP

### Dependencies
- **TDP:** TiDB migration impacts ERS (Entity Resolution Service)
- **TSP:** RFC coordination for unit creation and SKU management
- **BRIE:** Encrypted backup data support (customer-managed keys for backups)
- **AWS Services:** External key store integration (AWS-XKS)

### Current Status
- **FY26 Execution:** In-flight with funded projects
- **Prioritization:** Clear hierarchy of golden path first, then commercial/FedRamp
- **Infrastructure Decisions:** Major decisions made (VLE chosen, TiDB migration planned)
- **Team Activity:** High engagement indicated by recent page updates (May 1, 2026)

### Capacity/Headcount Signals
- **Team Name:** Coral (sub-teams: Kelpies, others)
- **Infrastructure:** Daily standups, retros, sprint boards
- **Innovation:** Active technical RFCs and design work
- **External Collaboration:** Cloud agnostic and ref client streams with sync meetings

### Team Operations
- **Slack:** #help-risk-assessment-platform integration
- **Operational Dashboard:** Coral OPEX tracking
- **Vulnerability Management:** Dedicated tracking and remediation workflows

---

## 5. ALP (ATLASSIAN LOGGING PLATFORM / AUDIT LOGS)

### Team Identity
- **DRI/Primary Owner:** Akshay Nambiar (Q4 FY26 planning owner)
- **Space Name:** Audit Logs (Confluence key visible in searches)
- **Related Spaces:** Cloud Security (Confluence key: related space)
- **Parent Initiative:** FY26 Audit Logs Program Governance

### Mission & Charter
ALP provides enterprise audit logging infrastructure:
- **Audit Log Ingestion:** Real-time event capture across products
- **Audit Log Platform:** Central event processing and storage
- **Embeddable Audit Logs:** Product-integrated audit capabilities
- **Log Retention & Compliance:** Data retention policies and regulatory compliance
- **Log Consumption:** Query and analysis capabilities for customers

### FY26 Roadmap & Deliverables

**Key Page:** "Audit Logs - Backup, Ingestion and Consumption: Q4 FY26 plan" (Page ID: 6729489529)

#### Milestone-Based Approach:

**Milestone 1 (Q3 FY26) - COMPLETED:**
- Ingestion system launch
- TDP Backup system launch
- Platform foundation established

**Milestone 2 (Q4 FY26) - IN PROGRESS:**
- **May 1, 2026:** Begin internal testing (UI testing readiness)
- **Goal:** Sufficient testing time before going live
- **Audit Log Team Requirement:** "Dynamic materialization" functionality needed by 2026-05-01 for UI testing enablement

#### Key FY26 Initiatives:

**1. Dynamic Materialization** (Critical Path Item)
- Required for UI testing and consumption features
- Enables real-time data presentation for audit logs
- Timeline pressure: Q4 completion critical

**2. Log Backup & Ingestion Integration** (TDP Dependency)
- Coordinate with TDP SQL and ERS teams
- Cross-cloud backup support for audit logs
- Cost optimization considerations

**3. Log Consumption & Querying**
- End-user facing capabilities
- Search and analysis interfaces
- Compliance report generation

**4. Product Integration Expansion**
- Confluence audit log onboarding ongoing
- Jira audit events handling
- JSM audit log integration
- App activity logs (GA delivery planning)

### FY26 Program Governance
**Key Page:** "FY26 Audit Logs Program Governance - Commits, Miles & Risks" (Page ID: 5410716135)

- **L3 Product KR Thesis:** Defined for FY26 (Page: 5380997877)
- **Risk Tracking:** Known risks and mitigation strategies
- **Milestone Tracking:** Regular updates and status

### Known Integration Points
- **Service Accounts Support:** ALP service account audit tracking (Page: 4987229499)
- **Confluence Alignment:** Cross-alignment briefing (Page: 6888306906)
- **UGC Handling:** User-generated content transition plan (Page: 6415000525)

### Known Jira Tickets
- **AGRC-15359:** Logs - platform setting audit, API token creation, import/export functions (Jira Align reference)
- **HOT-120786:** Confluence Audit Log Platform UGC Data vulnerability investigation
- **HOT-113300:** Sev3 - Connect and Forge JTI incorrectly sent as API token id

### Dependencies
- **TDP:** SQL and ERS teams for log storage and querying
- **BRIE:** Audit log backup and retention coordination
- **Product Teams:** Confluence, Jira, JSM for audit event feeds

### Current Status
- **Q4 FY26:** Active execution, internal testing beginning (May 1, 2026)
- **Milestone Tracking:** Milestone 1 complete, Milestone 2 in-flight
- **Critical Path:** Dynamic materialization is blocking further progress
- **Quality:** Testing phase initiation signals stability focus

### Capacity/Headcount Signals
- **Program Governance:** Formal tracking of commits and risks
- **Cross-team Coordination:** Multiple product team dependencies
- **Timeline Pressure:** Q4 completion deadlines driving active work

---

## 6. SANDBOX (FLIP2PROD)

### Team Identity
- **DRI/Primary Owner:** Sirisha Pendem (Sandbox Engineering)
- **Parent Organization:** TSP (Tenant Service Platform)
- **Space:** Sandbox (Confluence key: `TESTIN`)
- **Related Spaces:** Units Program (fka Collaboration Context)

### Mission & Charter
Sandbox provides:
- **Sandbox Creation & Management:** Isolated environments for customer testing
- **Flip-to-Production Workflows:** Promote sandbox configurations to production
- **Deep Clone (DSAN):** Full data cloning for testing scenarios
- **Enterprise Customer Support:** Dedicated sandbox instances for large customers
- **Configuration Testing:** Safe testing before production deployment

### FY26 Roadmap & Key Deliverables

**Key Pages:**
- "Sandbox Engineering Roadmap & Planning - H2FY26" (Page ID: 5822827719, Owner: Sirisha Pendem)
- "Sandbox Strategy & Release Plan - FY26" (Page ID: 5607997476)
- "Sandbox Engineering Roadmap & Planning - H1FY26" (Page ID: 5301028223)

#### P0 Priorities (High):

**1. Reliability Goal: 98% by End of FY26**
- Current tracking and improvements in progress
- SLO definition and monitoring
- Incident response and mitigation

**2. Sandbox Presence in Isolated Cloud**
- Multi-cloud deployment strategy
- Isolated Cloud infrastructure readiness
- Customer data residency support

**3. Config Promo Open Beta**
- Configuration promotion workflows
- Jira and JSM config support (ENT-50)
- Production readiness validation

**4. EPM Integration**
- Enterprise Product Manager integration
- Onboarding new products to Sandbox infrastructure
- Self-service product enablement

**5. Sandbox Units to Unblock Units GA**
- Units feature general availability dependent on sandbox units support
- Cross-product dependency for Units program

#### P1 Priorities (Medium):

**1. Dev Sandboxes Exploration**
- Developer sandbox capabilities
- Developer productivity improvements

**2. App Data Support for Sandbox FDC**
- App data integration with Sandbox
- Potential BRIE solution reuse
- Functional data center (FDC) support

### DevAI Sandbox Security Review
- **Security Review:** SECREV-5592 (Page: 6173408719)
- **FY26 DevAI Sandbox:** Scoping document in progress
- **Atlas Project:** Tracked for DevAI initiatives

### Known Jira Tickets
- **ENT-50:** Config promotion EAP (Key deliverable for Sandbox)
- **ENT-311:** Apps backup/restore (Related to app data support)

### Roadmap Issues Tracking
- **Bug Bash Tracking:** Active issue tracking during releases (Page: 5100603178)
- **Known Issues:** Documented with emoji legend (pre-existing, new, blocking, etc.)

### Dependencies
- **BRIE:** App data backup and restore for sandbox testing
- **TSP:** Core infrastructure and platform services
- **Encryption Platform:** CMK support for isolated/sandboxed environments
- **TDP:** Deep clone and data movement capabilities

### Current Status
- **H2FY26:** Active engineering roadmap execution
- **Reliability Tracking:** 98% goal for FY26 end
- **Feature Development:** Config Promo in Open Beta
- **Infrastructure Evolution:** Isolated Cloud deployment in progress

### Capacity/Headcount Signals
- **Team Lead:** Sirisha Pendem as primary DRI
- **Multiple Roadmaps:** Quarterly planning for H1 and H2
- **Innovation Projects:** Registry of FY26 innovation initiatives
- **Cross-team Coordination:** Heavy dependencies on BRIE, TSP, Encryption

---

## CROSS-PILLAR INTEGRATION MATRIX

### Key Dependencies and Interactions

```
BRIE (Backup/Restore)
├── Depends on: TDP (media/attachment handling)
├── Depends on: Encryption (customer-managed key encryption)
├── Depends on: Sandbox (config backup/restore)
└── Enables: Forge apps (backup/restore capability)

TSP/Sandbox (Tenant Service Platform & Flip2Prod)
├── Depends on: BRIE (app data support, config backup)
├── Depends on: TDP (deep clone, data movement)
├── Depends on: Encryption (CMK for isolated environments)
└── Enables: Customer testing and configuration management

TDP (Tenant Data Platform)
├── Depends on: Encryption (TiDB migration with VLE vs ALE)
├── Depends on: ALP (audit log storage)
├── Enables: BRIE (media/attachment handling)
├── Enables: TSP (deep clone/data movement)
└── Enables: All products (centralized data platform)

Encryption Platform (BYOK/CMK)
├── Depends on: TDP (ERS migration to TiDB)
├── Depends on: TSP (unit creation, org lifecycle)
├── Enables: BRIE (encrypted backup data)
├── Enables: All products (customer-managed encryption)
└── Enables: Compliance (FedRamp, HIPAA, others)

ALP (Audit Logs)
├── Depends on: TDP (log storage and querying)
├── Depends on: BRIE (log backup and retention)
└── Enables: All products (audit trail compliance)

Sandbox (Flip2Prod)
├── Depends on: BRIE (app data support)
├── Depends on: TSP (infrastructure)
├── Depends on: Encryption (customer-managed keys)
└── Enables: Customers (safe testing and config management)
```

### Critical Path Items (Blocking Other Work)

1. **Dynamic Materialization (ALP)** - Blocking audit log UI testing (Q4 deadline: May 1, 2026)
2. **TiDB Migration (TDP)** - Blocking CMK v2 GA (Encryption dependency)
3. **App Data Support (BRIE)** - Blocking Sandbox FDC and app backup features
4. **Config Promo GA (Sandbox)** - Blocking sandbox-to-prod workflows for enterprises

### FY26 Funding Status
- **BRIE:** Funded, Open Beta in-flight
- **TSP/Sandbox:** Funded, H2 execution in progress
- **TDP:** Funded, aggressive cost optimization targets ($3M goal)
- **Encryption:** Funded with clear prioritization (golden path first)
- **ALP:** Funded, Q4 completion timeline critical
- **Overall:** All pillars have FY26 funding and committed roadmaps

---

## KEY PEOPLE & CONTACTS

### BRIE
- **DRI:** Lakshmi Behl
- **Architect/Creator:** Viswanathan Puthukode Venkateswaran (Vishy)
- **Contributors:** Branimir Kain, Ankita Murali, Tarun Jadhwani, others

### TSP/Sandbox
- **TSP DRI:** Harpreet Singh Juneja
- **Sandbox DRI:** Sirisha Pendem
- **Multiple team leads** for customer onboarding and infrastructure

### TDP
- **Cost Optimization Lead:** Alex Grach
- **SQL Team Lead:** Prashanth Yerramilli (implied)
- **Multiple sub-teams:** ERS, SQL, APEX

### Encryption
- **DRI:** Greg Zaney
- **Team:** Coral (including Kelpies sub-team)
- **Cloud Agnostic & Ref Client:** Multiple stream leads

### ALP
- **Q4 Planning Lead:** Akshay Nambiar
- **Program Governance:** Cloud Security team
- **Product Integration:** Multiple teams (Confluence, Jira, JSM)

### Sandbox
- **Engineering DRI:** Sirisha Pendem
- **Cross-team:** Multiple product integration leads

---

## CONFLUENCE SPACES REFERENCE

| Pillar | Space Name | Key | Page Count | Focus |
|--------|-----------|-----|-----------|-------|
| BRIE | Project BRIE | BRIE | 20+ recent | Backup/restore roadmaps, customer cases |
| TSP | Tenant and Sharding Platform | TENSHARDPLAT | 15+ | Infrastructure investments, onboarding |
| TSP/Sandbox | Sandbox | TESTIN | 15+ | Roadmaps, release planning, engineering |
| TDP | Trusted Data Platform | TDP | Multiple | Ecosystem roadmap, Forge alignment |
| TDP | Core Data Platform | CDATS | 15+ | SQL, ERS, Q3/Q4 planning |
| TDP | TDP - Internal Space | DAP | 10+ | Cost savings, budget tracking, APEX |
| Encryption | Encryption Pillar | ENCRYPT | 20+ | CMK, BYOK, Forge scope, team operations |
| ALP | Cloud Security | (implicit) | 15+ | Audit logs governance, program tracking |
| ALP | Audit Logs | (audit logs space) | 10+ | Backup, ingestion, consumption planning |

---

## JIRA PROJECT REFERENCES

- **ENT (Enterprise):** Primary tracking for customer-facing features
  - ENT-1929: BRIE attachment support (Shipped)
  - ENT-50: Sandbox config promotion (Public Roadmap)
  - ENT-311: App backup/restore (Internal Roadmap)

- **COMMIT:** Core engineering priorities and cross-team work
  - Referenced for BRIE, TSP, Encryption, ALP initiatives
  - 60+ day lookback shows active planning and execution

- **ATLAS:** Strategic project tracking for all pillars
  - CMK Forge (Encryption): Active tracking
  - TDP initiatives: Budgeting and dependencies
  - Multiple pillar projects tracked for portfolio management

- **Jira Align (AGRC):** Specialized audit and compliance tracking
  - AGRC-15359: Logs platform setting audit
  - ALP integration point for Jira-specific features

---

## RISK & STATUS SUMMARY

### On Track
- ✅ **BRIE:** Open Beta launched (May 2025), large customer engagement (BMW)
- ✅ **TSP/Sandbox:** H2 roadmap in execution, 98% reliability target
- ✅ **Encryption:** Funded projects with clear prioritization
- ✅ **TDP:** Multiple teams with quarterly capacity planning complete

### At Risk or Attention Required
- ⚠️ **ALP:** Dynamic materialization is blocking UI testing (Q4 critical path)
- ⚠️ **TDP:** TiDB migration impacts both TDP and Encryption timelines
- ⚠️ **BRIE/Sandbox:** App data support dependency coordination needed
- ⚠️ **Overall:** Heavy interdependencies create schedule risk if one pillar slips

### Future Considerations
- **Commercial & FedRamp:** Encryption platform secondary priorities (after IC golden path)
- **Cost Optimization:** TDP aggressive $3M goal may require scope tradeoffs
- **Capacity Planning:** Multiple pillars at ~14-15 engineer teams - resource constraints

---

## APPENDIX: DATA SOURCES

### Confluence Pages Retrieved
- **BRIE Roadmap:** 4528149004 (v239)
- **Forge BYOK/BRIE SoW:** 4915529768 (v17)
- **Encryption CMK FY26:** 4929883349 (v130)
- **BRIE Open Beta Launch Review:** 5293512153 (v160)
- **TSP FY26 Investments:** 5477009716
- **Sandbox H2FY26 Roadmap:** 5822827719
- **Audit Logs Q4 Plan:** 6729489529
- **TDP Cost Saving:** 5636006536
- **CMK Forge Scope:** 5564211172

### Jira Issues Retrieved
- ENT-1929, ENT-50, ENT-311
- Multiple COMMIT project references

### Search Results Analyzed
- TSP/Sandbox/Flip2Prod focused queries
- ALP/Audit Log platform queries
- TDP platform queries
- BRIE space queries
- ENCRYPT space queries

### Data Collection Date
May 1, 2026, 08:31-08:36 UTC

---

**Report Generated By:** Rovo Dev Research Agent  
**Classification:** Internal Engineering Documentation  
**Last Updated:** May 1, 2026
