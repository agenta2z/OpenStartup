.. _criticality-dashboard:

==============================
Criticality Dashboard
==============================

Operational criticality assessment for the Proactive AI Service.  This
dashboard ranks every functional module by its impact on service health and
provides on-call guidance for incident triage.

Assessment Methodology
======================

Each module is scored across four dimensions (each 1–5):

1. **Traffic Exposure** — Does the module sit in the inbound request path?
2. **Blast Radius** — How many other modules or users are affected by failure?
3. **Recovery Complexity** — How hard is it to recover from a failure?
4. **Data Sensitivity** — Does the module handle PII, auth tokens, or billing data?

The **composite score** is the weighted average:
``0.35 × Traffic + 0.30 × Blast + 0.20 × Recovery + 0.15 × Data``.

.. list-table:: Criticality Assessment
   :header-rows: 1
   :widths: 20 10 10 10 10 10 30

   * - Module
     - Traffic
     - Blast
     - Recovery
     - Data
     - Score
     - Notes
   * - ``requestcontext``
     - 5
     - 5
     - 3
     - 4
     - **4.45**
     - Every request; stores auth + tenant context
   * - ``interceptor``
     - 5
     - 5
     - 2
     - 4
     - **4.25**
     - Auth enforcement; stateless → fast recovery
   * - ``task``
     - 3
     - 5
     - 4
     - 2
     - **3.65**
     - Async backbone; message loss risk with SQS
   * - ``sqs``
     - 3
     - 4
     - 3
     - 2
     - **3.15**
     - Analytics pipeline; DLQ provides buffer
   * - ``featuregate``
     - 4
     - 4
     - 2
     - 1
     - **3.25**
     - Cached evaluations reduce blast radius
   * - ``feature/rovoinsights``
     - 4
     - 3
     - 3
     - 3
     - **3.35**
     - Primary feature; user-visible impact
   * - ``stratus``
     - 3
     - 3
     - 2
     - 2
     - **2.65**
     - AI features degrade gracefully
   * - ``service/metric``
     - 2
     - 3
     - 2
     - 1
     - **2.15**
     - Observability loss; no data path impact
   * - ``logging``
     - 2
     - 3
     - 1
     - 2
     - **2.10**
     - Debugging impaired; fire-and-forget
   * - ``context``
     - 3
     - 4
     - 2
     - 3
     - **3.10**
     - Tenant models; no runtime logic
   * - ``client``
     - 2
     - 3
     - 2
     - 3
     - **2.45**
     - ID resolution; circuit breakers mitigate
   * - ``feature/nudge``
     - 3
     - 2
     - 2
     - 1
     - **2.20**
     - Isolated feature scope
   * - ``config``
     - 1
     - 2
     - 1
     - 1
     - **1.30**
     - Startup-only; no runtime failure mode
   * - ``greeting``
     - 2
     - 1
     - 1
     - 1
     - **1.40**
     - Health endpoint; trivial blast radius
   * - ``utility``
     - 1
     - 2
     - 2
     - 1
     - **1.45**
     - Shared helpers; failure depends on consumer
   * - ``exception``
     - 1
     - 1
     - 1
     - 1
     - **1.00**
     - Exception models; purely structural

Critical Path Summary
=====================

The **critical path** for an inbound HTTP request traverses these modules
in order:

.. code-block:: text

   requestcontext → interceptor → controller (feature/*) → service
   → [sqs | task] → external dependency

Modules on this path (``requestcontext``, ``interceptor``, and the active
feature controller) have the highest composite scores and should be
prioritized during incident response.

On-Call Triage Guide
====================

.. list-table:: Incident Triage by Symptom
   :header-rows: 1
   :widths: 30 25 45

   * - Symptom
     - Likely Module
     - First Action
   * - All endpoints returning 500
     - ``requestcontext``, ``interceptor``
     - Check recent deployments; rollback if new version
   * - 401 on all requests
     - ``interceptor`` (SLAUTH)
     - Verify SLAUTH token issuance; check POCO policies
   * - Rovo Insights not generating
     - ``feature/rovoinsights``, ``task``
     - Check SQS queue depth; verify LongRun nodes are healthy
   * - Analytics events backing up
     - ``sqs``, SHWorkers
     - Check SHWorker node count; inspect DLQ for poison messages
   * - Feature flags returning defaults
     - ``featuregate``
     - Check Feature Gate Service connectivity; verify cache TTL
   * - AI features unavailable
     - ``stratus``
     - Check AI Gateway health; verify MCP endpoint config
   * - Missing metrics/dashboards
     - ``service/metric``
     - Check Micrometer registry; verify metric key definitions
   * - No structured logs
     - ``logging``
     - Check LaasLogger initialization; verify logback-spring.xml
