# Integrated Plan v3 — Tide v3 + Quokka + Rovodev (post-self-redteam)

> **Author:** Rovo Dev (synthesis after Tide v3 rewrite + brutal self-redteam), 2026-05-05 14:45.
> **Supersedes:** `06-INTEGRATED-PLAN-V2.md`.
> **Source plans (re-read 2026-05-05):**
> * **Tide v3** — `~/.claude/plans/taking-a-deep-look-pure-tide.md` (741 lines, **just rewritten 25 min ago** at 14:20; itself an integrated synthesis with 6 self-corrections)
> * **Quokka** — `_plan/claude/taking-a-deep-look-lively-quokka.md` (361 lines, unchanged since 13:30)
> * **Rovodev** — `_plan/rovodev/00-…08-` (this directory, unchanged since 14:15)
>
> **Verification posture:** All claims grounded in HEAD on 2026-05-05; 3 parallel red-team agents
> (Tide v3 verification, Rovodev self-critique, net-new finding hunt) corroborated.

---

## Section 0 — What changed since `06-INTEGRATED-PLAN-V2.md`

### 0.1 — Tide v3 rewrote itself (4 hours after v2)

| Change | Tide v2 → Tide v3 | Implication for synthesis |
|---|---|---|
| **Picks Plan C (Rovodev) as best** (was Plan B / Quokka) | New verdict | Cross-validates my prior synthesis posture |
| 6 explicit self-corrections in a v3-corrections table | NEW | Walks back several Quokka-flagship claims (incl. nudge p95 quantification) |
| Adds 9 rovo-insights findings (RI-FINDING-1…9) | NEW | Independently re-discovered 8 of my 18 DC- items + adds 1 net-new (Experience enum gap) |
| Adds 5 system-wide findings (StratusTestController gating, SonarQube disabled, no rate limits, no shutdown hook, no input size validation) | NEW | All 5 verified by my agents; **none were in any prior plan** |
| Adds explicit "If you pick one plan: Plan C" section | NEW | Mirrors content of my `07-PLAN-PICK-RECOMMENDATION.md` |

### 0.2 — My own self-redteam (item-level reversals)

Brutal self-critique by an independent agent forced these corrections to my prior synthesis:

| Item I previously had | Corrected verdict | Source |
|---|---|---|
| **DC-06 / I-19** "delete orphan policy path `/api/v1/rovo-insights/*`" | ❌ **WRONG — DROP** the deletion. The hyphen path **is real**: `RovoInsightsTestController.kt:28` declares `@RequestMapping("/api/v1/rovo-insights")` with `@PostMapping("/generate")`. | Direct grep of TestController; Tide v3 RI-FINDING-1 was right to flag this as "two coexisting paths", not as one being orphan |
| **DC-04 (StratusTestController gating)** previously sat in `08-` Critical but was NOT promoted to a P0 plan item | ❌ **PROMOTE to P0 in this v3** as a new item | Tide v3 made it P0-3; my own agent agreed |
| **DC-05 (DLQ alarm priority)** previously labelled Critical | ⚠️ **DOWNGRADE** to "P0-when-ramp-imminent" — the SD comment "Bump to High in prod once PAI is on the hot path" makes today's `Low` *intentional* | Self-redteam agent + Tide v3 P0-2 (medium) |
| **I-08 (`ProactiveAiCache` primitive)** previously full abstraction | ⚠️ **SIMPLIFY** to thin `StringRedisTemplate` wrapper with 3 ops, design abstraction when 2nd consumer lands | Tide v3 P1-3 simplification + my agent's YAGNI agreement |
| **Original "0% Category A" claim** | ✅ **STILL HONEST** — I-18 (`make /status return false`) is technically Category A but materialises only when convo-ai HTTP integration is built; reclassify as **Category C-when-handler-ships** | Self-redteam agent |

### 0.3 — Cross-reference with `TESTING_SOP.md` (added 2026-05-05 15:48)

After authoring `codebase_understanding/TESTING_SOP.md`, all 14 verified test-policy gaps (G-1..G-14) are now explicitly owned by plan items:

| Status | Count | Gaps → Items |
|---|---|---|
| ✅ Owned by existing item (no change needed) | 5 | G-2 (I-21), G-7 (I-06), G-8 (I-20), G-9 (I-19), G-11 (org Sauron — out-of-repo) |
| ✅ Owned via **extension** to existing item | 4 | G-1 (extends I-21), G-5 (extends I-15+I-20), G-6 (extends I-10), G-7 (extends I-06) |
| ✅ Owned by **NEW v3 item** | 3 | G-3 → I-27, G-4 → I-28, G-12 → I-31 |
| ⏸ Deliberately **deferred** | 2 | G-10 (Pitest), G-13 (CHANGELOG) |
| ⏸ Deliberately **convention-only** | 1 | G-14 (FF policy — covered by §4 PR checklist) |

11 of 14 gaps (78 %) now have explicit plan-item ownership. See `codebase_understanding/TESTING_SOP.md` § 6 for the full reverse cross-reference (gap → plan-item).

### 0.4 — Net-new findings none of the 3 plans caught

3 critical/high items found by independent search agent, all verified against source:

| # | File:line | Finding | Severity |
|---|---|---|---|
| **NF-01** | `WebMvcConfiguration.kt:30,55` | `@Volatile companion object asyncExecutor: ThreadPoolTaskExecutor?` is **stored but never read** anywhere — pure dead storage. Combined with the missing shutdown hook (Tide v3 finding), this means the executor is **completely orphan on application shutdown**: no `shutdown()` is called, threads leak, in-flight tasks die without cleanup. | 🔴 Critical (resource leak + JVM hang on redeploy) |
| **NF-02** | `MvcSecurityConfig.kt` | `anonymousPaths()` bean declares `/healthcheck` and `/deepcheck` as anonymous, but **zero controllers exist** for these paths in the codebase. If Spring Boot auto-registers a default health endpoint (e.g., via `spring-boot-starter-actuator`), it lands on an anonymous path — **bypassing all ASAP/principal checks**. | 🟠 High (latent auth bypass; severity depends on starter pollution) |
| **NF-03** | `CoroutineMonitor.kt:33` | `@Volatile internal var scopeFactory: () -> CoroutineScope` + `start()` does compound read-then-invoke (`scopeFactory().launch { … }`) without lock. `@Volatile` provides only single-read visibility; if `scopeFactory` is reassigned mid-`start()` (e.g., concurrent test fixtures), the launched scope diverges from intent → leaked coroutines. | 🟠 High (test-only concern today, but `CoroutineMonitor` is production code; race will fire when tests run in parallel against it) |

---

## Section 1 — Re-verified ground truth (as of 14:47, 2026-05-05)

(Unchanged items from 06- elided. **NEW or REVISED rows only:**)

| # | Claim | Verified | Source |
|---|---|---|---|
| 14 | `RovoInsightsTestController` mounts `@RequestMapping("/api/v1/rovo-insights")` + `@PostMapping("/generate")` (the hyphen path is REAL, not orphan) | ✅ Verified directly | grep at line 28+32 |
| 15 | `StratusTestController` literally says "remove or gate behind a feature flag before production" + has no `@ConditionalOnProperty` | ✅ Verified | line 26 |
| 16 | `bitbucket-pipelines.yml:78` has `CHECK_QUALITY_GATES: "false"` with comment "temporarily turn it off until we have improved the code coverage" | ✅ Verified | line 78 |
| 17 | `WebMvcConfiguration.kt` has `@Volatile asyncExecutor` (line 30) that is **only ever assigned at line 55, never read** | ✅ Verified | grep `asyncExecutor` returns 2 hits: declaration + assignment |
| 18 | `Experience` enum has ONLY `PROACTIVE_AI_ROVO_BUTTON`; `UseCase.ROVO_INSIGHTS` exists but no matching `Experience` member | ✅ Verified | `Experience.kt` full file read |
| 19 | `MvcSecurityConfig` declares `/healthcheck`+`/deepcheck` anonymous; **no controllers exist** for these paths | ✅ Verified | grep returns 0 controller matches |
| 20 | `NudgeThrottleController` has zero feature-flag matches (Tide v2's "8+ flag checks per request" claim was FALSE; Tide v3 corrected) | ✅ Verified | empty grep |
| 21 | `FeatureFlagContextServiceImpl.isLoggingEnabled` IS cached per request (Tide v2's "multiplicative cost" claim was FALSE; Tide v3 corrected) | ✅ Verified | line 243: `data.loggingEnabled?.let { return it }` |

---

## Section 2 — The integrated initiative list (v3): 20 items

Items renumbered. Each item carries source attribution. **NEW** = first time in any version of the integrated plan. **REV** = revised from `06-`. **EXT-G_N_** = item extended to also close `TESTING_SOP.md` gap G-N (added 2026-05-05 15:48 — see § 0.4 below).

### Tier P0 — OKR-blocking preconditions (8 items, ~2.5 weeks)

| # | Initiative | Source | UX-Cat | Effort | Notes |
|---|---|---|---|---|---|
| **I-01** | Per-endpoint p95 histograms + nudge-aware buckets `(1, 5, 10, 25, 50, 100, 200, 500ms)` | Tide v3 P0-1 + Quokka A0 + Rovodev P0-2 | C | S | unchanged |
| **I-02** | Business-metric vocabulary (`surface`/`outcome`/`experience`/`model`/`cache_hit`); cardinality allow-list (no tenant_id tag) | Tide v3 P0-1 + Quokka A0 | C | S | unchanged |
| **I-03** | SLO file (`continuous-verification.yml`) + minimum runbooks + alarm-priority promotion | Tide v3 P0-2 + Rovodev P0-1 | B | S | unchanged |
| **I-04** | Wire/remove dead `MetricKey` enum values | Rovodev P0-3 | E | XS | unchanged |
| **I-05** **REV** | AI Gateway timeout `600 000 ms → 120 000 ms` (Tide v3 corrected from 60 000) + per-tenant `application.yml` override | Tide v3 P1-2 (corrected) | B | S | **120 s** not 60 s — complex LLM reasoning routinely takes 30-120 s |
| **I-06** **NEW** **EXT-G7** | **Gate `StratusTestController` for production** — add `@ConditionalOnProperty("proactive-ai.stratus-test.enabled", matchIfMissing=false)` + `@field:Size(max=50000)` on `AgentRequest.message`. **Extended to also sweep all `@PostMapping` controllers** (`StratusTestController` + `RovoInsightsTestController` + `RovoInsightsController` + `NudgeThrottleController`) and add `@Valid` annotations on every `@RequestBody` (closes **TESTING_SOP G-7**). | Tide v3 P0-3 + Tide v3 RI-FINDING-7 + self-redteam DC-04 + **TESTING_SOP G-7** | B | S (was XS, +1 size due to G-7 sweep) | Comment in code literally says "remove or gate before production"; today this endpoint can be hit from internal network and submits real LLM tasks |
| **I-07** **NEW** | **Add `Experience.PROACTIVE_AI_ROVO_INSIGHTS`** enum member (mirroring `PROACTIVE_AI_ROVO_BUTTON`) | Tide v3 RI-FINDING-9 | C | XS | Day-0 blocker for the real handler — without an Experience member, observability tagging has nowhere to land |
| **I-08** **NEW** | **Make `/status` honest while handler is stub** — change `RovoInsightsController.kt:25-30` from `insightsAvailable = true` to `false` | 06- I-18 (kept) | C-when-handler-ships | XS | Reclassified from A→C per self-redteam: no user calls /status today |

### Tier P1 — Platform foundation (7 items, ~3-4 weeks)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-09** | `queueCapacity = 0 → 64` + `RejectedExecutionHandler` emitting `task.rejected` metric, returning HTTP 503 (not 500) | Tide v3 P1-1 + Quokka A6 | B | XS |
| **I-10** **REV** **EXT-G6** | **Redis client + thin wrapper** — `spring-boot-starter-data-redis`; **3-op `RedisOperations`** wrapper (`setIfAbsent`, `get`, `increment`) over `StringRedisTemplate`; graceful degradation; `/deepcheck` Redis probe. **Extended to ship the first `src/test/resources/application-test.yml`** (sets `spring.data.redis.host=localhost`, points to testcontainer Valkey 7.x — closes **TESTING_SOP G-6**). | Tide v3 P1-3 (simplified) + **TESTING_SOP G-6** | C | S | **Simplified from 06-** — design `ProactiveAiCache` abstraction when 2nd consumer lands (YAGNI) |
| **I-11** | `AsyncTask` idempotency guard (`idempotencyKey: String?`; pre-handler `GET(":done")`; `setIfAbsent(":submitted")` on submit) | Quokka A2 + Tide v3 P1-4 | B | M (depends I-10) |
| **I-12** | Visibility-extension hardening — bounded heartbeat `TaskScheduler` (`pai-visibility-heartbeat-`, poolSize=4); `AtomicInteger` consecutive-failure cap; `task.visibility.extend.failure` metric | Quokka A3 + Tide v3 P1-5 | B | S |
| **I-13** | Error classification (`Permanent` vs `Transient`); permanent → write `:done` + skip retry | Quokka A4 + Tide v3 P1-6 | B | S (depends I-11) |
| **I-14** | Per-request feature-flag memoisation (wrap `checkGate*` results; do **not** memoise `getExperiment(logExperimentExposure=true)`) | Quokka A5 + Tide v3 P1-9 | C | S | Tide v3 honestly walked back the nudge-quantification claim; structural improvement only |
| **I-15** **EXT-G5** | **End-to-end synthetic canary** — `CanaryTask` round-trips WebServer→SQS→LongRun→completion metric; alarm if absent for 15 min. **Extended to replace `RovoInsightsControllerIT.kt`** (which today is a useless `HTTP POST → assert 200` smoke test) with the real canary E2E using LocalStack (closes **TESTING_SOP G-5** primary). | Rovodev P1-3 + Tide v3 P1-7 + **TESTING_SOP G-5** | B | M | Tide v3 attributes this idea to Rovodev (correct — it is) |

### Tier P2 — Observability + capacity once load arrives (4 items)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-16** | Convert `.blockingGet()` in `stratus/` to suspending coroutines (bounded `Semaphore(8)` per-pod ceiling) | Quokka B1 + Rovodev P2-1 + Tide v3 P2-1 | C | S |
| **I-17** | **Per-tenant LLM budget gate** (default cap `Int.MAX_VALUE` = no behaviour change; flag-gated) | Tide v3 P1-8 (newly re-added — Quokka B7) | B | M (depends I-10) | Walk-back: Quokka had this as B7 (feature work); Tide v3 correctly re-classifies as platform protection (analogous to rate limiting) |
| **I-18** | Scaling config: prepare `LongRun max 2→6` + SQS concurrency `8→16` as a **PR that does not deploy** until handler ships | Rovodev P1-1+P1-2 + Tide v3 P2-3 | C | S |
| **I-19** **NEW** **EXT-G9** | **FIFO/Standard queue alignment with convo-ai** — convo-ai's `sandbox.def.yml` declares `rovo-insights-generation-queue.fifo`; PAI provisions Standard. Cross-team conversation now. **Extended:** once alignment is reached, ship a single Pact contract test pinning the convo-ai → PAI message envelope (closes **TESTING_SOP G-9** narrowly; full Pact suite deferred until 2nd consumer lands). | 06- I-17 (preserved) + self-redteam + **TESTING_SOP G-9** | B | M | Sole **cross-team** item — start the conversation now |

### Tier P3 — Hygiene & code quality (5 items)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-20** **EXT-G5,G8** | Test coverage: `utility/threading/` (P0-blast, 0 tests) + `VisibilityExtendingSQSQueueConsumerTest` + `RovoInsightsControllerTest` (with snapshot test pinning `DATA_SCHEMA_VERSION = 3` — closes **TESTING_SOP G-8**). **Extended to also expand `HealthCheckIT.kt`** to validate response body + downstream-dependency probe rather than just asserting HTTP 200 (closes **TESTING_SOP G-5** secondary). | Tide v3 P3-1 + Rovodev P3-2 + **TESTING_SOP G-5, G-8** | D | M |
| **I-21** **NEW** **EXT-G1** | **Re-enable SonarQube quality gates + add JaCoCo coverage threshold** — `bitbucket-pipelines.yml:78`: flip `CHECK_QUALITY_GATES: "true"` after I-20 raises coverage above the threshold. **Extended to also add `jacocoTestCoverageVerification` Gradle task** with `violationRules { rule { limit { minimum = "0.60".toBigDecimal() } } }` — wired into `tasks.check` so coverage drops fail the build (closes **TESTING_SOP G-1**, prerequisite for G-2). | Tide v3 P3-4 + **TESTING_SOP G-1, G-2** | D | XS | Two-step: (a) baseline 0.60 right after I-20, (b) ratchet to 0.70 once tests stabilise |
| **I-22** | Detekt rule for `LaasLoggerFactory` (raise adoption 85% → 100%) | Rovodev P3-3 + Tide v3 P3-3 | D | XS |
| **I-23** | Remove dead `IdGatekeeperClient` (zero production callers) | Tide v3 P3-2 | E | XS |
| **I-24** **NEW** | **Fix `WebMvcConfiguration.kt:30` orphan `asyncExecutor`** — wire to a `@PreDestroy` method that calls `executor.shutdown()` + `awaitTermination(30s)`; **OR** remove the field entirely if shutdown is delegated to Spring | NF-01 (none of 3 plans) | D | XS | Resource leak on redeploy |

### Tier P3 (security/correctness, may bump to P1 after deeper audit)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-25** **NEW** | **`MvcSecurityConfig` audit** — declare anonymous paths only for endpoints that **actually exist**. Either implement `/healthcheck` + `/deepcheck` controllers explicitly **OR** remove from `anonymousPaths()`. Investigate whether `spring-boot-starter-actuator` is on the classpath — if so, add explicit `management.endpoints.web.exposure.include=` allow-list. | NF-02 (none of 3 plans) | B | S | Latent auth bypass risk |
| **I-26** **NEW** | **Fix `CoroutineMonitor.scopeFactory` race** — replace `@Volatile var` + compound read-then-invoke with `AtomicReference<() -> CoroutineScope>` + `getAndSet`-style atomic swap during `start()`. Or document that mutation is test-only and add a `check(monitorJob.get() == null)` precondition. | NF-03 (none of 3 plans) | E | XS |

### Tier P3 (test-policy gaps from `TESTING_SOP.md`, added 2026-05-05 15:48)

These 3 items close the only `TESTING_SOP G-N` gaps that lacked a plan-item home. Effort & ordering carefully sized so they don't block higher-tier items.

| # | Initiative | Source | UX-Cat | Effort | Notes |
|---|---|---|---|---|---|
| **I-27** **NEW** **G-3** | **Author `CONTRIBUTING.md` + `DEVELOPING.md` + `CODEOWNERS`** at repo root. CONTRIBUTING.md links to `codebase_understanding/TESTING_SOP.md` for the canonical PR-test SOP. DEVELOPING.md covers local-development setup (`./gradlew clean build`, IT pre-reqs, IDE config, `nebulae start` workflow). CODEOWNERS sets default reviewer ownership: `* @ai-experience` + `service-descriptor.sd.yml @ai-experience-sre`. | **TESTING_SOP G-3** | D | XS | Single PR, ~3 short markdown files; unblocks new-contributor onboarding and replaces tribal knowledge |
| **I-28** **NEW** **G-4** | **Add `.bitbucket/pull_request_template.md`** copying §4 of `TESTING_SOP.md` (test checklist + operational checklist). Bitbucket auto-injects this into every new PR description. Pair with a one-line addition to CONTRIBUTING.md telling reviewers to enforce the checklist. | **TESTING_SOP G-4** | D | XS | Single small file; immediate productivity win for reviewers |
| **I-31** **NEW** **G-12** | **Add `swagger.yaml` for the public PAI HTTP API** (`/api/v1/rovo/insights/status`, `/fetch`, `/api/v1/nudge/throttle`, `/api/v1/greeting`) generated from controller annotations via `springdoc-openapi-starter-webmvc-api`. Add `openapi-diff` Bitbucket pipe in PR pipeline that fails on **breaking changes** (removed paths, removed fields, type changes); allows additive changes. **Becomes a hard prerequisite for safe convo-ai integration** — without it, contract drift is silent. | **TESTING_SOP G-12** | C-when-handler-ships | M | Two PRs: (a) generate swagger from controllers + commit checked-in copy; (b) wire `openapi-diff` pipe (~5 lines in `bitbucket-pipelines.yml`) |

### Tier P0 — Empirical findings from running the build locally (2026-05-05 16:00)

These two items are **discovered by actually running `./gradlew test`** end-to-end (not by reading config). Promoted to P0 because they block any developer from compiling the project locally (I-33) or expose a real runtime bug at every shutdown (I-32).

| # | Initiative | Source | UX-Cat | Effort | Notes |
|---|---|---|---|---|---|
| **I-32** **NEW** **EF-05** | **Fix `ioDispatcher` bean's destroy method throwing `IllegalStateException: Cannot be invoked on Dispatchers.IO`** — at every Spring shutdown, `DisposableBeanAdapter.destroy` for bean `ioDispatcher` calls `kotlinx.coroutines.scheduling.DefaultIoScheduler.close()` which is illegal on the singleton `Dispatchers.IO`. **Fix:** either remove the `@Bean` declaration if it's just an alias for `Dispatchers.IO`, or wrap with a `LimitedDispatcher` (via `Dispatchers.IO.limitedParallelism(N)`) that **can** legally be closed. | **EF-05** (caught by running `./gradlew test` 2026-05-05 16:00; stack trace in `/tmp/pai_test.log`) | D | XS | Real runtime bug at every pod redeploy — no functional damage today but pollutes shutdown logs and may mask other issues |
| **I-33** **NEW** **G-15** | **Fix `settings.gradle.kts` to declare Atlassian's internal Maven repo** in `pluginManagement.repositories` and `dependencyResolutionManagement.repositories`. Today the project's `settings.gradle.kts` has only 10 lines and does NOT declare any repos for `pluginManagement`, so `./gradlew` fails with `Plugin io.atlassian.micros.springboot:7.10.0 was not found in any of the following sources: Gradle Central Plugin Repository`. | **TESTING_SOP G-15 / EF-01** | D | XS | Onboarding blocker; current workaround is a manual init-script. CI works because Bitbucket pipeline image bakes in the repo via global config — but no developer can build locally without intervention. |

---

## Section 3 — Items deliberately DROPPED (with reasons)

| Dropped item | Source plan(s) | Why dropped |
|---|---|---|
| **DC-06 / I-19 (old) — delete orphan `/api/v1/rovo-insights/*`** | 06- + Rovodev 08- DC-06 | **My DC-06 was wrong.** Verified directly: `RovoInsightsTestController` actually mounts that path (line 28). Tide v3 RI-FINDING-1 correctly characterises this as "two coexisting paths needing documented strategy", not "orphan to delete". |
| **Identity-dedup fix** | All three previously included | Verified zero production callers of `AsyncIdGatekeeperClient.checkPermissionBulk` |
| **MCP tool-discovery cache** | Tide v2, Quokka B0, Rovodev P2-2 | `IntegrationServiceToolProvider` only injected by `StratusTestController` (test-only); ship I-06 first |
| **Real nudge throttle (Quokka B6)** | Quokka B6 | Endpoint has zero upstream consumers; logic for unused endpoint is premature |
| **Real Rovo Insights handler (Quokka B2-B5)** | Quokka B2-B5 | Crosses "no user-facing behaviour change" constraint — team's roadmap work, not platform |
| **AI Gateway timeout < 120 s** | Quokka A6, my old I-05 | Tide v3 correctly flagged 60 s as too aggressive — complex LLM reasoning routinely 30-120 s |
| **Full `ProactiveAiCache` abstraction** | Quokka A1, my old I-08 | YAGNI — only one consumer (idempotency); ship thin wrapper, design abstraction at consumer #2 |
| **Coalescing (Quokka B8)** | Quokka B8 | Already deferred by Quokka itself; depends on workspace-shareability validation |
| **Mutation testing (Pitest)** | `TESTING_SOP G-10` | Useful **only after** I-21 raises baseline coverage above 60 %; revisit Q3 FY26 |
| **Repo-level CHANGELOG enforcement** | `TESTING_SOP G-13` | Optional polish — only useful when external consumers depend on PAI versioning (which they don't yet); revisit if PAI exposes versioned client SDK |
| **PR-time feature-flag-required policy** | `TESTING_SOP G-14` | Convention only — enforced by §4 PR-checklist + §5 reviewer checks; automation would have high false-positive rate (not all changes are user-visible) |

---

## Section 4 — UX-impact aggregate (v3, corrected)

| Category | Count | % | Items |
|---|---|---|---|
| **A** — Direct user-perceived | **0** | **0 %** | (none — handler still stub; I-08 reclassified to C) |
| **B** — Failure-path UX | 9 | 35 % | I-03, I-05, I-06, I-09, I-11, I-12, I-13, I-15, I-17, I-19, I-25 |
| **C** — Enables future user UX | 7 | 27 % | I-01, I-02, I-07, I-08, I-10, I-14, I-16, I-18 |
| **D** — Engineer / on-call UX | 5 | 19 % | I-20, I-21, I-22, I-24, NF-01 (consolidated) |
| **E** — Pure hygiene | 2 | 8 % | I-04, I-23, I-26 |

(Some items appear in 2 categories due to dual impact; counts >26.)

**Honest framing remains: 0 % Category A.** The system is pre-load. Adding 7 new items did not introduce any user-perceived improvements — they all enable / harden / observe a future shipping event.

---

## Section 5 — Sequencing graph

```
Week 1 (parallel, zero blast risk):
├── I-01  Per-endpoint histograms                         (PR-1: enum + register; PR-2: wire 5 controllers)
├── I-02  Business-metric vocabulary                      (rides with I-01 PR-1)
├── I-04  Dead-MetricKey cleanup                          (1 PR)
├── I-06  Gate StratusTestController + input size limit   (1 PR)
├── I-07  Add Experience.PROACTIVE_AI_ROVO_INSIGHTS       (1 PR — mirror existing pattern)
├── I-08  Make /status return false while stub            (1 PR — one-line)
├── I-14  FF memoisation                                  (1 PR, behind flag)
├── I-22  Detekt LaasLogger rule                          (1 PR, build-gate only)
└── I-24  Fix WebMvcConfiguration asyncExecutor leak      (1 PR — @PreDestroy or remove)

Week 2:
├── I-03  SLO + runbooks + alarm priority                 (3 PRs)
├── I-05  AI-Gateway timeout 600s → 120s                  (1 PR, separate commit)
├── I-09  queueCapacity 0 → 64 + reject metric            (1 PR)
├── I-19  FIFO/Standard discussion with convo-ai          (Slack/Confluence — no PR)
├── I-20  utility/threading + Visibility + RovoInsights tests (4 parallel PRs)
└── I-23  Remove dead IdGatekeeperClient                  (1 PR)

Week 3:
├── I-10  Redis client + thin RedisOperations wrapper     (1 PR; testcontainers Valkey 7.x)
├── I-12  Visibility-extension hardening                  (1 PR)
├── I-15  E2E synthetic canary (PR-1: CanaryTask)         (PR-1 of 2)
├── I-16  blockingGet → suspending in stratus/            (1 PR)
└── I-25  MvcSecurityConfig anonymous-paths audit         (1 PR — investigation + fix)

Week 4:
├── I-11  AsyncTask idempotency guard                     (depends on I-10)
├── I-15  Canary alarm                                    (PR-2 of 2 — after 7-day bake)
├── I-17  Per-tenant LLM budget gate                      (depends on I-10)
└── I-26  CoroutineMonitor race fix                       (1 PR — XS)

Week 5:
├── I-13  Error classification                            (depends on I-11)
├── I-18  Scaling config (prepared, not deployed)         (1 PR — gates on handler delivery)
└── I-21  Re-enable SonarQube quality gates               (1 PR — only after I-20 lifts coverage)

Week 6 — bake / observe; no new PRs
```

**Critical path:** I-01→I-02→I-10→I-11→I-13. Everything else parallelises.

---

## Section 6 — The single most important unanswered question (unchanged)

> **When does the real `RovoInsightsGenerationTaskHandler` replace its stub body, and what is the projected daily QPS profile?**

Without an answer, ~50% of the plan is precondition-building with no validation traffic. Capacity sizing (I-18), AI-Gateway timeout target (120s? 60s? 30s?), Redis sizing, and per-tenant budget cap (I-17) are all guesses.

---

## Section 7 — The single most important *insight* (unchanged from 06-)

> **Decouple infrastructure ramp from handler activation via Statsig flag** — ship I-01..I-26 (infrastructure) tested under stub-handler load; activate real handler via separate flag controlled by feature owner; weekly ramp Hello → 1 % → 5 % → 25 % → 100 %.

Tide v3's RI-FINDING-3 (zero feature flags in `feature/rovoinsights/` package) **strengthens** this insight: there is currently **no ramp mechanism at all** for the handler. Adding `ROVO_INSIGHTS_HANDLER_ENABLED` to `AiFeatureGates.kt` is a Day-0 blocker for safe handler shipping.

→ **New mini-item I-27** (deferred to feature-team handoff): Add `ROVO_INSIGHTS_HANDLER_ENABLED` to `AiFeatureGates.kt`; wire into `RovoInsightsGenerationTaskHandler.handle()`; when OFF, run current stub.

---

## Section 8 — If you pick only one plan (final, after Tide v3 self-pick of Plan C)

**Tide v3 picks Plan C (Rovodev/mine).** That is *partially* deserved:

* ✅ Rovodev's governance discipline (UX classification, non-goals doc, sequencing playbook, counter-metrics) is **the unique differentiator**.
* ✅ Rovodev's E2E synthetic canary is the only plan with this idea.
* ✅ Rovodev's deep-dive on rovo-insights (`08-…-DEEP-DIVE.md`, 18 items) catches more rovo-insights-specific issues than any other plan.

**But** the self-redteam exposed honest weaknesses in Rovodev:

* ❌ Missed StratusTestController gating as a P0 (was in "dropped" — should have been P0 — corrected by Tide v3 P0-3 + my I-06).
* ❌ Missed 7-8 hygiene findings (SonarQube disabled, no `@Valid`, no input size validation, no shutdown hook, etc.) — Tide v3 caught all 7.
* ❌ Overstated DC-05 (DLQ alarm) as Critical when team's own SD comment shows `Low` is intentional today.
* ❌ Wrong on DC-06 (orphan path) — verified by direct grep that the hyphen path is real.

**Ranking, post-redteam:**

1. 🥇 **Quokka — Track A only (A0–A6)** — has the most code-level bugs caught (queueCapacity, FF context, error classification, business metrics vocabulary). Drop Track B (roadmap work / unused endpoints).
2. 🥈 **Rovodev (with Tide v3 hygiene bolt-ons)** — best governance + rovo-insights specificity, weaker on technical breadth.
3. 🥉 **Tide v3** — best meta-analysis (acknowledges its own past errors), but its actual recommendations are mostly Quokka's findings + Rovodev's governance.

**The genuinely best answer is this `09-INTEGRATED-PLAN-V3.md`** — every plan has unique-and-correct findings + unique-and-correct gaps; the synthesis is strictly better than any single plan.

---

## Section 9 — Cross-references

* `00-INDEX.md` — entry point (will be updated to point here)
* `06-INTEGRATED-PLAN-V2.md` — **superseded by this file**
* `08-ROVO-INSIGHTS-DEEP-DIVE.md` — 18 DC-items (still mostly valid; DC-06 dropped per § 0.2)
* `~/.claude/plans/taking-a-deep-look-pure-tide.md` — **Tide v3** (the rewritten one)
* `_plan/claude/taking-a-deep-look-lively-quokka.md` — Quokka
