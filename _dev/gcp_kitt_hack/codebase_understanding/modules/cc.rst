==================================
``cc/`` — Confluence Cloud monolith manifests
==================================

Purpose
=======
Helm-templated Kubernetes manifests for deploying the **Confluence Cloud
monolith** onto a ``gcp_kitt``-managed cluster. Provides the canonical
shape of a heavyweight Atlassian product deployment (gateway, services,
rollouts, PDBs, KEDA-driven autoscaling, ASAP auth).

Layout
======
::

    cc/
      monolith/
        README.md                  # template/deploy commands
        gateway.yaml               # Contour HTTPProxy / Envoy config
        services.yaml              # Service definitions
        rollouts.yaml              # Argo Rollouts (canary / blue-green)
        pod-disruption-budgets.yaml
        scaled-objects.yaml        # KEDA autoscaling
        asap-key.yaml              # service-to-service auth
        micros-resources.yaml      # CPU/memory limits

Deployment
==========
Templated via Helm; example invocation from ``README.md``::

    HELM_DRIVER=configmap VERSION=1.0.0 helm template confluence-dev-us-11 .

Integrates with **Contour** ingress, **Argo Rollouts**, and **KEDA**
for traffic, progressive delivery, and autoscaling respectively.

Gotchas
=======
- Namespace is hardcoded in ``values.yaml`` — multi-environment use
  requires many ``--set`` overrides at template time.
- ``rollouts.yaml`` strategy assumes the cluster has Argo Rollouts
  installed; falls back to plain ``Deployment`` semantics otherwise
  (silent regression).
- ASAP key rotation is not automated; rotate via ``asap-key.yaml`` +
  manual reapply.
