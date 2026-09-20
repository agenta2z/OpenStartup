.. _mod-pii-anonymization:

====================
PII Anonymization Experiment
====================

:File: ``responsible-ai/experiments/PII_Anonymization/PII_Anonymization.py`` (~80 LoC)
:Status: **Research/experimental — not in production moderation pipeline**

Overview
=========

PII Anonymization explores using Microsoft Presidio + HuggingFace transformer
models for detecting and anonymizing personally identifiable information in text.
This complements the PII harm category in the main content moderation pipeline
(which detects PII presence but does not anonymize it).

Technology stack
=================

* **presidio-analyzer** — NLP-based PII entity detection engine
* **presidio-anonymizer** — Text anonymization using detected entities
* **Custom ``HFTransformersRecognizer``** — extends ``EntityRecognizer`` to use
  HuggingFace token-classification models (BERT-based NER)
* **Label mapping**: NER labels → Presidio entity types:

  .. code-block:: python

     {
       "PER": "PERSON",
       "LOC": "LOCATION",
       "ORG": "ORGANIZATION"
     }

Supported entity types (12)
==============================

.. code-block:: python

   DEFAULT_ANONYM_ENTITIES = [
       "CREDIT_CARD",      "CRYPTO",         "DATE_TIME",
       "EMAIL_ADDRESS",    "IBAN_CODE",      "IP_ADDRESS",
       "NRP",              "LOCATION",       "PERSON",
       "PHONE_NUMBER",     "MEDICAL_LICENSE","URL",
       "ORGANIZATION"
   ]

Core function
==============

.. code-block:: python

   def anonymize_text(data: dict, analyzer: AnalyzerEngine) -> dict:
       sentences = data.get("inputs")
       entities = data.get("parameters", {}).get("entities", DEFAULT_ANONYM_ENTITIES)
       should_anonymize = data.get("parameters", {}).get("anonymize", False)

       results = analyzer.analyze(text=sentences, entities=entities, language="en")

       if should_anonymize:
           anonymized = anonymizer.anonymize(text=sentences, analyzer_results=results)
           return {"anonymized": anonymized.text}
       else:
           return {"found": [entity.to_dict() for entity in results]}

The ``anonymize`` parameter controls whether to:

* ``False`` (default): Return detected entities with positions and confidence scores
* ``True``: Return text with PII replaced by ``<ENTITY_TYPE>`` placeholders

Relationship to main moderation pipeline
==========================================

The main moderation pipeline (``PromptModerationService``) detects the ``PII``
harm category and returns DISALLOWED — it **does not** anonymize the content.
This PII Anonymization experiment explores whether anonymization could be offered
as an alternative to blocking, allowing AI features to process content with PII
stripped out rather than rejecting it entirely.
