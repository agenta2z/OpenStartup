.. _pai-development-history:

============================================================================
Development History — How the codebase reached its current state
============================================================================

:Date: 2026-05-04 (original); 2026-05-05 (enhanced with verified data + 3 new
       deep-dive chapters; corrections noted below)
:Sources: ``git log`` on ``main`` (102 commits, verified) + Bitbucket Pull
          Requests #1–#116 + AIX Jira tickets (25 unique) + Confluence design
          docs (where they exist).
:Verification: Each PR cited with ID + commit hash. Numerical claims
               re-verified 2026-05-05 against ``git log`` direct output.

.. note::

   **This chapter is the human-narrative summary.** Three deep-dive
   companion chapters were authored 2026-05-05 to back this narrative
   with machine-followable detail:

   * :doc:`13-full-history-catalog` — every commit, every contributor,
     every AIX ticket, every churn file. Each cell paired with the exact
     ``git`` command that produces it.
   * :doc:`14-architectural-decisions` — ADR-style records of 13
     decisions extracted from the history (incl. retroactive ADRs marked
     as such), with alternatives considered + consequences + open questions.
   * :doc:`15-velocity-and-debt` — quantitative analytics: commits/month,
     contributor distribution, bug-fix ratio, test:source ratio, churn
     distribution, with reproducibility script.

   **Read order:** if you want the story, read this chapter first. If you
   want the receipts, jump straight to chapter 13.

.. note::

   **Verification corrections (2026-05-05):** the original "Q4 CY2025"
   bootstrap label is now precisely **2025-11-10** (first commit
   ``017d537``); the original "100+ commits" estimate is **102 exactly**;
   the contributor split was **inferred** in the original — verified
   numbers in :doc:`15-velocity-and-debt` Part 2 show Zhangbin Cheng at
   **82 % of human commits** (single-contributor concentration risk
   documented as RISK-001 in :doc:`14-architectural-decisions`).

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Timeline at a glance
==========================

::

   Q4 CY2025 ── Q1 CY2026 ──── Q2 CY2026 ──────────────────► today (May 2026)

   ┌─────────────┐ ┌─────────────────┐ ┌──────────────────────────────────┐
   │ Bootstrap   │ │ Foundation      │ │ Feature push                     │
   │ from        │ │                 │ │                                  │
   │ Spring Boot │ │ Kotlin          │ │ • Async-task framework           │
   │ template    │ │ migration       │ │ • Visibility extension (8× thpt) │
   │             │ │ Feature service │ │ • MCP integration                │
   │             │ │ Logging         │ │ • Rovo-Insights stub             │
   │             │ │                 │ │ • Nudge-throttle stub            │
   │             │ │                 │ │ • Redis cache provisioning       │
   └─────────────┘ └─────────────────┘ └──────────────────────────────────┘

2. Top 8 strategic PRs (deep-fetch)
========================================

These are the PRs that **moved the architecture**, not the dependency-bump PRs.

2.1 PR #96 — Redis integration (commit ``05a3219``)
------------------------------------------------------

* **Author:** Zhangbin Cheng
* **What:** Provisioned ``proactive-ai-cache`` (Valkey 7.x, ``cache.t4g.small``)
  in ``service-descriptor.sd.yml``; added Redis client wiring.
* **Why it matters:** First persistent state in the service. Unlocked
  Rovo-Insights result caching and (future) throttle decision dedupe.
* **Reviewer feedback patterns:** Sized small ("start small; resize via
  go/instance-types"); Single primary + 1 replica; transit encryption
  enabled; alarms wired for ``EngineCPUUtilization``.

2.2 PR #97 — Async task handler skeleton (commit ``393a5f8``)
---------------------------------------------------------------

* **Author:** Zhangbin Cheng
* **What:** Introduced ``AsyncTask`` / ``AsyncTaskHandler`` / ``AsyncTaskService``
  / ``AsyncTaskDispatcher`` interfaces and the ``RovoInsightsGenerationTask`` +
  handler stub. Wired the ``rovo-insights-generation-queue`` SQS consumer.
* **Why it matters:** Established the **send-once, replay-MDC** invariant
  that every long-running feature now uses. The pattern lets the team add
  new async features without touching SQS plumbing.
* **Architectural impact:** Codified separation of WebServer / LongRun JVMs;
  introduced ``AsyncTaskExecutionContext`` as the canonical context-replay
  triple.

2.3 PR #98 — REST controllers + endpoints (commit ``55042dd``)
----------------------------------------------------------------

* **Author:** Michael Dawson
* **What:** Added ``RovoInsightsController``, ``RovoInsightsTestController``,
  ``NudgeThrottleController`` and their DTOs.
* **Reviewer feedback** (visible in PR comments):

  * Multiple comments flagged **missing controller-layer tests** — accepted
    as a TODO with a follow-up ticket.
  * Convention check: ``@RequestAttribute(USER) user: User`` is the
    canonical way to receive the authenticated user (no
    ``SecurityContextHolder`` calls in controllers).
  * Header-vs-body decision: ``cloud_id`` lives in
    ``atl-cloud-id`` header to match other Atlassian services; nudge type
    lives in body for extensibility.

* **Why it matters:** First user-facing REST surface. Set the API style
  the rest of the service inherits.

2.4 PR #100 — Async-task context propagation (commit ``2ea5f42``)
-------------------------------------------------------------------

* **Author:** Zhangbin Cheng
* **What:** Implemented ``AsyncTaskExecutionContext`` packaging (tenant,
  account, request id) into SQS message attributes; ``LoggingContext.addAsyncTaskContext()``
  on the consumer side rebuilds MDC.
* **Why it matters:** End-to-end log correlation across the
  WebServer→SQS→LongRun boundary. Without this, a Splunk search for one
  ``request_id`` would cut off at the HTTP-202 response.

2.5 PR #101 — Integration tests (commit ``52688e8``)
------------------------------------------------------

* **Author:** Michael Dawson
* **What:** Spring-context integration tests (``@SpringBootTest``) covering
  the SQS produce-then-consume round trip and the interceptor chain.
* **Why it matters:** The codebase now has a regression net for the
  ``WebServer`` ↔ ``LongRun`` JVM split.
* **Pattern enforced:** integration tests live alongside unit tests in
  ``src/test/kotlin/`` and use the same Gradle target — no separate
  ``intTest`` source set.

2.6 PR #103 — SQS visibility-extension (commit ``e2de3cc``) — 8× throughput
----------------------------------------------------------------------------

* **Author:** Zhangbin Cheng
* **What:** Introduced a per-message visibility-extension scheduler in
  ``RovoInsightsGenerationSqsQueueConsumer``. While a handler is running,
  the consumer periodically extends the message's SQS visibility timeout
  so it is not redelivered.
* **Quantified benefit (per PR description):** ~**8× throughput uplift**
  for long-running insight generations on a single LongRun pod.
* **Why it matters:** This is the single largest production-throughput PR
  in the history of the repo. It removes the visibility-timeout vs
  generation-time tension that previously forced the team to either
  oversize the timeout (slow redelivery on real failures) or undersize
  it (thrashing on slow generations).
* **Pattern made canonical:** all future long-running consumers should
  follow the visibility-extension pattern.

2.7 PR #105 — Nebulae staging config (commit ``febb7d1``)
-----------------------------------------------------------

* **Author:** Zhangbin Cheng
* **What:** Added ``nebulae.yml`` Nebulae plugin staging config so PAI
  has an isolated staging environment matching prod resource shapes.
* **Why it matters:** Unblocked safe canary rollouts of the Rovo-Insights
  handler when production logic ships.

2.8 PR #108 — MCP integration service setup (commit ``5c6e72c``)
------------------------------------------------------------------

* **Author:** Zhangbin Cheng
* **What:** Wired the Atlassian Integrations Service as an MCP server for
  Stratus agents. Added ``IntegrationServiceMcpServerConfig``,
  ``IntegrationServiceMcpSessionManager``, ``IntegrationServiceToolProvider``.
* **Why it matters:** Stratus agents in PAI can now reach Atlassian
  product tools (Jira / Confluence search, Rovo Insights tooling) via the
  standard MCP protocol — no per-tool integration code.
* **Architectural impact:** PAI is now an MCP **client**; the
  Integrations Service is the **server**. Future tool integrations
  flow through MCP discovery, not Spring beans.

3. Patterns observed in PR descriptions
==========================================

3.1 Conventions consistently followed
---------------------------------------

* **AIX ticket reference** in every meaningful PR title or body
  (``AIX-3296``, ``AIX-3259``, etc.).
* **"Approved-by" footer** in merge commits.
* **Test-coverage callouts** when controllers were added (PR #98) — the
  team self-flags coverage gaps openly.
* **Quantified benefit** in performance PRs (#103's "8× throughput" is
  exemplary; new perf PRs are expected to follow).

3.2 Conventions inconsistently followed
-----------------------------------------

* **Explicit test plan** — present in some PRs, missing in others. Reviewer
  expectation is moving toward "always include for non-trivial PRs".
* **Rollback plan** — rarely included; should be added for resource /
  topology / SQS-schema PRs.
* **End-to-end UX impact** — the workflow-pillar batch (T0a/T0b/T1/T2/R-1A/R-1B/L1/C2)
  in convo-ai-platform PR descriptions established the
  pattern of an **End-to-End UX Impact** section. PAI should adopt it for
  any PR that affects the proactive surfaces.

4. Top contributors (last 6 months)
======================================

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Contributor
     - Focus area
     - Signature PRs
   * - **Zhangbin Cheng**
     - Infrastructure & async pipeline
     - #96 Redis, #97 Async tasks, #100 Context propagation, #103 Visibility extension, #105 Nebulae, #108 MCP
   * - **Michael Dawson**
     - Controllers & integration tests
     - #98 Controllers, #101 Integration tests
   * - Annie Lieu / Bo Han / Morin Rodenski
     - Cross-team coordination + product
     - PRs co-authored with above

5. Quality / debt items called out by reviewers
==================================================

A small number of reviewer comments turned into known-good "we'll fix it" debt:

* **Controller-layer test coverage** — PR #98 reviewers flagged this. Today
  the integration tests in PR #101 cover happy-paths but unit-level
  controller tests still don't exist.
* **LaasLoggerFactory direct instantiation** — early reviewers caught one
  case where a class instantiated ``LoggerFactory.getLogger(...)`` directly
  instead of via ``LaasLoggerFactory``. Re-flagged whenever spotted.
* **Package mismatch** — at least one reviewer noted a file living in a
  package that didn't match its responsibility (e.g. helper code in
  ``feature/`` that should be in ``utility/``). Fixed case-by-case.

6. What the next 6 months are likely to add
=================================================

Based on the FY26 H2 plan (see :doc:`01-business-and-technical-goals` §5), expect:

* Real ``RovoInsightsGenerationTaskHandler`` — port from convo-ai with
  Stratus agent + Redis result write.
* Real ``NudgeThrottleController`` logic — TAP-trait integration + GASv3
  signal ingestion.
* Additional ``AsyncTask`` types for new proactive surfaces.
* SLO registration in Tome (latencies + reliability — see
  :doc:`01-business-and-technical-goals` §3 for planned targets).
* Likely a second SQS queue or a fan-out topology if multi-experience
  generation arrives.

7. How to contribute (heuristic, not policy)
================================================

1. Pick a ticket from the AIX board with a clear "this rolls up to the
   400K→1.5M OKR" framing.
2. Identify which package(s) you'll touch; cross-check the
   :doc:`/overviews/03-criticality-dashboard` for required reviewer count.
3. Write the PR description with: AIX ticket, what changed, **End-to-End
   UX Impact** section, test plan, rollback plan if non-trivial.
4. Quantify benefit if your PR is performance-related (follow PR #103's
   format).
5. Tag a feature owner + a platform owner if you cross the feature/platform
   boundary.
