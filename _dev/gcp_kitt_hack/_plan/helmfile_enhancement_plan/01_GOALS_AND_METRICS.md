# Goals & Metrics — what every helmfile fix must move

## 1. Driver goal (alignment with the parent plan)

The parent plan family (`../00_README.md`) drives gcp_kitt towards supporting **Proactive AI Platform's 400K → 1.5M monthly invocations**. Within that context, **the helmfile package is the cluster-control plane** (Temporal, Cassandra, Elasticsearch, KEDA, ops jobs/scripts). Its job is **not to be a bottleneck or an outage source.** Concretely, every helmfile fix must move at least one of:

1. **Reliability** — pod-restart rate, MTTR, blast-radius of single-pod failure.
2. **Latency** — workflow start-to-execute p95, Temporal frontend RPC p95, gossip recovery time after partition.
3. **Security** — credentials at rest, JMX exposure, RBAC blast radius.
4. **Operability** — drift, deploy idempotency, on-call accident-prevention (env-guards), observability of partial-failures.

---

## 2. The four-axis dashboard (what we measure)

Every PR in `04_PR_BREAKDOWN.md` lists which of these axes it moves and by how much.

### 2.1 Reliability axis

| Metric | Source | Target after T0+T1 |
|---|---|---|
| `rate(kube_pod_container_status_restarts_total{namespace="temporal"}[1h])` | kube-state-metrics | ≤ 0.01 sustained for 24 h |
| `kube_poddisruptionbudget_status_current_healthy{namespace="temporal"}` | kube-state-metrics | = `desired` for every PDB |
| `temporal_persistence_errors_per_request` | Temporal SDK | < 0.001 |
| Time-to-first-readiness after `helmfile apply` against an empty cluster | manual stopwatch | ≤ 8 min (was: indefinite during Cassandra slow-start) |

### 2.2 Latency axis

| Metric | Source | Target after T1 |
|---|---|---|
| `histogram_quantile(0.95, sum(rate(temporal_request_latency_bucket[5m])) by (le, operation))` | Temporal Prom export | p95 ≤ 200 ms for `StartWorkflowExecution` |
| `cassandra_read_latency_p99{keyspace="temporal"}` | Cassandra JMX exporter | p99 ≤ 50 ms |
| Workflow start-to-execute (synthetic probe) | `temporal-helloworld` | ≤ 1 s end-to-end |

### 2.3 Security axis

| Metric | Source | Target after T0 |
|---|---|---|
| `grep -E 'password.*:.*"[A-Za-z0-9]{6,}"' helmfile/*.yaml` count | grep | = 0 |
| `git ls-files helmfile/python-app/creds.json` count | git | = 0 |
| Cassandra JMX accessible from non-metrics-exporter pod | NetworkPolicy + manual `nc` test | refused |
| Number of `:latest` image tags in helmfile/*-job.yaml | grep | = 0 |

### 2.4 Operability axis

| Metric | Source | Target after T1+T2 |
|---|---|---|
| Number of helmfile releases without `needs:` | grep `needs:` in `helmfile.yaml` | = 0 (every release explicitly declares deps) |
| Number of shell scripts without `set -euo pipefail` | head -3 of every `*.sh` | = 0 |
| Postsync hook chain that swallows admission-deferred errors | introduce a deliberately-bad manifest as canary | hook returns non-zero |
| `cleanup-all.sh` invoked without env-guard | bash exit code | exits 2 (not 0) |

---

## 3. Anti-goals (things we explicitly will NOT optimise for in this plan)

To keep the scope crisp:

- **We will NOT** introduce a service mesh (Istio/Linkerd). Any latency/observability fix that requires one is parked.
- **We will NOT** migrate Cassandra to a managed service (ScyllaCloud, MCS). Fixes assume the bitnami/temporal-bundled Cassandra StatefulSet stays.
- **We will NOT** rewrite shell scripts in Python/Go. Adding `set -euo pipefail` and env-guards is the bar.
- **We will NOT** introduce ArgoCD app-of-apps. This plan stays compatible with `helmfile apply`.
- **We will NOT** address Knative-specific issues (`KNATIVE_README.md`, `deploy-knative.sh`). They're out-of-scope for the stability goal; covered separately if needed.

---

## 4. Falsifiability checklist (every PR must pass)

For each PR-HF-NN in `04_PR_BREAKDOWN.md`:

1. **Has a binary acceptance test** (a single command whose exit code or stdout determines pass/fail).
2. **Has a single-command rollback** (`git revert <sha>`, `kubectl rollout undo`, `helm rollback`).
3. **Quotes a file:line** as evidence the problem exists *today*.
4. **Names which axis** above it moves and by how much.
5. **Names a potential regression** and how it would be detected (a Prom alert, a synthetic probe, a CI check).

If a PR can't satisfy all 5, it goes back to the catalog as "research" and is *not* in the work plan.

---

## 5. How this plan composes with `08_INTEGRATED_PLAN.md`

The parent plan's H-SERIES (lines 198–442 of `../08_INTEGRATED_PLAN.md`) named 22 helmfile findings but kept them at *strategic* granularity. **This plan is the tactical decomposition.** Every HF-NN here maps 1:1 to an H-series item there. The mapping table is in `02_FINDINGS_CATALOG.md` §6.

**Decision rule:** When the two files conflict, *this plan wins* — it has the file:line evidence and the verified diff. The H-series in `08_INTEGRATED_PLAN.md` should be considered the *summary* once this plan ships.
