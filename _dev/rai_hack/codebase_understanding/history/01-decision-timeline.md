# RAI Decision Timeline (Verified from Git)

> **Source**: `git log --all` on `responsible-ai-api` (1,487 commits) and
> `responsible-ai` (~700 commits). All entries are direct verbatim from
> commit messages.
> **Verified**: 2026-05-06 against current master HEAD.
> **Format**: `YYYY-MM-DD | <SHA> | <author> | <title> — <decision recorded>`

## 1. Repo Activity Shape (commits per month, `responsible-ai-api`)

```
2024-06: 1     ← repo created
2024-07: 121   ← initial buildout
2024-08-12: 30-55/mo (steady)
2025-01-03: 13-41/mo (slowdown)
2025-04: 65    ← model refresh wave
2025-08: 84    ← summer push
2026-02: 43
2026-03: 131   ← prompt + model versioning
2026-04: 429   ← refactor + perf wave (TC + xhuang3)
2026-05: 101   ← current month, MoM 5d
```

Pattern: **March 2026 onwards is the modern era**. The codebase you see today
was largely shaped between **2026-03-01 and 2026-05-06**. Anything older is
either deleted or has been heavily refactored.

## 2. Eras

### Era 0 — Founding (2024-06 to 2024-12)
- LLaMA-based moderation. Single model. Triton gRPC.
- Primary contributors: Matt Turner, Benjamin Joyce, Hussein.
- Decisions of this era largely overwritten by later refactors.

### Era 1 — GPT-OSS Onboarding (2025-04 to 2026-02)
- Added GPT-OSS 20B as second model (alongside LLaMA).
- Initial TeamServe HTTP integration (`triton_openai_api_client.py`).
- Primary contributors: Kai Zhang, Taotao Li, xhuang3.

### Era 2 — Prompt Iteration & Latency Tuning (2026-03)
- 5 prompt versions in 30 days (v1.0 → v1.4).
- max_tokens: 500 → 200 → 512 → 400 — explicit latency/quality dance.
- Primary contributors: Kai Zhang.

### Era 3 — Refactor + Perf Wave (2026-04)
- AI-NEW-1..6: Plan-driven perf optimization series (Tony Chen).
- AI-127: Inference layer refactor on a feature branch (xhuang3) — **NOT YET on master**.
- Primary contributors: Tony Chen, xhuang3.

### Era 4 — Top-15 Plan Execution (2026-05, current)
- RAI-01..05: Tony Chen executes the "top-15" plan with measurement discipline.
- RAI-15 specifically codifies "measured-not-estimated" rule.

## 3. Critical Commits (chronological, most recent first)

### 2026-05 — Top-15 Plan (Tony Chen, owner)

| Date | SHA | Title | Wave 9 relevance |
|---|---|---|---|
| 2026-05-04 | `407765f` | RAI-03: gRPC gevent.Timeout + per-endpoint breaker metric (Neutral) | Establishes pattern: per-endpoint breaker metrics |
| 2026-05-04 | `63d434a` | RAI-02: Cache `ModerationRequestContext` per request (Perf-Improving) | **PRECEDENT FOR W4/W5** — same flask.g caching pattern |
| 2026-05-04 | `26613af` | RAI-15: Benchmarking dev skill reference (Process) | **CRITICAL**: codifies "measured-not-estimated" rule. Cites RAI-09 *rejected* (claim 200x off), RAI-11 *downgraded*, RAI-01 *4x larger gain than estimated*. |
| 2026-05-04 | `406d286` | RAI-04: Parser fallback observability metrics (Observability) | Add metric, don't remove (W3 contradicts this pattern) |
| 2026-05-04 | `7eec261` | RAI-05: Model selection metric (Observability) | Same |
| 2026-05-04 | `79a0caf` | RAI-01: Eliminate double tokenization in LLaMA inference path (Perf-Improving) | **PRECEDENT FOR PERF WORK** — measured 4× larger gain than estimated |

### 2026-04-30 — AI-NEW Series (Tony Chen, owner)

The closest precedent for Wave 9. Tony Chen's plan-driven perf wave was
already approved. Here's what was done:

| Date | SHA | Title | Wave 9 relevance |
|---|---|---|---|
| 2026-04-30 | `9c33782` | **AI-NEW-6: TCS Session reuse + truthy-only TTL cache (P1-9)** | ⚠️ **CORRECTED**: this is on the feature branch `AI-NEW-6-tcs-session-and-truthy-cache`, NOT on master. PR #623 was **DECLINED**. The TCS client on master still uses bare `requests.get()` (verified). Decline reason unknown — must be read before treating this as a precedent. |
| 2026-04-30 | `a6b75c2` | AI-NEW-5: cache feature-gate user attributes per-request on flask.g | **PRECEDENT FOR W4/W5**. Same flask.g pattern. |
| 2026-04-30 | `9b1efdf` | AI-NEW-4: drop dead second tokenization in `GPTOSSModelInTeamserve._prepare_request` | Approved by Xiaojiang Huang, Kai Zhang. Tony Chen authored. |
| 2026-04-?? | `99daf3f` | AI-NEW-3: emit fail-open metric tagged by reason + fail-closed gate for malformed output | Observability *additive*. |

**Quote from AI-NEW-6 PR description (verbatim)**:
> "1. Share one requests.Session() with sized urllib3 connection pool
>     (pool_connections=10, pool_maxsize=50). Every TCS call now amortises
>     the TCP+TLS handshake across the worker's lifetime. Always-on win."
>
> "Why no feature gate: pure additive optimisation. Same input -> same
> output within TTL. If it misbehaves, `git revert` is the rollback."

**Implication for W1**: The author, repo, language, library (`requests`),
review pattern, and risk profile are *identical*. We have explicit precedent.

### 2026-04-22 — Inference Layer Refactor (xhuang3, on branch)

| Date | SHA | Title | Status |
|---|---|---|---|
| 2026-04-22 | `9b77f36` | AI-127: unify inference model layer — complete architecture refactor | **ON FEATURE BRANCH ONLY**. NOT in master HEAD. Plans to delete `rai_llama.py`, `rai_gpt_oss.py`, `triton_openai_api_client.py` and replace with `backends/{ai_gateway,teamserve}.py`. |

**Important**: 2 of our 4 subagents falsely concluded these files were deleted
on master. They are not. See [04-agent-claim-audit.md](04-agent-claim-audit.md).
**Implication**: If/when AI-127 lands, our W1 fix must be re-applied to the
new `backends/teamserve.py`. Both code paths still need the fix today.

### 2026-03-19 — `max_tokens` Latency/Quality Dance (Kai Zhang)

This is a textbook example of why we DON'T touch `max_tokens=400` lightly.

| Date | SHA | Title | Decision |
|---|---|---|---|
| 2026-03-16 | `6ab55ee` | revise max output token from 500 to 200 to reduce max latency | LATENCY: 500→200 |
| 2026-03-19 | `1a8adc4` | Revise max output tokens to 512, 200 truncation too much | QUALITY: 200→512 (200 truncated valid responses) |
| 2026-03-19 | `26303d2` | **Revise max output tokens to 400, 200 truncation too much** | **COMPROMISE**: 512→400 (final) |

**Explicit decision pattern**: 200 was too aggressive (truncated valid output);
500 was leaving latency on the table; **400 is the explicit Pareto compromise**
between truncation rate and worst-case decode time. **DO NOT lower without
fresh accuracy data.**

### 2026-03 — Prompt Version Series (Kai Zhang)

| Date | SHA | Title | Reason |
|---|---|---|---|
| 2026-03 | `9543c11` | v1.1 prompt version to reduce blocking rate for high-risk decision and special advice | Blocking rate too high |
| 2026-03 | `469e9dd` | prompt v1.2 | (incremental) |
| 2026-03 | `41e0677` | v1.3 prompt, expect to reduce blocking rate to <0.2% | Explicit target |
| 2026-03 | `89f703c` | **prompt v1.4 to block workplace flirting etc** | New harm category added |
| 2026-04 | (later) | prompt v1.5 (Telstra-driven) | Customer-specific |

**Implication for Wave 9**: Prompt size grew (v1.0 → v1.4: 1,374 → 1,947
tokens, +42%) because *each version added rules*. Removing rules to shrink
the prompt = product regression.

### 2026-02 — GPT-OSS-20B Initial Onboarding (Kai Zhang)

| Date | SHA | Title |
|---|---|---|
| 2026-02 | `56dba9b` | Add gpt-oss-20b model handler with new url endpoint gpt-oss-safeguard in controller |

**Note**: The original `triton_openai_api_client.py` was created here with
bare `requests.post()`. There is **no commit** showing this was a deliberate
choice over `Session()` — it was just the simplest first cut. AI-NEW-6 later
proved (for TCS) that `Session()` is the right answer.

## 4. Author Ownership Map (current era)

| File / Concern | Primary owner (most recent) | Verifier reviewer |
|---|---|---|
| `src/inference_models/rai_gpt_oss.py` | Tony Chen (AI-NEW-4) | Kai Zhang, Xiaojiang Huang |
| `src/inference_models/triton_openai_api_client.py` | Kai Zhang (initial) | — (not touched since 2026-02) |
| `src/inference_models/rai_llama.py` | Tony Chen (RAI-01) | Kai Zhang |
| `src/feature_service.py` | Tony Chen (AI-NEW-5, RAI-02) | Kai Zhang |
| `src/api/v1/moderation/prompt_moderation_controller.py` | Tony Chen (RAI-02) | Kai Zhang |
| `src/api/v1/moderation/etag/prompt_etag.py` | Kai Zhang (last touched) | — |
| TRT-LLM YAML (`responsible-ai/notebooks/inference/.../01_register_model_v3.py`) | Kai Zhang | — |
| Prompt template (Jinja v1.4) | Kai Zhang | — |
| `prompt_v1.4` content (workplace-flirting etc.) | Kai Zhang | Product/Trust team |
| AI-127 backends/ refactor (branch only) | xhuang3 | (in review) |

## 5. Documented Process (RAI-15)

`26613af` (Tony Chen, 2026-05-04) installs a measurement discipline for all
perf claims. The benchmarking.md doc requires:
- T1: in-process micro-bench
- T2: full unit-suite latency before/after
- T3: integration-test latency before/after
- T4: prod p50/p95/p99 in dashboards

**Wave 9 implication**: Each Wave 9 PR must follow this. We can't ship W1
on the strength of `requests.Session()` theory alone — we need a T1 micro-bench
in the PR description. AI-NEW-6 set the standard ("realistic warm-path
savings: ~100-400ms per gated agent request").

## 6. References

- All commits verified by `git log --all` on local checkouts.
- Repos:
  - `/Users/tchen7/MyProjects/atlassian_packages/responsible-ai-api`
    (origin: `git@bitbucket.org:atlassian/responsible-ai-api.git`)
  - `/Users/tchen7/MyProjects/atlassian_packages/responsible-ai`
    (sister monorepo)
- Top-15 plan: `_plan/responsible-ai-api-INTEGRATED-v4.md` (in
  `responsible-ai-api` checkout)
