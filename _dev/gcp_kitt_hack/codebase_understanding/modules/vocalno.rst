==================================
``vocalno/`` — Volcano batch scheduler
==================================

Purpose
=======

``vocalno/`` (10 files; the ``c`` is a typo of *volcano*) deploys the
**Volcano** batch scheduler for GPU/CPU-burst workloads. It provides
node-level agents (GCP and AWS), a sample ``Volcano Job`` CRD, a
``Queue``, GCP ``ResourceQuota`` constraints, and bootstrap/userdata
scripts for cluster nodes.

Tech stack
==========

* **YAML** Kubernetes manifests, Volcano CRDs
* **Helmfile** for chart deploy
* **Bash** bootstrap & label scripts

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - File
     - Size
     - Role
   * - ``vocalno/helmfile.yaml``
     - —
     - Volcano Helm release
   * - ``vocalno/agent.yaml``
     - —
     - GCP volcano-agent SA + RBAC
   * - ``vocalno/aws-agent.yaml``
     - —
     - AWS volcano-agent variant
   * - ``vocalno/vcjob.yaml``
     - —
     - Sample ``Volcano Job`` CRD instance
   * - ``vocalno/cpu_burst.yaml``
     - —
     - Sample burst Deployment (nginx)
   * - ``vocalno/queue.yaml``
     - —
     - Job queue definition
   * - ``vocalno/gcp-quotas.yaml``
     - —
     - ``ResourceQuota`` scoped to ``system-node-critical`` /
       ``system-cluster-critical`` PriorityClasses
   * - ``vocalno/bootstrap.sh`` (or ``boostrap.sh`` typo)
     - 26.8 KB
     - Node init script
   * - ``vocalno/userdata.sh``
     - 16.7 KB
     - EC2 userdata
   * - ``vocalno/add-labels.sh``
     - —
     - Labels nodes for workload-class scheduling

Public surface
==============

* CRDs from upstream Volcano (``vcjob.batch.volcano.sh``,
  ``queue.scheduling.volcano.sh``)

Build & deploy
==============

.. code-block:: bash

   helmfile -f vocalno/helmfile.yaml apply
   kubectl apply -f vocalno/queue.yaml
   kubectl apply -f vocalno/vcjob.yaml
   kubectl get vcjob -A
   ./vocalno/add-labels.sh                # label new nodes

Integration with gcp_kitt
=========================

* **Independent scheduler** — runs alongside native K8s scheduler.
* **Quota interaction:** ``ai/gcp-critical-pods.yaml`` reserves the
  same ``system-*-critical`` priority classes; do not remove either
  side.

Hazards
=======

* **Filename typo** ``boostrap.sh`` (vs ``bootstrap.sh``) — both have
  appeared in the tree; confirm which is the live one before changing.
* **Quota scope is limited to system-critical priority classes** —
  user workloads must declare matching ``priorityClassName`` or be
  throttled.
* **AWS vs GCP agents** are separate manifests; do not apply both on
  the same node group.
* **Userdata.sh ships secrets** in some forks — review before applying
  to a fresh cluster.
