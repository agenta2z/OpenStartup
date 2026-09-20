.. _mod-utilities-impl:

==============================================
``foundation/utilities/utilities-impl``
==============================================

:Tier: foundation
:Path: ``modules/foundation/utilities/utilities-impl``
:Size: ~8,364 source lines :sup:`(verified)`
:Importance: **Tier 1 — runtime substrate**

The runtime side of foundation utilities. Hosts ``RolloutService`` (Statsig), the IdGatekeeper client, core metrics service, identity caching, Arize OTel config, and Statsig evaluators.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Subsystem
   * - ``featureflag/RolloutServiceImpl.kt``
     - 1,011
     - Feature flags (Statsig)
   * - ``identity/IdGatekeeperClientImpl.kt``
     - 752
     - Identity
   * - ``metrics/CoreMetricsServiceImpl.kt``
     - 628
     - Metrics
   * - ``identity/IdentityPermissionCacheService.kt``
     - 568
     - Identity / cache
   * - ``tracing/ArizeOpenTelemetryConfig.kt``
     - 447
     - Arize tracing
   * - ``featureflag/StatsigEvaluatorImpl.kt``
     - 438
     - Statsig evaluator
   * - ``featureflag/ConsistencyCheckRolloutServiceImpl.kt``
     - 381
     - Rollout consistency

Subsystems
============

1. **RolloutService** — the Statsig-backed feature gate runtime. Evaluates gates against (tenant, user) tuples; emits exposure events.
2. **IdGatekeeper** — identity resolution (account ID → user details).
3. **Identity permission cache** — caches per-(user, resource) permission decisions to avoid repeated identity service calls.
4. **CoreMetricsService** — Micrometer-based metric registration with standard tags.
5. **Arize OTel config** — wires OTel exporter for Arize observability platform.
6. **Statsig evaluator** — the lower-level Statsig SDK wrapper.
7. **Consistency-check RolloutService** — wraps RolloutService to detect inconsistent gate evaluations across requests (debugging tool).

Patterns
==========

1. **Filter classes live here too** — ``HeaderFilter``, ``ExperienceRateLimitFilter`` (per agent investigation; verified earlier).
2. **Spring-bound.** This module exposes Spring beans; -api is Spring-free.
3. **Caches are everywhere.** Identity, permissions, gate evaluations — all cached. Reflects the cost of these lookups in the hot path.

What you would change here
============================

* **Modify Statsig integration** → ``featureflag/RolloutServiceImpl.kt``
* **Add a new metric tag dimension** → ``metrics/CoreMetricsServiceImpl.kt``
* **Add a new request filter** → new file under ``interceptors/``
* **Tune identity cache size/TTL** → ``identity/IdentityPermissionCacheService.kt``

