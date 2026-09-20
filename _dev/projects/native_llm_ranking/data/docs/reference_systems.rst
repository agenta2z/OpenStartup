===================================================
Reference Systems (Prior Art & Data Producers)
===================================================

.. contents::
   :local:
   :depth: 2

This chapter summarizes the **seven Meta LLM-RecSys systems** catalogued in the
entry-point reference *"RecSys LLM Systems — Codebase & Source Table Reference
(Verified)"* (GDoc ``10DAJgQxw6S26Ju3Jy0tOeN2ttiwxKoJBf1tO_VaXe-s``; a verbatim
copy is kept at ``references/RecSys LLM Systems — Codebase & Source Table
Reference.md``). Here we read that catalog **through a data-collection lens**:
each system is either a *producer* of data we can collect, a *consumer* whose
inputs tell us what a good user representation looks like, or both.

.. note::

   The source reference was compiled by parallel agents using code search +
   knowledge search + data-lineage tools, with unconfirmed items explicitly
   marked UNVERIFIED. The corrections it records (e.g. InterestFM's "87%" is
   *87% of Gemini 2.5 Pro performance*, not a detection rate; AdsLlama's
   "~145 QPS" is UNVERIFIED; POLARIS is *embedding* transfer, not soft-label
   distillation) are carried forward here. See :doc:`references`.


The seven systems at a glance
=============================

.. list-table::
   :header-rows: 1
   :widths: 14 30 26 30

   * - System
     - What it is
     - Owner / oncall
     - Role in data collection
   * - **ARS**
     - Agent-native recommender: LLM orchestrator + "Memory OS" + RecSys infra
       wrapped as tools
     - MRS Knowledge / ``rank_agent``
     - **Consumer + exemplar.** Its ingest (``datafm_adapter.py``) is our
       canonical online pattern; its memory model is our target profile schema
       (:doc:`data_model_user_profile`)
   * - **STAR** ("Dear Algo")
     - SilverTorch agentic retrieval + ranking (LangGraph/Llama+RAG) powering
       Threads "Dear Algo"
     - MRS SilverTorch + Threads / ``home_ml_platform``
     - **Producer.** Emits rich request/interaction logs
       (``instagram.star_dear_algo_reply``, ``threads_ranking_waterfall_events``)
   * - **Ember LLM Ranker**
     - LLM pointwise feed ranker for FB Groups / Forum app
     - Groups CEG Rec / ``groups_product_ranking``
     - **Producer + consumer.** Its ``llm_ranker_user_profile_input`` shows how a
       user is serialized *for* an LLM ranker
   * - **AdsLlama (SAGE)**
     - Multimodal content-understanding embedding model (Qwen3-VL-2B)
     - CU / ``megataxon``
     - **Producer (content).** Dense per-ad vision/text/fusion embeddings —
       content signal for the "content" pillar
   * - **InterestFM (IFM)**
     - LLaVA-style multimodal content FM → topics/entities/hashtags/sentiment/
       embeddings for organic FB/IG content
     - MRS Knowledge / ``ai_topic_understanding``
     - **Producer (content).** ``feed.interest_fm_api_logs_inc_archive`` and the
       CU cluster/SID enrichment traits in AUS
   * - **Biography**
     - LLM (Llama 3.x) that reasons over engagement history → free-form NL user
       profiles + RankLLM co-training
     - MRS Knowledge (User Knowledge) / ``ai_topic_understanding``
     - **Producer (the NL profile itself).** Directly emits the natural-language
       user representation we ultimately want — see
       :ref:`biography-as-profile`
   * - **POLARIS**
     - Ads Foundation embedding-transfer framework (OmniFM → Domain FM → VM)
     - Ads Foundation / ``scaling_user_ad_modeling``
     - **Consumer pattern.** Shows how precomputed foundation-model embeddings
       are shared as features (F3 ``ads.polaris.*``); less relevant to raw
       collection


Grouping by data role
======================

The seven fall into three data roles that map onto the paradigms in
:doc:`overview`:

* **Agentic / LLM rankers — event *producers*** (ARS, STAR, Ember). They log
  requests, scores, and rendered context; their logs are a rich source of
  labeled interactions and of *how a user is serialized for an LLM*.
* **Content / user understanding — signal *producers*** (AdsLlama/SAGE,
  InterestFM, Biography). They convert raw content and raw history into
  LLM-friendly signals: content embeddings, topic/entity labels, and — in
  Biography's case — the finished natural-language user profile.
* **Foundation transfer — feature *consumer*** (POLARIS). Precomputed embedding
  sharing; informs how collected signals get reused downstream, but is not a raw
  collection source.


.. _ars-as-exemplar:

ARS — the online-collection exemplar
====================================

ARS is the most important system for this project because **its ingest is our
online collection blueprint** and **its memory model is our target profile
schema**. Data-relevant facts (VERIFIED against code):

* Root: ``fbcode/mrs/rankevolve/ARS/`` (Memory OS at ``memory_os/``).
* **Reads:** DataFM AUS ``use_case_id=577`` via
  ``memory_os/nodes/ingest/datafm_adapter.py`` (ZippyDB, not Hive); Hive
  cold-start / cohort tables (e.g. ``feed_fblearner.*ars_cold_start_event*``,
  ``*generator_funnel_cohort_agg_daily``); ``groups.dim_group_fast`` for group
  name enrichment.
* **Writes:** ``EngagementSummaryMemory`` and profile/preference memories to
  ZippyDB (use-case 56862); per-user MezQL/Shots overrides to Laser; SFT
  datasets ``feed_fblearner.sft_preference_*/sft_profile_*``.
* **Serving flow:** ``WWW Watch Feed → refreshEngagementSummary (oneway Thrift)
  → DataFM → LLM summarize → ZippyDB``; a recsys planner then reads
  ``EngagementSummaryMemory`` and publishes overrides to Laser.

Full treatment in :doc:`online_collection_datafm_aus` (ingest) and
:doc:`data_model_user_profile` (memory model).


.. _biography-as-profile:

Biography — the NL user profile as a first-class artifact
=========================================================

Biography is the one system that **directly produces the natural-language user
profile** an LLM-native recommender wants, so its output tables are a shortcut
for the "profile" pillar (schemas VERIFIED — see :doc:`data_sources_catalog`):

* ``instagram.biography_prompts_inc_archive`` — the core inference log: the
  ``prompt`` fed to the LLM, the ``llm_output`` (the generated profile/interests),
  and inlined **UIH arrays** (``uih_object_ids``, ``uih_engagement_event_types``,
  ``uih_event_timestamps_ms``, ``uih_object_author_ids``, ``uih_apps``,
  ``uih_content_categories``). This single table shows *both* a finished NL
  profile *and* the exact historical-event encoding used to produce it — a
  strong template for our own profile builder.
* ``feed.biography_interests_for_meta_ai`` — parsed interests
  (``interests_array``) keyed by ``FamilyUID`` (IGID or FBID).
* ``instagram.ig_author_biography_prompt`` /
  ``instagram.threads_author_biography_prompt`` — per-app NL profile prompts.

.. tip::

   If your use case needs *a* user profile rather than a bespoke one, reading
   Biography output is far cheaper than regenerating it. If you need control over
   the schema/content, use Biography's ``uih_*`` encoding as a reference design
   and build from the raw sources in :doc:`data_sources_catalog`.
