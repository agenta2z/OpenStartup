.. _mod-client-impl:

==============================================
``platform/client/client-impl``
==============================================

:Tier: platform
:Path: ``modules/platform/client/client-impl``
:Size: ~54,844 source lines :sup:`(verified)`
:Importance: **Tier 1 — Atlassian-product clients**

HTTP / GraphQL clients for downstream Atlassian products. The code-volume hotspots are Confluence + Jira async clients (5,788 + 3,755 + 3,211 lines for the three biggest files alone).

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Subsystem
   * - ``platform/client/confluence/AsyncConfluenceRestClientImpl.kt``
     - 5,788
     - Confluence REST
   * - ``platform/client/jira/ExtendedJiraRestClientImpl.kt``
     - 3,755
     - Jira REST (extended)
   * - ``platform/client/confluence/AsyncConfluenceAggClientImpl.kt``
     - 3,211
     - Confluence Aggregator (GraphQL)
   * - ``platform/client/jira/AsyncJiraRestClientImpl.kt``
     - 1,714
     - Jira REST (base)
   * - ``platform/client/confluence/ConfluenceContentRestDelegate.kt``
     - 1,639
     - Confluence content delegation

Subsystems
============

* **Confluence REST client** (5,788 lines) — wraps the full Confluence REST API with retry, error mapping, metric emission
* **Confluence Aggregator client** (3,211 lines) — GraphQL-style queries against Confluence's aggregator
* **Jira REST clients** — base + extended (extended adds methods specific to Atlassian-internal callers)
* **Content delegation** — orchestrates content retrieval across multiple Confluence APIs

Why so big?
=============

These files are large because:

1. Each external API has dozens of operations
2. Each operation needs a typed request, typed response, error mapping, retry, metric emission
3. The async (suspend) wrapping is non-trivial for streaming endpoints

Patterns
==========

1. **Async by default.** All client methods are ``suspend fun``. No blocking calls.
2. **Per-product modules.** Confluence, Jira, etc. each get their own subpackage + client class.
3. **Extended vs base.** ``ExtendedJiraRestClient`` exists for methods that aren't in the public Jira REST contract.
4. **Aggregator for GraphQL.** Confluence has both REST and GraphQL surfaces; both are wrapped.

What you would change here
============================

* **Add a new external API call** → method in the appropriate ``Async<Product>RestClientImpl.kt``
* **Add a new external product client** → new sub-package + client class
* **Tune retry/backoff** → typically in a wrapping factory or via base client config

