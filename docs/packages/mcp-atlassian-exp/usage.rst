Usage
=====

This page documents the most common ways to interact with
``mcp-atlassian-exp``.

Installation
----------------------------------------

The package is published as part of the OpenStartup monorepo. From a
checkout::

    pip install -e packages/mcp-atlassian-exp

Environment
----------------------------------------

Set the runtime configuration via environment variables (a complete list
is documented on the the top-level ``docs/source/configuration.rst`` reference page). Common ones include:

* ``OPENSTARTUP_ENV`` -- ``dev``, ``staging`` or ``prod``.
* ``LOG_LEVEL`` -- defaults to ``INFO``.
* Package-specific overrides documented in :doc:`api` under
  ``mcp_atlassian_exp.config``.

Command-line
----------------------------------------

The package ships a ``mcp-atlassian-exp`` console script. Show available subcommands::

    mcp-atlassian-exp --help

Programmatic Python use
----------------------------------------

.. code-block:: python

    from mcp_atlassian_exp import build_default_client

    client = build_default_client()
    result = client.run(...)
    print(result)

Examples
----------------------------------------

End-to-end recipes live under ``examples/mcp-atlassian-exp/`` in the monorepo and
are referenced from the project README. Each example is runnable as a
script and exercises a representative integration path.

Troubleshooting
----------------------------------------

* **Missing dependencies** -- verify the extras for the package are
  installed (``pip install -e 'packages/mcp-atlassian-exp[all]'``).
* **Auth failures** -- confirm the credentials referenced in
  :doc:`api` are exported and that the host has network egress to the
  third-party APIs.
* **Rate limits** -- increase the backoff window via the package's
  ``RETRY_BACKOFF_SECONDS`` environment variable.
