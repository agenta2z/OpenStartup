Architecture
============

This page describes the runtime architecture of ``code-nemo``.

High-level diagram
----------------------------------------

.. code-block:: text

    +------------------------------------------------------------+
    | code-nemo                                                  |
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

* ``code_nemo/__init__.py`` -- public re-exports.
* ``code_nemo/server`` or ``code_nemo/app`` -- transport
  surface (FastAPI app, MCP server, or CLI dispatcher).
* ``code_nemo/adapters`` -- thin clients around third-party SDKs.
* ``code_nemo/models`` -- pydantic / dataclass schemas used by the
  public API.
* ``code_nemo/config`` -- environment-driven settings.

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

``code-nemo`` depends on:

* LangChain
* OpenAI / Anthropic chat completion APIs
* Bitbucket / GitHub PR APIs

These are declared as **mock imports** in the local ``conf.py`` so Sphinx
can build documentation in environments without the SDKs installed.
