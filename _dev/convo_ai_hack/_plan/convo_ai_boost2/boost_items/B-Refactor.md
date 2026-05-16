# B-Refactor — Architecture & Code-Quality Refactor Workstream

> Part of [BOOST Plan v1](../BOOST_PLAN_v1.md). 6 items.
> **Goal anchor:** Dev velocity (LoC removed, PRs merged/wk) + reliability (consistent error handling) + capacity (R8 directly).

---

## R1 — Monolithic AsyncConfluenceRestClientImpl refactor

**File:** `modules/platform/client/client-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/client/confluence/AsyncConfluenceRestClientImpl.kt` (5,788 LoC)

**Problem:** A single class handles 200+ REST endpoints across 8+ content types (pages, spaces, comments, attachments, databases, whiteboards, folders, embeds). Each content type has near-identical CRUD patterns duplicated 15-20 times. Methods like `getPageById`, `getSpaceById`, `getBlogPostById` are 95% identical.

**Why it matters:**
- **Dev velocity:** Adding new content types requires 100+ LoC of copy-paste, bug-prone
- **Testing:** A single timeout-policy change requires updating 200+ methods
- **Reliability:** Drift between endpoints (some have retries, some don't) causes inconsistent failure modes

**Effort:** M (2-3 weeks)
**Impact:** Dev velocity (+8-12% reduced boilerplate), reliability (fewer copy-paste bugs), code-quality (-2,500 LoC after consolidation)
**Approach:**
1. Define generic `execute<T>(method: HttpMethod, path: String, body: Any?, responseType: Class<T>): Mono<T>`
2. Annotate each endpoint with `@ConfluenceEndpoint(path = "...", method = GET)` for routing-by-annotation
3. Wrap legacy method signatures with `@Deprecated` adapter layer for callers (zero-downtime migration)
4. Add unified retry/timeout policy via interceptor

**Risk:** Med — caller signatures may break. Mitigation: deprecation wrapper layer; per-method test coverage.

**Acceptance:** ≥1,500 LoC removed; ≥3 callers verified working via end-to-end test; no regression in `RovoChatService` confluence-tool latency.

---

## R2 — Type-erasure anti-pattern in SearchSlotsConfiguration

**File:** `modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/search/SearchSlotsConfiguration.kt:25`

**Problem:** `markdownableFileKnowledgeSources: List<Any>?` uses `Any` to break circular import with `FileUploadMetadata`. Callers must cast `Any` back to the correct type, breaking type safety. Future devs don't know the actual type.

**Effort:** S (3-5 days)
**Impact:** Quality (catch type errors at compile time), dev velocity (better IDE support)
**Approach:**
1. Create `MarkdownableKnowledgeSource` interface in a new `service-shared-api` module
2. Both `SearchSlotsConfiguration` and `FileUploadMetadata` depend on it (no circular import)
3. Migrate all callsites to use the typed interface

**Risk:** Low — multi-module coordination only; no behavior change.

**Acceptance:** All `as Any` / `as List<...>` casts on this field removed; type-safety enforced at compile time.

---

## R5 — REST endpoint versioning debt

**Files:** `modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/internal/`, `rest/v1/`, `rest/v2/`

**Problem:** Three versioning tiers with overlapping endpoints. v1 controllers are likely still routed by legacy clients, duplicating business logic. Bug fixes must be applied N times.

**Effort:** L (3-4 weeks: audit + sunset + transformation layer)
**Impact:** Dev velocity (-20% boilerplate if v1 sunset), reliability (single source of truth)
**Approach:**
1. Audit actual client traffic per endpoint (Splunk / metrics) to identify <5%-traffic versions
2. Sunset eligible v1 endpoints with 6-month deprecation notice + redirect
3. Replace duplicated v2 controllers with a transformation layer (request-DTO → canonical → response-DTO)

**Risk:** Med — legacy client breakage. Mitigation: 6-month deprecation; gradual redirect; alarm on legacy version traffic.

**Acceptance:** ≥30% of v1 endpoints deleted; transformation layer covers ≥80% of v2 endpoints.

---

## R6 — SQS / Aqui handler unification

**Files:** `modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/service/sqs/queue/`, `service/streamhub/` (7+ consumer implementations)

**Problem:** Multiple SQS / StreamHub consumers (ActivateProductCompletions, Provisioning, StreamHub events, Kamino bootstrap, widget lifecycle, etc.) with individual error handling, retry logic, observability. No unified pattern.

**Effort:** M (2-3 weeks; 7 handlers to migrate)
**Impact:** Reliability (consistent retry/timeout/DLQ), operational excellence (faster incident response), dev velocity (one shared pattern)
**Approach:**
1. Extract `AbstractMessageQueueHandler<T>` base class with:
   - Pluggable retry policy (`RetryPolicy`)
   - Pluggable DLQ policy (`DlqPolicy`)
   - Standardized observability spans (`@WithSpan`, MDC injection)
   - Standardized idempotency-key support (composes with R-6A)
2. Migrate 7 handlers one-by-one with backward-compat wrapper

**Risk:** Med — refactoring 7 handlers introduces regression risk. Mitigation: per-handler integration tests + soak test 48h with chaos injection.

**Acceptance:** ≥5 of 7 handlers migrated; consistent retry policy across all; M9 silent-bug counters consistent.

---

## R8 — TCS (Tenant Context Service) cache consolidation 🔴 TOP-3 ITEM

**Files:** `modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/domain/tenant/TcsRequestCache.kt`, `TcsProcessCache.kt`

**Problem:** Two separate caches both store tenant policy results. Unclear deduplication strategy; risk of stale data if one invalidates without the other. Likely 2× Redis roundtrips for same data.

**Effort:** M (2 weeks)
**Impact:** **Cost (−15-20% latency on permission checks)** + reliability (single invalidation path) + capacity (1 fewer Redis roundtrip per request)
**Approach:**
1. Inventory ALL callsites of both caches
2. Define unified `TcsCacheService` with explicit TTL + invalidation semantics
3. Migrate callers to single cache; deprecate the other
4. Detailed cache-hit-rate metric before/after

**Risk:** Low (clear semantics) — but cache-hit regression possible if TTL chosen incorrectly. Mitigation: cache-hit-rate metric + revert flag.

**Acceptance:** Cache-hit-rate ≥ baseline; permission-check p99 latency −15-20%; M11 LoC counter shows ~200 LoC removed.

**Compounds with:** L1 AsyncTenantContext (v7) — both reduce TCS round-trips.

---

## R10 — Tool-output schema validation framework

**Files:** implicit across `modules/platform/tool-registry/`, `modules/platform/tool-execution/`

**Problem:** Multiple tool types (MCP, Forge, OpenAPI) each have individual deserialization / validation logic. No unified `ToolOutputSchema` validation framework. Risk of LLM hallucination from malformed tool output (e.g., missing required field, wrong type).

**Effort:** M (2-3 weeks)
**Impact:** **Quality (fewer hallucinations from malformed tool output)** + cost (-5-10% retry tokens) + reliability (fail fast on bad tools)
**Approach:**
1. `ToolOutputValidator` interface w/ JSON-Schema-driven validation (jackson-jsonschema or kotlinx-serialization-jsonschema)
2. Centralize deserialization with error telemetry (per-tool malformed-output counter)
3. Pre-flight schema registration during tool-registry init
4. **Audit-mode** for first 14 days: log violations but don't block tool output (avoid over-strictness)
5. Enforce after audit-mode validation

**Risk:** Med — over-strict schemas may block valid tool responses. Mitigation: audit mode first; per-tool allowlist for known-loose schemas.

**Acceptance:** Per-tool malformed-output rate baselined; after enforcement, hallucination rate (M1 LLM judge) shows measurable improvement.

**Compounds with:** R-1B tool-error feedback (v7) — both close the LLM tool-error loop.
