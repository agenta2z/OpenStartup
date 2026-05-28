Backend integration
===================

``web-gui`` is the user-facing front door for the OpenStartup
platform; it composes calls to the other packages.

Service dependencies
----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Upstream
     - Surface
     - Used for
   * - ``server`` (core)
     - HTTP + websockets
     - Task submission, status polling, log streaming.
   * - ``inference`` (core)
     - HTTP
     - Model registry browsing, ad-hoc completions.
   * - ``mcp-scout``
     - MCP over stdio
     - ``/scout`` search UI.
   * - ``mcp-atlassian-exp``
     - MCP over stdio
     - ``/atlassian`` browser, embedded ticket previews.
   * - ``code-conseil`` / ``code-nautilus`` / ``code-nemo``
     - HTTP webhooks
     - Triggering and inspecting agent runs from the dashboard.

API surface exposed by web-gui
----------------------------------------

The FastAPI app exposes a JSON API mounted under ``/api`` that the
frontend consumes exclusively. Notable endpoints include:

* ``GET  /api/health`` -- liveness probe.
* ``GET  /api/agents`` -- list registered code agents.
* ``POST /api/agents/{id}/runs`` -- kick off an agent run.
* ``GET  /api/scout/search?q=...`` -- proxy into ``mcp-scout``.
* ``WS   /api/runs/{run_id}/stream`` -- server-sent log stream.

Authentication
----------------------------------------

* Authenticates users via the shared OpenStartup OIDC provider.
* Server-to-server calls into MCP servers use a short-lived service
  token issued by the ``server`` package.

Observability
----------------------------------------

* Structured JSON logs on stdout (``LOG_LEVEL`` env var).
* OpenTelemetry traces exported to the OTLP endpoint configured by the
  platform; see the top-level ``docs/source/operations.rst`` reference.

Local development
----------------------------------------

``packages/web-gui/scripts/dev.sh`` launches:

1. The FastAPI backend with autoreload on port ``8000``.
2. The Vite dev server on port ``5173`` with proxying configured.
3. Mock MCP servers if ``MOCK_MCP=1`` is set.
