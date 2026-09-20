# PR #29114 — R-1B (stacked): same content as #29119, on R-1A branch

**Impact label:** 🟡 **MEDIUM** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `R-1B-llm-timeout-feedback` → **`R-1A-per-tool-deadline-v2`** (stacked, NOT main)
**Created:** 2026-05-04 12:01 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 2 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29114

> ⚠️ **DUPLICATE / housekeeping issue:** This PR is the **stacked** variant of R-1B targeting the R-1A feature branch. The functional content is the same as **PR #29119** (which targets `main`). **Close one of the two before merging the other** to avoid double-counting work and confusing review.

## Why labeled MEDIUM (not High like #29119)

The same content as #29119 is HIGH (load-bearing for R-1A). But this stacked PR's purpose is **review-flow** (allow R-1B to be reviewed without merging via R-1A first); it is NOT the version that lands on `main`. Therefore its actual impact-on-production is Medium (or zero, if #29119 is the one that ships).

## What it changes

Identical content to #29119:

- Synthesise `ToolExecution(status=ERRORED)` on TIMEOUT carrying stable JSON payload.
- Plumbing through `executeTools()` → function-message history → LLM next-iteration self-correction.
- 3 new R-1B regression tests.

(See [`pr-29119-R-1B-timeout-feedback-main.md`](pr-29119-R-1B-timeout-feedback-main.md) for full details.)

## Files changed (+280 / −8 across 4 files)

| File | +/− | Notes |
|------|-----|-------|
| `SimpleLoopWorkflowExecutorImplTest.kt` | +220 | R-1B regression tests |
| `R-1B-llm-timeout-feedback.md` | +117 | Task doc |
| `SimpleLoopWorkflowExecutorImpl.kt` | +58 / −6 | Synthetic execution builder |
| `SimpleLoopWorkflowConfiguration.kt` | +7 / −2 | Spring wiring |

## Recommendation

**Close this PR (#29114)** in favor of #29119 once R-1A (#29112) merges to main. Then #29119 (which targets `main` directly) can rebase cleanly.

OR — if the team prefers the stacked review flow — close #29119 and merge R-1A first, then merge #29114 (which auto-retargets to main once R-1A's branch is gone).

**Either way, only ONE of #29114 / #29119 should ship.**

## Suggested next steps

- Decide stacked vs main strategy with reviewers.
- Close the loser; merge the winner.
