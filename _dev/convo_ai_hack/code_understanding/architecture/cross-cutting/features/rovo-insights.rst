.. _feature-rovo-insights:

==================================================================
Rovo Insights — async LLM-generated personalized work insights
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: ~4,690 main + 1,329 test LoC across 49 files in 3 modules
:Test/main ratio: 1.5×

A user-facing async-generated feature surfacing six categories of
personalized "what's happening in your work" insights. **Not a
Gradle module** — a feature distributed across three existing
modules with sharp separation of concerns.

What it IS (in one sentence)
==============================

For each Rovo user, periodically generate six categories of
LLM-curated insight cards (Follow-Ups, Emerging Topics, Company
News, Trending Work, Recognition, Important Meetings), surface them
in the Rovo UI, and notify the user when fresh insights are ready.

Where it lives
===============

.. list-table::
   :header-rows: 1
   :widths: 35 12 12 41

   * - Module
     - Files
     - LoC
     - Role
   * - ``product/rovo/rovo-api/insights/``
     - 6
     - 155
     - Service contract, cache contracts, task envelope
   * - ``product/rovo/rovo-api/rest/insights/``
     - 9
     - 363
     - REST request/response DTOs, enums (InsightType, Glyph, Color), Defaults
   * - ``product/rovo/rovo-impl/.../rest/RovoInsightsV1Controller.kt``
     - 1
     - 205
     - REST endpoints + request routing
   * - ``product/rovo/rovo-extras-impl/insights/``
     - 25
     - **2,638**
     - Service impl, task handler, 6 LLM response types, 4 cache impls, notification, ADF builders
   * - **TOTAL (main)**
     - **41**
     - **3,361**
     -
   * - Tests across all 3 modules
     - 9
     - **1,329**
     - 1.5× test/main ratio

Architectural shape — three subsystems
========================================

Rovo Insights cleanly decomposes into three subsystems with sharp
separation of concerns:

1. **Generation** — REST/SQS entry, LLM orchestration, retry, response parsing
2. **Persistence** — 4-layer cache hierarchy (insights cache + task cache, each with API/Redis split)
3. **Delivery** — Notification + REST polling for cached results


End-to-end flow
=================

The two-phase async architecture is the core architectural decision:

**Phase 1 — Submission (sync, fast, ~100ms):**

1. Frontend calls ``POST /api/rovo/v1/insights/status`` to check if cached insights exist
2. If user wants fresh insights → frontend calls REST ``POST /api/rovo/v1/insights/fetch``
3. ``RovoInsightsV1Controller`` checks ``RovoInsightsCache.get()`` for existing cached result
4. **Cache hit** → return immediately (~10ms)
5. **Cache miss** → ``service.submitGenerationJob()`` creates ``RovoInsightsTask`` and enqueues SQS message via ``AsyncStreamingTaskService.startAsync()`` to ``TaskQueue.ROVO_INSIGHTS_GENERATION``
6. ``RovoInsightsTaskCache.put(user, task)`` records the in-flight task (1 hour TTL)
7. Return task ID to user; UI shows "generating insights..." state

**Phase 2 — Async generation (slow, 30s-4min):**

1. SQS worker picks up message → ``RovoInsightsGenerationTaskHandler.handle(task)``
2. Feature gate ``AIX_ROVO_INSIGHTS_ENABLED`` checked via ``RolloutService.controlledByFullContext()``
3. ``RovoInsightsServiceImpl.generate()`` runs all 6 insight types in parallel:

   .. code-block:: kotlin

      // RovoInsightsServiceImpl.kt:467
      coroutineScope {
          insightTypes.map { type ->
              async { generateInsightForType(type, ...) }
          }.awaitAll()
      }

4. Each ``generateInsightForType()`` invokes the **Rovo Chat agent** via ``RovoChatServiceApi.chatStream()``:

   * Agent: ``"ai_mate_agent"``
   * Prompt: Pebble template ``templates/rovo/insights/v1/<insightType>.pebble``
   * Streaming wrapped by ``SearchingStreamingWriter`` that waits for ``RovoChatV1FinalResponseMessageEnvelope``
   * Timeout: ``GENERATION_TIMEOUT_MILLIS = 240_000`` (4 min)

5. LLM returns JSON array → Jackson deserializes to typed ``List<T>`` where ``T extends Insight``
6. If zero insights returned → ``ZeroInsightsgeneratedException`` triggers retry (up to ``maxAttempts=3``)
7. ``RovoInsightsCache.put(user, cacheItem)`` stores result (7-day TTL)
8. ``RovoInsightsTaskCache.delete(user)`` clears the in-flight task marker
9. ``RovoInsightsNotificationService.sendInsightsReadyNotification()`` posts via Atlassian Post Office
10. Metrics emitted: per-type generation latency, count, error/success

**Phase 3 — User retrieval (sync, fast, ~10ms):**

1. User receives Post Office notification → frontend re-fetches
2. ``RovoInsightsCache.get()`` returns cached ``RovoInsightsCacheItem``
3. Response shape converted to flat ``RovoInsightsResponse`` with grouped insights

Sequence diagram
==================

.. mermaid::

   sequenceDiagram
       autonumber
       participant FE as Frontend
       participant Ctrl as RovoInsightsV1<br/>Controller
       participant Svc as RovoInsights<br/>ServiceImpl
       participant Cache as RovoInsights<br/>Cache
       participant TaskCache as RovoInsights<br/>TaskCache
       participant SQS as AsyncStreamingTask<br/>Service (SQS)
       participant Handler as RovoInsightsGen<br/>TaskHandler
       participant LLM as RovoChat<br/>(ai_mate_agent)
       participant Notif as Notification<br/>Service (PostOffice)

       FE->>Ctrl: POST /v1/insights/fetch
       Ctrl->>Cache: get(user)
       alt Cache hit (10 ms)
           Cache-->>Ctrl: cached RovoInsightsCacheItem
           Ctrl-->>FE: 200 OK + RovoInsightsResponse
       else Cache miss
           Ctrl->>Svc: submitGenerationJob(user, promptConfig)
           Svc->>SQS: startAsync(task envelope)
           Svc->>TaskCache: put(user, task)
           Svc-->>Ctrl: AsyncTaskId
           Ctrl-->>FE: 200 OK + taskId

           Note over SQS,Handler: Async (30s - 4 min)
           SQS->>Handler: dequeue task
           Handler->>Handler: check Statsig flag
           Handler->>Svc: generate(user, request)

           par 6 insights in parallel
               Svc->>LLM: chatStream(prompt[FOLLOW_UP])
               and
               Svc->>LLM: chatStream(prompt[EMERGING])
               and
               Svc->>LLM: chatStream(prompt[COMPANY])
               and
               Svc->>LLM: chatStream(prompt[YOUR_TRENDING])
               and
               Svc->>LLM: chatStream(prompt[RECOGNITION])
               and
               Svc->>LLM: chatStream(prompt[MEETING])
           end
           LLM-->>Svc: JSON streaming chunks → final response
           Svc->>Svc: Jackson parse → List<Insight>
           Svc-->>Handler: RovoInsightsResponse

           Handler->>Cache: put(user, cacheItem) [7 day TTL]
           Handler->>TaskCache: delete(user)
           Handler->>Notif: sendInsightsReadyNotification(user, taskId)
           Notif->>FE: PostOffice push notification

           FE->>Ctrl: POST /v1/insights/fetch (re-poll)
           Ctrl->>Cache: get(user) → HIT
           Ctrl-->>FE: 200 OK + RovoInsightsResponse
       end


The 6 insight types
=====================

Six distinct insight categories, each with a typed Kotlin data class
representing the LLM-emitted JSON shape. **NOT 7 types** — earlier
documentation incorrectly counted Common.kt as a 7th type.

.. list-table::
   :header-rows: 1
   :widths: 22 12 14 12 12 28

   * - InsightType enum
     - Class
     - JSON tag
     - Glyph
     - Color
     - Group title (UI)
   * - ``FOLLOW_UP_INSIGHTS``
     - ``FollowUp``
     - ``follow-up-insights``
     - TARGET
     - YELLOW
     - "Waiting on you"
   * - ``EMERGING_WITH_YOUR_TEAM``
     - ``Emerging``
     - ``emerging-with-your-team``
     - CHART_TREND_UP
     - MAGENTA
     - "What your team's into"
   * - ``COMPANY_INSIGHTS``
     - ``CompanyInsights``
     - ``company-insights``
     - MEGAPHONE
     - BLUE
     - "Across the company"
   * - ``YOUR_TRENDING_WORK``
     - ``YourTrendingWork``
     - ``your-trending-work``
     - EYE_OPEN
     - TEAL
     - "Your work is travelling"
   * - ``RECOGNITION_INSIGHTS``
     - ``RecognitionInsights``
     - ``recognition-insights``
     - GOAL
     - MAGENTA
     - "Worth celebrating"
   * - ``MEETING_INSIGHTS``
     - ``MeetingInsights``
     - ``meeting-insights``
     - CALENDAR
     - ORANGE
     - "Important meetings"

What each type means (semantic intent)
-----------------------------------------

* **Follow-Up Insights** — Tasks/threads/decisions awaiting the user's response
  (e.g., unanswered Slack threads, Jira tickets assigned and not updated)
* **Emerging with Your Team** — Topics gaining traction across team activity
  (e.g., new initiatives surfacing in multiple Confluence pages or Slack channels)
* **Company Insights** — Company-wide announcements, strategy shifts, major news
* **Your Trending Work** — User's own artifacts gaining engagement
  (a Confluence page they wrote getting many views, a Jira issue they reported being widely discussed)
* **Recognition Insights** — Noteworthy achievements by teammates worth acknowledging
* **Meeting Insights** — High-impact meetings the user attended/missed; outcomes worth knowing

The polymorphism design
=========================

Three layers of representation as data crosses the system:

**Layer 1 — LLM response shape** (Jackson polymorphism via discriminator):

.. code-block:: kotlin

   // Common.kt
   @JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type", visible = true)
   @JsonSubTypes(
       JsonSubTypes.Type(FollowUp::class, name = "follow-up-insights"),
       JsonSubTypes.Type(Emerging::class, name = "emerging-with-your-team"),
       JsonSubTypes.Type(CompanyInsights::class, name = "company-insights"),
       JsonSubTypes.Type(MeetingInsights::class, name = "meeting-insights"),
       JsonSubTypes.Type(RecognitionInsights::class, name = "recognition-insights"),
       JsonSubTypes.Type(YourTrendingWork::class, name = "your-trending-work"),
   )
   abstract class Insight(
       val type: InsightType,
       val sources: List<Source>,
       val title: String,
       val overview: String,
       val context: String?,
       val people: List<Person>?,
       val links: List<Link>?,
       val thinking: String,
       val followUps: List<String>?,
   ) {
       abstract fun toAdf(): JsonNode
       fun calculateValidationErrors(): List<String> { ... }
   }

**Layer 2 — Service-internal grouping**: After parsing, results are
grouped by ``InsightType`` enum.

**Layer 3 — REST response (flattened)**:

.. code-block:: kotlin

   data class RovoInsightsResponse(
       val schemaVersion: Int,
       val generatedAt: Instant,
       val count: Int,
       val summary: String,
       val insightGroups: List<RovoInsightsGroup>,
   )

   data class RovoInsightsGroup(
       val type: InsightType,
       val title: String,
       val icon: Glyph,
       val color: Color,
       val count: Int,
       val insights: List<RovoInsight>,
       val debugInfo: DebugInfo?,
   )

   data class RovoInsight(
       val title: String,
       val overview: String,
       val people: List<PersonReference>?,
       val urls: List<String>?,
       val thinking: String,
       val followUps: List<String>?,
       val detailsAdf: String,  // pre-rendered ADF JSON
   )

**Critical observation:** The polymorphic ``Insight`` hierarchy exists
**only at the LLM-parsing boundary**. Once parsed, insights are
flattened to a single generic ``RovoInsight`` shape for REST. The
polymorphism buys type-safe LLM response parsing but is intentionally
lost at the API boundary so the frontend doesn't need to handle 6
different schemas — just one schema with a category label.

Adding a new insight type — 6 file edits
==========================================

Architecturally, adding a 7th type requires:

1. Create new file ``rovo-extras-impl/insights/llmresponse/NewInsight.kt`` extending ``Insight``
2. Add enum value in ``rovo-api/rest/insights/InsightType.kt``
   (with ``Glyph`` icon + ``Color`` + ``groupTitle``)
3. Register in ``Common.kt``: add to ``@JsonSubTypes``
4. Register in ``Common.kt``: add to ``InsightTypeMapping`` (enum → class map)
5. Register in ``Common.kt``: add to ``InsightPromptRegistry`` (enum → prompt instructions)
6. Add to ``Defaults.kt`` ``DEFAULT_ROVO_INSIGHTS_PROMPT_CONFIG`` map
7. Create Pebble template ``rovo-impl/.../resources/templates/rovo/insights/v1/<new-type>.pebble``

This is a known friction point — each new type needs 6-7 coordinated
edits across 2 modules. A registration pattern (annotation processor
or service loader) could reduce this to 1-2 edits.


The 4-cache hierarchy
=======================

Two distinct caches × two abstraction layers each = 4 cache types.

.. list-table::
   :header-rows: 1
   :widths: 32 18 14 36

   * - Cache type
     - Stores
     - TTL
     - Key fields
   * - ``RovoInsightsCache`` (high-level)
     - Final ``RovoInsightsCacheItem``
     - 7 days
     - tenant + userId + schema versions + cacheSalt
   * - ``RovoInsightsRedisCache`` (low-level)
     - Same payload, raw Redis ops
     - 7 days
     - same
   * - ``RovoInsightsTaskCache`` (high-level)
     - In-flight ``RovoInsightsTask``
     - 1 hour
     - tenant + userId
   * - ``RovoInsightsTaskRedisCache`` (low-level)
     - Same payload, raw Redis ops
     - 1 hour
     - same

**Cache vs TaskCache** — different lifecycle phases:

* **InsightsCache** stores *completed* generation results.
  Immutable per (user, schema, salt). Long-lived (7 days).
  User-polled.
* **TaskCache** stores *in-flight* generation metadata.
  Mutable. Short-lived (1 hour, allowing graceful recovery
  if handler crashes). Cleared on completion.

**Why -Cache + -RedisCache split (NOT multi-level caching)** —
this is **abstraction layering**, not cache hierarchy:

* ``-Cache`` interfaces are high-level, tenant-aware, business logic
  (metrics emission, error handling, dynamic salt resolution)
* ``-RedisCache`` interfaces are low-level, Redis-specific, raw key-value ops
* The ``-Cache`` impl wraps the ``-RedisCache`` impl with cross-cutting concerns

**Example — cache key includes 4 versioning dimensions:**

.. code-block:: kotlin

   data class RovoInsightsKeyInput(
       val userId: String,             // tenant + user scoping
       val cacheSchemaVersion: Int,    // bump → invalidate on cache shape change
       val dataSchemaVersion: Int,     // bump → invalidate on response shape change
       val cacheSalt: String,          // dynamic Statsig flag → invalidate without deploy
   )

The ``cacheSalt`` is the operationally interesting one — fetched from
``rolloutService`` per-request, allowing **operator-driven cache
invalidation** without code deploy. If insights quality regresses,
ops can flip the salt to force regeneration for all users.

REST API
==========

Three endpoints exposed at ``/api/rovo/v1/insights`` from ``RovoInsightsV1Controller``:

.. list-table::
   :header-rows: 1
   :widths: 14 30 28 28

   * - Method
     - Path
     - Request
     - Response
   * - POST
     - ``/status``
     - ``RovoInsightsStatusRequest`` (forceCacheMiss flag)
     - ``RovoInsightsStatusResponse`` (insightsAvailable: Boolean)
   * - POST
     - ``/fetch``
     - ``RovoInsightsRequest`` (generate, debugInfo, promptConfig)
     - ``RovoInsightsResponse``
   * - POST
     - ``/enqueue``
     - (implicit)
     - ``AsyncTaskId``

Both ``/status`` and ``/fetch`` are marked ``@EndUserEndpoint`` and gated
by ``AIX_ROVO_INSIGHTS_ENABLED`` Statsig flag.

ADF rendering — 5 specialized builders
=========================================

ADF = Atlassian Document Format (the rich-text JSON format used across
Confluence, Jira). Each insight's ``detailsAdf`` field is a pre-rendered
JSON string. Generated by 5 builder utilities:

.. list-table::
   :header-rows: 1
   :widths: 38 12 50

   * - Builder
     - LoC
     - Output
   * - ``BuildHeading``
     - 24
     - ADF ``heading`` (level 4) with strong-marked text
   * - ``BuildParagraph``
     - 18
     - ADF ``paragraph`` with text node
   * - ``BuildLink``
     - 14
     - ADF ``extension`` (extensionKey ``insight:linkCard``) — single link card
   * - ``BuildInsightProfileGroupExtension``
     - 15
     - ADF ``extension`` (extensionKey ``insight:profileGroup``) — avatar group
   * - ``BuildInsightLinkCardGroupExtension``
     - 13
     - ADF ``extension`` (extensionKey ``insight:linkCardGroup``) — multiple link cards

The two ``insight:*`` extensions are **Rovo-specific custom ADF extensions**.
They require a corresponding renderer plugin in the consuming Atlassian
product (Confluence/Jira) to display them. The backend emits the extension
descriptor; the frontend renders the actual avatar group / link cards.

**Why these 5 specifically?** Insights are narrative-driven (title +
overview + maybe links/avatars). They're not tabular and not bulleted,
so no ``BuildBulletList`` or ``BuildTable`` builder exists. The minimal
builder set reflects intentional scope discipline.


External system fan-out
=========================

A single insights generation triggers calls to:

.. list-table::
   :header-rows: 1
   :widths: 28 38 34

   * - System
     - How it's invoked
     - Purpose
   * - **AI Gateway** (via Rovo Chat)
     - ``RovoChatServiceApi.chatStream()`` × 6 (one per type)
     - LLM inference for each insight type
   * - **Statsig**
     - ``RolloutService.controlledByFullContext()``
     - 2 flags: ``AIX_ROVO_INSIGHTS_ENABLED`` + ``AIX_ROVO_INSIGHTS_USER_HYDRATION_ENABLED`` + dynamic ``ROVO_INSIGHTS_CACHE_SALT``
   * - **Redis** (insights cache)
     - ``RovoInsightsRedisCache.set/get()``
     - 7-day cached results
   * - **Redis** (task cache)
     - ``RovoInsightsTaskRedisCache.set/get/delete()``
     - 1-hour task lifecycle marker
   * - **SQS**
     - ``AsyncStreamingTaskService.startAsync()``
     - Async generation queue
   * - **User Service**
     - ``UserService.getUserProfile()`` (per person)
     - Hydrate names + avatars for ``Person`` references
   * - **Post Office**
     - ``StreamhubEventPublisher.publish()``
     - User notification when insights ready
   * - **Metrics**
     - ``MetricsService.count/timeAndHistogram()``
     - Per-type latency, count, error counters

Design patterns identified
============================

.. list-table::
   :header-rows: 1
   :widths: 28 28 44

   * - Pattern
     - Where
     - Description
   * - Two-phase async (submit/poll)
     - Controller + handler
     - Sync REST kicks off task; user polls or notified later
   * - Cache-aside
     - Controller → Cache → SQS
     - Read-through on miss; write-back after generation
   * - Retry with typed exception
     - ``Retryable.kt:12`` ``inline fun retryable<T, reified E>``
     - Reified type parameter for selective exception catching
   * - Streaming-message filter
     - ``SearchingStreamingWriter.kt:12``
     - Predicate-driven awaitable for stream → single final message
   * - Parallel fan-out
     - ``RovoInsightsServiceImpl.kt:467`` ``coroutineScope { async { ... }.awaitAll() }``
     - 6 LLM calls in parallel per generation
   * - Polymorphic Jackson + flat REST
     - ``Common.kt`` ``@JsonSubTypes`` then flatten to ``RovoInsight``
     - Type-safe LLM parsing, simple frontend contract
   * - Operator-driven cache invalidation
     - ``cacheSalt`` from Statsig
     - Flip flag → invalidate all cached insights without deploy
   * - Backend-driven UI styling
     - ``Glyph`` + ``Color`` enums in REST response
     - Centralized styling decisions (also a smell — see below)

Smells and concerns
=====================

Brutally honest list, ranked by severity:

.. list-table::
   :header-rows: 1
   :widths: 8 32 14 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **No distributed cache invalidation**
     - cache impls
     - Cache salt is the only invalidation mechanism. If insights quality improves, old cached results don't update for up to 7 days unless ops flips the salt. No pub-sub / TTL-on-write-with-shorter-window strategy.
   * - 🔴
     - **Task cleanup only on success**
     - ``RovoInsightsGenerationTaskHandler``
     - If handler crashes mid-generation, ``RovoInsightsTask`` stays in ``TaskCache`` for 1 hour. No retry loop, no dead-letter handling. User sees "generating..." indefinitely.
   * - 🔴
     - **Backend-driven UI styling** (Glyph + Color enums)
     - REST response
     - Backend decides icon + color per ``InsightType``. Violates separation of concerns — styling should live in design-tokens or frontend code. Forces any UI restyle to be a backend deploy.
   * - 🟡
     - **Hardcoded 4-min timeout, no per-type tuning**
     - ``RovoInsightsServiceImpl.kt:569``
     - ``GENERATION_TIMEOUT_MILLIS = 240_000`` global. If one type times out, all 6 cancel (parallel ``coroutineScope`` semantics).
   * - 🟡
     - **Linear retry, no backoff/jitter**
     - ``Retryable.kt:17``
     - Retry-on-zero-insights slams the LLM 3× immediately. Risk of compounding LLM-side errors.
   * - 🟡
     - **Person hydration is per-call (no batching)**
     - ``RovoInsightsServiceImpl.kt:325``
     - Each ``Person`` reference hits ``UserService.getUserProfile()`` serially. With 6 insight types × N people each, this is an obvious N+1.
   * - 🟡
     - **6-edit cost to add a new insight type**
     - cross-file
     - 6-7 coordinated edits across 2 modules. Annotation processor or service loader could reduce to 1-2.
   * - 🟡
     - **Exception-based control flow for retry**
     - ``RovoInsightsServiceImpl.kt:265``
     - ``ZeroInsightsgeneratedException`` thrown to trigger retry. Considered anti-pattern but isolated.
   * - 🟢
     - **Mutable result-detail fields**
     - ``GenerateInsightResultDetails.kt``
     - ``var`` fields mutated during generation. Poor immutability but local.
   * - 🟢
     - **Inline LLM prompts (in Kotlin)**
     - ``Common.kt`` ``InsightPromptRegistry``
     - Prompts as Kotlin string constants. Pebble templates exist (``templates/rovo/insights/v1/<type>.pebble``) but the registry mixes inline + template. Inconsistency.
   * - 🟢
     - **Status response is binary**
     - ``RovoInsightsStatusResponse`` (7 LoC)
     - Just ``insightsAvailable: Boolean``. No progress %, no ETA, no last-updated timestamp.
   * - 🟢
     - **Notification not idempotent**
     - ``RovoInsightsNotificationService``
     - If handler re-executes (SQS at-least-once), duplicate notifications can fire. Mitigated by trigger ID but not guaranteed.

Refactoring opportunities
===========================

In rough effort × payoff order:

1. **Add SQS dead-letter handling for stuck tasks** (S effort, 🔴 high payoff) —
   Add a sweeper that detects tasks in ``TaskCache`` older than 5 min and either
   re-enqueues or marks failed. Today users see "generating..." indefinitely if a
   handler crashes.

2. **Batch user-profile hydration** (S effort, 🟡 medium payoff) —
   Replace per-person ``UserService.getUserProfile()`` calls with a single bulk
   ``UserService.getUserProfiles(List<aaid>)``. Likely cuts hydration latency 5-10×.

3. **Move ``Glyph`` and ``Color`` out of the REST response** (M effort, 🔴 high payoff long-term) —
   Frontend should map ``InsightType`` enum to UI styling using design tokens. Backend
   shouldn't ship icon/color per response. Required if frontend rebrands or supports themes.

4. **Add per-type generation timeout config** (S effort, 🟡 medium payoff) —
   Move ``GENERATION_TIMEOUT_MILLIS`` to per-type ``RovoInsightsPromptConfig``. Allows
   slow types (Meeting Insights — needs Calendar API) to have longer budget than fast
   types (Trending Work — only needs internal data).

5. **Replace exception-driven retry with explicit Result type** (M effort, 🟢 low payoff) —
   Cleaner code; easier to test; lets you accumulate per-attempt diagnostics.

6. **Annotation-processor or service-loader for insight type registration** (L effort, 🟢 low payoff) —
   Reduces 6-edit cost to add a new type. Worth doing only if 5+ new types planned.

7. **Add SSE/WebSocket for status updates** (L effort, 🟢 low payoff) —
   Replace polling with push. Frontend gets progress updates ("3 of 6 done") rather
   than just final notification.


What you would change here
============================

By task:

* **Add a new insight type** → see "Adding a new insight type — 6 file edits" above
* **Tweak an LLM prompt** → ``rovo-impl/src/main/resources/templates/rovo/insights/v1/<type>.pebble`` (Pebble template) OR ``Common.kt`` ``InsightPromptRegistry`` (inline)
* **Change cache TTL** → ``RovoInsightsCacheImpl`` (insights, 7 days) or ``RovoInsightsTaskCacheImpl`` (task, 1 hour)
* **Change parallel-generation behavior** → ``RovoInsightsServiceImpl.generate()`` (line 467)
* **Change retry policy** → ``RovoInsightsServiceImpl.generateInsight()`` (calls into ``Retryable.kt:12``)
* **Force cache invalidation across users** → flip ``ROVO_INSIGHTS_CACHE_SALT`` Statsig dynamic config
* **Add a new notification channel** → ``RovoInsightsNotificationService`` (currently Post Office only)
* **Render a new ADF node type in details** → add a new builder under ``rovo-extras-impl/.../insights/adf/``
* **Add an analytics event** → emit metric in ``RovoInsightsServiceImpl`` or the task handler

What you would NOT change here
================================

* LLM gateway invocation — uses the platform-level ``RovoChatServiceApi``
* Feature flags evaluation — uses platform-level ``RolloutService``
* Async task queuing — uses platform-level ``AsyncStreamingTaskService``
* Redis client — uses framework-level ``RedisCache<K, V>``
* User profile retrieval — uses platform-level ``UserService``
* Notification dispatch — uses Atlassian Post Office (downstream service)

Test coverage
===============

:Verification date: 2026-05-03
:Verification method: ``find``, ``grep``, ``./gradlew test`` execution, JUnit XML report aggregation, three independent investigation agents whose claims were cross-checked against source

.. note::

   The previous version of this section listed only 9 unit-test files and
   computed an LoC ratio. That undercounted by ~70% and gave a false sense
   of coverage. The corrected picture below shows **97 unit tests across 16
   files (all passing in 4m17s)** but **ZERO integration, load, perf, chaos,
   synthetic, or canary tests** specific to Rovo Insights. The unit-test
   coverage is genuinely strong; the missing layers above unit are the
   actual risk profile.

What exists today (verified by execution)
------------------------------------------

**97 unit tests across 16 files, all passing in 4m 17s wall time.**

Run command (verified):

.. code-block:: bash

   cd <repo>/atlassian_packages/conversational-ai-platform
   ./gradlew \
     :convo-ai-product-rovo-extras-impl:test \
     :convo-ai-product-rovo-impl:test \
     :convo-ai-aifeature-impl:test \
     --tests "*Insights*" \
     --tests "*RetryableTest*" \
     --tests "*AdfBuildersTest*" \
     --tests "*LocalIdGeneratorServiceTest*" \
     --tests "*SearchingStreamingWriterTest*" \
     --tests "*TaskEnvelopeResponseTypeSerializationTest*" \
     --tests "*CommonTest*"

Per-file inventory (from JUnit XML reports):

.. list-table::
   :header-rows: 1
   :widths: 35 30 10 10 15

   * - File
     - Module (Gradle project)
     - Tests
     - Time
     - Covers
   * - ``RovoInsightsServiceImplTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 10
     - 5.0s
     - Generation logic, retry, error paths
   * - ``RovoInsightsCacheImplTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 10
     - 0.4s
     - Hit/miss metrics, cache salt, key consistency
   * - ``RovoInsightsGenerationTaskHandlerTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 5
     - 0.3s
     - Full async flow, cancellation, flag toggling
   * - ``RovoInsightsNotificationServiceTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 3
     - 0.4s
     - Notification dispatch + error swallowing
   * - ``adf/AdfBuildersTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 7
     - <1s
     - All 5 ADF builders (direct map equality)
   * - ``RetryableTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 3
     - <1s
     - Retry semantics
   * - ``LocalIdGeneratorServiceTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 2
     - <1s
     - ID generation
   * - ``SearchingStreamingWriterTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 2
     - <1s
     - Stream-filter awaitable
   * - ``llmresponse/CommonTest.kt``
     - ``:convo-ai-product-rovo-extras-impl``
     - 2
     - <1s
     - Validation logic on shared Insight base
   * - ``TaskEnvelopeResponseTypeSerializationTest.kt``
     - ``:convo-ai-product-rovo-impl``
     - 16
     - 8.6s
     - Polymorphic JSON envelope (de)serialization
   * - ``RovoChatTaskEnvelopeTest.kt``
     - ``:convo-ai-product-rovo-impl``
     - 5
     - 0.4s
     - Task envelope handling
   * - ``ChartInsightsFeatureServiceTest.kt``
     - ``:convo-ai-aifeature-impl``
     - 16
     - 1.3s
     - ChartInsights feature service (adjacent feature)
   * - ``ChartInsightsConfigProviderTest.kt``
     - ``:convo-ai-aifeature-impl``
     - 1
     - <1s
     - ChartInsights config (adjacent feature)
   * - ``HamInsightsSkillTest.kt``
     - ``agent-adk-minions``
     - 8
     - 0.3s
     - Ham Insights skill (adjacent agent skill)
   * - ``SurveyInsightsSkillTest.kt``
     - ``agent-adk-minions``
     - 5
     - 0.3s
     - Survey Insights skill (adjacent agent skill)
   * - ``HamInsightsMinionTest.kt``
     - ``agent-adk-stratus``
     - 4
     - <1s
     - Ham Insights minion (adjacent agent minion)
   * - **TOTAL**
     -
     - **97**
     - **~4m 17s**
     -

.. warning::

   The bottom 5 files (ChartInsights, HamInsights, SurveyInsights) are
   **adjacent features** that share the "Insights" name but are NOT the
   same feature as Rovo Insights. They are included here because they get
   pulled in by the test glob and are part of the broader "insights"
   surface area in the codebase. **Strict Rovo Insights unit-test count
   = 67 (in ``:convo-ai-product-rovo-extras-impl`` + ``:convo-ai-product-rovo-impl``).**

What runs in CI (verified from ``bitbucket-pipelines.yml``)
------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 25 15 25

   * - Pipeline step
     - Trigger
     - Covers Rovo Insights?
     - Notes
   * - ``unit-tests-rovo``
     - Every PR + main + hotfix
     - ✅ YES
     - Runs ``./gradlew test -PunitTestShard=rovo`` — auto-collects all 97 Insights tests
   * - ``unit-tests-core``, ``unit-tests-product``
     - Every PR + main + hotfix
     - ❌ NO
     - Different shards
   * - ``integration-tests-shard-{1..4}`` (× flags-on/off = 8 runs)
     - Every PR + main + hotfix
     - ❌ NO
     - No file in ``convo-ai-test-integration/`` references ``RovoInsights``
   * - ``startup-test`` (FullContextStartupIT)
     - Every PR + main + hotfix
     - ⚠️ INDIRECT
     - Verifies bean wiring; does NOT exercise generation
   * - ``lint-and-static-analysis-rovo``
     - Every PR + main + hotfix
     - ⚠️ STYLE
     - Detekt only; not functional
   * - ``mutation-test-weekly``
     - Custom (weekly cron)
     - ⚠️ MAYBE
     - Generic mutation testing; quality for Insights unknown
   * - ``sauron PR-insights``
     - Every PR
     - ⚠️ STYLE
     - Code-quality only, not functional Insights tests

**Bottom line:** Insights unit tests run on every PR. **No other layer
of testing runs against Insights in CI.**

What does NOT exist (verified gaps)
------------------------------------

Each gap below was verified by direct repository search.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Test layer
     - Status
     - Verification evidence
   * - Integration tests
     - ❌ NONE
     - ``grep -ri "RovoInsights" convo-ai-test-integration/`` returns 0 hits
   * - Load tests (perfhammer)
     - ❌ NONE
     - ``perfhammer/tests/`` contains only ``rovo-chat-stream-api.py`` + ``aifc-page-create-stream-api.py``; no insights scenario
   * - Performance / benchmark tests
     - ❌ NONE
     - No ``*PerfTest.kt``, ``*Benchmark.kt`` in any insights module
   * - Chaos / fault-injection tests
     - ❌ NONE
     - No chaos test exists; the v3.3 plan §6.1 lists 8 chaos tests as "to write"
   * - Synthetic monitoring (Pollinator)
     - ❌ NONE
     - ``operations/pollinator/checks/`` covers ``csm/foundation/jsm/studio/teamworkgraph`` — NOT rovo-insights
   * - Production canaries
     - ❌ NONE
     - No canary YAML for ``/rovo-insights/*`` endpoints
   * - WireMock stubs for Insights
     - ❌ NONE
     - Stubs are ``graphql-gateway``, ``jira-project-components``, ``streamhub``, ``devai-rovodev-streamhub`` only
   * - LLM-judge / eval tests
     - ❌ NONE
     - ``evaluation/`` directory has no Rovo Insights eval suite
   * - E2E (Cypress / Playwright / Selenium)
     - ❌ NONE
     - No e2e directories exist for Insights in repo

.. danger::

   **Naming-confusion warning.** During investigation, one agent confused
   "CSM" (Customer Service Management — a JSM product chatbot covered by
   ``CsmEvaluationStrategyIT.kt`` and Pollinator) with Rovo Insights. They
   are different products. Future readers should verify any "insights"
   test file actually targets Rovo Insights — the ChartInsights /
   HamInsights / SurveyInsights / CsmEvaluation files are NOT Rovo
   Insights coverage.

Bug-vs-test mapping (empirical)
--------------------------------

Of the 22 verified findings in the v3.3 improvement plan (L1-L2, S1-S9,
E1-E7, P1-P5), **ZERO have a pre-existing test that asserts the bug or
its fix**. The existing 97 unit tests cover the *happy path mechanics* of
the cache, generation handler, retry primitive, and ADF builders — but
none of the failure-mode scenarios that the v3.3 plan targets.

.. list-table::
   :header-rows: 1
   :widths: 15 50 35

   * - Bug ID
     - Scenario
     - Has regression test today?
   * - L2 / B1
     - ``coroutineScope`` cancellation — 1 type fails → all 5 cancel
     - ❌ NONE — no test asserts "1 fails, 5 succeed"
   * - L1 / B2
     - User-profile hydration runs N+1 instead of batched
     - ❌ NONE
   * - S1 / B3
     - Handler crash at SQS in-flight → permanent stuck state
     - ❌ NONE
   * - S2 / B4
     - Notification SQS redrive on transient failure
     - ❌ NONE
   * - S5 / B7
     - Stuck-generating sweeper for orphaned tasks
     - ❌ NONE
   * - S7 / B0.1
     - Cache TTL semantics (boundary expiry vs refresh)
     - ❌ NONE — ``RovoInsightsCacheImplTest`` tests mechanism only
   * - E1 / B6.1
     - LLM retry tuning under upstream backpressure
     - ❌ NONE
   * - B0.5
     - ``/force-refresh`` rate-limiting per user
     - ❌ NONE
   * - B8
     - Cache stampede lock under concurrent fetch
     - ❌ NONE
   * - All 22
     - Aggregate
     - ❌ 0 / 22 covered

.. danger::

   **2026-05-03 INCIDENT — read this before reading what follows.**

   B0.1 (cache TTL extension 1d → 7d) was implemented and pushed as
   PR #29064. It was caught and closed as a hidden UX regression:
   users would see up to 7-day-old insights instead of next-day-fresh.
   The v3.x plan called this "no quality risk" — that claim was wrong.

   **The improvement plan has been rewritten as v4.0 with a
   UX-First Principle.** Every bundle is now classified as
   A (UX-Neutral), B (UX-Improving), or C (UX-Affecting).
   Category C cannot ship silently.

   **Read** ``_plan/rovo_insights/PLAN-INTEGRATED-v4.md`` **before
   implementing any item.** Do NOT use the v3.x mappings below as
   ship-ready guidance — they include items now rejected (B0.1,
   B0.6, B6.1, B7-as-scoped).

The "every B-bundle adds a test" requirement
---------------------------------------------

To prevent regressions and provide a falsifiable definition of done,
every plan item in the v4.0 improvement plan (Section 6.1) must
include adding the missing unit test as part of its DoD. Tests
auto-run via ``unit-tests-rovo`` shard — no CI changes needed.

**v3.5 update (2026-05-03 triple-agent audit):** the plan's §17.5 now
covers **21 mandatory tests across 11 bundles** (was 17 — added B5 row
which was missing, plus 4 cross-cutting interaction tests X1-X4):

* **X1** — handler crash recovery (B3 expansion, ``kill -9`` simulation)
* **X2** — stampede lock at TTL boundary (B8 expansion, Monday-cohort)
* **X3** — partial-success semantics when 1 of 6 types succeeds
  (B1 expansion — what does the user actually see?)
* **X4** — dynamic-config hot-reload at runtime
  (B0.1 expansion — Statsig flag changes without redeploy)

Each B-bundle PR must include a per-bundle DoD checklist (see plan
§17.5.2 for the markdown template).

How to run tests
-----------------

**Smoke (single test, ~30s):**

.. code-block:: bash

   ./gradlew :convo-ai-product-rovo-extras-impl:test \
     --tests "*RovoInsightsCacheImplTest*"

**Core 5 Insights tests (~2 min) — recommended for fast feedback during plan-item PRs:**

.. code-block:: bash

   ./gradlew :convo-ai-product-rovo-extras-impl:test \
     --tests "*RovoInsightsServiceImplTest" \
     --tests "*RovoInsightsCacheImplTest" \
     --tests "*RovoInsightsGenerationTaskHandlerTest" \
     --tests "*RovoInsightsNotificationServiceTest" \
     --tests "*RetryableTest"

**Full Insights suite (~4-5 min):** see top of section for full command.

**Test reports (HTML):**

.. code-block:: bash

   open modules/product/rovo/rovo-extras-impl/build/reports/tests/test/index.html
   open modules/product/rovo/rovo-impl/build/reports/tests/test/index.html
   open modules/product/aifeature/aifeature-impl/build/reports/tests/test/index.html

Test infrastructure investments needed (T1-T7)
-----------------------------------------------

Separate from the B-bundle bug fixes, the following test-infrastructure
items would each unblock many future Insights-related PRs. Each is a
candidate Jira ticket.

.. list-table::
   :header-rows: 1
   :widths: 8 32 15 45

   * - ID
     - Investment
     - Effort
     - Unblocks
   * - T1
     - Add ``RovoInsightsControllerIT.kt`` E2E integration test
     - ~2-3 hours
     - B0.1, B6 measurability
   * - T2
     - Add perfhammer scenario for ``/rovo-insights/*`` endpoints
     - ~1 day
     - All performance claims (p50/p95/p99)
   * - T3
     - Add Pollinator synthetic check for production
     - ~4 hours
     - Production canary signal
   * - T4
     - Add WireMock stubs for upstream LLM gateway in Insights flow
     - ~1 day
     - Integration tests, chaos tests
   * - T5
     - Add 8-test chaos suite (per v3.3 plan §6.1)
     - ~3 days
     - B3, B4, B8 fault scenarios
   * - T6
     - Add LLM-judge eval suite for insight quality
     - ~1 week
     - Quality regression detection
   * - T7
     - Enable Kover coverage gate ≥80% on rovo-extras-impl
     - ~2 hours
     - Prevent test-quality regressions

Critical thinking notes
------------------------

Six lessons from this investigation worth surfacing:

1. **Three independent agents disagreed.** Agent 1's findings (12-file
   inventory) were correct. Agent 2's findings (CI pipeline) were correct.
   Agent 3's findings (Pollinator/perfhammer/WireMock cover Insights)
   were ALL false — confused Customer Service Management with Rovo
   Insights. **Always verify agent claims against source.**

2. **The previous "Test coverage" section understated reality on count
   (9 → 16 files, ~50 → 97 tests) but overstated reality on completeness**
   by computing only an LoC ratio without acknowledging missing layers.

3. **Naming collisions are a real failure mode.** "Insights" appears in
   at least 5 unrelated features: Rovo Insights, ChartInsights,
   HamInsights, SurveyInsights, AgentStudio Insights, plus CsmEvaluation
   adjacent. Future PRs must verify file paths, not name matches.

4. **Unit-test coverage being strong does not mean the system is
   well-tested.** 97 unit tests with 0 integration / 0 load / 0 chaos
   tests means production behavior is empirically untested. The cache
   mechanism is tested 3.6× (LoC ratio); the cache *under concurrent
   stampede* is not tested at all.

5. **CI auto-pickup is the most underappreciated property.** Adding
   any new test under ``modules/product/rovo/rovo-extras-impl/src/test/``
   automatically runs in ``unit-tests-rovo`` shard on every PR. No
   pipeline edit needed. This is why "every B-bundle adds a test" is
   cheap to enforce.

6. **The v3.3 plan's perf claims (p50/p95/p99 wins) cannot be repo-
   validated.** They live in production telemetry only, because there is
   no load test. T2 above is the prerequisite for falsifiable perf claims.

Verification audit log
========================

Every claim in this document has been verified against the source. Verification details:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Claim
     - Verification source
   * - 6 (not 7) insight types
     - ``InsightType.kt`` enum has exactly 6 entries; ``llmresponse/`` has 6 files + Common.kt; ``@JsonSubTypes`` lists 6
   * - 4 cache types
     - ``rovo-api/insights/`` directly contains the 4 ``-Cache`` files
   * - File LoC counts
     - All from ``wc -l`` on actual source
   * - REST paths
     - Read from ``RovoInsightsV1Controller.kt`` (subagent)
   * - Statsig flag names
     - Found in ``RovoInsightsGenerationTaskHandler`` (subagent)
   * - Cache TTLs
     - Read from ``RovoInsightsCacheImpl`` + ``RovoInsightsTaskCacheImpl`` (subagent)
   * - Generation timeout 240s
     - ``RovoInsightsServiceImpl.kt:569`` ``GENERATION_TIMEOUT_MILLIS = 240_000``

Open questions — RESOLVED 2026-05-02
=========================================

All 4 prior open questions verified in source:

* ✅ **Pebble template path EXISTS.** Verified: 6 templates at
  ``modules/product/rovo/rovo-impl/src/main/resources/templates/rovo/insights/v1/<type>.pebble``
  (company-insights, emerging-with-your-team, follow-up-insights, meeting-insights,
  recognition-insights, your-trending-work). Plus build-output copies in
  ``build/resources/main/templates/rovo/insights/v1/``.

* ✅ **Pebble + InsightPromptRegistry are COMPLEMENTARY, not mixed.**
  Verified: ``InsightPromptRegistry: Map<InsightType, String>`` in ``Common.kt`` is a
  per-type **instruction string** built by concatenating ``resourceSourcesInstructionsPrompt``
  + ``typeExamples`` (inline Kotlin strings). The Pebble template provides the LLM
  prompt **structure**; the registry provides the per-type **payload variables**.
  Pebble interpolates the registry value into ``{{ promptInstructions }}`` placeholders.

* ✅ **AgentStudio Insights ≠ Rovo Insights.** Verified: ``AgentStudioInsightsConfigurationGraphQLType``
  is a generated GraphQL type used by ``AgentStudioReportService`` (in
  ``modules/product/agentstudio/agentstudio-impl/``). It powers **AgentStudio Reports**
  (analytics on agent usage, conversation success rates, etc.), NOT the Rovo Insights
  feature documented here.

* ⚠️ **Custom ADF extension *production* verified; *consumption* still unverified.**
  Backend confirmed: the 3 extension types (``insight:linkCard``, ``insight:profileGroup``,
  ``insight:linkCardGroup``) are emitted by 3 builders in ``rovo-extras-impl/.../insights/adf/``
  and verified in ``AdfBuildersTest``. Frontend renderer code is in a separate repository
  so cannot be cross-checked here. Confidence: **production verified, rendering assumed
  from naming + test evidence**.

