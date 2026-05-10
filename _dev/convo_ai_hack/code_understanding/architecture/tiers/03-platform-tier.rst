.. _platform-tier:

============================
Platform Tier (36 modules)
============================

The **platform tier** holds cross-product capabilities — anything that more than one product needs but isn't a low-level utility. It depends on the foundation tier (and contrib); product and service tiers depend on it.

**Hard rule:** platform CANNOT depend on product or aifeature. Enforced by Gradle (AGENTS.md line 22).

15 functional areas :sup:`(verified by directory listing)`
============================================================

::

   action/                  (api/impl/spi)         3 modules
   agent-version/           (api/impl/spi)         3 modules
   base/                    (api/impl)             2 modules
   client/                  (api/impl)             2 modules
   conversation/            (api/impl/spi)         3 modules
   convo-ai-test-utils                             1 module
   evaluation/              (api/impl/spi)         3 modules
   knowledge/               (api/impl/spi)         3 modules
   knowledge-gap/           (api/impl/spi)         3 modules
   sandbox/                 (api/impl)             2 modules
   service/                 (api/impl)             2 modules
   stratus-contracts/       (api/spi)              2 modules
   tool-registry/           (api/impl + base)      3 modules
   widget/                  (api only)             1 module
   workflow/                (api/impl + base)      3 modules

   Total: 36 modules

The api/impl/spi pattern :sup:`(verified)`
============================================

Most areas split into 3 gradle modules:

- ``-api``: data classes, public interfaces, exceptions. Whole platform tier and product tier depend on this.
- ``-spi``: Service Provider Interface — pluggable contracts. Only ``-impl`` and ``convo-ai-service`` may reference. (AGENTS.md line 21)
- ``-impl``: concrete implementation. **No module can depend on another module's -impl.** (AGENTS.md line 19)

This forbids implementation-leakage and forces extension to happen via SPI registration rather than direct call sites.

Functional areas
=================

action/ :sup:`(inferred — high confidence)`
--------------------------------------------

Tools/actions an agent can invoke ("execute_python", "run_jql_query", etc.). The api/spi/impl split suggests pluggable action implementations. Expected interfaces:

- ``ActionRegistry`` — list/lookup actions
- ``ActionExecutor`` — invoke an action with arguments
- ``ActionResult`` — wrapped success/failure with retry hints

agent-version/ :sup:`(inferred — high confidence)`
---------------------------------------------------

Versioning agent definitions. Critical for AgentStudio's "publish v3 of agent X" flows. The agent-studio failures in the integration test suite (3× ``AgentStudioUpgradeSchemaIT``) hit this tier when ``data.agentStudio_upgradeSchema.success`` returned ``false``.

base/ :sup:`(inferred)`
-----------------------

Shared types likely used across all platform areas: ``Conversation``, ``Message``, ``Agent``, ``ToolCall``, ``Citation``. The "lowest common denominator" of platform vocabulary.

client/ :sup:`(inferred — high confidence)`
--------------------------------------------

Client SDKs for downstream services. Likely contains gRPC stubs (the agent investigation found proto definitions in ``client-impl``) for talking to Marathon, AssistanceClient, etc.

conversation/ :sup:`(inferred — high confidence)`
--------------------------------------------------

Conversation state management — message history, branching, replay. Most ``GET /chat/v1/channel/{id}/messages`` requests pass through here.

convo-ai-test-utils :sup:`(verified — partial)`
------------------------------------------------

Test fixtures used across the codebase. Verified files include:

- ``modules/platform/convo-ai-test-utils/src/main/kotlin/io/atlassian/micros/convoai/testutils/testframework/featuregate/FeatureGateContextProvider.kt:34`` — feature gate test infrastructure
- ``modules/platform/convo-ai-test-utils/src/main/kotlin/io/atlassian/micros/convoai/testutils/testframework/mocks/MockLLMServiceRetry.kt`` — LLM retry mock pattern

This module is exempt from the "foundation must use MockK" rule because it IS the test-utility module.

evaluation/ :sup:`(inferred)`
------------------------------

Quality assessment — judges, metrics, batch evaluation harness. Backed by AgentStudio's batch-evaluation REST controller (``AgentStudioBatchEvaluationV1ControllerIT``).

knowledge/ :sup:`(inferred)`
-----------------------------

Knowledge base management. Vector store integration, document ingestion, retrieval. Probably wraps a vector DB client (Pinecone/Weaviate/etc.) behind the ``-api`` interface.

knowledge-gap/ :sup:`(inferred)`
---------------------------------

Tracking which knowledge base topics have been queried but lack good answers. Used for prioritizing knowledge base expansion.

sandbox/ :sup:`(inferred — high confidence)`
---------------------------------------------

Isolated execution environment for arbitrary code generated by an agent. The repo also has ``rovo-chat-sandbox-code-executor/`` at the top level — likely the docker container; the platform module is the in-process API.

service/ :sup:`(verified — high confidence — most important)`
--------------------------------------------------------------

This is where ``AIGatewayClientServiceImpl`` lives:

``modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/AIGatewayClientServiceImpl.kt``

3,087 lines of LLM orchestration code. See :ref:`ai-gateway` for the full deep-dive.

Other key files in service/service-impl:

- ``platform/service/helpkosh/HelpKoshReactiveClientFilter.kt`` (verified existence) — HelpKosh integration filter
- ``platform/service/ors/OrsFilter.kt`` (verified existence) — ORS integration filter

stratus-contracts/ :sup:`(inferred)`
-------------------------------------

Contracts for Stratus (Atlassian's internal observability/data platform). The service likely emits structured events to Stratus for downstream analytics.

tool-registry/ :sup:`(inferred)`
---------------------------------

Tool definitions an LLM agent can invoke. Different from ``action/`` — likely the registry is the catalog of TOOL definitions (name, JSON schema, description), while action is the EXECUTION machinery.

widget/ :sup:`(inferred)`
--------------------------

UI widget rendering specifications. Agent responses can include widgets (cards, charts, forms) that the client renders. ``-api`` only suggests this is mostly contracts; rendering happens client-side.

workflow/ :sup:`(inferred)`
----------------------------

Workflow orchestration — multi-step agent execution graphs. Likely backs the SAIN orchestrator and Marathon executor.

Cross-cutting capabilities housed in platform
==============================================

These deserve their own pages (linked from cross-cutting concerns chapter):

- **AI Gateway client** (``platform/service/service-impl``) — see :ref:`ai-gateway`
- **Conversation routing** (``platform/conversation``) — see :ref:`request-lifecycle`
- **Tool registry / Action executor** (``platform/tool-registry`` + ``platform/action``)

Patterns specific to platform tier
====================================

1. **api/spi/impl is non-negotiable.** Try to add a class to a ``-api`` module that imports from ``-impl`` — Gradle will reject the build at dependency-resolution time.

2. **No product names.** Module names are concept-based (action, conversation, knowledge), not product-based. Product-specific behavior happens in product/, not platform/.

3. **SPI = extension point.** When you see ``-spi``, that's a deliberate "future implementations may plug in here". Examples: pluggable LLM providers, pluggable action executors, pluggable knowledge stores.

4. **Service-impl is enormous.** The 3,087-line ``AIGatewayClientServiceImpl`` is a code smell — but it's intentionally consolidated because LLM orchestration involves many cross-cutting concerns (retry, fallback, attribution, metrics, error categorization) that are hard to split.

What you would change here
===========================

- **Add a new tool** → register in tool-registry-api/spi; implement in tool-registry-impl
- **Change retry policy** → modify the ``AIGatewayClientServiceImpl`` factory (be careful)
- **Add a new evaluator** → implement evaluation-spi interface; register impl
- **Add a new knowledge source** → implement knowledge-spi

What you would NOT change here
===============================

- **Per-product behavior** (lives in product/)
- **Authentication / tenant context** (lives in foundation/)
- **REST endpoint paths** (lives in service/)

