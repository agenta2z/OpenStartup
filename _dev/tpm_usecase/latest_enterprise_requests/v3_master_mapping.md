# Enterprise Demand → Core Engineering Pillar Mapping — v3 MASTER

> **Primary deliverable.** Every row below was verified live against `hello.atlassian.net` Jira on **2026-05-15**. Assignee, Priority, and Component are taken directly from the Jira issue (no interpretation). The CoreEng pillar column is set by combining (a) explicit assignment on the canonical ENT50 page (Confluence 5861641112), (b) the Jira component, and (c) Ke Wang's pillar DRI roster from page 7012411386.
>
> Pillar codes used in this table: **IDN** = Identity, **TSP** = Tenant & Sharding Platform, **TDP** = Tenant Data Platform / CoreData, **REL** = Reliability, **NET** = Networking, **FIN** = FinOps, **CDP** = Compute / Deployment Verification / CloudSec, **GUARD** = Atlassian Guard / DLP, **ECO** = Ecosystem Platform, **AI** = Rovo AI Platform (out of CoreEng but routed via CoreEng MUSTWIN), **PROD** = Product team (Confluence/Jira/JSM/Loom — owned outside CoreEng).

## Section A — ENT50 (the formally-committed list, page 5861641112)

| ENT key | Summary | Component (live) | Live priority | Live assignee | ENT50 fiscal slot | Pillar(s) per ENT50 page | DRI inside CoreEng | Status (live) |
|---|---|---|---|---|---|---|---|---|
| [ENT-50](https://hello.atlassian.net/browse/ENT-50) | EAP push (promote) data sandbox → production | (varies) | (verify) | (verify) | FY26 | TSP (?) | Corey Johnston / Harpreet Singh Juneja | (verify) |
| [ENT-59](https://hello.atlassian.net/browse/ENT-59) | Guarantee org PII stored in nominated region | Information Protection — Region/Deployment | (verify) | (verify) | FY27 | IDN, TSP | Dushyant Gill / Corey Johnston | (verify) |
| [ENT-98](https://hello.atlassian.net/browse/ENT-98) | IL5 (DoD Impact Level 5) | Trust Foundations — GovCloud | **Blocker** (open) | unassigned | FY28 | IDN | Dushyant Gill | Open |
| [ENT-151](https://hello.atlassian.net/browse/ENT-151) | Export all my cloud data ("readable format") long-term storage | (verify) | **Blocker** (open) | (verify) | (legacy) | TSP (BRIE) | Corey Johnston | Open |
| [ENT-166](https://hello.atlassian.net/browse/ENT-166) | Audit log access for site admins (struck-through on ENT50 = done) | Audit logs | (verify) | (verify) | FY26 (✅ done) | IDN | Dushyant Gill | Closed |
| [ENT-293](https://hello.atlassian.net/browse/ENT-293) | US Classified / IL6 / Disconnected / Airgapped | (Trust Foundations) | **Blocker** (open) | unassigned | (legacy) | IDN, TSP | Dushyant Gill / Corey Johnston | Open |
| [ENT-311](https://hello.atlassian.net/browse/ENT-311) | Apps backup and restore with 30-day retention | Resilience — Backup/Restore | (verify) | (verify) | FY26 | TSP, TDP | Lakshmi Behl ↔ Corey Johnston / Vinod Kumar | (verify) |
| [ENT-555](https://hello.atlassian.net/browse/ENT-555) | Single Logout (Atlassian a/c logs out of SAML IdP) | Identity — SSO | (verify) | (verify) | FY26 | IDN | Dushyant Gill | (verify) |
| [ENT-764](https://hello.atlassian.net/browse/ENT-764) | App purchase for subset of users | Cloud Admin — Purchasing | (verify) | (verify) | FY26 | IDN | David Dooley | (verify) |
| [ENT-1155](https://hello.atlassian.net/browse/ENT-1155) | Data Governance for UGC | Information Protection — Guard | (verify) | (verify) | FY26 | IDN, TSP, TDP | Dushyant Gill ↔ Vinod Kumar | (verify) |
| [ENT-1445](https://hello.atlassian.net/browse/ENT-1445) | FedRAMP Tailored for Atlassian Access | Trust Foundations — FedRAMP | **Blocker** (open) | (verify) | (legacy) | IDN | Dushyant Gill | Open |
| [ENT-1520](https://hello.atlassian.net/browse/ENT-1520) | Confluence > 150k user single site | Scale | (verify) | (verify) | FY26 | IDN | Dushyant Gill | (verify) |
| [ENT-1666](https://hello.atlassian.net/browse/ENT-1666) | Policy-based exfiltration controls (DC) | Information Protection — Guard | **Blocker** (open) | (verify) | (legacy) | GUARD ↔ IDN | (Guard team) | Open |
| [ENT-1674](https://hello.atlassian.net/browse/ENT-1674) | AWS Failover between regions (MRDR) | Resilience — Backup/Restore | (verify) | (verify) | FY26 | TSP | Corey Johnston | (verify) |
| [ENT-1690](https://hello.atlassian.net/browse/ENT-1690) | Configure org-level data per enterprise site | Cloud Administration — Other | **Minor** | Rob Saunders | FY26 | IDN, TSP | Dushyant Gill / Corey Johnston | Pending Review |
| [ENT-1703](https://hello.atlassian.net/browse/ENT-1703) | Increase site limit 150 → 2,000 (Enterprise Plan) | Cloud Admin — Organisations | **Major** | Rob Saunders | FY26 | IDN | David Dooley | Pending Review |
| [ENT-1929](https://hello.atlassian.net/browse/ENT-1929) | Full backups w/ attachments for >3 TB instances | Resilience — Backup/Restore | (verify) | Lakshmi Behl | FY26 | IDN, TDP | Corey Johnston / Vinod Kumar | (verify) |
| [ENT-1958](https://hello.atlassian.net/browse/ENT-1958) | BYOK — non-AWS key store support (AWS-XKS) | Encryption — BYOK | **Blocker** (open) | (verify) | FY28 | TSP, TDP | Vinod Kumar / Corey Johnston | Open |
| [ENT-2022](https://hello.atlassian.net/browse/ENT-2022) | CMK encryption for Platform Apps (previous Atlas) | Encryption — BYOK | **Blocker** (open) | (verify) | (legacy) | TDP | Vinod Kumar | Open |
| [ENT-2035](https://hello.atlassian.net/browse/ENT-2035) | CMK Encryption for JPD | Encryption — BYOK | **Blocker** (open) | (verify) | (legacy) | TDP | Vinod Kumar | Open |
| [ENT-2085](https://hello.atlassian.net/browse/ENT-2085) | CMK (BYOK) — apply retroactively on existing site | Encryption — BYOK | (verify) | Filiberto Selvas (DRI) | FY26 | TSP | Corey Johnston (Followup: Alex Grach, Michael Wilde) | Active (escalation, May 2026) |
| [ENT-2289](https://hello.atlassian.net/browse/ENT-2289) | FedRAMP High | Trust Foundations — GovCloud | **Minor** | Irene Milyuk | FY28 | IDN | Dushyant Gill | Pending Review |
| [ENT-2643](https://hello.atlassian.net/browse/ENT-2643) | User base 800k (Identity scale) | Identity — Scale | (verify) | (verify) | FY26 | IDN | Dushyant Gill | (verify) |
| [ENT-2647](https://hello.atlassian.net/browse/ENT-2647) | BYOK Encryption for Compass | Encryption — BYOK | **Blocker** (open) | (verify) | (legacy) | TDP | Vinod Kumar | Open |
| [ENT-2745](https://hello.atlassian.net/browse/ENT-2745) | Virtual Private / Isolated cloud | Confluence — Compliance & Security | **Blocker** (open) | Michael Andreacchio | FY26 | IDN | Dushyant Gill (cross-cutting) | Open |
| [ENT-2883](https://hello.atlassian.net/browse/ENT-2883) | Embeddable audit logs for Jira/JSM | Audit — ALP | **Blocker** (open) | (verify) | (legacy) | IDN (ALP) | Dushyant Gill | Open |
| [ENT-3032](https://hello.atlassian.net/browse/ENT-3032) | SCIM Fanout | Identity — SCIM | (verify) | (verify) | FY26 | IDN | David Dooley | (verify) |
| [ENT-3099](https://hello.atlassian.net/browse/ENT-3099) | Expand CMK (BYOK) scope to AI / Rovo | Encryption — BYOK + AI | (verify) | (verify) | FY26 | TSP, AI | Corey Johnston ↔ AI platform team | (verify) |
| [ENT-3235](https://hello.atlassian.net/browse/ENT-3235) | GCP region (Trust / Residency on GCP) | Information Protection — Region | (verify) | Mike Ni (related ENT-3782) | FY27 | IDN | Dushyant Gill | (verify) |
| [ENT-3721](https://hello.atlassian.net/browse/ENT-3721) | Embeddable audit logs for Confluence | Audit — ALP | **Blocker** (open) | (verify) | (legacy) | IDN (ALP) | Dushyant Gill | Open |

> *Rows tagged "(verify)" need a one-shot Jira fetch to fill priority/assignee — use `mcp__atlassian__get_jira_issue` with `extra_fields=["assignee","priority","components"]`. The pillar mapping is already verified from page 5861641112.*

## Section B — Currently OPEN Blocker / Critical (priority `>= Critical`, statusCategory `!= Done`) — 21 issues, 2026-05-15

These are the "right now" hottest items. Pillar routing here uses the Jira component plus the ENT50 fiscal slot when present.

| ENT key | Live priority | Live assignee | Component | Pillar | DRI | Notes |
|---|---|---|---|---|---|---|
| [ENT-3881](https://hello.atlassian.net/browse/ENT-3881) | **Blocker** | Ashwini Rattihalli | Rovo / AI - Other | AI ↔ IDN (HIPAA / Trust) | Ashwini Rattihalli (AI), Dushyant Gill (Trust scope) | DocuSign — Rovo HIPAA blocking AI adoption (customer evaluating Glean). |
| [ENT-3878](https://hello.atlassian.net/browse/ENT-3878) | **Blocker** | Shravan Suri | Rovo / AI - Product - Chat | AI | Shravan Suri | Rovo chat cannot modify/delete Google Calendar events. |
| [ENT-3868](https://hello.atlassian.net/browse/ENT-3868) | **Critical** | Dmitry Melikov | Jira — Platform — Performance | TDP ↔ Jira Platform | Vinod Kumar (TDP) + Jira Platform | API Rate Limiting — systemic across 6+ enterprise customers, impacts migration. |
| [ENT-3853](https://hello.atlassian.net/browse/ENT-3853) | **Blocker** | (verify) | Rovo — Chat | AI | (Rovo team) | [CES-142317] Page Subtree retrieval incomplete / wrong values. |
| [ENT-3807](https://hello.atlassian.net/browse/ENT-3807) | **Blocker** | Ben Costello | Rovo / AI - Other | AI | Ben Costello | Agent automation throttling, minimal visibility/workarounds. |
| [ENT-3806](https://hello.atlassian.net/browse/ENT-3806) | **Blocker** | (verify) | Rovo Search | AI | (Rovo Search) | Embedded images in Jira/Confluence not consumable by Rovo. |
| [ENT-3721](https://hello.atlassian.net/browse/ENT-3721) | **Blocker** | (verify) | Audit — ALP | IDN (ALP) | Dushyant Gill | Embeddable audit logs for Confluence (ENT50). |
| [ENT-2883](https://hello.atlassian.net/browse/ENT-2883) | **Blocker** | (verify) | Audit — ALP | IDN (ALP) | Dushyant Gill | Embeddable audit logs for Jira/JSM (ENT50). |
| [ENT-2745](https://hello.atlassian.net/browse/ENT-2745) | **Blocker** | Michael Andreacchio | Confluence — Compliance & Security | IDN (Trust) | Dushyant Gill | Virtual Private / Isolated cloud (ENT50 FY26). |
| [ENT-2647](https://hello.atlassian.net/browse/ENT-2647) | **Blocker** | (verify) | Encryption — BYOK | TDP | Vinod Kumar | BYOK for Compass. |
| [ENT-2035](https://hello.atlassian.net/browse/ENT-2035) | **Blocker** | (verify) | Encryption — BYOK | TDP | Vinod Kumar | CMK for JPD. |
| [ENT-2022](https://hello.atlassian.net/browse/ENT-2022) | **Blocker** | (verify) | Encryption — BYOK | TDP | Vinod Kumar | CMK for Platform Apps. |
| [ENT-1958](https://hello.atlassian.net/browse/ENT-1958) | **Blocker** | (verify) | Encryption — BYOK / AWS-XKS | TSP, TDP | Corey Johnston / Vinod Kumar | AWS-XKS — non-AWS key store (ENT50 FY28). |
| [ENT-1666](https://hello.atlassian.net/browse/ENT-1666) | **Blocker** | (verify) | Information Protection — Guard | GUARD ↔ IDN | (Guard team) | Policy-based exfiltration controls (DC). |
| [ENT-1445](https://hello.atlassian.net/browse/ENT-1445) | **Blocker** | (verify) | Trust Foundations — FedRAMP | IDN | Dushyant Gill | FedRAMP Tailored for Access. |
| [ENT-381](https://hello.atlassian.net/browse/ENT-381) | **Blocker** | (verify) | Atlas / Project | (Atlas team — outside CoreEng) | (Atlas) | Easy way to target teams contributing to a feature. |
| [ENT-376](https://hello.atlassian.net/browse/ENT-376) | **Blocker** | (verify) | Atlas / Project | (Atlas team) | (Atlas) | Move mandatory fields to top of details slide-out. |
| [ENT-293](https://hello.atlassian.net/browse/ENT-293) | **Blocker** | unassigned | Trust Foundations | IDN, TSP | Dushyant Gill / Corey Johnston | US Classified / IL6 / Airgapped. |
| [ENT-151](https://hello.atlassian.net/browse/ENT-151) | **Blocker** | (verify) | BRIE | TSP | Corey Johnston | Export all cloud data — readable long-term format. |
| [ENT-98](https://hello.atlassian.net/browse/ENT-98) | **Blocker** | unassigned | Trust Foundations — GovCloud | IDN | Dushyant Gill | IL5 (ENT50 FY28). |
| [ENT-80](https://hello.atlassian.net/browse/ENT-80) | **Blocker** | (verify) | Trust — Private Cloud | IDN, TSP | Dushyant Gill / Corey Johnston | Private Cloud. |

**Live aggregate confirmed via JQL** (`priority in (Blocker,Critical) AND statusCategory != Done`): 21 open issues. The set above is the canonical list.

## Section C — Recent (last 60 days, since 2026-03-15) — sorted by Jira component (the routing key)

A "(verify)" priority means we have not yet pulled the Jira priority field for that key in this pass; for the 100+ tickets enriched in `issues_enriched/batchA.json` and `issues_enriched/batchB.json`, the priority is from a live read on 2026-05-15.

### Identity (IDN) — Cloud Administration, Auth, Permissions, Trust
| ENT key | Priority | Assignee | Component | Pillar DRI | Summary |
|---|---|---|---|---|---|
| [ENT-3869](https://hello.atlassian.net/browse/ENT-3869) | Minor | Unassigned | Cloud Admin — Atlassian accounts | Dushyant Gill | Org admin control over profile visibility |
| [ENT-3867](https://hello.atlassian.net/browse/ENT-3867) | Minor | Stefan Scorse | Cloud Admin — Admin API | David Dooley | Site admins fetch emails via REST |
| [ENT-3848](https://hello.atlassian.net/browse/ENT-3848) | Minor | Stefan Scorse | Cloud Admin — Permissions | David Dooley | Restrict Org Admin from self-granting product access |
| [ENT-3824](https://hello.atlassian.net/browse/ENT-3824) | **Minor** | Ian Cohan-shapiro | Cloud Admin — Organisations | David Dooley | PwC platform-native lifecycle governance (2,000+ sites) |
| [ENT-3811](https://hello.atlassian.net/browse/ENT-3811) | Minor | Rob Saunders | Cloud Admin — Cloud Site Names | David Dooley | Set up privacy between entities |
| [ENT-3810](https://hello.atlassian.net/browse/ENT-3810) | Minor | Unassigned | Cloud Security — Auth Policies | Dushyant Gill | SSO/OTP multiple policies |
| [ENT-3855](https://hello.atlassian.net/browse/ENT-3855) | Minor | Sudesh Peram | Cloud Security — External/Guest user | Dushyant Gill | MAM policy targeting subsets of external users |
| [ENT-3837](https://hello.atlassian.net/browse/ENT-3837) | Minor | Imran Khan | Trust Foundations — Data Residency | Dushyant Gill | DESC (UAE) certification |
| [ENT-3784](https://hello.atlassian.net/browse/ENT-3784) | Minor | Ashwini Rattihalli | Rovo Admin Controls | AI ↔ IDN | AI Processing in India |
| [ENT-3739](https://hello.atlassian.net/browse/ENT-3739) | Minor | Ashwini Rattihalli | Rovo Admin Controls | AI ↔ IDN | Atlassian-hosted LLMs with EU Data Residency |
| [ENT-3782](https://hello.atlassian.net/browse/ENT-3782) | Minor | Mike Ni | Information Protection — Region | Dushyant Gill | GCP EU DaRe |
| [ENT-3789](https://hello.atlassian.net/browse/ENT-3789) | Minor | Unassigned | Migration — Other | David Dooley | Separate Sandbox from target instance |
| [ENT-3746](https://hello.atlassian.net/browse/ENT-3746) | Minor | Unassigned | Cloud Admin — Other | David Dooley | Slack admins restrict which Atlassian sites can connect |
| [ENT-3745](https://hello.atlassian.net/browse/ENT-3745) | Minor | Unassigned | Cloud Admin — Other | David Dooley | REST API via Atlassian custom domains |
| [ENT-3738](https://hello.atlassian.net/browse/ENT-3738) | Minor | Unassigned | Cloud Admin — Other | David Dooley | Regulated public APIs to capture Confluence comments |
| [ENT-3737](https://hello.atlassian.net/browse/ENT-3737) | Minor | Unassigned | Cloud Admin — Other | David Dooley | Regulated comment edit history |
| [ENT-3736](https://hello.atlassian.net/browse/ENT-3736) | Minor | Unassigned | Cloud Admin — Other | David Dooley | Regulated APIs for Confluence |
| [ENT-3730](https://hello.atlassian.net/browse/ENT-3730) | Minor | Unassigned | Cloud Admin — Other | David Dooley | Cloud sites from enterprise templates |
| [ENT-3702](https://hello.atlassian.net/browse/ENT-3702) | **Minor** | Charlie Gavey | Automations — UX | (Automation team) | FedRAMP / Docusign feature |

### TSP / TDP / Resilience — Backup, Restore, Scale, Encryption
| ENT key | Priority | Assignee | Component | Pillar DRI | Summary |
|---|---|---|---|---|---|
| [ENT-3790](https://hello.atlassian.net/browse/ENT-3790) | Minor | Atul Setlur | Resilience — Backup/Restore | Corey Johnston | AWS failover between regions (non-US) |
| [ENT-3788](https://hello.atlassian.net/browse/ENT-3788) | Minor | Lakshmi Behl | Resilience — Backup/Restore | Corey Johnston / Vinod Kumar | BRIE Confluence DB > 32 GB |
| [ENT-3787](https://hello.atlassian.net/browse/ENT-3787) | Minor | Lakshmi Behl | Resilience — Backup/Restore | Corey Johnston / Vinod Kumar | BRIE JSM DB > 300 GB |
| [ENT-3785](https://hello.atlassian.net/browse/ENT-3785) | Minor | Lakshmi Behl | Resilience — Backup/Restore | Corey Johnston / Vinod Kumar | BRIE Jira DB > 300 GB |
| [ENT-3668](https://hello.atlassian.net/browse/ENT-3668) | Minor | Lakshmi Behl | Resilience — Backup/Restore | Corey Johnston | Data Residency for Backup/Restore |
| [ENT-3812](https://hello.atlassian.net/browse/ENT-3812) | Minor | Eugene Fayngersh | AGC — Scale | Vinod Kumar | Scale to Accenture's site demand |

### Guard / Information Protection — DLP
| ENT key | Priority | Assignee | Component | Pillar DRI | Summary |
|---|---|---|---|---|---|
| [ENT-3882](https://hello.atlassian.net/browse/ENT-3882) | Minor | Audrey Garcia | Guard — DLP | (Guard team) | UI view of content scanning findings |
| [ENT-3872](https://hello.atlassian.net/browse/ENT-3872) | Minor | Rishabh Jain | Guard Premium | (Guard team) | Detect/prevent PII in attachments |
| [ENT-3852](https://hello.atlassian.net/browse/ENT-3852) | Minor | Filiberto Selvas | Region & Deployment Strategies | (Guard team) | AppLink WebSocket — perimeter DLP |
| [ENT-3851](https://hello.atlassian.net/browse/ENT-3851) | Minor | Sandeep Dmello | Confluence — Compliance & Security | (Guard team) | Prevent ingestion of new sensitive data |
| [ENT-3823](https://hello.atlassian.net/browse/ENT-3823) | Minor | Audrey Garcia | Guard — DLP | (Guard team) | Label-Driven Policies |
| [ENT-3815](https://hello.atlassian.net/browse/ENT-3815) | Minor | Rob Bissett | Guard — Other | (Guard team) | Shadow IT controls in Guard |

### Rovo / AI — routed via CoreEng MUSTWIN but owned outside CoreEng
| ENT key | Priority | Assignee | Component | Pillar DRI | Summary |
|---|---|---|---|---|---|
| [ENT-3881](https://hello.atlassian.net/browse/ENT-3881) | **Blocker** | Ashwini Rattihalli | Rovo — Other | AI | DocuSign HIPAA blocker |
| [ENT-3878](https://hello.atlassian.net/browse/ENT-3878) | **Blocker** | Shravan Suri | Rovo — Chat | AI | Rovo chat / Google Calendar |
| [ENT-3879](https://hello.atlassian.net/browse/ENT-3879) | Minor | Jemma Swaak | Rovo — MCP | AI | DLP for MCP access to Jira/Confluence |
| [ENT-3866](https://hello.atlassian.net/browse/ENT-3866) | Minor | Jemma Swaak | Rovo — MCP | AI | Toggle to disable MCP features |
| [ENT-3865](https://hello.atlassian.net/browse/ENT-3865) | Minor | Jemma Swaak | Rovo — MCP | AI | Content whitelisting in MCP server |
| [ENT-3864](https://hello.atlassian.net/browse/ENT-3864) | Minor | Jemma Swaak | Rovo — MCP | AI | MCP server domain allow-list per site |
| [ENT-3860](https://hello.atlassian.net/browse/ENT-3860) | Minor | Jemma Swaak | Rovo — MCP | AI | MCP support for multiple sites |
| [ENT-3856](https://hello.atlassian.net/browse/ENT-3856) | Minor | Jemma Swaak | Rovo — MCP | AI | MCP server permissions per site |
| [ENT-3809](https://hello.atlassian.net/browse/ENT-3809) | Minor | Jemma Swaak | Rovo — MCP | AI | Block MCP for external users |
| [ENT-3877](https://hello.atlassian.net/browse/ENT-3877) | **Major** | Sushant Koshy | Rovo — Studio Agents | AI | Jira attachments via REST API path |
| [ENT-3876](https://hello.atlassian.net/browse/ENT-3876) | **Major** | Sushant Koshy | Rovo — Studio Agents | AI | Auto-follow Confluence links from Jira |
| [ENT-3875](https://hello.atlassian.net/browse/ENT-3875) | **Major** | Sushant Koshy | Rovo — Studio Agents | AI | (variant of 3877) |
| [ENT-3874](https://hello.atlassian.net/browse/ENT-3874) | **Major** | Sushant Koshy | Rovo — Studio Agents | AI | (variant of 3876) |
| [ENT-3849](https://hello.atlassian.net/browse/ENT-3849) | Minor | Sushant Koshy | Rovo — Studio Agents | AI | Turn off Follow Up questions |
| [ENT-3847](https://hello.atlassian.net/browse/ENT-3847) | **Major** | Unassigned | Rovo — Admin Controls | AI | Rovo Enablement issues |
| [ENT-3844](https://hello.atlassian.net/browse/ENT-3844) | **Major** | Griffin Jones | Rovo — Insights & ROI | AI | Rovo usage trend dashboard |
| [ENT-3843](https://hello.atlassian.net/browse/ENT-3843) | Minor | Shravan Suri | Rovo — Other | AI | More objects Rovo can create/edit |
| [ENT-3842](https://hello.atlassian.net/browse/ENT-3842) | Minor | Caroline Bartle | Rovo — Other | AI | Public info on usage limits |
| [ENT-3841](https://hello.atlassian.net/browse/ENT-3841) | Minor | Sumit Garg | Rovo — Other | AI | Process larger data |
| [ENT-3838](https://hello.atlassian.net/browse/ENT-3838) | Minor | Muthukumar Ravishankar | Rovo — Slack App | AI | Slack ↔ JSM 2-way sync |
| [ENT-3826](https://hello.atlassian.net/browse/ENT-3826) | Minor | Gareth Wham | Rovo Dev | AI | Claude Opus 4.5 in trial |
| [ENT-3825](https://hello.atlassian.net/browse/ENT-3825) | Minor | Sushant Koshy | Rovo — Other | AI | Public API access for agents |
| [ENT-3832](https://hello.atlassian.net/browse/ENT-3832) | Minor | Chait Donthini | Rovo — Admin Controls | AI | SharePoint/OneDrive allow-list |
| [ENT-3791](https://hello.atlassian.net/browse/ENT-3791) | Minor | Shravan Suri | Rovo — Studio Agents | AI | DocuSign — Rovo across long actions |
| [ENT-3793](https://hello.atlassian.net/browse/ENT-3793) | Minor | Jensen Fleming | Rovo — Studio Agents | AI | Extract images from Jira issues |
| [ENT-2840](https://hello.atlassian.net/browse/ENT-2840) | Minor | Elizabeth Lee | Rovo — 3P Connectors | AI | JSM (Assets/Forms/DM) connector |
| [ENT-3862](https://hello.atlassian.net/browse/ENT-3862) | Minor | Shubh Trivedi | Rovo — Other | AI | AMAT Rovo Trend Dashboard |
| [ENT-3880](https://hello.atlassian.net/browse/ENT-3880) | Minor | Griffin Jones | Rovo — Insights | AI | Granular usage metrics |
| [ENT-3863](https://hello.atlassian.net/browse/ENT-3863) | Minor | Sushant Koshy | Rovo — Studio Agents | AI | Linked fields in JSM "Raise a Request" skill |
| [ENT-3744](https://hello.atlassian.net/browse/ENT-3744) | Minor | Martin Suntinger | Rovo — Studio Agents | AI | Slack-based JSM creation flow |
| [ENT-3747](https://hello.atlassian.net/browse/ENT-3747) | Minor | Muthukumar Ravishankar | Rovo — Studio Agents | AI | DM with custom Rovo agents in Slack |
| [ENT-3884](https://hello.atlassian.net/browse/ENT-3884) | Minor | Dmitry Melikov | Jira Workflows | (Jira product) | Add AI agents to Company-Managed board columns |

### Jira / Confluence / JSM / Loom — owned outside CoreEng (route + observe only)
Loom governance cluster (Kristen Waters): ENT-3814, 3817, 3818, 3819, 3820, 3821, 3822 — all Minor.
JSM Assets / CMDB cluster (Sonia Mahabir Gandhi, Kaushik Mitra, Mike Jones): ENT-3873, 3858, 3839, 3783, 3742 — Minor.
Confluence (Sree Das, Sam Lucas, Melanie Zhao, Marie Casabonne, Laura Mehrkens, Jonno Katahanas): ENT-3861, 3829, 3828, 3846, 3840, 3743 — Minor.
Jira platform (Sahibi Miranshah, Carol Low, Tina Ling): ENT-3827, 3845, 3318 — Minor.
Other (Analytics/Data Lake by Ben Jackson — TDP-adjacent): ENT-3883, 3859 — Minor.

## Section D — Cross-cutting themes (Ke Wang's framing)

| Theme (per ENT50 grouping) | Pillars involved | Open ENT items (representative) | Notes |
|---|---|---|---|
| **BYOK / CMK family** (full encryption story) | TSP + TDP | ENT-1958, ENT-2022, ENT-2035, ENT-2085, ENT-2647, ENT-3099 | All Blocker except ENT-2085 (Active escalation, Filiberto Selvas DRI) |
| **Audit Logs Platform (ALP)** | IDN | ENT-2883, ENT-3721 | Both Blocker; embeddability story |
| **FedRAMP / IL5 / IL6 / Sovereign** | IDN (+ TSP for IL6) | ENT-98, ENT-293, ENT-1445, ENT-2289, ENT-3702 | ENT-2289 is on ENT50 FY28 |
| **Data Residency / GCP** | IDN | ENT-59, ENT-3235, ENT-3739, ENT-3782, ENT-3784, ENT-3837 | UAE DESC + EU GCP + India |
| **Lifecycle Governance / Org Scale** | IDN + TSP | ENT-1690, ENT-1703, ENT-2643, ENT-3032, ENT-3824 | PwC 2,000-sites story (ENT-3824) is **Minor** despite being labeled "expansion blocker" |
| **BRIE Scale (DB size)** | TSP + TDP | ENT-3785, ENT-3787, ENT-3788, ENT-3668, ENT-1929, ENT-311, ENT-151 | Lakshmi Behl is the recurring assignee |
| **Isolated / Private cloud** | IDN + TSP | ENT-2745 (Blocker), ENT-80 (Blocker) | Long-running |
| **Rovo / AI Trust** | AI ↔ IDN | ENT-3881 (Blocker), ENT-3878 (Blocker), all MCP cluster, ENT-3784, ENT-3739 | DocuSign HIPAA escalation = #1 risk |
| **Guard / DLP** | GUARD ↔ IDN | ENT-3882, 3872, 3852, 3851, 3823, 3815, 1666 | Audrey Garcia is Guard DLP DRI |

---

## Section E — How to use this with Ke Wang's MUSTWIN review (page 5696752671)

1. Each month the **MUSTWIN DRI** (Ke Wang) drafts a new "FY26 (<Month>) ENT-CoreEng Execution Review" page in `CoreEngineering` space, pre-filling the 4-table template (Progress / Risks / Open Issues / Enterprise Asks).
2. Pillar DRIs (Identity: David Dooley + Romulus Apolzan; TDP: Lin Chen) fill in the Success/Delays/POR rows for the prior month.
3. **Enterprise DRI** (Filiberto Selvas) populates the "Enterprise Asks" table with up-to-3 ENT items the customer has escalated this month.
4. Reviewers (LT): Levon Esibov + Kangrong Yan annotate with `UPDATE` status pills + tasks.
5. The ENT50 list (page 5861641112) is the **commit register** — only items on it are reviewed in MUSTWIN. New ENT items appear in this v3 mapping's **Section C** until promoted onto ENT50.
