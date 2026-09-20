.. _mod-harm-taxonomy:

================
Harm Taxonomy
================

:File: ``responsible-ai/packages/rai/harm_taxonomy/harm_category.py`` (~50 LoC)
:Importance: **P0 — canonical shared taxonomy for all evaluation**

Overview
=========

The ``HarmCategory`` enum is the **single source of truth** for harm category
definitions across both ``responsible-ai`` (research/eval) and
``responsible-ai-api`` (production API). It contains 16 values.

The full taxonomy
==================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Category
     - Description
   * - ``VIOLENCE_HARASSMENT``
     - Content promoting, threatening, or depicting physical harm to people
   * - ``HATE_DISCRIMINATION``
     - Content targeting groups based on protected characteristics
   * - ``MISINFORMATION``
     - False or misleading information presented as fact
   * - ``SEXUAL_CONTENT``
     - Explicit or non-consensual sexual content
   * - ``ILLEGAL_ACTIVITY``
     - Instructions for or promotion of criminal activity
   * - ``SELF_HARM``
     - Content that encourages or provides instructions for self-harm
   * - ``JAILBREAK_PROMPT_INJECTION``
     - Attempts to bypass AI safety systems
   * - ``INTELLECTUAL_PROPERTY``
     - Copyright infringement or IP theft
   * - ``COPYRIGHT``
     - Specific copyright violations (sometimes merged with INTELLECTUAL_PROPERTY)
   * - ``PERSONALLY_IDENTIFIABLE_INFORMATION``
     - PII exposure (names, SSNs, addresses, etc.)
   * - ``POLITICS``
     - Political content that may be inappropriate in work context
   * - ``PROFANITY``
     - Offensive language (prompt moderation only, not agent)
   * - ``IMPERSONATION``
     - Pretending to be another person or entity
   * - ``HIGH_RISK_DECISIONS``
     - Advice on high-stakes decisions (medical, legal, financial) without disclaimer
   * - ``SPECIALIST_ADVICE``
     - Professional advice requiring licensed expertise
   * - ``NONE``
     - No harm detected (safe content)
   * - ``UNKNOWN``
     - Unrecognized category (model returned unexpected value)

Class interface
================

.. code-block:: python

   class HarmCategory(Enum):
       VIOLENCE_HARASSMENT = "Violence/Harassment"
       ...

       @property
       def slug(self) -> str:
           """Lowercase underscore name. E.g. 'violence_harassment'"""
           return self.name.lower()

       @property
       def friendly_name(self) -> str:
           """Display-friendly string. E.g. 'Violence/Harassment'"""
           return self.value

       @classmethod
       def from_slug(cls, slug: str) -> "HarmCategory":
           """Parse from lowercase underscore format."""
           for member in cls:
               if member.slug == slug.lower():
                   return member
           return cls.UNKNOWN

       @classmethod
       def _missing_(cls, value):
           """Returns NONE for None input; UNKNOWN for unrecognized string."""
           if value is None:
               return cls.NONE
           return cls.UNKNOWN

Relationship to API categories
================================

The production API uses separate enums per moderation type
(``PromptHarmCategory``, ``AgentHarmCategory``, ``ImageHarmCategory``), but
they are **derived from** and **consistent with** this canonical taxonomy.

Key differences from API enums:

* ``responsible-ai`` uses ``PERSONALLY_IDENTIFIABLE_INFORMATION`` (full name)
  vs API uses ``PII`` (abbreviation)
* Agent moderation adds ``EROTIC_CHATBOTS`` (not in base taxonomy)
* Agent moderation omits ``PROFANITY``
* Image moderation adds ``HUMAN`` (physical content detection)

Build integration (``BUILD`` file)
====================================

The harm taxonomy package is a Pants-managed Python library:

.. code-block:: python

   python_library(
       name="harm_taxonomy",
       sources=["*.py"],
       dependencies=[],
   )

This allows other Pants targets in ``responsible-ai`` to depend on it:
``"packages/rai/harm_taxonomy"`` dependency in dataset and evaluation BUILD files.
