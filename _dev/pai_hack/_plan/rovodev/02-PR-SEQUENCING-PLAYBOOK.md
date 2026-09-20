# PR-Sequencing Playbook

> How to ship the 12 initiatives from
> [`01-PRIORITISED-INITIATIVES.md`](01-PRIORITISED-INITIATIVES.md)
> as a series of small, independently-reviewable PRs (no big-bang
> PRs).
>
> **Guiding principle:** every PR must be **mergeable on its own**
> without depending on a future un-merged PR. Each PR must be
> **rollback-safe** (can be reverted with no data migration).
>
> **PR-title convention:** `[<INITIATIVE-ID>][<AIX-TICKET>] <intent>`.
> Example: `[P0-2 / AIX-XXXX] Add ROVO_INSIGHTS_GENERATE_LATENCY histogram`.

---

## Format for each entry

* **Series**: ordered list of PRs.
* **Per PR**: `intent`, `files touched`, `LoC budget`, `review focus`,
  `rollback plan`, `prerequisite`, `acceptance criteria`.
* **Why split this way** — the rationale for the sequencing.

---

## PR-SEQ-P0-1 — SLO file + minimum runbooks

**Why split this way.** The SLO file change is independent of the
runbook content (one is YAML, one is Confluence). Splitting lets a
reviewer focus on threshold reasonableness without context-switching
to runbook prose.

### PR-1 — Author `continuous-verification.yml`

* **Intent.** Make SLOs visible in Tome.
* **Files touched.** New `continuous-verification.yml` at repo root.
  Update `bitbucket-pipelines.yml` if a CV step exists.
* **LoC budget.** ≤ 60.
* **Review focus.** Threshold reasonableness (start conservative).
  Mesh dependency `continuousVerification` field set to a real
  SLO contract.
* **Rollback plan.** Delete the file; no behaviour change in the
  service.
* **Prerequisite.** None.
* **Acceptance criteria.** Tome dashboard shows the two SLOs
  (web availability, generation queue age) within 24 h of merge.

### PR-2 — Runbook URLs in alarm `Description:` fields

* **Intent.** Make on-call know what to do when paged.
* **Files touched.** `service-descriptor.sd.yml` only.
* **LoC budget.** ≤ 30 (just `Description:` text edits).
* **Review focus.** Each `Description:` ends with a Confluence URL
  that resolves; URL points at a *runbook* not a *design doc*.
* **Rollback plan.** Revert; alarm text reverts to old TBD content.
* **Prerequisite.** Confluence runbook drafts exist (created
  out-of-band).
* **Acceptance criteria.** Each alarm description in
  `service-descriptor.sd.yml` contains a `https://hello.atlassian.net/wiki/...` URL.

### PR-3 — Promote DLQ alarm to `Priority: Medium`

* **Intent.** Make DLQ depth wake on-call (today it doesn't).
* **Files touched.** `service-descriptor.sd.yml` (one alarm only).
* **LoC budget.** ≤ 5.
* **Review focus.** Confirm the team's on-call rotation is ready
  for medium-priority pages.
* **Rollback plan.** Revert; alarm goes back to Low.
* **Prerequisite.** PR-2 merged (description points at a real runbook).
* **Acceptance criteria.** Sauron / micros surfaces the alarm at
  Medium priority.

---

## PR-SEQ-P0-2 — Per-endpoint p95 histograms

### PR-1 — Add histogram enum entries + Spring registration

* **Intent.** Define the metric surface; no controller wiring yet
  so the PR is small and reviewable.
* **Files touched.**
  `service/metric/HistogramMetric.kt`,
  `service/metric/MetricsService.kt` (only if a method signature
  needs adding),
  `application.yml` (`histograms:` block).
* **LoC budget.** ≤ 80.
* **Review focus.** Histogram bucket choice (use existing
  `PROACTIVE_HISTOGRAM_BUCKETS` to be consistent).
* **Rollback plan.** Revert; no caller exists yet.
* **Prerequisite.** None.
* **Acceptance criteria.** Unit test asserts each new enum value
  returns a non-null `Timer.Builder` from `MetricsService`.

### PR-2 — Wire emit calls into the 5 controllers

* **Intent.** Actually emit the histograms.
* **Files touched.** 5 controller files.
* **LoC budget.** ≤ 100 total (≤ 20 per controller).
* **Review focus.** Verify the wrapper doesn't change response
  semantics or HTTP status codes.
* **Rollback plan.** Revert; histograms go silent (no behaviour
  change).
* **Prerequisite.** PR-1 merged (otherwise the metric names don't
  exist).
* **Acceptance criteria.** SignalFx datapoint rate for each new
  histogram is non-zero within 24 h of deploy.

---

## PR-SEQ-P0-3 — Wire/remove dead `MetricKey` values

### PR-1 — Combined wire + remove

* **Intent.** Close the WIRED-not-LIVE category; restore confidence
  in the catalog.
* **Files touched.**
  `service/metric/MetricKey.kt`,
  `service/metric/ResultMetricBase.kt`,
  call sites for any value being **kept and wired**.
* **LoC budget.** ≤ 50.
* **Review focus.** Each enum entry being deleted has zero
  `grep` hits in `src/main/`. Each entry being wired has a real
  emit site in this PR.
* **Rollback plan.** Revert; deleted entries return.
* **Prerequisite.** **Should be merged after PR-SEQ-P0-2 PR-1** so
  the `PROACTIVE_TEST_LATENCY` histogram registration is in place
  before its wiring lands.
* **Acceptance criteria.** Post-merge `grep -rn "WIRED but not LIVE"`
  in `cc/11-metrics-catalog` updated to "0 entries".

---

## PR-SEQ-P1-1 — Lift `LongRun.scaling.max` 2 → 6 + queue-depth scaling

### PR-1 — Single config-only PR

* **Intent.** Remove the throughput cap that will block Stage-2.
* **Files touched.** `service-descriptor.sd.yml` only.
* **LoC budget.** ≤ 30.
* **Review focus.**
  * Ops sign-off on cost-cap (worst-case 6× one-node baseline).
  * Scale-up trigger threshold is **not** so low that idle costs
    blow up.
  * Scale-down threshold is **not** so high that scaling thrashes.
* **Rollback plan.** Revert YAML; cluster size returns to 1-2.
  No data migration; existing in-flight tasks finish on whichever
  node owns them.
* **Prerequisite.** Real Rovo Insights handler is on the deploy
  schedule (this PR is wasteful if the handler isn't shipping
  in the same quarter).
* **Acceptance criteria.** Synthetic burst test shows 3 → 6
  nodes within 5 min of queue depth crossing the threshold.

---

## PR-SEQ-P1-2 — Per-queue SQS consumer concurrency

### PR-1 — Single config-only PR

* **Intent.** Differentiate the two queues' tuning.
* **Files touched.** `application.yml` only.
* **LoC budget.** ≤ 20.
* **Review focus.** Confirm property naming matches Spring's
  per-container override convention (validate by re-reading
  `atlassian-spring-boot-sqs-starter` docs in the same PR
  description).
* **Rollback plan.** Revert YAML; both queues go back to `2-8`.
* **Prerequisite.** None (independent of P1-1, but they compose).
* **Acceptance criteria.** JMS listener container logs at startup
  show different `concurrency` values for the two containers.

---

## PR-SEQ-P1-3 — E2E synthetic canary

### PR-1 — Add `CanaryTask`, handler, scheduled job, metric

* **Intent.** Detect silent message loss + context-replay
  regression. **No alarm yet** so the PR can be merged safely
  even if the metric is initially noisy.
* **Files touched.**
  New `feature/canary/CanaryTask.kt`,
  new `feature/canary/CanaryTaskHandler.kt`,
  new `feature/canary/CanaryScheduler.kt`,
  `service/metric/MetricKey.kt` (new entry).
* **LoC budget.** ≤ 200 (incl. tests).
* **Review focus.** The handler is genuinely simple (no
  external calls); the scheduler runs only on the WebServer
  group (`@Scheduled` + condition guard).
* **Rollback plan.** Revert; metric goes silent.
* **Prerequisite.** None.
* **Acceptance criteria.** SignalFx shows a canary heartbeat
  every 5 min for 7 consecutive days.

### PR-2 — Add Tome alarm + runbook entry

* **Intent.** Page on canary failure.
* **Files touched.** `service-descriptor.sd.yml` (new alarm),
  Confluence runbook (out-of-band).
* **LoC budget.** ≤ 40.
* **Review focus.** Threshold (90 % over 15 min) is loose enough
  to avoid noise, tight enough to catch a regression.
* **Rollback plan.** Revert YAML; alarm disappears.
* **Prerequisite.** PR-1 merged + 7 days of clean metric data
  (per the PR-1 acceptance criterion).
* **Acceptance criteria.** Alarm visible in Sauron, paged once
  via a deliberate test (e.g., temporarily disable the
  scheduler in staging).

---

## PR-SEQ-P1-4 — Idempotency-key contract

### PR-1 — Add interface method + dispatcher check (opt-in only)

* **Intent.** Land the framework support without touching any
  handler.
* **Files touched.**
  `task/AsyncTaskHandler.kt` (add default method returning `null`),
  `task/internal/AsyncTaskDispatcher.kt` (Redis SETNX check),
  `service/metric/MetricKey.kt` (`ASYNC_TASK_IDEMPOTENT_SKIP`),
  tests for both happy path and Redis-unavailable fail-open.
* **LoC budget.** ≤ 250 (incl. tests).
* **Review focus.**
  * Default value is `null` so the 1 existing handler
    (`RovoInsightsGenerationTaskHandler`) is unchanged.
  * Redis SETNX uses `EX` (TTL); never `NX` without TTL (would
    deadlock duplicate forever).
  * Fail-open semantics: Redis 5xx → log + metric + execute
    handler (don't block on cache).
* **Rollback plan.** Revert; new method goes back to default
  `null`; dispatcher path unchanged.
* **Prerequisite.** None.
* **Acceptance criteria.** Unit test for dispatcher invokes
  Redis once per non-null `idempotencyKey`; integration test
  confirms duplicate dispatch with the same key is skipped.

### PR-2 — Override `idempotencyKey` for the real Rovo Insights handler

* **Intent.** Use the contract for the highest-cost handler.
* **Files touched.**
  `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`
  (and its `RovoInsightsGenerationTask` data class — to derive
  a deterministic key).
* **LoC budget.** ≤ 50.
* **Review focus.** The key derivation function is **deterministic**
  (same task body → same key) and **collision-resistant**
  (different tasks → different keys).
* **Rollback plan.** Revert; handler goes back to executing on
  every delivery.
* **Prerequisite.** PR-1 merged + the real generation handler
  shipped (this PR is meaningless against the stub).
* **Acceptance criteria.** Synthetic duplicate-delivery test
  shows the second delivery emits `ASYNC_TASK_IDEMPOTENT_SKIP`
  and does not call AI Gateway.

---

## PR-SEQ-P2-1 — Drop `.blockingGet()` (4 sites)

### PR-1 — Single atomic conversion

* **Intent.** Convert all 4 sites in one PR (consistency).
* **Files touched.**
  `stratus/internal/AIGatewayServiceImpl.kt`,
  `stratus/StratusTestController.kt`,
  `stratus/IntegrationServiceToolProvider.kt`,
  any caller that needs `suspend` propagation.
* **LoC budget.** ≤ 200.
* **Review focus.** Error-handling parity (rxjava's
  `.blockingGet()` throws unchecked; coroutines' `.await()`
  cancels on parent cancellation — verify behaviour under
  request timeout).
* **Rollback plan.** Revert; old blocking style returns.
* **Prerequisite.** None (kotlinx-coroutines-rx3 is already a
  transitive dep — verify in `build.gradle.kts` before starting).
* **Acceptance criteria.** All 4 sites converted; existing
  Stratus tests pass; new test for cancellation behaviour added.

---

## PR-SEQ-P2-2 — MCP tool-discovery cache

### PR-1 — Single PR

* **Intent.** Cache `getTools(...)` for 5 min.
* **Files touched.**
  `stratus/IntegrationServiceToolProvider.kt`,
  new `stratus/CachedToolDiscovery.kt` (or an inline Caffeine
  builder if small enough),
  `service/metric/MetricKey.kt` (cache hit/miss),
  `build.gradle.kts` (if Caffeine isn't already present).
* **LoC budget.** ≤ 150.
* **Review focus.**
  * Cache key includes any tenant-scoping (if tools are
    tenant-specific — verify with the Integrations Service team
    before merge).
  * Refresh-after-write so latency tail isn't on the slow path.
  * Admin endpoint to invalidate the cache (e.g.,
    `POST /admin/tool-cache/invalidate` guarded by an internal
    flag).
* **Rollback plan.** Revert; per-request calls return.
* **Prerequisite.** Confirm with Integrations Service team that
  tool-list is **not** tenant-specific (or scope the cache key
  accordingly).
* **Acceptance criteria.** Cache hit ratio > 90 % within 5 min
  of warm-up.

---

## PR-SEQ-P2-3 — Detekt rule for `LaasLogger`

### PR-1 — Add rule + first cleanup pass

* **Intent.** Promote convention to lint.
* **Files touched.**
  New `detekt-rules-pai/` module (or single `.kt` file under
  `buildSrc/` if the project doesn't have a custom-rules module
  yet),
  `bitbucket-pipelines.yml` (wire detekt into CI as **warning**
  initially),
  any 3-5 violation sites cleaned up in the same PR.
* **LoC budget.** ≤ 250.
* **Review focus.** Rule scope: only `src/main/kotlin/`,
  exclude `logging/` package itself.
* **Rollback plan.** Revert; rule goes away.
* **Prerequisite.** None.
* **Acceptance criteria.** CI emits 0 detekt warnings for
  `org.slf4j.LoggerFactory.getLogger` outside `logging/`.

---

## PR-SEQ-P3-1 — Complete ADR-008 migration

### PR-1 — Single PR

* **Intent.** Make `MicrosEnvironmentType` actually consumed.
* **Files touched.**
  `featuregate/internal/FeatureFlagContextServiceImpl.kt`,
  test files for the same.
* **LoC budget.** ≤ 50.
* **Review focus.** Constructor injection vs `@Value` — verify
  Spring resolution order.
* **Rollback plan.** Revert; back to raw `@Value`.
* **Prerequisite.** None.
* **Acceptance criteria.** Test using a `@TestConfiguration`-supplied
  `MicrosEnvironmentType` mock passes.

---

## PR-SEQ-P3-2 — Controller test-coverage lift

### PRs-1 through 5 — One PR per controller

* **Intent.** Add unit tests for each of the 5 controllers, in any
  order.
* **Files touched per PR.** `<ControllerName>Test.kt` (new),
  no source changes.
* **LoC budget per PR.** ≤ 100.
* **Review focus.** Each PR covers ≥ 1 happy path + 1 error path.
* **Rollback plan.** Revert; tests disappear.
* **Prerequisite.** None; PRs are independent (no shared
  fixtures).
* **Acceptance criteria.** Jacoco coverage line for each
  controller increases from 0 % to ≥ 50 %.

---

## Cross-cutting PR hygiene

For every PR in this plan:

1. **Title** follows the `[<ID>][<AIX-TICKET>] <intent>` convention.
2. **Description** quotes:
   * The metric this PR is meant to move (name + current value).
   * The expected delta after merge.
   * The counter-metric to watch for regression.
   * A link to the relevant chapter of
     `../../codebase_understanding/architecture/cross-cutting/`.
3. **Tests** added for new logic (no test-deferral).
4. **Reviewers** chosen by the file-ownership chart in
   `cc/15-velocity-and-debt` (avoid sending all PRs to the same
   reviewer — addresses RISK-001).
5. **Rollback** explicitly described (the `Rollback plan` field).
6. **AIX ticket** linked (per the historical 75 %-of-human-PRs
   convention from `cc/13-full-history-catalog`).

---

## Sequencing graph (which PRs unblock which)

```
P0-1 PR-1 ───────┐
P0-1 PR-2 ──┐    │
P0-1 PR-3 ──┘    │  (P0-1 PR-3 needs PR-2)
                 │
P0-2 PR-1 ───────┼──┐
P0-2 PR-2 ───────┘  │
                    │
P0-3 PR-1 ──────────┘  (depends on P0-2 PR-1 to share registration)

P1-1 PR-1 ───── (independent; gated on real-handler delivery date)
P1-2 PR-1 ───── (independent)
P1-3 PR-1 ─── 7 days bake ── P1-3 PR-2
P1-4 PR-1 ─── (real handler ships) ── P1-4 PR-2

P2-1 PR-1 ───── (independent)
P2-2 PR-1 ───── (Integrations Service team confirmation)
P2-3 PR-1 ───── (independent)

P3-1 PR-1 ───── (independent; great first-PR for new contributor)
P3-2 PR-1..5 ── (independent of each other)
```

**Critical-path observation:** the only chain longer than 2 PRs is
`P0-1 PR-1 → PR-2 → PR-3` (~1-2 weeks total because PR-2 needs
runbook prose authored). **Everything else is parallelisable**
across multiple developers.

---

## Cross-references

* [`00-INDEX.md`](00-INDEX.md) — priority dashboard.
* [`01-PRIORITISED-INITIATIVES.md`](01-PRIORITISED-INITIATIVES.md) — what each initiative does.
* [`03-RISKS-AND-NON-GOALS.md`](03-RISKS-AND-NON-GOALS.md) — what we will NOT do.
* `../../codebase_understanding/architecture/cross-cutting/12-optimization-playbook.rst` Part 8 — generic PR-authoring checklist.
