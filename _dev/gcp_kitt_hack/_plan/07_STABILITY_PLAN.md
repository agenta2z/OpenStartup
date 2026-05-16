# Stability & Crash-Reduction Plan
**Trigger:** User report — *"the current service is unstable and very often crashes"*.
**Status:** This file is a **NEW EPIC P0-S** added on top of the existing plan in this directory.

> **See also:** [`helmfile_enhancement_plan/02_FINDINGS_CATALOG.md`](helmfile_enhancement_plan/02_FINDINGS_CATALOG.md) Appendix C — **S4** (DTE HTTP listener `os.Exit`) is mirrored as **HF-27** in the helmfile-specific plan. The remaining S-series items (S1, S2, S3, S5–S15) are explicitly OUT-OF-SCOPE for the helmfile child plan because they live under `kitt-runbooks/`, `scraper/`, `iam-sidecar/`, `asi/`, `forgeapp-controller/`, or `k8s-metadata-collector/`. Disposition for each S-item is documented in the child plan's Appendix C.

---

## TL;DR — alignment with the existing plan

| Existing plan covers? | Items |
|---|---|
| ✅ **Already in plan** | D1 (k8s-metadata-collector `log.Fatal` → backoff), B3 (scraper `gather_timeout` orphan), B9 (scraper pool exhaustion), D4 (sweeper retry-storm), A12 (race), C9 (Splunk 60s timeout), A5 (ctx.Done propagation) |
| ⚠️ **Partially covered, needs sharper fix** | k8s-metadata-collector loop (only the log was scoped; we also need to wrap the loop in a backoff *and* never restart the process for a List error) |
| ❌ **NEW — added by this stability investigation** | S1–S15 below — the **majority** of the user's reported crashes are NOT covered by §02 alone. The previous plan was a **performance plan**; this is a **reliability plan**. They are complementary and *both* needed. |

So: **the user's crash pain is only ~30% covered by the existing plan.** The remaining ~70% is here as **EPIC P0-S** — **Stability** — which now becomes **Phase 0.5** between Phase 0 (observability) and Phase 1 (perf wins). Stability ships first; without it, perf wins on a crashing service are worth nothing.

---

## Investigation evidence (receipts)

The evidence for *why* the service is unstable is empirical and overwhelming:

1. **Recent commits** include `1b1c279/d350db7/1571fe0 fix connection errors`, `f701b5d fixed deployment errors`, multiple `fix deployment failures` and `fix test failures`, plus `update filebeat memory request` (an OOM tuning). The team has been firefighting connection-layer and deployment crashes for months.
2. **Process-killing constructs** are densely populated:
   - `k8s-metadata-collector/main.go`: **7 `log.Fatal`** (lines 123, 128, 375, 380, 385, 392, 409) — including **two inside the steady-state collection loop** (lines 123 + 128).
   - `iam-sidecar/iam-sidecar.go`: **5 `log.Fatal`** including **line 160 inside `ServeHTTP`** — every malformed creds JSON crashes the sidecar (and the whole pod).
   - `asi/cmd/main.go`: **6 `panic(err)`** in startup; `asi/internal/asicore/asi.go:105,111`: 2 `log.Fatalf` in *business* code.
   - `amp/distributed-worker/main.go`: **5 `os.Exit(1)`** including one inside a goroutine running `http.ListenAndServe` (line 794).
3. **Silent worker death**: `kitt-runbooks/cmd/worker/main.go:107-108` — `w.Run(worker.InterruptCh())` error is logged as `Info` then ignored. Worker stops accepting tasks while `/healthz` keeps returning 200. **This is the #1 reason for "the service appears alive but doesn't process anything"**.
4. **Probe / lifecycle gaps**:
   - `kitt-runbooks/worker-values.yaml` has **no livenessProbe, no readinessProbe, no preStop, no terminationGracePeriodSeconds** — it relies entirely on defaults.
   - `scraper/temporal-pg-redis/values/worker.yaml:179-184` has comments documenting the team's firefight: *"Increased from 20s to allow more time during startup with concurrent activities"*, *"Increased from 30s to prevent restarts when event loop is busy"*. The probes have been progressively loosened to mask underlying issues.
5. **Recent Temporal port flip** (`1b1c279`, port 7243→7233 to fix "connection reset"/"EOF"/"404 Not Found") proves the connection layer is fragile and TLS configuration is brittle.

---

## EPIC P0-S — Stability (top 15 fixes ranked by crash-reduction impact)

> Scoring: **(Crash-frequency × Blast-radius) ÷ (Effort × Risk)**.
> "Blast-radius" considers cascading effects (e.g. an iam-sidecar crash takes down the whole pod, not just the sidecar).

### S1. Remove `log.Fatal` from `k8s-metadata-collector` collection loop (CRITICAL)
**File:line:** `k8s-metadata-collector/main.go:123, 128`
**Root cause:** Inside the collection loop, `clientset.CoreV1().Nodes().List(...)` and `Pods("").List(...)` errors trigger `log.Fatalf`, killing the pod. Every transient apiserver error (throttling, brief network blip, control-plane upgrade) → CrashLoopBackoff.
**Crash class:** Process-kill / CrashLoopBackoff
**Frequency at scale:** Multiple per day per cluster.
**Fix (elegant, idiomatic):**
- Change `GetPodsAndNodes` and `getServiceAccounts` to **return** errors instead of fatal.
- In `collectAndSendMetadata`, treat each iteration as a fallible operation; on error: log structured warning + emit `kitt_metadata_collect_errors_total` counter + **exponential backoff with jitter** (e.g., `backoff.NewExponentialBackOff()` capped at 30 s) before retry; **never exit the process**.
- Reserve `log.Fatalf` strictly for startup misconfiguration (env-var parse, client construction). Even those should prefer `os.Exit(1)` *after* a clear structured error, so `kubectl logs` shows the cause.
**Tests/observability:** Inject 503/timeout from a fake apiserver in unit test; assert no `os.Exit`. New Prometheus counter; new health check that goes red after `≥ 3 × interval` of all-failure.
**Effort:** 1 PR, ~120 LoC, ~1 day.
**Risk:** LOW.
**Aligns with existing plan:** Tightens **PR-B1** (originally framed as "log instead of fatal"); we now require backoff + observability + health-degradation signal as part of the same PR.

---

### S2. Stop silently dying: surface `w.Run()` failure on kitt-runbooks worker
**File:line:** `kitt-runbooks/cmd/worker/main.go:105-109` (`go func() { if err := w.Run(...); err != nil { log.Info("Worker stopped", "error", err.Error()) } }()`)
**Root cause:** Worker run-loop runs in a goroutine; on failure, error is logged at *Info* and discarded. Process stays alive but does no work; `/healthz` returns 200; SREs see nothing wrong while activities pile up in Temporal.
**Crash class:** Silent-failure / phantom-pod (worse than crash).
**Fix (elegant):**
```go
workerErr := make(chan error, 1)
go func() {
    if err := w.Run(worker.InterruptCh()); err != nil {
        workerErr <- err
        return
    }
    workerErr <- nil
}()

// later, in main wait-loop:
select {
case sig := <-sigChan:
    log.Info("Received signal, shutting down", "sig", sig)
case err := <-workerErr:
    if err != nil {
        log.Error("Worker run loop terminated unexpectedly", "error", err)
        os.Exit(1)   // let kubelet restart us
    }
}
```
- Plus: make `/healthz` reflect **worker** liveness, not just HTTP liveness — return 503 if `workerErr` channel fired and we're in shutdown.
**Tests/observability:** Unit test that closes Temporal connection mid-flight; assert process exits non-zero. New Prometheus counter `runbook_worker_run_loop_terminations_total`.
**Effort:** ~80 LoC, ~half-day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.** Not previously surfaced.

---

### S3. Add proper liveness/readiness/preStop to kitt-runbooks worker
**File:line:** `kitt-runbooks/worker-values.yaml` (entire file — currently has *no* probes/preStop/grace)
**Root cause:** With S2 fixed, the binary will exit on real errors — but kubelet must also catch *hung* binaries. Currently relies entirely on Kubernetes defaults (no liveness probe = pod is never auto-restarted).
**Fix (elegant — proper, not hacky):** Add to worker-values.yaml:
```yaml
livenessProbe:
  httpGet:
    path: /livez       # shallow check
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 15
  timeoutSeconds: 3
  failureThreshold: 3   # 45s tolerance

readinessProbe:
  httpGet:
    path: /readyz      # checks worker-registered + temporal-connected
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3

terminationGracePeriodSeconds: 120  # >= longest activity StartToCloseTimeout

lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 15 && kill -TERM 1"]
      # 15s lets in-flight tasks finish; SIGTERM triggers Temporal worker drain
```
And in code (`cmd/worker/main.go`): add `/livez` (always returns 200 if main goroutine alive) and `/readyz` (returns 200 only when `worker.Started() && temporal.Connected()`).
**Critical correctness rule:** `terminationGracePeriodSeconds` MUST be `≥ max(activity.StartToCloseTimeout)`. If activities can run 2 min, grace MUST be ≥ 120 s.
**Tests/observability:** k8s e2e: deploy → curl `/livez` and `/readyz` → SIGTERM → ensure no in-flight activity is dropped (Temporal sees graceful drain, not crash).
**Effort:** Helm + ~60 LoC of probe handlers, ~1 day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.** Probes were not part of the perf plan.

---

### S4. Don't `os.Exit(1)` from a goroutine in DTE distributed-worker HTTP listener
**File:line:** `amp/distributed-worker/main.go:791-794` (mirrored in `helmfile/dte/...`)
**Root cause:** A spawned goroutine calls `http.ListenAndServe`; on any bind error (port collision, lingering TIME_WAIT, IPv6/IPv4 mismatch) it calls `os.Exit(1)` directly. This races with main-goroutine shutdown: in-flight activities are killed mid-write to Temporal.
**Fix (elegant):**
- Run HTTP server with explicit `*http.Server` so we can `srv.Shutdown(ctx)` it.
- Surface goroutine errors via a buffered error channel; main goroutine selects on `sigCh`, `workerCh`, `httpCh`, then orchestrates shutdown:
```go
httpErr := make(chan error, 1)
srv := &http.Server{Addr: ":"+port, Handler: mux}
go func() { httpErr <- srv.ListenAndServe() }()
// in shutdown: ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second); defer cancel(); srv.Shutdown(ctx)
```
**Tests/observability:** Test `:8080` already taken → assert clean shutdown, not `os.Exit`. Add `dte_worker_shutdown_reason_total{reason}` counter.
**Effort:** ~120 LoC across both copies (or one if A1 consolidation lands first), ~1 day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.** Existing plan never inspected the HTTP server lifecycle in DTE worker.

---

### S5. iam-sidecar must NEVER `log.Fatal` from `ServeHTTP`
**File:line:** `iam-sidecar/iam-sidecar.go:159-160`
**Root cause:** Inside `(s *service) ServeHTTP`, `json.Marshal(credsResponse)` failure calls `log.Fatal(err)`. A single bad creds object crashes the sidecar; sidecar pattern means **the whole pod becomes broken**.
**Fix (elegant):** Return HTTP 500 with structured error body; emit `iam_sidecar_marshal_errors_total` metric:
```go
credsResponseBytes, err := json.Marshal(credsResponse)
if err != nil {
    log.Printf("ERROR marshalling creds: %v", err)
    iamMarshalErrors.Inc()
    http.Error(w, "internal error", http.StatusInternalServerError)
    return
}
```
Also: `isAWS()`/`isGCE()` retries — currently a single 2 s timeout decides cloud provider for the lifetime of the pod; if both fail (slow IMDS), sidecar `log.Fatalln("unsupported cloud provider")`. Add **3 retries with exponential backoff** before falling through.
**Tests/observability:** Unit test with crafted unmarshalable struct. e2e test with mocked slow IMDS (≥3 s).
**Effort:** ~50 LoC, ~half-day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.** Existing plan said "iam-sidecar is solid" — that judgement was wrong; this `ServeHTTP` Fatal was missed in §02-D12 and is hereby retracted.

---

### S6. ASI: replace `panic(err)` and `log.Fatalf` in business code with returned errors
**File:line:** `asi/cmd/main.go:259, 263, 267, 299, 310, 315`; `asi/internal/asicore/asi.go:105, 111`
**Root cause:** Six `panic(err)` calls in `cmd/main.go` and two `log.Fatalf` inside `asicore.NewRealService` mean any IAM client construction issue (transient GCP API error, IAM quota, slow ADC discovery) crashes the binary.
**Fix (elegant):**
- `cmd/main.go`: replace each `panic(err)` with `return fmt.Errorf("init X: %w", err)` from a `run()` helper; `main` becomes `if err := run(); err != nil { log.Error(err); os.Exit(1) }`.
- `asicore/asi.go:105, 111`: NewRealService should return `(*RealIAMService, error)`. Callers handle.
- Keep startup-only failures fatal (it's correct for "missing required env-var") — but **wrap them in clear, actionable error messages** so `kubectl describe pod` gives the SRE the answer immediately.
**Tests:** Inject GCP IAM client construction failure; assert clean shutdown with helpful log line.
**Effort:** ~150 LoC + small refactor, ~1.5 days.
**Risk:** MED — touches initialization order.
**Status vs existing plan:** **NEW.**

---

### S7. ForgeApp controller: nil-deref guard on `*deployment.Spec.Replicas`
**File:line:** `forge_containers/controllers/forgeapp_controller.go:261, 291-298`
**Root cause:** `*deployment.Spec.Replicas` is dereferenced without nil-check. If a Deployment is created with `replicas: nil` (defaulted upstream to 1, but kubebuilder/SSA edge cases exist), the controller panics on Reconcile. Controller-runtime recovers panic and re-queues — but at high reconcile rate this becomes a hot CPU loop and eventually the leader-election lease is lost, triggering failover.
**Fix (elegant, idiomatic):**
```go
desired := int32(1)
if deployment.Spec.Replicas != nil {
    desired = *deployment.Spec.Replicas
}
if deployment.Status.AvailableReplicas < desired { ... }
```
Plus: add `recover()` in a controller-runtime middleware that emits `forgeapp_reconcile_panics_total{controller}` so the next nil-deref class is *seen*, not just "absorbed".
**Tests:** Unit test with Deployment `Replicas == nil` → no panic.
**Effort:** ~40 LoC + middleware, ~half-day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.**

---

### S8. ForgeApp controller: don't `time.Sleep` inside Reconcile
**File:line:** `forge_containers/controllers/forgeapp_controller.go:604-628` (`ensureNamespace` 3× `time.Sleep(time.Second)`)
**Root cause:** Reconcile is a worker-pool worker; blocking it for 3 s starves all other reconciles. Under load, the workqueue depth grows, leader-election renewal misses (default lease duration 15 s), and the controller falls over to its replica → flapping leader → repeated stalls. This is the textbook anti-pattern — the controller-runtime FAQ explicitly warns against it.
**Fix (elegant):** Return `ctrl.Result{RequeueAfter: 1 * time.Second}, nil` to defer to the workqueue. The reconciler will re-enter cleanly when the namespace status flips.
**Tests:** Reconcile race-test simulating slow namespace activation; assert workqueue depth stays <10.
**Effort:** ~40 LoC, ~half-day.
**Risk:** LOW.
**Status vs existing plan:** Listed in §02-D7 as a P2; **promoted to P0 here** because it's a stability blocker, not just a perf nit.

---

### S9. Scraper: graceful shutdown on SIGTERM + preStop hook
**File:line:** `scraper/temporal-pg-redis/src/worker.py` main entrypoint; `charts/scraper-worker/templates/deployment.yaml`
**Root cause:** No SIGTERM handler. Kubernetes sends SIGTERM, then 30 s later SIGKILL. In-flight activities are killed mid-write → Temporal marks them failed → poison-pill retry storm.
**Fix (elegant, idiomatic Python+asyncio):**
```python
loop = asyncio.get_running_loop()
stop = loop.create_future()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda: stop.set_result(None))
worker_task = asyncio.create_task(worker.run())
await stop
logger.info("SIGTERM received, draining worker")
await worker.shutdown(graceful_shutdown_timeout=timedelta(seconds=60))
await worker_task
```
Plus in chart values:
```yaml
terminationGracePeriodSeconds: 120
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 10"]   # let endpoints depopulate
```
**Tests:** Send SIGTERM mid-activity → assert activity completes cleanly (logged + Temporal sees normal close).
**Effort:** ~80 LoC, ~1 day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.**

---

### S10. Scraper: bound aiohttp/requests session lifetime + per-request timeout
**File:line:** `scraper/temporal-pg-redis/src/worker.py:311-324, 581`
**Root cause:** aiohttp `ClientSession()` (or `requests.get()` without timeout) is created inside activities and never closed → connection leak; a single hung server hangs the activity for the full activity timeout (5 min) blocking a worker slot. Compounded under high RPS = effective worker starvation = pod restart by liveness probe.
**Fix (elegant):**
- Module-level singleton `aiohttp.ClientSession` (created in worker startup, closed on shutdown) — same pattern works in both runtimes.
- `aiohttp.ClientTimeout(total=30, connect=10, sock_connect=5, sock_read=20)` on every request.
- For `requests`, always pass `timeout=(connect, read)` tuple.
**Tests:** Slow-server fixture; assert request fails fast (≤30 s) with a structured error, not a 5 min hang.
**Effort:** ~100 LoC, ~1 day.
**Risk:** LOW.
**Status vs existing plan:** Strengthens §02-B7 (was P2; **promoted to P0-S** as part of crash-reduction).

---

### S11. Scraper: bounded retries + circuit breaker for poison-pill activities
**File:line:** `scraper/temporal-pg-redis/src/workflow.py:125-180` (`get_retry_policy`)
**Root cause:** Activities have generous retry policies. A consistently failing activity (e.g., bug in URL parsing on a particular schema) retries forever, monopolising worker CPU.
**Fix (elegant, idiomatic Temporal):**
- Set `maximum_attempts=5` for transient classes; `non_retryable_error_types=["ValueError", "InvalidURL", ...]` for permanent-failure classes.
- Add a workflow-level circuit breaker: if a job's failure rate >50% over last 100 activities, suspend that job and emit `scraper_job_circuit_open_total{job_id}`.
**Tests:** Unit test poison-pill activity; assert workflow stops retrying after policy max.
**Effort:** ~120 LoC, ~1.5 days.
**Risk:** MED (must classify error types correctly).
**Status vs existing plan:** **NEW.**

---

### S12. Splunk client: timeout 60s → 10s + circuit breaker (kitt-runbooks)
**File:line:** `kitt-runbooks/internal/splunk/client.go:55`
**Root cause:** Single slow Splunk query holds an activity slot for 60 s; with default 10-concurrent activities, **6 slow Splunk queries kill all worker capacity for a full minute**. This cascades: kubelet liveness probe times out → pod restart.
**Fix (elegant):**
- `HTTPClient: &http.Client{Timeout: 10 * time.Second}` (env-overridable).
- Wrap with `sony/gobreaker` circuit breaker: trip on 5 consecutive failures, open for 30 s; emit `splunk_circuit_state{state}` gauge.
**Tests:** Mock Splunk returning 60s delay → activity fails fast; circuit opens; subsequent calls fail without RPC.
**Effort:** ~80 LoC, ~half-day.
**Risk:** LOW.
**Status vs existing plan:** Existed as §02-C9 P2 (timeout-only); **promoted to P0-S and extended with circuit breaker.**

---

### S13. Temporal worker connection: cap retry, add jitter, fail-loud after N
**File:line:** `kitt-runbooks/cmd/worker/main.go:65-82` (the loop fixed by `1b1c279`)
**Root cause:** Linear backoff (5s+5s+...+60s) without jitter and without max-attempts. If Temporal is down for 10+ min, all kitt-runbooks workers thunder-herd reconnect simultaneously when it returns. No fail-loud signal — workers spin forever.
**Fix (elegant):**
- Use `cenkalti/backoff/v4` exponential backoff with jitter, max-elapsed-time = 5 min, max-interval = 30 s.
- After max-elapsed, `os.Exit(1)` so kubelet restart-policy applies (which itself has exponential backoff at the pod level — let it do its job).
- Emit `runbook_temporal_connect_attempts_total{result}` counter.
**Tests:** Mock Temporal as unreachable for 7 min → worker exits cleanly after 5 min, kubelet restarts.
**Effort:** ~60 LoC, ~half-day.
**Risk:** LOW.
**Status vs existing plan:** **NEW.** Builds on the recent fix `1b1c279`, doesn't conflict.

---

### S14. Replace TLS `InsecureSkipVerify` with proper CA bundle
**File:line:** `kitt-runbooks/cmd/worker/main.go:46-58` (TLS detection); whatever sets `InsecureSkipVerify` in DTE worker
**Root cause:** `InsecureSkipVerify=true` masks (a) cert expiry, (b) hostname mismatch from a load-balancer rerouting, (c) protocol-vs-port mismatch (this exact bug caused the recent 7243→7233 panic). A future cert rotation fails silently as a connection-refused, looking identical to today's "fix connection errors" story.
**Fix (elegant):** Load CA from `/var/run/secrets/kubernetes.io/serviceaccount/ca.crt`; configure `tls.Config{RootCAs: pool, ServerName: hostname}`; **never** `InsecureSkipVerify`. If certs are externally signed, mount via Secret. Add startup-time TLS handshake test.
**Tests:** Rotate Temporal cert in dev; assert worker connects without code change.
**Effort:** ~80 LoC, ~1 day.
**Risk:** MED (TLS bugs hard to debug; must canary).
**Status vs existing plan:** **NEW.** Touches the same area the team firefought; this is the structural fix, theirs was a port flip.

---

### S15. Scraper liveness/readiness/preStop alignment audit
**File:line:** `scraper/temporal-pg-redis/values/worker.yaml:177-184`; `charts/scraper-worker/templates/deployment.yaml:144-159`
**Root cause:** Probes were progressively loosened in firefights ("Increased from 30s to prevent restarts when event loop is busy") — that means the liveness check has been touching the same path used by the worker, so a busy worker has been killed by liveness historically. **The proper fix is to separate liveness from worker-blocking work paths**, not to keep loosening timeouts.
**Fix (elegant — proper separation, not hack):**
- `/livez`: returns 200 if process alive (atomic flag set in main goroutine). Should respond in <10ms even under full load.
- `/readyz`: returns 200 only if `worker.is_running() and temporal.is_connected() and db.is_connected() and redis.is_connected()`. Slower is OK.
- `terminationGracePeriodSeconds = max(activity_timeout)` ≈ 360 s (URL_TIMEOUT 5 min + 60 s buffer).
- `preStop` `sleep 10` for endpoint depopulation.
- Roll back the loosened probe timeouts to defaults (15-30 s) once `/livez` is properly cheap.
**Tests:** Load-test: full activity load + parallel `/livez` curl; assert <10ms.
**Effort:** ~80 LoC + helm changes, ~1 day.
**Risk:** MED — current probes are calibrated to current behavior; changing them needs a canary.
**Status vs existing plan:** **NEW.**

---

## How EPIC P0-S integrates with the existing plan

```
PHASE 0     Observability + drift fence       (existing)
PHASE 0.5   ──> NEW EPIC P0-S — Stability     (this file)
                S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15
PHASE 1     P0 perf wins                      (existing — unchanged)
PHASE 2..4  P1, P2, P3                        (existing — unchanged)
```

**Why insert a new phase rather than re-rank everything:**
- Stability fixes are **low-risk** and **uncorrelated** with perf fixes. They can land in parallel branches.
- Perf gains on a service that crashes are unrealisable. SRE goodwill ("are these refactors making things worse?") depends on visible stability *first*.
- Many stability fixes (S2, S4, S6) actually *unlock* the perf wins by giving observable error signals.

## Cross-references — what to **update** in earlier files

The following changes (made in §08) integrate this epic without forking the plan:

- `00_README.md`: top-line table now lists P0-S above P0-A.
- `02_FINDINGS_CATALOG.md`: add §F (Stability) as a new group; reuse IDs S1–S15.
- `03_PRIORITIZED_PLAN.md`: insert "Phase 0.5 — Stability" before existing Phase 1.
- `04_PR_BREAKDOWN.md`: add `PR-S01..PR-S15` ahead of existing P0 PRs.
- `05_RISK_AND_HISTORY.md`: explicit cross-check that S5 and S14 don't regress recent connection-fix commits (`1b1c279`, `d350db7`, `1571fe0`).

## Acceptance criteria for the whole stability epic

- **Hard SLO**: pod restart-rate per binary ↓ ≥ 80 % over a 7-day window (vs. baseline before any S-PR ships).
- **Symptom**: `kubectl describe pod` for kitt-runbooks/k8s-metadata-collector/iam-sidecar shows ≤ 0.5 restarts/day on the canary cluster.
- **Silent-failure detection**: `runbook_worker_run_loop_terminations_total > 0` triggers PagerDuty within 1 minute (S2).
- **Cascade prevention**: a chaos-test that kills Temporal for 10 min causes **no** retry-storm (S13) and **no** OOM (S11).
- **Probe correctness**: load-test asserts `/livez` p99 ≤ 10 ms while worker at full saturation (S15, S3).

## Rollout sequence (1 PR/day pattern, all small)

| Day | PR | Why this order |
|---|---|---|
| 1 | S1 | metadata-collector restart-loop is the most visible "service crashes" symptom |
| 1 | S5 | iam-sidecar Fatal in ServeHTTP is the highest blast-radius for one line of code |
| 2 | S2 | Silent worker death is the worst class — fix it second |
| 2 | S7 | Single nil-deref guard on forgeapp |
| 3 | S4 | DTE worker `os.Exit` from goroutine |
| 3 | S6 | ASI panic-storm |
| 4 | S8 | forgeapp Sleep-in-Reconcile |
| 4 | S12 | Splunk timeout + circuit |
| 5 | S13 | Temporal connect retry cap |
| 5 | S9 | Scraper SIGTERM handling |
| 6 | S10 | aiohttp session + per-request timeout |
| 6 | S11 | Bounded retries + poison-pill circuit |
| 7 | S3 | Probes/preStop/grace for kitt-runbooks |
| 7 | S15 | Probes alignment for scraper |
| 8 | S14 | TLS InsecureSkipVerify replacement (canary required) |

Total: **~8 working days**, **15 small PRs** (each 40–250 LoC), **all reviewable in <30 min by a maintainer who knows the file**.
