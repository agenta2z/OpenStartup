# 11 · The Validation Stack — Tier 1 / 2 / 3 applied to the mapping

> Per Ke Wang's *New Eval Paradigm* (Confluence page 6884917799 §1), the Validation Stack is **top-down**: start with whether the intent was captured correctly (Tier 1), then whether the architecture is sound (Tier 2), then whether non-functional constraints are met (Tier 3). This file applies that framework to the ENT → CoreEng mapping itself.

## Tier 1 — Intent Fidelity (Spec vs. Blueprint)

**The question:** Did the mapping interpret the customer's actual intent, or did it take the path-of-least-resistance interpretation that satisfies the prompt but misses the business goal?

**The artifact reviewed:** The **Intent Summary** for each ENT row in [`03_master_mapping.md`](03_master_mapping.md) §A — the 1-line "what the customer is asking for" derived from the ENT description.

**Eval Actor at this Tier:** primarily **Level 2 — Engineer (Judgment Owner)**, played here by the MUSTWIN DRI (Ke Wang) reviewing routing rationale; **Level 3 — Stakeholder** check by Filiberto Selvas.

### Tier 1 findings (Semantic Diffs against the spec)

| ENT key | Spec (customer intent) | Blueprint says (our routing) | Semantic Diff result |
|---|---|---|---|
| ENT-3824 (PwC) | Lifecycle governance for 2,000+ sites | Identity → David Dooley | ✅ Match — component is `Cloud Admin — Organisations`; David owns the org/site model |
| ENT-2289 (FedRAMP High) | US-government compliance certification | Identity → Dushyant Gill (FedRAMP/GovCloud) | ✅ Match |
| ENT-2085 (CMK retroactive) | Apply customer-managed keys to existing data, not just new | TSP → Corey Johnston, with TDP follow-up | ⚠️ **Drift** — live assignee is **Hui Ren**, not Corey/Filiberto/Alex. The May 2026 review row attributes Filiberto Selvas as "DRI" — but that's the *Enterprise DRI* role, not engineering. Need MUSTWIN to confirm primary engineering owner. |
| ENT-3881 (DocuSign HIPAA) | Block on AI adoption — HIPAA compliance for Rovo | AI ↔ Identity (Trust scope) | ⚠️ **Latent drift** — assignee Ashwini Rattihalli is in the Rovo/AI line; Identity Trust scope is implied but not formally engaged. Surfacing this drift here is the Tier 1 job. |
| ENT-1520 (Confluence > 150k) | Scale Confluence to 250k single-site (named: SAP, BMW, JPMC, Siemens, Bosch, NSA, Oracle, AT&T, Apple, Citi) | Identity → Dushyant Gill (Identity scale) | ⚠️ **Drift** — live assignee is **Cody Zhang**, component is `Confluence - Scale` (a Confluence-product component, not an Identity one). This is a Confluence product team item that Identity *scale* concerns dovetail into; the prior routing put the entire item under Identity. Re-route: **Confluence Scale (Cody Zhang) primary**, Identity Scale consults. |
| ENT-3099 (CMK for Rovo) | Customer-managed keys for AI workloads | TSP + AI | ✅ Match — and **Shipped** ✅. Tier 1 closed. |
| ENT-2643 (800k users) | Scale to 800k user provisioning | Identity → Dushyant Gill | ✅ Match — **Shipped** ✅, assignee David Dooley confirms Identity ownership. |

### Tier 1 escalations identified

Three Tier-1 drifts surfaced — each becomes a row in the next MUSTWIN review's *Open Issues* table:

1. **ENT-2085 — primary engineering owner ambiguity** between Hui Ren (live), Corey Johnston (per the May review prose), and the TPM coordination layer (Filiberto Selvas). Need explicit POR statement.
2. **ENT-3881 — Identity Trust scope not formally engaged** despite HIPAA being an Identity-pillar concern. Risk: Rovo team patches without Identity sign-off; Identity later challenges the scope.
3. **ENT-1520 — Confluence product-team owner not credited.** Cody Zhang and the Confluence Scale team have been doing the work; Identity Scale is the dependency. Re-route the row's primary owner.

---

## Tier 2 — Architectural Cohesion

**The question:** Has the mapping ignored systemic interactions? AI is prone to "Local Optimization" — perfect per-item routing that misses the global picture (e.g., several BYOK items routed to TDP individually, but no one notices that 6 of them collectively define a *BYOK programme*).

**The artifact reviewed:** The **Side-Effect Map** in [`03_master_mapping.md`](03_master_mapping.md) §D ("Cross-cutting themes") + the cross-pillar dependency table in [`01_organization.md`](01_organization.md) §4 + the deeper org file [`15_deep_org.md`](15_deep_org.md) §B.

**Eval Actor at this Tier:** **Level 1 — Automated** (CI gates on the master mapping's table integrity) + **Level 2 — Engineer** (judges whether the blast radius is acceptable for this monthly review cycle).

### Tier 2 findings (Side-Effect Analysis)

| Cluster | # of items | Engineering blast radius | Risk if treated per-item |
|---|---|---|---|
| **BYOK family** (ENT-1958, 2022, 2035, 2085, 2647, 3099) | 6 | TDP (Vinod Kumar) is overloaded — 4 open Blockers + 1 active escalation + 1 Shipped item all hit the same DRI | Reviewing one BYOK item at a time hides the cumulative load |
| **ALP family** (ENT-2883, 3721) | 2 | Identity (Dushyant Gill) — both Blockers, neither on ENT50 — orphan-cluster risk | Two flagship Blockers without an ENT50 slot signals a process gap |
| **FedRAMP / Sovereign** (ENT-98, 293, 1445, 2289, 3702 + UAE/India/EU items) | 8+ | Identity (Dushyant Gill) — same DRI as ALP and Trust scope on Isolated Cloud | One person becomes the shared bottleneck for the entire Trust pillar |
| **BRIE Phase 2** (ENT-3785, 3787, 3788, 3668, 1929, 311, 151) | 7 | TSP (Lakshmi Behl) | Without naming this as a cluster, it looks like 7 disparate items |
| **MCP cluster** (8 Minor items, all Jemma Swaak) | 8 | AI / Rovo | Single-assignee cluster signals platform-shape demand, not 8 features |
| **Loom governance** (ENT-3814, 3817-3822) | 7 | Loom (Kristen Waters) — outside CoreEng | MUSTWIN observation only; no CoreEng action |

### Tier 2 escalations identified

* **Cumulative-load signal:** TDP (Vinod Kumar) and Identity (Dushyant Gill) each carry 6+ open items. The mapping should expose that load to the LT reviewers (Levon, Kangrong) as a Tier 2 finding — single-DRI saturation is a delivery risk that no per-row review surfaces.
* **Orphan-cluster signal:** ALP family (2 Blockers) and the unclassified parts of the BYOK family are flagship items with **no ENT50 slot**. This is the Tier 2 review surface deciding whether to admit them.
* **Architectural fit signal:** The BRIE Phase 2 cluster is doctrinally a *new programme* but is being delivered as 7 individual tickets. This is the Tier 2 surface for whether to formalise it as a programme (see [`07_new_project_candidates.md`](07_new_project_candidates.md) §6).

---

## Tier 3 — Non-Functional Guardrails

**The question:** What are the cost, sustainability, and ethics constraints that the mapping must respect?

**The artifact reviewed:** The **Resource & Cost Estimate** column (which today is implicit, not explicit). For an ENT → CoreEng mapping, the "Resource" is **engineering capacity**, the "Cost" is **opportunity cost** (every ENT50 commit displaces another commit).

**Eval Actor at this Tier:** **Level 0 — AI Self-Eval** (this Blueprint surfacing capacity claims) + **Level 1 — Automated** (CI gates on the master mapping's row counts) + **Level 2 — Engineer** (LT reviewers judge fit).

### Tier 3 findings (Resource Audit)

| Pillar | Open Blocker / Critical | Open Major | Active escalations | Capacity headline |
|---|---|---|---|---|
| **Identity** | 8 | 1 (ENT-1703) | ENT-2745 (Isolated Cloud), ENT-2289 (FedRAMP High deferred to FY28) | Saturated — owns the entire Trust + ALP + FedRAMP surface |
| **TSP** | 5 (overlap w/ TDP) | 0 | ENT-2085 (active) | Heavy — joint with TDP on BYOK + BRIE |
| **TDP** | 4 (BYOK pure) | 0 | ENT-2085 (consult) | Heavy — Vinod Kumar wears TDP + CloudSec + Deployment Verification (per [`15_deep_org.md`](15_deep_org.md) §A) |
| **Compute** | 0 | 0 | none | Light load |
| **Reliability** | 0 | 1 (Critical: ENT-3868 API rate limiting via Jira Platform / TDP) | none | Light load on ENT items; heavy on incident response |
| **Networking** | 0 | 0 | none | Light load |
| **FinOps** | 0 | 0 | none | Light load on ENT items |
| **AI / Rovo** (out-of-CoreEng) | 6 | 6 | DocuSign / Glean threat | Saturated — 32 items in the recent inbox alone |
| **Atlassian Guard** (out-of-CoreEng) | 1 | 0 | none | Moderate |
| **Atlas / Other** | 2 | 0 | none | Long-running orphans (ENT-376, ENT-381) |

### Tier 3 escalations identified

* **Single-person saturation:** Dushyant Gill (Identity Trust + FedRAMP + ALP) and Vinod Kumar (TDP + CloudSec + Deployment Verification) each cover scopes that two-three managers could plausibly hold. The Tier 3 surface is whether to ask LT to formally split these scopes for FY27.
* **Out-of-CoreEng AI overload:** 32 Rovo items in the inbox + 6 open Blockers/Critical + a customer-evaluating-Glean threat. CoreEng cannot address this directly; the Tier 3 finding is an *escalation to the AI org* via MUSTWIN.
* **Long-running Atlas Blockers:** ENT-376 and ENT-381 have been Blocker-priority for years. Either they are not really Blockers or the Atlas team needs MUSTWIN-level escalation. This is a Tier 3 finding for the next review.

---

## Summary — three Tier escalations to MUSTWIN

| Tier | Escalation | Owner | Surface |
|---|---|---|---|
| Tier 1 | ENT-2085 owner ambiguity; ENT-3881 missing Identity Trust engagement; ENT-1520 mis-routed | MUSTWIN DRI (Ke Wang) | Open Issues row in next review |
| Tier 2 | TDP + Identity single-DRI saturation; ALP and BYOK orphan-cluster admissions to ENT50 | LT reviewers (Levon, Kangrong) | Risks row in next review |
| Tier 3 | Dushyant Gill / Vinod Kumar scope-split candidate; AI org overload escalation; Atlas Blocker triage | LT reviewers + Filiberto Selvas | POR / Enterprise Asks rows in next review |
