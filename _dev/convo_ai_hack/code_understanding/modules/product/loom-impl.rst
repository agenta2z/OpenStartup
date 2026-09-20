.. _mod-loom-impl:

==============================================
``product/loom/loom-impl``
==============================================

:Tier: product
:Path: ``modules/product/loom/loom-impl``
:Size: ~412 source lines :sup:`(verified)`

Loom video / transcript content provider.

Notable findings
==================

* Provides video content as a knowledge source — transcripts feed RAG retrieval.
* Compact module (412 LoC) — most of Loom's API/data-fetch lives in the Loom service itself; this module is the convo-ai adapter.

