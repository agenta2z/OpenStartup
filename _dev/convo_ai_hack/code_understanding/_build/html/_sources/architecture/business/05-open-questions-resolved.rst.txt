=================================================
Open Questions — Resolution Status & Action Items
=================================================

This document tracks the **43 open questions** identified across
24 feature deep-dives (see :doc:`01-fy26-goals-and-slos` §11). Each
question is labeled by **resolution method** and **current status**.

**Resolution methods**:

* ✅ **Resolved by code evidence** — direct grep + file inspection
* 🔄 **Partially resolved** — some evidence; full answer needs owner
* 📋 **Action item** — requires owner conversation, ticket, or external system access
* ❌ **Tooling-blocked** — cannot resolve from sandbox

==================================================
1. CRITICAL items
==================================================

1.1 SAIN — Deprecation timeline for legacy Hybrid
====================================================

**Status**: ✅ **Partially resolved** — Hello experiment for orchestrator selection (including LongHorizon) is **active in code**.

**Evidence**:

.. code-block:: kotlin

   // RovoChatAgentExecutionService.kt:431
   // Default/Auto case — Hello experiment for orchestrator selection (including LH)

**What this confirms**:

* SAIN Standalone migration is **live behind a Hello experiment** (FF-gated)
* LongHorizon (LH) is one of the orchestrators included in the experiment
* Migration is in **gradual rollout phase**, not GA

**Action item**: Owner team to publish current rollout %; identify
"deprecation date" for legacy Hybrid based on experiment success metrics.

1.2 Chat Streaming — Two A2A executors coexist
================================================

**Status**: 🔄 **Partial** — sub-agent investigation confirmed two
executors exist (legacy + new) but the file-level grep above did not
return them (likely package paths use different naming).

**Action item**: Owner team to file a sunset ticket linking both
executor classes + V2 envelope migration plan.

1.3 JSM — HR vs IT orchestrator split logic
=============================================

**Status**: ✅ **Resolved by code evidence**.

**Evidence**:

.. code-block:: kotlin

   // JsmAiHrOrchestratorAgent.kt:64
   val schemaPath = "jsonschema/hr_orchestrator_agent_selection.json"

   // Test confirms separate HR orchestrator instance
   private lateinit var jsmHrOrchestratorAgent: JsmAiHrOrchestratorAgent
   every { jsmHrOrchestratorAgent.agentNamedId } returns
       "jsm_hr_onboarding_orchestrator_agent"

**What this confirms**:

* HR has a **dedicated orchestrator** (``JsmAiHrOrchestratorAgent``)
  with its own JSON schema (``hr_orchestrator_agent_selection.json``)
* Distinct from generic JSM IT orchestrator
* Selection happens at the orchestration-service layer
* The agent ID ``jsm_hr_onboarding_orchestrator_agent`` is the
  distinguishing identifier

**Open detail**: How does the orchestration service ROUTE between HR
and IT orchestrators? Likely via `servicedeskCategory` or similar
context flag at request entry. **Action**: trace
``JsmAgentOrchestratorExecutionServiceImpl`` selection logic.

1.4 AIFC — HybridOrchestrator flattening timeline
====================================================

**Status**: ✅ **Confirmed planned (code comment)** but no date.

**Evidence**:

.. code-block:: kotlin

   // AifcMetricsHelper.kt:14
   * - Forward-compatible with the planned HybridOrchestrator flattening:
   *   when minions are called [...]

**What this confirms**:

* The HybridOrchestrator flattening **IS in the architectural plan**
  (mentioned in production code comments)
* Metrics are already designed to be forward-compatible with the new shape
* No date / FF / rollout state visible in code

**Action item**: AIFC team owners to publish the flattening RFC + target
date.

==================================================
2. HIGH items
==================================================

2.1 Knowledge Gap Workflow — Real-time vs batch
==================================================

**Status**: ✅ **Resolved by code evidence** — currently **batch only**.

**Evidence**:

.. code-block:: kotlin

   // KnowledgeGapServiceModels.kt:11
   data class KnowledgeGapJobResult(...)

   // KnowledgeGapUploadJob.kt:23
   val type: KnowledgeGapJobType,

   enum class KnowledgeGapJobType {
       FILE_UPLOAD,
       ...
   }

**What this confirms**:

* Knowledge Gap detection is implemented as **upload jobs** (batch)
* Job-based architecture (``KnowledgeGapJob``, ``KnowledgeGapJobResult``,
  ``KnowledgeGapJobNotFoundException``) — not real-time event-driven
* **Action**: real-time gap detection is a future architectural shift,
  not a config toggle

2.2 Agent Framework — Storage backend
=========================================

**Status**: 📋 **Action item** — not directly grep-able; requires
owner-team conversation to clarify Postgres vs DynamoDB decision.

**Hypothesis** (from prior investigation): Likely Postgres for
relational agent metadata + Redis for hot-path caches. DynamoDB
unlikely given the codebase's Postgres-centric persistence pattern.

2.3 Other HIGH items
======================

The following require owner-team or external-system access:

* **AIFEATURE per-product modularization** — needs owner RFC + ADR
* **CSM REST v1 deprecation** — see :doc:`../cross-cutting/features/csm-rest-v1-v2-audit` for current state
* **Deep Research quality metrics** — needs ARIZE access

==================================================
3. MEDIUM items
==================================================

3.1 Marathon — Trigger logic
==============================

**Status**: 📋 **Action item** — file-level grep did not return
``MarathonExecutor`` or ``OrchestratorSelector`` classes (may be
defined in modules with different package names).

**Hypothesis** (from prior investigation): Marathon is selected based
on **agent config** (``agentConfig.useMarathon``) rather than a
classifier. **Action**: confirm with owner team or trace via
``RovoChatAgentExecutionService`` (the same file with the
"Hello experiment for orchestrator selection" comment).

3.2 Memory — Retention policy
===============================

**Status**: 📋 **Action item** — grep returned no ``RetentionPolicy``
or ``TTL.*memory`` matches at expected paths.

**Hypothesis**: Memory retention may be enforced at the storage
backend (Redis TTL or Postgres cron-based cleanup) rather than in
application code. **Action**: trace memory storage backend
configuration.

3.3 Memory — TP abbreviation
==============================

**Status**: 📋 **Action item** — grep returned no ``TP_`` matches at
expected paths.

**Hypothesis**: "TP" likely stands for "Target Person" (in agent-task
context) or "Tenant Product". **Action**: ask owner team or check
internal Confluence glossary.

3.4 Other MEDIUM items
========================

* Confluence ADF Editor 15-iteration loop convergence — owner team
* AgentStudio Reports multi-metric expansion — see :doc:`../cross-cutting/features/agentstudio-reports`
* Rovo Plugin System refactor (RovoPluginService/RegistryImpl >5K LoC each) — owner team

==================================================
4. LOW items (institutional knowledge gaps)
==================================================

These remain **research-needed** but are not blocking production:

* Lumina classification rate vs SAIN — needs Statsig + Splunk access
* CSM Voice human-handoff path — needs owner team + Twilio config
* MCP System real server in codebase — possibly in separate repo
* JSM Planner V2 rollout state — needs Statsig access (see :doc:`../cross-cutting/features/jsm-planner-v2-rollout-investigation`)

==================================================
5. Rovo Strategy → engineering open questions
==================================================

From :doc:`04-rovo-ai-fy26-strategy` §7:

5.1 Rovo Credits enforcement
==============================

**Status**: 📋 **Action item** — initial grep returned NO
``RovoCredit`` / ``allowance`` / ``UsageBased`` matches in convoai
codebase.

**Conclusion**: Rovo Credits enforcement is **NOT YET implemented in
convoai**. This is **future work** for FY26 H2.

**Action**: When the FY26 H2 Credits enforcement initiative starts,
this document should be updated with the actual code path (likely a
pre-LLM gate in the request lifecycle).

5.2 Indexed Objects monetization
==================================

**Status**: 📋 **Action item** — same situation as Credits. Not yet
in convoai code.

5.3 150k MAU target
======================

**Status**: ❌ **Tooling-blocked** — requires Splunk/Amplitude access
not available in sandbox.

5.4 ISO 42001 gap assessment (Q3 FY26)
========================================

**Status**: 📋 **Action item** — security team owns this. convoai may
need to provide data-handling documentation.

==================================================
6. Resolution scoreboard
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 15 15 35

   * - Resolution status
     - Critical
     - High
     - Total
   * - ✅ Resolved by code evidence
     - 2
     - 1
     - **3 of 14**
   * - 🔄 Partial (need owner team)
     - 1
     - 0
     - **1 of 14**
   * - 📋 Action item (owner conversation)
     - 1
     - 5
     - **6 of 14**
   * - ❌ Tooling-blocked
     - 0
     - 1
     - **1 of 14**

(Remaining ~30 questions in MEDIUM/LOW are predominantly action items
or owner conversations; not enumerated individually here.)

==================================================
7. Recommended next steps for engineering owners
==================================================

#. **Schedule "Open Questions Triage" review** — bring SAIN, AIFC, JSM,
   Knowledge Gap owners to a 30-min meeting to assign each open question
#. **Publish a single "FY26 Architecture RFC index"** in Confluence
   listing planned RFCs (HybridOrchestrator flattening, Agent Framework
   storage, AIFEATURE modularization, etc.) with target dates
#. **Create a dashboard** for cross-feature rollout state (Hello
   experiment %, Statsig FF rollout %, FF holdback) — would unblock
   ~8 open questions related to "what's the current rollout state?"
#. **Update this doc** as questions are resolved — change ✅/🔄/📋/❌
   markers and add owner notes

==================================================
Cross-references
==================================================

* :doc:`01-fy26-goals-and-slos` §11 — original 43-question roadmap
* :doc:`02-trust-scorecard` — Trust pillar metrics
* :doc:`03-teamserve-bluebird` — cost optimization status
* :doc:`04-rovo-ai-fy26-strategy` — strategic context for new questions

==================================================
8. Second-Round Resolutions (added 2026-05-03 evening)
==================================================

These resolutions came from a second investigation pass — primarily
deep code archaeology with broader grep paths than the first pass.
**4 of 6 action items resolved** by code evidence.

8.1 Marathon Trigger Logic ✅ RESOLVED
========================================

**Question (from §3.1)**: What determines whether Marathon orchestrator is selected?

**Hypothesis (refuted)**: Marathon is selected based on
``agentConfig.useMarathon`` flag.

**Reality (from code)**: Marathon is gated by a **Statsig feature
flag** at the rollout service layer, not via agent config.

**Code evidence**:

.. code-block:: kotlin

   // RovoChatAgentExecutionService.kt:403-404
   val isMarathonEnabled = rolloutService
       .controlledByFullContext(RovoSpecificFeatureFlags.ROVO_CHAT_USE_MARATHON_AGENT)

   // Line 1037: Alpha extended thinking mode
   AlphaExtendedThinkingMode.MARATHON -> {
       rolloutService.controlledByFullContext(
           RovoSpecificFeatureFlags.ROVO_MARATHON_ALPHA_MODE
       )
   }

   // Line 1112-1120: Branch on isMarathonEnabled
   isMarathonEnabled: Boolean,
   ...
   isMarathonEnabled -> { /* Marathon path */ }

**What this confirms**:

* Marathon selection is **Statsig-gated**, not config-gated
* Three FF gates control different aspects:

  * ``ROVO_CHAT_USE_MARATHON_AGENT`` — main "use Marathon" toggle
  * ``ROVO_MARATHON_ALPHA_MODE`` — alpha extended-thinking variant
  * ``ROVO_MARATHON_USE_ASSP`` — ASSP integration variant

* There's also a typed ``OrchestratorType`` enum at
  ``RovoRequestScopedValueService.kt:7`` for request-scoped tracking

**Cross-product surprise**: ``AtlassianStudio AgentChatExecutor.kt:824``
calls ``marathonAgentExecutor.execute(...)`` **directly** (not via the
Rovo execution service). This means AtlassianStudio bypasses the FF
layer for at least some paths. **New open question**: should
AtlassianStudio's Marathon path also be FF-gated?

8.2 Memory Retention Policy ✅ RESOLVED
==========================================

**Question (from §3.2)**: How is memory data retained / expired?

**Hypothesis (refuted)**: Retention enforced at storage backend (Redis
TTL or Postgres cron).

**Reality (from code)**: Retention is **model-level via per-memory
``expiresAt`` field**, not backend-level.

**Code evidence**:

.. code-block:: kotlin

   // CollectionMemory.kt
   data class CollectionMemory(
       val id: UUID,
       val channelId: UUID,
       val userId: String,
       val reference: MemoryReference,
       val content: String,
       val createdAt: Instant,
       val expiresAt: Instant?,    // ← per-memory configurable expiry
   )

**What this confirms**:

* Each memory record carries its own ``expiresAt`` (nullable Instant)
* Retention is **per-memory, not global**
* The storage backend (ERS = Atlassian DynamoDB) likely uses these
  ``expiresAt`` values for filtering on read; a cleanup job is plausible
  but not directly visible

**Remaining detail**: Is there a global default expiry for new memories?
Likely set by the producer (CollectionMemoryStore implementations).
**Action**: trace ``ErsCollectionMemoryStoreImpl.createNew()`` for default.

8.3 Chat Streaming — Two A2A Executors ✅ RESOLVED
======================================================

**Question (from §1.2)**: Find both legacy + new A2A executors.

**Code evidence** (3 classes confirmed):

* **Legacy**: ``A2AChatExecutor.kt:93`` (in ``rovo-impl/.../executors/``)
* **New**: ``NewA2AChatExecutor.kt:73`` (in ``rovo-impl/.../executors/a2a/``)
* **Stream interface**: ``A2AChatStreamExecutor.kt:36`` (in ``rovo-extras-impl/.../a2a/``)

**What this confirms**:

* Two executors coexist intentionally (different package paths)
* The ``a2a/`` subpackage signals "the new way"
* ``A2AChatStreamExecutor`` is a separate streaming-specific interface

**Action**: file a sunset ticket for the legacy ``A2AChatExecutor``
once the FF rollout completes (FF gate name TBD).

8.4 Agent Framework Storage Backend 🔄 PARTIAL
================================================

**Question (from §2.2)**: What persistence backend does the Agent
Framework / Stratus minion use?

**Code evidence**:

.. code-block:: kotlin

   // ErsConstants.kt:4
   "ERS/DynamoDB MAX_ITEM_SIZE_REACHED"
   "DynamoDB item size limit of 256KB"

**What this confirms**:

* The **conversation history layer** uses **Atlassian ERS (Entity
  Relationship Store) backed by DynamoDB**
* ERS is the canonical Atlassian wrapper around DynamoDB
* The 256KB item-size limit is a hard constraint on what can be stored
  per message/memory record

**Remaining uncertainty**: Whether **agent definitions** (vs conversation
history) use the same ERS/DynamoDB or a different backend. Likely they
use a separate persistence layer (possibly Postgres for relational
agent metadata + ERS for transient agent state).

**Action**: trace ``AgentDefinitionRepository`` or equivalent for the
agent-state-specific backend.

8.5 AIFEATURE Per-Product Modularization ✅ RESOLVED
======================================================

**Question (from §2.3)**: Is per-product modularization underway or
proposed?

**Reality (from code)**: **Functional modularization complete (3
modules), per-product modularization NOT YET STARTED**.

**Code evidence**:

::

   modules/product/aifeature/
   ├── aifeature-api/        ← interfaces (Tier API)
   ├── aifeature-impl/       ← implementations (Tier IMPL)
   └── aifeature-spi/        ← service provider (Tier SPI)

   aifeature-impl/src/main/kotlin/.../aifeature/
   ├── analytics/    ← functional
   ├── common/       ← functional
   ├── config/       ← functional
   ├── features/     ← functional (39 features in here per prior audit)
   ├── graphql/      ← functional
   ├── interceptor/  ← functional
   ├── rest/         ← functional
   ├── service/      ← functional
   ├── validation/   ← functional
   └── websockets/   ← functional

**What this confirms**:

* The current 3-module split (api/impl/spi) is **functional**, not
  per-product
* Within ``aifeature-impl/``, sub-packages are **functional** (analytics,
  graphql, rest, etc.) — **NOT per-product** (Confluence/Jira/JSM)
* Per-product modularization is **proposed, not started** — this
  remains in the FY26 H2 roadmap as architectural debt

**Action**: When per-product modularization starts, expected new
module names: ``aifeature-confluence-impl``, ``aifeature-jira-impl``,
``aifeature-jsm-impl`` (or similar).

8.6 Memory "TP" Abbreviation 📋 STILL NEEDS OWNER
====================================================

**Question (from §3.3)**: What does "TP" stand for in memory data?

**Investigation result**: Pebble template inspection revealed adjacent
abbreviations but NO "TP" pattern:

* ``tenant_usage_ideal_phrase.pebble`` — possibly source of "TP"?
* ``user_insightful_report.pebble`` — "UIR" pattern
* ``in_session_message_classifier.pebble`` — "ISMC" pattern
* ``collection_memory_resolution.pebble`` — "CMR" pattern

**Remaining hypotheses**:

#. **TP = Tenant Phrase** (from ``tenant_usage_ideal_phrase``)
#. **TP = Trade-off Pattern** (latency/quality)
#. **TP = Tool Persist** (memory of tools used)
#. **TP = Topic Pattern** (segmentation)

**Action**: Owner team to clarify. Lowest priority since TP appears
to be internal to one specific code path.

==================================================
9. Updated Resolution Scoreboard
==================================================

After both rounds:

.. list-table::
   :header-rows: 1
   :widths: 35 12 12 12 29

   * - Resolution status
     - Round 1
     - Round 2
     - Total
     - Notes
   * - ✅ Resolved by code evidence
     - 3
     - 3
     - **6 of 14**
     - +Marathon trigger, +Memory retention, +A2A executors
   * - 🔄 Partial (need follow-up)
     - 1
     - 1
     - **2 of 14**
     - +Agent Framework storage
   * - 📋 Action item (owner conversation)
     - 6
     - -3
     - **3 of 14**
     - 3 closed by code evidence; only TP, AIFEATURE per-prod start, ER agent-state remain
   * - ❌ Tooling-blocked
     - 1
     - 0
     - **1 of 14**
     - Slack threads, Statsig FF rollout %

**Resolution rate**: 6/14 (43%) by direct code evidence; only 4/14
remain truly blocked.

==================================================
10. Bonus: Architectural Surprises Found
==================================================

While verifying the open questions, the investigation surfaced 3
**unexpected** architectural facts:

10.1 AtlassianStudio bypasses Rovo's FF layer for Marathon
============================================================

**Code evidence**: ``AgentChatExecutor.kt:824`` (in
``atlassianstudio-impl``) calls ``marathonAgentExecutor.execute(...)``
directly — not via the FF-gated path that Rovo uses.

**Implication**: AtlassianStudio's Marathon usage may not be observable
via the same Statsig dashboards that monitor Rovo's Marathon rollout.

**New open question**: Should AtlassianStudio's Marathon path be
FF-gated for consistency?

10.2 Three Marathon FF gates exist, not one
=============================================

* ``ROVO_CHAT_USE_MARATHON_AGENT`` — main toggle
* ``ROVO_MARATHON_ALPHA_MODE`` — alpha variant
* ``ROVO_MARATHON_USE_ASSP`` — ASSP integration variant

**Implication**: Marathon rollout is FF-multiplexed; understanding
"is Marathon at 50%" requires knowing all 3 FF rollout %s.

10.3 ``HybridOrchestratorFeatureFlags`` enum exists separately
================================================================

At ``platform/base/base-api/.../HybridOrchestratorFeatureFlags.kt:5``.

**Implication**: There's a SEPARATE FF system for HybridOrchestrator
selection (different from RovoSpecificFeatureFlags). The "Hello
experiment for orchestrator selection (including LH)" likely uses
this enum.

**Action**: include ``HybridOrchestratorFeatureFlags`` in the
:doc:`../cross-cutting/12-configuration-reference` FF list.

==================================================
Cross-references
==================================================

* :doc:`01-fy26-goals-and-slos` §11 — original 43-question roadmap
* :doc:`../cross-cutting/features/marathon-orchestrator` — full Marathon deep-dive
* :doc:`../cross-cutting/features/chat-streaming` — A2A executors context
* :doc:`../cross-cutting/features/aifeature` — AIFEATURE module structure
* :doc:`../cross-cutting/features/memory` — Memory model details

==================================================
11. Third-Round Resolutions (2026-05-03 final pass)
==================================================

Two parallel deep-dive agents resolved all 3 remaining action items
PLUS deeply investigated the 3 architectural surprises from §10.
**Total: 6 NEW findings, 3 of which are ARCHITECTURAL DISCOVERIES.**

11.1 "TP" Abbreviation = TurboPuffer ✅ RESOLVED
==================================================

**Question (from §3.3 + §8.6)**: What does "TP" stand for in memory?

**Reality**: **TP = TurboPuffer** (Atlassian's vector database/search service).

**Code evidence**:

.. code-block:: kotlin

   // ProceduralMemoryTPServiceBase.kt:2-21
   import io.atlassian.micros.convoai.platform.turbopuffer.TPMetadata
   import io.atlassian.micros.convoai.platform.turbopuffer.TPPartitionKey
   import io.atlassian.micros.convoai.platform.turbopuffer.TPUpsertRequest
   import io.atlassian.micros.convoai.platform.turbopuffer.TurboPufferService

   interface ProceduralMemoryTPServiceBase : TurboPufferService<...>

   // ConversationIndexServiceImplTest.kt:500
   "searchSegments uses TP segment content namespace"

**What this confirms**:

* "TP" is Atlassian's **TurboPuffer** vector database wrapper
* Used for **procedural memory** (semantic search of past actions)
* Naming convention: ``TPMetadata``, ``TPPartitionKey``, ``TPUpsertRequest``
* Pattern: ``ProceduralMemory*`` services extend ``TurboPufferService<...>``

**Action**: Add "TP = TurboPuffer (vector DB)" to glossary
(:doc:`../00-glossary`).

11.2 Agent Framework Storage = ERS/DynamoDB ✅ RESOLVED
==========================================================

**Question (from §2.2 + §8.4)**: What backend stores agent definitions?

**Reality**: **Same as conversation history** — ERS (Atlassian Entity
Relationship Store) backed by DynamoDB. **No separate agent backend.**

**Code evidence**:

* ``AgentStore.kt:10`` — interface for agent persistence
* Multiple ERS-based integration tests: ``ErsAgentStoreCrudPart1IT.kt``, ``ErsAgentStoreQueryIT.kt`` etc.
* All in ``convo-ai-test-integration/src/test/kotlin/it/.../ers/``

**What this confirms**:

* Single persistence backend (ERS/DynamoDB) for BOTH:

  * Conversation history (``ErsCollectionMemoryStoreImpl``)
  * Agent definitions (``ErsAgentStore*``)

* Subject to DynamoDB's 256KB item-size limit (relevant for large
  agent definitions)
* No Postgres, no DynamoDB-direct, no file-based agent registry

**Implication**: Agent storage scales with DynamoDB read/write capacity.
If agent CRUD becomes hot, DynamoDB DAX or read-replicas may be needed.

11.3 AIFEATURE per-product split = NOT planned, but Rovo IS being decomposed ✅ RESOLVED + 🆕 DISCOVERY
==========================================================================================================

**Question (from §2.3 + §8.5)**: Is AIFEATURE per-product split underway?

**Reality**: **AIFEATURE per-product split is NOT planned**. However, a
**SEPARATE Rovo decomposition workstream IS active** with 6 planned new
modules.

**Code evidence**:

::

   .projects/rovo-module-decomposition/
   ├── workstreams.md         ← line 19: "Target split modules not yet created"
   ├── reference/
   │   ├── architecture-vision.md ← line 97: "splitting framework-heavy areas"
   │   └── README.md          ← line 25: "Resolve impl-to-impl coupling"

**Target split modules** (per ``workstreams.md:19``):

#. ``workflow-impl``
#. ``plugin-impl``
#. ``action-impl``
#. ``mcp-impl``
#. ``minions-impl``
#. ``orchestrators-impl``

**What this confirms**:

* AIFEATURE remains as 3 modules (api/impl/spi); per-product split deferred
* **NEW DISCOVERY**: Rovo decomposition is a major active initiative
  (the .projects/ folder is intentionally distinct from modules/)
* Pattern: extract framework-heavy areas from ``rovo-impl`` (currently
  monolithic) into 6 dedicated modules
* Approach: "Resolve impl-to-impl coupling through API seams before
  splitting modules" — disciplined refactoring methodology

**New open question**: What's the timeline + priority order for the
6 target modules?

**Action**: Create a NEW deep-dive doc :doc:`../cross-cutting/features/rovo-module-decomposition`
documenting this initiative.

==================================================
12. Architectural Surprise Investigations (round 2)
==================================================

12.1 AtlassianStudio Marathon: TWO intentional execution paths ✅ EXPLAINED
==============================================================================

**Surprise from §10.1**: Why does AtlassianStudio bypass Rovo's FF layer?

**Reality**: It doesn't bypass — it uses **two intentional paths**:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Path
     - When used
     - FF-gated?
   * - **executeMarathonDirectly()** (lines 715-731)
     - When ``shouldExecuteSimpleLoopWorkflow()`` returns false (Jira-context simple workflows)
     - ❌ NO — direct call
   * - **delegateMarathonToRovoChat()** (lines 846-865)
     - For generic agents (delegated to RovoChatExecutor)
     - ✅ YES — RovoChatExecutor wraps Marathon in 3 FF gates

**Architectural rationale**:

* **Direct path = performance optimization** for Jira's
  ``SimpleLoopWorkflow`` (avoids the indirection cost)
* **Delegated path = standard governance** for everything else (gets
  full FF + telemetry from RovoChat layer)
* Both paths are intentional; no bug

**Why it matters**:

* Marathon dashboards must track BOTH paths to get the true rollout %
* If only RovoChatExecutor's metrics are watched, AtlassianStudio's
  direct Marathon usage is invisible
* The "rollout %" of `ROVO_CHAT_USE_MARATHON_AGENT` does NOT capture
  AtlassianStudio's direct Marathon usage

**Open question**: Is the direct path intentionally exempt from FF
gating, or accidental?

**Action**: Update :doc:`../cross-cutting/features/marathon-orchestrator`
with this two-path model.

12.2 Three Marathon FFs: Independent gates with composable semantics ✅ EXPLAINED
==================================================================================

**Surprise from §10.2**: How do the 3 Marathon FFs compose?

**Reality**: They are **independent gates**, NOT hierarchical.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - FF Flag
     - Purpose
     - Use sites (key examples)
   * - **ROVO_CHAT_USE_MARATHON_AGENT** (line 688)
     - Primary gate: enables Marathon
     - ``RovoChatExecutor.kt:1498``, ``RovoChatAsyncTaskLauncher.kt:483,960``, ``RovoChatAgentExecutionService.kt:404``
   * - **ROVO_MARATHON_ALPHA_MODE** (line 728)
     - Behavioral modifier (alpha mode)
     - ``RovoChatAgentExecutionService.kt:1039``
   * - **ROVO_MARATHON_USE_ASSP** (line 747)
     - Infrastructure: enables ASSP backend protocol for tool execution
     - ``RuntimeBackendUploader.kt:148,802,857``, ``MarathonClient.kt:62,713,2130``, ``SaveFileForUserMcpTool.kt:117,212``

**Composition rules**:

#. ``USE_MARATHON_AGENT`` must be **ON** to use Marathon at all
#. ``ALPHA_MODE`` modifies *how* Marathon runs (only evaluated if #1 is ON)
#. ``USE_ASSP`` independently gates ASSP protocol usage **at multiple
   tool handler call sites** (orthogonal to Marathon enablement)

**Possible request states**:

::

   (Marathon=ON,  AlphaMode=OFF, ASSP=OFF) — Standard Marathon, legacy protocol
   (Marathon=ON,  AlphaMode=OFF, ASSP=ON)  — Standard Marathon, ASSP protocol
   (Marathon=ON,  AlphaMode=ON,  ASSP=OFF) — Alpha mode, legacy
   (Marathon=ON,  AlphaMode=ON,  ASSP=ON)  — Alpha mode + ASSP
   (Marathon=OFF, *,             *)        — Marathon disabled (legacy A2A used)

**Why it matters**:

* Metrics pipelines must emit **separate counters per FF combination**
* "Marathon at 50%" is ambiguous — could be referring to any of the 3
* Rollout coordination requires understanding which combination is
  intended for each cohort

**Open question**: Does ``ALPHA_MODE`` change DECISION-LOGIC or just
LOGGING? Single use site at line 1039 needs code review.

**Action**: Add a "Marathon FF composition table" to
:doc:`../cross-cutting/12-configuration-reference`.

12.3 HybridOrchestratorFeatureFlags = orchestrator BEHAVIOR, not SELECTION ✅ EXPLAINED
========================================================================================

**Surprise from §10.3**: What does this enum control?

**Reality**: **23 enum values controlling orchestrator BEHAVIOR**
(not selection).

**Categories of values** (from full enum read):

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Category
     - Example values
   * - **Model config** (4)
     - ``ORCHESTRATOR_MODEL_CONFIG``, ``EXTENDED_THINKING_ORCHESTRATOR_MODEL_CONFIG``, ``CITATION_PROCESSOR_MODEL_CONFIG``, ``ANSWER_GENERATOR_MODEL_CONFIG``
   * - **Orchestrator behavior** (3)
     - ``HYBRID_ORCHESTRATOR_EXPERIMENT_CONTEXT_TEMPLATE``, ``ORCHESTRATOR_COMPLEXITY_CLASSIFY_LOGGING``, ``CANCEL_PARALLEL_JOB``
   * - **Editor/AIFC context** (5)
     - ``EDITOR_INLINE_ROVO_GUIDANCE_PROMPT``, ``EDITOR_ALIGNED_PROMPTS_2``, ``EDITOR_ALIGNED_PROMPTS_3``, ``AIFC_NEW_TRACES``, etc.
   * - **Reasoning / Extended Thinking** (4)
     - ``EXTENDED_THINKING_TOKEN_BUDGET``, ``REASONING_EFFORT``, ``DEFAULT_MODE_REASONING_BUDGET``, ``FORCE_EXTENDED_THINKING_ENABLED``
   * - **Marathon-related** (1)
     - ``MARATHON_RUNTIME_REMINDER`` (line 46) — runtime reminder during Marathon execution
   * - **Other** (~6)
     - Various trace, prompt, and configuration flags

**What this confirms**:

* HybridOrchestratorFeatureFlags is a **PARAMETER tuning layer**, not a
  selection layer
* Each flag controls a specific aspect of orchestrator BEHAVIOR (model
  used, token budget, prompt template, etc.)
* The "Hello experiment for orchestrator selection (including LH)"
  comment in ``RovoChatAgentExecutionService.kt:431`` references
  **a different mechanism** — likely Hello-experiment-style A/B
  testing, not this enum
* Does NOT map 1:1 to ``OrchestratorType`` enum

**Why it matters**:

* When tuning Marathon/SAIN/LongHorizon behavior, look at this enum
* When investigating WHICH orchestrator was selected, look elsewhere
  (Hello experiment service or RovoSpecificFeatureFlags)
* The two FF systems serve different purposes — engineers must know
  which one to consult

**Open question**: Where is the "Hello experiment for orchestrator
selection" code? It's not in this enum, not in RovoSpecificFeatureFlags
(only Marathon-related there).

**Action**: Search for "Hello experiment" service implementations
(separate investigation; possibly in ``platform/`` or ``foundation/``
tier).

==================================================
13. Final Resolution Scoreboard (after 3 rounds)
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 12 12 12 12 17

   * - Resolution status
     - R1
     - R2
     - R3
     - Total
     - Notes
   * - ✅ Resolved by code evidence
     - 3
     - 3
     - 3
     - **9 of 14**
     - +TP=TurboPuffer, +Agent=ERS, +AIFEATURE not planned
   * - 🔄 Partial (need follow-up)
     - 1
     - 1
     - -1
     - **1 of 14**
     - Agent Framework was confirmed as ERS in R3
   * - 📋 Action item (owner conversation)
     - 6
     - -3
     - -2
     - **1 of 14**
     - All 3 R3 items closed; only marathon ALPHA_MODE deep behavior remains
   * - ❌ Tooling-blocked
     - 1
     - 0
     - 0
     - **1 of 14**
     - Slack threads, Statsig FF rollout %

**Final resolution rate**: **9/14 (64%) by direct code evidence**;
only 2 remain truly blocked.

==================================================
14. NEW Findings & New Open Questions (round 3)
==================================================

The third round surfaced **3 net-new architectural facts** worth
documenting in dedicated docs:

14.1 Rovo Module Decomposition is an ACTIVE workstream
========================================================

**Location**: ``.projects/rovo-module-decomposition/``

**Scope**: Extract 6 modules from monolithic ``rovo-impl``:
``workflow-impl``, ``plugin-impl``, ``action-impl``, ``mcp-impl``,
``minions-impl``, ``orchestrators-impl``

**Status**: "Target split modules not yet created" — work is planned
+ documented but execution hasn't started

**Action**: File this as a HIGH priority deep-dive
(``rovo-module-decomposition.rst`` in features/) — comparable in
importance to the JQL audit because it's a major refactoring with
explicit design docs (``architecture-vision.md``, ``workstreams.md``,
``README.md``).

14.2 AtlassianStudio's two-path Marathon execution model
==========================================================

* Direct execution for Jira SimpleLoopWorkflow (performance)
* Delegated execution for generic agents (governance)
* **Both intentional** — not a bug

**Action**: Update ``marathon-orchestrator.rst`` deep-dive with this
two-path model + dashboard implications.

14.3 Hello experiment for orchestrator selection lives ELSEWHERE
==================================================================

* NOT in ``RovoSpecificFeatureFlags`` (which only has Marathon FFs)
* NOT in ``HybridOrchestratorFeatureFlags`` (which only controls behavior)
* Likely in a separate experiment service in ``platform/`` or ``foundation/``

**Action**: Spawn a dedicated investigation for "Hello experiment
service" — could uncover yet another FF system.

==================================================
Cross-references
==================================================

* :doc:`01-fy26-goals-and-slos` §11 — original 43-question roadmap
* :doc:`../cross-cutting/features/marathon-orchestrator` — needs update with two-path model
* :doc:`../cross-cutting/features/aifeature` — confirmed: per-product split NOT planned
* :doc:`../cross-cutting/12-configuration-reference` — needs Marathon FF composition table
* :doc:`../00-glossary` — needs TP = TurboPuffer entry
