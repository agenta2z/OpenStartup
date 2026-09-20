.. _mod-action-api:

==============================================
``platform/action/action-api``
==============================================

:Tier: platform
:Path: ``modules/platform/action/action-api``
:Size: ~780 source lines :sup:`(verified)`
:Importance: Tier 2 — required by every module that runs an action

Defines the runtime contract for **agent actions** — the things an LLM-emitted ``tool_call`` ultimately invokes. Distinguishes "config" (what an action *is*) from "runtime" (how an action *runs*) from "output processing" (how the result is shaped back).

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Concept
   * - ``ActionConfig.kt``
     - 162
     - Action declaration model
   * - ``ActionContext.kt``
     - 45
     - Per-invocation context
   * - ``ActionRuntimeService.kt``
     - 39
     - Top-level entry point
   * - ``StreamingActionOutputProcessor.kt``
     - 27
     - Streaming output postprocess

Key public contracts
======================

* ``interface ActionRuntimeService`` — invoke an action by reference + context
* ``interface ActionConfigService`` — load/lookup action configs
* ``interface ActionClassifier`` — classify actions (for routing/auth)
* ``interface ActionContextBuilder<C>`` — typed builder for action context
* ``interface ActionContextBuilderFactory`` — produces context builders
* ``interface StreamingActionOutputProcessor<O>`` / ``ActionOutputProcessorV2<O>`` / ``ActionOutputProcessor<O>`` — three generations of output processing API

Notable findings
==================

* **Three generations of output-processing API coexist** (``StreamingActionOutputProcessor``, ``ActionOutputProcessorV2``, ``ActionOutputProcessor``). Suggests organic evolution of the streaming/typing contract; deprecation status of older variants is worth checking.
* ``ActionConfig.kt`` (162 lines) is the largest single file — config schemas accumulate over time as new action types are introduced.

Patterns
==========

1. **Config vs runtime split.** ``ActionConfig`` is the static declaration; ``ActionContext`` carries per-invocation state.
2. **Generic output processors.** Type parameter ``<O>`` lets callers pin the shape of the action's result.

