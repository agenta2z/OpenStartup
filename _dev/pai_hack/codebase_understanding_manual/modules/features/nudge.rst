.. _pai-feature-nudge:

============================================================================
``feature/nudge`` — Throttle decisions for proactive nudges
============================================================================

:Date: 2026-05-04
:Files: 4 main + 0 test (gap — see §9)
:Importance: **P1 — co-highest priority with rovo-insights for the FY26 H2 OKR**
:Strategic role: Synchronous decision plane for proactive nudge rendering

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

A **throttle decision plane** for proactive nudges. Product surfaces (Confluence
"Summarise Changes", Rovo conversation starters, Jira nudges, etc.) call this
service before deciding whether to render a nudge. PAI returns a decision:
how many seconds to delay, and whether to suppress entirely.

The feature is synchronous (no SQS/async) and must be fast — the p95 latency
target is **<50 ms** because the caller blocks rendering on the response.

2. Public API
================

Single REST endpoint:

.. list-table::
   :header-rows: 1
   :widths: 10 35 55

   * - HTTP
     - Path
     - Purpose
   * - POST
     - ``/api/v1/nudge/throttle``
     - Throttle decision for a given nudge type for the calling user/workspace

2.1 Request contract
-----------------------

* **Headers** (required):

  * ``atl-cloud-id`` — workspace identifier
  * ``x-slauth-user-context-account-id`` — calling user's account_id (via SLAuth)

* **Body**: ``NudgeThrottleRequest``

.. code-block:: kotlin

   data class NudgeThrottleRequest(
       val nudgeType: NudgeType
   )

2.2 Response contract
------------------------

.. code-block:: kotlin

   data class NudgeThrottleResponse(
       val delaySeconds: Int,
       val suppress: Boolean
   )

* ``delaySeconds`` — number of seconds the caller should wait before rendering
* ``suppress`` — if ``true``, do not render the nudge at all

3. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``api/rest/NudgeThrottleController.kt``
     - ~45
     - REST controller; reads user + cloud_id, delegates to throttle logic
   * - ``api/dto/NudgeThrottleRequest.kt``
     - ~8
     - Inbound DTO
   * - ``api/dto/NudgeThrottleResponse.kt``
     - ~8
     - Outbound DTO
   * - ``api/domain/NudgeType.kt``
     - ~15
     - Enum of nudge categories

4. Domain model
==================

``NudgeType`` (enum)
~~~~~~~~~~~~~~~~~~~~~~

Closed set of nudge categories following Atlassian product-team naming:

.. code-block:: kotlin

   enum class NudgeType {
       SUMMARISE_CHANGES,       // Confluence "Summarise Changes" button
       CONVERSATION_STARTER,    // Rovo conversation starters
       JIRA_ISSUE_SUMMARY,      // Jira issue summary nudge
       // ... additional values per product-team registration
   }

Adding a new nudge type requires:

1. Add the enum value to ``NudgeType.kt``.
2. Register throttle weights for the new type in TAP (planned).
3. Add the corresponding GASv3 event filter in the StreamHub consumer (planned).

5. Internal data flow
========================

5.1 Today (stub)
-------------------

::

   POST /api/v1/nudge/throttle
     │
     ▼
   NudgeThrottleController                            (api/rest/)
     │  • @RequestAttribute(USER) user
     │  • @RequestHeader("atl-cloud-id") cloudId
     │  • CommonContextSetter.setTenant(cloudId, ...)
     │  • log {cloud_id, nudge_type}
     │  • return NudgeThrottleResponse(delaySeconds = 10, suppress = false)
     ▼
   200 OK

The body is a **hardcoded stub** today.

5.2 Planned production flow
-----------------------------

::

   POST /api/v1/nudge/throttle
     │
     ▼
   NudgeThrottleController
     │
     ▼
   NudgeThrottleService                               (planned)
     │  • Look up TAP traits for (user, nudgeType)
     │  • Look up recent GASv3 events for (user, nudgeType)
     │  • Compute composite delay/suppress decision
     │  • Write decision to Redis with TTL
     │  • Emit metric (proactive-ai.nudge.decision, tag: nudgeType, decision)
     ▼
   NudgeThrottleResponse(delaySeconds, suppress)

6. Code walkthrough
======================

``NudgeThrottleController.kt``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @RestController
   @RequestMapping("/api/v1/nudge")
   class NudgeThrottleController(
       private val commonContextSetter: CommonContextSetter,
       private val metricsService: MetricsService,
       private val logger: LaasLogger
   ) {
       @PostMapping("/throttle")
       fun throttle(
           @RequestAttribute(USER) user: User,
           @RequestHeader("atl-cloud-id") cloudId: String,
           @RequestBody request: NudgeThrottleRequest
       ): NudgeThrottleResponse {
           commonContextSetter.setTenant(cloudId, /* ... */)

           logger.infoWithContext(
               "Nudge throttle request",
               mapOf("cloud_id" to cloudId, "nudge_type" to request.nudgeType)
           )

           // TODO: replace with real throttle logic (TAP + GASv3)
           return NudgeThrottleResponse(delaySeconds = 10, suppress = false)
       }
   }

Key observations:

* Uses ``@RequestAttribute(USER)`` — requires ``UserContextInterceptor`` in the chain.
* Calls ``setTenant()`` early — establishes full MDC + Statsig context.
* Returns synchronously — no async dispatch.
* Stub logic: hardcoded 10s delay, never suppresses.

7. External system integrations (planned)
=============================================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - System
     - Integration purpose
   * - **TAP**
     - Trait/cohort-based throttle weights per user segment
   * - **GASv3 / StreamHub**
     - Recent-engagement signals (proxied via the StreamHub event consumer in ``sqs/``, persisted to Redis)
   * - **Redis (Valkey)**
     - Decision caching + per-user nudge-history TTL keys
   * - **MetricsService**
     - Decision telemetry feeding acceptance/dismiss-rate dashboards

The nudge throttle endpoint itself is synchronous, but it consumes **upstream**
data from the StreamHub event consumer (``sqs/``) which writes recent-event
signals to Redis. So the feature implicitly depends on the SHWorkers pod
group being healthy.

8. Feature flags
==================

None today. Once TAP integration lands, expect at least:

* ``AiFeatureGates.NUDGE_THROTTLE_TAP_ENABLED`` — kill switch for the TAP path
* Per-nudge-type gates for staged rollouts (e.g. enable Confluence nudges
  before Jira nudges)

9. Test coverage
==================

**Zero dedicated controller tests today.** Reviewer feedback on PR #98 flagged
this gap. The current risk assessment:

* **Today (P3)**: low blast radius — failing the endpoint just degrades to
  nudges rendering unconditionally (product surface has its own fallback).
* **Post-TAP (P2)**: higher blast radius — once the throttle gates user-visible
  behaviour, test coverage becomes mandatory.

Recommended test plan:

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Test
     - Type
     - Validates
   * - ``NudgeThrottleControllerTest``
     - Unit
     - Request parsing, context setup, response shape
   * - ``NudgeThrottleServiceTest``
     - Unit
     - TAP + GASv3 decision logic (when implemented)
   * - ``NudgeThrottleIntegrationTest``
     - Integration
     - End-to-end with mocked Redis/TAP

10. Production-readiness gaps
================================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Gap
     - Status
   * - Throttle logic hardcoded
     - No actual TAP/GASv3 integration
   * - No controller tests
     - PR #98 reviewer feedback — planned
   * - No metrics emission
     - No ``proactive-ai.nudge.*`` series in SignalFx yet
   * - No SLO / Tome registration
     - Latency SLO is aspirational (<50 ms p95)

11. Design decisions
=======================

1. **Synchronous over async** — nudge rendering is latency-sensitive; async
   would add SQS round-trip overhead (~200–500 ms) that exceeds the 50 ms target.
2. **Closed enum for NudgeType** — prevents unknown nudge types from entering
   the system; forces registration in PAI before product teams can call.
3. **Upstream data via SQS** — GASv3 signals are pre-ingested asynchronously
   (via ``sqs/`` StreamHub consumer) rather than fetched live, keeping the
   synchronous path fast.
4. **Stub-first approach** — ship the API contract early so product teams can
   integrate; backfill real logic later.

12. See also
===============

* :doc:`/architecture/cross-cutting/01-business-and-technical-goals` §2 — how
  this feature contributes to the OKR
* :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs` — the upstream
  StreamHub consumer this will read from
* :doc:`/modules/platform/sqs` — the SQS consumer infrastructure
* :doc:`/modules/platform/context` — tenant context types used by the controller
* :doc:`/modules/features/rovo-insights` — sibling feature (async pattern)
