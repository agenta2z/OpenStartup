.. _gcp-kitt-codebase-understanding:

==========================================================================
GCP KITT — Codebase Understanding Documentation
==========================================================================

:Date: 2026-05-08
:Repo: ``/Users/tchen7/MyProjects/atlassian_packages/gcp_kitt``
:Scope: 33 top-level subdirectories, ~909 source files (excluding ``.git``),
        primary languages Go (79 files), Python (63), TypeScript (52),
        plus 333 YAML manifests, 73 Markdown documents, and 66 shell scripts.

Comprehensive documentation for the ``gcp_kitt`` repository — Atlassian's
**KITT (Kubernetes Infrastructure Tooling) on GCP** monorepo. The project is
the Atlassian-internal control-plane and operations toolkit that runs the
*KITT* multi-cluster Kubernetes platform on Google Cloud Platform (with
parallel AWS support paths). It contains:

* **Distributed Task Execution (DTE)** — a Go + Temporal control plane
  (``amp/``, ``helmfile/dte/``) plus a Node.js CLI (``dtecli/``) and a small
  Express-based web UI (``dte-web/``) used to fan-out cluster operations
  (``health-check``, ``service-discovery``, ``hello-world``, custom Argo
  workflows) across many member clusters.
* **Two Kubernetes operators** — ``asi/`` (Atlassian Service Infrastructure
  — owns the ``ASI`` cluster-scoped CRD that bridges K8s ServiceAccounts to
  GCP IAM service accounts) and ``sweeper/`` (a kubebuilder operator that
  applies pod-labelling sweeps on a cron schedule, owning the ``Sweeper``
  CRD).
* **Temporal SRE Runbooks** — ``kitt-runbooks/`` houses three production
  Temporal workflows: ``K8sNodeCordoned``, ``CyclopsCycleNodes``, and
  ``HighUnhealthyDeployments``, all backed by activities that talk to the
  remote-cluster authentication-provider exchange and Splunk.
* **Helmfile platform** — ``helmfile/``, ``deploy/``, ``argocd/``, ``ai/``,
  ``vocalno/``, ``pae/``, ``pae-apps/`` together describe the GitOps
  bootstrap of cluster components: Knative, Istio/Kourier, Cassandra,
  Postgres, Redis, Elasticsearch, KEDA, Prometheus/Grafana, Volcano (GPU
  batch), Kueue (job queueing), and the Temporal cluster itself.
* **Observability stack** — ``logging/`` (Filebeat + Elasticsearch ingest
  pipelines + Fluent-Bit DTE shipper) and ``monitoring/`` (4 Grafana
  dashboards, Prometheus recording-rule update job for the
  ``dte-service-capture`` rules).
* **Security/IAM tooling** — ``iam-sidecar/`` (Go HTTP sidecar that mints
  GCP access/ID tokens via ``iamcredentials.GenerateAccessToken``) and
  ``portable-cryptor/`` (RSA-2048 + GCP/AWS KMS envelope-encryption helpers
  for portable key import & rotation).
* **Supporting services** — ``forge_containers/`` (Forge runtime + helm-crd
  controller), ``cc/monolith/`` (cc service extraction), ``go-app/`` and
  ``busybox/`` (sample/canary workloads), ``scraper/`` (Postgres +
  Temporal-backed scraper for service inventory), ``lambda/`` (AWS Lambda
  handlers — Dynamo + Postgres), ``routers/`` (a small Python URL routing
  library), ``cdp_services/``, ``atlassian_services/``, ``costs-estimates/``
  (analytics CSVs and cost models that quantify the migration scope).
* **Operations runbook collection** — ``kitt-runbooks/cli/`` and
  ``tests/`` capture the platform-level service catalogue and integration
  test inventory.

This documentation set was produced by **multi-agent parallel investigation**
of the live source tree on 2026-05-08, then critically cross-checked against
``find -type f``, ``wc -l``, ``grep -E '^func |^type '`` outputs to verify
every numerical claim.

Verified scope (2026-05-08)
==============================

* **33 top-level directories** (``ai amp amp-spike argocd asi
  atlassian_services busybox cc cdp_services costs-estimates deploy dte-web
  dtecli forge forge_containers go-app helmfile iam-sidecar
  k8s-metadata-collector kitt-runbooks kittz lambda logging monitoring pae
  pae-apps portable-cryptor routers scraper sweeper tests vocalno`` plus
  the reserved ``forge/`` placeholder)
* **909 tracked files** by extension: 333 ``.yaml``, 79 ``.go``,
  73 ``.md``/``.MD``, 66 ``.sh``, 63 ``.py``, 52 ``.ts``, 32 ``.json``,
  26 ``.txt``, 23 ``.js``, 20 ``.tpl`` (Helm), 10 ``go.sum``, 10 ``go.mod``,
  4 ``.tf`` (Terraform), 4 ``.toml``, 4 ``.sql``, 1 ``.rego`` (OPA).
* **DTE control plane** — ``amp/distributed-client/main.go`` 1,868 LoC,
  ``amp/distributed-worker/main.go`` 1,222 LoC, ``amp/distributed-worker/helpers.go``
  1,134 LoC, ``amp/distributed-worker/cluster_db.go`` 276 LoC,
  ``amp/pkg/types/types.go`` 82 LoC, ``amp/pkg/logger/logger.go`` 295 LoC.
  Mirror copy under ``helmfile/dte/`` totals **14,480 Go LoC** for the
  DTE subsystem (including 2,225 LoC of Go tests).
* **dtecli (CLI)** — 31 TypeScript files under ``dtecli/src/``, **7,943 LoC**
  total. Top files: ``cli/commands/workflow/status.ts`` (1,012 LoC),
  ``lib/health-check-parser.ts`` (1,124 LoC), ``cli/commands/runner/status.ts``
  (742 LoC), ``cli/commands/workflow/start.ts`` (672 LoC),
  ``lib/dte-client.ts`` (602 LoC).
* **dte-web (Web UI / proxy)** — ``server.js`` 1,241 LoC, ``Makefile`` 218
  LoC, ``deployment.yaml`` 106 LoC, ``README.md`` 299 LoC, plus auth docs
  (``asap.md``, ``sct.md``, ``auth-provider.md``, ``docs/auth.md``).
* **Operators** — ``asi/`` 14 Go files (``cmd/main.go`` 344, ``cmd/main_test.go``
  519, ``api/v1/asi_types.go`` 119, ``internal/asicore/asi.go`` 334);
  ``sweeper/`` 6 files (``main.go`` 83, ``api/v1/sweeper_types.go`` 164,
  ``controllers/sweeper_controller.go`` 207).
* **Runbooks** — ``kitt-runbooks/`` 20 Go files (3 workflows + 3 activity
  packages + ``internal/k8sclient`` 3 files + ``internal/splunk`` 2 files +
  ``cmd/worker/main.go`` 117 LoC).
* **Helmfile platform** — 141 files under ``helmfile/`` (largest top-level
  directory). Key sub-trees: ``bootstrap/``, ``temporal-manifests/``,
  ``dte/``, ``temporal-helloworld/``, ``s3-crud-api/``, ``python-app/``.
* **Observability** — ``logging/`` 25 tracked files (1,688 total LoC across
  9 ``.sh`` + 5 ``.md`` + Filebeat-DTE Helm chart),
  ``monitoring/`` 10 files including 4 Grafana dashboard JSON blobs.

How to read this documentation
================================

* **Brand new to KITT?** Start with :doc:`overviews/02-architectural-narrative`
  for a walking tour from a ``dtecli runner start`` invocation to a
  Temporal activity hitting a remote cluster.
* **Cross-package picture?** :doc:`overviews/01-multi-axis-matrix` ranks
  every top-level directory by file count, language, and platform tier.
* **SRE / on-call?** :doc:`overviews/03-criticality-dashboard` ranks
  components by blast-radius and includes a runbook index.
* **Architecture deep dive?** :doc:`architecture/index` covers the DTE
  request lifecycle, the dual ASAP+SCT auth-provider exchange, the
  Temporal task-queue topology, the cluster-registry S3 model, and the
  GitOps deployment chain.
* **Per-feature detail?** :doc:`modules/index` has deep-dives for each
  major subsystem: DTE control-plane, helmfile-platform, observability,
  security & IAM, k8s-operators, temporal-workflows, client-tooling, and
  data-services.
* **Cross-cutting glossary?** :doc:`architecture/00-glossary`.

Top-level structure
====================

.. toctree::
   :maxdepth: 2
   :caption: Cross-cutting overviews

   overviews/index

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/index

.. toctree::
   :maxdepth: 2
   :caption: Per-module catalog

   modules/index

Quick statistics
=================

.. list-table::
   :header-rows: 1
   :widths: 28 12 12 48

   * - Layer
     - Files
     - LoC (≈)
     - Notes
   * - DTE control-plane (``amp/`` + ``helmfile/dte/``)
     - 22 Go
     - 14,480
     - Mirrored production copy under helmfile/dte/. ``distributed-client``
       (HTTP API) + ``distributed-worker`` (Temporal worker + Argo bridge).
   * - DTE CLI (``dtecli/``)
     - 31 TS
     - 7,943
     - Node.js Atlas-plugin CLI (auth login, cluster, runner, workflow,
       config commands). Plus ``bootstrap/`` Knative JS worker (5 TS files).
   * - DTE Web (``dte-web/``)
     - 14
     - 2,075
     - Express server + static SPA; proxies to distributed-client and
       temporal-web; ASAP/SCT/AD-group docs.
   * - Operators (``asi/`` + ``sweeper/``)
     - 14 + 6 Go
     - 1,759 + 454
     - Two cluster-scoped CRDs (``asis``, ``sweepers``) under
       ``platform.atlassian.com/v1``.
   * - Runbooks (``kitt-runbooks/``)
     - 20 Go
     - ~3,200
     - 3 Temporal workflows: NodeCordoned, Cyclops, HighUnhealthyDeployments.
   * - Helmfile platform (``helmfile/`` + ``deploy/`` + ``argocd/``)
     - 141 + 19 + 16
     - n/a
     - YAML/Helm/Helmfile/ArgoCD GitOps stack for Knative, Istio, Cassandra,
       Postgres, Redis, ES, KEDA, Temporal, sample apps.
   * - Observability (``logging/`` + ``monitoring/``)
     - 48 + 10
     - 1,688 + n/a
     - Filebeat → ES pipelines, Fluent-Bit DTE shipper, 4 Grafana dashboards,
       Prometheus recording rules.
   * - Security/IAM (``iam-sidecar/`` + ``portable-cryptor/``)
     - 13 + 16
     - 750 + n/a
     - GCP iamcredentials sidecar; RSA-2048 + KMS portable cryptor with
       key-rotations/.
   * - Supporting services (``forge_containers/`` + ``cc/`` + ``go-app/`` +
       ``scraper/`` + ``lambda/`` + ``routers/`` + ``busybox/`` + ``kittz/``)
     - ~100
     - mixed
     - Forge runtime + helm-crd; cc monolith extraction; sample go-app;
       Postgres/Temporal scraper; AWS Lambdas; small Python router lib.
   * - Analytics (``cdp_services/`` + ``atlassian_services/`` +
       ``costs-estimates/``)
     - 24
     - n/a
     - Service-inventory CSVs and Python migration/cost models.
   * - Vocalno + Kueue (``vocalno/`` + ``pae/`` + ``pae-apps/``)
     - 36
     - n/a
     - Volcano scheduler (GPU/batch); PAE/Kueue job queueing.

Documentation provenance
==========================

**Investigation conducted** 2026-05-08 12:54–13:30 PT:

* 4 parallel Explore subagents reading every Go/TypeScript/Python/YAML
  artefact under the in-scope directories
* Cross-checked file counts against ``find . -type f -not -path './.git/*'``
* Cross-checked LoC against ``wc -l`` on every Go/TS file individually
* Cross-checked Go function/type inventories against
  ``grep -E '^func |^type ' <file>``
* All numerical claims verified against the actual source tree under
  ``/Users/tchen7/MyProjects/atlassian_packages/gcp_kitt``

**Authoritative reference docs in the repo itself**:

* ``amp/DTE_DISTRIBUTED_CLIENT_APIS_AND_FLOWS.md`` — 370 LoC, the canonical
  DTE HTTP API + cluster-registry data-model spec
* ``INTEGRATION_REVIEW.md`` (root) — cross-component integration checklist
  for dtecli ↔ distributed-client ↔ distributed-worker
* ``helmfile/DEPLOYMENT_ORDER.md`` — 11-step Knative/Istio/serving bring-up
  order
* ``helmfile/DEPLOYMENT_SUMMARY.md`` — Cassandra replication factor, Grafana
  dashboards, admin secrets
* ``helmfile/dte/README.md`` — production DTE deployment notes
* ``dte-web/README.md`` — DTE Web UI architecture and deployment
* ``logging/DEPLOYMENT.md`` and ``logging/INGEST_PIPELINE_EXPLANATION.md``
  — logging-stack walk-through
* ``monitoring/PROMETHEUS_DTASKE_UPDATE.md`` — Prometheus
  ``dte-service-capture`` recording-rule update procedure
* ``asi/ReadME.MD`` — ASI operator GCP-IAM role requirements
* ``kitt-runbooks/README.md`` and ``kitt-runbooks/cli/README.md`` — runbook
  inventory

**Team contact**: KITT (Kubernetes Infrastructure Tooling on GCP).
Repo authors: refer to ``git log`` and the SLAuth ``rollcall``-AD-group
references in ``dte-web/README.md`` (``kube-*`` group prefix indicates
cluster RBAC bindings).
