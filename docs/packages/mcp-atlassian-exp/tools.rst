MCP tools
=========

``mcp-atlassian-exp`` exposes the following tools over the
`Model Context Protocol <https://modelcontextprotocol.io>`_. Each tool is
registered with the ``mcp.server`` runtime at startup; schemas are
auto-derived from the pydantic models in ``mcp_atlassian_exp.models``.

.. contents::
   :local:
   :depth: 1

``jira.search_issues``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Jira issues with JQL.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``jql``
     - string
     - JQL expression.
   * - ``limit``
     - integer
     - Max results, default 25.

**Output**

list[Issue] -- flattened issue payloads with key, summary, status, assignee.
``jira.get_issue``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a single Jira issue by key.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``issue_key``
     - string
     - e.g. ``CTSC-39558``.

**Output**

Issue object with fields, comments, transitions.
``jira.add_comment``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add a comment to a Jira issue.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``issue_key``
     - string
     - Target issue.
   * - ``body``
     - string
     - Markdown comment body.

**Output**

Comment object with id, author, created.
``confluence.search_pages``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Confluence pages via CQL.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``cql``
     - string
     - Confluence Query Language string.
   * - ``limit``
     - integer
     - Max results.

**Output**

list[Page] with id, title, space, url.
``confluence.get_page``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch a Confluence page body.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``page_id``
     - string
     - Page identifier.

**Output**

Page object with storage-format body and metadata.
``bitbucket.list_prs``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List pull requests in a repository.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``workspace``
     - string
     - Bitbucket workspace.
   * - ``repo``
     - string
     - Repository slug.
   * - ``state``
     - string
     - OPEN | MERGED | DECLINED.

**Output**

list[PullRequest].


Tool registration
----------------------------------------

Tools are registered in ``mcp_atlassian_exp.server`` via the
``@server.tool(...)`` decorator. Adding a new tool only requires
defining its pydantic input model and an async handler; the schema is
emitted automatically.
