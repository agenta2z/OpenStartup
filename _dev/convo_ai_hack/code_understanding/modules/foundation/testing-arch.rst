.. _mod-foundation-testing-arch:

==============================================
``foundation/testing/arch``
==============================================

:Tier: foundation
:Path: ``modules/foundation/testing/arch``
:Importance: **Tier 2 — architecture enforcement**

ArchUnit assertions for foundation layering rules. Enforces foundation isolation **at test time** (not build time).

What it enforces (verified)
==============================

* No foundation module depends on platform/product/service (except ``utilities-impl`` which has documented carve-outs)
* The carve-out for ``utilities-impl`` is intentional (per a comment in build.gradle.kts)

Verified location
====================

``modules/foundation/testing/arch/.../FoundationModuleArchTest.kt:19-33``

Dependencies :sup:`(verified)`
================================

* ``capabilities-api``, ``capabilities-impl``, ``capabilities-spi``
* ``utilities-api``
* ArchUnit

What you would change here
============================

* Add a new architecture invariant → new ArchUnit test in this module

