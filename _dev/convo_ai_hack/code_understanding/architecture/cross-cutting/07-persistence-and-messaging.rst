.. _persistence:

============================
Persistence & Async Messaging
============================

The platform persists state via **Kamino** (Atlassian's event-sourced data platform) and **Redis** (for caches and ephemeral state). Async work flows through **SQS** (lifecycle events) and **Aqui** (long-running tasks).

Kamino
=======

- **Purpose:** event-sourced storage for conversations, agent state, audit trails
- **Bootstrap:** ``KaminoBootstrapController`` (in ``service/convo-ai-service/rest/``) — handles initial setup
- **Schema migration:** AgentStudio uses ``data.agentStudio_upgradeSchema`` mutation (visible in failing AgentStudioUpgradeSchemaIT integration tests)

Each conversation is essentially an event log:
- "User sent message X"
- "LLM responded with chunk Y, Z, W..."
- "User clicked thumbs up on message M"

Replay-ability and audit are first-class — you can reconstruct any conversation's full history.

Redis (2 clusters per integration-tests sandbox)
==================================================

Per the integration-tests container list (verified):
- ``redis (provisioning)`` — provisioning state cache
- ``redis (async-tasks)`` — async task state cache (REDISX_CONVOAI_ASYNC_TASKS_HOST env var)

Both are accessed via the ``redisx`` Atlassian Redis cluster abstraction.

SQS — lifecycle events
=======================

Annotated at ``Application.kt:13`` (verified):

.. code-block:: kotlin

   @EnableSqsQueues

The startup listener (``ConvoAiApplicationStartupListener.kt``) **fail-fasts** if ``SqsMicrosLifecycleEventHandler`` bean is not loaded — confirming SQS is critical for service operation.

Use cases:
- Provisioning events (tenant onboarded/offboarded)
- Cache invalidation
- Cross-service notifications

Per the deploy descriptor (agent-reported), there are multiple workers: SHWorkers, Standard, Rovo, LongRun.

Aqui — async tasks
===================

Annotated at ``Application.kt:14`` (verified):

.. code-block:: kotlin

   @EnableAquiQueues

Aqui is Atlassian's queue framework for long-running tasks where the client doesn't wait for completion. Use cases:
- Batch evaluation runs (AgentStudio)
- Knowledge base re-indexing
- Marathon-orchestrated agent workflows
- Bulk operations across many conversations

Aqui has its own Kafka-backed queue topology and provides delivery guarantees + retry semantics.

Patterns
=========

1. **Append-only by default.** Kamino events are append-only; mutations are encoded as new events ("message_edited"), not destructive updates.

2. **Cache vs source-of-truth.** Redis is for caches and ephemeral state. Source-of-truth is always Kamino.

3. **Async over sync.** Long work goes to Aqui. The user gets a 202 Accepted; status polled separately.

4. **Lifecycle events MUST handle retries.** SQS at-least-once delivery means handlers must be idempotent.

5. **Multiple queue workers.** Different SQS workers for different latency profiles (Standard for normal ops; LongRun for >30s tasks; Rovo dedicated for Rovo-specific events).

What you would change here
===========================

- **Add a new event type** → define new Kamino event class; emit at the relevant code site
- **Add a new SQS handler** → ``@SqsListener`` annotated method in service-tier
- **Add a new Aqui task** → register task type in ``foundation/capabilities/`` + handler in service-tier
- **Add a Redis cache** → new ``...CacheService`` class wrapping ``redisx`` client

What you would NOT change here
===============================

- Kamino infrastructure (managed by the Kamino team)
- SQS topology (managed by the deploy descriptor + AWS infra team)
- Aqui Kafka cluster (managed by Aqui platform team)

