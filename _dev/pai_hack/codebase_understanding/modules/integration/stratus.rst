======================================================
Module: ``stratus`` — AI Gateway / Stratus Integration
======================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Integrates the service with the **Atlassian AI Gateway** (codename Stratus)
for LLM-powered agent execution.  Provides:

* Client configuration for the AI Gateway's unified API.
* Agent construction and execution via Google ADK (Agent Development Kit).
* MCP (Model Context Protocol) session management for tool integration.
* A test controller for ad-hoc agent invocation.
* A sample ``WeatherTool`` for development/testing.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``AIGatewayClientConfiguration.kt``
     - 66
     - ``@Configuration`` — WebClient & observability beans
   * - ``AIGatewayService.kt``
     - 67
     - Interface — agent build & run API
   * - ``IntegrationServiceMcpServerConfig.kt``
     - 14
     - ``@ConfigurationProperties`` — MCP server connection config
   * - ``IntegrationServiceMcpSessionManager.kt``
     - 54
     - MCP session lifecycle (async client creation)
   * - ``IntegrationServiceToolProvider.kt``
     - 54
     - ``@Component`` — retrieves MCP tools for agents
   * - ``StratusTestController.kt``
     - 187
     - ``@RestController`` — test endpoints for chat & insights agents
   * - ``WeatherTool.kt``
     - 25
     - Sample tool for development testing
   * - ``internal/AIGatewayServiceImpl.kt``
     - 120
     - ``@Service`` — Google ADK-based implementation

**Total: 8 files, ~587 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``AIGatewayService`` — agent lifecycle API:

  - ``fun buildAgent(cloudId, user, useCaseId, name, description, instruction, tools, model): BaseAgent``
  - ``fun runAgent(agent, userId, userMessage, streamingMode): Flowable<Event>``
  - Companion: ``const val DEFAULT_MODEL = "gemini-2.5-pro"``

Configuration Classes
---------------------

* ``AIGatewayClientConfiguration`` (``@Configuration``) — produces:

  - ``@Bean fun asyncUnifiedClient(@Value("${ai-gateway.target-url}") url): Unified``
    — AI Gateway HTTP client.
  - ``@Bean fun observabilityContext(analyticsClient, meterRegistry): ObservabilityContext``
    — metrics/analytics wiring.

* ``IntegrationServiceMcpServerConfig`` (data class,
  ``@ConfigurationProperties(prefix = "integrations-service")``) — properties:

  - ``url: String`` — base URL of the integrations service.
  - ``endpoint: String`` — MCP endpoint path (default: ``/mcp``).
  - ``timeout: Duration`` (``@DurationUnit(SECONDS)``) — connection timeout.

MCP Classes
-----------

* ``IntegrationServiceMcpSessionManager`` — creates async MCP client sessions:

  - Constructor: ``config``, ``cloudId``, ``user``.
  - ``fun createSession(): McpSyncClient`` — throws
    ``UnsupportedOperationException`` (sync not supported).
  - ``fun createAsyncSession(): McpAsyncClient`` — connects to MCP server
    via SSE transport.

* ``IntegrationServiceToolProvider`` (``@Component``,
  ``@EnableConfigurationProperties(IntegrationServiceMcpServerConfig::class)``) —

  - ``fun getTools(cloudId, user, actionIds?): List<BaseTool>`` — retrieves
    available MCP tools, optionally filtered by action IDs.

Controllers
-----------

* ``StratusTestController`` (``@RestController``,
  ``@RequestMapping``) — test endpoints:

  - ``@PostMapping("/chat") fun chat(request, user, cloudId): AgentResponse``
  - ``@PostMapping("/insights") fun insights(request, user, cloudId): AgentResponse``

* ``AgentRequest`` (data class) — ``message: String``, optional agent config.
* ``AgentResponse`` (data class) — ``response: String``, metadata.

Tool Classes
------------

* ``WeatherTool`` (object) — sample tool with:

  - ``@JvmStatic @Annotations.Schema fun getWeather(city: String): Map<String, Any>``
  - Returns mock weather data for testing MCP tool integration.

Implementation Classes
----------------------

* ``AIGatewayServiceImpl`` (``@Service``) — implements ``AIGatewayService``:

  - ``buildAgent`` — constructs a Google ADK ``BaseAgent`` with:
    - ``UnifiedLlmProvider`` configured for the AI Gateway.
    - User context (cloud-id, account-id) for auth.
    - Provided tools and model selection.
  - ``runAgent`` — creates a ``Runner`` and executes with RxJava
    ``Flowable<Event>`` for streaming responses.
  - Private: ``buildUnifiedLlmProvider``, ``buildRunner``.

Spring Component Annotations
=============================

========================================= ================================
Bean                                       Annotation
========================================= ================================
``AIGatewayClientConfiguration``           ``@Configuration``
``IntegrationServiceMcpServerConfig``      ``@ConfigurationProperties``
``IntegrationServiceToolProvider``         ``@Component @EnableConfigProperties``
``StratusTestController``                  ``@RestController``
``AIGatewayServiceImpl``                   ``@Service``
========================================= ================================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["StratusTestController
       POST /chat or /insights"] -->|AgentRequest| B[AIGatewayServiceImpl.buildAgent]
       B --> C[IntegrationServiceToolProvider.getTools]
       C --> D[IntegrationServiceMcpSessionManager.createAsyncSession]
       D -->|SSE transport| E[Integrations Service]
       E -->|List of BaseTool| C
       B --> F["UnifiedLlmProvider
       (ai-gateway.target-url, auth)"]
       B --> G["BaseAgent(name, instruction, tools)"]
       G --> H[AIGatewayServiceImpl.runAgent]
       H -->|Runner.runAsync| I["Flowable&lt;Event&gt; (streaming)"]
       I --> J[Collect events]
       J --> K[AgentResponse]
       H --> L["AI Gateway (upstream)"]
       L -->|"LLM inference (Gemini 2.5 Pro)"| I
       L -->|tool calls via MCP| E

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 45 25 30

   * - Property
     - Default
     - Description
   * - ``ai-gateway.target-url``
     - ``${MESH_DEPENDENCY_AI_GATEWAY_BASE_URL}``
     - AI Gateway service URL
   * - ``integrations-service.url``
     - ``${MESH_DEPENDENCY_INTEGRATIONS_SERVICE_BASE_URL}``
     - Integrations service base URL
   * - ``integrations-service.endpoint``
     - ``/mcp``
     - MCP endpoint path
   * - ``integrations-service.timeout``
     - ``30`` (seconds)
     - MCP connection timeout

Testing Coverage
================

======================================== ====== ============================
Test class                                Lines  Subjects
======================================== ====== ============================
``AIGatewayServiceImplTest``              142    Agent building, runner execution
======================================== ====== ============================

**Coverage: 1/4 implementation files** directly tested.

**Gaps:**

* ``IntegrationServiceToolProvider`` — no test for MCP tool retrieval.
* ``IntegrationServiceMcpSessionManager`` — no test for session creation.
* ``StratusTestController`` — no dedicated test (may be covered by integration
  tests).

Dependencies
============

Inbound (consumed by)
---------------------

* ``feature/rovoinsights`` — insight generation may use AI Gateway for LLM
  inference.
* External test clients — via ``StratusTestController`` endpoints.

Outbound (depends on)
---------------------

* Google ADK — ``BaseAgent``, ``Runner``, ``RunConfig``, ``BaseTool``,
  ``UnifiedLlmProvider``.
* AI Gateway Client SDK — ``Unified``, ``ObservabilityContext``.
* MCP SDK — ``McpAsyncClient``, ``McpSyncClient``, ``McpSessionManager``.
* ``client/http-commons`` — ``Audiences.AI_GATEWAY``,
  ``Audiences.INTEGRATIONS_SERVICE``.
* ``utility/user`` — ``User`` interface.
* RxJava 3 — ``Flowable<Event>`` for streaming.
* Spring WebFlux — ``WebClient`` for HTTP calls.

Open Questions / Ambiguities
=============================

1. ``IntegrationServiceMcpSessionManager.createSession()`` throws
   ``UnsupportedOperationException`` — sync sessions are not supported but
   the method exists in the interface; callers must know to use async.
2. ``DEFAULT_MODEL = "gemini-2.5-pro"`` is hard-coded — model selection
   should be a configuration property for easy updates.
3. ``WeatherTool`` is a development artifact — should be excluded from
   production builds or gated behind a profile.
4. ``StratusTestController`` at 187 LoC is the largest controller — contains
   agent configuration logic that could be extracted to a service.
5. The relationship between ``AIGatewayService`` and the Rovo Insights
   generation pipeline is not explicitly wired in code — confirm the
   integration path.
