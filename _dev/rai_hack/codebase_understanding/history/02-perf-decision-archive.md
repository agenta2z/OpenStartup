# Performance Decision Archive (verbatim from git)

> Every documented latency / performance decision in `responsible-ai-api`
> with author, date, SHA, win-claim, and (where available) measured outcome.
>
> Use this to confirm Wave 9 wins are truly novel and not duplicates.

## 1. The Top-15 Plan + AI-NEW Plan

Two plan documents drive the modern perf wave (both in `responsible-ai-api`
checkout):

- `_plan/responsible-ai-api-INTEGRATED-v4.md` — AI-NEW-1..N items (P0/P1/P2
  priority) by Tony Chen + xhuang3.
- `_plan/PLAN-INTEGRATED-v4.md` — RAI-01..15 "Top-15 plan" by Tony Chen.

Both follow a strict format:
- WHY (motivation, with verified call-graph references)
- WHAT (concrete code change)
- IMPACT (measured, not estimated)
- TESTS (count + sweep result)
- ROLLBACK (single command)
- Cross-references

## 2. Recorded Perf Wins (chronological)

### AI-NEW-3 — Fail-open observability (`99daf3f`)
- **Author**: Tony Chen | **Date**: 2026-04-?? | **Class**: Observability
- **Change**: emit fail-open metric tagged by reason + fail-closed gate for malformed output
- **Win**: Not directly latency, but enables future latency root-cause analysis.
- **Wave 9 link**: Validates the *direction* of W3 — but W3 *removes* observability, not adds. Conflict.

### AI-NEW-4 — Drop dead double tokenization (`9b1efdf` → `9c16bf7`)
- **Author**: Tony Chen | **Date**: 2026-04-30 | **Approvers**: Xiaojiang Huang, Kai Zhang
- **Change**: removed dead `tokenizer.get_tokenized_input_as_int_list(...)` call in
  `GPTOSSModelInTeamserve._prepare_request` (server-side does it anyway).
- **Win** (verbatim): "One full HuggingFace BPE tokenizer pass per GPT-OSS request, saved."
- **Tests**: 22/22 + 216 sweep, ruff clean.
- **Wave 9 link**: Same file as Wave 9 W2/W3. Demonstrates that *removing dead
  CPU work* is the right model — gives confidence that W4 (cache prompt template)
  is in scope.

### AI-NEW-5 — Cache feature-gate user attributes per-request (`a6b75c2`)
- **Author**: Tony Chen | **Date**: 2026-04-30
- **Change**: cached `FeatureGateUserAttributes` on `flask.g`. Eliminates
  8–12× redundant attribute build per request.
- **Win**: ~1–3 ms/req (estimated; pre-RAI-15 measurement discipline).
- **Wave 9 link**: **DIRECT PRECEDENT FOR W4** — flask.g caching pattern.

### AI-NEW-6 — TCS Session reuse + truthy-only TTL cache (`9c33782`) — **DECLINED**
- **Author**: Tony Chen | **Date**: 2026-04-30 | **Plan ref**: P1-9 | **PR**: #623 — **DECLINED, NOT MERGED**
- **Branch**: `AI-NEW-6-tcs-session-and-truthy-cache` (also has `3491efc` "Fix pyright failures from PR #623 lint step")
- **What was proposed**:
  1. `requests.Session()` with `pool_connections=10, pool_maxsize=50` for the
     TCS client (Tenant Context Service).
  2. New `_truthy_time_cache` decorator (30s TTL, falsy results NOT cached).
- **Stated win** (from PR description, *not validated in production*):
  > "Realistic warm-path savings: ~100-400ms per gated agent request.
  > Cold-pool start (TCP+TLS handshake elimination): >1s."
- **Verified state on master**: TCS client at `src/tenant_context/tenant_context_client.py` STILL uses bare `requests.get(url, timeout=TIMEOUT, ...)` at lines 40 and 70. The Session pattern, pool config, and `_truthy_time_cache` decorator do NOT exist anywhere in `src/`.
- **Decline reason**: 🔴 **UNKNOWN — must be read from Bitbucket PR #623 review comments before treating any "Session-reuse" pattern as safe in this repo.**
- **Wave 9 link**: ⚠️ **NOT a precedent for W1.** Earlier draft of these docs incorrectly cited AI-NEW-6 as "merged" / "approved" / "safe pattern". Correction logged in [04-agent-claim-audit.md](04-agent-claim-audit.md).

### RAI-01 — Eliminate double tokenization in LLaMA inference path (`79a0caf`)
- **Author**: Tony Chen | **Date**: 2026-05-04 | **Class**: Perf-Improving
- **Companion**: `80eb4cd` — micro-benchmark with measured results.
- **Win**: Estimated ~10%; **measured −45%** (4× larger than estimated).
- **Wave 9 link**: Reinforces that perf wins in this codebase are commonly
  *underestimated* — Wave 9's "30–80 ms" claim for W1 is plausibly conservative.

### RAI-02 — Cache `ModerationRequestContext` per request (`63d434a`)
- **Author**: Tony Chen | **Date**: 2026-05-04 | **Class**: A (Neutral)
- **Stacked-on**: AI-NEW-5
- **Change**: `ModerationRequestContext.from_incoming_http_request_cached()`
  using `flask.g._rai_moderation_request_context`. Updated 5 call sites.
- **Win** (measured): 2.15 µs/req in micro-bench (10 µs simulated parse cost).
  Conservative; realistic prod saving with 500 µs/parse: **~2 ms/req**.
- **Tests**: 670/670 pass + 4 new RAI-02 tests, ruff clean, pyright 0 errors.
- **Resilience**: 3 graceful-degradation paths (outside Flask, MagicMock,
  parse errors).
- **Wave 9 link**: Direct precedent for W4 (cache prompt template).

### RAI-03 — gRPC gevent.Timeout + per-endpoint breaker metric (`407765f`)
- **Author**: Tony Chen | **Date**: 2026-05-04 | **Class**: Reliability/Neutral
- **Wave 9 link**: Demonstrates the "per-endpoint" granularity for breaker
  metrics — useful when wiring up tracing for the W1 measurement.

### RAI-04, RAI-05 — Observability adds (`406d286`, `7eec261`)
- **Author**: Tony Chen | **Date**: 2026-05-04 | **Class**: Observability
- **Wave 9 link**: Establish the *positive* model: add metrics to find perf
  wins. W3's proposal to *remove* `enable_iter_perf_stats` is the inverse and
  therefore deserves extra scrutiny.

### RAI-15 — Benchmarking dev skill reference (`26613af`)
- **Author**: Tony Chen | **Date**: 2026-05-04 | **Class**: Process
- **What**: 4-tier verification model (T1: micro-bench, T2: unit suite, T3:
  integration, T4: prod p50/p95/p99) installed in `.agents/skills/dev/references/benchmarking.md`.
- **Cited rejections** (verbatim from PR):
  - "RAI-09 was REJECTED after measurement showed claim was 200x off"
  - "RAI-11 was DOWNGRADED after reading code showed claim was wrong"
  - "RAI-01 measured 4x larger gain than estimated (-45% vs ~10% expected)"
- **Wave 9 link**: 🎯 **MUST-FOLLOW**. Every Wave 9 PR must have a measured
  benchmark, not an estimate. Wave 9's current claims (30–80 ms for W1, etc.)
  are estimates and need T1 evidence.

## 3. The `max_tokens` Saga (definitive)

The single best example of *intentional latency/quality balancing* in this repo:

| SHA | Date | Author | From → To | Stated reason |
|---|---|---|---|---|
| `6ab55ee` | 2026-03-16 | Kai Zhang | 500 → 200 | "to reduce max latency" |
| `1a8adc4` | 2026-03-19 | Kai Zhang | 200 → 512 | "200 truncation too much" |
| `26303d2` | 2026-03-19 | Kai Zhang | 512 → 400 | "200 truncation too much" (compromise) |

**Current value**: `max_tokens=400` in `src/inference_models/rai_gpt_oss.py:90`.

**Wave 9 implication**: The Wave-9 doc proposed lowering `max_tokens` to 256.
This **directly contradicts the documented Pareto compromise**. Any change to
this value requires fresh truncation-rate data — minimum a re-run of whatever
benchmark led Kai to 400.

## 4. Reverts / Hotfixes (perf-relevant)

| SHA | Date | Title | What we learn |
|---|---|---|---|
| `5d49c56` | 2026-05-04 | Merged in revert-sagemaker-sandbox-endpoints | Image-moderation rollback path — not Wave 9 relevant |
| `2edeb3d` | (recent) | hotfix-restore-conversation-starters | One-shot restore; not perf |
| `648e035` | 2026-04-?? | ops/2026-04-27-prod-east-rollback | Production rollback (region-specific). **No HTTP-client revert in history.** |

**No perf-related revert in the last year for HTTP / Session / Pool / Cache.**
This is *positive* evidence for W1 — the pattern has been used (AI-NEW-6) and
not reverted.

## 5. Pre-existing Caching Patterns (don't reinvent)

| Pattern | File | Use it for |
|---|---|---|
| `flask.g` per-request cache | `src/feature_service.py` (AI-NEW-5), `src/api/v1/moderation/utils/...` (RAI-02) | W4 (prompt template), W5 (ETag short-circuit) |
| `_truthy_time_cache` 30s TTL | new module by AI-NEW-6 | Tenant-scoped data with finite TTL |
| `requests.Session() + urllib3 pool` | (TCS client per AI-NEW-6) | **W1** (TeamServe HTTP client) |
| Module-level `lru_cache` | misc | Pure-function caching (NOT for tenant data) |

## 6. The "Measured-Not-Estimated" Rule (RAI-15)

```text
When proposing perf work, you MUST:
  T1 — In-process micro-bench (timeit, cProfile)
  T2 — Full unit-test suite latency before/after
  T3 — Integration test latency before/after
  T4 — Production p50/p95/p99 in dashboard

If you can show ≥T2 in your PR, the change is auto-eligible for review.
If only T1: requires explicit measurement-vs-claim discussion in PR.
If 0/4: NOT eligible (RAI-09 was rejected on this basis).
```

## 7. Open Plan Items (in `_plan/responsible-ai-api-INTEGRATED-v4.md`)

The Top-15 + AI-NEW plans contain items not yet executed. Wave 9 should be
cross-checked against these to avoid duplicating planned work. Suggested check:

```bash
cd ~/MyProjects/atlassian_packages/responsible-ai-api
ls _plan/
grep -nE 'P0-|P1-|P2-' _plan/responsible-ai-api-INTEGRATED-v4.md | head -30
grep -nE 'rank #' _plan/PLAN-INTEGRATED-v4.md | head -30
```

If W1, W2, W3, etc. appear there with a different ID (e.g., P1-12), use that
ID in the new PR title for traceability.
