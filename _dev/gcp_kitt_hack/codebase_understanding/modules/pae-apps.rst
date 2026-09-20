==================================
``pae-apps/`` — KueueViz dashboard + sample jobs
==================================

Purpose
=======
Companion deployment to :doc:`pae` that surfaces queued, pending and admitted
``Workloads`` in a browser-friendly UI (``kueueviz``) and ships a small set of
example ``Job`` manifests used for smoke-testing the queue.

Layout
======
::

    pae-apps/
      helmfile.yaml                  # KueueViz Helm release
      charts/kueueviz-raw/           # custom kueueviz wrapper chart
      kueueviz-ingress.yaml          # ingress for the dashboard
      jobs.yaml                      # sample Job manifests
      creat-jobs.sh                  # job creation helper script
      KUEUE-CRDS.md                  # CRD reference notes

Deployment ordering
===================
Deploy after :doc:`pae` — kueueviz needs the Kueue visibility API enabled
(``values/kueue-visibility-values.yaml`` from ``pae/``).

Key operational commands
========================
.. code-block:: bash

    helmfile apply
    ./creat-jobs.sh
    kubectl get workloads -A -o wide

Gotchas
=======
- The dashboard talks directly to the visibility API; if Kueue is upgraded
  past ``v1alpha1`` the UI will break until kueueviz catches up.
- Ingress hostname is environment-specific — check
  ``kueueviz-ingress.yaml`` before exposing publicly.

Cross-references
================
- :doc:`pae` — backend Kueue install.
