MCP resources
=============

In addition to tools, ``mcp-atlassian-exp`` exposes a set of MCP
**resources** that clients can subscribe to or read on demand. Resources
are addressed by URI templates that the server resolves at request time.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - URI template
     - Description
   * - ``atlassian://jira/issue/{key}``
     - Live Jira issue payload, refreshed on read.
   * - ``atlassian://confluence/page/{id}``
     - Confluence page in storage-format HTML.
   * - ``atlassian://bitbucket/pr/{workspace}/{repo}/{id}``
     - Pull-request payload with diff stats.
   * - ``atlassian://jira/search?jql=...``
     - Materialised search result list.

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
Refer to ``mcp_atlassian_exp.adapters`` for the supported subscription
backends.
