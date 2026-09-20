# 12 · The Eval Actor Stack — who validates the mapping, and when

> Per Ke Wang's *New Eval Paradigm* (Confluence page 6884917799 §0 + §2D), the Eval Actor Stack defines **who validates** the artifact, **when**, and **what they cannot catch** (which the next level must cover). This file applies that framework to the ENT → CoreEng mapping.

## The five levels, applied to this mapping

| Level | Actor | When | Primary Role for this mapping | Blind spot (covered by the next level) |
|---|---|---|---|---|
| **L0** | AI Self-Eval (this document set + Red Team review) | Before any human reviewer sees the artifact | This Blueprint produces the artifact set: Intent Summary per row, Decision Log, Assumption List, Side-Effect Map, Risk Flags, Resource & Cost Estimate, Test Strategy Summary. A "Red Team" pass would challenge: did we mis-route any row? Did we miss any cluster? | Cannot catch *spec-was-wrong* errors — if the customer's intent was misread upstream (in the ENT description itself), L0 cannot detect it |
| **L1** | Automated (build_html.py validation + JQL recompute hooks) | At "publish" of the v3_integrated set | Validates structural invariants: every ENT key has a verified `priority`; every cross-doc anchor link resolves; every pillar name appears in the verified DRI roster; the open-Blocker count matches live JQL (`priority in (Blocker, Critical) AND statusCategory != Done`); no Shipped item appears as "open Blocker" anywhere | Cannot evaluate intent or business context — only mechanical / countable properties |
| **L2** | Engineer / TPM (Judgment Owner) — currently Tony Chen, eventually MUSTWIN DRI (Ke Wang) | Artifact Review — after L0 + L1 pass | Reviews the artifact set for Tier 1 Intent Fidelity; approves Tier 2 blast radius (single-DRI saturation, orphan-cluster admission); approves Tier 3 cost fit (capacity claims). Logs reasoning in Decision Log §4 of [`10_blueprint.md`](10_blueprint.md) | Loses ENT-corpus intuition over time — addressed by Deep-Dive Rotations: a sample of 5 random ENT keys spot-checked monthly to maintain calibration |
| **L3** | Stakeholder (Enterprise DRI Filiberto Selvas + LT reviewers Levon Esibov, Kangrong Yan) | Pre-MUSTWIN cycle | Validates that the mapping does what the customer expects; adversarial — try to find an enterprise-revenue item that the mapping mis-prioritised because it's "Minor in Jira" but "Critical to the customer relationship" | Not equipped to catch architectural decay or technical debt accumulating across pillars |
| **L4** | Production (Continuous Eval) — the MUSTWIN review itself + the customer-escalation feedback loop | Post-publish, ongoing month-to-month | Are real ENT items being routed correctly? Are pillar DRIs reading and acting on the rows they own? Is Filiberto Selvas seeing fewer escalations of "you forgot about us" type? Production signals (escalation rate, MUSTWIN attendance, ENT50 admission lag) close the loop back to L0 | Latency — failures only surface after at least one full MUSTWIN cycle (4-6 weeks) |

## Per-row Eval Actor mapping

For each row in [`03_master_mapping.md`](03_master_mapping.md), the dominant Eval Actor depends on the row's status:

| Row state | Dominant Eval Actor | Why |
|---|---|---|
| Row is on ENT50 + Shipped | L4 (Production) — close the loop with the customer | The L0–L3 cycle is done; only customer-side production confirmation remains |
| Row is on ENT50 + open Blocker/Critical | L2 (Engineer) + L3 (Stakeholder) — joint review | This is the active-escalation surface for the monthly review |
| Row is on ENT50 + Pending Review / Public Roadmap | L2 (Engineer) only | Quarterly check-in cadence is sufficient |
| Row is in recent inbox (last 60 days) | L0 (Self-Eval) + L1 (Automated) | Routing assertion needs human upgrade only if L1 / L2 surface a drift |
| Row is in recent inbox + has named customer | L3 (Stakeholder — Filiberto) | Customer voice elevates the row to L3 review |
| Row is out-of-CoreEng (PROD/AI/GUARD/Atlas) | L0 (Self-Eval) only — observe, don't act | Routed but not owned by CoreEng |

## Eval Handoff Protocol

Per page 6884917799 §2D, each level produces a signed artifact that the next level accepts or escalates. For this mapping:

| From → To | Signed artifact | Escalation path on failure |
|---|---|---|
| L0 → L1 | The 10 markdown files + `data/*.json` raw enrichment | L0 failure → no L1 build runs (i.e., `build_html.py` fails fast on missing fields) |
| L1 → L2 | The published `index.html` + a "validation report" (`build_html.py` exit message) | L1 gate failure → blocks publish, no human review needed; fix and rebuild |
| L2 → L3 | The "ready for MUSTWIN" sign-off — currently a manual review pass logged in [`09_audit_log.md`](09_audit_log.md) | L2 unresolved → escalate to a second TPM (e.g., Kangrong Yan), not back to the AI |
| L3 → L4 | The published MUSTWIN review page (FY26 (June) ENT-CoreEng Execution Review) | L3 unresolved → escalate to LT (Levon) for prioritisation call |
| L4 → L0 | Customer-escalation events + MUSTWIN review feedback comments → roll into next month's Blueprint update | L4 failure (recurring escalation) → trigger a Prevention PR for the Blueprint itself (per [`13_maturity_model.md`](13_maturity_model.md) Stage 3) |

## Where this mapping currently sits in the Eval Actor Stack

* **L0:** ✅ Done (this document set is the L0 artifact)
* **L1:** ⚠️ Partially mechanised — `build_html.py` validates anchors and renders cleanly, but does not yet enforce all the structural invariants in [`10_blueprint.md`](10_blueprint.md) §7 Layer 2. Open work.
* **L2:** ⏳ Pending — TPM walk-through scheduled (this conversation is the prep for that walk-through)
* **L3:** ⏳ Pending — MUSTWIN review embedding scheduled for next month's review cycle
* **L4:** ⏳ Pending — first feedback wave will arrive after the June 2026 MUSTWIN review

## What we cannot catch (and how the Stack covers it)

| Risk | Which Eval Level catches it |
|---|---|
| The Jira `priority` field is wrong (e.g., should be Major but is Minor due to Jira-discipline gap on the customer-CSM side) | **L3 (Stakeholder)** — Filiberto Selvas catches via customer dialogue; mapping cannot infer this from Jira alone |
| The pillar DRI roster has changed since 2026-05-12 | **L1 (Automated)** — re-pull `org-tree` monthly; if the L0 artifact is older than the live data, fail the build |
| A new ENT cluster has emerged that crosses pillars in a way our cross-cutting themes don't capture | **L2 (Engineer)** — Deep-Dive Rotation surfaces it; the mapping cannot self-detect novel patterns |
| The MUSTWIN review process itself is broken (e.g., LT reviewers stop reading the published review) | **L4 (Production)** — escalation rate spike → trigger process retrospective |
