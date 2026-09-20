==================================
``iam-sidecar/`` — GCP token sidecar
==================================

Purpose
=======

``iam-sidecar/`` (13 files, Go) is a tiny HTTP sidecar that issues
short-lived **GCP access tokens / ID tokens** to the workload sharing
its pod. Apps call ``GET /token`` instead of carrying long-lived
credentials.

Tech stack
==========

* **Go** (single binary)
* **GCP IAM Credentials API** — ``iamcredentials.GenerateAccessToken``
  and ``GenerateIdToken``

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - File
     - Size / LoC
     - Role
   * - ``iam-sidecar.go``
     - 11.7 KB
     - Main sidecar logic; token serving on localhost
   * - ``gcp.go``
     - 3.6 KB
     - GCP IAM API calls (access token + ID token)
   * - ``gcp_test.go``
     - —
     - Unit tests for GCP client
   * - ``iam-sidecar_test.go``
     - —
     - Unit tests for HTTP layer
   * - ``Dockerfile``
     - —
     - Container image
   * - ``examples/``
     - —
     - Reference integrations
   * - ``lisa-ingress.yaml``
     - —
     - Sidecar injection / Ingress reference
   * - ``go.mod`` / ``go.sum``
     - —
     - Go module pinning
   * - ``README.md``
     - —
     - Usage docs

Public surface
==============

* ``GET /token`` — returns a fresh GCP access token for the pod's
  identity. The endpoint binds to localhost so only co-resident
  containers can call it.

Auth & RBAC
===========

* **Workload Identity** — sidecar pod uses an annotated K8s SA bound
  to a GCP SA (provisioned by ``asi``).
* **GCP IAM:** ``roles/iam.serviceAccountTokenCreator`` on the GCP SA.

Build & deploy
==============

* Standard Dockerfile build
* Deployed via sidecar-injection patterns documented in
  ``lisa-ingress.yaml``

Integration with gcp_kitt
=========================

* **Provided by:** ``asi`` (creates the K8s SA + GCP SA pairing)
* **Consumed by:** any pod that needs GCP access without static creds —
  ``go-app``, ``scraper`` workers, etc.
* **Pattern complements:** GCP Workload Identity (in fact, it is built
  *on top* of Workload Identity)

Hazards
=======

* **Localhost-only binding** must be enforced — accidentally exposing
  the port to the cluster network leaks tokens.
* **Token TTL is short** (default 1 h for access tokens) — callers
  must re-fetch; do not cache beyond TTL.
* **GCP API rate limits** — the IAM Credentials API has per-project
  QPS limits; high-fan-out apps need a short token cache.
