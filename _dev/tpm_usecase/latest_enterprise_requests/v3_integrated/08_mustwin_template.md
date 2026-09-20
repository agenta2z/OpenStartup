# 08 · MUSTWIN Monthly Review Template

> Mirror of Confluence page **5696752671** (*FY26 Enterprise MUSTWIN Monthly Review Template*) — the canonical format Ke Wang (MUSTWIN DRI) uses for the *FY26 (<Month>) ENT-CoreEng Execution Review* page each month.

## 0. Header (panel-info preamble)

> *For CoreEng to establish a monthly Enterprise MUSTWIN review with the stakeholders. The goal is to reflect on progress, risks / mitigations, etc.*
>
> Source-of-truth links:
> * MUSTWIN plan & staffing — Confluence page **5319794175**
> * ENT50 commit register — Confluence page **5861641112**

## 1. Stakeholder roster (small table at the top)

| Role | Person |
|---|---|
| MUSTWIN Owner (LT review) | Levon Esibov |
| Co-reviewer (LT) | Kangrong Yan |
| MUSTWIN DRI | **Ke Wang** |
| Pillar Owners — Identity | Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan |
| Pillar Owners — Tenant & Sharding (TSP) | Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles |
| Pillar Owners — Tenant Data Platform (TDP / CDP) | Vinod Kumar, Lin Chen, Alex Grach |
| Pillar Owner — Compute | Kayley Ma |
| Enterprise DRI | Filiberto Selvas |
| Data Governance DRI | Anand Balachandran, Sarah Brown |
| Cadence | Monthly on the first Tuesday |

## 2. Section 1 — Progress (Success / Delays / POR)

Three rows: **Success**, **Delays**, **POR (Plan-of-Record changes)**. Each row has columns:

| Category | What changed | Team | Notes |
|---|---|---|---|
| Success | (e.g., Units GA milestone met) | Identity | (link to ATLAS goal) |
| Delays | (e.g., Direct Role Assignment slip) | Identity | (mitigation status) |
| POR | (e.g., New GA target Sep 30, 2026) | Admin Experience | (alignment with sponsors) |

## 3. Section 2 — Risks (with mitigations)

| ⚠️ Risk | Followup |
|---|---|
| Free-form description of the risk (link to ATLAS goal where relevant) | `UPDATE` status pill + @-mention pillar DRI for the next review |

(Per May 2026 review: e.g. "**Units GA risk** — Identity projects Direct Role Assignment will not land in time for Units Internal release; SCIM rules allocation may exceed end-of-June. Mitigations under discussion this week.")

## 4. Section 3 — Open Issues (decisions / help asks)

| 🛈 Open Issue | Team |
|---|---|
| Free-form description of the open issue, with links to relevant Confluence pages, and any blockquoted external statements | `UPDATE` status pill + task list of follow-ups |

(Per May 2026 review: e.g. "**Assets ↔ TDP fit** — Assets delaying TDP migration; TiDB optimiser / columnar store cannot match Postgres at Assets' scale. TDP team + PingCap working on spike; decision end of May.")

## 5. Section 4 — Enterprise Asks (deep-dive, escalations)

| 🎯 Enterprise Ask | Notes | DRI | Followup |
|---|---|---|---|
| Link to ENT issue (e.g., ENT-2085) | Description of escalation; link to internal page | Filiberto Selvas (Enterprise DRI) | Pillar follow-up DRIs (e.g., Alex Grach + Michael Wilde) |

## 6. Call-to-Actions (panel-note at top of next review)

End each draft with an explicit Call-to-Actions panel listing the @-mentioned pillar DRIs and what they need to fill in by EoW.

---

## Suggested workflow when applying this to our analysis

1. **Open** the most recent FY26 ENT-CoreEng Execution Review page in Confluence (page 7012411386 was May; the next one will be June).
2. **Pre-fill** the Stakeholder Roster from §1 above (the names rarely change month-to-month).
3. **Update Progress** (§2) using ATLAS goal links from the linked pillar projects (Identity, TSP, TDP, Compute, Reliability, Networking, FinOps pillars all have ATLAS goals — re-pull each cycle).
4. **Lift Risks** (§3) from the prior month's review by checking for unresolved `UPDATE` rows.
5. **Pull Open Issues** (§4) by querying ENT for `priority in (Blocker, Critical) AND statusCategory != Done` — see [`04_open_blockers.md`](04_open_blockers.md).
6. **Curate Enterprise Asks** (§5) with Filiberto Selvas — prioritise items where the customer (or enterprise CSM) has escalated this month.
7. **Send call-to-actions** to the named pillar DRIs.

---

## Why this template matches Ke Wang's Artifact-Review framing

The user originally referenced *The New Eval Paradigm: From Construction to Evaluation* (Confluence page 6884917799) — Ke Wang's Artifact Review framework. The MUSTWIN format above maps directly:

| Artifact Review concept | MUSTWIN equivalent |
|---|---|
| **Intent Summary** | Stakeholder roster + ENT50 commit register link |
| **Decision Log** | POR row in §2 |
| **Assumption List** | Risks table §3 |
| **Side-Effect Map** | Enterprise Asks §5 (where one ENT request is a side-effect of a larger goal) |
| **Risk Flags** | Risks §3 |
| **Resource & Cost Estimate** | (added when needed under "Notes" of POR rows) |
| **Test Strategy Summary** | Implicit — the customer (Filiberto's Enterprise side) acts as the L3 stakeholder UAT |

This is why [`03_master_mapping.md`](03_master_mapping.md) is structured the way it is — Section A (ENT50 = Intent Summary), Section B (Open Blockers = Risk Flags), Section C (Recent inbox = Side-Effect Map / new demand), Section D (Cross-cutting themes = Assumption List), Section E (How to use = Test Strategy Summary).
