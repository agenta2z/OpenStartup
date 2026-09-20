.. _pai-auth-and-tenant:

============================================================================
Auth, SLAuth, Tenant Identity
============================================================================

:Date: 2026-05-04

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Inbound auth (SLAuth server)
=================================

Every request entering PAI is signed via Atlassian's **SLAuth** (ASAP-based).
The Micros starter ``micros-spring-boot-starter-security-slauth-server``
validates the signature *before* PAI code runs and populates ``X-Slauth-*``
headers.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Header
     - Carries
   * - ``X-Slauth-User-Context``
     - Authenticated user info (account_id, email, …) — read by ``UserContextInterceptor``
   * - ``X-Slauth-Audience``
     - The intended callee (used by SLAuth for routing/audit)
   * - ``X-Slauth-Egress``
     - The caller service id (used for inter-service authorization)

Anonymous paths bypass SLAuth: ``/healthcheck`` and ``/deepcheck`` are listed
in ``MvcSecurityConfig.kt`` and Spring Security excludes them.

2. Outbound auth (SLAuth client)
==================================

Every PAI-originated HTTP call to another Atlassian service includes an
``X-Slauth-Audience`` header naming the callee. PAI's known audiences are in
``client/Audiences.kt``:

* ``AI_GATEWAY`` — for Stratus / AI Gateway calls
* ``ID_GATEKEEPER`` — for IdGatekeeper user-enrichment calls

Adding a new outbound dependency means:

1. Add the audience constant to ``Audiences.kt``.
2. Configure the dependency endpoint env-var in ``service-descriptor.sd.yml``
   under ``mesh:`` so Micros knows about it.
3. Wire SLAuth client middleware into the new HTTP client bean.

3. Tenant identity
======================

Tenant identity arrives in two ways:

* **HTTP header** ``atl-cloud-id`` — the canonical Atlassian cloud_id /
  workspace identifier. Controllers read it via ``@RequestHeader``.
* **User-derived** — the ``UserImpl`` populated from ``X-Slauth-User-Context``
  carries the user's home tenant fields.

The controller is responsible for calling
``CommonContextSetter.setTenant(cloudId, ...)`` early in its body so the rest
of the request runs with full MDC + Statsig context.

4. Tenant data shapes
========================

The ``context/`` package defines the canonical types:

* ``TenantContext`` — the aggregate, implementing four marker interfaces
* ``CloudIdContext`` / ``OrgIdContext`` — for codepaths that need only the id
* ``PlatformTenantContext`` — for codepaths that need the platform-wide tenant model
* ``AIGatewayContext`` — for codepaths that build Stratus calls (carries useCaseId)

If you need to pass tenant info as a method arg, prefer the **narrowest**
interface that satisfies your callees — keeps coupling low.

5. The IdGatekeeper integration
==================================

``client/identity/`` wraps IdGatekeeper for user-enrichment lookups (e.g.
fetching email from account_id when the SLAuth header lacks it). Two flavours:

* ``IdGatekeeperClientImpl`` — sync (blocking on a CompletableFuture)
* ``AsyncIdGatekeeperClientImpl`` — coroutine-native ``suspend`` API

Prefer the async client unless you're inside a hard-blocking callsite.

6. See also
==============

* :doc:`/modules/platform/client` — per-file detail
* :doc:`/modules/platform/context` — domain-context types
* :doc:`/modules/platform/interceptor` — UserContextInterceptor
