# Risks and Non-Goals

> **What this plan deliberately does NOT propose**, and why.
>
> Every entry here is a candidate that one of the four investigation
> sub-agents (perf / COGS / reliability / quality) suggested but that
> failed at least one of these tests:
>
> 1. **Reality check** — the precondition for the gain doesn't exist
>    (e.g., "cache LLM responses" against a stub handler).
> 2. **Historical check** — the team already tried/removed something
>    similar; undoing it would re-introduce the original problem.
> 3. **User-behaviour-preserving check** — would change visible
>    user experience (the user said: don't change ranking semantics
>    etc.).
> 4. **Cost-of-large-effort check** — large refactor with no
>    quantifiable goal-metric gain.
>
> Each entry names the sub-agent that suggested it (so it's
> reviewable / re-litigable), the reason for rejection, and the
> **trigger condition** under which it should be reconsidered.

---

## Section 1 — Rejected because precondition doesn't exist

These are "great ideas after the real Rovo Insights handler ships;
premature today".

---

### NG-1 — "Implement Redis @Cacheable for AI-Gateway responses"

* **Suggested by.** COGS sub-agent (Finding #1, claimed
  $10.8M-$25.2M/year savings).
* **Why rejected.**
  `feature/rovoinsights/RovoInsightsGenerationTaskHandler.kt` is
  literally a stub (verified 2026-05-05 — body says
  *"stub - real generation logic not yet ported"*). There is no
  live LLM traffic to cache. Designing a cache key / TTL strategy
  before knowing the real generation algorithm risks either:
  * a key that is too narrow → 0 % hit rate,
  * a key that is too wide → stale insight served to wrong tenant.
* **Reconsider when.** The real handler ships **and** observed
  AI-Gateway egress costs cross a threshold worth a 2-PR
  optimisation. At that point the *real* algorithm dictates the
  *real* cache key.
* **Cross-reference.** ADR-010 in
  `cc/14-architectural-decisions`.

---

### NG-2 — "Add streaming WebFlux endpoint for AI-Gateway responses"

* **Suggested by.** COGS sub-agent (Finding #7).
* **Why rejected.**
  * No current production endpoint that needs streaming (the
    only AI-Gateway-facing endpoints are `StratusTestController`
    test routes).
  * Spring MVC ↔ WebFlux migration is a large blast-radius
    refactor.
  * Streaming is a **nudge-product** decision (does the user
    actually need progressive rendering?), not a back-end
    decision.
* **Reconsider when.** A product spec lands explicitly requiring
  streaming for a user-facing surface, AND the AI-Gateway client
  exposes a streaming SSE contract for that use case.

---

### NG-3 — "Pre-design batching for the (future) Rovo Insights handler"

* **Suggested by.** COGS sub-agent (Finding #8).
* **Why rejected.** Same as NG-1: pre-judging a stub. Batching is
  worth it only if (a) generation calls are bursty and (b) the
  generation API supports batched requests with a worthwhile
  cost-multiple. Both unknown today.

---

## Section 2 — Rejected because of historical decision

These would undo or contradict an intentional decision the team
made earlier.

---

### NG-4 — "Restore the `ddev-env` removed in PR #52"

* **Suggested by.** None (defensive listing — agents could have).
* **Why rejected.** PR #52 (`zcheng/remomve-ddev-env`,
  ``00d8323``) was an **intentional** cleanup. Re-introducing it
  would re-introduce its maintenance burden. If a developer
  workflow needs the equivalent, the answer is to add a *new*
  workflow on top of `nebulae` (which is the current standard),
  not to revert the removal.

---

### NG-5 — "Switch `rovo-insights-generation-queue` to FIFO"

* **Suggested by.** None (defensive listing).
* **Why rejected.** The `service-descriptor.sd.yml` comment
  literally says: *"Currently kept as a standard (non-FIFO) queue
  for simplicity. Switch to FifoQueue: true if needed"*. The
  team chose standard intentionally because they don't yet know
  whether per-tenant ordering matters. **No production load means
  no observed ordering bug**; switching now would lock in a
  decision before the data is available.
* **Reconsider when.** Real generation traffic shows out-of-order
  artefacts that confuse users (e.g., insight v2 served before
  insight v1 for the same content).

---

### NG-6 — "Add a custom Spring Cache abstraction"

* **Suggested by.** COGS sub-agent (implied).
* **Why rejected.** The Redis bean is already provisioned (per
  service-descriptor); adding a custom abstraction now would be
  invented infrastructure. P1-4 (idempotency keys) is the **first
  use** of the cache, on a contract that doesn't depend on the
  generation algorithm. Add `@Cacheable` only when there's a real
  caller for it.

---

## Section 3 — Rejected because would change user-visible behaviour

The user explicitly excluded these (e.g., "don't change ranking
semantics").

---

### NG-7 — "Re-rank nudges by relevance instead of recency"

* **Suggested by.** None (defensive listing — explicitly
  out-of-scope per the user's guidance).
* **Why rejected.** Would change the user-perceived nudge order
  and risks regressing acceptance-rate (the `nudge.accept.rate`
  metric per `cc/01-business-and-technical-goals` Part 3.2). Any
  ranking change must be a product-owned A/B experiment, not an
  engineering optimisation.
* **Reconsider when.** A product team owns the experiment with
  pre-registered success metrics.

---

### NG-8 — "Auto-throttle: silently drop nudge requests above
some-rate"

* **Suggested by.** Reliability sub-agent (implied as overload
  protection).
* **Why rejected.** Silent drops degrade user experience without
  surfacing the problem (acceptance-rate falls; cause invisible).
  Better to **alarm on saturation** (which P1-1's queue-depth
  alarm does) than to mask it.

---

### NG-9 — "Force one-prompt-per-tenant deduplication"

* **Suggested by.** COGS sub-agent (implied via "60-70 % cache
  hit rate" claim).
* **Why rejected.** Would mean two tenants with the same prompt
  see the same response. **Cross-tenant data leak risk** — even
  if "the same response" is generic, it's a security-review-worthy
  decision that should not be made silently as a perf
  optimisation.

---

## Section 4 — Rejected because effort vs goal-metric gain doesn't justify

---

### NG-10 — "Migrate to Spring WebFlux end-to-end"

* **Suggested by.** Perf sub-agent (Finding #4 was specifically
  about converting `.blockingGet()` calls — accepted as P2-1 —
  but the agent also implied a fuller WebFlux migration).
* **Why rejected.** The `.blockingGet()` conversion (P2-1) is
  high-leverage and small. A full WebFlux migration would cost
  weeks for an unmeasured benefit; Spring MVC's async support is
  sufficient at PAI's scale.
* **Reconsider when.** A specific endpoint shows a measurable
  thread-pool exhaustion problem under production load, AND the
  problem can't be solved by tuning thread-pool sizing.

---

### NG-11 — "GraalVM native-image build"

* **Suggested by.** None (defensive listing — common
  AI-suggestion).
* **Why rejected.** Cold-start time isn't an OKR metric. Spring
  Boot 7.10 supports native-image but the workflow / ecosystem
  cost (reflection config, Kotlin support gaps in some libs)
  outweighs the benefit at PAI's scale.

---

### NG-12 — "Switch from Statsig to a self-hosted feature-flag
service"

* **Suggested by.** None (defensive listing).
* **Why rejected.** Statsig is the Atlassian-blessed feature-flag
  provider. Switching would diverge from the platform; the cost
  is permanent.

---

### NG-13 — "Rewrite `MessageQueueConsumerMiddleware` from
`@Component` + interceptor to coroutine-flow"

* **Suggested by.** Code-quality sub-agent (implied as
  "modernisation").
* **Why rejected.** The current middleware works; it's tested;
  ADR-006 establishes the pattern. A rewrite would risk
  context-replay regressions for zero throughput gain.

---

### NG-14 — "Add a circuit-breaker library (Resilience4j /
Hystrix)"

* **Suggested by.** Reliability sub-agent (implied as
  resilience).
* **Why rejected.**
  * The mesh egress retry policies
    (`retryOn5xxAnd429Policy`) cover the most common case.
  * Adding a library multiplies failure modes; adding it
    *correctly* (timeout + retry + circuit + bulkhead)
    requires careful tuning.
  * The current bottleneck (per ADR-002 + the stub handler) is
    not "too many failures cascading"; it's "no real load yet".
* **Reconsider when.** An observed cascade (one downstream
  failing → PAI dies) is captured in a post-mortem.

---

### NG-15 — "Migrate `service/metric` to Micrometer Prometheus
backend instead of SignalFx"

* **Suggested by.** None (defensive listing).
* **Why rejected.** SignalFx is the Atlassian-blessed metric
  backend (per the observability sidecar). Switching would
  diverge from Tome / Splunk integration.

---

## Section 5 — Anti-patterns to avoid in any future PR

Independent of the 12 initiatives, these are general anti-patterns
that **every PR review should flag**.

* **Adding `private val log = LoggerFactory.getLogger(...)`**
  outside the `logging/` package — use `LaasLoggerFactory`
  (per ADR-009; will be enforced by P2-3's detekt rule).
* **Adding `@Value("\${MICROS_ENV:}")`** — use the typed
  `MicrosEnvironmentType` bean (per ADR-007 / ADR-008; P3-1
  closes the lone outstanding violation).
* **Adding a per-request loop that calls AI-Gateway / Integrations
  Service / IdGatekeeper one-by-one** — N+1 risk; batch or cache.
* **Adding a metric without a tag-cardinality budget** — a
  `tenant_id` tag on a high-rate metric will explode SignalFx
  series count.
* **Adding an alarm with `Priority: Low` and `Runbook: TBD`** —
  the very thing P0-1 fixes; don't recreate it.
* **Catching `Exception` and only logging** — bump an error
  metric too, otherwise the failure is silent (per the
  reliability sub-agent's Finding #4 pattern).
* **Storing user content in SQS message attributes** — message
  attributes have size cost; payload should carry user data.
* **Submitting a PR ≥ 500 LoC without a `series:` tag** — every
  PR ≥ 500 LoC should be split per the playbook in
  [`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md).
* **Submitting a PR without an AIX ticket reference** — even
  for "noissue" config changes, the ticket gives historical
  traceability (per `cc/13-full-history-catalog` Part 3 — 75 %
  of human PRs already follow this convention).
* **Reverting `[Renovate]` / `[autodev-bot]` PRs without
  understanding the dep-bump motivation** — these are usually
  CVE patches.

---

## Section 6 — Re-evaluation triggers

This plan should be **re-litigated** when any of these happen:

| Trigger | What to re-evaluate |
|---|---|
| Real Rovo Insights handler ships | Promote NG-1, NG-3 (caching, batching) from "rejected" to "consider as P1/P2"; promote P1-4 PR-2 (idempotency override) to immediate |
| OKR moves above ~1.0M / month | Re-evaluate P1-1 (LongRun max) for further lift to 10+ |
| AI-Gateway shipping a streaming SSE contract | Re-evaluate NG-2 (WebFlux streaming) |
| Out-of-order generation observed in production | Re-evaluate NG-5 (FIFO queue) |
| First production incident has post-mortem mentioning "cascade" | Re-evaluate NG-14 (circuit breaker) |
| Test:source ratio falls below 25 % (regression) | Promote P3-2 (controller tests) priority |
| `RISK-001` (Zhangbin = 82 % of human commits) worsens | Promote P3 hygiene PRs to top of next-quarter plan as on-ramp work for new contributors |

---

## Cross-references

* [`00-INDEX.md`](00-INDEX.md) — what we WILL do.
* [`01-PRIORITISED-INITIATIVES.md`](01-PRIORITISED-INITIATIVES.md) — full initiative detail.
* [`02-PR-SEQUENCING-PLAYBOOK.md`](02-PR-SEQUENCING-PLAYBOOK.md) — how to ship those.
* `../../codebase_understanding/architecture/cross-cutting/14-architectural-decisions.rst` — the 13 ADRs that capture the team's earlier decisions (the ones we're respecting here).
