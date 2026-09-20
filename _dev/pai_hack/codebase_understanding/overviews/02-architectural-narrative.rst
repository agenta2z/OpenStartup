.. _architectural-narrative:

==============================
Architectural Narrative
==============================

This document provides a narrative overview of the Proactive AI Service's
technology stack, Spring Boot architecture, and worker-group topology.

Technology Stack
================

The Proactive AI Service is built on the **Atlassian Micros PaaS** platform
using the following core technologies:

.. list-table:: Technology Stack
   :header-rows: 1
   :widths: 25 30 45

   * - Layer
     - Technology
     - Notes
   * - Language
     - Kotlin 1.9+ (JVM)
     - Coroutine-first async model
   * - Framework
     - Spring Boot 3.x
     - Auto-configuration via Micros starters
   * - Build
     - Gradle (Kotlin DSL)
     - ``build.gradle.kts`` with Micros plugin
   * - HTTP Server
     - Embedded Tomcat
     - Managed by Spring Boot
   * - Messaging
     - AWS SQS (via ``sqs-queues-starter``)
     - DLQ support, visibility-extending consumers
   * - Feature Flags
     - Atlassian Feature Gate Client
     - Switcheroo integration via ``featuregate-client-starter``
   * - Auth / AuthZ
     - SLAUTH + POCO
     - Service-level auth with policy-based authorization
   * - Observability
     - Micrometer + LAAS Logger
     - Structured logging, custom metric registry
   * - AI Integration
     - Stratus / AI Gateway
     - MCP server integration, tool provider pattern
   * - Analytics
     - StreamHub
     - Event ingestion via SQS subscription
   * - CI/CD
     - Bitbucket Pipelines → Spinnaker
     - Canary deployments, SOX-compliant
   * - Local Dev
     - Nebulae (Docker Compose)
     - ``atlas`` CLI for service mesh simulation

Spring Boot Architecture
========================

The service follows a layered Spring Boot architecture with clear separation
of concerns:

.. code-block:: text

   ┌─────────────────────────────────────────────────────┐
   │                   HTTP Layer                        │
   │  LoggingContextClearingFilter                       │
   │  ├─ RequestContextInterceptor                       │
   │  ├─ UserContextInterceptor                          │
   │  └─ CommonContextSetter                             │
   ├─────────────────────────────────────────────────────┤
   │                Controllers                          │
   │  NudgeThrottleController  │  RovoInsightsController │
   │  StratusTestController    │  WebServiceController   │
   │  RovoInsightsTestController                         │
   ├─────────────────────────────────────────────────────┤
   │              Services & Business Logic              │
   │  FeatureService     │  MetricsService               │
   │  AIGatewayService   │  CoreMetricsService           │
   │  AsyncTaskService   │  TcsService                   │
   ├─────────────────────────────────────────────────────┤
   │              Infrastructure                         │
   │  SQS Consumers      │  Async Task Dispatch          │
   │  Feature Gates       │  ID Gatekeeper Client        │
   │  Logging (LAAS)      │  Request Context             │
   ├─────────────────────────────────────────────────────┤
   │              Context & Models                       │
   │  TenantContext  │ CloudIdContext │ OrgIdContext      │
   │  AIGatewayContext │ PlatformTenantContext            │
   └─────────────────────────────────────────────────────┘

Key architectural patterns:

* **Interceptor chain** — HTTP requests pass through a filter and interceptor
  stack that establishes logging context, resolves user identity, and
  populates request-scoped values before reaching controllers.

* **Interface + ``internal/`` implementation** — Public APIs are defined as
  interfaces in the package root; implementations live in an ``internal/``
  sub-package, promoting testability and loose coupling.

* **Async task framework** — Long-running work is dispatched to SQS queues
  via ``AsyncTaskService`` and consumed by ``VisibilityExtendingSQSQueueConsumer``
  instances that automatically extend message visibility during processing.

* **Context propagation** — A rich set of context objects (tenant, cloud ID,
  org ID, platform) flow through the request lifecycle via request-scoped
  beans and ``RequestScopedValueOwner`` registrations.

Worker Groups
=============

The service operates three distinct **worker groups**, each with its own
scaling profile and SQS queue bindings:

.. list-table:: Worker Group Topology
   :header-rows: 1
   :widths: 20 25 25 30

   * - Worker Group
     - Node Condition
     - Queue(s)
     - Purpose
   * - **WebServer**
     - Default (no condition)
     - N/A (HTTP only)
     - Serves REST endpoints, health checks, and test controllers
   * - **LongRun**
     - ``OnLongRunWorkerNodeOrLocalCondition``
     - ``rovo_insights_generation``
     - Processes long-running Rovo Insights generation tasks
   * - **SHWorkers**
     - ``OnSHWorkerNodeOrLocalCondition``
     - ``analytics_events``
     - Consumes StreamHub analytics events

Each worker group is activated by a Spring ``@Conditional`` that checks
the ``MICROS_ENVTYPE`` environment variable or falls back to local mode.
This allows the same codebase to run in all three roles depending on the
deployment target.

.. mermaid::

   graph LR
       subgraph "WebServer Nodes"
           WS[REST Controllers]
       end
       subgraph "LongRun Nodes"
           LR[RovoInsightsGenerationSqsQueueConsumer]
       end
       subgraph "SHWorkers Nodes"
           SH[AnalyticsEventsSqsQueueConsumer]
       end

       SQS_RI[SQS: rovo_insights_generation] --> LR
       SQS_AE[SQS: analytics_events] --> SH
       WS -->|dispatch task| SQS_RI
       StreamHub[StreamHub] -->|subscription| SQS_AE

SQS Configuration
------------------

Both SQS queues share a common configuration pattern:

* **Concurrency**: 2–8 threads (auto-scaled)
* **Auto-lifecycle**: Disabled (managed by worker-group conditions)
* **Auto-startup**: Disabled (explicit activation per node type)
* **DLQ**: Enabled via ``sqs-queues-dlq-actuator``

External Service Dependencies
=============================

The service integrates with several external Atlassian platform services:

* **ID Gatekeeper** — Identity resolution and audience membership checks
* **AI Gateway (Stratus)** — LLM orchestration and tool-calling via MCP
* **Tenant Context Service (TCS)** — Tenant metadata and configuration
* **Feature Gate Service** — Feature flag evaluation (Switcheroo)
* **StreamHub** — Analytics event ingestion
* **SLAUTH** — Service-to-service authentication
* **POCO** — Policy-based authorization
