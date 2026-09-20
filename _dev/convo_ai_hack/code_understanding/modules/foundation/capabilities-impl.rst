.. _mod-capabilities-impl:

==============================================
``foundation/capabilities/capabilities-impl``
==============================================

:Tier: foundation
:Path: ``modules/foundation/capabilities/capabilities-impl``
:Size: ~2,313 source lines :sup:`(verified)`
:Importance: **Tier 2 — async runtime**

Concrete capability implementations: Redis-backed distributed state, SQS integration, MCP Spring WebFlux bridge, Caffeine caching.

Dependencies :sup:`(verified)`
================================

* ``capabilities-api`` + ``capabilities-spi``
* Redis, SQS Queue, Aqui
* MCP, MCP Spring WebFlux
* Caffeine
* WireMock (test)

What you would change here
============================

* Modify async task execution → here
* Modify MCP transport binding → here
* Tune cache TTL → Caffeine cache config

