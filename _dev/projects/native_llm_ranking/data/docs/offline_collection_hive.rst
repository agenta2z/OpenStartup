========================================
Offline Collection: Hive / Daiquery
========================================

.. contents::
   :local:
   :depth: 2

The **offline** pattern samples user cohorts from Hive and assembles their
history + content into a dataset for training/eval/analysis. The canonical entry
point is Daiquery ``queryid=909457732173156`` — *"[MCP] IG typical users
(cold/marginal/active) feed engagement + free text"*. This chapter dissects it,
flags its pitfalls, and gives a corrected, cost-safe recipe.


Provenance
==========

VERIFIED (``meta whatisthis.entity``): an **adhoc DaiQuery workspace**
(``ANALYTICS_NOTEBOOK`` fbtype 12180), created **2026-07-14 23:30 PT**,
not deleted, personal/workplace-loadable. The ``[MCP]`` prefix indicates it was
authored via an agent/MCP tool. Owner not retrievable in this environment
(GraphQL execute blocked); no external references found. It is exploratory
project work, complementary to — but **not code-linked with** — the online ARS
ingest.


What the query does
===================

Five cells build a ~200-users-per-cohort dataset with engagement + free text:

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Cell
     - Purpose
   * - *(markdown)*
     - Cohort definitions: **cold_starter** = reg ≤ 45d · **marginal** =
       reg > 28d & ``interface_l28['instagram']`` ∈ [1,14] · **active_core** =
       reg > 28d & L28 ≥ 25
   * - ``Cell1_discover_interaction_types``
     - Enumerate ``interaction_type``/``interaction_source`` from
       ``fct_ig_all_interactions``
   * - ``cohort_final``
     - Build cohorts from ``dim_ig_users`` (``isactivated='1'``, ``reg_ds``),
       compute ``days_since_reg`` + L28/L7 from ``interface_*`` maps, segment,
       then **deterministically sample** ~200/segment via
       ``row_number() OVER (PARTITION BY segment ORDER BY hash(userid))``
   * - ``Cell2_cohort_and_interactions`` (Query A)
     - Join cohort × ``fct_ig_all_interactions`` (feed/clips), keep ``post_fbid``
       (caption key), ``ig_media_id``, ``delivery_class``, ``is_passive``,
       ``comment_text``, and a **sentiment CASE** (positive/negative/neutral)
   * - ``Cell3_impressions_dwell_OPTIONAL`` (Query B)
     - *(expensive)* impressions + ``dwell_time_capped`` + inline caption from
       ``ig_impression_events_inc_archive`` (``event_name='vpvd_impression'``)
   * - ``Cell4_media_free_text`` (Query C)
     - Captions/hashtags via ``post_fbid`` → ``dim_instagram_media_caption``
       (``media_id``) + ``dim_ig_all_public_media_caption_hashtag``
       (``media_fbid``)

The pattern generalizes to *"sample a cohort → pull their events → attach content
text"* — the core offline collection loop.


Pitfalls the query teaches (and traps to avoid)
===============================================

.. warning::

   #. **Join captions on ``post_fbid`` (media FBID), never ``ig_media_id``.**
      The caption/hashtag tables key on the graph FBID; joining on the client id
      returns nothing. (The query is correct to emphasize this — VERIFIED in
      schemas.)
   #. **The "negative" sentiment bucket barely fires.** ``fct_ig_all_interactions``
      has no native negative ``interaction_type`` — see the warning in
      :doc:`event_taxonomy`. Get negatives from AUS traits
      (``NUM_HIDE_V2``/``NUM_SHOW_LESS``/``NUM_UNFOLLOW``) or NLP on comment text.
   #. **Caption freshness vs. retention.** ``dim_instagram_media_caption`` has
      **~5-day** retention — collect captions for recent ``ds`` promptly, or you
      will miss text for older engaged media.
   #. **The hashtag table is PAUSED / stale.**
      ``dim_ig_all_public_media_caption_hashtag`` upstream is paused (sparse
      weekly partitions). Don't depend on it for fresh hashtags.
   #. **Impressions are a firehose.** ``ig_impression_events_inc_archive`` is
      multi-TB/day; always filter ``ds`` **and** ``event_name`` and one day only.
      The "~800 TB/day" figure in the query is **UNVERIFIED-exact** but the cost
      risk is real.
   #. **Carousels:** ``post_fbid`` resolves to the container, not child items.


Corrected, cost-safe recipe
===========================

A hardened version of the pattern. This is a *sketch* — validate table/column
names in Daiquery before running (schemas drift), and never run Query B casually.

.. code-block:: sql

   -- 1) Cohorts: deterministic sample, partition-pruned, no RAND()
   WITH cohort AS (
     SELECT userid, reg_ds,
       date_diff('day', date(reg_ds), date('<DS>'))            AS days_since_reg,
       coalesce(element_at(interface_l28, 'instagram'), 0)     AS l28
     FROM instagram.dim_ig_users
     WHERE ds = '<DS>' AND isactivated = '1' AND reg_ds IS NOT NULL
   ),
   segmented AS (
     SELECT *,
       CASE
         WHEN days_since_reg <= 45                          THEN 'cold_starter'
         WHEN days_since_reg > 28 AND l28 BETWEEN 1 AND 14  THEN 'marginal'
         WHEN days_since_reg > 28 AND l28 >= 25             THEN 'active_core'
       END AS segment
     FROM cohort
   ),
   sampled AS (   -- deterministic, reproducible per (segment, userid)
     SELECT *, row_number() OVER (
              PARTITION BY segment
              ORDER BY abs(from_big_endian_64(xxhash64(to_utf8(cast(userid AS varchar)))))
            ) AS rn
     FROM segmented WHERE segment IS NOT NULL
   )
   SELECT * FROM sampled WHERE rn <= 200;

   -- 2) Interactions (feed/clips, organic), keep BOTH id spaces + negatives from
   --    a real signal, not a doomed interaction_type CASE.
   SELECT c.segment, c.userid,
          from_unixtime(cast(i.event_time AS bigint)) AS event_ts,
          i.post_fbid,                     -- caption join key (media FBID)
          i.ig_media_id,                   -- client id (reference)
          i.interaction_type, i.client_event_name,
          i.is_passive, i.delivery_class,  -- passive vs active; organic vs ad
          i.actor_target_is_following,
          element_at(i.extra_interaction_data, 'comment_text') AS comment_text
   FROM instagram.fct_ig_all_interactions i
   JOIN sampled c ON i.actor_id = c.userid
   WHERE i.ds = '<DS>' AND i.creation_media_group IN ('feed','clips');

   -- 3) Free text: join ONLY on post_fbid (media FBID). Caption first (fresh),
   --    hashtags best-effort (upstream paused).
   SELECT m.post_fbid, cap.text AS caption, cap.video_title, ht.hashtags
   FROM (SELECT DISTINCT post_fbid FROM /* step 2 result */ x WHERE post_fbid IS NOT NULL) m
   LEFT JOIN instagram.dim_instagram_media_caption cap
     ON cap.ds = '<DS>' AND cap.media_id = m.post_fbid
   LEFT JOIN instagram.dim_ig_all_public_media_caption_hashtag ht
     ON ht.ds = '<DS>' AND ht.media_fbid = m.post_fbid;

Improvements over the original: partition-pruned cohort; deterministic hash
sample; both id spaces retained; comment text via ``element_at`` on the verified
``map<string,string>``; captions joined only on ``post_fbid``; impressions left
out by default; honest handling of negatives and the paused hashtag table.

.. tip::

   To add **authored** content (posts/comments/replies/threads) to the same
   users, join the cohort ``userid`` (after ``FB_FBID_TO_IGID_V2`` if starting
   from a media object's author FBID) to ``dim_instagram_media_v2_unrestricted``,
   ``dim_instagram_comment_v2``, and ``dim_threads_media`` — see Recipe C in
   :doc:`collection_playbook`.


When to use offline collection
==============================

Use this pattern for training/eval dataset construction, cohort analysis, and any
work needing free text or full fidelity. For serving-time per-user context, use
:doc:`online_collection_datafm_aus` instead. The two are complementary: offline
to *build and evaluate*, online to *serve*.
