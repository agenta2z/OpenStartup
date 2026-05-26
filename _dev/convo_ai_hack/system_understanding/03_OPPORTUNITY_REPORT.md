# Opportunity Report — Ranked by Impact × Risk × Complexity

---

## ⚠️ DATA-SOURCE TRANSPARENCY (read before acting on rankings!)

**This Round-1 ranking pre-dates the Round-3 live-data unlock.** Several priorities have changed once we got primary-source data from the Tome SLO control-plane (Phobos API). When the rankings here conflict with later docs, **trust the later doc**.

| Doc | Status | What it overrides |
|---|---|---|
| `03_OPPORTUNITY_REPORT.md` (this file) | Round 1 baseline — inference-based | Original ranking |
| `07_DATA_DRIVEN_FINDINGS.md` §G.3 | Round 2 refinement | Strategic-context corrections (migration to PAI) |
| **`09_LIVE_TELEMETRY_FINDINGS.md` §G** | **Round 3 — primary data** | **Final ranking; supersedes both above** |

**Specifically updated in R3:**
- **OPP-02** (Rovo Chat SLO breach pattern): downgraded P0 → **P1** (live data: 0 currently-active breaches; only 7 PIRs in 6 months — much less acute than feared)
- **OPP-06** (TWG auto-revert detector): downgraded P1 → **P2-L** (TWG doesn't index this repo)
- **OPP-08** (PIR follow-up tracking): upgraded P1 → **P0** (live data: 5/7 PIRs still in Draft status — worse than estimated)
- **OPP-09** (Strangler-fig migration plan): upgraded P1 → **P0** (migration is happening; needs explicit plan)
- **OPP-13** (MetricKey extension pattern): downgraded P1 → **P3** (code is leaving the repo)
- **New: OPP-21–25** added (see doc 09 §G for full list)

**Data sources used to build *this* report (Round 1 only):**
- Static code analysis (cat/grep/AST)
- SignalFx detector Terraform IaC
- Confluence weekly oncall logs (text-only)
- Code-understanding Sphinx tree

**Data sources NOT used (Round 1):** Live Splunk, live SignalFx, live Tome SLOs, Databricks, distributed traces, Jira HOT project comments/PIR action items. R3 partially closed the gap; the rest remains TODO.

---

> Methodology: Each opportunity scored 1-5 on three axes (Impact = customer/cost/reliability blast-radius if fixed; Risk = risk of fix introducing new issues; Complexity = engineer-weeks). Weighted score = Impact × 2 − Risk − Complexity. **Type code:** 🔧 fix bug · ⚡ feature · 🧹 refactor · 📊 observability · 🛡 resilience · 🔄 process.

## Ranking Summary (sorted by weighted score)

| Rank | Code | Type | Title | Impact | Risk | Complexity | Score | Tier |
|------|------|------|-------|-------:|-----:|-----------:|------:|------|
| 1 | OPP-01 | 🔧 | TenantContextRunnerImpl MDC/suspend propagation fix | 5 | 2 | 3 | **5** | 🔴 P0 |
| 2 | OPP-02 | 🛡 | Per-route AGG client circuit breaker + bulkheads | 5 | 2 | 3 | **5** | 🔴 P0 |
| 3 | OPP-03 | 🛡 | LLM rate-limit pre-flight + token-bucket smoothing | 5 | 2 | 3 | **5** | 🔴 P0 |
| 4 | OPP-04 | 🛡 | Graceful-degradation pattern (cache+fallback+bulkhead) | 5 | 3 | 4 | **3** | 🟠 P1 |
| 5 | OPP-05 | 📊 | Staging thread-saturation alarm + scaling-first runbook | 4 | 1 | 2 | **5** | 🟠 P1 |
| 6 | OPP-06 | 📊 | Auto-revert candidate detector (PR-near-HOT correlation) | 4 | 2 | 3 | **3** | 🟠 P1 |
| 7 | OPP-07 | 📊 | Pollinator coverage expansion (GraphQL/X-Forwarded-Host/SVG) | 4 | 1 | 4 | **3** | 🟠 P1 |
| 8 | OPP-08 | 🔧 | Re-enable MCP detectors after stabilization | 3 | 1 | 2 | **3** | 🟡 P2 |
| 9 | OPP-09 | 🔧 | Complete async TCS client migration (last sync callers) | 4 | 2 | 3 | **3** | 🟠 P1 |
| 10 | OPP-10 | 📊 | Heartbeat SLO tuning (anti-noise) | 3 | 1 | 1 | **4** | 🟡 P2 |
| 11 | OPP-11 | 🔄 | "Where to file FE/FG-only issues" service-picker hint | 3 | 1 | 1 | **4** | 🟡 P2 |
| 12 | OPP-12 | 🔄 | PIR-owner mandatory field at on-call handover | 3 | 1 | 1 | **4** | 🟡 P2 |
| 13 | OPP-13 | 🧹 | Module-local MetricKey extension migration (kill 3,252-line enum) | 4 | 2 | 4 | **2** | 🟢 P3 |
| 14 | OPP-14 | 🧹 | Experience.kt decomposition (SVC1, 1,752 LoC) | 3 | 3 | 4 | **−1** | 🟢 P3 |
| 15 | OPP-15 | 🛡 | AsyncAgentInMemoryJobStore → Redis-backed persistence | 4 | 4 | 4 | **0** | 🟢 P3 |
| 16 | OPP-16 | 📊 | Detector runbook-URL coverage (every detector → runbook) | 3 | 1 | 2 | **3** | 🟡 P2 |
| 17 | OPP-17 | 🧹 | Helm worker manifest dedup (3× 763-line clones) | 2 | 1 | 2 | **1** | 🟢 P3 |
| 18 | OPP-18 | 🧹 | Anthropic provider dedup (4× ~975 LoC each) | 2 | 2 | 3 | **−1** | 🟢 P3 |

---

## 🔴 P0 OPPORTUNITIES (do first)

### OPP-01 🔧 Fix `TenantContextRunnerImpl` MDC/suspend propagation

**Why it matters (production evidence):**
- Open root cause behind ≥6 HOTs: HOT-300438 (Mar 4-5), HOT-300449 (Mar 7-9, **164 threads affected**), HOT-300485, HOT-300504, HOT-300517, HOT-300597, HOT-300989, HOT-301572
- RCA explicitly states: *"The core bug in `TenantContextRunnerImpl` persists. Any endpoint converted to `withTenantContextSuspend` will crash."*
- **Blocks ALL suspend migrations** — every Tomcat thread-exhaustion HOT in the past 3 months traces back to this
- Each HOT in this family takes **2-5 days to fully resolve** (revert + hotfix + retro) → ~30 engineer-days lost since Feb

**Impact:** 5/5 — blocks entire suspend migration roadmap; one of the two recurring SEV1-class root causes.

**Risk:** 2/5 — fix is well-understood (move `addTenantContext` inside the coroutine context carrying `RequestAttributes`, OR propagate `RequestAttributes` explicitly before the call). Risk is purely in scope creep (touches many call sites).

**Complexity:** 3/5 — 2-3 engineer-weeks: (1) fix `TenantContextRunnerImpl`, (2) propagation regression test, (3) DI-time lint rule that fails build if a new suspend method exists in `*Client` without a context-propagation companion test.

**Concrete proposal:**
1. Implement `TenantContextElement: CoroutineContext.Element` that captures `RequestAttributes` + MDC + Atlassian baggage headers
2. Refactor `withTenantContextSuspend(...)` to install the element before invoking user code
3. Add `TenantContextPropagationTest` base class — every `*Client.kt` suspend method gets a paired contract test that asserts MDC + tenant + baggage survive 1+ coroutine boundary
4. Add detekt/ArchUnit rule blocking new `*Client.kt` suspend methods without a paired test

**Owner suggestion:** Foundation team (per HOT-300485 ownership). Could partner with the engineers who patched PR-22983 (Yash, Alex).

**Cite:** [Confluence gai/6980681738 §Cross-cutting #1](https://hello.atlassian.net/wiki/spaces/gai/pages/6980681738)

---

### OPP-02 🛡 Per-route AGG client circuit breaker + bulkheads

**Why it matters:**
- Multiple HOTs (HOT-300504, HOT-300517) had GraphQL/AGG as the proximate cause of cascading thread exhaustion
- RCA recommendation: *"split the AGG circuit breaker per route"*
- Currently a **single shared CB** means one slow GraphQL route can starve every other route
- Bulkheads also limit blast-radius when a single upstream (e.g., `ai-3p-connector`) degrades

**Impact:** 5/5 — would have prevented at least 3 HOTs directly; reduces correlation between routes.

**Risk:** 2/5 — well-known Resilience4j pattern; the only risk is mis-tuning thresholds.

**Complexity:** 3/5 — 2 engineer-weeks. Refactor AGG client to keyed circuit breakers + thread-pool bulkheads (one per critical route group: GraphQL query / GraphQL mutation / REST / streaming).

**Concrete proposal:**
1. Wrap `AGGClient.executeQuery(route, ...)` with `Resilience4jCircuitBreakerRegistry.circuitBreaker(routeGroup)`
2. Define route groups: `agg.query.user`, `agg.query.work`, `agg.mutation.*`, `agg.subscription.*`
3. Pair with bounded `ThreadPoolBulkhead(max=N, queueSize=Q)` per group
4. Wire FF for staged rollout
5. Add per-group circuit-breaker `state` gauge in SignalFx; emit `circuit_breaker_state_transition` count

**Cite:** [Confluence gai/6980681738 §Cross-cutting #2](https://hello.atlassian.net/wiki/spaces/gai/pages/6980681738), HOT-300504/-300517

---

### OPP-03 🛡 LLM rate-limit pre-flight + token-bucket smoothing

**Why it matters:**
- HOT-300918 (Apr 2) + HOT-301437 (Apr 16) — **Rovo Chat exceeded 80M TPM cap TWICE in 2 weeks**
- Each excursion triggers AI Gateway 429s → customer-visible streaming failures
- No client-side smoothing today; we simply rely on AI Gateway to throttle (which fails when burst pattern arrives in <30s)

**Impact:** 5/5 — paged TWICE in 2 weeks; recurrence near-certain without action.

**Risk:** 2/5 — token-bucket is well-understood; risk is in tuning the per-tenant fairness slice.

**Complexity:** 3/5 — 2 engineer-weeks.

**Concrete proposal:**
1. Add `LlmTpmSmoother` at the AIGatewayClient boundary — pre-emptively delay/queue requests if 1-minute moving average projects >threshold (80M × 0.85 = 68M TPM headroom)
2. Token-bucket per `(provider, model)` (Anthropic, OpenAI, Atlassian) — 80M TPM / 60s = ~1.3M TPS
3. Per-tenant fairness: cap any single tenant at `tpm_budget / sqrt(active_tenants)` so a single big customer can't starve smaller ones
4. Emit `convo-ai.llm.tpm_smoother.queued`, `.shed_load`, `.delay_ms_p99` metrics
5. Wire into existing `downstream_rate_limiting.tf` detector
6. SR runbook: when smoother is engaged > 5min sustained, scale-out call

**Cite:** HOT-300918, HOT-301437, [RCA §B.3](../02_OPERATIONAL_SIGNALS.md)

---

## 🟠 P1 OPPORTUNITIES

### OPP-04 🛡 Graceful-degradation pattern for Rovo Chat (cache + fallback + bulkhead)

**Why:** `ai-3p-connector` outage repeated twice; rovo_chat_control_3p_agent_load FF amplified dependency; PIR explicitly calls this out.

**Impact:** 5/5. **Risk:** 3/5 (touches multiple call-sites). **Complexity:** 4/5 (4-6 engineer-weeks).

**Proposal:**
1. Define `ChatDegradationLevel` enum: `FULL` → `NO_3P_AGENTS` → `NO_KNOWLEDGE_FILTER` → `STATIC_RESPONSES_ONLY`
2. Per-feature `gracefulDegrade<T>(loadFn, fallbackFn, cacheKey)` wrapper with TTL cache + circuit breaker
3. `app-switcher-bff` cache for `/v1/third-party-configuration/connected-data-sources` (NavX work already started; close the loop)
4. UI hint: degraded mode badge ("3P agents temporarily unavailable")
5. Per-level emission: `convo-ai.rovo.chat.degradation_level` gauge

**Cite:** HOT-300710 ([gai/6980681738 §B.3](../02_OPERATIONAL_SIGNALS.md))

### OPP-05 📊 Staging thread-saturation alarm + scaling-first runbook

**Why:** Multiple HOTs detected only after prod-customer impact. Staging detectors exist but not for thread saturation.

**Impact:** 4. **Risk:** 1. **Complexity:** 2 (~1 engineer-week).

**Proposal:**
1. Clone `tomcat_thread_exhaustion.tf` for staging environment with lower threshold (30% minor, 50% major)
2. Wire to `aix-team` low-pri only
3. Add `convo_ai_staging_thread_saturation.tf`
4. Edit Tomcat runbook (gai/6192570939) to enforce **scaling-first ordering** before hotfix (PIR recommendation from HOT-301151)

### OPP-06 📊 Auto-revert candidate detector (PR-near-HOT correlation)

**Why:** "Hotfix pipeline too prone to failure, too long. Prioritize rollback first." (HOT-300753)

**Impact:** 4. **Risk:** 2 (false positives possible). **Complexity:** 3 (3-4 engineer-weeks).

**Proposal:**
1. Scheduled job: every 15 min, fetch HOTs in `convo-ai` opened in last 4h
2. Query Bitbucket for PRs merged to `main` in [HOT.openedAt − 6h, HOT.openedAt]
3. Score each PR: file overlap with stacktrace files (×3), changes to platform/foundation tier (×2), absence of FF gate (×2)
4. Top-scoring PR → automated comment + Slack post in `#hot-{id}` channel: *"Suspected revert candidate"*
5. Iff confidence > 0.8 AND single PR → propose automated revert PR

### OPP-07 📊 Pollinator coverage expansion

**Why:** Multiple HOTs caught by customer-report, not pollinator (HOT-300508 explicitly requests this; Feb 3 PIR calls for "wider suite").

**Impact:** 4. **Risk:** 1. **Complexity:** 4 (4-6 engineer-weeks across product teams).

**Coverage to add (priority order):**
1. **GraphQL streaming** pollinator: invoke `csmAi_generateCoachingTriggeringCondition` and similar GraphQL streaming endpoints (would have caught HOT-300438)
2. **X-Forwarded-Host** custom-domain pollinator: simulate `*.atlassian-domain.com` traffic
3. **Suspend-context propagation** pollinator: hit an endpoint that goes TCS→GraphQL→TCS and assert MDC consistency in response trace header
4. **Confluence whiteboard SVG** output pollinator (HOT Feb 17-23)
5. **Tool-schema-contract** pollinator: invoke Solution Architect with `number` type and assert (would have caught HOT-301898)

### OPP-09 🔧 Complete async TCS client migration

**Why:** Original Tomcat-exhaustion root cause (Feb 3-9). PR-22983 patched some but not all. RCA action item: "move to async TCS client completely."

**Impact:** 4. **Risk:** 2. **Complexity:** 3 (2-3 engineer-weeks).

**Proposal:**
1. Grep for remaining `tcsService.getXxx` (blocking) call sites
2. Migrate each to suspend equivalent
3. Pair with OPP-01 (TenantContextRunnerImpl fix) to ensure context survives
4. Detekt rule blocking new blocking TCS calls

---

## 🟡 P2 OPPORTUNITIES

### OPP-08 🔧 Re-enable MCP detectors after stabilization

**Why:** 3 of 4 prod MCP detectors disabled with comment *"too many errors and too little traffic to provide value"*. Quality debt accumulates silently.

**Impact:** 3. **Risk:** 1. **Complexity:** 2 (1 engineer-week).

**Proposal:**
1. Audit current MCP error rates by integration (group_by `integration`)
2. For low-volume integrations (<100 req/h), keep detectors disabled but add `convo-ai.mcp.low_volume_integration_count` gauge to track stale-integration count
3. For high-volume integrations, re-enable with realistic thresholds (e.g., 95% rel @ 30-day) per integration
4. Tag detectors with `mcp_integration_owner` so alerts route to the right team (not always convo-ai oncall)

### OPP-10 📊 Heartbeat SLO tuning (anti-noise)

**Why:** "Tune heartbeat SLO so a single 503 doesn't auto-page" (HOT-302076)

**Impact:** 3. **Risk:** 1. **Complexity:** 1 (1-2 engineer-days).

**Proposal:** Change heartbeat_availability detector from "any error in 5min window" to "2+ errors in 10min window with min_request_count=20".

### OPP-11 🔄 Service-picker hint at go/hot

**Why:** Many HOTs misrouted to convo-ai (App Switcher, Agents, Remix, Jira AI, Rovo Dev CLI).

**Impact:** 3. **Risk:** 1. **Complexity:** 1 (cross-team coordination, no code).

### OPP-12 🔄 PIR-owner mandatory field at on-call handover

**Why:** Multiple auto-HOTs (HOT-301437, -301585, -301839, -300961, -302076) left ownerless.

**Impact:** 3. **Risk:** 1. **Complexity:** 1 (process change, weekly-log template update).

### OPP-16 📊 Detector runbook-URL coverage

**Why:** Several detectors lack `runbook_url` → 3am paging without "what do I do" page.

**Impact:** 3. **Risk:** 1. **Complexity:** 2 (~1 engineer-week — write stub runbooks, link in IaC).

---

## 🟢 P3 OPPORTUNITIES (lower priority but worth backlog)

### OPP-13 🧹 Module-local MetricKey extension migration

**Why:** Central `MetricKey.kt` is 3,252 lines, single point of contention; many PRs conflict on it; my own PR-A used a module-local enum pattern to avoid touching it.

**Impact:** 4 (long-term velocity). **Risk:** 2. **Complexity:** 4 (4-6 engineer-weeks across all modules).

**Proposal:** Migrate ~50% of `MetricKey` entries to module-local enums implementing `MetricKeyLike`. Pattern proven in PRs #30308, #30309, #30334-#30343.

### OPP-14 🧹 Experience.kt decomposition (SVC1)

**Why:** 1,752 LoC composite per product. Already a spec PR (#30313).

**Impact:** 3. **Risk:** 3. **Complexity:** 4. Worth doing but only after P0/P1 are landed (refactor pressure compounds with active bugs).

### OPP-15 🛡 AsyncAgentInMemoryJobStore → Redis-backed persistence

**Why:** **Data loss on JVM shutdown** confirmed. PR-B #30309 added a shutdown-loss metric to quantify the problem.

**Impact:** 4 (silent customer-facing data loss). **Risk:** 4 (Redis is a new dep here; consistency model needs careful design). **Complexity:** 4.

**Proposal:** Use existing Redis Stream infrastructure to persist `JobStatus.PLANNING`/`EXECUTING` jobs. Replay on startup.

### OPP-17 🧹 Helm worker manifest dedup

**Why:** Already a spec PR (#30314); 3× 763-line clones currently. Low impact / low risk.

### OPP-18 🧹 Anthropic provider dedup

**Why:** Already a spec PR (#30316); 4× ~975 LoC each. **Risk is HIGH because the providers diverged for reasons** — refactoring without preserving each provider's quirks is dangerous.

---

## H. NON-CODE PROCESS OPPORTUNITIES (worth listing separately)

| # | Process change | Source recommendation |
|---|---|---|
| P-1 | Mandate ITAP tests for routing-path changes | HOT-300352 |
| P-2 | Hotfix-pipeline reliability investment (1 cycle) | HOT-300753 / HOT-300989 / HOT-301481 |
| P-3 | Add tool-schema contract tests (block PRs without one) | HOT-301898 |
| P-4 | Make `!disturbed-agents` rotation always staffed | (RCA misrouted section) |
| P-5 | Document change-freeze MIM workflow | RCA §Cross-cutting #5 |
| P-6 | Quarterly RCA-pattern review (this report is a precedent) | RCA exists but isn't yet recurring |

---

## I. How to use this report

1. **Pick a tier**: P0 if you have 6-8 weeks of capacity; P1 if 2-4 weeks; P2 for tactical sprint work.
2. **Cross-reference [04_EVIDENCE_INDEX.md](./04_EVIDENCE_INDEX.md)** to pull the exact file/HOT for any opportunity claim.
3. **For each chosen opportunity:** open a Jira epic with one of the OPP-NN codes; reference this doc.
4. **Re-run this analysis in 3 months** (next RCA at Aug 6, 2026) to validate / re-rank.

---

## J. What I deliberately did NOT recommend

These were considered and dropped:

| Idea | Why dropped |
|---|---|
| Rewriting RovoChatService.kt to be smaller | High-risk refactor on a hot module with active production bugs; sequencing wrong |
| Moving off SignalFx to OpenTelemetry | Out of scope; observability budget question, not a service-team decision |
| Custom rate-limiter inside convo-ai (vs. AI Gateway) | Duplicates AI Gateway's job; OPP-03 instead does smoother in-process |
| Generic "add more tests" | Without targeting a specific bug class, no measurable impact |
| Replacing Switcheroo with home-grown FF | Not an actual pain point — flags fire correctly when set |
| Sharded ConversationStateManager | Premature; current bottleneck is sync_session_public *call*, not concurrency |
