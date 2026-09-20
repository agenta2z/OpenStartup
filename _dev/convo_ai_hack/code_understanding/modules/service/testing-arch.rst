.. _mod-service-testing-arch:

==============================================
``service/testing/arch``
==============================================

:Tier: service
:Path: ``modules/service/testing/arch``
:Importance: **Tier 2 — service-level arch tests**

Service-level ArchUnit tests. Loads ALL product implementations at test runtime to validate cross-module rules.

Dependencies :sup:`(verified)`
================================

* All ``product/*-impl`` modules (8 products)
* ``aifeature-impl``
* ``platform/base-impl``, ``platform/service-impl``
* Spring GraphQL, ArchUnit

Patterns
==========

1. **Loads everything.** This is the only place where all product impls are simultaneously on the test classpath.
2. **No MockK.** Architecture tests don't need mocking.
3. **GraphQL schema validation possible.** Can validate that GraphQL schemas across products don't conflict.

What you would change here
============================

* Add a service-wide architecture invariant → new ArchUnit test
* Add a GraphQL schema compliance check → SchemaMapping-based test

