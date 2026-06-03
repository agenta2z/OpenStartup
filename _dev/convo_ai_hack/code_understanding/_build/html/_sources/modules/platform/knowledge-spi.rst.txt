.. _mod-knowledge-spi:

==============================================
``platform/knowledge/knowledge-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/knowledge/knowledge-spi``
:Size: ~100 source lines :sup:`(verified)`

Two ERS clients — one for collections, one for sources.

Top files :sup:`(verified)`
============================

* ``ErsKnowledgeSource.kt`` — 51 lines
* ``ErsKnowledgeCollection.kt`` — 37 lines
* ``KnowledgeSourceErsClient.kt`` — 6 lines
* ``KnowledgeCollectionErsClient.kt`` — 6 lines

Key contracts
==============

.. code-block:: kotlin

   interface KnowledgeCollectionErsClient :
       ShardedErsClient<ErsKnowledgeCollection, KnowledgeContext>

   interface KnowledgeSourceErsClient :
       ShardedErsClient<ErsKnowledgeSource, KnowledgeContext>

Notable findings
==================

* Both clients are **sharded** (per-tenant). No global knowledge entities at this level.

