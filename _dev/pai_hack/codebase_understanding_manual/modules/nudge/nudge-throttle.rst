.. _mod-nudge-throttle:

=========================
Nudge Throttle API
=========================

:Package: ``io.atlassian.micros.proactiveai.feature.nudge``
:Files: ``feature/nudge/api/domain/NudgeType.kt``, ``feature/nudge/api/dto/NudgeThrottleRequest.kt``, ``feature/nudge/api/dto/NudgeThrottleResponse.kt``, ``feature/nudge/api/rest/NudgeThrottleController.kt``
:Test: ``feature/nudge/api/rest/NudgeThrottleControllerAcceptanceTest.kt``
:Importance: **P1 — nudge rate-limiting entry point**

Overview
========

The nudge throttle module provides a REST API for clients to query whether a
specific nudge type should be throttled for a given user and tenant. It is the
entry point for all nudge rate-limiting decisions across the Proactive AI
platform.

Currently the controller returns a **stub** response (``score=10``,
``throttled=false``) for all nudge types, serving as a scaffold for the
real throttle logic that will incorporate user-level and tenant-level
rate-limiting state.

Domain Model — ``NudgeType``
============================

``NudgeType`` is an enum defining the full catalogue of proactive nudge
categories the platform supports:

.. code-block:: kotlin

   enum class NudgeType {
       CONVO_STARTER,
       JIRA_JQL_EXECUTED,
       JIRA_SIMILAR_WORK_ITEMS,
       JIRA_STATUS_UPDATER,
       JIRA_VERSION_CHANGE,
       JIRA_WORK_READINESS,
       NUDGE_LIMITER,
       PAGE_CATCHUP,
       PAGE_SUMMARIES,
       AUDIO_BRIEFING,
   }

Each variant maps to a distinct proactive experience in the Atlassian product
surface (Jira, Confluence, cross-product). ``NUDGE_LIMITER`` acts as a
meta-type for the throttle subsystem itself.

Request / Response DTOs
=======================

``NudgeThrottleRequest``
   Contains a single field ``nudgeType: NudgeType``. Jackson maps the JSON
   property ``nudge_type`` to the Kotlin field via ``@param:JsonProperty``.

``NudgeThrottleResponse``
   Returns ``score: Int`` (priority weight) and ``throttled: Boolean``
   (whether the nudge should be suppressed). Uses ``@field:JsonProperty``
   for serialisation.

REST Controller
===============

:Endpoint: ``POST /api/v1/nudge/throttle``
:Produces: ``application/json``
:Auth: SLAuth — requires ``atl-cloudid`` and ``X-Slauth-User-Context-Account-Id`` headers.

.. code-block:: text

   POST /api/v1/nudge/throttle
   Headers:
     atl-cloudid: <cloud-id>
     X-Slauth-User-Context-Account-Id: <user-id>
   Body: { "nudge_type": "CONVO_STARTER" }

   Response 200:
   { "score": 10, "throttled": false }

The controller logs the inbound request with ``cloud_id`` and ``nudge_type``
context using the ``LaasLoggerFactory`` structured logging framework.

Request Flow
============

::

   Client
     │
     ▼
   NudgeThrottleController.nudgeThrottle()
     ├── Extracts cloudId, userId from SLAuth headers
     ├── Deserialises NudgeThrottleRequest (nudge_type)
     ├── Logs request with cloud_id + nudge_type
     └── Returns NudgeThrottleResponse(score=10, throttled=false)  [stub]

Test Coverage
=============

``NudgeThrottleControllerAcceptanceTest`` is a full ``@SpringBootTest``
(``RANDOM_PORT``) acceptance test covering:

* **Happy path** — all headers present → 200 with expected response body.
* **Parameterised nudge types** — ``@EnumSource(NudgeType::class)`` ensures
  every variant is accepted and returns a valid response.
* **Missing ``atl-cloudid``** → 400 Bad Request.
* **Missing ``X-Slauth-User-Context-Account-Id``** → 400 Bad Request.
* **Invalid nudge type** — unrecognised enum value → 400 Bad Request.
* **Unauthorized** — missing ``X-Slauth-Authz`` header → 401 Unauthorized.

The test uses ``TestRestTemplate`` with explicit header construction,
validating both the HTTP status and the deserialised ``NudgeThrottleResponse``
body.
