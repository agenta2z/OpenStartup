.. _mod-msp-deployment:

==================
MSP Model Deployment
==================

:Files: ``msp_deploy/register_compliant_model.py``, ``msp_deploy/register_compliant_rai_model_v2_2.py``, ``msp_deploy/register_compliant_rai_model_v2_3.py``, ``msp_deploy/create_compliant_rai_model.json``, ``msp_deploy/create_compliant_rai_model_v24.json``
:Importance: **Bridge between research and production**

Overview
=========

MSP (Model Service Platform, also called "Tarot") is Atlassian's internal
platform for registering, versioning, and serving ML models. The ``msp_deploy``
scripts ship trained models from Databricks to MSP, making them available
to ``responsible-ai-api`` via the ``/v1/msp/`` endpoint prefix.

Model registration scripts
===========================

``register_compliant_model.py`` — Image moderation V0 (DEIM/D-FINE):

.. code-block:: python

   model_dir = "/dbfs/responsible_ai/models/sagemaker_packages/deim_dfine_large"
   model_version_tag = "rai-image-moderation-v0-deim-dfine-large"

   # Packages model artifacts from Databricks DBFS
   # Registers in MSP with:
   #   - model group: "responsible-ai"
   #   - instance type: ml.g6e.2xlarge (GPU)
   #   - environment: prod
   #   - compliance: checked (GDPR, data residency)

``register_compliant_rai_model_v2_2.py`` — LLaMA V2.2 fine-tune:

* Model: RAI fine-tuned LLaMA model V2.2
* Endpoint path after registration: ``/v1/msp/rai-ft-content-filter-v2-2``

``register_compliant_rai_model_v2_3.py`` — LLaMA V2.3 fine-tune:

* Model: RAI fine-tuned LLaMA model V2.3
* Endpoint path: ``/v1/msp/rai-ft-content-filter-v2-3``
* Current production default

Databricks job definitions (JSON)
===================================

``create_compliant_rai_model.json`` — Image moderation V0:

.. code-block:: json

   {
     "job_name": "Register RAI image moderation model with MSP-SDK",
     "tasks": [{
       "task_name": "register_rai_image_moderation_v0_model",
       "notebook_path": "msp_deploy/register_compliant_model.py",
       "parameters": {
         "model_dir": "/dbfs/responsible_ai/models/sagemaker_packages/deim_dfine_large",
         "model_version_tag_prefix": "rai-image-moderation-v0-deim-dfine-large"
       },
       "compute": {
         "type": "single_node",
         "spark_version": "14.3.x-cpu-ml-scala2.12",
         "driver_node_type": "r5.4xlarge"
       }
     }],
     "permissions": [{
       "permission_level": "CAN_MANAGE_RUN",
       "users": ["mturner@atlassian.com", "bjoyce@atlassian.com",
                 "jleventis@atlassian.com", "aabbi@atlassian.com"]
     }],
     "tags": {
       "environment": "prod",
       "service_name": "ap-db-interactive-responsible-ai-modeling",
       "resource_owner": "aabbi",
       "business_unit": "Engineering-AI"
     }
   }

``create_compliant_rai_model_v24.json`` — LLaMA V2.4:

* Same structure; different parameters:
* ``model_dir``: ``/dbfs/tmp/rai_finetuned_model/v24/``
* ``model_version_tag_prefix``: ``rai-v2-4-llama3-1-8b``

Model versioning in production
================================

Current model version matrix (from ``responsible-ai-api`` config):

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Model
     - MSP ID
     - Used for
   * - LLaMA RAI FT V2.3.3
     - ``rai-ft-content-filter-v2-3-3``
     - Prompt moderation (default primary)
   * - LLaMA RAI FT V2.4
     - ``rai-v2-4-llama3-1-8b``
     - Prompt moderation (Teamserve; feature-flagged)
   * - GPT-OSS Safeguard 20B
     - ``gpt-oss-safeguard-20b``
     - Prompt moderation alt + agent moderation
   * - Image Moderation V0
     - ``rai-image-moderation-v0-deim-dfine-large``
     - Image moderation (SageMaker)
   * - Image Moderation V1
     - ``rai-image-moderationv1-shieldgemma2-v1-4``
     - Image moderation (ShieldGemma2, feature-flagged)

Tokenizers directory (``tokenizers/``)
=========================================

The ``responsible-ai-api`` repo contains a ``tokenizers/`` directory with:

* ``gpt_oss_safeguard_20b/`` — GPT-OSS 20B tokenizer config
* ``rai_ft_v2_1/`` — RAI FT V2.1 tokenizer
* ``rai_ft_v2_2/`` — RAI FT V2.2 tokenizer
* ``gpt-oss-safeguard-20b/`` — alternate GPT-OSS tokenizer path

These are HuggingFace tokenizer files (``tokenizer.json``, ``tokenizer_config.json``,
``special_tokens_map.json``) bundled with the service for offline tokenization.

Model onboarding (``model_onboarding/``)
==========================================

The ``model_onboarding/`` directory in ``responsible-ai-api`` contains:

* ``service/`` — Service-side onboarding documentation
* ``test.json`` — Test configuration for new model validation

Used when onboarding a new model variant: validates request/response format,
registers model with the service, and runs regression tests before enabling
via feature flags.
