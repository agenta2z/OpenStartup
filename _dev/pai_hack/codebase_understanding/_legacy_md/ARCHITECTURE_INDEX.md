# Proactive AI Platform: Architecture & Design Documentation Index

**Last Updated:** 2026-05-05  
**Owner:** Proactive AI Platform Team  
**Related:** `ARCHITECTURE_DOCS_REPORT.md` (investigation results)

---

## Quick Navigation

### 🟢 Mature (Production-Ready)
- **[Async Task Framework](#async-task-framework)** — Long-running work off-request; 5★ docs
- **[AIGateway Integration](#aigateway--stratus-integration)** — LLM calls via Stratus SDK

### 🟡 In-Progress (Partial)
- **[Rovo Insights](#rovo-insights-feature)** — Insight generation service; stub implementation
- **[MCP Integration](#mcp-integration)** — Tool invocations via integration service; spike pending
- **[Feature Flags](#feature-flags--statsig)** — Gate taxonomy needs documentation
- **[Tenant Context](#tenant-context)** — CloudID interim model; roadmap needed

### 🔴 Needs ADR
- **[Nudge Throttle](#nudge-throttle-feature)** — Decision algorithm needs design doc
- **[Scaling Levers #2, #4](#scaling-considerations)** — Worker auto-scale and per-queue concurrency deferred

---

## Architecture Components

### Async Task Framework

**Status:** ✅ Production  
**Documentation:** ⭐⭐⭐⭐⭐ Excellent

#### Files
- **Source:** `src/main/kotlin/io/atlassian/micros/proactiveai/task/`
- **Design Doc:** `src/main/kotlin/io/atlassian/micros/proactiveai/task/README.md` (248 lines)
- **Tests:** `src/test/kotlin/io/atlassian/micros/proactiveai/task/`

#### Key Concepts
1. **Producer-Consumer Pattern:** Web tier submits `AsyncTask` → SQS → LongRun workers process
2. **One Queue Per Use Case:** Independent tuning (visibility timeout, DLQ, scaling)
3. **Execution Context Propagation:** `tenantId` + `requestId` threaded through all stages
4. **Visibility Extension:** Heartbeat `ChangeMessageVisibility(30s)` every 25s to prevent mid-flight redelivery
5. **Handler as Source of Truth:** Queue name lives on `AsyncTaskHandler.queueName`

#### Design Decisions (Documented)
| # | Decision | Rationale | Status |
|----|----------|-----------|--------|
| 1 | One queue per use case | Independent scaling/alarms per use case | ✅ Wired |
| 2 | Handler source of truth | No disagreement between producer/consumer | ✅ Wired |
| 3 | Use cases co-located with consumer | Encapsulation; prevent feature coupling | ✅ Wired |
| 4 | Consumer receives JsonNode, not typed envelope | Avoid SQS starter ObjectMapper | ✅ Wired |
| 5 | Context in body, not SQS attributes | Free propagation for all queues | ✅ Wired |

#### Scaling Levers
| Lever | What | Where | Status | Notes |
|---|---|---|---|---|
| 1 | Per-listener concurrency | `application.yml` → `concurrency: "2-8"` | ✅ Wired | Bumped from Spring default `1` → `2-8` |
| 2 | Queue-depth-driven worker scaling | `service-descriptor.sd.yml` → `LongRun` metrics | ❌ Deferred | `min: 1, max: 2` pinned; activate when bursts overwhelm |
| 3 | Visibility extension | `VisibilityExtendingSQSQueueConsumer` | ✅ Wired | Heartbeat extends visibility every 25s |
| 4 | Per-queue concurrency overrides | `IndividualConcurrencyJmsListenerContainerFactory` | ❌ Deferred | Add when second LongRun queue lands |

#### Current Capacity
```
2 instances × 8 listener threads = 16 in-flight rovo-insights tasks
200-message burst @ 30s/message → ~6 min drain (well below 720s alarm)
```

#### Adding a New Use Case
1. **SD resource** in `service-descriptor.sd.yml` (copy `rovo-insights-generation-queue`)
2. **Wire env vars** in `application.yml` under `worker.LongRun.<queue_name>`
3. **Queue name constant** in `sqs/QueueNames.kt`
4. **Envelope** at `feature/<usecase>/<UseCase>Task.kt` with `@JsonTypeName`
5. **Handler** at `feature/<usecase>/<UseCase>TaskHandler.kt` extending `AsyncTaskHandler<T>`
6. **Consumer** at `feature/<usecase>/internal/<UseCase>SqsQueueConsumer.kt` extending `VisibilityExtendingSQSQueueConsumer<JsonNode>`

#### Related PRs
- PR #97 (Apr 22, 2026): Setup Async Task Handler Framework (AIX-3265)
- PR #100 (Apr 24, 2026): Async Task Execution Context (AIX-3253)
- PR #103 (Apr 27, 2026): VisibilityExtendingSQSQueueConsumer (AIX-3259)

---

### Rovo Insights Feature

**Status:** 🟡 In-Progress (stub implementation)  
**Documentation:** ⭐⭐ Minimal

#### Files
- **Source:** `src/main/kotlin/io/atlassian/micros/proactiveai/feature/rovoinsights/`
- **Config:** `Config.kt` (45 lines, defines 6 insight types + prompt versions)
- **Controller:** `api/rest/RovoInsightsTestController.kt`
- **Handler:** `RovoInsightsGenerationTaskHandler.kt` (currently logs, doesn't generate)
- **Consumer:** `internal/RovoInsightsGenerationSqsQueueConsumer.kt`

#### Insight Types (Defined)
1. **Follow-Up Insights** — Suggested next steps based on recent work
2. **Emerging With Your Team** — Emerging trends in your team's work
3. **Company Insights** — Organization-wide insights
4. **Your Trending Work** — Your most active areas
5. **Recognition Insights** — Team recognition/acknowledgment
6. **Meeting Insights** — Meeting summaries/follow-ups

#### Config Structure
```kotlin
mapOf(
    InsightType.FOLLOW_UP_INSIGHTS to RovoInsightsPromptConfig(
        version = "v1",           // Supports A/B testing
        strategy = Strategy.EVALUATE,  // Route: EVALUATE | (future) RULE_BASED
        maxAttempts = 3,          // Retry resilience
        override = null,          // Per-user override (future)
    ),
    // ... 5 more types
)
```

#### Design Gaps
- ❓ **Prompt versioning strategy:** Why "v1"? How do we test v2 in parallel?
- ❓ **EVALUATE strategy:** What does evaluation mean? LLM inference? Rule-based filtering?
- ❓ **Max attempts = 3:** Why 3? What error triggers a retry?
- ❓ **User override:** When would we override per-user? Based on what signal?

#### Related PRs
- PR #98 (Apr 22, 2026): Add Controller and Endpoints (AIX-3273, AIX-3274)
- PR #101 (Apr 24, 2026): Add Integration Tests (AIX-3273, AIX-3274)

#### Next Steps
**⚠️ NEEDS ADR:** Create `docs/adr/ADR-NNN-Rovo-Insights-Strategy.md`
- Prompt versioning (A/B test plan)
- Evaluation methodology (LLM? Rule-based? Hybrid?)
- Retry/error handling logic
- Per-insight metrics and success criteria

---

### AIGateway & Stratus Integration

**Status:** ⚠️ Partial (MCP new, spike pending)  
**Documentation:** ⭐⭐⭐ Code comments only

#### Files
- **Configuration:** `src/main/kotlin/io/atlassian/micros/proactiveai/stratus/AIGatewayClientConfiguration.kt`
- **Service:** `stratus/AIGatewayService.kt` + `internal/AIGatewayServiceImpl.kt`
- **Context:** `context/AIGatewayContext.kt`

#### Design Principles
1. **Stable singleton beans:** `Unified` client and `ObservabilityContext` are request-agnostic
2. **Per-request context separation:** CloudID, user ID, use-case ID attached dynamically by `AIGatewayService`
3. **Service proxy pattern:** Base URL via `MESH_DEPENDENCY_AI_GATEWAY_BASE_URL`
4. **SLAUTH headers:** Identity/auth isolation via `X_SLAUTH_AUDIENCE_HEADER` + `X_SLAUTH_EGRESS_HEADER`
5. **Async/non-blocking:** `AIGatewayClient.async()` for LLM calls off-request

#### MCP Integration (NEW — PR #108)

**Status:** 🟡 Merged but spike pending  
**Jira:** AIX-3296 | **Date:** Apr 30, 2026 | **Author:** Zhangbin Cheng

#### Files
- **Config:** `stratus/IntegrationServiceMcpServerConfig.kt` (config properties)
- **Session Manager:** `stratus/IntegrationServiceMcpSessionManager.kt` (async session handling)
- **Tool Provider:** `stratus/IntegrationServiceToolProvider.kt` (load tools from integration service)
- **Test Controller:** `stratus/StratusTestController.kt` (demonstrates tool invocation)

#### Known Issues
⚠️ **Reviewer Note:** "Tool invocation works but returns unexpected outcome; spike planned for next phase"

**Design Gaps:**
- ❓ What is the "unexpected outcome"? Error type? Output format?
- ❓ Error handling strategy? (Retry? Fallback? Fail-fast?)
- ❓ Tool schema discovery? (How do we know what tools are available?)
- ❓ Integration service contract? (Expected input/output formats?)

#### Related PRs
- PR #108 (Apr 30, 2026): Integration Service MCP Setup (AIX-3296)

#### Next Steps
**🔴 NEEDS ADR:** Create `docs/adr/ADR-NNN-MCP-Integration-Error-Handling.md`
- Define "unexpected outcome"
- Error handling strategy (timeout, schema mismatch, service unavailable)
- Fallback/retry policy
- Tool schema discovery mechanism
- Metrics and logging for MCP calls

---

### Nudge Throttle Feature

**Status:** ⚠️ MVP (hardcoded response)  
**Documentation:** ⭐ OpenAPI only

#### Files
- **Controller:** `src/main/kotlin/io/atlassian/micros/proactiveai/feature/nudge/api/rest/NudgeThrottleController.kt`
- **DTO:** `feature/nudge/api/dto/NudgeThrottleRequest.kt` + `Response.kt`

#### Current Implementation
```kotlin
fun nudgeThrottle(
    @RequestHeader cloudId: String,
    @RequestHeader userId: String,
    @RequestBody body: NudgeThrottleRequest,  // { nudgeType: String }
): NudgeThrottleResponse {  // { score: Int, shouldThrottle: Boolean }
    // HARDCODED: score=10, throttle=false
    return NudgeThrottleResponse(10, false)
}
```

#### Design Gaps
- ❓ **Throttling algorithm:** Why score=10? What are decision thresholds?
- ❓ **Nudge types:** What nudge types exist? Are they feature-gated?
- ❓ **User signals:** What should drive throttling? (Recent nudges? Engagement? Feedback?)
- ❓ **Future strategy:** Rule-based? ML model? Bandit algorithm?

#### Related PRs
- PR #98 (Apr 22, 2026): Add Controller and Endpoints (AIX-3273, AIX-3274)

#### Next Steps
**🔴 NEEDS ADR:** Create `docs/adr/ADR-001-Nudge-Throttle-Strategy.md`
- Throttling algorithm (v1: rules; future: ML/bandit)
- Per-nudge-type rules (configurable via Statsig)
- User signals (cloudId, userId, nudgeType, recent activity, etc.)
- Metrics and monitoring (throttle rate, shown rate, engagement)
- A/B testing plan

---

### Feature Flags & Statsig

**Status:** 🟡 In-Progress  
**Documentation:** ⭐ Code references only

#### Files
- **Public Interface:** `src/main/kotlin/io/atlassian/micros/proactiveai/featuregate/AiFeatureGates.kt`
- **Service:** `featuregate/FeatureService.kt` + `internal/FeatureServiceImpl.kt`
- **Context:** `featuregate/FeatureFlagContextService.kt`
- **Tracking:** `featuregate/FeatureFlagEvaluationTracker.kt`

#### Architecture
- **Statsig integration:** Feature gates evaluated via Statsig SDK
- **Context-aware:** Cloud ID, user ID, experiment group used for evaluation
- **Metrics:** Gate evaluation results tracked for analysis

#### Design Gaps
- ❓ **Gate naming convention:** `feature-<name>`? `experiment-<name>`? `kill-switch-<name>`?
- ❓ **Gate taxonomy:** Which gates are feature flags? Which are kill switches? Which are experiments?
- ❓ **Rollout playbook:** Dark launch → canary → GA stages?
- ❓ **Gate lifecycle:** When do we retire gates? Cleanup policy?

#### Related PRs
- PR #10 (Dec 21, 2025): Statsig integration (initial)

#### Next Steps
**🟡 NEEDS DESIGN DOC:** Create `docs/FEATURE_GATES.md`
- Gate naming convention
- Gate taxonomy (feature flag, kill switch, experiment, config gate)
- Rollout playbook (stages, metrics, rollback criteria)
- Gate lifecycle and cleanup policy
- Metrics instrumentation

---

### Tenant Context

**Status:** 🟡 Interim (CloudID as TenantID)  
**Documentation:** ⭐⭐ Code comments only

#### Files
- **Context Interface:** `src/main/kotlin/io/atlassian/micros/proactiveai/context/TenantContext.kt`
- **Models:** `context/TenantContextModels.kt`
- **Cloud ID Context:** `context/CloudIdContext.kt`
- **Org ID Context:** `context/OrgIdContext.kt`

#### Current Model
```kotlin
// INTERIM: CloudID as TenantID
AsyncTaskExecutionContext {
    tenantId: String,      // Currently cloudId (opaque identifier)
    requestId: String,     // For log correlation
}
```

#### Design Gaps
- ❓ **Roadmap:** When do we promote to structured `TenantContext`?
- ❓ **Multi-tenancy:** Multi-org support? Shared orgs?
- ❓ **Data isolation:** How do we ensure tenant data is isolated?
- ❓ **Metrics isolation:** Per-tenant metrics/quotas?

#### Related Code
- `context/CloudIdContext.kt`
- `context/OrgIdContext.kt`
- `context/Experience.kt`, `Product.kt` (domain models)

#### Next Steps
**🟡 NEEDS ROADMAP DOC:** Create `docs/TENANT_CONTEXT_ROADMAP.md`
- Timeline for promotion from cloudId → structured `TenantContext`
- Migration path (backward compatibility? Phased rollout?)
- Multi-org/multi-tenant support plan
- Data isolation strategy
- Metrics/quota isolation

---

### Request Context & Interceptors

**Status:** ✅ Established  
**Documentation:** ⭐⭐⭐ Code + tests

#### Files
- **Context Setup:** `src/main/kotlin/io/atlassian/micros/proactiveai/requestcontext/`
- **Interceptors:** `interceptor/RequestContextInterceptor.kt`, `UserContextInterceptor.kt`
- **Logging Context:** `requestcontext/LoggingContext.kt`

#### Pattern
- Request scoped values extracted from headers
- Threaded through web + async task pipelines
- Logged on every event for traceability

---

### Metrics & Observability

**Status:** ✅ Established  
**Documentation:** ⭐⭐⭐ Code + links to Observability docs

#### Files
- **Service Interface:** `src/main/kotlin/io/atlassian/micros/proactiveai/service/metric/MetricsService.kt`
- **Core Metrics:** `service/metric/CoreMetricsService.kt`
- **Implementation:** `service/metric/internal/MetricsServiceImpl.kt`

#### Metrics Namespace
- **Prefix:** `proactive-ai` (defined in `AIGatewayClientConfiguration.METRICS_NAMESPACE`)
- **Provider:** Micrometer + Atlassian observability backend

---

## Design Decision Checklist

When adding a major feature or architecture pattern, create an ADR:

- [ ] **Is this a new architectural pattern?** (e.g., new queue, new service integration)
- [ ] **Does it affect multiple components?** (e.g., spans multiple packages)
- [ ] **Will new developers need to understand the trade-offs?** (e.g., why SQS vs. Kafka)
- [ ] **Are there alternatives that were considered?** (e.g., could use Redis instead of SQS)

**If YES to any:** Create `docs/adr/ADR-NNN-TITLE.md` using `docs/ADR_TEMPLATE.md`

---

## ADR Status & Index

| ADR | Title | Status | File |
|-----|-------|--------|------|
| Template | ADR Template for PAI | Active | `docs/ADR_TEMPLATE.md` |
| (Pending) | Async Task Framework | Accepted | Codified in `task/README.md` |
| (Pending) | Nudge Throttle Strategy | Proposed | NEEDS CREATION |
| (Pending) | MCP Integration Error Handling | Proposed | NEEDS CREATION |
| (Pending) | Rovo Insights Design | Proposed | NEEDS CREATION |
| (Pending) | Feature Flags Strategy | Proposed | NEEDS CREATION |
| (Pending) | Tenant Context Roadmap | Proposed | NEEDS CREATION |

---

## Confluence Space: PAI Designs

**Status:** ❌ DOES NOT EXIST

**Recommendation:** Create `PAI` or `AM3` space in Confluence with pages:
- Architecture Overview
- Design Decision Archive (links to ADRs)
- Component Catalog
- Integration Guide

---

## Code Quality Standards

### Logging
- ⚠️ **Requirement:** Use `LaasLoggerFactory.getLogger()` for custom logger
- ❌ **Violation in PR #98:** Custom logger pattern not enforced
- **Fix:** Add pre-commit hook in `bin/` or Poco policy

### Testing
- **Unit tests:** Handler/dispatcher instantiated directly (no SQS infra)
- **Spring `@SpringBootTest`:** Set `proactive-ai.sqs.enabled=false` to skip SQS
- **Real SQS locally:** Nebulae `local` profile provisions LocalStack queues

### Documentation
- **In-code design docs:** `README.md` files for major components (like `task/README.md`)
- **ADRs:** Decisions with alternatives/consequences
- **API docs:** OpenAPI `@Operation` annotations on controllers

---

## Contributing

### Before Opening a PR:
1. Check if your change is architectural (new queue? new service? new pattern?)
2. If yes, **draft an ADR** first (use `docs/ADR_TEMPLATE.md`)
3. Discuss ADR with tech lead / architecture owner
4. Implement, then link ADR from code/PR

### PR Description Template:
```
**Title:** [AIX-XXXX] Brief description

**Problem:** Why is this change needed?

**Solution:** What are we doing?

**Design Decision:** ADR link (if applicable)

**Test Plan:** How did you verify?

**Rollout Strategy:** Canary? Feature-gated? Immediate?
```

---

## Related Documentation

- **Git History:** `GIT_HISTORY_REPORT.md` (8 strategic PRs analysis)
- **Architecture Report:** `ARCHITECTURE_DOCS_REPORT.md` (full investigation results)
- **Core Platform Infrastructure:** `docs/02_CORE_PLATFORM_INFRASTRUCTURE.md` (~699 lines, 12 packages documented)
- **Local Development:** `LOCAL_DEV.md` (Nebulae sandbox setup)
- **Async Task Framework:** `src/main/kotlin/io/atlassian/micros/proactiveai/task/README.md` (comprehensive)

---

## Quick Links

### External Docs
- [Micros Spring Boot](https://developer.atlassian.com/platform/framework/micros-spring-boot/)
- [Stratus SDK](https://go/stratus)
- [Statsig Feature Flags](https://go/statsig)
- [RFC ARI-008: Atlassian Resource Matchers](https://hello.atlassian.net/wiki/spaces/ARCH/pages/1368170349/RFC+ARI-008+Atlassian+Resource+Matchers+ARMs)

### Team
- **Slack:** #help-ai-experience
- **Jira Project:** AIX
- **Confluence Space:** (PENDING)

---

**Last Updated:** 2026-05-05 | **Maintained By:** PAI Team
