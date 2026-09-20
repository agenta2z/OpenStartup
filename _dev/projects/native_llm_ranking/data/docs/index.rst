====================================================================
LLM-Native Recommendation — Data Collection
====================================================================

Formal project documentation for **how to collect the data needed to build
LLM-native recommendation systems** at Meta scale: a rich, natural-language-ready
representation of each user built from **profile metadata**, **historical events**
(authored posts / comments / replies / threads, plus interactions, impressions and
dwell), and the **content** those events touch.

This documentation was reverse-engineered and cross-verified from three concrete
production entry points (see :doc:`references`) and expanded outward into the
surrounding code, data lineage, and internal docs. It is meant to be read by data
engineers and modelers, and to be navigable both by humans and by agents.

.. note::

   **Verification discipline.** Every table, column, code path, and metric in
   this doc set is tagged **VERIFIED** (confirmed against production code, the
   Hive metastore, or an authoritative wiki) or **UNVERIFIED / TBD** (plausible
   but not confirmed at authoring time). Do not treat an UNVERIFIED item as
   ground truth — re-check in Daiquery / code search before relying on it. This
   mirrors the discipline of the source reference (:doc:`reference_systems`).

   Compiled 2026-07-15. IDs, retention windows, and table shapes drift — treat
   this as a living document.


The three entry points
======================

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Entry point
     - What it teaches about data collection
   * - **GDoc — "RecSys LLM Systems — Codebase & Source Table Reference"**
       (``docs.google.com/document/d/10DAJgQxw6S26Ju3Jy0tOeN2ttiwxKoJBf1tO_VaXe-s``)
     - The landscape of 7 Meta LLM-RecSys systems and the tables/stores each
       produces or consumes — i.e. *where the data already lives*. See
       :doc:`reference_systems`.
   * - **Code — ``ARS/memory_os/nodes/ingest/datafm_adapter.py``**
       (``internalfb.com/code/fbsource/fbcode/mrs/rankevolve/ARS/...``)
     - The canonical **online** collection pattern: read a user's engagement
       *sequence* from DataFM/AUS (ZippyDB), keyed by RID. See
       :doc:`online_collection_datafm_aus`.
   * - **Daiquery — ``queryid=909457732173156``**
       ("[MCP] IG typical users (cold/marginal/active) feed engagement + free text")
     - The canonical **offline** collection pattern: sample user cohorts from
       Hive and assemble interactions + free-text content. See
       :doc:`offline_collection_hive`.


How this documentation is organized
===================================

.. toctree::
   :maxdepth: 2
   :caption: Foundations

   overview
   reference_systems

.. toctree::
   :maxdepth: 2
   :caption: What to collect

   data_model_user_profile
   event_taxonomy

.. toctree::
   :maxdepth: 2
   :caption: Where the data lives

   data_sources_catalog
   identifiers_and_joins

.. toctree::
   :maxdepth: 2
   :caption: How to collect it

   online_collection_datafm_aus
   offline_collection_hive
   collection_playbook
   worked_example

.. toctree::
   :maxdepth: 2
   :caption: Guardrails & reference

   privacy_and_retention
   glossary
   references


Reading paths
=============

* **"I just need a dataset of users + their history + content."**
  Start with :doc:`overview`, then :doc:`offline_collection_hive` and the
  Recipe A/C sections of :doc:`collection_playbook`. Keep
  :doc:`identifiers_and_joins` and :doc:`privacy_and_retention` open.

* **"I'm building the online serving-time collector."**
  Read :doc:`online_collection_datafm_aus` end-to-end, then
  :doc:`data_model_user_profile` (the ARS memory model) and
  :doc:`identifiers_and_joins` (FBID→RID).

* **"I need the target profile schema to model against."**
  Read :doc:`data_model_user_profile` and :doc:`event_taxonomy`, backed by
  :doc:`data_sources_catalog`.

* **"Where does field X actually come from?"**
  Go straight to :doc:`data_sources_catalog` (the table inventory) and
  :doc:`identifiers_and_joins` (the join map).


Status legend
=============

The following markers are used consistently throughout:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Marker
     - Meaning
   * - ``VERIFIED``
     - Confirmed against production code, the Hive metastore (``meta`` CLI), a
       dataset definition file, or an authoritative wiki. Source cited.
   * - ``UNVERIFIED``
     - Named in a doc/comment but not confirmed against a primary source, or a
       value that could not be resolved with available tooling.
   * - ``TBD``
     - A deliberate open item to resolve before production use.
