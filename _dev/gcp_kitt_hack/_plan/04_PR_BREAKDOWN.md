# PR Breakdown

> Every plan item is decomposed into **one or more reviewable PRs**. Each PR has:
> - **Stable ID** (machine-readable)
> - **Branch suggestion**
> - **Files touched** (with rough LoC budget)
> - **Acceptance criterion** (a metric movement or test)
> - **Depends-on** (PR-level dependencies)
>
> **Rule of thumb**: no PR > ~600 LoC change unless it's a pure file move + import-rewrite.
> All multi-PR refactors go in **add-then-cutover-then-remove** order, never simultaneous.

---

## Phase 0 — Observability + drift fence

### `PR-PHASE0-01` Add Prom metrics + `/metrics` to DTE worker (amp + helmfile copies)
- Branch: `chore/dte-worker-metrics`
- Files: `amp/distributed-worker/main.go`, `helmfile/dte/distributed-worker/main.go`, new `pkg/metrics/metrics.go` (or per-binary if no shared module yet)
- LoC: ~200
- Adds histograms: `dte_activity_duration_seconds`, `dte_auth_token_exchange_seconds`, `dte_k8s_api_call_seconds`; counters: `dte_auth_token_cache_total{result}`, `dte_activity_total{result}`.
- Acceptance: `curl localhost:9090/metrics | grep dte_` returns the histograms in dev.
- Depends-on: none

### `PR-PHASE0-02` Add Prom metrics to kitt-runbooks worker
- Branch: `chore/runbooks-worker-metrics`
- Files: `kitt-runbooks/cmd/worker/main.go`, `kitt-runbooks/pkg/logger/`, new `kitt-runbooks/internal/metrics/`
- LoC: ~150
- Histograms: `runbook_activity_duration_seconds{activity}`, `runbook_k8s_client_create_seconds`.

### `PR-PHASE0-03` Scraper: add Prom histograms (Python + JS)
- Branch: `chore/scraper-histograms`
- Files: `scraper/temporal-pg-redis/src/metrics.py`, `src-js/metrics.js`
- LoC: ~80
- Buckets `[0.1,0.5,1,5,30,300]` per activity.

### `PR-PHASE0-04` CI drift-fence amp ↔ helmfile/dte
- Branch: `ci/dte-drift-fence`
- Files: `bitbucket-pipelines.yml` (root or per-component) + `scripts/check-dte-drift.sh`
- LoC: ~40
- Fails build if `diff -q amp/distributed-worker/{main,helpers,cluster_db}.go helmfile/dte/distributed-worker/...` returns differences AND `DTE_DIVERGENCE_OK` marker file is absent.

---

## Phase 0.5 — STABILITY EPIC (P0-S) — NEW, added 2026-05-08

> Each PR below corresponds 1:1 with a finding in `07_STABILITY_PLAN.md` (S1–S15). All fixes are **elegant, idiomatic** — no probe-loosening, no try/except-pass, no hardcoded retries.
> **ID prefix `PR-STAB-*`** is used to avoid collision with the existing scraper PRs (`PR-S1..S4`) below.
> **Total budget**: ~8 working days, 15 small PRs, each independently reviewable in <30 min.
> **Sequencing**: see `07_STABILITY_PLAN.md` §"Rollout sequence" — 1–2 PRs/day.

### `PR-STAB-01` Remove `log.Fatal` from k8s-metadata-collector collection loop (S1)
- **Branch:** `fix/metadata-collector-no-fatal-in-loop`
- **Files:** `k8s-metadata-collector/main.go` (lines 122–303 — `GetPodsAndNodes`, `getServiceAccounts`, `collectAndSendMetadata`); new `k8s-metadata-collector/metrics.go`.
- **LoC:** ~120
- **Change:** `GetPodsAndNodes` and `getServiceAccounts` return `error` instead of fataling; `collectAndSendMetadata` wraps each iteration in a fallible op + `cenkalti/backoff/v4` exponential backoff (cap 30 s) + new `kitt_metadata_collect_errors_total{op}` counter; `log.Fatalf` reserved strictly for **startup** misconfiguration. Health endpoint goes red after `≥ 3 × interval` of all-failure.
- **Acceptance:** chaos-test injects 503 from fake apiserver → no `os.Exit`; pod restart-count from this binary → 0 in staging week.
- **Depends-on:** PR-PHASE0-01 (metrics scaffolding).
- **Tightens existing PR-B1** — replaces it (PR-B1 was log-only; this adds backoff + observability + health-degradation as part of the same change).

### `PR-STAB-02` Surface kitt-runbooks worker `w.Run()` failure (S2)
- **Branch:** `fix/runbooks-worker-no-silent-death`
- **Files:** `kitt-runbooks/cmd/worker/main.go` (lines 105–109 + main wait-loop); add Prom counter `runbook_worker_run_loop_terminations_total`.
- **LoC:** ~80
- **Change:** Worker goroutine writes its terminal error to a buffered `chan error`; main `select` includes `case err := <-workerErr` → `os.Exit(1)` so kubelet restarts. `/healthz` reflects worker liveness, not just HTTP. New PagerDuty alert on `runbook_worker_run_loop_terminations_total > 0`.
- **Acceptance:** unit test that closes Temporal connection mid-flight → process exits non-zero (currently: stays alive forever returning 200).
- **Depends-on:** none.

### `PR-STAB-03` Add proper liveness/readiness/preStop/grace to kitt-runbooks worker (S3)
- **Branch:** `infra/runbooks-worker-probes`
- **Files:** `kitt-runbooks/worker-values.yaml` (entire file currently has *no* probes/preStop/grace); `kitt-runbooks/cmd/worker/main.go` (add `/livez` and `/readyz` HTTP handlers).
- **LoC:** ~60 (Go) + ~25 yaml
- **Change:** Add `livenessProbe` (`/livez`, `failureThreshold: 3`, `45 s` total tolerance), `readinessProbe` (`/readyz` checking worker-registered + temporal-connected), `terminationGracePeriodSeconds: 120` (≥ longest activity StartToCloseTimeout — **hard correctness rule**), `lifecycle.preStop` `sleep 15 && kill -TERM 1`. `/livez` is shallow (atomic-flag check); `/readyz` is deep.
- **Acceptance:** k8s e2e test: deploy → curl probes → SIGTERM → assert no in-flight activity dropped (Temporal sees graceful drain).
- **Depends-on:** PR-STAB-02 (so liveness exit isn't masked by silent worker death).
- **Risk note:** **Canary on one cluster for ≥ 48 h** before global rollout — see Risk R-S3 in `05_RISK_AND_HISTORY.md`.

### `PR-STAB-04` DTE distributed-worker: don't `os.Exit(1)` from HTTP goroutine (S4)
- **Branch:** `fix/dte-worker-graceful-http-shutdown`
- **Files:** `amp/distributed-worker/main.go` (lines 791–794 + spinup); mirror in `helmfile/dte/distributed-worker/main.go`.
- **LoC:** ~120 across both copies (single copy if A1 consolidation lands first).
- **Change:** Wrap HTTP listener in `*http.Server`; surface bind/serve error via `chan error`; main goroutine `select`s on `sigCh`, `workerCh`, `httpCh`; orchestrates `srv.Shutdown(ctx)` with 30 s deadline. New `dte_worker_shutdown_reason_total{reason}` counter.
- **Acceptance:** integration test: occupy `:8080` first → assert clean structured-error shutdown, not `os.Exit`.
- **Depends-on:** none (can land in parallel with A1 consolidation; Phase-0 CI fence ensures both copies stay in sync).

### `PR-STAB-05` iam-sidecar: never `log.Fatal` in `ServeHTTP` + IMDS retries (S5)
- **Branch:** `fix/iam-sidecar-no-fatal-in-handler`
- **Files:** `iam-sidecar/iam-sidecar.go` (lines 159–160 marshal Fatal; lines 207–326 cloud-provider detection).
- **LoC:** ~50
- **Change:** `json.Marshal` failure → `http.Error(w, "internal error", 500)` + `iam_sidecar_marshal_errors_total` counter. `isAWS()`/`isGCE()`: 3 retries with exponential backoff (1s/2s/4s) before fatal; structured error log on each attempt.
- **Acceptance:** unit test with deliberately-unmarshalable struct → HTTP 500, sidecar alive; e2e with mocked slow IMDS (3s) → success after retry.
- **Depends-on:** none.
- **Retracts** the §05 risk-register item that previously declared "iam-sidecar is solid" — that judgement was wrong; this `ServeHTTP` Fatal was missed in §02-D12.

### `PR-STAB-06` ASI: replace `panic(err)` and `log.Fatalf` in business code (S6)
- **Branch:** `fix/asi-no-panic-in-business-code`
- **Files:** `asi/cmd/main.go` (lines 259, 263, 267, 299, 310, 315); `asi/internal/asicore/asi.go` (lines 105, 111).
- **LoC:** ~150
- **Change:** Refactor `cmd/main.go` to a `run() error` helper; each `panic(err)` becomes `return fmt.Errorf("init X: %w", err)`. `asicore.NewRealService` returns `(*RealIAMService, error)`. `main` becomes `if err := run(); err != nil { log.Error(err); os.Exit(1) }` with **clear, actionable** error messages so `kubectl describe pod` shows the cause.
- **Acceptance:** inject GCP IAM construction failure → clean shutdown with helpful log line (currently: stack trace + crash).
- **Risk:** MED (touches initialization order). Add unit test for `run()` error path.

### `PR-STAB-07` ForgeApp: nil-deref guard on `*deployment.Spec.Replicas` (S7)
- **Branch:** `fix/forgeapp-replicas-nil-guard`
- **Files:** `forge_containers/controllers/forgeapp_controller.go` (lines 261, 291–298); add controller-runtime middleware for `forgeapp_reconcile_panics_total{controller}`.
- **LoC:** ~40 + middleware
- **Change:** `desired := int32(1); if deployment.Spec.Replicas != nil { desired = *deployment.Spec.Replicas }` before any comparison. Middleware emits a metric so future panic-classes are *seen*, not absorbed.
- **Acceptance:** unit test with `Deployment{Spec.Replicas: nil}` → no panic.

### `PR-STAB-08` ForgeApp: replace `time.Sleep` in `ensureNamespace` Reconcile (S8)
- **Branch:** `fix/forgeapp-no-sleep-in-reconcile`
- **Files:** `forge_containers/controllers/forgeapp_controller.go` (lines 604–628).
- **LoC:** ~40
- **Change:** Each `time.Sleep(time.Second)` → `return ctrl.Result{RequeueAfter: 1 * time.Second}, nil`. Reconcile re-enters cleanly when namespace status flips. (Textbook controller-runtime fix.)
- **Acceptance:** race-test simulating slow namespace activation → workqueue depth stays <10 (currently: blocks reconciler thread for 3 s × N items).
- **Depends-on:** none.
- **Promoted from §02-D7** (was P2 perf nit; **promoted to P0-S** because it's a stability blocker — leader-election lease is lost under load).

### `PR-STAB-09` Scraper: graceful shutdown on SIGTERM + preStop (S9)
- **Branch:** `fix/scraper-graceful-shutdown`
- **Files:** `scraper/temporal-pg-redis/src/worker.py` main entrypoint; `charts/scraper-worker/templates/deployment.yaml`.
- **LoC:** ~80
- **Change:** `loop.add_signal_handler(SIGTERM, …)`; on signal, `await worker.shutdown(graceful_shutdown_timeout=timedelta(seconds=60))` then `await worker_task`. Chart: `terminationGracePeriodSeconds: 120` + `preStop: sleep 10` (lets endpoints depopulate).
- **Acceptance:** SIGTERM mid-activity → activity completes cleanly (Temporal sees normal close, not `ActivityFailed`).
- **Depends-on:** none.

### `PR-STAB-10` Scraper: bounded aiohttp session + per-request timeout (S10)
- **Branch:** `fix/scraper-aiohttp-lifetime-and-timeout`
- **Files:** `scraper/temporal-pg-redis/src/worker.py` (lines 311–324 and 581).
- **LoC:** ~100
- **Change:** Single module-level `aiohttp.ClientSession` created in worker startup, closed on shutdown; **every** request uses `aiohttp.ClientTimeout(total=30, connect=10, sock_connect=5, sock_read=20)`. `requests` calls use `timeout=(connect, read)` tuple.
- **Acceptance:** slow-server fixture → request fails fast (≤30s) with structured error, not 5min worker-slot hang.
- **Strengthens existing §02-B7** (was P2; **promoted to P0-S** as part of crash-reduction).

### `PR-STAB-11` Scraper: bounded retries + poison-pill circuit breaker (S11)
- **Branch:** `fix/scraper-retry-policy-and-circuit`
- **Files:** `scraper/temporal-pg-redis/src/workflow.py` (lines 125–180 — `get_retry_policy`).
- **LoC:** ~120
- **Change:** `maximum_attempts=5` for transient classes; `non_retryable_error_types=["ValueError", "InvalidURL", ...]` for permanent. Workflow-level circuit: if a job's failure rate >50 % over last 100 activities, suspend that job + emit `scraper_job_circuit_open_total{job_id}`.
- **Acceptance:** unit test with poison-pill activity → workflow stops retrying after 5 attempts (currently: forever).
- **Risk:** MED (must classify error types correctly). Tests cover each error class.

### `PR-STAB-12` Splunk client: 60s → 10s + circuit breaker (S12)
- **Branch:** `fix/splunk-client-timeout-and-circuit`
- **Files:** `kitt-runbooks/internal/splunk/client.go` (line ~55).
- **LoC:** ~80
- **Change:** `HTTPClient.Timeout: 10 * time.Second` (env-overridable via `SPLUNK_TIMEOUT_SECONDS`); wrap with `sony/gobreaker` circuit (5 consecutive failures → open 30 s); `splunk_circuit_state{state}` gauge.
- **Acceptance:** mock 60s Splunk → activity fails in ~10s; after 5 such, circuit opens; subsequent calls fail immediately without RPC.
- **Promoted from §02-C9** (was P2 timeout-only; **promoted to P0-S and extended with circuit breaker** because 6 slow Splunk queries × 60 s starves all 10 worker slots → liveness probe times out → pod restart cascade).

### `PR-STAB-13` Temporal worker connect: backoff cap + jitter + fail-loud (S13)
- **Branch:** `fix/runbooks-temporal-connect-backoff`
- **Files:** `kitt-runbooks/cmd/worker/main.go` (lines 65–82 — the loop touched by `1b1c279`).
- **LoC:** ~60
- **Change:** Replace linear `5s+5s+...+60s` with `cenkalti/backoff/v4` exponential + jitter; `MaxElapsedTime = 5 min`, `MaxInterval = 30 s`. After max-elapsed, `os.Exit(1)` so kubelet's pod-level restart-policy applies. New `runbook_temporal_connect_attempts_total{result}` counter.
- **Acceptance:** mock Temporal as unreachable for 7 min → worker exits cleanly after 5 min, kubelet restarts; no thunder-herd reconnect.
- **Builds on** the recent fix `1b1c279` (port flip 7243→7233); does not conflict.

### `PR-STAB-14` Replace TLS `InsecureSkipVerify` with proper CA bundle (S14)
- **Branch:** `fix/runbooks-tls-proper-ca`
- **Files:** `kitt-runbooks/cmd/worker/main.go` (lines 46–58 TLS detection); whatever sets `InsecureSkipVerify` in DTE worker (`amp/distributed-worker/main.go`).
- **LoC:** ~80
- **Change:** Load CA from `/var/run/secrets/kubernetes.io/serviceaccount/ca.crt`; configure `tls.Config{RootCAs: pool, ServerName: hostname}`; **never** `InsecureSkipVerify`. For externally-signed certs, mount via `Secret`. Add startup-time TLS handshake test.
- **Acceptance:** rotate Temporal cert in dev → worker connects without code change.
- **Risk:** MED (TLS bugs hard to debug). **Must canary** for ≥48 h; coordinate with team that landed `1b1c279`. Roll-back plan = revert single commit + reset `InsecureSkipVerify` flag.

### `PR-STAB-15` Scraper probe realignment: cheap `/livez`, deep `/readyz`, correct grace (S15)
- **Branch:** `infra/scraper-probe-realignment`
- **Files:** `scraper/temporal-pg-redis/values/worker.yaml` (lines 177–184 — comments document progressive loosening); `charts/scraper-worker/templates/deployment.yaml` (lines 144–159); add `/livez` `/readyz` to `worker.py`.
- **LoC:** ~80 + helm
- **Change:** `/livez` returns 200 if process alive (atomic flag, <10 ms even at full load). `/readyz` returns 200 only if `worker.is_running() and temporal.is_connected() and db.is_connected() and redis.is_connected()`. `terminationGracePeriodSeconds = max(activity_timeout) ≈ 360 s` (URL_TIMEOUT 5 min + 60 s buffer). `preStop: sleep 10`. **Roll back loosened probe timeouts to defaults** once `/livez` is properly cheap.
- **Acceptance:** load-test full activity load + parallel `/livez` curl → p99 ≤ 10 ms.
- **Risk:** MED — current probes are calibrated to current behaviour; needs canary. **Hard prerequisite:** PR-STAB-09 (SIGTERM handler) and PR-STAB-10 (aiohttp timeout) must land first, otherwise tightening probes will trigger restarts.

---

## Phase 1 — P0 EPIC bundles

### EPIC P0-A : DTE auth-path

#### `PR-A1` Reusable HTTP clients (no functional change)
- Branch: `perf/dte-http-client-pool`
- Files: `amp/distributed-worker/helpers.go`, `cluster_db.go`; mirror in `helmfile/dte/`
- LoC: ~120
- Replace `&http.Client{Timeout:...}` per-call with package-level singletons configured `MaxIdleConnsPerHost: 32, IdleConnTimeout: 90s`.
- Acceptance: `dte_auth_token_exchange_seconds` p95 ↓ ≥ 30 % within 24 h on canary pod.
- Depends-on: PR-PHASE0-01

#### `PR-A2` In-memory token cache keyed by (cluster, groups, issuer)
- Branch: `perf/dte-token-cache`
- Files: `amp/distributed-worker/helpers.go` (+`cache.go` new), mirror.
- LoC: ~250
- LRU `golang-lru/v2` (3000 entries); TTL = `min(token_exp - 60s, 5m)`; invalidate on 401; `dte_auth_token_cache_total{result}` counter.
- Hard guard: cache key uses the **same** group filter convention as recent slauth commits; unit tests assert key uniqueness across group-set differences.
- Acceptance: `auth_token_cache_hit_ratio > 0.85` after 1 h warm-up.
- Depends-on: PR-A1

#### `PR-A3` Async `logAuthenticatedUser`
- Branch: `perf/dte-async-authlog`
- Files: `helpers.go` only.
- LoC: ~60
- Move call into `go func(){}` + 5 s ctx; small per-process result cache (`(cluster,user) -> 5m`).
- Acceptance: `dte_activity_duration_seconds` p95 ↓ ≥ 5 % on health-check activities.

#### `PR-A4` Regex compile cache for `filterGroupsByPattern`
- Branch: `perf/dte-regex-cache`
- Files: `helpers.go`.
- LoC: ~40
- `var compiledPatterns sync.Map` keyed by raw pattern string.
- Acceptance: `dte_auth_token_exchange_seconds` p95 ↓ further (~10 %).

### EPIC P0-B : k8s-metadata-collector

#### `PR-B1` Replace `log.Fatalf` with logged error + retry; add backoff
- Branch: `fix/metadata-collector-no-fatal`
- Files: `k8s-metadata-collector/main.go`.
- LoC: ~50
- Acceptance: pod restart-count from this binary → 0 in staging week.

#### `PR-B2` Convert to shared informers (Pod, Node, ServiceAccount)
- Branch: `perf/metadata-collector-informers`
- Files: `k8s-metadata-collector/main.go` (+ `informers.go`).
- LoC: ~400
- `informers.NewSharedInformerFactory(client, 30*time.Minute)`; event handlers update an in-memory map; periodic flush to send pipeline.
- Backwards-compat: same `ClusterMetadata` JSON shape on Kinesis.
- Acceptance: apiserver `request_total{user~="kitt-metadata.*"}` ↓ ≥ 80 %.
- Depends-on: PR-B1

#### `PR-B3` Batch `PutRecords` for Kinesis
- Branch: `perf/metadata-collector-putrecords`
- Files: `k8s-metadata-collector/main.go`.
- LoC: ~150
- Buffer up to 500 records or 4 MB; flush on timer or full; emit `kitt_metadata_kinesis_failed_records_total`.
- Acceptance: Kinesis `IncomingRecords` ↓ at constant data volume.
- Depends-on: PR-B2 (or independent if we keep the existing `for` loop in interim)

### EPIC P0-C : Sweeper retry-storm + scope

#### `PR-C1` Don't retry on non-transient errors in `labelPod`
- Branch: `fix/sweeper-retry-class`
- Files: `sweeper/controllers/sweeper_controller.go`.
- LoC: ~40 (+ tests)
- Replace `func(err error) bool { return true }` with `apierrors.IsConflict || IsServerTimeout || IsTooManyRequests`.
- Acceptance: in chaos-test of 403 pods, no retry beyond first attempt.

#### `PR-C2` Add label selector + pagination to `labelAllPods`
- Branch: `perf/sweeper-paginate`
- Files: `sweeper/controllers/sweeper_controller.go`.
- LoC: ~80 (+ tests)
- Use `client.MatchingLabels{}` to skip already-labeled pods at-source; loop with `Limit(500)` continue token.
- Acceptance: apiserver List bytes ↓ on canary cluster.
- Depends-on: PR-C1 (cleaner test surface)

### EPIC P0-D : ForgeApp Status churn

#### `PR-D1` Single Status().Patch() at end of Reconcile
- Branch: `perf/forgeapp-status-coalesce`
- Files: `forge_containers/controllers/forgeapp_controller.go` + tests.
- LoC: ~250 (refactor)
- Build a local `desired := forgeApp.Status.DeepCopy()`; mutate locally during Reconcile; one `r.Status().Patch(ctx, forgeApp, client.MergeFrom(original))` at end.
- Acceptance: etcd writes from controller ↓ ≥ 60 % per reconcile (sample by `kubectl audit log` or apiserver metric).

#### `PR-D2` Demote `logStatus` and drop MarshalIndent
- Branch: `perf/forgeapp-logstatus-level`
- Files: `forgeapp_controller.go`.
- LoC: ~30
- `V(1)` log level + `json.Marshal` (no indent); only on phase transitions.

### EPIC P0-E : Kitt-runbooks client cache

#### `PR-E1` Cache K8s clientset by cluster (with auth-failure invalidation)
- Branch: `perf/runbooks-client-cache`
- Files: `kitt-runbooks/internal/k8sclient/client.go`, `activities.go`, `activities_high_unhealthy_deployments.go`, `activities_cyclops.go` + tests.
- LoC: ~250
- `sync.Map[clusterID]*ClientBundle{client, expiresAt}`; invalidate on 401 / on cluster-config-change signal; metric `runbook_k8s_client_cache_total{result}`.
- Hard guard: respect existing `slauth-token` group cache (we don't re-implement; we sit *above* it).
- Acceptance: `runbook_k8s_client_create_seconds` count ↓ ≥ 80 % after warm-up.

#### `PR-E2` Make auth-diagnostics opt-in
- Branch: `perf/runbooks-authdiag-flag`
- Files: `kitt-runbooks/internal/k8sclient/auth_diag.go`, `client.go`.
- LoC: ~50
- `if os.Getenv("KITT_RUNBOOK_AUTH_DIAG") == "1"` else cached for 1 h.
- Acceptance: `runbook_activity_duration_seconds` p95 ↓ on first-call activities.

---

## Phase 2 — P1 EPIC bundles

### EPIC P1-A : Scraper Redis hot path

#### `PR-S1` Batched `was_url_visited`
- Branch: `perf/scraper-batch-visited`
- Files: `src/db_utils.py`, `src/redis_utils.py`, `src/worker.py`.
- LoC: ~180
- New `was_url_visited_batch(job_id, urls)` using `WHERE url = ANY($1)` + Redis `SMISMEMBER`.

#### `PR-S2` Redis pipelining for pop/process/ack
- Branch: `perf/scraper-redis-pipeline`
- Files: `src/redis_utils.py` (+ optional Lua script under `redis_scripts/`).
- LoC: ~120
- Acceptance: `scraper_url_processing_p50_ms` ↓ ≥ 30 %.

#### `PR-S3` Fix workflow `gather_timeout` race
- Branch: `fix/scraper-gather-timeout`
- Files: `src/workflow.py`.
- LoC: ~40
- Increase to 300 s OR shrink batch to 5; add metric `scraper_workflow_orphan_activities_total`.
- Acceptance: orphan count → 0 in staging chaos test.

#### `PR-S4` Pool monitoring + acquire-timeout + circuit-breaker
- Branch: `obs/scraper-pool-health`
- Files: `src/db_utils.py`, `src/redis_utils.py`.
- LoC: ~120
- Prom gauges; 5 s acquire timeout; periodic `SELECT 1` keepalive; metric `scraper_pool_acquire_timeout_total`.

### EPIC P1-B : Runbooks log-cost + parallel + retry

#### `PR-R1` Activity retry policies on cordon workflows
- Branch: `fix/runbooks-activity-retry`
- Files: `kitt-runbooks/workflow_node_cordoned.go`, `workflow_high_unhealthy_deployments.go`, `workflow_cyclops.go`.
- LoC: ~60
- `RetryPolicy: {MaxAttempts:3, InitialInterval:1s, BackoffCoefficient:2}` per ExecuteActivity.
- Acceptance: `runbook_activity_total{result="error"}` retry-rate ↑ then settle, terminal failure ↓.

#### `PR-R2` Parallelise CheckNodeStatus loop
- Branch: `perf/runbooks-parallel-nodecheck`
- Files: `kitt-runbooks/workflow_node_cordoned.go`.
- LoC: ~80
- Collect futures; cap parallelism at 10; `await` all.
- Acceptance: cordon workflow p95 ↓ ≥ 50 % on multi-node runs.

#### `PR-R3` Demote / sample noisy logs (preserve cordon-flow context)
- Branch: `obs/runbooks-log-levels`
- Files: `kitt-runbooks/activities.go`, `activities_*.go`, `workflow_*.go`.
- LoC: ~150
- For each `logger.Info` added by 3-month "added logging to the cordon workflows" series:
  - Keep the field set (consumers may rely on it).
  - Move per-node-loop logs to `Debug` (V(1)).
  - Sample 1/100 for high-volume Info lines via `slog.HandlerOptions.Level`.
- Hard guard: PR description must enumerate every demoted line + the SRE who introduced it; offer them an opt-out via env (`KITT_RUNBOOK_VERBOSE=1`).
- Acceptance: Splunk `index=kitt-runbooks` ingest GB/day ↓ ≥ 30 %.

### EPIC P1-C : DTE fan-out + ctx

#### `PR-D1` Fan-out semaphore + workflow.Sleep adaptive
- Branch: `perf/dte-fanout-sem`
- Files: `amp/distributed-worker/main.go`, mirror.
- LoC: ~120

#### `PR-D2` `ctx.Done()` in Argo poll loop
- Branch: `fix/dte-poll-ctx`
- Files: `amp/distributed-worker/main.go:520-548`, mirror.
- LoC: ~30

### EPIC P1-D : Predicate / status filter

#### `PR-PR1` GenerationChangedPredicate on owned objects in forgeapp
- Branch: `perf/forgeapp-predicates`
- Files: `forge_containers/controllers/forgeapp_controller.go:560-575`.
- LoC: ~40

### EPIC P1-E : Scraper Py↔JS audit

#### `PR-AUD1` Audit doc + diff matrix
- Branch: `docs/scraper-py-js-divergence`
- Files: `scraper/temporal-pg-redis/docs/PY_JS_DIVERGENCE.md`
- LoC: docs
- Outputs the canonical retry/skip semantics; drives PR-AUD2.

#### `PR-AUD2` Single shared YAML retry config
- Branch: `chore/scraper-shared-retry-config`
- Files: `scraper/temporal-pg-redis/config/retry-policies.yaml`, both `src/workflow.py` and `src-js/workflow.js`.
- LoC: ~150
- Both runtimes load same YAML at startup.

---

## Phase 3 — P2 (small PRs, can be done in any order)

| PR ID | Title | Files | LoC |
|-------|-------|-------|-----|
| `PR-P2-01` | Pagination + label selector for runbooks Pods/Nodes List | `kitt-runbooks/internal/k8sclient/client.go` | ~120 |
| `PR-P2-02` | Splunk query cache + tighten earliest | `kitt-runbooks/activities.go`, `internal/splunk/client.go` | ~150 |
| `PR-P2-03` | Activity-type-specific timeouts in DTE | `amp/distributed-worker/main.go` | ~80 |
| `PR-P2-04` | Histograms in scraper Python | `scraper/.../src/metrics.py` | ~80 |
| `PR-P2-05` | Workflow payload-size guard | `scraper/.../src/workflow.py` | ~60 |
| `PR-P2-06` | Redis TTLs on work/processing keys | `scraper/.../src/redis_utils.py` | ~60 |
| `PR-P2-07` | Prepared statements in scraper PG | `scraper/.../src/db_utils.py` | ~80 |
| `PR-P2-08` | Per-fetch timeout in scraper | `scraper/.../src/worker.py` | ~30 |
| `PR-P2-09` | `forgeapp` ensureNamespace requeue (drop sleep) | `forge_containers/controllers/forgeapp_controller.go` | ~40 |
| `PR-P2-10` | Backoff on not-ready deployment requeue | same | ~30 |
| `PR-P2-11` | KEDA scaler add Redis-depth trigger | `scraper/.../k8s/keda-scaledobject.yaml` | yaml |
| `PR-P2-12` | `pod_label_sweeper.py` parallelise (interim) | `deploy/python/pod_label_sweeper.py` | ~80 |
| `PR-P2-13` | Splunk client 60→15 s timeout | `kitt-runbooks/internal/splunk/client.go` | ~10 |
| `PR-P2-14` | Structured workflow logs | `kitt-runbooks/workflow_*.go` | ~100 |
| `PR-P2-15` | `scraper_processor.py` dedup (lambda → import) | `scraper/pg/`, `lambda/pg/` | move |
| `PR-P2-16` | `-race` in CI | bitbucket-pipelines | yaml |
| `PR-P2-17` | `forgeapp` addFinalizer use Patch | `forgeapp_controller.go:346-374` | ~40 |
| `PR-P2-18` | `asicore` UpdateASI diff-then-update | `asi/internal/asicore/asi.go` | ~50 |

---

## Phase 4 — P3 strategic refactors

See **`06_OUT_OF_BOX.md`**:
- `PR-OOB-01..04` — Extract `pkg/dte` shared module (DTE consolidation).
- `PR-OOB-05..06` — Extract `pkg/clusterauth` (cluster client + token cache shared by DTE worker AND kitt-runbooks).
- `PR-OOB-07..08` — Decommission `pod_label_sweeper.py` Python.
- `PR-OOB-09` — Scraper Py↔JS unification roadmap (if business decides to consolidate).
- `PR-OOB-10` — Optional: scraper signal-driven dispatcher to remove polling.
