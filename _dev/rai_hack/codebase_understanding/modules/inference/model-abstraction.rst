.. _mod-inference-abstraction:

==========================
Inference Model Abstraction
==========================

:File: ``src/inference_models/model.py`` (281 LoC)
:Importance: **P1 — core abstraction for all model backends**

Overview
=========

``model.py`` defines the type-safe generic abstract hierarchy that all 4 inference
backends implement. It uses Python generics (``TypeVar``, ``Generic``) throughout.

Class hierarchy
================

.. code-block:: text

   ModelTokenizer (ABC)
   └── HFPretrainedModelTokenizer

   ModelEndpoint[T, U, P] (ABC, Generic)
   ├── RAIFTEndpoint (rai_llama.py)
   │   ├── RAIFTTeamserveEndpoint
   │   └── RAIFTEndpointV2_3_3
   ├── GPTOSSTeamserveEndpoint (rai_gpt_oss.py)
   └── SageMakerInferenceBase (sagemaker_base.py)

   InferenceModel[U, P] (ABC, Generic)
   ├── LlamaModel
   ├── LlamaModelInTeamserve
   ├── GPTOSSModelInTeamserve
   └── ImageModerationSageMaker

   ShadowShim[U, P](InferenceModel)   # wraps ModelShadower as InferenceModel

Key classes
============

``ModelTokenizer`` (ABC)
~~~~~~~~~~~~~~~~~~~~~~~~~

Abstract tokenizer with two methods:

* ``get_tokenized_input_as_numpy_ndarray(input: str, options: TokenizeOptions) -> ndarray``
* ``get_tokenized_input_as_int_list(input: str) -> List[int]``
* ``apply_model_chat_template(user_prompt: str, system_prompt: str) -> str``

``HFPretrainedModelTokenizer``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wraps HuggingFace ``PreTrainedTokenizerFast``:

* ``_get_tokenized_input()``: traced span for tokenization with overflow tracking
* Returns ``TokenizedInput[T]`` with fields: ``token_ids``, ``overflow_ratio``,
  ``consumed_tokens``
* ``overflow_ratio``: fraction of input tokens that were truncated (important for
  accuracy monitoring — high overflow = model saw less than full prompt)

``TokenizeOptions``
~~~~~~~~~~~~~~~~~~~~

Dataclass controlling tokenization behaviour:

* ``max_length: int`` — maximum token count (model context window)
* ``truncation: bool`` — whether to truncate overlong inputs
* ``padding: bool``
* ``add_special_tokens: bool``

``ModelEndpoint[T, U, P]`` (ABC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generic endpoint abstraction (T=input type, U=output type, P=params type):

* ``send(prepared_request: PreparedRequest[T], **kwargs) -> InferenceResult[U]``

``InferenceModel[U, P]`` (ABC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Core interface all models implement:

* ``run_inference(input: str, endpoint_parameters: P) -> InferenceResult[U]``

``InferenceResult[U]``
~~~~~~~~~~~~~~~~~~~~~~~

Dataclass returned by all model backends:

* ``result: U`` — parsed model output
* ``model_evaluation_version: str`` — version string used in response headers
* ``prompt_evaluation_version: str`` — prompt template version

Error types (``errors.py``)
==============================

* ``MalformedModelOutputError`` — model returned unparseable response
* ``NoCompletionsReturnedError`` — model returned empty completions list
* ``AIGatewayResponseException`` — AI Gateway returned error response

Error handling (``error_handling.py``, 237 LoC)
=================================================

``InferenceErrorContext`` dataclass:

* ``fail_open_on_error: bool`` — if True, return NONE/0.0 on any error
* ``use_case_id: str``
* ``cloud_id: str``
* ``error_type: Optional[str]`` — classified error label for metrics

``@contextmanager inference_error_handler(ctx: InferenceErrorContext)``:

Catches and classifies:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Exception
     - ``error_type`` tag
     - Behaviour
   * - ``httpx.TimeoutException``
     - ``TIMEOUT``
     - fail-open if flag set; sends timeout metric
   * - ``pybreaker.CircuitBreakerError``
     - ``CIRCUIT_BREAKER_OPEN``
     - fail-open if flag set; sends CB metric
   * - ``AIGatewayRequestException`` (transport)
     - ``TRANSPORT_ERROR``
     - fail-open if flag set
   * - ``AIGatewayResponseException`` (HTTP error)
     - ``AIGATEWAY_RESPONSE_ERROR``
     - re-raises as ``APIException``
   * - ``MalformedModelOutputError``
     - ``MALFORMED_OUTPUT``
     - fail-open if flag set; logs warning
   * - Any other ``Exception``
     - ``UNKNOWN``
     - fail-open if flag set; logs full traceback

Fail-open return value: ``InferenceResult(result=ModerationResult(category=NONE, toBeFiltered=False), ...)``.

Confidence Thresholds (``confidence/confidence_thresholds.py``)
================================================================

``PromptHarmConfidenceThreshold``:

* ``harm_category: str``
* ``threshold: float``
* ``model_version: Optional[str]``
* ``exceeds_threshold(score: float) -> bool`` — ``score >= threshold``
* String serialization: ``"category|threshold"`` or ``"category|threshold|model_version"``

``PromptHarmConfidenceThresholds``:

* ``get_threshold(category: str, model_version: str) -> float``
  Lookup by (category, model_version); falls back to (category, "other"); then 0.5 default.
* ``to_flat_list() -> List[str]`` — serializes collection to string list

Loading pattern (60s TTL cache):

.. code-block:: python

   @time_cache(max_age=60)
   def get_prompt_harm_confidence_thresholds() -> PromptHarmConfidenceThresholds:
       # Loads from Feature Service (Confluence-backed remote config)
       # Parses each string entry into PromptHarmConfidenceThreshold
       ...
