.. _mod-conversation-impl:

==============================================
``platform/conversation/conversation-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/conversation/conversation-impl``
:Size: ~13,624 source lines :sup:`(verified)`
:Importance: **Tier 1 — conversation state**

Conversation state management — message history, branching, replay, ERS-backed storage.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Subsystem
   * - ``conversation/ConversationManagerImpl.kt``
     - 892
     - Top-level conversation manager
   * - ``conversation/history/ConversationHistoryItemManagerImpl.kt``
     - 803
     - History item management
   * - ``conversation/stores/ers/history/ErsConversationHistoryItemStoreImpl.kt``
     - 724
     - ERS-backed history store
   * - ``conversation/stores/ers/history/ConversationHistoryLargeComponentsHandler.kt``
     - 656
     - Large component handling
   * - ``conversation/stores/ers/channel/ErsConversationChannelStoreImpl.kt``
     - 593
     - ERS-backed channel store

Subsystems
============

1. **ConversationManager** — high-level orchestration (create, fetch, update, delete conversations).
2. **History item manager** — manages individual message history items within a conversation.
3. **ERS stores** — Elastic Resource Store (Atlassian's storage abstraction) backed implementations.
4. **Large components handler** — special handling for messages exceeding ERS row-size limits (chunking, blob references).

Patterns
==========

1. **ERS as primary store.** Conversations persist in ERS, not Kamino directly (Kamino is the event-sourced log; ERS is the materialized view).
2. **Large-component handling.** LLM responses can be huge (think long deep-research outputs); chunked + stored separately to avoid ERS row limits.
3. **Channel + history separation.** A "channel" is the conversation envelope; "history items" are the messages inside.

What you would change here
============================

* **Modify conversation lifecycle** → ``ConversationManagerImpl.kt``
* **Adjust large-component thresholds** → ``ConversationHistoryLargeComponentsHandler.kt``
* **Change ERS schema** → ``stores/ers/`` (then migrate)

