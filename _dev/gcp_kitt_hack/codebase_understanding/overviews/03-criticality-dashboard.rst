==============================================
Criticality dashboard (SRE / on-call lens)
==============================================

This page ranks every ``gcp_kitt`` component by **blast-radius** —
i.e. how many production behaviours break if the component is offline,
mis-configured, or rolled back to a bad version. It is intended as a
fast triage aid for an on-call engineer.

Methodology
============

Every component was scored on three axes:

* **Cluster-wide vs. workload-scoped** — does failure stop the *cluster*
  from functioning, or just one workload?
* **Sync vs. async** — does the failure surface immediately to the user,
  or only on next reconcile / next workflow?
* **Replaceable vs. unique** — is there a manual or alternate path?

Scores collapse to a single criticality bucket: ``CRITICAL``, ``HIGH``,
``MEDIUM``, ``LOW``.

CRITICAL — failure stops cluster bring-up or operator workflows
================================================================

.. list-table::
   :header-rows: 1
   :widths: 20 12 16 52

   * - Component
     - Tier
     - Failure mode
     - Mitigation / runbook pointer
   * - ``helmfile/`` (bootstrap, knative, istio, cassandra)
     - Tier 0
     - Cluster cannot be (re)built; Temporal lacks persistence
     - ``helmfile/DEPLOYMENT_ORDER.md`` (11 steps), ``cleanup-all.sh``
       (warning — full teardown), ``cleanup-and-redeploy.sh``.
   * - ``argocd/cluster-bootstrap/``
     - Tier 0
     - GitOps no longer reconciles new clusters
     - Manual ``kubectl apply -f bootstrap/`` then re-bootstrap ArgoCD via
       ``argocd-bootstrap/``.
   * - ``amp/distributed-client``
     - Tier 1
     - All operator-driven cluster operations stop (no ``runner start``)
     - Ingress URL ``distributed-client.<cluster>.kitt-inf.net``;
       ``GET /health`` for liveness; rollback via Knative service revision.
   * - ``amp/distributed-worker``
     - Tier 1
     - Workflows queued but not executed; Temporal task-queue depth grows
     - Check Temporal Web UI; scale Knative replicas; ``ServiceMonitor`` +
       Temporal Grafana dashboard reveal queue depth.
   * - Temporal cluster (``helmfile/temporal-manifests/``)
     - Tier 0
     - All Temporal-backed workflows (DTE, runbooks, scraper) fail
     - Cassandra-backed; check
       ``helmfile/check-schema-version-job.yaml`` and
       ``setup-temporal-schema-job.yaml``.
   * - ``asi/`` Operator
     - Tier 1
     - New services cannot bind to GCP service accounts (Workload Identity
       broken)
     - Required role: ``roles/iam.serviceAccountAdmin``; finalizer
       ``platform.atlassian.com/finalizer`` may block namespace deletes if
       ASI controller is down.
   * - ``iam-sidecar``
     - Tier 1
     - Workloads relying on local ``/token`` endpoint cannot mint GCP
       creds; downstream GCP calls fail with ``UNAUTHENTICATED``
     - Restart sidecar; verify Workload Identity binding via ASI;
       container logs show
       ``iamcredentials.GenerateAccessToken/GenerateIdToken`` failures.

HIGH — significant degradation but no full outage
===================================================

.. list-table::
   :header-rows: 1
   :widths: 20 12 16 52

   * - Component
     - Tier
     - Failure mode
     - Mitigation / runbook pointer
   * - ``kitt-runbooks/`` Temporal worker
     - Tier 2
     - ``K8sNodeCordoned``, ``CyclopsCycleNodes``,
       ``HighUnhealthyDeployments`` runbooks no longer auto-run
     - Workflows can be re-triggered manually via ``tctl`` / ``dtecli
       runner``; check ``kitt-runbooks`` task-queue depth.
   * - ``sweeper/`` Operator
     - Tier 1
     - Pods stop receiving the ``serviceID`` label sweep; downstream tooling
       (logging selectors, billing attribution) loses correlation
     - Reconcile runs every cron tick; status fields ``lastRun``/``nextRun``
       on each ``Sweeper`` CR show staleness.
   * - ``logging/`` (Filebeat → Elasticsearch)
     - Tier 2
     - Logs not shipped; live tailing still works via ``kubectl logs``
     - ``logging/check-fluent-bit-errors.sh``,
       ``logging/check-pods.sh``, ``logging/verify-json-parsing.sh``.
       ILM policy in ``elasticsearch-ilm-policy.yaml``.
   * - ``monitoring/`` (Prometheus + Grafana + KEDA dashboards)
     - Tier 2
     - Loss of alerting and capacity dashboards; Temporal/Postgres/Redis
       blind
     - Re-import dashboards via Grafana API (``monitoring/README.md`` notes
       the ConfigMap-update gotcha — Grafana doesn't auto-import); rerun
       ``monitoring/update-prometheus-dtaske.sh`` for recording-rule
       drift.
   * - ``portable-cryptor/key-rotations/``
     - Tier 1
     - Stale keys could be in use beyond rotation deadline
     - Re-run ``import_to_gcp.sh`` / ``import-aws-rsa.sh``;
       ``wrap_and_import_job2.sh``.
   * - ``vocalno/`` (Volcano)
     - Tier 2 (where deployed)
     - GPU/batch jobs queue but don't execute
     - Inspect ``vcjob.yaml`` queue; verify ``agent.yaml`` /
       ``aws-agent.yaml``; ``gcp-quotas.yaml`` for quota exhaustion.
   * - ``pae/`` + ``pae-apps/`` (Kueue)
     - Tier 2
     - Job admission paused; queue length grows
     - Connect-cluster notes in ``pae/connect-cluster.txt``;
       ``KUEUE-CRDS.md`` for CRD references.

MEDIUM — operator inconvenience but workloads keep running
============================================================

.. list-table::
   :header-rows: 1
   :widths: 20 12 16 52

   * - Component
     - Tier
     - Failure mode
     - Mitigation / runbook pointer
   * - ``dtecli/`` (CLI)
     - Tier 2
     - Operators must hit ``distributed-client`` via curl directly
     - The DTE_DISTRIBUTED_CLIENT_APIS_AND_FLOWS.md gives raw curl
       examples for every action.
   * - ``dte-web/``
     - Tier 2
     - Web UI down; CLI still works
     - ``dte-web/Makefile`` ``make all`` rebuilds & redeploys.
   * - ``forge_containers/``
     - Tier 2
     - Forge runtime workloads cannot be (re)deployed; existing instances
       continue to run
     - ``ARGOCD_SETUP.md``, ``KUBERNETES_DEPLOYMENT_COMPARISON.md``.
   * - ``k8s-metadata-collector/``
     - Tier 2
     - Snapshot drift; downstream analytics stale
     - Re-run on next schedule; verify outbound connectivity to sink.
   * - ``scraper/`` (both flavours)
     - Tier 3
     - Service-inventory data stale; KEDA-scaled workers idle
     - ``scraper/temporal-pg-redis/scale-workers.sh``,
       ``debug-keda-scaling.sh``,
       ``investigate-stuck-workflow.sh``.
   * - ``cdp_services/`` / ``atlassian_services/`` / ``costs-estimates/``
     - Tier 3
     - Reports become stale (no live impact)
     - Re-run Python scripts; outputs are CSV/PNG only.

LOW — sample / canary / utility
================================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Component
     - Note
   * - ``go-app/``
     - Sample Go service used for testing.
   * - ``busybox/``
     - Diagnostic image (debug pods).
   * - ``kittz/``
     - Tiny helper; check README before relying on.
   * - ``cc/``
     - Source extraction reference.
   * - ``helmfile/temporal-helloworld/``
     - Smoke-test workflow (``workflow.go`` + ``activities.go``).
   * - ``helmfile/python-app/``
     - Sample Python app demonstrating GCP auth, S3, PubSub.
   * - ``helmfile/s3-crud-api/``
     - Sample S3 CRUD service used as reference Knative deployment.
   * - ``amp-spike/``
     - Original Node.js prototype, superseded by ``amp/`` Go services.
   * - ``forge/``
     - Empty / placeholder.
   * - ``tests/``
     - Documentation-only test inventory.
   * - ``ai/``
     - One-file ``PriorityClass`` for AI/compute pods.
   * - ``routers/``
     - Stand-alone Python URL router library — no production deployment in
       this repo.

On-call quick links
====================

* **DTE 5xx rate** → Temporal Grafana dashboard
  (``monitoring/grafana-temporal-dashboard.json``) → workflow_failed
  panel.
* **Cluster registry stale** → ``cluster_db.go`` reads
  ``https://kitt-cluster-registry.s3.amazonaws.com/...``; check S3
  IAM/network connectivity from worker pod.
* **Auth-provider rejects token** → ``getClusterTokenFromAuthProvider``
  in ``amp/distributed-worker/helpers.go``; check ``X-DTE-GROUPS`` header
  format and per-cluster allow-list.
* **Workflow stuck** →
  ``scraper/temporal-pg-redis/investigate-stuck-workflow.sh``.
* **Filebeat parse errors** → ``logging/check-fluent-bit-errors.sh`` +
  ``logging/INGEST_PIPELINE_EXPLANATION.md`` for field-mapping rules.
* **PriorityClass eviction** → ``ai/gcp-critical-pods.yaml``.
* **Cassandra schema drift** → ``helmfile/check-schema-version-job.yaml``.
* **Recording rules outdated** → ``monitoring/update-prometheus-dtaske.sh``.
* **Key rotation overdue** → ``portable-cryptor/key-rotations/``.
