.. _feature-sain:

==================================================================
SAIN — Search-AI standalone hybrid orchestrator
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 9,268 main LoC across 41 files in 1 sub-package + cross-cutting plugin/CLI integration
:Module: ``rovo-impl/.../product/rovo/sain/``
:Authoritative source: `LongHorizon in SAIN — Feature Scope Design <https://hello.atlassian.net/wiki/spaces/~7120203a24768d69994fd084c94344792734e1/pages/6826296752>`_
:Related living doc: ``modules/product/rovo/rovo-impl/.../sain/orchestrator/longhorizon/DESIGN_NOTES.md``

.. contents:: On this page
   :local:
   :depth: 2

What SAIN IS (in one paragraph)
==================================

SAIN is the **Search-AI orchestrator family** — a set of orchestrators
specialized for **retrieval-augmented question answering** with citation
support. Distinct from Marathon (code-execution agents) and AgentStudio
(custom agents). SAIN composes search results, classifier-driven SIMPLE
vs COMPLEX routing, sub-agents (Confluence, Jira, People, Image Search,
URL Read), and answer generation with citation tagging into a low-latency
search-answer pipeline. Three orchestrator variants exist: **Hybrid**
(legacy), **StandaloneHybrid** (current production), and **LongHorizon**
(SAIN-LH — bounded multi-iteration tool-using extension).

The "AI" in SAIN refers to **citation-cognizant LLM answer generation**;
the "Search" refers to retrieval; the "standalone hybrid" refers to a
self-contained orchestrator that does not require Marathon's Python
sandbox infrastructure.

Anatomy — where the code lives
=================================

Single sub-package: ``rovo-impl/.../product/rovo/sain/``

**Sub-package breakdown** (verified totals):

.. list-table::
   :header-rows: 1
   :widths: 20 12 10 58

   * - Sub-package
     - LoC
     - Files
     - Role
   * - **orchestrator/**
     - **6,378**
     - 22
     - Three orchestrator agents (Hybrid, StandaloneHybrid, LongHorizon) + system prompt generators + streaming handlers + citation processor + skills provider + factory
   * - **mcp/**
     - 784
     - 10
     - SAIN-specific MCP tool definitions
   * - **executor/**
     - 502
     - 3
     - SAINExecutor — entry-point dispatcher into orchestrators
   * - **plugin/**
     - 493
     - 2
     - People-data provider for SAIN plugin lookup
   * - **cache/**
     - 380
     - 1
     - SAINWorkflowCacheImpl — global answer cache (4 hr TTL)
   * - **permission/**
     - 262
     - 2
     - SAINPermissionService — per-tenant access controls
   * - **answergenerator/**
     - 51
     - 1
     - Stream message buffer factory
   * - **TOTAL**
     - **9,268**
     - **41**
     -

Plus 2 top-level files:
* ``SainServiceImpl.kt`` (entry-point service, 70 LoC)
* ``SainRequestTransformer.kt`` (324 LoC) — request mapping between REST DTO and internal types

**Top-level files by LoC** (the complexity hotspots):

.. list-table::
   :header-rows: 1
   :widths: 56 12 32

   * - File
     - LoC
     - Role
   * - ``SainStandaloneHybridOrchestratorAgent.kt``
     - **1,908**
     - **Largest file in SAIN**. The current production orchestrator. Streaming handoff, step-result aggregation, individual-agent execution
   * - ``SainOrchestratorSystemPromptGeneratorImpl.kt``
     - 901
     - System prompt assembly per turn — context injection, persona, capabilities, tools description
   * - ``SainLongHorizonOrchestratorAgent.kt``
     - 699
     - SAIN-LH: low-latency multi-iteration agent with bounded budget (5-15s target, 2 min p95 safety net)
   * - ``SainStandaloneHybridOrchestratorStreamingHandler.kt``
     - 580
     - Streaming-event router for the StandaloneHybrid path
   * - ``DirectSainHybridOrchestratorConfigFactory.kt``
     - 514
     - Per-request config assembly (model picks, tool selection, prompt overrides)
   * - ``SainHybridOrchestratorAgent.kt``
     - 499
     - Legacy Hybrid orchestrator (predecessor; still active behind FF)
   * - ``SAINExecutorImpl.kt``
     - 394
     - Top-level dispatcher; routes between Hybrid / StandaloneHybrid / LongHorizon
   * - ``SAINWorkflowCacheImpl.kt``
     - 380
     - Redis-backed global answer cache; cache-key includes contentful ARIs
   * - ``PeopleDataProvider.kt``
     - 368
     - People-search plugin data provider

The 3 SAIN orchestrators
===========================

This is the most important architectural fact: **SAIN has THREE distinct
orchestrators**, not one. They share the SAIN namespace + cache + permission
infrastructure but have different execution semantics. Routing among them
is done by ``SAINExecutorImpl`` based on agent config + classifier
output + feature-flag gates.

.. list-table::
   :header-rows: 1
   :widths: 20 22 22 36

   * - Orchestrator
     - Status
     - Use case
     - Key features
   * - **Hybrid** (``SainHybridOrchestratorAgent``)
     - Legacy (still active behind FF)
     - Original SAIN path
     - SIMPLE/COMPLEX classifier (``SainOrchestrationComplexityClassifier``), Confluence routing guidance, ``ReadyToAnswerTool``
   * - **StandaloneHybrid** (``SainStandaloneHybridOrchestratorAgent``) — **1,908 LoC**
     - **Current production**
     - General SAIN questions
     - Self-contained (no AssistanceService dependency); per-step result containers; trace-writer integration; sub-agent fan-out (JiraToolLoop, MultiPartUrlRead, Action, Plugin)
   * - **LongHorizon** (``SainLongHorizonOrchestratorAgent``)
     - Active rollout (SAIN-LH)
     - Multi-iteration tool-using QA
     - Filesystem-based scratchpad (``LongHorizonFileSystemFactory``), subagent flattening (``LongHorizonSubagentFlatteningService``), 5-15s target / 2 min p95 budget

**Critical insight**: "LongHorizon" is NOT a separate top-level executor
— it is **SAIN's iterative tool-using path**. The earlier inventory's
"3 orchestrators (Marathon, Hybrid, LongHorizon)" was misleading;
the actual taxonomy is:

.. code-block:: text

   Top-level executors:
   - MarathonAgentExecutor (the only one) → routes by agent config to:
        * Marathon orchestrator (code execution in Python sandbox)
        * SAIN orchestrators (search-answer):
              - Hybrid              (legacy, FF-gated)
              - StandaloneHybrid    (current production)
              - LongHorizon         (multi-iteration tool-using; aka SAIN-LH)
        * AgentStudio agent execution (for user-built agents)

The SIMPLE vs COMPLEX classifier
===================================

``SainOrchestrationComplexityClassifier`` is a pre-orchestration step
that decides whether a SAIN turn is SIMPLE (can be answered directly
without tool calling) or COMPLEX (requires tool calls + multi-step
reasoning). Used by Hybrid orchestrator to choose between fast-path
and full orchestration. **LlmUsageTrackingId**: ``SAIN orchestration
SIMPLE vs COMPLEX routing (pre-orchestration)``.


SAIN-LH (LongHorizon) — the production-ready learning frontier
==================================================================

SAIN-LH deserves its own section because it has unique design
constraints captured in the ``DESIGN_NOTES.md`` living document:

**Latency target**: 5–15s normal case (3–5 iterations).
**Safety nets**: ``totalBudgetMs=2m``, ``toolExecutionTimeoutMs=30s`` (p95 only).

This is **NOT a deep-research path**. SAIN-LH is positioned as
low-latency. The wide budget exists only to prevent the rare slow
turn from failing. Design cuts (no context compaction, no quality
reflection, no resumption) all assume the steady-state is fast.

**Tool loading — TWO mechanisms in parallel**:

1. **Mechanism A** — ``AsyncJiraLongHorizonClient`` (already-flat API tools)

   * 159 ``@LongHorizonCallable``-annotated suspend methods on the interface
   * ``LongHorizonToolAdapter`` reflects over the interface at Spring startup
     and registers each method as an ``LhMcpTool`` in ``toolsByName``
   * ``flattenedTools(selectedAgentNames)`` filters by namespace prefix

2. **Mechanism B** — ``JiraSchemaAgent`` (composite agent, flattened)

   * ``SchemaAgent`` with own schema + behavior
   * ``LongHorizonSubagentFlatteningService.prepareFlattenedSchemaAgentArtifacts``
     extracts per-operation tools from the agent's internal schema
   * Used by SAIN hybrid orchestrator behind ``SAIN_JIRA_AGENT_V2`` FF

**SAIN-LH uses BOTH mechanisms** — strict parity with full LongHorizon.
The only SAIN-LH-specific scoping is ``agentFlattenAllowlist`` (P0
bounded set: ``"JiraAgent"``, ``"ConfluenceAgent"``, ...).

**Why two loaders behind a feature flag?** Local e2e validation
(2026-04-21) revealed: when staging ``ai-3p-connector`` is intermittently
5xx, ``LongHorizonOrchestratorAgentLoaderImpl`` hard-fails, degrading
``schemaAgents`` to ``emptyList()`` — the LLM then has no Jira tools
and answers go empty. The legacy ``OrchestratorAgentLoaderImpl`` provides
a safe fallback. Hence ``LONG_HORIZON_AGENT_LOADER_DECOUPLING`` FF gates
which loader is the primary, with the other as backup.

The 40+ SAIN feature flags
=============================

``SAINSpecificFeatureFlags`` enum has **40+ entries** controlling:

**Orchestrator routing**:

* ``SAIN_DIRECT_HYBRID_ORCHESTRATOR`` — direct path
* ``SAIN_STANDALONE_HYBRID_ORCHESTRATOR`` — current production path
* ``SAIN_HYBRID_ORCHESTRATOR_FORCE_TOOL_USAGE`` — force tool use even on SIMPLE
* ``SAIN_STANDALONE_FORCE_TOOL_USE`` — same for standalone
* ``SAIN_HYBRID_ORCHESTRATOR_ENABLE_URL_READ_TOOL`` — toggle URL read

**Sub-agent integration**:

* ``SAIN_HYBRID_ORCHESTRATOR_ENABLE_3P_RESEARCH_AGENT`` — 3rd-party research agent
* ``SAIN_HYBRID_ORCHESTRATOR_ENABLE_IMAGE_SEARCH_AGENT`` — image search agent
* ``SAIN_IMAGE_SEARCH_NATURAL_LANGUAGE_AGENT`` — NL image search

**Citation system**:

* ``SAIN_HYBRID_ORCHESTRATOR_DISABLE_LLM_CITATION`` — disable LLM-emitted citations
* ``SAIN_PREFER_THIRD_PARTY_CITATION_EXPERIMENT`` — 3rd party citation preference
* ``SAIN_TOOL_MESSAGE_GLOBAL_CITATION_INDEX`` — global citation indexing
* ``SAIN_GLOBAL_CITATION_INDEX_EXP`` + ``SAIN_GLOBAL_CITATION_INDEX_CUSTOMER_EXP`` — A/B
* ``SAIN_HYBRID_ORCHESTRATOR_CITATION_DEBUG_HELLO_ONLY`` — internal-team-only citation debug
* ``SAIN_CITATION_FIX_PROMPT`` — citation prompt fix experiment

**Cache control**:

* ``SAIN_GLOBAL_ANSWER_CACHE_FILTER_CONTENTFUL_ARIS`` — cache key includes ARIs
* ``SAIN_GLOBAL_ANSWER_CACHE_VERBOSE_LOGGING``
* ``SAIN_GLOBAL_ANSWER_CACHE_PROGRESSIVE_ROLLOUT``
* ``SAIN_GLOBAL_ANSWER_CACHE_CUSTOMER_EXPERIMENT``

**Performance experiments**:

* ``SAIN_PARALLEL_LLM_STREAMING`` — parallel LLM call streaming
* ``SAIN_HYBRID_ORCH_EARLY_STOP`` — early-stop heuristic
* ``SAIN_EARLY_STOP_HELLO_EXP`` + ``SAIN_EARLY_STOP_CUSTOMER_EXP`` — A/B
* ``SAIN_IMPROVE_PROMPT_CACHE_PROMPT`` + ``..._EXP`` — prompt-cache improvements

**Quality experiments**:

* ``SAIN_ASR_DSAT_PROMPT`` + ``SAIN_ASR_DSAT_PROMPT_EXPERIMENT`` — Answer Satisfaction Rating / DSAT alignment
* ``SAIN_NO_ANSWER_STATE`` + ``..._EXPERIMENT`` — handling unanswerable questions
* ``SAIN_IMPROVE_FORMATTING`` — formatting tweaks
* ``SAIN_EXPLORATION_DEPTH_CONFIG`` — depth-of-exploration config

**Model selection** (4 separate flags for orchestration vs answer-gen):

* ``SAIN_ORCHESTRATION_HAIKU_4_5`` — Anthropic Haiku 4.5 for tool calling
* ``SAIN_ORCHESTRATION_GPT_4_1`` — OpenAI GPT 4.1 for tool calling
* ``SAIN_ANSWER_GEN_GPT_5_1`` — OpenAI GPT 5.1 for answer generation
* ``SAIN_ANSWER_GEN_GPT_4_1_MINI`` — OpenAI GPT 4.1 mini for answer gen

**Async / context**:

* ``SAIN_ASYNC_REQUEST_CONTEXT`` — async request context propagation

**This is unprecedented FF granularity** — 40+ flags control essentially
every dimension of SAIN behavior. Implications:

* **Easy to leave one flag in inconsistent state** across A/B variants
* **Operational complexity** is high — runbooks must enumerate which flag affects what
* **Iteration velocity** is presumably very high to justify this many flags
* **Risk of "FF-driven" architecture** — model selection in particular should probably move to config (per-tenant settings) once the experiments stabilize

The citation system
======================

SAIN tracks **two distinct kinds of sources**:

1. **Cited sources** (``getCitedSources``) — post-citation-filtered. Only
   sources the LLM explicitly tagged with ``[^N^]`` citation markers in
   the answer text survive this filter. Used for **citation accuracy**
   evaluation.

2. **Retrieved sources** (``getRetrievedSources``) — unfiltered list of
   sources actually returned by the SearchTool. Used for **recall**
   evaluation.

Citation processing is in ``orchestrator/SainCitationProcessor.kt`` and
``SainCitationTagNormalizer.kt``. The global citation index
(``ToolMessageGlobalCitationIndexPreprocessor.kt``) maintains stable
citation IDs across multiple tool calls within a turn so the LLM can
reference earlier-found sources by ID without confusion.

**Two flags** (``SAIN_TOOL_MESSAGE_GLOBAL_CITATION_INDEX`` + experiments)
gate this; experiments running suggest it's still being tuned.

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - System
     - How
     - Used for
   * - **Atlassian Search Platform**
     - via ``SearchPlugin`` / ``AgenticSearch``
     - Confluence + Jira + cross-product retrieval
   * - **AI Gateway** (LLM)
     - 2-3 calls per turn (orchestration LLM + answer-gen LLM)
     - SIMPLE/COMPLEX classification, tool calling, answer synthesis
   * - **3P Connector**
     - via ``LongHorizonOrchestratorAgentLoaderImpl``
     - 3rd-party tool integration (when LongHorizon path active)
   * - **Redis**
     - via ``SAINWorkflowCacheImpl``
     - Global answer cache (cache key: tenant + question hash + contentful ARIs)
   * - **Statsig**
     - 40+ feature flags
     - Routing, model selection, experiment cohorts
   * - **Image Search service**
     - via ``ImageSearchSchemaAgent``
     - Confluence/Jira image search
   * - **People service**
     - via ``PeopleDataProvider``
     - Cross-product people lookup
   * - **MetricsService**
     - many emissions per turn
     - Latency, classifier outcomes, cache hits, citation accuracy


Sequence diagram — one StandaloneHybrid SAIN turn
=====================================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as User
       participant Svc as SainServiceImpl
       participant Exec as SAINExecutor
       participant Cache as SAINWorkflowCache<br/>(Redis)
       participant Cls as ComplexityClassifier
       participant Orch as StandaloneHybrid<br/>OrchestratorAgent
       participant LLM as Orchestration LLM
       participant Search as Search/Sub-agents
       participant AnsLLM as Answer-Gen LLM
       participant CitProc as CitationProcessor
       participant Stream as StreamingHandler

       U->>Svc: SAINRequest
       Svc->>Exec: dispatch(request)
       Exec->>Cache: lookup(tenant, qHash, ARIs)
       
       alt cache hit (and not bypassed)
           Cache-->>Exec: cached answer
           Exec-->>U: stream from cache
       else cache miss
           Exec->>Orch: route by FF + agent config
           Note over Orch: SAIN_STANDALONE_HYBRID FF gate
           Orch->>Cls: classify(query)
           Cls-->>Orch: SIMPLE | COMPLEX

           alt SIMPLE
               Orch->>AnsLLM: generate answer (no tools)
               AnsLLM-->>Stream: stream text
           else COMPLEX
               loop until ReadyToAnswerTool or max iters
                   Orch->>LLM: orchestrate(state, tools)
                   LLM-->>Orch: tool_call OR ready_to_answer

                   alt tool_call
                       Orch->>Search: execute(tool, args)
                       par parallel
                           Search->>Search: SearchPlugin
                           Search->>Search: PeopleDataProvider
                           Search->>Search: ImageSearchAgent
                           Search->>Search: 3P research agent (if FF)
                       end
                       Search-->>Orch: results + sources
                       Orch->>CitProc: index sources globally
                   else ready_to_answer
                       Note over Orch: exit loop
                   end
               end

               Orch->>AnsLLM: generate(state, indexedSources)
               AnsLLM-->>Stream: stream text with [^N^] markers
               Stream->>CitProc: post-process citations
               CitProc-->>Stream: final answer + cited/retrieved sources
           end

           Stream-->>U: FINAL_RESPONSE envelope
           Orch->>Cache: store(qHash, answer)
       end

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
     - **1,908-LoC ``SainStandaloneHybridOrchestratorAgent.kt``**
     - orchestrator/
     - The single largest file in SAIN. Contains routing + state + step-result aggregation + streaming handoff. Should split into router, state-manager, step-aggregator, streaming-glue. ~3 days mechanical refactor.
   * - 🔴
     - **40+ feature flags for SAIN behavior**
     - ``SAINSpecificFeatureFlags`` enum
     - 40+ FF surface is unprecedented. Easy to leave in conflicting state. Document the rollout matrix; sunset the experiments once decisions are made.
   * - 🔴
     - **Three coexisting orchestrators** (Hybrid + StandaloneHybrid + LongHorizon)
     - orchestrator/
     - Tech debt — the legacy Hybrid still has FF gates. Plan a deprecation date for Hybrid once StandaloneHybrid is at 100%.
   * - 🟡
     - **901-LoC ``SainOrchestratorSystemPromptGeneratorImpl.kt``**
     - orchestrator/
     - Concentrates per-turn prompt assembly. Likely contains many FF-gated branches. Refactor into composable prompt-section modules.
   * - 🟡
     - **699-LoC ``SainLongHorizonOrchestratorAgent.kt``**
     - orchestrator/longhorizon/
     - SAIN-LH itself is large for a "lite" orchestrator. Worth review against the design constraint of "loop + hooks trimmed".
   * - 🟡
     - **DESIGN_NOTES.md is the only living doc**
     - orchestrator/longhorizon/
     - Excellent in itself, but other SAIN paths have no equivalent. Hybrid + StandaloneHybrid lack design notes.
   * - 🟡
     - **Two parallel tool-loading mechanisms** (raw client interface + SchemaAgent)
     - LongHorizon
     - Maintenance cost is doubled. DESIGN_NOTES.md acknowledges they are "parallel systems" — but a long-term simplification path is not stated.
   * - 🟡
     - **Model selection via FFs** (4 model-pick flags)
     - SAINSpecificFeatureFlags
     - Convenient for experiments; scales poorly. Per-tenant model config would be cleaner once experiments stabilize.
   * - 🟡
     - **Defensive ``try/catch → emptyList()``** in tool loading
     - SAIN-LH per DESIGN_NOTES.md §11
     - Exists because of upstream 5xx flakiness. Acknowledged as future cleanup (PR #13 in DESIGN_NOTES roadmap).
   * - 🟡
     - **Citation system has 5 separate experiments** (Tool message global index, customer exp, 3P preference, fix prompt, debug)
     - SAINSpecificFeatureFlags
     - Same FF-driven pattern. Sunset stale experiments.
   * - 🟢
     - **No clear sunset for Hybrid orchestrator**
     - DEFERRED
     - StandaloneHybrid is current production but Hybrid still has live FF. Document the deprecation timeline.
   * - 🟢
     - **No README at SAIN module root**
     - product/rovo/sain/
     - 9.3K LoC and the module README is missing. Add a short index pointing at this doc.

Refactoring opportunities
============================

1. **Split ``SainStandaloneHybridOrchestratorAgent.kt``** (M, 🔴 high) — 1,908 LoC into ~4 files: router, state-manager, step-aggregator, streaming-glue. ~3 days.

2. **Split ``SainOrchestratorSystemPromptGeneratorImpl.kt``** (M, 🔴 high) — 901 LoC into composable prompt-section modules; each FF gate becomes a module-include rather than an inline ``if (ff.x)``.

3. **Consolidate or sunset legacy Hybrid orchestrator** (S, 🔴 high) — once StandaloneHybrid is at 100% rollout. Tracked in feature-flag table.

4. **Move stable SAIN model selection to per-tenant config** (S, 🟡 medium) — keep FFs only for active experiments; promote stable models (Haiku 4.5, GPT 5.1) to ``AgentConfigurationService``.

5. **Sunset stale SAIN feature flags** (S, 🟡 medium) — audit the 40+ flags; mark which are still active vs vestigial; remove vestigial ones in batches.

6. **Add design notes for Hybrid + StandaloneHybrid** (S, 🟡 medium) — mirror DESIGN_NOTES.md pattern; capture rationale for each. Saves on-call hours.

7. **Refactor LongHorizon's two-mechanism tool loading** (L, 🟡 medium) — once stable, plan migration to a single contract. DESIGN_NOTES.md §11 already calls out PR #13 as the eventual cleanup.

8. **Add a README at module root** (XS, 🟢 low) — point to this deep-dive.

What you would change here
============================

* **Add a new SAIN sub-agent** (e.g., new search source):
   1. Create ``SchemaAgent`` implementation
   2. Add to flattening-service input (for LongHorizon)
   3. Add tool to MCP plugin map (for Hybrid/StandaloneHybrid)
   4. Add FF in ``SAINSpecificFeatureFlags`` for rollout
   5. Update prompt generator to mention new capability

* **Tweak SIMPLE vs COMPLEX classifier threshold** → ``SainOrchestrationComplexityClassifier``

* **Adjust SAIN-LH budget** → ``SainLongHorizonConfigService.kt`` (top-level config)

* **Add new citation handling** → ``SainCitationProcessor.kt`` + ``SainCitationTagNormalizer.kt``

* **Modify cache key** → ``SAINWorkflowCacheImpl.kt`` (cache key generation)

* **Change orchestrator routing** → ``SAINExecutorImpl.kt``

* **Change model selection** → currently ``SAINSpecificFeatureFlags`` flags; eventually ``AgentConfigurationService``

* **Add new SAIN-specific MCP tool** → ``mcp/`` sub-package

What you would NOT change here
================================

* Core LLM integration → ``platform/service/service-impl``
* Search backend → ``platform/service/search/`` + Atlassian Search Platform
* Tool registry / MCP plumbing → ``rovo-impl/.../mcp/`` + LongHorizon adapter
* Streaming primitives → ``WorkflowStreamingResponseWriter``
* SchemaAgent base class → ``rovo-api/.../agent/minion/common/SchemaAgent.kt``

Verification audit log
========================

✅ **Personally verified with bash:**

* All 7 sub-package LoC + file counts (``find ... -exec cat | wc -l``)
* Total 9,268 LoC
* 41 files in ``sain/``
* Top-10 file LoC (``find ... -exec wc -l + | sort``)
* DESIGN_NOTES.md content (read end-to-end)
* All 40+ ``SAINSpecificFeatureFlags`` (read enum directly)
* SainCliStreamingWriter + 2-flavor citation source distinction (read KDoc)
* Three orchestrator file-existence + import patterns (read top 50 lines of each)
* SAIN as separate top-level agent type: ``rovo-api/.../agent/SAINAgent.kt``
* MetricKey.kt has SAIN-specific buckets (line 3114)
* LlmUsageTrackingIds: 5 SAIN entries identified

⚠️ **Inferred from naming + structure** (not deep-read):

* The 3-mechanism tool-loading deep flow (described from DESIGN_NOTES.md, not from reading LongHorizonSubagentFlatteningService source)
* The SIMPLE/COMPLEX classifier internals (only the entry-point name was verified)
* The cache key format (described from the FF name ``..._FILTER_CONTENTFUL_ARIS``)
* Sub-agent fan-out pattern (described from imports in StandaloneHybrid)

❌ **UNVERIFIED:**

* Exact L2 cache TTL (4-hour mention is from inventory, not directly verified)
* Whether the legacy Hybrid orchestrator has any active production traffic
* Whether ``SAIN_PARALLEL_LLM_STREAMING`` is on or off in production
* Per-orchestrator per-flag rollout state in production
* The ``SainSkillIntegrationService`` role (mentioned in file list but not deep-read)

Open questions for institutional knowledge
=============================================

1. **Deprecation timeline for legacy Hybrid orchestrator?** Currently FF-gated alongside StandaloneHybrid.
2. **Will model selection migrate to ``AgentConfigurationService`` post-experiment?** Currently 4 model-pick FFs.
3. **What's the production rollout state of SAIN-LH?** DESIGN_NOTES.md is from 2026-04-21; what's the state on 2026-05-02?
4. **Why are there 5 separate citation experiments?** What does each one test?
5. **What's the answer-cache hit rate in production?** ``SAIN_GLOBAL_ANSWER_CACHE_*`` family — operational data needed.
6. **What happens when ``SAIN_NO_ANSWER_STATE`` triggers?** UX behavior?


==================================================================
Open Questions — Resolved (2026-05-02 follow-up #2)
==================================================================

**Q1 (legacy Hybrid deprecation): UNRESOLVED in source**

See AIFC doc for matching investigation. Same answer:

* No ``@Deprecated`` annotations on ``SainHybridOrchestratorAgent``
* No sunset comments in source
* Coexistence is gated by ``SAIN_DIRECT_HYBRID_ORCHESTRATOR`` and
  ``SAIN_STANDALONE_HYBRID_ORCHESTRATOR`` feature flags
* Recommendation: file tech-debt ticket; add ``@Deprecated`` with replacement reference

