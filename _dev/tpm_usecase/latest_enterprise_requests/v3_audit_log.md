# v3 Audit Log — corrections vs prior `latest_enterprise_requests` docs

> Generated 2026-05-15 06:55–07:02 PT. Each correction below is backed by a live data source captured this session.

## A. Org-structure errors (the user-flagged Big One)

| # | Prior claim (file) | Live truth (verified 2026-05-15) | Source |
|---|---|---|---|
| A1 | "EVP Engineering: Levon Esibov" (`00_index.md`, `01_org_structure_leadership.md`, `05_master_coreng_mapping.md`) | Levon Esibov is **Head of TPgM** — TPM line, not engineering | `scripts/twg org-tree --email lesibov@atlassian.com --include-profile-title` |
| A2 | "VP Core Engineering: Ashish Consul" | Ashish Consul is **Head of TPM, CoreEng** — TPM line, not engineering VP | Same org-tree pull; also page 7012411386 lists Ashish in TPM context, not as a pillar engineering DRI |
| A3 | Mapped enterprise requests onto Levon's org tree (which is the TPM org) | Real engineering pillar DRIs are: **Identity** = Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan; **TSP** = Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles; **TDP** = Vinod Kumar, Lin Chen, Alex Grach | Confluence page **7012411386** (Ke Wang's May 2026 review, "Pillar Owners" section) |
| A4 | Ke Wang depicted as a pillar owner / engineering manager | Ke Wang is the **MUSTWIN DRI** (TPM) whose role is exactly what this analysis emulates — mapping ENT demand to engineering pillars | Confluence page **5696752671** ("MUSTWIN DRI: @Ke Wang") |
| A5 | Missing the Enterprise DRI (customer voice) | **Filiberto Selvas** is the Enterprise DRI per pages 5696752671 and 7012411386 | Both pages |

## B. ENT ticket priority mislabels (every claim above re-checked live)

For each of the following, the prior local docs labeled the ticket "P0", "P1", "Critical", or "blocker", but Jira's `priority` field on 2026-05-15 says otherwise.

| Key | Prior claim | Live priority (2026-05-15) | Live assignee |
|---|---|---|---|
| ENT-3824 | "P0 / Critical / blocker" (PwC expansion blocker) | **Minor** | Ian Cohan-shapiro |
| ENT-2289 (FedRAMP High) | "P0" | **Minor** | Irene Milyuk |
| ENT-3702 (FedRAMP / Docusign feature) | "P1" | **Minor** | Charlie Gavey |
| ENT-3737 / 3738 / 3736 (Wells-Fargo regulated) | "P1" | **Minor**, all unassigned | (unassigned) |
| ENT-1690 (org-level data per site) | "P1" | **Minor** (Major was prior typo) | Rob Saunders |
| ENT-3851 (Prevent ingestion of new sensitive data) | "P0/P1" | **Minor** | Sandeep Dmello |
| ENT-3823 (Label-Driven Policies) | "P1" | **Minor** | Audrey Garcia |
| ENT-3856 / ENT-3860 / ENT-3864 / ENT-3865 / ENT-3866 / ENT-3879 / ENT-3809 (MCP family) | mostly "P1/P2" | All **Minor** | Jemma Swaak |
| ENT-3837 (DESC UAE certification) | "P1" | **Minor** | Imran Khan |
| ENT-3833 / 3834 / 3836 (referenced as P0/P1) | — | tickets do not exist or were renumbered (verified gap in 3833-3836 sequence) | n/a |

**Source for all of B:** `mcp__atlassian__get_jira_issue` with `extra_fields=["assignee","priority","components","labels","reporter","duedate","fixVersions","parent"]` against `https://hello.atlassian.net/browse/<KEY>`. Raw outputs in `issues_enriched/batchA.json` and `issues_enriched/batchB.json`.

## C. Aggregate-count claims rechecked

| Prior claim | Live truth (2026-05-15) |
|---|---|
| "152 ENT tickets total" | The TWG `jira workitem search` aggregate `project = ENT` returns an anomalous totalCount (likely a quoted-JQL parsing artefact). **Reliable subsets**: open `priority in (Blocker, Critical) AND statusCategory != Done` returns **21**; the ENT50 commit list on page 5861641112 contains **25 named items** (FY26+FY27+FY28). |
| "Multiple ENT-3833→ENT-3836 P0 issues" | Those keys do not appear in any of the live Jira pulls; they may have been deleted, restricted, or fabricated upstream. |

## D. Mapping errors (where prior docs sent a ticket to the wrong pillar)

| Ticket | Prior pillar | Correct pillar | Why |
|---|---|---|---|
| ENT-3824 (PwC lifecycle) | "TSP / Tenant Platform" | **Identity → David Dooley** | Jira component is `Cloud Administration - Organisations`, owned by Identity (org/site model). David Dooley is the Identity DRI for Cloud Admin. |
| ENT-3811 (privacy between entities) | "TSP" | **Identity → David Dooley** | Component `Cloud Admin - Cloud Site Names`. |
| ENT-3851 (sensitive data ingestion) | "TDP" | **Guard / Information Protection** | Component `Confluence - Compliance & Security`, but the implementation is the Guard DLP path. |
| ENT-2085 (CMK retroactive) | "Encryption team (orphan)" | **TSP — Corey Johnston** with TDP follow-up | Per Ke Wang's May 2026 review (page 7012411386, "Enterprise Asks" row 1): Filiberto Selvas is DRI; Alex Grach + Michael Wilde are followup. |
| BRIE family (ENT-3785, 3787, 3788, 3668, 1929) | "Resilience" alone | **TSP + TDP** (joint) | Lakshmi Behl is the assignee but the work splits across both. |
| ALP family (ENT-2883, ENT-3721) | "Audit team (orphan)" | **Identity (ALP)** | ALP rolls under Identity's audit log platform per Ke Wang's mapping. |

## E. Files in this folder considered SUPERSEDED by v3

The following files are kept for historical traceability but should not be used as the current mapping:

* `00_SUMMARY_README.md`
* `INDEX.md`
* `01_security_compliance_identity_requests.md`
* `02_critical_analysis.md`
* `02_scale_integration_rovo_ai_requests.md`
* `03_governance_admin_data_requests.md`
* `04_confluence_voc_enterprise_context.md`
* `05_master_coreng_mapping.md`
* `06_priority_matrix_new_requests.md`
* `07_NEW_PROJECT_CANDIDATES.md`
* `corrected_master_mapping.md`
* `corrected_priority_matrix.md`
* `corrected_batch1_details.md`, `corrected_batch2_details.md`, `corrected_legacy_details.md`
* `RESEARCH_COMPLETE.md`, `RESEARCH_COMPLETION_REPORT.txt`
* `LEGACY_RESEARCH_INDEX.md`, `LEGACY_TICKETS_SUMMARY.md`

The current canonical files are: **`v3_FINAL_README.md`**, **`v3_coreng_org_map.md`**, **`v3_master_mapping.md`**, **`v3_open_blocker_critical.md`**, **`v3_recent_60d_inbox.md`**, **`v3_audit_log.md`**, **`v3_mustwin_review_template.md`**.
