==================================
``amp/`` — DTE distributed client & worker (Go)
==================================

Purpose
=======

``amp/`` (Atlassian Multi-cluster Platform) is the Go implementation of the
**Distributed Task Execution (DTE)** runtime. It is the production heart of
the system: ``distributed-client`` exposes an HTTP API that translates
incoming requests into Temporal workflows, and ``distributed-worker`` is the
Temporal worker that executes those workflows by spawning Argo Workflows on
remote Kubernetes clusters discovered through an S3 cluster registry.

A second copy of the worker exists under ``helmfile/dte/distributed-worker/``
(line-for-line identical to ``amp/distributed-worker/`` modulo the
``main.go`` size — 1222 vs 1178 LoC). The ``helmfile/`` copy is the version
actually packaged into the Helm chart; ``amp/`` is treated as the
source-of-truth and is the upstream that ``helmfile/dte`` mirrors.

Tech stack
==========

* **Go** (module: ``amp/``; ``go.mod`` 69 LoC)
* **Temporal SDK (``go.temporal.io/sdk``)** — workflow + activity authoring
* **Kubernetes ``client-go``** + **dynamic client** for Argo Workflow CRUD
* **Argo Workflows** as the runtime for the actual cluster-side payload
* **slog** structured JSON logging (custom ``initJSONLogger()``)

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``amp/distributed-client/main.go``
     - 1868
     - HTTP API server; converts REST calls to Temporal workflow invocations
   * - ``amp/distributed-worker/main.go``
     - 1222
     - Temporal worker; ``DistributedTaskExecutionWorkflow`` orchestrator + activities
   * - ``amp/distributed-worker/helpers.go``
     - 1134
     - Auth-token retrieval, remote-cluster config, exec helpers, workflow API
   * - ``amp/distributed-worker/cluster_db.go``
     - 276
     - In-memory cluster cache backed by S3 cluster registry
   * - ``amp/distributed-worker/main_test.go``
     - 395
     - Worker unit tests
   * - ``amp/distributed-worker/cluster_logging_test.go``
     - 276
     - Per-cluster logger tests
   * - ``amp/distributed-worker/logging_test.go``
     - 288
     - Logger plumbing tests
   * - ``amp/distributed-worker/cluster_db_test.go``
     - 216
     - cluster_db tests
   * - ``amp/distributed-worker/helpers_test.go``
     - 651
     - helpers tests
   * - ``amp/pkg/types/types.go``
     - 82
     - Shared Go types (``ClusterInfo``, ``DistributedTaskRequest`` etc.)
   * - ``amp/Makefile``
     - 294
     - Build / docker / push / kubectl-apply targets
   * - ``amp/helmfile.yaml``
     - 29
     - Local helmfile pinning ``../helmfile/dte/charts/dte``
   * - ``amp/DTE_DISTRIBUTED_CLIENT_APIS_AND_FLOWS.md``
     - 370
     - Spec: full API surface + EF-style cluster inventory model

Public surface — distributed-client (HTTP API)
==============================================

The HTTP handlers are explicit in ``main.go``:

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Path
     - Handler
     - Purpose
   * - ``GET /health``
     - ``healthHandler``
     - Liveness/readiness; returns ``HealthResponse``
   * - ``GET /info``
     - ``infoHandler``
     - Service metadata; returns ``ServiceInfoResponse``
   * - ``POST /execute-distributed-task``
     - ``executeDistributedTaskHandler``
     - Legacy direct task execution path
   * - ``POST /start-workflow``
     - ``startWorkflowHandler``
     - Generic workflow start entry-point
   * - ``POST /helloworld/start``
     - ``helloWorldStartHandler``
     - Demo hello-world workflow
   * - ``GET /helloworld/status``
     - ``helloWorldStatusHandler``
     - Demo hello-world status
   * - ``ANY /api/...``
     - ``unifiedAPIHandler``
     - Unified router; dispatches to ``handleHelloWorldStartViaAPI``, ``handleHealthCheckStartViaAPI``, ``handleServiceDiscoveryStartViaAPI``, ``handleGenericWorkflowStatusViaAPI``, ``handleWorkflowExecutionsViaAPI``

Auth-token plumbing is centralised in ``extractAuthTokens(r)`` which returns
three tokens: an ``ASAP`` token, a ``SLAuth`` token, and the DTE SLAuth
token used by ``getClusterTokenFromAuthProvider`` in the worker. Three-token
extraction is the canonical pattern for *every* DTE entry point.

Public surface — distributed-worker (Temporal)
==============================================

* **Workflow:** ``DistributedTaskExecutionWorkflow(ctx, DistributedTaskRequest) → *DistributedTaskResponse``
* **Workflow:** ``HelloWorldWorkflow(ctx, name string) → string``
* **Activities (registered):**

  - ``ExecuteArgoWorkflowActivity`` — main per-cluster execution
  - ``HealthCheckActivity``
  - ``ServiceDiscoveryActivity``
  - ``HelloWorldActivity``
  - ``GreetingActivity`` / ``ProcessingActivity`` / ``FormattingActivity`` (demo chain)
  - ``FilterServiceDiscoveryResultsActivity``

* **Helper free functions** (also reused by client):

  - ``createArgoWorkflowYAML(cluster, taskType)``
  - ``createServiceDiscoveryWorkflowYAML(cluster)``
  - ``createHealthCheckWorkflowYAML(cluster)``
  - ``executeArgoWorkflow(ctx, cluster, yaml)``
  - ``waitForArgoWorkflowCompletion(ctx, cluster, workflowID)``
  - ``getWorkflowOutput(ctx, workflowID)``

* **HTTP side-channel** on the worker: ``healthHandler``, ``infoHandler``,
  ``workerStatusHandler``, ``taskQueueMetricsHandler``.

Cluster discovery
=================

``ClusterDB`` (in ``cluster_db.go``) caches cluster metadata in-memory and
hydrates it from the S3 cluster registry::

   https://kitt-cluster-registry.s3.amazonaws.com/latest/apis/clusterregistry.k8s.io/v1alpha1/namespaces/kube-system/clusters/<cluster>

API:

* ``NewClusterDB() *ClusterDB``
* ``GetCluster(name) (*ClusterInfo, error)``
* ``AddCluster(*ClusterInfo)``
* ``ListClusters() []*ClusterInfo``
* ``isStale(*ClusterInfo) bool`` (TTL-based invalidation)
* ``fetchClusterFromRegistry(name)`` (S3 GET)
* ``parseClusterFromRegistry(name, resp)`` (decoder)
* Module-level wrappers: ``InitializeClusterDB``, ``GetClusterFromDB``,
  ``AddClusterToDB``, ``ListClustersFromDB``.

Auth & RBAC
===========

* **Inbound:** ASAP + SLAuth + DTE-SLAuth tokens (see ``extractAuthTokens``)
* **Outbound:** ``getClusterTokenFromAuthProvider`` exchanges DTE SLAuth for a
  per-cluster bearer token via ``AUTH_PROVIDER_URL`` env var
* **K8s API access on remote clusters:** ``getRemoteClusterConfig`` builds a
  ``rest.Config`` with the cluster-specific bearer; ``createClientsFromConfig``
  then yields a ``kubernetes.Clientset`` and ``dynamic.Interface``
* **S3 cluster registry:** anonymous public path, no creds required for read

Build & deploy
==============

``amp/Makefile`` (294 lines) provides the canonical lifecycle for both
binaries:

.. code-block:: bash

   make build-client            # go build cmd/distributed-client
   make build-worker            # go build cmd/distributed-worker
   make docker-client           # multi-arch docker build
   make docker-worker
   make push-client / push-worker
   make deploy-client / deploy-worker  # kubectl apply via helmfile
   helmfile -f amp/helmfile.yaml apply # references ../helmfile/dte/charts/dte

The ``amp/helmfile.yaml`` is intentionally tiny (29 lines) — it just pins
the local chart path so ``amp/`` developers can iterate without leaving the
sub-tree. The shipped chart lives at ``helmfile/dte/charts/dte``.

Integration with the rest of gcp_kitt
=====================================

* **Upstream callers:** ``dtecli`` and ``dte-web`` POST to
  ``distributed-client``'s ``/api`` and ``/start-workflow`` routes.
* **Downstream targets:** Argo Workflows on remote K8s clusters (one Argo
  Workflow per cluster per task).
* **Cluster registry:** S3 (``kitt-cluster-registry``) is the single source
  of truth for cluster metadata.
* **Auth fan-out:** ``AUTH_PROVIDER_URL`` (Lisa / SLAuth provider) issues
  per-cluster tokens.
* **Helm chart:** ``helmfile/dte/charts/dte`` deploys both binaries as
  Knative Services with Istio routing.
* **Mirror copy:** ``helmfile/dte/distributed-worker/`` is the in-repo
  shipping copy; do not edit it without also editing ``amp/``.

Hazards
=======

* **Code duplication:** ``amp/distributed-worker`` ↔
  ``helmfile/dte/distributed-worker``. Drift between the two is the most
  likely root-cause for "fix works locally, breaks in prod" tickets.
* **3-token soup:** Forgetting to forward any of the three auth tokens
  breaks the chain at a different layer (client, worker, or remote cluster);
  audit logs should be inspected at the layer that returned 401/403.
* **S3 registry staleness:** ``isStale`` uses a TTL — newly bootstrapped
  clusters may be invisible until the cache expires.
* **No exponential back-off documented** for ``executeArgoWorkflow`` polling —
  long-running Argo workflows can saturate the worker's HTTP client pool.
* **distributed-client may scale to zero** under Knative if traffic is bursty;
  first call after idle pays a cold-start penalty.
