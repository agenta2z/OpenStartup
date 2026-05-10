# Prioritized Plan (P0 → P3)

> Each item lists: **scope, target metric movement, dependencies, owner-hint, time-box.**
> Items reference findings in `02_FINDINGS_CATALOG.md` and PRs in `04_PR_BREAKDOWN.md`.

---

## Phase 0 — "Make the change measurable" (Week 0; mandatory precondition)

| ID | Title | Findings | Why it goes first |
|----|-------|----------|-------------------|
| **PHASE0-OBS** | Stand up Prom histograms + `/metrics` on DTE worker, scraper-go shim, kitt-runbooks worker. Standard RED labels. | E1, A11, B11, C12 | We cannot prove a 50 % auth-latency win without `auth_provider_token_exchange_p95_ms`. Without metrics, every later phase is unfalsifiable. |
| **PHASE0-CI** | CI assertion: `diff` between `amp/*` and `helmfile/dte/*` must be 0 OR an explicit `DIVERGENCE.md` exists. | E2 | Stops further drift while we plan A1 consolidation. |

**Acceptance**: `auth_provider_token_exchange_seconds`, `dte_activity_duration_seconds`, `forgeapp_reconcile_duration_seconds`, `scraper_url_processing_seconds` all visible in Grafana with one-week baseline before P0 patches go in.

---

## Phase 0.5 — STABILITY (NEW, inserted 2026-05-08 after user crash report)

> **The user reported the service is unstable and crashes frequently.** A multi-agent investigation (see `07_STABILITY_PLAN.md`) found that ~70 % of the crash classes were **NOT** addressed by the original (perf-oriented) plan. EPIC P0-S is therefore inserted **here** — between Phase 0 (observability) and Phase 1 (perf wins). It must ship **first**: perf wins on a crashing service are unrealisable.

### EPIC P0-S : "Stop the crashing — proper, idiomatic fixes only"
**Goal axes:** Reliability (pod restart-rate ↓ ≥ 80 %, MTTR ↓, no phantom-pods); Latency (no probe-induced restarts during legitimate long activities); Throughput (no worker-slot starvation from poison-pill retries or 60s Splunk hangs).
**Owner-hint:** Each item is scoped to a single binary's owner — small, atomic, parallel-mergable PRs.
**Items (15 total, see `07_STABILITY_PLAN.md` for full text + receipts):**

| ID | Binary | One-line summary | Crash class addressed |
|----|--------|------------------|------------------------|
| **S1** | k8s-metadata-collector | Remove `log.Fatal` from steady-state collection loop; add backoff + `kitt_metadata_collect_errors_total` | CrashLoopBackoff on every apiserver hiccup |
| **S2** | kitt-runbooks worker | Surface `w.Run()` error via channel; exit non-zero so kubelet restarts | Silent worker death (phantom pod) |
| **S3** | kitt-runbooks worker | Add `/livez` `/readyz` `terminationGracePeriodSeconds` `preStop` (currently NONE defined) | Hung binary not detected; activity-mid-flight kills |
| **S4** | DTE distributed-worker | Replace goroutine `os.Exit(1)` with `srv.Shutdown(ctx)`; surface error via channel | HTTP-bind glitch kills entire pod mid-activity |
| **S5** | iam-sidecar | Replace `log.Fatal` in `ServeHTTP` with HTTP 500; add IMDS retry | One bad creds object crashes the whole pod (sidecar pattern) |
| **S6** | ASI | Replace 6× `panic(err)` + 2× `log.Fatalf` in business code with returned errors | Crash-on-first-IAM-glitch |
| **S7** | ForgeApp controller | Nil-deref guard on `*deployment.Spec.Replicas` + `recover()` middleware | Reconcile panic → leader-election failover |
| **S8** | ForgeApp controller | Replace `time.Sleep` in Reconcile with `RequeueAfter` | Workqueue starvation → leader-election timeout |
| **S9** | Scraper worker (Py) | Add `loop.add_signal_handler(SIGTERM)` + graceful drain + preStop | Activities killed mid-write → poison-pill storm |
| **S10** | Scraper worker (Py) | Singleton `aiohttp.ClientSession` + per-request `ClientTimeout` | Connection leak; 5min hang on slow servers |
| **S11** | Scraper workflow | `maximum_attempts=5` + `non_retryable_error_types` + circuit breaker | Poison-pill activities monopolise worker CPU |
| **S12** | kitt-runbooks Splunk client | 60s → 10s timeout + `sony/gobreaker` circuit breaker | 6 slow Splunk queries kill all worker capacity |
| **S13** | kitt-runbooks worker | Exponential backoff + jitter + max-elapsed=5min, then exit | Thunder-herd reconnect when Temporal returns |
| **S14** | kitt-runbooks/DTE worker | Replace `InsecureSkipVerify=true` with proper CA bundle | Silent cert-rotation failure (next 7243→7233-class incident) |
| **S15** | Scraper worker | Realign probes: cheap `/livez` + deep `/readyz`; tGPS = max(activity_timeout) | Probes have been progressively loosened to mask real bugs |

**Hard constraints:**
- Every PR is **small** (40–250 LoC) and **atomic** — one finding per PR.
- For binaries duplicated across `amp/*` and `helmfile/dte/*`: matching change in both copies (CI fence per Phase-0 PR-PHASE0-04).
- For S3 + S15 (probe changes): must canary on one cluster for ≥48 h before global roll-out — probes are operationally sensitive.
- For S14 (TLS): must canary; coordinate with the team that landed `1b1c279` (recent port flip) — they have the receipts on the cert chain.
- No "ad-hoc" silencing of probes (e.g., raising failureThreshold to 50). All fixes must address the **underlying** issue.

**Time-box:** ~8 working days end-to-end with 1 PR/day cadence. Day-by-day rollout sequence is in `07_STABILITY_PLAN.md` §"Rollout sequence".

**Acceptance (the whole epic):**
- Pod restart-rate per binary ↓ ≥ 80 % over a 7-day post-rollout window vs. baseline (Phase-0 metrics make this measurable).
- `kubectl describe pod` for kitt-runbooks / k8s-metadata-collector / iam-sidecar shows ≤ 0.5 restarts/day on canary.
- New PagerDuty alert: `runbook_worker_run_loop_terminations_total > 0` fires within 1 min (S2).
- Chaos test: kill Temporal for 10 min — **no** retry-storm (S13), **no** OOM (S11), workers exit cleanly + kubelet restarts.
- Load test: `/livez` p99 ≤ 10 ms while worker at full saturation (S3, S15).

---

## Phase 1 — P0 perf wins (Weeks 2–4 — runs in parallel with P0-S) — "Stop the bleeding"

> **Note:** Phase 1 perf work was originally Weeks 1–3, now shifted right by ~1 week to let Phase 0.5 land first. P0-S and P0 perf-EPICs are uncorrelated and can be developed in parallel branches; the sequencing constraint is only on **canary**: never canary a perf change on a pod that just got a stability fix without a 48-hour soak.

These are the **highest impact, lowest risk** items. Each is goal-mapped:

### EPIC P0-A : "DTE auth path is the bottleneck"
**Goal axes:** Latency p95 ↓50–70% (auth path); COGS ↓ ~$3–6K/mo; Throughput ↑ ~10–15%.
**Owner-hint:** dte-worker maintainer (last 3 mo author of slauth commits).
**Items:** A2 (HTTP pool) → A3 (token cache) → A6 (async logAuthenticatedUser) → A7 (regex cache).
**Hard constraints:** Cache key MUST include `groups` (recent commits added group-aware tokens). Don't break TLS-for-Temporal change.
**Time-box:** 5 days net code; 2 days canary.
**Acceptance:** `auth_provider_token_exchange_p95_ms` < 50 ms cache hit / < 500 ms miss; `auth_token_cache_hit_ratio > 0.85` on a busy worker pod for 24 h.

### EPIC P0-B : "k8s-metadata-collector is a quiet apiserver killer"
**Goal axes:** K8s-API QPS ↓90%; Kinesis cost ↓60%; pod-restart count → 0.
**Owner-hint:** infra collectors team.
**Items:** D1 (informer) → D2 (PutRecords batch) → bonus: remove `log.Fatalf` (D1 covers).
**Hard constraints:** Output schema bytes-equivalent (downstream consumers).
**Time-box:** 6 days code; 1 week canary on one cluster.
**Acceptance:** apiserver `request_total{user="kitt-metadata"}` count ↓ ≥ 80 %; Kinesis `IncomingRecords` count ↓ ≥ 50 % at unchanged data volume.

### EPIC P0-C : "Sweeper retry-storm + cluster-wide list"
**Goal axes:** Reliability (no retry storm); K8s-API QPS ↓95% from sweeper.
**Items:** D4 (don't retry 403/422) → D3 (label selector + pagination) → eventually D11 (decom Python sibling).
**Hard constraints:** Sweeper is privileged; tests must include 403/422 scenarios.
**Time-box:** 3 days.
**Acceptance:** sweeper-controller errors plateau (no retry-storm); apiserver request rate from sweeper SA ↓.

### EPIC P0-D : "ForgeApp Status churn"
**Goal axes:** Reconcile p95 ↓30%; etcd writes ↓70% from controller.
**Items:** D5 (one Status patch/reconcile) → D6 (level + drop json.MarshalIndent).
**Time-box:** 3 days.
**Acceptance:** `controller_runtime_reconcile_total{controller="forgeapp"}` writes ↓ ≥ 60 %.

### EPIC P0-E : "Kitt-runbooks: stop re-creating clients per activity"
**Goal axes:** MTTR ↓ 2.5–10 s per cordon workflow; apiserver auth-load ↓.
**Items:** C2 (cache clientset) → C6 (gate auth-diag).
**Hard constraints:** Coordinate with the `slauth-token` group cache landed `00170e6`/`1d0fd4f`. Cache must invalidate on 401.
**Time-box:** 4 days.
**Acceptance:** `kitt_runbook_workflow_duration_p95_seconds` ↓ ≥ 5 s; `k8sclient_creation_total` ↓ ≥ 80 %.

---

## Phase 2 — P1 wins (Weeks 4–6) — "Compound the gains"

### EPIC P1-A : "Scraper Redis hot path"
**Items:** B1 (batched visited-check) → B2 (Redis pipeline) → B3 (gather_timeout race) → B9 (pool monitoring).
**Goal axes:** URL latency p50 ↓40-50%; reliability (silent-orphan elimination).
**Time-box:** 8 days.
**Acceptance:** `scraper_url_processing_p50_ms` ↓ ≥ 40 %; orphan-activity-count → 0 in staging.

### EPIC P1-B : "Kitt-runbooks log-cost + parallelism + retry"
**Items:** C1 (log levelling/sampling) → C3 (parallelise CheckNodeStatus) → C8 (activity retry policy).
**Hard constraints:** §05 — preserve cordon-flow context that recent commits added; downgrade Info → Debug rather than delete.
**Goal axes:** Splunk ingest ↓ 30-50% from runbook namespaces; MTTR ↓ ~90% on multi-node cordon; -10% workflow failures.
**Time-box:** 5 days.
**Acceptance:** Splunk ingest `index=kitt-runbooks` GB/day ↓ ≥ 30 %; cordon workflow p95 ↓.

### EPIC P1-C : "DTE worker bounded fan-out + ctx propagation"
**Items:** A4 (semaphore for fan-out) → A5 (ctx.Done() in poll loop).
**Goal axes:** p99 latency ↓ ~30 % at large fan-out; reliability.
**Time-box:** 3 days.

### EPIC P1-D : "Predicates & status-only filtering"
**Items:** D10 (GenerationChangedPredicate on owned objects) → D6 (logStatus level).
**Goal axes:** Reconcile rate ↓ at scale.
**Time-box:** 2 days.

### EPIC P1-E : "Python ↔ JS scraper divergence audit"
**Items:** B8 (audit + sync retry/skip semantics).
**Goal axes:** Reliability; pre-condition for P3 consolidation.
**Time-box:** 5 days (audit-only, no consolidation yet).

---

## Phase 3 — P2 wins (Weeks 7–10) — "Tighten the floor"

| Item | Finding | Lift |
|------|---------|------|
| Field-selectors + pagination on all `List` | C5, A9 | API CPU |
| Splunk query narrowing + cache | C4, C9, C10 | Splunk cost |
| Activity-type-specific timeouts | A8 | Tail latency |
| Histograms on scraper Python | B11 | Observability |
| Workflow payload size guards | B14 | Reliability |
| Redis TTLs / KEDA Redis-depth scaler | B6, B4 | Memory/scale |
| Prepared statements (scraper PG) | B5 | DB CPU |
| Per-fetch timeout in scraper | B7 | p95 latency |
| `forgeapp` ensureNamespace requeue (no sleep) | D7 | Reconciler thread |
| Backoff on not-ready deployment requeue | D9 | Reconcile churn |
| `pod_label_sweeper.py` parallelise (interim) | D11 | Big-cluster sweep time |
| Splunk client 60 s → 15 s timeout | C9 | SRE wait |
| Structured workflow logs | C12 | Splunk parse cost |
| `scraper_processor.py` dedup | B15 | Maintenance |
| `-race` in CI | E3 | Detect A12-class races |

---

## Phase 4 — P3 / strategic (Weeks 10+)

| Item | Finding | Notes |
|------|---------|-------|
| **Single shared Go module** for DTE worker/client | A1 | See §06 for the 4-PR plan |
| **Decommission** `pod_label_sweeper.py` Python in favour of operator | D11 | Requires confirmation no other consumer |
| **Consolidate** `scraper_processor.py` duplicates | B15 | Lambda just imports from package |
| **Scraper Python/JS unification** | B8 → B-consolidation | Pick one runtime; see §06 |
| Innovative: extract `pkg/clusterauth` (cluster-aware HTTP+token cache) shared by DTE worker & kitt-runbooks | A3 + C2 | One source of truth |
| Innovative: replace polling-loop scraper batching with Temporal `signal-based` queue feeder | B12 | Removes idle worker waste |

---

## Visual summary

```
PRIORITY  AXIS                       EPICS
P0-S      RELIABILITY (NEW Phase0.5) ┌── S1  metadata-collector log.Fatal in loop
                                     ├── S2  silent worker death (kitt-runbooks)
                                     ├── S3  probes/preStop/tGPS for kitt-runbooks
                                     ├── S4  DTE worker os.Exit from goroutine
                                     ├── S5  iam-sidecar Fatal in ServeHTTP
                                     ├── S6  ASI panic-in-business-code
                                     ├── S7  forgeapp nil-deref on Replicas
                                     ├── S8  forgeapp Sleep-in-Reconcile
                                     ├── S9  scraper SIGTERM handler + preStop
                                     ├── S10 scraper aiohttp session+timeout
                                     ├── S11 scraper bounded retries+circuit
                                     ├── S12 Splunk timeout + circuit breaker
                                     ├── S13 Temporal connect backoff cap
                                     ├── S14 TLS InsecureSkipVerify removal
                                     └── S15 scraper probe realignment

P0        Latency / Reliability      ┌── P0-A DTE auth path
                                     ├── P0-B metadata-collector apiserver killer
                                     ├── P0-C sweeper retry storm
                                     ├── P0-D forgeapp status churn
                                     └── P0-E runbooks client cache

P1        Compound gains             ┌── P1-A scraper redis hot path
                                     ├── P1-B runbooks log + parallel + retry
                                     ├── P1-C DTE fan-out + ctx
                                     ├── P1-D predicates / status filter
                                     └── P1-E python↔js audit

P2        Tighten floor              (15 small items, each <1 day)

P3        Strategic refactor         (consolidation; see §06)
```
