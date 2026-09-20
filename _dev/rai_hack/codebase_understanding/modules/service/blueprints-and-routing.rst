.. _mod-blueprints-and-routing:

==============================
Blueprints & Routing
==============================

:Files: ``src/api/api_blueprint.py``, ``src/api/v1/api_v1_blueprint.py``, ``src/api/v1/moderation/moderation_blueprint.py``, ``src/api/v1/admin/admin_blueprint.py``
:Importance: **P0 — all request routing**

Flask Blueprint Hierarchy
==========================

::

   Flask app (app.py)
   ├── healthcheck_blueprint        → url_prefix="/"
   │   ├── GET /healthcheck         → healthcheck status JSON
   │   ├── GET /ping                → {"pong": true}
   │   └── GET /status              → service version + uptime
   │
   └── api_blueprint                → url_prefix="/"
       └── api_v1_blueprint         → url_prefix="/v1"
           ├── admin_blueprint      → url_prefix="/v1/admin"
           │   └── GET /v1/admin/config   → config inspection (internal)
           │
           └── moderation_blueprint → url_prefix="/v1/moderation"
               ├── prompt_moderation_blueprint  → url_prefix="/v1/moderation/prompt"
               │   └── POST /v1/moderation/prompt/
               ├── output_moderation_blueprint  → url_prefix="/v1/moderation/output"
               │   └── POST /v1/moderation/output/
               ├── agent_moderation_blueprint   → url_prefix="/v1/moderation/agent"
               │   └── POST /v1/moderation/agent/
               └── image_moderation_blueprint   → url_prefix="/v1/moderation/image"
                   └── POST /v1/moderation/image/

App-level routes (``app.py``):

* ``GET /`` → ``{}`` (minimal liveness check)
* ``GET /api/swagger-ui/index.html`` → Swagger UI HTML
* ``GET /api/swagger-ui`` → redirect to index
* ``GET /openapi.json`` → parsed ``swagger.yaml`` as JSON

Middleware (moderation_blueprint)
===================================

Applied to ALL moderation requests via ``@moderation_blueprint.before_request``
and ``@moderation_blueprint.teardown_request``:

.. code-block:: python

   @moderation_blueprint.before_request
   def setup_request_logging_context():
       LoggingContextManager.setup_context()
       # Sets: request_id, cloud_id, use_case_id in MDC

   @moderation_blueprint.teardown_request
   def cleanup_log_context(exc):
       LoggingContextManager.cleanup_context(exc)
       # Clears MDC context; logs exception if present

This ensures structured logging includes request context on every log line
during moderation processing.

Strict URL matching
=====================

All moderation endpoints use ``strict_slashes=False``:

.. code-block:: python

   @prompt_moderation_blueprint.post("/", strict_slashes=False)

This means both ``/v1/moderation/prompt/`` and ``/v1/moderation/prompt``
are accepted, preventing 301 redirects that would break streaming clients.
