.. _pai-platform-stratus:

============================================================================
``stratus`` — AI Gateway client integration
============================================================================

:Date: 2026-05-04
:Files: 8 main / 1 test
:Importance: **P0 — every LLM call goes through here**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Wraps the Atlassian Stratus SDK so PAI-side code uses small ``AIGatewayService``
verbs instead of direct SDK plumbing. Provides per-request agent construction,
MCP tool discovery, and session management for the Atlassian Integrations
Service.

Every LLM call in PAI flows through this package — it is the single exit
point for AI inference.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - LoC
     - Role
   * - ``AIGatewayService.kt`` (interface)
     - ~30
     - ``buildAgent()`` + ``runAgent()`` contract
   * - ``AIGatewayServiceImpl.kt``
     - ~60
     - Per-request agent builder; wires ``UnifiedLlmProvider``
   * - ``AIGatewayClientConfiguration.kt``
     - ~30
     - ``@Configuration``: singleton ``Unified`` async client + observability
   * - ``IntegrationServiceMcpServerConfig.kt``
     - ~20
     - MCP server endpoint (Atlassian Integrations Service)
   * - ``IntegrationServiceMcpSessionManager.kt``
     - ~30
     - Per-tenant MCP session lifecycle
   * - ``IntegrationServiceToolProvider.kt``
     - ~40
     - Discovers MCP tools and feeds them to Stratus agents
   * - ``WeatherTool.kt``
     - ~15
     - Test/example tool (demonstrates tool registration pattern)
   * - ``internal/`` (1 file)
     - ~20
     - Helpers / private adapters

3. Key classes deep dive
===========================

``AIGatewayService`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface AIGatewayService {
       fun buildAgent(
           cloudId: String,
           user: User,
           useCaseId: String,
           name: String,
           description: String,
           instruction: String,
           tools: List<BaseTool> = emptyList(),
           model: String = DEFAULT_MODEL,    // "gemini-2.5-pro"
       ): BaseAgent

       fun runAgent(
           agent: BaseAgent,
           userId: String,
           userMessage: String,
           streamingMode: RunConfig.StreamingMode = RunConfig.StreamingMode.SSE,
       ): Flowable<Event>

       companion object {
           const val DEFAULT_MODEL = "gemini-2.5-pro"
       }
   }

**Usage pattern** (from a task handler):

.. code-block:: kotlin

   val agent = aiGatewayService.buildAgent(
       cloudId = tenantContext.getAiGatewayCloudId(),
       user = executionContext.user,
       useCaseId = tenantContext.getAiGatewayUseCaseId(),
       name = "rovo-insights-agent",
       description = "Generates workspace insights",
       instruction = "Analyse the workspace and return...",
       tools = toolProvider.getTools(tenantContext),
   )
   val events = aiGatewayService.runAgent(agent, userId, "Generate insights")

``AIGatewayClientConfiguration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``@Configuration`` class providing:

* Singleton ``Unified`` async client (Stratus SDK entry point)
* ``ObservabilityContext`` with Micrometer namespace ``"proactive-ai"``
* SLAuth middleware for outbound requests (audience: ``AI_GATEWAY``)

``IntegrationServiceMcpServerConfig``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configures the MCP (Model Context Protocol) server endpoint for the Atlassian
Integrations Service. MCP enables Stratus agents to discover and call
workspace tools (e.g. Jira search, Confluence read) at runtime.

``IntegrationServiceMcpSessionManager``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manages per-tenant MCP sessions. Each tenant gets its own session with
workspace-scoped tool access. Sessions are created on first use and cached
for the duration of the request.

``IntegrationServiceToolProvider``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discovers available MCP tools from the Integrations Service and wraps them
as ``BaseTool`` instances that Stratus agents can invoke. The tool list is
dynamic — it changes based on what integrations the tenant has enabled.

4. Agent lifecycle
=====================

::

   Controller / TaskHandler
     │
     ▼
   AIGatewayService.buildAgent(cloudId, user, useCaseId, ...)
     │  • Create SLAuth-authenticated Unified client
     │  • Wire UnifiedLlmProvider with model selection
     │  • Attach MCP tools from IntegrationServiceToolProvider
     │  • Return configured BaseAgent
     │
     ▼
   AIGatewayService.runAgent(agent, userId, message)
     │  • Submit to Stratus via Unified async client
     │  • Return Flowable<Event> (SSE stream)
     │
     ▼
   Consumer processes events (streaming or buffered)

5. MCP tool discovery flow
==============================

::

   IntegrationServiceToolProvider.getTools(tenantContext)
     │
     ▼
   IntegrationServiceMcpSessionManager.getSession(tenantContext)
     │  • Create session if not cached
     │  • Connect to MCP server endpoint
     │
     ▼
   MCP Server (Atlassian Integrations Service)
     │  • Returns available tools for this tenant
     │  • Tools are workspace-scoped (only tools the tenant has enabled)
     │
     ▼
   Wrap each MCP tool as BaseTool → feed to agent

6. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``AIGatewayServiceImplTest``
     - Agent builder contract, model selection, SLAuth header injection

7. Design decisions
======================

1. **Interface abstraction** — ``AIGatewayService`` hides Stratus SDK
   complexity; feature code never imports SDK classes directly.
2. **Per-request agents** — agents are built per request, not pooled, because
   each carries tenant-specific context and tools.
3. **Default model constant** — ``DEFAULT_MODEL = "gemini-2.5-pro"`` is
   centralised; model changes propagate to all features.
4. **SSE streaming default** — ``RunConfig.StreamingMode.SSE`` enables
   real-time token streaming for latency-sensitive UIs.
5. **MCP for tool discovery** — dynamic tool registration via MCP means
   adding new workspace integrations doesn't require PAI code changes.

8. See also
==============

* :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus` — end-to-end
  story (per-request lifecycle, MCP discovery, observability, SLAuth)
* :doc:`/modules/platform/client` — ``Audiences.AI_GATEWAY`` constant
* :doc:`/modules/features/rovo-insights` — primary consumer of this package
