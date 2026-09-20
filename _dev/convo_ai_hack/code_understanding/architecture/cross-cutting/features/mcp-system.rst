.. _feature-mcp-system:

==================================================================
MCP System — Model Context Protocol integration (server + client)
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: ~41,304 main LoC across ~190 files spanning 3 modules
:Modules:

  * ``platform/client/client-api`` (MCPClient interface)
  * ``platform/client/client-impl`` (MCPClientImpl)
  * ``rovo-impl/.../product/rovo/mcp/tool/`` (MCP tool implementations)

.. contents:: On this page
   :local:
   :depth: 2

What it IS (in one paragraph)
================================

This codebase plays **two roles** in the MCP ecosystem:

1. **MCP server** — The codebase exposes internal Atlassian capabilities
   (Jira search, Confluence pages, code search, etc.) as MCP tools that
   external LLM clients (Claude Desktop, etc.) can invoke
2. **MCP client** — The codebase consumes external MCP servers (e.g.,
   3rd-party tools registered by users) via ``MCPClient`` from platform tier

The 41K LoC concentration in ``mcp/tool/`` is overwhelmingly the
**server side** — implementations of Atlassian-specific MCP tools.
The client side (``MCPClient.kt`` + ``MCPClientImpl.kt`` in platform
tier) is small (likely <1K LoC).

This is unusual — most codebases are MCP clients OR MCP servers, not
both. Atlassian's choice reflects "we want our agents to use MCP tools
AND we want third parties to call Atlassian MCP tools".

The 11 MCP tool sub-systems
==============================

.. list-table::
   :header-rows: 1
   :widths: 22 12 10 56

   * - Sub-system
     - LoC
     - Files
     - Role
   * - **jira/**
     - **17,335**
     - **60**
     - The dominant MCP surface. Contains JiraNL2JQLV2 (NL→JQL conversion, 2,275 LoC), JiraAgenticSearch (1,168), JiraJQLValidation (1,081), JiraDataPool (844), JiraRefinement (1,368). Multiple sub-modules for query, refinement, debugging, schema introspection.
   * - **google/**
     - 5,716
     - 46
     - Google Workspace integration: Calendar (events, ACL, free/busy, settings, colors), Drive, Gmail. ``AbstractGoogleMcpTool`` provides shared OAuth handling.
   * - **search/**
     - 3,993
     - 12
     - Cross-product search. ``SearchMcpTool`` (518 LoC) + ``AgenticSearchService`` (2,130 LoC) + agentic search internals.
   * - **teamwork/**
     - 3,190
     - 10
     - Teamwork Graph queries. ``TeamworkGraphQueryMcpTool`` (2,115 LoC) is the largest single file in MCP.
   * - **codesearch/**
     - 2,701
     - 21
     - Bitbucket code search across repos.
   * - **slack/**
     - 2,440
     - 22
     - Slack integration (channels, messages, users).
   * - **entitylinking/**
     - 1,996
     - 12
     - Cross-product entity resolution. ``EntityLinkingV3McpTool`` (615 LoC) — disambiguate "the Apollo project" → which Atlas project ARI.
   * - **admin/**
     - 1,664
     - 2
     - Atlassian admin operations: ``AdminGraphqlMcpTools`` (1,074), ``AdminGroupMcpTool`` (590).
   * - **pagesearch/**
     - 275
     - 3
     - Page-level (vs cross-product) search.
   * - **conversationsession/**
     - 123
     - 3
     - MCP tool for inspecting current conversation state.
   * - **websearch/**
     - 120
     - 1
     - Web search integration (likely Brave/Bing/Google search API).

Top-level MCP tools (in ``mcp/tool/`` directly, not in a sub-dir)
==================================================================

.. list-table::
   :header-rows: 1
   :widths: 36 14 50

   * - File
     - Approx LoC
     - Role
   * - ``DataSculptorMcpTool.kt``
     - moderate
     - Data shaping for LLM
   * - ``MetricsDataMcpTool.kt``
     - moderate
     - Metrics querying
   * - ``OntologyContextMcpTool.kt``
     - moderate
     - Domain ontology context
   * - ``PeopleMcpTool.kt``
     - moderate
     - User/team directory
   * - ``ReadyToAnswerTool.kt``
     - small
     - Pre-computed answer lookup
   * - ``ShouldUseLuminaToAnswerTool.kt``
     - small
     - Decision tool: should we use Lumina (lightweight classifier)?
   * - ``TeamworkAnalyticsMcpTool.kt``
     - moderate
     - Teamwork analytics
   * - ``VisualizationMcpToolV2.kt``
     - 401
     - Charts/visualizations generation (V2 = current)
   * - ``AssetsMetricsDataMcpTool.kt``
     - small
     - Atlassian Assets / Insight metrics

Architecture — server-side and client-side
=============================================

**Server side (this codebase exposes tools)**

The MCP tools under ``rovo-impl/.../mcp/tool/`` are NOT classical MCP
servers (they don't run a stdio JSON-RPC loop). Instead, they're
**Kotlin classes that conform to a contract** the orchestrators can
discover and invoke. They become "MCP-style tools" because:

1. They have JSON schemas (params, returns) usable by the LLM as function-call schemas
2. They follow consistent naming conventions (``...McpTool``)
3. They can be discovered by ``MarathonMcpDiscoveryService`` for use in Marathon's Python runtime

So "MCP" here is more of a **shape convention** for tool implementations
than a literal protocol implementation. The actual Anthropic MCP
protocol surfacing (for external Claude Desktop etc) is UNVERIFIED in
this investigation — would need to check ``service/`` tier for an
``McpServerController`` or similar.

**Client side (this codebase consumes external MCP servers)**

The platform tier provides:

* ``platform/client/client-api/.../mcp/MCPClient.kt`` — client interface
* ``platform/client/client-api/.../mcp/MCPClientFactory.kt`` — factory for per-server clients
* ``platform/client/client-impl/.../mcp/MCPClientImpl.kt`` — implementation

This is what Marathon uses to consume **user-installed MCP servers**
(the third-party tools a Rovo user has connected to their account).
``MarathonMcpDiscoveryService.kt`` (651 LoC) is the orchestration layer
that enumerates available external MCP servers and integrates their
tools into Marathon's tool registry alongside internal MCP tools.

The Jira concentration — why so big?
=======================================

**17,335 LoC for Jira MCP tools** — 42% of the entire MCP surface.

The reason: **Jira is the most demanded data source for Rovo agents**
and its query surface is enormously rich:

* JQL is a complete SPARQL-style query language with quirks
* Jira issues have hundreds of custom fields per tenant
* Different products (Jira Software, JSM, JPD) have different schemas
* Jira-via-NL (natural language) requires converting LLM-imagined "tickets where bob is blocking" into precise JQL with the right field names

Hence the multiple Jira tools, each with a specialized role:

* ``JiraNL2JQLV2McpTool`` (2,275 LoC) — convert NL query to JQL (uses LLM internally)
* ``JiraJQLValidationMcpTool`` (1,081 LoC) — validate JQL before executing (catches LLM hallucinations)
* ``JiraAgenticSearchMcpTool`` (1,168 LoC) — agentic search (multi-turn refinement)
* ``JiraAgenticSearchExpMcpTool`` (1,379 LoC) — experimental variant
* ``JiraRefinementMcpTool`` (1,368 LoC) — refine query iteratively based on results
* ``JiraDataPool.kt`` (844 LoC) — schema/field caching/lookup

This 6-tool Jira architecture is a **micro-pipeline**: NL → JQL → validate → search → refine → present. Each step is a separate MCP tool the LLM can call.

Tool registration and invocation
====================================

**Registration** (Spring auto-discovery):

* MCP tools are ``@Component``-annotated Kotlin classes
* Implement ``McpTool`` interface (UNVERIFIED — assumed naming)
* Spring collects them into a ``Set<McpTool>`` injected at startup
* ``MarathonMcpDiscoveryService`` maintains the registry and exposes ToolManifest

**Schema generation**:

* Each tool exposes ``getSchema()`` returning JSON Schema for params + returns
* Used by:
   * Marathon to generate Python stubs (``PythonStubGenerator``)
   * Hybrid orchestrator to build LLM function-calling schemas
   * MCP server (UNVERIFIED) to advertise tools to external Claude clients

**Invocation**:

* LLM emits tool call: ``{tool: "JiraNL2JQLV2McpTool", args: {...}}``
* Orchestrator looks up the tool in ``Set<McpTool>``
* ``tool.invoke(args, ctx, user)`` runs (suspend coroutine)
* Result returned as JSON to LLM context


Auth model — different per service category
==============================================

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - Service category
     - Auth mechanism
     - Notes
   * - Atlassian (Jira/Confluence/etc)
     - Per-tenant, per-user OAuth/SLAuth
     - Already context-aware via TenantContext + User; piggybacks on platform clients
   * - Google (Calendar/Drive/Gmail)
     - Per-user OAuth tokens
     - ``AbstractGoogleMcpTool`` provides shared token resolution; tokens stored per (tenant, user, scope)
   * - Slack
     - Per-tenant or per-user (UNVERIFIED)
     - 22 files in slack/ — likely both Bot tokens and User tokens
   * - Bitbucket
     - SLAuth / per-user (UNVERIFIED)
     -
   * - Web search
     - System-level API key
     - Single ``websearch.kt``; likely tenant-pooled

OAuth tokens for 3rd-party services are likely managed via the
**Tool Integration Service** (separate Atlassian platform). MCP tools
just **request** the right token via injected services; they don't
manage token lifecycle directly.

Sequence diagram — MCP tool invocation
==========================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant LLM
       participant Orch as Orchestrator<br/>(Marathon/Hybrid)
       participant Reg as Tool Registry
       participant Tool as JiraNL2JQLV2<br/>McpTool
       participant LLM2 as LLM (internal<br/>NL→JQL conversion)
       participant Val as JiraJQLValidation<br/>McpTool
       participant Jira as Atlassian<br/>Jira REST

       Note over Orch: Build function schemas from Set<McpTool>
       Orch->>Reg: enumerate tools for current agent
       Reg-->>Orch: List<McpTool> (with JSON schemas)

       Note over LLM: User: "find all my open bugs in Apollo"
       LLM->>Orch: tool_call: jira_nl2jql({query: "my open bugs in Apollo"})
       Orch->>Tool: invoke(args, ctx, user)
       Tool->>LLM2: prompt: "convert NL → JQL"
       LLM2-->>Tool: JQL: "assignee=currentUser() AND project=APO AND issuetype=Bug AND status!=Done"
       Tool->>Val: validate(jql)
       Val->>Jira: GET /rest/api/3/search?jql=... (validation only)
       Jira-->>Val: 200 OK (or 400 if invalid)
       Val-->>Tool: ValidationResult(valid=true)
       Tool-->>Orch: { jql, validated: true }
       Orch-->>LLM: tool result

       Note over LLM: LLM now calls jira_search(jql)
       LLM->>Orch: tool_call: jira_search({jql})
       Orch->>Jira: actual search
       Jira-->>Orch: results
       Orch-->>LLM: tool result

       LLM-->>Orch: final answer

Note the **multi-tool composition pattern**: NL2JQL + Validation are
separate tools, allowing the LLM to detect and correct invalid queries
before executing them.

External system fan-out
=========================

.. list-table::
   :header-rows: 1
   :widths: 28 38 34

   * - System
     - How
     - Used for
   * - **Atlassian REST APIs** (Jira/Confluence/etc)
     - via platform-tier clients
     - The dominant traffic
   * - **AI Gateway** (LLM)
     - via platform-tier service
     - NL2JQL conversion, agentic search
   * - **Teamwork Graph**
     - dedicated client
     - Cross-product entity relationships
   * - **Atlassian Search Platform**
     - dedicated service
     - AgenticSearch backend
   * - **Google APIs** (Calendar/Drive/Gmail)
     - via OAuth-injected REST
     - Calendar events, Drive files, Gmail threads
   * - **Slack APIs**
     - via OAuth-injected REST
     - Channels, messages
   * - **Bitbucket APIs**
     - via SLAuth REST
     - Code search, repos
   * - **External MCP servers**
     - via ``MCPClient``
     - User-installed 3rd-party tools

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
     - **17K LoC for Jira tools** (42% of MCP)
     - mcp/tool/jira/
     - Single biggest hotspot. Multiple tools doing related-but-different things (NL2JQL, validation, agentic search, refinement). Some duplication likely; some intentional micro-pipeline. Worth a dedicated review.
   * - 🔴
     - **2,275 LoC ``JiraNL2JQLV2McpTool.kt``** (single file)
     - jira/
     - Largest single file in MCP. Contains LLM prompts, JQL building, schema lookups, error handling. Should split.
   * - 🔴
     - **2,130 LoC ``AgenticSearchService.kt``**
     - search/agentic/
     - Same pattern as above. Likely concentrating multiple agentic search modes.
   * - 🟡
     - **Two "Search" surfaces** (search/ and pagesearch/)
     - mcp/tool/
     - search/ vs pagesearch/ — overlap is ambiguous from naming alone. Each has its own tools. Consolidation question.
   * - 🟡
     - **Two "AgenticSearch" Jira variants** (Exp + non-Exp)
     - jira/JiraAgenticSearchExpMcpTool.kt vs JiraAgenticSearchMcpTool.kt
     - 1,168 + 1,379 LoC. Two near-parallel implementations. Either consolidate (with feature flag) or sunset the non-current one.
   * - 🟡
     - **Server-side MCP convention is informal**
     - cross-system
     - "MCP tool" here is a Spring-discoverable Kotlin class with conventions, not a strict protocol implementation. Risk: drift between intent and reality. Worth formalizing the contract (interface, annotation).
   * - 🟡
     - **MCP server endpoint not located in this investigation**
     - service/ tier (UNVERIFIED)
     - It's possible the codebase doesn't actually expose an MCP-protocol endpoint to external Claude clients — in which case the "MCP" naming is misleading internally.
   * - 🟢
     - **No central tool catalog API**
     - cross-system
     - To know "what MCP tools does this codebase have" requires `find ... -name '*McpTool*' | wc -l`. A central catalog (REST endpoint, generated docs) would help.
   * - 🟢
     - **Mixed code-locality** (some tools in subdirs, some at top level)
     - mcp/tool/
     - 9 tools at top level (e.g., DataSculptorMcpTool, PeopleMcpTool) + 11 sub-dirs. Inconsistent. Either move all to subdirs or all to top-level.

Refactoring opportunities
============================

1. **Split JiraNL2JQLV2McpTool.kt** (M, 🔴 high) — 2,275 LoC. Extract NL2JQL conversion, JQL building, schema lookup, error handling into separate classes. ~2 days mechanical refactor.

2. **Split AgenticSearchService.kt** (M, 🔴 high) — 2,130 LoC. Same pattern.

3. **Define a strict ``McpTool`` interface** (S, 🟡 medium) — Make the convention explicit. Compile-time enforcement of schema, name, invocation.

4. **Consolidate ``JiraAgenticSearch`` and its Exp variant** (S, 🟡 medium) — Remove the experimental variant or feature-flag it within one class.

5. **Move all top-level tools into subdirs by domain** (XS, 🟢 low) — Code-locality cleanup. ~1 hour.

6. **Add a ``/api/mcp/tools`` REST endpoint** (S, 🟢 low) — List all available MCP tools with schemas. Useful for debugging, admin UI, and external discovery.

7. **Locate or build the actual MCP-protocol server endpoint** (M, 🟡 medium-high) — If the goal is real MCP-protocol exposure to external Claude clients, ensure that endpoint exists and works. If it doesn't exist, rename the internal tools to drop "Mcp" prefix to avoid misleading future contributors.

8. **Document the 3-Jira-search-tool pattern** (XS, 🟡 medium) — Write a 1-page README in ``mcp/tool/jira/`` explaining when each tool is used (NL2JQL, validation, search, refinement). Saves new contributors hours.

What you would change here
============================

* **Add a new MCP tool** → create new ``...McpTool.kt`` in appropriate subdir, ``@Component`` annotate, implement schema/invoke. Spring auto-registers.
* **Tweak a Jira NL2JQL prompt** → ``mcp/tool/jira/JiraNL2JQLV2McpTool.kt``
* **Add a new Google service** → mirror existing google/ pattern, extend ``AbstractGoogleMcpTool`` for OAuth handling
* **Change tool discovery for Marathon** → ``MarathonMcpDiscoveryService`` (in agent/orchestrators/marathon/execution/)
* **Add a new external MCP server** → registration likely via ``MCPClientFactory`` + ``MCPClient`` in platform tier
* **Modify auth for 3rd-party tools** → tool-integration-service layer (outside this codebase)

What you would NOT change here
================================

* The MCP protocol (Anthropic spec) — Atlassian doesn't own this
* Atlassian REST clients — owned by ``platform/client/client-api``
* OAuth token management — owned by tool-integration-service
* LLM provider — owned by ``platform/service/service-impl``
* Agent function-calling schema generation — owned by orchestrator layer

Verification audit log
========================

✅ **Personally verified with bash:**

* 11 sub-systems and their LoC (``ls`` + per-dir ``find`` + ``wc``)
* 9 top-level tool files in ``mcp/tool/``
* MCPClient interface in platform tier (``find -name MCPClient*``)
* All top file sizes (JiraNL2JQLV2 2,275; AgenticSearch 2,130; TeamworkGraphQuery 2,115; etc.)
* ``AbstractGoogleMcpTool`` exists at ``mcp/tool/google/`` (verified)
* Total LoC: 41,304 (verified by find/cat/wc)

⚠️ **Inferred from naming/structure (not file-content read):**

* ``McpTool`` interface (assumed shape; the actual interface file not opened)
* Auth mechanisms per service (inferred from package names, not from token-handling code)
* The micro-pipeline pattern for Jira (NL→JQL→validate→search→refine) is structural inference

❌ **UNVERIFIED:**

* Whether an MCP-protocol server endpoint exists for external Claude clients
* The exact shape of OAuth token resolution
* TTL of any tool result caches
* Whether plugin output is shared between MCP and non-MCP paths

Open questions for institutional knowledge
=============================================

1. **Is there a real MCP-protocol server in this codebase?** Or is "MCP" purely an internal convention?
2. **Why two AgenticSearch Jira variants?** Live A/B test? Production vs experimental?
3. **What's "Lumina"?** ``ShouldUseLuminaToAnswerTool.kt`` references it — Lumina classifier (mentioned earlier in inventory) — but the relationship is unclear.
4. **What's the relationship between MCP tools and Rovo Plugins?** Both expose first-party Atlassian capabilities; some overlap (search appears in both).
5. **Why is admin/ only 2 files / 1664 LoC?** Both are huge multi-tool files (``AdminGraphqlMcpTools`` 1,074, ``AdminGroupMcpTool`` 590) — should they be split?

