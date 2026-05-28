Integrations
============

``code-nautilus`` reaches out to several third-party systems. This page
catalogues those integrations and the hooks the package exposes for
swapping or extending them.

.. contents::
   :local:
   :depth: 1

Bitbucket Cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nautilus`` clones and incrementally re-syncs Bitbucket Cloud repos into the local nautilus index.
* **Authentication:** ``BITBUCKET_ACCESS_TOKEN`` (read-only is sufficient) plus ``BITBUCKET_WORKSPACE`` to scope discovery. See the ``code_nautilus.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** REST v2 ``/repositories/{workspace}`` for discovery; git+https for clones via the URL returned by the API.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Discovery calls cached for 15 min; clone bandwidth is gated by ``NAUTILUS_MAX_PARALLEL_CLONES`` (default 4).

GitHub Enterprise
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nautilus`` indexes on-prem GitHub Enterprise organisations, including private repos behind VPN.
* **Authentication:** ``GHE_BASE_URL`` + ``GHE_TOKEN`` (PAT with ``read:org`` and ``repo``); ``GHE_CA_BUNDLE`` for custom certificates. See the ``code_nautilus.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** ``{GHE_BASE_URL}/api/v3`` for metadata; mirror clones over SSH when ``NAUTILUS_USE_SSH=1``.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** GHE primary 5,000 req/h + secondary abuse limits; adapter watches ``X-RateLimit-Used`` and pauses scans at 90% saturation.

Atlassian TeamWork Graph
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nautilus`` enriches the code knowledge graph with Jira/Confluence/page/issue edges sourced from the Atlassian TeamWork Graph (TWG).
* **Authentication:** ``TWG_SITE_URL`` + ``TWG_OAUTH_TOKEN`` (forge-issued service account token). See the ``code_nautilus.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** TWG Cypher endpoint (``/twg/graph/cypher``) and the entity-detail GraphQL gateway.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Server-side 50 concurrent queries per principal; adapter serialises with an ``asyncio.Semaphore(8)`` to stay well under the cap.

OpenSearch / Elastic indexers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nautilus`` stores the resulting symbol and embedding indices for low-latency lookup.
* **Authentication:** ``OPENSEARCH_HOSTS`` (comma-separated) plus ``OPENSEARCH_USERNAME`` / ``OPENSEARCH_PASSWORD`` or ``OPENSEARCH_AWS_REGION`` for SigV4. See the ``code_nautilus.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** Bulk ``_bulk`` ingestion and ``_search`` queries against the ``nautilus-*`` index pattern.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Client-side bulk batches default to 5 MiB / 500 docs; back-pressure derives from the cluster's ``429`` responses with exponential backoff up to 120s.

Extending
----------------------------------------

Adapters live under ``code_nautilus.adapters``. To add a new third-party
hook:

1. Subclass ``code_nautilus.adapters.base.BaseAdapter``.
2. Register the adapter via the entry-point group
   ``code-nautilus.adapters`` in ``pyproject.toml``.
3. Document the new integration in this file under its own heading,
   following the same Use case / Authentication / Endpoints / Failure
   mode / Rate limiting structure used above so consumers can scan the
   page consistently.

Webhooks
----------------------------------------

For inbound events (e.g. PR review requests), the package can be deployed
behind the shared OpenStartup webhook router. See the
``docs/MCP_INTEGRATION.md`` and ``docs/operations.rst`` files at the
repository root for the routing configuration; the package itself only
needs the ``WEBHOOK_SECRET`` environment variable set so it can verify
inbound payload signatures.
