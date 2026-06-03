.. _design-routing-service:

==================================================================
Unified RoutingService — design proposal for Pattern 2 quick-win
==================================================================

:Last updated: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Status: **DESIGN PROPOSAL** — implementation deferred until tech-lead review
:Companion docs: :ref:`cross-cutting-patterns` (Pattern 2), :ref:`feature-lumina`, :ref:`feature-sain`, :ref:`feature-mcp-system`
:Estimated implementation effort: ~4-6 weeks (medium architectural change, low blast radius)

.. contents:: On this page
   :local:
   :depth: 2

Why this design exists
=========================

The :ref:`cross-cutting-patterns` Pattern 2 identified that **the Rovo
codebase has 3+ classifiers all making the SAME routing decision** for
incoming queries:

1. **``LuminaClassificationService``** — pre-orchestration classifier
   (LUMINA vs STANDARD) :ref:`feature-lumina`
2. **``SainOrchestrationComplexityClassifier``** — within-orchestrator
   classifier (SIMPLE vs COMPLEX) :ref:`feature-sain`
3. **``ShouldUseLuminaToAnswerTool``** — mid-orchestration LLM-decided
   tool (the LLM asks itself) :ref:`feature-mcp-system`

These three classifiers **redundantly compute "what should be the path
of execution for this query"** at three different layers. Each adds
LLM cost (~150-300 tokens per call), latency (~200-500ms), and
maintenance burden. Worse, they can DISAGREE — leading to
unpredictable behavior.

This design proposes a **unified RoutingService** that consolidates
all three into a single decision point, with the existing classifiers
becoming **strategy implementations** behind a common interface.

Goals
========

**Functional goals**:

1. **Single source of truth** — one place that decides "what
   orchestrator/path/answer-mode should this query take?"
2. **Pluggable strategies** — classification can use heuristics, LLM
   classification, MCP tool calls, or hybrid
3. **Observable** — every routing decision emits a metric with the
   strategy used + reason + cost
4. **Backward-compatible** — existing classifiers become strategies;
   no consumer breakage during migration

**Non-functional goals**:

1. **No regression in routing accuracy** — A/B-tested per strategy
2. **Lower per-query cost** — ideally fewer LLM classifier calls
3. **Lower per-query latency** — by using the cheapest applicable
   strategy first
4. **Per-tenant configurability** — different tenants can use
   different strategies

Non-goals
============

1. **NOT a replacement for orchestrator selection** in Marathon/SAIN/
   JSM — those decisions stay where they are
2. **NOT a tool router** for MCP — MCP tool selection stays in the
   LLM-driven loop
3. **NOT a per-step decision** — RoutingService runs ONCE per query

The proposed architecture
============================

**Single new module**: ``modules/platform/routing/`` (api/spi/impl)

**Top-level interface** (in ``routing-api``):

.. code-block:: kotlin

   /**
    * Decides routing for an incoming agent query.
    *
    * The result is a structured decision indicating:
    * - What orchestrator/answer-mode should handle this query
    * - What execution strategy was used to decide
    * - Whether the decision is final or further routing may occur
    */
   interface RoutingService {
       suspend fun route(input: RoutingInput): RoutingDecision
   }

   data class RoutingInput(
       val query: String,
       val conversationContext: ConversationContext,
       val userContext: UserContext,
       val agentContext: AgentContext,
       val constraints: RoutingConstraints? = null,  // e.g., timeout, cost cap
   )

   data class RoutingDecision(
       val targetMode: RoutingTarget,           // SAIN_HYBRID | SAIN_LH | LUMINA | MARATHON | DIRECT_ANSWER | etc
       val confidence: Double,                   // 0.0 - 1.0
       val reasoning: String,                    // human-readable explanation
       val strategy: RoutingStrategyId,          // which strategy decided this
       val classifierUsed: ClassifierId?,        // which underlying classifier (if any)
       val costMetadata: RoutingCostMetadata,    // tokens, latency, etc.
   )

   enum class RoutingTarget {
       LUMINA,             // fast-path answer agent
       SAIN_HYBRID,        // SAIN with hybrid orchestration
       SAIN_LONG_HORIZON,  // SAIN long-horizon agent
       MARATHON,           // Python-execution agent
       DIRECT_ANSWER,      // skip orchestration; answer directly
       PASS_THROUGH,       // route to agent's own logic
   }

The strategy pattern
=======================

**``RoutingStrategy``** SPI in ``routing-spi``:

.. code-block:: kotlin

   /**
    * A single strategy for making a routing decision.
    *
    * Strategies are tried in order until one returns a decision.
    * If a strategy returns null, the next is tried.
    */
   interface RoutingStrategy {
       val id: RoutingStrategyId
       val cost: StrategyCost  // CHEAP | MODERATE | EXPENSIVE

       suspend fun decide(input: RoutingInput): RoutingDecision?
   }

   enum class StrategyCost {
       CHEAP,      // < 10ms, no LLM call (heuristics, regex, lookup)
       MODERATE,   // 100-500ms, lightweight classifier (e.g., embedding lookup)
       EXPENSIVE,  // > 500ms, full LLM call
   }

   enum class RoutingStrategyId {
       USER_OVERRIDE,            // user explicitly asked for "long answer" / "quick answer"
       PER_TENANT_CONFIG,        // tenant has hardcoded routing rules (e.g., "always SAIN-LH")
       AGENT_SCOPE_LOOKUP,       // agent's declared capabilities → only certain targets valid
       HEURISTIC_QUERY_LENGTH,   // long queries → SAIN-LH; short → LUMINA
       HEURISTIC_TOOL_REQUIRED,  // query mentions tool keywords → MARATHON
       LUMINA_LLM_CLASSIFIER,    // call LuminaClassificationService
       SAIN_COMPLEXITY_CLASSIFIER, // call SainOrchestrationComplexityClassifier
       FALLBACK_DEFAULT,         // last-resort: default to SAIN_HYBRID
   }

The default strategy chain
=============================

**``DefaultRoutingService``** in ``routing-impl`` runs strategies in
**cost-ordered** sequence — cheap first, expensive last. The first
strategy returning a non-null decision wins.

.. code-block:: kotlin

   class DefaultRoutingService(
       private val strategies: List<RoutingStrategy>,  // ordered by cost
       private val metricsService: MetricsService,
       private val featureGates: RoutingFeatureGates,
   ) : RoutingService {

       override suspend fun route(input: RoutingInput): RoutingDecision {
           val orderedStrategies = strategies
               .sortedBy { it.cost }
               .filter { featureGates.isStrategyEnabled(it.id, input.userContext.cloudId) }

           for (strategy in orderedStrategies) {
               val decision = strategy.decide(input)
               if (decision != null) {
                   metricsService.routingDecisionMade(decision)
                   return decision
               }
           }

           // last-resort default — should never happen if FALLBACK_DEFAULT is enabled
           error("No routing strategy returned a decision for query=${input.query}")
       }
   }

**Cost-ordered execution** is the key insight: most queries can be
routed by CHEAP strategies (user-override, tenant-config, agent-scope,
heuristics). Only ambiguous cases need an LLM classifier. This
**reduces per-query LLM cost** vs the current architecture where
multiple classifiers fire regardless.

The 3 existing classifiers as strategies
============================================

After adoption of RoutingService, the 3 existing classifiers become
strategy implementations:

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Existing classifier
     - Becomes
     - Notes
   * - ``LuminaClassificationService``
     - ``LuminaLlmClassifierStrategy`` (StrategyCost.EXPENSIVE)
     - Wraps the existing service; only fires if cheaper strategies returned null
   * - ``SainOrchestrationComplexityClassifier``
     - ``SainComplexityClassifierStrategy`` (StrategyCost.EXPENSIVE)
     - Wraps the existing classifier; alternative to Lumina
   * - ``ShouldUseLuminaToAnswerTool``
     - **DEPRECATED** — replaced by routing happening upstream
     - The MCP tool can be removed; LLM no longer needs to decide

**Critical**: each strategy's ``decide()`` can return null if it's not
applicable. E.g., ``UserOverrideStrategy`` returns null if the user
didn't explicitly ask for a routing override; the next strategy fires.

Migration path — phased rollout
==================================

**Phase 0 — design + ADR** (~1 week)

1. Tech-lead review of this design
2. ADR documenting the design + migration plan
3. Stakeholder buy-in (Lumina + SAIN + MCP teams)

**Phase 1 — module scaffolding** (~1 week)

1. Create ``modules/platform/routing/`` (api/spi/impl)
2. Define interfaces + data classes (no impl yet)
3. Add to ``settings.gradle.kts``
4. Add CI tests

**Phase 2 — implement default strategies** (~2 weeks)

1. ``UserOverrideStrategy``
2. ``PerTenantConfigStrategy``
3. ``AgentScopeLookupStrategy``
4. ``HeuristicQueryLengthStrategy``
5. ``HeuristicToolRequiredStrategy``
6. ``FallbackDefaultStrategy``

**Phase 3 — wrap existing classifiers as strategies** (~1 week)

1. ``LuminaLlmClassifierStrategy`` — wraps existing
2. ``SainComplexityClassifierStrategy`` — wraps existing
3. Both initially DISABLED via FF (existing classifiers continue to fire)

**Phase 4 — wire RoutingService into entry points** (~1 week)

1. Add ``RoutingService`` injection to:

   * ``RovoChatV2Controller`` (or its V3) — call route() once
   * ``CsmChatV2Controller`` — same
   * Future agent endpoints

2. Pass ``RoutingDecision`` to downstream code (orchestrators ignore
   for now, just observable metrics)

**Phase 5 — A/B test routing** (~2 weeks)

1. Enable RoutingService for 1% of queries (FF-gated)
2. Compare: latency, cost, accuracy vs control
3. Iterate based on metrics
4. Ramp to 10%, 50%, 100% over 1-2 weeks

**Phase 6 — sunset existing redundant calls** (~1 week)

1. Once routing is at 100%, ``LuminaClassificationService.classify()``
   is only called by ``LuminaLlmClassifierStrategy``
2. Direct callers can be removed
3. ``ShouldUseLuminaToAnswerTool`` MCP tool deleted (no longer needed)

**Total**: ~8-10 weeks calendar time, ~4-6 weeks actual engineering effort.

Observable benefits
======================

**Per-query cost reduction**:

* Today: 3 classifiers × 200 tokens each = 600 tokens overhead
* After: 1 classifier × 200 tokens (only if needed) = 200 tokens
* **Estimated savings: 30-50% routing cost per query**

**Per-query latency reduction**:

* Today: classifiers run sequentially, even if one's enough = +500ms
* After: cheap strategies short-circuit = +50ms typical
* **Estimated savings: 200-400ms p50 latency**

**Code reduction**:

* Existing duplicated routing code: ~2-3K LoC
* RoutingService implementation: ~1K LoC
* **Net reduction: ~1-2K LoC**

**Operational benefits**:

* Per-decision metric: ``routing.decision{strategy=...,target=...}``
* Per-tenant routing config — easy A/B testing
* Single source of truth for "why did this query route here?"
* Future routing strategies (e.g., GenAI-based reasoning router) plug
  in without touching consumers

Risks + mitigations
======================

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Risk
     - Mitigation
   * - **Routing accuracy regression** — new logic may route differently
     - A/B test rigorously; ramp gradually; monitor per-tenant accuracy metrics
   * - **Latency regression for unusual queries**
     - Add timeout to ``RoutingService.route()`` (e.g., 1s); fall back to default
   * - **Multi-classifier disagreement during transition**
     - During Phase 3-4, both old and new run in parallel; log disagreements; tune thresholds
   * - **Strategy ordering is wrong**
     - Make ordering configurable per-tenant via FF; default to cost-ordered
   * - **Breaking change for consumers**
     - Phase 4 doesn't change consumer behavior — RoutingDecision is just observed initially
   * - **Memory/perf impact of carrying RoutingDecision in flight**
     - Decision is small (~200 bytes); negligible

Alternative considered: just delete redundant classifiers
==============================================================

**Why not just delete ``ShouldUseLuminaToAnswerTool``?**

That ALONE doesn't fix the problem. Lumina + SAIN classifiers still
fire on every query. The deeper issue is that there's no SINGLE
DECISION POINT — each runtime makes its own routing call.

**Why not just unify Lumina + SAIN classifiers?**

That's a smaller refactor (~1 week) and could be a Phase 0 quick-win.
But it doesn't address the architectural issue: future agents will
add their own classifiers without a unifying contract. RoutingService
prevents this proliferation.

**Recommendation**: Do BOTH. Phase 0 quick-win = unify Lumina + SAIN
into one classifier. Phase 1+ = full RoutingService.

Open design questions
=========================

1. **Should ``RoutingDecision`` include downstream config**? E.g., if
   target is SAIN_HYBRID, should the decision also specify which
   variant (StandaloneHybrid vs Hybrid vs LongHorizon)?

2. **How should ``RoutingService`` interact with existing per-runtime
   classifiers** (e.g., ``SainOrchestrationComplexityClassifier`` is
   inside SAIN, not upstream)? Should we keep within-runtime
   classifiers or pull them all out?

3. **Should the strategy chain be ordered globally** (all strategies in
   one list) or **per-target** (one list per RoutingTarget)?

4. **Should there be a "ROUTING_OPT_OUT" gate** for tenants that prefer
   the old per-runtime routing? Probably yes for safety.

5. **What's the cost-billing model** for routing decisions? Are they
   billed to the user's existing query cost or shown separately?

Recommended next steps
=========================

1. **Walk this design with tech leads** of Lumina, SAIN, and MCP teams
2. **Write an ADR** capturing the decision + tradeoffs
3. **Implement Phase 0 quick-win first** (unify Lumina + SAIN; delete
   ``ShouldUseLuminaToAnswerTool`` MCP tool) to prove value
4. **Decide on full RoutingService rollout** based on quick-win results
5. **File a Jira CTSC epic** with the 6 phases as sub-tickets

