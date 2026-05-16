# PR #29099 — A10: Partial JSON recovery for malformed LLM responses (3-tier)

**Impact label:** 🟡 **MEDIUM** &nbsp;•&nbsp; **State:** OPEN &nbsp;•&nbsp; **Branch:** `tchen7/rovo-insights/A10-partial-json-recovery` → `main`
**Created:** 2026-05-04 07:35 UTC &nbsp;•&nbsp; **Last updated:** 2026-05-15 02:10 UTC &nbsp;•&nbsp; **Comments:** 3 &nbsp;•&nbsp; **Tasks:** 2
**URL:** https://bitbucket.org/atlassian/conversational-ai-platform/pull-requests/29099

## TL;DR

Three-tier JSON parsing for LLM responses: STRICT → SUBSTRING (handles prose-prefix / markdown fencing) → PER-ELEMENT (recovers from a single bad element in an array). **Recovers +1-2 insights per type during malformed responses** (categorical: 0 → some).

## Why this is MEDIUM impact

- **Conditional UX win:** only triggers on malformed LLM responses (~5-10% during model degradation).
- **Happy path is byte-for-byte unchanged** (no regression risk).
- Categorical recovery from "entire-type loss" failure mode.

## Three-tier strategy

| Tier | Strategy | Counter |
|------|---------|---------|
| **1 — STRICT** | `objectMapper.readValue(response, listType)` (default; happy path unchanged) | none on success |
| **2 — SUBSTRING** | Find first `[` and last `]`; parse substring (handles prose prefix, markdown fencing) | `tier=substring` |
| **3 — PER-ELEMENT** | Tokenize array, parse each element; collect successful, skip failures | `tier=per_element` |
| **No recovery** | Re-throw original Jackson exception (preserves caller semantics; `retryable()` decides retry) | `tier=none` |

## Three concrete LLM failure modes recovered

1. **Prose prefix/suffix:** LLM says `"Sure! Here are your insights: [...]"` → substring extracts JSON.
2. **Markdown fencing:** LLM wraps in ` ```json ... ``` ` → substring extracts JSON.
3. **Single bad item:** `[{good}, {malformed}, {good}]` → per-element returns 2 of 3 instead of 0.

## Claimed impact (per Plan v4 §5.5)

| Dimension | Impact |
|-----------|--------|
| Cost | NEUTRAL (no LLM call change) |
| Throughput | NEUTRAL on happy path |
| User-visible insight count | **+1-2 per type during malformed responses** |
| Stability | **MAJOR** — eliminates entire-type-loss failure mode |

## Files changed (+266 / −2 across 4 files)

| File | +/− | Notes |
|------|-----|-------|
| `RovoInsightsServiceImpl.kt` | +109 / −1 | 3-tier parse logic + metric |
| `RovoInsightsServiceImplTest.kt` | +83 / −1 | 6 new test cases; strict-path tests unchanged |
| `A10-partial-json-recovery.md` | +69 / 0 | Detailed task file |
| `MetricKey.kt` | +5 / 0 | New `ROVO_INSIGHTS_JSON_RECOVERY` metric |

## Test results

- **All 18/18 PASS**: 6 new (strict-happy, prose-prefix, markdown-fenced, per-element-bad-item, all-bad, empty-array) + 12 prior.

## Plan / refs

- **Plan:** PLAN-INTEGRATED-v4.md §5.5 rank #7. NEW item (v3 missed it).

## Risk & rollback (3-tier)

| Trigger | Action | ETA |
|---------|--------|-----|
| Recovery returns wrong data (impossible on happy path) | `git revert` | <15 min |
| `ROVO_INSIGHTS_JSON_RECOVERY{tier=*}` > 10% | Investigate prompt/model regression | <1 hour |
| Compile failure | `git revert` | <15 min |

## Dependencies / merge order

- **Independent.** Compounds with A9 (#29097 backoff) — both reduce retry pressure during incidents.

## Suggested next steps

- Get review approval.
- Add `ROVO_INSIGHTS_JSON_RECOVERY{tier=*}` to dashboards; monitor distribution post-deploy.
