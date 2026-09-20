.. _rai-inference-backends:

===================
Inference Backends
===================

See :doc:`../02-request-lifecycle` for detailed call stacks.

Summary of all inference backends:

.. list-table::
   :header-rows: 1
   :widths: 25 20 15 20 20

   * - Backend
     - Protocol
     - Model
     - Used for
     - Circuit breaker
   * - MSP via AI Gateway
     - HTTPS/HTTP
     - LLaMA RAI FT V2.3.3
     - Prompt (default primary)
     - None (tenacity retry)
   * - Teamserve gRPC (Triton)
     - gRPC
     - LLaMA RAI FT V2.4
     - Prompt (feature-flagged)
     - fail_max=30
   * - Teamserve HTTP (OpenAI)
     - HTTPS
     - GPT-OSS Safeguard 20B
     - Prompt alt + agent
     - fail_max=30
   * - AI Gateway Raw
     - HTTPS
     - gpt-4o / gpt-4-turbo-mini
     - Agent (default)
     - None (tenacity retry)
   * - SageMaker V0
     - HTTPS (boto3)
     - DEIM/D-FINE large
     - Image (always)
     - None (credential retry)
   * - SageMaker V1
     - HTTPS (boto3)
     - ShieldGemma2 4B
     - Image (feature-flagged)
     - None (gevent fallback)
   * - Anti-abuse API
     - HTTPS (httpx)
     - n/a (rule-based)
     - Image (best-effort)
     - fail_max=5 reset=60s
