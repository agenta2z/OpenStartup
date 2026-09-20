.. _mod-tool-registry-api:

==============================================
``platform/tool-registry/tool-registry-api``
==============================================

:Tier: platform
:Path: ``modules/platform/tool-registry/tool-registry-api``
:Size: ~902 source lines :sup:`(verified)`

Tool catalogue + registration contracts. The "what tools exist and what shape they have" half of the LLM tool-call cycle (the execution half lives in :ref:`mod-action-api` / impl).

Top files :sup:`(verified)`
============================

* ``ToolRegistryContext.kt`` — 309 lines (per-call context)
* ``SimpleLoopWorkflowOutputWriter.kt`` — 223 lines
* ``AgentPlaygroundToolInvocationToActionPlanMapper.kt`` — 59 lines
* ``PlaygroundTypes.kt`` — 47 lines
* ``ToolDefinitionSource.kt`` — 40 lines

Key contracts
==============

* ``ToolRegistryContext`` — per-call resolution context
* ``ToolDefinitionSource`` — pluggable tool sources
* ``PlaygroundTypes`` — agent playground data types

Notable findings
==================

* **Bridges tool-registry and workflow** — references ``SimpleLoopWorkflow*`` types from :ref:`mod-workflow-api`. Suggests the simple-loop workflow needs special tool-resolution semantics.
* **Agent Playground APIs visible** — testing infrastructure for agents is a first-class concept here.

