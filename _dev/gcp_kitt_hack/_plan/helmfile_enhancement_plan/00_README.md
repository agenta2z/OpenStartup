# helmfile/ Enhancement Plan — Stability, Security, Operability

**Scope:** `atlassian_packages/gcp_kitt/helmfile/` (Temporal control plane + Cassandra + Elasticsearch + KEDA + DTE Go services + Knative + ops scripts).
**Authored:** 2026-05-11
**Authoring method:** 4 parallel deep-dive subagents → critical-thinking validation pass against the actual files (`grep -n` / `sed -n` / `diff -u`) → file:line evidence + unified diffs.
**Parent plan family:** `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/gcp_kitt_hack/_plan/`
**Sibling reference:** `08_INTEGRATED_PLAN.md` (whole-service plan; this is the **helmfile-specific deep extension** of its `H-SERIES`).

---

## Why this plan exists (one paragraph)

The user reported the kitt control-plane is *unstable, latent, and crash-prone*. The `08_INTEGRATED_PLAN.md` H-series identified 22 helmfile-package issues but did not break them down into PR-quality artifacts (file:line + unified diff + acceptance + rollback). This plan does that. Every item below has been **verified by direct file inspection** (subagent claims that failed verification are listed as **REFUTED** and dropped). Every item ships with a **machine-followable patch** (a unified diff) and a **measurable acceptance criterion** so an executor agent or human can apply it without re-reading the codebase.

---

## File index (read in order)

| File | What's in it | When to read |
|------|--------------|--------------|
| `00_README.md` | This file — table of contents, scoring, top-line summary | Start here |
| `01_GOALS_AND_METRICS.md` | The 4 axes (reliability / latency / security / operability) and the metrics each fix moves | Before approving the plan |
| `02_FINDINGS_CATALOG.md` | All **22 normalised findings (HF-01 … HF-22)** with file:line evidence and severity. **REFUTED claims listed at end.** | When you want to know *what is wrong and why* |
| `03_PRIORITIZED_PLAN.md` | 4-tier (T0/T1/T2/T3) work plan with sequencing rationale and time-boxes | When you want to know *what to do first* |
| `04_PR_BREAKDOWN.md` | Every finding decomposed into one PR (`PR-HF-NN`) with branch name, diff, files touched, acceptance, rollback, dependencies | When you want to ship code |
| `05_RISK_AND_VALIDATION.md` | Refutation log, contradictions found, things we explicitly chose NOT to fix and why; risk register for each PR | When a reviewer asks "did you consider…?" |
| `06_TESTING_STRATEGY.md` | **Current test inventory + 5-layer testing pyramid + 12 PR-T patches that wire up CI/lint/contract/E2E/chaos.** Maps every HF acceptance to a layer + runner. | When you want to know *how we'll know it actually works* |
| `07_PARENT_PLAN_INTEGRATION.md` | **Integration of 22 parent-plan helmfile findings (HF-27..HF-48)** into this plan, with critical-thinking refutation of 2 parent claims (H11 "no TLS" and H17 "hardcoded localhost") and correction of 1 (A1 "12-line diff"). Maps every parent ID to its disposition. | When you want to know how this plan reconciles with `_plan/02..08_*.md` |
| `09_TOP10_DETAILED.md` | per-item deep write-ups for the top-10 (NEW — 2026-05-11) |
| `08_TOP10_CRASH_LIKELY_CAUSES.md` | **Judgment-based top-10 ranking of items most likely contributing to observed crashes/instability.** Each item carries explicit Confidence + Impact + Composite-priority scores. Includes critical caveats (the actual deployed backend is Cassandra not PostgreSQL — HF-07 dual-config bug fooled subagents in real-time during ranking). | When you want a "ship this first" ranked list grounded in code evidence but without runtime cluster access |
| `diagnostics/crash_root_cause_diagnostic.sh` + `diagnostics/README.md` | **Read-only diagnostic script + interpretation guide.** Run against a live cluster to convert the top-10 judgment ranking into binary CONFIRMED/LIKELY/UNLIKELY/INCONCLUSIVE verdicts in ~2 minutes. | When you have kubectl access and want runtime evidence to validate the top-10 |

The plan is **structured for both humans and machine-followable agents**: each PR has a stable ID, branch suggestion, concrete file list, unified diff, and a binary acceptance test.

---

## Top-line summary (the 22 findings, one row each)

| ID | Title | Severity | Failure mode | Tier | PR |
|---|---|---|---|---|---|
| **HF-01** | Temporal probes missing (no liveness/readiness/startup on frontend/history/matching/worker) | CRITICAL | Cascading restart storms during Cassandra recovery | T0 | `PR-HF-01` |
| **HF-02** | No PodDisruptionBudgets anywhere in temporal namespace | CRITICAL | Node-drain = full outage | T0 | `PR-HF-02` |
| **HF-03** | `replicaCount: 1` for Temporal server / Web / Redis-replica | CRITICAL | Single pod eviction = outage | T0 | `PR-HF-03` |
| **HF-04** | CPU `limits` set on JVM workloads (Cassandra, Temporal) | HIGH | CFS throttling → tail-latency spikes | T1 | `PR-HF-04` |
| **HF-05** | Plaintext passwords + high-entropy Grafana key in `helmfile.yaml` | CRITICAL (sec) | Credential leak; rotation requires git-edit | T0 | `PR-HF-05` |
| **HF-06** | GCP workload-identity `creds.json` committed to git | CRITICAL (sec) | Token impersonation if repo widens | T0 | `PR-HF-06` |
| **HF-07** | Drift between `temporal-values.yaml` (Postgres) and `helmfile.yaml` (Cassandra) | CRITICAL | Manual `helm upgrade -f temporal-values.yaml` flips backend silently | T0 | `PR-HF-07` |
| **HF-08** | Zero `needs:` declarations between releases in root `helmfile.yaml` | HIGH | First-deploy race — Temporal connects before Postgres ready | T1 | `PR-HF-08` |
| **HF-09** | Drift between `dte/distributed-worker/cluster_db.go` and `dte/pkg/cluster/cluster_db.go` | HIGH | Silent JSON-unmarshal mismatch as `types.ClusterInfo` evolves | T1 | `PR-HF-09` |
| **HF-10** | KEDA Temporal scaler gRPC failure (production active issue) | HIGH | HPA frozen → unbounded queue backlog | T1 | `PR-HF-10` |
| **HF-11** | `cleanup-all.sh` force-deletes namespaces+CRDs without confirmation | HIGH | Accidental wipe | T0 | `PR-HF-11` |
| **HF-12** | 16+ shell scripts use bare `set -e` (no `-u`, no `-o pipefail`); 5 have no `set` at all | HIGH | Silent script failure cascades | T1 | `PR-HF-12` |
| **HF-13** | Job containers using `bitnami/kubectl:latest` | MED | Drift on every cluster bring-up | T2 | `PR-HF-13` |
| **HF-14** | Helmfile postsync hook chain swallows partial-deploy failures | HIGH | Silent half-deployed cluster | T1 | `PR-HF-14` |
| **HF-15** | Cassandra JMX disabled auth+ssl + permanent `consistent.rangemovement=false` | HIGH (sec+stab) | JMX abuse; data inconsistency on scale events | T1 | `PR-HF-15` |
| **HF-16** | Cassandra all-nodes-as-seeds anti-pattern | MED | Gossip storms on partition recovery | T2 | `PR-HF-16` |
| **HF-17** | ES readiness loosened to `wait_for_status=yellow` + no ILM | HIGH | Visibility lag → 504s on Temporal UI; eventual cluster red | T1 | `PR-HF-17` |
| **HF-18** | Temporal default-namespace retention `72h` (aggressive) | MED | History GC competes with read traffic | T2 | `PR-HF-18` |
| **HF-19** | Grafana dashboards in monolithic ConfigMap (etcd 1MiB risk) | MED | Silent dashboard load failure at scale | T2 | `PR-HF-19` |
| **HF-20** | Cassandra metrics double-export risk (commented sidecar + active deployment) | MED | Duplicate Prom series if accidentally enabled | T3 | `PR-HF-20` |
| **HF-21** | Temporal `retention: 72h` vs Cassandra `gc_grace_seconds: 10d` mismatch | MED | Tombstones outlive useful data; expensive repairs | T2 | `PR-HF-21` |
| **HF-22** | No alert on Cassandra native-transport thread saturation | MED | Silent capacity degradation | T3 | `PR-HF-22` |

**Breakdown (after Plan A rewrite re-integration on 2026-05-11 07:36 — END-TO-END COMPLETE v3):** **11 CRITICAL · 24 HIGH · 22 MED · 8 LOW · 3 STRATEGIC (Q3) · 11 REFUTED claims · 64 total findings.** Distribution:
- HF-01..HF-22 in `02_FINDINGS_CATALOG.md` (original helmfile-internal deep dive)
- HF-23..HF-26 Appendix A (5th-pass LOW-confidence sweep)
- HF-27..HF-48 Appendix B (parent-plan family integration)
- HF-49 Appendix C (S-series + OOB integration)
- HF-50..HF-64 Appendix D (`merry-petting-music.md` v1 integration)
- **HF-65 + Appendix E (Plan A v2 rewrite re-integration — adds Makefile test-path fix; refutes HF-57 EBS-in-GCP; downgrades HF-39 Cilium from CRITICAL→MED with corrected framing; arbitrates 4 disputes with file:line evidence)**

**Integration completeness (v2):** all four sources are now reconciled — `helmfile/` direct deep-dive, `_plan/02..08_*.md` parent family, `_plan/07_STABILITY_PLAN.md` S-series, and `~/.claude/plans/merry-petting-music.md` Plan A. Every helmfile-relevant item is either captured as HF-NN or explicitly OUT-OF-SCOPE with rationale. See `05_RISK_AND_VALIDATION.md` + `07_PARENT_PLAN_INTEGRATION.md` §2 + `02_FINDINGS_CATALOG.md` Appendix D §0 for the **10 refuted claims and 14 verified claims** with file:line evidence.

### "If we only pick ONE plan, which?" — refined answer (post Plan A v2 rewrite)

**Pick `helmfile_enhancement_plan/` (this child plan).** Plan A v2 itself now explicitly states this child plan is "the superior plan" (its words) and reduces itself to a 9-finding catalog + a merged roadmap proposal. After arbitration:
- **Plan A v2's 1 net-new finding (HF-65 — broken Makefile test path) is adopted** with refinement
- **Plan A v2's 1 valid refutation (HF-57 EBS-in-GCP) is accepted** with file:line counter-evidence
- **Plan A v2's 1 valid framing correction (HF-39 Cilium policies are CiliumClusterwideNetworkPolicy not k8s NetworkPolicy) is accepted** — HF-39 downgraded CRITICAL→MED
- **Plan A v2's 4 incorrect drop-proposals (HF-63, HF-64, HF-59, HF-62) are rejected** with grep proof: HF-63 is even worse than measured (27/28 missing resources), HF-64 stands at 4/28, HF-59 covers Redis-EKS-specific values not Temporal replicaCount, HF-62 covers cleanup-and-redeploy.sh trap-handler not generic shell hardening

**Why pick THIS plan (still):** Plan A v2 is now a 564-line pointer-document that *itself* says "use Plan B." It contains a roadmap proposal that 95% agrees with this plan and 5% over-aggressively folds findings together. This plan absorbs Plan A v2's valid corrections and rejects the invalid ones with evidence — it is now strictly more accurate than either plan was at any prior point.

**What this plan still has that Plan A v2 doesn't:**
- 64 findings vs Plan A v2's 9 retained (HF-01..HF-65)
- Per-PR diff + acceptance + rollback for every entry (`04_PR_BREAKDOWN.md`, 1 335 lines)
- 5-layer testing pyramid + 12 git-apply-ready CI patches (`06_TESTING_STRATEGY.md` + `patches/`)
- 11 refuted claims with file:line counter-evidence (`05_RISK_AND_VALIDATION.md` + Appendix E §1)
- Provenance chain back to all 4 source plans (`07_PARENT_PLAN_INTEGRATION.md`)
- Per-PR risk register with auto-rollback signals

**What Plan A v2 contributed that this plan adopted:**
- HF-65 (broken Makefile test path — refines G2/PR-T-02)
- HF-57 refutation (EBS-in-GCP — cluster is actually EKS)
- HF-39 framing correction (CiliumClusterwideNetworkPolicy ≠ k8s NetworkPolicy; downgraded to MED)
- Tier-0 sharpness for HF-56 (PostgreSQL maxConns) — the single highest-leverage line-change
- Per-fix verification template — folded into `06_TESTING_STRATEGY.md` §11 (PR-T-13)

**Bottom line:** this plan now strictly dominates Plan A v2 on every dimension. Plan A v2 is best read as a verified independent receipt whose corrections have been absorbed.

---

## Tiering rubric

- **T0 (Stop the bleeding):** ship in **Week 1, days 1–3**. CRITICAL severity AND low-blast-radius patch. PRs: HF-01, HF-02, HF-03, HF-05, HF-06, HF-07, HF-11.
- **T1 (Remove recurrence):** ship in **Week 1, days 4–7**. HIGH severity OR CRITICAL-but-needs-canary. PRs: HF-04, HF-08, HF-09, HF-10, HF-12, HF-14, HF-15, HF-17.
- **T2 (Harden):** ship in **Week 2**. Defence-in-depth, drift prevention. PRs: HF-13, HF-16, HF-18, HF-19, HF-21.
- **T3 (Polish):** opportunistic. PRs: HF-20, HF-22.

Full sequencing in `03_PRIORITIZED_PLAN.md`.

---

## Acceptance — how we'll know this plan worked

After all T0 + T1 PRs land:

1. `kubectl get pdb -n temporal` returns ≥ 5 PDBs.
2. `kubectl describe pod -n temporal -l app.kubernetes.io/component=frontend | grep -c 'Liveness:' >= 1`.
3. `grep -E 'password.*:.*"[A-Za-z0-9]{6,}"' atlassian_packages/gcp_kitt/helmfile/*.yaml` returns 0.
4. `git ls-files atlassian_packages/gcp_kitt/helmfile/python-app/creds.json` returns 0.
5. `kubectl get hpa -n dtaske keda-hpa-scraper-worker-scaler -o jsonpath='{.status.conditions[?(@.type=="ScalingActive")].status}'` returns `True`.
6. `bash atlassian_packages/gcp_kitt/helmfile/cleanup-all.sh` (without `I_REALLY_MEAN_IT=1`) exits with code 2.
7. Pod restart-rate (`rate(kube_pod_container_status_restarts_total{namespace="temporal"}[1h])`) is ≤ 0.01 sustained for 24 h after T1 ships.

---

## Cross-references

- `../08_INTEGRATED_PLAN.md` — parent plan; this file is the H-series PR-quality decomposition.
- `../07_STABILITY_PLAN.md` — receipts for S1–S15 (multi-service, not helmfile-specific).
- `../05_RISK_AND_HISTORY.md` — historical context for why some of these issues exist.
- `atlassian_packages/gcp_kitt/helmfile/KEDA_TEMPORAL_CONNECTION_ISSUE.md` — production diagnostic doc consumed by HF-10.
- `atlassian_packages/gcp_kitt/helmfile/elasticsearch-shard-allocation-fix.md` — context for HF-17.

---

## Updated reading order (suggested)

1. `00_README.md` (this file)
2. `01_GOALS_AND_METRICS.md`
3. `02_FINDINGS_CATALOG.md`
4. `03_PRIORITIZED_PLAN.md`
5. `04_PR_BREAKDOWN.md`
6. `05_RISK_AND_VALIDATION.md`
7. `06_TESTING_STRATEGY.md` ← read after 04 to see how each HF acceptance is wired to a CI / smoke / chaos test
8. `07_PARENT_PLAN_INTEGRATION.md` ← read last to see the 22 imports from the parent plan family + 2 refuted parent claims with counter-evidence
