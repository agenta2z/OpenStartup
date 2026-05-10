.. _rai-architectural-narrative:

============================================================
Architectural Narrative — Walking Tour
============================================================

Mental model in one paragraph
==============================

Atlassian's Responsible AI platform is a **two-repo system**: ``responsible-ai``
is the research/ML side that defines harm taxonomies, curates datasets, trains
models, and runs evaluation pipelines; ``responsible-ai-api`` is the production
Flask service that serves those trained models as a low-latency REST API consumed
by every Atlassian AI product. A content moderation request flows from the caller
through Flask blueprints → typed Pydantic controllers → service-layer moderation
logic → inference backends (LLaMA fine-tunes via MSP/Teamserve gRPC, GPT-OSS 20B
via Teamserve HTTP, or ShieldGemma2 via SageMaker for images) → confidence threshold
evaluation → Prometheus metrics + GASv3 analytics events → HTTP response with
ETag caching header.

The two repositories
=====================

``responsible-ai`` (research monorepo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Managed with **Pants** build system. Python 3.12.

* ``packages/rai/harm_taxonomy/`` — canonical ``HarmCategory`` Enum (16 categories)
  used as ground truth across evaluation and API code.
* ``notebooks/data/`` — Pandera-validated ``RAI_Dataset`` schema (7 columns);
  multi-source ingestion pipeline (AUP violations, OpenAI Moderation, Anthropic
  hh-rlhf, Jailbreak, Beavertails, NVIDIA Aegis 2.0, NVIDIA Topic Control, production
  feedback, ROVO People).
* ``notebooks/evaluation/`` — offline eval (sklearn accuracy/precision/recall/F1/FPR/FNR,
  confusion matrix, MLflow logging) + online LLM judge workflow (Databricks notebooks,
  Jinja2 prompt templates, GASv3 analytics aggregation).
* ``experiments/image_moderation_v1/`` — ShieldGemma2 experimental pipeline;
  LLaVAGuard dataset; SageMaker deployment (``ml.g6e.2xlarge``); parallel MP
  inference; latency benchmarks (p50/p95/p99); Streamlit demo app.
* ``experiments/PII_Anonymization/`` — Presidio-based PII entity detection and
  anonymization (12 entity types, custom HF transformer recognizer).
* ``msp_deploy/`` — Python scripts to register trained models in Atlassian's Model
  Service Platform (MSP/Tarot), shipping them to ``responsible-ai-api``.
* ``analytics/terraform/`` — Terraform IaC for Livegraph dashboards (ethical filtering,
  online eval metrics, per-user analytics).

``responsible-ai-api`` (production Flask service)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Managed with **uv** / ``pyproject.toml``. Python 3.12. Deployed via Atlassian
Micros on Docker + gunicorn/gevent workers, listening on port 8080.

The 5 internal layers (responsible-ai-api)
============================================

::

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Layer 1: API / Routing  (src/api/)                                  │
  │    Flask app bootstrap (FlaskMicros, ProxyFix)                       │
  │    Blueprint hierarchy: api_blueprint → api_v1_blueprint →           │
  │      moderation_blueprint → {prompt,output,agent,image}_blueprint    │
  │    Swagger UI + /openapi.json served from swagger.yaml               │
  │    Global error handlers: APIException, ValidationError, NotFound    │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓ dispatches to
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Layer 2: Service / Moderation  (src/service/moderation/)            │
  │    prompt/prompt_moderation.py     — primary text filter             │
  │    output/output_moderation.py     — streaming chunk filter          │
  │    agent/agent_moderation.py       — agent config safety             │
  │    image/image_moderation.py       — multimodal image filter         │
  │    Shared: harm categories, types, request context, response headers │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓ calls
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Layer 3: Inference Models  (src/inference_models/)                  │
  │    Abstract base: ModelEndpoint[T,U,P], InferenceModel[U,P]          │
  │    LLaMA: RAIFTEndpoint → MSP /v1/msp/rai-ft-content-filter-v2-3-3   │
  │    LLaMA: RAIFTTeamserveEndpoint → Teamserve gRPC (circuit breaker)  │
  │    GPT-OSS: TritonOpenAIClient → Teamserve HTTP /v1/chat/completions │
  │    Image V0: SageMakerInferenceBase → image-moderation-v0            │
  │    Image V1: ImageModerationV1Client → image-moderation-v1-model     │
  │    Model shadowing: ModelShadower (gevent Pool 20) + ShadowShim      │
  │    Confidence: PromptHarmConfidenceThresholds (60s TTL cache)        │
  └──────────────────────────────────────────────────────────────────────┘
                                  ↓ reaches
  ┌──────────────────────────────────────────────────────────────────────┐
  │  External AI Inference Backends                                      │
  │    MSP endpoint:     /v1/msp/rai-ft-content-filter-v2-3-3            │
  │    Teamserve gRPC:   grpc-teamserve-us-west-2.dev.services.kitt-inf  │
  │    Teamserve HTTP:   …/tarot/responsible-ai/versions/…/v1/chat/…     │
  │    SageMaker V0:     image-moderation-v0 (DEIM/D-FINE object detect) │
  │    SageMaker V1:     image-moderation-v1-model (ShieldGemma2)        │
  │    Anti-abuse API:   abuse-filescanner-{dev,stg,prod}-east           │
  │    AI Gateway Raw:   Agent moderation direct calls                   │
  └──────────────────────────────────────────────────────────────────────┘

  Cross-cutting (all layers):
  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
  │  feature_service │  │  metrics/    │  │  gasv3_         │  │  slauth/     │
  │  (Statsig SDK)   │  │  (Prometheus)│  │  analytics/     │  │  tenant_ctx  │
  └─────────────────┘  └──────────────┘  └─────────────────┘  └──────────────┘

Request lifecycle — prompt moderation (detailed)
=================================================

1. **HTTP ingress** — POST ``/v1/moderation/prompt/`` with headers:
   - Required: ``X-Atlassian-Cloud-Id``, ``X-Atlassian-Use-Case-Id``
   - One-of: ``X-Slauth-User-Context`` OR ``X-Atlassian-Staff-Context-Token``
   - Optional: ``If-None-Match`` (ETag cache check), ``X-RAI-Debug-Verbose``

2. **before_request: ETag check** (``prompt_etag.py``) — If ``If-None-Match``
   header present, computes HMAC/SHA-256 hash of ``(prompt + model_version)``.
   Generates all possible category ETags. Returns HTTP 304 on match — zero inference.

3. **before_request: header validation** — ``@required_headers`` decorator enforces
   presence of cloud_id + use_case_id + one-of auth header; returns 400 on failure.

4. **Pydantic validation** — ``@validate()`` (flask-pydantic) parses
   ``ModeratePromptRequest(prompt: str[min_length=1], debug: Optional[DebugOptions])``.
   Strict mode: extra fields rejected. Returns 422 on schema violation.

5. **ModerationRequestContext.from_incoming_http_request()** — resolves:
   - ``cloud_id`` from ``X-Atlassian-Cloud-Id``
   - ``user_id`` from SLAuth headers (``X-Slauth-User-Context-Account-Id``)
   - ``use_case_id`` from ``X-Atlassian-Use-Case-Id``
   - ``issuer`` from ``X-Slauth-Issuer``

6. **Debug overrides** — if ``debug.feature_overrides`` provided, applies per-request
   Statsig gate overrides via ``feature_service.set_request_overrides()``.

7. **Feature flag resolution** (Statsig) — ``feature_service`` checks gates:
   - ``is_gpt_oss_safeguard_enabled()`` → use ``GPTOSSModelInTeamserve``
   - ``is_prompt_moderation_teamserve_v2_4_primary_enabled()`` → use V2.4
   - ``is_rai_ft_teamserve_shadowing_enabled()`` → wrap with ``ShadowShim``

8. **Service: tokenization** — ``HFPretrainedModelTokenizer.get_tokenized_input()``;
   tracks ``overflow_ratio`` (tokens truncated), ``consumed_tokens``.

9. **Service: template rendering** — Jinja2 template rendered with policy definitions,
   examples, and prompt text. Template version determines ``prompt_evaluation_version``.

10. **Inference** — ``model.run_inference(prompt, endpoint_params)``:
    - MSP path: POST to ``/v1/msp/rai-ft-content-filter-v2-3-3`` via AI Gateway sync client
    - Teamserve gRPC path: Triton ``InferInput`` tensors (input_ids, input_lengths,
      request_output_len, return_log_probs) → ``GrpcEndpoint.invoke()``
    - Response: JSON ``{"category": str, "toBeFiltered": bool}`` + log-probs histogram

11. **Multi-stage JSON parsing** (``model_text_response_parse.py``) — strict JSON →
    quote normalization → regex patterns → key-value fallback. Returns
    ``ModerationResult`` with ``category`` and ``toBeFiltered``.

12. **Confidence threshold** — ``PromptHarmConfidenceThresholds.get_threshold(category,
    model_version)`` (60s TTL cached from Feature Service). If
    ``violation_score >= threshold`` → DISALLOWED.

13. **Response headers** (``response_headers.py``) — sets on HTTP response:
    - ``X-RAI-Model-Evaluation-Version``
    - ``X-RAI-Prompt-Evaluation-Version``
    - ``X-RAI-Prompt-Violation-Score`` (float)
    - ``ETag: W/"<base_hash>:<category_hash>"``

14. **Observability** (non-blocking):
    - ``send_outcome_metrics()`` → Prometheus counter with tags:
      harm_category, violation_score, consumed_tokens, overflow_ratio, model_version
    - ``analytics_client.send_content_evaluated_event()`` → GASv3 via gevent Pool(10)

15. **Return** ``ModeratePromptResponse(status=ALLOWED|DISALLOWED, harm_category=str)``
    (violation_score, versions excluded from body; in headers only).

Request lifecycle — output moderation (streaming)
==================================================

NDJSON stream protocol. Each line: ``{stream_id, current_chunk, chunk_index}``.

``stream_processor.py`` processes each line:

1. Accumulate: ``stream_accumulated_content[stream_id] += current_chunk``
2. Size limits: ``MAX_ACCUMULATED_CONTENT_SIZE=10MB``, ``MAX_CHUNK_SIZE=100KB``, ``MAX_LINE_SIZE=1MB``
3. URL extraction: ``url_checker.extract_external_urls(accumulated)`` — regex ``\b(https?://|www\.)[^\s<>"']{1,2048}``; filters internal domains from ``internal_domains.txt``
4. Diff: count new URLs in current chunk vs previous accumulated
5. ML moderation: ``PromptModerationService.predict_harm_category_in_prompt(accumulated)``
6. Early exit: first DISALLOWED chunk terminates stream
7. Per-chunk response: ``ModerateOutputResponse(status, stream_id, chunk_index, harm_category, content, external_urls)``

Request lifecycle — agent moderation
=======================================

Agent moderation evaluates full agent configurations against harm policies using
an LLM-as-judge approach.

**Input** ``ModerateAgentRequest``:
- ``name: str``
- ``description: Optional[str]``
- ``prompt: str``
- ``conversation_starters: Optional[List[AgentConversationStarters]]``
- ``follow_up_prompt: Optional[str]``

**Model selection** per ``cloud_id`` via ``_get_moderation_config()``:
- Default: ModerationV2_3Config (gpt-4o or gpt-4-turbo-mini via AI Gateway Raw)
- Flag overrides: V1, V1.1, V2.3.1, V2.3_SH, V3 configs

**System message**: *"You are a content moderation expert..."*
**Response parsing**: JSON extraction of ``harm_category``, ``toBeFiltered``, ``violation_score``

**15 harm categories** (AgentHarmCategory): includes EROTIC_CHATBOTS (not in prompt),
excludes PROFANITY (not in agent). Deprecated aliases: HATE_SPEECH → HATE_DISCRIMINATION,
HARASSMENT/VIOLENCE → VIOLENCE_HARASSMENT.

Request lifecycle — image moderation
=======================================

**Parallel gevent execution** (``image_moderation_sagemaker.py``):

1. **V0** (``image-moderation-v0``): DEIM/D-FINE large object detection. Input: base64 image.
   Output: ``{class: str, score: float}`` for human/nudity/violence/etc.
2. **V1** (``image-moderation-v1-model``): ShieldGemma2 multimodal. Input: base64 image.
   Output: ``{policy: str, prediction: {category: score}}`` for 12 harm categories.
3. **Anti-abuse** (``antiabuse_client.py``): POST ``/api/moderation/scan`` with
   ``{region, platform, fileID, containerID, userID, media}``. Classifications:
   SPAM, ABUSE, POLICY_VIOLATION, CLEAN. Circuit breaker: fail_max=5, reset=60s.

**Result merging**: V1 policy violations override V0 → V0 human class → V0 top category.
``violation_score = max(V0_score, V1_score)``

Authentication and tenant context
===================================

**SLAuth headers** parsed by ``SlauthUserContextHeaders``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Header
     - Meaning
   * - ``X-Slauth-User-Context-Status``
     - ``none`` / ``invalid`` / ``valid``
   * - ``X-Slauth-User-Context``
     - Encoded JWT context blob
   * - ``X-Slauth-User-Context-Account-Id``
     - Atlassian Account ID (AAID)
   * - ``X-Slauth-User-Context-Request-Principal``
     - Service calling on behalf of user
   * - ``X-Slauth-Issuer``
     - Authenticating system
   * - ``X-Slauth-Principal``
     - Request principal (service identity)

**TenantContextClient** — HTTP calls to TCS sidecar (``http://localhost:50050``)
to resolve ``cloud_id`` → tenant metadata.

**ASAP JWT** — ``config.asap_signer`` created from ``ASAP_ISSUER`` + ``ASAP_PRIVATE_KEY``
env vars using ``atlassian_jwt_auth``. Used for service-to-service calls (anti-abuse,
Teamserve). Supports ``reuse_jwts=True`` for JWT reuse within expiry window.

Feature flag system (Statsig)
================================

``FeatureService`` wraps Statsig Server SDK. 30+ feature gates:

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Gate
     - Effect when enabled
   * - ``ENABLE_GPT_OSS_SAFEGUARD``
     - Switch prompt moderation to GPT-OSS 20B
   * - ``ENABLE_TEAMSERVE_V2_4_PRIMARY``
     - LLaMA V2.4 via Teamserve as primary model
   * - ``ENABLE_SHADOW_WITH_TEAMSERVE_2_4``
     - Shadow V2.3.3 with V2.4 in parallel
   * - ``ENABLE_TEAMSERVE_SHADOWING_FOR_PROMPT_MODERATION``
     - Shadow MSP primary with Teamserve
   * - ``ENABLE_SHADOW_WITH_AI_GATEWAY_2_3_3``
     - Shadow with AI Gateway 2.3.3
   * - ``ENABLE_FAIL_OPEN_ON_MODEL_TIMEOUT``
     - Return NONE/ALLOWED on inference timeout
   * - ``ENABLE_FAIL_OPEN_ON_CIRCUIT_BREAKER_OPEN``
     - Return ALLOWED when Triton CB open
   * - ``ENABLE_IMAGE_MODERATION_V1``
     - Enable ShieldGemma2 in parallel with V0
   * - ``ENABLE_IMAGE_MODERATION_ANTIABUSE``
     - Enable anti-abuse scan for images
   * - ``DISABLE_ANALYTICS``
     - Kill switch for GASv3 analytics
   * - ``ENABLE_JSON_DYNAMIC_CONFIG_THRESHOLDS``
     - Load thresholds from dynamic config JSON
   * - ``ENABLE_STANDARDIZED_IMAGE_MODERATION_RESPONSE``
     - Return ``ModerateImageResponseV1`` with abhorrent_material + actions
   * - ``DISABLE_EXTERNAL_LLM_CALLS``
     - Block all external LLM calls (safety kill switch)
   * - ``READ_EXTERNAL_LLM_CALLS_ORG_SETTING``
     - Honour org-level external LLM setting
   * - ``ENABLE_SAFE_PARSE_JSON_RESPONSE``
     - Use fallback JSON parsing for model responses
   * - ``ENABLE_CUSTOM_RETRY_CONFIG``
     - Enable tenacity retry on AI Gateway calls

**User attributes** for gate evaluation: ``tenantId=cloud_id``, ``atlassianAccountId=user_id``.
**Environments**: DEV→development, STAGING→staging, PROD→production.
**Per-request overrides**: ``debug.feature_overrides: {gate_name: bool}`` in request body.

Error resilience design
=========================

The system is designed to **fail open** (pass content through) rather than block on
inference failure:

* ``InferenceErrorContext`` — dataclass tracking error metadata: ``fail_open_on_error``,
  ``use_case_id``, ``cloud_id``.
* ``@contextmanager inference_error_handler(ctx)`` — catches all inference exceptions,
  logs structured error, optionally returns ``{category=NONE, score=0.0}`` → ALLOWED.
* **Triton gRPC circuit breaker**: ``pybreaker.CircuitBreaker(fail_max=30)``
* **Triton OpenAI circuit breaker**: ``pybreaker.CircuitBreaker(fail_max=30)``
* **Anti-abuse circuit breaker**: ``pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60s)``
* **GASv3 analytics**: async gevent Pool(10), never blocks moderation response
* **AI Gateway retries** (tenacity): retry on ``TimeoutException`` + ``NetworkError``;
  no retry on 429 (rate limit). ``wait_random_exponential``, ``stop_after_attempt(3)``.
* **Shadowing fail-safety**: if gevent Pool(20) is full, shadow model skipped silently.
