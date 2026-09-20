.. _mod-widget-api:

==============================================
``platform/widget/widget-api``
==============================================

:Tier: platform
:Path: ``modules/platform/widget/widget-api``
:Size: ~316 source lines :sup:`(verified)`

UI widget contracts. Defines the renderable artifacts (cards, charts, forms) that agents can return alongside text.

Top files :sup:`(verified)`
============================

* ``Widget.kt`` — 199 lines (data model + variants)
* ``WidgetService.kt`` — 92 lines (lookup + render contract)
* ``WidgetExceptions.kt`` — 25 lines

Key contracts
==============

* ``data class Widget`` (sealed/variant model)
* ``interface WidgetService``
* Exception types

Notable findings
==================

* **API only, no impl module.** Renders happen client-side; the platform only owns the contract for the widget descriptors.
* Small, focused module — no Spring beans expected.

