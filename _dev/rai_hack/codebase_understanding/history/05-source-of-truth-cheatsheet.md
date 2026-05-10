# Source-of-Truth Cheatsheet (Machine-Followable)

> **Purpose**: A 30-second lookup for any agent or human modifying RAI code.
> Format is intentionally tabular and stable so it is greppable by future
> automation.
>
> **Last verified**: 2026-05-06 against `responsible-ai-api` master HEAD
> `37fec91` and `responsible-ai` HEAD.
>
> **Schema**: `<file or knob> | <current value / state> | <author of record> | <last touch SHA> | <verdict for change> | <coordination needed>`

## File → Owner → Verdict Lookup Table

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ KEY                                       │ CURRENT       │ OWNER     │ LAST SHA  │ DATE        │ VERDICT      │ PING     │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ src/inference_models/triton_openai_api_client.py:28 (requests.post) │ no Session │ Kai Zhang │ 56dba9b   │ 2026-02-?? │ NEEDS-INFO    │ READ PR#623 first │
│ src/inference_models/rai_gpt_oss.py:88   (reasoning_effort)         │ "low"      │ Kai Zhang │ (initial) │ 2026-02-?? │ RISKY-product│ Kai+Trust│
│ src/inference_models/rai_gpt_oss.py:90   (max_tokens)               │ 400        │ Kai Zhang │ 26303d2   │ 2026-03-19 │ RISKY-quality│ Kai      │
│ src/api/v1/moderation/etag/prompt_etag.py (always-compute SHA-256)  │ always-on  │ Kai Zhang │ e24c5b6   │ 2026-?     │ SAFE-no-evid │ Stargate │
│ src/api/v1/moderation/prompt_moderation_controller.py (template render) │ per-req│ multi     │ multi     │ 2026-05    │ SAFE-PRECEDENT│ none     │
│ src/feature_service.py (per-req gate cache)                          │ cached    │ Tony Chen │ a6b75c2   │ 2026-04-30 │ DONE         │ -        │
│ src/api/v1/moderation/utils/moderation_request_context.py (per-req cache)│ cached│ Tony Chen │ 63d434a   │ 2026-05-04 │ DONE         │ -        │
│ src/inference_models/rai_gpt_oss.py (double tokenization)           │ removed   │ Tony Chen │ 9b1efdf   │ 2026-04-30 │ DONE         │ -        │
│ src/inference_models/rai_llama.py (double tokenization)             │ removed   │ Tony Chen │ 79a0caf   │ 2026-05-04 │ DONE         │ -        │
│ src/tenant_context/tenant_context_client.py (HTTP transport)         │ no Session│ (initial) │ 0de93e9   │ (initial)  │ DECLINED-#623 │ READ PR#623 first │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ responsible-ai/notebooks/.../01_register_model_v3.py                                                                       │
│   yaml_content.enable_chunked_prefill                              │ true       │ Kai Zhang │ (block)   │ 2026-04-30 │ NEEDS-INFO   │ Kai      │
│   yaml_content.enable_iter_perf_stats                              │ true       │ Kai Zhang │ (block)   │ 2026-04-30 │ RISKY-observ │ Kai+SRE  │
│   yaml_content.return_perf_metrics                                  │ true       │ Kai Zhang │ (block)   │ 2026-04-30 │ RISKY-observ │ Kai+SRE  │
│   yaml_content.cuda_graph_config.enable_padding                     │ true       │ Kai Zhang │ (block)   │ 2026-04-30 │ NEEDS-INFO   │ Kai      │
│   yaml_content.kv_cache_config.enable_block_reuse                   │ true       │ Kai Zhang │ (block)   │ 2026-04-30 │ KEEP — works │ -        │
│   yaml_content.disable_overlap_scheduler                            │ absent     │ Kai Zhang │ (block)   │ 2026-04-30 │ NEEDS-INFO   │ Kai      │
│   yaml_content.max_batch_size                                       │ 1          │ Kai Zhang │ (block)   │ 2026-04-30 │ KEEP — proves intent│ - │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Verdict legend (machine-parseable):
- `SAFE-PRECEDENT` — exact pattern shipped before in this repo, by the same person, not reverted
- `SAFE-no-evid` — no commit/comment indicates current behavior is intentional
- `RISKY-product` — current value is a deliberate product/quality choice (e.g., `reasoning_effort="low"` was chosen for accuracy after Wave 5)
- `RISKY-quality` — current value is a documented Pareto compromise (e.g., max_tokens=400)
- `RISKY-observ` — change would silently break observability
- `NEEDS-INFO` — git is silent; ping owner for benchmark/intent
- `KEEP` — current value is positively known to be correct (shouldn't be changed)
- `DONE` — already optimised; no further work needed
- `MOOT` — would touch deleted code

## Reviewer Routing (machine-followable)

```yaml
# review-routing.yml — apply to any PR for the listed file
src/inference_models/triton_openai_api_client.py:
  primary: tony.chen@atlassian.com
  required_reviewer: kai.zhang@atlassian.com
  precedent_pr: 9c33782  # AI-NEW-6
  reason: "Same Session pattern as TCS client; reuse review template."

src/inference_models/rai_gpt_oss.py:
  primary: kai.zhang@atlassian.com
  required_reviewer: xhuang3@atlassian.com
  precedent_pr: 9b1efdf  # AI-NEW-4
  reason: "Owns model + tokenization decisions; max_tokens history."

src/inference_models/rai_llama.py:
  primary: tony.chen@atlassian.com
  required_reviewer: kai.zhang@atlassian.com
  precedent_pr: 79a0caf  # RAI-01
  reason: "Tokenization optimisations precedent."

src/api/v1/moderation/etag/prompt_etag.py:
  primary: kai.zhang@atlassian.com
  required_reviewer: tony.chen@atlassian.com
  precedent_pr: e24c5b6
  reason: "Prior owner; sanity check vs Stargate routing."

src/feature_service.py:
  primary: tony.chen@atlassian.com
  required_reviewer: kai.zhang@atlassian.com
  precedent_pr: a6b75c2  # AI-NEW-5

src/api/v1/moderation/prompt_moderation_controller.py:
  primary: tony.chen@atlassian.com
  required_reviewer: kai.zhang@atlassian.com
  precedent_pr: 63d434a  # RAI-02

responsible-ai/notebooks/inference/inference_oss_safeguard_20b/01_register_model_v3.py:
  primary: kai.zhang@atlassian.com
  required_reviewer: (whoever owns Databricks dashboards)
  precedent_pr: (none — file is solo-Kai)
  reason: "Coordinated change required; impacts deployed model + dashboards."
```

## Decision-Making Flowchart for "Should I change this?"

```
┌─────────────────────────────────────────────────────────────────┐
│ START: I want to change <key>                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Look up <key> in the table above.                               │
│ Verdict = ?                                                     │
└─────────────────────────────────────────────────────────────────┘
       │            │           │           │           │
       ▼            ▼           ▼           ▼           ▼
   SAFE-*       NEEDS-INFO  RISKY-*    KEEP        DONE
       │            │           │           │           │
       ▼            ▼           ▼           ▼           ▼
   T1 micro-    Ping owner  Re-justify  STOP — do   STOP — already
   bench →      with        with fresh  not change  optimised
   file PR      proposal +  data, then              (consider
   citing       benchmark   coordinate              follow-on
   precedent    plan, then  with owner              instead)
   PR.          discuss.    BEFORE PR.
       │
       ▼
   Run unit + integration suite locally.
       │
       ▼
   Open PR. Cite precedent SHA in description.
   Use the RAI-15 4-tier verification template.
       │
       ▼
   END
```

## Precedent SHA Reference (one-line each, copy-paste)

```
9c33782  AI-NEW-6  TCS Session reuse + truthy-only TTL cache (P1-9) — ⚠️ PR #623 DECLINED, NOT ON MASTER
a6b75c2  AI-NEW-5  cache feature-gate user attributes per-request on flask.g
9b1efdf  AI-NEW-4  drop dead second tokenization in GPTOSSModelInTeamserve._prepare_request
99daf3f  AI-NEW-3  emit fail-open metric tagged by reason + fail-closed gate for malformed output
79a0caf  RAI-01    Eliminate double tokenization in LLaMA inference path (Perf-Improving)
63d434a  RAI-02    Cache ModerationRequestContext per request (Perf-Improving)
407765f  RAI-03    gRPC gevent.Timeout + per-endpoint breaker metric (Neutral)
406d286  RAI-04    Parser fallback observability metrics (Observability)
7eec261  RAI-05    Model selection metric (Observability)
26613af  RAI-15    Benchmarking dev skill reference (Process) — install measurement discipline
26303d2  Kai-3-19  Revise max output tokens to 400 — quality/latency Pareto compromise
1a8adc4  Kai-3-19  Revise max output tokens to 512 — bumped from 200 (truncation too much)
6ab55ee  Kai-3-16  Revise max output token from 500 to 200 — to reduce max latency
89f703c  Kai-2026  prompt v1.4 to block workplace flirting etc — adds harm category
56dba9b  Kai-init  Add gpt-oss-20b model handler (initial commit)
```

## Quick Re-verify Block (run before any PR)

```bash
# Re-validate verdicts before filing any Wave 9 PR
cd ~/MyProjects/atlassian_packages/responsible-ai-api
git fetch && git pull --ff-only origin master  # ensure HEAD is fresh
git branch --show-current                       # → master

# Confirm precedent SHAs are still on master
for sha in 9c33782 a6b75c2 9b1efdf 79a0caf 63d434a 26613af; do
  on_master=$(git branch --contains $sha 2>/dev/null | grep -c master)
  echo "$sha on_master=$on_master"
done

# Confirm files we want to modify still exist as the table claims
for f in src/inference_models/triton_openai_api_client.py \
         src/inference_models/rai_gpt_oss.py \
         src/api/v1/moderation/etag/prompt_etag.py; do
  test -f "$f" && echo "OK $f" || echo "MISSING $f"
done

# Spot-check the max_tokens line is still 400
grep -n "max_tokens" src/inference_models/rai_gpt_oss.py | head -3
```

If any line above prints `MISSING` or `on_master=0` for a precedent SHA,
**STOP and re-run the historical investigation** — the assumptions in this
doc may have shifted.
