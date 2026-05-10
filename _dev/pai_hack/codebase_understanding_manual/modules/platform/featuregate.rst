.. _pai-platform-featuregate:

============================================================================
``featuregate`` — Statsig feature flag wrapper
============================================================================

:Date: 2026-05-04
:Files: 8 main / 1 test
:Importance: **P1 — gates every safe rollout**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Provides ``FeatureService`` (boolean gates + dynamic config + experiments) and
the request-context glue (``FeatureFlagContextService``,
``FeatureFlagEvaluationTracker``). All feature-flag evaluation in PAI goes
through this package — never call Statsig SDK directly.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``FeatureGate.kt`` (interface)
     - ~5
     - ``statsigKey: String`` carrier
   * - ``AiFeatureGates.kt`` (enum)
     - ~10
     - AI-specific feature flags
   * - ``PermanentFeatureGates.kt`` (enum)
     - ~8
     - Non-experiment permanent gates
   * - ``FeatureService.kt`` (interface)
     - ~40
     - Full gate/config/experiment API
   * - ``FeatureFlagContextService.kt``
     - ~30
     - Builds Statsig user/group context from request
   * - ``FeatureFlagEvaluationTracker.kt``
     - ~20
     - Tracks evaluated gates per request (for logging/debugging)
   * - ``internal/FeatureServiceImpl.kt``
     - ~60
     - Statsig SDK delegate
   * - ``internal/FeatureFlagContextServiceImpl.kt``
     - ~40
     - Context builder implementation

3. Key classes & interfaces
===============================

``FeatureGate`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   interface FeatureGate {
       val statsigKey: String
   }

Marker interface carried by both gate enums. The ``statsigKey`` maps to the
Statsig console name (e.g. ``"aix_proactive_test_gate"``).

``AiFeatureGates`` (enum)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   enum class AiFeatureGates(override val statsigKey: String) : FeatureGate {
       TEST_GATE("aix_proactive_test_gate"),
       FEATURE_FLAG_EVALUATION_LOGGING_ENABLED("aix_feature_flag_evaluation_logging_enabled"),
   }

New AI feature flags are added here. Each maps to a Statsig gate key.

``PermanentFeatureGates`` (enum)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   enum class PermanentFeatureGates(override val statsigKey: String) : FeatureGate {
       ENABLE_UGC_LOGGING("proactive_ai_enable_ugc_logging"),
   }

Permanent gates that are not experiments — they control infrastructure behaviour
(e.g. whether UGC appears in logs).

``FeatureService`` (interface)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Full gate evaluation API:

.. code-block:: kotlin

   interface FeatureService {
       fun checkGate(featureGate: FeatureGate, defaultValue: Boolean = false): Boolean
       fun checkHelloOnlyGate(featureGate: FeatureGate, defaultValue: Boolean = false): Boolean
       fun checkGateWithLimitedContext(featureGate: FeatureGate, defaultValue: Boolean = false): Boolean
       fun getExperiment(featureGate: FeatureGate): DynamicConfig
       fun getDynamicConfigWithoutExperimentExposureLogging(featureGate: FeatureGate): DynamicConfig
       fun getStringConfigValue(featureGate: FeatureGate, defaultValue: String? = null): String?
       fun getIntConfigValue(featureGate: FeatureGate, defaultValue: Int): Int
       fun isInternalSite(cloudId: String): Boolean
   }

4. The limited vs full context distinction
=============================================

PAI cannot know the tenant_id at the very start of a request (it arrives in
``atl-cloud-id`` header which the controller reads). So the team distinguishes:

* **Limited context** — set by interceptor. Has ``account_id`` from SLAuth and
  hostname. Used by ``checkGateWithLimitedContext()`` for early-request flags.
* **Full context** — set by the controller via ``CommonContextSetter.setTenant()``.
  Adds ``tenant_id`` and ``org_id``. Used by ``checkGate()`` for tenant-scoped flags.

**Anti-pattern:** calling ``checkGate()`` before ``setTenant()`` produces wrong
evaluations. The ``FeatureFlagEvaluationTracker`` logs all evaluated gates per
request to help diagnose ordering issues.

**Invariant (I-5):** ``defaultValue`` should always be ``false`` for safety.
If Statsig is unreachable, PAI falls back to ``false`` (feature off) rather
than accidentally enabling an untested code path.

5. Test coverage
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Test
     - Validates
   * - ``FeatureFlagContextServiceImplTest``
     - Context building from request attributes; limited vs full context

6. Integration patterns
==========================

.. code-block:: text

   FeatureService
   ├── consumed by → every controller (checkGate before business logic)
   ├── consumed by → LaasLogger.withUGC() (PermanentFeatureGates.ENABLE_UGC_LOGGING)
   ├── context from → FeatureFlagContextService (request-scoped Statsig user)
   └── tracked by → FeatureFlagEvaluationTracker (per-request gate log)

7. Design decisions
======================

1. **Interface + enum** — ``FeatureGate`` interface with enum implementations
   gives compile-time safety while allowing multiple gate registries.
2. **Two gate enums** — separates experimental flags (``AiFeatureGates``) from
   permanent infrastructure flags (``PermanentFeatureGates``).
3. **Exposure logging control** — ``getDynamicConfigWithoutExperimentExposureLogging``
   allows reading config without triggering Statsig exposure events (useful for
   config-only reads that shouldn't pollute experiment data).
4. **``isInternalSite()``** — allows PAI to treat Atlassian-internal sites
   differently (e.g. enabling experimental features on dogfood instances).

8. See also
==============

* :doc:`/architecture/cross-cutting/04-feature-flags` — limited-vs-full context,
  evaluation tracking, and the default-value invariant (I-5)
* :doc:`/modules/platform/interceptor` — sets limited context
* :doc:`/modules/platform/logging` — ``LaasLogger.withUGC()`` checks UGC gate
