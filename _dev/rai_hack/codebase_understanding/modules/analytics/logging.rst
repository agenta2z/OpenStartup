.. _mod-logging:

===================
Structured Logging
===================

:File: ``src/micros_logging.py`` (198 LoC), ``src/gunicorn_logger.py`` (102 LoC)

Overview
=========

RAI uses structured JSON logging via the Atlassian Micros logging standard.
All log lines include MDC (Mapped Diagnostic Context) fields for correlation.

``LoggingContextManager`` (``micros_logging.py``):

* ``setup_context()`` — called in ``moderation_blueprint.before_request``
  Sets MDC fields: ``request_id`` (UUID), ``cloud_id``, ``use_case_id``, ``user_id``

* ``cleanup_context(exc)`` — called in ``moderation_blueprint.teardown_request``
  Clears MDC; if exc is not None, logs exception with full traceback

MDC fields propagate automatically to all log lines within the request context,
enabling correlation in log aggregation systems (Sumo Logic, Splunk).

Log levels:
* INFO — normal moderation outcomes, model selection decisions
* WARNING — malformed model output, validation failures, retry attempts
* ERROR — inference failures, unhandled exceptions, missing configuration
