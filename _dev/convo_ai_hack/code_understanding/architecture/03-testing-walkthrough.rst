.. _testing-walkthrough:

================================================================
Testing walkthrough — how to verify your changes
================================================================

This document is the **codebase-perspective** companion to the operational SOP at
``_dev/_plan/convo_ai_hack/test_sop/`` (8 files, 1,500+ lines).

Whereas the SOP answers *"how do I run X"* with exact commands, this document answers
*"what does the test infrastructure look like, what does it test, and how do I extend it"*
from a code architect's perspective.

The truth on the ground (verified 2026-05-04)
================================================

* **6 distinct test surfaces** exist in this repo (was previously documented as 3).
* **18-container Nebulae sandbox** wires up every external dependency; can be re-used
  across test invocations for 5-10× faster iteration.
* **Load testing** is real and uses Locust 2.20.1 + Atlassian perfkit; lives at
  ``operations/perfhammer/`` (NOT in ``test/``); two scripts cover the two highest-SLO
  endpoints.
* **Evaluation testing** uses the in-repo **LLMJudge** framework (NOT Arize directly);
  production runs orchestrated from Databricks via
  ``operations/pollinator/scripts/llm_judge_evaluation.py``.

The 6 test surfaces
======================

.. list-table::
   :header-rows: 1
   :widths: 18 32 30 20

   * - Surface
     - Where (path)
     - What it asserts
     - Run command
   * - **Unit**
     - Every module's ``src/test/kotlin``; sharded into ``core``, ``rovo``, ``product``
       via ``-PunitTestShard=...``.
     - Pure logic correctness; mocked deps; no Spring context, no Docker.
       Targets ~5-10 min total.
     - ``./gradlew test``
   * - **Startup smoke**
     - ``convo-ai-test-integration/.../FullContextStartupIT.kt``; tagged
       ``@Tag("startup-test")``.
     - The full Spring ApplicationContext boots successfully across all 84 modules.
       Catches Spring wiring breakage, autoconfig conflicts, missing beans.
     - ``./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true``
   * - **Integration**
     - ``convo-ai-test-integration/src/test/kotlin/it/...``; 250+ tests; tagged
       ``@Tag("integration-test")``; sharded into 4 × {FlagsOn, FlagsOff} = 8 shards in CI.
     - HTTP-level behavior: controllers, services, persistence, downstream calls
       (mocked via WireMock), AWS interactions (mocked via LocalStack), tenant context
       (mocked via TCS sidecar).
     - ``./gradlew :convo-ai-test-integration:integrationTest -Pnebulae.enabled=true``
   * - **Evaluation (BatchEval)**
     - ``convo-ai-test-integration/.../AgentStudioBatchEvaluation*IT.kt`` exercises the
       framework at ``modules/platform/evaluation/``.
     - Plumbing of the LLM-Judge eval pipeline: ``BatchEvaluationJob`` lifecycle,
       ``BatchEvaluationDatasetStore`` round-trip, ``BatchJudgementExecutionService``
       dispatch, ``ErsEvaluationResult`` persistence. WireMock-canned LLM responses.
     - ``./gradlew :convo-ai-test-integration:integrationTest --tests '*BatchEvaluation*' -Pnebulae.enabled=true``
   * - **Load (perfhammer/Locust)**
     - ``operations/perfhammer/tests/{rovo-chat-stream-api.py, aifc-page-create-stream-api.py}``
       + ``client/rest_client.py``.
     - Streaming-API throughput / saturation against local sandbox, staging, or (with
       approval) prod. Validates capacity claims (T-series in v7 plan).
     - ``cd operations/perfhammer && locust -f tests/rovo-chat-stream-api.py``
   * - **Live-sandbox iteration**
     - Re-uses an already-running ``convo-ai-integration-tests-<session-id>-*`` Compose
       project (currently session ``3f2a39fb`` started 2026-05-01).
     - Skips the 60-180 s Nebulae start/stop overhead; identical assertions to the
       Integration surface.
     - ``./gradlew … -Pnebulae.enabled=false``

Architecture of the integration sandbox
=========================================

The Nebulae sandbox is a Docker Compose project laid out at
``.nebulae/integration-tests/docker-compose.*.yml``. The full set of files is broken
into:

* ``docker-compose.resources.yml`` — primitives (Redis, Memcached, LocalStack,
  Step Functions, statsd)
* ``docker-compose.dependencies.yml`` — Atlassian-specific mocks (TCS sidecar, SLAuth
  sidecar, ERS control/data, TDP control/OS, Hofund)
* ``docker-compose.webserver.yml`` — egress mocks, Nebulae proxy (envoy), wiremock,
  S3 blackhole sink
* …and a few more for asap-env-post-provision and per-container env

Total: **18 containers**. Service map verified at
``_dev/_plan/convo_ai_hack/test_sop/08-live-sandbox.md`` §B.

The convo-ai-platform application itself does NOT run inside this sandbox by default.
It runs in your terminal (``./gradlew :convo-ai-test-integration:bootRun``) and binds to
the sandbox's services via the env vars / port mappings exported by Nebulae.

Test data flow
================

Reading ``convo-ai-test-integration/build.gradle.kts``:

* Lines 14-18 — explicit exclusion of ``docker-java-transport-httpclient5`` to prevent
  background thread leaks across FlagsOn/FlagsOff context restarts (a real bug fix).
* Lines 20-30 — ``INTEGRATION_TEST_SHARD_COUNT`` env var (default 4); CI runs 4 shards
  × 2 flag modes = 8 parallel jobs.
* Implementation depends on ~30 platform/product modules, demonstrating that
  ``convo-ai-test-integration`` is the **only** module where everything wires together.

WireMock stubs live at
``convo-ai-test-integration/src/test/resources/wiremocks/`` and are organized by
external-system name:

.. code-block:: text

   wiremocks/
   ├── ai_gateway/         # canned LLM responses
   ├── assistance-service/ # CSM out-of-process orchestrator
   ├── streamhub/          # Atlassian streaming bus mock
   ├── devai-rovodev-streamhub/
   ├── graphql-gateway/    # AGG gateway mock
   ├── jira-project-components/
   └── …

Test JSON fixtures (request bodies, expected responses) live at
``convo-ai-test-integration/src/test/resources/json/{adf, responses/{sain,playground,whiteboardaiteammate,aifeature,…}}``.

Where to put a new integration test
======================================

* Pick a sub-package under ``it.io.atlassian.micros.convoai.{your-domain}.``;
  this auto-tags it ``@Tag("integration-test")`` via the base class.
* Extend ``IntegrationTest`` (at
  ``convo-ai-test-integration/.../IntegrationTest.kt``) for the standard fixtures
  (TCS, ARI generation, headers).
* Add WireMock stubs as ``.json`` files under
  ``src/test/resources/wiremocks/<system-name>/`` and load them via the existing
  ``WireMockExtension`` setup in the base class.

Where to put a new load test
==============================

* Add a Python file at ``operations/perfhammer/tests/<endpoint>.py`` following the
  pattern in ``rovo-chat-stream-api.py`` (Locust ``HttpBaseUser`` + ``BaseTaskSet``).
* Use ``client.rest_client.RestClient`` for header injection.
* Validate streamed-response JSON-line bodies inline (cf. lines 57-67 of the example).
* If the new endpoint takes a different payload shape, factor the payload to a
  module-private constant; do not hardcode in the ``@task`` body.

Where to put a new evaluation
================================

* Define a new ``EvaluationDataset`` row by writing a Kotlin migration / fixture under
  ``modules/platform/evaluation/impl/.../store/``.
* Define a new judge prompt under ``modules/product/{rovo,csm}/evaluation/`` (extend the
  existing ``EvaluationStrategy`` interface).
* Wire it into the GraphQL ``startBatchEvaluation`` mutation so callers can opt in.
* Add a BatchEval integration test at
  ``convo-ai-test-integration/.../AgentStudioBatchEvaluationV1ControllerIT.kt`` that
  asserts your judge dispatch + result persistence.
* For the production nightly run, add a row to the Databricks-side dataset table that
  ``operations/pollinator/scripts/llm_judge_evaluation.py`` reads.

Cross-references
==================

* Operational SOP (commands, prereqs, troubleshooting): ``_dev/_plan/convo_ai_hack/test_sop/``
  (8 files; ``00-overview.md`` is the entry point).
* v7 plan integration with tests: ``_dev/_plan/convo_ai_hack/_plan/convo_ai/INTEGRATED_PLAN_v7_synthesis.md`` §13.
* Per-module test status: see the per-module pages in :doc:`../modules/index`.
* AI Gateway test surface (auth, ASAP token, mock): see :doc:`../architecture/cross-cutting/01-ai-gateway`.

Honest caveats
=================

* The **end-to-end real-LLM evaluation** is operator-driven and requires Sliver
  credentials for AI Gateway. There is no public CLI runner in this repo.
* The **AIFC golden-set evaluation** (referenced as M1 / Q13 in the v7 plan) does
  not yet exist as a checked-in dataset; v7 Q13 is the work item to create it.
* The **CI does not run perfhammer**. Load tests are operator-driven and scheduled
  ad-hoc by the on-call. v7 marks this as a gap.
* The **assistance-service** is a separate microservice; integration tests in this
  repo mock it via WireMock. Real cross-service behavior is verified only in
  staging end-to-end.
