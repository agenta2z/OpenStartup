# PR #29119 — R-1B: Surface TIMEOUT to LLM as synthetic ERRORED ToolExecution

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `R-1B-llm-timeout-feedback` → `main`
**Created:** 2026-05-04 13:43 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 1 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29119

> **Note:** This is the `main`-targeted version of R-1B. Companion PR #29114 is the same content stacked on the R-1A branch. **One should be closed before the other merges.**

> **Impact upgrade rationale (vs. initial Medium):** R-1B is **load-bearing** for R-1A. Without it, R-1A's TIMEOUT silently drops the result via `mapNotNull`, leaving the LLM with zero signal that the prior tool call timed out — agent re-calls the same hung tool on the next iteration, **defeating half of R-1A's value**. Same severity tier as R-1A itself (HIGH).

## TL;DR

R-1A (#29112) returns `null` on TIMEOUT, which `executeTools()` filters out via `mapNotNull`. The LLM sees nothing — and re-calls the hung tool on the next loop iteration. **R-1B fixes this** by constructing a synthetic `ToolExecution(status=ERRORED)` with stable JSON payload, so the LLM observes the timeout and self-corrects (skip / try alternate / apologize to user).

## Why this is HIGH impact

- **Closes the LLM-feedback loop on TIMEOUT** — without it, R-1A's value is at most halved.
- **Categorical improvement:** silent-skip / hung-loop → LLM-generated apology to user.
- **First-time LLM-observability of timeouts** — agent self-correction becomes possible.

## Synthetic JSON payload (stable, machine-parseable)

```json
{
  "error_code": "TOOL_EXECUTION_TIMEOUT",
  "tool": "<toolName>",
  "deadline_ms": <perToolDeadlineMs>,
  "message": "Tool '<toolName>' did not return within <N>ms and was cancelled. Do NOT retry this exact call. Either continue without it, try a different tool, or briefly inform the user that this step timed out."
}
```

Flows through existing pipeline: `toFunctionMessage` → LLM function-message history → next-iteration agent decision.

## What it changes

| Behavior | Before R-1B | After R-1B |
|----------|-------------|-------------|
| TIMEOUT in agent loop | Silent drop (null filtered out) | Synthetic ERRORED ToolExecution surfaced |
| LLM observability | NONE | Sees timeout in function-message history |
| Repeat-call rate after TIMEOUT | Uncontrolled | LLM-decision-bound (self-correction) |
| Failure-mode discoverability | NONE | Ops can grep `error_code=TOOL_EXECUTION_TIMEOUT` |
| User experience on TIMEOUT | Silent skip / hang | LLM-generated apology + try-alternate |

## Files changed (+301 / −6 across 6 files)

| File | +/− | Notes |
|------|-----|-------|
| `SimpleLoopWorkflowExecutorImplTest.kt` | +214 / 0 | 3 new regression tests |
| `SimpleLoopWorkflowExecutorImpl.kt` | +83 / −6 | Synthetic execution builder |
| `SimpleLoopWorkflowConfiguration.kt` | +4 / 0 | Spring wiring (perToolDeadlineMs) |
| `R-1B-llm-timeout-feedback.md` | +117 / 0 | Task doc |
| `R-1A-per-tool-deadline.md` | +12 / 0 | Companion task |
| `platform-workflow-impl/README.md` | +6 / 0 | Project readme |

## Test results

- **Total:** 94 PASS (91 existing + 3 new R-1B regression tests). Compile 2s. detekt clean.
- **3 new tests:**
  1. `R-1B execute surfaces synthetic ERRORED ToolExecution when tool exceeds per-tool deadline`
  2. `R-1B synthetic timeout output is stable parseable JSON with required fields`
  3. `R-1B happy-path tool finishing within deadline is unaffected by R-1A R-1B`

## Plan / refs

- **Plan:** INTEGRATED_PLAN_v7_synthesis.md TOP-15 rank #5 (companion to R-1A rank #4).
- **Compounds with:** #29112 R-1A.

## Risk & rollback

- **Risk:** LOW — no public API change; only internal TIMEOUT branch in `executeTool` changes behavior.
- **Rollback:** `git revert` <5 min. R-1A continues to bound latency; just falls back to silent-drop behavior.

## Dependencies / merge order

- **Tier 2 — should land paired with #29112 R-1A**.
- **MUST land before #29110 T0a** (so larger thread pool doesn't amplify hung-tool risk).
- **Housekeeping:** close #29114 (stacked duplicate) before merging this one — or vice versa.

## Suggested next steps

- Decide which of #29114 vs #29119 to keep; close the other.
- Coordinate merge with #29112 R-1A.
- Post-deploy: monitor LLM-action distribution after TIMEOUT events (>= 7 day window) per task acceptance criteria.
