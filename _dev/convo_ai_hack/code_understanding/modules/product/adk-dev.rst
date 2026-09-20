.. _mod-adk-dev:

==============================================
``product/adk/adk-dev``
==============================================

:Tier: product
:Path: ``modules/product/adk/adk-dev``
:Size: ~1,182 source lines :sup:`(verified)`

ADK developer tools — CLI + local-dev utilities for testing skills.

Top files :sup:`(verified)`
============================

* ``AdkCliUtils.kt`` — 296 lines
* ``CommandHistory.kt`` — 85 lines
* ``LocalContextBuilder.kt`` — 76 lines
* ``AdkUtils.kt`` — 70 lines

Notable findings
==================

* CLI-centric — supports interactive skill testing without a full Spring boot.
* ``LocalContextBuilder`` — assembles a fake ``TenantContext`` / ``User`` for local runs.
* ``CommandHistory`` — REPL-style history for skill-developer ergonomics.

