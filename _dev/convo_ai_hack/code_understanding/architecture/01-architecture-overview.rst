.. _arch-overview:

==========================
Architecture Overview
==========================

Mental model in one paragraph
==============================

The Conversational AI Platform is a **multi-tenant Kotlin/Spring Boot service** that
brokers conversational AI capabilities across all Atlassian products (Jira,
Confluence, JSM, Loom, JPD, AgentStudio, Rovo). It receives REST and GraphQL
requests, routes them to product-specific or shared agentic workflows, calls
out to LLMs via a unified AI Gateway, persists durable state via Kamino + Redis,
processes async work via SQS + Aqui queues, and streams results back via SSE.
The codebase is organized as a **5-tier hexagonal architecture** with strict
dependency-direction enforcement (see :ref:`build-rules` below).

The 5 tiers
============

::

   ┌────────────────────────────────────────────────────────────────┐
   │  service/    (5 modules)                                       │
   │    Spring Boot bootstrap, REST + GraphQL controllers,          │
   │    SQS handlers, deployment descriptor                         │
   └────────────────────────────────────────────────────────────────┘
                               ↓ depends on
   ┌────────────────────────────────────────────────────────────────┐
   │  product/    (30 modules)                                      │
   │    Per-product business logic: jira, confluence, jsm, csm,     │
   │    loom, jpd, agentstudio, atlassianstudio, rovo, aifeature,   │
   │    chat-common, agent-framework, adk, shared-features          │
   └────────────────────────────────────────────────────────────────┘
                               ↓ depends on
   ┌────────────────────────────────────────────────────────────────┐
   │  platform/   (36 modules)                                      │
   │    Cross-product capabilities: agent-version, tool-registry,   │
   │    conversation, knowledge, action, evaluation, workflow,      │
   │    sandbox, widget, base, client, service, etc.                │
   │    (api / spi / impl per area; impl never crossed)             │
   └────────────────────────────────────────────────────────────────┘
                               ↓ depends on
   ┌────────────────────────────────────────────────────────────────┐
   │  foundation/ (11 modules)                                      │
   │    Infrastructure primitives: TenantContext, RolloutService,   │
   │    MdcLoggingContext, AsyncStreamingTask, MCP/Aqui clients,    │
   │    LLM model unifying types, ADK core                          │
   │    *Foundation cannot depend on platform/product/service*      │
   └────────────────────────────────────────────────────────────────┘
                               ↓ depends on
   ┌────────────────────────────────────────────────────────────────┐
   │  contrib/    (4 modules)                                       │
   │    Vendor-specific adapters; tier intended for outside         │
   │    contributions                                               │
   └────────────────────────────────────────────────────────────────┘

.. _build-rules:

Architectural rules (enforced by Gradle)
========================================

These rules are documented in ``AGENTS.md`` lines 19-26. **Enforcement is
mixed:** some are caught at build time, some at test time, and some are
documented-only and rely on code review. See :ref:`diag-tier-graph` for the
full enforcement matrix with file:line evidence.

1. **api / spi / impl separation** *(documented only — no automated check)*.
   Interfaces and DTOs live in ``-api``. Implementations in ``-impl``.
   No module **should** depend on another module's ``-impl``. Reviewers must
   catch violations.

2. **spi modules** *(documented only)*. SPI references should be limited to the
   matching ``-impl`` and ``convo-ai-service``. No automated enforcement found.

3. **Platform cannot depend on Product or AiFeature** *(BUILD-TIME)*. Strict
   downward arrow. Enforced via ``GradleException`` in ``build.gradle.kts:588,
   596``. PRs that violate this fail at dependency resolution.

4. **Foundation modules are isolated** *(TEST-TIME)*. May only depend on other
   ``convo-ai-foundation-*`` modules or ``convo-ai-test-utils``. Enforced by
   ArchUnit at ``foundation/testing/arch/.../FoundationModuleArchTest.kt:19-33``
   — fails the test suite (not the build) on violation.

5. **Foundation tests must use MockK** *(BUILD-TIME)*. Mockito, PowerMock,
   EasyMock, Spock are forbidden via ``GradleException`` at
   ``build.gradle.kts:628``. PRs that try to add forbidden libraries fail
   at dependency resolution.

Bootstrap entry point :sup:`(verified)`
========================================

The service starts at:

.. code-block:: text

   modules/service/convo-ai-docker-image/src/main/kotlin/io/atlassian/micros/convoai/Application.kt

Key annotations on the Application class (lines 12-23):

.. code-block:: kotlin

   @ExcludeFromCoverage(reason = "Spring Boot application entry point")
   @EnableSqsQueues                  // SQS lifecycle events
   @EnableAquiQueues                 // Async task queue
   @SpringBootApplication(
       scanBasePackages = [
           "io.atlassian.micros.convoai",
           "io.atlassian.micros.convoai.product.csm.config",
           "io.atlassian.micros.convoai.product.jsm.config",
           "io.atlassian.micros.convoai.product.jira.config",
           "io.atlassian.micros.convoai.product.loom.config",
       ],
   )
   class Application

The ``main()`` function (lines 27-40) installs ``Hooks.onErrorDropped`` to log
dropped Reactor errors with exception-type context, then runs Spring Boot with
``ContextPropagationInitializer`` added — the latter is what enables MDC and
OTel context to survive coroutine boundaries.

A startup listener (``ConvoAiApplicationStartupListener.kt``) validates that
``SqsMicrosLifecycleEventHandler`` is loaded; if absent, throws
``IllegalStateException``. This is a hard fail-fast for misconfigured
deployments.

What "request lifecycle" looks like
====================================

For a high-level mental model, here's the typical flow of a chat request:

1. **Ingress** — HTTP request hits ``ChatV1Controller`` at
   ``modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt``.

2. **Authentication** — SLAuth headers validated; ASAP-issued service identity
   resolved into a ``User`` object (``foundation/utilities/user``).

3. **Tenant context** — ``TenantContext`` resolved from headers (cloud_id) and
   stored in request scope. Async-safe propagation via
   ``AsyncTenantContextService``.

4. **Routing** — Per-product controller dispatches to a workflow (e.g.
   ``SAINStandaloneHybridOrchestrator`` for Slack AI Notification flows).

5. **LLM call** — ``AIGatewayClientServiceImpl`` (3,087 lines) calls AI Gateway
   with attribution headers (``USE_CASE_ID``, ``CLOUD_ID``, ``USER_ID``,
   ``USER_CONTEXT``). May stream or batch.

6. **Streaming** — Response chunks flow back via ``Flux<Any>`` /
   ``Flow<ChatCompletionStreamResponse>``; SSE wrapped in ndjson media type.

7. **Persistence** — Conversation state written to Kamino (event log) and
   per-conversation Redis caches.

8. **Async tasks** — Long-running work queued via Aqui (e.g. batch evaluation,
   knowledge indexing).

9. **Telemetry** — All steps emit metrics (per-tenant, per-product,
   per-use-case) and OTel spans.

See :ref:`request-lifecycle` for the full diagram with file:line citations.

What this overview is NOT
==========================

- **NOT a class diagram.** With 12,990 source files, a class diagram would be
  noise. Focus instead on the tier boundaries and rule enforcement.

- **NOT exhaustive.** The 86-module catalog (in :ref:`module-catalog`) gives you
  the index; the per-tier deep dives explain the patterns.

- **NOT a build-system tutorial.** Build internals (Kover coverage tiers,
  Detekt rules, ktlint, lockfile workflows) are documented separately in
  :ref:`build-system`.

