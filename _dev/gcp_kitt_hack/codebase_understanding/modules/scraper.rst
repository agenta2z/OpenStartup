==================================
``scraper/`` — Temporal-backed Python web scraper
==================================

Purpose
=======

``scraper/`` (99 files — second-largest directory) is a distributed web
scraper written in Python. The flagship implementation lives under
``scraper/temporal-pg-redis/`` and uses **Temporal** for orchestration,
**PostgreSQL** for persistence, and **Redis** for queue management. A
legacy SQS+DynamoDB Lambda variant lives under ``scraper/pg/`` and
``lambda/`` and is no longer actively developed.

A Flask REST API exposes the job-management surface; KEDA autoscales
worker deployments based on Temporal task-queue depth; Prometheus +
Grafana provide observability.

Tech stack
==========

* **Python** (Flask API, Temporal workers, activities)
* **Temporal** (workflow engine; activity-based execution)
* **PostgreSQL** (state + results)
* **Redis** (queue / requeue counts)
* **Kubernetes**, **Helmfile**, **KEDA**, **Prometheus**, **Grafana**
* **Docker**, **ALB ingress**

Inventory highlights
====================

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Path
     - Role
   * - ``scraper/temporal-pg-redis/README.md``
     - Full architecture, API usage, setup
   * - ``scraper/temporal-pg-redis/k8s/adminer-deployment.yaml``
     - PostgreSQL Web UI (port 8080, host ``adminer.fqk5.kitt-inf.net``)
   * - ``scraper/temporal-pg-redis/k8s/create-temporal-namespace-job.yaml``
     - One-time namespace registration via ``tctl``
   * - ``scraper/temporal-pg-redis/k8s/import-grafana-dashboards-job.yaml``
     - Provisions Grafana dashboards from ConfigMaps
   * - ``scraper/temporal-pg-redis/k8s/keda-scaledobject.yaml`` /
       ``keda-scaledobject-pa.yaml``
     - KEDA autoscaling on Temporal task-queue depth
   * - ``scraper/temporal-pg-redis/k8s/redis-commander-deployment.yaml``
     - Redis admin UI
   * - ``scraper/temporal-pg-redis/k8s/secrets.yaml``
     - DB / API secrets
   * - ``scraper/temporal-pg-redis/values/api-server.yaml`` /
       ``values/worker.yaml`` / ``values/scraper-dashboards.yaml``
     - Helm chart value overrides
   * - ``scraper/temporal-pg-redis/setup-database.sh``
     - PG schema initialisation
   * - ``scraper/temporal-pg-redis/scale-workers.sh``
     - Manual scale override
   * - ``scraper/temporal-pg-redis/investigate-stuck-workflow.sh``
     - SRE helper script
   * - ``scraper/temporal-pg-redis/PROMETHEUS_METRICS.md``
     - Instrumentation reference
   * - ``scraper/temporal-pg-redis/SERVICEMONITOR_SETUP.md``
     - Prometheus ServiceMonitor wiring
   * - ``scraper/temporal-pg-redis/REQUEUE_COUNT_ANALYSIS.md``
     - Retry/requeue logic deep-dive
   * - ``scraper/temporal-pg-redis/WORKFLOW_TASK_NOT_FOUND_EXPLANATION.md``
     - Notes on the most common Temporal failure mode
   * - ``scraper/temporal-pg-redis/FIX_TEMPORAL_WEB_CSRF.md``
     - Workaround for Temporal Web CSRF blocking direct API calls
   * - ``scraper/temporal-pg-redis/GRAFANA_DASHBOARDS.md``
     - Dashboard catalogue
   * - ``scraper/temporal-pg-redis/docs/check-failed-workflows.md`` /
       ``find-previous-run-id.md``
     - Operational runbooks
   * - ``scraper/temporal-pg-redis/INSTALL_TEMPORAL_CLI.md``
     - ``tctl`` install walk-through
   * - ``scraper/temporal-pg-redis/src/`` / ``src-js/``
     - Python (workers, API server, activities) and a JS client harness
   * - ``scraper/temporal-pg-redis/scripts/``
     - Deployment automation
   * - ``scraper/pg/README.MD``
     - Legacy SQS+DLQ Lambda variant
   * - ``scraper/temporal-pg-redis/requirements.txt``
     - Python deps

Public surface
==============

* **Flask REST API** for job submission, status, and result retrieval
  (routes documented in the module README).
* **Temporal frontend:** ``temporal-frontend:7233``
* **Temporal namespace:** ``default`` (created with 72 h retention)

Database integrations
=====================

* **PostgreSQL**

  - Server: ``temporal-postgresql.temporal.svc.cluster.local``
  - Default DB: ``postgres``
  - Tables: jobs, results, requeue tracking (schema in README)

* **Redis**

  - Queue management (key structure in README)
  - Per-URL requeue count tracking

* **Cassandra:** none in this module (the platform Cassandra hosts
  Temporal persistence — that lives in ``helmfile/``)

KEDA scaling
============

Configured via ``k8s/keda-scaledobject*.yaml`` and detailed in
``TEMPORAL_SCALING.md`` — triggers off Temporal task-queue depth.

Observability
=============

* ConfigMaps: ``scraper-dashboard-overview``,
  ``scraper-dashboard-k8s-resources``
* ``prometheus: temporal`` label for scrape selection
* ServiceMonitor per ``SERVICEMONITOR_SETUP.md``

Build & deploy
==============

.. code-block:: bash

   make build          # Docker image (git hash/tag as version)
   make deploy         # helmfile apply (skip-deps)
   ./setup-database.sh
   ./scale-workers.sh
   ./investigate-stuck-workflow.sh

Key environment variables
=========================

* ``TEMPORAL_ADDRESS=temporal-frontend:7233``
* ``ADMINER_DEFAULT_SERVER=temporal-postgresql.temporal.svc.cluster.local``
* ``ADMINER_DEFAULT_USERNAME=postgres``
* ``ADMINER_DEFAULT_DB=postgres``
* ``ADMINER_DEFAULT_DRIVER=pgsql``
* Registry credentials (Helm values)

Integration with gcp_kitt
=========================

* **Depends on:** ``helmfile/`` (Temporal, PG, Redis), ``monitoring/``
  (Grafana / Prometheus), ``logging/`` (Filebeat → ES enrichment)
* **Replaces:** ``scraper/pg/`` (legacy SQS path) and the equivalent
  ``lambda/`` Lambda functions

Hazards
=======

* **Temporal Web CSRF** blocks direct ``temporal-web`` API calls;
  ``FIX_TEMPORAL_WEB_CSRF.md`` and the ``distributed-client``
  workaround are the canonical remediation.
* **Workflow-task-not-found** is the most common failure (see dedicated
  doc); causes are typically code-version drift between worker and
  history shard.
* **KEDA reaction time** is bounded by polling interval; bursty load
  may queue before workers scale.
* **Adminer is publicly addressable** (``adminer.fqk5.kitt-inf.net``);
  ensure ingress auth is enabled.
* **72 h retention** — long-running workflows must be designed to
  finish within the window.
