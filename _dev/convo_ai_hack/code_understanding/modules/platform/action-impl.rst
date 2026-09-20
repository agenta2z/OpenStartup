.. _mod-action-impl:

==============================================
``platform/action/action-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/action/action-impl``
:Size: ~461 source lines :sup:`(verified)`

Concrete implementation of action loading + service. Thin runtime; most logic delegates to the loader.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Role
   * - ``ActionConfigLoader.kt``
     - 72
     - Loads action configs from sources
   * - ``ActionConfigServiceImpl.kt``
     - 16
     - Service facade (delegates to loader)

Key Spring components
=======================

* ``class ActionConfigLoader`` — reads and validates action configs
* ``class ActionConfigServiceImpl`` — implements ``ActionConfigService``

Notable findings
==================

* **Service is 16 lines** — almost a pure delegate to the loader. The interesting work is in the loader.
* Module is small (461 LoC) — most action-runtime intelligence lives elsewhere (likely in workflow + tool-registry impl).

