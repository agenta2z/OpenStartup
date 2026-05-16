# PR #29096 — A12: Duplicate-handler detection counter (measurement-only)

**Impact label:** 🟢 **LOW** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A12-handler-idempotency-setnx` → `main`
**Created:** 2026-05-04 07:18 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 3 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29096

## TL;DR

Adds a `ROVO_INSIGHTS_HANDLER_DUPLICATE_DETECTED` counter to gather data on whether SQS at-least-once redelivery is causing actual duplicate handler invocations. **Measurement-only — no behavior change** (handler still runs every time). Gates a future decision on whether SETNX framework work (2-3 days cross-team) is justified.

## Why this is LOW impact

- **Measurement-only:** no behavior change, no cost win, no latency change.
- **Decision-gating:** value is in collecting evidence to decide whether the bigger SETNX framework work is justified.
- **Aligns with v4 plan L5** ("measure before optimizing").

## What it changes

| Aspect | Value |
|--------|-------|
| New metric | `ROVO_INSIGHTS_HANDLER_DUPLICATE_DETECTED` |
| Detection strategy | TTL-bounded ConcurrentHashMap (process-local) |
| TTL | 5 minutes (covers retry-storm window) |
| Memory bound | <100 KB worst case (10K entries × ~10 bytes) |
| Hot-path overhead | ~1 µs (ConcurrentHashMap put + check) |
| Behavior change | NONE (handler always runs) |

## Decision criteria (2-week measurement window)

- If duplicates **>5%** of invocations → schedule SETNX framework change as separate work.
- If duplicates **<1%** → close A12 ask permanently with measurement evidence.

## Why measurement-first?

A12 was originally scoped as "handler idempotency via Redis SETNX" to prevent duplicate handler invocations from SQS at-least-once semantics. Investigation revealed:
- Existing `RedisCache` interface does NOT support `setIfAbsent` / SETNX.
- Adding it = 2-3 days cross-team work.
- **No data exists on actual duplicate rate.**

Per Plan v4 L5 (measure-before-optimize), this PR ships a smaller "detection counter" to gather evidence first.

## Files changed (+227 / −0 across 4 files)

| File | +/− | Notes |
|------|-----|-------|
| `A12-handler-idempotency-measurement.md` | +112 / 0 | Task doc |
| `RovoInsightsGenerationTaskHandlerTest.kt` | +82 / 0 | 3 new tests |
| `RovoInsightsGenerationTaskHandler.kt` | +31 / 0 | `detectAndCountDuplicate` method |
| `MetricKey.kt` | +8 / 0 | New metric enum value |

## Test results

- **3 new tests:**
  1. Counter NOT emitted on empty cache
  2. Counter IS emitted when payload exists in cache
  3. Counter-emission failure is non-fatal (handler continues)
- All pass.

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #5.
- **Builds on:** A1 (#29092) — counter feeds into A1 dashboards.
- **Lesson source:** B0.1 incident (§7.0 lesson #1) — same pattern (measurement before optimization).

## Risk & rollback

- **Risk:** VERY LOW — measurement-only; no behavior change; bounded memory.
- **Rollback:** `git revert` <15 min.

## Dependencies / merge order

- **Tier 6** (measurement-only, any time). Best after #29092 A1.

## Suggested next steps

- Get review approvals (6 reviewers assigned).
- After merge + 2 weeks data, decide on SETNX framework work.
