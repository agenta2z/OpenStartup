.. _mod-conversation-api:

==============================================
``platform/conversation/conversation-api``
==============================================

:Tier: platform
:Path: ``modules/platform/conversation/conversation-api``
:Size: ~3,570 source lines :sup:`(verified)`

Conversation domain model + management contracts. Channels, messages, history, in-session segments.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Concept
   * - ``ConversationManager.kt``
     - 528
     - Top-level orchestrator
   * - ``ConversationChannel.kt``
     - 307
     - Channel model
   * - ``ConversationHistoryItem.kt``
     - 261
     - Message-event model
   * - ``ConversationHistoryItemManager.kt``
     - 156
     - History service
   * - ``InSessionSegment.kt``
     - 136
     - Sub-conversation segments

Key public contracts
======================

* ``interface ConversationManager`` — top-level conversation orchestration
* ``interface ConversationHistoryItemManager`` — message history access
* Data classes: ``ConversationChannel``, ``ConversationHistoryItem``, ``InSessionSegment``

Notable findings
==================

* ``ConversationManager`` (528 lines) is the central abstraction; most ``ChatV1Controller`` requests hit this.
* **InSessionSegment** is interesting — conversations can be partitioned into segments (e.g., for sub-tasks within a longer chat). Worth investigating semantics.

