# ADR Template for Proactive AI Platform

Use this template for any architectural decision. File as `docs/adr/ADR-NNN-TITLE.md`.

---

## ADR-XXX: [Short Title]

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Deprecated | Superseded  
**Author:** [Name]  
**Reviewers:** [Names]  

### Context

What is the issue we're facing? What constraints do we have?

Example:
> We need to process long-running RovoInsights generation tasks (30-120s per request) without blocking the web tier. The web tier is deployed on the ShortHandler worker group, which scales independently from LongRun workers.

### Decision

What is our decision?

Example:
> We will use a dedicated SQS queue per use case (e.g., `rovo-insights-generation-queue`) with a consumer on the LongRun worker group. The producer publishes an `AsyncTask` envelope via `AsyncTaskService.submit()`, and the consumer routes it to the appropriate handler via `AsyncTaskDispatcher`.

### Rationale

Why did we make this decision? What are the trade-offs?

Example:
> - **Per-queue isolation:** Visibility timeouts, DLQ alarms, and scaling are tuned independently for each use case.
> - **Handler as source of truth:** The queue name lives on `AsyncTaskHandler.queueName`, eliminating disagreement between producer and consumer.
> - **No streaming/state:** Unlike convo-ai's async task framework, we don't support streaming or Redis-backed state. This keeps the framework simple for v1.

### Alternatives Considered

What other options did we evaluate?

| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Shared SQS queue | Simpler infrastructure | Can't tune visibility/alarms per use case; contention on single consumer | Lost per-use-case tuning |
| Redis pubsub | Lightweight | Lossy (no durability); complex state management | Risk of message loss |
| Kafka | Durable, ordered | Operational overhead; partition rebalancing | Overkill for current scale |

### Consequences

What are the downstream implications?

**Positive:**
- Long handlers (100s+) can run without mid-flight redelivery (with `VisibilityExtendingSQSQueueConsumer`).
- Per-use-case scaling via levers: concurrency, worker group sizing, visibility extension.
- Adding a new use case is a 6-step process (documented in `task/README.md`).

**Negative:**
- Each use case needs its own SQS queue and DLQ (CloudFormation overhead).
- Handlers must be idempotent (at-least-once delivery).
- No built-in cancellation or streaming (future enhancement).

### Implementation Notes

- **Framework:** `io.atlassian.micros.proactiveai.task/`
- **Use case example:** `feature/rovoinsights/`
- **Consumer base class:** `VisibilityExtendingSQSQueueConsumer<JsonNode>`
- **Testing:** Set `proactive-ai.sqs.enabled=false` in test properties to skip SQS infra.

### Related Issues / PRs

- PR #97: Setup Async Task Handler (AIX-3265)
- PR #100: Async Task Execution Context (AIX-3253)
- PR #103: Visibility Extension (AIX-3259)

### Review Checklist

- [ ] Decision rationale clear to new team members?
- [ ] Alternatives documented?
- [ ] Implementation plan explicit?
- [ ] Consequences understood?
- [ ] Related code/docs linked?
- [ ] Approval from tech lead / architecture owner?

---

## Example: ADR-001 Nudge Throttle Strategy (Template Fill)

**Date:** 2026-05-05  
**Status:** Proposed  
**Author:** [PAI Team]  
**Reviewers:** [Tech Lead]  

### Context

The nudge throttle feature controls whether a nudge (alert/suggestion) should be shown to a user based on their recent activity. Currently, the endpoint returns hardcoded values (`score=10, shouldThrottle=false`), which was acceptable for MVP but needs a documented strategy for expansion.

### Decision

We will implement nudge throttling as a decision service with three future strategies:
1. **RULE_BASED** (current): Hard-coded rules by nudge type (v1)
2. **ML_MODEL** (future): Trained model predicting user engagement given context
3. **BANDIT** (future): Multi-armed bandit to optimize for nudge effectiveness

For v1, we hard-code one rule per nudge type. Rules are defined in Statsig feature flags (`nudge-throttle-<type>`) for easy A/B testing.

### Rationale

- **Future-proof:** Strategy pattern allows new algorithms without code changes.
- **A/B testable:** Statsig gates let us roll out rule changes incrementally.
- **User context available:** We have `cloudId`, `userId`, `nudgeType` in the request; room for more signals later.
- **Low operational burden:** v1 is simple (one rule per type), enabling fast iteration.

### Alternatives Considered

| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Hard-code all logic | Simplest | No A/B testing; no room for new strategies | Blocks future experiments |
| Call external ML service | Flexible | Latency risk; external dependency | Not yet trained; Stratus/AIGateway is for generation, not classification |
| Bandit algorithm immediately | Optimal | Complex; need tracking infrastructure first | Premature optimization |

### Consequences

**Positive:**
- A/B testing nudge rules via Statsig.
- Room to add ML/bandit later without API changes.
- Per-nudge-type rules (can differ by user segment if needed).

**Negative:**
- Need Statsig gate per nudge type (6 gates initially).
- Rules live in Statsig, not code (less reviewable via git).
- Must monitor throttle rates to detect bad rules.

### Implementation Notes

- **File:** `feature/nudge/` (new: `NudgeThrottleService`, strategy interface, implementations)
- **Config:** Statsig gates: `nudge-throttle-follow-up`, `nudge-throttle-meeting`, etc.
- **Metrics:** Track `nudge.throttle.rate` and `nudge.shown.rate` by type.
- **Endpoint:** `POST /api/v1/nudge/throttle` (existing); replace hardcoded response with service call.

### Related Issues / PRs

- PR #98: Add Controller and Endpoints (AIX-3273)
- (Pending) Feature: NudgeThrottleService implementation

### Review Checklist

- [ ] Strategy pattern clear?
- [ ] Statsig gates enumerated?
- [ ] Metrics plan documented?
- [ ] Future algorithms discussed with PMs?
- [ ] A/B test plan defined?

---

## Example: ADR-002 MCP Integration Error Handling

**Date:** 2026-05-05  
**Status:** Proposed  
**Author:** [PAI Team]  
**Reviewers:** [Tech Lead]  

### Context

PR #108 integrated MCP tools via `IntegrationServiceMcpSessionManager`, but the reviewer noted "tool invocation works but returns unexpected outcome; spike planned for next phase." We need to formalize:
1. What constitutes "unexpected outcome"?
2. How should we handle MCP tool errors?
3. When do we fall back vs. retry?

### Decision

- **On MCP success:** Return tool output directly to caller (e.g., AIGateway).
- **On MCP timeout (5s default):** Return error to caller; do NOT retry (caller decides).
- **On MCP schema mismatch:** Log to CloudWatch; return error; require manual tool registration fix.
- **On integration service unavailable:** Return `ServiceUnavailable` to caller; let Stratus decide retry.

### Rationale

- Timeouts are expected in distributed systems; retrying client-side compounds latency.
- Schema mismatches are developer errors; automating retry masks the problem.
- We keep error handling simple (fail-fast) to avoid hiding bugs.

### Alternatives Considered

| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Retry on any error | Resilient | May mask bugs; compounded latency | Hiding issues |
| Cache MCP schemas | Faster | Requires cache invalidation; adds complexity | Not needed for v1 |
| Fallback to rule-based tool | Safe | Degrades quality; hard to debug | Breaks MCP contract |

### Consequences

**Positive:**
- Clear error contracts (caller knows when to retry).
- Bugs surface quickly (no silent retries).

**Negative:**
- Caller must handle MCP errors (places burden on AIGateway/Stratus).
- No automatic resilience for transient failures.

### Implementation Notes

- **File:** `stratus/IntegrationServiceMcpSessionManager.kt`
- **Error types:** `MCP_TIMEOUT`, `MCP_SCHEMA_MISMATCH`, `MCP_SERVICE_UNAVAILABLE`
- **Metrics:** Track error rates by type.
- **Logging:** Include tool name, invocation time, error details in CloudWatch.

### Related Issues / PRs

- PR #108: Integration Service MCP Setup (AIX-3296)

---

## Usage Instructions

1. **Copy this file** to `docs/adr/ADR-NNN-TITLE.md` (replace XXX with next number, TITLE with short slug).
2. **Fill in all sections** using examples above as a guide.
3. **Link from related code** (add comment: "See docs/adr/ADR-NNN-TITLE.md").
4. **Commit to git** alongside PR that implements the decision.
5. **Index in Confluence** (create page in PAI space, link to MD file).

---

**Template Version:** 1.0 | Last Updated: 2026-05-05
