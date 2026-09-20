.. _mod-gpt-oss-model:

=====================
GPT-OSS Inference Model
=====================

:File: ``src/inference_models/rai_gpt_oss.py`` (287 LoC)
:Importance: **P1 — alternate prompt moderation + agent safety backend**

Overview
=========

``rai_gpt_oss.py`` implements inference for the GPT-OSS Safeguard 20B model
served via Atlassian's Teamserve HTTP endpoint using an OpenAI-compatible API.
This is an alternative to the LLaMA RAI FT model for prompt moderation, and
is also used directly for agent moderation.

Model identity
===============

* **Model name**: ``gpt-oss-safeguard-20b``
* **Model tag**: ``RAI-OSS-20B-nothinking-0211-2026-v5-compliant``
* **Endpoint**: Teamserve HTTP ``/v1/chat/completions``
* **Interface**: OpenAI chat completions API format
* **Context**: Used when ``is_gpt_oss_safeguard_enabled()`` flag is on

Classes
========

``RAIFTTeamserveEndpoint(ModelEndpoint)`` — Teamserve HTTP endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Uses ``TritonOpenAIClient`` (``triton_openai_api_client.py``)
* HTTP POST to ``config.teamserve_gptoss_endpoint``
* Sends: ``{"messages": [{role, content}, ...], "model": model_name}``
* Auth: ASAP JWT Bearer token via ``config.asap_signer``
* Timeout: 6s (``TritonOpenAIClient`` default)
* Circuit breaker: ``pybreaker.CircuitBreaker(fail_max=30)``

``GPTOSSModelInTeamserve(InferenceModel)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``run_inference(input: str, params: GPTOSSEndpointParameters) -> InferenceResult``
* Builds chat messages:

  .. code-block:: python

     messages = [
         {"role": "system", "content": ETHICAL_FILTER_PROMPT_GPT_OSS_SAFEGUARD},
         {"role": "user",   "content": input}
     ]

* Calls ``TritonOpenAIClient.send_chat_completions(messages)``
* Parses response: ``choices[0].message.content`` → JSON extract ``{category, toBeFiltered}``
* Returns ``InferenceResult(result=ModerationResult(...), model_evaluation_version="gpt_oss_safeguard_20b", ...)`

Prompt template (``ETHICAL_FILTER_PROMPT_GPT_OSS_SAFEGUARD``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

System prompt used for GPT-OSS moderation:

* Defines all harm categories with descriptions
* Requests JSON response format: ``{"category": "...", "toBeFiltered": true/false}``
* More structured than LLaMA template (no log-probs needed — uses greedy decoding)
* Does **not** use Jinja2 templating (inline Python string)

``TritonOpenAIClient`` (``triton_openai_api_client.py``, 36 LoC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thin HTTP wrapper for Triton's OpenAI-compatible API:

.. code-block:: python

   def send_chat_completions(self, messages: List[dict]) -> dict:
       response = httpx.post(
           self.endpoint,
           json={"messages": messages, "model": self.model_name},
           headers={"Authorization": f"Bearer {asap_token}"},
           timeout=6.0,
       )
       response.raise_for_status()
       return response.json()

Circuit breaker wraps the HTTP call at ``fail_max=30``.

Difference from LLaMA backend
================================

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - LLaMA (RAI FT)
     - GPT-OSS Safeguard
   * - Transport
     - gRPC (Triton tensors) or MSP HTTP
     - HTTP (OpenAI chat format)
   * - Tokenization
     - Explicit (HF tokenizer, overflow tracking)
     - Implicit (model handles it)
   * - Response
     - Log-probs + generated text
     - Generated text only (JSON)
   * - Violation score
     - From log-probs histogram (0.0–1.0)
     - From ``toBeFiltered`` bool + JSON parse
   * - Template
     - Jinja2 (versioned)
     - Inline Python string constant
   * - Timeout
     - 5s gRPC / 2s MSP read
     - 6s HTTP
