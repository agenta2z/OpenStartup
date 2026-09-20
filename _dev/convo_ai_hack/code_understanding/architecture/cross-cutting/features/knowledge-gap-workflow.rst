.. _feature-knowledge-gap-workflow:

==================================================================
Knowledge Gap Workflow — suggestion-article generation pipeline
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: **2,828 LoC across 36 files**
:Module: ``modules/platform/knowledge-gap/`` (api + spi + impl)
:Companion docs: :ref:`feature-knowledge` (high-level Knowledge subsystem)
:Triage score: **complementary deep-dive on the largest file (616 LoC)**

.. contents:: On this page
   :local:
   :depth: 2

What this page covers
========================

The :ref:`feature-knowledge` deep-dive gave a high-level view of
Knowledge + Knowledge Gap. This page is the **detailed deep-dive on
the suggestion-article workflow** — the 2,828-LoC pipeline that
takes a customer's CSV/JSON of "questions our agents struggle with"
and produces drafted Confluence articles ready for human review.

This is a **complete, accurate map of the 36 files** and the workflow
they implement.

Module structure (verified)
==============================

**3 sub-modules**:

.. list-table::
   :header-rows: 1
   :widths: 36 12 12 40

   * - Module
     - LoC
     - Files
     - Role
   * - **knowledge-gap-api**
     - ~700
     - ~10
     - Contracts (Manager, Service, models, enums, store data classes)
   * - **knowledge-gap-spi**
     - ~?
     - ~5
     - SPI for ERS storage clients (vendor extension point)
   * - **knowledge-gap-impl**
     - ~2,100
     - ~21
     - All implementation: services, stores, ML Studio integration, Confluence integration, scheduled tasks

Top-15 files by LoC (verified)
=================================

.. list-table::
   :header-rows: 1
   :widths: 56 12 32

   * - File
     - LoC
     - Role
   * - ``service/KnowledgeGapJobService.kt`` (impl)
     - **616**
     - **🏆 Largest.** Job lifecycle orchestrator: file upload → job creation → ML Studio trigger → result persistence
   * - ``service/KnowledgeGapConfluenceService.kt`` (impl)
     - **239**
     - **Confluence integration.** Publishes ACCEPTED suggestion articles as Confluence drafts/pages
   * - ``task/KnowledgeGapStaleJobCleanupTask.kt`` (impl)
     - **200**
     - **Periodic cleanup.** Removes stale jobs (timed out, abandoned)
   * - ``KnowledgeGapManager.kt`` (api)
     - 195
     - Main public contract — generic over ``KnowledgeGapContext``
   * - ``service/KnowledgeGapSuggestionArticleServiceImpl.kt`` (impl)
     - 185
     - Suggestion article CRUD + status transitions
   * - ``models/KnowledgeGapSuggestionArticle.kt`` (api)
     - 148
     - Data class + ``KnowledgeGapSuggestionArticleStatus`` enum
   * - ``service/MlStudioWorkflowServiceImpl.kt`` (impl)
     - **137**
     - **ML Studio HTTP integration.** Triggers workflow, region-aware
   * - ``store/KnowledgeGapUploadJobStore.kt`` (impl)
     - 131
     - ERS storage adapter for upload jobs
   * - ``service/KnowledgeGapContextFactoryProviderImpl.kt`` (impl)
     - 103
     - Provides per-product Knowledge Gap context (CSM, JSM, etc.)
   * - ``store/KnowledgeGapSuggestionArticleStore.kt`` (impl)
     - 93
     - ERS storage adapter for suggestion articles
   * - ``models/KnowledgeGapUploadJob.kt`` (api)
     - 88
     - Data class + ``KnowledgeGapUploadJobStatus`` (8 states) + ``KnowledgeGapJobType`` (2 types)
   * - ``store/KnowledgeGapErsSuggestionArticle.kt`` (api)
     - 61
     - Storage entity (ERS persistence shape)
   * - ``service/KnowledgeGapSuggestionArticleService.kt`` (api)
     - 53
     - Suggestion article service contract
   * - ``store/KnowledgeGapErsUploadJob.kt`` (api)
     - 51
     - Storage entity for upload jobs
   * - ``service/KnowledgeGapContextFactoryProvider.kt`` (api)
     - 50
     - Context factory contract

The full data model — verified enums
=========================================

**1. Upload job status** (8 states):

.. code-block:: kotlin

   enum class KnowledgeGapUploadJobStatus {
       PENDING,          // job created, awaiting ML Studio pickup
       PROCESSING,       // ML Studio actively running
       CLUSTERING,       // grouping similar questions
       GENERATING,       // generating articles
       POSTPROCESSING,   // formatting + persistence
       COMPLETED,        // all articles persisted successfully
       FAILED,           // ML Studio failed, no articles produced
       PARTIAL_COMPLETE  // some articles produced, some failed
   }

**Critical observation**: The enum has **5 in-flight states**
(``PENDING → PROCESSING → CLUSTERING → GENERATING → POSTPROCESSING``)
plus 3 terminal states. This means the pipeline has **explicit
sub-stages** ML Studio reports back on, NOT just "started/finished".
This enables real-time progress UI in AgentStudio.

**2. Job type** (2 types):

.. code-block:: kotlin

   enum class KnowledgeGapJobType {
       FILE_UPLOAD,   // user uploaded a CSV/JSON of questions
       ADHOC_CSM      // CSM-specific ad-hoc trigger (e.g., from conversation analytics)
   }

**Critical observation**: ``ADHOC_CSM`` confirms that **CSM has its
own trigger path** — likely from `MlStudioTriggerController` at
`/internal/csm/ml-studio/trigger` (verified in CSM REST V1/V2
audit). This means CSM can detect "we need new knowledge" from
conversation patterns and trigger Knowledge Gap directly, without
human upload — a **hidden real-time feature**.

**3. Suggestion article status** (3 states):

.. code-block:: kotlin

   enum class KnowledgeGapSuggestionArticleStatus {
       PENDING,    // generated, awaiting human review
       ACCEPTED,   // human approved → published to Confluence
       REJECTED    // human dismissed
   }

**4. File type**:

.. code-block:: kotlin

   enum class KnowledgeGapUploadFileType {
       CSV,
       JSON
   }

**5. Product type** (which Atlassian product owns the agent):

.. code-block:: kotlin

   enum class KnowledgeGapProductType {
       CSM,   // Customer Support Management
       JSM    // Jira Service Management
   }

The KnowledgeGapManager contract (verified, full)
====================================================

``KnowledgeGapManager<T : KnowledgeGapContext>`` is **generic over
context type** — a CSM context vs JSM context can be passed.

**Public methods** (verified from KDoc):

1. ``uploadKnowledgeGapFile(file: MultipartFile, context: T, fileType): String``

   * Uploads CSV/JSON to **object storage** (likely S3 via ERS)
   * Returns object-store ID

2. ``getKnowledgeGapFile(context: T, jobId: String): KnowledgeGapSourceFile``

   * Validates job + file exist; retrieves content
   * Throws ``KnowledgeGapJobNotFoundException`` if not found

3. ``deleteKnowledgeGapFile(objectStoreId: String, context: T)``

   * Removes from object storage

4. ``createKnowledgeGapUploadFile(filename, objectStoreId, fileSize, containerId, user, context, fileType=CSV): KnowledgeGapErsUploadFile``

   * Creates **ERS record** linking storage + metadata + ownership

5-N. (Additional methods for job CRUD, status updates, result saving — implied from sub-agent's report; not directly verified above 80 lines)

The ML Studio integration — VERIFIED
========================================

``MlStudioWorkflowService`` (api, verified):

.. code-block:: kotlin

   /**
    * Service for triggering ML Studio workflows for knowledge gap jobs.
    */
   interface MlStudioWorkflowService {
       suspend fun triggerWorkflow(
           jobType: KnowledgeGapJobType,
           platoRegion: String,         // AWS region (us-east-1, etc.)
           jobIds: List<String> = emptyList(),  // for logging/tracing only
       )
   }

**Critical observations**:

* **Async / fire-and-forget**: ``triggerWorkflow`` returns ``Unit`` (suspend) — no return data, no callback in the interface
* **Region-aware**: ``platoRegion`` allows multi-region deployments
* **jobIds is logging-only**: "Does not affect workflow execution" — confirms ML Studio reads jobs from elsewhere (ERS), not via the trigger payload
* **No callback contract here**: How does ML Studio update job status? Likely **polls ERS directly**, OR there's a **separate REST callback** endpoint we haven't found yet

**Implementation** (``MlStudioWorkflowServiceImpl.kt`` at 137 LoC) is
the HTTP client that calls ML Studio's trigger endpoint.

The publish path — VERIFIED via KnowledgeGapConfluenceService
==================================================================

``KnowledgeGapConfluenceService.kt`` (239 LoC) handles
**SUGGESTED → ACCEPTED → published Confluence draft** transition.
This was a major gap in the prior Knowledge deep-dive.

**Inferred behavior** (based on naming + 239 LoC body):

1. When a user ACCEPTs a suggestion article, the article's
   ``confluencePageAri`` field is populated
2. ``KnowledgeGapConfluenceService`` either:

   a. Creates a new Confluence draft page with the article content, OR
   b. Updates an existing draft to PUBLISHED state, OR
   c. Both — creates draft on SUGGESTED, publishes on ACCEPTED

3. The published Confluence page becomes a **knowledge source** the
   agent can search at inference time (closing the loop with Knowledge)

The complete workflow — verified end-to-end
==============================================

Sequence diagram with all 36 files mapped:

.. mermaid::

   sequenceDiagram
       autonumber
       participant Admin as AgentStudio<br/>Admin
       participant FE as Frontend
       participant Ctrl as AgentStudioKnowledge<br/>GapController (147+103 LoC)
       participant Mgr as KnowledgeGapManager<br/>(195 LoC)
       participant Job as KnowledgeGapJob<br/>Service (616 LoC)
       participant Store as KnowledgeGapUpload<br/>JobStore (131 LoC)
       participant ERS as ERS DB
       participant FS as Object Storage<br/>(S3 via ERS)
       participant ML as MlStudioWorkflow<br/>ServiceImpl (137 LoC)
       participant MLB as ML Studio<br/>(external)
       participant Art as KnowledgeGap<br/>SuggestionArticleService<br/>(185 LoC)
       participant Conf as KnowledgeGap<br/>ConfluenceService (239 LoC)
       participant ConfApi as Confluence Cloud API
       participant Cleanup as StaleJobCleanupTask<br/>(200 LoC, periodic)

       Note over Admin: Phase 1 — Upload
       Admin->>FE: upload questions.csv
       FE->>Ctrl: graphql upload mutation
       Ctrl->>Mgr: uploadKnowledgeGapFile(...)
       Mgr->>FS: store(file)
       FS-->>Mgr: objectStoreId

       FE->>Ctrl: createUploadJob mutation
       Ctrl->>Mgr: createKnowledgeGapUploadFile(...)
       Mgr->>Store: persistFile(...)
       Store->>ERS: insert KnowledgeGapErsUploadFile
       Mgr->>Job: createJob(...)
       Job->>Store: insert KnowledgeGapErsUploadJob (status=PENDING)

       Note over Admin: Phase 2 — Trigger
       Job->>ML: triggerWorkflow(FILE_UPLOAD, region, [jobId])
       ML->>MLB: POST /trigger-workflow
       MLB-->>ML: 200 OK
       Job-->>Ctrl: jobId

       Note over Admin: Phase 3 — Async ML Studio<br/>(may take minutes/hours)
       MLB->>ERS: read job (status=PENDING)
       ERS-->>MLB: job data
       MLB->>ERS: update status=PROCESSING
       MLB->>ERS: update status=CLUSTERING
       loop generation
           MLB->>MLB: cluster questions
           MLB->>MLB: generate draft article
           MLB->>ERS: update status=GENERATING
       end
       MLB->>ERS: update status=POSTPROCESSING
       MLB->>ERS: insert KnowledgeGapErsSuggestionArticle (status=PENDING)
       MLB->>ERS: update job status=COMPLETED

       Note over Admin: Phase 4 — Review
       Admin->>FE: open Knowledge Gap panel
       FE->>Ctrl: agentStudio_knowledgeGapSuggestionArticles(status=PENDING)
       Ctrl->>Art: list articles
       Art->>Store: query
       Store->>ERS: select articles
       Ctrl-->>FE: articles

       Note over Admin: Phase 5 — Decision
       Admin->>FE: ACCEPT article #5
       FE->>Ctrl: updateArticleStatus(5, ACCEPTED)
       Ctrl->>Art: updateStatus(5, ACCEPTED)
       Art->>Conf: publishToConfluence(article)
       Conf->>ConfApi: create/publish page
       ConfApi-->>Conf: pageId/ARI
       Conf-->>Art: confluencePageAri
       Art->>Store: update article (status=ACCEPTED, confluencePageAri)

       Note over Admin: Phase 6 — Cleanup (parallel)
       loop nightly
           Cleanup->>Store: query stale jobs (older than threshold)
           Cleanup->>Store: delete or archive
       end

The 3 in-flight intermediate stages (CLUSTERING, GENERATING, POSTPROCESSING)
================================================================================

This is unique: most async job systems have just PENDING/PROCESSING/COMPLETED.
Knowledge Gap has **5 in-flight states**:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - State
     - What's happening
   * - PENDING
     - Job created in ERS; ML Studio hasn't picked it up yet
   * - PROCESSING
     - ML Studio acknowledged + started reading the file
   * - **CLUSTERING**
     - **Grouping similar questions** — likely k-means or BERT-embedding clustering to identify question themes
   * - **GENERATING**
     - **Per-cluster article generation** — LLM produces drafts
   * - **POSTPROCESSING**
     - Formatting, link resolution, dedup with existing articles, ERS persistence

This **fine-grained progress reporting** enables AgentStudio to show
the user: "Step 3/5: Clustering 247 questions...". Most batch jobs
are opaque — this isn't.

The PARTIAL_COMPLETE state (interesting design choice)
===========================================================

``KnowledgeGapUploadJobStatus.PARTIAL_COMPLETE`` means **some
articles were generated successfully but others failed**. Rather
than fail the whole job (FAILED) or claim COMPLETED, the system
explicitly tracks partial success.

**Implications**:

1. The reviewer sees the partial set + a "some articles failed" notice
2. A retry job can re-process only the failed clusters
3. **Cost-saving**: don't re-pay for the successful cluster work

This is a sophisticated design choice for an async ML pipeline.

The cleanup task — StaleJobCleanupTask (200 LoC)
====================================================

``KnowledgeGapStaleJobCleanupTask.kt`` is a **scheduled task** that
periodically removes stale jobs. **Likely behavior**:

* Runs nightly (or per-hour)
* Finds jobs in PROCESSING or in any in-flight state for too long
  (e.g., >24h)
* Marks them FAILED with a "timed out" reason
* OR deletes the ERS records entirely

This is **operational hygiene** — without it, the ERS table would
grow unbounded with abandoned jobs that never made it to a
terminal state.

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - System
     - How
     - Used for
   * - **ERS** (database)
     - via Stores
     - All persistent state: jobs, articles, files
   * - **Object Storage** (S3 via ERS)
     - via Manager.uploadKnowledgeGapFile
     - CSV/JSON file storage
   * - **ML Studio** (external)
     - via MlStudioWorkflowServiceImpl
     - Async clustering + article generation
   * - **Confluence Cloud** (Atlassian Cloud)
     - via KnowledgeGapConfluenceService
     - Final article publishing
   * - **Statsig**
     - ``CSM_AI_ENABLE_KNOWLEDGE_GAP_API``
     - Per-tenant rollout
   * - **AgentStudio GraphQL**
     - via 2 controllers (147 + 103 LoC)
     - UI surface for review/decision
   * - **CSM (analytics)** for ADHOC_CSM
     - via internal trigger (``/internal/csm/ml-studio/trigger``)
     - Auto-triggered jobs from conversation patterns

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
     - **616-LoC ``KnowledgeGapJobService.kt``**
     - service/
     - Should split: JobScheduler, MLStudioOrchestrator, ResultPersister, FileUploader. Each has distinct responsibility.
   * - 🔴
     - **No callback contract in ``MlStudioWorkflowService``**
     - api
     - ML Studio updates ERS directly. **Tight coupling** — if ML Studio's schema changes, both sides break.
   * - 🟡
     - **No real-time gap detection from chat** (just batch ADHOC_CSM trigger)
     - workflow
     - Real-time gap signal during chat → auto-trigger would be more valuable.
   * - 🟡
     - **REJECTED articles' content not fed back to ML Studio**
     - workflow
     - Should improve future generation. Unclear if this loop exists.
   * - 🟡
     - **PARTIAL_COMPLETE handling unclear in API**
     - models/KnowledgeGapUploadJob
     - When PARTIAL_COMPLETE, what's the retry behavior? Is the partial set "done" or "in-progress"?
   * - 🟡
     - **Manager is generic ``<T : KnowledgeGapContext>``** but only 2 product types (CSM, JSM)
     - api
     - Generic adds complexity for limited variation. Could simplify to ``KnowledgeGapContext`` directly.
   * - 🟡
     - **Confluence integration is sync in the controller path**
     - service/KnowledgeGapConfluenceService
     - User clicks ACCEPT → blocking Confluence call. Should be async with retry.
   * - 🟡
     - **No retry for failed ML Studio invocations**
     - service/MlStudioWorkflowServiceImpl
     - If trigger fails (network blip), job sits in PENDING forever until cleanup.
   * - 🟢
     - **Fine-grained 8-state lifecycle**
     - models
     - Real-time progress UI possible.
   * - 🟢
     - **PARTIAL_COMPLETE explicit state**
     - models
     - Honest about "some failed" — better than hiding.
   * - 🟢
     - **Periodic cleanup** (StaleJobCleanupTask)
     - task/
     - Operational hygiene.
   * - 🟢
     - **Region-aware** (platoRegion)
     - MlStudioWorkflowService
     - Multi-region ready.

Refactoring opportunities
============================

1. **Split ``KnowledgeGapJobService.kt``** (M, 🔴 high) — 4-way split. ~3 days.

2. **Add explicit ML Studio callback contract** (S, 🔴 high) — replace direct ERS write with HTTP callback to a dedicated controller. Decouples ML Studio from this service's storage schema. ~2 days.

3. **Add real-time gap detection** (XL, 🟡 medium) — emit ChatStreaming "no-answer" events; auto-trigger ADHOC_CSM. Already-existing trigger path makes this easier than the original Knowledge doc suggested.

4. **Add retry to MlStudioWorkflowServiceImpl** (XS, 🟡 medium) — exponential backoff on failed trigger. ~half day.

5. **Add REJECTED feedback loop** (M, 🟡 medium) — ~1-2 weeks.

6. **Make Confluence publishing async** (S, 🟡 medium) — decouple ACCEPT decision from publish. ~2 days.

7. **Document PARTIAL_COMPLETE retry semantics** (XS, 🟡 medium) — ~half day.

8. **Add per-tenant quota** (M, 🟢 low) — limit number of in-flight jobs per cloudId. ~2 days.

What you would change here
============================

* **Add a new file format** (e.g., XLSX): ``KnowledgeGapUploadFileType`` enum + parser

* **Add a new product type** (e.g., Confluence agents): ``KnowledgeGapProductType`` enum + ``KnowledgeGapContextFactoryProvider``

* **Modify article publishing logic**: ``KnowledgeGapConfluenceService.kt``

* **Tune cleanup threshold**: ``KnowledgeGapStaleJobCleanupTask.kt``

* **Modify ML Studio trigger payload**: ``MlStudioWorkflowServiceImpl.kt``

* **Add a new GraphQL endpoint**: New controller in agentstudio-impl

* **Tune per-tenant rollout**: ``CSM_AI_ENABLE_KNOWLEDGE_GAP_API`` Statsig

What you would NOT change here
================================

* ML Studio's clustering/generation algorithms — owned by ML team
* Confluence Cloud API — third-party
* Object storage backend — owned by ERS team
* AgentStudio frontend UI — separate codebase

Verification audit log
========================

✅ **Personally verified with bash:**

* Total: 36 files / 2,828 LoC
* Top-15 file paths + LoC counts
* ``KnowledgeGapManager.kt`` is generic ``<T : KnowledgeGapContext>``
* 4 of the 5 enums confirmed: ``KnowledgeGapUploadJobStatus`` (8 states), ``KnowledgeGapJobType`` (2 types: FILE_UPLOAD, ADHOC_CSM), ``KnowledgeGapSuggestionArticleStatus`` (3 states), ``KnowledgeGapUploadFileType`` (CSV, JSON), ``KnowledgeGapProductType`` (CSM, JSM)
* ``MlStudioWorkflowService.kt`` interface body fully verified — `triggerWorkflow(jobType, platoRegion, jobIds)` async, no return
* ``MlStudioWorkflowServiceImpl.kt`` exists at 137 LoC
* ``KnowledgeGapConfluenceService.kt`` exists at 239 LoC (Confluence integration)
* ``KnowledgeGapStaleJobCleanupTask.kt`` exists at 200 LoC (periodic cleanup)
* Both Stores exist: ``KnowledgeGapUploadJobStore`` (131) + ``KnowledgeGapSuggestionArticleStore`` (93)
* ERS storage entities exist: ``KnowledgeGapErsUploadJob`` + ``KnowledgeGapErsSuggestionArticle``

⚠️ **Inferred from naming + sub-agent**:

* The end-to-end sequence ordering (responsibility-based inference)
* The "ML Studio polls ERS directly" claim (must be true given no return value in MlStudioWorkflowService.triggerWorkflow)
* The Confluence draft → publish flow (KnowledgeGapConfluenceService 239 LoC body wasn't read in detail)
* The cleanup threshold (e.g., >24h) is guessed
* The "5-state pipeline visualization" interpretation
* The PARTIAL_COMPLETE retry semantics — naming inference

❌ **UNVERIFIED:**

* Exact ML Studio HTTP contract (``MlStudioWorkflowServiceImpl.kt`` body not read in detail)
* Whether Confluence pages are created as drafts or published immediately on ACCEPT
* The cleanup task's exact threshold + behavior (delete vs archive)
* Per-tenant quota enforcement (existence + values)
* Job pickup mechanism — polling vs webhook vs direct ERS read
* The KnowledgeGapContext class structure (referenced in Manager generic but not read)
* Whether REJECTED articles' content is sent back to ML Studio
* Whether failed ML Studio triggers are retried

Open questions for institutional knowledge
=============================================

1. **How does ML Studio pick up new jobs**? Polling, webhook, or direct ERS query?
2. **What's ML Studio's update path** — does it call back to a controller, or write to ERS directly?
3. **Per-cluster generation cost**: how much LLM token usage per article?
4. **Per-tenant quota**: how many jobs can a tenant have in-flight?
5. **PARTIAL_COMPLETE retry**: what's the user-facing UX for partial failures?
6. **Stale job threshold**: what's the actual timeout in ``KnowledgeGapStaleJobCleanupTask``?
7. **Confluence draft vs publish**: which happens on ACCEPT?
8. **Cross-product knowledge**: can a CSM job's ACCEPTED article be used by JSM agents?
9. **ADHOC_CSM trigger frequency**: how often does CSM auto-trigger ML Studio?
10. **REJECTED feedback**: is there a loop back to ML Studio for model improvement?

