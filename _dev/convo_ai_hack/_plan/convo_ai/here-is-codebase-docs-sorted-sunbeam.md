# Convo AI / Rovo Chat — FY26 Goal-Driven Improvement Plan (v3 — comprehensive)

> Plan target: `C:\Users\yxinl\OneDrive\Projects\PythonProjects\CoreProjects\_dev\conversational-ai-platform`
> Investigation: **14 parallel agents over 3 waves · 80+ verified code-level findings** (file:line confirmed) · all top-leverage claims re-verified by direct file reading.
> v3 changes vs v2: adds **Throughput axis (T-series)**, **Feature Enhancements (F-series)**, **Caching/Coalescing (K-series)** as a separate workstream, **Operational Infra-Blockers (O-series)** elevated to Phase 0, **Repo-context items (R-series)** for stalled decisions.

---

## Context — Why this plan exists

The Conversational AI Platform (`convo-ai-service`, Kotlin/Spring Boot, 86 modules, 5-tier hexagonal) brokers Rovo Chat, AIFC, JSM/CSM AI, JPD/Loom AI, Marathon (Deep Research), Agent Studio. FY26 has **eight measurable goals**.

| Goal | Metric | Current | Target | Gap | Source |
|---|---|---|---|---|---|
| **Rovo MAU** | MAU | ~100.3k | **150k** by H2 FY26 | +50% | Atlas ATLAS-124112 |
| **Chat send-message reliability** | SLO | **99.6%** | 99.9% (LLM ceiling) | 0.3pp | TOME `convo_ai/locals.tf` |
| Agent Studio scenario create | SLO | 98.2% | 99.99% | 1.8pp | TOME |
| **AIFC factual consistency** (page-search ON) | LLM-judge | **13%** (was 80% baseline) | ≥ 70% | **57pp** | AIFC TWCLR2 (CRITICAL beta blocker) |
| AIFC contextual recall | LLM-judge | 47% | ≥ 65% | 18pp | AIFC Maturity Gap |
| AIFC contextual relevancy | LLM-judge | 40-44% | ≥ 70% | 27pp | AIFC Maturity Gap |
| AIFC Page Create Task Completion | % | unknown | 90% Beta | unknown | AIFC QBR |
| **Throughput** at 150k MAU peak | req/s peak (estimated) | ~1,500 cap | ~2,900 (5× burst) | **-48%** | Derived; no canonical target — **gap-of-target itself is a finding** |

**Hard ceiling**: OpenAI Scale Tier 99.9% caps LLM-dependent SLOs. Multi-provider failover is the only lever past it.

**Three design principles enforced everywhere**:
1. **Goal-driven priority** — every item declares one primary goal + quantified impact in goal-metric units + confidence + priority score = (impact / goal-gap) × confidence.
2. **User-facing-behavior preservation** — every item is tagged `user_facing_change: yes / no / conditional`. *Conditional* items split internal change from user-visible change (dual-list pattern). Any genuine UF change ships behind opt-in flag + cohort A/B + kill-switch + release note.
3. **Infra-blocker first** — auto-rollback, circuit breakers, graceful shutdown must EXIST before the 30+ flag rollouts in this plan are safe. v3 elevates these to Phase 0.

---

## A. Goal contribution matrix

| Goal (gap) | Item 1 | Item 2 | Item 3 | Item 4 | Total claimed gap closure |
|---|---|---|---|---|---|
| **AIFC FactualConsistency 70 (+57pp)** | Q1 LLM-rank +15-25pp | Q2 body excerpt +10-15pp | Q4 grounding prompt +8-12pp | Q3 score-threshold +3-5pp | **+36-57pp** |
| **AIFC ContextualRecall 65 (+18pp)** | Q2 +8-12pp | Q6 multi-source rerank +4-6pp | Q11 Slack date filter +2-4pp | Q14 ARIZE judge | **+14-22pp** |
| **AIFC Relevancy 70 (+27pp)** | Q1 +10-15pp | Q6/Q7/Q8/Q9/Q10 multi-source rerank +8-12pp | Q3 +3-5pp | Q4 +3-5pp | **+24-37pp** |
| **ChatSLO 99.9 (+0.3pp)** | L3 unblock servlet +0.1pp | T1 bound channel +0.1pp | T6 circuit breakers +0.05pp | L18 .blockingGet removal +0.05pp | **+0.3pp** (full gap) |
| **RovoMAU 150k (+50%)** | F2 starter prompts (Day-0 friction) | F4 last-conversation resume | F1 personality scope-fix (Trust/Fandom) | L1+T2 TTFB & throughput | **Direct activation lever × 4** |
| **Throughput +1400 req/s peak (+48%)** | T1 bound streaming channel | T2 AGG pool 4×→8× + eviction | T3 HTTP/2 multiplex AGG | T5 heap 5Gi→8Gi + ZGC | **+1400 req/s** (closes gap) |
| **CSM/JSM TTFB** | L22+L23 CSM streaming unblock | L24 HC ID cache | L25/L26 Firebolt cache+gate | L27/L28 JSM HR convergence | **-800-1500ms p50** |
| **Cost $/turn reduction** | C1 persist compaction -$80-120k/mo | K1 Anthropic prompt-cache enable -$40-80k/mo (Kotlin path) | C2 classifier debounce -$15-25k/mo | K3+K4+K5 caching layer -$80-150k/mo | **-$215-375k/mo** (was $110-170k in v2) |
| **EngVelocity LoC removed** | E1 retire A2AChatExecutor -1,370 LoC | E3 delete v1 410 routes -85 LoC | E2 PlanGenerator V2 cutover | E6 AIFEATURE split | **~1,500+ LoC** |

---

## B. TOP 12 items ranked by priority score (was 10 in v2)

| # | Item | File | Goal | Quantified impact | Conf | Effort | UF | Flag | Exit |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **O1 Add auto-rollback infra** (NEW Phase 0) | new + Statsig API + SignalFx detector | InfraBlocker | Enables every flagged item below; without it, plan v3 has no MTTR | 1.0 | M | no | n/a | A regressed flag auto-flips to 0% within ≤ 5 min of detector trip |
| **2** | C1 Persist compaction summary | [ContextCompactionServiceImpl.kt](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/agent/orchestrators/compaction/ContextCompactionServiceImpl.kt) | Cost | -$80-120k/mo | 1.0 | M | no | `ROVO_COMPACTION_PERSIST` | Re-compaction <0.2/conv |
| **3** | Q1 PageSearch L2 rerank for LLM context (split from UI) | [ConfluencePageSearchServiceImpl.kt:47-77](_dev/conversational-ai-platform/modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/common/contentretrieval/confluence/ConfluencePageSearchServiceImpl.kt#L47-L77) | FactualConsistency | +15-25pp | 1.0 | S | conditional (split) | `ROVO_PAGESEARCH_LLM_RERANK` | Eval factual ≥ 40% |
| **4** | **T1 Bound `Channel.UNLIMITED` in streaming writer** | [HttpRequestStreamingWriter.kt:44](_dev/conversational-ai-platform/modules/platform/base/base-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/base/streaming/HttpRequestStreamingWriter.kt#L44) | Throughput / Memory | Prevents unbounded memory growth on slow clients; closes a verified known-risk in code comment | 1.0 | S | no | `ROVO_STREAMING_BOUNDED_CHANNEL` | Heap-pressure alarms gone under burst |
| **5** | **T2 AGG WebClient pool 4×→8× + eviction** | [AggWebClientConfiguration.kt:48,67,135,158](_dev/conversational-ai-platform/modules/platform/client/client-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggWebClientConfiguration.kt#L48) | Throughput | +600 req/s peak; +0.1pp SLO under burst | 1.0 | S | no | `ROVO_AGG_POOL_LARGE` | Pool exhaustion alerts -90% |
| **6** | Q2 Add bodyExcerpt/passages (additive, no UI change) | [PageSearchResponse.kt:12-33](_dev/conversational-ai-platform/modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/confluence/PageSearchResponse.kt#L12-L33) | Recall+FC | +10-15pp recall, +10-15pp FC | 0.7 | M | conditional (additive) | `ROVO_PAGESEARCH_BODY_EXCERPT` | Recall ≥ 58% |
| **7** | L3 Remove `runBlockingWithContext` AI_EDITOR | [ChatV1Controller.kt:267](_dev/conversational-ai-platform/modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt#L267) | ChatSLO | +0.1pp SLO, -100-300ms tail | 1.0 | M | no | `ROVO_CHAT_NONBLOCKING_STREAM` | Tomcat busy-thread p99 < 60% |
| **8** | L1 AsyncTenantContext Caffeine cache | [AsyncTenantContextService.kt:35-260](_dev/conversational-ai-platform/modules/foundation/context/context-impl/src/main/kotlin/io/atlassian/micros/convoai/foundation/context/AsyncTenantContextService.kt#L35-L260) | TTFB / MAU | -100-200ms × N (avg -150ms p50) | 1.0 | S | no | `ROVO_TCS_CACHE` | Cache hit ≥ 95%, TCS RPS -80% |
| **9** | C2 Debounce in-session classifier | [InSessionSegmentationServiceImpl.kt:75-108](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/memory/conversation/InSessionSegmentationServiceImpl.kt#L75-L108) | Cost | -$15-25k/mo | 1.0 | S | no | `ROVO_SEGMENTATION_DEBOUNCE` | Classifier calls/turn ≤ 0.3 |
| **10** | **F1 Personality-experiment scope-fix (chat-only, not SAIN)** | [RovoChatAnswerGeneratorHelper.kt](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/answergenerator/RovoChatAnswerGeneratorHelper.kt) (active feature; PR #26895; doc-confirmed leak) | MAU/Trust | Unblocks broader rollout of the personality experiment; protects search-path factual tone | 1.0 | S | yes (scoped) | extends existing `rovo_chat_personality_experiment` flag | SAIN responses revert to factual; chat keeps personality |
| **11** | Q4 Grounding/citation system prompt | HybridOrchestrator prompt assembly | FC+Relevancy | +8-12pp FC, +3-5pp relevancy | 0.7 | S | conditional (output style) | `ROVO_HYBRID_GROUNDING_V1` | Citation-presence ≥ 90% |
| **12** | **F2 Empty-state starter prompts (Day-0 activation)** | new endpoint `GET /rovo/v1/me/starter-prompts`, integrate `MyActivitiesService` | RovoMAU activation | Direct Day-0 activation lever (industry-proven) | 0.7 | M | yes (release note) | `ROVO_STARTER_PROMPTS` | First-message rate +X% per cohort A/B |

---

## Measurement plan (M1-M7) — must ship in Weeks 1-2

| ID | What it proves | Required instrumentation |
|---|---|---|
| **M1** | AIFC eval harness | Golden 300-row dataset (Q13); LLMJudge factual + recall + relevancy; nightly job; per-flag-cohort deltas |
| **M2** | ARIZE per-turn quality | `LLMJudgeServiceImpl` wired into ARIZE event pipeline (Q14); 5% sample; cohort tags |
| **M3** | TTFB per-orchestrator + dispatcher utilization | `@WithSpan` + per-pool dispatcher utilization metrics (already partially in [CoroutineContextProvider.kt:80-94](_dev/conversational-ai-platform/modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt#L80-L94) `InstrumentedDispatcher`). Single panel: "Pre-LLM serial time" + per-pool saturation |
| **M4** | Cost per turn — **leverage existing** | Use Socrates `convo_ai_usage` data product (verified at `socrates-vnext/`) — it ingests `cloud_id, user_id, llm_model, llm_token_count, duration_ms` from StreamHub via Kinesis → dbt. Add per-feature attribution panel; do not reinvent |
| **M5** | Model-downsize quality non-regression | A/B with paired prompts; LLMJudge delta; user thumbs-down |
| **M6** | Cache discipline | Hit/miss/eviction per Caffeine cache; Redis memory + eviction; FF-call counter per request |
| **M7** | **NEW: Throughput / saturation** | Per-pod req/s; per-downstream connection pool saturation; HPA scale event log; pod cold-start time. Required to validate T-series claims |

**No item ships claiming impact until the relevant `M*` is live.** This is load-bearing for goal-driven prioritization.

---

## C. Per-workstream phased plan

### Workstream O — Operational Infra-Blockers (PHASE 0, MUST-DO)
**Why first**: plan v3 has 30+ feature flag rollouts assuming auto-rollback + circuit breakers + graceful drain. Audit confirmed these are partial/absent. Without them, the plan is fictional.

| ID | Name · File | Change | Effort | Risk | UF | Exit |
|---|---|---|---|---|---|---|
| **O1** | **Auto-rollback wiring** — SignalFx detector → Statsig API | `operations/terraform/modules/.../detectors/` + new `RollbackController` Lambda (or CloudFunction) | M | medium | no | A regressed flag auto-flips to 0% within ≤ 5 min of detector trip; chaos-drill verified |
| **O2** | **Circuit breakers** (Resilience4j) wrapping AI Gateway, AGG, TCS, Statsig, Heimdall | `modules/platform/client/...` per-client | M | low | no | Single-dep failure does not cascade in fault-injection test |
| **O3** | **Graceful shutdown / stream drain** — `preStop` hook + 30-60s drain | [helm/templates/webserver.yaml:90-114](_dev/conversational-ai-platform/helm/templates/webserver.yaml#L90-L114) (verified: no preStop) | S | low | no | Rolling deploy preserves in-flight streams; no EOF mid-answer in canary deploy test |
| **O4** | **Tenant-level canary registry** | new — small static list under `config/`, drive via Statsig user-targeting | S | low | no | Named tenants reliably get new flags first |
| **O5** | **Schedule batch eval cron** — leverage existing `AgentStudioBatchEvaluationJobRun` (verified to exist) | `bitbucket-pipelines.yml` or k8s CronJob | S | low | no | Nightly eval runs against AIFC golden set; trend chart populated |
| **O6** | **Per-tenant SLO dashboards** | `operations/terraform/modules/dashboards/` | S | low | no | Per-tenant chat-message SLO panel; ops can spot noisy-neighbor effects |

### Workstream A — AIFC Quality Recovery (Beta-GA blocker)
**Goal**: factual 13 → ≥70% · recall 47 → ≥65% · relevancy 40-44 → ≥70%.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **Q1** | LLM-context rerank (split) · [ConfluencePageSearchServiceImpl.kt:47-77](_dev/conversational-ai-platform/modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/common/contentretrieval/confluence/ConfluencePageSearchServiceImpl.kt#L47-L77), [PageSearchPlugin.kt:175-186](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/plugin/pagesearch/PageSearchPlugin.kt#L175-L186) | Two ordered lists: `uiOrdered=byLastModified` (existing — for `sources`/`header`), `llmOrdered=byScoreL2Desc.take(20)` (new — LLM context only) | S | low | conditional (split) | `ROVO_PAGESEARCH_LLM_RERANK` | Eval factual ≥ 40%; UI snapshot diff = 0 | M1 |
| **Q2** | Add `bodyExcerpt`+`passages` (additive) · [PageSearchResponse.kt:12-33](_dev/conversational-ai-platform/modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/confluence/PageSearchResponse.kt#L12-L33) | Add NULLABLE fields; UI emits `snippet` (unchanged); LLM emits `passages ?: bodyExcerpt ?: snippet` | M | medium | conditional (additive) | `ROVO_PAGESEARCH_BODY_EXCERPT` | Recall ≥ 58%; payload p99 < 16MB | T9 advisable |
| **Q3** | Score-threshold + topK trim · [PageSearchPlugin.kt:272](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/plugin/pagesearch/PageSearchPlugin.kt#L272) | `first=50` raw passthrough → threshold (default 0.35) + topK=10 (LLM context only) | S | low | conditional (LLM-side) | `ROVO_PAGESEARCH_TOPK` | Tokens/turn -30% | Q1 |
| **Q4** | Grounding system prompt · HybridOrchestrator | "answer only from retrieved context; cite source IDs" + refusal pattern | S | low | conditional (output style + release note) | `ROVO_HYBRID_GROUNDING_V1` | Citation-presence ≥ 90% | M2 |
| **Q5** | Page-search opt-in re-eval · [PageSearchPlugin.kt:84](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/plugin/pagesearch/PageSearchPlugin.kt#L84) | Convert opt-in-to-disable → opt-in-to-enable AFTER Q1+Q2+Q3+Q4 | S | medium | yes (release note) | replace existing flag | A/B win ≥ +10pp factual | Q1-Q4 |
| **Q6** | Confluence multi-source rerank · `SearchConfluenceServiceImpl.kt:63-87, 121` | Use captured `scoreL2Ranker` for LLM-context; UI unchanged | S | low | conditional (split) | `ROVO_CONFSEARCH_LLM_RERANK` | Relevancy +4-6pp | Q1 |
| **Q7** | Slack rerank · `SlackSearchServiceImpl.kt:49-371` | Same dual-list split; cross-encoder for LLM context | M | medium | conditional (split) | `ROVO_SLACKSEARCH_LLM_RERANK` | Relevancy +3-5pp | Q1 |
| **Q8** | First-party multi-type rerank · `FirstPartySearchServiceImpl.kt:38-86` | Score-normalize per type; interleave for LLM context | M | medium | conditional (split) | `ROVO_FPSEARCH_LLM_RERANK` | Relevancy +2-4pp | Q6 |
| **Q9** | Jira issue neural rerank · `JiraIssueSearchServiceImpl.kt:101-277` | LLM-context only; UI JSIS order preserved | M | low | conditional (split) | `ROVO_JIRA_LLM_RERANK` | Recall +2-3pp | — |
| **Q10** | JSD Apollo rerank · `JsdApolloSearchServiceImpl.kt` | Same split | S | low | conditional | `ROVO_JSD_LLM_RERANK` | Recall +1-2pp | — |
| **Q11** | Slack `before`/`after` filter forward · `SlackRealTimeSearchMcpTool.kt` (using args from [SlackRealTimeSearchArguments.kt:24-25](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/mcp/tool/slack/types/arguments/SlackRealTimeSearchArguments.kt#L24-L25)) | Wire existing args through | XS | low | yes (bug fix) | `ROVO_SLACK_DATE_FILTER_FIX` | Filter applied rate ≥ 99% | — |
| **Q12** | CI quality gate · [bitbucket-pipelines.yml](_dev/conversational-ai-platform/bitbucket-pipelines.yml) | Eval pipeline step using `AgentStudioBatchEvaluationV1Controller` + `LLMJudgeServiceImpl`; block PRs that regress factual ≥ 3pp | M | low | no | none | Pipeline blocks a synthetic regression test | M1, O5 |
| **Q13** | Golden dataset (300+ rows) · `convo-ai-test-integration/src/test/resources/evaluation/aifc/golden_v1/*.jsonl` | **Verified empty today** (`evaluation/` only contains macOS metadata files). Replace with 300+ stratified labels | M | low | no | none | ≥ 300 cases, 80/20 holdout | Q12 |
| **Q14** | ARIZE in-loop LLM-judge · `LLMJudgeServiceImpl` | Wire to per-turn ARIZE; 5% sample | M | low | no | `ROVO_ARIZE_JUDGE_INLOOP` | Per-turn factual score visible | — |

### Workstream B — Rovo Chat TTFB & SLO
**Goal**: SLO 99.6 → 99.85+; p50 TTFB -25-35%.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **L1** | TCS cache · [AsyncTenantContextService.kt:35-260](_dev/conversational-ai-platform/modules/foundation/context/context-impl/src/main/kotlin/io/atlassian/micros/convoai/foundation/context/AsyncTenantContextService.kt#L35-L260) | `Caffeine.AsyncCache` per-method, TTL 60-300s, max 50k | S | low | no | `ROVO_TCS_CACHE` | Hit ≥ 95%, p50 -150ms | — |
| **L2** | Batch config-service · [ChatExecutorRouterImpl.kt:48-52](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/executors/ChatExecutorRouterImpl.kt#L48-L52) | Single `getRoutingConfig(agentId)` + Caffeine | S | low | no | `ROVO_ROUTER_BATCH` | Config-svc RPS -50% | — |
| **L3** | AI_EDITOR non-blocking · [ChatV1Controller.kt:267](_dev/conversational-ai-platform/modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt#L267) | Reactive `Flux<ServerSentEvent>` | M | medium | no | `ROVO_CHAT_NONBLOCKING_STREAM` | Tomcat busy < 60% p99 | O3 |
| **L4** | Parallel pre-LLM gates · `LongHorizonOrchestratorAgent` | `coroutineScope { async … }` for FF/agent/tool-rank | M | medium | no | `ROVO_LH_PARALLEL_GATES` | TTFB p50 -25% | L1, L8 |
| **L5** | Pre-warm Jackson writer · [SseStreamingWriter.kt:31](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/SseStreamingWriter.kt#L31) | Static `ObjectWriter` per chunk class | S | low | no | none | -10-20µs/chunk × 75 | — |
| **L8** | Request-scoped FF memoization | Statsig wrapper `RequestScope` map | S | low | no | `ROVO_FF_MEMO` | Statsig RPS -80% | — |
| **L9** | ContentHydration N+1 fix · `ContentHydrationService.kt` | DataLoader / batch GraphQL aliases | L | high | no | `ROVO_HYDRATION_BATCH` | Search p95 -3-5s | — |
| **L10** | Kamino multi-region parallel publish · `KaminoDataServiceImpl.kt:66, 94` | `awaitAll` regional publishes | M | medium | no | `KAMINO_PARALLEL_PUBLISH` | Multi-region p50 -2× | — |
| **L11** | Bound `LLMResponseChunkAccumulator.partialToolCalls` · `LLMResponseChunkAccumulator.kt:30` | Max-size LRU; cleanup on tool completion | S | low | no | none | Heap-leak alarm gone | — |
| **L13** | Retry jitter · AggClient | Exponential + decorrelated jitter | S | low | no | `ROVO_AGG_RETRY_JITTER` | Retry-storm RPS -90% | — |
| **L14** | Pagination strategy at `first:50` callsites | Cursor pagination + topK from L2 | M | medium | no | `ROVO_GRAPHQL_PAGINATE` | Avg page size 10 | Q3 |
| **L15** | Per-conversation MCP session · `AdkToolsServiceFromMcp.kt:159-186` (TODO `GAPF-1554`) | Session manager keyed by conversationId | M | medium | no | `ROVO_MCP_SESSION_REUSE` | MCP setup -70% | L17 |
| **L16** | Sandbox cache TTL · `AtlassianSandboxEndpointProvider.kt:54` | 3480s → 1800s + refresh-ahead | S | low | no | none | Expiry-miss <0.1% | — |
| **L17** | Tool registry per-conversation cache · `ToolRegistryServiceImpl.kt:34-74` | Cache by (tenantId, agentId) | M | medium | no | `ROVO_TOOLREG_CACHE` | Build calls/turn -90% | L19 |
| **L18** | Remove `.blockingGet` · `AdkToolsServiceFromMcp.kt:96-98, 126` | suspend/await | M | medium | no | `ROVO_MCP_NONBLOCKING` | Reactive starvation 0 | — |
| **L19** | Tenanted agent inventory cache · `AgentRegistry.kt:10-22` | Caffeine TTL 30s | S | low | no | `ROVO_AGENT_INV_CACHE` | Registry RPS -80% | — |
| **L20** | MCP tools `Map` lookup · `McpServerManagerImpl.kt:14-31` | List → ConcurrentHashMap | XS | low | no | none | Lookup O(1) | — |
| **L21** | History delta fetch · [InSessionSegmentationServiceImpl.kt:312-319](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/memory/conversation/InSessionSegmentationServiceImpl.kt#L312-L319) | Tail-only fetch by lastSeq cursor | M | medium | no | `ROVO_HISTORY_DELTA` | History fetch p50 -60% | C2 |
| **L31** | Compaction ratio guard · `ContextCompactionHook.kt:55-63` | Fire only when tokens > threshold AND ratio > 1.2 | S | low | no | `ROVO_COMPACTION_GUARD` | Compaction freq -50% | C1 |
| **L32** | Realtime async send · `OpenAiRealtimeProvider.kt:74-86` | Non-blocking `sendMessageIfReady` | S | low | no | `ROVO_REALTIME_ASYNC_SEND` | TTFA -80-120ms | — |

### Workstream T — Throughput / Capacity (NEW in v3)
**Goal**: close estimated 1,400 req/s peak gap at 150k MAU. **No canonical QPS target exists** in docs or terraform — *this absence is itself a finding* and gets a corresponding M7 dashboard item.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **T1** | **Bound `Channel.UNLIMITED`** · [HttpRequestStreamingWriter.kt:44](_dev/conversational-ai-platform/modules/platform/base/base-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/base/streaming/HttpRequestStreamingWriter.kt#L44) (verified: code comment literally says "Risk: possible memory growth") | `Channel.UNLIMITED` → bounded `Channel<T>(capacity = 10_000, onBufferOverflow = SUSPEND)` with backpressure | S | low | no | `ROVO_STREAMING_BOUNDED_CHANNEL` | Heap-pressure alarm gone under burst test | — |
| **T2** | **AGG WebClient pool 4×→8× + eviction enabled** · [AggWebClientConfiguration.kt:48,67,135,158](_dev/conversational-ai-platform/modules/platform/client/client-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggWebClientConfiguration.kt#L48) (verified: pool = `max(cores,8) * 4` = 32-64 on typical pods; codec hardcoded 24MB) | Pool 8×; eviction `withEviction=true`, idle 30s, max-life 60s; codec 24MB → 64MB | S | medium | no | `ROVO_AGG_POOL_LARGE` (load-tested before flip) | Pool exhaustion alerts -90%, AGG p99 stable, no FD exhaustion | M7 |
| **T3** | **HTTP/2 multiplex on AGG** | Enable h2 in `WebClientConfiguration` | M | low | no | `ROVO_AGG_HTTP2` | Connection count to AGG -10×; throughput +30% | T2 |
| **T4** | **Bound `AsyncAgentInMemoryQueue`** · `AsyncAgentWorkflowOrchestrator.kt` | Add capacity param; default 5,000; metric on overflow | S | low | no | none | Async-queue heap-leak alarm gone | — |
| **T5** | **Heap 5Gi → 8Gi + ZGC** · [helm/templates/webserver.yaml:101-107](_dev/conversational-ai-platform/helm/templates/webserver.yaml#L101-L107) (verified: 5Gi req / 6Gi limit) | Increase heap; switch G1 → ZGC (sub-ms pauses for streaming) | S | low | no | none | GC pause p99 < 5ms; heap util steady-state | M7 |
| **T6** | **Circuit breakers around downstreams** | merged into O2; relisted here for traceability | M | low | no | n/a | n/a | O2 |
| **T7** | **Default WebClient pool sizing for non-AGG clients** · [WebClientConfiguration.kt:156-176](_dev/conversational-ai-platform/modules/platform/client/client-api/src/main/kotlin/io/atlassian/micros/convoai/platform/client/common/WebClientConfiguration.kt) | Default `max(cores,8)*2` → `*8` for high-volume clients (AssistanceClient, AI Gateway) | S | medium | no | `ROVO_DEFAULT_POOL_LARGE` | Pool wait p99 < 5ms | M7 |
| **T8** | **Pod cold-start: AppCDS** | Enable AppCDS in `Dockerfile` / build | M | medium | no | none | Cold-start p50 -50% (15-20s) | — |
| **T9** | **AGG codec buffer raise** · [AggWebClientConfiguration.kt:67,135,158](_dev/conversational-ai-platform/modules/platform/client/client-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/client/agg/AggWebClientConfiguration.kt#L67) | Merged into T2; relisted (same flag) | S | low | no | n/a | n/a | T2 |
| **T10** | **Per-pool dispatcher saturation metrics** | Already partially exists via `InstrumentedDispatcher` ([CoroutineContextProvider.kt:80-94](_dev/conversational-ai-platform/modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt#L80-L94)). Wire to dashboard | S | low | no | none | Per-pool saturation panel live; verify before tuning T11/T12 | M7 |
| **T11** | **Re-tune `streamingWriterPool=1024`** ([CoroutineContextProvider.kt:46](_dev/conversational-ai-platform/modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt#L46)) — INFERRED, **measure first** | After T10 dashboard is live, tune based on p99 saturation | S | medium | no | `ROVO_STREAMING_POOL_TUNE` | Per-pool util ≥ 50% at peak; no contention with other pools | T10 |
| **T12** | **Re-tune `MAX_IO_PARALLELISM=3072`** ([CoroutineContextProvider.kt:156](_dev/conversational-ai-platform/modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt#L156); explicit TODO at line 32 "Tune the parallelism based on metrics") | After T10, set parallelism per data | S | medium | no | `ROVO_IO_POOL_TUNE` | CPU context-switch overhead < 10% at peak | T10 |
| **T13** | **Define explicit QPS targets** in TOME terraform | Document target req/s per pod and cluster as a first-class SLO | S | low | no | none | TOME PR merged with QPS target | — |
| **T14** | **DNS caching tune** · JVM `networkaddress.cache.ttl` | Raise from 30s default to 300s; document | XS | low | no | none | DNS lookups/sec -90% | — |

### Workstream C — Cross-cutting Cost
| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **C1** | **Persist compaction summary** · [ContextCompactionServiceImpl.kt](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/agent/orchestrators/compaction/ContextCompactionServiceImpl.kt) | Versioned, checksummed summary in conv-store; reuse if hash matches | M | medium | no | `ROVO_COMPACTION_PERSIST` | Re-compaction <0.2/conv; **-$80-120k/mo** | L31 |
| **C2** | **Debounce in-session classifier** · [InSessionSegmentationServiceImpl.kt:75-108](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/memory/conversation/InSessionSegmentationServiceImpl.kt#L75-L108) | Skip when last < N turns AND embedding-cosine > 0.85 | S | low | no | `ROVO_SEGMENTATION_DEBOUNCE` | Calls/turn ≤ 0.3; **-$15-25k/mo** | — |
| **C3** | Citation model GPT_4_1 → GPT_4_1_MINI · [SAINLanguageModelConfig.kt:78-85](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/sain/orchestrator/SAINLanguageModelConfig.kt#L78-L85) | A/B citation accuracy | S | medium | no | `ROVO_CITATION_MODEL_MINI` | Accuracy ΔLLM-judge ≤ 1pp; **-$3-5k/mo** | M5 |
| **C4** | Lumina model GPT_5_1 → GPT_5_1_MINI · [SAINLanguageModelConfig.kt:107-123](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/sain/orchestrator/SAINLanguageModelConfig.kt#L107-L123) | A/B quality | S | medium | no | `ROVO_LUMINA_MODEL_MINI` | Quality non-regression; **-$5-8k/mo** | M5 |
| **C5** | `CacheFriendlyPromptAssembler` adoption to V1 / non-LH paths | Adopt across remaining executors | M | low | no | `ROVO_CACHE_PROMPT_V1` | Cache-hit-tokens ratio +20pp | — |
| **C6** | Tool ranking pre-serialization | Move `ToolRankingService` ahead of schema serialize | S | low | no | `ROVO_TOOLS_PRERANK` | Schema tokens -14k/turn | L17 |
| **C7** | Batch-API path for offline workloads | Route eval/index/summary to OpenAI/Anthropic Batch API | M | low | no | `ROVO_BATCH_API_OFFLINE` | Offline cost -50% | — |
| **C8** | Dedup Lumina + SAIN classifiers · `LuminaClassificationService.kt:60-120` + `SainOrchestrationComplexityClassifier.kt:63-81` | Single classifier emits both labels | M | medium | no | `ROVO_CLASSIFIER_DEDUP` | Classifier calls -50%; **-$5-8k/mo** | — |
| **C9** | DeepResearch convergence stop · `DeepResearchExecutionAgent` | Same-citations-twice → finalize | M | medium | no | `ROVO_DR_CONVERGE` | Avg iterations -25%; **-$5-7k/mo** | L29 pattern |

### Workstream K — Caching / Coalescing / Speculative (NEW in v3)
**Goal**: cost AND latency double-wins. Many were buried under "C" in v2; v3 elevates because the in-codebase infrastructure (`RedisCacheClient`) is built but unused.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **K1** | **Anthropic prompt-cache enable in Kotlin path** — verify `cache_control` markers actually emit (audit existing [CacheFriendlyPromptAssembler.kt](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/agent/prompt/CacheFriendlyPromptAssembler.kt) usage by request builders) | Verify and fix any builder that drops markers; audit V1, SAIN, A2A | M | low | no | none (it's a fix, not a rollout) | ARIZE prompt-cache-hit ≥ 70%; **-$40-80k/mo** | M2 |
| **K2** | **Python sidecar prompt caching ENABLE** · [python-sidecar/src/agents/agent.py:142](_dev/conversational-ai-platform/python-sidecar/src/agents/agent.py#L142) (**verified disabled** — line 142 is a commented `# model = get_model(..., self.prompt_caching_strategy)` and line 143 falls back without caching) | Re-enable the call site; verify `prompt_caching_strategy` field (line 95, default `"last_4"`) actually applies | S | low | no | `PYSIDECAR_PROMPT_CACHE_ENABLED` | Sidecar cost -15-25%; scope: sidecar workloads (Marathon-research path), NOT main chat | — |
| **K3** | **Tool-result coalescing within turn** | Deduplicate identical `(toolName, args)` calls in same turn (same conversation, same orchestrator iteration) | M | medium | no | `ROVO_TOOL_RESULT_COALESCE` | Tool RPS -20-30% on multi-classifier paths | — |
| **K4** | **In-flight singleflight for AGG / TCS / Statsig** | Coalesce identical concurrent upstream calls | M | medium | no | `ROVO_UPSTREAM_SINGLEFLIGHT` | Upstream RPS -10-30% during burst | — |
| **K5** | **Edge cache headers** for static GETs (agent list, tool registry) | Set `Cache-Control: public, max-age=30` + `ETag`/`Last-Modified` on idempotent GETs | S | low | conditional (clients honoring stale-while-revalidate get faster responses but may see brief staleness) | `ROVO_EDGE_CACHE_HEADERS` | Backend RPS for those endpoints -80% | — |
| **K6** | **Wire `RedisCacheClient` into chat flows** · [RedisCacheClient.kt](_dev/conversational-ai-platform/modules/platform/client/client-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/client/redis/RedisCacheClient.kt) (built; usage check: agent's claim of "zero callsites" is INFERRED — verify with grep before relying on $ figure) | Identify cacheable patterns (per-conv tool results, FAQ); wire incrementally | M | medium | no | `ROVO_REDIS_TOOL_CACHE` | Cache hit-rate ≥ 30% on instrumented patterns | M6, K3 |
| **K7** | **Embedding similarity cache** for repeat queries | Cache by query-embedding cosine > 0.95 | M | medium | conditional (could surface near-stale FAQ answers — TTL 1h + manual refresh) | `ROVO_EMBED_SIM_CACHE` | Embed RPS -50%; FAQ-style query latency -200-500ms | — |
| **K8** | **Malformed-LLM-response repair** before retry | Local JSON repair (e.g., `json-repair` lib) instead of re-call on minor errors | S | low | no | `ROVO_LLM_JSON_REPAIR` | Re-call rate on parse-failure -80% | — |

### Workstream F — Feature Enhancements (NEW in v3)
**Goal**: direct activation/MAU levers. Most are M-effort but high upside on the activation funnel.

| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **F1** | **Personality-experiment scope-fix** · [RovoChatAnswerGeneratorHelper.kt](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/answergenerator/RovoChatAnswerGeneratorHelper.kt) (active feature; PR #26895; doc-confirmed leak into SAIN/Search) | Add caller-context check; only apply personality on chat path, NOT SAIN/Search | S | low | yes (release note: search reverts to factual tone) | extends existing `rovo_chat_personality_experiment` | SAIN responses revert to factual; chat keeps warm tone | — |
| **F2** | **Empty-state starter prompts** (Day-0 Activation) | New endpoint `GET /rovo/v1/me/starter-prompts`; integrate `MyActivitiesService` for context-aware suggestions | M | medium | yes (release note + UX work) | `ROVO_STARTER_PROMPTS` | First-message rate +X% per cohort A/B | — |
| **F3** | **Adaptive follow-up count** · existing follow-up template `templates/aidefinition/follow_up_prompt.pebble` accepts 0-3 | Track click-rate; adapt count per user via FF | M | low | yes (release note) | `ROVO_FOLLOWUP_ADAPTIVE_COUNT` | Follow-up CTR +X%; conversation continuation rate +X% | M2 |
| **F4** | **Last-conversation resume** | Add endpoint returning recent N conversation summaries; UI shows "Continue?" on app open | S | low | yes (release note) | `ROVO_LAST_CONV_RESUME` | Day-1 return rate +X% in cohort A/B | — |
| **F5** | **Citation hover preview** | Backend: enrich citation envelope with `{title, snippet, lastUpdated}`; FE: hover tooltip | S/M | low | yes (release note) | `ROVO_CITATION_PREVIEW` | Citation-click rate +X% | — |
| **F6** | **Confidence scoring badges** | Prompt LLM to emit `HIGH/MEDIUM/LOW_CONFIDENCE`; envelope passes to UI | M | medium | yes | `ROVO_CONFIDENCE_BADGES` | User trust survey +X% | M2 |
| **F7** | **Graceful error UX** | Unify LLM-failure / tool-failure / rate-limit error messages; preserve partial-streamed content | M | low | yes | `ROVO_GRACEFUL_ERROR_UX` | User-reported "lost answer" rate -X% | O3 |
| **F8** | **Recent-activity context injection** in system prompt | Use existing `MyActivitiesService` to inject "user recently viewed: …" | S | low | no (transparent to user; better answers) | `ROVO_RECENT_ACTIVITY_CTX` | Clarification-turn rate -X% | — |
| **F9** | **Stale-source warning** | When retrieved page lastModified > 180d, prefix in markdown "(may be outdated)" | S | low | yes | `ROVO_STALE_SOURCE_WARN` | Hallucination on stale-content -X% | M2 |
| **F10** | **Feedback loop → ARIZE / dataset growth** | Wire thumbs-down to ARIZE event with metadata (model, tools used); auto-add to candidate-eval list | M | low | no | none | Negative-feedback turns flow into next eval cycle | M2, Q13 |
| **F11** | **Hardcoded prompt → Statsig dynamic config** for base instructions in `oai_chat_completions.pebble` | Move "On your profile" block to dynamic config | S | low | no | `ROVO_BASE_PROMPT_DYNAMIC` | Base-prompt iteration cycle: deploy → no deploy | — |

### Workstream E — Engineering Velocity / Debt
| ID | Name · File | Change | Effort | Risk | UF | Flag | Exit | Dep |
|---|---|---|---|---|---|---|---|---|
| **E1** | Retire A2AChatExecutor (1,370 LoC verified) · [ChatExecutorRouterImpl.kt:18-19](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/executors/ChatExecutorRouterImpl.kt#L18-L19) + [A2AChatExecutor.kt](_dev/conversational-ai-platform/modules/product/rovo/rovo-impl/src/main/kotlin/io/atlassian/micros/convoai/product/rovo/chat/service/executors/A2AChatExecutor.kt) | Cutover; shadow parity ≥ 1wk; delete | L | medium | no | `ROVO_NEW_A2A_DEFAULT` | 100% on new; old deleted | parity replay |
| **E2** | JSM PlanGenerator V2 default · `JsmFeatureFlags.JSM_PLANNER_V2_MULTI_STAGE_GENERATION` | Flip; deprecate V1 | M | medium | conditional | `JSM_PLANGEN_V2_DEFAULT` | Win-rate ≥ V1 in shadow | shadow |
| **E3** | Delete v1 410-Gone routes · [ChatV1Controller.kt:76-160](_dev/conversational-ai-platform/modules/service/convo-ai-service/src/main/kotlin/io/atlassian/micros/convoai/rest/v1/ChatV1Controller.kt#L76-L160) | Delete dead handlers | XS | low | no | none | 404; ~85 LoC removed | — |
| **E4** | Streaming metric cardinality · `MetricsServiceImpl` tagging | Drop per-chunk-id tag | S | low | no | none | Series -90% | — |
| **E5** | `logInSplunk=true` default off for streaming · [MetricsServiceImpl.kt:181-229](_dev/conversational-ai-platform/modules/platform/service/service-api/src/main/kotlin/io/atlassian/micros/convoai/platform/service/metrics/MetricsServiceImpl.kt#L181-L229) | Per-call opt-in | S | low | no | none | Splunk volume -30-50% | — |
| **E6** | Split AIFEATURE monolith (37 features → grouped) | Module split | L | medium | no | none | < 10 features per file | — |
| **E7** | Agent storage backend Postgres/DynamoDB ADR | ADR + migration plan only | M | n/a | no | none | ADR merged | leadership |

### Workstream R — Repo-Context / Stalled-Decision Items (NEW in v3)
| ID | Name | Action | Effort |
|---|---|---|---|
| **R1** | **Python Sidecar sunset/keep decision** · [python-sidecar/](_dev/conversational-ai-platform/python-sidecar/) (verified active: FastAPI/Uvicorn, Python 3.11.13, JQL doc routing). Doc flagged "sunset/keep" as open; sidecar appears active and production-ready | Close decision: sunset (timeline + replacement) OR keep (SLA + versioning strategy for stub generation fragility) | S |
| **R2** | **Loom-Author scope clarification** | Verified: only `loom-team` references in `.bitbucket/teams.yml`; no Loom client SDK in convoai. Rovo PR Loom Author work likely lives outside this repo. Cross-reference with Atlas project | S |
| **R3** | **Socrates / StreamHub integration health** · [socrates-vnext/](_dev/conversational-ai-platform/socrates-vnext/) | Verify dbt cadence aligns with backend release; alert on Kinesis → Databricks failures | S |
| **R4** | **Shipyard S3 bucket lifecycle audit** · [shipyard/shipyard-specs/artifact.yml](_dev/conversational-ai-platform/shipyard/shipyard-specs/artifact.yml) | Audit retention policies for 8 buckets (plugin invocations, minion outputs, agent context, history, tool outputs, KG uploads, private skills, index content) | S |
| **R5** | **ERS schema backward-compat CI gate** · [ers/](_dev/conversational-ai-platform/ers/) (60+ schemas) | Add CI gate that verifies schema rollback doesn't break event consumers | M |
| **R6** | **SageMaker Jira similar-issues model versioning** · per `jira_api_tools_agents_report.md` (425-line inventory; 3 ML models, no version pinning) | Add versioning strategy for endpoint rollover | M |
| **R7** | **Spring Actuator endpoint hardening** · `application.yml` does not explicitly allowlist | Verify POCO rules gate `/trace`, `/env`; audit for PII | S |

---

## D. User-facing-behavior preservation policy

**Pattern**: every retrieval/ranking change returns TWO ordered lists from one search call:
- `uiOrdered` — existing order, existing fields, byte-identical to today; bound to UI `sources`/`header`
- `llmOrdered` — reranked / enriched / score-filtered; consumed only inside the LLM context block

**Items requiring explicit user-visible release note** (UF=yes): F2, F3, F4, F5, F6, F7, F9, Q4, Q5, Q11, F1 (scoping change). Each ships behind opt-in flag + cohort A/B (5% → 25% → 100%) + kill-switch + UI snapshot diff = 0 in cohort A.

(Detail per item documented in section C exit criteria.)

---

## E. Sequencing — week-by-week (12 weeks)

```
Wk 1   O1, O2, O3 (infra-blockers)  ·  M1 harness  ·  Q13 dataset start  ·  M3 + M7 instrumentation  ·  T1, T4 (bound channels)  ·  E3 (delete dead routes)
Wk 2   O4, O5, O6  ·  M2 ARIZE judge  ·  Q12 CI scaffold  ·  L1, L8, L16  ·  T2 + T9 (AGG pool + codec, load-tested)  ·  K2 (sidecar prompt cache enable)  ·  C2 classifier debounce  ·  R7 actuator hardening
Wk 3   Q11 Slack date filter (XS bug-fix)  ·  Q1 dev  ·  L2, L13, L19  ·  T5 (heap + ZGC)  ·  C1 dev  ·  F1 personality-scope dev  ·  K1 audit cache_control
Wk 4   Q1 ship 5%→25%  ·  Q4 dev  ·  L4 dev, L7 codec confirmed live, L20 (XS)  ·  T3 (HTTP/2)  ·  T7 default pool sizing  ·  C1 ship 5%, C6  ·  F1 ship 5%→100%  ·  R1 sidecar decision
Wk 5   Q1 100%, Q3, Q2 dev  ·  L4 ship 5%→25%, L17 cache  ·  T8 AppCDS dev  ·  C1 25%, C8 dev  ·  K3 dev  ·  F2 starter-prompts dev  ·  E1 parity test build
Wk 6   Q2 ship 5%, Q12 CI gate enforced  ·  L17 100%, L15 MCP session, L11 chunk-accumulator bound  ·  T11+T12 pool tune (gated by M7 dashboards)  ·  C1 100%, C3 citation A/B  ·  K4 in-flight singleflight  ·  F2 ship 5%, F4 dev  ·  E1 cutover 5%
Wk 7   Q2 100%, Q6 dev  ·  L21 history-delta dev, L18 .blockingGet removal  ·  C4 Lumina A/B, C9 dev  ·  K5 edge cache headers  ·  F4 last-conv-resume ship 5%, F8 recent-activity-ctx  ·  E1 25%
Wk 8   Q6 ship, Q7 dev  ·  L21 ship, L18 ship  ·  C9 ship, C5 cache prompt V1  ·  K6 Redis wire incremental  ·  F3 adaptive follow-up dev, F5 citation hover dev  ·  E1 100% (delete A2AChatExecutor: -1,370 LoC)
Wk 9   Q7 ship, Q8/Q9/Q10 dev  ·  L31 compaction guard, L32 realtime async  ·  C7 batch API offline  ·  K7 embedding-sim cache, K8 JSON-repair  ·  F5 ship, F9 stale-source-warn  ·  E2 PlanGen V2 shadow  ·  R3, R4
Wk 10  Q8/Q9/Q10 ship  ·  L9 N+1 hydration batch, L10 Kamino parallel publish, L12 redis discipline  ·  C5 100%  ·  F3 ship, F10 feedback→ARIZE  ·  E2 100% if shadow wins  ·  R6 SageMaker versioning
Wk 11  **Q5 page-search opt-in flip A/B**  ·  L3 AI_EDITOR non-blocking 5%→25%  ·  T13 QPS targets defined in TOME, T14 DNS TTL  ·  F6 confidence badges, F7 graceful error UX, F11 base-prompt-dynamic  ·  E6 AIFEATURE split  ·  R5 ERS CI gate
Wk 12  Q5 100%, final eval lockdown  ·  L3 100%, L14 GraphQL pagination  ·  E7 storage ADR  ·  R2 Loom scope
```

**Critical paths**:
- **Beta GA**: O1+O5 → M1+M2 → Q1 → Q2 → Q4 → Q12 enforced → Q5 flip → final lockdown.
- **150k MAU readiness**: M3+M7 → L1+L8 → T1+T2+T5 → L4 → L17 → L21 → L3 + F2+F4.
- **Cost realization**: M4 (leverage Socrates) → C1+C2 → C3+C4+C8 → K1+K2+K3 → C7+C9.

---

## F. Risk register (Top 6 — added a 6th in v3)

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| 1 | C1 compaction persist corruption causes wrong-context replies | M | H | Versioned schema + checksum + fall-back recompute on mismatch; 5% canary 1 wk |
| 2 | Q1/Q2 LLM rerank surfaces lower-quality content | L | H | Eval gate (Q12) blocks promotion if factual <baseline; kill-switch |
| 3 | L3/L23 reactive conversion races / leaked subscriptions | M | H | 24h soak; thread-leak detector; bounded scheduler; staged rollout |
| 4 | E1 A2AChatExecutor cutover regression (1,370 LoC) | M | H | Shadow-replay parity ≥ 10k turns; auto-rollback on parity divergence (relies on O1) |
| 5 | C3/C4 model-downsizing degrades quality | M | M | Paired-prompt A/B; rollback if Δquality < -2pp |
| 6 | **NEW: T-series throughput tuning over-provisions and starves another pool** | M | M | Land M7 saturation panel BEFORE T11/T12; gated rollout; per-pool eviction metric; Resilience4j bulkheads (O2) |

---

## G. Findings → plan map (completeness check, all 80+ accounted for)

Wave 1+2 (50 findings): **Q1-Q14, L1-L32, C1-C9, E1-E7** — all in C above (cross-reference v2).
Wave 3 (~30 new findings):
| Wave-3 finding | Item |
|---|---|
| Auto-rollback ABSENT | O1 |
| Circuit breakers ABSENT | O2 |
| Graceful shutdown PARTIAL | O3 |
| Tenant canary missing | O4 |
| Batch eval not scheduled | O5 |
| Per-tenant SLO missing | O6 |
| `Channel.UNLIMITED` streaming writer | T1 |
| AsyncAgentInMemoryQueue unbounded | T4 |
| AGG WebClient pool 4×, no eviction, 24MB codec | T2 + T9 |
| Default WebClient pool too small | T7 |
| HTTP/2 not enabled on AGG | T3 |
| JVM heap 5Gi/G1 | T5 |
| Pod cold start AppCDS | T8 |
| Per-pool dispatcher saturation no dashboard | T10, M7 |
| `streamingWriterPool=1024` over-provisioned (INFERRED) | T11 (gated on M7) |
| `MAX_IO_PARALLELISM=3072` over-provisioned (INFERRED) | T12 (gated on M7) |
| No QPS targets in TOME | T13 |
| DNS TTL default | T14 |
| Personality experiment leaks to SAIN | F1 |
| No starter prompts | F2 |
| Adaptive follow-up count missing | F3 |
| Last-conversation resume missing | F4 |
| Citation hover preview missing | F5 |
| Confidence scoring missing | F6 |
| Graceful error UX missing | F7 |
| Recent-activity context missing | F8 |
| Stale-source warning missing | F9 |
| Feedback → ARIZE not wired | F10 |
| Hardcoded prompt template | F11 |
| Anthropic prompt-cache adoption uneven | K1 |
| Python sidecar prompt cache disabled | K2 |
| Tool-result coalescing missing | K3 |
| In-flight singleflight missing | K4 |
| Edge cache headers missing | K5 |
| RedisCacheClient unused (INFERRED) | K6 (verify before relying on $) |
| Embedding similarity cache missing | K7 |
| Malformed-LLM-response repair missing | K8 |
| Python sidecar sunset/keep decision | R1 |
| Loom Author scope unclear | R2 |
| Socrates pipeline alignment | R3 |
| Shipyard bucket lifecycle | R4 |
| ERS schema CI gate | R5 |
| SageMaker model versioning | R6 |
| Spring Actuator allowlist | R7 |

**Total: 80+ findings, all mapped, none dropped.**

---

## H. Anti-goals — what NOT to do

1. Do **not** rewrite UI source-list ordering. All ranking changes are LLM-context-only unless explicitly opted in via Q5.
2. Do **not** disable PageSearch globally. Q5 flip happens only after Q1+Q2+Q3+Q4 prove ≥ +10pp factual.
3. Do **not** chase 99.9% SLO past 99.85% without multi-provider failover (out of scope; mark dependency).
4. Do **not** unify Postgres/DynamoDB agent storage in this 12-wk horizon (E7 = ADR only).
5. Do **not** remove `lastModified` UI ordering — documented user contract.
6. Do **not** ship cost reductions without paired quality A/B (M5).
7. Do **not** combine flags. Each item has its own flag for clean attribution.
8. Do **not** cache TCS without a tenant-update invalidation hook OR explicit security review of 60s eventual consistency.
9. Do **not** LLM-rerank in the hot path before Q2 ships.
10. Do **not** bundle TTFB and quality changes in one PR.
11. Do **not** raise `first` above 50 to compensate for low recall.
12. Do **not** ship E1 cutover until shadow-replay parity is green for 1 full week.
13. **NEW: Do not tune `streamingWriterPool` (T11) or `MAX_IO_PARALLELISM` (T12) without the per-pool saturation dashboard (M7+T10) live for ≥ 7 days first.** The pool sizes are intentionally isolated to prevent starvation; "over-provisioned" is INFERRED, not measured.
14. **NEW: Do not enable T2 AGG pool 8× without a load-test plan**. Larger pool = more downstream pressure on AGG. Coordinate with AGG team.
15. **NEW: Do not roll out F-series UF features without `O3` graceful shutdown landed** — partial-streamed answer preservation requires it.
16. **NEW: Do not assume K2 ($ savings from sidecar prompt-cache) is multi-hundred-$k**. The Python sidecar serves Marathon-research path, not main chat; the cost agent's $400-600k/month estimate is OVER-SCOPED to the broader codebase. Re-scope after M4 token attribution.

---

## I. End-state acceptance criteria (per goal)

| Goal | Criterion |
|---|---|
| AIFC FactualConsistency 70 | Nightly LLM-judge ≥ 70% on 300-row golden set, 7-day rolling, page-search ON cohort |
| AIFC ContextualRecall 65 | Nightly recall ≥ 65%, 7-day rolling |
| AIFC Relevancy 70 | Nightly relevancy ≥ 70%, 7-day rolling |
| ChatSLO 99.9 | 28-day rolling success ≥ 99.85%; ≥ 99.9% needs multi-provider failover (out of scope) |
| RovoMAU 150k | (Product metric, not eng-attributable directly) — TTFB p50 -25%; activation lift +X%; F-series uplift on cohort A/B |
| **Throughput** at 150k MAU peak | Sustained ≥ 2,900 req/s for 5 min on staging load test; pool exhaustion alerts -90% in prod |
| CSM/JSM TTFB | CSM TTFB p50 -30%; JSM HR avg-steps ≤ 2.5 |
| Cost $/turn | -$215-375k/mo realized in M4 finance attribution (vs $110-170k/mo in v2) |
| EngVelocity LoC removed | A2AChatExecutor + v1 410 routes deleted; AIFEATURE split |
| **Operational readiness** | O1-O6 all in production; chaos drill validates auto-rollback within 5 min |

**Beta GA gate**: Q1+Q2+Q3+Q4+Q5+Q12 shipped; factual consistency ≥ 70% on golden 14 consecutive days; CI gate blocking on main 3 weeks; 1 chaos-drill rollback validated (relies on O1).

**150k MAU readiness gate**: L1+L4+L8+L17+L21+L3 + T1+T2+T5+T7 shipped; p50 TTFB -25% in prod; staging load-test 2,900 req/s sustained 5 min; chat send-message SLO ≥ 99.85%.

---

## J. Verification plan

| Item class | How proven |
|---|---|
| Q1-Q11 | Nightly eval (M1) shows per-flag-cohort delta ≥ claimed pp; 7-day soak |
| Q12-Q14 | Q12: PR pipeline blocks a synthetic regression. Q13: dataset PR landed. Q14: ARIZE shows per-turn factual score |
| L-series | M3 spans show p50 delta ≥ claimed in 25% cohort over 48h; promote at ≥ 80% of claim |
| **T-series** | **M7 saturation panel ≥ 7 days steady before tuning**; staging load test 2× peak rate; per-pool utilization at peak < 80%; no FD exhaustion |
| C-series | M4 (Socrates `convo_ai_usage` data product) per-feature attribution shows ≥ 80% of claimed $/mo over 14 days |
| **K-series** | M6 cache hit-rate dashboards; K1: ARIZE prompt-cache-hit ≥ 70%; K2: sidecar token-cost panel; K6: per-pattern hit-rate ≥ 30% |
| **F-series** | Cohort A/B with primary metric (first-message rate / Day-1 return / CTR / etc.); UF=yes items have UI snapshot diff = 0 in cohort A and release notes merged |
| E-series | E1 deletes ≥ 1,300 LoC + parity replay green; E3 returns 404 |
| **O-series** | O1: chaos drill auto-flips a test flag in ≤ 5 min. O2: fault-injection shows no cascade. O3: rolling deploy preserves in-flight streams (verified in canary) |
| UF preservation (Q-conditional, F-yes) | UI snapshot diff = 0 in cohort A; release note merged in cohort B; manual UI smoke pass |

---

## K. What changed in v3 (vs v2)

1. **Throughput axis added** (T1-T14, M7). v2 had no throughput coverage despite docs explicitly noting "no QPS targets". Closes a 1,400 req/s estimated gap at 150k MAU peak.
2. **Operational infra-blockers (O1-O6) elevated to Phase 0**. Audit found auto-rollback ABSENT, circuit breakers ABSENT, graceful shutdown PARTIAL — without these, v2's 30+ flag rollouts had no MTTR backstop.
3. **Caching/coalescing workstream split out as K-series** (K1-K8). Surfaces $40-80k/mo of additional cost wins (Anthropic prompt cache audit, RedisCacheClient wiring, edge cache headers, JSON-repair, embedding similarity cache).
4. **Feature enhancements (F1-F11) added** as direct activation/MAU levers — F2 starter prompts, F3 adaptive follow-ups, F4 last-conversation resume, F5 citation hover preview, F1 personality-scope-fix (active in-flight feature, doc-confirmed leak).
5. **Repo-context items (R1-R7)** capture stalled decisions (Python sidecar sunset/keep, Loom scope, Socrates alignment, ERS CI gate, SageMaker versioning, Spring Actuator hardening).
6. **Cost ceiling raised**: $110-170k/mo (v2) → **$215-375k/mo** (v3) once K-series and C-series compound.
7. **Honest re-scoping**: K2 (Python sidecar prompt cache) noted as sidecar-only — the previous agent's $400-600k/mo claim was over-scoped to "all of convoai".
8. **Critical Anti-goals added** (#13-#16): T-pool tuning gated on M7 dashboards; T2 AGG pool needs load-test; F-series UF features need O3; K2 $ over-scoped.
9. **Anti-double-counting**: T6 = O2 (circuit breakers); T9 = T2 (codec raise) — listed twice for traceability but counted once for effort/risk.

---

## L. Limitations & honest caveats

1. Quantitative impact estimates are claims pending production validation. M1-M7 are the load-bearing instruments. **No item ships claiming impact until its M-series instrument is live.**
2. AIFC pp-recovery is cumulative-additive *only on the golden eval*; production deltas may differ in magnitude but not direction.
3. Cost numbers assume model pricing as of investigation date and SAIN volume mix.
4. **K2 ($/mo from prompt-caching enable) is sidecar-only** — main chat path uses a different prompt-cache mechanism (`CacheFriendlyPromptAssembler`) that K1 audits. Do not double-count.
5. **K6 ("RedisCacheClient unused")** is INFERRED from the audit agent's grep; verify with a careful grep before committing $ savings.
6. **T11/T12 ("pool over-provisioned")** are INFERRED. The dispatcher pools are intentionally isolated to prevent starvation per the explicit comment in [CoroutineContextProvider.kt:32](_dev/conversational-ai-platform/modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/threading/CoroutineContextProvider.kt#L32) ("TODO: Tune the parallelism based on metrics"). Land M7 dashboard ≥ 7 days before tuning.
7. **The `assistance-service` is a separate microservice** — some Rovo Chat orchestration is out-of-process. Mirror priorities (TCS caching, prompt caching audit, dual-list rerank, throughput tuning) should also be applied there.
8. **Synthetic monitoring exists** via `operations/pollinator/checks/{prod,staging}.yml` (5-15min interval) — leverage rather than rebuild for parts of M-series.
9. **Auto-rollback (O1) is the single biggest open dependency** — every flagged rollout in this plan assumes it exists, but the audit confirmed it does not. If O1 slips, the plan must use manual oversight which doubles the team's coordination cost.
10. **Loom Author work likely lives in another repo** — exclude from convoai scope; close R2 by cross-referencing the Atlas project.
