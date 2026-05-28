MCP resources
=============

In addition to tools, ``mcp-scout`` exposes a set of MCP
**resources** that clients can subscribe to or read on demand. Resources
are addressed by URI templates that the server resolves at request time.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - URI template
     - Description
   * - ``scout://hit/{uri_b64}``
     - Resolves an opaque scout hit reference to its full document.
   * - ``scout://activity/{user}``
     - Recent activity timeline for the given user.
   * - ``scout://index/sources``
     - Static list of indexed sources with health status.

Resource lifecycle
----------------------------------------

* Resources are listed via the standard ``resources/list`` MCP call.
* Read operations are idempotent; the server caches upstream responses
  for a short TTL configurable via ``MCP_RESOURCE_TTL`` (seconds).
* Mutations are performed exclusively through tools -- resources are
  read-only.

Subscriptions
----------------------------------------

Resources that map to mutable upstream entities (issues, pages, PRs)
support change notifications when the upstream API exposes a webhook.
Refer to ``mcp_scout.adapters`` for the supported subscription
backends.
