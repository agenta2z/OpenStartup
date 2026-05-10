.. _mod-context-api:

==============================================
``foundation/context/context-api``
==============================================

:Tier: foundation
:Path: ``modules/foundation/context/context-api``
:Importance: **Tier 2 — small but central**

Lightweight contracts for tenant context propagation across thread / coroutine boundaries.

Public surface :sup:`(inferred from naming + agent investigation)`
====================================================================

* ``TenantContextService`` — resolve the current TenantContext
* ``AsyncTenantContextService`` — coroutine-safe variant
* ``TcsService`` — TCS (Tenant Context Service) integration

Dependencies :sup:`(verified via build.gradle.kts)`
=====================================================

* ``foundation/utilities-api``
* TCS starter (Atlassian internal)
* Jackson

Patterns
==========

1. **No Spring deps.** Pure interface module.
2. **TCS-backed.** Tenant context lookups eventually go through TCS.
3. **Async variant exposed in -api.** Coroutine-safe contract is part of the public surface, not impl-internal.

What you would change here
============================

* Add a new tenant-context field → modify ``TenantContext`` data class
* Add a new context-resolution operation → extend ``TenantContextService``

