.. _mod-rovo-api:

==============================================
``product/rovo/rovo-api``
==============================================

:Tier: product
:Path: ``modules/product/rovo/rovo-api``
:Size: ~74,684 source lines :sup:`(verified)`
:Importance: **Tier 1 — Rovo's public contract**

The contract module for Rovo. Anything that wants to call into Rovo (or be called by it) sees this surface, NOT ``rovo-impl``.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Role
   * - ``product/rovo/chat/streaming/RovoChatStreamingEntities.kt``
     - 1,210
     - Streaming DTOs
   * - ``product/rovo/plugin/sain/cli/SainToolCliRunner.kt``
     - 1,179
     - SAIN CLI runner
   * - ``product/rovo/plugin/search/cli/SearchToolCliRunner.kt``
     - 1,007
     - Search CLI runner
   * - ``product/rovo/agent/tools/jira/workflowbuilder/JiraWorkflowOperationsToolDefinition.kt``
     - 916
     - Jira workflow tool definition
   * - ``product/rovo/agent/tools/hiringmanager/HiringManagerToolDefinition.kt``
     - 867
     - Hiring Manager tool definition

Why an API module is so big (74K LoC)
========================================

Most of the size comes from:

1. **Tool definitions** — each tool the Rovo agent can invoke is defined as a JSON-schema-bearing class. Many tools, many definitions.
2. **Streaming DTOs** — ``RovoChatStreamingEntities`` (1,210 lines) is essentially a giant set of typed event classes for the streaming wire format.
3. **CLI runners** — ``SainToolCliRunner``, ``SearchToolCliRunner`` etc. are runnable test/dev tools that exercise individual tools standalone.

API modules are usually small; Rovo's is large because it owns a large catalog of tool contracts.

Patterns
==========

1. **Tool definition = data class + JSON schema.** Each tool's class declares its name, input schema, output schema, description.
2. **CLI runners as dev fixtures.** ``Tool*CliRunner`` allows running a single tool from the command line without bringing up the full service.
3. **Streaming entity types are first-class.** Streaming response typing is non-trivial; deserves a dedicated file.

What you would change here
============================

* **Define a new Rovo tool** → new ``<Name>ToolDefinition.kt`` here + impl in ``rovo-impl``
* **Add a new streaming event type** → ``RovoChatStreamingEntities.kt``
* **Add a CLI runner for a tool** → new ``<Tool>CliRunner.kt``

