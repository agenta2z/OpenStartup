=====================================================
Module: ``interceptor`` — HTTP Request Interceptors
=====================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Implements the Spring MVC interceptor chain that bootstraps per-request context
before any controller executes.  The chain clears stale MDC state, initialises
request-scoped values, extracts tenant/user identity, and sets up feature-flag
evaluation context.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``CommonContextSetter.kt``
     - 57
     - Interfaces for context-setting contract
   * - ``LoggingContextClearingFilter.kt``
     - 62
     - ``@Component`` servlet filter — clears MDC on entry
   * - ``RequestContextInterceptor.kt``
     - 44
     - ``@Component`` — main interceptor: scoped values + context
   * - ``UserContextInterceptor.kt``
     - 75
     - ``@Component`` — extracts ``User`` from headers
   * - ``internal/CommonContextSetterImpl.kt``
     - 57
     - ``@Component`` — orchestrates all context-setting steps

**Total: 5 files, ~295 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``CommonContextSetter`` — public API:
  ``setRequest(HttpServletRequest, TenantContext)``,
  ``setLoggingContext(HttpServletRequest, TenantContext)``,
  ``setTenant(HttpServletRequest, TenantContext)``.
  Each method has overloads accepting request-only or request+tenant.
* ``CommonContextSetterForInterceptors`` — extends ``CommonContextSetter``
  with interceptor-specific overloads used by ``RequestContextInterceptor``.

Classes
-------

* ``LoggingContextClearingFilter`` (``@Component``,
  ``@Order(HIGHEST_PRECEDENCE + 4)``) — servlet ``Filter`` that:

  1. Clears MDC.
  2. Sets ``traceId`` from W3C ``Baggage`` / ``Span``.
  3. Delegates to ``FilterChain``.

* ``RequestContextInterceptor`` (``@Component``,
  ``HandlerInterceptor``) —

  - ``preHandle``: calls ``RequestScopedValuesInitter.setupRequestScopedValues()``
    then ``CommonContextSetterForInterceptors.setRequest(request)``.
  - ``afterCompletion``: calls ``LoggingContext.clear()``.

* ``UserContextInterceptor`` (``@Component``,
  ``HandlerInterceptor``) —

  - ``preHandle``: builds ``UserImpl`` and ``ExtraContextImpl`` from request
    headers, stores as request attribute.

* ``CommonContextSetterImpl`` (``@Component``) — coordinates:

  1. ``RequestContextExtractor`` → extract product/experience/cloud-id.
  2. ``LoggingContext.setFromRequest()`` → write MDC.
  3. ``MiscellaneousRequestContextVariablesService.setFromRequest()``.
  4. ``FeatureFlagContextService.setFromRequest()``.
  5. ``LoggingContext.addTenantContext()``.

Spring Component Annotations
=============================

=========================================== ========================
Bean                                        Annotation
=========================================== ========================
``LoggingContextClearingFilter``             ``@Component @Order``
``RequestContextInterceptor``               ``@Component``
``UserContextInterceptor``                  ``@Component``
``CommonContextSetterImpl``                 ``@Component``
=========================================== ========================

Registration: ``WebMvcConfiguration.addInterceptors()`` registers
``RequestContextInterceptor`` and ``UserContextInterceptor`` in order.

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[HTTP Request] --> B["LoggingContextClearingFilter
       (Servlet Filter, order=HIGHEST+4)"]
       B -->|MDC.clear, set traceId| C["RequestContextInterceptor #1
       .preHandle()"]
       C --> C1[setupRequestScopedValues]
       C --> C2["CommonContextSetter.setRequest
       extract cloudId, product, setLoggingContext,
       setFeatureFlags, setMiscVars"]
       C1 & C2 --> D["UserContextInterceptor #2
       .preHandle()"]
       D -->|parse User-Context header, build UserImpl| E[Controller method executes]
       E --> F["RequestContextInterceptor
       .afterCompletion()"]
       F --> G[LoggingContext.clear]

Configuration Knobs
===================

* Interceptor URL patterns are configured in
  ``WebMvcConfiguration.addInterceptors()`` (see ``config`` module).
* ``LoggingContextClearingFilter`` order: ``Ordered.HIGHEST_PRECEDENCE + 4``
  (hard-coded; runs before Spring Security filters).

Testing Coverage
================

=========================================== ============================
Test class                                   Subjects
=========================================== ============================
``RequestContextInterceptorTest``            preHandle / afterCompletion
``UserContextInterceptorTest``               User header parsing
``LoggingContextClearingFilterTest``          MDC clearing, traceId
``CommonContextSetterTest``                  Orchestration of sub-setters
=========================================== ============================

**Coverage: 4/5 files** — all public classes are directly tested.

Dependencies
============

Inbound (consumed by)
---------------------

* ``config/WebMvcConfiguration`` — registers interceptors.
* All controllers — benefit from pre-set context.

Outbound (depends on)
---------------------

* ``requestcontext`` — ``RequestScopedValuesInitter``,
  ``RequestContextExtractor``, ``LoggingContext``, ``MiscVarsService``.
* ``featuregate`` — ``FeatureFlagContextService``.
* ``utility/user`` — ``UserImpl``, ``ExtraContextImpl``.
* ``context`` — ``TenantContext``.
* Spring Web — ``HandlerInterceptor``, ``Filter``.
* Micrometer Tracing — ``Baggage``, ``Span``.

Open Questions / Ambiguities
=============================

1. ``LoggingContextClearingFilter`` uses ``@Order(HIGHEST_PRECEDENCE + 4)``
   — the ``+4`` offset is undocumented; what occupies +1 through +3?
2. ``UserContextInterceptor`` builds ``UserImpl`` inline rather than
   delegating to a factory — makes testing straightforward but couples
   header parsing to the interceptor.
3. If ``X-Cloud-Id`` is missing, ``RequestContextExtractor`` may throw
   ``CloudIdMissingException`` during ``preHandle`` — callers must handle
   this via ``@ControllerAdvice`` or similar.
