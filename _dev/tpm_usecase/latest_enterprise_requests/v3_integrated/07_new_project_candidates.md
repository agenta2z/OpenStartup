# 07 · New Project Candidates
*(carried forward from prior `corrected_master_mapping.md` §3, re-checked 2026-05-15)*

> These are clusters where customer demand is large enough or coherent enough to warrant a **named CoreEng project** but where current pillar coverage is fragmented or absent. Each candidate is supported by a verified ENT cluster from this analysis.

## How to read this list

Each candidate has:
* **Demand evidence** — the verified ENT items underwriting the case
* **Suggested pillar(s)** — using the verified DRI roster from [`01_organization.md`](01_organization.md)
* **Why now** — the current trigger
* **Open question** — what still needs MUSTWIN-level decision

## 1. Policy Engine / Label-Driven Policies

* **Demand evidence:** ENT-3823 (Label-Driven Policies), ENT-3815 (Shadow IT controls in Guard), ENT-1666 (policy-based exfiltration controls — Blocker), ENT-3851 (prevent ingestion of new sensitive data), ENT-3852 (AppLink WebSocket DLP), ENT-3855 (MAM policy for external user subsets)
* **Suggested pillar(s):** Atlassian Guard (out-of-CoreEng) ↔ Identity (Trust scope, Dushyant Gill) — joint platform initiative
* **Why now:** A 6-ticket cluster with heterogeneous components but one common ask: a **policy engine** that can apply consistent rules across content classification, network egress, and external-user scoping. Today these are individual product features.
* **Open question:** Should this live in Guard (which already owns DLP) or in a new joint platform? Needs a director-level decision.

## 2. Service Account Management at Scale

* **Demand evidence:** ENT-3709 (restrict API token creation for Bitbucket), ENT-3745 (REST API via custom domains), ENT-3867 (site admins fetch emails via REST), ENT-3725 (direct chat links for Rovo agents), ENT-3825 (public API access for agents)
* **Suggested pillar:** Identity → David Dooley
* **Why now:** Multiple admin-API and service-account control items are accumulating; today there is no single product surface for "manage service accounts at enterprise scale".
* **Open question:** Whether to fold this into the existing Cloud Admin Admin-API roadmap or carve it out as a named project.

## 3. MCP Server Platform — Enterprise Controls

* **Demand evidence:** ENT-3856, 3860, 3864, 3865, 3866, 3879, 3809 (the 8-ticket MCP family — all Minor priority but coherent), ENT-3727 (block external MCP — Accenture)
* **Suggested pillar:** Rovo / AI Platform (out-of-CoreEng) ↔ Identity (admin scope)
* **Why now:** MCP is a **new control surface** introduced in the last quarter. All 8 customer-facing asks are about adding enterprise governance (multi-site, allow-list, per-site permissions, external-user scoping). All are routed to a single assignee (Jemma Swaak) — pointing to a candidate platform initiative rather than 8 separate features.
* **Open question:** Whether MCP governance should ride on Identity's existing admin model or be a Rovo-platform first-class concept.

## 4. Platform-Native Lifecycle Governance (PwC blocker)

* **Demand evidence:** ENT-3824 (PwC, 2,000+ sites — *Minor priority despite the customer narrative*), ENT-3730 (cloud sites from enterprise templates), ENT-1703 (site limit 150 → 2,000 — Major)
* **Suggested pillar:** Identity → David Dooley + TSP → Corey Johnston (joint org-and-site model)
* **Why now:** The "Lifecycle Governance" theme has only one named customer story (PwC) but it is the **single largest enterprise expansion blocker** in the inbox per CSM narrative. Because Jira's priority field shows Minor, this is exactly the kind of item that needs MUSTWIN-level disambiguation between "field priority" and "customer-revenue priority".
* **Open question:** Re-prioritise to Major / Critical in Jira to match the CSM narrative? Or keep field priority Minor and track the customer-revenue narrative separately?

## 5. New Compliance Certifications FY26

* **Demand evidence:** ENT-3837 (DESC UAE), ENT-3833 (NATO D32), ENT-3672 (Spanish ENS), ENT-3740 (HIPAA in AGC), ENT-2289 (FedRAMP High — ENT50 FY28), ENT-1445 (FedRAMP Tailored — Blocker), ENT-98 (IL5 — Blocker)
* **Suggested pillar:** Identity → Dushyant Gill (FedRAMP / GovCloud) + Compliance program management
* **Why now:** The **5 sovereign-region** asks (UAE, NATO, Spain, India, EU) plus the **3 US-government tiers** (FedRAMP Tailored, FedRAMP High, IL5) form a coherent multi-year programme that is currently fragmented across individual ENT items.
* **Open question:** Whether to consolidate into a single MUSTWIN "Sovereign Cloud" programme row or keep them as separate ENT50 items.

## 6. BRIE Phase 2 — Exit & Sovereignty

* **Demand evidence:** ENT-3785, 3787, 3788 (BRIE DB scale — Jira / Confluence / JSM), ENT-3668 (Data Residency for Backup), ENT-3724 (BRIE for standard licence), ENT-3717, 3726 (backup retention > 30 days), ENT-3836 (on-prem backup for emergency / exit), ENT-151 (export "readable format" — Blocker), ENT-1929 (full backups w/ attachments > 3 TB)
* **Suggested pillar:** TSP → Corey Johnston + TDP → Vinod Kumar
* **Why now:** The original BRIE charter (backup / restore / import / export) has accumulated a **second-generation** ask set: longer retention, larger DBs, exit-grade portable formats, and data-residency-aware storage. Lakshmi Behl is the recurring assignee — clear single-team locus.
* **Open question:** Whether to position this as an explicit "BRIE Phase 2" engineering programme tied to the CSM exit-clause narrative.

## 7. AI Data Sovereignty

* **Demand evidence:** ENT-3739 (Atlassian-hosted LLMs with EU residency), ENT-3784 (AI processing in India), ENT-3731 (Analytics / Data Lake residency in Switzerland), ENT-3881 (DocuSign HIPAA — Blocker), ENT-3099 (BYOK scope to AI / Rovo — ENT50 FY26)
* **Suggested pillar:** Rovo / AI Platform (out-of-CoreEng) ↔ TDP (Vinod Kumar) for residency / encryption substrate
* **Why now:** AI demand and data-residency demand are colliding. Customers want region-local AI processing **and** customer-managed encryption keys for AI workloads. The DocuSign HIPAA item escalates this to Blocker level.
* **Open question:** Joint engineering programme between Rovo platform + TDP — needs cross-org sponsorship.

## 8. Private Network Connectivity / Customer-Managed Network

* **Demand evidence:** ENT-3852 (AppLink WebSocket — perimeter DLP), ENT-3682 (separate IP allowlists for user vs API traffic), ENT-3734 (Intune MAM-aware IP allowlist bypass), ENT-3728 (mobile app block per site)
* **Suggested pillar:** Networking → Mathrubootham Janakiraman + Atlassian Guard
* **Why now:** Customers want to **shape the network surface** of the cloud product (allow-lists, MAM-aware exceptions, perimeter DLP). Currently fragmented across product teams.
* **Open question:** Whether the Networking pillar adopts this as a named programme or it stays distributed.

## Status of these candidates vs current ENT50

| Candidate | On ENT50? | If yes, FY slot |
|---|---|---|
| Policy Engine | No (parts of family related) | — |
| Service Account Management | No | — |
| MCP Server Platform | No | — |
| Lifecycle Governance | Partial — ENT-1703 is FY26 | FY26 |
| New Compliance Certifications | Partial — ENT-2289 is FY28 | FY28 (FedRAMP High) |
| BRIE Phase 2 | Partial — ENT-311, 1929, 1958 | FY26 / FY28 |
| AI Data Sovereignty | Partial — ENT-3099 is FY26 | FY26 |
| Private Network Connectivity | No | — |

> Five of these eight candidates are **not on the current ENT50** — they are bottom-up signals from the inbox that may warrant promotion in the next quarterly review.
