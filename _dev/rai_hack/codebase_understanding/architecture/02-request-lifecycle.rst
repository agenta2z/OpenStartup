.. _rai-request-lifecycle:

========================
Request Lifecycle Detail
========================

This page traces the full call stack for each of the 4 moderation endpoints,
with exact file paths and key class/method names.

Prompt Moderation — full call stack
=====================================

.. code-block:: text

   POST /v1/moderation/prompt/
     │
     ├─ [before_request] handle_etag() → check_etag(request)
     │     prompt_etag.py: parse body → ModeratePromptRequest
     │     generate_comparison_etag(request_input, model_version) → SHA-256 truncated
     │     matches_any_possible_etag() → If match: return Response(304)
     │
     ├─ [before_request] @required_headers(...)
     │     validate_header.py: enforce cloud_id + use_case_id + one-of auth
     │     → 400 if missing
     │
     ├─ @validate() → flask-pydantic
     │     ModeratePromptRequest(prompt: str[≥1], debug: Optional[DebugOptions])
     │     strict=True: no extra fields; → 422 on failure
     │
     ├─ index(body: ModeratePromptRequest)
     │     prompt_moderation_controller.py
     │     ModerationRequestContext.from_incoming_http_request()
     │       moderation_request_context.py: cloud_id, user_id, use_case_id, issuer
     │     get_prompt_moderation_service() → app_context.py singleton
     │     _process_prompt_moderation(body, service, context)
     │
     ├─ _process_prompt_moderation()
     │     is_debug_verbose(debug) → bool
     │     apply_debug_overrides(debug) → feature_service.set_request_overrides()
     │     [verbose] pre-call: resolve model_id, model_version, gateway_endpoint
     │
     ├─ PromptModerationService.predict_harm_category_in_prompt()
     │     prompt_moderation.py
     │     RAILlamaModels.get_model(feature_service) → select inference model
     │       ├─ is_gpt_oss_safeguard_enabled() → GPTOSSModelInTeamserve
     │       ├─ is_prompt_moderation_teamserve_v2_4_primary_enabled() → LlamaModelInTeamserve V2.4
     │       ├─ is_rai_ft_teamserve_shadowing_enabled() → wrap ShadowShim
     │       └─ default → LlamaModel (MSP V2.3.3)
     │     HFPretrainedModelTokenizer.get_tokenized_input()
     │       → TokenizedInput(token_ids, overflow_ratio, consumed_tokens)
     │     filter_prompt_template.render(prompt) → formatted string
     │     model.run_inference(formatted_prompt, endpoint_params)
     │
     ├─ [MSP path] RAIFTEndpointV2_3_3.send()
     │     ml_platform/input_moderation_client.py: SyncMspWithRAIFT
     │     AI Gateway sync client POST /v1/msp/rai-ft-content-filter-v2-3-3
     │     Request: {inputs: str, parameters: {do_sample, return_full_text, details, top_n_tokens}}
     │     Response: ResponsibleAIFineTunedModelOutput
     │
     ├─ [Teamserve gRPC path] GrpcEndpoint.invoke()
     │     triton_grpc_client.py: circuit breaker (fail_max=30)
     │     InferInput tensors: input_ids, input_lengths, request_output_len,
     │       return_generation_logits, return_log_probs
     │     Response: output_ids numpy array + output_log_probs
     │
     ├─ parse_model_response() → model_text_response_parse.py
     │     Stage 1: strict json.loads()
     │     Stage 2: normalize quotes → json.loads()
     │     Stage 3: regex patterns ({"category":…,"toBeFiltered":…})
     │     Stage 4: key-value fallback parser
     │     Returns: ModerationResult{category: str, toBeFiltered: bool}
     │
     ├─ _get_score_from_details() (LLaMA)
     │     rai_llama.py: extract log-probs from 10-bin histogram
     │     violation_score = P(toBeFiltered=True) from token log-probs
     │
     ├─ confidence_thresholds.get_threshold(category, model_version)
     │     confidence_thresholds.py: @time_cache(60s) lookup
     │     If score >= threshold → DISALLOWED; else ALLOWED
     │
     ├─ ModeratePromptResponse(status, harm_category, violation_score[excluded],
     │     model_evaluation_version[excluded], prompt_evaluation_version[excluded])
     │
     ├─ [after_this_request] set_response_headers()
     │     response_headers.py:
     │     X-RAI-Model-Evaluation-Version, X-RAI-Prompt-Evaluation-Version,
     │     X-RAI-Prompt-Violation-Score, ETag: W/"hash:category_hash"
     │
     └─ [async] send_outcome_metrics() + analytics_client.send_content_evaluated_event()
           metrics_handler.py: Prometheus counter
           rai_analytics_client.py: gevent Pool(10) spawn

Output Moderation — call stack
================================

.. code-block:: text

   POST /v1/moderation/output/   (NDJSON streaming body)
     │
     ├─ output_moderation_controller.py
     │     reads request.stream line by line
     │     parse each line: ModerateOutputRequest(stream_id, current_chunk, chunk_index)
     │
     ├─ stream_processor.process_output_stream()
     │     Per line:
     │     1. size_check: chunk < 100KB, line < 1MB
     │     2. accumulate: stream_content[stream_id] += current_chunk
     │     3. size_check: accumulated < 10MB
     │     4. url_checker.extract_external_urls(accumulated)
     │         → regex: \b(https?://|www\.)[^\s<>"']{1,2048}
     │         → filter internal domains (internal_domains.txt)
     │         → ExternalUrlsResult{external_urls, external_domains}
     │     5. diff new URLs vs previous
     │     6. PromptModerationService.predict_harm_category_in_prompt(accumulated)
     │         (same pipeline as above, minus ETag)
     │     7. If DISALLOWED → yield final chunk + break
     │     yield: ModerateOutputResponse(status, stream_id, chunk_index,
     │             harm_category, content, external_urls)
     │
     └─ [per chunk] send_output_metrics() + analytics per stream_id

Agent Moderation — call stack
================================

.. code-block:: text

   POST /v1/moderation/agent/
     │
     ├─ agent_moderation_controller.py
     │     ModerateAgentRequest(name, description, prompt, conversation_starters,
     │                          follow_up_prompt, debug)
     │     ModerationRequestContext.from_incoming_http_request()
     │     get_agent_moderation_service()
     │
     ├─ AgentModerationService.predict_harm_category_for_agent()
     │     agent_moderation.py
     │     _get_moderation_config(cloud_id) → AgentModerationVersionConfig
     │       checks feature gates per cloud_id:
     │       is_agent_moderation_v2_3_1_enabled() → V2.3.1 config
     │       is_agent_moderation_v3_enabled() → V3 config
     │       default → V2.3 config (gpt-4o or gpt-4-turbo-mini)
     │     Build prompt: name + description + prompt + starters + follow_up
     │     system_message: "You are a content moderation expert..."
     │     AI Gateway Raw client POST (direct, not MSP/Teamserve)
     │     Headers: USE_CASE_ID, CLOUD_ID, USER_ID, USER_CONTEXT
     │     parse_response: JSON → {harm_category, toBeFiltered, violation_score}
     │
     ├─ AgentHarmCategory resolution (15 categories)
     │     _missing_(): substring + case-insensitive matching
     │     deprecated alias map applied
     │
     └─ ModerateAgentResponse(status, harm_category, trace?)

Image Moderation — call stack
================================

.. code-block:: text

   POST /v1/moderation/image/
     │
     ├─ image_moderation_controller.py
     │     ModerateImageRequest(image_data: str, type: base64, format?,
     │                          file_id?, container_id?, user_id?, region?, platform?)
     │     @model_validator: image_data non-empty check
     │     base64 decode → image_bytes
     │
     ├─ ImageModerationService.moderate_image()
     │     image_moderation.py
     │     Parallel gevent spawns:
     │
     │     ├─ [greenlet A] ImageModerationSageMaker.run_parallel_inference()
     │     │     image_moderation_sagemaker.py
     │     │     gevent Pool:
     │     │     ├─ V0: boto3 invoke_endpoint(image-moderation-v0)
     │     │     │     → {class, score} dict; find max score
     │     │     └─ V1: ImageModerationV1Client.run_inference()
     │     │           → {policy: str, prediction: {category: score}}
     │     │           ShieldGemma2: 12 harm categories, threshold=0.5
     │     │     Merge: V1 violations override V0 results
     │     │
     │     └─ [greenlet B] AntiAbuseClient.scan_content() (best-effort)
     │           antiabuse_client.py: POST to abuse-filescanner-*
     │           ASAP JWT Bearer token auth
     │           {region, platform, fileID, containerID, userID, media}
     │           → AntiAbuseResponse{classification, confidence}
     │           circuit breaker fail_max=5, reset=60s
     │
     ├─ Merge all results:
     │     V1 policy → V0 human class → V0 top category → anti-abuse
     │     final_score = max(V0_score, V1_score)
     │
     ├─ feature_service.is_standardized_image_moderation_response_enabled()
     │     True → ModerateImageResponseV1(status, harm_category,
     │             abhorrent_material: bool, actions: {deletion: bool}, comment?)
     │     False → ModerateImageResponse(status, harm_category)
     │
     └─ send_image_metrics() + analytics_client.send_image_evaluated_event()
