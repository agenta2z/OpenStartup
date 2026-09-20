.. _mod-knowledge-gap-api:

==============================================
``platform/knowledge-gap/knowledge-gap-api``
==============================================

:Tier: platform
:Path: ``modules/platform/knowledge-gap/knowledge-gap-api``
:Size: ~958 source lines :sup:`(verified)`

Tracks **knowledge gaps** — questions or topics for which the platform has no good answer. Used to prioritize what to add to knowledge bases.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Concept
   * - ``KnowledgeGapManager.kt``
     - 195
     - Top-level manager
   * - ``KnowledgeGapSuggestionArticle.kt``
     - 148
     - Suggested-article model
   * - ``KnowledgeGapUploadJob.kt``
     - 88
     - Upload-job model
   * - ``KnowledgeGapErsSuggestionArticle.kt``
     - 61
     - ERS form

Key public contracts
======================

* ``interface KnowledgeGapManager<T : KnowledgeGapContext>`` — generic manager
* ``interface KnowledgeGapSuggestionArticleService``
* ``interface KnowledgeGapSpaceService``
* ``interface KnowledgeGapContextFactory`` / ``KnowledgeGapContextFactoryProvider``
* Exception types: ``KnowledgeGapJobNotFoundException``, ``KnowledgeGapInvalidStatusException``, ``KnowledgeGapInvalidJobTypeException``, ``SpaceIdNotFoundException``

Notable findings
==================

* **Generic manager** ``KnowledgeGapManager<T : KnowledgeGapContext>`` — designed for reuse across different knowledge contexts.
* Domain-heavy: ``KnowledgeGapSuggestionArticle`` (148 LoC) and ``KnowledgeGapUploadJob`` (88 LoC) carry meaningful structure, not just IDs.

