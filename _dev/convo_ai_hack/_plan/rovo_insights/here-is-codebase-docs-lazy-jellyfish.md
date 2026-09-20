# Rovo Insights — Performance, Throughput & Stability Rework Plan

**Audit date:** 2026-05-03 · **Source path:** `_dev/conversational-ai-platform/modules/product/rovo/{rovo-api, rovo-impl, rovo-extras-impl}` · **Audit method:** 3 parallel Explore agents (hot-path, cache/resilience, LLM efficiency) + 2 parallel Plan agents (implementation, verification) + first-hand source verification of every claim cited below.

---

## 1. Context — why this work is needed

User feedback identifies two dominant pain points with Rovo Insights:

1. **Too slow.** End-to-end generation is 30–60 s p50, 60–120+ s p95. The product is async-fan-out (6 parallel LLM calls), but architectural choices serialize avoidable work post-LLM and waste streaming bandwidth.
2. **Unstable.** Users occasionally see "generating…" indefinitely, miss "ready" notifications, or get partial/zero results. Causes are concrete and quantifiable, not "LLM flakiness."

The audit examined 16 files in detail and verified ~30 findings with file:line evidence. Roughly **two-thirds of the latency cost is fixable in code without LLM-side changes**, and **stability hazards are concentrated in three specific code sites** (handler entry, notification service, cache-key salt fetch).

**Headline measurable goals**

| Metric                                          | Today (estimate) | Target post-rework |
| ----------------------------------------------- | ---------------: | ------------------: |
| `ROVO_INSIGHTS_GENERATION_LATENCY` p50          |          30–50 s |             15–25 s |
| `ROVO_INSIGHTS_GENERATION_LATENCY` p95          |         60–120 s |             25–40 s |
| `ROVO_INSIGHTS_GENERATION_LATENCY` p99          |       180–300+ s |              < 60 s |
| First-insight TTFB (NEW metric)                 |       same as p95 |               < 8 s |
| Stuck-generating (orphan task) rate             |        unmeasured |              < 0.5 % |
| Notification miss rate                          |        unmeasured |              < 0.1 % |
| LLM input tokens / generation                   | ~36 000 (6×6 000) |              ~9–12 k |
| Daily LLM input-token cost / 100 k DAU          |         baseline X |       ~0.28 X (–72 %) |
| SQS duplicate generations per task              |  occasional (no guard) |                    0 |

The plan is to reach the targets above through **3 tiers of code change** plus **observability and rollout discipline** that lets us prove improvement and revert any single change with a flag flip.

---

## 2. Verified findings (with file:line evidence)

Every finding was verified by reading the actual source file. Each lists the concrete code site, what's wrong, and quantified impact.

### Tier 1 — Latency on the hot path

**[L1] Person hydration is N+1 and runs serially after the LLM** — *p95 cost: 5–10 s*
- [`RovoInsightsServiceImpl.kt:322-334`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L322-L334) `hydratePersonReferences` is sequential `mapNotNull`.
- Called per-insight inside the 6-case `when` block at lines 396, 406, 416, 426, 436, 446 — also sequential `.map`.
- Each person → [`RovoInsightsServiceImpl.kt:292`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L292) `userService.getUserProfile(user, aaid)` — single-user remote call.
- No deduplication: same person referenced by 5 insights = 5 lookups.
- Hydration runs *after* `coroutineScope { ... awaitAll() }` finishes (line 482) → cost is added to wall-clock, not overlapped.
- `UserService` has [`getUserNames(List<String>)`](_dev/conversational-ai-platform/modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/user/UserService.kt#L45-L48) (names only) but **no batched `getUserProfiles` API** for full profile + avatar.
- Estimate: ≈ 6 types × ≈ 3 insights × ≈ 3 people = **~54 sequential remote calls** per generation.

**[L2] Per-call timeout + structured concurrency cancellation kills siblings** — *worst case: 12 min per type, all-or-nothing*
- [`RovoInsightsServiceImpl.kt:152`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L152) `searcher.waitUntilFound(GENERATION_TIMEOUT_MILLIS)` — uses [`SearchingStreamingWriter.kt:23-26`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/SearchingStreamingWriter.kt#L23-L26) `withTimeout(...)` → throws `TimeoutCancellationException` per-call.
- `GENERATION_TIMEOUT_MILLIS = 240_000` (4 min) at line 570.
- Fan-out at line 474 uses `coroutineScope { ... async { ... }.awaitAll() }` → **structured concurrency**: one async failure cancels all siblings.
- `generateInsight` line 275–276 catches `CancellationException` and **rethrows** — so timeout in any one type cancels the whole 6-way batch.
- Combined with retry × 3, **single-type worst case = 12 min**, and that 12 min discards the work of 5 healthy siblings.

**[L3] Retry has no backoff and no jitter** — *up to 12 s wasted on retry path*
- [`Retryable.kt:13-29`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/Retryable.kt#L13-L29): `attempt += 1` immediately, no `delay()`.
- `maxAttempts = 3` default, called from line 234 of service impl.
- Three immediate retries × 240 s timeout = **12 min worst case before giving up**.

**[L4] Statsig hydration flag re-evaluated per person** — *up to 1.25–2.5 s*
- [`RovoInsightsServiceImpl.kt:327-333`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L327-L333): `rolloutService.controlledByFullContext(AIX_ROVO_INSIGHTS_USER_HYDRATION_ENABLED)` is **inside** the `mapNotNull` over people. With ~50 people referenced per generation, that is ~50 flag evaluations.

**[L5] Filter+map two-pass over insights** — *20–50 ms*
- [`RovoInsightsServiceImpl.kt:377-391`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L377-L391) — filter (with side-effect logging) followed by 6-case map. Trivially collapsible to `mapNotNull`.

**[L6] Conversation created per LLM call (and per retry)** — *0.6–1.8 s wasted*
- [`RovoInsightsServiceImpl.kt:117`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L117) `createConversationId(...)` is inside `evaluateWithRovoChat`, called per type, per retry. With `storeMessage = false` (line 137), the conversation is ephemeral. **6–18 conversation-create remote calls per generation** could collapse to 1.

**[L7] Hot-path log emits full prompt** — *50–200 ms blocking I/O + Splunk cost*
- [`RovoInsightsServiceImpl.kt:168-185`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L168-L185) logs entire `prompt` string (~20 KB) per type → ~120 KB log volume per generation.

### Tier 2 — LLM efficiency

**[E1] 118 KB of prompt content with massive duplication** — *targets ~70 % input-token reduction; ~10–18 s wall-clock if upstream supports prompt caching*
- Verified byte counts: `company-insights.pebble` 17 636 B, `emerging-with-your-team.pebble` 18 074 B, `follow-up-insights.pebble` 21 171 B, `meeting-insights.pebble` 22 092 B, `recognition-insights.pebble` 19 464 B, `your-trending-work.pebble` 20 070 B → **118 507 B total**.
- [`Common.kt:32-44`, `46-77`, `79-116`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/llmresponse/Common.kt#L32-L116) — `responseStructureInstructionsPrompt`, `resourceSourcesInstructionsPrompt`, `typeExamples` are concatenated into `InsightPromptRegistry` for **each of 6 types**.
- Pebble templates also duplicate role/scoring/validation prose (verified by spot-check of `follow-up-insights.pebble` lines 1–80).
- Per call ≈ 24 KB input ≈ **~6 000 input tokens × 6 calls = ~36 000 tokens per generation**.

**[E2] Streaming bandwidth is wasted; result is delivered atomically** — *atomic 6-way wait blocks user until slowest type finishes*
- [`SearchingStreamingWriter.kt:13-34`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/SearchingStreamingWriter.kt#L13-L34) only completes its `Deferred` when a `RovoChatV1FinalResponseMessageEnvelope` arrives — all intermediate chunks are discarded.
- Per-call wall-clock = full LLM response time.
- Wall-clock for the whole user wait = `max(p95 of 6 types)`. One slow type drags every user.
- The user sees nothing until **all 6 finish AND hydration AND ADF render AND cache write AND notification dispatch all complete**.

**[E3] Structured-output enforcement supported but disabled** — *parse-failure retries waste 30 s–4 min each*
- [`RovoChatServiceApi.kt:30`](_dev/conversational-ai-platform/modules/product/rovo/rovo-api/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/RovoChatServiceApi.kt#L30) exposes `structuredOutputEnabled: Boolean = false`. Insights does **not** pass `true` (call site lines 127–150 of service impl). LLM is instructed in prose only ("Return ONLY a raw JSON array…", `Common.kt:32-44`).
- `parseRovoChatResponse` ([line 210-217](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L210-L217)) is all-or-nothing — any malformed JSON triggers full retry. No partial recovery.

**[E4] All 6 types share one agent / model**
- Hardcoded `recipientAgentNamedId = "ai_mate_agent"` at line 134. No per-type model tier — "Recognition" runs on the same expensive model as "Meeting Insights".

### Tier 3 — Stability

**[S1] No idempotency guard in SQS handler** — *duplicate generations on at-least-once delivery*
- [`RovoInsightsGenerationTaskHandler.kt:50-79`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsGenerationTaskHandler.kt#L50-L79) unconditionally calls `generateInsights(...)` on every dequeue.
- SQS visibility timeout (typically 5 min) < worst-case handler runtime (4 min × possibility of retries) → duplicate delivery → second handler overwrites first cache write → wasted LLM cost.

**[S2] Notification swallows errors silently** — *user cached but never notified*
- [`RovoInsightsNotificationService.kt:88-98`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsNotificationService.kt#L88-L98) catches `Exception`, logs `warn`, returns normally.
- Plus lines 52–58 silently return when `rovoWorkspaceARI == null`.
- Handler [line 159](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsGenerationTaskHandler.kt#L159) treats this as success → SQS acks → user gets cached results but **no "ready" ping**.

**[S3] Cache salt fetched per cache op** — *thundering-herd risk on salt rotation*
- [`RovoInsightsCacheImpl.kt:74-80`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsCacheImpl.kt#L74-L80) calls Statsig dynamic config inside `buildCacheKey` (line 70) — **every `get()` and `put()`**.
- Operator flips salt → all caches miss simultaneously → thundering-herd LLM fan-out.

**[S4] `forceCacheMiss` has no rate limiting** — *per-user DoS path*
- [`RovoInsightsV1Controller.kt:97`](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/rest/RovoInsightsV1Controller.kt#L97) — `request.forceCacheMiss` short-circuits all checks. One client can spam regenerations indefinitely.

**[S5] Pod kill mid-generation leaves a stuck task entry up to 1 hour**
- Handler `catch` block clears task cache only if a Kotlin exception fires ([line 70](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsGenerationTaskHandler.kt#L70)). Pod kill (SIGKILL/OOM) skips that.
- TaskCache TTL = 1 h ([`RovoInsightsTaskCacheImpl.kt:66`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsTaskCacheImpl.kt#L66)), so user sees "generating…" for up to 1 h.

**[S6] Status endpoint also enqueues** — *not a pure read*
- [`RovoInsightsV1Controller.kt:97-107`](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/rest/RovoInsightsV1Controller.kt#L97-L107) enqueues a job inside the `/status` POST. Status check is a write. The `hasActiveTask` guard prevents stampede, but mixes concerns and complicates rate-limiting.

**[S7] `CACHE_TIMEOUT = Duration.ofDays(1)` triggers daily regen for every active user**
- [`RovoInsightsV1Controller.kt:193`](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/rest/RovoInsightsV1Controller.kt#L193). Cache TTL is 7 d, but the controller treats anything > 1 d as stale and re-enqueues. Every active user pays daily LLM cost regardless of whether their underlying signals changed.

### Findings that turned out to be NON-issues (after reading the code)

| Doc claim                                  | Reality after reading source                                                                                                                                                                                                                                  |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "No distributed cache invalidation"        | `cacheSchemaVersion`, `dataSchemaVersion`, and `cacheSalt` are all in the cache key (`RovoInsightsCacheImpl.kt:67-71`). Schema bumps invalidate cleanly; the operator-driven salt provides ad-hoc invalidation. **Working as designed.** |
| "Pebble template compiled per request"    | `PromptFormatterConfigProviderImpl.kt` enables `cacheActive(true)` — Pebble caches compiled templates. **Not a problem.**                                                                                                                                          |
| "Task cleanup only on success"            | Handler `catch` block at line 70 also calls `clearTaskCache`. Mostly mitigated; only **pod kill / SIGKILL** path leaves orphans (covered by **S5**).                                                                                                                  |

---

## 3. Implementation plan — phased

The plan groups the fixes into **8 deployable bundles (B0–B7)**. Each bundle is independently revertable behind a Statsig flag (with one exception, T3.3, called out below). Critical-path order is `T1.2 → T1.1 → T3.1 → T3.5`; everything else parallelizes.

### B0 · Quick wins — ship today (≤ 1 day total work, zero architectural risk)

| Item                 | File                                                                | Change                                                                                                                                                                                                                                                                                                  |
| -------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **T1.5** Hoist hydration flag | `RovoInsightsServiceImpl.kt:322-334`                               | Resolve `rolloutService.controlledByFullContext(AIX_ROVO_INSIGHTS_USER_HYDRATION_ENABLED).value` once in `generate(…)`; pass the boolean down to a refactored `hydratePersonReferences(…, useFull: Boolean)`. Saves ~50 evaluations/request.                                                                       |
| **T1.4** Filter→`mapNotNull` | `RovoInsightsServiceImpl.kt:377-391`                               | Collapse `filter { … }.map { … }` into one `mapNotNull { itt -> if (errors.isEmpty()) build(itt) else null.also { logFiltered(...) } }`.                                                                                                                                                                |
| **T1.3** Backoff + jitter | `Retryable.kt:13-29`                                              | Make `retryable` `suspend`; add `delay(min(base * 2^(n-1), maxDelayMs) + Random.nextLong(0, base))` between attempts. Defaults `base=500ms`, `max=5000ms`.                                                                                                                                              |
| **L7 · T2.6** Drop full-prompt log | `RovoInsightsServiceImpl.kt:168-185`                               | Replace `"prompt" to prompt` with `"prompt_hash" to prompt.hashCode()`. Gate full-prompt logging behind `ROVO_INSIGHTS_LOG_FULL_PROMPT` (default off).                                                                                                                                                  |
| **T3.4** Rate-limit `forceCacheMiss` | `RovoInsightsV1Controller.kt:97`                                  | Bucket4j-style limiter keyed by `(tenantId, userId)`; default 3/hour. HTTP 429 on excess. Configurable via dynamic config `ROVO_INSIGHTS_FORCE_REFRESH_LIMITS`.                                                                                                                                              |

These ship together behind the umbrella `AIX_ROVO_INSIGHTS_ENABLED` (already in use) — no new flag plumbing, no schema bumps.

### B1 · Cancellation isolation (T1.2) — single largest stability + tail-latency win

**File:** [`RovoInsightsServiceImpl.kt:468-485`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L468-L485)

Replace `coroutineScope { ... async { ... }.awaitAll() }` with `supervisorScope` and wrap each child in `runCatching`:

```kotlin
override suspend fun generate(...): RovoInsightsResponse =
    try {
        val insightResultDetails = supervisorScope {
            availableInsightTypes.map { insightType ->
                async {
                    runCatching {
                        generateInsightForType(tenantContext, user, insightType, rovoInsightsRequest)
                    }.getOrElse { e ->
                        log.warnWithContext("Insight type failed in isolation",
                            mapOf("insight_type" to insightType.value), e)
                        GenerateInsightResultDetails<Insight>(
                            insightType = insightType,
                            generatedAt = Instant.now(clock),
                        ).also { it.error = e }
                    }
                }
            }.awaitAll()
        }
        insightsToRovoInsightsResponse(user, insightResultDetails)
    } catch (e: Exception) { ... }
```

The existing `catch (CancellationException) { throw e }` at [`generateInsight` line 275-276](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L275-L276) **stays** — under `supervisorScope`, peer-induced cancellation cannot occur, so this only fires on legitimate outer cancellation (request abort, pod shutdown).

**Flag:** `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED` (new gate, off → 100 % over 5 days).
**Test additions:** extend `RovoInsightsServiceImplTest.kt` with `single_type_timeout_does_not_cancel_siblings` — currently impossible to write because of `awaitAll` semantics; this change unblocks it.
**Risk:** none — `supervisorScope` is the canonical Kotlin idiom; outer cancellation still propagates correctly.

### B2 · Hydration parallelization + dedup (T1.1) — biggest p95 win

**File:** [`RovoInsightsServiceImpl.kt:322-334, 391-455, 357-466`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L322-L466)

**Approach:** keep hydration in-process; do not ship a new `UserService.getUserProfiles(List<aaid>)` API as part of this change (it requires upstream service work). Instead, dedup + concurrency-bound at the Insights layer.

```kotlin
private suspend fun hydrateAllPersonReferences(
    user: User,
    insightResultDetails: List<GenerateInsightResultDetails<out Insight>>,
    useFullProfileHydration: Boolean,    // hoisted in T1.5
): Map<String, PersonReference?> = coroutineScope {
    val byAaid: Map<String, Person> = insightResultDetails
        .flatMap { it.insights }
        .flatMap { it.people.orEmpty() }
        .associateBy { it.aaid }       // dedup across insights and types
    val sem = Semaphore(maxConcurrency)  // dynamic config; default 16
    byAaid.mapValues { (aaid, person) ->
        async {
            sem.withPermit {
                if (useFullProfileHydration) hydratePersonReference(user, aaid)
                else hydratePersonReferenceLegacy(person)
            }
        }
    }.mapValues { it.value.await() }
}
```

Then refactor [`insightsToRovoInsightsResponse` lines 357–466](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt#L357-L466) to:
1. Accept the precomputed `hydrationMap`.
2. Replace each per-branch call to `hydratePersonReferences(user, itt.people)` with `itt.people?.mapNotNull { hydrationMap[it.aaid] }`.
3. Collapse the 6 near-identical `is FollowUp -> RovoInsight(...)` branches into a single `buildRovoInsight(itt, hydrationMap)` helper.

**Follow-up (separate proposal, not blocking):** add `UserService.getUserProfiles(List<aaid>): Map<String, UserProfile>` to the platform `UserService` interface. The `getUserNames(List<aaid>)` batch already exists ([`UserService.kt:45-48`](_dev/conversational-ai-platform/modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/user/UserService.kt#L45-L48)) — extending it to full profile + avatar is straightforward but cross-team.

**Flag:** `ROVO_INSIGHTS_BATCH_HYDRATION_ENABLED` (new). **Dynamic config:** `ROVO_INSIGHTS_HYDRATION_MAX_CONCURRENCY` (default 16 — tune by Identity-service tolerance).

### B3 · Handler idempotency + wall-clock budget (T3.1 + T3.5)

**File:** [`RovoInsightsGenerationTaskHandler.kt:50-79`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsGenerationTaskHandler.kt#L50-L79) and `RovoInsightsServiceImpl.kt:468-485`.

**T3.1 — idempotency guard** (must add `enqueuedAt: Instant` to `RovoInsightsGenerationTask` envelope; nullable, default `Instant.MIN` for in-flight legacy messages):

```kotlin
flow {
    try {
        val cached = rovoInsightsCache.get(tenantContext, user)
        val enqueuedAt = taskEnvelope.enqueuedAt ?: Instant.MIN
        if (cached != null && cached.generatedAt.isAfter(enqueuedAt)) {
            metricsService.count(MetricKey.ROVO_INSIGHTS_IDEMPOTENCY_SHORT_CIRCUIT)
            clearTaskCache(taskExecutionContext)
            notifyCompletion(...)        // re-attempt ping in case prior handler died before notify
            emit(Result.success(Unit)); return@flow
        }
        // existing flow unchanged
    }
}
```

**T3.5 — wall-clock budget:**

```kotlin
override suspend fun generate(...): RovoInsightsResponse =
    withTimeout(GENERATION_WALL_CLOCK_BUDGET_MILLIS) {  // default 360_000 (6 min)
        // existing supervisorScope (B1)
    }
```

**SQS visibility coordination** — at the enqueue site, set `visibilityTimeout = Duration.ofMinutes(8)` so visibility ≥ wall-clock + 2 min buffer. If the wall-clock fires, `withTimeout` throws → handler `catch` block clears task cache → SQS will redrive after visibility expires → idempotency guard short-circuits cleanly.

**Flags:** `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED`, `ROVO_INSIGHTS_WALL_CLOCK_BUDGET_MS` (dynamic long).

### B4 · Notification reliability (T3.2)

**File:** [`RovoInsightsNotificationService.kt:88-98`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsNotificationService.kt#L88-L98)

Convert swallow-and-log to retry-with-backoff (uses the post-T1.3 `Retryable` with `suspend delay`); after final failure, throw — propagates to handler `catch`, becomes `Result.failure`, SQS redrives. **Requires B3 to ship first** so the redrive doesn't pay double LLM cost.

```kotlin
suspend fun sendInsightsReadyNotification(...) {
    val workspaceAri = tenantContext.getRovoWorkspaceARI()
        ?: throw NotificationConfigException("Rovo workspace ARI unavailable")
    retryable<Unit, RetryableNotificationException>(maxAttempts = 3, baseDelayMs = 500) { _ ->
        try { postOfficeStreamhubEventPublisher.publishPostOfficeMessageTriggerEvent(message) }
        catch (e: TransientPostOfficeException) { throw RetryableNotificationException(e) }
    }
}
```

**Permanent-failure handling:** rely on SQS `maxReceiveCount` → DLQ + ops alert (don't mask in handler). **Flag:** `ROVO_INSIGHTS_STRICT_NOTIFICATION_ENABLED`.

### B5 · Cache salt memoize + stuck-task sweeper (T3.3 + S5)

**T3.3 — salt memoize** (`RovoInsightsCacheImpl.kt:74-80`): wrap `getCacheSalt()` in a Caffeine cache with `expireAfterWrite(60s)`. Trade-off: salt rotation now propagates over up to 60 s instead of instantly — acceptable, and within the existing operational expectation. **No flag** (pure perf optimization, code-only revert).

**S5 — stuck-task sweeper:** new component `RovoInsightsStuckTaskSweeper` running on a `@Scheduled` 2-minute tick. Reads `RovoInsightsTaskCache` for tenants in scope, finds entries older than 10 min with no corresponding fresh data-cache entry, **re-enqueues** the task (idempotency guard from B3 makes this safe). Emits new metric `ROVO_INSIGHTS_STUCK_TASK_DETECTED` / `_RECOVERED`. Two-phase rollout: observe-only (flag off) → active.

**Flag:** `ROVO_INSIGHTS_STUCK_SWEEPER_ENABLED` (off → observe-only → active).

### B6 · LLM-call efficiency (T2.3, T2.4)

**T2.3 — partial JSON recovery** (`RovoInsightsServiceImpl.kt:210-217`):

```kotlin
internal fun <T : Insight> parseRovoChatResponse(response: String, responseType: Class<T>): List<T> {
    val parser = objectMapper.createParser(response)
    val results = mutableListOf<T>()
    var dropped = 0
    parser.use { p ->
        if (p.nextToken() == JsonToken.START_ARRAY) {
            while (p.nextToken() != JsonToken.END_ARRAY) {
                runCatching { results.add(p.readValueAs(responseType)) }
                    .onFailure { dropped++ }
            }
        }
    }
    metricsService.count(MetricKey.ROVO_INSIGHTS_PARTIAL_JSON_PARSE,
        listOf("valid_count" to results.size.toString(), "dropped_count" to dropped.toString()))
    return results
}
```

Retry triggers only when `results.isEmpty()`. **Flag:** `ROVO_INSIGHTS_PARTIAL_JSON_RECOVERY_ENABLED`.

**T2.4 — hoist conversation-create above fan-out** (`RovoInsightsServiceImpl.kt:117`):

```kotlin
override suspend fun generate(...) {
    val sharedConversationId = createConversationId(tenantContext, user)
    supervisorScope { ... generateInsightForType(..., sharedConversationId) ... }
}
```

**Pre-implementation gate:** verify `RovoChatService.chatStream` tolerates concurrent calls on the same `conversationId` with `storeMessage = false`. If not, fall back to one-conv-per-type (still saves the per-retry duplication). **Flag:** `ROVO_INSIGHTS_SHARED_CONVERSATION_ENABLED`. **Bundles with B1** because it touches the same code site.

**T2.3 toggle:** also pass `structuredOutputEnabled = true` at `chatStream` call site (line 127) — supported flag exists at [`RovoChatServiceApi.kt:30`](_dev/conversational-ai-platform/modules/product/rovo/rovo-api/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/RovoChatServiceApi.kt#L30) but is left at default `false`. Gate per-type behind `ROVO_INSIGHTS_STRUCTURED_OUTPUT_ENABLED`.

### B7 · Prompt deduplication for prompt caching (T2.1)

**Three-step refactor:**

1. **Code-level extraction** in [`Common.kt:79-116`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/llmresponse/Common.kt#L79-L116): keep `responseStructureInstructionsPrompt`, `resourceSourcesInstructionsPrompt`, `typeExamples`, but ensure they appear in the **same byte order** at the **head** of every type's final prompt. Do not interpolate user-specific data inside the shared block.
2. **Pebble template refactor** at `modules/product/rovo/rovo-impl/src/main/resources/templates/rovo/insights/v1/`: extract role/persona/scoring/validation prose into 4–5 partials in `_shared_*.pebble`, included via `{% include "_shared_role.pebble" %}`. Reorder all 6 templates to:

   ```
   [SHARED prefix — byte-identical across the 6 calls in one fan-out]
   ---USER CONTEXT---  (same for all 6)
   ---TASK---
   [type-specific 4–6 KB segment]
   ```

3. **Prompt-version flag.** `RovoInsightsPromptConfig.version` already exists. Ship as `v2`. Statsig dynamic config `ROVO_INSIGHTS_PROMPT_VERSION` selects v1/v2. Run side-by-side eval (the existing `Strategy.EVALUATE` pattern) for a week before flipping default.

**Open question that gates this bundle's ceiling:** does the upstream `RovoChatService` route to a model with prompt caching (Anthropic-style)? If yes, the byte-identical prefix gives ~70 % input-token cost reduction. If no, we still get token-cost savings from deduplication but not from cache-read pricing.

**Schema:** bump `RovoInsightsResponse.DATA_SCHEMA_VERSION` (currently 3) to invalidate v1-generated cached entries when v2 promotes to default.

### Deferred (not in this rework)

- **T2.5 per-type model routing:** add `agentNamedId: String` to `RovoInsightsPromptConfig`; route per-type. Needs product input on which types tolerate a cheaper model.
- **T2.2 progressive surfacing:** per-type cache writes + status endpoint reads partials. Smallest viable design described in detail in the implementation-strategy agent output; deferred because it requires frontend coordination and is the largest UX-shape change.
- **S6 endpoint split** (`/status` read vs `/generate` write): coordinated with frontend.
- **`systemPrompt` parameter on `RovoChatServiceApi.chatStream`:** cross-package contract change; separate proposal.

### Dependency graph

```
B0 (quick wins)              ──── independent, ship today
B1 (T1.2 isolation)          ──── ship before B2/B3 (changes fan-out semantics)
B2 (T1.1 hydration)          ──── needs B0 (T1.5 hoisted flag)
B3 (T3.1 idem + T3.5 budget) ──── needs B1 (timeout coord)
B4 (T3.2 strict notify)      ──── needs B3 (idem makes redrive safe) + B0 (T1.3 backoff)
B5 (salt memoize + sweeper)  ──── needs B3 (sweeper relies on idem to re-enqueue safely)
B6 (T2.3 + T2.4)             ──── B6.T2.4 bundles with B1 (same code site)
B7 (T2.1 prompt v2)          ──── independent, longest validation cycle
```

Critical path (sequential): **B0 → B1 → B2 → B3 → B4**. Five bundles. Everything else parallelizes.

---

## 4. Verification & rollout

### 4.1 New telemetry to add (Phase P0, before any flag flip)

| Metric                                              | Type      | Instrument at                                                                | Purpose                                  |
| --------------------------------------------------- | --------- | ---------------------------------------------------------------------------- | ---------------------------------------- |
| `ROVO_INSIGHTS_HYDRATION_LATENCY_MS`                | histogram | new `hydrateAllPersonReferences` (B2)                                        | Quantify L1 fix                          |
| `ROVO_INSIGHTS_HYDRATION_BATCH_SIZE`                | histogram | same                                                                         | Confirm dedup ratio (unique/total people) |
| `ROVO_INSIGHTS_PER_TYPE_FAILURE` (tag insight_type) | counter   | `runCatching` site in B1                                                     | Quantify L2 fix                          |
| `ROVO_INSIGHTS_PER_TYPE_TIMEOUT`                    | counter   | same                                                                         | Distinguish timeout vs other failures    |
| `ROVO_INSIGHTS_RETRY_ATTEMPT` (tag attempt_index)   | counter   | `Retryable.kt`                                                              | Retry distribution                       |
| `ROVO_INSIGHTS_RETRY_BACKOFF_MS`                    | histogram | `Retryable.kt`                                                              | Tune backoff                             |
| `ROVO_INSIGHTS_INPUT_TOKENS_PER_TYPE`               | histogram | `RovoInsightsServiceImpl.kt:168-185` (existing log block)                   | E1 cost validation                       |
| `ROVO_INSIGHTS_PROMPT_CACHE_HIT` / `_MISS`          | counter   | same (post-B7)                                                               | Validate B7 ceiling                      |
| `ROVO_INSIGHTS_TTFB_MS`                             | histogram | first per-type completion (post-T2.2)                                        | Progressive UX (deferred bundle)         |
| `ROVO_INSIGHTS_PARTIAL_JSON_PARSE`                  | counter   | new `parseRovoChatResponse` in B6                                            | Validate B6 fix                          |
| `ROVO_INSIGHTS_IDEMPOTENCY_SHORT_CIRCUIT`           | counter   | handler entry post-B3                                                        | Validate B3 fix                          |
| `ROVO_INSIGHTS_NOTIFICATION_DISPATCH_ERROR`         | counter   | notification service                                                         | Validate B4 fix                          |
| `ROVO_INSIGHTS_STUCK_TASK_DETECTED` / `_RECOVERED`  | counter   | new sweeper                                                                  | Validate S5 fix                          |
| `ROVO_INSIGHTS_FORCE_REFRESH_RATE_LIMITED`          | counter   | controller                                                                   | Validate S4 fix                          |
| `ROVO_INSIGHTS_CACHE_SALT_LOOKUP_LATENCY_MS`        | histogram | `RovoInsightsCacheImpl.kt:74-80` post-B5                                     | Validate B5 perf claim                   |

Existing metrics already in code that we **do not need to add** (just dashboard them):

- `ROVO_INSIGHTS_CACHE_HIT` / `_MISS` (`RovoInsightsCacheImpl.kt:34-42`)
- `ROVO_INSIGHTS_GENERATED` / `_GENERATION_SUCCESS` / `_GENERATION_ERROR` (handler)
- `ROVO_INSIGHTS_JOB_SUBMITTED` / `_JOB_SUBMISSION_ERROR` (service `submitGenerationJob`)
- `ROVO_INSIGHTS_GENERATION_LATENCY` (handler)
- `ROVO_INSIGHTS_PER_TYPE_GENERATION_LATENCY` (service `generateInsightForType`)

### 4.2 Statsig flags

**Existing — reuse:**

| Flag                                              | Use                                                |
| ------------------------------------------------- | -------------------------------------------------- |
| `AiFeatureGate.AIX_ROVO_INSIGHTS_ENABLED`        | Top-level kill switch. Already in use.             |
| `AIX_ROVO_INSIGHTS_USER_HYDRATION_ENABLED`       | Keep, but evaluation hoisted (T1.5). Per-user bucket. |
| `AiFeatureDynamicConfigs.ROVO_INSIGHTS_CACHE_SALT` | Reuse for ad-hoc invalidation if B7 prompt v2 misbehaves. |

**New:** all with `accountId` sticky bucketing.

| Flag                                                  | Type           | Default       | Purpose                                |
| ----------------------------------------------------- | -------------- | ------------- | -------------------------------------- |
| `ROVO_INSIGHTS_PER_TYPE_ISOLATION_ENABLED`            | gate           | off → 100 %    | B1 (T1.2)                              |
| `ROVO_INSIGHTS_BATCH_HYDRATION_ENABLED`               | gate           | off → 100 %    | B2 (T1.1)                              |
| `ROVO_INSIGHTS_HYDRATION_MAX_CONCURRENCY`             | dynamic int    | 16            | B2 — semaphore                         |
| `ROVO_INSIGHTS_RETRY_BACKOFF_ENABLED`                 | gate           | off → 100 %    | B0 (T1.3)                              |
| `ROVO_INSIGHTS_LOG_FULL_PROMPT`                       | gate           | off           | B0 (T2.6)                              |
| `ROVO_INSIGHTS_FORCE_REFRESH_LIMITS`                  | dynamic config | `{userQpm:3, tenantQpm:50}` | B0 (T3.4) |
| `ROVO_INSIGHTS_IDEMPOTENCY_GUARD_ENABLED`             | gate           | off → 100 %    | B3 (T3.1)                              |
| `ROVO_INSIGHTS_WALL_CLOCK_BUDGET_MS`                  | dynamic long   | 360 000       | B3 (T3.5)                              |
| `ROVO_INSIGHTS_STRICT_NOTIFICATION_ENABLED`           | gate           | off → 100 %    | B4 (T3.2)                              |
| `ROVO_INSIGHTS_STUCK_SWEEPER_ENABLED`                 | tri-state gate | off → observe → active | B5 (S5)                  |
| `ROVO_INSIGHTS_PARTIAL_JSON_RECOVERY_ENABLED`         | gate           | off → 100 %    | B6 (T2.3)                              |
| `ROVO_INSIGHTS_STRUCTURED_OUTPUT_ENABLED`             | per-type gate  | off           | B6 (E3)                                |
| `ROVO_INSIGHTS_SHARED_CONVERSATION_ENABLED`           | gate           | off → 100 %    | B6 (T2.4)                              |
| `ROVO_INSIGHTS_PROMPT_VERSION`                        | dynamic string | `v1` → `v2`    | B7 (T2.1)                              |

### 4.3 Rollout phases (5 phases over ~6 weeks)

| Phase                      | Week  | Ships                                                                            | Gate to next phase                                                                                                  |
| -------------------------- | ----- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **P0 — telemetry baseline** | 1     | All "new telemetry" entries above; build dashboards. **No behavior change.**     | 7 days of clean baseline data captured for every metric in §4.1.                                                    |
| **P1 — quick wins**        | 2     | B0 (T1.3 backoff, T1.4 mapNotNull, T1.5 hoist flag, T2.6 log shrink, T3.4 rate limit). | All B0 items at 100 % for 48 h with no error-rate or latency regression.                                          |
| **P2 — isolation + reliability** | 3 | B1 (T1.2) at 1 → 10 → 50 → 100 % over 5 days; B5 salt memoize at 100 % (code change); B5 sweeper observe-only. | `_PER_TYPE_FAILURE` populating; `_GENERATION_SUCCESS{has_insights=true}` rate **+2pp**; sweeper `_DETECTED` matches help-desk reports. |
| **P3 — latency core**      | 4     | B2 (T1.1) at 10 → 50 → 100 % over 4 days; B3 (T3.1 idempotency + T3.5 wall-clock) at 10 → 50 → 100 % over 3 days; B5 sweeper switched to active. | `_GENERATION_LATENCY` p95 improved by **≥ 5 s**; `_IDEMPOTENCY_SHORT_CIRCUIT > 0` confirms duplicate dedup; stuck-task rate **< 0.5 %**. |
| **P4 — notification + LLM efficiency** | 5 | B4 (T3.2 strict notify) at 5 → 25 → 100 % (gated on B3 at 100 %); B6 (T2.3 partial JSON, T2.4 hoisted conversation, E3 structured output per-type). | Notification miss rate **< 0.1 %** for 48 h; `_PARTIAL_JSON_PARSE` shows non-zero `valid_count` recovery; `conversationCreate` rate per generation **drops to ≈ 1.0**. |
| **P5 — prompt v2 + cleanup** | 6   | B7 (T2.1 prompt v2) at 5 → 25 → 50 % (hold for cost validation); promote to 100 % once `_PROMPT_CACHE_HIT` ratio confirms upstream caching applies; deprecate baseline-comparison flags. | Input-token cost **−50 %**; validation-error rate ≤ baseline + 0.5 pp; all SLOs in §4.4 green for 7 days. |

Sticky-bucketing rule: every per-user flag uses `accountId` (not `tenantId`) so a single user gets a consistent generation experience day-to-day; cohort isolation for SLO comparison stays clean.

### 4.4 Dashboards (Splunk + Grafana, six panels)

| Panel                       | Source                                                                                  | SLO target                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Cache health                | `_CACHE_HIT / (_HIT + _MISS)` split by `experience`                                     | Hit rate > 70 % steady; alert if < 50 % for 30 min.                         |
| Generation latency by type | `_PER_TYPE_GENERATION_LATENCY` p50/p95/p99 grouped by `insight_type`                    | Per-type p95 < 30 s; e2e (`_GENERATION_LATENCY`) p95 < 45 s, target < 35 s. |
| Stability / stuck rate      | `_GENERATION_SUCCESS / _JOB_SUBMITTED`, `_STUCK_TASK_DETECTED`, `_PER_TYPE_FAILURE`     | Success > 98 %; stuck rate < 0.5 %.                                         |
| LLM cost                    | `_INPUT_TOKENS_PER_TYPE` × price; `_PROMPT_CACHE_HIT` ratio; cost / active user        | Cost / active user trending down through P5; alert at 1.5 × baseline.       |
| Error budget + notification | `_GENERATION_ERROR` rate; `_NOTIFICATION_DISPATCH_ERROR` rate                          | Error < 1 %; notification miss < 0.1 %.                                     |
| Retry + validation          | `_RETRY_ATTEMPT` distribution; validation-filtered rate (existing log); partial-parse counters | < 5 % need attempt 2; < 2 % need attempt 3.                                 |

### 4.5 PagerDuty alerts (7 new)

| Alert                            | Threshold                                                                            | Severity | Pager        |
| -------------------------------- | ------------------------------------------------------------------------------------ | -------- | ------------ |
| Stuck-task rate high             | `_STUCK_TASK_DETECTED / _JOB_SUBMITTED > 1 %` over 30 min                            | SEV-3    | Rovo on-call |
| Generation error rate            | `_GENERATION_ERROR / _JOB_SUBMITTED > 5 %` over 15 min                               | SEV-2    | Rovo on-call |
| Notification dispatch error      | `_NOTIFICATION_DISPATCH_ERROR_RATE > 1 %` over 15 min                                | SEV-3    | Rovo on-call |
| LLM cost per-user spike          | `_INPUT_TOKENS_PER_TYPE × price ÷ active users > 2 ×` 7-day rolling avg              | SEV-3    | FinOps + Rovo |
| Cache hit-rate drop              | `_CACHE_HIT` ratio < 40 % for 30 min (excluding salt-rotation windows)               | SEV-3    | Rovo on-call |
| Per-type p95 latency regression  | `_PER_TYPE_GENERATION_LATENCY` p95 > 60 s for 30 min                                 | SEV-2    | Rovo on-call |
| Force-refresh flood              | `_FORCE_REFRESH_RATE_LIMITED > 100/min` sustained 10 min                             | SEV-3    | Rovo on-call |

### 4.6 Load testing & chaos

**Load tests** (extend `convo-ai-test-integration` with new module `rovo-insights-loadtest`, Gatling/Kotlin):

1. **SQS visibility under handler concurrency.** 200 generations/min for 30 min at 80 % worker CPU → assert SQS message redelivery rate < 0.1 %.
2. **Cache-salt rotation under load.** Bump `ROVO_INSIGHTS_CACHE_SALT` while 50 active users have valid caches → assert provider 429 rate < 1 %, per-type p95 < 45 s.
3. **100 × cache-miss spike.** Inject 100 × normal miss rate via forced refresh → assert chat p95 + < 10 %, agent p95 + < 10 % (cross-feature isolation).

**Chaos tests** (Toxiproxy + extensions to existing test classes):

1. **Post Office 500 for 60 s** → user notification eventually delivered (post-B4). Test in `RovoInsightsNotificationServiceTest.kt`.
2. **Redis timeout 30 s** → user sees error path, not stuck. Test in `RovoInsightsCacheImplTest.kt`.
3. **One LLM type times out** → other 5 still served (post-B1). New test `single_type_timeout_does_not_cancel_siblings` in `RovoInsightsServiceImplTest.kt`.
4. **Pod kill mid-generation** → next status check resumes correctly (post-B5 sweeper). New `RovoInsightsStuckTaskSweeperTest`.
5. **LLM 429 burst on 30 % requests** → backoff + jitter spreads retries (post-B0 T1.3); success rate stays > 95 %. Extend `RetryableTest`.

### 4.7 Pre/post measurement

- **Pre (P0, 14 days):** capture daily series for every metric in §4.1; cohort by `experience` and `insight_type`.
- **Post (P5 → 100 %, then 14 days):** same metrics + new ones (TTFB if T2.2 ships, prompt-cache hit ratio, stuck-task rate, notification miss rate).
- **Report structure:** executive summary (3 bullets), per-change attribution table (which metric moved on which flag-flip day), control-vs-treatment cohort comparison, cost analysis recomputed against actual cache-hit ratios, anomalies + open issues, SLO dashboard screenshots at start/midpoint/end.

### 4.8 Cost-reduction math (T2.1 / B7)

Inputs: 6 calls × ~6 000 input tokens × 100 000 active users × 1 generation/day = **3.6 B input tokens/day baseline**.

Assumption: 80 % of those tokens are the shared prefix; if upstream prompt-caching applies, prefix reads cost ~0.1 × normal.

- Baseline (relative units, 1.0 = normal token): 3.6 B × 1.0 = **3.6 B units/day**.
- Post-T2.1: shared 0.8 × 3.6 B at 0.1 × = 0.288 B; unique 0.2 × 3.6 B at 1.0 × = 0.72 B → total **1.008 B units/day**.
- Reduction: **(3.6 − 1.008) / 3.6 ≈ 72 %**.

At ~$0.003/1 K input tokens (typical Haiku-class): baseline ≈ $10 800/day → ≈ $3 024/day → **~$7 800/day saved, ~$2.83 M/year**.

Caveat: depends on the upstream model actually supporting prompt caching. P5 holds B7 at 50 % until `_PROMPT_CACHE_HIT` confirms.

### 4.9 Reversibility matrix

All changes except B5 salt memoize revert via Statsig flag flip (~60 s). B5 salt memoize is a code-only revert (redeploy) but can be guarded by a temporary `ROVO_INSIGHTS_SALT_MEMOIZE_ENABLED` flag for the first week. **No change in this rework requires a Redis cache flush**: the schema is keyed by `cacheSchemaVersion + dataSchemaVersion + cacheSalt` ([`RovoInsightsCacheImpl.kt:67-69`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsCacheImpl.kt#L67-L69)). When B7 prompt v2 promotes, bump `RovoInsightsResponse.DATA_SCHEMA_VERSION` (currently 3) — old entries become unreachable and TTL-out at 7 days.

---

## 5. Critical files (every modification location, in one place)

| File                                                                                                                                                                    | Touched by                                                                                       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [`modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsServiceImpl.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsServiceImpl.kt)                       | B0 (T1.4, T1.5, T2.6), B1 (T1.2 supervisorScope), B2 (T1.1 hydration refactor), B3 (T3.5 budget), B6 (T2.3 partial JSON, T2.4 hoist conversation, E3 structured output) |
| [`modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsGenerationTaskHandler.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsGenerationTaskHandler.kt)   | B3 (T3.1 idempotency guard); minor metric additions                                              |
| [`modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsNotificationService.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsNotificationService.kt)       | B4 (T3.2 strict notify with retry+throw)                                                        |
| [`modules/product/rovo/rovo-extras-impl/.../insights/Retryable.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/Retryable.kt)                                                  | B0 (T1.3 backoff/jitter; signature becomes `suspend`)                                            |
| [`modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsCacheImpl.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsCacheImpl.kt)                          | B5 (T3.3 salt memoize via Caffeine)                                                              |
| `modules/product/rovo/rovo-extras-impl/.../insights/RovoInsightsStuckTaskSweeper.kt` (NEW)                                                                                | B5 (S5 stuck-task sweeper, `@Scheduled`)                                                         |
| [`modules/product/rovo/rovo-impl/.../rest/RovoInsightsV1Controller.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/rest/RovoInsightsV1Controller.kt)                                          | B0 (T3.4 rate limit on `forceCacheMiss`); deferred S6 endpoint split                            |
| [`modules/product/rovo/rovo-extras-impl/.../insights/llmresponse/Common.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-extras-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/llmresponse/Common.kt)                                | B7 (T2.1 prompt extraction reorg)                                                                |
| `modules/product/rovo/rovo-impl/src/main/resources/templates/rovo/insights/v1/*.pebble` and `_shared_*.pebble` (NEW)                                                       | B7 (T2.1 Pebble partial extraction + reorder for prompt cache)                                  |
| [`modules/product/rovo/rovo-api/.../insights/RovoInsightsGenerationTask.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-api/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/insights/RovoInsightsGenerationTask.kt)                               | B3 (add nullable `enqueuedAt: Instant`)                                                          |
| [`modules/product/rovo/rovo-api/.../rest/insights/fetch/RovoInsightsResponse.kt`](_dev/conversational-ai-platform/modules/product/rovo/rovo-api/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/rest/insights/fetch/RovoInsightsResponse.kt)                     | B7 (bump `DATA_SCHEMA_VERSION` from 3 when v2 prompts promote)                                  |

**Existing utilities to reuse (do not reinvent):**

- `Retryable.kt` `retryable<T, reified E>(...)` — extend with backoff (B0); reuse from B4 for notification retry.
- [`UserService.getUserNames(List<String>)`](_dev/conversational-ai-platform/modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/user/UserService.kt#L45-L48) — pattern for batch APIs (when proposing the follow-up `getUserProfiles` extension).
- `MetricsService.count / timeAndHistogram` — reuse for all new metrics.
- `RolloutService.controlledByFullContext / getDynamicConfigField` — every new flag/dynamic config goes through this.
- Existing `cacheSchemaVersion + dataSchemaVersion + cacheSalt` keying scheme — invalidation path is already correct.
- The existing `Strategy.EVALUATE` side-by-side eval pattern — reuse for B7 prompt v1 vs v2 quality testing.

---

## 6. Open architectural questions (need product / leadership input — not blocking B0–B5)

1. **Progressive UI (deferred T2.2):** is the product team OK with users seeing 1–6 insight groups arriving over time, or must the result be atomic? Determines whether progressive surfacing becomes default or experimental.
2. **Per-type model routing (deferred T2.5):** which insight types tolerate a cheaper / faster model? Needs quality eval. Blocked on product.
3. **`systemPrompt` parameter on `RovoChatServiceApi.chatStream` (B7 ceiling):** add to API surface? Affects all `RovoChatServiceApi` consumers — separate proposal, not coupled to this rework.
4. **Concurrent same-`conversationId` `chatStream` calls (B6 / T2.4):** does the upstream chat service tolerate this with `storeMessage = false`? Must confirm with chat-service owner before enabling shared-conversation mode.
5. **Endpoint split (deferred S6):** is the frontend able to migrate from POST `/status` (mixed read+enqueue) to GET `/insights` + POST `/generate`? If not, the rate-limit (T3.4 in B0) is the minimum bar.
6. **DLQ philosophy for B4 notification permanent failures:** swallow after N redrives to break the loop, or trust SQS DLQ + alerting? Operational philosophy decision.

---

## 7. End-to-end verification at completion

A reviewer or operator can verify the rework is in effect by:

1. **Telemetry spot-check.** Open the "Rovo Insights — Health & Cost" Grafana dashboard. Confirm all six panels are populated and SLOs are within target. Specifically:
   - `_GENERATION_LATENCY` p95 < 35 s in the post-rollout 14-day window.
   - `_PROMPT_CACHE_HIT` ratio > 50 % (post-B7).
   - `_STUCK_TASK_DETECTED` rate < 0.5 %.
   - `_NOTIFICATION_DISPATCH_ERROR_RATE` < 0.1 %.
2. **Code-site spot-check.** Confirm `RovoInsightsServiceImpl.kt` `generate(...)` uses `supervisorScope` (B1), the hydration call is a single `hydrateAllPersonReferences` above the response build (B2), and the conversation create is hoisted out of the per-type loop (B6 T2.4).
3. **Behavioral spot-check.** Run the chaos test "single LLM type times out" — assert the response includes the other 5 groups with non-empty content. Run "Post Office 500 for 60 s" — assert SQS redrive observed and notification ultimately delivered. Run "pod kill mid-generation" — assert sweeper re-enqueues within 10 min.
4. **Cost spot-check.** Compare `_INPUT_TOKENS_PER_TYPE × price ÷ active users` against the 14-day pre-baseline; expect ~70 % reduction post-B7.
5. **Local/dev verification commands.**
   - `./gradlew :modules:product:rovo:rovo-extras-impl:test --tests RovoInsightsServiceImplTest`
   - `./gradlew :modules:product:rovo:rovo-extras-impl:test --tests RetryableTest`
   - `./gradlew :modules:product:rovo:rovo-extras-impl:test --tests RovoInsightsGenerationTaskHandlerTest`
   - `./gradlew :modules:product:rovo:rovo-extras-impl:test --tests RovoInsightsNotificationServiceTest`
   - The new `RovoInsightsStuckTaskSweeperTest` and `single_type_timeout_does_not_cancel_siblings` integration test must pass.

---

*Plan written 2026-05-03. Ready for review and approval before implementation begins.*
