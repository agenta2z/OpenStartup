.. _mod-image-moderation:

====================
Image Moderation
====================

:Files: ``src/service/moderation/image/image_moderation.py``, ``src/inference_models/image_moderation_sagemaker.py`` (325 LoC)
:Importance: **P1 — image upload safety gate**

Purpose
========

Screens images uploaded to Atlassian products against 12 harm categories using
two parallel SageMaker inference models (V0: object detection, V1: ShieldGemma2
multimodal) plus an optional anti-abuse scan.

API contract
=============

**Request** (``ModerateImageRequest``):

.. code-block:: json

   {
     "image_data": "<base64-encoded-image>",
     "type": "base64",
     "format": "jpg",
     "file_id": "optional-uuid",
     "container_id": "optional-uuid",
     "user_id": "optional-aaid",
     "region": "us-east-1",
     "platform": "confluence"
   }

**Response** (``ModerateImageResponse``):

.. code-block:: json

   {
     "status": "ALLOWED | DISALLOWED",
     "harm_category": "none | human | hate_discrimination | ..."
   }

**Response V1** (when ``is_standardized_image_moderation_response_enabled()``):

.. code-block:: json

   {
     "status": "ALLOWED | DISALLOWED",
     "harm_category": "none | human | ...",
     "abhorrent_material": false,
     "actions": {"deletion": false},
     "comment": null
   }

Response headers: ``X-RAI-Model-Evaluation-Version`` (from V1 model).

Harm categories (``ImageHarmCategory``)
=========================================

12 categories (StrEnum): ``HUMAN``, ``NONE``, ``UNKNOWN``, ``HATE_DISCRIMINATION``,
``VIOLENCE_HARASSMENT``, ``MISINFORMATION``, ``ILLEGAL_ACTIVITY``,
``JAILBREAK_PROMPT_INJECTION``, ``INTELLECTUAL_PROPERTY``, ``PII``,
``POLITICS``, ``IMPERSONATION``, ``SPECIALIST_ADVICE``, ``HIGH_RISK_DECISIONS``.

``MODERATION_THRESHOLD = 0.4`` (for V0 HUMAN class; V1 uses ``config.image_moderation_v1_threshold = 0.5``).

Parallel inference architecture
=================================

``ImageModerationSageMaker`` uses gevent ``Pool`` for parallel V0+V1 execution:

.. code-block:: text

   gevent.Pool.spawn(v0_inference) ──┐
                                     ├─► merge results
   gevent.Pool.spawn(v1_inference) ──┘

Pool fallback: if pool is full, runs V0 only (V1 skipped, not fail-open on V1).

**V0 model** (DEIM/D-FINE large object detector):

* SageMaker endpoint: ``image-moderation-v0`` (configurable)
* Input: ``{"image": "<base64>"}``
* Output: ``[{"class": "human", "score": 0.95}, {"class": "nudity", ...}]``
* ``get_max_score_from_output()`` → finds max score across all classes
* Primary purpose: detect human presence (NSFW content, CSAM risk)

**V1 model** (ShieldGemma2 multimodal):

* SageMaker endpoint: ``image-moderation-v1-model`` (configurable)
* Input: ``{"image": "<base64>", "policies": [...]}``
* Output: ``{"policy": "str", "prediction": {"category": score}}``
  where categories map to: HATE_DISCRIMINATION, VIOLENCE_HARASSMENT, SEXUAL_CONTENT, etc.
* 12 harm categories; threshold: 0.5

**Anti-abuse scan** (concurrent, best-effort):

* ``AntiAbuseClient.scan_content(AntiAbuseRequest)``
* Circuit breaker: fail_max=5, reset_timeout=60s
* Classifications: SPAM, ABUSE, POLICY_VIOLATION, CLEAN
* Result merged into final response if non-CLEAN

Result merging logic
=====================

.. code-block:: text

   priority order (highest wins):
   1. V1 policy violation (ShieldGemma2 detected a policy category above threshold)
   2. V0 human class (HUMAN/nudity above V0 threshold)
   3. V0 top category (highest scoring non-human class from V0)
   4. NONE (no violations found)

   final violation_score = max(V0_max_score, V1_max_score)
   final anti_abuse_classification merged if POLICY_VIOLATION or ABUSE

SageMaker invocation (``sagemaker_base.py``)
=============================================

* ``invoke_sagemaker_endpoint(payload: dict) -> dict``
* Uses boto3 ``SageMakerRuntimeClient.invoke_endpoint()``
* Role assumption: ``arn:aws:iam::540824312222:role/SageMakerExecutionRole``
  (auto-refreshed on credential expiry)
* Timeout: ``config.sagemaker_inference_timeout`` (default 30s)
* JSON encode/decode with ``ContentType="application/json"``
* Retry on boto3 ``ClientError`` with credential expiry code

Image preprocessing (optional)
================================

When ``is_extra_image_preprocessing_enabled()`` feature flag is on:

* Additional preprocessing applied before base64 encoding
* Purpose: normalize image format, resize extreme dimensions
* ``ENABLE_EXTRA_IMAGE_PREPROCESSING`` Statsig gate

Analytics emitted
==================

``ImageEvaluatedEvent``: cloud_id, user_id, evaluation_version,
detected_harm_category, outcome, violation_score, image_size_bucket
(via ``image_buckets.get_image_size_bucket(width, height)``).
