.. _mod-feature-flags:

================
Feature Flags (Statsig)
================

:File: ``src/feature_service.py`` (256 LoC)
:Importance: **P1 — controls model selection and all rollouts**

Overview
=========

``FeatureService`` wraps the Statsig Server SDK to provide feature gate evaluation
throughout the service. It supports ~30 gates, per-request overrides, and
developer-mode bypasses.

``Features`` enum (all Statsig gate names)
==========================================

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Gate constant
     - Effect
   * - ``ENABLE_GPT_OSS_SAFEGUARD``
     - Use GPT-OSS 20B for prompt moderation (replaces LLaMA)
   * - ``ENABLE_TEAMSERVE_V2_4_PRIMARY``
     - Use LLaMA V2.4 via Teamserve as primary model
   * - ``ENABLE_SHADOW_WITH_TEAMSERVE_2_4``
     - Shadow with V2.4 while V2.3.3 is primary
   * - ``ENABLE_SHADOW_WITH_AI_GATEWAY_2_3_3``
     - Shadow with MSP V2.3.3 while Teamserve is primary
   * - ``ENABLE_TEAMSERVE_SHADOWING_FOR_PROMPT_MODERATION``
     - Shadow MSP primary with Teamserve (for comparison)
   * - ``ENABLE_TEAMSERVE_PRIMARY_FOR_PROMPT_MODERATION``
     - Use Teamserve as primary (LLaMA gRPC)
   * - ``ENABLE_FAIL_OPEN_ON_MODEL_TIMEOUT``
     - Return ALLOWED on inference timeout (fail-open)
   * - ``ENABLE_FAIL_OPEN_ON_CIRCUIT_BREAKER_OPEN``
     - Return ALLOWED when circuit breaker is open
   * - ``ENABLE_IMAGE_MODERATION_V1``
     - Run ShieldGemma2 (V1) in parallel with V0
   * - ``ENABLE_IMAGE_MODERATION_ANTIABUSE``
     - Enable anti-abuse scan for images
   * - ``ENABLE_EXTRA_IMAGE_PREPROCESSING``
     - Apply additional image preprocessing before inference
   * - ``ENABLE_STANDARDIZED_IMAGE_MODERATION_RESPONSE``
     - Return ``ModerateImageResponseV1`` with abhorrent_material + actions
   * - ``DISABLE_ANALYTICS``
     - Kill switch: drop all GASv3 analytics events
   * - ``DISABLE_EXTERNAL_LLM_CALLS``
     - Block all external LLM calls (emergency kill switch)
   * - ``READ_EXTERNAL_LLM_CALLS_ORG_SETTING``
     - Honour org-level external LLM setting
   * - ``ENABLE_JSON_DYNAMIC_CONFIG_THRESHOLDS``
     - Load confidence thresholds from dynamic config JSON (vs Feature Service)
   * - ``ENABLE_SAFE_PARSE_JSON_RESPONSE``
     - Use multi-stage fallback JSON parser for model responses
   * - ``ENABLE_CUSTOM_RETRY_CONFIG``
     - Enable tenacity retry config on AI Gateway calls
   * - ``ENABLE_STRICT_TOKENIZATION_FAILURE``
     - Fail hard on tokenization failure (vs fail-open)
   * - ``ENABLE_INCREASED_INPUT_CLIPPING_BUFFER``
     - Increase token clipping buffer for long prompts
   * - ``ENABLE_USER_INPUT_LOGGING``
     - Log user input content (for debugging; off by default for privacy)
   * - ``ENABLE_CONN_POOL_LOGGING``
     - Log httpx connection pool state after each request
   * - ``AGENT_MODERATION_PROMPT_V2_3_1``
     - Use V2.3.1 agent moderation prompt template
   * - ``AGENT_MODERATION_V3``
     - Use V3 agent moderation config
   * - ``ENABLE_FOR_DEVELOPER``
     - Internal developer bypass (skips use_case_id allow-list check)

``FeatureService`` implementation
===================================

.. code-block:: python

   class FeatureService:
       def __init__(self):
           statsig.initialize(
               sdk_key=config.statsig_sdk_key,
               options=StatsigOptions(
                   environment=config.statsig_environment,
                   local_mode=config.is_local,
               )
           )

       def _check_gate(self, gate: Features) -> bool:
           user = StatsigUser(custom_ids=self._get_user_attributes())
           return statsig.check_gate(user, gate.value)

       def _get_user_attributes(self) -> FeatureGateUserAttributes:
           ctx = ModerationRequestContext.from_incoming_http_request()
           return FeatureGateUserAttributes(
               tenantId=ctx.cloud_id or "",
               atlassianAccountId=ctx.user_id or "",
           )

Per-request override system
=============================

Supports ``debug.feature_overrides`` in request body (developer use only):

.. code-block:: python

   def set_request_overrides(self, overrides: dict[str, bool]) -> None:
       # Stores overrides in thread-local / request context
       _request_overrides.overrides = overrides

   def _check_gate(self, gate: Features) -> bool:
       # Checks thread-local overrides first
       if gate.value in _request_overrides.overrides:
           return _request_overrides.overrides[gate.value]
       # Falls through to Statsig

   def get_request_overrides(self) -> dict[str, bool]:
       # Returns active overrides (for debug trace inclusion)
       return getattr(_request_overrides, "overrides", {})

Use-case ID allowlist
======================

``is_use_case_allowed() -> bool``:

* Returns ``True`` if ``use_case_id`` is in the allowlist (``USE_CASE_IDS`` set)
* Returns ``True`` if ``ENABLE_FOR_DEVELOPER`` gate is on
* Used to restrict moderation endpoints to known callers

Developer mode (local/nebulae)
================================

When ``config.is_local=True``:

* ``StatsigOptions(local_mode=True)`` — all gates default to False (no network calls)
* ``statsig_flags/local_overrides.py`` — can specify local override file for testing
* ``NO_ASAP_SIGNER=true`` — uses Mock signer (no JWT needed)
