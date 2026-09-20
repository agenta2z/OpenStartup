# RAI Hack — PLAN-INTEGRATED-v4.md
## Goal-Driven, Impact-Ranked, Code-Verified, PR-Deduplicated

> **Status**: v4 Final — 2026-05-04
> **Constraint**: No user-facing behaviour changes. Internal only.
> **Sources of truth**: Live code reads + PR #620 and #622 exact diff scope
> **Task files**: `responsible-ai-api/tasks/RAI-XX-*.md` (one per item)
> **Commit style**: See §Conventions/Commit description format below

---

## PR Exclusion Boundary (do not re-implement)

| PR | Exact scope | Status |
|---|---|---|
| **PR #620** | `FailOpenReason` enum (4 values); `_emit_fail_open_metric()`; `ENABLE_FAIL_CLOSED_ON_MALFORMED_OUTPUT` gate; dashboard chart; operator runbook; 14 new tests | OPEN |
| **PR #622** | `_get_or_build_user_attributes()` caches `FeatureGateUserAttributes` in `flask.g`; `_GATE_USER_ATTRS_G_ATTR` class constant; 5 new tests; 670 passing. Explicitly rejected: full gate-result caching; ModerationRequestContext caching for controllers | OPEN |
| **PR #621** | GPT-OSS dead tokenization path removal | OPEN |

---

## Production Context

| Metric | Value |
|---|---|
| Prompt moderation traffic share | **98.9%** |
| P95 latency (prod-east, 2026-04-26) | **2,152ms** vs 1,000ms P90 SLO — 2.15× over |
| Traffic growth | +243% in 4 weeks (1,953 → 6,692 req/min) |
| Reliability SLO | 99.7% (prompt), 99.5% (agent/image) |

---

## Tasks Index

| ID | Title | Priority | Effort | UX-Class | Status | PR |
|---|---|---|---|---|---|---|
| RAI-01 | Eliminate double tokenization (LLaMA) | **P0** | M | A (Neutral) | todo | N/A |
| RAI-02 | Cache ModerationRequestContext (2 remaining callers) | **P0** | XS | A (Neutral) | todo | N/A |
| RAI-03 | gRPC healthcheck + gevent-native hard timeout | **P0** | M | A (Neutral) | todo | N/A |
| RAI-04 | Parser fallback metrics + CONSTRAINT comments (AI-126) | P1 | M | A (Neutral) | todo | N/A |
| RAI-05 | `rai.model.selected` metric per request | P1 | XS | A (Neutral) | todo | N/A |
| RAI-06 | Output moderation debug trace (AI-114) | P1 | S | A (Neutral) | todo | N/A |
| RAI-07 | Delete dead config classes + unreachable gated code | P1 | S | A (Neutral) | todo | N/A |
| RAI-08 | Unify inference model layer: `BasePromptModerationModel` (AI-127) | P1 | L | A (Neutral) | todo | N/A |
| RAI-09 | Feature gate lifecycle audit + annotations (AI-128) | P2 | M | A (Neutral) | todo | N/A |
| RAI-10 | ETag: prefix-match instead of category enumeration | P2 | S | A (Neutral) | todo | N/A |
| RAI-11 | Pre-compile inline regexes in parser | P2 | XS | A (Neutral) | todo | N/A |
| RAI-12 | Parser test coverage floor raise (74%→90%) | P2 | M | A (Neutral) | todo | N/A |
| RAI-13 | Unify `MalformedModelOutput` error classes | P3 | XS | A (Neutral) | todo | N/A |
| RAI-14 | Add 1 agent moderation test (29→30) | P3 | XS | A (Neutral) | todo | N/A |
| RAI-15 | Document stream in-process state constraint (AI-122) | P3 | XS | A (Neutral) | todo | N/A |
| RAI-16 | Deprecate `is_fail_open_case()` heuristic (post-PR #620, ≥14d) | P3 | XS | A (Neutral) | todo | N/A |

---

## Corrections Log (applied — do not re-propose these)

| Claim | Source | Verdict |
|---|---|---|
| Cache full `_check_gate` results by gate name | stonebraker ITEM 3 | ❌ WRONG — `agent_moderation_controller.py` checks `is_analytics_disabled()` (L156) and `is_user_input_logging_enabled()` (L247) BEFORE `apply_debug_overrides()` (L253). Gate-result caching → stale values. PR #622 rejected this explicitly. |
| Cache ModerationRequestContext for controllers | stonebraker ITEM 2 | ❌ WRONG for controllers — they hold context as local variable. 2 uncached callers remain: `micros_logging.py:32` + `feature_service.is_use_case_allowed():240`. RAI-02 covers them. |
| "14× SHA-256 per ETag check" → 10–15ms saving | rai_hack v1 | ❌ WRONG — `get_category_hash()` is `@functools.cache`. Real: ~1ms. |
| "Regex precompile saves 2.5–5ms" | rai_hack v1 | ❌ OVERSTATED — Python `re` has 512-entry LRU cache. Real: ~0.05ms. Code clarity only. |
| Double tokenization saves 20–50ms | stonebraker | ✅ CORRECT — lines 330+394 (`LlamaModel`), 434+500 (`LlamaModelInTeamserve`). |
| 2 uncached ModerationRequestContext callers remain | New finding | ✅ CONFIRMED — not in either prior plan. |
| gRPC incident → 22,260 errors, 27–75s block time | rai_hack v1 | ✅ CORRECT and underweighted in stonebraker. P0. |

---

## Execution Sequence

```
Phase 1 — Quick wins, additive only (after PRs #620/#621/#622 merge):
  RAI-02  Cache ModerationRequestContext 2 remaining callers  (XS, zero risk)
  RAI-05  Model selection metric                               (XS, additive)
  RAI-11  Pre-compile parser regexes                          (XS, code clarity)

Phase 2 — High-impact performance + reliability (Week 1–2):
  RAI-01  Double tokenization fix                             (M, needs boundary tests)
  RAI-03  gRPC healthcheck + gevent timeout                   (M, incident prevention)
  RAI-04  Parser fallback metrics                             (M, safety observability)

Phase 3 — Completeness (Week 2–3):
  RAI-06  Output debug trace                                  (S)
  RAI-07  Dead code deletion                                  (S, verify gate % first)
  RAI-10  ETag prefix-match                                   (S)

Phase 4 — Architecture (Weeks 3–5):
  RAI-08  Inference model unification                         (L, requires RAI-01 first)
  RAI-09  Gate lifecycle audit                                (M)
  RAI-12  Parser coverage floor raise                         (M, after RAI-04 bakes)

Phase 5 — Polish (ongoing):
  RAI-13  Unify MalformedModelOutput                          (XS)
  RAI-14  Agent test +1                                       (XS)
  RAI-15  Document stream constraint                          (XS)
  RAI-16  Deprecate is_fail_open_case()                       (XS — after PR #620 ≥14d in prod)
```

---

## Out of Scope

| Excluded | Reason |
|---|---|
| Cache full `_check_gate` results | Correctness hazard — overrides set after some gate calls in agent controller |
| Changing ALLOWED/DISALLOWED thresholds | User-facing: changes moderation decisions |
| Adding new harm categories | Product scope |
| Changing response body schema | Breaking API change |
| Switching model versions (LLaMA → GPT-OSS) | Operational decision |
| ML model accuracy improvements | ML team responsibility |

---

## Conventions

### Finishing a task

1. Change `Status:` in the task file to `shipped-pending-merge` + add `PR: #NNN`
2. Write a session log in `agentic-coding-logs/YYYY-MM-DD-HHMMSS-short-topic.md`
3. After merge: change `Status:` to `shipped`, fill `## Lessons learned`
4. `git mv tasks/RAI-XX-*.md tasks/done/RAI-XX-*.md`
5. Remove the row from the Tasks Index table above

### Commit description format

Follow this style exactly (from the project Rovo Insights precedent):

```
<plan item rank and title>

Plan: PLAN-INTEGRATED-v4.md §<section> rank #<N>
Task file: tasks/RAI-<XX>-<kebab-title>.md
UX classification: A (Neutral) | B (Improving) | C (Affecting — PM sign-off required)

📚 WHY (motivation)
<concrete problem statement with code paths/metrics/incident links>

🔧 WHAT (overview)
<what changed, with before/after snippets or pseudocode>

📊 IMPACT — measurable, falsifiable claims
| Metric | Pre | Post | Improvement |
|--------|-----|------|-------------|

✅ TESTS — ALL PASS
<test count and results>

🔄 ROLLBACK
| Trigger | Action | ETA |
|---------|--------|-----|

Cross-references
<compound items, plan sections, prior incidents>

DoD checklist
- [ ] Code compiles
- [ ] New tests added and pass
- [ ] Full unit test suite passes
- [ ] Coverage floors held
- [ ] Session log committed
- [ ] Task file Status → shipped-pending-merge
```

### Task file naming

```
tasks/RAI-<XX>-<kebab-title>.md           live
tasks/RAI-<XX>-REJECTED-<title>.md        rejected (stays in tasks/, not moved to done/)
tasks/RAI-<XX>-DEFERRED-<title>.md        deferred
tasks/done/RAI-<XX>-<kebab-title>.md      shipped
```

### Test SOP (quick reference)

```bash
# Unit tests (fast, ~12s)
bin/unit-test

# Unit tests + coverage gates (~18s)
bin/unit-test --coverage

# Coverage floor view
uv run python bin/check-coverage-floors --print

# Full CI equivalent
pre-commit run --all-files && bin/unit-test --coverage

# Integration (local sandbox)
atlas nebulae start --export-env=env.json   # terminal 1
bin/start-app-locally.sh                    # terminal 2
bin/integration-test --smoke                # terminal 3

# Load test baseline (for RAI-01, RAI-02, RAI-03)
locust -f test/capacity/prompt_moderation.py \
  --host https://responsible-ai-api.us-east-1.staging.atl-paas.net \
  --users 400 --spawn-rate 20 --run-time 300s --headless --csv=baseline
```


---

## Convention: Files NOT tracked in PRs

**Established 2026-05-04 from RAI-01 retrospective** (PR #629 originally contained 130+ contaminated files from prior agent state).

The following paths are **agent-internal, per-engineer artifacts** and MUST NOT appear in pull requests:

| Path | Purpose | Where it actually lives |
|---|---|---|
| `.agents/` | Agent skills, scripts, runbooks (per-engineer) | Local + workspace docs |
| `agentic-coding-logs/` | Per-session reasoning logs | Local only |
| `agentic-ops-logs/` | Per-session ops investigation logs | Local only |
| `tasks/` | Per-engineer plan task files (RAI-01.md, etc.) | Local + this plan folder |
| `AGENTS.md` | Per-engineer agent invocation rules | Local + workspace docs |
| `PLAN.md` | Per-engineer rolling plan | This folder (`rai_hack/_plan/`) |

**Source-of-truth for these artifacts** lives in `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/_plan/rai_hack/`, NOT in the repo.

### Enforcement

1. **`.gitignore` patterns added in PR #629** prevent NEW additions:
   ```gitignore
   .agents/
   agentic-coding-logs/
   agentic-ops-logs/
   tasks/
   AGENTS.md
   PLAN.md
   ```

2. **Existing tracked files in those paths** require a separate `git rm --cached` cleanup PR (out-of-scope for any feature PR).

3. **Per-PR checklist additions** (now part of every task DoD):
   - [ ] PR diff contains ONLY files relevant to the change
   - [ ] No `.agents/`, `agentic-*-logs/`, `tasks/`, `AGENTS.md`, or `PLAN.md` files in diff
   - [ ] Verified via `git diff --name-status master..HEAD` before push

### Why this matters

- **Review hygiene**: reviewers should not have to skim through hundreds of unrelated agent-state files
- **Merge conflicts**: agent state changes per-engineer, would conflict constantly
- **Security**: agent runbooks may reference local paths, internal URLs, or secrets
- **Velocity**: a PR with 130 files is unmergeable; a PR with 3 files merges in minutes

### Workflow correction (applied retroactively)

The previous workflow created task files in `responsible-ai-api/tasks/` and session logs in `responsible-ai-api/agentic-coding-logs/`. Going forward:

- **Task files** live in `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/_plan/rai_hack/_plan/tasks/RAI-XX-*.md`
- **Session logs** live in `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/_plan/rai_hack/_plan/sessions/YYYY-MM-DD-HHMMSS-*.md`
- **Both reference the PR by URL**, not the other way around


---

## Convention: Quantitative impact claims must be MEASURED, not estimated

**Established 2026-05-04 from RAI-01 retrospective** (PR #629 originally claimed "≥10% reduction (load test pending)"; we then ran a real micro-benchmark and found the actual number was **−45.3% aggregate, −22–−49% per prompt class** — the truth was 4× better than the placeholder).

### The rule

For any plan item where the claimed impact is a quantitative metric (latency, throughput, CPU, memory, accuracy, error rate, etc.), the PR MUST include:

1. **A reproducible benchmark or test script** committed to the proper test path
2. **A `RESULTS.md` (or equivalent) with measured before/after numbers**
3. **A "Reproduce" section in the PR description** with the exact command to re-run

A vague "expected ~X% reduction" is no longer acceptable for items in the plan with a quantitative impact column.

### Where benchmarks live

| Type | Path | When to use |
|---|---|---|
| **Python micro-benchmark** | `test/capacity/microbench/bench_<thing>.py` + `RESULTS.md` | Isolating CPU work of a single function or module. Mocks I/O, runs in-process. Reproducible in <1 minute. |
| **Locust load test** | `test/capacity/<endpoint>.py` (already established) | Full HTTP path; needs Nebulae or deployed target. Measures real RPS/P95/P99 under sustained load. |
| **Perfhammer capacity** | `test/capacity/perfhammer-definitions/<endpoint>.json` | Production-grade certification. Used pre-prod deploy or for SLO validation. |
| **Pytest benchmark** | `test/unit_tests/benchmarks/test_<thing>_bench.py` | Property-based or comparative bench in unit-test infra. Use `pytest-benchmark` if added to deps. |

### When each layer is appropriate

| Question the change answers | Use |
|---|---|
| "How much CPU time does this function take?" | Micro-benchmark (`test/capacity/microbench/`) |
| "What's the end-to-end latency under load?" | Locust against Nebulae or staging |
| "Will this hold under production capacity?" | Perfhammer pre-prod sweep |
| "Did we regress in production?" | SignalFx dashboard observation, ≥1 week post-deploy |

### What goes in the PR description

For any quantitative-impact PR:

```markdown
### IMPACT — measured (not estimated)

Methodology: <N> warmup + <M> measured iterations, <what's mocked vs real>, <env>

| Metric | Before | After | Saved | % reduction |
|---|---:|---:|---:|---:|
| ... | ... | ... | ... | **−X%** |

### Reproduce
```bash
<exact command>
```

### Caveats
- <what the bench does NOT measure>
- <what end-to-end production validation is still needed>
```

### Anti-pattern (now forbidden)

```markdown
### IMPACT
Expected ~10% reduction in P95 latency (load test pending).
```

This is a guess, not an impact claim. Either:
- Run the bench and put real numbers in, OR
- Mark the item as a code-quality / observability change with no quantitative claim, OR
- Commit a runnable bench skeleton with a `Status: blocked-on-load-test` note.

### Lessons from RAI-01

1. **The bench can save you from over- or under-claiming.** RAI-01 estimated 10% but delivered 45%; without the bench we'd have under-sold the win. Other items might over-claim — the bench reveals the truth either way.
2. **Even a mocked-I/O bench is credible** when you're isolating CPU work. The harness in `test/capacity/microbench/bench_llama_tokenization.py` mocks the upstream HTTP endpoint but uses the real production tokenizer + template — that's enough to attribute the delta to the change under test.
3. **Production end-to-end will always look smaller** than the micro-bench because of upstream latency dominance. Always note this caveat. Don't promise a 45% E2E P95 reduction from a 45% CPU reduction when the upstream model is the bottleneck.
