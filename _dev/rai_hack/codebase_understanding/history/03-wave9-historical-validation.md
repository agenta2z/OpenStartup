# Wave 9 Historical Validation — "Was this an intentional production design?"

> **Primary deliverable** of this investigation. Answers: for each Wave 9 quick
> win, is the current behavior the result of an explicit production decision,
> or an oversight that we are safe to fix?
>
> **Method**: Direct git log + diff inspection on `master` HEAD `37fec91`
> (2026-05-05) of `responsible-ai-api`, plus the `responsible-ai` deployment
> notebook at HEAD.
>
> **Verdict legend**:
> - ✅ **SAFE — STRONG PRECEDENT**: A nearly identical change was made in this
>   repo, was approved by the relevant reviewers, and was not reverted.
> - ✅ **SAFE — NO COUNTER-EVIDENCE**: No commit, comment, or PR description
>   indicates the current behavior is intentional. Pattern fits established
>   conventions.
> - ⚠️ **NEEDS-MORE-INFO**: The history is silent on intent. Get explicit
>   sign-off from the author of record before changing.
> - 🛑 **RISKY — INTENTIONAL**: There is direct evidence (commit message,
>   PR body, or comment) that the current value was chosen on purpose to
>   trade off X for Y. Changing it is a product/quality regression unless
>   re-justified.
> - ❌ **MOOT**: The code we'd change has been removed (or scheduled for
>   removal) on master. No-op.

---

## W1 — Use `requests.Session()` for the TeamServe HTTP client

### What Wave 9 proposed

In `src/inference_models/triton_openai_api_client.py`, replace:
```python
response = requests.post(self.url, json=payload, ...)
```
with a long-lived `self._session = requests.Session()` (sized urllib3 pool),
amortising TCP+TLS handshake across requests.

### Verified current state (master HEAD `37fec91`, 2026-05-05)

```python
# File: src/inference_models/triton_openai_api_client.py (entire file, 35 lines)
class TritonOpenAIClient:
    def __init__(self, url, asap_signer, audience="teamserve"):
        self.url = url
        self.auth = JWTAuth(asap_signer, audience)
        self.headers = {"Content-Type": "application/json"}
        self.breaker = pybreaker.CircuitBreaker(name="triton_circuit_breaker", fail_max=30)
    def send_chat_completions(self, messages, **kwargs):
        with self.breaker.calling():
            response = requests.post(self.url, json=payload, headers=..., auth=self.auth, timeout=6)
```

The file uses the module-level `requests.post()` (creates a fresh
connection each call). Author of record: Kai Zhang (`56dba9b`,
2026-02-?). No subsequent change touches the HTTP transport.

### Historical search

- Searched all commits touching this file: only **5 commits ever** —
  initial creation (`56dba9b`), then 3 lint fixes (`53aaacc`, `ca33bda`,
  `faadd74`, `bc6bfbe`), and the AI-127 refactor on a feature branch
  (`9b77f36`, NOT merged to master).
- Searched all `*.md` files in repo for "connection pool", "keep-alive",
  "session reuse" rationale: zero hits explaining current behavior.
- Searched for circuit-breaker design notes that might require fresh
  connections: zero hits. `pybreaker` operates at call-count granularity,
  not connection granularity — orthogonal to connection pooling.
- Searched ASAP/JWT auth docs for per-call freshness requirements: JWT
  is passed in headers; reusing a TCP socket with a fresh JWT header is
  the standard pattern.

### 🚨 CORRECTION (2026-05-06 06:33) — The "precedent" was DECLINED

**An earlier draft of this doc claimed AI-NEW-6 (`9c33782`, PR #623) was
the strong precedent for W1. This was WRONG.**

Direct git verification on master proves:

```bash
$ git merge-base --is-ancestor 9c33782 master ; echo $?
NO, NOT on master

$ grep -rn "requests.Session\|_truthy_time_cache" src/ --include='*.py'
(no results — code does not exist on master)

$ git branch -a --contains 9c33782
  AI-NEW-6-tcs-session-and-truthy-cache
  remotes/origin/AI-NEW-6-tcs-session-and-truthy-cache
  (i.e. only on the feature branch)

$ cat src/tenant_context/tenant_context_client.py | head -45
# → Still uses bare requests.get(url, timeout=TIMEOUT, ...) at lines 40 and 70.

$ git log master --oneline -- src/tenant_context/tenant_context_client.py
0de93e9 Merged in CAIM-400-add-tcs-client-and-lookups-for-org-control (pull request #405)
# → Only one merge ever. PR #623 (AI-NEW-6) was DECLINED.
```

Notably, the branch had a follow-up commit `3491efc` ("Fix pyright failures
from PR #623 lint step") — meaning a real review happened and was responded
to. But the PR was still not merged. **No follow-up PR replaced it.** This
means the decline likely had substantive review concerns, not just lint.

### ⚠️ REVISED VERDICT: **NEEDS-MORE-INFO — DECLINE REASON UNKNOWN**

Until the AI-NEW-6 decline reason is understood, we cannot conclude that
the same pattern would be safely accepted for the TeamServe client. The
decline could mean:

1. **Reviewer found a real concern** with the Session pattern in this repo
   (e.g., gevent-monkey-patching interaction with urllib3 pool, fork-safety
   in gunicorn workers, ASAP per-call freshness assumptions, etc.)
2. **Reviewer disagreed with risk/reward** (small Pareto win not worth the
   API-surface change)
3. **Bundling concern** (the PR also added `_truthy_time_cache`; reviewer
   may have wanted them split)
4. **Author deferred** for unrelated reasons (priority shift, branch
   conflict, etc.)

### Action required BEFORE filing W1

1. **Read PR #623 review comments** at
   `https://bitbucket.org/atlassian/responsible-ai-api/pull-requests/623`
   to learn the actual decline reason.
2. If concern was **substantive** (cases 1 or 2 above): W1 is also at risk.
   Address the same concern in W1's design BEFORE filing.
3. If concern was **bundling** (case 3): split — file just the Session
   change, no decorator. Match what the reviewer asked for.
4. If concern was **deferred** (case 4): re-engage the original reviewers
   on W1 with a fresh proposal.

**Until the decline reason is known, W1 verdict is downgraded from
"SAFE — STRONG PRECEDENT" to "NEEDS-MORE-INFO".**

**Action**: File W1 PR. Cite `9c33782` (AI-NEW-6) as the precedent in the
PR description. Apply the same `pool_connections=10, pool_maxsize=50` sizing
unless there's a TeamServe-specific reason to differ. Add 5–10 unit tests
matching AI-NEW-6's coverage shape (Session reuse, sized HTTPAdapter pool,
auth header per call). Include T1 micro-bench per RAI-15 discipline.

**Caveat**: If/when AI-127 (`9b77f36`) lands and refactors this file into
`backends/teamserve.py`, the Session pattern must be re-applied there.
Track this as "AI-127-followup" in the PR description.

---

## W2 — `enable_chunked_prefill: false` (TRT-LLM YAML)

### What Wave 9 proposed

In `responsible-ai/notebooks/inference/inference_oss_safeguard_20b/01_register_model_v3.py`,
flip `enable_chunked_prefill` from `true` to `false` to optimize for batch=1
TTFT.

### Verified current state (responsible-ai HEAD)

The YAML literal in the notebook:
```yaml
enable_attention_dp: false
cuda_graph_config:
  max_batch_size: 1
  enable_padding: true
moe_config:
  backend: CUTLASS
enable_iter_perf_stats: true
enable_chunked_prefill: true
return_perf_metrics: true
kv_cache_config:
  enable_block_reuse: true
max_batch_size: 1
```

The file is a Databricks notebook (`# COMMAND ----------` cell separators)
named `low_latency.yaml`. Owner: Kai Zhang. The companion vLLM notebook
(`01_vllm-gpt-oss-safeguard-20b-it.py`) was added on Apr 29 alongside, but
the v3 register script remains and was last touched 2026-04-30.

### Historical search

- All notebook content was committed as a coherent block by Kai Zhang;
  no per-line "why this value" comments.
- `max_batch_size: 1` and `cuda_graph_config.max_batch_size: 1` *do*
  prove the file targets the low-latency single-request path. So
  `chunked_prefill: true` is suspicious here — community convention is
  to disable it for batch=1.
- BUT the file is named `low_latency.yaml`. The author intentionally
  thought about latency. Either (a) `chunked_prefill: true` was a default
  Kai didn't realize hurts batch=1, or (b) Kai measured it and accepted
  the trade-off. Git history can't distinguish.

### ⚠️ VERDICT: **NEEDS-MORE-INFO**

We have *circumstantial* evidence (the file is named `low_latency.yaml`
and pins `max_batch_size: 1`) that the author intended low latency, which
is consistent with W2. But we do **not** have a measured benchmark or a
PR comment from Kai explaining the choice. Coordinate with Kai Zhang
before changing. Do not file unilaterally.

**Recommended action**: Slack/Jira Kai with:
> "We're proposing `enable_chunked_prefill: false` for the v3 register
> script — community guidance is that chunked prefill hurts TTFT at
> batch=1. Did you benchmark this when the YAML was first set? Mind
> if I run a side-by-side TTFT measurement?"

---

## W3 — Disable `enable_iter_perf_stats` + `return_perf_metrics`

### What Wave 9 proposed

Set both to `false` to save 5–15 ms of per-iter stats collection.

### Verified current state

Both are `true` in the same YAML as W2.

### Historical search

- The `responsible-ai-api` perf wave (RAI-04, RAI-05) is *adding*
  observability (parser fallback metrics, model selection metrics).
  Wave 9 W3 is *removing* observability. Inconsistent direction.
- Whether Kai Zhang's Databricks dashboards consume `iter_perf_stats`
  was not directly verifiable from git (would need to inspect
  Grafana/Databricks dashboard configs).

### 🛑 VERDICT: **RISKY**

There is asymmetric upside vs downside:
- Upside: 5–15 ms (estimated, not measured)
- Downside: silent observability regression. Recovery cost: detect a
  prod incident → realize the metric is missing → re-deploy.

**Recommended action**: Don't ship W3 until we have proof that
`iter_perf_stats` is NOT consumed by any active dashboard / alert. Check
with Kai Zhang first.

---

## W6 — `disable_overlap_scheduler: true`

### What Wave 9 proposed

Add `disable_overlap_scheduler: true` to the YAML (currently absent →
defaults to scheduler enabled).

### Verified current state

The setting is absent from the YAML. TRT-LLM default is overlap-scheduler
enabled.

### Historical search

- Same scope as W2: YAML change, owner Kai Zhang.
- Community evidence (NVIDIA docs) supports disabling for batch=1.
- No prior PR has touched this knob.

### ⚠️ VERDICT: **NEEDS-MORE-INFO**

Bundle with W2 in the same coordination ping with Kai. Both are TRT-LLM
YAML knobs and should be benchmarked together.

---

## W4 — Cache rendered prompt template

### What Wave 9 proposed

Render the Jinja prompt template once per worker process; reuse the
rendered string across requests (the template depends on model version,
which is known at startup, not per-request).

### Verified current state

In the prompt-moderation flow, the Jinja template is re-rendered on
every request.

### ⚠️ "Precedent" claims (NEITHER is on master — verified 2026-05-06 06:35)

- AI-NEW-5 (`a6b75c2`) — flask.g per-request caching pattern. **Not on master.**
- RAI-02 (`63d434a`) — `from_incoming_http_request_cached()` pattern. **Not on master.**

W4 is a one-step generalization of patterns that are *still author-proposed*
in feature branches. They have not been reviewer-approved on master. Citing
them in a W4 PR description would mislead the next reviewer.

### ⚠️ REVISED VERDICT: **NEEDS-MORE-INFO**

The flask.g caching pattern looks idiomatic, AND `functools.lru_cache` for
process-level caching is standard Python — but neither has been formally
landed in this repo. We should:
1. Either wait for AI-NEW-5/RAI-02 to land first (then cite them legitimately),
2. Or file W4 standalone with thorough unit-test evidence and let the
   reviewer judge it on its own merits — without claiming "precedent".

---

## W5 — Conditional ETag SHA-256

### What Wave 9 proposed

In `src/api/v1/moderation/etag/prompt_etag.py`, only compute the SHA-256
ETag when an `If-None-Match` header is present (skip the hash on the
common no-cache-header path).

### Verified current state

The ETag is computed unconditionally on every request (full
`model_dump()` → SHA-256).

### Historical search

- File last touched by Kai Zhang in PRs `e24c5b6` ("refactor: use
  dynamic model/prompt version for ETag check instead of hardcoded
  V2_3_3"). Focus was correctness, not perf.
- No prior PR has discussed when ETag computation should run.
- HTTP RFC 7232 actually allows servers to skip ETag generation when
  client doesn't ask for cache validation; nothing in the API contract
  forces unconditional computation.

### ✅ VERDICT: **SAFE — NO COUNTER-EVIDENCE**

Pure HTTP-spec-compliant micro-optimization. Output is byte-identical
when the client *does* send `If-None-Match`. When the client doesn't,
the ETag header is allowed to be omitted (or computed lazily on demand
by HTTP middleware).

**Action**: File W5 PR. Add 2 tests:
1. `If-None-Match` present → ETag is computed and matched.
2. No `If-None-Match` → response is byte-identical to today minus the
   ETag header (or with empty ETag), and clients that don't read it
   don't break.

Verify Atlassian intermediaries (Stargate, ingress) don't *require* the
ETag header for routing. If they do, downgrade verdict.

---

## Bonus: `max_tokens` (NOT in Wave 9, but agents proposed it)

### Verdict: 🛑 **RISKY — INTENTIONAL**

This is the textbook case. Three commits in March 2026 explicitly
balance latency vs truncation rate (see
[01-decision-timeline.md §3](01-decision-timeline.md) and
[02-perf-decision-archive.md §3](02-perf-decision-archive.md)).
Lowering `max_tokens=400` re-opens a settled trade-off.

**Action**: Do not change without fresh truncation-rate measurement
on the current prompt v1.4 + harm taxonomy.

---

## Summary

| Wave 9 ID | Verdict | Effort to ship | Coordination needed |
|---|---|---|---|
| W1 (Session) | ⚠️ **NEEDS-MORE-INFO** (downgraded — see correction above; PR #623 was declined) | (TBD pending decline-reason) | **READ PR #623 REVIEW FIRST** |
| W2 (chunked_prefill) | ⚠️ NEEDS-MORE-INFO | YAML + Databricks redeploy | Ping Kai Zhang |
| W3 (perf stats) | 🛑 RISKY | YAML + Databricks redeploy | Confirm dashboards first |
| W4 (cache prompt) | ⚠️ **NEEDS-MORE-INFO** (downgraded — flask.g precedents AI-NEW-5/RAI-02 are NOT on master) | 1 PR, ~10 LoC + 4 tests | Verify reviewers will accept the flask.g pattern (still in-flight elsewhere) |
| W5 (conditional ETag) | ✅ SAFE — NO COUNTER-EVIDENCE (independent of declined precedents) | 1 PR, ~5 LoC + 2 tests | Spot-check Stargate |
| W6 (overlap scheduler) | ⚠️ NEEDS-MORE-INFO | YAML | Bundle with W2 ping |

**Recommended sequencing (REVISED 2026-05-06 06:33 after PR #623 decline discovery)**:
1. **BLOCKER**: read PR #623 (AI-NEW-6) review comments to learn the decline reason. This gates W1 entirely.
2. **Today (still safe)**: W4, W5 — both SAFE; ~15 LoC + ~6 tests across 2 PRs.
3. **This week (after Kai sync)**: W2 + W6 bundle — depends on benchmark + sign-off.
4. **Conditional**: W3 — only after dashboard audit confirms zero consumers.
5. **Conditional**: W1 — after PR #623 review is understood, address concerns, then file.
