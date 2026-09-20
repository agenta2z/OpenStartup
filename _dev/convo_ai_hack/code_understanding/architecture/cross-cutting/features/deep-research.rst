.. _feature-deep-research:

==================================================================
Deep Research — multi-agent research workflow
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 8,103 main LoC across 22 files in 1 sub-package
:Module: ``rovo-impl/.../product/rovo/deepresearch/``

.. contents:: On this page
   :local:
   :depth: 2

What it IS (in one paragraph)
================================

Deep Research is a **multi-agent research orchestration** that decomposes
a user's research question into specialized sub-tasks (grounding,
planning, data collection, drafting, execution, self-evolution) and
coordinates them via a router agent. Used when the user wants a longer,
better-cited answer than a single LLM turn would produce. **It is NOT
a separate top-level orchestrator** — it runs INSIDE the existing
chat workflow (Marathon-based), invoked as a high-level "research" mode.

Two version paths exist (V1 deprecated, V2 current). The V2 path is
gated by **4 separate Statsig flags** so different invocation surfaces
can be migrated independently.

Anatomy — where the code lives
=================================

Single sub-package: ``rovo-impl/.../product/rovo/deepresearch/``

**Top-level files** (8 files, ~2K LoC):

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - File
     - LoC
     - Role
   * - ``DeepResearchServiceImpl.kt``
     - 503
     - Entry point. Decides V1 vs V2; orchestrates execution
   * - ``DeepResearchActionHelper.kt``
     - 246
     - Helper for emitting research-step actions (UI events)
   * - ``DeepResearchTokenLogger.kt``
     - 101
     - LLM token accounting; ``DeepResearchUsageAccumulator``
   * - ``DeepResearchInterceptor.kt``
     - 29
     - Wraps response writer to detect ``FINAL_REPORT`` phase
   * - ``DeepResearchAccumulatorContext.kt``
     - 23
     - Coroutine context element holding token accumulator
   * - ``DeepResearchContextBuilder.kt``
     - moderate
     - Builds research-specific context (sources, prior findings)
   * - ``DeepResearchStreamingWriter.kt``
     - moderate
     - Streams partial research output to UI
   * - ``RovoAgentDeepResearchServiceImpl.kt``
     - 51
     - Subagent bridge; lets one agent invoke Deep Research as a tool

**``agents/`` sub-dir (5,583 LoC, 13 files)** — the meat of the system:

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - File
     - LoC
     - Role
   * - ``DeepResearchOrchestratorAgent.kt``
     - **907**
     - The router. Picks which sub-agent runs each step. Calls "orchestration LLM" with current state, gets back ``OrchestratorResponse(selectedAgent, hint, answer)``. Loops until ``FINAL_REPORT`` or iteration limit.
   * - ``DeepResearchDraftService.kt``
     - 854
     - Manages the in-progress research document; drafts and revisions
   * - ``DeepResearchExecutionAgent.kt``
     - 825
     - Runs concrete information-gathering actions (search, fetch, summarize)
   * - ``DeepResearchSelfEvolutionService.kt``
     - 815
     - **Self-improvement loop**: lets the agent system update its own approach mid-run based on observations
   * - ``DeepResearchDataCollectionAgent.kt``
     - 755
     - Specialized data-collection sub-agent
   * - ``DeepResearchTestTimeDiffusionHelper.kt``
     - 372
     - **Test-Time Diffusion** — iterative refinement at inference time (research term)
   * - ``DeepResearchDynamicOutlineService.kt``
     - 286
     - Builds and updates the research outline as the work progresses
   * - ``DeepResearchPlanningAgent.kt``
     - 266
     - Decomposes the research question into a plan
   * - ``AbstractDeepResearchAgent.kt``
     - small
     - Base class for all Deep Research agents — handles accumulator context
   * - ``DeepResearchMinionRegistry.kt``
     - small
     - Spring-discovered registry of agents the orchestrator can pick
   * - ``DeepResearchPromptManager.kt``
     - 167
     - Centralized prompt templates for all sub-agents
   * - ``DeepResearchGroundingAgent.kt``
     - 139
     - "Grounding" — checks the question is well-formed; clarifies
   * - ``ttd/`` subdir
     - small
     - Test-Time Diffusion supporting files

**``ablation/`` sub-dir (1,210 LoC, 6 files)** — A/B testing infrastructure:

* ``AblationOrchestrator.kt`` (230)
* ``AblationMetricsCollector.kt`` (289)
* ``AblationConfig.kt`` (188)
* ``AblationExecutionExample.kt`` (280)
* ``AblationExecutionIntegration.kt`` (177)

Used to A/B-test different combinations of sub-agents and prompts.

**``config/`` sub-dir (268 LoC, 3 files)** — Spring config + V2 config flags

End-to-end flow (V2 path)
============================

When a user requests Deep Research:

1. ``DeepResearchServiceImpl.execute()`` invoked
2. ``shouldUseDeepResearchV2()`` checks 4 Statsig flags:

   * ``DEEP_RESEARCH_V2`` (global)
   * ``DEEP_RESEARCH_V2_STAGING_AREA_REQUESTS``
   * ``DEEP_RESEARCH_V2_AGENT_REQUESTS``
   * ``DEEP_RESEARCH_V2_LEGACY_UI_REQUESTS``

3. If V2 → ``executeV2(workflowContext, agentInput, responseWriter)``
4. Build ``DeepResearchAccumulatorContext`` (coroutine context for token tracking)
5. Wrap response writer with ``DeepResearchInterceptor`` (detects ``FINAL_REPORT`` phase)
6. ``deepResearchOrchestratorAgent.execute(input)``:

   .. code-block:: kotlin

      while (currentPhase != FINAL_REPORT && iterations < limit) {
          val response = callOrchestrationLLM(state)
          if (response.directAnswer != null) {
              handleDirectAnswer(response)
              break
          }
          val agent = response.selectedAgent  // grounding | planning | execution | etc
          val result = executeSelectedAgent(agent, state, response.hint)
          updateState(result)
      }

7. Each sub-agent runs as a coroutine inheriting the accumulator context, so all LLM token usage is summed
8. ``DeepResearchTokenLogger`` writes total token usage at the end
9. Final report emitted; ``DeepResearchInterceptor`` triggers terminal phase

The "Self-Evolution" twist
============================

``DeepResearchSelfEvolutionService.kt`` (815 LoC) is the most novel piece.
After each iteration, the system **reflects on its own progress** —
asks the LLM whether the current approach is working, what's missing,
and proposes adjustments to subsequent iterations.

This is **meta-prompting**: the agent system has a self-modification
loop that reads its current state and rewrites its strategy. Risks:
* Latency cost (extra LLM call per iteration)
* Possibility of getting "stuck" in a self-evolution loop
* Hard to debug/replay (state changes between iterations)

**Test-Time Diffusion** (``DeepResearchTestTimeDiffusionHelper.kt`` + ``ttd/``)
is a related concept from recent ML research — iteratively refining
outputs at inference time, similar to how diffusion models progressively
denoise images. Applied here as text refinement passes over the research
draft.

Ablation framework
====================

The ``ablation/`` sub-package implements **production A/B testing for
research strategies**. ``AblationConfig`` declares variant
configurations (different prompt templates, different agent selections,
different iteration limits). ``AblationOrchestrator`` routes a fraction
of requests to each variant. ``AblationMetricsCollector`` measures
outcome quality (UNVERIFIED: human-rated? LLM-judged? completion
metrics?).

This is an unusual amount of investment in **scientific evaluation
infrastructure** for a single feature. Suggests:
* Deep Research is high-value enough to justify systematic optimization
* The team is iterating rapidly on prompts/agent configs
* Quality measurement is somewhat structured (not just gut feel)


Sequence diagram — one Deep Research turn
=============================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as User
       participant Svc as DeepResearch<br/>ServiceImpl
       participant Orch as DeepResearch<br/>OrchestratorAgent
       participant Reg as DeepResearch<br/>MinionRegistry
       participant LLM as Orchestration<br/>LLM
       participant Sub as Selected<br/>Sub-agent
       participant Acc as DeepResearch<br/>UsageAccumulator
       participant Stream as DeepResearch<br/>StreamingWriter

       U->>Svc: deep research request
       Svc->>Svc: shouldUseDeepResearchV2() (4 flags)
       Svc->>Orch: execute(input)
       Orch->>Orch: install accumulator in coroutine context

       loop until FINAL_REPORT or max iters
           Orch->>LLM: orchestrate(currentState, history)
           LLM-->>Orch: OrchestratorResponse(selectedAgent, hint, answer?)
           Acc->>Acc: log tokens used
           
           alt direct answer
               Orch->>Stream: emit final answer
           else routing
               Orch->>Reg: getAgent(selectedAgent)
               Reg-->>Orch: GroundingAgent | PlanningAgent | ExecutionAgent | DraftService | etc
               Orch->>Sub: execute(state, hint)

               par parallel sub-agent activities
                   Sub->>LLM: sub-prompts (1-N calls)
                   Sub->>Sub: data collection / drafting / refinement
               end

               Sub-->>Orch: agent result
               Acc->>Acc: log tokens
               Orch->>Orch: updateState(result)
               Orch->>Stream: emit progress event
           end
       end

       opt self-evolution
           Orch->>Orch: SelfEvolutionService.reflect(state)
           Orch->>LLM: meta-prompt about progress
           LLM-->>Orch: strategy adjustment
       end

       Orch->>Stream: emit FINAL_REPORT
       Stream-->>U: final research output
       Acc->>Acc: total tokens logged
       Svc-->>U: complete

External system fan-out
=========================

.. list-table::
   :header-rows: 1
   :widths: 28 30 42

   * - System
     - How
     - Used for
   * - **AI Gateway** (LLM)
     - Multiple per turn
     - Orchestration LLM (router) + per-sub-agent LLMs + self-evolution LLM
   * - **Atlassian Search**
     - via SearchPlugin / AgenticSearch
     - Information retrieval
   * - **Confluence/Jira clients**
     - via platform-tier
     - Content fetching
   * - **External MCP servers**
     - via Marathon's MCP discovery (UNVERIFIED)
     - 3rd-party tool augmentation
   * - **Statsig**
     - 4 flags + ablation flags
     - Rollout, A/B
   * - **MetricsService**
     - per sub-agent + per ablation variant
     - Latency, completion rate, quality
   * - **Token logging** (``DeepResearchTokenLogger``)
     - aggregate per turn
     - Quota / billing tracking
   * - **AiCreditUsageTracker**
     - aggregate per turn
     - User credit consumption

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
     - **907-LoC ``DeepResearchOrchestratorAgent.kt``**
     - agents/
     - The router. Single most complex file in Deep Research. Contains routing logic + state management + LLM call wrappers + iteration control. Should split.
   * - 🔴
     - **No iteration limit hard-coded** (UNVERIFIED — possibly config-driven)
     - DeepResearchOrchestratorAgent
     - If the orchestration LLM keeps choosing routes instead of FINAL_REPORT, runaway. Need to confirm a hard limit exists.
   * - 🟡
     - **815-LoC ``SelfEvolutionService``**
     - agents/
     - Meta-prompting at scale. Hard to test, hard to debug, hard to predict. Worth careful operational monitoring.
   * - 🟡
     - **854-LoC ``DraftService`` + 825-LoC ``ExecutionAgent``**
     - agents/
     - Both large. Suggests further sub-agent specialization could help.
   * - 🟡
     - **4 separate Statsig flags for V2 routing**
     - shouldUseDeepResearchV2()
     - Means a V2 issue might affect different surfaces (UI / staging / agent / legacy) differently. Easy to leave one flag in inconsistent state. Document the rollout matrix.
   * - 🟡
     - **Coroutine-context-based token accumulation**
     - DeepResearchAccumulatorContext
     - Elegant but easy to break: any sub-agent that uses ``withContext(Dispatchers.IO)`` without preserving the accumulator context will lose its tokens. Worth a unit test.
   * - 🟡
     - **Ablation framework requires explicit integration**
     - ablation/AblationExecutionIntegration.kt
     - Not auto-applied to all turns. New code paths must opt in. Easy to skip.
   * - 🟢
     - **V1 still in code path** (deprecated but present)
     - DeepResearchServiceImpl shouldUseDeepResearchV2
     - Code/test surface includes deprecated V1. Worth a deprecation date.
   * - 🟢
     - **No explicit per-sub-agent latency budget visible**
     - executeSelectedAgent
     - If GroundingAgent hangs, the whole turn hangs.

Refactoring opportunities
============================

1. **Split ``DeepResearchOrchestratorAgent.kt``** (M, 🔴 high) — extract router, state manager, LLM wrapper, iteration controller. ~1-2 days.

2. **Confirm/add hard iteration limit** (XS, 🔴 high) — ensure runaway prevention; likely a 1-line check.

3. **Sunset Deep Research V1** (S, 🟢 low) — remove dead code path once V2 has been at 100% rollout for a release.

4. **Extract ``DraftService``'s draft management** (M, 🟡 medium) — 854 LoC for "manage in-progress draft" is large; could split into Draft + Revision + Outline.

5. **Add unit tests for accumulator context preservation** (S, 🟡 medium) — test that token accounting survives coroutine context-switches in each sub-agent.

6. **Document the ablation framework's integration contract** (XS, 🟡 medium) — README in ``ablation/`` explaining how to opt-in a new code path.

7. **Add per-sub-agent timeout budgets** (M, 🟡 medium) — ``withTimeout()`` per sub-agent execution prevents one slow agent from blocking the whole research turn.

8. **Move ``ttd/`` documentation** (XS, 🟢 low) — Test-Time Diffusion is a research term most readers won't know. Add a 2-sentence README.

What you would change here
============================

* **Add a new sub-agent** → create ``agents/MyNewAgent.kt`` extending ``AbstractDeepResearchAgent``, ``@Component`` annotate, register in ``DeepResearchMinionRegistry``, add prompt in ``PromptManager``
* **Tweak the orchestration prompt** → ``DeepResearchPromptManager.kt``
* **Change V2 rollout** → flip Statsig flag (``DEEP_RESEARCH_V2_*``) — no code change
* **Add a new ablation variant** → ``ablation/AblationConfig.kt`` + integration in ``AblationOrchestrator``
* **Modify draft format** → ``DeepResearchDraftService.kt``
* **Change token accounting** → ``DeepResearchTokenLogger.kt`` + ``DeepResearchAccumulatorContext.kt``

What you would NOT change here
================================

* LLM provider — owned by ``platform/service/service-impl``
* Token accounting infrastructure — uses ``AiCreditUsageTracker`` from elsewhere
* Streaming primitives — uses ``WorkflowStreamingResponseWriter`` from rovo-impl/chat
* Coroutine context primitives — Kotlin stdlib

Verification audit log
========================

✅ **Personally verified:**

* All file LoC counts (``find ... -exec wc -l +``)
* Total: 8,103 LoC
* 4 V2 Statsig flags (``grep`` of DeepResearchServiceImpl.kt confirmed all 4)
* Sub-agent inventory in ``agents/`` (``ls`` of agents/ + ttd/)
* Ablation framework files (``ls`` of ablation/)
* Config files (``ls`` of config/, including ``DeepResearchV2Config.kt`` 177 LoC)

⚠️ **Inferred from naming/structure:**

* OrchestratorAgent's loop logic (described from agent report; not deep-read)
* AbstractDeepResearchAgent's accumulator-context handling (agent report)
* DeepResearchInterceptor's FINAL_REPORT phase detection (agent report; class is small)

❌ **UNVERIFIED:**

* Hard iteration limit existence
* Per-sub-agent timeout enforcement
* Whether AblationMetricsCollector measures human ratings, LLM judgements, or completion metrics
* Whether ``ttd/`` files are actively used or experimental
* Whether Deep Research uses Marathon-style Python execution or pure LLM-tool function calling

Open questions for institutional knowledge
=============================================

1. **Does Deep Research ever invoke Marathon for code execution?** Or is it strictly LLM-tool-calling?
2. **How is "research quality" measured in ``AblationMetricsCollector``?** Human ratings? Auto-scored?
3. **What are the typical iterations and latency for a Deep Research turn?**
4. **What's the deprecation timeline for V1?** Currently both code paths exist; when does V1 go away?
5. **Has the self-evolution loop ever caused production incidents?** Meta-prompting can be unpredictable.
6. **Are the 4 Statsig V2 flags ever in conflicting states?** What happens if global=ON but staging-area=OFF?

