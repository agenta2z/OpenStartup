# Enterprise Request Map → CoreEng Org & Projects
**Generated:** May 1, 2026 | **Method:** Live data from Atlassian TWG, Jira, Confluence
**Purpose:** Map every known enterprise request to the CoreEng team/pillar responsible

---

## How to Read This Document

Each enterprise capability row shows:
- **ENT Ticket(s):** The official Enterprise Jira ticket(s)
- **Priority:** P0 (Must Win) / P1 (High) / P2 (Medium) / P3 (Low)
- **Status:** Current delivery status
- **CoreEng Pillar:** Which CoreEng team owns the work
- **CoreEng DRI:** Known owner within CoreEng
- **Existing Project:** Atlas/Jira project this maps to (if exists)
- **New Project Needed:** Whether a new project should be created

---

## SECTION A: EXISTING ENTERPRISE REQUESTS (34 Known Tickets)

### 🔐 Security & Encryption

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-1958 | AWS-XKS Customer-Managed Keys (CMK) | P0 | 📋 Public Roadmap | Encryption Platform (Cryptor/Coral) | Greg Zaney | CMK FY26 (ENCRYPT space) | No |
| ENT-2085 | Apply CMK retroactively to existing sites | P1 | 📋 Public Roadmap | Encryption Platform (Cryptor/Coral) | Greg Zaney | CMK FY26 (ENCRYPT space) | No |
| ENT-398 | Customer-managed keys with AWS Cloud HSM | P3 | ⬛ Not Prioritized | Encryption Platform (Cryptor/Coral) | Greg Zaney | — | No (defer) |

### 📋 Audit Logs (ALP)

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-166 | Audit log access for site admins | P1 | ✅ Shipped | ALP (Audit Logging Platform) | Akshay Nambiar | ALP Platform (ALP space) | No |
| ENT-2883 | Embeddable audit logs for Jira/JSM | P1 | 🔒 Internal Roadmap | ALP + Identity (container perms) | Akshay Nambiar | ALP Platform (ALP space) | No |
| ENT-1057 | Audit Log Retention 12 months for AGP | P1 | 📋 Public Roadmap | ALP (Audit Logging Platform) | Akshay Nambiar | ALP Platform (ALP space) | No |

### 🔑 Identity & Access Management

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-555 | Single Logout — Atlassian-initiated (SLO) | P1 | ✅ Shipped | Identity (Rocket/Fortress) | Prashant Ghosal | Identity Platform (I space) | No |
| ENT-2303 | Single Logout — IdP-initiated SLO | P1 | 🔍 Pending Review | Identity (Rocket/Fortress) | Prashant Ghosal | Identity Platform (I space) | No |
| ENT-652 | App migration content access — restricted pages | P1 | 🔒 Internal Roadmap | Identity | Prashant Ghosal | Identity Platform (I space) | No |

### 🛡️ Threat Detection / Atlassian Guard

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| AG-42 | API Tokens & API Keys (Guard Stage 3) | P1 | 🟡 In Progress | Identity (API Token mgmt) | Prashant Ghosal | Guard / Identity (I space) | No |
| AG-43 | Service principal-based token access | P1 | 🟡 In Progress | Identity (API Token mgmt) | Prashant Ghosal | Guard / Identity (I space) | No |

### 📊 Data Governance

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-1155 | Immature Data Governance erodes customer trust | P1 | ✅ Shipped | Multiple (Identity, TDP, Micros) | Ke Wang (coord.) | Data Governance FY26 | No |
| ENT-2864 | Customer can retain data up to N years | P1 | 🔒 Internal Roadmap | TDP + ALP | TBD | — | ⚠️ May need new project |

### 💾 Resilience / BRIE (Backup & Restore)

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-1929 | Full backups >3TB with attachments | P0 | ✅ Shipped | BRIE + TDP (media) | Lakshmi Behl | BRIE Project (BRIE space) | No |
| ENT-311 | Apps backup/restore 30-day retention | P1 | 🔒 Internal Roadmap | BRIE | Lakshmi Behl | BRIE Project (BRIE space) | No |
| ENT-151 | Export all cloud data long-term storage | P1 | 🔒 Internal Roadmap | BRIE | Lakshmi Behl | BRIE Project (BRIE space) | No |
| ENT-1104 | Automatic/Scheduled backups | P1 | ✅ Shipped | BRIE | Lakshmi Behl | BRIE Project (BRIE space) | No |
| ENT-1909 | Backup direct to AWS S3 (BYOS) | P1 | ✅ Shipped | BRIE | Lakshmi Behl | BRIE Project (BRIE space) | No |
| ENT-1983 | Increase backup import size limit <3TB | P1 | ✅ Shipped | BRIE | Lakshmi Behl | BRIE Project (BRIE space) | No |
| ENT-2331 | Daily backups of Cloud products | P1 | ✅ Shipped | BRIE | Lakshmi Behl | BRIE Project (BRIE space) | No |

### 🏗️ Sandbox / Flip2Prod

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-50 | Push/promote data from sandbox to production | P1 | 📋 Public Roadmap | TSP (Flip2Prod) | Sirisha Pendem | TSP/Flip2Prod (TSP space) | No |
| ENT-2124 | Large attachment size in Confluence Sandbox | P1 | 🔍 Investigating | TSP + TDP (media-copy) | Harpreet Singh Juneja | TSP/Sandbox (TSP space) | No |

### 🌍 Compliance (FedRAMP / IL5 / Isolated Cloud / C5 / DaRe)

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-2289 | FedRAMP High | P0 | 📋 Public Roadmap | Compliance/RegInd (cross-pillar) | Wayne Yim | RegInd FY26 | No |
| ENT-2745 | Virtual Private / Isolated Cloud (Oasis) | P0 | 📋 Public Roadmap | Compliance + Identity + Infra | Wayne Yim + cross-pillar | Oasis IC Program | No |
| ENT-59 | PII stored in nominated region (DaRe) | P0 | ⚪ Paused | Identity (DaRe) | Peter Wang / Amaranath Dabbara | DaRe Program | No |
| ENT-1957 | BYOK-related compliance | P1 | 📋 Public Roadmap | Encryption Platform | Greg Zaney | CMK FY26 | No |

### 🏢 Org Data Isolation / Admin Hub

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-1690 | Configure org-level data per enterprise site | P2 | 📋 Public Roadmap | Identity (Collab Context) | Prashant Ghosal | Org Isolation / Collab Context | No |
| ENT-764 | Purchase Apps for subset of users | P2 | 🔒 Internal Roadmap | Identity (License Decoupling) | Prashant Ghosal | License Decoupling (I space) | No |
| ENT-351 | Modify app approvals in enterprise | P2 | 🔒 Internal Roadmap | Identity | Prashant Ghosal | Identity Platform (I space) | No |
| ENT-1703 | Site count above 150, up to 2,000 | P1 | 🔒 Internal Roadmap | Identity (Admin Hub Scale) | Prashant Ghosal | Admin Hub Scale (I space) | No |
| ENT-2643 | 800K users + ≤100 sites provisioning | P1 | ✅ Shipped | Identity (SCIM/UUL) | Prashant Ghosal | UUL / SCIM Scale (I space) | No |

### 📈 Scale (Confluence / Jira / Platform)

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-1520 | Confluence 150K–250K scale | P0 | 📋 Public Roadmap | Scale/CRSP (Compute/Networking) | CRSP Team | Confluence Scale FY26 | No |
| ENT-2199 | Jira vertical scale 50K–150K | P0 | ✅ Shipped | Scale/CRSP (Compute/Networking) | CRSP Team | Jira Scale FY26 | No |

### 🔧 Admin APIs / Change Management

| ENT Ticket | Summary | Priority | Status | CoreEng Pillar | CoreEng DRI | Existing Project | New Project? |
|---|---|---|---|---|---|---|---|
| ENT-2089 | Data Management Admin role | P2 | 🔒 Internal Roadmap | Identity / Admin APIs | Prashant Ghosal | Identity Admin APIs | No |
| ENT-2122 | REST API for Atlassian Analytics | P2 | ✅ Shipped | FinOps / Analytics | Ke Wang | CFINOPS / Analytics | No |
| ENT-35 | Change freeze period for production site | P3 | ✅ Shipped | Eng Excellence | TBD | — | No |

---

## SECTION B: NEW ENTERPRISE REQUESTS (Last 90 Days — Requires Triage)

*50 new tickets created. Below are the 15 most CoreEng-relevant for mapping.*

| ENT Ticket | Summary | Priority | Status | Recommended CoreEng Pillar | Action Required |
|---|---|---|---|---|---|
| **ENT-3863** | JSM skill "Raise a Request" linked fields support | TBD | Pending Review | N/A (Product/JSM) | Route to JSM team |
| **ENT-3860** | Atlassian MCP server — multi-site support simultaneously | TBD | Pending Review | Eng Excellence / Developer Platform | ⚠️ NEW PROJECT: MCP Platform |
| **ENT-3856** | MCP server permissions per site (extends ENT-3684) | TBD | Pending Review | Identity (Permission Model) | Route to Identity |
| **ENT-3855** | MAM policy targeting for external users | TBD | Pending Review | Identity (Guard/External Users) | Route to Identity/Guard |
| **ENT-3852** | AppLink WebSocket tunnels — DLP-compatible | TBD | Pending Review | Identity + Networking | ⚠️ Cross-pillar coordination needed |
| **ENT-3851** | Prevent ingestion of new sensitive data in Jira/Confluence | TBD | Pending Review | Compliance + Identity | Route to RegInd/Identity |
| **ENT-3848** | Restrict Org Admin from self-granting product access | TBD | Pending Review | Identity (Admin Hub) | Route to Identity |
| **ENT-3837** | DESC (UAE) Certification | TBD | Pending Review | Compliance/RegInd | Route to Wayne Yim |
| **ENT-3836** | Store backups on-prem (emergency/exit scenarios) | TBD | Pending Review | BRIE | ⚠️ NEW SCOPE for BRIE |
| **ENT-3834** | App-Level Access Control for users/groups | TBD | Pending Review | Identity (License/Auth) | Route to Identity |
| **ENT-3833** | NATO D32 Cybersecurity Directive | TBD | Pending Review | Compliance/RegInd | Route to Wayne Yim |
| **ENT-3827** | Jira perf degradation with 100+ child subtasks | TBD | Pending Review | Scale/CRSP | Route to CRSP |
| **ENT-3824** | Platform-native lifecycle governance multi-site | TBD | Pending Review | Identity (Collab Context / Org Units) | Extend ENT-1690 scope |
| **ENT-3823** | Label Driven Policies | TBD | Pending Review | Identity (Policy Engine) | ⚠️ May need new project |
| **ENT-3318** | Analytics schema objects unavailable (Jira data lake) | Actively Investigating | High | FinOps / TDP / Analytics | Route to Ke Wang / TDP |

---

## SECTION C: CORENG PILLAR CAPABILITY MAP

*What each CoreEng pillar can absorb vs. needs new projects for.*

### Identity & IAM (Prashant Ghosal's org)
**Can absorb:** ENT-3856, ENT-3855, ENT-3848, ENT-3834, ENT-3824, ENT-3823, ENT-3852 (partial)
**New project consideration:** Policy Engine (ENT-3823 + ENT-3851 + label-driven governance cluster)
**Capacity concern:** 🔴 OVERLOADED — 9 existing P0/P1 items + 7 new requests

### BRIE (Lakshmi Behl)
**Can absorb:** ENT-3836 (on-prem backup) into BRIE Phase 2 scope
**New project consideration:** ⚠️ On-prem/exit scenarios may need separate project if large scope

### ALP / Audit Logs (Akshay Nambiar)
**Can absorb:** No new requests this cycle
**Status:** Q4 FY26 execution critical path (Dynamic Materialization by May 1)

### Encryption Platform / BYOK (Greg Zaney — Coral)
**Can absorb:** No new requests this cycle
**Status:** Focused execution: IC golden path first, then Commercial/FedRAMP

### TSP / Sandbox (Harpreet Singh Juneja)
**Can absorb:** No new requests this cycle
**Status:** H2FY26 roadmap in-flight

### Compliance / RegInd (Wayne Yim)
**Can absorb:** ENT-3837 (UAE DESC cert), ENT-3833 (NATO D32), ENT-3851 (sensitive data prevention)
**New project consideration:** ⚠️ DESC + NATO D32 likely warrant new compliance project

### Scale / CRSP
**Can absorb:** ENT-3827 (Jira perf/scale)
**Status:** Confluence 250K shipped ✅; focus shifts to Jira 150K+

### FinOps / Cost Attribution (Ke Wang)
**Can absorb:** ENT-3318 (analytics schema), coordinate with TDP
**Status:** Project Bigsky + Project Cypress active; FinOps portal launching

### Eng Excellence / Developer Platform
**Can absorb:** ENT-3860 (MCP multi-site)
**New project consideration:** ⚠️ MCP server platform capability likely needs new formal project

---

## SECTION D: RECOMMENDED NEW ATLAS PROJECTS

Based on the new ENT requests and gaps, these new Atlas projects should be considered:

| # | Proposed Project | Trigger Tickets | Suggested Owner | Priority | Rationale |
|---|---|---|---|---|---|
| 1 | **MCP Server Platform** | ENT-3860, ENT-3856 | Eng Excellence / Developer Platform | P1 | Growing class of MCP-related enterprise requests; needs formal CoreEng ownership |
| 2 | **Policy Engine** | ENT-3823, ENT-3851, ENT-3834 | Identity | P1 | Label-driven policies + data ingestion controls + app-level access = common policy infrastructure |
| 3 | **New Compliance Certifications FY26** | ENT-3837 (DESC/UAE), ENT-3833 (NATO D32) | Compliance/RegInd (Wayne Yim) | P2 | New geo/regulatory certifications beyond existing FedRAMP/C5/IRAP track |
| 4 | **BRIE Phase 2: Exit & Sovereignty** | ENT-3836 (on-prem backup) | BRIE (Lakshmi Behl) | P2 | On-prem/exit scenario represents new BRIE capability class |
| 5 | **Rovo Enterprise Governance** | ENT-3849, ENT-3843, ENT-3841, ENT-3830 | Rovo + Identity | P1 | Cluster of Rovo enterprise requests needing CoreEng governance hooks |

---

## SECTION E: DEPENDENCY HEAT MAP

*Which CoreEng pillars are dependencies for the most enterprise capabilities*

```
Identity      ████████████████████████████  28 capabilities (CRITICAL BOTTLENECK)
Compliance    ████████████████              16 capabilities
BRIE          █████████████                13 capabilities  
Scale/CRSP    ██████████                   10 capabilities
Encryption    ████████                      8 capabilities
ALP           ███████                       7 capabilities
TSP/Sandbox   ██████                        6 capabilities
TDP           █████                         5 capabilities
FinOps        ████                          4 capabilities
Eng Excellence███                           3 capabilities
```

**Critical Insight:** Identity is a dependency for **83% of P0 enterprise requests**. Any capacity shortfall in Identity directly blocks enterprise program delivery.

---

## SECTION F: STATUS SUMMARY

### By Status (All 34 Known ENT Tickets)
| Status | Count | % |
|---|---|---|
| ✅ Shipped / Done | 13 | 38% |
| 📋 Public Roadmap | 9 | 26% |
| 🔒 Internal Roadmap | 9 | 26% |
| 🔍 Investigating | 2 | 6% |
| ⚪ Paused | 1 | 3% |
| ⬛ Not Prioritized | 1 | 3% |

### By Priority (Active items only)
| Priority | Shipped | Active | Paused/NP | Total |
|---|---|---|---|---|
| P0 | 3 | 5 | 2 | 10 |
| P1 | 9 | 12 | 0 | 21 |
| P2 | 1 | 3 | 0 | 4 |
| P3 | 0 | 1 | 0 | 1 |

### New Requests Triage Needed (50 tickets, last 90d)
| Category | Count | CoreEng Relevant |
|---|---|---|
| Rovo/AI capabilities | 18 | 3 |
| Security/Governance | 12 | 9 |
| Compliance | 4 | 4 |
| Scale/Performance | 3 | 2 |
| Integration/API | 7 | 2 |
| Feature Requests | 6 | 0 |

---

*Last updated: May 1, 2026 | Data sources: Atlassian TWG CLI, Jira ENT project, Confluence CoreEngineering space*
