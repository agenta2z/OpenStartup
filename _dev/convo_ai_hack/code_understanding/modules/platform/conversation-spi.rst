.. _mod-conversation-spi:

==============================================
``platform/conversation/conversation-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/conversation/conversation-spi``
:Size: ~1,110 source lines :sup:`(verified)`

ERS persistence models for conversations. Each conversation entity has an ``Ers*`` mirror class for storage.

Top files :sup:`(verified)`
============================

* ``ErsConversationHistoryItem.kt`` — 186 lines
* ``ErsConversationChannel.kt`` — 145 lines
* ``ErsConversationFunctionMessage.kt`` — 65 lines
* ``ErsConversationGeneratedContent.kt`` — 63 lines
* ``SessionAssociationPublicStore.kt`` — 55 lines

Notable findings
==================

* **Mirror classes pattern** — domain types in ``-api``, ERS forms in ``-spi``. ``conversation-impl`` does the mapping between them via ``ConversationMapper`` (verified in conversation-impl docs).
* **Function messages and generated content have their own ERS types** — separate from history items. Reflects that LLM tool calls and outputs are first-class persistence concerns.

