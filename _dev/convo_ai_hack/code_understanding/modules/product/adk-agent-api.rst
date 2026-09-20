.. _mod-adk-agent-api:

==============================================
``product/adk/adk-agent-api``
==============================================

:Tier: product
:Path: ``modules/product/adk/adk-agent-api``
:Size: ~3,077 source lines :sup:`(verified)`

User-facing ADK skill API — concrete skills exported for external consumers (other Atlassian teams, Forge apps).

Top files :sup:`(verified)`
============================

* ``SolutionArchitectSkill.kt`` — 298 lines
* ``SurveyInsightsSkill.kt`` — 135 lines
* ``AutomationWorkflowBuilderSkill.kt`` — 131 lines
* ``HamInsightsSkill.kt`` — 128 lines

Notable findings
==================

* Distinct from foundation/adk/core-api — that's the runtime; this is the **catalog** of pre-built skills.
* Solution Architect, Survey Insights, HAM (Heap Analyzer Manager?), Automation Workflow Builder — domain-specific skills shipped as a library.

