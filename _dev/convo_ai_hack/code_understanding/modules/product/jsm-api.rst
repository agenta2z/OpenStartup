.. _mod-jsm-api:

==============================================
``product/jsm/jsm-api``
==============================================

:Tier: product
:Path: ``modules/product/jsm/jsm-api``
:Size: ~523 source lines :sup:`(verified)`

JSM (Jira Service Management) service contracts. Pairs with the already-documented :ref:`mod-jsm-impl`.

Notable findings
==================

* Stub-style API surface — most JSM logic is in -impl.
* Also see ``platform/base-api/JsmFeatureFlags.kt`` (463 lines) for JSM-related flags that live in the base layer for cross-tier access.

