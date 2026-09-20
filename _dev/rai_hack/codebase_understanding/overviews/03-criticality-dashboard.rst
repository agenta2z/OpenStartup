.. _rai-criticality-dashboard:

============================================================
Criticality Dashboard — Blast-radius Rankings
============================================================

:Purpose: SRE on-call quick reference. Sorted P0 → P3.

P0 — Full service outage
==========================

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Component
     - File(s)
     - Failure mode
   * - Flask app bootstrap
     - ``src/app.py``, ``src/config.py``
     - Missing ``ASAP_ISSUER``/``ASAP_PRIVATE_KEY`` → ``ValueError`` at startup → service never starts
   * - Blueprint registration
     - ``api/v1/moderation/moderation_blueprint.py``
     - All 4 moderation endpoints return 404
   * - gunicorn/gevent worker pool
     - ``src/gunicorn.conf.py``
     - Worker exhaustion → 502 gateway errors; gevent timeout default 600s

P1 — Specific moderation type broken
======================================

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Component
     - File(s)
     - Failure mode
   * - Prompt moderation service
     - ``service/moderation/prompt/prompt_moderation.py``
     - Prompts pass (fail-open NONE) or 500s; primary LLM filter bypassed
   * - LLaMA inference (MSP)
     - ``inference_models/rai_llama.py`` (``RAIFTEndpointV2_3_3``)
     - MSP endpoint down → falls to Teamserve or fail-open if flag set
   * - Teamserve gRPC (Triton)
     - ``inference_models/triton_grpc_client.py``
     - Circuit breaker trips at fail_max=30 → CB open → fail-open if flag enabled
   * - Agent moderation service
     - ``service/moderation/agent/agent_moderation.py``
     - Agent configs not screened; Rovo/AgentStudio unprotected
   * - GPT-OSS (Teamserve HTTP)
     - ``inference_models/rai_gpt_oss.py``
     - Agent + GPT-OSS safeguard path broken
   * - Image moderation service
     - ``service/moderation/image/image_moderation.py``
     - Image uploads not screened
   * - SageMaker client
     - ``inference_models/image_moderation_sagemaker.py``
     - Both V0+V1 inference fail; gevent pool + fail-open applies
   * - Output stream processor
     - ``service/moderation/output/stream_processor.py``
     - Streaming moderation broken; LLM outputs not scanned in real-time
   * - Feature service (Statsig)
     - ``feature_service.py``
     - All gates return False/default; model selection fixed at V2.3.3;
       fail-open flags off; shadowing off

P1 — Authentication / tenant broken
=====================================

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Component
     - File(s)
     - Failure mode
   * - SLAuth user context
     - ``slauth/user_context.py``
     - user_id=None → analytics sends anonymous events; no auth block (auth is upstream)
   * - Tenant context client
     - ``tenant_context/tenant_context_client.py``
     - cloud_id resolution fails; downstream context validation may reject request
   * - ASAP signer
     - ``src/config.py`` (``config.asap_signer``)
     - All service-to-service calls (anti-abuse, Teamserve) fail 401

P2 — Telemetry / observability broken
========================================

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Component
     - File(s)
     - Failure mode
   * - GASv3 analytics client
     - ``gasv3_analytics/rai_analytics_client.py``
     - Moderation events not tracked; non-blocking (async Pool 10) → no customer impact
   * - Prometheus metrics
     - ``metrics/metrics_handler.py``
     - Dashboards go dark; alerting may miss anomalies
   * - Anti-abuse client
     - ``antiabuse/antiabuse_client.py``
     - Scan fails open (circuit breaker fail_max=5); images not CSAM/spam checked
   * - Structured logging
     - ``src/micros_logging.py``
     - Log context lost; debugging harder; no request impact

P3 — Performance / developer experience degraded
==================================================

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Component
     - File(s)
     - Failure mode
   * - ETag prompt caching
     - ``api/v1/moderation/etag/prompt_etag.py``
     - Cache miss → inference on every duplicate request; higher latency + cost
   * - Time cache (threshold TTL)
     - ``cache/time_cache.py``
     - Confidence threshold lookups hit Feature Service every request (60s TTL lost)
   * - Debug trace builder
     - ``api/v1/moderation/debug_trace_builder.py``
     - ``debug.verbose`` traces unavailable; developer experience only; no user impact
   * - Model shadowing
     - ``inference_models/model_shadowing/shadower.py``
     - Shadow evaluation silent fails if Pool(20) full; A/B data not collected

Key SLOs to monitor
=====================

* **Prompt moderation p99 latency** target < 2s
  (Teamserve gRPC: 5s greenlet join timeout; MSP: 2s read timeout)
* **Image moderation p99 latency** target < 30s
  (SageMaker inference timeout = 30s from ``config.sagemaker_inference_timeout``)
* **Fail-open rate** — ``FAIL_OPEN_TYPE`` tag on ``PROMPT_MODERATION_OUTCOME`` metric;
  non-zero indicates model instability
* **Circuit breaker state** — ``ANTIABUSE_CIRCUIT_BREAKER_STATE`` metric tag;
  "open" means abuse scanning is offline
* **Token overflow ratio** — ``token_overflow_ratio`` Prometheus histogram;
  high ratio means prompts being truncated before inference (accuracy risk)
* **GASv3 event delivery** — monitor for gaps in ethical_filtering_analytics dashboards

On-call runbook pointers
==========================

* **High 500s on /v1/moderation/prompt/**:
  1. Check Teamserve gRPC CB state (``ANTIABUSE_CIRCUIT_BREAKER_STATE`` metric).
  2. Toggle ``ENABLE_FAIL_OPEN_ON_CIRCUIT_BREAKER_OPEN`` in Statsig.
  3. Check MSP endpoint health.

* **Image moderation timeouts**:
  1. SageMaker V0/V1 endpoint cold start. Check AWS SageMaker console in ``MICROS_AWS_REGION``.
  2. Tune ``SAGEMAKER_INFERENCE_TIMEOUT`` env var (default 30s).

* **Agent moderation 500s**:
  1. Check AI Gateway connectivity (agent uses Raw client, not MSP/Teamserve).
  2. Check ``cloud_id``-specific model config in ``agent_moderation.py:_get_moderation_config()``.

* **All requests returning ALLOWED unexpectedly**:
  1. Verify ``ENABLE_FAIL_OPEN_ON_MODEL_TIMEOUT`` not globally enabled.
  2. Verify ``DISABLE_EXTERNAL_LLM_CALLS`` kill switch is off.

* **Analytics gap in GASv3**:
  1. Check ``DISABLE_ANALYTICS`` feature gate in Statsig (should be false in prod).
  2. Check GASv3 client pool health.
