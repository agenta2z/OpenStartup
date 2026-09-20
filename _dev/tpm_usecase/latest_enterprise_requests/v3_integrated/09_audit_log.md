# 09 · Audit Log — corrections vs prior `latest_enterprise_requests/` docs

> Generated 2026-05-15. Each correction below is backed by a live data source captured this session. The file lists which prior content was kept (deduplicated and integrated), which was corrected, and which was discarded as outdated or wrong.

## A · Org-structure errors (the biggest fix)

| # | Prior claim (file) | Live truth (verified 2026-05-15) | Source |
|---|---|---|---|
| A1 | "EVP Engineering: Levon Esibov" (in flat files `00_*`, `01_*`, `05_master_coreng_mapping.md`) | Levon Esibov is **Head of TPgM** — TPM line, not engineering | `scripts/twg org-tree --email lesibov@atlassian.com --include-profile-title` |
| A2 | "VP Core Engineering: Ashish Consul" | Ashish Consul is **Head of TPM, CoreEng** — TPM line, not engineering VP | Same `org-tree` pull |
| A3 | Mapped enterprise requests onto Levon's org (which is the TPM org) | Real engineering pillar DRIs come from page **7012411386** | Confluence page 7012411386 (Ke Wang's May 2026 review) |
| A4 | Ke Wang depicted as engineering pillar owner (e.g., "FinOps owner: Ke Wang" in `corrected_master_mapping.md`) | Ke Wang is the **MUSTWIN DRI (TPM)**; FinOps DRI is **Tom Cutajar** | Confluence pages 5696752671 + onboarding hub 6258849065 |
| A5 | Missing Enterprise DRI (customer voice) | **Filiberto Selvas** is the Enterprise DRI | Pages 5696752671 + 7012411386 |

## B · Pillar-owner mislabels in `corrected_master_mapping.md`

The prior `corrected_master_mapping.md` introduced 9 named pillar owners. Six of those nine are **not the verified pillar owner per Ke Wang's May 2026 page**.

| Pillar (per `corrected_master_mapping.md`) | Owner per old doc | Owner per page 7012411386 (verified) | Correct contextual role of the old name |
|---|---|---|---|
| Identity & IAM | Prashant Ghosal | Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan | Prashant is a Reliability co-lead per FY25Q1 reference, not Identity owner |
| BRIE | Lakshmi Behl | (rolls under TSP — Corey Johnston) | Lakshmi is the recurring **assignee** on BRIE-family tickets |
| TSP / Sandbox | Harpreet Singh Juneja / Sirisha Pendem | Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles | Harpreet IS verified TSP DRI; Sirisha is a sandbox engineering lead historically |
| Encryption / BYOK | Greg Zaney (Coral team) | (rolls under TDP — Vinod Kumar) | Greg / Coral were a historical brand for the BYOK team; current line is TDP |
| ALP | Akshay Nambiar | (rolls under Identity — Dushyant Gill) | Akshay may have been ALP eng manager in earlier era |
| Compliance / RegInd | Wayne Yim | (rolls under Identity — Dushyant Gill) | Wayne may have been the compliance program manager historically |
| Scale / CRSP | "CRSP Team" | (covered by Identity scale + TDP) | CRSP was a sub-program; not a current named pillar |
| FinOps | Ke Wang | Tom Cutajar (Org HoE) | Ke Wang is MUSTWIN DRI, **not** FinOps owner |
| Eng Excellence | TBD | (FY25 lead Jason Yang; FY26 not re-verified) | Status unchanged |

## C · ENT ticket priority mislabels (every claim re-checked live)

For each of the following, prior local docs labelled the ticket "P0", "P1", "Critical", or "blocker"; Jira's `priority` field on 2026-05-15 says otherwise.

| Key | Prior claim | Live priority (2026-05-15) | Live assignee |
|---|---|---|---|
| ENT-3824 | "P0 / Critical / blocker" (PwC expansion blocker) | **Minor** | Ian Cohan-shapiro |
| ENT-2289 (FedRAMP High) | "P0" | **Minor** | Irene Milyuk |
| ENT-3702 (FedRAMP / Docusign) | "P1" | **Minor** | Charlie Gavey |
| ENT-3737 / 3738 / 3736 (Wells-Fargo regulated) | "P1" | **Minor**, all unassigned | (unassigned) |
| ENT-1690 (org-level data per site) | "P1" | **Minor** | Rob Saunders |
| ENT-3851 (Prevent ingestion of new sensitive data) | "P0/P1" | **Minor** | Sandeep Dmello |
| ENT-3823 (Label-Driven Policies) | "P1" | **Minor** | Audrey Garcia |
| ENT-3856 / ENT-3860 / ENT-3864 / ENT-3865 / ENT-3866 / ENT-3879 / ENT-3809 (MCP family) | mostly "P1/P2" | All **Minor** | Jemma Swaak |
| ENT-3837 (DESC UAE certification) | "P1" | **Minor** | Imran Khan |
| ENT-3833 / 3834 / 3836 (referenced as P0/P1) | — | **ENT-3833** (NATO D32) **Minor**; ENT-3834 / 3836 — only verifiable via search; not in the open Blocker / Critical set | n/a |

**Source:** `mcp__atlassian__get_jira_issue` with `extra_fields=["assignee","priority","components","labels","reporter","duedate","fixVersions","parent"]`. Raw outputs in `data/batchA.json` and `data/batchB.json`.

## D · Aggregate-count claims rechecked

| Prior claim | Live truth (2026-05-15) |
|---|---|
| "152 ENT tickets total" (in `00_SUMMARY_README.md`, `05_master_coreng_mapping.md`) | The TWG `jira workitem search` aggregate `project = ENT` returns an anomalous totalCount (likely a quoted-JQL parsing artefact). **Reliable subsets**: open `priority in (Blocker, Critical) AND statusCategory != Done` returns **21**; the ENT50 commit list on page 5861641112 contains **25 named items** (FY26 + FY27 + FY28). |
| "107 ENT tickets — Security/Compliance/Identity cluster" (`README.md`, `01_security_compliance_identity_requests.md`) | Number was a Feb 1 → May 1 2026 snapshot; valid for that window. Today (May 15), the directly-fetched recent set is **46 items in the last 60 days** (since 2026-03-15). |
| "210 tickets across Scale/Integration/Rovo/Backup/Notifications" (`02_scale_integration_rovo_ai_requests.md`) | Self-contradictory (the doc also said 85 unique). Heavy multi-tagging across categories. We do not carry this 210 number forward. |
| "93 tickets in Governance/Admin/Data" (`03_governance_admin_data_requests.md`) | Window-snapshot from 2026-05-01. Still useful for cluster-narrative; superseded by per-ticket data in `data/batchA.md` + `data/batchB.md`. |

## E · Mapping errors (where prior docs sent a ticket to the wrong pillar)

| Ticket | Prior pillar | Correct pillar | Why |
|---|---|---|---|
| ENT-3824 (PwC lifecycle) | "TSP / Tenant Platform" | **Identity → David Dooley** | Jira component is `Cloud Administration - Organisations`, owned by Identity (org / site model) |
| ENT-3811 (privacy between entities) | "TSP" | **Identity → David Dooley** | Component `Cloud Admin - Cloud Site Names` |
| ENT-3851 (sensitive data ingestion) | "TDP" | **Guard / Information Protection** | Component `Confluence — Compliance & Security`, but the implementation path is Guard DLP |
| ENT-2085 (CMK retroactive) | "Encryption team (orphan)" | **TSP — Corey Johnston** with TDP follow-up | Per page 7012411386 *Enterprise Asks* row 1: Filiberto Selvas DRI, Alex Grach + Michael Wilde follow-up |
| BRIE family (ENT-3785, 3787, 3788, 3668, 1929) | "Resilience" alone | **TSP + TDP** (joint) | Lakshmi Behl is assignee but work splits across both |
| ALP family (ENT-2883, ENT-3721) | "Audit team (orphan)" | **Identity (ALP)** | ALP rolls under Identity per Ke Wang's mapping |

## F · What was kept vs discarded from prior content

### Kept (and integrated)
* The **107-ticket Security/Compliance breakdown** — preserved as historical aggregate in [`02_demand_overview.md`](02_demand_overview.md) §5
* The **75-page Confluence VoC catalog** — preserved in [`06_voc_sources.md`](06_voc_sources.md)
* The **8 New Project Candidates** from `corrected_master_mapping.md` §3 — re-verified and preserved in [`07_new_project_candidates.md`](07_new_project_candidates.md)
* The **MUSTWIN review framing and the cross-cutting themes** — preserved in [`03_master_mapping.md`](03_master_mapping.md) §D and [`08_mustwin_template.md`](08_mustwin_template.md)
* The **status-bucket distribution** (Pending Review / Roadmap / Actively Investigating) — preserved in [`02_demand_overview.md`](02_demand_overview.md) §5

### Discarded as wrong / outdated
* The "EVP Engineering: Levon Esibov" claim and all dependent narrative
* The "152 total ENT tickets" headline number
* The "210 / 50 / 50 / 50 / 30 / 30" overlapping bucket claims in `02_scale_integration_rovo_ai_requests.md`
* The 9 mis-named pillar owners in `corrected_master_mapping.md`
* All "P0 / P1" severity labels not backed by a live `priority` field
* The redundant `corrected_*` files (the "corrected" prefix was misleading because they encoded the same Levon-EVP error and bogus-P0 labels)

### Files in the parent `latest_enterprise_requests/` folder considered superseded by `v3_integrated/`

The following files in the **parent** folder are kept on disk for historical traceability but should not be consulted as the current mapping:

* `00_SUMMARY_README.md`, `INDEX.md`, `README.md`
* `01_security_compliance_identity_requests.md`
* `02_critical_analysis.md`, `02_scale_integration_rovo_ai_requests.md`
* `03_governance_admin_data_requests.md`
* `04_confluence_voc_enterprise_context.md`
* `05_master_coreng_mapping.md`
* `06_priority_matrix_new_requests.md`
* `07_NEW_PROJECT_CANDIDATES.md`
* `corrected_master_mapping.md`, `corrected_priority_matrix.md`, `corrected_batch1_details.md`, `corrected_batch2_details.md`, `corrected_legacy_details.md`
* `RESEARCH_COMPLETE.md`, `RESEARCH_COMPLETION_REPORT.txt`
* `LEGACY_RESEARCH_INDEX.md`, `LEGACY_TICKETS_SUMMARY.md`
* `index.html` (built from old data; the new `v3_integrated/index.html` supersedes it)
* `v3_*` flat files (kept for diff context; integrated into this folder)

The current canonical files are: this folder (`v3_integrated/`), entry point [`README.md`](README.md), primary deliverable [`03_master_mapping.md`](03_master_mapping.md).
