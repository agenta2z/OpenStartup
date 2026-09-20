.. _mod-llm-models-api:

==============================================
``foundation/llm-models/llm-models-api``
==============================================

:Tier: foundation
:Path: ``modules/foundation/llm-models/llm-models-api``
:Importance: **Tier 2 — DTOs**

Unified LLM request/response data classes used across providers.

Dependencies :sup:`(verified)`
================================

* Lombok (POJOs)
* Jackson Annotation + Databind

Patterns
==========

1. **Lombok for POJOs.** Reduces boilerplate.
2. **No convo-ai deps.** Pure data definitions.

What you would change here
============================

* Add a new field to LLM request/response → here

