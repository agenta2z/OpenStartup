.. _mod-stratus-api:

==============================================
``platform/stratus-contracts/stratus-api``
==============================================

:Tier: platform
:Path: ``modules/platform/stratus-contracts/stratus-api``
:Size: ~1,542 source lines :sup:`(verified)`

Contracts for **Stratus** — Atlassian's internal entity/knowledge-graph platform. Defines the events and data models the convo-ai service emits to Stratus.

Notable findings
==================

* Specialized integration module — only relevant when convo-ai needs to publish entities or query the entity graph.
* Pairs with ``stratus-spi`` (1,045 LoC) for persistence/subscription.

