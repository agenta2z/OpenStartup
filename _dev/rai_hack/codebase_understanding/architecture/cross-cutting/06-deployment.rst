.. _rai-deployment:

========================
Deployment & CI/CD
========================

Service deployment (responsible-ai-api)
==========================================

**Container**: Docker image built from ``Dockerfile``

* Base: PyTorch 2.6.0 image with Python 3.12
* Entrypoint: gunicorn with gevent workers
* Port: 8080 (exposed internally)

**Runtime**: Atlassian Micros (internal Kubernetes-based PaaS)

* Service registration via ``nebulae.yml``
* Health check endpoints: ``/healthcheck``, ``/ping``, ``/status``
* Resource allocation defined in Micros service descriptor

**Build output** (``build-output/``):

* ``git-version.json`` — git SHA and branch
* ``release-version.json`` — semver release version
* ``config.py`` reads both at startup: ``config.version = release_version["version"]``

**Environment variables** (required in production):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Purpose
   * - ``ASAP_ISSUER``
     - ASAP JWT issuer identity
   * - ``ASAP_PRIVATE_KEY``
     - ASAP private key (Data URI format)
   * - ``STATSIG_SERVER_SDK_KEY``
     - Statsig Server SDK key
   * - ``MICROS_ENVTYPE``
     - Environment type (dev/staging/prod)
   * - ``MICROS_SERVICE_DOMAIN_NAME``
     - Service domain for self-reference
   * - ``MICROS_AWS_REGION``
     - AWS region for SageMaker
   * - ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL``
     - AI Gateway base URL (set by Micros service mesh)
   * - ``SM_ENDPOINT_IMAGE_MODERATION_V0_ENDPOINT_NAME``
     - SageMaker V0 endpoint name
   * - ``SM_ENDPOINT_IMAGE_MODERATION_V1_MODEL_ENDPOINT_NAME``
     - SageMaker V1 endpoint name
   * - ``TCS_SIDECAR_HOST``
     - TCS sidecar host (default: localhost)
   * - ``TEAMSERVE_ENDPOINT``
     - Teamserve gRPC host
   * - ``TEAMSERVE_GPTOSS_ENDPOINT``
     - Teamserve GPT-OSS HTTP endpoint URL

CI/CD (``bitbucket-pipelines.yml``)
======================================

Stages:

1. **Build** — Docker image build + push to Atlassian container registry
2. **Test** — ``pytest test/unit_tests/`` + integration tests in Nebulae env
3. **Deploy DEV** — automatic on main branch merge
4. **Deploy STAGING** — automatic after DEV deploy succeeds
5. **Deploy PROD** — manual approval gate + Spinnaker pipeline

Testing environments:

* **Unit tests**: mock all external services (AI Gateway, SageMaker, Statsig)
* **Integration tests (Nebulae)**: WireMock stubs for AI Gateway and GPT-OSS Teamserve
  (``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL`` set to WireMock URL)
* **Regression tests**: run against labeled eval set; check precision/recall thresholds

Test file structure
====================

.. code-block:: text

   test/
   ├── conftest.py                     # top-level pytest config
   ├── unit_tests/
   │   ├── conftest.py                 # shared fixtures
   │   ├── feature_flag_fixtures.py    # Statsig gate mocks
   │   ├── api/
   │   │   ├── test_healthcheck.py
   │   │   ├── test_prompt_moderation_controller.py
   │   │   ├── test_output_moderation_controller.py
   │   │   ├── test_agent_moderation_controller.py
   │   │   └── test_image_moderation_controller.py
   │   ├── service/moderation/
   │   │   ├── prompt/test_prompt_moderation.py
   │   │   ├── prompt/test_prompt_harm_category.py
   │   │   ├── output/test_output_moderation.py
   │   │   ├── output/test_stream_processor.py
   │   │   ├── output/test_url_checker.py
   │   │   ├── agent/test_agent_moderation.py
   │   │   ├── agent/test_agent_harm_category.py
   │   │   ├── image/test_image_moderation.py
   │   │   ├── image/test_image_processing.py
   │   │   └── image/test_image_harm_category.py
   │   ├── inference_models/
   │   │   ├── test_rai_llama.py
   │   │   ├── test_rai_gpt_oss.py
   │   │   ├── test_image_moderation_sagemaker.py
   │   │   ├── test_triton_grpc_client.py
   │   │   ├── test_triton_openai_api_client.py
   │   │   ├── test_confidence_thresholds.py
   │   │   └── test_error_handling.py
   │   ├── metrics/
   │   │   ├── test_metrics_handler.py
   │   │   ├── test_prompt_moderation_metrics.py
   │   │   └── test_image_buckets.py
   │   └── gasv3_analytics/
   │       └── events/test_content_evaluated.py
   ├── integration_tests/
   │   ├── conftest.py
   │   ├── rai_api_client.py           # test HTTP client for live endpoints
   │   ├── test_prompt_moderation.py
   │   ├── test_output_moderation.py
   │   ├── test_agent_moderation.py
   │   ├── test_image_moderation.py
   │   ├── test_endpoints.py
   │   └── test_config.py
   ├── regression_tests/
   │   └── test_regression_suite.py   # precision/recall threshold checks
   ├── validation/
   │   ├── eval_utils.py
   │   └── run_models_on_eval_set.py
   └── capacity/
       ├── agent_moderation.py        # load test: agent endpoint
       └── prompt_moderation.py       # load test: prompt endpoint
