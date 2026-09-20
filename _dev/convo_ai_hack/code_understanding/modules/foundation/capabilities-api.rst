.. _mod-capabilities-api:

==============================================
``foundation/capabilities/capabilities-api``
==============================================

:Tier: foundation
:Path: ``modules/foundation/capabilities/capabilities-api``
:Size: ~1,165 source lines :sup:`(verified)`
:Importance: **Tier 2 — async + MCP**

Contracts for async tasks, MCP (Model Context Protocol) integration, and Aqui task framework.

Dependencies :sup:`(verified)`
================================

* ``utilities-api``
* MCP BOM + MCP SDK
* Reactor

Patterns
==========

1. **Lightweight API.** Pure contracts; no Spring deps.
2. **MCP-aware.** First-class support for the Model Context Protocol.

What you would change here
============================

* Define a new capability type → here
* Modify MCP message contracts → here

