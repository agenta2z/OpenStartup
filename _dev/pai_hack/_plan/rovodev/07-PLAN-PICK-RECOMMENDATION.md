# If Forced to Pick One Plan — Recommendation

> **Author:** Rovo Dev, 2026-05-05.
> **Question from the user:** *"If we only pick one plan, which would you choose?"*
> **Companion to:** `06-INTEGRATED-PLAN-V2.md` (which is the **better** answer, but is a synthesis, not a single existing plan).

---

## TL;DR

> **Pick Quokka** (`_plan/claude/taking-a-deep-look-lively-quokka.md`).
>
> **With one mandatory amendment:** **drop Track B (B0–B8)** — those are user-facing
> roadmap work that crosses the user's "no user-facing behaviour change" constraint and
> targets endpoints/code paths with **zero production consumers today** (verified). Ship
> only **Track A (A0–A6)**, which is the highest-quality platform foundation in any of
> the three plans.

This matches Tide v2's own conclusion ("Plan B / quokka"), arrived at independently.

---

## Why Quokka — the three things only it caught

All three plans have overlap. The decisive question is *what's unique?* Three platform
issues are caught **only** by Quokka, all three independently re-verified by me against
HEAD on 2026-05-05:

| Quokka-only find | File:line | Real impact today |
|---|---|---|
| **`queueCapacity = 0`** in `WebMvcConfiguration.kt:48` | Verified | Any micro-burst above 64 concurrent threads → `RejectedExecutionException` → HTTP 500 storm. **Production time bomb the day real load arrives.** |
| **AI Gateway 600 s timeout** at `service-descriptor.sd.yml:312` | Verified | A single hung LLM call ties **1 / 8 of one pod for 10 minutes**. With 96-concurrent capacity (after scaling), 1 stuck call costs 1.04 % capacity for 10 minutes. With 8 stuck = 8.3 %. **No internal override exists.** |
| **Feature-flag memoisation** — `FeatureFlagContextServiceImpl.kt` lines 179, 199, 208, 232 allocate **4 mutableMaps per call**; `checkGate()` is called **5–8× per request** | Verified | On the **only** path that already has live production traffic (nudge throttle), this is ~32 redundant allocations per request, plus 5–8 redundant Statsig SDK calls. Cuts ~2–5 ms off the 50 ms nudge SLO budget. |

Tide v1 missed all three. Rovodev caught capacity headroom (P1-1, P1-2) but not these
three specific code-level issues. **These are the closest thing to "found bugs" in any of
the three plans.**

---

## Why not Tide v2

Tide v2 is itself a synthesis (it labels itself "Integrated Improvement Plan v2" and
even runs its own Plan A/B/C comparison). That makes it tempting to pick. But:

1. **It's a meta-plan, not a primary plan.** The actual recommendations it carries forward
   are **mostly Quokka's** (Tide v2 says explicitly: "Plan B / quokka" if forced to one). So
   "picking Tide v2" effectively means "picking Quokka with some selection".
2. **It drops the identity-dedup fix** with the right verdict (verified zero callers) but
   without surfacing that the **same logic applies to the MCP cache item and the nudge
   throttle item** — both of which target code with no live blast radius today (verified).
   Tide v2 keeps the MCP cache item; it should also be demoted.
3. **It is silent on the handler-shipping conditionality.** The most important question
   for prioritisation — *"when does the real handler ship?"* — is not surfaced. Quokka
   doesn't lead with it either, but its phased B2–B5 makes the dependency explicit; Rovodev
   leads with it. Tide v2 buries it.

---

## Why not Rovodev (my own plan)

Honest self-critique:

1. **Rovodev's biggest strength is governance, not technical depth.** UX classification,
   non-goals, re-evaluation triggers, sequencing playbook — all valuable, but they don't
   *find* the three issues Quokka found.
2. **Rovodev's P1-1 (`LongRun.scaling.max 2 → 6`) is correct but incomplete** — it changes
   capacity ceiling without addressing what happens *inside* a pod when one LLM call hangs
   (Quokka's I-05 / AI-Gateway timeout). Without I-05, scaling pods just gives you 6× the
   stuck-thread pain.
3. **The "0 % Category A" honesty is right, but the plan still pads with P1-5/P1-6**
   ("status endpoint", "graceful 4xx error messaging") that **assume** front-end and
   AI-Gateway error paths that don't exist today. The red-team agent independently flagged
   this discrepancy.
4. **Coverage of business metrics is weaker than Quokka's A0** — Rovodev P0-3 cleans up dead
   `MetricKey`s but doesn't propose the `surface`/`outcome`/`experience` vocabulary that
   makes the OKR measurable. Quokka A0 does both.

---

## What Quokka is missing (and how to compensate)

If you pick Quokka as-is, three things from Rovodev's governance must be **bolted on**:

| Missing in Quokka | Compensation from Rovodev |
|---|---|
| Explicit non-goals + historical sanity check | Adopt `03-RISKS-AND-NON-GOALS.md` verbatim |
| UX impact classification (forces honest framing) | Adopt `04-USER-EXPERIENCE-IMPACT.md` §2 (A/B/C/D/E) as a required PR-description field |
| PR-authoring checklist (counter-metric + rollback recipe) | Adopt `02-PR-SEQUENCING-PLAYBOOK.md` cross-cutting hygiene |

And from Tide v2:

| Missing in Quokka | Compensation from Tide v2 |
|---|---|
| Test coverage debt (utility/threading P0-blast, 0 tests) | Adopt Tide P3-1 as a Week-1 sub-PR |
| Detekt rule for `LaasLoggerFactory` | Adopt Tide P3-3 |

---

## What Quokka is *wrong* about (and must be removed)

If you pick Quokka, you must drop:

* **B2–B5 (real handler implementation)** — crosses "no user-facing behaviour change"
  constraint; this is the team's roadmap work, not platform improvement.
* **B6 (real nudge throttle)** — endpoint has zero production consumers today
  (verified — only acceptance tests reference it). Building logic for an unused endpoint
  is premature.
* **B7 (per-tenant LLM budget gate)** — depends on real handler existing; pre-handler
  it's a no-op (default `Int.MAX_VALUE` cap).
* **B8 (workspace coalescing)** — Quokka itself defers it; depends on validating
  workspace-shareability of insights, which is unknown.
* **B0 (MCP tool-discovery cache)** — `IntegrationServiceToolProvider` is injected only by
  `StratusTestController` (verified — single grep hit). Optimising test-only code is wrong
  tier. **Reconsider when MCP becomes part of the real handler.**

---

## Quokka — final scoped scope

After amendments, "picking Quokka" really means shipping:

| From Quokka (Track A) | Status |
|---|---|
| **A0** — Business metric vocabulary + per-endpoint histograms | ✅ Ship |
| **A1** — Redis client + `ProactiveAiCache` primitive | ✅ Ship |
| **A2** — AsyncTask idempotency guard | ✅ Ship (depends A1) |
| **A3** — Visibility-extension hardening | ✅ Ship |
| **A4** — Error classification (Permanent/Transient) | ✅ Ship (depends A2) |
| **A5** — FF memoisation | ✅ Ship |
| **A6** — `queueCapacity` + AI-Gateway timeout fix | ✅ Ship (the highest-impact item in any plan) |

| From Quokka (Track B) | Status |
|---|---|
| B0 (MCP cache) | ❌ Drop — test-only code path |
| B1 (reactive Stratus) | ⚠️ Keep as P2 (verified valid, but lower urgency) |
| B2–B5 (real handler) | ❌ Drop — roadmap work, not platform |
| B6 (nudge throttle) | ❌ Drop — no upstream consumer |
| B7 (budget gate) | ❌ Defer until handler ships |
| B8 (coalescing) | ❌ Defer (Quokka itself defers) |

| From Rovodev (bolted on) | Status |
|---|---|
| `03-RISKS-AND-NON-GOALS.md` | ✅ Adopt as governance |
| `04-USER-EXPERIENCE-IMPACT.md` (UX classification) | ✅ Adopt as PR-description requirement |
| P0-1 (SLO file + runbooks) | ✅ Add (Quokka A0 doesn't cover this) |
| P0-3 (dead MetricKey cleanup) | ✅ Add (rides with A0) |
| P1-3 (E2E synthetic canary) | ✅ Add (none of Quokka's items cover this failure class) |

| From Tide v2 (bolted on) | Status |
|---|---|
| Test coverage for `utility/threading/` (P0-blast, 0 tests) | ✅ Add |
| Detekt rule for `LaasLoggerFactory` | ✅ Add |

---

## The honest truth

**The best answer to "which plan would you pick" is "the integrated plan in
`06-INTEGRATED-PLAN-V2.md`"** — because all three plans have unique-and-correct findings
and unique-and-correct gaps. The synthesis is **strictly better** than any single plan.

But if you genuinely must pick one of the three:

1. 🥇 **Quokka — Track A only**. Has the most code-verified bugs (queueCapacity, timeout,
   FF memoise). Has the cleanest architectural primitives (Redis abstraction, error
   classification). Has the safest rollout strategy (Statsig flag per item, default off).

2. 🥈 **Rovodev**. Best governance (UX classification, non-goals, sequencing playbook).
   Most honest about the team's pre-launch posture. But misses the three Quokka-only bugs.

3. 🥉 **Tide v2**. Best meta-analysis. Best surgical file:line precision. But it's a
   synthesis-of-syntheses; the actual recommendations it carries forward are mostly
   Quokka's. Picking Tide v2 is approximately picking Quokka with extra editorial.

---

## The one question that beats every plan

> *"When does the real `RovoInsightsGenerationTaskHandler` replace its stub body, and what
> is the projected daily QPS profile?"*

Until this is answered:

* All three plans are ~50 % precondition-building with no validation traffic.
* Capacity sizing (I-14 / Quokka-implicit / Rovodev P1-1) is a guess.
* AI-Gateway timeout target (60 s? 30 s?) is a guess.
* Redis cache TTL strategy (I-08 / Quokka A1) is a guess.

**Recommendation:** Block the Week-3 kick-off (when Redis client lands) on a one-paragraph
answer from the feature owner. The answer is three numbers: (a) projected daily-active
tenants, (b) average insights generated per active tenant per day, (c) target ship date.

Without those three numbers, **no platform plan can rank items honestly** — they can only
rank items defensibly.
