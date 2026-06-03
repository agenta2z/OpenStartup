.. _mod-workflow-api:

==============================================
``platform/workflow/workflow-api``
==============================================

:Tier: platform
:Path: ``modules/platform/workflow/workflow-api``
:Size: ~677 source lines :sup:`(verified)`

Workflow executor contracts. Currently focused on the **SimpleLoop** workflow pattern — a deliberate single-pattern abstraction (not a generic graph framework).

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Concept
   * - ``SimpleLoopWorkflowExecutorOutput.kt``
     - 136
     - Output type
   * - ``ToolInvocationPostProcessor.kt``
     - 104
     - Post-processor hook
   * - ``SimpleLoopWorkflowMetricsEmitter.kt``
     - 71
     - Metrics
   * - ``SimpleLoopWorkflowExecutorInput.kt``
     - 62
     - Input type
   * - ``SimpleLoopWorkflowExecutorConfig.kt``
     - 54
     - Config

Key contracts
==============

* ``SimpleLoopWorkflowExecutor*`` family — input/output/config/metrics
* ``ToolInvocationPostProcessor`` — pluggable post-processing hook

Notable findings
==================

* **One workflow pattern, well-scoped.** Not a generic state-machine framework. The "simple loop" is: ``LLM → tool_call? → execute tool → feed result → LLM again``.
* This is the dominant agent-execution loop in the codebase — anything more complex escapes via Marathon (see :ref:`diag-agent-runtime`).

