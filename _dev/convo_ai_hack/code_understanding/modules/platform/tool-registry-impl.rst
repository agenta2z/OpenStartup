.. _mod-tool-registry-impl:

==============================================
``platform/tool-registry/tool-registry-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/tool-registry/tool-registry-impl``
:Size: ~897 source lines :sup:`(verified)`

Concrete tool-registry implementation with **multiple registration strategies**.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``McpToolRegistrationServiceImpl.kt``
     - 373
     - MCP-protocol tools (largest)
   * - ``ToolRegistryServiceImpl.kt``
     - 245
     - Top-level registry
   * - ``IntegrationServiceToolRegistrationServiceImpl.kt``
     - 193
     - IntegrationService tools
   * - ``ForgeToolRegistrationServiceImpl.kt``
     - 49
     - Forge-app tools
   * - ``NativeToolRegistrationServiceImpl.kt``
     - 27
     - Built-in tools

Key Spring components
=======================

* ``@Component @Primary class ToolRegistryServiceImpl`` — top-level entry
* ``class McpToolRegistrationServiceImpl`` — MCP source
* ``class IntegrationServiceToolRegistrationServiceImpl`` — Atlassian Integration Service source
* ``@Component @Primary class ForgeToolRegistrationServiceImpl`` — Forge marketplace apps as tools
* ``class NativeToolRegistrationServiceImpl`` — built-in convoai tools

Notable findings
==================

* **Four registration sources** — MCP (largest), IntegrationService, Forge, Native. Each is a separate registration strategy bean.
* Two ``@Primary`` annotations (``ToolRegistryServiceImpl``, ``ForgeToolRegistrationServiceImpl``) — wins over alternative beans in tests.
* MCP being the largest source (373 LoC) reflects MCP's maturity as the strategic protocol.

