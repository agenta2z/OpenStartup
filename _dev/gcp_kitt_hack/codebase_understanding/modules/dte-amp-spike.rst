==================================
``amp-spike/`` — earliest DTE prototype (Express.js)
==================================

Purpose
=======

``amp-spike/`` is the *original* throw-away prototype that preceded the Go
``amp/`` implementation. It is a tiny Node.js Express server packaged as
an Atlassian Micros service; it lives in the tree for historical / template
reasons and is referenced by onboarding docs that demonstrate the
``atlas micros service deploy`` path.

Tech stack
==========

* **Node.js** (Express)
* **Atlassian Micros** for deployment (``atlas micros service deploy``)
* **Service Descriptor** ``amp-spike.sd.yml`` (32 lines)

Inventory
=========

7 files (verified — file count 7):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - File
     - LoC / size
     - Role
   * - ``server.js``
     - 34
     - Bare Express app — minimal route(s)
   * - ``Dockerfile``
     - 872 B
     - Container image definition
   * - ``Makefile``
     - 1419 B
     - Convenience targets (build / push / deploy)
   * - ``package.json``
     - 13
     - npm metadata (name, scripts, deps)
   * - ``amp-spike.sd.yml``
     - 32
     - Atlas Micros service descriptor
   * - ``README.md``
     - 24
     - Lists ``atlas micros`` invocation snippets
   * - ``.dockerignore``
     - 69 B
     - Build context exclusions

Public surface
==============

A single Express app listening on the Micros default port; no documented
HTTP routes beyond a health probe (the ``server.js`` is only 34 LoC).

Auth & RBAC
===========

The README references the **GCP workload-identity binding** required for
the service identity::

   gcloud projects add-iam-policy-binding gcp-ff58b41a \
     --member="principalSet://iam.googleapis.com/projects/635306927653/locations/global/workloadIdentityPools/kitt-auth-pool-f63e3a/group/dev-atlas-kube-platform-asapprod-micros:dtaske:kube-kittsune-dl-all-admin-dev" \
     --role="roles/container.developer"

The ASAP principal is
``dev-atlas-kube-platform-asapprod-micros:dtaske:kube-kittsune-dl-all-admin-dev``.

Build & deploy
==============

The README spells out the deploy commands explicitly:

.. code-block:: bash

   atlas micros resource list --service=amp-spike -o yaml -e ddev
   atlas micros service create -s dtaske --no-sd
   atlas micros accessgroup set --group dtaske -f access-group.sd.yml
   atlas micros service deploy --service amp-spike --env ddev --file amp-spike.sd.yml

Integration with gcp_kitt
=========================

* **Production status:** none — superseded by ``amp/distributed-client``.
* **Documentation value:** canonical example of how *any* gcp_kitt service
  joins the ``dtaske`` Micros service group + GCP workload-identity pool.
* **Cleanup pointer:** README links to
  https://hello.atlassian.net/wiki/spaces/MICROS/pages/167213240/Service+descriptor+reference#cleanup

Hazards
=======

* Out-of-date dependencies (last-touched May 2026 per filesystem mtimes).
* No tests, no CI hookup; treat as read-only reference.
* If used as a copy-paste template, beware that the access-group / IAM
  bindings here grant ``container.developer`` cluster-wide.
