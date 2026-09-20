# PR #29092 — A1: Foundational observability metrics for /fetch + /status

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A1-observability-foundational` → `main`
**Created:** 2026-05-04 06:49 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:09 UTC &nbsp;•&nbsp; **Comments:** 2 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29092

## TL;DR

Adds the missing baseline observability for `/fetch` and `/status` endpoints: 4 metric keys + 2 latency histograms (p50/p95/p99) + per-endpoint outcome counter. **No user-visible behavior change**, but **enables measurement of every other Rovo Insights PR** (A6, A8, A9, A10, A12, NEW).

## Why this is HIGH impact

- **Foundational / load-bearing for measurement:** without these metrics, post-deploy validation of A6+A11 (3-7% latency) and A8 (cost) is **literally impossible to measure in production**.
- **Operational SLO enablement:** first-time visibility into endpoint-level p50/p95/p99.
- **`forceRefresh=true` abuse counter** enables future cost analysis.

> Foundational observability that unblocks others is rated High alongside reliability fixes — without it, every other PR's claimed impact stays unverifiable in prod.

## What it changes

| Metric | Type | Purpose |
|--------|------|---------|
| `ROVO_INSIGHTS_STATUS_LATENCY` | Histogram | p50/p95/p99 for `/status` |
| `ROVO_INSIGHTS_FETCH_LATENCY` | Histogram | p50/p95/p99 for `/fetch` |
| `ROVO_INSIGHTS_FORCE_REFRESH` | Counter | `forceRefresh=true` tracking |
| `ROVO_INSIGHTS_ENDPOINT_RESULT` | Counter (tagged) | per-endpoint outcome (200 / 4xx / 5xx) |

**Histogram buckets (ms):** `50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000` — tuned for cached <250ms + hydration 500ms-5s.

## Implementation pattern

- `try / finally` for latency capture (always recorded, even on exception)
- `runCatching` for outcome result tagging
- Per-endpoint wrapper methods refactored from inline controller logic

## Files changed (+540 / −0 across 6 files)

| File | +/− | Notes |
|------|-----|-------|
| `RovoInsightsV1Controller.kt` | +90 / 0 | Instrumentation wrapper; refactored endpoints |
| `MetricKey.kt` | +31 / 0 | 4 new metric keys + histogram defs |
| `RovoInsightsV1ControllerInstrumentationTest.kt` | +184 new | 4 new instrumentation unit tests |
| `A1-observability-foundational.md` | +112 new | Task file |
| `HistogramBucket` def | included | Tuned bucket configuration |

## Performance overhead

- **<1 ms per request** (sub-millisecond) — sub-LSB on real call latencies of 50-30,000 ms.

## Test results

- **Total:** 106 tests PASS (102 prior + 4 new instrumentation tests).
- All lint shards ✅ pass.

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #3 (Top-10 plan item #3, after B0.1'-α deferred to RFC).
- **Task file:** `.ai_employee/projects/rovo_insights/tasks/A1-observability-foundational.md`

## Risk & rollback

- **Risk:** VERY LOW — pure additive instrumentation; no behavior change.
- **Rollback:** `git revert` <15 min.

## Dependencies / merge order

- **Should merge first** (Tier 1 — foundation). Unblocks measurement of every other rovo-insights PR.

## Suggested next steps

- Get review + merge ASAP.
- Build dashboards for the 4 new metrics before merging A6+A11 / A5 / A8 so post-deploy validation is possible.
