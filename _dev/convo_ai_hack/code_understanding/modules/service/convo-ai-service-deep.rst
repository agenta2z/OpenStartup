.. _mod-convo-ai-service-deep:

==================================================================
``service/convo-ai-service`` — the entry-point layer
==================================================================

:Tier: service
:Path: ``modules/service/convo-ai-service``
:Size: **44,948 main + 59,598 test LoC** :sup:`(verified 2026-05-02)`
:Files: 389 main + 467 test
:Importance: ⭐⭐⭐⭐⭐ Tier 0 — Spring Boot main, every request enters here

The bootstrap layer that wires Spring DI, exposes REST/GraphQL endpoints, and orchestrates
the cross-cutting infrastructure needed by every request: SQS workers, Redis caches,
ERS stores, content retrievers, tenant context, streaming, GraphQL subscriptions.

Eight functional sub-systems
==============================

.. list-table::
   :header-rows: 1
   :widths: 30 12 12 46

   * - Sub-system
     - LoC
     - Files
     - What it is
   * - **Content retrieval**
     - **12,246**
     - 60
     - ``common/contentretrieval/`` — resolvers + Confluence-specific retriever
   * - **Tenant domain**
     - **5,611**
     - 24
     - ``domain/tenant/`` — multi-tenant isolation, context resolution
   * - **REST controllers**
     - **5,041**
     - 22
     - ``rest/v1/`` (chat) + ``rest/v2/prompt/`` + ``rest/internal/``
   * - **ERS tenanted stores**
     - 2,566
     - 60
     - ``service/ers/tenanted/`` — per-tenant entity persistence
   * - **SQS workers**
     - 1,907
     - 44
     - ``service/sqs/queue/`` — async background jobs
   * - **Redis caches**
     - 1,151
     - 37
     - ``service/redis/impl/`` — caching layer impls
   * - **Streamhub**
     - 1,437
     - 7
     - ``service/streamhub/`` — streaming response infrastructure
   * - **Provisioning**
     - 1,349
     - 13
     - ``service/provisioning/`` — tenant onboarding
   * - GraphQL
     - 866 + 560
     - 12
     - ``service/graphql/`` + ``service/graphql/subscription/``

Top sub-packages by LoC
=========================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Path
     - LoC
     - Role
   * - ``common/contentretrieval/resolvers/``
     - **7,948**
     - Generic content resolvers (39 files)
   * - ``domain/tenant/``
     - 5,611
     - Tenant context + isolation
   * - ``common/contentretrieval/confluence/``
     - 4,298
     - Confluence-specific retriever (specialized due to permissions complexity)
   * - ``rest/v1/``
     - 2,765
     - **All chat endpoints** — ChatV1Controller and siblings (18 files)
   * - ``service/ers/tenanted/``
     - 2,566
     - ERS tenant-sharded stores
   * - ``rest/v2/prompt/``
     - **1,760**
     - Single 1,760-line file — V2 prompt API
   * - ``common/assistance/``
     - 1,518
     - Cross-cutting assistance utilities
   * - ``service/streamhub/``
     - 1,437
     - Streaming response infrastructure
   * - ``service/provisioning/``
     - 1,349
     - Tenant provisioning
   * - ``service/redis/impl/``
     - 1,151
     - Redis cache implementations
   * - ``common/queryrewriter/``
     - 1,081
     - Query rewriting (2 files)
   * - ``common/orchestrator/``
     - 980
     - Generic orchestrator helpers
   * - ``service/sqs/queue/aqui/``
     - 977
     - AQUI (Async Query Index?) SQS queue
   * - ``service/sqs/queue/``
     - 930
     - Other SQS queue handlers (23 files)
   * - ``service/kamino/``
     - 833
     - Kamino integration (single file)
   * - ``common/teamcamp/``
     - 658
     - Teamcamp integration
   * - ``service/features/``
     - 646
     - Feature management
   * - ``service/interceptors/``
     - 578
     - Request interceptors
   * - ``service/graphql/subscription/``
     - 560
     - GraphQL subscriptions

What you would change here
============================

* **Add a new REST endpoint** → ``rest/v1/`` (chat APIs) or ``rest/v2/`` (newer APIs)
* **Add a new SQS queue handler** → ``service/sqs/queue/`` (subdir per queue)
* **Add a new content source for retrieval** → ``common/contentretrieval/resolvers/``
* **Add a Redis cache for a new entity** → ``service/redis/impl/``
* **Add a tenant-context interceptor** → ``service/interceptors/``
* **Add a GraphQL subscription** → ``service/graphql/subscription/``

What you would NOT change here
================================

* LLM invocation → :ref:`mod-service-impl`
* Conversation lifecycle → :ref:`mod-conversation-impl`
* Workflow execution loop → :ref:`mod-workflow-impl`
* ERS persistence contracts → ``platform/foundation/ers-api`` + ``ers-impl``

Critical observations
=======================

1. **The single 1,760-line file at ``rest/v2/prompt/``** stands out — should be checked for refactoring opportunity. Most other REST controllers are split across multiple files.

2. **``common/contentretrieval/resolvers/`` (8K LoC, 39 files)** is the largest sub-package — content retrieval is genuinely complex due to multi-source + permission-aware logic.

3. **Confluence has its own retriever package** (``common/contentretrieval/confluence/``, 4.3K LoC) — separate from the generic ``resolvers/``. Confluence's permission model is complex enough to warrant specialization.

4. **44K LoC of bootstrap layer** is noteworthy — the entry-point service is ~10× larger than typical Spring Boot main modules. Suggests too much logic has accumulated here that could move down to platform tier.

5. **59K LoC of test code** vs 45K main — strong test coverage for the highest-blast-radius module.

