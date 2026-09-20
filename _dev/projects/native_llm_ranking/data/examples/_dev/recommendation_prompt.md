# Recommendation prompt — real production structure, markdown, no JSON

A recommendation/ranking prompt (assemble a user's profile + historical events →
**predict future events**) written the way Meta's real LLM rankers write it: **natural-
language markdown**, not JSON. The user-facing values are **slots** (`‹…›`) that you fill
with **real data** by running the queries in Part 2 — nothing here is synthesized, and no
real user PII is baked into this file.

> **Why slots, not baked-in values.** Bulk-exporting a real user's engagement history / PII
> into a repo file is blocked by a privacy control (correctly). This file is the real
> prompt *structure* + the real *queries*; you (authorized, with proper access) run the
> queries and the output drops straight into the `‹slots›`. The structure and serialization
> are copied from real production prompts (see Provenance).


## Provenance — the real prompts this is modeled on

| Element | Real production source (VERIFIED) |
|---|---|
| Markdown `#####` profile sections (`User Demographics Profile`, `User Niche Interests Profile`, `User Negative Profile`, `User Instagram/Facebook Engagement History`, `User Creation History`, `User Search History`) | Ember `complete_user_profile` — `tasks/groups/groups_signals/llm/llm_ranker/user_profile/llm_ranker_user_profile_input_prepare.py` (H5-section `CONCAT`) |
| Prose event line `‹N days ago›, ‹verb› a post about ‹topics›` + verb map (liked/commented on/saved/reshared/followed the author from…) | Biography `prompt_builder.py` `DEFAULT_SUB_PROMPT_TEMPLATE` + `ENGAGEMENT_TYPE_TO_PHRASE` + `_get_timestamp_in_days` |
| NL bullet history + NL numbered candidates ("- The user watched to completion a short video. ‹caption›") | ARS omnimem `prototype/omnimem_mini/eval/raw_uih.py` |
| Pipe-delimited, non-JSON output (`ID | SCORE | TIER | reason`) + "spread scores" | ARS `prototype/experiments/ars_model/ranking/ranker.py` `UNIFIED_RANK_PROMPT` |
| Signal-strength weighting (search/save/follow > comment > like > show_less/hide) + hypothesis cap | ARS `core/llm/prompts.py` `INTENT_GUIDANCE_PROMPT` |
| Tiered rubric + hard caps (negative-interest / off-topic) | Ember `EmberLLMPointwisePromptConfig::SYSTEM_PROMPT_DEFAULT` |

Field values, retention windows, and id-spaces are from the verified data model in
`../../docs/` (`data_sources_catalog.rst`, `event_taxonomy.rst`, `identifiers_and_joins.rst`).


---

## Part 1 — The prompt (fill every `‹slot›` from Part 2)

### SYSTEM message

```text
You are an expert recommendation and user-modeling engine for Instagram / Facebook /
Threads. You are given ONE user's profile and their historical events (in markdown), plus a
list of candidate items. Predict the user's FUTURE ENGAGEMENT: for each candidate predict
whether and how they will interact, and forecast their next session.

Weight evidence by intent strength (strongest first):
- explicit search / "Dear Algo" requests; follows; saves; content they AUTHOR on a topic
- comments, reshares, profile visits, "show more"
- long dwell / watched-to-completion; repeated exposure
- a single like or short view  (weak — context only)
- NEGATIVE (strong): hide, "show less", report, unfollow, quick skip  -> suppress that topic
Weight the last 7 days most; let older signals decay; note rising vs. fading interests.
Treat what the user CREATES as first-party interest evidence. Separate long-term taste
from in-session intent (recent intent can override taste).

Score each candidate:
- STRONG   (p_engage 0.80-1.00): matches a high-confidence interest or a followed creator,
           with a corroborating strong signal.
- MODERATE (0.45-0.79): matches a general/adjacent interest.
- WEAK     (0.15-0.44): tangential or thinly supported.
- SUPPRESS (0.00-0.14): matches the user's Negative Profile, or a hard cap.
Hard caps (take the MIN of the score and the cap): negative-interest match -> 0.10;
off-topic with no interest overlap -> 0.30; ad on a non-preferred topic -> 0.20.

Rules: use the FULL range and SPREAD scores (best >= 0.90, worst <= 0.10; no ties). Ground
every prediction in a specific line from the user's history/profile. Do NOT invent
interests; a claim with no behavioral evidence is a "hypothesis" capped at 0.30. Be
decisive about the single most likely action.

Output — one line per candidate, ranked best first, NO JSON, no prose outside the lines:
  CANDIDATE_ID | P_ENGAGE (0.00-1.00) | PREDICTED_ACTION | TIER | one clause of evidence
PREDICTED_ACTION is one of: save, comment, share, follow, like, watch_complete, view_only,
skip, show_less, hide. Then one final line:
  NEXT_SESSION | active window: ‹when› | rising: ‹…› | fading: ‹…› | most likely next: ‹…›
```

### USER message

```text
# Recommend for this user

## About this user
‹one natural-language sentence: age, gender, location, language, tenure, cohort, creator?›
  ← fill from Query A (dim_ig_users / bi.dim_all_users)

##### User Demographics Profile:
‹age / gender / location / locale / account type (creator/business/personal) / followers / following›
  ← Query A

##### User Niche Interests Profile:
‹fine-grained interests with confidence, e.g. "trail & ultra running (high) · race fueling (high) · trail shoes (med)"›
  ← Query F (biography_interests_for_meta_ai) or derive from history topics (Query C+E)

##### User Long-term Interest Profile:
‹coarse topics, e.g. "Fitness & Training · Outdoor & Nature · Travel"›
  ← Query F / interest clusters

##### User Negative Profile:
‹topics/creators the user suppressed (hide / show-less / unfollow), e.g. "crypto/day-trading; fast-food"›
  ← Query D (ig_feed_events / instagram_engagement_events: see_less/hide)

##### User Instagram Engagement History (most recent first):
- ‹2h ago›, ‹saved› a ‹Reel› by ‹@author›‹ (follows)› about ‹topics› — "‹caption of that post›"; ‹watched 58s to completion›
- ‹3h ago›, ‹commented on› a ‹Reel› by ‹@author› about ‹topics› — "‹caption›"; the user wrote: "‹their comment text›"
- ‹…one line per event, newest first…›
  ← Query C (interactions) + Query E (caption/topics of each engaged post) + Query G (comment text)

##### User Facebook Engagement History (most recent first):
- ‹…same shape, from Query C-FB (feed.fct_feed_interactions)…›

##### User Threads Engagement History (most recent first):
- ‹…same shape, from Query C-TH (Threads engagement)…›

##### User Creation History (what the user authored — first-party signal):
- ‹6d ago›, posted a ‹Reel›: "‹caption›" (topics: ‹…›) — it received ‹views/likes/saves›
- ‹…one line per authored post/reel/story/comment/thread, from Query H…›

##### User Search History:
- ‹recent search queries, strongest intent signal — from Query I if available›

## Candidates to rank
1. by ‹@author›‹ (follows)› — ‹Reel›, posted ‹6h ago›, ‹5.4k likes› — "‹caption›" — topics: ‹…›
2. by ‹@author› — ‹Carousel›, ‹organic|ad› — "‹caption›" — topics: ‹…›
‹…one entry per candidate; fill from your candidate source (retrieval output) + Query E for their captions/topics…›

## Task
Predict this user's future events:
(A) Rank & predict every candidate above (use the SYSTEM output format).
(B) Forecast the next session (the NEXT_SESSION line).
```


---

## Part 2 — Real data-collection queries (fill the slots)

Run these in Daiquery/Presto. Pin `<DS>` (recent day) and resolve ids first. Every table,
column, join key, and retention below is VERIFIED (see `../../docs/`). Respect retention:
captions ~3d, comments ~3d, media dims ~7d, FB interactions 35d, IG interactions 790d,
impressions 30d — so collect content text within days or fall back to the 90-day InterestFM
snapshot.

**Query 0 — resolve ids (start here).**
```sql
-- IGID -> RID and FB, for the online/cross-app joins
SELECT fbid, rid FROM privacy.dim_ig_fbid_to_rid WHERE ds='<DS>' AND fbid = <IG_FBID_6057>;
-- FB<->IG family link (cross-platform assembly)
SELECT ff_sk, fb_ids, ig_ids FROM ffdp.dim_family_fb_ig_user
WHERE ds='<DS>' AND CONTAINS(ig_ids, <IGID>);
```

**Query A — profile / demographics (`##### User Demographics Profile`).**
```sql
SELECT userid, username, gender, country, stated_age, reg_ds,
       element_at(interface_l28,'instagram') AS l28,
       is_creator_account, is_business_profile, is_private, account_tiers, followers, following
FROM instagram.dim_ig_users
WHERE ds='<DS>' AND isactivated='1' AND userid = <IGID>;
-- FB side (optional): SELECT userid, name, gender, age, country, locale, friend_count
--   FROM bi.dim_all_users WHERE ds='<DS>' AND userid = <FBID>;
```

**Query C — IG engagement events (`##### User Instagram Engagement History`).**
```sql
SELECT from_unixtime(cast(event_time AS bigint)) AS ts,
       interaction_type, is_passive, delivery_class, actor_target_is_following,
       post_fbid, ig_media_id, creation_media_group, media_type_name,
       element_at(extra_interaction_data,'comment_text') AS comment_text
FROM instagram.fct_ig_all_interactions
WHERE ds BETWEEN '<DS_START>' AND '<DS>' AND actor_id = <IGID>
  AND creation_media_group IN ('feed','clips')
ORDER BY event_time DESC LIMIT 200;
-- FB (Query C-FB): feed.fct_feed_interactions WHERE userid=<FBID> (retention 35d)
-- Threads (Query C-TH): aus_threads_public_* / fct_threads_* keyed by ThreadsUserRID
```

**Query D — negative signals (`##### User Negative Profile`).** Follow/see-less are NOT in
`fct_ig_all_interactions` — use the feed/engagement events + graph.
```sql
-- see-less / hide (topics to suppress): source = ig_feed_events / instagram_engagement_events
--   (confirm exact table+column in your namespace; then map post_fbid -> topics via Query E)
-- unfollow / follow events: connection/graph domain (connection_events), NOT the fact table
```

**Query E — content of each engaged/candidate post (caption + hashtags + topics).** Join on
`post_fbid` (media FBID), NEVER `ig_media_id`.
```sql
-- caption text (retention ~3d):
SELECT media_id AS post_fbid, text AS caption, video_title
FROM instagram.dim_instagram_media_caption
WHERE ds='<DS>' AND media_id IN (<post_fbids>);
-- hashtags:
SELECT media_fbid AS post_fbid, hashtags
FROM instagram.dim_ig_all_public_media_caption_hashtag
WHERE ds='<DS>' AND media_fbid IN (<post_fbids>);
-- content-understanding topics/entities/sentiment (retention ~90d — the durable fallback):
SELECT object_fbid AS post_fbid, interest_fm_task, output
FROM feed.interest_fm_api_logs_inc_archive
WHERE ds='<DS>' AND object_fbid IN (<post_fbids>);
-- (FIT topic is also in-row on fct_ig_all_interactions: feed_interest_classification)
```

**Query G — the user's comment text + the post it was on (`commented on` lines).**
```sql
SELECT c.text AS comment_text, c.media_id AS post_fbid, c.parent_comment_id, c.created_at
FROM instagram.dim_instagram_comment_v2 c
WHERE c.ds='<DS>' AND c.user_id = <IG_FBID_6057>
ORDER BY c.created_at DESC LIMIT 100;
-- then join media_id -> Query E for the caption of the post they commented on
```

**Query H — authored content (`##### User Creation History`) + received engagement.**
```sql
-- posts/reels/stories/carousels the user created (media dim ~7d; use fct_ig_media_events for >7d):
SELECT fbid AS post_fbid, ig_id, product_type, media_type, createtime
FROM instagram.dim_instagram_media_v2_unrestricted
WHERE ds='<DS>' AND user_id = <IG_FBID_6057> ORDER BY createtime DESC;
-- caption via Query E (media_id=fbid); received engagement:
SELECT * FROM instagram.ig_media_engagement_datelist WHERE ds='<DS>' AND /* their media */ ...;
-- comments/replies authored: dim_instagram_comment_v2 (Query G)
-- Threads authored: instagram.dim_threads_media WHERE user_id=<ThreadsUserID>
-- FB authored: measurementsystems.post_events_unsessionized (post.author.profile.id=<FBID>)
```

**Query F — NL interests (optional shortcut for the Niche/Long-term profile).**
```sql
SELECT user_id, interests_array, parsed_interest
FROM feed.biography_interests_for_meta_ai
WHERE ds='<DS>' AND user_id = <FamilyUID = IGID or FBID>;
-- or the full generated NL profile: instagram.biography_prompts_inc_archive.llm_output
```


---

## Part 3 — What user data we can get (recap)

| Prompt section | Source table(s) | How far back |
|---|---|---|
| Demographics / profile | `dim_ig_users`, `bi.dim_all_users` | ∞ |
| Interests (niche/long-term) | `biography_interests_for_meta_ai`, in-row FIT, `interest_fm_api_logs` | 45d / 90d |
| Negative profile (hide/see-less/unfollow) | `ig_feed_events`/`instagram_engagement_events`, connection graph | varies |
| IG engagement history | `instagram.fct_ig_all_interactions` | **790d** |
| FB engagement history | `feed.fct_feed_interactions` | 35d |
| Threads engagement history | `aus_threads_public_*` / `fct_threads_*` | 90d |
| Engaged/candidate post content (caption, hashtags) | `dim_instagram_media_caption`, `dim_ig_all_public_media_caption_hashtag` | **~3d** (→ 90d via InterestFM) |
| Content-understanding (topics/entities/sentiment) | `feed.interest_fm_api_logs_inc_archive` + `meta_i2_*` | 90d |
| Comment text + parent + post | `dim_instagram_comment_v2` / `ig_comment_events` | ~3d |
| Authored content + received engagement | `dim_instagram_media_v2_unrestricted`, `dim_threads_media`, `post_events_unsessionized`; `ig_media_engagement_datelist` | ~7d (media dim) / longer via event tables |
| Impressions + dwell | `ig_impression_events_inc_archive` | 30d |
| Online pre-aggregated sequence | DataFM/AUS (577 fb 30d · 574 fb_sparse 400d · 658 ig 30d · 698 ig 90d · 750 threads) | 30–400d |

Cross-platform: assemble FB + IG + Threads separately, unify by per-app RID →
`ffdp.dim_family_fb_ig_user` (Biography already does this via its `uih_apps` = IG/FB/Threads).


## Honesty & privacy note

- **Nothing here is synthesized.** User-specific values are `‹slots›` populated by the Part 2
  queries; no fabricated names/numbers are presented as real.
- **The prompt is pure markdown / natural language** (no JSON in the user message), matching
  real production serialization (Ember `#####` sections, Biography prose event lines). The
  only code blocks are SQL (Part 2) and the pipe-delimited output spec.
- **Real-user PII is not written into this repo.** An automated agent bulk-collecting real
  user engagement data into a local file is blocked by a privacy control; the correct path
  is you running the authorized queries with proper access/retention handling.
- **Structure/serialization/tables are VERIFIED** against production code and the metastore
  this session; see Provenance and `../../docs/`.
