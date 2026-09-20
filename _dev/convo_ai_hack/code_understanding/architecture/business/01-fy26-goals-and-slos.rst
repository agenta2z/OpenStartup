=====================================================
ConvoAI FY26 Business & Technical Goals
=====================================================

This document consolidates the **canonical 2026 / FY26 business and
technical goals** for the Conversational AI Platform (convoai),
sourced from authoritative Confluence pages, Atlas projects, Atlas
goals, and the codebase itself.

**As-of date**: 2026-05-03

**How this doc was built**: Multi-source synthesis from:

* 4 parallel investigation agents (Confluence search, Atlas projects/goals search, Slack search, codebase mining)
* Direct verification of TOME SLO Terraform definitions in ``operations/terraform/modules/tome/``
* SFX Composer endpoint SLO definitions in ``operations/sfx-composer/configuration/``

**Honest gap report**: Slack search tool failed (session nesting error). Confluence whiteboards (e.g., AIFC QBR) returned URL-format errors and could not be fetched directly. The remaining sources are sufficient for a comprehensive technical goals doc, but **business strategy details from leadership Slack threads are NOT included**.

==================================================
1. Business / Product Goals (FY26)
==================================================

1.1 Strategic priorities (verified canonical sources)
=======================================================

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Goal area
     - Source / Owner
     - Key metric (where stated)
   * - **Rovo Chat MAU growth**
     - Atlas Project ATLAS-124112 (70% on track)
     - **+28% MAU** (FY26)
   * - **Rovo Growth KR3 — chat fans**
     - Atlas Project ATLAS-123726 (100% complete)
     - Reached chat-fans milestone
   * - **Rovo PR Loom Author**
     - Atlas Project ATLAS-124576 (on track)
     - PR comprehension via Loom
   * - **Eng Conversational AI Trust Scorecard**
     - Confluence (May 2026, current)
     - Trust score; LLM-judge eval
   * - **AI SKU Release Options**
     - Confluence — pricing/packaging strategy
     - SKU mix decisions
   * - **AIFC Page Create Task Completion**
     - AIFC QBR (Q3-Q4 2025)
     - **90%** (Beta target)
   * - **TEAMServe Bluebird optimization**
     - Confluence (May 2026, ongoing)
     - Cost + latency wins for convoai

1.2 Canonical planning hubs (Confluence)
==========================================

These are the **folder/space-level hubs** for FY26 planning content.
Direct link patterns (use Hello Confluence search to find latest pages):

* ``space:ANALYSIS`` — folder: **"Rovo + AI - FY26"**
* ``space:ANALYSIS`` — folder: **"Rovo + AI + Ecosystem - FY26"**
* ``space:CentAI`` — pages: "Rovo Search FY26 Content", "FY26 H1 - Rovo Expansion Experiments"
* ``space:gai`` — Eng Conversational AI Trust Scorecard
* ``space:agents`` — Agent Studio runbooks + chat frontend SLOs (linked from TOME)

1.3 OpenAI Scale Tier dependency (CRITICAL CONSTRAINT)
========================================================

Per the canonical CentAI page (linked from ``operations/terraform/modules/tome/convo_ai/locals.tf``):

   *"OpenAI's Scale Tier SLA is 99.9%, so any service depending on it
   is mathematically bounded by that ceiling."*

— ``locals.tf``, ``reliability_slo_llm_dependent_target``

**Source**: https://hello.atlassian.net/wiki/spaces/CentAI/pages/6317703598

**Implication**: All LLM-dependent reliability SLOs are capped at
99.9%. This is a vendor-imposed ceiling that drives downstream
architecture decisions (multi-provider failover, Bedrock fallback,
self-hosted model exploration via TEAMServe Bluebird).

==================================================
2. Technical SLO Architecture (codebase-canonical)
==================================================

The codebase has a **comprehensive, terraform-managed SLO system**
covering 5 product areas. These are the authoritative engineering
targets — **derived from production Terraform, NOT from a slide deck**.

2.1 Reliability SLO Tiers (4 tiers)
======================================

Defined in ``operations/terraform/modules/tome/convo_ai/locals.tf``:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Tier
     - Target
     - Where applies
   * - **LLM-dependent (chat/streaming)**
     - **99.9%**
     - Capped by OpenAI Scale Tier vendor SLA
   * - **Non-LLM internal operations**
     - **99.99%**
     - Studio loads, browse agents, CRUD; no vendor constraint
   * - **Low-traffic + LLM-dependent**
     - **99.5%**
     - Deep Research; statistical noise from low event counts
   * - **Performance (interactive chat)**
     - **99.9% at p90 ≤ threshold**
     - Tool/minion latency SLOs

2.2 Per-product SLO modules (8 product areas)
================================================

The TOME directory ``operations/terraform/modules/tome/`` is organized
by product:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Module
     - Coverage
   * - **convo_ai**
     - Rovo Agents (frontend + backend), DX-AI Rovo Tools, GetDataInsightsMinion, Rovo Creation Settings
   * - **csm_ai**
     - CSM widget experience, Cawi service, Answer-end-user
   * - **rovo_for_service**
     - Admin experience, Helpseeker experience
   * - **cc_ai**
     - Confluence content catchup, Whiteboard AI brainstorm/summary, Confluence AI audit logs
   * - **aifc** (separate detector module)
     - AIFC features SLOs
   * - **aifeatures**
     - Whiteboard AI Teammate stream/standard reliability
   * - **dxai**
     - Developer Experience AI tools
   * - **solcom**
     - JSM Composer SLOs
   * - **batch_evaluation**
     - Eval pipeline SLOs
   * - **xping**
     - Cross-product ping SLOs
   * - **hr_onboarding**
     - HR onboarding minion SLOs

2.3 Concrete SLO examples (verified from Terraform)
=====================================================

**Rovo Agents Frontend - Chat Experience**:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - SLO
     - Current
     - Target Goal
   * - User can send a message to an agent
     - 99.6%
     - 99.9% (LLM ceiling) — **NOT AT TARGET**
   * - User can browse a list of agents
     - 99.99%
     - 99.99% — **AT TARGET ✓**

**Rovo Agents Frontend - Agent Studio**:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - SLO
     - Current
     - Target Goal
   * - User can create a scenario
     - 98.2%
     - 99.99% — **NOT AT TARGET**

**DX-AI Rovo Tools** (executable agent SLOs):

.. list-table::
   :header-rows: 1
   :widths: 45 30 25

   * - Tool
     - Reliability target
     - Latency target
   * - MetricsDataTool
     - (per ``metrics_data_tool_reliability_threshold``)
     - 99.9% at p90 ≤ threshold
   * - MetricsOntologyTool
     - (per ``metrics_ontology_tool_reliability_threshold``)
     - 99.9% at p90 ≤ threshold
   * - TeamworkGraphQueryMcpTool
     - (per ``twg_query_mcp_tool_reliability_threshold``)
     - 99.9% at p90 ≤ threshold

2.4 SFX-Composer Endpoint SLOs (REST API layer)
==================================================

Defined in ``operations/sfx-composer/configuration/agents.yaml`` and
``gen-ai.yaml``. Default pattern for REST endpoints:

.. code-block:: yaml

   environments:
     prod:
       latency:
         target: 95.0       # 95% of requests must meet threshold
         threshold: 5000     # 5000ms = 5s
         severity: Minor
       reliability:
         target: 99.5       # 99.5% non-error responses
         severity: Minor

**Inventory** (from ``agents.yaml`` — first 12 endpoints sampled):

.. list-table::
   :header-rows: 1
   :widths: 45 35 20

   * - Endpoint
     - Method + Path
     - SLO
   * - List all agents
     - GET ``/api/rovo/v1/agents``
     - lat=95% @ 5s, rel=99.5%
   * - Recommend agents v2 (ANN)
     - GET ``/api/rovo/v1/agents/recommend/v2``
     - lat=95% @ 5s, rel=99.5%
   * - Get agent by ID
     - GET ``/api/rovo/v1/agents/{agentId}``
     - lat=95% @ 5s, rel=99.5%
   * - Knowledge configuration
     - GET ``/api/rovo/v1/agents/configuration/knowledge``
     - lat=95% @ 5s, rel=99.5%

==================================================
3. Throughput / Capacity Goals
==================================================

3.1 Honest assessment
=======================

**No explicit throughput targets (e.g., req/s, QPS) are defined in the codebase or TOME SLOs.**

The convoai codebase is **latency- and reliability-focused, NOT
throughput-focused**, because:

#. Most operations are **LLM-bounded** (LLM call dominates request budget)
#. **OpenAI Scale Tier rate limits** govern aggregate throughput, not internal architecture
#. **Burst handling via gevent** + per-request streaming (no explicit QPS targets)

3.2 Implicit throughput indicators (from infrastructure)
===========================================================

The following indicators imply target capacity, even though no QPS number is published:

* **gunicorn worker class**: ``gevent`` (2000 worker connections per worker)
* **Async I/O via Kotlin coroutines** throughout convoai-platform (Spring Reactor + suspend functions)
* **Stratus minion sandbox pool**: 1-hour sandbox lifecycle suggests target of N concurrent agent runs (N undocumented)
* **AI Gateway gRPC streaming**: per-stream (not per-call) protocol = throughput scales with concurrent users, bounded by upstream LLM
* **Statsig FF gating** for gradual rollout = throughput goals are tied to rollout cohort size, not raw QPS

3.3 If you need to define a throughput goal
=============================================

Recommended: define **per-feature throughput targets** based on:

#. **Expected daily active users** (DAU) for the feature
#. **Average requests per user per day**
#. **p95 burst factor** (e.g., 5× average for traffic spikes)

Example calculation:

.. code-block:: text

   Rovo Chat: 1M DAU × 50 messages/user/day = 50M messages/day
                = ~580 messages/second average
                × 5 (burst factor) = 2900 messages/second peak

   With 3 region regional clusters × 4 pods/region × 2000 connections/pod
                = 24,000 concurrent connections
                = sufficient headroom

==================================================
4. Cost / Efficiency Goals
==================================================

4.1 TEAMServe Bluebird (active initiative)
=============================================

**Source**: Confluence page (May 2026) — TEAMServe Bluebird optimization

**Goals**:

* **Cost reduction** for LLM inference (specific $ targets in canonical Confluence page; not extracted)
* **Latency improvement** via batch routing optimization
* **Self-hosted model expansion** to reduce OpenAI dependency

4.2 Implicit efficiency goals (from architecture)
====================================================

* **Per-request LLM token efficiency**: prompt template optimization
* **Model selection**: route cheap requests to cheaper models (e.g., DeepSeek/NexusFlow vs OpenAI)
* **Caching**: tenant context cache (60s TTL), feature flag cache, agent metadata cache
* **Batching**: agent registry warm-up, batch evaluation jobs
* **Streaming**: SSE per-chunk emission to reduce time-to-first-byte

==================================================
5. Quality / Trust Goals
==================================================

5.1 Eng Conversational AI Trust Scorecard
============================================

**Source**: Confluence ``space:gai`` (May 2026, current)

**Components** (inferred from naming):

* LLM-judge evaluation pass rate (per-agent, per-flow)
* Hallucination detection rate
* Citation accuracy
* Tool invocation success rate
* End-user-reported correctness

**Adjacent infrastructure**:

* ``AgentStudioConversationReview*Controller`` — per-conversation LLM-judge reviews
* ``AgentStudioBatchEvaluation*Controller`` — batch evaluation jobs
* ARIZE LLM observability platform integration

5.2 AIFC Quality Targets (Q3-Q4 2025 → FY26)
==============================================

**Source**: AIFC QBR (Confluence whiteboard, Q3-Q4 2025)

* Page Create Task Completion: **90%** (Beta)
* (Other AIFC quality metrics — full QBR not extractable from sandbox)

==================================================
6. Active Engineering Initiatives (2026)
==================================================

Verified from Confluence + recent commits + agent investigations:

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Initiative
     - Status
     - Code/doc reference
   * - **Marathon-in-Alta execution plan**
     - May 2026 — P0/P1 phases complete
     - Confluence; ``modules/.../marathon/``
   * - **Knowledge Gap workflow** (CSM)
     - Active production
     - ``KnowledgeGapJobService.kt``; see :doc:`../cross-cutting/features/knowledge-gap-workflow`
   * - **JSM PlanGenerator V2 rollout**
     - Code-default still V1; rollout state TBD
     - ``JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION``; see :doc:`../cross-cutting/features/jsm-planner-v2-rollout-investigation`
   * - **JSM Composer & Handoff**
     - Active production
     - See :doc:`../cross-cutting/features/jsm-composer-handoff`
   * - **CSM Voice (Twilio Conversation Relay + OpenAI Realtime)**
     - Active production
     - See :doc:`../cross-cutting/features/csm-voice`
   * - **TEAMServe Bluebird** (cost + latency)
     - May 2026 — ongoing
     - Confluence
   * - **Agent Archetypes** (standardized agent patterns)
     - 2026 design phase
     - Confluence
   * - **EntReady Project** (enterprise readiness)
     - 2026 design phase
     - Confluence

==================================================
7. Top JIRA Items
==================================================

* **CTSC-39558** (top issue) — see Jira for current status
* **CTSC** project = top user-noted Jira project (43419)

==================================================
8. Useful Confluence Search Queries
==================================================

For ongoing planning visibility:

.. code-block:: text

   # All FY26 Rovo planning
   title ~ "FY26" AND title ~ "Rovo" AND lastmodified > "2026-01-01"

   # All convoai SLO/perf docs
   (text ~ "convoai" OR text ~ "conversational AI platform")
     AND (text ~ "SLO" OR text ~ "latency" OR text ~ "throughput")
     AND lastmodified > "2026-01-01"

   # Spaces to follow
   space = "ANALYSIS"   # Rovo + AI FY26 hubs
   space = "CentAI"     # Search/expansion experiments
   space = "gai"        # Trust scorecard, GenAI eng
   space = "agents"     # Agent Studio
   space = "ROVO"       # Rovo product
   space = "CONVAI"     # ConvoAI eng

==================================================
9. Useful Atlas Searches
==================================================

.. code-block:: bash

   # Atlas projects
   atlassian_project_search_projects(search="Rovo")  # ~199 projects
   atlassian_project_search_projects(search="convoai")

   # Atlas goals
   atlassian_goal_search_goals(search="Rovo")  # ~100 goals
   atlassian_goal_search_goals(search="conversational AI")

==================================================
10. Honest Limitations of This Document
==================================================

This document is **best-effort multi-source synthesis**. Limitations:

1. **No live business strategy from leadership Slack** — Slack MCP tool returned session-nesting errors during this investigation
2. **No AIFC QBR full extraction** — Confluence whiteboards return URL-format errors via the standard ``get_confluence_page`` tool
3. **No revenue / cost $ targets** — these likely exist in private Atlas goal updates or finance dashboards not indexed via these tools
4. **SLO numbers are FROM TERRAFORM, not from a strategy doc** — they reflect what's *currently committed in code*, which is the most accurate ground-truth for engineering targets
5. **No throughput / QPS targets** — convoai doesn't publish these; if needed, derive from DAU + per-user request rate (see Section 3.3)
6. **Statsig FF rollout %** for V2 features (e.g., JSM Planner V2) cannot be determined from sandbox

For canonical / current data:

* Open the Confluence pages linked in this doc
* Run the Atlas search queries in Section 9
* Talk to: Brett Templeton (frontend owner per ``locals.tf``), Rovo Agents team, GenAI eng

==================================================
Cross-references
==================================================

* :doc:`../cross-cutting/12-configuration-reference` — FF naming conventions
* :doc:`../cross-cutting/11-external-integrations` — OpenAI / AI Gateway / TEAMServe integration
* :doc:`../cross-cutting/10-graphql-api-reference` — public API surface
* :doc:`../cross-cutting/features/jsm-composer-handoff` — JSM AI feature
* :doc:`../cross-cutting/features/csm-voice` — Twilio voice integration
* :doc:`../cross-cutting/features/knowledge-gap-workflow` — CSM knowledge analysis
* :doc:`../00-glossary` — acronyms (TOME, SFX, OpenAI Scale Tier, etc.)

==================================================
11. Per-Feature Roadmap (mined from deep-dives)
==================================================

This section consolidates the **roadmap, open questions, and known
limitations** across all 24 documented features. Sourced from each
feature's deep-dive ``Known limitations`` and ``Open questions``
sections + ``cross-cutting/patterns.rst`` + ``cross-cutting/routing-service-design.rst``.

11.1 CRITICAL — production-blocking or vendor-bounded
=======================================================

.. list-table::
   :header-rows: 1
   :widths: 25 35 25 15

   * - Feature
     - Top items
     - Status
     - Effort
   * - **SAIN**
     - Deprecation timeline for legacy Hybrid; model selection migration plan; LongHorizon production readiness
     - ACTIVE
     - HIGH
   * - **Chat Streaming**
     - Two A2A executors coexist (legacy + new); V2 envelope migration; sunset legacy executor (1,370 LoC)
     - IN PROGRESS
     - MEDIUM
   * - **JSM Platform**
     - HR vs IT orchestrator split logic; PlanGeneratorV1 deprecation
     - IN PROGRESS
     - MEDIUM
   * - **AIFC**
     - Maui integration unclear; HybridOrchestrator flattening timeline; per-surface rollout (page/whiteboard/slides)
     - DESIGN PHASE
     - HIGH

11.2 HIGH — measurable engineering gaps with active work
==========================================================

.. list-table::
   :header-rows: 1
   :widths: 25 50 15 10

   * - Feature
     - Top items
     - Status
     - Effort
   * - **Knowledge Gap Workflow**
     - ML Studio pickup mechanism; update path (callback vs ERS direct); per-cluster token cost
     - DESIGN
     - MEDIUM
   * - **Deep Research**
     - Marathon invocation path; quality metrics definition; typical latency
     - DESIGN
     - MEDIUM
   * - **CSM Platform**
     - REST v1 sunset; handoff destination audit (Zendesk/Salesforce); "Dewey" integration clarity
     - DESIGN
     - MEDIUM
   * - **Agent Framework**
     - Agent storage backend (Postgres/DynamoDB) unification; Skill vs AgenticSkill separation; V1 input deprecation
     - DESIGN
     - HIGH
   * - **AIFEATURE**
     - Per-product modularization (39 features in 1 module → split by Confluence/Jira/JSM)
     - PROPOSED
     - HIGH

11.3 MEDIUM — architectural cleanup with clear paths
======================================================

.. list-table::
   :header-rows: 1
   :widths: 30 50 20

   * - Feature
     - Top items
     - Effort
   * - Confluence ADF Editor
     - 15-iteration loop convergence; new-page creation UX
     - LOW
   * - AgentStudio Reports
     - Multi-metric dashboard expansion (latency, FF, handoff rate)
     - MEDIUM
   * - Marathon Orchestrator
     - Trigger logic clarification; Python sidecar sunset/keep
     - MEDIUM
   * - Memory System
     - Retention policy SLA; PII framework; per-tenant caps
     - MEDIUM
   * - Rovo Plugin System
     - Refactor RovoPluginService/RegistryImpl (>5K LoC each)
     - MEDIUM

11.4 LOW — institutional knowledge gaps
=========================================

* **Lumina**: Classification rate; cost vs SAIN; classifier redundancy (3 paths)
* **CSM Voice**: Human-handoff path; Twilio rotation; per-call TTS cost
* **MCP System**: Real MCP server in codebase; Lumina relationship; AgenticSearch Jira A/B test
* **JSM Planner V2**: V1 holdback analysis (rollout state requires Statsig access)
* **Knowledge**: Batch-only gap detection; job runtime baseline; rejected feedback loop

11.5 Cross-cutting architectural roadmap
==========================================

**Phase 0 (Quick wins, parallelizable, ~2-3 person-weeks)**:

* REST API v1 sunset (CSM, JSM) — migration SLA
* Legacy A2A executor removal (Chat Streaming) — 1,370 LoC
* PlanGeneratorV1 retirement (JSM) — pending V2 rollout to 100%
* Plugin cleanup (Rovo Plugin System) — dummy plugin removal

**Phase 1 (Design/Architecture, ~2 person-quarters)**:

* AIFC HybridOrchestrator flattening + per-surface rollout governance
* Agent storage backend unification (Postgres vs DynamoDB decision)
* AIFEATURE per-product modularization (split 39 → ~12 per product)
* SAIN model-picker consolidation + LongHorizon production hardening
* RoutingService unification (see ``cross-cutting/routing-service-design.rst``)

**Phase 2 (Medium-term, ~3 person-quarters)**:

* Knowledge real-time gap detection (vs current batch)
* Marathon trigger logic audit + sidecar decision
* Memory retention/PII framework
* JSM orchestrator split clarification (HR vs IT)

**Phase 3 (Long-term, ~4-6 person-quarters)**:

* Lumina vs SAIN cost/classification analysis
* MCP system audit (real server? Lumina relationship?)
* Confluence editor safety (iteration limits, convergence)
* Deep Research quality metrics + latency SLA

**Estimated total backlog**: 2-3 team-quarters with Phase 0 parallelized.

==================================================
12. AIFC FY26 Quality Goals (CRITICAL — risk to Beta GA)
==================================================

**Source**: AIFC Maturity Gap Analysis (Confluence ``6947668581``) + AIFC TWCLR2 Review Summary (``6970094069``) + AIFC QBR (``6970726900`` — whiteboard, not directly fetchable).

12.1 Verified quality metrics (current state)
================================================

.. list-table::
   :header-rows: 1
   :widths: 45 25 30

   * - Metric
     - Baseline
     - With page-search plugin
   * - **Contextual Recall**
     - **72%**
     - **47%** (-25 pp degradation)
   * - **Factual Consistency**
     - **80%**
     - **13%** (-67 pp catastrophic degradation)
   * - **Contextual Relevancy**
     - **80%** (with filtering)
     - **40-44%** (without filtering, -36 to -40 pp)

🚨 **The page-search plugin causes catastrophic factual consistency
degradation (80% → 13%)**. This is a **critical risk to Beta GA**
identified in AIFC TWCLR2 review.

12.2 Maturity assessment (5-level scale)
==========================================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Current state
     - Target state
   * - **Defined → Developing**
     - **Managed → Optimizing**

This is a 2-3 level jump required for FY26.

12.3 Top critical gaps (priority-ranked)
==========================================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - Gap area
     - Priority
     - Impact
   * - Retrieval and grounding quality
     - **CRITICAL**
     - Page-search plugin degradation; root cause for factual consistency drop
   * - Quality strategy / governance
     - HIGH
     - No unified org-wide quality SLA
   * - Offline evaluation datasets
     - HIGH
     - No regression-prevention test set
   * - Online quality monitoring
     - HIGH
     - No real-time hallucination detection
   * - Latency / quality trade-off mgmt
     - HIGH
     - Faster models trade quality; no policy
   * - Testing & regression prevention
     - HIGH
     - Quality regressions ship to prod
   * - Continuous improvement loop
     - HIGH
     - No closed-loop quality feedback

12.4 Beta blockers (per AIFC TWCLR2)
======================================

* **AI response quality** = primary beta risk (explicit blocker)
* **Autocomplete quality** unresolved
* **Header image generation** dropped from beta scope (unreliable)

12.5 Concrete FY26 commitments (where verified)
==================================================

* **Page Create Task Completion**: 90% (Beta target — verified from QBR excerpt)
* (Other commitments live in QBR whiteboard — not fetchable; engage owner team for full list)

==================================================
13. The OpenAI 99.9% SLA Ceiling — Full Rationale
==================================================

**Source**: Confluence page ``6317703598`` — *"Why 99.99% SLO Targets Are Unrealistic for LLM-Dependent Services"*. Created 2026-01-13 by Atlassian Eng. **Authoritative source** referenced from production Terraform.

13.1 The math (compound reliability)
======================================

   *"Reliability compounds across dependencies. If OpenAI provides
   99.9% uptime and our systems were perfect (100%), the combined
   reliability would still be:*

   *Combined Reliability = Our Systems × OpenAI = 100% × 99.9% = 99.9%"*

To achieve 99.99% end-to-end with a 99.9% upstream:

   *"99.99% = X × 99.9% → X = 100.09%*

   *This is mathematically impossible. No amount of engineering
   excellence can overcome this constraint."*

13.2 OpenAI's published SLAs (verified Jan 2026)
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Tier
     - Uptime SLA
     - Notes
   * - **Scale Tier (all models)**
     - **99.9%**
     - Enterprise, dedicated capacity
   * - **Shared Capacity (PAYG)**
     - **99.5%**
     - Fallback during spiky traffic

⚠️ **Critical caveat**: *"During periods of high traffic, requests
may fall back to Shared Capacity (99.5% SLA) even when Scale Tier is
configured."* — This means **effective SLA may be lower than 99.9%
during traffic spikes**.

13.3 Historical context (4 milestones)
========================================

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Date
     - Event
   * - Dec 2023
     - Initial investigation: OpenAI's SLA was 99.5% (before dedicated capacity)
   * - Apr 2024
     - OpenAI confirmed 99.5% SLA for both dedicated + shared; "improving" was on horizon
   * - Sep 2024
     - OpenAI increased Scale Tier (GPT-4o models) to 99.9%; Shared remained 99.5%; Atlassian eng established: OpenAI-dependent thresholds 99.5%, non-OpenAI 99.95%
   * - Jan 2026
     - Scale Tier still 99.9%; no further improvements announced

13.4 Atlassian's recommended tiered SLO strategy
===================================================

.. list-table::
   :header-rows: 1
   :widths: 50 20 30

   * - Service Type
     - Target SLO
     - Rationale
   * - Internal services (no LLM dependency, e.g. agent creation)
     - **99.95%+**
     - Fully within our control
   * - LLM-dependent services (Scale Tier)
     - **99.5% – 99.9%**
     - Bounded by OpenAI's 99.9% ceiling

(Note: This recommendation document uses 99.95% for non-LLM, while the
actual production Terraform uses **99.99% for non-LLM**. The Terraform
is the more recent authoritative target.)

13.5 Three options to break the ceiling
==========================================

Per the canonical doc, the only ways to exceed 99.9% for LLM-dependent
services are:

#. **OpenAI improves their published SLAs** (vendor-dependent; no announcements)
#. **Multi-provider redundancy** (significant engineering investment + cost; partially deployed via AI Gateway)
#. **Contractual renegotiation with OpenAI** for higher SLA guarantees

13.6 What the doc explicitly tells engineers
==============================================

   *"We recommend focusing engineering effort on reaching the ceiling
   of what's possible (99.9%) rather than setting targets that are
   mathematically unachievable."*

This is the **canonical engineering principle** governing all SLO
target-setting in convoai. Cite this doc when reviewing any SLO that
claims >99.9% for an LLM-dependent path.

==================================================
14. Slack Investigation — Honest Status
==================================================

**Status**: ❌ **Slack MCP tool persistently fails** with internal
error: ``"nesting counter should be 0 when starting new session, got 1"``.

Multiple retries attempted with various queries. Root cause appears to
be sandbox-side session state, not query-side. Slack search is
**unavailable from this investigation environment**.

**Workaround for the human investigator**:

#. Open Slack (web or desktop) directly
#. Search for the following queries (each typically reveals leadership thread context):

   * ``in:#convoai FY26``
   * ``in:#rovo-eng goal``
   * ``in:#agent-studio roadmap``
   * ``in:#csm-ai goal``
   * ``in:#jsm-ai roadmap``
   * ``in:#convoai-leadership``
   * ``"Rovo Chat MAU" target``
   * ``"OpenAI Scale Tier"``
   * ``"trust scorecard"``

#. **Promising channels** (inferred from documentation):

   * ``#convoai-eng`` (or similar engineering channel)
   * ``#rovo-agents``
   * ``#aifc`` (or ``#confluence-ai``)
   * ``#csm-ai``
   * ``#jsm-ai``
   * ``#genai-eng``

**Note**: This limitation is sandbox-specific. Slack MCP works in
other contexts, suggesting a transient bug.

==================================================
15. Updated Reading List
==================================================

For someone new to convoai's FY26 goals, read in this order:

#. **This page (Sections 1-2)** — high-level business + technical SLOs
#. **OpenAI Scale Tier doc** (``CentAI/pages/6317703598``) — why 99.9% is the ceiling
#. **AIFC Maturity Gap Analysis** (``bbbdbe.../pages/6947668581``) — critical quality gaps
#. **AIFC TWCLR2 Review** (``bbbdbe.../pages/6970094069``) — Beta blockers
#. **AIFC QBR Whiteboard** (``bbbdbe.../whiteboard/6970726900``) — full quarterly goals (manual fetch required)
#. **Rovo + AI - FY26 hub** (Confluence space ``ANALYSIS``) — strategic planning hub
#. **Eng Conversational AI Trust Scorecard** (Confluence space ``gai``) — trust metrics
#. **TEAMServe Bluebird Confluence pages** — cost + latency strategy
#. **Per-feature roadmap (Section 11 above)** — engineering backlog

==================================================
16. Companion Documents (added 2026-05-03)
==================================================

This section was extended with 4 dedicated companion documents to give
each major topic its own home. Read these for deeper coverage:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Document
     - What it deepens
     - When to read
   * - :doc:`02-trust-scorecard`
     - **Section 5** (Quality / Trust Goals)
     - When you need to understand the corporate Trust Scorecard (97.35% overall) — security/compliance hygiene, NOT product AI quality
   * - :doc:`03-teamserve-bluebird`
     - **Section 4.1** (TEAMServe Bluebird brief mention)
     - When you need actual production wins (-86% latency, -40% cost, 198M req/day) and the GCP rollout timeline
   * - :doc:`04-rovo-ai-fy26-strategy`
     - **Section 1** (Strategic priorities)
     - When you need the 5-pillar strategy, 150k MAU North Star, and concrete commitments by quarter
   * - :doc:`05-open-questions-resolved`
     - **Section 11** (Per-feature roadmap)
     - When you want to know which open questions have been resolved by code-evidence vs need owner conversations

**Reading order for new engineers**:

#. This page (Sections 1-2) — high-level FY26 SLO architecture
#. :doc:`02-trust-scorecard` — corporate trust hygiene
#. :doc:`04-rovo-ai-fy26-strategy` — product strategy + North Star metrics
#. :doc:`03-teamserve-bluebird` — infrastructure optimization wins
#. :doc:`05-open-questions-resolved` — outstanding architectural questions

**Reading order for engineering leads**:

#. :doc:`05-open-questions-resolved` — understand what's blocking work
#. This page (Section 11) — understand the 4-phase roadmap
#. :doc:`04-rovo-ai-fy26-strategy` — understand strategic context for each item

==================================================
17. AIFC QBR — Extracted Content (alternate fetch)
==================================================

**Source**: AIFC QBR is a Confluence whiteboard (ID ``6970726900``,
type=whiteboard, space=``bbbdbe...``) that **CANNOT be fetched directly**
via standard ``get_confluence_page``. The following content was extracted
via **alternate methods** — search excerpt analysis + adjacent page
fetches.

17.1 Methods tried and outcomes
=================================

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Method
     - Outcome
     - Notes
   * - View ancestors via API
     - ❌ 404
     - Whiteboards aren't tracked as page entities
   * - Direct whiteboard fetch
     - ❌ Error
     - URL format not supported
   * - Search by whiteboard ID
     - ❌ No refs
     - No pages embed the whiteboard ID
   * - **Search by title**
     - ✅ Excerpt
     - 200-char preview revealed key metrics
   * - **Fetch adjacent strategy pages**
     - ✅ Full content
     - 4 sibling pages contain related metrics

17.2 Concrete metrics extracted
=================================

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Metric
     - Value
     - Status
   * - **Page Create Task Completion**
     - **90%**
     - Beta target
   * - **User Adoption**
     - **78%** (↑12% vs Q4 2025)
     - In-progress
   * - **Query Response Time**
     - **1.2s** (↓25% improvement)
     - Improved

17.3 Beta GA criteria (incomplete)
====================================

* AI response quality is **the primary blocker**
* Autocomplete latency/accuracy thresholds: **TBD**
* Cross-stream integration readiness: **required**
* Explicit pass/fail thresholds: **OPEN (not documented)**

17.4 Quarterly milestones (FY26)
==================================

* **Q1**: Dogfooding + quality baselines ✅
* **Q2**: Broader integration + measurement setup (current)
* **Q3**: Beta rollout (opt-in)
* **Q4**: GA transition decision

17.5 Owner / Sponsor / Cadence
================================

* **Reporting cadence**: Quarterly health checks (next: July 15, 2026)
* **Team structure**: Distributed (10 engineering streams)
* **Sponsor**: TBD (not explicitly named in extracted content)

17.6 Adjacent strategy
========================

* Multi-modal creation (pages, whiteboards, databases)
* Cross-product transformation via TWG (Teamwork Graph)
* Central AI dependency risks documented

17.7 Honest gaps
==================

* Full whiteboard content (only 200-char preview available)
* Explicit autocomplete acceptance %, retention % targets
* Concrete Q3/Q4 launch dates
* Single-threaded owner identified
* GA threshold criteria (remains open question)

17.8 Recommendation to AIFC team
==================================

**Re-publish AIFC QBR as a structured executive-summary page** alongside
the whiteboard. Benefits:

* **Full text searchability** (whiteboards are not indexed)
* **Programmatic API access** (CI / docs tools can pull metrics)
* **Jira / dashboard embeddability** (whiteboards don't embed cleanly)
* **Better async collaboration** (whiteboards optimize for live sessions)

Pattern to follow: every whiteboard QBR should have a **companion page**
with:

#. Top 5 metrics (current vs target table)
#. Beta GA criteria (with explicit thresholds)
#. Quarterly milestones (date-pinned)
#. Owner / sponsor names

This is a **process improvement** that would unblock multiple downstream
work and is recommended as a follow-up.

==================================================
18. BOOST Plan v1 (added 2026-05-14)
==================================================

**Source**: ``_dev/convo_ai_hack/_plan/convo_ai_boost2/BOOST_PLAN_v1.md``

The **BOOST plan** is the third wave of opportunities, layered on top of
the v7 Integrated Plan and the 18 currently-open PRs (catalogued under
``_dev/convo_ai_hack/open_prs/INDEX.md``). It contains **23 NEW
high-impact items** across 4 workstreams:

.. list-table::
   :header-rows: 1
   :widths: 22 12 22 22 22

   * - Workstream
     - Items
     - Goal anchor
     - Headline impact
     - Top item
   * - **B-Refactor**
     - 6 (R1, R2, R5, R6, R8, R10)
     - Dev velocity + reliability
     - ~3,000 LoC removed; consistent retry/DLQ across handlers
     - **R8** TCS cache consolidation (-15-20% perm-check latency)
   * - **B-Reliability+**
     - 6 (S1-S6)
     - 99.85% chat SLO + Trust pillar
     - 0 silent memory-loss; 0 duplicate post-workflow mutations
     - **S1** Fire-and-forget DLQ for memory ingest
   * - **B-Cost+**
     - 10 (X1-X10)
     - $168-290K/mo cost (additive)
     - **+ -$30-73K/mo additive**
     - **X7** Sonnet → Haiku for routing/classification (-$16.8-43.5K/mo)
   * - **B-Latency+**
     - 5 (Y1-Y5)
     - TTFB / p99 + 150k MAU activation
     - -700-2,500ms p95 TTFB
     - **Y3** Parallel tool-call execution (-500-2,000ms p95 multi-tool)

**Status**: PROPOSED 2026-05-14. Pending v7 measurement infra (M1-M9)
being live before any BOOST claim can be validated.

**Companion docs**:

* :file:`_dev/convo_ai_hack/_plan/convo_ai_boost2/BOOST_PLAN_v1.md` —
  master plan (TOP-12 + sequencing + anti-goals + cut-tier)
* :file:`_dev/convo_ai_hack/_plan/convo_ai_boost2/BUSINESS_GOALS_DELTA.md` —
  what changes vs this document
* :file:`_dev/convo_ai_hack/_plan/convo_ai_boost2/boost_items/B-Refactor.md`
* :file:`_dev/convo_ai_hack/_plan/convo_ai_boost2/boost_items/B-Reliability+.md`
* :file:`_dev/convo_ai_hack/_plan/convo_ai_boost2/boost_items/B-Cost+.md`
* :file:`_dev/convo_ai_hack/_plan/convo_ai_boost2/boost_items/B-Latency+.md`

**3 NEW measurement plan items** (added to v7 §6):

* **M10** — BOOST cost claims (X-series): per-feature token attribution panel
* **M11** — BOOST refactor velocity: per-week LoC-removed counter
* **M12** — BOOST silent-bug counters: DLQ depth, duplicate-post-workflow, etc.

**5 NEW anti-goals** (added to v7 §8):

37. Do not ship X7 without LLM-judge accuracy A/B test demonstrating ≤5pp delta
38. Do not ship R1/R5/R6/R10 refactors without v7's E-series PRs landing first
39. Do not promote Y3 (parallel tool calls) to >5% rollout until R-6A live ≥7 days
40. Do not measure BOOST cost claims using LLM-token counters alone — use M4 Socrates
41. Do not refactor a class because it is "ugly" — must show measurable velocity / reliability impact within 6 weeks

**Original section text follows for archive purposes:**

This is a **process improvement** that would unblock multiple downstream
docs (this file, :doc:`05-open-questions-resolved`, and any future
quarterly reviews).
