.. _mod-llama-model:

====================
LLaMA Inference Model
====================

:File: ``src/inference_models/rai_llama.py`` (689 LoC — largest file in codebase)
:Importance: **P1 — primary text moderation backend**

Overview
=========

``rai_llama.py`` implements all LLaMA-based inference for prompt and output
moderation. It contains three endpoint classes, two model classes, a factory,
and a shadow evaluator. The file is the most complex in the codebase.

Endpoint classes
=================

``RAIFTEndpoint(ModelEndpoint)`` — MSP base endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Base class for RAI Fine-Tuned model endpoints. Calls MSP via AI Gateway sync client.

* ``send(prepared_request: PreparedRequest[str]) -> InferenceResult[ModerationResult]``
* Creates ``RAIFTRequest`` from template-rendered prompt
* Request body: ``{inputs: str, parameters: {do_sample, return_full_text, details, top_n_tokens}}``;
  ``top_n_tokens=10`` (for log-probs histogram)
* Error handling wraps ``AIGatewayResponseException`` with context

``RAIFTEndpointV2_3_3(RAIFTEndpoint)`` — MSP V2.3.3 primary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Endpoint: ``/v1/msp/rai-ft-content-filter-v2-3-3``
* Uses ``SyncMspWithRAIFT`` client (``ml_platform/input_moderation_client.py``)
* Model ID: ``rai-ft-content-filter-v2-3-3``
* Default inference model for prompt moderation

``RAIFTTeamserveEndpoint(RAIFTEndpoint)`` — Teamserve gRPC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Uses ``GrpcEndpoint`` (``triton_grpc_client.py``) with ASAP JWT auth via ``TeamservePlugin``
* Endpoint: ``grpc-teamserve-us-west-2.dev.services.kitt-inf.net``
* Circuit breaker: ``fail_max=30``
* Sends Triton ``InferInput`` tensors:

  .. code-block:: python

     input_ids         → int32 tensor [1, seq_len]
     input_lengths     → int32 tensor [1, 1]
     request_output_len→ int32 tensor [1, 1] = [1]  (1 token needed)
     return_generation_logits → bool tensor
     return_log_probs  → bool tensor = True

* Returns: ``output_ids`` numpy array + ``output_log_probs`` numpy array

Model classes
==============

``LlamaModel(InferenceModel)`` — MSP-backed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``run_inference(input: str, endpoint_parameters: LlamaEndpointParameters) -> InferenceResult``

  1. ``HFPretrainedModelTokenizer.get_tokenized_input()`` → token_ids + overflow_ratio
  2. ``_render_template(token_ids)`` → formatted prompt string (Jinja2)
  3. ``endpoint.send(PreparedRequest(formatted_prompt))``
  4. ``_get_score_from_details(response_details)`` → ``violation_score: float``
  5. ``_parse_response(response_text)`` → ``ModerationResult``

* ``_get_score_from_details()``:
  Extracts log-probabilities from top-N tokens histogram. Finds token for
  "true" in ``toBeFiltered`` field. Computes ``violation_score = exp(log_prob_true)``
  using 10-bin softmax histogram. Returns float in [0.0, 1.0].

* Template versions supported:

  .. list-table::
     :header-rows: 1
     :widths: 20 40 40

     * - Version
       - Template file
       - Notes
     * - V2.3
       - ``filter_prompt_v2_3.jinja``
       - Original template
     * - V2.3.2
       - ``filter_prompt_v2_3_2.jinja``
       - Refined policy descriptions
     * - V2.4
       - ``filter_prompt_v2_4.jinja``
       - Extended categories + improved examples

``LlamaModelInTeamserve(InferenceModel)`` — Teamserve gRPC-backed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Uses ``RAIFTTeamserveEndpoint`` (gRPC to Triton)
* Same tokenization + template rendering as ``LlamaModel``
* Teamserve gRPC timeout: 5s greenlet join timeout (``config.greenlet_join_timeout``)
* Circuit breaker on gRPC endpoint (fail_max=30)

Factory: ``RAILlamaModels``
=============================

Central factory for model selection based on feature flags:

.. code-block:: python

   @staticmethod
   def get_model(feature_service: FeatureService) -> InferenceModel:
       if feature_service.is_gpt_oss_safeguard_enabled():
           return GPTOSSModelInTeamserve(...)

       if feature_service.is_prompt_moderation_teamserve_v2_4_primary_enabled():
           model = LlamaModelInTeamserve(version=V2_4, ...)
       else:
           model = LlamaModel(version=V2_3_3, ...)   # default

       if feature_service.is_rai_ft_teamserve_shadowing_enabled():
           shadow = LlamaModelInTeamserve(version=V2_4, ...)
           return ShadowShim(ModelShadower(model, shadow, evaluator))

       if feature_service.is_shadow_with_ai_gateway_2_3_3_enabled():
           shadow = LlamaModel(version=V2_3_3, endpoint=msp_v2_3_3)
           return ShadowShim(ModelShadower(model, shadow, evaluator))

       return model

Model shadowing (``model_shadowing/shadower.py``)
==================================================

``ModelShadower[U, P]``:

* ``run_inference(input, params) -> InferenceResult[U]``
  1. ``greenlet_a = gevent.spawn(model_a.run_inference, input, params)``
  2. Wait for A with ``config.greenlet_join_timeout`` (default 30s)
  3. If A succeeded: ``pool.spawn(_wait_for_b)`` (best-effort, Pool size 20)
  4. ``_wait_for_b``: runs model_b.run_inference + evaluator.evaluate(a_result, b_result)
  5. Returns A's result unconditionally

``ShadowShim[U, P](InferenceModel)``:

Wraps ``ModelShadower`` presenting identical ``InferenceModel`` interface.
Used so the factory returns a uniform ``InferenceModel`` regardless of shadowing.

``RAIModelShadowEvaluator``:

Compares A vs B results and logs discrepancies for analysis. Does not affect
returned result. Key metric: ``violation_score`` delta between model versions.

Harm categories (``prompt/prompt_harm_category.py``)
======================================================

``PromptHarmCategory`` (StrEnum):

.. code-block:: python

   VIOLENCE_HARASSMENT       = "violence_harassment"
   HATE_DISCRIMINATION       = "hate_discrimination"
   MISINFORMATION            = "misinformation"
   SEXUAL_CONTENT            = "sexual_content"
   ILLEGAL_ACTIVITY          = "illegal_activity"
   SELF_HARM                 = "self_harm"
   JAILBREAK_PROMPT_INJECTION= "jailbreak_prompt_injection"
   INTELLECTUAL_PROPERTY     = "intellectual_property"
   COPYRIGHT                 = "copyright"
   PII                       = "pii"
   POLITICS                  = "politics"
   PROFANITY                 = "profanity"
   IMPERSONATION             = "impersonation"
   HIGH_RISK_DECISIONS       = "high_risk_decisions"
   SPECIALIST_ADVICE         = "specialist_advice"
   NONE                      = "none"
   UNKNOWN                   = "unknown"

* ``get_category_hash(category) -> str`` — stable short hash for ETag computation
* ``get_harm_category(value: str) -> PromptHarmCategory`` — case-insensitive lookup
  with ``_missing_()`` returning UNKNOWN for unrecognized values

Per-model ignored categories:

* V2.4: ``{}`` (no ignored categories — all 15 active)

Response parsing (``service/moderation/model_text_response_parse.py``)
========================================================================

Multi-stage fallback JSON parser designed for resilience against malformed LLM output:

1. **Stage 1 — strict**: ``json.loads(response_text)``
2. **Stage 2 — normalized quotes**: replace smart quotes, then ``json.loads()``
3. **Stage 3 — regex**: ``re.search(r'\{"category"\s*:\s*"[^"]+",\s*"toBeFiltered"\s*:\s*(true|false)\}', ...)``
4. **Stage 4 — key-value fallback**: ``re.search(r'category["\s:]+([a-z_]+)', ...)``
   + ``re.search(r'toBeFiltered["\s:]+(true|false)', ...)``

Returns: ``ModerationResult(category=str, toBeFiltered=bool)``
