.. _mod-sandbox-api:

==============================================
``platform/sandbox/sandbox-api``
==============================================

:Tier: platform
:Path: ``modules/platform/sandbox/sandbox-api``
:Size: ~466 source lines :sup:`(verified)`

Sandbox **endpoint provisioning** contracts — for the isolated code-execution environment agents can call into.

Top files :sup:`(verified)`
============================

* ``SandboxConstants.kt`` — 213 lines
* ``SandboxProvisioningException.kt`` — 94 lines
* ``SandboxEndpointProvider.kt`` — 61 lines
* ``PendingBootstrapRegistry.kt`` — 44 lines
* ``AtlassianSandboxRedisCache.kt`` — 28 lines

Key contracts
==============

* ``interface SandboxEndpointProvider``
* ``class SandboxProvisioningException``
* ``class PendingBootstrapRegistry``

Notable findings
==================

* The actual code-execution sandbox is **not in this repo** — it lives in the top-level ``rovo-chat-sandbox-code-executor/`` (separate Docker container). This module is the in-process API for **provisioning + addressing** sandbox endpoints.
* Provides Redis cache abstraction (``AtlassianSandboxRedisCache``) for sandbox endpoint state.

