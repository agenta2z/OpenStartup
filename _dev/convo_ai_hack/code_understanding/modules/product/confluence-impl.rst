.. _mod-confluence-impl:

==============================================
``product/confluence/confluence-impl``
==============================================

:Tier: product
:Path: ``modules/product/confluence/confluence-impl``
:Size: ~27,262 source lines :sup:`(verified)`
:Importance: **Tier 1 — content-creation product**

Confluence integration. Hosts the page-creation orchestrator, ADF (Atlassian Document Format) editor minion, infographic generation, header image generation, semantic table tooling.

Top files :sup:`(verified by line-count)`
===========================================

.. list-table::
   :header-rows: 1
   :widths: 65 15 20

   * - File
     - Lines
     - Subsystem
   * - ``product/confluence/infographic/ConfluenceInfographicServiceImpl.kt``
     - 1,502
     - Infographic generation
   * - ``agent/confluence/minion/adfeditor/AdfEditorMinion.kt``
     - 1,449
     - ADF editor agent
   * - ``agent/confluence/orchestrator/ConfluenceCreationOrchestratorAgent.kt``
     - 1,365
     - Page creation orchestrator
   * - ``agent/confluence/minion/pagecreator/converter/HtmlToAdfConverter.kt``
     - 1,208
     - HTML → ADF format converter
   * - ``agent/confluence/minion/contentcreation/TemplateRecommenderService.kt``
     - 1,035
     - Template recommendations
   * - ``product/confluence/headerimage/ConfluenceHeaderImageServiceImpl.kt``
     - 955
     - Header image generation
   * - ``agent/confluence/minion/adfeditor/tools/SemanticTableToolExecutor.kt``
     - 878
     - Semantic table tool

Subsystems
============

1. **Page creation orchestrator** — coordinates the multi-step "create a Confluence page from a prompt" flow (recommend template → generate content → render to ADF → submit).
2. **ADF editor minion** — operates on Atlassian Document Format documents (the JSON format Confluence uses internally).
3. **HTML → ADF converter** — bridges LLM HTML output to Confluence's structured format.
4. **Template recommender** — suggests appropriate Confluence templates given a user goal.
5. **Infographic generation** — renders data-driven infographic blocks.
6. **Header image generation** — generates header images for pages.
7. **Semantic table tool** — manipulates Confluence tables semantically (sort, filter, summarize).

Patterns specific to confluence-impl
======================================

1. **ADF-native.** Output is structured ADF JSON, not raw markdown — preserves Confluence editor fidelity.
2. **Orchestrator + minion pattern.** ``ConfluenceCreationOrchestratorAgent`` coordinates multiple specialized minions.
3. **Format conversion in code.** ``HtmlToAdfConverter`` (1208 lines) handles the impedance mismatch between LLM output (HTML/markdown) and Confluence (ADF).
4. **Image generation as a service.** Header image + infographic each have their own service classes.

What you would change here
============================

* **Add a new ADF mutation** → ``agent/confluence/minion/adfeditor/tools/`` + register tool
* **Modify page-creation flow** → ``ConfluenceCreationOrchestratorAgent.kt``
* **Add a new template-recommendation rule** → ``TemplateRecommenderService.kt``
* **Improve HTML → ADF conversion** → ``HtmlToAdfConverter.kt`` (be careful — many edge cases)

