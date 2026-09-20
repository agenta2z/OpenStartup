.. _feature-jsm-platform:

==================================================================
JSM Platform — Jira Service Management agent platform
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: **69,395 LoC across 351 files** (largest product-tier module after rovo-impl)
:Module: ``modules/product/jsm/`` (jsm-api + jsm-impl)
:Triage score: **24/25 — product-critical, plan-driven workflow**

.. contents:: On this page
   :local:
   :depth: 2

What JSM Platform IS (in one paragraph)
==========================================

The JSM Platform is the **Jira Service Management agent platform** —
the AI for IT-service-management workflows. Where CSM is "external
customer asks help question", JSM is "internal employee files an IT
ticket and the agent runs a multi-step service workflow to resolve
it" (e.g., "I need a new laptop" → triggers a journey: validate
request → check inventory → create approval → notify procurement →
update ticket). The defining JSM concept is the **Journey** — a
deterministic, multi-step plan that combines tool execution, human
approvals, and ticket updates. JSM has its own **plan-driven
orchestrator** (distinct from Marathon's LLM-loop or SAIN's
hybrid-orchestration), with **plan quality gates**, **runtime plan
editing** (with full undo/redo), **execution memory** for stateful
multi-turn workflows, and a **specialized HR orchestrator variant**.
JSM is the **largest product-tier module** at 69K LoC across 351
files — but file-density is high (avg 198 LoC/file vs CSM's 119 — JSM
files are bigger).

Anatomy — module structure
==============================

**2 sub-modules**:

.. list-table::
   :header-rows: 1
   :widths: 32 16 16 36

   * - Module
     - LoC
     - Files
     - Role
   * - **jsm-api**
     - small
     - ~30
     - Contracts, journey/plan DTOs
   * - **jsm-impl**
     - **~69K**
     - **~321**
     - All implementation: orchestrator, minions, services, journey CRUD

**Top-20 files by LoC** (verified):

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - File
     - LoC
     - Role
   * - ``JourneyCraftingMinion.kt``
     - **2,671**
     - **🏆 Largest single file in JSM (and biggest minion in entire codebase).** Core journey generation + transformation logic
   * - ``BaseComposerAgent.kt``
     - 2,046
     - Foundation for multi-agent composition strategies
   * - ``PlanQualityGateService.kt``
     - 1,168
     - Plan validation + quality enforcement before execution
   * - ``JourneyRecommendationService.kt``
     - 1,007
     - Personalized journey selection
   * - ``WorkItemUpdateServiceImpl.kt``
     - 956
     - Ticket / work-item state management
   * - ``RunbookSearchServiceImpl.kt``
     - 899
     - Knowledge base search + ranking (JSM's equivalent of CSM search)
   * - ``JsmAgentExecutorImpl.kt``
     - 885
     - Step-by-step plan execution engine
   * - ``JSMServiceDeskComposerAgent.kt``
     - 865
     - Multi-agent coordination for service desk
   * - ``PlanEditorMinion.kt``
     - 857
     - **Runtime plan modification** (the editor for live journeys)
   * - ``SimilarIssuesKnowledgeSource.kt``
     - 850
     - Issue deduplication + recommendations
   * - ``PlanningStateHandler.kt``
     - 815
     - State machine for planning phase
   * - ``PlanExecutionService.kt``
     - 741
     - Orchestrates plan step execution
   * - ``JourneyReferenceDocumentBuilderService.kt``
     - 736
     - Context-aware journey documentation builder
   * - ``NextStepResolver.kt``
     - 727
     - Determines next executable step in plan
   * - ``JsmConversationStateUpdater.kt``
     - 716
     - Conversation state synchronization
   * - ``ExecutionMemoryService.kt``
     - 693
     - **Execution-scoped memory** (per-(user, journey)) — confirmed in Memory deep-dive
   * - ``StepResultHandler.kt``
     - 665
     - Post-step state transitions + error handling
   * - ``JsmAiHrOrchestratorAgent.kt``
     - 658
     - **HR-specific orchestration variant** (separate path for HR workflows)
   * - ``StepExecutor.kt``
     - 639
     - Individual step execution framework
   * - ``QueryFormulationService.kt``
     - 620
     - Converts user intent to search queries
   * - ``JourneyPersonalizationMinion.kt``
     - 542
     - Personalizes JSM journeys (confirmed in Memory deep-dive)

The 12 main feature areas
=============================

**1. Journey Crafting & Generation** (~4,800 LoC)
----------------------------------------------------

* ``JourneyCraftingMinion.kt`` (2,671) — **biggest minion**
* ``JourneyCraftingTransformer.kt``, ``JourneyCraftingModels.kt``
* ``PlanGeneratorV2.kt``

Synthesizes multi-step solution journeys from user requests +
knowledge sources. The core "given a user need, generate a plan"
capability.

**2. Plan Quality & Validation** (~1,200 LoC)
------------------------------------------------

* ``PlanQualityGateService.kt`` (1,168)

Enforces correctness gates before execution. Critical for
determinism in service workflows: validates plan steps make sense,
required fields populated, no impossible transitions, etc. **Without
this gate, generated plans could execute incorrectly with
production consequences (wrong approvals, wrong tickets created)**.

**3. Journey Personalization & Recommendation** (~1,500 LoC)
----------------------------------------------------------------

* ``JourneyRecommendationService.kt`` (1,007)
* ``JourneyPersonalizationMinion.kt`` (542)

Selects optimal journey based on user context, historical data,
preference signals. Different employees get different journey
variants for the same request type.

**4. Multi-Agent Composition** (~3,000 LoC)
-----------------------------------------------

* ``BaseComposerAgent.kt`` (2,046)
* ``JSMServiceDeskComposerAgent.kt`` (865)
* ``JsmAiHrOrchestratorAgent.kt`` (658)

Coordinates multiple specialized agents (planning, execution, HR-specific).
**HR is a first-class variant** — JSM has dedicated infrastructure
for HR service workflows distinct from IT.

**5. Orchestration & State Management** (~2,700 LoC)
------------------------------------------------------

* ``JsmConversationStateUpdater.kt`` (716)
* ``ExecutionMemoryService.kt`` (693)
* ``PlanningStateHandler.kt`` (815)

Manages conversation state, execution context, state machine transitions.
Stateful — unlike a typical chat turn, JSM workflows persist across
many turns and back-end events.

**6. Plan Execution Engine** (~2,500 LoC)
--------------------------------------------

* ``JsmAgentExecutorImpl.kt`` (885)
* ``StepExecutor.kt`` (639)
* ``PlanExecutionService.kt`` (741)
* ``NextStepResolver.kt`` (727)
* ``StepResultHandler.kt`` (665)

Executes plans step-by-step with error recovery + result aggregation.
Each step has its own execution context, error handling, and result
shape.

**7. Knowledge Integration** (~2,000 LoC)
--------------------------------------------

* ``RunbookSearchServiceImpl.kt`` (899)
* ``SimilarIssuesKnowledgeSource.kt`` (850)
* ``JourneyReferenceDocumentBuilderService.kt`` (736)

Knowledge sources for JSM:

* **Runbooks** — operational procedures (different from generic Confluence pages)
* **Similar issues** — find duplicates / related tickets to avoid recreating work
* **Reference documents** — context for journey crafting

**8. Work Item / Ticket Management** (~2,500 LoC)
----------------------------------------------------

* ``WorkItemUpdateServiceImpl.kt`` (956) — ticket state management
* Plus ticket lifecycle handlers + queue management

JSM agent ultimately **modifies Jira tickets** as part of its workflow.

**9. Search & Query Formulation** (~2,000 LoC)
------------------------------------------------

* ``QueryFormulationService.kt`` (620)
* ``RunbookSearchMinion.kt``

Converts NL intent into structured queries for runbook + ticket search.

**10. Plan Editing & Modification** (~1,200 LoC) — **THE STANDOUT JSM CAPABILITY**
-----------------------------------------------------------------------------------

* ``PlanEditorMinion.kt`` (857)

Enables **runtime plan adjustments + re-planning** during execution.
This is JSM's defining capability — plans are NOT static. As
execution progresses (and as the user provides new info), the plan
can be edited.

**Verified: 13 journey-handler operations** (in
``minion/journey/handler/``):

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Handler
     - Operation
   * - ``CreateJourneyHandler``
     - Create new journey from scratch
   * - ``UpdateJourneyHandler``
     - Modify existing journey
   * - ``UpdateJourneyNameHandler``
     - Rename
   * - ``UpdateJourneyTriggerHandler``
     - Modify when journey activates
   * - ``DeleteJourneyHandler``
     - Delete
   * - ``InsertJourneyHandler``
     - Insert step at position
   * - ``BulkUpdateJourneyItemsHandler``
     - Batch updates
   * - ``PublishJourneyHandler``
     - Promote DRAFT → PUBLISHED
   * - ``UndoJourneyHandler``
     - **Undo last operation**
   * - ``RedoJourneyHandler``
     - **Redo undone operation**
   * - ``JourneyOperationHandler``
     - Base class
   * - + 2 more (recommendation handler, etc.)

This is a **full CRUD + undo/redo system for journeys** — sophisticated
beyond what most agent platforms have.

**11. Status & Event Handling** (~1,000+ LoC)
------------------------------------------------

* ``StatusUpdateHandler``, enricher minions

Tracks status updates + enriches execution events with metadata.
Important for audit trails ("who approved this? when? based on what?").

**12. Composition & REST/GraphQL APIs** (~5,000+ LoC)
--------------------------------------------------------

REST controllers, GraphQL schemas, configuration. Surfaces functionality
to client applications.

The plan-driven orchestrator (vs Marathon / SAIN)
=====================================================

JSM's orchestrator is **fundamentally different** from Marathon and SAIN:

.. list-table::
   :header-rows: 1
   :widths: 24 24 26 26

   * - Aspect
     - Marathon
     - SAIN
     - **JSM**
   * - Execution model
     - LLM-loop (LLM picks next tool)
     - Hybrid (sometimes LLM, sometimes routed)
     - **Plan-driven** (plan generated upfront, then executed step-by-step)
   * - State
     - Stateless within turn
     - Mostly stateless
     - **Stateful across many turns** (ExecutionMemoryService)
   * - User approval
     - LLM mid-flow asks user
     - Same
     - **Built-in approval steps** (part of plan)
   * - Determinism
     - Low (LLM-driven)
     - Medium
     - **High** (validated plan)
   * - Editability mid-flow
     - Hard (LLM context only)
     - Hard
     - **First-class** (PlanEditorMinion)

JSM's **plan-driven model is appropriate for IT service management**
because workflows must be auditable, repeatable, and approvable.
Marathon's LLM-loop would be too unpredictable for "create a $5,000
PO" or "grant production database access".

End-to-end flow — typical JSM IT request
=============================================

User: *"I need a new laptop"*

1. **Intent parsing** → JsmAgentExecutor receives request
2. **Journey selection** → JourneyRecommendationService picks "laptop_request" journey
3. **Plan generation** → JourneyCraftingMinion synthesizes plan:

   a. Validate user is eligible
   b. Check inventory
   c. Create JSM ticket (DRAFT)
   d. Request manager approval (BLOCKING)
   e. Notify procurement
   f. Update ticket status

4. **Plan validation** → PlanQualityGateService rejects if invalid
5. **Plan execution** → PlanExecutionService runs steps:

   a. StepExecutor executes step 1 (eligibility check)
   b. StepResultHandler stores result, decides next step
   c. NextStepResolver finds step 2

6. **Approval blocker** → Plan execution pauses; ticket waits
7. **Manager approves** → Webhook triggers ExecutionMemoryService update
8. **Plan resumes** → StepExecutor continues from step 5
9. **Ticket updated** → WorkItemUpdateServiceImpl finalizes

Sequence diagram
==================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as Employee
       participant Chat as JSM Chat<br/>Endpoint
       participant Exec as JsmAgentExecutorImpl<br/>(885 LoC)
       participant Rec as JourneyRecommendation<br/>Service (1,007 LoC)
       participant Craft as JourneyCraftingMinion<br/>(2,671 LoC)
       participant Gate as PlanQualityGate<br/>Service (1,168 LoC)
       participant Plan as PlanExecution<br/>Service (741 LoC)
       participant Step as StepExecutor<br/>(639 LoC)
       participant Mem as ExecutionMemory<br/>Service (693 LoC)
       participant WI as WorkItemUpdate<br/>ServiceImpl (956 LoC)
       participant Mgr as Manager (human)

       U->>Chat: "I need a new laptop"
       Chat->>Exec: handle(req, ctx)
       Exec->>Rec: recommendJourney(intent, user)
       Rec-->>Exec: "laptop_request" journey

       Exec->>Craft: craftPlan(journey, user, ctx)
       Craft->>Craft: synthesize 6-step plan
       Craft-->>Exec: Plan

       Exec->>Gate: validate(plan)
       alt invalid
           Gate-->>Exec: REJECTED + reasons
           Exec-->>U: "Cannot proceed: <reason>"
       else valid
           Gate-->>Exec: ACCEPTED

           Exec->>Plan: execute(plan, ctx)
           loop for each non-blocking step
               Plan->>Step: execute(step)
               Step-->>Plan: result
               Plan->>Mem: persistState(plan, step, result)
           end

           Plan->>WI: createTicket(DRAFT, "laptop request")
           WI-->>Plan: ticketId

           Plan->>Mgr: requestApproval (async, blocking)
           Note over Plan: Plan execution pauses;<br/>ticket in WAITING_APPROVAL state

           Mgr-->>Mem: approvalWebhook(approved=true)
           Mem->>Plan: resume(plan, fromStep=5)

           Plan->>Step: notifyProcurement
           Step-->>Plan: ok
           Plan->>WI: updateStatus(IN_PROGRESS)
           WI-->>Plan: ok

           Plan-->>U: "Approved + procurement notified"
       end

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - System
     - How
     - Used for
   * - **Jira Cloud REST**
     - via WorkItemUpdateServiceImpl
     - Ticket creation/updates
   * - **AI Gateway** (LLM)
     - via JourneyCraftingMinion
     - Plan generation
   * - **Knowledge sources** (Confluence, runbooks, similar issues)
     - via search services
     - Knowledge retrieval
   * - **Manager / approver workflow** (email, Slack)
     - via async approval messaging
     - Human approval blocking
   * - **Procurement / IT systems**
     - via custom integrations
     - Downstream actions
   * - **Statsig**
     - per-feature FF
     - Per-tenant rollout
   * - **Compass / Opsgenie** (likely)
     - via service-context lookup
     - Service ownership context
   * - **Embedding / vector search**
     - via SimilarIssuesKnowledgeSource
     - Issue dedup

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
     - **2,671-LoC ``JourneyCraftingMinion.kt``**
     - minion/
     - **🏆 Biggest minion in entire codebase.** Should split: JourneyParser, PlanSynthesizer, ContextEnricher, FormatRenderer.
   * - 🔴
     - **2,046-LoC ``BaseComposerAgent.kt``**
     - composer/
     - Same split principle.
   * - 🔴
     - **1,168-LoC ``PlanQualityGateService.kt``**
     - service/
     - Per-validator-rule split would be much more maintainable.
   * - 🔴
     - **3 distinct orchestrator agents** (BaseComposerAgent, JSMServiceDeskComposerAgent, JsmAiHrOrchestratorAgent)
     - composer/
     - Coexistence pattern same as SAIN's. Document intent: HR-specialized vs general?
   * - 🔴
     - **Plan editing has full undo/redo system** but no observable docs
     - minion/journey/handler/
     - Sophisticated capability that's not surfaced anywhere.
   * - 🟡
     - **JSM has its own search** (RunbookSearchServiceImpl) separate from Rovo + CSM
     - service/
     - Same problem (knowledge search) solved 3 ways across the codebase. Convergence opportunity.
   * - 🟡
     - **Average file size is 198 LoC** (vs 119 in CSM, 144 in rovo-impl)
     - module
     - JSM files are bigger; refactoring needed.
   * - 🟡
     - **JSM has its own memory** (ExecutionMemoryService) separate from collection/conversation memory
     - service/
     - 4th memory variant (after Collection, Conversation, Procedural). Worth consolidation review.
   * - 🟡
     - **PlanGeneratorV2 implies V1 exists** somewhere
     - PlanGeneratorV2.kt
     - Migration plan? Sunset date?
   * - 🟡
     - **No clear entry-point controller** in top files
     - rest/
     - Top-20 has no controller > 600 LoC. Either small controllers (good) or scattered across many files.
   * - 🟢
     - **Plan-driven model is the right choice** for IT service workflows
     - design
     - Auditability + determinism + approvals = critical for service management.
   * - 🟢
     - **Undo/redo for journey editing** is sophisticated UX investment
     - minion/journey/handler/
     - Most agent platforms don't have this.
   * - 🟢
     - **HR specialized variant** (JsmAiHrOrchestratorAgent) shows commitment to per-vertical adaptation
     - composer/
     - Suggests JSM serves both IT and HR — two product lines on same platform.

Refactoring opportunities
============================

1. **Split ``JourneyCraftingMinion.kt``** (XL, 🔴 high) — 2,671 LoC into 4-5 files. ~5-7 days; biggest single refactoring opportunity in codebase.

2. **Split ``BaseComposerAgent.kt``** (L, 🔴 high) — 2,046 LoC. ~4-5 days.

3. **Split ``PlanQualityGateService.kt``** (M, 🔴 high) — per-validator-rule classes. ~3 days.

4. **Document journey editing UX** (XS, 🟡 medium) — full CRUD + undo/redo deserves a UX doc. ~1 day.

5. **Consolidate JSM search with Rovo + CSM search** (XL, 🟡 medium) — 3-way duplication; major effort. ~1 month.

6. **Audit ExecutionMemoryService vs Collection/Conversation memory** (M, 🟡 medium) — ~1 week.

7. **Document HR vs IT orchestrator split** (XS, 🟡 medium) — when does which fire? ~half day.

8. **Audit V1 vs V2 plan generators** (S, 🟡 medium) — same as JQL audit pattern.

9. **Modularize jsm-impl** (XL, 🟢 low) — per-domain Gradle sub-modules. ~3-4 weeks.

10. **Add Sphinx journey-lifecycle diagram** (XS, 🟢 low) — visualize Create → Validate → Execute → Edit → Publish.

What you would change here
============================

* **Add a new journey type** (e.g., "office_relocation_request"):
   1. Add to journey registry / config
   2. Add Pebble template at ``resources/templates/jsm/journey/office_relocation.pebble``
   3. Add per-step handlers if non-standard steps needed
   4. Test plan quality gate

* **Modify journey crafting prompt** → ``resources/templates/jsm/journey/...pebble``

* **Add new plan validation rule** → ``PlanQualityGateService.kt``

* **Add new plan step type** → step type enum + ``StepExecutor`` dispatch

* **Add new journey editing operation** → new ``XxxJourneyHandler.kt`` in ``minion/journey/handler/``

* **Tune approval blocking timeout** → ``PlanExecutionService`` config

* **Modify HR orchestrator behavior** → ``JsmAiHrOrchestratorAgent.kt``

* **Add new ticket field update** → ``WorkItemUpdateServiceImpl.kt``

What you would NOT change here
================================

* Marathon orchestrator — owned by ``rovo-impl/.../agent/orchestrators/marathon/``
* SAIN orchestrators — owned by ``rovo-impl/.../product/rovo/sain/``
* CSM agent — owned by ``csm-impl/`` (separate platform)
* Jira Cloud REST API — owned by Jira Cloud
* Knowledge sources (Confluence, Jira) — owned by external services
* Approval messaging (email, Slack) — likely external systems

Verification audit log
========================

✅ **Personally verified with bash:**

* Total LoC: 69,395 across 351 files (find + cat + wc)
* JourneyCraftingMinion.kt is 2,671 LoC (largest minion in entire codebase)
* Top-20 file LoC counts (find + sort)
* 13 journey handler operations (Create/Update/Delete/Bulk/Publish/Undo/Redo/Insert/UpdateName/UpdateTrigger)
* JsmAiHrOrchestratorAgent.kt is 658 LoC (HR variant exists)
* PlanGeneratorV2 exists (V2 in name)
* Module structure: api/impl pattern

⚠️ **Inferred from sub-agent + naming**:

* The 12 feature-area categorization (sub-agent's grouping; my organization)
* End-to-end flow ordering (responsibility-based inference)
* The "approval blocking" semantics — naming inference; not source-verified
* The HR vs IT scope split — naming inference
* Per-step execution model details (StepExecutor + NextStepResolver inference)
* "Plan-driven" vs "LLM-loop" framing — architectural inference

❌ **UNVERIFIED:**

* The exact plan validation rules in PlanQualityGateService (1,168 LoC)
* The relationship between BaseComposerAgent, JSMServiceDeskComposerAgent, JsmAiHrOrchestratorAgent
* PlanGeneratorV1 existence + deprecation status
* The approval-webhook mechanics (which external system?)
* Per-tenant rollout state of journey-editing
* Whether undo/redo is per-user or per-journey
* The relationship between ExecutionMemoryService and other memory types
* The "Runbook" content source

Open questions for institutional knowledge
=============================================

1. **What's the HR vs IT orchestrator split logic** — when does ``JsmAiHrOrchestratorAgent`` fire vs ``JSMServiceDeskComposerAgent``?
2. **Is ``PlanGeneratorV1`` still active**? Deprecation timeline?
3. **What's the typical journey length** (number of steps)?
4. **What % of journeys have approval steps**?
5. **What external system** handles the approval messaging (email? Slack? in-app)?
6. **What's the undo/redo scope** — per-user-session, per-journey, per-tenant?
7. **What's the most-used journey type** in production?
8. **How are runbooks different from generic Confluence pages**?
9. **Is HR a separate product or just a vertical of JSM**?
10. **What's the relationship between BaseComposerAgent and the 2 specific composers**?

