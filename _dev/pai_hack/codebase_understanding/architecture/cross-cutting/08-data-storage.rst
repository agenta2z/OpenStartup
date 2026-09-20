=========================================
08 — Data Storage
=========================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

Proactive-AI-Platform has **no relational or document database**.  All
durable state is held in **SQS queues** (message-level persistence) and
**Redis/Valkey** (ephemeral cache).  This is a deliberate architectural
choice: the service acts as an orchestration and event-processing layer
whose primary job is to receive events, invoke LLM-backed pipelines, and
return results — not to own long-lived entity state.

Storage Layer Summary
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Technology
     - Resource Name
     - Persistence
     - Role
   * - **AWS SQS**
     - ``analytics-events``
     - Transient (1 h retention)
     - Inbound StreamHub analytics events.  Messages are consumed by the
       ``SHWorkers`` group and deleted on successful processing.
   * - **AWS SQS**
     - ``rovo-insights-generation-queue``
     - Transient (default 4 days)
     - Async-task envelopes published by the WebServer and consumed by
       the ``LongRun`` worker group.  Each message is a JSON-serialised
       ``AsyncTask`` with a ``@type`` discriminator.
   * - **AWS SQS (DLQ)**
     - Auto-provisioned per queue
     - Transient
     - Failed messages (exceeding ``MaxReceiveCount``) are moved here for
       investigation.  Alarms fire on DLQ depth > 0.
   * - **Redis / Valkey**
     - ``proactive-ai-cache``
     - Ephemeral
     - General-purpose cache.  Valkey 7.x, single-node
       (``cache.t4g.small``), 1 replica, TLS enabled, cluster mode
       disabled.

Why No Database?
----------------

1. **Stateless orchestration**: The service's primary flows (nudge
   throttling, Rovo Insights generation, Stratus agent invocation) are
   request-scoped or SQS-message-scoped.  Results are returned to the
   caller or published back to upstream services — there is no entity
   lifecycle to persist.

2. **SQS-as-work-queue**: The async-task framework
   (``AsyncTaskService`` / ``AsyncTaskHandler``) uses SQS as a durable
   work queue with built-in retry (``MaxReceiveCount``) and dead-letter
   routing.  This provides sufficient durability for fire-and-forget task
   dispatch without requiring a database-backed job table.

3. **Cache-only reads**: Where data *is* cached (Redis), it is
   reconstructable from upstream sources.  Cache eviction causes a
   re-fetch, not data loss.

Data Classification
-------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Resource
     - Data Types
   * - ``analytics-events`` queue
     - ``Usage/Action`` — analytics event payloads from StreamHub.
   * - ``rovo-insights-generation-queue``
     - ``Identifier/OfEntity``, ``PD/Pseudonymous`` — tenant identifiers,
       user account IDs, and insight request parameters.
   * - ``proactive-ai-cache``
     - ``Identifier/OfEntity``, ``UGC/Raw``, ``PD/Pseudonymous``.

The top-level service ``computeClassification`` declares
``dataType: [None]`` because the service itself stores no persistent
customer data; transient SQS messages and cache entries carry the
classifications above.

SQS Message Lifecycle
---------------------

.. code-block:: text

   Producer (WebServer)
       │
       │  SQS SendMessage
       ▼
   ┌──────────────┐    consumed      ┌─────────────────┐
   │  SQS Queue   │ ──────────────▶  │  Worker (LongRun │
   │              │                  │   or SHWorkers)  │
   └──────┬───────┘                  └────────┬────────┘
          │                                    │
          │ fails MaxReceiveCount times         │ success → message deleted
          ▼                                    │
   ┌──────────────┐                            │
   │     DLQ      │                            │
   └──────────────┘                            │
          │                                    │
          └── alarm fires ─────────────────────┘

Messages are not persisted beyond the SQS retention period.  There is no
replay mechanism beyond manual re-driving from the DLQ.

Future Considerations
---------------------

- **Database introduction**: If the service needs to own entity state
  (e.g. insight history, user preferences), a DynamoDB or RDS resource
  would be added to the service descriptor.
- **Redis cluster mode**: Currently disabled; can be enabled with multiple
  shards if high-throughput workloads need to be decoupled from the shared
  cache.
- **SQS FIFO**: The ``rovo-insights-generation-queue`` is currently a
  standard queue.  Switching to FIFO would provide exactly-once processing
  and ordering guarantees if needed.
