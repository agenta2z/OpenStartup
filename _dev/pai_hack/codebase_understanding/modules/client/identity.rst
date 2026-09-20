=====================================================
Module: ``identity`` — Identity Gatekeeper Client
=====================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Provides async and synchronous HTTP clients for the **Identity Gatekeeper**
service, which handles permission checks (RBAC) for Atlassian cloud products.
The async client is the primary implementation; the synchronous client is a
deprecated wrapper that blocks on the async result.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``AsyncIdGatekeeperClient.kt``
     - 28
     - Interface + nested ``Permissions`` object & ``PrincipalFilter`` enum
   * - ``IdGatekeeperClient.kt``
     - 8
     - ``@Deprecated`` synchronous interface
   * - ``IdGatekeeperModels.kt``
     - 81
     - Data classes: request/response models, exception types
   * - ``internal/AsyncIdGatekeeperClientImpl.kt``
     - 229
     - ``@Component`` — WebClient-based async implementation
   * - ``internal/IdGatekeeperClientImpl.kt``
     - 27
     - ``@Component @Deprecated`` — blocking wrapper

**Total: 5 files, ~373 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``AsyncIdGatekeeperClient`` — primary async API:

  - ``suspend fun checkPermissionBulk(requests: List<PermissionRequest>): List<PermissionResult>``
  - ``suspend fun checkPermission(request: PermissionRequest): Boolean``
  - Nested ``object Permissions``:
    - ``const val WRITE``
    - ``const val GENERATIVE_AI_RBAC_PERMISSION``
  - Nested ``enum class PrincipalFilter``: ``USER``, ``GROUP``

* ``IdGatekeeperClient`` (``@Deprecated``) — synchronous mirror:

  - ``fun checkPermissionBulk(requests: List<PermissionRequest>): List<PermissionResult>``
  - ``fun checkPermission(request: PermissionRequest): Boolean``

Data Classes
------------

* ``PermissionRequest`` — fields: ``permissionId``, ``principalId``,
  ``resourceId``, ``dontRequirePrincipalInSite``.  Uses ``@JsonProperty``
  for serialisation.

* ``PermissionResult`` — fields: ``permissionId``, ``principalId``,
  ``resourceId``, ``permitted: Boolean``, ``dontRequirePrincipalInSite``,
  ``error: PermissionResultError?``.

Exception Classes
-----------------

All extend ``RestClientException`` (from ``exception`` module):

* ``IdentityClientException`` — generic identity service error.
* ``IdentityClientRateLimitException`` — 429 from identity service.
* ``IdentityClientPermissionException`` — 403 from identity service.
* ``IdentityClientResourceNotFoundException`` — 404 from identity service.

Type Aliases
------------

* ``PermissionResultError = Map<ErrorType, ErrorDetails>``
* ``ErrorType = String``
* ``ErrorDetails = JsonNode``

Implementation Classes
----------------------

* ``AsyncIdGatekeeperClientImpl`` (``@Component``) — uses Spring
  ``WebClient`` for non-blocking HTTP calls:

  - Constructor: ``@Value("${id-gatekeeper.target-url}")`` for base URL.
  - ``checkPermissionBulk`` — POST to ``/v1/permission/check``, maps response
    to ``List<PermissionResult>``.
  - ``checkPermission`` — delegates to ``checkPermissionBulk`` with single
    request, returns ``permitted`` boolean.
  - ``internal fun mapErrorResponseToException(...)`` — maps HTTP status codes
    to typed exceptions (404→ResourceNotFound, 403→Permission, 429→RateLimit,
    else→IdentityClientException).
  - Private helpers: ``logIdentityError``, ``convertObjectToQueryParams``,
    ``containsNotFoundError``.

* ``IdGatekeeperClientImpl`` (``@Component``, ``@Deprecated``) — wraps
  ``AsyncIdGatekeeperClientImpl`` using ``runBlocking`` to block on suspend
  functions.

Spring Component Annotations
=============================

================================== ==========================
Bean                                Annotation
================================== ==========================
``AsyncIdGatekeeperClientImpl``     ``@Component``
``IdGatekeeperClientImpl``          ``@Component @Deprecated``
================================== ==========================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[Service code] -->|checkPermission with PermissionRequest| B[AsyncIdGatekeeperClientImpl]
       B -->|"WebClient.post /v1/permission/check
       with Slauth-Egress header"| C{HTTP Response}
       C -->|200 OK| D[PermissionResult.permitted]
       C -->|404| E[IdentityClientResourceNotFoundException]
       C -->|403| F[IdentityClientPermissionException]
       C -->|429| G[IdentityClientRateLimitException]
       C -->|other| H[IdentityClientException]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Property
     - Default
     - Description
   * - ``id-gatekeeper.target-url``
     - ``${MESH_DEPENDENCY_ID_GATEKEEPER_BASE_URL}``
     - Base URL for Identity Gatekeeper (local: ``http://localhost/``)

Testing Coverage
================

======================================= ====== ============================
Test class                               Lines  Subjects
======================================= ====== ============================
``AsyncIdGatekeeperClientTest``          541    Full coverage: success, bulk,
                                                error mapping, rate limit,
                                                404, 403, query params
``IdGatekeeperClientTest``                59    Blocking delegation
======================================= ====== ============================

**Coverage: 2/2 implementation files** — excellent test coverage.
``AsyncIdGatekeeperClientTest`` at 541 LoC is the largest test file in the
project, covering all error-mapping paths.

Dependencies
============

Inbound (consumed by)
---------------------

* ``feature/rovoinsights`` — permission checks before insight generation.
* ``feature/nudge`` — may check AI permissions before nudge delivery.
* ``integration/stratus`` — RBAC checks before AI gateway calls.

Outbound (depends on)
---------------------

* ``exception`` — ``RestClientException`` base class.
* ``client/http-commons`` — ``HttpClientCommons`` header constants,
  ``Audiences.IDENTITY_PLATFORM`` for Slauth egress.
* Spring WebFlux — ``WebClient`` for reactive HTTP.
* Jackson — ``ObjectMapper``, ``JsonNode``, ``@JsonProperty``.

Open Questions / Ambiguities
=============================

1. ``IdGatekeeperClient`` is deprecated but still has a ``@Component``
   implementation — it remains in the Spring context and could be injected
   accidentally.  Consider removing the ``@Component`` annotation.
2. ``AsyncIdGatekeeperClientImpl.mapErrorResponseToException`` is
   ``internal`` visibility — allows testing but breaks encapsulation for
   other modules in the same package.
3. The ``dontRequirePrincipalInSite`` flag on ``PermissionRequest`` is a
   boolean with an unusual name — document when it should be ``true``.
4. No retry/circuit-breaker logic — rate limit (429) exceptions propagate
   directly to callers without back-off.
