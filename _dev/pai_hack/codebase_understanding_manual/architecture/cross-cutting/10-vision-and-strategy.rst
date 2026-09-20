.. _pai-vision-and-strategy:

============================================================================
Vision & Long-Horizon Strategy (FY26 → FY28)
============================================================================

:Date authored: 2026-05-05
:Status: Synthesised from public artefacts + investigations dated 2026-05-04/05
:Confidence: **MIXED.** FY26 H2 facts are HIGH confidence (live OKR, live
             roadmap doc). FY27+ themes are MEDIUM confidence (no published
             team vision doc was found; long-horizon claims are inferred from
             corporate AI strategy, the existing FY26 roadmap stages, and
             siblings-team scopes). Where confidence is LOW, this chapter
             explicitly says so.

----

.. contents:: On this page
   :depth: 3
   :local:

----

Why this chapter exists
==========================

:doc:`01-business-and-technical-goals` covers **what** the team is
shipping in FY26 H2 and the metrics that prove it worked.

This chapter covers **why** — the multi-year direction, where Proactive
AI Platform (PAI) sits in Atlassian's broader AI strategy, and what the
team is *unlikely* to ship until FY27 or FY28. The intent is to make
long-range product/architecture decisions traceable to a strategic frame
rather than to whatever the most recent OKR looked like.

Part 1 — Honest preface: what we could not find
==================================================

Before stating the vision, the boundary of available evidence:

* **No formal "PAI Team Vision FY27" Confluence page exists** that an
  external investigator can access. Searches across the ``proai``,
  ``AM3``, ``CentralAI``, ``Rovo``, and ``StrategicAlign`` Confluence
  spaces (with keywords ``proactive ai vision``, ``habitual AI``,
  ``fy27``, ``proactive AI roadmap``) returned no canonical multi-year
  vision document.
* **No FY27 Atlassian goal** with PAI as owner is currently visible to
  Atlas-goal MCP queries.
* **The Atlas Goal MCP returns "Success" with empty body** for both
  ``ATLAS-115305`` (the live FY26 OKR) and any search; live progress
  numbers are therefore not retrievable through the available APIs as
  of 2026-05-05. The OKR's *target* is verified
  (Confluence page ``6143084752``) but its *current value* and
  *status phase* are not retrievable here.

The vision below is therefore **constructed** from:

1. The FY26 H2 R4 plan (Confluence ``6169149742``), which names the
   "Stage 1 / Stage 2 / Stage 3" phasing — Stage 3 spills into Q1 FY27.
2. Atlassian's published Rovo strategy and corporate-deck materials in
   ``CoreProjects/atlassian_packages_corporate-docs/rovo/`` (visible in
   this workspace).
3. Source-of-truth files inside ``proactive-ai-platform/`` that
   constrain what is technically possible without a major rewrite.
4. The boundary lines drawn by sibling-team scopes (see Part 5).

If you read this and you are inside the team, **please replace the
LOW-confidence parts with citations to the canonical doc** when one
is published.

Part 2 — The team's mission, in one sentence
================================================

PAI exists to make AI **habitual**, not occasional, by carrying the
backend (throttling, generation, routing, observability, agent
orchestration) of every Atlassian surface that proactively offers AI to
a user — so product teams can experiment with new proactive UX without
re-implementing the platform plumbing.

This sentence is **synthesised** (HIGH confidence) from:

* The FY26 OKR's framing — "drive habitual AI usage **via proactive
  invocations**" makes "proactive" the noun the team owns and
  "invocations" the verb being maximised.
* The team's own positioning per the FY26 R4 plan: PAI is the
  **throttle / decision / backend-orchestration plane**; the UX and
  the model live in product teams (Confluence Editor AI, AIX,
  Rovo Chat, Central AI).
* The repository structure: every package outside ``feature/`` is a
  pure platform layer (interceptor, featuregate, sqs, task,
  service/metric, stratus, …). The deliberate ratio of feature code
  vs. platform code reinforces the "platform-first, surfaces-second"
  shape.

Part 3 — Three-horizon view
==============================

McKinsey-style horizons, calibrated to Atlassian's R4 / FY plan rhythm:

.. list-table::
   :header-rows: 1
   :widths: 12 18 70

   * - Horizon
     - Window
     - What changes for PAI
   * - **H1 — Now**
     - Q3-Q4 FY26
     - Proactive **suggestions** (nudges, conversation starters, insight
       cards) on a small handful of surfaces; PAI provides throttle +
       generation + caching. Single OKR: **invocations 400K → 1.5M / month**.
       (HIGH confidence — already shipping.)
   * - **H2 — Next**
     - Q1 FY27 — Q2 FY27
     - Move from "PAI suggests, user clicks" to "PAI **acts on a budget**".
       The team begins serving multi-step **agentic workflows** (LAM /
       Rovo Studio agents) where the user delegates outcomes instead of
       confirming each suggestion. The KPI shifts from raw invocations to
       **outcome-acceptance rate** and **agent-delegation rate**.
       (MEDIUM confidence — corporate Rovo strategy points here; PAI's
       Stage-3 roadmap line "scale 1P + 3P proactive interactions"
       implies it.)
   * - **H3 — Bet**
     - FY28
     - Proactive AI as the **default** way users interact with Atlassian
       products: the surface is no longer a Jira board with an AI
       sidebar, it is an AI workspace that opens specific Atlassian UIs
       only when human review is required. PAI becomes the
       **invocation budget manager** for an organisation rather than for
       a session — a tenant-level economic primitive.
       (LOW confidence — this is the corporate Rovo bet, restated for
       PAI; not stated in any PAI doc found.)

Part 4 — North-star: from invocations to value
=================================================

The current OKR (invocations) is a **leading indicator**, not the
end-state metric. The corporate AI / Rovo materials in
``CoreProjects/.../corporate-docs/rovo/`` consistently push toward
**outcome metrics** (acceptance rate, delegation rate, COGS-adjusted
revenue attribution, retention lift on AI-engaged cohorts). Expect the
PAI metric to evolve along this path:

.. list-table::
   :header-rows: 1
   :widths: 18 25 22 35

   * - Generation
     - Metric
     - Status
     - Why the team will graduate from this
   * - G1 (today)
     - **Monthly proactive AI invocations**
     - LIVE (FY26 H2 OKR)
     - Counts attempts, not value. Easy to game with a noisy nudge.
   * - G2 (next)
     - **Acceptance rate** (insertions ÷ interactions) and
       **dismiss rate**
     - Tracked, not OKR
     - Distinguishes a useful suggestion from an annoying one.
   * - G3 (next)
     - **Proactive Fans %** — % of MAU at L4+ engagement on proactive
       surfaces in 28 days
     - Tracked
     - Habit formation, not just engagement.
   * - G4 (likely FY27)
     - **Outcome-acceptance rate** for delegated agentic workflows
     - Not yet defined
     - The suggestion → action gap is where the dollar value lives.
   * - G5 (FY27/28 bet)
     - **Revenue uplift attributable to proactive surfaces**
       (likely via Atlassian Intelligence pricing tiers)
     - Not yet attempted by PAI
     - Aligns engineering investment to commercial outcome.

This trajectory is **not** in any PAI doc; it is inferred from
corporate Rovo strategy (Glean competitive teardown, Maestro proposal,
Microsoft Team Copilot teardown). Treat as **MEDIUM-LOW confidence
direction**, but **HIGH confidence shape** — the metric *will* mature
beyond raw invocations.

Part 5 — Where PAI sits in the Atlassian AI estate
======================================================

The five sibling AI engineering teams and the boundary line between
each and PAI. Scopes verified by reading each repo's ``AGENTS.md`` /
``README.md``:

.. list-table::
   :header-rows: 1
   :widths: 22 32 46

   * - Sibling team / repo
     - Scope (one line)
     - Boundary with PAI
   * - **convo-ai-platform** (Rovo Chat)
     - Synchronous chat orchestration, conversation state, tool calling
     - Rovo Chat is **request-driven** (user types). PAI is
       **event-driven** (user views something, the system decides to
       suggest). Rovo Insights logic is being **ported** from
       convo-ai → PAI.
   * - **ai-gateway**
     - Single LLM-call abstraction (model routing, retry, quota,
       streaming, cost tagging)
     - PAI is one of many *clients* of AI Gateway. PAI does not pick
       models; it consumes them. AI Gateway latency caps PAI's SLO.
   * - **responsible-ai-api**
     - Pre/post-prompt safety, PII / toxicity / policy filters,
       evaluation harness
     - PAI calls Responsible AI for input/output checks on every
       generation. RAi's verdict can suppress an invocation entirely.
   * - **ml-studio**
     - Training infrastructure, fine-tuning, dataset versioning
     - PAI does **not** train models. ML Studio produces the models
       that AI Gateway then serves to PAI.
   * - **devai-services**
     - Developer-AI surfaces (Bitbucket Rovo, code review, autodev)
     - Distinct user surface. PAI does not own developer flows; it
       *could* in future provide the proactive layer if devai surfaces
       adopt the same throttle / orchestration plane.
   * - **central AI / AIX**
     - Cross-product AI experience, evaluation framework, UX standards
     - PAI is a **backend** for AIX-owned UX. Acceptance/dismiss rate
       definitions are owned by AIX; PAI emits the events.

Part 6 — Competitive frame
===============================

PAI's competitive context is dominated by **proactive enterprise AI**
players. Source: ``CoreProjects/.../corporate-docs/rovo/`` corporate
strategy notes (HIGH confidence on competitor identity, MEDIUM
confidence on the "PAI competes on dimension X" mapping below — those
mappings come from the strategic-context investigation 2026-05-05).

.. list-table::
   :header-rows: 1
   :widths: 18 18 64

   * - Competitor
     - Threat tier
     - Dimension PAI must win on
   * - **Glean**
     - 🔴 Highest
     - Cross-product knowledge graph + agentic actions on it. PAI's
       counter: **Teamwork Graph + first-party UI integration**.
   * - **Microsoft Team Copilot**
     - 🟠 High
     - Bundled in M365; PAI's counter: deeper Atlassian-tool
       integration, lower friction inside Jira/Confluence.
   * - **Salesforce Agentforce**
     - 🟡 Medium-High
     - CRM-domain agents; doesn't overlap PAI's surfaces directly today.
   * - **Notion AI** / **ServiceNow Now Assist** / **Cursor**
     - 🟢 Medium
     - Adjacent surfaces; only relevant when PAI considers expanding
       into their domain.

The strategic value-prop for PAI, distilled across the corporate docs:

1. **Native Atlassian semantics.** PAI sees structured Jira / Confluence /
   Bitbucket data, not screen-scraped HTML. This is the moat against
   vision-model UI agents.
2. **Compliance-grade trust.** Tenant-scoped, RBAC-aware, audit-trailed
   through the Responsible AI pipeline.
3. **Platform leverage.** A single PAI investment is reused by every
   product surface (Confluence editor, Jira boards, Rovo Chat,
   future Maestro).
4. **Long-tail coverage via UI agents.** Where APIs are missing
   (custom fields, plug-ins, on-prem), the LAM-driven path can fall
   back to UI control — a credibility advantage over API-only
   competitors.

Part 7 — Strategic risks the team is exposed to
==================================================

Honest risk register synthesised from the corporate competitive notes
and the technical posture documented in :doc:`05-observability-and-metrics`:

.. list-table::
   :header-rows: 1
   :widths: 30 18 52

   * - Risk
     - Likelihood
     - Mitigation surface
   * - **AI Gateway latency cap** dominates p95 for any LLM-touching
       PAI endpoint
     - HIGH
     - Push for AI Gateway SLO tightening; design async-first so
       latency is hidden from the user.
   * - **OKR is gameable** by adding noisier nudges that increase
       invocations but reduce acceptance rate
     - MEDIUM
     - Pair every invocation OKR with a quality OKR (acceptance /
       dismiss / fans). Already partly in place per
       :doc:`01-business-and-technical-goals` Part 4.
   * - **No FY27 vision artefact** means each PR is reasoned against
       the OKR alone, not the multi-year direction
     - MEDIUM
     - Publish a team vision page (Confluence) and link from this
       chapter. Hold quarterly vision-vs-OKR alignment review.
   * - **Sibling-team boundary drift** — if Rovo Chat or AIX takes
       over throttling, PAI loses its primary platform purpose
     - LOW-MEDIUM
     - Maintain explicit charter; document boundary in
       :doc:`07-ai-gateway-and-stratus` and Part 5 above.
   * - **Glean closes the cross-product knowledge gap before
       Atlassian's Teamwork Graph is mature**
     - MEDIUM
     - Out of PAI's hands; PAI contributes by emitting high-fidelity
       invocation traces into the Teamwork Graph.

Part 8 — Decisions still owed (open vision questions)
========================================================

Questions that this investigation surfaced and that the team should
answer in writing before FY27 planning. Each is an *opportunity*, not
a critique.

1. What is the **post-OKR metric**? When invocations cross 1.5M, what
   is the FY27 H1 north star? (Acceptance rate? Outcome-acceptance?
   Revenue?)
2. **How much of "agentic workflow execution" is PAI vs. Rovo Chat?**
   The platform-vs-surface boundary that worked for nudges may not
   transfer to multi-step agents.
3. **Does PAI own the cross-tenant invocation budget**, or does
   Atlassian Intelligence pricing own it? An economic primitive
   has to live somewhere.
4. **What does deprecation look like for a proactive surface** that
   misses its acceptance-rate floor? PAI today has gating but no
   formal "retire surface" workflow.
5. **Does PAI build its own evaluation pipeline**, or does it remain a
   pure data-emitter for Central AI's evaluator? This is a
   ~year of engineering either way.

Part 9 — How to use this chapter
====================================

* When **scoping a PR**, check Parts 3-4: does the change move a G1
  metric, a G2 metric, or neither? PRs that move only G1 should
  document why they don't degrade G2/G3.
* When **proposing a new surface**, check Part 5: which sibling team
  owns the UX, and which boundary line are you crossing?
* When **prioritising a refactor**, check Part 7: does this refactor
  reduce a strategic risk? If yes, the risk register is your
  justification narrative.
* When **planning a quarter**, check Parts 3 + 8: is the work in the
  current horizon, or is it pulling FY27 horizon-2 capability into
  H1 because nothing else is competing for the time?

Part 10 — Citations
======================

HIGH-confidence sources (live, retrievable):

* `Proactive AI Engineering Deep Dive <https://hello.atlassian.net/wiki/spaces/AM3/pages/6143084752>`_
* `R4 Planning, FY26 H2 <https://hello.atlassian.net/wiki/spaces/proai/pages/6169149742>`_
* `Onboarding Rovo Insights to PAI <https://hello.atlassian.net/wiki/spaces/AM3/pages/6849003562>`_
* ``service-descriptor.sd.yml`` — boundary on what PAI's runtime can do
* :doc:`01-business-and-technical-goals` — current OKR + KPIs

MEDIUM-confidence sources (corporate, in workspace, not authored by PAI):

* ``CoreProjects/.../corporate-docs/rovo/Glean - The Startup Competitor.md``
* ``CoreProjects/.../corporate-docs/rovo/Microsoft Team Copilot & AI Agents - Competitive Teardown.md``
* ``CoreProjects/.../corporate-docs/rovo/Why Atlassian - UI Agents & Deep Operations.md``
* ``CoreProjects/.../corporate-docs/rovo/Hybrid Orchestration Framework - An Evolution.md``
* ``CoreProjects/.../corporate-docs/rovo/Project Maestro Proposal.md``
* ``CoreProjects/.../corporate-docs/rovo/Atlassian Owning Deep Operations UI Agents.md``

LOW-confidence inferences (no canonical doc):

* "Three horizons" framing in Part 3 — synthesised from the H2 R4 plan's
  Stage 1/2/3 phases.
* "Five generations of metric" framing in Part 4 — extrapolated from
  acceptance/dismiss/fans KPIs already on the team's dashboard.
* "FY28 north-star = invocation budget manager" in Part 3 — a corporate
  Rovo bet, not a stated PAI bet.

Cross-references inside this documentation set:

* :doc:`01-business-and-technical-goals` — what the OKR is today.
* :doc:`11-metrics-catalog` — every metric with its source-of-truth.
* :doc:`12-optimization-playbook` — how to move each metric.
* :doc:`02-development-history` — what shipped in the last 6 months.
