.. _mod-prompt-moderation:

====================
Prompt Moderation
====================

:Files: ``src/service/moderation/prompt/prompt_moderation.py``, ``src/api/v1/moderation/prompt_moderation_controller.py``, ``src/api/v1/moderation/etag/prompt_etag.py``
:Importance: **P1 — most-used moderation path**

Purpose
========

Screens text prompts (user inputs to AI features) against 15 harm categories
before they are sent to LLMs. Returns ALLOWED or DISALLOWED with a harm category
and violation score.

API contract
=============

**Request** (``ModeratePromptRequest``):

.. code-block:: json

   {
     "prompt": "string (min_length=1)",
     "debug": {
       "verbose": false,
       "feature_overrides": {"gate_name": true}
     }
   }

Required headers: ``X-Atlassian-Cloud-Id``, ``X-Atlassian-Use-Case-Id``,
plus one-of: ``X-Slauth-User-Context`` or ``X-Atlassian-Staff-Context-Token``.

**Response body** (``ModeratePromptResponse``):

.. code-block:: json

   {
     "status": "ALLOWED | DISALLOWED",
     "harm_category": "none | violence_harassment | hate_discrimination | ...",
     "trace": null
   }

**Response headers**:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Header
     - Value
   * - ``X-RAI-Model-Evaluation-Version``
     - Model version string (e.g. ``"v2.3.3"``)
   * - ``X-RAI-Prompt-Evaluation-Version``
     - Prompt template version string
   * - ``X-RAI-Prompt-Violation-Score``
     - Float score 0.0–1.0 (e.g. ``"0.87"``)
   * - ``ETag``
     - ``W/"<base_hash>:<category_hash>"``

ETag caching
=============

The prompt moderation endpoint implements HTTP caching via ``If-None-Match`` /
``ETag`` to avoid re-running inference on duplicate prompts.

**ETag generation** (``prompt_etag.py``):

.. code-block:: python

   base_hash = SHA256(prompt + model_version)[:16]  # truncated
   category_hash = SHA256(harm_category)[:8]
   ETag = f'W/"{base_hash}:{category_hash}"'

**Cache check flow**:

1. Client sends ``If-None-Match: W/"abc:def"``
2. Server re-computes ``base_hash`` from request body
3. Generates all possible ETags (one per ``PromptHarmCategory`` + one without category)
4. If ``If-None-Match`` in possible_etags → return HTTP 304 (no inference)

This means a repeated identical prompt always hits cache regardless of which
harm category was previously determined — the client doesn't need to know the
category to benefit from caching.

Decision logic
===============

.. code-block:: text

   violation_score >= threshold → DISALLOWED (harm_category = detected_category)
   violation_score <  threshold → ALLOWED    (harm_category = "none")

Thresholds are per-category and per-model-version, loaded from Feature Service
with 60s TTL cache. Default: 0.5 for all categories.

Debug trace
============

When ``debug.verbose=true``:

.. code-block:: json

   {
     "trace": {
       "service_version": "1.2.3",
       "environment": "staging",
       "model_evaluation_version": "v2.3.3",
       "prompt_evaluation_version": "v2.3.3",
       "model_id": "rai-ft-content-filter-v2-3-3",
       "gateway_endpoint": "/v1/msp/rai-ft-content-filter-v2-3-3",
       "error_detail": null,
       "error_type": null,
       "extra": {"feature_overrides_applied": {"gate": true}}
     }
   }

On error, ``error_detail`` includes exception chain: ``ExcType: msg | caused by CauseType: cause_msg``.

Metrics emitted
================

On every request (success or failure):

* ``PROMPT_MODERATION_OUTCOME`` counter with tags:
  ``use_case_id``, ``outcome`` (ALLOWED/DISALLOWED/exception), ``harm_category``,
  ``model_version``, ``evaluation_version``, ``fail_open_type``
* ``PROMPT_MODERATION_LATENCY`` histogram (via ``@measure_latency``)
* Token bucket: ``consumed_tokens`` → one of [256, 512, 1K, 2K, 4K, 8K, 16K, 32K+]
* Overflow ratio bucket: ``token_overflow_ratio`` → one of [0, 10%, 20%, ..., 90-100%]

GASv3 event emitted:

* ``ContentEvaluatedEvent`` with fields: cloud_id, user_id, evaluation_version,
  detected_harm_category, outcome, violation_score

Connection pool logging (debug)
================================

When ``is_connection_pool_logging_enabled()`` feature flag is on, logs the state
of the httpx transport connection pool after each request. Used to diagnose
connection exhaustion under load.
