.. _pai-business-and-technical-goals:

============================================================================
Business & Technical Goals, Metrics, and Optimization Priorities (FY26)
============================================================================

:Date: 2026-05-04
:Sources: Atlassian Confluence (AM3 / proai spaces) + Atlassian Goals + Atlassian Projects MCP, cross-verified against ``service-descriptor.sd.yml``, ``application.yml``, FY26 H2 R4 planning doc.
:Verification: All numerical targets cited to a Confluence URL or a goal/project ARI (no estimates).

**Purpose of this document:** if you are optimising this codebase — for engagement,
quality, latency, throughput, reliability, or developer velocity — this page tells
you what to optimise, by how much, and in what order.

.. note::

   **This chapter is one of four** that together form the
   business-and-strategy spine of this documentation set:

   * :doc:`01-business-and-technical-goals` *(this page)* — **what** the
     team is shipping in FY26 H2 and the metrics that prove it worked.
   * :doc:`10-vision-and-strategy` — **why** (the multi-year direction
     and PAI's place in the Atlassian AI estate).
   * :doc:`11-metrics-catalog` — **the source-of-truth** for every metric,
     SLO, alarm, and capacity number, each cited to ``file:line``.
   * :doc:`12-optimization-playbook` — **the how** (which code lever
     moves which metric, in priority order).

   Read them as a set. The vision chapter is also where the **honest
   limits of what we can verify** are documented (no live OKR-progress
   API access as of 2026-05-05; targets are HIGH confidence, current
   *progress* values are NOT retrievable through this documentation
   set's tooling).

.. note::

   **Verification status of numerical claims (audited 2026-05-05):**

   * **OKR target ``1.5M / month`` and baseline ``400K / month``** —
     HIGH confidence (sourced from Confluence pages ``6143084752`` and
     ``6169149742``).
   * **OKR live progress %** — NOT VERIFIABLE via Atlas Goal MCP today;
     the API returns a successful empty response. Visit goal
     ``ATLAS-115305`` directly for the live number, or contact
     Brian Feldman (DRI).
   * **Planned SLOs in Part 3** — aspirational, NOT enforced. There is
     no ``continuous-verification.yml`` in the repo as of this date
     (verified by directory listing). See :doc:`11-metrics-catalog`
     Part 5 for the full status.
   * **All other facts** are cited inline.

----

.. contents:: Table of Contents
   :depth: 3
   :local:

----

Part 1 — The Primary FY26 H2 OKR
====================================

The team's single most important measurable goal this half is the **Habitual AI
Usage** OKR, owned by Brian Feldman (DRI), with Anthony Manchin as technical
lead.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Field
     - Value
     - Notes
   * - Objective
     - Drive habitual AI usage via proactive invocations
     - Aligns to Rovo's 3× adoption mission
   * - **Primary metric**
     - **# of AI action invocations via proactive experiences (per month)**
     - Counts every successful invocation across all proactive surfaces
   * - **Baseline (start of H2)**
     - **400,000 / month**
     - Snapshot at H2 kickoff
   * - **Target (end of H2)**
     - **1,500,000 / month**
     - 3.75× growth in 6 months
   * - **Stretch (0.7 confidence)**
     - **1,200,000 / month**
     - 3.0× growth — committed
   * - Owner / DRI
     - Brian Feldman
     -
   * - Tech lead
     - Anthony Manchin
     -

Why **invocations** rather than MAU?

* Captures **engagement depth**, not just monthly reach.
* Responds quickly to UX changes (a successful nudge tweak shows up within days).
* Naturally weights toward **proactive surfaces** the team actually owns
  (contextual menu, Rovo Button nudges, search suggestions, Home Threads/Tasks).

Part 2 — Contributing experiences (the OKR's denominators)
==============================================================

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Surface
     - Status
     - Owns
     - What "an invocation" means here
   * - **Summarise Changes Nudge**
     - GA (Dec 2025)
     - Confluence AI
     - User clicks "Summarise" on a page they revisited; PAI returns the throttle decision before the nudge is shown
   * - **Conversation Starter Nudge**
     - Fishfooding (Q3 FY26)
     - AIX + Confluence
     - User opens Rovo and clicks one of the suggested starters
   * - **Rovo Insights**
     - In dev (Q3-Q4 FY26)
     - PAI core team
     - User clicks "Show insights" on Jira/Confluence dashboard; PAI generates the insight bundle
   * - **Rovo Button nudges**
     - Always-on
     - Cross-team
     - User clicks the floating Rovo button (with PAI-curated CTA)
   * - **Search-based proactive suggestions**
     - In planning
     - AIX
     - User accepts a search-driven nudge
   * - **Home Threads & Tasks**
     - Emerging
     - Cross-team
     - Future surface

PAI's role across all of these is the **same**: be the throttle / decision /
backend-orchestration plane. The UX and the model live in product teams.

Part 3 — Production SLOs (planned; not yet registered in Tome)
===================================================================

These targets are stated in the FY26 H2 planning doc but **are not yet
enforced** by Tome. The codebase will treat them as aspirational SLOs until
the alarm rules ship:

3.1 Reliability (planned)
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Endpoint
     - Target
     - Status
   * - ``POST /api/v1/nudge/throttle``
     - **99.9 %** non-5xx
     - Aspirational; today's stub trivially meets it
   * - ``POST /api/v1/rovo-insights/generate`` (HTTP-side)
     - **99.9 %** non-5xx
     - Aspirational; just enqueues — should be near-perfect
   * - Rovo-Insights generation success (worker-side)
     - **≥ 95 %**
     - Worker → DLQ ratio; will alert when handler is real
   * - SQS DLQ depth (any queue)
     - **0** sustained
     - Page-worthy if non-zero for >10 min

3.2 Latency (planned)
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Endpoint
     - p95 Target
     - Notes
   * - ``POST /api/v1/nudge/throttle``
     - **< 50 ms**
     - Critical — sits in the user-facing nudge render path
   * - ``POST /api/v1/rovo-insights/generate``
     - **< 200 ms** (HTTP-side)
     - Just SQS send; should be cheap
   * - Rovo-Insights worker generation
     - **< 30 s** end-to-end
     - From submit to result-available in cache
   * - ``POST /api/v1/rovo/insights/status`` (poll)
     - **< 100 ms**
     - Redis lookup only

3.3 Throughput (planned)
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Resource
     - Target
     - Notes
   * - WebServer pod
     - **1,000 RPS** sustained
     - Spring async executor: 16 core / 64 max threads
   * - LongRun pod (insight generation)
     - **8 concurrent generations** per pod
     - PR #103 unblocked this via visibility extension
   * - SHWorkers pod (StreamHub events)
     - **500 events / sec / pod**
     - Bounded by upstream AI Gateway

Part 4 — Business KPIs the team tracks (beyond the OKR)
============================================================

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - KPI
     - Today
     - Why it matters
   * - **Acceptance rate** (insertions ÷ interactions)
     - Per-surface
     - Quality signal — distinguishes "user clicked through" from "user benefited"
   * - **Dismiss rate**
     - Per-surface
     - Fatigue signal — too high → adjust throttle weights
   * - **Ignore / non-interaction rate**
     - Per-surface
     - Saturation signal — too high → reduce frequency or improve targeting
   * - **Proactive Fans %** (L4+ engagement in 28d)
     - Cohort
     - Long-term retention proxy
   * - **Throttle effectiveness** (TAP traits)
     - Not yet measured
     - Will land when ``feature/nudge`` real-throttle ships
   * - **Inference quality (LLM evals)**
     - Per-experience
     - Driven by Central AI evaluation framework, fed by PAI invocations

Part 5 — Roadmap by phase
============================

.. list-table::
   :header-rows: 1
   :widths: 18 14 68

   * - Phase
     - Quarter
     - Deliverables
   * - **Stage 1**
     - Q3 FY26
     - Prioritised use cases; Rovo-button ranking improvements; throttling strategy v1; FedAI team support
   * - **Stage 2**
     - Q4 FY26
     - Launch 2-3 new use cases; mature platform capabilities; uplift quality / latency / throughput
   * - **Stage 3**
     - Q1 FY27
     - Scale 1P + 3P proactive interactions

Part 6 — How code-level work maps to the OKR
==================================================

If you are a backend engineer wondering which package to invest your week in,
here is the value-chain map (high → low impact on the OKR):

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Package
     - Impact
     - Why
   * - ``feature/rovoinsights``
     - 🔴 Highest
     - The single biggest invocation lift this half. Production handler not yet ported.
   * - ``feature/nudge``
     - 🔴 Highest
     - Real TAP-trait throttle is the gate to "Stage 2" use-case launches.
   * - ``stratus``
     - 🟠 High
     - Latency + reliability of every LLM call; affects all surfaces
   * - ``task`` + ``sqs``
     - 🟠 High
     - Throughput ceiling for Rovo Insights; PR #103 already gave 8× headroom
   * - ``service/metric``
     - 🟡 Medium
     - Without metric tagging the team cannot debug surface-level acceptance rates
   * - ``featuregate``
     - 🟡 Medium
     - Required for safe rollouts of new surfaces
   * - ``logging``
     - 🟢 Low (but blocking)
     - On-call burden — low absolute priority but blocks others from shipping
   * - ``requestcontext`` / ``interceptor``
     - 🟢 Low (stable)
     - Stable; touch only when correctness gap is identified

Part 7 — Cross-team dependencies the team relies on
======================================================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Team
     - PAI's dependency on them
   * - **AI Gateway**
     - Every LLM call. Latency / availability of AI Gateway directly caps PAI's SLOs.
   * - **Central AI**
     - Owns evaluation framework + LLM model selection. PAI reports invocation outcomes for evaluation.
   * - **AIX (AI Experience)**
     - Owns the in-product UX (nudge surfacing, conversation-starter chips). PAI provides backend.
   * - **Editor AI**
     - Owns Confluence Editor's AI affordances. Co-owner of Summarise Changes.
   * - **Rovo Chat / convo-ai-platform**
     - PAI inherits Rovo Insights logic from convo-ai. Cross-repo coordination required for the port.
   * - **TAP team**
     - Will provide trait/cohort data once throttle integration lands.
   * - **Statsig (FF) team**
     - Feature-flag infrastructure for gated rollouts.

Part 8 — Citations
=====================

Confluence pages that back this chapter:

* `Proactive AI Engineering Deep Dive <https://hello.atlassian.net/wiki/spaces/AM3/pages/6143084752>`_
* `R4 Planning, FY26 H2 <https://hello.atlassian.net/wiki/spaces/proai/pages/6169149742>`_
* `Onboarding Rovo Insights to PAI <https://hello.atlassian.net/wiki/spaces/AM3/pages/6849003562>`_

Service catalog:

* ``service-descriptor.sd.yml`` — single source of truth for resources, alarms,
  retry policies.

People (DRI / contributors per the FY26 H2 R4 doc):

* Brian Feldman (H2 OKR DRI)
* Anthony Manchin (Tech lead)
* Annie Lieu, Zhangbin Cheng, Bo Han, Morin Rodenski (Core contributors)
* Slack: ``#help-ai-experience``
