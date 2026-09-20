.. _mod-agent-framework-impl:

==============================================
``product/agent-framework/agent-framework-impl``
==============================================

:Tier: product
:Path: ``modules/product/agent-framework/agent-framework-impl``
:Size: ~10,047 source lines :sup:`(verified)`

Core agent framework — implementations of skills + Stratus minions for cross-product agents.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``AssessChangeRiskSkill.kt``
     - **2,157**
     - Change-risk assessment
   * - ``AdminTroubleshootPermissionsSkill.kt``
     - 725
     - Admin permission troubleshooting
   * - ``TalentMinion.kt``
     - 658
     - Talent / hiring minion
   * - ``SolutionArchitectStratusMinion.kt``
     - 568
     - Architecture-design minion

Notable findings
==================

* **AssessChangeRiskSkill at 2,157 lines** is by far the largest skill in the codebase — assessing change risk apparently involves a lot of decision logic.
* **"Stratus minions"** — agents that act on the Stratus knowledge graph. Distinct from product-tier per-product skills.
* TalentMinion suggests hiring/recruitment workflows.

