==================================
Per-module catalog
==================================

This section catalogs every directory under ``atlassian_packages/gcp_kitt/``
with deep-dive content. Each module document follows a consistent shape:

* **Purpose** — one-paragraph statement of intent
* **Tech stack** — languages, frameworks, key dependencies
* **Inventory** — file count, key files with role/LoC
* **Public surface** — CRDs, HTTP endpoints, CLI commands, Temporal workflows
* **Auth & RBAC** — SLAuth, ASAP, JWT, GCP IAM, K8s ClusterRoles
* **Build & deploy** — Make targets, helmfile commands, scripts
* **Integration** — how it wires into the rest of the platform
* **Hazards** — production gotchas observed from docs/code

The grouping below mirrors the *Walking Tour* in
:doc:`../overviews/02-architectural-narrative`.

Distributed Task Execution (DTE)
================================

.. toctree::
   :maxdepth: 1

   dte-amp
   dte-amp-spike
   dte-cli
   dte-web

Helm-deployed platform
======================

.. toctree::
   :maxdepth: 1

   helmfile-platform
   deploy
   argocd

Kubernetes operators
====================

.. toctree::
   :maxdepth: 1

   asi
   sweeper
   forge-containers

Temporal workflow services
==========================

.. toctree::
   :maxdepth: 1

   kitt-runbooks
   scraper

Edge / sidecar services
=======================

.. toctree::
   :maxdepth: 1

   iam-sidecar
   k8s-metadata-collector
   go-app

Observability stack
===================

.. toctree::
   :maxdepth: 1

   logging
   monitoring

Batch / GPU workloads
=====================

.. toctree::
   :maxdepth: 1

   vocalno
   pae
   pae-apps

Cryptography & routing libs
===========================

.. toctree::
   :maxdepth: 1

   portable-cryptor
   routers

Lambda / serverless
===================

.. toctree::
   :maxdepth: 1

   lambda

Reporting & analytics
=====================

.. toctree::
   :maxdepth: 1

   atlassian_services
   cdp_services
   costs-estimates

Reference workloads & misc
==========================

.. toctree::
   :maxdepth: 1

   cc
   forge
   kittz
   busybox
   ai
   tests

At-a-glance counts
==================

The following table summarises the file counts per top-level directory
(verified by ``find . -type f -not -path '*/.git/*' | wc -l`` on
2026-05-08). These numbers anchor every per-module document.

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Directory
     - Files
     - One-line purpose
   * - ``helmfile/``
     - 205
     - Single largest subsystem; deploys Temporal, Postgres, Redis, Cassandra, Knative, DTE, sample apps
   * - ``scraper/``
     - 99
     - Temporal-backed web scraper (Python) with PG+Redis backend, KEDA scaling, Grafana dashboards
   * - ``deploy/``
     - 78
     - Secondary helmfile orchestrator (Kafka, basic ingresses, sample test pods)
   * - ``forge_containers/``
     - 67
     - K8s operator + ForgeApp CRD for Atlassian Forge container deployments
   * - ``dtecli/``
     - 62
     - TypeScript CLI for DTE (auth, cluster, workflow, config commands); Temporal Cloud bootstrap helmfile
   * - ``kitt-runbooks/``
     - 55
     - Go Temporal worker for K8s SRE runbooks (cordoned-node, cyclops cycle, unhealthy-deployments)
   * - ``logging/``
     - 48
     - Fluent Bit DaemonSet → Elasticsearch ingest pipeline with Kubernetes/Temporal enrichment
   * - ``amp/``
     - 36
     - Go DTE distributed-client + distributed-worker (HTTP API, Temporal workflows, Argo execution)
   * - ``dte-web/``
     - 26
     - Express.js Web UI + REST API for DTE; ASAP + slauth-sidecar
   * - ``lambda/``
     - 23
     - AWS Lambda scrapers (DynamoDB, Postgres) — legacy SQS path
   * - ``pae/``
     - 19
     - Kueue (Job Priority Queue) ClusterQueues + LocalQueues
   * - ``portable-cryptor/``
     - 16
     - AWS↔GCP KMS-portable RSA encryption library
   * - ``argocd/``
     - 16
     - GitOps app-of-apps (Argo CD bootstrap + cluster-bootstrap manifests)
   * - ``routers/``
     - 14
     - Pure-Python URL router library with wildcard/path-param matching
   * - ``asi/``
     - 14
     - K8s controller for ``ASI`` CRD; manages GCP IAM-bound K8s ServiceAccounts
   * - ``iam-sidecar/``
     - 13
     - Sidecar exposing ``/token`` for GCP service-account JWT issuance
   * - ``cc/``
     - 12
     - Confluence Cloud monolith Helm template manifests
   * - ``pae-apps/``
     - 11
     - kueueviz dashboard + sample jobs alongside ``pae``
   * - ``atlassian_services/``
     - 11
     - Shard/region distribution analysis (Pandas + CSV/PNG reports)
   * - ``vocalno/``
     - 10
     - Volcano batch scheduler agent + queue/quota config
   * - ``monitoring/``
     - 10
     - Prometheus + Grafana for Temporal/dtaske; ConfigMap update tooling
   * - ``go-app/``
     - 9
     - Sample Go service: Pub/Sub, GCS, Spanner, Cloud Trace
   * - ``k8s-metadata-collector/``
     - 8
     - Go collector → Kinesis stream of pod/node metadata
   * - ``sweeper/``
     - 7
     - K8s controller for ``Sweeper`` CRD; labels pods with serviceID
   * - ``costs-estimates/``
     - 7
     - GCP/AWS compute cost calculator (Pandas + Matplotlib)
   * - ``amp-spike/``
     - 7
     - Earliest experimental Express.js prototype of DTE; deployed via ``atlas micros``
   * - ``cdp_services/``
     - 6
     - Service-environment explosion + region histogram analytics
   * - ``forge/``
     - 5
     - Reference Forge apps (quiz-app, long-running-app, i18n-question-generator)
   * - ``kittz/``
     - 4
     - Node.js multi-region EKS deployment orchestrator (standalone)
   * - ``busybox/``
     - 4
     - Debug image (BusyBox derivative) for ``kubectl debug``
   * - ``tests/``
     - 2
     - Service-discovery integration test scaffolding
   * - ``ai/``
     - 1
     - ResourceQuota for system-critical pods (single YAML)
