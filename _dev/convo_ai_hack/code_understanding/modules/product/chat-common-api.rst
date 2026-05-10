.. _mod-chat-common-api:

==============================================
``product/chat-common/chat-common-api``
==============================================

:Tier: product
:Path: ``modules/product/chat-common/chat-common-api``
:Size: ~1,276 source lines :sup:`(verified)`

Chat-common contracts shared across chat surfaces. Notably, **sensitive-data detection** lives here.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``SensitiveDataDetectionServiceImpl.kt``
     - **914**
     - PII / secret detection (impl in API!)
   * - ``SensitiveDataDetectionService.kt``
     - 167
     - Detection contract
   * - ``ChatExecutor.kt``
     - 46
     - Chat-execution contract
   * - ``SensitiveDataDetectionResult.kt``
     - 43
     - Detection result type

Notable findings
==================

* **Impl class lives in -api.** ``SensitiveDataDetectionServiceImpl`` (914 lines) is in chat-common-api, not -impl. This is unusual — likely because the detection logic is pure (no Spring deps, no I/O) and other modules want to use it directly without DI overhead.
* Pattern-matching / regex-heavy logic: 914 LoC of detection rules.
* Critical for chat safety — every conversation routes input through this before LLM submission.

