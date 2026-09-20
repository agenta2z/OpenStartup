.. _multi-axis-matrix:

==============================
Multi-Axis Module Matrix
==============================

This matrix provides an at-a-glance comparison of every functional module in
the Proactive AI Service across multiple dimensions: operational tier, code
size, dependency weight, Spring component count, and criticality ranking.

.. note::

   The service contains **15 top-level packages (16 functional modules)**.
   The ``feature`` package houses two distinct functional modules — *Nudge
   Throttle* and *Rovo Insights* — which are tracked separately because they
   have independent lifecycles, SQS queues, and operational profiles.

Tier × Size Matrix
==================

Modules are classified into three tiers based on their operational impact:

* **Tier 1 — Critical Path**: Modules that directly handle inbound requests
  or whose failure causes user-visible impact.
* **Tier 2 — Core Infrastructure**: Shared modules consumed by Tier 1;
  failures degrade but don't fully block the service.
* **Tier 3 — Supporting**: Utilities, configuration, and development-time
  modules with limited blast radius.

.. list-table:: Module Tier × Size Classification
   :header-rows: 1
   :widths: 22 10 10 10 10 10 28

   * - Module
     - Tier
     - Files
     - LoC
     - Controllers
     - Components
     - Purpose
   * - ``requestcontext``
     - 1
     - 14
     - 906
     - 0
     - 5
     - Request-scoped value management and logging context
   * - ``interceptor``
     - 1
     - 5
     - 295
     - 0
     - 4
     - HTTP interceptors for context propagation and auth
   * - ``feature/nudge``
     - 1
     - 5 (est.)
     - 180 (est.)
     - 1
     - 0
     - Nudge throttle API for proactive notifications
   * - ``feature/rovoinsights``
     - 1
     - 15 (est.)
     - 550 (est.)
     - 2
     - 2
     - Rovo Insights generation, SQS consumer, test endpoints
   * - ``greeting``
     - 1
     - 1
     - 56
     - 1
     - 0
     - Health/sample REST endpoint
   * - ``stratus``
     - 1
     - 8
     - 587
     - 1
     - 2
     - AI Gateway client, MCP integration, tool provider
   * - ``sqs``
     - 2
     - 8
     - 370
     - 0
     - 6
     - Analytics event SQS consumers and middleware
   * - ``task``
     - 2
     - 11
     - 649
     - 1
     - 7
     - Async task dispatch, SQS queue registry, visibility extender
   * - ``featuregate``
     - 2
     - 8
     - 754
     - 0
     - 3
     - Feature flag evaluation, context service, tracking
   * - ``service/metric``
     - 2
     - 5
     - 1243
     - 0
     - 2
     - Metrics emission (Micrometer), metric key registry
   * - ``logging``
     - 2
     - 6
     - 568
     - 0
     - 1
     - Structured logging (LaasLogger), UGC-safe logger, intercepted logger
   * - ``context``
     - 2
     - 9
     - 381
     - 0
     - 0
     - Tenant, cloud-id, org-id, platform, AI gateway context models
   * - ``client``
     - 2
     - 7
     - 399
     - 0
     - 2
     - ID Gatekeeper HTTP client (sync + async)
   * - ``config``
     - 3
     - 6
     - 208
     - 0
     - 3
     - MVC security, web config, environment detection
   * - ``exception``
     - 3
     - 1
     - 116
     - 0
     - 0
     - REST client exception hierarchy
   * - ``utility``
     - 3
     - 8
     - 557
     - 0
     - 1
     - TCS client, threading (coroutine monitor, dispatchers), user model

Totals
------

.. list-table:: Aggregate Metrics by Tier
   :header-rows: 1
   :widths: 15 15 15 15

   * - Tier
     - Modules
     - Files
     - LoC (approx.)
   * - Tier 1 — Critical Path
     - 6
     - 48
     - 2,574
   * - Tier 2 — Core Infrastructure
     - 7
     - 54
     - 4,364
   * - Tier 3 — Supporting
     - 3
     - 15
     - 881
   * - **Total**
     - **16**
     - **117**
     - **7,819**

Criticality Rankings
====================

Modules ranked by operational criticality (weighted combination of tier,
inbound traffic exposure, failure blast radius, and dependency fan-in):

.. list-table:: Criticality Ranking
   :header-rows: 1
   :widths: 5 25 15 55

   * - Rank
     - Module
     - Score
     - Rationale
   * - 1
     - ``requestcontext``
     - ★★★★★
     - Every request flows through; failure = total outage
   * - 2
     - ``interceptor``
     - ★★★★★
     - Auth + context propagation; failure = 401/500 on all endpoints
   * - 3
     - ``task``
     - ★★★★☆
     - Async task backbone; failure = all background processing stops
   * - 4
     - ``sqs``
     - ★★★★☆
     - Analytics event pipeline; failure = data loss
   * - 5
     - ``featuregate``
     - ★★★★☆
     - Feature evaluation; failure = incorrect feature exposure
   * - 6
     - ``feature/rovoinsights``
     - ★★★★☆
     - Primary feature surface; failure = Rovo Insights unavailable
   * - 7
     - ``stratus``
     - ★★★☆☆
     - AI Gateway integration; failure = AI features unavailable
   * - 8
     - ``service/metric``
     - ★★★☆☆
     - Observability; failure = blind operations
   * - 9
     - ``logging``
     - ★★★☆☆
     - Structured logging; failure = debugging impaired
   * - 10
     - ``context``
     - ★★★☆☆
     - Tenant models; failure = multi-tenancy broken
   * - 11
     - ``client``
     - ★★★☆☆
     - ID Gatekeeper; failure = identity resolution fails
   * - 12
     - ``feature/nudge``
     - ★★☆☆☆
     - Nudge API; isolated feature scope
   * - 13
     - ``config``
     - ★★☆☆☆
     - Startup-time only; no runtime failure path
   * - 14
     - ``greeting``
     - ★★☆☆☆
     - Health endpoint; low blast radius
   * - 15
     - ``utility``
     - ★★☆☆☆
     - Shared utilities; failure depends on consumer
   * - 16
     - ``exception``
     - ★☆☆☆☆
     - Exception models; purely structural
