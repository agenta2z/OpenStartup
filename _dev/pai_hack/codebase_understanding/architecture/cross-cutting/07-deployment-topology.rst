=========================================
07 — Deployment Topology
=========================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

Proactive-AI-Platform is deployed as an Atlassian Micros service with
**three JVM worker groups** sharing a single Docker image.  Each group
runs the same Spring Boot application but activates different beans via
the ``MICROS_GROUP`` environment variable and Spring ``@Conditional``
annotations.

Worker Groups
-------------

.. list-table::
   :header-rows: 1
   :widths: 18 15 35 32

   * - Group Name
     - ``MICROS_GROUP``
     - Role
     - Scaling
   * - **WebServer**
     - ``WebServer`` (default)
     - Serves HTTP traffic (REST controllers, healthchecks).  Also hosts
       the SQS *producer* side (``AsyncTaskServiceImpl`` publishes to
       queues).
     - ``t3a.medium``, ALB single load-balancer
   * - **SHWorkers**
     - ``SHWorkers``
     - Consumes StreamHub analytics events from the ``analytics_events``
       SQS queue.  Gated by ``OnSHWorkerNodeOrLocalCondition``.
     - ``t3a.medium``, min 1
   * - **LongRun**
     - ``LongRun``
     - Consumes async-task envelopes from the
       ``rovo_insights_generation_queue`` SQS queue.  Gated by
       ``OnLongRunWorkerNodeOrLocalCondition``.  Designed for high-latency
       LLM-backed workloads (5–60 s per task).
     - ``t3a.medium``, min 1, max 2

Worker Group Activation Conditions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   // OnSHWorkerNodeOrLocalCondition
   fun isWorkerNode() = System.getenv().getOrDefault("MICROS_GROUP", "WebServer") == "SHWorkers"
   fun isLocalProfile(ctx) = ctx.environment.activeProfiles.any { it == "local" }

   // OnLongRunWorkerNodeOrLocalCondition
   fun isWorkerNode() = System.getenv().getOrDefault("MICROS_GROUP", "WebServer") == "LongRun"
   fun isLocalProfile(ctx) = ctx.environment.activeProfiles.any { it == "local" }

Both conditions also match the ``local`` profile, allowing developers to
run all consumers in a single JVM during local development.

SQS Queue Bindings
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 18 18 34

   * - Queue (SD name → app key)
     - Worker Group
     - Visibility Timeout
     - Max Receive / DLQ
   * - ``analytics-events`` → ``analytics_events``
     - SHWorkers
     - 120 s
     - 3 attempts → auto-provisioned DLQ
   * - ``rovo-insights-generation-queue`` → ``rovo_insights_generation_queue``
     - LongRun
     - 360 s (6 min)
     - 2 attempts → auto-provisioned DLQ

Queue-to-worker mapping is declared in ``application.yml``:

.. code-block:: yaml

   worker:
     SHWorkers:
       analytics_events:
         name: ${SQS_ANALYTICS_EVENTS_QUEUE_NAME}
         url: ${SQS_ANALYTICS_EVENTS_QUEUE_URL}
     LongRun:
       rovo_insights_generation_queue:
         name: ${SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_NAME}
         url: ${SQS_ROVO_INSIGHTS_GENERATION_QUEUE_QUEUE_URL}

SQS Configuration
^^^^^^^^^^^^^^^^^

- **Prefetch = 0**: ``CommonSqsConfig`` explicitly overrides the default
  ``prefetch=1`` of the AWS SQS Java Messaging Library.  With PAI's
  high-variance per-task latency (5–60 s), prefetch=0 prevents a slow
  listener from holding a prefetched message while a fast listener sits
  idle.
- **Concurrency**: ``"2-8"`` per listener container — 2 threads at idle,
  scaling up to 8 under load.
- **Lifecycle**: ``auto-lifecycle-management-disabled: false``,
  ``enable-auto-startup: false`` — consumers rely on Micros lifecycle
  events (delivered via SQS queue) to start/stop during progressive
  rollouts.
- **Duplicate handling**: ``NopDuplicateHandler`` (no dedup; standard
  queues deliver at-least-once).

Consumer Activation
^^^^^^^^^^^^^^^^^^^

Each consumer requires **two** conditions (AND):

1. The worker-group condition (``@Conditional(OnSHWorkerNodeOrLocalCondition::class)``).
2. A per-queue ``@ConditionalOnProperty`` (e.g. ``SQS_ANALYTICS_EVENTS_QUEUE_URL``).

This allows multiple consumers on the same worker group without coupling
their activation.

Docker Image
------------

.. code-block:: docker

   FROM docker.atl-paas.net/sox/micros-java-21:1.5.0
   COPY ./build/libs/proactive-ai-platform*.jar /opt/service/service.jar

Single-layer SOX-compliant Java 21 image.  The fat JAR is the only
application artifact.  Memory is configured via
``MEMORY_OPTS=-XX:MaxRAMPercentage=25.0`` (25% of system RAM).

Compose Services
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Service
     - Image
     - Ports
   * - ``proactive-ai-platform``
     - ``docker.atl-paas.net/${DOCKER_IMAGE}``
     - 8080 (HTTP), 9010 (JMX)
   * - ``tap-sidecar``
     - ``docker.atl-paas.net/sox/atlassian/tap-sidecar-go:stable-v1``
     - 8083

Environment Profiles
--------------------

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Profile
     - Configuration
   * - ``local``
     - ``application-local.yml``, ``MEMORY_OPTS=-Xmx512M``, port 8090,
       sandbox Docker tag, all worker conditions match.
   * - ``staging``
     - ``application-staging.yml``, includes ``continuous-chaos`` resource
       for fault injection.
   * - ``prod``
     - ``application-prod.yml``, organisation set to ``Engineering-AI COGS``.

Environment type is resolved at startup via ``MicrosEnvironmentConfig``
which reads ``${MICROS_ENVTYPE}`` and maps it to
``MicrosEnvironmentType.{LOCAL, STAGING, PROD}``.

Spinnaker Pipelines
-------------------

Defined in ``default-pipelines.spinnaker.yaml``:

.. list-table::
   :header-rows: 1
   :widths: 30 25 25 20

   * - Pipeline
     - Environments
     - Template
     - Notes
   * - ``service-descriptor``
     - stg-east → prod-east
     - ``safeRelease``
     - Progressive rollout (``useDefault: true``) for prod.
   * - ``service-descriptor-branch-deploy-staging``
     - stg-east only
     - ``safeRelease``
     - Branch deploy for staging pre-merge validation.

Common pipeline config:

- **Namespace**: ``spinnaker-proactive-ai-platform``
- **Throughput**: ``high``
- **Failure notification**: Slack ``#ai-experience-ops`` with commit
  author and changelog.

Bitbucket Pipelines
-------------------

``bitbucket-pipelines.yml`` orchestrates CI:

- **Image**: ``gradle:9.4.1-jdk21``
- **Branches → main**: lint, test, build, deploy to staging, deploy to prod.
- **Pull requests**: lint + test + build.
- **Custom → branch-deploy-staging**: on-demand staging deploy from any branch.

Infrastructure Resources
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Type
     - Name
     - Details
   * - ``slauth-gateway``
     - ``proactive-ai-gateway``
     - SLAUTH ingress gateway.
   * - ``redisx``
     - ``proactive-ai-cache``
     - Valkey 7.x, single-node (``cache.t4g.small``), 1 replica,
       TLS enabled, cluster mode off.
   * - ``sqs``
     - ``analytics-events``
     - StreamHub event queue, 1 h retention, policy allows
       ``streamhub-demux`` to write.
   * - ``sqs``
     - ``rovo-insights-generation-queue``
     - Async-task queue, standard (non-FIFO), alarms on age > 12 min
       and DLQ depth > 0 / > 100.

Alarms
------

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Alarm
     - Priority
     - Trigger
   * - ``UnHealthyHostCount``
     - Low
     - ≥ 1 unhealthy host for 6 consecutive periods (60 s each).
   * - ``WebServerMemoryAlarmHigh``
     - Low
     - Memory utilisation > 90% avg over 2 × 5 min periods.
   * - ``EngineCPUUtilizationTooHigh`` (Redis)
     - Low
     - Engine CPU > 90% avg over 5 × 60 s periods.
   * - ``HighRovoInsightsGenerationProcessingLatency``
     - Low
     - Oldest message age > 720 s (12 min) for 6 × 5 min periods.
   * - ``RovoInsightsGenerationDLQueueAlertLow``
     - Low
     - DLQ depth > 0.
   * - ``RovoInsightsGenerationDLQueueAlertHigh``
     - Low
     - DLQ depth > 100.
