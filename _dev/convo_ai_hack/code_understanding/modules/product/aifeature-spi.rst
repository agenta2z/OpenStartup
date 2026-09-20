.. _mod-aifeature-spi:

==============================================
``product/aifeature/aifeature-spi``
==============================================

:Tier: product
:Path: ``modules/product/aifeature/aifeature-spi``
:Size: ~428 source lines :sup:`(verified)`

ERS persistence + Redis caches for AI features.

Top files :sup:`(verified)`
============================

* ``ErsContentSuggestedEdit.kt`` — 48 lines
* ``ProactiveRecommendationsRedisCache.kt`` — 40 lines
* ``QuickSummaryRedisCache.kt`` — 38 lines
* ``ContentCatchupRedisCache.kt`` — 38 lines

Notable findings
==================

* **Three Redis caches** — Proactive Recommendations, Quick Summary, Content Catchup. Each AI feature with a "fresh-on-page-load" UX has its own cache.
* Cache abstraction is at SPI level — concrete Redis client is in -impl.

