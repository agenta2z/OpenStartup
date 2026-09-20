=============================================
Module: ``exception`` — REST Exception Types
=============================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Defines a hierarchy of HTTP-status-mapped exception classes used for outbound
REST client error handling and inbound controller error responses.  Each
exception carries an ``HttpStatus``, a message, and a configurable log level.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``RestClientException.kt``
     - 116
     - Full exception hierarchy + ``ExceptionLogLevel`` enum

**Total: 1 file, ~116 LoC**

Class / Interface / Enum Catalog
================================

Exception Hierarchy
-------------------

::

  RuntimeException
    └── RestException(message, cause)
          ├── RestClientException(message, status: HttpStatus, cause, logLevel)
          └── RestServerException(message, status: HttpStatus)
                ├── UnauthorizedException        (401)
                ├── ForbiddenException            (403)
                ├── NotFoundException             (404)
                ├── BadRequestException           (400)
                ├── NotAcceptableException         (406)
                ├── PayloadTooLargeException       (413)
                ├── GoneException                 (410)
                ├── IAmATeapotException            (418)
                ├── InternalServerErrorException   (500)
                ├── OpenAIRateLimitRestException   (429 — AI-specific)
                └── PlatformRateLimitException     (429 — platform-wide)

Enums
-----

* ``ExceptionLogLevel`` — ``ERROR``, ``WARN``, ``INFO``, ``DEBUG``.
  Used by ``RestClientException`` to let callers control how the exception is
  logged when caught by global error handlers.

Key Design Decisions
--------------------

* ``RestClientException`` is for **outbound** errors — when this service calls
  an upstream and receives an error response.  It stores the upstream
  ``HttpStatus`` and an ``ExceptionLogLevel``.

* ``RestServerException`` and its subclasses are for **inbound** errors —
  thrown by controllers / services to produce the corresponding HTTP response.

* Two separate 429 exceptions:

  - ``OpenAIRateLimitRestException`` — for AI Gateway / LLM rate limits.
  - ``PlatformRateLimitException`` — for Atlassian platform rate limits.

  This allows error handlers to apply different retry/backoff strategies.

Spring Component Annotations
=============================

None — pure domain exception types with no Spring annotations.

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       subgraph Outbound Error Path
           A1[Upstream service call] -->|HTTP 4xx/5xx| B1[Client implementation]
           B1 -->|throw RestClientException with status, logLevel| C1[Global exception handler]
           C1 -->|logs at specified logLevel| D1[Maps to HTTP response]
       end
       subgraph Inbound Error Path
           A2[Controller / Service code] -->|throw BadRequestException| B2["Spring @ControllerAdvice"]
           B2 --> C2[HTTP 400 response]
       end

Configuration Knobs
===================

None — exception types are static.

Testing Coverage
================

No dedicated test file exists for ``RestClientException.kt``.

Coverage is achieved indirectly:

* ``AsyncIdGatekeeperClientTest`` — verifies that HTTP error responses are
  mapped to correct ``RestClientException`` subclasses / identity-specific
  exceptions.
* ``NudgeThrottleControllerAcceptanceTest`` — verifies ``BadRequestException``
  handling.

**Gap:** No unit test directly verifies the ``ExceptionLogLevel`` propagation
or the distinction between ``OpenAIRateLimitRestException`` and
``PlatformRateLimitException``.

Dependencies
============

Inbound (consumed by)
---------------------

* ``client/identity`` — ``IdentityClientException`` extends
  ``RestClientException``.
* ``requestcontext`` — ``BadRequestException`` thrown by extractors.
* ``context`` — ``ExperienceIdNotFoundException`` (separate exception but same
  pattern).
* ``integration/stratus`` — AI Gateway error mapping.
* Controllers — throw ``RestServerException`` subclasses for HTTP responses.

Outbound (depends on)
---------------------

* ``org.springframework.http.HttpStatus`` — status code constants.
* Kotlin stdlib — ``RuntimeException``.

Open Questions / Ambiguities
=============================

1. ``RestClientException`` vs ``RestServerException`` naming is from the
   *service's perspective* (client = outbound, server = inbound) — but could
   confuse readers who think "client" means "the HTTP client calling us".
2. ``IAmATeapotException`` (418) is present — likely used for testing or
   sentinel purposes; confirm whether it appears in production code paths.
3. Two 429 exceptions (``OpenAIRateLimitRestException``,
   ``PlatformRateLimitException``) — no shared interface or marker for
   "rate limit" categorisation; callers must catch both individually.
4. The ``logLevel`` field on ``RestClientException`` is advisory — actual
   logging depends on the catching code respecting it.  No framework
   enforcement exists.
