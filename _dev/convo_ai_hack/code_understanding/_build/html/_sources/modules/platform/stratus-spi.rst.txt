.. _mod-stratus-spi:

==============================================
``platform/stratus-contracts/stratus-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/stratus-contracts/stratus-spi``
:Size: ~1,045 source lines :sup:`(verified)`

SPI-side of the Stratus integration — pluggable event/subscription extensions.

Notable findings
==================

* Smaller than the API (1,045 vs 1,542) — typical when the API exposes data shapes but the SPI is just extension hooks.

