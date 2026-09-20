# PR #29103 — A8: Cache salt memoize (~95% Statsig SDK access reduction)

**Impact label:** 🟢 **LOW** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A8-cache-salt-memoize` → `main`
**Created:** 2026-05-04 07:50 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 3 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29103

> **Impact downgrade rationale (vs initial Medium):** PR description itself states "<0.5% user-perceived". −24ms saved out of 15-30s regen = imperceptible micro-optimization. Belongs in the LOW tier with other micro-perf wins (NEW telemetry dedup, C2 lookup).

## TL;DR

Memoize the cache-salt dynamic-config value with a 5-second TTL to skip ~95% of redundant Statsig SDK access on the cache hot path. **Saves ≤24ms per regen** (1-2ms × 12 cache ops). PR's own honest assessment: "<0.5% user-perceived".

## Why this is LOW impact

- **PR own assessment:** "<0.5% user-perceived"
- **Aggregate win is small:** ~24ms out of a 15-30s regen path
- **No behavior change** beyond the 5s operator UX delay for salt invalidation
- Belongs alongside other micro-optimizations (#29101, #29121)

## What it changes

| Aspect | Before | After |
|--------|--------|-------|
| Statsig client lookups per regen | ~12 (one per cache get/put) | ≤1 (memoized for 5s) |
| Operator salt-change visibility | Instant | ≤5s delay (acceptable trade-off) |
| Cache hot-path latency | n × 1-2ms | ~1-2ms total |

## Implementation

- `@Volatile`-guarded in-process memoize for cache salt
- TTL = **5 seconds** (preserves operator UX)
- `nowMsProvider` injection point for testability without sleeping
- 3 new A8 tests (memoize, TTL contract, default fallback)

## Files changed (+152 / −10 across 3 files)

| File | +/− | Notes |
|------|-----|-------|
| `A8-cache-salt-memoize.md` | +122 / 0 | Detailed task doc |
| `RovoInsightsCacheImplTest.kt` | +43 / 0 | 3 new tests for memoize behavior |
| `RovoInsightsCacheImpl.kt` | +36 / −10 | Memoize implementation |

## Test results

- **All 13/13 PASS:** 3 new + 10 prior cache tests.

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #9 (after A17 rejection).
- **Builds on:** A1 (#29092 metrics).

## Risk & rollback

- **Risk:** LOW — memoize is additive and TTL-bounded.
- **Rollback:** `git revert` <15 min.

## Dependencies / merge order

- **Independent.** Tier 5 (aggregate fleet wins, any time).

## Suggested next steps

- Get review approval (Michael Dawson, Zhangbin Cheng assigned).
- Land any time after A1 (#29092) so the cache hit-rate metric can validate post-deploy.
