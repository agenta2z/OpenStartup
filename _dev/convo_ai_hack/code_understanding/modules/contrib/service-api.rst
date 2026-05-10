.. _mod-contrib-service-api:

==============================================
``contrib/service/service-api``
==============================================

:Tier: contrib
:Path: ``modules/contrib/service/service-api``
:Size: ~1,144 source lines :sup:`(verified)`

Sub-team-contributed service contracts. **JQL services** dominate: Jira Field Service, JQL generation, plugin input.

Top files :sup:`(verified)`
============================

* ``jql/JiraFieldService.kt``
* ``jql/JiraJqlFieldAndValues.kt``
* ``jql/RovoJiraJqlGenerationService.kt``
* ``jql/JiraPluginInput.kt``
* ``jql/JQLFieldsAndFunctionDocuments.kt``

Notable findings
==================

* **NOT vestigial** — 31 Kotlin files (largest contrib module).
* Heavy JQL focus — natural-language → JQL is a Rovo capability that needs domain-specific knowledge of Jira fields, functions, and operators.
* Lives in contrib (not in product/jira) likely because it's a shared capability used by multiple consumers (Rovo + AgentStudio + AI features).

