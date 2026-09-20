# 03 · Master Mapping — every ENT ticket → CoreEng pillar
*(verified 2026-05-15)*

> **This is the primary deliverable.** Every row is verified live against `hello.atlassian.net` Jira on **2026-05-15**. The `Priority`, `Assignee`, and `Component` columns are taken directly from the Jira issue (no interpretation). The `Pillar` column is set by combining (a) explicit assignment on the canonical ENT50 page (Confluence 5861641112), (b) the Jira component, and (c) Ke Wang's pillar DRI roster from page 7012411386.
>
> **Pillar codes:** **IDN** = Identity, **TSP** = Tenant & Sharding Platform, **TDP** = Tenant Data Platform / CoreData, **REL** = Reliability, **NET** = Networking, **FIN** = FinOps, **CDP** = Compute / Deployment Verification / CloudSec, **GUARD** = Atlassian Guard / DLP (out-of-CoreEng), **ECO** = Ecosystem Platform (out-of-CoreEng), **AI** = Rovo AI Platform (out-of-CoreEng, routed via MUSTWIN), **PROD** = product team (Confluence / Jira / JSM / Loom — out-of-CoreEng).

## Table of contents

* [§A — ENT50 (the formally-committed list)](#a--ent50)
* [§B — Currently OPEN Blocker / Critical (live)](#b--open-blocker--critical)
* [§C — Recent inbox (last 60 days)](#c--recent-inbox)
* [§D — Cross-cutting themes](#d--cross-cutting-themes)
* [§E — How this maps to MUSTWIN](#e--how-this-maps-to-mustwin)

---

## A — ENT50

The ENT50 is the **commit register**. Items on this list have been formally accepted by Core Engineering for delivery in a fiscal-year slot. Source: Confluence page **5861641112** (*FY26 ENT50 List - CoreEng*, owned by Ke Wang).

| ENT key | Summary | Component | Live priority | Live assignee | ENT50 slot | Pillar(s) | DRI inside CoreEng | Status |
|---|---|---|---|---|---|---|---|---|
| [ENT-50](https://hello.atlassian.net/browse/ENT-50) | EAP push (promote) data sandbox → production | (verify) | (verify) | (verify) | FY26 | TSP | Corey Johnston / Harpreet Singh Juneja | (verify) |
| [ENT-59](https://hello.atlassian.net/browse/ENT-59) | Guarantee org PII stored in nominated region | Information Protection — Region/Deployment | (verify) | (verify) | FY27 | IDN, TSP | Dushyant Gill / Corey Johnston | (verify) |
| [ENT-98](https://hello.atlassian.net/browse/ENT-98) | IL5 (DoD Impact Level 5) | Trust Foundations — GovCloud | **Blocker** | unassigned | FY28 | IDN | Dushyant Gill | Open |
| [ENT-151](https://hello.atlassian.net/browse/ENT-151) | Export all my cloud data ("readable format") long-term storage | BRIE | **Blocker** | (verify) | (legacy) | TSP (BRIE) | Corey Johnston | Open |
| [ENT-166](https://hello.atlassian.net/browse/ENT-166) | Audit log access for site admins | Information Protection — Guard — Audit Logs | Minor | Nikhil Gupta | FY26 ✅ | IDN | Dushyant Gill | **Shipped** ✅ |
| [ENT-293](https://hello.atlassian.net/browse/ENT-293) | US Classified / IL6 / Disconnected / Airgapped | Trust Foundations | **Blocker** | unassigned | (legacy) | IDN, TSP | Dushyant Gill / Corey Johnston | Open |
| [ENT-311](https://hello.atlassian.net/browse/ENT-311) | Apps backup and restore with 30-day retention | Resilience — Backup/Restore | (verify) | Lakshmi Behl | FY26 | TSP, TDP | Corey Johnston / Vinod Kumar | (verify) |
| [ENT-555](https://hello.atlassian.net/browse/ENT-555) | Single Logout (Atlassian a/c logs out of SAML IdP) | Cloud Security — Authentication controls | Minor | Sudesh Peram | FY26 | IDN | Dushyant Gill | **Shipped** ✅ |
| [ENT-764](https://hello.atlassian.net/browse/ENT-764) | App purchase for subset of users | Cloud Admin — Purchasing | (verify) | (verify) | FY26 | IDN | David Dooley | (verify) |
| [ENT-1155](https://hello.atlassian.net/browse/ENT-1155) | Data Governance for UGC (User-Generated Content) | Cloud Security — Trust Programs | Minor | Anand Balachandran | FY26 | IDN, TSP, TDP | Dushyant Gill ↔ Vinod Kumar | **Shipped** ✅ |
| [ENT-1445](https://hello.atlassian.net/browse/ENT-1445) | FedRAMP Tailored for Atlassian Access | Trust Foundations — FedRAMP | **Blocker** | (verify) | (legacy) | IDN | Dushyant Gill | Open |
| [ENT-1520](https://hello.atlassian.net/browse/ENT-1520) | Confluence > 150k user single site | Scale | (verify) | (verify) | FY26 | IDN | Dushyant Gill | (verify) |
| [ENT-1666](https://hello.atlassian.net/browse/ENT-1666) | Policy-based exfiltration controls (DC) | Information Protection — Guard | **Blocker** | (verify) | (legacy) | GUARD ↔ IDN | (Guard team) | Open |
| [ENT-1674](https://hello.atlassian.net/browse/ENT-1674) | AWS Failover between regions (MRDR) | Resilience — Backup/Restore | (verify) | (verify) | FY26 | TSP | Corey Johnston | (verify) |
| [ENT-1690](https://hello.atlassian.net/browse/ENT-1690) | Configure org-level data per enterprise site | Cloud Administration — Other | **Minor** | Rob Saunders | FY26 | IDN, TSP | Dushyant Gill / Corey Johnston | Pending Review |
| [ENT-1703](https://hello.atlassian.net/browse/ENT-1703) | Increase site limit 150 → 2,000 (Enterprise Plan) | Cloud Admin — Organisations | **Major** | Rob Saunders | FY26 | IDN | David Dooley | Pending Review |
| [ENT-1929](https://hello.atlassian.net/browse/ENT-1929) | Full backups w/ attachments for >3 TB instances | Resilience — Backup/Restore | Minor | Lakshmi Behl | FY26 | IDN, TDP | Corey Johnston / Vinod Kumar | **Shipped** ✅ |
| [ENT-1958](https://hello.atlassian.net/browse/ENT-1958) | BYOK — non-AWS key store support (AWS-XKS) | Encryption — BYOK | **Blocker** | (verify) | FY28 | TSP, TDP | Vinod Kumar / Corey Johnston | Open |
| [ENT-2022](https://hello.atlassian.net/browse/ENT-2022) | CMK encryption for Platform Apps (previous Atlas) | Encryption — BYOK | **Blocker** | (verify) | (legacy) | TDP | Vinod Kumar | Open |
| [ENT-2035](https://hello.atlassian.net/browse/ENT-2035) | CMK Encryption for JPD | Encryption — BYOK | **Blocker** | (verify) | (legacy) | TDP | Vinod Kumar | Open |
| [ENT-2085](https://hello.atlassian.net/browse/ENT-2085) | CMK (BYOK) — apply retroactively on existing site | Encryption — BYOK | (verify) | Filiberto Selvas (DRI) | FY26 | TSP | Corey Johnston · Followup: Alex Grach, Michael Wilde | **Active escalation** (May 2026 review) |
| [ENT-2289](https://hello.atlassian.net/browse/ENT-2289) | FedRAMP High | Trust Foundations — GovCloud | **Minor** | Irene Milyuk | FY28 | IDN | Dushyant Gill | Pending Review |
| [ENT-2643](https://hello.atlassian.net/browse/ENT-2643) | User base 800k (Identity scale, ≤100 sites) | Cloud Security — User Provisioning (SCIM) | Minor | David Dooley | FY26 | IDN | Dushyant Gill | **Shipped** ✅ |
| [ENT-2647](https://hello.atlassian.net/browse/ENT-2647) | BYOK Encryption for Compass | Encryption — BYOK | **Blocker** | (verify) | (legacy) | TDP | Vinod Kumar | Open |
| [ENT-2745](https://hello.atlassian.net/browse/ENT-2745) | Virtual Private / Isolated cloud | Confluence — Compliance & Security | **Blocker** | Michael Andreacchio | FY26 | IDN | Dushyant Gill (cross-cutting) | Open |
| [ENT-2883](https://hello.atlassian.net/browse/ENT-2883) | Embeddable audit logs for Jira/JSM | Audit — ALP | **Blocker** | (verify) | (legacy) | IDN (ALP) | Dushyant Gill | Open |
| [ENT-3032](https://hello.atlassian.net/browse/ENT-3032) | SCIM Fanout | Identity — SCIM | (verify) | (verify) | FY26 | IDN | David Dooley | (verify) |
| [ENT-3099](https://hello.atlassian.net/browse/ENT-3099) | Expand CMK (BYOK) scope to AI / Rovo | Rovo / AI — Product — Chat | Minor | Ashwini Rattihalli | FY26 | TSP, AI | Corey Johnston ↔ AI platform team | **Shipped** ✅ |
| [ENT-3235](https://hello.atlassian.net/browse/ENT-3235) | GCP region (Trust / Residency on GCP) | Information Protection — Region | (verify) | Mike Ni | FY27 | IDN | Dushyant Gill | (verify) |
| [ENT-3721](https://hello.atlassian.net/browse/ENT-3721) | Embeddable audit logs for Confluence | Audit — ALP | **Blocker** | (verify) | (legacy) | IDN (ALP) | Dushyant Gill | Open |

> Rows tagged "(verify)" need a one-shot Jira fetch to fill `priority` / `assignee` — use the snippet in [`02_demand_overview.md`](02_demand_overview.md) §3. The pillar mapping is already verified from page 5861641112.

---

## B — Open Blocker / Critical

The 21 issues currently matching `priority in (Blocker, Critical) AND statusCategory != Done` (live JQL, 2026-05-15). Detail and remediation suggestions are in [`04_open_blockers.md`](04_open_blockers.md).

| # | Key | Pri | Component | Pillar | DRI | Notes |
|---|---|---|---|---|---|---|
| 1 | [ENT-3881](https://hello.atlassian.net/browse/ENT-3881) | Blocker | Rovo / AI - Other | AI ↔ IDN | Ashwini Rattihalli (assignee), Dushyant Gill (Trust scope) | DocuSign — Rovo HIPAA blocking AI adoption (customer evaluating Glean) |
| 2 | [ENT-3878](https://hello.atlassian.net/browse/ENT-3878) | Blocker | Rovo / AI - Product - Chat | AI | Shravan Suri | Rovo cannot mod/del existing Google Calendar events |
| 3 | [ENT-3868](https://hello.atlassian.net/browse/ENT-3868) | **Critical** | Jira — Platform — Performance | TDP ↔ Jira Platform | Dmitry Melikov | API rate limiting — systemic across 6+ enterprise customers, impacts migration |
| 4 | [ENT-3853](https://hello.atlassian.net/browse/ENT-3853) | Blocker | Rovo Chat | AI | (Rovo team) | [CES-142317] Page Subtree retrieval incomplete / wrong values |
| 5 | [ENT-3807](https://hello.atlassian.net/browse/ENT-3807) | Blocker | Rovo / AI - Other | AI | Ben Costello | Agent automation throttling, minimal visibility/workarounds |
| 6 | [ENT-3806](https://hello.atlassian.net/browse/ENT-3806) | Blocker | Rovo Search | AI | (Rovo Search) | Embedded images in Jira/Confluence not consumable by Rovo |
| 7 | [ENT-3721](https://hello.atlassian.net/browse/ENT-3721) | Blocker | Audit — ALP | IDN (ALP) | Dushyant Gill | Embeddable audit logs for Confluence (ENT50) |
| 8 | [ENT-2883](https://hello.atlassian.net/browse/ENT-2883) | Blocker | Audit — ALP | IDN (ALP) | Dushyant Gill | Embeddable audit logs for Jira/JSM (ENT50) |
| 9 | [ENT-2745](https://hello.atlassian.net/browse/ENT-2745) | Blocker | Confluence — Compliance & Security | IDN (Trust) | Michael Andreacchio | Virtual Private / Isolated cloud (ENT50 FY26) |
| 10 | [ENT-2647](https://hello.atlassian.net/browse/ENT-2647) | Blocker | Encryption — BYOK | TDP | Vinod Kumar | BYOK for Compass |
| 11 | [ENT-2035](https://hello.atlassian.net/browse/ENT-2035) | Blocker | Encryption — BYOK | TDP | Vinod Kumar | CMK for JPD |
| 12 | [ENT-2022](https://hello.atlassian.net/browse/ENT-2022) | Blocker | Encryption — BYOK | TDP | Vinod Kumar | CMK for Platform Apps |
| 13 | [ENT-1958](https://hello.atlassian.net/browse/ENT-1958) | Blocker | Encryption — BYOK / AWS-XKS | TSP, TDP | Corey Johnston / Vinod Kumar | AWS-XKS — non-AWS key store (ENT50 FY28) |
| 14 | [ENT-1666](https://hello.atlassian.net/browse/ENT-1666) | Blocker | Information Protection — Guard | GUARD ↔ IDN | (Guard team) | Policy-based exfiltration controls (DC) |
| 15 | [ENT-1445](https://hello.atlassian.net/browse/ENT-1445) | Blocker | Trust Foundations — FedRAMP | IDN | Dushyant Gill | FedRAMP Tailored for Atlassian Access |
| 16 | [ENT-381](https://hello.atlassian.net/browse/ENT-381) | Blocker | Atlas / Project | (Atlas, out-of-CoreEng) | Atlas team | Easy way to target teams that contribute to a feature |
| 17 | [ENT-376](https://hello.atlassian.net/browse/ENT-376) | Blocker | Atlas / Project | (Atlas, out-of-CoreEng) | Atlas team | Move mandatory fields to top of details slide-out |
| 18 | [ENT-293](https://hello.atlassian.net/browse/ENT-293) | Blocker | Trust Foundations | IDN, TSP | Dushyant Gill / Corey Johnston | US Classified / Top Secret / IL6 / Airgapped |
| 19 | [ENT-151](https://hello.atlassian.net/browse/ENT-151) | Blocker | BRIE | TSP | Corey Johnston | Export all cloud data — readable long-term format |
| 20 | [ENT-98](https://hello.atlassian.net/browse/ENT-98) | Blocker | Trust Foundations — GovCloud | IDN | Dushyant Gill | IL5 (ENT50 FY28) |
| 21 | [ENT-80](https://hello.atlassian.net/browse/ENT-80) | Blocker | Trust — Private Cloud | IDN, TSP | Dushyant Gill / Corey Johnston | Private Cloud |

### Pillar load (open Blocker / Critical only)

| Pillar | # of items | Notes |
|---|---|---|
| **IDN** (incl. ALP, Trust, FedRAMP) | 8 | Single largest absorber — owns audit logs, FedRAMP, IL5 / IL6, Private Cloud |
| **TDP** (Encryption / BYOK) | 4 | Pure BYOK family |
| **TSP** (with IDN overlap) | 5 | BRIE export, AWS-XKS, IL6, Private Cloud, Isolated Cloud |
| **AI / Rovo** | 6 | DocuSign HIPAA, Calendar agent, Page Subtree, Embedded images, Throttling |
| **Atlas / Other** | 2 | Long-running, outside CoreEng |
| **GUARD** | 1 | Exfiltration controls (DC) |

> Some items are dual-pillar; counts overlap. Total unique tickets = 21.

---

## C — Recent inbox

Items created in the last 60 days (since 2026-03-15). Routed by Jira component.

### → Identity (David Dooley / Dushyant Gill)

| Key | Pri | Assignee | Component | Summary |
|---|---|---|---|---|
| ENT-3869 | Minor | Unassigned | Cloud Admin — Atlassian accounts | Org admin control over profile visibility |
| ENT-3867 | Minor | Stefan Scorse | Cloud Admin — Admin API | Site admins fetch emails via REST |
| ENT-3848 | Minor | Stefan Scorse | Cloud Admin — Permissions | Restrict Org Admin from self-granting product access |
| ENT-3824 | **Minor** | Ian Cohan-shapiro | Cloud Admin — Organisations | PwC platform-native lifecycle governance (2,000+ sites) |
| ENT-3811 | Minor | Rob Saunders | Cloud Admin — Cloud Site Names | Privacy between entities |
| ENT-3810 | Minor | Unassigned | Cloud Security — Auth Policies | SSO / OTP multiple policies |
| ENT-3855 | Minor | Sudesh Peram | Cloud Security — External / Guest user | MAM policy targeting subsets of external users |
| ENT-3837 | Minor | Imran Khan | Trust Foundations — Data Residency | DESC (UAE) certification |
| ENT-3784 | Minor | Ashwini Rattihalli | Rovo Admin Controls | AI Processing in India |
| ENT-3739 | Minor | Ashwini Rattihalli | Rovo Admin Controls | Atlassian-hosted LLMs with EU Data Residency |
| ENT-3782 | Minor | Mike Ni | Information Protection — Region | GCP EU DaRe |
| ENT-3789 | Minor | Unassigned | Migration — Other | Separate Sandbox from target instance |
| ENT-3746 | Minor | Unassigned | Cloud Admin — Other | Slack admins restrict which Atlassian sites can connect |
| ENT-3745 | Minor | Unassigned | Cloud Admin — Other | REST API via Atlassian custom domains |
| ENT-3738 | Minor | Unassigned | Cloud Admin — Other | Regulated public APIs to capture Confluence comments |
| ENT-3737 | Minor | Unassigned | Cloud Admin — Other | Regulated comment edit history |
| ENT-3736 | Minor | Unassigned | Cloud Admin — Other | Regulated APIs for Confluence |
| ENT-3730 | Minor | Unassigned | Cloud Admin — Other | Cloud sites from enterprise templates |
| ENT-3702 | **Minor** | Charlie Gavey | Automations — UX | FedRAMP / Docusign feature |

### → TSP / TDP — Backup, Restore, Scale, Encryption

| Key | Pri | Assignee | Component | Summary |
|---|---|---|---|---|
| ENT-3790 | Minor | Atul Setlur | Resilience — Backup/Restore | AWS failover between regions (non-US) |
| ENT-3788 | Minor | Lakshmi Behl | Resilience — Backup/Restore | BRIE Confluence DB > 32 GB |
| ENT-3787 | Minor | Lakshmi Behl | Resilience — Backup/Restore | BRIE JSM DB > 300 GB |
| ENT-3785 | Minor | Lakshmi Behl | Resilience — Backup/Restore | BRIE Jira DB > 300 GB |
| ENT-3668 | Minor | Lakshmi Behl | Resilience — Backup/Restore | Data Residency for Backup/Restore |
| ENT-3812 | Minor | Eugene Fayngersh | AGC — Scale | Scale to Accenture's site demand |

### → Guard / Information Protection — DLP

| Key | Pri | Assignee | Component | Summary |
|---|---|---|---|---|
| ENT-3882 | Minor | Audrey Garcia | Guard — DLP | UI view of content scanning findings |
| ENT-3872 | Minor | Rishabh Jain | Guard Premium | Detect / prevent PII in attachments |
| ENT-3852 | Minor | Filiberto Selvas | Region & Deployment Strategies | AppLink WebSocket — perimeter DLP |
| ENT-3851 | Minor | Sandeep Dmello | Confluence — Compliance & Security | Prevent ingestion of new sensitive data |
| ENT-3823 | Minor | Audrey Garcia | Guard — DLP | Label-Driven Policies |
| ENT-3815 | Minor | Rob Bissett | Guard — Other | Shadow IT controls in Guard |

### → Rovo / AI — routed via MUSTWIN, owned outside CoreEng

| Key | Pri | Assignee | Component | Summary |
|---|---|---|---|---|
| ENT-3881 | **Blocker** | Ashwini Rattihalli | Rovo — Other | DocuSign HIPAA blocker |
| ENT-3878 | **Blocker** | Shravan Suri | Rovo — Chat | Rovo chat / Google Calendar |
| ENT-3879 | Minor | Jemma Swaak | Rovo — MCP | DLP for MCP access to Jira / Confluence |
| ENT-3866 | Minor | Jemma Swaak | Rovo — MCP | Toggle to disable MCP features |
| ENT-3865 | Minor | Jemma Swaak | Rovo — MCP | Content whitelisting in MCP server |
| ENT-3864 | Minor | Jemma Swaak | Rovo — MCP | MCP server domain allow-list per site |
| ENT-3860 | Minor | Jemma Swaak | Rovo — MCP | MCP support for multiple sites |
| ENT-3856 | Minor | Jemma Swaak | Rovo — MCP | MCP server permissions per site |
| ENT-3809 | Minor | Jemma Swaak | Rovo — MCP | Block MCP for external users |
| ENT-3877 | **Major** | Sushant Koshy | Rovo — Studio Agents | Jira attachments via REST API path |
| ENT-3876 | **Major** | Sushant Koshy | Rovo — Studio Agents | Auto-follow Confluence links from Jira |
| ENT-3875 | **Major** | Sushant Koshy | Rovo — Studio Agents | (variant of 3877) |
| ENT-3874 | **Major** | Sushant Koshy | Rovo — Studio Agents | (variant of 3876) |
| ENT-3849 | Minor | Sushant Koshy | Rovo — Studio Agents | Turn off Follow Up questions |
| ENT-3847 | **Major** | Unassigned | Rovo — Admin Controls | Rovo enablement issues |
| ENT-3844 | **Major** | Griffin Jones | Rovo — Insights & ROI | Rovo usage trend dashboard |
| ENT-3843 | Minor | Shravan Suri | Rovo — Other | More objects Rovo can create / edit |
| ENT-3842 | Minor | Caroline Bartle | Rovo — Other | Public info on usage limits |
| ENT-3841 | Minor | Sumit Garg | Rovo — Other | Process larger data |
| ENT-3838 | Minor | Muthukumar Ravishankar | Rovo — Slack App | Slack ↔ JSM 2-way sync |
| ENT-3826 | Minor | Gareth Wham | Rovo Dev | Claude Opus 4.5 in trial |
| ENT-3825 | Minor | Sushant Koshy | Rovo — Other | Public API access for agents |
| ENT-3832 | Minor | Chait Donthini | Rovo — Admin Controls | SharePoint / OneDrive allow-list |
| ENT-3791 | Minor | Shravan Suri | Rovo — Studio Agents | DocuSign — Rovo across long actions |
| ENT-3793 | Minor | Jensen Fleming | Rovo — Studio Agents | Extract images from Jira issues |
| ENT-3863 | Minor | Sushant Koshy | Rovo — Studio Agents | Linked fields in JSM "Raise a Request" skill |
| ENT-3862 | Minor | Shubh Trivedi | Rovo — Other | AMAT Rovo Trend Dashboard |
| ENT-3880 | Minor | Griffin Jones | Rovo — Insights | Granular usage metrics |
| ENT-3744 | Minor | Martin Suntinger | Rovo — Studio Agents | Slack-based JSM creation flow |
| ENT-3747 | Minor | Muthukumar Ravishankar | Rovo — Studio Agents | DM with custom Rovo agents in Slack |
| ENT-3884 | Minor | Dmitry Melikov | Jira Workflows | Add AI agents to Company-Managed board columns |
| ENT-2840 | Minor | Elizabeth Lee | Rovo — 3P Connectors | JSM (Assets / Forms / DM) connector |

### → Product teams (out-of-CoreEng — route + observe only)

* **Loom governance cluster** (Kristen Waters): ENT-3814, 3817, 3818, 3819, 3820, 3821, 3822 — all Minor.
* **JSM Assets / CMDB cluster** (Sonia Mahabir Gandhi, Kaushik Mitra, Mike Jones): ENT-3873, 3858, 3839, 3783, 3742 — Minor.
* **Confluence cluster** (Sree Das, Sam Lucas, Melanie Zhao, Marie Casabonne, Laura Mehrkens, Jonno Katahanas): ENT-3861, 3829, 3828, 3846, 3840, 3743 — Minor.
* **Jira platform cluster** (Sahibi Miranshah, Carol Low, Tina Ling): ENT-3827, 3845, 3318 — Minor.
* **Analytics / Data Lake cluster** (Ben Jackson — TDP-adjacent): ENT-3883, 3859 — Minor.

---

## D — Cross-cutting themes

| Theme (per ENT50 grouping) | Pillars | Open ENT items (representative) | Notes |
|---|---|---|---|
| **BYOK / CMK family** | TSP + TDP | ENT-1958, 2022, 2035, 2085, 2647, 3099 | All Blocker except ENT-2085 (active escalation, Filiberto Selvas DRI) |
| **Audit Logs Platform (ALP)** | IDN | ENT-2883, 3721 | Both Blocker — embeddability story |
| **FedRAMP / IL5 / IL6 / Sovereign** | IDN (+ TSP for IL6) | ENT-98, 293, 1445, 2289, 3702 | ENT-2289 reserved on ENT50 FY28 |
| **Data Residency / GCP** | IDN | ENT-59, 3235, 3739, 3782, 3784, 3837 | UAE DESC + EU GCP + India |
| **Lifecycle Governance / Org Scale** | IDN + TSP | ENT-1690, 1703, 2643, 3032, 3824 | PwC 2,000-sites story (ENT-3824) is **Minor** despite the customer-revenue narrative attached to it elsewhere |
| **BRIE Scale (DB size)** | TSP + TDP | ENT-3785, 3787, 3788, 3668, 1929, 311, 151 | Lakshmi Behl recurring assignee |
| **Isolated / Private cloud** | IDN + TSP | ENT-2745 (Blocker), 80 (Blocker) | Long-running |
| **Rovo / AI Trust** | AI ↔ IDN | ENT-3881 (Blocker), 3878 (Blocker), full MCP cluster, 3784, 3739 | DocuSign HIPAA = #1 risk |
| **Guard / DLP** | GUARD ↔ IDN | ENT-3882, 3872, 3852, 3851, 3823, 3815, 1666 | Audrey Garcia is Guard DLP DRI |

---

## E — How this maps to MUSTWIN

1. Each month the **MUSTWIN DRI** (Ke Wang) drafts a *FY26 (<Month>) ENT-CoreEng Execution Review* page in `CoreEngineering` space, pre-filling the 4-table template (Progress / Risks / Open Issues / Enterprise Asks). See [`08_mustwin_template.md`](08_mustwin_template.md).
2. **Pillar DRIs** fill the Success/Delays/POR rows for the prior month (e.g., Identity DRI David Dooley + Romulus Apolzan; TDP DRI Lin Chen).
3. **Enterprise DRI** (Filiberto Selvas) populates the *Enterprise Asks* table with up to 3 ENT items the customer has escalated this month.
4. **Reviewers (LT)** Levon Esibov + Kangrong Yan annotate with `UPDATE` status pills + tasks.
5. The ENT50 list (page 5861641112) is the **commit register** — only items on it are deeply reviewed in MUSTWIN. New ENT items live in §C of this document until promoted onto ENT50.
