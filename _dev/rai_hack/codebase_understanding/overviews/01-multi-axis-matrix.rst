.. _rai-multi-axis-matrix:

============================================================
Multi-axis Module Overview Matrix
============================================================

:Date: 2026-05-04
:Verification: ``find … | wc -l`` + ``wc -l`` run on actual source trees.

---

Axis A: Repository × Layer size matrix
----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 10 35

   * - Layer
     - Src Files
     - Src LoC
     - Test Files
     - Role
   * - **rai-api / API & Routing**
     - 12
     - ~700
     - 5
     - Flask blueprints, controllers, Pydantic schemas, ETag, debug trace
   * - **rai-api / Inference Models**
     - 12
     - ~1,680
     - 8
     - LLaMA, GPT-OSS, SageMaker, Triton gRPC/OpenAI, shadowing, confidence thresholds
   * - **rai-api / Service Moderation**
     - 20
     - ~1,200
     - 10
     - 4 moderation pipelines, harm categories, stream processor, URL checker
   * - **rai-api / Observability**
     - 12
     - ~700
     - 5
     - Prometheus metrics, GASv3 analytics events, structured logging
   * - **rai-api / Support**
     - 38
     - ~900
     - 12
     - Config, slauth, tenant context, Statsig, time-cache, anti-abuse, ML platform client
   * - **rai-api TOTAL**
     - **94**
     - **5,272**
     - **40+**
     -
   * - **responsible-ai / harm_taxonomy**
     - 1
     - ~50
     - 0
     - 16-category HarmCategory Enum (canonical shared taxonomy)
   * - **responsible-ai / notebooks/data**
     - 6
     - ~400
     - 0
     - RAI_Dataset Pandera schema, multi-source ingestion, stratified sampling
   * - **responsible-ai / notebooks/evaluation**
     - 10
     - ~700
     - 0
     - Offline eval (sklearn metrics), online LLM judge workflow, MLflow, Databricks
   * - **responsible-ai / experiments/image_moderation_v1**
     - 10
     - ~600
     - 0
     - ShieldGemma2 pipeline, LLaVAGuard eval, SageMaker deploy, latency benchmarks
   * - **responsible-ai / experiments/PII_Anonymization**
     - 1
     - ~80
     - 0
     - Presidio-based PII anonymization (12 entity types)
   * - **responsible-ai / msp_deploy**
     - 4
     - ~200
     - 0
     - MSP compliant model registration (DEIM/D-FINE V0, LLaMA V2.4)
   * - **responsible-ai / analytics/terraform**
     - ~10
     - ~300
     - 0
     - Terraform IaC for Livegraph dashboards (ethical filtering analytics)
   * - **responsible-ai TOTAL**
     - ~42
     - ~2,330
     - 0
     -

---

Axis B: Size class distribution (responsible-ai-api by file)
--------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 12 63

   * - Size class
     - Count
     - Representative files
   * - **Large (>300 LoC)**
     - 5
     - ``rai_llama.py`` (689), ``prompt_moderation_metrics.py`` (345), ``image_moderation_sagemaker.py`` (325), ``metrics_handler.py`` (305), ``rai_gpt_oss.py`` (287)
   * - **Medium (100–300 LoC)**
     - 18
     - ``model.py`` (281), ``error_handling.py`` (237), ``app_context.py`` (~200), ``micros_logging.py`` (198), ``ml_platform/input_moderation_client.py`` (193), ``antiabuse_client.py`` (189), ``config.py`` (182), ``rai_analytics_client.py`` (178), ``app.py`` (163), ``slauth/user_context.py`` (155), ``triton_grpc_client.py`` (148), ``antiabuse_utils.py`` (123), ``exception.py`` (105), ``tenant_context_client.py`` (104), ``sagemaker_base.py`` (104), ``gunicorn_logger.py`` (102), ``healthcheck.py`` (258), ``feature_service.py`` (256)
   * - **Small (<100 LoC)**
     - 71
     - All schema files, ``__init__.py``, ``time_cache.py`` (26), ``errors.py`` (18), ``use_cases.py`` (7), etc.

---

Axis C: Criticality ranking
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 8 30 62

   * - Tier
     - Module(s)
     - Blast radius if broken
   * - **P0**
     - ``app.py``, ``config.py``
     - Full service outage; missing ASAP_ISSUER/ASAP_PRIVATE_KEY prevents startup
   * - **P0**
     - ``moderation_blueprint.py``, blueprint registration
     - All 4 moderation endpoints return 404
   * - **P0**
     - gunicorn/gevent worker pool
     - Worker exhaustion → 502 gateway errors
   * - **P1**
     - ``prompt_moderation.py``, ``rai_llama.py``
     - All prompt/output moderation bypassed (most-used path); fail-open on model timeout
   * - **P1**
     - ``agent_moderation.py``, ``rai_gpt_oss.py``
     - Agent safety screening broken (Rovo, AgentStudio)
   * - **P1**
     - ``image_moderation.py``, ``image_moderation_sagemaker.py``
     - Image uploads unscreened
   * - **P1**
     - ``feature_service.py`` (Statsig)
     - Model selection falls to defaults; shadowing/fail-open flags may misbehave
   * - **P2**
     - ``rai_analytics_client.py``
     - GASv3 moderation events lost; async non-blocking → no customer impact
   * - **P2**
     - ``metrics_handler.py``
     - Prometheus dashboards dark; alerting may miss incidents
   * - **P2**
     - ``antiabuse_client.py``
     - Anti-abuse scan fail-open; images pass without CSAM/spam check
   * - **P3**
     - ``prompt_etag.py``, ``time_cache.py``
     - Cache miss → inference on every request; higher cost/latency
   * - **P3**
     - ``debug_trace_builder.py``
     - debug.verbose traces unavailable; developer experience impact only

---

Axis D: Test coverage by layer
--------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Layer
     - Approx test files
     - Test strategy
   * - API controllers
     - 5
     - pytest + Flask test client; mock services
   * - Service moderation
     - 10
     - pytest; mock inference models; harm category round-trips
   * - Inference models
     - 8
     - pytest; mock SageMaker/Triton; circuit breaker state tests
   * - Metrics & analytics
     - 5
     - pytest; mock GASv3 client; metric tag assertions
   * - Integration tests
     - 10+
     - ``nebulae`` environment; WireMock stubs for AI Gateway
   * - Regression tests
     - 1 suite
     - Eval set (labeled prompts); precision/recall thresholds
   * - Capacity tests
     - 2
     - Load tests for agent + prompt moderation endpoints
