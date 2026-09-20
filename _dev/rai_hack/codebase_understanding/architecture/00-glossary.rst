.. _rai-glossary:

========
Glossary
========

.. glossary::

   RAI
      Responsible AI. The team and platform at Atlassian responsible for content
      moderation across all AI-powered products.

   responsible-ai-api
      The production Flask service (this repo) that exposes REST endpoints for
      content moderation. Deployed via Atlassian Micros.

   responsible-ai
      The research/ML monorepo containing harm taxonomy, dataset infrastructure,
      model evaluation pipelines, experiments, and model deployment scripts.

   MSP
      Model Service Platform. Atlassian's internal platform for registering and
      serving ML models. RAI fine-tuned models are registered here and accessed
      via ``/v1/msp/rai-ft-content-filter-v2-3-3``.

   Teamserve
      Atlassian's internal ML inference platform. Used for both gRPC (LLaMA via
      Triton) and HTTP (GPT-OSS 20B via OpenAI-compatible API) inference.

   Triton
      NVIDIA Triton Inference Server. Powers Teamserve gRPC endpoints.

   SageMaker
      AWS SageMaker. Used for image moderation endpoints (V0: DEIM/D-FINE,
      V1: ShieldGemma2).

   GASv3
      Atlassian's analytics event pipeline (v3). RAI fires ``OperationalEvent``
      objects for every moderation outcome.

   Statsig
      Feature flag platform used by RAI for gate-based model selection, fail-open
      configuration, and experiment rollouts.

   SLAuth
      Atlassian's service-to-service authentication layer. Passes identity via
      ``X-Slauth-*`` headers.

   ASAP
      Atlassian Service Authentication Protocol. JWT-based auth used for
      service-to-service calls (anti-abuse, Teamserve).

   TCS
      Tenant Context Service. Sidecar resolving ``cloud_id`` → tenant metadata.
      Accessed via ``http://localhost:50050``.

   HarmCategory
      Canonical 16-value enum defined in ``responsible-ai/packages/rai/harm_taxonomy/``.
      Used as ground truth across evaluation and API code.

   ETag
      HTTP caching mechanism used by prompt moderation. Computed as
      ``W/"SHA256(prompt + model_version)[:category_hash]"``. On ``If-None-Match``
      match → HTTP 304, zero inference.

   Model Shadowing
      Parallel gevent execution of a primary model (A) and a shadow model (B).
      Only A's result is returned. B's result is used for comparison/evaluation.
      Pool size: 20. Shadow is skipped silently if pool is full.

   gevent
      Python cooperative multitasking library (green threads). Used for parallel
      inference (image V0+V1, model shadowing, async analytics).

   pybreaker
      Python circuit breaker library. Used on Triton gRPC, Triton OpenAI, and
      anti-abuse endpoints. ``fail_max=30`` for Triton; ``fail_max=5`` for anti-abuse.

   Pandera
      Python dataframe validation library. Used in ``responsible-ai`` notebooks to
      enforce ``RAI_Dataset`` schema (7 columns, typed, uniqueness constraints).

   Pants
      Python monorepo build system used in ``responsible-ai``. Manages inter-package
      dependencies and test execution.

   LLaVAGuard
      A dataset of images used for image moderation evaluation experiments.

   ShieldGemma2
      Google's multimodal safety model (``google/shieldgemma-2-4b-it``). Used in
      image moderation V1 SageMaker endpoint.

   AUP
      Atlassian User Policy. The set of content policies that RAI enforces.

   LLM Judge
      An LLM (e.g. Claude or GPT-4) used as an automated evaluator to assess
      whether production moderation decisions are correct. Used in online evaluation.
