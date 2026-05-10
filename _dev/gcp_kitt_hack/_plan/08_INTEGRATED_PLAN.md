# 08 — INTEGRATED PLAN: Best-of-Both Stability Plan
**Date:** 2026-05-08
**Sources reconciled:**
- **Plan-A** (`/Users/tchen7/.claude/plans/taking-a-deep-look-modular-hopper.md`) — *deep, scraper-only, 10 PRs*
- **Plan-B** (`07_STABILITY_PLAN.md` in this directory, S1–S15) — *broad, multi-service, 15 PRs*

> This file is the **canonical merged plan**. It supersedes neither — both remain as receipts. Items below carry a tag indicating origin: `[A]`, `[B]`, or `[A+B]` when the integrated version draws from both.

---

## TL;DR — what changed and why

The two plans are **complementary, not redundant**. A critical-validation pass (using `bash` against the actual source) found:

| | Plan-A (scraper-deep) | Plan-B (multi-service) |
|---|---|---|
| Coverage scope | scraper only | 5 binaries (scraper, kitt-runbooks, DTE worker, iam-sidecar, ASI, ForgeApp, k8s-metadata-collector) |
| Validated true claims | **11 / 15** (~73 %) | ~14 / 15 (already verified earlier) |
| Validated FALSE claims | **4 / 15** (C4 double-putconn, C6 logger-order, C9 Temporal-no-retry, C12 api_server-leak — code is actually correct) | ~1 (none material) |
| Scraper-internal coverage | **Excellent** — finds bugs Plan-B never inspected | Surface-level — `aiohttp` lifetime, retry policy, probes |
| Probe / lifecycle / SIGTERM coverage | **Missing** | Strong (S3, S9, S15) |
| Workflow `continue_as_new` | **Caught** (PR-3) | **MISSED** — silent killer for >40K-event jobs |
| Cross-service breadth | **Missing** | Strong |

**Decision:** **Integrate.** Adopt Plan-B as the structural skeleton (broad, machine-followable, has risk register & rollout sequence). **Replace scraper section** with Plan-A's deeper scraper findings. **Drop the 4 invalid claims.** **Add 5 critic-flagged gaps** that neither plan caught.

If we **must pick only one**, the answer is at the bottom of this file (§"If you can only pick one").

---

## Validation receipts (what we actually checked)

Subagent-validated against `/Users/tchen7/MyProjects/atlassian_packages/gcp_kitt/scraper/temporal-pg-redis/`:

| Plan-A claim | Result | Evidence |
|---|---|---|
| C1: `workflow.py` has zero `continue_as_new` | ✅ CONFIRMED | grep returned 0 hits |
| C2: `worker.yaml:63` — `processingBatchSize: 100` | ✅ CONFIRMED | exact match |
| C3: `workflow.py:441` — comment "Reduced … from 25 to 10" | ✅ CONFIRMED | exact match |
| C4: `db_utils.py` double-`putconn` bug at lines 122/137 | ❌ **REFUTED** | finally block has `if conn:` guard; the line-122 `putconn` is followed by `raise`, finally then sees no conn |
| C5: `db_utils.py:118` — f-string SQL `cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")` | ✅ CONFIRMED | f-string with int literal — low SQLi risk in practice but bad-practice |
| C6: `worker.py:55` — logger used before line 57 init | ❌ **REFUTED** | line 55 is inside an `except ImportError` for the `kubernetes` package; logger is defined at module load time before that except can fire |
| C7: `worker.py:786` — bare `except: pass` | ✅ CONFIRMED | exact match |
| C8: `worker.py:1230` — health check always healthy | ✅ CONFIRMED | returns `{"status":"healthy"}` unconditionally |
| C9: `worker.py:1329` — Temporal connect with NO retry | ❌ **REFUTED** | `Client.connect()` is wrapped in try/except with structured error handling; no explicit `RetryPolicy` but reconnect via outer loop exists |
| C10: `redis_utils.py` — `max_connections: 10` | ✅ CONFIRMED | line 49 |
| C11: `db_utils.py` — `POOL_MAX_CONN=10` + no `getconn()` timeout | ✅ CONFIRMED | line 31 + line 113 |
| C12: `api_server.py` creates new Temporal client per request | ❌ **REFUTED** | grep found zero `Client(...)` constructions per request |
| C13: `redis_utils.py:16` — `getLogger()` (root logger pollution) | ✅ CONFIRMED | exact match |
| C14: `db_utils.py:21-24` — forces WARNING level override | ✅ CONFIRMED | exact match |
| C15: `workflow.py:244` — hardcoded `kubernetes_namespace = "dtaske"` | ✅ CONFIRMED | exact match |

**The 4 REFUTED claims are critical** — Plan-A would have shipped fixes for non-existent bugs, and the code reviewer would have rejected them. The integrated plan **drops** them.

---

## What Plan-B (mine) MISSED that Plan-A caught (must add)

| # | Finding | File:line | Severity | Origin |
|---|---|---|---|---|
| **N1** | Scraper workflow has NO `continue_as_new` → workflows hit 50K Temporal history limit and get hard-killed after ~4–5 h | `src/workflow.py` (no occurrence) | **CRITICAL** | [A] |
| **N2** | `worker.yaml` has `processingBatchSize: 100` but workflow code says "reduced from 25 to 10 to prevent timeouts" → orphaned activity accumulation | `values/worker.yaml:63` vs `src/workflow.py:441` | **CRITICAL** | [A] |
| **N3** | Health endpoint **always returns healthy** → kubelet never restarts truly broken pods (worse than no probe) | `src/worker.py:1230` | **HIGH** | [A] |
| **N4** | `db_utils.py:118` uses f-string SQL — bad practice (low SQLi risk because integer, but reviewer rejection guaranteed) | `src/db_utils.py:118` | **MED** | [A] |
| **N5** | `worker.py:786` bare `except:` swallows `SystemExit`/`KeyboardInterrupt` — masks shutdown signals (relevant to S9 SIGTERM work) | `src/worker.py:786` | **HIGH** (interacts with S9) | [A] |
| **N6** | `workflow.py:244` hardcoded `kubernetes_namespace = "dtaske"` → not portable, fails in non-prod clusters | `src/workflow.py:244` | **MED** | [A] |
| **N7** | `db_utils.py:113` `pool.getconn()` blocks **indefinitely** when pool exhausted — silent deadlock under load | `src/db_utils.py:113` | **HIGH** | [A] |
| **N8** | `redis_utils.py:49` `max_connections: 10` is too low for scraper's actual concurrency (5–50 activities × pipelines) | `src/redis_utils.py:49` | **HIGH** | [A] |
| **N9** | `redis_utils.py:16` uses root logger (`getLogger()` no name) — log routing breaks; floods other modules | `src/redis_utils.py:16` | **LOW** | [A] |
| **N10** | `db_utils.py:21-24` forces WARNING level override — overrides operator's `LOG_LEVEL` env var | `src/db_utils.py:21-24` | **LOW** | [A] |

## What Plan-A MISSED that Plan-B caught (must keep)

The 14 multi-service stability fixes from `07_STABILITY_PLAN.md` (S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15). Plan-A is **scraper-only** and silent on every other binary.

## What BOTH plans MISSED (critic-3 + critic-A gap analysis)

| # | Finding | Why both missed it | Severity |
|---|---|---|---|
| **G1** | `/readyz` semantics for "running" is undefined. A worker stuck in a single 5-min activity is still "running" but cannot accept work. | Plan-B's S15 says "worker.is_running()" without specifying. Plan-A doesn't address probes at all. | **MED** |
| **G2** | Splunk activity retry policy in kit-runbooks may still be 60s **after** S12 lowers client timeout to 10s → retries fire before circuit-breaker opens | Plan-B's S12 changes one knob but not the second one | **MED** |
| **G3** | DB connection-pool `pool_recycle` and `pool_pre_ping` not specified for scraper PG pool (long-lived connections die silently behind cloud LB idle-timeout) | Both plans treat pool size only; not pool freshness | **MED** |
| **G4** | Temporal client `connect_timeout` not set explicitly — relies on OS TCP timeout (~2 min). DNS or endpoint changes hang the worker | Plan-B's S13 caps reconnect attempts but not the per-attempt timeout | **MED** |
| **G5** | No `idempotency_key` audit on activities. With S11's bounded retries, an activity that does I/O (DB write, Kinesis put) **must** be idempotent or retries will produce duplicates | Both plans treat retry-count without semantic safety | **MED** |

---

## INTEGRATED EPIC P0-S+ — final fix list (S1–S15 + N1–N10 + G1–G5 = 30 items)

> Naming convention: keep S1–S15 stable (already in `07_STABILITY_PLAN.md`); add **N-series** for scraper-deep adds (Plan-A); add **G-series** for cross-cutting gaps (critic-flagged).
>
> **All fixes must be elegant and idiomatic — no probe-loosening, no try/except: pass, no hardcoded retries, no raising memory limits to mask leaks.**

### Tier-0 — STOP THE BLEEDING (Week 1, days 1-3, ship in this order)

| ID | Origin | Title | Files (with file:line) | LoC | Why first |
|----|--------|-------|------------------------|-----|-----------|
| **N2** | [A] | Restore `processingBatchSize: 10`, `maxUrlsPerFetch: 50`, `maxConcurrentActivities: 10` | `scraper/temporal-pg-redis/values/worker.yaml:49,56,63` | ~10 | Most likely **active** cause of scraper crashes; pure config rollback |
| **N3** | [A+B] | Real health check (Redis + PG ping) **and** split into `/livez` (cheap) + `/readyz` (deep, with G1 stuck-thread check) | `scraper/temporal-pg-redis/src/worker.py:1230` | ~80 | Until probe is real, S15 work is unmeasurable |
| **S1** | [B] | Remove `log.Fatal` from `k8s-metadata-collector` collection loop; add backoff + counter | `k8s-metadata-collector/main.go:123,128` | ~120 | CrashLoopBackoff on every apiserver hiccup |
| **S5** | [B] | iam-sidecar: never `log.Fatal` in `ServeHTTP`; IMDS retry | `iam-sidecar/iam-sidecar.go:159-160, 207-326` | ~50 | One bad creds object kills the pod |
| **S2** | [B] | Surface `w.Run()` failure on kitt-runbooks worker | `kitt-runbooks/cmd/worker/main.go:105-109` | ~80 | Silent worker death (worse than crash) |

### Tier-1 — REMOVE RECURRENCE (Week 1, days 4-7)

| ID | Origin | Title | Files | LoC |
|----|--------|-------|-------|-----|
| **N1** | [A] | Implement `workflow.continue_as_new()` after configurable history threshold (default 40 000 events) — preserve job state via Redis source-of-truth | `scraper/temporal-pg-redis/src/workflow.py` (new logic at ~line 376 in `process_urls_as_activities` loop, plus `run()` at line 507 to handle continue-as-new entry path) | ~150 |
| **N7** | [A] | Add `getconn()` timeout (10 s) + connection-validation-on-checkout for scraper PG pool | `scraper/temporal-pg-redis/src/db_utils.py:113` | ~60 |
| **N8** | [A] | Make Redis `max_connections` configurable (`REDIS_MAX_CONNECTIONS` env, default 50) — sized to `maxConcurrentActivities × 2 × pipeline_depth` | `scraper/temporal-pg-redis/src/redis_utils.py:49` | ~20 |
| **G3** | [critic] | Add `pool_recycle=3600s` + `pool_pre_ping` (or psycopg equivalent: `tcp_user_timeout`, periodic `SELECT 1` keepalive) to scraper PG pool — survives cloud LB idle-timeout | `scraper/temporal-pg-redis/src/db_utils.py` | ~40 |
| **N5** | [A+B] | Replace bare `except: pass` (`worker.py:786`) with `except Exception:` + structured debug log; explicitly **let** `SystemExit`/`KeyboardInterrupt` propagate so S9 SIGTERM works | `scraper/temporal-pg-redis/src/worker.py:786` | ~10 |
| **S9** | [B] | Scraper SIGTERM handler + graceful drain + preStop — depends on N5 | `scraper/temporal-pg-redis/src/worker.py` main entrypoint; `charts/scraper-worker/templates/deployment.yaml` | ~80 |
| **S10** | [B] | Module-level `aiohttp.ClientSession` + per-request `ClientTimeout` (total=30, connect=10, sock_read=20) | `scraper/temporal-pg-redis/src/worker.py:311-324, 581` | ~100 |
| **S11** | [B] | `maximum_attempts=5` + `non_retryable_error_types` + workflow-level circuit | `scraper/temporal-pg-redis/src/workflow.py:125-180` | ~120 |
| **G5** | [critic] | Idempotency audit pass: every retry-eligible activity must either be (a) pure read, (b) idempotent write (SADD, INSERT … ON CONFLICT), or (c) gated by a Redis `SETNX dedupe-key` | `scraper/temporal-pg-redis/src/worker.py` activities | audit + ~80 |
| **S7** | [B] | ForgeApp nil-deref guard on `*deployment.Spec.Replicas` + recover() middleware | `forge_containers/controllers/forgeapp_controller.go:261, 291-298` | ~40 |
| **S8** | [B] | ForgeApp: replace `time.Sleep` in Reconcile with `RequeueAfter` | `forge_containers/controllers/forgeapp_controller.go:604-628` | ~40 |
| **S6** | [B] | ASI: replace `panic(err)` + `log.Fatalf` in business code with returned errors | `asi/cmd/main.go:259,263,267,299,310,315`; `asi/internal/asicore/asi.go:105,111` | ~150 |
| **S4** | [B] | DTE worker: don't `os.Exit(1)` from goroutine; `srv.Shutdown(ctx)` | `amp/distributed-worker/main.go:791-794` (mirror in `helmfile/dte/`) | ~120 |

### Tier-2 — HARDEN (Week 2)

| ID | Origin | Title | Files | LoC |
|----|--------|-------|-------|-----|
| **S3** | [B] | kitt-runbooks worker probes/preStop/grace (currently NONE defined) | `kitt-runbooks/worker-values.yaml`; `cmd/worker/main.go` for `/livez` `/readyz` | ~85 |
| **S15** | [B+critic G1] | Scraper probe realignment with **proper `/readyz` semantics**: 503 if any worker thread executing same activity > 3× its timeout (uses Temporal SDK active-activity counter) | `scraper/temporal-pg-redis/values/worker.yaml:177-184`; `charts/scraper-worker/templates/deployment.yaml:144-159`; `worker.py` | ~90 |
| **S12** | [B+critic G2] | Splunk client 60s → 10s **AND** activity retry policy `MaxAttempts=3, MaxInterval=5s` (must be < client timeout) + `sony/gobreaker` circuit | `kitt-runbooks/internal/splunk/client.go:55`; activity files using Splunk | ~100 |
| **S13** | [B+critic G4] | Temporal worker connect: exp backoff + jitter + max-elapsed=5min + **explicit `connect_timeout=10s`** per attempt | `kitt-runbooks/cmd/worker/main.go:65-82` | ~80 |
| **N4** | [A] | Replace f-string SQL with parameterised query | `scraper/temporal-pg-redis/src/db_utils.py:118` | ~5 |
| **N6** | [A] | Replace hardcoded `"dtaske"` with `KUBERNETES_NAMESPACE` env var (default `"dtaske"` for back-compat) | `scraper/temporal-pg-redis/src/workflow.py:244` | ~10 |
| **N9** | [A] | `redis_utils.py:16` — `getLogger()` → `getLogger(__name__)` | `scraper/temporal-pg-redis/src/redis_utils.py:16` | ~1 |
| **N10** | [A] | Remove forced WARNING-level override; respect `LOG_LEVEL` env | `scraper/temporal-pg-redis/src/db_utils.py:21-24` | ~5 |

### Tier-3 — TLS + final hardening (Week 3, canary required)

| ID | Origin | Title | Files | LoC | Risk |
|----|--------|-------|-------|-----|------|
| **S14** | [B] | Replace TLS `InsecureSkipVerify=true` with proper CA bundle | `kitt-runbooks/cmd/worker/main.go:46-58`; DTE worker | ~80 | MED — mandatory ≥48h canary |

### EXPLICITLY DROPPED items (validation showed they're false positives)

| ID | Original claim | Why dropped |
|----|---------------|-------------|
| ~~Plan-A C4~~ | Double-`putconn` in `db_utils.py:122/137` | REFUTED — `finally` has `if conn:` guard; first putconn is followed by `raise`, finally sees no conn. Code is correct. |
| ~~Plan-A C6~~ | Logger used at `worker.py:55` before line 57 init | REFUTED — line 55 is inside `except ImportError`; logger module-level definition fires first |
| ~~Plan-A C9~~ | Temporal connect at `worker.py:1329` has no retry | PARTIAL/REFUTED — `Client.connect()` is wrapped in try/except with reconnect; we still want **S13**'s explicit backoff cap, but Plan-A's framing is wrong |
| ~~Plan-A C12~~ | api_server creates new Temporal client per request | REFUTED — grep returned no per-request `Client()` constructions |

---

## Updated rollout sequence (1–2 PRs/day, ~12 working days end-to-end)

| Day | PR | Why this order |
|---|---|---|
| 1 | N2 (config), S1 (metadata Fatal) | Highest visibility wins; pure config rollback + 1 file change |
| 2 | N3 (real health), S5 (iam-sidecar Fatal) | Health-check fix unblocks measurement of all later work |
| 3 | S2 (worker silent death), S7 (forgeapp nil-deref) | Cheap, atomic, zero-risk |
| 4 | N1 (continue_as_new), S4 (DTE os.Exit) | Highest scraper-stability lift |
| 5 | N7 (DB getconn timeout), N8 (Redis max_conns), G3 (pool_recycle) | Connection-pool hardening as a single coherent PR |
| 6 | N5 (bare except), S9 (SIGTERM) | N5 is prerequisite for S9 |
| 7 | S10 (aiohttp), S11 (retry+circuit), G5 (idempotency audit) | Activity-level safety as a coherent block |
| 8 | S6 (ASI panic-storm), S8 (forgeapp Sleep) | Independent, parallelisable |
| 9 | S3 (runbooks probes), S15 (scraper probes with G1 stuck-thread) | After all worker-internals are correct |
| 10 | S12 (Splunk timeout + G2 retry), S13 (Temporal backoff + G4 connect_timeout) | After probes so we can measure |
| 11 | N4 (SQL), N6 (hardcoded ns), N9 (logger), N10 (log level) | "Lint" PRs; cleanup |
| 12 | S14 (TLS InsecureSkipVerify removal) | LAST — canary ≥48 h; risk-managed solo |

**Total: ~30 fixes in 12 working days, all elegant/idiomatic, all <250 LoC per PR.**

---

## Acceptance criteria (whole integrated epic)

Inherits everything from `07_STABILITY_PLAN.md` §"Acceptance criteria", **plus**:

- **N1 (continue_as_new):** A 10 000-URL job spans ≤ 5 workflow-history chunks, not 1; no Temporal `WORKFLOW_TASK_FAILED: history_size_exceeded` events.
- **N2 (config):** No `"Activities still running after Xs, continuing..."` log lines in steady-state; orphaned-activity-count = 0 in Temporal UI.
- **N3 (real health):** Killing PG on canary causes `/readyz` to return 503 within 10 s and pod to be removed from service endpoints.
- **N7+G3 (DB pool):** Chaos test pulls 100 connections in parallel — `pool_acquire_timeout_total` increments and the 101st caller fails fast (10 s), not hangs forever.
- **G1 (stuck-thread `/readyz`):** Inject a 30-min activity (3× the 10-min URL_TIMEOUT) — `/readyz` returns 503 even though the worker process is alive.
- **G5 (idempotency):** Replay every activity twice in chaos suite — `visited_urls` count and `scraper_results` rows are identical to single-run baseline.

---

## Risk register additions (extending `05_RISK_AND_HISTORY.md`)

| Risk ID | Description | Linked PR(s) | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| **R-N1** | `continue_as_new` boundary loses in-flight signals/state | N1 | M | H | Use Redis work-queue as source of truth (no signals to lose); from-continue branch checks Redis state, not workflow input. Test: N consecutive continues preserve `visited_urls` count. |
| **R-N2** | Reverting `processingBatchSize: 100→10` cuts apparent throughput | N2 | H (intentional) | L | This restores the throughput the *code* was designed for; existing high value was the bug. Capacity gain comes back from S10/N7/N8/G3. |
| **R-N3** | Real health check catches a transient Redis blip → false pod-restart cascade | N3 | M | M | Use 5-second cache for downstream-ping result; `/livez` (always-200 if process alive) is unaffected; only `/readyz` flaps. PR description requires alert: "if `/readyz` flaps >5 times in 5 min on canary, roll back the readiness change". |
| **R-N7** | DB getconn 10-s timeout causes activity to fail mid-iteration | N7 | M | L | Activity returns retryable error; Temporal retries (with S11's bounded retry); strictly better than today's silent infinite hang. |
| **R-G3** | `pool_recycle: 3600` recycles a connection mid-statement | G3 | L | L | psycopg2 `pool_recycle` only affects newly-checked-out connections, not in-flight; same idiom is used by SQLAlchemy at scale. |
| **R-G5** | Idempotency audit produces a long PR; reviewers fatigue | G5 | M | L | Split per-activity (1 PR per activity); each PR documents the idempotency proof inline. |

---

## H-SERIES — `helmfile/` package deep-dive (NEW, added 2026-05-08, second pass)

> **Trigger**: User asked us to "double check you have dived really deep into helmfile package". Previous helmfile section was based on 1 subagent + grep; this section is based on **4 parallel deep-dive subagents** (cassandra/temporal/ES, DTE-drift, operational-security, misc-subdirs) + direct evidence.
>
> Drift quantified: `helmfile/dte/distributed-worker/{main,helpers,cluster_db}.go` vs `amp/distributed-worker/*` — **93 lines diff in main.go (TLS config absent in helmfile copy), 26 lines in helpers.go, 474 lines in cluster_db.go**. The drift is far worse than 02-A1 estimated.

### H-SERIES findings — 22 items, evidence-grounded

> Format: `ID | severity | file:line | crash-link (YES/AMP/NO) | one-line root cause`. Full fix in §"H-series fix specifications" below. **AMP** = amplifier (turns small failures into big ones).

#### Tier-0 — ACTIVE FIRES (causing crashes/instability **right now**)

| ID | Sev | File:line | Crash | Root cause |
|---|---|---|---|---|
| **H1** | CRIT | `helmfile/temporal-values.yaml:35` (per agent: `server.replicaCount: 1`) | YES | **Temporal frontend is a single replica** — single-pod failure = entire workflow plane down |
| **H2** | CRIT | `helmfile/temporal-manifests/temporal-server.yaml` & `helmfile/temporal-values.yaml` (zero probes/PDBs found) | YES | **No livenessProbe, readinessProbe, or PodDisruptionBudget** on Temporal — kubelet cannot detect a hung frontend; node drains take it down |
| **H3** | CRIT | `helmfile/KEDA_TEMPORAL_CONNECTION_ISSUE.md` (full doc; in-tree firefighting receipt) | YES | KEDA→Temporal **gRPC `connection refused` + `context deadline exceeded`** while TCP works → autoscaling broken → backlog → user-visible "service unstable". Documented in-tree as actively firing; multiple workarounds tried, none permanent |
| **H4** | CRIT | `helmfile/dte/distributed-worker/main.go:750` | YES | `os.Exit(1)` inside HTTP-listener goroutine — port-bind glitch kills entire pod mid-activity (mirror of S4) |
| **H5** | CRIT | `helmfile/dte/distributed-worker/main.go:659, 673` | YES | 2 more `os.Exit(1)` on Temporal client init — every reconnect blip kills the worker |
| **H6** | CRIT | `helmfile/dte/distributed-client/main.go:116, 160` | YES (when invoked) | `os.Exit(1)` in client init + HTTP server goroutine — caller workflows fail |
| **H7** | HIGH | `helmfile/temporal-helloworld/go-web-service/main.go:52, 75`; `worker-web-service/main.go:58, 111` | YES (it IS deployed) | Verified: `helmfile.yaml:442-461` deploys `temporal-helloworld-worker` and `temporal-helloworld-go-web-service` as **production releases**. `log.Fatalf("Unable to create Temporal client")` on first blip; tutorial code in production |
| **H8** | HIGH | `helmfile/dte/charts/dte/values.yaml` (per agent: NO probes/preStop/grace) | YES (during deploys) | DTE worker chart missing `preStop` + `terminationGracePeriodSeconds` — pods killed without draining; activities marked failed; retry storm |

#### Tier-1 — STRUCTURAL HAZARDS that cause OR amplify crashes

| ID | Sev | File:line | Crash | Root cause |
|---|---|---|---|---|
| **H9** | HIGH | `helmfile/elasticsearch-shard-allocation-fix.md` (in-tree firefighting receipt) + `fix-unassigned-shards.sh` | AMP | ES unassigned-shards have happened repeatedly; documented fix is `index.number_of_replicas: 0` for the 3-node cluster but not enforced via index template |
| **H10** | HIGH | `helmfile/cassandra-exporter-sidecar-fix.yaml` + `apply-and-verify-cassandra-exporter.sh` (existence is the smell) | AMP | Cassandra exporter sidecar repeatedly broken; "fix" yaml + "verify" script = unresolved firefighting; observability hole during incidents |
| **H11** | HIGH | `helmfile/dte/distributed-worker/main.go` (TLS config 93 lines diff vs `amp/*` — agent confirmed `crypto/tls` and `crypto/x509` imports absent) | AMP / latent | **`helmfile/dte` Go binary lacks TLS code entirely**; `amp/*` has full `tls.Config + x509.CertPool` setup. If `helmfile/dte` binary is shipped to prod without TLS, every Temporal connection is plaintext or fails handshake — would explain part of H3 (KEDA gRPC failures may share root cause: TLS misconfig at connection layer) |
| **H12** | HIGH | `helmfile/helmfile.yaml:34, 207, 225, 258` + `values-production.yaml:10, 32` + `values-eks.yaml:10, 29` + `values-development.yaml:10, 28` | NO (security) | **Plaintext passwords hardcoded** for `temporal-postgres-password`, `temporal-redis-password`, `temporal-eks-password`, `temporal-dev-password`. `values-production.yaml:32` has the comment *"Should be set via secret in real deployment"* — but isn't. Live credential exposure |
| **H13** | HIGH | `helmfile/delete-all-temporal-data-job.yaml:10` (`backoffLimit: 2`, `restartPolicy: Never`, hardcoded creds in plaintext) | YES (if mis-applied) | **Destructive `DROP KEYSPACE`** with no approval gate, no dry-run, hardcoded creds, retries twice on failure. One mis-applied helmfile = full Cassandra data loss. The `backoffLimit: 2` means a fat-fingered apply has a SECOND attempt automatically |
| **H14** | MED | `helmfile/recreate-cassandra-statefulset-with-vac-job.yaml`, `helmfile/fix-cassandra-downtime-job.yaml`, `helmfile/delete-old-indices.sh` | NO (latent) | Multiple destructive jobs without dry-run defaults; `fix-cassandra-downtime-job.yaml:77-79` documents that VolumeClaimTemplates can't be added to existing StatefulSets → "downtime unavoidable" |
| **H15** | MED | `helmfile/dte/distributed-worker/main.go` (cluster_db.go drift 474 LoC) | AMP | `cluster_db.go` between the two copies differs by **474 LoC** — far beyond §02-A1's "~100 LoC" estimate. Any DB-related stability fix that ships to one copy will silently miss the other |
| **H16** | MED | `helmfile/dte/distributed-worker/main.go:541-542 + 721, 747` | AMP | `ctx.Done()` exists in select but goroutine fan-out at lines 721, 747 has no semaphore/WaitGroup cap — at large fanout, OOMKill |
| **H17** | MED | `helmfile/dte/distributed-client/main.go:109` | AMP | Hardcoded fallback `"localhost:7233"` masks misconfig errors — silent dev-vs-prod mismatch |
| **H18** | MED | `helmfile/values-development.yaml`, `values-eks.yaml`, `values-production.yaml` | NO (operational) | Multiple environment overlays exist but no test that values-production has stricter limits than values-development; drift is silent |
| **H19** | MED | `helmfile/all-egress.yaml`, `all-ingress.yaml`, `allow-all.yaml`, `deny-all.yaml` | NO (security) | Cilium NetworkPolicy *templates* sit in production tree; no helmfile env predicate gating them. One accidental `helmfile apply -e dev` from prod kubeconfig = cluster wide-open |
| **H20** | LOW | `helmfile/temporal-manifests/temporal-server.yaml` | NO (operational) | Directory exists but **no release in `helmfile.yaml` references it** — orphaned config; either dead code or installed via another path → unclear source-of-truth |
| **H21** | LOW | `helmfile/python-app/docker-compose.yml` | NO (housekeeping) | Abandoned dev artifact; not referenced by any helmfile release |
| **H22** | LOW | `helmfile/DEPLOYMENT_SUMMARY.md:38-39` | NO (security/leak) | Grafana admin password + internal hostnames hardcoded in a tracked markdown — leaked into git history |

#### Items the agents flagged but I'm DEMOTING after critical thinking

> Critical thinking: not every grep hit is a real issue. These are findings the agents reported that I am **dropping** or **caveating** before they go in the plan.

| Agent claim | My judgement | Rationale |
|---|---|---|
| `s3-crud-api/values.yaml` no probes (agent FINDING_006) | **KEEP as LOW** | Real, but s3-crud-api blast radius is small; not a stability priority |
| `aws-accounts.json in tree` (agent FINDING_006) | **VERIFY before acting** | Agent didn't confirm whether file contains secrets or just account IDs (latter is fine in many shops). Need to read the file before raising severity |
| `gatekeeper-opa.yaml` "policies have gaps" | **DROP** — not actionable without specifying which policies are missing | Agent didn't enumerate gaps |
| `latest` image tags | **CONFIRMED ABSENT** by agent's grep — good practice already in place | No action needed |
| Wildcard RBAC | **CONFIRMED ABSENT** | No action needed |

---

### H-series fix specifications (elegant, idiomatic — no hacks)

#### Tier-0 fixes (ship in week 1, in this order)

**H1 — Temporal frontend HA** (`helmfile/temporal-values.yaml`)
- Change `server.replicaCount: 1` → `3`. Add anti-affinity (`podAntiAffinity` on `app.kubernetes.io/name: temporal`).
- Add `PodDisruptionBudget` `minAvailable: 2`.
- **Risk**: Cassandra/PG must support 3 frontend connections; verify connection-pool sizing on persistence backend before rollout.
- **Acceptance**: `kubectl drain` any node → no Temporal API outage.
- LoC: ~30 yaml. Canary on dev environment first.

**H2 — Temporal probes + lifecycle** (same file)
- Add `livenessProbe` (`tcpSocket: 7233`, `failureThreshold: 6`, `periodSeconds: 10`).
- Add `readinessProbe` (Temporal `/health` if exposed; else gRPC health probe via `grpc_health_probe`).
- Add `terminationGracePeriodSeconds: 60`.
- LoC: ~25 yaml.
- **Hard prereq for H1**: without H2, scaling to 3 doesn't help if kubelet can't detect a stuck frontend.

**H3 — KEDA → Temporal connection** (proper fix, not hack)
- **Root cause is most likely a combination**: (a) KEDA Temporal scaler version mismatch with Temporal v0.65.0 server; (b) gRPC keepalive defaults too aggressive for the cross-namespace path; (c) connection-pool not bounded.
- **Elegant fix sequence** (in priority order):
  1. **Pin KEDA ≥2.13.x** with the patched temporal scaler (`keda-2.13.1` released the gRPC keepalive fix).
  2. Add explicit `metricType: AverageValue` and `unsafeSsl: false` (current ScaledObject is implicit).
  3. Configure Temporal frontend with explicit `frontend.rps` rate-limits **above** KEDA's poll rate (KEDA default = once per `pollingInterval`; default 30s; ensure frontend RPS ≥ this).
  4. Add `initialCooldownPeriod` to ScaledObject so KEDA doesn't poll during Temporal startup.
  5. Add monitoring: `keda_temporal_scaler_metrics_value` alert on `unable_to_fetch` errors.
- **Critical correctness check**: do **NOT** "fix" by adding retries blindly — that masks the real KEDA bug. Pin the version.
- LoC: ~10 yaml + KEDA chart pin. **Mandatory canary** ≥48h on dev.
- **Cross-link**: this also unblocks the work-queue scaling that the scraper depends on.

**H4 — DTE worker `os.Exit(1)` in goroutine** (mirror of S4)
- Same fix pattern as `08_INTEGRATED_PLAN.md` §S4: wrap HTTP listener in `*http.Server`, surface error via `chan error`, `srv.Shutdown(ctx)` on signal.
- **Apply to BOTH copies** in same PR (CI fence PR-PHASE0-04 enforces).
- LoC: ~120 across both copies (deduplicated when A1 consolidation lands).

**H5 — DTE worker startup `os.Exit(1)`**
- `os.Exit(1)` on Temporal client init failure (lines 659, 673) is **acceptable for true startup misconfig** (kubelet pod-restart-policy + exp backoff handles it).
- But: prepend a clear, structured error log so `kubectl describe pod` shows the cause — not just "exit code 1".
- Use `slog.Error("temporal client init failed", "endpoint", endpoint, "error", err)` then `os.Exit(1)`.
- LoC: ~10. Trivial PR.

**H6 — DTE client `os.Exit(1)`**
- Same fix as H5 for line 116; same fix as H4 for line 160 (HTTP server goroutine).
- LoC: ~30.

**H7 — `temporal-helloworld` `log.Fatalf` (or remove from prod entirely)**
- **First decision**: should `temporal-helloworld` be in prod at all? Per agent FINDING_1: "tutorial code clogs prod". Two options:
  - (A) **Remove from `helmfile.yaml:442-461`** — keep the chart but don't deploy. Best option if it's truly a tutorial.
  - (B) If it's actually used (e.g., as a healthcheck canary), then apply the same `log.Fatalf` → returned error pattern as S6 (ASI fix); add probes; promote it to a first-class binary.
- **Need 1-question clarification from team** before shipping. Default to (A) (remove) if no answer in 24h.
- LoC: 5 (helmfile delete) OR ~80 (proper rewrite).

**H8 — DTE worker chart preStop + grace**
- Add to `helmfile/dte/charts/dte/values.yaml` (or templates):
  ```yaml
  terminationGracePeriodSeconds: 60   # ≥ activity StartToCloseTimeout
  lifecycle:
    preStop:
      exec:
        command: ["/bin/sh", "-c", "sleep 15"]
  ```
- **Hard correctness rule**: `terminationGracePeriodSeconds ≥ longest activity timeout`. If activities can run 5 min, grace ≥ 300 s.
- LoC: ~15 yaml.

#### Tier-1 fixes (week 2)

**H9 — Elasticsearch ILM + replica config** (proper, not patch)
- Add index template applied at startup that sets `number_of_replicas: 0` for the 3-node cluster (proper for that topology).
- Define ILM policy: hot → warm at 7 days → delete at 30 days.
- Replace `fix-unassigned-shards.sh` with an automated job that runs `_cluster/reroute?retry_failed=true` on a schedule.
- **Then delete** `elasticsearch-shard-allocation-fix.md` and the `*fix*` yaml — the fix is now codified.
- LoC: ~120.

**H10 — Cassandra exporter sidecar — fold the patch in** (proper, not patch-yaml)
- Move `cassandra-exporter-sidecar-fix.yaml` content into the StatefulSet template.
- Add an `initContainer` validator: `chmod +x ... && nodetool status | grep -q UN` — fail-fast if Cassandra not Up-Normal.
- **Then delete** the patch yaml + verify script.
- LoC: ~80.

**H11 — DTE worker TLS parity**
- Backport `crypto/tls + crypto/x509 + x509.CertPool` from `amp/distributed-worker/main.go:665-700` to `helmfile/dte/distributed-worker/main.go`.
- Use `pkg/clusterauth` shared module (per §06 OOB-05) so this never drifts again.
- Couples with **S14**: same TLS proper-CA work; both copies must use the system CA bundle, not `InsecureSkipVerify`.
- LoC: ~80 + tests.

**H12 — Plaintext passwords → Secrets**
- Move every `*-password: "..."` literal in `helmfile.yaml`, `values-{production,eks,development}.yaml` to `valueFrom.secretKeyRef`.
- Use external-secrets or sealed-secrets operator.
- **Pre-rotation** required: any password committed to git is compromised; rotate during the same change window.
- LoC: ~60 yaml + Secret/SealedSecret manifests.

**H13 — Destructive job hardening**
- Add to `delete-all-temporal-data-job.yaml`:
  - `backoffLimit: 0` (NOT 2) — one fat-finger should not auto-retry destructive ops.
  - Manual `--from=cronjob/...` pattern OR pre-run `requires-confirmation` ConfigMap check.
  - OPA Gatekeeper policy: deny `Job` create if name matches `delete-*` and label `confirmed-by: <user>` is absent.
- Same hardening for `recreate-cassandra-statefulset-with-vac-job.yaml`, `delete-old-indices.sh` (`--dry-run` default; require `--force`).
- LoC: ~40 yaml + 1 OPA policy.

**H14 — Cassandra destructive-job lifecycle**
- Same as H13 pattern for: `recreate-cassandra-statefulset-with-vac-job.yaml`, `fix-cassandra-downtime-job.yaml`, `enrichment-job-simple-fix.yaml` (all retain destructive verbs).
- For `fix-cassandra-downtime-job.yaml`: add a snapshot step (`nodetool snapshot`) **before** the recreate, so even a misfire is recoverable.

**H15 — Cluster_db.go drift (474 LoC)**
- Drift is too large to merge mechanically. Run `diff -u` and write a **3-PR sequence**:
  1. Lint pass on each copy independently (no behaviour change).
  2. Pick the better impl per function; merge into shared `pkg/clusterauth` (see §06 OOB-05).
  3. Cut over both binaries to import shared package; delete the duplicates.
- This is a §06 strategic refactor item; promoted to Tier-1 in the H-series because the magnitude (474 LoC) means **any S-series fix touching cluster_db.go will silently miss one copy**.
- LoC: ~600 over 3 PRs.

**H16 — DTE goroutine fan-out cap**
- Same fix pattern as §02-A4: `golang.org/x/sync/semaphore` cap = `min(20, runtime.NumCPU()*4)`.
- LoC: ~40.

**H17 — Hardcoded `localhost:7233` fallback**
- Remove the fallback. If `TEMPORAL_HOSTPORT` env is unset → `os.Exit(1)` with clear error. (Distinct from S2's silent worker death — this is startup misconfig, fail-fast is correct.)
- LoC: ~5.

#### Tier-2 fixes (week 3)

**H18 — Environment-overlay test**
- Add a `pre-commit` script: `helmfile -e {dev,prod,eks} template > /dev/null` and assert `prod` has ≥dev resource limits, ≥dev replica counts.
- LoC: ~30 lines bash.

**H19 — Move hazardous NetworkPolicies out of prod tree**
- Move `allow-all.yaml`, `all-egress.yaml`, `all-ingress.yaml` to `helmfile/dev-tools/` subdir.
- Add a `helmfile.yaml` env predicate: `if eq .Environment "dev"`.
- Add a CI guard: `grep -r "allow-all\.yaml\|all-egress\.yaml" helmfile/values-production.yaml` MUST be empty.
- LoC: ~10 + file moves.

**H20 — Resolve orphaned `temporal-manifests/`**
- Either reference it from `helmfile.yaml` (and document why it exists alongside the temporal helm chart) or delete it.
- Decision needed from infra owner.

**H21 — Delete or relocate `python-app/docker-compose.yml`**
- Move to `dev-tools/` or delete.

**H22 — `DEPLOYMENT_SUMMARY.md` credential leak**
- Rotate the Grafana admin password (compromised — committed to git history).
- Replace the password reference in the doc with `kubectl get secret grafana-admin -o jsonpath=...`.
- Add a `.gitleaks` rule to prevent recurrence.

---

### H-series rollout (1–2 PRs/day, integrates with the existing 12-day plan)

> Slot the H-series in alongside the existing S+N rollout (`08_INTEGRATED_PLAN.md` §"Updated rollout sequence"). Total epic now 12 days → **15 days**.

| Day | NEW H-series PR | Pairs with |
|---|---|---|
| 1 | **H4 + H5** (DTE worker `os.Exit` mirror of S4) — same diff applied to both copies | S4 (Day 4 of S-series) — combine into one PR |
| 1 | **H7** (decision: remove `temporal-helloworld` from prod) | independent |
| 2 | **H8** (DTE chart preStop+grace) | parallel with S3 |
| 3 | **H2** (Temporal probes) | independent — unblocks H1 |
| 4 | **H1** (Temporal HA, replicas: 3) — only after H2 lands and one canary day | independent |
| 5 | **H3** (KEDA pin + ScaledObject hardening) — canary mandatory | independent |
| 6 | **H6** (DTE client `os.Exit`) | parallel with S6 |
| 7 | **H11** (DTE worker TLS parity) | parallel with S14 |
| 8 | **H12** (passwords → Secrets) — must rotate during same window | independent |
| 9 | **H13 + H14** (destructive-job hardening + OPA) | independent |
| 10 | **H9** (ES ILM + replica) | independent |
| 11 | **H10** (Cassandra exporter sidecar fold-in) | independent |
| 12 | **H16** (DTE goroutine cap) | parallel with §02-A4 |
| 13 | **H17, H19, H20, H21, H22** (lint/cleanup PRs) | independent |
| 14 | **H15 part-1** (cluster_db.go drift assessment + lint) | start §06 OOB-05 |
| 15 | **H18** (env-overlay test) | independent |

### H-series acceptance criteria (whole)

- **H1 + H2**: `kubectl drain` any node hosting a Temporal frontend → no API gap.
- **H3**: KEDA `keda_temporal_scaler_metrics_value` alert quiet for ≥48h on canary; HPA scales workers from 1 → 5 → 1 across a load-test cycle.
- **H4–H8**: DTE worker chaos-test (occupy `:8080`, kill Temporal mid-activity) → clean structured shutdown, not `os.Exit`.
- **H12**: `git grep -E '(password|secret|token).*[:=].*"' helmfile/` returns 0 hits.
- **H13–H14**: chaos-test attempts `kubectl apply -f delete-all-temporal-data-job.yaml` → OPA denies; with `confirmed-by` label + `kubectl create job --from=...`, applies cleanly.
- **H19**: `helmfile -e prod template` does NOT include `allow-all` NetworkPolicy.

### H-series risk register

| Risk ID | Description | Linked PR | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| **R-H1** | Temporal `replicaCount: 1 → 3` exhausts Cassandra/PG connection pool | H1 | M | H | Verify pool sizing first; add monitoring before scaling; canary on dev |
| **R-H2** | Adding probes flaps pods if Temporal is currently borderline-unhealthy | H2 | L | M | `failureThreshold: 6` is generous; `tcpSocket` is cheap |
| **R-H3** | KEDA pin breaks an existing `ScaledObject` API | H3 | L | M | Read KEDA 2.13 changelog for breaking changes; canary first |
| **R-H7** | Removing `temporal-helloworld` breaks an undocumented healthcheck | H7 | M | L | Decision must be validated with the team; default to non-removal if uncertain |
| **R-H11** | TLS parity backport breaks `helmfile/dte` Temporal connection | H11 | M | H | Mandatory canary ≥48h; same-PR rollback; coordinate with team that landed `1b1c279` |
| **R-H12** | Password rotation breaks running pods until restart | H12 | H (intentional) | M | Plan a rolling-restart window same as the password rotation |
| **R-H13** | OPA policy blocks legitimate destructive op when SRE actually needs to drop keyspace | H13 | L | L | Doc the bypass: `kubectl label cm/delete-protection confirmed-by=$USER` |
| **R-H15** | `cluster_db.go` drift merge introduces a bug that's in only one copy today | H15 | M | M | 3-PR sequence; each copy lint-pass before merge; full test-suite run |

---

## Cross-references

- The full text of S1–S15 lives in `07_STABILITY_PLAN.md` (do not duplicate here).
- The full code-deltas for N1–N10 are in `/Users/tchen7/.claude/plans/taking-a-deep-look-modular-hopper.md` PR-1, PR-2, PR-3, PR-4 (with the four caveats listed in §"EXPLICITLY DROPPED items").
- This file is the **canonical source of truth** for *what ships*; the other two files are *receipts*.

---

## Updated reading order (for `00_README.md`)

1. `01_GOALS_AND_METRICS.md`
2. **`08_INTEGRATED_PLAN.md`** ← *this file* (start here for the merged plan)
3. `07_STABILITY_PLAN.md` (§07 — multi-service receipts for S-series)
4. `/Users/tchen7/.claude/plans/taking-a-deep-look-modular-hopper.md` (out-of-tree — scraper receipts for N-series, with 4 caveats noted in §"EXPLICITLY DROPPED")
5. `03_PRIORITIZED_PLAN.md` / `04_PR_BREAKDOWN.md` (existing perf plan)
6. `02_FINDINGS_CATALOG.md` / `05_RISK_AND_HISTORY.md` (older receipts)
7. `06_OUT_OF_BOX.md`

---

## If you can only pick ONE plan — answer + reasoning

> **Pick `07_STABILITY_PLAN.md` (Plan-B / mine).**

### Why

1. **Blast-radius**: Plan-B covers 5 binaries (scraper + kitt-runbooks + DTE worker + iam-sidecar + ASI + ForgeApp + k8s-metadata-collector). Plan-A is scraper-only. The user's complaint was *"the service is unstable"* — singular but the underlying systems are plural. Picking Plan-A leaves k8s-metadata-collector's `log.Fatal`-in-loop, iam-sidecar's `log.Fatal`-in-`ServeHTTP`, the silent worker death in kitt-runbooks, and 10 other crash classes in production.
2. **Validation accuracy**: Plan-A had **4/15 false-positive claims** (~27 %) that would have produced PRs the maintainer rejected (or worse, merged and broken working code). Plan-B's claims survived validation cleaner.
3. **Lifecycle/probe coverage**: Plan-B has S3, S9, S15 (probes, SIGTERM, preStop). Plan-A is silent on these; even its scraper-deep work is undermined by lack of probe alignment.
4. **Risk register & rollout sequence**: Plan-B ships with a cross-history risk register and day-by-day rollout. Plan-A has a dependency graph but no historical cross-check.
5. **Machine-followability**: Plan-B has stable PR IDs, branch names, file:line, acceptance criteria, and ties to `02_FINDINGS_CATALOG.md`. Plan-A has prose-heavy descriptions that would need translation.

### What we lose by **not** picking Plan-A

We lose the 10 N-series scraper-deep findings (continue_as_new, batch-size mismatch, real health check, etc.). These are **real** and **important** — but they are *additive* to Plan-B, not substitutes. The integrated plan above adds them on.

### Therefore the *real* recommendation

> **Pick the integrated plan in this file (`08_INTEGRATED_PLAN.md`).** It is Plan-B + Plan-A's verified-true findings + 5 critic-flagged gaps − Plan-A's 4 false-positive claims. Same blast-radius as B, same scraper depth as A, no false-positive PRs, all elegant/idiomatic, no hacks.
