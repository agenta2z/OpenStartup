.. _overview-multi-axis-matrix:

================================================
Multi-axis matrix — packages × size × purpose
================================================

:Date: 2026-05-04
:Source: ``find /Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform/src/main/kotlin -name '*.kt' -type f``

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. The 16 top-level packages
==============================

Every Kotlin file in the service lives under ``io.atlassian.micros.proactiveai.<package>``. The
table below ranks all 16 packages by file count (descending).

.. list-table::
   :header-rows: 1
   :widths: 20 8 10 12 50

   * - Package
     - Files
     - LoC (≈)
     - Tier
     - One-line purpose
   * - ``requestcontext``
     - 14
     - 906
     - Platform
     - Request-scoped MDC, thread-local state, header extraction
   * - ``feature/rovoinsights``
     - 16
     - 658
     - Feature
     - Async AI-powered insight generation for Jira/Confluence workspaces (see :doc:`/modules/features/rovo-insights`)
   * - ``task``
     - 11
     - 649
     - Platform
     - JSON-envelope async-task framework (web → SQS → worker JVM)
   * - ``context``
     - 9
     - 381
     - Platform
     - Domain models — TenantContext, ProductContext, Experience (7 products)
   * - ``stratus``
     - 8
     - 587
     - Platform
     - AI Gateway SDK: agents, tools, LLM provider, MCP session mgmt (see :doc:`/architecture/cross-cutting/07-ai-gateway-and-stratus`)
   * - ``sqs``
     - 8
     - 302
     - Platform
     - StreamHub event consumption + SQS lifecycle middleware (see :doc:`/architecture/cross-cutting/06-async-tasks-and-sqs`)
   * - ``utility``
     - 8
     - 557
     - Platform
     - Coroutine context propagation, user/tenant utilities, threading (includes ``utility/threading``: 5 files, 454 LoC)
   * - ``featuregate``
     - 8
     - 754
     - Platform
     - Statsig feature flags (AiFeatureGates enum) + dynamic config (see :doc:`/architecture/cross-cutting/04-feature-flags`)
   * - ``client`` (+ ``client/identity``)
     - 7
     - 399
     - Platform
     - HTTP client commons + IdGatekeeper async client integration
   * - ``logging``
     - 6
     - 568
     - Platform
     - SLF4J + MDC wrapper (LaasLogger, infoWithContext extensions) — see :doc:`/architecture/cross-cutting/05-observability-and-metrics`
   * - ``config``
     - 6
     - 208
     - Platform
     - Spring Web/Security/async-executor configuration (WebMvcConfiguration registers interceptor chain)
   * - ``service/metric``
     - 5
     - 1,243
     - Platform
     - Micrometer + SignalFx metrics (count, time, summarize) — see :doc:`/architecture/cross-cutting/05-observability-and-metrics`
   * - ``interceptor``
     - 5
     - 295
     - Platform
     - HTTP request interceptor chain (RequestContextInterceptor → UserContextInterceptor → CommonContextSetter)
   * - ``feature/nudge``
     - 4
     - 72
     - Feature
     - Throttle/suppress decision API for proactive nudges (currently stub)
   * - ``exception``
     - 1
     - 116
     - Platform
     - REST client exception types and log levels
   * - ``feature/greeting``
     - 1
     - 56
     - Feature/Template
     - Minimal example feature controller (``GET /greetings/{name}``)
   * - **TOTAL (main)**
     - **118**
     - **~7,765**
     -
     -

2. Tier definitions
====================

* **Platform** — cross-cutting infrastructure that **all features** depend on. Changes
  here have wide blast radius. Examples: ``requestcontext``, ``task``, ``stratus``,
  ``logging``.
* **Feature** — vertical slices that expose a specific REST API and implement a
  user-facing capability. They depend on the Platform tier but not on each other.
  Examples: ``rovoinsights``, ``nudge``, ``greeting``.
* **Feature/Template** — example feature kept as a working reference for new feature
  authors. Today: ``greeting`` only.

3. Cross-axis: package × dependency direction
================================================

Every Feature package depends transitively on **6+ Platform packages** (verified by scanning ``import`` statements).
Platform packages form a **DAG** with no circular dependencies.

**Dependency flow** (features → platforms):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Feature package
     - Platform packages it consumes (verified by ``import``)
   * - ``feature/rovoinsights`` (16 files, 658 LoC)
     - ``requestcontext``, ``task``, ``sqs``, ``logging``, ``service/metric``, ``featuregate``, ``client/identity``, ``stratus``, ``utility/user``, ``utility/tenant``, ``context``, ``interceptor``
   * - ``feature/nudge`` (4 files, 72 LoC)
     - ``requestcontext``, ``logging``, ``service/metric``, ``utility/user``, ``utility/tenant``, ``context``
   * - ``feature/greeting`` (1 file, 56 LoC)
     - ``service/metric``, ``featuregate``, ``context``

**Platform package depencencies** (verified by scanning imports):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Platform package
     - Its platform dependencies
   * - ``task``
     - ``sqs``, ``requestcontext``, ``logging``
   * - ``sqs``
     - ``requestcontext``, ``logging``, ``service/metric``
   * - ``stratus``
     - ``client``, ``utility/user``, ``context``
   * - ``interceptor``
     - ``requestcontext``, ``logging``, ``featuregate``, ``context``
   * - All others (``requestcontext``, ``logging``, ``service/metric``, etc.)
     - Only ``context`` and utility packages (leaf nodes of DAG)

4. Test coverage by package
==============================

Total: **32 test files** + **4 root-level integration tests** (ArchUnitTest, ExampleTest, HealthCheckIT, RovoInsightsControllerIT).

.. list-table::
   :header-rows: 1
   :widths: 30 12 18 40

   * - Package
     - Test files
     - Ratio (test/main)
     - Status
   * - ``logging``
     - 7
     - 1.17
     - **Strong** — LaasLogger + MDC wrappers heavily tested
   * - ``interceptor``
     - 4
     - 0.80
     - **Strong** — RequestContextInterceptor + UserContextInterceptor coverage
   * - ``task``
     - 3 + 1 root
     - 0.36
     - **Adequate** — async framework tested; some SQS edge cases via root IT
   * - ``client/identity``
     - 2
     - 0.40
     - **Adequate** — IdGatekeeperClient async methods tested
   * - ``service/metric``
     - 2
     - 0.40
     - **Adequate** — MetricsService emit paths tested
   * - ``requestcontext``
     - 2
     - 0.14
     - **Light** — covered indirectly by interceptor + task tests + integration tests
   * - ``feature/nudge``
     - 1
     - 0.25
     - **Light** — NudgeThrottleController under test
   * - ``feature/rovoinsights``
     - 2
     - 0.03
     - **Light** — only RovoInsightsControllerIT exists; see criticality gap below
   * - ``featuregate``
     - 1
     - 0.13
     - **Light** — FeatureService + Statsig defaults tested
   * - ``stratus``
     - 1
     - 0.13
     - **Light** — WeatherTool test agent; AIGatewayService lacks unit tests
   * - ``sqs``
     - 1
     - 0.13
     - **Light** — SqsEventConsumerConfig tested
   * - ``greeting``
     - 1
     - 1.00
     - **Template** — minimal feature, fully tested (1 test file)
   * - **Feature controllers** (REST endpoints)
     - **0 dedicated unit tests**
     - 0.00
     - **CRITICAL GAP** — :doc:`03-criticality-dashboard` §4

5. Reading guide for newcomers
================================

**Start here** — this page tells you what code is where and why it matters.

If you have **15 minutes**:

1. This page (multi-axis matrix) — 5 min — *you're reading it*
2. :doc:`02-architectural-narrative` §1 (system at a glance) — 5 min — *mental model*
3. :doc:`/architecture/cross-cutting/01-business-and-technical-goals` §1 (FY26 OKR) — 5 min — *why PAI exists*

If you have **1 hour** (recommended for all engineers):

1. All of :doc:`02-architectural-narrative` (walking tour) — 30 min
2. :doc:`/architecture/02-request-lifecycle` (sync + async paths) — 20 min
3. :doc:`/modules/features/rovo-insights` (the largest feature) — 10 min

If you have **2+ hours** (deep-dive for platform owners, SREs):

1. All 3 overviews (this one + §2 + §3) — 30 min
2. All cross-cutting chapters in :doc:`/architecture/cross-cutting/index` — 60 min
3. Module deep-dives by relevance:
   - :doc:`/modules/platform/requestcontext` (every request)
   - :doc:`/modules/platform/task` (async framework)
   - :doc:`/modules/platform/stratus` (AI integration)
   - Your task-specific modules (e.g., metrics for observability work)

See also: :doc:`03-criticality-dashboard` (blast radius by package) and :doc:`/architecture/00-glossary` (terminology).
