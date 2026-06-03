.. _mod-base-impl:

==============================================
``platform/base/base-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/base/base-impl``
:Size: ~2,659 source lines :sup:`(verified)`

Implementation of the cross-cutting base services: feature config, LLM-tool adapter, streaming writer, MCP wrapper, TurboPuffer (vector store).

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``FeatureConfigServiceImpl.kt``
     - 612
     - Feature-config runtime
   * - ``LlmInvocableAdapterImpl.kt``
     - 440
     - LLM-tool invocation adapter
   * - ``HttpRequestStreamingWriter.kt``
     - 240
     - Streaming HTTP body writer
   * - ``IntegrationsServiceMcpToolWrapperImpl.kt``
     - 218
     - MCP tool wrapper for IntegrationsService
   * - ``AbstractTurboPufferService.kt``
     - 210
     - TurboPuffer vector-store base

Key Spring components
=======================

* ``class FeatureConfigServiceImpl``
* ``class LlmInvocableAdapterImpl``
* ``class HttpRequestStreamingWriter``
* ``class IntegrationsServiceMcpToolWrapperImpl``
* ``class AbstractTurboPufferService``

Notable findings
==================

* **TurboPuffer integration is here** (``AbstractTurboPufferService``) — vector store for retrieval/embeddings is in base-impl, not in knowledge-impl. Suggests vector retrieval is a base capability, not knowledge-specific.
* **MCP tool wrapper** — Model Context Protocol wraps Integration Service tools so they can be invoked by LLMs.
* **Streaming primitive** lives here — ``HttpRequestStreamingWriter`` provides the streaming body abstraction other modules build on.

