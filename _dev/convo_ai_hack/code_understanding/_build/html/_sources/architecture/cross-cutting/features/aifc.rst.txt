.. _feature-aifc:

==================================================================
AIFC — AI-First Creation (Create with Rovo)
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: ~2,107 LoC of AIFC-named integration code + ~5K LoC of related editor minions and schema agents in product modules
:Type: Cross-cutting framework (NOT a single sub-package)

.. contents:: On this page
   :local:
   :depth: 2

What AIFC IS (in one paragraph)
==================================

AIFC = **AI-First Creation** (a.k.a. "Create with Rovo"). It is the
**framework for generating Atlassian content from natural-language
prompts** — Confluence pages, whiteboards, databases, slides, and
similar artifacts. The user types "Create a kickoff page for project
X with sections Y and Z" and AIFC's pipeline (preprocessor → context
builder → schema/editor agents → output processor → finalize hooks)
produces the actual content in the right Atlassian product surface
with the right shape (ADF, HTML, database rows, etc).

AIFC is **NOT** a sub-package — it's a **cross-cutting framework** with
hooks distributed across modules:

* ``rovo-impl`` (action pipeline hooks: preprocessor, context-builder, output-processor, finalize)
* ``confluence-impl`` (editor minions, AIFC-aware sub-agents)
* ``rovo-extras-impl`` (content extractors)
* ``rovo-api`` (release helper, action configs)
* ``agent-framework-impl`` (schema-agent + minion infrastructure)

The cross-cutting nature is INTENTIONAL — each Atlassian product owns
its own AIFC integration (Confluence's editor minions know ADF;
JSM has plan editor minions; whiteboards have whiteboard logic), but
they all share the AIFC pipeline shape and metrics surface.

The "planned HybridOrchestrator flattening"
==============================================

The most important forward-looking comment in the entire AIFC area is
in ``AifcMetricsHelper.kt`` KDoc:

.. code-block:: text

   "Forward-compatible with the planned HybridOrchestrator flattening:
    when minions are called directly as schema agents, the same helper
    and tag shape apply."

**Decoded**: today, AIFC has TWO modes of running its component agents:

1. **Minion mode** — agents wrapped in a Minion class (e.g., ``FocusSummaryMinion``,
   ``CapacityPlanManageMinion``, ``EnrichActionItemMinion``)
2. **Schema agent mode** — same agents exposed as ``SchemaAgent``
   instances directly to an orchestrator (Hybrid or LongHorizon)

The "flattening" referenced is the migration FROM minion-wrapped TO
schema-agent-direct. The metrics helper is built to work in both modes
so the migration is incremental. This convergence is the same one
referenced in SAIN-LH's DESIGN_NOTES.md (where ``LongHorizonSubagentFlatteningService``
performs flattening on ``SchemaAgent`` instances).

**Implication**: AIFC, SAIN, and Marathon converge on the same agent
contract (``SchemaAgent``) at the bottom. AIFC's value-add is the
**creation pipeline** (preprocess → schema-agent → outputprocess →
finalize) layered on top of the orchestrator family.

Anatomy — where the code lives
=================================

**A. AIFC pipeline hooks** (``rovo-impl/.../product/rovo/action/``):

.. list-table::
   :header-rows: 1
   :widths: 56 12 32

   * - File
     - LoC
     - Role
   * - ``AIFCConfluenceCreatePageActionOutputProcessorHook.kt``
     - 247
     - **Largest AIFC hook**. Post-creation processor for "Create Page" — wires LLM output to Confluence Page creation
   * - ``ConfluenceAIFCFinalizeExecutionHook.kt``
     - 237
     - Final-stage cleanup — converts in-progress generation to a published page; emits success metrics
   * - ``AIFCConfluenceCreateWhiteboardActionOutputProcessorHook.kt``
     - 165
     - Whiteboard creation processor
   * - ``AIFCContentCreatePreProcessorHook.kt``
     - 151
     - **Preprocessor** — common to all AIFC create actions; sanity-checks input + populates context
   * - ``AIFCConfluenceDatabaseActionOutputProcessorHook.kt``
     - 150
     - Database row creation processor
   * - ``AIFCConfluenceUpdateWhiteboardDirectOutputProcessorHook.kt``
     - 146
     - In-place whiteboard updates
   * - ``AIFCConfluenceSlidesActionOutputProcessorHook.kt``
     - 100
     - Slides creation
   * - ``AIFCConfluenceDatabaseDirectOutputProcessorHook.kt``
     - 97
     - Direct (vs indirect) database update
   * - ``AIFCConfluenceUpdateSlidesDirectOutputProcessorHook.kt``
     - 78
     - Direct slides update
   * - ``AIFCConfluenceWhiteboardToPageActionOutputProcessorHook.kt``
     - 38
     - Convert whiteboard → page
   * - 4 context-builder hooks (whiteboard/database/slides/whiteboardToPage)
     - 80-120 each
     - Pre-LLM context assembly per surface

**B. AIFC content extractors** (``rovo-extras-impl/.../content/extractors/strategies/``):

.. list-table::
   :header-rows: 1
   :widths: 56 12 32

   * - File
     - LoC
     - Role
   * - ``AIFCConfluencePageExtractor.kt``
     - 47
     - Extract page content for AIFC consumption
   * - ``AIFCConfluencePageDeepExtractor.kt``
     - 46
     - Extract page + linked content (deep traversal)
   * - ``AIFCConfluenceWhiteboardExtractor.kt``
     - 46
     - Extract whiteboard ADF
   * - ``AIFCConfluenceDatabaseExtractor.kt``
     - 47
     - Extract database schema + rows

**C. AIFC editor minions** (in product modules):

.. list-table::
   :header-rows: 1
   :widths: 56 32 12

   * - File
     - Module
     - Role
   * - ``AdfEditorMinion.kt``
     - confluence-impl
     - ADF (Atlassian Document Format) editor — the standard rich-text format
   * - ``AdfEditorMinionStatefulChunkProcessor.kt``
     - confluence-impl
     - Streaming chunk processor for ADF generation
   * - ``HtmlEditorMinion.kt``
     - confluence-impl
     - HTML editor (legacy or specific surfaces)
   * - ``HtmlEditorMinionStatefulChunkProcessor.kt``
     - confluence-impl
     - Streaming chunk processor for HTML
   * - ``PlanEditorMinion.kt``
     - jsm-impl
     - JSM-specific plan editor

**D. AIFC infrastructure**:

* ``AifcMetricsHelper.kt`` (116 LoC) — central metrics emission helper (Schema Agent, Image Gen, Dynamic UI, Maui)
* ``AifcAdfUpdateActionConfig.kt`` (62 LoC) — config for ADF update actions
* ``ConfluenceAifcReleaseHelper.kt`` (48 LoC) — release-gate; checks Statsig + denies certain channels (iOS, Android, Slack, web extension)
* ``AifcTwgContextFetcher.kt`` (163 LoC) — TWG (Teamwork Graph) context fetching for AIFC personalization
* ``AIFCPromptOverrideHelper.kt`` (76 LoC) — workflow-level prompt override
* ``ConfluenceAIFCData.kt`` (28 LoC) — domain data type

**Total AIFC-named main code**: ~2,107 LoC across 21 files. The full
AIFC capability also draws on the broader ``minions/`` (69 files) and
``SchemaAgent`` (~36 files) infrastructure that's not exclusively AIFC.

The AIFC pipeline (the architectural pattern)
=================================================

AIFC follows a strict 4-stage pipeline for every "create" action:

.. code-block:: text

   1. PREPROCESS   ← AIFCContentCreatePreProcessorHook
        - Validate input
        - Resolve target surface (page/database/whiteboard/slides)
        - Initialize per-action context

   2. CONTEXT BUILD ← AIFCWhiteboardUpdateContextBuilderHook + others
        - Fetch existing content (via extractors)
        - Fetch TWG context (via AifcTwgContextFetcher)
        - Build LLM input

   3. AGENT EXEC   ← (calls into schema agent / minion)
        - LLM generates content
        - Streamed via stateful chunk processor
        - Output buffered to ADF / HTML / database rows

   4. OUTPUT PROCESS ← AIFCConfluenceXXXOutputProcessorHook
        - Post-process LLM output
        - Persist to Atlassian product (page create, etc.)
        - Apply post-creation hooks (e.g., default permissions)

   5. FINALIZE     ← ConfluenceAIFCFinalizeExecutionHook
        - Mark generation as complete
        - Emit success metrics
        - Notify UI

Each stage is a **Spring-discovered hook**. New surfaces (e.g., adding
"AI-create Stride channel") would mean implementing the same 5 hook
types. This is a clean **Pipeline pattern** with extension points.


Schema Agents — the LLM-callable building blocks
==================================================

Schema Agents are **typed sub-agents** (``SchemaAgent<TArgs, TResult>``)
that an orchestrator can call as if they were tools. They're contracted
in ``rovo-api/.../agent/minion/common/SchemaAgent.kt``.

**71 Schema Agents** exist across the codebase. Most cluster into:

**Jira Schema Agents** (~24 files) — primary AIFC tool surface for Jira:

* ``JiraNL2JQLSchemaAgent`` (NL → JQL)
* ``ValidateJqlSchemaAgent`` (validate JQL)
* ``EnhancedJqlExecutionSchemaAgent`` / ``JqlExecutionSchemaAgent`` / ``JqlExecutionSchemaAgentV1``
* ``SearchJqlFieldsSchemaAgent`` / ``SearchAndRankSystemFieldsSchemaAgent`` / ``JqlDocumentationSearchSchemaAgent``
* ``JiraSimilarIssuesSchemaAgent``
* ``JqlIssueCountSchemaAgent``
* ``JiraBulkIssueDeleteSchemaAgent``
* ``JiraUrlReadSchemaAgent``
* ``JiraActionToolBatchSchemaAgent``
* ``JiraProjectActionsSchemaAgent``
* ``GetUsersRecentJiraProjectsSchemaAgent``
* ``SearchProjectsSchemaAgent``
* ``JiraBatchSchemaAgent``
* Multiple V1/V2/Enhanced variants → suggests active version migration

**Cross-product sub-agent specs** (~7 files) — third-party / external surface specs:

* ``GoogleDriveSchemaAgentSpec``
* ``MicrosoftTeamsSchemaAgentSpec``
* ``MicrosoftOutlookCalendarSchemaAgentSpec``
* ``QueryDebuggerSchemaAgentSpec``
* ``FlattenedConfluenceSchemaAgentHelper``
* ``ConfluenceCreationSchemaAgent``
* ``JiraCreationSchemaAgent``
* ``TeamworkSchemaAgentV3``
* ``ImageSearchSchemaAgent``

**Long-Horizon executable** (1 file):

* ``LongHorizonExecutableAgentSchemaAgent``

The naming includes both ``SchemaAgent`` (the implementation) and
``SchemaAgentSpec`` (the specification — the agent is generated from a
spec at runtime). This is a **declarative agent pattern** — for
external services, the spec is enough to define the agent; for
Atlassian-internal services, full Kotlin implementations exist.

Editor Minions — the streaming output surface
================================================

Editor Minions are AIFC's **streaming generators** for editor surfaces.
Each one knows how to:

1. Accept a creation prompt
2. Call an LLM with the right system prompt + tools
3. Stream the response chunks
4. Apply chunks to a stateful buffer (ADF tree, HTML DOM, etc.)
5. Validate the final output
6. Return the persisted artifact

**5 main editor minions** in product modules:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Minion
     - Module
     - Output format
   * - ``AdfEditorMinion``
     - confluence-impl
     - ADF (Atlassian Document Format) — JSON tree
   * - ``AdfEditorMinionStatefulChunkProcessor``
     - confluence-impl
     - Helper for ADF chunk-streaming
   * - ``HtmlEditorMinion``
     - confluence-impl
     - HTML — for special surfaces (legacy or rich preview)
   * - ``HtmlEditorMinionStatefulChunkProcessor``
     - confluence-impl
     - HTML chunk-streaming
   * - ``PlanEditorMinion``
     - jsm-impl
     - JSM-specific plan-format

The ``StatefulChunkProcessor`` pattern is unusual — it's required
because:

* LLMs emit content as a token stream
* But ADF/HTML are **tree structures** — partial updates need to
  understand brace/tag nesting
* So each chunk arrives, gets parsed and merged into the in-progress
  tree, validated, then either accepted or used to trigger an
  intermediate render

**This is the Marathon-equivalent of "stream interpretation"** — but
for content artifacts instead of code execution.

Other AIFC sub-systems
========================

From ``AifcMetricsHelper.kt`` we see AIFC also covers:

* **Image Generation Agent** — image generation operations (CREATE, EDIT)
  with error type enum (``IMAGE_LLM_ERROR``, ``IMAGE_LLM_EXCEPTION``)

* **Dynamic UI Agent** — generates UI components on the fly
  (``DYNAMIC_UI_LLM_ERROR``, ``DYNAMIC_UI_LLM_EXCEPTION``)

* **Maui Client** — UNRESOLVED what "Maui" stands for; likely an
  Atlassian internal codename for a content-related service. Operations:
  ``GET``, ``SAVE``. Error type: ``MAUI_EXCEPTION``.

* **Schema Agent results** — every schema-agent invocation tracked
  with ``schema_agent_name``, ``result`` (SUCCESS/NO_ACTION/FAILURE),
  optional ``failure_reason``

The release-gate
==================

``ConfluenceAifcReleaseHelper.isAifcEnabled()`` (48 LoC) acts as the
master switch for "Create with Rovo":

.. code-block:: kotlin

   tenantContext.getConfluenceWorkspaceARI() != null &&
       tenantContext.experienceContext.experience != Experience.ROVO_CHAT_A2A_SERVER &&
       tenantContext.experienceContext.experience != Experience.ROVO_MSTEAMS_INTEGRATION &&
       !isDisabledEntryPoint(tenantContext.experienceContext.channelId) &&
       rolloutService.controlledByFullContext(SharedProductFeatureFlags.AIFC_CREATE_ENABLED)
           .replacing { false }
           .with { true }
           .value

**Disabled entry points** (hardcoded):

* ``ios``
* ``android``
* ``rovo-slack-svc``
* ``rovo-extension-web``

**Rationale**: AIFC requires the user to view the generated content in
a "specialised view" (a Confluence editor with AIFC-specific UI). These
surfaces don't have that view, so the experience is gated off.

Sequence diagram — AIFC "Create Page" flow
==============================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as User
       participant Chat as Rovo Chat
       participant Rel as ConfluenceAifc<br/>ReleaseHelper
       participant Pre as AIFCContent<br/>CreatePreProcessorHook
       participant Ctx as ContextBuilder<br/>Hooks
       participant TWG as AifcTwgContextFetcher
       participant Min as AdfEditorMinion
       participant Agent as Schema/Sub-agents
       participant LLM
       participant Out as AIFCConfluenceCreatePage<br/>OutputProcessorHook
       participant CR as Confluence REST
       participant Fin as ConfluenceAIFCFinalize<br/>ExecutionHook
       participant Met as AifcMetricsHelper

       U->>Chat: "Create a page about X"
       Chat->>Rel: isAifcEnabled(tenant, experience)
       Rel-->>Chat: enabled (or DISABLED → fall back)

       Chat->>Pre: preprocess(input)
       Pre->>Pre: validate, resolve surface=page
       Pre-->>Chat: PreparedAction(targetSurface, params)

       Chat->>Ctx: buildContext(prepared)
       Ctx->>TWG: fetchTwgContext(tenant, user)
       TWG-->>Ctx: linked-content context
       Ctx-->>Chat: AgentInput(prompt, context)

       Chat->>Min: invoke(input)
       Min->>LLM: stream generate

       loop streaming chunks
           LLM-->>Min: chunk (token)
           Min->>Min: StatefulChunkProcessor.consume(chunk)
           Min->>Chat: stream partial ADF preview
           Chat-->>U: live update
       end

       Note over Min,Agent: Optionally calls schema agents during gen
       Min->>Agent: invoke(args)
       Agent->>Met: recordSchemaAgentResult(name, SUCCESS)
       Agent-->>Min: result

       Min-->>Chat: final ADF tree
       Chat->>Out: process(output, prepared)
       Out->>CR: POST /wiki/api/v2/pages
       CR-->>Out: created page (id, url)
       Out-->>Chat: outputProcessed

       Chat->>Fin: finalize(prepared, output)
       Fin->>Met: emit AIFC success metrics
       Fin-->>Chat: complete

       Chat-->>U: "Created page: <link>"

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - System
     - How
     - Used for
   * - **AI Gateway** (LLM)
     - 1 main + N schema-agent calls
     - Generation + sub-task tool calls
   * - **Confluence REST**
     - via platform-tier client
     - Page/whiteboard/database/slides creation
   * - **JSM**
     - via JSM client
     - Plan creation
   * - **TWG** (Teamwork Graph)
     - via ``AifcTwgContextFetcher``
     - Personalization context (linked content, recently viewed)
   * - **Maui** (UNRESOLVED)
     - via Maui client
     - Unknown — possibly content storage service
   * - **Image generation service**
     - via Image LLM
     - AI-generated images for pages
   * - **Statsig**
     - ``AIFC_CREATE_ENABLED`` + per-surface flags
     - Rollout control
   * - **MetricsService**
     - via ``AifcMetricsHelper``
     - 5 metric domains: Schema Agent, Image Gen, Dynamic UI, Maui, generic


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
     - **Cross-cutting framework with no central README**
     - distributed
     - 21 AIFC-named files + 5 editor minions + 36 schema agents across 5+ modules. Hard to discover. Consider a central index doc; this page is a start.
   * - 🔴
     - **HardCoded "disabled entry points"** for AIFC
     - ConfluenceAifcReleaseHelper.kt:DISABLED_CHANNEL_IDS
     - Hardcoded ``setOf("ios", "android", "rovo-slack-svc", "rovo-extension-web")``. Should be a Statsig flag for operational flexibility (re-enable if surfaces gain editor support without code change).
   * - 🟡
     - **AIFC + Schema Agent + Editor Minion = three overlapping concepts**
     - cross-cutting
     - "Minion" is wrapping an agent. "Schema Agent" is a typed agent. "AIFC hooks" wrap actions invoking minions. The relationship is layered but the naming is confusing for newcomers.
   * - 🟡
     - **Multiple Jql*SchemaAgent variants** (V1, V2, Enhanced, Validate, Documentation, Search, etc.)
     - jirabatchagents/
     - Suggests active version migration. Worth deduplication audit + sunset of older variants.
   * - 🟡
     - **"Maui" client is undocumented**
     - AifcMetricsHelper
     - ``MauiOperation``, ``MauiErrorType`` — what's Maui? No KDoc, no README.
   * - 🟡
     - **Planned ``HybridOrchestrator flattening``** — direction stated but timeline unclear
     - AifcMetricsHelper KDoc
     - "Forward-compatible with the planned HybridOrchestrator flattening" — when is this planned for? No ADR.
   * - 🟡
     - **Stateful chunk processor pattern** is duplicated for ADF and HTML
     - confluence-impl
     - Both ``AdfEditorMinionStatefulChunkProcessor`` and ``HtmlEditorMinionStatefulChunkProcessor`` exist. Could share an abstract base.
   * - 🟡
     - **AIFC content extractors are 4 separate strategies**
     - rovo-extras-impl
     - PageExtractor, PageDeepExtractor, WhiteboardExtractor, DatabaseExtractor. The "Page" + "PageDeep" split could be a single class with a depth parameter.
   * - 🟢
     - **Per-tenant disabled list** is also missing
     - ConfluenceAifcReleaseHelper
     - Currently global hardcoded list; if a single tenant should be excluded, no mechanism today.
   * - 🟢
     - **Minor**: The pipeline order (preprocess → context → exec → output → finalize) is implicit
     - distributed
     - Spring discovers hooks via interface + ``@Component``. Order is enforced by phase but not documented at one place.

Refactoring opportunities
============================

1. **Add a central AIFC README** (XS, 🔴 high) — short doc at ``rovo-impl/.../action/`` pointing to all 5 hook types + this deep-dive. ~1 hour.

2. **Move ``DISABLED_CHANNEL_IDS`` to Statsig** (XS, 🔴 high) — make the disabled-entry-points list operationally configurable. ~1 hour.

3. **Consolidate ``Page`` and ``PageDeep`` extractors** (XS, 🟡 medium) — single class with ``depth`` param. ~1 hour.

4. **Extract abstract ``StatefulChunkProcessor``** (S, 🟡 medium) — share infrastructure between ADF and HTML processors. ~half day.

5. **Audit and sunset old Jql*SchemaAgent variants** (M, 🟡 medium) — V1 vs Enhanced + Search vs Validate vs Documentation. Identify which are dead. ~1 day.

6. **Document Maui** (XS, 🟡 medium) — find its purpose and add a README. ~30 min.

7. **Plan and execute the HybridOrchestrator flattening migration** (L, 🟡 medium-high) — major refactor; timeline TBD; ADR needed first.

8. **Expose AIFC hook order via a reified ``Phase`` enum** (S, 🟢 low) — make the pipeline explicit (e.g., ``@AifcPhase(PRE)``).

9. **Add a per-tenant exclusion list** (S, 🟢 low) — once Statsig flag is created (#2), allow per-tenant overrides.

What you would change here
============================

* **Add a new "Create with Rovo" surface** (e.g., Stride channels):
   1. Implement ``AIFCXxxContentCreatePreProcessorHook``
   2. Implement ``AIFCXxxContextBuilderHook``
   3. Implement ``XxxEditorMinion`` + ``XxxEditorMinionStatefulChunkProcessor`` in the product module (e.g., ``stride-impl``)
   4. Implement ``AIFCXxxOutputProcessorHook``
   5. Implement ``XxxAIFCFinalizeExecutionHook``
   6. Register all hooks via ``@Component``
   7. Update release-helper to allow the new entry-point channel

* **Add a new schema agent** → new ``XxxSchemaAgent.kt`` extending ``SchemaAgent``, ``@Component`` annotate

* **Tweak generation prompt for a surface** → ``AIFCPromptOverrideHelper.kt`` OR the surface's editor minion

* **Add new metrics** → extend ``AifcMetricsHelper.kt`` with new method + tag enum

* **Change the disabled-channel list** → ``ConfluenceAifcReleaseHelper.DISABLED_CHANNEL_IDS`` (today; Statsig flag tomorrow)

* **Add new image-gen error types** → ``AifcMetricsHelper.ImageGenerationErrorType`` enum

What you would NOT change here
================================

* LLM provider — owned by ``platform/service/service-impl``
* Confluence REST endpoints — owned by ``platform/client/.../confluence``
* SchemaAgent base interface — owned by ``rovo-api/.../agent/minion/common``
* Streaming primitives — owned by ``rovo-impl/.../chat/streaming``
* TWG context retrieval contract — owned by ``platform/service/.../ags``
* Generic Minion infrastructure — owned by ``agent-framework-impl``

Verification audit log
========================

✅ **Personally verified with bash:**

* All 21 AIFC-named files (find + sort by LoC)
* AIFC total: ~2,107 LoC across 21 named files
* AifcMetricsHelper.kt fully read (116 LoC)
* Five Schema Agent / Image Gen / Dynamic UI / Maui / Editor Minion sub-systems identified from metrics enum
* ConfluenceAifcReleaseHelper.kt top read — 4 disabled channels + 2 disabled experiences confirmed
* 5 editor-minion files in product modules (find with grep filter)
* 71 SchemaAgent files inventory (find ``*SchemaAgent*.kt``)
* 4 content extractor strategies (find ``AIFCConfluence*Extractor.kt``)
* 5 pipeline-hook types confirmed by file naming (PreProcessor / ContextBuilder / OutputProcessor / Execution / Finalize)
* "HybridOrchestrator flattening" forward-comment confirmed in ``AifcMetricsHelper.kt`` KDoc
* TWG context fetcher exists at ``confluence-impl/agent/confluence/minion/AifcTwgContextFetcher.kt``

⚠️ **Inferred from naming + structure** (not deep-read):

* Pipeline ordering (preprocess → context → exec → output → finalize) — inferred from phase names, not from a Spring config that asserts order
* StatefulChunkProcessor mechanics — inferred from class name + chunked-LLM-token reality; full state-machine logic not read
* Schema Agent vs SchemaAgentSpec distinction — inferred from naming pattern, not from the base contract files
* Image Generation Agent + Dynamic UI Agent locations — inferred from metric enums; actual implementation file locations not enumerated

❌ **UNVERIFIED:**

* What "Maui" is / does
* Concrete DI wiring of pipeline hooks (Spring config that orders them)
* Whether ``AIFC_CREATE_ENABLED`` is at 100% rollout or partial
* Per-surface (page vs whiteboard vs slides) success rate distribution
* Whether the planned "HybridOrchestrator flattening" migration has a target date

Open questions for institutional knowledge
=============================================

1. **What is Maui?** Where does its code live? What's its role in AIFC?
2. **When is the planned ``HybridOrchestrator flattening``?** ADR? Roadmap?
3. **What are the rollout percentages** for ``AIFC_CREATE_ENABLED`` per surface (page vs whiteboard vs slides)?
4. **Why is JSM ``PlanEditorMinion`` separate from Confluence editor minions?** Different team owners or different output format?
5. **Are V1 Jql*SchemaAgents safe to delete?** Multiple V1/V2/Enhanced variants exist.
6. **Is the StatefulChunkProcessor pattern formalized or duplicated?** Different implementations for ADF/HTML — should they share a base?
7. **What's the typical end-to-end latency for a page creation via AIFC?** And what's the failure rate (LLM error / Confluence REST 5xx / chunk parse failure)?


==================================================================
Open Questions — Resolved (2026-05-02 follow-up)
==================================================================

**Q1: What is Maui? — RESOLVED (High confidence)**

Maui is **Atlassian's AI-generated mini-app compilation service** —
a backend service (``maui-service``) that compiles user/AI-authored
web mini-apps (HTML/JS/CSS source code packaged as tarballs) into
deployable artifacts that get embedded as ``native-embed:maui`` ADF
extensions in Confluence content.

Evidence:

* ``platform/client/.../maui/MauiClientImpl.kt`` (296 LoC) — full client
* ``platform/client/.../maui/MauiClientConfiguration.kt`` (54 LoC) — Spring config
* ``foundation/.../adf/AdfToMarkdownConverter.kt:631`` — ``if (extensionKey == "native-embed:maui")``
* ``platform/service/.../imagegeneration/ImageGenerationResponse.kt:38`` — ``// Media collection (e.g. maui-personal-collection-*) if uploaded successfully``
* OTel trace attributes show full pipeline:
   * ``maui.compile.request_id``, ``maui.compile.cloud_id``, ``maui.compile.entry_point``
   * ``maui.compile.file_count``, ``maui.compile.base_manifest_tar_bytes``
   * ``maui.compile.prepare_tar``, ``maui.compile.compress_gzip``, ``maui.compile.http_compile``
   * ``maui.compile.tar_input_bytes``, ``maui.compile.compressed_input_bytes``

**Maui Client API surface** (4 methods on ``MauiClient`` interface):

.. list-table::
   :header-rows: 1
   :widths: 24 12 64

   * - Method
     - Suspend
     - Purpose
   * - ``getManifest()``
     - ✓
     - Fetch the catalog/index of available app templates and their versions. Cached for **5 min** (Caffeine; ``DEFAULT_MANIFEST_CACHE_TTL_SECONDS = 300L``)
   * - ``get(...)``
     - ✓
     - Fetch existing app source code by app id (line 104). Used to load apps the LLM is going to edit
   * - ``save(...)``
     - ✓
     - Save authored or edited app source (line 203)
   * - ``compile(...)``
     - ✓
     - **The big one**: package source files as tarball, gzip, POST to ``maui-service`` for compilation (line 230). Tracks file count, tar size, compressed size as OTel attributes for cost/quota monitoring.

**Workspace headers** (line 71): Maui requires ``ATL_ACTIVATION_ID`` and
``ATL_WORKSPACE_ID`` headers in addition to the standard ``User-Context``
+ ``atl-cloudid`` propagation. Workspace context comes from the product
context's ``workspaceARI``. Manifest version + LLM model are sent as
``x-manifest-version`` + ``x-manifest-model`` headers.

**Why this matters for AIFC**: Maui is one of the **5 metric domains**
in ``AifcMetricsHelper``. It enables the "AI generates an interactive
app embedded in your Confluence page" flow — distinct from "AI generates
static content in your page". Examples of likely Maui use cases:
calculators, charts, interactive demos, mini-tools the AI authored
on the user's behalf.

**Q2: SAIN Hybrid orchestrator deprecation timeline — UNRESOLVED in source**

NO ``@Deprecated`` annotation, NO TODO comments, NO ADR found in source
referencing a sunset date. The legacy ``SainHybridOrchestratorAgent``
(499 LoC) coexists with ``SainStandaloneHybridOrchestratorAgent`` (1,908 LoC,
current production) gated by ``SAIN_DIRECT_HYBRID_ORCHESTRATOR`` and
``SAIN_STANDALONE_HYBRID_ORCHESTRATOR`` flags.

**Recommendation**: Track this as a **process gap** — the team should:

1. Document a target date (e.g., "remove legacy Hybrid by 2026-Q3")
2. Add ``@Deprecated`` annotation with replacement = ``SainStandaloneHybridOrchestratorAgent``
3. File a tech-debt ticket

This is a documentation/process question, not a code question.

**Q3: Planned ``HybridOrchestrator flattening`` date — UNRESOLVED**

Only TWO references in source:

* ``AifcMetricsHelper.kt:14`` (KDoc — "Forward-compatible with the
  planned HybridOrchestrator flattening")
* ``.agents/skills/investigate-aifc-issue/SKILL.md`` (skill doc, not
  loaded into this audit)

NO dedicated ADR, NO migration plan, NO target date in source. This
is **intentional architectural direction** but **not currently
scheduled**. The closest concrete artifact is ``LongHorizonSubagentFlatteningService``
in SAIN-LH (already implementing the pattern for SAIN).

**Recommendation**: Investigate the SKILL.md referenced above; it may
have the rationale. Otherwise, file an ADR + roadmap entry to make
the direction trackable.

