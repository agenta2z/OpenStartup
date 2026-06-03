============================================================
JSM PlanGenerator V2 — Rollout State Investigation
============================================================

This is a follow-up to the JSM PlanGenerator audit (which identified
the FF gate ``JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION``
as the V1↔V2 toggle). This investigation attempts to determine the
**current rollout percentage** so we can plan when V1 can be safely
deleted.

Goal
======

Determine: what % of JSM traffic is currently using V2?

* If V2 = 100%: V1 can be deleted (~500 LoC); FF can be retired.
* If V2 = 50-99%: hold off on deletion; help drive rollout to 100%.
* If V2 = 0-49%: V2 is not production-default yet; investigate why.

Methodology + findings (sandbox-only, NOT runtime)
====================================================

Search 1 — local Splunk dashboards
---------------------------------------

.. code-block:: bash

   $ grep -rln "JSM_PLAN_GENERATOR\|jsm_planner_v2" \
       operations/splunk 2>/dev/null

**Result**: 0 matches.

The local Splunk dashboard inventory contains only:

.. code-block:: text

   operations/splunk/dashboards/convo_ai_agent_permissions.xml

No JSM-specific Splunk panels exist locally. Either:

* JSM has dashboards stored in **a separate location** (Atlassian
  Splunk Cloud, not committed to repo)
* JSM uses a different observability stack (SignalFX, Honeycomb)
* The metric is too new — not yet wired into a dashboard

Search 2 — local Terraform dashboards
---------------------------------------

.. code-block:: bash

   $ grep -rln "JSM_PLAN_GENERATOR\|jsm_planner_v2" \
       operations/terraform 2>/dev/null

**Result**: 0 matches.

The Terraform dashboards directory exists at
``operations/terraform/modules/dashboards`` but doesn't reference
either metric.

Search 3 — Statsig configuration files
-----------------------------------------

.. code-block:: bash

   $ find . -name '*statsig*.json' -o -name '*rollout*.json' \
       2>/dev/null | grep -v build

**Result**: 0 matches.

Statsig FF state is **not stored in the repo** — it's stored in the
Statsig platform (https://console.statsig.com). Cannot determine V2
rollout state from sandbox.

Search 4 — Code-side default value of FF
-------------------------------------------

The code at ``PlannerMinion.kt:237-241``:

.. code-block:: kotlin

   val planGeneratorProvider = rolloutService
       .controlledByLimitedContext(JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION)
       .replacingSuspend { planGeneratorFactory.getPlanGenerator() }     // V1
       .with { planGeneratorFactory.getPlanGeneratorV2() }                // V2
       .value

**Code-side default**: V1 (``replacingSuspend`` is the fallback when
FF returns false).

This is the **only verifiable fact** about rollout state from the
sandbox: when Statsig is unreachable / cloudId is unmapped /
gate is unconfigured, V1 is used.

Required information to determine rollout (cannot get from sandbox)
======================================================================

To verify V2 rollout state, the operator needs:

* **Statsig console access**: Search for gate
  ``jsm_planner_v2_multi_stage_generation``
* **SignalFX/Splunk dashboard**: Plot
  ``LlmUsageTrackingIds.JSM_PLAN_GENERATOR_V2`` count vs
  ``JSM_PLAN_GENERATOR`` count over time
* **Helmsman/Switcheroo**: Check FF rollout config for the gate

Suggested SignalFlow query (for SignalFX):

.. code-block:: text

   v1_count = data('atlassian.convoai.llm.invocations.count',
                   filter=filter('usage_tracking_id', 'JSM_PLAN_GENERATOR'))
              .sum().publish(label='V1')

   v2_count = data('atlassian.convoai.llm.invocations.count',
                   filter=filter('usage_tracking_id', 'JSM_PLAN_GENERATOR_V2'))
              .sum().publish(label='V2')

   v2_pct = (v2_count / (v1_count + v2_count) * 100)
            .publish(label='V2 percentage')

Suggested Splunk query:

.. code-block:: text

   index=convoai source="micros-sv-conversational-ai-platform-*"
   "JSM_PLAN_GENERATOR" OR "JSM_PLAN_GENERATOR_V2"
   | rex field=_raw "usage_tracking_id=(?<tid>[A-Z_]+)"
   | timechart count by tid

Honest assessment
====================

**Decision: PUNT — operator must complete this investigation**

The sandbox cannot determine rollout state. Action items for operator:

#. **Open the Statsig console**, find ``jsm_planner_v2_multi_stage_generation``
#. **Note the rollout percentage** + cohort scope (cloudId, segment, etc.)
#. **Run the SignalFlow query above** for last 30 days
#. **Decide**: Can we delete V1?

Result: append outcome to ``jsm-plangenerator-audit.rst``.

What we DID accomplish
========================

* ✅ Confirmed FF name + key match via grep (``JsmFeatureFlags.kt:242``)
* ✅ Confirmed code-side default is V1 (``replacingSuspend`` fallback)
* ✅ Confirmed both V1 and V2 metrics exist (``PlanGenerator.kt:124``,
  ``PlanGeneratorV2.kt:412,433,459``)
* ✅ Provided SignalFlow + Splunk queries the operator can run
* ❌ Could NOT determine V2 % from sandbox — requires external systems

This is the **honest reality** of FF rollout investigation from
sandbox: code changes (FF references, metric definitions) are
verifiable, but rollout state lives in external systems (Statsig +
observability) that require auth.
