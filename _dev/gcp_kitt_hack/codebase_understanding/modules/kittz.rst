==================================
``kittz/`` — multi-region EKS deployment orchestrator (Node.js)
==================================

Purpose
=======
Standalone Node.js library / CLI for orchestrating Kubernetes
deployments across multiple AWS EKS regions. Wraps namespace creation,
RBAC bootstrap, health-check configuration, resource tracking, and
LoadBalancer provisioning. Sits **alongside** the helmfile platform
(:doc:`helmfile-platform`) — it is *not* invoked by Helmfile but is
sometimes called from CI pipelines that need imperative control.

Layout
======
::

    kittz/
      package.json           # npm dependencies
      README.md              # full feature documentation
      model.js               # data models
      k8s-deployment.js      # Kubernetes API wrapper

Capabilities
============
- Multi-region AWS EKS integration.
- Namespace + RBAC bootstrap.
- Health-check configuration (default ``80:80`` HTTP, ``/health``,
  30 s initial delay).
- Resource tracking: pods, deployments, services, ConfigMaps, secrets,
  PVCs.
- ``LoadBalancer`` service provisioning.
- Winston logging + metrics emission.

Operational commands
====================
.. code-block:: bash

    npm install
    npm start
    tail -f k8s-deployment.log
    kubectl get deployments -n kittz

Gotchas
=======
- AWS credentials are looked up via local profile, not assumed-role —
  pipeline runners need a real key.
- Health checks are HTTP-only; gRPC services need a wrapper endpoint.
- Cleanup on failure is **not** transactional — partial deployments
  must be reaped manually.
