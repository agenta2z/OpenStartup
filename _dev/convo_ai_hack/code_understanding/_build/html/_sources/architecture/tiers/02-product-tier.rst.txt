.. _product-tier:

============================
Product Tier (30 modules)
============================

The **product tier** holds business logic specific to each Atlassian product. It depends on the platform tier (for shared capabilities) and is depended on by the service tier (which routes requests to product-specific controllers and resolvers).

The product tier follows the api/impl/spi pattern: API contracts in ``-api`` modules, implementations in ``-impl``.

Product modules at a glance
============================

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Product
     - Modules
     - Primary responsibility
   * - **rovo**
     - 6
     - General-purpose Atlassian-Intelligence-style chat agent; Marathon orchestration; SAIN (Slack AI Notification) workflows
   * - **agentstudio**
     - 2
     - Agent CRUD, scenarios, batch evaluation, widget management, conversation review
   * - **atlassianstudio**
     - 2
     - User site context, access control, permissions
   * - **agent-framework**
     - 1
     - Core agent framework templates; Stratus minion configurations
   * - **adk**
     - 2
     - Agent Development Kit (tool templates, dev utilities, agent registration)
   * - **aifeature**
     - 3
     - Cross-product writing/summarization (smart links, comment summary, sprint summary, suggest issues)
   * - **chat-common**
     - 1
     - Shared chat/messaging abstractions
   * - **shared-features**
     - 1
     - Common feature abstractions across products
   * - **jira**
     - 2
     - Jira-specific templates: comment summary, sprint summary, suggest issues, work breakdown
   * - **confluence**
     - 2
     - Confluence space recommendations, page content analysis
   * - **jsm**
     - 2
     - JSM journey crafting, request orchestration, HR agent selection
   * - **csm**
     - 2
     - CSM workflows: email suppression, migration analysis, refund requests, password reset
   * - **loom**
     - 2
     - Loom video integration with conversational platform
   * - **jpd**
     - 2
     - Jira Product Discovery integration

Total: ~30 modules across 14 product groupings.

Major product deep-dives
=========================

``product/rovo`` :sup:`(agent-reported)`
-----------------------------------------

The largest and most complex product. Six modules:

- ``rovo-api`` — public contracts (``SainService.kt``, agent definitions)
- ``rovo-spi`` — pluggable extension points
- ``rovo-impl`` — concrete implementations (``MarathonApiCallbackController.kt:29``)
- ``rovo-extras-impl`` — non-core feature extensions
- ``rovo-leaf-agents-impl`` — leaf-level agent implementations
- ``marathon-stubs-publisher`` — publishes Marathon test stubs

Two flagship subsystems:

**Marathon orchestration** — long-horizon multi-step workflows. Agents that need to take dozens of LLM-mediated actions over minutes/hours (e.g. "find all related Jira issues, summarize each, write a meta-summary"). Coordinated through a callback controller pattern: ``MarathonApiCallbackController`` receives async progress updates from the Marathon orchestrator service.

**SAIN (Slack AI Notification)** — workflow caching, permission management, global cache debugging for AI-generated Slack notifications. Tested by the failing-locally ``SAINStandaloneHybridOrchestratorIT`` (see ``hack_states/02-integrationTest-result.md``).

``product/agentstudio`` :sup:`(agent-reported)`
------------------------------------------------

The **agent management UI** backend. Provides:

- Agent CRUD via GraphQL (``AgentStudioAgentQueryController.kt:75``, ``AgentStudioAgentMutationController.kt``)
- Scenario management (test scenarios for agents)
- Skill integration (which skills an agent can invoke)
- Widget management (UI rendering for agent responses)
- Batch evaluation (run an agent against a dataset; collect metrics)
- Conversation review (human evaluators rate agent outputs)
- Tool configuration

Most complex per-product GraphQL surface in the codebase.

``product/aifeature`` :sup:`(agent-reported)`
----------------------------------------------

**Cross-product** features. Despite living in ``product/``, AiFeature is the catalog of capabilities that ANY product can invoke:

- Smart links generation (Confluence, Jira, Atlas, Bitbucket PR descriptions)
- Comment summary
- Sprint summary
- Suggest issues
- Tone changes
- Chart generation

Templates live in ``aifeature-impl/src/main/resources/prompts/`` (80+ templates per agent) and ``aifeature-impl/src/main/resources/templates/`` (rendering templates).

``product/csm`` :sup:`(agent-reported)`
----------------------------------------

Customer Success Management workflows. Skills are markdown files at ``csm-impl/src/main/resources/skills/``:

- ``email-suppression-skill.md``
- ``migration-analysis-skill.md``
- (refund requests, password reset, etc.)

These are loaded by the ``adk`` (Agent Development Kit) at runtime and exposed as agent capabilities.

Other products :sup:`(agent-reported)`
---------------------------------------

- **jira:** Templates at ``jira-impl/src/main/resources/templates/`` for comment summary, sprint summary, suggest issues, work breakdown
- **confluence:** Templates + GraphQL schema at ``confluence-impl/src/main/resources/`` (``ConfluenceSpaceRecommendations.graphqls``)
- **jsm:** Templates + YAML agent configs at ``jsm-impl/src/main/resources/`` for journey crafting, HR agent selection, inline doc segmentation
- **loom:** Loom video transcript / metadata integration
- **jpd:** Jira Product Discovery integration
- **atlassianstudio:** ``AtlassianStudioContextQueryController.kt``, ``AtlassianStudioAccessServiceImpl.kt``

Product-tier patterns
======================

1. **Templates over code.** Most product-specific behavior is encoded in Pebble/Jinja-style templates under ``src/main/resources/`` rather than Kotlin code. This lets prompt engineers iterate without touching code.

2. **GraphQL > REST.** Most newer per-product surfaces are GraphQL controllers (``@QueryMapping``, ``@MutationMapping``). REST is reserved for backward compatibility (``ChatV1Controller``) and special cases (streaming).

3. **Skills as markdown.** CSM (and likely others) defines agent skills as markdown files loaded by ADK. This is a versioning escape hatch — a customer-success-manager can edit a skill description without a code release.

4. **Per-product config classes.** Each product has its own ``...config`` package scanned via ``Application.kt:scanBasePackages``. This isolates Spring beans so a product can opt in/out at deployment time.

5. **Suspend GraphQL handlers MUST use ``withRequestAttributesContext { }``.** Per AGENTS.md lines 31-33, suspend GraphQL handlers (``@QueryMapping``, ``@MutationMapping``, etc.) must wrap their bodies in ``withRequestAttributesContext { }`` before any suspension point. Otherwise Spring's ``RequestContextHolder`` (thread-local) is lost after the first suspend.

What you would change here
===========================

- **Add a new product** → new directory under ``modules/product/<name>/`` with ``-api`` and ``-impl``; add to ``Application.kt:scanBasePackages``
- **Add a new agent skill** → markdown file under ``<product>-impl/src/main/resources/skills/`` (CSM pattern)
- **Add a new prompt template** → Pebble file under ``<product>-impl/src/main/resources/templates/`` or ``prompts/``
- **Modify product-specific controller** → edit GraphQL controller in ``<product>-impl/src/main/kotlin/.../graphql/``

What you would NOT change here
===============================

- **AI Gateway calling code** (lives in ``platform/service``)
- **Tenant context resolution** (lives in ``foundation/context``)
- **Feature flag evaluation** (lives in ``foundation/utilities``)
- **Conversation persistence** (lives in ``platform/conversation``)

