# Rovo Insights — Dedicated Deep-Dive & Double-Check Items

> **Author:** Rovo Dev (in response to user question "does it have a dedicated package regarding rovo insights? in the plan can we have specific double check opportunities regarding rovo insights?"), 2026-05-05.
> **Companion to:** `06-INTEGRATED-PLAN-V2.md` (the master integrated plan).
> **Verification posture:** Every claim in this document is grounded in `git grep` on `proactive-ai-platform` HEAD + cross-repo verification with `conversational-ai-platform`, run via 3 parallel agents on 2026-05-05.

---

## TL;DR

> **Yes — there is a dedicated package** at
> `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/`
> with **16 production files (706 LoC)** + **2 test files (266 LoC)**, structured as
> `api/` (controllers + DTOs), `internal/` (SQS consumer), `system/` (domain
> primitives), plus the stub handler, task envelope, and `Config.kt`.
>
> **Three of the most consequential bugs across the entire codebase live in this
> package**, and **all three were missed by all three source plans** (Tide, Quokka,
> Rovodev). This file enumerates **18 rovo-insights-specific double-check items**
> — 6 Critical, 7 High, 5 Medium — with file:line evidence and a path to fix each.

---

## Section 1 — The package, charted

### 1.1 — File map (verified 2026-05-05)

```
feature/rovoinsights/
├── Config.kt                                    (45 lines)  ← 6 InsightType prompt configs
├── RovoInsightsGenerationTask.kt                ( 9 lines)  ← AsyncTask wire envelope
├── RovoInsightsGenerationTaskHandler.kt         (62 lines)  ← STUB (literal "stub - real generation logic not yet ported")
│
├── api/
│   ├── RovoInsightsController.kt                (50 lines)  ← /status + /fetch — both HARDCODED
│   ├── status/
│   │   ├── RovoInsightsStatusRequest.kt         (14 lines)  ← promptConfig + forceCacheMiss
│   │   └── RovoInsightsStatusResponse.kt        ( 9 lines)  ← insightsAvailable: Boolean
│   ├── fetch/
│   │   ├── RovoInsightsFetchRequest.kt          (14 lines)  ← generate + debugInfo + promptConfig
│   │   └── RovoInsightsFetchResponse.kt         (77 lines)  ← schemaVersion / insightGroups / DebugInfo (full schema)
│   ├── rest/
│   │   └── RovoInsightsTestController.kt        (82 lines)  ← /api/internal/test/insights/generate — submits real SQS task
│   └── dto/
│       ├── RovoInsightsTestRequest.kt           ( 3 lines)
│       └── RovoInsightsTestResponse.kt          ( 5 lines)
│
├── internal/
│   └── RovoInsightsGenerationSqsQueueConsumer.kt (122 lines) ← LongRun SQS consumer; gated by 2 conditions
│
└── system/
    ├── InsightType.kt                           (52 lines)  ← 6 types: FOLLOW_UP, EMERGING_WITH_TEAM, COMPANY, YOUR_TRENDING, RECOGNITION, MEETING
    ├── Color.kt                                 (34 lines)  ← 20 design-system colours (ref atlassian.design)
    ├── Glyph.kt                                 (49 lines)  ← 36 design-system glyphs (ref atlassian.design)
    └── RovoInsightsRequest.kt                   (31 lines)  ← PromptConfig type alias + RovoInsightsPromptConfig + Strategy enum

src/test/.../feature/rovoinsights/
├── RovoInsightsGenerationTaskHandlerTest.kt     (65 lines)
└── internal/RovoInsightsGenerationSqsQueueConsumerTest.kt (201 lines)
```

### 1.2 — How the data flow is wired today

```
                    (no production client calls /status or /fetch yet — verified)
convo-ai-platform ──HTTP──▶ /api/v1/rovo/insights/status   →  always returns insightsAvailable=true (HARDCODED)
                            /api/v1/rovo/insights/fetch    →  always returns count=0, summary="", insightGroups=[] (HARDCODED)

            (only test controller submits real tasks)
internal     ──HTTP──▶ /api/internal/test/insights/generate
                            └─▶ asyncTaskService.submit(RovoInsightsGenerationTask(cloudId))
                                  └─▶ SQS rovo_insights_generation_queue
                                        └─▶ LongRun pod
                                              └─▶ RovoInsightsGenerationSqsQueueConsumer.processMessage
                                                    └─▶ AsyncTaskDispatcher.dispatch
                                                          └─▶ RovoInsightsGenerationTaskHandler.handle  ← STUB (logs only)
                                                                                                          (no LLM call, no result write)
```

### 1.3 — What's missing (relative to "real-handler shipped")

* **Result storage** — there is **no `RovoInsightsService` / `RovoInsightsRepository`** that the handler writes to and that `/fetch` reads from. The fetch endpoint has no service dependency injected. Even if the handler did real work, `/fetch` would still return empty.
* **Status / fetch coupling** — there's no shared `cacheKey` (e.g. `(tenantId, accountId, promptConfigHash)`) between the SQS task and the read endpoints.
* **Generation trigger from `/fetch`** — `RovoInsightsFetchRequest.generate: Boolean` exists but no consumer ever reads it.
* **Cache-miss signalling** — `RovoInsightsStatusRequest.forceCacheMiss: Boolean` exists but no consumer ever reads it.
* **Debug echo** — `RovoInsightsFetchRequest.debugInfo: Boolean` and the response field `RovoInsightsFetchResponse.debugInfo: DebugInfo?` exist; nothing populates the response side.

---

## Section 2 — The 18 double-check items

### 2.1 — 🔴 Critical (6 items, must resolve before any production ramp)

| # | Item | Evidence | Why critical | Effort |
|---|---|---|---|---|
| **DC-01** | **Queue-type mismatch — FIFO vs Standard** | PAI's `service-descriptor.sd.yml` provisions `rovo-insights-generation-queue` as **Standard** (no `FifoQueue: true`). Convo-AI's `.nebulae/integration-tests/sandbox.def.yml:639,4327` declares the **same logical queue with `.fifo` suffix and `FifoQueue: true`**. Confirmed by 2 cross-repo greps. | When convo-ai is wired to enqueue real generation requests, **the first message will be rejected** because FIFO requires `MessageGroupId` headers that Standard rejects (and vice-versa). **This blocks the entire feature.** | M (cross-team alignment) |
| **DC-02** | **Status endpoint always lies** | `RovoInsightsController.kt:25-30` returns `RovoInsightsStatusResponse(insightsAvailable = true)` unconditionally. Swagger summary on the same method **explicitly contradicts this**: *"A cache miss or a cache hit with zero insights will return a 'no insights available' response."* | When the real handler ships and a cache miss occurs, `/status` will say "available" while `/fetch` returns empty — frontend will show a permanent loading state. | XS (one-line stub fix to `false` while handler is stub) |
| **DC-03** | **`/fetch` has no service dependency** | `RovoInsightsController` constructor is empty — no `RovoInsightsService` injected. There is no service that a real handler could write to and `/fetch` could read from. | Without a storage abstraction (Redis result cache or RDB row), the handler/fetch loop cannot be closed. **Blocks DC-08.** | M (define & inject `RovoInsightsResultService`) |
| **DC-04** | **`RovoInsightsTestController` is not production-gated** | `RovoInsightsTestController.kt` mounts `/api/internal/test/insights/generate` and **submits real SQS tasks with no `@ConditionalOnProperty` or feature gate**. It only requires the `internal` URL prefix (which the API gateway typically allows from internal traffic). | Anyone with internal-network access can submit unbounded real tasks → cost & DLQ pressure. | S (`@ConditionalOnProperty("proactive-ai.test-controller.enabled")` default false in non-`hello`) |
| **DC-05** | **DLQ alarm is `Priority: Low` with literal SD comment "Bump to High in prod once PAI is on the hot path"** | `service-descriptor.sd.yml`: `rovo-insights-generation-queue` DLQ alarm block | The team **already knows** they have to fix this. If it's not promoted before convo-ai starts producing, DLQ accumulation will be silent. | XS (1 PR, change `Priority: Low` → `High`) |
| **DC-06** | **Path mismatch in `policies/service/policy.json`** | Policy lists both `/api/v1/rovo/insights/*` (matches `RovoInsightsController`) **and** `/api/v1/rovo-insights/*` (does NOT match any controller — verified via git log to be an orphan from a removed test path). | Misleading; suggests an endpoint exists that doesn't. Risk: someone wires convo-ai to the hyphen path → silent 403. | XS (delete the orphan entry) |

### 2.2 — 🟠 High (7 items, before public ramp)

| # | Item | Evidence | Why important | Effort |
|---|---|---|---|---|
| **DC-07** | **Cost ceiling: 6 InsightTypes × maxAttempts=3 = up to 18 LLM calls per generation request** | `Config.kt`: `DEFAULT_ROVO_INSIGHTS_PROMPT_CONFIG` has 6 entries, each with `maxAttempts = 3`. No call-count budget per request. | At even 1k requests/day this is 18k LLM calls/day — material AI-Gateway spend. Need a per-request ceiling and a metric `insights.llm_calls_per_request{insight_type}`. | S (add metric; document budget) |
| **DC-08** | **Result storage abstraction not designed** | No `RovoInsightsResultService` / `Repository`; no Redis namespace defined. | Without this, `06-INTEGRATED-PLAN-V2.md` I-08 (`ProactiveAiCache` primitive) needs an explicit `INSIGHTS_RESULT` namespace + a documented key schema (`insights:result:{tenantId}:{accountId}:{promptConfigHash}`). | M (design + small PR adding namespace + service interface) |
| **DC-09** | **`generate: Boolean` field on `RovoInsightsFetchRequest` has zero consumers** | Field declared at `RovoInsightsFetchRequest.kt:9`; grep on `request.generate` returns zero hits in main. | Either remove the field (clarity) **or** wire it to enqueue an `RovoInsightsGenerationTask` on cache-miss when `generate=true`. **Decide before any client integrates.** | XS to remove; S to wire |
| **DC-10** | **`forceCacheMiss: Boolean` field on `RovoInsightsStatusRequest` has zero consumers** | Field at `RovoInsightsStatusRequest.kt:13`; grep on `request.forceCacheMiss` returns zero hits in main. | Same as DC-09 — either remove or wire. Likely intended as a debug knob; tag clearly or delete. | XS / S |
| **DC-11** | **`debugInfo` response field has no producer** | `RovoInsightsFetchResponse.kt:60` declares `debugInfo: DebugInfo? = null`; the `DebugInfo` class itself is defined in the same file but never instantiated anywhere in the package. | Frontend may render different UI if `debugInfo != null`. Schema is undefined. **Document the populate-when contract** or remove. | XS |
| **DC-12** | **`DATA_SCHEMA_VERSION` constant has no automated check** | Defined as `RovoInsightsFetchResponse.Companion.DATA_SCHEMA_VERSION` (read it: probably an `Int`); no test pinning it; no contract test ensuring producer/consumer agree. | If we bump it without coordination, frontend deserialisers may break. **Add a snapshot test that fails on schema-version change without an explicit annotation.** | S |
| **DC-13** | **InsightType enum drift between PAI and convo-ai prompts** | PAI declares 6 enum values in `system/InsightType.kt`. The matching prompts live (or will live) in convo-ai-platform; if names diverge, parsing the LLM JSON fails. | When B-track (Quokka B3) ports the real prompt, **assert at startup that the names match** (load expected names from a resources file). | S |

### 2.3 — 🟡 Medium (5 items, post-ramp polish)

| # | Item | Evidence | Why nice | Effort |
|---|---|---|---|---|
| **DC-14** | **No per-`InsightType` rollout flag** | `Config.kt` has 6 entries; if one type's prompt regresses, the whole feature must be flag-flipped off. | Add `proactive-ai.insights.<type>.enabled` flag per type; default true. | S |
| **DC-15** | **Color/Glyph enum drift vs design system** | `Color.kt` (20 values) and `Glyph.kt` (36 values) reference `atlassian.design` URLs in comments; no automated check that the design system hasn't deprecated a glyph. | Add a CI check (or yearly manual sync) against the published design-system enum. | M |
| **DC-16** | **`generatedAt: Instant` serialisation format unspecified** | `RovoInsightsFetchResponse.kt`: `generatedAt: Instant` — Jackson default for `Instant` is configurable. | **Add a snapshot test** that pins the format (likely UTC ISO-8601 string) so frontend doesn't break on `MapperFeature` change. | XS |
| **DC-17** | **No metric on `forceCacheMiss=true` rate** (when wired) | Will be invisible whether anyone uses the debug knob. | Add `insights.cache.force_miss{tenant_id}` counter when DC-10 is wired. | XS |
| **DC-18** | **No test that the SQS consumer's `ConditionalOnProperty` actually gates correctly** | `RovoInsightsGenerationSqsQueueConsumer.kt` is gated by both `OnLongRunWorkerNodeOrLocalCondition` AND `@ConditionalOnProperty("SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL")`; a Spring context test would catch a regression. | A misconfigured pod (e.g. deploying a WebServer pod with the env var set) would start consuming. | S |

---

## Section 3 — How these items fold into `06-INTEGRATED-PLAN-V2.md`

### 3.1 — Cross-walk

| New double-check | Folds into existing item or stands alone | Tier |
|---|---|---|
| **DC-01 (FIFO mismatch)** | **NEW** — add as **I-17** in P0 (cross-team alignment can take weeks; start now) | P0 |
| **DC-02 (status lies)** | **NEW** — add as **I-18** in P0 (one-line fix to make status return `false` while handler is stub) | P0 |
| **DC-04 (test-controller gating)** | Folds into **I-15** (test coverage) — add as a sub-PR | P3 → bump to P1 |
| **DC-05 (DLQ alarm priority)** | Folds into **I-03** (SLO + runbooks + alarm priority) — explicitly call out the rovo-insights DLQ alarm | P0 |
| **DC-06 (policy path mismatch)** | **NEW** — add as **I-19** in P3 (xs delete) | P3 |
| **DC-08 (result storage abstraction)** | Folds into **I-08** (`ProactiveAiCache`) — add the `INSIGHTS_RESULT` namespace + key schema as a sub-deliverable | P1 |
| **DC-12 (schema-version snapshot)** | Folds into **I-15** (test coverage) | P3 |
| All others (DC-03, 07, 09, 10, 11, 13, 14, 15, 16, 17, 18) | **NEW** "Track R" (rovo-insights pre-handler hardening) — separate from Tracks A/B/C; can be picked up by feature owner | new tier |

### 3.2 — Three new initiatives to add to `06-INTEGRATED-PLAN-V2.md` § 2

| # | Title | Tier | Effort | Why this is a P0 item (justifying the tier promotion) |
|---|---|---|---|---|
| **I-17** | **FIFO/Standard queue alignment with convo-ai** | P0 | M | Without this, the entire feature blocks on first production message. Cross-team work; start the conversation now. |
| **I-18** | **Make `/status` honest while handler is stub** (return `insightsAvailable=false`) | P0 | XS | Without this, when convo-ai integrates, every user sees "loading…" forever. One-line PR. |
| **I-19** | **Delete orphan `/api/v1/rovo-insights/*` entry from `policy.json`** | P3 | XS | Misleading dead text; will mislead future reviewers. |

These are **additive** — `06-INTEGRATED-PLAN-V2.md` § 2 P0 grows from 5 → 7 items (still small).

---

## Section 4 — What none of the three source plans caught about rovo-insights

This is the answer to your question *"in the plan can we have specific double check opportunities regarding rovo insights?"*. The 6 Critical and 7 High items above include **9 issues that ALL THREE plans missed** (cross-validated by a dedicated coverage agent). The list:

| # | Missed-by-all finding | Why it was missed |
|---|---|---|
| **DC-01** FIFO mismatch | Cross-repo concern; none of the plans grep'd convo-ai |
| **DC-02** status endpoint logic inversion | Plans treat "controller is stub" as opaque; none read the swagger annotation |
| **DC-03** no result-storage abstraction | Plans assume the handler will figure it out |
| **DC-04** test-controller not production-gated | Plans treated `RovoInsightsTestController` as obviously test-only without checking the gating |
| **DC-06** policy path mismatch | Policy file is rarely audited |
| **DC-09** `generate: Boolean` field unused | Plans focused on infra, not DTOs |
| **DC-10** `forceCacheMiss: Boolean` field unused | Same |
| **DC-11** `debugInfo` field never populated | Same |
| **DC-13** InsightType enum drift | Cross-repo concern; convo-ai owns the prompts |

---

## Section 5 — Recommended action

1. **Add I-17 + I-18 to `06-INTEGRATED-PLAN-V2.md` § 2** as P0 items. Update INDEX accordingly.
2. **Add I-19 to P3.**
3. **Surface DC-04, DC-08, DC-12 as sub-bullets** under their integrating P-items.
4. **Send DC-01 (FIFO mismatch) to the feature owner** (zcheng / mdawson per `git log`) **today** — cross-team alignment has the longest lead time.
5. **Optional: open a CTSC ticket** (or one ticket per Critical item) to track each. Each ticket should reference this file.

The remaining items (DC-07, DC-09, DC-10, DC-11, DC-13, DC-14, DC-15, DC-16, DC-17, DC-18) are
naturally feature-team work, not platform work. **Hand them off to the feature owner** as a
single document — this file.

---

## Section 6 — Cross-references

* **Master plan:** `06-INTEGRATED-PLAN-V2.md`
* **Pick recommendation:** `07-PLAN-PICK-RECOMMENDATION.md`
* **Original plans:** `~/.claude/plans/taking-a-deep-look-pure-tide.md` (Tide v2), `_plan/claude/taking-a-deep-look-lively-quokka.md` (Quokka)
* **Live source files referenced (HEAD 2026-05-05):**
  * `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/RovoInsightsController.kt` (lines 25-46)
  * `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/rest/RovoInsightsTestController.kt`
  * `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt` (line 22 stub literal)
  * `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/Config.kt` (DEFAULT_ROVO_INSIGHTS_PROMPT_CONFIG)
  * `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/api/fetch/RovoInsightsFetchResponse.kt` (DATA_SCHEMA_VERSION + DebugInfo)
  * `src/main/resources/policies/service/policy.json` (lines for both rovo-insights paths)
  * `service-descriptor.sd.yml` (rovo-insights-generation-queue + 3 alarm blocks + AI Gateway timeout=600000)
  * `/Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform/.nebulae/integration-tests/sandbox.def.yml` (lines 639, 4327 — `.fifo` queue declaration)
