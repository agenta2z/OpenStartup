.. _diag-messaging:

================================================
Diagram 5 — Messaging & Async Topology
================================================

Three different async mechanisms coexist: **SQS task handlers** (long-running jobs), **Kamino events** (event-sourced conversation state), and **StreamHub events** (analytics/metering pipeline). This diagram clarifies which handles what.

Top-level topology
===================

.. mermaid::

   flowchart LR
       %% Producers
       subgraph PROD["Producers (within the service)"]
           CTL["Controllers / Workflows<br/>(synchronous handler entry)"]
           WLP["WorkflowLifecycleEventPublisher<br/>(publishes Kamino events)"]
           FFTEP["FeatureFlagAwareTaskEventPublisher<br/>(publishes async tasks to SQS)"]
           ACSHEP["AiCreditStreamHubEventPublisher<br/>SocratesMetadataEventPublisher"]
       end

       %% Channels
       subgraph CH["Async channels"]
           SQS_DR["SQS / Aqui:<br/>**TaskQueue.DEEP_RESEARCH**<br/>(LongRun worker)"]
           SQS_BE["SQS / Aqui:<br/>**TaskQueue.BATCH_EVALUATION**<br/>(60-min timeout)"]
           SQS_LIFECYCLE["SQS:<br/>**Micros lifecycle events**<br/>(provisioning, etc)"]
           KAM["Kamino<br/>(event-sourced log)"]
           SH["StreamHub<br/>(metrics / metering pipeline)"]
       end

       %% Consumers
       subgraph CONS["Consumers (within the service)"]
           BETH["BatchEvaluationTaskHandler<br/>(60-min timeout)"]
           BEDH["BatchEvaluationDeleteTaskHandler"]
           DRTH["DeepResearchTaskHandler"]
           SLEH["SqsMicrosLifecycleEventHandler<br/>(@EnableSqsQueues bean)"]
           KCONS["Kamino consumers<br/>(replay, audit, analytics)"]
       end

       %% Wiring — producers → channels
       FFTEP --> SQS_DR
       FFTEP --> SQS_BE
       CTL --> SQS_LIFECYCLE
       WLP --> KAM
       ACSHEP --> SH

       %% channels → consumers
       SQS_DR --> DRTH
       SQS_BE --> BETH
       SQS_BE --> BEDH
       SQS_LIFECYCLE --> SLEH
       KAM --> KCONS
       SH -.->|external<br/>downstream| ANALYTICS[(Atlassian<br/>analytics<br/>warehouses)]

       %% Style
       style PROD fill:#fff8e1,stroke:#f57c00
       style CH fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
       style CONS fill:#e8f5e9,stroke:#2e7d32
       style KAM fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
       style SH fill:#ede7f6,stroke:#5e35b1

How to read it
---------------

* **Left column (yellow)** = producer beans/services (publish messages)
* **Center (blue)** = the async channel itself (queue / log / pipeline)
* **Right column (green)** = consumer handlers (process messages)
* **Solid arrows** = within-service publish/consume
* **Dashed arrow** = external downstream (StreamHub feeds analytics outside this service)

Three async mechanisms
=======================

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Mechanism
     - Purpose
     - Delivery semantics
   * - **SQS / Aqui** (task queues)
     - Long-running async jobs
     - At-least-once; handlers must be idempotent
   * - **Kamino** (event log)
     - Event-sourced conversation state
     - Append-only; durable; replayable
   * - **StreamHub** (analytics)
     - Metrics / metering / audit
     - Fire-and-forget; drops on backpressure tolerated

Why three? Because each has different durability + latency requirements:

* SQS = "do this work later" → strong delivery + retry
* Kamino = "remember this happened" → durability + replay
* StreamHub = "tell analytics this happened" → throughput-optimized fire-and-forget

What gets bootstrapped at startup
==================================

The Application class declares (verified):

.. code-block:: kotlin

   @EnableSqsQueues           // line 13 — turns on @TaskHandler scanning
   @EnableAquiQueues          // line 14 — turns on Aqui task framework
   @SpringBootApplication

The startup listener (``ConvoAiApplicationStartupListener.kt``) FAIL-FASTS if ``SqsMicrosLifecycleEventHandler`` is not loaded — confirming the lifecycle queue is critical, not optional.

The TaskQueue enum
===================

The codebase uses a ``TaskQueue`` enum (verified existence) to namespace different SQS queues. Known values:

* ``DEEP_RESEARCH`` — long-running multi-LLM-call deep-research workflows
* ``BATCH_EVALUATION`` — agent quality evaluations against datasets
* (others exist but weren't enumerated in this investigation)

Each queue has its own **worker count + timeout** configuration in ``convo-ai.ad.yml`` (verified naming pattern: SHWorkers, Standard, Rovo, LongRun).

Per the deploy descriptor (agent-reported):
* ``Standard`` worker — short-latency tasks (<5 min)
* ``LongRun`` worker — extended-timeout tasks (deep research, batch eval)
* ``Rovo`` worker — Rovo-specific lifecycle events
* ``SHWorkers`` — StreamHub publication workers

Patterns visible in this diagram
==================================

1. **Three orthogonal channels.** SQS for jobs, Kamino for state, StreamHub for analytics. Don't conflate.

2. **No direct Kafka producers/consumers found.** Despite messaging being a Kafka-style problem, all access goes through the higher-level abstractions (Aqui, Kamino, StreamHub).

3. **Idempotency is mandatory for SQS handlers.** At-least-once delivery means handlers must be safe to re-run.

4. **Kamino is the source of truth.** Conversations exist as an event log; everything else (Redis caches, in-memory state) is derived.

5. **Workflow events go through a dedicated publisher.** ``WorkflowLifecycleEventPublisher`` has ``publishUserRequestKaminoEvent``, ``publishUserResponseKaminoEvent``, ``publishPluginInvocationKaminoEvent`` — making the event taxonomy discoverable.

Open questions / not-yet-investigated
=======================================

* Full enumeration of ``TaskQueue`` enum values (only 2 confirmed)
* Full inventory of Kamino event types
* StreamHub schema and downstream consumers
* Aqui delivery semantics (at-least-once? exactly-once? FIFO ordering?)

These are good follow-ups for a future deep-dive.

