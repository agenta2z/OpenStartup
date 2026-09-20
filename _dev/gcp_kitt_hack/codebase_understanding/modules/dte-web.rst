==================================
``dte-web/`` — DTE Web UI + REST proxy (Express.js)
==================================

Purpose
=======

``dte-web/`` is the browser-facing front-door for DTE. A single Express.js
server (``server.js``, 1241 LoC) serves both static UI assets and a REST
API that proxies to ``distributed-client``. Authentication is delegated
to a ``slauth-sidecar`` running in the same pod (SAML against Atlassian
SSO), with ASAP token signing performed in-process via ``httplease-asap``.

Tech stack
==========

* **Express.js**
* **httplease-asap** — ASAP JWT issuance / verification
* **axios** — proxy HTTP to ``distributed-client`` and Temporal Web
* **cors**
* **slauth-sidecar** (separate container) — SAML auth + header injection

Inventory (26 files)
====================

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - File
     - LoC
     - Role
   * - ``server.js``
     - 1241
     - Express app, all routes & auth middleware
   * - ``Dockerfile``
     - 23
     - Container image build
   * - ``Makefile``
     - 218
     - Build / docker / push / kubectl-apply targets
   * - ``deployment.yaml``
     - —
     - K8s Deployment with sidecar
   * - ``service.yaml``
     - —
     - Service exposing port 8081 (sidecar)
   * - ``ingress.yaml``
     - 33
     - ALB Ingress
   * - ``asapkey-dtaske.yaml``
     - —
     - ASAP private-key Secret (referenced by env)
   * - ``slauth.json``
     - 4
     - Sidecar config snippet
   * - ``helmfile/helmfile.yaml``
     - —
     - Optional helmfile-based deploy path
   * - ``README.md``
     - 299
     - Deployment & local dev guide
   * - ``auth-provider.md``
     - —
     - Architecture of the slauth-sidecar interaction
   * - ``asap.md``
     - —
     - ASAP key & header docs
   * - ``sct.md``
     - 88
     - Service Context Token notes
   * - ``docs/auth.md``
     - —
     - Additional auth notes
   * - ``package.json``
     - 19
     - npm metadata

Public surface — HTTP routes
============================

Routes inferred from ``server.js`` (``app.get`` / ``app.post``):

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Verb
     - Path
     - Behaviour
   * - GET
     - ``/health``
     - Liveness; bypasses auth
   * - GET
     - ``/api/info``
     - Service metadata
   * - GET
     - ``/api/auth/token``
     - Returns the current bearer token (extracted from sidecar headers)
   * - GET
     - ``/api/auth/status``
     - Authentication state probe
   * - POST
     - ``/api/workflows/start``
     - Proxies to ``distributed-client`` ``/start-workflow``
   * - GET
     - ``/api/workflows``
     - Lists workflows
   * - GET
     - ``/api/workflows/:id/status``
     - Workflow status
   * - POST
     - ``/api/workflows/:id/terminate``
     - Hard terminate
   * - POST
     - ``/api/workflows/:id/cancel``
     - Graceful cancel
   * - GET
     - ``*``
     - SPA fallback to ``public/index.html``

Auth & RBAC
===========

* **slauth-sidecar** (separate container, port 8081) authenticates the
  user via SAML and injects ``x-slauth-*`` headers (user/email/groups)
  before forwarding to dte-web on port 8080. The known gap (called out
  in ``auth-provider.md``) is that the SAML plugin does **not** currently
  inject a JWT bearer or ``x-slauth-staff-context`` header — endpoints
  expecting a Bearer must build it via ASAP.
* **ASAP** — issued in-process using env vars
  ``ASAP_PRIVATE_KEY`` / ``ASAP_ISSUER`` / ``ASAP_KEY_ID`` /
  ``ASAP_AUDIENCE`` (private key sourced from ``asapkey-dtaske``).
* **ROLLCALL_URL** — secondary auth endpoint (Atlassian Rollcall) for
  allow-listing.

Build & deploy
==============

.. code-block:: bash

   # Local dev
   npm install
   PORT=8080 \
     DTE_CLIENT_URL=http://distributed-client.fqk5.kitt-inf.net \
     TEMPORAL_WEB_URL=http://temporal-web.fqk5.kitt-inf.net \
     ASAP_PRIVATE_KEY=... ASAP_ISSUER=... ASAP_KEY_ID=... ASAP_AUDIENCE=... \
     npm start

   # Image build & push (Makefile)
   make build push

   # Manual K8s apply
   kubectl apply -f deployment.yaml -f service.yaml -f ingress.yaml

The README also documents a ``docker buildx build --platform linux/amd64,linux/arm64``
multi-arch path tagged ``docker.atl-paas.net/kitt/dte-web:<timestamp>`` and ``:latest``.

Integration with gcp_kitt
=========================

* **Calls:** ``distributed-client``, Temporal Web, Rollcall
* **Sidecar:** ``slauth-sidecar`` co-located in the same pod; Service port
  8081 routes through the sidecar
* **Helm chart:** optional ``helmfile/`` directory for Helmfile-driven
  deploys; primary path is hand-applied YAML via Makefile
* **Namespace:** typically ``dtaske``

Hazards
=======

* **JWT injection gap** — endpoints expecting Bearer fail unless ASAP is
  issued in-process; this surface is the most common production 401
  source.
* **Port mismatch** — Service exposes 8081 (sidecar), backend listens on
  8080; mis-routed traffic *bypasses* auth entirely.
* **CORS default** — broad CORS may accept any origin in production
  unless overridden.
* **ASAP secret rotation** — ``asapkey-dtaske`` Secret must be rotated in
  lockstep with the issuer registration; mis-rotation breaks every
  outbound call.
* **Hard-coded fqk5 defaults** — multi-cluster operation requires every
  caller to set ``DTE_CLIENT_URL`` and ``TEMPORAL_WEB_URL`` explicitly.
