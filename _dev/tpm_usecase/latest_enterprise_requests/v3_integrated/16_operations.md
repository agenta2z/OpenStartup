# 16 · Operations — Policies, Guardrails, Incident Artifacts, Reference Case

> Per Ke Wang's *Agentic Operations in the New SDLC* (Confluence page 6885869718), operations is **woven into every stage**, not bolted on after Ship. This file applies that vision to the ENT → CoreEng mapping discipline as a continuously-operated system, not a one-shot artifact.

## 1. Policy Governor role for the MUSTWIN DRI

Per page 6885869718 §3, the SRE's highest-value activity is no longer watching dashboards or running runbooks — it's **authoring, testing, and maintaining the policies the agents operate under**. For the MUSTWIN DRI (Ke Wang's role), the equivalent is:

* **Author** the routing rules that determine which ENT item lands in which pillar's queue.
* **Test** them by spot-checking 10 random ENT items per quarter (Deep-Dive Rotation).
* **Maintain** them by versioning the policy set in `policies.yaml` (today: prose; FY27: machine-executable).
* **Govern** by reviewing the agent's Reasoning Traces — *not* approving every routing call, but auditing edge cases and approving the policy set itself.

Per page 6885869718, the only **true escalation events** are **strategic ambiguity** — situations where two routing choices both carry negative business impact and the right call depends on context the agent doesn't have (regulatory exposure, customer relationship sensitivity, upcoming announcements).

## 2. Policy types (mirror of page 6885869718 §3)

| Policy Type | Example for the mapping discipline | Agent Behaviour |
|---|---|---|
| **SLO Contract** | "Every ENT item from a P50 named-regulated customer must reach pillar DRI acknowledgment within 7 days" | Auto-routes the ticket; auto-pings DRI; tracks ack latency; escalates breach to MUSTWIN |
| **Rollout Gate** | "An ENT item is admitted to ENT50 only if (a) named on the canonical ENT50 page OR (b) Blocker priority + on the corpus for > 30 days OR (c) named-customer escalation in Filiberto's queue" | Filters new admissions; auto-files candidates; rejects orphans |
| **Cost Guardrail** | "Never auto-route more than 5 new ENT items per pillar DRI per week without human approval" | Caps autonomous routing pressure; pages MUSTWIN DRI when cap reached |
| **Escalation Boundary** | "Page the MUSTWIN DRI when any new ENT item carries a named customer not previously seen, OR when an open Blocker passes 365 days without movement" | Defines the exact threshold at which autonomous routing stops and human judgment begins |

## 3. Guardrails (the hard limits on autonomous mapping)

Per page 6885869718 §5, autonomous action depends on explicit, well-tested guardrails. For the mapping discipline:

| Failure Mode | Risk | Guardrail |
|---|---|---|
| Mapping mis-routes a ticket; pillar DRI gets noise; trust in mapping degrades | **HIGH** | All autonomous routings are *staged* (suggested, not committed) until L2 reviewer accepts. Routing committed only after confidence threshold or human approval. |
| Policy gap — incident type not covered, agent takes no action | **HIGH** | Default-to-page: any ENT item not matching a known policy pattern immediately escalates to the MUSTWIN DRI. Silence is never the default. |
| Permanent Remediation PR for the mapping introduces a new routing failure mode | **MEDIUM** | Every Blueprint update goes through the full Validate stage (L1 invariant check + L2 review) before publish — not a fast path. |
| Policy drift — routing rules become stale as pillar leadership changes | **MEDIUM** | Policies are versioned alongside the Blueprint. Quarterly governance rotation ensures policies are reviewed on cadence, not left to accumulate. |
| MUSTWIN DRI loses ENT-corpus familiarity, can't validate routing decisions meaningfully | **MEDIUM** | Deep-Dive Rotations (per [`13_maturity_model.md`](13_maturity_model.md)) maintain the technical grounding required to exercise sound judgment on AI-generated routing. |

## 4. Three incident artifacts when an enterprise escalation hits

Per page 6885869718 §4, when an incident hits an SRE receives three AI-generated artifacts: Impact Delta, Causal Chain, Permanent Remediation PR. Mirror for the MUSTWIN DRI when an enterprise escalation arrives:

### Artifact 1 — Impact Delta

Who was affected and for how long, expressed in business terms — not "ENT-3881 is Blocker" but **"DocuSign — flagship enterprise customer evaluating Glean as a competitor — flagged Rovo HIPAA gap; risk = ARR retention; latency = 14 days from initial flag to MUSTWIN surface."**

The MUSTWIN DRI's first question: does the business impact cross the escalation threshold defined in policy?

### Artifact 2 — Causal Chain

A visual map showing how a routing or commit gap cascaded into the customer escalation — the full blast radius, not just the ticket symptom.

For ENT-3881 (DocuSign):
```
ENT-3881 raised (Apr 2026) [component: Rovo / AI - Other]
  → routed to Rovo team only [Identity Trust scope NOT engaged at L1]
    → Rovo team scopes as a feature gap, not a Trust commitment
      → Identity-pillar HIPAA roadmap not consulted
        → Customer escalates to Filiberto Selvas (May 2026)
          → MUSTWIN review surfaces gap (this Blueprint)
            → Routing rule update needed: AI Trust items co-route to Identity
```

This Causal Chain maps directly to a Tier 2 (Architectural Cohesion) finding: a routing rule that lacked cross-pillar awareness produced a single-pillar response to a multi-pillar concern.

### Artifact 3 — Permanent Remediation PR

The most consequential artifact. The mapping doesn't just patch ENT-3881's routing — it adds a constraint that ensures **this specific failure mode cannot recur**:

* **Spec constraint added** to ENT50 admission criteria: "Any AI/Rovo item with HIPAA, GDPR, FedRAMP, or BYOK scope MUST co-route to Identity-pillar Trust DRI (Dushyant Gill) at L1 — autonomous routing alone is insufficient."
* **Policy update** in `policies.yaml`: `when: ticket.component matches "Rovo" and ticket.description contains regex "(HIPAA|GDPR|FedRAMP|BYOK|sovereign|residency)" → co_route_to: pillar.identity.trust_dri`
* **Blueprint Assumption List** updated: add A10 — "AI items with regulatory keywords are not single-pillar items even if Jira component says so."
* **MUSTWIN review process** updated: any AI item with a named regulated customer auto-files in the Enterprise Asks table for the next review.

The MUSTWIN DRI's role: review the proposed Spec constraint and the policy fix, then approve. This is the highest-leverage action — it converts a one-off escalation into a permanent improvement to the mapping discipline.

## 5. Reference case — ENT-2745 (Isolated Cloud) walked end-to-end

To match page 6885869718's *RAI Apr 2026* reference case (Stage 1 done well; the gap to Stage 2 made visible), the equivalent reference case for this mapping discipline is **ENT-2745 (Virtual Private / Isolated Cloud)**.

### Where ENT-2745 sits today (Stage 1 demonstration)

* On ENT50 FY26 ✅
* Live priority: **Blocker** ✅ (verified 2026-05-15)
* Live assignee: Michael Andreacchio
* Routed to: Identity (Dushyant Gill) primary, TSP (Corey Johnston) consults
* Surfaced in: [`04_open_blockers.md`](04_open_blockers.md) row 9, [`03_master_mapping.md`](03_master_mapping.md) §A row, [`10_blueprint.md`](10_blueprint.md) §5 (full per-item Blueprint)

### What Stage 1 *cannot* yet do for ENT-2745

* **No automatic re-check.** If Dushyant moves off Identity Trust scope tomorrow, the mapping won't notice until the next manual L0 refresh.
* **No customer-revenue context.** ENT-2745 has no named customer in Jira; the customer-revenue narrative lives in Filiberto's head.
* **No engineering-POR linkage.** The mapping says "Identity owns" but does not link to an ATLAS goal or a sprint commitment.
* **No aged-escalation trigger.** ENT-2745 has been on ENT50 since FY26 began (Q1); there's no policy that auto-flags it as "open Blocker for > 6 months without progress."

### What Stage 2 would add

* `policies.yaml` rule: "any ENT50 Blocker with no commit in > 90 days → auto-file MUSTWIN risk row"
* Auto-pull of the linked ATLAS goal (when Dushyant attaches one) into the mapping row
* Customer-revenue context column populated from Filiberto's CRM
* Weekly L1 build re-validates the row's pillar DRI against the latest org-tree

### What Stage 3 would add

* Permanent Remediation PR fires on the customer's first escalation event, encoding "Isolated Cloud must have a per-monthly POR statement — never an empty 'in progress'"
* Causal Chain auto-generated when Filiberto reports "the customer is unhappy"; the mapping shows the full cascade

The ENT-2745 case is concrete, ongoing, and exactly demonstrates what page 6885869718's "RAI Apr 2026 is a Stage 1 case executed exceptionally well — and the ceiling is visible" framing predicted.

## 6. Agent assignment & specialisation (mirror of page 6885869718 §"Scope of the SRE Agent")

In the FY27+ vision (Stage 4 of [`13_maturity_model.md`](13_maturity_model.md)), TPM mapping agents are **generic at birth, specialists by assignment**. A new mapping agent assigned to *one pillar* (say Identity) and one assigned to *another pillar* (say TDP) start from the same base, but after 30 days they have entirely different domain models.

| Scope | What the agent owns | Training inputs | Specialisation over time |
|---|---|---|---|
| **Pillar** | All ENT items routed to one specific pillar (e.g., Identity) | Pillar's onboarding hub, Ke Wang's pillar roster, the pillar DRI's recent comments, prior MUSTWIN review rows for this pillar, ATLAS goals, Confluence space | Learns pillar's unique component patterns, which DRI takes which sub-component, escalation patterns, customer overlaps |
| **ENT corpus** | All ENT items, cross-pillar | The full ENT Jira project, all ENT50 history, all MUSTWIN reviews, named-customer overlay | Learns cross-pillar patterns (e.g., BYOK items always touch TDP + TSP; ALP always Identity), customer-cluster patterns, predictive cluster emergence |
| **Customer** | All ENT items from a single named enterprise customer (e.g., DocuSign) | Customer's CSM history, prior escalations, named-customer ENT items, S360 ARR data | Learns customer's communication style, escalation triggers, which CSM follows up on what |

Today, all three scopes are held by a single human (the MUSTWIN DRI). The Stage 4 vision is one agent per scope, with the human as Strategic Architect.

## 7. The honest gap

This file articulates Stages 2–4 as *vision*. None of the policies, agents, or auto-remediation flows above exist today. What exists today (this v3_integrated set) is the *substrate* the FY27+ implementation will need:

* The 100+ verified ENT items → training corpus for the agent
* The Blueprint + Decision Log + Assumption List → the policy seed
* The Validation Stack + Eval Actor Stack → the audit framework
* The Maturity Model → the staging plan

Stage 2 is a quarter-of-engineering-investment away. This file documents what that investment buys.
