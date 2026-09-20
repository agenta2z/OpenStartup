.. _mod-schemas-and-validation:

=============================
Schemas & Validation
=============================

:Files: ``src/api/v1/moderation/schema/``
:Importance: **P1 — contract enforcement**

Overview
=========

All request and response bodies are Pydantic v2 models with ``strict=True``
and ``extra="forbid"``. ``flask-pydantic`` handles validation automatically
via the ``@validate()`` decorator.

Common validation patterns
===========================

All request models use:

.. code-block:: python

   model_config = ConfigDict(extra="forbid", strict=True)

* ``extra="forbid"`` — unknown fields → 422 error (no silently ignored fields)
* ``strict=True`` — no type coercion (``"1"`` ≠ ``1``, ``True`` ≠ ``1``)

All response models also exclude internal fields from serialization:

.. code-block:: python

   violation_score: Optional[float] = Field(exclude=True)
   model_evaluation_version: str = Field(exclude=True)

These fields go to response headers, not body.

``DebugOptions`` and ``DebugTrace``
=====================================

Shared across prompt and agent moderation:

**DebugOptions** (request):

.. code-block:: python

   class DebugOptions(BaseModel):
       verbose: bool = Field(default=False)
       feature_overrides: Optional[dict[str, bool]] = Field(default=None)

**DebugTrace** (response, when verbose=True):

.. code-block:: python

   class DebugTrace(BaseModel):
       service_version: Optional[str]      # deployed version
       environment: Optional[str]          # dev/staging/prod/local
       model_evaluation_version: Optional[str]
       prompt_evaluation_version: Optional[str]
       model_id: Optional[str]             # e.g. "rai-ft-content-filter-v2-3-3"
       error_detail: Optional[str]         # "ExcType: msg | caused by CauseType: cause"
       error_type: Optional[str]           # "AIGATEWAY_TIMEOUT", etc.
       gateway_endpoint: Optional[str]     # upstream endpoint URL
       extra: Optional[dict[str, Any]]     # {"feature_overrides_applied": {...}}

All fields optional — trace is populated on best-effort basis even in error paths.

Prompt schemas (``schema/moderate_prompt.py``)
================================================

Request: ``ModeratePromptRequest(prompt: str[≥1], debug: Optional[DebugOptions])``
Response: ``ModeratePromptResponse(status: ALLOWED|DISALLOWED, harm_category: str, trace?)``

Output schemas (``schema/moderate_output.py``)
================================================

Request: ``ModerateOutputRequest(current_chunk: str[≥0], stream_id: str[1-255], chunk_index: int[≥0]=0)``
Response: ``ModerateOutputResponse(status, stream_id, chunk_index?, harm_category?, content: str[≥0], external_urls?)``

Agent schemas (``schema/moderate_agent.py``)
==============================================

Request: ``ModerateAgentRequest(name, description?, prompt, conversation_starters?, follow_up_prompt?, debug?)``
Sub-model: ``AgentConversationStarters(text: str)``
Response: ``ModerateAgentResponse(status, harm_category: AgentHarmCategory, trace?)``

Image schemas (``schema/moderate_image.py``)
=============================================

Request: ``ModerateImageRequest(image_data: str, type: ImageType.BASE64, format?, file_id?, container_id?, user_id?, region?, platform?)``

* Extends ``AntiAbuseOptionalFields`` (``antiabuse/models.py``) — adds file_id, container_id, user_id, region, platform
* ``@model_validator(mode="after")``: validates ``image_data`` non-empty

Response V0: ``ModerateImageResponse(status, harm_category: ImageHarmCategory)``
Response V1: ``ModerateImageResponseV1(status, harm_category, abhorrent_material: bool=False, actions: {deletion: bool}=False, comment?)``

Validation error handling (``app.py``)
=======================================

``@app.errorhandler(ValidationError)`` (flask-pydantic):

Iterates over all param types (body/form/path/query), collects Pydantic
``ValidationError`` objects per type, logs warnings, returns:

.. code-block:: json

   {
     "validation_error": {
       "body_params": [{"loc": ["prompt"], "msg": "...", "type": "..."}]
     }
   }

HTTP 400 status. ``include_url=False, include_input=False`` for security
(don't echo back user input in validation error messages).
