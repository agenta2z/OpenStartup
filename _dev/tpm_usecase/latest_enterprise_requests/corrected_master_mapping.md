# Corrected Master Mapping: Enterprise Requests → CoreEng Pillars
**Generated:** May 01, 2026 09:49 UTC  
**Method:** Live Jira data (TWG CLI) + CoreEng understanding docs (5 files)  
**Total Unique ENT Tickets:** 129  
**Data Confidence:** HIGH — all tickets cross-referenced with CoreEng pillar ownership rules  

## 📊 Coverage Summary

| Metric | Count | % |
|---|---|---|
| Total tickets analyzed | 129 | 100% |
| Map to **existing** CoreEng project | 77 | 59% |
| Need **new** CoreEng project | 27 | 20% |
| NOT CoreEng (route to product teams) | 24 | 18% |
| TRIAGE NEEDED (ambiguous) | 1 | 0% |

| Status | Count | % |
|---|---|---|
| ⏳ Pending Review | 56 | 43% |
| 🔍 Actively Investigating | 33 | 25% |
| 🔒 Roadmap (Internal Only) | 16 | 12% |
| ✅ Shipped | 10 | 7% |
| 📋 Public Roadmap | 8 | 6% |
| ⬛ Not Currently Prioritized | 3 | 2% |
| ❓ Closed | 2 | 1% |
| 🔑 Pending Exec Decision | 1 | 0% |

---

## 🗺️ Section 1: Master Mapping Table

*Sorted by priority (P0 first), then ENT key number.*

| ENT Key | Summary | Status | Priority | CoreEng Pillar | Existing Project | New Project? |
|---|---|---|---|---|---|---|
| [ENT-293](https://hello.jira.atlassian.cloud/browse/ENT-293) | US Classified/Top Secret/Secret Cloud deployment + IL6/ Disc… | 🔍 Actively Investigating | 🔴 P0 | Compliance / RegInd | RegInd FY26 | No |
| [ENT-2289](https://hello.jira.atlassian.cloud/browse/ENT-2289) | FedRAMP High | 📋 Public Roadmap | 🔴 P0 | Compliance / RegInd | RegInd FY26 | No |
| [ENT-2745](https://hello.jira.atlassian.cloud/browse/ENT-2745) | Virtual Private / Isolated cloud | 📋 Public Roadmap | 🔴 P0 | Compliance / RegInd | Oasis IC Program | No |
| ENT-3702 | FedRamp | Docusign Feature | ⏳ Pending Review | 🔴 P0 | Compliance / RegInd | RegInd / FedRAMP | No |
| [ENT-3824](https://hello.jira.atlassian.cloud/browse/ENT-3824) | Platform-native lifecycle governance for large-scale multi-s… | ⏳ Pending Review | 🔴 P0 | Identity & IAM | Platform-Native Lifecycle Governance | ⚠️ YES |
| [ENT-50](https://hello.jira.atlassian.cloud/browse/ENT-50) | EAP for the Ability to push (promote) Jira and JSM config da… | 📋 Public Roadmap | 🟠 P1 | TSP / Sandbox | TSP/Flip2Prod | No |
| [ENT-59](https://hello.jira.atlassian.cloud/browse/ENT-59) | Guarantee that my organisation's user account account inform… | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | DaRe Program | No |
| [ENT-151](https://hello.jira.atlassian.cloud/browse/ENT-151) | Export all of my cloud data for long term storage in a "read… | 🔒 Roadmap (Internal Only) | 🟠 P1 | BRIE | BRIE Project | No |
| [ENT-311](https://hello.jira.atlassian.cloud/browse/ENT-311) | Apps backup and restore with 30 days retention | 🔒 Roadmap (Internal Only) | 🟠 P1 | BRIE | BRIE Project | No |
| [ENT-351](https://hello.jira.atlassian.cloud/browse/ENT-351) | Modify how app approvals work in enterprise environments | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | Identity Platform | No |
| [ENT-652](https://hello.jira.atlassian.cloud/browse/ENT-652) | App migration content access problems - Restricted pages | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | Identity Platform | No |
| [ENT-764](https://hello.jira.atlassian.cloud/browse/ENT-764) | Purchase Apps for a subset of users on an instance | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | License Decoupling | No |
| [ENT-1057](https://hello.jira.atlassian.cloud/browse/ENT-1057) | Audit Log Retention for 12 months for AGP customers | 📋 Public Roadmap | 🟠 P1 | ALP | ALP Platform | No |
| [ENT-1520](https://hello.jira.atlassian.cloud/browse/ENT-1520) | Expand Confluence Capabilities to Support Customer Size 150K… | 📋 Public Roadmap | 🟠 P1 | Scale / CRSP | Confluence Scale FY26 | No |
| [ENT-1690](https://hello.jira.atlassian.cloud/browse/ENT-1690) | Ability to configure what enterprise org level data is avail… | 📋 Public Roadmap | 🟠 P1 | Identity & IAM | Org Isolation / Collab Context | No |
| [ENT-1703](https://hello.jira.atlassian.cloud/browse/ENT-1703) | Enterprise support (by exception) for site count above 150, … | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | Admin Hub Scale | No |
| [ENT-1958](https://hello.jira.atlassian.cloud/browse/ENT-1958) | Support AWS-XKS with Customer-managed keys (CMK) | 📋 Public Roadmap | 🟠 P1 | Encryption / BYOK | CMK FY26 | No |
| [ENT-2085](https://hello.jira.atlassian.cloud/browse/ENT-2085) | CMK (BYOK) - Apply Customer-managed keys retroactively on ex… | 📋 Public Roadmap | 🟠 P1 | Encryption / BYOK | CMK FY26 | No |
| [ENT-2089](https://hello.jira.atlassian.cloud/browse/ENT-2089) | Create a Migration / Data Management Admin role | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | Identity Admin APIs | No |
| [ENT-2864](https://hello.jira.atlassian.cloud/browse/ENT-2864) | Customer can retain data up to n years to meet compliance ne… | 🔒 Roadmap (Internal Only) | 🟠 P1 | Compliance / RegInd | Data Governance / Compliance | No |
| [ENT-2883](https://hello.jira.atlassian.cloud/browse/ENT-2883) | Embeddable audit logs for Jira/JSM | 🔒 Roadmap (Internal Only) | 🟠 P1 | ALP | ALP Platform | No |
| ENT-3668 | Data Residency for Backup and Restore | 🔒 Roadmap (Internal Only) | 🟠 P1 | BRIE + Compliance | BRIE Phase 2 | ⚠️ YES |
| ENT-3696 |  Ability to Identify Content/Work Authored or Edited by Rovo… | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | Identity Platform / Guard | No |
| ENT-3707 | Ability to copy Rovo agents between sandbox and production | 🔒 Roadmap (Internal Only) | 🟠 P1 | TSP / Sandbox | TSP/Sandbox | No |
| [ENT-3783](https://hello.jira.atlassian.cloud/browse/ENT-3783) | Provide an Assets Data Manager Adapter for AWS Cloud  | 🔒 Roadmap (Internal Only) | 🟠 P1 | NOT CoreEng | JSM / Product Team | No |
| [ENT-3805](https://hello.jira.atlassian.cloud/browse/ENT-3805) | ROVO: Agent activity must be logged, capturing sufficient te… | 🔒 Roadmap (Internal Only) | 🟠 P1 | NOT CoreEng | Rovo / Product Team | No |
| [ENT-3809](https://hello.jira.atlassian.cloud/browse/ENT-3809) | Rovo | Policy to block MCP access for external users | 🔒 Roadmap (Internal Only) | 🟠 P1 | Identity & IAM | Service Account Management | ⚠️ YES |
| [ENT-1158](https://hello.jira.atlassian.cloud/browse/ENT-1158) | Audit Logs for Admin pages | 🔍 Actively Investigating | 🟡 P2 | ALP | ALP Platform | No |
| [ENT-1555](https://hello.jira.atlassian.cloud/browse/ENT-1555) | Google CloudSQL and Cloud storage support for Atlassian prod… | 🔍 Actively Investigating | 🟡 P2 | Scale / CRSP | CloudSQL / GCP Support | ⚠️ YES |
| [ENT-1638](https://hello.jira.atlassian.cloud/browse/ENT-1638) | Jira Data Center WCAG 2.1 AA Conformance Required | 🔍 Actively Investigating | 🟡 P2 | Compliance / RegInd | Accessibility / WCAG | No |
| [ENT-1697](https://hello.jira.atlassian.cloud/browse/ENT-1697) | Gliffy app for Confluence cloud - performance issues | 🔍 Actively Investigating | 🟡 P2 | Scale / CRSP | Jira Scale / Performance | No |
| [ENT-1786](https://hello.jira.atlassian.cloud/browse/ENT-1786) | [Cloud] Allow admins to remove the "Discover" and other prod… | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Identity Platform / Admin Hub | No |
| [ENT-1804](https://hello.jira.atlassian.cloud/browse/ENT-1804) | Ability to mask sensitive content | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Policy Engine | ⚠️ YES |
| [ENT-2124](https://hello.jira.atlassian.cloud/browse/ENT-2124) | Support large total attachment size in Confluence Sandbox cr… | 🔍 Actively Investigating | 🟡 P2 | TSP / Sandbox | TSP/Sandbox | No |
| [ENT-2225](https://hello.jira.atlassian.cloud/browse/ENT-2225) | App usage for Confluence | 🔍 Actively Investigating | 🟡 P2 | FinOps | App Analytics | No |
| [ENT-2303](https://hello.jira.atlassian.cloud/browse/ENT-2303) | Single Logout - Atlassian Account should support IdP-initiat… | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Identity Platform | No |
| [ENT-2347](https://hello.jira.atlassian.cloud/browse/ENT-2347) | Object level controls or permissions for Goals | 🔍 Actively Investigating | 🟡 P2 | NOT CoreEng | Goals Product Team | No |
| [ENT-2409](https://hello.jira.atlassian.cloud/browse/ENT-2409) | Ability to retrieve detailed billing information via REST AP… | 🔍 Actively Investigating | 🟡 P2 | FinOps | CFINOPS Analytics | No |
| [ENT-2460](https://hello.jira.atlassian.cloud/browse/ENT-2460) | AI Processing in Europe | 🔍 Actively Investigating | 🟡 P2 | Compliance / RegInd | AI Data Sovereignty | ⚠️ YES |
| [ENT-2590](https://hello.jira.atlassian.cloud/browse/ENT-2590) | REST API usage insights | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence | Developer APIs | No |
| [ENT-2625](https://hello.jira.atlassian.cloud/browse/ENT-2625) | Ability to deactivate users who haven't logged in for a peri… | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Identity Platform / Admin Hub | No |
| [ENT-2667](https://hello.jira.atlassian.cloud/browse/ENT-2667) | Automation Rules Should be Included in Jira Backups (Back up… | 🔍 Actively Investigating | 🟡 P2 | BRIE + Eng Excellence | BRIE Project | No |
| [ENT-2787](https://hello.jira.atlassian.cloud/browse/ENT-2787) | Improve public customer facing documentation around how app … | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence | Documentation / Developer Experience | No |
| [ENT-2788](https://hello.jira.atlassian.cloud/browse/ENT-2788) | Improve cloud app version visibility and information on the … | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence | App Marketplace Visibility | No |
| [ENT-2840](https://hello.jira.atlassian.cloud/browse/ENT-2840) | JSM (Assets, Forms, Data Manager) [Rovo Connector Enhancemen… | 🔍 Actively Investigating | 🟡 P2 | NOT CoreEng | JSM / Rovo Product Team | No |
| [ENT-2858](https://hello.jira.atlassian.cloud/browse/ENT-2858) | Improve Visibility of Upcoming Features in Release Tracks an… | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence | Release Track Visibility | No |
| [ENT-2880](https://hello.jira.atlassian.cloud/browse/ENT-2880) | Support "Scalable Silos" complex company archetype.  | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Org Isolation / Scalable Silos | ⚠️ YES |
| ENT-3291 | Classification Based Access Control | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Policy Engine | ⚠️ YES |
| ENT-3318 | Analytics - Schema objects unavailable for Jira in the Atlas… | 🔍 Actively Investigating | 🟡 P2 | FinOps | CFINOPS Analytics | No |
| ENT-3354 | Allow Rovo Agents to search multiple sites | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence + Identity | Rovo Enterprise / MCP Platform | ⚠️ YES |
| ENT-3436 | Private network connectivity to Atlassian Cloud (Eg: Private… | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence | Private Network Connectivity | ⚠️ YES |
| ENT-3595 | Rovo skill to be able to read Jira Dashboards (and its widge… | 🔍 Actively Investigating | 🟡 P2 | NOT CoreEng | Rovo Product Team | No |
| ENT-3631 | Service Accounts in AGC | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Service Account Management | ⚠️ YES |
| ENT-3664 | Service account to owner association covering secure account… | 🔍 Actively Investigating | 🟡 P2 | Identity & IAM | Service Account Management | ⚠️ YES |
| ENT-3665 | IP range restrictions for Service Account network controls | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Service Account Management | ⚠️ YES |
| ENT-3669 | Statuspage for AGC | 🔍 Actively Investigating | 🟡 P2 | Eng Excellence | Reliability / Statuspage | No |
| ENT-3675 | Enhance Rovo audit logging and observability for AI-assisted… | ⏳ Pending Review | 🟡 P2 | ALP | ALP Platform | No |
| ENT-3676 | Enable automated export or external sharing of Rovo usage an… | 🔍 Actively Investigating | 🟡 P2 | FinOps | CFINOPS Analytics | No |
| ENT-3679 | Backup Automation Rules associated with Confluence product (… | ⏳ Pending Review | 🟡 P2 | BRIE + ALP + Eng Excellence | BRIE / Config Backup | No |
| ENT-3685 | Guard Detect alert export with custom date range selection | ⏳ Pending Review | 🟡 P2 | ALP | ALP Platform | No |
| ENT-3686 | Next steps with the Legacy Backup Manager UI availability fo… | 🔍 Actively Investigating | 🟡 P2 | BRIE | BRIE Project | No |
| ENT-3692 | Ability to select Atlassian Teams scope (site vs org) | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / Product Team | No |
| ENT-3711 | Increase projects and team limits of Plans (Advanced Roadmap… | 🔍 Actively Investigating | 🟡 P2 | Compliance / RegInd | Data Residency | No |
| ENT-3724 | Make backup and restore available to standard license custom… | ⏳ Pending Review | 🟡 P2 | BRIE | BRIE Phase 2 | No |
| ENT-3726 | Backup retention > 30 days | ⏳ Pending Review | 🟡 P2 | BRIE | BRIE Phase 2 | No |
| ENT-3728 | Mobile App admin settings at the site level: Ability to bloc… | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Guard / MAM / MDM | No |
| ENT-3730 | Ability to create Cloud Sites from set Enterprise Templates | ⏳ Pending Review | 🟡 P2 | Eng Excellence | Platform-Native Lifecycle Governance | ⚠️ YES |
| ENT-3732 | Ability to have an efficient group membership retrieval in D… | ⏳ Pending Review | 🟡 P2 | Eng Excellence | Developer APIs | No |
| ENT-3736 | Regulated customers need public APIs to capture all Confluen… | ⏳ Pending Review | 🟡 P2 | ALP | ALP Platform | No |
| [ENT-3738](https://hello.jira.atlassian.cloud/browse/ENT-3738) | Regulated customers need public APIs to capture all Confluen… | ⏳ Pending Review | 🟡 P2 | ALP + Compliance | ALP Platform / Compliance | No |
| [ENT-3739](https://hello.jira.atlassian.cloud/browse/ENT-3739) | Atlassian‑hosted LLMs with EU Data Residency | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | AI Data Sovereignty | ⚠️ YES |
| [ENT-3745](https://hello.jira.atlassian.cloud/browse/ENT-3745) | Allow REST API calls via Atlassian custom domains | ⏳ Pending Review | 🟡 P2 | Eng Excellence | Developer APIs / Custom Domain | No |
| [ENT-3746](https://hello.jira.atlassian.cloud/browse/ENT-3746) | Allow Slack admins to restrict which Atlassian cloud sites c… | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Identity Platform / Guard | No |
| [ENT-3782](https://hello.jira.atlassian.cloud/browse/ENT-3782) | GCP EU DaRe | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | Data Residency | ⚠️ YES |
| [ENT-3784](https://hello.jira.atlassian.cloud/browse/ENT-3784) | AI Processing in India | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / Product Team | No |
| [ENT-3785](https://hello.jira.atlassian.cloud/browse/ENT-3785) | Increase BRIE scale for Jira database scale beyond 300 GB to… | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / Product Team | No |
| [ENT-3787](https://hello.jira.atlassian.cloud/browse/ENT-3787) | Increase BRIE scale for JSM database beyond 300 GB to suppor… | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | HIPAA / Compliance | ⚠️ YES |
| [ENT-3788](https://hello.jira.atlassian.cloud/browse/ENT-3788) | Increase BRIE for Confluence database scale beyond 32 GB to … | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | Data Residency | No |
| [ENT-3789](https://hello.jira.atlassian.cloud/browse/ENT-3789) | Separate Sandbox from target instance to allow continuous te… | ⏳ Pending Review | 🟡 P2 | TSP / Sandbox | TSP/Sandbox | No |
| [ENT-3790](https://hello.jira.atlassian.cloud/browse/ENT-3790) | [Outside US-only] AWS Failover between regions (MRDR - Multi… | ⏳ Pending Review | 🟡 P2 | Eng Excellence | Infrastructure / SRE | No |
| [ENT-3791](https://hello.jira.atlassian.cloud/browse/ENT-3791) | [Docusign] Rovo (chat and agents) cannot orchestrate across … | 🔍 Actively Investigating | 🟡 P2 | NOT CoreEng | Rovo / Product Team | No |
| [ENT-3810](https://hello.jira.atlassian.cloud/browse/ENT-3810) | SSO/OTP Multiple Policies | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Identity Platform / Guard | No |
| [ENT-3812](https://hello.jira.atlassian.cloud/browse/ENT-3812) | Be able to scale to Accenture's demand using sites | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / AI Product Team | No |
| [ENT-3813](https://hello.jira.atlassian.cloud/browse/ENT-3813) | Support OAuth API Requests in Jira Align | ⏳ Pending Review | 🟡 P2 | Identity & IAM | OAuth / Identity Platform | No |
| [ENT-3815](https://hello.jira.atlassian.cloud/browse/ENT-3815) | Implement Shadow IT controls in Atlassian Guard | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Guard / Threat Detection | No |
| [ENT-3817](https://hello.jira.atlassian.cloud/browse/ENT-3817) | Loom - Approved domain sharing | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Guard / Threat Detection | No |
| [ENT-3818](https://hello.jira.atlassian.cloud/browse/ENT-3818) | Loom - Support Global Organization Policies | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / AI Product Team | No |
| [ENT-3819](https://hello.jira.atlassian.cloud/browse/ENT-3819) | Loom - Policy inheritance and enforcement | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / AI Product Team | No |
| [ENT-3820](https://hello.jira.atlassian.cloud/browse/ENT-3820) | Loom - Public link restriction | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | JSM Product Team | No |
| [ENT-3821](https://hello.jira.atlassian.cloud/browse/ENT-3821) | Loom - Managed-only access | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo / AI Product Team | No |
| [ENT-3822](https://hello.jira.atlassian.cloud/browse/ENT-3822) | Loom - Uncontrolled usage prevention | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Confluence Product Team | No |
| [ENT-3823](https://hello.jira.atlassian.cloud/browse/ENT-3823) | Label Driven Policies | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Policy Engine | ⚠️ YES |
| [ENT-3827](https://hello.jira.atlassian.cloud/browse/ENT-3827) | Jira Cloud: Severe performance degradation when parent work … | ⏳ Pending Review | 🟡 P2 | Scale / CRSP | Jira Scale FY26 | No |
| [ENT-3830](https://hello.jira.atlassian.cloud/browse/ENT-3830) | Accurate Jira agent behavior and changelog queries | 🔍 Actively Investigating | 🟡 P2 | NOT CoreEng | Rovo Product Team | No |
| [ENT-3833](https://hello.jira.atlassian.cloud/browse/ENT-3833) | D32 - NATO Cybersecurity Directive Accreditation (AC/322-D(2… | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | New Compliance Certs FY26 | ⚠️ YES |
| [ENT-3834](https://hello.jira.atlassian.cloud/browse/ENT-3834) | App-Level Access Control for users/groups | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Policy Engine | ⚠️ YES |
| [ENT-3836](https://hello.jira.atlassian.cloud/browse/ENT-3836) | Ability to store backups on prem for emergency / exit scenar… | ⏳ Pending Review | 🟡 P2 | BRIE | BRIE Phase 2: Exit & Sovereignty | ⚠️ YES |
| [ENT-3837](https://hello.jira.atlassian.cloud/browse/ENT-3837) | DESC (Digital Economy Security Council) Certification — UAE | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | New Compliance Certs FY26 | ⚠️ YES |
| [ENT-3840](https://hello.jira.atlassian.cloud/browse/ENT-3840) | HTTP 2 Customer Refusal to Enable (Confluence/Jira)  | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | New Compliance Certs FY26 | ⚠️ YES |
| [ENT-3841](https://hello.jira.atlassian.cloud/browse/ENT-3841) | Improve Rovo's processing of large amount of data | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo Product Team | No |
| [ENT-3843](https://hello.jira.atlassian.cloud/browse/ENT-3843) | Increase the number of supported objects Rovo can create, ed… | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo Product Team | No |
| [ENT-3848](https://hello.jira.atlassian.cloud/browse/ENT-3848) | Restrict Org Admin from Self-Granting Product Access (Inform… | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Identity Platform / Admin Hub | No |
| [ENT-3849](https://hello.jira.atlassian.cloud/browse/ENT-3849) | Allow a user to turn off Follow Up questions on a scenario b… | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Rovo Product Team | No |
| [ENT-3851](https://hello.jira.atlassian.cloud/browse/ENT-3851) | Prevention of ingestion of new sensitive data in Jira and Co… | ⏳ Pending Review | 🟡 P2 | Compliance / RegInd | AI Data Sovereignty | ⚠️ YES |
| [ENT-3852](https://hello.jira.atlassian.cloud/browse/ENT-3852) | For AppLink WebSocket tunnels, enable perimeter DLP-compatib… | ⏳ Pending Review | 🟡 P2 | Identity & IAM + Eng Excellence | Networking / DLP Integration | ⚠️ YES |
| [ENT-3855](https://hello.jira.atlassian.cloud/browse/ENT-3855) | Enable Mobile App Management (MAM) policy targeting for subs… | ⏳ Pending Review | 🟡 P2 | Identity & IAM | Identity Platform / Guard | No |
| [ENT-3856](https://hello.jira.atlassian.cloud/browse/ENT-3856) | Ability to configure MCP server permissions per site (extend… | ⏳ Pending Review | 🟡 P2 | Identity & IAM + Eng Excellence | MCP Server Platform | ⚠️ YES |
| [ENT-3857](https://hello.jira.atlassian.cloud/browse/ENT-3857) | Native capability to move work items between CSM and JSM spa… | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | JSM Product Team | No |
| [ENT-3858](https://hello.jira.atlassian.cloud/browse/ENT-3858) | JSM – Deployment Gating – Pass GitHub actor/deployer email i… | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | JSM Product Team | No |
| [ENT-3859](https://hello.jira.atlassian.cloud/browse/ENT-3859) | Confluence space_permission_mapping table in Data Lake missi… | ⏳ Pending Review | 🟡 P2 | FinOps | Data Lake / Analytics | No |
| [ENT-3860](https://hello.jira.atlassian.cloud/browse/ENT-3860) | Atlassian MCP server should support connecting to multiple s… | ⏳ Pending Review | 🟡 P2 | Eng Excellence | MCP Server Platform | ⚠️ YES |
| [ENT-3861](https://hello.jira.atlassian.cloud/browse/ENT-3861) | Enable native Microsoft Teams integration for Confluence Whi… | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | Whiteboard Product Team | No |
| [ENT-3863](https://hello.jira.atlassian.cloud/browse/ENT-3863) | Support linked fields in forms - "Raise a Request" JSM skill | ⏳ Pending Review | 🟡 P2 | NOT CoreEng | JSM Product Team | No |
| [ENT-166](https://hello.jira.atlassian.cloud/browse/ENT-166) | Audit log access for site admins | ✅ Shipped | 🔵 P3 | ALP | ALP Platform | No |
| [ENT-398](https://hello.jira.atlassian.cloud/browse/ENT-398) | Customer-managed keys (CMK) with AWS Cloud HSM solutions | ⬛ Not Currently Prioritized | 🔵 P3 | Encryption / BYOK | CMK FY26 (deferred) | No |
| [ENT-555](https://hello.jira.atlassian.cloud/browse/ENT-555) | Single Logout - Logging out of Atlassian account does not lo… | ✅ Shipped | 🔵 P3 | Identity & IAM | Identity Platform | No |
| [ENT-1155](https://hello.jira.atlassian.cloud/browse/ENT-1155) | Immature Data Governance / Data Lifecycle Operational Proces… | ✅ Shipped | 🔵 P3 | Multiple | Data Governance FY26 | No |
| [ENT-1909](https://hello.jira.atlassian.cloud/browse/ENT-1909) | Support for backup direct to 3rd party cloud storage (AWS S3… | ✅ Shipped | 🔵 P3 | BRIE | BRIE Project | No |
| [ENT-1929](https://hello.jira.atlassian.cloud/browse/ENT-1929) | Support full backups with attachments for instances with lar… | ✅ Shipped | 🔵 P3 | BRIE | BRIE Project | No |
| [ENT-1983](https://hello.jira.atlassian.cloud/browse/ENT-1983) | Increase size limit for site backup imports (<3TB) | ✅ Shipped | 🔵 P3 | BRIE | BRIE Project | No |
| [ENT-2122](https://hello.jira.atlassian.cloud/browse/ENT-2122) | REST API capabilities for Atlassian Analytics | ✅ Shipped | 🔵 P3 | FinOps | CFINOPS / Analytics | No |
| [ENT-2199](https://hello.jira.atlassian.cloud/browse/ENT-2199) | Jira: Vertical scale 50K-100k users per instance | ✅ Shipped | 🔵 P3 | Scale / CRSP | Jira Scale FY26 | No |
| [ENT-2331](https://hello.jira.atlassian.cloud/browse/ENT-2331) | Support daily backups of Cloud products | ✅ Shipped | 🔵 P3 | BRIE | BRIE Project | No |
| [ENT-2643](https://hello.jira.atlassian.cloud/browse/ENT-2643) | Increase Atlassian user base and user provisioning limits to… | ✅ Shipped | 🔵 P3 | Identity & IAM | UUL / SCIM Scale | No |
| ENT-3672 | Spanish ENS certification to unlock Spanish public sector | 🔑 Pending Exec Decision | 🔵 P3 | TRIAGE NEEDED | ? | ⚠️ YES |
| ENT-3673 | Ability to opt-out from the auto-suspension of sandbox | ⬛ Not Currently Prioritized | 🔵 P3 | TSP / Sandbox | TSP/Sandbox | No |
| ENT-3680 | Rovo C5: Cloud Computing Compliance Controls Catalog (C5) | ⬛ Not Currently Prioritized | 🔵 P3 | Compliance / RegInd | New Compliance Certs FY26 | No |
| ENT-3737 | Regulated customers need comment edit history or granular co… | ❓ Closed | 🔵 P3 | Identity & IAM | Identity Platform | No |
| [ENT-3862](https://hello.jira.atlassian.cloud/browse/ENT-3862) | [AMAT] Rovo Trend Dashboard (to track usages) | ❓ Closed | 🔵 P3 | NOT CoreEng | Rovo / AI Product Team | No |

---

## 🏛️ Section 2: Per-Pillar Breakdown

### Identity & IAM (🔴 OVERLOADED)
**Owner:** Prashant Ghosal (sub-teams: Rocket, Goomda, Fortress, FastShift)  
**Jira:** `IDENTITY, GUARD` | **Confluence:** `I, TRUSTED`  
**Capacity Assessment:** Team executing DaRe+GCP migration+SCIM/Nexus+Admin Hub+Collab Context simultaneously. Cannot absorb new P1 work without scope cuts.

**35 tickets** | P0:1 P1:9 P2:21 P3:4

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-3824](https://hello.jira.atlassian.cloud/browse/ENT-3824) | Platform-native lifecycle governance for large-scale mu… | ⏳ Pending Review | 🔴 P0 | ⚠️ YES |
| [ENT-59](https://hello.jira.atlassian.cloud/browse/ENT-59) | Guarantee that my organisation's user account account i… | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-351](https://hello.jira.atlassian.cloud/browse/ENT-351) | Modify how app approvals work in enterprise environment… | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-652](https://hello.jira.atlassian.cloud/browse/ENT-652) | App migration content access problems - Restricted page… | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-764](https://hello.jira.atlassian.cloud/browse/ENT-764) | Purchase Apps for a subset of users on an instance | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-1690](https://hello.jira.atlassian.cloud/browse/ENT-1690) | Ability to configure what enterprise org level data is … | 📋 Public Roadmap | 🟠 P1 |  |
| [ENT-1703](https://hello.jira.atlassian.cloud/browse/ENT-1703) | Enterprise support (by exception) for site count above … | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-2089](https://hello.jira.atlassian.cloud/browse/ENT-2089) | Create a Migration / Data Management Admin role | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| ENT-3696 |  Ability to Identify Content/Work Authored or Edited by… | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-3809](https://hello.jira.atlassian.cloud/browse/ENT-3809) | Rovo | Policy to block MCP access for external users | 🔒 Roadmap (Internal Only) | 🟠 P1 | ⚠️ YES |
| [ENT-1786](https://hello.jira.atlassian.cloud/browse/ENT-1786) | [Cloud] Allow admins to remove the "Discover" and other… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-1804](https://hello.jira.atlassian.cloud/browse/ENT-1804) | Ability to mask sensitive content | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| [ENT-2303](https://hello.jira.atlassian.cloud/browse/ENT-2303) | Single Logout - Atlassian Account should support IdP-in… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-2625](https://hello.jira.atlassian.cloud/browse/ENT-2625) | Ability to deactivate users who haven't logged in for a… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-2880](https://hello.jira.atlassian.cloud/browse/ENT-2880) | Support "Scalable Silos" complex company archetype.  | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3291 | Classification Based Access Control | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3631 | Service Accounts in AGC | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3664 | Service account to owner association covering secure ac… | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3665 | IP range restrictions for Service Account network contr… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| ENT-3728 | Mobile App admin settings at the site level: Ability to… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3746](https://hello.jira.atlassian.cloud/browse/ENT-3746) | Allow Slack admins to restrict which Atlassian cloud si… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3810](https://hello.jira.atlassian.cloud/browse/ENT-3810) | SSO/OTP Multiple Policies | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3813](https://hello.jira.atlassian.cloud/browse/ENT-3813) | Support OAuth API Requests in Jira Align | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3815](https://hello.jira.atlassian.cloud/browse/ENT-3815) | Implement Shadow IT controls in Atlassian Guard | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3817](https://hello.jira.atlassian.cloud/browse/ENT-3817) | Loom - Approved domain sharing | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3823](https://hello.jira.atlassian.cloud/browse/ENT-3823) | Label Driven Policies | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3834](https://hello.jira.atlassian.cloud/browse/ENT-3834) | App-Level Access Control for users/groups | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3848](https://hello.jira.atlassian.cloud/browse/ENT-3848) | Restrict Org Admin from Self-Granting Product Access (I… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3852](https://hello.jira.atlassian.cloud/browse/ENT-3852) | For AppLink WebSocket tunnels, enable perimeter DLP-com… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3855](https://hello.jira.atlassian.cloud/browse/ENT-3855) | Enable Mobile App Management (MAM) policy targeting for… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3856](https://hello.jira.atlassian.cloud/browse/ENT-3856) | Ability to configure MCP server permissions per site (e… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-555](https://hello.jira.atlassian.cloud/browse/ENT-555) | Single Logout - Logging out of Atlassian account does n… | ✅ Shipped | 🔵 P3 |  |
| [ENT-1155](https://hello.jira.atlassian.cloud/browse/ENT-1155) | Immature Data Governance / Data Lifecycle Operational P… | ✅ Shipped | 🔵 P3 |  |
| [ENT-2643](https://hello.jira.atlassian.cloud/browse/ENT-2643) | Increase Atlassian user base and user provisioning limi… | ✅ Shipped | 🔵 P3 |  |
| ENT-3737 | Regulated customers need comment edit history or granul… | ❓ Closed | 🔵 P3 |  |

### BRIE (🟡 ACTIVE)
**Owner:** Lakshmi Behl  
**Jira:** `BRIE` | **Confluence:** `BRIE`  
**Capacity Assessment:** Open Beta launched. GA planned Jan 2026. Some headroom for Phase 2 scope if scoped correctly.

**13 tickets** | P0:0 P1:3 P2:6 P3:4

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-151](https://hello.jira.atlassian.cloud/browse/ENT-151) | Export all of my cloud data for long term storage in a … | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-311](https://hello.jira.atlassian.cloud/browse/ENT-311) | Apps backup and restore with 30 days retention | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| ENT-3668 | Data Residency for Backup and Restore | 🔒 Roadmap (Internal Only) | 🟠 P1 | ⚠️ YES |
| [ENT-2667](https://hello.jira.atlassian.cloud/browse/ENT-2667) | Automation Rules Should be Included in Jira Backups (Ba… | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3679 | Backup Automation Rules associated with Confluence prod… | ⏳ Pending Review | 🟡 P2 |  |
| ENT-3686 | Next steps with the Legacy Backup Manager UI availabili… | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3724 | Make backup and restore available to standard license c… | ⏳ Pending Review | 🟡 P2 |  |
| ENT-3726 | Backup retention > 30 days | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3836](https://hello.jira.atlassian.cloud/browse/ENT-3836) | Ability to store backups on prem for emergency / exit s… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-1909](https://hello.jira.atlassian.cloud/browse/ENT-1909) | Support for backup direct to 3rd party cloud storage (A… | ✅ Shipped | 🔵 P3 |  |
| [ENT-1929](https://hello.jira.atlassian.cloud/browse/ENT-1929) | Support full backups with attachments for instances wit… | ✅ Shipped | 🔵 P3 |  |
| [ENT-1983](https://hello.jira.atlassian.cloud/browse/ENT-1983) | Increase size limit for site backup imports (<3TB) | ✅ Shipped | 🔵 P3 |  |
| [ENT-2331](https://hello.jira.atlassian.cloud/browse/ENT-2331) | Support daily backups of Cloud products | ✅ Shipped | 🔵 P3 |  |

### TSP / Sandbox (🟢 MANAGEABLE)
**Owner:** Harpreet Singh Juneja / Sirisha Pendem  
**Jira:** `TSP` | **Confluence:** `TSP`  
**Capacity Assessment:** H2FY26 roadmap in-flight. Can absorb 1-2 new P2 items.

**5 tickets** | P0:0 P1:2 P2:2 P3:1

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-50](https://hello.jira.atlassian.cloud/browse/ENT-50) | EAP for the Ability to push (promote) Jira and JSM conf… | 📋 Public Roadmap | 🟠 P1 |  |
| ENT-3707 | Ability to copy Rovo agents between sandbox and product… | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-2124](https://hello.jira.atlassian.cloud/browse/ENT-2124) | Support large total attachment size in Confluence Sandb… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-3789](https://hello.jira.atlassian.cloud/browse/ENT-3789) | Separate Sandbox from target instance to allow continuo… | ⏳ Pending Review | 🟡 P2 |  |
| ENT-3673 | Ability to opt-out from the auto-suspension of sandbox | ⬛ Not Currently Prioritized | 🔵 P3 |  |

### Encryption / BYOK (🟡 FOCUSED)
**Owner:** Greg Zaney (Coral team)  
**Jira:** `ENCRYPT` | **Confluence:** `ENCRYPT`  
**Capacity Assessment:** Executing IC golden path first. FedRAMP+Commercial to follow. No capacity for new scope.

**3 tickets** | P0:0 P1:2 P2:0 P3:1

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-1958](https://hello.jira.atlassian.cloud/browse/ENT-1958) | Support AWS-XKS with Customer-managed keys (CMK) | 📋 Public Roadmap | 🟠 P1 |  |
| [ENT-2085](https://hello.jira.atlassian.cloud/browse/ENT-2085) | CMK (BYOK) - Apply Customer-managed keys retroactively … | 📋 Public Roadmap | 🟠 P1 |  |
| [ENT-398](https://hello.jira.atlassian.cloud/browse/ENT-398) | Customer-managed keys (CMK) with AWS Cloud HSM solution… | ⬛ Not Currently Prioritized | 🔵 P3 |  |

### ALP (🟡 Q4 CRITICAL PATH)
**Owner:** Akshay Nambiar  
**Jira:** `ALP` | **Confluence:** `ALP`  
**Capacity Assessment:** Dynamic Materialization milestone critical. 2 new ALP tickets manageable within existing project.

**8 tickets** | P0:0 P1:2 P2:5 P3:1

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-1057](https://hello.jira.atlassian.cloud/browse/ENT-1057) | Audit Log Retention for 12 months for AGP customers | 📋 Public Roadmap | 🟠 P1 |  |
| [ENT-2883](https://hello.jira.atlassian.cloud/browse/ENT-2883) | Embeddable audit logs for Jira/JSM | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-1158](https://hello.jira.atlassian.cloud/browse/ENT-1158) | Audit Logs for Admin pages | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3675 | Enhance Rovo audit logging and observability for AI-ass… | ⏳ Pending Review | 🟡 P2 |  |
| ENT-3685 | Guard Detect alert export with custom date range select… | ⏳ Pending Review | 🟡 P2 |  |
| ENT-3736 | Regulated customers need public APIs to capture all Con… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3738](https://hello.jira.atlassian.cloud/browse/ENT-3738) | Regulated customers need public APIs to capture all Con… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-166](https://hello.jira.atlassian.cloud/browse/ENT-166) | Audit log access for site admins | ✅ Shipped | 🔵 P3 |  |

### Compliance / RegInd (🔴 OVERLOADED)
**Owner:** Wayne Yim  
**Jira:** `REGS` | **Confluence:** `RegulatedIndustries`  
**Capacity Assessment:** Oasis IC (P0) + FedRAMP ongoing. New DESC/NATO/HIPAA/AI-sovereignty requests flooding in. Needs dedicated sub-team.

**17 tickets** | P0:4 P1:1 P2:11 P3:1

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-293](https://hello.jira.atlassian.cloud/browse/ENT-293) | US Classified/Top Secret/Secret Cloud deployment + IL6/… | 🔍 Actively Investigating | 🔴 P0 |  |
| [ENT-2289](https://hello.jira.atlassian.cloud/browse/ENT-2289) | FedRAMP High | 📋 Public Roadmap | 🔴 P0 |  |
| [ENT-2745](https://hello.jira.atlassian.cloud/browse/ENT-2745) | Virtual Private / Isolated cloud | 📋 Public Roadmap | 🔴 P0 |  |
| ENT-3702 | FedRamp | Docusign Feature | ⏳ Pending Review | 🔴 P0 |  |
| [ENT-2864](https://hello.jira.atlassian.cloud/browse/ENT-2864) | Customer can retain data up to n years to meet complian… | 🔒 Roadmap (Internal Only) | 🟠 P1 |  |
| [ENT-1638](https://hello.jira.atlassian.cloud/browse/ENT-1638) | Jira Data Center WCAG 2.1 AA Conformance Required | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-2460](https://hello.jira.atlassian.cloud/browse/ENT-2460) | AI Processing in Europe | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3711 | Increase projects and team limits of Plans (Advanced Ro… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-3739](https://hello.jira.atlassian.cloud/browse/ENT-3739) | Atlassian‑hosted LLMs with EU Data Residency | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3782](https://hello.jira.atlassian.cloud/browse/ENT-3782) | GCP EU DaRe | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3787](https://hello.jira.atlassian.cloud/browse/ENT-3787) | Increase BRIE scale for JSM database beyond 300 GB to s… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3788](https://hello.jira.atlassian.cloud/browse/ENT-3788) | Increase BRIE for Confluence database scale beyond 32 G… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3833](https://hello.jira.atlassian.cloud/browse/ENT-3833) | D32 - NATO Cybersecurity Directive Accreditation (AC/32… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3837](https://hello.jira.atlassian.cloud/browse/ENT-3837) | DESC (Digital Economy Security Council) Certification —… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3840](https://hello.jira.atlassian.cloud/browse/ENT-3840) | HTTP 2 Customer Refusal to Enable (Confluence/Jira)  | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| [ENT-3851](https://hello.jira.atlassian.cloud/browse/ENT-3851) | Prevention of ingestion of new sensitive data in Jira a… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| ENT-3680 | Rovo C5: Cloud Computing Compliance Controls Catalog (C… | ⬛ Not Currently Prioritized | 🔵 P3 |  |

### Scale / CRSP (🟢 SHIFTING)
**Owner:** CRSP Team  
**Jira:** `CRSP` | **Confluence:** `CRSP`  
**Capacity Assessment:** Confluence 250K shipped. Pivoting to Jira 150K+. Some headroom.

**5 tickets** | P0:0 P1:1 P2:3 P3:1

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-1520](https://hello.jira.atlassian.cloud/browse/ENT-1520) | Expand Confluence Capabilities to Support Customer Size… | 📋 Public Roadmap | 🟠 P1 |  |
| [ENT-1555](https://hello.jira.atlassian.cloud/browse/ENT-1555) | Google CloudSQL and Cloud storage support for Atlassian… | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| [ENT-1697](https://hello.jira.atlassian.cloud/browse/ENT-1697) | Gliffy app for Confluence cloud - performance issues | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-3827](https://hello.jira.atlassian.cloud/browse/ENT-3827) | Jira Cloud: Severe performance degradation when parent … | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-2199](https://hello.jira.atlassian.cloud/browse/ENT-2199) | Jira: Vertical scale 50K-100k users per instance | ✅ Shipped | 🔵 P3 |  |

### FinOps (🟢 LAUNCHING)
**Owner:** Ke Wang  
**Jira:** `CFINOPS, PPE` | **Confluence:** `CFINOPS`  
**Capacity Assessment:** Project Bigsky+Cypress active. FinOps portal launching. Modest headroom for analytics tickets.

**6 tickets** | P0:0 P1:0 P2:5 P3:1

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-2225](https://hello.jira.atlassian.cloud/browse/ENT-2225) | App usage for Confluence | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-2409](https://hello.jira.atlassian.cloud/browse/ENT-2409) | Ability to retrieve detailed billing information via RE… | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3318 | Analytics - Schema objects unavailable for Jira in the … | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3676 | Enable automated export or external sharing of Rovo usa… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-3859](https://hello.jira.atlassian.cloud/browse/ENT-3859) | Confluence space_permission_mapping table in Data Lake … | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-2122](https://hello.jira.atlassian.cloud/browse/ENT-2122) | REST API capabilities for Atlassian Analytics | ✅ Shipped | 🔵 P3 |  |

### Eng Excellence (🟡 EMERGING)
**Owner:** TBD (emerging pillar)  
**Jira:** `SHPLXII` | **Confluence:** `CoreEngineering`  
**Capacity Assessment:** No formal DRI. Growing set of developer platform / observability / API requests. Needs ownership definition.

**12 tickets** | P0:0 P1:0 P2:12 P3:0

| Key | Summary | Status | Priority | New Project? |
|---|---|---|---|---|
| [ENT-2590](https://hello.jira.atlassian.cloud/browse/ENT-2590) | REST API usage insights | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-2787](https://hello.jira.atlassian.cloud/browse/ENT-2787) | Improve public customer facing documentation around how… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-2788](https://hello.jira.atlassian.cloud/browse/ENT-2788) | Improve cloud app version visibility and information on… | 🔍 Actively Investigating | 🟡 P2 |  |
| [ENT-2858](https://hello.jira.atlassian.cloud/browse/ENT-2858) | Improve Visibility of Upcoming Features in Release Trac… | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3354 | Allow Rovo Agents to search multiple sites | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3436 | Private network connectivity to Atlassian Cloud (Eg: Pr… | 🔍 Actively Investigating | 🟡 P2 | ⚠️ YES |
| ENT-3669 | Statuspage for AGC | 🔍 Actively Investigating | 🟡 P2 |  |
| ENT-3730 | Ability to create Cloud Sites from set Enterprise Templ… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |
| ENT-3732 | Ability to have an efficient group membership retrieval… | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3745](https://hello.jira.atlassian.cloud/browse/ENT-3745) | Allow REST API calls via Atlassian custom domains | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3790](https://hello.jira.atlassian.cloud/browse/ENT-3790) | [Outside US-only] AWS Failover between regions (MRDR - … | ⏳ Pending Review | 🟡 P2 |  |
| [ENT-3860](https://hello.jira.atlassian.cloud/browse/ENT-3860) | Atlassian MCP server should support connecting to multi… | ⏳ Pending Review | 🟡 P2 | ⚠️ YES |

---

## 🆕 Section 3: New Project Candidates

*Tickets that require a NEW CoreEng Atlas project (no existing project covers them)*

### 🆕 Policy Engine / Label-Driven Policies
- **Trigger Tickets:** ENT-3823, ENT-3834, ENT-3291, ENT-3851, ENT-1804
- **Suggested Owner:** Identity & IAM (sub-team: Goomda)
- **Priority:** P1
- **Estimated Scope:** L (6-9 engineers, 2 quarters)
- **Business Justification:** Growing cluster of policy/governance requests: label-driven policies, classification-based access, sensitive data prevention, content masking. No single product team owns the policy infrastructure layer.

### 🆕 Service Account Management at Scale
- **Trigger Tickets:** ENT-3631, ENT-3664, ENT-3665, ENT-3809
- **Suggested Owner:** Identity & IAM (sub-team: Fortress)
- **Priority:** P1
- **Estimated Scope:** M (3-5 engineers, 1 quarter)
- **Business Justification:** Service accounts in AGC, owner association, IP range controls — forming a coherent cluster with no existing project coverage.

### 🆕 MCP Server Platform
- **Trigger Tickets:** ENT-3860, ENT-3856, ENT-3354
- **Suggested Owner:** Eng Excellence / Developer Platform
- **Priority:** P1
- **Estimated Scope:** M (4-6 engineers, 2 quarters)
- **Business Justification:** MCP multi-site support, per-site permissions, Rovo multi-site search — new class of enterprise requests enabled by MCP architecture.

### 🆕 Platform-Native Lifecycle Governance
- **Trigger Tickets:** ENT-3824, ENT-3730, ENT-2880
- **Suggested Owner:** Eng Excellence / Admin Hub
- **Priority:** P1
- **Estimated Scope:** L (6-8 engineers, 3 quarters)
- **Business Justification:** Multi-site lifecycle governance, scalable silos, cloud site templates — enterprise org management at scale needs a formal platform layer.

### 🆕 New Compliance Certifications FY26
- **Trigger Tickets:** ENT-3837, ENT-3833, ENT-3787, ENT-3680, ENT-3840
- **Suggested Owner:** Compliance / RegInd (Wayne Yim)
- **Priority:** P2
- **Estimated Scope:** M (3-4 engineers, 2 quarters)
- **Business Justification:** DESC (UAE), NATO D32, HIPAA AGC, Rovo C5 — new certifications beyond existing FedRAMP/IL5/C5 track; each unlocks new geo/sector.

### 🆕 BRIE Phase 2: Exit & Sovereignty
- **Trigger Tickets:** ENT-3836, ENT-3668
- **Suggested Owner:** BRIE (Lakshmi Behl)
- **Priority:** P2
- **Estimated Scope:** S (2-3 engineers, 1 quarter)
- **Business Justification:** On-prem backup for exit scenarios + data residency for backup data — new capability class beyond current BRIE GA scope.

### 🆕 AI Data Sovereignty
- **Trigger Tickets:** ENT-2460, ENT-3739, ENT-3851, ENT-3682
- **Suggested Owner:** Compliance / RegInd + Rovo
- **Priority:** P2
- **Estimated Scope:** M (4-5 engineers, 2 quarters)
- **Business Justification:** EU-only LLM processing, AI data residency, sensitive data ingestion prevention — cross-cutting AI governance with no current owner.

### 🆕 Private Network Connectivity
- **Trigger Tickets:** ENT-3436
- **Suggested Owner:** Eng Excellence / Infrastructure
- **Priority:** P2
- **Estimated Scope:** L (requires infra partnership, 3+ quarters)
- **Business Justification:** Private Endpoint / PrivateLink to Atlassian Cloud — significant infrastructure investment enabling regulated/high-security customers.

---

## ❓ Section 4: Triage Needed

| ENT Key | Summary | Ambiguity | Action |
|---|---|---|---|
| ENT-2460 | AI Processing in Europe | Is this data residency (Compliance/RegInd) or model selection (Rovo pr | Schedule 30-min triage call |
| ENT-1804 | Ability to mask sensitive content | DLP-like masking (Compliance/Guard) or user-facing redaction (Identity | Schedule 30-min triage call |
| ENT-2880 | Support Scalable Silos | Org Isolation extension (Identity) or new architecture pattern (Eng Ex | Schedule 30-min triage call |
| ENT-2347 | Object-level controls for Goals | Goals product team work or Identity/platform governance layer? | Schedule 30-min triage call |
| ENT-1555 | Google CloudSQL/Cloud Storage support | Platform infra (TDP/Infrastructure) or product-specific (Confluence/Ji | Schedule 30-min triage call |
| ENT-3811 | Privacy between entities | What are "entities"? Confluence spaces, Jira projects, org units? Clar | Schedule 30-min triage call |
| ENT-3354 | Allow Rovo Agents to search multiple sites | MCP platform (Eng Excellence) or Rovo product feature? Depends on impl | Schedule 30-min triage call |

---

## ⛔ Section 5: NOT CoreEng — Route to Product Teams

These 24 tickets are product feature requests, not platform/CoreEng work:

| ENT Key | Summary | Route To |
|---|---|---|
| ENT-2347 | Object level controls or permissions for Goals | Goals Product Team |
| ENT-2840 | JSM (Assets, Forms, Data Manager) [Rovo Connector Enhancemen | JSM / Rovo Product Team |
| ENT-3595 | Rovo skill to be able to read Jira Dashboards (and its widge | Rovo Product Team |
| ENT-3692 | Ability to select Atlassian Teams scope (site vs org) | Rovo / Product Team |
| ENT-3783 | Provide an Assets Data Manager Adapter for AWS Cloud  | JSM / Product Team |
| ENT-3784 | AI Processing in India | Rovo / Product Team |
| ENT-3785 | Increase BRIE scale for Jira database scale beyond 300 GB to | Rovo / Product Team |
| ENT-3791 | [Docusign] Rovo (chat and agents) cannot orchestrate across  | Rovo / Product Team |
| ENT-3805 | ROVO: Agent activity must be logged, capturing sufficient te | Rovo / Product Team |
| ENT-3812 | Be able to scale to Accenture's demand using sites | Rovo / AI Product Team |
| ENT-3818 | Loom - Support Global Organization Policies | Rovo / AI Product Team |
| ENT-3819 | Loom - Policy inheritance and enforcement | Rovo / AI Product Team |
| ENT-3820 | Loom - Public link restriction | JSM Product Team |
| ENT-3821 | Loom - Managed-only access | Rovo / AI Product Team |
| ENT-3822 | Loom - Uncontrolled usage prevention | Confluence Product Team |
| ENT-3830 | Accurate Jira agent behavior and changelog queries | Rovo Product Team |
| ENT-3841 | Improve Rovo's processing of large amount of data | Rovo Product Team |
| ENT-3843 | Increase the number of supported objects Rovo can create, ed | Rovo Product Team |
| ENT-3849 | Allow a user to turn off Follow Up questions on a scenario b | Rovo Product Team |
| ENT-3857 | Native capability to move work items between CSM and JSM spa | JSM Product Team |
| ENT-3858 | JSM – Deployment Gating – Pass GitHub actor/deployer email i | JSM Product Team |
| ENT-3861 | Enable native Microsoft Teams integration for Confluence Whi | Whiteboard Product Team |
| ENT-3862 | [AMAT] Rovo Trend Dashboard (to track usages) | Rovo / AI Product Team |
| ENT-3863 | Support linked fields in forms - "Raise a Request" JSM skill | JSM Product Team |

---

## 🌡️ Section 6: CoreEng Capacity Heat Map

| Pillar | Owner | P0 | P1 | P2 | P3 | Total | Load | Can Absorb? |
|---|---|---|---|---|---|---|---|---|
| Identity & IAM | Prashant Ghosal | 1 | 9 | 21 | 3 | 34 | 🔴 OVERLOADED | ❌ NO |
| BRIE | Lakshmi Behl | 0 | 3 | 6 | 4 | 13 | 🟡 ACTIVE | ⚠️ LIMITED |
| TSP / Sandbox | Harpreet Singh Juneja / Sirisha Pendem | 0 | 2 | 2 | 1 | 5 | 🟢 MANAGEABLE | ✅ YES |
| Encryption / BYOK | Greg Zaney | 0 | 2 | 0 | 1 | 3 | 🟡 FOCUSED | ⚠️ LIMITED |
| ALP | Akshay Nambiar | 0 | 2 | 6 | 1 | 9 | 🟡 Q4 CRITICAL PATH | ⚠️ LIMITED |
| Compliance / RegInd | Wayne Yim | 4 | 1 | 11 | 1 | 17 | 🔴 OVERLOADED | ❌ NO |
| Scale / CRSP | CRSP Team | 0 | 1 | 3 | 1 | 5 | 🟢 SHIFTING | ✅ YES |
| FinOps | Ke Wang | 0 | 0 | 5 | 1 | 6 | 🟢 LAUNCHING | ✅ YES |
| Eng Excellence | TBD | 0 | 0 | 16 | 0 | 16 | 🟡 EMERGING | ⚠️ LIMITED |

> **Critical Bottleneck:** Identity & IAM (32 tickets, overloaded) and Compliance/RegInd (17 tickets, overloaded) are the primary constraints for enterprise program delivery.

---

*Document generated May 01, 2026 09:49 UTC | Source: Atlassian TWG CLI + CoreEng understanding docs | Confidence: HIGH*