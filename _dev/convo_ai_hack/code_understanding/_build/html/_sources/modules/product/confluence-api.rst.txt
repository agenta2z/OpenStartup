.. _mod-confluence-api:

==============================================
``product/confluence/confluence-api``
==============================================

:Tier: product
:Path: ``modules/product/confluence/confluence-api``
:Size: ~157 source lines :sup:`(verified)`

Confluence content / page abstractions. Stub-style API; pairs with :ref:`mod-confluence-impl`.

Notable findings
==================

* Tiny API surface — Confluence-specific AI logic mostly lives in -impl + in ``platform/client-api/AsyncConfluenceRestClient.kt`` (2,699 lines).
* The split is: client-api owns the REST DTOs; product/confluence owns the AI-feature abstractions.

