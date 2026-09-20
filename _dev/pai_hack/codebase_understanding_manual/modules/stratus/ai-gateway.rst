.. _mod-ai-gateway:

==============================
AI Gateway Service
==============================

:Files: ``stratus/AIGatewayClientConfiguration.kt``, ``stratus/AIGatewayService.kt``, ``stratus/internal/AIGatewayServiceImpl.kt``, ``stratus/WeatherTool.kt``, ``stratus/StratusTestController.kt``
:Tests: ``stratus/internal/AIGatewayServiceImplTest.kt``
:Importance: **P0 — LLM agent execution**

AIGatewayClientConfiguration
============================

Spring ``@Configuration`` class providing two singleton beans:

1. **Unified** — the async AI Gateway client from ``com.atlassian.mlp.client``.
   Base URL is resolved from ``ai-gateway.target-url`` (injected via service
   proxy as ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL``). Default headers include
   ``X-Slauth-Audience`` (targeting ``ai-gateway``) and ``X-Slauth-Egress: true``.

2. **ObservabilityContext** — wires ``AnalyticsClient`` and ``MeterRegistry``
   into the Stratus SDK's observability pipeline under the
   ``proactive-ai`` metrics namespace.

AIGatewayService Interface
==========================

Defines two operations:

``buildAgent()``
   Creates a ``BaseAgent`` (from Google ADK) configured with:

   - Per-request ``UnifiedLlmProvider`` carrying AI Gateway headers
     (cloud ID, user ID, use-case ID)
   - Agent name, description, system instruction
   - Optional tool list and model override (default: ``gemini-2.5-pro``)

``runAgent()``
   Executes an agent with a user message, returning a ``Flowable<Event>``
   for streaming responses. Creates a ``StratusRunner``, establishes a
   session, and runs the agent with configurable streaming mode (default: SSE).

AIGatewayServiceImpl
====================

The implementation performs three key operations:

1. **buildUnifiedLlmProvider()** — Creates a per-request LLM provider with
   AI Gateway headers:

   .. code-block:: kotlin

      HttpHeaders.builder()
          .add(AIGatewayHeaders.CLOUD_ID, cloudId)
          .add(AIGatewayHeaders.USER_ID, user.getAccountId().value())
          .add(AIGatewayHeaders.USE_CASE_ID, useCaseId)
          .build()

2. **buildAgent()** — Assembles an ``LlmAgent`` via the builder pattern with
   the provider, name, description, instruction, and tools.

3. **runAgent()** — Creates a ``StratusRunner`` with app name ``proactive-ai``,
   creates a session for the user, and runs the agent. Returns a
   ``Flowable<Event>`` for reactive streaming.

StratusTestController
=====================

REST controller at ``/api/v1/stratus`` providing two test endpoints:

.. code-block:: text

   POST /api/v1/stratus/chat
   POST /api/v1/stratus/insights

**``/chat``** — Builds an agent with ``WeatherTool`` and a simple instruction,
executes it with the user's message, collects all events, and extracts
model-role text parts into the response.

**``/insights``** — Same pattern but wires the agent to MCP tools from
``IntegrationServiceToolProvider.getTools()``, enabling the agent to call
any tool that integration-service exposes for the calling tenant.

Both endpoints require ``atl-cloudid`` header and a ``User`` request
attribute (set by ``UserContextInterceptor``).

WeatherTool
===========

A minimal example tool using Google ADK's ``@Annotations.Schema``:

.. code-block:: kotlin

   object WeatherTool {
       @JvmStatic
       @Annotations.Schema(description = "Retrieves the weather information for a given city.")
       fun getWeather(@Annotations.Schema(...) city: String): Map<String, Any> =
           mapOf("city" to city, "temperature" to "22C", "condition" to "Sunny")
   }

Returns hardcoded weather data. Intended as a verification tool for the agent
pipeline; will be replaced with real tools.

Test Coverage
=============

``AIGatewayServiceImplTest`` verifies:

- Agent building produces a correctly configured ``LlmAgent`` with the
  expected name, description, and tools.
- The ``UnifiedLlmProvider`` is created with correct AI Gateway headers.
- ``runAgent()`` returns a ``Flowable<Event>`` stream.
