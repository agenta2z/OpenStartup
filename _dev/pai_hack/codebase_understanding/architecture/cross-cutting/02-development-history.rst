.. _development-history:

============================================================
Development History — Proactive AI Platform
============================================================

:Document-ID: ARCH-CROSS-02
:Status: Living Document
:Created: 2026-05-17
:Data-Sources: Bitbucket merged PRs (140 total), PR review comments,
               Git commit history, codebase structural analysis
:Repository: ``atlassian/proactive-ai-platform``
:First-Commit: 2025-11-10
:Latest-Analyzed-PR: PR #140 (2026-05-16)

.. contents:: Table of Contents
   :depth: 3
   :local:

----

1. Pull Request Timeline
=========================

1.1 Repository Genesis (November 2025)
----------------------------------------

The ``proactive-ai-platform`` repository was created on **2025-11-10**
with an initial commit establishing the Atlassian Micros Spring Boot
service scaffold.

.. list-table:: Genesis Phase PRs
   :header-rows: 1
   :widths: 8 12 50 15 15

   * - PR
     - Date
     - Title / Purpose
     - Author
     - Comments
   * - #1
     - 2025-11-30
     - Make build green — initial CI/CD pipeline setup
     - Zhangbin Cheng
     - —
   * - #2
     - 2025-12-03
     - Fix deployment — resolve initial Micros deployment issues
     - Zhangbin Cheng
     - —
   * - #3
     - 2025-12-03
     - Fix team email — correct service ownership metadata
     - Zhangbin Cheng
     - —
   * - #4
     - 2025-12-07
     - SOX-compliant setup — enable compliance controls
     - Zhangbin Cheng
     - —
   * - #5
     - 2025-12-07
     - Quicker dev loop — optimize local development workflow
     - Zhangbin Cheng
     - —
   * - #6
     - 2025-12-09
     - POCO config — policy configuration for service access
     - Zhangbin Cheng
     - —
   * - #7
     - 2025-12-15
     - Convert to Kotlin — migrate from Java scaffold to Kotlin
     - Zhangbin Cheng
     - —

**Key Decision**: The team chose Kotlin over Java from the outset,
converting the standard Micros Java scaffold within the first month.
This decision aligned with the broader convo-ai team's Kotlin-first
approach and enabled full coroutine support.

1.2 Foundation Phase (December 2025 – January 2026)
-----------------------------------------------------

.. list-table:: Foundation Phase PRs
   :header-rows: 1
   :widths: 8 12 50 15 15

   * - PR
     - Date
     - Title / Purpose
     - Author
     - Comments
   * - #8
     - 2025-12-09
     - Update README — project documentation
     - Zhangbin Cheng
     - —
   * - #9
     - 2025-12-18
     - Setup logging — LAAS structured logging integration
     - Zhangbin Cheng
     - —
   * - #10
     - 2025-12-21
     - Statsig local mode — feature flag development support
     - Zhangbin Cheng
     - —
   * - #11
     - 2025-12-31
     - Feature service and tenant setup — multi-tenant foundation
     - Zhangbin Cheng
     - —
   * - #12
     - 2026-01-02
     - Use Statsig key — production feature gate configuration
     - Zhangbin Cheng
     - —

**Key Decision**: Feature gating was established very early (PR #10-12),
before any feature code was written. This "gates before features" approach
ensured safe rollout capability was baked into the platform from inception.

1.3 Core Platform Phase (January – April 2026)
------------------------------------------------

This phase saw the introduction of the major platform subsystems:

.. list-table:: Core Platform PRs (Selected Significant)
   :header-rows: 1
   :widths: 8 12 50 15 15

   * - PR
     - Date
     - Title / Purpose
     - Author
     - Comments
   * - ~#20-40
     - Jan-Feb
     - Interceptors, request context, logging extensions
     - Zhangbin Cheng
     - Multiple
   * - ~#40-60
     - Feb-Mar
     - SQS consumers, StreamHub integration, analytics events
     - Zhangbin Cheng
     - Multiple
   * - ~#60-80
     - Mar-Apr
     - Nudge types, throttle controller, AI Gateway setup
     - Zhangbin Cheng
     - Multiple
   * - #86
     - 2026-04-15
     - Rovo Dev coding standards — automated review setup
     - Rovo Dev (bot)
     - 1
   * - #88
     - Apr
     - Setup user context for requests (AIX-3251)
     - Zhangbin Cheng
     - —

1.4 Async Task Framework Phase (April – May 2026)
---------------------------------------------------

.. list-table:: Async Task Framework PRs
   :header-rows: 1
   :widths: 8 12 50 15 15

   * - PR
     - Date
     - Title / Purpose
     - Author
     - Comments
   * - #96
     - Apr-May
     - Setup Redis resource (AIX-3260)
     - Zhangbin Cheng
     - —
   * - #97
     - Apr-May
     - Setup async task handler (AIX-3259)
     - Zhangbin Cheng
     - —
   * - #98
     - Apr-May
     - Add controller and endpoints (AIX-3273/3274)
     - Michael Dawson
     - —
   * - #100
     - May
     - Task context propagation (AIX-3259)
     - Zhangbin Cheng
     - —
   * - #101
     - May
     - Add integration tests (AIX-3273/3274)
     - Michael Dawson
     - —
   * - #103
     - May
     - Add visibility-extending consumer (AIX-3259)
     - Zhangbin Cheng
     - —

**Key Decision**: The async task framework was designed from the start with
visibility extension to handle long-running AI generation tasks. The
``VisibilityExtendingSQSQueueConsumer`` prevents SQS message timeout during
multi-second LLM calls.

1.5 Production Readiness Phase (May 2026)
-------------------------------------------

.. list-table:: Production Readiness PRs
   :header-rows: 1
   :widths: 8 12 50 15 15

   * - PR
     - Date
     - Title / Purpose
     - Author
     - Comments
   * - #105
     - May
     - Update nebulae config (AIX-3312)
     - Michael Dawson
     - —
   * - #108
     - May
     - MCP with integration service (AIX-3296)
     - Zhangbin Cheng
     - —
   * - #109
     - May
     - Add stg_env_only run instructions
     - Morin Rodenski
     - —
   * - #116
     - May
     - Nebulae staging improvements
     - Michael Dawson
     - —
   * - #119
     - May
     - Refactor MCP integration service (AIX-3296)
     - Zhangbin Cheng
     - —
   * - #120
     - May
     - Async agent runner (AIX-3296)
     - Zhangbin Cheng
     - —
   * - #127
     - 2026-05-11
     - Add Redis services (AIX-3298)
     - Michael Dawson
     - 48
   * - #134
     - 2026-05-14
     - Introduce rollout service (AIX-3340)
     - Zhangbin Cheng
     - 6
   * - #138
     - 2026-05-15
     - Add staff access for endpoints (AIX-3332)
     - Zhangbin Cheng
     - 1
   * - #139
     - 2026-05-15
     - Fix Redis connection factory config (AIX-3345)
     - Zhangbin Cheng
     - 2
   * - #140
     - 2026-05-16
     - Log generation response (AIX-3332)
     - Zhangbin Cheng
     - 5

1.6 PR Volume and Velocity
----------------------------

.. list-table:: Monthly PR Velocity
   :header-rows: 1
   :widths: 20 15 15 25 25

   * - Month
     - Feature PRs
     - Bot/Renovate PRs
     - Total
     - Trend
   * - Nov 2025
     - 5
     - 0
     - 5
     - Repository genesis
   * - Dec 2025
     - 7
     - 0
     - 7
     - Foundation building
   * - Jan 2026
     - ~8
     - ~5
     - ~13
     - Core platform
   * - Feb 2026
     - ~10
     - ~8
     - ~18
     - SQS/Analytics
   * - Mar 2026
     - ~8
     - ~10
     - ~18
     - Feature build-out
   * - Apr 2026
     - ~10
     - ~12
     - ~22
     - Integration + cleanup
   * - May 2026
     - ~15
     - ~10
     - ~25
     - Production push

**Total merged PRs**: ~140 (as of PR #140, 2026-05-17)

**Renovate bot contribution**: Approximately 40-50% of total PRs are
automated dependency updates, indicating healthy dependency management
hygiene.

----

2. Key Milestones
==================

2.1 Milestone Timeline
------------------------

.. code-block:: text

   2025-11-10  ████ Repository created (initial commit)
   2025-11-30  ████ First PR merged — CI/CD pipeline green
   2025-12-07  ████ SOX compliance established
   2025-12-15  ████ Kotlin conversion complete
   2025-12-31  ████ Feature service + tenant context foundation
   2026-01-02  ████ Statsig feature gates production-ready
   2026-01~02  ████ Request interceptors + logging framework
   2026-02~03  ████ SQS consumers + StreamHub integration
   2026-03~04  ████ Nudge types + AI Gateway (Stratus) setup
   2026-04-15  ████ Rovo Dev automated code review standards
   2026-04~05  ████ Async task framework (AIX-3259)
   2026-05-11  ████ Redis services integration (AIX-3298)
   2026-05-14  ████ RolloutService migration begins (AIX-3340)
   2026-05-15  ████ Redis connection factory fix (AIX-3345)
   2026-05-15  ████ Staff access for prod Rovo Insights (AIX-3332)
   2026-05-16  ████ Generation response logging (AIX-3332)

2.2 Milestone Categories
--------------------------

**Infrastructure Milestones**:

- Repository creation and initial deployment (Nov 2025)
- SOX compliance (Dec 2025)
- Kotlin migration (Dec 2025)
- Gradle daemon enablement (May 2026)

**Feature Milestones**:

- Feature gating system (Dec 2025 – Jan 2026)
- SQS event processing pipeline (Feb – Mar 2026)
- Nudge type system (Mar – Apr 2026)
- Async task framework (Apr – May 2026)
- Rovo Insights pipeline (May 2026)
- Redis caching layer (May 2026)

**Operational Milestones**:

- Staging environment configuration (Apr – May 2026)
- Production staff access (May 2026)
- Nebulae deployment improvements (May 2026)

----

3. Architectural Evolution
===========================

3.1 Evolution Phases
---------------------

**Phase 1: Scaffold (Nov 2025)**

.. code-block:: text

   Standard Micros Spring Boot scaffold (Java)
   └── Basic health check endpoint
   └── Default Spinnaker pipeline
   └── SOX compliance configuration

**Phase 2: Foundation (Dec 2025 – Jan 2026)**

.. code-block:: text

   Kotlin + Spring Boot + Statsig
   ├── Feature gating (FeatureService)
   ├── Tenant context (TenantContext)
   ├── Structured logging (LAAS)
   ├── Request interceptors
   └── Metrics service

**Phase 3: Event-Driven Core (Feb – Mar 2026)**

.. code-block:: text

   + SQS Integration
   ├── StreamHub analytics event consumer
   ├── Analytics enriched event handler
   ├── Event AVI routing
   └── Message queue consumer middleware

**Phase 4: AI-Powered Features (Mar – Apr 2026)**

.. code-block:: text

   + AI Gateway + Nudge System
   ├── Stratus / AI Gateway integration
   │   ├── Agent builder (build/run pattern)
   │   ├── MCP integration service
   │   └── Tool provider framework
   ├── Nudge type taxonomy (10+ types)
   └── Nudge throttle controller

**Phase 5: Reliable Async Processing (Apr – May 2026)**

.. code-block:: text

   + Async Task Framework + Redis
   ├── AsyncTaskService (SQS-based)
   │   ├── Task dispatcher
   │   ├── Task handler registry
   │   ├── Context propagation via message attributes
   │   └── Visibility-extending consumer
   ├── Redis caching (RedisX)
   │   ├── Typed cache service
   │   └── Connection factory configuration
   └── Rovo Insights generation pipeline

**Phase 6: Production Hardening (May 2026 – Current)**

.. code-block:: text

   + Production Readiness
   ├── RolloutService (replacing FeatureService)
   ├── Staff access for production testing
   ├── Generation response logging
   ├── Redis connection factory fix
   └── SQS prefetch=0 restoration

3.2 Package Growth Timeline
-----------------------------

.. list-table:: Source Package Introduction Timeline
   :header-rows: 1
   :widths: 15 30 55

   * - Period
     - Package
     - Purpose
   * - Dec 2025
     - ``config``
     - Spring configuration (MVC security, environment)
   * - Dec 2025
     - ``context``
     - Tenant context models (CloudId, OrgId, Product)
   * - Dec 2025
     - ``featuregate``
     - Feature flag evaluation (Statsig)
   * - Jan 2026
     - ``service.metric``
     - Metrics service (Micrometer)
   * - Jan 2026
     - ``interceptor``
     - HTTP request context extraction
   * - Jan 2026
     - ``logging``
     - LAAS structured logging, UGC safety
   * - Jan 2026
     - ``requestcontext``
     - Request-scoped value management
   * - Feb 2026
     - ``sqs``
     - SQS consumers, StreamHub events
   * - Feb 2026
     - ``client``
     - HTTP client commons, audiences
   * - Mar 2026
     - ``feature.nudge``
     - Nudge types and throttle control
   * - Mar 2026
     - ``stratus``
     - AI Gateway integration, MCP
   * - Apr 2026
     - ``task``
     - Async task framework
   * - Apr 2026
     - ``utility``
     - Threading, tenant, user utilities
   * - May 2026
     - ``feature.rovoinsights``
     - Rovo Insights generation pipeline
   * - May 2026
     - ``exception``
     - REST client exceptions

----

4. Decision Provenance
=======================

4.1 Architectural Decision Record
-----------------------------------

.. list-table:: Key Architectural Decisions
   :header-rows: 1
   :widths: 8 15 35 25 17

   * - ADR
     - Decision
     - Rationale
     - Evidence
     - Date
   * - ADR-001
     - Kotlin over Java
     - Coroutine support, convo-ai alignment, conciseness
     - PR #7 (convert to Kotlin)
     - Dec 2025
   * - ADR-002
     - Gates before features
     - Ensure safe rollout from day one; avoid retrofitting
     - PR #10, #11, #12
     - Dec 2025
   * - ADR-003
     - SQS for async processing
     - Decouple HTTP from long-running AI tasks; at-least-once delivery
     - ``AnalyticsEventsSqsQueueConsumer``
     - Feb 2026
   * - ADR-004
     - Interface/internal pattern
     - Clean API boundaries; enable implementation swapping
     - PR #127 review comment
     - May 2026
   * - ADR-005
     - Visibility-extending SQS consumer
     - Prevent message redelivery during 30+ second AI generations
     - PR #103 (AIX-3259)
     - May 2026
   * - ADR-006
     - Redis via RedisX (not localhost)
     - Managed cache service; avoid auto-configured localhost fallback
     - PR #139 (AIX-3345)
     - May 2026
   * - ADR-007
     - RolloutService over FeatureService
     - Alignment with convo-ai; support dynamic config and metrics
     - PR #134 (AIX-3340)
     - May 2026
   * - ADR-008
     - Multi-model AI Gateway
     - Flexibility when models have availability/rate issues
     - PR #134 review discussion
     - May 2026
   * - ADR-009
     - SQS prefetch=0
     - Prevent over-fetching messages; one-at-a-time processing
     - Commit ``e98b0c4``
     - May 2026

4.2 Decision Detail: Kotlin Over Java (ADR-001)
-------------------------------------------------

**Context**: The Micros scaffold generated a Java-based Spring Boot service.
The team converted to Kotlin within the first month.

**Decision**: Full Kotlin conversion (PR #7, December 2025).

**Rationale**:

1. Kotlin coroutines provide first-class non-blocking I/O support,
   critical for AI Gateway streaming responses
2. The parent ``convo-ai`` service uses Kotlin, enabling code sharing
3. Kotlin data classes simplify DTO definitions (context models, DTOs)
4. Null safety reduces NullPointerException risk in multi-tenant code

4.3 Decision Detail: RolloutService Migration (ADR-007)
---------------------------------------------------------

**Context**: The original ``FeatureService`` provided basic Statsig gate
checks. The convo-ai team developed a more capable ``RolloutService``
with dynamic config, metrics, and controlled stage support.

**Decision**: Adopt ``RolloutService`` from convo-ai (PR #134, May 2026).

**Rationale** (from PR description):

    "Introduce rollout service from convo-ai (currently with only the
    essential gate methods), this replace the existing feature service.
    We will add more support going forward (e.g. dynamic config) and metrics"

**Review discussion** (Morin Rodenski → Zhangbin Cheng):

    Q: "We have more instance of the featureService in the code — is this
    PR intending to replace all of them?"

    A: "Good point, it is backward compatible, so will handle the
    replacement in another PR"

**Status**: Partial migration. ``RolloutService`` is introduced alongside
``FeatureService``; full replacement deferred to follow-up PR.

4.4 Decision Detail: Redis Connection Factory Fix (ADR-006)
-------------------------------------------------------------

**Context**: After adding Redis services (PR #127), deployments failed
because Spring Boot Actuator's health check used an auto-configured
``redisConnectionFactory`` pointing to ``localhost:6379`` instead of the
RedisX instance configured in ``application.yml``.

**Decision**: Fix the connection factory to use the interface that extends
both reactive and non-reactive Redis connection factories (PR #139).

**Root cause** (from PR #139 description):

    "The deployment is failing because Spring Boot Actuator is running a
    Redis health check against an auto-configured Redis connection pointing
    to localhost:6379, not the remote RedisX cache instance"

**Impact**: Deployment failure in staging (deep check returned 503).

**Resolution**: Changed to use the unified connection factory interface,
ensuring both reactive and non-reactive Redis paths connect to RedisX.

----

5. Review Patterns
===================

5.1 Code Review Culture
-------------------------

Analysis of PR review comments reveals several consistent patterns:

**Architecture-First Reviews**

Reviewers focus on architectural consistency over implementation details:

- *"Can we put the implementation into /internal directory"* (PR #127)
- *"We don't have SPI folder"* (PR #127)
- *"RolloutServiceImpl should be marked internal"* (PR #134, Rovo Dev)

**Scope-Conscious Development**

Teams explicitly manage PR scope boundaries:

- *"Do we need this for now?"* (PR #127, questioning unnecessary complexity)
- *"Will handle the replacement in another PR"* (PR #134, deferring
  full migration)

**Operational Awareness**

Reviewers consider production implications:

- *"Is this change intentional? BTW gemini 3 pro wasn't working for me"*
  (PR #134, flagging model availability issues)
- *"We have more instance of the featureService in the code"* (PR #134,
  tracking migration completeness)

**Naming Consistency**

Terminology standardization is actively managed:

- *"Given we are using cloudId and tenantId interchangeably, we'll
  probably stick with just one of them"* (PR #127)

5.2 Review Metrics
--------------------

.. list-table:: Review Activity Summary
   :header-rows: 1
   :widths: 15 15 20 25 25

   * - PR
     - Comments
     - Reviewers
     - Key Theme
     - Resolution
   * - #127
     - 48
     - Zhangbin Cheng (reviewer)
     - Architecture patterns, Redis design
     - Simplified; moved to /internal
   * - #134
     - 6
     - Morin Rodenski, Rovo Dev
     - Migration scope, model selection
     - Deferred full migration
   * - #139
     - 2
     - —
     - Deployment fix
     - Merged quickly
   * - #138
     - 1
     - —
     - Staff access
     - Merged quickly
   * - #140
     - 5
     - —
     - Debug logging
     - Merged

**Observation**: High-comment PRs (#127 with 48 comments) correlate with
foundational infrastructure changes. Feature PRs and operational fixes
receive lighter review, suggesting team trust in established patterns.

5.3 Automated Review Integration
----------------------------------

The team adopted **Rovo Dev** automated code reviews in April 2026 (PR #86).
Rovo Dev contributions include:

- Custom coding standards file (``.rovodev/.review-agent.md``)
- Inline code suggestions (e.g., marking ``RolloutServiceImpl`` as
  ``internal`` in PR #134)
- Architecture-aware feedback based on repository-specific patterns

**SonarQube Integration**: Every PR receives automated SonarQube analysis:

- Quality gate checks (reliability, security, maintainability, coverage)
- Coverage tracking with per-PR new code coverage
- Estimated post-merge coverage impact

----

6. Contributors
================

6.1 Core Team
--------------

.. list-table:: Core Contributors
   :header-rows: 1
   :widths: 25 20 30 25

   * - Name
     - Role (Inferred)
     - Key Contributions
     - Active Period
   * - Zhangbin Cheng
     - Tech Lead / Primary Developer
     - Repository creation, Kotlin conversion, all core subsystems,
       feature gating, SQS, AI Gateway, Rovo Insights
     - Nov 2025 – Present
   * - Michael Dawson
     - Platform Engineer
     - Redis services, controller endpoints, integration tests,
       nebulae config, deployment improvements
     - May 2026 – Present
   * - Morin Rodenski
     - Team Member
     - Staging instructions, Renovate approvals, code reviews,
       operational feedback
     - Apr 2026 – Present

6.2 Automated Contributors
----------------------------

.. list-table:: Bot Contributors
   :header-rows: 1
   :widths: 25 35 40

   * - Bot
     - Purpose
     - Volume
   * - Renovate Bot
     - Automated dependency updates
     - ~50 PRs (40-50% of total)
   * - Rovo Dev
     - Automated code review + coding standards
     - PR #86 + inline review comments
   * - SonarQube Bot
     - Code quality analysis
     - Comments on every PR

6.3 Contribution Distribution
-------------------------------

.. code-block:: text

   Zhangbin Cheng    ████████████████████████████████████████  ~70%
   Michael Dawson    ████████████                              ~15%
   Morin Rodenski    ██████                                    ~8%
   Renovate Bot      ████████████████████                      (auto)
   Rovo Dev          ██                                        (auto)

----

7. Technical Debt Origin
=========================

7.1 Debt Introduction Timeline
-------------------------------

.. list-table:: Technical Debt Origin Tracking
   :header-rows: 1
   :widths: 10 20 25 25 20

   * - ID
     - Debt Item
     - Introduced By
     - Root Cause
     - Status
   * - TD-001
     - Dual tenant ID usage
     - PR #127
     - Ported pattern from convo-ai without simplification
     - Open
   * - TD-002
     - Incomplete FeatureService migration
     - PR #134
     - Intentionally deferred to manage PR scope
     - In Progress
   * - TD-003
     - Redis key prefix complexity
     - PR #127
     - Over-engineered pattern from convo-ai
     - Open
   * - TD-004
     - Hardcoded LLM model
     - Original AI Gateway integration
     - Dynamic config not yet available via RolloutService
     - Planned
   * - TD-005
     - SQS prefetch deletion
     - PR #68
     - False assumption about default behavior
     - Fixed (``e98b0c4``)
   * - TD-006
     - Test coverage gaps
     - PR #127
     - New Redis code had 54.3% coverage
     - Open
   * - TD-007
     - Missing SPI convention
     - PR #127
     - Different organizational convention than convo-ai
     - Open

7.2 Debt Patterns
------------------

**Pattern 1: convo-ai Port Overhead**

Several debt items (TD-001, TD-003, TD-007) originate from porting code
patterns from the larger ``convo-ai`` service without simplifying for
proactive-ai's smaller scope. Michael Dawson acknowledged this in PR #127:

    "Can probably reduce the sprawl of this logic as we don't need anything
    as complex as was necessary in convo ai"

**Pattern 2: Scope-Managed Deferral**

TD-002 (FeatureService migration) was intentionally deferred to keep PR
scope manageable. This is a healthy pattern when tracked and followed up,
but creates debt if follow-up PRs are not prioritized.

**Pattern 3: Configuration Assumptions**

TD-005 (SQS prefetch) was caused by an incorrect assumption about SQS
default behavior, leading to a regression that required explicit restoration.
This highlights the risk of removing configuration "overrides" that appear
redundant but serve important purposes.

----

8. Lessons Learned
===================

8.1 What Worked Well
---------------------

1. **Kotlin-First from Day One**

   Converting to Kotlin in PR #7 (within the first month) paid dividends
   throughout development. Coroutines enabled clean async code in the
   task framework and AI Gateway integration without callback complexity.

2. **Gates Before Features**

   Establishing feature gating (PRs #10-12) before writing feature code
   ensured every subsequent feature had safe rollout capability built in.
   The later migration to RolloutService (PR #134) was backward-compatible
   because the pattern was established early.

3. **convo-ai Pattern Reuse**

   Leveraging proven patterns from convo-ai (rollout service, Redis cache,
   async task framework) accelerated development significantly. The team
   was able to build the complete platform in ~6 months.

4. **Automated Dependency Management**

   Renovate bot handling ~50% of PRs freed developers to focus on feature
   work while keeping dependencies current and secure.

5. **Interface/Internal Convention**

   The ``/internal`` directory pattern, enforced through code review,
   created clean API boundaries that made the RolloutService migration
   possible without breaking consumers.

8.2 What Could Be Improved
----------------------------

1. **Simplify convo-ai Ports**

   Code ported from convo-ai should be simplified for proactive-ai's
   smaller scope before merging. The Redis key prefix complexity and
   dual tenant ID usage are examples of unnecessary complexity.

2. **Configuration Documentation**

   The SQS prefetch=0 regression (PR #68 → fix in commit ``e98b0c4``)
   shows the need for documenting *why* configuration values are set,
   not just *what* they are. ADR-style comments in configuration files
   would prevent similar regressions.

3. **Test Coverage for Infrastructure**

   The SonarQube gate failure on PR #127 (54.3% new coverage) indicates
   infrastructure code is harder to test well. Consider integration test
   patterns or test fixtures for Redis and SQS code.

4. **LLM Model Availability Planning**

   The Gemini 2.5 Pro issues and 100K TPM GPT-4o-mini limit (PR #134
   discussion) suggest the need for proactive model capacity planning
   and dynamic fallback configuration.

5. **Deployment Validation**

   The Redis connection factory issue (PR #139) that caused staging
   deployment failure highlights the importance of pre-deployment
   validation beyond unit tests. Consider adding deployment smoke tests
   that verify external service connectivity.

8.3 Risk Observations
-----------------------

.. list-table:: Development Risk Observations
   :header-rows: 1
   :widths: 15 35 25 25

   * - Risk
     - Description
     - Mitigation
     - Status
   * - Bus Factor
     - Zhangbin Cheng is author of ~70% of code; single-point-of-knowledge
       risk for core subsystems
     - Michael Dawson and Morin Rodenski ramping up
     - Active
   * - convo-ai Divergence
     - Ported patterns may diverge from convo-ai upstream changes
     - Regular alignment reviews needed
     - Monitor
   * - LLM Availability
     - Dependence on specific LLM models with rate limits
     - Dynamic config for model switching
     - In Progress
   * - Test Debt
     - ~64% coverage may hide bugs in edge cases
     - Coverage improvement OKR needed
     - Open
   * - Configuration Fragility
     - Config changes can break deployments (Redis, SQS prefetch)
     - Integration test + deployment smoke tests
     - Open

----

Appendix A: Jira Issue Cross-Reference
========================================

.. list-table:: AIX Issues Referenced in PRs
   :header-rows: 1
   :widths: 15 40 25 20

   * - Issue Key
     - Description (Inferred from PR)
     - PRs
     - Status
   * - AIX-2605
     - Initial service setup and deployment
     - #1, #2, #3, #4, #5
     - Done
   * - AIX-2689
     - Convert to Kotlin
     - #7
     - Done
   * - AIX-2690
     - POCO configuration
     - #6
     - Done
   * - AIX-2773
     - Logging setup
     - #9, #10
     - Done
   * - AIX-2791
     - Feature service and tenant setup
     - #11
     - Done
   * - AIX-2806
     - Statsig key configuration
     - #12
     - Done
   * - AIX-3251
     - User context for requests
     - #88
     - Done
   * - AIX-3259
     - Async task framework
     - #97, #100, #103
     - Done
   * - AIX-3260
     - Redis resource setup
     - #96
     - Done
   * - AIX-3273/3274
     - Controller and endpoints
     - #98, #101
     - Done
   * - AIX-3296
     - MCP integration service
     - #108, #119, #120
     - Done
   * - AIX-3298
     - Redis services
     - #127
     - Done
   * - AIX-3312
     - Nebulae config update
     - #105
     - Done
   * - AIX-3332
     - Rovo Insights production access
     - #138, #140
     - Done
   * - AIX-3340
     - Rollout service
     - #134
     - In Progress
   * - AIX-3345
     - Redis connection factory fix
     - #139
     - Done

Appendix B: PR Comment Themes
===============================

Analysis of code review comments across significant PRs reveals
these recurring themes:

.. list-table:: Review Comment Theme Distribution
   :header-rows: 1
   :widths: 30 15 55

   * - Theme
     - Frequency
     - Example
   * - Architecture patterns
     - High
     - "Put implementation into /internal directory"
   * - Scope management
     - High
     - "Do we need this for now?"
   * - Naming consistency
     - Medium
     - "Using cloudId and tenantId interchangeably"
   * - convo-ai alignment
     - Medium
     - "Reduce sprawl as we don't need anything as complex"
   * - Operational concerns
     - Medium
     - "Gemini 3 pro wasn't working for me"
   * - Code quality
     - Low
     - SonarQube automated reports
   * - Security
     - Low
     - SLAuth access control patterns
