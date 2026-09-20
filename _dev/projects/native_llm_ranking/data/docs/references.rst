==========
References
==========

.. contents::
   :local:
   :depth: 2

Provenance for this documentation set. Everything traces to one of the three
entry points below and the primary sources reached from them. Access notes are
included because they materially affect reproducibility.


The three entry points
======================

.. list-table::
   :header-rows: 1
   :widths: 30 44 26

   * - Entry point
     - URL / locator
     - Access (this env)
   * - GDoc — *RecSys LLM Systems — Codebase & Source Table Reference (Verified)*
     - ``docs.google.com/document/d/10DAJgQxw6S26Ju3Jy0tOeN2ttiwxKoJBf1tO_VaXe-s``
     - Live ``knowledge_load`` **fails**; full body via
       ``meta google.docs export --export-as=txt``; snippets via
       ``knowledge_filtered_search``. Verbatim copy kept at
       ``references/RecSys LLM Systems — Codebase & Source Table Reference.md``.
   * - Code — ``datafm_adapter.py``
     - ``internalfb.com/code/fbsource/fbcode/mrs/rankevolve/ARS/memory_os/nodes/ingest/datafm_adapter.py``
     - ``knowledge_load`` **works** for code URLs.
   * - Daiquery — IG typical users
     - ``internalfb.com/intern/daiquery/workspace/?queryid=909457732173156``
     - ``knowledge_load`` **works** (returns all cells).


Local reference artifacts (preserved in this repo)
==================================================

Verbatim copies of the three entry points are kept under ``references/`` for
provenance and offline use:

* ``references/RecSys LLM Systems — Codebase & Source Table Reference.md`` — the
  GDoc body (7-system reference).
* ``references/datafm_adapter.py`` — the online-ingest source file (analyzed in
  :doc:`online_collection_datafm_aus`).
* ``references/daiquery_909457732173156.sql`` — the offline query, all cells
  (analyzed and hardened in :doc:`offline_collection_hive`).

These are excluded from the Sphinx build; treat them as source snapshots and
re-fetch from the live locations above before relying on them.


Primary code sources (VERIFIED)
===============================

ARS Memory OS (``fbcode/mrs/rankevolve/ARS/``):

* ``memory_os/nodes/ingest/datafm_adapter.py`` — the online-ingest entry point.
* ``core/interfaces/datafm_adapter.py`` — ``DataFMAdapter`` Protocol.
* ``memory_os/workflows/engagement_summary.py`` — 7-use-case fan-out
  (``AUS_USE_CASES``), merge, ``_format_engagement``.
* ``memory_os/server/handler.py`` — ``refreshEngagementSummary``, ``addEvent``.
* ``memory_os/nodes/recsys/fbid_rid.py`` — FBID→RID resolver (Laser →
  ``RidBackfillService``).
* ``core/models/{memory,event_memory,preference_memory,profile_memory,engagement_summary_memory}.py``
  — the user-profile / memory data model.
* ``core/memory/{updater_types,preference_updater,profile_updater}.py`` — event
  types, thresholds, ``_PROFILE_SCHEMA``.
* ``production/memory_os/if/memory_service.thrift`` — wire schemas.

DataFM / AUS (``fbcode/multifeed/datafm/`` + configerator):

* ``tools/DataFMPyBind.cpp`` / ``tools/datafm_pybind.pyi`` — pybind API.
* ``configerator/structs/multifeed/aus/aus_reader.thrift`` — ``AusFetchMode``.
* ``configerator/structs/multifeed/aus/aus_common.thrift`` — ``AusDataType``,
  ``AusLists``.
* ``configerator/structs/multifeed/entrepot/v2/entrepot_unique_ids.thrift`` —
  ``hstu_v2_fb_public = 577`` (use-case registry).
* ``client/AusClient.cpp`` + ``utils/AusMerger.{h,cpp}`` + ``utils/TimeUtils.h``
  — BOTH-mode merge & compaction.
* ``model_context_protocol/python_servers/aus/AusUseCases.py`` — 577 trait
  catalog + config.

Trait catalogs & pipelines (``fbcode/dataswarm-pipelines/``):

* ``dataswarm_commons/mrs/datafm/models/{fb_trait_catalog,ig_trait_catalog,xlog_trait_catalog}.py``
* ``tasks/feed_fblearner/mrs/xlog/configs/{aus_pipeline_configs,enrichment_join_configs}.py``
* ``upm_data/datasets/hive/...`` — dataset definitions for every table in
  :doc:`data_sources_catalog` (e.g. ``instagram/dim_instagram_media_v2_unrestricted.py``,
  ``instagram/dim_instagram_comment_v2.py``, ``instagram/dim_threads_media.py``,
  ``bi/dim_all_users.py``, ``feed/fct_feed_interactions.py``, ...).

Origin diff:

* **D104460408** — *"[ARS] Switch DataFMPybindAdapter to
  multi_fetch_datafm_feature for full AUS history"* — produced the ingest
  behavior documented in :doc:`online_collection_datafm_aus`.


Primary docs / wikis (VERIFIED)
===============================

* DataFM system wiki —
  ``internalfb.com/wiki/Benrhodeland/MRS_Wiki/Systems/Datafm/``
* AUS_LIST vs AUS_ROW —
  ``internalfb.com/wiki/Multifeed/.../DataFM/DataFM_Developers_Guide_0/DataFM_Data_Representations/``
* Serving reliability (immutable/mutable ↔ AUS_LIST/ROW) —
  ``internalfb.com/wiki/Multifeed/.../DataFM/Runbook/Serving_Reliability/``
* RID definition —
  ``internalfb.com/wiki/Privacy/User_Data/.../Hive_Anonymization/Mapping_User-Identifying_IDs_to_RIDs/``
* ARS announcement / Memory OS —
  ``fb.workplace.com/groups/228479108798071/permalink/1486772432968726/``
* MRS DS Context / knowledge —
  ``internalfb.com/wiki/MRS_DS_Context/domains/knowledge/``
* The 7-system reference (verbatim copy) —
  ``references/RecSys LLM Systems — Codebase & Source Table Reference.md``


Verification metadata
=====================

* **Metastore verification** of every Daiquery/catalog table used the ``meta``
  CLI (``hive.table schema``/``metadata``, ``hive.column metadata``,
  ``hive.table partitions``) and ``meta wut``/``whatisthis`` for semantics
  (VPVD, entity type of the queryid).
* **Known discrepancies** carried forward (see per-page warnings): DataFM
  acronym variants; ``dim_ig_all_public_media_caption_hashtag`` retention
  (25d vs 45d) and its **paused** upstream; impression "~800 TB/day" size
  (UNVERIFIED); ``datafm_pybind.pyi`` stub inaccuracies; ``AusClientCLI.cpp``
  fetch-mode mislabel; AUS per-use-case ``xlog_traits`` allowlist lives in
  configerator (not read here).
* **Corrections** inherited from the source reference: InterestFM "87%" =
  *87% of Gemini 2.5 Pro performance* (not a detection rate); AdsLlama
  "~145 QPS" UNVERIFIED; POLARIS is embedding transfer (not soft-label
  distillation); Biography "+1.235% time spent" not found (actual figures
  differ).

.. note::

   Compiled 2026-07-15. This set was authored by cross-verifying the three entry
   points against production code, the Hive metastore, and internal wikis; items
   that could not be confirmed are marked UNVERIFIED throughout. Re-verify before
   production use.
