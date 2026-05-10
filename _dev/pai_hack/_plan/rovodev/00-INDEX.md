# Proactive AI Platform — Goal-Driven Improvement Plan

> **Date:** 2026-05-05
> **Author:** Rovo Dev (AI agent), grounded in
> [`../../codebase_understanding/`](../../codebase_understanding) and
> live source at `atlassian_packages/proactive-ai-platform/`.
> **Purpose:** Identify the highest-impact technical improvements that
> directly serve the team's FY26 H2 OKR (drive AI invocations
> 400K → 1.5M / month) and prepare for Stage-2 production ramp.
> **Confidence:** HIGH on the *mechanics* of each lever (cited to
> file:line). MEDIUM on the *impact estimates* (calibrate before
> quoting in PR descriptions).

---

## How to read this plan

Seven companion files; read in order or jump:

* **`11-OPPORTUNITY-AUDIT.md`** *(LATEST — 2026-05-05 16:20)* — honest
  re-evaluation answering "is there really no opportunity in PAI today?" after
  another session concluded "no big actionable wins exist." **Verdict: 8
  verified opportunities exist.** Adds 6 new items (I-34..I-39) to `09-`. Read
  if the question of "is it worth us doing anything pre-launch?" is live.
* **`09-INTEGRATED-PLAN-V3.md`** *(synthesis from 14:50; will be extended by
  `11-`)* — 20 items + 5 net-new findings, post-self-redteam corrections;
  supersedes `06-`. Tide v3 rewrote and now picks Plan C (Rovodev). Read this
  if you want the full per-item plan.
* **`06-INTEGRATED-PLAN-V2.md`** *(superseded by `09-`)* — 16-item integrated
  plan from 2026-05-05 14:15. Kept for historical comparison.
* **`07-PLAN-PICK-RECOMMENDATION.md`** — answers "if forced to pick one
  plan, which?". TL;DR: Quokka Track A only, with Rovodev governance bolt-ons.
* **`08-ROVO-INSIGHTS-DEEP-DIVE.md`** *(rovo-insights-specific)* — 18
  double-check items (6 Critical, 7 High, 5 Medium) for the
  `feature/rovoinsights/` package. Includes the **FIFO/Standard queue mismatch
  with convo-ai** (DC-01) and the **status endpoint logic inversion**
  (DC-02) — both missed by every source plan. **3 new P0/P3 items
  (I-17, I-18, I-19) folded into `06-`.**

The original five:

* **`00-INDEX.md`** *(this file)* — priorities at a glance, **with
  user-impact category** for each.
* **`01-PRIORITISED-INITIATIVES.md`** — the 14 ranked initiatives
  (12 original + 2 newly-proposed), each with **expected metric
  delta**, **PR series**, **risks**, and **counter-metrics**.
* **`02-PR-SEQUENCING-PLAYBOOK.md`** — how to ship each initiative as a
  small reviewable PR series (no big-bang PRs).
* **`03-RISKS-AND-NON-GOALS.md`** — what we will *not* do, and why
  (avoiding undoing intentional decisions; respecting historical
  context).
* **`04-USER-EXPERIENCE-IMPACT.md`** — **the missing UX-impact lens**.
  For every initiative, the causal chain from technical change to
  what an end-user actually perceives, plus an honest classification
  (A/B/C/D/E). **Read this if you want to understand which
  initiatives a real user will feel.**

---

## The single most important truth in this plan

> **The Rovo Insights generation handler is currently a stub** —
> verified at
> `src/main/kotlin/.../feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt`,
> the body literally says
> `"stub - real generation logic not yet ported"`.
>
> **Implication:** the team is in a **pre-load** posture. The biggest
> COGS / cost / throughput "wins" sub-agents excitedly quote
> ("$25M/yr saved by adding caching!") are **theoretical** — there is
> no live LLM traffic to cache yet. The honest framing is:
>
> > *"These changes are **preconditions** for Stage-2 ramp. Build them
> > **before** the real handler ships, or shipping the handler will
> > expose the gap and force emergency work."*

This plan ranks initiatives by **how much they de-risk or enable
the OKR**, not by speculative savings on traffic that doesn't exist.

---

## Goal mapping

The **single OKR** (`cc/01-business-and-technical-goals` Part 1):

```
Drive monthly AI invocations 400K → 1.5M (Q4 FY26)
  Stretch (0.7 confidence): 1.2M
```

The **single biggest unknown** that determines whether the team
hits it:

```
Will the real Rovo Insights handler scale to ~50K-200K
invocations/day on the current LongRun pool of 2 nodes?
```

Every initiative below is scored on its **contribution to closing
that unknown**, on a 0–5 scale.

---

## Priority dashboard (top 14, ranked)

**Added column: UX-Impact category** (see
[`04-USER-EXPERIENCE-IMPACT.md`](04-USER-EXPERIENCE-IMPACT.md) §2.1).
The honest aggregate is **0 / 12 in Category A** for the original
plan — the team is in pre-launch / pre-load posture. Adding **P1-5**
and **P1-6** brings 2 direct user-perceived initiatives in.

* **A** — Direct user-perceived improvement (rare today; pre-handler).
* **B** — User-perceived improvement only on failure paths.
* **C** — Enables future user-perceived improvement (instrumentation, capacity).
* **D** — Engineer / operator UX only.
* **E** — Pure technical hygiene.

| # | Initiative | OKR-impact (0-5) | UX-Cat | Effort | PR series | Status today |
|---|---|---|---|---|---|---|
| **P0** | **Wire SLO file + minimum runbooks** | **5** | **B** | S | 3 PRs | All alarms `Priority: Low` + `Runbook: TBD` |
| **P0** | **Per-endpoint p95 histograms** for the 5 controllers | **5** | **C** | S | 2 PRs | Only global histogram registered |
| **P0** | **Wire/remove 4 dead `MetricKey` enum values** | **3** | **E** | XS | 1 PR | 4 of 7 WIRED-not-LIVE |
| **P1** | **Lift `LongRun.scaling.max` 2 → 6** + autoscale on queue depth | **5** | **C** | S | 1 PR | Hard cap = 2 nodes = 16 in-flight |
| **P1** | **Per-queue SQS concurrency** | **4** | **C** | XS | 1 PR | Single global `2-8` |
| **P1** | **End-to-end synthetic canary** (request-id round-trip) | **4** | **B** | M | 2 PRs | No e2e canary |
| **P1** | **Idempotency keys on `AsyncTaskHandler`** | **4** | **B** | M | 2 PRs | Convention-only |
| **P1** ⭐ NEW | **`/api/v1/rovo-insights/{id}/status` endpoint** + Redis-persisted lifecycle | **4** | **A** | M | 3 PRs | No status surface today |
| **P1** ⭐ NEW | **Graceful-degradation messaging** (Problem-Details for AI Gateway 429 / 4xx) | **3** | **A** | S | 2 PRs | All AI-Gateway errors → generic 5xx |
| **P2** | **Convert 4 `.blockingGet()` calls** to suspending | **3** | **C** | S | 1 PR | 4 sites in 3 files (all `stratus/`) |
| **P2** | **MCP tool-discovery cache** | **3** | **C** | S | 1 PR | No cache; only `StratusTestController` caller |
| **P2** | **Detekt rule** for `LaasLoggerFactory` | **2** | **D** | XS | 1 PR | 85 % adoption |
| **P3** | **Complete ADR-008 migration** (typed `MicrosEnvironmentType`) | **1** | **E** | XS | 1 PR | 1 raw `@Value` consumer |
| **P3** | **Controller test-coverage** (5 controllers) | **2** | **D** | M | 5 PRs | 0 / 5 unit tests |

**Tier definitions:**

* **P0** = OKR-blocking. Without it, Stage-2 ramp is unsafe / unobservable.
* **P1** = OKR-enabling. With it, the team can ramp confidently.
* **P2** = OKR-accelerating. Improves capacity / latency / quality once load arrives.
* **P3** = Hygiene. Improves long-term velocity / bus-factor.

Effort scale: XS (≤1 day), S (2-5 days), M (1-2 weeks), L (>2 weeks).

**UX-impact aggregate (with the 2 new initiatives):**

| Cat | Count | % | What this means |
|---|---|---|---|
| A | 2 | 14% | Real user perceives a direct improvement (P1-5, P1-6) |
| B | 3 | 21% | Failure-path UX (recovery / silent-loss prevention) |
| C | 5 | 36% | Instrumentation / capacity — enables future UX |
| D | 2 | 14% | Engineer / on-call UX |
| E | 2 | 14% | Pure hygiene |

**Honest note.** The aggregate is still infrastructure-heavy. That's
correct for the team's stage (pre-handler-launch). When the real
generation handler ships, the right move is to re-prioritise toward
A and add concrete user-perceived deltas. See
[`04-USER-EXPERIENCE-IMPACT.md`](04-USER-EXPERIENCE-IMPACT.md) §4.

---

## What this plan deliberately does NOT propose

(See [`03-RISKS-AND-NON-GOALS.md`](03-RISKS-AND-NON-GOALS.md) for full
list and historical justification.)

* **No "add a cache layer to the LLM response"** — would prejudge the
  TTL / key strategy that the real handler hasn't yet defined.
  Premature optimisation against a stub.
* **No "switch to FIFO SQS"** — switch cost is non-trivial; need
  per-tenant fairness pressure from real load before justifying.
* **No "rewrite to WebFlux for streaming"** — large refactor, no
  current bottleneck. Revisit when AI Gateway exposes a streaming
  contract for the use cases PAI actually needs.
* **No "switch to GraalVM native-image"** — cold-start isn't an OKR
  blocker today; would invalidate decades of Spring tooling.
* **No "add a circuit breaker library"** — mesh egress retry policies
  cover this partially; adding a library multiplies failure modes.
* **No undoing of the recent `zcheng/remove-ddev-env` PR #52** — it
  was an intentional simplification.

---

## How to use this plan to drive PRs

1. Pick the **highest priority** open initiative.
2. Read its **expected metric delta** in
   `01-PRIORITISED-INITIATIVES.md`.
3. Read the **PR series** in `02-PR-SEQUENCING-PLAYBOOK.md` to see
   which sub-PRs to ship in what order.
4. Use the **PR-authoring checklist** from
   `cc/12-optimization-playbook.rst` Part 8 (already documented):
   name the metric in the title, quote the baseline, quote expected
   delta, link the alarm, list counter-metric.
5. Update the **status column** in this index when each PR merges.

---

## Maintenance

* Re-rank quarterly (next: end of Q4 FY26 / start of Q1 FY27).
* If an initiative's prerequisite changes (e.g., the real Rovo
  Insights handler ships), re-evaluate priorities — many P2s
  become P0s the day load arrives.
* Add new initiatives at the bottom; don't edit the IDs of merged
  ones (so PR descriptions can refer back stably).

---

## Cross-references

* [`../../codebase_understanding/AGENTS.md`](../../codebase_understanding/AGENTS.md) — agent-routing entry point.
* [`../../codebase_understanding/architecture/cross-cutting/01-business-and-technical-goals.rst`](../../codebase_understanding/architecture/cross-cutting/01-business-and-technical-goals.rst) — OKR contract.
* [`../../codebase_understanding/architecture/cross-cutting/11-metrics-catalog.rst`](../../codebase_understanding/architecture/cross-cutting/11-metrics-catalog.rst) — current metric / alarm / SLO inventory.
* [`../../codebase_understanding/architecture/cross-cutting/12-optimization-playbook.rst`](../../codebase_understanding/architecture/cross-cutting/12-optimization-playbook.rst) — generic levers; this plan is the *specific* selection.
* [`../../codebase_understanding/architecture/cross-cutting/14-architectural-decisions.rst`](../../codebase_understanding/architecture/cross-cutting/14-architectural-decisions.rst) — open ADRs (007/008/010 are referenced here).
