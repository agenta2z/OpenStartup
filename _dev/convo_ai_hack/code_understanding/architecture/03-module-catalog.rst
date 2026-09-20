.. _module-catalog:

============================
Module Catalog (84 modules)
============================

This page lists every Gradle module in the codebase with a one-line role description. For deep dives on a tier, see :ref:`service-tier`, :ref:`product-tier`, :ref:`platform-tier`, :ref:`foundation-tier`, :ref:`contrib-tier`.

contrib/ (4 modules)
=====================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Path
     - Role
   * - ``contrib/client/client-api``
     - Vendor adapter client API contracts
   * - ``contrib/client/client-impl``
     - Vendor adapter client implementations
   * - ``contrib/service/service-api``
     - Vendor service API contracts
   * - ``contrib/service/service-impl``
     - Vendor service implementations

foundation/ (11 modules)
=========================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Path
     - Role
   * - ``foundation/adk/core-api``
     - Agent Development Kit contracts (agent definition, tool registration)
   * - ``foundation/adk/core-impl``
     - ADK runtime that loads agents and dispatches tool calls
   * - ``foundation/capabilities/capabilities-api``
     - Async task / MCP / Aqui contracts
   * - ``foundation/capabilities/capabilities-spi``
     - Pluggable capability extension points
   * - ``foundation/capabilities/capabilities-impl``
     - Concrete capability implementations
   * - ``foundation/context/context-api``
     - TenantContext, TenantContextService contracts
   * - ``foundation/context/context-impl``
     - AsyncTenantContextService, TcsService implementations
   * - ``foundation/llm-models/llm-models-api``
     - Unified LLM request/response types across providers
   * - ``foundation/testing/arch``
     - ArchUnit assertions for tier rules
   * - ``foundation/utilities/utilities-api``
     - 15 sub-packages of cross-cutting primitives (cache, logging, metrics, ...)
   * - ``foundation/utilities/utilities-impl``
     - Filters (HeaderFilter, ExperienceRateLimitFilter), interceptors, concrete utility impls

platform/ (36 modules)
=======================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Path
     - Role
   * - ``platform/action/action-api``
     - Action (tool execution) contracts
   * - ``platform/action/action-spi``
     - Pluggable action provider extension points
   * - ``platform/action/action-impl``
     - Concrete action executors
   * - ``platform/agent-version/agent-version-api``
     - Agent version management contracts
   * - ``platform/agent-version/agent-version-spi``
     - Pluggable version source extension points
   * - ``platform/agent-version/agent-version-impl``
     - Agent versioning runtime
   * - ``platform/base/base-api``
     - Lowest-common-denominator platform vocabulary
   * - ``platform/base/base-impl``
     - Base type implementations
   * - ``platform/client/client-api``
     - Downstream service client contracts
   * - ``platform/client/client-impl``
     - gRPC stubs and HTTP client implementations
   * - ``platform/conversation/conversation-api``
     - Conversation state management contracts
   * - ``platform/conversation/conversation-spi``
     - Pluggable conversation store extension points
   * - ``platform/conversation/conversation-impl``
     - Conversation state implementation (history, branching, replay)
   * - ``platform/convo-ai-test-utils``
     - Shared test fixtures (FeatureGateContextProvider, MockLLMServiceRetry, ...)
   * - ``platform/evaluation/evaluation-api``
     - Quality assessment contracts (judges, metrics)
   * - ``platform/evaluation/evaluation-spi``
     - Pluggable evaluator extension points
   * - ``platform/evaluation/evaluation-impl``
     - Batch evaluation harness
   * - ``platform/knowledge/knowledge-api``
     - Knowledge base contracts
   * - ``platform/knowledge/knowledge-spi``
     - Pluggable knowledge source extension points
   * - ``platform/knowledge/knowledge-impl``
     - Vector store / retrieval implementation
   * - ``platform/knowledge-gap/knowledge-gap-api``
     - Knowledge-gap tracking contracts
   * - ``platform/knowledge-gap/knowledge-gap-spi``
     - Pluggable gap-detector extension points
   * - ``platform/knowledge-gap/knowledge-gap-impl``
     - Knowledge-gap analysis implementation
   * - ``platform/sandbox/sandbox-api``
     - Code-execution sandbox contracts
   * - ``platform/sandbox/sandbox-impl``
     - Sandbox runtime (likely wraps rovo-chat-sandbox-code-executor)
   * - ``platform/service/service-api``
     - Service-tier integration contracts
   * - ``platform/service/service-impl``
     - **Hosts AIGatewayClientServiceImpl (3,087 lines) — the LLM orchestrator**
   * - ``platform/stratus-contracts/stratus-api``
     - Stratus (Atlassian observability) event contracts
   * - ``platform/stratus-contracts/stratus-spi``
     - Stratus pluggable extension points
   * - ``platform/tool-registry``
     - Top-level tool-registry module (umbrella)
   * - ``platform/tool-registry/tool-registry-api``
     - Tool registration and lookup contracts
   * - ``platform/tool-registry/tool-registry-impl``
     - Tool registry implementation
   * - ``platform/widget/widget-api``
     - UI widget rendering specifications (cards, charts, forms)
   * - ``platform/workflow``
     - Top-level workflow module (umbrella)
   * - ``platform/workflow/workflow-api``
     - Workflow orchestration contracts
   * - ``platform/workflow/workflow-impl``
     - Multi-step agent execution graph runtime

product/ (29 modules)
======================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Path
     - Role
   * - ``product/adk/adk-agent-api``
     - Agent Development Kit user-facing API
   * - ``product/adk/adk-dev``
     - ADK dev utilities and tooling
   * - ``product/agent-framework/agent-framework-impl``
     - Core agent framework templates; Stratus minion configurations
   * - ``product/agentstudio/agentstudio-api``
     - AgentStudio CRUD/scenarios/skills GraphQL contracts
   * - ``product/agentstudio/agentstudio-impl``
     - AgentStudio backend (CRUD, batch evaluation, conversation review, widget mgmt)
   * - ``product/aifeature/aifeature-api``
     - Cross-product writing/summarization contracts
   * - ``product/aifeature/aifeature-spi``
     - Pluggable AI feature extension points
   * - ``product/aifeature/aifeature-impl``
     - Cross-product features (smart links, comment summary, sprint summary, suggest issues)
   * - ``product/atlassianstudio/atlassianstudio-api``
     - Atlassian Studio contracts (site context, access control)
   * - ``product/atlassianstudio/atlassianstudio-impl``
     - Atlassian Studio impl (AtlassianStudioContextQueryController, AccessServiceImpl)
   * - ``product/chat-common/chat-common-api``
     - Shared chat/messaging abstractions across products
   * - ``product/confluence/confluence-api``
     - Confluence integration contracts
   * - ``product/confluence/confluence-impl``
     - Confluence space recommendations, page content analysis
   * - ``product/csm/csm-api``
     - Customer Success Management contracts
   * - ``product/csm/csm-impl``
     - CSM workflows (email suppression, migration analysis, refund, password reset; skills as markdown)
   * - ``product/jira/jira-api``
     - Jira integration contracts
   * - ``product/jira/jira-impl``
     - Jira templates (comment summary, sprint summary, suggest issues, work breakdown)
   * - ``product/jpd/jpd-api``
     - Jira Product Discovery contracts
   * - ``product/jpd/jpd-impl``
     - JPD integration backend
   * - ``product/jsm/jsm-api``
     - Jira Service Management contracts
   * - ``product/jsm/jsm-impl``
     - JSM journey crafting, request orchestration, HR agent selection
   * - ``product/loom/loom-api``
     - Loom video integration contracts
   * - ``product/loom/loom-impl``
     - Loom transcript / metadata integration with conversational platform
   * - ``product/rovo/rovo-api``
     - Rovo public contracts (SainService, agent definitions)
   * - ``product/rovo/rovo-spi``
     - Rovo pluggable extension points
   * - ``product/rovo/rovo-impl``
     - Rovo concrete impls (MarathonApiCallbackController, SAIN orchestrator, ...)
   * - ``product/rovo/rovo-extras-impl``
     - Non-core Rovo feature extensions
   * - ``product/rovo/rovo-leaf-agents-impl``
     - Leaf-level Rovo agent implementations
   * - ``product/rovo/marathon-stubs-publisher``
     - Publishes Marathon test stubs for integration testing
   * - ``product/shared-features/shared-features-api``
     - Common feature abstractions across products

service/ (5 modules)
=====================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Path
     - Role
   * - ``service/convo-ai-docker-image``
     - Spring Boot bootstrap, Docker packaging, Reactor + OTel context init (Application.kt)
   * - ``service/convo-ai-service``
     - Core REST/GraphQL controllers, SQS handlers, admin services, KaminoBootstrapController
   * - ``service/convo-ai-service-api``
     - Public API contracts (REST guards, GraphQL resolvers, store interfaces)
   * - ``service/convo-ai-service-descriptor``
     - Atlassian Deployment descriptor (convo-ai.ad.yml) — pure declarative manifest
   * - ``service/testing/arch``
     - ArchUnit-style architecture tests (layer isolation enforcement)

Total
======

- **contrib:** 4 modules
- **foundation:** 11 modules
- **platform:** 36 modules
- **product:** 29 modules
- **service:** 5 modules
- **Total: 85 gradle modules** (verified by ``find modules -name build.gradle.kts | wc -l``)

Note on accuracy
=================

The total of 85 here differs from the 86 estimate in :ref:`arch-overview` due to one module (``platform/widget`` umbrella) not having its own ``build.gradle.kts``. The functional area count remains 15 across platform.

This catalog is a snapshot at commit ``9151ac1341583a0a1ba81d5742f904ff2c43d62b`` on branch ``main``. New modules added after this snapshot are not listed.

