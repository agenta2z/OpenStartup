.. _mod-adk-core-impl:

==============================================
``foundation/adk/core-impl``
==============================================

:Tier: foundation
:Path: ``modules/foundation/adk/core-impl``
:Size: ~1,224 source lines :sup:`(verified)`
:Importance: **Tier 2 — ADK runtime**

Runtime that loads agents and dispatches tool calls. Heavily integrates Google ADK + A2A Spring Boot + analytics + MCP HTTP transport.

Dependencies :sup:`(verified)`
================================

* ``adk-core-api``, ``utilities-api``
* Google ADK (with extensive exclusions for BigQuery, AI Platform, Speech, Storage, Auth, Arrow)
* A2A Spring Boot
* Analytics Spring Boot
* MSB WebFlux

Patterns
==========

1. **Heavy exclusions of Google ADK transitive deps.** Brings only what's needed; avoids dragging in BigQuery/etc.
2. **MCP HTTP transport customization.** Adapts MCP for Spring WebFlux.

What you would change here
============================

* Modify agent loading lifecycle → here
* Modify A2A integration → here
* Modify MCP transport → here

