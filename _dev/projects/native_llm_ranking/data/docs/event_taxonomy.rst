==========================
Historical Event Taxonomy
==========================

.. contents::
   :local:
   :depth: 2

"Historical events" is the heart of the user representation. This chapter defines
the event categories, the two ways they are represented (row-level Hive facts vs.
the online aggregated **AUS** sequence), the interaction-type vocabulary, and the
verified **AUS trait catalog** — i.e. exactly which events are captured and under
what names.


Two representations of the same history
=======================================

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Aspect
     - Row-level Hive facts
     - Online AUS sequence
   * - Grain
     - one row per event (or per interaction bucket)
     - one **column per trait**, one array-index per event
   * - Tables / store
     - ``fct_ig_all_interactions``, ``feed.fct_feed_interactions``,
       ``ig_impression_events_inc_archive`` (:doc:`data_sources_catalog`)
     - ZippyDB via DataFM; offline mirror
       ``aus_fb_public_compaction_30m_enriched_map``
   * - Access
     - Presto/Spark (offline)
     - ``multi_fetch_datafm_feature`` (online) —
       :doc:`online_collection_datafm_aus`
   * - Best for
     - full fidelity, free text, exploration
     - compact, serving-time, pre-aggregated + CU-enriched


Event categories
================

.. list-table::
   :header-rows: 1
   :widths: 20 34 46

   * - Category
     - Examples
     - Primary source(s)
   * - **Authored — post**
     - create IG media / FB post / Threads post
     - ``dim_instagram_media_v2_unrestricted``, ``dim_threads_media``,
       ``content_actions`` (``action_type='create'``)
   * - **Authored — comment / reply**
     - comment, reply, comment-like
     - ``dim_instagram_comment_v2`` (``text`` + parent/replied-to)
   * - **Authored — thread / repost / quote**
     - reply chains, reposts, quote posts
     - ``dim_threads_media`` (``is_reply``, ``reply_root_media_fbid``, …)
   * - **Engagement — positive**
     - like, comment, share, save, follow, reactions (love/haha/…)
     - ``fct_ig_all_interactions``; AUS ``NUM_LIKE``/``NUM_COMMENT``/… traits
   * - **Engagement — negative**
     - hide, report, unfollow, not-interested, show-less
     - AUS ``NUM_HIDE_V2``/``NUM_SHOW_LESS``/``NUM_UNFOLLOW`` (see warning below)
   * - **Engagement — passive / consumption**
     - impression, VPVD view, dwell, video watch, swipe, tap, pause
     - ``ig_impression_events_inc_archive`` (dwell); AUS ``VPVD_MSEC``,
       ``VIDEO_WATCH_TIME_SEC``, ``NUM_*_SWIPE``…
   * - **Context**
     - surface, position, session, country, following-state, organic/ad
     - fact-table columns; AUS ``SURFACE``/``POSITION_ID``/``IS_FOLLOWING``/
       ``IS_AD``


Interaction-type vocabulary (Hive facts)
========================================

In ``fct_ig_all_interactions`` the ``interaction_type`` is a **partition key** — a
curated taxonomy of **86 values** (VERIFIED via metastore partition scan),
spanning positive engagement, navigation, and story/creation actions, e.g.:
``like, media_like, story_like, comment, comment_reply, comment_like, save,
repost, public_reshare, external_share, poll_vote, quiz_response, story_reply,
screenshot`` and navigation ``media_tap, single_tap, swipe_{up,down,left,right},
pause, auto_advance, replay_button_tap, pinch_to_zoom``. Companion columns:

* ``client_event_name`` — the raw underlying client event (a *data* column here).
* ``is_passive`` (bool) — *"whether an interaction is active or passive"*;
  passive = consumption (views/dwell/auto-advance), active = deliberate.
* ``delivery_class`` — *"organic or ad"*; filter ``='organic'`` to exclude ads.
* ``actor_target_is_following`` — whether the actor follows the content author.

.. warning::

   **Negative feedback is under-represented in ``fct_ig_all_interactions``.** The
   86-value ``interaction_type`` taxonomy contains **no native negative event**
   (no ``hide`` / ``not_interested`` / ``report`` / ``unfollow``). A
   ``CASE ... interaction_type IN ('hide','report','unfollow','not_interested')``
   (as written in the entry-point Daiquery) will therefore rarely or never match.
   Robust negative signal must come from: (a) the **AUS** negative traits
   (``NUM_HIDE_V2``, ``NUM_SHOW_LESS``, ``NUM_UNFOLLOW``, ``NUM_SUBMIT_REPORT``),
   (b) a dedicated "see less"/negative-feedback source, or (c) NLP over
   ``comment_text``. Do not treat absence of a negative row as neutral.


AUS trait catalog (what the online sequence captures)
=====================================================

The online AUS sequence is an ``AusLists`` columnar struct: a ``SERVER_TIME``
timestamp spine plus ``map<XLogEventTraitID, list<...>>`` columns, all
index-aligned (index ``i`` across all columns = the i-th event). The trait
**vocabulary** is defined by per-surface catalogs; the **emitted subset** per use
case is a configerator allowlist (``DeploymentConfig.xlog_traits``, in the
configerator repo — **UNVERIFIED-exact** here). Below is the VERIFIED catalog
content per surface.

Use case 577 — ``fb_public`` (Facebook organic feed)
----------------------------------------------------

Curated trait groups (VERIFIED — ``model_context_protocol/python_servers/aus/
AusUseCases.py``, corroborated in ``fb_trait_catalog.py``):

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Group
     - Traits
   * - Spine / context
     - ``SERVER_TIME`` (spine), ``SURFACE``, ``POSITION_ID``, ``CONTENT_TYPE``,
       ``IS_AD``, ``IS_FOLLOWING``, ``POST_IS_PUBLIC``, ``POST_CREATION_TIME``,
       ``IS_REELS``, ``FB_SHORTS_IFU_TRAY_POSITION`` *(last UNVERIFIED in code)*
   * - Content / author
     - ``POST_ID``, ``POST_OWNER_ID``, ``POST_OWNER_RID``, ``ROOT_POST_ID``,
       ``VIDEO_ID``, ``AD_ID``
   * - Video
     - ``VIDEO_LENGTH_SEC``, ``VIDEO_WATCH_TIME_SEC`` (+ ``_MSEC`` / ``_PFL``),
       ``VPVD_MSEC`` (viewport-view duration)
   * - Positive engagement
     - ``NUM_LIKE``, ``NUM_LIKE_ON_COMMENT``, ``NUM_COMMENT``,
       ``NUM_COMMENT_REPLY``, ``NUM_COMMENT_VPV``, ``NUM_SHARE``,
       ``NUM_SAVE_V2``, ``NUM_FOLLOW_V2``
   * - Reactions
     - ``NUM_LOVE``, ``NUM_HAHA``, ``NUM_WOW``, ``NUM_ANGER`` *(via AusUseCases)*,
       ``NUM_SORRY`` *(via AusUseCases)*, ``NUM_SUPPORT`` *(via AusUseCases)*
   * - Negative
     - ``NUM_HIDE_V2``, ``NUM_SHOW_MORE``, ``NUM_SHOW_LESS``, ``NUM_EXIT_VDD_V2``
   * - Share targets
     - ``NUM_SHARE_MESSENGER``, ``NUM_SHARE_WHATSAPP``, ``NUM_SHARE_SMS``
   * - CU / embed (enrichment, joined on post_id/creator_id)
     - ``IFR_UNIFIED_I3_CLUSTER_ID``, ``JSTM_2023C_SUBTOPIC_IDS``, ``UIR_90K_L0``
       — shorthand for enrichment columns
       ``ifr_unified_i3_cluster_id_11_list_pos0``,
       ``jstm_2023c_subtopic_ids_high_recall_pos0``, ``uir_90k_l0_xsurface_pos0``;
       plus semantic-IDs ``IFM_ONEFLOW_SID_V1``, ``IFM_V4_SID_8K4L``,
       ``CU_UIR_V2_SID_PREFIX_1..4GRAM``,
       ``INTERESTFM_128D_ENCODER_EMBEDDING_1M_CL_POS0``,
       ``XRVISUAL_2024_1280D_20K_KMEANS_CLUSTERS_POS0``

Use case 658 — ``ig_public`` (Instagram organic feed)
-----------------------------------------------------

The IG catalog (VERIFIED, ``ig_trait_catalog.py`` read in full — mirrors
``aus_ig_public_compaction_30m_map``) is the richest. Highlights beyond the
common set:

* **Counts:** ``NUM_SAVE, NUM_SHARE, NUM_FOLLOW, NUM_RECIPROCAL_FOLLOW,
  NUM_UNFOLLOW, NUM_SHOW_LESS, NUM_SHOW_MORE, NUM_SCREENSHOT, NUM_MEDIA_TAP,
  NUM_IMPRESSION, NUM_LIKE_TAP, NUM_HIDE, NUM_SUBMIT_REPORT, NUM_VPV,
  NUM_PROFILE_TAP, NUM_AUDIO_TAP``, prediction scores ``P_SKIP_SCORE``.
* **Clips / video:** ``NUM_CLIPS_SWIPE_NEXT/BACK``,
  ``NUM_CLIPS_VIEWER_ENTRY/EXIT``, ``NUM_VIDEO_PAUSE``, ``VPVD_MSEC``,
  ``VIDEO_WATCH_TIME_SEC``, ``NUM_ZOOM``, ``NUM_CAROUSEL_SWIPE``.
* **Falco-gated engagement:** ``NUM_COMMENT`` (``instagram_organic_comment``),
  ``NUM_LIKE`` (``instagram_organic_like``), ``NUM_UNLIKE``,
  ``NUM_LIKE_ON_COMMENT``, ``NUM_SHARE_STORY``, ``NUM_SHARE_EXTERNAL``,
  ``NUM_RESHARE_SELECT_*_RECIPIENT``.
* **Story / create:** ``NUM_CREATE_MEDIA``, ``NUM_STORY_PLAYBACK_ENTRY/EXIT``,
  ``NUM_STORY_QUICK_REACTION``, ``NUM_REPOST``, ``NUM_QUOTE_POST``.
* **Context / IG-specific:** ``IG_MEDIA_PRODUCT_TYPE``, ``AUDIO_ID``,
  ``IG_ORIGINAL_MEDIA_ID``, ``IS_FRIENDS_AND_FAMILY``, ``IS_CONNECTED``,
  ``POST_OWNER_FOLLOWER_COUNT``, ``IG_MEDIA_AUTHOR_ID``,
  ``VISUAL_SIMILARITY_CLUSTER_ID``, ``MEDIA_ORIGINAL_LANGUAGE_HASH``.
* **CU / embed (enrichment):** ``ig_jstm_2023b_id2_ig_50k_pos0``,
  ``uir_v2_50k_clusters_ig_pos0``, ``interest_fm_dit_mini_l1/l2_ig_pos0``,
  ``ig_postray_2024a_rqkmeans_sid_1024_l12/l34``,
  ``xray_visual_2025_semantic_id_graphsid_bigram12``.

.. note::

   **Shared base raw traits** (both FB & IG, from ``xlog_trait_catalog.py
   ::add_basic_raw_traits``): ``SERVER_TIME`` (COALESCE of long-trait /
   ``event_time``), ``TARGET_USER_RID``, ``TARGET_USER_ID``,
   ``TARGET_OBJECT_KEY``, ``SURFACE``, ``POST_ID``, ``POST_IS_PUBLIC``,
   ``POST_CREATION_TIME``, ``IS_REELS``, ``IS_AD``, ``IS_FOLLOWING``,
   ``POST_OWNER_RID/ID``, ``AD_ID``, ``POSITION_ID``, ``VPV_DURATION``,
   ``VIDEO_LENGTH_MS``, ``EVENT_TYPE``, ``CONTENT_TYPE``,
   ``COMMENT_VPV_DURATION``.


Impressions & dwell
===================

Impressions (what the user *saw*, whether or not they engaged) come from
``ig_impression_events_inc_archive``:

* ``event_name = 'vpvd_impression'`` = an impression that achieved a **VPVD
  (Viewport View Duration)** view. (VPV = a VPVD entry with duration ≥ 250 ms.)
  VERIFIED via glossary + partition scan.
* ``dwell_time_capped`` (double) — capped dwell: for ``igtv``/``live`` capped at
  min(actual, 4 h), otherwise min(actual, 1 h). VERIFIED (column comment).
* Nested content ``content.containing_post.{ig_id, fbid, text.content}`` gives an
  inline caption of the impressed post.

.. warning::

   This is the most expensive source in the catalog (multi-TB/day; the Daiquery
   labels it "~800 TB/day", **UNVERIFIED-exact**). Only collect impressions when
   dwell/exposure is essential, always constrained to a single ``ds`` **and**
   ``event_name`` (both partition keys). See :doc:`offline_collection_hive`.


From XLog to AUS (how these events are captured)
================================================

Both representations originate from the same **XLog** engagement stream (VERIFIED
via ``stage2_aggregation.md`` / ``xlog_onboarding.md``):

.. mermaid::

   flowchart LR
     CLIENT["Client engagement events"] --> XLOG["XLog ml_core_traits (Scribe)<br/>facebook_/instagram_ml_core_traits_long_term_inc_archive_signal"]
     XLOG --> ONLINE["Stylus PTail AUS writer<br/>map/reduce → enrich → encode →<br/>ZippyDB AUS_ROW (mutable) + daily AUS_LIST (immutable)"]
     XLOG --> OFFLINE["Dataswarm DataFMComposer (11-stage)<br/>30-min compaction → Hive<br/>aus_fb_public_compaction_30m_enriched_map"]
     ONLINE --> READ["multi_fetch_datafm_feature (BOTH)"]

The **row-level facts** (``fct_ig_all_interactions`` etc.) are separate
warehouse products of the same client events, so the two representations are
consistent but not identical (the AUS view is aggregated, CU-enriched, and
RID-keyed; the facts are row-level, free-text-bearing, and IGID-keyed).
