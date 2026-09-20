.. _feature-flags:

============================
Feature Flags & Rollout
============================

The platform uses **Statsig** for feature flags, accessed via the ``RolloutService`` abstraction in foundation. Per the codebase pattern observed across multiple modules:

The ``RolloutService`` interface :sup:`(inferred from codebase patterns)`
=========================================================================

**Lives in:** ``modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/featureflag/`` (verified directory)

Likely interface:

.. code-block:: kotlin

   interface RolloutService {
       fun isEnabled(gate: String, tenantContext: TenantContext, user: User): Boolean
       fun getDynamicConfig(name: String, tenantContext: TenantContext): JsonObject
       fun getExperiment(name: String, tenantContext: TenantContext): ExperimentResult
   }

Statsig is configured via the ``statsig-sidecar`` Docker container that runs alongside the main service (visible in the integration-tests sandbox container list).

Patterns
=========

1. **Always pass tenant + user.** Feature gates evaluate against the (tenant, user) tuple. Never call without both — Statsig will use defaults that may not match production behavior.

2. **Per-request caching.** Per the ``responsible-ai-api`` AI-NEW-5 pattern (and likely mirrored here), gate user attributes are cached per-request to avoid re-evaluating the same gate 8-12× per request.

3. **Default-False for safety.** When Statsig is unreachable or the gate is unconfigured, it returns False. Design new gates so False = current/safe behavior.

4. **Local mode in tests.** The integration-tests sandbox uses Statsig in local mode (from container logs: "FeatureGatesClient is configured to use local mode") — gates evaluate against local configuration, not the production Statsig service.

Where gates are evaluated
==========================

Examples observed in code:

- Inside controllers — to gate new endpoints
- Inside ``AIGatewayClientServiceImpl`` — to roll out new providers/models per cohort
- Inside ``AssistanceClient`` — to A/B test routing logic
- Inside agent skill loaders — to gate which skills are available per tenant

What you would change here
===========================

- **Add a new gate** → register in Statsig admin UI; add ``rolloutService.isEnabled("gate_name", ctx, user)`` at call site
- **Roll out a new model** → check existing rollout patterns in ``AIGatewayClientServiceImpl`` (search for ``isEnabled``)

What you would NOT change here
===============================

- Statsig SDK config (lives in service-tier Spring config)
- Default gate fallback semantics (lives in foundation/featureflag/)

