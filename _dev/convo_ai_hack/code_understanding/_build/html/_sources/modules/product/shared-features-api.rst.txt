.. _mod-shared-features-api:

==============================================
``product/shared-features/shared-features-api``
==============================================

:Tier: product
:Path: ``modules/product/shared-features/shared-features-api``
:Size: ~16 source lines :sup:`(verified)` — *smallest module in repo*

A single feature-flag enum file — ``SharedProductFeatureFlags.kt``. Defines flags shared across multiple product modules.

Notable findings
==================

* Tiniest module in the repo. Exists purely for shared product-tier feature flags.
* Compare to ``platform/base-api/JsmFeatureFlags.kt`` (463 lines) — the convention is that JSM-only flags live in base-api, while truly cross-product flags live here.

