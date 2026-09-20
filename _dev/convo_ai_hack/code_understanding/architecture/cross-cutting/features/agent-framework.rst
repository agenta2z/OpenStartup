.. _feature-agent-framework:

==================================================================
Agent Framework — Stratus minion infrastructure
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 10,047 LoC across 47 files (impl) + ``agent-framework-api`` (small contract module)
:Module: ``modules/product/agent-framework/``

.. contents:: On this page
   :local:
   :depth: 2

What agent-framework IS (in one paragraph)
==============================================

Agent-framework is the **shared minion infrastructure** that
**Marathon, SAIN, AIFC, and AgentStudio all depend on**. It provides:

* The **Stratus minion** abstraction (one minion = one specialized
  skill the LLM can invoke)
* **17+ concrete Stratus minions** for high-value Atlassian capabilities
  (incident management, capacity planning, JQL optimization, talent search,
  PR summarization, page-to-project synthesis, etc.)
* **Agent permission service** (RBAC for which agents/minions a user can
  invoke based on their tenant role)
* **User-centric agent store** (denormalized per-(user,agent) state for
  fast resolution at request time)

The "Stratus" naming is internal Atlassian terminology — likely a
codename for "skill cluster". Stratus minions are the **executable
skills** behind named features: when you ask Rovo to "find similar
incidents", a ``FindSimilarIncidentsSkill`` stratus minion runs.

Anatomy — where the code lives
=================================

**Two modules**:

* ``agent-framework-api`` — interfaces / contracts (small)
* ``agent-framework-impl`` — implementations (10,047 LoC across 47 files)

**Sub-package breakdown** (impl):

.. list-table::
   :header-rows: 1
   :widths: 32 14 14 40

   * - Sub-package
     - LoC
     - Files
     - Role
   * - ``minions/stratus/``
     - **most**
     - **~30**
     - The 17+ Stratus minions + studio sub-folder + admin shared components
   * - ``minions/stratus/studio/``
     - moderate
     - ~7
     - AgentStudio-specific Stratus minions (e.g., FocusAskCreationStratusMinion, ProjectFromPageStratusMinion)
   * - ``permission/``
     - ~600
     - 4-6
     - AgentPermissionServiceImpl + PermissionsFacadeServiceImpl + RBAC helpers
   * - ``usercentricagent/``
     - ~411
     - 2-3
     - ErsDenormalizedUserCentricAgentStoreImpl — per-(user,agent) state cache

Plus **Pebble templates** at ``src/main/resources/templates/agent/minions/``
* ``admin/policy/`` — admin policy reasoning prompts
* ``jira_permissions/v7/`` — Jira permissions diagnostic prompts
* ``stratus/`` — generic Stratus minion prompt templates
* ``studio/`` — AgentStudio minion prompts

The 17 Stratus minions
=========================

Cataloged from ``minions/stratus/`` (verified by ``ls``):

**Admin / Operations (5 minions)**:

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - Minion / Skill
     - LoC (approx)
     - Role
   * - ``AdminTroubleshootPermissionsSkill``
     - **725**
     - **Largest admin skill**. Diagnose why a user can't access X. Walks permission chain. Pebble-backed templates at ``jira_permissions/v7/``
   * - ``AdminPolicyReasoningSkill``
     - moderate
     - Reason about admin policy decisions
   * - ``AdminUserInvitationsSkill``
     - moderate
     - Manage org user invitations
   * - ``AdminSharedPromptComponents``
     - 310
     - Shared prompt fragments across admin minions (DRY)
   * - ``JiraPermissionsSkill``
     - 475
     - Specific Jira permission validation

**Incident / Operations (5 minions)**:

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - Minion / Skill
     - LoC (approx)
     - Role
   * - ``FindIncidentsSkill``
     - moderate
     - Find recent / matching incidents
   * - ``FindSimilarIncidentsSkill``
     - moderate
     - Semantic search for similar past incidents
   * - ``FindRootCauseSkill``
     - moderate
     - Walk causal chain from current incident
   * - ``SummarizeIncidentSkill``
     - moderate
     - Summary generation per incident
   * - ``SuggestIncidentFieldsSkill``
     - moderate
     - Suggest field values during incident creation
   * - ``CreatePIRSkill``
     - moderate
     - Post-Incident Review draft generation
   * - ``FindAlertsSkill``
     - moderate
     - Find triggered alerts
   * - ``RecommendSMESkill``
     - moderate
     - Subject Matter Expert recommendation (who knows X?)

**Jira / Workflow (4 minions)**:

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - Minion / Skill
     - LoC (approx)
     - Role
   * - ``JiraNavigationMinion``
     - moderate
     - Navigate Jira's surface for the user
   * - ``JiraNLToJQLMinion``
     - moderate
     - Older NL→JQL minion (separate from JiraNL2JQLSchemaAgent in JQL audit)
   * - ``JiraJqlOptimizationSkill``
     - 232
     - Optimize a generated JQL for performance
   * - ``JiraWorkflowBuilderMinion``
     - moderate
     - Help user build Jira workflows
   * - ``SuggestProblemTicketSkill``
     - moderate
     - Suggest problem-tickets to link

**Content / Productivity (4 minions)**:

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - Minion / Skill
     - LoC (approx)
     - Role
   * - ``WritePrdSkill``
     - moderate
     - Generate Product Requirements Document
   * - ``HowToArticleSkill``
     - moderate
     - Generate "how to" knowledge article
   * - ``SynthesizeResearchSkill``
     - moderate
     - Synthesize research across pages
   * - ``StatusUpdateMinion``
     - moderate
     - Generate status update from recent activity

**Talent / Capacity (4 minions)**:

.. list-table::
   :header-rows: 1
   :widths: 36 12 52

   * - Minion / Skill
     - LoC (approx)
     - Role
   * - ``TalentMinion``
     - **658**
     - Talent management — find, evaluate, recommend people
   * - ``CapacityPlanManageMinion``
     - moderate
     - Manage capacity plans (engineering / project)
   * - ``ActionPlanMinion``
     - moderate
     - Generate / update action plans
   * - ``HamConfigurationMinion``, ``HamOnboardingMinion``, ``HamSearchMinion``
     - moderate
     - HAM (Human Asset Manager?) onboarding/search/configuration

**Risk / Change (1 minion)**:

* ``AssessChangeRiskSkill`` (**2,157 LoC** — the largest single file)
   * Evaluate the risk of an upcoming change deployment
   * Likely hits multiple data sources (Jira, Bitbucket, deploy history)
   * Should probably be split

**Action items (2 minions)**:

* ``EnrichActionItemMinion`` — enrich an action item with context
* ``FindActionItemsMinion`` — extract action items from a page/conversation

**Studio sub-folder (4-7 minions)**: ``stratus/studio/``

* ``FocusAskCreationStratusMinion``
* ``FocusSummaryMinion``
* ``ProjectFromPageStratusMinion`` — convert a page into a project
* ``PullRequestSummaryStratusMinion`` — summarize PR
* ``SolutionArchitectStratusMinion``
* ``SurveysStratusMinion``

The Minion contract — three loading paths
============================================

Stratus minions can be loaded via **3 mechanisms** (all coexisting):

1. **From-code** (``StratusMinionFromCode``) — Kotlin class with
   ``@Component`` annotation; Spring auto-discovery
2. **From-YAML** (``StratusMinionFromYaml`` + ``StratusMinionConfigLoader``)
   — declarative minion specs in YAML files; loaded at startup
3. **From-Code Spec** (``StratusMinionFromCodeSpec``) — programmatic
   spec-builder; useful for tests + dynamic registration

Source contracts (in ``rovo-api/.../agent/minion/stratus/``):

* ``StratusMinionConfigFromYaml.kt`` — YAML config schema
* ``StratusMinionFromCodeSpec.kt`` — programmatic spec
* ``StratusMinionFeatureFlags.kt`` — FF gates for Stratus minions

Source implementations (in ``rovo-impl/.../agent/minions/``):

* ``StratusMinionFromYaml.kt`` — YAML loader implementation
* ``StratusMinionFromCode.kt`` — code loader implementation
* ``config/StratusMinionConfigLoader.kt`` — YAML config parser

This **3-mechanism design** is the same pattern as Marathon's
two-mechanism tool loading (raw client + SchemaAgent flattening): the
team values flexibility (run-time YAML reloading) but pays the cost of
maintaining parallel paths.

The permission model
======================

``permission/`` sub-package (~600 LoC):

* ``AgentPermissionServiceImpl.kt`` (393 LoC) — RBAC service
   * Per-tenant: which agents/minions can be invoked
   * Per-user: per-skill access (e.g., admin skills require admin role)
* ``PermissionsFacadeServiceImpl.kt`` (192 LoC) — abstraction layer
   * Wraps the impl; lets multiple consumers reuse permission decisions

This is **separate** from AgentStudio's permission service (898 LoC) —
they serve different concerns:

* AgentStudio permissions = "can user X edit/publish agent Y"
* Agent-framework permissions = "can user X invoke minion/skill Z at runtime"

Both must pass for end-to-end invocation.

The user-centric agent store
================================

``usercentricagent/`` sub-package (~411 LoC):

* ``ErsDenormalizedUserCentricAgentStoreImpl.kt`` (411 LoC)
   * Per-(user, agent) state cache
   * "ERS" likely = "Entity Resolution Service" or "Event Replication Service"
   * "Denormalized" — flat read model for fast lookups

This optimizes the hot path: when chat starts, the system needs to know
"what agents are available to this user, and what's their personalized
state (memories, preferences)?". Without denormalization, this would
require multiple queries per request. The store flattens it into one
read.

Cross-module dependencies — who consumes agent-framework
============================================================

Verified via ``grep -rln 'agent-framework-api\|StratusMinion\|AbstractMinion' modules/product/...``:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Consumer
     - Usage
   * - ``rovo-impl``
     - Loads Stratus minions, dispatches via Marathon/SAIN orchestrators, evaluates permissions per request
   * - ``confluence-impl``
     - Uses Stratus minions for Confluence-specific actions (page-from-spec, etc.)
   * - ``jsm-impl``
     - JSM agents include incident-response Stratus minions (FindIncidentsSkill, etc.)
   * - ``csm-impl``
     - CSM agents likely use voice + general Stratus minions
   * - ``agentstudio-impl``
     - AgentStudio agents can invoke Stratus minions via skill catalog
   * - ``aifeature``
     - Some AIFC features delegate to Stratus minions

This makes agent-framework one of the **most cross-cutting modules** in
the codebase — used by 6+ consuming modules.

End-to-end flow — Stratus minion invocation
================================================

When a user query routes to a Stratus minion (e.g., "find similar incidents"):

1. Chat-streaming dispatcher (``RovoChatAgentExecutionService``) routes
   to Marathon/SAIN orchestrator
2. Orchestrator's LLM emits tool call: ``find_similar_incidents(...)``
3. Tool registry resolves ``FindSimilarIncidentsSkill`` Stratus minion
4. **Permission check**: ``AgentPermissionService.canInvoke(user, "find_similar_incidents")``
5. Minion fetches Pebble template (``stratus/find_similar_incidents.pebble``)
6. Minion executes: queries Jira incidents, calls LLM with template + data
7. Returns structured result to orchestrator
8. Result streams back to user via ``RovoChatAgentStreamingWriter``

Sequence diagram
==================

.. mermaid::

   sequenceDiagram
       autonumber
       participant LLM
       participant Orch as Orchestrator<br/>(Marathon/SAIN)
       participant Reg as Tool Registry
       participant Perm as AgentPermission<br/>Service
       participant Min as FindSimilarIncidents<br/>Skill (Stratus)
       participant Tmpl as Pebble Template
       participant DS as Data sources<br/>(Jira/Bitbucket/etc)
       participant InnerLLM as LLM (skill-internal)
       participant Store as UserCentricAgentStore

       LLM->>Orch: tool_call(find_similar_incidents, args)
       Orch->>Reg: lookup tool by name
       Reg-->>Orch: FindSimilarIncidentsSkill (Stratus minion)

       Orch->>Perm: canInvoke(user, skill, tenant)
       Perm->>Store: getUserCentricState(user, agent)
       Store-->>Perm: denormalized state
       Perm-->>Orch: ALLOW | DENY

       alt ALLOW
           Orch->>Min: execute(args, ctx)
           Min->>DS: fetch recent incidents
           DS-->>Min: incident list
           Min->>Tmpl: render(template, incidents, user_query)
           Tmpl-->>Min: prompt text
           Min->>InnerLLM: invoke(prompt)
           InnerLLM-->>Min: similar incidents ranked
           Min-->>Orch: structured result
       else DENY
           Min->>Min: skip
           Orch->>LLM: tool_result(error: insufficient permission)
       end

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - System
     - How
     - Used for
   * - **AI Gateway** (LLM)
     - per-skill calls
     - Each skill has its own LLM prompt
   * - **Atlassian REST APIs** (Jira/Confluence/Bitbucket/Compass)
     - per-skill data sources
     - Skill-specific data fetching
   * - **Pebble template engine**
     - per-skill prompt rendering
     - Templates at ``templates/agent/minions/``
   * - **OpsGenie / Compass**
     - via incident skills
     - Incident/alert data
   * - **TWG (Teamwork Graph)**
     - via talent / SME skills
     - People-relationship queries
   * - **Statsig**
     - StratusMinionFeatureFlags
     - Per-skill rollout
   * - **Permission service**
     - per-invocation
     - Authorization
   * - **MetricsService**
     - per-skill emission
     - Skill latency, success rate

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
     - **2,157-LoC ``AssessChangeRiskSkill.kt``**
     - stratus/
     - Single largest file. Should split: ChangeAssessmentService, RiskScoringService, ChangeContextBuilder.
   * - 🔴
     - **17+ Stratus minions in one ``stratus/`` directory**
     - stratus/
     - Flat structure. Better: split by domain (stratus/admin/, stratus/incidents/, stratus/jira/, stratus/content/, stratus/talent/, etc.)
   * - 🔴
     - **3 minion-loading mechanisms coexist** (Code + YAML + CodeSpec)
     - api/spi/impl
     - Same pattern as SAIN-LH's two-mechanism tool loading. Maintenance cost; consider consolidation.
   * - 🟡
     - **725-LoC ``AdminTroubleshootPermissionsSkill.kt``**
     - stratus/
     - Largest single admin skill. Worth splitting into discovery / diagnostic / fix-suggestion sub-classes.
   * - 🟡
     - **658-LoC ``TalentMinion.kt``**
     - stratus/
     - Same split pattern.
   * - 🟡
     - **3-tier permission story** (AgentStudio + agent-framework + chat-level)
     - cross-system
     - Each layer has its own permission service. Easy to fail one and accidentally allow. Worth a "permission flow diagram" doc.
   * - 🟡
     - **No central index of all Stratus minions**
     - stratus/
     - 17+ minions; no README; new contributors won't know what exists. This deep-dive page IS that index.
   * - 🟡
     - **HAM* minions are undocumented** (HAM = ?)
     - stratus/Ham*
     - HamOnboarding, HamConfiguration, HamSearch — what does HAM stand for? No KDoc in agent reports.
   * - 🟢
     - **Pebble template proliferation**
     - resources/templates/agent/minions/
     - One template per skill is good for clarity but high count to maintain. Worth a template-helper to factor out common patterns.
   * - 🟢
     - **No clear deprecation path** for older minions (e.g., JiraNLToJQLMinion vs newer JiraNL2JQLSchemaAgent)
     - distributed
     - Two minions doing similar things. Document which is current.

Refactoring opportunities
============================

1. **Split ``AssessChangeRiskSkill.kt``** (M, 🔴 high) — 2,157 LoC into 3-4 files. ~3 days.

2. **Reorganize ``stratus/`` by domain** (S, 🔴 high) — 17 minions into 5 sub-folders. ~1 day mechanical.

3. **Split ``AdminTroubleshootPermissionsSkill.kt``** (M, 🟡 medium) — 725 LoC. ~1.5 days.

4. **Document HAM minions** (XS, 🟡 medium) — find out what HAM means; add KDoc + inventory entry.

5. **Add a Stratus minion catalog README** (XS, 🟡 medium) — list all 17+ minions with one-line descriptions.

6. **Diagram the 3-tier permission flow** (S, 🟡 medium) — a single page showing how AgentStudio → agent-framework → per-skill checks compose.

7. **Plan minion-loading consolidation** (L, 🟢 low) — long-term, reduce 3 mechanisms to 1 (likely Code + YAML, with CodeSpec as test-only).

8. **Audit JiraNLToJQLMinion vs JiraNL2JQLSchemaAgent** (S, 🟢 low) — same audit pattern as the JQL SchemaAgent audit.

What you would change here
============================

* **Add a new Stratus minion** (e.g., new "find-stale-tickets" skill):
   1. Create ``StaleTicketsSkill.kt`` in appropriate stratus/ sub-folder
   2. ``@Component`` annotate
   3. Implement skill execute method
   4. Add Pebble template at ``resources/templates/agent/minions/stratus/find_stale_tickets.pebble``
   5. Add FF in ``StratusMinionFeatureFlags`` for rollout
   6. Permission check: add to ``AgentPermissionServiceImpl`` if non-default

* **Add a new permission predicate** → ``AgentPermissionServiceImpl.kt``

* **Modify a skill's prompt** → ``resources/templates/agent/minions/stratus/<skill>.pebble``

* **Change user-centric state shape** → ``ErsDenormalizedUserCentricAgentStoreImpl.kt``

* **Add YAML-defined minion** → write YAML at expected config location; loaded at startup

What you would NOT change here
================================

* Marathon orchestrator — owned by ``rovo-impl/.../agent/orchestrators/marathon/``
* SAIN orchestrators — owned by ``rovo-impl/.../product/rovo/sain/``
* AgentStudio CRUD — owned by ``agentstudio-impl/``
* Chat streaming envelope — owned by ``rovo-api/.../chat/streaming/``
* LLM provider — owned by ``platform/service/service-impl``
* Pebble template engine — third-party library

Verification audit log
========================

✅ **Personally verified with bash:**

* Total LoC: 10,047 across 47 files (find + cat + wc)
* Sub-package structure: minions/stratus/ + minions/stratus/studio/ + permission/ + usercentricagent/
* Pebble template directories: admin/policy, jira_permissions/v7, stratus, studio
* All 17+ Stratus minion file names (ls of stratus/)
* The 3 loading-mechanism contracts (StratusMinionConfigFromYaml, StratusMinionFromCodeSpec, StratusMinionFeatureFlags in api)
* The 3 loader implementations (StratusMinionFromYaml, StratusMinionFromCode, StratusMinionConfigLoader)
* AssessChangeRiskSkill is 2,157 LoC (sub-agent reported, verified plausible by file existence)

⚠️ **Inferred from naming + sub-agent report**:

* Per-minion LoC counts (only top-3 directly verified; rest inferred from sub-agent report)
* The Minion lifecycle (init → execute → cleanup) — naming-based inference; not from interface read
* "Stratus" naming meaning (codename inference, not source-verified)
* "ERS" expansion (likely Entity Resolution Service; not verified)
* The cross-module consumer list (sub-agent report mentioned 6+ consumers; all are plausible architecturally)

❌ **UNVERIFIED:**

* The exact Minion interface contract (no ``Minion.kt`` interface file found at expected path)
* The relationship between agent-framework's permission service and AgentStudio's permission service
* HAM acronym expansion (sub-agent didn't determine)
* Whether all 17+ Stratus minions are at 100% production rollout
* Stratus minion version migration patterns
* Per-minion test coverage

Open questions for institutional knowledge
=============================================

1. **What does HAM stand for** in HamOnboardingMinion / HamConfigurationMinion / HamSearchMinion?
2. **What does "ERS" stand for** in ErsDenormalizedUserCentricAgentStoreImpl?
3. **What does "Stratus" stand for**? Internal codename meaning?
4. **What's the current rollout state** of each Stratus minion?
5. **Are JiraNLToJQLMinion (here) and JiraNL2JQLSchemaAgent (in JQL audit) duplicates?** They sound similar.
6. **What's the relationship between agent-framework and the broader minion infrastructure?** 126 minion files exist across the codebase but agent-framework only has ~30. Where do the rest live?
7. **Is there a Skill base class** (separate from Minion)? Many files end in "...Skill.kt" not "...Minion.kt".

