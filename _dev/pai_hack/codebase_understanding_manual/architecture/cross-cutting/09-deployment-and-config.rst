.. _pai-deployment-and-config:

============================================================================
Deployment and Configuration
============================================================================

:Date: 2026-05-04

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Deployment platform
=========================

PAI deploys via **Atlassian Micros** + **Spinnaker**.

* ``service-descriptor.sd.yml`` — declares resources (Redis cache via
  ``redisx``, SLAuth gateway, mesh dependencies), alarms, retry policies,
  POCO data classification.
* ``default-pipelines.spinnaker.yaml`` — defines the deployment pipeline
  (env progression, canary, full rollout).
* ``canary-config.yml`` — canary rules.
* ``nebulae.yml`` — Nebulae Gradle plugin configuration (added in PR #105).
* ``component-descriptor.yml`` — Atlassian service catalog metadata.
* ``Dockerfile`` — Micros golden-image base; minimal layering.

2. CI
======

``bitbucket-pipelines.yml`` defines the CI pipeline:

* Build + test (``./gradlew check``)
* Sonar branch analysis
* Detekt + ktlint
* JaCoCo coverage report
* Docker image build
* Spinnaker deploy on merge-to-main

3. Configuration files (runtime)
==================================

3.1 ``application.yml`` (the Spring config)
---------------------------------------------

Key sections:

* **Logging** — pattern, level overrides
* **Metrics** — Micrometer histogram bin definitions; observability sidecar
  prefix filter
* **SQS** — queue URL env-vars (``SQS_*_QUEUE_URL``), worker-group mapping
* **Analytics** — product name for GASv3 events

3.2 ``logback-spring.xml``
----------------------------

JSON log layout for Splunk ingest. Includes MDC fields (``request_id``,
``tenant_id``, ``account_id``, …) at the top level so Splunk indexes them
without parsing.

3.3 ``policies/service/policy.json``
--------------------------------------

POCO (compute-classification + retry policies) for inbound endpoints.

4. Three runtime topologies (one image, three groups)
========================================================

Same Docker image, three Micros worker groups:

* **WebServer** (default) — serves HTTP on :8080
* **SHWorkers** — drains the ``analytics_events`` queue (StreamHub events)
* **LongRun** — drains long-running task queues (e.g. rovo-insights)

Worker-group activation is controlled by Spring conditions
(``OnSHWorkerNodeOrLocalCondition``, ``OnLongRunWorkerNodeOrLocalCondition``)
in the ``config/`` package — beans destined for a different group don't
exist in the bean graph on this pod.

5. Resources provisioned per environment
==========================================

5.1 Redis (Valkey 7.x) — ``proactive-ai-cache``
-------------------------------------------------

* Instance type: ``cache.t4g.small`` (start small per PR #96 guidance)
* Cluster mode: disabled (single primary + 1 replica)
* Transit encryption: enabled
* Data type tags: ``Identifier/OfEntity``, ``UGC/Raw``, ``PD/Pseudonymous``
* Alarms: ``EngineCPUUtilization`` (Redis is single-threaded, so this is the
  precise load signal)

5.2 SLAuth gateway — ``proactive-ai-gateway``
-----------------------------------------------

The Micros-provided SLAuth ingress.

5.3 Mesh dependencies (env vars Micros injects)
-------------------------------------------------

* ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL``
* ``MESH_DEPENDENCY_ID_GATEKEEPER_BASE_URL``
* ``MESH_DEPENDENCY_INTEGRATIONS_SERVICE_BASE_URL`` (added in PR #108)

5.4 SQS queues
----------------

Provisioned via terraform/Spinnaker (not in service descriptor today).
URLs injected as env vars (``SQS_*_QUEUE_URL``).

6. Local development
======================

See ``LOCAL_DEV.md`` in the repo root. Highlights:

* ``./gradlew bootRun`` to start WebServer locally
* Set ``ATL_MICROS_GROUP=LongRun`` to start a worker pod locally
* SQS endpoints can be pointed to LocalStack via env-var override

7. Observability runbooks
============================

Today's ``service-descriptor.sd.yml`` references runbook URLs as ``TBD``
(captured as a known gap). Once authored they will live under the
``go/proactive-ai-platform-runbook`` short-link convention.

8. See also
==============

* :doc:`/modules/platform/config` — Spring beans + conditions
* :doc:`05-observability-and-metrics` — metrics + logging chapter
* :doc:`/overviews/03-criticality-dashboard` — incident playbook entries
