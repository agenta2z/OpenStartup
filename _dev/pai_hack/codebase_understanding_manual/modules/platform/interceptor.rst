.. _pai-platform-interceptor:

============================================================================
``interceptor`` — HTTP interceptor chain
============================================================================

:Date: 2026-05-04
:Files: 5 main / 4 test (highest test/main ratio after ``logging``)
:Importance: **P0 — every HTTP request crosses this**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Two ordered Spring ``HandlerInterceptor`` beans plus the
``CommonContextSetter`` abstraction they use, and a servlet ``Filter`` for
cleanup. Together, these four classes form the **request entry pipeline** —
every HTTP request entering PAI passes through them in order.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``RequestContextInterceptor.kt``
     - ~30
     - Order 1: request-scoped values + limited context
   * - ``UserContextInterceptor.kt``
     - ~55
     - Order 2: extracts authenticated user from SLAuth
   * - ``CommonContextSetter.kt`` (interface)
     - ~20
     - Abstraction for setting logging/feature/tenant context
   * - ``internal/CommonContextSetterImpl.kt``
     - ~60
     - Wires logging + feature-flag + misc context
   * - ``LoggingContextClearingFilter.kt``
     - ~30
     - Post-response MDC cleanup (``@Order(HIGHEST_PRECEDENCE + 4)``)

3. Request entry sequence
============================

::

   HTTP Request arrives
     │
     ▼
   LoggingContextClearingFilter (servlet Filter, outermost)
     │  • Sets trace_id, span_id from OpenTelemetry Span
     │  • Sets experimentId from OTel Baggage
     │  • try { chain.doFilter(...) } finally { loggingContext.clear() }
     │
     ▼
   RequestContextInterceptor (order 1)
     │  • Guard: skip if already invoked or ASYNC dispatch
     │  • requestScopedValuesInitter.setupRequestScopedValues()
     │  • commonContextSetter.setRequest(this, request)
     │       → LoggingContext: adds request_id, limited MDC keys
     │       → FeatureFlagContextService: limited Statsig context
     │       → MiscellaneousRequestContextVariablesService: X-Forwarded-*, X-Request-Id
     │
     ▼
   UserContextInterceptor (order 2)
     │  • Guard: skip if already invoked or ASYNC dispatch
     │  • userContextService.getUserContext(request)
     │  • Build UserImpl with ExtraContext (forwarded headers)
     │  • request.setAttribute(USER, user)
     │
     ▼
   Controller (@RequestAttribute(USER) user: User)

4. Key classes deep dive
===========================

``RequestContextInterceptor``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Component
   class RequestContextInterceptor(
       private val requestScopedValuesInitter: RequestScopedValuesInitter,
       private val commonContextSetterForInterceptors: CommonContextSetterForInterceptors,
   ) : HandlerInterceptor {
       override fun preHandle(request, response, handler): Boolean {
           if (request.getAttribute("RequestContextInterceptor.invoked") == "true"
               || DispatcherType.ASYNC == request.dispatcherType) {
               return true  // idempotency guard
           }
           request.setAttribute("RequestContextInterceptor.invoked", "true")
           requestScopedValuesInitter.setupRequestScopedValues()
           commonContextSetterForInterceptors.setRequest(this, request)
           return true
       }
   }

The idempotency guard (``"invoked"`` attribute) prevents double-setup on async
dispatches and forwarded requests.

``UserContextInterceptor``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Component
   class UserContextInterceptor(
       private val userContextService: UserContextService,
   ) : HandlerInterceptor {
       override fun preHandle(request, response, handler): Boolean {
           // ... idempotency guard ...
           val userContext = userContextService.getUserContext(request).orElse(null)
           if (userContext == null) {
               logger.infoWithContext("User context not found in request", ...)
               return true  // anonymous request — proceed without user
           }
           val user = UserImpl(userContext, ExtraContextImpl(...))
           request.setAttribute(USER, user)
           return true
       }
   }

Missing user context is **not** an error — anonymous paths (e.g. ``/healthcheck``)
have no SLAuth context. The interceptor logs and proceeds.

``CommonContextSetter`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface CommonContextSetter {
       fun setRequest(interceptor: HandlerInterceptor?, request: HttpServletRequest)
       fun setLoggingContext(accountId: String?, requestId: String?)
       fun setTenant(interceptor: HandlerInterceptor?, tenantContext: TenantContext)
   }

``setRequest()`` populates **limited** context (no tenant yet).
``setTenant()`` populates **full** context (adds tenant_id, org_id to MDC,
upgrades Statsig context). Controllers must call ``setTenant()`` early.

``LoggingContextClearingFilter``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   @Order(Ordered.HIGHEST_PRECEDENCE + 4)
   @Component
   class LoggingContextClearingFilter(
       private val loggingContext: LoggingContext,
   ) : Filter {
       override fun doFilter(request, response, chain) {
           try {
               // Set OpenTelemetry trace context into MDC
               MDC.put("trace_id", Span.current().spanContext.traceId)
               chain?.doFilter(request, response)
           } finally {
               loggingContext.clear()  // MDC.clear() + thread-local teardown
           }
       }
   }

The ``finally`` block is critical — without it, the next request on the same
thread would inherit stale ``tenant_id``.

5. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``RequestContextInterceptorTest``
     - Setup call, idempotency guard, async-dispatch skip
   * - ``UserContextInterceptorTest``
     - User extraction, missing-user handling, attribute setting
   * - ``CommonContextSetterTest``
     - Limited vs full context population
   * - ``LoggingContextClearingFilterTest``
     - MDC cleanup in finally block, trace context propagation

6. Design decisions
======================

1. **Two interceptors, strict order** — request context must be ready before
   user context extraction. Spring ``@Order`` enforces this.
2. **Idempotency guards** — prevent double-setup on Spring async dispatches
   and internal forwards.
3. **Filter for cleanup** — ``LoggingContextClearingFilter`` runs at
   ``HIGHEST_PRECEDENCE + 4`` (outermost) to guarantee cleanup even if
   interceptors or controllers throw.
4. **Graceful anonymous handling** — missing user context logs info (not warn)
   and proceeds, supporting anonymous endpoints.

7. See also
==============

* :doc:`/architecture/cross-cutting/03-request-context-and-mdc` — end-to-end
  request entry sequence
* :doc:`/modules/platform/requestcontext` — thread-locals and MDC API
* :doc:`/modules/platform/logging` — logger used by interceptors
* :doc:`/modules/platform/client` — ``HttpClientCommons`` header constants
