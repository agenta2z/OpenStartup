.. _mod-mcp-integration:

==============================
MCP Integration Service
==============================

:Files: ``stratus/IntegrationServiceMcpServerConfig.kt``, ``stratus/IntegrationServiceMcpSessionManager.kt``, ``stratus/IntegrationServiceToolProvider.kt``
:Importance: **P0 — cross-product tool access**

Overview
========

The MCP (Model Context Protocol) integration connects the Proactive AI Platform
to Atlassian's Integration Service, enabling AI agents to invoke tools across
Atlassian products (Jira, Confluence, etc.) on behalf of authenticated users.

IntegrationServiceMcpServerConfig
=================================

Spring ``@ConfigurationProperties`` bound to ``integrations-service.*``:

.. code-block:: kotlin

   data class IntegrationServiceMcpServerConfig(
       val url: String,           // base URL of the MCP server
       val endpoint: String,      // MCP endpoint path
       val timeout: Duration,     // connection + request timeout (seconds)
   )

IntegrationServiceMcpSessionManager
====================================

Per-request session manager implementing ``McpSessionManager``. Constructed
with ``cloudId`` and ``user`` (both request-scoped).

Only supports **async sessions** (``createSession()`` throws
``UnsupportedOperationException``).

``createAsyncSession()`` builds an ``McpAsyncClient`` with:

- ``HttpClientStreamableHttpTransport`` targeting the configured MCP server URL
- Custom HTTP headers injected via ``asyncHttpRequestCustomizer``:

  - ``X-Slauth-Egress: true`` — enables egress authentication
  - ``X-Slauth-Audience: integrations-service`` — targets the MCP server
  - ``atl-cloudid`` — tenant scoping
  - ``User-Context`` — user authentication token
  - ``Atl-Surface`` — surface identifier from Stratus SDK headers

IntegrationServiceToolProvider
==============================

Spring ``@Component`` that loads MCP tools from the Integration Service:

.. code-block:: kotlin

   fun getTools(
       cloudId: String,
       user: User,
       actionIds: List<String>? = null,
   ): List<BaseTool>

For each call:

1. Creates a new ``IntegrationServiceMcpSessionManager`` (request-scoped).
2. Builds an ``McpAsyncToolset`` with optional action ID filtering via
   ``Filters.actionIds()``.
3. Blocks until the MCP server returns its tool list.

The ``actionIds`` parameter allows restricting the toolset to specific actions;
passing ``null`` surfaces all tools the service is entitled to per the
``poco`` policy.

Data Flow
=========

::

   StratusTestController.insights()
     │
     ▼
   IntegrationServiceToolProvider.getTools(cloudId, user)
     │  creates IntegrationServiceMcpSessionManager
     │  builds McpAsyncToolset with filters
     │  blocks for tool list from Integration Service
     │
     ▼
   List<BaseTool> (MCP tools)
     │
     ▼
   AIGatewayService.buildAgent(tools = mcpTools)
     │  agent can now invoke any Integration Service tool
     │
     ▼
   AIGatewayService.runAgent(agent, userId, message)
     │  agent calls tools as needed during reasoning
     │
     ▼
   AgentResponse (collected model text)

Security Model
==============

All MCP requests carry the calling user's context token (UCT), ensuring
tool invocations are scoped to the user's permissions within their tenant.
The ``X-Slauth-Egress`` + ``X-Slauth-Audience`` headers enable service-to-
service authentication via Atlassian's SLAuth infrastructure.
