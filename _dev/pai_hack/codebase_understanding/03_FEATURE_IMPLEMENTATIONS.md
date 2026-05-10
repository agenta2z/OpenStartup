# 03 — Feature Implementations: Business Logic Layer

> **Scope**: Deep documentation of all feature implementations in the Proactive AI Platform (PAI).
> Covers three major feature areas: Rovo Insights, Nudge Throttle, and Stratus/AI Gateway integration.
>
> **Source**: `io.atlassian.micros.proactiveai.feature.*` + `io.atlassian.micros.proactiveai.stratus.*`
> **Total**: 29 production files (~1,400+ LoC) + 5 test files (~700 LoC)

---

## Table of Contents

1. [Rovo Insights — Async Insight Generation Pipeline](#1-rovo-insights)
2. [Nudge Feature — Throttle Decision Plane](#2-nudge-feature)
3. [Stratus / AI Gateway Integration](#3-stratus--ai-gateway-integration)
4. [Cross-Feature Integration Patterns](#4-cross-feature-integration-patterns)
5. [Summary of Test Coverage](#5-summary-of-test-coverage)
6. [Appendix: Complete File Inventory](#6-appendix-complete-file-inventory)

---

## 1. Rovo Insights — Async Insight Generation Pipeline

**Package**: `io.atlassian.micros.proactiveai.feature.rovoinsights`
**Files**: 16 production files (~658 LoC) + 3 test files (~327 LoC)
**Criticality**: P0 (async insight generation backbone) / P1 (API layer)
**Queue**: `rovo_insights_generation_queue` (consumed by LongRun worker group)

### 1.1 Architecture Overview

Rovo Insights is the flagship feature of PAI. It generates AI-powered insights for users by analyzing their work context across Atlassian products. The architecture follows a three-layer design:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: REST API                                                  │
│  ┌─────────────────────────┐  ┌──────────────────────────────────┐  │
│  │ RovoInsightsController  │  │ RovoInsightsTestController       │  │
│  │ /api/v1/rovo/insights/* │  │ /api/v1/rovo-insights/generate   │  │
│  │ (production - STUB)     │  │ (testing - submits real tasks)   │  │
│  └──────────┬──────────────┘  └──────────────┬───────────────────┘  │
├─────────────┼────────────────────────────────┼──────────────────────┤
│  Layer 2: Async Task Pipeline                │                      │
│             │                 ┌──────────────▼───────────────────┐  │
│             │                 │ AsyncTaskService.submit()        │  │
│             │                 │ → RovoInsightsGenerationTask     │  │
│             │                 │ → SQS enqueue                   │  │
│             │                 └──────────────┬───────────────────┘  │
├─────────────┼────────────────────────────────┼──────────────────────┤
│  Layer 3: SQS Consumer (LongRun pods)        │                      │
│             │                 ┌──────────────▼───────────────────┐  │
│             │                 │ RovoInsightsGenerationSqs-       │  │
│             │                 │   QueueConsumer → dispatch       │  │
│             │                 └──────────────┬───────────────────┘  │
│             │                 ┌──────────────▼───────────────────┐  │
│             │                 │ RovoInsightsGenerationTaskHandler│  │
│             │                 │ → AI Gateway call (STUB today)  │  │
│             │                 └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Current state**: Production controllers return hardcoded stubs. Only the test controller submits real tasks to SQS. The generation handler logs context but does not yet make LLM calls or persist results.

### 1.2 System Domain Models

All system models live under `system/` and define the vocabulary for insight categorization and UI rendering.

#### 1.2.1 InsightType Enum

**File**: `system/InsightType.kt` (52 lines) — Six business-meaningful insight categories:

| Enum Variant | JSON Value | Icon (Glyph) | Color | Group Title |
|-------------|-----------|-------------|-------|-------------|
| `FOLLOW_UP_INSIGHTS` | `follow-up-insights` | `TARGET` | `YELLOW` | "Waiting on you" |
| `EMERGING_WITH_YOUR_TEAM` | `emerging-with-your-team` | `CHART_TREND_UP` | `MAGENTA` | "What your team's into" |
| `COMPANY_INSIGHTS` | `company-insights` | `MEGAPHONE` | `BLUE` | "Across the company" |
| `YOUR_TRENDING_WORK` | `your-trending-work` | `EYE_OPEN` | `TEAL` | "Your work is travelling" |
| `RECOGNITION_INSIGHTS` | `recognition-insights` | `GOAL` | `MAGENTA` | "Worth celebrating" |
| `MEETING_INSIGHTS` | `meeting-insights` | `CALENDAR` | `ORANGE` | "Important meetings" |

Each variant has four properties: `value` (kebab-case via `@JsonValue`), `icon`, `color`, `groupTitle`.

#### 1.2.2 Color Enum

**File**: `system/Color.kt` (34 lines) — 20-value enum mapping Atlassian Design System color tokens. 10 base colors (`GRAY`, `BLUE`, `TEAL`, `GREEN`, `LIME`, `YELLOW`, `ORANGE`, `RED`, `MAGENTA`, `PURPLE`) plus 10 bold variants (`GRAY_BOLD` → `grayBold`, etc.). Each uses `@JsonValue` on a camelCase string.

#### 1.2.3 Glyph Enum

**File**: `system/Glyph.kt` (49 lines) — 35-value enum mapping icon identifiers. Includes: `ALERT`, `AUTOMATION`, `BOOK_WITH_BOOKMARK`, `BRIEFCASE`, `CALENDAR`, `CHART_BAR`, `CHART_TREND`, `CHART_TREND_UP`, `CHECK_CIRCLE`, `CLOCK`, `COMMENT`, `COMPASS`, `DASHBOARD`, `DEPARTMENT`, `EYE_OPEN`, `FLAG`, `GLOBE`, `GOAL`, `LIGHTBULB`, `LINK`, `MEGAPHONE`, `OFFICE_BUILDING`, `PEOPLE_GROUP`, `PERSON`, `PRIORITY_HIGH`, `QUESTION_CIRCLE`, `SPRINT`, `STAR_STARRED`, `STATUS_WARNING`, `STOPWATCH`, `TARGET`, `TASK`, `TEAMS`, `THUMBS_UP`, `WARNING`. Each maps to kebab-case via `@JsonValue`.

#### 1.2.4 RovoInsightsRequest & PromptConfig

**File**: `system/RovoInsightsRequest.kt` (31 lines)

- **`Strategy` enum** — `EVALUATE` (run full LLM evaluation) and `SKIP` (bypass). Both serialize via `@JsonValue`.
- **`RovoInsightsPromptConfig`** — `version: String` (default `"v1"`), `strategy: Strategy` (default `EVALUATE`), `maxAttempts: Int` (default `3`), `override: String?`.
- **`PromptConfig` type alias** — `Map<InsightType, RovoInsightsPromptConfig>`.

### 1.3 REST API Layer

#### 1.3.1 RovoInsightsController (Production)

**File**: `api/RovoInsightsController.kt` (50 lines) — Base Path: `/api/v1/rovo/insights`

| Endpoint | Method | Request DTO | Response DTO | Current Behavior |
|----------|--------|-------------|--------------|-----------------|
| `/status` | POST | `RovoInsightsStatusRequest` | `RovoInsightsStatusResponse` | Always `insightsAvailable = true` (stub) |
| `/fetch` | POST | `RovoInsightsFetchRequest` | `RovoInsightsFetchResponse` | `count=0`, empty `insightGroups`, `schemaVersion=3` (stub) |

#### 1.3.2 RovoInsightsTestController (Testing)

**File**: `api/rest/RovoInsightsTestController.kt` (82 lines) — Base Path: `/api/v1/rovo-insights`
**Activation**: `@ConditionalOnProperty("proactive-ai.test-controllers-enabled")`

| Endpoint | Method | Response | Behavior |
|----------|--------|----------|---------|
| `/generate` | POST | `RovoInsightsTestResponse` (202) | Submits `RovoInsightsGenerationTask` to SQS; returns `taskId` |

Required headers: `atl-cloudid` (required), `X-Request-Id` (optional → UUID). The controller is `suspend fun`, builds `AsyncTaskExecutionContext`, submits via `AsyncTaskService.submit()`.

#### 1.3.3 Request/Response DTOs

**RovoInsightsFetchRequest** (14 lines): `generate: Boolean`, `debugInfo: Boolean`, `promptConfig: PromptConfig`

**RovoInsightsFetchResponse** (77 lines):

| Field | Type | Description |
|-------|------|-------------|
| `schemaVersion` | `Int` | Currently `3` (`DATA_SCHEMA_VERSION`); incremented on breaking changes |
| `generatedAt` | `Instant` | Timestamp of generation |
| `count` | `Int` | Total insight count |
| `summary` | `String` | Human-readable summary |
| `insightGroups` | `List<RovoInsightsGroup>` | Grouped by InsightType |

**RovoInsightsGroup**: `type`, `title`, `icon`, `color`, `count`, `insights: List<RovoInsight>`, `debugInfo: DebugInfo?` (`@JsonInclude(NON_NULL)`)

**RovoInsight**: `title`, `overview`, `people: List<PersonReference>?` (name/aaid/avatarUrl), `urls: List<String>?`, `thinking` (LLM reasoning), `followUps: List<String>?`, `detailsAdf` (ADF markup)

**DebugInfo**: `generatedAt`, `prompt`, `llmResponse`, `error`, `durationSecs`, `attempts`

**Status**: Request — `promptConfig`, `forceCacheMiss: Boolean`; Response — `insightsAvailable: Boolean`

**Test**: Request — empty class; Response — `taskId: String`

### 1.4 Generation Pipeline (Async)

#### 1.4.1 RovoInsightsGenerationTask

**File**: `RovoInsightsGenerationTask.kt` (9 lines) — `@JsonTypeName("rovo_insights_generation") data class RovoInsightsGenerationTask(val cloudId: String) : AsyncTask`

The `"rovo_insights_generation"` discriminator enables `AsyncTaskDispatcher` routing. Minimal payload — only `cloudId`; user context travels in `AsyncTaskExecutionContext`.

#### 1.4.2 RovoInsightsGenerationTaskHandler

**File**: `RovoInsightsGenerationTaskHandler.kt` (62 lines) — `type = RovoInsightsGenerationTask::class.java`, `queueName = ROVO_INSIGHTS_GENERATION_QUEUE`

- **`handle(ctx, task)`** — **STUB**: logs tenant_id/account_id/request_id. No AI Gateway calls.
- **`onSuccess(ctx, task)`** — Logs completion for Splunk correlation.
- **`onFailure(ctx, task, error)`** — Logs via `errorWithContext`. Does not throw (lets dispatcher rethrow original).

**Planned**: `AIGatewayService.buildAgent()` → run with prompts from `Config.kt` → parse → persist to Redis.

#### 1.4.3 RovoInsightsGenerationSqsQueueConsumer

**File**: `internal/RovoInsightsGenerationSqsQueueConsumer.kt` (122 lines) — Extends `VisibilityExtendingSQSQueueConsumer<JsonNode>`

**Activation** (AND): `OnLongRunWorkerNodeOrLocalCondition` + `@ConditionalOnProperty("SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL")`

**Dependencies** (7): `messageQueueConsumerMiddleware`, `asyncTaskDispatcher`, `objectMapper`, `userContextService`, `loggingContext`, `sqsClient`, `taskScheduler`

**Processing flow (critical ordering invariant):**

```
SQS Message (JsonNode)
  ├─ 1. Deserialize → AsyncTaskMessage (wire + task envelope)
  ├─ 2. Enter middleware.consume() — request-scope lifecycle
  ├─ 3. Populate MDC FIRST (tenant_id/request_id/account_id)
  │      ⚠️ MUST precede step 4 so failures are observable
  ├─ 4. Validate UCT: wire.toContext(userContextService)
  └─ 5. Dispatch: asyncTaskDispatcher.dispatch(ctx, task)
         Failures rethrown → SQS retries until DLQ
```

**Key invariant**: MDC populated _before_ UCT validation. Tested via `verifyOrder` in `RovoInsightsGenerationSqsQueueConsumerTest`.

### 1.5 Configuration

**File**: `Config.kt` (45 lines) — `DEFAULT_ROVO_INSIGHTS_PROMPT_VERSION = "v1"`. All 6 insight types share identical config: version `"v1"`, strategy `EVALUATE`, max 3 attempts, no override.

### 1.6 Test Coverage

**RovoInsightsGenerationSqsQueueConsumerTest** (201 lines, MockK):

| Test | Validates |
|------|-----------|
| MDC before UCT validation | Ordering invariant via `verifyOrder` |
| Successful dispatch | Wire fields propagated to context |
| Dispatcher failure rethrown | SQS retry; MDC still populated |
| Middleware delegation | All work inside `consume()` |

**RovoInsightsGenerationTaskHandlerTest** (65 lines): handler type routing, stub completion, `onFailure` safety, Jackson `@type` round-trip.

**RovoInsightsControllerIT** (61 lines): `/status` and `/fetch` return 200 OK via Apache HttpClient.

### 1.7 Known Issues & Gaps

| Gap | Impact |
|-----|--------|
| Production controller stubs | No real insight data |
| Handler doesn't invoke AI Gateway | Pipeline ends at logging |
| No result persistence | No Redis/cache integration |
| No controller unit tests | Production endpoints untested directly |
| Test controller feature-gate untested | Could be accidentally exposed |
| No `DATA_SCHEMA_VERSION` contract test | Version bump could break frontend |

---

## 2. Nudge Feature — Throttle Decision Plane

**Package**: `io.atlassian.micros.proactiveai.feature.nudge`
**Files**: 4 production files (~72 LoC) + 1 test file (~158 LoC)
**Criticality**: P1 — synchronous nudge throttling
**Latency Target**: <50 ms p95

### 2.1 Architecture Overview

Provides a **throttle decision plane** for proactive nudges. Product surfaces call this service before rendering; PAI returns a priority score and suppress/allow decision. **Synchronous** — no SQS/async.

```
POST /api/v1/nudge/throttle
  Body: { "nudge_type": "CONVO_STARTER" }
  Headers: atl-cloudid, X-Slauth-User-Context-Account-Id
  → NudgeThrottleController → NudgeThrottleResponse(score=10, throttled=false)
```

### 2.2 Domain Model — NudgeType

**File**: `api/domain/NudgeType.kt` (14 lines) — Closed enum of 10 nudge categories:

| Variant | Surface |
|---------|---------|
| `CONVO_STARTER` | Rovo conversation starters |
| `JIRA_JQL_EXECUTED` | JQL execution nudges |
| `JIRA_SIMILAR_WORK_ITEMS` | Similar work items |
| `JIRA_STATUS_UPDATER` | Status update reminders |
| `JIRA_VERSION_CHANGE` | Version change notifications |
| `JIRA_WORK_READINESS` | Work readiness checks |
| `NUDGE_LIMITER` | Meta-type for throttle subsystem |
| `PAGE_CATCHUP` | Confluence catch-up |
| `PAGE_SUMMARIES` | Page summaries |
| `AUDIO_BRIEFING` | Audio briefing |

Closed enum → unknown values cause 400 Bad Request → forces registration before use.

### 2.3 Request / Response DTOs

- **NudgeThrottleRequest** (9 lines): `nudgeType: NudgeType` via `@param:JsonProperty("nudge_type")`
- **NudgeThrottleResponse** (10 lines): `score: Int` (hardcoded `10`), `throttled: Boolean` (hardcoded `false`) via `@field:JsonProperty`

### 2.4 REST Controller

**File**: `api/rest/NudgeThrottleController.kt` (39 lines)

| Property | Value |
|----------|-------|
| **Endpoint** | `POST /api/v1/nudge/throttle` |
| **Auth** | SLAuth — `atl-cloudid` + `X-Slauth-User-Context-Account-Id` required |
| **Response** | `{ "score": 10, "throttled": false }` (hardcoded) |

Logs via `LaasLoggerFactory.infoWithContext()` with `cloud_id` and `nudge_type`.

### 2.5 Design Decisions

1. **Synchronous** — SQS latency (200-500ms) exceeds 50ms target
2. **Closed enum** — Forces registration of new nudge types
3. **Upstream data pre-ingested** — GASv3 signals via SQS StreamHub consumer
4. **Stub-first** — Ship contract early, backfill logic later

### 2.6 Test Coverage

**NudgeThrottleControllerAcceptanceTest** (158 lines, `@SpringBootTest` RANDOM_PORT):

| Test | Type | Validates |
|------|------|-----------|
| All headers present | Positive | 200 + correct body |
| All enum variants | Parameterized (`@EnumSource`) | All 10 types accepted |
| Missing headers | Negative | 400 Bad Request |
| Not authenticated | Negative | 401 Unauthorized |

### 2.7 Future Architecture

Planned integrations: **TAP** (cohort weights), **GASv3/StreamHub** (engagement signals), **Redis/Valkey** (caching + TTL).

### 2.8 Production-Readiness Gaps

| Gap | Status |
|-----|--------|
| Throttle logic hardcoded | No TAP/GASv3 integration |
| No metrics emission | No SignalFx series |
| No SLO registration | <50 ms p95 aspirational |

---

## 3. Stratus / AI Gateway Integration

**Package**: `io.atlassian.micros.proactiveai.stratus`
**Files**: 8 production files (~587 LoC) + 1 test file (~142 LoC)
**Criticality**: P0 — LLM agent execution infrastructure
**Default Model**: `gemini-2.5-pro`

### 3.1 Architecture Overview

Integrates PAI with Atlassian's AI Gateway via the Stratus SDK. Provides infrastructure for building and executing LLM-powered agents with tool-use capabilities, connecting to the Integration Service MCP server for cross-product tool access.

```
┌────────────────────────────────────────────────────────────────────┐
│  Controller / Handler                                              │
│       ▼                                                            │
│  AIGatewayService.buildAgent(cloudId, user, useCaseId)             │
│       │  • UnifiedLlmProvider with per-request headers             │
│       │  • Toolset via IntegrationServiceToolProvider               │
│       ▼                                                            │
│  AIGatewayService.runAgent(agent, userId, message)                 │
│       │  • StratusRunner (app: "proactive-ai")                     │
│       │  • Returns Flowable<Event> for streaming                   │
│       ▼                                                            │
│  ┌──────────────────┐    ┌─────────────────────────────┐           │
│  │  AI Gateway      │    │  Integration Service (MCP)  │           │
│  │  gemini-2.5-pro  │    │  Jira, Confluence tools     │           │
│  └──────────────────┘    └─────────────────────────────┘           │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 AI Gateway Client Configuration

**File**: `AIGatewayClientConfiguration.kt` (66 lines) — `@Configuration` providing singleton beans:

- **`asyncUnifiedClient`** — `Unified` async client. Base URL from `${ai-gateway.target-url}`. Default headers: `X-Slauth-Audience: ai-gateway`, `X-Slauth-Egress: true`.
- **`observabilityContext`** — `AnalyticsClient` + `MeterRegistry` with namespace `"proactive-ai"`.

### 3.3 AIGatewayService Interface & Implementation

**Interface** (`AIGatewayService.kt`, 67 lines):

- `buildAgent(cloudId, user, useCaseId, name, description, instruction, tools, model)` → `BaseAgent`
- `runAgent(agent, userId, userMessage, streamingMode)` → `Flowable<Event>`
- `DEFAULT_MODEL = "gemini-2.5-pro"`

**Implementation** (`internal/AIGatewayServiceImpl.kt`, 120 lines) — `@Service`:

- `APP_NAME = "proactive-ai"`
- **`buildAgent()`** — Creates per-request `UnifiedLlmProvider` with AI Gateway headers (`CLOUD_ID`, `USER_ID`, `USE_CASE_ID`, `USER_CONTEXT`). Builds `LlmAgent` via Google ADK builder.
- **`runAgent()`** — New `StratusRunner` per invocation → session → `RunConfig` (SSE) → `Flowable<Event>`
- **`buildUnifiedLlmProvider()`** — Attaches headers via `requestWrapperCustomizer`
- **`buildRunner()`** — `StratusRunner.from(Runner.builder())` with observability

### 3.4 MCP Integration (Model Context Protocol)

#### 3.4.1 IntegrationServiceMcpServerConfig

**File**: `IntegrationServiceMcpServerConfig.kt` (14 lines) — `@ConfigurationProperties("integrations-service")`: `url`, `endpoint`, `timeout: Duration` (`@DurationUnit(SECONDS)`)

#### 3.4.2 IntegrationServiceMcpSessionManager

**File**: `IntegrationServiceMcpSessionManager.kt` (54 lines) — Per-request (constructed with `cloudId` + `user`). Only async sessions (`createSession()` throws `UnsupportedOperationException`).

Headers per-request: `X-Slauth-Egress: true`, `X-Slauth-Audience: integrations-service`, `atl-cloudid`, `User-Context` (UCT), `Atl-Surface` (Stratus SDK).

**Security**: UCT scopes MCP tool invocations to user's permissions.

#### 3.4.3 IntegrationServiceToolProvider

**File**: `IntegrationServiceToolProvider.kt` (54 lines) — `@Component`:

`getTools(cloudId, user, actionIds?)` → `List<BaseTool>`: Creates session manager → `McpAsyncToolset` with optional `Filters.byActionIds()` → blocks for tool list. `null` actionIds → all entitled tools per `poco` policy.

**MCP data flow:**

```
StratusTestController.insights()
  → IntegrationServiceToolProvider.getTools(cloudId, user)
    → new IntegrationServiceMcpSessionManager
    → McpAsyncToolset → toolset.getTools().blockingGet()
  → List<BaseTool>
  → AIGatewayService.buildAgent(tools = mcpTools)
  → AIGatewayService.runAgent() → AgentResponse
```

### 3.5 StratusTestController

**File**: `StratusTestController.kt` (187 lines) — `/stratus/test`

**POST `/chat`** — Builds agent with `WeatherTool`, runs with user message, collects model text → `AgentResponse(agentName, response, eventCount)`. Verifies basic LLM + local tool pipeline.

**POST `/insights`** — Loads MCP tools via `IntegrationServiceToolProvider.getTools()`, builds `"insights-agent"` wired to Integration Service, same event collection. Verifies full MCP pipeline.

DTOs: `AgentRequest(message: String)`, `AgentResponse(agentName, response, eventCount)`.

### 3.6 WeatherTool

**File**: `WeatherTool.kt` (25 lines) — `object` with `@Annotations.Schema`. `getWeather(city)` returns hardcoded `{city, "22C", "Sunny"}`. Verification tool; replaced by MCP tools in production.

### 3.7 Observability

Stratus SDK metrics via `ObservabilityContext`:

| Metric | Type | Tags |
|--------|------|------|
| `proactive-ai.stratus.invocation.count` | Counter | useCaseId, model, result |
| `proactive-ai.stratus.invocation.timing.histogram` | Histogram | useCaseId, model |
| `proactive-ai.stratus.tokens.summary` | Summary | direction |

### 3.8 Test Coverage

**AIGatewayServiceImplTest** (142 lines, MockK, `@Nested`):

| Group | Tests | Validates |
|-------|-------|-----------|
| `BuildAgent` | 4 | Name/description, with/without tools, custom/default model |
| `Constants` | 2 | `APP_NAME == "proactive-ai"`, `DEFAULT_MODEL == "gemini-2.5-pro"` |

**Gaps**: No integration test for agent lifecycle. No MCP provider test. No StratusTestController test.

### 3.9 AIGatewayContext

**File**: `context/AIGatewayContext.kt` (7 lines) — Interface: `getAiGatewayUseCaseId()`, `getAiGatewayCloudId()`.

---

## 4. Cross-Feature Integration Patterns

### 4.1 Shared Platform Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│  Feature Layer                                              │
│  ┌──────────────┐ ┌───────────┐ ┌─────────────────────┐    │
│  │ Rovo Insights│ │  Nudge    │ │ Stratus/AI Gateway  │    │
│  └──────┬───────┘ └─────┬─────┘ └──────────┬──────────┘    │
├─────────┼───────────────┼──────────────────┼───────────────┤
│  Platform: task/sqs (AsyncTask) │ interceptor (SLAuth)     │
│  requestcontext/ (MDC) │ logging/ (LaasLogger)             │
│  featuregate/ (TAP)    │ client/ (IdGatekeeper)            │
│  config/ (WorkerNode)  │ service/metric/ (MetricsService)  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Request Context Flow

All controllers: SLAuth Filter → RequestContextInterceptor (MDC) → UserContextInterceptor → Controller.

### 4.3 Worker Groups

| Pod Group | Features | Condition |
|-----------|----------|-----------|
| **WebServer** | All REST controllers | Default |
| **LongRun** | `RovoInsightsGenerationSqsQueueConsumer` | `OnLongRunWorkerNodeOrLocalCondition` |
| **SHWorkers** | StreamHub event consumer | `OnSHWorkerNodeOrLocalCondition` |

### 4.4 Planned: Rovo Insights → Stratus

```
RovoInsightsGenerationTaskHandler.handle() [planned]
  → AIGatewayService.buildAgent(tools from MCP, prompts from Config.kt)
  → runAgent() → parse Flowable<Event> → RovoInsight objects
  → persist to Redis → available via /fetch
```

---

## 5. Summary of Test Coverage

| Feature | Test File | Lines | Type | Assessment |
|---------|-----------|-------|------|------------|
| Rovo Insights | `SqsQueueConsumerTest` | 201 | Unit (MockK) | Strong: MDC ordering, errors, middleware |
| Rovo Insights | `TaskHandlerTest` | 65 | Unit | Stub verification + Jackson round-trip |
| Rovo Insights | `ControllerIT` | 61 | Integration | Basic HTTP status checks |
| Nudge | `AcceptanceTest` | 158 | @SpringBootTest | Strong: all variants, auth, errors |
| Stratus | `AIGatewayServiceImplTest` | 142 | Unit (MockK) | Agent building, constants |

**Key gaps**: No controller unit tests for production Rovo Insights endpoints. No MCP integration test. No StratusTestController tests. No feature-gate tests. No contract test for `DATA_SCHEMA_VERSION`.

---

## 6. Appendix: Complete File Inventory

### Rovo Insights (16 production + 3 test)

```
feature/rovoinsights/
├── Config.kt                                     (45 lines)
├── RovoInsightsGenerationTask.kt                  (9 lines)
├── RovoInsightsGenerationTaskHandler.kt           (62 lines)
├── api/
│   ├── RovoInsightsController.kt                  (50 lines)
│   ├── status/
│   │   ├── RovoInsightsStatusRequest.kt           (14 lines)
│   │   └── RovoInsightsStatusResponse.kt          (9 lines)
│   ├── fetch/
│   │   ├── RovoInsightsFetchRequest.kt            (14 lines)
│   │   └── RovoInsightsFetchResponse.kt           (77 lines)
│   ├── rest/
│   │   └── RovoInsightsTestController.kt          (82 lines)
│   └── dto/
│       ├── RovoInsightsTestRequest.kt             (3 lines)
│       └── RovoInsightsTestResponse.kt            (5 lines)
├── internal/
│   └── RovoInsightsGenerationSqsQueueConsumer.kt  (122 lines)
└── system/
    ├── InsightType.kt                             (52 lines)
    ├── Color.kt                                   (34 lines)
    ├── Glyph.kt                                   (49 lines)
    └── RovoInsightsRequest.kt                     (31 lines)
test/
├── RovoInsightsGenerationTaskHandlerTest.kt       (65 lines)
├── RovoInsightsGenerationSqsQueueConsumerTest.kt  (201 lines)
└── RovoInsightsControllerIT.kt                    (61 lines)
```

### Nudge (4 production + 1 test)

```
feature/nudge/api/
├── domain/NudgeType.kt                            (14 lines)
├── dto/
│   ├── NudgeThrottleRequest.kt                    (9 lines)
│   └── NudgeThrottleResponse.kt                   (10 lines)
└── rest/NudgeThrottleController.kt                (39 lines)
test/NudgeThrottleControllerAcceptanceTest.kt      (158 lines)
```

### Stratus / AI Gateway (8 production + 1 test)

```
stratus/
├── AIGatewayClientConfiguration.kt                (66 lines)
├── AIGatewayService.kt                            (67 lines)
├── internal/AIGatewayServiceImpl.kt               (120 lines)
├── IntegrationServiceMcpServerConfig.kt           (14 lines)
├── IntegrationServiceMcpSessionManager.kt         (54 lines)
├── IntegrationServiceToolProvider.kt              (54 lines)
├── StratusTestController.kt                       (187 lines)
└── WeatherTool.kt                                 (25 lines)
# Note: AIGatewayContext.kt (7 lines) is in context/ package, not stratus/
test/AIGatewayServiceImplTest.kt                   (142 lines)
```

---

*Generated from source analysis of the Proactive AI Platform codebase.*
*All paths relative to `src/main/kotlin/io/atlassian/micros/proactiveai/`.*
*Test paths relative to `src/test/kotlin/io/atlassian/micros/proactiveai/`.*
