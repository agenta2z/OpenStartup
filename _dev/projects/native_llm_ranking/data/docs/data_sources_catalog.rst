=====================
Data Sources Catalog
=====================

.. contents::
   :local:
   :depth: 2

The verified inventory of tables and stores for collecting user profiles +
historical events + content. Organized by role. Unless marked **UNVERIFIED**,
every table below was confirmed against its Hive **dataset definition file**
(``fbcode/dataswarm-pipelines/upm_data/datasets/hive/<ns>/<table>.py``), the Hive
**metastore** (``meta`` CLI), or a code read. Join keys are detailed in
:doc:`identifiers_and_joins`; retention nuances in :doc:`privacy_and_retention`.

.. note::

   Hive catalog URLs follow ``https://www.internalfb.com/data/tables/<namespace>/<table>``.
   The ``namespace.table`` identity is verified; re-check exact schemas in
   Daiquery before a production run, as columns/retention drift.


Profile & identity
==================

.. list-table::
   :header-rows: 1
   :widths: 30 12 20 38

   * - Table
     - Status
     - Owner · Retention · Partitions
     - Key columns (collection-relevant)
   * - ``instagram.dim_ig_users``
     - VERIFIED
     - ``ig_home_eco_de`` · ∞ · ``ds``/``isactivated``
     - ``userid`` (IGID), ``reg_ds``, ``interface_l28``/``interface_l7``
       (``map<string,bigint>`` = # DAU-days in last 28/7 on the interface),
       ``username``, ``gender``, ``country``, ``is_private``, ``account_tiers``,
       ``is_creator_account``, ``is_business_profile``, ``is_ai_agent``,
       ``stated_age`` (~55 cols total)
   * - ``bi.dim_all_users``
     - VERIFIED
     - ``dau_pipeline`` · ∞ · ``ds``/``isactivated``/``isdeleted``/
       ``is{1,7,28,30}dayactive``
     - ``userid`` (FBProfileID), ``rid``, ``name``/``firstname``/``lastname``,
       ``gender``, ``dob_*``, ``age``, ``country``, ``locale``,
       ``friend_count``, ``subscriber_count``, ``user_type`` — *the* canonical
       FB user dim
   * - ``ffdp.dim_family_fb_ig_user``
     - VERIFIED
     - (cross-app) · 30d · ``ds``/``version``
     - ``ff_sk`` (family key), ``fb_ids: Array<FBAccountID>``,
       ``ig_ids: Array<UserIGID>`` — FB↔IG account soft-match
   * - ``privacy.dim_ig_fbid_to_rid`` (→ ``..._unpublished``)
     - VERIFIED
     - ``dftr_pipeline`` · 45d · ``ds``
     - ``fbid: IG_FBID_V2`` ↔ ``rid: InstagramV2RID`` (IG FBID↔RID daily map)
   * - ``instagram.dim_instagram_media_igid_to_fbid``
     - VERIFIED
     - ``ig_bizrex_bex_de`` · 16d · ``ds``
     - ``ig_id: MediaIGID`` ↔ ``fbid: MediaFBIDV2`` + author
       ``user_id``/``user_rid``/``user_igid`` — media id-space bridge


Authored content (user as creator)
==================================

.. list-table::
   :header-rows: 1
   :widths: 30 12 20 38

   * - Table
     - Status
     - Owner · Retention · Partitions
     - Key columns
   * - ``instagram.dim_instagram_media_v2_unrestricted``
     - VERIFIED
     - ``ig_rc_de`` · 7d · ``ds``
     - ``fbid`` (media FBID / post_fbid), ``ig_id`` (client ig_media_id),
       ``user_id: IG_FBID_V2`` (author), ``createtime``/``taken_at``,
       ``media_type``, ``product_type`` (FEED/STORY/IGTV/CLIPS),
       ``custom_accessibility_caption``, ``num_likes``/``num_comments``/
       ``num_reposts``
   * - ``instagram.dim_instagram_media_v2_unrestricted_partitioned``
     - VERIFIED
     - ``ig_creation_de`` · 7d · ``ds``/``product_type``/``media_type``/
       ``app_family``
     - same rows + ``user_rid`` prejoined; easier/cheaper to filter by media type
   * - ``instagram.dim_instagram_comment_v2``
     - VERIFIED
     - WWW · 3d · ``ds``
     - ``fbid`` (comment), ``user_id: IG_FBID_V2`` (commenter),
       ``media_id: OID`` (target media FBID), ``text``,
       ``parent_comment_id``, ``replied_to_comment_id`` (reply threading),
       ``created_at``
   * - ``instagram.dim_threads_media``
     - VERIFIED
     - ``p92_data_engineering`` · 7d · ``ds``/``product_type``/``media_type``
     - ``fbid``, ``ig_id``, ``user_id: ThreadsUserID``, ``user_rid``,
       ``is_reply``, ``is_quote_post``, ``reply_depth``,
       ``reply_to_media_fbid``, ``reply_root_media_fbid``,
       ``quote_original_media_fbid``, ``repost_original_media_fbid`` (thread
       tree), ``username``, ``user_country``
   * - ``measurementsystems.post_events_unsessionized``
     - VERIFIED
     - ``key_user_interaction_data`` · **5475d (~15y)** · ``ds``/``ts``
     - Nested ``post`` struct; author ``post.author.profile.id: FBProfileID``
       (+ ``id_rid``). FB posts + stories. **UDP-gated** access.
   * - ``measurementsystems.content_actions``
     - VERIFIED (f3 def)
     - ``key_user_interaction_data`` · (see def) · ``ds``
     - ``actor_id`` (author FBID), ``content_id``, ``container_id``,
       ``parent_content_id``, ``action_type`` (``'create'`` = authored),
       ``content_type`` (``'post'``/``'photo'``/...), ``text``,
       ``extra_user_generated_content``, ``creation_time`` — canonical FB
       content-action log
   * - ``ad_metrics.daily_user_fb_post_content_actions_for_relevance``
     - VERIFIED
     - (ads) · 45d · ``ds``
     - ``separable_id: FBSID``, ``actor_fbtype``, ``post_id``, ``post_fb_type``,
       ``event_time``, ``content_type`` — rec/relevance daily index (no text)

.. warning::

   ``instagram.dim_instagram_media`` and ``instagram.dim_ig_media`` **do NOT
   exist** — do not cite them. The canonical IG media object is
   ``dim_instagram_media_v2_unrestricted``. Likewise ``instagram.ig_media_to_author_ids``
   exists but is **filtered to Wearables creators** — not canonical; use
   ``dim_instagram_media_igid_to_fbid`` for the general media→author mapping.


Content free-text (captions & hashtags)
=======================================

.. list-table::
   :header-rows: 1
   :widths: 32 12 20 36

   * - Table
     - Status
     - Owner · Retention · Partitions
     - Key columns
   * - ``instagram.dim_instagram_media_caption``
     - VERIFIED
     - WWW · **~5d** · ``ds``
     - ``media_id: OID`` (media FBID / post_fbid — **the join key**),
       ``user_id: OID`` (author), ``text`` (caption body), ``video_title``,
       ``ig_id``. Caption text lives here, **not** in the media object.
   * - ``instagram.dim_ig_all_public_media_caption_hashtag``
     - VERIFIED
     - ``fair_de`` · ~25–45d *(sources disagree)* · ``ds``
     - ``media_fbid: FBID`` (join key), ``user_id: IG_FBID_V2``,
       ``caption``, ``hashtags: Map<Bigint,Varchar>``, ``media_type``,
       ``taken_at``, ``product_type``

.. warning::

   ``dim_ig_all_public_media_caption_hashtag`` **upstream is currently PAUSED**
   ("trying to bring back data till the upstream is unpaused") — only sparse
   weekly ``ds`` partitions observed, so it is **stale/gappy**. Do not rely on it
   for fresh hashtags; prefer ``dim_instagram_media_caption`` (fresh but ~5-day
   retention) for caption text. The two agents disagreed on its retention
   (25d vs 45d) — treat as UNVERIFIED-exact and re-check.


Engagement facts (user as consumer)
===================================

.. list-table::
   :header-rows: 1
   :widths: 30 12 22 36

   * - Table
     - Status
     - Owner · Retention · Partitions
     - Key columns
   * - ``instagram.fct_ig_all_interactions``
     - VERIFIED
     - ``rainyshen`` / ``ig_interactions_de`` · **790d** ·
       ``ds``/``interaction_type``/``interaction_source``
     - ``actor_id`` (IGID), ``event_time``, ``post_fbid`` (join to caption),
       ``ig_media_id``, ``post_id``, ``creation_media_group`` (feed/clips/story),
       ``delivery_class`` (organic/ad), ``is_passive``, ``client_event_name``,
       ``extra_interaction_data`` (``map<string,string>``),
       ``actor_target_is_following``, ``interface``, ``country``
   * - ``feed.fct_feed_interactions``
     - VERIFIED
     - ``core_feed_de`` · (see def) ·
       ``ds``/``interaction_type``/``interface``/``post_type``
     - ``userid``, ``rid``, ``content_id``, ``story_event_type``, ``is_ad``,
       ``content_creator_id``(``_rid``), ``object_type``, ``share_type``,
       ``interaction_count``, ``interaction_duration``, ``min/max_position`` —
       the **FB** analog of ``fct_ig_all_interactions``
   * - ``instagram.ig_impression_events_inc_archive``
     - VERIFIED
     - ``ig_impressions_de`` · **30d** ·
       ``ds``/``event_name``/``client_event_name``/``delivery_class``/``ts``
     - ``event_name`` (e.g. ``vpvd_impression``), nested
       ``content.containing_post.ig_id`` / ``.fbid`` / ``.text.content`` /
       ``.hashtag[]``, ``viewer.profile.ig_id``, ``dwell_time_capped``
       (double). **Impression firehose — huge.**

.. warning::

   ``ig_impression_events_inc_archive`` is the most expensive source here (the
   entry-point Daiquery labels the impression+dwell query *"~800 TB/day"* —
   **UNVERIFIED exact size**, but it is unquestionably a multi-TB/day firehose).
   Always constrain by ``ds`` **and** ``event_name`` (both partition keys) and a
   single day; treat as opt-in. ``vpvd_impression`` = an impression that achieved
   a **VPVD (Viewport View Duration)** view (glossary-VERIFIED).


Online engagement sequences (DataFM / AUS)
==========================================

The online path reads pre-aggregated per-user sequences from **ZippyDB** via
DataFM/AUS. Details and the read API in :doc:`online_collection_datafm_aus`; the
per-event trait vocabulary in :doc:`event_taxonomy`.

**Use cases (VERIFIED — ``entrepot_unique_ids.thrift`` + ARS ``AUS_USE_CASES``):**

.. list-table::
   :header-rows: 1
   :widths: 14 34 52

   * - ``use_case_id``
     - Name
     - Surface / notes
   * - 574
     - ``fb_public_sparse``
     - FB public, sparse variant (fewer traits, longer history)
   * - **577**
     - ``fb_public`` (``hstu_v2_fb_public``)
     - **FB public/organic feed** — the default in ``datafm_adapter.py``
   * - 611
     - ``fb_video_positive``
     - FB video positive engagement
   * - 644
     - ``fb_private``
     - FB private
   * - 658
     - ``ig_public``
     - IG public/organic feed
   * - 698
     - ``ig_video_positive``
     - IG video positive engagement
   * - 750
     - ``threads_public``
     - Threads public

**Offline lineage (Hive) of the sequences (VERIFIED):**

.. list-table::
   :header-rows: 1
   :widths: 40 12 48

   * - Table
     - Status
     - Notes
   * - ``feed_fblearner.aus_fb_public_compaction_30m_enriched_map``
     - VERIFIED
     - Daily 30-min-window compaction of 577; ``viewer_rid`` + 6 map trait
       columns (``int/long/bool/float/string/id_score_pair_traits`` keyed by
       ``XLogEventTraitID``); ``ds``; retention 60d
   * - ``feed_fblearner.dim_aus_fb_public_compaction_30m_enriched_map``
     - VERIFIED
     - Cumulative/lifelong rollup of the above
   * - ``...aus_ig_public_compaction_30m_map``
     - VERIFIED
     - IG (658) counterpart
   * - ``feed_fblearner.dim_fb_xlog_{post_id,creator_id}_enrichments``,
       ``dim_fb_xlog_object_traits_rollup``
     - VERIFIED (filenames)
     - Post/creator/object enrichment dims joined into 577 (CU cluster/SID
       traits)
   * - ``facebook_ml_core_traits_long_term_inc_archive_signal`` /
       ``instagram_ml_core_traits_long_term_inc_archive_signal``
     - VERIFIED
     - Raw XLog engagement events feeding AUS (the upstream firehose)


NL user profiles (Biography output)
===================================

.. list-table::
   :header-rows: 1
   :widths: 32 12 18 38

   * - Table
     - Status
     - Owner · Retention
     - Key columns
   * - ``instagram.biography_prompts_inc_archive``
     - VERIFIED (via mirror)
     - async job ``2712004`` · (``ds``+``ts``)
     - ``user_id: FamilyUID``, ``query_type``, ``prompt``, ``llm_output``
       (the generated profile/interests), UIH arrays
       ``uih_object_ids``/``uih_engagement_event_types``/
       ``uih_event_timestamps_ms``/``uih_object_author_ids``/``uih_apps``/
       ``uih_content_categories``, ``llm_post_processing_output``.
       ~340M rows/~2.8 TB per ``ds``. No standalone dataset ``.py``.
   * - ``feed.biography_interests_for_meta_ai``
     - VERIFIED
     - ``ai_topic_understanding`` · 45d
     - ``user_id: FamilyUID``, ``query_type``, ``parsed_interest``,
       ``interests_array: Array<Varchar>``, ``last_updated_ds``
   * - ``instagram.ig_author_biography_prompt``
     - VERIFIED
     - ``user_taste_graph`` · 44d
     - ``user_id: UserIGID``, ``message_v2_prompt`` (NL profile prompt)
   * - ``instagram.threads_author_biography_prompt``
     - VERIFIED
     - ``user_taste_graph`` · 7d
     - ``author_threads_rid: ThreadsUserRID``, ``message_v2_prompt``


Social graph
============

.. list-table::
   :header-rows: 1
   :widths: 34 12 18 36

   * - Table
     - Status
     - Owner · Retention
     - Key columns
   * - ``instagram.dim_instagram_follow_graph_partitioned``
     - VERIFIED
     - ``ig_growth_de`` · 21d
     - ``source_id: UserIGID`` (follower) + ``source_rid``,
       ``target_id: UserIGID`` (followee) + ``target_rid``, ``created_at``;
       partitions ``ds``/``source_is_active``/``target_is_active``/
       ``is_reciprocal``


Online stores (non-Hive)
========================

.. list-table::
   :header-rows: 1
   :widths: 16 22 62

   * - Store
     - Where
     - Role
   * - **ZippyDB**
     - AUS sequences; ARS memory
     - Serving-time AUS reads (``datafm_adapter.py``); ARS Memory OS store
       (use-case **56862**, ACL ``zippydb.free.rec_sys_demo``)
   * - **Laser**
     - KV tiers
     - FBID→RID (``rid_mapping``, ``fbid_to_rid``); ARS per-user MezQL/Shots
       overrides; ``biography_interests_meta_ai_mvp``
   * - **Scribe / XLog**
     - event categories
     - Raw engagement (``*_ml_core_traits_*``) feeding AUS; ``content_actions``
       realtime category (FB authored actions)

.. seealso::

   The 7 reference systems (:doc:`reference_systems`) also emit useful logs —
   e.g. ``instagram.star_dear_algo_reply`` (STAR),
   ``groups.ember_llm_ranker_logging_inc_archive`` (Ember),
   ``feed.interest_fm_api_logs_inc_archive`` (InterestFM content labels),
   ``ad_metrics.adsllama_30_embeddings_cluster_ids_eds_dump_ads`` (AdsLlama
   content embeddings). See the reference ``.md`` for their verified schemas.
