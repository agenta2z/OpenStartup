# Enterprise Demand → Core Engineering Mapping
### Integrated, deduplicated v3 — verified 2026-05-15

> **Purpose.** This is the single source of truth for "what is the Atlassian Enterprise customer asking for, and which Core Engineering pillar should deliver it?" — written from the perspective of a TPM doing exactly the job that **Ke Wang** (MUSTWIN DRI) does. Every fact in this set is verified against live Jira (`hello.atlassian.net`) on **2026-05-15** and against Ke Wang's own canonical Confluence pages.
>
> The integrated set replaces the prior `00_*`–`07_*`, `corrected_*`, and `v3_*` flat files in this folder. Those files contained duplicated and partially incorrect content (see `09_audit_log.md`).

---

## Quick navigation

| # | File | What it answers |
|---|---|---|
| 1 | [`01_organization.md`](01_organization.md) | Who owns what? Engineering vs TPM separation; verified pillar DRIs; cross-org roles. |
| 2 | [`02_demand_overview.md`](02_demand_overview.md) | How big is the demand and what does it look like in aggregate? Counts, buckets, trends, methodology. |
| 3 | [`03_master_mapping.md`](03_master_mapping.md) | **Primary deliverable.** Per-ticket → pillar → DRI table covering ENT50, all open Blocker/Critical, and the last-60-day inbox. |
| 4 | [`04_open_blockers.md`](04_open_blockers.md) | The 21 open Blocker/Critical items right now, with verified routing. |
| 5 | [`05_recent_inbox.md`](05_recent_inbox.md) | Last 60-day ENT inbox (since 2026-03-15), pillar-routed by Jira component. |
| 6 | [`06_voc_sources.md`](06_voc_sources.md) | Voice-of-customer source catalog (75 Confluence pages across 4 spaces). |
| 7 | [`07_new_project_candidates.md`](07_new_project_candidates.md) | 8 emerging initiatives where customer demand exceeds current capacity. |
| 8 | [`08_mustwin_template.md`](08_mustwin_template.md) | Ke Wang's MUSTWIN monthly review format, mirrored for our reuse. |
| 9 | [`09_audit_log.md`](09_audit_log.md) | Every correction made vs prior local docs, with citation. |
| 10 | [`data/`](data/) | Raw verified Jira data (`batchA.json/.md`, `batchB.json/.md`) for ~100 ENT tickets. |
| 11 | [`index.html`](index.html) | Single-page rendered site (built by `build_html.py`) for stand-alone viewing. |

---

## The 60-second answer

* The Atlassian **Enterprise (ENT) Jira project** captures customer demand from the high-touch enterprise segment.
* Of ~100 actively-tracked ENT tickets, **25 are on the formally-committed "ENT50"** list curated by Ke Wang on Confluence page **5861641112**.
* Right now there are **21 open Blocker/Critical** ENT tickets (live JQL, 2026-05-15) — the focus of this month's MUSTWIN review.
* Demand concentrates on **3 Core Engineering pillars** that absorb the majority of ENT items:
  1. **Identity** — DRIs Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan
  2. **Tenant & Sharding Platform (TSP)** — DRIs Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles
  3. **Tenant Data Platform (TDP / CoreData)** — DRIs Vinod Kumar, Lin Chen, Alex Grach
* Adjacent pillars taking specific items: **Compute** (Kayley Ma), **Reliability** (Arun Jayandra), **Networking** (Mathrubootham Janakiraman), **FinOps** (Tom Cutajar), **Deployment Verification / CloudSec** (Vinod Kumar).
* **Out-of-CoreEng routes** (still relevant for MUSTWIN observation): **Atlassian Guard / DLP**, **Rovo / AI platform**, individual product teams (Confluence, Jira, JSM, Loom).
* **Enterprise DRI** (the customer voice) — **Filiberto Selvas**.
* **MUSTWIN Owner / LT Reviewers** — Levon Esibov + Kangrong Yan. Levon is **Head of TPgM** (TPM/program-management line, *not* an engineering EVP).
* **MUSTWIN DRI (TPM)** — **Ke Wang**. This entire research effort emulates his role.

---

## How to use this document set

| If you want to … | Open … |
|---|---|
| Get oriented in 5 minutes | this `README.md` then [`02_demand_overview.md`](02_demand_overview.md) |
| Route a single ENT ticket | [`03_master_mapping.md`](03_master_mapping.md) (Ctrl-F the key) |
| Triage an incoming escalation | [`04_open_blockers.md`](04_open_blockers.md) and the "Suggested Triage Actions" section |
| Plan a monthly MUSTWIN review | [`08_mustwin_template.md`](08_mustwin_template.md) + [`03_master_mapping.md`](03_master_mapping.md) |
| Identify a missing initiative | [`07_new_project_candidates.md`](07_new_project_candidates.md) |
| Understand prior errors and what changed | [`09_audit_log.md`](09_audit_log.md) |
| Re-run live Jira queries | the JQL snippets in [`02_demand_overview.md`](02_demand_overview.md) §3 |

---

## Verification provenance (so future readers can trust the numbers)

| Source category | What was queried | When |
|---|---|---|
| Live Jira (REST via `mcp__atlassian__get_jira_issue`) | ~100 ENT tickets, full fields including `assignee`, `priority`, `components`, `labels` | 2026-05-15 06:55–07:00 PT |
| Live Jira (TWG `jira workitem search`) | Aggregate counts and the open Blocker/Critical list | 2026-05-15 06:56 PT |
| TWG `org-tree --include-profile-title` | Job titles for Levon Esibov, Ashish Consul, Ke Wang | 2026-05-15 06:42 PT |
| Confluence page **7012411386** | "FY26 (May) ENT-CoreEng Execution Review" — Ke Wang's own pillar DRI roster | created 2026-05-11, read 2026-05-15 |
| Confluence page **5861641112** | "FY26 ENT50 List - CoreEng" — the commit register | read 2026-05-15 |
| Confluence page **5696752671** | "FY26 Enterprise MUSTWIN Monthly Review Template" | read 2026-05-15 |
| Confluence page **5319794175** | "MUSTWIN CoreEng FY26 Enterprise Plan" — deliverables & staffing | read 2026-05-15 |
| Confluence page **5619065001** (TRUSTED space) | "High-Touch Roadmap → ENT50 Source of Truth" | read 2026-05-15 |
| Confluence page **6884917799** | "The New Eval Paradigm: From Construction to Evaluation" — Ke Wang's Artifact Review framing (the format expectation) | read 2026-05-15 |

Where this set says "(verify)" against a row, the value can be filled with a one-shot Jira REST call using the snippet in [`02_demand_overview.md`](02_demand_overview.md) §3.

---

## What changed vs the prior local doc set?

See [`09_audit_log.md`](09_audit_log.md) for the full diff. The headlines:

1. **Org-structure errors fixed.** Prior docs called Levon Esibov "EVP Engineering" and Ashish Consul "VP Core Engineering." Live `org-tree` shows both lead the **TPM line**, not engineering.
2. **Ticket priority mislabels fixed.** Prior docs labeled many ENT tickets "P0/P1/Critical/blocker"; live Jira shows most are **Minor**. (e.g., ENT-3824 PwC = Minor; ENT-2289 FedRAMP High = Minor.)
3. **Aggregate-count claims rechecked.** "152 ENT tickets total" was unreproducible. Reliable subsets: 21 open Blocker/Critical; 25 named ENT50.
4. **Pillar-owner names updated.** Prior `corrected_master_mapping.md` named Prashant Ghosal, Lakshmi Behl, Greg Zaney, Akshay Nambiar, Wayne Yim, Ke-Wang-as-FinOps-owner, etc. The **verified May 2026 pillar DRIs** are different (and Ke Wang is a TPM, not FinOps DRI — Tom Cutajar is). Some legacy names remain accurate as **assignees on individual tickets** (e.g., Lakshmi Behl on the BRIE family) — those are preserved in [`03_master_mapping.md`](03_master_mapping.md).
5. **8 New Project Candidates preserved.** From the old `corrected_master_mapping.md` Section 3, with each one re-checked against current Jira and the May 2026 review — see [`07_new_project_candidates.md`](07_new_project_candidates.md).
6. **75 Confluence VoC pages cataloged.** From old `04_confluence_voc_enterprise_context.md`, deduplicated and trimmed — see [`06_voc_sources.md`](06_voc_sources.md).
