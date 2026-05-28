MCP tools
=========

``mcp-scout`` exposes the following tools over the
`Model Context Protocol <https://modelcontextprotocol.io>`_. Each tool is
registered with the ``mcp.server`` runtime at startup; schemas are
auto-derived from the pydantic models in ``mcp_scout.models``.

.. contents::
   :local:
   :depth: 1

``scout.search``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unified search across Confluence, Jira, Bitbucket, Drive and Slack.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``query``
     - string
     - Free-text query.
   * - ``sources``
     - array[string]
     - Subset of sources to include.
   * - ``limit``
     - integer
     - Max results per source.

**Output**

list[Hit] with source, title, url, snippet, score.
``scout.fetch``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch the full body of a single hit by URI.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``uri``
     - string
     - Resource URI returned by ``scout.search``.

**Output**

Document object with title, content, metadata.
``scout.recent_activity``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Surface recent activity for a user across sources.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``user``
     - string
     - AAID, email, or username.
   * - ``hours``
     - integer
     - Lookback window, default 24.

**Output**

list[Activity] with type, source, timestamp, entity.
``scout.related``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find resources related to a seed URI.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``uri``
     - string
     - Seed resource.
   * - ``limit``
     - integer
     - Max related items.

**Output**

list[RelatedHit] with relation type and confidence.


Tool registration
----------------------------------------

Tools are registered in ``mcp_scout.server`` via the
``@server.tool(...)`` decorator. Adding a new tool only requires
defining its pydantic input model and an async handler; the schema is
emitted automatically.
