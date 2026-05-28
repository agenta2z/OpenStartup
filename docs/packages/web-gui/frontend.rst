Frontend
========

``web-gui`` ships a Single Page Application served by the
FastAPI backend. This page documents the asset layout, route map, and
build pipeline.

Asset layout
----------------------------------------

::

    packages/web-gui/
    |-- src/web_gui/
    |   |-- app.py            # FastAPI app factory
    |   |-- static/           # built JS/CSS bundles (generated)
    |   `-- templates/        # Jinja templates for the SSR shell
    `-- frontend/
        |-- package.json      # pnpm workspace manifest
        |-- vite.config.ts    # Vite build configuration
        |-- tailwind.config.ts
        |-- public/           # static assets copied verbatim
        `-- src/
            |-- main.tsx      # React entrypoint
            |-- routes/       # React-Router route components
            |-- components/   # shared UI primitives
            |-- hooks/        # data-fetching hooks (TanStack Query)
            `-- api/          # generated TypeScript clients

Route map
----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Route
     - Purpose
   * - ``/``
     - Dashboard summarising recent inference runs and scout activity.
   * - ``/agents``
     - List and detail views for the registered code agents.
   * - ``/agents/:id``
     - Per-agent run history, logs, and configuration editor.
   * - ``/scout``
     - Scout search experience backed by ``mcp-scout``.
   * - ``/atlassian``
     - Browser for Jira / Confluence content fetched via
       ``mcp-atlassian-exp``.
   * - ``/settings``
     - Connection wizard and environment overview.
   * - ``/api/*``
     - JSON API mounted by ``web_gui.app:create_app``; documented under
       :doc:`api`.

Build pipeline
----------------------------------------

1. ``pnpm install`` inside ``packages/web-gui/frontend``.
2. ``pnpm run build`` produces hashed assets under
   ``frontend/dist/`` and copies them into
   ``src/web_gui/static/`` for serving by FastAPI's
   :class:`~starlette.staticfiles.StaticFiles`.
3. ``pnpm run dev`` runs Vite's HMR dev server on port ``5173`` and
   proxies ``/api`` to ``http://localhost:8000``.
4. In production the FastAPI app serves the prebuilt bundle directly;
   the Vite dev server is **not** required at runtime.

Deployment
----------------------------------------

* The package's wheel includes the prebuilt frontend assets, so
  deploying ``web-gui`` is a single ``uvicorn web_gui.app:create_app``
  invocation behind a TLS-terminating proxy.
* For multi-replica deployments use ``gunicorn`` with the
  ``uvicorn.workers.UvicornWorker`` worker class.

Theming & accessibility
----------------------------------------

* Tailwind tokens are defined under ``frontend/src/styles/tokens.css``.
* Components target WCAG 2.1 AA; keyboard navigation and high-contrast
  modes are exercised in the Storybook stories shipped under
  ``frontend/src/stories/``.
