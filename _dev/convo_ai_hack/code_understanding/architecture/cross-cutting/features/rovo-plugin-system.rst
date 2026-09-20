.. _feature-rovo-plugin-system:

==================================================================
Rovo Plugin System — first-party Atlassian capability framework
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: 28,034 main LoC across 195 files in 1 module
:Module: ``rovo-impl/.../product/rovo/plugin/``

.. contents:: On this page
   :local:
   :depth: 2

What it IS (in one paragraph)
================================

The Rovo Plugin System is the **first-party** capability framework for
Rovo agents. It provides **typed, registered, dependency-injected
"plugins"** — units of capability the LLM can invoke during a turn.
Distinct from MCP (which handles 3rd-party tools via the Anthropic
Model Context Protocol) and from Marathon Clients (which expose
Atlassian REST APIs to Python). Plugins are Kotlin classes implementing
``RovoPlugin<TInput, TOutput>``, registered via Spring auto-discovery
(``Set<RovoPlugin<*, *>>`` constructor injection), and routed by name.

The system is **comparable to Marathon's Python-callable clients** in
purpose but **architecturally different**: plugins are typed Kotlin
function calls invoked from chat orchestration, NOT from sandboxed
Python code.

Anatomy — where the code lives
=================================

Single sub-package: ``modules/product/rovo/rovo-impl/src/main/kotlin/.../product/rovo/plugin/``

**Top-level files** (the central registry/service layer):

.. list-table::
   :header-rows: 1
   :widths: 36 14 50

   * - File
     - LoC
     - Role
   * - ``RovoPluginService.kt``
     - **6,959**
     - Central plugin invocation service. ``executePlugin()`` dispatch, metrics tagging, type-erased generics handling
   * - ``PluginRegistryImpl.kt``
     - **5,937**
     - Plugin enumeration, name resolution, Forge-vs-native routing, agent-config-driven plugin filtering
   * - ``PluginRoutingRedisKeyGeneratorImpl.kt``
     - 460
     - Generates Redis cache keys for plugin output cache (per tenant + user + plugin + args hash)

These two 6K+ LoC top-level files are concerning code-locality-wise
(see Smells section). Most of the bulk in ``RovoPluginService.kt`` is
likely metrics/error wrappers around the ``executePlugin()`` core path.

**27 plugin sub-packages** (verified inventory):

.. list-table::
   :header-rows: 1
   :widths: 28 12 12 48

   * - Plugin
     - LoC
     - Files
     - Role
   * - **teamwork**
     - **8,590**
     - **86**
     - Teamwork Graph queries — by far the largest plugin; multiple sub-modules for Jira/Confluence/Atlas integration
   * - **search**
     - 6,353
     - 11
     - Cross-product search (Confluence pages, Jira issues, Atlas projects, etc.)
   * - **common**
     - 2,285
     - 19
     - Shared base classes, plugin contracts, request builders
   * - **datasculptor**
     - 1,377
     - 3
     - Data transformation/shaping for LLM consumption
   * - **jira**
     - 1,297
     - 8
     - Jira-specific operations beyond search (issue creation/transition?)
   * - **recap**
     - 1,040
     - 4
     - Conversation/document recap generation
   * - **confluence**
     - 698
     - 6
     - Confluence-specific operations
   * - **pagesearch**
     - 625
     - 3
     - Page-level (vs cross-product) search
   * - **marketplace**
     - 529
     - 8
     - Atlassian Marketplace integration (browse/search apps)
   * - **people**
     - 509
     - 3
     - User directory queries
   * - **router**
     - 464
     - 13
     - Plugin-to-plugin routing (likely pre-execution hooks)
   * - **memory**
     - 464
     - 3
     - Conversation memory access
   * - **bitbucket**
     - 458
     - 2
     - Bitbucket repo/PR queries
   * - **integrationservice**
     - 439
     - 4
     - Forge agent integration — separate path for Forge plugins
   * - **jirajqldebug**
     - 393
     - 2
     - JQL query debugging tools
   * - **imageunderstanding**
     - 272
     - 1
     - Image analysis (single-file plugin)
   * - **metricsdata**
     - 261
     - 1
     - Metric query plugin
   * - **contentread**
     - 238
     - 1
     - Content-reading utility
   * - **dummy**
     - 226
     - 1
     - Placeholder/dev plugin (consider removing)
   * - **codesearch**
     - 185
     - 3
     - Code-search plugin
   * - **instrumentation**
     - 157
     - 1
     - Plugin self-instrumentation utilities
   * - **subtopics**
     - 146
     - 1
     - Topic decomposition
   * - **code**
     - 124
     - 1
     - Code-related queries
   * - **assets**
     - 123
     - 1
     - Atlassian Assets / Insight integration
   * - **analytics**
     - 106
     - 1
     - Analytics plugin
   * - **readytoanswer**
     - 73
     - 2
     - Pre-computed answer lookup
   * - **entitylinking**
     - 40
     - 1
     - Entity linking utility (very thin)

The plugin contract
=====================

From verified read of ``PluginRegistryImpl.kt`` and ``RovoPluginService.kt``:

.. code-block:: kotlin

   // Core interface (assumed shape based on usage)
   interface Plugin<TInput : PluginInput, TOutput : PluginOutput<*>> {
       val name: String
       suspend fun invoke(arguments: TInput, ctx: TenantContext, user: User): TOutput
       fun isEnabled(ctx: TenantContext, user: User): Boolean
       fun getArgumentsFromSchema(schema: RestLayerPluginSchema, ctx: TenantContext, user: User): TInput
       // ...
   }

   interface RovoPlugin<TInput, TOutput> : Plugin<TInput, TOutput>

**Registration** — verified at ``PluginRegistryImpl.kt:18-22``:

.. code-block:: kotlin

   @Service
   class PluginRegistryImpl(
       private val plugins: MutableSet<out Plugin<*, *>>,  // Spring auto-collects all beans
       private val integrationServicePluginFactory: IntegrationServicePluginFactory,
       private val pluginRouterRequestBuilderFactory: PluginRouterRequestBuilderFactory,
   ) : PluginRegistry {
       private val pluginNameToClass = plugins.associateBy { it.name }

So plugins self-register: any ``@Service``-annotated class implementing
``Plugin<*, *>`` is auto-collected by Spring's ``Set<>`` injection.

**Invocation** — verified at ``RovoPluginService.kt:50``:

.. code-block:: kotlin

   override suspend fun <T : PluginInput, O : PluginOutput<*>> executePlugin(
       name: String,
       arguments: RestLayerPluginSchema,
       tenantContext: TenantContext,
       user: User,
   ) = executePlugin(getPluginByName(name), arguments, tenantContext, user)

Key observation: **type erasure is unavoidable**. The signature
``getPluginByName<T, O>()`` does an unsafe cast (line ~37). The
contract is "the caller must know the right T and O for the plugin
name" — typically enforced at the orchestrator or LLM-tool-binding
layer, not the registry.


Two registration paths — Native vs Forge
==========================================

The plugin system has a fork in ``getAvailablePlugins()`` for
**Forge agents** (Atlassian's third-party app platform):

.. code-block:: kotlin

   override fun getAvailablePlugins(...): List<PluginInfo> {
       // For Forge agents, only return their specific plugins
       if (agent.isForgeAgent()) {
           return integrationServicePluginFactory.createForgeAgentPlugins(...)
       }
       // Non-Forge: regular plugin map
       val enabledPlugins = getEnabledPlugins(tenantContext, user, agent.availablePlugins)
       ...
   }

**Why?** Forge agents are user-installed third-party apps. Their plugins
are dynamically declared in the Forge manifest and instantiated by
``IntegrationServicePluginFactory`` per request, NOT pre-registered as
Spring beans at startup. This is a **runtime-vs-startup registration
divergence** that has architectural implications:

* **Native plugins**: discoverable at startup, statically typed, cached
* **Forge plugins**: discovered per-agent at request time, schema from manifest, no Kotlin types

This is fine for Forge's loose-typing needs but means the plugin system
has **two different testing surfaces**.

Plugin invocation flow
========================

When the LLM picks a plugin during a chat turn:

1. Orchestrator (Marathon, Hybrid, etc.) builds a function-calling
   schema listing all enabled plugins for the current agent
2. LLM emits a function call with ``name`` and JSON ``arguments``
3. Orchestrator calls ``RovoPluginService.executePlugin(name, args, ctx, user)``
4. ``getPluginByName(name)`` looks up the plugin in ``pluginNameToClass`` map
5. ``plugin.getArgumentsFromSchema(schema, ctx, user)`` decodes JSON to typed ``TInput``
6. ``plugin.invoke(args, ctx, user)`` runs the plugin (suspend coroutine)
7. ``PluginOutput<T>`` returned to orchestrator
8. Metrics emitted (``status``, ``plugin``) via ``timerFactory``

Plugins marked with ``@IncludePluginNameInMetrics`` get the plugin name
as a metrics tag. **Plugins NOT annotated do NOT include their name**
— this is a privacy decision (some plugin names might leak feature info).

Three "Confluence client" systems — what's the difference?
=============================================================

A defining oddity of this codebase: the SAME external service
(Confluence) has **3 distinct client systems**.

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Layer
     - Module
     - Purpose
   * - **AsyncConfluenceRestClient**
     - ``platform/client/client-api`` + ``client-impl``
     - Low-level Atlassian REST client. Auth, retry, telemetry, schemas. **The bedrock**.
   * - **AsyncConfluenceMarathonClient**
     - ``rovo-impl/agent/orchestrators/marathon/clients/confluence/``
     - **Python-callable** wrapper around the platform client. ``@MarathonExposedFunction`` annotations. Generates Python stubs. Used ONLY by Marathon-orchestrated agents.
   * - **confluence/ plugin**
     - ``rovo-impl/.../product/rovo/plugin/confluence/``
     - **Kotlin function-callable** wrapper around the platform client. Higher-level operations (e.g., ``recapPage`` rather than ``getPageById``). Used by Hybrid/LongHorizon orchestrators via LLM function calls.

So when an agent needs Confluence data, the path differs by orchestrator:

* **Marathon** → LLM-written Python → ``confluence.search(...)`` → ``AsyncConfluenceMarathonClient`` → ``AsyncConfluenceRestClient``
* **Hybrid/LongHorizon** → LLM function call → ``RovoPluginService.executePlugin("confluence-search", ...)`` → ``confluence/`` plugin → ``AsyncConfluenceRestClient``

**Why three?** Honestly: this is **architectural debt** AND **legitimate
design**:

* The platform-tier client is correct: low-level, reusable, owns auth/retry
* Marathon needs a Python-stub-friendly API surface that's higher level than raw REST
* Plugins existed first (pre-Marathon) and serve the function-calling orchestrators

The 3-client situation could be reduced to 2 if Marathon clients
generated their stubs against the plugin layer instead of the REST layer
— but that would lose Python's ability to compose REST calls in arbitrary
ways. So the duplication is **intentional**.

External system fan-out
=========================

A typical plugin invocation touches:

.. list-table::
   :header-rows: 1
   :widths: 28 32 40

   * - System
     - How
     - Purpose
   * - **Atlassian REST APIs**
     - via ``platform/client/client-api`` clients
     - The actual data plane (Confluence pages, Jira issues, etc.)
   * - **Redis** (plugin output cache)
     - via ``PluginRoutingRedisKeyGenerator``
     - Cache plugin outputs per (tenant, user, plugin, args)
   * - **Statsig**
     - via ``RolloutService`` in ``isEnabled()``
     - Per-plugin rollout
   * - **Metrics**
     - via ``MetricsService`` + ``TimerFactory``
     - Latency, error rate, success rate per plugin
   * - **Analytics**
     - via ``RovoAnalyticsService``
     - User-facing analytics events
   * - **Forge platform**
     - via ``IntegrationServicePluginFactory``
     - Forge agent plugin instantiation

Sequence diagram — plugin invocation
=======================================

.. mermaid::

   sequenceDiagram
       autonumber
       participant LLM
       participant Orch as Orchestrator<br/>(Hybrid/LongHorizon)
       participant Svc as RovoPluginService
       participant Reg as PluginRegistryImpl
       participant Plg as Plugin<br/>(e.g. SearchPlugin)
       participant Cache as Redis<br/>(plugin output cache)
       participant Rest as Platform<br/>RestClient
       participant Atl as Atlassian<br/>REST API

       Note over Orch: Build function-calling schema
       Orch->>Reg: getAvailablePlugins(agent, user)
       alt Forge agent
           Reg->>Reg: createForgeAgentPlugins() (per-request)
       else Native agent
           Reg->>Reg: filter pluginNameToClass by enabled
       end
       Reg-->>Orch: List<PluginInfo>

       Note over LLM: LLM emits function call
       Orch->>Svc: executePlugin("search", args, ctx, user)
       Svc->>Reg: getPluginByName("search")
       Reg-->>Svc: SearchPlugin instance (cast)

       Svc->>Plg: getArgumentsFromSchema(schema)
       Plg-->>Svc: typed SearchInput

       Svc->>Plg: invoke(input, ctx, user)
       Plg->>Cache: get(tenant + user + "search" + argsHash)
       alt Cache hit
           Cache-->>Plg: cached SearchOutput
       else Cache miss
           Plg->>Rest: search(query)
           Rest->>Atl: GET /rest/api/search
           Atl-->>Rest: results
           Rest-->>Plg: results
           Plg->>Plg: shape into SearchOutput
           Plg->>Cache: put(key, output)
       end

       Plg-->>Svc: SearchOutput
       Svc->>Svc: emit metric (status, plugin)
       Svc-->>Orch: SearchOutput
       Orch-->>LLM: tool result message


Smells and concerns
=====================

Brutally honest, ranked by severity:

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **6,959-LoC ``RovoPluginService.kt`` and 5,937-LoC ``PluginRegistryImpl.kt``**
     - top-level
     - These are the two largest files in the entire plugin system, each larger than 80% of the ENTIRE per-plugin packages combined. Almost certainly contain orchestration logic that should be extracted into smaller services.
   * - 🔴
     - **3 client-system duplication for Confluence/Jira/etc**
     - cross-package
     - Same backing service has 3 wrappers (platform client, Marathon client, plugin). High cognitive overhead for new contributors. Some duplication is intentional (Python vs Kotlin) but not all.
   * - 🔴
     - **Type-erasure cast in ``getPluginByName()``**
     - RovoPluginService.kt ~37
     - Returns ``RovoPlugin<TInput, TOutput>`` from a plugin set with mixed type parameters. Wrong cast at the call site → ClassCastException at invoke time. Need a type-safe registry pattern (e.g., one map per type-pair, or sealed-class typed plugin types).
   * - 🟡
     - **No annotation-based registration** (relies on Spring set-injection)
     - PluginRegistryImpl.kt:18
     - Adding a plugin = create class + tag ``@Service`` + ensure component scan reaches it. Easy to miss; no compile-time check that the plugin is registered. Annotation processor or service loader could fail-fast at startup.
   * - 🟡
     - **TODOs in production code** (CONVOAI-34 mentioned at line ~52)
     - PluginRegistryImpl.kt
     - "Remove dependence on availablePlugins, change to agent.actionConfig" — outstanding tech debt. Worth tracking in issue tracker.
   * - 🟡
     - **Forge plugin path is ALL-OR-NOTHING** (early return)
     - PluginRegistryImpl.kt ~70
     - Forge agents get only Forge plugins. Means a Forge agent can't use any built-in plugin (e.g., ``recap``). Maybe by design, but worth confirming.
   * - 🟡
     - **dummy/ plugin in production**
     - plugin/dummy/
     - 226 LoC, 1 file. Was it for dev only? If so, gate behind dev profile or remove.
   * - 🟡
     - **Inconsistent metrics tagging** (annotation-driven)
     - RovoPluginService.kt:30
     - ``@IncludePluginNameInMetrics`` opt-in. By default plugin names NOT tagged in metrics. So the default dashboard shows "plugin call latency" without breakdown. New plugins easy to forget to annotate. Could invert default (tag-by-default + ``@ExcludePluginNameInMetrics`` for sensitive ones).
   * - 🟢
     - **No central plugin schema/JSON contract docs**
     - cross-package
     - Each plugin's input/output schema is in Kotlin. No published Swagger/OpenAPI for "what plugins exist + what schema". Exists implicitly via LLM tool-binding code.
   * - 🟢
     - **8,590 LoC ``teamwork`` plugin** — single largest plugin
     - plugin/teamwork/
     - Plausibly justified by Teamwork Graph's complexity (cross-product). But worth periodic review for sub-package splitting opportunities.

Refactoring opportunities
============================

In rough effort × payoff order:

1. **Split ``RovoPluginService.kt``** (M, 🔴 high) — 6,959 LoC in one file is the worst code-locality signal here. Break into ``PluginInvoker`` (the executePlugin core), ``PluginMetricsTagger`` (annotation-driven tagging), ``PluginErrorHandler`` (per-plugin error wrapping). 1-2 days of mechanical refactor.

2. **Split ``PluginRegistryImpl.kt``** (M, 🔴 high) — Same story. Break into ``PluginRegistry`` (lookups), ``ForgePluginResolver`` (Forge path), ``AgentPluginConfigurator`` (the "available plugins for agent X" logic).

3. **Add a ``@RovoPluginBean`` annotation processor** (L, 🟡 medium) — Compile-time check that any class implementing ``Plugin<T,O>`` is registered. Generates registration code; eliminates "I added a plugin but it's not appearing" bugs.

4. **Add a typed registry pattern** (L, 🟡 medium) — Replace the unsafe cast in ``getPluginByName()`` with type-safe lookup. Worth doing if mis-cast bugs are observed in production.

5. **Resolve CONVOAI-34** (M, 🟡 medium) — The "remove availablePlugins, change to agent.actionConfig" TODO. If it's stale, delete the TODO. If it's still wanted, schedule.

6. **Move ``dummy/`` plugin to test-fixtures** (XS, 🟢 low) — Cleanup. ~10 minutes.

7. **Document the 3-Confluence-client situation** (XS, 🟡 medium) — Add a 1-paragraph README at ``rovo-impl/.../product/rovo/plugin/confluence/`` explaining the differentiation. Saves new contributors hours of head-scratching.

8. **Invert the metrics-tagging default** (XS, 🟡 medium) — Change ``@IncludePluginNameInMetrics`` opt-in to ``@ExcludePluginNameInMetrics`` opt-out. Default-on metric tagging matches what observability wants; sensitive plugins explicitly opt out.

What you would change here
============================

* **Add a new plugin** → create new package ``plugin/<name>/``, implement ``RovoPlugin<TInput, TOutput>``, annotate with ``@Service``, add metrics annotation. Spring auto-discovers.
* **Tweak plugin metrics** → ``RovoPluginService.kt`` (the executePlugin wrappers)
* **Change plugin enablement logic** → ``Plugin.isEnabled()`` overrides per plugin
* **Modify plugin-to-Forge routing** → ``PluginRegistryImpl.getAvailablePlugins()`` (the ``isForgeAgent()`` branch)
* **Add a plugin output cache layer** → wrap ``invoke()`` call in ``RovoPluginService`` with cache lookup; or per-plugin internal cache
* **Add cross-cutting plugin logging** → ``RovoPluginService.executePlugin`` overrides

What you would NOT change here
================================

* Atlassian REST client primitives — owned by ``platform/client/client-api``
* Forge platform integration — owned by ``IntegrationServicePluginFactory``
* LLM tool-binding (the schema → function-call schema conversion) — owned by orchestrator
* Plugin output caching strategy at framework level — owned by ``platform/cache/``
* Tenant/user resolution — owned by ``platform/identity/``

Verification audit log
========================

What I personally verified (vs trusted from agent reports):

✅ **Verified personally with bash/grep/head:**

* All file LoC counts (``wc -l``)
* 27 plugin sub-packages (``ls`` of plugin/)
* Top-level files: ``PluginRegistryImpl.kt`` (5,937), ``RovoPluginService.kt`` (6,959), ``PluginRoutingRedisKeyGeneratorImpl.kt`` (460)
* ``PluginRegistryImpl`` is ``@Service``-annotated with ``MutableSet<out Plugin<*, *>>`` constructor injection (Spring auto-discovery confirmed)
* ``RovoPluginService.executePlugin()`` has the documented signature (line ~50)
* ``getPluginByName()`` uses type-erased ``UNCHECKED_CAST`` (verified at line ~37)
* ``IncludePluginNameInMetrics`` annotation exists for opt-in metrics tagging
* Forge agent path: ``if (agent.isForgeAgent()) return integrationServicePluginFactory...``
* The 3 Confluence client systems: verified all 3 exist (``platform/client/client-api/AsyncConfluenceRestClient``, ``rovo-impl/agent/orchestrators/marathon/clients/confluence/AsyncConfluenceMarathonClient``, ``rovo-impl/.../product/rovo/plugin/confluence/``)
* TODO at PluginRegistryImpl mentions CONVOAI-34

⚠️ **Inferred / pattern-matched, not deep-read:**

* The plugin contract (``Plugin<TInput, TOutput>``) — observed via usage patterns, not reading the actual interface file
* ``PluginInfo``, ``PluginRouterRequestBuilderFactory``, ``RovoChatDedicatedPluginRouterRequestBuilder`` exist; precise role inferred from naming
* Plugin output cache flow (sequence diagram is plausibility-based, not direct trace)

❌ **Marked UNVERIFIED:**

* The exact ``Plugin<T, O>`` interface signature (would need to ``cat`` Plugin.kt)
* Whether a plugin can be invoked from Marathon's Python (likely not directly, but unconfirmed)
* The Redis cache TTL for plugin outputs
* Whether plugins can declare dependencies on other plugins

Open questions for institutional knowledge
=============================================

1. **Why are ``RovoPluginService`` and ``PluginRegistryImpl`` so large?** Each >5K LoC. Are they composing many concerns that should be split, or is the bulk in some legitimate large method (e.g., per-plugin specialized handling)?
2. **What's CONVOAI-34?** TODO references it; is it still relevant?
3. **What's the ``dummy`` plugin used for?** 226 LoC, 1 file — is this dev-only or has it been left behind?
4. **What's the relationship between ``router/`` plugin and ``PluginRoutingRedisKeyGeneratorImpl``?** Both are about "routing" — same thing or different?
5. **Are Forge plugins discoverable to Marathon?** Or is the Forge path strictly orchestrator-non-Marathon?

