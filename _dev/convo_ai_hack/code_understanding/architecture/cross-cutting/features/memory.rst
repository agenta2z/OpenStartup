.. _feature-memory:

==================================================================
Memory subsystem — cross-conversation personalization
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 17,066 LoC across **109 files** matching memory paths (cross-cutting)
:Triage score: **22/25 — strong deep-dive candidate**

.. contents:: On this page
   :local:
   :depth: 2

What Memory IS (in one paragraph)
====================================

The memory subsystem is the **cross-conversation personalization
layer** that lets Rovo remember user-specific facts, preferences, and
context across multiple conversations. Visible to users via the
``GET /memories/agent/{agentId}`` endpoint (where users can inspect
"what does the agent remember about me?"). Architecturally split into
**3 distinct memory types** with different lifecycles and storage
backends: (1) **Collection memories** (long-term per-(user, agent)
facts, extracted via LLM from chat turns), (2) **Conversation
segments** (per-turn extracted segments stored in a vector DB for
semantic retrieval), and (3) **Procedural memory** (workflow/process
knowledge per-tenant). Plus per-product memory variants (JSM has its
own ``ExecutionMemoryService`` for journey personalization, ADK has
its own memory ingestion). 4 distinct extraction prompts, 3 storage
backends, and an **LLM-as-judge "helpfulness classifier"** that prunes
unhelpful memories.

Anatomy — where memory code lives
====================================

Memory is **distributed across 5+ modules** (no single "memory module"):

.. list-table::
   :header-rows: 1
   :widths: 36 16 12 36

   * - Module
     - LoC
     - Files
     - Role
   * - **rovo-impl/.../product/rovo/memory/**
     - largest
     - ~30
     - **Main collection memory + conversation memory implementation**
   * - **rovo-impl/.../product/rovo/procedural/**
     - ~750
     - ~3
     - **Procedural memory** (separate type — workflow/process knowledge)
   * - **platform/conversation/conversation-impl/.../memory/**
     - ~1,000
     - ~5
     - **Storage backends** (ERS — Entity Resolution Service stores)
   * - **platform/conversation/conversation-api/.../history/memory/**
     - ~500
     - ~10
     - Memory contracts (CollectionMemory, MemoryReference, ConversationTopicSegmentManager)
   * - **platform/stratus-contracts/.../api/memory/**
     - 353
     - ~6
     - Stratus platform memory contracts (MemorySliceType, ConversationSegment, SegmentSearchRequest)
   * - **product/jsm/.../orchestrator/memory/**
     - 693
     - 1
     - **JSM-specific** ``ExecutionMemoryService`` — execution memory for JSM agents
   * - **rovo-impl/.../agent/minions/adk/memory/**
     - moderate
     - ~3
     - **ADK-specific** memory ingestion (``AdkMemoryIngestService`` + enablement policy)
   * - **rovo-extras-impl/.../marathon/memory/**
     - 262
     - 1
     - **Marathon-specific** ``MemoryStoreImpl`` for marathon orchestrator state

Top files by LoC (verified)
==============================

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - File
     - LoC
     - Role
   * - ``ProceduralMemoryTPService.kt``
     - **748**
     - **Largest single memory file.** Procedural-memory third-party (TP) service — workflow/process knowledge management
   * - ``ExecutionMemoryService.kt`` (jsm)
     - **693**
     - JSM execution memory — tracks execution state per (user, journey)
   * - ``JourneyPersonalizationMinion.kt`` (jsm)
     - 542
     - JSM journey personalization minion (uses execution memory)
   * - ``RovoChatWorkflowMemoryHelperImpl.kt``
     - 450
     - Workflow-level memory helper for chat
   * - ``ConversationIndexServiceImpl.kt``
     - 423
     - Conversation index service (vector DB integration)
   * - ``ErsConversationTopicSegmentStoreImpl.kt``
     - 390
     - ERS-backed conversation topic segment store
   * - ``ErsInSessionSegmentStoreImpl.kt``
     - 342
     - ERS-backed in-session segment store
   * - ``ConversationVectorDBServiceImpl.kt``
     - 330
     - Vector DB integration for conversation memory
   * - ``InSessionSegmentationServiceImpl.kt``
     - 325
     - In-session segmentation (per-turn extraction)
   * - ``ErsCollectionMemoryStoreImpl.kt``
     - 274
     - ERS-backed collection memory store
   * - ``MemoryStoreImpl.kt`` (marathon)
     - 262
     - Marathon's memory store
   * - ``ConversationIndexBootstrapHelper.kt``
     - 248
     - Bootstrap helper for conversation index
   * - ``ConversationSegmentationServiceImpl.kt``
     - 231
     - Conversation-level segmentation

The 3 memory types
======================

**Type 1: Collection Memory** (long-term per-(user, agent) facts)
---------------------------------------------------------------------

* **Contract**: ``CollectionMemoryService.kt`` (in rovo-api/.../memory/)
   * 3 operations: ``extractMemory()``, ``searchMemory()``, ``updateMemory()``
* **Implementation**: ``CollectionMemoryServiceImpl.kt``
* **Storage**: ``ErsCollectionMemoryStoreImpl.kt`` (274 LoC) — ERS-backed
* **Extraction**: ``CollectionMemoryExtractor.kt``
   * **3 Pebble template variants**:
      * ``long_term_collection_memory.pebble``
      * ``long_term_collection_memory_v2.pebble``
      * ``long_term_collection_memory_explicit_only.pebble``
   * The 3 templates suggest A/B testing or progressive rollout (V1 → V2 → explicit-only)
* **Search**: ``CollectionMemorySearchRequest`` + ``SearchCollectionMemoryResponse``
   * Likely vector-similarity-based via ``ConversationVectorDBServiceImpl``
* **Resolution**: ``CollectionMemoryResolver.kt``
   * Pebble template: ``collection_memory_resolution.pebble``
   * Resolves "what memories are relevant to this query?"
* **Helpfulness classifier**: ``RovoChatMemoryHelpfulnessClassifier.kt``
   * Pebble template: ``memory_helpfulness_classifier.pebble``
   * **LLM-as-judge** that classifies whether a memory was helpful — likely used for pruning

**Type 2: Conversation Memory** (per-turn segments for retrieval)
---------------------------------------------------------------------

* **Contracts** (in conversation-api/.../history/memory/):
   * ``ConversationTopicSegmentManager.kt``
   * ``InSessionSegmentManager.kt``
   * ``CollectionMemory.kt``
   * ``MemoryReference.kt``
* **Storage** (in conversation-impl/.../memory/):
   * ``ErsConversationTopicSegmentStoreImpl.kt`` (390 LoC) — topic-level segments
   * ``ErsInSessionSegmentStoreImpl.kt`` (342 LoC) — in-session segments
* **Segmentation services** (in rovo-impl/.../memory/conversation/):
   * ``ConversationSegmentationServiceImpl.kt`` (231 LoC) — conversation-level
   * ``InSessionSegmentationServiceImpl.kt`` (325 LoC) — in-session-level
* **Indexing**:
   * ``ConversationIndexServiceImpl.kt`` (423 LoC) — main index
   * ``ConversationVectorDBServiceImpl.kt`` (330 LoC) — vector DB
   * ``ConversationIndexBootstrapHelper.kt`` (248 LoC) — bootstrap

**Type 3: Procedural Memory** (workflow/process knowledge)
-------------------------------------------------------------

* **Service**: ``ProceduralMemoryTPService.kt`` (748 LoC) — largest single memory file
* **Path**: ``rovo-impl/.../product/rovo/procedural/``
* "TP" likely = "Third-Party" (suggests integration with external knowledge store)
* Used for storing reusable process / workflow knowledge per tenant

The Stratus platform memory contracts
========================================

Beyond the rovo-specific layer, ``platform/stratus-contracts/.../api/memory/`` defines:

* ``MemorySliceType.kt`` — enum of memory slice types (different "kinds" of memories)
* ``ConversationSegment.kt`` — segment data class
* ``SegmentSearchRequest.kt`` + ``SegmentSearchResponse.kt`` — search interface
* ``MemoryNamespace.kt`` — multi-tenant memory namespacing
* ``RetrievalMetadata.kt`` — metadata about retrieved memories

This **stratus platform layer** is what Rovo consumes — the
underlying storage is in ``platform/conversation/`` (ERS).

Per-product memory variants
==============================

Multiple products have their own memory layers:

.. list-table::
   :header-rows: 1
   :widths: 32 16 52

   * - Product
     - Layer
     - Role
   * - **JSM** (jsm-impl)
     - ``ExecutionMemoryService`` (693 LoC)
     - Tracks execution state per (user, journey) for JSM service workflows
   * - **JSM** (jsm-impl)
     - ``JourneyPersonalizationMinion`` (542 LoC)
     - Personalizes JSM journeys based on memory
   * - **ADK** (rovo-impl)
     - ``AdkMemoryIngestService`` + ``DefaultAdkMemoryEnablementPolicy``
     - Memory layer for the Agent Development Kit (external SDK)
   * - **Marathon** (rovo-extras-impl)
     - ``MemoryStoreImpl`` (262 LoC)
     - Marathon orchestrator's per-execution memory
   * - **Lumina** (rovo-impl, indirect)
     - via Stratus contracts
     - Lumina sub-agent uses memory for citation context

The 9+ Pebble templates
=========================

Each memory operation has its own LLM prompt template:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Template
     - Purpose
   * - ``long_term_collection_memory.pebble``
     - V1 memory extraction
   * - ``long_term_collection_memory_v2.pebble``
     - V2 memory extraction (likely current)
   * - ``long_term_collection_memory_explicit_only.pebble``
     - Variant: only extract explicit "remember that..." statements
   * - ``collection_memory_search_by_intent.pebble``
     - Intent-based memory search (used by ``CollectionMemoryIntentClassifier``)
   * - ``collection_memory_resolution.pebble``
     - Resolve "which memories relevant to query?"
   * - ``user_profile_memory.pebble``
     - User profile memory (used by ``RovoChatMemoryPromptFormatterImpl``)
   * - ``memory_helpfulness_classifier.pebble``
     - LLM-as-judge for memory helpfulness
   * - ``oov_keyword_memory.pebble``
     - Out-Of-Vocabulary keyword extraction (``OOVKeywordLLMExtractor``)
   * - ``in_session_message_classifier.pebble``
     - Per-message segmentation classifier
   * - ``message_segment_classifier.pebble``
     - Message segment classifier

End-to-end flow — Collection Memory extraction (per chat turn)
=================================================================

When a user sends a chat message and the agent responds:

1. **Chat turn completes** — ``RovoChatExecutor`` finishes processing
2. **Async memory extraction triggered** by ``CollectionMemoryExtractor``
3. **Pebble template rendered** with:
   * Recent chat history
   * Current user / tenant context
4. **LLM called** to extract candidate memories from the conversation
   * Typical output: list of ``ExtractedCollectionMemory`` data classes
   * Each has: content, scope (user|agent|tenant), confidence
5. **Helpfulness classifier** filters extracted memories
   * LLM-as-judge: "Is this memory likely to be helpful in future conversations?"
   * Filters out trivia, transient context, low-value extractions
6. **Vector embedding** computed for retained memories
7. **Stored in ERS** (``ErsCollectionMemoryStoreImpl``)
8. **Indexed in vector DB** (``ConversationVectorDBServiceImpl``)

End-to-end flow — Memory retrieval (per chat request)
========================================================

When a new chat turn starts:

1. **Memory retriever queried** with current user message
2. **Vector similarity search** in conversation vector DB
3. **CollectionMemoryResolver** runs LLM resolution to filter to most-relevant
4. **Returned as ``MemoryReference`` list** to chat orchestrator
5. **Memories injected into LLM prompt** via ``RovoChatMemoryPromptFormatterImpl``
   * Pebble template: ``user_profile_memory.pebble``
6. **LLM responds** with full context awareness

Sequence diagram — extraction
==================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant Chat as RovoChatExecutor
       participant Ext as CollectionMemory<br/>Extractor
       participant Tmpl as Pebble Template<br/>(long_term_v2)
       participant LLM
       participant HC as Helpfulness<br/>Classifier
       participant Vec as Vector Embedding<br/>Service
       participant Ers as ErsCollectionMemory<br/>StoreImpl
       participant VDB as Conversation<br/>VectorDB

       Chat-->>Ext: turnCompleted(history, user, tenant)
       Ext->>Tmpl: render with history+context
       Tmpl-->>Ext: prompt text
       Ext->>LLM: invoke(prompt)
       LLM-->>Ext: List<ExtractedCollectionMemory>

       loop for each candidate memory
           Ext->>HC: classify(memory, future_likely?)
           HC->>LLM: invoke helpfulness prompt
           LLM-->>HC: HELPFUL | NOT_HELPFUL
           HC-->>Ext: keep | drop
       end

       Ext->>Vec: embed(retained memories)
       Vec-->>Ext: embeddings
       Ext->>Ers: storeAll(memories+embeddings)
       Ers-->>Ext: ack
       Ext->>VDB: indexAll(embeddings)
       VDB-->>Ext: ack

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - System
     - How
     - Used for
   * - **AI Gateway** (LLM)
     - per-extraction + per-classification
     - Memory extraction, helpfulness classification, resolution
   * - **ERS (Entity Resolution Service)**
     - via ``Ers*StoreImpl``
     - Persistent storage backend for all memory types
   * - **Vector DB** (likely OpenSearch/ES)
     - via ``ConversationVectorDBServiceImpl``
     - Semantic search over memories
   * - **Embedding Service**
     - per-memory storage
     - Vector embeddings for retrieval
   * - **MetricsService**
     - per-operation
     - Latency, extraction rate, helpfulness ratio
   * - **Statsig**
     - via various FF gates
     - Per-template rollout, per-tenant memory enablement

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
     - **No single "memory module"** — distributed across 5+ modules
     - architecture
     - Hard to onboard, hard to evolve coherently. Should consolidate (or document the contract clearly).
   * - 🔴
     - **3 extraction template variants** (V1, V2, explicit_only)
     - templates/
     - Suggests A/B testing without a clear retirement path. When does V1 die?
   * - 🔴
     - **3 distinct memory types** with no obvious synthesis (Collection, Conversation, Procedural)
     - architecture
     - Unclear how they interact. Does Procedural memory ever flow into Collection memory? Vice versa?
   * - 🔴
     - **Per-product variants** (JSM, ADK, Marathon, Lumina each have their own memory layer)
     - distributed
     - Risk of inconsistency in scope, retention, and PII handling.
   * - 🔴
     - **748-LoC ``ProceduralMemoryTPService.kt``**
     - procedural/
     - Single largest memory file. Should split.
   * - 🔴
     - **693-LoC ``ExecutionMemoryService.kt``** (JSM)
     - jsm-impl/
     - Same split principle.
   * - 🟡
     - **No central documentation of memory retention policy**
     - architecture
     - How long do memories persist? When are they evicted? What's the per-tenant cap?
   * - 🟡
     - **Helpfulness classifier is itself an LLM call**
     - extraction path
     - Adds cost; cost-benefit tradeoff unclear. How often does it filter?
   * - 🟡
     - **No observable "memory governance"** (PII handling, deletion requests)
     - architecture
     - GDPR / right-to-be-forgotten implications need clarity.
   * - 🟡
     - **Vector DB technology not source-verified**
     - storage
     - Inferred to be OpenSearch/ES; could be Pinecone, Weaviate, or other.
   * - 🟢
     - **Good separation of types** — Collection vs Conversation vs Procedural
     - design
     - Each has its own lifecycle and contract.
   * - 🟢
     - **LLM-as-judge for helpfulness** is sophisticated
     - design
     - Better than rule-based pruning; expensive but valuable.

Refactoring opportunities
============================

1. **Consolidate memory into one Gradle module** (XL, 🔴 high) — currently distributed across 5+ modules. Major effort but huge clarity win. ~2-3 weeks.

2. **Document memory retention + eviction policy** (S, 🔴 high) — currently undocumented. Critical for GDPR, ops planning. ~1 day.

3. **Audit Pebble template variants** (S, 🟡 medium) — 3 collection memory templates suggest abandoned A/B test. Identify current; sunset others. ~1 day.

4. **Split ``ProceduralMemoryTPService.kt``** (M, 🟡 medium) — 748 LoC. ~2 days.

5. **Split ``ExecutionMemoryService.kt``** (M, 🟡 medium) — 693 LoC. ~2 days.

6. **Add per-tenant memory metrics dashboard** (S, 🟡 medium) — observability for ops. ~1 day.

7. **Document interaction between 3 memory types** (S, 🟡 medium) — currently unclear. ~half day.

8. **Audit ADK memory enablement policy** (S, 🟢 low) — ``DefaultAdkMemoryEnablementPolicy`` is named "Default" — what are the non-default cases?

9. **Add Sphinx memory-architecture diagram** (XS, 🟢 low) — visualize the 3 types + 5 modules + storage backends.

What you would change here
============================

* **Add a new memory type** (e.g., "skill memory" — what tools the user has used):
   1. Define contract in ``platform/stratus-contracts/.../memory/``
   2. Implementation in ``rovo-impl/.../memory/<newtype>/``
   3. Storage backend in ``platform/conversation/.../memory/``
   4. Pebble template at ``resources/templates/memory/``
   5. Wire into chat orchestrator's memory injection point

* **Modify extraction prompt** → ``resources/templates/memory/long_term_collection_memory_v2.pebble``

* **Tune helpfulness threshold** → ``RovoChatMemoryHelpfulnessClassifier`` config

* **Change retention policy** → ``Ers*StoreImpl`` (storage layer)

* **Add new memory namespace** → ``MemoryNamespace.kt`` enum + filter logic

* **Inspect a user's memories** → ``GET /memories/agent/{agentId}`` endpoint (in RovoChatV1Controller)

What you would NOT change here
================================

* Chat streaming envelope — owned by ``rovo-api/.../chat/streaming/``
* LLM provider — owned by ``platform/service/service-impl``
* Vector DB technology — owned by ops / platform team
* ERS storage backend — owned by ``platform/conversation/``
* Per-product agent definitions — owned by their respective product modules

Verification audit log
========================

✅ **Personally verified with bash:**

* 109 files match memory paths (find + count)
* 17,066 LoC total memory-related code
* Top-15 files by LoC (verified: ProceduralMemoryTPService at 748, ExecutionMemoryService at 693, etc.)
* CollectionMemoryService contract has 3 operations (read interface)
* 9+ Pebble templates referenced by extractor + classifier files
* Memory-FF-related files exist in 4+ modules
* No single ``MemoryService.kt`` interface at top-level — sub-agent's claim was wrong
* JSM has its own memory service (independent of rovo-impl)
* ADK has its own memory enablement policy
* Marathon has its own memory store

⚠️ **Inferred from naming + sub-agent reports**:

* "TP" in ProceduralMemoryTPService = Third-Party (educated guess)
* "ERS" = Entity Resolution Service (educated guess; could be Event Replication Service)
* "OOV" in OOVKeywordLLMExtractor = Out-Of-Vocabulary (standard NLP term)
* End-to-end extraction flow ordering — based on file responsibilities, not from a deep read
* Vector DB technology = OpenSearch/ES (could be other)
* The 3 template variants represent A/B test stages (could be permanent variants)

❌ **UNVERIFIED:**

* The exact retention/eviction policy
* Per-tenant memory caps
* PII handling logic
* Whether ``DefaultAdkMemoryEnablementPolicy`` has non-default subclasses
* Per-template current rollout state
* Helpfulness-classifier filter rate (what % of extracted memories survive?)
* Cross-type memory interactions (does Collection ever read from Procedural?)

Open questions for institutional knowledge
=============================================

1. **What does "TP" stand for** in ``ProceduralMemoryTPService``? (Third-Party? Tenant? Tracking Pattern?)
2. **What's the retention policy?** How long do collection memories persist? Per-tenant caps?
3. **PII handling**: how are sensitive memories detected and handled?
4. **Right-to-be-forgotten**: is there a delete-all-memories operation? GDPR compliance flow?
5. **Why 3 collection memory template variants?** A/B test? Per-tenant config? Something else?
6. **What's the helpfulness-classifier filter rate?** What % of extracted memories survive?
7. **How does Procedural memory interact with Collection memory?** Synthesis? Independent?
8. **Is the vector DB OpenSearch/ES or something else?**
9. **What's "ERS"?** (Entity Resolution Service? Event Replication Service?)
10. **JSM ExecutionMemoryService vs ADK MemoryIngestService — are they redundant?**

