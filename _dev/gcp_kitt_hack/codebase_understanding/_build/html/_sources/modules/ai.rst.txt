==================================
``ai/`` — critical-pod ResourceQuota
==================================

Purpose
=======
Single-file module containing a Kubernetes ``ResourceQuota`` scoped to
``system-node-critical`` and ``system-cluster-critical`` priority
classes. Ensures that critical system pods (Volcano scheduler, system
controllers) are never starved or evicted by higher-priority workloads.

Layout
======
::

    ai/
      gcp-critical-pods.yaml      # ResourceQuota manifest

Deployment
==========
Apply directly to ``volcano-system`` (or wherever critical pods live)::

    kubectl apply -f ai/gcp-critical-pods.yaml -n volcano-system

Cross-references
================
- :doc:`vocalno` — primary consumer of the critical priority classes.
