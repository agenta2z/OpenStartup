========
Glossary
========

Terms, acronyms, and identifiers used across this documentation. Definitions are
VERIFIED against code/metastore/wikis unless marked otherwise.

.. glossary::
   :sorted:

   ARS
     Agentic Recommendation System — an agent-native recommender (LLM
     orchestrator + "Memory OS" + RecSys infra wrapped as tools). Code at
     ``fbcode/mrs/rankevolve/ARS/``. Source of the online-ingest entry point.

   AUS
     Aggregated User Sequence(s) — the columnar per-user engagement sequence
     implemented by ``multifeed/datafm``. Stored in ZippyDB as ``AUS_ROW`` +
     ``AUS_LIST``. (One wiki says "Aggregated User Storage"; naming is
     inconsistent.)

   AUS_ROW
     Mutable, real-time AUS tier: one row per recent event, written from the
     XLog tailer. Fetch mode ``ONLY_MUTABLE=0``.

   AUS_LIST
     Immutable, daily-compacted AUS tier: columnar ``AusLists`` history. Fetch
     mode ``ONLY_IMMUTABLE=1``. ``BOTH=2`` merges LIST + ROW.

   AusLists
     The columnar return struct: a ``timestamps`` (``SERVER_TIME``) spine plus
     ``map<XLogEventTraitID, list<...>>`` trait columns, index-aligned.

   Biography
     Meta's LLM (Llama 3.x) user-understanding system that turns engagement
     history into free-form NL user profiles. Output tables
     (``biography_prompts_inc_archive``, ``biography_interests_for_meta_ai``)
     are a shortcut for the profile pillar.

   DataFM
     The MRS long-sequence user-history (UIH) infrastructure over AUS.
     Authoritative expansion *"Data for Future Modeling"* (NOT "Data Feature
     Materialization").

   DAS
     Data Augmentation Service — the Ads C++/Folly service that runs foundation-
     model inference and caches embeddings (POLARIS mechanism).

   delivery_class
     Column indicating whether media is **organic** or **ad**.

   ds
     The standard daily date partition key on Hive tables (``YYYY-MM-DD``).

   EDS
     Entity Data Service — holds per-entity columns (e.g. AdsLlama embeddings)
     dumped to Hive.

   EngagementSummaryMemory
     ARS memory item: a singleton, RID-keyed, 100–200 word NL summary of a
     user's DataFM engagement. Distinct from ``ProfileMemory``.

   EventMemory
     ARS "L0" memory item: one raw engagement event
     (``user_id, session_id, event_ts, event_type, event_description, ...``).

   FamilyUID
     A dual-app user key that is either an IGID or an FBID; used by Biography
     output tables.

   FBID
     Facebook graph id. IG users are FBID fbtype 6057 (``IG_FBID_V2``); IG media
     are fbtype 6097 (``INSTAGRAM_MEDIA_V2``).

   fetch_mode
     ``AusFetchMode`` enum controlling an AUS read:
     ``ONLY_MUTABLE=0, ONLY_IMMUTABLE=1, BOTH=2, ONLY_CACHABLE_MUTABLE=3,
     BOTH_WITH_CACHABLE_MUTABLE=4``.

   HSTU
     The core MRS generative-recommender sequence architecture; the AUS use-case
     ids carry the ``hstu_v2_*`` prefix (e.g. ``hstu_v2_fb_public = 577``).

   IGID
     Instagram client/legacy user id. Most derived IG tables and the engagement
     facts key on IGID (e.g. ``dim_ig_users.userid``,
     ``fct_ig_all_interactions.actor_id``).

   ig_media_id
     Instagram's **client-side** media id. NOT the caption-table join key.

   InterestFM (IFM)
     Multimodal content-understanding FM producing topics/entities/hashtags/
     sentiment/embeddings for organic content. Output:
     ``feed.interest_fm_api_logs_inc_archive`` + AUS CU traits.

   is_passive
     Interaction column: passive = consumption (views/dwell/auto-advance),
     active = deliberate engagement.

   Laser
     Meta's low-latency KV store. Tiers used here: ``rid_mapping``/``fbid_to_rid``
     (FBID→RID), ARS per-user MezQL/Shots overrides, ``biography_interests_*``.

   L28 / L7
     From ``dim_ig_users.interface_l28``/``interface_l7`` (``map<string,bigint>``):
     the number of days in the last 28 / 7 the user was a DAU on that interface.
     (Pre-2025-05-12 it counted Time-Spent days, not DAU.)

   MediaFBIDv2
     Informal name for a media object's FBID (``post_fbid``). The concept is
     VERIFIED; the term has no formal glossary entry.

   Memory OS
     ARS v2's memory subsystem (design tiers L0/L1/L2 → ``EventMemory`` /
     ``PreferenceMemory`` / ``ProfileMemory``).

   post_fbid
     The media object's FBID (fbtype 6097) — the join key for caption/hashtag
     tables. Appears as ``fbid``/``post_fbid``/``media_id``/``media_fbid``.

   PreferenceMemory
     ARS "L1" memory item: an LLM-distilled preference with polarity/strength/
     confidence/TTL metadata.

   Presto / Daiquery
     Presto is the interactive SQL engine; Daiquery is Meta's notebook UI over
     it. The offline entry point is a Daiquery workspace.

   ProfileMemory
     ARS "L2" memory item: the synthesized user profile — a 150–300 word NL
     ``profile_description`` + ``persona_tags`` + ``top_interests`` +
     ``potential_interests``.

   RID
     Replacement ID — a de-identified FBID for anonymized/long-lived data; the
     FBID↔RID mapping is severed at deletion. Required by online AUS lookups.

   Scribe
     Meta's log-transport bus; raw XLog engagement events land in Scribe
     categories (``*_ml_core_traits_*``) that feed AUS.

   SERVER_TIME
     The timestamp spine of an AUS sequence; every trait column is aligned to it.

   UIH
     User Interaction History — a user's engagement sequence; inlined as
     ``uih_*`` arrays in Biography's prompt table.

   use_case_id
     The DataFM/AUS deployment id selecting a surface's sequence (e.g.
     ``577 = fb_public``, ``658 = ig_public``); registered in
     ``entrepot_unique_ids.thrift``.

   VPVD / VPV
     Viewport View Duration — time a story is fully visible or covers >½ the
     screen. VPV = a VPVD entry with duration ≥ 250 ms.
     ``event_name='vpvd_impression'`` marks such impressions.

   XLog
     The engagement-event logging layer; raw ``ml_core_traits`` events are the
     source for both AUS and the interaction fact tables.

   ZippyDB
     Meta's distributed KV store; holds AUS sequences and the ARS Memory OS
     store (use-case 56862).
