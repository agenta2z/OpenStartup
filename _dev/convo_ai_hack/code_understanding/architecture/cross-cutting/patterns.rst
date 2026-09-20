.. _cross-cutting-patterns:

==================================================================
Cross-cutting recurring patterns — actionable refactoring guide
==================================================================

:Last updated: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Audience: tech leads, architects, anyone planning structural refactoring
:Companion docs: All 22 feature deep-dives in :ref:`features`

.. contents:: On this page
   :local:
   :depth: 2

Why this page exists
========================

After deep-diving 22 features (Marathon, SAIN, Lumina, AIFC, AIFEATURE,
AgentStudio, Rovo Insights, MCP, Rovo Plugin, Knowledge, Knowledge Gap,
Memory, agent-framework, chat-streaming, Deep Research, JSM, CSM, CSM
Voice, JQL audit, JSM PlanGenerator audit, CSM REST audit), **5
patterns recur across many of them**. This page is the **consolidated
view** that lets you plan refactoring at the codebase level instead of
per-feature.

Each pattern below has:

* Where it appears (verified instances)
* Why it's a problem
* Why it exists (root cause / context)
* What "good" looks like
* Concrete refactoring path (with effort)

Pattern 1 — Legacy/new coexistence (multi-version classes living together)
===========================================================================

**The pattern**: A new (V2/Enhanced/Improved/...) implementation of a
class is added alongside the old one. Both are kept alive — sometimes
one is used in production while the other is experimentally rolled
out via FF, sometimes both are actively used in different code paths.

**Verified instances** (with disposition):

.. list-table::
   :header-rows: 1
   :widths: 32 24 12 32

   * - Where
     - Old vs New
     - Disposition
     - Source verified?
   * - **JQL agents** (rovo-impl)
     - ``EnhancedJqlExecutionSchemaAgent`` (orphan) vs ``JqlExecutionSchemaAgentV1`` (active) vs current
     - **DELETED** Enhanced ✅
     - :ref:`jql-audit` Phase 2
   * - **JSM PlanGenerator** (jsm-impl)
     - ``PlanGenerator`` (V1) vs ``PlanGeneratorV2`` (both active via Factory)
     - **COEXIST** ❌ delete
     - :ref:`audit-jsm-plangenerator`
   * - **NL2 Jql variants** (rovo-impl)
     - ``NL2JqlSchemaAgent`` (1 caller) vs ``JiraNL2JQLSchemaAgent`` (current)
     - **MIGRATE** (deferred to Phase 3)
     - :ref:`jql-audit` Phase 3
   * - **SAIN orchestrators** (rovo-impl)
     - 3 coexist: ``SainStandaloneHybridOrchestratorAgent`` (1908 LoC) + ``SainHybridOrchestratorAgent`` (499) + ``SainLongHorizonOrchestratorAgent`` (699)
     - **COEXIST intentionally** (different complexity tiers)
     - :ref:`feature-sain`
   * - **Pebble templates** (knowledge-gap)
     - V1 + V2 + ``explicit_only`` template variants for memory extraction
     - **COEXIST** (likely A/B test or progressive rollout)
     - :ref:`feature-memory`
   * - **CSM REST controllers** (csm-impl)
     - "v1" + "v2" namespaces
     - **NOT MIGRATION** (separate domains, no pairs)
     - :ref:`audit-csm-rest-v1-v2`
   * - **A2A versioning** (suspected)
     - "legacy" + new agent-to-agent protocols
     - **NEEDS AUDIT**
     - inferred
   * - **AIFC SchemaAgent variants** (aifc)
     - Search vs Validate vs Documentation vs Enhanced
     - **NEEDS AUDIT** — same JQL pattern likely
     - :ref:`feature-aifc`

**Root cause**: Migration work without a hard deadline. The new class
gets created, work moves to the next priority, the old class lingers.
Sometimes the new class genuinely needs the old one as fallback (FF
gating); often it's just "we never got around to deleting".

**Why it's a problem**:

* **Ambiguity for new contributors** — which one should I use?
* **Dead-code risk** — orphan classes accumulate
* **Test maintenance overhead** — 2× test surfaces for "the same" thing
* **Bug surface** — bugs fixed in V2 might not be ported to V1, and vice versa

**What good looks like**:

1. Every "VN" class has a documented sunset criterion (date, FF rollout %, or "delete on next release")
2. Every "Enhanced" / "V2" class has its V1 counterpart's deletion ticket filed
3. CI fails on any class with > N versions still wired
4. Convention: **No "V1" suffix ever**. Just refactor in-place; if the change is breaking, version the API endpoint, not the class name

**Refactoring path**:

* **Step 1** (recurring) — for each "VN" class, file a Jira ticket: "Delete VN-1 of <class>; check FF rollout state"
* **Step 2** — Run the audit pattern (find all callers, check FF state, decide). See :ref:`jql-audit` for the methodology
* **Step 3** — Add a CI lint rule: any class with > 1 production-active version triggers warning

**Estimated codebase-level cleanup effort**: ~2-3 weeks for full sweep
of all instances (most aren't deletable, but each needs investigation).

Pattern 2 — Multi-classifier / multi-router decisions for the same task
==========================================================================

**The pattern**: A single decision (e.g., "what orchestrator path should
this query take?") has multiple classifier/router classes that all
contribute to the answer. Often runs sequentially, sometimes redundantly.

**Verified instances**:

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Decision
     - Classifiers/Routers
     - Where verified
   * - **"Should this be a fast-path query?"**
     - 3 classifiers: ``LuminaClassificationService`` (LUMINA vs STANDARD) + ``SainOrchestrationComplexityClassifier`` (SIMPLE vs COMPLEX) + ``ShouldUseLuminaToAnswerTool`` (mid-flow LLM-decided)
     - :ref:`feature-lumina`
   * - **"What MCP tool to call?"**
     - LLM tool-selection (built-in) + ``ShouldUse*Tool`` MCP tools (declarative routing) + Lumina's classifier
     - :ref:`feature-mcp-system` + :ref:`feature-lumina`
   * - **"What CSM plugin sequence to run?"**
     - Router plugin + Search plugin + Clarify plugin + OOD plugin + Handoff plugin (each is a routing decision)
     - :ref:`feature-csm-platform`
   * - **"What JSM journey to use?"**
     - ``JourneyRecommendationService`` + ``PlanQualityGateService`` + ``BaseComposerAgent`` + ``JsmAiHrOrchestratorAgent`` HR-vs-IT split
     - :ref:`feature-jsm-platform`
   * - **"Which AIFC SchemaAgent variant?"**
     - Likely 4+ classifiers: V1 vs Enhanced vs Search vs Validate vs Documentation
     - :ref:`feature-aifc`

**Root cause**: Each classifier was added incrementally to handle a
specific edge case. Nobody has done the holistic "we have 3 classifiers
for the same decision; can we unify?" review.

**Why it's a problem**:

* **3× LLM cost** if all 3 classifiers fire
* **Inconsistent routing** — what if classifiers disagree?
* **Hard to reason about** — "why did this query route here?" requires reading 3+ code paths
* **Hard to A/B test** — can't isolate classifier effect from full pipeline

**What good looks like**:

1. **One classifier per decision** with explicit fallback chain
2. **Unified routing service** — single source of truth for "what runs"
3. **Routing decision is observable** (logged with reason)
4. **A/B testing via FF on routing classifier**, not via parallel classifiers

**Refactoring path**:

* **Step 1** — Audit: enumerate all classifier/router classes per decision
* **Step 2** — Build a unified ``RoutingService`` with declarative rules
* **Step 3** — Migrate consumers to the new service; remove redundant classifiers
* **Step 4** — Add observability: every routing decision emits a metric with reason

**Estimated effort**: ~1-2 weeks per decision (lots of consumer
updates). Total: 6-8 weeks across all 5 instances.

**Highest priority**: Lumina + SAIN + ShouldUse classifier convergence.
Three classifiers for the same decision is genuinely redundant.

Pattern 3 — Knowledge / search infrastructure duplicated across products
============================================================================

**The pattern**: Multiple modules implement their own
search/knowledge-retrieval infrastructure for the same kind of content
(Confluence pages, Jira issues, etc.).

**Verified instances**:

.. list-table::
   :header-rows: 1
   :widths: 32 22 46

   * - Implementation
     - LoC
     - What it does
   * - **MCP search tools** (rovo-impl)
     - ~5K
     - Confluence + Jira search via MCP tool surface
   * - **CSM Internal Search** (csm-impl)
     - 1,217
     - ``CsmInternalSearchServiceImpl`` — knowledge bases, internal docs
   * - **CSM External Search** (csm-impl)
     - 911
     - ``CsmSearchServiceImpl`` — external sources (Zendesk, web, etc.)
   * - **CSM Search Aggregation** (csm-impl)
     - 802
     - ``SearchAggServiceImpl`` — multi-source aggregation + ranking
   * - **JSM Runbook Search** (jsm-impl)
     - 899
     - ``RunbookSearchServiceImpl`` — runbook-specific search
   * - **JSM Similar Issues** (jsm-impl)
     - 850
     - ``SimilarIssuesKnowledgeSource`` — issue dedup
   * - **AIFEATURE relatedresource** (aifeature-impl)
     - ~5,168
     - Related resource discovery
   * - **Knowledge module** (platform/knowledge)
     - 554
     - Knowledge source contract (NOT search itself)

**Total duplicated effort**: ~15K+ LoC implementing variations of "find
relevant content for a query".

**Root cause**: Each product team built what they needed when they
needed it. The Knowledge module came later as a contract layer but
didn't replace existing implementations.

**Why it's a problem**:

* **15K+ LoC of duplication** — bug fixes go in 1 place, miss the others
* **Inconsistent ranking** — same query can return different rankings in CSM vs JSM
* **No shared cache** — same Confluence page fetched 3× per request when 3 systems search
* **Can't easily add new source types** — each system reimplements

**What good looks like**:

1. **One "ContentSearchService"** in platform/knowledge — handles all sources, all ranking
2. **Per-product extensions via SPI** — JSM adds Runbook scoring, CSM adds Zendesk
3. **Shared embedding/index infrastructure** — vector search per cloudId, reused across consumers
4. **Per-source caching** — Confluence page fetched once, used many times

**Refactoring path**:

* **Step 1** (~1 week) — Audit all search implementations; produce shared API spec
* **Step 2** (~3-4 weeks) — Build unified ``ContentSearchServiceImpl`` in platform/knowledge
* **Step 3** (~2 weeks per consumer × 4 consumers) — Migrate CSM, JSM, AIFEATURE, Rovo
* **Step 4** (~1 week) — Delete duplicated code

**Estimated effort**: ~3-4 months total. Major architectural project.

**Why this is worth it**: Cumulative ROI is high — every future agent
gets consistent search for free; bug-fix cost reduced 4×; embedding
work amortized across consumers.

Pattern 4 — Memory infrastructure duplicated across runtimes
================================================================

**The pattern**: Same — different agent runtimes (Marathon, JSM, ADK,
Conversation, Procedural, Collection) each have their own memory
subsystem.

**Verified instances**:

.. list-table::
   :header-rows: 1
   :widths: 32 16 52

   * - Memory variant
     - LoC
     - What it stores
   * - **Collection memory** (rovo-impl)
     - ~?
     - Long-term per-(user, agent) facts; LLM-extracted from conversations
   * - **Conversation memory** (rovo-impl)
     - ~?
     - Per-turn segments; recent dialog history
   * - **Procedural memory** (rovo-impl)
     - 748
     - ``ProceduralMemoryTPService.kt`` — workflow knowledge / how-to-execute
   * - **JSM Execution memory** (jsm-impl)
     - 693
     - ``ExecutionMemoryService.kt`` — per-(user, journey) execution state
   * - **JSM Journey personalization** (jsm-impl)
     - 542
     - ``JourneyPersonalizationMinion.kt`` — personalization signals
   * - **ADK memory** (rovo-impl)
     - ~?
     - ``AdkMemoryIngestService`` + ``DefaultAdkMemoryEnablementPolicy``
   * - **Marathon memory** (rovo-impl)
     - ~?
     - Marathon-specific kernel cache (58-min TTL) — see :ref:`feature-marathon-orchestrator`

**Total**: ~5-6 memory variants × ~500-1500 LoC each = ~5K-9K LoC of
memory infra.

**Root cause**: Memory needs vary slightly per runtime (per-(user, agent)
vs per-(user, journey) vs per-execution). Rather than build a generic
abstraction, each runtime built its own.

**Why it's a problem**:

* **Per-user privacy/GDPR controls** are spread across 5+ files — easy to miss when implementing right-to-be-forgotten
* **No shared "extract memory from text"** — each variant does its own LLM call
* **Inconsistent retention policies** — Marathon = 58 min, JSM = ?, Collection = ?
* **Cross-runtime memory** is impossible — JSM agent can't see what user told Marathon agent yesterday

**What good looks like**:

1. **One ``MemoryService`` interface** with per-scope variants (UserScope, AgentScope, JourneyScope, ExecutionScope)
2. **Shared LLM-extraction service** — one Pebble template, one classifier
3. **Centralized retention/PII/GDPR policy** — one place to update
4. **Cross-scope queries** — "what does user X want in any context?"

**Refactoring path**:

* **Step 1** (~1 week) — Audit + spec
* **Step 2** (~4-6 weeks) — Build unified ``MemoryService`` with scope adapters
* **Step 3** (~2 weeks per consumer × 5 consumers) — Migrate
* **Step 4** (~1 week) — Delete duplicates + add cross-runtime queries

**Estimated effort**: ~3-4 months total.

**Highest urgency**: GDPR compliance. Right now, "delete all memory for
user X" requires touching 5+ different services. A privacy bug here
is high-cost.

Pattern 5 — Plugin/tool registry duplicated 4 ways
=====================================================

**The pattern**: Multiple plugin/tool registry systems exist that all
solve "how does the agent discover and invoke external capabilities?"

**Verified instances**:

.. list-table::
   :header-rows: 1
   :widths: 32 22 46

   * - Plugin system
     - LoC
     - Owner / scope
   * - **Rovo Plugin System** (rovo-impl)
     - 27,000+
     - Original plugin system; 27 sub-systems (Confluence, Jira, etc.)
   * - **MCP System** (rovo-impl)
     - 41,000+
     - Newer; agentic tools using Model Context Protocol
   * - **Stratus Minions** (agent-framework)
     - ~10K
     - Reusable agent capabilities (Skill, Minion patterns)
   * - **CSM Plugin System** (csm-impl)
     - ~2,700
     - CSM-specific (router, search, clarify, handoff plugins)

**Total**: ~80K+ LoC implementing variations of "agent capability
registry + invocation".

**Root cause**: New systems were added when capabilities couldn't fit
the old system's model. Rovo Plugin came first, then MCP for agentic
tools, then Stratus minions for shared infrastructure, then CSM
plugins for CSM-specific needs.

**Why it's a problem**:

* **Same capability implemented 2-4 times** (e.g., "search Confluence")
* **Per-system tool description templates** — each plugin's "how to call me" doc is owned by the plugin system
* **Inconsistent invocation surfaces** — agents have to know "is this a Rovo plugin or an MCP tool or a Stratus minion?"
* **Rate limiting / quota / per-tenant config** is per-system

**What good looks like**:

1. **One unified ``CapabilityRegistry``** with subtypes (BatchPlugin, RealtimeTool, ResidentMinion)
2. **Standardized invocation surface** for the LLM
3. **Per-tenant config + quota in one place**
4. **Migration path** — old systems become adapters

**Refactoring path**:

* **Step 1** (~2 weeks) — Audit all 4 systems; produce capability spec
* **Step 2** (~6-10 weeks) — Build unified registry + adapters for each old system
* **Step 3** (~2-3 months) — Gradual migration of plugins (each plugin is a small migration; ~250 plugins total)
* **Step 4** (~1 month) — Sunset old systems

**Estimated effort**: ~6-9 months. Largest of all 5 patterns.

**Why this is worth it**: New capabilities can be added once and
exposed to all agents. Per-tenant config is unified.

Cross-pattern observations
=============================

**1. Most patterns have the same root cause**: incremental growth without
a "stop and consolidate" pause. Each pattern = a frozen-in-place layer
of geological history.

**2. Effort is large** but cumulative. Each refactor unlocks the next:

* Memory consolidation makes cross-runtime memory possible
* Search consolidation makes cross-product knowledge sharing possible
* Plugin consolidation makes new agents trivial to build

**3. Refactoring order should be**:

1. **Pattern 1** (legacy/new coexistence) — cleanup, ~2-3 weeks total
2. **Pattern 2** (multi-classifier) — focus on Lumina + SAIN, ~4-6 weeks
3. **Pattern 4** (memory) — GDPR-driven, ~3-4 months
4. **Pattern 3** (search) — biggest LoC win, ~3-4 months
5. **Pattern 5** (plugins) — biggest scope, ~6-9 months

**Total span**: ~1.5-2 years of consolidation effort. Could be
parallelized to ~9-12 months with multiple teams.

**4. Each pattern has a "stop the bleeding" tactical fix**:

* Pattern 1: CI lint — no new V1/V2 patterns
* Pattern 2: ADR requiring new classifier to justify why existing won't work
* Pattern 3: All new search code in platform/knowledge, with ADR
* Pattern 4: All new memory code via single service
* Pattern 5: All new tools registered as MCP (the most modern of the 4)

These tactical fixes prevent further accumulation while strategic
refactoring proceeds.

Quick-reference table — codebase-wide consolidation candidates
==================================================================

.. list-table::
   :header-rows: 1
   :widths: 28 14 14 16 28

   * - Pattern
     - Effort
     - LoC reduction
     - Risk
     - Highest-value win
   * - 1 — Legacy/new coexistence
     - 2-3 wks
     - ~2-5K
     - Low (per audit)
     - Per-instance audits
   * - 2 — Multi-classifier
     - 4-6 wks
     - ~3-5K
     - Medium
     - Lumina + SAIN unification
   * - 3 — Search infra
     - 3-4 mo
     - ~10-15K
     - High
     - Cross-product ranking consistency
   * - 4 — Memory infra
     - 3-4 mo
     - ~3-5K
     - High
     - GDPR compliance
   * - 5 — Plugin/tool registry
     - 6-9 mo
     - ~5-10K
     - Very high
     - Plugin developer DX

**Total potential reduction**: 23-40K LoC removable, ~1.5-2 years effort.


==================================================================
Subsequent audit findings (2026-05-02 follow-up)
==================================================================

After the patterns doc was first written, **two follow-up audits ran**.
Their findings update Pattern 1's instance count and refine the
recommendations.

Updates to Pattern 1 — Legacy/new coexistence
=================================================

**Resolved instances**:

.. list-table::
   :header-rows: 1
   :widths: 32 22 46

   * - Original entry
     - Disposition
     - Resolution doc
   * - JSM PlanGenerator V1 vs V2
     - **FF identified** — ``JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION``
     - :ref:`audit-jsm-plangenerator` (updated)
   * - AIFC SchemaAgent variants
     - **CLAIM REFUTED** — no AIFC-prefixed SchemaAgents exist
     - :ref:`audit-refuted-pattern-claims`
   * - A2A versioning (suspected)
     - **CLAIM REFUTED** — single non-versioned implementation
     - :ref:`audit-refuted-pattern-claims`

**Updated Pattern 1 instance count**: **6 verified instances** (was 8).

JSM PlanGenerator now has a clear deletion path:

* **Today**: Both V1 + V2 active; V1 is default; V2 progressively
  rolling out via ``JSM_PLANNER_V2_MULTI_STAGE_GENERATION``
* **When V2 reaches 100%**: Execute V1 deletion (~500 LoC removable,
  ~2 days effort) following the JQL Phase 2 pattern
* **Observable rollout signal**: Compare
  ``LlmUsageTrackingIds.JSM_PLAN_GENERATOR_V2`` vs
  ``LlmUsageTrackingIds.JSM_PLAN_GENERATOR`` traffic ratio in metrics

Updates to Pattern 2 — Multi-classifier
==========================================

A **detailed design proposal** for unifying Lumina + SAIN +
ShouldUseLuminaToAnswerTool has been written:
:ref:`design-routing-service`

**Summary**:

* Estimated effort: ~4-6 weeks
* Estimated savings: 30-50% routing LLM cost; 200-400ms p50 latency
* Phase 0 quick-win (unify just Lumina + SAIN) = ~1 week, immediate value
* Full implementation is a 6-phase rollout with FF-gated A/B testing

The design proposes:

1. New ``modules/platform/routing/`` (api/spi/impl)
2. Single ``RoutingService.route()`` entry point
3. Pluggable ``RoutingStrategy`` SPI with cost-ordered execution
4. Existing classifiers become strategies (no breaking changes)
5. ``ShouldUseLuminaToAnswerTool`` MCP tool deleted (no longer needed)

The patterns themselves are unchanged
=========================================

Patterns 3 (search), 4 (memory), and 5 (plugin) are unchanged. Their
verification depth is described in the original section above.

Recommended order for further audits
=======================================

Based on what we've learned from the 2 refutations + 1 resolution:

1. **Audit Pebble template variants** in memory extraction (Pattern 1
   instance #5) — currently flagged but not deeply audited
2. **Audit AIFC's actual SchemaAgent consumers** (the JQL family in
   rovo-impl) — Phase 4 of JQL audit
3. **Audit per-search-system overlaps** for Pattern 3 priority work
4. **Implement Phase 0 of RoutingService** (Lumina + SAIN unification)

