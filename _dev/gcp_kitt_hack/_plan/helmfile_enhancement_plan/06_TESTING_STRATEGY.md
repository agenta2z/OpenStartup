# Testing Strategy — Current State, Gaps, Target Process

**Scope:** `atlassian_packages/gcp_kitt/helmfile/` (Temporal control plane + Cassandra + Elasticsearch + KEDA + DTE Go services + ops scripts).
**Authored:** 2026-05-11
**Method:** 4 parallel deep-dive subagents → critical-thinking validation against actual files (`grep -n`, `wc -l`, `find`).
**Sibling files:** `00_README.md`, `01_GOALS_AND_METRICS.md`, `02_FINDINGS_CATALOG.md`, `03_PRIORITIZED_PLAN.md`, `04_PR_BREAKDOWN.md`, `05_RISK_AND_VALIDATION.md`.

---

## 0. TL;DR

The helmfile package today has **70 Go test functions** across 6 files (better than first reported), **3 in-cluster smoke Jobs** (helloworld-workflow, helloworld-visibility, keda-connectivity), **1 manual health-check script** (`temporal-health-check.sh`, 8 stages), and **zero CI pipelines, zero PrometheusRules, zero pre-commit hooks**. Validation is overwhelmingly **manual + visual** (Grafana dashboards, README runbooks). The KEDA connectivity test is **TCP-only** so it does not catch the documented gRPC failure (`HF-10`). Several "test" Jobs are actually **setup jobs misnamed**, and one cluster-wide test (`temporal-helloworld/Makefile:test`) **silently swallows curl failures**.

This document defines a **5-layer testing pyramid** (lint → unit → contract → smoke → E2E/chaos), maps the existing artefacts onto those layers, identifies 17 gaps, and provides 12 PR-quality patches (`PR-T-01 … PR-T-12`) that close the gaps in a tiered way that respects the existing `04_PR_BREAKDOWN.md` work plan.

---

## 1. Why a testing-strategy file exists in this plan family

The 22 PRs in `04_PR_BREAKDOWN.md` change probes, replicas, secrets, network policies, retention, image pins, and shell scripts. Each carries a **per-PR acceptance command** but those commands assume the reviewer can run them by hand against a live cluster. **Without a testing fabric, the acceptance commands are aspirational.** This file makes them executable: every HF acceptance maps to a layer of the testing pyramid below, and every layer has a runner that produces a binary pass/fail signal.

It also addresses a deeper risk: many of the existing tests are **safety-theatre** — they apply something and report success even when the assertion never ran (e.g., `make test` in `temporal-helloworld/Makefile` uses `|| echo "❌"` which logs a sad face but still exits 0). A future executor would see "tests pass" and merge a regression. This document tags each existing test by its **truthfulness class** so we can decide what to trust.

---

## 2. The testing pyramid (what we'll target)

```
                ┌──────────────────────┐
                │  L5  Chaos / DR      │  ← seasonal, manual-triggered
                ├──────────────────────┤
                │  L4  E2E / Smoke     │  ← post-deploy, automated
                ├──────────────────────┤
                │  L3  Contract        │  ← schema, API, manifest validation
                ├──────────────────────┤
                │  L2  Unit            │  ← Go tests, Python tests
                ├──────────────────────┤
                │  L1  Lint / Static   │  ← pre-commit, every PR
                └──────────────────────┘
```

Each layer answers a different question:

| Layer | Question | Fast? | Live cluster? | Today's coverage |
|---|---|---|---|---|
| L1 — Lint / Static | "Did I write valid YAML/Go/shell?" | < 30s | no | **partial** (`go fmt` only) |
| L2 — Unit | "Does each function do what I claim?" | < 60s | no | **70 Go tests; 0 Python tests** |
| L3 — Contract | "Does the manifest comply with chart schema, k8s API, OPA?" | < 60s | no | **none** |
| L4 — E2E / Smoke | "After helmfile apply, does Temporal accept a workflow?" | 2–10 min | yes (canary) | **3 Jobs (one is TCP-only)** |
| L5 — Chaos / DR | "What happens when I drain a node, kill a pod, rotate a secret?" | hours | yes (canary) | **none documented** |

**Bottom line of current state**: L1 weak; L2 reasonable for DTE only; L3 absent; L4 incomplete (KEDA TCP-only); L5 absent.

---

## 3. Current state — verified inventory

All facts below were verified by direct file inspection (`grep -n`, `wc -l`, `find`) on 2026-05-11.

### 3.1 Go unit tests — `dte/`

| File | Test funcs | Lines | Quality notes |
|---|---|---|---|
| `dte/distributed-worker/cluster_db_test.go` | **14** | 404 | Mocked Kibana via httptest |
| `dte/distributed-worker/cluster_logging_test.go` | **4** | 276 | Logger field assertions |
| `dte/distributed-worker/helpers_test.go` | **22** | 651 | Largest; helpers + JWT split |
| `dte/distributed-worker/logging_test.go` | **7** | 288 | Structured logger sanity |
| `dte/distributed-worker/main_test.go` | **17** | 395 | Workflow + activities mocked |
| `dte/pkg/logger/logger_test.go` | **6** | 209 | Pure unit |
| **Total** | **70** | **2 223** | |

Quality concerns (sampled):
- `main_test.go` defines a `MockClusterDB` (line 18-22) but several activity tests appear to call only `assert.NotNil(...)` rather than asserting business logic. Re-grep of each `Test*` function for `assert.Equal\|require.Equal\|reflect.DeepEqual` would show how many tests carry an actual contract. **Action:** PR-T-04 audits this and tightens.
- **Coverage % unknown** because nothing runs `go test -coverprofile` today. We add this in PR-T-03.
- `dte/Makefile:test` runs `go test ./pkg/... ./cmd/...` — but **there is no `cmd/` directory**. Glob silently matches nothing for cmd. The `./pkg/...` path picks up only `pkg/logger` (6 tests) — **the 64 tests under `distributed-worker/` are NEVER run by `make test`.** This is a major bug captured as PR-T-02.

### 3.2 Python tests — `python-app/`

| File | Lines | Framework | Invoked by Makefile? | Assertions? |
|---|---|---|---|---|
| `python-app/test.py` | 225 | ad-hoc (boto3) | **no** | none — prints AWS responses |
| `python-app/test_api.py` | 153 | ad-hoc (`requests`) | yes (`make test`) | **none** — prints HTTP responses, never `assert` |

Both files **always exit 0**, even on failure. They are **manual diagnostic scripts** misnamed as tests. PR-T-05 converts at least `test_api.py` to pytest with assertions.

### 3.3 Kubernetes Job manifests classified as test/setup

Verified job specs (line numbers verified):

| File | Class | Image (pinned?) | `backoffLimit` | `ttl` | What it asserts |
|---|---|---|---|---|---|
| `test-helloworld-workflow-job.yaml` | smoke | `temporalio/admin-tools:1.28.1-tctl-1.18.4-cli-1.4.1` ✅ | 1 | 300s | tctl can describe a workflow |
| `test-helloworld-visibility-job.yaml` | smoke | `temporalio/admin-tools:1.28.1-tctl-1.18.4-cli-1.4.1` ✅ | 1 | 300s | workflow appears in `tctl list` (ES indexed) |
| `test-keda-temporal-connectivity-job.yaml` | connectivity (**TCP only**) | `curlimages/curl:latest` ❌ | 1 | 300s | TCP 7233 reachable; **does NOT exercise gRPC** → would not catch HF-10 |
| `check-schema-version-job.yaml` | schema | `cassandra:3.11.3` ✅ | 1 | 300s | reads `schema_version` from Cassandra |
| `temporal-namespace-register-job.yaml` | **setup (misnamed)** | `temporalio/server:1.28.1` ✅ | 5 | (none) | one-shot tctl namespace register |
| `temporal-keyspace-setup-job.yaml` | **setup (misnamed)** | `cassandra:3.11.3` ✅ | 3 | (none) | CREATE KEYSPACE IF NOT EXISTS |
| `temporal-schema-setup-job.yaml` | **setup (broken-as-test)** | `temporalio/server:1.28.1` ✅ | 3 | (none) | runs `temporal server start-dev` then dies — appears unhealthy |
| `setup-temporal-schema-job.yaml` | setup | `temporalio/admin-tools:1.28.1-tctl-1.18.4-cli-1.4.1` ✅ | 2 | 300s | applies temporal-cassandra schema |
| `create-default-namespace-job.yaml` | setup | `temporalio/admin-tools:1.28.1-tctl-1.18.4-cli-1.4.1` ✅ | 3 | 300s | tctl namespace register (idempotent) |

### 3.4 Shell scripts as tests/validators

| Script | Strict mode | Exit-code reliability | CI-ready? | Coverage of HF-10 (KEDA gRPC)? |
|---|---|---|---|---|
| `temporal-health-check.sh` | ✅ `set -euo pipefail` | reliable | **yes** | **partial** — stage 8 does a gRPC health check |
| `apply-and-verify-cassandra-exporter.sh` | `set -e` only | exits 0 even on warnings | manual-only | n/a |
| `fix-unassigned-shards.sh` | `set -e` only | counts FAILED but exits 0 | broken-as-test | n/a |
| `dte/scripts/force-delete-terminating-pods.sh` | ✅ | reliable | manual-only (destructive) | n/a |
| `temporal-helloworld/Makefile:test` | n/a | **always exits 0** (curl `\|\|` echo) | **broken-as-test** | n/a |
| `python-app/Makefile:test` | n/a | calls `test_api.py` (no assertions) | broken-as-test | n/a |

**`temporal-health-check.sh` stages** (verified line numbers):

| Stage | Lines | Function | What it covers |
|---|---|---|---|
| 1 | 38–46 | `check_cluster_access()` | kubectl works |
| 2 | 48–56 | `check_namespace()` | `temporal` ns exists |
| 3 | 58–106 | `check_deployment()` | ready replicas, recent restarts |
| 4 | 107–139 | `check_statefulset()` | Cassandra/ES pod state, disk |
| 5 | 140–156 | `check_service_endpoints()` | endpoints populated |
| 6 | 157–168 | `check_resource_usage()` | kubectl top |
| 7 | 169–197 | `check_stuck_pods()` | NotReady / CrashLoop |
| 8 | 198–216 | `check_network_connectivity()` | DNS → TCP → **gRPC** /grpc.health.v1.Health/Check |

Stage 8 is the closest existing test to HF-10. **It is not run automatically anywhere.** PR-T-09 wires it into a postsync hook.

### 3.5 CI / lint / pre-commit — verified absences

- `bitbucket-pipelines.yml` at gcp_kitt root: NOT FOUND (verified by `find /Users/tchen7/MyProjects/atlassian_packages/gcp_kitt -maxdepth 2 -name 'bitbucket-pipelines.yml'`).
- `.github/workflows/` directory: NOT FOUND.
- `.pre-commit-config.yaml`: NOT FOUND.
- `helmfile lint` invocation: NOT FOUND in any Makefile or script.
- `helm template --validate`: NOT FOUND.
- `kubeval`, `kube-linter`, `kube-score`, `conftest`, `polaris`: NOT FOUND.
- `golangci-lint`: called by `dte/Makefile:lint` but the target uses `command -v golangci-lint >/dev/null || exit 0`, so it silently passes when the binary is missing.
- `go fmt`: called by `dte/Makefile:fmt`, but reformats without failing.

**Net:** the helmfile package has **no automated test gate**. Code lands by visual review only.

### 3.6 Stale build artifact in git: `dte/distributed-worker.test`

- Size: **79 952 146 bytes (~76 MB)**.
- File mode: `-rwxr-xr-x` (executable).
- Origin: compiled Go test binary (`go test -c -o distributed-worker.test`).
- Referenced anywhere? **NO** (`grep -rn distributed-worker.test` returns 0 hits).
- Likely cause: developer ran `go test -c` once and committed by accident.

This is **bloat + supply-chain risk** (anyone running it from a stale checkout would execute month-old test code). PR-T-11 deletes it and adds a `.gitignore` rule.

### 3.7 Observability-as-test (current)

- Grafana dashboards: **4** (cassandra, postgresql, redis, temporal). None of them carry `alert:` blocks.
- ServiceMonitors: **2** (`temporal-services-servicemonitors.yaml`, `cassandra-servicemonitor.yaml`). Scrape targets defined; metrics consumed only by humans.
- `kind: PrometheusRule`: **0** (`grep -rn 'kind: PrometheusRule' helmfile/` returns 0).
- Documented runbooks (READMEs with "Verify" / "Smoke test" / "Health check" sections): **9** (see §3.8). All manual; no automation.

### 3.8 Documented manual runbooks (verified)

| README | Section | Lines | Type |
|---|---|---|---|
| `helmfile/README.md` | Health Checks; Testing | 345; 376 | manual connectivity |
| `helmfile/bootstrap/README.md` | Test service discovery workflow | 106 | manual workflow |
| `helmfile/bootstrap/DEPLOYMENT_RESULTS.md` | Test Workflow Execution; Verify installation | 73; 208 | post-deploy checklist |
| `helmfile/DEPLOYMENT_ORDER.md` | Test deployment | 56 | phase manual |
| `helmfile/KEDA_TEMPORAL_CONNECTION_ISSUE.md` | Testing Commands | 135 | troubleshooting |
| `helmfile/temporal-helloworld/README.md` | Test workflow execution; Test endpoints | 124, 160; 163 | manual e2e |
| `helmfile/dte/README.md` | Health Checks; Test health-check; Test service-discovery | 340; 463; 468 | manual health |
| `helmfile/cassandra-metrics-exporter-summary.md` | Health Metrics | 194 | metrics docs |
| `helmfile/kibana-monitoring-setup.md` | Verify monitoring is enabled | 72 | manual logging |

---

## 4. Truthfulness classification (don't trust everything labelled "test")

| Class | Definition | Example | Decision |
|---|---|---|---|
| **TRUTHFUL** | runs assertion; non-zero exit on fail | DTE Go tests; `temporal-health-check.sh` | keep as-is |
| **PARTIAL** | runs assertion but exits 0 in some failure modes | `apply-and-verify-cassandra-exporter.sh`; `test-keda-temporal-connectivity-job.yaml` (TCP-only) | tighten via PR-T-* |
| **SAFETY-THEATRE** | applies/runs but never asserts; always exits 0 | `python-app/test.py`, `test_api.py`; `temporal-helloworld/Makefile:test` | rewrite or delete |
| **MISNAMED-SETUP** | called "test" but is actually a one-time setup | `temporal-namespace-register-job.yaml`, `temporal-keyspace-setup-job.yaml`, `temporal-schema-setup-job.yaml`, `setup-temporal-schema-job.yaml` | rename or move out of `test-*` namespace |

This taxonomy is enforced by PR-T-12 (a CI lint that grep-checks names match behaviour).

---

## 5. The 17 verified test gaps

| # | Gap | Layer | Today | Target | Linked PR |
|---|---|---|---|---|---|
| **G1** | No CI pipeline runs anything on PR | L1-L3 | nothing | `bitbucket-pipelines.yml` runs L1+L2+L3 in <5 min on every PR | `PR-T-01` |
| **G2** | `dte/Makefile:test` glob misses `distributed-worker/` and `distributed-client/` | L2 | only 6/70 tests run | all 70 + new packages run | `PR-T-02` |
| **G3** | No coverage report; coverage % unknown | L2 | unknown | `go test -coverprofile`; coverage published; threshold ≥40% | `PR-T-03` |
| **G4** | Vacuous Go assertions in some tests (NotNil only) | L2 | unknown count | audit + tighten to assert business outputs | `PR-T-04` |
| **G5** | `python-app/test_api.py` and `test.py` are safety-theatre (no assertions) | L2 | always exit 0 | pytest with assertions; mocked backend | `PR-T-05` |
| **G6** | No helmfile/Helm chart manifest validation | L3 | nothing | `helmfile lint`, `helm template \| kubeval`, `kube-linter`, `polaris audit` in CI | `PR-T-06` |
| **G7** | No OPA/conftest policy tests for HF-15 (JMX), HF-13 (latest tags), HF-05 (plaintext secrets) | L3 | nothing | `conftest test --policy ./policy *-job.yaml helmfile.yaml` | `PR-T-07` |
| **G8** | KEDA test is TCP-only (won't catch HF-10 gRPC fail) | L4 | TCP-only | replace `nc` with `grpcurl` health-check probe | `PR-T-08` |
| **G9** | Temporal health-check script never run automatically | L4 | manual only | wire as postsync hook + scheduled CronJob | `PR-T-09` |
| **G10** | No assertion that helloworld smoke job actually scaled up via KEDA HPA | L4 | not asserted | extend smoke job to load-generate then assert `replicas > 1` | `PR-T-10` |
| **G11** | 76 MB compiled test binary `dte/distributed-worker.test` checked into git | L1 | bloat + risk | `git rm` + `.gitignore` | `PR-T-11` |
| **G12** | Test names don't match behaviour (`test-*` vs `setup-*`) | L1 | confusing | CI rule: `test-*-job.yaml` must contain at least one `assert\|fail\|exit 1` | `PR-T-12` |
| **G13** | No PrometheusRule / alert anywhere | L4 | only dashboards | first PrometheusRule introduced in `PR-HF-22`; reuse pattern | already in `PR-HF-22` |
| **G14** | No PDB-blocks-eviction synthetic test | L5 | nothing | drain-test job: `kubectl drain --delete-emptydir-data` + assert PDB violation | `PR-T-13` (T2 backlog) |
| **G15** | No probe-restart-loop synthetic test (`PR-HF-01` regression) | L5 | nothing | inject a 30-min activity, assert pod NOT restarted | `PR-T-13` |
| **G16** | No secret-rotation drill | L5 | nothing | rotate `temporal-postgres-secret`, expect rolling restart, no data loss | `PR-T-14` (T3 backlog) |
| **G17** | No upgrade/rollback drill (helmfile minor-version bump) | L5 | nothing | scripted: `helmfile apply` → record metric → `helm rollback` → assert metric ≥ baseline | `PR-T-15` (T3 backlog) |

---

## 6. Target end-state — the testing pyramid wired up

After all `PR-T-*` PRs land, every code change to `helmfile/` will pass through this gate sequence:

```
git push
  │
  ▼
[ pre-commit hook ]    L1: yamllint + shellcheck + go fmt + ban :latest tags
  │ pass
  ▼
[ CI: bitbucket-pipelines.yml ]
  ├─ L1 lint stage           ~30s   yamllint, shellcheck, hadolint, kube-linter, polaris
  ├─ L2 unit stage           ~90s   go test ./..., pytest python-app/, coverage gate
  ├─ L3 contract stage       ~60s   helmfile lint + helm template | kubeval + conftest
  └─ L3 manifest schema      ~30s   kustomize/values.schema.json
  │ pass
  ▼
[ merge → CD: helmfile apply against canary cluster ]
  │
  ▼
[ L4 post-deploy hooks (helmfile postsync) ]
  ├─ test-helloworld-workflow-job (smoke; existing)
  ├─ test-helloworld-visibility-job (visibility; existing)
  ├─ test-keda-temporal-connectivity-job (now gRPC; PR-T-08)
  ├─ temporal-health-check-cronjob (every 5 min; PR-T-09)
  └─ keda-scaling-validation-job (synthetic load; PR-T-10)
  │ pass
  ▼
[ L5 weekly chaos drill (manual-trigger) ]
  ├─ pdb-drain-drill              (PR-T-13)
  ├─ probe-restart-loop-drill     (PR-T-13)
  ├─ secret-rotation-drill        (PR-T-14)
  └─ upgrade-rollback-drill       (PR-T-15)
```

Every layer produces a binary pass/fail. A failure at any layer **blocks the next layer**. Layers L1-L3 fail-fast on PR; L4 fails the helmfile apply (via `apply-and-verify.sh` from `PR-HF-14`); L5 pages on-call but does not block deploys.

---

## 7. Mapping HF acceptance criteria → testing layer

Every `PR-HF-NN` in `04_PR_BREAKDOWN.md` carries an acceptance command. This table assigns each to its layer so the executor knows where to wire it.

| HF PR | Acceptance command | Layer | Runner |
|---|---|---|---|
| `PR-HF-01` (probes) | `kubectl describe pod ... \| grep -c 'Liveness:' >= 3` | L4 | new `verify-probes-job.yaml` (PR-T-09 wraps) |
| `PR-HF-02` (PDBs) | `kubectl get pdb -n temporal \| wc -l >= 5` | L4 | extends health-check script |
| `PR-HF-03` (replicaCount) | `kubectl get deploy -o json \| jq replicas` | L4 | health-check |
| `PR-HF-04` (CPU limits) | `kubectl get deploy -o json \| jq limits.cpu` | L3 | conftest policy "no CPU limit on JVM" (PR-T-07) |
| `PR-HF-05` (secrets) | `grep -E 'password.*:.*"...' helmfile/*.yaml \| wc -l == 0` | L1 | pre-commit hook (PR-T-11) |
| `PR-HF-06` (creds.json) | `git ls-files python-app/creds.json \| wc -l == 0` | L1 | pre-commit + CI scan |
| `PR-HF-07` (drift) | `find -name 'temporal-values*.yaml'` ≤ 1 with UNUSED header | L1 | CI script |
| `PR-HF-08` (needs:) | `helmfile --debug template \| grep needs:` ≥ 4 | L3 | helmfile lint stage |
| `PR-HF-09` (cluster_db) | `go build && go test ./...` (PR-T-02 fixes glob) | L2 | go test |
| `PR-HF-10` (KEDA) | `kubectl get hpa ... ScalingActive==True` | L4 | PR-T-08 (gRPC variant) |
| `PR-HF-11` (cleanup-all guard) | `bash cleanup-all.sh; [ $? == 2 ]` | L1 | shellcheck + script smoke-test |
| `PR-HF-12` (set -euo pipefail) | `head -3 *.sh \| grep -q 'set -euo pipefail'` | L1 | shellcheck (PR-T-01) |
| `PR-HF-13` (image pin) | `grep -n 'image:.*:latest' *-job.yaml \| wc -l == 0` | L1 | conftest "no :latest" (PR-T-07) |
| `PR-HF-14` (apply-and-verify) | synthetic bad-job hook returns ≠0 | L4 | smoke job (already in PR description) |
| `PR-HF-15` (Cassandra JMX) | `kubectl run nc-test ... ; expect refused` | L4 | extends health-check |
| `PR-HF-16` (seed cap) | `nodetool gossipinfo \| grep -c seed ≤ 3` | L4 | health-check |
| `PR-HF-17` (ES green) | `curl ES/_cluster/health \| jq .status == green` | L4 | health-check |
| `PR-HF-18` (retention) | `tctl namespace describe \| grep Retention.*168h` | L4 | new namespace-validate job |
| `PR-HF-19` (dashboards size) | `find -name '*-grafana-dashboard.yaml' -size +800k \| wc -l == 0` | L1 | pre-commit + CI |
| `PR-HF-20` (sidecar cleanup) | `[ ! -f cassandra-exporter-sidecar-fix.yaml ]` | L1 | CI script |
| `PR-HF-21` (gc_grace) | `cqlsh DESCRIBE TABLE \| grep gc_grace_seconds 259200` | L4 | new cassandra-config-validate job |
| `PR-HF-22` (Cassandra alert) | `kubectl get prometheusrule cassandra-rules` | L4 | apply-and-verify hook |

**Outcome:** every HF acceptance has a test layer + a runner. No hand-waved acceptance.

---

## 8. PR-quality patches for testing infrastructure

Each PR-T-NN below follows the same shape as the HF series in `04_PR_BREAKDOWN.md`: stable ID, branch suggestion, files touched, unified diff, acceptance, rollback, depends-on, risk-of-being-wrong.

### `PR-T-01` — Add bitbucket-pipelines.yml with L1+L2+L3 stages

- **Branch:** `ci/helmfile-bitbucket-pipelines`
- **Files touched:** new `atlassian_packages/gcp_kitt/bitbucket-pipelines.yml` (~140 lines), new `helmfile/.pre-commit-config.yaml` (~30 lines)
- **LoC budget:** +170
- **Depends-on:** none
- **Severity gap:** G1
- **Closes layers:** L1, L2, L3

**Patch — `bitbucket-pipelines.yml` skeleton (place at gcp_kitt root):**
```yaml
image: atlassian/default-image:4

definitions:
  caches:
    gomod: $HOME/go/pkg/mod

pipelines:
  pull-requests:
    '**':
      - parallel:
          - step:
              name: L1 — lint (YAML / shell / Dockerfile / k8s)
              script:
                - cd atlassian_packages/gcp_kitt/helmfile
                - pip install --quiet yamllint pre-commit
                - yamllint -c .yamllint.yaml .
                - find . -name '*.sh' -print0 | xargs -0 shellcheck
                - find . -name 'Dockerfile*' -print0 | xargs -0 -n1 hadolint --no-fail
                - kube-linter lint --do-not-auto-add-defaults . || true
                - polaris audit --audit-path . --format=score
          - step:
              name: L2 — unit (Go + Python)
              caches: [gomod]
              script:
                - cd atlassian_packages/gcp_kitt/helmfile/dte
                - go mod download
                - go vet ./...
                - go test -race -coverprofile=coverage.out ./...
                - go tool cover -func=coverage.out | tail -1
                - awk '/total:/ { if ($3+0 < 40.0) { print "FAIL: coverage "$3" < 40%"; exit 1 } }' coverage.out
                - cd ../python-app
                - pip install --quiet pytest requests-mock boto3
                - pytest -q
          - step:
              name: L3 — contract (helmfile/helm/kubeval/conftest)
              script:
                - curl -fsSL https://github.com/helmfile/helmfile/releases/download/v0.169.0/helmfile_0.169.0_linux_amd64.tar.gz | tar -C /usr/local/bin -xz helmfile
                - cd atlassian_packages/gcp_kitt/helmfile
                - helmfile lint --skip-deps
                - helmfile template --skip-deps | kubeval --strict --ignore-missing-schemas
                - conftest test --policy policy *-job.yaml helmfile.yaml
```

**Acceptance:**
```bash
# After merge, push a PR and verify all 3 stages pass:
git push
# Bitbucket UI: pipeline shows 3 green steps (L1, L2, L3); ~5 min total.
```

**Rollback:** `git revert <sha>` removes the file; pipeline becomes a no-op.

**Risk-of-being-wrong:** MED. helmfile/helm/kubeval/conftest binary versions may pin-drift; use the explicit version pins shown in the script. **Pre-merge:** run each `script:` block locally first.

---

### `PR-T-02` — Fix `dte/Makefile:test` glob; run all 70 Go tests

- **Branch:** `chore/dte-makefile-fix-test-glob`
- **Files touched:** `dte/Makefile` (~5 lines)
- **LoC budget:** ±5
- **Depends-on:** none
- **Severity gap:** G2
- **Closes layer:** L2

**Patch:**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/dte/Makefile
+++ b/atlassian_packages/gcp_kitt/helmfile/dte/Makefile
 .PHONY: test
 test: ## Run tests
 	@echo "Running tests..."
-	go test ./pkg/... ./cmd/... || echo "No tests found or tests failed"
+	go test -race -coverprofile=coverage.out ./...
+	@go tool cover -func=coverage.out | tail -1
 .PHONY: test-verbose
 test-verbose: ## Run tests with verbose output
 	@echo "Running tests with verbose output..."
-	go test -v ./pkg/... ./cmd/...
+	go test -race -v ./...
```
The key changes: drop the bogus `./cmd/...` glob, use `./...` (which catches `distributed-worker/`, `distributed-client/`, `pkg/...`), enable `-race`, generate coverage, and **stop swallowing failures** (`|| echo` → removed).

**Acceptance:** `cd dte && make test 2>&1 | grep -cE '^(=== RUN|--- (PASS|FAIL))' >= 70`.

**Rollback:** `git revert <sha>`.

**Risk-of-being-wrong:** LOW. `-race` may surface real data-race bugs (good). If race-detector flakes a specific test, that's information, not a regression.

---

### `PR-T-03` — Coverage gate (≥40% on dte/) + report upload

- **Branch:** `ci/dte-coverage-gate`
- **Files touched:** `dte/Makefile` (small extension), `bitbucket-pipelines.yml` (1 step)
- **LoC budget:** +20
- **Depends-on:** `PR-T-01`, `PR-T-02`
- **Severity gap:** G3
- **Closes layer:** L2

**Patch:** see L2 step in PR-T-01 (the `awk '/total:/ ...'` line). Plus a `make coverage-report` target that emits `coverage.html` for human review.

**Acceptance:** CI shows coverage % each run; PR fails when < 40 % (initial bar) — raise to 60 % after a quarter.

**Rollback:** drop the `awk` gate.

**Risk-of-being-wrong:** LOW. Threshold is calibrated to existing reality (we don't actually know the % yet — first run sets the baseline; if higher than 40, raise the bar).

---

### `PR-T-04` — Audit and tighten vacuous Go assertions

- **Branch:** `chore/dte-tighten-test-assertions`
- **Files touched:** `dte/distributed-worker/*_test.go`, `dte/pkg/logger/logger_test.go`
- **LoC budget:** +50, ±100
- **Depends-on:** `PR-T-02`
- **Severity gap:** G4
- **Closes layer:** L2

**Approach:**
1. Run audit grep: `grep -nE 'assert\.NotNil\([^,]+\)\s*$|require\.NotNil\([^,]+\)\s*$' dte/...` — list every test that **only** asserts non-nil.
2. For each, add at least one structural assertion (e.g., `assert.Equal(t, expected, result.Status)`).
3. Convert any obvious table-amenable test into a `tests := []struct{ name string ... }{ ... }` block.

**Acceptance:** number of `NotNil`-only test bodies (per the audit grep) drops by ≥ 80 %.

**Rollback:** `git revert <sha>`.

**Risk-of-being-wrong:** MED. Tightened assertions may reveal latent bugs; that's the point. Each new test failure is a **finding**, not a regression of this PR.

---

### `PR-T-05` — Convert `python-app/test_api.py` to pytest with assertions + mocks

- **Branch:** `chore/python-app-pytest`
- **Files touched:** rewrite `python-app/test_api.py` (~150 lines), delete or quarantine `python-app/test.py`, update `python-app/Makefile`
- **LoC budget:** ±200
- **Depends-on:** none
- **Severity gap:** G5
- **Closes layer:** L2

**Approach:** introduce `pytest` + `requests-mock`. Each existing diagnostic call becomes a real assertion (`response.status_code == 200`, JSON shape, etc.) against a mocked `localhost:5000`. Move `test.py` (AWS IMDS smoke) to `scripts/aws-imds-debug.py` and stop calling it "test".

**Acceptance:** `cd python-app && pytest -q` shows ≥ 5 PASS, 0 FAIL; `python-app/test.py` no longer exists at top level.

**Rollback:** `git revert <sha>`.

**Risk-of-being-wrong:** LOW. Mocked tests can't regress production; they only protect future refactors.

---

### `PR-T-06` — Helmfile / Helm / kubeval / kube-linter / polaris in CI

- **Branch:** `ci/helmfile-manifest-validation`
- **Files touched:** part of `bitbucket-pipelines.yml` (already in PR-T-01); add `helmfile/.kube-linter.yaml`, `helmfile/.polaris.yaml` config files
- **LoC budget:** +60 (configs)
- **Depends-on:** `PR-T-01`
- **Severity gap:** G6
- **Closes layer:** L3

**Approach:** ship config files that suppress known acceptable findings (e.g., HF-04's intentional removal of CPU limits) so the CI is signal not noise.

**Acceptance:** `kube-linter lint . --do-not-auto-add-defaults --config .kube-linter.yaml` exits 0; `polaris audit --score >= 80`.

**Rollback:** drop the L3 step from CI.

**Risk-of-being-wrong:** MED. Strict polaris/kube-linter will flag real legacy issues. Pre-baseline by accepting all current violations as "known"; gate fails only on **new** violations.

---

### `PR-T-07` — Conftest / OPA policy tests for HF-13 / HF-15 / HF-05

- **Branch:** `ci/conftest-policy-tests`
- **Files touched:** new `helmfile/policy/*.rego` (~80 lines), CI step
- **LoC budget:** +80
- **Depends-on:** `PR-T-01`
- **Severity gap:** G7
- **Closes layer:** L3

**Patch — `helmfile/policy/no_latest_tag.rego`:**
```rego
package main
deny[msg] {
  input.kind == "Job"
  container := input.spec.template.spec.containers[_]
  endswith(container.image, ":latest")
  msg := sprintf("Container %s uses :latest tag (HF-13)", [container.name])
}
```

**Patch — `helmfile/policy/no_plaintext_password.rego`:**
```rego
package main
deny[msg] {
  walk(input, [path, value])
  is_string(path[count(path)-1])
  contains(lower(path[count(path)-1]), "password")
  is_string(value)
  count(value) >= 6
  not startswith(value, "$(")  # allow env-var refs
  msg := sprintf("Plaintext password at %v (HF-05)", [path])
}
```

**Patch — `helmfile/policy/jmx_must_authenticate.rego`** for HF-15.

**Acceptance:** `conftest test --policy helmfile/policy helmfile/*-job.yaml helmfile/helmfile.yaml` exits 0 after HF-05/HF-13/HF-15 land; **before** they land it returns the matching `deny` messages.

**Rollback:** drop the L3 conftest step or the specific `.rego` file.

**Risk-of-being-wrong:** MED. Rego false-positives are common; **add `# OPA-EXEMPT:` annotations** as escape hatches with rationale.

---

### `PR-T-08` — Replace KEDA TCP test with gRPC health-check probe

- **Branch:** `fix/keda-test-actual-grpc`
- **Files touched:** `test-keda-temporal-connectivity-job.yaml`
- **LoC budget:** ~20
- **Depends-on:** none (parallel with PR-HF-10)
- **Severity gap:** G8
- **Closes layer:** L4

**Patch:** swap `curlimages/curl:latest` (TCP-only) for `fullstorydev/grpcurl:v1.9.1` and call `grpc.health.v1.Health/Check`:
```diff
-        image: curlimages/curl:latest
+        image: fullstorydev/grpcurl:v1.9.1-alpine
         command:
           - /bin/sh
           - -c
           - |
-            nc -zv temporal-frontend.temporal.svc.cluster.local 7233
+            grpcurl -plaintext temporal-frontend.temporal.svc.cluster.local:7233 \
+              grpc.health.v1.Health/Check
+            # Exit non-zero if SERVING is not in the response:
+            grpcurl -plaintext temporal-frontend.temporal.svc.cluster.local:7233 \
+              grpc.health.v1.Health/Check | grep -q '"status": "SERVING"'
```

**Acceptance:** the job's pod logs show `{"status": "SERVING"}` and exit 0 in healthy state; deliberately blocking gRPC (e.g., NetworkPolicy block) makes it exit 1.

**Rollback:** `git revert <sha>` restores the TCP-only test.

**Risk-of-being-wrong:** LOW. `grpcurl` is the canonical gRPC client; image is small.

---

### `PR-T-09` — Wire `temporal-health-check.sh` as scheduled CronJob + postsync hook

- **Branch:** `obs/temporal-health-cronjob`
- **Files touched:** new `helmfile/temporal-health-cronjob.yaml` (~70 lines), `helmfile.yaml` (1 hook + dockerized image of the script)
- **LoC budget:** +90
- **Depends-on:** `PR-HF-14` (apply-and-verify)
- **Severity gap:** G9
- **Closes layer:** L4

**Approach:** package the script + `kubectl` + `grpcurl` into a small image (`temporal-tools` already exists per `Dockerfile.temporal-tools`). Run as `CronJob` every 5 min; first run also wired as helmfile postsync to gate `helmfile apply`.

**Acceptance:** `kubectl get cronjob temporal-health -n temporal -o jsonpath='{.status.lastScheduleTime}'` updates within 5 min; failed run sends `kubectl get event -n temporal --field-selector reason=BackoffLimitExceeded`.

**Rollback:** `kubectl delete cronjob temporal-health -n temporal`.

**Risk-of-being-wrong:** LOW; script already TRUTHFUL-class.

---

### `PR-T-10` — KEDA scaling validation (synthetic load → assert HPA scaled)

- **Branch:** `test/keda-scaling-validation-job`
- **Files touched:** new `test-keda-scaling-validation-job.yaml` (~80 lines)
- **LoC budget:** +80
- **Depends-on:** `PR-HF-10` (KEDA fixed)
- **Severity gap:** G10
- **Closes layer:** L4

**Approach:** Job that submits 200 workflows to the scraper task queue, sleeps 90 s, then asserts `kubectl get hpa keda-hpa-scraper-worker-scaler -o jsonpath='{.status.currentReplicas}' >= 2`.

**Acceptance:** Job exits 0 in healthy state; deliberate KEDA mis-config makes it exit 1.

**Rollback:** delete the Job manifest.

**Risk-of-being-wrong:** MED. Synthetic load on prod is risky; **only run against canary cluster**, gated by a label selector.

---

### `PR-T-11` — Delete `dte/distributed-worker.test`; add `.gitignore`

- **Branch:** `chore/remove-stale-test-binary`
- **Files touched:** `git rm dte/distributed-worker.test`, append `.gitignore`
- **LoC budget:** −1 binary, +3 lines
- **Depends-on:** none
- **Severity gap:** G11
- **Closes layer:** L1

**Patch:**
```bash
cd atlassian_packages/gcp_kitt/helmfile
git rm dte/distributed-worker.test
cat >> .gitignore <<'EOF'
# Compiled Go test binaries
*.test
**/distributed-worker
**/distributed-client
**/bin/
EOF
```

**Acceptance:** `git ls-files | grep -E '\.test$' | wc -l == 0`; repo size shrinks by ~76 MB.

**Rollback:** N/A (cleanup).

**Risk-of-being-wrong:** LOW. Binary is unreferenced.

---

### `PR-T-12` — CI lint: `test-*` jobs must contain assertions; setup-jobs renamed

- **Branch:** `chore/rename-misnamed-test-jobs`
- **Files touched:** rename ~4 setup jobs out of `test-*` namespace; new `helmfile/.test-name-lint.sh`; CI hook
- **LoC budget:** ±20
- **Depends-on:** `PR-T-01`
- **Severity gap:** G12
- **Closes layer:** L1

**Approach:**
1. Rename `temporal-namespace-register-job.yaml`, `temporal-keyspace-setup-job.yaml`, `temporal-schema-setup-job.yaml`, `setup-temporal-schema-job.yaml`, `create-default-namespace-job.yaml` → already correctly prefixed `setup-*` / `temporal-*-setup-*` (most are fine; verify).
2. Add `.test-name-lint.sh` to assert: every `test-*-job.yaml` contains at least one `assert\|fail\|exit 1\|grep -q` in its `command:` or `args:`.

**Patch — `.test-name-lint.sh`:**
```bash
#!/bin/bash
set -euo pipefail
status=0
for f in atlassian_packages/gcp_kitt/helmfile/test-*-job.yaml; do
  if ! grep -qE 'assert|fail|exit 1|grep -q' "$f"; then
    echo "FAIL: $f is named test-* but contains no assertion"; status=1
  fi
done
exit $status
```

**Acceptance:** script exits 0 on every PR.

**Rollback:** `git revert <sha>`.

**Risk-of-being-wrong:** LOW.

---

## 9. T2/T3 backlog — chaos drills (PR-T-13/14/15)

These are sketched, not fully patched, because they require the rest of the plan to land first. The shape is:

- **`PR-T-13` PDB-drain + probe-restart-loop** — bash CronJob (weekly) that `kubectl drain`s a worker node and asserts no Temporal frontend pod exited; second job injects a 30-min `time.Sleep` activity and asserts no probe-induced restart.
- **`PR-T-14` Secret-rotation drill** — bash CronJob (monthly) that rotates `temporal-postgres-secret`, verifies pods restart in rolling order, and asserts no failed transactions during the window.
- **`PR-T-15` Upgrade/rollback drill** — bash CronJob (per-release) that bumps Temporal chart minor version, runs synthetic workflow, then `helm rollback` and asserts metric ≥ pre-baseline.

Each becomes a full PR-T-NN entry once the T0/T1 foundation is in place. Tracked in `02_FINDINGS_CATALOG.md` as future work.

---

## 10. Sequencing & integration with `04_PR_BREAKDOWN.md`

Insert testing PRs in this order, interleaved with HF PRs already in `04_PR_BREAKDOWN.md`:

| Day | What ships | Why interleaved here |
|---|---|---|
| 1 | `PR-T-11` (delete stale binary) + `PR-HF-06` (creds.json) | Both are git-removal items; do them together |
| 2 | `PR-T-02` (fix glob) + `PR-T-09` (wire health-check) | Get the existing tests actually running before adding more |
| 3 | T0 HF PRs (HF-07/05/01/03/02) | Ship the structural fixes; PR-T-09 health-check now validates them |
| 4 | `PR-T-01` (CI pipeline) + `PR-T-06` (manifest validation in CI) | Once the cluster is healthy, CI gates further changes |
| 5 | `PR-T-03` (coverage gate) + `PR-T-12` (test-name lint) | Quality bars |
| 6 | `PR-T-08` (KEDA gRPC test) + HF-10 (KEDA fix) | Pair the test with the fix it's covering |
| 7 | `PR-T-07` (conftest policies) | Codify the rules from HF-04/HF-13/HF-15 |
| 8 | `PR-T-04` (tighten Go assertions) | Now that CI runs them, make them mean more |
| 9 | `PR-T-05` (pytest for python-app) | Mirror Go quality for Python |
| 10 | `PR-T-10` (KEDA scaling validation) | Needs HF-10 + PR-T-08 already landed |

Total: **+10 testing PRs** sandwiched into the existing 22-PR helmfile plan. Net additional wall-clock: ~3 working days when interleaved (most PRs are < 100 LoC).

---

## 11. Per-PR-T risk register

| PR-T | Likelihood of regression | Impact | Mitigation |
|---|---|---|---|
| PR-T-01 | MED | LOW (CI failure blocks no prod) | run each step locally first |
| PR-T-02 | MED | MED (race detector may flake) | accept first run as baseline; re-run flaky tests with `-count=10` |
| PR-T-03 | LOW | LOW | calibrate threshold from baseline |
| PR-T-04 | MED | MED (will surface latent bugs) | each surfaced bug is a separate ticket; don't block PR-T-04 on fixes |
| PR-T-05 | LOW | LOW | mocked tests cannot regress prod |
| PR-T-06 | MED | LOW | baseline known-violations |
| PR-T-07 | MED | LOW | exempt list with rationale |
| PR-T-08 | LOW | LOW | grpcurl is canonical |
| PR-T-09 | LOW | LOW | script is TRUTHFUL today |
| PR-T-10 | MED | MED (synthetic load on cluster) | canary-only via label selector |
| PR-T-11 | LOW | LOW (binary unreferenced) | n/a |
| PR-T-12 | LOW | LOW | rename if false positive |

---

## 12. "Done" definition

This testing strategy is considered DONE when:

1. ✅ All 17 verified gaps documented (done — §5).
2. ✅ All 12 PR-T-NN sketched with diff/acceptance/rollback (done — §8/9).
3. ✅ All 22 HF acceptance commands mapped to a layer + runner (done — §7).
4. ✅ Truthfulness classification applied to every existing test/script (done — §4).
5. ⏳ PR-T-01 + PR-T-02 + PR-T-09 + PR-T-11 merged → "minimal viable test fabric" online; CI pipeline runs L1+L2+L3 on every PR.
6. ⏳ All HF-PRs that ship after `PR-T-01` MUST include a CI-passing run (no exceptions).
7. ⏳ Weekly (T0+T1 phase): `make test` exit code recorded in oncall channel; PR-T-09 CronJob results recorded in Grafana.

When items 5-7 are checked, the helmfile package has parity with the parent plan family's "machine-followable" standard.

---

## 13. Cross-references

- `00_README.md` — gets a new pointer to this file (added in step 13 below).
- `04_PR_BREAKDOWN.md` — every HF acceptance now has a layer assignment in §7 here.
- `05_RISK_AND_VALIDATION.md` — PR-T-NN risk register in §11 here mirrors the HF format.
- `KEDA_TEMPORAL_CONNECTION_ISSUE.md` — closed by PR-HF-10 + PR-T-08 working together.
- `temporal-health-check.sh` — verified TRUTHFUL; promoted to first-class CronJob in PR-T-09.
