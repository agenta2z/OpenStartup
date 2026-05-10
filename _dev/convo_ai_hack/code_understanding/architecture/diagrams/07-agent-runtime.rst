.. _diag-agent-runtime:

================================================
Diagram 7 — Agent Runtime: Tools, Skills, Workflows
================================================

The platform is fundamentally an **agent runtime**. This diagram shows how an agent definition becomes an LLM call with tools, what happens when the LLM invokes a tool, and how long-horizon workflows escape the request scope.

Agent definition → LLM call
=============================

.. mermaid::

   flowchart LR
       %% Storage
       subgraph STORE["Persistent storage"]
           KAM_AGENT[(Kamino<br/>agent definitions)]
           SKILLS[(Markdown skill files<br/>product/csm/skills/<br/>jsm/skills/...)]
           PROMPTS[(Pebble templates<br/>product/&lt;name&gt;/<br/>resources/prompts/)]
       end

       %% Loaders
       subgraph LOAD["Runtime loaders"]
           ADK_API[adk/core-api<br/>Agent, Tool, Skill contracts]
           ADK_IMPL[adk/core-impl<br/>loads agents at boot/refresh]
           TR[platform/tool-registry<br/>catalogue: name, schema, description]
       end

       %% Build the prompt
       subgraph BUILD["Per-request build"]
           CTX[Conversation context<br/>conversation/conversation-impl]
           AGNT[Resolved Agent + Skills + Tools]
           PROMPT[Rendered prompt<br/>system + user + tool defs]
       end

       %% Execution
       AGS[AIGatewayClientServiceImpl<br/>:1061 streamOpenaiClient]

       %% Wiring
       KAM_AGENT --> ADK_IMPL
       SKILLS --> ADK_IMPL
       PROMPTS --> ADK_IMPL
       ADK_API -.contract.-> ADK_IMPL
       TR --> AGNT

       ADK_IMPL --> AGNT
       CTX --> PROMPT
       AGNT --> PROMPT
       PROMPT --> AGS

       %% Style
       style STORE fill:#fff8e1,stroke:#f57c00
       style LOAD fill:#e3f2fd,stroke:#1565c0
       style BUILD fill:#e8f5e9,stroke:#2e7d32
       style AGS fill:#fce4ec,stroke:#c2185b,stroke-width:2px

How to read it
---------------

* **Yellow boxes (top)** = persistent agent state (Kamino events + markdown skills + Pebble templates)
* **Blue boxes (middle)** = ADK runtime + tool registry — load definitions and produce a resolved agent
* **Green boxes** = per-request prompt assembly — combine conversation context with the resolved agent
* **Pink box** = the LLM call itself

Three layers of mutability
============================

* **Pebble templates** = file changes (require a code release to deploy)
* **Markdown skills** = file changes (same — code release)
* **Kamino agent definitions** = data changes (editable via AgentStudio GraphQL — NO release needed)

This is by design. Code-controlled artifacts (templates, skills) get the safety of code review + deployment gating. Data-controlled artifacts (agent definitions, tool selections) get the agility of "edit in production".

Tool invocation cycle
======================

When the LLM emits a ``tool_call``:

.. mermaid::

   sequenceDiagram
       autonumber
       participant LLM as LLM<br/>(via AI Gateway)
       participant AGS as AIGatewayClientServiceImpl
       participant CTL as Controller / Workflow
       participant TR as platform/tool-registry
       participant ACT as platform/action/<br/>action-impl
       participant TOOL as Concrete tool<br/>(e.g. JqlSearchTool)

       Note over LLM: Generates response with tool_call

       LLM-->>AGS: chunk with tool_call
       AGS-->>CTL: chunk parsed as ToolCallEvent
       CTL->>TR: lookup tool by name
       TR-->>CTL: ToolDefinition + Executor reference
       CTL->>ACT: dispatch ToolCall(args)

       ACT->>ACT: authorize(tenant, user, agent, tool)
       alt unauthorized
           ACT-->>CTL: AuthorizationException
           CTL-->>LLM: error result fed back
       end

       ACT->>TOOL: execute(args)
       TOOL-->>ACT: ToolResult or exception

       ACT-->>CTL: typed result
       CTL->>AGS: continue conversation with tool_result
       AGS->>LLM: append tool result, request next chunk

       Note over LLM,CTL: LLM may emit more tool_calls<br/>OR final user-facing text

Two registries, one purpose
============================

* ``platform/tool-registry/`` = the **catalogue** the LLM "sees" (names, JSON schemas, descriptions)
* ``platform/action/`` = the **execution machinery** that runs the tool

The split allows:

* **Hot-add tools** without modifying core code (register via SPI)
* **Multiple implementations of the same tool name** (A/B test executors)
* **Authorization independent of execution** (auth in the action tier; execution in tool-specific impl)

Long-horizon workflows: the Marathon escape hatch
===================================================

For agents that need minutes-to-hours of work (multiple LLM turns + tool calls + waiting), in-request execution doesn't fit (HTTP timeouts, Reactor thread occupancy, etc).

.. mermaid::

   sequenceDiagram
       autonumber
       actor U as User
       participant CTL as Controller
       participant MAR as Marathon<br/>(external service)
       participant CB as MarathonApiCallbackController<br/>product/rovo/rovo-impl :29
       participant CONV as conversation-impl

       U->>CTL: POST /start_long_workflow
       CTL->>MAR: initiate workflow<br/>(agent def, ctx, callback URL)
       MAR-->>CTL: workflow_id
       CTL-->>U: 202 Accepted + workflow_id

       Note over MAR: Marathon executes asynchronously<br/>(potentially over hours)

       loop on each significant event
           MAR-->>CB: POST callback<br/>(step_started / completed / failed)
           CB->>CONV: update conversation state
           Note over CB: client may poll for state<br/>OR subscribe to events
       end

       MAR-->>CB: workflow_complete
       CB->>CONV: mark conversation done

How long-horizon escapes the request scope
--------------------------------------------

* The **request returns 202 Accepted** immediately with a workflow ID.
* **Marathon owns the long execution** — durable, restartable, observable independently.
* **Callbacks come back** via a separate endpoint that updates conversation state.
* **Clients poll or subscribe** for completion status.

This pattern is used by:

* **SAIN** (Slack AI Notification orchestrator)
* **Deep research** workflows
* **Batch evaluation** runs (uses BatchEvaluationTaskHandler instead of Marathon, but same pattern)

Patterns visible in this diagram
==================================

1. **Agents are data, not code.** Kamino-stored, AgentStudio-edited. No code release needed to update an agent.

2. **Skills are markdown.** ``product/csm/skills/email-suppression-skill.md`` — the agent's "knowledge" comes from markdown that ADK loads.

3. **Tools are pluggable via two registries.** Tool-registry for the LLM-facing definition; action-impl for execution. Adding a new tool means two registrations + one executor.

4. **Authorization is layered.** Tool authorization (in action-impl) is separate from request authorization (in HeaderFilter). An agent might pass HeaderFilter but be denied a specific tool.

5. **Long workflows escape via callbacks.** Marathon (or batch task handlers) own the long execution; callbacks update conversation state.

