# PR #29111 — T0b: Heimdall timeout 3000ms → 500ms

**Impact label:** 🔴 **HIGH** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `T0b-heimdall-timeout` → `main`
**Created:** 2026-05-04 11:36 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:09 UTC &nbsp;•&nbsp; **Comments:** 0 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29111

## TL;DR

Tightens Heimdall (rate-limiter) timeout from **3000ms → 500ms**. **Saves 2.5s of TTFT delay during Heimdall degradation** (a quarterly-ish auth-service incident pattern). At 500ms, still > 5× Heimdall's healthy p99 (~50-100ms). Fail-open semantics preserved.

## Why this is HIGH impact

- **2.5s TTFT improvement is user-perceptible** during degradation events (~10-15% of sessions during event windows).
- **Removes the dominant p99 contribution during Heimdall incidents.**
- **Fail-open preserved** — only latency impact, not correctness.

## What it changes

| Setting | Before | After |
|---------|--------|-------|
| Heimdall timeout | 3000ms | 500ms |
| Healthy p99 buffer | 30-60× headroom (overkill) | 5-10× (still safe) |

## Honest user-perceived translation

| Heimdall state | Frequency | Impact |
|---------------|-----------|--------|
| Healthy (~50-100ms) | normal | **Identical** — no change |
| Degraded (~3s) | quarterly incidents, 10-15% sessions | **TTFT delayed ~3s → ~0.5s** (2.5s faster) |
| Down | rare | 3s → 0.5s (**6× better latency**) |

## Files changed (+109 / −2 across 3 files)

| File | +/− | Notes |
|------|-----|-------|
| `modules/foundation/utilities/utilities-impl/.../ExperienceRateLimitFilter.kt` | +6 / −2 | Core change (timeout constant) |
| `.ai_employee/projects/foundation-utilities-impl/README.md` | +24 / 0 | Project readme |
| `.ai_employee/projects/foundation-utilities-impl/tasks/T0b-heimdall-timeout.md` | +99 / 0 | Detailed task file |

## Plan / refs

- **Plan:** INTEGRATED_PLAN_v7_synthesis.md TOP-15 rank #3.

## Risk & rollback (2-tier)

| Trigger | Action | ETA |
|---------|--------|-----|
| Heimdall p99 climbs above 500ms | Revert to 3000ms via config | <5 min |
| Catastrophic regression | `git revert` | <30 min |

## Dependencies / merge order

- **Independent** — can land any time. Low-risk; high-value during the next Heimdall incident.

## Suggested next steps

- Land first (low risk, immediate p99-during-incident win).
- Add Heimdall p99 to monitoring with alarm at 400ms (so we hit before the new 500ms timeout).
