.. _feature-chat-streaming:

==================================================================
Chat Streaming — the message-level workflow plumbing
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: ~25,600 LoC in ``rovo-impl/.../product/rovo/chat/service/`` (62 files) + ~1,600 LoC controller + streaming entities + writer infrastructure
:Module: ``rovo-impl/.../product/rovo/chat/`` + ``rovo-api/.../product/rovo/chat/streaming/``

.. contents:: On this page
   :local:
   :depth: 2

What chat-streaming IS (in one paragraph)
============================================

Chat streaming is the **message-level workflow plumbing** that
connects an HTTP request to an agent execution and back to the user.
It owns: REST endpoint routing (23 endpoints in ``RovoChatV1Controller``),
SSE / NDJSON response framing, conversation history loading, agent
selection, executor dispatch (Marathon, A2A, async tasks), streaming
event envelope construction, and per-event-type metric/trace emission.
Every feature (Marathon, SAIN, AIFC, AgentStudio agents, Deep Research)
ultimately produces output as ``RovoChatV1StreamMessageEnvelope`` events
flowing through this layer.

Anatomy — where the code lives
=================================

The chat-streaming subsystem spans **4 distinct locations**:

**A. Public stream contract** (``rovo-api/.../product/rovo/chat/streaming/``):

* ``RovoChatStreamingEntities.kt`` (261 LoC) — **the canonical envelope contract**:
  ``RovoChatV1StreamMessageEnvelope``, ``RovoChatV1StreamMessageType`` enum
  (30+ types), per-type sealed message classes
* ``RovoChatStream`` typealias = ``Stream<RovoChatV1StreamMessageEnvelope>``

**B. Workflow contract** (``rovo-api/.../product/rovo/workflow/``):

* ``WorkflowStreamResponse.kt`` — internal workflow output type (orchestrator output)
* ``AssistanceServiceWorkflowService.kt`` — the assistance-service workflow interface (legacy v1 path)
* ``AssistanceServiceWorkflowRequest.kt`` — request DTO

**C. Implementation** (``rovo-impl/.../product/rovo/chat/service/``, **25,600 LoC across 62 files**):

.. list-table::
   :header-rows: 1
   :widths: 56 12 32

   * - File
     - LoC
     - Role
   * - ``RovoChatService.kt``
     - **2,966**
     - **Largest in chat/.** Top-level service: conversation lookup, agent selection, history loading, dispatch to executor
   * - ``agents/MarathonAgentDefinitions.kt``
     - 1,996
     - System-defined agent registry: lists what agents exist (Generic, Confluence, Jira, etc.) with their config (tools, knowledge, instructions)
   * - ``executors/RovoChatExecutor.kt``
     - 1,600
     - Top-level executor — receives a chat request, invokes the right inner executor (Marathon / A2A / sync / async)
   * - ``executors/RovoChatAgentExecutionService.kt``
     - 1,424
     - **THE CENTRAL DISPATCHER** — routes between executor variants based on agent type, conversation state, FF
   * - ``executors/A2AChatExecutor.kt``
     - 1,370
     - Agent-to-Agent executor (legacy A2A protocol)
   * - ``executors/RovoChatAsyncTaskLauncher.kt``
     - 1,223
     - Async task launcher — for long-running background work
   * - ``executors/stream/RovoChatAgentStreamingWriter.kt``
     - **1,220**
     - **The stream writer** — converts orchestrator output events into ``RovoChatV1StreamMessageEnvelope`` and writes to HTTP response
   * - ``executors/a2a/NewA2AChatExecutor.kt``
     - 893
     - New A2A executor (replacement for ``A2AChatExecutor``)
   * - ``executors/a2a/A2AEventHandler.kt``
     - 845
     - A2A event handling
   * - ``executors/stream/RovoChatStreamOutputHandler.kt``
     - 808
     - Output handler — buffers/flushes streamed bytes
   * - ``executors/MarathonAgentExecutorImpl.kt``
     - 803
     - The Marathon agent-executor (the only ``MarathonAgentExecutor`` impl)
   * - ``agents/MarathonPromptBuilder.kt``
     - 714
     - Builds Marathon-style system prompts
   * - ``analytics/RovoChatAnalyticsHelperImpl.kt``
     - 679
     - Per-event analytics emission (event tags, timing, outcomes)
   * - ``SkillRegistryServiceImpl.kt``
     - 552
     - Skill discovery / registration

**D. Controller** (``rovo-impl/.../product/rovo/rest/``):

* ``RovoChatV1Controller.kt`` (~1,565 LoC) — the **23-endpoint REST surface**

The 23 REST endpoints
=======================

``RovoChatV1Controller`` exposes 23 endpoints. Categorized:

**Conversation lifecycle** (5):

.. list-table::
   :header-rows: 1
   :widths: 18 36 46

   * - Method
     - Path
     - Role
   * - GET
     - ``/conversations``
     - List conversations
   * - GET
     - ``/conversation/{conversationId}``
     - Get conversation details
   * - POST
     - ``/conversation``
     - Create new conversation
   * - PUT
     - ``/conversation/{conversationId}``
     - Update conversation (e.g. rename)
   * - DELETE
     - ``/conversation/{conversationId}``
     - Delete conversation

**Synchronous message + action** (3):

.. list-table::
   :header-rows: 1
   :widths: 18 56 26

   * - Method
     - Path
     - Role
   * - POST
     - ``/conversation/{conversationId}/action``
     - Synchronous action (returns full result, no streaming)
   * - POST
     - ``/conversation/{conversationId}/message/{messageId}/tools/resolution``
     - Tool resolution callback (interactive flows)
   * - GET
     - ``/conversation/{conversationId}/messages``
     - Get message history

**Streaming** (5 — **the important ones**):

.. list-table::
   :header-rows: 1
   :widths: 18 50 32

   * - Method
     - Path
     - Format
   * - POST
     - ``/conversation/{conversationId}/action/stream``
     - **NDJSON** (newline-delimited JSON)
   * - POST
     - ``/conversation/{conversationId}/message/stream``
     - **NDJSON** — primary chat streaming endpoint
   * - POST
     - ``/conversation/{conversationId}/message/stream/sse``
     - **SSE** (text/event-stream) — alternative for browser EventSource
   * - POST
     - ``/conversation/{conversationId}/voiceMessage/stream``
     - NDJSON for voice messages
   * - POST
     - ``/conversation/{conversationId}/custom-action/{scenarioId}/message/stream``
     - NDJSON for AgentStudio scenario-driven custom actions

**Files** (4):

* GET ``/conversation/{conversationId}/files`` — list files
* GET ``/file/{fileBlobId}`` — fetch file
* POST ``/message/file/validate`` — pre-upload validation
* POST ``/message/file`` — upload file

**Misc** (6):

* GET ``/generated-content`` — list generated content
* POST ``/conversation/{conversationId}/evaluate`` — evaluate quality
* GET ``/conversation/{conversationId}/debug-logs`` — debug logs
* POST ``/conversation/{conversationId}/message/{messageId}/cancel`` — cancel in-flight message
* POST ``/conversation/{conversationId}/message/{messageId}/answer-now`` — accelerate (if waiting)
* PUT ``/conversation/{conversationId}/message/{messageId}/feedback`` — submit feedback
* GET ``/memories/agent/{agentId}`` — agent memory inspection

The 30+ stream message types
==============================

``RovoChatV1StreamMessageType`` enum (canonical contract for what
clients can receive):

**Conversational lifecycle** (8):

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Type
     - Meaning
   * - ``CONVERSATION_CHANNEL_DATA``
     - Initial channel/conversation metadata
   * - ``TRACE``
     - Diagnostic trace event (for debug UI)
   * - ``ANSWER_PART``
     - Streaming token of the assistant answer
   * - ``REASONING_PART``
     - Streaming token of the reasoning output (e.g., Claude thinking)
   * - ``FINAL_RESPONSE``
     - The terminal envelope (signals end-of-stream)
   * - ``EARLY_STOP``
     - Stream early-stop indication
   * - ``ANSWER_GENERATION_TYPE``
     - Tag indicating which orchestrator/strategy was used
   * - ``ASK_QUESTION``
     - Agent is requesting a clarification

**Tool / plugin invocation** (3):

* ``PLUGIN_INVOCATION`` — a plugin/tool was invoked
* ``TOOL_SELECTION`` — LLM picked a tool
* ``TOOL_INVOCATION`` — tool actually called

**Action streaming** (6 — **NEW in v1**):

* ``ACTION_CLASSIFICATION`` — action classified
* ``ACTION_PREPARE`` — preparing to execute
* ``ACTION_PART`` — streaming part of action result
* ``ACTION_ERROR`` — action errored
* ``ACTION_METADATA`` — action metadata
* ``ACTION_COMPLETE`` — action finished

**Safety / moderation** (5):

* ``PROMPT_REDACTION`` — prompt was redacted (PII stripped)
* ``RESPONSE_REDACTION`` — response was redacted
* ``PROMPT_BLOCKED`` — prompt was blocked entirely
* ``RESPONSE_BLOCKED`` — response was blocked
* ``ATTACHMENT_BLOCKED`` — attachment was blocked

**Follow-up & UI** (5):

* ``FOLLOW_UP_QUERIES`` — suggested follow-up questions
* ``ERROR_STATE_QUERY_SUGGESTIONS`` — suggestions when error occurred
* ``TODO_SNAPSHOT`` — todo list snapshot
* ``AGENTIC_UI`` — agentic UI element to render
* ``TASK_STATUS`` — long-running task status update

**Voice / sub-agents / errors** (4+):

* ``TEXT_OF_SPEECH`` — voice output
* ``DL_SUB_AGENT`` — Deep Research sub-agent event
* ``ERROR`` — error event

**This 30+ envelope vocabulary IS the contract** between the backend
and any streaming client (web UI, mobile UI, voice UI, debugger UI,
external integrations). Adding a new envelope type requires:

1. Add to ``RovoChatV1StreamMessageType`` enum
2. Add a sealed ``RovoChatV1...Message`` data class with ``@JsonSubTypes`` registration
3. Update the writer (``RovoChatAgentStreamingWriter``) to emit it
4. Update all client consumers

End-to-end flow
==================

**HTTP request → response (the canonical happy path)**:

1. **Browser/mobile client** sends ``POST /conversation/{id}/message/stream``
   with body containing the user's message
2. **Spring receives** the request, dispatches to ``RovoChatV1Controller.conversationMessageCreateStream()``
3. **Controller** sets response content-type to ``application/x-ndjson`` and starts the streaming response body
4. **Controller** delegates to ``RovoChatService`` (top-level service)
5. **RovoChatService** loads conversation history, resolves which agent
   to use (default vs custom), validates permissions
6. **RovoChatService** invokes ``RovoChatExecutor.execute(...)``
7. **RovoChatExecutor** routes to ``RovoChatAgentExecutionService`` (the central dispatcher)
8. **AgentExecutionService** picks the executor variant:

   * Standard chat → ``MarathonAgentExecutorImpl``
   * A2A chat → ``A2AChatExecutor`` or ``NewA2AChatExecutor``
   * Long-running → ``RovoChatAsyncTaskLauncher`` (returns task id; later events delivered via task-status stream)

9. **MarathonAgentExecutor** dispatches by agent config:

   * Marathon agent → Marathon orchestrator (Python sandbox)
   * SAIN agent → SAIN StandaloneHybrid / Hybrid / LongHorizon
   * AIFC agent → AIFC pipeline (preprocess → exec → output → finalize)
   * AgentStudio agent → standard chat with custom config

10. **Orchestrator** runs, producing ``WorkflowStreamResponse`` events
11. **RovoChatAgentStreamingWriter** wraps each event in ``RovoChatV1StreamMessageEnvelope``
12. **RovoChatStreamOutputHandler** buffers and flushes JSON-serialized
    envelopes to the HTTP response stream as NDJSON
13. **Browser** parses each line as one JSON event; renders incrementally
14. **Final**: writer emits ``FINAL_RESPONSE`` envelope, closes stream

Sequence diagram
==================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as Browser
       participant Ctrl as RovoChatV1<br/>Controller
       participant Svc as RovoChatService<br/>(2,966 LoC)
       participant Exec as RovoChat<br/>Executor (1,600 LoC)
       participant AES as RovoChatAgent<br/>ExecutionService (1,424 LoC)
       participant ME as Marathon<br/>AgentExecutorImpl (803 LoC)
       participant Orch as Marathon /<br/>SAIN / AIFC / etc.
       participant W as RovoChatAgent<br/>StreamingWriter (1,220 LoC)
       participant OH as StreamOutput<br/>Handler (808 LoC)

       U->>Ctrl: POST /conversation/{id}/message/stream
       Ctrl->>Ctrl: setResponseContentType("application/x-ndjson")
       Ctrl->>Svc: createStreamingMessage(req, user, tenant)

       Svc->>Svc: load conversation history
       Svc->>Svc: resolve agent (default vs custom)
       Svc->>Svc: validate permissions

       Svc->>Exec: execute(prepared)
       Exec->>AES: executeAgent(input, ctx)
       AES->>AES: pick executor variant by FF + agent type
       AES->>ME: executeAgent(...)
       ME->>Orch: orchestrate(...)

       loop streaming events
           Orch-->>W: WorkflowStreamResponse(answerPart="hello")
           W->>W: wrap in RovoChatV1StreamMessageEnvelope(type=ANSWER_PART, ...)
           W->>OH: write(envelope)
           OH->>OH: serialize to JSON line
           OH-->>U: write to HTTP response (chunked)
       end

       opt tool call
           Orch-->>W: WorkflowStreamResponse(toolInvocation=...)
           W->>W: type=TOOL_INVOCATION
           W->>OH: write
           OH-->>U: stream
       end

       opt safety
           Orch-->>W: WorkflowStreamResponse(blocked)
           W->>W: type=PROMPT_BLOCKED | RESPONSE_BLOCKED
           W->>OH: write
           OH-->>U: stream
       end

       Orch-->>W: terminal event
       W->>W: emit FINAL_RESPONSE envelope
       W->>OH: flush + close
       OH-->>U: end of stream


External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 30 46

   * - System
     - How
     - Used for
   * - **Conversation storage**
     - via ``ConversationHistoryItem`` lookup
     - Loading prior turns; persisting new turns
   * - **Agent storage**
     - via ``AgentStudioAgentService`` etc
     - Resolving agent definitions at request time
   * - **Orchestrators** (Marathon, SAIN, AIFC, AgentStudio)
     - via ``MarathonAgentExecutor``
     - Actual execution
   * - **AsyncTaskLauncher**
     - via ``RovoChatAsyncTaskLauncher`` (1,223 LoC)
     - Long-running task offload (returns task id)
   * - **A2A protocol**
     - via ``A2AChatExecutor`` / ``NewA2AChatExecutor``
     - Agent-to-agent communication
   * - **Safety pipeline**
     - via prompt/response moderation
     - Emits ``PROMPT_BLOCKED`` / ``RESPONSE_BLOCKED`` envelopes
   * - **MetricsService + AnalyticsHelper**
     - per envelope emission
     - Per-event-type tracking (latency, success, error rates)
   * - **OpenInference tracing**
     - per-request OISpan
     - Distributed tracing — every chat-stream call has spans
   * - **TimerFactory**
     - per-request timer
     - Time-to-first-byte, time-to-final-response
   * - **AgentUserContext**
     - via ``AgentUserContext`` workflow type
     - Per-(agent, user) context (memories, preferences)
   * - **FeatureFlagEvaluation**
     - emitted as part of envelope ``ConvoAiV1StreamMessageMetadata``
     - Lets clients log which FFs were evaluated for this turn

The 4 executor variants
==========================

The "central dispatcher" ``RovoChatAgentExecutionService`` (1,424 LoC)
routes between **4 distinct executor variants**:

.. list-table::
   :header-rows: 1
   :widths: 30 14 56

   * - Executor
     - LoC
     - Use case
   * - ``MarathonAgentExecutorImpl``
     - 803
     - **The standard chat path.** Handles all "normal" agent execution (Marathon/SAIN/AIFC/AgentStudio agents). Despite the name, it dispatches to many orchestrator types.
   * - ``A2AChatExecutor``
     - 1,370
     - Legacy Agent-to-Agent (A2A) protocol — agents calling other agents
   * - ``NewA2AChatExecutor``
     - 893
     - Newer A2A executor — replacement for ``A2AChatExecutor``; suggests ongoing migration
   * - ``RovoChatAsyncTaskLauncher``
     - 1,223
     - Async task offload — returns immediately with task id; events delivered via separate task-status stream

**Coexistence implication**: Both ``A2AChatExecutor`` and
``NewA2AChatExecutor`` exist with no clear sunset, similar to SAIN's
Hybrid coexistence pattern. **Same audit recommendation applies**:
add ``@Deprecated`` and a target sunset date.

The two response framings
============================

The system supports both framings:

* **NDJSON** (``application/x-ndjson``) — newline-delimited JSON
   * Used by: 4 of 5 streaming endpoints
   * Pros: simple to parse; works with HTTP/1.1 chunked encoding; minimal overhead
   * Cons: not directly compatible with browser ``EventSource`` API

* **SSE** (``text/event-stream``) — Server-Sent Events
   * Used by: 1 streaming endpoint (``/message/stream/sse``)
   * Pros: native browser ``EventSource`` support; auto-reconnect
   * Cons: more verbose ("data: ..." prefix per line); slightly larger payload

**Why both?** Likely because SSE is for browsers using ``EventSource``,
NDJSON is for clients that use a custom HTTP client (mobile apps,
backend integrations, the desktop app). The SSE endpoint is a
relatively recent addition.

Smells and concerns
=====================

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **2,966-LoC ``RovoChatService.kt``**
     - chat/service/
     - The single largest file. Conversation lookup + agent selection + history + dispatch all in one. Should split into: ConversationLoader, AgentResolver, MessageBuilder, DispatchCoordinator. ~3-4 days mechanical refactor.
   * - 🔴
     - **1,996-LoC ``MarathonAgentDefinitions.kt``**
     - chat/service/agents/
     - System-defined agent registry. 1,996 lines of agent definitions in one file. Should split per-agent or per-domain (Generic, Confluence, Jira, etc.).
   * - 🔴
     - **1,600-LoC ``RovoChatExecutor.kt``**
     - chat/service/executors/
     - Top-level executor. Same split principle.
   * - 🔴
     - **1,424-LoC ``RovoChatAgentExecutionService.kt``**
     - chat/service/executors/
     - The central dispatcher. Critical complexity hotspot.
   * - 🔴
     - **1,370-LoC ``A2AChatExecutor.kt`` AND 893-LoC ``NewA2AChatExecutor.kt`` coexist**
     - chat/service/executors/ + a2a/
     - Same pattern as SAIN Hybrid. Plan a sunset date for ``A2AChatExecutor``.
   * - 🟡
     - **23 endpoints in one controller**
     - rest/RovoChatV1Controller.kt
     - Above the threshold where splitting starts paying off. Consider per-domain controllers (ConversationController, MessageStreamController, FileController, etc.). Risk: breaks Spring URI conventions; better as a thin facade pattern.
   * - 🟡
     - **30+ stream message types in one enum**
     - RovoChatStreamingEntities.kt
     - The contract is wide. Tracking which types need which client renderers is complex. Worth a separate "envelope contract" doc with per-type schemas.
   * - 🟡
     - **WorkflowStreamResponse exists in TWO places** (rovo-api + csm-impl)
     - duplicated
     - csm-impl has its own ``WorkflowStreamResponse``. Cross-product duplication. Either share the contract or document why they differ.
   * - 🟡
     - **5 streaming endpoints with subtly different semantics**
     - Controller
     - action/stream + message/stream + message/stream/sse + voiceMessage/stream + custom-action/.../message/stream. Easy for a contributor to add a 6th by accident. Worth a base helper.
   * - 🟡
     - **No formal envelope versioning** (V1 in name, but no v2 path visible)
     - RovoChatV1StreamMessageType
     - "V1" implies "V2 might come". When? Migration plan?
   * - 🟢
     - **Per-event MetricService emissions**
     - RovoChatAnalyticsHelperImpl
     - 30+ event types × N tags = high cardinality. Already mitigated by ``RovoChatAnalyticsHelperImpl`` but worth verifying cardinality stays bounded.
   * - 🟢
     - **No per-endpoint OpenAPI spec visible**
     - rest/
     - 23 endpoints with no published spec means external integrators must read source.

Refactoring opportunities
============================

1. **Split ``RovoChatService.kt``** (L, 🔴 high) — 2,966 LoC into ~4 services. ~3-4 days.

2. **Split ``MarathonAgentDefinitions.kt``** (M, 🔴 high) — 1,996 LoC of agent definitions per-domain or per-agent. ~2 days.

3. **Split ``RovoChatExecutor.kt``** (M, 🔴 high) — 1,600 LoC. ~2 days.

4. **Split ``RovoChatAgentExecutionService.kt``** (M, 🔴 high) — 1,424 LoC central dispatcher. ~2 days.

5. **Sunset ``A2AChatExecutor``** in favor of ``NewA2AChatExecutor`` (M, 🔴 high) — same pattern as SAIN Hybrid. Add ``@Deprecated`` first; migrate callers; remove.

6. **Add OpenAPI for ``RovoChatV1Controller``** (M, 🟡 medium) — 23 endpoints with no spec. Springdoc auto-generation is straightforward.

7. **Add an "envelope contract" doc** (XS, 🟡 medium) — per-type schemas for the 30+ ``RovoChatV1StreamMessageType`` values. Useful for client contributors.

8. **Consolidate ``WorkflowStreamResponse``** (S, 🟡 medium) — investigate why csm-impl has its own copy; share if possible.

9. **Add a base streaming helper** (S, 🟡 medium) — DRY the 5 streaming endpoints' setup code (response content type, error handling, async dispatch).

10. **Split per-domain controllers** (L, 🟢 low) — 23 endpoints into 5-7 controllers. Risk: client URL changes. Best done as a thin facade keeping URIs stable.

11. **Add Sphinx envelope-flow diagram for ``MarathonAgentDefinitions``** (XS, 🟢 low) — visualize the registered agents and their orchestrator routing.

What you would change here
============================

* **Add a new stream message type**:
   1. Add to ``RovoChatV1StreamMessageType`` enum
   2. Add data class with ``@JsonSubTypes`` registration
   3. Update ``RovoChatAgentStreamingWriter`` to emit it
   4. Notify all client teams (web, mobile, desktop, voice, debugger)

* **Add a new chat endpoint** → new method on ``RovoChatV1Controller`` (preferred) OR new per-domain controller (if cohesive)

* **Add a new executor variant** → new ``XxxChatExecutor.kt`` in ``executors/``; register in ``RovoChatAgentExecutionService``'s dispatch logic

* **Modify a system-defined agent's config** → ``MarathonAgentDefinitions.kt`` (find the relevant agent by name)

* **Tweak streaming output buffering** → ``RovoChatStreamOutputHandler.kt`` (808 LoC)

* **Add per-event analytics tag** → ``RovoChatAnalyticsHelperImpl.kt`` (679 LoC)

* **Add a new safety event type** → enum + envelope class + safety pipeline integration

* **Change conversation history loading** → ``RovoChatService.kt`` history-loading methods

What you would NOT change here
================================

* Conversation storage backend — owned by ``platform/conversation/``
* Tool/plugin registry — owned by ``platform/toolregistry/``
* Agent-store implementations — owned by ``rovo-api/.../agent/`` + AgentStudio
* Orchestrators themselves — owned by their respective sub-packages
* Safety pipeline — owned by safety services (prompt/response moderation)
* OpenInference tracing — owned by Atlassian platform

Sub-agent feedback (corrections + supplements)
=================================================

The investigating sub-agent reported:

* ``streamhub/`` is a top-level module — **WRONG**. It is a package
  inside ``platform/base/base-api/``, not a top-level Gradle module. No
  such directory exists at ``modules/streamhub/``.
* ``WorkflowStreamingResponseWriter`` exists — **WRONG NAME**. The
  actual class is ``WorkflowStreamResponse`` (the data contract), and
  the writer is ``RovoChatAgentStreamingWriter`` (1,220 LoC) +
  ``RovoChatStreamOutputHandler`` (808 LoC).
* ``RovoChatAgentExecutionService`` is the dispatcher — **CONFIRMED**
  (1,424 LoC, location verified).
* ``AssistanceServiceWorkflowServiceImpl`` exists — **CONFIRMED** at
  ``rovo-impl/.../product/rovo/workflow/AssistanceServiceWorkflowServiceImpl.kt``.

Verification audit log
========================

✅ **Personally verified with bash:**

* ``chat/`` has only 2 sub-dirs: ``cache/`` (8 LoC, 1 file) and ``service/`` (25,600 LoC, 62 files)
* All top-15 file LoC counts (find + sort)
* 30+ envelope types in ``RovoChatV1StreamMessageType`` enum (read first 80 lines of file)
* All 23 REST endpoint paths and HTTP methods (grep ``@(Get|Post|Put|Delete)Mapping``)
* ``RovoChatStreamingEntities.kt`` is 261 LoC; located at ``rovo-api/.../chat/streaming/``
* ``WorkflowStreamResponse.kt`` exists at 2 locations (rovo-api + csm-impl)
* ``AssistanceServiceWorkflowServiceImpl.kt`` exists at expected path
* The 5 streaming endpoints' content-type production:
   * 4 ``application/x-ndjson``
   * 1 ``MediaType.TEXT_EVENT_STREAM_VALUE`` (SSE)
* RovoChatV1Controller imports show ``StreamingResponseBodyFactory``, ``StreamingResult``, ``AsyncStreamingWriterReceiver`` from ``platform/base/base-api``
* ``MarathonAgentDefinitions.kt`` is at ``service/agents/`` (1,996 LoC)

⚠️ **Inferred from imports + naming**:

* End-to-end flow ordering (HTTP → Controller → Service → Executor → ...) — based on file responsibilities, not from a deep read of dispatcher logic
* The "thin-facade" potential of consolidating controllers — design suggestion, not source-verified
* The relationship between A2AChatExecutor and NewA2AChatExecutor — naming-based inference; could be parallel (different protocol versions) or serial (replacement)
* Whether ``RovoChatStreamOutputHandler`` does buffering, or just streams immediately — name suggests buffering

❌ **UNVERIFIED:**

* The actual flow of ``conversationMessageCreateStream()`` in
  ``RovoChatV1Controller`` — has 100+ lines of business logic at line
  810 onward; would need close reading
* Whether ``WorkflowStreamResponse`` (rovo-api) and the csm-impl
  variant are intentionally different
* The dispatcher (``RovoChatAgentExecutionService``) routing rules
  (which conditions pick Marathon vs A2A vs Async)
* The ``ConvoAiV1StreamMessageEnvelope`` shape (only the type enum was read)
* Per-endpoint authentication / authorization annotations (some have ``@HelpSeekerAllowed``, ``@CustomerAccountAllowed``, ``@EndUserEndpoint`` per import list)
* Streaming buffer size, flush cadence, backpressure handling

Open questions for institutional knowledge
=============================================

1. **Why two A2A executors** (legacy + new)? What's the migration plan?
2. **What's the sunset for the legacy A2A executor** (1,370 LoC)?
3. **Is there a V2 streaming envelope coming?** "V1" in name implies a planned V2.
4. **Why does CSM have its own ``WorkflowStreamResponse``?** Intentional divergence or duplication debt?
5. **What's the current envelope cardinality limit?** 30+ types × N tags — could be high-cardinality risk on metrics.
6. **What's the per-endpoint typical latency** (P50, P95) for ``/message/stream`` end-to-end?
7. **Is there a streaming-protocol contract test** that catches accidental envelope-shape changes?

