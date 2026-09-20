.. _pai-platform-client:

============================================================================
``client`` — HTTP client commons + IdGatekeeper
============================================================================

:Date: 2026-05-04
:Files: 7 main (2 in ``client/`` + 3 in ``client/identity/`` + 2 in ``client/identity/internal/``) / 2 test
:Importance: **P2 — outbound HTTP constants + user-enrichment integration**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Two responsibilities in one package:

1. **HTTP header constants** (``HttpClientCommons``) — canonical names for every
   header PAI reads or writes, used across interceptors, controllers, and
   outbound clients.
2. **IdGatekeeper integration** (``identity/``) — user-enrichment lookups
   (e.g. fetching email from account_id) in both sync and coroutine-native
   flavours.

The package also defines the ``Audiences`` object listing every SLAuth audience
PAI uses for outbound calls.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``HttpClientCommons.kt``
     - ~15
     - Shared HTTP header constants (object)
   * - ``Audiences.kt``
     - ~8
     - SLAuth audience constants (object)
   * - ``identity/IdGatekeeperClient.kt``
     - ~8
     - Sync permission-check interface
   * - ``identity/AsyncIdGatekeeperClient.kt``
     - ~25
     - Coroutine-native permission-check interface + ``Permissions`` + ``PrincipalFilter``
   * - ``identity/IdGatekeeperClientImpl.kt``
     - ~50
     - Sync (blocking-future) implementation
   * - ``identity/internal/AsyncIdGatekeeperClientImpl.kt``
     - ~60
     - Coroutine-native implementation

3. Key classes & interfaces
===============================

``HttpClientCommons`` (object)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Central constant pool for HTTP header names:

.. code-block:: kotlin

   object HttpClientCommons {
       const val HOST = "Host"
       const val X_FORWARDED_HOST = "X-Forwarded-Host"
       const val X_FORWARDED_FOR = "X-Forwarded-For"
       const val X_SLAUTH_EGRESS_HEADER = "X-Slauth-Egress"
       const val X_SLAUTH_AUDIENCE_HEADER = "X-Slauth-Audience"
       const val X_SLAUTH_USER_CONTEXT_ACCOUNT_ID = "X-Slauth-User-Context-Account-Id"
       const val USER_CONTEXT = "User-Context"
       const val ATL_CLOUD_ID = "atl-cloudid"
       const val ATL_WORKSPACE_ID = "Atl-WorkspaceId"
       const val X_NO_USER_ID_HEADER = "X-Requested-No-User-Id"
       const val X_REQUEST_ID = "X-Request-Id"
   }

Every interceptor, controller, and outbound client references these constants
instead of string literals — a single rename propagates everywhere.

``Audiences`` (object)
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   object Audiences {
       const val AI_GATEWAY = "ai-gateway"
       const val CONVO_AI = "convo-ai"
       const val INTEGRATIONS_SERVICE = "integrations-service"
       const val IDENTITY_PLATFORM = "identity-platform"
   }

Adding a new outbound dependency requires:

1. Add the audience constant here.
2. Configure the endpoint in ``service-descriptor.sd.yml`` under ``mesh:``.
3. Wire SLAuth client middleware into the new HTTP client bean.

``IdGatekeeperClient`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sync permission-check API:

* ``checkPermissionBulk(requests: List<PermissionRequest>): List<PermissionResult>``
* ``checkPermission(request: PermissionRequest): Boolean``

``AsyncIdGatekeeperClient`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Coroutine-native variant with ``suspend`` methods:

* ``suspend fun checkPermissionBulk(requests: List<PermissionRequest>): List<PermissionResult>``
* ``suspend fun checkPermission(request: PermissionRequest): Boolean``

Also defines:

* ``Permissions.GENERATIVE_AI_RBAC_PERMISSION = "read:features:ai"``
* ``PrincipalFilter`` enum: ``USER("arm:cloud:identity::user/.+")``,
  ``GROUP("arm:cloud:identity::group/.+")``

**Design guidance:** Prefer ``AsyncIdGatekeeperClient`` unless you are inside a
hard-blocking callsite (e.g. a synchronous ``@Bean`` initialiser).

4. Class hierarchy
=====================

.. code-block:: text

   IdGatekeeperClient (interface)
   └── IdGatekeeperClientImpl — sync, blocks on CompletableFuture

   AsyncIdGatekeeperClient (interface)
   └── AsyncIdGatekeeperClientImpl — coroutine-native suspend API

Both interfaces share the same method signatures (``checkPermission``,
``checkPermissionBulk``) but differ in blocking vs suspend semantics.

5. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``IdGatekeeperClientTest``
     - Sync client: permission check + bulk permission check
   * - ``AsyncIdGatekeeperClientTest``
     - Async client: coroutine-based permission checks

6. Integration patterns
==========================

* **Used by**: ``UserContextInterceptor`` (user enrichment), controllers
  needing RBAC permission checks
* **Depends on**: IdGatekeeper external service (SLAuth-authenticated)
* **Consumed by**: :doc:`/modules/platform/interceptor` (indirectly via
  ``User`` population)

7. Design decisions
======================

1. **Two client flavours** — sync for legacy/blocking contexts, async for
   coroutine-native code. Both share the same interface contract.
2. **Constants over strings** — ``HttpClientCommons`` prevents typos in header
   names that would silently fail.
3. **RBAC permission as constant** — ``GENERATIVE_AI_RBAC_PERMISSION`` ensures
   consistent permission checking across all AI feature gates.

8. See also
==============

* :doc:`/architecture/cross-cutting/08-auth-and-tenant` — audience pattern and
  outbound-auth conventions
* :doc:`/modules/platform/interceptor` — consumes ``HttpClientCommons`` headers
* :doc:`/modules/platform/context` — ``TenantContext`` populated from headers
