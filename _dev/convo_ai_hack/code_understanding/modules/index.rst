.. _module-catalog:

============================================================
Module catalog (85 modules)
============================================================

Per-module deep-dive documentation for every Gradle module in conversational-ai-platform.

Each module page documents:

* **Path, size, importance tier** (header)
* **Top files by line count** (verified by ``wc -l``)
* **Key public contracts / Spring components**
* **Notable findings** (god-classes, anti-patterns, interesting design)
* For ``-impl`` modules: **What you would change here / what you would NOT change here**

Tiers
=======

.. toctree::
   :maxdepth: 1

   foundation/index
   platform/index
   product/index
   service/index
   contrib/index

Module sizing
=================

The 5 largest modules in the codebase:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Module
     - LoC
     - Why so large
   * - ``platform/client/client-api``
     - **45,005**
     - Atlassian REST/GraphQL DTOs (machine-generated)
   * - ``platform/evaluation/evaluation-impl``
     - 26,625
     - Batch eval is genuinely complex
   * - ``product/rovo/rovo-extras-impl``
     - 20,992
     - Avatar gen, insights, evaluation strategy
   * - ``product/aifeature/aifeature-api``
     - 14,658
     - Whiteboard / editor / content models
   * - ``platform/base/base-api``
     - 13,271
     - Cross-cutting vocabulary, feature flags

The 3 smallest modules:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Module
     - LoC
     - Purpose
   * - ``product/shared-features/shared-features-api``
     - **16**
     - Shared feature flag enum
   * - ``platform/action/action-spi``
     - 13
     - Single SPI interface
   * - ``platform/knowledge-gap/knowledge-gap-spi``
     - 44
     - Mix of sharded + global ERS clients
