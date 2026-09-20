.. _mod-jira-api:

==============================================
``product/jira/jira-api``
==============================================

:Tier: product
:Path: ``modules/product/jira/jira-api``
:Size: ~571 source lines :sup:`(verified)`

Jira-specific API surface, focused on the **Suggest Issues** feature.

Top files :sup:`(verified)`
============================

* ``SuggestIssuesRequest.kt`` — 265 lines
* ``SuggestIssuesConfig.kt`` — 99 lines
* ``SuggestIssueSource.kt`` — 48 lines
* ``SuggestIssuesOrchestrator.kt`` — 46 lines
* ``SuggestIssuesResponse.kt`` — 41 lines

Notable findings
==================

* **Single-feature API** — focused entirely on issue suggestion. Jira's other AI features must live elsewhere (likely in aifeature-api or jira-impl directly).
* Request type (265 lines) is data-rich — many filter / scope options.

