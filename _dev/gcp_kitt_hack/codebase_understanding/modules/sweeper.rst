==================================
``sweeper/`` — pod-labelling controller
==================================

Purpose
=======

``sweeper/`` (7 files, Go) is a Kubernetes controller that reconciles the
``Sweeper`` CRD and labels pods across namespaces with a service-ID label.
The output feeds inventory, billing, and metrics pipelines.

Tech stack
==========

* **Go** with **controller-runtime**, **client-go**
* Standard Kubebuilder layout

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``sweeper/main.go``
     - 83
     - Manager bootstrap, leader election, port wiring
   * - ``sweeper/api/v1/sweeper_types.go``
     - 164
     - ``Sweeper`` types (Spec/Status, deepcopy)
   * - ``sweeper/controllers/sweeper_controller.go``
     - 207
     - Reconciler with ``loadConfig``, ``processNamespace``, ``labelAllPods``, ``labelNamespacePods``, ``labelPod``
   * - ``sweeper/sweeper-crd.yaml``
     - —
     - CRD manifest
   * - ``sweeper/sweepr-crd.yaml``
     - —
     - Older typo-named copy (cleanup candidate)

CRD definition
==============

* **Group:** ``platform.atlassian.com``
* **Kind:** ``Sweeper``
* **Version:** ``v1``
* **Spec:** ``name`` (string), ``schedule`` (cron string),
  ``resourceTypes`` ([]string), ``namespace`` (string)
* **Status:** ``lastRun``, ``nextRun`` (timestamps), ``conditions``
  (``[]metav1.Condition``)
* **Print columns** (kubectl): ``Schedule``, ``Last Run``, ``Next Run``

Reconciler behaviour
====================

``SweeperReconciler.Reconcile()``:

1. ``loadConfig()`` — pulls the Sweeper CR.
2. ``processNamespace()`` — iterates namespaces named in
   ``spec.namespace`` (or all if empty).
3. ``labelAllPods()`` / ``labelNamespacePods()`` — fan-out per namespace.
4. ``labelPod()`` — applies the service-ID label.

Operational details
===================

* **Leader election:** enabled via ``sweeper-controller-lock`` lease
* **Ports:** metrics ``:8080``, health ``:8081``, webhooks ``:9443``
* **No finalizer** documented — labels are non-destructive

Auth & RBAC
===========

* ClusterRole: ``pods/get,list,watch,patch`` and CRUD on the
  ``Sweeper`` CRD.

Integration with gcp_kitt
=========================

* **Reads from:** Kubernetes API only.
* **Coordinates with:** ``asi`` (shared label schema) so that
  service-account ↔ pod label correlation works for downstream
  inventory.
* **Replaces:** the legacy ``deploy/python/pod_label_sweeper.py``
  Python prototype.

Hazards
=======

* **Two CRD files** (``sweeper-crd.yaml`` and ``sweepr-crd.yaml``); apply
  the correct one — the typo'd file is a cleanup candidate.
* **No status conditions actually populated** in the reconciler observed
  here; observability is via logs.
* **Cron-style ``schedule`` is informational** — the controller does not
  itself enforce cadence; it relies on the K8s reconciliation loop.
