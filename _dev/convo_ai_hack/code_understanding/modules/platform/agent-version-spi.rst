.. _mod-agent-version-spi:

==============================================
``platform/agent-version/agent-version-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/agent-version/agent-version-spi``
:Size: ~61 source lines :sup:`(verified)`

ERS (Atlassian Entity Resource Store) client for agent versions. Sharded for multi-tenant scale.

Top files :sup:`(verified)`
============================

* ``ErsAgentVersion.kt`` — 48 lines (ERS document model)
* ``AgentVersionErsClient.kt`` — 13 lines

Key contract :sup:`(verified)`
===============================

.. code-block:: kotlin

   interface AgentVersionErsClient :
       ShardedErsClient<ErsAgentVersion, AgentVersioningContext>

Notable findings
==================

* **ShardedErsClient** parameterization — agent versions are stored per-tenant shard. Cross-tenant lookup is therefore not a single query.
* Tiny module (61 LoC) by design — just the persistence contract; the impl is in ``agent-version-impl``.

