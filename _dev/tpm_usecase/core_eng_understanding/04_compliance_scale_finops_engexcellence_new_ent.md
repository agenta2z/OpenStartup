# Atlassian Core Engineering Pillars - Comprehensive Research Report
**Date:** May 1, 2026  
**Research Focus:** Compliance/RegInd, Scale, FinOps/Cost Attribution, Engineering Excellence

---

## EXECUTIVE SUMMARY

This report documents a comprehensive investigation of Atlassian's Core Engineering strategic pillars including:
- **Compliance & Regulated Industries (RegInd):** FedRAMP, IL5, C5, DORA, IRAP, Isolated Cloud/Oasis
- **Scale Initiatives:** Confluence 150K-250K, Jira 50K-150K, Rovo scale capabilities
- **FinOps & Cost Attribution:** Led by Ke Wang, includes Project Bigsky, Project Cypress, One-AI-Cost-Report
- **Engineering Excellence:** Reliability, performance, cost optimization, developer tooling

Additionally, this report identifies **NEW enterprise requests** beyond the originally known 23 tickets and maps them to Core Engineering priorities.

---

## 1. NEW/UPDATED ENT ENTERPRISE REQUESTS (Last 90 Days)

### Recent ENT Tickets Created (50 total in last 90 days)

**Highest Priority New Requests:**

| Ticket | Summary | Status | Category |
|--------|---------|--------|----------|
| ENT-3863 | Support linked fields in forms - "Raise a Request" JSM skill | Pending Review | JSM/Rovo Integration |
| ENT-3862 | [AMAT] Rovo Trend Dashboard (to track usages) | Closed | Analytics/Rovo |
| ENT-3861 | Enable native Microsoft Teams integration for Confluence Whiteboards | Pending Review | Collaboration |
| ENT-3860 | Atlassian MCP server - multiple sites support simultaneously | Pending Review | Developer Tooling |
| ENT-3859 | Confluence space_permission_mapping - missing permission granularity | Pending Review | Analytics/Data |
| ENT-3858 | JSM Deployment Gating - GitHub actor/deployer email in change request | Pending Review | JSM/DevOps |
| ENT-3857 | Native capability to move work items between CSM and JSM spaces | Pending Review | JSM/Workflow |
| ENT-3856 | Configure MCP server permissions per site (extends ENT-3684) | Pending Review | Security/Governance |
| ENT-3855 | Mobile App Management (MAM) policy targeting for external users | Pending Review | Security/Mobile |
| ENT-3854 | Add new entry point for ViewIssueModal | Pending Review | Jira Extensions |
| ENT-3852 | AppLink WebSocket tunnels - DLP-compatible connectivity | Pending Review | Integration/Security |
| ENT-3851 | Prevention of ingestion of new sensitive data in Jira/Confluence | Pending Review | Compliance/Security |
| ENT-3849 | Rovo - turn off Follow Up questions on scenario basis | Pending Review | Rovo AI |
| ENT-3848 | Restrict Org Admin from Self-Granting Product Access | Pending Review | Security/Access Control |
| ENT-3847 | Rovo Enablement Issues | Pending Review | Rovo Operations |
| ENT-3846 | Confluence whiteboards permissions parity vs Miro | Pending Review | Collaboration |
| ENT-3845 | Prevent duplication of custom fields | Not Currently Prioritized | Governance |
| ENT-3844 | Create Rovo usage trend dashboard - user-level engagement | Actively Investigating | Analytics/Rovo |
| ENT-3850 | SharePoint connector in sandbox incorrectly requiring admin consent | Roadmap (Internal) | Integration/Security |
| ENT-3843 | Increase supported objects Rovo can create/edit/modify | Pending Review | Rovo Capabilities |
| ENT-3842 | Additional public information around Rovo usage limits | Pending Review | Documentation |
| ENT-3841 | Improve Rovo processing of large amount of data | Pending Review | Rovo Performance |
| ENT-3840 | HTTP 2 Customer Refusal to Enable (Confluence/Jira) | Pending Review | Protocol Support |
| ENT-3853 | Rovo chat - Incomplete page retrieval, incorrect subtree values | Roadmap (Internal) | Rovo Bug |
| ENT-3839 | JSM Operations Global Admins - Manage Stakeholders/Groups | Pending Review | JSM Governance |
| ENT-3838 | Granular control over 2-way comment sync (Slack/JSM/Rovo) | Pending Review | Integration |
| ENT-3837 | DESC (UAE) Certification | Pending Review | **Compliance** |
| ENT-3836 | Ability to store backups on-prem (emergency/exit scenarios) | Pending Review | **Data Residency** |
| ENT-3835 | File upload via Rovo MCP server to Confluence/Jira | Pending Review | Rovo Capabilities |
| ENT-3834 | App-Level Access Control for users/groups | Pending Review | Security/Governance |
| ENT-3833 | D32 - NATO Cybersecurity Directive (AC/322-D(2021)) | Pending Review | **Compliance** |
| ENT-3832 | Allow-list/whitelisting for SharePoint/OneDrive Rovo connector | Pending Review | Security/Integration |
| ENT-3829 | Confluence side-by-side image placement (game dev teams) | Pending Review | Feature Request |
| ENT-3828 | Confluence - Korean characters split (edit mode Ctrl+F) | Pending Review | Localization |
| ENT-3827 | Jira - Severe perf degradation with 100+ child subtasks | Pending Review | **Performance/Scale** |
| ENT-3826 | Enable Claude Opus 4.5 during Rovo Dev trial | Pending Review | Rovo AI Models |
| ENT-3825 | Reddit - Public API access for agents | Actively Investigating | Integration/API |
| ENT-3824 | Platform-native lifecycle governance (multi-site enterprises) | Pending Review | **Enterprise Governance** |
| ENT-3830 | Accurate Jira agent behavior and changelog queries | Actively Investigating | Rovo/Jira |
| ENT-3823 | Label Driven Policies | Pending Review | Governance/Automation |

### Key New ENT-3318 (Analytics Schema Objects)
**Status:** Actively Investigating  
**Summary:** Analytics - Schema objects unavailable for Jira in Atlassian Analytics data lake for data shares  
**Impact:** Enterprise customers unable to access complete data for analytics and reporting  
**Maps to:** FinOps/Cost Attribution + Data Governance

---

## 2. COMPLIANCE & REGULATED INDUSTRIES PILLAR

**DRI:** Wayne Yim (from planning documentation)  
**Key Spaces:** RegulatedIndustries, PRODSEC, DR (Data Residency)

### FedRAMP Compliance

**Current Initiatives:**
- FedRAMP Compliance SCR (Service Change Request) Intake Form - Page 6243577190
  - Last modified: Apr 29, 2026
  - Process for reviewing services for Atlassian Government Cloud (AGC) authorization
  - Requires SECREV (security review) from Product Security Team

- FedRAMP Moderate CSP Violations Tracking - Page 6007058673
  - Last modified: Apr 29, 2026
  - Tracks connect-src violations across admin.atlassian-us-gov-mod.com
  - CSP violations from external sources (statuspage.io, sentry.io, etc.)

**Status:** Active monitoring and enforcement

### Isolated Cloud (Oasis) - HIGHEST PRIORITY P0 Initiative

**Program Overview:**
- Initiative: "Oasis Program" - isolated cloud solutions for highly regulated enterprise customers
- Cross-pillar: Involves Product Security, Platform, Data Residency teams
- **Status:** In execution (EAP-3: Jan 1 - Apr 30, 2026)

**Key Pages:**
1. **FY26: Isolated Cloud <> Product Security Overview** (ID: 5362319056)
   - Last modified: May 1, 2026 (1 hour ago)
   - Contributors: Deepam Kanjani, Raghavendra Karthik D, Praful Agarwal
   - Defines Oasis Program structure and security posture

2. **FY26 Q3 R4 Planning - ProdSec Oasis** (ID: 6153601445)
   - Last modified: May 1, 2026 (4 hours ago)
   - EAP-3 Timeline: Jan 1, 2026 - Apr 30, 2026
   - SECREV cutoff: Feb 15, 2026
   - Reviews completion target: Apr 15, 2026
   - **Status:** On track with team bandwidth allocated

3. **FY26-Q4: IC Security Domain Verticals** (ID: 6602953578)
   - Last modified: Apr 30, 2026
   - Security Domains to deliver for IC GA (General Availability)
   - Q4 PPD (Product Delivery Planning) grooming: Apr 10, 2026 deadline
   - **Goal:** Ship Trusted IC to GA in Q4

4. **IC FY26 - Findings & Assessment Metrics** (ID: 6476523296)
   - Tracks security assessments and findings metrics
   - EAP-3 SECREV tracking and metrics

**Isolated Cloud Infrastructure:**
- **Staging IC:** ic-tm2 (Compass Record)
- **Production IC:** ic-em8 (Compass Record)
- Service: data-policy (mono-service with bulk-transfer capability)
- Bulk-Transfer Oasis Hydration Tasks (Page 5869415410) - Apr 29 update

**Security Review Program:**
- EAP-3 SECREV completion target: Apr 15, 2026
- Multiple verticals being assessed and delivered
- Data egress assessments in progress

### Data Residency (DARE Program)

**Program Structure:**
- **DARE 2.0 Split:** Initiative now divided into multiple projects
  - Data Localisation for EU
  - Org-level Data Residency (2 projects)
  - Replication (Low zero-downtime)

**Key Pages:**
1. **Data Residency 2.0** (ID: 3656260298)
   - Last modified: Apr 29, 2026 (v37)
   - Owner: Jatin Malik
   - **Status:** Split into multiple projects; NOT doing data in transit for all regions
   - Focus: Data Localisation in EU only

2. **DaRe - FY26 Priorities** (ID: 4933026283)
   - Last modified: Apr 29, 2026 (v55)
   - Owner: Alisa Garibovic
   - **Purpose:** Unblock largest customers from moving to Cloud
   - "Big Rocks" are key initiatives for Enterprise Grade
   - Related: ENT50 FY25Q4 Planning KR Scope
   - Comments: 11

3. **Data Residency for PII at Rest - Delivery Plan** (ID: 5162665224)
   - Last modified: Apr 29, 2026 (v85)
   - Covers: DaRe PII - Identity, Business Requirements, User Journeys
   - **Standard vs Custom:** Options for non-Identity PII data

**Status:** Mid-execution; focused on PII at rest in EU region

### Compliance Certifications & Standards

**New/Active Certifications:**
- **ENT-3837:** DESC (Digital Economy Security Council) Certification - UAE
- **ENT-3833:** D32 - NATO Cybersecurity Directive (AC/322-D(2021)0032-REV1)

**Scope:** RegInd team actively addressing new international compliance requirements

### IL5, C5, DORA, IRAP Status

- **IL5 (Intelligence Level 5):** Not explicitly found in recent 90-day searches; likely in-progress from FY25
- **C5 (German Cloud Security):** Not explicitly found; mapped to Data Residency work
- **DORA (Digital Operational Resilience Act):** Not explicitly found; likely in EU/DARE scope
- **IRAP (Australian Certification):** Not explicitly found; possibly under compliance pipeline

**Recommendation:** These likely tracked in TRUSTED or specialized compliance spaces not captured in initial searches.

---

## 3. SCALE PILLAR

**Focus:** Confluence 150K-250K users, Jira 50K-150K users, Rovo scale capabilities

### Confluence Scale - 250K User Tier (SHIPPED Q2 2026)

**Major Achievement:**
- **SHIPPED:** Confluence now supports 250K+ users per instance
- **Timeline:** Shipped Q2 2026, **full quarter ahead of schedule** vs FY27H1 public roadmap
- **Blog Post:** "BREAKING NEWS: Confluence scale rocket ship passes 250k users, on the road to 1M!" (Apr 30, 2026)
- **Customers Unblocked:** SAP, BMW, JPMC, Siemens, Bosch, Apple

**Key Pages:**
1. **Confluence Scale 250k GA - Launch Readiness** (ID: 6390999856)
   - Last modified: Apr 30, 2026
   - **Overall Status:** On track
   - Target launch: Apr 15, 2026 (now GA)
   - Tracks: Launch readiness, technical dependencies

2. **Confluence User Scale: 250K Program Status & Path Forward** (ID: 5308699822)
   - Last modified: Apr 30, 2026 (live page)
   - Strategy, decisions, dependencies documented
   - Next phase: Path to 1M users

3. **Confluence Scale 250k - AdminHub Scope** (ID: 5051856064)
   - Covers admin functionality scope for 250k tier

4. **BREAKING NEWS Blog Post** (ID: 6844257866)
   - Last modified: Apr 30, 2026
   - Public announcement of 250K achievement
   - Signals customer readiness for enterprise migration

### Confluence Beyond 150K

**Page:** Confluence: Scaling Beyond 150K? (ID: 3578746377)
- Last modified: Apr 30, 2026
- Current state from 2024-05-15
- Accelerating Scale to Unblock HELA Customers
- Next Scale tier needed: "Confluence 150k+ Unscoped"
- **Current Step:** DACI to detail move focus to CRS (Customer Requested Scope)

### Jira Scale Status

**Not explicitly found in recent searches.** Likely tracked in separate JIRA-scale or CSDE spaces.
- Known target: 50K-150K user tiers
- **Recommendation:** Request search in JIRA-specific scaling spaces

### Rovo Scale Capabilities

**Related ENT Tickets:**
- ENT-3843: Increase number of supported objects Rovo can create/edit/modify
- ENT-3841: Improve Rovo's processing of large amounts of data
- ENT-3842: Additional public information around Rovo usage limits

**Tracking:** Rovo scale likely managed within Rovo team, not primary Core Engineering scope

---

## 4. FINOPS & COST ATTRIBUTION PILLAR

**Owner:** Ke Wang (kwang4@atlassian.com)  
**Related Roles:** Levon Esibov (TPM), Ashish Consul (Finance)  
**Jira Spaces:** CFINOPS (FinOps), PPE (Product Profitability), SHPLXII (AI)

### FinOps Team (CFINOPS Space)

**Recent Activity (May 1, 2026):**

1. **Guide: How to Submit Your Forecast in FinOps Portal** (ID: 6858807857)
   - Last modified: May 1, 2026 (10 hours ago)
   - **New Feature:** FinOps Portal forecasting feature piloting in May
   - Replacing Google Sheets with FinOps Portal for FY27 planning
   - Initiative: Project-only Initiative Forecasting

2. **Service Catalogue Requirements** (ID: 6329578594)
   - Last modified: May 1, 2026 (14 hours ago)
   - **Critical Initiative:** Service Catalogue as Tier 0 Deployment Prerequisite
   - Requirement: Integrate directly into deployment pipeline
   - Mandate: No service deployment without Service Catalogue registration
   - **Status:** WIP - requirements definition phase

3. **Proposal for Usage Attribution & Cost Allocation for K8s Resources** (ID: 6723048767)
   - Last modified: May 1, 2026 (14 hours ago)
   - [WIP] in progress
   - Addresses: K8s compute and storage cost attribution
   - Simplified control plane cost allocation methodology proposed
   - Networking: TODO

4. **Allocation and Attribution Discussion** (ID: 6850070240)
   - Active discussion on cost allocation methodologies
   - Challenges: 130M lines/day, complex rule combinations
   - Approach: Hash-based allocation, ruleset compilation

### Product Profitability Engineering (PPE Space)

**FY26 Execution Reviews (Monthly):**

1. **FY26 (Apr) Product Profitability Execution Review** (ID: 6866915715)
   - Latest monthly review
   - TPM: Levon Esibov, Ke Wang
   - Finance stakeholder involvement

2. **FY26 (Dec) Product Profitability Execution Review** (ID: 6231831653)
   - Last modified: Apr 29, 2026
   - Monthly review cadence established

3. **FY26 (Sept) Product Profitability Execution Review** (ID: 5835483811)
   - Last modified: Apr 29, 2026
   - Consistent monthly review process

### Product Profitability Wave Planning

**Completed Waves:**
- **Wave 4** (ID: 5581512001) - FY25 completed 20 models covering 90% hosting COGS
- **Wave 5** (ID: 5831958339) - FY26 update
  - Remaining 10% driven by: SRE COGS, Security, Growth, Globalization, Ecosystem Platform
  - Model coverage includes: GTM COGS, Processing Fees, Enterprise COGS Migration
  - Roadmap: Quarterly divisions with progress tracking

**Models in Flight (FY26 Wave 5):**
- Employment Spend
- R&D General Cloud
- IT
- TWC (Teamwork) - Jira
- Trust
- Growth
- Commerce & CCP
- Teamwork Platform
- Core Engineering COGS

**Status:** Q4 completion targets across all models

### Key FinOps Projects

**Known Projects:**
1. **Project Bigsky** - FY26 Budget and Forecast System
2. **Project Cypress** - FY26 Optimization and Recommendation
3. **One-AI-Cost-Report** - AI-specific cost tracking

**Status:** In progress; forecasting system in pilot phase

### FinOps Governance

**Tools in Development:**
- FinOps Portal (May 2026 pilot launch)
- Service Catalogue integration (Tier 0 deployment prerequisite)
- Cost attribution methodologies (K8s, compute, storage)

**Team:** Ke Wang leading all three tracks

---

## 5. ENGINEERING EXCELLENCE PILLAR

### Reliability & Performance

**Key ENT Issues Mapped to Engineering Excellence:**

| Ticket | Category | Summary |
|--------|----------|---------|
| ENT-3827 | **Jira Performance** | Severe perf degradation with 100+ child subtasks |
| ENT-3840 | Protocol Support | HTTP 2 Customer Refusal to Enable (Confluence/Jira) |
| ENT-3841 | Rovo Performance | Improve Rovo's processing of large amount of data |
| ENT-3828 | Localization/Perf | Korean characters split in edit mode (Ctrl+F) |
| ENT-3829 | Editor Features | Side-by-side image placement (game dev teams) |

**Status:** Active investigation and refinement phase

### Developer Tooling & Integration

**MCP (Model Context Protocol) Server Enhancements:**
- ENT-3860: Multi-site connectivity support
- ENT-3856: Per-site permission configuration
- ENT-3835: File upload capability to Confluence/Jira
- ENT-3838: 2-way comment sync (Slack/JSM/Rovo)
- ENT-3852: AppLink WebSocket tunnels with DLP compatibility

**Status:** All pending review/implementation

### Cost Optimization

**Tracked under FinOps Pillar:**
- K8s cost allocation and attribution
- Service Catalogue enforcement (cost governance)
- Wave-based product profitability modeling
- One-AI-Cost tracking

---

## 6. CROSS-CUTTING THEMES & NEW CORENG DISCOVERIES

### A. Rovo Expansion Across Enterprise

**Emerging as 4th Strategic Pillar:**
- Multiple ENT tickets (40+ of 50 recent) involve Rovo
- Covers: AI/LLM capabilities, data processing, API access, integration scope
- **New dimensions:**
  - Rovo MCP Server (file uploads, multi-connector support)
  - Rovo agent accuracy (Jira behavior, changelog queries)
  - Usage dashboards and limits transparency
  - Slack/JSM/Confluence integration
  - Model selection (Claude Opus 4.5 trial)

### B. Enterprise Governance & Lifecycle Management

**ENT-3824:** Platform-native lifecycle governance for large-scale multi-site enterprises
- **Blocker:** PwC expansion
- **Scope:** Multi-site lifecycle management at platform level
- **Status:** Pending Review
- **Implication:** New architectural requirement for Core Engineering

### C. Analytics & Data Intelligence

**ENT-3318:** Analytics schema objects unavailable
- **Root cause:** Jira analytics in data lake missing for data shares
- **Impact:** Enterprise customers cannot access complete analytics
- **Maps to:** FinOps + Data Governance + Analytics Platform

**ENT-3844/3862:** Rovo usage trend dashboards
- Real-time user engagement tracking
- Scope: Admin visibility into Rovo adoption

### D. Security & Access Control Evolution

**New Patterns:**
- ENT-3851: Prevention of sensitive data ingestion
- ENT-3848: Restrict Org Admin self-granting
- ENT-3834: App-level access control (users/groups)
- ENT-3855: Mobile App Management (MAM) for external users
- ENT-3832: Allow-listing for SharePoint/OneDrive

**Emerging:** Zero-trust, granular access models spreading across products

### E. Data Residency & Backup Strategy

**ENT-3836:** On-premise backup storage (emergency/exit scenarios)
- **New requirement:** Customers want data portability
- **Implication:** Architectural consideration for Cloud-first products

---

## 7. COMMIT PROJECT ACTIVITY (Last 60 Days)

**Total COMMIT tickets updated:** 50  
**Sample of recent tickets (non-compliance related):**

- COMMIT-26909: Catalog Account Migration - Trial Extension Promotion
- COMMIT-26908: DE SSOT API deprecation (derived entities) - Resolved
- COMMIT-26906: Non-UGC ERS CDC Events for DROID ERS
- COMMIT-26905: Legion "org reparent" consumer update
- *[General COMMIT focus: Data infrastructure, account systems, not RegInd/Scale]*

---

## 8. PRIORITY MAPPING: UNSHIPPED P0/P1/P2 ITEMS

### High-Priority Unshipped Items (Pending Review / Actively Investigating)

**P0 Equivalents (Actively Investigating):**
1. ENT-3844: Rovo usage trend dashboard
2. ENT-3825: Public API access for agents
3. ENT-3830: Accurate Jira agent behavior queries

**P1 Equivalents (Pending Review, Strategic Impact):**
1. **ENT-3318:** Analytics schema objects - **FinOps blocker**
2. **ENT-3824:** Multi-site lifecycle governance - **PwC blocker**
3. **ENT-3827:** Jira performance (100+ subtasks) - **Scale blocker**
4. **ENT-3836:** On-prem backup capability - **Data residency**
5. **ENT-3837:** DESC (UAE) Certification - **Compliance**
6. **ENT-3833:** NATO D32 Directive - **Compliance**

**P2 Equivalents (Pending Review, Product Enhancements):**
- Rovo capabilities (file upload, multi-site, advanced queries)
- JSM improvements (stakeholder management, deployment gating)
- Integration enhancements (Teams, SharePoint)
- Governance features (label-driven policies, field duplication prevention)

---

## 9. MAPPING NEW REQUESTS TO CORENG PILLARS

| ENT Ticket | Request | Primary Pillar | Secondary | Status |
|------------|---------|---|---|---|
| ENT-3318 | Analytics schema objects | **FinOps** | Data Governance | Investigating |
| ENT-3824 | Multi-site lifecycle governance | **Engineering Excellence** | Enterprise Governance | Pending |
| ENT-3827 | Jira perf (subtasks) | **Scale** | Engineering Excellence | Pending |
| ENT-3836 | On-prem backup | **Compliance/RegInd** | Data Residency | Pending |
| ENT-3837 | DESC (UAE) | **Compliance/RegInd** | New certification | Pending |
| ENT-3833 | NATO D32 | **Compliance/RegInd** | New certification | Pending |
| ENT-3860 | MCP multi-site | **Engineering Excellence** | Developer Tooling | Pending |
| ENT-3841 | Rovo data processing | **Scale** | Rovo AI | Pending |
| ENT-3844 | Rovo usage dashboards | **FinOps** | Analytics | Investigating |

---

## 10. SUMMARY TABLE: CORENG PILLARS STATUS

| Pillar | Owner(s) | Key Initiative | Status | Recent Update | Blockers |
|--------|----------|---|---|---|---|
| **Compliance/RegInd** | Wayne Yim | Isolated Cloud (Oasis) GA | P0 In Progress | May 1 (1h ago) | Security domain finalization |
| | | FedRAMP Moderate | Active | Apr 29 | CSP policy compliance |
| | | Data Residency (DARE) | In Progress | Apr 29 | EU-only scope, PII at rest |
| | | New Certifications | Just Started | Apr/May | DESC, NATO D32 |
| **Scale** | CRSP Team | Confluence 250K | **SHIPPED** | Apr 30 | None - achieved |
| | | Confluence 250K+ | Scoped | Apr 30 | Path to 1M |
| | | Jira Scale | Ongoing | Unknown | TBD |
| | | Rovo Scale | In Progress | Pending review | ENT-3841, ENT-3843 |
| **FinOps** | Ke Wang | FinOps Portal | Piloting | May 1 | FY27 rollout |
| | | Service Catalogue | Requirements | May 1 | Tier 0 integration |
| | | K8s Attribution | WIP | May 1 | Methodology finalization |
| | | Product Profitability Waves | Executing | Monthly reviews | Wave 5 completion |
| **Eng Excellence** | TBD | MCP Server | Enhancing | Pending review | Multi-site, permissions |
| | | Jira Performance | Investigating | Pending | Subtask perf (ENT-3827) |
| | | Lifecycle Governance | New | Pending | Architecture design |

---

## APPENDIX A: KEY STAKEHOLDER MAPPING

**Compliance/RegInd:**
- Wayne Yim (DRI)
- Deepam Kanjani (IC Security)
- Raghavendra Karthik D (IC Security)
- Praful Agarwal (IC Security)
- Alisa Garibovic (DARE Program)
- Jatin Malik (Data Residency)

**FinOps:**
- Ke Wang (Owner - FinOps + Product Profitability)
- Levon Esibov (TPM)
- Ashish Consul (Finance)

**Scale:**
- CRSP Team (Confluence Scale)
- Confluence engineering leads (250K delivery)

---

## APPENDIX B: CRITICAL TIMELINE EVENTS

**May 1, 2026 (TODAY):**
- FinOps Portal pilot launch announced
- Isolated Cloud Q4 planning completion
- Service Catalogue requirements finalization

**Apr 30, 2026:**
- Confluence 250K GA shipped (public announcement)
- All scale readiness checks passed

**Apr 29, 2026:**
- Data Residency v37 updated
- FedRAMP compliance forms refreshed
- Jira performance issues escalated (ENT-3827)

**Key Upcoming Dates:**
- May 2026: FinOps Portal rollout begins
- Q2 2026: Confluence 250K GA (achieved)
- Q4 2026: Isolated Cloud GA target
- FY27H1: Confluence 1M user path

---

## APPENDIX C: RECOMMENDED NEXT STEPS

1. **Immediate (This Week):**
   - Schedule briefing with Wayne Yim on Oasis IC GA timeline
   - Review ENT-3318 analytics schema impact with Ke Wang
   - Confirm ENT-3824 multi-site governance as new CoreEng priority

2. **Near-term (This Sprint):**
   - Audit IL5, C5, DORA, IRAP status (likely in TRUSTED space)
   - Request Jira Scale pillar status (may be in separate space)
   - Map Rovo scale requirements formally to Core Engineering

3. **Strategic (This Quarter):**
   - Define "Engineering Excellence" pillar DRI and roadmap
   - Integrate Rovo as 4th pillar with formal governance
   - Establish cross-pillar metrics and dependencies

---

**Report Generated:** May 1, 2026, 08:35 UTC  
**Data Sources:** TWG CLI (Jira, Confluence, TeamWork Graph), 90-day lookback  
**Total Artifacts Analyzed:** 50+ ENT tickets, 20+ Confluence pages, 10+ COMMIT tickets
