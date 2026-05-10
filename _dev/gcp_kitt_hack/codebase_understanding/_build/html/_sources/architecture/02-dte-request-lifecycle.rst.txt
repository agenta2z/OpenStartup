==================================
DTE request lifecycle (deep)
==================================

This document is the canonical reference for **every step a DTE request
takes** from the operator's keyboard to the remote-cluster Argo workflow
output, with concrete file:LoC pointers verified on 2026-05-08.

Sources of truth
=================

* ``amp/DTE_DISTRIBUTED_CLIENT_APIS_AND_FLOWS.md`` (370 LoC) — accepted
  HTTP API surface and message flows.
* ``INTEGRATION_REVIEW.md`` (root) — cross-component compatibility
  matrix and the *POTENTIAL MISMATCH* call-out.
* ``amp/distributed-client/main.go`` (1,868 LoC).
* ``amp/distributed-worker/main.go`` (1,222 LoC).
* ``amp/distributed-worker/helpers.go`` (1,134 LoC).
* ``amp/distributed-worker/cluster_db.go`` (276 LoC).
* ``helmfile/dte/distributed-client/main.go`` (1,803 LoC) — production
  copy.
* ``helmfile/dte/distributed-worker/{main.go,helpers.go,cluster_db.go}``
  (1,178 / 1,134 / 441 LoC) — production copy with extended cluster_db.

Phase 0 — Operator authenticates
==================================

The user runs (interactively, once per session):

.. code-block:: bash

   atlas slauth login          # legacy single-token mode
   # or
   atlas slauth token -a rollcall -e staging   # modern ASAP

Behind the scenes the dtecli auth commands wrap this in friendlier output:

* ``dtecli/src/cli/commands/auth/login.ts`` (250 LoC)
* ``dtecli/src/cli/commands/auth/token.ts`` (135 LoC)
* ``dtecli/src/cli/commands/auth/logout.ts`` (41 LoC)
* ``dtecli/src/cli/commands/auth/index.ts`` (15 LoC) — wiring

The CLI also resolves AD-group membership via the rollcall API
(``dtecli/src/lib/ad-groups.ts`` 114 LoC), filtering for groups whose
name starts with ``kube-``. Equivalent curl in ``dte-web/README.md``::

   TOKEN=$(atlas slauth token -a rollcall)
   curl -X GET "https://rollcall.prod.atl-paas.net/api/v1/people/<user>" \
     -H "X-Slauth-Authorization: true" \
     -H "Authorization: SLAUTH $TOKEN" \
     -H "Accept: application/json" \
     | jq -r '.memberOf[].name | select(startswith("kube-"))'

Phase 1 — CLI builds the HTTP request
======================================

For ``dtecli runner start --task health-check --cluster fqk5,mfc2``:

* ``dtecli/src/cli/commands/runner/start.ts`` (100 LoC) parses flags.
* Delegates to ``dtecli/src/lib/dte-client.ts`` (602 LoC) which:

  - Loads endpoint from ``dtecli/src/lib/config.ts`` (135 LoC).
  - Attaches headers based on which token is cached:

    * **Modern**: ``X-DTE-ASAP`` + ``X-DTE-SCT`` + ``X-DTE-GROUPS``.
    * **Legacy**: ``X-DTE-Auth-Token``.
  - Issues ``GET /api?action=health-check-start&cluster=fqk5,mfc2``.

Phase 2 — distributed-client routes the request
================================================

In ``amp/distributed-client/main.go``:

1. ``main()`` registers HTTP handlers on a single mux.
2. ``unifiedAPIHandler`` (the ``/api`` route) inspects the
   ``action`` query parameter and dispatches to:

   * ``handleHealthCheckStartViaAPI`` for ``health-check-start``
   * ``handleServiceDiscoveryStartViaAPI`` for
     ``service-discovery-start``
   * ``handleHelloWorldStartViaAPI`` for ``hello-world-start``
   * ``handleGenericWorkflowStatusViaAPI`` for any ``…-status`` action
   * ``handleWorkflowExecutionsViaAPI`` for ``workflow-executions``
3. Inside the handler:

   a. ``extractAuthTokens(r)`` validates the auth invariants (mutually
      exclusive token sets).
   b. ``cluster`` query param is comma-split.
   c. A ``DistributedTaskRequest`` struct is populated.
   d. ``ExecuteWorkflow`` is called on the Temporal client with
      ``StartWorkflowOptions``::

         WorkflowOptions{
            ID:          "health-check-multi-<unix-ts>"   // multi-cluster
                       | "health-check-<cluster>-<unix-ts>",  // single
            TaskQueue:   "dte-workflows",                 // HARDCODED
            Namespace:   "default",
         }

      .. note::
         ``INTEGRATION_REVIEW.md`` flags the hard-coded task queue as a
         *POTENTIAL MISMATCH* with the worker (which reads
         ``TEMPORAL_TASKQUEUE``) and recommends fixing the client to use
         ``os.Getenv("TEMPORAL_TASKQUEUE")``.

   e. ``WorkflowID`` and ``RunID`` are returned in a
      ``GenericWorkflowStartResponse`` JSON to the CLI.

Phase 3 — Temporal hands the workflow to a worker
==================================================

The worker process (``amp/distributed-worker/main.go``) is registered on
``${TEMPORAL_TASKQUEUE}``. ``DistributedTaskExecutionWorkflow`` is invoked
with the ``DistributedTaskRequest`` payload.

The workflow body:

1. **Validates** ``request.TaskType`` is one of ``"hello-world"``,
   ``"health-check"``, ``"service-discovery"``.
2. **Fans out** by spawning N parallel selector branches, one per
   cluster.
3. For each branch:

   - Picks the activity by task type:

     * ``HealthCheckActivity(ctx, input map[string]string)`` for
       ``"health-check"`` (input keys ``clusterName``, ``authToken``)
     * ``ServiceDiscoveryActivity(ctx, input)`` for ``"service-discovery"``
     * ``HelloWorldActivity(ctx, input)`` for ``"hello-world"``
     * ``ExecuteArgoWorkflowActivity(ctx, cluster, taskType)`` is the
       common implementation for the first two — it generates the
       cluster-side Argo workflow YAML and runs it.
   - Wraps the call with default timeouts and retry policy.
4. **Aggregates** ``[]ClusterTaskResult`` into
   ``DistributedTaskResponse``.

Each ``ClusterTaskResult`` has::

   type ClusterTaskResult struct {
       ClusterName string
       Success     bool
       Output      string                 // raw activity output
       Error       string
       Duration    time.Duration
       Metadata    map[string]interface{}  // includes "taskType"
   }

Phase 4 — Activity executes against the remote cluster
=======================================================

This is the meat of the system. Implementation in
``amp/distributed-worker/helpers.go``:

Step A — Fetch ``ClusterInfo``
-------------------------------

``cluster_db.go`` issues a signed AWS S3 GET to::

   https://kitt-cluster-registry.s3.amazonaws.com/latest/apis/clusterregistry.k8s.io/v1alpha1/namespaces/kube-system/clusters/<cluster-id>

Returns JSON populating::

   type ClusterInfo struct {
       Name             string
       MasterEndpoint   string
       CACertPEM        string
       AuthProviderURL  string
       Network          string
       Provider         string  // "gcp" | "aws"
       Region           string
       // … additional metadata fields
   }

Step B — Token introspection
-----------------------------

``isSCTToken``, ``extractTokenIssuer``, ``extractGroupsFromToken`` parse
the operator's token (these are *unsigned* parses for routing only).

Step C — Filter groups
-----------------------

``filterGroupsByPattern(groups, cluster, logger)`` strips groups that do
not match the cluster's allow-list pattern.

Step D — Auth-provider exchange
--------------------------------

::

   POST <cluster.AuthProviderURL>
   Body: { token: <ASAP+SCT or SLAuth>, groups: <filtered> }

Returns a short-lived bearer token bound to the operator's filtered AD
groups. Implemented in
``getClusterTokenFromAuthProvider``.

Step E — Build K8s clients
---------------------------

``createConfigFromClusterInfo`` produces ``rest.Config`` with the bearer
token + CA cert. ``createClientsFromConfig`` returns
``*kubernetes.Clientset`` and ``dynamic.Interface``.

Optional auth diagnostics:
``logAuthenticatedUser``, ``probeKubernetesAuth``.

Step F — Generate Argo Workflow YAML
-------------------------------------

* ``createHealthCheckWorkflowYAML(cluster ClusterInfo)`` — produces the
  per-cluster Argo workflow that runs the cluster-side health probes.
* ``createServiceDiscoveryWorkflowYAML(cluster ClusterInfo)`` — produces
  the service-discovery workflow.
* ``createArgoWorkflowYAML(cluster, taskType)`` — generic dispatcher.

Step G — Submit and poll
-------------------------

``createWorkflowViaAPI(ctx, dynamicClient, workflowYAML, clusterName,
logger)`` posts the YAML as an Argo ``Workflow`` CR via the dynamic
client.

``waitForArgoWorkflowCompletion(ctx, cluster, workflowID)`` polls
``getWorkflowStatus`` and ``getWorkflowMessage`` until the workflow
reaches a terminal phase.

``getWorkflowOutput`` reads the output from the workflow status field.

Step H — Post-processing
-------------------------

For service-discovery only: ``FilterServiceDiscoveryResultsActivity(ctx,
output)`` strips internal fields (consistent with
``dtecli/src/lib/service-discovery-parser.ts`` 363 LoC expectations).

Phase 5 — Workflow result returns
==================================

The workflow output (``DistributedTaskResponse``) is persisted by
Temporal. The CLI either:

* Polled with ``GET /api?action=health-check-status&workflowId=<id>``
  via ``handleGenericWorkflowStatusViaAPI`` (which returns the full
  ``HelloWorldStatusResponse``-shaped envelope reused for all generic
  status queries).
* Or used Temporal's gRPC ``GetWorkflow`` if running directly inside the
  cluster.

The CLI's ``runner status`` command (742 LoC) recognises the workflow
type by ID/metadata and routes parsing to either:

* ``health-check-parser.ts`` (1,124 LoC) — produces a coloured table per
  cluster.
* ``service-discovery-parser.ts`` (363 LoC) — produces a service
  inventory output.

Headers and HTTP-level matrix
==============================

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Header
     - Required when
     - Notes
   * - ``X-DTE-ASAP``
     - Modern auth mode
     - JWT-style ASAP token from ``atlas slauth``.
   * - ``X-DTE-SCT``
     - Modern auth mode
     - Service Context Token. Always paired with ASAP.
   * - ``X-DTE-GROUPS``
     - With ASAP+SCT
     - Comma-separated ``kube-*`` AD groups; required by the worker for
       the auth-provider exchange.
   * - ``X-DTE-Auth-Token``
     - Legacy mode
     - Single SLAuth token. Mutually exclusive with the trio above.

Endpoint reference
===================

.. list-table::
   :header-rows: 1
   :widths: 38 12 50

   * - Endpoint
     - Method
     - Purpose
   * - ``GET /health``
     - GET
     - Liveness; returns ``{status, timestamp}``.
   * - ``GET /``
     - GET
     - Service info + endpoint discovery.
   * - ``GET|POST /api?action=hello-world-start&cluster=…``
     - GET/POST
     - Start ``DistributedTaskExecutionWorkflow`` with
       ``taskType="hello-world"``.
   * - ``GET /api?action=hello-world-status&workflowId=…``
     - GET
     - Status query.
   * - ``GET /api?action=health-check-start&cluster=…``
     - GET
     - Start health-check.
   * - ``GET /api?action=health-check-status&workflowId=…``
     - GET
     - Status query.
   * - ``GET /api?action=service-discovery-start&cluster=…``
     - GET
     - Start service-discovery.
   * - ``GET /api?action=service-discovery-status&workflowId=…``
     - GET
     - Status query.
   * - ``GET /api?action=workflow-executions&workflowId=…``
     - GET
     - Lists matching executions (``ListWorkflowExecutions`` if available,
       else describe latest run).
   * - ``POST /start-workflow``
     - POST
     - Generic workflow start with body ``{workflowType, workflowId?,
       taskQueue?, namespace?, input?, timeout?}``. **Auth is NOT
       enforced in this handler** — treat as internal/admin-only behind
       ingress policy.

Worker-side environment variables
==================================

(``amp/distributed-worker/main.go`` and Helm values)

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Env var
     - Purpose
   * - ``TEMPORAL_ADDRESS``
     - Temporal frontend service (e.g. ``temporal-frontend.temporal.svc:7233``).
   * - ``TEMPORAL_NAMESPACE``
     - Temporal namespace (default ``default``).
   * - ``TEMPORAL_TASKQUEUE``
     - Task queue to register on (default ``dte-workflows``).
   * - ``AUTH_PROVIDER_URL``
     - Per-cluster auth-provider URL (also encoded in ClusterInfo).
   * - ``AWS_REGION``
     - For Signature V4 to fetch from ``kitt-cluster-registry``.
   * - ``LOG_LEVEL``
     - ``slog`` level (defaults to ``INFO``).

Mirror copy under ``helmfile/dte/``
====================================

The ``helmfile/dte/`` tree is the **production-deployed** copy of the
DTE control-plane and is intentionally a near-mirror of ``amp/``. The
notable differences (verified by ``wc -l``):

* ``helmfile/dte/distributed-client/main.go`` is **1,803 LoC** (vs.
  ``amp/`` 1,868) — small drift in handlers/log messages.
* ``helmfile/dte/distributed-worker/main.go`` is **1,178 LoC** (vs.
  ``amp/`` 1,222) — same activities/workflows.
* ``helmfile/dte/distributed-worker/cluster_db.go`` is **441 LoC** (vs.
  ``amp/`` 276) — extended cluster registry handling.
* ``helmfile/dte/distributed-worker/cluster_db_test.go`` is **404 LoC**
  (vs. ``amp/`` 216) — extended test coverage.
* New packages under ``helmfile/dte/pkg/``:

  - ``pkg/cluster/cluster_db.go`` (412 LoC) — promoted ``cluster_db``
    into a dedicated package.
  - ``pkg/types/types.go`` (82 LoC) — same as ``amp/pkg/types/types.go``.
  - ``pkg/logger/logger.go`` (295 LoC) — same as ``amp/pkg/logger/logger.go``.

Treat the two trees as **logically equivalent for documentation
purposes**, and prefer ``helmfile/dte/`` as the source-of-truth for
production runs.
