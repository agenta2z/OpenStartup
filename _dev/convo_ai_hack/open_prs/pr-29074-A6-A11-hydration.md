# PR #29074 — A6+A11: Hydration parallel + person dedup

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A6-A11-hydration-paired` → `main`
**Created:** 2026-05-04 04:35 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:09 UTC &nbsp;•&nbsp; **Comments:** 23 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29074

## TL;DR

Two paired Rovo Insights optimizations that together deliver a **58–113× component-level speedup**, **−70-90% UserService RPC volume** (real cost win), and **3–7% e2e latency improvement on the `/fetch?generate=true` regen path**. The honest user-perceived saving is ~500–1000 ms out of a 15–30 s regeneration, but the cost reduction is the headline.

## Why this is HIGH impact

- **Cost (real $$):** −70-90% UserService RPC calls is direct cost reduction even outside latency wins.
- **p95/p99 win on regen path:** 3-7% e2e improvement on a 15–30s operation = 500–1000 ms saved per regeneration.
- **Compounds with A5:** A6+A11 unlocks more of A5's cancellation-isolation value because hydration is no longer the dominant per-type cost.
- **Component-level benchmarks are dramatic:** 58.65× on realistic prod scenario (6 types × 10 people × 60% overlap).

## What it changes

| Component | Before | After |
|----------|--------|-------|
| Hydration strategy | Sequential per type, re-fetches same person 3-4× | Pre-fetch all unique AAIDs once, parallel via `supervisorScope` |
| RPC fan-out per regen | 30-60 person fetches | ~10-20 (one per unique AAID) |
| Failure isolation | One AAID failure cancels all sibling fetches | `supervisorScope` (C3 fix) — failures are isolated and counted |
| New metrics | n/a | `rovo.insights.hydration.aaid_fetch_failed`, `rovo.insights.hydration.dedup_metrics` |

## Measured benchmarks (component-level, HydrationBenchmarkTest)

| Scenario | OLD | NEW | Speedup |
|----------|-----|-----|---------|
| **Realistic prod** (6 types × 10 people, 60% overlap) | 3,214 ms | 55 ms | **58.65×** |
| Stress (6 × 20, 50% overlap) | 6,422 ms | 57 ms | 113.07× |
| Heavy overlap | 1,610 ms | 55 ms | 29.17× |
| No overlap | 1,615 ms | 56 ms | 28.63× |
| Empty | 0 ms | 0 ms | (no overhead) |

## Honest user-perceived translation (per Plan v4 L8)

| Path | Saving |
|------|--------|
| `/status` endpoint | **0 ms** (background async; user sees boolean ~10 ms regardless) |
| `/fetch` cache HIT | **0 ms** (pre-hydrated from Redis) |
| `/fetch?generate=true` regen path | **500–1,000 ms** out of 15–30s = **3–7% e2e** |
| Per-pod RPC volume | **−70-90%** (cost win) |

## Files changed (+250 / −16 across 2 files)

| File | +/− | Notes |
|------|-----|-------|
| `modules/product/rovo/rovo-extras-impl/.../RovoInsightsServiceImpl.kt` | +180 / −8 | Refactored hydration; added `prefetchPersonReferencesByAaid`, `collectAndPrefetchPeople` |
| `modules/product/rovo/rovo-extras-impl/.../HydrationBenchmarkTest.kt` | +277 new | Comprehensive benchmark with 5 scenarios |
| `.gitignore` | +4 / 0 | Added `.ai_employee/` exclusion |

## Test results

- **Total:** 107/107 PASS (102 prior + 5 new HydrationBenchmarkTest scenarios)
- **Time:** 2 min 19 s
- **Lint:** Lint-Core, Lint-Rovo, Lint-Product, Lint-Tests all ✅

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #1 (Top-10 plan item #1)
- **Task file:** `.ai_employee/projects/rovo_insights/tasks/A6-A11-hydration-paired.md`

## Risk & rollback

- **Risk:** LOW — refactor preserves semantics; `supervisorScope` is the only behavior change (improves failure isolation).
- **Rollback:** `git revert` <30 min.

## Dependencies / merge order

- **Independent** — can merge anytime.
- **Compounds with:** #29085 (A5 cancellation), #29092 (A1 metrics — to validate post-deploy)

## Suggested next steps

- Get review from Michael Dawson / Zhangbin Cheng (rovo-extras owners).
- After merge, monitor `rovo.insights.hydration.aaid_fetch_failed` and validate −70-90% RPC drop in dashboards.
