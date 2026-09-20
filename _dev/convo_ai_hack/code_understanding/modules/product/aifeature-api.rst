.. _mod-aifeature-api:

==============================================
``product/aifeature/aifeature-api``
==============================================

:Tier: product
:Path: ``modules/product/aifeature/aifeature-api``
:Size: ~14,658 source lines :sup:`(verified)` — *second-largest product module*
:Importance: Tier 1 — broad cross-feature surface

API for Atlassian's "AI features" — non-conversational AI capabilities (whiteboard AI, editor AI, content suggestions, summaries).

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Concept
   * - ``AiFeature.kt``
     - 492
     - Feature registry
   * - ``WhiteboardAITeammateResponse.kt``
     - 455
     - Whiteboard response model
   * - ``EditorAiFeatureService.kt``
     - 425
     - Editor AI service
   * - ``SimplePluginWorkflowImpl.kt``
     - 355
     - Plugin workflow

Notable findings
==================

* **Broad surface** — covers whiteboard, editor, content, summaries; data models are large because each surface has rich response schemas.
* **Heavy data classes** — response objects are domain-rich, not just text wrappers.
* Distinct from "conversational" Rovo flow — AI features are typically one-shot / synchronous.

