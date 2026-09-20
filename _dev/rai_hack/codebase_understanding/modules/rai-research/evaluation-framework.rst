.. _mod-evaluation-framework:

=========================
Model Evaluation Framework
=========================

:Files: ``notebooks/evaluation/model_evaluation.py``, ``notebooks/evaluate_utils.py``, ``notebooks/evaluation/README.md``
:Importance: **Core quality gate for model releases**

Overview
=========

The offline evaluation framework measures model performance on labeled datasets
using standard binary classification metrics. Results are logged to MLflow and
written to CSV for analysis. This runs before every model version release to
validate performance thresholds.

Metrics computed (``model_evaluation.py``)
==========================================

All metrics are standard binary classification metrics using ``sklearn``:

.. code-block:: python

   compute_accuracy()    → (TP+TN) / (TP+TN+FP+FN)
   compute_precision()   → TP / (TP+FP)
   compute_recall()      → TP / (TP+FN)          # = True Positive Rate
   compute_f1()          → 2 * (P*R) / (P+R)
   compute_fpr()         → FP / (FP+TN)          # False Positive Rate = wrongly blocked
   compute_fnr()         → FN / (FN+TP)          # False Negative Rate = missed violations
   compute_confusion_matrix() → sklearn.metrics.confusion_matrix()

The most important SLOs:

* **FPR** (False Positive Rate) — critical for user experience. High FPR means
  legitimate content is being blocked. Target: < 5% in most categories.
* **FNR** (False Negative Rate) — critical for safety. High FNR means harmful
  content passes through. Target: varies by category (lower for JAILBREAK, PII).

Evaluation runner (``evaluate_utils.py``)
==========================================

``evaluate_moderation_model(model, dataset_df, model_name, mlflow_experiment)``

Full evaluation pipeline:

1. Loads labeled DataFrame (``content`` column for input, ``label`` column for ground truth)
2. Calls ``model.run_moderation_batch(contents)`` → predictions list
3. Computes all metrics
4. Logs to MLflow:

   * Metrics: accuracy, precision, recall, F1, FPR, FNR
   * Artifacts: confusion_matrix.png, false_positives.csv, false_negatives.csv, all_reports.csv
   * Parameters: model_name, dataset_source, dataset_size, threshold

5. Writes results CSV: ``{content, label, model_response, model_category, model_reason, model_score}``

``run_moderation_get_categories(model, contents)``

Batch inference with category extraction:

* Returns ``(predictions: List[str], categories: List[str], reasons: List[str], scores: List[float])``
* Handles model errors gracefully (returns UNKNOWN on exception)
* Supports ``write_batch_size`` parameter for memory-efficient processing

Result file structure
======================

Stored in ``notebooks/evaluation/results/``:

.. code-block:: text

   results/
   ├── all_reports.csv                            # summary across all model versions
   ├── cat_acc_report.csv                         # per-category accuracy breakdown
   ├── anthropic.claude-3-5-sonnet-20240620/
   │   ├── confusion_matrix.png
   │   ├── false_negatives.csv
   │   └── false_positives.csv
   ├── anthropic.claude-3-haiku-20240307/
   │   └── ...
   ├── anthropic.claude-3-sonnet-20240229/
   │   └── ...
   └── assistance-service-plugin-gpt3/
       └── ...

These results show that **multiple LLM models** have been evaluated as potential
moderation backends, with Claude 3.5 Sonnet being the strongest performer.

Databricks integration (``notebooks/databricks_utils.py``)
============================================================

All evaluation notebooks run on **Databricks**:

* ``get_auth_databricks_widgets()`` — retrieves ASAP credentials from Databricks
  secret scope ``"mls-ai_modeling-experimental"`` / key ``"MLS_USER_MANAGE_SHARED_RAI_ASAP_PRIVATE_KEY"``
* ``set_hf_token()`` — loads HuggingFace API token for model downloads
* Notebooks use ``dbutils.widgets`` for parameterization (model_name, threshold, etc.)
* Data stored on DBFS: ``/dbfs/responsible_ai/models/`` and ``/Workspace/Teams/responsible-ai/data/``

Auth utilities (``notebooks/auth_utils.py``)
=============================================

``get_auth(issuer="micros/ai-policy-filtering", audience="ai-gateway") -> JWTAuth``:

* Creates ASAP JWT using ``atlassian_jwt_auth`` library
* Loads private key from environment or ``.env`` file
* Returns ``requests``-compatible auth object for API calls from notebooks

Used when evaluation notebooks need to call the production ``responsible-ai-api``
endpoint directly to evaluate live model behaviour.
