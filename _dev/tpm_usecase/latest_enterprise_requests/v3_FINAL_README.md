# Enterprise → Core Engineering Mapping — v3 (FINAL, verified 2026-05-15)

**Author of this refresh:** Tony Chen (TPM-style mapping pass)
**Verification timestamp:** 2026-05-15 06:55 PT
**Sources of truth used:**
1. Live Jira (`hello.atlassian.net`, project `ENT`) via `mcp__atlassian__get_jira_issue` (`extra_fields=[priority, assignee, components, labels]`)
2. Confluence canonical pages owned by **Ke Wang (kwang4@atlassian.com)** in space `CoreEngineering`:
   * **page 7012411386** — *FY26 (May) ENT-CoreEng Execution Review* (created 2026-05-11)
   * **page 5861641112** — *FY26 ENT50 List - CoreEng* (the canonical "what CoreEng committed to" list)
   * **page 5696752671** — *FY26 Enterprise MUSTWIN Monthly Review Template* (the canonical reporting format)
   * **page 5319794175** — *MUSTWIN CoreEng FY26 Enterprise Plan* (deliverables & staffing)
   * **page 5619065001** — *High-Touch Roadmap → ENT50 Source of Truth* (in space `TRUSTED`)
3. CoreEng pillar onboarding hubs in space `CoreEngineering` (Tenant Platform, Networking, Reliability, CDP, Deployment Verification, CloudSec, FinOps, Identity)
4. Live Jira aggregate via `scripts/twg jira workitem search` (totals + open Blocker/Critical list)

---

## Why this is "v3 FINAL" (and what was wrong before)

The previous artifacts in this folder (`05_master_coreng_mapping.md`, `corrected_master_mapping.md`, `06_priority_matrix_new_requests.md`, etc.) contained **significant factual errors**. Two critical ones called out by the user have been corrected here:

### Correction #1 — Scope of "Core Engineering"
| Claim in prior docs | Reality (verified 2026-05-15) |
|---|---|
| "EVP Engineering: Levon Esibov" | Levon Esibov is **Head of TPM / Program Management** (not Engineering). Source: org-tree `lesibov@atlassian.com` shows job title "Head of TPgM"; reports up Ananth Sundararaj → Taroon Mandhana. |
| "VP Core Engineering: Ashish Consul" | Ashish Consul is **Head of TPM, CoreEng** (a TPM line-manager under Levon), **not** the engineering VP. Source: org-tree + page 7012411386 (Ashish does not appear as an engineering pillar lead). |
| Mapped enterprise requests onto "Levon's org" | Levon's org **is the TPM org**, not the engineering supply org. **Real engineering pillar leads** for the ENT50 are listed below. |
| Treated Ke Wang's org as the engineering org | Ke Wang is the **MUSTWIN DRI** (TPM); his job is to **map enterprise demand → real engineering pillars**. This document is now scoped that way. |

### Correction #2 — Priority labels on individual ENT tickets
The prior docs labeled many tickets "P0 / Blocker" that are actually **Minor** in Jira. Examples verified live on 2026-05-15:

| Ticket | Prior doc claim | Live Jira value (2026-05-15) | Real assignee |
|---|---|---|---|
| ENT-3824 (PwC lifecycle governance) | "P0 / Critical / blocker" | **Priority = Minor**, status = Pending Review | Ian Cohan-shapiro |
| ENT-2289 (FedRAMP High) | "P0" | **Priority = Minor**, ENT50 listed for FY28 | Irene Milyuk |
| ENT-3702 (FedRamp / Docusign feature) | "P1" | **Priority = Minor** | Charlie Gavey |
| ENT-3737 / 3738 / 3736 (Wells Fargo regulated) | "P1" | **Priority = Minor**, all Unassigned | (unassigned) |
| ENT-1690 (org-level data per site) | "P1" | **Priority = Minor**, on ENT50 (Identity + TSP) | Rob Saunders |

The **only** Critical / Blocker priority items currently open in `project = ENT` (verified 2026-05-15) are 21 issues — see `v3_open_blocker_critical.md`.

---

## What's in this v3 set

| File | Purpose | Status |
|---|---|---|
| `v3_FINAL_README.md` | This index + correction log | ✅ this file |
| `v3_coreng_org_map.md` | Verified engineering org (pillar → real engineering DRIs from page 7012411386) | ✅ |
| `v3_master_mapping.md` | **Primary deliverable.** ENT50 + recent priority ENT tickets mapped to real CoreEng pillar + DRI + status | ✅ |
| `v3_open_blocker_critical.md` | The 21 currently-open Blocker/Critical ENT items, with verified mapping | ✅ |
| `v3_recent_60d_inbox.md` | All ENT tickets created since 2026-03-15 (~46), with verified component-driven routing | ✅ |
| `v3_audit_log.md` | Every correction made vs prior docs (with citation) | ✅ |
| `v3_mustwin_review_template.md` | The Ke-Wang-canonical monthly review template (mirror of page 5696752671) for our use | ✅ |

The legacy v1/v2 files have been **left in place** for traceability but should be considered superseded.

---

## Quick reference (the answer in one paragraph)

Enterprise customer demand for Atlassian Cloud is captured in the `ENT` Jira project (`hello.atlassian.net/browse/ENT-*`). The ~50-issue subset that **Core Engineering has formally committed to deliver** is curated by Ke Wang on Confluence page **5861641112 (FY26 ENT50 List - CoreEng)** and reviewed monthly via the **MUSTWIN review** (template page 5696752671, May review page 7012411386). The three engineering pillars that absorb the bulk of ENT50 are:

1. **Identity** — DRIs: Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan
2. **Tenant & Sharding Platform (TSP)** — DRIs: Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles
3. **Tenant Data Platform (TDP / CoreData)** — DRIs: Vinod Kumar, Lin Chen, Alex Grach

Adjacent enabling pillars that pick up specific ENT items: **Reliability** (Arun Jayandra), **Networking** (Mathrubootham Janakiraman), **FinOps** (Tom Cutajar), **Deployment Verification / CloudSec** (Vinod Kumar). The Enterprise side DRI (the customer voice) is **Filiberto Selvas**, with Levon Esibov + Kangrong Yan as LT reviewers. See `v3_master_mapping.md` for the per-ticket table.
