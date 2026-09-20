=========================================
06 — Error Handling & Resilience
=========================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

Error handling in proactive-ai-platform follows a **typed exception
hierarchy** rooted at ``RestException``.  Each exception class carries an
HTTP status code, a structured error key, a log-level hint, and an SLO
impact flag, allowing controllers and global handlers to map exceptions to
appropriate HTTP responses and observability signals without ad-hoc logic.

Exception Hierarchy
-------------------

.. code-block:: text

   RuntimeException
   └── RestException                         (base; carries status, errorKey, logLevel, payload)
       ├── RestClientException               (upstream/outbound failures — 4xx/5xx from dependencies)
       └── RestServerException               (this service's own errors)
           ├── UnauthorizedException          401  isBadSLOEvent=false
           ├── ForbiddenException             403  isBadSLOEvent=false
           ├── NotFoundException              404  isBadSLOEvent=false
           ├── BadRequestException            400  isBadSLOEvent=false
           ├── NotAcceptableException         406  isBadSLOEvent=false
           ├── PayloadTooLargeException       413  isBadSLOEvent=false
           ├── GoneException                  410  isBadSLOEvent=false
           ├── PlatformRateLimitException     429  isBadSLOEvent=false
           ├── OpenAIRateLimitRestException   429  isBadSLOEvent=true (ERROR)
           ├── InternalServerErrorException   500  isBadSLOEvent=true (ERROR)
           └── IAmATeapotException            418  isBadSLOEvent=true (ERROR)

Key Design Decisions
^^^^^^^^^^^^^^^^^^^^

``isBadSLOEvent``
   When ``true``, the error is counted against the service's SLO budget.
   Client errors (4xx) default to ``false`` so that bad caller input does
   not penalise the service's error rate.  Server errors (5xx) and the
   ``OpenAIRateLimitRestException`` (an upstream dependency failure surfaced
   as 429) default to ``true``.

``ExceptionLogLevel``
   Each exception declares whether it should be logged at ``ERROR``,
   ``WARN``, ``INFO``, or ``DEBUG``.  ``logAsError()`` returns ``true``
   for ``ERROR`` and ``WARN``, giving metrics code a single predicate
   for "should this count as an operational error?".

   - Client errors (401, 403, 404, 400, 406, 413, 410, 429-platform)
     → ``INFO`` (expected, non-actionable).
   - Server errors (500, 418) and upstream OpenAI rate limits → ``ERROR``.
   - ``RestClientException`` → ``ERROR`` (upstream dependency failure).

``errorKey``
   Machine-readable string (e.g. ``proactiveai.rest.not.found``) suitable
   for structured log indexing and alert routing.

``payload``
   Optional additional context (default ``null``) that can be serialised
   into the HTTP error response body.

``IAmATeapotException`` (418)
   Reserved for known-but-unhandleable edge cases.  The HTTP 418 status
   makes these immediately identifiable in dashboards.  Usage is
   intentionally discouraged in the KDoc.

Error Handling Patterns
-----------------------

Pattern 1: catch-log-rethrow in SQS consumers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   try {
       process(event)
   } catch (e: Exception) {
       log.errorWithContext("Failed to consume event", ctx, e)
       metricsService.count(MetricKey.STREAMHUB_EVENT_ERROR, tags)
       throw e   // ← SQS retries up to MaxReceiveCount, then DLQ
   }

Used in ``AnalyticsEventsMessageQueueConsumer``.  Rethrowing lets the SQS
framework NACK the message so AWS applies its retry/DLQ policy.

Pattern 2: fallback-on-exception in feature gates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   return try {
       featureGatesService.checkGate(context, key)
   } catch (ex: Exception) {
       log.warnWithContext("Failed to check gate", ctx, ex)
       defaultValue   // ← graceful degradation
   }

Used in ``FeatureServiceImpl.checkGateImpl()``.  Feature-flag failures
never block request processing; the gate falls back to its declared
default.

Pattern 3: runCatching for non-critical side-effects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   runCatching {
       featureFlagEvaluationTracker.recordGateCheck(flagName, result)
   }.onFailure { ex ->
       log.warnWithContext("Failed to record evaluation", ctx, ex)
   }

Used in ``FeatureServiceImpl`` for evaluation tracking and in
``AsyncTaskDispatcher`` for ``onFailure`` hooks.  The original exception
is preserved; the side-effect failure is swallowed with a warning.

Pattern 4: metrics-aware exception counting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``CoreMetricsServiceImpl`` introspects exceptions:

- ``extractStatusCode(exception)`` — if the exception is a
  ``RestServerException``, the HTTP status is extracted and emitted as a
  ``status_code`` tag on the error counter.
- ``logAndCountException()`` — logs the exception with structured context
  and counts it, separating expected (INFO-level) from unexpected (ERROR-level)
  failures in dashboards.

Resilience Mechanisms
---------------------

Retry Policies (Egress)
^^^^^^^^^^^^^^^^^^^^^^^

Defined in ``service-descriptor.sd.yml``:

.. code-block:: yaml

   retryPolicy: &retryOn5xxAnd429Policy
     enabled: true
     retryOn: [ "5xx", "retriable-status-codes" ]
     retriableStatusCodes: [ 429 ]

Applied to all three egress dependencies (``id-gatekeeper``,
``ai-gateway``, ``integrations-service``).  Retries are handled at the
service-proxy (Envoy) level, transparent to the application.

SQS Retry & DLQ
^^^^^^^^^^^^^^^^

Each SQS queue declares a ``MaxReceiveCount`` that controls how many times
a failed message is retried before being sent to the automatically
provisioned Dead Letter Queue (DLQ):

- ``analytics-events``: ``MaxReceiveCount=3``, ``VisibilityTimeout=120s``
- ``rovo-insights-generation-queue``: ``MaxReceiveCount=2``,
  ``VisibilityTimeout=360s``

DLQ alarms are configured to fire when messages arrive in the DLQ
(threshold > 0 for low priority, > 100 for high).

Timeout Configuration
^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Dependency
     - Timeout
   * - ``id-gatekeeper``
     - 20 s
   * - ``ai-gateway``
     - 600 s (10 min — LLM inference)
   * - ``integrations-service``
     - 60 s

Circuit Breakers
^^^^^^^^^^^^^^^^

No application-level circuit breakers are currently implemented.  Resilience
to dependency failures relies on:

1. Service-proxy retry policies (immediate retries on 5xx/429).
2. SQS retry + DLQ for asynchronous workloads.
3. Feature-gate fallback-on-exception for Switcheroo SDK failures.
4. Generous timeouts for LLM-backed calls (``ai-gateway`` at 600 s).

Continuous Chaos (staging)
^^^^^^^^^^^^^^^^^^^^^^^^^^

The staging environment includes a ``continuous-chaos`` resource
(``service-descriptor.sd.yml → environmentOverrides.staging``), enabling
automated fault-injection testing in the staging environment.
