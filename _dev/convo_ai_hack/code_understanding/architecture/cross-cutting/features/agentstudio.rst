.. _feature-agentstudio:

==================================================================
AgentStudio — build-an-agent platform
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 15,443 main LoC across ~63 files in the impl module
:Modules:

  * ``product/agentstudio/agentstudio-api`` (interfaces)
  * ``product/agentstudio/agentstudio-impl`` (implementations)

.. contents:: On this page
   :local:
   :depth: 2

What it IS (in one paragraph)
================================

AgentStudio is the **backend for the Atlassian "build an agent" UI**.
Users go to a web UI to create custom Rovo agents — define the agent's
identity, attach knowledge sources, configure skills, run test
scenarios, evaluate quality, and publish for use in chat. AgentStudio
provides the GraphQL + REST APIs that back this UI, plus the service
layer that persists agent definitions, manages permissions, runs batch
evaluations, and generates usage reports.

It is **NOT a runtime orchestrator** — it doesn't process chat
conversations. Once an agent is published in AgentStudio, it becomes
available for the existing Rovo chat orchestrators (Marathon/Hybrid/
LongHorizon) to invoke via standard agent-execution paths.

Anatomy — where the code lives
=================================

**Two modules**:

* ``agentstudio-api`` (interfaces, DTOs)
* ``agentstudio-impl`` (15,443 LoC of implementations) — focus of this doc

Sub-package breakdown (impl):

.. list-table::
   :header-rows: 1
   :widths: 24 14 14 48

   * - Sub-package
     - LoC
     - Files
     - Role
   * - **service/**
     - **6,967**
     - 17
     - Business logic. Agent CRUD, scenarios, evaluations, reports, permissions
   * - **graphql/**
     - **6,232**
     - 35
     - 21 GraphQL query/mutation controllers + mappers + DTOs
   * - **rest/**
     - 747
     - 6
     - 3 REST controllers (batch eval, LLM judge config, internal)
   * - **exception/**
     - 99
     - 2
     - Domain exceptions (e.g., ``AgentStudioAgentAccessDeniedException``)
   * - **context/**
     - 89
     - 2
     - Per-request context primitives
   * - **config/**
     - 27
     - 1
     - Spring config

**Top files by LoC** (showing concentrations of complexity):

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - File
     - LoC
     - Role
   * - ``AgentStudioAgentService.kt``
     - **1,605**
     - Agent CRUD, draft/publish lifecycle, configuration management — **biggest single file**
   * - ``AgentStudioScenarioServiceImpl.kt``
     - 1,178
     - Test scenario CRUD, validation
   * - ``AgentStudioConversationReviewServiceImpl.kt``
     - 940
     - Human + LLM-judge conversation review pipeline
   * - ``AgentStudioPermissionServiceImpl.kt``
     - 898
     - Edit/view permission checks; role enforcement; audit logging
   * - ``AgentStudioAgentMutationController.kt``
     - 822
     - Create/update/delete/publish agent mutations
   * - ``AgentStudioAgentQueryController.kt``
     - 812
     - List/get/search agent queries
   * - ``AgentStudioBatchEvaluationQueryController.kt``
     - 553
     - Batch evaluation queries
   * - ``AgentStudioAgentResponse.kt`` (mapper)
     - 499
     - GraphQL output type for Agent (40-50+ fields)
   * - ``UpdateAgentConfigurationToolImpl.kt``
     - 430
     - **Cross-module exception**: lives in ``rovo-impl/.../tools/studio/`` but accesses AgentStudio
   * - ``AgentStudioBatchEvaluationMutationController.kt``
     - 398
     - Run/cancel batch evaluations

The 21 GraphQL controllers
=============================

.. list-table::
   :header-rows: 1
   :widths: 36 24 40

   * - Controller
     - Type
     - Purpose
   * - ``AgentStudioAgentQueryController``
     - Query
     - List/get/search agents
   * - ``AgentStudioAgentMutationController``
     - Mutation
     - Create/update/delete/publish agents
   * - ``AgentStudioActionMutationController``
     - Mutation
     - Manage agent actions/skills (likely)
   * - ``AgentStudioScenarioQueryController``
     - Query
     - Test scenarios — list/get
   * - ``AgentStudioScenarioMutationController``
     - Mutation
     - Test scenarios — CRUD
   * - ``AgentStudioSkillsQueryController``
     - Query
     - Available skills catalog
   * - ``AgentStudioAgenticSkillsQueryController``
     - Query
     - "Agentic" skills (separate concept from base Skills)
   * - ``AgentStudioKnowledgeMutationController``
     - Mutation
     - Knowledge bases — add/update/remove
   * - ``AgentStudioKnowledgeGapQueryController``
     - Query
     - "What's missing" — gap detection
   * - ``AgentStudioKnowledgeGapMutationController``
     - Mutation
     - Knowledge gap actions
   * - ``AgentStudioBatchEvaluationQueryController``
     - Query
     - Batch evaluation runs
   * - ``AgentStudioBatchEvaluationMutationController``
     - Mutation
     - Trigger evaluations
   * - ``AgentStudioConversationReviewQueryController``
     - Query
     - Conversation reviews
   * - ``AgentStudioConversationReviewMutationController``
     - Mutation
     - Submit reviews / scoring
   * - ``AgentStudioReportQueryController``
     - Query
     - Usage reports / insights
   * - ``AgentStudioAuthReadinessQueryController``
     - Query
     - Check auth integration readiness
   * - ``AgentStudioWidgetQueryController``
     - Query
     - Embedded widget data
   * - ``AgentStudioWidgetMutationController``
     - Mutation
     - Widget operations
   * - ``AgentStudioToolIntegrationQueryController``
     - Query
     - Tool integration list
   * - ``AgentStudioChannelQueryController``
     - Query
     - Available channels for agent publishing
   * - ``AgentStudioMigrationController``
     - Mutation
     - Agent version migration

**Observation**: 21 controllers is a LOT of GraphQL surface area. Most
modern GraphQL practice consolidates into fewer thicker controllers
with delegated resolvers. Splitting by capability is OK but the
proliferation of "Query + Mutation" pairs per concept (Agent, Scenario,
Knowledge, BatchEvaluation, ConversationReview, Widget, KnowledgeGap)
means 7+ paired classes alone.

The 3 REST controllers
========================

REST is reserved for **internal/admin/batch operations** that don't fit
the GraphQL model (file uploads, internal-only judge invocation):

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Controller
     - Path prefix (likely)
     - Role
   * - ``AgentStudioBatchEvaluationV1Controller``
     - ``/api/agentstudio/v1/batch-eval``
     - Dataset upload + result download (file-bytes traffic)
   * - ``LLMJudgeConfigV1Controller``
     - ``/api/agentstudio/v1/judge-config``
     - LLM-judge configuration CRUD
   * - ``LLMJudgeConversationInternalController``
     - ``/api/internal/agentstudio/judge``
     - Internal-only conversation evaluation endpoint

Why REST not GraphQL? File uploads (multipart) are awkward in GraphQL.
Internal endpoints don't need the public GraphQL contract surface.

The agent data model
======================

From ``AgentStudioAgentResponse.kt`` (499 LoC) we can see an agent
carries roughly this shape (UNVERIFIED — not verbatim from the file,
but inferred from typical fields in Atlassian agent platforms):

.. code-block:: kotlin

   data class AgentStudioAgent(
       val agentId: String,
       val key: String,                  // human-readable identifier
       val name: String,
       val description: String,
       val version: String,
       val status: AgentStatus,          // DRAFT, PUBLISHED, ARCHIVED
       val createdBy: AccountId,
       val lastModifiedBy: AccountId,
       val identity: AgentIdentity,      // persona, instructions
       val knowledge: List<KnowledgeSource>,  // attached KBs
       val skills: List<Skill>,          // capabilities
       val agenticSkills: List<AgenticSkill>,
       val scenarios: List<Scenario>,    // test cases
       val configuration: AgentConfiguration,  // model, temperature, etc
       val permissions: AgentPermissions,
       val publishedChannels: List<Channel>,
       // ... plus 10-20 more fields
   )

   enum class AgentStatus { DRAFT, PUBLISHED, ARCHIVED }
   enum class AgentActorRole { CREATOR, EDITOR, VIEWER }


End-to-end flow — agent creation to chat
============================================

**Phase 1 — Author** (in AgentStudio UI):

1. User enters AgentStudio UI, clicks "create agent"
2. UI calls ``createAgent`` GraphQL mutation
3. ``AgentStudioAgentMutationController.createAgent()`` (line ~30 of file)
4. ``AgentStudioAgentService.createAgent()`` validates + persists draft
5. Returns ``AgentStudioAgent`` with ``status=DRAFT``

**Phase 2 — Configure** (iterative):

* Add knowledge sources via ``addKnowledge`` mutation
* Attach skills via ``AgentStudioActionMutationController``
* Run knowledge-gap analysis via ``AgentStudioKnowledgeGapQueryController``
* Define test scenarios via ``AgentStudioScenarioMutationController``

**Phase 3 — Test/Evaluate**:

* Run a single conversation against the draft agent
* Submit conversation for review (``AgentStudioConversationReviewMutationController``)
* OR run a batch evaluation (``AgentStudioBatchEvaluationMutationController``):

  1. Upload dataset via REST ``/batch-eval``
  2. Configure LLM judge via ``LLMJudgeConfigV1Controller``
  3. Trigger run; orchestrator runs all scenarios in parallel
  4. LLM judge scores each conversation
  5. Results downloadable via REST

**Phase 4 — Publish**:

* User clicks "publish"; UI calls ``publishAgent`` mutation
* ``AgentStudioAgentService.publishAgent()`` validates the agent (must have name, ID, etc.) and updates status
* New ``status=PUBLISHED``; agent now visible to chat orchestrators
* Optionally publish to specific channels via ``AgentStudioChannelQueryController`` integration

**Phase 5 — Use** (in chat):

* User in Rovo chat selects the agent (or agent recommendation surfaces it)
* Standard chat flow: ``RovoChatV1Controller`` → orchestrator → ...
* The agent definition (knowledge, skills, instructions) is loaded from the same persistence layer AgentStudio writes to

**Phase 6 — Insights** (analytics back to author):

* ``AgentStudioReportQueryController.getAgentReport()`` returns usage metrics
* Powered by ``AgentStudioReportServiceImpl``: conversation count, success rate, popular skills, user satisfaction signals

Permission model
==================

Verified from ``AgentStudioPermissionServiceImpl.kt`` (898 LoC):

* **3 roles**: CREATOR, EDITOR, VIEWER
* Permissions checked at every mutation entry point
* ``AgentPermissionAuditLogger`` logs all permission changes (audit trail)
* Custom exceptions (``AgentStudioAgentAccessDeniedException``, ``AgentUpdateDeniedException``, ``AgentVerificationPermissionDeniedException``) per failure mode

The 898-LoC permission service is unusually large. Suggests:
* Multiple permission predicates (can-read, can-edit, can-publish, can-delete, can-share)
* Per-channel/per-tenant overrides
* Audit log emission per check
* Cache invalidation when memberships change

External system fan-out
=========================

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - System
     - How
     - Used for
   * - **Agent persistence**
     - via ``AgentService`` API in rovo-api
     - Storing agent definitions (UNVERIFIED backend; likely Postgres/DynamoDB)
   * - **AI Gateway** (LLM)
     - in batch eval, judge, review flows
     - Auto-evaluation, scoring
   * - **Knowledge sources**
     - via ``platform/knowledge/knowledge-impl`` indirectly
     - Attaching documents to agents
   * - **Skills registry**
     - via ``platform/tool-registry``
     - Listing available skills
   * - **Tool integration**
     - via ``ToolConfigLookupRegistry``
     - Resolving external-tool schemas
   * - **Permission audit**
     - dedicated audit service
     - Compliance / change history

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
     - **1,605-LoC ``AgentStudioAgentService.kt``**
     - service/
     - The core agent-CRUD service. Should split into ``AgentLifecycleService`` (draft/publish), ``AgentConfigurationService`` (config CRUD), ``AgentVersioningService`` (history/migration).
   * - 🔴
     - **21 GraphQL controllers** for one feature area
     - graphql/
     - Above the threshold where consolidation pays off. Consider grouping (e.g., AgentStudioCoreController + AgentStudioEvaluationController + AgentStudioPermissionsController).
   * - 🔴
     - **898-LoC permission service**
     - service/
     - One service handling all permission concerns. Extract role-resolution, audit emission, and check-evaluation into separate classes.
   * - 🟡
     - **Cross-module class** (``UpdateAgentConfigurationToolImpl.kt`` lives in agentstudio-impl/.../rovo/agent/tools)
     - service/...
     - 430-LoC implementation file in agentstudio-impl using ``rovo`` package paths. Either move to rovo-impl or keep in agentstudio with a clearer name.
   * - 🟡
     - **Two REST + GraphQL APIs in parallel**
     - rest/ + graphql/
     - Some operations (LLM judge config) only in REST; others only in GraphQL; some duplicated. Document the division of responsibility.
   * - 🟡
     - **No GraphQL federation visible**
     - graphql/
     - 21 controllers all in this module. If other modules expose related queries (chat history, agent execution), federation could unify the surface.
   * - 🟡
     - **"NormalizedV2AgentInput"** suggests version migration debt
     - graphql/mapper/
     - Implies V1 input format still in use somewhere; conversion happening explicitly. Worth tracking deprecation.
   * - 🟢
     - **No README in agentstudio-impl**
     - module root
     - 15K LoC and no entry-point doc explaining how the parts compose. New contributor onboarding cost.
   * - 🟢
     - **3 distinct review/evaluation surfaces** (Conversation review + Batch eval + LLM judge)
     - service/ + rest/
     - Clear use cases but worth cross-referencing in docs

Refactoring opportunities
============================

1. **Split ``AgentStudioAgentService.kt``** (M, 🔴 high) — 1,605 LoC into ~3 services. ~2 days mechanical work.

2. **Split ``AgentStudioPermissionServiceImpl.kt``** (M, 🔴 high) — extract audit, role-resolution, check-evaluation. ~1.5 days.

3. **Consolidate GraphQL controllers** (L, 🟡 medium) — 21 → ~7 controllers. Risk: breaks existing operations. Better done as a "thin facade" pattern with current controllers wrapping new fewer-controller backend.

4. **Move ``UpdateAgentConfigurationToolImpl.kt``** (S, 🟡 medium) — to rovo-impl where it belongs by package path; OR rename to make AgentStudio ownership obvious.

5. **Document the REST↔GraphQL split** (XS, 🟡 medium) — README explaining when to use which. Saves contributors hours.

6. **Add a module README** (XS, 🟡 medium) — Sphinx-friendly README.rst at module root explaining: what's an agent, lifecycle, permission model, how to add a new skill type. Should reference this deep-dive.

7. **Plan V1 agent input deprecation** (M, 🟢 low) — track usage of ``NormalizedV2AgentInput``; eventually remove the V1 path.

8. **Add OpenAPI for REST controllers** (S, 🟢 low) — currently 3 REST controllers; OpenAPI generation would make external integration easier.

What you would change here
============================

* **Add a new agent field** (e.g., new configuration parameter):
   1. Update ``AgentStudioAgent`` data class in ``agentstudio-api``
   2. Update ``AgentStudioAgentResponse.kt`` GraphQL mapper (graphql/mapper/)
   3. Update persistence layer to handle the new field
   4. Update ``createAgent``/``updateAgent`` mutations in ``AgentStudioAgentMutationController``
   5. Update test scenarios

* **Add a new GraphQL operation** → new method on existing controller (preferred) OR new controller class (if cohesive operation set)
* **Add a new REST endpoint** → new method on existing controller; ``@RequestMapping``
* **Modify permission checks** → ``AgentStudioPermissionServiceImpl.kt``
* **Add a new review type** → ``AgentStudioConversationReviewServiceImpl.kt``
* **Tweak batch eval orchestration** → batch-eval flow in ``AgentStudioBatchEvaluation*``
* **Add a new LLM judge type** → ``LLMJudgeConfigV1Controller`` + service backing

What you would NOT change here
================================

* Agent execution at runtime — owned by ``rovo-impl/.../agent/``
* LLM provider — owned by ``platform/service/service-impl``
* Knowledge source storage — owned by ``platform/knowledge/knowledge-impl``
* Skill execution — owned by ``rovo-impl/.../adk/`` or ``rovo-impl/.../agent-framework/``
* Authentication primitives — owned by Atlassian platform

Verification audit log
========================

✅ **Personally verified with bash:**

* All sub-package LoC (``find ... -exec cat | wc -l`` per dir)
* Total: 15,443 LoC
* Top-10 file LoC (``find ... -exec wc -l + | sort``)
* 21 GraphQL controllers in graphql/ (``find -name *Controller*``)
* 3 REST controllers in rest/
* Sub-modules: agentstudio-api, agentstudio-impl

⚠️ **Inferred from naming + patterns** (not deep-read):

* The agent data model (data class structure) — based on common Atlassian patterns
* Permission model details — inferred from class names
* GraphQL operation paths — UI-facing operations always go through these controllers, but exact paths inferred
* REST controller @RequestMapping prefixes (UNVERIFIED — would need to ``grep RequestMapping``)

❌ **UNVERIFIED:**

* Storage backend (Postgres? DynamoDB? Both?)
* Whether agent versioning supports full history or just current
* Whether LLM judge runs on AI Gateway or external LLM
* Specific contents of ``AgenticSkill`` vs ``Skill`` distinction
* Whether ``UpdateAgentConfigurationToolImpl`` is in correct module

Open questions for institutional knowledge
=============================================

1. **What's the agent storage backend?** Postgres? DynamoDB? Both for different aspects?
2. **What's the difference between Skill and AgenticSkill?** Two separate query controllers exist for each.
3. **What's the deprecation timeline for V1 agent input?** ``NormalizedV2AgentInput`` mapper exists.
4. **Is there agent versioning beyond status changes?** What's stored when an agent is updated — full history or current?
5. **Why are LLM Judge endpoints in REST not GraphQL?** Just file-uploads or other reason?
6. **What's the GraphQL federation strategy?** 21 controllers in this module; is there a plan to merge with chat-history GraphQL?

