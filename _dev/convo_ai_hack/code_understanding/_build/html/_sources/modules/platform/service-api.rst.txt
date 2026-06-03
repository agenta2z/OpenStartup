.. _mod-service-api:

==============================================
``platform/service/service-api``
==============================================

:Tier: platform
:Path: ``modules/platform/service/service-api``
:Size: ~1,838 source lines :sup:`(verified)`

Public service contracts that downstream callers use to talk to platform-tier services. The "wire" between product/service tiers and platform-tier ``service-impl`` (which contains the 3,087-line AI Gateway client).

Notable findings
==================

* Moderate size (1.8K LoC) — focused on contracts, not impl.
* See :ref:`mod-service-impl` for the implementation that backs these contracts.
* See :ref:`ai-gateway` for the AI Gateway service-impl deep-dive.

