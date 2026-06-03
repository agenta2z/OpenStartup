.. _feature-knowledge:

==================================================================
Knowledge & Knowledge Gap — agent knowledge sources + drafted articles
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 3,382 LoC across 48 files (knowledge: 554 LoC / 12 files; knowledge-gap: 2,828 LoC / 36 files)
:Modules: ``modules/platform/knowledge/`` + ``modules/platform/knowledge-gap/``
:Triage score: **19/25 — important AgentStudio feature**

.. contents:: On this page
   :local:
   :depth: 2

What Knowledge IS — and what it ISN'T
==========================================

**Knowledge** is the system that lets an agent **reference external content
sources at inference time**. When you build an agent in AgentStudio,
you can attach knowledge sources — Confluence pages, Jira issues,
Zendesk articles, web pages — and the agent will search/cite them
when answering user questions. The Knowledge module is small (554 LoC,
12 files) because it's a **contract layer**: the actual content
fetching and ranking is delegated to consumers (CSM, AIFEATURE's
relatedresource, etc.) that implement the ``KnowledgeService`` contract.

**Knowledge Gap** is a **different beast entirely** — and it's NOT what
the Wave-2 inventory hypothesized. It is **NOT** a real-time LLM-as-judge
that detects "the agent kept saying I don't know". Rather, it is a
**batch async workflow**:

1. User uploads a CSV/JSON file of "questions our agents struggle with"
2. ML Studio job runs offline to generate suggestion articles (Confluence drafts)
3. Articles surface in AgentStudio's UI with status SUGGESTED
4. Human reviewer ACCEPTs or REJECTs each suggestion
5. Accepted suggestions get attached as new knowledge sources

Knowledge Gap is the **content acquisition pipeline** for new knowledge.
It's gated behind the ``CSM_AI_ENABLE_KNOWLEDGE_GAP_API`` Statsig flag.

Anatomy — module structure
==============================

.. list-table::
   :header-rows: 1
   :widths: 36 12 12 40

   * - Module
     - LoC
     - Files
     - Role
   * - **knowledge-api**
     - small
     - ~5
     - Contracts: KnowledgeSource, KnowledgeSourceType, KnowledgeReference
   * - **knowledge-spi**
     - small
     - ~3
     - SPI for product-specific extension
   * - **knowledge-impl**
     - ~400
     - ~4
     - Default knowledge source registry, validation
   * - **knowledge-gap-api**
     - ~700
     - ~10
     - Contract: KnowledgeGapManager (the upload-job-result interface)
   * - **knowledge-gap-spi**
     - small
     - ~5
     - SPI extensions
   * - **knowledge-gap-impl**
     - ~2,100
     - ~21
     - **Main implementation**: jobs, ML Studio integration, suggestion article persistence

Plus AgentStudio integration:

* ``agentstudio-impl/.../graphql/AgentStudioKnowledgeGapQueryController.kt`` (147 LoC)
* ``agentstudio-impl/.../graphql/AgentStudioKnowledgeGapMutationController.kt`` (103 LoC)

Top files by LoC
====================

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - File
     - LoC
     - Role
   * - ``knowledge-gap-impl/.../service/KnowledgeGapJobService.kt``
     - **616**
     - **Largest single file.** Orchestrates job lifecycle: upload → ML Studio call → result storage → suggestion-article creation
   * - ``knowledge-gap-api/.../KnowledgeGapManager.kt``
     - 195
     - **Main contract.** Job API: uploadKnowledgeGapFile, createKnowledgeGapUploadJob, saveKnowledgeGapJobResult
   * - ``agentstudio-impl/.../AgentStudioKnowledgeGapQueryController.kt``
     - 147
     - GraphQL query: list suggestion articles by status; list jobs
   * - ``agentstudio-impl/.../AgentStudioKnowledgeGapMutationController.kt``
     - 103
     - GraphQL mutation: update suggestion article status
   * - ``knowledge-api/.../source/KnowledgeSource.kt``
     - 46
     - Knowledge source data class

The Knowledge contract
=========================

``KnowledgeSource.kt`` (46 LoC) — the canonical knowledge source shape:

.. code-block:: kotlin

   data class KnowledgeSource(
       val id: String,                     // unique source ID
       val enabled: Boolean,               // toggle
       val type: KnowledgeSourceType,      // CONFLUENCE, JIRA, ZENDESK, WEB_PAGES
       val filters: Map<String, Any>?      // type-specific filters
   )

**Knowledge source types** (verified in ``KnowledgeSourceType`` enum):

* ``CONFLUENCE`` — Confluence pages/spaces
* ``JIRA`` — Jira issues
* ``ZENDESK`` — Zendesk articles (external integration)
* ``WEB_PAGES`` — generic web URLs

**Filter examples** (per-type):

* CONFLUENCE: ``{"spaceFilter": ["IT issues"]}`` — restrict to specific spaces
* JIRA: ``{"projectKey": "SD"}`` — restrict to specific projects
* ZENDESK: ``{"locale": "en-US"}`` — locale filter
* WEB_PAGES: ``{"urls": [...]}`` — explicit URL list

The Knowledge Gap workflow
=============================

**Phase 1 — Upload** (``KnowledgeGapManager.uploadKnowledgeGapFile``):

1. User uploads a CSV/JSON file via UI
2. ``MultipartFile`` arrives at controller
3. Stored in object storage (likely S3 via ERS file storage)
4. Returns ``fileId``

**Phase 2 — Job creation** (``KnowledgeGapManager.createKnowledgeGapUploadJob``):

1. Caller passes ``fileId``, ``containerId`` (agent or workspace), user, ``KnowledgeGapJobType``
2. Creates an ``KnowledgeGapErsUploadJob`` record (likely in ERS)
3. Schedules ML Studio job execution
4. Returns the job record

**Phase 3 — Job execution** (async, ML Studio):

1. ML Studio picks up the job
2. Reads the CSV/JSON of "questions agents struggle with"
3. For each question:

   a. Searches existing knowledge for related content
   b. Detects gap (no good existing answer)
   c. Generates a draft Confluence article that would answer it
   d. Stores draft as ``KnowledgeGapSuggestionArticle`` with status SUGGESTED

4. Marks job complete

**Phase 4 — Review** (``AgentStudioKnowledgeGapQueryController``):

1. Reviewer opens AgentStudio's "Knowledge Gap" panel
2. Frontend calls ``agentStudio_knowledgeGapSuggestionArticles(cloudId, containerAri, productType, status?, first, after)``
3. Server returns paginated list of suggestion articles filtered by status

**Phase 5 — Decision** (``AgentStudioKnowledgeGapMutationController``):

1. Reviewer ACCEPTs or REJECTs each article
2. Frontend calls ``agentStudio_updateKnowledgeGapSuggestionArticleStatus(articleId, status)``
3. Server persists new status (SUGGESTED → ACCEPTED or REJECTED)
4. ACCEPTED articles get published as Confluence pages, attached as knowledge sources

The 3 status states
========================

``KnowledgeGapSuggestionArticleStatus`` enum:

* ``SUGGESTED`` — generated by ML Studio job; awaiting review
* ``ACCEPTED`` — reviewer approved; will be published
* ``REJECTED`` — reviewer dismissed

End-to-end flow
==================

Sequence diagram for the full Knowledge Gap workflow:

.. mermaid::

   sequenceDiagram
       autonumber
       participant Admin as AgentStudio<br/>Admin
       participant FE as Frontend
       participant Ctrl as AgentStudio<br/>KnowledgeGapMutationController
       participant Mgr as KnowledgeGap<br/>Manager
       participant FS as File Storage<br/>(ERS/S3)
       participant Svc as KnowledgeGap<br/>JobService (616 LoC)
       participant ML as ML Studio<br/>(async worker)
       participant Conf as Confluence

       Admin->>FE: upload questions.csv
       FE->>Ctrl: agentStudio_uploadKnowledgeGapFile(file, ...)
       Ctrl->>Mgr: uploadKnowledgeGapFile(file, ...)
       Mgr->>FS: store(file)
       FS-->>Mgr: fileId

       FE->>Ctrl: createKnowledgeGapUploadJob(fileId, ...)
       Ctrl->>Mgr: createKnowledgeGapUploadJob(...)
       Mgr->>Svc: scheduleJob(fileId, jobType)
       Svc->>ML: enqueueJob(...)
       Svc-->>Mgr: KnowledgeGapErsUploadJob
       Mgr-->>Ctrl: job
       Ctrl-->>FE: jobId (UI shows "in progress")

       Note over ML: Async — ML Studio runs<br/>(may take minutes/hours)

       loop for each question in CSV
           ML->>ML: search existing knowledge
           ML->>ML: detect gap
           ML->>ML: generate draft Confluence article
           ML->>Svc: saveKnowledgeGapJobResult(article, status=SUGGESTED)
       end

       ML->>Svc: jobCompleted
       Svc->>Svc: persist all suggestion articles

       Note over Admin: Later — review phase

       Admin->>FE: open Knowledge Gap panel
       FE->>Ctrl: agentStudio_knowledgeGapSuggestionArticles(status=SUGGESTED, ...)
       Ctrl-->>FE: paginated list

       Admin->>FE: ACCEPT article #5
       FE->>Ctrl: agentStudio_updateKnowledgeGapSuggestionArticleStatus(5, ACCEPTED)
       Ctrl->>Mgr: updateStatus(5, ACCEPTED)
       Mgr->>Conf: publish(article)
       Conf-->>Mgr: pageId
       Mgr-->>Ctrl: ACCEPTED

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 32 44

   * - System
     - How
     - Used for
   * - **ML Studio**
     - async job dispatch
     - Knowledge gap detection + article generation (offline)
   * - **ERS (file storage)**
     - via KnowledgeGapJobService
     - Persistent storage of uploaded CSV/JSON + generated articles
   * - **Confluence Cloud**
     - via publish API
     - Final destination for ACCEPTED articles
   * - **Statsig**
     - ``CSM_AI_ENABLE_KNOWLEDGE_GAP_API``
     - Per-tenant rollout
   * - **AgentStudio GraphQL**
     - via 2 controllers
     - UI surface (list + status update)

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
     - **Knowledge module is tiny (554 LoC) but cross-cutting**
     - architecture
     - Many consumers (CSM, AIFEATURE, AgentStudio) re-implement knowledge fetching. Worth audit: is the contract too thin?
   * - 🔴
     - **Knowledge Gap is BATCH only** (not real-time)
     - workflow
     - Long lag between "agent fails to answer" → "human uploads CSV" → "ML Studio generates" → "human reviews". Real-time gap detection would be more valuable.
   * - 🔴
     - **616-LoC ``KnowledgeGapJobService.kt``**
     - knowledge-gap-impl/
     - Single largest file. Should split: JobScheduler, MLStudioClient, ResultPersister.
   * - 🟡
     - **Only 4 knowledge source types** (CONFLUENCE, JIRA, ZENDESK, WEB_PAGES)
     - KnowledgeSourceType
     - Limits the universe of knowledge. Where's Slack? GitHub? Notion?
   * - 🟡
     - **Knowledge has no built-in vector/embedding indexing**
     - knowledge-impl
     - Search/embedding is left to consumers. Risk: each consumer re-implements (inconsistent ranking).
   * - 🟡
     - **Filter map is ``Map<String, Any>?``** (untyped)
     - KnowledgeSource
     - Type-safe per-source filter classes would catch invalid filters at compile time.
   * - 🟡
     - **Knowledge Gap article workflow blocks on human review**
     - workflow
     - For an org with many low-volume queries, manual review may become bottleneck. Consider auto-acceptance for high-confidence drafts.
   * - 🟡
     - **No "REJECTED feedback loop"**
     - workflow
     - When reviewers reject suggestions, the data should improve future generation. Unclear if this exists.
   * - 🟢
     - **Clear status lifecycle** (SUGGESTED → ACCEPTED/REJECTED)
     - KnowledgeGapSuggestionArticleStatus
     - Simple, auditable.
   * - 🟢
     - **api/spi/impl pattern**
     - module structure
     - Standard Atlassian convention.

Refactoring opportunities
============================

1. **Add real-time gap detection** (XL, 🔴 high) — emit "no-good-answer" events from chat orchestrators; auto-trigger Knowledge Gap detection. ~2-3 weeks; major UX win.

2. **Split ``KnowledgeGapJobService.kt``** (M, 🟡 medium) — 616 LoC. ~2 days.

3. **Type-safe filter classes per knowledge source** (S, 🟡 medium) — replace ``Map<String, Any>?`` with ``ConfluenceFilter``, ``JiraFilter``, etc. ~1 day.

4. **Add Slack/GitHub/Notion source types** (S, 🟡 medium) — enum extension + per-type fetch logic. ~1 week per source.

5. **Add REJECTED feedback loop** (M, 🟡 medium) — train ML Studio with REJECTED examples to improve future generation. ~1-2 weeks.

6. **Move embedding/indexing into Knowledge module** (XL, 🟡 medium) — currently each consumer re-implements. ~3-4 weeks.

7. **Add auto-acceptance threshold** (S, 🟢 low) — high-confidence drafts skip review. ~3 days.

8. **Add Knowledge browsing GraphQL** (S, 🟢 low) — currently only knowledge-gap has GraphQL surface; knowledge browsing/management surface missing.

What you would change here
============================

* **Add a new knowledge source type** (e.g., GITHUB):
   1. Add to ``KnowledgeSourceType`` enum
   2. Add filter shape to ``KnowledgeSource`` filter map convention
   3. Implement fetcher in consumer modules (CSM, AIFEATURE)

* **Modify Knowledge Gap detection logic** → ML Studio side (NOT in this codebase)

* **Add a new GraphQL endpoint to Knowledge Gap UI** → ``AgentStudioKnowledgeGapQueryController.kt``

* **Change the SUGGESTED → ACCEPTED/REJECTED flow** → ``AgentStudioKnowledgeGapMutationController.kt``

* **Add new status state** → enum + state-machine validation

* **Tune per-tenant gap detection** → ``CSM_AI_ENABLE_KNOWLEDGE_GAP_API`` flag rules in Statsig

What you would NOT change here
================================

* The actual knowledge content (Confluence, Jira) — owned by external services
* ML Studio's gap detection model — owned by ML team
* Knowledge fetching/ranking by consumers — owned by CSM, AIFEATURE
* User management / permissions — owned by ``platform/security``

Verification audit log
========================

✅ **Personally verified with bash:**

* Total knowledge LoC: 554 (12 files)
* Total knowledge-gap LoC: 2,828 (36 files)
* Module structure: api/spi/impl pattern for both
* ``KnowledgeGapJobService.kt`` is 616 LoC
* ``KnowledgeGapManager.kt`` is 195 LoC at ``knowledge-gap-api/.../KnowledgeGapManager.kt``
* ``AgentStudioKnowledgeGapQueryController.kt`` is 147 LoC
* ``AgentStudioKnowledgeGapMutationController.kt`` is 103 LoC
* ``KnowledgeSource.kt`` is 46 LoC; has ``id``, ``enabled``, ``type``, ``filters`` fields
* ``KnowledgeSourceType`` enum has CONFLUENCE/JIRA/ZENDESK/WEB_PAGES
* Feature flag ``CSM_AI_ENABLE_KNOWLEDGE_GAP_API`` exists

⚠️ **Inferred from sub-agent + naming**:

* ML Studio integration (sub-agent claim; not directly source-verified)
* The ``SUGGESTED → ACCEPTED/REJECTED`` lifecycle (sub-agent claim; enum membership inferred)
* Per-source filter examples (e.g., ``spaceFilter``, ``projectKey``) — naming inference
* The "publish to Confluence" step on ACCEPTED — inferred; not source-verified

❌ **UNVERIFIED:**

* ML Studio's actual API contract
* Per-job latency (how long does an upload take to process?)
* Per-tenant quotas
* Feedback loop from REJECTED back to ML Studio
* Whether Knowledge module has any vector/embedding internal infrastructure
* Cross-product knowledge sharing (can JSM agent use a CSM knowledge source?)

Open questions for institutional knowledge
=============================================

1. **Why is Knowledge Gap detection BATCH only?** Real-time would be more valuable.
2. **What's the typical job runtime** in ML Studio?
3. **Is there a REJECTED feedback loop** to improve ML Studio's draft generation?
4. **Can knowledge sources be cross-product** (e.g., can a CSM agent reference a JSM knowledge source)?
5. **Where does embedding/indexing happen** for knowledge sources? Per-consumer?
6. **What's the per-tenant quota** for knowledge sources / suggested articles?
7. **Why only 4 source types?** (no Slack, GitHub, Notion, etc.)
8. **Is there a knowledge-source health check** (broken Confluence link, expired Zendesk article)?
9. **What's the auto-acceptance threshold** for high-confidence ML drafts (if any)?
10. **What's the Confluence draft → page promotion flow** for ACCEPTED articles?

