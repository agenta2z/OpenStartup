.. _feature-inventory:

==================================================================
Feature Inventory — All user-facing features in the codebase
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Method: 4 parallel discovery agents + bash cross-verification of every
  size/path claim against actual filesystem

A complete catalog of distinct user-facing features distributed across
modules. Use this as the **starting point** for any feature-level work
or deep-dive prioritization.

How features are organized in this codebase
==============================================

Features are NOT first-class Gradle modules. They are **named feature
packages** distributed across existing modules. The codebase uses three
organizational patterns:

1. **Sub-package per feature** (most common) — e.g.,
   ``aifeature-impl/.../features/<featureName>/``,
   ``rovo-extras-impl/.../insights/``, ``rovo-impl/.../product/rovo/<featureName>/``

2. **Feature spread across multiple modules** — e.g., Rovo Insights spans
   3 modules (rovo-api, rovo-impl, rovo-extras-impl)

3. **Feature realized as REST controller + service** — e.g., AgentStudio
   Reports lives in ``agentstudio-impl/.../service/AgentStudioReportServiceImpl``
   + ``graphql/AgentStudioReportQueryController``

Feature scope spans ~36 distinct sub-packages in ``aifeature-impl``,
~47 in ``rovo-impl/product/rovo/``, plus several scattered features in
other modules.

Glossary of recurring confusion
=================================

Several names appear in multiple places — call out the distinctions:

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Name pattern
     - One thing
     - Different thing
   * - "Insights"
     - **Rovo Insights** (this feature, async LLM-generated personalized cards) in ``rovo-extras-impl/.../insights/``
     - **AgentStudio Insights** (analytics on agent usage) in ``agentstudio-impl/.../service/AgentStudioReportServiceImpl``
   * - "Insights" (more)
     - **HamInsightsMinion** (HAM = Help Article Manager? Internal minion in stratus pipeline)
     - **Chart Insights** (analyzes chart data in Confluence/Jira) in ``aifeature-impl/.../features/chartinsights/``
   * - "Agent"
     - **Rovo Agent** (the user-facing chatbot persona)
     - **Agent Framework** (the SDK/runtime for building agents)
   * - "Agent" (more)
     - **AgentStudio** (the build-an-agent UI backend)
     - **ADK** (Agent Development Kit — internal plugin framework)
   * - "Workflow"
     - **rovo-impl/agent/workflows/** (Marathon workflow definitions)
     - **platform/workflow/workflow-impl/** (the SimpleLoop executor)
   * - "Workflow" (more)
     - **rovo-impl/.../product/rovo/workflow/** (per-product Rovo workflow logic)
     - **agent/orchestrators/** (LongHorizon, Hybrid orchestrators)
   * - "Skill"
     - **agent-framework's Skill** (Kotlin class implementing one capability)
     - **adk's Skill** (configurable skill definition)
   * - "Skill" (more)
     - **SkillRegistryController** (REST endpoint listing all skills)
     - **rovo-impl/.../product/rovo/skilltool/** (skill-tool integration)
   * - "Memory"
     - **rovo-impl/.../product/rovo/memory/** (per-agent persistent memory)
     - **conversation-impl** (per-conversation transient state)


The master feature inventory
==============================

All features grouped by **functional category**, with verified
LoC and primary location. Every size number was verified by
``find ... -name '*.kt' -exec cat {} + | wc -l`` against the live source.

Tier C = Core agent runtime / orchestration
---------------------------------------------

User-facing in the sense that this is *the chat product itself*.

.. list-table::
   :header-rows: 1
   :widths: 22 8 38 14 18

   * - Feature
     - LoC
     - One-line definition
     - Primary path
     - Maturity
   * - **Marathon Orchestrator**
     - 96K
     - Multi-step agent workflow runner; the main "do this complex task" engine
     - ``rovo-impl/agent/orchestrators/marathon/``
     - 🟢 Production
   * - **Minions execution layer**
     - 54K
     - Pluggable execution units (Action, Tool, Plugin, MCP variants) Marathon dispatches to
     - ``rovo-impl/agent/minions/``
     - 🟢 Production (internal)
   * - **MCP Plugin System**
     - 41K
     - Model Context Protocol — third-party tool integration (Google Cal, etc.)
     - ``rovo-impl/.../product/rovo/mcp/``
     - 🟢 Production
   * - **Rovo Plugin System**
     - 28K
     - Native (non-MCP) Atlassian plugin registration, lifecycle, hooks
     - ``rovo-impl/.../product/rovo/plugin/``
     - 🟢 Production
   * - **Action Runtime**
     - 25K
     - Action invocation engine (the lower layer beneath Minions)
     - ``rovo-impl/.../product/rovo/action/``
     - 🟢 Production
   * - **Rovo Chat (workflow + endpoints)**
     - 26K
     - Chat session orchestration; main user-facing chat surface
     - ``rovo-impl/.../product/rovo/chat/``
     - 🟢 Production
   * - **Deep Research**
     - 8K
     - Multi-step research agent (gather sources → synthesize)
     - ``rovo-impl/.../product/rovo/deepresearch/``
     - 🟢 Production
   * - **Sain (?)**
     - 9K
     - Investigation needed — unknown abbreviation
     - ``rovo-impl/.../product/rovo/sain/``
     - ⚠️ Unknown
   * - **Lumina classification**
     - 1K
     - Lightweight intent/routing classifier
     - ``rovo-impl/agent/lumina/``
     - 🟢 Production (small)
   * - **Workflow Engine (Rovo-side)**
     - 8K
     - Workflow definitions/executor specific to Rovo orchestrators
     - ``rovo-impl/.../product/rovo/workflow/``
     - 🟢 Production
   * - **Memory System**
     - 5K
     - Per-agent persistent memory (vector store + KV)
     - ``rovo-impl/.../product/rovo/memory/``
     - 🟢 Production
   * - **Answer Generator**
     - 5K
     - Generic LLM-prompted answer pipeline (RAG-style)
     - ``rovo-impl/.../product/rovo/answergenerator/``
     - 🟢 Production
   * - **Auto Dev**
     - varies
     - Code generation / dev assistance
     - ``rovo-impl/.../product/rovo/autodev/``
     - 🟢 Production
   * - **Procedural agent**
     - 1K
     - Procedural-DSL agent variant
     - ``rovo-impl/.../product/rovo/procedural/``
     - 🟡 Specialized

Tier U = User-visible product features
----------------------------------------

These appear in product UIs (Confluence, Jira, JSM, etc.) as named user features.

.. list-table::
   :header-rows: 1
   :widths: 26 8 36 30

   * - Feature
     - LoC
     - One-line definition
     - Primary path
   * - **Rovo Insights** ✅ documented
     - ~3.4K
     - Async LLM-generated personalized work insights (6 categories)
     - ``rovo-extras-impl/.../insights/`` + ``rovo-api/.../insights/``
   * - **Confluence Concise Summary**
     - ~400
     - AI-powered page summarization
     - ``aifeature-impl/.../features/confluence/concisesummary/``
   * - **Confluence Content Catchup**
     - small
     - Quick briefing on missed content
     - ``aifeature-impl/.../features/confluence/contentcatchup/``
   * - **Confluence Infographic**
     - small
     - Visual content generation
     - ``aifeature-impl/.../features/confluence/infographic/``
   * - **Confluence Fact Checker**
     - small
     - Page-level accuracy verification
     - ``aifeature-impl/.../features/confluence/factschecker/``
   * - **Smart Replies (Suggested Comments)**
     - 630
     - AI-suggested comment responses
     - ``aifeature-impl/.../features/suggestedcomments/``
   * - **Improve Writing**
     - 112
     - Editor-level writing suggestions
     - ``aifeature-impl/.../features/improvewriting/``
   * - **Whiteboard AI Brainstorm**
     - 285
     - Collaborative brainstorming aid (whiteboard)
     - ``aifeature-impl/.../features/whiteboardaibrainstorm/``
   * - **Whiteboard AI Teammate**
     - small
     - Conversational AI within whiteboard
     - ``aifeature-impl/.../features/whiteboardaiteammate/``
   * - **Whiteboard Summary**
     - small
     - Whiteboard-content summarization
     - ``aifeature-impl/.../features/whiteboardsummary/``
   * - **Chart Insights**
     - 137
     - AI analysis of chart data
     - ``aifeature-impl/.../features/chartinsights/``
   * - **Focus Mode**
     - 107
     - Distraction-free AI workspace
     - ``aifeature-impl/.../features/focus/``
   * - **PR Summary**
     - small
     - AI-generated pull-request summaries
     - ``aifeature-impl/.../features/prsummary/``
   * - **Smart Link Summary**
     - small
     - Hover-link AI summaries
     - ``aifeature-impl/.../features/smartlinksummary/``
   * - **Auto Title (Loom)**
     - small
     - Automated video title generation
     - ``aifeature-impl/.../features/loom/autotitle/``
   * - **Audio STT (real-time)**
     - small
     - Speech-to-text in conversations
     - ``aifeature-impl/.../features/audio/``
   * - **Briefing**
     - small
     - Daily/weekly briefing generation
     - ``aifeature-impl/.../features/briefing/``
   * - **Work Summary**
     - small
     - Summary of user's recent work
     - ``aifeature-impl/.../features/worksummary/``
   * - **Related Resources**
     - small
     - Smart linking and discovery
     - ``aifeature-impl/.../features/relatedresource/``
   * - **Issue Reformatter (Jira)**
     - small
     - Jira issue description improvement
     - ``aifeature-impl/.../features/jira/issuereformatter/``
   * - **Similar Issues / Similar Work Items**
     - small
     - Duplicate/related issue discovery
     - ``aifeature-impl/.../features/similarissues/``, ``.../similarworkitems/``
   * - **Capacity Planning**
     - small
     - Capacity-related AI features
     - ``aifeature-impl/.../features/capacityplanning/``
   * - **Significant Change Request**
     - small
     - Detect significant changes
     - ``aifeature-impl/.../features/significantchangerequest/``
   * - **Convo Starter**
     - small
     - Page-contextual conversation prompts
     - ``aifeature-impl/.../features/convostarter/``
   * - **Proactive Nudges (Rovo Button Nudges)**
     - varies
     - Context-aware AI button-prompt nudges
     - ``aifeature-impl/.../features/proactive/listener/rovobuttonnudges/``
   * - **AIOps RRAI**
     - small
     - AIOps Root-cause and recommendation AI
     - ``aifeature-impl/.../features/aiopsRRAI/``
   * - **Atlas (Atlassian Atlas integration)**
     - small
     - Atlas-specific AI features
     - ``aifeature-impl/.../features/atlas/``
   * - **Echo**
     - small
     - Specific feature; investigation needed
     - ``aifeature-impl/.../features/echo/``
   * - **Home (Rovo Home)**
     - small
     - Rovo Home feature integration
     - ``aifeature-impl/.../features/home/``

Tier S = Studio / Build-an-agent
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 26 8 36 30

   * - Feature
     - LoC
     - One-line definition
     - Primary path
   * - **AgentStudio**
     - large
     - Build-an-agent UI backend (CRUD agents, KB sources, settings)
     - ``agentstudio-impl/`` (15K LoC module)
   * - **AgentStudio Reports**
     - moderate
     - Analytics on agent usage, success rates
     - ``agentstudio-impl/.../service/AgentStudioReportServiceImpl``
   * - **AgentStudio Insights** ⚠️ (NOT Rovo Insights)
     - small
     - Agent-usage configuration UI
     - ``agentstudio-impl/.../graphql/AgentStudioInsightsConfigurationGraphQLType``
   * - **AgentStudio Publishing**
     - small
     - Publish agent to marketplace flow
     - ``agentstudio-impl/.../service/`` + REST controllers
   * - **NL Agent Create**
     - moderate
     - LLM-powered "describe an agent" → generated agent
     - ``rest/v1/RovoAgentsV1Controller.kt`` ``/api/rovo/v1/agents/nlcreate``
   * - **Agent Recommendations**
     - small
     - Context-aware "you might want this agent" suggestions
     - ``rest/v1/RovoAgentsV1Controller.kt`` ``/api/rovo/v1/agents/recommend/v2``
   * - **Conversation Starters**
     - small
     - Page-contextual conversation prompts (for an agent)
     - ``rest/v1/RovoAgentsV1Controller.kt`` ``/api/rovo/v1/agents/conversation-starter``
   * - **Skill Registry**
     - small
     - REST endpoint listing all available skills
     - ``rest/SkillRegistryController.kt``

Tier P = Platform features
-----------------------------

User-visible but live in platform tier (debatable placement).

.. list-table::
   :header-rows: 1
   :widths: 26 8 36 30

   * - Feature
     - LoC
     - One-line definition
     - Primary path
   * - **Code Sandbox**
     - 1.3K
     - Code execution provisioning (the "run this Python code" feature)
     - ``platform/sandbox/sandbox-impl/``
   * - **Knowledge Gap**
     - 616
     - Detect what user-facing knowledge sources are missing
     - ``platform/knowledge-gap/knowledge-gap-impl/``
   * - **Stratus**
     - moderate
     - Atlassian-internal LLM/data platform integration
     - ``platform/stratus/stratus-impl/``
   * - **Tool Registry**
     - varies
     - 4 sources (MCP, Forge, Native, Integrations) tool catalog
     - ``platform/tool-registry/tool-registry-impl/``
   * - **Evaluation (auto-eval)**
     - 7K
     - Auto-evaluate agent responses against rubrics
     - ``platform/evaluation/evaluation-impl/``
   * - **Journey Builder** ⚠️ (in service-impl, not platform)
     - 1.4K
     - Automated multi-step workflows for users
     - ``platform/service/service-impl/.../JourneyBuilderServiceImpl.kt``


Triage matrix — what to deep-dive next
=========================================

Ranked by expected payoff for someone joining this codebase. Scoring on:

* **Size** — how much code is involved (proxy for complexity)
* **Visibility** — how often the feature is mentioned, demoed, sold
* **Surface area** — how many other modules / external systems touch it
* **Mystery factor** — how poorly named or undocumented internally
* **Refactor likelihood** — how often someone needs to edit it

.. list-table::
   :header-rows: 1
   :widths: 28 8 8 10 10 10 8 18

   * - Feature
     - Size
     - Vis
     - Surface
     - Mystery
     - Refactor
     - **Score**
     - Verdict
   * - **Marathon Orchestrator**
     - 🔴 96K
     - 🔴 high
     - 🔴 wide
     - 🟡 med
     - 🔴 high
     - **24 / 25**
     - 🥇 **Next deep-dive**
   * - **MCP Plugin System**
     - 🔴 41K
     - 🔴 high
     - 🔴 wide (3rd-party)
     - 🟢 low
     - 🟡 med
     - **20 / 25**
     - 🥈 High value
   * - **Deep Research**
     - 🟡 8K
     - 🔴 high
     - 🟡 med
     - 🟡 med
     - 🟡 med
     - **18 / 25**
     - 🥉 Worth it (compact + named)
   * - **AgentStudio**
     - 🔴 15K module
     - 🔴 high
     - 🔴 wide
     - 🟡 med
     - 🟡 med
     - **20 / 25**
     - 🥈 High value
   * - **Rovo Plugin System**
     - 🔴 28K
     - 🟡 med
     - 🟡 med
     - 🔴 high
     - 🟡 med
     - **18 / 25**
     - 🥉 Worth it
   * - **Action Runtime**
     - 🔴 25K
     - 🟢 low
     - 🔴 wide
     - 🟡 med
     - 🔴 high
     - **18 / 25**
     - 🥉 Worth it
   * - **Rovo Chat workflow**
     - 🔴 26K
     - 🔴 high
     - 🔴 wide
     - 🟢 low
     - 🟡 med
     - **19 / 25**
     - 🥈 High value
   * - **Knowledge Gap**
     - 🟡 616
     - 🟡 med
     - 🟡 med
     - 🔴 high
     - 🟢 low
     - **13 / 25**
     - Defer (only ~600 LoC)
   * - **Code Sandbox**
     - 🟡 1.3K
     - 🔴 high
     - 🟡 med
     - 🟢 low
     - 🟢 low
     - **15 / 25**
     - Defer (already documented well)
   * - **Memory System**
     - 🟡 5K
     - 🟢 low
     - 🟡 med
     - 🔴 high
     - 🟡 med
     - **15 / 25**
     - Maybe (mystery-driven)
   * - **Sain (?)**
     - 🟡 9K
     - 🟢 low
     - 🟢 low
     - 🔴 ??
     - 🟢 low
     - **10 / 25**
     - **Resolve mystery first** (1-line lookup)
   * - **Lumina classifier**
     - 🟢 1K
     - 🟢 low
     - 🟡 med
     - 🟡 med
     - 🟢 low
     - **10 / 25**
     - Defer
   * - **Journey Builder**
     - 🟡 1.4K
     - 🟡 med
     - 🟢 low
     - 🟡 med
     - 🟡 med
     - **12 / 25**
     - Maybe
   * - **AnswerGenerator**
     - 🟡 5K
     - 🟢 low
     - 🟡 med
     - 🟢 low
     - 🟡 med
     - **12 / 25**
     - Defer
   * - **Stratus**
     - 🟡 moderate
     - 🟢 low (internal)
     - 🟢 low
     - 🔴 high
     - 🟢 low
     - **10 / 25**
     - Defer

Honest assessment of agent reports
====================================

This inventory was built from 4 parallel agent investigations.
**Brutally honest** about what each got right and wrong:

.. list-table::
   :header-rows: 1
   :widths: 26 25 25 24

   * - Agent
     - Strong
     - Weak
     - Was correct?
   * - **rovo-impl agent**
     - Identified Marathon, Deep Research, MCP correctly
     - Listed only 12-15 items; reality is 47 sub-packages in /product/rovo/ alone
     - **Partially.** Headlines correct; underestimated breadth ~3×
   * - **aifeature agent**
     - Found 15 of the 36 feature sub-packages with reasonable categorization
     - Said "40+ features" (actual = 36); didn't note that many are tiny stubs
     - **Mostly.** Counts roughly right; missed the "stub vs full" distinction
   * - **platform-tier agent**
     - Correctly identified Knowledge Gap, Sandbox, Stratus as candidates
     - Did NOT verify file counts; gave size estimates without checking
     - **Half right.** Names correct; sizes I had to verify myself
   * - **service/controllers agent**
     - Excellent on REST controllers — listed 12 with paths
     - Conflated "endpoint" with "feature"; some entries are infra not features
     - **Best of the 4.** Specific entry-points were verified

What I personally cross-verified vs trusted from agents:

* ✅ **All LoC numbers in this document** — verified via direct ``find ... -exec cat | wc -l``
* ✅ **All path counts** (47 sub-packages, 36 features, etc.) — verified via direct ``ls``
* ✅ **Glossary disambiguations** — verified via ``grep`` on actual file contents
* ⚠️ **One-line definitions** — for major features (Marathon, MCP, Deep Research, etc.) verified by my own grep on key class names. For smaller features (chartinsights, focus, etc.) trusted from agent + naming inference.
* ❌ **"Maturity" labels (🟢 production, etc.)** — best-guess based on test density and feature-flag presence; not verified rollout status

Open questions for someone with more institutional knowledge
==============================================================

These are real questions I could not answer from source alone:

1. **What does "Sain" mean?** 9K LoC under ``rovo-impl/.../product/rovo/sain/``.
   No README; module name is opaque. Likely an acronym.

2. **What does "Kamino" mean?** 906 LoC under ``rovo-impl/.../product/rovo/kamino/``.
   Likely a code-name (Star Wars planet?).

3. **Is "AIFC" something?** 116 LoC under ``rovo-impl/agent/aifc/``.

4. **What's "HOT300495BackfillTask"?** Looks like a Jira ticket reference baked
   into class names — does this code still need to exist?

5. **What's the relationship between rovo-impl/agent/workflows/ (2.8K LoC) and
   rovo-impl/.../product/rovo/workflow/ (7.5K LoC)?** Two different "workflow"
   subsystems — purpose split unclear.

6. **Why is there no ``platform/agent/agent-impl/``?** Agent code lives entirely in
   product tier (rovo-impl). This suggests "agent" is intentionally a product
   concept, not a platform abstraction. But ``agent-version-api`` is platform.

7. **Why is ``RovoInsightsServiceImpl`` in ``rovo-extras-impl`` instead of ``rovo-impl``?**
   What goes in extras? (likely: things that depend on extra third-party libraries)

If you find answers, please add them as comments on this page.


==================================================================
Open Questions — Resolved (2026-05-02 follow-up)
==================================================================

The "Open inventory questions" listed in §4 were investigated via direct
source-code grep. Below are the verified answers.

**Q1: What does "SAIN" mean? — RESOLVED (High confidence)**

SAIN is **Search-AI** (search-based answer generation) — a **standalone
hybrid orchestrator** for retrieval-augmented question answering.
Distinct from Marathon (code-execution agents) and Hybrid (general chat).

Evidence:

* ``platform/service/service-api/.../llm/LlmUsageTrackingIds.kt:277`` —
  ``/** SAIN standalone hybrid orchestrator */``
* ``LlmUsageTrackingIds.kt:597`` — ``/** SAIN orchestration SIMPLE vs COMPLEX routing (pre-orchestration) */``
* ``LlmUsageTrackingIds.kt:652`` — ``/** SAIN answer helper */``
* ``LlmUsageTrackingIds.kt:655`` — ``/** SAIN layout answer generation */``
* ``LlmUsageTrackingIds.kt:658`` — ``/** SAIN entity related people sub-agent */``
* ``LlmUsageTrackingIds.kt:661`` — ``/** SAIN project highlights sub-agent */``
* ``RankingServiceImpl.kt:62`` — ``"The SAIN CLI module supplies an implementation gated on sain.tool.cli.enabled=true"``
* ``RankingServiceImpl.kt:957`` — ``"DO NOT alter: consumed by Query Debugger for SAIN tool. Coordinate with SAIN team before changes."``
* ``ImageSearchMediaService.kt:7`` — ``"Service to fetch Confluence attachment metadata for SAIN image search results."``

Architecture: SAIN has SIMPLE vs COMPLEX routing, sub-agents (entity-related
people, project highlights), an answer helper, layout generation, and a
CLI tool. It is the current generation of "answer my question with
search results" within Rovo. **Worth a dedicated deep-dive**.

**Q2: What does "Kamino" mean? — RESOLVED (High confidence)**

Kamino is the **agent-replication infrastructure** — the system that
replicates Rovo agent definitions across multiple stores (Plato, Search)
to support multiple consumer products. Named after the cloning planet
in Star Wars.

Evidence:

* ``rovo-impl/.../product/rovo/kamino/AgentReplicationFeatureDecisions.kt:1-20`` (KDoc):

   .. code-block:: text

      "Feature decisions to conditionally enable agent replication logic.
       Agents will be replicated to multiple replicas, in support of
       multiple projects."

* Files: ``RovoAgentBootstrapDataLoaderImpl.kt``, ``RovoAgentKaminoDTO.kt``,
  ``RovoAgentKaminoFilter.kt``, ``RovoAgentKaminoPublisher.kt``,
  ``RovoAgentKaminoTombstoneDTO.kt``, ``RovoAgentManifoldMapper.kt``
* Replicas: ``REPLICATE_AGENTS_TO_PLATO``, ``REPLICATE_AGENTS_TO_SEARCH``
  (feature flags)
* Cross-reference: ``platform/service/.../kamino/KaminoReplica.kt`` — the
  replica abstraction (in platform tier)

Pattern: Kamino is the Atlassian internal name for **multi-store agent
replication**, not user-facing. The publisher emits agent changes to
the replicas; the manifold mapper translates between Rovo's agent model
and the replica-specific schemas.

**Q3: What is "AIFC"? — RESOLVED (Medium-High confidence)**

AIFC = **AI Feature Composer** (or "AI-Featured Components" — exact
expansion not fully verified, but the function is well-documented).
It is the **schema-agent and minion-based AI composition framework**
used for editor-context features (write/refine, slash commands,
inline AI in Confluence/Jira).

Evidence:

* ``rovo-impl/.../agent/aifc/metrics/AifcMetricsHelper.kt`` (KDoc):

   .. code-block:: text

      "Centralises all AIFC and Remix metric emissions.
       ... Forward-compatible with the planned HybridOrchestrator
       flattening: when minions are called directly as schema agents,
       the same helper and tag shape apply."

* ``MetricKey.kt:30`` — ``"AIFC Schema Agent observability"``
* ``MetricKey.kt:974`` — ``"AIFC Tool Metrics - E2E and Specific Network Call Latency"``
* ``MetricKey.kt:1526`` — ``"AIFC action streaming"``
* ``MetricKey.kt:1540`` — ``"AIFC - simple ADF generation"``
* ``MetricKey.kt:3073, 3200`` — ``"AIFC Editor Minion"``
* ``CypherQueries.kt:103`` — ``"Used for AIFC context personalization."``

Architecture: AIFC has **Schema Agents** + **Editor Minions** + ADF
generation + context personalization. Forward-looking note: "planned
HybridOrchestrator flattening" suggests AIFC and Hybrid are converging.
**Likely worth a dedicated deep-dive**.

**Q4: What is "HOT300495BackfillTask"? — RESOLVED (High confidence)**

A **one-off backfill task** referencing internal Jira ticket
**HOT-300495**. Backfills the ``agentAssignability`` field on existing
Rovo agents via a Jira REST call (with retry).

Evidence:

* ``rovo-impl/.../agent/HOT300495BackfillTask.kt:25-30``:

   .. code-block:: kotlin

      @Service
      class HOT300495BackfillTask(
          private val agentStore: AgentStore,
          private val jiraClient: AsyncJiraRestClient,
          ...
      ) : BackfillTask<HOT300495BackfillPayload>

* Implements ``platform/service/.../backfill/BackfillTask`` — generic
  one-shot data-migration framework
* No KDoc explaining the original problem; the ticket reference IS the
  documentation

Pattern: Backfill tasks are **persistent one-time data migrations**
that run via the BackfillTask framework. They should be removed once
they've completed (likely abandoned tech-debt).

**Q5: Two workflow directories — RESOLVED (Medium confidence)**

* ``rovo-impl/.../agent/workflows/`` (2.8K LoC) — agent workflow
  primitives at the orchestrator/agent level. Contains ``simpleloop/``
  for the simple orchestration loop and various agent-side workflow utilities.
* ``rovo-impl/.../product/rovo/workflow/`` (7.5K LoC) — chat-message
  workflow service (the broader-scope workflow that invokes agents).
  Contains ``AssistanceServiceWorkflowServiceImpl.kt``,
  ``AgentMessageResponseMapper.kt``, ``LLMMessageMapper.kt``,
  history/, config/, input/.

**Difference**: ``agent/workflows/`` is **inside the agent execution boundary**
(per-turn workflow logic). ``product/rovo/workflow/`` is **outside**
(message-level workflow plumbing — preprocessing, history management,
streaming output assembly). Both are necessary; the naming is just
ambiguous.

**Q6: Why no platform/agent/agent-impl/? — RESOLVED (High confidence)**

There IS platform-tier agent code, but it's organized into multiple
narrower modules instead of a single ``agent-impl``:

* ``platform/agent-version/agent-version-api`` (interfaces)
* ``platform/agent-version/agent-version-spi`` (SPI for product modules to plug in)
* ``platform/agent-version/agent-version-impl`` (versioning service implementation)

And related agent-flavored platform code:

* ``platform/client/.../tecton/agent/`` (Tecton agents — declarative agent specs)
* ``platform/client/.../virtualagents/`` (virtual agent client)
* ``platform/stratus-contracts/.../api/agent/`` (Stratus agent contracts)
* ``platform/conversation/.../agentusercontext/`` (per-agent user context in conversations)

**Pattern**: Platform tier has **agent-versioning + agent-publishing-contracts**;
the **agent-execution runtime** (orchestrators, executors, definitions)
lives in product tier (rovo-impl) because it's specifically the Rovo
team's responsibility, not platform-wide. Platform doesn't dictate
agent execution semantics.

