.. _mod-atlassianstudio-impl:

==============================================
``product/atlassianstudio/atlassianstudio-impl``
==============================================

:Tier: product
:Path: ``modules/product/atlassianstudio/atlassianstudio-impl``
:Size: ~4,734 source lines :sup:`(verified)`

Concrete Atlassian Studio chat executor.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``AgentChatExecutor.kt``
     - **2,618**
     - Chat execution (god-class)
   * - ``AtlassianStudioAgentStreamingWriter.kt``
     - 708
     - Streaming output
   * - ``AgentChatWorkflowImpl.kt``
     - 460
     - Workflow orchestration
   * - ``AgentChatSuccessMetricsPublisherImpl.kt``
     - 275
     - Metrics
   * - ``AtlassianStudioStreamOutputHandler.kt``
     - 248
     - Stream handler

Notable findings
==================

* **AgentChatExecutor is 2,618 lines = 55% of module** — Atlassian Studio's chat execution is significant complexity, separate from Rovo's.
* Has its own streaming writer + output handler (separate from platform/base-impl streaming infrastructure) — likely product-specific output shaping.

