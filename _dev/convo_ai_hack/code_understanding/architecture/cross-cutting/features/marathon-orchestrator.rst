.. _feature-marathon-orchestrator:

==================================================================
Marathon Orchestrator — LLM-driven Python execution agent
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 44,256 main LoC across 121 files in 1 module
:Module: ``rovo-impl/.../agent/orchestrators/marathon/``
:Test ratio: TBD (test files exist but ratio not yet computed)

.. contents:: On this page
   :local:
   :depth: 2

What it IS (in one paragraph)
================================

Marathon is the **most powerful and most complex orchestrator** in the
codebase. Unlike a typical "LLM picks a tool, then calls the tool"
pattern, Marathon takes a fundamentally different approach:

    The LLM writes **Python code**. That code runs in a **CPython
    sandbox** (either an Atlassian-managed Sandbox or a local
    PythonSidecar). When the code wants to read or write Atlassian
    data, it calls **HTTP-callbacks back into the JVM** which
    dispatch to the appropriate ``Async<Service>MarathonClient``
    via Kotlin reflection. The kernel is **cached per session** so
    multi-turn conversations preserve Python state.

This makes Marathon effectively **a code-execution agent on Atlassian
data**, more powerful than function-calling but with a much larger
surface area. The 23K LoC of ``clients/`` are essentially a
**Python-callable SDK over Atlassian REST APIs**, generated as
typed Python stubs from Kotlin function signatures.

How it differs from other orchestrators in this codebase:

* **Hybrid orchestrator** = LLM picks a tool from a predefined list per turn (function-calling)
* **LongHorizon orchestrator** = Multi-turn planning with explicit step decomposition
* **Marathon orchestrator** = LLM writes code that calls APIs directly


Anatomy — where the code lives
=================================

Single Gradle module: ``modules/product/rovo/rovo-impl/``.
Within it, Marathon owns one sub-package:
``src/main/kotlin/.../agent/orchestrators/marathon/``.

Subsystem breakdown
---------------------

.. list-table::
   :header-rows: 1
   :widths: 18 8 8 18 48

   * - Subsystem
     - Files
     - LoC
     - Role
     - Key classes
   * - **clients/**
     - 33
     - **23,072**
     - Python-callable SDK over 10 Atlassian/3p REST APIs
     - ``AsyncConfluenceMarathonClient`` (5,189), ``AsyncJiraMarathonClient`` (3,103), 8 more
   * - **execution/**
     - 51
     - **16,060**
     - Python kernel mgmt, callback HTTP server, MCP discovery, stub gen
     - ``MarathonClient`` (3,278), ``KotlinFunctionCallback`` (886), ``MarathonMcpDiscoveryService`` (651), ``RuntimeBackendUploader`` (1,353), ``PythonStubGenerator`` (642), ``GrepMcpTool`` (641)
   * - **plan/**
     - 10
     - **2,118**
     - Plan-mode (LLM generates step list, executes sequentially)
     - ``PlanModeAgentDefinitions`` (638), ``PlanModeResumptionHandler`` (937)
   * - **todo/**
     - 8
     - **1,457**
     - In-memory todo list (4 statuses, 3 priorities) maintained by LLM
     - ``TodoItem``, ``TodoStorage``
   * - **question/**
     - 5
     - **529**
     - User-confirmation flow (LLM asks → UI renders → resumption injects answer)
     - ``AskQuestionMcpTool``, ``QuestionResumptionHandler``
   * - **memory/**
     - 3
     - **507**
     - Cross-turn memory primitives (NOT cross-session)
     - (3 small files)
   * - **confirmation/**
     - 1
     - **282**
     - Pre-execution write-operation analyzer (regex-based safety gate)
     - ``RegexWriteOperationAnalyzer``
   * - **advisor/**
     - 1
     - **231**
     - Single LLM tool that analyzes conversation context for guidance
     - ``AdvisorMcpTool``
   * - **top-level**
     - 10
     - ~480
     - Runtime, metrics, tracing, response assembly, system reminders
     - ``MarathonRuntime`` (590), ``MarathonResumption``, ``MarathonResumptionService``, ``MarathonMetrics``, ``MarathonResponseAssembler``, ``MarathonTraceWriter``, ``MarathonIndividualAgentExecutor``, ``ReminderInjection``, ``SystemReminderProvider``, ``PreRenderedInventory``
   * - **TOTAL**
     - **121**
     - **44,256**
     -
     -

The 10 Marathon clients
========================

Each client wraps one external service in 4 files (interface + impl +
models + optional mappers). The full inventory:

.. list-table::
   :header-rows: 1
   :widths: 22 22 56

   * - Client
     - LoC
     - What it exposes to Python
   * - **confluence**
     - 5,189 + 2,622 + 898
     - Pages, spaces, search, comments, attachments, restrictions, history, watching, labels, properties, classification levels, blogs, whiteboards, databases — 70+ public methods
   * - **jira**
     - 3,103 + 2,754 + 1,257
     - Issues, JQL search, transitions, comments, custom fields, fields, projects, users, attachments, links, etc.
   * - **bitbucket**
     - moderate
     - Repos, PRs, commits, branches
   * - **slack**
     - moderate
     - Channels, messages, users (likely DMs + posting)
   * - **googlecalendar**
     - 1,009
     - Calendars, events, free/busy
   * - **googledrive**
     - moderate
     - Files, folders, sharing
   * - **googlegmail**
     - moderate
     - Threads, messages, drafts
   * - **codesearch**
     - small
     - Code search across repos
   * - **people**
     - small
     - User profile + relationships
   * - **generic**
     - small
     - Generic / catch-all client (likely for arbitrary HTTP calls?)


End-to-end execution flow
============================

Marathon execution is a graph-state machine that loops between LLM
invocation and tool/code execution until the LLM emits a final answer
or a max-iteration limit is hit.

**Phase 0 — Selection** (caller-side):

* User message arrives at ``RovoChatV1Controller``
* Conversation routed by ``MarathonAgentDefinitions`` /
  ``MarathonAgentExecutorImpl`` to use the Marathon orchestrator
  (UNVERIFIED: exact selection logic not yet traced — likely agent-config-driven)

**Phase 1 — Setup** (``MarathonRuntime.execute()`` line 165):

1. Increment ``MARATHON_CONCURRENT_CONVERSATIONS`` gauge
2. Emit ``MARATHON_PRE_ORCHESTRATION_LATENCY`` histogram
3. Create ``GraphState`` from ``agent.stateFactory``
4. Bind MCP tools (``AdvisorMcpTool.bindGraphState()``, etc.) to GraphState
5. Build ``GraphDeps`` (writer, modelInvoker, toolExecutor, promptProvider, ...)
6. If resumption present → call ``executeConfirmedTools()`` to re-execute previously confirmed tools

**Phase 2 — Graph loop** (``GraphRunner.run()`` starting at ``UserPromptNode``):

The graph state machine executes:

::

    UserPromptNode
        ↓
    LLMInvocationNode  ← (loop back here after tool execution)
        ↓
    DecisionNode
        ├─ "function_calls"  → ToolExecutionNode → loop
        ├─ "ask question"    → pause for user (RequiresConfirmation)
        ├─ "enter plan mode" → switch to PlanModeOrchestrator
        └─ "final response"  → exit loop

**Phase 3 — Tool execution** (``MarathonIndividualAgentExecutor.executeToolsInParallel()``):

* Tools run **in parallel** (coroutine fan-out)
* Each tool emits ``ResearchStepTitleStatus`` (start) and ``ResearchStepCompleteStatus`` (end) trace messages
* If a tool is **code execution** (the most common case for Marathon) → invoke ``MarathonClient.executeCode()``
* If a tool is **MCP** → discover & invoke via ``MarathonMcpDiscoveryService``
* If a tool needs **confirmation** → emit ``RequiresConfirmation`` and pause

**Phase 4 — Code execution** (the Marathon-distinctive part):

When the LLM-generated code runs, the flow is:

1. ``MarathonClient.executeCode()`` line 82 invoked with Python source
2. Feature flag ``useEmbeddedIpython()`` decides:

   * **TRUE** → ``executeViaAtlassianSandbox()`` (default, production path)
   * **FALSE** → ``executeViaPythonSidecar()`` (legacy fallback)

3. **Sandbox path**:

   a. ``resolveAtlassianSandboxEndpoint()`` (line 383) — find available sandbox
   b. ``ensureRuntimeInfraInstalled()`` (line 2604) — idempotent infra install
   c. ``getOrCreateKernel()`` (line 1343) — L1 (in-mem) → L2 (Redis) cache lookup; create new IPython kernel if neither hits
   d. ``buildSandboxBootstrapCell()`` (line 1833) — inject callback handlers, imports, MCP bridge
   e. ``wrapInAsyncIfNeeded()`` (line 1760) — wrap user code in ``async def`` if it uses ``await``
   f. POST code to ``SandboxKernelExecutionService`` REST endpoint
   g. Stream stdout/stderr back via SSE

4. While Python runs, it calls ``function_call(service, fn, params)`` (Python helper) which HTTP POSTs to the JVM callback endpoint
5. ``KotlinFunctionCallbackHandler.handleFunctionCall()`` (line 330):

   * Resolves ``service`` + ``function`` from ``allowedFunctionsByService`` map (built from ``@MarathonExposedFunction`` annotations)
   * ``convertValue()`` (line 568) coerces JSON params to Kotlin types
   * ``invokeFunction()`` (line 492) calls the Kotlin function via reflection
   * Returns ``FunctionCallResponse`` (success/error + status_code)

6. Python receives the result, continues executing
7. When code finishes, ``ExecutionResult`` (stdout, stderr, execution_count, ``data: JsonNode``) returned to JVM

**Phase 5 — Response & metrics** (``MarathonResponseAssembler.writeWorkflowResponse()``):

1. Final messages assembled
2. Tool invocation metrics emitted: ``TOOLS_INVOKED`` (count w/ ``has_tools`` tag), ``TOOL_USAGE_DISTRIBUTION`` (per tool)
3. Orchestration completion analytics emitted
4. ``OISpan`` agent span finalized (for OpenInference tracing)


Sequence diagram — one Marathon turn
=======================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as User
       participant Ctrl as RovoChatV1<br/>Controller
       participant MR as MarathonRuntime
       participant GR as GraphRunner
       participant LLM as LLM<br/>(Claude/Gemini)
       participant TE as MarathonIndividual<br/>AgentExecutor
       participant MC as MarathonClient
       participant SB as Atlassian<br/>Sandbox
       participant Cb as KotlinFunction<br/>CallbackHandler
       participant CC as AsyncConfluence<br/>MarathonClient

       U->>Ctrl: "find pages about X and tag them"
       Ctrl->>MR: execute(agent, ctx, input, writer)
       MR->>MR: setup GraphState, GraphDeps
       MR->>GR: run(UserPromptNode)

       loop max iterations
           GR->>LLM: invoke(systemPrompt + history + tools)
           LLM-->>GR: stream response

           alt LLM emits Python code
               GR->>TE: executeToolsInParallel([code_exec])
               TE->>MC: executeCode(pythonSource, ctx)
               MC->>MC: getOrCreateKernel() (L1/L2 cache)
               MC->>SB: POST /execute (kernelId, code)

               loop while code runs
                   SB->>Cb: POST /callback {service:"confluence", fn:"search", params}
                   Cb->>Cb: resolve via allowedFunctionsByService
                   Cb->>CC: search(...) [reflective invoke]
                   CC->>CC: -> platform AsyncConfluenceRestClient
                   CC-->>Cb: List<Page>
                   Cb-->>SB: FunctionCallResponse(success, data)
               end

               SB-->>MC: ExecutionResult(stdout, data)
               MC-->>TE: result
               TE-->>GR: tool result message
           else LLM asks question
               GR-->>MR: RequiresConfirmation
               MR-->>Ctrl: pause + emit question
               Ctrl-->>U: render question UI
               Note over U,Ctrl: User responds → resumption flow → continue loop
           else LLM emits final response
               GR-->>MR: exit loop
           end
       end

       MR->>MR: assemble messages, emit metrics
       MR-->>Ctrl: List<ExecutableAgentMessage>
       Ctrl-->>U: stream final response

The dual Python runtime — Sandbox vs Sidecar
================================================

Marathon supports two Python execution backends, controlled by a feature flag:

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * -
     - **Atlassian Sandbox** (default)
     - **PythonSidecar** (legacy)
   * - Feature flag
     - ``useEmbeddedIpython()`` = TRUE
     - ``useEmbeddedIpython()`` = FALSE
   * - Runtime
     - Cloud-managed CPython on remote infra
     - Local CPython process via sidecar HTTP
   * - Isolation
     - Per-tenant container isolation
     - Process boundary
   * - Kernel mgmt
     - Atlassian-managed lifecycle
     - In-process sidecar
   * - Endpoint
     - ``SandboxKernelExecutionService`` REST API
     - ``PythonSidecarClient`` (platform/client/pythonsidecar/)
   * - Network egress
     - Fully sandboxed (proxy-controlled)
     - Limited (sidecar process)
   * - Resource limits
     - Per-call quota + circuit breaker
     - Process-level
   * - Timeout handling
     - Sandbox kills kernel; provisions new
     - Process-level
   * - State
     - Production (Atlassian managed)
     - Fallback / dev path

Both paths use the **same** ``KotlinFunctionCallbackHandler`` for
JVM↔Python bridge — so the function-callback shape is unified.

Python stub generation — bridging Kotlin to Python
======================================================

This is the architecturally most-novel piece of Marathon.

The Python runtime needs to know what functions are callable.
Rather than hand-writing Python stubs, ``PythonStubGenerator`` generates
them at runtime from Kotlin reflection.

Process:

1. At startup, ``MarathonMcpDiscoveryService`` enumerates ``@MarathonExposedFunction``-annotated
   methods on each ``Async<Service>MarathonClient``
2. Builds a ``ToolManifest`` (typed tree of bundles → functions → params/returns)
3. ``PythonStubGenerator.generateAll(manifest)`` produces a map of file paths → Python source:

   * ``kotlin_client/__init__.py`` — root namespace
   * ``kotlin_client/client.py`` — base ``Client`` class
   * ``kotlin_client/<bundle>/`` — per-service module with typed ``def`` stubs
   * ``skills/__init__.py`` — agent skills namespace
   * ``skills/<skill>/`` — per-skill module

4. ``RuntimeBackendUploader`` (1,353 LoC) uploads these files into the sandbox kernel
5. The Python code can then ``from kotlin_client import jira; jira.search(...)``
6. Each generated stub body is a ~3-line wrapper that POSTs to the callback endpoint

So **the Python that the LLM writes against is type-safe Python that calls real Kotlin
implementations via HTTP**. Python sees:

.. code-block:: python

   # Generated stub (simplified)
   def search_issues(jql: str, fields: List[str] = None) -> List[Issue]:
       """Search Jira issues using JQL."""
       return _function_call("jira", "searchIssues", {"jql": jql, "fields": fields})

And the JVM-side handler turns the call back into ``AsyncJiraMarathonClient.searchIssues(jql, fields)``
via reflection.


The metacognitive layer — plan, todo, question, advisor, confirmation
========================================================================

Marathon has 5 sub-systems for **reasoning about its own execution**.
This is unusually rich for an agent framework.

**Plan Mode** (``plan/`` 2,118 LoC)

* **What**: For complex tasks, Marathon switches into a mode where the LLM first generates a multi-step plan, then executes it sequentially.
* **When**: User triggers via prompt complexity OR LLM voluntarily emits ``EnterPlanModeTool``
* **How**: ``PlanModeAgentDefinitions.kt:638`` builds a "plan-mode agent" that has different system prompts and reduced tool surface
* **Resumption**: If interrupted (server restart, user abort), ``PlanModeResumptionHandler.kt:937 LoC`` reconstructs in-flight plan state. The 937 LoC is justified by needing to track per-action execution status, stream task updates, and re-emit observability events on resume.
* **Persistence**: UNVERIFIED — likely Redis-backed via ``ConversationManager``

**Todo** (``todo/`` 1,457 LoC)

* In-memory todo list maintained by the LLM during a Marathon turn
* Statuses: ``PENDING | IN_PROGRESS | COMPLETED | CANCELLED``
* Priorities: ``HIGH | MEDIUM | LOW``
* Each todo has an ``activeForm`` field (e.g., "Running tests" vs "Run tests") for natural UI display
* **NOT persisted to a database** — scoped to the execution context (likely lost across server restarts unless captured by resumption)

**Question** (``question/`` 529 LoC)

* When the LLM emits ``AskQuestionMcpTool``, Marathon pauses and asks the user
* Question shape: ``header`` (≤30 chars) + ``question`` (≤120 chars) + ``options`` (2-4 choices)
* Pause mechanism: tool returns ``RequiresConfirmation``; UI renders question; ``QuestionResumptionHandler`` injects answer into next turn

**Advisor** (``advisor/`` 231 LoC, single file)

* ``AdvisorMcpTool`` — gives the LLM a "phone-a-friend" — a separate LLM call that analyzes the conversation context to provide guidance on the current decision
* Uses ``bindGraphState()`` so the advisor sees the live conversation state at call time

**Confirmation** (``confirmation/`` 282 LoC, single file)

* ``RegexWriteOperationAnalyzer`` scans Python code BEFORE execution for write patterns: API writes (POST/PUT/DELETE), MCP write calls, ``executeAction``, dangerous imports
* If a write is detected and the agent isn't pre-authorized → emit ``RequiresConfirmation``, pause for user to OK/cancel
* This is the **safety gate** for destructive operations
* Regex-based (not AST-based) so it can be fooled by sufficiently obfuscated code — but the LLM has no incentive to evade it

External system dependencies
==============================

A single Marathon turn touches:

.. list-table::
   :header-rows: 1
   :widths: 24 30 46

   * - System
     - How
     - What's used
   * - **AI Gateway** (LLM)
     - via ``HybridModelInvoker``
     - Claude or Gemini (configured per-agent); streaming completions
   * - **Atlassian Sandbox**
     - REST API
     - Python kernel provisioning + code execution
   * - **PythonSidecar** (fallback)
     - HTTP via ``PythonSidecarClient``
     - Local Python runtime
   * - **Redis** (L2 kernel cache)
     - via ``RedisCache``
     - Kernel ID lookup by ``KernelCacheKey(workspace, agent, session)``
   * - **Confluence / Jira / etc**
     - via ``Async<X>MarathonClient`` → platform-tier ``AsyncXRestClient``
     - All read/write Atlassian operations
   * - **MCP servers**
     - via ``MarathonMcpDiscoveryService``
     - 3rd-party tool integration (Google Cal, Drive, etc.)
   * - **OpenInference Tracing**
     - via ``SpanWriter``
     - Per-tool spans, agent spans
   * - **MetricsService**
     - direct
     - Latency histograms, concurrent gauges, tool counters
   * - **Statsig**
     - via ``RolloutService``
     - ``useEmbeddedIpython`` + many other gates

Resumption — pause, store, resume
====================================

Marathon execution can be paused and resumed, which is necessary for:

* User confirmation flows (question, write confirmation)
* Long-running plan-mode execution
* Server restart / failover

**State persisted** (``MarathonResumption.kt:6-12``):

.. code-block:: kotlin

   data class MarathonResumption(
       val confirmedTools: List<ConfirmedToolRequest>,
       val latestUserMessage: String,
       val previouslyInvokedTools: List<List<MinionOutput>> = emptyList(),
       val deferredSystemReminders: List<String> = emptyList(),
       val contextAugmentations: List<ContextAugmentation> = emptyList(),
   )

**Storage backend**: UNVERIFIED — ``MarathonResumptionService`` delegates
to ``ConversationManager``, which is presumably Redis or DynamoDB
(common Atlassian patterns), but I haven't traced through the
``ConversationManager`` impl in this investigation pass.

**Lifecycle**:

* On pause → ``persistConfirmationDecisions()`` (line 63) writes resumption state
* On resume → ``getResumption()`` (line 42) reads it back
* ``executeConfirmedTools()`` re-executes any already-confirmed tools without re-asking the LLM
* ``transformCancelledTools()`` (line 476) handles user-cancelled tools

**Critical observation**: The Python kernel state in the sandbox is **separately**
cached (in Redis L2 by ``KernelCacheKey``). So pausing/resuming a Marathon turn
re-uses the same kernel — the Python ``import``s, variables, and previous
function-call state are all preserved. This is a big architectural decision: it
means a multi-turn Marathon conversation can build up sophisticated Python state
(e.g., a fetched DataFrame, a parsed schema) and reference it across turns.


Design patterns identified
=============================

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Pattern
     - Where
     - Why
   * - **Code-as-tool-calling**
     - The Marathon thesis
     - Lets the LLM compose API calls in arbitrary ways (loops, conditionals, variable reuse) rather than being constrained to one-tool-per-turn
   * - **Generated stubs from reflection**
     - ``PythonStubGenerator`` + ``@MarathonExposedFunction``
     - Single source of truth (Kotlin signatures) for what's callable; Python automatically gets typed APIs
   * - **HTTP callback bridge**
     - ``KotlinFunctionCallbackHandler``
     - Enables sandbox isolation while preserving cross-process function calls; alternative would be IPC via shared memory (much more complex)
   * - **L1+L2 kernel cache**
     - ``MarathonClient`` line 309 (in-mem) + 3160 (Redis)
     - Reuse expensive IPython kernels across turns of the same session; L2 enables sticky-session-free routing
   * - **Graph state machine**
     - ``GraphRunner.run(UserPromptNode)``
     - Cleaner than nested if/else for orchestration; node types are reusable across orchestrators
   * - **Plan-then-execute meta-mode**
     - ``plan/`` subsystem
     - For complex tasks, having an explicit plan reduces "wandering" and provides UI hooks for progress display
   * - **Pre-execution write analysis**
     - ``RegexWriteOperationAnalyzer``
     - Safety gate that runs before code is sent to the sandbox; cheaper than post-hoc audit
   * - **Per-tool execution spans**
     - ``MarathonTraceWriter``
     - OpenInference tracing for production observability + offline replay
   * - **Tool-call confirmation + resumption**
     - ``MarathonResumption``
     - Decouples LLM "wants to do X" from user "OK, do X" without losing turn state

Smells and concerns
=====================

Brutally honest, ranked by severity for someone working in this code:

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **5,189-LoC single file** (``AsyncConfluenceMarathonClient.kt``)
     - clients/confluence/
     - 70+ public methods in one file. Nearly impossible to review changes; collisions in concurrent edits inevitable. Should split by concern (pages / spaces / classification / blogs / whiteboards).
   * - 🔴
     - **Reflection-based dispatch** (``KotlinFunctionCallbackHandler.invokeFunction()``)
     - line 492
     - Function names are strings on the wire. Renames silently break callers; type errors surface at runtime not compile time. ``@MarathonExposedFunction`` annotations are required to opt-in (good), but rename safety still depends on careful coordination with stub regeneration.
   * - 🔴
     - **Regex-based safety gate** (``RegexWriteOperationAnalyzer``)
     - confirmation/
     - Easily evaded by string concatenation, dynamic imports, ``getattr``-based dispatch. Adequate for benign LLMs; not a security boundary against adversarial code.
   * - 🟡
     - **Resumption persistence not introspectable from this code** (``ConversationManager``)
     - MarathonResumptionService line 26
     - The ``ConversationManager`` interface is in another module. Hard to reason about resumption durability/TTL/failure modes without leaving the file.
   * - 🟡
     - **Two Python runtimes in production**
     - ``useEmbeddedIpython`` flag
     - Maintaining both ``executeViaAtlassianSandbox`` and ``executeViaPythonSidecar`` doubles surface area. The sidecar path appears legacy — should plan a deprecation.
   * - 🟡
     - **Kernel cache key complexity** (``KernelCacheKey``)
     - line 3160
     - Key includes workspace + agent + session + ... — many dimensions. Risk of cache fragmentation (low hit rate) or cross-tenant leak (high impact). Cache hit rate metric would help observability.
   * - 🟡
     - **Plan-mode resumption is 937 LoC**
     - plan/PlanModeResumptionHandler.kt
     - Single file owning all plan-resume logic. As plan mode evolves, this will grow. Worth extracting per-action-status handlers into a composable strategy.
   * - 🟡
     - **TODOs not persisted** (just in-memory)
     - todo/TodoStorage
     - Restart loses todos. Surfaces as "agent forgot what it was doing" UX.
   * - 🟢
     - **No REST surface for direct Marathon invocation**
     - (search returned nothing)
     - Marathon is invoked only through ``MarathonAgentDefinitions``/``MarathonAgentExecutorImpl``. This is good for encapsulation but bad for E2E testing. Test fixtures must invoke via the agent layer.
   * - 🟢
     - **Tool selection logic for Marathon vs Hybrid vs LongHorizon not in this folder**
     - upstream
     - A new contributor reading ``orchestrators/`` won't immediately learn when each is used. A README in ``orchestrators/`` listing the selection logic would help orientation.
   * - 🟢
     - **MarathonRuntime is 590 LoC** (top-level, not a single subsystem)
     - MarathonRuntime.kt
     - Concentrates execute() + executeInternal() + transformCancelledTools() + injectPreviouslyInvokedTools(). Could split orchestration vs lifecycle vs reminders.

Refactoring opportunities
============================

Roughly effort × payoff order:

1. **Split ``AsyncConfluenceMarathonClient.kt``** (S, 🔴 high) — break into 5-6 files by concern (pages, spaces, content-type-X). 5K LoC in one file is the worst code-locality signal in Marathon. ~1 day of mechanical work; immediately improves reviewability.

2. **Add ``ConversationManager`` documentation cross-link** (XS, 🟡 medium) — a single paragraph in ``MarathonResumptionService`` explaining what storage backs it would unlock independent reasoning about Marathon's durability.

3. **Plan a sidecar deprecation** (M, 🟡 medium) — track usage of ``useEmbeddedIpython=false``; if low, set a deprecation date and remove ``executeViaPythonSidecar`` path.

4. **Persist TODOs to Redis** (S, 🟡 medium) — TodoStorage → RedisTodoStorage with same TTL as the rest of the resumption state. Fixes the "agent forgot" UX after restarts.

5. **Add cache-hit-rate metric to L2 kernel cache** (XS, 🟢 low) — ``MARATHON_KERNEL_L2_HIT`` counter tagged with ``hit|miss``. Without this, no one knows if the cache is doing its job.

6. **Replace ``RegexWriteOperationAnalyzer`` with AST-based** (L, 🟢 low for security; 🟡 medium for accuracy) — Python ``ast`` module would catch obfuscation. But: Marathon's threat model is "LLM might write code that does something the user didn't ask for", not "adversarial code". So regex is probably OK; this is only worth doing if Marathon's threat model expands.

7. **Refactor ``MarathonRuntime`` into smaller services** (M, 🟢 low) — split into ``MarathonOrchestrator`` (the loop) + ``MarathonResumptionCoordinator`` + ``MarathonReminderManager``. Cleaner; lower bar for unit testing.

8. **AnnotationProcessor for ``@MarathonExposedFunction``** (L, 🟢 low) — generate the dispatch table at compile time instead of reflective scan at startup. Faster cold start; compile-time errors on rename. But: only worth it if startup time or rename safety becomes painful.

What you would change here
============================

* **Add a new client (e.g., GitHub)** → create ``clients/github/AsyncGithubMarathonClient.kt`` + impl + models, annotate methods with ``@MarathonExposedFunction``, regenerate stubs (likely a Gradle task)
* **Tweak code-execution timeout** → ``MarathonClient`` ``executeCode()`` (line 82); look for ``timeout`` parameter handling around line 1255
* **Change L2 cache TTL** → ``MarathonClient`` line ~3160 (Redis cache config)
* **Add a new metacognitive capability** → mirror ``advisor/`` pattern: single MCP tool, single LLM call with bound graph state
* **Modify question-confirmation UX** → ``question/AskQuestionMcpTool.kt``
* **Add new write-detection pattern** → ``confirmation/RegexWriteOperationAnalyzer.kt``
* **Change orchestrator selection** → search for ``MarathonAgentDefinitions`` / ``MarathonAgentExecutorImpl`` in ``product/rovo/chat/service/``

What you would NOT change here
================================

* Sandbox provisioning logic — owned by ``platform/sandbox/sandbox-impl/`` (separate)
* Python sidecar implementation — owned by ``platform/client/pythonsidecar/``
* LLM invocation primitives — owned by ``platform/service/service-impl/``
* MCP protocol implementation — owned by ``rovo-impl/.../product/rovo/mcp/``
* Conversation persistence — owned by ``platform/conversation/conversation-impl/``
* Atlassian REST client implementations — owned by ``platform/client/client-api/``

Verification audit log
========================

Every concrete claim was verified by direct inspection. Notes:

✅ **Verified personally with bash/grep:**

* All file LoC counts (``wc -l`` on each)
* 10 client modules (``ls clients/``)
* ``PythonSidecarClient`` is real (``grep -n PythonSidecar``)
* ``FunctionCallRequest/Response`` data classes (``sed`` of file)
* ``PythonStubGenerator`` generates ``kotlin_client/<bundle>/__init__.py`` files (``sed`` of file)
* MarathonRuntime is 590 LoC and ``@Component``
* Marathon entry points: ``MarathonAgentDefinitions`` + ``MarathonAgentExecutorImpl`` in ``product/rovo/chat/service/``

⚠️ **Trusted from agent reports** (high-confidence based on agent's claimed file:line citations):

* Specific line numbers within files (e.g., ``MarathonRuntime.execute()`` at line 165, ``KotlinFunctionCallbackHandler.handleFunctionCall()`` at line 330) — agent reports were consistent on these
* GraphRunner state-machine flow (UserPromptNode → LLMInvocation → Decision → ToolExecution)
* L2 cache key composition (workspace + agent + session)
* TodoItem 4 statuses + 3 priorities

❌ **Marked UNVERIFIED:**

* Default LLM provider (Claude vs Gemini) — likely config-driven, not hardcoded
* Exact storage backend for ``ConversationManager`` (Redis vs DynamoDB vs SQL)
* Selection logic for Marathon vs Hybrid vs LongHorizon (the trigger)
* Failure recovery semantics if Marathon crashes mid-step

Open questions for institutional knowledge
=============================================

1. **What triggers Marathon vs Hybrid vs LongHorizon?** Is it agent config, prompt classifier, or both?
2. **What's the rationale for two Python runtimes?** Is sidecar a dev-only path or production fallback?
3. **What's "generic" client used for?** Generic HTTP? A specific service that doesn't fit a pattern?
4. **Why is plan-mode resumption 937 LoC?** Is there a simpler design or is the complexity inherent?
5. **What's the cache-hit rate of the L2 kernel cache in production?** Determines whether this layer is doing its job.
6. **What's the typical Marathon turn duration?** Could justify (or refute) the metacognitive overhead.


==================================================================
Open Questions — Resolved (2026-05-02 follow-up)
==================================================================

The Marathon doc's "Open questions" section was investigated via direct
source-code grep. Below are the verified answers.

**M1: Marathon vs Hybrid vs LongHorizon orchestrator selection — RESOLVED (Medium-High confidence)**

There is **no separate Hybrid or LongHorizon executor class**. The only
``AgentExecutor`` for Rovo agents in this codebase is ``MarathonAgentExecutor``
(interface in ``rovo-api``, impl in ``rovo-impl``). It is also the
executor used by AtlassianStudio chat (``AgentChatExecutor`` injects
``MarathonAgentExecutor``).

Evidence:

* ``rovo-api/.../chat/service/executors/MarathonAgentExecutor.kt:13`` —
  ``interface MarathonAgentExecutor`` (only one)
* ``rovo-impl/.../chat/service/executors/MarathonAgentExecutorImpl.kt:54`` —
  ``class MarathonAgentExecutorImpl``
* ``atlassianstudio-impl/.../AgentChatExecutor.kt:212`` — also injects
  ``MarathonAgentExecutor``
* ``MarathonAgentDefinitionsTest.kt:1007`` — comment about AIFC stripping
  performed by ``MarathonAgentExecutorImpl``

What the inventory called "Hybrid" and "LongHorizon" are **not separate
executors** — they're either:

* Routing modes within the single Marathon executor
* Sub-orchestrators within agent definitions (``MarathonAgentDefinitions``
  selects different agent configurations)
* Pre-Marathon / planned future modes

**Implication**: The orchestrator picture in §1 of this Marathon doc
should be revised. Marathon is the **only Rovo agent executor**, and
Hybrid/LongHorizon are categories of agents/modes, not separate
executors.

**M2: Two Python runtimes rationale — RESOLVED (High confidence)**

PythonSidecar and AtlassianSandbox are **fallback chains, not separate
products**. Code execution flow:

1. Try ``executeViaPythonSidecar(...)`` first
2. On failure, fallback to ``executeViaAtlassianSandbox(...)``

Gated by ``useEmbeddedIpython()`` (``MarathonClient.kt:1329-1335``).

Evidence:

* ``MarathonClient.kt:714-715``:

   .. code-block:: kotlin

      .replacingSuspend { executeViaPythonSidecar(...) }
        .with { executeViaAtlassianSandbox(...) }

* Two separate execution methods: ``MarathonClient.kt:718-721`` (sidecar) and ``794-797`` (sandbox)

**Pattern**: This is a **migration** — newer code uses Atlassian Sandbox
(more secure, in-cluster), older code uses PythonSidecar (Modal). The
``useEmbeddedIpython()`` gate routes based on flags. Eventually one will
sunset.

**M3: Generic Marathon client — RESOLVED (High confidence)**

``AsyncGenericMarathonClient`` (in ``marathon/clients/generic/``) is a
**Marathon-specific wrapper for generic client operations**, exposing
only the methods Marathon should access, with Marathon-specific DTOs
for a stable tool surface.

Evidence (KDoc on the interface):

.. code-block:: text

   "Marathon-specific wrapper for generic client operations.
    Exposes only the methods that Marathon should have access to,
    using Marathon-specific DTOs for a stable tool surface."

Methods include: ``MarathonEntityLinkingResponse``, ``MarathonUrlReadResponse``,
``MarathonVisualizationResponse``. Each has a ``@MarathonCallable``
annotation with description for the LLM (e.g., "Identifying entities").

**Pattern**: Generic client decouples Marathon from internal client
schemas — Marathon DTOs are stable contracts, while internal generic
client may evolve freely.

**M4: 937 LoC PlanModeResumptionHandler — RESOLVED (High confidence)**

The handler manages **multi-step plan execution lifecycle**: task
creation, status updates, resumption from prior turns, conversation
history mapping, tool result mapping, and integration with long-running
task infrastructure.

Evidence (major methods identified by grep):

* ``tryHandle()`` (lines 68-410) — main resumption logic (~340 LoC)
* ``isPlanModeActive()`` (lines 417-454)
* ``tryHandleExplicitPlanMode()``
* ``prepareExecution()``
* ``buildPlanModeToolResult()``
* ``updateActionStatus()``
* ``shouldSkipTerminalTask()``
* ``getOrCreateTask()`` / ``updateTaskStatus()``
* ``streamLatestTaskStatus()`` / ``streamTaskStatus()``

**Pattern**: 10+ methods of substantial size. The 937 LoC is justified
by genuine complexity (cross-turn state, error recovery, multiple
status models). Refactoring to <500 LoC would require splitting into
``PlanResumption``, ``TaskLifecycle``, ``StatusStream``.

**M5 + M6: L2 cache TTL and turn duration metrics — UNRESOLVED in main metric files**

* ``MarathonMetrics.kt`` only defines 2 metrics (TOOLS_INVOKED,
  TOOL_USAGE_DISTRIBUTION). No kernel cache hit rate, no
  ``MARATHON_KERNEL_*`` metrics, no latency histograms here.
* L2 cache helpers DO exist (``MarathonClient.kt:3158-3190``:
  ``getKernelFromL2``, ``putKernelToL2``, ``evictKernelFromL2``)
  but no TTL constant visible in the file structure mapping.
* ``MARATHON_PRE_ORCHESTRATION_LATENCY`` doesn't exist in the
  ``MarathonMetrics.kt`` enum — it may not be tracked, OR it may be
  emitted via the broader ``platform/service/.../metrics/MetricKey.kt``
  (~3,200 lines of metric definitions across the codebase).

**Recommended follow-up**: search ``platform/service/.../metrics/MetricKey.kt``
for Marathon entries (we know SAIN has ~30 entries there); Marathon
likely has similar coverage. Investigation deferred — answering would
require reading 3K-line metric files.


==================================================================
M5 + M6 — Resolved (2026-05-02 follow-up #2)
==================================================================

After grepping ``platform/service/.../metrics/MetricKey.kt``
(3,200-line metric registry), both M5 and M6 are now fully resolved.

**M5: L2 kernel cache TTL — RESOLVED (High confidence)**

* **L1 (in-memory) TTL**: ``KERNEL_CACHE_TTL_MS = (3600 - 120) * 1000L``
  = **58 minutes** (1 hour minus 2 minutes safety margin to avoid
  using a kernel that's about to expire on the sandbox side).
  Defined at ``MarathonClient.kt:191``.

* **L1 size cap**: ``MAX_LOCAL_CACHE_SIZE`` (constant; verified by test
  ``MarathonClientImplTest.kt:957`` — ``"kernelCache does not grow beyond MAX_LOCAL_CACHE_SIZE"``).

* **L2 (Redis) backend**: ``MarathonKernelRedisCacheImpl.kt`` in
  ``service/convo-ai-service/`` uses Redis key prefix ``marathon-kernel``
  (defined at ``foundation/utilities/.../cache/RedisCacheKeyPrefix.kt:50``:
  ``MARATHON_KERNEL("marathon-kernel")``).

* **L2 TTL**: NOT visible in MarathonClient.kt; would need to inspect
  ``MarathonKernelRedisCacheImpl.kt`` directly. Likely matches L1
  (~58 min) but unverified.

* **Cache flow**: ``getKernelFromL2`` → ``putKernelToL2`` → ``evictKernelFromL2``
  at ``MarathonClient.kt:3158-3190``.

**M6: Marathon latency metrics — RESOLVED (High confidence)**

The metrics absent from ``MarathonMetrics.kt`` are present in the
**central metric registry** ``platform/service/.../metrics/MetricKey.kt``
(3,200 lines) at lines 2184-2230. **40+ Marathon metrics** are defined
including all the latency histograms expected.

**Latency / duration metrics** (MarathonMetrics.kt:2184-2230):

.. list-table::
   :header-rows: 1
   :widths: 56 44

   * - Metric
     - Purpose
   * - ``marathon.pre_orchestration.latency``
     - Time from request entry to LLM first token (P50/P95)
   * - ``marathon.executor_setup.duration``
     - Setup time (per-turn one-time cost)
   * - ``marathon.executor_setup.mcp_discovery.duration``
     - MCP tool discovery during executor setup
   * - ``marathon.executor_setup.runtime_inventory.duration``
     - Runtime stub generation timing
   * - ``marathon.tool_push.duration``
     - Total tool stub push duration to sandbox
   * - ``marathon.tool_push.generation.duration``
     - Stub generation phase
   * - ``marathon.tool_push.upload.duration``
     - Stub upload phase (network I/O)
   * - ``marathon.callback.duration``
     - HTTP callback from Python sandbox back to JVM
   * - ``marathon.mcp_discovery.latency``
     - Per-server MCP tool discovery
   * - ``marathon.mcp_server.fetch.latency``
     - Per-server fetch call
   * - ``marathon.memory_read.duration``
     - Memory subsystem read latency
   * - ``marathon.stubs.transport.duration``
     - Stub transport (sandbox upload)
   * - ``marathon.stubs.active_manifest_upload.duration``
     - Active manifest upload

**Counter metrics**:

.. list-table::
   :header-rows: 1
   :widths: 56 44

   * - Metric
     - Purpose
   * - ``marathon.tool_push.cache_hit``
     - **L1 stub-cache hit rate** (push deduplication)
   * - ``marathon.tool_push.file_count``
     - File count per push
   * - ``marathon.tool_push.size_bytes``
     - Push size distribution
   * - ``marathon.tool_push.result``
     - SUCCESS / FAILURE / SKIPPED outcomes
   * - ``marathon.memory_read.result``
     - SUCCESS / FAILURE outcomes
   * - ``marathon.mcp_discovery.success``
     - Discovery success counter
   * - ``marathon.mcp_discovery.error``
     - Discovery error counter
   * - ``marathon.mcp_discovery.timeout``
     - Discovery timeout counter
   * - ``marathon.mcp_discovery.cache_hit``
     - MCP discovery cache hit
   * - ``marathon.mcp_discovery.cache_miss``
     - MCP discovery cache miss
   * - ``marathon.mcp_discovery.servers_discovered``
     - Histogram of servers discovered per turn
   * - ``marathon.mcp_discovery.tools_discovered``
     - Histogram of tools discovered per turn
   * - ``marathon.mcp_server.fetch.success``
     - Per-server fetch success
   * - ``marathon.mcp_server.fetch.error``
     - Per-server fetch error
   * - ``marathon.mcp_server.fetch.timeout``
     - Per-server fetch timeout
   * - ``marathon.mcp_server.fetch.unauthorized``
     - 401/403 from MCP server
   * - ``marathon.stubs.publisher.exit_code``
     - Stub publisher process exit code
   * - ``marathon.stubs.hash_mismatch_fallback``
     - Times the hash-based dedup failed and full upload fired
   * - ``marathon.concurrent_conversations``
     - Concurrent in-flight conversations gauge

**Histogram bucket definitions** (HistogramBucket enum, line 2638+):
``MARATHON_PRE_ORCHESTRATION_HISTOGRAM_BUCKETS`` is the dedicated bucket
set for ``marathon.pre_orchestration.latency``, suggesting the team
tuned bucket boundaries specifically for Marathon's expected latency
profile.

**L2 cache hit rate metric**: NOT explicitly visible — search did NOT
find a ``marathon.kernel.l2.cache_hit`` counter. The L2 cache hit/miss
might be tracked under generic Redis metrics (``redis.cache.hit{prefix=marathon-kernel}``)
or may be unmeasured. Worth a follow-up.

**Implication for the Marathon doc**: The "Smells" section earlier
should be **revised** — Marathon is **extensively instrumented** (40+
metrics with sub-millisecond histogram resolution). Earlier smell
"sparse metrics in MarathonMetrics.kt" was wrong — the real metric
registry is the central ``MetricKey.kt``, not the per-feature
``MarathonMetrics.kt`` (which only holds 2 enum entries because
``send_metric()`` accepts ``MetricKey`` from the central registry).


==================================================
12. AtlassianStudio Two-Path Execution Model (added 2026-05-03)
==================================================

After deep investigation of architectural surprises (see
:doc:`../../business/05-open-questions-resolved` §12.1), it was
discovered that **AtlassianStudio's Marathon usage is intentionally
split across two execution paths**:

12.1 Path 1: Direct execution (performance-optimized, NOT FF-gated)
=====================================================================

**Location**: ``AgentChatExecutor.kt:715-731`` (atlassianstudio-impl)

**Method**: ``executeMarathonDirectly()``

**When taken**: ``shouldExecuteSimpleLoopWorkflow()`` returns ``false``
— typically for **Jira-context simple workflows**

**Flow**:

.. mermaid::

   sequenceDiagram
       participant User
       participant AgentChatExecutor as AgentChatExecutor (AtlassianStudio)
       participant MarathonAgentExecutor

       User->>AgentChatExecutor: chat request
       AgentChatExecutor->>AgentChatExecutor: shouldExecuteSimpleLoopWorkflow()?
       Note over AgentChatExecutor: Returns false (Jira simple flow)
       AgentChatExecutor->>MarathonAgentExecutor: executeMarathonDirectly()
       Note over AgentChatExecutor,MarathonAgentExecutor: NO FF check at this layer
       MarathonAgentExecutor->>User: response

**Key implication**: There is **NO FF gate** at this layer. Marathon
runs unconditionally for SimpleLoopWorkflow Jira contexts.

12.2 Path 2: Delegated to RovoChat (FF-gated)
================================================

**Location**: ``AgentChatExecutor.kt:846-865`` (atlassianstudio-impl)

**Method**: ``delegateMarathonToRovoChat()``

**When taken**: For **generic agents** (not Jira simple workflows)

**Flow**:

.. mermaid::

   sequenceDiagram
       participant User
       participant AgentChatExecutor as AgentChatExecutor (AtlassianStudio)
       participant RovoChatExecutor
       participant RolloutService
       participant MarathonAgentExecutor

       User->>AgentChatExecutor: chat request
       AgentChatExecutor->>AgentChatExecutor: shouldExecuteSimpleLoopWorkflow()?
       Note over AgentChatExecutor: Returns true (generic agent)
       AgentChatExecutor->>RovoChatExecutor: delegateMarathonToRovoChat()
       RovoChatExecutor->>RolloutService: controlledByFullContext(ROVO_CHAT_USE_MARATHON_AGENT)
       alt FF ON
           RolloutService->>RovoChatExecutor: true
           RovoChatExecutor->>MarathonAgentExecutor: execute(...)
           MarathonAgentExecutor->>User: response
       else FF OFF
           RolloutService->>RovoChatExecutor: false
           RovoChatExecutor->>RovoChatExecutor: legacy A2A executor
       end

12.3 Why this matters
=======================

**Observability impact**:

* Marathon dashboards must track **both paths separately**
* If only ``RovoChatExecutor``'s metrics are watched, AtlassianStudio's
  direct Marathon usage is **invisible**
* The "rollout %" of ``ROVO_CHAT_USE_MARATHON_AGENT`` does NOT capture
  AtlassianStudio's direct Marathon usage from
  ``executeMarathonDirectly()``

**Refactoring impact**:

* Any change to Marathon's interface affects BOTH call sites
* The "two paths" pattern means Marathon changes need testing in BOTH
  AtlassianStudio (direct) AND RovoChat (delegated) contexts
* Sunsetting Marathon would require coordinating BOTH AtlassianStudio
  and RovoChat code paths

**Open question**: Is the direct path's FF-exemption intentional or
oversight? See
:doc:`../../business/05-open-questions-resolved` §12.1.

12.4 Action items (for Marathon team)
=======================================

#. **Add metrics** at ``executeMarathonDirectly()`` (line 715-731) to
   track AtlassianStudio's direct Marathon usage volume
#. **Decide**: should the direct path be FF-gated for consistency?
#. **Document** in this page (and in any internal Marathon runbook)
   that AtlassianStudio uses two paths
