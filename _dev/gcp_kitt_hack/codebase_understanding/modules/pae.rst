==================================
``pae/`` — Portable Async Engine (Kueue)
==================================

Purpose
=======
Kubernetes job-scheduling and admission-control layer built on `Kueue
<https://kueue.sigs.k8s.io/>`_. ``pae`` (Portable Async Engine) provides
``ClusterQueue`` / ``LocalQueue`` resources, workload admission, and a
visibility API so downstream consumers (DTE workers, Volcano jobs, Forge
batch tasks) get fair queueing rather than naive ``kubectl apply``.

Layout
======
::

    pae/
      helmfile.yaml                       # primary deployment entry-point
      .helmfile.d/environments.yaml       # per-env overrides
      charts/kueue-raw/Chart.yaml         # custom Kueue wrapper chart
      values/kueue-values.yaml            # controller config
      values/kueue-visibility-values.yaml # enable visibility API
      single-clusterqueue-setup.yaml      # example single-queue config
      visibility-api-setup.yaml           # API enablement
      README.md                           # full module documentation

Deployment
==========
``helmfile apply`` deploys Kueue (v0.8.x) into the ``kueue-system`` namespace.
Workloads (``Job``, ``Pod``) reference a ``LocalQueue``; ``LocalQueues`` delegate
to a ``ClusterQueue`` that owns the actual quota.

Key operational commands
========================
.. code-block:: bash

    helmfile apply
    kubectl get workloads -A -o wide
    kubectl get --raw \
      "/apis/visibility.kueue.x-k8s.io/v1alpha1/clusterqueues/cluster-queue/pendingworkloads" \
      | jq

Gotchas
=======
- Kueue 0.8.x exposes the visibility API at ``v1alpha1`` — pin clients to the
  matching version.
- Workloads stuck in ``Pending`` are almost always a zero-quota
  ``ClusterQueue``; check ``kubectl describe clusterqueue cluster-queue``.
- The visibility API requires the companion ``kueueviz`` UI for human
  inspection — see :doc:`pae-apps`.

Cross-references
================
- :doc:`pae-apps` — KueueViz dashboard and sample jobs.
- :doc:`vocalno` — alternate batch scheduler for GPU/CPU bursts.
