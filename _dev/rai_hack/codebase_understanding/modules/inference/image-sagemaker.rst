.. _mod-image-sagemaker:

=============================
Image Moderation SageMaker
=============================

:File: ``src/inference_models/image_moderation_sagemaker.py`` (325 LoC)
:Importance: **P1 — image inference backend**

Overview
=========

Implements parallel SageMaker inference for image moderation using gevent
greenlets. Coordinates two model versions (V0: DEIM/D-FINE, V1: ShieldGemma2)
and merges their results.

``SageMakerInferenceBase`` (``sagemaker_base.py``, 104 LoC)
=============================================================

Abstract base for all SageMaker invocations:

.. code-block:: python

   def invoke_sagemaker_endpoint(self, payload: dict) -> dict:
       client = boto3.client("sagemaker-runtime",
                             region_name=config.micros_aws_region)
       response = client.invoke_endpoint(
           EndpointName=self.endpoint_name,
           ContentType="application/json",
           Body=json.dumps(payload)
       )
       return json.loads(response["Body"].read())

**Role assumption**: on credential expiry (boto3 ``ClientError`` with code
``"ExpiredTokenException"``), automatically calls:

.. code-block:: python

   sts = boto3.client("sts")
   assumed = sts.assume_role(
       RoleArn="arn:aws:iam::540824312222:role/SageMakerExecutionRole",
       RoleSessionName="rai-api-sagemaker-session"
   )
   # Refresh boto3 credentials from assumed role

Timeout: ``config.sagemaker_inference_timeout`` (default 30s).

``ImageModerationSageMaker`` (main class)
==========================================

Orchestrates parallel V0 + V1 inference via gevent:

.. code-block:: python

   def _run_parallel_inference(self, image_bytes: bytes) -> InferenceResult:
       pool = gevent.Pool(size=config.inference_pool_size)  # default 2

       greenlet_v0 = pool.spawn(self._run_v0, image_bytes)
       greenlet_v1 = pool.spawn(self._run_v1, image_bytes)

       gevent.wait([greenlet_v0, greenlet_v1],
                   timeout=config.greenlet_join_timeout)

       v0_result = greenlet_v0.value if not greenlet_v0.failed else None
       v1_result = greenlet_v1.value if not greenlet_v1.failed else None
       return self._merge_results(v0_result, v1_result)

Pool fallback: if ``pool.full()``, only V0 runs (V1 skipped).

Result merging logic:

.. code-block:: python

   def _merge_results(v0, v1) -> ImageModerationResult:
       # Priority: V1 policy violation > V0 human > V0 top_category > NONE
       if v1 and v1.has_policy_violation():
           category = v1.top_violated_policy()
           score = v1.max_score
       elif v0 and v0.human_score >= IMAGE_MODERATION_V0_THRESHOLD:
           category = ImageHarmCategory.HUMAN
           score = v0.human_score
       elif v0 and v0.max_score >= IMAGE_MODERATION_V0_THRESHOLD:
           category = v0.top_category
           score = v0.max_score
       else:
           category = ImageHarmCategory.NONE
           score = 0.0

       return ImageModerationResult(category=category, violation_score=score)

``ImageModerationV1Client`` (ShieldGemma2)
============================================

* Endpoint: ``config.sm_endpoint_image_moderation_v1``
  (``"image-moderation-v1-model"`` default)
* Input payload: ``{"image": base64_str, "policies": [list_of_policy_strings]}``
* Output: ``{"policy": "harm_category_name", "prediction": {"category": score}}``
  where policy scores map to ``ImageHarmCategory`` values
* Threshold: ``config.image_moderation_v1_threshold`` (default 0.5)

``get_max_score_from_output()`` (V0):

Finds max score across all detection classes from V0 response list:

.. code-block:: python

   def get_max_score_from_output(output: List[dict]) -> Tuple[str, float]:
       # output = [{"class": "human", "score": 0.95}, ...]
       top = max(output, key=lambda x: x["score"])
       return top["class"], top["score"]
