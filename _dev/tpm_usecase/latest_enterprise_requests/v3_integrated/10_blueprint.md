# 10 · The Blueprint — formal artifact for the ENT → CoreEng mapping

> Authored in the format Ke Wang defines on Confluence page **6986270793** (*The Blueprint: Deep Dive*). The Blueprint is the **formal intermediate artifact between Spec (the customer ask) and Code (the engineering delivery)** — machine-readable, human-reviewable, persisted across the full lifecycle.
>
> This file *is* the Blueprint for the broader artifact set. Section 5 also embeds a **per-ENT-item Blueprint** for the highest-stakes open Blocker (ENT-2745 — Isolated Cloud) so the format is concrete, not abstract.

## 0. The problem this Blueprint solves

In the legacy TPM workflow, the ENT → CoreEng mapping lives nowhere. It exists in the head of the MUSTWIN DRI (Ke Wang), in scattered Confluence pages, and in monthly review notes that expire. When a new TPM is on-boarded, the design rationale is gone. The repo (this folder) becomes the only source of truth — and the repo does not explain *why* a ticket was routed to one pillar rather than another.

This Blueprint is the answer. It externalises the **routing logic** between Spec (the ENT ticket as the customer-stated intent) and Code (the CoreEng engineering plan and ATLAS goal that delivers it).

## 1. What this Blueprint is (and is not)

| Dimension | Description |
|---|---|
| **Execution Flow** | The logical sequence of how an ENT request becomes engineering work: customer raises ENT → ENT triaged on component → routed to pillar DRI → MUSTWIN review → ENT50 admission decision → ATLAS goal commitment → engineering execution → Shipped status → customer notified. |
| **Dependency Map** | A graph of how the mapping interacts with existing systems: ENT (Jira) ↔ ENT50 (Confluence 5861641112) ↔ MUSTWIN review (Confluence 5696752671) ↔ ATLAS goals ↔ pillar onboarding hubs ↔ TRUSTED roadmap. |
| **Risk Surface** | Misrouting (wrong pillar) → engineering frustration. Mispriortising (Minor labelled Blocker) → MUSTWIN review wastes time on noise. Stale data (a Shipped item still flagged "open Blocker") → Filiberto Selvas escalates an item that is already done — credibility loss with the customer. |
| **Spec Traceability** | Every row in [`03_master_mapping.md`](03_master_mapping.md) §A traces to a specific ENT key + the ENT50 page row + (where applicable) an ATLAS goal ARI. |
| **Decision Log** | See §4 below. |
| **Assumption List** | See §3 below. |

## 2. How this Blueprint was produced

The four-step process from page 6986270793 §2:

1. **Spec ingestion.** The "spec" is the union of (a) the canonical ENT50 page (5861641112), (b) the most recent MUSTWIN review (7012411386), and (c) the live ENT Jira project. Each ENT key is a clause in the spec. Ambiguities surfaced as `(verify)` rows in §A of the master mapping rather than as silent assumptions.
2. **Constraint mapping.** Each ENT clause was mapped against the existing CoreEng pillar graph (Identity / TSP / TDP / Compute / Reliability / Networking / FinOps / CDP) and the out-of-CoreEng route table (Atlassian Guard / Rovo AI / Product teams / Atlas / Ecosystem). The mapping rule is: **Jira component → primary pillar**, with cross-pillar overlap declared explicitly.
3. **Logic externalisation.** The Execution Flow above was made explicit (rather than left tacit in the MUSTWIN cadence).
4. **Spec traceability binding.** Every row in the master mapping is tagged with `spec_ref = ENT-<key> + page-5861641112-row-<n>` (where applicable).

## 3. Assumption List (validate before relying on this artifact)

| # | Assumption | What changes if false |
|---|---|---|
| A1 | Confluence page 7012411386 (Ke Wang's May 2026 review) is the authoritative current-state pillar DRI roster | Pillar DRIs in [`01_organization.md`](01_organization.md) are stale; refresh from latest MUSTWIN page |
| A2 | The Jira `priority` field on each ENT ticket reflects engineering urgency (not customer-revenue urgency) | Many "Minor" items become rightly Major when revenue-context is added; need a parallel "customer-revenue priority" column |
| A3 | The ENT50 page (5861641112) is comprehensive — every committed item appears there | If commits exist outside the ENT50 list, this mapping under-counts the engineering load |
| A4 | Components on a Jira ENT ticket reflect the implementing team's surface | Some components are obsolete category labels; routing should also check assignee + recent comments |
| A5 | Out-of-CoreEng items (Rovo AI, Guard, Confluence/Jira/JSM/Loom) are still legitimately surfaced via MUSTWIN even though CoreEng does not deliver them | If MUSTWIN scope tightens to CoreEng-only, drop §C "Product teams" sub-bullets |
| A6 | "Shipped" status in Jira means delivery is complete *for the customer*, not just engineering | A Shipped item may still need Filiberto-Selvas-side announcement; check before closing the customer-facing loop |
| A7 | The 21 open Blocker/Critical count is volatile (tickets get re-prioritised week-to-week) | Refresh `04_open_blockers.md` at the start of each MUSTWIN cycle, not less often |
| A8 | TPM headcount (Levon → Ashish → Ke Wang) is stable through FY26 | Pillar DRI assignments may shift if the TPM org reorgs |

## 4. Decision Log — choices made in producing this artifact set

| Choice | Considered | Chosen | Reason |
|---|---|---|---|
| File format | Single 200-page doc · 10 small files + HTML · Notion-style database | **10 small files + HTML** | Each file maps to one MUSTWIN information need; the HTML provides the cross-doc reading view |
| Pillar source-of-truth | FY25Q1 onboarding hubs · live `org-tree` · Ke Wang's May 2026 review (page 7012411386) | **Ke Wang's May 2026 review (primary), onboarding hubs (secondary)** | This is the most recent and most authoritative on current pillar leadership; reduces stale-name risk |
| Routing rule | Jira component only · ENT50 explicit assignment only · combined | **Combined: ENT50 explicit > Jira component > Ke Wang's narrative** | Each rule is the answer to the question "what happens when each upstream signal is silent on a ticket?" |
| Out-of-CoreEng items | Drop them · include and route · include and label | **Include and label** with PROD/AI/GUARD/ECO/Atlas codes | Drops would lose ~40% of inbox; labelling preserves observability without claiming CoreEng ownership |
| Treatment of "Shipped" items | Drop · keep with Shipped tag · list in a separate "Recently Closed" section | **Keep with Shipped tag inline** | Preserves continuity with prior MUSTWIN reviews and signals momentum on the ENT50 |
| Customer-revenue context | Skip · narrative only · structured column | **Narrative inline + named-customer column** in [`data/ent50_enriched_2026-05-15.md`](data/ent50_enriched_2026-05-15.md) | We have customer names (PwC, DocuSign, AMAT, Wells Fargo, etc.) but not revenue numbers — keep what's verified |
| Data freshness | Single point-in-time snapshot · refresh hooks · live-query JQL embedded | **Snapshot + JQL snippets** in [`02_demand_overview.md`](02_demand_overview.md) §3 | Snapshot makes the file self-contained; JQL makes refresh a 1-command operation |
| HTML build | External SSG (MkDocs / Docusaurus) · Markdown-only · custom no-deps script | **Custom no-deps Python script** (`build_html.py`) | No external dependencies; 134 KB self-contained HTML; one file to deploy anywhere |

## 5. Concrete Blueprint example — ENT-2745 (Isolated / Virtual Private Cloud)

This is what a Blueprint looks like for a single high-stakes ENT item. Authored as YAML to match the structure on Confluence page 6986270793 §5.

```yaml
spec:
  source: ENT-2745
  url: https://hello.atlassian.net/browse/ENT-2745
  canonical_priority: Blocker      # live Jira value, 2026-05-15
  customer_intent: |
    Allow regulated customers (FedRAMP, gov, finance) to run Atlassian Cloud
    inside a customer-controlled isolated network — a "virtual private cloud"
    on Atlassian's stack but with single-tenant data plane and customer-
    managed network ingress.
  named_customers: [<not yet attributed in Jira; verify with Filiberto>]
  components:
    - "Confluence — Compliance & Security"
  ent50_slot: FY26
  ent50_row: page 5861641112, row "Virtual Private / Isolated cloud"

execution_flow:
  - step: triage
    actor: MUSTWIN DRI (Ke Wang)
    logic: Recognised on ENT50 FY26 — already a committed item
    spec_ref: ENT50 page row
  - step: pillar_routing
    actor: MUSTWIN DRI
    logic: Joint Identity (Trust scope) + TSP (tenancy scope) — Identity DRI Dushyant Gill is primary because the request lives under Confluence-Compliance-Security
    spec_ref: page 7012411386 pillar roster
  - step: monthly_review
    actor: MUSTWIN review (Levon, Kangrong, Filiberto, Dushyant)
    logic: Open-Issues table row in next FY26 review; status reviewed monthly
    decision: Identity owns, TSP consults
    decision_ref: A4 (component-driven routing)
  - step: customer_engagement
    actor: Filiberto Selvas (Enterprise DRI)
    logic: Maintain customer dialogue; log every escalation event in the May review's Enterprise Asks table
  - step: engineering_commitment
    actor: Identity pillar (Dushyant Gill)
    logic: Plan-of-record decision on FY26 vs slip; if slip, declare in POR row of Section 1 of the next MUSTWIN

dependency_map:
  spec_inputs: [ENT-2745, page 5861641112, page 5696752671]
  pillars_engaged: [Identity, TSP]
  external_actors: [Filiberto Selvas, customer CSM]
  blast_radius_if_misrouted:
    - high   # this is a flagship FedRAMP-adjacent item; misrouting compounds with ENT-1445 / ENT-2289 / ENT-98
  does_not_touch: [Compute, Networking, FinOps, Rovo/AI]

risk_surface:
  - risk: status remains "open Blocker" across multiple monthly reviews without movement
    severity: high
    mitigation: name a per-review POR commitment in §1 of the MUSTWIN review
    spec_ref: ENT-2745 status as of 2026-05-15
  - risk: customer perception of single-tenant promise mismatching engineering reality
    severity: medium
    mitigation: Filiberto-led joint customer briefing once Identity provides a credible POR
  - risk: scope creep from adjacent FedRAMP family (ENT-1445, ENT-2289, ENT-98) being conflated with this single Isolated-Cloud line
    severity: medium
    mitigation: keep Isolated Cloud as its own MUSTWIN review row; avoid bundling with FedRAMP family

assumption_list:
  - The customer accepts a virtual-private model (single-tenant logical, shared physical) rather than fully airgapped
  - Identity has the architectural mandate to scope this — TSP only consults
  - The May 2026 MUSTWIN review's "Enterprise Asks" table is the right surface for this

spec_traceability:
  - flow_step: pillar_routing → spec_ref: page 7012411386 (Identity DRI = Dushyant Gill)
  - flow_step: engineering_commitment → spec_ref: ENT50 page 5861641112 (FY26 row)
  - flow_step: customer_engagement → spec_ref: page 5696752671 (Enterprise DRI role definition)
```

The reviewer reads this Blueprint, not the underlying Confluence and Jira directly. The questions the reviewer answers:

* Is the routing rule (Identity primary, TSP consults) correct? (Tier 1 — Intent Fidelity)
* Is the blast radius acceptable given other FedRAMP-family items? (Tier 2 — Architectural Cohesion)
* Are the customer-perception and scope-creep risks adequately mitigated? (Tier 3 — Non-Functional Guardrails)

## 6. Blueprint Lifecycle for the ENT → CoreEng mapping

Per page 6986270793 §6, a Blueprint persists across the lifecycle:

| Lifecycle stage | This artifact's role |
|---|---|
| **Blueprint Review** | Today's pass — TPM (Tony Chen) walks Ke Wang through this Blueprint before any monthly MUSTWIN review embeds it |
| **Code Synthesis** | The next MUSTWIN review page (June 2026) is "synthesised" from this Blueprint — the 4-section template (Progress / Risks / Open Issues / Enterprise Asks) is filled with the rows defined here |
| **Validate** | After publishing the June review, validate: (a) every Open Issue row has a verified Jira priority match, (b) every Enterprise Ask is on the ENT50 or has a write-up explaining why not, (c) every Risk has a `UPDATE` annotation owner |
| **Operate** | When an enterprise escalation hits Filiberto Selvas, this Blueprint is the anchor — it tells him which pillar to walk into, which DRI to ping, and which prior review row to cite |
| **Prevention PR** | Every escalation that exposes a Blueprint gap (e.g., a Wells-Fargo regulated item that this Blueprint failed to route) yields a Blueprint update — not a new orphan doc |
| **Onboarding** | A new TPM joining the MUSTWIN review reads this Blueprint to learn the routing logic without re-deriving it from raw Confluence + Jira |

## 7. Three enforcement layers (per page 6986270793 §4)

| Layer | What it does for this Blueprint |
|---|---|
| **Layer 1 — Pre-Mapping Auditor (Tier 1)** | Before each MUSTWIN review, an Auditor Agent (or human reviewer) compares the proposed routing against the canonical ENT50 page and Ke Wang's most recent pillar roster, surfacing intent drift before the review goes out. The audit log [`09_audit_log.md`](09_audit_log.md) is itself a Layer 1 artifact. |
| **Layer 2 — Structural Linters during Mapping (Harness)** | The mapping has structural invariants: (i) every ENT key must have a Jira-verified `priority` value (no inferred P0/P1); (ii) every pillar name must appear in the verified DRI roster (no orphan pillar labels); (iii) every "Shipped" item must drop out of the open-Blockers list. The Python `build_html.py` script enforces some of these mechanically (cross-doc anchor validation); the rest is human-enforced via the audit log. |
| **Layer 3 — Post-Mapping Validation (Tier 2 + 3)** | After every MUSTWIN review publishes, run a validation pass: (a) Semantic Diff — does any review row contradict a master-mapping row? (b) Architectural Cohesion — has any new ENT cluster emerged that we mis-routed? (c) Risk Surface — has any open Blocker aged beyond N months without movement (= aged escalation needing a new POR)? |

## 8. Open Questions

Per page 6986270793 §8, surfacing the unresolved design questions explicitly:

* **Format standardisation.** Should Blueprints for ENT items be YAML (as in §5 above), JSON, or a hybrid? YAML reads well; JSON parses everywhere. Decision deferred until an Auditor Agent is built.
* **Who owns Blueprint updates?** When an escalation reveals a Blueprint gap, who authors the update — the MUSTWIN DRI (Ke Wang), the pillar DRI, or the Enterprise DRI (Filiberto)? Today the answer is "MUSTWIN DRI", which scales poorly.
* **Granularity.** Should every ENT50 item have its own per-ticket Blueprint (as in §5), or is one umbrella Blueprint per pillar enough? Per-item is high fidelity but heavy maintenance.
* **Linter generation from Blueprint.** Can the structural linters (Layer 2) be auto-generated from the Decision Log + Assumption List, or do they require hand-authoring? Today they're hand-authored.
* **Blueprint in the absence of a Spec.** What happens for ENT items that arrive *off* the ENT50 (i.e., bottom-up from the inbox)? Current answer: they live in [`05_recent_inbox.md`](05_recent_inbox.md) until promoted; need a lightweight Blueprint variant for unpromoted items.

---

## Appendix — Related pages

* [`11_validation_stack.md`](11_validation_stack.md) — Tier 1 / Tier 2 / Tier 3 framework applied row-by-row
* [`12_eval_actor_stack.md`](12_eval_actor_stack.md) — Levels 0-4 framework: who validates this Blueprint, when, with what blind spots
* [`13_maturity_model.md`](13_maturity_model.md) — Stage 0–4 maturity model for the ENT → CoreEng mapping (where we are today, what's next)
* [`14_metrics.md`](14_metrics.md) — 2024 vs 2026 metrics + Time-to-Intent definition for this work
* Source: Confluence **6986270793** *The Blueprint: Deep Dive* (Ke Wang)
* Source: Confluence **6884917799** *The New Eval Paradigm* (Ke Wang)
* Source: Confluence **6885869718** *Agentic Operations in the New SDLC* (Ke Wang)
* Source: Confluence **6786483776** *The Agentic Engineering Shift* (parent vision, Ke Wang)
