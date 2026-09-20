.. _mod-image-moderation-v1-experiment:

============================
Image Moderation V1 Experiment
============================

:Path: ``responsible-ai/experiments/image_moderation_v1/``
:Status: **Research complete; V1 deployed to production via SageMaker**

Overview
=========

The image moderation V1 experiment evaluated **ShieldGemma2** (Google's multimodal
safety model) as the next-generation image moderation backend, replacing V0's
DEIM/D-FINE object detection approach. The experiment established that ShieldGemma2
provides superior policy-level classification vs V0's class-level detection.

ShieldGemma2 model
===================

* HuggingFace model: ``google/shieldgemma-2-4b-it``
* Architecture: Gemma2 4B fine-tuned for safety classification
* Input: image + text policy descriptions
* Output: per-policy violation probability scores
* Task: multi-label classification across 11 external harm policies

The 11 evaluated policies:

.. code-block:: text

   1. Hate/Discrimination
   2. Misinformation
   3. Jailbreak/Prompt Injection
   4. Personally Identifiable Information (PII)
   5. Politics
   6. Impersonation
   7. Specialist Advice
   8. High-risk Decisions
   9. Sexual Content
   10. Violence/Harassment
   11. (+ HUMAN detection from V0)

LLaVAGuard dataset
====================

* Training/test split: ``train_llavaguard.csv``, ``test_llavaguard.csv``
* Analyzed in ``analyze_llavaguard_data.py``
* Category distribution analysis stored in:
  ``data/train_llavaguard_category_counts.txt``,
  ``data/test_llavaguard_analysis.txt``

Inference implementations
==========================

Three implementations for different deployment contexts:

**1. Local inference** (``src/inference_shieldgemma2.py``):

.. code-block:: python

   processor = AutoProcessor.from_pretrained("google/shieldgemma-2-4b-it")
   model = ShieldGemma2ForImageClassification.from_pretrained(...)

   # Per-image inference:
   inputs = processor(images=image, text=policy_description, return_tensors="pt")
   outputs = model(**inputs)
   scores = torch.sigmoid(outputs.logits)

Used for development and notebook experimentation.

**2. SageMaker single-instance** (``src/inference_shieldgemma2_sagemaker.py``):

* Base64 encodes image
* POST to SageMaker endpoint: ``{"image": base64_str, "policies": [...]}``.
* Instance type: ``ml.g6e.2xlarge`` (NVIDIA L40S GPU)
* Container: PyTorch 2.6.0 + Python 3.12

**3. SageMaker multi-process** (``src/inference_shieldgemma2_sagemaker_mp.py``):

.. code-block:: python

   with ThreadPoolExecutor(max_workers=8) as executor:
       futures = [executor.submit(infer_single, image) for image in images]
       results = [f.result() for f in futures]

8-worker thread pool for batch evaluation throughput. Used during dataset
evaluation runs.

Evaluation pipeline (``src/eval_image_moderations_v1.py``)
===========================================================

Full evaluation against ground-truth dataset:

1. Load ground truth JSON files (list of ``{image_path, gt_is_safe, gt_categories}``)
2. Run ShieldGemma2 inference on each image
3. Compute metrics:
   * Binary: accuracy, F1 (vs is_safe threshold)
   * Multi-class: per-category precision/recall
   * AUC: ROC-AUC, PR-AUC (via sklearn)
4. Output: JSON results + formatted metrics report

Result format per image:

.. code-block:: json

   {
     "image_path": "...",
     "image_name": "...",
     "image_width": 1024,
     "image_height": 768,
     "inference_time_seconds": 0.34,
     "status": "safe | unsafe",
     "predictions": {"hate_discrimination": 0.02, "sexual_content": 0.89, ...},
     "timestamp": "2025-01-15T10:23:45Z"
   }

Analysis (``src/eval_analysis.py``)
=====================================

Post-evaluation analysis pipeline:

* **Binary analysis**: Safe vs Unsafe (``y_true = ~gt_is_safe``)
* **Threshold optimization**: ``argmax(F1_scores)`` over ``linspace(0, 1, 501)`` thresholds
* **Plots saved as PNG**:
  * ROC curve (FPR vs TPR)
  * Precision-Recall curve
  * F1 vs threshold curve
* **Optimal threshold computation**: finds threshold maximizing F1 on test set

CSV output per image:

.. code-block:: text

   filename, gt_is_safe, gt_categories, model_is_safe,
   unsafe_policies_count, most_violated_policy, max_violation_prob,
   policy_hate_discrimination_prob, policy_sexual_content_prob, ...

Latency benchmarks (``notebooks/evaluation_image_moderation_v1_LATENCY.py``)
===============================================================================

Databricks notebook that measures and analyzes inference latency:

* Tracks ``processing_time_seconds`` (end-to-end) and ``inference_time_seconds`` (model only)
* Correlation analysis: latency vs image pixel count via ``LinearRegression``
* Percentile computation: p50, p95, p99 across test set
* Key finding: latency scales approximately linearly with image pixel count

Results: on ``ml.g6e.2xlarge``:

* p50 inference time: ~200ms
* p95 inference time: ~400ms
* p99 inference time: ~600ms

Streamlit demo app (``streamlit-app/app.py``)
===============================================

Simple demo UI for internal stakeholder evaluation:

* Text input field (max 500 chars) for optional context
* Image upload (PNG/JPG/JPEG/WebP)
* Calls moderation backend and displays result
* Styled with CSS classes ``.big-header``, ``.result-box``, ``.subtext``
* Deployed via ``app.yaml`` (Streamlit Cloud or Atlassian internal)
