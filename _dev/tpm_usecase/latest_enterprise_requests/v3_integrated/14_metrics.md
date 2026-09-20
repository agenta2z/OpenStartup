# 14 · Metrics — 2024 vs 2026, plus Time-to-Intent for this discipline

> Per Ke Wang's *New Eval Paradigm* (Confluence page 6884917799 §3 + §4), the 2026 measure of engineering excellence is **Time-to-Intent** — how quickly a business idea becomes a validated, deployed reality. This file articulates what the 2024-style and 2026-style metrics look like for the ENT → CoreEng mapping discipline.

## 1. Mapping-discipline metrics: 2024 vs 2026

| Metric | 2024 (manual TPM) | 2026 (this artifact set) |
|---|---|---|
| **Coverage of ENT corpus per review** | ~25 hand-picked ENT50 items | 100+ ENT items live-fetched (ENT50 + open Blockers + 60-day inbox) |
| **Time to refresh the mapping** | 5-7 days of TPM time per quarterly review | < 30 minutes for the data fetch + < 1 hour for the human L2 review |
| **Routing decision quality** | "Who wrote this ticket → ask them" (relies on tribal knowledge) | Component → pillar policy (deterministic, auditable, traceable to Ke Wang's pillar roster) |
| **Priority-label trust** | Hand-typed in MUSTWIN slides; drift between Jira and slides | Live `priority` field always; drift caught at L1 build |
| **Pillar DRI freshness** | Latest known names from monthly all-hands | Verified against `org-tree` + the May 2026 review on the day of L0 publish |
| **Customer-context attachment** | Mentioned in slide notes; not durable | Named-customer column in [`data/ent50_enriched_2026-05-15.md`](data/ent50_enriched_2026-05-15.md) |
| **Audit trail of routing changes** | None — slides overwritten each cycle | Versioned [`09_audit_log.md`](09_audit_log.md) + Decision Log §4 of [`10_blueprint.md`](10_blueprint.md) |
| **Identification of orphan clusters** | Surfaced when a CSM yells | Surfaced as Tier 2 finding in [`11_validation_stack.md`](11_validation_stack.md) |
| **"What did we ship this quarter?"** | Reconstructed manually from sprint reviews | Auto-detected: 6 ENT50 items Shipped between prior review and this one |

## 2. Mirror of the Eval Paradigm metrics table (from page 6884917799 §3)

The eval-paradigm doc lists these five engineering metrics in 2024 vs 2026 form. The same table, applied to the **mapping discipline** (not to engineering work itself):

| Metric | 2024 mapping (Code-Driven equivalent) | 2026 mapping (AI-Dependent equivalent) |
|---|---|---|
| **Coverage** | Manual writing of routing tables for 25 ENT items per quarter | Model-Based Coverage: AI generates routing assertions for 100+ items; human reviews the routing strategy |
| **"Security" (correctness checks)** | Static analysis (does the slide compile?) | Autonomous mapping check: a Red-Team Agent attempts to find ENT items that could plausibly route to a different pillar than declared, in a sandbox |
| **Performance** | "Did we get the deck out on time?" | Predictive Coverage: AI estimates how many ENT items are in each cluster *before* the next inbox arrives — surfaces capacity bottlenecks pre-emptively |
| **Maintenance** | "Who built this slide?" | Lineage Tracking: which version of which Blueprint and which routing policy produced each row in the master mapping, and why |
| **Review Quality** | Number of slide comments, slide turnaround time | Intent coverage: what % of the ENT50's stated commitments are explicitly addressed in the AI's artifact set this cycle |

## 3. Time-to-Intent for the mapping discipline

Per page 6884917799 §4, **Time-to-Intent** = "how quickly a business idea becomes a validated, deployed reality." For the ENT → CoreEng mapping discipline, this translates as:

| Time-to-Intent decomposition | Definition | 2024 baseline | 2026 target (this artifact) | 2027 vision (Stage 3) |
|---|---|---|---|---|
| **T1: Customer raises ENT** → **Triaged** | First MUSTWIN-visible signal | 1-30 days | 1-7 days | < 24 hours |
| **T2: Triaged** → **Routed to pillar DRI** | Mapping decision logged | 7-30 days | 1-7 days (this Blueprint) | Real-time on Jira event |
| **T3: Routed** → **Pillar DRI acknowledges** | First reply / status update | 7-60 days | 7-14 days (next MUSTWIN cycle) | < 7 days (policy-driven) |
| **T4: Acknowledged** → **ENT50 admission decision** | Yes/No on commit | 1-2 quarters | 1-2 quarters | 1 quarter |
| **T5: Admitted to ENT50** → **Engineering POR** | Plan-of-record committed | 1-2 quarters | 1-2 quarters | 1 quarter |
| **T6: POR** → **Shipped** | Customer-visible delivery | 6-18 months | 6-18 months | 6-12 months |
| **T7: Shipped** → **Customer-visible "the ask is done"** | Filiberto-side close-the-loop | (gap) | 1-3 months | < 14 days |

**Today's leverage:** the mapping discipline can drive T1 → T5 down dramatically. T6 (engineering build time) is the largely orthogonal pillar-execution metric. T7 (customer close-the-loop) is the Filiberto-Selvas-side discipline that this artifact enables but does not yet own.

## 4. Operational metrics for this artifact (the ones that should appear on a dashboard)

If we wanted to monitor the *health of this mapping discipline itself*, these are the metrics:

| Metric | Definition | Today's value (2026-05-15) | Target |
|---|---|---|---|
| **Stale-row count** | # of master-mapping rows where last verification > 14 days ago | 0 (snapshot is today) | < 5 |
| **L1 build pass rate** | % of `build_html.py` runs that pass all anchor + invariant checks | 100% (this build) | > 95% |
| **Tier 1 drift count** | # of Semantic Diffs surfaced per cycle | 3 (per [`11_validation_stack.md`](11_validation_stack.md) §Tier 1) | track trend; act on > 5 |
| **Single-DRI saturation count** | # of pillar DRIs carrying 5+ open items | 2 (Vinod Kumar TDP, Dushyant Gill Identity) | < 3 |
| **Orphan-cluster count** | # of clusters with 3+ open Blockers and no ENT50 slot | 1 (ALP family) | 0 |
| **Mean ENT-item triage age** | Median days from ENT created → first routing decision | (unmeasured today; baseline this month) | < 7 days at Stage 2 |
| **Customer-escalation surfacing rate** | % of named-customer ENT items that appear in Filiberto's MUSTWIN Enterprise Asks table | (unmeasured) | > 80% |
| **Shipped-items credit rate** | % of items Shipped this quarter that have a customer-facing "you asked for X, here it is" notification | (unmeasured) | > 90% |

## 5. The metric that Ke Wang's vision says matters most

Per page 6884917799 §4 closer:

> "You are no longer checking if the code is right; you are checking if the code is what you meant. The 2026 measure of engineering excellence is not 'lines shipped' — it's **Time-to-Intent**: how quickly a business idea becomes a validated, deployed reality."

For the ENT → CoreEng mapping discipline, the equivalent statement is:

> **You are no longer checking if the routing slide is well-formatted; you are checking if every customer ask has been heard, routed, and tracked to delivery. The 2026 measure of TPM excellence is not "review pages produced" — it's *Time-to-Intent for enterprise demand*: how quickly a customer-stated ask becomes a Shipped, customer-acknowledged delivery.**

That metric is the north star this artifact set was built to enable.
