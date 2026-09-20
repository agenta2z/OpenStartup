==================================
Temporal topology
==================================

KITT runs Temporal as a shared workflow-orchestration substrate. This
page enumerates **every workflow, activity, task queue, and worker
process** that participates in the deployment.

Temporal cluster
=================

Deployed by ``helmfile/`` via the ``temporal`` Helm release:

* **Persistence**: Cassandra by default
  (``helmfile/cassandra-*.yaml`` manifests + ``cassandra-jmx-exporter``
  + ``cassandra-servicemonitor.yaml``). ``DEPLOYMENT_SUMMARY.md``
  mandates **replication factor 3**.
* **Alternate persistence**: Postgres + Redis under
  ``scraper/temporal-pg-redis/`` (used by the scraper subsystem).
* **Web UI**: ``temporal-web`` (proxied by ``dte-web/server.js``).
* **Default namespace**: ``default``. Additional namespaces created via
  ``helmfile/temporal-namespace-register-job.yaml``.
* **Ports**: frontend gRPC ``:7233``, web UI ``:8080``.
* **Tools image**: ``docker.atl-paas.net/kitt/temporal-tools:1.0.1``,
  used by jobs like ``temporal-keyspace-setup-job.yaml``,
  ``temporal-schema-setup-job.yaml``,
  ``temporal-schema-version-setup-job.yaml``,
  ``setup-temporal-schema-job.yaml``,
  ``delete-all-temporal-data-job.yaml``,
  ``update-cassandra-replication-factor-job.yaml``.

Task queues
============

.. list-table::
   :header-rows: 1
   :widths: 28 15 57

   * - Task queue
     - Worker
     - Workflows registered
   * - ``dte-workflows``
     - ``amp/distributed-worker`` and
       ``helmfile/dte/distributed-worker``
     - ``DistributedTaskExecutionWorkflow``, ``HelloWorldWorkflow``.
   * - ``kitt-runbooks``
     - ``kitt-runbooks/cmd/worker/main.go``
     - ``WorkflowK8sNodeCordoned``,
       ``WorkflowCyclopsCycleNodes``,
       ``WorkflowHighUnhealthyDeployments``.
   * - ``temporal-helloworld`` (sample)
     - ``helmfile/temporal-helloworld/worker-web-service/main.go``
     - ``HelloWorldWorkflow`` (sample app).
   * - ``scraper-task-queue``
     - ``scraper/temporal-pg-redis/`` worker
     - Scraper workflows (KEDA-scaled). The ``tctl`` command in
       ``helmfile/README.md`` (``tctl taskqueue describe --taskqueue
       scraper-task-queue``) is the canonical inspection example.

Workflow & activity inventory
==============================

DTE workflows (``amp/distributed-worker/main.go``)
---------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Symbol
     - Kind
     - Notes
   * - ``DistributedTaskExecutionWorkflow``
     - Workflow
     - Fan-out across ``request.ClusterNames``, validates ``TaskType``
       in ``{hello-world, health-check, service-discovery}``.
   * - ``HelloWorldWorkflow``
     - Workflow
     - Three-step sample workflow (Greeting → Processing → Formatting).
   * - ``HealthCheckActivity``
     - Activity
     - Inputs: ``map[string]string`` ({clusterName, authToken}).
   * - ``ServiceDiscoveryActivity``
     - Activity
     - Same input shape; output filtered later.
   * - ``HelloWorldActivity``
     - Activity
     - Sample.
   * - ``GreetingActivity`` / ``ProcessingActivity`` /
       ``FormattingActivity``
     - Activity
     - HelloWorld chain.
   * - ``ExecuteArgoWorkflowActivity``
     - Activity
     - Concrete worker for health-check / service-discovery — generates
       Argo YAML and submits it to the remote cluster.
   * - ``FilterServiceDiscoveryResultsActivity``
     - Activity
     - Strips internal fields from service-discovery output.

Helper functions inside the worker (non-activity)
---------------------------------------------------

* ``createK8sClient`` / ``createConfigFromClusterInfo`` /
  ``createClientsFromConfig`` — K8s client construction.
* ``logAuthenticatedUser`` / ``probeKubernetesAuth`` — auth diagnostics.
* ``filterGroupsByPattern`` / ``getClusterTokenFromAuthProvider`` /
  ``getRemoteClusterConfig`` — auth-provider exchange.
* ``createWorkflowViaAPI`` / ``getWorkflowStatus`` /
  ``getWorkflowMessage`` — Argo workflow CRUD via ``dynamic.Interface``.
* ``createArgoWorkflowYAML`` / ``createServiceDiscoveryWorkflowYAML`` /
  ``createHealthCheckWorkflowYAML`` — YAML generators.
* ``executeArgoWorkflow`` / ``waitForArgoWorkflowCompletion`` /
  ``getWorkflowOutput`` — submit-and-poll loop.
* ``extractGroupsFromToken`` / ``extractTokenIssuer`` /
  ``isSCTToken`` — token parsing.
* ``execCommand`` / ``execCommandWithOutput`` — shell-out (used in some
  diagnostics).
* ``initJSONLogger`` / ``getWorkflowLogger`` / ``getActivityLogger`` —
  ``slog`` integration.
* HTTP handlers on the worker process: ``healthHandler``, ``infoHandler``,
  ``workerStatusHandler``, ``taskQueueMetricsHandler``.

kitt-runbooks workflows
------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Workflow / activity
     - Notes
   * - ``WorkflowK8sNodeCordoned``
       (``kitt-runbooks/workflow_node_cordoned.go`` 107 LoC)
     - Diagnoses cordoned node, optionally deletes. Activities:
       ``ListCordonedNodesActivity``, ``CheckNodeStatusActivity``,
       ``CheckLogsForCordonAuditActivity`` (via Splunk),
       ``BuildDeleteNodeActivity``.
   * - ``WorkflowCyclopsCycleNodes``
       (``kitt-runbooks/workflow_cyclops.go`` 168 LoC)
     - Creates ``CycleNodeRequest`` in ``kube-system``. Inputs:
       ``TicketName`` (required, e.g. ``kube-xxxx``),
       ``nodeGroupLabelSelector`` (optional).
       Activities in ``activities_cyclops.go`` 198 LoC.
   * - ``WorkflowHighUnhealthyDeployments``
       (``kitt-runbooks/workflow_high_unhealthy_deployments.go`` 125 LoC)
     - Lists pods, groups by ReplicaSet → Deployment, computes
       unhealthy %. Activities in
       ``activities_high_unhealthy_deployments.go`` 184 LoC.
   * - Common
       (``kitt-runbooks/workflow_common.go`` 29 LoC)
     - ``WithDefaultActivityOptions()`` — StartToClose 2 min,
       ScheduleToClose 5 min, RetryPolicy {3 attempts, 1s initial, 2x
       backoff, 30s max}.
   * - K8s client
       (``kitt-runbooks/internal/k8sclient/`` 3 files, 657 LoC)
     - ``client.go`` 313 (cluster API calls), ``cluster.go`` 249
       (cluster info), ``auth_diag.go`` 95 (auth diagnostics).
   * - Splunk client
       (``kitt-runbooks/internal/splunk/client.go`` 140 LoC)
     - Used by ``CheckLogsForCordonAuditActivity``.
   * - Worker entry-point
       (``kitt-runbooks/cmd/worker/main.go`` 117 LoC)
     - Registers all three workflows and their activities on task queue
       ``kitt-runbooks``.

Test files (``kitt-runbooks/``)
--------------------------------

* ``activities_test.go`` 38 LoC
* ``activities_cyclops_test.go`` 28 LoC
* ``workflow_cyclops_test.go`` 51 LoC
* ``workflow_high_unhealthy_deployments_test.go`` 47 LoC
* ``workflow_node_cordoned_test.go`` 60 LoC
* ``internal/k8sclient/client_pod_node_test.go`` 78 LoC
* ``internal/k8sclient/cluster_test.go`` 203 LoC
* ``internal/splunk/client_test.go`` 177 LoC

Sample helloworld workflow (``helmfile/temporal-helloworld/``)
----------------------------------------------------------------

* ``workflow.go``, ``activities.go`` — sample workflow used as the
  KITT smoke-test.
* ``go-web-service/main.go`` — HTTP starter.
* ``worker-web-service/main.go`` — worker.
* ``charts/temporal-helloworld/`` — Helm chart with Deployment, HPA,
  Namespace.

Common Go code patterns
========================

1. **Logging** — every workflow/activity gets a ``*slog.Logger``
   produced by ``getWorkflowLogger`` / ``getActivityLogger`` so JSON log
   lines carry workflow ID, run ID, activity name. ``initJSONLogger``
   sets the global handler at startup.
2. **Activity options** — DTE worker uses Temporal default options
   for activities except where the YAML generators inject explicit
   timeouts; runbooks use ``WithDefaultActivityOptions()`` from
   ``workflow_common.go``.
3. **Determinism** — workflow code is purely functional; all I/O
   (K8s API calls, Splunk queries, S3 cluster registry reads) lives in
   activities.
4. **Cluster ID convention** — clusters use 4-letter codes
   (``mfc2``, ``fqk5``, ``cxjl``, ``ddev``) referenced throughout
   examples in READMEs and the inputs to ``WorkflowK8sNodeCordoned``.

Operational gotchas
====================

* ``temporal-tools`` image **must be present in the namespace's
  imagePullSecrets** — see the ``imagePullSecrets`` shuffle in
  ``helmfile/README.md``.
* Schema-version mismatches are detected by
  ``helmfile/check-schema-version-job.yaml``; run
  ``setup-temporal-schema-job.yaml`` to repair.
* Stuck workflows can be diagnosed via
  ``scraper/temporal-pg-redis/investigate-stuck-workflow.sh``.
* Force-deletion of terminating pods:
  ``scraper/temporal-pg-redis/force-delete-terminating-pods.sh``.
* CSRF on Temporal Web after upgrade: see
  ``scraper/temporal-pg-redis/FIX_TEMPORAL_WEB_CSRF.md``.
