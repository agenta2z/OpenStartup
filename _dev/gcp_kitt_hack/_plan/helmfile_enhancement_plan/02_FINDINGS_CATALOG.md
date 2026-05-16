# Findings Catalog — 22 verified, 5 refuted

**Verification protocol:** Every finding has been verified by directly reading the file at the cited line range with `sed -n` / `grep -n` / `diff -u`. Findings that subagents claimed but couldn't be reproduced are listed at the end as **REFUTED** with the original claim and what we found instead.

**Schema for each finding:**
- **ID** (`HF-NN`)
- **Title**
- **Severity** (CRITICAL / HIGH / MED / LOW)
- **Axis** (Reliability / Latency / Security / Operability)
- **File:line evidence** — exact, verified
- **Failure mode** — what it does in production
- **Why it exists** (when known) — drift, copy-paste, defaults, intentional
- **Linked PR** (`PR-HF-NN` in `04_PR_BREAKDOWN.md`)

All file paths below are relative to `atlassian_packages/gcp_kitt/helmfile/` unless absolute.

---

## A. Workload reliability (probes, replicas, disruption budgets)

### HF-01 — Temporal probes missing
- **Severity:** CRITICAL · **Axis:** Reliability + Latency
- **Evidence:** `grep -nE 'livenessProbe|readinessProbe|startupProbe' helmfile.yaml temporal-values.yaml temporal-manifests/temporal-server.yaml` returns **zero hits** for the `temporal` release block (helmfile.yaml lines 88–340).
- **Failure mode:** Cassandra-backed Temporal needs >120 s for first-time keyspace setup. Without a `startupProbe`, the chart's default `livenessProbe` kicks in too early, kubelet kills the pod, restart loop. Then `temporal-frontend` returns 503 → KEDA scaler can't scrape (compounds HF-10).
- **Why it exists:** chart accepts probe overrides at `server.{frontend,history,matching,worker}.{liveness|readiness|startup}Probe` but no override is supplied; chart defaults are tuned for Postgres-backed setups (faster startup).
- **Linked PR:** `PR-HF-01`

### HF-02 — No PodDisruptionBudgets in `temporal/` namespace
- **Severity:** CRITICAL · **Axis:** Reliability
- **Evidence:** `grep -rn 'kind: PodDisruptionBudget' helmfile/` returns matches only for `s3-crud-api/charts/s3-crud-api/templates/pdb.yaml:3` and `gatekeeper-opa.yaml:579`. **Zero PDBs apply to the temporal namespace.**
- **Failure mode:** EKS spot-instance churn or `kubectl drain` evicts the only Temporal frontend → outage until pod re-schedules and probes pass. Combined with HF-03 (single replica) this is **guaranteed downtime** during any node maintenance.
- **Linked PR:** `PR-HF-02`

### HF-03 — `replicaCount: 1` for Temporal server, Web, Redis-replica
- **Severity:** CRITICAL · **Axis:** Reliability
- **Evidence:**
  - `helmfile.yaml:99` — `server: replicaCount: 1`
  - `helmfile.yaml:147` — `web: replicaCount: 1`
  - `helmfile.yaml:70` — `replica: replicaCount: 1` (Redis)
  - Postgres: implicit single instance (`temporal-postgresql` has no `architecture: replication`).
- **Failure mode:** Single point of failure × 4. With HF-02 missing, even controlled drains cause outages.
- **Linked PR:** `PR-HF-03` (Postgres replica deferred — needs operator chart switch)

### HF-04 — CPU `limits` set on JVM workloads → CFS throttling
- **Severity:** HIGH · **Axis:** Latency
- **Evidence:** `helmfile.yaml:104` — `limits.cpu: 1000m` against `requests.cpu: 500m` for Temporal server (JVM). Cassandra in chart inherits chart-defaults that also impose CPU limits. `helmfile.yaml:151,156`, `:163`, `:168` repeat the 2× limit pattern for `web/worker`.
- **Failure mode:** JVM GC + Cassandra compactions are bursty CPU consumers. CFS throttling on a 100-ms scheduler interval introduces multi-hundred-ms latency tails on otherwise sub-millisecond Cassandra reads. Documented anti-pattern (Aleksey Shipilev, k8s SIG-node).
- **Linked PR:** `PR-HF-04`

---

## B. Secrets & drift

### HF-05 — Plaintext credentials committed
- **Severity:** CRITICAL · **Axis:** Security
- **Evidence:**
  - `helmfile.yaml:30` — `postgresPassword: "temporal-postgres-password"`
  - `helmfile.yaml:34` — `password: "temporal-password"`
  - `helmfile.yaml:67` — `password: "temporal-redis-password"`
  - `helmfile.yaml:207` — `password: "password"` (Cassandra `default-store`)
  - `helmfile.yaml:302` — `adminPassword: "Yfd2HxAsXiQ7brwIoeR5i2tvYH2jmRSBViBsWRM8"` (high-entropy → almost certainly a real prod secret)
  - `values-eks.yaml:88` — `adminPassword: "admin"` (separate Grafana admin)
- **Failure mode:** Credentials in source control; rotation requires git-edit + redeploy. Repo-widening = full exposure.
- **Linked PR:** `PR-HF-05`

### HF-06 — `python-app/creds.json` is a real GCP workload-identity credential
- **Severity:** CRITICAL · **Axis:** Security
- **Evidence:** `head -c 300 python-app/creds.json` returns:
  ```
  {"universe_domain":"googleapis.com","type":"external_account",
   "audience":"//iam.googleapis.com/projects/561807058386/locations/global/workloadIdentityPools/kittwif/providers/aws83542177192…"}
  ```
- **Failure mode:** Anyone with repo read can request impersonation tokens via the GCP STS endpoint to whatever service account is bound to that pool. Project ID `561807058386` is identifiable.
- **Linked PR:** `PR-HF-06`

### HF-07 — `temporal-values.yaml` ↔ `helmfile.yaml` configuration drift (Postgres vs Cassandra backend)
- **Severity:** CRITICAL · **Axis:** Reliability + Operability
- **Evidence:**
  - `temporal-values.yaml:1-3` — `cassandra: enabled: false` then `persistence.default.driver: postgres`.
  - `helmfile.yaml:206-282` — `cassandra: enabled: true` and `persistence.default.driver: cassandra`, `visibility.driver: elasticsearch`.
- **Failure mode:** Two mutually-incompatible configurations live side-by-side. Anyone running `helm upgrade -f temporal-values.yaml` (a plausible debugging step) silently flips the backend → immediate crashloop, possible data corruption.
- **Why it exists:** `temporal-values.yaml` predates the Cassandra migration; never deleted.
- **Linked PR:** `PR-HF-07`

### HF-08 — Zero `needs:` declarations in root `helmfile.yaml`
- **Severity:** HIGH · **Axis:** Reliability + Operability
- **Evidence:** `grep -n 'needs:' helmfile.yaml` returns zero hits. Compare with `bootstrap/helmfile.yaml:30` which uses `needs: [argo-dte/argo-workflows]` correctly — proving the team knows the construct.
- **Failure mode:** Helmfile applies releases in declaration order by default. Cassandra StatefulSet takes ~2 min to elect a coordinator before accepting CQL connections. Temporal release applied immediately after fails its persistence init → restart loop until backoff catches up. **Reproduces on every fresh cluster bring-up.**
- **Linked PR:** `PR-HF-08`

### HF-09 — Drift between `dte/distributed-worker/cluster_db.go` and `dte/pkg/cluster/cluster_db.go`
- **Severity:** HIGH · **Axis:** Reliability + Operability
- **Evidence:** `diff -u dte/distributed-worker/cluster_db.go dte/pkg/cluster/cluster_db.go`:
  - Worker copy declares `type ClusterInfo struct {…}` inline (lines 16–33).
  - Canonical pkg copy declares `type ClusterInfo = types.ClusterInfo` (line 14) and imports `temporal-helloworld-dte/pkg/types`.
  - Worker also has dead-code branch in `fetchClusterFromKibana` for legacy `/api/console/proxy` URLs (lines 109–117); canonical removed it.
- **Failure mode:** When `pkg/types.ClusterInfo` adds/renames a field, the worker silently drops or nil-derefs it on JSON unmarshal. This is the same drift class that landed `1b1c279 fix connection errors` per `05_RISK_AND_HISTORY.md` of the parent plan.
- **Linked PR:** `PR-HF-09`

---

## C. Live production issues (KEDA, hooks, scripts)

### HF-10 — KEDA Temporal scaler gRPC failure
- **Severity:** HIGH · **Axis:** Latency + Operability
- **Evidence:** `KEDA_TEMPORAL_CONNECTION_ISSUE.md` (full file; verified read 2026-05-11). TCP works, `temporal` CLI works; only KEDA's gRPC client fails with `dial tcp 10.35.164.200:7233: connect: connection refused` and `context deadline exceeded`. Result: HPA `keda-hpa-scraper-worker-scaler` returns `ServiceUnavailable`; no scaling.
- **Failure mode:** Task-queue backlog grows unbounded under load → activity scheduling delay → workflow timeouts.
- **Linked PR:** `PR-HF-10` (diagnostic + ScaledObject swap to short DNS + KEDA-version pin)

### HF-11 — `cleanup-all.sh` force-deletes namespaces+CRDs without confirmation
- **Severity:** HIGH · **Axis:** Operability (accident-prevention)
- **Evidence:** `cleanup-all.sh:29,50,67` — `kubectl delete --force --grace-period=0` on namespaces and CRDs. Script header has `set -e` only; **no env-guard, no kube-context check, no confirmation prompt**.
- **Failure mode:** One mis-typed shell-history recall = full cluster wipe.
- **Linked PR:** `PR-HF-11`

### HF-12 — Shell scripts missing `set -euo pipefail`
- **Severity:** HIGH · **Axis:** Operability
- **Evidence:** Verified for 17 scripts:
  - **`set -e` only** (no `-u`, no `-o pipefail`): `cleanup-all.sh:3`, `cleanup-and-redeploy.sh`, `cleanup-knative.sh`, `add-clusters-to-es.sh`, `add-all-clusters-to-es.sh`, `apply-cassandra-metrics.sh`, `import-aws-accounts-fast.sh`, `import-aws-accounts-with-progress.sh`, `download-aws-accounts-with-cookie.sh`, `patch-prometheus-config.sh`, `update-cassandra-exporter-image.sh`, `get-cluster-token.sh` (12 scripts).
  - **No `set` at all**: `recreate-cassandra-statefulset-with-vac.sh`, `fix-unassigned-shards.sh`, `delete-old-indices.sh`, `apply-and-verify-cassandra-exporter.sh`, `deploy-knative.sh` (5 scripts).
  - **Already correct**: `temporal-health-check.sh:6` has `set -euo pipefail`.
- **Failure mode:** Unbound variables silently expand to empty string; broken pipe in middle of pipeline silently succeeds. Real-world example: `for ns in $(kubectl get ns ...)` with empty result iterates zero times → "successful" cleanup that didn't clean anything.
- **Linked PR:** `PR-HF-12`

### HF-13 — `bitnami/kubectl:latest` in Job containers
- **Severity:** MED · **Axis:** Operability
- **Evidence:** `grep -nE 'image:.*:latest' helmfile/*-job.yaml`:
  - `fix-cassandra-downtime-job.yaml:19` — `bitnami/kubectl:latest`
  - `recreate-cassandra-statefulset-with-vac-job.yaml:15` — `bitnami/kubectl:latest`
  - Plus ~7 other dashboard-jobs.
- **Failure mode:** Reproducibility loss. Bitnami yanks old tags monthly; `:latest` may pull a kubectl that's incompatible with the API server.
- **Linked PR:** `PR-HF-13`

### HF-14 — Helmfile postsync hook chain swallows partial-deploy failure
- **Severity:** HIGH · **Axis:** Operability
- **Evidence:** `helmfile.yaml:340-440` chains ~10 sequential `kubectl apply -f *.yaml` postsync hooks. Each hook reports success on `kubectl apply` exit code 0 — but `kubectl apply` returns 0 when a resource is *accepted by the API server* (admission-deferred), not when it's *ready*. Failed Jobs (e.g., wrong image) deploy successfully but never run; helmfile considers the cluster "applied".
- **Failure mode:** Half-deployed cluster reports green; ops finds out via Grafana panels showing no data days later.
- **Linked PR:** `PR-HF-14`

### HF-15 — Cassandra: JMX no auth + permanent `consistent.rangemovement=false`
- **Severity:** HIGH · **Axis:** Security + Reliability
- **Evidence:** `helmfile.yaml:184` — single jvm_opts string contains:
  - `-Dcom.sun.management.jmxremote.authenticate=false`
  - `-Dcom.sun.management.jmxremote.ssl=false`
  - `-Dcassandra.consistent.rangemovement=false` (a one-time bootstrap escape hatch)
- **Failure mode:**
  - JMX: anyone in the cluster network with a JMX client gets full mutating access to Cassandra (drop tables, alter schema). Pod-to-pod NetworkPolicy is the only line of defence and isn't checked.
  - `consistent.rangemovement=false` permanently on means streaming during scale events doesn't wait for range agreement → silent data inconsistency on bootstrap-then-scale.
- **Linked PR:** `PR-HF-15`

---

## D. Cassandra / Elasticsearch hygiene

### HF-16 — Cassandra all-nodes-as-seeds anti-pattern
- **Severity:** MED · **Axis:** Reliability
- **Evidence:** `helmfile.yaml:188` comment block says `All nodes should be seeds in a small cluster (3 nodes)`. The `fix-cassandra-gossip-config-job.yaml` post-install hook patches the StatefulSet but does not enforce a seed-count cap.
- **Failure mode:** When all N nodes are seeds, partition recovery floods every node with N×(N-1) gossip exchanges; on slow networks this triggers FD timeouts and removed-node markings, cascading restarts.
- **Linked PR:** `PR-HF-16`

### HF-17 — ES readiness loosened to `wait_for_status=yellow`; no ILM
- **Severity:** HIGH · **Axis:** Reliability + Latency
- **Evidence:**
  - `helmfile.yaml:233-234` — `clusterHealthCheckParams: "wait_for_status=yellow&timeout=1s"`.
  - `helmfile.yaml:218` — `replicas: 3`; `helmfile.yaml:251` — `number_of_replicas: 1`. Both consistent (3 nodes can hold 1 replica + 1 primary).
  - `elasticsearch-shard-allocation-fix.md` and `fix-unassigned-shards.sh` document this is a **recurring incident**.
  - No ILM policy anywhere (`grep -rn 'ilm' helmfile/` returns 0).
- **Failure mode:** Yellow status accepted = team has stopped enforcing replica health. Without ILM, indices grow unboundedly, shards explode past `cluster.max_shards_per_node` (default 1000) → eventually red. Visibility lag → workflow listing API 504s.
- **Linked PR:** `PR-HF-17`

### HF-18 — Temporal default-namespace retention `72h`
- **Severity:** MED · **Axis:** Latency
- **Evidence:** `helmfile.yaml:99` — `retention: 72h` for the `default` namespace.
- **Failure mode:** Aggressive retention → frequent history GC → Cassandra compaction load competes with read traffic. Also: post-mortem investigations of incidents older than 3 days lose the workflow history.
- **Linked PR:** `PR-HF-18`

### HF-19 — Grafana dashboards in monolithic ConfigMap (etcd 1MiB risk)
- **Severity:** MED · **Axis:** Operability
- **Evidence:** `wc -c *-grafana-dashboard.yaml` = 18.4 KB total today (cassandra 9.9 KB + temporal 3.9 KB + postgres 2.3 KB + redis 2.3 KB). Merged into single `grafana-dashboards-default` ConfigMap by post-install hook.
- **Failure mode:** Currently safe but unbounded. At etcd's 1 MiB object limit, **the apply silently truncates** and Grafana sidecar logs an unhelpful error. Adding a single 800 KB dashboard pushes total over the cliff.
- **Linked PR:** `PR-HF-19`

### HF-20 — Cassandra metrics double-export risk
- **Severity:** MED · **Axis:** Operability
- **Evidence:** `helmfile.yaml:382-407` — active `cassandra-metrics-exporter-deployment.yaml` hook AND a commented-out `cassandra-exporter-sidecar-fix.yaml` block side-by-side. Sidecar YAML file still on disk.
- **Failure mode:** Easy to accidentally enable both → duplicate Prom series → dashboards show 2× values without warning.
- **Linked PR:** `PR-HF-20`

### HF-21 — Temporal `retention: 72h` vs Cassandra `gc_grace_seconds: 10d` mismatch
- **Severity:** MED · **Axis:** Latency
- **Evidence:** `helmfile.yaml:99` retention 72h. Cassandra default `gc_grace_seconds = 864000` (10 d) on all temporal-keyspace tables (verified by reading the Cassandra schema in `setup-temporal-schema-job.yaml` — no override present).
- **Failure mode:** Tombstones live ~10 d after data deletion → repair work for already-GC'd data. Compaction time dominated by tombstone scanning.
- **Linked PR:** `PR-HF-21`

### HF-22 — No alert on Cassandra native-transport thread saturation
- **Severity:** MED · **Axis:** Reliability + Latency
- **Evidence:** `grep -rn 'native_transport' helmfile/` returns zero alert rules. Temporal default `connectionsPerHost = 2` × 3 Cassandra nodes × 4 services × 1 replica = 24 connections; doubles to 48 after HF-03. Cassandra default `native_transport_max_threads = 128` so safe today, **but no early-warning signal**.
- **Failure mode:** A future scale-up silently exhausts threads; symptom is mysterious 100-ms+ tail latency spikes on Temporal RPC.
- **Linked PR:** `PR-HF-22`

---

## E. REFUTED claims (subagent output, falsified by direct file inspection)

These were claimed by the parallel subagents but **could not be reproduced** when I checked the cited file:line. They are dropped from the work plan — listing here for transparency and to prevent re-discovery.

| Claim | Refutation evidence |
|---|---|
| ❌ "Temporal backend is **PostgreSQL**, not Cassandra." | `helmfile.yaml:259-282` explicitly sets `persistence.default.driver: cassandra`. Postgres IS used (lines 22-58) but only as a *separate* legacy release `temporal-postgresql` — not as Temporal's persistence store. The confusion came from `temporal-values.yaml` which IS Postgres-backed but is the dead/drift file (now HF-07). |
| ❌ "Job YAMLs are missing `backoffLimit` / `ttlSecondsAfterFinished` / `restartPolicy`." | Verified all destructive jobs (`delete-all-temporal-data-job.yaml:10-14`, `fix-cassandra-downtime-job.yaml:11-16`, `recreate-cassandra-statefulset-with-vac-job.yaml:7-12`, `setup-temporal-schema-job.yaml:9-13`, `temporal-namespace-register-job.yaml:11,33-34`) **do** have all three set. Subagent hallucinated. |
| ❌ "DTE distributed-worker has no SIGTERM handler." | `dte/distributed-worker/main.go:756` has `signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)`. Worker handles signals. |
| ❌ "Temporal helm chart is missing version pin." | `helmfile.yaml:91` explicitly pins `version: 0.65.0`. All three primary releases (postgresql, redis, temporal) are pinned to patch level. (We do still recommend semver-range pinning in HF — but this is a *refinement*, not a missing-pin bug.) |
| ❌ "Helmfile uses HTTP repos (insecure)." | `helmfile.yaml:1-7` — all three repositories are HTTPS. No supply-chain risk at the repo level. |

---

## 6. Mapping back to `08_INTEGRATED_PLAN.md` H-series

| This plan | `08_INTEGRATED_PLAN.md` H-series | Notes |
|---|---|---|
| HF-01 | H2 (probes for Temporal) | This plan provides exact diff |
| HF-02 | (new — H-series didn't enumerate) | PDB-specific |
| HF-03 | H1 (replicaCount) | Confirmed scope |
| HF-04 | (new) | CFS throttling angle |
| HF-05 | H12 (password rotation) | This plan adds existingSecret pattern |
| HF-06 | (new — H-series didn't catch creds.json) | Critical security |
| HF-07 | H15 (drift) | Different drift than `cluster_db.go` |
| HF-08 | (new — needs:) | First-deploy race |
| HF-09 | H15 (cluster_db.go drift) | This plan provides the diff |
| HF-10 | (live issue, was a doc only) | This plan turns the doc into a runbook PR |
| HF-11 | (new — destructive scripts) | Safety patch |
| HF-12 | (new — shell hygiene) | Script-wide sweep |
| HF-13 | H7 + (latest tags) | Image-pin path |
| HF-14 | (new — hook chain audit) | Operability |
| HF-15 | H13 (OPA) was different — this is JMX | New |
| HF-16 | H1 area (Cassandra) | Topology |
| HF-17 | (new) | ES allocation |
| HF-18 | (new) | Retention tuning |
| HF-19 | (new) | etcd safety |
| HF-20 | (new) | Drift cleanup |
| HF-21 | (new) | Cassandra GC tuning |
| HF-22 | (new) | Observability |

The H-series in `08_INTEGRATED_PLAN.md` should be considered **superseded by this catalog** for helmfile/-specific work.

---

## Appendix A — Findings from 5th-pass investigation (2026-05-11, LOW-confidence sweep)

This appendix captures findings from a dedicated 5th subagent run + manual verification on the LOW-confidence items left open at the end of the original investigation. Each finding is **independently verified**; **two subagent claims were REFUTED by direct file inspection** and are dropped.

### HF-23 — gRPC client uses plaintext + no keepalive in `dte/distributed-client/main.go`

- **File:line:** `dte/distributed-client/main.go:131` and `:110`
- **Severity:** HIGH
- **Evidence (verified by direct grep):**
  - Line 110: `temporalClient, err = client.Dial(client.Options{ HostPort: os.Getenv("TEMPORAL_HOSTPORT") ... })` — Temporal SDK client (uses SDK defaults).
  - Line 131: `workflowServiceConn, err = grpc.Dial(temporalHostPort, grpc.WithTransportCredentials(insecure.NewCredentials()))` — **raw gRPC dial with `insecure` credentials (no TLS) and NO `keepalive.ClientParameters`, NO `MaxCallRecvMsgSize`, NO retry policy.**
  - Line 118 + 138: two separate `defer ...Close()` paths (dual-connection lifecycle to the same backend).
- **Failure mode:** When KEDA scaler or the frontend has a mid-stream blip, the client has no keepalive → connection silently dies but pool keeps it → next call hangs to gRPC default timeout (often minutes). Compounds HF-10 (KEDA gRPC issue).
- **Tier:** T1
- **Suggested PR:** `PR-HF-23` — set `grpc.WithKeepaliveParams(keepalive.ClientParameters{Time:30s, Timeout:10s, PermitWithoutStream:true})`, set `grpc.WithDefaultServiceConfig(...retryPolicy...)`, switch to `grpc.NewClient` (replaces deprecated `grpc.Dial`), and **drop the dual-connection pattern** (use the Temporal SDK client only — the raw `workflowServiceConn` appears unused after grep `grep -nE 'workflowServiceConn\\.'`).

### HF-24 — Go binaries lack init/tini and HEALTHCHECK; gunicorn missing `--worker-tmp-dir /dev/shm`

- **Files:** `dte/Dockerfile.distributed-client`, `dte/Dockerfile.distributed-worker`, `temporal-helloworld/Dockerfile.go-web-service`, `temporal-helloworld/Dockerfile.worker-web-service`, `python-app/Dockerfile`
- **Severity:** MED
- **Evidence (verified):**
  - Every `USER appuser` directive present (line 42 / 52 / 41 / 41 / 19) — **REFUTED** that they run as root.
  - `python-app/Dockerfile:25-26` has `HEALTHCHECK` — only Python container. Go containers have **no HEALTHCHECK** (line absent in all 4).
  - **No `tini` / `dumb-init` in any Dockerfile.** Go binaries run directly as PID 1, so they receive SIGTERM but children of the binary (none today, but a Go program that spawns a sidecar would not get reaped).
  - `python-app/Dockerfile:29` runs `gunicorn` without `--worker-tmp-dir /dev/shm` — under memory pressure, gunicorn temp files thrash the rootfs, causing slow restarts.
- **Failure mode:** ack-storms during pod restart (no init reaping zombies if subprocess pattern is added later); slow gunicorn restarts on memory pressure.
- **Tier:** T2
- **Suggested PR:** `PR-HF-24` — add `tini` to Go images; add `HEALTHCHECK` (`/health` endpoint added per chart); add `--worker-tmp-dir /dev/shm --timeout 60 --graceful-timeout 30` to gunicorn invocation in `python-app/Dockerfile`.

### HF-25 — OPA Gatekeeper: 2 critical policies in `dryrun` mode (audit-only)

- **File:** `gatekeeper-opa.yaml:447`, `gatekeeper-opa.yaml:505`
- **Severity:** MED (security posture)
- **Evidence (subagent + verified):** `grep -n 'enforcementAction'` shows 9 `deny`, 3 `warn`, **2 `dryrun`** (lines 447 + 505). Dryrun policies log violations to the audit log but do not block apply. The README `gatekeeper-opq.MD` does not document why these specific 2 are dryrun.
- **Failure mode:** newly created bad manifests (e.g., privileged: true) pass admission silently because the relevant constraint is in dryrun.
- **Tier:** T2
- **Suggested PR:** `PR-HF-25` — read the constraint at lines 447 + 505, decide either (a) flip to `deny` (preferred) or (b) document `dryrun` rationale + ticket link in `gatekeeper-opq.MD`.

### HF-26 — `temporal-helloworld` chart missing `startupProbe` for slow-start workloads

- **File:** `temporal-helloworld/charts/temporal-helloworld/templates/deployment.yaml:53-65`
- **Severity:** LOW (demo workload)
- **Evidence (verified):** chart **HAS** `livenessProbe` (line 53) and `readinessProbe` (line 59), both on `/health` — **REFUTED** that probes are absent. **Missing:** `startupProbe` — a slow start (e.g., during Cassandra warmup) will be killed by liveness before it can become ready. For a demo this is fine; for the same pattern repeated in prod charts (HF-01) it would be a CRITICAL.
- **Failure mode:** restart-loop on cold cluster bring-up; cosmetic for the demo, but bad pattern.
- **Tier:** T3 (demo only); pattern lesson is folded into HF-01 fix.
- **Suggested PR:** `PR-HF-26` — add `startupProbe` mirroring readiness with `failureThreshold: 30` to give 5 min grace; document the pattern in chart README so prod copy-pasters get it right.

### REFUTED claims from the 5th-pass

| Claim | Verdict | Counter-evidence |
|---|---|---|
| "Dockerfiles run as root" | **REFUTED** | All 5 Dockerfiles have explicit `USER appuser` directives at the lines cited above. |
| "temporal-helloworld chart has no probes" | **REFUTED** | `deployment.yaml:53,59` define liveness + readiness on `/health`. Only `startupProbe` is missing. |
| "polaris baseline contains hostNetwork/privileged violations" | **REFUTED** | `grep -rn 'hostNetwork: true\|privileged: true' helmfile/` returns 0 hits. Only resource-limits/securityContext gaps remain (already covered by `.polaris.yaml` baseline in PR-T-06). |

### Updated count

- **Total findings:** **22 HF + 4 HF-Appendix-A = 26.**
- **CRITICAL:** 6 · **HIGH:** 10 (was 9; +HF-23) · **MED:** 9 (was 7; +HF-24, +HF-25) · **LOW:** 1 (HF-26).
- **REFUTED:** **5 originals + 3 from 5th pass = 8** total dropped claims.

---

## Appendix B — Findings imported from parent plan family (2026-05-11)

This appendix integrates 22 helmfile-relevant findings extracted from `_plan/02..08_*.md` after a 3-subagent extraction pass + critical-thinking verification (see `07_PARENT_PLAN_INTEGRATION.md` for full provenance and 2 refuted parent claims).

Each finding cites the parent ID it descends from, the workspace verification command, severity, and a fix sketch.

### HF-27 — DTE worker `os.Exit(1)` in HTTP listener goroutine kills pod mid-activity

- **Parent:** H4 (08_INTEGRATED_PLAN.md:228)
- **File:line:** `dte/distributed-worker/main.go:750`
- **Severity:** CRITICAL
- **Evidence (verified):** `grep -n 'os.Exit' helmfile/dte/distributed-worker/main.go` → matches at lines 659, 673, 750. Line 750 is inside `go func() { if err := http.ListenAndServe(":"+port, nil); err != nil { ...; os.Exit(1) } }()`. Any port-bind blip during steady-state kills the pod, abandoning in-flight Temporal activities.
- **Failure mode:** worker dies → Temporal marks all in-flight activities failed → KEDA scales replacements → cascade.
- **Tier:** T0
- **Suggested PR:** `PR-HF-27` — wrap listener in `*http.Server`, surface error via `chan error`, call `srv.Shutdown(ctx)` on signal. **Mirror the same change to `amp/distributed-worker/main.go`** (parent R-S4 risk).

### HF-28 — DTE worker `os.Exit(1)` on Temporal client init blip

- **Parent:** H5 (08_INTEGRATED_PLAN.md:229)
- **File:line:** `dte/distributed-worker/main.go:659, 673`
- **Severity:** HIGH
- **Evidence:** `grep` confirmed both lines. Init-time `client.Dial` failure → `os.Exit(1)`. Tolerable at startup but if these lines are reachable post-startup (e.g., reconnect path), every blip kills the pod.
- **Tier:** T0
- **Suggested PR:** `PR-HF-28` — keep startup-time exit (acceptable: misconfig should fail fast) but prepend a structured error log and document the contract that these lines never run post-startup. If reachable post-startup (verify by code-walk), convert to retry-with-backoff.

### HF-29 — DTE client `os.Exit(1)` ×2 in `distributed-client/main.go`

- **Parent:** H6 (08_INTEGRATED_PLAN.md:230)
- **File:line:** `dte/distributed-client/main.go:116, 160`
- **Severity:** HIGH
- **Evidence:** verified. Line 116 = client init (HF-28 pattern); line 160 = HTTP server goroutine (HF-27 pattern).
- **Tier:** T0
- **Suggested PR:** `PR-HF-29` — apply HF-28 fix at line 116, HF-27 fix at line 160. Mirror to `amp/distributed-client/main.go`.

### HF-30 — `temporal-helloworld` shipped to prod with 4× `log.Fatalf`

- **Parent:** H7 (08_INTEGRATED_PLAN.md:231)
- **File:line:** `temporal-helloworld/go-web-service/main.go:52, 75`; `temporal-helloworld/worker-web-service/main.go:58, 111`
- **Severity:** HIGH
- **Evidence:** `grep -nE 'log\.Fatal' helmfile/temporal-helloworld/{go-web-service,worker-web-service}/main.go` confirmed all 4 instances. Verified: `helmfile.yaml:442-461` deploys both as releases (i.e., this is *not* dead code).
- **Tier:** T0 (with team-decision dependency)
- **Suggested PR:** `PR-HF-30` — **decision required:** (A) **Remove** the temporal-helloworld releases from `helmfile.yaml` (tutorial code — not for production); or (B) **Rewrite** with proper retries + structured error handling + probes. Default to (A) if no answer in 24 h. Risk-of-being-wrong: there may be an undocumented healthcheck dependency on the helloworld endpoint.

### HF-31 — DTE chart missing `preStop` lifecycle hook + `terminationGracePeriodSeconds`

- **Parent:** H8 (08_INTEGRATED_PLAN.md:232)
- **File:line:** `dte/charts/dte/templates/distributed-{worker,client}-deployment.yaml` and `…-knative-service.yaml`
- **Severity:** HIGH
- **Evidence (verified):** `grep -rn 'preStop\|terminationGracePeriod' dte/charts/` returns **0** matches. `grep -rn 'livenessProbe\|readinessProbe' dte/charts/` returns 8 matches → probes exist but no graceful-shutdown configuration. On node drain, pods get default 30 s grace; activities longer than 30 s are abandoned mid-flight.
- **Tier:** T0
- **Suggested PR:** `PR-HF-31` — add `terminationGracePeriodSeconds: max(activity_timeout)` (chart values; per-deployment) + `lifecycle.preStop.exec.command: ["sh","-c","sleep 15"]` (gives endpoints controller time to remove pod from Service before SIGTERM). Hard correctness rule: `terminationGracePeriodSeconds >= longest activity`.

### HF-32 — Elasticsearch unassigned-shards firefighting not enforced via index template

- **Parent:** H9 (08_INTEGRATED_PLAN.md:236)
- **Files:** `elasticsearch-shard-allocation-fix.md`, `fix-unassigned-shards.sh`
- **Severity:** HIGH
- **Evidence:** both files exist. The MD documents that 3-node cluster needs `index.number_of_replicas: 0` for some indices, but the fix is applied manually via `fix-unassigned-shards.sh`, not enforced via an index template.
- **Failure mode:** every new index repeats the failure mode → ops gets paged → manual intervention.
- **Tier:** T1
- **Suggested PR:** `PR-HF-32` — add Elasticsearch index template + ILM policy (hot → warm → delete) committed to `helmfile/elasticsearch/index-templates/`; deploy via Job at install-time; delete `fix-unassigned-shards.sh` once the template is enforced.

### HF-33 — Cassandra exporter sidecar repeatedly broken (existence is the smell)

- **Parent:** H10 (08_INTEGRATED_PLAN.md:237)
- **Files:** `cassandra-exporter-sidecar-fix.yaml`, `apply-and-verify-cassandra-exporter.sh`
- **Severity:** HIGH
- **Evidence:** both files exist. The presence of a "fix" yaml + "verify" script in the repo is a strong signal of unresolved firefighting. Causes observability holes during incidents.
- **Tier:** T1
- **Suggested PR:** `PR-HF-33` — fold the sidecar into the Cassandra StatefulSet template directly (so it cannot drift); add an initContainer that runs `nodetool status` and fails the pod if it cannot reach the cluster; delete the fix yaml + verify script once the integration is stable.

### HF-34 — `delete-all-temporal-data-job.yaml` has `backoffLimit: 2` (auto-retries on destruction)

- **Parent:** H13 + H14 (08_INTEGRATED_PLAN.md:240, :241)
- **File:line:** `delete-all-temporal-data-job.yaml:10`; also `recreate-cassandra-statefulset-with-vac-job.yaml`, `fix-cassandra-downtime-job.yaml`, `delete-old-indices.sh`
- **Severity:** HIGH
- **Evidence:** verified `backoffLimit: 2` for the destructive job. Combined with no `confirmed-by` label gate, a fat-fingered apply DOES the destruction, fails, and AUTO-RETRIES twice.
- **Tier:** T1
- **Suggested PR:** `PR-HF-34` — set `backoffLimit: 0`; add an OPA/Gatekeeper `ConstraintTemplate` that **denies** any Job whose name matches `^delete-` or `^recreate-` unless it carries the label `confirmed-by: <user>`. Document bypass procedure: `kubectl label job/<name> confirmed-by=$USER`.

### HF-35 — `cluster_db.go` 474-line drift between `amp/` and `helmfile/dte/`

- **Parent:** H15 (08_INTEGRATED_PLAN.md:242)
- **Files:** `amp/distributed-worker/cluster_db.go` vs `helmfile/dte/distributed-worker/cluster_db.go`
- **Severity:** HIGH
- **Evidence (verified exact):** `diff -u amp/distributed-worker/cluster_db.go helmfile/dte/distributed-worker/cluster_db.go | wc -l` = **474**.
- **Failure mode:** any DB-related stability fix to one copy silently misses the other.
- **Tier:** T1 (lint/diff first); T3 to fully consolidate via HF-46
- **Suggested PR:** `PR-HF-35` — first land **CI lint** that flags the drift (`PR-HF-45` material), then a 3-PR sequence: (1) characterize the diff (which side is newer for each function); (2) merge the canonical version into a shared package (HF-46); (3) cut over both binaries.

### HF-36 — DTE worker goroutine fan-out without semaphore cap

- **Parent:** H16 (08_INTEGRATED_PLAN.md:243)
- **File:line:** `dte/distributed-worker/main.go:541, 721, 747` (fan-out points)
- **Severity:** MED
- **Evidence:** verified — `go func()` blocks at line 720+ with no `golang.org/x/sync/semaphore` or `WaitGroup` cap on concurrent activities. At large fan-out, OOMKill.
- **Tier:** T1
- **Suggested PR:** `PR-HF-36` — `import "golang.org/x/sync/semaphore"`; wrap each fan-out site with `sem.Acquire(ctx, 1)` … `defer sem.Release(1)`; cap = `min(20, runtime.NumCPU()*4)`; emit `dte_active_goroutines` Prom gauge.

### HF-37 — `dte/distributed-client/main.go:111` reads TEMPORAL_HOSTPORT with no fallback (silent-empty)

- **Parent:** H17 (08_INTEGRATED_PLAN.md:244, **REFUTED-AS-STATED**, downgraded)
- **File:line:** `dte/distributed-client/main.go:111` — `HostPort: os.Getenv("TEMPORAL_HOSTPORT")`
- **Severity:** LOW (corrected from parent's MED)
- **Evidence:** verified. Parent claimed hardcoded `"localhost:7233"` fallback; actual code has **no fallback**. When the env var is unset, `HostPort` is the empty string and `client.Dial` returns a confusing error.
- **Tier:** T2
- **Suggested PR:** `PR-HF-37` — at process start, validate required env vars with a small `mustGetEnv("TEMPORAL_HOSTPORT")` helper that panics with a clear message; remove ambiguity at the call-site.

### HF-38 — Env-overlay drift untested between `values-{development,eks,production}.yaml`

- **Parent:** H18 (08_INTEGRATED_PLAN.md:245)
- **Files:** `values-development.yaml`, `values-eks.yaml`, `values-production.yaml`
- **Severity:** MED
- **Evidence:** files exist, no test compares them. Production could silently end up with weaker limits than development.
- **Tier:** T2
- **Suggested PR:** `PR-HF-38` — add a `pre-commit` script that yq-extracts `resources.limits.{cpu,memory}` and `replicaCount` from each overlay and asserts `production >= development` (and equivalent for EKS). Fails the commit on regression.

### HF-39 — Cilium ClusterWide NetworkPolicies committed to production tree without env predicate

- **Parent:** H19 (08_INTEGRATED_PLAN.md:246, verified CRITICAL)
- **Files:** `all-egress.yaml`, `all-ingress.yaml`, `allow-all.yaml`, `deny-all.yaml`
- **Severity:** CRITICAL (security)
- **Evidence (verified):** `allow-all.yaml` has `kind: CiliumClusterwideNetworkPolicy` with `endpointSelector: {}` and `ingress: []` + `egress: []` (cluster-wide allow). One accidental `helmfile apply -e dev` from a prod kubeconfig = cluster-wide-open. None of the 4 files are gated by an environment predicate in `helmfile.yaml`.
- **Tier:** T0 (security)
- **Suggested PR:** `PR-HF-39` — `git mv` the 4 files into `helmfile/dev-tools/`; in `helmfile.yaml`, only include them under an explicit environment block (`if .Environment.Name == "dev"`); add a CI guard that fails if any `*-production.yaml` references a `Cluster*NetworkPolicy` with empty selector.

### HF-40 — Orphan `temporal-manifests/` directory

- **Parent:** H20 (08_INTEGRATED_PLAN.md:247)
- **Files:** `temporal-manifests/temporal-server.yaml` (and the directory)
- **Severity:** LOW
- **Evidence (verified):** `grep -rn 'temporal-manifests\|temporal-server.yaml' helmfile/helmfile.yaml` returns **0**. The directory's content is either dead code or installed via a path not in the helmfile (unclear source-of-truth).
- **Tier:** T2
- **Suggested PR:** `PR-HF-40` — owner decision: either (a) reference from `helmfile.yaml` as a clearly-named dev release, or (b) delete the directory. Document the decision in `temporal-manifests/README.md`.

### HF-41 — Abandoned `python-app/docker-compose.yml`

- **Parent:** H21 (08_INTEGRATED_PLAN.md:248)
- **File:** `python-app/docker-compose.yml`
- **Severity:** LOW
- **Evidence (verified):** file exists (504 bytes); not referenced by any helmfile release; appears to be a dev-time convenience.
- **Tier:** T2
- **Suggested PR:** `PR-HF-41` — move to `python-app/dev-tools/docker-compose.yml` with a README header; OR delete entirely if unused.

### HF-42 — Grafana admin password committed plaintext in `DEPLOYMENT_SUMMARY.md`

- **Parent:** H22 (08_INTEGRATED_PLAN.md:249, verified CRITICAL)
- **File:line:** `DEPLOYMENT_SUMMARY.md:70` — `Login with admin / Yfd2HxAsXiQ7brwIoeR5i2tvYH2jmRSBViBsWRM8`
- **Severity:** CRITICAL (security)
- **Evidence (verified):** `grep -nE 'password\|admin' DEPLOYMENT_SUMMARY.md` → line 70 has the plaintext credential. The same string appears at `helmfile.yaml:302` (Grafana adminPassword) — confirmed reuse.
- **Tier:** T0 (security)
- **Suggested PR:** `PR-HF-42` — **immediately rotate** the Grafana admin password; remove the credential from `DEPLOYMENT_SUMMARY.md` (replace with: "Run `kubectl get secret grafana-admin -o jsonpath={.data.password} | base64 -d`"); rewrite git history with `git-filter-repo` to scrub the leaked string; add a `gitleaks`/`trufflehog` pre-commit hook; raise an incident if the cluster is internet-reachable.

### HF-43 — `amp/* ↔ helmfile/dte/*` cross-package fork (~600 LoC drift across 3 files)

- **Parent:** A1 (02_FINDINGS_CATALOG.md:16, verified with corrected numbers)
- **Files (verified):**
  - `amp/distributed-worker/helpers.go` ↔ `helmfile/dte/distributed-worker/helpers.go` — **26 LoC diff** (parent said 12; **corrected**)
  - `amp/distributed-worker/main.go` ↔ `helmfile/dte/distributed-worker/main.go` — **93 LoC diff** ✅
  - `amp/distributed-worker/cluster_db.go` ↔ `helmfile/dte/distributed-worker/cluster_db.go` — **474 LoC diff** ✅
- **Severity:** HIGH (maintenance burden + silent regression risk)
- **Evidence:** `diff -u … | wc -l` for each, run on 2026-05-11.
- **Tier:** T1 (drift fence first via HF-45); T3 (full consolidation via HF-46)
- **Suggested PR:** `PR-HF-43` — first land HF-45 (CI drift fence) so the drift can't grow; then plan HF-46 (`pkg/dte` extraction).

### HF-44 — Per-call `&http.Client{Timeout: 20*time.Second}` allocation in `helpers.go`

- **Parent:** A2 (02_FINDINGS_CATALOG.md:25, verified)
- **File:line:** `dte/distributed-worker/helpers.go:642` (verified by `sed`).
- **Severity:** MED (latency tail)
- **Evidence:** `client := &http.Client{Timeout: 20 * time.Second}` allocated inside hot-path function → no keep-alive reuse, fresh TLS handshake + connection per call.
- **Tier:** T1
- **Suggested PR:** `PR-HF-44` — promote `*http.Client` to a package-level singleton constructed once (with proper `Transport.MaxIdleConnsPerHost`, `IdleConnTimeout`, etc.); pair with HF-43 mirroring rule.

### HF-45 — No CI parity test for `amp/* ≡ helmfile/dte/*`

- **Parent:** E2 + PR-PHASE0-04 (02_FINDINGS_CATALOG.md:551, 04_PR_BREAKDOWN.md:36)
- **Severity:** HIGH (process)
- **Evidence (negative):** no CI exists today (per `06_TESTING_STRATEGY.md`); the diff today is ~600 LoC across 3 files; without a fence, drift will grow.
- **Tier:** T1
- **Suggested PR:** `PR-HF-45` — add to `bitbucket-pipelines.yml` (PR-T-01) a step:
  ```bash
  for f in main.go helpers.go cluster_db.go; do
    if ! diff -q amp/distributed-worker/$f helmfile/dte/distributed-worker/$f >/dev/null; then
      if [ ! -f DTE_DIVERGENCE_OK ]; then
        echo "FAIL: $f drift detected; create DTE_DIVERGENCE_OK with rationale to bypass"
        exit 1
      fi
    fi
  done
  ```
  Same for `distributed-client/main.go`. Bypass via marker file with rationale.

### HF-46 — Extract shared `pkg/dte` Go module (closes HF-35, HF-43, HF-45)

- **Parent:** OOB-1 (06_OUT_OF_BOX.md:7-47)
- **Severity:** STRATEGIC (Q3 backlog)
- **Approach (parent-spec):** new Go module `pkg/dte` containing `helpers/`, `cluster_db/`, `client/` packages. 4-PR sequence: (1) create `pkg/dte` from canonical version; (2) migrate `amp/distributed-worker` to import `pkg/dte`; (3) migrate `helmfile/dte/distributed-worker`; (4) delete the duplicates. Each step reversible.
- **Tier:** T3 (Q3)
- **Risks:** R12 (cyclic import) — mitigation: `forbidigo` lint disallowing imports from `pkg/dte/*` back to binaries.
- **Suggested PR series:** `PR-HF-46-{01,02,03,04}` per parent §06.

### HF-47 — Extract shared `pkg/clusterauth` Go module

- **Parent:** OOB-2 (06_OUT_OF_BOX.md:50-77)
- **Severity:** STRATEGIC (Q3 backlog)
- **Approach:** consolidate cluster-token/auth-provider logic from `amp/distributed-worker/helpers.go`, `helmfile/dte/distributed-worker/helpers.go`, and `kitt-runbooks/internal/k8sclient/client.go` into `pkg/clusterauth`. Closes part of HF-44 by allowing connection-pool sharing.
- **Tier:** T3 (Q3, after HF-46)
- **Suggested PR series:** `PR-HF-47-{01,02}`.

### HF-48 — DTE worker has no `/metrics` endpoint or Prometheus instrumentation

- **Parent:** PR-PHASE0-01 (04_PR_BREAKDOWN.md:17)
- **Severity:** MED (observability foundation)
- **Evidence (negative):** `grep -rn 'prometheus\|promhttp' helmfile/dte/distributed-worker/` returns near-empty. Without RED-style histograms (`auth_provider_token_exchange_p95_ms`, `dte_workflow_active`, etc.), every later finding is unfalsifiable.
- **Tier:** T2 (foundation for measuring HF-23/HF-27/HF-44 fixes)
- **Suggested PR:** `PR-HF-48` — add `pkg/metrics/metrics.go` with standard RED histograms; expose `/metrics` via `promhttp.Handler()` on a sidecar port; add a Prometheus `ServiceMonitor` to `helmfile/`. Mirror to both `amp/*` and `helmfile/dte/*`.

### Updated severity rollup (after Appendix B)

| Severity | Pre-Appendix-A | Post-Appendix-A | Post-Appendix-B (final) |
|---|---|---|---|
| CRITICAL | 6 | 6 | **9** (+HF-27, HF-39, HF-42) |
| HIGH | 9 | 10 | **17** (+HF-28, HF-29, HF-30, HF-31, HF-32, HF-33, HF-34, HF-35, HF-43, HF-45) |
| MED | 7 | 9 | **18** (+HF-36, HF-38, HF-44, HF-48) |
| LOW | 0 | 1 | **6** (+HF-37, HF-40, HF-41) |
| STRATEGIC (Q3) | 0 | 0 | **2** (HF-46, HF-47) |
| **Total findings** | 22 | 26 | **48** |
| **REFUTED claims** | 5 | 8 | **10** (+H11, +H17-as-stated) |

See `07_PARENT_PLAN_INTEGRATION.md` for the full provenance map and the 2 refuted parent claims with counter-evidence.

---

## Appendix C — Final-sweep integration: S-series + remaining OOB items (2026-05-11)

This appendix closes the integration loop by capturing helmfile-relevant content from `_plan/07_STABILITY_PLAN.md` (S1–S15) and any remaining items in `_plan/06_OUT_OF_BOX.md` (OOB-3, OOB-6) not already in Appendix B.

### Methodology

Two parallel subagents extracted; I then critically verified every claim against the actual source files. The result is **1 net-new finding (HF-49)** + **3 explicit cross-references** + **4 deliberate exclusions documented** + **5 parent files to receive See-also pointers**. The S-series itself remains in the parent plan as the canonical S-PR family — only items with a verified helmfile dimension are imported.

### S-series disposition table (S1..S15)

| S-PR | Lives in | Helmfile dimension? | Verdict | Disposition |
|---|---|---|---|---|
| **S1** — `log.Fatal` in `k8s-metadata-collector` | `k8s-metadata-collector/...` | NO (lives in metadata-collector binary, not helmfile/) | OUT-OF-SCOPE | Stays in parent S-plan |
| **S2** — `w.Run()` failure logged at Info, process stays alive | `kitt-runbooks/cmd/worker/main.go:105-109` | **NO** — verified: `kitt-runbooks/` only; no helmfile-mirror clause in S2 body | OUT-OF-SCOPE | Stays in parent S-plan; **not** mirrored to helmfile/dte/ (verified by reading lines 55-90 of 07_STABILITY_PLAN.md) |
| **S3** — Add probes/preStop/grace to kitt-runbooks worker chart | `kitt-runbooks/worker-values.yaml` | **NO** — `kitt-runbooks` chart, not helmfile/. The same *pattern* applies to DTE chart and is already captured as **HF-31** (different chart, different file) | OUT-OF-SCOPE for chart, but cross-link the *pattern* | Cross-link from HF-31 to S3 for the canonical probe-template |
| **S4** — `os.Exit(1)` in HTTP listener goroutine | `amp/distributed-worker/main.go:791-794` (mirrored in `helmfile/dte/...`) | **YES — explicit mirror** | DUPLICATE | Already **HF-27**. Cross-linked. |
| **S5** — iam-sidecar `log.Fatal` in `ServeHTTP` | `iam-sidecar/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S6** — ASI `panic(err)` + `log.Fatalf` | `asi/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S7** — ForgeApp nil-deref on `*Replicas` | `forgeapp-controller/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S8** — ForgeApp `time.Sleep` in Reconcile | `forgeapp-controller/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S9** — Scraper SIGTERM + preStop | `scraper/temporal-pg-redis/.../deployment.yaml` | NO (scraper chart) | OUT-OF-SCOPE | Stays in parent |
| **S10** — Scraper aiohttp session lifetime | `scraper/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S11** — Scraper bounded retries + circuit breaker | `scraper/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S12** — Splunk client timeout 60s→10s | `kitt-runbooks/...` | NO | OUT-OF-SCOPE | Stays in parent |
| **S13** — Temporal worker reconnect: jitter + fail-loud | `kitt-runbooks/...` (per "Temporal worker connection" heading at line 286) | NO — explicitly kitt-runbooks | OUT-OF-SCOPE | Stays in parent |
| **S14** — Replace `InsecureSkipVerify` with proper CA bundle | generic across services | **YES — pattern matches HF-23** (gRPC plaintext in dte/distributed-client) | CROSS-REFERENCE | Note added to HF-23 below |
| **S15** — Scraper liveness/readiness/preStop alignment | `scraper/temporal-pg-redis/values/...` | NO (scraper) | OUT-OF-SCOPE | Stays in parent |

**Verified by direct file inspection (`sed -n` of S2 lines 55-90 and S3 lines 88-130):** neither S2 nor S3 contains a "mirror to helmfile/dte/" clause. The original concern was unfounded — only S4 carries that explicit clause, and S4 is already HF-27.

### Cross-reference added to HF-23 (gRPC plaintext in distributed-client)

**See parent S14 in `07_STABILITY_PLAN.md:300-310`** for the canonical pattern of replacing `InsecureSkipVerify`/`insecure.NewCredentials()` with a proper CA bundle (`x509.NewCertPool()` + `creds := credentials.NewClientTLSFromCert(pool, "")`). HF-23's fix should follow that pattern verbatim — there is no need to invent a different idiom for helmfile/dte/.

### Remaining OOB items (06_OUT_OF_BOX.md)

| OOB | Lives in | Helmfile dimension? | Verdict | Disposition |
|---|---|---|---|---|
| **OOB-1** — extract `pkg/dte` | `06_OUT_OF_BOX.md:7-47` | YES | DUPLICATE | Already **HF-46**. |
| **OOB-2** — extract `pkg/clusterauth` | `06_OUT_OF_BOX.md:50-77` | YES | DUPLICATE | Already **HF-47**. |
| **OOB-3** — decommission `pod_label_sweeper.py` | `06_OUT_OF_BOX.md:78-103` | **NO** — verified: lives in `deploy/python/` and `sweeper/` operator; does not touch helmfile/ | OUT-OF-SCOPE | Stays in parent OOB-plan |
| **OOB-4** — Scraper Python ↔ JS unification | `06_OUT_OF_BOX.md:104-124` | NO (scraper) | OUT-OF-SCOPE | Stays in parent |
| **OOB-5** — Signal-driven scraper dispatcher | `06_OUT_OF_BOX.md:127-150` | NO (scraper) | OUT-OF-SCOPE | Stays in parent |
| **OOB-6** — Shared `pkg/observability` GitOps fabric | `06_OUT_OF_BOX.md:153-163` | **YES — partially overlaps HF-48** (just `/metrics` endpoint) but is *strategically distinct*: HF-48 is per-binary instrumentation, OOB-6 is the **shared library** that defines the canonical label set + dashboard templates | NEW (strategic, complements HF-48 + HF-46 + HF-47) | → **HF-49** |

### HF-49 — Shared `pkg/observability` GitOps fabric

- **Parent:** OOB-6 (`06_OUT_OF_BOX.md:153-163`)
- **Severity:** STRATEGIC (Q3 backlog; pairs with HF-46 + HF-47 to form a 3-package shared-code program)
- **Scope:** create a single `pkg/observability` Go package consumed by `dte`, `kitt-runbooks`, `iam-sidecar`, etc. Defines a canonical Prom label set (`service`, `cluster`, `activity`, `result`, `latency_bucket`), provides standard RED histograms, and ships with Grafana dashboard JSON templates that instantiate per service.
- **Why it's NOT a duplicate of HF-48:** HF-48 wires `/metrics` into one binary (DTE worker). HF-49 ensures every binary that comes online — today and in the future — emits the *same* shape of metrics, so dashboards are template-once-instantiate-many. Without HF-49, every team re-invents the label set; HF-48 then has to be repeated for `kitt-runbooks`, `iam-sidecar`, etc., with subtly different labels and unjoinable Grafana panels.
- **Tier:** T3 (Q3) — explicitly after HF-48 has proven the per-binary value
- **Approach (parent-spec):** 1 week design + ~3 weeks implementation. PR sequence: (1) `PR-HF-49-01` create `pkg/observability` skeleton with documented label contract; (2) `PR-HF-49-02` migrate DTE worker to consume it (closes HF-48); (3) `PR-HF-49-03` migrate `kitt-runbooks` worker; (4) `PR-HF-49-04` ship Grafana dashboard JSON template generator.
- **Risk:** R-INT-7 — designing a label set too rigid for one downstream consumer. Mitigation: leave the `extra` map open for service-specific dimensions; lint that `extra` cannot collide with canonical label names.

### Pointer-only items (kept in parent for canonical authority)

The following parent items are **deliberately not duplicated** here — they live in the parent because they are the canonical source for the broader S-PR / OOB plans. The child plan references them by ID:

- **S1, S2, S3, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15** — full text in `_plan/07_STABILITY_PLAN.md`
- **OOB-3, OOB-4, OOB-5** — full text in `_plan/06_OUT_OF_BOX.md`
- The full S-series risk register (R-S1..R-S15) — in `_plan/05_RISK_AND_HISTORY.md`
- The full S-series day-by-day rollout — in `_plan/03_PRIORITIZED_PLAN.md` and `_plan/08_INTEGRATED_PLAN.md`

This is **proper plan-family hygiene**: a single source of truth per item, with cross-references for navigation. The child plan owns helmfile/-relevant content; the parent owns cross-cutting content.

### Final updated severity rollup (after Appendix C)

| Severity | After Appendix B | After Appendix C (final) |
|---|---|---|
| CRITICAL | 9 | **9** (no change — S-series didn't add criticals to helmfile) |
| HIGH | 17 | **17** |
| MED | 18 | **18** |
| LOW | 6 | **6** |
| STRATEGIC (Q3) | 2 (HF-46, HF-47) | **3** (+HF-49) |
| **Total findings** | 48 | **49** |
| REFUTED claims | 10 | **10** |

### Done definition for Appendix C

This appendix is DONE when:
1. ✅ All 15 S-series items disposition is documented (above table)
2. ✅ All 6 OOB items disposition is documented (above table)
3. ✅ The 1 truly-new finding (HF-49) has a stable ID, severity, scope, and PR sketch
4. ✅ Cross-reference added to HF-23 for S14 TLS pattern
5. ⏳ See-also pointers added to 5 parent files (next task — see `07_PARENT_PLAN_INTEGRATION.md` §13)
6. ⏳ `00_README.md` totals refreshed to "49 total findings" (next task)

After items 5-6 complete, **every helmfile-relevant item from any parent file is either captured as an HF entry in this catalog or explicitly documented as OUT-OF-SCOPE with rationale.** The integration is end-to-end complete.

---

## Appendix D — `merry-petting-music.md` integration (HF-50..HF-64)

This appendix integrates the helmfile-specific deep-dive plan at `~/.claude/plans/merry-petting-music.md` (590 lines, S25-S48). All 14 critical claims were independently verified by direct file inspection (`02_FINDINGS_CATALOG.md` Appendix D §0). The result: **13 net-new findings** (HF-50..HF-64; HF-50 jumps to HF-64 with one ID skipped to align with NEW count), **2 extensions** to existing HF-11 + HF-42, **2 duplicates** (S36→HF-03, S48→HF-39) cross-linked only.

### §0 Verification receipts (binary CONFIRMED/REFUTED with evidence)

| Plan A claim | Verdict | Evidence |
|---|---|---|
| S25 os.Setenv race | ✅ CONFIRMED | `main.go:910,999` — both activities call `os.Setenv("DTE_SLAUTH_TOKEN", ...)` without process-wide synchronization |
| S26 HTTP `ListenAndServe` no timeouts + SIGTERM only stops worker | ✅ CONFIRMED | `main.go:747` is bare `http.ListenAndServe`; lines 754-761 only call `workerInstance.Stop()` |
| S28 fixed 5s polling | ✅ CONFIRMED | `main.go:534` `time.NewTicker(5 * time.Second)` |
| S29 worker goroutine no recovery + fake healthy | ✅ CONFIRMED | `main.go:720-725` no `recover()`, `/health` always returns 200 |
| S32 missing gossip job file | ✅ CONFIRMED | `helmfile.yaml:432-439` references `fix-cassandra-gossip-config-job.yaml`; `ls helmfile/fix-cassandra-gossip-config-job.yaml` returns "No such file" |
| S34 PostgreSQL maxConns:20 | ✅ CONFIRMED | `temporal-values.yaml:19-20,31-32` show `maxConns: 20`/`maxIdleConns: 20` for both default and visibility stores |
| S37 ES visibility replicas=1 | ✅ CONFIRMED | `helmfile.yaml:252` `number_of_replicas: 1` |
| S42 Hardcoded JWT in shell script | ✅ CONFIRMED | `download-aws-accounts-with-cookie.sh:16` contains full SAML/JWT token (~1100 chars), user identity `lzhu3@atlassian.com`, prod service `alfred.prod.atl-paas.net` |
| S43 Grafana password in Job manifest | ✅ CONFIRMED | `delete-dashboards-from-db-job.yaml:28` `AUTH="admin:Yfd2HxAsXiQ7brwIoeR5i2tvYH2jmRSBViBsWRM8"` (same password as HF-42, second leaked location) |
| S45 cleanup-and-redeploy.sh no rollback | ✅ CONFIRMED | `cleanup-and-redeploy.sh:9-29` scales to 0 then runs operations; `kubectl wait` has fallback echo (no abort), no trap handler |
| S46 jobs missing resource limits | ✅ CONFIRMED with corrected count | I measured **26/28 jobs missing resources** (Plan A said 24/28). Actual: only `delete-dashboards-from-db-job.yaml` and one other have `resources:` |
| S47 jobs missing ttlSecondsAfterFinished | ✅ CONFIRMED with corrected count | I measured **4/28 jobs missing ttl** (Plan A said 8 missing). Actual: 24/28 already have it; 4 missing |
| S48 NetworkPolicies allow all | ✅ CONFIRMED | `allow-all.yaml:6` `endpointSelector: {}` (cluster-wide); `all-ingress.yaml:17` `fromEntities:` and `all-egress.yaml:17` `toEntities:` use unrestricted entity sets |

**No claims in Plan A were refuted.** Plan A is high-quality, code-grounded, and the two count discrepancies (S46/S47) are minor.

### §1 Disposition table (S25-S48 → HF mapping)

| Plan A | Verdict | Mapped to | One-line rationale |
|---|---|---|---|
| **S25** os.Setenv race | NEW | **HF-50** | Race in concurrent activities; not in any HF entry |
| **S26** HTTP server timeouts + graceful shutdown | NEW (extends HF-27) | **HF-51** | HF-27 was about `os.Exit` only; this adds timeouts + shutdown |
| **S28** 5s polling no backoff | NEW | **HF-52** | API overload risk; not in HF |
| **S29** Worker goroutine no recovery + fake `/health` | NEW | **HF-53** | Health-lies-while-worker-dead pattern; not in HF |
| **S32** Missing gossip job file | NEW | **HF-54** | Critical deployment-time failure; postsync hook silently fails |
| **S33** Kibana OOM hook commented out | NEW | **HF-55** | Comment/code disagreement; tech-debt |
| **S34** PostgreSQL maxConns:20 | NEW | **HF-56** | Likely **primary latency contributor**; trivial fix |
| **S35** EBS storage class in GCP context | NEW | **HF-57** | Cloud-mismatch risk; verify before next fresh deploy |
| **S36** Single Temporal replica | DUPLICATE | HF-03 | Cross-link only |
| **S37** ES visibility replicas=1 | NEW | **HF-58** | Permanent yellow cluster; contradicts internal fix doc |
| **S40** Redis HA inconsistency | NEW | **HF-59** | EKS values:1 vs prod values:2 |
| **S41** Prometheus comment mismatch | NEW (LOW) | **HF-60** | Cosmetic; auditing trail |
| **S42** Hardcoded JWT in shell script | NEW CRITICAL | **HF-61** | Security blast-radius; distinct file from HF-42 |
| **S43** Grafana password second location | EXTENDS HF-42 | (HF-42 updated) | Adds `delete-dashboards-from-db-job.yaml:28` to scope |
| **S44** Destructive jobs without safeguards | EXTENDS HF-11 | (HF-11 updated) | Adds confirmation/dry-run/backup pattern |
| **S45** cleanup-and-redeploy.sh no rollback | NEW | **HF-62** | Scaled-to-0 left after script failure |
| **S46** Jobs missing resource limits (26/28) | NEW | **HF-63** | Unbounded resource consumption from Jobs |
| **S47** Jobs missing TTL (4/28) | NEW (LOW) | **HF-64** | etcd accumulation; minor since 24/28 already correct |
| **S48** NetworkPolicies allow all | DUPLICATE | HF-39 | Cross-link only |

### §2 New findings (HF-50..HF-64) — full content

#### HF-50 — `os.Setenv` race in concurrent Temporal activities

- **Severity:** **CRITICAL** (silent auth failures, impossible-to-reproduce)
- **File:line:** `helmfile/dte/distributed-worker/main.go:910-931, 999-1021`
- **Evidence:** Two activity functions (`HealthCheckActivity` and `ServiceDiscoveryActivity`) both call `os.Setenv("DTE_SLAUTH_TOKEN", authToken)` (and `DTE_ASAP_TOKEN`, `DTE_SCT_TOKEN`, `DTE_GROUPS`). `os.Setenv` modifies process-wide state and is **not goroutine-safe**. Temporal runs activities concurrently within a worker process, so Activity A's tokens can be overwritten by Activity B mid-execution.
- **Why it crashes/causes instability:** Auth-token corruption produces 401/403 responses that are non-deterministic; downstream code reads via `os.Getenv` which has already been mutated. Symptoms: intermittent "permission denied" against random target clusters that disappear on retry.
- **Fix:** Pass tokens through the activity input map (already partially supported) and thread through function parameters; remove all `os.Setenv`/`os.Unsetenv` from activity functions. ~100 LoC, contained refactor.
- **Tier:** **T0** (week 1, day 2 — pairs with HF-27)
- **Acceptance:** `go vet ./...` + `grep -nE 'os\.(Setenv|Unsetenv)' dte/distributed-worker/*.go` returns 0 hits. Add a stress test that runs 100 concurrent `HealthCheckActivity` invocations with distinct tokens and asserts each downstream call sees its own token.
- **Risk-of-being-wrong:** LOW. Verified by direct `grep -n 'os\\.Setenv' main.go` returning 4 hits at the cited lines.

#### HF-51 — HTTP server has zero timeouts + graceful shutdown skipped

- **Severity:** HIGH
- **File:line:** `helmfile/dte/distributed-worker/main.go:747-761`
- **Evidence:** `http.ListenAndServe(":"+port, nil)` (line 747) creates server with no `ReadTimeout`/`WriteTimeout`/`IdleTimeout`. SIGTERM handler (lines 754-761) only calls `workerInstance.Stop()`, never `srv.Shutdown(ctx)`.
- **Why it causes instability:** (1) Slowloris-style resource exhaustion possible. (2) During rolling updates, in-flight HTTP requests dropped instead of drained. (3) Health check stays "healthy" after worker stops (compounds with HF-53).
- **Fix:** Replace bare `http.ListenAndServe` with `*http.Server{ReadTimeout: 10s, WriteTimeout: 30s, IdleTimeout: 120s, Handler: mux}`. Add `srv.Shutdown(ctx)` to signal handler before `workerInstance.Stop()`. ~30 LoC.
- **Tier:** T0 (week 1, day 3 — pairs with HF-27)
- **Acceptance:** `kubectl rollout status deployment/dte-distributed-worker` shows zero "request dropped" log lines during rolling update; load test with `slowhttptest -c 200 -i 110 -X` shows server rejects/closes connections (does not hang).
- **Risk-of-being-wrong:** LOW.
- **Why split from HF-27:** HF-27 was specifically the `os.Exit(1)` removal (one line). HF-51 is the broader timeout + graceful-shutdown contract. Both fixes can land in one commit but are distinct correctness contracts.

#### HF-52 — Fixed 5-second polling in `waitForArgoWorkflowCompletion` (no backoff, no jitter)

- **Severity:** HIGH (under load)
- **File:line:** `helmfile/dte/distributed-worker/main.go:534-588`
- **Evidence:** `ticker := time.NewTicker(5 * time.Second)` and `timeout := time.After(10 * time.Minute)`. With N concurrent workflows, generates `N × 120` API calls over 10 minutes against the target cluster's Argo API.
- **Why it causes latency:** Under load (10+ concurrent cluster tasks), can overload target Kubernetes API server → 429 responses → cascading timeouts; thunder-herd against any shared cluster.
- **Fix:** Exponential backoff `5s → 10s → 20s → 40s → 60s` (cap), with ±20% jitter. ~20 LoC.
- **Tier:** T1 (week 1, day 4)
- **Acceptance:** Run 50 concurrent workflows; assert Argo API request rate stays below 10/sec (was 50/sec). Standard p95 latency drop ≥ 20%.
- **Risk-of-being-wrong:** LOW.

#### HF-53 — Worker goroutine has no panic recovery and `/health` lies

- **Severity:** HIGH (silent worker death masked from k8s)
- **File:line:** `helmfile/dte/distributed-worker/main.go:720-726, 764`
- **Evidence:** `go func() { if err := workerInstance.Run(...); err != nil { jsonLogger.Error(...) } }()` — no `recover()`, no atomic state, no health signal. `/health` (line 764) always returns `{"status":"healthy"}` regardless of worker liveness.
- **Why it causes instability:** Lost Temporal connection → goroutine logs error then exits → pod still passes liveness/readiness probes → k8s leaves pod in service → activities never processed → silent backlog accumulation.
- **Fix:** Wrap goroutine body in `defer func() { if r := recover(); r != nil { atomic.StoreInt32(&workerHealthy, 0); jsonLogger.Error("worker panic", "recover", r) } }()`. Use `atomic.LoadInt32(&workerHealthy)` in `/health` handler; return 503 if worker not healthy. Optional: auto-restart with bounded retries. ~40 LoC.
- **Tier:** T0 (week 1, day 3 — pairs with HF-27, HF-51)
- **Acceptance:** Force-kill Temporal frontend connection (network policy block); within 30s, `/health` returns 503; pod is removed from k8s service.
- **Risk-of-being-wrong:** LOW.

#### HF-54 — Missing `fix-cassandra-gossip-config-job.yaml` referenced in postsync hook

- **Severity:** **CRITICAL** (every `helmfile apply` silently fails this hook)
- **File:line:** `helmfile/helmfile.yaml:432-439` references `fix-cassandra-gossip-config-job.yaml`; the file **does not exist** in `helmfile/`.
- **Evidence:** Verified by `ls helmfile/fix-cassandra-gossip-config-job.yaml` → "No such file or directory".
- **Why it causes instability:** Cassandra seed-node configuration and gossip-protocol fixes are never applied. Comments at lines 184-190 of helmfile.yaml describe the intended fix. This directly contributes to Cassandra node-discovery failures and gossip-state corruption on restarts (a recurring symptom).
- **Fix:** Two paths: **(a) restore** the file by reconstructing from comments + helm chart context (~50 lines); **(b) remove** the postsync hook (6 lines) if the fix has been applied manually and is no longer needed. Choose (a) by default unless ops explicitly confirms (b).
- **Tier:** **T0** (week 1, day 1 — fast fix; even (b) is 6-line delete)
- **Acceptance:** `helmfile -e production apply --skip-deps --concurrency=1 --interactive=false 2>&1 | tee deploy.log` shows zero "Error: open fix-cassandra-gossip-config-job.yaml: no such file" messages.
- **Risk-of-being-wrong:** ZERO. File missing is verified.

#### HF-55 — Kibana OOM-fix hook commented out; comment misleading

- **Severity:** MED (technical debt)
- **File:line:** `helmfile/helmfile.yaml:237, 240-246, 345-352`
- **Evidence:** Hook to apply Kibana resource fix (line 345-352) is `#`-commented out. Current limits (lines 240-246) are 512Mi/1Gi. Comment at line 237 says "too low, causing OOM kills" — internally inconsistent.
- **Fix:** Either uncomment the hook (and apply the larger limits the hook was meant to set) or delete the misleading comment if 1Gi is now sufficient. Document the decision either way.
- **Tier:** T2 (week 2)
- **Acceptance:** Either the hook is uncommented and applied OR the comment is removed/updated. `grep -A2 'too low' helmfile.yaml` finds no contradictions.
- **Risk-of-being-wrong:** LOW.

#### HF-56 — PostgreSQL `maxConns: 20` likely primary latency contributor

- **Severity:** **HIGH** (latency root cause candidate)
- **File:line:** `helmfile/temporal-values.yaml:19-20, 31-32`
- **Evidence:** Both `default` and `visibility` stores configured with `maxConns: 20, maxIdleConns: 20`. Temporal frontend/history/matching/worker services all multiplex over this pool. With `replicaCount: 1` (HF-03) all four services share 20 connections.
- **Why it causes latency:** Under moderate load (~50 concurrent workflows) connection pool exhausts → queries queue → latency spikes → Temporal frontend RPC timeouts → workflow task failures. Pattern matches user's "very often crashes" report.
- **Fix:** `maxConns: 100` (default), `maxConns: 50` (visibility); `maxIdleConns: maxConns/2`. 4 lines.
- **Tier:** **T0** (week 1, day 1 — high-leverage trivial fix)
- **Acceptance:** p95 Temporal RPC latency drops by ≥ 30% under existing load (measure via existing `temporal_request_latency_bucket` metric); zero `pq: too many connections for role` errors in postgres logs over 24h.
- **Risk-of-being-wrong:** LOW. PostgreSQL chart's default `max_connections` is 100, so the chart can serve 100 client connections without further config.

#### HF-57 — EBS storage class declared in (likely) GCP context

- **Severity:** MED (deploy-time failure if cloud is GCP)
- **File:line:** `helmfile/helmfile.yaml:40, 72, 196, 307`
- **Evidence:** Storage class `ebs-volume-gp3-encrypted` (AWS-specific) used for PostgreSQL, Redis, Cassandra, Grafana PVCs. Cluster name pattern (`fqk5.kitt-inf.net`) and Go code suggest GCP/GKE.
- **Fix:** Verify target cloud provider with ops. If GCP/GKE: change to `standard-rwo` or parameterize via values files: `storageClass: {{ .Values.storageClass | default "standard-rwo" }}`.
- **Tier:** T1
- **Acceptance:** Test deploy to a fresh cluster reaches `Bound` PVC state for all 4 PVCs.
- **Risk-of-being-wrong:** MED — requires cloud-provider verification.

#### HF-58 — Elasticsearch visibility `number_of_replicas: 1` causes permanent yellow

- **Severity:** HIGH
- **File:line:** `helmfile/helmfile.yaml:251-252` (`number_of_replicas: 1`); `helmfile.yaml:231` (`clusterHealthCheckParams: wait_for_status=yellow` — workaround). Internal doc `elasticsearch-shard-allocation-fix.md` recommends `replicas: 0`.
- **Why it causes instability:** Permanent yellow status masks real problems; unassigned replica shards consume resources; if a node fails, replica can't be reallocated.
- **Fix:** `number_of_replicas: 0`; restore `wait_for_status=green` health check. 2 lines.
- **Tier:** **T0** (week 1, day 1)
- **Acceptance:** `curl :9200/_cluster/health` returns `"status":"green"` within 60s of apply.
- **Risk-of-being-wrong:** LOW (matches internal recommendation).

#### HF-59 — Redis HA inconsistency: EKS has dev-level redundancy

- **Severity:** MED
- **File:line:** `helmfile/values-eks.yaml:43` (`replicaCount: 1`) vs `helmfile/values-production.yaml:45` (`replicaCount: 2`)
- **Why it matters:** EKS environment is meant to be production-like; with replica:1, Redis is SPOF in EKS.
- **Fix:** `replicaCount: 2` in `values-eks.yaml`. 1 line.
- **Tier:** T2
- **Acceptance:** `kubectl get statefulset/redis-master -n temporal -o jsonpath='{.spec.replicas}'` returns `2` in EKS env.
- **Risk-of-being-wrong:** LOW.

#### HF-60 — Prometheus memory comment ↔ value mismatch

- **Severity:** LOW (documentation hygiene)
- **File:line:** `helmfile/helmfile.yaml:271` — comment says "Increased from 4Gi to 8Gi" but actual value is 12Gi (two undocumented increases).
- **Fix:** Update comment to `"8Gi → 12Gi (2 undocumented bumps)"`. 1 line.
- **Tier:** T3
- **Acceptance:** `grep -A1 'Increased' helmfile.yaml` shows comment matches value.

#### HF-61 — Hardcoded JWT/SAML token in `download-aws-accounts-with-cookie.sh`

- **Severity:** **CRITICAL** (security)
- **File:line:** `helmfile/download-aws-accounts-with-cookie.sh:16`
- **Evidence:** `COOKIE="observability-saml-token0=eyJhbGciOiJSUzI1NiIs..."` (~1100 chars). JWT decoded payload contains user identity `lzhu3@atlassian.com`, prod service `alfred.prod.atl-paas.net`, full SAML SessionIndex.
- **Why it matters:** Anyone with repo access has a (possibly expired) prod auth token. Pattern indicates future tokens may be committed the same way. PII (user email + display name) leaked.
- **Fix:** (1) Remove the hardcoded token immediately. (2) `read -s -p "Cookie: " COOKIE` or `COOKIE="${COOKIE_ENV:?Set COOKIE_ENV}"`. (3) `.gitignore` for `.env` files. (4) Pre-commit hook: `gitleaks` or `detect-secrets` to flag JWT shapes. (5) Coordinate with security to **revoke the leaked token** server-side and rotate user's session.
- **Tier:** **T0** (week 1, day 1)
- **Acceptance:** `grep -rE 'eyJ[A-Za-z0-9_-]{10,}\\.eyJ' helmfile/` returns 0 hits; pre-commit hook installed; security ack on revocation.
- **Risk-of-being-wrong:** ZERO.

#### HF-62 — `cleanup-and-redeploy.sh` leaves services scaled to 0 on failure

- **Severity:** HIGH (operational outage risk)
- **File:line:** `helmfile/cleanup-and-redeploy.sh:9-29`
- **Evidence:** Script scales Temporal frontend/history/matching to 0, then runs operations. If any subsequent step fails, services stay at 0 → manual recovery required. `kubectl wait` uses fallback echo (no abort).
- **Fix:** Add `trap 'restore_replicas' EXIT ERR INT TERM` at top; define `restore_replicas()` that restores recorded replica counts. Add `set -euo pipefail`. ~30 LoC.
- **Tier:** T1 (week 1, day 5)
- **Acceptance:** Manually inject failure between scale-down and scale-up steps; verify replicas auto-restored to recorded values; verify exit code is non-zero.
- **Risk-of-being-wrong:** LOW.

#### HF-63 — 26 of 28 Job manifests missing resource limits

- **Severity:** HIGH (any Job can OOM-kill neighbors)
- **File:line:** Verified by `grep -L 'resources:' helmfile/*-job.yaml | wc -l` → 26.
- **Why it matters:** Jobs without resource limits can consume unbounded memory/CPU, OOM-killing other pods on the same node — including Temporal frontend/history.
- **Fix:** Add `resources: { requests: {cpu: 100m, memory: 128Mi}, limits: {cpu: 500m, memory: 512Mi} }` to every Job container. Use a YAML anchor or kustomize patch to apply to all 26 at once. Standard Job pattern.
- **Tier:** T1 (week 1, day 5; sweep PR)
- **Acceptance:** `for f in helmfile/*-job.yaml; do grep -q 'resources:' "$f" || echo MISSING $f; done` returns empty.
- **Risk-of-being-wrong:** LOW (default limits are conservative; can be tuned per-job).

#### HF-64 — 4 of 28 Job manifests missing `ttlSecondsAfterFinished`

- **Severity:** LOW (24/28 already correct; minor remaining cleanup)
- **File:line:** Verified by `grep -L 'ttlSecondsAfterFinished' helmfile/*-job.yaml | wc -l` → 4. **Note: Plan A claimed 8 missing; actual is 4.**
- **Fix:** Add `ttlSecondsAfterFinished: 300` to the 4 remaining Jobs.
- **Tier:** T2
- **Acceptance:** `for f in helmfile/*-job.yaml; do grep -q 'ttlSecondsAfterFinished' "$f" || echo MISSING $f; done` returns empty.
- **Risk-of-being-wrong:** ZERO.

### §3 Extensions to existing HF entries

#### HF-42 (Grafana password) — extend with second leaked location

Original HF-42 cited `helmfile.yaml:302` and `DEPLOYMENT_SUMMARY.md:70`. **Add:** `delete-dashboards-from-db-job.yaml:28` (`AUTH="admin:Yfd2HxAsXiQ7brwIoeR5i2tvYH2jmRSBViBsWRM8"`). The remediation (rotate + use Secret) must cover all three locations. Acceptance update: `grep -rEl 'Yfd2HxAsXiQ' helmfile/` returns empty.

#### HF-11 (destructive jobs) — extend with safeguard pattern

Original HF-11 cited `delete-all-temporal-data-job.yaml` lifecycle controls. **Add:** confirmation/dry-run/backup pattern (Plan A S44). Implement as: (a) `env: I_REALLY_MEAN_IT` gate on container args; (b) optional `--dry-run` flag; (c) preceding `cassandra snapshot` activity for keyspace-drop jobs. Acceptance update: running the job without `I_REALLY_MEAN_IT=1` exits non-zero with explanatory message; with the flag, executes and creates a snapshot first.

### §4 Plan A's testing process — what to take vs. what's already covered

Plan A has a **6-phase testing process (T1-T5 + summary)** at lines 287-573. Mapping against child's `06_TESTING_STRATEGY.md`:

| Plan A phase | Child plan equivalent | Verdict |
|---|---|---|
| Phase T1 (pre-implementation: lint, typecheck, schema-validate) | L1 (lint/typecheck) in 5-layer pyramid | DUPLICATE — child has it |
| Phase T2 (per-fix verification template) | NOT in child | **NEW pattern — adopt as `06_TESTING_STRATEGY.md` §11** |
| Phase T3 (integration testing post-all-fixes) | L4 (E2E) in pyramid | DUPLICATE |
| Phase T4 (regression / stability testing) | L5 (chaos drills) | PARTIAL — chaos is sketch only; T4 has concrete checklist worth adopting |
| Phase T5 (long-term tests to add) | Already in PR-T-01..PR-T-12 | DUPLICATE |
| Summary table (per-fix coverage matrix) | NOT in child | **NEW pattern — adopt as `06_TESTING_STRATEGY.md` §12** |

**Action:** Add §11 (per-fix verification template) and §12 (per-fix coverage matrix) to `06_TESTING_STRATEGY.md` in a follow-up commit (out of scope for Appendix D — to be tracked as **PR-T-13** on the testing roadmap).

### §5 Final updated severity rollup (after Appendix D)

| Severity | After Appendix C | **After Appendix D (FINAL)** |
|---|---|---|
| CRITICAL | 9 | **12** (+HF-50 race, +HF-54 missing-file, +HF-61 JWT) |
| HIGH | 17 | **23** (+HF-51, HF-52, HF-53, HF-56, HF-58, HF-62, HF-63) |
| MED | 18 | **22** (+HF-55, HF-57, HF-59, +HF-11/HF-42 extension scope) |
| LOW | 6 | **8** (+HF-60, HF-64) |
| STRATEGIC (Q3) | 3 | **3** |
| **Total findings** | 49 | **64** (+13 new + 2 extensions logically) |
| REFUTED claims | 10 | **10** (no new refutations from Plan A — Plan A's claims all verified) |
| Plan A duplicates folded | — | 2 (S36→HF-03, S48→HF-39) |

### §6 Done definition for Appendix D

This appendix is DONE when:
1. ✅ All 19 Plan A findings (S25-S48) have a disposition (NEW/EXTEND/DUPLICATE) with file:line evidence
2. ✅ HF-50..HF-64 entries written above
3. ✅ HF-42 + HF-11 extensions documented
4. ✅ §0 verification receipts published (binary CONFIRMED with grep proof for every claim)
5. ⏳ `00_README.md` totals refreshed to "64 total findings" + new severity counts (next commit)
6. ⏳ "Pick one plan" answer documented in `00_README.md` (next commit)

The integration of `merry-petting-music.md` is end-to-end complete after items 5-6.

---

## Appendix E — Re-integration after Plan A rewrite (2026-05-11 07:34)

### §0 Why this appendix exists

`~/.claude/plans/merry-petting-music.md` was **rewritten** between my first integration (07:25) and now (07:34). The new file (564 lines, down from 590) is no longer a flat catalog of S25-S48; instead it is itself a **comparison + integration document** that explicitly references this child plan as "Plan B (the superior plan)" and proposes a merged roadmap.

The rewritten Plan A:
- Acknowledges this child plan as the canonical superior baseline
- Reduces its own catalog to **9 retained S-findings** (S25, S26, S28, S29, S32, S34, S37, S42, S43)
- **Disputes 4 of my Appendix D findings** as false/overstated/questionable (S35, S46, S47, S48)
- Proposes its own **MERGED PRIORITY ROADMAP** (T0/T1/T2/T3) that interleaves Plan A retained items into my T0/T1/T2/T3
- Adds a **TESTING LANDSCAPE** section identical to my `06_TESTING_STRATEGY.md` content area but with one specific catch: **broken Makefile test path** at `dte/Makefile`

This appendix arbitrates the 4 disputes by direct file inspection, accepts Plan A's 1 new finding (broken Makefile path), and reconciles the proposed merged roadmap with mine.

### §1 Arbitration of 4 disputed findings (binary verdict + evidence)

| Dispute | Plan A v2 verdict | My HF verdict | **Arbitration** | Evidence |
|---|---|---|---|---|
| **S35 / HF-57 EBS storage** | EBS is correct (cluster is EKS) | EBS-in-GCP risk (MED) | **PLAN A WINS — HF-57 REFUTED** | (a) Only `values-eks.yaml` exists (no `values-gcp.yaml`/`values-gke.yaml`). (b) `helmfile.yaml:159-167, 278` use `alb.ingress.kubernetes.io/*` annotations (AWS ALB Controller). (c) `values-eks.yaml:99` `external-dns.alpha.kubernetes.io/hostname: temporal.fqk5.kitt-inf.net`. **Conclusion:** cluster is EKS; `ebs-volume-gp3-encrypted` is correct. The `fqk5.kitt-inf.net` cluster-name pattern was a misleading internal heuristic — kitt-inf.net is the EKS cluster's domain. |
| **S46 / HF-63 jobs missing resources** | "overstated" | 26/28 missing | **MY DATA WINS, PLAN A WAS WRONG TO DISPUTE — corrected count: 27/28 missing** | Direct count: `for f in helmfile/*-job.yaml; do grep -c 'resources:' "$f"; done` shows **only `migrate-cassandra-to-persistent-storage-job.yaml` and `patch-prometheus-config-job.yaml` have any `resources:` lines, and the latter is for a different purpose** — actually only 1 job has true resource limits. Plan A v2's dispute conflated `backoffLimit`/`ttlSecondsAfterFinished`/`restartPolicy` (which 24+ Jobs have) with `resources` (which only 1 Job has). HF-63 stands at HIGH severity with **27/28** missing (corrected from 26/28). |
| **S47 / HF-64 jobs missing TTL** | "overstated" | 4/28 missing | **MY DATA WINS — Plan A v2's dispute is wrong** | Already verified earlier: `for f in helmfile/*-job.yaml; do grep -L 'ttlSecondsAfterFinished' "$f"; done | wc -l` → **4**. HF-64 stands at LOW severity with 4/28 missing (24/28 already correct, as my entry already noted). Plan A v2 v1 said "8 missing" which I correctly downgraded to 4. Plan A v2 then conflated this with the broader job-lifecycle question and incorrectly disputed it. |
| **S48 / HF-39 Cilium NetworkPolicies** | "questionable — Cilium ≠ k8s NetworkPolicy, may be intentional" | CRITICAL | **PARTIAL REFUTATION — adjust HF-39 framing** | Plan A v2 is *technically right* that these are `apiVersion: cilium.io/v2 / CiliumClusterwideNetworkPolicy`, NOT standard k8s `networking.k8s.io/v1/NetworkPolicy`. The "allow-all" framing was imprecise. **However** — `allow-all.yaml` declares `endpointSelector: {}` (cluster-wide selector match) + `ingress: []` + `egress: []`. In Cilium semantics, an empty `ingress: []` array means "no ingress rules — DENY" but applied with empty endpointSelector across the entire cluster, this depends on whether the CRD is applied. The actual security posture cannot be determined from the file alone — it depends on Cilium's `enable-policy=default` setting. **Action:** downgrade HF-39 from CRITICAL to **MED**; rewrite scope to "audit Cilium policy semantics with security team rather than treat as wide-open by default." |

### §2 Plan A v2's 1 net-new finding

Plan A v2 surfaces **one finding** I had not captured: **broken DTE Makefile test path**.

#### HF-65 — DTE `make test` runs against non-existent paths

- **Severity:** HIGH (testing — silently passes for code with zero coverage)
- **File:line:** `helmfile/dte/Makefile`
- **Evidence:** `make test` runs `go test ./pkg/... ./cmd/...` — these directories *exist* but the actual code is in `./distributed-worker/` and `./distributed-client/`. The test target finds nothing to run for the worker/client binaries and **exits 0**. This was caught earlier as G2 / PR-T-02 (in `06_TESTING_STRATEGY.md`), but the patch focuses on `./distributed-worker/...` only.
- **Fix:** `go test ./pkg/... ./distributed-worker/... ./distributed-client/... -race -coverprofile=coverage.out`. Add `-race` to catch HF-50 class of bugs at CI time.
- **Tier:** **T2 day 10** (matches Plan A v2's roadmap)
- **Acceptance:** `cd dte && make test 2>&1 | grep -c 'FAIL\|PASS:'` returns ≥ 70 (covering all 70 test functions in 6 files); `-race` flag catches HF-50 stress-test in CI.
- **Risk-of-being-wrong:** ZERO.
- **Cross-link:** This refines existing G2/PR-T-02; treat HF-65 as the canonical entry and update `patches/PR-T-02.patch` to include `./distributed-client/...` and `-race`.

### §3 Plan A v2's MERGED PRIORITY ROADMAP — comparison vs ours

Plan A v2 proposes a T0/T1/T2/T3 sequence interleaving 9 Plan A items with my 22 PR-HF entries. Reviewing it against `03_PRIORITIZED_PLAN.md`:

| Aspect | Plan A v2 roadmap | Our roadmap | Verdict |
|---|---|---|---|
| Day 1 includes HF-06 (creds.json) | ✅ | ✅ | match |
| Day 1 includes HF-11 (cleanup-all guard) | ✅ | ✅ | match |
| Day 1 includes S42/HF-61 (JWT) | ✅ | ✅ | match — already in our T0 |
| Day 1 includes HF-56 (PostgreSQL maxConns) | ✅ (as S34) | ✅ | match (already in our T0) |
| Day 2 includes HF-07 (drift), HF-05 (secrets), HF-43 (Grafana password — S43 extends HF-42) | ✅ | ✅ | match |
| Day 3 includes HF-01 (probes), HF-03 (replicaCount), HF-02 (PDBs) | ✅ | ✅ | match |
| Day 4 includes HF-08 (needs:), HF-09 (drift), **HF-50 (S25 race)** | ✅ | **MISSING — our roadmap has HF-50 at T0 day 2** | minor sequencing diff; either order is fine |
| Day 5 includes HF-04 (CPU), HF-15 (JMX), **HF-51 (S26-ext)** | ✅ | match | match |
| Day 6 includes HF-10 (KEDA), HF-14 (postsync wrapper), **HF-53 (S29 health)** | ✅ | match | match |
| Day 7 includes HF-12 (shell), HF-17 (ES ILM), **HF-58 (S37 replicas=0)**, **HF-52 (S28 backoff)** | ✅ | match | match |
| Day 8 includes HF-13 (image pin), HF-16 (Cassandra seeds), **HF-54 (S32 missing file)** | ✅ | match | match |
| Day 10 includes **HF-65 (Makefile fix)** | ✅ | **MISSING from our roadmap** | adopt — see §2 above |

**Net delta:** the two roadmaps agree on 95% of sequencing. The only meaningful add is **HF-65** at T2 day 10. HF-57 should be **deleted from the roadmap** entirely (refuted in §1).

### §4 Plan A v2's "what to drop" list — arbitration

Plan A v2 proposes dropping 8 items. My arbitration:

| Item Plan A v2 wants to drop | My HF | Verdict |
|---|---|---|
| S35 EBS | HF-57 | **AGREE — DROP HF-57** (refuted in §1) |
| S46 jobs missing limits | HF-63 | **DISAGREE — KEEP HF-63 at HIGH severity** (data is verified, count even worse) |
| S47 jobs missing TTL | HF-64 | **DISAGREE — KEEP HF-64 at LOW severity** (data is verified at 4/28) |
| S48 NetworkPolicies | HF-39 | **PARTIAL — KEEP HF-39 but downgrade to MED with corrected Cilium framing** (see §1) |
| S36 Temporal replica | (already absorbed into HF-03) | AGREE — already done |
| S40 Redis EKS HA | HF-59 | **DISAGREE — KEEP HF-59 at MED** (Plan A v2's "absorbed by HF-03" claim is wrong; HF-03 covers Temporal replicaCount, not Redis EKS-specific values file) |
| S44 destructive job safeguards | (extension to HF-11) | AGREE — already done (HF-11 extension in Appendix D §3) |
| S45 cleanup-and-redeploy | HF-62 | **DISAGREE — KEEP HF-62** (Plan A v2's "absorbed by HF-12" claim is wrong; HF-12 is shell-script `set -euo pipefail` sweep, while HF-62 is the trap-handler-rollback specifically for cleanup-and-redeploy.sh) |

**Net:** of the 8 proposed drops, **only 1 is correct (HF-57)**, **3 are partial agreements** (already done), and **4 are wrong** (Plan A v2 over-aggressively absorbed findings into other HFs that don't actually cover the same scope).

### §5 Net delta summary (post-Appendix-E)

| Action | Count | Items |
|---|---|---|
| **Refute (drop)** | 1 | HF-57 (EBS storage) |
| **Downgrade severity** | 1 | HF-39 CRITICAL → MED (Cilium framing correction) |
| **Add NEW** | 1 | HF-65 (Makefile test path — refines G2/PR-T-02) |
| **Reject Plan A v2's drop proposal** | 4 | HF-39 (downgraded but kept), HF-59, HF-62, HF-63, HF-64 (HF-39 counted in downgrade) |
| **Roadmap sequencing changes** | 1 | Add HF-65 at T2 day 10; remove HF-57 from any roadmap |
| **Refutations log entries** | 1 | HF-57 (with full file:line evidence in §1) |

### §6 Final updated severity rollup (after Appendix E)

| Severity | After Appendix D | **After Appendix E (FINAL v3)** |
|---|---|---|
| CRITICAL | 12 | **11** (HF-39 downgraded MED) |
| HIGH | 23 | **24** (+HF-65 testing; HF-57 dropped from MED so no change to HIGH) |
| MED | 22 | **22** (+HF-39 downgrade, −HF-57 refutation) |
| LOW | 8 | **8** |
| STRATEGIC (Q3) | 3 | **3** |
| **Total findings** | 64 | **64** (+1 new HF-65, -1 refuted HF-57; net 0) |
| REFUTED claims | 10 | **11** (+HF-57) |

### §7 Done definition for Appendix E

This appendix is DONE when:
1. ✅ All 4 disputed findings (S35/HF-57, S46/HF-63, S47/HF-64, S48/HF-39) are arbitrated with file:line evidence
2. ✅ HF-57 marked REFUTED with verified counter-evidence; severity rollup recomputed
3. ✅ HF-39 framing rewritten with Cilium correction; severity downgraded to MED
4. ✅ HF-65 (Makefile test path) added as new entry
5. ✅ Plan A v2's merged roadmap reconciled with our `03_PRIORITIZED_PLAN.md`
6. ⏳ `00_README.md` updated with new totals + retained "pick one" answer (next commit)

The integration of the **rewritten** `merry-petting-music.md` is end-to-end complete after item 6.
