.. _glossary:

==============================
Glossary
==============================

Key terms and acronyms used throughout the Proactive AI Service documentation.

Platform & Infrastructure
=========================

.. glossary::
   :sorted:

   Micros
      Atlassian's internal Platform-as-a-Service (PaaS) for deploying and
      managing micro-services.  Provides service descriptors, environment
      management, and integration with Atlassian's deployment pipeline.

   SLAUTH
      **S**\ ervice **L**\ evel **Auth**\ entication — Atlassian's
      service-to-service authentication framework.  Issues and validates
      JWT-like tokens for inter-service communication.  Configured via
      ``MvcSecurityConfig`` and enforced by Spring Security filters.

   POCO
      **Po**\ licy **Co**\ ntrol — Atlassian's authorization framework that
      enforces fine-grained access policies on service endpoints.  Policies
      are defined in ``policies/service/policy.json`` and tested via
      ``policies/tests.json``.

   Nebulae
      Local development tool that uses Docker Compose to simulate the
      Atlassian service mesh on a developer's machine.  Provides SLAUTH
      token minting and service discovery for local testing.

   StreamHub
      Atlassian's analytics event streaming platform.  Events are published
      to StreamHub topics and delivered to subscribers via SQS queues.
      The Proactive AI Service subscribes to analytics events through
      the ``analytics_events`` queue.

   Spinnaker
      Continuous deployment platform used by Atlassian for production
      releases.  Supports canary deployments, manual approval gates,
      and automated rollback.

   Switcheroo
      Atlassian's feature flag management platform.  Feature gates are
      defined in Switcheroo and evaluated at runtime via the Feature Gate
      Client.

Logging & Observability
=======================

.. glossary::
   :sorted:

   LaasLogger
      **L**\ ogging **a**\ s **a** **S**\ ervice Logger — the service's
      structured logging abstraction.  Wraps SLF4J with mandatory fields
      (tenant, user, trace ID) and provides UGC-safe variants that redact
      user-generated content.

   LAAS
      **L**\ ogging **a**\ s **a** **S**\ ervice — Atlassian's centralized
      logging infrastructure.  LaasLogger formats log entries for ingestion
      by the LAAS pipeline.

   UGC Logger
      A ``LaasLogger`` variant (``WithUGCLogger``) that marks log entries
      as containing User-Generated Content, enabling downstream filtering
      and compliance controls.

   Intercepted Logger
      A ``LaasLogger`` decorator (``InterceptedLogger``) that intercepts
      log calls for testing or conditional processing.

   Micrometer
      Metrics facade used by Spring Boot.  The service emits custom metrics
      via ``MetricsService`` and ``CoreMetricsService`` using Micrometer's
      registry API.

Architecture & Patterns
=======================

.. glossary::
   :sorted:

   Request Context
      The set of request-scoped values (tenant ID, user ID, cloud ID,
      trace ID, etc.) that are established by interceptors and propagated
      through the request lifecycle via ``RequestScopedValueOwner``
      registrations.

   Worker Group
      A deployment topology where the same codebase runs in different roles
      (WebServer, LongRun, SHWorkers) based on the ``MICROS_ENVTYPE``
      environment variable.  Each worker group activates different Spring
      beans via ``@Conditional`` annotations.

   Async Task Framework
      An internal framework (``task`` package) for dispatching long-running
      work to SQS queues.  Provides ``AsyncTaskService`` for dispatch,
      ``AsyncTaskHandler`` for processing, and
      ``VisibilityExtendingSQSQueueConsumer`` for automatic SQS visibility
      timeout extension.

   Visibility Extending Consumer
      An SQS queue consumer (``VisibilityExtendingSQSQueueConsumer``) that
      automatically extends message visibility timeouts while processing is
      in progress, preventing premature redelivery of long-running tasks.

   MCP
      **M**\ odel **C**\ ontext **P**\ rotocol — a protocol for providing
      tools and context to LLMs.  The service integrates with the AI Gateway's
      MCP server via ``IntegrationServiceMcpServerConfig``.

AI & Features
=============

.. glossary::
   :sorted:

   AI Gateway
      Atlassian's centralized AI orchestration service (also called
      *Stratus*).  Provides LLM access, tool-calling via MCP, and
      session management.

   Stratus
      See :term:`AI Gateway`.  The internal project name for Atlassian's
      AI Gateway infrastructure.

   Rovo Insights
      The primary feature of this service — generates AI-powered insights
      by processing data through the AI Gateway.  Insights are dispatched
      as async tasks to the ``rovo_insights_generation`` SQS queue.

   Nudge Throttle
      A throttling mechanism for proactive AI notifications (nudges).
      Prevents notification fatigue by rate-limiting nudge delivery per
      user and per nudge type.

   Feature Gate
      A feature flag evaluated at runtime to control feature rollout.
      Gates are defined in :term:`Switcheroo` and evaluated via
      ``FeatureService``.  The service defines gates in ``AiFeatureGates``
      and ``PermanentFeatureGates``.

Identity & Multi-Tenancy
========================

.. glossary::
   :sorted:

   Cloud ID
      A unique identifier for an Atlassian cloud site (tenant).  Resolved
      from request headers and propagated via ``CloudIdContext``.

   Org ID
      An organization-level identifier that groups multiple cloud sites.
      Resolved via ``OrgIdContext``.

   TCS
      **T**\ enant **C**\ ontext **S**\ ervice — an external Atlassian
      service that provides tenant metadata.  Accessed via ``TcsService``
      in the ``utility/tenant`` package.

   ID Gatekeeper
      An external Atlassian service for identity resolution and audience
      membership verification.  Accessed via ``IdGatekeeperClient`` (sync)
      and ``AsyncIdGatekeeperClient`` (async) in the ``client/identity``
      package.

   AAID
      **A**\ tlassian **A**\ ccount **ID** — a globally unique user
      identifier in the Atlassian identity system.
