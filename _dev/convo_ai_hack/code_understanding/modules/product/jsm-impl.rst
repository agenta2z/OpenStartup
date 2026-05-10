.. _mod-jsm-impl:

==============================================
``product/jsm/jsm-impl``
==============================================

:Tier: product
:Path: ``modules/product/jsm/jsm-impl``
:Size: ~68,570 source lines :sup:`(verified)`
:Importance: **Tier 1 — large product**

JSM (Jira Service Management) integration — service desk composer agents, journey crafting, runbook search, admin guidance.

Top files :sup:`(verified by line-count)`
===========================================

.. list-table::
   :header-rows: 1
   :widths: 65 15 20

   * - File
     - Lines
     - Subsystem
   * - ``agent/jsm/minion/JourneyCraftingMinion.kt``
     - 2,671
     - Journey crafting agent
   * - ``agent/jsm/composer/BaseComposerAgent.kt``
     - 2,046
     - Composer agent base class
   * - ``agent/jsm/minion/quality/PlanQualityGateService.kt``
     - 1,168
     - Plan quality gating
   * - ``agent/jsm/minion/JourneyRecommendationService.kt``
     - 1,007
     - Journey recommendations
   * - ``agent/jsm/service/WorkItemUpdateServiceImpl.kt``
     - 956
     - Work item updates
   * - ``agent/jsm/service/search/RunbookSearchServiceImpl.kt``
     - 899
     - Runbook search
   * - ``agent/jsm/executor/JsmAgentExecutorImpl.kt``
     - 885
     - JSM agent executor

Subsystems
============

1. **Composer agents** (``agent/jsm/composer/``) — guided agent workflows that compose service desk artifacts. ``BaseComposerAgent`` is the inheritance base.
2. **Journey crafting** (``agent/jsm/minion/JourneyCraftingMinion.kt``) — generates customer journey definitions from natural language.
3. **Quality gating** (``agent/jsm/minion/quality/PlanQualityGateService.kt``) — validates generated plans before execution.
4. **Runbook search** (``agent/jsm/service/search/RunbookSearchServiceImpl.kt``) — searches JSM runbooks for incident response.
5. **Work item updates** (``agent/jsm/service/WorkItemUpdateServiceImpl.kt``) — applies AI-suggested updates to JSM tickets.
6. **Admin guidance** :sup:`(inferred)` — provides admin-facing recommendations about JSM configuration.

Patterns specific to jsm-impl
================================

1. **Minion + composer pattern.** "Minions" are specific-purpose agents (journey crafter, quality gate); composers orchestrate them.
2. **Quality gating before execution.** Generated plans pass through ``PlanQualityGateService`` before being applied — protects against bad LLM output.
3. **Templates in ``src/main/resources/``** :sup:`(inferred)` — system prompts and plan templates likely Pebble-rendered.

What you would change here
============================

* **Modify a journey-crafting prompt** → templates under ``src/main/resources/templates/`` :sup:`(inferred)`
* **Add a new minion** → new file under ``agent/jsm/minion/`` + register
* **Modify quality gate logic** → ``PlanQualityGateService.kt``
* **Add a new composer flow** → extend ``BaseComposerAgent``

