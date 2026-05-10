.. _mod-knowledge-gap-spi:

==============================================
``platform/knowledge-gap/knowledge-gap-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/knowledge-gap/knowledge-gap-spi``
:Size: ~44 source lines :sup:`(verified)` — *one of the two smallest SPIs*

Four ERS clients with a deliberate **mix of sharded and global** contracts.

Top files :sup:`(verified)`
============================

* ``KnowledgeGapSuggestionArticleErsClient.kt`` — 13 lines
* ``KnowledgeGapQAPairsErsClient.kt`` — 13 lines
* ``KnowledgeGapUploadFileErsClient.kt`` — 13 lines
* ``KnowledgeGapUploadJobErsClient.kt`` — 5 lines

Key contracts :sup:`(verified)`
=================================

.. code-block:: kotlin

   interface KnowledgeGapSuggestionArticleErsClient<T : KnowledgeGapContext>
       : ShardedErsClient<...>          // tenant-scoped

   interface KnowledgeGapQAPairsErsClient<T : KnowledgeGapContext>
       : ShardedErsClient<...>          // tenant-scoped

   interface KnowledgeGapUploadFileErsClient<T : KnowledgeGapContext>
       : ShardedErsClient<...>          // tenant-scoped

   interface KnowledgeGapUploadJobErsClient
       : GlobalErsClient<...>           // GLOBAL — not tenant-scoped

Notable findings
==================

* **Upload jobs are global**, but their content (suggestions, QA pairs, files) is sharded. Suggests an upload-job entry point that is centrally managed (e.g. by ML Studio) but produces tenant-specific results.

