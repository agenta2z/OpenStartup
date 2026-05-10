.. _mod-stratus:

==============================
Stratus / AI Gateway
==============================

.. toctree::
   :maxdepth: 1

   ai-gateway
   mcp-integration

Overview
========

The ``stratus`` package integrates the Proactive AI Platform with Atlassian's
AI Gateway via the Stratus SDK. It provides the infrastructure for building
and executing LLM-powered agents with tool-use capabilities, including
connection to the Integration Service MCP server for cross-product tool access.

Package Layout
==============

::

   stratus/
   ├── AIGatewayClientConfiguration.kt    ← Spring config: Unified client + ObservabilityContext beans
   ├── AIGatewayService.kt                ← Interface for agent building/execution
   ├── internal/
   │   └── AIGatewayServiceImpl.kt        ← Implementation: UnifiedLlmProvider + StratusRunner
   ├── IntegrationServiceMcpServerConfig.kt ← @ConfigurationProperties for MCP connection
   ├── IntegrationServiceMcpSessionManager.kt ← Per-request MCP session with auth headers
   ├── IntegrationServiceToolProvider.kt   ← Loads MCP tools from Integration Service
   ├── StratusTestController.kt           ← Test endpoints: /chat + /insights
   └── WeatherTool.kt                     ← Example tool for agent verification
