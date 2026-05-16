# PR #29120 — L1: Per-execute tool-schema cache (skip redundant Jackson parses)

**Impact label:** 🟡 **MEDIUM** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `L1-tool-schema-per-execution-cache` → `main`
**Created:** 2026-05-04 13:48 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 5 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29120

## TL;DR

Adds a per-execute `ConcurrentHashMap<String, ToolSchema>` cache to skip redundant FF-lookups + Jackson parsing across agent-loop iterations. Measured **7.89× speedup** (396.3 µs → 50.2 µs per request) — but at 346 µs/req aggregate, **not user-perceptible** at single-request level. **Fleet aggregate win** (~1% CPU headroom on agent-loop threads).

## Why this is MEDIUM (not High)

- **Honest analysis (per PR description):** 346 µs against typical TTFT of 200-800 ms = **unperceptible** at single-request level.
- **Fleet aggregate win:** 346 µs × millions of req/day = measurable CPU headroom.
- **Defers thread-pool saturation under sustained burst** — this is real but conditional.
- Per-component speedup is dramatic (7.89×) but absolute time saved is small.

## What it changes

| Aspect | Before | After |
|--------|--------|-------|
| Per-request schema operations (50 tools × 5 loops) | 250 FF-lookups + 250 Jackson parses | 50 FF-lookups + 50 Jackson parses (1 per tool, then cached) |
| Cache lifecycle | n/a | Per `execute()` call (allocated fresh, discarded with return) |
| Backwards compat | n/a | Original `getToolSchemas(toolRegistrations)` overload preserved |

## Measured benchmarks (real call-path microbench)

| Metric | Pre-L1 | Post-L1 | Δ |
|--------|--------|---------|---|
| Per-request time | 396.3 µs | 50.2 µs | **7.89× faster (-87.32%)** |

## Honest user-perceived translation

| Dimension | Impact |
|-----------|--------|
| Per-request CPU saving | ~346 µs (sits BEFORE LLM streaming) |
| Single-user perception | **Unperceptible** (TTFT 200-800 ms baseline) |
| Fleet-level | ~346 µs × millions req/day = ~1% agent-loop-thread CPU freed |
| Sustained burst | Defers thread-pool saturation (compounds with T0a) |

## Files changed (+320 / −3 across 5 files)

| File | +/− | Notes |
|------|-----|-------|
| `L1ToolSchemaCacheMicroBenchmark.kt` | +121 / 0 | Real call-path v2 microbench |
| `L1-tool-schema-per-execution-cache.md` | +101 / 0 | Task doc |
| `SimpleLoopWorkflowExecutorImplTest.kt` | +50 / 0 | 1 cache-hit regression test |
| `.ai_employee/projects/.../README.md` | +27 / 0 | Project readme |
| `SimpleLoopWorkflowExecutorImpl.kt` | +20 / −3 | Cache var + overload |

## Plan / refs

- **Plan:** INTEGRATED_PLAN_v7_synthesis.md TOP-15 rank #6 (latency pillar).
- **Compounds with:** #29121 C2 (same hot path).

## Risk & rollback

- **Risk:** LOW — cache is per-execute (not class-level), so no cross-request leak risk.
- **Rollback:** `git revert` <15 min.

## Dependencies / merge order

- **Independent.** Compounds with C2 (#29121) on the agent-loop hot path.

## Suggested next steps

- Get review from platform-workflow-impl owners.
- Land paired with C2 (#29121) for combined hot-path latency win.
