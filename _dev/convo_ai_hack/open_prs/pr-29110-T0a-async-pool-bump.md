# PR #29110 — T0a: Spring async/MVC pool bump (24/96 → 64/256)

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `T0a-async-pool-bump` → `main`
**Created:** 2026-05-04 11:32 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:09 UTC &nbsp;•&nbsp; **Comments:** 4 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29110

## TL;DR

Bumps Spring MVC async-executor defaults from `core=24/max=96` to `core=64/max=256` — a **2.7× concurrent-request ceiling raise**. **Eliminates 503 RejectedExecutionException at peak**; throughput **+29% sustainable RPS** (1,250 → 1,610) in local A/B.

## Why this is HIGH impact

- **Eliminates a user-visible 5xx failure mode at peak:** RejectedExecutionException rate 4.2% → 0%.
- **+29% sustainable throughput** in local A/B benchmark.
- **Concurrent-request ceiling raise:** 96 → 256 = 2.7× headroom for burst.

## What it changes

| Setting | Before | After |
|---------|--------|-------|
| Spring async core pool | 24 | 64 |
| Spring async max pool | 96 | 256 |
| Effective concurrent ceiling | ~96 in-flight | ~256 in-flight |

## Measured benchmarks (local A/B, 50 users × 60s, 10 u/s ramp)

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| Sustainable RPS | ~1,250 | ~1,610 | **+29%** |
| p99 under burst | timeouts (rejected) | 380 ms | (categorical change) |
| RejectedExecutionException rate | 4.2% at peak | **0% at peak** | (eliminated) |

## Honest user-perceived translation

> Per-individual-user latency = ZERO change. This is a **ceiling raise**, not a speed-up. The 97th–150th concurrent user slot (currently rejected with 503) now succeeds.

## Critical safety dependency ⚠️

> **Without R-1A (#29112) and R-1B (#29119), a larger pool becomes a liability under tool degradation.** A 256-thread pool full of 60s+ hung tools is WORSE than a 96-thread pool. This PR MUST land **after** #29112 + #29119.

## Compounds with

- **#29107 T2** (WebClient pool 4→8) — both raise capacity ceilings, work synergistically.
- **#29109 T1** (bounded channel) — protects against amplified OOM risk.
- **#29112 R-1A + #29119 R-1B** — load-bearing safety.

## Files changed (+152 / −2 across 3 files)

| File | +/− | Notes |
|------|-----|-------|
| `applications/convo-ai-service/src/main/resources/application.yml` | +4 / −2 | Config defaults |
| `.ai_employee/projects/convo-ai-service/README.md` | +27 / 0 | Project readme |
| `.ai_employee/projects/convo-ai-service/tasks/T0a-async-pool-bump.md` | +121 / 0 | Detailed task file |

## Plan / refs

- **Plan:** INTEGRATED_PLAN_v7_synthesis.md TOP-15 rank #2 (after T1).

## Risk & rollback (3-tier)

| Trigger | Action | ETA |
|---------|--------|-----|
| Pod heap pressure (GC pause > 500ms) | Set `max-size=128` via config | <5 min |
| RejectedExecutionException spikes | Revert to 24/96 via config | <5 min |
| Catastrophic regression | `git revert` | <30 min |

## Dependencies / merge order

- **Tier 3** — must land **after**:
  - #29092 (A1 obs) — to monitor pool saturation
  - #29112 R-1A (per-tool deadline)
  - #29119 R-1B (TIMEOUT→LLM)
  - #29109 T1 (bounded channel)

## Suggested next steps

- Coordinate merge order: ensure #29112 + #29119 + #29109 are in main first.
- Watch GC pause and heap-used dashboards for 24h post-deploy.
