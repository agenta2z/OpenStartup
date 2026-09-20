==================================
``kitt-runbooks/`` — SRE runbooks as Temporal workflows
==================================

Purpose
=======

``kitt-runbooks/`` (55 files, Go) implements the day-to-day Kubernetes
operational runbooks as **Temporal workflows + activities**. Workflows
are submitted to the ``kitt-runbooks`` task queue and executed by a Go
worker that has K8s + Splunk client access.

Three workflows ship today:

1. **``K8SNodeCordoned``** — investigates a cordoned node, audits the
   reason via logs, optionally force-deletes.
2. **Cyclops Cycle Nodes** — cycles a node group via the
   ``CycleNodeRequest`` CRD.
3. **High Unhealthy Deployments %** — monitors deployment health by
   walking pods → ReplicaSets → Deployments (handling both native
   Deployments and CRD-managed pods).

Tech stack
==========

* **Go** with **Temporal SDK** (``go.temporal.io/sdk``)
* **client-go** + **dynamic** for K8s CRD CRUD
* **Splunk** SDK for log audits (custom client)
* **AWS Signature V4** for the cluster registry (S3-backed)

Inventory highlights
====================

.. list-table::
   :header-rows: 1
   :widths: 55 10 35

   * - File
     - LoC
     - Role
   * - ``cmd/worker/main.go``
     - 117
     - Worker bootstrap; registers workflows & activities
   * - ``workflow_node_cordoned.go``
     - 107
     - ``K8SNodeCordoned`` workflow
   * - ``workflow_node_cordoned_test.go``
     - —
     - Tests
   * - ``workflow_cyclops_test.go`` / ``activities_cyclops*.go``
     - —
     - Cyclops cycle workflow + activities
   * - ``workflow_high_unhealthy_deployments_test.go`` /
       ``activities_high_unhealthy_deployments.go``
     - —
     - Deployment-health workflow + activities
   * - ``activities.go``
     - —
     - Shared activities (e.g., ``ListCordonedNodesActivity``,
       ``CheckNodeStatusActivity``,
       ``CheckLogsForCordonAuditActivity``,
       ``BuildDeleteNodeActivity``)
   * - ``workflow_common.go``
     - —
     - ``WithDefaultActivityOptions`` (Start-to-Close 2 min,
       Schedule-to-Close 5 min, Retry 3× exponential)
   * - ``internal/k8sclient/client.go``
     - 313
     - Cluster API calls
   * - ``internal/k8sclient/cluster.go``
     - 249
     - Cluster info + remote-cluster auth
   * - ``internal/k8sclient/auth_diag.go``
     - 95
     - Auth diagnostics
   * - ``internal/k8sclient/client_pod_node_test.go``
     - 78
     - Tests
   * - ``internal/k8sclient/cluster_test.go``
     - 203
     - Tests
   * - ``internal/splunk/client.go``
     - 140
     - Splunk REST client
   * - ``internal/splunk/client_test.go``
     - 177
     - Tests
   * - ``cli/`` (TypeScript)
     - —
     - Optional CLI to start workflows; ``cli/src/cli.ts``,
       ``cli/vitest.config.ts``

Workflow inputs
===============

* **``K8SNodeCordoned``** — ``NodeName`` (optional), ``ClusterName``
  (4-letter, e.g. ``mfc2``), ``AuthToken`` (SLAuth JWT for remote
  clusters)
* **Cyclops Cycle Nodes** — ``TicketName`` (required, e.g.
  ``kube-xxxx``), ``nodeGroupLabelSelector`` (optional);
  creates a ``CycleNodeRequest`` in ``kube-system``.
* **High Unhealthy Deployments %** — ``DeploymentName`` (optional),
  ``ClusterName``, ``AuthToken``.

Activity options (shared)
=========================

Defined in ``workflow_common.go``::

   StartToClose:    2 minutes
   ScheduleToClose: 5 minutes
   RetryPolicy:     3 attempts, 1s initial, 2x backoff, 30s max

Auth & RBAC
===========

* **Remote cluster access** via ``AUTH_PROVIDER_URL`` env var (worker
  Helm chart's ``worker-values.yaml``)
* **Cluster registry on S3:** AWS Signature V4 (no SLAuth/Bearer)
* **K8s ClusterRole:** pod/exec, pod/logs, node patch, deployment list

Build & deploy
==============

* Standard ``Dockerfile`` + Helm chart at ``charts/kitt-runbooks/``
* Worker deployed in ``kitt-runbooks`` namespace; polls
  ``kitt-runbooks`` task queue.

Integration with gcp_kitt
=========================

* **Submitted by:** human SREs via the optional ``cli/`` or directly via
  Temporal Web
* **Targets:** any K8s cluster present in the S3 cluster registry (same
  registry consumed by ``amp/``)
* **Splunk integration** for cordon-audit log inspection
* **Tests** cover each workflow and the K8s client

Hazards
=======

* **AUTH_PROVIDER_URL outage** breaks every remote-cluster workflow —
  monitor the auth provider with the same severity as Temporal itself.
* **Force-delete in K8SNodeCordoned** is destructive; workflow inputs
  should require explicit confirmation flag.
* **Deployment-health workflow walks pods → ReplicaSets → Deployments**
  — high cardinality clusters can blow past the 5-minute
  schedule-to-close.
* **CRD-managed pods** are handled by the deployment-health workflow,
  but unknown CRDs may be missed; review per cluster.
