.. _rai-arch-overview:

==========================
Architecture Overview
==========================

System boundary
===============

The Responsible AI system sits **between Atlassian AI products and their LLM
backends**, acting as a content safety firewall. Every AI product (Rovo Chat,
AgentStudio, Confluence AI, JSM AI, Loom) must call ``responsible-ai-api``
to screen prompts before sending them to LLMs, and screen LLM outputs before
showing them to users.

::

   Atlassian AI Products
         │
         │  POST /v1/moderation/prompt/
         │  POST /v1/moderation/output/
         │  POST /v1/moderation/agent/
         │  POST /v1/moderation/image/
         ▼
   ┌──────────────────────────────────────┐
   │      responsible-ai-api              │
   │   (Flask + gevent, port 8080)        │
   │                                      │
   │   4 moderation pipelines             │
   │   + 4 inference backends             │
   │   + Statsig feature flags            │
   │   + Prometheus metrics               │
   │   + GASv3 analytics                  │
   └──────────────────────────────────────┘
         │                   │
         │ LLaMA/GPT-OSS     │ Image V0/V1
         ▼                   ▼
   MSP / Teamserve      AWS SageMaker
   (gRPC / HTTP)        (DEIM + ShieldGemma2)

   Research side:
   ┌──────────────────────────────────────┐
   │       responsible-ai                 │
   │   harm taxonomy + dataset pipeline   │
   │   offline/online eval + experiments  │
   │   MSP model registration             │
   └──────────────────────────────────────┘
         │ registers models ──────────────► MSP (consumed by rai-api)

Flask application structure
============================

.. code-block:: text

   src/
   ├── app.py                    # Flask app, error handlers, Swagger UI, main()
   ├── config.py                 # Config singleton (env vars, ASAP signer, endpoints)
   ├── feature_service.py        # Statsig wrapper (~30 feature gates)
   ├── exception.py              # APIException, make_api_error_response()
   ├── micros_logging.py         # Structured logging with MDC context
   ├── gunicorn.conf.py          # gevent worker class, 600s timeout
   │
   ├── api/
   │   ├── api_blueprint.py      # Root blueprint, registers healthcheck + v1
   │   ├── healthcheck.py        # /healthcheck, /ping, /status endpoints
   │   └── v1/
   │       ├── api_v1_blueprint.py          # /v1/ prefix
   │       ├── admin/admin_blueprint.py     # Admin endpoints (internal)
   │       └── moderation/
   │           ├── moderation_blueprint.py  # /v1/moderation/ — registers 4 sub-blueprints
   │           ├── prompt_moderation_controller.py
   │           ├── output_moderation_controller.py
   │           ├── agent_moderation_controller.py
   │           ├── image_moderation_controller.py
   │           ├── app_context.py           # Lazy service singletons
   │           ├── debug_trace_builder.py   # DebugTrace construction
   │           ├── etag/prompt_etag.py      # ETag cache check logic
   │           └── schema/                  # Pydantic request/response models
   │
   ├── service/moderation/
   │   ├── prompt/               # Prompt moderation pipeline
   │   ├── output/               # Output streaming moderation
   │   ├── agent/                # Agent config moderation
   │   └── image/                # Image moderation
   │
   ├── inference_models/         # ML inference abstractions + backends
   ├── gasv3_analytics/          # GASv3 event definitions + client
   ├── metrics/                  # Prometheus metric definitions
   ├── antiabuse/                # Anti-abuse HTTP client
   ├── ml_platform/              # MSP client (SyncMspWithRAIFT)
   ├── slauth/                   # SLAuth header parsing
   ├── tenant_context/           # TCS sidecar client
   ├── cache/                    # time_cache decorator
   ├── dynamic_config/           # Dynamic config client
   └── statsig_flags/            # Statsig local overrides (local dev)

App context and lazy initialization
=====================================

``api/v1/moderation/app_context.py`` uses module-level globals for service
singletons, initialized lazily on first request. This avoids circular imports
and allows the Flask app to start before all backends are available.

Services initialized once per worker process:

* ``prompt_service`` — ``PromptModerationService`` with AI Gateway sync client
* ``agent_service`` — ``AgentModerationService`` with AI Gateway Raw client
* ``image_service`` — ``ImageModerationService`` with SageMaker + anti-abuse clients
* ``output_service`` — ``OutputModerationService`` (wraps prompt_service)
* ``analytics_client`` — ``RAIAnalyticsClient`` (gevent pool 10)
* ``tenant_content_client`` — ``TenantContextClient`` (TCS sidecar HTTP)

AI Gateway client configuration:

* ``MAX_CONNECTIONS = 1024``; ``MAX_KEEPALIVE_CONNECTIONS = 204``
* ``connect_timeout = 10s``; ``read_timeout = 10s`` (default HTTP config)
* ``read_timeout = 2s`` (RAI FT config — strict latency SLO)
* Retry: tenacity with ``wait_random_exponential``, ``stop_after_attempt(3)``
  (only on TimeoutException/NetworkError, not 429)

Deployment configuration
==========================

* **Runtime**: Python 3.12, gunicorn + gevent workers
* **Port**: 8080 (internal); Micros routes via load balancer
* **Container**: Docker image built from ``Dockerfile``
* **Secrets via env**: ``ASAP_ISSUER``, ``ASAP_PRIVATE_KEY``, ``STATSIG_SERVER_SDK_KEY``,
  ``SM_ENDPOINT_IMAGE_MODERATION_V0_ENDPOINT_NAME``,
  ``SM_ENDPOINT_IMAGE_MODERATION_V1_MODEL_ENDPOINT_NAME``,
  ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL``, ``TCS_SIDECAR_HOST``
* **Nebulae**: Integration-test env with WireMock stubs for AI Gateway + GPT-OSS Teamserve
