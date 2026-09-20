==============================================
Module: ``featuregate`` — Feature Flag Service
==============================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Wraps the **Statsig** feature-flag SDK behind service interfaces, providing:

* Gate checks (boolean feature flags).
* Experiment parameter reads (A/B tests).
* Dynamic config values (string, int).
* Per-request evaluation context (cloud-id, org-id, user-id).
* Evaluation tracking for analytics.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``AiFeatureGates.kt``
     - 9
     - Enum: AI-specific gate definitions
   * - ``FeatureFlagContextService.kt``
     - 26
     - Interface: per-request flag context management
   * - ``FeatureFlagEvaluationTracker.kt``
     - 81
     - ``@Component`` — records gate/experiment evaluations per request
   * - ``FeatureGate.kt``
     - 11
     - Interface: ``statsigKey`` property
   * - ``FeatureService.kt``
     - 114
     - Interface: gate checks, experiments, dynamic config
   * - ``PermanentFeatureGates.kt``
     - 7
     - Enum: permanent/stable gate definitions
   * - ``internal/FeatureFlagContextServiceImpl.kt``
     - 245
     - ``@Component`` — builds Statsig ``FeatureGateUser`` from request
   * - ``internal/FeatureServiceImpl.kt``
     - 261
     - ``@Component @Primary`` — Statsig-backed implementation

**Total: 8 files, ~754 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``FeatureGate`` — marker with ``val statsigKey: String``.  Implemented by
  enum entries to define gate names.

* ``FeatureFlagContextService`` — per-request lifecycle:

  - ``addTenantContext(TenantContext): SetContextUndo``
  - ``setFromRequest(HttpServletRequest)``
  - ``getFeatureGateUser(cloudId, orgId?, userAccountId?): FeatureGateUser``

* ``FeatureService`` — evaluation API:

  - ``checkGate(gate: FeatureGate): Boolean``
  - ``checkGate(gate: FeatureGate, user: FeatureGateUser): Boolean``
  - ``checkHelloOnlyGate(gate: FeatureGate): Boolean``
  - ``checkHelloOnlyGate(gate: FeatureGate, user: FeatureGateUser): Boolean``
  - ``checkGateWithLimitedContext(gate: FeatureGate): Boolean``
  - ``checkGateWithLimitedContext(gate: FeatureGate, user: FeatureGateUser): Boolean``
  - ``getExperiment(name: String, user: FeatureGateUser): DynamicConfig``
  - ``getDynamicConfigWithoutExperimentExposureLogging(name, user): DynamicConfig``
  - ``getStringConfigValue(name, paramKey): String?``
  - ``getStringConfigValue(name, paramKey, user): String?``
  - ``getStringConfigValueWithoutExposureLogging(name, paramKey): String?``
  - ``getStringConfigValueWithoutExposureLogging(name, paramKey, user): String?``
  - ``getIntConfigValue(name, paramKey): Int?``
  - ``getIntConfigValue(name, paramKey, user): Int?``
  - ``isInternalSite(): Boolean``

Enums
-----

* ``AiFeatureGates`` — implements ``FeatureGate``:

  - ``TEST_GATE`` — test/development gate.
  - ``FEATURE_FLAG_EVALUATION_LOGGING_ENABLED`` — controls verbose flag-eval
    logging.

* ``PermanentFeatureGates`` — implements ``FeatureGate``:

  - ``ENABLE_UGC_LOGGING`` — gates user-generated-content logging.

* ``FeatureFlagContextContextType`` — ``TENANT``, ``REQUEST`` — indicates
  the source of flag-evaluation context.

Classes
-------

* ``FeatureFlagEvaluationTracker`` (``@Component``) — tracks per-request
  flag evaluations as ``RequestScopedValueOwner``:

  - Sealed class ``FeatureFlagEvaluation``:

    - ``GateCheck(gateName, result: Boolean)``
    - ``Experiment(experimentName, config: DynamicConfig)``

  - ``recordGateCheck(gateName, result)``
  - ``recordExperiment(experimentName, config)``
  - ``getAllEvaluations(): List<FeatureFlagEvaluation>``
  - ``getTrackerData(): FeatureFlagEvaluationTrackerData``

  Implements ``RequestScopedValueOwner<FeatureFlagEvaluationTrackerData>``
  with key ``FEATURE_FLAG_EVALUATION_TRACKER``.

* ``FeatureFlagContextServiceImpl`` (``@Component``) — builds
  ``FeatureGateUser`` objects:

  - Extracts cloud-id, org-id, user account-id from request or
    ``TenantContext``.
  - Maintains ``FeatureFlagScopedData`` in request scope via
    ``RequestScopedValueOwner`` pattern.
  - ``addTenantContext`` returns ``FeatureFlagAddTenantContextUndo`` for
    stack-based revert.

* ``FeatureServiceImpl`` (``@Component``, ``@Primary``) — delegates to
  Statsig SDK:

  - Wraps ``Statsig.checkGate()`` / ``Statsig.getExperiment()`` /
    ``Statsig.getConfig()`` calls.
  - Records evaluations via ``FeatureFlagEvaluationTracker``.
  - Logs evaluations when ``FEATURE_FLAG_EVALUATION_LOGGING_ENABLED`` gate
    is open.
  - ``isInternalSite()`` — checks if current cloud-id is an Atlassian
    internal site.

Data Classes (Internal)
-----------------------

* ``FeatureFlagAddTenantContextUndo`` — implements ``SetContextUndo``.
* ``FeatureFlagScopedData`` — holds ``FeatureGateUser`` for current request.
* ``FeatureFlagEvaluationTrackerData`` — mutable list of evaluations.

Spring Component Annotations
=============================

======================================= ========================
Bean                                     Annotation
======================================= ========================
``FeatureFlagEvaluationTracker``         ``@Component``
``FeatureFlagContextServiceImpl``        ``@Component``
``FeatureServiceImpl``                   ``@Component @Primary``
======================================= ========================

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["RequestContextInterceptor.preHandle()"] --> B["FeatureFlagContextService.setFromRequest"]
       B -->|builds from X-Cloud-Id, X-Org-Id, User-Context| C[FeatureGateUser]
       C -->|stores in RequestScopedValue| D[Request Scope]
       D --> E["Service / Controller code"]
       E -->|featureService.checkGate| F[FeatureServiceImpl]
       F -->|retrieves FeatureGateUser| D
       F --> G["Statsig.checkGate(user, key)"]
       G -->|result| F
       F -->|records eval| H[FeatureFlagEvaluationTracker]
       F -->|returns Boolean| E
       H -->|getAllEvaluations| I[Analytics / Logging]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Property
     - Default
     - Description
   * - ``statsig.secret``
     - ``${STATSIG_SDK_KEY:-}``
     - Statsig server secret key
   * - ``statsig.local-mode``
     - ``false`` (prod/staging), ``true`` (local)
     - When true, all gates default without network calls
   * - ``statsig.micros-environment-type``
     - ``prod`` / ``staging`` / ``local``
     - Passed as environment tier to Statsig

Testing Coverage
================

============================================= ============================
Test class                                     Subjects
============================================= ============================
``FeatureFlagContextServiceImplTest``          Context building, tenant add/undo
============================================= ============================

**Coverage: 1/3 implementation files** directly tested.

**Gaps:**

* ``FeatureServiceImpl`` — no dedicated unit test for gate checks, experiment
  reads, or evaluation tracking.
* ``FeatureFlagEvaluationTracker`` — no test for ``recordGateCheck``,
  ``recordExperiment``, ``getAllEvaluations``.

Dependencies
============

Inbound (consumed by)
---------------------

* ``interceptor`` — ``FeatureFlagContextService.setFromRequest()`` called
  during request bootstrap.
* ``logging`` — ``FeatureService.checkGate(ENABLE_UGC_LOGGING)`` gates UGC
  logger.
* All feature modules — ``FeatureService.checkGate()`` for feature gating.

Outbound (depends on)
---------------------

* Statsig SDK — ``Statsig.checkGate()``, ``Statsig.getExperiment()``,
  ``Statsig.getConfig()``, ``FeatureGateUser``, ``DynamicConfig``.
* ``requestcontext`` — ``RequestScopedValueOwner``, ``RequestScopedValueKey``,
  ``SetContextUndo``.
* ``context`` — ``TenantContext`` for cloud-id, org-id.
* ``logging`` — ``LaasLoggerFactory`` for internal logging.

Open Questions / Ambiguities
=============================

1. ``FeatureServiceImpl`` is ``@Primary`` — implies there may be alternative
   implementations (e.g., for testing).  None are visible in the codebase;
   confirm if test doubles exist elsewhere.
2. ``checkHelloOnlyGate`` vs ``checkGate`` vs ``checkGateWithLimitedContext``
   — three gate-check variants with different context levels; the naming
   convention (``HelloOnly``) is non-obvious — document what "Hello" means
   in this context.
3. ``FeatureFlagEvaluationTracker`` stores evaluations in a mutable list in
   request scope — no thread-safety guarantees if coroutines on multiple
   dispatchers record concurrently.
4. ``AiFeatureGates`` and ``PermanentFeatureGates`` are separate enums —
   no enforcement preventing a gate from being defined in both.
5. ``isInternalSite()`` method has business logic that may belong in a
   separate service rather than the feature-flag layer.
