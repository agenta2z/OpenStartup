==================================
``argocd/`` — GitOps app-of-apps
==================================

Purpose
=======

``argocd/`` (16 files) is the GitOps control plane that bootstraps Argo CD
into a fresh cluster and then layers an *app-of-apps* hierarchy that
deploys ``forgeapp-controller``, the ``forgeapp-crd``, and per-cluster
patches. Once a cluster is bootstrapped, every subsequent change is
delivered via Git → Argo CD → cluster, instead of imperative
``helmfile apply``.

Tech stack
==========

* **Argo CD** (``Application``, ``AppProject``, ``ApplicationSet``)
* **Kustomize** for per-cluster overlays
* **Helm** for the controller charts under ``forge_containers/``

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Path
     - Role
   * - ``argocd/argocd-bootstrap/install-argocd-chart.sh``
     - Helm install of Argo CD itself
   * - ``argocd/argocd-bootstrap/kittz-system-applications-project.yaml``
     - Argo CD ``AppProject`` scoping the kittz-system apps
   * - ``argocd/argocd-apps/forgeapp-crd/forgeapp-crd-app.yaml``
     - Argo CD ``Application`` for the CRD-only chart (deploys first)
   * - ``argocd/argocd-apps/forgeapp-controller/forgeapp-controller-app.yaml``
     - Argo CD ``Application`` for the controller chart (deploys second)
   * - ``argocd/cluster-bootstrap/zt-xen-dev-dev-usw2-ndgn-app.yaml``
     - Per-cluster app-of-apps that points at ``cluster-apps/``
   * - ``argocd/cluster-apps/<cluster>/kustomization.yaml``
     - Per-cluster Kustomize patches
   * - ``argocd/README.md``
     - GitOps architecture & install order

Public surface
==============

None directly — Argo CD's UI/API is the surface; this directory is
declarative state.

Auth & RBAC
===========

* The ``AppProject`` scopes which destinations and source repos the apps
  can target (least-privilege).
* The bootstrap script installs Argo CD with default RBAC; harden via
  the upstream Argo CD docs before running in a multi-tenant cluster.

Build & deploy
==============

.. code-block:: bash

   # 1. Install Argo CD itself
   ./argocd/argocd-bootstrap/install-argocd-chart.sh
   # 2. Apply the per-cluster app-of-apps (everything cascades from here)
   kubectl apply -f argocd/cluster-bootstrap/zt-xen-dev-dev-usw2-ndgn-app.yaml

Integration with gcp_kitt
=========================

* **Sources:** ``forge_containers/helm-crd/`` (CRD chart) and
  ``forge_containers/helm/`` (controller chart)
* **Owns lifecycle of:** ``forgeapp-controller``, ``forgeapp-crd``, and
  any future controllers wired into the ``cluster-apps`` overlay tree
* **Replaces:** imperative ``helmfile apply`` once GitOps is enabled

Hazards
=======

* **CRD must be applied before controller.** Argo CD sync waves or
  explicit ``Application`` ordering enforce this; do not parallelise.
* **Auto-sync is OFF by default.** Stale resources may drift silently
  unless ``syncPolicy.automated`` is enabled per-Application.
* **Kustomize patches require exact ``apiVersion``/``kind`` matches** —
  silent no-op on typo.
* **Argo CD upgrades break Application APIVersion compatibility**
  every couple of releases; pin Argo CD version in the bootstrap chart.
