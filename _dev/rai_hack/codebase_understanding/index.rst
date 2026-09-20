.. _rai-code-understanding:

=============================================================================
Responsible AI — Joint Codebase Understanding Documentation
=============================================================================

Comprehensive documentation for **two related repositories** that together form
Atlassian's Responsible AI moderation platform:

* ``responsible-ai-api`` — The **production Flask service** receiving REST
  requests and running content moderation inference.
* ``responsible-ai`` — The **research/ML monorepo** for harm taxonomy, dataset
  infrastructure, model training, offline/online evaluation, and model deployment.

**Verified scope** (2026-05-04):

* ``responsible-ai-api``: **94 Python source files**, **5,272 source LoC**, ~40+ test files
* ``responsible-ai``: Pants-based monorepo; packages + notebooks + experiments + msp_deploy + analytics
* Both repos: **Python 3.12**, uv/Pants dependency management, Atlassian Micros deployment

How to read this documentation
=================================

* **Brand new to RAI?** Start with :doc:`overviews/02-architectural-narrative` (walking tour).
* **Need the cross-system picture?** :doc:`overviews/01-multi-axis-matrix` has tier × size tables.
* **SRE / on-call?** :doc:`overviews/03-criticality-dashboard` has blast-radius rankings.
* **Architecture deep dive?** :doc:`architecture/index` covers request lifecycle, inference, auth, feature flags.
* **Per-module detail?** :doc:`modules/index` has deep-dives for every module in both repos.

.. note::

   All numerical claims (LoC, file counts) are verified by ``find`` + ``wc -l`` on the actual
   source trees. Investigation conducted 2026-05-04 via 4 parallel subagents + direct file reads
   of all 94 source files.

Top-level structure
======================

.. toctree::
   :maxdepth: 2
   :caption: Cross-cutting overviews

   overviews/index

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/index

.. toctree::
   :maxdepth: 2
   :caption: Per-module catalog

   modules/index

.. toctree::
   :maxdepth: 2
   :caption: Development history & decision provenance

   history/index

Quick statistics
==================

.. list-table::
   :header-rows: 1
   :widths: 30 12 12 46

   * - Repo / Layer
     - Files
     - LoC
     - Notes
   * - **rai-api** API + routing
     - 12
     - ~700
     - Flask blueprints, controllers, Pydantic schemas, ETag, debug trace
   * - **rai-api** Inference models
     - 12
     - ~1,680
     - LLaMA, GPT-OSS, SageMaker, Triton gRPC/OpenAI, shadowing, confidence
   * - **rai-api** Service / moderation
     - 20
     - ~1,200
     - 4 moderation pipelines, harm categories, stream processor, URL checker
   * - **rai-api** Observability
     - 12
     - ~700
     - Prometheus metrics, GASv3 analytics events, structured logging
   * - **rai-api** Support modules
     - 38
     - ~900
     - Config, slauth, tenant context, Statsig, cache, anti-abuse, ML platform
   * - **rai-api TOTAL**
     - **94**
     - **~5,272**
     -
   * - **responsible-ai** harm_taxonomy
     - 1
     - ~50
     - 16-category HarmCategory Enum
   * - **responsible-ai** notebooks/data
     - 6
     - ~400
     - Pandera schema, multi-source ingestion, sampling
   * - **responsible-ai** notebooks/evaluation
     - 10
     - ~700
     - Offline eval + online LLM judge workflow
   * - **responsible-ai** experiments
     - ~11
     - ~680
     - Image moderation v1 (ShieldGemma2), PII anonymization
   * - **responsible-ai** msp_deploy
     - 4
     - ~200
     - MSP compliant model registration
   * - **responsible-ai** analytics/terraform
     - ~10
     - ~300
     - Livegraph dashboard Terraform IaC
   * - **responsible-ai TOTAL**
     - ~42
     - ~2,330
     -


.. toctree::
   :maxdepth: 1
   :caption: Business & Technical Goals

   architecture/cross-cutting/07-business-and-technical-goals

Documentation provenance
==========================

Generated 2026-05-04 via multi-agent parallel investigation (4 subagents) of the live source trees
plus direct file reads of all 94 ``responsible-ai-api`` source files and ~42 ``responsible-ai`` files.
Every numerical claim cross-verified against ``find + wc -l`` output.
