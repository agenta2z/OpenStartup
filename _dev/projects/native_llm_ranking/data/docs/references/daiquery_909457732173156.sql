-- ---------------------------------------------------------------------------
-- REFERENCE COPY — provenance artifact.
-- Source: Daiquery workspace "[MCP] IG typical users (cold/marginal/active)
--         feed engagement + free text"
-- URL:    https://www.internalfb.com/intern/daiquery/workspace/?queryid=909457732173156
-- Type:   ANALYTICS_NOTEBOOK (adhoc DaiQuery workspace), created 2026-07-14.
-- Captured verbatim 2026-07-15 via knowledge_load. Analyzed (and hardened) in
-- ../offline_collection_hive.rst. Macros: <DS> (end date), <DS_START> (window start).
-- NOTE: original inline comments (incl. Chinese) are preserved as-is.
-- ---------------------------------------------------------------------------

-- Cohort definition:
--   cold_starter = registration <= 45 days
--   marginal     = registration > 28 days & interface_l28['instagram'] in [1,14]
--                  (Ecosystems DS: marginal = L28 <= 14)
--   active_core  = registration > 28 days & interface_l28['instagram'] >= 25


-- === Cell1_discover_interaction_types =====================================
-- Check sentiment CASE values in Query A
SELECT interaction_type, interaction_source, count(*) AS n
FROM instagram.fct_ig_all_interactions
WHERE ds = '<DS>'
GROUP BY 1, 2
ORDER BY n DESC
LIMIT 100;


-- === cohort_final =========================================================
WITH cohort AS (
  SELECT userid, reg_ds,
    date_diff('day', date(reg_ds), date('<DS>'))          AS days_since_reg,
    coalesce(element_at(interface_l28,'instagram'),0)      AS l28,
    coalesce(element_at(interface_l7 ,'instagram'),0)      AS l7,
    CASE
      WHEN date_diff('day', date(reg_ds), date('<DS>')) <= 45 THEN 'cold_starter'
      WHEN date_diff('day', date(reg_ds), date('<DS>')) > 28
           AND coalesce(element_at(interface_l28,'instagram'),0) BETWEEN 1 AND 14 THEN 'marginal'
      WHEN date_diff('day', date(reg_ds), date('<DS>')) > 28
           AND coalesce(element_at(interface_l28,'instagram'),0) >= 25 THEN 'active_core'
      ELSE NULL END AS segment
  FROM instagram.dim_ig_users
  WHERE ds = '<DS>' AND isactivated = '1' AND reg_ds IS NOT NULL
),
cohort_ranked AS (
  SELECT *, row_number() OVER (PARTITION BY segment
      ORDER BY abs(from_big_endian_64(xxhash64(to_utf8(cast(userid AS varchar)))))) AS rn
  FROM cohort WHERE segment IS NOT NULL
)
  SELECT * FROM cohort_ranked WHERE rn <= 200;  -- ~200 typical users per cohort


-- === Cell2_cohort_and_interactions (Query A) ==============================
-- 3 cohorts of typical users + feed interactions (keep ig_media_id and post_fbid)
SELECT c.segment, c.userid, c.l28, c.days_since_reg,
  from_unixtime(cast(i.event_time AS bigint))  AS event_ts,
  i.post_fbid,                                 -- free-text join key (MediaFBIDv2), used for caption lookup
  i.ig_media_id,                               -- user-side media id (!= caption table key; reference only)
  i.post_id, i.creation_media_group,
  i.media_type_name,
  i.extra_interaction_data,
  extra_interaction_data['comment_text'] AS comment_text,
  i.delivery_class,                            -- organic vs ad
  i.interaction_type, i.client_event_name,
  i.is_passive,                                -- true = passive (save/screenshot/private); false = social (like/comment)
  CASE
    WHEN lower(i.interaction_type) IN ('like','story_like','comment','comment_reply','comment_like','share','reshare','repost','direct_reshare','public_reshare','follow','save','screenshot','external_share','poll_vote','quiz_response','story_reply','live_comment')
      OR regexp_like(lower(i.client_event_name),'like|save|comment|share|follow|repost|reply|screenshot') THEN 'positive'
    WHEN lower(i.interaction_type) IN ('hide','report','unfollow','not_interested')
      OR regexp_like(lower(i.client_event_name),'hide|not_interest|report|unfollow') THEN 'negative'
    ELSE 'neutral' END                         AS sentiment,
  i.actor_target_is_following                  AS follows_author,
  i.interface, i.session_id, i.country
FROM instagram.fct_ig_all_interactions i
JOIN cohort_final c ON i.actor_id = c.userid
WHERE i.ds = '<DS>'
  AND i.creation_media_group IN ('feed','clips');
-- CAVEAT (see docs): the 'negative' branch rarely matches — fct_ig_all_interactions
-- has no native negative interaction_type. Use AUS negative traits or comment NLP.


-- === Cell3_impressions_dwell_OPTIONAL (Query B) ===========================
-- Very expensive (~800TB/d, UNVERIFIED): feed + dwell time + inline caption users "saw"
SELECT c.segment, c.userid,
  from_unixtime(cast(e.event_time AS bigint))   AS event_ts,
  e.content.containing_post.ig_id                AS ig_media_id,
  e.content.containing_post.text.content         AS caption_inline,
  e.dwell_time_capped                            AS dwell_time,
  e.event_name
FROM instagram.ig_impression_events_inc_archive e
JOIN cohort_final c
  ON e.viewer.profile.ig_id = c.userid
WHERE e.ds = '<DS>'                              -- single day only
  AND e.event_name = 'vpvd_impression';


-- === Cell4_media_free_text (Query C) ======================================
-- Free text of the feeds (post_fbid -> caption/hashtags)
-- KEY: caption table's join key is post_fbid (MediaFBIDv2), NOT ig_media_id!
WITH media AS (
  SELECT DISTINCT i.post_fbid
  FROM instagram.fct_ig_all_interactions i
  JOIN cohort_final c ON i.actor_id = c.userid
  WHERE i.ds BETWEEN '<DS_START>' AND '<DS>'
    AND i.creation_media_group IN ('feed','clips')
    AND i.post_fbid IS NOT NULL
)
SELECT m.post_fbid,
  cap.text          AS caption,        -- caption free text
  cap.video_title,
  ht.hashtags                          -- map<bigint,string>
FROM media m
LEFT JOIN instagram.dim_instagram_media_caption cap
  ON cap.ds = '<DS>' AND cap.media_id = m.post_fbid          -- << post_fbid, not ig_media_id
LEFT JOIN instagram.dim_ig_all_public_media_caption_hashtag ht
  ON ht.ds = '<DS>' AND ht.media_fbid = m.post_fbid;
