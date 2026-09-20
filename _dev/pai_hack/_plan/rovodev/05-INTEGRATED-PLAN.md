# Integrated Plan — Best of Tide + Quokka + Rovodev

> **Author:** Rovo Dev (synthesis), 2026-05-05.
> **Inputs:** Three independent improvement plans for the
> Atlassian `proactive-ai-platform` service:
>
> * **Tide** — `~/.claude/plans/taking-a-deep-look-pure-tide.md`
>   (302 lines, 12 PRs in T1/T2/T3; tactical, file:line surgical
>   bug fixes, test-coverage focus).
> * **Quokka** —
>   `_dev/pai_hack/_plan/claude/taking-a-deep-look-lively-quokka.md`
>   (361 lines, 16 PRs in Track A platform-foundation + Track B
>   feature/LLM; architecturally cohesive, real-handler wiring,
>   per-tenant budget gate).
> * **Rovodev** — `_dev/pai_hack/_plan/rovodev/` (5 files, 14
>   initiatives in P0/P1/P2/P3; methodologically rigorous, UX
>   classification, explicit non-goals, pre-stage focus).
>
> **Goal:** integrate the genuine strengths of all three, drop
> the inaccuracies, and produce **one elegant, ramp-safe plan**.
>
> **Confidence:** HIGH on the structural choices. MEDIUM on
> individual quantitative claims (each carries the original
> author's confidence level + my verification flag).

---

## Section 0 — Why a synthesis is needed

The three plans are **not redundant** — they are **complementary**:

* Tide finds the **real bugs** (identity dedup, JVM heap, scaling
  config). Tide is grounded; you can ship Tide PRs tomorrow.
* Quokka builds the **right abstractions** (Redis primitive, error
  classification, per-tenant budget gate, idempotency contract,
  feature-flag memoisation). Quokka thinks in framework terms.
* Rovodev brings the **discipline** (UX impact category A/B/C/D/E,
  explicit non-goals doc, "today's stub vs tomorrow's load"
  honest framing, per-PR rollback plans).

Each plan also has a **single biggest weakness**:

* Tide misses **AI-Gateway timeout** (left at 600s vs 30s SLO),
  misses **per-request feature-flag memoisation**, misses
  **per-endpoint p95 histograms**.
* Quokka **invents Redis client work that's bigger than it
  needs to be** (assumes spring-boot-starter-data-redis for a
  service that already has `redisx` provisioned with valkey;
  needs the `redisx-spring-boot-starter` family check first),
  and **gets ahead of itself** with B3-B8 (defines the LLM-handler
  fan-out before the team has decided whether the real handler is
  in scope this quarter).
* Rovodev **defers handler activation to P3** (treats the real
  Rovo Insights handler as someone else's concern — it isn't),
  and **doesn't catch tactical bugs** like Tide's identity-dedup
  finding.

**The integration thesis**: adopt **Rovodev's preconditions-first
discipline**, **Quokka's Track A→B sequencing**, and **Tide's
surgical bug fixes**, glued together with a **handler-activation
decoupling** that none of the three plans articulated.

---

## Section 1 — Critical-thinking corrections (independently verified)

Before I trust any plan's claim, here are the verified-2026-05-05
ground truths and where each plan got it right or wrong:

### 1.1 — Redis is provisioned, but the client is NOT wired

| Source | Claim | Truth |
|---|---|---|
| Tide PR 2.6 | "needs Redis setup" (footnote) | ✅ Honest — flags the precondition |
| Quokka A1 | "Add `spring-boot-starter-data-redis`" | ✅ Mostly right — but should consider Atlassian's `redisx-spring-boot-starter` family first (tenant-context aware client) |
| Rovodev (earlier rounds) | "Redis already provisioned per ADR-010" | ❌ **Mixed** — ADR-010 cites it correctly, but a later verification round wrongly said "no Redis" because I checked `build.gradle.kts` only |

**Verified facts (2026-05-05):**

* `service-descriptor.sd.yml` declares a `redisx` resource named
  `proactive-ai-cache`, engine `valkey`, instance `cache.t4g.small`,
  with `EngineCPUUtilization` alarm.
* Provisioned by **PR #96** (commit `05a3219`,
  `zcheng/AIX-3260-setup-redis-resource`).
* **No** Redis client dependency in `build.gradle.kts`.
* **No** `RedisTemplate` / Lettuce / Jedis / `@Cacheable` in
  `src/main/kotlin/`.
* **Conclusion**: client wiring is real work; resource is already
  paid for. Quokka's A1 is the right scope, modulo checking
  Atlassian's `redisx-spring-boot-starter` first.

### 1.2 — Identity dedup IS a real bug (Tide alone caught it)

`src/main/kotlin/.../client/identity/internal/AsyncIdGatekeeperClientImpl.kt`:

* Line 82: `val distinctRequests = requests.map { Triple(...) }.toSet().size`
* Line 83-90: logs `duplicates_in_batch` and `distinct_principals`
* Lines 95-110: sends `BodyInserters.fromValue(requests)` — the
  un-deduplicated list — to the API.

**Verdict:** Tide's PR 1.3 is **correct and important**. Quokka
and Rovodev both miss this. **Adopt as P1-7 in the integrated plan.**

### 1.3 — `.blockingGet()` sites are in `stratus/` only (not user-facing)

`grep -rn "\.blockingGet()"` in `src/main/kotlin/`:

* `stratus/internal/AIGatewayServiceImpl.kt:73` (1 site)
* `stratus/StratusTestController.kt` (2 sites — `:78`, `:158`)
* `stratus/IntegrationServiceToolProvider.kt:51` (1 site)

**Verdict:** Tide's PR 1.1 claim of "6.4 req/sec → 1000+ concurrent"
is **over-stated for today's traffic** because none of these
sites is on a live nudge/insights user path. The conversion is
*structurally correct* and is *necessary preparation* for when
the real handler ships and these calls move to a real user-facing
hot path. Quokka's B1 framing ("frees Tomcat threads on test
endpoints + future insights worker") is more honest.

### 1.4 — Real Rovo Insights handler IS a stub

`src/main/kotlin/.../feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`
contains the literal string
`"stub - real generation logic not yet ported"`.

**Verdict:** every plan's *quantitative* invocation-saving claims
("save $1.2K/month", "30% input-token reduction", "60% LLM call
elimination") are **conditional** on the real handler shipping.
Rovodev is most honest about this (entire `04-USER-EXPERIENCE-IMPACT.md`
file is structured around it). Tide skips the issue. Quokka
addresses it via incremental B2 → B3 → B4 PRs but assumes the
team commits to the wiring effort.

### 1.5 — All 6 alarms are `Priority: Low + Runbook: TBD`

Verified in `service-descriptor.sd.yml`. **All three plans agree**
this is a P0 issue (Tide PR 2.5 + 3.3, Quokka does not call out
explicitly, Rovodev P0-1).

### 1.6 — JVM heap at 25% — Tide's PR 1.5 alone catches this

`service-descriptor.sd.yml` line 247: `MEMORY_OPTS:
"-XX:MaxRAMPercentage=25.0"`. Tide PR 1.5 correctly notes that the
memory alarm threshold was already raised from 80% → 90% in
PR #58 (a hint that memory pressure was already observed).

**Verdict:** Tide's finding is real but the proposed 25% → 50%
jump is aggressive without staging-load-test validation. The
integrated plan accepts the change but ships it as a **separate
config commit with 48h staging soak** (Tide already proposes this).

### 1.7 — `LongRun.scaling.max: 2` — all three plans agree

Tide PR 1.4 + Rovodev P1-1 propose 2 → 6. Quokka does NOT
explicitly include this (a real gap in Quokka). Adopt: lift to 6
+ add queue-depth scaling rule.

### 1.8 — Per-request feature-flag memoisation — Quokka A5 alone catches this

Quokka observes that `checkGate*` may be called 5× per request
during context build, costing ~1ms in repeated SDK calls. **No
other plan caught this.** Adopt as P1-8 in the integrated plan.

---

## Section 2 — Integrated initiative list (16 items, ranked)

Format: each row cites its source plan(s). Single-source rows are
explicitly attributed (T = Tide, Q = Quokka, R = Rovodev). UX
category from Rovodev's framework: **A** = direct user-perceived,
**B** = failure-path UX, **C** = enables future UX, **D** =
engineer/operator UX, **E** = pure hygiene.

### P0 — Preconditions (5 items)

| ID | Title | Source | Effort | PRs | UX |
|---|---|---|---|---|---|
| **I-01** | SLO file (`continuous-verification.yml`) + 2 minimum runbooks + DLQ alarm priority promotion | R/P0-1 + T/PR2.5+3.3 | S | 3 | B |
| **I-02** | Per-endpoint p95 histograms for the 5 controllers (`HistogramMetric` + `application.yml` registration + emit calls) | R/P0-2 | S | 2 | C |
| **I-03** | Wire / remove the 4 dead `MetricKey` enum values + add MCP/agent timing metrics | R/P0-3 + T/PR3.2 | XS | 1 | E |
| **I-04** | **Business-metric vocabulary**: new `MetricKey` values with tags `surface`, `experience`, `model`, `outcome`, `cache_hit`, `dedup_hit`, `tenant_id` (with cardinality budget) | Q/A0 | S | 1 | C |
| **I-05** | **AI-Gateway timeout audit** — drop egress `timeoutMs: 600000` → `60000` (separate commit, behind config var, 1-week observation) | Q/A6 (partial) | XS | 1 | B |

### P1 — Platform Foundation + Tactical Wins (8 items)

| ID | Title | Source | Effort | PRs | UX |
|---|---|---|---|---|---|
| **I-06** | **Redis client + `ProactiveAiCache` primitive** (check `redisx-spring-boot-starter` first; if not, Lettuce + tests via Testcontainers; deepcheck probe; fail-open on outage) | Q/A1 | M | 1 | C |
| **I-07** | **Async-task idempotency contract** (interface method `idempotencyKey()`, dispatcher SETNX check, `:done` marker for permanent errors after I-09) | Q/A2 + R/P1-4 + T/PR2.6 | M | 2 | B |
| **I-08** | **Visibility-extension hardening** (dedicated `ThreadPoolTaskScheduler`, consecutive-failure counter, `task.visibility.extend.failure` metric, `VisibilityExtendingSQSQueueConsumerTest`) | Q/A3 + T/PR2.4 | S | 1 | C |
| **I-09** | **Error classification (Permanent vs Transient)** (sealed `TaskError` + `:done` ack on `Permanent`, default `Transient` for unknown; behind `platform.error.classification.enabled` flag) | Q/A4 | S | 2 | B |
| **I-10** | **Lift `LongRun.scaling.max: 2 → 6`** + queue-depth scaling + per-queue SQS concurrency (`analytics-events: 1-4`, `rovo-insights-generation-queue: 4-12`) | T/PR1.4 + R/P1-1+P1-2 | S | 1 | C |
| **I-11** | **Async executor `queueCapacity: 0 → 64`** + `RejectedExecutionHandler` emitting metric (in `WebMvcConfiguration`); ride along with I-05 | Q/A6 (partial) | XS | 1 (combined w I-05) | B |
| **I-12** | **End-to-end synthetic canary** (`CanaryTask` every 5 min, asserts `request_id` survives WebServer → SQS → LongRun) | R/P1-3 | M | 2 | B |
| **I-13** | **Handler-activation decoupling** (Statsig flag `ROVO_INSIGHTS_HANDLER_REAL_ENABLED`, default off; weekly ramp playbook 1% → 5% → 25% → 100%) | Synthesis insight | S | 1 | C |

### P2 — Latency / Throughput Wins + Test Coverage (7 items)

| ID | Title | Source | Effort | PRs | UX |
|---|---|---|---|---|---|
| **I-14** | **Identity permission dedup** — fix `AsyncIdGatekeeperClientImpl.checkPermissionBulk()` to actually deduplicate before the API call (the code computes `distinctRequests` and logs but sends the un-deduped list) | T/PR1.3 | XS | 1 | C |
| **I-15** | **Per-request feature-flag memoisation** (Map keyed by `(statsigKey, contextType, randomizationId)` in `RequestScopedValueService`; explicitly **don't** memoise `getExperiment` with `logExperimentExposure=true`) | Q/A5 | S | 1 | C |
| **I-16** | **Convert 4 `.blockingGet()` calls to coroutine `.await()`** + `LlmEventAggregator` for SSE-aware aggregation | T/PR1.1 + Q/B0+B1 + R/P2-1 | S | 1 | C |
| **I-17** | **MCP tool-list cache** (Caffeine, 5-min TTL, refresh-after-write, key by `(cloudId, actionIdsHash)`, admin invalidate endpoint) — combines Tide's "reuse HTTP transport" with Quokka's "cache the tool list" into the right scope | T/PR1.2 + Q/B0 + R/P2-2 | S | 1 | C |
| **I-18** | **Detekt rule** banning `org.slf4j.LoggerFactory.getLogger` outside `logging/` (promote ADR-009 from convention to lint) | R/P2-3 | XS | 1 | D |
| **I-19** | **JVM heap 25% → 50%** (separate config commit, 48h staging soak) | T/PR1.5 | XS | 1 | C |
| **I-20** | **Test coverage P0 modules** (5 PRs, one each): `utility/threading/` (P0 blast, 0 tests), `RovoInsightsControllerTest`, `IntegrationServiceMcpSessionManagerTest`, `IntegrationServiceToolProviderTest`, `AIGatewayServiceImplTest` | T/PR2.1+2.2+2.3 + R/P3-2 | M | 5 | D |

### P3 — Real Handler Wiring + Cost Defenses (3 items)

> These are **conditional** on team commitment to ship the real
> Rovo Insights handler this quarter. If the team punts on the
> handler, **defer all of P3** (Quokka's B3-B8 work is wasted
> against a stub).

| ID | Title | Source | Effort | PRs | UX |
|---|---|---|---|---|---|
| **I-21** | **Handler — Phase A: ping** (real AI-Gateway round-trip with canned response, gated by I-13 flag, idempotency via I-07, cache write via I-06) — proves the wire end-to-end with zero LLM cost | Q/B2 | M | 1 | A |
| **I-22** | **Handler — Phase B: real prompt for one `InsightType`** (with prompt-caching headers; per-type Statsig gate; Hello → 1% → 10% → 100% over 2 weeks) | Q/B3 | L | 2 | A |
| **I-23** | **Per-tenant LLM budget gate** (`TenantBudgetGuard` using I-06 `cache.increment(BUDGET_COUNTER, ...)`, default cap = `Int.MAX_VALUE` so no UX change; PMs turn down per-tenant tier) | Q/B7 | M | 1 | B |

### Explicitly out of scope (Quokka B4, B5, B6, B8)

* **B4** parallel fan-out across all `InsightType`s — defer until
  I-22 single-type proves quality bar.
* **B5** `/status` + `/fetch` cache reads — defer; Rovodev's
  P1-5 (status visibility) already-flagged-as-product-prerequisite.
* **B6** real nudge throttle — defer; needs product-design sign-off
  on user behaviour (Rovodev's P1-5 prerequisite logic applies).
* **B8** workspace-scoped insights coalescing — Quokka itself
  defers pending shadow data; correct call.

### Explicitly out of scope (from `03-RISKS-AND-NON-GOALS.md`)

NG-1 through NG-15 from
[`03-RISKS-AND-NON-GOALS.md`](03-RISKS-AND-NON-GOALS.md) all
remain valid (caching speculation against stub, FIFO queue
switch, WebFlux migration, GraalVM, circuit-breaker library,
etc.).

---

## Section 3 — Sequencing graph

```
Week 1 (parallel, all P0):
  I-01 (SLO file PR-1)  ───┐
  I-02 (histogram PR-1) ───┤
  I-03 (dead enum + MCP) ──┤
  I-04 (biz-metric vocab) ─┤
  I-05 + I-11 (timeout + queueCapacity, sep commits) ─┘

Week 2 (P0 finish + P1 start):
  I-01 PR-2,3 (runbooks + DLQ promote)
  I-02 PR-2 (histograms wired)
  I-06 (Redis client) ─┐
  I-15 (FF memoise)    ┤   (parallel, independent)
  I-17 (MCP tool cache)┘

Week 3 (P1 platform):
  I-07 PR-1 (idempotency framework)
  I-08 (visibility hardening)
  I-09 PR-1 (error classification)
  I-12 PR-1 (e2e canary code, no alarm yet)

Week 4 (P1 wrap + P2 tactical):
  I-09 PR-2 (error classification flag-on)
  I-10 (LongRun max + per-queue concurrency)
  I-13 (handler-activation flag plumbing)
  I-14 (identity dedup) — XS, easy first PR
  I-16 (.blockingGet conversion)

Week 5 (P2 finish):
  I-19 (JVM heap, staging soak start)
  I-20 (5 test PRs in parallel by reviewer)
  I-12 PR-2 (canary alarm after 7-day bake)
  I-18 (detekt rule)

Week 6 (handler check-in):
  Decision: is the real handler shipping this quarter?
  If yes → start I-21 (Phase A ping).
  If no  → defer P3; revisit Week 8.

Weeks 7-9 (P3, conditional):
  I-21 (handler Phase A) — Hello → 1% canary
  I-22 (handler Phase B real prompt, single type) — 2-week ramp
  I-23 (per-tenant budget gate) — defaults preserve current behaviour
  I-07 PR-2 (handler overrides idempotencyKey)
```

**Critical path**: I-04 + I-06 → I-07 → I-09 → I-21 → I-22.
Approximately **6 weeks for P0+P1+P2** with 2-3 engineers in
parallel. Add **3 more weeks for P3** if handler ships.

---

## Section 4 — UX-impact aggregate

Counting the 23 items in the integrated list (excluding 4 explicit
deferrals):

| Category | Count | % | Honest interpretation |
|---|---|---|---|
| **A** (direct user) | 2 | 9% | I-21, I-22 — only when real handler ships |
| **B** (failure-path / cost) | 6 | 26% | Outage MTTR, double-charge prevention, silent-loss detection, generic error mitigation |
| **C** (enables future UX) | 11 | 48% | Instrumentation + capacity + plumbing |
| **D** (engineer/operator) | 3 | 13% | Detekt rule + tests |
| **E** (pure hygiene) | 1 | 4% | Dead enum cleanup |

**Compared to the Rovodev-only plan** (0% A, 21% B, 36% C, 14% D,
14% E): the integrated plan **doubles user-direct (A) initiatives
and increases cost-defence (B)** by adopting Quokka's I-21/I-22/I-23
chain. Still infrastructure-heavy, **honestly so**, because the
team is still pre-handler-launch.

---

## Section 5 — Cross-cutting PR hygiene (extends `02-PR-SEQUENCING-PLAYBOOK.md`)

For every PR in this integrated plan:

1. **Title:** `[<I-NN> / <AIX-TICKET>] <intent>`.
2. **Source-plan attribution:** mention which plan inspired it
   (`from Tide PR1.3` / `from Quokka A2` / `from Rovodev P0-1` /
   `synthesis I-13`) so future readers can trace lineage.
3. **Five mandatory questions** (from
   [`04-USER-EXPERIENCE-IMPACT.md`](04-USER-EXPERIENCE-IMPACT.md)
   §5):
   * What metric does this move?
   * Expected delta?
   * UX category (A/B/C/D/E)?
   * Materialisation condition (when does the user feel it)?
   * Counter-metric to watch for regression?
4. **Rollback plan** explicitly stated.
5. **Statsig kill-switch** for any behaviour-changing PR (default
   off; ramp Hello → 1 % → 10 % → 100 %).
6. **Acceptance criteria** that include either a metric assertion
   (SignalFx datapoint within 24h) or a load-test result.

---

## Section 6 — The single most important unanswered question

**"What's the planned ship-date for the real Rovo Insights
generation handler, and is the team committed?"**

Without this answer, **30-50 % of the work in any of the three
plans is preconditional** — it's correct work, but it's *waste*
if the handler is deferred to next quarter (because the load
patterns it would address don't exist).

Both Tide and Quokka assume the handler ships. Rovodev makes the
conditionality explicit but treats it as someone else's problem.
The integrated plan **builds the conditionality into the
sequencing** (P3 is gated on a Week-6 decision) — but the team
must still answer the question.

If I were the engineering lead, I would push back on the entire
P3 tier until I had a date.

---

## Section 7 — The single most important insight

**Decouple infrastructure ramp from handler activation.**

All three plans intertwine infrastructure work with handler
work. This is the wrong glue. The correct architecture:

* **Infrastructure ramp (P0+P1+P2)** runs to completion *without
  the real handler*. It uses the stub handler as a load source
  (a `CanaryTask` from I-12 + a stress harness can produce
  representative SQS pressure).
* **Handler activation (P3)** is a Statsig flag flip the day the
  handler is ready, with a pre-rehearsed weekly ramp (I-13
  defines it).

This decoupling lets the platform team ship I-01 through I-20
on a predictable schedule **regardless** of the feature team's
handler-ship date. It also means that the day the handler
arrives, the infrastructure has already been load-tested and the
SLO baselines are established.

**None of the three input plans articulates this decoupling
explicitly.** It is the synthesis's contribution.

---

## Section 8 — Cross-references

* [`00-INDEX.md`](00-INDEX.md) — original priority dashboard
  (will be updated to point at this synthesis as the primary
  artefact).
* [`01-PRIORITISED-INITIATIVES.md`](01-PRIORITISED-INITIATIVES.md) — original 14 Rovodev initiatives (preserved for lineage).
* [`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md) — PR-authoring discipline (extends to this plan).
* [`03-RISKS-AND-NON-GOALS.md`](03-RISKS-AND-NON-GOALS.md) — non-goals (still valid).
* [`04-USER-EXPERIENCE-IMPACT.md`](04-USER-EXPERIENCE-IMPACT.md) — UX classification framework.
* `~/.claude/plans/taking-a-deep-look-pure-tide.md` — Tide source.
* `_dev/pai_hack/_plan/claude/taking-a-deep-look-lively-quokka.md` — Quokka source.
