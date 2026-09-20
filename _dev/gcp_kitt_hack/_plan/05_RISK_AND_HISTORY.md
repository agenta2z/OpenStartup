# Risk Register & Recent-History Cross-Check

> **See also:** [`helmfile_enhancement_plan/05_RISK_AND_VALIDATION.md`](helmfile_enhancement_plan/05_RISK_AND_VALIDATION.md) for the helmfile-specific risk register (22 per-PR risks + 6 integration risks R-INT-1..R-INT-6 + 10 refuted parent claims with file:line counter-evidence). The R12, R-S3, R-S4 entries below are mirrored into the child plan as meta-risks against HF-46, HF-01/HF-31, and HF-43.

> Per the user's hard constraints: "double-check if your plan aligns or conflicts with historical development".
> This file maps each risky proposal to the recent commits that touched the same area, asks the "did they remove this on purpose?" question, and gives the mitigation.

---

## 1. The 3-month commit story (what was on the team's mind)

From `git log --since="3 months ago"`:

| Theme | Sample commits | What it tells us |
|---|---|---|
| **Cordon workflow logging** (~15 commits) | `acc71a1`, `8eee6b4`, `b424cf5`, `9d74bb8`, `668009a`, `2c1b56f`, … | The team is actively investigating something via SRE log forensics. Adding ~+400 lines of Info-level logs in 3 months. **Implication:** any Splunk-cost reduction MUST keep the structural fields and offer a "verbose" escape hatch. |
| **slauth-token group caching** | `00170e6 check groups in cached slauth-token`, `1d0fd4f`, `4ff93c1`, `5c4ac31`, `350e6ab`, `7fb7f25` | Group-aware token caching is **already** being added — but at the slauth level. **Implication:** our DTE/kitt-runbooks token cache must use the **same key shape** (`cluster, groups, issuer`) and not duplicate the work; ideally it sits *above* slauth's cache and uses the slauth-cached token. |
| **Group-aware auth provider requests** | `fdfade1 add groups in the auth provider requests`, `f08c3fd`, `ce14db4`, `7d0dcb6` | The HTTP requests now carry group filters. **Implication:** PR-A2's cache key must include the group list. Unit test required. |
| **Detailed errors** | `cf10ed7`, `0ea7b42`, `e215fe6` | Better error logging preferred. **Implication:** any log-level demotion must keep error logs at Info or higher; only diagnostic Info logs go to Debug. |
| **TLS for Temporal** | `b879784`, `5b66c9c` | Temporal client now uses TLS. **Implication:** any HTTP/Transport pooling refactor in `pkg/clusterauth` must NOT bypass TLS; must use system roots. |
| **Test failures fixed** | `3882d61`, `008bc93` | Test pain near the area we're touching. **Implication:** PRs touching `helpers.go` must include unit tests; CI must run on both `amp` and `helmfile/dte` copies. |

---

## 2. Risk register

| Risk ID | Description | Linked PR(s) | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| **R1** | Token cache returns a stale token after a permissions change | PR-A2 | M | H (auth bug) | TTL ≤ 5 min; invalidate on 401; cache-key includes `groups`; unit test that flipping groups returns different token. |
| **R2** | HTTP client pool reuses a TLS connection that has had its server cert rotated | PR-A1, PR-OOB-05 | L | M | `IdleConnTimeout: 90s` is short enough for cert-rotation safety; `MaxConnsPerHost` cap prevents fan-out leak. |
| **R3** | Removing per-call `logAuthenticatedUser` hides an audit signal that someone relies on | PR-A3 | L | M | Async (don't block) — we still emit the log, just off-thread; cache result keyed by `(cluster, user)` for 5 min. Mention in PR description: search Splunk for users of this log line in the last 30 days. |
| **R4** | k8s-metadata-collector schema change breaks downstream Kinesis consumers | PR-B2, PR-B3 | M | H | Schema is **bytes-equivalent**: same `ClusterMetadata` struct, same JSON fields; only how often we send and via which Kinesis API differs. CI: golden-file test that a sample fixture produces identical JSON. |
| **R5** | Sweeper non-retry change leaves pods unlabelled forever in 422 case | PR-C1 | L | L | Already happens today (just hidden by infinite retry); we'll add `sweeper_pod_label_failed_total{reason}` counter so SRE can dashboard it. |
| **R6** | ForgeApp Status coalescing changes the user-facing CR status timeline (intermediate phases no longer visible) | PR-D1 | L | M | Keep emitting Kubernetes **Events** (`r.Recorder.Eventf`) for each step (already in code). Status writes are coalesced; events still fire. The user's `kubectl describe` story is unchanged. |
| **R7** | Kitt-runbooks client cache returns stale credentials after slauth invalidates upstream | PR-E1 | M | H | Cache `expiresAt` derived from token expiry; invalidate on 401; unit test forces 401 → next call must re-fetch. Coordinate cache-bust with the recent `slauth-token` work (read shared lib). |
| **R8** | Log-level demotion in `kitt-runbooks` removes a field someone added 2 weeks ago | PR-R3 | M | M | PR description must enumerate every demoted line and tag the original commit author for review. Also offer `KITT_RUNBOOK_VERBOSE=1` env var to restore Info level. |
| **R9** | Splunk query cache returns stale results during an active incident | PR-P2-02 | M | M | TTL = 10 min; expose `force_refresh` via cli; only cache when `latest=""` (i.e., trailing window). |
| **R10** | Activity-type-specific timeouts collide with downstream Argo retry semantics | PR-P2-03 | L | M | Per-type timeouts must always be ≥ argo job timeout + 60 s buffer; keep a unit test asserting this invariant. |
| **R11** | Parallelising CheckNodeStatus over many cordoned nodes hammers apiserver | PR-R2 | M | M | Cap parallelism at 10; emit `runbook_node_check_concurrency` gauge; backoff if >5% errors. |
| **R12** | Shared `pkg/dte` consolidation introduces a cyclic import | PR-OOB-01..04 | M | H | Add Go `forbidigo` lint that disallows imports going from `pkg/dte/*` back to binaries; 4-PR sequence (add → migrate amp → migrate helmfile → remove dup) so each step is reversible. |

### Risk register — STABILITY EPIC (added 2026-05-08, see `07_STABILITY_PLAN.md`)

| Risk ID | Description | Linked PR(s) | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| **R-S1** | Removing `log.Fatal` from metadata-collector loop hides a real "nothing-works, please page me" condition | PR-STAB-01 | L | M | New health endpoint goes red after `≥ 3 × interval` of all-failure; `kitt_metadata_collect_errors_total` counter + alert >5/min; PagerDuty wires the alert. The signal moves from `pod restart` to `metric red` — strictly better SRE ergonomics. |
| **R-S2** | Surfacing `w.Run()` error and exiting non-zero increases pod restart count short-term | PR-STAB-02 | H (intentional) | L | This is **the desired behaviour** — kubelet restart with exponential backoff is the proper response. Without this, the failure was silent (worse). PR description must call out that 2026-05-08-week restart-rate may temporarily spike before the underlying causes (S4, S6, S13) are addressed. |
| **R-S3** | New liveness probe kills pod during legitimate long activity | PR-STAB-03, PR-STAB-15 | M | H | `/livez` is shallow (atomic-flag check, <10 ms) — by design, never blocks on work. `terminationGracePeriodSeconds = max(activity_timeout)` is a **hard correctness rule** enforced by chart-template assertion. Canary ≥48 h on one cluster before global rollout. |
| **R-S4** | DTE worker graceful shutdown change conflicts with the same code A1 consolidation will rewrite | PR-STAB-04 ↔ A1 | H | L | PR-STAB-04 is structured as a **pure-additive** refactor (introduce `*http.Server`, error chan, select) — A1 will absorb it cleanly. PR-STAB-04 is also mirrored to both `amp/*` and `helmfile/dte/*` (CI fence PR-PHASE0-04 enforces). |
| **R-S5** | iam-sidecar HTTP-500 instead of Fatal masks bad creds object that should never be returned | PR-STAB-05 | L | L | New `iam_sidecar_marshal_errors_total` counter is alerted on; on alert fire, the offending creds object is logged for diff. Behaviour change is strictly safer (single bad request fails, vs. pod kill). |
| **R-S6** | ASI refactor (`run() error`) re-orders initialization → subtle bug | PR-STAB-06 | M | M | Add unit test for `run()` happy + each error path; also add integration test in dev (boot ASI with broken IAM creds → assert clean exit + log message). MED-risk; assigned to ASI maintainer (last-touch on `cmd/main.go`). |
| **R-S7** | ForgeApp `RequeueAfter(1s)` instead of `Sleep(1s)` causes reconcile churn if many ForgeApps stuck on namespace creation | PR-STAB-08 | L | M | `RequeueAfter` is the **standard** controller-runtime idiom; workqueue dedupes per resource. Add `forgeapp_namespace_pending_seconds` histogram to make any pathology visible. |
| **R-S8** | Scraper SIGTERM handler races with KEDA scale-down | PR-STAB-09 | L | M | `preStop: sleep 10` ensures endpoint depopulation before drain begins; `terminationGracePeriodSeconds: 120` covers worker.shutdown(60s); KEDA polling interval is 30 s, so race window is small. e2e test scales scraper from 5→2 mid-activity → assert all activities complete. |
| **R-S9** | Scraper aiohttp singleton breaks per-activity isolation (one activity's slow request blocks another) | PR-STAB-10 | L | L | aiohttp `ClientSession` is **already** designed for concurrent reuse via the underlying connector pool; `limit=100, limit_per_host=10` keeps concurrency bounded. Per-request timeout (`ClientTimeout`) ensures no single request blocks the pool indefinitely. |
| **R-S10** | Bounded retries (`maximum_attempts=5`) cause real transient failures to be dropped | PR-STAB-11 | M | M | Classification of error types is the key risk surface. `non_retryable_error_types` is **opt-in** — defaults to retrying everything 5×. Permanent errors (`ValueError`, `InvalidURL`, etc.) are explicitly listed. PR description enumerates each classification with a unit test; SRE escape hatch via `SCRAPER_MAX_ATTEMPTS` env var. |
| **R-S11** | Splunk circuit breaker opens too eagerly during a transient Splunk outage, hiding the cordon-audit signal | PR-STAB-12 | M | M | Threshold = 5 consecutive failures (not first); open duration = 30 s; circuit-state gauge alerted. SRE can manually close via debug endpoint. Trade-off favoured: 30 s of degraded cordon audit is much better than 60 s × 6 = pod restart cascade across the runbook fleet. |
| **R-S12** | Temporal connect backoff `MaxElapsedTime = 5 min` then exit causes thrashing if Temporal is genuinely down for 30 min | PR-STAB-13 | L | L | This is the **intentional design** — kubelet pod-restart-policy itself has exponential backoff (5 s → 10 s → 20 s → ... → 5 min cap), so process exit + kubelet restart is a strictly better global backoff strategy than in-process forever-spin. `runbook_temporal_connect_attempts_total{result="timeout"}` counter alerted. |
| **R-S13** | Replacing `InsecureSkipVerify` with proper CA bundle breaks all worker→Temporal auth at rollout | PR-STAB-14 | M | H | **Highest-risk PR in the epic.** Mandatory canary on **one** worker pod for ≥48 h before any global rollout. Roll-back plan = single revert commit (no DB / state to clean up). Coordinate with the team that landed `1b1c279` — they know the cert chain on the current 7233 port. Add startup TLS handshake test that fails-loud with a clear error message ("expected hostname X, got Y") if cert is misconfigured. |
| **R-S14** | Probe realignment on scraper triggers restart loop because `/readyz` discovers a *real* upstream issue (PG/Redis) the old probes were masking | PR-STAB-15 | M | M | This is, again, **the desired outcome** — masked failures should surface. PR description requires SRE pre-brief: "expect 1–2 surprise restarts after rollout; investigate `/readyz` failing component (DB? Redis? Temporal?) — do not roll back the probe change." Canary ≥48 h. |

---

## 3. Things we deliberately do NOT change

These are areas where exploration suggested a change, but recent history or engineering instinct says "leave it":

1. **~~`iam-sidecar`~~ — D12** — **RETRACTED 2026-05-08.** This previously said "Cache, TTL, mutex, dual-cloud detection look correct. Skip." The stability investigation found `log.Fatal` inside `(s *service) ServeHTTP` at `iam-sidecar/iam-sidecar.go:159-160` (json.Marshal failure crashes the whole sidecar — and via the sidecar pattern, the whole pod). See **PR-STAB-05**. The latency/COGS judgement still stands; the **reliability** judgement was wrong. The `isAWS()`/`isGCE()` cloud-provider detection also has a single 2 s timeout that fatals if both fail — also addressed in PR-STAB-05.
2. **Recent kitt-runbooks logging** — we **demote and sample**, we do not **remove**. The team added these logs deliberately. PR-R3 description must list every change for the original author to ack.
3. **Temporal task queue config in scraper** — KEDA threshold=50 was chosen recently (`README.md` references it). We **add** a Redis trigger; we don't change the Temporal one.
4. **DTE worker `30 min` activity timeout** — used by long ServiceDiscovery activities. We make it **configurable per type** (PR-P2-03), not change the default.
5. **`amp/distributed-worker` codebase** in isolation — until consolidation lands, all P0/P1 changes ship to **both** `amp` and `helmfile/dte` copies (CI fence in PR-PHASE0-04 forces this).

---

## 4. Pre-flight checklist for every P0 PR

Before merging any P0 PR, confirm:
- [ ] Metric to validate the win exists (Phase-0 work landed)
- [ ] Canary cluster identified
- [ ] Roll-back plan documented in PR description (single revert commit + cache flush if any)
- [ ] If touching `amp/*`: matching change in `helmfile/dte/*` (or CI fence acknowledged)
- [ ] If touching auth: cache-key audit done against `slauth-token` recent commits
- [ ] Unit test added; integration test (Temporal devkit) updated where applicable
