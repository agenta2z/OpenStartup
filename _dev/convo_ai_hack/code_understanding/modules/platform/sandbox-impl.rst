.. _mod-sandbox-impl:

==============================================
``platform/sandbox/sandbox-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/sandbox/sandbox-impl``
:Size: ~2,037 source lines :sup:`(verified)`

Concrete sandbox endpoint provisioning + bootstrap.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Role
   * - ``AtlassianSandboxEndpointProvider.kt``
     - 1,311
     - Endpoint resolution (god-class)
   * - ``SandboxProxyFactory.kt``
     - 304
     - HTTP-proxy factory
   * - ``SandboxBootstrapValidator.kt``
     - 227
     - Bootstrap-payload validator
   * - ``SandboxBootstrapClasspathResourceFactory.kt``
     - 84
     - Resource loader
   * - ``SandboxBootstrapClientImpl.kt``
     - 81
     - Bootstrap client

Notable findings
==================

* **AtlassianSandboxEndpointProvider is a god-class** — 1,311 lines = 64% of the module. Resolves which sandbox endpoint to use for a given request, handles failover, caching, and error recovery.
* The high concentration in one file likely reflects that endpoint resolution touches many sub-concerns (cache, retry, lifecycle, error mapping) that are hard to split cleanly.

