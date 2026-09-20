# BOOST_INTEGRATED v2 — Comprehensive Per-PR Documentation

**Companion to:** `BOOST_INTEGRATED_v2.md`, `AUDIT_REPORT_v2.md`
**Date:** 2026-05-15
**Repository:** `atlassian/conversational-ai-platform`
**Purpose:** Provide deep, human-readable, code-grounded narrative for each of the 30 planned PRs. Each entry contains: title, plan-vs-audited impact, what is changed, where (file:line), why (business and technical motivation), the design sketch, dependencies, risks, success metrics, and an explicit pointer to gaps in the plan.

> **Reading guide:** Each section is self-contained. The "Audited evidence" subsection lists the exact files and lines verified against the live repository. The "Plan vs. reality" subsection is the most important quality control — it is where audit-discovered mis-statements are recorded.

## Workstream legend

- **P** — Perf Contract & Observability (PR #1, #2, #3)
- **A** — Architecture (PR #7 here; A1/A2/A3 deferred outside the 30)
- **L** — Latency & Cost (PR #5, #6, #14, #15, #16, #17, #18, #19, #25)
- **R** — Resilience (PR #9, #10, #11, #12, #13, #20, #21, #22, #23, #24)
- **I** — Conversation Intelligence (PR #4 (eval), #26, #27, #28, #29)
- **W** — Tactical wins / dev velocity (PR #8, #30)

---

## PR #1 — `[Impact: High] [observability] P3 — Real-time (model, experience, tenant) cost metric (foundation)`

**Workstream:** P (Perf Contract & Observability) · **Item:** P3 / OBS3 · **Goal anchor:** FY26 Cost foundation · **Stacked-on:** none.

### Plan-vs.-reality

| | Plan claim | Audited reality |
|---|---|---|
| Symbol exists today | (foundation, net-new) | `LlmTokenUsageReporter.kt`, `MeterCostResolutionService.kt` (`modules/platform/service/service-api/.../service/llm/` and `.../service/ubpenforcement/`) already track token usage and dynamic pricing. **No** Micrometer counter currently emits the joined `(model, experience, tenant)` triple. |
| Impact label | HIGH | **HIGH** confirmed — without this, every $/mo claim downstream is unprovable. |

### What this PR delivers

A single Micrometer counter (or a small family of counters) emitted on every successful LLM call from `LLMServiceImpl`, tagged with at minimum:

- `model` — `LanguageModelSpec.id` (e.g. `claude-3-7-sonnet`, `gpt-4-1`).
- `experience` — `Experience` enum (e.g. `AIMATE`, `AI_MATE_AUTOMATIONS`, `INSIGHTS`, `LH_ORCHESTRATOR`).
- `tenant` (or `tenant_tier`) — derived from `TenantContext.getCloudId()` (raw cloudId is high-cardinality; recommend bucketing into `tenant_tier` per anti-goal #45 once M1 lands).
- `usage_kind` — `prompt_tokens`, `completion_tokens`, `cached_tokens` (the last is the L1 leverage point).
- `cost_usd_cents` — derived via `MeterCostResolutionService` for the current model + region + UBP price plan.

### Where it goes

| File | Change |
|---|---|
| `modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/LLMServiceImpl.kt` | Wire `LlmTokenUsageReporter` outputs into a new `CostMetricEmitter`. |
| `modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/metrics/MetricKey.kt` | Add `LLM_COST_USD_CENTS`, `LLM_TOKENS` (kind-tagged). |
| (new) `modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/metrics/CostMetricEmitter.kt` | New class. |

### Why now

Listed across all three source plans as the #1 keystone. Without it, downstream PRs (#14 L6, #15-16 L3, #17 L1, #6 L7, #20 R3, #29 I4) cannot prove their cost claims, and anti-goal #52 ("don't promote a rollout cohort past 5%→25% until OBS3 has 7d of data") cannot be enforced.

### Risks & mitigations

- **High-cardinality blow-up** if raw `cloudId` is used as a tag — mitigate by bucketing into `tenant_tier` (free / standard / premium) and emitting raw cloudId only at debug/sample.
- **Performance** — Micrometer counters are O(1); negligible.

### Success metrics

- Splunk panel "convo-ai/cost-by-(model, experience, tenant_tier)" showing 100% of LLM calls with attribution.
- Reconciles within 1% of M4 Socrates `convo_ai_usage` daily total.

### Audit-discovered gap to fix in plan

None. Plan is correct in framing this as foundational. **Do** add the `cached_tokens` dimension explicitly — it is the metric that proves PR #17 (L1).

---

## PR #2 — `[Impact: High] [observability] P3 follow-up — per-experience cost panel + tenant-budget-overrun alarm <1min`

**Workstream:** P · **Item:** P3 / OBS3 · **Stacked-on:** PR #1.

### Plan-vs.-reality
This PR is purely additive on top of PR #1 and depends on it landing in production with stable tags before alarms can be calibrated. No code paths in repo today emit a per-experience cost panel. ✅ verified.

### What this PR delivers

1. **Splunk dashboard:** "convo-ai/cost-by-experience" with one stacked bar per Experience, broken down by model. Acts as the daily exec-level slice.
2. **Tenant-budget-overrun alarm** in Splunk (or Datadog, depending on team policy):
   - Trigger: a single `tenant_tier=premium` cloudId exceeds **2× its 7-day-rolling-mean** USD/min cost for ≥60 seconds.
   - Routes to convo-ai oncall + the COGS-watch Slack channel.
3. **Sub-1min alarm latency** is achieved by counting at `LLMServiceImpl` emit time, not waiting for the daily Socrates batch (which has ~24h lag).

### Why <1 minute matters

The plan correctly cites that today's cost-overrun detection is daily Socrates batch (24h lag). A single tenant or feature can spend $50k+ in that window if a runaway agent loops. <1min alarm shrinks blast radius by ~1440×.

### Risks & mitigations
- **Alarm fatigue** — calibrate threshold against 30 days of historical $/min variance per tier.
- **False negatives** during cold-start of a new model rollout — alarms suppressed for first 24h after a new `model` tag appears.

### Success metrics
- Mean-time-to-detect-cost-anomaly drops from ~24h to <60s.
- Dashboard daily reconciles within 1% of M4 Socrates.

---

## PR #3 — `[Impact: High] [perf-contract] P1 — Cat-1 Perf Contract instrumentation (TTFT/jitter/cancel/stream-success histograms)`

**Workstream:** P · **Item:** P1 (Z-1) · **Goal anchor:** FY27 Cat-1/3/5 SLO compliance · **Stacked-on:** none. **Gate:** jgrose confirms numeric SLO targets (anti-goal #50).

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| Symbol exists today | (net-new) | No `TTFT`, `timeToFirstToken`, `first_token` symbol found anywhere in `modules/`. `MetricKey` has counters but no Cat-1 SLO histograms. |
| Impact | HIGH | **HIGH** confirmed — replaces today's flat 99.9% SLO with user-perceptible histograms. |

### What this PR delivers

Four Micrometer histograms (timer-style with percentile buckets) emitted from the streaming write path:

1. **TTFT — Time To First Token.** From `ChatV1Controller.conversationStream(...)` request entry → first emitted NDJSON message containing model output. Tagged by `(experience, model, agent_type)`.
2. **Jitter — inter-chunk gap.** Histogram of milliseconds between successive emitted NDJSON chunks within the same response. Aggregated p50/p95/p99 surfaced; alarm fires if p95 > target (target TBD by jgrose).
3. **Cancel — client cancellation latency.** From client disconnect detection (`StreamingResponseBody` close) → upstream LLM call cancellation acknowledgement. The cancellation path already exists (`RovoChatServiceCancellationTest`). This adds telemetry.
4. **Stream-success rate.** Counter of streams that close cleanly vs. error-mid-stream. Surfaced as `(success_rate = clean_close / total_starts)`.

### Where it goes

| File | Change |
|---|---|
| `modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt` (lines 164, 254 — both `produces=application/x-ndjson` POST endpoints) | Wrap `Flux`/`StreamingResponseBody` to record timestamps and emit metrics. |
| `modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/metrics/MetricKey.kt` | Add `STREAM_TTFT_MS`, `STREAM_JITTER_MS`, `STREAM_CANCEL_LATENCY_MS`, `STREAM_OUTCOME` |
| `modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/RovoChatService.kt` (existing `concurrentConversations` gauge area, ~line 1075) | Add stream-start / stream-first-token / stream-end markers. |

### Why now

The FY27 Cat-1 perf contract (per-experience SLO) supersedes the FY26 flat 99.9%. We cannot claim SLO compliance without per-Experience TTFT measurements; the existing tomcat thread/concurrent-conversation gauges only measure capacity, not perceived latency.

### Dependency: jgrose's confirmation (anti-goal #50)

The PR commits the histograms; the alarm thresholds wait for jgrose to confirm numeric Cat-1 targets per Experience. Recommend committing thresholds in a separate PR after Wk 0 confirmation.

### Risks & mitigations
- **Over-counting** if a request retries — bind the histogram to the outermost request span (use `MDC` request-id).
- **Streaming back-pressure jitter** caused by client slow-read — distinguish `client_jitter` vs `server_jitter` by inspecting `StreamingResponseBody` write-pending state.

### Success metrics
- p95 TTFT per Experience visible in Splunk within 24h of merge.
- 0 false-positive jitter alarms in first 7 days.
- Stream-success rate baselined per Experience.

### Audit-discovered gap
None for this PR. Plan accurate. (But see PR #8 — its title mentions "SSE" for the same controller, which is wrong — controller emits NDJSON. Fix #8 in step.)

---

## PR #4 — `[Impact: High] [reliability][reliability-eval] G-3 — PR-gate eval harness on Goldens-300 (EVAL1)`

**Workstream:** I (Conversation Intelligence) · **Item:** G-3 / EVAL1 · **Stacked-on:** depends on v7-Q13-datasets.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| Eval framework | "exists" | ✅ Verified — `modules/platform/evaluation/` exists with `BatchEvaluationContext`, `BatchEvaluationExecutionService`, `LLMJudgeServiceImpl`. |
| PR-gate CI integration | "missing" | ✅ Verified — `bitbucket-pipelines.yml` has no Goldens-300 batch-eval step today. |
| Goldens-300 / Q13 dataset | (referenced) | ⚪ Not located in code — likely lives in v7's Q13 work / Databricks workspace. **Confirm before merge.** |
| Impact | HIGH | **HIGH** confirmed. |

### What this PR delivers

A new bitbucket-pipelines step that, on every PR touching `modules/product/**` or `modules/platform/service/llm/**`:

1. Runs `BatchEvaluationExecutionService` against the **Goldens-300** golden-set with the PR's HEAD model+prompt configuration.
2. Compares aggregate scores (LLM-judge `quality`, `groundedness`, `safety`) against the trunk baseline.
3. **Fails the build** if any aggregate metric regresses beyond a threshold (default: -3pp on quality OR any regression in safety).
4. Posts a comment to the PR with the diff table.

### Where it goes

| File | Change |
|---|---|
| `bitbucket-pipelines.yml` (after the existing IT-shard blocks ~line 633) | Add `&pr-gate-eval-goldens300` step with conditional `branches: feature/**`. |
| `modules/platform/evaluation/evaluation-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/evaluation/service/LLMJudgeServiceImpl.kt` | Add a CLI entrypoint (`mainPrEval()`) that reads HEAD config + Goldens-300 from a known location and emits JUnit-style XML. |
| (new) `bin/pr-eval-runner` | Shell wrapper for the bitbucket step. |
| (new) `evaluation/goldens300/` (or sym-link to v7's location) | Dataset checkpoint — the v7 Q13 work owns the dataset. |

### Why now

Anti-goal v7 #16 mandates that no quality claim ships without BatchEval on Q13 Goldens-300. Today this gate is enforced manually (developer runs eval before merge); enforcing in CI removes the human-in-the-loop and is the precondition for I4 (PR #29) to safely roll out skill-conflict changes.

### Risks & mitigations
- **Eval flakiness** — LLM-judge stochasticity. Mitigate by running at temperature=0 and median-of-3 on the LLM-judge layer.
- **Build wall-clock** — Goldens-300 is ~300 LLM calls; expect ~5 min added per PR. Acceptable per CI1 follow-up (PR #30 trims overall PR wall-clock by 25-35%).

### Success metrics
- 100% of PRs touching gated paths run the eval.
- Mean PR-eval wall-clock ≤ 5 min.
- 0 false-positive failures in first 4 weeks (calibrate threshold).

### Audit-discovered gap
**Title:** `[reliability][reliability-eval]` is an awkward double-tag. Recommend `[Impact: High] [eval][quality-gate] G-3 …`. The CSV row 4 also uses the double-tag — fix together.

---

## PR #5 — `[Impact: High] [latency] W-2 — Split hydratePool=2 web-Jsoup pool from history hydration pool (R23)`

**Workstream:** W (tactical wins) · **Item:** W-2 / R23 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `hydratePool=2` exists | yes | ✅ Verified — `modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt:44`: `private val hydratePool: CoroutineDispatcher = Dispatchers.IO.limitedParallelism(2)` |
| "history hydration uses hydratePool" | (implicit) | 🟡 **Unverified.** A separate `convHistPool: limitedParallelism(128)` exists at the same file — used for `ConversationHistoryItemManagerImpl`. So claim "history hydration uses hydratePool=2" needs a profile to confirm which call site. |
| Impact | HIGH | **MEDIUM** until profile data confirms which dispatcher is the bottleneck. |

### What this PR (likely) delivers

Two-pool split:
- `webHydratePool` — small (size 2-4) for outbound Jsoup fetches subject to external-site throttling.
- `historyHydratePool` — larger (size 32-64) for in-process ERS history hydration that doesn't go through Jsoup.

Both wired through the existing `CoroutineContextProvider` and `InstrumentedDispatcher`.

### Where it goes

| File | Change |
|---|---|
| `modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt:44, 83` | Split into two pools, expose two dispatchers. |
| `modules/foundation/utilities/utilities-impl/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/DispatcherMonitor.kt` (whatever defines `HYDRATE_IO`) | Add `WEB_HYDRATE_IO`, `HISTORY_HYDRATE_IO` enums. |
| All call sites currently using `hydrateDispatcher` | Move to the appropriate new dispatcher based on workload (Jsoup → webHydrate, ERS → historyHydrate). |

### Why now

If history-resume requests today serialize through a 2-coroutine pool that is also throttled by external Jsoup throughput, p95 latency on resume can spike to 2+ seconds for a moderately long conversation. Splitting frees the in-process work from the external-throttling pool.

### Risks & mitigations
- **Reverse risk** — if the `convHistPool=128` is already where history hydration runs, this PR has near-zero impact. **Profile first.**
- **External-site throttling** — keep webHydratePool ≤ 4 to honor existing politeness for outbound Jsoup.

### Success metrics
- p95 history-resume latency drop measurable in M2 latency histograms.
- `HYDRATE_IO` dispatcher utilization no longer correlates with `convHist` request volume.

### Audit-discovered gap (must fix before merge)
**Verify with profiling** that history hydration actually uses `hydratePool` and not `convHistPool`. If the latter, this PR is moot. Recommend tagging W-2 with `[needs-profile]` until then. Suggested label downgrade: HIGH → MEDIUM.

---

## PR #6 — `[Impact: High] [latency][cost] L7 — Drop accountId from MCP schema cache key (~80% Redis savings, AIFC7)`

**Workstream:** L (Latency & Cost) · **Item:** L7 / AIFC7 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `accountId` in cache key | yes | ✅ Verified — `MarathonMcpSchemaRedisCache.kt:29-34`: `data class MarathonMcpSchemaCacheKeyInput(val cloudId: String, val accountId: String, val serverAri: String, val mcpToolType: String?)` |
| Risk understated | — | 🔴 The class doc literally says: *"MCP tool availability can depend on the requesting account and tool type, so the cache key must include those dimensions to avoid leaking another user's integration inventory into the current prompt/runtime snapshot."* Dropping `accountId` naively leaks cross-user integration listings. |
| 80% Redis savings | claim | ⚪ Plausible (per-account cardinality blow-up) but unverified. |
| Impact | HIGH | **MEDIUM** — risk-adjusted, until safe key shape is designed. |

### What this PR delivers (correct framing)

Replace `accountId` in the cache key with a coarser-but-correct token that preserves the integration-inventory boundary:

- **Option A — entitlement hash:** hash of `(cloudId, sorted(server-entitlement-set))` so users with the same enabled integrations share a cache slot.
- **Option B — per-tenant namespace:** drop `accountId` only when the integration is `mcpToolType ∈ tenant-scoped`; keep it for `user-scoped`.
- **Option C — second-tier cache:** a per-tenant L2 cache layer in front of the per-account L1, capturing the common case.

The PR must include a security/privacy design note approving the chosen scheme. **Plan today does not call this out.**

### Where it goes

| File | Change |
|---|---|
| `modules/product/rovo/rovo-api/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/marathon/mcpdiscovery/MarathonMcpSchemaRedisCache.kt:29-34` | Modify `MarathonMcpSchemaCacheKeyInput`. |
| `modules/product/rovo/rovo-extras-impl/.../MarathonMcpSchemaRedisKeyGeneratorImpl.kt` (presumed) | Update key-gen logic. |
| (new) Test suite asserting cross-account cache isolation. |

### Why now

If `accountId` is a key dimension and a cloud has 5,000 active users, the same MCP server's schema is cached 5,000 times. With ~80% of users on common integration sets, an entitlement-hash key collapses 5,000 → ~5-50 keys.

### Risks & mitigations
- **Cross-user information leak** (highest) — see options above; **PR must include a security design note**.
- **Cache miss after schema drift** — tier the cache key by schema version.

### Success metrics
- Redis key cardinality for `mcp_schema/*` drops by ≥80%.
- 0 cross-account leak incidents in monitoring (specifically: log a counter when a cache hit returns an entitlement set NOT in the requesting user's entitlement list).

### Audit-discovered gap (must fix before merge)
- Add explicit anti-goal: "Do NOT drop `accountId` from the MCP schema cache key without first introducing a coarser key that preserves the per-account integration-inventory boundary documented in `MarathonMcpSchemaCacheItem`."
- Downgrade impact label HIGH → MEDIUM until the safe key scheme is designed.

---

## PR #7 — `[Impact: Medium] [latency] A5 — Typed Dynamic Config + RequestScopedLLMFlags (33+ FF evals → 1)`

**Workstream:** A (Architecture) · **Item:** A5 · **Stacked-on:** none. **Unblocks:** A3 (LLMServiceImpl decomposition).

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `RequestScopedLLMFlags` | implies absent | ✅ Confirmed absent. `RequestScopedValue` exists (`AI3PConnectorRequestCache.kt`); pattern available, not yet applied to LLM flag bundle. |
| 33+ FF evals per request | claim | 🟡 Codebase total of `checkGate/getConfig/isEnabled` calls is 1029 across non-test sources. Per-request count of dozens is plausible but unverified by this audit. |
| 20-50ms p95 latency win | claim | ⚪ Will need per-request profiling to validate. |
| Impact | MEDIUM | **MEDIUM** confirmed. |

### What this PR delivers

A `RequestScopedLLMFlags` bundle bean (likely lives in `modules/platform/service/service-api/.../service/llm/`) that:

1. Eagerly evaluates the full set of LLM-relevant feature flags **once at request entry** (in a Servlet filter or Spring `RequestScope`).
2. Caches the typed result in a `RequestScopedValue<LLMFlagBundle>`.
3. Replaces the 33+ scattered `rolloutService.controlledByFullContext(...).ofNewCode { … }` call sites in the LLM hot path with `requestFlags.useNewModel`, etc.
4. Provides a typed enum/sealed-class API instead of stringly-typed flag names — catches typos at compile time.

### Where it goes

| File | Change |
|---|---|
| (new) `modules/platform/service/service-api/.../service/llm/flags/RequestScopedLLMFlags.kt` | New bean. |
| (new) `modules/platform/service/service-api/.../service/llm/flags/LLMFlagBundle.kt` | Typed flag holder. |
| `modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/LLMServiceImpl.kt` | Replace `rolloutService.controlledBy…` calls with `requestFlags.X`. |
| ~30 other call sites in `modules/product/rovo/rovo-impl/.../agent/orchestrators/` | Same replacement. |

### Why now

Each `Statsig.checkGate` is a network round-trip (or local cache hit + lock); 33+ per request is measurable latency. More importantly, **A3 (LLMServiceImpl decomposition)** pulls flag-parsing logic into a separate component that needs a single read API — this PR creates that API. Hence the dependency: **A3 cannot land before A5** (anti-goal #47).

### Risks & mitigations
- **Stale-flag risk within a request** — by design, flags are frozen at request entry, so a flag flip mid-flight does not affect the current request. Document this clearly.
- **Eager-eval overhead** — bundle eval = N flag evals at once vs. N spread out; same total work, lower jitter.

### Success metrics
- Per-request `Statsig.checkGate` calls in LLM path drop to ≤1 (the bundle).
- p95 LLM-request latency drops 20-50ms (measurable in PR #3 TTFT histogram).
- A3 PR can begin after this lands.

---

## PR #8 — `[Impact: Medium] [latency] W-1 — SSE event:ack preamble for /ChatV1Controller streaming endpoints`

**Workstream:** W · **Item:** W-1 / Y1 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `/ChatV1Controller` is SSE | implied | 🔴 **WRONG.** `ChatV1Controller.kt:164` declares `produces = ["application/x-ndjson"]`. Same at line 254. The controller emits NDJSON, not SSE (`text/event-stream`). |
| TTFB-class win | yes | 🟡 An immediate first-chunk on stream-open is still a real win on NDJSON, but the wire format is different. |
| Impact | MEDIUM | **LOW** as currently scoped (must retitle). |

### What this PR (correctly framed) delivers

A "stream-opened" preamble emitted on the first NDJSON line of every `/chat/v1/channel/{conversationId}/message/stream` and `/chat/v1/invoke_agent/stream` response. Possible payloads:

```ndjson
{"type":"stream_ack","ts":1715750200123,"conv_id":"...","stream_id":"..."}
{"type":"agent_metadata","agent_id":"...","model":"..."}
{"type":"first_token","ts":1715750201500,"first_token":"…"}
```

Goal: get **something** to the client within ~10ms of TCP accept, so the client UI shows "thinking…" indicator immediately rather than after the LLM round-trip.

### Where it goes

| File | Change |
|---|---|
| `modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt:164, 254` | Emit `stream_ack` JSON line on the `Flux`/`StreamingResponseBody` before the suspending request to `assistanceClient`/`rovoAgentService` begins. |
| Client SDKs in `client/` — confirm they tolerate the new line type | Probably already filter unknown `type` values; verify. |

### Risks & mitigations
- **Schema drift** — clients that strictly validate must whitelist `stream_ack`/`agent_metadata`. Coordinate with rovo-chat-desktop, frontend Confluence/Jira teams.
- **Buffering** — if the servlet container buffers the first line until X bytes accumulate, the win evaporates. Verify `tomcat.flushAfterWrite` semantics in `application.yml`.

### Audit-discovered gap (must fix before merge)
- **Retitle:** `[Impact: Low] [latency] W-1 — NDJSON ack preamble for /chat/v1/{message,invoke_agent}/stream endpoints` (drop "SSE", drop "ChatV1Controller" — the controller and route names are clearer). Update CSV row 8.

---

## PR #9 — `[Impact: Medium] [reliability] PLT-15 — Silent failure remediation in ConversationStateManagerImpl:86-94 (counter + 1-retry)`

**Workstream:** R (Resilience) · **Item:** PLT-15 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `ConversationStateManagerImpl:86-94` silent failure | yes | ✅ **Verified verbatim.** File is 116 lines. Lines 85-95 contain `try { sessionPublicStore.update(conversationContext, sessionPublic) } catch (e: Exception) { log.warnWithContext("Failed to sync session public", …, e) // Don't re-throw - this is a side effect, not critical to the main operation }`. |
| Impact | MEDIUM | **MEDIUM** confirmed. |

### What this PR delivers

Two-step hardening of the silent-swallow at lines 85-95:

1. **Counter** — `metricsService.counter(MetricKey.SESSION_PUBLIC_SYNC_FAILURE, tags=("error_class", e.javaClass.simpleName))`. Without this, we can't measure the actual silent-loss rate.
2. **One retry with bounded back-off** — wrap the `sessionPublicStore.update(...)` call in a single retry (e.g., `withRetry(maxAttempts=2, baseDelay=100ms)`) before logging warn-and-swallow. Most transient `sessionPublicStore` failures are network blips that succeed on retry.

The `// Don't re-throw - this is a side effect, not critical to the main operation` comment **stays** — the agent-session-state main update has already succeeded; we just want to reduce silent loss of the side-effect sync.

### Where it goes

| File | Change |
|---|---|
| `modules/platform/conversation/conversation-impl/src/main/kotlin/io/atlassian/micros/convoai/conversation/ConversationStateManagerImpl.kt:85-95` | Add retry + counter. |
| `modules/platform/service/service-api/.../service/metrics/MetricKey.kt` | Add `SESSION_PUBLIC_SYNC_FAILURE`. |

### Why now

The plan is aligned with the broader v2 pattern: instrument every silent-swallow to know its rate; then add a small retry to halve it. Cheap, safe, observable.

### Risks & mitigations
- **Retry storm risk** — 1 retry with 100ms delay; capped. Negligible.
- **Misclassifying retry-non-retryable errors** — if `IllegalArgumentException` (bad input) hits this path, retry is a waste. Filter on `IOException`/`SocketTimeoutException` only.

### Success metrics
- Silent-loss rate visible in counter; trend down as PRs land.
- 1-retry recovery rate ≥ 30% on transient failures.

---

## PR #10 — `[Impact: Medium] [reliability] S2-Phase1 — Concurrent-conversation saturation gauge (RovoChatService:207, metric-only)`

**Workstream:** R · **Item:** S2 / PLT-11.5 · **Stacked-on:** none.

### Plan-vs.-reality (CRITICAL)
| | Plan | Reality |
|---|---|---|
| `RovoChatService:207` | gauge to be added | 🔴 **Line 207 already exists** as `private val concurrentConversations = AtomicInteger(0)`, and the gauge **is already emitted**: `RovoChatService.kt:1075-1076` `metricsService.gauge(MetricKey.CONCURRENT_CONVERSATIONS, concurrentConversations.incrementAndGet().toDouble())`; decrement at `:1190-1192`. There is also a duplicate gauge in `MarathonRuntime.kt:108, 205, 235`. |
| Impact | MEDIUM | **LOW** — what's actually missing is per-tag slicing, not the gauge itself. |

### What this PR (correctly framed) delivers

Add per-`(experience, tenant_tier, agent_type)` tags to the existing `CONCURRENT_CONVERSATIONS` gauge so saturation can be sliced by experience/tenant. Currently it is a single global gauge — useful for capacity planning but not for per-experience SLOs.

Optional second piece: **alarm** on the sliced gauge (e.g., per-tenant_tier saturation > 80% sustained 5min).

### Where it goes

| File | Change |
|---|---|
| `modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/RovoChatService.kt:1075, 1190` | Pass tags into `metricsService.gauge(...)`. |
| `modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/agent/orchestrators/marathon/MarathonRuntime.kt:205, 235` | Same. |

### Risks & mitigations
- **Tag cardinality** — `experience` ≤ 20 enums, `tenant_tier` ≤ 4, `agent_type` ≤ 50 → ~4000 unique series. Acceptable for Micrometer.

### Audit-discovered gap (must fix before merge)
- **Retitle:** `[Impact: Low] [observability] S2-Phase1 — Add (experience, tenant_tier, agent_type) tags to existing CONCURRENT_CONVERSATIONS gauge`. Drop the "(metric-only)" suffix — the metric exists. Update CSV row 10.

---

## PR #11 — `[Impact: Low] [perf] PLT-2-equivalent — TokenBucketRateLimiter spin-wait → AggResilienceProvider RateLimiter`

**Workstream:** R · **Item:** PLT-2 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `TokenBucketRateLimiter` exists | yes | ✅ Verified — `modules/foundation/utilities/utilities-impl/.../foundation/utilities/featureflag/TokenBucketRateLimiter.kt`, 37 lines. |
| "spin-wait" pattern | claim | 🟡 **Mischaracterized.** The class uses a CAS retry loop (`while(true) { val current = state.get(); …; if (state.compareAndSet(current, new)) return true }`). On contention it retries the CAS; on no-tokens it returns `false` immediately. Not a busy-wait for the clock, not a spin-wait for tokens. |
| `AggResilienceProvider` has RateLimiter | implied | ⚪ Not directly verified; `AggResilienceProvider.kt` currently exposes only `resolveBreaker()` (CircuitBreaker). RateLimiter would need to be added to it (Resilience4j supports it). |
| Impact | LOW | **LOW** confirmed. |

### What this PR delivers (correctly framed)

Two-line summary: replace the bespoke 37-line `TokenBucketRateLimiter` with a Resilience4j `RateLimiter` instance vended by `AggResilienceProvider` (which currently vends only `CircuitBreaker`). Benefits:
- Single resilience framework per anti-goal #42 (corrected wording).
- Free metrics, observability, and config-flag plumbing.
- Proven concurrency semantics (Resilience4j's `RateLimiter` is well-tested).

The current `TokenBucketRateLimiter` is correct but isolated — every dev encountering it has to reason about its CAS loop independently.

### Where it goes

| File | Change |
|---|---|
| `modules/platform/client/client-api/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggResilienceProvider.kt` | Add `resolveRateLimiter(serviceKey: AggServiceKey, config: RateLimiterConfig)`. |
| `modules/foundation/utilities/utilities-impl/.../TokenBucketRateLimiter.kt` | Mark `@Deprecated`; delete after callers migrate. |
| Callers of `TokenBucketRateLimiter` (find via grep) | Migrate. |

### Audit-discovered gap
- Drop "spin-wait" wording — replace with "bespoke 37-line `TokenBucketRateLimiter`". Otherwise direction correct, label LOW correct.

---

## PR #12 — `[Impact: Medium] [reliability] R2 — Standardized retry patterns (6 patterns → 1: ConvoAiRetryPolicy enum)`

**Workstream:** R · **Item:** R2 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| 6 distinct retry patterns | claim | 🟡 **Plausible but uncounted.** Files like `LLMServiceRetry.kt`, per-provider `*RateLimitException.kt` (Anthropic/OpenAI/Llama/DeepSeek/Nexusflow + Generic), plus ad-hoc retries in agent code. The "6" appears to enumerate roughly: (1) Resilience4j Retry in AGG, (2) `LLMServiceRetry`, (3) per-provider 429 handling, (4) ad-hoc `retry(times)` in Insights, (5) Spring `@Retryable` annotations (if any), (6) bespoke loops in `MarathonRuntime`. **Inventory should be added to PR description.** |
| Impact | MEDIUM | **MEDIUM** confirmed. |

### What this PR delivers

A single `ConvoAiRetryPolicy` enum (likely in `modules/foundation/utilities/...`) and an extension function `suspend fun <T> withRetry(policy: ConvoAiRetryPolicy, body: suspend () -> T): T` that wraps Resilience4j's `Retry`. Predefined policies:

- `LLM_TRANSIENT` — 2 retries, exponential backoff 100ms→400ms, retry on `IOException`/`429`/`503`.
- `LLM_RATE_LIMITED` — 5 retries, longer backoff, retry only on per-provider `RateLimitException`s.
- `STORAGE_TRANSIENT` — 1 retry, 100ms.
- `STREAMING_FATAL` — 0 retries (do not retry mid-stream).
- `IDEMPOTENT_MUTATION` — 3 retries with idempotency-key support (ties into PR #24 S3).
- `AGG_GRAPHQL` — already in AggResilienceProvider; bridge to the enum.

Then mass-migrate the 6 ad-hoc retry sites to call `withRetry(LLM_TRANSIENT) { … }` etc.

### Where it goes

| File | Change |
|---|---|
| (new) `modules/foundation/utilities/utilities-api/.../resilience/ConvoAiRetryPolicy.kt` | Enum + ext fn. |
| `modules/platform/service/service-api/.../service/llm/LLMServiceRetry.kt` | Migrate to use the enum. |
| Per-provider retry sites in `modules/platform/service/service-impl/.../languagemodelprovider/*` | Migrate. |
| Ad-hoc retry loops in `modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsServiceImpl.kt` and `modules/product/rovo/rovo-impl/.../agent/orchestrators/marathon/*` | Migrate. |

### Risks & mitigations
- **Behavior drift** — different sites have subtly different back-off curves; pick the most conservative as the new default and deviate explicitly per call site.
- **Test coverage** — each migrated site needs a regression test that the new policy still recovers from the original failure mode.

### Audit-discovered gap
Add an inventory table to the PR description listing the 6 (or N) sites being migrated, with current vs. new policy. Otherwise plan accurate.

---

## PR #13 — `[Impact: Medium] [reliability] R4 — Streaming quality gate (heuristic; uses TextGenerationRequest.fallbackModel)`

**Workstream:** R · **Item:** R4 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `TextGenerationRequest.fallbackModel` | yes | ✅ Verified — `TextGenerationRequest.kt:14`: `val fallbackModel: LanguageModelSpec? = null`. The hook exists. |
| Streaming quality gate | (net-new) | ✅ Confirmed absent. |
| Impact | MEDIUM | **MEDIUM** confirmed. |

### What this PR delivers

A heuristic streaming-quality gate that, mid-stream, detects degenerate output (e.g., infinite repetition, extremely low entropy, schema-violation in a structured-output stream) and cancels the in-flight LLM call to fall over to `fallbackModel`. Heuristics:

1. **Repetition gate** — if last N tokens form a 4+-gram repeated ≥ 3 times, cancel.
2. **Entropy gate** — for structured outputs, if the running output exceeds the response cap by 2× without parseable JSON, cancel.
3. **Tool-call thrash gate** — if the agent emits ≥ 5 identical tool calls in a window, cancel.

On cancellation, the stream is rebuilt from the same `TextGenerationRequest` but with `model = fallbackModel`, and the new stream's first chunks are emitted to the client (with a small `quality_recover` event).

### Where it goes

| File | Change |
|---|---|
| `modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/LLMServiceImpl.kt` | Wrap stream consumer with `StreamingQualityGate`. |
| (new) `modules/platform/service/service-impl/.../service/llm/quality/StreamingQualityGate.kt` | Heuristic gate. |
| Test fixtures for each heuristic. |

### Risks & mitigations
- **False positives on legitimate repetitive output** (e.g., user asks "list the integers 1 to 100") — make heuristics conservative; FF-gate per Experience.
- **Double-cost** — if the gate fires often, fallback triggers double LLM cost. Track FP rate via M20.

### Success metrics
- Gate fires <0.5% of streams.
- When fires, fallback recovers ≥ 70% of cases.
- Measured via M20 (per plan §7).

---

## PR #14 — `[Impact: High] [cost] L6 — Adaptive Marathon iteration cap via QueryComplexityService (RV5)`

**Workstream:** L · **Item:** L6 / RV5 · **Stacked-on:** PR #1 (P3 cost metric live ≥7d) · **Gate:** anti-goal #51 paired accuracy A/B.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `QueryComplexityService` exists | yes | ✅ Verified — `modules/product/rovo/rovo-impl/.../classification/QueryComplexityService.kt` (275 lines). Single LLM call to classify a query as DEFAULT/COMPLEX. |
| Marathon iteration cap | exists, not adaptive | ✅ Verified — `Agent.kt:890` `var maxIterations: Int? = TerminationCondition.Companion.DEFAULT_MAX_ITERATIONS`; `MarathonRuntime.kt:182` reads from `agent.config.terminationCondition.maxIterations`. **Currently constant per agent**, not adaptive on query. |
| `DEFAULT` classification used downstream | yes | 🟡 Returned by classifier; not yet wired into Marathon's `terminationCondition`. |
| Impact | HIGH | **HIGH** confirmed. |

### What this PR delivers

Wire `QueryComplexityService.classifyQuery()` output into Marathon's `TerminationCondition.maxIterations` selection at agent-build time:

- `DEFAULT` queries → cap at e.g. 5 iterations (was: `DEFAULT_MAX_ITERATIONS`, often 50+).
- `COMPLEX` queries → cap unchanged (`DEFAULT_MAX_ITERATIONS`).

Implementation sketch:
```kotlin
// in MarathonRuntime or LongHorizonOrchestratorAgent build path
val complexity = queryComplexityService.classifyQuery(userQuery, …)
val cap = when (complexity.classification) {
    "DEFAULT" -> SIMPLE_QUERY_ITERATION_CAP // FF-gated, default 5
    "COMPLEX" -> TerminationCondition.DEFAULT_MAX_ITERATIONS
    else -> TerminationCondition.DEFAULT_MAX_ITERATIONS // fallback
}
agent.config = agent.config.copy(
    terminationCondition = TerminationCondition(maxIterations = cap)
)
```

### Where it goes

| File | Change |
|---|---|
| `modules/product/rovo/rovo-impl/.../agent/orchestrators/marathon/MarathonRuntime.kt` (~line 116, 182) | Read complexity result; set adaptive cap. |
| `modules/product/rovo/rovo-impl/.../agent/orchestrators/LongHorizonOrchestratorAgent.kt` | Same wiring on the LH path. |
| `modules/product/rovo/rovo-impl/.../classification/QueryComplexityService.kt` | Cache classification on the `RequestScopedValue` so we don't re-classify per turn. |

### Why now

Empirically, simple queries (e.g., "what's my next meeting?") rarely need >2-3 Marathon iterations, but currently they share the high cap with research queries. Cutting the cap from 50 → 5 on `DEFAULT` cuts 80%+ of wasted LLM calls on the easy class.

### Risks & mitigations
- **Mis-classification under-shoots** — anti-goal #51 mandates a paired accuracy A/B showing ≤5% task-completion regression for DEFAULT-classified queries at the reduced cap. **PR must include the A/B harness**, not just the wiring.
- **Classification cost** — adds 1 LLM call up front; mitigated by `RequestScopedValue` caching across turns.
- **Cold start** — if classification fails, fall back to high cap (don't penalize on classifier outage).

### Success metrics
- Mean iteration count on DEFAULT-classified queries drops by ≥50%.
- DEFAULT-class task-completion rate within 5pp of trunk (A/B).
- $/mo Rovo cost (from PR #1 metric) drops measurably.

### Audit-discovered gap
None on the work itself. **CSV row 14 should include `accuracy-A/B-anti-goal-51` in the gates column** (only partially noted today).

---

## PR #15 — `[Impact: High] [cost][quality] L3-Phase1 — Insights cohort A/B harness (per-insight-type CTR baseline)`

**Workstream:** L · **Item:** L3 / INS1 · **Stacked-on:** PR #1, PR #4.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| 6 InsightTypes | yes | ✅ Verified — `modules/product/rovo/rovo-api/.../rest/insights/Defaults.kt:8-38` defines exactly 6: FOLLOW_UP, EMERGING, COMPANY, YOUR_TRENDING, RECOGNITION, MEETING. `RovoInsightsServiceImpl.kt:725-730` iterates these 6. |
| Each is its own LLM call | yes | 🟡 Indirectly — each InsightType has its own prompt config (`InsightPromptRegistry`) and is enqueued via `asyncStreamingTaskService` to `RovoChatServiceApi`, which makes the LLM call. So 6 InsightTypes × 1 LLM call/type per generation = 6 calls per Insights run for a user. |
| Cohort A/B harness | (net-new) | ✅ Confirmed absent. |
| Impact | HIGH | **HIGH** confirmed. |

### What this PR delivers (Phase 1: baseline)

A cohort-A/B harness that:

1. Logs the **current per-InsightType click-through rate** (CTR) and time-to-first-Insight latency for a 7-day baseline window. Tag by `InsightType`, `tenant_tier`, `experience`.
2. Enables a Statsig segment that can split users into "control" (current 6-call path) and "treatment" (future consolidated path, dark-launched).
3. Adds the M19 measurement fields (per plan §7): per-insight-type LLM cost, total Insights $/mo, per-insight-type CTR.
4. **Does NOT yet change generation logic.** This is purely instrumentation.

### Where it goes

| File | Change |
|---|---|
| `modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsServiceImpl.kt:725-730` | Wrap each per-type generation with cohort logging + per-type cost emission via PR #1 metric. |
| `modules/product/aifeature/aifeature-impl/.../proactive/listener/rovobuttonnudges/insights/` | Add CTR collection on click events. |
| (new) Splunk dashboard "convo-ai/insights-baseline". |

### Why now

Anti-goal #46 forbids shipping the consolidation (PR #16) without 7-day baseline data. This PR establishes that baseline.

### Success metrics
- 7-day baseline collected: per-type CTR, per-type cost, per-type latency.
- Treatment cohort can be flipped on at 0% via Statsig.

### Audit-discovered gap
None. Plan correct.

---

## PR #16 — `[Impact: High] [cost] L3-Phase2 — Consolidate 6-conv Insights → 1 structured-output call (gated by L3-P1 baseline)`

**Workstream:** L · **Item:** L3 / INS1 · **Stacked-on:** PR #15.

### Plan-vs.-reality
Same evidence as PR #15. The "6 → 1" arithmetic checks out structurally: 6 InsightTypes are independently prompted today; consolidating into a single structured-output call (one LLM round-trip producing a JSON with all 6 sections) is the design.

### What this PR delivers

Replace the 6 per-type LLM calls with a single LLM call that:
- Uses **structured output** (JSON schema) to produce all 6 InsightType payloads in one response.
- Composes a single system prompt that concatenates the 6 per-type prompt segments from `InsightPromptRegistry`.
- Parses the structured response into the existing per-type `Insight` types via the `InsightTypeMapping`.

### Where it goes

| File | Change |
|---|---|
| (new) `modules/product/rovo/rovo-extras-impl/.../insights/ConsolidatedInsightsLLMCall.kt` | Single-call generator. |
| `modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsServiceImpl.kt:725-730` | FF-gated branch: when treatment cohort, call consolidated path; else legacy 6-call path. |
| Per-type response classes (`Common.kt:15-20`) | Reuse via `InsightTypeMapping` for parsing the consolidated response. |

### Why now

The "single largest unclaimed lever" per plan §2 row 2. Each Insight call is 4k-8k tokens of prompt; collapsing 6 → 1 saves 5×4k = 20k+ prompt tokens per generation, plus the ~5 extra completions worth of output. Estimated −$30-80K/mo.

### Risks & mitigations
- **Quality regression** per-type — anti-goal #46 mandates ≥7-day baseline (PR #15) before flipping. Per-type CTR delta must be within −3pp on each type.
- **JSON schema brittleness** — per-type consumers are well-defined (`Common.kt:15`); use Jackson with strict mode + structured-output schema validation (PR #13 R4 catches schema violations mid-stream).
- **One model bad at all 6 types** — `fallbackModel` (PR #13 hook) covers this.

### Success metrics
- $/mo Insights drop ≥ 50% in 30 days (from PR #1 cost metric).
- Per-type CTR within ±3pp on each of the 6 types.
- Per-type latency improves (single call avoids per-type queue waits).

### Audit-discovered gap
None. Plan correct; gating discipline is exemplary.

---

## PR #17 — `[Impact: High] [cost] L1 — Cache-friendly prompt structure (completes .projects/cache-friendly-schema-agent-prompts/)`

**Workstream:** L · **Item:** L1 · **Stacked-on:** extends in-flight 4-PR plan in `.projects/`.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `.projects/cache-friendly-schema-agent-prompts/` exists | yes | ✅ Verified — `README.md`, `design.md`, `implementation-plan.md` (4-PR plan, all behind FF `ROVO_CHAT_MCP_AGENT_CACHE_FRIENDLY_PROMPT`). |
| `CacheFriendlyPromptAssembler` | future | 🟡 **Already landed** at `modules/product/rovo/rovo-impl/.../agent/prompt/CacheFriendlyPromptAssembler.kt` with companion test. So PR 1 of the in-flight plan has shipped. |
| Impact | HIGH | **HIGH** confirmed. |

### What this PR delivers

This is plan PR 4 (the *final* PR) of the in-flight 4-PR `.projects/cache-friendly-schema-agent-prompts/` rollout (per `implementation-plan.md`):

- Migrate the remaining V2 schema agents (`NotionSchemaAgentSpec`, etc.) to use `CacheFriendlyPromptAssembler` and the new V7 templates.
- Promote the FF `ROVO_CHAT_MCP_AGENT_CACHE_FRIENDLY_PROMPT` from staff/dogfood → 5% → 25% → 100% based on the Anthropic `cache_read_input_tokens` deltas observed in the dashboard.
- Optionally execute followup F1 ("Move system-prompt rendering into `CacheFriendlyPromptAssembler`") if not already in scope.

### Where it goes

| File | Change |
|---|---|
| `modules/product/rovo/rovo-impl/.../agent/orchestrators/longhorizon/agents/NotionSchemaAgentSpec.kt` (and the other listed V2 agents in `implementation-plan.md` §PR 4) | Adopt cache-friendly assembler. |
| Per-agent V7 pebble templates `templates/agent/minions/*_schema_agent_system_template_v7.pebble` | New static templates. |
| `modules/platform/base/.../features/RovoSpecificFeatureFlags.kt` | Promote rollout cohort. |

### Why now

Anthropic prompt-cache hit rate is the single biggest dial on Rovo Chat input-token cost. Per Anthropic's pricing (cached tokens at ~10% of normal), going from ~30% hit rate (current) to 80% on schema agents drops input-token cost ~3-5×.

### Risks & mitigations
- **Per-agent template drift** — checklist in `implementation-plan.md` §"Per-agent changes" enforces the same migration pattern across all 4 PRs.
- **Cache invalidation on schema drift** — already addressed by the `.projects/` design (V7 templates are static; turn-dependent vars move to providers).

### Success metrics (from PR #17 + the broader 4-PR plan)
- Anthropic `cache_read_input_tokens / total_input_tokens` ≥ 0.8 on schema-agent calls.
- Aggregate input-token cost on schema agents −60% vs. baseline.
- −$30K+/mo (per plan §2 row 3).

### Audit-discovered gap
None. The framing as "completes in-flight 4-PR plan" is correct given `CacheFriendlyPromptAssembler` already exists.

---

## PR #18 — `[Impact: High] [latency][reliability] L4 — N+1 elimination in ConversationHistoryItemManager (lines 529-604)`

**Workstream:** L · **Item:** L4 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| File length sufficient | yes | ✅ File is 803 lines. |
| Lines 529-604 contain three enrichment methods | yes | ✅ Verified — `withPluginInvocations` (529-551), `withMinionOutputs` (554-578), `withAgentUserContext` (580-603). |
| Pattern is N+1 | claim | 🟡 **Mischaracterized.** Each method already runs as `coroutineScope { allItems.map { async { … } }.awaitAll() }` — N parallel async calls, not classic sequential N+1. The fix is BATCH FETCH (1 query, all items), not "introduce parallelization". |
| −50-80% Object Store calls | claim | ✅ Consistent with batch fetch (N parallel calls → 1 batch call). |
| Impact | HIGH | **HIGH** confirmed (correctly framed). |

### What this PR delivers (correctly framed)

Replace the N parallel async per-item `pluginInvocationManager.getPluginInvocationsFromHistoryItem(...)` (and `minionOutputManager.getMinionOutputsFromHistoryItem(...)`, and `agentUserContextManager.getAgentUserContextFromHistoryItem(...)`) with a single batched fetch per page:

- Add `pluginInvocationManager.getPluginInvocationsForHistoryItems(conversationContext, items: List<…>)` returning `Map<HistoryItemId, List<PluginInvocation>>`.
- Same for `minionOutputManager` and `agentUserContextManager`.
- Replace the `.map { async { … } }.awaitAll()` with one batched call + index lookup.

### Where it goes

| File | Change |
|---|---|
| `modules/platform/conversation/conversation-impl/src/main/kotlin/io/atlassian/micros/convoai/conversation/history/ConversationHistoryItemManagerImpl.kt:529-604` | Switch the three methods to batch-fetch. |
| The three managers (likely in `modules/platform/conversation/conversation-impl/.../`) | Add the new batch APIs (preserve old per-item APIs for compatibility). |
| ERS query layer | Ensure batch query is single round-trip. |

### Why now

Even with parallelization, each of N async calls is a separate ERS round-trip; on a long conversation (~100 items) this is 100 round-trips × ~10ms = ~1s of latency. Batch fetch is 1 round-trip ≈ 50ms.

### Risks & mitigations
- **Page-size cap** — batch query may have a per-call size cap; chunk into batches of e.g. 50.
- **ERS query rewrite** — ensure the batch query supports the same predicates.

### Success metrics
- p95 `getHistoryItems` latency drops 1-3 seconds for long conversations.
- Object Store call count per request −50-80%.

### Audit-discovered gap
**Retitle:** `[Impact: High] [latency][reliability] L4 — Batched fetch for plugin invocations / minion outputs / agent user context (replaces N parallel async per-item fetches in ConversationHistoryItemManagerImpl 529-604)`. Drop the "N+1" framing — it's misleading given current code is parallelized fan-out.

---

## PR #19 — `[Impact: Medium] [latency] L5 — ERS query push-down (pageLimit + sortDescending; replace fetchAllPages)`

**Workstream:** L · **Item:** L5 · **Stacked-on:** none.

### Plan-vs.-reality
| | Plan | Reality |
|---|---|---|
| `fetchAllPages` exists | yes | ✅ Verified in `AgentVersionStoreImplTest.kt:159, 484, 522`, `AgentVersioningIntegrationTest.kt:84, 156, 227, 297, 341, 360, 394` — at least via test mocks. Actual production caller in `AgentVersionStoreImpl` is implied but not directly opened in this audit. |
| pageLimit/sortDescending push-down missing | claim | 🟡 Plausible but unverified by this audit. |
| Impact | MEDIUM | **MEDIUM** confirmed. |

### What this PR delivers

Replace client-side `fetchAllPages(...).filter{…}.sortedByDescending{…}.take(N)` patterns with ERS query parameters that push down `pageLimit` and `sortDescending` to the ERS query itself. Avoids fetching pages that are immediately discarded.

### Where it goes

| File | Change |
|---|---|
| `modules/platform/agent-version/agent-version-impl/.../AgentVersionStoreImpl.kt` | Push down sort+limit to ERS query. |
| Other `fetchAllPages` callers (find via grep on production code, not just tests). |

### Risks & mitigations
- **API surface** — ERS query DSL must support the predicates; verify before scoping.

### Success metrics
- Per-call ERS payload size −X% (X = avg ratio of all-pages to top-N).
- p95 latency on AgentVersion queries drops measurably.

### Audit-discovered gap
PR description should include the **actual** production callers of `fetchAllPages` (not only the test mocks) before merge. Tag `[needs-grep]` until then.

---

