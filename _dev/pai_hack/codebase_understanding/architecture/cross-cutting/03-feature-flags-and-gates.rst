==================================
03 — Feature Flags & Gates
==================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

The proactive-ai-platform uses **Atlassian Switcheroo** (backed by the Statsig
SDK) for runtime feature gating and experimentation.  All gate definitions live
in the ``featuregate/`` package and are evaluated through a single
``FeatureService`` interface so that every call site gets consistent context
propagation, evaluation tracking, and fallback behaviour.

Gate Inventory
--------------

AiFeatureGates (transient / experiment gates)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Enum Constant
     - Statsig Key
     - Purpose
   * - ``TEST_GATE``
     - ``aix_proactive_test_gate``
     - Canary gate used by the ``/greetings`` endpoint to verify the
       feature-flag pipeline end-to-end.
   * - ``FEATURE_FLAG_EVALUATION_LOGGING_ENABLED``
     - ``aix_feature_flag_evaluation_logging_enabled``
     - Controls whether per-request feature-flag evaluation results are
       recorded into the ``FeatureFlagEvaluationTracker`` (request-scoped
       store).  Used to limit observability overhead to opted-in tenants.

PermanentFeatureGates (long-lived operational gates)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Enum Constant
     - Statsig Key
     - Purpose
   * - ``ENABLE_UGC_LOGGING``
     - ``proactive_ai_enable_ugc_logging``
     - Guards the ``WithUGCLogger`` path inside ``LaasLogger.withUGC()``.
       When the gate is **on** for the current tenant, log statements that
       may contain user-generated content are emitted to the ``unsafe``
       privacy-environment suffix; when **off**, a ``NoopLogger`` silently
       discards them.

Core Abstractions
-----------------

FeatureGate interface
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   interface FeatureGate {
       val statsigKey: String
   }

Every gate enum (``AiFeatureGates``, ``PermanentFeatureGates``) implements this
interface, allowing call sites to reference gates polymorphically.

FeatureService interface
^^^^^^^^^^^^^^^^^^^^^^^^

The primary evaluation API exposes the following methods:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Semantics
   * - ``checkGate(gate, default)``
     - Full-context evaluation.  Requires ``tenantId`` to be present in the
       request-scoped context; logs a warning if missing.
   * - ``checkHelloOnlyGate(gate, default)``
     - Evaluates only when the current tenant is the Hello dogfood site
       (cloud-id ``a436116f-…``).  Returns ``defaultValue`` for all other
       tenants.
   * - ``checkGateWithLimitedContext(gate, default)``
     - Early-request or async evaluation path.  Does **not** require
       ``tenantId``; percent-rollout and dogfood targeting are unavailable.
   * - ``getExperiment(gate)``
     - Returns a ``DynamicConfig`` with exposure logging.
   * - ``getDynamicConfigWithoutExperimentExposureLogging(gate)``
     - Returns a ``DynamicConfig`` **without** recording exposure.
   * - ``getStringConfigValue`` / ``getIntConfigValue``
     - Convenience extractors that read the ``"value"`` key from the config.
   * - ``isInternalSite(cloudId)``
     - Static check against ``INTERNAL_SITE_ID_SET`` (currently only Hello).

FeatureFlagContextService
^^^^^^^^^^^^^^^^^^^^^^^^^

Manages the per-request Switcheroo context that is passed into every gate
evaluation:

1. ``setFromRequest(request)`` — called by ``CommonContextSetterImpl`` during
   interceptor setup; extracts SLAUTH principal, ``X-Forwarded-Host``, and
   account-id from the servlet request.
2. ``addTenantContext(tenantContext)`` — enriches the context with ``tenantId``,
   ``orgId``, ``experienceId``, and ``channelId`` once tenant hydration
   completes.
3. ``getFeatureGateUser(gate, contextType, randomizationId?)`` — builds the
   ``FeatureGateUser`` Statsig payload, choosing between ``FULL`` and
   ``LIMITED_CONTEXT`` modes.

All context values are stored in ``FeatureFlagScopedData``, a
``RequestScopedValue`` that participates in the request-scoped-values
lifecycle (see ``RequestScopedValuesInitter``).

Evaluation Flow
---------------

.. code-block:: text

   ┌──────────────┐      ┌───────────────────────┐
   │  Call site    │─────▶│  FeatureServiceImpl    │
   └──────────────┘      │  .checkGate()          │
                         └───────┬───────────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │ FeatureFlagContextService  │
                    │ .getFeatureGateUser()      │
                    │ (builds FeatureGateUser    │
                    │  from request-scoped data) │
                    └────────────┬──────────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │ FeatureGatesService (SDK)  │
                    │ .checkGate(user, key)      │
                    └────────────┬──────────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │ recordGateCheck()          │
                    │ → FeatureFlagEvaluation    │
                    │   Tracker (if logging on)  │
                    └───────────────────────────┘

1. The caller invokes one of the ``FeatureService`` methods.
2. ``FeatureServiceImpl`` asks ``FeatureFlagContextServiceImpl`` to build a
   ``FeatureGateUser`` containing identifiers, custom attributes (tenant,
   org, hostname), and the randomization id.
3. The Atlassian ``FeatureGatesService`` (Switcheroo Statsig SDK) evaluates
   the gate rule.
4. On success the result is recorded via ``FeatureFlagEvaluationTracker``
   (gated behind ``FEATURE_FLAG_EVALUATION_LOGGING_ENABLED``).
5. On SDK exception the ``defaultValue`` is returned and a structured
   warning is logged.

Context Propagation
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Propagation Boundary
     - Mechanism
   * - HTTP request → interceptors
     - ``RequestContextInterceptor`` →
       ``CommonContextSetterImpl.setRequest()`` →
       ``FeatureFlagContextService.setFromRequest``
   * - Tenant hydration
     - ``CommonContextSetter.setTenant()`` →
       ``FeatureFlagContextService.addTenantContext()``
   * - Async (SQS workers)
     - No automatic propagation. Workers use
       ``checkGateWithLimitedContext()`` or
       ``tenantContextManagerFeatureGateCheck()``
       with explicit ``tenantId``/``orgId`` args.

Evaluation Tracking
-------------------

``FeatureFlagEvaluationTracker`` is a ``RequestScopedValueOwner`` that
maintains a thread-safe list of ``FeatureFlagEvaluation`` sealed-class
instances:

- ``GateCheck(flagName, result: Boolean)``
- ``Experiment(flagName, result: Map<String, Any>)``

Recording is **opt-in**: ``FeatureServiceImpl.isLoggingEnabled()`` checks the
``FEATURE_FLAG_EVALUATION_LOGGING_ENABLED`` gate once per request and caches
the result in ``FeatureFlagEvaluationTrackerData.loggingEnabled``.

Switcheroo Integration
----------------------

- **SDK**: ``com.atlassian.statsig.featuregate.client.service.FeatureGatesService``
- **Sidecar**: TAP sidecar deployed as a compose service on port 8083
  (``service-descriptor.sd.yml``).
- **Shutdown**: ``FeatureServiceImpl`` registers a ``@PreDestroy`` hook that
  calls ``featureGatesService.close()`` to flush pending exposure events.
- **Dashboard links**: Gate definitions reference Switcheroo URLs (e.g.
  ``https://switcheroo.atlassian.com/ui/gates/…``) in source comments.
