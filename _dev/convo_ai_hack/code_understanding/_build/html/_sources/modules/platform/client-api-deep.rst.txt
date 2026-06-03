.. _mod-client-api-deep:

==================================================================
``platform/client/client-api`` — Atlassian REST/GraphQL clients
==================================================================

:Tier: platform
:Path: ``modules/platform/client/client-api``
:Size: **45,005 main + ~unverified test LoC** :sup:`(verified 2026-05-02)`
:Files: ~529 main
:Importance: ⭐⭐⭐⭐⭐ Tier 0 — every Atlassian-product integration depends on this

The largest single module in the codebase. Provides REST + GraphQL client contracts for
**every Atlassian service** convo-ai integrates with. Most of the size is data-class DTOs
(many of which are likely machine-generated).

Per-product client breakdown
==============================

.. list-table::
   :header-rows: 1
   :widths: 35 12 12 41

   * - Sub-package
     - LoC
     - Files
     - Service it talks to
   * - ``platform/client/jira/``
     - **11,599**
     - 61
     - Jira REST API + GraphQL
   * - ``platform/client/confluence/``
     - **4,394**
     - 12
     - Confluence REST API
   * - ``platform/client/jsm/``
     - 2,705
     - 11
     - Jira Service Management
   * - ``platform/client/ags/``
     - 1,824
     - 35
     - Atlassian Granular Service
   * - ``platform/client/bitbucket/``
     - 1,492
     - 11
     - Bitbucket REST API
   * - ``platform/client/skills/``
     - 1,416
     - 6
     - Skills service (talent / hiring?)
   * - ``platform/client/compass/``
     - 1,249
     - 1
     - **Compass** (Atlassian's component catalog) — single 1,249-line file
   * - ``platform/client/atlas/``
     - 1,225
     - 3
     - Atlas (project management)
   * - ``platform/client/search/aggregator/``
     - 1,033
     - 8
     - Search aggregator
   * - ``platform/client/agg/``
     - 931
     - 12
     - AGG (Aggregator)
   * - ``platform/client/googlecalendar/``
     - 793
     - 2
     - Google Calendar
   * - ``platform/client/integrationsservice/``
     - 729
     - 15
     - Atlassian Integration Service
   * - ``platform/client/user/``
     - 687
     - 5
     - User service
   * - ``platform/client/tritongrpc/``
     - 677
     - 7
     - **Triton gRPC** (NVIDIA Triton inference server)
   * - ``platform/client/marketplace/``
     - 649
     - 5
     - Atlassian Marketplace

The top 5 files alone
=======================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Why so big
   * - ``AsyncConfluenceRestClient.kt``
     - 2,699
     - Reactive Confluence REST surface — many endpoints
   * - ``JiraProjectsRestClientDataModel.kt``
     - 2,008
     - Jira projects API DTOs (likely generated)
   * - ``JsmServicedeskModels.kt``
     - 1,644
     - JSM service-desk DTOs
   * - ``JiraBoardRestClientDataModel.kt``
     - 1,586
     - Jira boards DTOs
   * - ``ExtendedJiraRestClient.kt``
     - 1,406
     - Extended Jira client surface

What you would change here
============================

* **Add support for a new Atlassian service** → new sub-package under ``platform/client/``
* **Add a new endpoint to an existing client** → modify the corresponding ``Async*RestClient.kt`` file
* **Add new fields to a DTO** → modify the corresponding ``*DataModel.kt`` file (but these may be regenerated from OpenAPI schemas — check first)

What you would NOT change here
================================

* Authentication — uses standard ASAP/OAuth provided by foundation tier
* Service discovery — handled by service mesh (declared in ``convo-ai.ad.yml``)
* Caching — caches live in caller modules (``service-impl/`` + product-tier)

Critical observations
=======================

1. **The 2,699-line ``AsyncConfluenceRestClient.kt``** is in a single file. This is unusual for hand-written code — likely the file is mechanically generated from OpenAPI/GraphQL schema, or split across @JsonProperty data classes that pack densely.

2. **``platform/client/compass/`` is a single 1,249-line file** — same observation: probably generated from a GraphQL schema (Compass is GraphQL-first).

3. **Triton gRPC client (677 LoC, 7 files)** — direct integration with NVIDIA Triton inference server, separate from AI Gateway. This is for self-hosted models that bypass the gateway.

4. **No tests in this module's test directory** for many sub-packages — DTOs aren't tested directly; integration tests live in caller modules.

5. **The "platform/client/" prefix** is verbose given this IS a platform/client module. The deep nesting suggests packages were designed to mirror the broader codebase's import structure.

Refactoring opportunities
===========================

* **Verify which DTOs are generated** — if many are, document the generator + regen procedure prominently
* **Split mega-files** — 2,000+ line single files are hard to navigate; could split per endpoint group
* **Audit unused clients** — at 529 files, some may no longer have callers

