.. _mod-knowledge-gap-impl:

==============================================
``platform/knowledge-gap/knowledge-gap-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/knowledge-gap/knowledge-gap-impl``
:Size: ~7,146 source lines :sup:`(verified)`
:Importance: Tier 2 — heavy job orchestration

Implementation of the knowledge-gap workflow: Confluence integration, ML Studio integration, async cleanup, suggestion-article serving.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``KnowledgeGapJobService.kt``
     - 616
     - Job orchestration (god-class)
   * - ``KnowledgeGapConfluenceService.kt``
     - 239
     - Confluence integration
   * - ``KnowledgeGapStaleJobCleanupTask.kt``
     - 200
     - Background cleanup
   * - ``KnowledgeGapSuggestionArticleServiceImpl.kt``
     - 185
     - Suggestion serving

Key Spring components
=======================

* ``class KnowledgeGapJobService`` — 616-line orchestrator
* ``class KnowledgeGapConfluenceService`` — Confluence ingestion
* ``class KnowledgeGapStaleJobCleanupTask`` — async sweeper
* ``class KnowledgeGapSuggestionArticleServiceImpl``
* ``class KnowledgeGapUploadJobServiceImpl``
* ``class MlStudioWorkflowServiceImpl`` — ML Studio integration
* ``class KnowledgeGapContextFactoryProviderImpl``
* ``class KnowledgeGapConfig``
* ``object LinkUtils``
* ``object KnowledgeGapGasV3Events`` — analytics-event constants

Notable findings
==================

* **616-line god-class** in ``KnowledgeGapJobService``. Plausible split: job-state-machine, source-coordination, output-emission.
* **Three external integrations in one module** — Confluence (KG ingestion), ML Studio (workflow), and analytics (GASv3 events).
* Has its own background cleanup task ``KnowledgeGapStaleJobCleanupTask`` — operates independently of the main job lifecycle.

