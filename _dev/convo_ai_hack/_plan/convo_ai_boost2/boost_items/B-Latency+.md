# B-Latency+ — TTFB / p99 / first-chunk Wins NOT in T/L/N Series

> Part of [BOOST Plan v1](../BOOST_PLAN_v1.md). 5 items.
> **Goal anchor:** TTFB / p99 latency reduction → 150k MAU activation lever (perceived speed) + capacity (parallel-tool throughput).

---

## Y1 — SSE `event: ack` preamble flushed immediately after auth

**Files:** `modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt:164,254`

**Problem:** NDJSON streaming endpoints (e.g., `/v1/channel/{conversationId}/message/stream` and `/v1/invoke_agent/stream`) currently produce `Flux<Any>` — but the **first byte the client sees is the first LLM chunk**, which can be 2-10 seconds after request entry. Browser/SDK timeouts and "feels slow" perception are dominated by this first-byte latency.

**Estimated saving:** **−50-150ms perceived TTFB** (and sub-second timeout-immunity)
**Effort:** S (2-3 days)
**Risk:** Low (preamble is non-payload; client SDKs already tolerant of `event:ack` lines)
**Approach:**
1. Immediately after authentication succeeds (before tenant resolution / conversation hydration), `sink.next("event: ack\\ndata: {\"timestamp\": ...}\\n\\n")`
2. Add SSE `flush()` call (Netty's `Flux<DataBuffer>` requires explicit signal)
3. Update client SDKs to consume and ignore `event: ack` (likely already tolerant)

**Acceptance:** Wireshark / RUM shows time-to-first-byte ≤200ms (was 2-10s); ack frame received before LLM-first-chunk in 99% of requests.

**User-perceived impact:** Chat session, AIFC create, agent loop — ALL streaming endpoints feel responsive.
**FY26 goal:** 150k MAU activation (perceived speed).

---

## Y2 — Eliminate `.block()` calls on pre-LLM serial paths 🔴 TOP-4 ITEM

**Verified file:line evidence (4 sites):**

| File | Line | Risk |
|------|------|------|
| `modules/product/rovo/rovo-impl/.../tooldeclarations/ToolDeclarationDsl.kt` | 12 | False positive (lambda parameter named `block`) |
| `modules/product/rovo/rovo-impl/.../template/ConfluencePageTemplateFetcherPlugin.kt` | 59 | **REAL** — pre-LLM template fetch |
| `modules/product/rovo/rovo-impl/.../client/codesearch/DevAICoreClientImpl.kt` | 120 | **REAL** — pre-LLM code search |
| `modules/product/rovo/rovo-impl/.../client/assistanceServiceEval/AssistanceServiceEvalServiceImpl.kt` | 218 | **REAL** — eval service call |

**Problem:** `.block()` on `Mono`/`Flux` blocks the calling thread until the reactive call completes. On a servlet thread, this **wastes the entire HTTP-handler thread** and adds 100-300ms p95 TTFB (network call + thread-context-switch). Compounds with L3 (`runBlockingWithContext` in `ChatV1Controller`).

**Estimated saving:** **−100-300ms p95 TTFB** + frees servlet thread for other requests
**Effort:** M (1-2 weeks for 3 real sites + audit)
**Risk:** Low (suspend conversion is mechanical)
**Approach:**
1. Convert each calling site to a `suspend` function
2. Convert the `Mono.block()` to `.awaitSingle()` or `.awaitFirstOrNull()`
3. Trace upward to see which controller calls into the suspend chain — convert intermediates as needed
4. Add `@Suppress("ForbiddenBlockCall")` lint rule that BLOCKS new `.block()` calls (PR-time check)

**Acceptance:** 0 `.block()` calls remain in pre-LLM paths under `modules/product/rovo/rovo-impl`; p95 TTFB on `/v1/channel/.../message/stream` shows -100ms.

**Compounds with:** L3 `runBlockingWithContext` removal (v7) — both free servlet threads on the hot path.

---

## Y3 — Parallel tool-call execution within single LLM-decision turn 🔴 TOP-9 ITEM

**File:** `modules/platform/workflow/workflow-impl/.../execution/SimpleLoopWorkflowExecutorImpl.kt` (executeTools loop)

**Problem:** When the LLM emits ≥2 tool calls in one decision (modern LLMs do this routinely with parallel function calling), the loop executes them **sequentially**. If each tool takes 500-1,500ms, this adds 500-2,000ms p95 latency for every multi-tool turn.

**Estimated saving:** **−500-2,000ms p95** when LLM emits parallel tools
**Effort:** S-M (1 week — the implementation is small but safety analysis matters)
**Risk:** Low (R-6A makes side-effects safe; `parallelizable=true` allowlist initially limited to read-only tools)
**Approach:**
1. Per-tool registry annotation `parallelizable: Boolean = false`
2. In `executeTools()`, group calls into:
   - **Parallel batch:** all `parallelizable=true` tools → `awaitAll`
   - **Sequential batch:** all `parallelizable=false` tools → existing per-tool loop
3. Initially mark only **read-only** tools (search, fetch, list) as parallelizable
4. After R-6A live ≥7 days, allow opt-in for side-effecting tools
5. Add `convoai.tool_loop.parallel_count` counter

**Acceptance:** ≥30% of multi-tool turns use parallel batch; p95 multi-tool-turn latency -500ms.

**Compounds with:** R-1A per-tool deadline (my open PR #29112) — deadline applies per-tool, parallel execution still bounded.
**FY26 goal:** 150k MAU activation + capacity.

---

## Y4 — Speculative pre-warm (parallelize tenant resolution + auth + user-context hydration)

**File:** `RovoChatService.chatStream()` and `ChatV1Controller`

**Problem:** Currently sequential: auth → tenant resolution → user-context hydration → LLM call. Each step is 30-100ms; sequential = 100-300ms before LLM.

**Estimated saving:** **−80-200ms p50 TTFB**
**Effort:** M (1-2 weeks)
**Risk:** Low (additive parallelism)
**Approach:**
1. After auth completes, `coroutineScope { async tenant; async userContext; async embeddingPrep }`
2. `awaitAll` before LLM call
3. Add `convoai.pre_llm_phase.parallel_saving_ms` histogram

**Acceptance:** p50 TTFB shows -80ms; per-step latency unchanged.

**Compounds with:** L1 AsyncTenantContext caching (v7) — both reduce pre-LLM serial time.

---

## Y5 — Per-request Statsig FF-eval memo (extends N6)

**Files:** Multiple sites in `modules/product/rovo/`, `modules/platform/conversation/`

**Problem:** N6 (v7) hoists Insights Statsig FF eval. **Beyond Insights**, multiple sites in the chat path evaluate the same FF multiple times per request. Each FF eval is 1-5ms; aggregate ≥20-50ms p95.

**Estimated saving:** **−20-50ms p95**
**Effort:** XS (2-3 days)
**Risk:** Very low (drop-in)
**Approach:**
1. Per-request `Map<FlagKey, Result>` cache (request-scoped, no cross-request pollution)
2. Wrap `featureGatesService.checkGate(...)` with cache-aware extension
3. Add `convoai.statsig.ff_eval_count_per_request` histogram (target ≤10)

**Acceptance:** Per-request FF-eval count ≤10 (was 30-50); per-request FF-eval-total-time -50%.

**Compounds with:** N6 (v7) — N6 hoists Insights specifically; Y5 generalizes to chat path.

---

## Summary Table

| ID | Title | TTFB / p95 saving | Effort | Risk | User Impact |
|----|-------|---------------------|--------|------|-------------|
| **Y1** | SSE `event:ack` preamble | -50-150ms perceived | S | Low | All streaming |
| **Y2** | Eliminate `.block()` calls | -100-300ms p95 | M | Low | Chat + tool flows |
| **Y3** | Parallel tool execution | -500-2,000ms p95 (multi-tool) | S-M | Low (gated) | Agent loop |
| **Y4** | Speculative pre-warm | -80-200ms p50 | M | Low | All chat |
| **Y5** | FF-eval memo | -20-50ms p95 | XS | Very low | All requests |
| **TOTAL** | | -750-2,700 ms p95 | | | |

**Combined with v7's T0a/T0b/T1/T2 (capacity) and L1/L3 (TTFB), BOOST B-Latency+ closes the perceived-speed gap to <500ms TTFB on most chat sessions.**
