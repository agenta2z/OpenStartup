.. _overview-criticality-dashboard:

==================================================================
Criticality / blast-radius dashboard
==================================================================

For SRE, on-call, and refactor planning. Classifies modules by **what breaks** if they break,
and **how big the change risk is** for refactoring.

Tier-zero modules (every request, total platform outage if down)
=================================================================

These modules are on the **hot path of every conversation**. A bug here = full platform outage:

.. list-table::
   :header-rows: 1
   :widths: 35 12 25 28

   * - Module
     - Main LoC
     - Failure mode if buggy
     - Best deploy practice
   * - ``service/convo-ai-service``
     - 44,948
     - 5xx on every request
     - Long bake; canary 1% → 5% → 25% → 100%
   * - ``platform/service/service-impl``
     - 68,863
     - LLM calls fail; fail-open semantics depend on AI Gateway
     - Provider-by-provider rollout via Statsig
   * - ``platform/conversation/conversation-impl``
     - 13,624
     - History persistence broken; chat appears to "lose memory"
     - Multi-store dual-write as safety net
   * - ``platform/workflow/workflow-impl``
     - 1,564
     - Agent loops never terminate / loop forever
     - Gate by Statsig flag
   * - ``platform/base/base-api``
     - 13,271
     - Compile-time break in 30+ modules
     - Treat as ABI; never breaking-change without coordination
   * - ``platform/client/client-api`` + ``client-impl``
     - 100K
     - All Atlassian API calls fail
     - Test deeply before deploy

Tier-one modules (per-product or per-feature blast radius)
=============================================================

A bug here = one product affected, but rest of platform stays up:

.. list-table::
   :header-rows: 1
   :widths: 35 12 25 28

   * - Module
     - Main LoC
     - Failure scope
     - Deploy practice
   * - ``product/rovo/rovo-impl``
     - 446,922
     - Rovo down (but Jira/Confluence/JSM AI features keep working)
     - Largest module = highest individual deploy risk
   * - ``product/jsm/jsm-impl``
     - 68,570
     - JSM AI features down
     - Per-tenant rollout via Statsig
   * - ``product/csm/csm-impl``
     - 62,796
     - CSM AI features down
     - Same
   * - ``product/aifeature/aifeature-impl``
     - 59,375
     - Whiteboard/editor/content AI down (NOT chat)
     - Per-feature rollout
   * - ``product/confluence/confluence-impl``
     - 27,262
     - Confluence-specific AI features down
     - Same
   * - ``product/agentstudio/agentstudio-impl``
     - 15,443
     - Agent publishing UI broken (existing agents keep running)
     - Lower urgency rollback
   * - ``product/jira/jira-impl``
     - 8,974
     - Jira issue suggestion / breakdown broken
     - Per-feature rollout

Tier-two modules (degraded but not catastrophic)
==================================================

A bug here = a specific feature degrades; users see worse experience but core chat works:

* ``platform/evaluation/evaluation-impl`` — batch evaluation jobs fail (no user-facing impact unless running an eval)
* ``platform/knowledge-gap/knowledge-gap-impl`` — knowledge-gap suggestions stop working
* ``platform/sandbox/sandbox-impl`` — code-execution agents lose sandbox access (fall back to error responses)
* ``platform/agent-version/agent-version-impl`` — can't publish new agent versions (existing keep working)
* ``product/loom/loom-impl`` — Loom transcripts not indexed
* All ``contrib/*`` — TAP / A2A / JQL services degraded

Tier-three modules (offline / batch / no chat impact)
========================================================

A bug here = no impact to live chat. Most -api modules; some background workers:

* All ``-api`` and ``-spi`` modules — compile-time only (no runtime behavior)
* ``service/convo-ai-service-descriptor`` — deployment-time only
* ``foundation/testing/arch`` and ``service/testing/arch`` — test-time only
* ``product/rovo/marathon-stubs-publisher`` — CLI utility for stubs

Refactor risk ranking
=======================

Scoring: how risky is a non-trivial refactor in each module?

.. list-table::
   :header-rows: 1
   :widths: 35 12 53

   * - Module
     - Risk
     - Why
   * - ``platform/service/service-impl``
     - 🔴 EXTREME
     - 7 god-classes >1K LoC; 6 LLM providers; central to every request; 1.7× test coverage helps but doesn't eliminate
   * - ``product/rovo/rovo-impl``
     - 🔴 EXTREME
     - 447K LoC; "platform-within-product" duplication of platform-tier concerns; large API surface
   * - ``platform/client/client-api``
     - 🔴 HIGH
     - Likely generated DTOs — can break unexpectedly if regen + transient hand-edits exist
   * - ``service/convo-ai-service``
     - 🔴 HIGH
     - Bootstrap layer; many concerns mixed; tenant-context refactor would be especially risky
   * - ``platform/conversation/conversation-impl``
     - 🟡 MEDIUM
     - Layered persistence makes it relatively safe; multi-store pattern adds complexity
   * - ``platform/sandbox/sandbox-impl``
     - 🟡 MEDIUM
     - 1,311-line god-class but well-isolated
   * - ``platform/workflow/workflow-impl``
     - 🟡 MEDIUM
     - 1,222-line god-class but small module + critical path = test rigor
   * - ``platform/evaluation/evaluation-impl``
     - 🟢 LOW
     - Two-phase model is sound; 2.6× test coverage; not on hot path
   * - ``foundation/utilities/utilities-impl``
     - 🟢 LOW
     - 2.2× test coverage; well-bounded utilities
   * - All ``-api`` modules
     - 🟢 LOW (per-module)
     - But 🔴 HIGH if you change a contract (transitive blast radius)

Test coverage as a safety-net signal
======================================

Test/main ratio is a rough proxy for "how confident can I be about this module".

**Best-covered modules (>2× ratio)**:

* ``foundation/context/context-impl`` — 3.9× (the smallest impl module also has the deepest tests)
* ``foundation/capabilities/capabilities-impl`` — 3.0× (capability checking is security-critical)
* ``platform/evaluation/evaluation-impl`` — 2.6×
* ``product/agentstudio/agentstudio-impl`` — 2.4×
* ``foundation/utilities/utilities-impl`` — 2.2×

**Concerning coverage (<1.0× ratio on critical modules)**:

* ``platform/agent-version/agent-version-impl`` — 933 main / 2,506 test — 2.7× ratio is fine
* ``platform/workflow/workflow-impl`` — 1,564 main / 4,960 test — 3.2× ratio is fine
* ``platform/client/client-api`` — 45,005 main / 1,547 test — **0.034× ratio** — but expected (DTOs aren't unit-tested; tested via integration tests in callers)

The pattern is healthy: critical impl modules have high ratios; API-only modules have low ratios (they have no logic to test).

What to look at first as a new SRE
======================================

Recommended on-boarding read order:

1. **``service/convo-ai-service/rest/v1/``** — the entry points (~2,765 LoC, 18 files)
2. **``platform/service/service-impl/llm/AIGatewayClientServiceImpl.kt``** — central LLM client (3,087 LoC)
3. **``platform/workflow/workflow-impl/SimpleLoopWorkflowExecutorImpl.kt``** — agent loop (1,222 LoC)
4. **``service/convo-ai-service/domain/tenant/``** — tenant context
5. **``platform/conversation/conversation-impl/ConversationManagerImpl.kt``** — conversation lifecycle
6. **``service/convo-ai-service/service/sqs/queue/``** — async background work

Then for each product you operate, the corresponding ``product/<product>/<product>-impl/`` module.

What to NOT touch unless you really know
============================================

* ``platform/foundation/ers-impl`` — backwards-compat with existing data
* ``platform/agent-version/agent-version-impl/AgentVersionDataCompressor.kt`` — compression format compat
* ``platform/sandbox/sandbox-impl/AtlassianSandboxEndpointProvider.kt`` — provisioning state machine
* ``platform/conversation/conversation-impl/ConversationHistoryLargeComponentsHandler.kt`` — historical document boundary handling

