.. _mod-rovo-insights-api:

==================================
Rovo Insights — REST API
==================================

:Files: ``feature/rovoinsights/api/RovoInsightsController.kt``, ``feature/rovoinsights/api/rest/RovoInsightsTestController.kt``
:DTOs: ``api/dto/``, ``api/status/``, ``api/fetch/``
:Test: ``RovoInsightsControllerIT.kt``
:Importance: **P1 — public-facing insight endpoints**

Controllers
===========

RovoInsightsController (``/api/v1/rovo-insights``)
---------------------------------------------------

The primary production controller with three endpoints:

.. code-block:: text

   POST /api/v1/rovo-insights/generate   → Triggers async insight generation
   POST /api/v1/rovo-insights/status     → Checks if insights are available
   POST /api/v1/rovo-insights/fetch      → Retrieves generated insights

All endpoints require SLAuth headers (``atl-cloudid``,
``X-Slauth-User-Context-Account-Id``).

**Generate** (``/generate``)
   Accepts ``RovoInsightsStatusRequest`` (contains optional ``PromptConfig``).
   Currently returns ``RovoInsightsStatusResponse(insightsAvailable=false)``
   as a stub.

**Status** (``/status``)
   Accepts ``RovoInsightsStatusRequest``. Returns
   ``RovoInsightsStatusResponse(insightsAvailable=false)`` — stub.

**Fetch** (``/fetch``)
   Accepts ``RovoInsightsFetchRequest`` (with ``generate: Boolean``,
   ``debugInfo: Boolean``, ``promptConfig: PromptConfig``). Returns
   ``RovoInsightsFetchResponse`` with ``schemaVersion=3``, empty
   insight groups — stub awaiting generation pipeline integration.

RovoInsightsTestController (``/api/v1/rovo-insights/generate``)
----------------------------------------------------------------

A test/dev controller gated by ``proactive-ai.sqs.enabled=true`` that
actually submits a ``RovoInsightsGenerationTask`` to the async-task
framework:

.. code-block:: kotlin

   suspend fun generate(...): RovoInsightsTestResponse {
       val executionContext = AsyncTaskExecutionContext(
           tenantId = cloudId,
           user = user,
           requestId = inboundRequestId ?: UUID.randomUUID().toString(),
       )
       val taskId = asyncTaskService.submit(
           executionContext,
           RovoInsightsGenerationTask(cloudId = cloudId),
       )
       return RovoInsightsTestResponse(taskId = taskId.value)
   }

Returns ``202 Accepted`` with the ``taskId`` for correlation in Splunk.

Response DTOs
=============

``RovoInsightsFetchResponse``
   The main response envelope for ``/fetch``:

   - ``schemaVersion: Int`` — currently ``3``; incremented on breaking changes.
   - ``generatedAt: Instant`` — timestamp of generation.
   - ``count: Int`` — total insight count across all groups.
   - ``summary: String`` — human-readable summary.
   - ``insightGroups: List<RovoInsightsGroup>`` — grouped by ``InsightType``.

``RovoInsightsGroup``
   Groups insights by type with metadata:
   ``type``, ``title``, ``icon`` (Glyph), ``color`` (Color), ``count``,
   ``insights: List<RovoInsight>``, optional ``debugInfo``.

``RovoInsight``
   Individual insight card: ``title``, ``overview``, ``people`` (list of
   ``PersonReference`` with ``name``, ``aaid``, ``avatarUrl``), ``urls``,
   ``thinking`` (LLM reasoning), ``followUps``, ``detailsAdf`` (ADF markup).

``RovoInsightsTestRequest`` / ``RovoInsightsTestResponse``
   Simple DTOs for the test controller: request has optional ``cloudId``,
   response carries the generated ``taskId: String``.
