.. _tenant-isolation:

============================
Multi-Tenancy & Tenant Isolation
============================

The Conversational AI Platform serves **every Atlassian customer cloud** (millions of tenants). Tenant isolation is therefore non-negotiable — a bug here means cross-tenant data leakage.

The ``TenantContext`` object
=============================

Every request carries a ``TenantContext`` with at least:

- **cloud_id** — the customer's unique cloud ID
- **product_context** — which product the request originated from (jira, confluence, jsm, etc.)
- **experience_context** — the specific UX surface (ISSUE_WORK_BREAKDOWN, UNIFIED_HELP, RovoChat, etc.)
- **channel_id** (optional) — Slack/Teams channel if applicable

**Lives in:** ``modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/context/TenantContext.kt`` (verified to exist)

Resolution flow :sup:`(verified at lines)`
============================================

1. **Header parsing** (``HeaderFilter`` in ``foundation/utilities/utilities-impl/.../interceptors/HeaderFilter.kt`` — verified existence)
   - Reads ``X-Tenant-Context`` header
   - Decodes/validates
   - Stores resolved object in request attributes

2. **Controller injection** (``ChatV1Controller.kt:170``):
   - ``@RequestAttribute(TENANT_CONTEXT) tenantContext: TenantContext``
   - No re-parsing per controller — the filter ran once

3. **Async propagation** (``foundation/context/context-impl/AsyncTenantContextService.kt`` — agent-reported)
   - When a coroutine suspends, the ``TenantContext`` must travel with it
   - Implemented via ``CoroutineContextProvider`` (foundation/utilities/threading/)

4. **Downstream call enrichment** (``AIGatewayClientServiceImpl.kt:655``):
   - ``.header(AIGatewayHeaders.CLOUD_ID, aiGatewayContext.getAiGatewayCloudId())``
   - The same cloud_id propagates to AI Gateway → upstream LLM provider

Enforcement points :sup:`(observed)`
======================================

- **Experience allowlist** — ``ChatV1Controller.kt:175-179`` rejects requests whose ``tenantContext.getExperience()`` is outside an allowlist (HTTP 410 Gone). This prevents cross-experience accidental routing.

- **Agent deactivation check** — ``ChatV1Controller.kt:181-188`` looks up agent state per ``(tenantContext, user, agentId)`` triple. A deactivated agent in tenant A cannot be invoked by a request that somehow has agent A's ID but tenant B's context.

- **Logging context** — every log line includes cloud_id, experience_id, channel_id (when present). MDC keys are set up by ``HeaderFilter`` and survive coroutine boundaries via ``MdcLoggingContext``.

Patterns
=========

1. **Resolve once.** ``TenantContext`` is parsed in a Spring filter, NOT in each controller. Re-parsing would be wasteful (and risk drift between filter and controller decoders).

2. **Inject via attribute.** Controllers receive ``TenantContext`` via ``@RequestAttribute``. They do not look at headers directly.

3. **Coroutine-safe.** Suspend functions that fork onto IO dispatchers must use ``CoroutineContextProvider`` (or ``withRequestAttributesContext { }`` for GraphQL — AGENTS.md line 31). Raw ``Dispatchers.IO`` is forbidden because it loses the request context.

4. **Tenant key in every metric.** ``PlatformMetricTagsService`` tags every metric with cloud_id (subject to high-cardinality controls). See :ref:`telemetry`.

5. **Tenant key in every audit log.** Structured logs include cloud_id at MDC level — never log tenant data without this key.

What you would change here
===========================

- **Add a new field to TenantContext** → modify TenantContext.kt + propagate through HeaderFilter and async services
- **Tighten an experience allowlist** → modify the relevant controller's allowlist set

What you would NOT change here
===============================

- Per-product tenant logic (product-tier responsibility)
- LLM-specific tenant attribution (handled by AI Gateway service)

