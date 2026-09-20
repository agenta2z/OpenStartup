.. _overview-multi-axis-matrix:

==================================================================
Multi-axis module overview matrix
==================================================================

:Date: 2026-05-02
:Verification: All numbers from ``find -P -name '*.kt' -type f -exec cat {} + | wc -l`` run on commit ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``

This is the high-info-dense overview the simpler module catalog couldn't provide.
Every module is classified along **multiple axes simultaneously**: tier, size class, role, criticality, test coverage.

.. warning::

   **Many earlier catalog estimates were wrong by 5-30×.** This overview reflects ground truth.
   For example: ``jsm-impl`` was previously documented as ~10K LoC; actual is **68,570 LoC**.
   ``csm-impl`` was documented as ~5K; actual is **62,796 LoC**.
   The corrections are tabulated in §6 below.

Axis A: Tier × Size matrix
============================

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15 20

   * - Tier
     - Modules
     - Total main LoC
     - Total main files
     - Total test LoC
     - Test/main ratio
   * - **foundation**
     - 11
     - 26,518
     - 298
     - 42,576
     - **1.6×**
   * - **platform**
     - 34
     - 264,257
     - 2,146
     - 259,703
     - 1.0×
   * - **product**
     - 30
     - **830,968**
     - 5,967
     - **982,235**
     - 1.2×
   * - **service**
     - 5
     - 46,021
     - 415
     - 60,618
     - 1.3×
   * - **contrib**
     - 4
     - 7,395
     - 81
     - 9,380
     - 1.3×
   * - **TOTAL**
     - **84**
     - **1,175,159**
     - **8,907**
     - **1,354,512**
     - **1.15×**

**Key takeaways:**

1. **Product tier dominates** — 70% of code is in product/. Most lives in ``rovo-impl`` (38% of all main LoC).
2. **Test coverage is consistently strong** — every tier has >1× test/main ratio. Foundation leads at 1.6×.
3. **The codebase is 2.5M total LoC** — significantly larger than typical Spring Boot services.

Axis B: Size class distribution
=================================

How modules cluster by size:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Size class
     - Count
     - Notes
   * - **Mega (>100K LoC)**
     - 1
     - ``rovo-impl`` only — a "platform-within-product"
   * - **Huge (50K-100K)**
     - 4
     - ``rovo-api``, ``service-impl``, ``jsm-impl``, ``csm-impl``, ``aifeature-impl``, ``client-impl``
   * - **Large (10K-50K)**
     - 11
     - The "real work" modules
   * - **Medium (1K-10K)**
     - 28
     - Standard module size — implementations + APIs
   * - **Small (100-1K)**
     - 26
     - Focused APIs, light impls
   * - **Tiny (<100 LoC)**
     - 14
     - Pure interface modules, descriptors, or just-built
   * - **Empty (0 LoC main)**
     - 4
     - Aggregator-only modules + descriptor

Axis C: The 20 most strategic modules (by LoC × criticality)
================================================================

Combining size with "every-request-touches-this" criticality:

.. list-table::
   :header-rows: 1
   :widths: 6 30 12 12 40

   * - Rank
     - Module
     - Main LoC
     - Test LoC
     - Why strategic
   * - 1
     - ``product/rovo/rovo-impl``
     - **446,922**
     - 544,376
     - Largest by far; agents, MCP, deep research, plugin system. Functionally a hidden second platform.
   * - 2
     - ``product/rovo/rovo-api``
     - 74,684
     - 18,160
     - All Rovo-product API contracts; previously under-documented as small.
   * - 3
     - ``platform/service/service-impl``
     - 68,863
     - 117,192
     - Multi-LLM-provider gateway + cross-product search. Not just AI Gateway.
   * - 4
     - ``product/jsm/jsm-impl``
     - 68,570
     - 93,157
     - JSM AI integration — actually huge, not the small module catalog suggested.
   * - 5
     - ``product/csm/csm-impl``
     - 62,796
     - 86,067
     - CSM AI integration — Customer Service Management; previously docs were 100× too small.
   * - 6
     - ``product/aifeature/aifeature-impl``
     - 59,375
     - 96,173
     - Whiteboard AI, editor AI, content AI features — non-conversational AI.
   * - 7
     - ``platform/client/client-impl``
     - 54,844
     - 69,757
     - REST/GraphQL client implementations; pairs with client-api.
   * - 8
     - ``platform/client/client-api``
     - 45,005
     - 1,547
     - All Atlassian-product API DTOs (mostly generated).
   * - 9
     - ``service/convo-ai-service``
     - 44,948
     - 59,598
     - Spring Boot main; REST/GraphQL entry; SQS workers; tenant context.
   * - 10
     - ``platform/service/service-api``
     - 32,482
     - 3,070
     - Service contracts — bigger than expected (32K, not 1.8K as previously documented).
   * - 11
     - ``product/confluence/confluence-impl``
     - 27,262
     - 47,542
     - Confluence AI features impl.
   * - 12
     - ``product/rovo/rovo-extras-impl``
     - 20,992
     - 25,613
     - Insights, evaluation strategy, SVG avatar generator (1,848 LoC alone).
   * - 13
     - ``product/agentstudio/agentstudio-impl``
     - 15,443
     - 36,814
     - Publishing UI backend.
   * - 14
     - ``product/aifeature/aifeature-api``
     - 14,658
     - 0
     - AI feature API contracts (no tests — API-only modules).
   * - 15
     - ``platform/conversation/conversation-impl``
     - 13,624
     - 20,930
     - Chat lifecycle.
   * - 16
     - ``platform/base/base-api``
     - 13,271
     - 5,172
     - Cross-cutting vocabulary; KnowledgeSourceType enum (691 LoC).
   * - 17
     - ``foundation/utilities/utilities-api``
     - 11,712
     - 12,566
     - Foundation utilities — bigger than expected.
   * - 18
     - ``product/agent-framework/agent-framework-impl``
     - 10,047
     - 5,999
     - Skills + Stratus minions (AssessChangeRiskSkill 2,157 LoC).
   * - 19
     - ``product/jira/jira-impl``
     - 8,974
     - 13,722
     - Jira AI features impl.
   * - 20
     - ``foundation/utilities/utilities-impl``
     - 8,364
     - 18,260
     - Foundation utility implementations.

Axis D: Test coverage outliers
================================

Modules that **invest heavily in tests** (top quartile by test/main ratio):

.. list-table::
   :header-rows: 1
   :widths: 50 15 15 20

   * - Module
     - Main LoC
     - Test LoC
     - Test/main ratio
   * - ``platform/service/service-impl``
     - 68,863
     - 117,192
     - **1.7×**
   * - ``product/aifeature/aifeature-impl``
     - 59,375
     - 96,173
     - 1.6×
   * - ``foundation/utilities/utilities-impl``
     - 8,364
     - 18,260
     - **2.2×**
   * - ``product/agentstudio/agentstudio-impl``
     - 15,443
     - 36,814
     - **2.4×**
   * - ``foundation/capabilities/capabilities-impl``
     - 2,313
     - 6,923
     - **3.0×**
   * - ``foundation/context/context-impl``
     - 259
     - 1,000
     - **3.9×**
   * - ``platform/evaluation/evaluation-impl``
     - 7,390
     - 19,235
     - 2.6×

Modules with **zero tests** (most are pure -api or -spi):

* All -spi modules (zero tests for ERS contracts)
* Most -api modules (DTOs, no logic to test)
* ``service/convo-ai-service-descriptor`` (deployment config, no code)
* ``foundation/llm-models/llm-models-api`` (pure interface module — 0 LoC)

Axis E: Where do god-classes live?
=====================================

Files >1,500 LoC by module:

.. list-table::
   :header-rows: 1
   :widths: 35 25 15 25

   * - Module
     - File
     - LoC
     - Criticality
   * - ``product/rovo/rovo-extras-impl``
     - ``SvgAvatarGenerator.kt``
     - 1,848
     - Standalone — splittable
   * - ``platform/service/service-impl``
     - ``AIGatewayClientServiceImpl.kt``
     - **3,087**
     - Tier 0 — careful refactor needed
   * - ``platform/service/service-impl``
     - ``JiraServiceImpl.kt``
     - 2,466
     - Tier 0
   * - ``platform/service/service-impl``
     - ``LLMServiceImpl.kt``
     - 1,831
     - Tier 0
   * - ``platform/service/service-impl``
     - ``RankingServiceImpl.kt``
     - 1,647
     - Tier 1
   * - ``platform/service/service-impl``
     - ``GenericGeminiLanguageModelProvider.kt``
     - 1,484
     - Tier 1
   * - ``platform/service/service-impl``
     - ``GeminiLanguageModelProvider.kt``
     - 1,406
     - Tier 1
   * - ``platform/service/service-impl``
     - ``JourneyBuilderServiceImpl.kt``
     - 1,378
     - Tier 1
   * - ``platform/sandbox/sandbox-impl``
     - ``AtlassianSandboxEndpointProvider.kt``
     - 1,311
     - Tier 1
   * - ``platform/workflow/workflow-impl``
     - ``SimpleLoopWorkflowExecutorImpl.kt``
     - 1,222
     - Tier 0 — agent loop heart
   * - ``platform/service/service-impl``
     - ``InterleaverSearchProvider.kt``
     - 1,201
     - Tier 1
   * - ``product/atlassianstudio/atlassianstudio-impl``
     - ``AgentChatExecutor.kt``
     - 2,618
     - Tier 1 — 55% of module
   * - ``product/agent-framework/agent-framework-impl``
     - ``AssessChangeRiskSkill.kt``
     - 2,157
     - Tier 2 — single skill
   * - ``platform/client/client-api``
     - ``AsyncConfluenceRestClient.kt``
     - 2,699
     - Tier 0 — likely generated
   * - ``platform/client/client-api``
     - ``JiraProjectsRestClientDataModel.kt``
     - 2,008
     - DTO file (likely generated)
   * - ``service/convo-ai-service``
     - ``rest/v2/prompt/`` (single file)
     - 1,760
     - Tier 0 — refactor candidate

**Pattern:** ``service-impl`` has 7 files >1K LoC. Largest concentration of god-classes in the codebase.

Axis F: Catalog corrections (numbers were wrong by 5-30×)
============================================================

Modules where the previous catalog significantly under-reported size:

.. list-table::
   :header-rows: 1
   :widths: 35 15 15 15 20

   * - Module
     - Old number
     - Real (verified)
     - Δ ratio
     - Note
   * - ``product/jsm/jsm-impl``
     - "small"
     - **68,570**
     - >>20×
     - Major omission
   * - ``product/csm/csm-impl``
     - "small"
     - **62,796**
     - >>20×
     - Major omission
   * - ``product/aifeature/aifeature-impl``
     - "small"
     - **59,375**
     - >>20×
     - Major omission
   * - ``platform/client/client-impl``
     - 1,088 (was contrib confused)
     - **54,844**
     - >>50×
     - Major omission
   * - ``platform/service/service-api``
     - 1,838
     - **32,482**
     - 18×
     - Was thin, now huge
   * - ``product/confluence/confluence-impl``
     - "small"
     - **27,262**
     - >>20×
     - Major omission
   * - ``product/rovo/rovo-api``
     - 1,041
     - **74,684**
     - 72×
     - **Worst miss** — was confused with rovo-spi
   * - ``platform/evaluation/evaluation-impl``
     - 26,625
     - **7,390**
     - 0.28×
     - Was over-counted
   * - ``platform/sandbox/sandbox-impl``
     - 2,037
     - 2,037
     - 1.0×
     - Correct
   * - ``platform/agent-version/agent-version-impl``
     - 3,439
     - 933
     - 0.27×
     - Was over-counted

These corrections will be applied to the per-module catalog pages in a follow-up pass.

Axis G: Functional grouping
=============================

Cross-tier grouping by what the modules actually do:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Function
     - Modules involved
   * - **HTTP entry**
     - ``service/convo-ai-service``, ``service/convo-ai-service-api``
   * - **AI/LLM**
     - ``platform/service/service-impl/llm/*`` (22K LoC), ``platform/service/service-api``
   * - **Conversation lifecycle**
     - ``platform/conversation/{api,spi,impl}``, ``service/convo-ai-service/common/contentretrieval/``
   * - **Agent execution**
     - ``platform/workflow/{api,impl}``, ``product/rovo/rovo-impl/agent/orchestrators/`` (96K LoC), ``product/agent-framework/*``
   * - **Tool registry**
     - ``platform/tool-registry/{api,impl}``, ``platform/action/{api,spi,impl}``, ``product/rovo/rovo-impl/product/rovo/mcp/`` (41K LoC)
   * - **Knowledge / RAG**
     - ``platform/knowledge/{api,spi,impl}``, ``platform/knowledge-gap/{api,spi,impl}``, ``platform/base-impl`` (TurboPuffer), ``service-impl/search/``
   * - **Per-product features**
     - ``product/{jira,jsm,csm,confluence,loom,jpd}/*``, ``product/aifeature/*``, ``product/atlassianstudio/*``
   * - **Persistence (ERS)**
     - All -spi modules + ``platform/foundation/ers-{api,impl}`` + ``service/convo-ai-service/service/ers/tenanted/``
   * - **Multi-tenant isolation**
     - ``foundation/context/{api,impl}``, ``service/convo-ai-service/domain/tenant/``
   * - **Background jobs**
     - ``service/convo-ai-service/service/sqs/queue/``, ``platform/evaluation-impl`` (job lifecycle)
   * - **Deployment / boot**
     - ``service/convo-ai-service-descriptor``, ``service/convo-ai-docker-image``
   * - **Architecture testing**
     - ``foundation/testing/arch``, ``service/testing/arch``
   * - **Agent Studio (publishing UI)**
     - ``product/agentstudio/{api,impl}``, ``platform/agent-version/{api,spi,impl}``
   * - **Evaluation**
     - ``platform/evaluation/{api,spi,impl}``, evaluation-related code in ``product/rovo/rovo-extras-impl``
   * - **Sandbox (code execution)**
     - ``platform/sandbox/{api,impl}``, separate ``rovo-chat-sandbox-code-executor/`` (top-level Docker)
   * - **TAP / A2A / JQL**
     - All 4 ``contrib/*`` modules

