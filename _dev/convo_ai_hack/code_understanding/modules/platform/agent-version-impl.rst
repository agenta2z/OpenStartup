.. _mod-agent-version-impl:

==============================================
``platform/agent-version/agent-version-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/agent-version/agent-version-impl``
:Size: ~3,439 source lines :sup:`(verified)`
:Importance: Tier 2 — large impl, multiple notable subsystems

Concrete agent versioning runtime. Includes schema validation, config migration, and data compression.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``AgentVersionStoreImpl.kt``
     - 275
     - Versioned-storage backend
   * - ``AgentVersioningServiceImpl.kt``
     - 182
     - Service facade
   * - ``AgentVersionMapper.kt``
     - 148
     - Domain-to-ERS mapping
   * - ``RovoAgentVersionConfigMigrator.kt``
     - 116
     - Schema-evolution migrator

Key Spring components
=======================

* ``class AgentVersionStoreImpl`` — implements ``AgentVersionStore``
* ``class AgentVersioningServiceImpl`` — implements ``AgentVersioningService``
* ``class AgentVersionSchemaValidator`` — validates definitions against generated JSON schema
* ``class RovoAgentVersionConfigMigrator`` — migrates older config schema versions to current
* ``class SchemaJsonGeneratorImpl`` — implements ``SchemaJsonGenerator``
* ``class AgentVersionMapper`` — translates between domain types and ERS documents
* ``class AgentVersionDataCompressor`` — compresses stored definitions

Notable findings
==================

* **Three architectural concerns visible in class names**: storage, schema validation, migration, compression. Schema migration suggests definition format has evolved at least once; backwards-compat is a first-class concern.
* **AgentVersionDataCompressor** — agent definitions can be large (prompt templates, tool lists, schemas); compression at-rest is a real concern.

