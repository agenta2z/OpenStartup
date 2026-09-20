# Tenant-Isolation-Safe Performance Opportunities (Wave 9.5)

> **Trigger**: PR #623 (AI-NEW-6, "TCS Session reuse + truthy-only TTL cache") was DECLINED with the reason:
> > *"TTL cache was removed in PR #416 due to 10% cache hit rate and not allowed to share cached prompt between tenant in production env."*
>
> **Context**: This rule INVALIDATES any tenant-scoped caching, even per-worker. But it does NOT invalidate transport-layer pooling or process-level invariants.
>
> **This document** identifies the surviving opportunities — verified directly against master HEAD `37fec91`.
> **Date**: 2026-05-06 06:41
> **Verification method**: Each finding is read directly from the actual file content; no agent-only claims accepted.

---

## 0. The Constraint (precise statement)

A piece of state can be cached/shared/pooled only if **all** of the following hold:

| Constraint | Rationale | Examples allowed | Examples forbidden |
|---|---|---|---|
| **Tenant-invariant** | Tenant data sharing is forbidden by product policy | TCP sockets, gRPC channels, JWT (service-scoped), Jinja templates of static prompts | User input, model response for a tenant's specific input, ASAP user-context |
| **Demonstrably valuable** | PR #416 was removed because hit rate was 10% — not zero, just not enough to justify cost | Things hit on >50% of requests OR things that are pure-overhead (TLS handshake, DNS lookup, regex compile) | Things hit on <30% of requests where cache stale-window matters |
| **Reversible** | We must be able to `git revert` cleanly | Module-level `lru_cache`, single-file change | Cross-cutting refactors, schema changes |

If any one of the three fails, the optimization is rejected.

---

## 1. Agent Claim Verification Table

Direct ground-truth check on each subagent's report (no agent claim accepted without independent file read):

| Agent claim | Direct verification | Truth | Verdict |
|---|---|---|---|
| Q1: "the codebase is not accessible" | `ls src/inference_models/` shows files exist | **Q1 agent failed** — gave up incorrectly | Discard agent; do work directly |
| Q2: "INPUT_TEMPLATE.render() per request" at `rai_gpt_oss.py:188` | `grep -n` confirmed line 188 has `input = INPUT_TEMPLATE.render(input=input)` | TRUE — but `INPUT_TEMPLATE = Template("{{input}}")` — the template is a no-op pass-through; rendering cost is microseconds | Marginal; not low-hanging |
| Q2: "format_template called per request via render(content=content)" at `model.py:142` | confirmed `return self.jinja_template.render(content=content, **kwargs)` | TRUE — but the *content* is the user's input; per-request rendering is intrinsic | Cannot cache the rendered output (depends on content); must render every time |
| Q2: "model_template_and_prompt_tokens already cached at class init" | `rai_gpt_oss.py:223-224` shows `if self.model_template_and_prompt_tokens is None: empty_model_prompt = ...format_template(content="")` | TRUE — the static-prompt portion IS already cached. The `content=""` rendering only happens once. | ✅ **Already optimized** — no work needed |
| Q3: "ETag SHA-256 always-on" | Read full `prompt_etag.py` | **MIXED** — `check_etag()` already returns early at line 107 if `If-None-Match` is None. So the SHA-256 is ONLY computed when cache validation is requested. | ✅ **Already optimized** for the no-cache-header case |
| Q3: "Redundant Pydantic validation in check_etag" | Read lines 114-115 | TRUE — `request.get_json()` + `ModeratePromptRequest.model_validate(...)` happens twice (etag check + main handler) | ⚠️ Real but small — and only fires on If-None-Match hits |
| Q3: "from_incoming_http_request called 7+ times" | `grep -rn` confirmed: 9 call sites across micros_logging, 4 controllers, feature_service ×2, demo_blueprint, definition | TRUE — **but RAI-02 is not on master**; the dup is real and unfixed | ✅ Real opportunity — file as new PR |
| Q4: "gevent.monkey.patch_all() in WRONG order in src/gunicorn.conf.py" | Read full file | **FALSE** — file content shows: `import gevent.monkey` → `gevent.monkey.patch_all()` → `import grpc.experimental.gevent` → `grpc_gevent.init_gevent()`. **This is the CORRECT order.** | ❌ Agent wrong — current code is fine |
| Q4: "gunicorn worker_class missing" | Read full file | TRUE — no `worker_class = "gevent"` line. With `multiprocessing.cpu_count() * 2 + 1` workers but no class set, defaults to sync (which makes `gevent.monkey.patch_all()` ineffective for serving). | 🚨 Real high-impact opportunity — verify in prod |
| Q4: "gRPC channel not reused" | Read full `triton_grpc_client.py` | **FALSE** — `GrpcEndpoint.__init__` creates `self.triton_client = InferenceServerClient(url=url, ...)` ONCE. Reused via `self.triton_client.infer(...)` per call. | ✅ Already optimized |
| Q4: "boto3.Session created per call in sagemaker_base.py" | Read lines 25-60 | **MIXED** — `_create_runtime_client()` is called once during `__init__` (line 22-24: `self.runtime = ... or self._create_runtime_client()`), so the Session/client is reused. The `boto3.client("sts")` and `boto3.Session().client(...)` only fire on the credential-failure paths (rare). | ✅ Already optimized for happy path |
| Q4: "JWT not cached" | `triton_openai_api_client.py:18` shows `JWTAuth(asap_signer, audience)` is called in `__init__` (once), but `requests.post(..., auth=self.auth, ...)` triggers `JWTAuth.__call__` which generates a new JWT per request | TRUE — JWT signing happens per request | ⚠️ Worth measuring; ASAP signing is typically <1ms but might matter |
| Q4: "Flask response compression missing" | Need to check; not yet read | UNKNOWN | Defer |
| Q4: "DNS+TLS savings via Session" | This IS the W1 case from Wave 9 — `triton_openai_api_client.py:28` does `requests.post()` with no Session | TRUE — and now we know PR #623's decline was about TTL cache, NOT the Session part | 🚨 W1 may still be safe — needs sub-PR (Session only) |

---

## 2. Verified Surviving Opportunities (master HEAD `37fec91`)

These have been read directly from source; tenant-safety analyzed; verdict given.

### 🥇 OPP-1 — Add `worker_class = "gevent"` to gunicorn.conf.py
- **Severity**: 🚨 HIGH IMPACT (likely the biggest single win in this list)
- **File**: `src/gunicorn.conf.py` (entire file is 31 lines)
- **Current state** (verbatim):
  ```python
  try:
      import gevent.monkey
      gevent.monkey.patch_all()
      import grpc.experimental.gevent as grpc_gevent
      grpc_gevent.init_gevent()
  except ImportError:
      pass
  
  import multiprocessing
  import os
  
  if os.environ.get("NEBULAE") == "true":
      workers = 1
  else:
      workers = multiprocessing.cpu_count() * 2 + 1
  
  logger_class = "src.gunicorn_logger.CustomGunicornLogger"
  ```
- **The bug**: `gevent.monkey.patch_all()` is called, but **no `worker_class = "gevent"`** is set. Default gunicorn worker is `sync`. With `sync` workers and `monkey.patch_all()`, the gevent loop never runs in worker processes — the monkey patches apply to nothing useful. Each worker handles requests serially.
- **Proposed fix** (1 line addition):
  ```python
  worker_class = "gevent"
  worker_connections = 1000
  ```
- **Tenant safety**: ✅ Pure process-config change. No data shared between requests.
- **Estimated win**: This is **catastrophic to under-claim**. If true:
  - Concurrency goes from 1-per-worker to ~1000-per-worker
  - p50 may not change much (latency-bound), but p99 under load drops by 10-100×
  - Note: if there's an external load balancer assuming sync semantics, may shift queueing behaviour
- **Verification needed before filing**:
  1. Check `nebulae.yml`, `Dockerfile`, `bitbucket-pipelines.yml` for any explicit `--worker-class` flag overriding gunicorn.conf.
  2. Run `grep -rn "worker_class\|--worker-class" .` to confirm no override.
  3. **If a CLI override exists, this is moot** (production is correctly configured; only local dev sees sync).
- **Confidence**: HIGH that the file is incomplete; MEDIUM that prod isn't already overriding via CLI.
- **Action**: Verify CLI override → if absent, file 1-line PR; if present, update gunicorn.conf to match for consistency.

---

### 🥈 OPP-2 — `requests.Session()` for `triton_openai_api_client.py` (W1, RE-EVALUATED)
- **File**: `src/inference_models/triton_openai_api_client.py:28`
- **Current state**: `response = requests.post(self.url, json=payload, ..., auth=self.auth, timeout=6)`
- **The opportunity**: TCP+TLS handshake savings on cross-region calls (~30-80ms warm, >100ms cold).
- **Tenant safety analysis** (the critical question):
  - `requests.Session()` shares: TCP sockets, urllib3 connection pool, DNS cache, TLS session tickets.
  - `requests.Session()` does NOT share: request bodies, response bodies, headers (`auth=self.auth` is per-call), or any application data.
  - **Therefore: Session-only ≠ what PR #623 was declined for.**
- **Why PR #623 was declined**: The bundled `_truthy_time_cache` decorator was caching application response data. The Session pattern was bundled but is not what the rule forbids.
- **Recommended approach**: Re-file as a standalone PR with ONLY the Session change:
  ```python
  def __init__(self, ...):
      self._session = requests.Session()
      adapter = HTTPAdapter(pool_connections=10, pool_maxsize=50)
      self._session.mount("https://", adapter)
      ...
  
  def send_chat_completions(self, ...):
      with self.breaker.calling():
          response = self._session.post(self.url, ...)  # was: requests.post
  ```
- **Tenant safety**: ✅ Transport-layer only. Confirmed no application data shared.
- **Confidence**: MEDIUM-HIGH that this passes review IF presented separately from any caching. Reviewers explicitly objected to the cache, not the Session.
- **Action**: Confirm with PR #623 reviewers (Xiaojiang Huang, Kai Zhang) that "Session-only, no cache" is acceptable. Then file.

---

### 🥉 OPP-3 — Cache `ModerationRequestContext.from_incoming_http_request()` per-request on `flask.g`
- **File**: 9 call sites across `src/`
- **Verified call site count**:
  ```
  src/micros_logging.py:32
  src/api/v1/moderation/output_moderation_controller.py:38
  src/api/v1/moderation/agent_moderation_controller.py:263
  src/api/v1/moderation/prompt_moderation_controller.py:270
  src/api/v1/moderation/image_moderation_controller.py:192
  src/feature_service.py:160
  src/feature_service.py:240
  ```
  → 7 active call sites per request lifecycle, parsing the same headers each time.
- **Tenant safety analysis**:
  - The cache is **per-request** (Flask `g` object dies with the request).
  - The cache key is the request itself (no cross-request sharing).
  - **This does NOT match the PR #623 decline pattern** — that was about *cross-tenant* sharing within a worker. Per-request `flask.g` caching is fundamentally different.
- **Pre-existing attempts on feature branches** (NOT yet on master):
  - AI-NEW-5 (`a6b75c2`): cached `FeatureGateUserAttributes` on flask.g
  - RAI-02 (`63d434a`): added `from_incoming_http_request_cached()`
  - **Both languish unmerged** — could be revived with explicit "this is per-request, NOT cross-tenant" framing in the PR description.
- **Tenant safety**: ✅ Per-request caching = same isolation guarantees as no caching.
- **Confidence**: MEDIUM — depends on whether the original AI-NEW-5/RAI-02 PRs were declined OR just sitting in review. Need to check.
- **Action**: Find out PR status of AI-NEW-5 / RAI-02 first; if declined for cache reasons, re-frame; if just stuck, push for review.

---

### OPP-4 — Drop double tokenization for LLaMA (analog of AI-NEW-4 for GPT-OSS)
- **Pattern**: AI-NEW-4 (`9c16bf7`, ON MASTER) eliminated dead client-side tokenization for GPT-OSS. The same pattern for LLaMA was attempted as RAI-01 on a feature branch but **NOT merged**.
- **File**: `src/inference_models/rai_llama.py`
- **Verification needed**:
  1. Read the LLaMA prepare-request code
  2. Confirm whether server-side tokenization makes the client-side tokenization dead
  3. If yes — re-file as a minimal PR mirroring AI-NEW-4
- **Tenant safety**: ✅ Eliminating computation is always tenant-safe.
- **Confidence**: MEDIUM-HIGH that the opportunity exists; need to read code to confirm.
- **Action**: Verify by reading `rai_llama.py:_prepare_request`, then file standalone PR.

---

### OPP-5 — JWT signing per call (verify before filing)
- **File**: `src/inference_models/triton_openai_api_client.py:18` (`self.auth = JWTAuth(asap_signer, audience)`)
- **Current behavior**: `JWTAuth.__call__` signs a fresh JWT for each `requests.post(...)`.
- **Tenant safety analysis**: ASAP service-tokens are signed by the *service identity*, not by user. They are **not tenant-scoped** — the same JWT is valid for any incoming user request to TeamServe. ✅ Caching the JWT for ~30s does not leak data between tenants.
- **BUT** — the rule from PR #416/623 ("not allowed to share cached prompt between tenant") is about the *response payload*, not the *outbound auth*. JWT caching is in a different layer.
- **Win estimate**: <1ms per request (ASAP signing is fast). Likely too small to justify.
- **Confidence**: LOW that this is worth filing (small win, slightly different concern from rule, but conservatively skip).
- **Verdict**: ❌ **SKIP** — too small to justify the risk of misreading the rule.

---

### OPP-6 — Tenant Context Service (`tenant_context_client.py`) — Session-only
- **File**: `src/tenant_context/tenant_context_client.py:40, 70`
- **Current**: bare `requests.get(url, timeout=TIMEOUT, ...)`
- **Same exact analysis as OPP-2** but for a different client.
- **Tenant safety**: ✅ Transport-layer.
- **Win estimate**: Similar to OPP-2 — ~30-80ms cross-region per call.
- **Note**: PR #623 already proposed this for THIS file with the cache; declined for the cache. Session-only sub-PR has not been tried.
- **Confidence**: MEDIUM-HIGH (same as OPP-2).
- **Action**: Bundle with OPP-2 in coordination ping with reviewers.

---

## 3. Rejected Candidates

### ❌ Q2 — Cache rendered prompt template
The "rendered prompt" is `template + content` where `content` is the user input. **Per-request, not cacheable.** Q2 agent confused the cached static-prefix (already done) with the per-call rendered output (intrinsic).

### ❌ Q3 — Always-on ETag SHA-256
Already conditionally guarded at `prompt_etag.py:107` (returns early if no `If-None-Match` header). Q3 agent missed this guard.

### ❌ Q4 — gevent monkey-patch ordering
`src/gunicorn.conf.py` has the order **correct** (`patch_all()` before `grpc_gevent`). Q4 agent inverted the actual file content.

### ❌ Q4 — gRPC channel not reused
`GrpcEndpoint.__init__` creates `self.triton_client` once and reuses it. Q4 agent didn't read the file.

### ❌ Q4 — boto3 session per call
`SagemakerBase.__init__` calls `_create_runtime_client()` once and stores `self.runtime`. Per-call instantiation only happens on credential-failure paths.

### ❌ FP8 KV cache, speculative decoding, prompt distillation
Out of scope (model/serving infrastructure, not request-path).

---

## 4. Summary Table — Verified Opportunities

| ID | Opportunity | File | Win | Tenant-safe? | On-master prior PR? | Recommended? |
|---|---|---|---|---|---|---|
| **OPP-1** | gunicorn `worker_class = "gevent"` | `src/gunicorn.conf.py` | **HIGH** (10-100× concurrency under load) | ✅ Process config | None | 🚨 **YES — verify CLI override first** |
| **OPP-2** | `requests.Session()` for TritonOpenAIClient | `src/inference_models/triton_openai_api_client.py:28` | 30-80ms/call cross-region | ✅ Transport layer | PR #623 (declined for unrelated cache) | ✅ **YES — file as Session-ONLY** |
| **OPP-3** | flask.g cache for ModerationRequestContext | 7 call sites across `src/` | ~1-3ms/req | ✅ Per-request | AI-NEW-5/RAI-02 (status unknown) | ⚠️ **Check PR status first** |
| **OPP-4** | Drop double tokenization for LLaMA | `src/inference_models/rai_llama.py` | TBD (mirror of AI-NEW-4) | ✅ Computation removal | RAI-01 (not on master) | ✅ **YES — verify pattern, then file** |
| **OPP-5** | JWT caching | `triton_openai_api_client.py:18` | <1ms | ✅ Service-scoped | None | ❌ **NO — too small** |
| **OPP-6** | `requests.Session()` for TCS client | `src/tenant_context/tenant_context_client.py:40,70` | 30-80ms/call cross-region | ✅ Transport layer | Bundled in PR #623 (declined for cache) | ✅ **YES — bundle with OPP-2** |

---

## 5. Recommended Sequencing

### Phase 1 (immediate, lowest risk):
1. **OPP-1**: Verify CLI doesn't override worker_class. If not, file 2-line gunicorn.conf PR. **Highest payoff.**

### Phase 2 (after coordination with PR #623 reviewers):
2. **OPP-2 + OPP-6**: Bundle "Session-only for both clients" in one PR with explicit framing:
   > "This is the Session-only sub-change extracted from declined PR #623. Per discussion, the decline was due to the TTL cache (which violated the cross-tenant sharing rule). This PR contains NO caching — only TCP/TLS pool reuse via `requests.Session()`. Verified no application data is shared."

3. **OPP-3**: Check status of AI-NEW-5 / RAI-02. If declined for cache reasons, re-frame as "per-request only, dies with Flask request, no cross-request sharing"; if just stuck, push for review.

### Phase 3 (deeper investigation needed):
4. **OPP-4**: Read `rai_llama.py:_prepare_request` to confirm dead computation; file minimal PR mirroring AI-NEW-4.

---

## 6. Lessons Reinforced (from prior failure mode)

This investigation independently verified each agent's claim against the actual file content **before** writing any conclusion. Two of four agents had at least one significant error:
- Q1 declared the codebase inaccessible (wrong)
- Q4 declared gevent monkey-patching wrong (correct order in file)
- Q4 declared gRPC channel not reused (it is)
- Q4 declared boto3 session per call (it isn't on the happy path)

The new SOP from `04-agent-claim-audit.md` worked: every claim was checked with `grep`/`cat` before being escalated.

## 7. Re-verify block

```bash
cd ~/MyProjects/atlassian_packages/responsible-ai-api
# OPP-1: confirm gunicorn config still missing worker_class
grep -n "worker_class" src/gunicorn.conf.py

# OPP-2/OPP-6: confirm bare requests.X still present
grep -n "requests\.\(post\|get\)" src/inference_models/triton_openai_api_client.py src/tenant_context/tenant_context_client.py

# OPP-3: confirm 7+ from_incoming_http_request call sites
grep -rn "from_incoming_http_request\b" src/ --include='*.py' | wc -l

# OPP-4: confirm LLaMA double tokenization not yet removed on master
git log master --oneline --grep='RAI-01\|llama.*tokeni' | head
```
