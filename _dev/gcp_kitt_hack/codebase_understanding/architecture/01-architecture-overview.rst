==================================
Architecture overview
==================================

System diagram (textual)
=========================

::

   ┌─────────────┐       ┌──────────────┐
   │   Operator  │──CLI──│   dtecli     │  Node.js, 31 TS files, 7,943 LoC
   │  (laptop)   │       │   binary     │  Atlas plugin
   └─────────────┘       └──────┬───────┘
                                │ HTTPS  X-DTE-ASAP / X-DTE-SCT / X-DTE-GROUPS
                                ▼
                         ┌──────────────────┐
                         │   dte-web        │  optional browser UI
                         │   (Express SPA)  │  dte-web/server.js 1,241 LoC
                         └────────┬─────────┘
                                  │ same headers (proxied)
                                  ▼
   ┌──────────────────────────────────────────────────────┐
   │           distributed-client (Knative svc)            │
   │           amp/distributed-client/main.go 1,868 LoC    │
   │     /health  /api?action=...  /start-workflow         │
   └────────────┬─────────────────────────────────────────┘
                │  StartWorkflow(taskQueue="dte-workflows",
                │                workflowType="DistributedTaskExecutionWorkflow",
                │                input=DistributedTaskRequest)
                ▼
        ┌───────────────────────────────────────────┐
        │   Temporal cluster                         │
        │   (helmfile/temporal-manifests/, Cassandra)│
        └────────────┬──────────────────────────────┘
                     │ pollers on task-queue "dte-workflows"
                     ▼
        ┌──────────────────────────────────────────────┐
        │  distributed-worker (Knative svc)             │
        │  amp/distributed-worker/main.go 1,222 LoC     │
        │  helpers.go 1,134, cluster_db.go 276          │
        │                                               │
        │  Workflows registered:                        │
        │   - DistributedTaskExecutionWorkflow          │
        │   - HelloWorldWorkflow                        │
        │  Activities registered:                       │
        │   - HealthCheckActivity                       │
        │   - ServiceDiscoveryActivity                  │
        │   - HelloWorldActivity / Greeting / Processing │
        │     / FormattingActivity                      │
        │   - ExecuteArgoWorkflowActivity               │
        │   - FilterServiceDiscoveryResultsActivity     │
        └─────────┬────────────────────────────────────┘
                  │
        Per-cluster fan-out (parallel):
                  │
   ┌──────────────┴────────────────────────────────────┐
   │ For each cluster c in request.ClusterNames:        │
   │   1. cluster_db.go   → fetch ClusterInfo from S3   │
   │      (kitt-cluster-registry.s3.amazonaws.com)      │
   │   2. helpers.go      → exchange operator token     │
   │      for cluster-bearer (auth-provider)            │
   │   3. createK8sClient → rest.Config + dynamic.IF    │
   │   4. createWorkflowViaAPI → POST Argo Workflow CR  │
   │   5. getWorkflowStatus / getWorkflowOutput         │
   └────────────────────────────────────────────────────┘

Three independent Operator/Worker control loops
================================================

In addition to DTE, three more long-lived processes run inside each
cluster:

1. **ASI Operator** (``asi/cmd/main.go`` 344 LoC) — controller-runtime
   reconciler for ``ASI`` cluster-scoped CRD. Binds K8s ``ServiceAccount``
   to GCP IAM SA. Required GCP role:
   ``roles/iam.serviceAccountAdmin``.
2. **Sweeper Operator** (``sweeper/main.go`` 83 LoC, controller 207 LoC)
   — kubebuilder Operator on ``sweepers.platform.atlassian.com/v1``.
   Schedules pod-labelling sweeps. Leader election lock
   ``sweeper-controller-lock``. Ports: metrics ``:8080``, health
   ``:8081``, webhooks ``:9443``.
3. **kitt-runbooks worker** (``kitt-runbooks/cmd/worker/main.go`` 117
   LoC) — Temporal worker polling task queue ``kitt-runbooks``. Three
   workflows: ``WorkflowK8sNodeCordoned``, ``WorkflowCyclopsCycleNodes``,
   ``WorkflowHighUnhealthyDeployments``.

Two side-car / agent patterns
==============================

* **iam-sidecar** (``iam-sidecar/iam-sidecar.go`` 340 LoC) — runs
  alongside any pod that needs GCP creds; mints tokens via
  ``iamcredentials.GenerateAccessToken``/``GenerateIdToken``. Exposes
  ``/token`` over localhost.
* **k8s-metadata-collector** — daemon collecting per-pod / per-node
  metadata snapshots.

Helmfile deployment graph (top-level)
======================================

::

   helmfile/helmfile.yaml
       ├── repositories: temporal, bitnami, elastic
       ├── environments: dev, prod, eks
       └── releases (rendered in dependency order):
              ├── temporal-postgresql      (bitnami/postgresql)
              ├── temporal-redis           (bitnami/redis)
              ├── temporal                 (temporal/temporal)
              ├── temporal-helloworld-worker
              ├── temporal-helloworld-go-web-service
              └── s3-crud-api

   argocd/argocd-bootstrap     ─►  argocd/argocd-apps     ─►
       argocd/cluster-bootstrap ─►  argocd/cluster-apps   ─►
           helmfile renders & helm-crd controller applies

Layer-by-layer breakdown
=========================

.. list-table::
   :header-rows: 1
   :widths: 18 22 60

   * - Layer
     - Owns
     - Notes
   * - **Bootstrap**
     - ``helmfile/bootstrap/``, ``argocd/argocd-bootstrap/``,
       ``ai/gcp-critical-pods.yaml``
     - First-deploy CRDs, RBAC, ClusterRoles, namespace, PriorityClass.
   * - **Persistence**
     - ``helmfile/`` cassandra-* manifests, Bitnami Postgres / Redis
       releases, ``helmfile/scraper/temporal-pg-redis/setup-database.sh``
     - Temporal can run on Cassandra (default) or Postgres+Redis
       (``scraper/temporal-pg-redis``).
   * - **Networking**
     - ``deny-all.yaml``, ``allow-all.yaml``, ``all-ingress.yaml``,
       ``all-egress.yaml``, Knative + Kourier + Istio configs in
       ``helmfile/``
     - Steps 3–9 of ``DEPLOYMENT_ORDER.md``.
   * - **Workload identity**
     - ``asi/``, ``iam-sidecar/``
     - ASI annotates SA → GCP SA email; iam-sidecar uses Workload
       Identity to mint runtime tokens.
   * - **Control plane**
     - ``amp/distributed-client``, ``amp/distributed-worker``,
       ``kitt-runbooks/``, ``sweeper/``, ``forge_containers/`` (helm-crd
       controller)
     - Knative-deployed Go services + controller-runtime operators.
   * - **Operator UX**
     - ``dtecli/``, ``dte-web/``
     - CLI + Web UI front-ends to DTE.
   * - **Observability**
     - ``logging/`` + ``monitoring/``
     - Filebeat → ES; Prometheus + Grafana + KEDA.
   * - **Batch / GPU**
     - ``vocalno/``, ``pae/``, ``pae-apps/``
     - Volcano scheduler + Kueue queueing.
   * - **Data plane**
     - ``go-app/``, ``helmfile/python-app/``,
       ``helmfile/s3-crud-api/``, ``cc/monolith/``, ``scraper/``,
       ``lambda/``
     - Sample / production workloads; AWS Lambda services.
   * - **Cryptography**
     - ``portable-cryptor/``
     - Cross-cloud key import + envelope encryption.

Key invariants
==============

These invariants are referenced throughout the documentation and are
considered binding by the codebase:

1. **Auth headers are mutually exclusive.** Either ``X-DTE-Auth-Token``
   (legacy SLAuth) is set, OR ``X-DTE-ASAP`` + ``X-DTE-SCT`` (modern) are
   both set. ``X-DTE-GROUPS`` is required when using ASAP+SCT for the
   worker-side auth-provider exchange.
2. **Cluster registry is read with AWS Signature V4**, never SLAuth.
3. **Task queue ``dte-workflows`` is hardcoded in distributed-client**
   but the worker reads the env var (``INTEGRATION_REVIEW.md`` flags this
   as a *POTENTIAL MISMATCH* and recommends fixing the client to also use
   ``TEMPORAL_TASKQUEUE``).
4. **The ASI finalizer must be present** before namespace deletion or GCP
   IAM cleanup is skipped.
5. **PriorityClass ``gcp-critical-pods``** must be set on AI/compute
   workloads to avoid eviction.
6. **Cassandra replication factor 3** is mandatory for Temporal HA
   (per ``DEPLOYMENT_SUMMARY.md``).
7. **Knative serving step ordering** — domain config must precede
   serving-core (steps 6 → 7 in ``DEPLOYMENT_ORDER.md``).
