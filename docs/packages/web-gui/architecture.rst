Architecture
============

This page describes the runtime architecture of ``web-gui``.

High-level diagram
----------------------------------------

.. code-block:: text

    +------------------------------------------------------------+
    | web-gui                                                    |
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

* ``web_gui/__init__.py`` -- public re-exports.
* ``web_gui/server`` or ``web_gui/app`` -- transport
  surface (FastAPI app, MCP server, or CLI dispatcher).
* ``web_gui/adapters`` -- thin clients around third-party SDKs.
* ``web_gui/models`` -- pydantic / dataclass schemas used by the
  public API.
* ``web_gui/config`` -- environment-driven settings.

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

``web-gui`` depends on:

* FastAPI
* Vite + React frontend
* Tailwind CSS
* uvicorn / gunicorn

These are declared as **mock imports** in the local ``conf.py`` so Sphinx
can build documentation in environments without the SDKs installed.
