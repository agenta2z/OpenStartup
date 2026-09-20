=========================
Identifiers & Join Keys
=========================

.. contents::
   :local:
   :depth: 2

Getting identifiers wrong is the single most common way to silently corrupt an
LLM-native dataset: a join on the wrong id space returns **zero rows without
erroring**. This chapter is the authoritative id + join reference for everything
in :doc:`data_sources_catalog`.


The identifier zoo
==================

.. list-table::
   :header-rows: 1
   :widths: 20 18 62

   * - Identifier
     - Space
     - What it is / where it appears
   * - **FBID**
     - account & object
     - Raw Facebook graph id. IG *users* are FBID **fbtype 6057**
       (``IG_FBID_V2``); IG *media* are FBID **fbtype 6097**
       (``INSTAGRAM_MEDIA_V2``). Media object tables store the author as
       ``user_id: IG_FBID_V2``. **VERIFIED** (dataset defs).
   * - **IGID**
     - client / legacy
     - Instagram's client/legacy id. **Most derived IG tables and all the
       engagement facts key on IGID** (``fct_ig_all_interactions.actor_id``,
       ``dim_ig_users.userid``). **VERIFIED**.
   * - **RID**
     - de-identified
     - "Replacement ID" — a pseudo-anonymous FBID used for long-lived /
       anonymized data. **Online AUS lookups require RID.** IG-user RID type is
       ``InstagramV2RID``; Threads is ``ThreadsUserRID``. See
       :doc:`privacy_and_retention`. **VERIFIED**.
   * - **post_fbid** (a.k.a. **MediaFBIDv2**)
     - media graph id
     - The media object's FBID (fbtype 6097). **This is the join key for the
       caption / hashtag tables.** Appears as ``fbid`` (media object),
       ``post_fbid`` (interactions), ``media_id`` (caption), ``media_fbid``
       (hashtags). **VERIFIED**.
   * - **ig_media_id**
     - media client id
     - The Instagram *client-side* media id (``dim_...media_v2.ig_id``,
       ``content.containing_post.ig_id``). **Not** the caption-table key — a
       frequent bug. **VERIFIED**.
   * - **FamilyUID**
     - cross-app user
     - A dual-app user key that is *either* an IGID *or* an FBID; used by
       Biography output tables (``user_id: FamilyUID``). **VERIFIED**.

.. warning::

   "MediaFBIDv2" is used informally in queries/docs for the media FBID
   (``post_fbid``). The **term** itself has no glossary entry (UNVERIFIED as a
   formal term), but the underlying **FBID-vs-client-id distinction it names is
   VERIFIED** in the dataset definitions.


Conversion tables & functions
=============================

.. list-table::
   :header-rows: 1
   :widths: 34 20 46

   * - Mapping
     - Direction
     - Mechanism (VERIFIED)
   * - IG user FBID (6057) → IGID
     - offline
     - UDF ``FB_FBID_TO_IGID_V2(user_id)`` (per the column comment on
       ``dim_instagram_media_v2_unrestricted.user_id``)
   * - IG FBID ↔ RID
     - offline
     - ``privacy.dim_ig_fbid_to_rid`` (signal view over
       ``privacy.dim_ig_fbid_to_rid_unpublished``): ``fbid: IG_FBID_V2`` ↔
       ``rid: InstagramV2RID`` (daily, ``ds``-partitioned)
   * - client ``ig_media_id`` ↔ media ``post_fbid``
     - offline
     - ``instagram.dim_instagram_media_igid_to_fbid``: ``ig_id (MediaIGID)`` ↔
       ``fbid (MediaFBIDV2)`` (+ author in all 3 spaces:
       ``user_id``/``user_rid``/``user_igid``)
   * - FB account ↔ IG account (cross-app)
     - offline
     - ``ffdp.dim_family_fb_ig_user``: ``fb_ids: Array<FBAccountID>`` ↔
       ``ig_ids: Array<UserIGID>`` (family soft-match)
   * - FBID → RID (online, ARS)
     - online
     - ``ARS/memory_os/nodes/recsys/fbid_rid.py::fbid_to_rid_sync`` — a 3-tier
       chain: Laser ``rid_mapping`` → Laser ``fbid_to_rid`` →
       ``RidBackfillService``. See warning below.

.. danger::

   The online tier-3 fallback ``RidBackfillService.backfill`` is **read-write**:
   if an FBID has no RID it **allocates a new one and writes it to TAO**. It is a
   side-effecting call, not a pure lookup. Prefer the Laser tiers; only fall
   through to backfill deliberately. **VERIFIED** in ``fbid_rid.py``.


The join map
============

The verified linkage across authored-content, profile, and engagement tables.
Everything hangs off two hubs: the **media FBID** (``post_fbid``) for content,
and the **user id** (IGID/FBID, bridged to RID) for people.

Media / content joins (all on **media FBID**)::

    dim_instagram_media_v2_unrestricted.fbid   (media FBID = post_fbid)
       = dim_instagram_media_caption.media_id                 (caption text)
       = dim_ig_all_public_media_caption_hashtag.media_fbid   (caption + hashtags)
       = dim_instagram_comment_v2.media_id                    (comments on the post)
       = dim_threads_media.fbid                               (Threads posts)
       = fct_ig_all_interactions.post_fbid                    (engagement, FB side)

    # comment / thread trees:
    dim_instagram_comment_v2.parent_comment_id / .replied_to_comment_id
    dim_threads_media.reply_to_media_fbid / reply_root_media_fbid
                     / quote_original_media_fbid / repost_original_media_fbid

Media id-space bridge (client ⇄ graph)::

    dim_instagram_media_igid_to_fbid:  ig_id (client ig_media_id) ⇄ fbid (post_fbid)
    dim_instagram_media_v2_unrestricted.ig_id  = client ig_media_id
        → matches engagement tables that key on ig_media_id

User / author joins::

    # engagement facts key on IGID; media objects store author as IG_FBID_V2:
    IGID(author) = FB_FBID_TO_IGID_V2( dim_instagram_media_v2_unrestricted.user_id )
    FBID ⇄ RID (IG):        privacy.dim_ig_fbid_to_rid.fbid ⇄ .rid
    FBID ⇄ RID (prejoined): dim_instagram_media_v2_unrestricted_partitioned.user_rid
    FB ⇄ IG account:        ffdp.dim_family_fb_ig_user.fb_ids[] ⇄ ig_ids[]

    # profiles:
    IG:  dim_ig_users.userid                 (IGID)
    FB:  bi.dim_all_users.userid (FBID) = content_actions.actor_id
                                        = post_events_unsessionized.post.author.profile.id

Biography NL-profile join (dual-app key)::

    biography_prompts_inc_archive.user_id (FamilyUID = IGID or FBID)
       → dim_ig_users        (when IGID)
       → bi.dim_all_users     (when FBID)
    uih_object_ids[] / uih_object_author_ids[]  → media / author ids in the history

Visually:

.. mermaid::

   flowchart TB
     subgraph PEOPLE["People id spaces"]
       IGID["IGID<br/>(engagement facts, dim_ig_users)"]
       FBID["FBID<br/>(IG user 6057, media 6097, bi.dim_all_users)"]
       RID["RID<br/>(AUS / privacy)"]
     end
     subgraph MEDIA["Media id spaces"]
       CLIENT["ig_media_id<br/>(client)"]
       GRAPH["post_fbid / MediaFBIDv2<br/>(caption, hashtag, comment, interactions)"]
     end
     FBID -->|FB_FBID_TO_IGID_V2| IGID
     FBID -->|dim_ig_fbid_to_rid| RID
     CLIENT -->|dim_instagram_media_igid_to_fbid| GRAPH
     FBID -.family soft-match.-> IGID


Critical pitfalls
=================

.. warning::

   #. **Caption/hashtag tables join on ``post_fbid`` (media FBID), never on
      ``ig_media_id``.** Joining on the client id returns nothing. This is called
      out explicitly in the entry-point Daiquery and **VERIFIED** in the schemas.
   #. **Engagement facts key users on IGID; media objects store the author as
      ``IG_FBID_V2`` (6057).** Convert with ``FB_FBID_TO_IGID_V2`` before joining
      author↔engagement.
   #. **Online AUS needs RID, not FBID/IGID.** Resolve first
      (:doc:`online_collection_datafm_aus`).
   #. **Carousels:** ``post_fbid`` / ``post_id`` resolve to the *carousel
      container*, not child items — relevant when matching a caption to a
      specific child. **VERIFIED** (column comment).
   #. **Two IG "id" columns look alike.** ``dim_instagram_media_v2_unrestricted``
      exposes both ``fbid`` (graph) and ``ig_id`` (client); pick deliberately.
