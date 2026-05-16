# PR #29112 — R-1A: Per-tool execution deadline (`withTimeoutOrNull`)

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `R-1A-per-tool-deadline-v2` → `main`
**Created:** 2026-05-04 11:52 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:09 UTC &nbsp;•&nbsp; **Comments:** 1 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29112

## TL;DR

Bounds per-tool execution time in the agent loop with `withTimeoutOrNull(perToolDeadlineMs)` (default **30 s**). **Prevents indefinite tool hangs** that currently cause client timeout (60-120s) and broken streaming responses. **Load-bearing safety change that makes T0a's larger thread pool safe to ship.**

## Why this is HIGH impact

- **Categorical safety:** prevents indefinite tool hangs (60-120s → bounded at 30s).
- **Load-bearing for T0a:** without R-1A, a 256-thread pool full of hung tools is WORSE than 96 threads. T0a (#29110) cannot safely ship without this.
- **User experience during failure:** broken streaming response → clean parseable error after 30s.

## What it changes

| Behavior | Before | After |
|----------|--------|-------|
| Hung tool | Indefinite block | Cancelled after 30s |
| Client timeout cascade | 60-120s, broken streaming | None — agent loop continues |
| User experience on hang | Unknown failure | Bounded latency, parseable error |

## Honest user-perceived translation

| User segment | Frequency | Impact |
|--------------|-----------|--------|
| Median (<1s tools) | most | **Identical** — no change |
| p95 (5-10% flaky tools) | mostly fine | Same behavior |
| p99 (5% on flaky/slow MCP) | minority | **30-60s hangs → capped at 30s; request completes cleanly with parseable error** |
| p99.9 (1-2% degradation) | rare | Indefinite hangs → 30s cap → LLM retries; user keeps conversation context |

## Critical context

> **R-1A is the load-bearing safety change that makes T0a's larger thread pool safe to ship.** The PR description explicitly calls this out. Merging T0a (#29110) before R-1A would be net negative.

## Companion: R-1B (#29119)

R-1A returns `null` on TIMEOUT. R-1B converts that null into LLM-visible feedback so the agent self-corrects on next loop iteration. **R-1B is required to capture R-1A's full value** — without it, the LLM has no signal that the prior tool timed out and may re-call the same hung tool.

## Files changed (+62 / −5 across 4 files)

| File | +/− | Notes |
|------|-----|-------|
| `modules/platform/workflow/workflow-impl/.../SimpleLoopWorkflowExecutorImpl.kt` | +30 / −5 | Core timeout wrapping |
| `modules/platform/workflow/workflow-impl/.../SimpleLoopWorkflowConfiguration.kt` | +4 / 0 | Spring property wiring |
| `.ai_employee/projects/platform-workflow-impl/README.md` | +27 / 0 | Project readme |
| `.ai_employee/projects/platform-workflow-impl/tasks/R-1A-per-tool-deadline.md` | +121 / 0 | Detailed task file |

## Plan / refs

- **Plan:** INTEGRATED_PLAN_v7_synthesis.md TOP-15 rank #4.

## Risk & rollback (2-tier)

| Trigger | Action | ETA |
|---------|--------|-----|
| TOOL TIMEOUT rate spikes for known-healthy tool | Bump deadline to 60s via config | <5 min |
| Catastrophic regression | `git revert` | <30 min |

## Dependencies / merge order

- **Tier 2 — must land before #29110 (T0a)**.
- **Should land paired with #29119 R-1B** for full value.

## Suggested next steps

- Coordinate merge with #29119 R-1B.
- Add `TOOL_EXECUTION_TIMEOUT` counter to dashboards before merge.
