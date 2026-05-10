.. _mod-dataset-infrastructure:

=========================
Dataset Infrastructure
=========================

:Files: ``notebooks/data/dataset.py``, ``notebooks/data/dataset_processing.py``, ``notebooks/data/dataset_sampling.py``, ``notebooks/data/nvidia_aegis_2.0_data.py``
:Importance: **Training data pipeline for all RAI models**

Overview
=========

The dataset infrastructure provides a validated, schema-enforced pipeline for
ingesting multi-source training data into a unified format for RAI model training
and evaluation.

Schema (``dataset.py`` — ``RAI_Dataset``)
==========================================

Built on **Pandera** for DataFrame schema validation. 7 columns:

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Column
     - Type
     - Required
     - Description
   * - ``source``
     - ``str``
     - Yes
     - Dataset origin identifier (e.g. ``"aup_violation"``, ``"openai_moderation"``)
   * - ``content``
     - ``str``
     - Yes (unique)
     - The text to moderate (uniqueness constraint — no duplicates)
   * - ``label``
     - ``int``
     - No (nullable)
     - Ground truth: 0=safe, 1=AUP violation
   * - ``label_categories``
     - ``List[str]``
     - No (nullable)
     - Specific harm categories detected; must be valid ``HarmCategory`` slugs
   * - ``labeling_metadata``
     - ``Dict``
     - No
     - Metadata about labeling process (labeler IDs, timestamps, etc.)
   * - ``original_label``
     - ``int``
     - No
     - Original label from source dataset (before RAI relabeling)
   * - ``original_categories``
     - ``List[str]``
     - No
     - Original category labels from source dataset
   * - ``metadata``
     - ``Dict``
     - No
     - Additional arbitrary metadata

Storage paths (Databricks DBFS):

.. code-block:: text

   /Workspace/Teams/responsible-ai/data/
   ├── raw/                          # unprocessed source data
   └── schema_enforced/
       ├── offline/
       │   ├── labeled/              # labeled for training/eval
       │   └── unlabeled/            # unlabeled (for future annotation)
       └── online/
           ├── labeled/              # production feedback, labeled
           └── unlabeled/            # production feedback, unlabeled

Data sources (``dataset_processing.py``)
==========================================

9 sources ingested into unified schema:

.. list-table::
   :header-rows: 1
   :widths: 30 12 58

   * - Source
     - Approx. size
     - Notes
   * - **AUP Violation Dataset**
     - 238 samples
     - Manually labeled; Atlassian AUP policy violations
   * - **OpenAI Moderation**
     - 1,665 samples
     - OpenAI's public moderation benchmark dataset; unlabeled
   * - **Anthropic hh-rlhf**
     - 7,754 samples
     - Human feedback dataset; split into queries and AI outputs
   * - **Jailbreak Prompts**
     - ~273 (sampled)
     - Labeled harmful prompts; 40% stratified sample by source
   * - **Beavertails Dataset**
     - varies (sampled)
     - Anthropic dataset of harmful Q&A pairs; 20% stratified sample
   * - **Production Feedback (online)**
     - 23 samples
     - Real production moderation feedback; labeled
   * - **ROVO People Dataset**
     - 33 samples
     - Rovo-specific test cases
   * - **NVIDIA Aegis 2.0**
     - varies
     - NVIDIA safety dataset with detailed category labels
   * - **NVIDIA Topic Control**
     - varies
     - Domain-restricted queries (insurance, health, education, legal, banking, taxes)

NVIDIA Aegis 2.0 (``nvidia_aegis_2.0_data.py``):

* Loads from HuggingFace: ``nvidia/Aegis-AI-Content-Safety-Dataset-2.0``
* Category mapping: NVIDIA labels → RAI ``HarmCategory`` slugs
* Filters by confidence threshold before including samples

Sampling strategy (``dataset_sampling.py``)
=============================================

To prevent class imbalance and control dataset size:

.. code-block:: python

   # Jailbreak: 40% stratified sample by source field
   jailbreak_sample = stratified_sample(jailbreak_df, by="source", frac=0.4)
   # → ~273 samples

   # Beavertails: 20% stratified sample by original label
   beavertails_sample = stratified_sample(beavertails_df, by="original_label", frac=0.2)

   # Other sources: used as-is

Policy category definitions (``data/policy_category_defns.json``)
===================================================================

JSON file mapping category slugs to human-readable descriptions and examples.
Used in: LLM judge prompts, model evaluation templates, AUP policy documentation.

Structure:

.. code-block:: json

   {
     "violence_harassment": {
       "name": "Violence/Harassment",
       "description": "...",
       "examples": ["...", "..."]
     },
     ...
   }
