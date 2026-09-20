.. _mod-rovo-impl:

==================================================================
``product/rovo/rovo-impl`` — the largest module in the codebase
==================================================================

:Tier: product
:Path: ``modules/product/rovo/rovo-impl``
:Size: **446,922 main + 544,376 test LoC** :sup:`(verified 2026-05-02)`
:Files: 2,215 main + 1,467 test
:Importance: ⭐⭐⭐⭐⭐ Tier 0 — by far the largest module; functionally a "platform-within-product"

.. warning::
   **This module is functionally a second platform layer.** It contains 1.6× more code than
   the entire ``modules/platform/`` tier combined. The "platform vs product" tier separation
   is partially an aspiration here — much of what would architecturally belong in the
   platform tier lives inside ``rovo-impl/agent/`` and ``rovo-impl/product/rovo/``.

The hidden hierarchy
======================

While the Gradle module is named ``rovo-impl``, internally it has two top-level functional sub-trees that
are themselves the size of major systems:

.. list-table::
   :header-rows: 1
   :widths: 30 12 12 46

   * - Sub-tree
     - LoC
     - Files
     - What it is
   * - ``product/rovo/``
     - **264,179**
     - 1,533
     - Per-product Rovo logic — chat, MCP, plugins, actions, deep research, memory
   * - ``agent/``
     - **176,641**
     - 669
     - Agent-orchestration runtime — Marathon, LongHorizon, Hybrid orchestrators + minions
   * - ``platform/``
     - 5,889
     - 8
     - Tiny — mostly gateways into platform-tier services
   * - ``modules/``
     - 213
     - 5
     - Spring config glue

``agent/`` sub-tree (176K LoC, 669 files)
============================================

The orchestration heart of Rovo. Contains the multi-orchestrator architecture:

.. list-table::
   :header-rows: 1
   :widths: 25 12 12 51

   * - Sub-package
     - LoC
     - Files
     - Role
   * - ``orchestrators/``
     - **96,249**
     - 272
     - Marathon, LongHorizon, Hybrid orchestrators — the agent-execution loops
   * - ``minions/``
     - **53,920**
     - 261
     - All concrete skill implementations (Jira, Confluence, JSM, Talent, etc.)
   * - ``playground/``
     - 6,876
     - 45
     - Agent Playground — interactive testing UI backend
   * - ``workflows/``
     - 2,866
     - 13
     - Workflow definitions (multi-step agent flows)
   * - ``dynamic/``, ``adk/``, ``lumina/``
     - ~3,700
     - ~21
     - Dynamic agent loading, ADK runtime, Lumina (specific feature)
   * - ``bitbucket/``, ``jira/``, ``terminal/``
     - ~1,800
     - 8
     - Per-product agent variants
   * - ``filter/``, ``prompt/``, ``scenario/``, ``intermediate/``, ``capacity/``, ``provisioning/``, ``aifc/``
     - ~1,700
     - ~17
     - Cross-cutting concerns (filtering, prompting, scenarios, capacity planning)

**Three orchestrator types** (``orchestrators/``):

* **MarathonOrchestratorAgent** — fan-out parallel orchestrator. Runs multiple specialist sub-agents concurrently and synthesises. Used for complex multi-source queries.
* **LongHorizonOrchestratorAgent** — durable async orchestrator for tasks that take minutes to hours. Persists state, supports resume.
* **HybridOrchestratorAgent** — routes incoming requests to either Marathon (immediate) or LongHorizon (deferred) based on cost/complexity heuristics.

``product/rovo/`` sub-tree (264K LoC, 1,533 files)
======================================================

Per-product features and integrations. **The largest sub-trees**:

.. list-table::
   :header-rows: 1
   :widths: 25 12 12 51

   * - Sub-package
     - LoC
     - Files
     - Role
   * - ``agent/``
     - **68,134**
     - 408
     - Per-agent definitions — agent configs, agent factories, per-agent skills
   * - ``mcp/``
     - **41,304**
     - 201
     - **MCP (Model Context Protocol) integration** — tool servers, MCP transport layer
   * - ``plugin/``
     - 27,804
     - 193
     - Plugin system — extensibility hooks for adding new capabilities
   * - ``chat/``
     - 25,608
     - 63
     - Chat session orchestration — message handling, context assembly
   * - ``action/``
     - 24,507
     - 237
     - Action runtime — concrete action implementations + dispatch
   * - ``rest/``
     - 10,393
     - 62
     - REST controllers exposed to product UIs
   * - ``sain/``
     - 9,268
     - 43
     - "SAIN" subsystem (acronym not documented; likely Search/AI/Inference)
   * - ``deepresearch/``
     - 8,103
     - 30
     - Deep Research feature — long-form research workflows
   * - ``workflow/``
     - 7,544
     - 38
     - Workflow definitions specific to Rovo product
   * - ``memory/``
     - 4,681
     - 33
     - Conversation/agent memory — long-term context retention
   * - ``answergenerator/``
     - 4,565
     - 34
     - Answer generation pipeline
   * - ``scenario/``
     - 3,574
     - 15
     - Scenario testing infrastructure
   * - Smaller sub-packages
     - ~16,000
     - ~250
     - tool, forge, task, eventtrigger, conversation, client, classification, etc.

What you would change here
============================

* **Add a new Rovo product feature** → add a new sub-package under ``product/rovo/``
* **Add a new agent type** → ``agent/orchestrators/`` if it's a new orchestration strategy, or ``agent/minions/`` if it's a new specialist skill
* **Add MCP server integration** → ``product/rovo/mcp/``
* **Add a deep-research workflow variant** → ``product/rovo/deepresearch/``

What you would NOT change here
================================

* AI Gateway invocations → :ref:`mod-service-impl`
* Workflow loop primitives → :ref:`mod-workflow-impl` (but most of Rovo's actual loop logic is duplicated here in ``orchestrators/``)
* Knowledge retrieval → :ref:`mod-knowledge-impl` + ``platform/base-impl`` TurboPuffer
* Cross-cutting platform vocabulary → :ref:`mod-base-api`

Critical observations
=======================

1. **The "platform vs product" boundary is leaky here.** ``rovo-impl/agent/orchestrators/`` (96K LoC) is functionally orchestration infrastructure, but lives in product-tier. Compare to ``platform/workflow/workflow-impl`` (1.5K LoC) which is the "official" platform orchestration. There are likely parallel implementations of similar concerns.

2. **MCP at 41K LoC** is a heavy investment — Model Context Protocol is the strategic tool-integration protocol. The volume here suggests ``product/rovo/mcp/`` may be functioning as the de-facto MCP integration layer for the whole codebase, not just Rovo.

3. **Deep Research (8K LoC)** is its own sub-system — long-form research workflows are first-class.

4. **544K LoC of test code** (vs 446K main) — exceptional 1.2× test/main ratio. The test culture is strong even at this scale.

Refactoring opportunities
===========================

* **Extract ``agent/orchestrators/`` to a new platform-tier module** — would normalize the platform/product boundary.
* **Extract ``product/rovo/mcp/`` to ``platform/mcp-impl``** — MCP is cross-cutting infrastructure, not Rovo-specific.
* **Audit ``platform/`` sub-package (5,889 LoC inside rovo-impl)** — likely cross-cutting code that crept in; should move to actual platform tier.

