==================================
``helmfile/`` — the Helm-based platform (largest subsystem)
==================================

Purpose
=======

``helmfile/`` (205 files — the single largest directory in the repo) is
the canonical Helm-driven control plane for the entire gcp_kitt cluster.
It deploys, in dependency order:

1. **Knative serving** (operator → CRDs → networking → domain → core →
   Kourier → Istio → ALB)
2. **Data plane** — Cassandra (RF=3), PostgreSQL (Bitnami), Redis (Bitnami),
   Elasticsearch
3. **Temporal** server (Bitnami / temporal.io chart)
4. **DTE workloads** — ``distributed-client`` and ``distributed-worker``
   from ``helmfile/dte`` (mirror of ``amp/``)
5. **Sample applications** — ``temporal-helloworld``, ``s3-crud-api``,
   ``python-app``
6. **Bootstrap chart** under ``helmfile/bootstrap/`` (Argo CD seed,
   ServiceAccount/ClusterRole/ClusterRoleBinding)
7. **Operational jobs** — Cassandra schema setup, Temporal namespace
   registration, schema versioning, dashboard import, replication-factor
   updates, full-data wipe, etc.

A second helmfile (``deploy/helmfile.yaml``) is layered *on top* for
secondary releases (Kafka, basic ingresses, sample test workloads).

Tech stack
==========

* **Helmfile** as orchestrator
* **Helm** charts (Bitnami, temporal.io, custom in ``charts/``)
* **Knative serving** + **Kourier** + **Istio**
* **ArgoCD** integration via the ``bootstrap`` chart
* **Cassandra** as Temporal persistence (RF=3)
* **Bash scripts** for ordered rollout / cleanup

Inventory highlights
====================

Top-level files

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - Path
     - Size / LoC
     - Role
   * - ``helmfile.yaml``
     - —
     - Root release manifest (5 main releases + samples)
   * - ``Makefile``
     - —
     - ``make deploy-prod``, ``make deploy-dev``, ``make test``
   * - ``DEPLOYMENT_ORDER.md``
     - —
     - 11-step ordered deployment chain (see :doc:`../architecture/05-helmfile-deployment-chain`)
   * - ``DEPLOYMENT_SUMMARY.md``
     - —
     - Cassandra RF=3 notes, Grafana dashboard provisioning, admin creds
   * - ``deploy-knative.sh``
     - 133
     - Automated Knative deployment in dependency order
   * - ``cleanup-all.sh``
     - 100
     - Full teardown
   * - ``aws-accounts.json``
     - 76 MB
     - AWS account enumeration (consumed by ``scraper``)
   * - ``values-development.yaml``
     - —
     - Dev environment overrides
   * - ``values-production.yaml``
     - —
     - Prod overrides
   * - ``values-eks.yaml``
     - —
     - EKS overrides (ALB, cloud-provider)
   * - ``README.md`` / ``README-EKS.md``
     - —
     - Top-level platform & EKS-specific docs

Subdirectories

* ``helmfile/bootstrap/`` — initial cluster CRDs, RBAC, operators;
  contains ``charts/argo-dte-bootstrap/`` (ServiceAccount, ClusterRole,
  ClusterRoleBinding for the Argo CD seed)
* ``helmfile/dte/`` — *mirror* of ``amp/distributed-worker`` packaged into
  ``charts/dte/`` with Knative Service, Istio, ExternalName services,
  RBAC. ``helmfile/dte/distributed-worker/main.go`` is 1178 LoC vs
  1222 LoC in ``amp/``.
* ``helmfile/temporal-helloworld/`` — Temporal workflow demo (workflow.go,
  activities.go, two workers — web-service & distributed-worker) +
  ``charts/temporal-helloworld/`` (Deployment, HPA, Namespace).
* ``helmfile/s3-crud-api/`` — AWS S3 CRUD service with HPA, NetworkPolicy,
  PDB.
* ``helmfile/python-app/`` — Python app demonstrating GCP auth, S3,
  PubSub.
* ``helmfile/dte/charts/dte/templates/`` — Knative Services, Istio,
  ExternalName, RBAC templates.

Operational manifests (top-level YAML — non-exhaustive)
========================================================

* ``temporal-keyspace-setup-job.yaml`` — creates Cassandra keyspace, RF=3
* ``temporal-schema-setup-job.yaml`` — schema initialisation
* ``temporal-schema-version-setup-job.yaml`` — schema version pin
* ``setup-temporal-schema-job.yaml`` — CQL bootstrap
* ``temporal-namespace-register-job.yaml`` — registers default namespace
* ``temporal-services-servicemonitors.yaml`` — Prometheus scrape targets
* ``temporal-grafana-dashboard.yaml`` /
  ``redis-grafana-dashboard.yaml`` /
  ``postgresql-grafana-dashboard.yaml`` — dashboard ConfigMaps
* ``cassandra-jmx-exporter-*.yaml`` — Cassandra JMX → Prometheus
* ``allow-all.yaml`` / ``deny-all.yaml`` /
  ``all-ingress.yaml`` / ``all-egress.yaml`` — NetworkPolicy templates
* ``delete-all-temporal-data-job.yaml`` — full wipe (be careful!)
* ``delete-dashboard-files-job.yaml`` /
  ``delete-dashboards-from-db-job.yaml`` /
  ``delete-unwanted-dashboards-job.yaml`` /
  ``delete-old-indices.sh`` — cleanup tooling
* ``update-cassandra-replication-factor-job.yaml`` — mid-deployment RF
  scale
* ``Dockerfile.temporal-tools`` — image holding ``tctl`` and Cassandra
  CLI

Helmfile release shape
======================

``helmfile.yaml`` (root) declares:

.. code-block:: yaml

   repositories:
     - temporal
     - bitnami
     - elastic
   environments:
     dev:  { values: [values-development.yaml] }
     prod: { values: [values-production.yaml] }
     eks:  { values: [values-eks.yaml] }
   releases:
     - temporal-postgresql               # bitnami/postgresql
     - temporal-redis                    # bitnami/redis
     - temporal                          # temporal/temporal
     - temporal-helloworld-worker
     - temporal-helloworld-go-web-service
     - s3-crud-api

Build & deploy
==============

.. code-block:: bash

   # Whole platform
   helmfile deploy
   # Selective
   helmfile apply --selector name=temporal
   # Makefile wrappers
   make deploy-prod
   make deploy-dev
   # Explicit Knative dependency-order deploy
   ./deploy-knative.sh
   # Operational jobs (raw kubectl)
   kubectl apply -f temporal-keyspace-setup-job.yaml
   kubectl apply -f temporal-namespace-register-job.yaml

Environment variables of note
=============================

* ``TEMPORAL_ADDRESS`` / ``TEMPORAL_NAMESPACE`` — server connectivity
* ``AWS_REGION`` / ``GOOGLE_CLOUD_PROJECT`` — cloud credentials
* ``CASSANDRA_REPLICATION_FACTOR=3`` — HA replication
* Grafana admin credentials — embedded in ``DEPLOYMENT_SUMMARY.md``

Integration with gcp_kitt
=========================

* **Upstream consumer:** ``deploy/`` (Kafka + secondary releases) and
  ``argocd/`` (GitOps sync)
* **Downstream:** every other module ultimately lands here as a Helm
  release (DTE, scraper, monitoring, logging…) or relies on the
  Temporal/Cassandra/PG/Redis/ES it provisions
* **EKS vs GKE:** ``values-eks.yaml`` swaps Knative networking to AWS ALB
* **Bootstrap chart** seeds Argo CD which then pulls the rest

Hazards
=======

* **DEPLOYMENT_ORDER.md is gospel.** Steps 6 (Domain Config) → 7 (Knative
  Serving Core) cannot be reordered without breaking the cluster.
* **``aws-accounts.json`` is 76 MB.** Treat as data, not source; never
  edit by hand and never commit transformations of it.
* **DTE worker drift.** ``helmfile/dte/distributed-worker/main.go`` is
  smaller than ``amp/distributed-worker/main.go``; verify in CI that the
  two stay in lockstep before bumping image tags.
* **Cassandra RF=3 is hardcoded** in ``DEPLOYMENT_SUMMARY.md`` — single-AZ
  test clusters with RF=3 will refuse writes if any AZ is degraded.
* **delete-all-temporal-data-job.yaml** is a destructive primitive; do
  not leave it scheduled.
* **Knative scale-to-zero** propagates throughout — first request after
  idle pays cold-start.
