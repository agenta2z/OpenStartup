.. _pai-architectural-decisions:

============================================================================
Architectural Decision Records — Extracted from History
============================================================================

:Date: 2026-05-05
:Confidence: **Decisions themselves are HIGH confidence** — each is tied
             to a specific PR, commit, or YAML block in the live source.
             **Stated rationale is MEDIUM confidence** — most decisions
             do not have a written ADR or design doc; rationale is
             reverse-engineered from PR descriptions, code comments,
             reviewer feedback, and the in-repo
             ``src/main/kotlin/io/atlassian/micros/proactiveai/task/README.md``.
             Where the rationale is uncertain, this chapter says so.
:Companion chapters:
             :doc:`02-development-history` (narrative summary),
             :doc:`13-full-history-catalog` (the underlying ledger),
             :doc:`15-velocity-and-debt` (the analytics).

----

.. contents:: On this page
   :depth: 3
   :local:

----

How to read this chapter
=========================

This chapter is the **decision record** for the
``proactive-ai-platform`` service. Each ADR follows a fixed schema so
they can be diffed, indexed, and reasoned about by both humans and
tools.

ADR schema:

* **ID** — ``ADR-NNN`` (zero-padded, never re-used).
* **Title** — present-tense imperative ("Use X for Y").
* **Status** — ``Accepted`` (in production), ``Superseded by ADR-NNN``,
  ``Open question`` (no decision yet but the choice exists).
* **Date** — when the decision shipped (merge date) or when this ADR
  was written (for retroactive ADRs).
* **Context** — why a decision was needed.
* **Decision** — the decision itself, stated unambiguously.
* **Alternatives considered** — what was rejected.
* **Consequences** — both intended and unintended.
* **Source** — the PR / commit / file that implements the decision.
* **Confidence** — how confident this chapter's author is in the
  decision/rationale (HIGH = stated in source; MEDIUM = inferred from
  context; LOW = guess, marked for team review).

A retroactive ADR (one written *after* the decision shipped) is
explicitly marked ``[RETROACTIVE]`` and is a request for the team to
confirm or correct it.

----

ADR-001 — Split execution across WebServer / SHWorkers / LongRun JVMs
============================================================================

* **Status:** Accepted.
* **Date:** 2026-02 (PR #97 ``393a5f8``).
* **Confidence:** HIGH (stated in
  ``src/main/kotlin/io/atlassian/micros/proactiveai/task/README.md``).

**Context.** Long-running LLM-bound tasks (Rovo Insights generation,
multi-second AI Gateway calls) cannot share a thread pool with
latency-sensitive HTTP requests. A nudge-throttle decision has a
sub-50 ms p95 target; a single generation call can occupy a thread
for tens of seconds. Co-locating them on one JVM/pool causes head-of-
line blocking and request timeouts under load.

**Decision.** Run **three deployment groups** of the same Spring Boot
application:

* ``WebServer`` — handles synchronous HTTP traffic.
* ``SHWorkers`` — drains StreamHub analytics SQS events.
* ``LongRun`` — drains Rovo Insights generation tasks.

Each group has its own ``MICROS_GROUP`` env var. Beans are gated to
the correct group by ``OnSHWorkerNodeOrLocalCondition`` /
``OnLongRunWorkerNodeOrLocalCondition`` (both in
``config/``). The ``local`` profile short-circuits both conditions so
local dev gets the full bean graph on a single JVM.

**Alternatives considered.**

1. **Single JVM, multiple thread pools.** Rejected: a single JVM
   crash takes everything down; CPU contention isn't isolated.
2. **Separate microservices per workload.** Rejected: triples
   deployment & ownership cost; the service is small enough that
   pool isolation is sufficient.
3. **Coroutine-only async on web tier.** Rejected: AI Gateway calls
   can be 10s of seconds; coroutines suspend but the underlying SQS
   message is still in flight and capacity-counted.

**Consequences.**

* **Intended:** latency isolation; per-pool autoscaling;
  failure-isolation.
* **Unintended:** every Spring bean must carry a ``@Conditional`` or
  be safe on all groups. Adds a small mental tax on every new bean.
  Documented in :doc:`/modules/platform/config`.

**Source.**

* PR #97 ``393a5f8`` (initial split).
* ``service-descriptor.sd.yml`` §``workers`` (lines ~205-223).
* ``config/OnSHWorkerNodeOrLocalCondition.kt``,
  ``OnLongRunWorkerNodeOrLocalCondition.kt``.

----

ADR-002 — Use SQS as the in-process async transport
============================================================================

* **Status:** Accepted.
* **Date:** 2026-02 (PR #97 ``393a5f8``).
* **Confidence:** HIGH
  (stated in ``task/README.md`` Tradeoffs section).

**Context.** Async tasks must survive JVM restarts (a Rovo Insights
generation may take 30+ s; a deploy or scale-down event must not lose
the request) and must scale horizontally across LongRun workers.

**Decision.** Use **AWS SQS** as the transport, with one queue per
async-task type:

* ``rovo-insights-generation-queue`` — standard SQS, MaxReceiveCount=2,
  VisibilityTimeout=360 s.
* ``analytics-events`` — standard SQS, MaxReceiveCount=3,
  VisibilityTimeout=120 s.
* DLQ provisioned per queue.

Tasks are JSON-serialised with ``@JsonTypeInfo`` polymorphism via
``AsyncTask`` interface; reconstruction context (tenant, account,
request id) is carried in **SQS message attributes** (not in the
JSON body), so logging context can be re-established before
deserialisation.

**Alternatives considered.**

1. **In-process queue (Spring task executor).** Rejected: doesn't
   survive restarts; doesn't scale across nodes.
2. **Kafka.** Rejected: SQS already in the Atlassian standard stack
   for similar workloads; Kafka would add a new ops surface.
3. **Redis lists / Streams.** Rejected: durability story weaker
   than SQS for the Atlassian deployment topology.
4. **Step Functions.** Rejected: overkill for single-step tasks;
   may revisit for multi-step generation flows in FY27.

**Consequences.**

* **Intended:** durable, horizontally scalable, ops-team familiar.
* **Unintended:** at-least-once delivery means every handler must be
  idempotent. Currently enforced by convention, not by code; flagged
  as a hardening item in :doc:`12-optimization-playbook` Lever 4.2.
* **Unintended:** ordered delivery is not guaranteed (standard SQS).
  Acceptable because each generation task is independent. Re-evaluate
  if per-tenant ordering becomes a requirement (FIFO migration —
  Lever 3.3 in the playbook).

**Source.**

* PR #97 ``393a5f8``;
* ``service-descriptor.sd.yml`` §``sqs`` (lines ~93-152);
* ``src/main/kotlin/io/atlassian/micros/proactiveai/task/README.md``.

----

ADR-003 — Replay request context via SQS message attributes
============================================================================

* **Status:** Accepted.
* **Date:** 2026-02 (PR #100 ``2ea5f42``).
* **Confidence:** HIGH (entire purpose of PR #100).

**Context.** A developer searching Splunk for a ``request_id``
should see the entire end-to-end story — HTTP request, async task
dispatch, SQS message landing on a worker, generation, response —
without the trail breaking at the SQS boundary. Without context
replay, the trail dies at the HTTP-202 response from the producer.

**Decision.** Carry ``tenant_id``, ``account_id``, ``request_id``,
and ``user`` (JSON) as **SQS message attributes** (not in the body).
On the consumer side, ``MessageQueueConsumerMiddleware`` rebuilds
MDC via ``LoggingContext.addAsyncTaskContext()`` *before* the handler
runs. The body remains the polymorphic JSON ``AsyncTask``.

**Alternatives considered.**

1. **Carry context in the JSON body.** Rejected: forces every
   ``AsyncTask`` subclass to declare context fields; pollutes the
   domain shape with infra concerns.
2. **Re-derive context from the SQS handler thread.** Rejected:
   thread is fresh; nothing to derive from.
3. **W3C Trace-context propagation.** Rejected for now: works
   beautifully for traces but doesn't cover MDC fields like
   ``account_id`` and the user JSON. May add as a complement, not a
   replacement, in FY27.

**Consequences.**

* **Intended:** full Splunk story per ``request_id`` across the
  WebServer→SQS→LongRun boundary.
* **Intended:** the same context-replay invariant applies to any new
  ``AsyncTask`` type for free.
* **Unintended:** SQS message-attribute size limits cap the user
  JSON to 256 KB total per message; not a problem today, would be a
  problem if user objects grew unbounded.

**Source.**

* PR #100 ``2ea5f42``.
* ``task/internal/AsyncTaskExecutionContextWire.kt``.
* ``requestcontext/internal/LoggingContextImpl.kt:54-58``.

----

ADR-004 — Extend SQS visibility timeout in-flight, not at config
============================================================================

* **Status:** Accepted.
* **Date:** 2026-04 (PR #103 ``e2de3cc``).
* **Confidence:** HIGH (the *whole point* of PR #103).

**Context.** SQS messages must complete within their VisibilityTimeout
or be redelivered. Generation tasks vary widely in duration. Setting
the queue-level timeout to the worst case (e.g., 10 minutes) wastes
worker capacity for short tasks; setting it low (e.g., 5 minutes)
causes false re-deliveries for long tasks.

**Decision.** Set queue ``VisibilityTimeout`` to a moderate baseline
(360 s on ``rovo-insights-generation-queue``) and have a dedicated
``VisibilityExtendingSQSQueueConsumer`` periodically extend visibility
on still-in-flight messages. Result: per-message effective timeout
adjusts to actual work, not to worst-case config.

**Alternatives considered.**

1. **Set queue VisibilityTimeout to worst case.** Rejected: 8×
   throughput penalty (per the PR's quoted measurement).
2. **Split queues by expected duration.** Rejected: brittle;
   developers can't predict duration accurately.
3. **Move to Step Functions.** Rejected: too much surgery for the
   problem at hand.

**Consequences.**

* **Intended:** **8× throughput improvement** as quoted by the PR
  description. (Independently re-verifiable: read PR #103
  description.)
* **Unintended:** the ``VisibilityExtendingSQSQueueConsumer`` is
  itself gated by ``OnLongRunWorkerNodeOrLocalCondition``; if a
  developer adds a new generation queue, they must remember to add
  the consumer to the visibility-extender's awareness list.
  Documented in :doc:`/modules/platform/sqs`.

**Source.**

* PR #103 ``e2de3cc``.
* ``task/internal/VisibilityExtendingSQSQueueConsumer.kt``.

----

ADR-005 — Use Atlassian Integrations Service as the MCP tool server
============================================================================

* **Status:** Accepted.
* **Date:** 2026-04 (PR #108 ``5c6e72c``).
* **Confidence:** HIGH on the choice; **MEDIUM** on the long-term
  fit (the Confluence-ADR investigation surfaced a comment that the
  PR was merged with "unexpected outcome" — implementation works but
  some error handling is undefined).

**Context.** Stratus agents in PAI need to call Atlassian product
tools (Jira search, Confluence read, Rovo Insights internals).
Implementing per-tool integration code for every product is
prohibitively expensive and a re-implementation of work the
Integrations Service already does.

**Decision.** Use the Atlassian **Integrations Service** as an
**MCP server**; PAI is an MCP **client**. New tools become available
via MCP discovery — no PAI code change needed.

Wiring lives in three classes in ``stratus/``:

* ``IntegrationServiceMcpServerConfig`` — server URL + auth.
* ``IntegrationServiceMcpSessionManager`` — MCP session lifecycle.
* ``IntegrationServiceToolProvider`` — adapter exposing MCP tools to
  Stratus.

Mesh egress to ``integrations-service`` is configured in
``service-descriptor.sd.yml`` with a 60 s timeout.

**Alternatives considered.**

1. **Per-tool Spring beans.** Rejected: doesn't scale; every new
   product tool is a new PR.
2. **Direct Jira/Confluence API calls.** Rejected: re-implements
   auth, retry, multi-tenancy that Integrations Service already
   handles.
3. **Wait for Rovo Chat's tool layer.** Rejected: convo-ai-platform
   is request-driven; PAI is event-driven; the contract differs.

**Consequences.**

* **Intended:** zero-PR cost to expose a new tool in PAI once the
  tool exists in Integrations Service.
* **Unintended:** PAI now depends on the Integrations Service uptime
  for any agentic generation. Ingest-side egress timeout is
  60 s; a failed Integrations Service call causes a generation to
  fall back to "no tools available" rather than fail entirely
  (graceful-degradation pattern).
* **Open question (MEDIUM-LOW confidence):** error-handling for
  partial MCP-session failures (some tools available, some not)
  is **undefined in code** as of 2026-05-05. The Confluence-ADR
  investigation flagged this as a follow-up. **Action:** write a
  proper ADR-005a addendum once behaviour is decided.

**Source.**

* PR #108 ``5c6e72c``.
* ``stratus/IntegrationServiceMcpServerConfig.kt`` and siblings.

----

ADR-006 — Use Statsig for feature flags with two-phase context
============================================================================

* **Status:** Accepted.
* **Date:** 2026-01 (early feature service work).
* **Confidence:** HIGH (the two-phase pattern is explicit in
  ``FeatureService.kt``: ``checkGate`` vs ``checkGateWithLimitedContext``).

**Context.** Some feature decisions must be made early in a request
(before tenant resolution) — e.g., to short-circuit a route. Others
need full tenant context (e.g., per-tenant rollout). A single
``checkGate`` call would force every flag to wait for tenant
resolution.

**Decision.** Two-phase API:

* ``checkGateWithLimitedContext()`` — early, no tenant required.
* ``checkGate()`` — full, requires tenant id.

``RequestContextInterceptor`` populates limited context;
``UserContextInterceptor`` populates full context. Statsig SDK
under the hood.

**Alternatives considered.**

1. **Single ``checkGate`` with implicit context-fill.** Rejected:
   silently produces wrong decisions when called early.
2. **LaunchDarkly / split.io.** Rejected: Statsig is the Atlassian
   standard.
3. **Self-rolled flags in a YAML.** Rejected: no per-tenant rollout
   support.

**Consequences.**

* **Intended:** correct flag evaluation at every request lifecycle
  stage.
* **Unintended:** developers must pick the right method; a wrong
  choice silently degrades to a correct-by-accident behaviour. Flag
  this in code-review.

**Source.**

* ``featuregate/FeatureService.kt:22-113``.
* :doc:`04-feature-flags`.

----

ADR-007 — Use Statsig environment via raw env var, not the typed enum
============================================================================

* **Status:** Accepted **as a temporary state** (not a long-term
  intent).
* **Date:** 2026-01 (initial feature service); audited 2026-05-05.
* **Confidence:** HIGH on the present state; the *intent* of the
  decision is unwritten.

**Context.** ``MicrosEnvironmentConfig`` (config package) produces a
typed ``MicrosEnvironmentType`` bean. ``FeatureFlagContextServiceImpl``
needs the environment string for Statsig's ``customAttributes`` key.

**Decision.** ``FeatureFlagContextServiceImpl`` reads
``@Value("\${MICROS_ENV:}")`` directly, ignoring the typed bean.

**Alternatives considered.**

1. **Inject ``MicrosEnvironmentType`` bean.** Would be cleaner,
   single source of truth.
2. **Status quo (raw string).** Faster to implement; no compile-time
   coupling.

**Consequences.**

* The typed bean has **zero consumers** as of 2026-05-05
  (verified inline; see :doc:`/modules/platform/config` Part —
  "Environment Modelling" + the ``.. note::`` block).
* Future contributors may write their own ``@Value("\${MICROS_ENV}")``
  reads, multiplying the inconsistency.

**Recommendation (this chapter):** **Supersede this ADR with ADR-008
(below).** Migrate the one extant raw-string consumer to the typed
bean; mark this ADR as ``Superseded by ADR-008`` once done. Good
first-PR for new contributors.

----

ADR-008 — [PROPOSED, RETROACTIVE] Use ``MicrosEnvironmentType`` bean for environment-conditional code
========================================================================================================

* **Status:** **Open question** (proposed, not accepted).
* **Date:** Drafted 2026-05-05 by this chapter's author.
* **Confidence:** LOW — this is a proposal, not a record.

**Context.** As ADR-007 documents, environment is read both as a
typed bean (one consumer: ``MicrosEnvironmentConfig`` itself) and as
a raw string (one consumer: ``FeatureFlagContextServiceImpl``).
Two patterns for the same concept invites drift.

**Proposed decision.** All environment-conditional code reads the
``MicrosEnvironmentType`` bean. ``MicrosEnvironmentConfig`` becomes
the single source of truth.

**Alternatives.** Status quo (ADR-007); deprecate the typed bean and
standardise on raw strings.

**Open question for the team.** Which way? Document the call,
update :doc:`/modules/platform/config`, supersede ADR-007.

----

ADR-009 — Wrap SLF4J via ``LaasLoggerFactory`` exclusively
============================================================================

* **Status:** Accepted (enforced by code review, not by lint).
* **Date:** Early 2026; reinforced repeatedly by reviewers.
* **Confidence:** HIGH on the intent; MEDIUM on the
  enforcement mechanism (no detekt rule found that automatically
  bans direct ``LoggerFactory.getLogger(...)``).

**Context.** MDC keys (``request_id``, ``tenant_id``, etc.) are
carried by the ``LaasLogger`` wrapper around SLF4J. A direct
``LoggerFactory.getLogger(...)`` call drops the MDC enrichment that
on-call relies on for Splunk pivots.

**Decision.** Every logger declaration goes through
``LaasLoggerFactory.create<MyClass>()``. Direct ``LoggerFactory``
calls are **forbidden**.

**Alternatives considered.**

1. **Just put MDC in the SLF4J Mapped Diagnostic Context directly.**
   Rejected: the MDC keys can drift; a wrapper enforces the schema.
2. **Subclass ``LoggerFactory``.** Rejected: brittle to SLF4J
   version changes.

**Consequences.**

* **Intended:** correct MDC enrichment everywhere.
* **Unintended:** adoption is by reviewer vigilance, not by lint;
  recurrent reviewer comments per :doc:`02-development-history` §5.
  **Recommendation:** add a detekt rule that bans
  ``org.slf4j.LoggerFactory.getLogger`` outside ``logging/``.

**Source.**

* ``logging/LaasLoggerFactory.kt``.
* :doc:`/modules/platform/logging`.

----

ADR-010 — Async-first generation; Redis caches the result
============================================================================

* **Status:** Accepted (architectural intent; full implementation
  pending real generation handler).
* **Date:** 2026-02 (Redis PR #96 + async task PRs #97/#100); intent
  documented in ``task/README.md``.
* **Confidence:** HIGH on the intent; MEDIUM on the cache-key /
  TTL choices because the real handler is still a stub.

**Context.** A Rovo Insights generation can take 30+ seconds. Front
ends should not block on the AI Gateway call.

**Decision.** The user-facing API is **async** — submit returns
202 with a result identifier; the front end polls a separate read
endpoint backed by Redis (``proactive-ai-cache``, single primary +
1 replica, cache.t4g.small). Generation runs on LongRun workers;
result is written to Redis.

**Alternatives considered.**

1. **Sync, with streaming.** Rejected: ties up an HTTP thread for
   30 s; doesn't survive worker restart.
2. **Webhook back to caller.** Rejected: requires every caller to
   implement a webhook; complicated for first-party UIs.

**Consequences.**

* **Intended:** request-thread free; user-perceived latency = poll
  cadence × Redis p99.
* **Open questions** (the real generation handler is still a stub):
  cache TTL not yet decided; per-tenant cache-key strategy not yet
  decided. **Action:** write ADR-010a once the handler ships.

**Source.**

* PR #96 ``05a3219`` (Redis).
* PR #97 ``393a5f8`` (async).
* ``service-descriptor.sd.yml`` §``redisx``.

----

ADR-011 — Use t3a.medium across all groups (start small)
============================================================================

* **Status:** Accepted (intentionally provisional).
* **Date:** Initial provisioning (``service-descriptor.sd.yml`` §
  ``scaling``).
* **Confidence:** HIGH (PR comment quoted in
  :doc:`02-development-history`: *"start small; resize via
  go/instance-types"*).

**Context.** Service has no production hot-path load yet. Instance
sizing is a knob to be turned later, not a thing to optimise upfront.

**Decision.** All deployment groups use ``t3a.medium`` (2 vCPU /
4 GiB / ~1 GiB JVM heap with ``-XX:MaxRAMPercentage=25.0``).
LongRun is capped ``max: 2``; SHWorkers is ``min: 1`` with no max.

**Alternatives.** Larger instance types; explicit autoscaling rules
per group.

**Consequences.**

* **Intended:** low cost while pre-production; easy to bump.
* **Unintended:** **LongRun ``max: 2`` is a hard ceiling on
  generation parallelism**, identified as the bottleneck for the
  Rovo Insights production rollout. Lever 3.2 in
  :doc:`12-optimization-playbook`.

**Source.**

* ``service-descriptor.sd.yml`` (lines ~205-265).

----

ADR-012 — All alarms ``Priority: Low``; runbooks deferred
============================================================================

* **Status:** Accepted **as a temporary state**.
* **Date:** Inception of each alarm (2026-01 onward).
* **Confidence:** HIGH on the present state.

**Context.** Service is pre-hot-path. False-positive pages would
train on-call to ignore real ones.

**Decision.** Every alarm starts at ``Priority: Low``. Runbook URL
is ``TBD`` until the alarm ever fires in anger.

**Alternatives.**

1. Author runbooks pre-emptively.
2. Wire alarms to a dev Slack channel only.

**Consequences.**

* **Intended:** zero pager fatigue; alarm authors aren't blocked on
  runbook writing.
* **Unintended:** when load arrives, no alarm wakes anyone, and no
  runbook exists to guide recovery. **Action:** before ramp,
  promote at least one alarm per surface to ``Priority: Medium``
  and author its runbook. Lever 4.3 + 5.1 in
  :doc:`12-optimization-playbook`.

**Source.**

* ``service-descriptor.sd.yml`` §``alarms`` and §``sqs[*].alarms``.

----

ADR-013 — No formal SLO file; aspirational targets in docs only
============================================================================

* **Status:** Accepted **as a temporary state**.
* **Date:** Verified 2026-05-05 by listing
  ``continuous-verification.yml`` (does not exist) and
  ``compass.yaml`` (does not exist).

**Context.** SLOs in Tome / continuous-verification are deploy-gating
once registered. Pre-production load means a tight SLO would block
deploys for synthetic reasons.

**Decision.** Document aspirational SLOs in
:doc:`01-business-and-technical-goals` Part 3 only. No
``continuous-verification.yml`` is committed.

**Consequences.**

* **Intended:** no false deploy blocks during early development.
* **Unintended:** when production load arrives, regressions are
  invisible to deploy gates. **Action:** before ramp, author a
  starter ``continuous-verification.yml`` with conservative SLOs
  (e.g., p95 < 1 s on the nudge endpoint). Lever 5.2 in
  :doc:`12-optimization-playbook`.

----

RISK-001 — Single-contributor concentration
============================================================================

(Not a decision — a *risk* documented here so the decision
"do nothing about it" is explicit.)

* **Status:** Acknowledged, no mitigation in code yet.
* **Confidence:** HIGH (per the verified contributor count in
  :doc:`13-full-history-catalog` Part 3).

**Risk.** Zhangbin Cheng authored 55 of 102 commits (54 % of all,
**82 % of human commits**). Every load-bearing platform PR in the
list above (#96, #97, #100, #103, #108) is theirs.

**Mitigation surface.** Cross-train MD or another contributor on
the async-task framework + Stratus / MCP integration. Add a
"knowledge-distribution" KPI to the team's H2 or H1-FY27 OKR list
(e.g., "≥ 2 unique authors per critical-path PR"). Pair-program
the next material change to ``feature/rovoinsights/`` or
``stratus/``.

----

How to add a new ADR
======================

When you ship a PR that introduces a non-obvious architectural
choice — anything that another engineer might later ask "why was
this done?" — add an ADR here:

1. Pick the next ``ADR-NNN`` (zero-padded).
2. Use the schema above.
3. **Be honest** about confidence and alternatives. ADRs that hide
   the alternatives don't help anyone six months later.
4. Cite the implementing PR / commit / YAML block.
5. Cross-link from :doc:`13-full-history-catalog` Part 5
   (the strategic-PR list) if applicable.
6. If your decision **supersedes** an existing ADR, mark the old
   one ``Superseded by ADR-NNN`` and link in both directions.

Cross-references
==================

* :doc:`13-full-history-catalog` — the underlying history.
* :doc:`02-development-history` — narrative summary.
* :doc:`15-velocity-and-debt` — analytics that informed RISK-001.
* :doc:`12-optimization-playbook` — the "what to do about it"
  for many of these "temporary state" ADRs.
* :doc:`/modules/platform/config` — implementation of ADRs 1, 7, 11.
* :doc:`/modules/platform/task` — implementation of ADRs 2, 3, 4, 10.
* :doc:`/modules/platform/stratus` — implementation of ADR 5.
* :doc:`/modules/platform/featuregate` — implementation of ADR 6.
* :doc:`/modules/platform/logging` — implementation of ADR 9.
