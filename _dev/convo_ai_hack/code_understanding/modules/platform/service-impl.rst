.. _mod-service-impl:

==================================================================
``platform/service/service-impl`` — multi-LLM + search platform
==================================================================

:Tier: platform
:Path: ``modules/platform/service/service-impl``
:Size: **68,863 main + 117,192 test LoC** :sup:`(verified 2026-05-02)`
:Files: 274 main + 260 test
:Importance: ⭐⭐⭐⭐⭐ Tier 0 — multi-provider LLM gateway + cross-product search infrastructure

.. note::
   The previous catalog reduced this module to "the 3,087-line AIGatewayClientServiceImpl".
   That class is real and important, but it is **4.5% of the module**. The rest is a
   multi-LLM-provider abstraction layer + a cross-product search infrastructure layer
   + per-product service integrations.

The four sub-systems
======================

``service-impl`` is really four things bundled into one Gradle module:

.. list-table::
   :header-rows: 1
   :widths: 30 12 12 46

   * - Sub-system
     - LoC
     - Files
     - What it is
   * - **LLM provider abstraction**
     - **22,251**
     - 71
     - ``llm/`` + ``llm/languagemodelprovider/`` + ``llm/processor/`` + ``llm/toolconverter/`` + ``llm/schema/`` + ``llm/tokencounter/`` + ``llm/teamserve/`` + ``llm/truncator/``
   * - **Cross-product search**
     - **13,889**
     - 35
     - ``search/`` + ``search/providers/`` + ``search/queries/`` + ``search/datasource/`` + ``search/text/`` + ``search/aggregator/``
   * - **Per-product services**
     - **9,373**
     - 31
     - ``jira/`` + ``jsm/`` + ``loom/`` + ``ags/`` + ``ors/``
   * - Specialized services
     - ~23,000
     - ~140
     - ``adf/``, ``ags/domainmappers/``, ``journeybuilder/``, ``avpcharts/``, ``avpdashboards/``, ``entitylinking/``, etc.

LLM provider abstraction (22K LoC)
=====================================

The most architecturally sophisticated sub-system. Provides a **uniform interface across multiple LLM providers**.

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Provider
   * - ``AIGatewayClientServiceImpl.kt``
     - **3,087**
     - The unified gateway client
   * - ``LLMServiceImpl.kt``
     - 1,831
     - Top-level LLM service
   * - ``GenericGeminiLanguageModelProvider.kt``
     - 1,484
     - Generic Gemini provider
   * - ``GeminiLanguageModelProvider.kt``
     - 1,406
     - Gemini-specific provider
   * - ``GcpAnthropicLanguageModelProvider.kt``
     - 1,006
     - Anthropic on GCP
   * - ``GenericGcpAnthropicLanguageModelProvider.kt``
     - 975
     - Generic Anthropic-on-GCP provider
   * - ``AnthropicLanguageModelProvider.kt``
     - 963
     - Anthropic provider (direct)
   * - ``GenericAnthropicLanguageModelProvider.kt``
     - 956
     - Generic Anthropic provider

**Six providers, two flavors each (concrete + Generic-prefixed).** The "Generic" prefix likely indicates
a parameterizable variant supporting multiple model families behind a single interface
(e.g., GenericGeminiLanguageModelProvider supports Gemini 1.5, Gemini 2.0, etc., while
GeminiLanguageModelProvider is hardcoded to one model family).

**Sub-packages of LLM:**

* ``processor/`` (1,894 LoC) — response post-processing (tool call parsing, content extraction)
* ``toolconverter/`` (1,354 LoC) — converts platform tool definitions to provider-specific tool schemas
* ``schema/`` (770 LoC) — JSON schema utilities for tool I/O
* ``tokencounter/`` (733 LoC) — token counting per provider (each provider tokenizes differently)
* ``truncator/`` (262 LoC) — truncates oversized inputs to fit context windows
* ``teamserve/`` (473 LoC) — Teamserve (internal Atlassian model serving) integration

Cross-product search (14K LoC)
================================

A complete search infrastructure. Multiple providers, query DSL, aggregation.

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Role
   * - ``RankingServiceImpl.kt``
     - 1,647
     - Cross-source result ranking
   * - ``InterleaverSearchProvider.kt``
     - 1,201
     - Multi-source result interleaving
   * - ``AggInterleaverSearchQueries.kt``
     - 1,066
     - Query templates
   * - ``SalesforceSearchProvider.kt``
     - 1,014
     - Salesforce search backend
   * - ``ConfluenceSearchProvider.kt``
     - 954
     - Confluence search backend

**Sub-packages of search:**

* ``providers/`` (4,951 LoC) — concrete search providers per data source (Confluence, Salesforce, Interleaver, etc.)
* ``queries/`` (1,668 LoC) — reusable search-query templates (likely AQL/Atlassian Query Language)
* ``datasource/`` (851 LoC) — data-source registration + lifecycle
* ``aggregator/`` (212 LoC) — result aggregation across providers
* ``text/`` (301 LoC) — text-search utilities

Per-product services (9K LoC)
================================

Domain-specific service integrations:

* ``jira/`` (5,345 LoC) — JiraServiceImpl is 2,466 LoC; sprint + issue + workflow sub-services
* ``jsm/`` (987 LoC) — JSM service-desk integration
* ``loom/`` (485 LoC) — Loom video integration
* ``ags/`` (943 + 2,089 domain-mappers LoC) — Atlassian Granular Service (entity store)
* ``ors/`` (1,571 LoC) — likely "ORS" entity resource store (separate from ERS)

Specialized services
======================

A long tail of specialized services worth noting:

* ``adf/`` (1,656 LoC) — Atlassian Document Format processing
* ``journeybuilder/JourneyBuilderServiceImpl.kt`` (1,378 LoC, single file) — user-journey orchestration
* ``avpcharts/`` (467) + ``avpdashboards/`` (403) — Atlassian Visual Platform charts/dashboards
* ``entitylinking/`` (699) — entity linking (e.g., linking text mentions to Jira issues)
* ``aicreditusage/`` (501) — AI usage / credit tracking
* ``auditlog/`` (494) — audit logging
* ``ubpenforcement/`` (375) — UBP (Usage-Based Pricing?) enforcement
* ``responsibleai/`` (316) — responsible-AI policy hooks
* ``followup/`` (260) — follow-up question generation
* ``imagegeneration/gemini/`` (212) — image generation via Gemini
* ``backfill/`` (285) — backfill operations
* ``socratesmetadata/`` (204) — Socrates metadata

What you would change here
============================

* **Add a new LLM provider** → ``llm/languagemodelprovider/`` — implement both concrete + Generic-prefixed variants
* **Add a new search source** → ``search/providers/`` — implement ``SearchProvider`` interface
* **Add a Jira-specific feature** → ``jira/`` (split into ``sprint/``, ``issue/``, ``workflow/`` already)
* **Hook AI usage tracking for a new feature** → ``aicreditusage/``
* **Add an AVP chart/dashboard type** → ``avpcharts/`` or ``avpdashboards/``

What you would NOT change here
================================

* Direct calls to AI Gateway HTTP endpoints (use ``AIGatewayClientServiceImpl`` instead)
* Token counting hand-rolling — use existing ``llm/tokencounter/`` per-provider counters
* Response truncation — use ``llm/truncator/``
* Tool-schema conversion — use ``llm/toolconverter/``

Critical observations
=======================

1. **The "Generic" prefix pattern** for LLM providers is interesting — it suggests the team initially shipped concrete providers (one per model family) then refactored to a generic/parameterized variant. Both still exist; presumably for compatibility.

2. **Multi-LLM-provider architecture is real and significant.** This isn't an "AI Gateway thin client" module. It's a full provider-abstraction layer with provider-specific token counting, tool conversion, response processing, truncation, and schema validation.

3. **Search is its own service.** ``search/`` (14K LoC, 5 file>1000 LoC) is genuinely a multi-source search platform with ranking + interleaving + aggregation. Could plausibly be its own module.

4. **AGS/ORS/ERS coexist.** Three different storage abstractions are referenced (AGS = Atlassian Granular Service, ORS = ?, ERS = Entity Resource Store). Worth investigating overlap.

5. **117K LoC of test code** vs 68K main = **1.7× test/main ratio**. Excellent test coverage culture.

Refactoring opportunities
===========================

* **Extract ``search/`` to its own module** ``platform/search-impl`` — would unbundle two unrelated concerns from one Gradle target.
* **Extract ``llm/languagemodelprovider/`` to its own module** — provider abstractions are reusable beyond convo-ai.
* **Audit the ``GenericXxxProvider`` vs ``XxxProvider`` duplication** — likely opportunities to consolidate.

