==================================
``asi/`` — Atlassian Service Identity controller
==================================

Purpose
=======

``asi/`` (14 files, Go) is a Kubernetes controller that reconciles the
``ASI`` (Atlassian Service Identity) CRD. For each ASI it manages:

* the K8s ``ServiceAccount`` that workloads use as their pod identity
* the GCP IAM **service account** that the K8s SA federates to (Workload
  Identity)
* the IAM-policy bindings that grant the GCP SA the roles it needs

It is the foundation of every other module's "talk to GCP" story.

Tech stack
==========

* **Go** with **controller-runtime**
* **GCP IAM Admin API** (``iamcredentials``, ``iam.serviceAccountAdmin``)
* **Kubernetes ``client-go``**

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``asi/cmd/main.go``
     - 344
     - Manager bootstrap, controller registration, leader election
   * - ``asi/cmd/main_test.go``
     - 519
     - Manager-level tests
   * - ``asi/api/v1/asi_types.go``
     - 119
     - ``ASI`` Go types (Spec/Status, deepcopy)
   * - ``asi/api/v1/asi_types_test.go``
     - 177
     - Type tests
   * - ``asi/internal/asicore/asi.go``
     - 334
     - Core reconciliation logic; ``UpdateASI``, ``bindIAMRole``, ``RealIAMService``
   * - ``asi/internal/asicore/asi_test.go``
     - 266
     - Unit tests for core
   * - ``asi/asi-crd.yaml``
     - —
     - CRD manifest (group ``platform.atlassian.com``, kind ``ASI``)
   * - ``asi/ReadME.MD``
     - —
     - Required GCP IAM role: ``roles/iam.serviceAccountAdmin``

CRD definition
==============

* **Group:** ``platform.atlassian.com``
* **Kind:** ``ASI`` (plural ``asis``)
* **Version:** ``v1``
* **Spec:** ``name`` (string)
* **Status:** initially empty (no state tracking yet — listed as a gap)
* **Finalizer:** ``platform.atlassian.com/finalizer`` — deletes IAM
  bindings + GCP SA before allowing CR removal

Reconciler behaviour
====================

``ASIController.Reconcile()`` performs:

1. Project-ID detection from the GCP metadata server.
2. ``UpdateASI`` — creates the K8s namespace, the K8s ``ServiceAccount``,
   and annotates it with the GCP SA email.
3. ``bindIAMRole`` — sets the IAM policy on the GCP SA via
   ``RealIAMService`` (a wrapper over ``iamcredentials``).
4. Finalizer registration on first observation; cleanup on delete.

Auth & RBAC
===========

* **GCP:** ``roles/iam.serviceAccountAdmin`` on the project
* **K8s:** ``ClusterRole`` granting CRUD on ``serviceaccounts`` and
  the ``ASI`` CRD
* **Workload identity:** controller pod itself runs as a workload-identity
  bound SA so it can call IAM Admin API without static keys

Build & deploy
==============

* Standard Go build + Dockerfile (managed under ``deploy/charts/asi/``)
* Helm chart under ``deploy/`` Helmfile

Integration with gcp_kitt
=========================

* **Provides identity to:** every workload that needs GCP access
  (``go-app``, ``scraper``, ``k8s-metadata-collector``,
  ``iam-sidecar``)
* **Coordinates with:** ``sweeper`` (label schema overlap)
* **Tested via:** unit tests in ``asi/api/v1`` and ``asi/internal/asicore``

Hazards
=======

* **No status field** populated yet — observability of failed IAM binds
  must come from controller logs.
* **iam.serviceAccountAdmin is a powerful role** — over-broad if granted
  at project level; prefer per-SA grants.
* **Finalizer can hang** if the GCP SA is deleted out-of-band; manual
  ``kubectl patch`` to drop the finalizer is the documented escape
  hatch.
