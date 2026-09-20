==================================
``monitoring/`` — Prometheus + Grafana for Temporal/dtaske
==================================

Purpose
=======

``monitoring/`` (10 files) reuses the **Prometheus + Grafana** charts
already deployed by the platform Temporal Helm release and:

1. Patches the Prometheus ``ConfigMap`` to scrape the ``dtaske``
   namespace (and any other namespace via regex).
2. Provisions four pre-built Grafana dashboards covering Temporal,
   KEDA, PostgreSQL and Redis.
3. Configures Grafana persistence (10 GiB EBS GP3 PVC).

Tech stack
==========

* **Prometheus** + **Grafana** (charts owned by the temporal release)
* **YAML** + **Bash** + **jq** for ConfigMap surgery

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - File
     - Role
   * - ``monitoring/helmfile.yaml``
     - Helm chart references (temporal-prometheus, temporal-grafana)
   * - ``monitoring/PROMETHEUS_DTASKE_UPDATE.md``
     - ConfigMap patching guide
   * - ``monitoring/update-prometheus-dtaske.sh``
     - Automated jq-based ConfigMap update
   * - ``monitoring/temporal-grafana-values.yaml``
     - Persistence config (10 GiB EBS GP3)
   * - ``monitoring/.helmfile.d/values.yaml``
     - ES / Kibana host configuration
   * - ``monitoring/grafana-keda-scaledobjects.json``
     - KEDA autoscaling dashboard
   * - ``monitoring/grafana-postgres-overview.json``
     - PostgreSQL dashboard
   * - ``monitoring/grafana-redis-overview.json``
     - Redis dashboard
   * - ``monitoring/grafana-temporal-dashboard.json``
     - Temporal workflow / task-queue dashboard
   * - ``monitoring/README.md``
     - Setup & dashboard import instructions

Recording rules
===============

Documented in ``PROMETHEUS_DTASKE_UPDATE.md`` for ``dte-service-capture``
metric aggregations (Temporal task / workflow rates).

Build & deploy
==============

.. code-block:: bash

   ./update-prometheus-dtaske.sh           # patches ConfigMap
   kubectl get configmap temporal-prometheus-server \
       -n temporal -o jsonpath='{.data.prometheus\.yml}' | grep "regex:"
   # Force pod restart to pick up new ConfigMap
   kubectl delete pod -n temporal -l app=prometheus
   kubectl port-forward -n temporal svc/temporal-prometheus-server 9090:80
   # Grafana UI: http://temporal-grafana.fqk5.kitt-inf.net

Integration with gcp_kitt
=========================

* **Reuses:** the Prometheus + Grafana from ``helmfile/``'s Temporal
  release
* **Scrape targets:** ``temporal-services-servicemonitors.yaml`` (in
  ``helmfile/``)
* **Dashboards consumed by:** any team running workloads in ``dtaske``

Hazards
=======

* **ConfigMap edits do not auto-reload.** Must delete the Prometheus
  pod after every ``update-prometheus-dtaske.sh`` run.
* **Namespace regex is OR-pipe** (``|``) — must update both
  ``kubernetes-service-endpoints`` and ``kubernetes-pods`` jobs.
* **Grafana persistence path** ``/var/lib/grafana`` — without the PVC,
  pod restarts wipe all custom dashboards.
* **Dashboards imported manually via UI** — drift between repo JSON and
  live UI is common; treat repo as source of truth.
