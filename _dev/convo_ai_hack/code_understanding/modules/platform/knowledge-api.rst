.. _mod-knowledge-api:

==============================================
``platform/knowledge/knowledge-api``
==============================================

:Tier: platform
:Path: ``modules/platform/knowledge/knowledge-api``
:Size: ~131 source lines :sup:`(verified)` — *smallest API in the platform tier*

Minimal contract for **knowledge sources** the agent can retrieve from. Tight scope: one manager interface, one collection model, one source model, one context.

Top files :sup:`(verified)`
============================

* ``KnowledgeSource.kt`` — 46 lines (source model)
* ``KnowledgeManager.kt`` — 35 lines (top-level service)
* ``KnowledgeCollection.kt`` — 31 lines (grouping)
* ``KnowledgeContext.kt`` — 10 lines (per-call context)

Key contracts
==============

* ``interface KnowledgeManager`` — list/get/upsert collections + sources
* ``class KnowledgeCollectionNotFoundException``

Notable findings
==================

* **Cleanest API in the platform tier.** Just 131 LoC. Suggests deliberate scope discipline: this module exposes the minimum surface a caller needs.
* The smallness contrasts sharply with ``knowledge-gap-api`` (958 LoC) — even though both are in the same domain, they have very different abstraction shapes.

