.. _pai-modules-platform:

================
Platform layers
================

Cross-cutting infrastructure used by every feature. Ordered by blast radius
and request-lifecycle position.

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Module
     - Priority
     - Description
   * - :doc:`requestcontext`
     - P0
     - Request-scoped values, MDC API, lifecycle setup/teardown
   * - :doc:`interceptor`
     - P0
     - HTTP interceptor chain (request context + user extraction + cleanup)
   * - :doc:`stratus`
     - P0
     - AI Gateway client (Stratus SDK wrapper, MCP tool discovery)
   * - :doc:`featuregate`
     - P1
     - Statsig feature flag wrapper (gates, experiments, dynamic config)
   * - :doc:`logging`
     - P1
     - LaasLogger (SLF4J + MDC wrapper, UGC handling)
   * - :doc:`service-metric`
     - P1
     - Micrometer-based metrics API (auto-tagged from MDC)
   * - :doc:`task`
     - P1
     - Async-task envelope framework (SQS-based, JSON-polymorphic)
   * - :doc:`sqs`
     - P1
     - StreamHub event consumer + shared consumer middleware
   * - :doc:`client`
     - P2
     - HTTP client commons + IdGatekeeper user-enrichment
   * - :doc:`context`
     - P2
     - Tenant / Product / Experience domain models
   * - :doc:`utility`
     - P2
     - Threading (coroutine monitors), user abstraction, TCS integration
   * - :doc:`config`
     - P0
     - Spring MVC bootstrap: interceptor registration, async ``ThreadPoolTaskExecutor``,
       worker-group ``Condition`` classes, environment enum, security whitelist (208 LoC)

.. toctree::
   :maxdepth: 1

   requestcontext
   interceptor
   stratus
   featuregate
   logging
   service-metric
   task
   sqs
   client
   context
   utility
   config
