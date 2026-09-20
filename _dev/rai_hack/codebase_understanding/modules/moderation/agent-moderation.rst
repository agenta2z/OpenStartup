.. _mod-agent-moderation:

====================
Agent Moderation
====================

:Files: ``src/service/moderation/agent/agent_moderation.py``, ``src/api/v1/moderation/agent_moderation_controller.py``
:Importance: **P1 — Rovo/AgentStudio safety gate**

Purpose
========

Screens entire agent configurations (name, description, system prompt, conversation
starters, follow-up prompts) against 15 harm categories using an LLM-as-judge
approach. Called when users create or modify agents in AgentStudio/Rovo.

API contract
=============

**Request** (``ModerateAgentRequest``):

.. code-block:: json

   {
     "name": "My Agent",
     "description": "optional description",
     "prompt": "You are a helpful assistant...",
     "conversation_starters": [{"text": "How do I..."}],
     "follow_up_prompt": "optional follow-up",
     "debug": {"verbose": false, "feature_overrides": {}}
   }

**Response** (``ModerateAgentResponse``):

.. code-block:: json

   {
     "status": "ALLOWED | DISALLOWED",
     "harm_category": "none | erotic_chatbots | violence_harassment | ..."
   }

Response headers: ``X-RAI-Model-Evaluation-Version``, ``X-RAI-Prompt-Evaluation-Version``.

Harm categories (``AgentHarmCategory``)
=========================================

15 categories (StrEnum). Notable differences from ``PromptHarmCategory``:

* **Includes**: ``EROTIC_CHATBOTS`` (not in prompt moderation)
* **Excludes**: ``PROFANITY`` (not screened for agents)
* **Deprecated aliases** (``_missing_()`` handles legacy values):

  .. list-table::
     :header-rows: 1
     :widths: 40 60

     * - Deprecated value
       - Maps to
     * - ``hate_speech``
       - ``HATE_DISCRIMINATION``
     * - ``harassment``
       - ``VIOLENCE_HARASSMENT``
     * - ``violence``
       - ``VIOLENCE_HARASSMENT``

* Case-insensitive + substring matching in ``_missing_()``.

Model selection by cloud_id
=============================

``_get_moderation_config(cloud_id: str) -> AgentModerationVersionConfig``:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Feature flag
     - Config version
     - Model
   * - Default
     - V2.3
     - gpt-4o or gpt-4-turbo-mini (AI Gateway Raw)
   * - ``is_agent_moderation_v2_3_1_enabled()``
     - V2.3.1
     - Same model, updated prompt template
   * - ``is_agent_moderation_v3_enabled()``
     - V3
     - gpt-4o (latest), V3 prompt template

``AgentModerationVersionConfig`` fields:

* ``prompt_template: PromptTemplate`` — Jinja2 template for system + user messages
* ``model_config: ModelConfig`` — model name, temperature, max_tokens
* ``evaluation_version: str`` — used in response headers + GASv3 events

Inference path
===============

Direct AI Gateway ``Raw`` client call (not MSP/Teamserve):

.. code-block:: python

   messages = [
       {"role": "system", "content": "You are a content moderation expert..."},
       {"role": "user",   "content": render_template(name, description, prompt, ...)}
   ]
   response = ai_gateway_raw_client.chat_completions(messages, model_config)

Response parsing: multi-stage JSON extraction of
``{harm_category: str, toBeFiltered: bool, violation_score: float}``.

Error handling:

* ``AIGatewayCommsError`` → logs + returns NONE (fail-open)
* ``MalformedModelOutputError`` → logs warning + returns UNKNOWN
* ``NoCompletionsReturnedError`` → logs error + returns UNKNOWN

Analytics emitted
==================

``AgentEvaluatedEvent``: cloud_id, user_id, use_case_id, slauth_principal,
evaluation_version, detected_harm_category, outcome, violation_score.
