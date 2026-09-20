.. _mod-agentstudio-impl:

==============================================
``product/agentstudio/agentstudio-impl``
==============================================

:Tier: product
:Path: ``modules/product/agentstudio/agentstudio-impl``
:Size: ~15,443 source lines :sup:`(verified)`
:Importance: **Tier 1 — agent management UI backend**

Backend for **AgentStudio** — the UI for managing agents (CRUD, scenarios, evaluation, conversation review).

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Role
   * - ``service/AgentStudioAgentService.kt``
     - 1,605
     - Agent CRUD service
   * - ``service/AgentStudioScenarioServiceImpl.kt``
     - 1,178
     - Scenario management
   * - ``service/AgentStudioConversationReviewServiceImpl.kt``
     - 940
     - Conversation review (human evaluation)
   * - ``service/AgentStudioPermissionServiceImpl.kt``
     - 898
     - Permission checks
   * - ``graphql/AgentStudioAgentMutationController.kt``
     - 822
     - GraphQL mutations

Subsystems
============

1. **Agent CRUD** — create / read / update / delete agents (stored in Kamino).
2. **Scenarios** — test scenarios that can be run against agents.
3. **Conversation review** — human evaluators rate past agent conversations.
4. **Permissions** — who can edit / view / publish which agents.
5. **GraphQL mutations** — expose CRUD via GraphQL (consumed by AgentStudio UI).
6. **Batch evaluation** :sup:`(inferred)` — kicks off evaluation runs against datasets (works with ``BatchEvaluationTaskHandler``).

Patterns
==========

1. **GraphQL-first.** Most of the surface is GraphQL; small REST surface for batch operations.
2. **Suspend-aware GraphQL.** Mutations use ``withRequestAttributesContext { }`` per the codebase's GraphQL contract.
3. **Permission-gated.** Each operation checks ``AgentStudioPermissionService`` before proceeding.
4. **Schema migrations.** ``data.agentStudio_upgradeSchema`` mutation exists (visible in failing integration tests) — handles agent-config schema upgrades.

What you would change here
============================

* **Add a new agent operation** → new mutation in ``graphql/AgentStudioAgentMutationController.kt`` + service method
* **Add a new scenario type** → ``service/AgentStudioScenarioServiceImpl.kt``
* **Add a new permission rule** → ``service/AgentStudioPermissionServiceImpl.kt``
* **Modify schema migration** → tied to ``agent-version-impl`` and Kamino schema

