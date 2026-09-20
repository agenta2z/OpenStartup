.. _mod-aifeature-impl:

==============================================
``product/aifeature/aifeature-impl``
==============================================

:Tier: product
:Path: ``modules/product/aifeature/aifeature-impl``
:Size: ~59,375 source lines :sup:`(verified)`
:Importance: **Tier 1 — cross-product features**

AiFeature is the **catalog of capabilities every product can invoke** (smart links, comment summary, sprint summary, briefing, suggest issues, similar work items). Despite living under ``product/``, AiFeature is cross-product — any consumer can wire it in.

Top files :sup:`(verified by line-count)`
===========================================

.. list-table::
   :header-rows: 1
   :widths: 65 15 20

   * - File
     - Lines
     - Subsystem
   * - ``aifeature/rest/AiFeaturesController.kt``
     - 2,236
     - REST controller (the entry point)
   * - ``features/editor/EditorAiFeatureServiceImpl.kt``
     - 1,569
     - Editor-AI feature service
   * - ``features/briefing/BriefingScorer.kt``
     - 1,191
     - Briefing scoring
   * - ``features/briefing/BriefingPrompt.kt``
     - 900
     - Briefing prompt builder
   * - ``features/aisuggestionspoc/AiSuggestionsPocServiceImpl.kt``
     - 842
     - AI Suggestions PoC
   * - ``features/similarworkitems/JiraSimilarWorkItemsFeatureServiceImpl.kt``
     - 776
     - Similar work items
   * - ``features/briefing/BriefingScorerV03.kt``
     - 772
     - Briefing scorer v0.3 (newer)

Major features
================

1. **Editor AI** — in-place AI in editors (Confluence, Jira, etc.); rewrite, summarize, etc.
2. **Briefing** — generate executive briefings from work items, comments, activity
3. **Smart links / comment summary / sprint summary / suggest issues** :sup:`(inferred from agent reports)`
4. **Similar work items** — Jira-specific deduplication / related-issue surfacing
5. **AI Suggestions PoC** — proof-of-concept feature for general AI suggestions

The "v0.3 vs original" pattern :sup:`(observed)`
===================================================

``BriefingScorer.kt`` (1191 lines) and ``BriefingScorerV03.kt`` (772 lines) coexist — versioning happens by class suffix. Likely:

* Original ``BriefingScorer`` is the production path
* ``V03`` is a newer variant being A/B tested via feature flag
* Eventually V03 replaces the original

This is a common pattern in this codebase: keep both, gate via Statsig, observe metrics, retire the loser.

Patterns specific to aifeature-impl
=====================================

1. **REST-first.** ``AiFeaturesController.kt`` is the largest file (2236 lines) — many endpoints, all REST. GraphQL is less prominent here.
2. **Templates / prompts in resources.** Most prompt rendering happens via Pebble templates under ``src/main/resources/templates/`` :sup:`(per agent investigation)`.
3. **Cross-product reuse.** AiFeature is consumed by Confluence, Jira, JSM, etc. — each calls AiFeature's REST API or wires the services directly.
4. **A/B testing in code.** ``V03`` suffixes signal active experimentation.

What you would change here
============================

* **Add a new AI feature** → new package under ``features/<name>/`` + controller endpoint
* **Modify briefing scoring** → ``features/briefing/`` (which scorer depends on which gate is on)
* **Add a new editor mutation** → ``features/editor/EditorAiFeatureServiceImpl.kt``
* **Modify a prompt template** → ``src/main/resources/templates/`` :sup:`(inferred)`

