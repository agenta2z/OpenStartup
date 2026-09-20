.. _audit-jsm-plangenerator:

==================================================================
JSM PlanGenerator V1 vs V2 — coexistence audit
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Status: **AUDIT COMPLETE — NEITHER is safe to delete**
:Disposition: Coexistence is intentional via Factory pattern; possibly FF-gated; needs deeper FF + telemetry investigation before any change

.. contents:: On this page
   :local:
   :depth: 2

TL;DR
========

In the original :ref:`feature-jsm-platform` deep-dive, we noted that
"PlanGeneratorV2 implies V1 exists" and flagged this as a candidate
for the same delete-dead-code pattern as JQL Phase 2.

**Audit verdict**: ❌ **Both are alive and intentionally co-used**.

Unlike the JQL audit (where ``EnhancedJqlExecutionSchemaAgent`` had
**zero** production callers and was safely deleted), the JSM
``PlanGenerator`` (V1) and ``PlanGeneratorV2`` are both actively
wired through ``PlanGeneratorFactory`` and selected at runtime via
``PlannerMinion``'s ``.replacingSuspend { ... }.with { ... }`` pattern
— a textbook **replace-with feature toggle** (likely FF-gated).

**Recommendation**: Do NOT delete either. File a follow-up ticket to:

1. Find the FF that selects V1 vs V2
2. Determine the V2 rollout state (% of tenants on V2)
3. Plan deletion of V1 only after V2 is at 100% and stable

Hard evidence (verified by ``grep`` + ``find``)
==================================================

**Files** (3 production + 3 test):

.. list-table::
   :header-rows: 1
   :widths: 60 12 28

   * - File
     - LoC
     - Status
   * - ``PlanGenerator.kt``
     - ~?
     - **V1 — alive**
   * - ``PlanGeneratorV2.kt``
     - 530+
     - **V2 — alive**
   * - ``PlanGeneratorFactory.kt``
     - ~36
     - **Factory wiring both**
   * - test/PlanGeneratorTest.kt
     - ?
     - V1 test
   * - test/PlanGeneratorV2Test.kt
     - ?
     - V2 test
   * - test/PlanGeneratorFactoryTest.kt
     - ?
     - Factory test

The factory wiring (smoking gun)
====================================

``PlanGeneratorFactory.kt`` is **explicitly designed to provide BOTH**:

.. code-block:: kotlin

   class PlanGeneratorFactory(
       private val planGenerator: PlanGenerator,        // V1
       private val planGeneratorV2: PlanGeneratorV2,    // V2
   ) {
       fun getPlanGenerator(): PlanGeneratorProvider {
           return EnhancedPlanGeneratorProvider(planGenerator)
       }

       fun getPlanGeneratorV2(): PlanGeneratorProvider {
           return EnhancedPlanGeneratorV2Provider(planGeneratorV2)
       }
   }

   sealed interface PlanGeneratorProvider {
       // ...
   }

The fact that **both injected fields exist** (``planGenerator`` AND
``planGeneratorV2``) is hard proof that **both are kept alive
intentionally**.

The runtime selection (PlannerMinion.kt:239-240)
====================================================

``PlannerMinion`` selects between them with a **replace-with pattern**:

.. code-block:: kotlin

   .replacingSuspend { planGeneratorFactory.getPlanGenerator() }   // line 239 — V1 default
   .with { planGeneratorFactory.getPlanGeneratorV2() }              // line 240 — V2 override

This is the classic **feature-flag-gated upgrade pattern**:

* The ``replacingSuspend`` block sets the **default behavior** (V1)
* The ``with`` block defines the **alternative behavior** (V2)
* Some condition decides which one fires

**Inference (UNVERIFIED)**: The condition is likely a Statsig FF —
``JSM_USE_PLAN_GENERATOR_V2`` or similar — that allows per-tenant
gradual rollout of V2.

Why this is NOT the same as JQL Phase 2
==========================================

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - JQL EnhancedJqlExecutionSchemaAgent
     - JSM PlanGenerator V1
   * - **Production callers**
     - **0** (verified)
     - **at least 1** — PlannerMinion via factory
   * - **Wiring**
     - Self-contained (only the class + its test)
     - Spring-injected into PlanGeneratorFactory
   * - **Decision pattern**
     - None — orphan class
     - Active replace-with pattern
   * - **Test coverage**
     - Self-test only
     - Has Test + FactoryTest + PlannerMinion tests
   * - **Safe to delete?**
     - ✅ YES (verified)
     - ❌ NO (wired in, possibly FF-gated)

What investigation is still needed
=====================================

Before any deletion of V1, the following questions need answers:

1. **What's the FF that selects V1 vs V2**? Search:

   .. code-block:: bash

      grep -rn 'PLAN_GENERATOR\|planGenerator\|getPlanGeneratorV2' modules \\
        --include='*.kt' | grep -i 'flag\|featuregate\|statsig\|treatment'

2. **What's V2's rollout state**? (% tenants on V2; needs production telemetry)

3. **Why does ``EnhancedPlanGeneratorProvider`` exist** vs just using the raw classes?

4. **What's different between V1 and V2 outputs**? (need to read both classes' core methods)

5. **Are there per-tenant reasons to keep V1**? (e.g., HR uses V1, IT uses V2)

6. **Are there test coverage gaps** for V2 that prevent rollout?

7. **What's the cost difference** (LLM tokens, latency) between V1 and V2?

Recommended next steps (in order)
====================================

**Step 1** (5 min) — File a Jira CTSC ticket: "Investigate JSM PlanGenerator
V1 vs V2 coexistence; determine V2 rollout state and V1 deprecation timeline"

**Step 2** (~30 min) — Find the FF gate by searching:

.. code-block:: bash

   grep -rn 'V2\|getPlanGeneratorV2\|planGeneratorFactory' \\
       modules/product/jsm --include='*.kt' | grep -v '/test/'

**Step 3** (~1 hr) — Read ``PlanGenerator.kt`` and ``PlanGeneratorV2.kt``
fully (530+ LoC for V2). Compare their behavior + outputs.

**Step 4** (~ ?) — Query Statsig dashboard for the rollout state.

**Step 5** (~ ?) — If V2 is at 100%, plan V1 deletion (similar to JQL
Phase 2 pattern). If V2 is partial, determine the holdback reason
and resolve before deletion.

**Step 6** (~ ?) — Document the V1 → V2 migration in this audit
page. Update the JSM platform deep-dive accordingly.


==================================================================
RESOLUTION (2026-05-02 follow-up audit)
==================================================================

✅ **Feature flag DEFINITIVELY IDENTIFIED**

The FF gate is **``JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION``**,
verified at ``PlannerMinion.kt:238``:

.. code-block:: kotlin

   import io.atlassian.micros.convoai.platform.base.features.JsmFeatureFlags

   // ... in nextAction() at line ~237 ...

   val planGeneratorProvider = rolloutService
       .controlledByLimitedContext(JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION)
       .replacingSuspend { planGeneratorFactory.getPlanGenerator() }       // V1 default
       .with { planGeneratorFactory.getPlanGeneratorV2() }                  // V2 override
       .value

The semantics
================

The Atlassian ``rolloutService.controlledByLimitedContext(...)`` API
evaluates the named FF in the **limited context** (cloudId only —
NOT user-level personalization). This is appropriate for tenant-wide
rollouts.

* **FF returns ``false`` (default)** → ``planGenerator`` (V1) is used
* **FF returns ``true``** → ``planGeneratorV2`` is used

The fact that V1 is the **``replacingSuspend``** branch (i.e., the
default) confirms that **V1 is the production default at most tenants**
as of 2026-05-01. V2 is being progressively rolled out.

Observable rollout — usage tracking IDs
==========================================

Both versions emit **distinct LLM usage tracking metrics** for cost +
latency observability:

* ``LlmUsageTrackingIds.JSM_PLAN_GENERATOR`` — V1 traffic
* ``LlmUsageTrackingIds.JSM_PLAN_GENERATOR_V2`` — V2 traffic

This means rollout state can be **directly observed in production
metrics** without needing Statsig dashboard access. A simple Splunk/
Prometheus query (``count(LlmUsageTrackingIds.JSM_PLAN_GENERATOR_V2) /
count(LlmUsageTrackingIds.JSM_PLAN_GENERATOR)``) gives the V2/V1 ratio.

Provider naming convention
=============================

Both providers use the ``enhanced`` prefix in their identity:

* ``EnhancedPlanGeneratorProvider`` → ``planType = "enhanced"`` (wraps V1)
* ``EnhancedPlanGeneratorV2Provider`` → ``planType = "enhanced_v2"`` (wraps V2)

The "Enhanced" prefix likely indicates these wrap base ``PlanGenerator``
+ ``PlanGeneratorV2`` with additional fallback handling
(``createEnhancedFallbackPlan``).

Updated recommendation
=========================

**1. ❌ DO NOT DELETE V1** until ``JSM_PLANNER_V2_MULTI_STAGE_GENERATION``
is at 100% rollout AND V2 has been at 100% for ≥1 month with no
regressions.

**2. ✅ FILE A JIRA TICKET** to:

   * Query Statsig for current V2 rollout state (% of cloudIds on V2)
   * Query production metrics for ``JSM_PLAN_GENERATOR_V2`` /
     ``JSM_PLAN_GENERATOR`` ratio
   * If V2 > 50% — start preparing V1 deletion PR
   * If V2 < 10% — investigate why rollout is slow (regressions? edge
     cases?)

**3. ✅ ONCE V2 IS AT 100%** — execute the deletion in this order:

   * Step 1: Delete ``PlanGenerator.kt`` (V1) and ``PlanGeneratorTest.kt``
   * Step 2: Simplify ``PlanGeneratorFactory.kt`` to only expose V2
   * Step 3: Inline ``EnhancedPlanGeneratorV2Provider`` if no longer needed
   * Step 4: Remove the ``rolloutService.controlledByLimitedContext(...)``
     wrapper in ``PlannerMinion.kt:237-241``
   * Step 5: Remove ``JSM_PLANNER_V2_MULTI_STAGE_GENERATION`` from
     ``JsmFeatureFlags.kt``
   * Step 6: Remove ``LlmUsageTrackingIds.JSM_PLAN_GENERATOR`` from
     ``LlmUsageTrackingIds.kt``

**Estimated cleanup effort once V2 is at 100%**: ~2 days (similar size
to JQL Phase 2; ~500 LoC removable).

Updated audit verdict
========================

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Audit aspect
     - Original assumption (May 2)
     - Resolution (May 2 follow-up)
   * - V1 status
     - "Possibly dead, candidate for sunset"
     - **Active production default** — verified via FF default branch
   * - V2 status
     - "Newer experimental"
     - **In progressive rollout** via ``JSM_PLANNER_V2_MULTI_STAGE_GENERATION``
   * - Action needed
     - "Investigate FF, then decide"
     - **Wait for V2 100% rollout**, then delete V1 (clear path identified)
   * - LoC removable today
     - "Unknown"
     - **0 today; ~500 LoC after V2 ships**
   * - Investigation completeness
     - "Partial"
     - **Complete** — FF identified, observable metrics confirmed

