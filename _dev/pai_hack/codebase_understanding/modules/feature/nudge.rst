=============================================
Module: ``nudge`` — Nudge Throttle Controller
=============================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Provides a REST endpoint for **nudge throttling** — determining whether a
specific nudge type should be delivered to a user or suppressed based on
frequency / scoring logic.  This is the service's simplest feature module,
consisting of a single controller, a domain enum, and request/response DTOs.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``api/domain/NudgeType.kt``
     - 14
     - Enum: 10 nudge type categories
   * - ``api/dto/NudgeThrottleRequest.kt``
     - 9
     - Request DTO with ``nudgeType``
   * - ``api/dto/NudgeThrottleResponse.kt``
     - 10
     - Response DTO with ``score`` and ``throttled``
   * - ``api/rest/NudgeThrottleController.kt``
     - 39
     - ``@RestController`` — throttle check endpoint

**Total: 4 files, ~72 LoC**

Class / Interface / Enum Catalog
================================

Enums
-----

* ``NudgeType`` — 10 nudge categories:

  - ``CONVO_STARTER`` — conversation starters.
  - ``JIRA_JQL_EXECUTED`` — JQL execution nudges.
  - ``JIRA_SIMILAR_WORK_ITEMS`` — similar-issue suggestions.
  - ``JIRA_STATUS_UPDATER`` — status update reminders.
  - ``JIRA_VERSION_CHANGE`` — version change notifications.
  - ``JIRA_WORK_READINESS`` — work readiness checks.
  - ``NUDGE_LIMITER`` — meta-throttle for all nudges.
  - ``PAGE_CATCHUP`` — page catch-up suggestions.
  - ``PAGE_SUMMARIES`` — page summary nudges.
  - ``AUDIO_BRIEFING`` — audio briefing triggers.

Data Classes
------------

* ``NudgeThrottleRequest`` — ``val nudgeType: NudgeType``
  (``@param:JsonProperty("nudge_type")``).

* ``NudgeThrottleResponse`` — ``val score: Int``, ``val throttled: Boolean``
  (``@field:JsonProperty``).

REST Controllers
----------------

* ``NudgeThrottleController`` (``@RestController``,
  ``@RequestMapping("/api/v1/nudge")``) —

  - ``POST /throttle`` (implied by ``@Operation``) →
    ``fun nudgeThrottle(cloudId: String, userId: String, body: NudgeThrottleRequest): NudgeThrottleResponse``

  Parameters extracted from:

  - ``@RequestHeader("X-Cloud-Id") cloudId``
  - ``@RequestHeader("X-User-Id") userId`` (or similar)
  - ``@RequestBody body: NudgeThrottleRequest``

Spring Component Annotations
=============================

=============================== ===================
Bean                             Annotation
=============================== ===================
``NudgeThrottleController``      ``@RestController``
=============================== ===================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["Upstream service / UI client"] -->|"POST /api/v1/nudge/throttle
       Headers: X-Cloud-Id, X-User
       Body: nudge_type"| B[NudgeThrottleController]
       B --> C[Deserialise NudgeType]
       C --> D[Evaluate throttle logic]
       D --> E["Response: { score, throttled }"]

Configuration Knobs
===================

No YAML properties specific to this module.  Throttle logic parameters (if
any) are likely managed through feature flags via the ``featuregate`` module.

Testing Coverage
================

============================================= ====== ============================
Test class                                     Lines  Subjects
============================================= ====== ============================
``NudgeThrottleControllerAcceptanceTest``       158   Full request/response cycle
============================================= ====== ============================

**Coverage: 1 test file** — acceptance-level test covering the controller.

Dependencies
============

Inbound (consumed by)
---------------------

* External clients — Rovo UI / upstream services call the throttle endpoint.

Outbound (depends on)
---------------------

* Jackson — ``@JsonProperty`` for serialisation.
* Swagger — ``@Operation`` for OpenAPI documentation.
* Spring Web — ``@RestController``, ``@RequestMapping``, ``@RequestHeader``,
  ``@RequestBody``.

Open Questions / Ambiguities
=============================

1. The throttle logic implementation is not visible in this module — the
   controller may delegate to an injected service not shown in the file
   inventory.  Verify whether throttle evaluation lives in this module or
   elsewhere.
2. ``NUDGE_LIMITER`` is a meta-type (throttle for all nudges) — its
   relationship to the other 9 types is not documented.
3. ``score: Int`` in the response — the scoring range and semantics are not
   documented in the code or DTOs.
4. No rate limiting or authentication-specific logic visible in the controller
   — relies entirely on the interceptor chain for auth.
