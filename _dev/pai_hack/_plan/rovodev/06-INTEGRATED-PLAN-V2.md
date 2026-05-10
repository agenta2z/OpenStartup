# Integrated Plan v2 — Best of Tide v2 + Quokka + Rovodev

> **Author:** Rovo Dev (re-synthesis after Tide v2 rewrite), 2026-05-05 13:50.
> **Supersedes:** `05-INTEGRATED-PLAN.md` (which was authored against Tide v1).
> **Source plans:**
> * **Tide v2** — `~/.claude/plans/taking-a-deep-look-pure-tide.md` (401 lines, rewritten as itself a synthesis)
> * **Quokka** — `_plan/claude/taking-a-deep-look-lively-quokka.md` (361 lines, two-track A0–A6 / B0–B8)
> * **Rovodev** — `_plan/rovodev/00-…04-` (this directory, 5 files, 2113 lines)
>
> **Verification posture:** Every claim below is grounded in `git grep` on
> `atlassian_packages/proactive-ai-platform` HEAD, 2026-05-05. Where a prior
> integrated plan asserted a fact that I independently re-verified and found
> wrong, the correction is called out **explicitly**.

---

## Section 0 — What changed since the last synthesis

| Change | Source | Impact on synthesis |
|---|---|---|
| **Tide v1 → Tide v2** is itself now a synthesis | New | Tide v2 explicitly compares Plan A/B/C and recommends **Plan B (Quokka)** if forced to one. This is the **same** conclusion my prior synthesis reached. Strong cross-validation. |
| **Tide v2 reverses on identity dedup** ("DROP — fixing a bug in dead code has zero impact") | New | Independently re-verified by call-graph agent: `AsyncIdGatekeeperClient.checkPermissionBulk` has **zero production callers** in `src/main/`. **My prior synthesis was wrong** to keep this as P1-4. **Drop it.** |
| **Nudge throttle endpoint has no production consumers** | Call-graph agent | Hardcoded `(score=10, throttled=false)`; only acceptance tests reference it. Quokka B6 (real throttle implementation) would build logic for an **unused endpoint**. **Drop or defer until upstream consumer is defined.** |
| **`IntegrationServiceToolProvider` is only injected by `StratusTestController`** (which carries `// remove or gate behind feature flag before production`) | Call-graph agent | MCP tool-discovery cache (Tide P2-2 / Quokka B0 / Rovodev P2-2) optimises a **test-only** code path. **Keep as P3 or drop.** This is a reversal of my prior P2 ranking. |
| **Histograms: only one global `http.server.requests` exists** with buckets ≥100ms | Re-verified | Per-endpoint histograms must be **added**, not "tightened". Plan wording must change from "tighter histograms" → "add per-endpoint histograms with nudge-aware buckets (1, 5, 10, 25, 50, 100, 200, 500ms)". |

The net effect is the integrated plan **shrinks** versus my prior synthesis: 3 items drop or demote
because they target dead/test-only code paths.

---

## Section 1 — Re-verified ground truth (single source of truth)

| # | Claim | Verified? | Evidence |
|---|---|---|---|
| 1 | `RovoInsightsGenerationTaskHandler` is a stub | ✅ YES | Line 22 emits literal string `"stub - real generation logic not yet ported"` |
| 2 | Redis CLIENT not wired | ✅ YES | Zero matches for `redis|lettuce|jedis|valkey` in `build.gradle.kts` |
| 3 | Redis RESOURCE provisioned | ✅ YES | `service-descriptor.sd.yml`: `- type: redisx · name: proactive-ai-cache · engine: valkey · version: 7.x` |
| 4 | Redis was never previously removed | ✅ YES | `git log` — PR #96 (`05a3219 zcheng/AIX-3260-setup-redis-resource`) added the **resource only**; client wiring never landed. Quokka was right. |
| 5 | AI Gateway egress timeout = 600 s | ✅ YES | `service-descriptor.sd.yml:312` — `timeoutMs: 600000` |
| 6 | `queueCapacity = 0` in `WebMvcConfiguration.kt:48` | ✅ YES | Literal `executor.queueCapacity = 0`; comment block above it explains this means "any task above core size triggers a new thread until max, then **rejects**" |
| 7 | FF: 4 mutableMaps in `getFeatureGateUser` | ✅ YES | `FeatureFlagContextServiceImpl.kt` lines 179, 199, 208, 232 |
| 8 | Histogram buckets start at 100 ms | ✅ YES | `application.yml`: `boundaries: 100ms, 500ms, 1s, 2s, 3s, 4s, 5s, 10s, 20s, 120s` (single global histogram) |
| 9 | `AsyncIdGatekeeperClient.checkPermissionBulk` has **zero production callers** | ✅ YES | grep `src/main/`: only the interface declaration, the impl, and the deprecated `IdGatekeeperClient` wrapper — no `@Autowired` / DI site uses it from real code. **Tide v2's reversal is correct.** |
| 10 | `NudgeThrottleController` has **zero upstream consumers** | ✅ YES | Hardcoded `NudgeThrottleResponse(10, false)`; only `NudgeThrottleControllerAcceptanceTest.kt` references it |
| 11 | `IntegrationServiceToolProvider` injected only by `StratusTestController` | ✅ YES | grep — only one injection site; controller comment: "Test controller for development/testing only — remove or gate behind a feature flag before production" |
| 12 | All 6 alarms `Priority: Low` + `Runbook: TBD` | ✅ YES | `service-descriptor.sd.yml` alarm blocks |
| 13 | `LongRun.scaling.max: 2` | ✅ YES | `service-descriptor.sd.yml`: scaling block; inline comment "Kept minimal for now since PAI has no production workload yet" |

**Implication of 9, 10, 11:** Three items in the prior plans target code that has **no live blast radius today**. They become low-priority hygiene unless (a) the dead endpoint is wired by a downstream team, or (b) the test controller becomes a real surface.

---

## Section 2 — The integrated initiative list (15 items, ranked)

Each item cites its source plan(s). **Source-of-truth column** indicates which plan first surfaced the
issue. Items where I independently disagree with all three plans are tagged `[NEW INSIGHT]`.

### Tier P0 — OKR-blocking preconditions (5 items, 7 PRs, ~2 weeks)

| # | Initiative | Source | UX-Cat | Effort | Ship-order |
|---|---|---|---|---|---|
| **I-01** | **Per-endpoint p95 histograms** for the 5 controllers + nudge-aware buckets `(1, 5, 10, 25, 50, 100, 200, 500ms)` | Rovodev P0-2 + Tide P0-1 + Quokka A0 | C | S | Week 1 |
| **I-02** | **Business-metric vocabulary** — new `MetricKey`s tagged `surface`, `experience`, `outcome`, `model`, `cache_hit` (allow-list enforced — **no `tenant_id` tag** to prevent SignalFx cardinality blow-up) | Quokka A0 + Tide P0-1 | C | S | Week 1 |
| **I-03** | **SLO file (`continuous-verification.yml`) + minimum runbooks + alarm-priority promotion** | Rovodev P0-1 + Tide P0-2 | B | S | Week 1–2 |
| **I-04** | **Wire/remove 4 dead `MetricKey` enum values** (`PROACTIVE_TEST_LATENCY`, `TENANT_CONTEXT_BUILD_*`) | Rovodev P0-3 | E | XS | Week 1 |
| **I-05** | **AI Gateway timeout `600 000 ms → 60 000 ms`** + per-tenant `application.yml` override (`proactive-ai.ai-gateway.client-timeout-seconds`) | Quokka A6 + Tide P1-2 | B | S | Week 2 (separate commit, surgical rollback) |

**Why these are P0:** Without I-01/I-02 nothing in P1/P2 can *prove* its impact (the 50 ms nudge SLO is currently invisible). Without I-03 the on-call is blind. Without I-05 a single hung LLM call ties 12.5 % of one pod for 10 minutes when the real handler ramps.

### Tier P1 — Platform foundation (5 items, 7 PRs, ~3–4 weeks)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-06** | **`queueCapacity` fix** — change 0 → 64 + `RejectedExecutionHandler` that emits `task.rejected` metric **instead of** HTTP 500 | Quokka A6 + Tide P1-2 | B | S |
| **I-07** | **Per-request feature-flag memoisation** — wrap `checkGate*` results in per-request `MutableMap<(statsigKey, contextType), Boolean>` (do **NOT** memoise `getExperiment(logExperimentExposure=true)`) | Quokka A5 + Tide P1-1 | C | S |
| **I-08** | **Redis client + `ProactiveAiCache` primitive** — `spring-boot-starter-data-redis`; namespaces `IDEMPOTENCY`, `INSIGHTS_RESULT`, `NUDGE_COUNTER`, `BUDGET_COUNTER`; **graceful degradation** (errors → `null` + metric, never throw); `/deepcheck` Redis probe | Quokka A1 + Tide P1-3 | C | M |
| **I-09** | **AsyncTask idempotency guard** — `idempotencyKey: String?` on `AsyncTask`; pre-handler `cache.get(IDEMPOTENCY, ":done")`; `cache.setIfAbsent(":submitted")` on submit | Quokka A2 + Tide P1-4 | B | M |
| **I-10** | **Visibility-extension hardening** — bounded heartbeat `TaskScheduler`, consecutive-failure cap, restart on failure ≥ N times, `vis.extend.error` metric | Quokka A3 + Tide P1-5 | B | S |
| **I-11** | **Error classification (`Permanent` vs `Transient`)** — wrap LLM/AI-Gateway exceptions; `Permanent` → write `:done` + skip retry; `Transient` → retry as today | Quokka A4 + Tide P1-6 | B | S |

**Depends-on graph:** I-09 requires I-08. I-11 requires I-09. I-06/I-07/I-10 are independent.

### Tier P2 — Observability + capacity once load arrives (3 items, 4 PRs, ~2 weeks)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-12** | **End-to-end synthetic canary** — `CanaryTask` round-trips WebServer → SQS → LongRun → completion metric; alarm if absent for 15 min | Rovodev P1-3 + Tide P1-7 | B | M |
| **I-13** | **Convert `.blockingGet()` in `stratus/`** to suspending coroutines (bounded `Semaphore(8)` per-pod ceiling) | Rovodev P2-1 + Tide P2-1 + Quokka B1 | C | S |
| **I-14** | **Scale config: prepare `LongRun max 2 → 6` + SQS concurrency `8 → 16`** as a **PR that does not deploy** until handler ships (per Rovodev's "scale only when load justifies" principle) | Rovodev P1-1+P1-2 + Tide P2-3 | C | S |

### Tier P3 — Hygiene (3 items, 4 PRs, ~1 week)

| # | Initiative | Source | UX-Cat | Effort |
|---|---|---|---|---|
| **I-15** | **Test coverage: `utility/threading/` (P0-blast, 0 tests today) + `VisibilityExtendingSQSQueueConsumerTest` + `RovoInsightsControllerTest`** | Tide P3-1 + Rovodev P3-2 | D | M |
| **I-16** | **Detekt rule for `LaasLoggerFactory`** (raise adoption 85 % → 100 %) | Rovodev P3-3 + Tide P3-3 | D | XS |
| **I-19** | **Delete orphan `/api/v1/rovo-insights/*` entry from `policy.json`** (dead text — actual route is `/api/v1/rovo/insights/*`) | `08-DEEP-DIVE.md` DC-06 | E | XS |

### Tier P0 — Rovo-Insights-specific additions (2 items, 2 PRs)

These are **additions to P0** (now 7 items total) surfaced by `08-ROVO-INSIGHTS-DEEP-DIVE.md`:

| # | Initiative | Source | UX-Cat | Effort | Why P0 |
|---|---|---|---|---|---|
| **I-17** | **FIFO/Standard queue alignment with convo-ai** — convo-ai's `sandbox.def.yml` declares `rovo-insights-generation-queue.fifo` (FIFO required for `MessageGroupId`); PAI provisions Standard. **First production message will be rejected** unless aligned. | `08-DEEP-DIVE.md` DC-01 | B | M | Cross-team work has the longest lead time; **start the conversation now** |
| **I-18** | **Make `/status` honest while handler is stub** — change `RovoInsightsController.kt:25-30` from `insightsAvailable = true` to `false`. Today the controller's hardcoded `true` directly contradicts the swagger annotation that says cache miss should return `false`. | `08-DEEP-DIVE.md` DC-02 | A | XS | One-line fix; without it convo-ai users see permanent "loading" state when integration starts |

---

## Section 3 — Items deliberately DROPPED (with reasons)

| Dropped item | Source plan(s) | Why dropped |
|---|---|---|
| **Identity-dedup fix** | All three previously included | Verified zero production callers of `AsyncIdGatekeeperClient.checkPermissionBulk`. Tide v2 was right to reverse. |
| **MCP tool-discovery cache** | Tide P2-2, Quokka B0, Rovodev P2-2 | Single injection site is `StratusTestController` (test/dev only). Optimising test-only code is wrong tier. **Reconsider when MCP becomes part of the real handler (B3+).** |
| **Real nudge throttle implementation (Quokka B6)** | Quokka B6 | Endpoint has zero upstream consumers; building logic for unused endpoint is premature. **Reconsider when downstream PM identifies a calling surface.** |
| **Real Rovo Insights handler (Quokka B2-B5)** | Quokka B2-B5 | Crosses the user's "no user-facing behaviour change" constraint. This is the team's **roadmap work**, not platform improvement. The platform plan **prepares the ground** for it. |
| **Coalescing (Quokka B8)** | Quokka B8 | Already deferred by Quokka itself; depends on validating workspace-shareability of insights — unknown today. |
| **Per-tenant LLM budget gate (Quokka B7)** | Quokka B7 | Useful **after** real handler exists. Pre-handler, default cap = `Int.MAX_VALUE` is identical to nothing. Add when budget enforcement is needed. |
| **Identity dedup on dead code** | Tide v1 | See first row. |
| **Pre-design LLM response caching** | None proposed | Premature against a stub handler. Cache shape depends on real handler's response schema. |
| **FIFO SQS / WebFlux migration / GraalVM / circuit-breaker library** | None | Already covered in Rovodev's `03-RISKS-AND-NON-GOALS.md` |

**Total dropped:** 8 items. **Net plan:** 16 items down from 26 in the prior synthesis.

---

## Section 4 — Sequencing graph

```
Week 1 (3 PRs in parallel — all additive, zero blast):
├── I-01  Per-endpoint histograms                  (PR-1: enum + register; PR-2: wire 5 controllers)
├── I-02  Business-metric vocabulary               (rides with I-01 PR-1)
├── I-04  Dead-MetricKey cleanup                   (1 PR)
├── I-07  FF memoisation                           (1 PR, behind flag)
└── I-16  Detekt LaasLogger rule                   (1 PR, build-gate only)

Week 2:
├── I-03  SLO + runbooks + alarm priority          (3 PRs)
├── I-05  AI-Gateway timeout 600s → 60s            (1 PR, separate commit)
├── I-06  queueCapacity 0 → 64 + reject metric     (1 PR)
└── I-15  utility/threading tests                  (1 PR — closes blast-radius gap)

Week 3:
├── I-08  Redis client + ProactiveAiCache primitive (1 PR; testcontainers Valkey 7.x)
├── I-10  Visibility-extension hardening            (1 PR)
└── I-12  E2E synthetic canary (PR-1: CanaryTask)   (PR-1 of 2)

Week 4:
├── I-09  AsyncTask idempotency guard              (depends on I-08)
├── I-13  blockingGet → suspending                  (1 PR)
└── I-12  Canary alarm                             (PR-2 of 2 — after 7-day bake)

Week 5:
├── I-11  Error classification                     (depends on I-09)
└── I-14  Scaling config (prepared, not deployed)  (1 PR — gates on handler delivery)

Week 6 — bake / observe; no new PRs
```

**Critical path:** I-01 → I-02 (Week 1) → I-08 (Week 3) → I-09 (Week 4) → I-11 (Week 5).
Everything else parallelises.

---

## Section 5 — UX-impact aggregate (corrected)

Using Rovodev's A/B/C/D/E classification, the integrated 16-item plan is:

| Category | Count | % | Items |
|---|---|---|---|
| **A** — Direct user-perceived | 0 | 0 % | (none — handler still stub) |
| **B** — Failure-path UX | 6 | 38 % | I-03, I-05, I-06, I-09, I-10, I-11, I-12 |
| **C** — Enables future user UX | 5 | 31 % | I-01, I-02, I-07, I-08, I-13, I-14 |
| **D** — Engineer / on-call UX | 2 | 13 % | I-15, I-16 |
| **E** — Pure hygiene | 1 | 6 % | I-04 |

**Honest framing:** **0 % Category A** is the right answer for the team's current stage
(pre-handler-launch). The synthesis's prior claim of "14 %" via Rovodev P1-5/P1-6 was
inflated — those items were "status endpoint design" (no front-end consumer agreed) and
"RFC-7807 problem-details for AI-Gateway 4xx" (no AI-Gateway error today because handler
doesn't make calls). Both are **dropped** in favour of the honest aggregate.

When the real handler ships, the right re-prioritisation move is to **add 2–3 Category-A
items** (e.g. user-visible status + retry messaging) in a follow-up plan — not to retro-fit
them into the platform plan.

---

## Section 6 — Cross-cutting PR hygiene

Every PR in this plan must satisfy:

1. **Title:** `[I-NN / AIX-TICKET] <intent>` (e.g. `[I-08 / AIX-3340] Wire spring-boot-starter-data-redis + ProactiveAiCache`)
2. **Behind a Statsig flag**, default off in non-`hello`. Naming convention: `proactive-ai.<area>.<feature>.enabled`.
3. **Snapshot test** if the PR touches anything in a controller's response chain (byte-equality vs current behaviour when flag off).
4. **Counter-metric** named in the description (the metric that, if it regresses, you must roll back).
5. **Rollback recipe** — specific commit revert + flag flip.
6. **Two reviewers:** one platform-area owner + one SRE for any PR touching `service-descriptor.sd.yml`.

---

## Section 7 — The single most important unanswered question

> **When does the real Rovo Insights handler ship, and what is its expected daily QPS profile?**

This question gates ~50 % of the plan's value:

* Without a handler-ship date, scaling config (I-14), error classification (I-11), and idempotency (I-09) are precondition-building with **no validation traffic**.
* Without a QPS profile, capacity targets (`scaling.max = 6`?), Redis sizing (current `t4g.small`?), and AI-Gateway timeout headroom (60 s? 30 s?) are guesses.

**Recommendation to the team:** Block this plan's Week 4 kick-off on a one-paragraph answer
from the feature owner (zcheng / mdawson per `git log`). Their answer should be 3 numbers:
projected daily-active tenants, average insights generated per active tenant per day, and
the date `RovoInsightsGenerationTaskHandler` will replace its stub body.

---

## Section 8 — The single most important *insight* the synthesis surfaces

> **Decouple infrastructure ramp from handler activation.**

* **Infrastructure ramp** = I-01 through I-15 — ships independently, tested under stub-handler
  load (which is functionally a no-op so queues drain instantly; perfect for stress-testing
  *everything except the LLM call*).
* **Handler activation** = the team's roadmap work, gated by **a separate Statsig flag**
  controlled by the feature owner, ramped Hello → 1 % → 5 % → 25 % → 100 % over 2–3 weeks
  after I-01–I-15 are stable.

Why this insight is important:

1. **None of the three plans articulates this.** Tide v2 implies it; Quokka collapses it
   into B2–B5 (which carries roadmap risk into platform PRs); Rovodev defers without
   articulating the seam.
2. **It de-risks both timelines.** Platform team ships independently; feature team owns
   handler readiness; ramp is a configuration change, not a release event.
3. **It makes the OKR measurable.** I-01/I-02 metrics will show the *moment* handler ramp
   produces the first real LLM invocation, with all downstream observability already in place.

---

## Section 9 — Cross-references

* `00-INDEX.md` — original Rovodev priority dashboard (now superseded by this file's Section 2)
* `01-PRIORITISED-INITIATIVES.md` — Rovodev's full per-initiative detail (still valid for I-01, I-03, I-04, I-12, I-14, I-15, I-16)
* `02-PR-SEQUENCING-PLAYBOOK.md` — Rovodev's PR-authoring patterns (extended by Section 6 above)
* `03-RISKS-AND-NON-GOALS.md` — covers the dropped items in Section 3
* `04-USER-EXPERIENCE-IMPACT.md` — UX classification methodology (now corrected to honest 0 % A)
* `05-INTEGRATED-PLAN.md` — **superseded by this file**
* `~/.claude/plans/taking-a-deep-look-pure-tide.md` — Tide v2
* `_plan/claude/taking-a-deep-look-lively-quokka.md` — Quokka
