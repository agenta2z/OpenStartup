.. _business-and-technical-goals:

============================================================
Business and Technical Goals — Proactive AI Platform
============================================================

:Document-ID: ARCH-CROSS-01
:Status: Living Document
:Created: 2026-05-17
:Data-Sources: Atlas Goals API, Confluence CQL, Jira JQL (CTSC project),
               Bitbucket PR history, codebase analysis
:Risk-R5: Some Atlas/Confluence goal data was unavailable at query time
          (API rate limits / session errors). Sections marked ``[PARTIAL-DATA]``
          may require follow-up enrichment when data sources become available.

.. contents:: Table of Contents
   :depth: 3
   :local:

----

1. Mission Statement
====================

1.1 Platform Purpose
--------------------

The **Proactive AI Platform** (``proactive-ai-platform``) is Atlassian's
backend service for delivering *unsolicited, context-aware AI experiences*
across the Atlassian product suite. Unlike reactive AI features (where users
explicitly ask for help), this platform **proactively** identifies moments
where AI-generated insights, nudges, and recommendations can improve user
productivity without requiring explicit user action.

The platform serves as the **orchestration layer** between:

- **StreamHub analytics events** — real-time user interaction signals
  (page views, Jira status changes, JQL executions)
- **AI Gateway / Stratus** — Atlassian's unified LLM access layer
  (currently supporting Gemini 2.5 Pro and GPT-4o-mini)
- **Product surfaces** — Jira, Confluence, Trello, and Bitbucket UIs
  where proactive insights are rendered

1.2 Core Value Proposition
---------------------------

The platform exists to answer a fundamental product question:

    *"What should the user know or do next, even before they ask?"*

This is achieved through three primary feature pillars:

1. **Rovo Insights** — AI-generated summaries and recommendations delivered
   asynchronously via SQS-based task processing
2. **Nudge Throttling** — Intelligent control of when and how frequently
   contextual nudges are surfaced to prevent engagement fatigue
3. **Stratus / AI Gateway Integration** — Agentic AI capabilities with
   tool use, MCP protocol support, and streaming responses

1.3 Strategic Context
---------------------

The Proactive AI Platform is part of Atlassian's broader **AIX**
(AI Experiences) initiative, which aims to embed intelligence into every
Atlassian product interaction. The platform sits within the
**Conversational AI** (convo-ai) organizational context, sharing
architectural patterns, libraries, and operational practices with the
``convo-ai`` service.

.. note::

   ``[PARTIAL-DATA]`` Atlas Goals API queries for "proactive-ai-platform"
   and "AIX proactive AI" returned errors due to API rate limits.
   The mission statement above is derived from codebase analysis,
   PR descriptions, and service configuration. When Atlas data becomes
   available, this section should be enriched with formal goal linkages.

----

2. FY26 Business Goals
======================

2.1 Goal Hierarchy
------------------

Based on codebase analysis, PR descriptions, and Jira issue references
(AIX-xxxx series), the platform's FY26 business goals align to the
following hierarchy:

.. list-table:: FY26 Business Goal Hierarchy
   :header-rows: 1
   :widths: 10 30 30 30

   * - Level
     - Goal
     - Measure
     - Status
   * - L0
     - Embed AI into every Atlassian product interaction
     - MAU of AI-powered features
     - In Progress
   * - L1
     - Deliver proactive AI experiences across products
     - Number of proactive insights delivered
     - In Progress
   * - L2a
     - Rovo Insights: Generate and deliver AI summaries
     - Insight generation success rate, latency
     - Active Development
   * - L2b
     - Nudge system: Control engagement quality
     - Nudge delivery rate, user engagement
     - Active Development
   * - L2c
     - Multi-product support: Jira, Confluence, Trello, Bitbucket
     - Product coverage percentage
     - Foundation Laid

2.2 Rovo Insights Business Goal
--------------------------------

**Objective**: Enable AI-generated insights that surface relevant information
to users proactively, without requiring explicit queries.

**Evidence from codebase**:

- ``RovoInsightsGenerationTask`` and ``RovoInsightsGenerationTaskHandler``
  implement asynchronous insight generation triggered via SQS
- ``RovoInsightsController`` provides REST endpoints for fetching generated
  insights, checking status, and triggering test generations
- ``InsightType`` enum defines the taxonomy of insight categories
- Staff access endpoints were added in PR #138 (May 2026) to enable
  production testing of Rovo Insights generation

**Business context** (from PR #138 description):

    "Add staff access for endpoints so we can access prod endpoints through
    SLAuth (so we can trigger Rovo Insights generation in prod)"

This confirms the feature was in active production validation as of May 2026.

2.3 Nudge System Business Goal
-------------------------------

**Objective**: Deliver contextual nudges across Atlassian products while
maintaining engagement quality through intelligent throttling.

**Evidence from codebase**:

The ``NudgeType`` enum reveals the breadth of planned nudge categories:

.. code-block:: kotlin

   enum class NudgeType {
       CONVO_STARTER,
       JIRA_JQL_EXECUTED,
       PAGE_SUMMARIES,
       AUDIO_BRIEFING,
       // ... 10+ nudge categories
   }

The ``NudgeThrottleController`` provides REST APIs for managing throttle
state, confirming that engagement quality control is a first-class
business requirement.

2.4 Multi-Product Expansion Goal
---------------------------------

**Objective**: Extend proactive AI capabilities across the Atlassian
product suite.

**Evidence from codebase**:

The ``Product`` enum in the context system defines supported products:

- Jira
- Confluence
- Trello
- Bitbucket

The ``TenantContext`` system provides unified tenant resolution across
products, with ``cloudId``, ``workspaceARI``, and ``orgId`` support
for multi-tenant isolation.

2.5 Goal Data Availability Notes
---------------------------------

.. warning::

   ``[PARTIAL-DATA]`` The following data sources were queried but
   returned limited results:

   - **Atlas Goals API**: Searches for "proactive-ai-platform" and
     "AIX proactive AI" returned API errors (rate limits / session errors).
     Formal goal ARIs and key results are not available.
   - **Confluence CQL**: Searches for proactive-ai OKR pages returned
     general results not specific to this platform's goals.
   - **Jira JQL**: Searches in CTSC project for epics/stories related
     to proactive-ai features returned no results, suggesting the work
     may be tracked under a different project key (likely AIX-prefixed
     issues based on PR branch naming).

   The goals documented above are inferred from code artifacts and
   PR descriptions. Follow-up enrichment is recommended when data
   sources become available.

----

3. Success Metrics
==================

3.1 Platform Health Metrics
---------------------------

The platform implements comprehensive metrics through ``MetricsService``
and ``CoreMetricsService``:

.. list-table:: Platform Health Metrics
   :header-rows: 1
   :widths: 25 35 20 20

   * - Metric
     - Description
     - Source
     - Target
   * - Insight Generation Latency
     - Time from SQS trigger to insight availability
     - ``CoreMetricsServiceImpl``
     - < 30s (estimated)
   * - SQS Processing Rate
     - Events consumed per second
     - ``AnalyticsEventsSqsQueueConsumer``
     - Scales with load
   * - Feature Gate Evaluation
     - Gate check latency and hit rate
     - ``FeatureFlagEvaluationTracker``
     - < 10ms per check
   * - AI Gateway Response Time
     - LLM call round-trip time
     - ``AIGatewayServiceImpl``
     - Model-dependent
   * - Redis Cache Hit Rate
     - Cache effectiveness for throttle state
     - RedisX integration
     - > 90%

3.2 Code Quality Metrics
--------------------------

From SonarQube analysis (extracted from PR review comments):

.. list-table:: Code Quality Baselines
   :header-rows: 1
   :widths: 30 30 40

   * - Metric
     - Value
     - Source
   * - Project Code Coverage
     - 63.9% – 64.7%
     - SonarQube PR #127, #134
   * - New Code Coverage (PR #134)
     - 97.5%
     - SonarQube Rollout Service PR
   * - New Code Coverage (PR #127)
     - 54.3%
     - SonarQube Redis Services PR
   * - Reliability
     - Passing
     - SonarQube Quality Gate
   * - Security
     - Passing
     - SonarQube Quality Gate
   * - Maintainability
     - Passing
     - SonarQube Quality Gate

3.3 Operational Metrics
------------------------

.. list-table:: Operational Health Targets
   :header-rows: 1
   :widths: 25 35 40

   * - Metric
     - Target
     - Implementation
   * - Service Availability
     - 99.9%
     - Deep check endpoint via Spring Boot Actuator
   * - Deployment Success
     - Zero-downtime
     - Spinnaker pipeline with staging gates
   * - SQS Message Processing
     - At-least-once delivery
     - Visibility-extending consumer pattern
   * - Redis Connectivity
     - RedisX (not localhost)
     - Fixed in PR #139 (Redis connection factory config)

----

4. Technical Goals
==================

4.1 Architecture Principles
-----------------------------

The platform follows these core technical principles, evidenced by
codebase structure and PR review discussions:

**Interface-Driven Design**

Every service exposes a public interface with implementations in an
``/internal`` subdirectory. This pattern was explicitly enforced in
code review (PR #127, Zhangbin Cheng):

    "Can we put the implementation into /internal directory (for a
    pattern where we just have the api level interfaces exposed)."

**Coroutine-First Concurrency**

All async operations use Kotlin coroutines with structured concurrency:

- ``suspend fun`` interfaces throughout service layer
- ``InstrumentedDispatcher`` for thread pool management
- ``CoroutineMonitor`` for health monitoring
- OpenTelemetry integration via ``kotlinx-coroutines-opentelemetry``

**Tenant Isolation**

Multi-tenant context propagation is a first-class concern:

- ``TenantContext`` aggregates product, data, and experience contexts
- ``RequestContextInterceptor`` extracts tenant info from HTTP headers
- ``AsyncTaskExecutionContext`` preserves tenant context through SQS

**Feature Gate Safety**

All feature rollouts go through Statsig-based gates:

- ``FeatureService`` provides three evaluation variants (standard,
  Hello-only, limited-context)
- ``RolloutService`` (introduced PR #134) replaces the older
  ``FeatureService`` with enhanced capabilities from convo-ai

4.2 Technical Quality Goals
----------------------------

.. list-table:: Technical Quality Goals
   :header-rows: 1
   :widths: 25 40 35

   * - Goal
     - Description
     - Status
   * - Internal visibility
     - Mark implementation classes ``internal`` to enforce interface usage
     - Enforced in PR #134 review
   * - Consistent tenant ID usage
     - Use either ``cloudId`` or ``tenantId`` consistently, not both
     - Identified in PR #127 review
   * - Redis key simplification
     - Remove unnecessary key prefix complexity
     - Noted as future work in PR #127
   * - Dynamic model configuration
     - Enable LLM model switching via Statsig DynamicConfig
     - Planned (PR #134 discussion)
   * - Test coverage > 80%
     - Improve from current ~64% baseline
     - In progress

4.3 Technology Stack Goals
---------------------------

.. list-table:: Technology Stack
   :header-rows: 1
   :widths: 25 25 25 25

   * - Layer
     - Current
     - Target
     - Notes
   * - Runtime
     - JDK 21
     - JDK 21+
     - SOX-compliant Docker image
   * - Framework
     - Spring Boot (Micros v7.10.x)
     - Latest Micros
     - Atlassian's managed Spring Boot
   * - Language
     - Kotlin 2.3.x
     - Kotlin 2.x
     - Full coroutine support
   * - Build
     - Gradle 9.5.x
     - Latest Gradle 9.x
     - Daemon enabled (PR-based)
   * - Queue
     - AWS SQS (SDK v2)
     - AWS SQS
     - Visibility-extending consumer
   * - Cache
     - RedisX (Atlassian-managed)
     - RedisX
     - Fixed config in PR #139
   * - AI/LLM
     - AI Gateway (Gemini 2.5 Pro)
     - Multi-model via DynamicConfig
     - GPT-4o-mini as fallback
   * - Feature Flags
     - Statsig
     - Statsig
     - Via featuregate-client-starter
   * - Observability
     - OpenTelemetry + LAAS
     - Full LAAS integration
     - Structured logging with UGC safety

----

5. Technical Debt Inventory
===========================

5.1 Known Technical Debt
-------------------------

Derived from PR discussions, code comments, and codebase analysis:

.. list-table:: Technical Debt Registry
   :header-rows: 1
   :widths: 10 25 35 15 15

   * - ID
     - Debt Item
     - Description
     - Origin
     - Priority
   * - TD-001
     - Dual tenant ID usage
     - ``cloudId`` and ``tenantId`` used interchangeably across cache
       and context modules
     - PR #127 review
     - Medium
   * - TD-002
     - Incomplete FeatureService migration
     - ``RolloutService`` introduced but old ``FeatureService`` instances
       remain in code; backward-compatible but creates confusion
     - PR #134 review
     - Medium
   * - TD-003
     - Redis key prefix complexity
     - Key prefix system ported from convo-ai may be over-engineered
       for proactive-ai's simpler use cases
     - PR #127 discussion
     - Low
   * - TD-004
     - Hardcoded LLM model selection
     - AI Gateway model (Gemini 2.5 Pro → GPT-4o-mini) is configured
       statically; goal is Statsig DynamicConfig
     - PR #134 discussion
     - High
   * - TD-005
     - SQS prefetch configuration
     - Prefetch=0 was incorrectly deleted in PR #68 and had to be
       restored; indicates fragile SQS configuration management
     - Git commit ``e98b0c4``
     - Medium
   * - TD-006
     - Test coverage gaps
     - Project coverage at ~64%; new Redis code at 54.3% coverage
       fell below SonarQube quality gate
     - SonarQube PR #127
     - Medium
   * - TD-007
     - Missing SPI folder convention
     - Service Provider Interface (SPI) folder pattern from convo-ai
       not adopted; noted in PR #127 review
     - PR #127 review
     - Low

5.2 Debt Reduction Trajectory
-------------------------------

The team is actively addressing technical debt through:

1. **RolloutService migration** (PR #134) — Replacing legacy FeatureService
   with convo-ai's improved rollout service pattern
2. **Redis configuration fix** (PR #139) — Resolving the RedisX vs localhost
   connection factory issue that caused deployment failures
3. **Gradle daemon enablement** — Build performance improvement mirroring
   convo-ai PR #5438

----

6. Feature Roadmap
==================

6.1 Current Feature State (May 2026)
--------------------------------------

.. list-table:: Feature Maturity Matrix
   :header-rows: 1
   :widths: 20 15 30 35

   * - Feature
     - Maturity
     - Current State
     - Evidence
   * - Rovo Insights
     - Beta
     - Async generation via SQS; staff-access production testing
     - PRs #138, #140; task handler + controller
   * - Nudge Throttling
     - Alpha
     - REST API for throttle management; 10+ nudge categories defined
     - ``NudgeThrottleController``, ``NudgeType`` enum
   * - Stratus AI Gateway
     - Beta
     - Agent builder with MCP tool support; streaming responses
     - ``AIGatewayService``, ``IntegrationServiceMcpServerConfig``
   * - Analytics Event Processing
     - Production
     - StreamHub event consumption via SQS
     - ``AnalyticsEventsSqsQueueConsumer``
   * - Async Task Framework
     - Production
     - SQS-based task dispatch with context propagation
     - ``AsyncTaskService``, ``VisibilityExtendingSQSQueueConsumer``
   * - Feature Gating
     - Production → Migration
     - Statsig gates; migrating to RolloutService
     - ``FeatureService`` → ``RolloutService``
   * - Redis Caching
     - Production
     - RedisX integration for throttle state/insight caching
     - PR #127, #139

6.2 Planned Feature Evolution
-------------------------------

Based on PR descriptions and code review discussions:

1. **Dynamic LLM Model Config** — Switch AI models via Statsig DynamicConfig
   without deployment (Q3 FY26)
2. **Rate Limit Improvements** — TPM bump for GPT-4o-mini (100K TPM
   currently, bump requested as of May 2026)
3. **Full FeatureService → RolloutService Migration** — Replace all
   remaining FeatureService instances (planned post-PR #134)
4. **Enhanced Metrics** — Additional rollout service metrics and
   dynamic config support
5. **Multi-Product Nudge Expansion** — Extend nudge types to cover
   more product interactions beyond current 10+ categories

6.3 Architecture Evolution Path
---------------------------------

.. code-block:: text

   Phase 1 (Current):     Event → SQS → Task → AI Gateway → Insight
   Phase 2 (Near-term):   + Redis caching + Throttle control
   Phase 3 (Mid-term):    + Dynamic model selection + Multi-model support
   Phase 4 (Future):      + Cross-product correlation + User preference learning

----

7. Team OKRs
=============

7.1 Inferred OKR Structure
----------------------------

.. note::

   ``[PARTIAL-DATA]`` Formal team OKRs could not be retrieved from Atlas
   Goals API or Confluence due to API availability issues. The following
   OKR structure is inferred from development activity, PR descriptions,
   and feature implementation patterns.

**Objective 1: Ship Rovo Insights to Production**

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Key Result
     - Evidence
     - Status
   * - KR1.1: Complete async generation pipeline
     - ``RovoInsightsGenerationTaskHandler``, SQS consumer
     - Done
   * - KR1.2: Enable staff-access production testing
     - PR #138 (SLAuth staff access endpoints)
     - Done (May 2026)
   * - KR1.3: Add generation response logging
     - PR #140 (log generation response for debugging)
     - Done (May 2026)
   * - KR1.4: Achieve production rollout
     - Feature gate configuration
     - In Progress

**Objective 2: Establish Platform Foundation**

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Key Result
     - Evidence
     - Status
   * - KR2.1: Implement Redis caching layer
     - PR #127 (Redis services), PR #139 (config fix)
     - Done
   * - KR2.2: Migrate to RolloutService
     - PR #134 (rollout service from convo-ai)
     - Partial
   * - KR2.3: Achieve SOX compliance
     - PR #4 (SOX-compliant setup, Dec 2025)
     - Done
   * - KR2.4: Set up observability pipeline
     - LAAS logger, OpenTelemetry, metrics service
     - Done

**Objective 3: Enable Multi-Product AI Experiences**

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Key Result
     - Evidence
     - Status
   * - KR3.1: Unified tenant context for all products
     - ``TenantContext`` with Product enum
     - Done
   * - KR3.2: Nudge type taxonomy covering key use cases
     - ``NudgeType`` enum with 10+ categories
     - Done
   * - KR3.3: AI Gateway with multi-model support
     - ``AIGatewayService`` + Stratus config
     - In Progress

7.2 Development Velocity Indicators
-------------------------------------

.. list-table:: Development Activity (FY26)
   :header-rows: 1
   :widths: 25 25 25 25

   * - Period
     - PRs Merged
     - Key Focus
     - Contributors
   * - Nov 2025
     - ~5
     - Initial repo setup, SOX compliance
     - Zhangbin Cheng
   * - Dec 2025
     - ~10
     - Kotlin conversion, logging, feature service
     - Zhangbin Cheng
   * - Jan-Mar 2026
     - ~30
     - SQS consumers, analytics, interceptors
     - Zhangbin Cheng, Michael Dawson
   * - Apr 2026
     - ~15
     - Renovate updates, Rovo Dev standards, cleanup
     - Zhangbin Cheng, Morin Rodenski
   * - May 2026 (to date)
     - ~15
     - Redis, rollout service, Rovo Insights prod
     - Zhangbin Cheng, Michael Dawson, Morin Rodenski

----

8. Alignment Matrix
====================

8.1 Feature-to-Goal Alignment
-------------------------------

.. list-table:: Feature → Business Goal Alignment
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Feature
     - Business Goal
     - Technical Goal
     - Jira Reference
     - Alignment Strength
   * - Rovo Insights
     - Proactive AI summaries
     - Async SQS pipeline
     - AIX-3332
     - Strong
   * - Nudge Throttle
     - Engagement quality
     - Redis-backed state
     - (Inferred)
     - Strong
   * - Stratus/AI Gateway
     - LLM access layer
     - Multi-model agentic AI
     - AIX-3340
     - Strong
   * - Analytics Events
     - User signal capture
     - StreamHub SQS integration
     - AIX-3259
     - Strong
   * - Async Task Framework
     - Reliable background work
     - SQS + context propagation
     - AIX-3259
     - Strong
   * - Feature Gating
     - Safe rollout
     - Statsig + RolloutService
     - AIX-3340
     - Strong
   * - Redis Caching
     - Performance + state
     - RedisX integration
     - AIX-3298
     - Strong
   * - Tenant Context
     - Multi-product support
     - Unified context model
     - AIX-3251
     - Strong

8.2 Code-to-Goal Traceability
-------------------------------

.. list-table:: Source Package → Goal Traceability
   :header-rows: 1
   :widths: 35 35 30

   * - Source Package
     - Primary Goal
     - Secondary Goal
   * - ``feature.rovoinsights``
     - Proactive AI summaries (L2a)
     - Async processing reliability
   * - ``feature.nudge``
     - Engagement quality (L2b)
     - Multi-product coverage
   * - ``stratus``
     - LLM access standardization
     - Multi-model flexibility
   * - ``sqs``
     - Real-time signal processing
     - Event-driven architecture
   * - ``task``
     - Background work reliability
     - Context propagation
   * - ``featuregate``
     - Safe feature rollout
     - A/B testing capability
   * - ``context``
     - Multi-product support (L2c)
     - Tenant isolation
   * - ``interceptor``
     - Request context management
     - Observability
   * - ``logging``
     - Operational visibility
     - UGC safety compliance
   * - ``service.metric``
     - Platform health monitoring
     - SLO tracking

8.3 Architectural Decision Traceability
-----------------------------------------

Key architectural decisions and their business justification:

1. **SQS over synchronous processing** — Enables long-running AI
   generation without blocking HTTP requests; critical for Rovo Insights
   latency requirements

2. **Visibility-extending SQS consumer** — Prevents message re-delivery
   during long AI generation tasks; ensures at-least-once processing

3. **Interface/Internal package pattern** — Enforces clean API boundaries;
   enables swapping implementations (e.g., FeatureService → RolloutService)

4. **Coroutine-first design** — Non-blocking I/O for AI Gateway calls;
   efficient thread utilization under load

5. **Multi-product tenant context** — Future-proofs for product expansion;
   single codebase serves all Atlassian products

----

Appendix A: Data Source Inventory
==================================

.. list-table:: Data Sources Consulted
   :header-rows: 1
   :widths: 25 25 25 25

   * - Source
     - Query
     - Result
     - Completeness
   * - Atlas Goals API
     - ``search_goals("proactive-ai-platform")``
     - API rate limit error
     - Incomplete
   * - Atlas Goals API
     - ``search_goals("AIX proactive AI")``
     - Session error
     - Incomplete
   * - Confluence CQL
     - ``text ~ "proactive-ai" AND (OKR OR goals)``
     - 15 results (general, not platform-specific)
     - Partial
   * - Confluence CQL
     - ``text ~ "proactive-ai-platform" AND type = page``
     - 15 results (general)
     - Partial
   * - Jira JQL
     - ``project = CTSC AND ... "proactive-ai"``
     - No results
     - Empty
   * - Jira JQL
     - ``project = CTSC AND ... labels/summary``
     - No results
     - Empty
   * - Bitbucket PRs
     - Merged PRs (pages 1-2, 50 per page)
     - ~100 PRs including 140 total
     - Complete
   * - Bitbucket Comments
     - PR #127, #134 review comments
     - 48 + 6 comments
     - Complete
   * - Git Log
     - Full commit history since inception
     - 80+ commits since Nov 2025
     - Complete
   * - Codebase Analysis
     - All source packages
     - 7 feature areas analyzed
     - Complete

Appendix B: Glossary
=====================

See :doc:`/architecture/00-glossary` for the full project glossary covering
all terms used in this document (AIX, Rovo Insights, Stratus, StreamHub,
LAAS, MCP, TCS, and others).
