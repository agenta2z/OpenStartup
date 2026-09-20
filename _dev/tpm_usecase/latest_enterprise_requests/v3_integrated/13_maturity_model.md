# 13 · Maturity Model — for the ENT → CoreEng mapping discipline

> Per Ke Wang's *Agentic Operations in the New SDLC* (Confluence page 6885869718), Stages 0-4 describe the journey from Manual Ops to Role Instantiation. This file applies the same Stage 0–4 frame to the **TPM mapping discipline** itself — where are we today, what's the next step, what would Stage 4 look like?

## The five stages, applied to the ENT → CoreEng mapping

| Stage | Name | How mappings are produced | Role of AI | Human role | Real example |
|---|---|---|---|---|---|
| **0** | Manual Mapping | TPM keeps the mapping in their head + scattered Confluence pages. Each MUSTWIN review re-derives the routing manually. | None | Firefighter + tribal-knowledge keeper | Pre-2026 baseline; the prior `00_*`–`07_*` flat files in this folder are Stage 0 artifacts (each one re-derived; no single source of truth) |
| **1** | AI-Assisted Reactive | TPM uses AI agents to fetch ENT data faster, generate routing tables, write per-pillar summaries, draft the MUSTWIN review page. AI is an accelerator; TPM still drives every routing decision. | Accelerator — speeds up human-driven mapping | Still primary mapper; AI as fast junior TPM | **This v3_integrated artifact set (May 2026).** AI fetched 100+ Jira tickets, cross-checked 75 Confluence pages, surfaced 21 open Blockers. Tony Chen made every routing call. |
| **2** | Policy-Governed Mapping | TPM authors machine-executable routing policies (e.g., "ENT items with component `Encryption — BYOK` → TDP Vinod Kumar"; "ENT items on ENT50 with status `Shipped` → drop from open-Blocker list"). Agent enforces policies autonomously for known patterns; escalates for novel ones. | Autonomous executor within policy bounds | Policy Governor — authors routing rules, reviews edge cases, evolves the policy set | **FY26 H2 target.** Routing rules below in §"Sample policies"; an agent runs them weekly and auto-files the next MUSTWIN review draft. |
| **3** | Self-Healing Mapping | When a customer escalation reveals a Blueprint gap (e.g., a Wells-Fargo regulated item that the mapping mis-routed), the agent detects, files a Permanent Remediation PR (per page 6885869718 §4 Artifact 3), and updates the Blueprint Spec — before the human is paged. | Primary responder; human reviews outcomes, not events | Governance rotation — auditing decisions, evolving policy set, deep-dive rotations | **FY27 vision.** Every escalation auto-files a Blueprint update; spec constraint encoded so future routings inherit the lesson. |
| **4** | Role Instantiation | A digital MUSTWIN-DRI agent owns the entire ENT → CoreEng mapping surface. Humans manage a fleet of digital TPMs (one per pillar?). | Digital employee — title (MUSTWIN DRI), scope (ENT corpus), memory (every prior month's review), track record | Strategic Architect — delegates pillar scopes, sets risk tolerance, reviews aggregate outcomes | **FY28+ vision.** "Hire via URL" pattern (page 6885869718 §6) instantiates a high-context MUSTWIN-DRI agent bootstrapped from prior MUSTWIN reviews + ENT50 + pillar onboarding hubs on Day 1. |

## Where we sit today (verified 2026-05-15)

**Stage 1 — AI-Assisted Reactive, executed exceptionally well.** This v3_integrated set demonstrates real AI-assisted-TPM value:

* 100+ ENT tickets enriched live in one session via `mcp__atlassian__get_jira_issue` (would have taken 2 days manually)
* 21 open Blocker/Critical surfaced via JQL in 30 seconds
* 75 Confluence VoC pages cataloged (prior manual catalog: 7 days)
* 6 Shipped items detected and re-tagged (would have been mislabelled "open Blocker" in a manual review)
* Pillar DRI roster verified against Ke Wang's own page (drift caught at L1)

**The Stage 1 ceiling, made visible by this very artifact:**

* All routing rules live in *prose* across [`03_master_mapping.md`](03_master_mapping.md), [`05_recent_inbox.md`](05_recent_inbox.md), [`07_new_project_candidates.md`](07_new_project_candidates.md). They are not yet machine-executable. **At Stage 2, they become policy expressions an agent can enforce.**
* The mapping was rebuilt from scratch at this snapshot (2026-05-15). There is no continuous loop. **At Stage 2, the mapping refreshes weekly; at Stage 3, it auto-updates on each Jira event.**
* The "Decision Log" in [`10_blueprint.md`](10_blueprint.md) §4 is hand-authored. **At Stage 2, decisions are logged as policy diffs against a versioned policy set.**
* Customer-revenue context (named accounts, ARR, escalation history) is partial and manually curated. **At Stage 3, it is auto-pulled from S360 / TWG.**

## Sample policies (Stage 2 starter set)

These are the routing rules that, if expressed as machine-executable policies, would lift the mapping from Stage 1 to Stage 2. Each line is a candidate for a future YAML policy file.

```yaml
# Pillar routing
- when: jira.component starts with "Cloud Administration"
  route_to: pillar.identity.dri.david_dooley
- when: jira.component starts with "Cloud Security"
  route_to: pillar.identity.dri.dushyant_gill
- when: jira.component starts with "Trust Foundations"
  route_to: pillar.identity.dri.dushyant_gill
- when: jira.component contains "Encryption" or "BYOK" or "CMK"
  route_to: pillar.tdp.dri.vinod_kumar
- when: jira.component starts with "Resilience - Backup"
  route_to: [pillar.tsp.dri.corey_johnston, pillar.tdp.dri.vinod_kumar]
- when: jira.component starts with "Audit"
  route_to: pillar.identity.alp_owner.dushyant_gill
- when: jira.component starts with "Information Protection - Guard"
  route_to: pillar.guard.audrey_garcia
  note: out_of_coreng_observe_only
- when: jira.component starts with "Rovo"
  route_to: pillar.ai_platform
  note: out_of_coreng_observe_only

# State transitions
- when: jira.priority in [Blocker, Critical] and jira.statusCategory != Done
  add_to: open_blockers_list
- when: jira.status == "Shipped"
  remove_from: open_blockers_list
  add_to: shipped_this_quarter

# Escalation surfacing
- when: ticket.named_customer in ["DocuSign", "PwC", "Wells Fargo", "AMAT", "Accenture", "SAP", "BMW", "JPMC", "Siemens", "Bosch", "NSA", "Oracle", "AT&T", "Apple", "Citi"]
  surface_in: mustwin.enterprise_asks_table
- when: ticket.priority == Blocker and ticket.age_days > 365
  surface_in: mustwin.aged_escalation_review

# Cluster detection
- when: 5+ open tickets share a single assignee + a single component family
  flag_as: cluster_candidate_for_named_programme
- when: 3+ ENT50 items share a single DRI and all are open Blocker
  flag_as: single_dri_saturation_risk
```

## Permanent Remediation PR (Stage 3 vision)

Per page 6885869718 §4 Artifact 3, every escalation that exposes a Blueprint gap should produce a **Permanent Remediation PR** — not just patch the immediate routing issue, but **encode a constraint** so the gap cannot recur.

### Example (forward-looking, FY27)

* **Escalation event:** Wells-Fargo CSM escalates that ENT-3737 (regulated APIs for comments) was sitting unassigned for 60 days; the customer felt ignored.
* **Immediate fix:** TPM routes ENT-3737 to David Dooley, MUSTWIN reviews surfaces it.
* **Permanent Remediation PR (the Stage-3 part):**
  - Update `policies.yaml`: add `rule "ticket from named-regulated-customer with no assignee for 30 days → auto-escalate to MUSTWIN DRI"`
  - Update Spec: add to ENT50 admission criteria "any item from a P50 named-regulated customer is fast-tracked to ENT50 candidate review within 14 days"
  - Update [`10_blueprint.md`](10_blueprint.md) §3 Assumption List: add "A9: Regulated-customer escalation latency must be < 30 days"
  - Update Confluence page (5848788720, ENT50 triage principles) with the new admission criterion
* **Result:** the next time a regulated-customer ticket sits unassigned for 30+ days, the policy fires automatically. The lesson is encoded, not just documented.

## Maintaining human judgment (Deep-Dive Rotations + Production Signal Loop)

Per page 6884917799 §4, the biggest risk in agentic operations is humans losing the technical familiarity needed to catch a bad decision. For this mapping discipline:

* **Deep-Dive Rotations:** Once a quarter, the MUSTWIN DRI manually re-routes 10 random ENT items from scratch — without consulting prior mappings or the agent. Compares own routing to the agent's. Discrepancies are calibration signal.
* **System State Narratives:** Once a month, the agent generates a 1-page plain-language summary: "what changed in the ENT corpus this month, which clusters grew, which Shipped, which escalated." Replaces the per-row reading load with system-level orientation.
* **Production Signal Loop:** Every customer escalation event becomes an input to the next mapping cycle (via Permanent Remediation PR). Without this loop, the mapping is a one-way gate rather than a learning system.

## Acknowledging the gap honestly

This artifact set is **Stage 1 done well**. It is **not** Stage 2 yet. The honest message to anyone reading this — and to Ke Wang in particular — is:

> The current artifact set is the *input* required to graduate from Stage 1 to Stage 2. Stage 2 needs (a) the policies above expressed in YAML against an executable engine, (b) a weekly refresh hook that re-validates the L0 + L1 artifacts, and (c) a `policy.yaml` change-log that captures every routing rule revision. None of those exist today; they are the next-quarter delta.
