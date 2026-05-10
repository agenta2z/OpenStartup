.. _overview-architectural-narrative:

==================================================================
The architectural narrative — what each layer actually does
==================================================================

A walking tour of the codebase. **No tables; pure narrative.** If you read this end-to-end,
you'll understand what every tier and major subsystem actually does and why it exists.

The 30,000-foot view
======================

Conversational-AI-Platform is a Spring Boot service that turns Atlassian REST/GraphQL APIs into
**agentic AI capabilities**. The fundamental shape:

1. A user types into a chat box (in Jira / Confluence / Rovo / AgentStudio / etc.)
2. The frontend sends a request to ``ChatV1Controller`` (in ``service/convo-ai-service``)
3. The controller resolves tenant context, conversation history, and product context
4. It hands off to a **workflow executor** which runs an agent loop:

   * **LLM call** → emits text or tool_calls
   * If tool_calls: dispatch to the **action runtime** which invokes the tool
   * Loop until the LLM emits a "final" message
5. Stream the response back to the user as Server-Sent Events (SSE)

Around this core loop, the codebase has accumulated **enormous infrastructure**:

* Multi-LLM-provider abstraction (Gemini, Anthropic, plus hosted variants on GCP/Vertex)
* Multi-source RAG (Confluence, Jira, Salesforce, vector store, Loom transcripts)
* Multi-orchestrator agent execution (Marathon for parallel, LongHorizon for async, Hybrid for routing)
* A "publishing UI" for non-developers to create agents (AgentStudio)
* Per-product specialization for Jira, Confluence, JSM, CSM, JPD, Loom, AtlassianStudio
* A sandbox code-execution environment (separate Docker container, addressed via service mesh)
* Batch evaluation infrastructure (LLM-as-judge with separate execution + judging phases)
* Knowledge-gap tracking (which questions can't be answered well)
* MCP (Model Context Protocol) integration for external tool servers
* TAP integration for user targeting / experimentation
* Deep Research workflows for long-form investigations
* Avatar generation, insights, journey building, AVP charts/dashboards, and dozens more side-features

The total: **2.5M lines of Kotlin** across 84 Gradle modules. Half is test code (12,606 test files,
1.35M LoC). The codebase has a strong test culture.

Layer 1: Bootstrap (``service/convo-ai-service``, 45K LoC)
============================================================

Spring Boot starts here. The ``Application.kt`` (15 lines) just calls ``runApplication``;
the real Spring DI graph assembles ~389 beans across 8 sub-systems:

* **REST controllers** (``rest/v1/``, ``rest/v2/``, ``rest/internal/``) — the HTTP surface area.
  ``ChatV1Controller`` exposes ``/v1/chat`` and several streaming variants.
* **Tenant domain** (``domain/tenant/``, 5,611 LoC) — multi-tenant isolation, context resolution.
  Every request passes through tenant resolution before any business logic.
* **Content retrieval** (``common/contentretrieval/``, 12,246 LoC) — the largest sub-system.
  Generic "resolvers" (8K LoC, 39 files) plus a Confluence-specific retriever (4.3K LoC) for
  the special permission complexity Confluence has.
* **SQS workers** (``service/sqs/queue/``, 1,907 LoC across 44 files) — async background jobs.
  Distinct queues for batch evaluation, agent provisioning, knowledge-gap upload, etc.
* **Redis caches** (``service/redis/impl/``, 37 files) — caching layer for hot data.
* **ERS tenanted stores** (``service/ers/tenanted/``, 60 files) — per-tenant entity persistence.
* **Streamhub** (``service/streamhub/``) — the SSE streaming infrastructure.
* **GraphQL** (``service/graphql/`` + ``service/graphql/subscription/``) — alternative API surface.

The bootstrap layer is **bigger than typical** — most Spring Boot main modules are <5K LoC; this is
9× larger. The reason is convo-ai's bootstrap also owns content retrieval and tenant infrastructure
that arguably could move to platform tier. This is a refactoring target.

Layer 2: Service abstraction (``platform/service/service-impl``, 69K LoC)
==========================================================================

The "smart middleware" layer between bootstrap and the per-product implementations. Four sub-systems:

**LLM provider abstraction (22K LoC).** The most architecturally sophisticated part of the codebase.
Provides a uniform interface across 6 LLM providers with **two flavors each**:

* ``GeminiLanguageModelProvider`` (1,406 LoC) — model-family-specific
* ``GenericGeminiLanguageModelProvider`` (1,484 LoC) — parameterized variant
* Same pattern for Anthropic, GCP-Anthropic, Vertex variants

The "Generic" variants suggest a refactoring journey: initially shipped one class per model,
later refactored to a single class that takes the model family as parameter. Both still exist;
the duplication is a known cleanup target.

Behind the providers sits the ``AIGatewayClientServiceImpl`` (3,087 LoC) — the unified HTTP client
that talks to Atlassian's central AI Gateway service (a separate microservice that handles auth,
quota, fail-open semantics — see the ``responsible-ai-api`` repo). When you read documentation
about "the AI gateway," it lives in that other service; this module is the **client**.

Token counting is per-provider (``llm/tokencounter/``, 733 LoC, 11 files) because each provider
tokenizes differently. Tool schema conversion is per-provider too (``llm/toolconverter/``, 1,354 LoC,
12 files). Truncation is per-provider (``llm/truncator/``).

**Cross-product search (14K LoC).** A complete multi-source search infrastructure:

* ``RankingServiceImpl`` (1,647 LoC) ranks results across sources
* ``InterleaverSearchProvider`` (1,201 LoC) interleaves results from multiple sources
* Per-source providers: Confluence (954 LoC), Salesforce (1,014 LoC), Interleaver, Jira, etc.
* Query templates in ``search/queries/`` (1,668 LoC, 5 files)

This is genuinely a search platform; it could plausibly be its own module
(``platform/search-impl``).

**Per-product service integrations.** Jira (5,345 LoC, with sprint + issue + workflow sub-services),
JSM (987 LoC), Loom (485 LoC), AGS (943 LoC + 2,089 domain mappers).

**Specialized services.** Long tail: ADF processing, JourneyBuilder (1,378 LoC single file),
AVP charts/dashboards, entity linking, AI credit usage tracking, audit log, UBP enforcement,
responsible-AI policy hooks, follow-up question generation, image generation via Gemini,
backfill operations, Socrates metadata.

Layer 3: Conversation lifecycle (``platform/conversation/conversation-impl``, 14K LoC)
=========================================================================================

Manages the lifecycle of a chat conversation. Layered persistence:
manager → store → ERS-store → ERS-client (4 layers).

The ``ConversationManagerImpl`` (892 LoC) is the entry point. Most ``ChatV1Controller`` requests
hit this. Channels group messages; messages are "history items"; large messages are split via
``ConversationHistoryLargeComponentsHandler`` (656 LoC) because individual ERS docs have size limits.

The ``ConversationChannelMultiStoreImpl`` (441 LoC) is interesting — it suggests dual-write or
shadow-read between primary and secondary stores, possibly for an in-flight migration.

Layer 4: Agent execution (multiple modules, ~100K+ LoC total)
===============================================================

The most architecturally diffuse layer. Spread across:

**``platform/workflow/workflow-impl`` (1.5K LoC)** — the "official" platform workflow:
``SimpleLoopWorkflowExecutorImpl.kt`` (1,222 LoC, 78% of the module). Implements the simple loop:
``LLM → tool_call? → execute → feed result → LLM again``.

**``product/rovo/rovo-impl/agent/orchestrators/`` (96K LoC, 272 files)** — Rovo's *own* parallel
universe of orchestrators:

* **MarathonOrchestratorAgent** — fan-out parallel orchestrator. Runs multiple specialist sub-agents
  concurrently and synthesises. Used for complex multi-source queries.
* **LongHorizonOrchestratorAgent** — durable async orchestrator for tasks that take minutes to hours.
  Persists state, supports resume.
* **HybridOrchestratorAgent** — routes between Marathon and LongHorizon based on cost/complexity heuristics.

The **massive duplication** between the small "official" workflow and Rovo's 96K LoC orchestrator
sub-tree is the codebase's biggest architectural smell. The "platform vs product" boundary is
leaky here — most of what would architecturally belong in platform/workflow lives in product/rovo.

**``product/rovo/rovo-impl/agent/minions/`` (54K LoC, 261 files)** — concrete skill implementations.
Each "minion" is a specialist agent that handles a specific domain (Jira, Confluence, JSM, Talent, etc.).

**``product/agent-framework/agent-framework-impl`` (10K LoC)** — cross-product skills + Stratus minions.
The largest single skill is ``AssessChangeRiskSkill.kt`` (2,157 LoC) — change-risk assessment is
apparently very involved.

Layer 5: Tools (multiple modules, ~50K LoC total)
====================================================

How the LLM actually invokes external operations. Two layers:

**Tool registry** (``platform/tool-registry``, 902 + 897 LoC) — the "what tools exist" half.
Four registration sources:

* **MCP** (``McpToolRegistrationServiceImpl``, 373 LoC) — Model Context Protocol tool servers
* **IntegrationsService** (``IntegrationServiceToolRegistrationServiceImpl``, 193 LoC) — Atlassian-internal tools
* **Forge** (``ForgeToolRegistrationServiceImpl``, 49 LoC) — third-party Forge marketplace apps
* **Native** (``NativeToolRegistrationServiceImpl``, 27 LoC) — built-in convoai tools

MCP being the largest source (373 LoC) reflects MCP's strategic importance as the unified protocol.
Forge and Native are smaller because they have a fixed set of tools.

**Action runtime** (``platform/action``, 444 + 13 + 88 LoC) — the "how to execute" half.
The action-impl is tiny (88 LoC) because it's largely a delegate; the real action execution
intelligence lives in the per-product impls.

**MCP servers in product/rovo** (``product/rovo/rovo-impl/product/rovo/mcp/``, 41K LoC, 201 files)
— a heavy investment in MCP infrastructure that goes well beyond simple registration. This subdir
likely contains the actual MCP server implementations + transport layer + tool definitions.

Layer 6: Knowledge / RAG (multiple modules, ~10K LoC scattered)
==================================================================

* ``platform/knowledge`` — minimal API (131 LoC) + small impl (323 LoC). Manages knowledge sources.
* ``platform/knowledge-gap`` — heavier (958 + 44 + 1.8K LoC). Tracks "questions we can't answer well."
* ``platform/base-impl/AbstractTurboPufferService.kt`` (210 LoC) — TurboPuffer vector store integration
* ``platform/service/service-impl/search/`` (14K LoC) — the actual search/retrieval infrastructure
* ``service/convo-ai-service/common/contentretrieval/`` (12K LoC) — request-time content fetching

Knowledge is a **distributed concern** in this codebase. Vector retrieval in base-impl, content
retrieval in convo-ai-service, knowledge-source management in platform/knowledge, knowledge-gap
tracking in platform/knowledge-gap, and search providers in service-impl/search/. There's no single
"RAG module."

Layer 7: Per-product features (``product/*``, 831K LoC = 70% of codebase)
============================================================================

Where the product-specific AI features live:

* ``product/rovo`` — the AI assistant; biggest module (``rovo-impl`` 447K LoC)
* ``product/jira/jira-impl`` (9K LoC) — issue suggestion, comment summarization, work breakdown
* ``product/jsm/jsm-impl`` (**69K LoC** — far bigger than expected) — JSM AI features
* ``product/csm/csm-impl`` (**63K LoC**) — Customer Service AI
* ``product/confluence/confluence-impl`` (**27K LoC**) — Confluence AI
* ``product/aifeature/aifeature-impl`` (**59K LoC**) — non-conversational AI (whiteboard, editor, summaries)
* ``product/atlassianstudio/atlassianstudio-impl`` (5K LoC) — AgentChatExecutor 2,618 LoC = 55% of module
* ``product/agentstudio/agentstudio-impl`` (15K LoC) — publishing UI backend (the "create your own agent" surface)
* ``product/loom/loom-impl`` (3K LoC) — Loom video transcripts as knowledge

The **per-product impls are huge**. This was the biggest miss in the prior catalog: jsm/csm/aifeature/confluence
were all documented as small modules; they're collectively **216K LoC** of per-product feature code.

Layer 8: Foundations and contrib (~34K LoC)
==============================================

* **Foundation** (26.5K LoC across 11 modules) — Atlassian platform integrations: utilities, metrics,
  feature-flag client, ADK core, ERS client. ArchUnit-enforced "may not depend on platform/product/service".
* **Contrib** (7.4K LoC across 4 modules) — sub-team-contributed clients/services: TAP (targeting platform),
  A2A (agent-to-agent), JQL services (natural-language → JQL).

Layer 9: Service mesh + sidecar (declared in ``convo-ai.ad.yml``)
====================================================================

The Atlas/Micros deployment descriptor declares 7 mesh dependencies on other Atlassian services:
Formosa, TAP, JSWDD, Maui, DevAI, DSS, TWG. Plus a Python sidecar (separate container — likely
tokenization or other Python-only ML helpers).

The chat sandbox is also a separate top-level Docker container (``rovo-chat-sandbox-code-executor/``
in the repo root, NOT inside ``modules/``) addressed via the ``platform/sandbox`` API.

What's missing from the codebase
==================================

Notable absences worth understanding:

* **No first-class workflow framework** beyond SimpleLoop. Marathon/LongHorizon/Hybrid orchestrators
  in rovo-impl are ad-hoc, not formalized as a generic state-machine framework.
* **No central "context assembly" module.** Building an LLM context (system prompt + history + retrieved
  knowledge + tools) is scattered across content-retrieval, conversation-impl, llm/processor, and
  per-product code.
* **No central RAG module.** As noted above, retrieval is distributed.
* **No A/B testing module.** Statsig provides feature flags, but cohort-based A/B testing infrastructure
  isn't visible (may live in ``contrib/service-impl`` TAP integration).

Where you'd actually edit code, by task
==========================================

Quick reference for "where do I make this change?":

* **Add a new chat endpoint** → ``service/convo-ai-service/rest/v1/`` or ``rest/v2/``
* **Add a new LLM provider** → ``platform/service/service-impl/llm/languagemodelprovider/``
* **Add a new tool to the registry** → ``platform/tool-registry/tool-registry-impl/`` (pick MCP, Forge, Native, or Integrations)
* **Add a new search source** → ``platform/service/service-impl/search/providers/``
* **Add a Jira-specific feature** → ``product/jira/jira-impl/``
* **Add a Rovo agent** → ``product/rovo/rovo-impl/agent/orchestrators/`` (orchestrator) or ``agent/minions/`` (skill)
* **Add a knowledge source type** → ``platform/base-api/KnowledgeSourceType.kt`` enum + ``platform/knowledge/`` impl
* **Add a feature flag** → ``platform/base-api`` (per-product flags) or ``product/shared-features-api`` (cross-product)
* **Add an SQS worker** → ``service/convo-ai-service/service/sqs/queue/<queue_name>/``
* **Add an ERS-stored entity** → ``-spi`` module in the relevant tier + ``-impl`` for the store
* **Add an evaluation metric** → ``platform/evaluation/evaluation-impl/service/BatchJudgementExecutionServiceImpl.kt``
* **Add a tenant-context interceptor** → ``service/convo-ai-service/service/interceptors/``

