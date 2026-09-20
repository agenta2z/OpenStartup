# Proactive AI Platform — Code Quality & Refactor Opportunities

**Investigation Date:** 2026-05-05  
**Codebase State:** 7,765 source LoC / 6,313 test LoC / 27% test:source ratio  
**Bus Factor:** Zhangbin Cheng 82% of commits (RISK-001)  
**Config Churn:** 9/10 top files are infra/config (confirmed)

---

## FINDING 1: Dead Metric Keys (Easy Win)
**File:** `src/main/kotlin/io/atlassian/micros/proactiveai/service/metric/MetricKey.kt:11-12`  
**Current State:**
- `TENANT_CONTEXT_BUILD_SUCCESS` and `TENANT_CONTEXT_BUILD_ERROR` are declared but **never emitted in source code**
- Only appear in test mock assertions (5 occurrences in tests)
- `PROACTIVE_TEST_LATENCY` is declared but not used; only `PROACTIVE_TEST_COUNT` is live

**Proposed Change:**
- Remove lines 11-12 from MetricKey enum (2 LoC)
- Remove unused `HistogramMetric.PROACTIVE_TEST_LATENCY` entry if histogram buckets are not wired
- Update tests to use `PROACTIVE_TEST_COUNT` only

**Technical Impact:**
- **LoC reduction:** −2 lines in enum, −4 lines in tests
- **Dead code eliminated:** 2/7 MetricKey entries (28%)
- **No contributor friction:** purely internal cleanup
- **Metric cardinality:** 5 live metrics instead of 7

**PR Sequence:** 1st (no dependencies; unblocks metrics catalog documentation update)

---

## FINDING 2: LaasLogger Enforcement via Detekt Rule (High Leverage)
**File:** `src/main/kotlin/io/atlassian/micros/proactiveai/logging/LaasLogger*.kt`  
**Current State:**
- ADR-009 states: *"enforced by code review, not by lint"*
- **21 LaasLogger.getLogger calls** vs. **3 raw LoggerFactory.getLogger calls** in source
- Non-compliance: `WebServiceController.kt:53`, `StratusTestController.kt:34`, `RequestContextValues.kt` (companion object loggers)
- ~85% adoption without enforcement

**Proposed Change:**
1. Create a new detekt rule `NoRawLoggerFactory` in `build.gradle.kts`:
   ```kotlin
   detekt {
     rules {
       ruleSet("custom") {
         "NoRawLoggerFactory" {
           active = true
           autoCorrect = true
         }
       }
     }
   }
   ```
2. Rule logic: Forbid `org.slf4j.LoggerFactory.getLogger` in source (allow only in tests / logging module)
3. Fix the 3 violations in: `WebServiceController.kt`, `StratusTestController.kt`, `RequestContextValues.kt`

**Technical Impact:**
- **Enforcement improvement:** 0% → 100% via CI gate
- **LoC cost:** +~40 LoC (detekt rule impl) but saves ~10 LoC (fix violations)
- **Contributor onramp:** Strong signal for new contributors
- **Bus factor mitigation:** Reduces code-review burden on Zhangbin

**PR Sequence:** 2nd (depends on Finding 1; enables testing of metrics)

---

## FINDING 3: Controller Base Class / Shared Interceptor (Medium Win)
**Files:** All 5 controllers
**Current State:**
- **Identical boilerplate in 5 controllers:**
  - `private val log = LaasLoggerFactory.getLogger(this::class.java)` (repeated in all)
  - `infoWithContext` log calls with identical context structure
  - `@PostMapping` / `@GetMapping` patterns with identical header extraction
- **RovoInsightsTestController & StratusTestController:** Both extract `cloudId` + `user` + `requestId`
- **Inconsistency:** WebServiceController uses `LoggerFactory` directly (not `LaasLoggerFactory`)

**Proposed Change:**
Create a `BaseController` trait:
```kotlin
abstract class BaseController {
    protected val log = LaasLoggerFactory.getLogger(this::class.java)
    
    protected fun logRequest(
        endpoint: String,
        cloudId: String? = null,
        userId: String? = null
    ) = log.infoWithContext("Request received", mapOf(
        "endpoint" to endpoint,
        *listOfNotNull(
            cloudId?.let { "cloud_id" to it },
            userId?.let { "user_id" to it }
        ).toTypedArray()
    ))
}
```
- Migrate all 5 controllers to extend `BaseController`
- Extract common header-extraction logic into `@ControllerAdvice` or interceptor

**Technical Impact:**
- **Boilerplate reduction:** ~15 LoC per controller (75 LoC saved across 5)
- **Test:source ratio:** +0.5% (LoC reduction without test changes)
- **Consistency gain:** Uniform logging / header handling
- **Contributor friction:** −1 (new contributors have one pattern to learn)
- **Bug risk:** Minimal (trait extraction, no logic change)

**PR Sequence:** 3rd (after LaasLogger enforcement in Finding 2)

---

## FINDING 4: MicrosEnvironmentType Migration (ADR-008 Completion)
**File:** `src/main/kotlin/io/atlassian/micros/proactiveai/config/MicrosEnvironmentConfig.kt`  
**Current State:**
- ADR-007 (current): reads environment as string, converts via `fromString()`
- **ADR-008 (open question):** migrate to typed `@Value("${micros.environment.type}")` bean injection
- **Status:** "Open question (proposed, not accepted)" per 14-architectural-decisions.rst
- **Size estimate:** ~20 LoC change (bean -> enum bean, update 5 injection sites)

**Proposed Change:**
1. Convert `MicrosEnvironmentConfig.microsEnvironment()` to return bean via Spring's enum support
2. Inject `MicrosEnvironmentType` directly into the 3-5 classes that currently use the string
3. Update `application.yml` to use enum-aware binding
4. **Decision:** Accept ADR-008, supersede ADR-007

**Technical Impact:**
- **Type safety:** String → enum at injection time (compile-time benefit)
- **LoC cost:** +8 (enum bean registration), −12 (removed fromString calls) = −4 net
- **Bus factor:** Reduces string-parsing risk; onboards new contributors to Spring patterns
- **Complexity:** Low; Spring has built-in enum support

**Blockers:** Verify Spring `@Value` enum binding works with Micros config injection

**PR Sequence:** 4th (independent; can run in parallel with Finding 3)

---

## FINDING 5: AsyncTaskHandler Base Implementation (Pattern Extraction)
**File:** `src/main/kotlin/io/atlassian/micros/proactiveai/task/AsyncTaskHandler.kt`  
**Current State:**
- Only **1 concrete implementation:** `RovoInsightsGenerationTaskHandler`
- Base interface defines optional `onSuccess()` / `onFailure()` hooks
- Logging pattern is **identical** in the single implementation:
  ```kotlin
  private fun logContext(...): Map<String, Any> = mapOf(
      "tenant_id" to ...,
      "account_id" to ...,
      "request_id" to ...
  )
  ```

**Proposed Change:**
1. Create abstract `BaseAsyncTaskHandler<T>` extending `AsyncTaskHandler<T>`:
   ```kotlin
   abstract class BaseAsyncTaskHandler<T : AsyncTask> : AsyncTaskHandler<T> {
       protected val log = LaasLoggerFactory.getLogger(this::class.java)
       
       protected fun contextMap(executionContext: AsyncTaskExecutionContext): Map<String, Any> =
           mapOf(
               "tenant_id" to executionContext.tenantId,
               "account_id" to executionContext.user.getAccountId().toString(),
               "request_id" to executionContext.requestId
           )
       
       // Default onSuccess/onFailure implementations
       override suspend fun onSuccess(...) { ... }
       override suspend fun onFailure(...) { ... }
   }
   ```
2. Migrate `RovoInsightsGenerationTaskHandler` to extend `BaseAsyncTaskHandler`

**Technical Impact:**
- **Boilerplate reduction:** ~20 LoC per handler
- **Future-proofing:** Next async task handler requires only `handle()` implementation
- **Test:source ratio:** +0.1% (small change)
- **Contributor onramp:** Clear template for the next async task type

**PR Sequence:** 5th (independent; sets stage for next async feature)

---

## FINDING 6: Controller Test Coverage (Quantified Opportunity)
**Files:** All 5 controllers
**Current State:**
- **0/5 controllers have unit tests**
- 1 acceptance test exists: `NudgeThrottleControllerAcceptanceTest.kt` (covers 1 of 5 controllers)
- Test:source ratio is 27% overall, but controllers specifically: **0% coverage**
- Total controller LoC: ~250 lines (estimated)

**Proposed Change:**
Phase 1 (immediate):
- Add unit test for `WebServiceController.getResponse()` — 3 test cases:
  - Feature gate ON → returns greeting
  - Feature gate OFF → returns greeting (gate doesn't affect output)
  - Metric emission verified
- **LoC cost:** ~40-50 test lines

Phase 2 (next sprint):
- Add integration tests for async controllers (`RovoInsightsTestController`, `StratusTestController`)
- Each: 20-30 test lines
- Total Phase 2: ~80 LoC

**Technical Impact:**
- **Phase 1 test:source:** 27% → ~27.5% (minimal immediate impact)
- **Phase 2 test:source:** 27.5% → ~28% (cumulative)
- **50% controller coverage:** Requires ~100 test LoC
- **80% controller coverage (reasonable target):** Requires ~150 test LoC
- **Bus factor:** Reduces Zhangbin's code-review load on controller changes
- **Regression risk:** Eliminates class-load and HTTP-binding bugs

**PR Sequence:** 6th (can start in parallel with Finding 3; uses `BaseController` if available)

---

## FINDING 7: Process Gap Analysis (From Part 7, ch. 13)
**Files:** Per 13-full-history-catalog.rst Part 7
**Current State:**
- **Process gaps identified:**
  - No-ticket PRs (PRs without AIX tickets) exist
  - Declined PRs in history
  - Reverted changes in history
- **Architectural code-smells NOT surfaced by Part 5 (strategic PRs):**
  - No evidence of architectural debt from no-ticket PRs
  - Single recent removal: "remove prod for testing" (bitbucket-pipelines.yml) — intentional, not a code-smell

**Proposed Action:**
- **Do NOT propose undoing removals** (per instruction)
- Strategic PRs appear to have captured the major architectural decisions
- Current process gaps (no-ticket PRs) suggest: either PRs are too small to require tickets, or there's a process gap in ticket creation
- **Recommendation:** This is a **process issue, not a code issue** — outside scope of this code-quality review

**Technical Impact:** None (process-level finding)

**PR Sequence:** Out of scope (requires team/process discussion)

---

## FINDING 8: Test Coverage Ratio Target & Feasibility
**Current State:**
- **27% test:source ratio** (6,313 test LoC / 7,765 source LoC)
- Healthy for early-stage service (per 15-velocity-and-debt.rst)
- Controllers are the **acknowledged gap** (per SYMBOL_INDEX.md § 1)

**Proposed Target:**
- **50% test:source ratio** (realistic, high-leverage)
- Requires: +~1,100 test LoC
- Primary focus: Controllers (Finding 6: 100 LoC), async handlers (30 LoC), integration scenarios (970 LoC)

**Cost-Benefit Analysis:**
| Metric | Current | Post-Findings 1–6 | Lift |
|--------|---------|-------------------|------|
| Test:source ratio | 27% | ~30% | +3pp |
| Dead code (MetricKeys) | 2/7 | 0/5 | −2 |
| LaasLogger enforcement | 85% | 100% | +15pp |
| Controller boilerplate | 5× | 1× (BaseController) | −75 LoC |
| Async handler boilerplate | 1× (stub) | 1× (inherited) | −20 LoC |
| Controller test coverage | 0% | 20% (Phase 1) | +20pp |
| Bus factor risk (Zhangbin) | 82% | ~75% | Mitigated |

**PR Sequence:** Cumulative effect of Findings 1–6 above

---

## SUMMARY TABLE (Sorted by Impact)

| Finding | Focus | File:Line | Change Type | LoC Δ | Impact | Priority | Effort |
|---------|-------|-----------|-------------|-------|--------|----------|--------|
| **1** | Dead MetricKeys | `MetricKey.kt:11-12` | Removal | −6 | Dead-code elimination; cleaner enum | 🟩 High | 30 min |
| **2** | LaasLogger Detekt | `build.gradle.kts` | Add rule + fix | −5 net | Enforcement; bus-factor mitigation | 🟩 High | 2 hrs |
| **3** | BaseController | All 5 controllers | Inheritance | −75 | Boilerplate; consistency; contributor onramp | 🟨 Medium | 3 hrs |
| **4** | MicrosEnvironmentType | `MicrosEnvironmentConfig.kt:13-19` | Refactor | −4 | Type safety; ADR-008 completion | 🟨 Medium | 1.5 hrs |
| **5** | BaseAsyncTaskHandler | `AsyncTaskHandler.kt` | Inheritance | −20 | Future-proofing; pattern extraction | 🟡 Low | 1.5 hrs |
| **6** | Controller Tests | `src/test/kotlin/` | Addition | +100 (Phase 1) | Coverage; regression prevention; load-testing | 🟨 Medium | 4 hrs (Phase 1) |
| **7** | Process Gaps | 13-catalog Part 7 | Analysis only | N/A | Process-level; out of scope | ⚪ N/A | N/A |
| **8** | Test Ratio Target | Cumulative | Guidance | +1,100 | Cumulative outcome of 1–6 | 🟡 Low | Ongoing |

---

## RECOMMENDED PR SEQUENCE

1. **PR #1: Remove dead metric keys** (Finding 1)
   - Reviewers: 1 (Zhangbin)
   - CI time: ~5 min
   - Merge time: Same day

2. **PR #2: Add Detekt LaasLogger rule + fix violations** (Finding 2)
   - Reviewers: 1 + arch review
   - CI time: ~10 min
   - Merge time: 1–2 days (rule requires consensus)

3. **PR #3: Extract BaseController trait** (Finding 3)
   - Reviewers: 1 + style review
   - CI time: ~10 min
   - Merge time: 1 day

4. **PR #4: Complete ADR-008 (MicrosEnvironmentType migration)** (Finding 4)
   - Reviewers: 1 + arch review
   - CI time: ~10 min
   - Merge time: 1–2 days (architectural decision)

5. **PR #5: Extract BaseAsyncTaskHandler** (Finding 5)
   - Reviewers: 1
   - CI time: ~5 min
   - Merge time: 1 day

6. **PR #6a: Controller unit tests (Phase 1 — WebServiceController)** (Finding 6)
   - Reviewers: 1
   - CI time: ~10 min
   - Merge time: 1 day

7. **PR #6b: Integration tests for async controllers (Phase 2)** (Finding 6)
   - Reviewers: 1 + QA review
   - CI time: ~15 min
   - Merge time: 2 days

---

## VERIFICATION & METRICS

**Post-Implementation Targets:**
- Test:source ratio: 27% → 30% (+3pp)
- Dead code: 2 MetricKeys → 0
- LaasLogger enforcement: 85% → 100%
- Controller boilerplate: 5 copies → 1 (BaseController)
- Controller test coverage: 0% → 20% (Phase 1) → higher (Phase 2)
- Bus-factor mitigation: Documented patterns reduce code-review load

**Reproducible Verification:**
```bash
# Verify dead metrics removed
grep -c "TENANT_CONTEXT_BUILD" src/main/kotlin/io/atlassian/micros/proactiveai/service/metric/MetricKey.kt

# Verify LaasLogger compliance (should be 0)
grep -r "LoggerFactory.getLogger" src/main/kotlin --include="*.kt" | grep -v LaasLoggerFactory | wc -l

# Verify test:source ratio
echo "scale=2; $(find src/test/kotlin -name '*.kt' | wc -l) / $(find src/main/kotlin -name '*.kt' | wc -l)" | bc

# Verify controller test coverage
find src/main/kotlin -name "*Controller.kt" | wc -l
find src/test/kotlin -name "*ControllerTest.kt" -o -name "*ControllerAcceptanceTest.kt" | wc -l
```

---

## NOTES

- **Finding 7 (Process Gaps):** Analyzed but outside scope; recommend team discussion on no-ticket PR policy.
- **Recently removed code (commit 8584920):** "remove prod for testing" — intentional config change, not a code-smell. No action needed.
- **ADR-007 vs. ADR-008:** Completing ADR-008 (Finding 4) effectively supersedes ADR-007 via type safety.
- **Detekt rule (Finding 2):** Rule implementation details assume standard detekt plugin; may need adjustment for custom rules setup.
