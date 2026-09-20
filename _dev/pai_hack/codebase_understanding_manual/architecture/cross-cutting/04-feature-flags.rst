.. _pai-feature-flags:

============================================================================
Feature Flags (Statsig)
============================================================================

:Date: 2026-05-04

PAI gates every new behavior behind a Statsig flag. The wrapper layer is in
``featuregate/``.

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. The 3 things you can ask Statsig
======================================

1. **Boolean gate** — ``checkGate(featureGate, defaultValue)``: is this user/tenant in the cohort?
2. **Dynamic config** — ``getStringConfigValue(...)`` / ``getIntConfigValue(...)``: tunable parameter.
3. **Experiment** — ``getExperiment(...)``: A/B/n bucket assignment.

All three accept a **default value at the call site** (Invariant I-5) so a
Statsig outage degrades gracefully.

2. The 2 context modes
========================

* ``checkGateWithLimitedContext()`` — call this in interceptor [1] code. Has
  account_id + hostname only.
* ``checkGate()`` — call this from controllers + below. Has full
  account_id + tenant_id + org_id + hostname.

If you call full-context ``checkGate()`` before the controller runs
``setTenant()``, Statsig won't have the tenant fields and the cohort decision
will be wrong. **Don't call gates from interceptor [1] body except via the
limited variant.**

3. Concrete gate enums
=========================

* ``AiFeatureGates`` — gates for the AI features (rovoinsights, nudge,
  conversation-starter, …). Each gate has a ``statsigKey: String``.
* ``PermanentFeatureGates`` — gates that are **never** intended to be removed
  (kill-switches, regional toggles).

When you add a new gate, register it as an enum value in the appropriate
holder. The compile-time type system prevents typos in Statsig keys.

4. Evaluation tracking
=========================

``FeatureFlagEvaluationTracker`` (a request-scoped value) records every gate
that was evaluated in this request. Used for analytics events ("which flags
shaped this user's experience?") — not for billing.

5. Statsig user/group context
================================

``FeatureFlagContextService`` builds the ``StatsigUser`` Statsig SDK requires:

* ``userID`` = SLAuth account_id
* ``customIDs`` = ``{tenant_id: ..., org_id: ...}``
* ``custom`` = ``{hostname: ..., environment: prod/staging/dev}``
* ``email`` = from ``UserImpl`` if available

Cohorts in the Statsig UI can target on any of these fields.

6. Where to find the wrapper
==============================

See :doc:`/modules/platform/featuregate` for per-file detail.
