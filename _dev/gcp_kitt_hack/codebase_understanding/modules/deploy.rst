==================================
``deploy/`` — secondary helmfile + sample / test workloads
==================================

Purpose
=======

``deploy/`` (78 files) is a *second-tier* helmfile that runs after
``helmfile/`` has provisioned the platform. Its scope is intentionally
narrower:

* Kafka cluster (``kafka.yaml``, 122 KB)
* Sample test pods that exercise GCP/AWS access, ingress modes, and
  internal vs external Service routing
* A Python ``pod_label_sweeper`` (precursor of the ``sweeper`` controller)

Tech stack
==========

* **Helmfile + Helm**
* **Kubernetes** raw manifests
* **GCP Workload Identity** (OIDC federation) — ``README.md`` documents
  the required ``gcloud auth login`` step

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - File
     - Role
   * - ``helmfile.yaml``
     - Top-level release set: awsauth, go-app, collector, asi, asimgr
   * - ``kafka.yaml``
     - Strimzi/Confluent Kafka cluster (122 KB)
   * - ``README.md``
     - GCP auth prerequisites + ``helmfile apply --skip-deps`` command
   * - ``test.sh``
     - End-to-end smoke test
   * - ``testpod.yaml``
     - Generic test pod
   * - ``testpubsvc.yaml``
     - Public Service smoke test
   * - ``testsvc.yaml``
     - Cluster-internal Service smoke test
   * - ``testaws-go.yaml`` / ``testaws-python.yaml``
     - Workload-identity smoke tests for AWS
   * - ``web-service.yaml``
     - Sample Knative web service
   * - ``internalsvc.yaml`` / ``internal-ingress.yaml``
     - Internal-ingress reference
   * - ``basic-ingress.yaml`` / ``managed-cert-ingress.yaml`` /
       ``testmanagedcert.yaml``
     - Ingress variants exercising managed-cert provisioning
   * - ``charts/``
     - Per-release Helm chart definitions
   * - ``python/sweeper.yaml`` / ``python/pod_label_sweeper.py``
     - Python prototype of the Sweeper CRD controller

Public surface
==============

None directly — this directory ships infra/test workloads, not services.

Auth & RBAC
===========

GCP **Workload Identity** with the ``--skip-deps`` flag prevents Helmfile
from re-resolving chart dependencies (the platform helmfile already did
that work). The README explicitly instructs::

   gcloud auth login
   helmfile apply --skip-deps    # in the kitt namespace

Build & deploy
==============

.. code-block:: bash

   cd deploy
   gcloud auth login
   helmfile apply --skip-deps
   ./test.sh

Integration with gcp_kitt
=========================

* **Sits on top of:** ``helmfile/`` (assumes Knative + Istio + ALB are up)
* **Sits below:** ``argocd/`` if the cluster has GitOps enabled
* **Cross-references:** ``asi/``, ``sweeper/`` (the Python proto here was
  the design seed for the Go controller in ``sweeper/``)

Hazards
=======

* **``--skip-deps`` is mandatory.** Forgetting it triggers a
  full-platform re-resolve that has caused multi-hour drift incidents.
* **Test ingresses are public.** The test ingress YAMLs allocate real
  ALB/managed certs; do not leave them applied between dev sessions.
* **Kafka manifest is huge** (122 KB) — diff-review carefully before
  apply.
* **Python sweeper is legacy.** Use ``sweeper/`` (Go controller) for any
  new namespace.
