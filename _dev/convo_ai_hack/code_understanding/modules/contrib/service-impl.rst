.. _mod-contrib-service-impl:

==============================================
``contrib/service/service-impl``
==============================================

:Tier: contrib
:Path: ``modules/contrib/service/service-impl``
:Size: ~4,785 source lines :sup:`(verified)`

JQL service implementations.

Top files :sup:`(verified)`
============================

* ``jql/DocumentationSearchServiceImpl.kt``
* ``jql/JiraJqlCorrectionServiceImpl.kt``
* ``jql/JiraPluginPromptServiceImpl.kt``
* ``jql/JQLDocumentationProvider.kt``
* ``jql/RovoJiraJqlGenerationServiceImpl.kt``

Notable findings
==================

* **JQL correction service** — corrects malformed JQL queries (e.g., when LLM emits invalid JQL).
* **JQL documentation search** — RAG over Jira's JQL function docs to ground LLM JQL generation.
* **Prompt service** — builds the JQL-generation prompts.
* Substantial module (4,785 LoC) — natural-language → JQL is non-trivial.

