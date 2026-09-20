.. _pai-request-context-and-mdc:

============================================================================
Request Context, MDC, and Coroutine Propagation
============================================================================

:Date: 2026-05-04

This chapter is the single source of truth for how PAI keeps a "logical request"
identifiable across HTTP threads, coroutine dispatchers, async executor
hand-offs, and SQS workers.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. The four kinds of context PAI tracks
==========================================

.. list-table::
   :header-rows: 1
   :widths: 25 22 53

   * - Kind
     - Backed by
     - What it carries
   * - **MDC** (logging)
     - SLF4J ``MDC``
     - ``request_id``, ``tenant_id``, ``account_id``, ``org_id``, ``trace_id``
   * - **Request-scoped values**
     - Custom thread-locals via ``RequestScopedValue<T>``
     - Misc per-request values not appropriate for MDC (e.g. feature-flag evaluation tracker, full ``UserImpl`` reference)
   * - **Spring RequestAttributes**
     - ``ServletRequestAttributes``
     - HTTP request/response references; ``@RequestAttribute(USER)`` reads from here
   * - **Domain context**
     - ``TenantContext`` / ``ProductContext`` / ``ExperienceContext``
     - Business semantics (which product, which workspace, which use-case)

2. Setup at request entry
============================

``RequestContextInterceptor`` (order 1) calls
``RequestScopedValuesInitter.setupRequestScopedValues()`` which iterates every
registered ``RequestScopedValueOwner`` and seeds its thread-local. This validates
**at startup time** that every owner is present (``RequestScopedValueOwners``
collects them all and fails fast on duplicates / gaps).

Then ``CommonContextSetterImpl.setRequest()`` populates:

* ``LoggingContextImpl`` — adds ``request_id`` and the *limited* (no-tenant-yet) MDC keys
* ``FeatureFlagContextService`` — adds the limited Statsig context (account_id from SLAuth header, hostname from X-Forwarded-Host)
* ``MiscellaneousRequestContextVariablesService`` — captures X-Forwarded-For, X-Forwarded-Host, X-Request-ID

``UserContextInterceptor`` (order 2) reads ``X-Slauth-User-Context``, hydrates
``UserImpl``, stores it as a request attribute so controllers can inject it via
``@RequestAttribute(USER) user: User``.

3. The "limited" vs "full" context distinction
================================================

PAI cannot know the tenant_id at the very start of a request — it arrives in
the body or in ``atl-cloud-id`` header which the controller reads. So the team
distinguishes:

* **Limited context** — set by interceptor [1]. Has account_id from SLAuth, hostname.
  Used by ``FeatureService.checkGateWithLimitedContext()`` for early-request flags.
* **Full context** — set by the controller via ``CommonContextSetter.setTenant(cloudId, ...)``.
  Adds ``tenant_id`` and ``org_id`` to MDC, upgrades the Statsig context.

**Anti-pattern:** calling ``checkGate()`` (the full-context variant) before
``setTenant()`` runs will produce wrong evaluations. Linter / unit tests should
catch this; in practice it's caught at code review.

4. Teardown
===============

``LoggingContextClearingFilter`` runs after the response is committed. It calls
``MDC.clear()`` and removes the registered request-scoped value thread-locals.
Without this, the next request on the same thread would inherit stale tenant_id.

5. Coroutine propagation
============================

When a controller launches a coroutine, two ``CoroutineContext.Element``\\s
must be on the context for MDC + RequestAttributes to survive thread switches:

.. code-block:: kotlin

   import kotlinx.coroutines.slf4j.MDCContext
   import io.atlassian.micros.proactiveai.utility.threading.RequestAttributesCoroutineContext

   suspend fun handle() = withContext(
       Dispatchers.IO
       + MDCContext()
       + RequestAttributesCoroutineContext.fromCurrent()
   ) {
       // MDC + RequestAttributes preserved here
   }

For coroutines that **outlive the response** (rare in PAI today), use the
async-only mode of ``RequestAttributesCoroutineContext`` which copies the
attributes instead of holding a reference to the (soon-disposed) servlet
request:

.. code-block:: kotlin

   RequestAttributesCoroutineContext.fromCurrentAsyncOnly()

6. Async-task replay
=========================

For async tasks (SQS-driven), there is no servlet request to capture. Instead:

* Producer: ``AsyncTaskExecutionContext`` is built explicitly from MDC + the
  authenticated user.
* Producer: ``AsyncTaskServiceImpl`` packs context fields into SQS message
  attributes (``tenant_id``, ``request_id``, ``account_id``, ``user_email``).
* Consumer: ``MessageQueueConsumerMiddleware`` calls
  ``LoggingContext.addAsyncTaskContext(messageAttributes)`` which rebuilds the
  MDC before the handler runs.

Same MDC keys, same Splunk search syntax — the WebServer and the LongRun pod's
log lines join on ``request_id``.

7. Test strategy
=====================

* **Unit tests** for each ``RequestScopedValueOwner`` to verify setup +
  teardown idempotency.
* **``RequestScopedValuesInitterTest``** verifies the startup-time validation.
* **``CommonContextSetterTest``** + ``UserContextInterceptorTest`` +
  ``RequestContextInterceptorTest`` exercise the full request entry.
* **``LoggingContextClearingFilterTest``** verifies post-response cleanup.
* Coroutine context propagation has **no dedicated test** today — the
  :doc:`/overviews/03-criticality-dashboard` §4 calls this gap out.

See :doc:`/modules/platform/requestcontext` and
:doc:`/modules/platform/interceptor` for per-file detail.
