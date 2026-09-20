# Proactive‑AI‑Platform — Goal‑Driven Improvement Plan (FY26 H2)

> Repo: `C:\Users\yxinl\OneDrive\Projects\PythonProjects\CoreProjects\_dev\proactive-ai-platform`
> Date: 2026‑05‑05 · Author: planning pass with parallel Explore + Plan agents
> Codebase docs at `…\_dev\proactive-ai-platform\codebase_understanding\` (verified against current source — drift noted below)

---

## 1. Context — why this plan exists

The `proactive-ai-platform` (PAI) is the Atlassian backend that powers proactive AI surfaces (Rovo Insights, conversation‑starter nudges, throttling). The team's single most important goal this half is the **Habitual AI Usage OKR** ([codebase_understanding/architecture/cross-cutting/01-business-and-technical-goals.rst](_dev/proactive-ai-platform/codebase_understanding/architecture/cross-cutting/01-business-and-technical-goals.rst)):

| OKR primary metric | Baseline (start H2) | Target (end H2) | Stretch |
|---|---|---|---|
| **AI invocations / month via proactive surfaces** | **400 K** | **1.5 M** | 1.2 M committed |

Supporting (planned, not yet enforced) SLOs:

| Endpoint | p95 latency | Reliability |
|---|---|---|
| `POST /api/v1/nudge/throttle` | **< 50 ms** | 99.9 % non‑5xx |
| `POST /api/v1/rovo-insights/generate` (HTTP enqueue) | **< 200 ms** | 99.9 % non‑5xx |
| Insights worker generation (end‑to‑end) | **< 30 s** | ≥ 95 % success |
| `/rovo/insights/status` poll | < 100 ms | — |
| LongRun pod throughput | 8 concurrent generations | — |
| SQS DLQ depth | 0 sustained | — |

The team's value‑chain map ranks **`feature/rovoinsights`** and **`feature/nudge`** as 🔴 highest‑impact, **`stratus`** + **`task`/`sqs`** as 🟠 high.

**Constraint set** the user gave us:
- No user‑facing behavior changes (e.g. don't swap recency→relevance ranking).
- Double‑check against historical development; don't undo prior intentional removals.
- Be innovative only when measurable goal/metric impact justifies the effort.
- Sequence as **multiple small, human‑readable PRs** — not one mega‑PR.

---

## 2. What I found (confirmed in code on 2026‑05‑05)

**Strategic gaps that block the OKR — confirmed by reading the actual files (not just docs):**

1. **Redis is provisioned but NOT wired into code.** `service-descriptor.sd.yml:30` declares `proactive-ai-cache` (Valkey 7.x, transit‑encrypted, EngineCPU alarm). [build.gradle.kts](_dev/proactive-ai-platform/build.gradle.kts) has zero Redis/Lettuce/Jedis/spring‑data‑redis dependencies; no `RedisTemplate`, `RedisConnectionFactory`, or `@Cacheable` anywhere in main sources. The codebase doc [modules/features/rovo-insights.rst:278](_dev/proactive-ai-platform/codebase_understanding/modules/features/rovo-insights.rst#L278) describes Redis as the result cache — **this is aspirational**, not implemented. PR #96 set up the resource only.

2. **`RovoInsightsGenerationTaskHandler` is a stub.** [`RovoInsightsGenerationTaskHandler.kt:17-25`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt#L17-L25) — body is one log line. No LLM call, no cache write. Real generation logic must be ported from `convo-ai-platform`.

3. **`/rovo/insights/{status,fetch}` are stubs.** [`RovoInsightsController.kt:25-29 / :35-45`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/RovoInsightsController.kt#L25-L45) — `/status` always returns `insightsAvailable=true`; `/fetch` always returns empty `RovoInsightsFetchResponse`. The `forceCacheMiss` field is silently ignored.

4. **Nudge throttle is hardcoded.** [`NudgeThrottleController.kt:33`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/nudge/api/rest/NudgeThrottleController.kt#L33) returns `(score=10, throttled=false)` for every call.

5. **AsyncTask framework lacks idempotency.** [`AsyncTaskServiceImpl.kt:48`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/task/internal/AsyncTaskServiceImpl.kt#L48) generates a fresh UUID per submit; [`AsyncTaskDispatcher.kt:44-84`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/task/AsyncTaskDispatcher.kt#L44-L84) has no "already done" check. `MaxReceiveCount=2` ([service-descriptor.sd.yml:113](_dev/proactive-ai-platform/service-descriptor.sd.yml#L113)) means a transient handler failure re‑runs the full LLM at full $.

6. **Visibility‑extension scheduler has no failure recovery.** [`VisibilityExtendingSQSQueueConsumer.kt:84-109`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/task/internal/VisibilityExtendingSQSQueueConsumer.kt#L84-L109) — uses Spring's default `TaskScheduler` (single‑threaded, unbounded queue); `ChangeMessageVisibility` failure only logs; no consecutive‑failure bound; **zero unit tests** for this class.

7. **All errors handled identically.** Permanent (bad input) vs transient (5xx, timeout) both go through SQS retry up to MaxReceiveCount → DLQ. Wastes budget on permanent errors and underserves true transients.

8. **No business metrics for the OKR.** [`MetricKey.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/service/metric/MetricKey.kt) defines only `PROACTIVE_TEST_*`, `TENANT_CONTEXT_BUILD_*`, `STREAMHUB_EVENT_*`. **Zero** metrics tagged with `surface`, `outcome=accept|dismiss|ignore`, `experience`, `model`, `cache_hit`. Histogram boundaries in [application.yml:17-25](_dev/proactive-ai-platform/src/main/resources/application.yml#L17-L25) start at 100 ms — invisible to the < 50 ms nudge SLO.

9. **AI Gateway egress timeout is 600 000 ms (10 min).** [service-descriptor.sd.yml:312](_dev/proactive-ai-platform/service-descriptor.sd.yml#L312). With insights worker SLO of 30 s, a hung LLM call ties a worker thread for 10 minutes = 1/8 of one pod's capacity per stuck call.

10. **Stratus integration burns latency on every call.**
    - [`IntegrationServiceToolProvider.kt:32-53`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/stratus/IntegrationServiceToolProvider.kt#L32-L53) — constructs a fresh `IntegrationServiceMcpSessionManager` + `McpAsyncToolset` per call, then `.blockingGet()` for the tool list. ~200–500 ms wasted per insights generation on TCP + MCP handshake + tools/list.
    - [`AIGatewayServiceImpl.kt:67-83`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/stratus/internal/AIGatewayServiceImpl.kt#L67-L83) — `buildRunner` constructs a new `StratusRunner` per request; downstream callers `.blockingGet()` the entire `Flowable<Event>` into a `List` before responding (no streaming, full memory buffer, pinned thread).
    - No prompt‑caching headers configured on `UnifiedLlmProvider`.

11. **Async executor `queueCapacity = 0`.** [`WebMvcConfiguration.kt:48`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/config/WebMvcConfiguration.kt#L48) — any micro‑burst above 64 threads → `RejectedExecutionException` → HTTP 500 storm.

12. **Feature‑flag eval not memoized per request.** [`FeatureServiceImpl.kt:44-75`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/featuregate/internal/FeatureServiceImpl.kt#L44-L75) calls `getFeatureGateUser(...)` (allocates 2 mutableMaps) + `featureGatesService.checkGate(...)` on every call. Repeated checks of the same flag in one request hit the SDK 5×.

13. **No per‑tenant cost / budget gate.** Nothing prevents a single misbehaving tenant from monopolising the AI Gateway quota.

14. **Test coverage debt** (per [overviews/03-criticality-dashboard.rst §4](_dev/proactive-ai-platform/codebase_understanding/overviews/03-criticality-dashboard.rst)): zero tests for `utility/threading` (P1 blast), zero for `stratus` business logic, zero for `VisibilityExtendingSQSQueueConsumer`, no controller unit tests for `RovoInsightsController`.

**Historical sanity‑check** (`git log`, PRs #96–#108):
- Nothing was deliberately *removed* that this plan re‑introduces. The Redis client was never added; the visibility‑extension scheduler was added in PR #103 but its failure paths were left aspirational; the metrics package has only ever held test/streamhub keys.
- PR #103 (visibility extension) is the single largest production‑throughput PR (8×). Plan respects its design and only hardens the failure paths.
- PR #108 (MCP integration) added the per‑request session manager — by design (cloudId + user are request‑scoped) — but did not address tool‑list caching, which is a **value‑add not a regression** to introduce.

---

## 3. Strategic frame — how to prioritise

Each plan item is scored against **exactly one** of these OKR/SLO levers. PRs without a quantifiable lever do not enter the plan.

| Lever | Maps to | What it shifts |
|---|---|---|
| **L1: Activate Insights generation** | OKR primary metric | Unblocks ~biggest single contributor to 400 K → 1.5 M (currently 0 invocations from insights handler). |
| **L2: Activate Nudge throttle** | OKR + Stage‑2 launches | Unblocks PMs to ramp new proactive surfaces with safety. |
| **L3: $/invocation reduction** | Stretch headroom for OKR | Cache hits + dedup + prompt caching. Direct LLM cost saving + relieves AI Gateway quota. |
| **L4: Latency p95** | Nudge SLO 50 ms · Insights enqueue SLO 200 ms | Removes blocking I/O, FF dedup, tighter histograms. |
| **L5: Throughput / pod** | 8 concurrent generations / LongRun pod | Concurrency cap + tighter timeouts + idempotency. |
| **L6: Reliability / DLQ depth** | 99.9 % non‑5xx · 0 sustained DLQ | Visibility‑extension hardening + error classification + budget gate. |
| **L7: Observability gap** | All other levers depend on this | Metric vocabulary + tighter histograms + cardinality safety. Must land **first**. |

Priority rule: **everything ramped behind a Statsig flag**, default off, unless purely additive (metrics) or behind a no‑op default (cache abstraction with no callers).

---

## 4. The plan — two parallel tracks of small PRs

PRs are sized to be human‑reviewable (~150–400 LOC target). Bigger work is split. Each PR carries its own flag for ramp + rollback. **Track A (Platform Foundation)** unblocks **Track B (Feature & LLM)**.

### 4.1 Track A — Platform Foundation (unblocks everything)

#### A0. Business‑metric vocabulary + tighter histograms `[L7]` ⭐ ship first
**Files:** `service/metric/MetricKey.kt`, `service/metric/HistogramBucket`, `application.yml`, new `service/metric/BusinessMetrics.kt` facade.
**What:** Add new `MetricKey`s — `INVOCATION_COUNT/LATENCY` (tags: `surface`, `experience`, `model`, `outcome`, `cache_hit`, `dedup_hit`), `INSIGHTS_ENQUEUE_LATENCY`, `INSIGHTS_E2E_LATENCY`, `INSIGHTS_GENERATION_SUCCESS/FAILURE`, `INSIGHTS_CACHE_HIT/MISS`, `LLM_INPUT_TOKENS / OUTPUT_TOKENS / CACHED_INPUT_TOKENS`, `NUDGE_THROTTLE_DECISION` (tags: `nudgeType`, `decision`, `reason`), `DLQ_MESSAGE` (tags: `queue`, `dlq_class`), `CACHE_OP` (tags: `namespace`, `op`, `outcome`), `FEATURE_FLAG_EVAL` (tags: `flag`, `outcome`, `source`). Add `NUDGE_HISTOGRAM_BUCKETS` (1, 5, 10, 25, 50, 100, 200, 500 ms) and `INSIGHTS_ENQUEUE_BUCKETS` (10, 25, 50, 100, 200, 500, 1000 ms). New `BusinessMetrics` facade enforces tag allowlist (no `tenantId` ever) — prevents SignalFx cardinality blowup.
**Why (lever, quantified):** L7. Without this we cannot *measure* the 400 K → 1.5M trajectory, success‑rate SLO, or cache hit‑rate. Tighter buckets make the < 50 ms nudge SLO measurable for the first time.
**Order deps:** None.
**Risk / blast:** Negligible (no behavior change). Coordinate one‑time Grafana dashboard refresh with Brian Feldman. Reference [overviews/03-criticality-dashboard.rst §3](_dev/proactive-ai-platform/codebase_understanding/overviews/03-criticality-dashboard.rst) — `service/metric` is P1, requires 1 SRE‑tagged reviewer.
**Test plan:** Unit tests per metric key (tag set verified); cardinality test (1 000 fake tenants → tag‑set count < 50); local Micrometer composite‑registry assertion.
**Rollback:** Revert PR. Pure additions; no caller depends on these yet.

#### A1. Redis client + `ProactiveAiCache` primitive `[L3, L4]`
**Files:** `build.gradle.kts` (add `spring-boot-starter-data-redis`), `application{,-local,-staging,-prod}.yml`, new `platform/cache/{ProactiveAiCache, CacheNamespace, RedisKeyCodec, JsonValueCodec, LettuceProactiveAiCache, ProactiveAiCacheConfig}.kt`. Health endpoint: add Redis probe to `/deepcheck`.
**What:** Reusable cache primitive (per the user's framework‑design preference — design for future consumers, not just current ones). Operations: `get`, `put`, `getOrCompute`, `setIfAbsent` (used by A2 idempotency), `increment` (used by Nudge throttle B6). `CacheNamespace` enum forces declared intent (`INSIGHTS_RESULT`, `IDEMPOTENCY`, `NUDGE_COUNTER`, `COALESCE_LOCK`, `BUDGET_COUNTER`); `pai:{env}:{namespace}:{key}` codec for grep‑in‑CloudWatch + namespace flush. **Cache failures degrade gracefully — interface has no `throws`; Redis errors → return `null` + `cache.error` metric, never throw to caller.** Lettuce default; commandTimeout 200 ms, connectTimeout 1 s. ZERO callers in this PR; gated by `proactive-ai.cache.enabled` (default true non‑local) so existing tests don't need Testcontainers.
**Why (lever, quantified):** L3, L4. Foundational. Without this no feature can dedupe, cache, or counter. Estimated 30–50 % redundant LLM call elimination once insights cache is wired (B4) at 1.5 M monthly = ~$ figure tracked via A0 metrics post‑rollout. Also unblocks nudge throttle counters (B6).
**Order deps:** A0 (uses `CACHE_OP` metric).
**Risk / blast:** Medium. New connection pool per JVM (Lettuce/Netty), separate from AWS SDK pool — no contention. P0 package (`config/`) touched lightly. Ramp by enabling `proactive-ai.cache.enabled` per environment, not by % traffic.
**Test plan:** Testcontainers Valkey 7.x integration tests — cache miss → loader → cached, Redis down → null + metric (no throw), TTL honored, namespace isolation.
**Rollback:** `proactive-ai.cache.enabled=false` → no‑op impl. No callers depend on it yet (safe).

#### A2. AsyncTask idempotency + dedup wrapper `[L3, L5]`
**Files:** `task/AsyncTask.kt` (add `idempotencyKey: String?` default `null`), `task/AsyncTaskHandler.kt` (KDoc), `task/internal/AsyncTaskServiceImpl.kt`, `task/AsyncTaskDispatcher.kt`.
**What:** `AsyncTaskService.submit`: when `task.idempotencyKey != null`, `cache.setIfAbsent(IDEMPOTENCY, "{type}:{key}:submitted", taskId, ttl=24h)`; collision → return existing taskId, **don't send to SQS** (records `task.dedup.hit`). `AsyncTaskDispatcher.dispatch`: pre‑handler `cache.get(IDEMPOTENCY, "{type}:{key}:done")` → skip if present (defends against MaxReceiveCount retry after success but before ack). Post‑success `cache.put(":done", ttl=24h)` *before* `onSuccess`. TTL ≫ MaxReceiveCount × VisibilityTimeout (= 12 min) by 100×.
**Why (lever, quantified):** L3, L5. With MaxReceiveCount=2 and ~$0.04 / LLM invocation, every transient handler failure today doubles cost. At 1.5 M / mo with conservative 2 % transient rate → ~30 K duplicate LLM calls (~$1.2 K / mo) avoided. Also closes A3 visibility‑extension duplicate‑delivery gap.
**Order deps:** A1 (`setIfAbsent`, `get`, `put`).
**Risk / blast:** Medium. P1 (`task/`) — 1 platform owner reviewer. Adds 1 Redis GET per dispatch (~1 ms). False‑positive (dedup‑hit when work didn't happen) impossible because `:done` only written after `handle()` returns.
**Test plan:** Unit — same task submitted twice → 1 SQS message + 1 taskId; dispatcher receives same envelope twice → handler called once; handler throws → no `:done` → next delivery re‑runs. Integration — full SQS round trip with injected duplicate.
**Rollback:** Statsig kill‑switch `platform.async-task.idempotency.enabled` checked in submit + dispatch.

#### A3. Visibility‑extension hardening + dedicated TaskScheduler `[L5, L6]`
**Files:** `config/WebMvcConfiguration.kt` (or new `config/SchedulerConfig.kt`), `task/internal/VisibilityExtendingSQSQueueConsumer.kt`, new `task/internal/VisibilityExtendingSQSQueueConsumerTest.kt`.
**What:** Dedicated `ThreadPoolTaskScheduler` (`pai-visibility-heartbeat-`, poolSize=4) so heartbeats can't be starved by other `@Scheduled` users; monitored via `ExecutorServiceMetrics`. Track consecutive `extendVisibility` failures in `AtomicInteger`; after 2 consecutive failures emit `task.visibility.extend.failure` (tags: `queue`, `errorType`) + `task.visibility.extend.success`. **Honest scope note:** the bound is *observability + alerting*, not cooperative cancellation (most LLM HTTP calls don't honor `Thread.interrupt`). The deeper "abort handler when visibility lost" fix is documented as a follow‑up PR. Add the missing unit test class (currently 0 LOC of coverage per [criticality-dashboard §4.3](_dev/proactive-ai-platform/codebase_understanding/overviews/03-criticality-dashboard.rst)).
**Why (lever, quantified):** L5, L6. Today a SQS API blip silently degrades to duplicate delivery (which A2 then catches at the `:done` layer). A3 makes the failure observable + bounded so SRE can alert on `extend.failure / extend.total > 1 %`.
**Order deps:** A0 (metrics).
**Risk / blast:** Low. Pure additions to behaviour; revert‑safe.
**Test plan:** Heartbeat fires every 25 s; `ChangeMessageVisibility` throws → metric incremented, handler still runs; cancelled in `finally`.
**Rollback:** Revert PR.

#### A4. Error classification + per‑class SQS handling `[L3, L6]`
**Files:** new `platform/error/{TaskError, PermanentTaskException, TransientTaskException}.kt`, `task/AsyncTaskDispatcher.kt`, `feature/rovoinsights/internal/RovoInsightsGenerationSqsQueueConsumer.kt`.
**What:** Sealed `TaskError` (`Permanent` / `Transient`) with `fromException(Throwable): TaskError` classifier. `Permanent` → log + `task.error.permanent` metric + write `:done` marker (A2 dep) + ack message (no SQS retry). `Transient` → rethrow as today. Tag metric with `dlq_class`.
**Why (lever, quantified):** L3, L6. Permanent errors (bad cloudId) today bounce twice through MaxReceiveCount before DLQ — wastes 2× cost + delays the DLQ alarm signal. Adds the `dlq_class` dimension SRE needs for "0 sustained DLQ depth" SLO (today they can't tell whether DLQ is a code bug or a transient blip). Conservative classifier — when in doubt, `Transient` (today's behavior).
**Order deps:** A2 (uses `:done`), A0 (metrics).
**Risk / blast:** Medium‑high — misclassifying transient as permanent silently drops work. Mitigation: `platform.error.classification.enabled` flag, default false. Ramp 10 % → 50 % → 100 % weekly, watching DLQ depth + permanent rate.
**Test plan:** Each known exception type → expected class; unknown `RuntimeException` → `Transient` (safe default); `Permanent` → handler not retried, `:done` written; `Transient` → exception propagates.
**Rollback:** Statsig flag flip → uniform behaviour. Already‑acked permanent‑classified messages are unrecoverable, hence the slow ramp.

#### A5. Per‑request feature‑flag memoisation `[L4]`
**Files:** `featuregate/internal/{FeatureServiceImpl, FeatureFlagContextServiceImpl}.kt`, `requestcontext/RequestScopedValueKey.kt` (add `FEATURE_FLAG_EVAL_CACHE`).
**What:** Wrap `checkGate*` results in a per‑request `MutableMap<(statsigKey, contextType, randomizationId), Boolean>` stored in the existing `RequestScopedValueService` (cleared at request end automatically). Also memoise `FeatureGateUser` (currently rebuilt with mutableMap allocs per call). **Do NOT memoise `getExperiment` with `logExperimentExposure=true`** (Statsig SDK relies on the call to log) — only the boolean hot path.
**Why (lever, quantified):** L4. In a hot path checking 5 flags, 5× SDK calls + 5× allocation per request. Statsig in‑process is ~0.2 ms / check; 5 × 0.2 = 1 ms recovered + reduced GC. At 600 RPS sustained (1.5 M / mo), nudge‑throttle p95 should drop ~2–5 ms (~10 % of the 50 ms budget).
**Order deps:** A0 (uses `FEATURE_FLAG_EVAL` metric).
**Risk / blast:** Low. Per‑request scope ⇒ no cross‑tenant leakage. Exposure‑logging trap above is the one real risk.
**Test plan:** Same gate twice in one request → SDK called once; same gate, different request → SDK called once per request; exception in SDK → cached as default within request; experiment NOT cached when exposure logging on.
**Rollback:** Statsig flag `platform.featureflag.memoization.enabled`.

#### A6. Async executor queueCapacity + AI Gateway timeout sanity `[L5, L6]`
**Files:** `config/WebMvcConfiguration.kt` (queueCapacity 0 → 64 + `RejectedExecutionHandler` emitting metric), `service-descriptor.sd.yml` (`ai-gateway` `timeoutMs` 600 000 → **60 000** — see reasoning), `application.yml` (new `proactive-ai.ai-gateway.client-timeout-seconds: 60`).
**What & reasoning for 60 s** (reconciling the two Plan agents — 90 s vs 45 s): end‑to‑end SLO is 30 s. Insights handler (B3) fans out 6 sub‑LLM calls bounded by `Semaphore(3)` → each sub‑call has ~10–15 s budget. 60 s gives ~3× p99 single‑sub‑call headroom while reclaiming ~9 min per stuck call vs today.
**Why (lever, quantified):** L5, L6. With 8 worker threads / pod and even one stuck call/hour today, 60 s reclaims ~8.7 % capacity per pod. Async‑executor 0→64 queue prevents `RejectedExecutionException` → 500 storm under burst.
**Order deps:** A0 (rejection metric), A4 (`TransientTaskException` for upstream timeout).
**Risk / blast:** Medium‑high. Tighter timeout could break a legitimately slow generation. Mitigations: (a) ship the timeout drop as a SEPARATE commit inside the same PR (revertable independently), (b) Statsig flag for the executor queue capacity, (c) watch `insights.e2e.latency` p99 + `ai-gateway.timeout.count` for 1 week post‑rollout.
**Test plan:** Unit — rejection records metric, doesn't 500; timeout fires at configured value. Load test — 50 RPS into insights endpoint with mocked slow upstream.
**Rollback:** Independent flags for queue capacity + service‑descriptor revert. Done as 2 commits.

---

### 4.2 Track B — Feature / LLM (drives the OKR directly)

#### B0. Cache the MCP tool list (drop blocking + per‑request handshake) `[L4, L5]`
**Files:** `stratus/IntegrationServiceToolProvider.kt` (rewrite), new `stratus/internal/McpToolListCache.kt`.
**What:** Replace per‑call `IntegrationServiceMcpSessionManager` + `McpAsyncToolset.build()` with a Caffeine cache keyed by `(cloudId, actionIdsHash)` returning a memoised `List<BaseTool>` (5 min TTL, refresh‑after‑write, max 5 000). `removalListener` closes the underlying session. Expose `getToolsAsync(): Mono<List<BaseTool>>` so worker handler can stay non‑blocking.
**Why (lever, quantified):** L4, L5. Per‑call MCP cost is 200–500 ms (TCP + handshake + tools/list). At 1.5 M monthly insights × 250 ms saved = ~6 250 minutes / month of saved worker‑thread time + 1 fewer TCP socket churn / call.
**Order deps:** None platform; pure local Stratus win.
**Risk / blast:** Medium. 5 min TTL means a tenant entitlement flip is invisible for ~5 min. Mitigation: `forceCacheMiss` on `RovoInsightsStatusRequest` plumbed to a force‑refresh hook + 5 min TTL aligned with Statsig flag refresh cadence. Currently only callers are test endpoints + (future) insights worker.
**Test plan:** 100 concurrent `getTools(cloudId=A)` → loader fires once, `cloudId=B` independent. WireMock MCP server, second call within TTL emits zero MCP traffic.
**Rollback:** Flag `STRATUS_MCP_TOOL_CACHE_ENABLED` falls through to existing per‑call construction.

#### B1. Replace `runAgent(...).blockingGet()` with reactive consumption + `LlmEventAggregator` `[L5]`
**Files:** new `stratus/internal/LlmEventAggregator.kt`, `stratus/StratusTestController.kt` (return `Flux<ServerSentEvent>` instead of blocking aggregate).
**What:** `LlmEventAggregator` folds `Flowable<Event>` → `GenerationResult(text, usage, toolCalls)`. Used by both SSE controller path *and* the future insights worker. Worker path uses `.collectList().awaitSingle()` inside `suspend handle()` instead of `blockingGet`.
**Why (lever, quantified):** L5. Without this, the insights worker (B3) caps at thread‑pool size, not coroutine count, defeating the 8 concurrent generations / pod SLO. Also frees Tomcat threads on test endpoints.
**Order deps:** None.
**Risk / blast:** Medium — SSE response shape change is user‑visible for `/stratus/test/*` (already gated as dev‑only). User‑facing `/api/v1/rovo/insights/*` untouched.
**Test plan:** `LlmEventAggregatorTest` with canned event flowables (partial chunks, tool calls, final response); IT against test endpoint.
**Rollback:** `STRATUS_REACTIVE_PIPELINE_ENABLED` flag; old `.blockingGet()` retained for one release.

#### B2. Insights handler — Phase A: wire AI Gateway end‑to‑end with canned response `[L1]`
**Files:** `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`, `featuregate/AiFeatureGates.kt` (new gates).
**What:** Replace stub log line with: (1) `featureService.checkGate(ROVO_INSIGHTS_HANDLER_ENABLED)` — default off, off path = current stub; (2) build trivial "ping" `LlmAgent` (`instruction="reply with the literal token OK"`, no tools); (3) execute via the new reactive pipeline (B1); (4) write a canned `RovoInsightsFetchResponse(count=0, summary="(stub)", insightGroups=[])` to `ProactiveAiCache` keyed `insights:{cloudId}:{accountId}` with 24 h TTL; (5) tag idempotency key (A2) `insights-gen:{cloudId}:{accountId}:{floor(now/30s)}` so burst clicks within 30 s dedup.
**Why (lever, quantified):** L1. Proves SQS → handler → AI Gateway → cache wire end‑to‑end with ~zero LLM cost. Validates A1+A2+B0+B1 in production. Step toward the biggest single OKR contributor.
**Order deps:** A1 (cache), A2 (idempotency), B0 (tool cache infra even if no tools used), B1 (reactive pipeline).
**Risk / blast:** Low. Real prompt not yet wired. Flag‑off everywhere by default; flag‑on path is one trivial AI Gateway round trip + 1 Redis write.
**Test plan:** Unit — handler with mocked `AIGatewayService` returning canned `Flowable<Event>`, assert cache `put` with right key + TTL. IT — full SQS → handler → in‑memory Redis path.
**Rollback:** `ROVO_INSIGHTS_HANDLER_ENABLED=false` → reverts to stub‑log‑and‑ack.

#### B3. Insights handler — Phase B: real prompt, single insight type first `[L1, L3]`
**Files:** new `feature/rovoinsights/system/RovoInsightsPromptBuilder.kt`, `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`, `stratus/internal/AIGatewayServiceImpl.kt` (prompt‑caching headers).
**What:** Port the real prompt for **one** `InsightType` first (e.g. `FOLLOW_UP`) from convo‑ai‑platform. Wire MCP tools via `B0.getToolsAsync`. **Add `cache_control` headers on the `requestWrapperCustomizer`** (`AIGatewayServiceImpl.kt:98-109`) — system prompt is the cached prefix, per‑tenant context is the cache‑miss tail. **Marked as a hypothesis: verify `Unified` SDK accepts these headers; if not, file a ticket against `ai-gateway` SDK team and proceed without the prompt cache for now.** Per‑attempt retry honors `RovoInsightsPromptConfig.maxAttempts`. Gated by `ROVO_INSIGHTS_HANDLER_REAL_PROMPT_ENABLED` (default off; off path = B2 ping).
**Why (lever, quantified):** L1, L3. Ports the real LLM call for one insight type — validates the full quality bar before fanning out. Prompt caching, if supported, cuts ~50–70 % of input tokens after warmup → directly affordable at 1.5 M.
**Order deps:** B2.
**Risk / blast:** High (this is real generation). Mitigations: per‑`InsightType` gate (`ROVO_INSIGHTS_TYPE_FOLLOW_UP_ENABLED`) so only one type ramps; Hello → 1 % → 10 % → 100 % over 2 weeks; cache write only on success.
**Test plan:** Snapshot test on prompt (lock drift); WireMock AI Gateway with canned response, assert handler aggregates correctly; staging load test 8 concurrent × 60 min → assert p95 < 30 s, success ≥ 95 %; 100‑sample‑tenant cost dry‑run.
**Rollback:** `ROVO_INSIGHTS_HANDLER_REAL_PROMPT_ENABLED=false` → B2 ping. Per‑type flag for surgical disable.

#### B4. Insights handler — Phase C: parallel fan‑out across all insight types + result transformer `[L1]`
**Files:** `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`, new `feature/rovoinsights/system/RovoInsightsResultTransformer.kt`.
**What:** Iterate the 6 `InsightType`s with structured concurrency: `coroutineScope { types.map { async { generate(it) } }.awaitAll() }` bounded by per‑task `Semaphore(3)`. Failure of one InsightType does not fail the whole task; partial results stored. Transformer parses raw LLM JSON → `RovoInsightsGroup` / `RovoInsight`. **Strict parse with fallback:** malformed insight → drop the single insight, keep the group, emit `proactive-ai.insights.parse.error`. Cache value JSON‑encodes `RovoInsightsFetchResponse` directly (no intermediate type). **Cache key includes schema version: `insights:v{DATA_SCHEMA_VERSION}:{cloudId}:{accountId}`** — bumping `DATA_SCHEMA_VERSION` ([RovoInsightsFetchResponse.kt:75](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/fetch/RovoInsightsFetchResponse.kt#L75)) auto‑invalidates without manual purge.
**Why (lever, quantified):** L1. Every successful invocation now counts toward 1.5 M as soon as B5 lands. Parallel fan‑out keeps total per‑task latency ~= max(sub‑task) instead of sum.
**Order deps:** B3.
**Risk / blast:** Medium. Per‑`InsightType` flag from B3 gives surgical disable.
**Test plan:** 30 fixture LLM outputs (golden + 10 malformed); IT — handler → transformer → Redis → manual deserialize, assert byte‑equal `RovoInsightsFetchResponse`.
**Rollback:** Flag `ROVO_INSIGHTS_PARALLEL_FANOUT_ENABLED` → revert to B3 single‑type sequential.

#### B5. `/status` + `/fetch` — read from cache, preserve current behavior when flag off `[L1, L4]`
**Files:** `feature/rovoinsights/api/RovoInsightsController.kt`.
**What:** `/status` reads `ProactiveAiCache.get(insights:v{N}:{cloudId}:{accountId})` → `insightsAvailable = (key present)`. If absent and (`request.forceCacheMiss == true` OR `featureService.checkGate(ROVO_INSIGHTS_AUTO_GENERATE_ON_STATUS)`) → `asyncTaskService.submit(RovoInsightsGenerationTask)` (idempotent via A2). `/fetch` reads same key → returns persisted `RovoInsightsFetchResponse`; on miss → existing empty shape (no schema change). Gated by `ROVO_INSIGHTS_CACHE_READ_ENABLED` — when off, identical to current stub responses (snapshot test verifies byte equality). `forceCacheMiss` rate‑limited at 1 / user / 5 min via Redis `setIfAbsent` to prevent abuse.
**Why (lever, quantified):** L1, L4. User‑visible activation: `/status` becomes a sub‑ms Redis GET, meeting the < 100 ms poll SLO trivially. `/fetch` is a single Redis GET on hit. Once on, every successful insights view is one OKR invocation.
**Order deps:** B4, A2.
**Risk / blast:** **Highest user‑visible PR in the plan.** Mitigations: default flag off (snapshot test enforces byte equality vs today); ramp Hello → 1 % → 10 % → 100 % per cohort, gated separately from B4's generation flag so cache must be filled before reads flip on.
**Test plan:** E2E IT — POST `/status` (with auto‑generate gate on) → drain SQS via test consumer → re‑POST `/status` → assert `insightsAvailable=true` → `/fetch` → assert non‑empty. Compatibility — flag off, response bodies byte‑identical to today.
**Rollback:** `ROVO_INSIGHTS_CACHE_READ_ENABLED=false` → identical to today. Cache not deleted (no data loss).

#### B6. Nudge real throttle (TAP traits + GASv3) — default off per type `[L2, L4]`
**Files:** new `feature/nudge/internal/NudgeThrottleService.kt`, `feature/nudge/api/rest/NudgeThrottleController.kt`, `featuregate/AiFeatureGates.kt`.
**What:** Service evaluates per‑`(user, NudgeType)` Redis sliding‑window counter (cap from `getIntConfigValue(NUDGE_TYPE_<X>_DAILY_CAP, defaultValue=Int.MAX_VALUE)` — **default = behaves identically to today**); TAP fatigue trait fetch (caffeine 5 min TTL, async refresh, 20 ms hard timeout, fail‑open); GASv3 recent‑signal lookup (caffeine 5 min, fail‑open). Output: `NudgeThrottleResponse(score, throttled)`. **Per‑`NudgeType` Statsig gate** controls whether the new service runs at all — when off, controller returns the existing `(score=10, throttled=false)`. Master kill‑switch `NUDGE_THROTTLE_KILL_SWITCH` for one‑flag panic.
**Why (lever, quantified):** L2, L4. Real throttle gates Stage‑2 use‑case launches per the FY26 roadmap. Even all gates flipped on, defaults = no UX regression. Lift comes from PMs being **willing to ramp more proactive surfaces** behind a real throttle. Latency: 1 INCR + 1 EXPIRE pipelined ~1 ms; 20 ms cap on each external dep + cache‑first design keeps p95 < 5 ms in service, well inside the 50 ms SLO.
**Order deps:** A1 (Redis), A5 (FF memoise), A0 (NUDGE_THROTTLE_DECISION metric).
**Risk / blast:** High user‑visible if mis‑configured. Mitigations enumerated above; *also* a `NUDGE_THROTTLE_SHADOW_MODE_ENABLED` flag runs the real logic and emits `NUDGE_THROTTLE_DECISION` tagged `shadow=true` but always returns the legacy response — lets PM observe what *would* be throttled before any ramp.
**Test plan:** Matrix unit tests over (TAP present/absent) × (GASv3 present/absent) × (counter cap reached/not). Microbench → service `evaluate()` p95 < 5 ms with mocked deps. Snapshot test in `NudgeThrottleControllerAcceptanceTest.kt` — flag off → response byte‑identical to today's `(10, false)` for every `NudgeType`.
**Rollback:** Master kill‑switch flag → all types instantly back to `(10, false)`.

#### B7. Per‑tenant LLM budget gate `[L3, L6]`
**Files:** new `feature/rovoinsights/internal/TenantBudgetGuard.kt`, `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`.
**What:** Before LLM invocation in handler, `cache.increment(BUDGET_COUNTER, "insights:{cloudId}:{ymd}", ttl=48h)` and compare against `featureService.getIntConfigValue(INSIGHTS_TENANT_DAILY_CAP, defaultValue=Int.MAX_VALUE)`. Over‑cap → emit `tenant.budget.exceeded` metric, write a "rate‑limited" cache value, ack message (don't bounce through SQS). **Default cap = Int.MAX_VALUE** preserves current behavior.
**Why (lever, quantified):** L3, L6. Protects the AI Gateway quota from a single misbehaving tenant (CI loop, scripted scrape). At 1.5 M / mo target, a single tenant doing 100 K calls in a day = 6.7 % of the entire month's budget burned in a day. Cap to e.g. 1 K / tenant / day still keeps the OKR safe at scale.
**Order deps:** A1, A0, B5.
**Risk / blast:** Low because default = no cap. Becomes a dial PM can turn down per tenant tier.
**Test plan:** Unit — within cap → LLM proceeds; over cap → metric + ack, no LLM call. Integration — inject 1001 messages with cap=1000 → 1000 LLM calls, 1 over‑cap event.
**Rollback:** Set `INSIGHTS_TENANT_DAILY_CAP` to MAX_VALUE.

#### B8 (defer / validate first). Workspace‑scoped insights coalescing `[L3]`
**What:** Per‑(`cloudId`) `setIfAbsent` lock with 90 s TTL — siblings within the window see `inFlight=true` (additive field on response). Only enqueue once, fan out the result to every user's cache key.
**Why (deferred):** Estimated 40–60 % LLM call reduction *only if* insights are truly shareable across users in the same workspace. **Critical caveat: today's `RovoInsightsFetchResponse` is keyed by `(cloudId, accountId)` and the convo‑ai inheritance suggests per‑user personalisation.** Validate first by: (a) reading the convo‑ai‑platform handler being ported, (b) shadow‑mode coalescing for one week — measure how often two users in the same workspace hit `/generate` within 90 s. If ratio > 20 %, ship; if < 5 %, drop.
**Order deps:** B5, A1.
**Risk / blast:** Medium‑high UX (first user pays latency, others wait). Hard cap 35 s sibling wait; fallback if generation slow.
**Test plan / rollback:** Standard flag‑gated ramp.

---

## 5. Cross‑cutting concerns (ride along with the relevant PR)

| Concern | Where | Why |
|---|---|---|
| **Add Redis probe to `/deepcheck`** | A1 | Without it, prod won't roll back on Redis outage. |
| **Add `VisibilityExtendingSQSQueueConsumerTest`** | A3 | Closes the explicit test gap from criticality‑dashboard §4. |
| **Add `RovoInsightsControllerTest` (unit)** | B5 | Closes [criticality-dashboard §4.1](_dev/proactive-ai-platform/codebase_understanding/overviews/03-criticality-dashboard.rst#L240) gap. |
| **Add `RequestAttributesCoroutineContextTest` + `InstrumentedDispatcherTest`** | A5 | Closes [§4.3](_dev/proactive-ai-platform/codebase_understanding/overviews/03-criticality-dashboard.rst#L266) — utility/threading is P1 blast with 0 tests. |
| **Add `AIGatewayServiceImplTest` + `IntegrationServiceToolProviderTest`** | B0/B1 | Closes [§4.4](_dev/proactive-ai-platform/codebase_understanding/overviews/03-criticality-dashboard.rst#L279) — stratus is P0 blast with 0 unit tests. |

---

## 6. Sequencing — recommended merge order

```
Week 1   A0 (metrics)      ───┬─────────────────────────────────────────────────────────────
Week 1   A5 (FF memoise)   ───┤      ⌐ in parallel with A0; small + independent
Week 1   B0 (MCP cache)    ───┤      ⌐ in parallel; pure local Stratus win
                              │
Week 2   A1 (Redis client) ───┤
Week 2   A3 (vis. heartbeat) ─┤
                              │
Week 3   A2 (idempotency)  ───┤
Week 3   B1 (reactive Stratus) ┤
                              │
Week 4   A4 (error class)  ───┤
Week 4   B2 (handler ping) ───┤
                              │
Week 5   A6 (timeout + queue) ┤  ⌐ HIGH‑attention; SRE pair
Week 5   B3 (real prompt, 1 type) ─ behind flag; Hello rampStart
                              │
Week 6   B4 (parallel fan‑out)
Week 6   B7 (budget gate)
                              │
Week 7   B5 (cache reads)  ───┤  ⌐ user‑visible flip; snapshot tests must pass
Week 7   B6 (nudge throttle, shadow first)
                              │
Week 8+  B8 (coalescing) — only if shadow‑data justifies
```

If forced to pick the **smallest 3 PRs that move the needle now**: ship **A0 + A5 + B0** in week one. Pure additions, no blast risk, immediately measurable: tighter histograms for SLO tracking, ~5 ms shaved off nudge p95, and 200–500 ms shaved off every (current + future) Stratus call.

---

## 7. Verification — how to know it worked

For each PR, the verification gate before declaring it "done":

1. **Unit + IT pass locally** (`./gradlew test` and `./gradlew intTest`).
2. **Local Nebulae smoke** — start service, hit the affected endpoint(s), verify behavior + metric emission via local Micrometer registry assertion.
3. **Staging canary** — deploy with flag off; enable per‑Hello tenant via `checkHelloOnlyGate` ramp; verify the SignalFx metric you care about for 24 h.
4. **Production ramp** — Hello → 1 % → 10 % → 50 % → 100 % cohort by Statsig, with at least one full business‑day between steps for the user‑visible PRs (B5, B6, B8). Each step gated on:
   - `proactive-ai.invocations.count` not regressing
   - `proactive-ai.insights.e2e.latency` p95 not regressing
   - SQS DLQ depth = 0
   - `ai-gateway.timeout.count` flat
5. **Track A0 dashboards** for the lifetime of the rollout — these are the OKR’s leading indicators.

---

## 8. Critical risks + historical sanity checks

| Risk | Mitigation |
|---|---|
| **Redis outage during ramp** | A1 cache calls fail closed (return `null` + metric, never throw). Worst case = no caching, same as today. |
| **AI Gateway timeout drop (10 min → 60 s) breaks a slow tenant** | Ship as separate commit inside A6; set behind a config var; watch `ai-gateway.timeout.count` for 1 week. Per dev‑history, no prior PR has constrained this — we're tightening, not undoing. |
| **`:done` marker writes for permanent errors silently drop work if classifier wrong** | A4 ramps slowly with `platform.error.classification.enabled` flag; classifier defaults unknown → Transient. |
| **Nudge throttle introduces UX regression** | B6 default per‑type flag off; defaults for cap = `Int.MAX_VALUE`; shadow mode runs the logic without applying. Snapshot test pins current behavior for flag‑off. |
| **B5 `/fetch` returns different shape than today** | Snapshot test in `RovoInsightsControllerIT.kt` enforces byte equality for flag‑off path; flag‑on path constrained to existing schema (no new required fields, no removed fields). |
| **Coalescing (B8) wrongly assumed insights are workspace‑scoped** | Explicitly deferred until shadow data validates. |
| **Prompt caching headers not supported by Stratus SDK** | B3 marks as a hypothesis; if SDK doesn't accept the headers, file a ticket and ship without — the rest of B3 still works. |

**Historical check:** I read `git log` (PRs #65 → #111) and the codebase docs. No prior PR removed Redis, async‑task idempotency, error classification, business metrics, or feature‑flag memoization. The cache infra was added in PR #96 and the client wiring was simply never done. Visibility‑extension was added in PR #103 and only its happy path was implemented. This plan extends, not undoes.

---

## 9. Innovative options (out of scope unless we want to go bigger)

| Idea | Why interesting | Why deferred |
|---|---|---|
| **Pre‑warm insights for top N active users per tenant** during off‑peak | Makes p95 fetch latency ≈ 1 ms (always cache hit). Could move OKR by another ~30 % if click rate matches predictions. | Needs cohort definition + new scheduled SQS publisher; 4–6 PR effort. Park until B5 shows steady state. |
| **Per‑experience model routing (Gemini → Anthropic on outage)** | Eliminates whole‑outage class of incidents. | Requires `Unified` SDK to expose multi‑model — owner is AI Gateway team, not us. |
| **Streaming `/fetch` (SSE)** | Time‑to‑first‑insight drops from full‑bundle latency to first‑token. | Frontend coordination; user said "no user‑facing behavior change" — would need explicit alignment with AIX. |
| **Per‑tenant token budget surfaced in product UI** | Useful for cost transparency + upsell. | Out of platform scope; product‑led decision. |

---

## 10. Critical files (for the implementer)

Platform foundation:
- [`build.gradle.kts`](_dev/proactive-ai-platform/build.gradle.kts) — A1
- [`service-descriptor.sd.yml`](_dev/proactive-ai-platform/service-descriptor.sd.yml) — A6
- [`src/main/resources/application.yml`](_dev/proactive-ai-platform/src/main/resources/application.yml) — A0, A1, A6
- [`config/WebMvcConfiguration.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/config/WebMvcConfiguration.kt) — A3, A6
- [`task/internal/AsyncTaskServiceImpl.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/task/internal/AsyncTaskServiceImpl.kt) — A2
- [`task/AsyncTaskDispatcher.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/task/AsyncTaskDispatcher.kt) — A2, A4
- [`task/internal/VisibilityExtendingSQSQueueConsumer.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/task/internal/VisibilityExtendingSQSQueueConsumer.kt) — A3
- [`service/metric/MetricKey.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/service/metric/MetricKey.kt) — A0
- [`featuregate/internal/FeatureServiceImpl.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/featuregate/internal/FeatureServiceImpl.kt) — A5
- [`featuregate/internal/FeatureFlagContextServiceImpl.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/featuregate/internal/FeatureFlagContextServiceImpl.kt) — A5

Feature / LLM:
- [`feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt) — B2, B3, B4, B7
- [`feature/rovoinsights/api/RovoInsightsController.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/RovoInsightsController.kt) — B5
- [`feature/rovoinsights/api/fetch/RovoInsightsFetchResponse.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/fetch/RovoInsightsFetchResponse.kt) — referenced by B4 schema versioning
- [`stratus/IntegrationServiceToolProvider.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/stratus/IntegrationServiceToolProvider.kt) — B0
- [`stratus/internal/AIGatewayServiceImpl.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/stratus/internal/AIGatewayServiceImpl.kt) — B1, B3
- [`stratus/StratusTestController.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/stratus/StratusTestController.kt) — B1
- [`feature/nudge/api/rest/NudgeThrottleController.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/feature/nudge/api/rest/NudgeThrottleController.kt) — B6
- [`featuregate/AiFeatureGates.kt`](_dev/proactive-ai-platform/src/main/kotlin/io/atlassian/micros/proactiveai/featuregate/AiFeatureGates.kt) — B2/B3/B4/B5/B6/B7 (new gates)
