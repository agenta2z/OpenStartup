================================================
Worked Example: One User, End to End
================================================

.. contents::
   :local:
   :depth: 2

This chapter shows **what the collected data actually looks like** for a single
user, walked through every stage of the pipeline — raw source rows → id
resolution → online AUS sequence → Biography UIH encoding → the assembled
LLM-ready record. It ties together :doc:`data_sources_catalog`,
:doc:`identifiers_and_joins`, :doc:`event_taxonomy`, and
:doc:`data_model_user_profile` with concrete values.

.. warning::

   **Real schema, synthetic values.** Every **table name, column name, type,
   id-space, join key, AUS trait name, and enum code below is VERIFIED** against
   production code / the Hive metastore / dataset definitions. The **values are
   synthetic** (one fabricated user, "maya.trailruns") — this is *not* pulled
   from production, and no real user PII is shown. The only non-fabricated
   values are the ``FBID 61573248217892 → RID 545114654589218`` pair, which is
   the documented example pair from the ARS unit tests
   (``test_fbid_rid.py`` / ``test_engagement_summary.py``); NL text
   (profile / interests) is an *illustrative* LLM output, since no captured real
   ``llm_output`` string exists in code.


The demo user
=============

An Instagram-primary trail-running creator, in the ``active_core`` cohort
(reg > 28d, L28 = 27). She has presence on IG, FB, and Threads. Her identifiers
across the three user id-spaces and the two media id-spaces she touches:

.. list-table:: Identity (synthetic except the FBID↔RID pair)
   :header-rows: 1
   :widths: 30 34 36

   * - Id / attribute
     - Value
     - Space / source
   * - username
     - ``maya.trailruns``
     - ``dim_ig_users.username``
   * - **IGID**
     - ``76400489123``
     - IGID — ``dim_ig_users.userid``, ``fct_ig_all_interactions.actor_id``
   * - **FBID** (IG user, fbtype 6057)
     - ``61573248217892``
     - ``IG_FBID_V2`` — media object ``user_id`` (author)
   * - **RID**
     - ``545114654589218``
     - ``InstagramV2RID`` — AUS / privacy key
   * - Threads user id / RID
     - ``71234509876`` / ``559900112233``
     - ``ThreadsUserID`` / ``ThreadsUserRID``


Stage 0 — ID resolution
=======================

Before any collection, resolve all needed spaces (:doc:`identifiers_and_joins`).

.. code-block:: text

   FBID  61573248217892  --(laser: rid_mapping)-->  RID 545114654589218
   FBID  61573248217892  --(FB_FBID_TO_IGID_V2)--->  IGID 76400489123

   # media she engaged with (a Reel authored by "alex.ultramarathon"):
   ig_media_id (client) 3401234567890123456
        <--(dim_instagram_media_igid_to_fbid)-->  post_fbid 17920000000012345

.. note::

   Online AUS reads use the **RID**; Hive engagement facts key on **IGID**;
   caption/hashtag joins use **post_fbid** (media FBID), never ``ig_media_id``.


Stage 1 — Profile / identity rows
=================================

``instagram.dim_ig_users`` (partition ``ds='2026-07-13'``, ``isactivated='1'``) —
selected columns:

.. code-block:: text

   userid            = 76400489123
   username          = 'maya.trailruns'
   reg_ds            = '2024-11-02'            -- ~618 days tenure
   interface_l28     = {'instagram': 27, 'instagram_android': 27}   -- map<string,bigint>
   interface_l7      = {'instagram': 7}
   gender            = 'F'
   country           = 'AU'
   is_creator_account = 1
   is_business_profile = 0
   is_private        = 0
   stated_age        = 31

Cohort math: ``days_since_reg > 28`` and ``interface_l28['instagram'] = 27 ≥ 25``
→ **active_core**.

``bi.dim_all_users`` (the FB dim, if cross-app profile is needed) would carry the
FBID-keyed row: ``userid = 61573248217892``, ``rid = 545114654589218``,
``country='AU'``, ``locale='en_AU'``, etc.


Stage 2 — Authored content (user as creator)
============================================

**Her IG post** — ``instagram.dim_instagram_media_v2_unrestricted``:

.. code-block:: text

   fbid        = 17920000000067890     -- media FBID (= post_fbid space)
   ig_id       = 3402999888777666555   -- client ig_media_id space
   user_id     = 61573248217892        -- author (IG_FBID_V2 = our user)
   media_type  = 1                     -- InstagramMediaType: 1 = IMAGE
   product_type= 2                     -- InstagramMediaProductType: 2 = FEED
   createtime  = '2026-07-10 08:15:03'
   num_likes   = 214 , num_comments = 18

...with its caption in ``instagram.dim_instagram_media_caption`` (join
``media_id = fbid``):

.. code-block:: text

   media_id    = 17920000000067890
   user_id     = 61573248217892
   text        = 'Sunrise 30K on the Overland Track. Legs destroyed, soul restored. #trailrunning #tasmania'
   video_title = NULL

**Her comment** — ``instagram.dim_instagram_comment_v2`` (a reply on Alex's Reel):

.. code-block:: text

   fbid                 = 17930000000045678
   user_id              = 61573248217892          -- commenter (our user)
   media_id             = 17920000000012345       -- target media = Alex's Reel (post_fbid)
   text                 = 'This is gold — the fueling tip saved me on my last long run 🙏'
   parent_comment_id    = 0                        -- top-level
   replied_to_comment_id= 0
   created_at           = '2026-07-13 19:42:11'

**Her Threads post** — ``instagram.dim_threads_media`` (text via caption join on
``fbid``):

.. code-block:: text

   fbid        = 17920000000099999
   user_id     = 71234509876          -- ThreadsUserID
   user_rid    = 559900112233
   is_reply    = false , is_quote_post = false , reply_depth = 0
   -- text (via dim_instagram_media_caption.media_id = fbid):
   text        = 'hot take: zone 2 is the most underrated training tool for trail runners'


Stage 3 — Engagement events (user as consumer)
==============================================

``instagram.fct_ig_all_interactions`` — three rows for ``actor_id = 76400489123``
on Alex's Reel (``post_fbid = 17920000000012345``, ``ds='2026-07-13'``):

.. list-table::
   :header-rows: 1
   :widths: 16 16 12 12 14 30

   * - interaction_type
     - event_time
     - is_passive
     - delivery_class
     - follows_author
     - other
   * - ``like``
     - 1752432131
     - false
     - organic
     - true
     - ``creation_media_group='clips'``, ``ig_media_id=3401234567890123456``
   * - ``comment``
     - 1752432142
     - false
     - organic
     - true
     - ``extra_interaction_data['comment_text']='This is gold…'``
   * - ``save``
     - 1752432150
     - true
     - organic
     - true
     - ``interaction_source='feed'``

The content she engaged with — captions/hashtags via ``post_fbid`` (Alex's Reel):

.. code-block:: text

   dim_instagram_media_caption:  media_id=17920000000012345
     text = '5 things I wish I knew before my first 50K ultra 🏔️ #trailrunning #ultramarathon #running'
   dim_ig_all_public_media_caption_hashtag:  media_fbid=17920000000012345
     hashtags = {17841500000001:'trailrunning', 17841500000002:'ultramarathon', 17841500000003:'running'}
   -- (that media: media_type=2 VIDEO, product_type=16 CLIPS  → a Reel)

Optionally, an impression — ``instagram.ig_impression_events_inc_archive``
(``event_name='vpvd_impression'``): nested
``content.containing_post.ig_id=3401234567890123456``,
``content.containing_post.fbid=17920000000012345``,
``content.containing_post.text.content='5 things I wish…'``,
``dwell_time_capped=47.5`` (seconds), ``viewer.profile.ig_id=76400489123``.


Stage 4 — Online AUS sequence
=============================

The serving-time read ``multi_fetch_datafm_feature(577, [545114654589218],
fetch_mode=2, start_ts, end_ts)`` returns a **columnar** ``dict`` — trait name →
per-event array, all index-aligned to the ``SERVER_TIME`` spine. This is the
``fb_public`` (577) slice of ARS's 7-use-case fan-out; the ``ig_public`` (658)
slice is analogous with IG traits (:doc:`event_taxonomy`). Trait names are
``XLogEventTraitID`` enum names; values here are per-event (4 events shown):

.. code-block:: python

   {
     "SERVER_TIME":  [1752429600, 1752426000, 1752422400, 1752411600],  # epoch sec, desc
     "POST_ID":      [988770001, 988770002, 988770003, 988770004],       # longTraits
     "FEED_OBJECT_TYPE": [3, 7, 3, 7],   # FeedObjectType: 3=Video, 7=Photo
     "SURFACE":      [1, 1, 1, 1],       # surface code (illustrative)
     "NUM_LIKE":     [1, 0, 1, 0],       # per-event 0/1 flags
     "NUM_COMMENT":  [0, 1, 0, 0],
     "NUM_SHARE":    [0, 0, 1, 0],
     "NUM_SHOW_LESS":[0, 0, 0, 1],       # a negative signal on event 3
     "NUM_HIDE":     [0, 0, 0, 0],
     "VPVD_MSEC":    [47230, 8900, 63000, 1200],   # viewport-view duration, ms
   }

ARS's ``_format_engagement`` then reduces this to the LLM-facing text (sums the
0/1 flags, splits weekday/weekend from ``SERVER_TIME``) and the
``FeedObjectType`` enricher adds a distribution:

.. code-block:: text

   NUM_LIKE: 2 total across 4 events
   NUM_COMMENT: 1 total across 4 events
   NUM_SHARE: 1 total across 4 events
   Content type distribution: Video: 2, Photo: 2

.. note::

   Verified from the ARS fixture ``test_engagement_summary.py::_make_raw_data``
   (same shape: ``SERVER_TIME``/``FEED_OBJECT_TYPE=[3…,7…]``/``NUM_LIKE=[1…]``/
   ``NUM_COMMENT=[0…]``) and the UIH debugger's ``hstu_v2_fb_public`` read-set
   (``POST_ID`` from ``longTraits``; ``NUM_*``/``VPVD_MSEC``/``CONTENT_TYPE``/
   ``SURFACE`` from ``intTraits``; ``=== 1`` per-event check). ``SURFACE`` and
   ``CONTENT_TYPE`` code *values* are illustrative.


Stage 5 — Biography UIH encoding (history → prompt)
===================================================

The same engagement history, encoded the way Biography stores it in
``instagram.biography_prompts_inc_archive`` — the ``uih_*`` arrays use the
``Biography`` thrift enums (VERIFIED), index-aligned:

.. code-block:: python

   user_id = 76400489123          # FamilyUID (IGID here)
   query_type = 'ig_dear_algo_user_interests_in_uih_3b_sft_v3'
   uih_object_ids            = [17920000000012345, 17920000000012345, 17920000000055512, 17920000000066623]
   uih_engagement_event_types= [1, 3, 5, 10]          # EngagementEventType: 1=LIKE 3=COMMENT 5=SAVE 10=FOLLOW
   uih_event_timestamps_ms   = [1752432131000, 1752432142000, 1752190000000, 1751990000000]
   uih_object_author_ids     = [61550012349999, 61550012349999, 61550019998888, 61550012349999]
   uih_apps                  = [1, 1, 1, 1]           # App: 1=INSTAGRAM (2=FACEBOOK, 3=THREADS)
   uih_content_categories    = [1, 1, 1, 1]           # ContentCategory: 1=ORGANIC (2=AD)

Enum legend (VERIFIED — ``biography_generation_settings.thrift``):
``EngagementEventType`` 1=LIKE, 2=RESHARE, 3=COMMENT, 4=VIEW, 5=SAVE,
6=PROFILE_VISIT, 10=FOLLOW, 31=CREATE, 32=SEARCH_QUERY, 36=REPOST, 17=HIDE,
38=SEE_LESS (full range 0–38). ``App`` 1=IG/2=FB/3=Threads. ``ContentCategory``
1=ORGANIC/2=AD.

.. important::

   The **id flavor** of ``uih_object_ids`` / ``uih_object_author_ids`` is only
   typed as ``i64`` (object/author id in the engaged app's space) — whether a
   given IG row uses media-FBID vs IG-native id is **UNVERIFIED** by schema. Do
   not assume plain FBID for IG rows.

Rendered into the actual production prompt shape (verbatim template structure;
engagement verbs derive from the codes above — ``1→"liked"``, ``3→"commented
on"``, ``5→"saved"``, ``10→"followed the author from"`` — and topics from the
media's InterestFM hashtags):

.. code-block:: text

   You are tasked with summarizing a user's interests into granular topics.
   ...
   And this user has basic demographic info:
   Gender: The user is female and not a teen.
   Location: Hobart, Tasmania, Australia

   Given the a list of user engagement history on a social media platform:
   <user_engagement>
   today, user liked a post about trailrunning, ultramarathon, running,
   today, user commented on a post about trailrunning, ultramarathon, running,
   3 days ago, user saved a post about zone2, basebuilding, endurance,
   5 days ago, user followed the author from a post about ultrarunning, coaching,
   </user_engagement>
   ... Generate 10 fine-grained high-confidence interests [hierarchical JSON: L1_topic + L3_interests] ...

Example ``llm_output`` (**illustrative** — format is VERIFIED, values authored):

.. code-block:: json

   [
     {"L1_topic": "Fitness & Training",
      "L3_interests": ["Ultramarathon training", "Zone 2 base building", "Trail-running fueling"]},
     {"L1_topic": "Outdoor & Nature",
      "L3_interests": ["Overland Track Tasmania", "Alpine trail routes"]},
     {"L1_topic": "Sports",
      "L3_interests": ["50K ultra races"]}
   ]


Stage 6 — The assembled LLM-ready user record
=============================================

The four collection blocks (:doc:`data_model_user_profile`) merged into one
record, keyed by **RID**, ready to serialize into an LLM prompt or store:

.. code-block:: json

   {
     "user": {
       "rid": "545114654589218",
       "igid": "76400489123",
       "fbid": "61573248217892",
       "cohort": "active_core",
       "profile": {
         "username": "maya.trailruns", "gender": "F", "country": "AU",
         "reg_ds": "2024-11-02", "tenure_days": 618, "l28": 27,
         "is_creator_account": true, "stated_age": 31
       }
     },
     "authored_history": {
       "posts": [
         {"post_fbid": "17920000000067890", "ig_media_id": "3402999888777666555",
          "media_type": "IMAGE", "product_type": "FEED", "createtime": "2026-07-10 08:15:03",
          "caption": "Sunrise 30K on the Overland Track. Legs destroyed, soul restored. #trailrunning #tasmania"}
       ],
       "comments": [
         {"comment_fbid": "17930000000045678", "on_media": "17920000000012345",
          "text": "This is gold — the fueling tip saved me on my last long run 🙏", "ts": "2026-07-13 19:42:11"}
       ],
       "threads": [
         {"fbid": "17920000000099999", "is_reply": false,
          "text": "hot take: zone 2 is the most underrated training tool for trail runners"}
       ]
     },
     "engagement_history": {
       "interactions": [
         {"post_fbid": "17920000000012345", "type": "like",    "passive": false, "delivery": "organic", "follows_author": true, "ts": 1752432131},
         {"post_fbid": "17920000000012345", "type": "comment", "passive": false, "delivery": "organic", "follows_author": true, "ts": 1752432142},
         {"post_fbid": "17920000000012345", "type": "save",    "passive": true,  "delivery": "organic", "follows_author": true, "ts": 1752432150}
       ],
       "aus_summary_577": {"likes": 2, "comments": 1, "shares": 1, "events": 4,
                           "content_mix": {"Video": 2, "Photo": 2}, "window_days": 30}
     },
     "content": {
       "17920000000012345": {
         "caption": "5 things I wish I knew before my first 50K ultra 🏔️ #trailrunning #ultramarathon #running",
         "hashtags": ["trailrunning", "ultramarathon", "running"],
         "media_type": "VIDEO", "product_type": "CLIPS"
       }
     },
     "nl_layer": {
       "biography_interests": [
         {"L1_topic": "Fitness & Training", "L3_interests": ["Ultramarathon training", "Zone 2 base building", "Trail-running fueling"]},
         {"L1_topic": "Outdoor & Nature",   "L3_interests": ["Overland Track Tasmania", "Alpine trail routes"]},
         {"L1_topic": "Sports",             "L3_interests": ["50K ultra races"]}
       ]
     }
   }


Stage 7 — ARS memory objects (the production shape)
===================================================

If instead you target the ARS Memory OS representation
(:doc:`data_model_user_profile`), the same user materializes as these rows
(schema VERIFIED; NL text illustrative):

``ProfileMemory`` (``memory_type='profile'``, FBID-keyed):

.. code-block:: json

   {
     "memory_type": "profile",
     "user_id": "61573248217892",
     "profile_ts": 1752432200,
     "demographics": {"gender": "female", "location": "Hobart, Tasmania, AU", "language": "en"},
     "profile_description": "This user is a highly engaged endurance-sports creator based in Tasmania who centers her activity on trail and ultramarathon running. She both produces content (a recent sunrise 30K on the Overland Track) and actively engages with other runners' training and fueling advice — liking, commenting on, and saving Reels about 50K ultras and zone-2 base building, and following coaching creators. Her engagement skews toward long-form video she watches to completion, and she rarely gives negative feedback. For recommendations, prioritize technical trail-running, ultra-race preparation, fueling/nutrition, and Australian/Tasmanian outdoor content; de-prioritize generic fitness.",
     "persona_tags": ["endurance_athlete", "trail_runner", "content_creator"],
     "top_interests": ["trail running", "ultramarathon", "endurance training", "Tasmania outdoors"],
     "profile_metadata": {
       "potential_interests": [
         {"topic": "ultra-race nutrition", "reason": "saved multiple fueling-tip Reels", "confidence": 0.82},
         {"topic": "zone 2 training", "reason": "authored a Threads post on it", "confidence": 0.74}
       ]
     },
     "last_updated": 1752432200
   }

``EngagementSummaryMemory`` (``memory_type='engagement_summary'``, **RID**-keyed,
singleton):

.. code-block:: json

   {
     "memory_type": "engagement_summary",
     "user_id": "545114654589218",
     "summary": "Over the last 30 days this user engaged mostly on weekday evenings, favoring short-form video (Reels/Clips). She liked and shared trail- and ultra-running content and watched several videos to completion, with one show-less signal on an off-topic photo. Engagement is consistently positive and creator-following oriented.",
     "summary_ts": 1752432180,
     "data_window_days": 30,
     "aus_use_case_id": 577,
     "event_count": 4,
     "summary_metadata": {"contributing_use_cases": [577, 658, 611, 698]}
   }


Reproduce it for real
=====================

To produce the genuine version of this record for real users, run the offline
recipe (Recipe A/C in :doc:`collection_playbook`) against a pinned ``ds``, or the
online read (Recipe B) for a resolved RID. Everything above is schema-faithful,
so a real pull will have exactly these shapes with real values — subject to the
retention windows in :doc:`privacy_and_retention` (captions ~5d, comments ~3d,
impressions ~30d).
