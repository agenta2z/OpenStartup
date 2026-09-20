.. _mod-agent-version-api:

==============================================
``platform/agent-version/agent-version-api``
==============================================

:Tier: platform
:Path: ``modules/platform/agent-version/agent-version-api``
:Size: ~879 source lines :sup:`(verified)`

Versioning contracts for **agent definitions**. Backs AgentStudio's "publish v3 of agent X" flow + the schema-validation that rejects malformed publishes.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Concept
   * - ``AgentVersionStore.kt``
     - 178
     - Versioned-storage interface
   * - ``RovoAgentVersionConfig.kt``
     - 172
     - Rovo-specific config schema
   * - ``AgentVersioningService.kt``
     - 113
     - Top-level version service
   * - ``AgentVersionIdentifier.kt``
     - 58
     - Versioned ID type

Key public contracts
======================

* ``interface AgentVersionStore`` — CRUD over versioned agent definitions
* ``interface AgentVersioningService`` — version creation, promotion, rollback
* ``interface SchemaJsonGenerator`` — produces JSON schemas for validation
* ``object VersionedIdGenerator`` — utility for generating versioned IDs
* ``class AgentVersionSchemaValidationException`` — schema-validation error type

Notable findings
==================

* ``RovoAgentVersionConfig.kt`` (172 lines) is **product-specific** schema in a platform-tier module. This is mildly suspect — it suggests Rovo-specific concepts have leaked upward. Worth checking whether it should move to product/rovo.
* ``VersionedIdGenerator`` is an ``object`` (Kotlin singleton) — utility-style, no DI.

