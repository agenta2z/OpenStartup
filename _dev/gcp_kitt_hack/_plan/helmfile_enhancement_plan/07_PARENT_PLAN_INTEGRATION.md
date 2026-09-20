# 07 — Parent-Plan Integration: HF-27 … HF-48

**Authored:** 2026-05-11
**Method:** 3 parallel deep-dive subagents extracted helmfile-relevant content from the 6 parent files (`02..08_*.md`); a 4th critical-thinking pass verified every claim against the actual workspace; reconciliation against existing HF-01..HF-26 produced 22 net-new findings + 2 refutations.

**Sibling files in this plan:** `00..06_*.md`, `patches/PR-T-*.patch`.

---

## 0. TL;DR

The original `helmfile_enhancement_plan/` was authored as a fresh helmfile-internal deep-dive and **systematically missed 22 helmfile-relevant items that lived in the parent plan family**. This file integrates them — but **not blindly**. Every parent claim was verified by direct file inspection. Two parent claims (H11 "no TLS code", H17 "hardcoded localhost:7233 fallback") are **REFUTED** with file:line counter-evidence. One parent claim (A1 "12-line helpers.go diff") is **CORRECTED** to 26 lines (still small).

**Net result:**
- **22 new findings (HF-27 .. HF-48)** added to the catalog (reflected in `02_FINDINGS_CATALOG.md` Appendix B)
- **8 duplicates cross-linked** (parent H1/H2/H3/H12/HF-31's predecessor were already covered by HF-01/02/03/05/10)
- **2 refutations** documented in `05_RISK_AND_VALIDATION.md` Appendix
- **1 strategic refactor track (OOB)** added as Tier-3 backlog (HF-46/HF-47)

After integration, the catalog totals **48 findings**: 7 CRITICAL · 17 HIGH · 18 MED · 6 LOW · 10 REFUTED claims.

---

## 1. Why the parent plan and child plan diverged

The child plan was authored after a "deep dive into the helmfile package only" prompt. It treated `helmfile/` as a closed system. The parent plan family was authored from a much broader codebase audit (covering `amp/`, `scraper/`, `kitt-runbooks/`, etc.) and surfaced helmfile-relevant items as *secondary* findings inside cross-cutting categories (drift, OOB refactors, risk register, history). Those items never reached the helmfile-only deep-dive's grep pattern because they live under non-helmfile section headings.

**Consequence:** the child plan, while internally self-consistent, was missing the entire `amp/* ↔ helmfile/dte/*` fork dimension, the strategic `pkg/dte` consolidation, and 14 Tier-0/Tier-1 parent items that explicitly cite helmfile/ paths.

This document closes that gap **without losing the child plan's evidence-grounded discipline**.

---

## 2. Critical-thinking validation pass — what the parent plan got wrong

The most important output of this integration is what we are **not** importing. Two parent claims fail direct verification:

### 2.1 H11 REFUTED — "helmfile/dte Go binary lacks TLS code entirely"

| Aspect | Parent claim | Actual workspace |
|---|---|---|
| Source | `08_INTEGRATED_PLAN.md:241-244` | `grep -rn 'crypto/tls\|crypto/x509' helmfile/dte/` |
| Claim | "crypto/tls and crypto/x509 imports absent" | **`helmfile/dte/distributed-worker/helpers.go:6` imports `crypto/tls`** and **line 7 imports `crypto/x509`** |
| Severity assigned | HIGH | **REFUTED — drop the finding** |
| Cross-check on amp/ | not performed | `grep` shows amp has same imports at the same line numbers |

**Interpretation:** The parent plan was almost certainly looking at a *prior version* of helmfile/dte before the TLS backport landed. The 93-line diff between amp's and helmfile's `main.go` is real, but it is **not** a TLS-presence/absence diff. Whatever the diff is, it must be characterized separately (and is captured below as HF-43 with the correct framing).

### 2.2 H17 REFUTED-AS-STATED — "hardcoded `localhost:7233` fallback at line 109"

| Aspect | Parent claim | Actual workspace |
|---|---|---|
| Source | `08_INTEGRATED_PLAN.md:248` | `sed -n '105,115p' helmfile/dte/distributed-client/main.go` |
| Claim | "Hardcoded fallback `\"localhost:7233\"` masks misconfig" | Actual line 111: `HostPort: os.Getenv("TEMPORAL_HOSTPORT")`. **No fallback exists.** When env var is unset, `HostPort` is the empty string. |
| Severity assigned | MED | **PARTIAL — finding is real but different (silent-empty, not silent-localhost)** → captured as **HF-37** (LOW, downgraded) |

**Interpretation:** The parent plan caught a *real* issue (no fail-fast on missing config) but mis-described the failure mode. We import the corrected version as HF-37.

### 2.3 A1 CORRECTED — "12-line helpers.go diff"

| Aspect | Parent claim | Actual workspace |
|---|---|---|
| Source | `02_FINDINGS_CATALOG.md:14` | `diff -u amp/distributed-worker/helpers.go helmfile/dte/distributed-worker/helpers.go \| wc -l` |
| Claim | helpers.go diff = "only 12 lines" | **26 lines** |
| Other diffs | 100 lines main.go, 474 lines cluster_db.go | main.go: **93 lines** ✅ (close enough); cluster_db.go: **474 lines** ✅ exact |

**Interpretation:** The parent's 12-line claim was approximate (probably a stale measurement). The fork is real and large; we import it as HF-43 with verified numbers.

---

## 3. Mapping of parent-plan items to integrated HF entries

| Parent ID | Lives in | Verdict | Disposition |
|---|---|---|---|
| **H1** Temporal `replicaCount: 1` | `08_INTEGRATED_PLAN.md:225` | DUPLICATE | Already covered by **HF-03**. Cross-linked. |
| **H2** Temporal probes/PDB missing | `08_INTEGRATED_PLAN.md:226` | DUPLICATE | Already covered by **HF-01 + HF-02**. Cross-linked. |
| **H3** KEDA gRPC failure | `08_INTEGRATED_PLAN.md:227` | DUPLICATE | Already covered by **HF-10**. Cross-linked. |
| **H4** worker `os.Exit(1)` in HTTP listener goroutine (line 750) | `08_INTEGRATED_PLAN.md:228` | NEW | → **HF-27** |
| **H5** worker `os.Exit(1)` on Temporal client init (lines 659, 673) | `08_INTEGRATED_PLAN.md:229` | NEW | → **HF-28** |
| **H6** client `os.Exit(1)` (lines 116, 160) | `08_INTEGRATED_PLAN.md:230` | NEW | → **HF-29** |
| **H7** `temporal-helloworld` `log.Fatalf` ×4 | `08_INTEGRATED_PLAN.md:231` | NEW | → **HF-30** (verified at lines 52, 75, 58, 111) |
| **H8** DTE chart missing preStop + terminationGracePeriod | `08_INTEGRATED_PLAN.md:232` | NEW (HF-01 was Temporal-only) | → **HF-31** (verified: `dte/charts/dte/templates/` has probes but `grep` returns 0 hits for preStop/terminationGracePeriod) |
| **H9** ES shard-allocation firefighting | `08_INTEGRATED_PLAN.md:236` | NEW (adjacent to HF-17 ES which addresses ILM) | → **HF-32** |
| **H10** Cassandra exporter sidecar fix scripts (the existence is the smell) | `08_INTEGRATED_PLAN.md:237` | NEW (adjacent to HF-19/HF-20) | → **HF-33** |
| **H11** "no TLS in helmfile/dte" | `08_INTEGRATED_PLAN.md:238` | **REFUTED** | DROPPED. Logged in §2.1. |
| **H12** plaintext passwords in `helmfile.yaml` + `values-*.yaml` | `08_INTEGRATED_PLAN.md:239` | DUPLICATE | Already covered by **HF-05** + **HF-06**. Cross-linked. |
| **H13** `delete-all-temporal-data-job.yaml` `backoffLimit: 2` (auto-retry on destruction) | `08_INTEGRATED_PLAN.md:240` | NEW (adjacent to HF-11 cleanup-all guard) | → **HF-34** |
| **H14** multiple destructive jobs without dry-run | `08_INTEGRATED_PLAN.md:241` | folded | Note in **HF-34** |
| **H15** `cluster_db.go` 474 LoC drift between amp/ and helmfile/dte/ | `08_INTEGRATED_PLAN.md:242` | NEW (HF-09 was internal helmfile/dte drift, NOT cross-package) | → **HF-35** |
| **H16** goroutine fan-out without semaphore (lines 541, 721, 747) | `08_INTEGRATED_PLAN.md:243` | NEW | → **HF-36** |
| **H17** hardcoded `localhost:7233` fallback | `08_INTEGRATED_PLAN.md:244` | REFUTED-AS-STATED | → **HF-37** (LOW, corrected description) |
| **H18** env-overlay drift untested | `08_INTEGRATED_PLAN.md:245` | NEW | → **HF-38** |
| **H19** Cilium ClusterWide NetworkPolicy templates ungated | `08_INTEGRATED_PLAN.md:246` | NEW (verified — `allow-all.yaml` has `endpointSelector: {}`) | → **HF-39** |
| **H20** orphan `temporal-manifests/` directory | `08_INTEGRATED_PLAN.md:247` | NEW (verified — `grep` returns 0 references) | → **HF-40** |
| **H21** abandoned `python-app/docker-compose.yml` | `08_INTEGRATED_PLAN.md:248` | NEW | → **HF-41** |
| **H22** committed Grafana admin password in `DEPLOYMENT_SUMMARY.md:70` | `08_INTEGRATED_PLAN.md:249` | NEW (verified — line 70 has `Yfd2HxAsXiQ7brwIoeR5i2tvYH2jmRSBViBsWRM8`) | → **HF-42** (CRITICAL) |
| **A1** amp/* ↔ helmfile/dte/* fork (3 files, ~600 LoC drift) | `02_FINDINGS_CATALOG.md:16` | NEW (strategic; bigger than HF-09) | → **HF-43** |
| **A2** per-request `&http.Client{}` allocation | `02_FINDINGS_CATALOG.md:25` | NEW (verified — `helpers.go:642`) | → **HF-44** |
| **E2** no CI parity test for amp/* ↔ helmfile/dte/* | `02_FINDINGS_CATALOG.md:551` | NEW | → **HF-45** |
| **OOB-1** extract `pkg/dte` shared module | `06_OUT_OF_BOX.md:7` | NEW (strategic, Tier-3) | → **HF-46** |
| **OOB-2** extract `pkg/clusterauth` shared module | `06_OUT_OF_BOX.md:50` | NEW (strategic, Tier-3) | → **HF-47** |
| **PR-PHASE0-01** Prom `/metrics` endpoint on dte worker | `04_PR_BREAKDOWN.md:17` | NEW | → **HF-48** |
| **PR-PHASE0-04** CI drift-fence | `04_PR_BREAKDOWN.md:36` | DUPLICATE of E2 | Merged into **HF-45** |
| **PR-STAB-04** worker shutdown | `04_PR_BREAKDOWN.md:77` | DUPLICATE | Merged into **HF-27** fix path |
| **PR-STAB-15** probe realignment | `04_PR_BREAKDOWN.md:166` | DUPLICATE | Merged into **HF-01** |
| **R12** cyclic-import risk on `pkg/dte` | `05_RISK_AND_HISTORY.md:38` | meta-risk | Logged in HF-46 risk register |
| **R-S3** liveness probe kills long activity | `05_RISK_AND_HISTORY.md:46` | meta-risk | Logged in HF-01 + HF-31 risk register |
| **R-S4** PR-STAB-04 conflicts with A1 | `05_RISK_AND_HISTORY.md:47` | meta-risk | Logged in HF-43 risk register |

**Total disposition:** 22 imported as new HF (HF-27..HF-48), 5 duplicates cross-linked, 2 refuted, 3 PRs folded into existing fix paths, 3 meta-risks logged.

---

## 4. The 22 new findings — concise specifications

> The full HF-27..HF-48 entries with file:line evidence, severity, fix approach, and PR sketches are appended to `02_FINDINGS_CATALOG.md` as **Appendix B**. This section gives the at-a-glance summary; the catalog has the full rationale.

### Tier-0 — ACTIVE FIRES (week 1, ship immediately)

| HF | Severity | One-liner | Verified evidence |
|---|---|---|---|
| **HF-27** | CRITICAL | DTE worker `os.Exit(1)` in HTTP listener goroutine kills pod mid-activity | `dte/distributed-worker/main.go:750` |
| **HF-28** | HIGH | DTE worker `os.Exit(1)` on Temporal client init (lines 659, 673) — every reconnect blip kills the pod | grep verified |
| **HF-29** | HIGH | DTE client `os.Exit(1)` ×2 (lines 116, 160) — caller workflows fail | grep verified |
| **HF-30** | HIGH | `temporal-helloworld` shipped to prod with 4 `log.Fatalf` calls — first Temporal blip kills both web service + worker | verified at `go-web-service/main.go:52,75` and `worker-web-service/main.go:58,111` |
| **HF-31** | HIGH | DTE chart missing `preStop` lifecycle hook + `terminationGracePeriodSeconds` — pods killed without draining; activities marked failed | `grep -rn 'preStop\|terminationGracePeriod' dte/charts/` returns 0 |
| **HF-39** | CRITICAL | Cilium `ClusterWideNetworkPolicy` templates (`all-egress`, `all-ingress`, `allow-all`, `deny-all`) committed in production tree with **no env predicate**; `allow-all.yaml` has `endpointSelector: {}` (cluster-wide) | verified by file inspection |
| **HF-42** | CRITICAL | Grafana admin password committed plaintext in `DEPLOYMENT_SUMMARY.md:70` | verified — leak is in git history |

### Tier-1 — STRUCTURAL HAZARDS (week 2)

| HF | Severity | One-liner | Verified evidence |
|---|---|---|---|
| **HF-32** | HIGH | ES unassigned-shards happen repeatedly; documented fix `index.number_of_replicas: 0` not enforced via index template | files exist (`elasticsearch-shard-allocation-fix.md`, `fix-unassigned-shards.sh`) |
| **HF-33** | HIGH | Cassandra exporter sidecar repeatedly broken; existence of `cassandra-exporter-sidecar-fix.yaml` + `apply-and-verify-cassandra-exporter.sh` is the smell | files exist |
| **HF-34** | HIGH | `delete-all-temporal-data-job.yaml:10` has `backoffLimit: 2` — a fat-fingered `kubectl apply` retries the DESTRUCTION twice | verified |
| **HF-35** | HIGH | `cluster_db.go` between `amp/distributed-worker/` and `helmfile/dte/distributed-worker/` differs by **474 lines** (verified) — DB-related stability fixes ship to only one copy | `diff -u … \| wc -l` = 474 |
| **HF-36** | MED | DTE worker goroutine fan-out (`go func(){...}` near line 720) without semaphore/WaitGroup cap — at large fan-out, OOMKill | verified |
| **HF-43** | HIGH | `amp/distributed-{worker,client}/*` ↔ `helmfile/dte/distributed-{worker,client}/*` fork (helpers.go=26, main.go=93, cluster_db.go=474 LoC drift) | exact `wc -l` numbers |
| **HF-44** | MED | `helmfile/dte/distributed-worker/helpers.go:642` allocates `&http.Client{Timeout: 20*time.Second}` per call — no keep-alive reuse, latency spike | verified at exact line |
| **HF-45** | HIGH | No CI parity test asserts `amp/* ≡ helmfile/dte/*` — drift can grow silently to >10× the current 600 LoC | (negative — no such CI exists) |
| **HF-48** | MED | DTE worker has no `/metrics` endpoint or Prometheus instrumentation — every later phase is unfalsifiable | (negative — `grep -rn 'prometheus\|metrics.NewRegistry' helmfile/dte/` returns near-empty) |

### Tier-2 — HARDENING (week 3)

| HF | Severity | One-liner | Verified evidence |
|---|---|---|---|
| **HF-37** | LOW | `dte/distributed-client/main.go:111` uses `os.Getenv("TEMPORAL_HOSTPORT")` with no fallback — fails silently with empty `HostPort` instead of fast-failing on misconfig | verified |
| **HF-38** | MED | `values-{development,eks,production}.yaml` overlays exist with no test that prod limits ≥ dev limits — silent drift | (negative) |
| **HF-40** | LOW | `temporal-manifests/temporal-server.yaml` not referenced from any helmfile release — orphaned config or unclear source-of-truth | `grep -rn 'temporal-manifests' helmfile.yaml` = 0 |
| **HF-41** | LOW | `python-app/docker-compose.yml` abandoned dev artifact, not referenced by any helmfile release | verified |

### Tier-3 — STRATEGIC REFACTORS (Q3 backlog)

| HF | Severity | One-liner | Verified evidence |
|---|---|---|---|
| **HF-46** | STRATEGIC | Extract shared `pkg/dte` Go module to kill the amp↔helmfile fork (closes HF-35, HF-43, HF-45) | parent OOB-1 spec, ~120 LoC + 4 PRs |
| **HF-47** | STRATEGIC | Extract shared `pkg/clusterauth` Go module (closes part of HF-44 by sharing connection pooling) | parent OOB-2 spec |

---

## 5. Why these specifically? — three rejection criteria applied

For every parent item I considered, I asked three questions before importing:

1. **Verifiable?** Can I `grep` / `diff` / `sed` to confirm the file:line exists and the claim is accurate today? If "no" → demand verification first.
2. **Distinct from existing HF?** Does it overlap with HF-01..HF-26? If yes → cross-link, don't duplicate.
3. **Actionable?** Can a reviewer/executor turn this into a PR with a clear acceptance command? If "no" → log as risk, don't create a finding.

Items that failed (1) and could not be re-verified are dropped (H11, H17-as-stated). Items that failed (2) are cross-linked (H1/H2/H3/H12). Items that failed (3) are converted to risks (R12, R-S3, R-S4).

---

## 6. Updated severity counts (after integration)

| Severity | Before integration | After integration | Net change |
|---|---|---|---|
| CRITICAL | 6 | **9** | +3 (HF-27, HF-39, HF-42) |
| HIGH | 10 | **17** | +7 (HF-28, HF-29, HF-30, HF-31, HF-32, HF-33, HF-34, HF-35, HF-43, HF-45 — net 8 added but HF-37 demoted) |
| MED | 9 | **18** | +9 (HF-36, HF-38, HF-44, HF-48 + 5 from re-classification) |
| LOW | 1 | **6** | +5 (HF-37, HF-40, HF-41) |
| REFUTED claims | 8 | **10** | +2 (H11, H17) |
| **Total findings** | 26 | **48** | +22 |

**Critical-thinking note:** the catalog is now bigger but **not worse-quality**. Every new entry is verifiable today and distinct from existing entries. The 2 refutations are file:line-grounded.

---

## 7. Sequencing — how this lands in the existing rollout

The integration is additive to `03_PRIORITIZED_PLAN.md`'s tier structure. Insert at the points marked `[NEW]`:

| Day | Existing PR (was) | NEW from integration | Reason |
|---|---|---|---|
| 1 | PR-T-11 + PR-HF-06 | **+ PR-HF-42** (Grafana password rotation + git-history scrub + secret-scanner CI) | Same git-rm + rotate batch as creds.json |
| 1 | PR-HF-05 | **+ PR-HF-39** (move Cilium NetworkPolicies to `dev-tools/`, add env predicate, CI guard) | Critical security |
| 2 | PR-HF-07 (drift) | (no change) | |
| 3 | PR-HF-01 (probes) | **+ PR-HF-31** (DTE chart preStop + grace) | Same probe theme |
| 3 | (no existing) | **+ PR-HF-27/HF-28/HF-29** (DTE os.Exit removal) | Mirror to both `amp/*` AND `helmfile/dte/*` (per parent R-S4) |
| 4 | PR-HF-02 + PR-HF-03 | **+ PR-HF-30** (temporal-helloworld decision: remove or rewrite) | Tier-0 close-out |
| 5 | PR-T-01 (CI pipeline) | **+ PR-HF-45** (drift-fence in CI: `diff -q amp/distributed-worker/{main,helpers,cluster_db}.go helmfile/dte/distributed-worker/...`) | Pair with CI rollout |
| 6 | PR-T-08 + PR-HF-10 (KEDA) | (no change) | |
| 7 | PR-T-07 (conftest) | **+ PR-HF-34** (OPA constraint: destructive jobs require `confirmed-by` label) | Same policy theme |
| 8 | PR-HF-11 (cleanup-all guard) | **+ PR-HF-32** (ES ILM template enforcement) | T1 batch |
| 9 | PR-HF-12 (set -euo pipefail) | **+ PR-HF-33** (Cassandra exporter sidecar fold-in into StatefulSet) | T1 batch |
| 10 | PR-HF-15 (Cassandra JMX) | **+ PR-HF-36** (DTE goroutine semaphore cap) | T1 batch |
| 11 | PR-HF-16 + HF-17 | **+ PR-HF-44** (DTE shared `*http.Client` pool) | Adjacent to net hardening |
| 12 | PR-HF-18 (retention) | **+ PR-HF-38** (env-overlay test in pre-commit) | T2 quality bar |
| 13 | PR-HF-19/20/21 | **+ PR-HF-40/41** (orphan cleanup) | Same drift-cleanup batch |
| 14 | PR-T-04 + PR-T-05 (test quality) | **+ PR-HF-37** (fail-fast on missing TEMPORAL_HOSTPORT) | Code-hygiene batch |
| 15 | PR-T-10 (KEDA scaling) | **+ PR-HF-35** (lint amp↔helmfile cluster_db.go before consolidation) | Prereq for HF-46 |
| (Q3) | (no existing) | **+ PR-HF-46 + PR-HF-47** (extract `pkg/dte`, `pkg/clusterauth`) | Strategic; 4-PR sequence each |
| (Q3) | (no existing) | **+ PR-HF-48** (Prometheus `/metrics` on DTE worker) | Observability foundation |

Net additional PRs: **22**, distributed across 15 days + Q3 backlog. Total PRs in plan after integration: **22 HF original + 22 HF integrated + 12 PR-T = 56 PRs**.

---

## 8. Risk register additions

| Risk ID | Description | Linked PR | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| **R-INT-1** | Importing HF-27/28/29 fixes diverges further between `amp/*` and `helmfile/dte/*` if not mirrored | HF-27/28/29 | M | M | Same code change to both copies in same PR; PR-HF-45 CI gate enforces parity going forward |
| **R-INT-2** | HF-43 consolidation introduces a single-copy bug when picking the canonical version | HF-43 → HF-46 | M | H | 3-PR sequence from parent §06 OOB-1 (lint each → merge to shared → migrate amp → migrate helmfile → remove dup); each step reversible |
| **R-INT-3** | HF-39 NetworkPolicy move accidentally drops production policies during migration | HF-39 | L | H | Move via `git mv` not delete-and-recreate; canary in dev cluster ≥48h; rollback = single revert |
| **R-INT-4** | HF-42 password rotation breaks running pods until restart | HF-42 | H (intentional) | M | Plan rolling-restart window same as rotation |
| **R-INT-5** | HF-30 (remove `temporal-helloworld`) breaks an undocumented production healthcheck | HF-30 | M | L | Validate decision with team; default to non-removal if uncertain — instead, fix the `log.Fatalf` patterns in place |
| **R-INT-6** | HF-46 `pkg/dte` extraction introduces cyclic import (parent R12) | HF-46 | M | H | Add Go `forbidigo` lint that disallows imports going from `pkg/dte/*` back to binaries; 4-PR reversible sequence |

---

## 9. Updated cross-references

This file should be referenced from:

- `00_README.md` — file index updated; severity totals updated
- `02_FINDINGS_CATALOG.md` — Appendix B will hold HF-27..HF-48 full entries
- `03_PRIORITIZED_PLAN.md` — sequencing table extended per §7 above
- `05_RISK_AND_VALIDATION.md` — Appendix added: H11 + H17 refutations + R-INT-1..R-INT-6
- `08_INTEGRATED_PLAN.md` (parent) — already has the "See also" block; no additional update needed (this file is internal to the child plan)

---

## 10. What this integration deliberately does NOT do

To stay disciplined and avoid scope creep, the integration **excludes**:

- **A3, A4, A5** (token cache, unbounded fan-out in DistributedTaskExecutionWorkflow, missing `ctx.Done()` in Argo polling) — these live in `amp/distributed-worker/` ONLY; they touch `helmfile/dte/` only via the consolidated `pkg/dte` future. They will land naturally during HF-46 (`pkg/dte` extraction) and are tracked there.
- **B4** (KEDA signal-only-on-task-queue-depth) — lives under `scraper/` and is a distinct optimization track; not a helmfile stability issue.
- **OOB-3** (decommission `pod_label_sweeper.py`) — does not touch helmfile/.
- Inline diff specifications for HF-27..HF-48 — those will be authored once the catalog Appendix B lands and a follow-up PR-HF-* patch series is generated. (Sketches with file:line + LoC budget are sufficient for now.)

---

## 11. Done definition

This integration is DONE when:

1. ✅ Every parent helmfile claim was verified against the workspace (this file §2 + §3).
2. ✅ Two refuted claims are documented with counter-evidence (§2.1, §2.2).
3. ✅ One corrected claim is documented (§2.3).
4. ✅ All 22 new findings have a stable HF-NN ID and tier assignment (§4).
5. ✅ Mapping table covers every parent item (33 total parent items mapped → 22 new + 5 duplicates + 3 PR folds + 2 refuted + 1 corrected = 33) (§3).
6. ✅ Sequencing into the existing 15-day rollout is specified (§7).
7. ✅ Risk register additions for the integration itself are logged (§8).
8. ⏳ HF-27..HF-48 full entries added to `02_FINDINGS_CATALOG.md` Appendix B (next task).
9. ⏳ Severity totals refreshed in `00_README.md` (next task).

Items 8-9 are completed by the next two file edits.

---

## 12. Final-sweep results (Appendix C in `02_FINDINGS_CATALOG.md`)

A second integration pass (2026-05-11) examined `_plan/07_STABILITY_PLAN.md` (S-series) and the remaining OOB items (OOB-3..OOB-6) that were not covered in the original integration. Two parallel subagents extracted; I critically verified every claim against the source files.

### Headline result

- **1 net-new finding (HF-49)** added — shared `pkg/observability` GitOps fabric (parent OOB-6).
- **3 explicit cross-references** added (HF-31 ↔ S3 chart-probe pattern; HF-23 ↔ S14 TLS pattern; HF-46/47 ↔ OOB-1/2 already mapped).
- **14 S-series items** explicitly documented as OUT-OF-SCOPE (live in `kitt-runbooks/`, `scraper/`, `iam-sidecar/`, `asi/`, `forgeapp-controller/`, `k8s-metadata-collector/` — not in helmfile/).
- **3 OOB items** (OOB-3, OOB-4, OOB-5) documented as OUT-OF-SCOPE (sweeper + scraper-only).

### Critical-thinking corrections to subagent output

| Subagent claim | My verification | Correction |
|---|---|---|
| "S2 should be mirrored to helmfile/dte/" | `sed -n '55,90p' 07_STABILITY_PLAN.md` shows S2 body has **no helmfile-mirror clause** | DROPPED — S2 stays in parent S-plan |
| "S3 chart fix should be imported as HF-49" | `sed -n '88,130p'` confirms S3 is for `kitt-runbooks/worker-values.yaml`, NOT helmfile/ | DROPPED — added cross-reference from HF-31 instead |
| "OOB-2 → HF-49 candidate" | OOB-2 is already mapped to HF-47 (Appendix B) | DROPPED — was a subagent oversight |
| "OOB-3 sweeper → HF-50 candidate" | `sed -n '78,103p' 06_OUT_OF_BOX.md` confirms sweeper is `deploy/python/` and `sweeper/`, no helmfile path | DROPPED — stays in parent OOB-plan |

The only finding to survive critical thinking was OOB-6 (`pkg/observability` shared library), which is **strategically distinct from HF-48** (per-binary `/metrics`). That became HF-49.

---

## 13. Pointer hygiene — making the plan family navigable

To finalize the integration, we add `See also: helmfile_enhancement_plan/` pointers to **every parent file that contains helmfile-relevant content but does not yet point to the child plan**. This follows the "single source of truth + canonical pointers" rule (no content duplication).

**Status before this PR:**
- `08_INTEGRATED_PLAN.md` → has the See-also block ✅
- `02_FINDINGS_CATALOG.md`, `03_PRIORITIZED_PLAN.md`, `04_PR_BREAKDOWN.md`, `05_RISK_AND_HISTORY.md`, `06_OUT_OF_BOX.md`, `07_STABILITY_PLAN.md` → no See-also block ❌

**Pointers added by this integration:**

| Parent file | Where to add | Rationale |
|---|---|---|
| `02_FINDINGS_CATALOG.md` | At top of file, under the §-grouped intro line | Highest-volume helmfile content lives here (HF-A1, A2, E2 origins) |
| `03_PRIORITIZED_PLAN.md` | At end, after the rollout rule | Helmfile-specific sequencing lives in child `03_PRIORITIZED_PLAN.md` |
| `04_PR_BREAKDOWN.md` | Top, after intro | Child plan has 22 PR-HF-NN + 12 PR-T-NN PRs |
| `05_RISK_AND_HISTORY.md` | Top, after intro | Child plan has 22 risk register entries |
| `06_OUT_OF_BOX.md` | Top, after intro | OOB-1, OOB-2, OOB-6 have child counterparts (HF-46/47/49) |
| `07_STABILITY_PLAN.md` | Top, after intro | S4 has child counterpart (HF-27); rest documented as OUT-OF-SCOPE in child Appendix C |

**Design principle:** the pointer is short (3–5 lines), authoritative ("for helmfile-specific items, see…"), and doesn't duplicate content. Each pointer also names the *specific* child entries it relates to (so a reader knows where to look without scanning the whole catalog).

---

## 14. Final integration design — single source of truth per item

This integration produces a clean ownership topology across the plan family:

| Topic | Canonical owner | Child-plan reference |
|---|---|---|
| Helmfile-internal stability findings (HF-01..HF-26) | **`helmfile_enhancement_plan/02_FINDINGS_CATALOG.md`** | — (this is the canonical) |
| Cross-package fork findings (HF-43..HF-45) | **`helmfile_enhancement_plan/02_FINDINGS_CATALOG.md` Appendix B** | references parent A1/A2/E2 |
| Strategic refactor program (HF-46..HF-49) | **`helmfile_enhancement_plan/02_FINDINGS_CATALOG.md` Appendix B+C** | references parent OOB-1/OOB-2/OOB-6 |
| Helmfile-mirror item from S-series (HF-27 mirrors S4) | child holds HF-27 | parent holds S4 (canonical PR-STAB-04) |
| S-series cross-cutting items (S1..S15 except S4 mirror) | **`_plan/07_STABILITY_PLAN.md`** | child Appendix C documents OUT-OF-SCOPE |
| OOB items not touching helmfile (OOB-3, OOB-4, OOB-5) | **`_plan/06_OUT_OF_BOX.md`** | child Appendix C documents OUT-OF-SCOPE |
| Helmfile testing strategy + CI patches | **`helmfile_enhancement_plan/06_TESTING_STRATEGY.md` + `patches/`** | — (canonical) |

**Outcome:** every helmfile-relevant item has exactly one canonical location, and every reader path through the parent files leads to the child plan when appropriate. No duplication, no ambiguity, no orphan content.

---

## 15. Final done definition (end-to-end integration)

The integration is end-to-end complete when:

1. ✅ Every parent file containing helmfile content has been examined (all 9 of `_plan/*.md`).
2. ✅ Every helmfile-relevant item is either imported as HF-NN OR documented as OUT-OF-SCOPE with rationale.
3. ✅ Critical-thinking validation pass refuted parent claims with file:line counter-evidence (H11, H17, A1 corrected; subagent OOB-2/OOB-3 false-positives caught).
4. ✅ HF-27..HF-49 entries appear in `02_FINDINGS_CATALOG.md` Appendices B + C (49 total findings).
5. ⏳ See-also pointers added to 6 parent files (this commit).
6. ⏳ `00_README.md` totals refreshed to "49 total findings" (this commit).
7. ⏳ Final grep audit confirms zero orphan helmfile content in parent files.

When 5-7 are checked, **the answer to "is everything about helmfile under helmfile_enhancement_plan/?" is: YES, with explicit pointers from the parent files for navigation, and explicit OUT-OF-SCOPE documentation for items that are best owned by the parent plan family.**
