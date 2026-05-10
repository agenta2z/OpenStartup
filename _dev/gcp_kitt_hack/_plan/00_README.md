# gcp_kitt — Goal-Driven Improvement Plan
**For:** `atlassian_packages/gcp_kitt`
**Authored:** 2026-05-08
**Top-of-tree commit observed:** `cf10ed7 print detailed errors`
**Driver-OKR:** Proactive AI Platform (PAI) — scale AI invocations from **400K → 1.5M / month** in FY26 H2. The PAI compute, scraper-driven knowledge ingestion, and runbook-driven reliability all run on top of the gcp_kitt control-plane (DTE workers, ForgeApp operator, Sweeper, kitt-runbooks, scraper).

> **gcp_kitt is the floor; PAI's ceiling rests on it.** Every 1 ms of activity overhead costs ~25 CPU-minutes/day at the 1.5M/mo rate. Every duplicate K8s `List(NamespaceAll)` call shaves headroom from every workload sharing the cluster.

---

## How this plan is organized

| File | What's in it |
|------|--------------|
| `00_README.md` | Goals, scoring rubric, top-line summary table (this file) |
| `01_GOALS_AND_METRICS.md` | The measurable goals every plan item must move; how we'll measure |
| `02_FINDINGS_CATALOG.md` | All ~50 findings, normalised, with file:line and quantified impact |
| `03_PRIORITIZED_PLAN.md` | The actual prioritized work plan, P0 → P3, with epics |
| `04_PR_BREAKDOWN.md` | Every plan item decomposed into reviewable PRs (size, dependencies) |
| `05_RISK_AND_HISTORY.md` | What recent commits changed, why, and how we avoid regressing |
| `06_OUT_OF_BOX.md` | Innovative refactor proposals (consolidation, observability fabric) |
| `07_STABILITY_PLAN.md` | **EPIC P0-S** (Stability) — added 2026-05-08 in response to user crash report; ships as Phase 0.5 |
| **`08_INTEGRATED_PLAN.md`** | **CANONICAL merged plan (2026-05-08)** — reconciles `07_STABILITY_PLAN.md` with `~/.claude/plans/taking-a-deep-look-modular-hopper.md`; adds 10 scraper-deep findings (N1–N10), 5 cross-cutting gaps (G1–G5); drops 4 validation-refuted claims. **Read this first.** |

The plan is intentionally **structured for both humans and machine-followable agents** (each PR has a stable ID, branch suggestion, file list, and acceptance metrics).

---

## The lens we use to prioritise

Every item is scored along **four PAI-relevant axes**:

| Axis | Metric | Why it matters for the 400K→1.5M OKR |
|---|---|---|
| **Throughput** | Workflows/min, K8s API QPS headroom | More PAI invocations / unit infra |
| **Latency** | p50/p95/p99 of activity, reconcile, auth-token | Lower TTFB → more daily active users → more invocations |
| **COGS** | $/month: compute, K8s API, Splunk ingest, Kinesis PUTs, AI Gateway egress | Survives the 3.75× scale-up |
| **Reliability** | Workflow success rate, MTTR | One incident eats a week of OKR progress |

Each finding is rated **P0 / P1 / P2 / P3** by **Impact × Confidence ÷ Effort × Risk**.

---

## Top-line summary

> **2026-05-08 update — STABILITY EPIC inserted as Phase 0.5.**
> A user report — *"the current service is unstable and very often crashes"* — triggered a deep crash-investigation (see `07_STABILITY_PLAN.md`). Cross-validation against the existing plan found that **only ~30 % of the user's crash pain was covered** by the original (perf-oriented) plan. **EPIC P0-S** (15 fixes, S1–S15) is therefore inserted as **Phase 0.5**, between Phase 0 (observability) and Phase 1 (perf wins). Stability ships first; performance gains on a service that crashes are unrealisable.

| Tier | What | Lift | Effort | Risk | Source |
|---|---|---|---|---|---|
| **P0-S** | **Stability EPIC** — 15 small fixes (S1–S15): remove `log.Fatal` from steady-state loops, surface silent worker death, proper liveness/readiness/preStop, bounded retries, circuit breakers, TLS hardening | Pod restart-rate ↓ ≥ 80 %; eliminates phantom-pod failure mode; SLO-grade reliability floor | ~8 working days; 15 PRs (40–250 LoC each) | LOW–MED | **§07 (NEW)** |
| **P0** | De-duplicate `amp/*` ↔ `helmfile/dte/*` (12 lines diff in helpers, 100 in client) | Eliminates silent divergence; halves bug-fix cost | 2 weeks | M (refactor) | §02-A1, §03-E1 |
| **P0** | HTTP client + token cache for `getClusterTokenFromAuthProvider` | -50–70% auth-path latency; ~$2-5K/mo COGS | 3 days | L | §02-A2/A3 |
| **P0** | Switch `k8s-metadata-collector` from `List(All)+Sleep` to **shared informers + Kinesis PutRecords batch** | -90% K8s API list calls; -60% Kinesis cost; remove `log.Fatalf` crash-loop | 1 week | L | §02-D1/D2 |
| **P0** | Sweeper: replace cluster-wide List with **predicate-filtered watch on KITT namespace** + remove unbounded retry-on-any-error | -95% K8s API load from sweeper | 3 days | L | §02-D3/D4 |
| **P0** | Reduce ForgeApp Status().Update() churn (5/reconcile → 1) + remove `logStatus` JSON marshal | -70% etcd write/sec; -30% reconcile p95 | 2 days | L | §02-D5/D6 |
| **P1** | Logging-cost reduction in kitt-runbooks (recent +400 lines log) → leveled + sampled | -30–50% Splunk ingest from runbooks | 3 days | L | §02-C1, §05 |
| **P1** | Cache K8s clientset in kitt-runbooks activities (currently re-created per activity) | -2.5–10s MTTR per cordon workflow | 2 days | L | §02-C2 |
| **P1** | Parallelise sequential `CheckNodeStatusActivity` loop | -90% MTTR for multi-node cordon | 1 day | L | §02-C3 |
| **P1** | Scraper Redis pipelining + batched visited-check | -40–50% per-URL latency; -50% Redis ops | 1 week | L | §02-B1/B2 |
| **P1** | Workflow `gather_timeout` race in scraper; KEDA Redis-depth scaler | Eliminates silent activity-orphan; +30% spike scaling | 2 days | M | §02-B3/B4 |
| **P1** | Bound goroutine fan-out in DTE workflow | -30% p99 latency at large fanout | 2 days | L | §02-A4 |
| **P2** | Field selector + pagination on Sweeper, k8s-metadata, kitt-runbooks `List` calls | -40–60% K8s API CPU on big clusters | 2 days | L | §02-D7 |
| **P2** | Splunk query narrowing + result caching (kitt-runbooks) | -50% Splunk query cost | 2 days | L | §02-C4 |
| **P2** | Observability epic — emit histograms and tag-based logs across workers | Removes blind spot (currently no p95 metric for activities) | 1 week | L | §02-E1 |
| **P3** | Out-of-box: a single `pkg/dte` Go module + Python/JS scraper consolidation roadmap | -30% maintenance; ground for future refactors | 4–8 weeks | H | §06 |

**Estimated aggregate:**
- **Latency:** -30–60% on hot paths (auth, reconcile, scraper URL).
- **K8s apiserver QPS:** -60–90%.
- **COGS:** ~**$15–35K / month** of pure infra waste removed at current load (1.5–3.5× at OKR target).
- **Reliability (with P0-S landed):** Pod restart-rate ↓ ≥ 80 %; ≥10 silent/cascading-failure modes removed (steady-state `log.Fatal`s, silent worker death, sidecar-Fatal-in-ServeHTTP, `os.Exit(1)` from goroutines, panic-in-Reconcile, Sleep-in-Reconcile, missing SIGTERM handlers, missing/misaligned probes, unbounded retries, TLS `InsecureSkipVerify`).
- **Risk profile:** P0-S epic is intentionally **low-risk and uncorrelated** with perf work — the two streams can ship in parallel branches. See `07_STABILITY_PLAN.md` §"How EPIC P0-S integrates with the existing plan".

---

## Reading order
1. `01_GOALS_AND_METRICS.md` — anchor the "why".
2. **`08_INTEGRATED_PLAN.md`** — **CANONICAL** merged stability plan (S1–S15 + N1–N10 + G1–G5).
3. `07_STABILITY_PLAN.md` — receipts for S-series.
4. `03_PRIORITIZED_PLAN.md` — what we're doing and in what order.
5. `04_PR_BREAKDOWN.md` — the actual PRs to open.
6. `02_FINDINGS_CATALOG.md` / `05_RISK_AND_HISTORY.md` — receipts.
7. `06_OUT_OF_BOX.md` — strategic, longer-horizon proposals.
