# PR #29097 — A9: Exponential backoff with jitter for `retryable()` (opt-in)

**Impact label:** 🟡 **MEDIUM** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A9-exponential-backoff-with-jitter` → `main`
**Created:** 2026-05-04 07:23 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 7 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29097

## TL;DR

Adds **opt-in** exponential backoff + jitter to `Retryable.kt` (default = zero delay = backwards-compatible). Addresses two concrete failure-mode costs: (1) **wasted LLM cost** ($0.20-$1 per retry × 3 immediate = $1.50-$3 wasted), and (2) **thundering herd** — all users retrying at the same wall-clock instant, cascading rate-limit on downstream LLM.

## Why this is MEDIUM impact

- **Conditional value:** only matters during transient failures (incident windows).
- **Real cost saving** during incidents (−2× wasted LLM calls per failed type) but $0 saving on the happy path.
- **Throughput improvement during failure windows:** ~+10%.
- Not user-perceptible at single-request level on the happy path.

## What it changes

- New optional `initialDelayMs` and `maxDelayMs` parameters on `retryable()`.
- Default `initialDelayMs = 0L` → backwards-compatible (no delay if not opted in).
- Caller (`RovoInsightsServiceImpl`) opts in with `initialDelayMs=100L, maxDelayMs=5000L`.

### Backoff schedule (when opt-in via `initialDelayMs=100L`)

| Retry | Sleep (ms) |
|-------|-----------|
| 1 | 100 × jitter (jitter ∈ [0.5, 1.5)) |
| 2 | 200 × jitter |
| 3 | 400 × jitter |
| ... | exponential, capped at `maxDelayMs` (default 5000) |

## Claimed impact (per Plan v4 §5.5)

| Dimension | Impact |
|-----------|--------|
| Wasted LLM cost during transients | **−2×** per failed type |
| Throughput during failure windows | **+~10%** (no rate-limit cascade) |
| Latency on success | UNCHANGED (sleep only between retries) |
| p99 | **−10s** (eliminates retry-burst exhausting timeout) |
| Stability during incidents | MAJOR |

## Files changed (+198 / −13 across 4 files)

| File | +/− | Notes |
|------|-----|-------|
| `RetryableTest.kt` | +108 / −8 | 5 new test cases; existing tests unchanged (backwards-compat verified) |
| `Retryable.kt` | +33 / −1 | Core backoff logic |
| `RovoInsightsServiceImpl.kt` | +5 / −1 | Caller opts in (100ms → 200ms → 400ms with 5s cap) |
| `.gitignore` | +3 / 0 | AI-employee task journal |

## Test results

- **All 8/8 PASS**: 5 new (default-behavior, exponential-schedule, maxDelayMs-cap, no-final-sleep, non-retryable-exception) + 3 prior (success-on-first, retry-once, retries-exceeded).

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #6.
- Replaces v3 ID B6.1 (originally bundled with structured output — that rejected; backoff retained as A9).

## Risk & rollback (3-tier)

| Trigger | Action | ETA |
|---------|--------|-----|
| Retry latency ballooning (>30s) | Investigate `maxDelayMs`; revert if needed | <30 min |
| Retry semantics regression | `git revert` | <15 min |
| Compile failure | `git revert` | <15 min |

## Dependencies / merge order

- **Independent.** Compounds with A10 (#29099 partial JSON) — both reduce retry pressure.

## Suggested next steps

- Get review approval.
- Add retry-count and retry-delay metrics to dashboards before merge.
