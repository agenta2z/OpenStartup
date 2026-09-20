.. _mod-contrib-client-impl:

==============================================
``contrib/client/client-impl``
==============================================

:Tier: contrib
:Path: ``modules/contrib/client/client-impl``
:Size: ~1,088 source lines :sup:`(verified)`

Concrete TAP + A2A client implementations.

Top files :sup:`(verified)`
============================

* ``targetingplatform/TapClientImpl.kt``
* ``targetingplatform/TapConfiguration.kt``
* ``targetingplatform/TapRequest.kt``
* ``a2a/A2AClientFactoryImpl.kt``
* ``a2a/A2AClientAdapter.kt``

Notable findings
==================

* TAP has Spring config (``TapConfiguration``) — wires up the HTTP client + endpoint.
* A2A uses a **factory + adapter** pattern (``A2AClientFactoryImpl`` + ``A2AClientAdapter``) — likely a thin wrapper around an upstream A2A SDK.
* Active module — 12 implementations, 1,088 LoC.

