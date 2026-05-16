# Prioritized Plan (T0 → T3)

> Each item lists: **scope**, **target metric movement** (axis), **dependencies**, **owner-hint**, **time-box**.
> All items reference findings in `02_FINDINGS_CATALOG.md` and PRs in `04_PR_BREAKDOWN.md`.
> All file paths are relative to `atlassian_packages/gcp_kitt/helmfile/`.

---

## Tiering rubric (recap)

| Tier | When to ship | Severity criterion | LoC bound per PR |
|---|---|---|---|
| **T0** | Week 1, days 1–3 | CRITICAL + low blast radius | < 200 LoC |
| **T1** | Week 1, days 4–7 | HIGH OR CRITICAL needing canary | < 500 LoC |
| **T2** | Week 2 | MED | < 300 LoC |
| **T3** | Opportunistic | MED defence-in-depth | any |

---

## T0 — STOP THE BLEEDING (Week 1, days 1–3)

> **Rule**: ship in this order. Each PR can be reviewed independently but the order minimises blast-radius windows.

| Day | PR | Title | Why first | Axis moved | Time-box |
|---|---|---|---|---|---|
| 1 | `PR-HF-06` | Remove `python-app/creds.json` + revoke GCP impersonation | **Highest blast-radius security item** | Security | 1 hr code + revocation |
| 1 | `PR-HF-11` | `cleanup-all.sh` env-guard + kube-context check | Prevents accidents during rest of plan | Operability | 30 min |
| 2 | `PR-HF-07` | Delete or rename `temporal-values.yaml` (drift removal) | Removes the catastrophic-misapply trap **before** anyone needs to debug T0 work | Reliability | 30 min |
| 2 | `PR-HF-05` | Move plaintext secrets to `existingSecret:` references | Pre-requisite for repo-widening / open-sourcing parts | Security | 4 hr (bootstrap docs + diff) |
| 3 | `PR-HF-01` | Add startup/readiness/liveness probes to Temporal frontend/history/matching/worker | **Unblocks measurement** of every later fix; current probe-noise drowns signal | Reliability + Latency | 2 hr |
| 3 | `PR-HF-03` | Bump `replicaCount` 1 → 2 for Temporal frontend/history/matching/worker, web, Redis-replica | Removes the SPOF that PDB depends on | Reliability | 1 hr (values change) + canary |
| 3 | `PR-HF-02` | Add PDBs (`temporal-pdbs.yaml`) for the 5 critical workloads | Locks in the safety the replica bump enabled | Reliability | 1 hr |

**Acceptance for T0 (apply at end of day 3):**
- `kubectl get pdb -n temporal | wc -l` ≥ 5
- `kubectl get deploy,sts -n temporal -o json | jq '.items[].spec.replicas' | sort -u` shows no `1` for Temporal sub-roles
- `kubectl describe pod -n temporal -l app.kubernetes.io/component=frontend | grep -c 'Liveness\|Readiness\|Startup'` ≥ 3
- `grep -E 'password.*:.*"[A-Za-z0-9]{6,}"' helmfile/*.yaml` returns 0
- `git ls-files helmfile/python-app/creds.json` returns 0
- `bash helmfile/cleanup-all.sh` exits with code 2

---

## T1 — REMOVE RECURRENCE (Week 1, days 4–7)

| Day | PR | Title | Depends-on | Axis | Time-box |
|---|---|---|---|---|---|
| 4 | `PR-HF-08` | Add `needs:` declarations to root `helmfile.yaml` | T0 PRs landed | Reliability + Operability | 1 hr |
| 4 | `PR-HF-09` | Eliminate `dte/distributed-worker/cluster_db.go` drift (use `pkg/cluster`) | none | Reliability + Operability | 2 hr (Go change + tests) |
| 5 | `PR-HF-04` | Remove (or 4×-bump) CPU `limits` for Temporal + Cassandra | `PR-HF-01` (probes must work first to detect any regression) | Latency | 2 hr |
| 5 | `PR-HF-15` | Cassandra JMX NetworkPolicy + `consistent.rangemovement` comment | none | Security + Reliability | 3 hr (NetworkPolicy + canary) |
| 6 | `PR-HF-10` | KEDA Temporal scaler diagnostic runbook + ScaledObject fix | none | Latency + Operability | 4 hr (live debugging) |
| 6 | `PR-HF-14` | `apply-and-verify.sh` wrapper for postsync hooks | none | Operability | 3 hr |
| 7 | `PR-HF-12` | Mass `set -euo pipefail` sweep for 17 shell scripts | `PR-HF-11` (cleanup-all guarded) | Operability | 4 hr (audit + smoke tests) |
| 7 | `PR-HF-17` | Restore `wait_for_status=green` + add ES ILM policy | none | Reliability + Latency | 4 hr + 24 h soak |

**Acceptance for T1 (end of week 1):**
- `helmfile --debug template helmfile.yaml | grep -c 'needs:'` ≥ 4
- `diff -u dte/distributed-worker/cluster_db.go dte/pkg/cluster/cluster_db.go | wc -l` < 30
- `kubectl get hpa -n dtaske keda-hpa-scraper-worker-scaler -o jsonpath='{.status.conditions[?(@.type=="ScalingActive")].status}'` returns `True`
- For each of the 17 scripts, `head -3 <script> | grep -q 'set -euo pipefail'` passes
- `curl -s "$ES_URL/_cluster/health" | jq -r .status` returns `green` within 60 s of cluster bring-up
- 24-hour Prometheus check: `rate(kube_pod_container_status_restarts_total{namespace="temporal"}[1h])` ≤ 0.01

---

## T2 — HARDEN (Week 2)

| Day | PR | Title | Axis | Time-box |
|---|---|---|---|---|
| 8 | `PR-HF-13` | Pin `bitnami/kubectl:1.32.0` across all `*-job.yaml` | Operability | 1 hr |
| 8 | `PR-HF-16` | Cassandra seed-count cap (≤ 3) | Reliability | 2 hr + canary |
| 9 | `PR-HF-18` | Bump default-namespace retention 72h → 168h; add short-lived NS @ 72h | Latency | 2 hr |
| 9 | `PR-HF-21` | Set Cassandra `gc_grace_seconds=259200` for temporal keyspace (idempotent Job) | Latency | 2 hr + 24 h soak |
| 10 | `PR-HF-19` | Migrate Grafana dashboards to per-CM sidecar discovery + CI size check | Operability | 3 hr |

**Acceptance for T2:**
- `grep -n 'image:.*:latest' helmfile/*-job.yaml` returns 0
- `kubectl exec -n temporal cassandra-0 -- nodetool gossipinfo | grep -c seed` ≤ 3
- `tctl --ns default namespace describe | grep Retention` shows `168h0m0s`
- `cqlsh -e "DESCRIBE TABLE temporal.executions" | grep gc_grace_seconds` shows `259200`
- `find helmfile -name '*-grafana-dashboard.yaml' -exec wc -c {} + | awk '$1 > 800000 { exit 1 }'` exits 0
- New CI rule: same script enforced on every PR

---

## T3 — POLISH (opportunistic)

| PR | Title | Axis | Trigger |
|---|---|---|---|
| `PR-HF-20` | Delete commented-out cassandra-exporter-sidecar block + add `cassandra-metrics-exporter-summary.md` | Operability | When touching `helmfile.yaml` for any other reason |
| `PR-HF-22` | Add Prom alert `cassandra_thread_pools_native_transport_active / max > 0.8 for 5m`; document `connectionsPerHost: 4` plan | Reliability | When metrics-exporter scrape lands |

---

## Sequencing rationale (why this order)

1. **HF-06 first.** A leaked credential in a public-eligible repo is the highest-blast-radius item; everything else can wait an hour.
2. **HF-11 day 1.** During T0/T1 churn, ops will run cleanup scripts; the env-guard prevents a catastrophic mis-fire while everything is in motion.
3. **HF-07 before HF-05.** Removing the drift file *before* migrating secrets means we don't accidentally edit two copies of the secret block.
4. **HF-01 before HF-03/HF-02.** Probes must exist before we can prove the new replica's health; without them, doubling replicas just doubles the noise.
5. **HF-03 before HF-02.** PDBs need ≥2 replicas to mean anything; setting `minAvailable: 1` on a 1-replica deployment deadlocks `kubectl drain`.
6. **HF-08 before HF-04.** The race in HF-08 currently masks any latency regression that HF-04 might cause; fix race first.
7. **HF-15 before HF-04.** Cassandra JMX hardening should happen before we remove CPU limits — limits removal could let Cassandra burst-saturate and we want JMX to stay accessible to the metrics-exporter.
8. **HF-12 last in T1.** Adds `set -u` which can reveal latent unbound-var bugs in the scripts we just changed (HF-11 etc); doing it last lets us run those scripts manually first.
9. **HF-21 only after HF-18.** `gc_grace_seconds` change must be aligned with the new retention; both together or it's worse than either alone.

---

## What this plan does NOT cover (parking lot)

These were spotted during the investigation but are out of scope for the stability mandate. Recommend separate tickets:

| Item | Reason out of scope | Suggested ticket type |
|---|---|---|
| Migrate `temporal-postgresql` to AWS RDS managed | Multi-week migration; needs DR plan | Epic |
| Adopt service mesh (mTLS for KEDA↔Temporal) | Architecture decision; out of helmfile scope | RFC |
| Replace `bitnami/cassandra` with Scylla | Multi-week; data migration | Epic |
| Switch `helmfile apply` → ArgoCD `app-of-apps` | Fundamental deploy-tool swap | RFC |
| Knative serving config drift in `KNATIVE_README.md` | Different subsystem | Separate plan |
| `aws-accounts.json` (76 MB in repo) | Bloat fix, not stability | Cleanup ticket |
| Dockerfile USER root + tini for `Dockerfile.distributed-worker` | Container hygiene; LOW severity | Cleanup ticket |

---

## Risk-managed rollouts

- **HF-04 (CPU limits removal)** and **HF-15 (Cassandra JMX)**: require a **canary cluster** for ≥ 4 h before prod. Document in PR description.
- **HF-17 (ES wait_for_status=green)**: requires understanding the underlying allocation issue first; if shards are stuck, going to green will block all readiness. Prereq: `bash fix-unassigned-shards.sh` completes successfully on the target cluster.
- **HF-21 (Cassandra `gc_grace_seconds`)**: Document in PR that the change is **forward-only** — once tombstones are GC'd, repairs of nodes that were down for >3 d will resurrect deleted data. Operational prereq: nodes must not be allowed to stay down >3 d before this PR ships.

---

## "Done" definition for the whole plan

The helmfile_enhancement_plan is **DONE** when:

1. All T0 + T1 PRs are merged.
2. All acceptance commands listed in `00_README.md` §"Acceptance" return their target values.
3. 7-day Prometheus query `max_over_time(rate(kube_pod_container_status_restarts_total{namespace="temporal"}[1h])[7d:1h])` ≤ 0.05 (peak hourly restart-rate over a week).
4. Single page on-call runbook updated to reference: `KEDA_TEMPORAL_CONNECTION_ISSUE.md` (HF-10), `cleanup-all.sh` env-guard (HF-11), `apply-and-verify.sh` (HF-14).
5. T2 + T3 backlog tracked but no longer blocking.
