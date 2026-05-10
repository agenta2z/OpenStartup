.. _mod-context-impl:

==============================================
``foundation/context/context-impl``
==============================================

:Tier: foundation
:Path: ``modules/foundation/context/context-impl``
:Importance: **Tier 2 — runtime**

Concrete implementations of context-api contracts.

Notable
========

* Implements ``AsyncTenantContextService`` :sup:`(per agent investigation)`
* Wraps TCS client for tenant lookups
* Uses MockK for tests (foundation rule)

What you would change here
============================

* Modify TCS lookup behavior → implementation classes here
* Add a new context-impl SPI → register a new ``Tenant*ServiceImpl``

