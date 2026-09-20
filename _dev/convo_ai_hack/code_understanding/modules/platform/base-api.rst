.. _mod-base-api:

==============================================
``platform/base/base-api``
==============================================

:Tier: platform
:Path: ``modules/platform/base/base-api``
:Size: ~13,271 source lines :sup:`(verified)`
:Importance: Tier 1 — most-imported platform module

Lowest-common-denominator platform vocabulary. Knowledge-source types, tool integrations, feature flags, logging context — the shared "nouns" platform/* modules use to talk to each other.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Concept
   * - ``KnowledgeSourceType.kt``
     - 691
     - Enum of every supported knowledge source
   * - ``ToolIntegration.kt``
     - 570
     - Tool catalogue model
   * - ``DeprecatedRovoFeatureFlags.kt``
     - 512
     - Legacy Rovo flags (kept for compat)
   * - ``LoggingContext.kt``
     - 478
     - Standard logging fields
   * - ``JsmFeatureFlags.kt``
     - 463
     - JSM-product flags

Key public contracts
======================

* Data classes for ``KnowledgeSourceType``, ``ToolIntegration``, ``LoggingContext``
* Feature-flag enumerations (``DeprecatedRovoFeatureFlags``, ``JsmFeatureFlags``, etc.)
* Cross-product domain types

Notable findings
==================

* **13K LoC of vocabulary.** Suggests significant accumulation of cross-cutting types over time.
* **Per-product feature flags live here.** ``JsmFeatureFlags`` is in platform/base, not in product/jsm. This is a deliberate cross-tier convention so other products + platform code can branch on JSM flags without depending on the JSM module.
* **DeprecatedRovoFeatureFlags** — 512-line file dedicated to legacy flags kept around for backward compat. Worth scheduling a cleanup pass.

