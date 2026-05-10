.. _mod-knowledge-impl:

==============================================
``platform/knowledge/knowledge-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/knowledge/knowledge-impl``
:Size: ~959 source lines :sup:`(verified)`

Implementation of the ``KnowledgeManager`` plus two store classes.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Role
   * - ``KnowledgeCollectionStore.kt``
     - 127
     - Collection persistence
   * - ``KnowledgeSourceStore.kt``
     - 107
     - Source persistence
   * - ``KnowledgeManagerImpl.kt``
     - 89
     - Manager facade

Notable findings
==================

* Three classes do all the work — proportionate to the small API surface.
* No vector-store integration found in this module — the actual retrieval/embedding lives elsewhere (likely in ``platform/knowledge-gap-impl`` ML-Studio integration or in product-tier).

