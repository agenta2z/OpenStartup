==================================
``dtecli/`` — DTE TypeScript CLI + Temporal-Cloud bootstrap
==================================

Purpose
=======

``dtecli/`` is the operator-facing CLI for the Distributed Task Execution
(DTE) platform. It is a single-file Node.js bundle (``dist/cli.cjs``)
authored in TypeScript. It also ships a ``bootstrap/`` sub-project: a
self-contained Helmfile + Temporal-worker that bootstraps a fresh DTE
control plane (Temporal Cloud namespace registration, IAM seeding,
ConfigMap generation, etc.).

Tech stack
==========

* **Language:** TypeScript (Node.js 18+, ES modules), bundled by **esbuild**
* **CLI framework:** ``commander`` ^12.1.0
* **HTTP:** ``axios`` ^1.7.9
* **Temporal:** ``@temporalio/client`` ^1.10.2
* **Logging:** ``pino`` ^9.5.0
* **Validation:** ``zod`` ^3.24.1
* **Config parsing:** ``js-yaml`` ^4.1.0
* **Cross-platform binaries:** ``pkg`` (Linux x64/arm64, macOS x64)

Inventory (62 files)
====================

CLI source (``src/cli/``):

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``src/cli/cli.ts``
     - 47
     - ``commander`` root program; mounts sub-commands
   * - ``src/cli/commands/auth/login.ts``
     - 250
     - ``auth login`` (SLAuth) — token retrieval + persistence
   * - ``src/cli/commands/auth/token.ts``
     - 135
     - ``auth token --show``
   * - ``src/cli/commands/auth/logout.ts``
     - 41
     - ``auth logout`` — token deletion
   * - ``src/cli/commands/cluster/list.ts``
     - 235
     - ``cluster list``
   * - ``src/cli/commands/cluster/status.ts``
     - 339
     - ``cluster status`` — Elasticsearch ``cluster_registry`` query
   * - ``src/cli/commands/cluster/utils.ts``
     - 168
     - Shared cluster helpers
   * - ``src/cli/commands/config/index.ts``
     - 13
     - ``config`` mount point (``set`` / ``list``)
   * - ``src/cli/commands/workflow/*.ts``
     - —
     - ``workflow start/status/list/stop`` operations

Library (``src/lib/``):

* ``dte-client.ts`` — HTTP client to ``distributed-client``
* ``ad-groups.ts`` — Active Directory group helpers
* ``logger.ts`` — pino logger wrapper
* ``config.ts`` — file-based config (``~/.dte/``)
* ``service-discovery-parser.ts`` — parses worker output for service-discovery
* ``health-check-parser.ts`` — parses worker output for health-check

Bootstrap sub-project (``dtecli/bootstrap/``):

* ``Dockerfile``, ``Makefile``, ``helmfile.yaml``, ``vitest.config.ts``
* ``helm/Chart.yaml``, ``helm/values.yaml``
* ``src/worker.ts`` — Temporal worker entrypoint
* ``src/workflows.ts`` + ``src/workflows.test.ts`` — bootstrap workflows
* ``src/activities.ts`` — bootstrap activities (register namespace, seed
  ConfigMap, etc.)
* ``src/logger.ts`` — bootstrap logger
* ``releases/manifest.toml`` — release pinning manifest
* ``bin/build.sh`` — release build script

Public surface — CLI commands
==============================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Command
     - Behaviour
   * - ``auth login --slauth``
     - Logs in via SLAuth; persists token to ``~/.dte/token.json``
   * - ``auth token --show``
     - Prints current bearer token
   * - ``auth logout``
     - Removes the persisted token
   * - ``cluster list [--env dev|stg|prod] [--region NAME] [--verbose]``
     - Lists clusters from local clusters.json
   * - ``cluster status <code>``
     - Queries Elasticsearch ``cluster_registry`` index for full status
   * - ``workflow start <type> [--task-queue Q] [-n NAME]``
     - POSTs to ``distributed-client`` to start a Temporal workflow
   * - ``workflow list``
     - Lists workflows known to ``distributed-client``
   * - ``workflow status <id>``
     - Polls workflow execution status
   * - ``workflow stop <id>``
     - Terminates the workflow
   * - ``config set --dte-url <url>``
     - Persists ``distributed-client`` URL (default ``http://distributed-client.fqk5.kitt-inf.net``)
   * - ``config list``
     - Dumps all persisted config

Auth & RBAC
===========

* **SLAuth** — primary; tokens stored in ``~/.dte/token.json``
* **Atlas CLI integration** — ``atlas kitt context`` is invoked for cluster
  discovery
* **No ASAP issuance** in dtecli itself; ASAP-required calls are routed
  through ``distributed-client`` which performs the exchange.

Build & deploy
==============

.. code-block:: bash

   npm install
   npm run build      # tsc type-check + esbuild bundle
   npm run bundle     # esbuild → dist/cli.cjs
   npm run package    # pkg → multi-platform binaries
   node dist/cli.cjs <command>

The ``bootstrap/`` Helmfile is run separately during one-time DTE platform
provisioning::

   cd dtecli/bootstrap
   helmfile apply

Integration with gcp_kitt
=========================

* **Calls:** ``distributed-client`` HTTP API; Elasticsearch
  ``cluster_registry`` index; Temporal Cloud (via Temporal client SDK).
* **Default URL:** ``http://distributed-client.fqk5.kitt-inf.net``.
* **Bootstrap:** plays once during platform install; not a runtime
  dependency.

Hazards
=======

* **CSRF bypass via distributed-client.** The CLI deliberately routes
  through ``distributed-client`` to dodge Temporal Web's CSRF protection;
  see ``scraper/temporal-pg-redis/FIX_TEMPORAL_WEB_CSRF.md`` for the
  matching fix on the worker side.
* **Knative scale-to-zero.** ``distributed-client`` may be cold; first
  call after idle returns 503 unless the user runs a warm-up curl or
  ``kubectl port-forward``.
* **Token file permissions.** ``~/.dte/token.json`` contains a long-lived
  SLAuth bearer; CLI does not enforce 0600 mode.
* **Hard-coded default URL** — if a user forgets to ``config set
  --dte-url``, every workflow call goes to the *fqk5* dev cluster.
