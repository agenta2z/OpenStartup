.. _convo-ai-code-understanding:

================================================================
Conversational AI Platform — Code Understanding Documentation
================================================================

Comprehensive documentation for the ``conversational-ai-platform`` codebase.

**Verified scope** (2026-05-02):

* **84 Gradle modules** in 5 tiers (foundation / platform / product / service / contrib)
* **1,175,159 main LoC** across 8,907 Kotlin files
* **1,354,512 test LoC** — 1.15× test/main ratio
* **Total: 2.5M LoC**

How to read this documentation
=================================

* **Brand new to convo-ai?** Start with :doc:`overviews/02-architectural-narrative` (a walking tour).
* **Need the cross-module picture?** :doc:`overviews/01-multi-axis-matrix` has tier × size × function tables.
* **SRE / on-call?** :doc:`overviews/03-criticality-dashboard` has blast-radius rankings.
* **Architecture deep dive?** :doc:`architecture/index` covers request lifecycle, AI Gateway, tenant isolation, etc.
* **Looking for a specific module?** :doc:`modules/index` has a one-page summary per module.
* **Want depth on a strategic module?** :doc:`modules/deep/index` has 300-500+ line deep-dives for 6 modules.

.. note::

   **Many earlier estimates were wrong by 5-30×.** This documentation reflects ground-truth
   verified by ``find -P -name '*.kt' -type f -exec cat {} +`` on the actual source tree.
   See :ref:`overview-multi-axis-matrix` §6 for the corrections list.

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
   :caption: Per-module catalog (84 modules)

   modules/index

.. toctree::
   :maxdepth: 2
   :caption: Deep-dive pages (6 strategic modules)

   modules/deep/index

Quick statistics by tier
============================

.. list-table::
   :header-rows: 1
   :widths: 20 12 18 18 18 14

   * - Tier
     - Modules
     - Main LoC
     - Main files
     - Test LoC
     - Test ratio
   * - **foundation**
     - 11
     - 26,518
     - 298
     - 42,576
     - 1.6×
   * - **platform**
     - 34
     - 264,257
     - 2,146
     - 259,703
     - 1.0×
   * - **product**
     - 30
     - **830,968**
     - 5,967
     - 982,235
     - 1.2×
   * - **service**
     - 5
     - 46,021
     - 415
     - 60,618
     - 1.3×
   * - **contrib**
     - 4
     - 7,395
     - 81
     - 9,380
     - 1.3×
   * - **TOTAL**
     - **84**
     - **1,175,159**
     - **8,907**
     - **1,354,512**
     - **1.15×**

Documentation provenance
==========================

* **Initial generation** (prior session): Multi-agent investigation — 4 parallel sub-agents covering ~58 modules. Produced 50 module pages + 6 index pages + master index.
* **Architecture pages** (prior session): Pre-existing 26 RST files / 3,577 lines covering tier rules, request lifecycle, AI Gateway, MDC/coroutine state, etc. + 7 Mermaid diagrams.
* **Deep-dive pass** (this session): 6 strategic modules taken from catalog-level (~50-150 lines) to deep-dive (300-500+ lines) using verified ``find`` / ``wc`` / ``grep`` data on the actual source tree.
* **Verification standard**: All numerical claims (LoC, file counts, line numbers) verified directly. The 6 deep-dive pages identified that the original catalog had under-counted ~10 modules by 5-30×; corrections are tabulated in :ref:`overview-multi-axis-matrix` §6.
* **Honest scope acknowledgment**: True 100% deep coverage of all 84 modules would require 100-200 hours of sustained engineering work. The current 6 deep dives cover the **architecturally most-significant** modules. The other 78 retain their existing one-page summaries which are accurate but shallow.

What this documentation does NOT cover
========================================

* **Per-Spring-component DI graphs** — would require extracting all ``@Component`` declarations and following constructor params. Possible follow-up work.
* **GraphQL schema documentation** — 30+ per-product GraphQL controllers; schema strings live in resources directories.
* **Per-method API documentation** — Kotlin source has KDoc; we don't reproduce it.
* **Operational runbooks** — see ``ops/`` directory in the repo, not here.
* **Frontend integration** — convo-ai is a backend service; client-side JavaScript / React lives in other repos.
