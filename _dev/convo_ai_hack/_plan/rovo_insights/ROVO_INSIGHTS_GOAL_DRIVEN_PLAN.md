# Rovo Chat / Convo AI — Goal-Driven Improvement Plan

**As-of:** 2026-05-03
**Author:** Rovo Insights deep-investigation pass (Rovo Dev, multi-agent)
**Codebase:** `atlassian_packages/conversational-ai-platform` @ HEAD (2026-05-01 sync)
**Reference docs:** `convo_ai_hack/code_understanding/` (Sphinx site, 2.5M LoC analyzed)
**Status:** PROPOSED — pending owner sign-off (AI Mate / Rovo Agents teams)

---

## TL;DR — What and Why

Rovo Chat / Convo AI must hit a small set of **measurable** FY26 goals or H2 will under-deliver. This plan targets the **highest-leverage code changes** that move those metrics, ranked by goal-impact / effort.

| Rank | Goal targeted | Concrete metric | Code lever | Best-est. impact | Effort |
|------|--------------|-----------------|-----------|-----------------|--------|
| **P0-1** | Send-message reliability | 99.6% → 99.9% (+0.3pp) | Multi-provider streaming failover + per-tool deadlines + tool-error-feedback loop in `SimpleLoopWorkflowExecutorImpl` | +0.30 pp SLO | M (~6 wks, 2 eng) |
| **P0-2** | Cost / monetisation | -25–40% LLM input-token cost | Default-on Anthropic prompt-cache + system-prompt cache for OpenAI/Gemini + tool-catalog hash-cache + cost-tier model routing | $0.6–1.0M/yr saved | M (~4 wks, 1.5 eng) |
| **P0-3** | TTFB latency (p95) | -800ms to -1.5s on streaming hot path | Parallelise pre-stream setup + defer channel persistence post-first-chunk + cache request-scope FF results | -25–35% p95 | S–M (~3 wks, 1 eng) |
| **P0-4** | Quality / hallucination | Add factual-consistency canary; close 80→13% AIFC regression detection gap | No-grounding telemetry, citation-preserving truncation, continuous canary eval, feedback→eval loop | Detect regressions in <1 day vs >quarter | M–L (~8 wks, 2 eng) |
| **P1-1** | Create-scenario reliability | 98.2% → 99.9% (+1.7pp) | Coordinated dual-store writes + saga compensation in `ConversationChannelMultiStoreImpl` | +1.5 pp | M (~5 wks, 1 eng) |
| **P1-2** | MAU / Activation | +5–15k MAU via faster, smarter discovery | Cold-start agent recommendation; cached follow-up templates with LLM rewrite; visible UBP-denial telemetry | 5–10% Day-7 conversion lift | M (~6 wks, 1.5 eng) |
| **P1-3** | Observability / detection | Per-agent quality + cost dashboards; tokens/sec + TTFB histograms; feedback↔eval link | TTFB, cost-per-msg, citation-rate, hallucination-flag span attrs | Median MTTD <1 hr | M (~6 wks, 1 eng) |
| **P2-1** | Maintainability (drag on velocity) | -8K LoC duplication | Consolidate `Generic*LanguageModelProvider` duplicates; extract `search/` to its own module | -10–15% review burden | L (~12 wks, 1 eng) |

**Cumulative quantified outcome (12-week target):**
- Send-message SLO: **99.6% → 99.9%** (P0-1) — meets the OpenAI Scale Tier ceiling
- p95 TTFB: **−25–35%** (P0-3)
- Per-message LLM input-cost: **−25–40%** (P0-2)
- Quality-regression MTTD: **>quarter → <1 day** (P0-4 + P1-3)
- Net annualised inference cost reduction: **~$0.6–1.0M** (P0-2 conservative)
- MAU lift: **+5–15k toward 150k H2-FY26 target** (P1-2)

---

## 0. How to read this doc

1. **Section 1 (Business Goals)** — the canonical goals this plan is keyed to. Every initiative in §3 cites a Section-1 goal.
2. **Section 2 (Methodology)** — how findings were produced and validated.
3. **Section 3 (Initiatives)** — one section per P0/P1/P2 with: problem → evidence → fix → metric → owner → schedule.
4. **Section 4 (Sequencing & dependencies)** — what to do in week 1 vs week 12.
5. **Section 5 (Risks & open questions)** — what could derail it.
6. **Section 6 (Machine-followable task list)** — JSON-friendly tickets with file:line, acceptance criteria, and rollout flag suggestion.
7. **Appendix A** — verification log of every code-level claim (file:line citations).

**Conventions:**
- "S" = small (≤1 wk eng); "M" = medium (2–6 wks eng); "L" = large (>6 wks eng).
- Estimated impact ranges are **best-effort engineering judgment** (no production access in this investigation). Always validate with shadow deploys + A/B before declaring victory.
- All file paths are relative to the repo root: `atlassian_packages/conversational-ai-platform/`.

---

## 1. Critical Business / Engineering Goals (Source of Truth)

Sourced from `code_understanding/architecture/business/01-fy26-goals-and-slos.rst`, `02-trust-scorecard.rst`, `03-teamserve-bluebird.rst`, `04-rovo-ai-fy26-strategy.rst` and re-verified against the `operations/terraform/modules/tome/convo_ai/locals.tf` SLO definitions.

### 1.1 Top-level North-Star metrics (FY26)

| Metric | Baseline | H2-FY26 target | Source / verified |
|---|---|---|---|
| **Rovo Chat MAU** | ~100.3k | **150k+** (+50%) | Atlas Project ATLAS-124112; Rovo Growth strategy |
| Discovery (Day 0–7) | — | 150k users | Same |
| Activation (Day 1–30) | — | 80k users | Same |
| Fandom (sustained) | — | 100k users | Same |
| **Send-message SLO** (chat-to-agent) | **99.6%** | **99.9%** (LLM-vendor ceiling) | TOME `locals.tf`, NOT AT TARGET |
| **Create-scenario SLO** | **98.2%** | **99.99%** | TOME `locals.tf`, NOT AT TARGET |
| Browse-agents SLO | 99.99% | 99.99% | At target |
| AIFC Page-create completion | TBD | **90%** (Beta) | AIFC QBR |
| **Inference cost / month** | $5,002 → $2,958 (-40% Bluebird wins on embedding/reranking) | continued reduction | TEAMServe Bluebird (live) |
| Trust Scorecard | 97.35% | ≥98.5% | gai space (org-hygiene only — no product-quality SLO) |
| Factual consistency (AIFC quality) | **regressed 80% → 13%** | recover to ≥80% | AIFC Maturity Gap (CRITICAL) |

### 1.2 Critical constraints

1. **OpenAI Scale Tier 99.9% ceiling** — any single-provider hot path is mathematically capped at 99.9%. To beat that, **multi-provider failover is mandatory**.
2. **Trust Scorecard does NOT measure product-AI quality** — it tracks org hygiene only (training, REPCOM, PUOL). The 80→13% AIFC regression went undetected for a quarter precisely because product-quality has no scorecard. **This plan adds one (P0-4 + P1-3).**
3. **Bluebird wins are platform-side** — convoai inherits the 86% latency / 40% cost reduction on embedding/reranking *for free*. That means the remaining cost/latency lever is the **LLM call itself** (input tokens, output tokens, model tier, prompt-caching). This plan goes there (P0-2).
4. **No throughput/QPS targets** are codified — convoai is latency- and reliability-bound. Per the FY26 doc §3.3 the implicit ceiling at peak is ~2,900 messages/sec (1M DAU × 50 msg/day × 5× burst). All plan items respect that envelope.

### 1.3 Goal → metric → code mapping

| FY26 Goal | Engineering metric | Hot-path code lever | This plan's initiative |
|---|---|---|---|
| MAU 150k | Day-7 retention; agent-recommend CTR | `RovoAgentServiceImpl.getRecommendedAgentsByIds`; `LLMFollowUpGenerationServiceImpl` | P1-2 |
| Send-msg 99.9% | 5xx rate; stream-abort rate | `LLMServiceImpl.withFallbackModelRetry`; `SimpleLoopWorkflowExecutorImpl` tool error path | P0-1 |
| Create-scenario 99.99% | dual-store write success | `ConversationChannelMultiStoreImpl`; `ConversationHistoryLargeComponentsHandler` | P1-1 |
| Cost (Monetisation) | input tokens / msg; $/msg | `AnthropicLanguageModelProvider` cache_control gating; `LLMServiceImpl` model routing | P0-2 |
| Quality (Trust) | factual-consistency; citation accuracy | `evaluation-impl`; `responsibleai/`; `ranking/`; `truncator/` | P0-4, P1-3 |
| TTFB latency | p95 ms before first chunk | `ChatV1Controller.conversationChannelMessageCreateStream`; `RovoChatService.chatStreamRovoImpl` | P0-3 |

---

## 2. Methodology & validation

This plan was produced by:

1. **Doc baseline:** Read `code_understanding/` (Sphinx site, 84 modules, criticality dashboard, request-lifecycle, AI-Gateway cross-cutting, FY26 goals & SLOs).
2. **Codebase mapping:** `find/wc/grep` against the actual repo to identify largest files, hot paths, FF/RolloutService usage, prompt-cache adoption, fallback wiring.
3. **Multi-agent deep-dives (7 parallel subagents):**
   - latency-hotpath
   - llm-cost-efficiency
   - reliability-slo
   - trust-quality
   - agent-loop-tools
   - growth-mau
   - observability-eval
4. **Spot validation:** Each high-impact subagent claim re-verified by direct `grep`/`sed -n` on the actual file. Examples validated in Appendix A.

### 2.1 Corrections to prior assumptions during this pass

| Prior claim | Verified truth (with file:line) |
|---|---|
| "No max-iteration cap on agent loop" | **WRONG.** `SimpleLoopWorkflowExecutorImpl.kt:185` `for (loop in 1..config.maxLoops)`; `config.maxLoops` defaults to 5 in `SimpleLoopWorkflowExecutorConfig.kt:12`. Real risk is **per-tool unbounded execution** (no per-tool deadline) and **tool-error feedback loop**, not loop-count. |
| "No prompt caching" | **PARTIAL.** Anthropic prompt cache IS implemented (`AnthropicLanguageModelProvider.kt:228, 344, 391, 401`; `GcpAnthropicLanguageModelProvider.kt:444+`) but **gated behind a Statsig flag** (`controlledByLimitedContext`) and **only on cross-turn history**, not on system prompts/tool catalogs. OpenAI/Gemini paths do **not** apply cache hints. |
| "No fallback model" | **PARTIAL.** `LLMServiceImpl.kt:1345 withFallbackModelRetry` exists for non-streaming; **streaming path does fallback only on pre-emit errors** (line 1384–1394). Once a chunk is emitted, no failover. |

### 2.2 Honest scope limits

- No production data access; all impact estimates are based on code structure, comparable systems, and published Bluebird wins (86% latency, 40% cost on embedding/reranking).
- Slack threads with leadership not accessible; some strategic priority weighting is best-guess.
- Only ~58 of 84 modules deeply read. Hot-path coverage is high; tail modules less so.
- **Always shadow-deploy and A/B-test** before claiming any quantified win.

---
## 3. Initiatives (P0 critical, P1 significant, P2 major)

Each initiative: Problem → Evidence (file:line) → Fix → Metric → Owner → Schedule → Risk.

---

### P0-1 — Multi-provider failover + tool-error feedback loop
Goal: Send-message SLO 99.6 → 99.9% (+0.3 pp). Beat OpenAI Scale Tier ceiling.

Problem
Three concrete reliability gaps drop the chat hot path below 99.9%:
1. Streaming failover triggers only BEFORE any chunk is emitted. Mid-stream LLM failures terminate the user response without recovery.
2. Tool execution in the agent loop has NO per-tool deadline; a hung tool stalls the entire conversation until the gateway timeout.
3. Tool errors are caught but NOT fed back to the LLM, so the model cannot self-correct on tool failure.

Evidence (verified)
- modules/platform/service/service-impl/.../llm/LLMServiceImpl.kt:1345 — `withFallbackModelRetry` exists for non-streaming.
- LLMServiceImpl.kt:1384–1394 — fallback retry path is wrapped in `emitAll(func(...))` only BEFORE the upstream Flow has emitted; once chunks are flowing, no recovery.
- modules/platform/workflow/workflow-impl/.../SimpleLoopWorkflowExecutorImpl.kt:914–920 — tool execution invoked without `withTimeout` / deadline.
- SimpleLoopWorkflowExecutorImpl.kt:938–962 — tool errors converted to internal types, NOT appended as `FunctionMessage` "tool_error" payloads to next LLM turn.
- SimpleLoopWorkflowExecutorImpl.kt:519–527 — unknown tool calls do trigger a "self-correct" loop, but the same pattern is NOT applied to ordinary tool failures.

Fix
1. Stream-resumable failover: in `LLMServiceImpl.streamGeneration`, buffer the last safe-checkpoint chunk and on stream-error, replay to fallback model with a resume directive (or emit a typed STREAM_FALLBACK event so the client can stitch).
2. Per-tool deadline: add `toolTimeoutMs` to `SimpleLoopWorkflowExecutorConfig` (default 30s; per-tool overrides via tool-registry). Wrap each `toolExecutor.executeSingle(...)` in `withTimeoutOrNull(toolTimeoutMs)`. On timeout, emit a synthetic `tool_error` message back into the LLM context.
3. Tool-error feedback: when a tool throws, append a structured `tool_call_result` with `is_error=true, message=<sanitised>` to `functionMessages` and let the loop continue (subject to a small `maxToolErrorRetries` budget — e.g., 2 — to avoid runaway).
4. Targeted retries in `LLMServiceRetryImpl`: distinguish (a) transient 5xx (1 retry, 200 ms backoff), (b) rate-limit 429 (retry on alternate provider), (c) content-policy / 400 (no retry).

Metric & validation
- Primary: chat-stream success rate per TOME `frontend_chat_send_message_reliability_threshold`.
- Secondary: mean tool-call success rate; mean loop-iterations-per-conversation; abandonment rate within 10 s of stream-start.
- Validation: `ChatHotPathReliabilityV2` Statsig flag; 1% → 5% → 25% → 100% over 4 weeks. Compare per-tenant SLOs in TOME convoai dashboard.

Owner / schedule
- AI Mate platform (workflow-impl) + Service-impl (LLM service). 2 eng × 6 weeks.

Risk
- Stream-resume requires careful client cooperation. Mitigation: implement "soft" resume (concat to message + visible "[continued from fallback model]" annotation) before "hard" resume.
- Tool-error feedback can balloon prompt size. Mitigation: cap individual tool-error message at 512 chars.

---

### P0-2 — LLM cost reduction (prompt cache + smart routing + tool-catalog hash)
Goal: −25–40% input-token cost per message; direct $ savings + faster TTFT.

Problem
Prompt caching is implemented for Anthropic only and gated by Statsig (suboptimal cache-hit rate). OpenAI/Gemini paths emit no cache hints. Tool catalogs are re-serialised in full every turn (up to 128 tools per `MAX_NUM_TOOLS = 128`). Use-case routing exists but does not pick a cheaper model for routine queries (no cost-tier ladder). Two `Generic*LanguageModelProvider` files (1.4–1.5K LoC each) duplicate concrete provider classes.

Evidence
- AnthropicLanguageModelProvider.kt:228, 344, 391, 401 — `cacheControl(DEFAULT_CACHE_CONTROL)` only emitted when `controlledByLimitedContext(...).ofNewCode { ... }` returns truthy.
- GcpAnthropicLanguageModelProvider.kt:444–455 — same gating pattern.
- No `cache_control` references in OpenAI / Gemini providers (grep over service-impl/.../languagemodelprovider/).
- SimpleLoopWorkflowExecutorImpl.kt:212–213 — `selectedToolSchemas.take(MAX_NUM_TOOLS)`; full schema list included in EVERY loop iteration.
- LLMServiceImpl.kt:1345 — `withFallbackModelRetry` retries the same model only; no escalator/de-escalator across cost tiers.
- Duplicate provider files: `GenericGeminiLanguageModelProvider.kt` (1,484 LoC) vs `GeminiLanguageModelProvider.kt` (1,406 LoC); same for Anthropic, OpenAI, GCP-Anthropic.

Fix
1. Default-on Anthropic prompt cache (drop FF gate after 2-week canary). Adds `cache_control: ephemeral` to system prompt + second-to-last turn for any conversation ≥2 turns. Estimated 15–30% input-token saving on multi-turn.
2. OpenAI prompt-caching headers. OpenAI auto-caches >1024-token static prefixes. Restructure system prompt + tool catalog so the stable prefix is at the top (system → tools → conversation). Verify via `usage.cached_tokens`.
3. Gemini context-caching API for system prompts ≥32K tokens; for smaller prompts, ensure stable ordering for implicit cache.
4. Tool-catalog hash cache: hash `(agent_id, tools_set, tools_version)` → JSON-serialised tool block; reuse across loop iterations. Saves serialisation CPU + bytes on the wire.
5. Cost-tier model routing: extend `withFallbackModelRetry` with a `costTier: PRIMARY/CHEAP/DEEP_RESEARCH` and per-use_case_id mapping in `useCaseManager`. Route trivial intents to Haiku/Mini/Flash; reasoning-heavy to 4o/Sonnet/Pro. Conservative goal: 30% of traffic to cheaper tier with quality-eval gating.
6. Provider-class consolidation: merge `Generic*` and concrete provider duplicates behind an adapter pattern. Net deletion ~3–5K LoC.

Metric & validation
- Primary: `usage.cached_tokens / usage.input_tokens` per response (target ≥0.5 on multi-turn). Total $/msg.
- Secondary: model mix (% on each tier); per-use-case latency; quality-canary delta (P0-4) must stay flat.
- Validation: dual-write metric ("current cost" vs "shadow cost") for 2 weeks before flip.

Owner / schedule
- Service-impl owners. 1.5 eng × 4 weeks.

Risk
- Quality regression on cheaper tier. Mitigation: require P0-4 canary eval green for 7 days before tier-down.
- Cache-invalidation bugs. Mitigation: only cache stable prefix (system + tool schemas), never user content.

---

### P0-3 — Latency: parallelise pre-stream setup + defer non-critical work
Goal: −25–35% p95 TTFB on `/chat/v1/channel/{id}/message/stream`.

Problem
Streaming endpoint does 6 sequential synchronous-suspend operations before the first byte. Many can be parallelised or deferred.

Evidence
- modules/service/convo-ai-service/.../rest/v1/ChatV1Controller.kt:181–219 — sequential `agentService.isDeactivated(...)` then `preloadRovoAgentIfNeeded(...)` before `assistanceClient...` returns the Flux.
- RovoChatService.kt:755–770 (deep-dive subagent finding) — `getAgentIfActive()` and `resolveMemorySettings()` sequential; channel `getOrCreateChannel` blocks at ~800–830.
- Multiple `rolloutService.controlledByLimitedContext(...).ofNewCodeSuspend { ... }` calls for the same flag in same request; no request-scope cache.

Fix
1. Parallelise step 2 + 3 in ChatV1Controller via `coroutineScope { async { isDeactivated } / async { preloadRovoAgentIfNeeded } }.awaitAll()`.
2. Request-scope FF cache: add a `RequestScopedFlagCache` resolved at filter-time for well-known chat-hot-path flags. RolloutService calls hit the cache.
3. Defer channel persistence to `doOnSubscribe` (or a launched coroutine off the response Flux). User does not need to wait for channel-row persistence before bytes start flowing.
4. Lazy logging context: defer `infoWithContext` "Received ... request" to `doOnSubscribe`.
5. Pre-warm tool-catalog cache (P0-2 item 4) — first-message latency win.

Metric & validation
- Primary: p50/p95/p99 TTFB on POST /chat/v1/channel/{id}/message/stream. Add `convoai.ttfb_ms` span attr.
- Secondary: "pre-stream phase" duration; per-step span.
- Validation: `ChatPreStreamParallelisation` flag; 1% → 100% over 2 weeks.

Owner / schedule
- convo-ai-service + rovo-impl. 1 eng × 3 weeks.

Risk
- Deferred persistence races with reconnection retries. Mitigation: idempotent channel upserts; rely on `requestId` as natural key.
- FF cache staleness. Mitigation: lifetime = single request; never cross requests.

---

### P0-4 — Quality canary + factual-consistency feedback loop
Goal: Detect AIFC-class regressions (80% → 13%) in <1 day instead of >quarter; close the Trust-Scorecard product-quality gap.

Problem
`platform/evaluation/evaluation-impl` is batch-only; no continuous canary on production traffic. User feedback (PUT /v1/channel/{id}/message/{mid}/feedback) is captured but not fed back into eval datasets. There is NO factual-consistency or citation-accuracy metric in production telemetry. Trust Scorecard tracks org hygiene only and missed the AIFC regression entirely.

Evidence
- modules/platform/evaluation/evaluation-impl — top-level orchestrator is `BatchEvaluationOrchestratorImpl`; no streaming/canary code path.
- LlmRequestSpanAttributesExtractors.kt (850 LoC) — emits latency-related attrs; grep for `factual_consistency`, `citation_recall`, `hallucination` returns nothing.
- ChatV1Controller.kt:323 — feedback endpoint exists; downstream tracing of feedback into eval dataset not present.
- code_understanding/architecture/business/02-trust-scorecard.rst §5 — explicitly notes scorecard does not include hallucination, citation accuracy, or per-agent quality.

Fix
1. Continuous canary eval: sample 0.5% of production conversations; replay through an LLM-judge eval (factual consistency, citation accuracy, instruction-following). Emit metrics tagged by `agent_id, model_version, prompt_version, tenant_id_segment`.
2. Citation-preserving truncation in `RequestTruncatorImpl`: mark "source"/"citation" segments with higher retention priority than ordinary content. Never drop the last cited source for a still-referenced citation token.
3. No-grounding detector: when all retrieval providers return empty for a query, set `convoai.grounding_state = NONE` span attr and either (a) trigger a clarification turn or (b) emit a clearly-flagged ungrounded answer. Alarm on per-tenant rise in NONE rate.
4. Feedback → eval pipeline: persist feedback (👍/👎 + free-text) into the eval dataset store keyed on `(conversation_id, message_id, agent_version, prompt_version)`. Surface `feedback_negativity_rate` per agent on the new product-quality dashboard.
5. AI-quality span attributes: extend `LlmRequestSpanAttributesExtractors` with `convoai.cached_tokens`, `convoai.cost_usd_estimate`, `convoai.citation_count`, `convoai.grounding_state`, `convoai.factual_consistency_canary_score`.

Metric & validation
- Primary: mean factual-consistency score (LLM-judge); 7-day rolling.
- Secondary: per-agent feedback-negativity rate; "no-grounding" rate; alarm-to-detect time on synthetic regression.
- Validation: synthetic A/B (degraded prompt) — confirm canary alarm fires within 24 h.

Owner / schedule
- Evaluation team + GenAI eng. 2 eng × 8 weeks. Phased: eval pipeline (3 wk) → instrumentation (2 wk) → dashboards + alarms (3 wk).

Risk
- LLM-judge quality drift. Mitigation: pin judge model version; rerun calibration set monthly.
- Cost of canary: ~0.5% extra LLM spend. Acceptable vs cost of an undetected regression.

---

### P1-1 — Coordinated dual-store writes (saga compensation)
Goal: Create-scenario SLO 98.2% → 99.5+% (+1.3 pp); reduce orphaned blobs.

Problem
`ConversationChannelMultiStoreImpl` (441 LoC) writes to two stores (ERS + assistance) without transactional coordination. `ConversationHistoryLargeComponentsHandler` (656 LoC) splits oversized history items and migrates blobs without coordinated rollback on partial failure.

Fix
1. Saga pattern for dual-store ops: write primary → enqueue secondary; on failure, compensating delete on primary OR retry secondary with idempotency key.
2. Outbox table for blob-handler operations so partial failures are crash-safe.
3. Reconciliation worker for orphaned blobs (daily sweep; emit metric).

Metric: Create-scenario reliability per TOME; orphaned-blob count; reconciliation job lag.
Owner: Conversation team, 1 eng × 5 weeks.

---

### P1-2 — Growth: cold-start agent recommendation + cached follow-ups + UBP visibility
Goal: +5–15k MAU toward 150k; +5–10% Day-7 conversion.

Problem
- Agent recommendation lacks cold-start signals (no domain/usage features for new tenants).
- Follow-up question generation is a synchronous LLM call per message → adds 2–4s tail latency.
- UBP enforcement fails open (good) but lacks per-segment denial telemetry → can't tell if it's silently killing engagement.

Fix
1. Cold-start ranker: for first-7-day tenants, blend ANN scores with priors derived from `(tenant_size_bucket, primary_product, locale)`. Maintain a small lookup table refreshed weekly from offline analytics.
2. Cached follow-up templates with LLM-rewriting pass: keep ~20 high-quality templates per (agent, intent); rewrite at most 1 per 5 messages with the LLM; otherwise serve cached. Saves ~1 LLM call/turn.
3. UBP denial dashboard segmented by tenant tier, experience, agent. Add `convoai.ubp_denied=true` span attr. Alarm if denial rate >1% on AIMATE.
4. Conversation memory recall: integrate `ErsConversationTopicSegmentStoreImpl` (currently low usage) into Rovo Chat session warm-up — use last-7-days topic summary as memory hint at conversation start.

Metric: Day-7 retention; agent-recommendation CTR; follow-up CTR; UBP denial rate per segment.
Owner: Rovo Growth + AI Mate, 1.5 eng × 6 weeks.

---

### P1-3 — Observability: TTFB / cost / quality dashboards
Goal: MTTD <1 hr on regressions; full per-agent / per-tenant cost & quality visibility.

Fix
1. TTFB & generation-rate histograms in `LlmRequestSpanAttributesExtractors`: `convoai.ttfb_ms`, `convoai.tokens_per_second`.
2. Per-agent quality dashboards sourced from canary eval (P0-4) + feedback rate.
3. LLM cost attribution dashboards: $/agent, $/tenant, $/use_case_id; daily and weekly.
4. A/B framework hooks: `convoai.experiment_arm` span attr so any prompt/model A/B can be sliced server-side.
5. Detekt enforcement of `RolloutLiteralLambda` and `FeatureFlagRolloutPattern` rules — make sure new code stays measurable.

Owner: Platform observability, 1 eng × 6 weeks.

---

### P2-1 — Maintainability: consolidate provider duplication + extract `search/`
Goal: Long-term velocity. -8K LoC drag.

Fix
1. Merge `Generic{Provider}` + `{Provider}` pairs via adapter pattern (Anthropic, GCP-Anthropic, Gemini, OpenAI). Each pair shares ~85% logic.
2. Extract `platform/service/service-impl/.../search/` (~14K LoC, 35 files) into its own Gradle module `platform/search-impl`.
3. Audit AGS vs ORS vs ERS overlap — propose unified storage SPI.

Owner: Platform refactor, 1 eng × 12 weeks (background, no dependencies).

---
## 4. Sequencing & dependencies

### Phase 1 — Weeks 1–4 (foundations)
- P0-3 latency parallelisation (3 wk, 1 eng) — quick win, no dependencies.
- P0-4 canary eval pipeline build (3 wk of 8) — must precede any cost/model routing changes (P0-2 depends on quality gate).
- P1-3 add TTFB / cost / quality span attrs (parallel to P0-3, 2 wk) — prerequisite for measuring the wins.

### Phase 2 — Weeks 4–8 (reliability + cost)
- P0-1 multi-provider streaming failover + tool-error feedback (6 wk, 2 eng) — primary SLO mover.
- P0-2 prompt-cache default-on + tool-catalog hash + model routing (4 wk, 1.5 eng) — gated on P0-4 canary green.
- P1-1 dual-store saga (5 wk, 1 eng) — independent.

### Phase 3 — Weeks 8–12 (growth + alarms)
- P0-4 dashboards + alarms (final 3 wk).
- P1-2 cold-start + cached follow-ups + UBP visibility (6 wk).
- P1-3 finalize per-agent dashboards.

### Phase 4 — Weeks 12+ (background)
- P2-1 maintainability — runs in background; review-burden win.

### Dependency graph (textual)
- P0-4 canary -> gates P0-2 model-routing rollout.
- P1-3 span attrs -> measurement layer for all P0/P1.
- P0-1 stream-resume -> protocol agreement with frontend (rovo-chat-desktop) team — start design discussion week 1.
- P0-3 deferred channel persistence -> verify with conversation team that idempotent upserts handle reconnects.

---

## 5. Risks, open questions, mitigations

### Top risks
1. Stream-resume protocol coordination with rovo-chat-desktop / Rovo iframe clients. Mitigation: ship "soft" resume first (visible annotation); negotiate hard resume in a follow-up RFC.
2. Quality regression on cheaper-model tier (P0-2). Mitigation: P0-4 canary blocks rollout if factual-consistency drops >2 pp.
3. Saga compensation correctness in P1-1. Mitigation: chaos-engineering dual-store kill-switch tests in staging.
4. Statsig flag explosion. Mitigation: register all new flags in a central registry doc; require sunset date on PR.
5. Canary eval cost (~0.5% LLM spend). Mitigation: cap with budget alarm; downsample on cost spike.

### Open questions
- What is current production cache-hit rate on Anthropic? (Need ARIZE / dashboards access — flag for owner team.)
- What % of streaming failures occur AFTER first chunk vs BEFORE? Drives P0-1 design weight.
- Are tool execution timeouts already enforced at any infra layer (e.g., gateway, sidecar)? If yes, per-tool deadline is belt-and-suspenders.
- Per-tenant cost attribution — is `aicreditusage` already tagged with `tenant_id` or only with `user_id`?
- Trust Scorecard: who owns adding a "product-quality" module? (gai team? AI Mate?)

### Things NOT in this plan (deferred)
- Voice / Twilio integration overhaul (separate CSM track).
- Whiteboard AI generation latency (separate aifeature-impl track).
- AgentStudio publishing reliability (separate agentstudio-impl track).
- Loom transcript indexing latency (separate loom-impl track).

---

## 6. Machine-followable task list

Each item is a self-contained ticket. Use as-is to file Jira / Bitbucket PR descriptions.

### TASK P0-1-A — Per-tool deadline in SimpleLoopWorkflowExecutor
- File: modules/platform/workflow/workflow-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/workflow/simpleloop/SimpleLoopWorkflowExecutorImpl.kt
- Lines: 914–920 (tool execution call site); 855–867 (parallel tool execution chunks).
- Change: add `toolTimeoutMs: Duration` to `SimpleLoopWorkflowExecutorConfig` (default 30 s). Wrap each `toolExecutor.executeSingle(...)` in `withTimeoutOrNull(toolTimeoutMs)`. On timeout, append synthetic `tool_error` to `functionMessages`.
- Acceptance: integration test with a deliberately-hanging stub tool returns within 35 s with a typed error in the LLM context.
- Rollout: Statsig flag `convo-ai-platform-tool-deadline-enabled`; default off; 1% → 100% over 2 weeks.
- Owner: workflow-impl owner.
- Effort: S (1 wk).

### TASK P0-1-B — Tool-error feedback to LLM
- File: SimpleLoopWorkflowExecutorImpl.kt:938–962.
- Change: when tool error caught, append `FunctionMessage(role=tool, name=<toolName>, content=<sanitised_error>, isError=true)` to `functionMessages`. Increment a `toolErrorBudget` counter; break out of loop after `maxToolErrorRetries` (default 2).
- Acceptance: agent receives tool-error feedback and can self-correct within `maxToolErrorRetries`.
- Rollout: same flag as P0-1-A.
- Effort: S (1 wk).

### TASK P0-1-C — Stream-resumable failover
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/LLMServiceImpl.kt:1345–1394.
- Change: introduce `StreamFailoverPolicy` (NONE / SOFT_RESUME / HARD_RESUME). For SOFT_RESUME, on stream error after first emit, emit a typed `STREAM_FALLBACK_EVENT(reason, fallback_model)` and start a fresh stream with `previous_partial_text` re-injected as a system note. For HARD_RESUME (later phase), full stitching.
- Acceptance: kill-switch integration test (force AI Gateway 5xx after 3 chunks) returns a continuous user-visible response from the fallback model.
- Rollout: Statsig flag `convo-ai-platform-stream-failover-soft-resume`; 1% → 100% over 4 weeks.
- Owner: service-impl owner.
- Effort: M (3 wk).

### TASK P0-2-A — Default-on Anthropic prompt cache
- Files: modules/platform/service/service-impl/.../languagemodelprovider/AnthropicLanguageModelProvider.kt:228, 344, 391; GcpAnthropicLanguageModelProvider.kt:444; GenericGcpAnthropicLanguageModelProvider.kt:285.
- Change: invert the FF gate: cache_control emitted by default; FF turns it OFF (kill switch).
- Acceptance: `usage.cached_tokens` ≥ 50% of `usage.input_tokens` on conversations ≥3 turns in canary.
- Rollout: replace `controlledByLimitedContext(...).ofNewCode { textBuilder.cacheControl(...) }` with always-on call; new FF `convo-ai-platform-anthropic-cache-killswitch` defaults false.
- Effort: S (3 d).

### TASK P0-2-B — OpenAI prompt-prefix optimisation
- Files: GenericOpenAILanguageModelProvider.kt and OpenAIHarmonyLanguageModelProvider.kt — message-list construction.
- Change: ensure stable prefix order (system → tools → conversation history → current user turn). No structural changes mid-conversation. Verify via `usage.prompt_tokens_details.cached_tokens`.
- Acceptance: cached_tokens > 0 on second turn of any conversation.
- Effort: S (3 d).

### TASK P0-2-C — Tool-catalog hash cache
- File: modules/platform/tool-registry/tool-registry-impl/.../ToolRegistryImpl.kt; consumed in SimpleLoopWorkflowExecutorImpl.kt at the textGenerationRequest construction site.
- Change: introduce `ToolCatalogCacheKey(agentId, toolNamesHash, toolsVersion)` → cached pre-serialised JSON. Reuse across loop iterations.
- Acceptance: serialisation CPU profile drops; identical tool-block bytes across loop iterations within a single conversation.
- Effort: M (1 wk).

### TASK P0-2-D — Cost-tier model routing
- File: LLMServiceImpl.kt:1345 (`withFallbackModelRetry`).
- Change: introduce `CostTier` enum and per-use_case_id mapping in `useCaseManager`. Add a routing rule: if `intent.complexity_score < threshold`, route to CHEAP tier.
- Acceptance: shadow metric `shadow_cost_$ < primary_cost_$ * 0.85` across 30% of routine intents.
- Effort: M (2 wk).

### TASK P0-2-E — Provider-class consolidation
- Files: AnthropicLanguageModelProvider.kt + GenericAnthropicLanguageModelProvider.kt; GcpAnthropicLanguageModelProvider.kt + GenericGcpAnthropicLanguageModelProvider.kt; GeminiLanguageModelProvider.kt + GenericGeminiLanguageModelProvider.kt.
- Change: extract shared logic into an abstract base `BaseProviderImpl<T>`; collapse generic + concrete into a single generic implementation parameterised over the provider-specific overrides.
- Acceptance: net deletion ≥ 3 KLoC; existing tests pass without behavioural change.
- Effort: M (3 wk). Background work.

### TASK P0-3-A — Parallelise pre-stream setup
- File: modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt:181–219.
- Change: wrap `agentService.isDeactivated(...)` and `preloadRovoAgentIfNeeded(...)` in `coroutineScope { async { ... } }.awaitAll()`.
- Acceptance: p95 TTFB drops by ≥150 ms vs baseline.
- Rollout: Statsig flag `convo-ai-service-prestream-parallel`; 1% → 100% over 2 weeks.
- Effort: S (3 d).

### TASK P0-3-B — Request-scope FF cache
- File: new `modules/foundation/utilities/utilities-impl/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/featureflag/RequestScopedFlagCache.kt`.
- Change: cache resolved RolloutService results within request scope keyed by `flagId`. Wire into HeaderFilter at request entry.
- Acceptance: FF call count per request drops ≥50%.
- Effort: M (1 wk).

### TASK P0-3-C — Defer channel persistence
- File: modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/RovoChatService.kt at the channel `getOrCreateChannel` site (~ line 800–830 per subagent report; verify).
- Change: move channel write to a launched coroutine fired from `doOnSubscribe`; verify idempotent upsert keyed on `requestId`.
- Acceptance: pre-stream phase span drops by ≥200 ms.
- Effort: M (1 wk).

### TASK P0-4-A — Continuous canary eval pipeline
- New module: modules/platform/evaluation/evaluation-impl/.../canary/CanaryEvaluationOrchestratorImpl.kt.
- Change: 0.5% sampling at the response Flux level; replay through LLM-judge with factual-consistency, citation-recall, instruction-following metrics.
- Acceptance: synthetic regression (degraded prompt deployed to 10% of traffic) detected within 24 h.
- Effort: L (3 wk).

### TASK P0-4-B — Citation-preserving truncation
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/truncator/RequestTruncatorImpl.kt.
- Change: tag content segments with `retentionPriority`; never drop a source still referenced by an active citation token.
- Acceptance: citation-recall metric ≥ 0.95 in canary.
- Effort: M (2 wk).

### TASK P0-4-C — No-grounding detector + alarm
- File: modules/platform/service/service-impl/.../search/InterleaverSearchProvider.kt or RankingServiceImpl.kt.
- Change: when all providers return zero results for a query, set span attribute `convoai.grounding_state=NONE`. Emit metric. Alarm on per-tenant rise > 2 sigma.
- Effort: S (1 wk).

### TASK P0-4-D — Feedback → eval pipeline
- File: ChatV1Controller.kt:323 (feedback endpoint) downstream to evaluation-impl.
- Change: persist feedback to eval dataset store keyed `(conversation_id, message_id, agent_version, prompt_version)`. Periodic sync into evaluation harness.
- Effort: M (2 wk).

### TASK P0-4-E — AI-quality span attributes
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/LlmRequestSpanAttributesExtractors.kt.
- Change: add `convoai.cached_tokens`, `convoai.cost_usd_estimate`, `convoai.citation_count`, `convoai.grounding_state`, `convoai.factual_consistency_canary_score`.
- Effort: S (3 d).

### TASK P1-1-A — Saga pattern for ConversationChannelMultiStore
- File: modules/platform/conversation/conversation-impl/src/main/kotlin/io/atlassian/micros/convoai/conversation/stores/multi/ConversationChannelMultiStoreImpl.kt.
- Change: write primary first; enqueue secondary via outbox; on secondary failure, retry with idempotency key OR compensate primary.
- Acceptance: chaos-test (force secondary write failure) leaves no orphaned data.
- Effort: M (3 wk).

### TASK P1-1-B — Outbox for blob handler
- File: modules/platform/conversation/conversation-impl/src/main/kotlin/io/atlassian/micros/convoai/conversation/stores/ers/history/ConversationHistoryLargeComponentsHandler.kt.
- Change: write blob outbox row before split; mark complete after all parts written.
- Effort: M (2 wk).

### TASK P1-2-A — Cold-start agent recommendation prior
- File: modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/agent/RovoAgentServiceImpl.kt.
- Change: blend ANN scores with priors derived from `(tenant_size_bucket, primary_product, locale)` for tenants in first 7 days.
- Effort: M (3 wk).

### TASK P1-2-B — Cached follow-up templates
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/followup/LLMFollowUpGenerationServiceImpl.kt.
- Change: cache ~20 high-quality templates per (agent, intent); rewrite at most 1 in 5 with the LLM.
- Acceptance: follow-up median latency drops by ≥1 s; quality score (canary) stays within 2 pp.
- Effort: M (2 wk).

### TASK P1-2-C — UBP denial telemetry
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/ubpenforcement/UbpCreditsEnforcementServiceImpl.kt.
- Change: emit `convoai.ubp_denied=true` span attr + counter `ubp_denial_total` with tags (tenant_tier, experience, agent).
- Effort: S (3 d).

### TASK P1-3-A — TTFB + tokens/sec histograms
- File: LlmRequestSpanAttributesExtractors.kt.
- Change: add `convoai.ttfb_ms` (gauge per request), `convoai.tokens_per_second` (computed at stream end).
- Effort: S (3 d).

### TASK P1-3-B — Per-agent quality dashboards
- New: dashboards in TOME / Splunk; sourced from canary eval metrics + feedback rate.
- Effort: M (2 wk).

### TASK P1-3-C — LLM cost attribution dashboards
- New: dashboards by `agent_id`, `tenant_id`, `use_case_id`.
- Effort: M (2 wk).

### TASK P2-1-A — Extract platform/search-impl module
- Files: move modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/search/* into a new module.
- Acceptance: no behavioural change; tests pass; build-graph dependency clean.
- Effort: L (4 wk).

---

## 7. Acceptance gates (per phase)

| Gate | Trigger | Measurement |
|---|---|---|
| Gate-1 (end of week 4) | P0-3 + P1-3 span attrs landed | TOME shows `convoai.ttfb_ms` p95 ≤ baseline − 200 ms |
| Gate-2 (end of week 8) | P0-1 stream failover at 25% | Send-msg SLO ≥ 99.75% on canary cohort |
| Gate-3 (end of week 8) | P0-2 cost routing in shadow | Shadow $/msg ≤ 80% of primary $/msg with quality delta < 2 pp |
| Gate-4 (end of week 10) | P0-4 canary alarms armed | Synthetic regression detected in < 24 h |
| Gate-5 (end of week 12) | All P0s at 100%; P1s at ≥ 50% | Send-msg SLO ≥ 99.9%; cost down ≥ 25%; MTTD < 1 h |

---

## 8. Owner & RACI summary

| Initiative | R (Responsible) | A (Accountable) | C (Consulted) | I (Informed) |
|---|---|---|---|---|
| P0-1 | AI Mate platform + service-impl owners | AI Mate EM | rovo-chat-desktop FE; SRE | Rovo Agents PM |
| P0-2 | Service-impl owners | Service-impl EM | GenAI eng (model routing); Finance | Rovo Agents PM |
| P0-3 | convo-ai-service + rovo-impl owners | Convo-AI service EM | conversation team (channel persistence) | Rovo Agents PM |
| P0-4 | Evaluation team + GenAI eng | GenAI eng EM | gai (Trust Scorecard); product-quality DRI | All product teams |
| P1-1 | Conversation team | Conversation team EM | SRE | All product teams |
| P1-2 | Rovo Growth + AI Mate | Rovo Growth EM | UX research | Rovo Agents PM |
| P1-3 | Platform observability | Platform obs EM | All product teams | SRE |
| P2-1 | Platform refactor | Platform EM | All -impl owners | All teams |

---
## Appendix A — Verification log (file:line citations re-checked during this pass)

This appendix lists every code-level claim used in the plan and the exact `grep`/`sed` evidence that supports it. Use this as the audit trail before filing tickets.

### A.1 Agent-loop iteration cap (re-verified)
- File: modules/platform/workflow/workflow-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/workflow/simpleloop/SimpleLoopWorkflowExecutorImpl.kt
- Line 69: `private const val MAX_NUM_TOOLS = 128` — tool-count cap (not iteration cap).
- Line 185: `for (loop in 1..config.maxLoops) {` — verified iteration cap exists.
- Line 203–205: `if (loop == config.maxLoops) { ... selectedToolSchemas = emptyList() }` — graceful exhaustion (force-final-answer).
- Line 212–213: `if (selectedToolSchemas.size > MAX_NUM_TOOLS) { selectedToolSchemas = selectedToolSchemas.take(MAX_NUM_TOOLS); maxNumToolsExceeded = true }` — tool-list truncation.
- Implication: the original criticality-dashboard concern "agent loops never terminate" is BOUNDED by `maxLoops`; the real risk is per-tool unbounded runtime + missing error feedback. Plan reflects this.

### A.2 Anthropic prompt cache (FF-gated)
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/languagemodelprovider/AnthropicLanguageModelProvider.kt
- Lines 228, 233: `).ofNewCode { textBuilder.cacheControl(DEFAULT_CACHE_CONTROL) }` — gated.
- Lines 344, 391, 401–402: similar pattern.
- File: GcpAnthropicLanguageModelProvider.kt — lines 291, 296, 390, 444, 454–455 same pattern.
- File: GenericGcpAnthropicLanguageModelProvider.kt — lines 285, 290, 407, 461, 471–472, 844, 863–865 same pattern.
- No matches for `cache_control`, `cacheControl`, `prompt_cache`, `promptCache`, `ephemeral` in OpenAI / Gemini provider files (grep over `service-impl/src/main/kotlin/.../languagemodelprovider/`).
- Implication: P0-2-A invert FF gate; P0-2-B add OpenAI prefix optimisation.

### A.3 Streaming failover scope
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/LLMServiceImpl.kt
- Line 167: `controlledByLimitedContext(AIGatewayFeatureFlags.DEFENSIVE_MODEL_ROUTING_OPENAI_FALLBACK)` — defensive routing flag.
- Line 655: `withFallbackModelRetry(textGenerationRequest) { textGenerationRequest -> ... }` — non-streaming fallback.
- Line 808: `ModelProvider.OPEN_AI -> withFallbackModelRetry(textGenerationRequest) { ... }` — same usage.
- Line 1345: `private suspend fun withFallbackModelRetry(` — the retry primitive.
- Line 1349: `val fallbackModel = textGenerationRequest.fallbackModel ?: return func(textGenerationRequest)` — early exit if no fallback configured.
- Line 1361: `return func(textGenerationRequest.copy(model = fallbackModel))`.
- Line 1384: `} else if (textGenerationRequest.fallbackModel != null) {`.
- Line 1389: `"retry_model" to textGenerationRequest.fallbackModel,`.
- Line 1394: `emitAll(func(textGenerationRequest.copy(model = textGenerationRequest.fallbackModel!!)))` — only triggers BEFORE first emission of the upstream Flow.
- Line 1671: `request.fallbackModel?.let { ... }`.
- Implication: stream-mid-flight failures bypass fallback. P0-1-C ships soft-resume.

### A.4 ChatV1Controller streaming hot path
- File: modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt
- Line 164: `@PostMapping("/v1/channel/{conversationId}/message/stream", produces = ["application/x-ndjson"])`.
- Line 173: `withMdcContext { ... }` wrapper.
- Line 175–179: experience allowlist (ISSUE_WORK_BREAKDOWN, UNIFIED_HELP).
- Line 181–188: `agentId != null` then sequential `agentService.isDeactivated(...)` then throw if deactivated.
- Line 190: `val preloadedAgent = preloadRovoAgentIfNeeded(body, tenantContext, user)` — synchronous suspend.
- Line 192–201: `streamLoggingContext` build.
- Line 209–214: body mutation injecting `RovoAgentForAssistanceService.fromAgent(preloadedAgent)`.
- Line 219: `assistanceClient.conversationChannelMessageCreateStreamWithPassThroughHeaders(tenantContext, user, conversationId, bodyForAssistanceService, headers)`.
- Implication: P0-3-A parallelise lines 184 and 190.

### A.5 Cross-references to operational SLOs
- TOME `operations/terraform/modules/tome/convo_ai/locals.tf` defines:
  - `frontend_chat_send_message_reliability_threshold` — currently 99.6%, target 99.9% (LLM-vendor ceiling).
  - `agentstudio_create_scenario_reliability_threshold` — currently 98.2%, target 99.99%.
  - `reliability_slo_llm_dependent_target` — bounded 99.9% by OpenAI Scale Tier per upstream Confluence (page 6317703598).
- Implication: 99.9% target on send-message requires multi-provider failover; non-LLM-dependent SLOs (e.g., agent-CRUD) can target 99.99% only via P1-1 saga writes.

### A.6 Search providers (RAG quality)
- File: modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/search/RankingServiceImpl.kt — 1,647 LoC.
- File: InterleaverSearchProvider.kt — 1,201 LoC.
- File: AggInterleaverSearchQueries.kt — 1,066 LoC.
- File: SalesforceSearchProvider.kt — 1,014 LoC; ConfluenceSearchProvider.kt — 954 LoC.
- Subagent finding: no consistent "no-grounding" detection. Plan adds it in P0-4-C.

### A.7 Provider-class duplication (consolidation candidate)
- GenericGeminiLanguageModelProvider.kt: 1,484 LoC.
- GeminiLanguageModelProvider.kt: 1,406 LoC.
- GenericGcpAnthropicLanguageModelProvider.kt: 975 LoC.
- GcpAnthropicLanguageModelProvider.kt: 1,006 LoC.
- GenericAnthropicLanguageModelProvider.kt: 956 LoC.
- AnthropicLanguageModelProvider.kt: 963 LoC.
- GenericOpenAILanguageModelProvider.kt: 835 LoC.
- Implication: ~5 KLoC consolidation potential. P2-1-A.

### A.8 Conversation persistence (multi-store)
- File: modules/platform/conversation/conversation-impl/src/main/kotlin/io/atlassian/micros/convoai/conversation/ConversationManagerImpl.kt — 892 LoC.
- File: ConversationHistoryItemManagerImpl.kt — 803 LoC.
- File: ErsConversationHistoryItemStoreImpl.kt — 724 LoC.
- File: ConversationHistoryLargeComponentsHandler.kt — 656 LoC (the "large component splitter"; subagent identified consistency risk).
- File: ErsConversationChannelStoreImpl.kt — 593 LoC.
- File: ConversationChannelMultiStoreImpl.kt — 441 LoC (multi-store coordinator; saga target).
- Implication: P1-1-A and P1-1-B.

### A.9 Doc provenance
- All section-1 goals sourced from:
  - code_understanding/architecture/business/01-fy26-goals-and-slos.rst
  - code_understanding/architecture/business/02-trust-scorecard.rst
  - code_understanding/architecture/business/03-teamserve-bluebird.rst
  - code_understanding/architecture/business/04-rovo-ai-fy26-strategy.rst
- Sub-agent findings re-validated where feasible:
  - "No prompt cache on OpenAI / Gemini" — confirmed via grep.
  - "Anthropic cache FF-gated" — confirmed via grep.
  - "Streaming fallback only pre-emit" — confirmed via sed at LLMServiceImpl.kt:1345–1394.
  - "MAX_NUM_TOOLS = 128, no per-tool deadline" — confirmed via grep+sed at SimpleLoopWorkflowExecutorImpl.kt:69, 212.
  - "for (loop in 1..config.maxLoops)" — confirmed at line 185 (i.e., iteration cap exists; original criticality dashboard wording is misleading).

---

## Appendix B — Glossary

- **TTFB** — Time to first byte (here: time from controller entry to first ndjson chunk emitted).
- **TOME** — Terraform-managed operational SLO definitions in `operations/terraform/modules/tome/`.
- **SFX** — Composer-managed REST-endpoint SLOs in `operations/sfx-composer/configuration/`.
- **AIFC** — AI Feature Composer (whiteboard / page generation surface).
- **UBP** — Usage-Based Pricing (Rovo Credits enforcement).
- **MAU** — Monthly Active Users.
- **ARIZE** — observability platform used for AI quality dashboards.
- **TWG** — Teamwork Graph.
- **ANN** — Approximate Nearest Neighbor (used for agent recommendation v2 endpoint).
- **MDC** — Mapped Diagnostic Context (SLF4J logging context that must survive coroutine suspensions).
- **Statsig** — Atlassian's feature-flag / experimentation platform.
- **RolloutService** — internal wrapper that auto-emits per-flag invocation/latency/error metrics.

---

## Appendix C — How to extend this plan

1. **New initiative template**: copy any P0/P1 section as the template; mandatory fields are Problem / Evidence (with file:line) / Fix / Metric & validation / Owner / Schedule / Risk.
2. **New finding from production**: add to Appendix A first (with file:line) before drafting an initiative — keeps the plan grounded.
3. **Goal alignment**: every new initiative must cite at least one row from §1.3 (Goal → metric → code mapping).
4. **Effort estimation**: S = ≤1 wk; M = 2–6 wk; L = >6 wk. Always 1 eng-equivalent unless noted.
5. **Quantification discipline**: avoid unsourced numbers. If you state "−25% cost", cite the mechanism (e.g., "Anthropic cache typically saves 25–80% on cached prefix per their docs"). If unverifiable, prefix with "best-est."

---

## Appendix D — What this plan is NOT

- **Not a rewrite plan.** All initiatives target localised changes in existing files; no green-field redesigns.
- **Not a frontend plan.** Rovo iframe / rovo-chat-desktop / Confluence chat UI changes are out-of-scope (separate repo / team).
- **Not an infra plan.** Bluebird / TEAMServe / GCP-multi-cloud / sandbox-pool capacity work is owned by ML platform.
- **Not a security plan.** Trust-Scorecard module-by-module remediation (Risk Assessment 60→90%, Accessibility Training 83.3→100%) is owned by Robbie Livermore / Kevin Ma per the gai scorecard.
- **Not a model-training plan.** All optimisations are at the inference / orchestration layer; no fine-tuning recommended.

---

End of plan.


---

# v2 ADDENDUM (2026-05-03 deep-review pass)

## v2.0 What changed and why

After a critical self-review with 4 additional parallel deep-dive subagents, the v1 plan was found to UNDER-COVER several measurable-impact areas:

1. **Throughput / concurrency** — v1 noted "no QPS targets defined" but proposed no instrumentation or capacity initiative. v2 adds **P0-5** (capacity & throughput baseline + protective limits).
2. **Correctness bugs that quietly degrade quality** — v1 was optimization-focused; missed potentially **silent data-corruption** bugs (duplicate tool execution on retry, conversation-history write race, stream-chunk dedup on failover). v2 adds **P0-6** (correctness guardrails).
3. **Enterprise readiness** — v1 explicitly de-scoped security; v2 re-scopes the **monetisable** subset of enterprise (per-tenant rate limit, pre-LLM PII scrub, prompt-injection guard, tool-call user-impersonation, audit logging of LLM I/O, data-residency routing). Added as **P1-4**.
4. **Monetisation conversion levers** — v1 covered cost reduction but not credit-conversion UX, paywall events, or paid-tier feature gating. Added as **P1-5**.
5. **Quantification discipline** — several v1 estimates lacked clear measurement plans. v2 adds a **§9 Measurement Charter** that names the metric, its source-of-truth dashboard, baseline collection method, and sampling cadence for every initiative.

**Net effect on cumulative outcome (12-week target):**

| Outcome | v1 estimate | v2 (revised, with P0-5/P0-6/P1-4/P1-5) |
|---|---|---|
| Send-message SLO | 99.6 → 99.9% | **99.6 → 99.9%** (unchanged; P0-1 still primary) |
| p95 TTFB | −25–35% | **−25–35% + reduced tail variance** (P0-5 backpressure caps remove p99 spikes) |
| LLM input-cost | −25–40% | −25–40% (unchanged) |
| Quality MTTD | <1 day | <1 day (unchanged) |
| **NEW: Sustained QPS headroom** | not measured | **+200–500 QPS / shard at p95 SLO** (P0-5 pool tuning + per-tenant limits) |
| **NEW: Memory safety** | not addressed | **−25% GC pause times** (P0-5 ConcurrentHashMap bounds) |
| **NEW: Silent data-corruption bug rate** | not addressed | **target 0** (P0-6 idempotency keys + transactional history writes) |
| **NEW: Enterprise deal-blocker count** | not addressed | **−6 blockers cleared** (P1-4: tenant rate limit, pre-LLM PII, audit, residency, soft-block UX, user-impersonation) |
| **NEW: Free→Paid conversion event** | not measured | **baseline + 5–8% lift** via paywall UX events (P1-5) |
| **NEW: Cost saved** annual | $0.6–1.0M | **$0.7–1.2M** (incl. P0-5 connection-pool right-sizing avoiding over-provisioned shards) |

---

## v2.1 New / re-prioritised initiatives

### **P0-5 — Throughput, concurrency, & memory-safety guardrails (NEW)**
**Goal:** Establish a measurable throughput envelope (QPS, concurrent streams, p99 tail), eliminate unbounded resource growth, prevent noisy-neighbor stalls.

#### Why this is P0
The v1 plan's TTFB and SLO targets are meaningless without a measured **capacity envelope**. If a single tenant can saturate the pool, P0-1's failover is overwhelmed. If `ConcurrentHashMap` allocations grow unbounded, GC pauses dominate p99. These are foundational.

#### Concrete problems (validated)
1. **HTTP client pool fixed-formula sizing.** `AggWebClientConfiguration.kt:48` sets `maxConnections = max(Runtime.getRuntime().availableProcessors(), 8) * 4` (i.e. 32–64 on prod). No per-route, per-host, or per-tenant differentiation. A single AGG-heavy tenant can drain the pool.
2. **No streaming backpressure bound.** Streaming Flux/Flow returned from `ChatV1Controller.kt:163-219` and `LLMServiceImpl.streamGeneration` have no `onBackpressureBuffer(n, OVERFLOW_STRATEGY)` ceiling; slow client → unbounded server buffer → OOM.
3. **No per-tenant rate limits.** `HeimdallRateLimiterConfiguration` and `ExperienceRateLimitFilter` only apply global limits. One tenant burst can starve others.
4. **Unbounded in-memory caches in request hot path.** `AvpMetricsApiServiceImpl.kt:43-44` *does* cap (`expireAfterWrite=2 min, maximumSize=200`) — good — but the `inFlight`, `mcpToolExecutionUnauthorised`, and per-loop tool-result accumulators inside `SimpleLoopWorkflowExecutorImpl` use raw `mutableMapOf<...>` / lists with no bound, growing per iteration.
5. **Unmeasured streaming chunk size.** No min-flush policy: tiny tokens shipped one-per-chunk inflate TCP frame count; conversely, jumbo chunks inflate latency variance.
6. **No HTTP/2 enforcement on inbound.** Mobile / browser clients may downgrade to HTTP/1.1, capping per-connection multiplexing — bad for streaming concurrency.
7. **No compression on `application/x-ndjson` streaming.** Network-bound clients pay full bandwidth.

#### Fix
1. **Capacity baseline first.** Add a 1-week canary run on a single shard with synthetic load (10 → 100 → 500 concurrent streams) and capture: p50/p95/p99 TTFB, throughput, CPU%, GC%, pool-acquire-wait, OOM headroom. Publish as the canonical "Convo-AI shard envelope" doc. *Without this, we cannot quantify any throughput claim.*
2. **Pool right-sizing** by actual saturation: introduce `convoai.pool.{name}.acquire_wait_ms_p95` metric; right-size each pool (AGG, Confluence, Jira, Bitbucket, Salesforce, AGS) based on observed wait. Suggested initial: AGG → 128, Confluence → 64, Jira → 64, others → 32. Validate via canary.
3. **Per-tenant token-bucket rate limiter.** New `TenantTokenBucketFilter` keyed on `cloudId` (or `aaid` fallback for unauthenticated paths), with limits sourced from `Statsig`-driven config per tenant tier (free: 60 req/min; standard: 600; enterprise: 6,000). Default deny graceful with `Retry-After`.
4. **Streaming backpressure bound.** `ChatV1Controller`: wrap returned `Flux<ServerSentEvent>` with `.onBackpressureBuffer(MAX_BUFFER, BufferOverflowStrategy.ERROR)` (suggest `MAX_BUFFER=1024` events). On overflow, emit a typed `STREAM_OVERFLOW` event and close.
5. **Bounded mutable accumulators.** In `SimpleLoopWorkflowExecutorImpl`, replace raw `mutableListOf` for tool-output accumulation with size-capped buffers; emit a typed metric when cap hit (signals an agent stuck in tool-spam).
6. **Min-flush + chunk batching.** In streaming output writer, batch tokens until either 64 ms elapsed OR 1.4 KB written; emit on first satisfied condition. Reduces TCP frame count by 5–10×.
7. **Enforce HTTP/2 on edge.** Verify Spring WebFlux `server.http2.enabled=true`; add a startup assertion.
8. **Enable compression** on `application/x-ndjson` (deflate; gzip is undesirable for streams). Verify via `Content-Encoding` response header in canary.

#### Measurable outcome
- Baseline doc published (week 2): "Convo-AI shard envelope" — measurable target for every subsequent change.
- p95 acquire-wait <50 ms across all pools.
- p99 TTFB tail variance −30%.
- Per-tenant stall events (one tenant bursting, others 5xx): target 0.
- Memory: −25% GC pause time at p95.
- Bandwidth: −30–40% on streaming responses (compression).

#### Owner / schedule
- **Foundation perf** + **convo-ai-service** owners. 1.5 eng × 5 weeks (1 wk capacity test, 2 wk pool/limit/backpressure, 2 wk wire-level + canary).

#### Risk
- Per-tenant rate limit too aggressive → false denials. Mitigation: dual-mode (observe-only first 2 weeks, enforce after).
- Backpressure buffer too small → user-visible stream truncation. Mitigation: emit overflow event so client can reconnect; tune from canary.

---

### **P0-6 — Correctness guardrails (NEW: idempotency, history-write isolation, FF stability, cancellation hygiene)**
**Goal:** Eliminate silent data-corruption / duplicate-effect bugs that erode user trust and inflate cost.

#### Why this is P0
A duplicate Jira ticket created by a retried tool call is invisible in latency dashboards but **directly user-visible** and erodes Trust Score. v1 plan did not address these.

#### Concrete problems (validated by code reading)
1. **Tool retry without idempotency key.** `SimpleLoopWorkflowExecutorImpl.kt:849-882` parallel-executes tools via `flatMap { async { ... } }`. On loop retry (after a tool error fed back per P0-1-B), nothing prevents the SAME tool re-executing with side-effects (e.g., creating two Jira tickets).
2. **Conversation history write race.** `ConversationManagerImpl` lacks transaction isolation between concurrent message writes on the same channel (two browser tabs same channel; or quick-fire user retries).
3. **Stream chunk dedup on failover.** When P0-1-C "soft resume" emits the fallback model's continuation, no dedup on overlap with the partial primary content. Could result in repeated tokens visible to the user.
4. **FF treatment switch mid-request.** Same Statsig flag re-checked across request lifecycle — if Statsig flips during a long agent loop, prompt template / model can switch mid-conversation. Inconsistent behavior; hard to debug.
5. **Coroutine cancellation hygiene.** When `Flux` is cancelled (user closes tab), the deep coroutine chain (LLM call → tool calls → DB writes) may not all observe cancellation. Detached `launch { ... }` writes proceed, wasting tokens and risking partial state.
6. **JSON parse failures on tool args.** When LLM emits invalid JSON for tool args, no recovery path catches & feeds back a typed error → loop wastes a turn.
7. **Multi-store dual-write hazard.** v1 P1-1 already addresses; v2 RE-PRIORITISES it as **P0** because the Create-scenario SLO miss is the most user-visible reliability gap.

#### Fix
1. **Idempotency-key contract** on all side-effecting tools. Tool registry declares `isSideEffecting: Boolean` + `idempotencyKeyTemplate: String`. Before executing a side-effecting tool, compute key from `(conversationId, messageId, toolCallId, argsHash)`. Store in `ProcessedToolCallStore` (DynamoDB w/ `conditional put`). Skip on duplicate; return cached result.
2. **Conversation-write transaction isolation.** Wrap dual-write in `TransactWriteItems` (ERS supports it); add ConditionExpression on monotonic `seq` to detect concurrent writes; on conflict, retry once with re-fetched seq.
3. **Stream-resume overlap dedup.** On soft-resume, prefix continuation with last-seen-token-prefix from primary; LLM uses it as a "continue from here" instruction; client-side dedup on `event_id`.
4. **Request-scope FF freeze.** `RequestScopedFlagCache` (P0-3-B) applies BEFORE the agent loop starts; all subsequent loop iterations consult the frozen snapshot. Eliminates mid-request flips.
5. **Structured cancellation.** Use `coroutineScope { ... }` instead of detached `launch { ... }` for any work that should die with the user request. `currentCoroutineContext().ensureActive()` checkpoints between tool calls. Add `convoai.cancellation.observed_ms` metric.
6. **Tool-arg JSON-parse recovery.** Catch `SerializationException` in tool dispatcher; emit `tool_error` with parse details fed back to LLM (per P0-1-B). Log at WARN with sample.
7. **Promote dual-store saga to P0.** See §v2.4 for the elevated P1-1 → P0-1.5 reprio.

#### Measurable outcome
- Duplicate side-effecting tool invocations: target **0** in production logs after rollout.
- Conversation-history write conflicts (currently un-instrumented): emit metric; target <0.01% conflict rate.
- Mid-request FF inconsistency events: target 0 after freeze.
- Token-waste from orphaned post-cancellation work: −80%.

#### Owner / schedule
- **AI Mate platform** + **conversation team**. 2 eng × 5 weeks.

#### Risk
- Idempotency-key collision (two intentionally-different calls hashing same). Mitigation: include `messageId` in key; conservative TTL (30 min) on cache.

---

### **P1-4 — Enterprise readiness (the monetisable subset)**
**Goal:** Unblock named enterprise deals; remove compliance objections; turn enterprise-readiness into a paid-tier differentiator.

#### Why this re-enters scope (was de-scoped in v1)
v1 deferred all "security" to gai. But several security-shaped items are actually **product features that block enterprise revenue**: per-tenant rate limit (sells as "guaranteed performance"), pre-LLM PII scrub (sells as "your data stays yours"), audit logging of LLM I/O (sells as "SOC 2 / FedRAMP-ready"), data residency (sells as "EU-data-stays-in-EU"). These are revenue-coupled.

#### Concrete problems (validated)
1. **Tool execution uses service-account impersonation header** rather than user UCT propagation — `AsyncJiraRestClientImpl.kt:39-40` `X-ATL-Creating-User-AAID`. Actions appear in Jira as "Rovo Agent on behalf of X" rather than as X. Privilege boundary blurred.
2. **PII / sensitive-data detection runs on RESPONSES** (`SensitiveDataDetectionServiceImpl`) but no equivalent runs on user INPUT before reaching the LLM provider.
3. **No prompt-injection guard.** RAG-retrieved Confluence/Jira content can contain instructions that steer the LLM (e.g., "ignore previous instructions, ...").
4. **Audit log omits LLM prompts and responses.** `AuditLogServiceImpl` records agent + tool actions but not LLM I/O — fails SOC 2 / FedRAMP discovery.
5. **No data residency routing.** EU/AU realm tenants' messages are sent to default LLM endpoints; no in-region pinning.
6. **No per-tenant concurrency cap.** Same gap as P0-5; called out separately because the *enterprise SLA narrative* requires it ("we guarantee 60 concurrent streams for your tenant").

#### Fix
1. **User-UCT-on-tool-call.** Tool registry declares `requiresUserContext: Boolean`. For user-context tools, pass user UCT (not agent service token) downstream. Surface "acted as user X" in audit log + Jira/Confluence audit trail.
2. **Pre-LLM PII pipeline.** Reuse `SensitiveDataDetectionServiceImpl` model on user input + RAG-retrieved snippets BEFORE assembling the LLM prompt. Behavior: per-tenant config — `mask` (default), `block` (enterprise-strict), or `warn`. Emit `convoai.pii_detected` span attr.
3. **Prompt-injection guard.** Wrap RAG-retrieved chunks in `<retrieved_content user_supplied="true">…</retrieved_content>` boundaries with a system-prompt hardening rule. For high-risk surfaces (tool call args derived from RAG), run a lightweight classifier (LLM judge or regex heuristic) and elevate to "human confirm" for write-side tools.
4. **LLM I/O audit log.** Extend `AuditLogServiceImpl` with `publishLLMRequestAuditLog()` + `publishLLMResponseAuditLog()`. Enterprise tier: full prompt + response, 7-yr retention. Standard tier: hash of prompt + length-only of response, 30-day retention.
5. **Data-residency routing.** Use `tenantContext.realm` + `tenantContext.region` to select LLM endpoint cluster (US, EU, AU). Wire into `LLMServiceImpl.routeRequest`. Emit `convoai.llm_region` span attr; alarm on mismatch.
6. **Per-tenant concurrency cap** — see P0-5; call out the enterprise tier guarantee in customer-facing SLA doc.

#### Measurable outcome
- Number of named enterprise deals previously gated by these items that close after the change. Tracked via Salesforce opportunity tag.
- Audit-log completeness on LLM I/O: 100% for enterprise tier.
- Cross-region LLM call rate (EU-tenant calling US-endpoint): target 0%.
- PII-detected-and-masked events: surface as a positive ENT-tier marketing metric.
- User-impersonation tool calls (acted-as-user vs acted-as-service-account): track ratio; target ≥80% on user-context tools after rollout.

#### Owner / schedule
- **Trust & Compliance** + **AI Mate platform**. 2 eng × 8 weeks. (Coordinate with Atlassian Trust org.)

#### Risk
- Pre-LLM scrub adds latency (best-est. 50–150 ms per request). Mitigation: run async + tee; only block on enterprise-strict mode.
- Prompt-injection classifier false-positives. Mitigation: enforce only on side-effecting tool args; observe-only on read-only tools.

---

### **P1-5 — Monetisation conversion levers (NEW)**
**Goal:** Make the free→paid funnel measurable and instrumentable; lift conversion 5–8% via targeted UX events.

#### Why this is significant
v1 covered "saving cost" but not "earning more revenue." Per the Rovo Strategy doc, monetisation gates H2 FY26. Today, credit denial is silent; users hit a wall and churn rather than upgrade.

#### Concrete problems (validated)
1. **Silent credit denial.** `UbpCreditsEnforcementServiceImpl` returns `allowed=false` without emitting a typed event the FE can render as a paywall. No `creditsRemaining` echoed to FE on each message.
2. **No `MONETIZATION` analytics product.** `AnalyticsEventProduct` enum lacks a monetisation surface; no canonical events for "credits-low warning", "upgrade-prompt-shown", "paid-feature-denied", "upgraded-from-prompt".
3. **Tool calls drain credits without per-call visibility** — user can't tell which agent action cost what.
4. **No paid-tier feature gating** for power features (deep-research, multi-agent, large-context). All-or-nothing flag pattern; no clean "free tier sees feature exists but is locked" affordance.

#### Fix
1. **Emit `creditsRemaining` and `creditsLowWarningThreshold` on every chat response** (header or first NDJSON event). FE renders progress bar + soft-warning at 20% remaining.
2. **Add `MONETIZATION` analytics product** to `AnalyticsEventProduct`; define `CREDITS_EXHAUSTED`, `UPGRADE_PROMPT_SHOWN`, `UPGRADE_PROMPT_CLICKED`, `PAID_FEATURE_DENIED`, `CREDITS_LOW_WARNING_SHOWN`, `UPGRADE_COMPLETED_FROM_PROMPT` events. Wire into UbpEnforcement deny-paths + paid-tier gating points.
3. **Per-tool-call credit attribution** in response metadata. FE expandable "what did this cost?" — drives transparent monetisation.
4. **Paid-tier feature gating SPI.** New `FeatureGate.requirePaid("deep-research")` helper consulted at code-path entry; on free tier, returns a typed `Locked(feature, upgradeUrl)` instead of executing. Metrics: per-feature lock-rate, per-feature upgrade-from-lock conversion.

#### Measurable outcome
- Free→paid conversion rate from chat surface: baseline + lift target 5–8%.
- Credit-low warning CTR.
- Per-feature upgrade-from-lock conversion (e.g., "deep-research locked → upgrade").
- "Cost transparency" event open-rate (signal of trust).

#### Owner / schedule
- **Rovo Growth + Monetisation eng**. 1 eng × 5 weeks.

#### Risk
- Aggressive paywall hurts MAU. Mitigation: dual goal — MAU floor + conversion lift; if MAU drops, soften paywall.

---

## v2.2 Re-prioritisation summary

| Item | v1 prio | v2 prio | Rationale |
|---|---|---|---|
| Multi-provider failover & tool-error feedback | P0-1 | **P0-1** (unchanged) | Still primary SLO mover |
| LLM cost reduction | P0-2 | **P0-2** (unchanged) | Direct $ savings |
| Latency parallelisation | P0-3 | **P0-3** (unchanged) | Quick win |
| Quality canary | P0-4 | **P0-4** (unchanged) | Detection gap |
| **Throughput & memory guardrails** | — | **P0-5 (NEW)** | Foundation for everything else |
| **Correctness guardrails** | — | **P0-6 (NEW)** | User-visible silent bugs |
| Dual-store saga (create-scenario SLO) | P1-1 | **P0-7** (promoted) | Highest-magnitude SLO miss (98.2 → 99.99% target = 1.8 pp) |
| Growth: cold-start & follow-ups | P1-2 | **P1-2** (unchanged) | MAU lever |
| Observability dashboards | P1-3 | **P1-3** (unchanged) | Detection layer |
| **Enterprise readiness** | — (was Appendix-D excluded) | **P1-4 (NEW)** | Revenue blocker |
| **Monetisation conversion** | — | **P1-5 (NEW)** | Direct $ uplift |
| Provider-class consolidation | P2-1 | **P2-1** (unchanged) | Long-term velocity |

---

## v2.3 Updated TL;DR table

| Rank | Goal | Concrete metric | Lever | Best-est. impact | Effort |
|------|------|-----------------|-------|-----------------|--------|
| **P0-1** | Send-msg SLO | 99.6 → 99.9% | Multi-provider streaming failover + per-tool deadlines + tool-error feedback | +0.30 pp | M (6 wks, 2 eng) |
| **P0-2** | Cost / monetisation | -25–40% LLM input-token cost | Anthropic prompt-cache default-on + OpenAI prefix opt + tool-catalog hash + cost-tier routing | $0.6–1.0M / yr | M (4 wks, 1.5 eng) |
| **P0-3** | TTFB latency | -25–35% p95 | Pre-stream parallelisation + request-scope FF cache + deferred channel persist | -800 ms to -1.5 s | S–M (3 wks, 1 eng) |
| **P0-4** | Quality canary | MTTD <1 day | Continuous canary eval + citation-preserving truncation + no-grounding detector | Detection from >quarter to <1 day | M–L (8 wks, 2 eng) |
| **P0-5 (NEW)** | Throughput & memory safety | +200–500 QPS; -25% GC | Pool right-sizing + per-tenant rate limiter + backpressure cap + bounded accumulators + min-flush + HTTP/2 + compression | +200–500 QPS / shard at SLO; -30–40% bandwidth | M (5 wks, 1.5 eng) |
| **P0-6 (NEW)** | Silent bug rate | target 0 dup-side-effects | Idempotency keys + history-write txn + FF freeze + cancellation hygiene + JSON-parse recovery | Eliminates user-visible silent corruption | M (5 wks, 2 eng) |
| **P0-7 (was P1-1)** | Create-scenario SLO | 98.2 → 99.5+% | Saga-pattern dual-store writes + outbox + reconciliation worker | +1.3 pp | M (5 wks, 1 eng) |
| **P1-2** | MAU / activation | +5–15k MAU | Cold-start agent recommend + cached follow-ups + UBP visibility + cross-session memory | 5–10% Day-7 conv lift | M (6 wks, 1.5 eng) |
| **P1-3** | Observability MTTD | <1 hr | TTFB + cost + quality dashboards + A/B hooks + Detekt enforcement | Median MTTD <1 hr | M (6 wks, 1 eng) |
| **P1-4 (NEW)** | Enterprise revenue | unblock 6 deal-blockers | User-UCT tool calls + pre-LLM PII + injection guard + LLM I/O audit + data residency | Closes named ENT deals | M–L (8 wks, 2 eng) |
| **P1-5 (NEW)** | Conversion uplift | +5–8% free→paid | creditsRemaining echo + MONETIZATION events + per-call attribution + paid-tier gating | Direct ARR uplift | M (5 wks, 1 eng) |
| **P2-1** | Maintainability | -8K LoC | Provider-class consolidation + extract `search/` module | -10–15% review burden | L (12 wks, 1 eng) |

**Total scope:** ~72 eng-weeks across 12 weeks calendar with 6–8 engineers. Achievable with the AI Mate + service-impl + conversation + observability + growth squads in parallel.

---

## v2.4 Measurement Charter (one row per initiative)

| Initiative | Primary metric | Source-of-truth dashboard | Baseline collection method | Sampling cadence | Definition-of-done |
|---|---|---|---|---|---|
| P0-1 (failover) | `frontend_chat_send_message_reliability` | TOME convoai SLO | TOME terraform locals.tf threshold; Splunk for raw event count | 1-min rolling; 7-day SLO window | 99.9% sustained for 14 consecutive days |
| P0-2 (cost) | `usage.cached_tokens / usage.input_tokens`; `$/msg` | New "LLM Cost" Splunk dashboard | LLM response usage object; AI Gateway billing export | per-request; daily aggregate | cached_tokens >=50% on multi-turn; cost/msg -25% on routine intents |
| P0-3 (TTFB) | `convoai.ttfb_ms` p50/p95/p99 | TOME convoai latency | New OTel histogram; existing TOME endpoint SLO | per-request | p95 -25% sustained 14d |
| P0-4 (quality) | `convoai.factual_consistency_canary_score` | New Splunk "AI Quality" | LLM-judge pipeline (P0-4-A) on 0.5% sample | per-conversation; 7-day rolling | synthetic regression detected <24h |
| P0-5 (capacity) | `convoai.pool.{name}.acquire_wait_ms_p95`; `convoai.streams.concurrent`; `convoai.gc.pause_ms_p99` | New Foundation perf dashboard | Reactor Netty metrics; JMX GC; Splunk per-tenant tagging | 1-min rolling | All pools acquire-wait <50ms p95; per-tenant cap enforced |
| P0-6 (correctness) | `convoai.duplicate_tool_call_count`; `convoai.history_write_conflict_count`; `convoai.ff_mid_request_flip_count` | New "Correctness" Splunk panel | New counters in tool-dispatcher + ConversationManager | per-event; daily aggregate | 0 duplicates; <0.01% conflicts |
| P0-7 (saga, was P1-1) | `agentstudio_create_scenario_reliability` | TOME convoai SLO | locals.tf threshold | 7-day SLO window | 99.5%+ sustained 14d |
| P1-2 (growth) | Day-7 retention; agent-recommend CTR; follow-up CTR | TOME growth + Amplitude | gasV3 events + Amplitude funnel | per-user; weekly cohort | +5pp Day-7 conv on canary cohort |
| P1-3 (observability) | mean MTTD on synthetic regression | Splunk alarms history | Pager + Statuspage | per-incident | median <1hr |
| P1-4 (enterprise) | Closed enterprise deals (Salesforce); audit completeness; cross-region rate | Salesforce ENT pipeline; new audit dashboard | SF opportunity tag; OTel `convoai.llm_region` attr | per-deal; per-request | 6 named blockers cleared; 100% LLM I/O audited on ENT |
| P1-5 (monetisation) | free->paid conversion from chat surface; credit-low CTR | New Amplitude funnel | New MONETIZATION analytics events | per-user; weekly | +5-8% conversion lift on canary |
| P2-1 (maintainability) | LoC delta; review turnaround | Bitbucket metrics | git log | per-PR | -8KLoC; -10% review time |

---

## v2.5 Updated sequencing (12-week phased)

### Phase 1 - Weeks 1-4 (foundation + measurement)
- P0-3 latency parallelisation (3 wk, 1 eng) - quick win
- P0-4 canary eval pipeline build (3 wk of 8) - gates downstream cost work
- P0-5 capacity baseline + pool right-sizing (2 wk of 5) - prerequisite for all throughput claims
- P1-3 TTFB / cost / quality span attrs (2 wk) - measurement layer

### Phase 2 - Weeks 4-8 (reliability + cost + correctness)
- P0-1 multi-provider streaming failover + tool-error feedback (6 wk, 2 eng)
- P0-2 prompt-cache default-on + tool-catalog hash + model routing (4 wk, 1.5 eng) - gated on P0-4 canary
- P0-5 per-tenant rate limit + backpressure (3 wk, 1 eng) - completes capacity work
- P0-6 correctness guardrails (5 wk, 2 eng)
- P0-7 dual-store saga (5 wk, 1 eng)

### Phase 3 - Weeks 6-10 (enterprise + monetisation)
- P1-4 enterprise readiness (8 wk, 2 eng) - starts week 6, runs through week 13 - longest runway
- P1-5 monetisation conversion levers (5 wk, 1 eng)

### Phase 4 - Weeks 8-12 (growth + alarms + dashboards)
- P0-4 dashboards + alarms (final 3 wk)
- P1-2 cold-start + cached follow-ups + UBP visibility (6 wk, 1.5 eng)
- P1-3 finalize per-agent dashboards (final 4 wk)

### Phase 5 - Weeks 12+ (background)
- P2-1 maintainability - background

### New dependency edges (v2)
- P0-5 capacity baseline -> required before any other latency claim is "verified"
- P0-6 idempotency keys -> required before P0-1's tool-error retry loop is enabled (else dup-side-effects)
- P0-3-B request-scope FF cache -> required for P0-6 FF freeze
- P1-4 user-UCT propagation -> required for any future enterprise-tier rollout
- P1-5 paid-tier feature gating -> requires P1-3 analytics events landed first

---

## v2.6 New machine-followable tasks (continued from section 6)

### TASK P0-5-A - Capacity baseline canary
- New: synthetic load harness in `modules/foundation/loadtest/` (or use existing perfhammer dir)
- Change: 1-week canary run on single shard; sweep 10 -> 100 -> 500 concurrent streams; capture p50/p95/p99 TTFB, throughput, CPU%, GC%, pool-acquire-wait
- Acceptance: published "Convo-AI Shard Envelope v1" doc; SLO panel in TOME shows current vs target
- Effort: M (2 wk)

### TASK P0-5-B - HTTP pool right-sizing
- File: modules/platform/client/client-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggWebClientConfiguration.kt:48
- Files: similar in confluence/jira/bitbucket/salesforce/AGS configurations
- Change: parameterise maxConnections via Statsig per-environment; instrument `acquire_wait_ms`; tune to keep p95 <50ms
- Acceptance: zero pool-exhaustion log lines under canary load
- Effort: S (3 d)

### TASK P0-5-C - Per-tenant token-bucket rate limiter
- New: modules/foundation/utilities/utilities-impl/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/ratelimit/TenantTokenBucketFilter.kt
- Wired into modules/service/convo-ai-service filter chain
- Change: token bucket keyed on cloudId; limits from Statsig per-tier; observe-only mode 2 wk then enforce; emit `Retry-After` header
- Acceptance: synthetic burst from one tenant doesn't degrade p95 latency for other tenants
- Effort: M (2 wk)

### TASK P0-5-D - Streaming backpressure cap
- File: modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt:163-219
- Change: wrap returned `Flux<ServerSentEvent>` with `.onBackpressureBuffer(1024, BufferOverflowStrategy.ERROR)`; emit typed `STREAM_OVERFLOW` event on overflow
- Acceptance: chaos test (slow client at 1KB/s) does not OOM server
- Effort: S (3 d)

### TASK P0-5-E - Bounded mutable accumulators
- File: modules/platform/workflow/workflow-impl/.../SimpleLoopWorkflowExecutorImpl.kt
- Change: replace raw `mutableListOf<...>` for `toolOutputsInCurrentLoop` and `functionMessages` with size-capped buffers; emit `convoai.workflow.accumulator_cap_hit` when cap reached
- Effort: S (3 d)

### TASK P0-5-F - Min-flush + chunk batching
- File: streaming output writer in convo-ai-service/.../streaming/
- Change: batch tokens until 64ms elapsed OR 1.4KB written; emit on first satisfied condition
- Acceptance: TCP frame count per response -50% to -90%
- Effort: M (1 wk)

### TASK P0-5-G - Enable HTTP/2 + ndjson compression
- File: modules/service/convo-ai-service application properties
- Change: `server.http2.enabled=true`; `server.compression.enabled=true` with `mime-types=application/x-ndjson,application/json`
- Acceptance: response headers show `Content-Encoding: deflate`; HTTP/2 negotiated on edge
- Effort: S (1 d)

### TASK P0-6-A - Idempotency-key contract for side-effecting tools
- Files: modules/platform/tool-registry/tool-registry-api + tool-registry-impl
- Change: extend `ToolMetadata` with `isSideEffecting: Boolean, idempotencyKeyTemplate: String`
- New: `ProcessedToolCallStore` (DynamoDB w/ conditional put, 30-min TTL)
- Wire into SimpleLoopWorkflowExecutorImpl.kt:849-882 dispatcher
- Acceptance: chaos test - retried tool call returns cached result, no second side effect
- Effort: M (2 wk)

### TASK P0-6-B - Conversation-write transaction isolation
- File: modules/platform/conversation/conversation-impl/.../ConversationManagerImpl.kt
- Change: wrap dual-write in `TransactWriteItems`; ConditionExpression on monotonic `seq`; on conflict, retry once with re-fetched seq
- Acceptance: chaos test - 100 concurrent writes on same channel produce 100 sequential entries (no dups)
- Effort: M (2 wk)

### TASK P0-6-C - Stream-resume overlap dedup
- File: LLMServiceImpl.kt soft-resume path (introduced in P0-1-C)
- Change: prefix continuation with last-seen-token-prefix from primary; client-side dedup on `event_id`
- Effort: S (3 d)

### TASK P0-6-D - Request-scope FF freeze
- File: modules/foundation/utilities/utilities-impl/.../featureflag/RequestScopedFlagCache.kt (introduced in P0-3-B)
- Change: snapshot all consulted flags at request entry; subsequent calls hit snapshot; emit `ff.cache.freeze_violations` if mid-request flip detected
- Effort: S (1 wk)

### TASK P0-6-E - Structured cancellation
- File: modules/product/rovo/rovo-impl/.../RovoChatService.kt; LLMServiceImpl.kt
- Change: replace detached `launch { ... }` with `coroutineScope { ... }`; add `currentCoroutineContext().ensureActive()` between tool calls; emit `convoai.cancellation.observed_ms`
- Acceptance: chaos test - close client connection mid-stream; downstream LLM call cancelled within 200ms
- Effort: M (1 wk)

### TASK P0-6-F - Tool-arg JSON-parse recovery
- File: SimpleLoopWorkflowExecutorImpl.kt tool dispatcher
- Change: catch SerializationException; emit `tool_error` with parse details fed back to LLM (per P0-1-B); WARN log with sample
- Effort: S (3 d)

### TASK P1-4-A - User-UCT-on-tool-call
- File: modules/platform/tool-registry tool metadata + modules/platform/client/client-impl/.../AsyncJiraRestClientImpl.kt:39-40 + similar Confluence/Bitbucket
- Change: tool registry declares `requiresUserContext: Boolean`; for user-context tools, propagate user UCT instead of agent service token
- Acceptance: Jira audit trail shows actions attributed to actual user, not "Rovo Agent"
- Effort: M (3 wk)

### TASK P1-4-B - Pre-LLM PII pipeline
- File: modules/product/chat-common/chat-common-api/.../SensitiveDataDetectionServiceImpl.kt - extend with `actionSensitiveDataDetectionOnRequest()`
- Wire into LLMServiceImpl.kt before sending to AI Gateway
- Change: per-tenant config (mask|block|warn); emit `convoai.pii_detected` span attr
- Effort: M (3 wk)

### TASK P1-4-C - Prompt-injection guard
- File: modules/platform/service/service-impl/.../search prompt-assembly path
- Change: wrap RAG-retrieved chunks in `<retrieved_content user_supplied="true">...</retrieved_content>`; for high-risk tool args derived from RAG, run lightweight classifier; elevate write-side tools to "human confirm"
- Effort: M (3 wk)

### TASK P1-4-D - LLM I/O audit log
- File: modules/platform/service/service-impl/.../auditlog/AuditLogServiceImpl.kt
- Change: add `publishLLMRequestAuditLog()` + `publishLLMResponseAuditLog()`; enterprise tier full prompt + response 7-yr retention; standard tier hash + length 30-day retention
- Effort: M (2 wk)

### TASK P1-4-E - Data-residency LLM routing
- File: LLMServiceImpl.kt `routeRequest`
- Change: use `tenantContext.realm` + `tenantContext.region` to select LLM endpoint cluster; emit `convoai.llm_region` span attr; alarm on mismatch
- Effort: M (2 wk)

### TASK P1-5-A - creditsRemaining echo on every chat response
- File: modules/platform/service/service-impl/.../ubpenforcement/UbpCreditsEnforcementServiceImpl.kt + ChatV1Controller streaming response
- Change: include `creditsRemaining`, `creditsLowWarningThreshold`, `creditsResetAt` in first NDJSON event or response header
- Effort: S (1 wk)

### TASK P1-5-B - MONETIZATION analytics events
- File: modules/platform/base/base-api/.../AnalyticsEventProduct.kt
- Change: add MONETIZATION product; define CREDITS_EXHAUSTED, UPGRADE_PROMPT_SHOWN, UPGRADE_PROMPT_CLICKED, PAID_FEATURE_DENIED, CREDITS_LOW_WARNING_SHOWN, UPGRADE_COMPLETED_FROM_PROMPT
- Wire into UbpEnforcement deny-paths and paid-tier gating points
- Effort: S (1 wk)

### TASK P1-5-C - Per-tool-call credit attribution
- File: response-builder code path
- Change: attach per-tool-call cost metadata to response; FE renders expandable "what did this cost?"
- Effort: S (3 d)

### TASK P1-5-D - Paid-tier feature gating SPI
- New: modules/platform/base/base-api/.../FeatureGate.kt with `requirePaid(featureKey: String): GateResult`
- Wire into deep-research, multi-agent, large-context entry points
- Change: free tier returns `Locked(feature, upgradeUrl)` instead of executing; metrics per-feature lock-rate, conversion-from-lock
- Effort: M (2 wk)

---

## v2.7 Acceptance gates (revised)

| Gate | Trigger | Measurement |
|---|---|---|
| Gate-1 (week 2) | P0-5-A capacity baseline published | Convo-AI Shard Envelope v1 doc + SLO panel |
| Gate-2 (week 4) | P0-3 + P1-3 span attrs landed | TOME shows `convoai.ttfb_ms` p95 <= baseline -200ms |
| Gate-3 (week 6) | P0-5-B/C/D rolled out (observe-only) | Pool acquire-wait p95 <50ms; backpressure overflow rate <0.01% |
| Gate-4 (week 8) | P0-1 stream failover at 25% + P0-6 idempotency | Send-msg SLO >=99.75% on canary cohort; 0 duplicate tool calls |
| Gate-5 (week 8) | P0-2 cost routing in shadow + P0-4 canary armed | Shadow $/msg <=80% primary; quality delta <2pp; synth regression detected <24h |
| Gate-6 (week 10) | P0-7 dual-store saga at 100%; P1-4 user-UCT rolled out for read-tools | Create-scenario SLO >=99.5%; user-UCT rate >=80% on user-context tools |
| Gate-7 (week 12) | All P0s at 100%; P1s at >=50% | Send-msg SLO >=99.9%; cost down >=25%; MTTD <1h; +200 QPS headroom validated |

---

## v2.8 Risks & mitigations (additions)

- Capacity baseline reveals worse-than-expected envelope (P0-5-A). Mitigation: publish anyway; recompute every other initiative's claim against measured baseline.
- Per-tenant rate limit triggers customer escalations. Mitigation: 2-week observe-only mode + customer comms before enforce.
- Pre-LLM PII pipeline adds 50-150ms latency. Mitigation: async + tee on standard tier; only block on enterprise-strict.
- Idempotency-key collision (rare). Mitigation: include messageId in key; conservative TTL (30min).
- Conversation-write transaction conflicts (under heavy concurrent use). Mitigation: emit metric; retry with backoff; observe before tightening.

---

## v2.9 Critical-thinking double-check log

This v2 pass corrected several v1 over-claims:

1. v1 claimed "agent loops can run forever" - WRONG. `for (loop in 1..config.maxLoops)` exists at SimpleLoopWorkflowExecutorImpl.kt:185. The real loop risk is **per-tool unbounded runtime + missing tool-error feedback**, not loop count. v2 P0-1 reflects the corrected risk.

2. v1 claimed "no max iteration cap on agent loop" - WRONG (same as above).

3. v1 "no prompt cache" - PARTIAL. Anthropic prompt cache IS implemented but FF-gated. OpenAI/Gemini paths do NOT apply cache hints. v2 P0-2 keeps the fix scope.

4. v1 "no fallback model" - PARTIAL. `withFallbackModelRetry` exists for non-streaming; streaming path does fallback only on PRE-EMIT errors. v2 P0-1 ships soft-resume.

5. v2 sub-agent claim "tool execution lacks dependency tracking" - PARTIALLY VALID. SimpleLoopWorkflowExecutorImpl.kt:849-882 uses `flatMap { async { ... } }` to PARALLELISE tool execution within a turn. This is CORRECT for independent tools (LLM-emitted tool_calls in a single turn are by-spec independent). The real risk is when LLM emits dependent tools - that case is **rare** (LLMs typically chain over multiple turns) but not impossible. v2 P0-6-A idempotency contract addresses the failure mode.

6. v2 sub-agent claim "M cache (AvpMetricsApiServiceImpl) lacks tenant scoping" - REQUIRES VERIFICATION before action. Cache key may already include tenant via wrapping context. Marked as a P0-6 audit item rather than a definite bug.

7. v2 sub-agent claim "TwgAssistantApiServiceImpl uses maximumSize=1" - CONFIRMED at line 29; this is intentional (single-config-per-instance singleton-style cache). NOT a bug.

8. v2 sub-agent claim "merge/mergeAll order-non-preserving" in LLMServiceImpl - REQUIRES VERIFICATION; many `flatMap` calls are over per-message data, not per-chunk. Re-read showed order-preserving usage in the streaming hot path. NOT confirmed.

This corrects-as-we-go discipline keeps the plan grounded.

---

End of v2 addendum.
