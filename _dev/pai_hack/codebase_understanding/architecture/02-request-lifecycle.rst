.. _request-lifecycle:

==============================
Request Lifecycle
==============================

This document traces an HTTP request through the Proactive AI Service from
ingress to response, covering every major processing stage.

Overview
========

A typical request traverses the following stages:

.. mermaid::

   sequenceDiagram
       participant Client
       participant Filter as LoggingContextClearingFilter
       participant RCI as RequestContextInterceptor
       participant UCI as UserContextInterceptor
       participant CCS as CommonContextSetter
       participant Ctrl as Controller
       participant Svc as Service Layer
       participant SQS as SQS Queue

       Client->>Filter: HTTP Request
       Filter->>Filter: Clear stale logging context
       Filter->>RCI: doFilter → preHandle
       RCI->>RCI: Extract headers, populate RequestContext
       RCI->>UCI: preHandle
       UCI->>UCI: Resolve user identity (SLAUTH)
       UCI->>CCS: setContext()
       CCS->>CCS: Set logging MDC, metrics tags
       CCS->>Ctrl: Forward to controller
       Ctrl->>Svc: Business logic
       Svc->>SQS: Dispatch async task (optional)
       Svc-->>Ctrl: Response DTO
       Ctrl-->>Client: HTTP Response
       Note over RCI,CCS: afterCompletion: cleanup context

Stage 1 — Filter Chain
=======================

``LoggingContextClearingFilter`` (Servlet Filter)
-------------------------------------------------

The first component to touch the request.  Its sole responsibility is to
**clear any stale logging context** from the current thread, ensuring that
MDC values from a previous request on the same thread do not leak.

.. code-block:: text

   Input:  Raw HTTP request (possibly on a recycled thread)
   Output: Clean thread-local state
   Key class: interceptor/LoggingContextClearingFilter.kt

Stage 2 — Interceptor Chain
============================

Spring MVC ``HandlerInterceptor`` instances execute in registration order
(configured in ``WebMvcConfiguration``).

``RequestContextInterceptor``
-----------------------------

**preHandle**: Extracts standard headers and populates the request context:

* ``X-Cloud-Id`` → ``CloudIdContext``
* ``X-Org-Id`` → ``OrgIdContext``
* Trace / span IDs → ``LoggingContext``
* ``RequestScopedValuesInitter`` initializes all registered
  ``RequestScopedValueOwner`` instances

**afterCompletion**: Tears down request-scoped values and emits
request-level metrics (duration, status code).

``UserContextInterceptor``
--------------------------

**preHandle**: Resolves the authenticated user from the SLAUTH token in
the ``Authorization`` header.  Populates user-related context:

* User AAID
* User permissions / roles
* Tenant association

``CommonContextSetter``
-----------------------

**setContext**: Called by the interceptor chain to finalize cross-cutting
context:

* Sets MDC fields for structured logging (tenant, user, trace)
* Attaches metric tags for the current request
* Populates ``MiscellaneousRequestContextVariablesService`` with
  derived values

Stage 3 — Controller Layer
==========================

Controllers receive the fully-contextualized request.  The service has
five REST controllers:

.. list-table:: Controller Endpoints
   :header-rows: 1
   :widths: 30 20 50

   * - Controller
     - Base Path
     - Responsibility
   * - ``NudgeThrottleController``
     - ``/nudge``
     - Nudge throttle check and state management
   * - ``RovoInsightsController``
     - ``/rovo-insights``
     - Insight fetch, status queries
   * - ``RovoInsightsTestController``
     - ``/rovo-insights/test``
     - Test-mode insight generation
   * - ``StratusTestController``
     - ``/stratus``
     - AI Gateway integration test endpoint
   * - ``WebServiceController``
     - ``/``
     - Health check and sample response

Stage 4 — Service Layer
========================

Controllers delegate to service interfaces:

* ``FeatureService`` — evaluates feature gates before executing logic
* ``AIGatewayService`` — orchestrates calls to the AI Gateway
* ``AsyncTaskService`` — dispatches work to SQS for async processing
* ``MetricsService`` / ``CoreMetricsService`` — emits business and
  infrastructure metrics
* ``IdGatekeeperClient`` — resolves user identity and audience membership

Stage 5 — Async Task Dispatch (Optional)
=========================================

For long-running operations (e.g., Rovo Insights generation), the service
dispatches tasks to SQS rather than processing synchronously:

.. code-block:: text

   Controller → AsyncTaskService.dispatch(task)
       → Serialize AsyncTaskMessage
       → Send to SQS queue (rovo_insights_generation)
       → Return 202 Accepted to client

   [On LongRun worker node]
   VisibilityExtendingSQSQueueConsumer
       → Receive message
       → Deserialize AsyncTaskMessage
       → Invoke AsyncTaskHandler.handle(task)
       → Extend visibility timeout during processing
       → Delete message on success / send to DLQ on failure

Stage 6 — SQS Consumer Processing
==================================

Two SQS consumer paths exist:

**Analytics Events** (SHWorker nodes):

.. code-block:: text

   StreamHub → SQS: analytics_events
       → AnalyticsEventsSqsQueueConsumer
       → AnalyticsEventsMessageQueueConsumer
       → MessageQueueConsumerMiddleware (enrichment)
       → AnalyticsEnrichedEventHandler (processing)

**Rovo Insights Generation** (LongRun nodes):

.. code-block:: text

   WebServer dispatch → SQS: rovo_insights_generation
       → RovoInsightsGenerationSqsQueueConsumer
       → RovoInsightsGenerationTaskHandler
       → AIGatewayService (LLM call)
       → Store/return results

Context Cleanup
===============

After the response is sent (or on error), the interceptor chain's
``afterCompletion`` methods fire in reverse order:

1. ``RequestContextInterceptor.afterCompletion`` — tears down all
   ``RequestScopedValueOwner`` registrations and emits request metrics
2. ``LoggingContextClearingFilter`` — clears MDC for thread reuse

This ensures no context leaks between requests on pooled threads.
