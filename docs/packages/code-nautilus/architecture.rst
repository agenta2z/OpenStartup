Architecture
============

This page describes the runtime architecture of ``code-nautilus``.

High-level diagram
----------------------------------------

.. code-block:: text

    +------------------------------------------------------------+
    | code-nautilus                                              |
    +------------------------------------------------------------+
    | Entrypoints (CLI / app factory / MCP server / HTTP)         |
    +------------------------------------------------------------+
    | Application services                                        |
    |  - request / task handlers                                  |
    |  - adapters to third-party APIs                             |
    |  - result formatters / serializers                          |
    +------------------------------------------------------------+
    | Shared OpenStartup runtime contracts                        |
    |  - openteam.* task & artifact primitives                    |
    |  - server.*   transport helpers                             |
    +------------------------------------------------------------+

Module layout
----------------------------------------

* ``code_nautilus/__init__.py`` -- public re-exports.
* ``code_nautilus/server`` or ``code_nautilus/app`` -- transport
  surface (FastAPI app, MCP server, or CLI dispatcher).
* ``code_nautilus/adapters`` -- thin clients around third-party SDKs.
* ``code_nautilus/models`` -- pydantic / dataclass schemas used by the
  public API.
* ``code_nautilus/config`` -- environment-driven settings.

Data flow
----------------------------------------

1. Caller invokes one of the entrypoints listed in the overview.
2. The entrypoint resolves configuration from environment variables and
   passes a validated ``Settings`` object into the service layer.
3. The service layer composes one or more adapters to fulfil the request
   and emits a typed response.
4. Errors are normalised into the OpenStartup error envelope so that the
   web GUI and MCP clients can render consistent diagnostics.

Concurrency model
----------------------------------------

* I/O paths are ``async``-first. Synchronous helpers wrap ``anyio.run``
  for ergonomic use from notebooks and scripts.
* Long-running work (indexing, multi-file refactors, large search
  fan-outs) is dispatched onto background workers and tracked via the
  shared task store.

Dependency boundaries
----------------------------------------

``code-nautilus`` depends on:

* Bitbucket Cloud
* GitHub Enterprise
* Atlassian TeamWork Graph
* OpenSearch / Elastic indexers

These are declared as **mock imports** in the local ``conf.py`` so Sphinx
can build documentation in environments without the SDKs installed.
