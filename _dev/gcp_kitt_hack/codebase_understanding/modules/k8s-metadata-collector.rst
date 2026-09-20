==================================
``k8s-metadata-collector/`` — pod/node metadata → Kinesis
==================================

Purpose
=======

``k8s-metadata-collector/`` (8 files, Go) is a long-running Deployment
that periodically lists Kubernetes pods, nodes, and ServiceAccounts and
streams the snapshot to **AWS Kinesis** for downstream analytics.

Tech stack
==========

* **Go** with **client-go**
* **AWS SDK** (Kinesis writer)

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - File
     - Role
   * - ``main.go``
     - Entrypoint and 11 handler functions
   * - ``main_test.go``
     - Unit tests
   * - ``test.sh``
     - Local smoke harness
   * - ``Dockerfile``
     - Container build
   * - ``Makefile``
     - Build / docker / push targets

Function inventory (``main.go``)
================================

* ``getK8sClient()``
* ``getClusterIdentifier()``
* ``GetPodsAndNodes()``
* ``getServiceAccounts()``
* ``sendToKinesis()``
* ``collectAndSendMetadata()``  (main collection loop)
* ``healthCheckHandler()``
* ``handleShutdown()``

Public surface
==============

* HTTP ``/health`` — readiness/liveness probe
* No CRDs, no Temporal workflows.

Auth & RBAC
===========

* **K8s ClusterRole:** ``get,list`` on ``pods``, ``nodes``,
  ``namespaces``, ``serviceaccounts``
* **AWS IAM:** ``kinesis:PutRecord`` / ``PutRecords`` on the target
  stream

Build & deploy
==============

* Image built via ``Makefile``; deployed as a ``Deployment`` in the
  cluster being inventoried.

Integration with gcp_kitt
=========================

* **Reads:** the cluster's API server
* **Writes:** Kinesis stream (downstream of the gcp_kitt platform)
* **Identity:** uses ``asi``-provisioned SAs for AWS access via
  Workload Identity federation

Hazards
=======

* **Single Deployment, no leader election** — duplicate metadata
  records if scaled > 1.
* **Kinesis throttling** — large clusters can exceed shard throughput;
  use batching.
* **Schema evolution** — downstream consumers must tolerate new fields
  without breakage; rolling-upgrade should ship schema docs first.
