.. _mod-rovo-extras-impl:

==============================================
``product/rovo/rovo-extras-impl``
==============================================

:Tier: product
:Path: ``modules/product/rovo/rovo-extras-impl``
:Size: ~20,992 source lines :sup:`(verified)` — *largest single product module*
:Importance: Tier 1 — large, multi-feature

Non-core Rovo features. Includes the avatar generator, evaluation strategy, insights service, and configuration service.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``SvgAvatarGenerator.kt``
     - **1,848**
     - SVG avatar generation
   * - ``RovoAgentEvaluationStrategy.kt``
     - 623
     - Eval orchestration
   * - ``RovoInsightsServiceImpl.kt``
     - 572
     - Usage insights
   * - ``AgentConfigurationServiceImpl.kt``
     - 524
     - Agent config

Notable findings
==================

* **SvgAvatarGenerator at 1,848 lines** is unusual for a product module — agent avatars are SVG-rendered server-side rather than picked from a static set. Likely supports per-agent customization.
* **Insights + evaluation + config in one module** — three non-core but related features grouped together. Could split if they grow further.

