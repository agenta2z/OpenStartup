==================================
Authentication & IAM
==================================

KITT-on-GCP separates *operator identity* (humans + their tokens) from
*workload identity* (pods + their GCP IAM service accounts). This page
documents the four authentication paths in scope:

1. Operator → distributed-client (HTTP API auth).
2. distributed-worker → member-cluster auth-provider (token exchange).
3. Pod → GCP API (Workload Identity via ASI + iam-sidecar).
4. Operator → KITT clusters via ``kubectl`` (separate, via
   per-cluster auth-provider direct).

1. Operator → distributed-client
=================================

Two mutually-exclusive token modes (as enforced by ``extractAuthTokens``
in ``amp/distributed-client/main.go``):

.. list-table::
   :header-rows: 1
   :widths: 16 84

   * - Mode
     - Headers
   * - Modern
     - ``X-DTE-ASAP`` + ``X-DTE-SCT`` (+ ``X-DTE-GROUPS`` required)
   * - Legacy
     - ``X-DTE-Auth-Token`` (single SLAuth token)

Token issuance for the operator:

* ``atlas slauth login`` (legacy interactive)
* ``atlas slauth token -a <audience> [-e <env>]`` (modern, prints token
  to stdout — used by the CLI)

ASAP key material storage:

* The DTE web service mounts an ASAP keypair via
  ``dte-web/asapkey-dtaske.yaml`` (12 LoC, points to a K8s ``Secret``).
* The ``Slauth gateway`` config is in ``dte-web/slauth.json`` (4 LoC).

2. distributed-worker → auth-provider exchange
================================================

Once the workflow is on the worker, the activity must talk to the
*member* cluster's API server. KITT uses a per-cluster
**auth-provider** service that exchanges the operator's ASAP+SCT (or
SLAuth) token for a short-lived bearer token bound to the operator's
filtered AD groups.

The flow inside ``getClusterTokenFromAuthProvider``
(``amp/distributed-worker/helpers.go``):

::

   POST  <ClusterInfo.AuthProviderURL>
   Headers:
      Content-Type: application/json
   Body:
      {
        "token":  "<operator ASAP+SCT or SLAuth>",
        "groups": "<filtered kube-* groups>"
      }
   200 OK
      { "kubeToken": "<short-lived bearer>" }

Group-filtering is handled by ``filterGroupsByPattern(groups, cluster,
logger)`` — the cluster's allow-list is encoded in ``ClusterInfo``.

Token introspection helpers (no signature verification at this layer):

* ``isSCTToken(token)``        — checks SCT-specific claim.
* ``extractTokenIssuer(token)`` — returns issuer for routing.
* ``extractGroupsFromToken(token)`` — returns embedded groups.

The exchanged ``kubeToken`` is then used in ``rest.Config.BearerToken``
for the ``client-go`` and ``dynamic`` clients
(``createConfigFromClusterInfo`` + ``createClientsFromConfig``).

3. Pod → GCP API (Workload Identity)
=====================================

Two cooperating components:

A. ASI Operator (``asi/``)
---------------------------

For each ``ASI`` resource (cluster-scoped, group ``platform.atlassian.com/v1``):

1. Create K8s ``Namespace`` if missing.
2. Create K8s ``ServiceAccount`` (named after ``ASI.spec.name``).
3. Annotate it with the GCP IAM SA email
   (``iam.gke.io/gcp-service-account``).
4. Call ``RealIAMService.bindIAMRole`` (in
   ``internal/asicore/asi.go``) which sets the
   ``roles/iam.workloadIdentityUser`` IAM policy on the GCP SA so that
   the K8s SA is allowed to impersonate it.
5. Add finalizer ``platform.atlassian.com/finalizer``.

GCP project ID is detected from the GCP **metadata server**
(``http://metadata.google.internal``) when the controller runs inside
GKE.

Required GCP role for the controller's own SA:
``roles/iam.serviceAccountAdmin`` (per ``asi/ReadME.MD``).

B. iam-sidecar (``iam-sidecar/``)
----------------------------------

A small Go HTTP server in 4 files (3 prod + 1 test, 750 LoC total):

* ``iam-sidecar.go`` (340 LoC) — HTTP server, ``/token`` and ``/idtoken``
  endpoints, token cache + refresh loop.
* ``gcp.go`` (110 LoC) — wraps
  ``iamcredentials.GenerateAccessToken`` and
  ``iamcredentials.GenerateIdToken``.
* ``iam-sidecar_test.go`` (73 LoC), ``gcp_test.go`` (227 LoC) — unit
  tests.

Pods that need GCP creds query ``http://localhost:<port>/token`` instead
of carrying GCP keys. The sidecar uses Workload Identity (from the SA
ASI bound) to mint downstream credentials.

4. Operator → cluster API server (kubectl path)
=================================================

Documented in ``dte-web/sct.md``. Operators typically run::

   atlas micros service show -s slauth-gateway
   atlas micros compute ssh -s amp-spike -e ddev
   sudo egrep 'CENTRIFY_CENTRIFY_CERT|CENTRIFY_CENTRIFY_KEY' \
        /opt/docker-compose.yml

…and use Centrify-issued mTLS certs for cluster API access. This path
is not used by DTE (which goes through the auth-provider exchange).

5. AD-group resolution (``rollcall``)
=======================================

Mentioned in ``dte-web/README.md`` and implemented in
``dtecli/src/lib/ad-groups.ts`` (114 LoC):

::

   curl -X GET "https://rollcall.<env>.atl-paas.net/api/v1/people/<user>" \
     -H "X-Slauth-Authorization: true" \
     -H "Authorization: SLAUTH <token>" \
     -H "Accept: application/json" \
     | jq -r '.memberOf[].name | select(startswith("kube-"))'

Only ``kube-*`` group memberships are forwarded to the auth-provider
exchange.

Cross-cluster RBAC inspection (operator help)
==============================================

To audit which AD groups have RBAC bindings on a cluster, the
``dte-web/README.md`` recommends::

   kubectl get clusterrolebinding -o json | jq '
     .items[]
     | select(.subjects[]? | select(.kind=="Group" and (.name | startswith("kube-"))))
   '

KMS / Cryptography sidebar
===========================

For data-at-rest concerns, ``portable-cryptor/`` provides:

* RSA-2048 keypair generation (``generate_rsa_keypair.py``) and
  public/private extraction (``extract_public_from_private.py``).
* GCP Cloud KMS import (``import_to_gcp.sh``, ``import_rsa_key.py``,
  ``import_rsa_key.sh``).
* AWS KMS import via Encryption SDK envelope wrapping
  (``import-aws-rsa.sh``, ``kms_encrypt_decrypt_esdk.py``,
  ``wrap_and_import_job2.sh``).
* Plain GCP/AWS KMS encrypt/decrypt
  (``kms_encrypt_decrypt.py``, ``encrypt.sh``, ``rsa_encrypt_decrypt.py``).
* ``key-rotations/`` — rotation playbooks (one folder per key version).
* Sample artefacts in repo: ``private_key.pem``, ``public_key.pem`` —
  **these are example/test material; never reuse in production**.
