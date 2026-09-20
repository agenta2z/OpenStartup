==============================================
Architectural narrative — a walking tour
==============================================

This page tells the story of ``gcp_kitt`` end-to-end as if you were
shadowing a single ``dtecli runner start`` invocation from your laptop, all
the way to a labelled pod in a remote member cluster.

Setting the scene
==================

KITT (Kubernetes Infrastructure Tooling) is Atlassian's internal
multi-cluster Kubernetes platform. ``gcp_kitt`` is the **Google Cloud
Platform leg** of KITT — its job is to:

1. **Bring up new GKE clusters** with a fixed component stack (Knative,
   Istio/Kourier, Cassandra, Postgres, Redis, Elasticsearch, KEDA,
   Volcano, Kueue, Temporal, Prometheus, Grafana, Filebeat) using
   helmfile + ArgoCD GitOps. (See ``helmfile/``, ``argocd/``,
   ``helmfile/DEPLOYMENT_ORDER.md``.)
2. **Operate those clusters** through a fleet of small Go services and
   Operators (``amp/distributed-client``, ``amp/distributed-worker``,
   ``asi/``, ``sweeper/``, ``iam-sidecar/``, ``kitt-runbooks/``).
3. **Give operators a single CLI + Web UI** (``dtecli/``, ``dte-web/``)
   that abstracts the per-cluster operations behind workflow names like
   ``health-check``, ``service-discovery``, ``hello-world``, plus
   SRE runbooks (``K8sNodeCordoned``, ``CyclopsCycleNodes``,
   ``HighUnhealthyDeployments``).
4. **Observe** every workflow with structured JSON logs into Filebeat →
   Elasticsearch and Prometheus metrics scraped into 4 Grafana dashboards.

Below we walk through the request lifecycle for a representative call
``dtecli runner start --task health-check --cluster fqk5,mfc2`` (numbers
referenced in square brackets are file:LoC pointers verified on 2026-05-08).

Step 1 – CLI parses the command (``dtecli/``)
==============================================

The user invokes the binary that ``bin/build.sh`` ships:

.. code-block:: bash

   dtecli runner start --task health-check --cluster fqk5,mfc2

* **Entry point**: ``dtecli/src/cli/cli.ts`` (47 LoC) wires up the
  Commander.js root and lazily registers each command group:

  - ``cli/commands/auth/`` (``login.ts`` 250, ``token.ts`` 135,
    ``logout.ts`` 41) — issues + caches SLAuth/ASAP/SCT tokens via the
    Atlas plugin host.
  - ``cli/commands/cluster/`` (``status.ts`` 339, ``list.ts`` 235,
    ``utils.ts`` 168) — reads the local ``clusters.json`` registry.
  - ``cli/commands/runner/`` (``start.ts`` 100, ``status.ts`` 742 — by far
    the largest, ``stop.ts`` 51, ``list.ts`` 76,
    ``distributed-task.ts`` 120, ``utils.ts`` 104) — the *runner* abstraction
    around DTE workflows.
  - ``cli/commands/workflow/`` (``status.ts`` 1,012, ``start.ts`` 672,
    ``stop.ts`` 69, ``list.ts`` 78) — direct workflow operations.
  - ``cli/commands/config/`` (``set.ts`` 114, ``list.ts`` 31) — local
    config file management.

* **Shared library**: ``dtecli/src/lib/dte-client.ts`` (602 LoC) is the
  single HTTP client that knows how to attach the right auth headers and
  call the ``distributed-client`` API. ``health-check-parser.ts`` (1,124
  LoC) and ``service-discovery-parser.ts`` (363) are the response
  formatters used by ``runner status``.

* **AD-group resolution**: ``dtecli/src/lib/ad-groups.ts`` (114 LoC)
  resolves the user's ``kube-*`` Active Directory groups via the SLAuth
  ``rollcall`` API (the curl example in ``dte-web/README.md`` is the
  canonical reference).

The ``runner start`` command resolves to a single HTTP call:

.. code-block:: text

   GET https://distributed-client.mfc2.kitt-inf.net/api?action=health-check-start&cluster=fqk5,mfc2
   Headers:
     X-DTE-ASAP: <ASAP token from atlas slauth>
     X-DTE-SCT:  <SCT token from atlas slauth>
     X-DTE-GROUPS: kube-foo,kube-bar  (resolved via rollcall)

(See ``amp/DTE_DISTRIBUTED_CLIENT_APIS_AND_FLOWS.md`` for the canonical
list of accepted headers and actions.)

Step 2 – Optional Web UI hop (``dte-web/``)
=============================================

If the user prefers a browser, ``dte-web/`` provides the same surface:

* **Frontend**: ``dte-web/public/app.js`` is a single-page JS app served as
  a static asset.
* **Backend**: ``dte-web/server.js`` (1,241 LoC) is an Express server that
  proxies to ``distributed-client`` for workflow operations and to
  ``temporal-web`` for execution history.
* **Auth**: documented in ``dte-web/asap.md`` (3 LoC summary),
  ``dte-web/sct.md`` (88 LoC walkthrough including ``atlas slauth token``
  and ``rollcall`` curl examples), ``dte-web/auth-provider.md`` (1 LoC
  pointer), and ``dte-web/docs/auth.md``. The ASAP keypair is materialised
  via ``dte-web/asapkey-dtaske.yaml`` (12 LoC), Slauth gateway config in
  ``slauth.json``.
* **Deployment**: ``deployment.yaml`` 106 LoC, ``ingress.yaml`` 33,
  ``service.yaml`` 18, ``access-group.sd.yml`` 10. Image build via
  ``Makefile`` (218 LoC) with ``docker buildx build --platform
  linux/amd64,linux/arm64 -t docker.atl-paas.net/kitt/dte-web:<ts>``.

Step 3 – Distributed Client receives the request (``amp/distributed-client/main.go``)
=====================================================================================

The Go service binds at ``:8080`` and routes through:

* ``healthHandler`` (liveness)
* ``infoHandler`` (service info)
* ``executeDistributedTaskHandler`` (legacy unified handler)
* ``startWorkflowHandler`` (generic ``POST /start-workflow``)
* ``helloWorldStartHandler`` / ``helloWorldStatusHandler``
* ``unifiedAPIHandler`` — dispatcher for ``/api?action=…`` invocations,
  delegating to:

  - ``handleHelloWorldStartViaAPI`` / ``handleHelloWorldStatusViaAPI``
  - ``handleHealthCheckStartViaAPI``
  - ``handleServiceDiscoveryStartViaAPI``
  - ``handleGenericWorkflowStatusViaAPI``
  - ``handleWorkflowExecutionsViaAPI``

(See ``amp/distributed-client/main.go`` lines 1–1868; the inventory
above was confirmed by ``grep -E '^func '``.)

For ``action=health-check-start``:

1. ``extractAuthTokens(r)`` validates that **either** ``X-DTE-Auth-Token``
   (legacy SLAuth) **or both** ``X-DTE-ASAP`` and ``X-DTE-SCT`` are
   present. ``X-DTE-GROUPS`` is required for the worker-side auth-provider
   exchange when ASAP+SCT is used.
2. The ``cluster`` query parameter is split on commas, producing
   ``[]string{"fqk5","mfc2"}``.
3. A ``DistributedTaskRequest`` is built::

      type DistributedTaskRequest struct {
          ClusterNames []string `json:"clusterNames"`
          TaskType     string   `json:"taskType"`     // "health-check"
          AuthToken    string   `json:"authToken,omitempty"`
      }

4. ``StartWorkflowRequest`` is sent to Temporal:

   - ``workflowType``  = ``DistributedTaskExecutionWorkflow``
   - ``taskQueue``     = ``"dte-workflows"`` (hardcoded — see
     ``INTEGRATION_REVIEW.md`` "Task Queue Configuration" for the
     **POTENTIAL MISMATCH** call-out)
   - ``workflowId``    = ``health-check-multi-{timestamp}`` for >1 cluster,
     ``health-check-{cluster}-{timestamp}`` for single-cluster
   - ``namespace``     = ``"default"``
5. Temporal returns ``WorkflowID`` + ``RunID``, which are wrapped in a
   ``GenericWorkflowStartResponse`` and returned as JSON (HTTP 200) to
   ``dtecli``.

Logging uses the standard library ``slog`` configured by ``initJSONLogger()``
(structured JSON to stdout) so the response also lands in the Filebeat
pipeline.

Step 4 – Temporal Worker picks up the workflow (``amp/distributed-worker/main.go``)
==================================================================================

The worker binary in ``amp/distributed-worker/main.go`` (1,222 LoC)
registers two workflows and **seven activities** on task queue
``${TEMPORAL_TASKQUEUE}`` (default ``dte-workflows``):

**Workflows**

* ``DistributedTaskExecutionWorkflow`` — fan-out the requested task to
  every cluster in parallel using Temporal child contexts.
* ``HelloWorldWorkflow`` — three-step Greeting → Processing → Formatting
  chain used as smoke test.

**Activities**

* ``HealthCheckActivity(ctx, input map[string]string) (string, error)``
* ``ServiceDiscoveryActivity(ctx, input map[string]string) (string, error)``
* ``HelloWorldActivity(ctx, input map[string]string) (string, error)``
* ``GreetingActivity``, ``ProcessingActivity``, ``FormattingActivity``
  (HelloWorld chain)
* ``ExecuteArgoWorkflowActivity(ctx, cluster ClusterInfo, taskType string) (*ArgoWorkflowResult, error)``
* ``FilterServiceDiscoveryResultsActivity(ctx, output string) (string, error)``

For our health-check call, ``DistributedTaskExecutionWorkflow``:

1. Validates ``request.TaskType ∈ {"hello-world","health-check","service-discovery"}``.
2. For each ``cluster`` in ``request.ClusterNames``, schedules an
   ``ExecuteArgoWorkflowActivity`` (or the matching native activity) in
   parallel.
3. Aggregates results into ``DistributedTaskResponse``::

      type DistributedTaskResponse struct {
          RequestID     string
          TotalClusters int
          SuccessCount  int
          FailureCount  int
          Results       []ClusterTaskResult
          TotalDuration time.Duration
          Timestamp     time.Time
      }

4. Each ``ClusterTaskResult`` tags ``Metadata["taskType"]`` so the CLI's
   parser (``dtecli/src/lib/health-check-parser.ts``) can dispatch
   appropriately.

Step 5 – Activity reaches the remote cluster (``helpers.go`` + ``cluster_db.go``)
====================================================================================

The activity must talk to a *member* cluster (e.g. ``fqk5``), not the
local one. The path is implemented in
``amp/distributed-worker/helpers.go`` (1,134 LoC) and
``cluster_db.go`` (276 LoC):

1. **Cluster lookup** — ``cluster_db.go`` calls the cluster-registry S3
   bucket directly:

   .. code-block:: text

      https://kitt-cluster-registry.s3.amazonaws.com/latest/apis/clusterregistry.k8s.io/v1alpha1/namespaces/kube-system/clusters/<cluster-id>

   AWS Signature V4 is used (not SLAuth). The returned JSON populates
   ``ClusterInfo`` (master endpoint, CA cert, auth-provider URL, network
   path).
2. **Token exchange** — ``getClusterTokenFromAuthProvider(ctx, dteSlauthToken,
   cluster, groups, logger)`` POSTs the operator's SLAuth/ASAP+SCT token
   plus the ``X-DTE-GROUPS`` list (filtered through
   ``filterGroupsByPattern`` against ``cluster``-specific allow-lists) to
   the cluster's authentication provider. The response contains a
   short-lived bearer token scoped to the operator's ``kube-*`` AD groups.
3. **Token introspection** — ``isSCTToken``, ``extractTokenIssuer``,
   ``extractGroupsFromToken`` parse the JWT-like payload (no signature
   verify; that happens upstream).
4. **K8s client** — ``createK8sClient`` builds a ``rest.Config`` from
   ``ClusterInfo`` + the bearer token, then ``createClientsFromConfig``
   returns ``*kubernetes.Clientset`` and ``dynamic.Interface``. Auth
   diagnostics: ``logAuthenticatedUser``, ``probeKubernetesAuth``.
5. **Argo bridge** — ``createWorkflowViaAPI`` POSTs the YAML produced by
   ``createHealthCheckWorkflowYAML`` (or
   ``createServiceDiscoveryWorkflowYAML``) into the cluster as an Argo
   ``Workflow`` CR via the dynamic client. ``getWorkflowStatus`` polls
   until completion. ``getWorkflowOutput`` fetches the result.
6. **Filtering** (service-discovery only) —
   ``FilterServiceDiscoveryResultsActivity`` strips internal fields before
   returning to the parent workflow.

Step 6 – Result returns to the user
====================================

* The worker activity returns its ``ClusterTaskResult``.
* Temporal aggregates all per-cluster results into the workflow output.
* ``dtecli`` polls ``GET /api?action=health-check-status&workflowId=<id>``
  via ``handleGenericWorkflowStatusViaAPI``.
* The CLI parser (``health-check-parser.ts``) detects the workflow type
  by ID/metadata, parses the per-cluster ``output`` strings, and prints a
  formatted table to the operator's terminal.
* All hops emit structured JSON logs that the **Filebeat-DTE** Helm chart
  (``logging/charts/fluent-bit-dte``) forwards to Elasticsearch via the
  ingest pipelines defined under ``logging/`` (see
  ``logging/INGEST_PIPELINE_EXPLANATION.md``).
* Prometheus ``ServiceMonitors`` deployed under ``helmfile/`` scrape worker
  metrics; the **Temporal Grafana dashboard**
  (``monitoring/grafana-temporal-dashboard.json``) visualises task-queue
  depth, workflow latency, and failure rate. Recording rules are deployed
  by ``monitoring/update-prometheus-dtaske.sh``.

Where the operators fit in
============================

While DTE handles **explicit, on-demand** cluster operations triggered by
operators, two other Operator-pattern controllers run continuously inside
each cluster:

* **ASI Operator** (``asi/cmd/main.go``) — reconciles ``ASI`` resources
  (cluster-scoped). Each ``ASI`` represents a **logical service**. The
  ``Reconcile()`` loop:

  1. Ensures a K8s namespace exists.
  2. Creates a K8s ``ServiceAccount`` and annotates it with a GCP IAM
     service-account email.
  3. Calls ``RealIAMService`` (in ``internal/asicore/asi.go``) to bind the
     ``iam.workloadIdentityUser`` IAM policy on the GCP service account so
     that pods using the K8s SA can impersonate the GCP SA via Workload
     Identity. Required role: ``roles/iam.serviceAccountAdmin``
     (per ``asi/ReadME.MD``).
  4. Adds finalizer ``platform.atlassian.com/finalizer`` to ensure GCP
     IAM cleanup before namespace deletion.
* **Sweeper Operator** (``sweeper/main.go``) — reconciles ``Sweeper``
  resources. Each ``Sweeper.spec`` declares a cron ``schedule``,
  ``namespace``, and a list of ``resourceTypes`` to label. ``Reconcile()``
  calls ``processNamespace → labelAllPods → labelPod`` to write per-pod
  labels (typically ``serviceID``). Status fields ``lastRun``, ``nextRun``,
  ``conditions`` are surfaced via Kubebuilder additionalPrinterColumns.

Both operators are built from controller-runtime, deployed via standard
Helm charts under ``helmfile/``, and run in their own namespace with
leader election (``sweeper-controller-lock`` for sweeper).

Where the runbooks fit in
==========================

``kitt-runbooks/`` is a **separate Temporal worker** (entry point
``cmd/worker/main.go``, 117 LoC) that registers three SRE workflows on
task queue ``kitt-runbooks``:

1. ``WorkflowK8sNodeCordoned`` — diagnoses and (optionally) deletes a
   cordoned node. Activities: ``ListCordonedNodesActivity``,
   ``CheckNodeStatusActivity``, ``CheckLogsForCordonAuditActivity``,
   ``BuildDeleteNodeActivity``. Splunk client
   (``internal/splunk/client.go``, 140 LoC) queries the audit logs.
2. ``WorkflowCyclopsCycleNodes`` — automates the
   `Cyclops <https://github.com/atlassian-labs/cyclops>`_ ``CycleNodeRequest``
   creation against ``kube-system``. Required input ``TicketName``;
   optional ``nodeGroupLabelSelector``.
3. ``WorkflowHighUnhealthyDeployments`` — finds Deployments whose
   ``unhealthy/total`` percentage exceeds a threshold by listing pods,
   grouping by ReplicaSet then Deployment (handles both K8s native
   Deployments and CRD-managed pods).

Activities share ``WithDefaultActivityOptions()`` from
``workflow_common.go``: ``StartToClose 2 min``, ``ScheduleToClose 5 min``,
``RetryPolicy {3 attempts, 1s initial, 2x backoff, 30s max}``.

How everything is deployed
============================

The bootstrap chain is captured in ``helmfile/DEPLOYMENT_ORDER.md`` (11
explicit steps):

1. Knative Operator
2. CRDs
3. Network config
4. Network policies (webhook)
5. Network policies (ALB)
6. **Domain Config (CRITICAL — must precede step 7)**
7. Knative Serving Core
8. Kourier Operator
9. Istio configuration
10. ALB Ingress
11. Application layer

ArgoCD then watches ``argocd/cluster-apps/`` and syncs the application
layer (DTE worker, distributed-client, dte-web, kitt-runbooks worker, ASI
controller, sweeper, iam-sidecar, monitoring/logging stacks).

Why so many ``go.mod`` files?
==============================

Each Go-based component is its own module to keep build closures small and
to allow independent ``replace`` directives during development. The 10
distinct modules are: ``amp/``, ``helmfile/dte/``, ``asi/``, ``sweeper/``,
``iam-sidecar/``, ``go-app/``, ``forge_containers/``, ``kitt-runbooks/``,
``helmfile/temporal-helloworld/``, plus a supporting one used during
spike work. The ``amp/`` and ``helmfile/dte/`` modules are intentionally
**near-mirrors** because the production helm-deployed copy under
``helmfile/dte/`` is a vendored snapshot that diverges only in the
``cluster_db.go`` package layout (``helmfile/dte/pkg/cluster/cluster_db.go``
412 LoC vs. ``amp/distributed-worker/cluster_db.go`` 276 LoC) and added
``helmfile/dte/pkg/cluster``/``pkg/types``/``pkg/logger`` submodules.

End of narrative
=================

If you have read this far, you should now be able to:

* Trace any DTE-related issue from CLI to remote-cluster Argo workflow.
* Identify whether a given subdirectory is bootstrap, control-plane, ops,
  or analytics tier (see :doc:`01-multi-axis-matrix`).
* Pick the right :doc:`../modules/index` document for any deeper question.
