=================================================
Orchestrator Selection (How Rovo Chooses Marathon vs LH vs HO)
=================================================

**Discovered**: 2026-05-03 during architectural-surprise investigation
(see :doc:`../../business/05-open-questions-resolved` §14.3).

**Critical correction**: There is **NO separate "Hello experiment service"**.
The "Hello experiment for orchestrator selection (including LH)" is a
**code comment** at ``RovoChatAgentExecutionService.kt:431`` describing
TWO cascading Statsig experiments — both in ``RovoSpecificFeatureFlags``.

==================================================
1. The Selection Algorithm (full decision tree)
==================================================

**File**: ``RovoChatAgentExecutionService.kt:431-525``

**Pseudo-code**:

.. code-block:: kotlin

   fun selectOrchestrator(orchestratorAgentInput: AgentInput) {
       // Step 1: Pre-experiment gate — creation-context override
       if (shouldRedirectToHO(orchestratorAgentInput)) {
           useHybridOrchestrator(...)
           return
       }

       // Step 2: Primary experiment — ROVO_CHAT_LH_ORCHESTRATOR_EXP
       val variant = rolloutService.experimentParameter(
           RovoSpecificFeatureFlags.ROVO_CHAT_LH_ORCHESTRATOR_EXP,
           "variant",
           "control"
       ).value

       when (variant) {
           "lh_no_td" -> executeLongHorizonAsDefault(...)
           "ho_no_td" -> useHybridOrchestrator(...)
           "lh_implicit_td" -> executeLongHorizonImplicitTdOrchestration(...)
           else /* "control" */ -> {
               // Step 3: Nested control-branch experiment
               val ttfbVariant = rolloutService.experimentParameter(
                   RovoSpecificFeatureFlags.LH_TTFB_OPTIMIZATION_EXP,
                   "variant",
                   "control"
               ).value
               when (ttfbVariant) {
                   "lh_default_llm_classifier" ->
                       executeLhWithClassifierFallback(...)
                   // ... other variants
               }
           }
       }
   }

==================================================
2. The Two Experiments
==================================================

2.1 Primary: ROVO_CHAT_LH_ORCHESTRATOR_EXP
============================================

**Purpose**: Decide between LongHorizon (LH) and HybridOrchestrator (HO)
as default

**Variants**:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variant
     - Behavior
   * - **lh_no_td**
     - Use LongHorizon as default; no transition delay
   * - **ho_no_td**
     - Use HybridOrchestrator (HO) as default; no transition delay
   * - **lh_implicit_td**
     - LongHorizon with implicit TD (transition delay) orchestration
   * - **control** (default)
     - Falls through to nested experiment ``LH_TTFB_OPTIMIZATION_EXP``

2.2 Nested: LH_TTFB_OPTIMIZATION_EXP
======================================

**Purpose**: TTFB (time-to-first-byte) optimization variant within the
control branch of the primary experiment

**Variants** (only one explicitly enumerated in current investigation):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variant
     - Behavior
   * - **lh_default_llm_classifier**
     - LongHorizon execution with LLM classifier fallback for TTFB optimization
   * - (other variants exist but were not enumerated in source review)
     - TBD

==================================================
3. The Pre-experiment Override: shouldRedirectToHO()
==================================================

**File**: ``RovoChatAgentExecutionService.kt:847-870``

**Purpose**: Force HO (HybridOrchestrator) selection regardless of
experiment, based on **creation context**.

**Override conditions** (configurable via routing config):

* ``remix`` → force HO
* ``inline rovo`` → force HO
* ``cwr_edits`` → force HO
* ``cwr_first_message`` → force HO
* ``cwr_staging`` → force HO

**Why**: Certain creation contexts (e.g., Confluence remix flows, inline
Rovo guidance) require predictable HO behavior and should not be subject
to the LH-vs-HO experiment.

==================================================
4. Critical Insight: Two FF Systems, Different Roles
==================================================

After this investigation, we now have a complete map of the FF systems
involved in orchestrator behavior:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - FF System
     - Role
   * - ``RovoSpecificFeatureFlags`` — Marathon FFs (3 flags)
     - **Marathon enablement** (separate from LH/HO selection)
   * - ``RovoSpecificFeatureFlags`` — LH/HO experiments (2 experiments)
     - **Orchestrator SELECTION** (LH vs HO with TTFB nested experiment)
   * - ``HybridOrchestratorFeatureFlags`` (23 flags)
     - **Orchestrator BEHAVIOR / parameter tuning** (model configs, token budgets, prompts)

**Three orchestrators exist**:

#. **Marathon** — gated by Marathon FFs; standalone executor
#. **HybridOrchestrator (HO)** — selected by experiments above; tuned by HybridOrchestratorFeatureFlags
#. **LongHorizon (LH)** — selected by experiments above; tuned by HybridOrchestratorFeatureFlags

==================================================
5. Why It Took 3 Investigation Rounds to Find This
==================================================

Lessons learned:

#. **The comment was misleading** — "Hello experiment" suggested an
   external "Hello" service or branded A/B framework, but it's actually
   **Atlassian Statsig experiments** with the standard
   ``rolloutService.experimentParameter(...)`` API
#. **Selection logic is INSIDE one large method** at lines 431-525 of
   ``RovoChatAgentExecutionService.kt`` — no dedicated "OrchestratorSelector"
   class
#. **Two FF systems coexist** for orchestrator concerns
   (RovoSpecificFeatureFlags + HybridOrchestratorFeatureFlags), each with
   different responsibilities — easy to confuse
#. **Cascading experiments** (control branch of one experiment = entire
   sub-experiment) is a non-obvious pattern that doesn't show up in
   simple FF dashboards

==================================================
6. Implications for Operations
==================================================

6.1 Reading orchestrator-selection metrics
============================================

To understand "what orchestrator is in use right now":

#. Check ``shouldRedirectToHO()`` short-circuit rate (creation-context override)
#. Check ``ROVO_CHAT_LH_ORCHESTRATOR_EXP`` variant distribution in Statsig
#. For users in "control" variant, ALSO check ``LH_TTFB_OPTIMIZATION_EXP``
   variant distribution
#. Marathon is **separate** (different code path entirely; gated by
   Marathon FFs)

6.2 Rolling out a new orchestrator
====================================

To add a new orchestrator (e.g., "GPT-X-Orchestrator"):

#. Add a new variant to ``ROVO_CHAT_LH_ORCHESTRATOR_EXP`` (e.g.,
   ``"gptx_no_td"``)
#. Implement ``executeGPTXAsDefault(...)`` in RovoChatAgentExecutionService
#. Update ``HybridOrchestratorFeatureFlags`` for GPT-X-specific tuning
   (model config, token budget, prompts)
#. Coordinate with the AB-test team to allocate traffic %

6.3 Debugging "wrong orchestrator selected"
=============================================

If a user reports "I expected HO but got LH":

#. **First**, check creation context — was there a ``shouldRedirectToHO()``
   override active?
#. **Second**, check Statsig for the user's bucket in
   ``ROVO_CHAT_LH_ORCHESTRATOR_EXP``
#. **Third**, if user is in "control", check
   ``LH_TTFB_OPTIMIZATION_EXP`` bucket
#. **Fourth**, check Marathon — is the user's request also matching
   Marathon FF (independent decision path)?

==================================================
7. Open Questions
==================================================

* **Full enumeration of ``LH_TTFB_OPTIMIZATION_EXP`` variants** —
  current investigation only found ``lh_default_llm_classifier``
* **What's the current rollout %** of ``ROVO_CHAT_LH_ORCHESTRATOR_EXP``
  variants? — needs Statsig dashboard access
* **Why is the experiment named "Hello experiment"** in the code
  comment? — likely a Statsig experiment series naming convention
* **Why are creation-context overrides hard-coded** rather than being
  experiment variants themselves? — likely product-decision (some
  contexts must be deterministic)
* **Is there a parallel selection algorithm for AtlassianStudio**? —
  AtlassianStudio's ``executeMarathonDirectly()`` bypasses this entirely;
  but for non-Marathon AtlassianStudio paths, what's the selection
  logic?

==================================================
8. Recommended Documentation Updates
==================================================

#. **This page** (``orchestrator-selection.rst``) — NEW; this doc
#. **``marathon-orchestrator.rst``** — ALREADY UPDATED (Section 12) with
   AtlassianStudio two-path model
#. **``12-configuration-reference.rst``** — ALREADY UPDATED with Marathon
   FF composition + HybridOrchestratorFeatureFlags table
#. **``00-glossary.rst``** — could add "HO = HybridOrchestrator",
   "LH = LongHorizon", "TD = Transition Delay", "TTFB = Time To First Byte"
#. **A new architecture diagram** at
   ``diagrams/orchestrator-selection-flow.rst`` would be valuable

==================================================
9. Cross-references
==================================================

* :doc:`marathon-orchestrator` — Marathon (independent of LH/HO selection)
* :doc:`sain` — SAIN orchestrator (relationship to LH/HO TBD)
* :doc:`../12-configuration-reference` — Marathon FFs + HybridOrchestratorFeatureFlags table
* :doc:`../../business/05-open-questions-resolved` §14.3 — original open question
* :doc:`../../business/01-fy26-goals-and-slos` §11 — orchestrator-related items
