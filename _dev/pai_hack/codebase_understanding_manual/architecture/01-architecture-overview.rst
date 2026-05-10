.. _pai-architecture-overview:

================================
Architecture Overview
================================

:Date: 2026-05-04
:Audience: Engineers new to ``proactive-ai-platform``

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Stack
=========

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Concern
     - Choice
   * - Language
     - Kotlin (JVM target 21)
   * - Build
     - Gradle 9.x with Kotlin DSL (``build.gradle.kts``, ``settings.gradle.kts``)
   * - Framework
     - Spring Boot via ``io.atlassian.micros.springboot:7.10.0`` plugin
   * - HTTP
     - Spring MVC (``micros-spring-boot-starter-rest-spring-mvc``)
   * - Auth
     - SLAuth via ``micros-spring-boot-starter-security-slauth-server``
   * - Async
     - Kotlin coroutines (``kotlinx-coroutines-core/slf4j/reactor`` 1.10.2)
   * - Reactive
     - Reactor (mixed with coroutines via ``kotlinx-coroutines-reactor``)
   * - Metrics
     - Micrometer 1.16.4 → SignalFx via Micros observability sidecar
   * - Feature flags
     - Statsig via ``com.atlassian.spring.boot:featuregate-client-starter:10.4.0``
   * - LLM client
     - Stratus SDK over Atlassian AI Gateway (Unified provider)
   * - Persistence
     - Redis (Valkey 7.x, ``cache.t4g.small``, single primary + 1 replica)
   * - Messaging
     - AWS SQS via ``atlassian-spring-boot-sqs-starter``
   * - Test
     - JUnit + ArchUnit + MockK
   * - Quality
     - Detekt + ktlint + SonarQube + JaCoCo
   * - Deployment
     - Atlassian Micros, Spinnaker pipelines, Bitbucket Pipelines CI

2. Repository layout
========================

::

   proactive-ai-platform/
   ├── build.gradle.kts                # Single-module gradle build
   ├── settings.gradle.kts
   ├── service-descriptor.sd.yml       # Micros service descriptor (resources, alarms)
   ├── component-descriptor.yml        # Catalog metadata
   ├── nebulae.yml                     # Nebulae plugin config (staging)
   ├── default-pipelines.spinnaker.yaml
   ├── bitbucket-pipelines.yml         # CI definition
   ├── canary-config.yml               # Canary deployment rules
   ├── checkstyle.xml
   ├── docs/                           # Operational docs (not feature docs)
   │   ├── micros.md, slauth.md, sonarqube.md, …
   ├── streamhub/                      # StreamHub event-schema config
   ├── src/main/kotlin/io/atlassian/micros/proactiveai/
   │   ├── client/                     # HTTP commons + IdGatekeeper
   │   ├── config/                     # Spring beans (web, security, async)
   │   ├── context/                    # Domain context models
   │   ├── exception/                  # REST client exception types
   │   ├── feature/
   │   │   ├── greeting/               # Example/template feature
   │   │   ├── nudge/                  # Throttle decision API
   │   │   └── rovoinsights/           # Async insight generation
   │   ├── featuregate/                # Statsig wrapper
   │   ├── interceptor/                # HTTP interceptor chain
   │   ├── logging/                    # LaasLogger (SLF4J + MDC)
   │   ├── requestcontext/             # Request-scoped values + MDC helpers
   │   ├── service/metric/             # Micrometer-based metric API
   │   ├── sqs/                        # SQS consumer middleware
   │   ├── stratus/                    # AI Gateway / Stratus SDK integration
   │   ├── task/                       # Async-task envelope framework
   │   └── utility/                    # threading / user / tenant helpers
   ├── src/main/resources/
   │   ├── application.yml             # SQS queue env-vars, metrics histogram bins
   │   ├── policies/service/policy.json  # POCO policy
   │   └── logback-spring.xml          # Log appenders
   └── src/test/kotlin/…               # 32 test files mirroring main packages

3. Two runtime topologies, one JAR
=====================================

The single artifact runs in **two distinct modes** based on the ``ATL_MICROS_GROUP``
environment variable that Micros injects into each pod:

.. list-table::
   :header-rows: 1
   :widths: 18 14 28 40

   * - Mode
     - Group
     - Activated by
     - Responsibility
   * - WebServer
     - WebServer
     - Default (no special condition)
     - Serve HTTP traffic on :8080. Run all REST controllers. Submit async tasks to SQS.
   * - SHWorkers
     - SHWorkers
     - ``OnSHWorkerNodeOrLocalCondition``
     - Drain ``analytics_events`` SQS queue (StreamHub events).
   * - LongRun
     - LongRun
     - ``OnLongRunWorkerNodeOrLocalCondition``
     - Drain long-running task queues, e.g. ``rovo-insights-generation-queue``.

The ``OnXxxCondition`` classes (in ``config/``) are Spring conditions that gate
``@Configuration`` classes / ``@Component`` beans on/off depending on the worker
group. Beans destined for the WebServer (controllers) do *not* exist in the bean
graph on a LongRun pod, and vice versa — saving memory and preventing
cross-topology footguns.

4. Spring Boot auto-configuration chain
=========================================

The application starts with ``Application.kt`` and bootstrap follows this wiring order:

.. code-block:: kotlin

    @SpringBootApplication
    class Application {
        // Component scan: io.atlassian.micros.proactiveai.*
    }

    fun main(args: Array<String>) {
        SpringApplication.run(Application::class.java, *args)
    }

Auto-configuration then activates:

1. **WebMvcConfiguration** (unconditional)
   - Registers ``RequestContextInterceptor`` + ``UserContextInterceptor`` via ``addInterceptors()``
   - Sets up coroutine context bridge

2. **MvcSecurityConfig** (unconditional)
   - Enables ``@EnableWebSecurity`` for SLAuth JWT validation

3. **LoggingContextClearingFilter** (unconditional, as ``@Component``)
   - Clears MDC after every request

4. **SqsEventConsumerConfig** (conditional)
   - SHWorker group: activates ``analytics_events`` consumer
   - LongRun group: activates long-running task queues

5. **AIGatewayClientConfiguration** (unconditional)
   - Instantiates Stratus ``UnifiedLlmProvider`` client bean

6. **ThreadConfig** (unconditional)
   - Creates ``InstrumentedDispatcher`` for coroutine work

5. Package dependency flow
===========================

The dependency graph shows which packages depend on which:

.. list-table::
   :header-rows: 1
   :widths: 20 50

   * - Package
     - Depends on (key dependencies)
   * - feature/rovoinsights (16 files, 658 LoC)
     - requestcontext, task, sqs, logging, service/metric, featuregate, stratus, client, context, utility
   * - feature/nudge (4 files, 72 LoC)
     - featuregate, requestcontext, logging, context
   * - service/metric (5 files, 1243 LoC)
     - requestcontext, logging
   * - task (11 files, 649 LoC)
     - sqs, requestcontext, logging
   * - sqs (8 files, 302 LoC)
     - requestcontext, logging, service/metric
   * - stratus (8 files, 587 LoC)
     - client, utility/user, context
   * - interceptor (5 files, 295 LoC)
     - requestcontext, logging, featuregate, context
   * - requestcontext (14 files, 906 LoC)
     - logging, config, context, client/identity, utility
   * - featuregate (8 files, 754 LoC)
     - logging
   * - config (6 files, 208 LoC)
     - logging, requestcontext
   * - logging (6 files, 568 LoC)
     - (no dependencies within PAI; uses SLF4J + Micrometer)
   * - client (7 files, 399 LoC)
     - logging, context, utility
   * - context (9 files, 381 LoC)
     - logging
   * - utility (8 files, 557 LoC)
     - logging

**Invariant**: No downward dependencies. Leaf packages (logging, context, utility)
have minimal dependencies. Feature packages are leaf consumers.

6. The five strategic invariants

These are the rules the codebase enforces — break them at your peril.

I-1. **Every request, sync or async, has an MDC-restorable identity triple.**
   ``request_id`` + ``tenant_id`` + ``account_id`` are populated *before* any
   business logic runs (HTTP: by interceptors; SQS: by message-attribute replay).
   See :doc:`cross-cutting/03-request-context-and-mdc`.

I-2. **No business logic in controllers.**
   Controllers extract DTOs + the authenticated ``User`` and delegate to a
   Spring service. This makes mocking/testing of business logic possible
   without spinning Spring up. (Verified by inspection of all 3 features.)

I-3. **Long-running work goes to SQS.**
   No HTTP request should hold a thread for >1s of business work. Anything
   slower (LLM inference, multi-stage analysis) lives behind ``AsyncTaskService``.
   See :doc:`cross-cutting/06-async-tasks-and-sqs`.

I-4. **All LLM/agent inference goes through Stratus.**
   Direct OpenAI/Anthropic/etc. SDKs are forbidden. Stratus's
   ``UnifiedLlmProvider`` enforces tenant/audience/observability context per call.

I-5. **All feature flags carry a default value.**
   ``FeatureService.checkGate(featureGate, defaultValue)`` makes the default
   mandatory at the call site. Statsig outage → service degrades to defaults,
   not exceptions.

7. Where this codebase is going
==================================

The development trajectory (verified by reading PRs #96-#108) is:

* **Q1 2026** — Bootstrap. Kotlin migration (PR #45-ish), feature service,
  logging.
* **Q2 2026** — Feature push. Async tasks, visibility extension, MCP integration,
  REST controllers, Redis cache.
* **Q3-Q4 2026 (planned)** — Production hardening. Real Rovo Insights
  generation logic ported in. TAP-trait throttling for nudges. GASv3 signal
  ingestion. Quality/latency/throughput uplift.
* **Q1 2027 (planned)** — Scale 1P + 3P proactive interactions.

See :doc:`cross-cutting/01-business-and-technical-goals` for the OKR backing
each milestone, and :doc:`cross-cutting/02-development-history` for the
chronological PR walkthrough.

See also
=========

- **:doc:`00-glossary`** — Definitions of all 80+ terms (Application, Stratus, MetricKey, etc.)
- **:doc:`03-module-catalog`** — Deep dive into each package: responsibilities, public API, test coverage
- **:doc:`cross-cutting/03-request-context-and-mdc`** — How identity context flows through HTTP + async
- **:doc:`cross-cutting/06-async-tasks-and-sqs`** — AsyncTask envelope, SQS consumer, visibility extension
- **:doc:`cross-cutting/07-ai-gateway-and-stratus`** — Stratus SDK integration, MCP server config
- **:doc:`cross-cutting/01-business-and-technical-goals`** — OKRs and team velocity metrics
- **service-descriptor.sd.yml** — Micros service config: alerts, resources, environment variables
- **build.gradle.kts** — Gradle build config: Spring Boot 7.10.0, dependencies, plugin versions
