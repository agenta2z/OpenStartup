.. _mod-client-api:

==============================================
``platform/client/client-api``
==============================================

:Tier: platform
:Path: ``modules/platform/client/client-api``
:Size: **~45,005 source lines** :sup:`(verified)` — *largest module by line count*
:Importance: Tier 1 — every product module imports this

REST/GraphQL client contracts for downstream Atlassian services (Jira, Confluence, JSM). Massive because each Jira/Confluence/JSM API surface area is itself massive.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Concept
   * - ``AsyncConfluenceRestClient.kt``
     - 2,699
     - Reactive Confluence REST client
   * - ``JiraProjectsRestClientDataModel.kt``
     - 2,008
     - Jira projects API DTOs
   * - ``JsmServicedeskModels.kt``
     - 1,644
     - JSM service-desk models
   * - ``JiraBoardRestClientDataModel.kt``
     - 1,586
     - Jira boards API DTOs
   * - ``ExtendedJiraRestClient.kt``
     - 1,406
     - Extended Jira client

Key public contracts
======================

* ``AsyncConfluenceRestClient`` — non-blocking Confluence REST surface
* ``ExtendedJiraRestClient`` — extended Jira REST surface
* DTOs for Jira projects, boards, JSM service-desk
* Apollo GraphQL clients (per build deps)

Notable findings
==================

* **45K LoC** — by far the largest single module. The size reflects the breadth of Atlassian APIs the platform integrates with, not internal complexity.
* **Top 5 files = 9.7K LoC alone** — Jira and Confluence dominate.
* Uses both REST (manual DTOs) and GraphQL (Apollo). The DTO files are large because Jira/Confluence APIs themselves expose many fields.
* Considered a generated-code module by some teams — DTOs may be machine-generated from OpenAPI schemas.

