==================================
``go-app/`` — sample Go service (Pub/Sub, GCS, Spanner)
==================================

Purpose
=======

``go-app/`` (9 files) is a reference Go service that exercises the major
GCP integrations enabled by the ``asi`` + ``iam-sidecar`` identity
foundation: Pub/Sub publish/subscribe, Cloud Storage read/write, Spanner
read/upsert, and Cloud Trace. It is the canonical "does Workload Identity
work end-to-end?" smoke test in the cluster.

Tech stack
==========

* **Go**
* **GCP client libraries:** Pub/Sub, Cloud Storage, Spanner, Cloud Trace
* **Workload Identity** for credentials (no static keys)

Inventory
=========

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - File
     - LoC
     - Role
   * - ``main.go``
     - 402
     - HTTP server with 14 handler functions
   * - ``go.mod`` / ``go.sum``
     - —
     - Module pinning (Pub/Sub, Storage, Spanner SDKs)
   * - ``Dockerfile``
     - —
     - Container image build
   * - ``Makefile``
     - —
     - Convenience build / push targets
   * - ``printjwt.py``
     - —
     - Helper to dump JWT (debugging)

Public surface — HTTP handlers (``main.go``)
============================================

* ``healthHandler`` — liveness/readiness
* ``checkHandler`` — environment / SA echo
* ``pubHandler`` — Pub/Sub publish
* ``subHandler`` — Pub/Sub subscribe (pull)
* ``ensureTopic()`` / ``ensureSubscription()`` — idempotent setup
* ``gcsWriteHandler`` / ``gcsReadHandler`` — Cloud Storage round-trip
* ``spannerReadHandler`` / ``spannerUpsertHandler`` — Spanner DB ops
* ``insertSinger()`` / ``readSingers()`` — Spanner schema demo

Auth & RBAC
===========

* **K8s SA** annotated with the GCP SA email (managed by ``asi``)
* **GCP IAM roles** required:

  - ``roles/pubsub.publisher`` + ``roles/pubsub.subscriber``
  - ``roles/storage.objectAdmin`` (or finer per bucket)
  - ``roles/spanner.databaseUser``
  - ``roles/cloudtrace.agent``

Build & deploy
==============

.. code-block:: bash

   make build     # go build
   make docker    # docker build
   make push      # push to registry
   # Deployment via deploy/helmfile.yaml release "go-app"

Integration with gcp_kitt
=========================

* **Identity from:** ``asi`` (K8s SA + GCP SA pair)
* **Optional sidecar:** ``iam-sidecar`` for token issuance
* **Deployed by:** ``deploy/helmfile.yaml``
* **Smoke-tested by:** ``deploy/test.sh`` (sanity ping)

Hazards
=======

* **printjwt.py** can leak credentials in logs — gate behind a
  feature flag.
* **Spanner emulator vs prod:** the handlers do not branch; misconfig
  hits production by default.
* **Unbounded Pub/Sub publishes** — backpressure depends on quota; add
  rate limiting before stress tests.
