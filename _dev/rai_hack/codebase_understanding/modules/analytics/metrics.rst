.. _mod-metrics:

===================
Prometheus Metrics
===================

:Files: ``src/metrics/metrics_handler.py`` (305 LoC), ``src/metrics/prompt_moderation_metrics.py`` (345 LoC), ``src/metrics/output_moderation_metrics.py`` (56 LoC), ``src/metrics/image_buckets.py`` (21 LoC)
:Importance: **P2 — observability**

Overview
=========

RAI emits Prometheus-compatible metrics for every moderation outcome. Metrics
are the primary signal for SRE alerting on model health, latency SLOs, and
fail-open rates.

Metric definitions (``metrics_handler.py``)
=============================================

``Metric`` enum (all are counter/gauge type via ``MetricType.INCREMENT``):

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Metric name
     - What it counts
   * - ``PROMPT_MODERATION_OUTCOME``
     - Every prompt moderation result (ALLOWED/DISALLOWED/exception)
   * - ``PROMPT_MODERATION_LATENCY``
     - Prompt moderation end-to-end latency histogram
   * - ``AGENT_MODERATION_OUTCOME``
     - Every agent moderation result
   * - ``IMAGE_MODERATION_OUTCOME``
     - Every image moderation result
   * - ``OUTPUT_MODERATION_OUTCOME``
     - Every output moderation chunk result
   * - ``PROMPT_NON_ALPHANUMERIC_RATIO``
     - Distribution of non-alphanumeric character ratio in prompts
   * - ``ANTIABUSE_CIRCUIT_BREAKER_STATE``
     - Anti-abuse circuit breaker open/closed state
   * - ``ANTIABUSE_RESPONSE_STATUS``
     - HTTP status code distribution for anti-abuse API calls

``MetricTag`` enum — tag keys used across metrics:

``USE_CASE_ID``, ``OUTCOME``, ``HARM_CATEGORY``, ``REGION``,
``NON_ALPHANUMERIC_BUCKET``, ``CIRCUIT_BREAKER_STATE``, ``HTTP_STATUS_CODE``,
``MODEL_VERSION``, ``EVALUATION_VERSION``, ``FAIL_OPEN_TYPE``,
``TOKEN_BUCKET``, ``OVERFLOW_RATIO_BUCKET``, ``IMAGE_SIZE_BUCKET``.

``@measure_latency(metric_name, derive_tags_from_result=fn)`` decorator:

* Wraps function with timer
* After function returns, calls ``derive_tags_from_result(result)`` to get tag dict
* Sends latency histogram metric with tags

Prompt moderation metrics (``prompt_moderation_metrics.py``)
=============================================================

``get_prompt_moderation_tags(result: ModeratePromptResponse) -> Dict[str, str]``:

Builds full tag set:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Tag key
     - Value
   * - ``OUTCOME``
     - ``"ALLOWED"`` or ``"DISALLOWED"``
   * - ``HARM_CATEGORY``
     - PromptHarmCategory value (e.g. ``"jailbreak_prompt_injection"``)
   * - ``MODEL_VERSION``
     - Model evaluation version string
   * - ``EVALUATION_VERSION``
     - Prompt evaluation version string
   * - ``FAIL_OPEN_TYPE``
     - Non-empty only if fail-open triggered (e.g. ``"TIMEOUT"``, ``"CIRCUIT_BREAKER_OPEN"``)
   * - ``TOKEN_BUCKET``
     - ``consumed_tokens`` bucketed: ``"256"``, ``"512"``, ``"1K"``, ``"2K"``, ``"4K"``, ``"8K"``, ``"16K"``, ``"32K+"``
   * - ``OVERFLOW_RATIO_BUCKET``
     - ``token_overflow_ratio`` bucketed: ``"0%"``, ``"10%"``, ``"20%"``, ..., ``"90-100%"``
   * - ``USE_CASE_ID``
     - From ``ModerationRequestContext.use_case_id``

``send_outcome_metrics()``: sends ``PROMPT_MODERATION_OUTCOME`` counter with above tags.

``send_exception_metrics()``: sends metrics for exception cases with ``outcome="exception"``.

Image size buckets (``image_buckets.py``)
==========================================

``get_image_size_bucket(width: int, height: int) -> str``:

Classifies images by pixel count (width × height):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Bucket
     - Pixel range
   * - ``"0-4K"``
     - < 4,096 pixels
   * - ``"4K-16K"``
     - 4,096–16,383
   * - ``"16K-65K"``
     - 16,384–65,535
   * - ``"65K-262K"``
     - 65,536–262,143
   * - ``"262K-1M"``
     - 262,144–1,048,575
   * - ``"1M-4M"``
     - 1,048,576–4,194,303
   * - ``"4M-16M"``
     - 4,194,304–16,777,215
   * - ``"16M+"``
     - ≥ 16,777,216
