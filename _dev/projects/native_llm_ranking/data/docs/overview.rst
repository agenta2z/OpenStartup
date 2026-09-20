========
Overview
========

.. contents::
   :local:
   :depth: 2


The problem
===========

Classic recommendation models consume *sparse IDs and dense features*. An
**LLM-native** recommender instead reasons over a **natural-language-ready
representation of the user and the content** — free-form profiles, event
narratives, captions, and semantically-typed sequences that an LLM can attend to
directly (see the paradigm analysis in :doc:`reference_systems`).

That shifts the data-collection burden. To build or train an LLM-native
recommender we must be able to assemble, per user, three pillars:

#. **Profile / identity metadata** — who the user is (account attributes,
   demographics, tenure/activity level, cross-app identity, follow graph).
#. **Historical events** — what the user has *done* over time, in two flavors:

   * **Authored events** — content the user *created*: posts, comments, replies,
     threads, reposts/quotes.
   * **Engagement events** — content the user *consumed / reacted to*: likes,
     comments, shares, saves, follows, hides, impressions, dwell.

#. **Content / free-text** — the actual text (captions, hashtags, comment
   bodies, video titles) and content-understanding signals of the objects those
   events touch, so the LLM can reason about *what* the user engaged with, not
   just *that* they engaged.

The user's requirement for this project — *"collect detailed user profile,
including metadata and historical events (post, comments, replies, threads,
interactions, etc.)"* — maps exactly onto these three pillars. This doc set is
the collection playbook for all three.


Two collection paradigms
=========================

Meta already collects this data two complementary ways. Both are documented here
because an LLM-native system typically needs both — offline for training/eval
dataset construction, online for serving-time context assembly.

.. list-table::
   :header-rows: 1
   :widths: 18 41 41

   * - Dimension
     - **Online** (DataFM / AUS)
     - **Offline** (Hive / Presto / Daiquery)
   * - Reference
     - :doc:`online_collection_datafm_aus` (entry point:
       ``datafm_adapter.py``)
     - :doc:`offline_collection_hive` (entry point: Daiquery
       ``909457732173156``)
   * - Store
     - ZippyDB (AUS sequences), Laser, Scribe
     - Hive warehouse tables, queried via Presto/Spark
   * - Shape
     - A pre-aggregated, columnar **event sequence** per user (``AusLists``:
       trait → per-event array), read in single-digit ms
     - Row-level **event facts** + dimension tables, joined ad hoc; minutes-to-
       hours, TB-scale scans
   * - Key space
     - **RID** (Replacement ID) — required by ZippyDB AUS lookups
     - Mostly **IGID / FBID**; RID where anonymized
   * - Freshness
     - Real-time (mutable ``AUS_ROW``) + daily-compacted history
       (``AUS_LIST``)
     - ``ds``-partitioned; typically T-1 (some tables lag ~2 days)
   * - Best for
     - Serving-time per-user context; production LLM-native ranking/summarization
     - Cohort sampling, training-set / eval-set construction, exploratory
       analysis
   * - Cost model
     - Cheap per lookup; infra-owned pipelines
     - Pay-per-scan; some source tables are enormous (impressions ≈ many TB/day)


Reference architecture
======================

The end-to-end shape of LLM-native data collection — sources on the left,
assembled user representation on the right:

.. mermaid::

   flowchart LR
     subgraph SRC["Raw sources"]
       XL["XLog engagement events<br/>(Scribe: *_ml_core_traits_*)"]
       TAO["TAO / WWW objects<br/>(media, comments, users)"]
     end

     subgraph OFF["Offline (Hive)"]
       FACTS["Event facts<br/>fct_ig_all_interactions<br/>feed.fct_feed_interactions<br/>ig_impression_events_inc_archive"]
       AUTH["Authored content<br/>dim_instagram_media_v2_unrestricted<br/>dim_instagram_comment_v2<br/>dim_threads_media"]
       TXT["Free text<br/>dim_instagram_media_caption<br/>dim_ig_all_public_media_caption_hashtag"]
       PROF["Profile / identity<br/>dim_ig_users · bi.dim_all_users"]
       BIO["NL profiles (Biography)<br/>biography_prompts_inc_archive"]
     end

     subgraph ON["Online (DataFM / AUS)"]
       AUS["AUS sequences (ZippyDB)<br/>use cases 577 fb_public / 658 ig_public / ..."]
     end

     XL --> FACTS
     XL --> AUS
     TAO --> AUTH
     TAO --> TXT
     TAO --> PROF

     FACTS --> ASM["User representation<br/>(profile + events + content)"]
     AUTH --> ASM
     TXT --> ASM
     PROF --> ASM
     BIO --> ASM
     AUS --> ASM

     ASM --> LLM["LLM-native recommender<br/>(rank / retrieve / summarize / profile)"]

The three entry points sit inside this picture: the **reference GDoc** catalogs
the boxes; **``datafm_adapter.py``** is the ``AUS → user representation`` edge;
the **Daiquery** is the ``Hive facts + free text → user representation`` edge.


Design principles
=================

These principles are enforced throughout the playbook:

#. **Verification discipline.** Prefer primary sources (code, metastore, dataset
   definitions) over docs; tag everything VERIFIED / UNVERIFIED; never invent a
   table or column. (This is how the source reference was built and how the
   corrections in :doc:`reference_systems` were found.)

#. **Identifier correctness is not optional.** IG media has *two* id spaces
   (client ``ig_media_id`` vs. graph ``post_fbid`` / MediaFBIDv2), users have
   *three* (IGID / FBID / RID), and joining on the wrong one silently returns
   nothing. See :doc:`identifiers_and_joins`.

#. **Privacy by RID.** Long-lived history is keyed by **RID**, a de-identified
   id whose mapping is severed on account deletion. Online AUS *requires* RID.
   See :doc:`privacy_and_retention`.

#. **Respect retention.** Source tables have wildly different windows (captions
   ~5 days; impressions ~30 days; interactions ~790 days; some dims infinite;
   one hashtag source is currently *paused*). Collection windows must be planned
   around these — see :doc:`privacy_and_retention`.

#. **Cost-awareness.** Some sources are multi-TB/day. Always filter on partition
   keys first, sample deterministically, and prefer pre-aggregated tables.

#. **Reproducibility.** Deterministic cohort sampling (hash-based, not
   ``RAND()``), pinned ``ds`` windows, and recorded query provenance.
