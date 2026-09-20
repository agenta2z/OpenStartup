.. _mod-rovo-leaf-agents-impl:

==============================================
``product/rovo/rovo-leaf-agents-impl``
==============================================

:Tier: product
:Path: ``modules/product/rovo/rovo-leaf-agents-impl``
:Size: ~427 source lines :sup:`(verified)`

Concrete leaf-level Rovo agents — currently dominated by **DevAgent** provisioning + service.

Top files :sup:`(verified)`
============================

* ``RovoDevAgentProvisioningServiceImpl.kt`` — 175 lines
* ``RovoDevAgentServiceImpl.kt`` — 154 lines
* ``AgentRecommendationServiceImpl.kt`` — 98 lines

Notable findings
==================

* "Leaf agents" = terminal-task-specific agents (vs. orchestrators).
* Heavy DevAgent presence — Rovo Dev (the developer agent) has its own provisioning + service.
* ``AgentRecommendationServiceImpl`` — recommends agents based on context.

