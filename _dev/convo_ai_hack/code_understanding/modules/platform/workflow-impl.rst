.. _mod-workflow-impl:

==============================================
``platform/workflow/workflow-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/workflow/workflow-impl``
:Size: ~1,564 source lines :sup:`(verified)`

Implementation of the SimpleLoop workflow executor.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``SimpleLoopWorkflowExecutorImpl.kt``
     - 1,222
     - Core executor (god-class)
   * - ``NoOpImplementations.kt``
     - 129
     - No-op strategies
   * - ``SimpleLoopWorkflowConfiguration.kt``
     - 81
     - Spring config
   * - ``FinalContentMessageBuilderImpl.kt``
     - 74
     - Final-message builder
   * - ``ToolInvocationCounter.kt``
     - 32
     - Counter

Key Spring components
=======================

* ``@Component class SimpleLoopWorkflowExecutorImpl``
* ``class FinalContentMessageBuilderImpl``
* ``class ToolInvocationCounter``
* No-op strategies (``NoOpImplementations``)

Notable findings
==================

* **78% of LoC in one file** — ``SimpleLoopWorkflowExecutorImpl`` (1,222 lines) holds essentially all loop logic. This is the heart of agent execution; reasonable to keep monolithic to avoid scattered state.
* ``NoOpImplementations`` — provides no-op strategies for optional hooks (e.g., when no post-processor is configured). Keeps the executor's null-checks simple.

