=======================================================
Module: ``requestcontext`` — Request-Scoped Value Store
=======================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Manages per-request state that must survive across interceptors, controllers,
and async continuations.  Provides a typed, key-based value store backed by
Spring ``RequestAttributes``, MDC-aware logging context, and header extraction
utilities.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``HeaderConstants.kt``
     - 5
     - Well-known HTTP header names
   * - ``LoggingContext.kt``
     - 75
     - Interface — MDC/tenant-aware logging context
   * - ``LoggingContextExtensions.kt``
     - 37
     - Inline extension fns for ``LoggingContext``
   * - ``MiscellaneousRequestContextVariablesService.kt``
     - 84
     - ``@Service`` — request-id / X-Forwarded-* extraction
   * - ``RequestAttributes.kt``
     - 13
     - Attribute key constants
   * - ``RequestContextValues.kt``
     - 213
     - Core extractors & ``RequestScopedValue`` / ``RequestScopedValueService`` interfaces
   * - ``RequestScopedValueKey.kt``
     - 21
     - Enum of all scoped-value keys
   * - ``RequestScopedValueOwner.kt``
     - 18
     - Generic owner interface ``<T>``
   * - ``RequestScopedValueOwners.kt``
     - 27
     - ``@Component`` — registry of all owners
   * - ``RequestScopedValuesInitter.kt``
     - 22
     - Interface — bootstrap scoped values per request
   * - ``SetContextUndo.kt``
     - 9
     - Undo-token interface for context mutations
   * - ``internal/LoggingContextImpl.kt``
     - 227
     - ``@Component`` — MDC-backed implementation
   * - ``internal/RequestScopedValueServiceImpl.kt``
     - 123
     - ``@Component`` — Spring-attribute-backed value store
   * - ``internal/RequestScopedValuesInitterImpl.kt``
     - 32
     - ``@Component`` — wires ``RequestAttributes`` for async

**Total: 14 files, ~906 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``LoggingContext`` — MDC lifecycle: ``runWithContext``, ``addTenantContext``,
  ``addStreamHubEventInfo``, ``addAsyncTaskContext``, ``setFromRequest``,
  ``getRequestId``, ``clear``.
* ``RequestScopedValue<T>`` — typed value stored in request scope.
* ``RequestScopedValueService`` — get/set/update scoped values by key.
* ``RequestScopedValueOwner<T>`` — declares a key, empty-value factory, and
  Java type for one scoped value.
* ``RequestScopedValuesInitter`` — ``setupRequestScopedValues()`` /
  ``initRequestScopedValuesAndRun(Runnable)``.
* ``SetContextUndo`` — single method ``revert()`` for stack-based undo.
* ``RequestIdGetter`` / ``XForwardedForGetter`` / ``XForwardedHostGetter`` —
  accessor interfaces implemented by ``MiscellaneousRequestContextVariablesService``.

Classes
-------

* ``RequestContextExtractor`` (object) — static helpers that pull cloud-id,
  product, experience, org-id, etc. from ``HttpServletRequest``.
* ``MiscellaneousRequestContextVariablesService`` (``@Service``) — extracts
  ``X-Request-Id``, ``X-Forwarded-For``, ``X-Forwarded-Host``.
* ``RequestScopedValueOwners`` (``@Component``) — injects all
  ``RequestScopedValueOwner`` beans, exposes ``getOwners()``.
* ``LoggingContextImpl`` (``@Component``) — MDC-backed ``LoggingContext``; uses
  ``LogKey`` enum for MDC key names.
* ``RequestScopedValueServiceImpl`` (``@Component``) — stores values in
  ``RequestAttributes`` via Spring ``RequestContextHolder``.
* ``RequestScopedValuesInitterImpl`` (``@Component``) — sets up
  ``RequestAttributesForAsyncProcessing`` for async threads.

Data Classes
------------

* ``MiscellaneousRequestContextVariables`` — request-id, forwarded headers.
* ``ProductContextValues``, ``ExperienceValuesFromRequest``,
  ``OldAndNewValue<T>`` — extracted request parameters.

Exceptions
----------

* ``CloudIdMissingException``, ``MismatchingCloudIdParametersException``.

Enums
-----

* ``RequestScopedValueKey`` — ``FEATURE_FLAG_CONTEXT``,
  ``FEATURE_FLAG_EVALUATION_TRACKER``, ``MISC_VARS``, etc.
* ``LogKey`` (internal) — MDC key constants.

Spring Component Annotations
=============================

=============================================== =====================
Bean                                            Annotation
=============================================== =====================
``MiscellaneousRequestContextVariablesService``  ``@Service``
``RequestScopedValueOwners``                     ``@Component``
``LoggingContextImpl``                           ``@Component``
``RequestScopedValueServiceImpl``                ``@Component``
``RequestScopedValuesInitterImpl``               ``@Component``
=============================================== =====================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[Incoming HTTP Request] --> B[LoggingContextClearingFilter]
       B -->|clears MDC, sets traceId| C[RequestContextInterceptor.preHandle]
       C --> D[RequestScopedValuesInitter.setupRequestScopedValues]
       C --> E[CommonContextSetter.setRequest]
       E --> F[RequestContextExtractor: extract cloudId, product]
       E --> G[LoggingContext.setFromRequest: write MDC]
       E --> H[MiscVarsService.setFromRequest]
       E --> I[FeatureFlagContextService.setFromRequest]
       D & F & G & H & I --> J[Controller / Service]
       J -->|reads via RequestScopedValueService & LoggingContext| K[RequestContextInterceptor.afterCompletion]
       K --> L[LoggingContext.clear]

Configuration Knobs
===================

This module reads no direct YAML properties but reacts to:

* ``spring.profiles.active`` (indirectly via ``Environment`` in
  ``RequestScopedValueServiceImpl`` for debug logging).
* HTTP headers: ``X-Request-Id``, ``X-Forwarded-For``, ``X-Forwarded-Host``,
  ``X-Cloud-Id``, ``X-Product``, ``X-Experience``, ``X-Org-Id``.

Testing Coverage
================

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - Test class
     - Lines
     - Subjects
   * - ``MiscellaneousRequestContextVariablesServiceTest``
     - —
     - MiscVarsService extraction
   * - ``RequestScopedValuesInitterTest``
     - —
     - Initter lifecycle

**Gap:** ``LoggingContextImpl`` and ``RequestScopedValueServiceImpl`` have no
dedicated unit tests (covered indirectly through interceptor tests).

Dependencies
============

Inbound (consumed by)
---------------------

* ``interceptor`` — ``RequestContextInterceptor`` drives the lifecycle.
* ``logging`` — ``LaasLogger`` reads ``LoggingContext``.
* ``featuregate`` — ``FeatureFlagContextServiceImpl`` is a
  ``RequestScopedValueOwner``.
* ``sqs`` / ``task`` — async consumers call ``LoggingContext.addAsyncTaskContext``.

Outbound (depends on)
---------------------

* ``context`` — ``TenantContext``, ``CloudId`` type aliases.
* ``utility/threading`` — ``RequestAttributesForAsyncProcessing``.
* Spring Framework — ``RequestContextHolder``, ``RequestAttributes``.
* SLF4J MDC — for structured-logging propagation.

Open Questions / Ambiguities
=============================

1. ``RequestContextValues.kt`` at 213 LoC mixes data classes, extractors, and
   interface definitions — candidate for split.
2. ``CloudIdMissingException`` vs ``MismatchingCloudIdParametersException`` are
   not ``@ResponseStatus``-annotated; error mapping relies on global handler.
3. The ``SetContextUndo`` pattern is used in featuregate but never in this
   module directly — circular awareness or leftover design?
4. ``LoggingContextImpl`` enum ``LogKey`` duplicates some keys also present in
   ``HeaderConstants`` — potential drift risk.
