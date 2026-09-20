.. _rai-module-catalog:

==============
Module Catalog
==============

All modules in both repositories, with LoC and one-line purpose.

responsible-ai-api modules
===========================

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - Module / File
     - LoC
     - Purpose
   * - ``src/app.py``
     - 163
     - Flask app factory; registers blueprints; global error handlers; Swagger UI
   * - ``src/config.py``
     - 182
     - Config singleton; env var parsing; ASAP signer init; endpoint URLs; Statsig env
   * - ``src/feature_service.py``
     - 256
     - Statsig wrapper; ~30 feature gates; per-request override support
   * - ``src/micros_logging.py``
     - 198
     - Structured logging with MDC context (request_id, cloud_id, use_case_id)
   * - ``src/exception.py``
     - 105
     - ``APIException`` hierarchy; ``make_api_error_response()`` helper
   * - ``src/gunicorn.conf.py``
     - 31
     - Gunicorn config: gevent worker class, 600s timeout, worker count
   * - ``src/gunicorn_logger.py``
     - 102
     - Custom gunicorn access/error logger with structured JSON output
   * - ``src/cache/time_cache.py``
     - 26
     - ``@time_cache(max_age)`` — LRU cache with time-based TTL invalidation
   * - ``src/dynamic_config/client.py``
     - 19
     - Dynamic config client (Confluence-backed remote configuration)
   * - ``src/statsig_flags/local_overrides.py``
     - 23
     - Statsig local override file support for dev/test environments
   * - ``src/api/api_blueprint.py``
     - 7
     - Root Flask blueprint; registers ``/v1/`` and ``/healthcheck``
   * - ``src/api/healthcheck.py``
     - 258
     - ``/healthcheck``, ``/ping``, ``/status`` — Micros health protocol
   * - ``src/api/v1/api_v1_blueprint.py``
     - ~20
     - ``/v1/`` blueprint; registers moderation + admin sub-blueprints
   * - ``src/api/v1/admin/admin_blueprint.py``
     - ~50
     - Internal admin endpoints (model info, config inspection)
   * - ``src/api/v1/moderation/moderation_blueprint.py``
     - ~30
     - Parent blueprint; registers 4 moderation sub-blueprints; logging middleware
   * - ``src/api/v1/moderation/prompt_moderation_controller.py``
     - 314
     - POST /v1/moderation/prompt/ — ETag, feature flags, service call, response headers
   * - ``src/api/v1/moderation/output_moderation_controller.py``
     - ~120
     - POST /v1/moderation/output/ — NDJSON streaming; delegates to stream_processor
   * - ``src/api/v1/moderation/agent_moderation_controller.py``
     - ~100
     - POST /v1/moderation/agent/ — agent config moderation; debug trace
   * - ``src/api/v1/moderation/image_moderation_controller.py``
     - ~100
     - POST /v1/moderation/image/ — base64 image; V0+V1 parallel; anti-abuse
   * - ``src/api/v1/moderation/app_context.py``
     - ~200
     - Lazy service singleton factory; AI Gateway client config; retry setup
   * - ``src/api/v1/moderation/debug_trace_builder.py``
     - ~70
     - ``build_trace()`` — DebugTrace from runtime context; error chain; overrides
   * - ``src/api/v1/moderation/etag/prompt_etag.py``
     - ~120
     - ETag check/generate for prompt caching; SHA-256 hash of (prompt+version+category)
   * - ``src/api/v1/moderation/schema/moderate_prompt.py``
     - ~45
     - ``ModeratePromptRequest``, ``ModeratePromptResponse``, ``ModeratePromptDetermination``
   * - ``src/api/v1/moderation/schema/moderate_output.py``
     - ~40
     - ``ModerateOutputRequest``, ``ModerateOutputResponse``, ``ModerateOutputDetermination``
   * - ``src/api/v1/moderation/schema/moderate_agent.py``
     - ~50
     - ``ModerateAgentRequest``, ``ModerateAgentResponse``, ``AgentConversationStarters``
   * - ``src/api/v1/moderation/schema/moderate_image.py``
     - ~60
     - ``ModerateImageRequest``, ``ModerateImageResponse``, ``ModerateImageResponseV1``
   * - ``src/api/v1/moderation/schema/debug.py``
     - ~80
     - ``DebugOptions`` (verbose + feature_overrides), ``DebugTrace`` (all optional fields)
   * - ``src/inference_models/model.py``
     - 281
     - Abstract base: ``ModelTokenizer``, ``ModelEndpoint``, ``InferenceModel``, ``InferenceResult``
   * - ``src/inference_models/rai_llama.py``
     - 689
     - LLaMA endpoints (MSP, Teamserve gRPC); ``LlamaModel``; score histogram; shadowing
   * - ``src/inference_models/rai_gpt_oss.py``
     - 287
     - GPT-OSS 20B via Teamserve HTTP; ``GPTOSSModelInTeamserve``; OpenAI chat format
   * - ``src/inference_models/sagemaker_base.py``
     - 104
     - ``SageMakerInferenceBase``; boto3 invoke_endpoint; role assumption; retry on creds
   * - ``src/inference_models/triton_grpc_client.py``
     - 148
     - ``GrpcEndpoint``; Triton InferInput tensors; circuit breaker fail_max=30
   * - ``src/inference_models/triton_openai_api_client.py``
     - 36
     - ``TritonOpenAIClient``; HTTP chat completions; 6s timeout; circuit breaker
   * - ``src/inference_models/image_moderation_sagemaker.py``
     - 325
     - ``ImageModerationSageMaker`` V0+V1 parallel; ``ImageModerationV1Client`` ShieldGemma2
   * - ``src/inference_models/image_moderation_types.py``
     - 30
     - Image moderation response type definitions
   * - ``src/inference_models/error_handling.py``
     - 237
     - ``InferenceErrorContext``; ``@inference_error_handler``; structured error capture
   * - ``src/inference_models/errors.py``
     - 18
     - Custom exception types for inference errors
   * - ``src/inference_models/confidence/confidence_thresholds.py``
     - ~80
     - ``PromptHarmConfidenceThreshold``, ``PromptHarmConfidenceThresholds``; 60s TTL cache
   * - ``src/inference_models/model_shadowing/shadower.py``
     - ~100
     - ``ModelShadower``, ``ShadowEvaluator``, ``ShadowShim``; gevent Pool(20)
   * - ``src/service/moderation/prompt/prompt_moderation.py``
     - ~200
     - ``PromptModerationService``; tokenize → template → infer → parse → threshold
   * - ``src/service/moderation/prompt/prompt_harm_category.py``
     - ~80
     - ``PromptHarmCategory`` StrEnum (14 categories + NONE + UNKNOWN); get_category_hash
   * - ``src/service/moderation/prompt/filter_prompt_template.py``
     - ~60
     - Jinja2 template loader; multi-version (V2.3, V2.3.2, V2.4) template management
   * - ``src/service/moderation/prompt/constants.py``
     - ~30
     - ``ModelVersion`` enum (V2_3, V2_3_2, V2_3_3, V2_4); ignored categories per version
   * - ``src/service/moderation/output/output_moderation.py``
     - ~100
     - ``OutputModerationService``; chunk accumulation; URL detection; ML moderation
   * - ``src/service/moderation/output/stream_processor.py``
     - ~150
     - NDJSON stream processing; size limits; early termination; per-chunk metrics
   * - ``src/service/moderation/output/url_checker.py``
     - ~60
     - ``extract_external_urls()``; regex + internal domain filter; dedup by domain
   * - ``src/service/moderation/agent/agent_moderation.py``
     - ~200
     - ``AgentModerationService``; per-cloud config; LLM-as-judge via AI Gateway Raw
   * - ``src/service/moderation/agent/agent_harm_category.py``
     - ~60
     - ``AgentHarmCategory`` StrEnum (15 categories); deprecated alias mapping
   * - ``src/service/moderation/image/image_moderation.py``
     - ~150
     - ``ImageModerationService``; parallel V0+V1+anti-abuse; result merging
   * - ``src/service/moderation/image/image_harm_category.py``
     - ~40
     - ``ImageHarmCategory`` StrEnum (12 categories); ``MODERATION_THRESHOLD=0.4``
   * - ``src/service/moderation/types.py``
     - ~40
     - Shared types: ``ModerationResult``, ``PredictionResult``, ``OutputModerationResult``
   * - ``src/service/moderation/moderation_request_context.py``
     - ~80
     - ``ModerationRequestContext``; header parsing; user ID resolution
   * - ``src/service/moderation/model_text_response_parse.py``
     - ~120
     - Multi-stage JSON parser for LLM responses; strict → normalized → regex → kv fallback
   * - ``src/service/moderation/prompt_text_analysis.py``
     - ~40
     - Text analysis utilities (non-alphanumeric ratio, etc.)
   * - ``src/service/moderation/response_headers.py``
     - ~50
     - Sets X-RAI-* response headers + ETag on Flask response object
   * - ``src/service/moderation/validate_header.py``
     - ~50
     - ``@required_headers`` decorator; ``one_of_headers`` validator
   * - ``src/metrics/metrics_handler.py``
     - 305
     - ``Metric`` enum; ``MetricTag`` enum; ``send_metric()``; ``@measure_latency`` decorator
   * - ``src/metrics/prompt_moderation_metrics.py``
     - 345
     - Tag builders for prompt moderation; token/overflow buckets; ``send_outcome_metrics()``
   * - ``src/metrics/output_moderation_metrics.py``
     - 56
     - Tag builders for output moderation outcomes
   * - ``src/metrics/image_buckets.py``
     - 21
     - ``get_image_size_bucket(width, height)`` — pixel-range buckets for metrics
   * - ``src/gasv3_analytics/rai_analytics_client.py``
     - 178
     - ``RAIAnalyticsClient``; gevent Pool(10); env-aware retries; event dispatch methods
   * - ``src/gasv3_analytics/events/policy_filter/content_evaluated.py``
     - ~40
     - ``ContentEvaluatedEvent`` + ``ContentEvaluatedEventOutcome`` for prompt moderation
   * - ``src/gasv3_analytics/events/output_moderation/output_evaluated.py``
     - ~40
     - ``OutputEvaluatedEvent`` schema
   * - ``src/gasv3_analytics/events/agent_moderation/agent_evaluated.py``
     - ~40
     - ``AgentEvaluatedEvent`` schema
   * - ``src/gasv3_analytics/events/image_moderation/image_evaluated.py``
     - ~40
     - ``ImageEvaluatedEvent`` schema
   * - ``src/antiabuse/antiabuse_client.py``
     - 189
     - ``AntiAbuseClient``; httpx; circuit breaker; ASAP JWT auth; POST /api/moderation/scan
   * - ``src/antiabuse/antiabuse_utils.py``
     - 123
     - Anti-abuse request/response utilities; classification mapping
   * - ``src/antiabuse/models.py``
     - 65
     - ``AntiAbuseRequest``, ``AntiAbuseResponse``, ``AntiAbuseOptionalFields`` Pydantic models
   * - ``src/ml_platform/input_moderation_client.py``
     - 193
     - ``SyncMspWithRAIFT``; MSP request/response models; ``ResponsibleAIFineTunedModelRequest``
   * - ``src/ml_platform/use_cases.py``
     - 7
     - ``UseCases`` enum (PROMPT_MODERATION, OUTPUT_MODERATION, AGENT_MODERATION, IMAGE_MODERATION)
   * - ``src/slauth/user_context.py``
     - 155
     - SLAuth header parsing; ``SlauthUserContextHeaders``; status validation
   * - ``src/tenant_context/tenant_context_client.py``
     - 104
     - ``TenantContextClient``; TCS sidecar HTTP calls; cloud_id → tenant metadata

responsible-ai modules
========================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Module / File
     - Purpose
   * - ``packages/rai/harm_taxonomy/harm_category.py``
     - ``HarmCategory`` Enum (16 categories); slug/friendly_name; from_slug(); _missing_()
   * - ``notebooks/data/dataset.py``
     - ``RAI_Dataset`` Pandera schema (7 columns); validation; read/write helpers
   * - ``notebooks/data/dataset_processing.py``
     - Multi-source ingestion pipeline (9 data sources → schema-enforced DataFrames)
   * - ``notebooks/data/dataset_sampling.py``
     - Stratified sampling (jailbreak 40%, beavertails 20%, others as-is)
   * - ``notebooks/data/dataset_schema_example.py``
     - Example notebook showing schema usage
   * - ``notebooks/data/nvidia_aegis_2.0_data.py``
     - NVIDIA Aegis 2.0 dataset loading + preprocessing
   * - ``notebooks/auth_utils.py``
     - ``get_auth()`` — ASAP JWT creation for notebook API calls
   * - ``notebooks/databricks_utils.py``
     - Databricks secret scope access; HuggingFace token loading
   * - ``notebooks/evaluate_utils.py``
     - ``evaluate_moderation_model()``; MLflow logging; batch eval; CSV result writing
   * - ``notebooks/evaluation/model_evaluation.py``
     - Sklearn metrics: accuracy, precision, recall, F1, FPR, FNR, confusion_matrix
   * - ``notebooks/evaluation/online_evaluation/online_eval_workflow.py``
     - Online eval orchestration pipeline (Databricks-based)
   * - ``notebooks/evaluation/online_evaluation/llm_judge_query_response.py``
     - LLM judge inference for online evaluation (production log sampling)
   * - ``notebooks/evaluation/online_evaluation/eval_utils.py``
     - Online eval helper functions
   * - ``notebooks/evaluation/online_evaluation/rai_analytics.py``
     - Analytics aggregation for online evaluation results
   * - ``notebooks/evaluation/online_evaluation/judge_category_policy_defns.json``
     - Policy definitions used by LLM judge for category evaluation
   * - ``msp_deploy/register_compliant_model.py``
     - MSP model registration (DEIM/D-FINE V0: ``rai-image-moderation-v0-deim-dfine-large``)
   * - ``msp_deploy/register_compliant_rai_model_v2_2.py``
     - MSP registration for RAI FT model V2.2
   * - ``msp_deploy/register_compliant_rai_model_v2_3.py``
     - MSP registration for RAI FT model V2.3
   * - ``msp_deploy/create_compliant_rai_model.json``
     - Databricks job JSON for V0 image model registration (r5.4xlarge driver)
   * - ``msp_deploy/create_compliant_rai_model_v24.json``
     - Databricks job JSON for LLaMA V2.4 model registration
   * - ``experiments/image_moderation_v1/src/eval_image_moderations_v1.py``
     - Evaluation pipeline for ShieldGemma2 (accuracy, F1, ROC-AUC, PR-AUC)
   * - ``experiments/image_moderation_v1/src/inference_shieldgemma2.py``
     - Local ShieldGemma2 inference (HuggingFace AutoProcessor)
   * - ``experiments/image_moderation_v1/src/inference_shieldgemma2_sagemaker.py``
     - SageMaker-based ShieldGemma2 inference (base64 payload)
   * - ``experiments/image_moderation_v1/src/inference_shieldgemma2_sagemaker_mp.py``
     - Multi-threaded parallel SageMaker inference (ThreadPoolExecutor, 8 workers)
   * - ``experiments/image_moderation_v1/src/eval_analysis.py``
     - Binary + multi-class analysis; ROC/PR curves; optimal threshold via argmax(F1)
   * - ``experiments/image_moderation_v1/streamlit-app/app.py``
     - Streamlit demo UI (text input + image upload → moderation result)
   * - ``experiments/PII_Anonymization/PII_Anonymization.py``
     - Presidio + HF transformer PII detection/anonymization (12 entity types)
