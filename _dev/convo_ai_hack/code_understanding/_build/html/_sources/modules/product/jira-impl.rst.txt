.. _mod-jira-impl:

==============================================
``product/jira/jira-impl``
==============================================

:Tier: product
:Path: ``modules/product/jira/jira-impl``
:Size: ~8,974 source lines :sup:`(verified)` — *largest -impl in product tier*
:Importance: Tier 1

Jira AI feature implementations: issue suggestion, comment summarization, work breakdown.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Role
   * - ``SuggestIssueCompletedAnalyticsAttributes.kt``
     - **800**
     - Analytics-event schema
   * - ``CommentSummaryServiceImpl.kt``
     - 655
     - Comment summarization
   * - ``SuggestIssuesOrchestratorImpl.kt``
     - 486
     - Issue-suggestion orchestrator
   * - ``WorkItemSuggestIssuesService.kt``
     - 401
     - Work-item suggestions
   * - ``JiraAiWorkBreakdownServiceImpl.kt``
     - 366
     - Work breakdown

Key Spring components
=======================

* ``class SuggestIssuesOrchestratorImpl`` — multi-source content fan-out
* ``class CommentSummaryServiceImpl``
* ``class WorkItemSuggestIssuesService``
* ``class JiraAiWorkBreakdownServiceImpl``
* ``class MediaServiceFacade``

Notable findings
==================

* **Largest analytics-attributes file in repo** — ``SuggestIssueCompletedAnalyticsAttributes.kt`` at 800 LoC. Reflects how much detail is captured per suggestion (per-step, per-source, per-LLM-call).
* Multi-source content provider pattern: pulls from Confluence, Loom, third-party sources.
* **100+ JQL YAML config files** in resources — Jira field definitions used by query builders.

