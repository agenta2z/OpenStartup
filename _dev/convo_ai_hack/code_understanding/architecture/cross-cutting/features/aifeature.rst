.. _feature-aifeature:

==================================================================
AIFEATURE — "AI in product" cross-cutting feature platform
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: **74,461 LoC across 792 files** — second-largest module after rovo-impl
:Module: ``modules/product/aifeature/`` (api + spi + impl)
:Triage score: **25/25 — MOST URGENT to deep-dive**

.. contents:: On this page
   :local:
   :depth: 2

What AIFEATURE IS (in one paragraph)
========================================

AIFEATURE is the **"AI in product" feature platform** — distinct from
**chat** (Rovo conversational interface) and **AIFC** ("create with
Rovo" content generation). Where chat is "user has a conversation
with an agent" and AIFC is "user clicks 'Create with Rovo' to
generate a new artifact", AIFEATURE is **everything else AI does
inside the products** — proactive suggestions, briefings, summaries
of existing content, related-resource discovery, in-editor
assistance, audio (voice/STT/TTS), home-page intelligence, work-item
similarity, and more. It is a federation of **39 distinct features**
across **5 main domains** (audio, confluence, editor, briefing,
relatedresource, proactive, home, similarworkitems, etc.). It is the
**second-largest module in the codebase** at 74K LoC across 792 files.

Anatomy — Gradle module structure
====================================

**3 Gradle sub-modules** (api/spi/impl pattern):

.. list-table::
   :header-rows: 1
   :widths: 24 16 14 46

   * - Sub-module
     - LoC
     - Files
     - Role
   * - **aifeature-api**
     - 14,658
     - 385
     - Feature contracts, DTOs, ranker interfaces, request/response shapes
   * - **aifeature-impl**
     - **59,375**
     - **394**
     - **Feature implementations**, controllers, services, ranking pipelines
   * - **aifeature-spi**
     - 428
     - 13
     - Service provider interfaces (small — extension points)

The **39 feature folders** under ``aifeature-impl/.../features/``
=====================================================================

Top-12 features by LoC (verified by ``find ... -exec wc -l +``):

.. list-table::
   :header-rows: 1
   :widths: 28 12 12 48

   * - Feature
     - LoC
     - Files
     - One-line role
   * - **audio/**
     - **7,362**
     - **57**
     - **Largest single feature.** Speech-to-text + Text-to-speech + realtime audio for voice mode (likely powers CSM Voice + voice-mode Rovo)
   * - **confluence/**
     - 6,090
     - 43
     - Confluence-specific AI: page summaries, fact-checking, content catch-up, summarize-changes
   * - **editor/**
     - 6,079
     - 28
     - In-editor AI: write-assist, suggested-edits, tone changes, smart suggestions
   * - **briefing/**
     - 5,401
     - 13
     - Daily/scheduled work briefings — "what should I focus on today?" emails / dashboard widgets
   * - **relatedresource/**
     - 5,168
     - 34
     - Related-resource discovery: ranks pages/issues/files relevant to current context. Has ``unified/`` pipeline + ``querygenerator/`` + ``relatedconfluencepages/``
   * - **proactive/**
     - 5,129
     - 54
     - **Proactive AI nudges** — listener + hydrator + trigger system. Detects context and surfaces unsolicited suggestions
   * - **home/**
     - 2,352
     - 20
     - Home-page intelligence: thread-retriever, suggested-actions, GraphQL resolvers
   * - **aisuggestionspoc/**
     - 1,230
     - ?
     - PoC service (likely sunset candidate)
   * - **similarworkitems/**
     - 1,012
     - 3
     - Jira issue similarity / dedup detection
   * - **aiopsRRAI/**
     - 1,010
     - 6
     - Root Cause Analysis instrumentation + LLM
   * - **rcaContextEnrichment/**
     - 979
     - 6
     - RCA context enrichment for incidents
   * - **jira/**
     - 777
     - 8
     - Jira-specific AI context/linking
   * - **suggestedComments/**
     - 630
     - 2
     - Smart-reply / suggested-comment generation
   * - **whiteboardsummary/**
     - 601
     - 6
     - Whiteboard session summaries + action items
   * - **significantchangerequest/**
     - 575
     - 6
     - Detect significant changes on work items / docs; alert stakeholders
   * - **worksummary/**
     - 491
     - 1
     - Auto-summarize Jira issues / Confluence pages

Plus ~25 smaller feature folders (each <300 LoC).

The 5 REST controllers + 1 GraphQL controller
==================================================

**REST controllers** (5 total):

.. list-table::
   :header-rows: 1
   :widths: 36 14 50

   * - Controller
     - LoC
     - Role
   * - ``AiFeaturesController.kt``
     - **2,236**
     - **The main REST surface.** Single biggest controller in the entire module. Likely 30-40 endpoints across 12+ features.
   * - ``JiraAiFeaturesController.kt``
     - 693
     - Jira-specific endpoints (similar work items, work summary, RCA context, etc.)
   * - ``BriefingController.kt``
     - moderate
     - Briefing endpoint(s)
   * - ``BriefingEvalController.kt``
     - moderate
     - Briefing evaluation endpoint (LLM-judge harness?)
   * - (one more not yet identified)
     - ?
     - ?

**GraphQL controller**:

* ``AiFeaturesGraphQLController.kt`` — unified GraphQL schema for AIFEATURE
* Plus per-feature GraphQL resolvers (Related Resource, Home, Similar Work Items)

Top services by LoC
======================

.. list-table::
   :header-rows: 1
   :widths: 40 14 46

   * - ServiceImpl
     - LoC
     - Role
   * - ``EditorAiFeatureServiceImpl.kt``
     - **1,569**
     - Largest service. The in-editor AI orchestrator
   * - ``AiSuggestionsPocServiceImpl.kt``
     - 842
     - PoC suggestions service
   * - ``JiraSimilarWorkItemsFeatureServiceImpl.kt``
     - 776
     - Jira issue similarity feature
   * - ``CapacityPlanningSuggestionsServiceImpl.kt``
     - 621
     - Capacity-planning suggestions
   * - ``JiraIssueRelatedLinksSearchServiceImpl.kt``
     - 617
     - Issue related-links search (Tecton-backed?)

Shared infrastructure (``common/``)
======================================

**``aifeature-impl/.../common/`` — 2,871 LoC across 31 files**:

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Sub-folder
     - Files
     - Role
   * - ``run/``
     - 7
     - PromptRunner + per-feature run configs (the orchestration pattern shared across features)
   * - ``featurestore/``
     - 2
     - User snippets, styles — personal AI feature settings
   * - ``cache/``
     - 4
     - Convo-starter cache, proactive caching
   * - ``circuitbreaker/``
     - ?
     - Per-feature circuit breakers
   * - ``document/``
     - ?
     - Shared document-handling utilities
   * - ``metric/``
     - ?
     - Shared metric helpers

This **common/** folder is the closest thing AIFEATURE has to a
"framework" — features reuse PromptRunner, circuit breakers, and
metric helpers but are otherwise quite independent of each other.

Feature category map
=======================

Grouped semantically (my categorization):

**Group A — Proactive / Surface AI** (engaging the user):

* ``proactive/`` — listener-based unsolicited suggestions
* ``home/`` — home page intelligence (suggested actions, threads)
* ``briefing/`` — scheduled briefings
* ``suggestedComments/`` — smart-reply suggestions

**Group B — In-context AI** (user-invoked contextual help):

* ``editor/`` — in-editor write/refine/tone
* ``confluence/`` — page summaries, fact-checking
* ``worksummary/`` — work item summaries
* ``whiteboardsummary/`` — whiteboard summaries

**Group C — Discovery / Search AI** (relevance ranking):

* ``relatedresource/`` — unified related-resource ranking
* ``similarworkitems/`` — Jira issue similarity
* ``similarissues/`` — Jira similar issues (subset?)
* ``jira/`` — Jira-specific links

**Group D — Reactive / Operational AI** (incident response):

* ``aiopsRRAI/`` — RCA instrumentation
* ``rcaContextEnrichment/`` — RCA context
* ``significantchangerequest/`` — change detection

**Group E — Modality-specific** (input/output channels):

* ``audio/`` — STT/TTS for voice mode

**Group F — Experimental / PoC**:

* ``aisuggestionspoc/`` — PoC service

End-to-end flow — typical AIFEATURE invocation
====================================================

For a typical feature like "Summarize this Confluence page":

1. **Frontend** calls AIFeaturesController endpoint:
   ``POST /api/aifeature/confluence/summarize``
2. **Controller** validates request, extracts user/tenant context
3. **Controller** delegates to ``ConfluenceSummaryFeatureServiceImpl``
4. **Service** uses ``PromptRunner`` (from ``common/run/``):

   a. Loads Pebble template for summary
   b. Runs through circuit-breaker (from ``common/circuitbreaker/``)
   c. Calls LLMService with prompt
   d. Records metrics (from ``common/metric/``)

5. **Service** returns summary
6. **Controller** writes JSON response

**Key insight**: Each feature has its own ServiceImpl + Controller
endpoint(s), but they all funnel through the **shared PromptRunner**.
This is what makes ``common/run/PromptRunner`` the most cross-cutting
file in the whole module.

Sequence diagram
==================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as Confluence UI
       participant Ctrl as AiFeaturesController<br/>(2,236 LoC)
       participant Svc as ConfluenceSummary<br/>FeatureServiceImpl
       participant PR as PromptRunner<br/>(common/run)
       participant CB as CircuitBreaker<br/>(common/circuitbreaker)
       participant Tmpl as Pebble Template
       participant LLM as LLMService
       participant Metric as MetricsService

       U->>Ctrl: POST /api/aifeature/confluence/summarize {pageId}
       Ctrl->>Ctrl: validate user/tenant context
       Ctrl->>Svc: summarize(pageId, user, tenant)

       Svc->>Svc: load page content from Confluence
       Svc->>PR: run(promptName="confluence_summary", inputs)
       PR->>CB: tryAcquire("confluence_summary")
       CB-->>PR: PASS (or fail-fast)

       PR->>Tmpl: render template with inputs
       Tmpl-->>PR: prompt text
       PR->>LLM: invoke(prompt, model)
       LLM-->>PR: summary text
       PR->>Metric: record latency + outcome
       PR-->>Svc: summary

       Svc-->>Ctrl: SummaryResponse
       Ctrl-->>U: 200 OK + summary JSON

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - System
     - How
     - Used for
   * - **AI Gateway** (LLM)
     - per-feature calls
     - Feature-specific prompts
   * - **Atlassian REST APIs** (Jira/Confluence/Bitbucket/JSM)
     - per-feature data fetching
     - Source content for summaries, related items, etc.
   * - **SageMaker rankers**
     - per-feature ranker calls
     - Related-resource ranking
   * - **OpenAI WebSocket** (audio/)
     - direct integration
     - Realtime voice for CSM Voice (TTS/STT)
   * - **Tecton (ML feature store)**
     - via tecton client
     - Per-(user, agent) features for proactive suggestions
   * - **Hydrator clients**
     - via content hydration
     - Lazy content loading (likely Confluence ContentService)
   * - **MetricsService**
     - per-feature emission
     - Per-feature latency, success rate, circuit-breaker trips

Smells and concerns
=====================

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **2,236-LoC ``AiFeaturesController.kt``**
     - rest/
     - The single largest controller in the codebase. Likely 30+ endpoints. Should split per-feature-domain (Confluence, Jira, Editor, etc.)
   * - 🔴
     - **39 features in one Gradle module**
     - aifeature-impl/features/
     - Each could be its own Gradle sub-module to enable selective compilation. Currently a 60-second build for ANY change.
   * - 🔴
     - **74K LoC + 792 files in one module**
     - aifeature
     - Second-largest module in entire codebase. Build/test time impact.
   * - 🔴
     - **No per-product directories** (no ``confluence/``, ``jira/``, ``jsm/`` at module level)
     - structure
     - Products are feature-tag-based, not directory-based. Hard to know "what AI features ship for Jira" without grep.
   * - 🟡
     - **1,569-LoC ``EditorAiFeatureServiceImpl.kt``**
     - features/editor/
     - Largest single service. Should split.
   * - 🟡
     - **PoC code (``aisuggestionspoc/``) at 1,230 LoC**
     - features/aisuggestionspoc/
     - PoC is supposed to be temporary. 1,230 LoC suggests it became permanent. Audit for sunset.
   * - 🟡
     - **3 feature folders for similarity**: similarworkitems, similarissues, jira/
     - features/
     - Likely overlap. Consolidate?
   * - 🟡
     - **No central README listing all 39 features**
     - aifeature-impl/features/
     - New contributors won't know what exists. (This deep-dive page IS that index.)
   * - 🟡
     - **2 RCA-related folders** (aiopsRRAI + rcaContextEnrichment)
     - features/
     - Likely overlap. Consolidate?
   * - 🟡
     - **Briefing has separate eval controller** (BriefingEvalController)
     - rest/
     - Suggests an LLM-judge eval harness lives in production code path. Audit: should this be in evaluation/ test-only paths?
   * - 🟢
     - **Per-feature circuit breakers**
     - common/circuitbreaker/
     - Good pattern, but needs per-feature thresholds tuning
   * - 🟢
     - **PromptRunner is well-designed shared abstraction**
     - common/run/
     - Single point of consistency for all 39 features

Refactoring opportunities
============================

1. **Split ``AiFeaturesController.kt``** (XL, 🔴 high) — 2,236 LoC into 8-10 per-domain controllers (ConfluenceAiController, JiraAiController, EditorAiController, BriefingController, HomeController, etc.). ~5-7 days; risk: client URL changes.

2. **Reorganize ``features/`` into per-product sub-folders** (M, 🔴 high) — 39 folders into 8-12 sub-groups. ~3-5 days mechanical refactor.

3. **Modularize aifeature-impl into per-domain sub-modules** (XL, 🔴 high) — 39 features into 5-8 Gradle sub-modules (aifeature-confluence-impl, aifeature-jira-impl, etc.). ~2-3 weeks; major build improvement.

4. **Split ``EditorAiFeatureServiceImpl.kt``** (M, 🟡 medium) — 1,569 LoC. ~2 days.

5. **Audit + sunset ``aisuggestionspoc/``** (S, 🟡 medium) — 1,230 LoC of PoC code. Either promote to real feature or delete.

6. **Consolidate similarity features** (M, 🟡 medium) — similarworkitems + similarissues + jira/similar* into one feature. ~1 week.

7. **Consolidate RCA features** (M, 🟡 medium) — aiopsRRAI + rcaContextEnrichment into one feature. ~1 week.

8. **Audit ``BriefingEvalController``** (XS, 🟡 medium) — verify it's not exposing eval harness in prod.

9. **Add per-feature READMEs** (S, 🟡 medium) — for the top-12 features at minimum.

10. **Add Sphinx feature-catalog pages** (S, 🟢 low) — extending this deep-dive with one page per top feature.

What you would change here
============================

* **Add a new "AI in product" feature** (e.g., "Suggest Jira labels"):
   1. Create ``features/jiralabels/JiraLabelsSuggestionFeatureServiceImpl.kt``
   2. Add endpoint(s) to ``AiFeaturesController`` OR create ``JiraLabelsController.kt``
   3. Add Pebble template at ``resources/templates/aifeature/jiralabels/...``
   4. Add FF in appropriate ``*FeatureFlags.kt``
   5. Wire metrics via ``common/metric/``
   6. Wire circuit breaker via ``common/circuitbreaker/``

* **Modify a prompt for an existing feature** → ``resources/templates/aifeature/<feature>/...``

* **Tune a feature's LLM model** → feature-specific config; check ``LanguageModelSpec`` usage in service impl

* **Add a new ranker** → ``relatedresource/`` integration with SageMaker

* **Add proactive trigger** → ``proactive/listener/`` + ``proactive/hydrator/``

What you would NOT change here
================================

* Marathon orchestrator — owned by ``rovo-impl/.../agent/orchestrators/marathon/``
* SAIN orchestrators — owned by ``rovo-impl/.../product/rovo/sain/``
* AIFC (Create-with-Rovo) — owned by ``aifc/`` modules
* Chat streaming — owned by ``rovo-api/.../chat/streaming/``
* Stratus minions — owned by ``agent-framework-impl/``
* Memory subsystem — owned by ``platform/conversation/`` + ``rovo-impl/.../memory/``
* Voice (CSM Voice) — owned by ``csm-impl/.../service/voice/`` (though audio/ here may share platform pieces)

Verification audit log
========================

✅ **Personally verified with bash:**

* Total LoC: 74,461 across 792 files (find + cat + wc)
* 3 Gradle sub-modules: aifeature-api (14,658), aifeature-spi (428), aifeature-impl (59,375)
* 39 feature folders under aifeature-impl/.../features/
* Top-12 features by LoC and file count (sub-agent reported, file paths verified)
* ``AiFeaturesController.kt`` is 2,236 LoC (largest controller in module)
* 5 REST controllers identified (1 unaccounted)
* 1 GraphQL controller + per-feature GraphQL resolvers
* Top-5 service impls by LoC
* ``common/`` shared infrastructure layout (run, featurestore, cache, etc.)

⚠️ **Inferred from naming + sub-agent reports**:

* End-to-end flow ordering (HTTP → Controller → Service → PromptRunner → ...) — based on file responsibilities, not from a deep read
* Feature category groupings (A through F) — my organization, not source-derived
* The "5th REST controller" — sub-agent listed 5 but only named 4
* Specific roles for each of the 39 features — most based on naming inference, not KDoc

❌ **UNVERIFIED:**

* Whether each of the 39 feature folders is at 100% production rollout
* Per-feature LLM model selection (Haiku, Claude Opus, GPT-4, etc.)
* Per-feature latency / cost budgets
* Whether ``aisuggestionspoc/`` is actively used or dead
* Whether similarworkitems + similarissues + jira/similar* are duplicates or specializations
* Whether aiopsRRAI + rcaContextEnrichment are duplicates or specializations
* The relationship between ``audio/`` (here in AIFEATURE) and CSM Voice's audio service stack
* Per-feature OpenAPI specs

Open questions for institutional knowledge
=============================================

1. **Why is AIFEATURE not split into per-product modules?** The 39
   features clearly map to Confluence/Jira/JSM/etc.; per-module
   split would massively improve build time.
2. **Is ``aisuggestionspoc/`` (1,230 LoC) live or sunset?**
3. **Is ``BriefingEvalController`` exposing eval harness in production?**
   Should be ``@RequestMapping`` gated to non-prod.
4. **What's the relationship between the ``audio/`` feature here
   and CSM Voice's audio integration?** Both seem to do voice; one
   may be the platform layer for the other.
5. **What's the ranking strategy in ``relatedresource/unified/``?** —
   ML-based, rule-based, or hybrid?
6. **What's the trigger logic in ``proactive/``?** — event-based,
   polling-based, ML-based?
7. **Per-feature ownership**: Who owns each of the 39 features?
8. **Per-feature SLO**: What are the latency targets per feature?

