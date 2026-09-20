.. _architecture-overview:

==============================
Architecture Overview
==============================

This document describes the Proactive AI Service's component topology,
package dependency DAG, and external service dependencies.

Package Dependency DAG
======================

The diagram below shows the dependency relationships between the 15
top-level packages (16 functional modules).  Arrows point from dependent
to dependency.

.. mermaid::

   graph TD
       subgraph "Tier 1 — Critical Path"
           FEAT_NUDGE[feature/nudge]
           FEAT_ROVO[feature/rovoinsights]
           GREETING[greeting]
           STRATUS[stratus]
           INTERCEPTOR[interceptor]
           REQCTX[requestcontext]
       end

       subgraph "Tier 2 — Core Infrastructure"
           SQS[sqs]
           TASK[task]
           FGATE[featuregate]
           METRIC[service/metric]
           LOGGING[logging]
           CONTEXT[context]
           CLIENT[client]
       end

       subgraph "Tier 3 — Supporting"
           CONFIG[config]
           EXCEPTION[exception]
           UTILITY[utility]
       end

       %% Tier 1 dependencies
       FEAT_NUDGE --> FGATE
       FEAT_NUDGE --> METRIC
       FEAT_NUDGE --> LOGGING

       FEAT_ROVO --> TASK
       FEAT_ROVO --> FGATE
       FEAT_ROVO --> STRATUS
       FEAT_ROVO --> METRIC
       FEAT_ROVO --> LOGGING
       FEAT_ROVO --> CONTEXT

       STRATUS --> CLIENT
       STRATUS --> LOGGING
       STRATUS --> CONTEXT
       STRATUS --> METRIC

       INTERCEPTOR --> REQCTX
       INTERCEPTOR --> LOGGING
       INTERCEPTOR --> CONTEXT
       INTERCEPTOR --> UTILITY

       GREETING --> LOGGING

       %% Tier 2 dependencies
       SQS --> LOGGING
       SQS --> METRIC
       SQS --> CONTEXT

       TASK --> SQS
       TASK --> LOGGING
       TASK --> METRIC
       TASK --> REQCTX

       FGATE --> LOGGING
       FGATE --> CONTEXT
       FGATE --> METRIC

       METRIC --> LOGGING

       REQCTX --> LOGGING
       REQCTX --> CONTEXT

       CLIENT --> LOGGING
       CLIENT --> EXCEPTION
       CLIENT --> CONTEXT

       %% Tier 3 dependencies
       UTILITY --> LOGGING
       CONFIG --> UTILITY

Component Topology
==================

The service is deployed as a single container image that runs in three
distinct roles based on the ``MICROS_ENVTYPE`` environment variable:

.. code-block:: text

   ┌──────────────────────────────────────────────────────────────┐
   │                    Load Balancer                             │
   └────────────┬─────────────────────────────────────────────────┘
                │
   ┌────────────▼─────────────────────────────────────────────────┐
   │              WebServer Nodes                                 │
   │  ┌─────────────────┐  ┌──────────────────┐                  │
   │  │ Spring MVC       │  │ Interceptor Chain │                 │
   │  │ Controllers      │  │ (Auth + Context)  │                 │
   │  └────────┬─────────┘  └──────────────────┘                  │
   │           │                                                  │
   │  ┌────────▼──────────────────────────────────────────┐       │
   │  │ Services: FeatureService, AIGatewayService,       │       │
   │  │ MetricsService, AsyncTaskService                  │       │
   │  └────────┬──────────────────────────────────────────┘       │
   │           │ dispatch                                         │
   └───────────┼──────────────────────────────────────────────────┘
               │
       ┌───────▼───────┐         ┌─────────────────────┐
       │ SQS Queue:    │         │ SQS Queue:          │
       │ rovo_insights │         │ analytics_events    │
       │ _generation   │         │ (StreamHub)         │
       └───────┬───────┘         └──────────┬──────────┘
               │                            │
   ┌───────────▼────────────┐  ┌────────────▼─────────────────┐
   │  LongRun Nodes         │  │  SHWorker Nodes              │
   │  RovoInsights           │  │  AnalyticsEvents              │
   │  SqsQueueConsumer       │  │  SqsQueueConsumer             │
   └─────────────────────────┘  └──────────────────────────────┘

External Service Dependencies
=============================

.. list-table:: External Dependencies
   :header-rows: 1
   :widths: 20 20 25 35

   * - Service
     - Protocol
     - Client Module
     - Purpose
   * - ID Gatekeeper
     - HTTPS (REST)
     - ``client/identity``
     - User identity resolution, audience membership checks
   * - AI Gateway
     - HTTPS (REST + MCP)
     - ``stratus``
     - LLM orchestration, tool-calling, session management
   * - TCS
     - HTTPS (REST)
     - ``utility/tenant``
     - Tenant metadata and configuration lookup
   * - Feature Gate Service
     - HTTPS (REST)
     - ``featuregate``
     - Feature flag evaluation (Switcheroo backend)
   * - StreamHub
     - SQS (subscription)
     - ``sqs``
     - Analytics event delivery to ``analytics_events`` queue
   * - SLAUTH
     - JWT (headers)
     - ``config`` / ``interceptor``
     - Service-to-service authentication token validation
   * - POCO
     - Policy files
     - ``config``
     - Endpoint-level authorization policy enforcement

Dependency Health Monitoring
----------------------------

Each external dependency should be monitored for:

* **Latency** — via ``MetricsService`` timer metrics per client call
* **Error rate** — via ``MetricsService`` counter metrics for HTTP 4xx/5xx
* **Availability** — via health check endpoints where available
* **Circuit breaking** — recommended for all HTTP clients to prevent
  cascade failures
