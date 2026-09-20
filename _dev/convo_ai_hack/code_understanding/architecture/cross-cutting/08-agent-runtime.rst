.. _agent-runtime:

============================
Agent Runtime (ADK)
============================

The platform is fundamentally an **agent runtime** — it loads agent definitions, exposes tools, manages multi-step LLM-mediated workflows, and reports results.

The Agent Development Kit (ADK)
================================

**Lives in:** ``modules/foundation/adk/`` (verified directory listing)

Two modules:

- ``adk/core-api`` — agent definition contracts, tool registration interface, agent lifecycle hooks
- ``adk/core-impl`` — runtime that loads agents, dispatches tool calls, manages conversation state

ADK is at the **foundation tier** because every product depends on it; foundation isolation rules ensure it can't grow product-specific concerns.

Agent definitions
==================

Agents are defined declaratively. Per the AGENTS.md context and the CSM ``skills/`` markdown pattern, an agent typically consists of:

1. **Identity** — name, description, version
2. **System prompt** — instructions to the LLM (Pebble template under product's ``resources/prompts/``)
3. **Tools** — list of capabilities the agent can invoke
4. **Skills** — markdown documents the agent can reference (CSM pattern)
5. **Model preference** — which provider/model to use (or "default")
6. **Output schema** — structured output type (if applicable)

Storage: agents are stored in Kamino + cached in Redis. AgentStudio's GraphQL CRUD API manipulates these definitions.

Tool invocation
================

When the LLM emits a tool_call, the platform:

1. **Parses** the tool call from the LLM response (JSON schema)
2. **Authorizes** the call against the (tenant, user, agent) triple
3. **Dispatches** to the registered ``ActionExecutor`` (in ``platform/action/action-impl``)
4. **Captures** the result
5. **Feeds back** to the LLM for the next turn

Tools register via ``platform/tool-registry/`` and execute via ``platform/action/``. The split is deliberate:

- **tool-registry** = catalog (name, schema, description) — what the LLM "sees"
- **action** = execution machinery — what actually runs the call

Multi-step workflows: Marathon
================================

For agents that need to take many steps over a long time horizon (minutes to hours), the platform delegates to **Marathon** — an external orchestrator service.

Pattern (per ``MarathonApiCallbackController.kt:29``, agent-reported):

1. Platform initiates a Marathon workflow with: agent definition, initial context, callback URL
2. Marathon executes the workflow asynchronously (potentially across hours)
3. Marathon calls back to the callback URL on each significant event (step started, step completed, workflow done)
4. Platform updates conversation state on each callback

Marathon is **not in this codebase** — it's a separate service. The integration point is:

- ``MarathonApiCallbackController`` (in ``product/rovo/rovo-impl``) — receives callbacks
- Marathon stub publisher module (``product/rovo/marathon-stubs-publisher``) — for testing

SAIN: Slack AI Notification orchestrator
==========================================

A specific agent runtime variant for Slack notification flows. The integration test ``SAINStandaloneHybridOrchestratorIT`` (failing locally — see hack_states/02-integrationTest-result.md) exercises this path. Coordinates:

- Permission checks (``SAINPermissionService``)
- Workflow caching (``SAINWorkflowCachingService``)
- Global cache debugging
- LLM call patterns specific to Slack output formatting

Patterns
=========

1. **Agents are data, not code.** Agent definitions are stored in Kamino, edited via AgentStudio GraphQL, versioned via agent-version/.

2. **Tools are pluggable.** New tools register via tool-registry-spi without modifying core code.

3. **Skills are markdown.** Adding a skill to an agent is a markdown file edit, not a code change.

4. **Long workflows go to Marathon.** Don't try to run a 30-minute workflow inside a single HTTP request.

5. **Streaming for short workflows.** Single LLM turn (or short multi-turn) → direct streaming. Long workflows → Marathon callback pattern.

What you would change here
===========================

- **Add a new tool** → register in tool-registry; implement in action-impl; potentially add UI widget
- **Add a new skill** → markdown file in product/<name>/skills/
- **Add a new agent type** → AgentStudio GraphQL mutation (no code change typically needed)
- **Modify Marathon callback handling** → ``MarathonApiCallbackController.kt``

What you would NOT change here
===============================

- Marathon's internal workflow execution (separate service)
- LLM provider mechanics (lives in AIGatewayClientServiceImpl)
- Conversation persistence (lives in conversation-impl)

