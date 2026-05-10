.. _pai-feature-greeting:

============================================================================
``feature/greeting`` — Example / template feature
============================================================================

:Date: 2026-05-04
:Files: 1 main + 0 test
:Importance: **P3 — reference implementation for new feature authors**
:Strategic role: Template feature; regression target for framework changes

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

A minimal end-to-end feature kept as a working reference. The entire feature
lives in a single file (``WebServiceController.kt``) and demonstrates the
canonical pattern every new PAI feature should follow:

* Spring ``@RestController`` with path-parameter binding
* Feature-flag check via ``AiFeatureGates.TEST_GATE`` (gating a log line)
* Metric emission via ``MetricsService.count``
* DTO serialisation with a data-class response

This feature has **zero business logic** by design — its value is as a
template and regression target, not as a user-facing surface.

2. Public API
================

.. list-table::
   :header-rows: 1
   :widths: 10 35 55

   * - HTTP
     - Path
     - Purpose
   * - GET
     - ``/greetings/{name}``
     - Returns ``SampleResponse(greeting: "Hello, {name}!")``

* **Auth**: No auth required (anonymous path — not behind SLAuth).
* **Body**: None.
* **Response**: ``200 OK`` with JSON body.

Response schema:

.. code-block:: json

   {
     "greeting": "Hello, Alice!"
   }

3. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``WebServiceController.kt``
     - ~35
     - Complete feature: controller + DTO + wiring

4. Code walkthrough
======================

``WebServiceController.kt``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @RestController
   class WebServiceController(
       private val featureService: FeatureService,
       private val metricsService: MetricsService,
       private val logger: LaasLogger
   ) {
       @GetMapping("/greetings/{name}")
       fun greeting(@PathVariable name: String): SampleResponse {
           // 1. Feature-flag gated log (demonstrates gate usage)
           if (featureService.checkGate(AiFeatureGates.TEST_GATE)) {
               logger.info("Test gate is ON for this request")
           }

           // 2. Metric emit (demonstrates MetricsService usage)
           metricsService.count("greeting.invoked")

           // 3. DTO return (demonstrates response pattern)
           return SampleResponse(greeting = "Hello, $name!")
       }
   }

   data class SampleResponse(val greeting: String)

Key patterns demonstrated:

* **Constructor injection** of platform services (``FeatureService``,
  ``MetricsService``, ``LaasLogger``)
* **``@GetMapping``** with ``@PathVariable`` for REST binding
* **``checkGate()``** for feature-flag evaluation
* **``count()``** for metric emission
* **Data class** as response DTO (auto-serialised by Spring/Jackson)

5. Design rationale
======================

Why keep a trivial feature?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Atlassian Spring Boot template ships with a minimal example endpoint. The
PAI team kept this slimmed-down version after the template-bootstrap PR for
three reasons:

1. **Copy-paste template** — new contributors can duplicate the pattern into
   ``feature/<new-feature>/`` without guessing the wiring.
2. **Smoke test target** — deployment pipelines hit ``/greetings/smoke`` as a
   dependency-free health signal separate from ``/healthcheck``.
3. **Regression target** — framework-level changes (interceptor refactors,
   Spring upgrades, Jackson config changes) can be validated against a
   no-business-logic endpoint. If ``greeting`` breaks, so does every feature.

6. Test coverage
==================

**No dedicated tests.** This is acceptable because:

* The feature has zero business logic.
* It exercises only platform code that is independently tested.
* It serves as an implicit integration test target during CI smoke runs.

7. Integration patterns
==========================

.. code-block:: text

   WebServiceController
   ├── uses → FeatureService (checkGate)
   ├── uses → MetricsService (count)
   └── uses → LaasLogger (info)

* **No external dependencies** — no HTTP calls, SQS, Redis, or AI Gateway.
* **No tenant context** — does not call ``CommonContextSetter.setTenant()``.
* **No auth** — listed in anonymous paths.

8. Should you ever modify it?
================================

* **Add a new feature:** Don't modify ``greeting``; copy the pattern into a new
  ``feature/<your-feature>/`` package.
* **Framework refactor:** Use ``greeting`` as a regression target — if a
  refactor breaks ``greeting``, it will break every feature.
* **Add a platform service demo:** Acceptable to add a one-line demo of a new
  platform service (e.g. showing ``LoggingContext.runWithContext``), but keep
  the feature minimal.

9. See also
==============

* :doc:`/modules/features/rovo-insights` — the strategic feature (async pattern)
* :doc:`/modules/features/nudge` — the synchronous decision-plane feature
* :doc:`/modules/platform/interceptor` — the interceptor chain this request crosses
* :doc:`/modules/platform/featuregate` — the feature-flag system ``checkGate()`` delegates to
