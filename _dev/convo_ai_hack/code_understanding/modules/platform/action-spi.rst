.. _mod-action-spi:

==============================================
``platform/action/action-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/action/action-spi``
:Size: ~13 source lines :sup:`(verified)`

A single SPI interface for **pluggable action config providers**. The smallest meaningful module in the platform tier.

Single contract :sup:`(verified)`
====================================

* ``interface ActionConfigProvider`` (13 lines)

Notable findings
==================

* The minimalism is intentional — by isolating only the provider extension point as SPI (not the runtime service), the rest of the platform doesn't have to consider provider-pluggability.
* Actions can therefore be registered from multiple sources (built-in YAML, dynamic Statsig, external services) without touching ``action-impl``.

