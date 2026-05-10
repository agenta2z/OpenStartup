==================================
Multi-axis matrix of every directory
==================================

This page enumerates **all 33 top-level directories** in ``gcp_kitt`` along
five axes: file count, primary language, platform tier, primary purpose,
and which document under :doc:`../modules/index` covers it. Numbers were
collected with ``find . -maxdepth 2 -type f`` and ``wc -l`` on every
language file.

Axis 1 – Size, language, primary purpose
==========================================

.. list-table::
   :header-rows: 1
   :widths: 18 8 18 56

   * - Directory
     - Files
     - Primary language(s)
     - Primary purpose / one-line summary
   * - ``ai/``
     - 1
     - YAML
     - Critical-pod ``PriorityClass`` for AI/compute-class pods
       (``gcp-critical-pods.yaml``).
   * - ``amp/``
     - 21
     - Go (8 files, 6,065 LoC) + Helm/Yaml + Markdown
     - First-generation **Distributed Task Execution** (DTE) control plane
       — ``distributed-client`` (HTTP API, 1,868 LoC) + ``distributed-worker``
       (Temporal worker + Argo workflow bridge, 1,222 LoC) + shared
       ``pkg/types`` & ``pkg/logger``. Companion docs:
       ``DTE_DISTRIBUTED_CLIENT_APIS_AND_FLOWS.md``.
   * - ``amp-spike/``
     - 7
     - JavaScript (Node.js) + Markdown + ``amp-spike.sd.yml``
     - Original **Atlas micros AMP spike** that prototyped the same
       distributed-task control flow before the Go/Temporal rewrite.
       ``server.js`` is the prototype.
   * - ``argocd/``
     - 16
     - YAML + Markdown
     - GitOps layer. Recursive ``argocd-bootstrap/`` →
       ``argocd-apps/`` → ``cluster-bootstrap/`` → ``cluster-apps/`` ApplicationSet
       hierarchy.
   * - ``asi/``
     - 14
     - Go (6 files, 1,759 LoC) + YAML + Python (requirements.txt)
     - **Atlassian Service Infrastructure operator** — controller-runtime
       Operator that owns the ``asis.platform.atlassian.com/v1`` cluster-scoped
       CRD. Each ``ASI`` resource creates a K8s ServiceAccount and binds it
       to a GCP IAM service account.
   * - ``atlassian_services/``
     - 11
     - Python + CSV + PNG
     - Migration analytics: dataset of all "sliver" services and their
       region/shard distribution; Python helpers
       (``analyze_sliver_services.py``).
   * - ``busybox/``
     - 4
     - Dockerfile + shell + Python
     - Canary/diagnostic image (debug pods) — small Dockerfile, Makefile,
       requirements.txt and ``test.sh``.
   * - ``cc/``
     - 12
     - Mixed
     - Container ``monolith`` source extraction; see
       ``cc/monolith/README.md`` and ``README-extracted-files.md``.
   * - ``cdp_services/``
     - 6
     - Python + CSV + PNG
     - Region/environment analytics for the Cloud-Data-Plane services
       (``explode_environments.py``, ``region_count_histogram.py``).
   * - ``costs-estimates/``
     - 7
     - Python + PNG + CSV + ``rules.txt``
     - Cost modelling — ``compute_costs.py`` produces the comparison graphs
       and CSVs used to size GCP migration vs. existing AWS spend.
   * - ``deploy/``
     - 19
     - YAML + Helm + Python
     - Application-layer Helmfile + ingress + Kafka manifests; charts under
       ``deploy/charts/go-app``.
   * - ``dte-web/``
     - 14
     - Node.js (1,241 LoC ``server.js``) + YAML + Markdown
     - **DTE Web UI** — Express server + static SPA (``public/app.js``)
       proxying to ``distributed-client`` + ``temporal-web``. Auth notes in
       ``asap.md``, ``sct.md``, ``auth-provider.md``.
   * - ``dtecli/``
     - 19+ (incl. ``src/cli`` and ``bootstrap/``)
     - TypeScript (31 files, 7,943 LoC)
     - **Atlas-plugin CLI** for KITT operators. Five command groups
       (``auth``, ``cluster``, ``config``, ``runner``, ``workflow``) plus
       the ``bootstrap/`` Knative JS worker (5 TS files).
   * - ``forge/``
     - 0
     - —
     - Reserved/empty placeholder — paired with the populated
       ``forge_containers/`` peer.
   * - ``forge_containers/``
     - 48
     - Go + TypeScript + YAML + Helm
     - Forge-runtime container fleet plus the ``helm-crd`` controller and
       ``forgeapp`` deployer. Top-level ``main.go``, ``deploy.ts``,
       ``forgeapp-deployment.ts`` plus per-feature dirs (``api``, ``config``,
       ``controllers``, ``hack``, ``helm``, ``helm-crd``, ``yamls``).
   * - ``go-app/``
     - 9
     - Go (``main.go`` 402 LoC)
     - Sample Go service used as a smoke-test workload (Pub/Sub + GCS +
       Spanner integration patterns).
   * - ``helmfile/``
     - 141 (largest top-level dir)
     - Helm + helmfile YAML + shell + Markdown + Go (DTE prod copy)
     - Cluster bring-up: Knative + Istio + Kourier + Cassandra + Postgres +
       Redis + Elasticsearch + KEDA + Temporal + sample apps. Also hosts the
       production copy of DTE under ``helmfile/dte/``.
   * - ``iam-sidecar/``
     - 13
     - Go (4 files, 750 LoC)
     - Sidecar container that mints GCP access/ID tokens via
       ``iamcredentials.GenerateAccessToken``; exposes ``/token`` HTTP
       endpoint on localhost.
   * - ``k8s-metadata-collector/``
     - 8
     - Mixed
     - Collects per-pod / per-node metadata snapshots from member clusters.
   * - ``kitt-runbooks/``
     - 24
     - Go (20 files) + Markdown + Helm values
     - **Three Temporal workflows** for SRE: ``K8sNodeCordoned``,
       ``CyclopsCycleNodes``, ``HighUnhealthyDeployments``. Activities call
       ``internal/k8sclient`` and ``internal/splunk``. Worker entry-point
       ``cmd/worker/main.go`` (117 LoC).
   * - ``kittz/``
     - 4
     - Mixed
     - Tiny supporting tool (4 files; check ``README.md``).
   * - ``lambda/``
     - 23
     - Python + AWS SAM templates + SQL
     - AWS Lambdas in two flavours: ``dynamo/`` (DynamoDB-backed) and
       ``pg/`` (Postgres-backed).
   * - ``logging/``
     - 25 (1,688 LoC of shell/MD)
     - Shell + JSON + YAML + Helm
     - Filebeat → Elasticsearch ingest pipelines + Fluent-Bit DTE shipper
       Helm chart (``charts/fluent-bit-dte``). Validation scripts:
       ``check-fluent-bit-errors.sh``, ``verify-json-parsing.sh``.
   * - ``monitoring/``
     - 10
     - JSON + YAML + Markdown + Shell
     - Four Grafana dashboards (KEDA, Postgres, Redis, Temporal) +
       Prometheus ``dte-service-capture`` recording-rule update job
       (``update-prometheus-dtaske.sh``).
   * - ``pae/``
     - 15
     - Helm + JSON + Markdown + LICENSE
     - **PAE / Kueue platform** — connect-cluster notes, Kueue config,
       ``pae.json``/``kueue.json`` definitions.
   * - ``pae-apps/``
     - 7
     - Shell + Helm + Markdown
     - PAE-managed sample applications + ``creat-jobs.sh`` job-creation
       script + ``KUEUE-CRDS.md``.
   * - ``portable-cryptor/``
     - 16
     - Python + Shell
     - **Cross-cloud key portability** — RSA-2048 keypair generation,
       export, GCP/AWS KMS import (``import_to_gcp.sh``, ``import-aws-rsa.sh``),
       envelope encryption via AWS Encryption SDK
       (``kms_encrypt_decrypt_esdk.py``). ``key-rotations/`` subfolder.
   * - ``routers/``
     - 14
     - Python
     - Self-contained URL routing library — ``router.py`` core + path
       parameter, wildcard, performance, integration, stress test suites.
   * - ``scraper/``
     - 44
     - Python + Helm + Shell
     - Two flavours: ``pg/`` (AWS SAM-deployed Postgres scraper —
       ``scraper_processor.py``, ``scraper_post_job.py`` etc.) and
       ``temporal-pg-redis/`` (Temporal-orchestrated scraper with KEDA-scaled
       workers).
   * - ``sweeper/``
     - 6
     - Go (3 files, 454 LoC) + YAML
     - **Sweeper operator** — kubebuilder Operator that owns the
       ``sweepers.platform.atlassian.com/v1`` CRD. ``Reconcile()`` labels pods
       on a cron schedule.
   * - ``tests/``
     - 2
     - Markdown + text
     - Platform-level test inventory (``service_list.txt``).
   * - ``vocalno/``
     - 10
     - YAML + Shell
     - **Volcano** batch scheduler config (``agent.yaml``, ``aws-agent.yaml``,
       ``vcjob.yaml``, ``cpu_burst.yaml``, ``gcp-quotas.yaml``).
   * - root-level files
     - 6
     - Python + Markdown
     - ``analyze_service_regions.py``, ``INTEGRATION_REVIEW.md`` (DTE spec
       cross-check), ``.agent.md``, ``.gitignore``.

Axis 2 – Language distribution (whole repo)
=============================================

.. list-table::
   :header-rows: 1
   :widths: 20 12 68

   * - Extension
     - Count
     - Notes
   * - ``.yaml`` / ``.yml``
     - 333 + 4
     - Helm/helmfile manifests dominate — every chart has 3–8
       ``templates/*.yaml`` plus ``values*.yaml``.
   * - ``.go``
     - 79
     - DTE (22), kitt-runbooks (20), forge_containers (~10), iam-sidecar (4),
       asi (6), sweeper (3), go-app (1), sweeper api (1), helmfile/dte
       sample (4), kitt-runbooks/internal (5).
   * - ``.md`` / ``.MD``
     - 73 + 7
     - 35+ READMEs (one per major component), plus DEPLOYMENT,
       INTEGRATION_REVIEW, AUTH, RECOMMENDATION, OPTIONS docs.
   * - ``.sh``
     - 66
     - Heavy in ``logging/`` (9), ``helmfile/`` (~25), ``portable-cryptor/``
       (4), ``vocalno/`` (4), one-shot deploy/cleanup/check scripts.
   * - ``.py``
     - 63
     - Largest concentrations in ``routers/`` (14), ``scraper/pg`` (10),
       ``portable-cryptor/`` (7), analytics dirs (``cdp_services/``,
       ``atlassian_services/``, ``costs-estimates/``).
   * - ``.ts``
     - 52
     - Concentrated in ``dtecli/`` (31) and ``forge_containers/`` (~10).
   * - ``.json``
     - 32
     - Includes 4 Grafana dashboard JSONs, ``aws-accounts.json``,
       ``workflows.json``, ``clusters.json``, package manifests.
   * - ``.tpl``
     - 20
     - Helm template helpers (``_helpers.tpl``).
   * - ``.go.mod`` / ``.go.sum``
     - 10 + 10
     - 10 distinct Go modules (separate ones for ``amp/``, ``helmfile/dte/``,
       ``asi/``, ``sweeper/``, ``iam-sidecar/``, ``go-app/``, ``forge_containers/``,
       ``kitt-runbooks/``, ``helmfile/temporal-helloworld/``, plus a
       supporting one).
   * - ``.tf``
     - 4
     - A small amount of Terraform (likely under ``lambda/`` or ``forge_containers/``).
   * - ``.sql``
     - 4
     - Schema files (e.g. ``scraper/pg/schema.sql``,
       ``helmfile/scraper/.../cleanup-all-tables.sql``).
   * - ``.rego``
     - 1
     - One Open Policy Agent rule (likely a network/admission policy).

Axis 3 – Platform tier
=========================

This is a **subjective tiering** based on blast-radius and how foundational
each component is to a running cluster. ``Tier 0`` = without it, no cluster
exists; ``Tier 3`` = developer convenience.

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Tier
     - Components (alphabetical)
   * - **Tier 0** (cluster bring-up)
     - ``argocd/``, ``helmfile/`` (bootstrap, temporal-manifests, charts),
       ``ai/`` (PriorityClass).
   * - **Tier 1** (control-plane + IAM + network)
     - ``amp/`` (DTE), ``asi/``, ``sweeper/``, ``iam-sidecar/``,
       ``portable-cryptor/`` (key-rotation), ``vocalno/`` (batch scheduler),
       ``pae/`` + ``pae-apps/`` (Kueue queueing).
   * - **Tier 2** (operational tooling + observability)
     - ``logging/``, ``monitoring/``, ``kitt-runbooks/``, ``dte-web/``,
       ``dtecli/``, ``k8s-metadata-collector/``, ``forge_containers/``.
   * - **Tier 3** (sample/canary/utilities/analytics)
     - ``go-app/``, ``busybox/``, ``kittz/``, ``cc/``, ``deploy/``,
       ``lambda/``, ``routers/``, ``scraper/``, ``cdp_services/``,
       ``atlassian_services/``, ``costs-estimates/``, ``tests/``,
       ``amp-spike/``, ``forge/``.

Axis 4 – Primary external integrations
==========================================

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Integration target
     - Used by
   * - **GCP IAM** (``iamcredentials.googleapis.com``)
     - ``iam-sidecar/``, ``asi/`` (``RealIAMService`` wraps GCP Admin API).
   * - **GCP Cloud KMS**
     - ``portable-cryptor/`` (``kms_encrypt_decrypt.py``,
       ``import_to_gcp.sh``).
   * - **AWS KMS / Encryption SDK**
     - ``portable-cryptor/`` (``kms_encrypt_decrypt_esdk.py``,
       ``import-aws-rsa.sh``).
   * - **AWS S3 / SDK**
     - DTE worker (``cluster_db.go`` reads
       ``https://kitt-cluster-registry.s3.amazonaws.com/...``);
       ``helmfile/s3-crud-api/``; AWS Signature V4 used to fetch cluster
       registry.
   * - **AWS Lambda / API Gateway / SAM**
     - ``lambda/dynamo/``, ``lambda/pg/``, ``scraper/pg/``
       (``setup_api_gateway.sh``, ``samconfig.toml``, ``template.yaml``).
   * - **Temporal**
     - ``amp/``, ``helmfile/dte/``, ``kitt-runbooks/``,
       ``helmfile/temporal-helloworld/``, ``scraper/temporal-pg-redis/``,
       ``dte-web/`` (proxy to ``temporal-web``).
   * - **Argo Workflows** (CRD)
     - DTE worker (``createArgoWorkflowYAML``,
       ``createServiceDiscoveryWorkflowYAML``,
       ``createHealthCheckWorkflowYAML``,
       ``executeArgoWorkflow``).
   * - **Elasticsearch** (logs ingest)
     - ``logging/`` (Filebeat ingest pipeline + ILM policy).
   * - **Splunk** (log queries)
     - ``kitt-runbooks/internal/splunk/client.go`` — used by
       ``CheckLogsForCordonAuditActivity``.
   * - **Prometheus / Grafana / KEDA**
     - ``monitoring/`` (4 dashboards + ``dte-service-capture`` recording
       rules), ``scraper/temporal-pg-redis/`` (KEDA scaling).
   * - **SLAuth / ASAP / SCT (Atlassian)**
     - ``dte-web/`` (auth headers), DTE worker
       (``getClusterTokenFromAuthProvider``, ``isSCTToken``,
       ``extractGroupsFromToken``, ``filterGroupsByPattern``),
       ``dtecli/src/cli/commands/auth/``.
   * - **Centrify / Rollcall**
     - DTE web README references both for AD-group resolution.
   * - **Knative**
     - ``helmfile/`` knative configs; ``dtecli/bootstrap/helm/templates/js-worker-knative-service.yaml``.
   * - **Cassandra**
     - Temporal persistence (``helmfile/`` cassandra-* manifests, exporter,
       JMX scrape).
   * - **Postgres + Redis**
     - Temporal persistence variant (``scraper/temporal-pg-redis/``);
       Bitnami Helm releases in main ``helmfile/helmfile.yaml``.
   * - **Volcano + Kueue**
     - ``vocalno/``, ``pae/``, ``pae-apps/``.

Axis 5 – Cross-reference to per-module documentation
=======================================================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module document
     - Covers
   * - **Distributed execution (DTE)**
     - :doc:`../modules/dte-amp`, :doc:`../modules/dte-amp-spike`,
       :doc:`../modules/dte-cli`, :doc:`../modules/dte-web`,
       :doc:`../modules/helmfile-platform` (the ``dte/`` chart),
       root ``INTEGRATION_REVIEW.md``.
   * - **Helmfile platform & workloads**
     - :doc:`../modules/helmfile-platform`, :doc:`../modules/deploy`,
       :doc:`../modules/argocd`, :doc:`../modules/ai`,
       :doc:`../modules/vocalno`, :doc:`../modules/pae`,
       :doc:`../modules/pae-apps`, :doc:`../modules/forge-containers`,
       :doc:`../modules/cdp_services`, :doc:`../modules/atlassian_services`,
       :doc:`../modules/costs-estimates`, root ``analyze_service_regions.py``.
   * - **Observability**
     - :doc:`../modules/logging`, :doc:`../modules/monitoring`.
   * - **Security & IAM**
     - :doc:`../modules/iam-sidecar`, :doc:`../modules/portable-cryptor`.
   * - **K8s operators / controllers**
     - :doc:`../modules/asi`, :doc:`../modules/sweeper`,
       :doc:`../modules/k8s-metadata-collector`.
   * - **Temporal workflows (non-DTE)**
     - :doc:`../modules/kitt-runbooks`, :doc:`../modules/scraper`
       (``temporal-pg-redis``), :doc:`../modules/helmfile-platform`
       (``temporal-helloworld`` chart).
   * - **Client tooling**
     - :doc:`../modules/dte-cli` (deep), :doc:`../modules/routers`,
       :doc:`../modules/busybox`, :doc:`../modules/kittz`,
       :doc:`../modules/tests`.
   * - **Data-plane / sample services**
     - :doc:`../modules/cc`, :doc:`../modules/go-app`,
       :doc:`../modules/scraper`, :doc:`../modules/lambda`,
       :doc:`../modules/helmfile-platform` (``s3-crud-api``,
       ``python-app`` charts).
