# PR #29113 — A2: LLM parse-duration metric (recast); A3/A4/A13/A14 rejected with grep evidence

**Impact label:** 🟢 **LOW** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A2-parse-duration-measurement` → `main`
**Created:** 2026-05-04 11:55 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 1 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29113

> **Impact downgrade rationale (vs initial Medium):** Pure observability + a rejection report. PR explicitly states "instrumentation only, NO user-visible behavior change". Same category as A12 (#29096) measurement-only counter. Plus, the methodology contribution (rejecting 4 of 5 plan items with grep evidence) is documentation, not impact.

## TL;DR

V4 plan ranks #11-#15: 1 of 5 ships (recast as measurement-only); 4 of 5 rejected with grep evidence. Adds `ROVO_INSIGHTS_LLM_RESPONSE_PARSE_DURATION` histogram metric to instrument `parseRovoChatResponse()`. **No user-visible behavior change.** Methodology contribution: 4 plan items rejected with concrete grep evidence proving they had no actionable target.

## Why this is LOW impact

- **Pure observability:** instrumentation only, no behavior change.
- **Decision-enabler, not direct-value:** measurement gates a future decision on whether parsing optimization is needed.
- **Same category as A12 (#29096) and A1 (#29092)** — measurement infrastructure.
- The **methodology contribution** (rejecting 4 plan items with grep) is doc/learnings, not user-impact.

## What it ships (1 of 5)

### New histogram metric: `ROVO_INSIGHTS_LLM_RESPONSE_PARSE_DURATION`

| Aspect | Value |
|--------|-------|
| Buckets (ms) | 1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000 |
| Tagged | `insight_type=<RECOGNITION_INSIGHTS\|EMERGING\|...>` |
| Cardinality | 6 (one per InsightType enum, bounded) |
| Hot-path overhead | <1µs |
| Memory | A few KB for histogram buckets |

`parseRovoChatResponse()` instrumented via try/finally (records on success AND failure paths). Optional `insightType: InsightType?` parameter for tagging (backwards-compatible; defaults to null).

## What it rejects (4 of 5) — with grep evidence

| Rank | ID | Plan title | Grep evidence | Verdict |
|------|----|-----------|---------------|---------|
| #12 | A3 | "Eager Statsig client warm-up" | 0 hits in `insights/` for Statsig/warmup/@PostConstruct | OUT-OF-SCOPE |
| #13 | A4 | "Coroutine context propagation hygiene" | 0 hits in `insights/` for `withContext`/`MDC` | NO TARGET |
| #14 | A13 | "Replace `runBlocking` in test setup" | 0 hits in `insights/test/` for `runBlocking` | ALREADY FIXED |
| #15 | A14 | "Bounded `flow.collect` parallelism" | Only single-emission `Flow<Result<Unit>>` exists | NO MEANINGFUL TARGET |

## Decision criterion (post-deploy, ~1 week data)

- If p95 > 50ms → file follow-up to move parsing to `Dispatchers.Default` explicitly.
- If p95 < 10ms → close the optimization permanently with evidence.

## Files changed (+335 / −0 across 6 files)

| File | +/− | Notes |
|------|-----|-------|
| `A2-parse-duration-measurement.md` | +107 / 0 | Recast task doc |
| `A3-A4-A13-A14-REJECTED-no-actionable-target.md` | +55 / 0 | Rejection report w/ grep evidence |
| `R-1A-per-tool-deadline.md` | +12 / 0 | Cross-link |
| `platform-workflow-impl/README.md` | +6 / 0 | Project readme |
| `MetricKey.kt` | included | Metric registration + histogram bucket |
| `RovoInsightsServiceImpl.kt` + test file | included | Instrumentation + 3 new tests |

## Test results

- **All 15/15 PASS**: 3 new A2 tests + 12 prior. `./gradlew lintRovoShard` ✅.

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 ranks #11-#15.
- **Methodology lessons added:** v4 plan L7 ("pattern-matched plan items must be evidence-checked BEFORE entering the queue").

## Risk & rollback

- **Risk:** VERY LOW — purely additive instrumentation.
- **Rollback:** `git revert` <15 min.

## Dependencies / merge order

- **Tier 6** (measurement-only, any time).
- Should land before A1 dashboards are extended.

## Suggested next steps

- Get review approval.
- After 1 week of data, decide whether to ship parse-duration optimization.
