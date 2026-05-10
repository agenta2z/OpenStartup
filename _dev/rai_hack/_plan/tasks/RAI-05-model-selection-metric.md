# RAI-05 — Model selection metric

Status: in_progress
Priority: P1
UX-Class: A (Neutral)
PM-Sign-off: N/A
Plan: PLAN-INTEGRATED-v4.md rank #5
PR: pending
Jira: not-tracked
Author: Tony Chen
Date opened: 2026-05-04

## Problem

| Issue | Evidence |
|---|---|
| No live observability into which inference model serves each prompt moderation request | `src/service/moderation/prompt/prompt_moderation.py:76-83` chooses GPT-OSS or LLaMA via `feature_service.is_gpt_oss_safeguard_enabled()` but emits no metric naming the chosen model |
| GPT-OSS rollout safety blocked: cannot diff per-model latency, error rate, or fail-open rate from a single dashboard query | `model_evaluation_version` tag exists on outcome/latency metrics but only the LLaMA shadower (`shimmed_*`) writes to it via `model.version`; no clean per-request "which model served this request" signal |

The prompt moderation hot path serves ~98.9% of production traffic via two model variants. A staged rollout of GPT-OSS Safeguard depends on being able to attribute KPIs (P95 latency, fail-open rate, harm-category distribution) to each variant in real time. We have the data structurally (every model has `.version`) but no metric emits it.

## Approach

1. Add `MetricTag.MODEL_SELECTED = "model_selected"` to `metrics_handler.py`.
2. Add `Metric.PROMPT_MODERATION_MODEL_SELECTED = MetricDef.prompt_moderation("model_selected")`.
3. In `predict_harm_category_in_prompt()`, after the model is chosen, call `send_metric(Metric.PROMPT_MODERATION_MODEL_SELECTED, value=1, tags={MODEL_SELECTED: model.version, USE_CASE_ID: ...})`.
4. Identical hook for `agent_moderation.py` (also picks between models).
5. Unit tests: assert the metric is emitted exactly once per request with the right `model_selected` tag for both GPT-OSS and LLaMA paths.

## UX Classification rationale (5-question form)

| Question | Answer |
|---|---|
| Does this change what users see? | NO |
| Does this change when users see it (freshness)? | NO |
| Does this remove any user-facing feature? | NO |
| Does this add user-perceived latency? | NO — single counter increment, microseconds |
| If any YES → is this Cat C with PM sign-off attached? | N/A — all NO → **Cat A (Neutral)** |

## Acceptance criteria

- [ ] `grep -c "MODEL_SELECTED" src/metrics/metrics_handler.py` → ≥1
- [ ] `grep -c "PROMPT_MODERATION_MODEL_SELECTED" src/metrics/metrics_handler.py` → ≥1
- [ ] `grep -c "PROMPT_MODERATION_MODEL_SELECTED" src/service/moderation/prompt/prompt_moderation.py` → ≥1
- [ ] `bin/unit-test test/unit_tests/service/moderation/prompt/` → all pass
- [ ] New tests: `test_emits_model_selected_metric_for_gpt_oss`, `test_emits_model_selected_metric_for_llama`
- [ ] `uv run ruff check src/ test/` → clean
- [ ] `uv run pyright src/metrics src/service/moderation/prompt` → 0 errors

## Impact

### Claimed (additive observability — not a perf optimization)

| Metric | Before | After |
|---|---|---|
| `rai.prompt_moderation.model_selected` counter | does not exist | emitted once per request, tagged with model version (`V2_4_teamserve`, `gpt_oss_safeguard_20b`, etc.) |
| Per-model rollout dashboard query | not possible | possible via `sum_by(model_selected)` |
| Per-model fail-open rate diff | requires log scrape | possible by joining `model_selected` × `fail_open` tags |

### Measured

CPU cost: a single `send_metric` call adds ~5–10 µs to the hot path (one dict alloc + statsd UDP write). This will be measured by extending the existing `bench_llama_tokenization.py` harness to count the metric call.

## Rollback plan

| Trigger | Action | ETA |
|---|---|---|
| Metric volume floods statsd backend | Revert single commit; metric definition is purely additive so revert is safe | <5 min |
| Tag cardinality alarm fires | Revert; cardinality is bounded by ~5 model versions | <5 min |

## Cross-references

- **Compounds with**: RAI-08 (inference model unification — once unified, the metric stays the same since `model.version` is on the base class).
- **Plan**: PLAN-INTEGRATED-v4.md rank #5
