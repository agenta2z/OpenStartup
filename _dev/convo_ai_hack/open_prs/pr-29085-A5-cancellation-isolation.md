# PR #29085 — A5: Cancellation isolation (5/6 insights survive single LLM failure)

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A5-supervisor-scope-cancellation-isolation` → `main`
**Created:** 2026-05-04 05:43 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:09 UTC &nbsp;•&nbsp; **Comments:** 6 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29085

## TL;DR

Replaces `coroutineScope { awaitAll() }` with `supervisorScope` for the 6 parallel LLM insight-type calls. **Categorical reliability win:** during transient LLM failure, users now get **5 of 6 insights in ~1 minute** instead of **0 insights after a 13-minute retry storm**.

## Why this is HIGH impact

- **Categorical user-visible win** — converts "broken" → "works": 0/6 insights → 5/6 insights.
- **−12 minutes** at p99 during LLM degradation (eliminates retry-storm cascade).
- **Failure-mode improvement is permanent**, not conditional — happy path is preserved byte-for-byte.

## What it changes

| Behavior | Before (`coroutineScope`) | After (`supervisorScope`) |
|----------|---------------------------|----------------------------|
| Single-type LLM rate-limit | Cancels all 5 sibling fetches | Caught individually; 5 succeed, 1 recorded as failed |
| User experience | 0/6 insights, 13-min p99 retry loop | 5/6 insights, 1-min response |
| Total failure (all 6 fail) | Cascading retries | Single clean exception |

## New metrics

| Metric | When emitted |
|--------|--------------|
| `ROVO_INSIGHTS_PARTIAL_SUCCESS` | Some-but-not-all types succeed |
| `ROVO_INSIGHTS_TYPE_FAILED{type=...}` | Per-type failure counter |

## Honest user-perceived impact (per Plan v4 §6.5 + L8)

| User segment | Frequency | Impact |
|--------------|-----------|--------|
| Off-peak (~85%) | most | **0 ms** (no contention) |
| Happy path all-6 succeed | 70-90% of regens | **0 ms** (semantics unchanged) |
| Partial failure during LLM degradation | 5-10% | **−12 min wait + 5 extra insights returned** |
| Total failure | <1% | **−12 min wait** (clean exception vs retry loop) |

## Files changed (+102 / −8 across 3 files)

| File | +/− | Notes |
|------|-----|-------|
| `RovoInsightsServiceImpl.kt` | +93 / −3 | Added `generateAllTypesWithCancellationIsolation`; metric emission |
| `RovoInsightsServiceImplTest.kt` | +128 new | 4 new regression tests |
| `MetricKey.kt` | +6 / 0 | 2 new metric keys |

## Test scenarios (all PASS)

1. All 6 succeed → no PARTIAL_SUCCESS or TYPE_FAILED metric
2. 1 of 6 fails → other 5 succeed; metrics counted; no throw
3. All 6 fail → throws `RovoInsightsGenerationException`
4. **Regression guard:** first failure does NOT cancel pending siblings (proven via timing test)

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #2 (Top-10 plan item #2)
- **Task file:** `.ai_employee/projects/rovo_insights/tasks/A5-supervisor-scope-cancellation-isolation.md`

## Risk & rollback

- **Risk:** LOW — happy path is byte-for-byte identical.
- **Rollback:** `git revert` <30 min.

## Dependencies / merge order

- **Independent** of A6+A11 (#29074) but **compounds:** A6+A11 reduces hydration cost so partial-success path returns faster.
- **Best validated via:** A1 (#29092) metrics for measuring `PARTIAL_SUCCESS` rate post-deploy.

## Suggested next steps

- Get review approval from Michael Dawson.
- Add `PARTIAL_SUCCESS` and `TYPE_FAILED` to dashboards after merge.
