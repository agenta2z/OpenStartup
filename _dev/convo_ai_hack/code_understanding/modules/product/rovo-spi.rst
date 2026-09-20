.. _mod-rovo-spi:

==============================================
``product/rovo/rovo-spi``
==============================================

:Tier: product
:Path: ``modules/product/rovo/rovo-spi``
:Size: ~1,041 source lines :sup:`(verified)`

ERS persistence contracts for Rovo-specific entities: agents, knowledge sources, widgets, tasks.

Top files :sup:`(verified)`
============================

* ``ErsAgentKnowledgeSource.kt`` — 193 lines
* ``ErsWidget.kt`` — 113 lines
* ``ErsTask.kt`` — 87 lines
* ``ErsAgent.kt`` — 68 lines

Notable findings
==================

* All four entity types have separate ERS classes — Rovo agents are first-class persistent entities (not just config records).
* Tasks have an ERS form too — Rovo's "background task" concept is durable, not ephemeral.

