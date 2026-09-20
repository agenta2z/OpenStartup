.. _mod-convo-ai-service:

==============================================
``service/convo-ai-service``
==============================================

:Tier: service
:Path: ``modules/service/convo-ai-service``
:Size: ~44,948 source lines :sup:`(verified by line-count)`
:Importance: **Tier 1 — assembly point**

This is the **assembly point** of the entire codebase. It contains REST/GraphQL controllers, SQS handlers, admin services, and the bootstrap-coordination code that wires every other module into a runnable service. It depends on most other modules; nothing else depends on it.

Top-level packages :sup:`(verified by directory listing)`
============================================================

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Package
     - Role
   * - ``acf``
     - Assurance Capability Framework — quality assurance / safety machinery
   * - ``admin``
     - Admin services (org admin, studio admin)
   * - ``asap``
     - ASAP authentication helpers (token caching, validation)
   * - ``common``
     - Shared utilities (content retrieval, schema, elevate model)
   * - ``config``
     - Spring configuration (component scans, bean definitions)
   * - ``domain``
     - Cross-cutting domain types
   * - ``graphql``
     - GraphQL gateway / resolvers
   * - ``IndexController.kt``
     - Top-level index/health endpoint
   * - ``micros``
     - Micros-platform integrations (lifecycle, deploy)
   * - ``permission``
     - Permission service (resource access checks)
   * - ``rest``
     - **REST controllers (v1, v2)** — the HTTP entry points
   * - ``service``
     - Internal services (Redis, ERS, SQS/Aqui queues, object store, GraphQL observability, store/migration)
   * - ``uts``
     - User-tenant-something (likely user/tenant utilities)

Key sub-packages
=================

* ``rest/v1/`` — versioned REST APIs (e.g. ``ChatV1Controller.kt`` — verified, 13 endpoints)
* ``rest/v2/perms/`` — v2 permissions API
* ``rest/v2/prompt/`` — v2 prompt API
* ``service/sqs/queue/`` — SQS queue configuration
* ``service/sqs/queue/aqui/`` — Aqui task framework wiring
* ``service/store/versioningmigration/`` — schema versioning + migration
* ``common/contentretrieval/`` — content fetching utilities (Confluence, Jira, etc.)
* ``service/graphql/observability/`` — GraphQL metric/tracing instrumentation
* ``service/graphql/subscription/`` — GraphQL subscription support

Patterns specific to convo-ai-service
=======================================

1. **Aggregate-but-don't-implement.** This module wires everything together but keeps business logic minimal. Most code is composition.
2. **Versioned REST.** ``rest/v1/`` and ``rest/v2/`` coexist. New endpoints generally go in v2; v1 is maintained for backward compat.
3. **GraphQL alongside REST.** Both surfaces are first-class. Streaming uses REST (ndjson); structured queries prefer GraphQL.
4. **Per-product config beans.** Each product's beans are scanned via Application.kt's ``scanBasePackages`` enumeration.
5. **Admin services are isolated.** ``admin/`` has its own auth gates (only admin tokens may access).

What you would change here
============================

* **Add a new REST endpoint** → new method in existing controller in ``rest/v2/<area>/`` OR new controller
* **Add a GraphQL query/mutation** → new resolver in ``graphql/<area>/`` (don't forget ``withRequestAttributesContext { }``)
* **Add a new SQS queue** → register in ``service/sqs/queue/`` + bean for handler
* **Add an admin-only operation** → ``admin/`` package; ensure admin auth gate

What you would NOT change here
================================

* LLM provider mechanics (``platform/service/service-impl``)
* Per-product business logic (``product/<name>``)
* Tenant/identity primitives (``foundation/utilities``)

