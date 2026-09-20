.. _mod-utilities-api:

==============================================
``foundation/utilities/utilities-api``
==============================================

:Tier: foundation
:Path: ``modules/foundation/utilities/utilities-api``
:Size: ~11,712 source lines :sup:`(verified)`
:Importance: **Tier 1 — most-imported module**

The crown jewel of foundation. **15 sub-packages** of cross-cutting primitives that virtually every other module imports. See :ref:`foundation-tier` for the sub-package breakdown.

Top files :sup:`(verified by line-count)`
============================================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Sub-package
   * - ``context/Experience.kt``
     - 1,752
     - context
   * - ``featureflag/FakeRolloutService.kt``
     - 780
     - featureflag (test stub)
   * - ``tracing/ArizeSpanWriter.kt``
     - 751
     - tracing
   * - ``client/HttpClientExtensions.kt``
     - 676
     - client
   * - ``identity/IdGatekeeperModels.kt``
     - 408
     - identity
   * - ``logging/InterceptedLogger.kt``
     - 401
     - logging
   * - ``tracing/RootSpanFactory.kt``
     - 302
     - tracing

Notable findings
==================

* ``context/Experience.kt`` is **1,752 lines** — the Experience enum + supporting code is the biggest single file. This reflects the breadth of UX surfaces the platform serves (each is a distinct ``Experience`` value).
* ``FakeRolloutService.kt`` lives in ``-api`` (not ``-impl``) — it's a test fixture meant to be consumed without pulling in Statsig deps.
* ``ArizeSpanWriter.kt`` (tracing/) — the **API-side** of Arize observability; the impl is in utilities-impl.

Patterns
==========

1. **Test fakes in -api.** ``FakeRolloutService`` exists in -api to satisfy the foundation-uses-MockK rule (consumers don't have to mock; they instantiate the fake).
2. **15 sub-packages, one module.** Could be split, but combining keeps the import path stable: ``foundation.utilities.<sub>``.
3. **No Spring dependencies.** This module is pure Kotlin + select Java SDKs (Caffeine, Micrometer, OTel) — pulled into Spring via -impl.

What you would change here
============================

* **Add a new utility primitive** → new file in the appropriate sub-package
* **Add a new test fake** → new ``Fake<X>.kt`` in same sub-package
* **Modify the ``Experience`` enum** → ``context/Experience.kt`` (touches everything; high-blast-radius change)

