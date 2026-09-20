.. _pai-ai-gateway-and-stratus:

============================================================================
AI Gateway and Stratus
============================================================================

:Date: 2026-05-04

PAI consumes LLM/agent capabilities exclusively via Atlassian's **AI Gateway**,
accessed through the **Stratus** Kotlin SDK. The wrapper layer is in ``stratus/``.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. The Stratus surface PAI uses
=================================

* ``Unified`` async client — singleton bean built in
  ``AIGatewayClientConfiguration`` with the ``proactive-ai`` Micrometer namespace.
* ``ObservabilityContext`` — registered with the same configuration; emits
  per-call metrics into Micrometer → SignalFx.
* ``UnifiedLlmProvider`` — produces the LLM-call closure injected into agent
  builders.
* **Agent builder** — ``AIGatewayService.buildAgent(cloudId, user, useCaseId)``
  returns an agent ready for ``run()``.
* **Tool provider** (MCP) — ``IntegrationServiceToolProvider`` returns the set
  of tools available to the agent for the given tenant.

2. The MCP integration
=========================

PR #108 wired the Atlassian Integrations Service as PAI's **MCP server**.
Three components:

* ``IntegrationServiceMcpServerConfig`` — endpoint config (env-var driven)
* ``IntegrationServiceMcpSessionManager`` — per-tenant session lifecycle (open,
  reuse, close, error-recovery)
* ``IntegrationServiceToolProvider`` — exposes the discovered toolset to Stratus

The win: new product tools become available to PAI agents **without code
changes** — they show up via MCP discovery as soon as the Integrations Service
exposes them.

3. Per-request agent lifecycle
================================

::

   Controller / Handler
        │
        ▼
   AIGatewayService.buildAgent(cloudId, user, useCaseId)
        │  • Constructs UnifiedLlmProvider with per-request observability tags
        │  • Resolves toolset via IntegrationServiceToolProvider
        │  • Returns Agent
        ▼
   agent.run(input) suspending function
        │  • Stratus issues the LLM call(s)
        │  • Tool calls dispatch through MCP session
        │  • All calls observed via ObservabilityContext
        ▼
   Result returned to caller

4. Auth & headers
====================

Outbound calls to AI Gateway carry:

* ``X-Slauth-Audience: AI_GATEWAY``
* ``X-Slauth-Egress: <PAI service id>``
* The standard ASAP/SLAuth signature

Constants live in ``client/Audiences.kt`` + ``client/HttpClientCommons.kt``.

5. Observability
==================

Every Stratus call emits:

* ``proactive-ai.stratus.invocation.count`` (tagged: useCaseId, model, result)
* ``proactive-ai.stratus.invocation.timing.histogram`` (latency)
* ``proactive-ai.stratus.tokens.summary`` (input/output/total tokens)

These flow into the SignalFx dashboards used to compute SLOs (see
:doc:`01-business-and-technical-goals` §3).

6. See also
=============

* :doc:`/modules/platform/stratus` — per-file detail
* :doc:`08-auth-and-tenant` — SLAuth audience pattern
