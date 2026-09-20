==================================
Helmfile deployment chain
==================================

Top-level orchestrator
========================

The single source of truth for KITT-on-GCP cluster deployment is
``helmfile/helmfile.yaml`` plus the **11-step bring-up order** documented
in ``helmfile/DEPLOYMENT_ORDER.md``.

::

   helmfile/
     ├── helmfile.yaml             ← top-level orchestrator
     ├── values.yaml               ← shared defaults
     ├── values-development.yaml
     ├── values-production.yaml
     ├── values-eks.yaml
     ├── Makefile                  ← make deploy ENV=dev|prod
     ├── env.example
     ├── README.md                 ← walkthrough + tctl examples
     ├── README-EKS.md             ← AWS variant notes
     ├── DEPLOYMENT_ORDER.md       ← 11 steps (see below)
     ├── DEPLOYMENT_SUMMARY.md     ← Cassandra RF=3, Grafana creds
     ├── deploy-knative.sh         ← 133 LoC ordered deployment
     ├── cleanup-all.sh            ← full teardown (DESTRUCTIVE)
     ├── cleanup-and-redeploy.sh
     ├── cleanup-knative.sh
     ├── apply-and-verify-cassandra-exporter.sh
     ├── apply-cassandra-metrics.sh
     ├── add-clusters-to-es.sh / add-all-clusters-to-es.sh
     ├── delete-old-indices.sh
     ├── aws-accounts.json         ← scraper-sourced AWS account inventory
     ├── bootstrap/                ← cluster CRDs + RBAC + operators
     ├── temporal-manifests/       ← Temporal cluster manifests
     ├── dte/                      ← production DTE control-plane
     ├── temporal-helloworld/      ← sample Temporal app
     ├── s3-crud-api/              ← sample S3 CRUD service
     ├── python-app/               ← sample Python app (GCP)
     └── (29+ root-level cassandra-*, knative, network YAMLs)

Top-level YAMLs (selected)
===========================

* ``cassandra-metrics-exporter-deployment.yaml``,
  ``cassandra-jmx-exporter-config.yaml``,
  ``cassandra-jmx-exporter-sidecar.yaml``,
  ``cassandra-servicemonitor.yaml``,
  ``cassandra-grafana-dashboard.yaml`` — Cassandra observability.
* ``add-cassandra-jmx-scrape-job.yaml``,
  ``cassandra-jmx-scrape-config.yaml`` — Prometheus scrape job.
* ``temporal-keyspace-setup-job.yaml``,
  ``temporal-namespace-register-job.yaml``,
  ``temporal-schema-setup-job.yaml``,
  ``temporal-schema-version-setup-job.yaml``,
  ``setup-temporal-schema-job.yaml``,
  ``check-schema-version-job.yaml`` — Temporal schema lifecycle jobs.
* ``delete-all-temporal-data-job.yaml`` — full reset (use with care).
* ``update-cassandra-replication-factor-job.yaml`` — RF migration.
* ``copy-dashboards-job.yaml``,
  ``cleanup-unwanted-dashboards-job.yaml``,
  ``delete-unwanted-dashboards-job.yaml``,
  ``delete-dashboards-from-db-job.yaml``,
  ``delete-dashboard-files-job.yaml`` — Grafana dashboard housekeeping.
* ``create-default-namespace-job.yaml`` — bootstrap default namespace.
* ``allow-all.yaml``, ``deny-all.yaml``,
  ``all-ingress.yaml``, ``all-egress.yaml`` — NetworkPolicy primitives.
* ``basic-ingress.yaml``, ``internal-ingress.yaml``,
  ``managed-cert-ingress.yaml``, ``internalsvc.yaml`` — Ingress
  primitives.
* ``config-domain-patch.yaml``, ``config-domain-update.yaml`` — Knative
  domain config (Step 6 of DEPLOYMENT_ORDER).
* ``Dockerfile.temporal-tools`` — image used by the schema/job pods.
* ``combined.yaml`` — aggregated ingress/services for one-shot apply.

The 11-step deployment order
=============================

From ``DEPLOYMENT_ORDER.md`` (paraphrased; do not skip steps 6 → 7):

.. list-table::
   :header-rows: 1
   :widths: 8 32 60

   * - Step
     - What
     - Notes
   * - 0
     - Knative Operator
     - Deploys CRDs and core operator pod.
   * - 1
     - CRDs
     - All required CRDs (Knative, KEDA, Temporal, custom KITT CRDs from
       ``asi/`` and ``sweeper/``).
   * - 2
     - Network config
     - Per-cluster networking baseline.
   * - 3
     - Network policy — webhook
     - Allows webhook traffic.
   * - 4
     - Network policy — ALB
     - For AWS variant.
   * - 5
     - Network policy — general
     - Generic deny-all baseline + selective allows.
   * - 6
     - **Domain config** (CRITICAL)
     - Must precede serving-core (Step 7) — otherwise Knative serving
       starts with the wrong cluster-local domain.
   * - 7
     - Knative Serving Core
     - The actual serving controller.
   * - 8
     - Kourier Operator
     - Knative ingress.
   * - 9
     - Istio configuration
     - Service mesh.
   * - 10
     - ALB Ingress
     - External traffic entry point (AWS) or GCLB (GCP).
   * - 11
     - Application layer
     - DTE distributed-client/worker, dte-web, dtecli/bootstrap,
       monitoring, logging, ASI, sweeper, kitt-runbooks worker, scraper.

Sample Helmfile orchestrator (helmfile.yaml)
=============================================

::

   repositories:
     - name: temporal
       url: https://temporalio.github.io/helm-charts
     - name: bitnami
       url: https://charts.bitnami.com/bitnami
     - name: elastic
       url: https://helm.elastic.co

   environments:
     dev:  { values: [values-development.yaml] }
     prod: { values: [values-production.yaml] }
     eks:  { values: [values-eks.yaml] }

   releases:
     - name: temporal-postgresql
       chart: bitnami/postgresql
     - name: temporal-redis
       chart: bitnami/redis
     - name: temporal
       chart: temporal/temporal
     - name: temporal-helloworld-worker
     - name: temporal-helloworld-go-web-service
     - name: s3-crud-api

(Reproduced from helmfile/README.md skeleton; actual file may include
additional charts.)

ArgoCD GitOps overlay
======================

::

   argocd/
     ├── argocd-bootstrap/    ← installs ArgoCD itself
     ├── argocd-apps/         ← ArgoCD ApplicationSet for first-party apps
     ├── cluster-bootstrap/   ← cluster-level CRDs + ASI/sweeper init
     └── cluster-apps/        ← runtime apps (DTE, kitt-runbooks, etc.)

The recursive App-of-Apps pattern means a single ``argocd-bootstrap``
manifest pulls in everything else.

Companion ``deploy/`` and ``ai/``
=================================

* ``deploy/helmfile.yaml`` — secondary Helmfile orchestrator (Kafka,
  charts/, ingress flavours). 19 files including ``helmfile``,
  ``charts/go-app/`` Helm chart, ``python/`` scripts, ``test.sh``.
* ``ai/gcp-critical-pods.yaml`` — single PriorityClass manifest applied
  to AI/compute-class pods to prevent eviction.

Cost & migration analytics
===========================

Numbers used to size the deployment came from these analytics:

* ``analyze_service_regions.py`` (root, 10,665 bytes) — regional service
  distribution analysis.
* ``cdp_services/`` — 6 files: ``all.csv``, ``service_environments.csv``,
  ``service_region_counts.csv``, ``region_count_histogram.{py,png}``,
  ``explode_environments.py``.
* ``atlassian_services/`` — 11 files including ``all_services.csv``
  (404 KB), ``analyze_sliver_services.py``,
  ``services_20plus_shards_report.md``,
  ``services_under20_shards_report.md``,
  ``sliver_services_per_region.{csv,png}``,
  ``sliver_services_per_shard_count.{csv,png}``,
  ``sliver_services_prod_envs.csv``,
  ``sliver_services_under20_shard_count.csv``.
* ``costs-estimates/`` — 7 files: ``compute_costs.py``,
  ``comprehensive_cost_analysis.png``, ``cost_comparison_graph.png``,
  ``cost_comparison_table.{csv,txt}``, ``cost_differences_graph.png``,
  ``rules.txt``.

These are **read-only** analytics artefacts — re-running the Python
scripts regenerates the PNG/CSV outputs.

Volcano + Kueue (batch / GPU)
==============================

* ``vocalno/`` — 10 files. Helmfile (``helmfile.yaml``), agent configs
  for GCP and AWS (``agent.yaml``, ``aws-agent.yaml``), sample
  ``vcjob.yaml``, ``queue.yaml``, ``cpu_burst.yaml``,
  ``gcp-quotas.yaml``, ``add-labels.sh``, ``bootstrap.sh``,
  ``userdata.sh``.
* ``pae/`` — 15 files. Helmfile (``helmfile.yaml``) + ``helmfile/``
  subdir, ``charts/`` per-component, ``connect-cluster.txt``,
  ``kueue.json``, ``pae.json``, ``prompts.txt``, ``Makefile``,
  ``LICENSE``, ``README.md``.
* ``pae-apps/`` — 7 files. Sample apps + ``creat-jobs.sh``,
  ``jobs.yaml``, ``KUEUE-CRDS.md``, ``kueueviz-ingress.yaml``,
  ``Makefile``, ``charts/``, ``helmfile.yaml``.
