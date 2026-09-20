# B-Reliability+ — Reliability gaps NOT covered by v7's R-series

> Part of [BOOST Plan v1](../BOOST_PLAN_v1.md). 6 items.
> **Goal anchor:** Silent-bug elimination + 99.85% chat SLO + Trust pillar.

---

## S1 — Fire-and-forget task DLQ (async memory ingest) 🔴 TOP-5 ITEM

**File:** `modules/foundation/utilities/utilities-impl/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/ApplicationCoroutineScope.kt:20-21,34-40,51-53`

**Problem:** `ApplicationCoroutineScope.launchFireAndForget()` captures async memory-ingestion tasks (e.g., conversation memory writes) with only a `CoroutineExceptionHandler` that logs a warning. On pod eviction or OOM, the task silently dies. **No retry, no DLQ, no dead-letter tracking** — the user's memory context is permanently lost.

**Code evidence:**
```kotlin
val exceptionHandler = CoroutineExceptionHandler { _, throwable ->
    log.warnWithContext(
        "Fire-and-forget task failed",
        mapOf("exception_type" to throwable.javaClass.simpleName),
        throwable,
    )
}
// No metrics. No DLQ. No async retry.
```

**Failure mode prevented:** Silent loss of user conversation memory on pod eviction, OOM, or any unhandled exception in the fire-and-forget block. Users notice "the AI doesn't remember what I told it last week" and lose trust.

**Effort:** M (3-4 days)
**Impact:** **0 silent memory-loss events** (categorical safety win) + first-time observability of memory-ingest failures
**Approach:**
1. Wrap `launchFireAndForget` with a try/catch that emits to a SQS DLQ topic on exception (with original task payload)
2. Add `convoai.fire_and_forget.dlq.depth` gauge metric
3. Add `convoai.fire_and_forget.failed{task_type}` counter
4. SQS handler replays from DLQ with exponential backoff
5. (Phase 2) Add `task_type` enum to `launchFireAndForget` so DLQ knows how to replay

**Risk:** Med — SQS DLQ coordination required; replay-handler must be idempotent.

**Acceptance:** DLQ depth gauge live ≥7 days with baseline; chaos drill (kill pod mid-ingest) verifies replay works; 0 silent losses in soak test.

**FY26 goal:** Reliability + Trust pillar.

---

## S2 — Concurrent-conversation saturation gauge + load-shed 🔴 TOP-10 ITEM

**File:** `modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/RovoChatService.kt:206`

**Problem:** `AtomicInteger(0) concurrentConversations` tracks in-flight chats but has **no max threshold, no alert, and no queueing backpressure**. Under thundering-herd load, the service accepts unlimited concurrent streams, exhausts thread pools (Dispatcher.IO), and causes latency cascade. No metric to detect saturation.

**Code evidence:**
```kotlin
private val concurrentConversations = AtomicInteger(0)
// Incremented on chatStream entry, decremented on exit.
// No max(), no gauge metric, no backpressure.
```

**Failure mode prevented:** Tail-latency cascade under load spike. T0a (Spring async pool 64/256) raises capacity but does NOT add load-shedding; if traffic exceeds 256 concurrent, the request queue grows unboundedly.

**Effort:** S (2-3 days)
**Impact:** Prevents tail-latency cascade; safer at peak load; first-time visibility into concurrency saturation
**Approach:**
1. **Phase 1 (metric-only):** Add `convoai.rovo_chat.concurrent_conversations` gauge metric
2. **Phase 2 (load-shed):** Add configurable threshold via `ROVO_CHAT_MAX_CONCURRENT` flag (default = T0a's 256)
3. **Phase 3 (graceful):** When threshold hit, return 429 with `Retry-After` header (don't reject silently)
4. Add `convoai.rovo_chat.load_shed_count` counter

**Risk:** Low — metric-only first; load-shed gated behind flag.

**Acceptance:** Phase 1 metric live ≥7 days; Phase 2 threshold tuned via M7 saturation panel; Phase 3 load-shed activates only above 90% capacity.

**Compounds with:** T0a (v7 + my open PR #29110) — T0a raises ceiling, S2 adds the safety valve.

---

## S3 — MDC context propagation on async task boundaries

**File:** `modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/executors/RovoChatAsyncTaskLauncher.kt:166-168`

**Problem:** `launchPreWorkflowTasks()` captures OTel context via `Context.current()` but uses `scope.launch()` without explicit MDC propagation. Tasks that log errors **lose tenant/user/session context** — debugging is impossible. Distributed traces break across pre/post workflow boundaries.

**Code evidence:**
```kotlin
val otelContext = Context.current()
// Captured for OTel only. MDC (tenant_id, user_id, session_id) not explicitly propagated.
// Child coroutines inherit requestScope, but MDC is thread-local and dispatcher-dependent.
```

**Failure mode prevented:** Logs from async pre/post-workflow tasks lack tenant/user attribution → impossible to correlate during incident response.

**Effort:** S-M (3-5 days)
**Impact:** Better incident MTTR (faster log correlation); end-to-end traces work
**Approach:**
1. Create `withMdcContext { ... }` extension that captures + restores MDC across coroutine boundaries
2. Wrap all `scope.launch { ... }` in `RovoChatAsyncTaskLauncher` with this extension
3. Add `@WithSpan` annotation on pre/post-workflow boundaries with tenant/user/session attributes
4. Add a unit test that asserts MDC keys present on log events from launched tasks

**Risk:** Very low — additive; no behavior change.

**Acceptance:** All log events from `launchPreWorkflowTasks` / `launchPostWorkflowTasks` carry tenant_id + user_id + session_id; OTel spans contain matching attributes.

**Compounds with:** R-6E structured cancellation (v7) — both improve coroutine context discipline.

---

## S4 — Streaming-buffer depth gauge + slow-client timeout policy

**File:** `modules/platform/base/base-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/base/streaming/HttpRequestStreamingWriter.kt:136,145,212-240`

**Problem:** T1 (my open PR #29109) bounds `Channel.UNLIMITED` to 1024 capacity, but **no depth gauge, no slow-client timeout policy.** A single slow client can hold a bounded buffer for an entire stream lifetime, defeating the bound's intent.

**Effort:** S (3-4 days)
**Impact:** Earlier slow-client detection; alerts on stream stalls
**Approach:**
1. Add `convoai.streaming_writer.buffer_depth{capacity_bucket}` gauge (sampled per chunk emit)
2. Add `convoai.streaming_writer.slow_client_count` counter (incremented when buffer ≥ 80% capacity for ≥1 second)
3. Add per-stream timeout: if buffer is full for ≥5 seconds, close the stream with `STREAM_CLIENT_TOO_SLOW` error
4. Add `convoai.streaming_writer.client_timeout_count` counter

**Risk:** Low — metric-only initially; timeout policy gated.

**Acceptance:** Buffer-depth p95 < 50% under normal load; slow-client counter baselined; timeout policy validated with 1KB/sec throttled test client.

**Compounds with:** T1 (#29109) — T1 bounds capacity, S4 adds the visibility + slow-client policy.

---

## S5 — Idempotency keys for post-workflow mutations 🔴 TOP-6 ITEM

**File:** `modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/executors/RovoChatAsyncTaskLauncher.kt:1088-1101`

**Problem:** `launchPostWorkflowTasks()` (e.g., user message storage, memory ingest) lacks idempotency keys. **If the handler is retried (queue replay or network timeout), duplicate messages / memory entries are created.** No deduplication across attempts.

**Code evidence:**
```kotlin
suspend fun launchPostWorkflowTasks(
    scope: CoroutineScope,
    // ... params ...
): PostWorkflowInputResults {
    val userMessageTask = if (isChatStorageEnabled) {
        // Stores message, but no idempotency key passed to storage layer
```

**Failure mode prevented:** Duplicate user messages in conversation history after queue replay or retry. Symptom: "I see my message twice in the chat after a glitch."

**Effort:** M (1-2 weeks)
**Impact:** **0 duplicate post-workflow mutations** + clear ownership of write-side idempotency
**Approach:**
1. Generate idempotency key from `(conversationId, requestId, taskType, stepId)` at launch
2. Pass key to storage layer (extend `MessageStore` interface with `idempotencyKey` parameter)
3. Storage layer uses DynamoDB conditional put with 24h TTL
4. On duplicate detection, return cached result + emit `convoai.post_workflow.duplicate_detected{task_type}` counter

**Risk:** Med — storage layer coordination; idempotency cache must be TTL'd.

**Acceptance:** 0 duplicate messages in soak test (force 100 retries); duplicate-detected counter baselined; 24h TTL prevents unbounded cache growth.

**Compounds with:** R-6A tool idempotency (v7) — extends the same pattern from tool execution to post-workflow mutations.

---

## S6 — Health-readiness probe reflects orchestrator + LLM downstream availability

**Location:** Implicit across `modules/product/rovo/rovo-impl/.../RovoChatService.kt` (chatStream / chatStreamRovo declare no explicit health dependencies)

**Problem:** The `/health/ready` probe does NOT verify that the agent orchestrator, LLM router, or embedding service are available. The service marks itself ready but fails immediately on first chatStream request. **Kubernetes routes traffic to a "healthy" pod that returns errors** → cascading timeouts.

**Effort:** S-M (3-5 days)
**Impact:** Reduced customer error rate during downstream degradation; pod-ready-state thrash eliminated
**Approach:**
1. Define `HealthChecker` interface for downstream dependencies (orchestrator, LLM router, knowledge service)
2. Cache health-check result for 30 seconds (avoid cascading probe checks)
3. Wire `/health/ready` to fail if ≥2 critical downstreams are unavailable
4. **Distinguish from liveness:** liveness must remain stable to avoid restart loops

**Risk:** Low — readiness ≠ liveness; TTL prevents probe-storm.

**Acceptance:** During simulated downstream outage, pod is marked NotReady within 30s; traffic drains; restart count unchanged.

**FY26 goal:** Reliability + 99.85% SLO.
