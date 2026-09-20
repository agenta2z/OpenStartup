==========================================================
Pebble Memory Templates — Variant Audit (Pattern 1 instance)
==========================================================

This audit closes out **Pattern 1** (legacy/new coexistence) for the
memory subsystem. The other Pattern 1 instances (V1/V2 PlanGenerator,
JQL family, etc.) have been audited separately; this audit covers the
memory-extraction Pebble template family.

Source location
=================

All under ``modules/product/rovo/rovo-impl/src/main/resources/templates/memory/``

Total: **16 memory templates** + 2 in ``long_horizon/`` + 3 in ``agent/``
= **21 memory-related Pebble templates** across the codebase.

The 4 long-term memory variants (Pattern 1 candidates)
========================================================

These 4 templates are the Pattern 1 candidates — all share the same
opening 4 lines, suggesting V2 evolved from V1, with ``explicit_only``
and ``v2_formatting`` as further variants:

.. list-table::
   :header-rows: 1
   :widths: 36 12 38

   * - Template
     - LoC
     - **Verdict**
   * - ``long_term_collection_memory.pebble``
     - ~150
     - **V1, candidate for deletion** (if V2 fully replaces)
   * - ``long_term_collection_memory_v2.pebble``
     - ~180
     - **V2, current production**
   * - ``long_term_collection_memory_explicit_only.pebble``
     - ~110
     - **OPT-IN variant** (different semantics)
   * - ``long_term_memory_v2_formatting.pebble``
     - ~50
     - **V2 helper template** (formatting-only, partial)

Semantic differences (verified by reading top of each)
========================================================

V1 vs V2 (lines 1-7 identical)
---------------------------------

.. code-block:: text

   You are the **Memory Extraction Helper**.
   Your job is to scan the **current chat session** between a user and
   **Rovo** (an AI work-assistant created by Atlassian) and decide
   which facts should be saved to Rovo's long-term memory.

   **Remember:** you only ever see the current session, but whatever
   you write to memory will be available to Rovo in future sessions.
   The extracted memory **must be** understandable without the
   original conversation context.

   You don't extract all the details or information from the conversation.
   Instead, you focus on information that can help Rovo understand the
   user's preference and their work context better and information
   that will reduce the need of further clarifications or
   disambiguation in future interactions.

**Both V1 and V2** are PROACTIVE extraction (the helper auto-decides
which facts to save).

``explicit_only`` variant (line 5+ DIFFERS):
-----------------------------------------------

.. code-block:: text

   You do **not** proactively extract information from the conversation.
   You only save a memory when the user **explicitly asks** Rovo to
   remember or memorize something.

This is **OPT-IN memory extraction** — fundamentally different
semantics from V1/V2. Used for **cohorts/users who turned off
proactive memory** (privacy / tenant preference).

**Verdict for ``explicit_only``: KEEP** — distinct semantic, not a
generation variant.

``v2_formatting`` variant
----------------------------

.. code-block:: text

   {% if domainExpertises is defined and domainExpertises | length > 0 %}
   ### Domain Expertises
   {% for item in domainExpertises %}
   - {{ item }}
   ...

This is **NOT a memory-extraction prompt**. It's a **rendering/formatting
template** for showing memory items in a structured way (Domain
Expertises, Goals & OKRs, etc.).

**Verdict for ``v2_formatting``: KEEP** — purpose differs (rendering
vs extraction).

Caller analysis
=================

Where each template is loaded:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Caller class
     - Templates loaded
   * - ``CollectionMemoryExtractor.kt``
     - V1 + V2 + explicit_only (FF-gated selection)
   * - ``UserLLMContextFormatter.kt``
     - v2_formatting

Therefore: **the V1 vs V2 split is genuine Pattern 1**. The other 2
templates (explicit_only + v2_formatting) are NOT Pattern 1 — they
serve different purposes.

The Pattern 1 audit decision
==============================

**For V1 vs V2 (the only true Pattern 1 instance):**

* Need to find the FF gate in ``CollectionMemoryExtractor.kt``
* Verify V2 rollout state from telemetry/dashboards
* If V2 100%: delete V1, save ~150 LoC of template + simplify caller
* If V2 partial: keep V1 as fallback

**Investigation:**

.. code-block:: bash

   grep -n 'long_term_collection_memory' \
     modules/product/rovo/rovo-impl/.../CollectionMemoryExtractor.kt

(Investigation deferred — same pattern as JSM PlanGenerator V1/V2,
needs Statsig FF rollout state which we cannot query from sandbox.)

Other 17 memory templates
============================

The remaining 17 memory templates each serve **distinct purposes**:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Template
     - Purpose
   * - ``user_insightful_report.pebble``
     - User insightful report rendering (Rovo Insights)
   * - ``tenant_usage_ideal_phrase.pebble``
     - Phrasing helper for tenant-level usage examples
   * - ``collection_memory_resolution.pebble``
     - Memory conflict/duplicate resolution
   * - ``memory_helpfulness_classifier.pebble``
     - LLM judge: was this memory useful?
   * - ``in_session_message_classifier.pebble``
     - Was this message worth remembering during session?
   * - ``oov_keyword_memory.pebble``
     - Out-Of-Vocabulary keyword extraction
   * - ``user_profile_memory.pebble``
     - User profile (long-lived) memory rendering
   * - ``message_segment_classifier.pebble``
     - Message segmentation classification
   * - ``user_profile_plugin_sub_profile_template.pebble``
     - Plugin-specific user sub-profile
   * - ``project_description_clustering.pebble``
     - Project description clustering for memory
   * - ``collection_memory_search_by_intent.pebble``
     - Intent-based memory search
   * - ``long_horizon/long_horizon_user_memory_context.pebble``
     - Memory context for long-horizon orchestrator
   * - ``long_horizon/long_horizon_turn_dependent_user_memory_context.pebble``
     - Per-turn memory context for long-horizon orchestrator
   * - ``agent/orchestrator/context_template_default_with_conversation_memory.pebble``
     - Conversation memory context for orchestrators
   * - ``agent/orchestrator/memory_context_template.pebble``
     - Generic memory context for orchestrators
   * - ``agent/minions/jira_agent_system_template_with_memory.pebble``
     - Jira agent system template with memory injected

Each of these is **distinct in purpose** — NOT Pattern 1 candidates.

Summary
==========

* **Pattern 1 instance count for memory subsystem**: **1 true V1/V2 split**
  (``long_term_collection_memory`` V1 vs V2)
* **3 other variants** (explicit_only, v2_formatting, etc.) are **distinct semantics**, not Pattern 1
* **17 distinct memory templates** for legitimate purposes — not refactor candidates

**Reconciliation with patterns.rst Pattern 1 count**:

* Patterns.rst should claim: **1 memory V1/V2 instance** (not "many")
* Same as JQL family (1 confirmed V1/V2 — JqlExecutionSchemaAgent V1 vs V2)
* Same as JSM PlanGenerator (1 V1/V2 — both alive, FF-gated)

**Total true Pattern 1 instances codebase-wide**: **3** (memory + JQL + JSM Planner).

This is fewer than the 6 originally claimed in patterns.rst — the
remaining 3 turned out to be misframed (refuted in
``refuted-pattern-claims-audit.rst``).
