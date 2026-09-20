.. _service-tier:

============================
Service Tier (5 modules)
============================

The **service tier** is the outermost layer — Spring Boot bootstrap, REST + GraphQL
controllers, SQS handlers, and the deployment descriptor. It depends on everything
below; nothing depends on it.

Modules
========

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Role
   * - ``service/convo-ai-docker-image``
     - Spring Boot bootstrap; Docker packaging; Reactor + OTel context init
   * - ``service/convo-ai-service``
     - Core REST/GraphQL controllers, SQS handlers, admin services, permissions
   * - ``service/convo-ai-service-api``
     - Public API contracts (REST guards, GraphQL resolvers, store interfaces)
   * - ``service/convo-ai-service-descriptor``
     - Atlassian Deployment descriptor (``convo-ai.ad.yml``); pure declarative manifest
   * - ``service/testing/arch``
     - ArchUnit-style architecture tests (layer isolation enforcement)

``convo-ai-docker-image`` :sup:`(verified)`
============================================

**File:** ``modules/service/convo-ai-docker-image/src/main/kotlin/io/atlassian/micros/convoai/Application.kt``

This is the JVM entry point. Annotations stack (lines 12-23):

.. code-block:: kotlin

   @ExcludeFromCoverage(reason = "Spring Boot application entry point")
   @EnableSqsQueues                  // line 13 — SQS lifecycle event handler
   @EnableAquiQueues                 // line 14 — async task queue support
   @SpringBootApplication(           // line 15
       scanBasePackages = [
           "io.atlassian.micros.convoai",
           "io.atlassian.micros.convoai.product.csm.config",
           "io.atlassian.micros.convoai.product.jsm.config",
           "io.atlassian.micros.convoai.product.jira.config",
           "io.atlassian.micros.convoai.product.loom.config",
       ],
   )
   class Application

The ``main()`` function (lines 27-40):

1. **Hooks.onErrorDropped** — logs Reactor errors that escape subscriber error handling. AIM-4394 ticket reference in the comment.
2. **ContextPropagationInitializer** — installs the bridge that lets MDC, OTel trace, and request attributes survive coroutine boundaries.

Other key files in this module (verified by directory listing):

- ``ContextPropagationInitializer.kt`` — installs RxJava + OTel context propagation hooks at Spring Application init time.
- ``ConvoAiApplicationStartupListener.kt`` — fail-fast guard: throws ``IllegalStateException`` if ``SqsMicrosLifecycleEventHandler`` bean is missing.
- ``CoroutineMonitorStartupListener.kt`` — observes coroutine pool health.

This module deliberately disables Detekt linting (per agent investigation; verify by reading ``build.gradle.kts``) to keep Docker builds fast.

``convo-ai-service`` :sup:`(agent-reported, partial-verify)`
=============================================================

This is the **biggest, most heterogeneous** module in the codebase. It aggregates 30+ internal APIs and SPIs and contains:

- **Controllers:** REST (``ChatV1Controller``, ``IndexController``), GraphQL (per-product resolvers)
- **Services:** ``AdminService``, ``PermissionService``, ``OrgAdminService``, ``StudioAdminService``
- **Frameworks:** ``AssuranceCapabilityFramework`` (acf folder)
- **Bootstrap controllers:** ``KaminoBootstrapController`` (rest folder)

Verified existence:
``modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt`` — 13 endpoints (verified via grep).

This module depends on ALL ``-api`` and ``-spi`` modules across foundation/platform/product. It is the **assembly point**: it does not own much business logic itself, but it wires controllers to platform services and product implementations.

``convo-ai-service-api`` :sup:`(agent-reported)`
=================================================

The **contract layer** that other modules depend on without pulling in the full ``convo-ai-service`` weight. Contains:

- ``rest/guard/`` — request validation contracts (return types, error envelopes)
- ``rest/v1/`` — versioned REST API contracts
- ``service/graphql/`` — GraphQL resolver interfaces
- ``service/provisioning/`` — provisioning interfaces (e.g. ``ProvisioningService``)
- ``service/store/`` — storage abstractions

This module is what other tiers depend on when they need to call back UP into the service layer (rare but happens for things like emitting standardized error envelopes).

``convo-ai-service-descriptor`` :sup:`(agent-reported)`
========================================================

**Pure declarative module** — zero code dependencies. The single source of truth for deployment configuration:

**File:** ``modules/service/convo-ai-service-descriptor/...convo-ai.ad.yml``

Approximate contents (per agent investigation; spot-verify before relying on specific lines):

- Service ID: ``convo-ai-archetype``
- Network ingress: internal (no public ALB)
- ALB routing: ``least_outstanding_requests`` (better tail-latency than round-robin)
- WebSocket connection timeout: 1860s (31 minutes — accommodates long-lived chat streams)
- Startup initialization timeout: 360s (6 minutes — generous for warm-up)
- Multiple SQS queue workers: SHWorkers, Standard, Rovo, LongRun
- Redis caches: provisioning + module state (2 clusters)
- CloudGuardian profiling enabled

This descriptor is what Spinnaker reads to provision the service in each environment.

``service/testing/arch`` :sup:`(inferred)`
============================================

Architecture-test module. Likely contains ArchUnit assertions enforcing the api/spi/impl rules described in :ref:`arch-overview` programmatically (so violations fail the test suite, not just the build).

Not directly verified.

Patterns specific to the service tier
======================================

1. **No business logic in controllers.** Controllers like ``ChatV1Controller`` are thin — they validate inputs, resolve tenant context, and delegate to platform-tier ``AssistanceClient`` services.

2. **Pass-through headers.** Multiple controllers use the ``...WithPassThroughHeaders`` pattern to retain the original SLAuth ``X-Slauth-Issuer`` for downstream calls (so the AI Gateway sees the customer's identity, not the service's).

3. **Per-product config scanning.** ``@SpringBootApplication.scanBasePackages`` explicitly enumerates 4 product config packages (csm, jsm, jira, loom). This isolates feature gates: a CSM-only feature gate can't accidentally enable JSM behavior because the bean isn't scanned.

4. **Startup validation.** Multiple ``ApplicationListener`` beans validate critical infrastructure (SQS handler presence, coroutine pool health) at ``ContextRefreshedEvent`` time, before HTTP traffic begins.

5. **Reactor error transparency.** ``Hooks.onErrorDropped`` catches "lost" Reactor errors and logs them with stack traces — turns silent failures into observable ones.

What you would change here
===========================

Service-tier work is typically:

- Adding a new REST endpoint → new method in an existing controller, OR new controller in ``rest/v2/``
- Adding a new product → add ``product.<name>.config`` to ``scanBasePackages``
- Adjusting deployment params → edit ``convo-ai.ad.yml``
- Modifying SQS queue topology → edit descriptor + add new ``@SqsListener`` handler

What you would NOT change here
===============================

- LLM call patterns (those live in ``platform/service``)
- Per-product business logic (lives in ``product/<name>``)
- Authentication mechanism (filters live in ``foundation/utilities/utilities-impl``)
- Feature flag definitions (lives in ``foundation/utilities``)

