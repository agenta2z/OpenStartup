==================================
``forge_containers/`` — ForgeApp operator (Go)
==================================

Purpose
=======

``forge_containers/`` (67 files) is a Kubernetes operator + CRD that
deploys Atlassian Forge applications as containerised workloads on the
gcp_kitt platform. The operator watches the ``ForgeApp`` CRD and
generates a per-app ``ServiceAccount``, RBAC, and ``Deployment`` (with
sidecar injection) from the spec.

Two Helm charts ship with the operator:

* ``helm-crd/`` — CRD-only chart (deployed first via Argo CD sync wave)
* ``helm/`` — controller chart (deployed second)

Tech stack
==========

* **Go** (controller, ~400 LoC for the reconciler)
* **TypeScript** for deployment helpers
* **Helm** for packaging; **Kustomize** for per-cluster overlays
* **Argo CD** for sync ordering

Inventory highlights
====================

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - File
     - Role
   * - ``main.go``
     - Operator entrypoint
   * - ``controllers/forgeapp_controller.go``
     - Reconciler (~400 LoC)
   * - ``controllers/deployment.go``
     - Generates ``Deployment`` from ``ForgeApp`` spec
   * - ``api/v1alpha1/forgeapp_types.go``
     - ``ForgeApp`` CRD schema
   * - ``helm/Chart.yaml`` / ``helm/values.yaml``
     - Controller Helm chart
   * - ``helm-crd/Chart.yaml``
     - CRD-only chart (Argo CD wave 0)
   * - ``config/rbac/role.yaml``
     - Controller RBAC
   * - ``config/crd/kustomization.yaml``
     - CRD kustomization
   * - ``test/helmfile.yaml``
     - Local helmfile for integration tests
   * - ``test-app.yaml``
     - Sample ``ForgeApp`` CR
   * - ``yamls/deployment.yaml`` / ``yamls/deploy-compute.yaml`` /
       ``yamls/network-policy.yaml``
     - Reference manifests
   * - ``ARGOCD_SETUP.md``
     - Argo CD wiring guide
   * - ``KUBERNETES_DEPLOYMENT_COMPARISON.md``
     - Decision matrix vs. plain Deployments
   * - ``docs/forgeapp-crd-diagram.md``
     - CRD diagram

Public surface
==============

* **CRD:** ``ForgeApp`` (group/version per ``api/v1alpha1``)
* **Operator-managed objects:** per-app ``ServiceAccount``,
  ``RoleBinding``, ``Deployment``, optional sidecar containers

Reconciler behaviour
====================

For each ``ForgeApp``:

1. Watch ``ForgeApp`` CRs.
2. Generate / update a dedicated ``ServiceAccount`` and RBAC.
3. Build a ``Deployment`` from spec (image, replicas, env vars).
4. Patch in sidecar configurations (e.g., ``iam-sidecar``).

Auth & RBAC
===========

* **Operator ClusterRole** scoped to namespaces it manages
* **Per-app SA** isolated to its own namespace
* **Workload-identity binding** plumbed via ``asi``

Build & deploy
==============

.. code-block:: bash

   make install                                # Install CRD
   helm install forgeapp-controller ./helm \
        --namespace kittz-system
   kubectl apply -f test-app.yaml              # Sample ForgeApp
   kubectl get forgeapps -A
   kubectl logs -n kittz-system deployment/forgeapp-controller

Integration with gcp_kitt
=========================

* **Drives:** ``forge/`` reference applications (quiz-app, etc.) when
  packaged as ``ForgeApp`` CRs
* **Driven by:** ``argocd/`` (CRD app + controller app, in that order)
* **Identity:** ``asi`` provides the workload-identity foundation for
  per-app SAs

Hazards
=======

* **CRD/controller version mismatch** between ``helm-crd/`` and
  ``helm/`` breaks reconciliation silently — bump versions in lockstep.
* **Hard-coded sidecar injection patterns** — custom sidecars require
  Go code changes today.
* **No documented Helm upgrade strategy** — current SOP is
  delete-and-recreate during upgrades, which causes brief downtime.
* **Argo CD sync waves** must be configured; without them the controller
  Application can race ahead of the CRD Application.
