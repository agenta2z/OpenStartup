.. _mod-conversation-impl-deep:

==================================================================
``platform/conversation/conversation-impl`` — chat lifecycle
==================================================================

:Tier: platform
:Path: ``modules/platform/conversation/conversation-impl``
:Size: **13,624 main + 20,930 test LoC** :sup:`(verified 2026-05-02)`
:Files: 96 main + 113 test
:Importance: ⭐⭐⭐⭐ Tier 1 — every chat message routes through here

The conversation lifecycle implementation. Manages channels, history items, persistence, and the
"large component" handling for messages that exceed simple ERS document size limits.

Top files (verified 2026-05-02)
==================================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File (relative)
     - Lines
     - Role
   * - ``conversation/ConversationManagerImpl.kt``
     - **892**
     - Top-level conversation orchestration
   * - ``conversation/history/ConversationHistoryItemManagerImpl.kt``
     - 803
     - History item CRUD
   * - ``conversation/stores/ers/history/ErsConversationHistoryItemStoreImpl.kt``
     - 724
     - ERS persistence for history items
   * - ``conversation/stores/ers/history/ConversationHistoryLargeComponentsHandler.kt``
     - **656**
     - Handles items too large for single ERS doc
   * - ``conversation/stores/ers/channel/ErsConversationChannelStoreImpl.kt``
     - 593
     - ERS persistence for channels
   * - ``conversation/stores/multi/ConversationChannelMultiStoreImpl.kt``
     - 441
     - Multi-store coordination
   * - ``conversation/stores/ers/memory/ErsConversationTopicSegmentStoreImpl.kt``
     - 390
     - Topic-segment persistence
   * - ``conversation/channel/ConversationChannelManagerImpl.kt``
     - 390
     - Channel management
   * - ``conversation/space/SpaceServiceImpl.kt``
     - 385
     - Conversation "space" service

Architectural sub-systems
============================

The 13,624 LoC organizes around four concerns:

1. **Top-level orchestration** (``conversation/``)

   * ``ConversationManagerImpl`` — entry point, ~892 LoC

2. **History items** (``conversation/history/`` + ``stores/ers/history/``)

   * Manager → store → ERS persistence
   * **``ConversationHistoryLargeComponentsHandler`` (656 LoC)** — splits oversized history items across multiple ERS documents (because individual ERS docs have size limits)

3. **Channels** (``conversation/channel/`` + ``stores/ers/channel/``)

   * Channels are the "container" for a conversation thread
   * Multi-store pattern: ``ConversationChannelMultiStoreImpl`` (441 LoC) coordinates between primary and secondary stores

4. **Memory + topic segments** (``conversation/stores/ers/memory/``)

   * In-session sub-conversation segments (the ``InSessionSegment`` type from ``conversation-api``)
   * Persisted via ``ErsConversationTopicSegmentStoreImpl``

Notable design patterns
=========================

* **Layered persistence** — manager → store → ERS-store → ERS-client. Four layers of indirection. Allows substituting backends in tests + permits the "multi-store" pattern.
* **Large component handling** — the existence of ``ConversationHistoryLargeComponentsHandler`` (656 LoC) reveals a real production constraint: ERS document size limits force history items >X bytes to be split.
* **Multi-store** — ``ConversationChannelMultiStoreImpl`` suggests dual-write or shadow-read for migration / consistency checks.

What you would change here
============================

* **Add a new conversation event type** → extend ``ConversationHistoryItemManagerImpl``
* **Adjust large-component split boundaries** → ``ConversationHistoryLargeComponentsHandler``
* **Add a topic-segment policy** → ``ErsConversationTopicSegmentStoreImpl``
* **Change channel multi-store routing** → ``ConversationChannelMultiStoreImpl``

What you would NOT change here
================================

* Conversation domain types → :ref:`mod-conversation-api`
* ERS contracts → ``conversation-spi`` + ``platform/foundation/ers-impl``
* Per-product conversation logic → product-tier impl modules

Critical observations
=======================

1. **Manager is 892 LoC** — borderline god-class but reasonable given conversation has many lifecycle events.

2. **Large-component handler at 656 LoC is suspicious** — that's a lot of code to "split a document". May indicate the splitting algorithm has accumulated edge cases over time. Worth a refactoring review.

3. **20,930 test LoC vs 13,624 main = 1.5×** — strong coverage; aligned with the criticality.

4. **Multi-store pattern presence** strongly suggests an ongoing storage migration. Worth understanding the dual-store invariant before changing channel logic.

