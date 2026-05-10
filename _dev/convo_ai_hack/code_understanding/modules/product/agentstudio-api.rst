.. _mod-agentstudio-api:

==============================================
``product/agentstudio/agentstudio-api``
==============================================

:Tier: product
:Path: ``modules/product/agentstudio/agentstudio-api``
:Size: ~1,159 source lines :sup:`(verified)`

Agent Studio service contracts — skills mgmt, scenario execution, tool config, permissions.

Top files :sup:`(verified)`
============================

* ``AgentStudioSkillsService.kt`` — 602 lines
* ``AgentStudioScenarioService.kt`` — 109 lines
* ``ToolConfigLookupResolver.kt`` — 82 lines
* ``AgentStudioPermissionService.kt`` — 78 lines

Notable findings
==================

* ``AgentStudioSkillsService`` (602 lines) is the dominant API — substantial skill-CRUD surface.
* AgentStudio is the **publishing UI** for agents; this API backs that UI's skills/scenarios pages.

