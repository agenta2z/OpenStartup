.. _mod-app-and-config:

=======================
App Bootstrap & Config
=======================

:Files: ``src/app.py`` (163 LoC), ``src/config.py`` (182 LoC), ``src/gunicorn.conf.py`` (31 LoC), ``src/gunicorn_logger.py`` (102 LoC)
:Importance: **P0 — service startup**

Flask App (``app.py``)
========================

Entry point for the Flask application. Creates and configures the Flask instance,
registers all blueprints, and defines global error handlers.

Key initialization sequence:

.. code-block:: python

   app = Flask(__name__)
   app.wsgi_app = ProxyFix(app.wsgi_app)      # handles X-Forwarded-* from load balancer
   FlaskMicros(app)                            # Atlassian Micros integration
   app.register_blueprint(api_blueprint, url_prefix="/")
   app.register_blueprint(healthcheck_blueprint, url_prefix="/")
   app.config.update(FLASK_PYDANTIC_VALIDATION_ERROR_RAISE=True)  # strict validation

**Routes defined in app.py**:

* ``GET /`` → empty dict (liveness check)
* ``GET /api/swagger-ui/index.html`` → renders ``swagger_ui.html`` template
* ``GET /api/swagger-ui`` → redirects to ``/api/swagger-ui/index.html``
* ``GET /openapi.json`` → reads ``swagger.yaml``, returns as JSON

**Global error handlers** (all return ``make_api_error_response()``):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Exception type
     - Behaviour
   * - ``APIException``
     - Logs error; calls ``error.get_response()`` (status from exception)
   * - ``ValidationError`` (flask-pydantic)
     - Iterates body/form/path/query param errors; returns 400 JSON
   * - ``InternalServerError`` (werkzeug)
     - Logs original exception; surfaces debug_trace if present; returns 500
   * - ``NotFound``
     - Logs path; returns 404
   * - ``Exception`` (catch-all)
     - Logs unexpected error; surfaces debug_trace attribute; returns 500

**Debug trace propagation**: both ``InternalServerError`` and catch-all handlers call
``getattr(exception, "debug_trace", None)`` — the prompt moderation controller
attaches a ``DebugTrace`` to exceptions when ``debug.verbose=True``.

Config Singleton (``config.py``)
===================================

``Config`` is a module-level singleton (``config = Config()``). It reads all
environment variables once at import time and fails fast on missing required vars.

**Key configuration fields**:

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Field
     - Default
     - Source
   * - ``env_type``
     - ``EnvType.UNKNOWN``
     - ``MICROS_ENVTYPE`` env var; maps to EnvType enum
   * - ``service_url``
     - ``http://localhost``
     - ``MICROS_SERVICE_DOMAIN_NAME``
   * - ``micros_aws_region``
     - ``"unknown"``
     - ``MICROS_AWS_REGION``
   * - ``port``
     - ``8080``
     - hardcoded
   * - ``sm_endpoint_image_moderation``
     - ``"image-moderation-v0"``
     - ``SM_ENDPOINT_IMAGE_MODERATION_V0_ENDPOINT_NAME``
   * - ``sm_endpoint_image_moderation_v1``
     - ``"image-moderation-v1-model"``
     - ``SM_ENDPOINT_IMAGE_MODERATION_V1_MODEL_ENDPOINT_NAME``
   * - ``image_moderation_v0_threshold``
     - ``0.4``
     - ``IMAGE_MODERATION_V0_THRESHOLD``
   * - ``image_moderation_v1_threshold``
     - ``0.5``
     - ``IMAGE_MODERATION_V1_THRESHOLD``
   * - ``antiabuse_api_base_url``
     - per-env default
     - ``ANTIABUSE_API_BASE_URL`` or ``_get_default_antiabuse_url()``
   * - ``sagemaker_inference_timeout``
     - ``30``
     - ``SAGEMAKER_INFERENCE_TIMEOUT``
   * - ``greenlet_join_timeout``
     - ``30``
     - ``GREENLET_JOIN_TIMEOUT``
   * - ``inference_pool_size``
     - ``2``
     - ``INFERENCE_POOL_SIZE``
   * - ``statsig_sdk_key``
     - ``"secret-dummykey"``
     - ``STATSIG_SERVER_SDK_KEY``
   * - ``teamserve_endpoint``
     - ``grpc-teamserve-us-west-2.dev.services.kitt-inf.net``
     - ``TEAMSERVE_ENDPOINT``
   * - ``teamserve_gptoss_endpoint``
     - stg Teamserve URL (or WireMock in Nebulae)
     - ``TEAMSERVE_GPTOSS_ENDPOINT``
   * - ``tcs_url``
     - ``http://localhost:50050``
     - ``TCS_SIDECAR_HOST`` + ``TCS_SIDECAR_HTTP_PORT``

**ASAP JWT signer** — created at startup from ``ASAP_ISSUER`` + ``ASAP_PRIVATE_KEY``
(Data URI format). Uses ``atlassian_jwt_auth.create_signer(reuse_jwts=True)`` for
JWT token reuse within expiry window. On local env with ``NO_ASAP_SIGNER=true``,
replaced with ``Mock(JWTAuthSigner)`` for testing.

**Anti-abuse URL defaults by environment**:

.. code-block:: python

   {
       EnvType.DEV:     "https://abuse-filescanner.ap-southeast-2.dev.atl-paas.net",
       EnvType.STAGING: "https://abuse-filescanner-stg-east.staging.atl-paas.net",
       EnvType.PROD:    "https://abuse-filescanner-prod-east.prod.atl-paas.net",
   }

**Nebulae detection**: ``is_nebulae = os.environ.get("NEBULAE") == "true"``.
When Nebulae, ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL`` is set to local WireMock;
GPT-OSS Teamserve endpoint is patched to ``{ai_gw_base}/gptoss-teamserve/v1/chat/completions``.

Gunicorn Configuration
=========================

``src/gunicorn.conf.py``:

* ``worker_class = "gevent"`` — cooperative green threads
* ``workers`` — auto-scaled based on ``multiprocessing.cpu_count()``
* ``timeout = 600`` — maximum request processing time (seconds)
* ``keepalive = 5``
* Access log format: JSON structured via ``gunicorn_logger.py``

``src/gunicorn_logger.py``:

* Custom ``GunicornLogger`` extending gunicorn's ``Logger``
* Emits structured JSON access logs with: method, path, status, duration_ms, remote_addr
* Error logs forwarded to Python ``logging`` system with correct log levels

Time Cache (``cache/time_cache.py``)
========================================

A 26-line utility combining ``functools.lru_cache`` with time-based TTL:

.. code-block:: python

   @time_cache(max_age=60)       # 60-second TTL
   def get_prompt_harm_confidence_thresholds():
       ...

Implementation: wraps LRU cache key with ``__time_salt=int(time.time() / max_age)``.
Cache busts automatically every ``max_age`` seconds. Exposes ``cache_clear()`` for tests.
