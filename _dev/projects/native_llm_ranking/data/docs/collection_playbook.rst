====================
Collection Playbook
====================

.. contents::
   :local:
   :depth: 2

Practical, end-to-end recipes that compose the sources
(:doc:`data_sources_catalog`), joins (:doc:`identifiers_and_joins`), and paradigms
(:doc:`online_collection_datafm_aus`, :doc:`offline_collection_hive`) into
runnable collection flows. Start here once you know *what* you want (
:doc:`data_model_user_profile`).


Decision guide: online vs offline
==================================

.. mermaid::

   flowchart TD
     Q1{Serving-time,<br/>per-user, ms latency?} -->|yes| ON["Online: DataFM/AUS<br/>Recipe B"]
     Q1 -->|no| Q2{Need free text /<br/>full fidelity /<br/>many users?}
     Q2 -->|yes| OFF["Offline: Hive<br/>Recipe A / C"]
     Q2 -->|no| Q3{Just need an<br/>NL user profile?}
     Q3 -->|yes| BIO["Reuse Biography<br/>Recipe D"]
     Q3 -->|no| OFF


Recipe A — Offline cohort dataset (engagement + free text)
==========================================================

Goal: a reproducible dataset of sampled users × their feed engagement × the text
of engaged content. This is the hardened entry-point Daiquery pattern.

#. **Pick ``DS`` / window.** Choose a recent ``ds`` (caption text only ~5 days
   back — :doc:`privacy_and_retention`).
#. **Build cohorts** from ``instagram.dim_ig_users`` with deterministic hash
   sampling (cold_starter / marginal / active_core). See the SQL in
   :doc:`offline_collection_hive`.
#. **Pull interactions** from ``instagram.fct_ig_all_interactions`` (feed/clips),
   keeping ``post_fbid`` + ``ig_media_id``, ``is_passive``, ``delivery_class``,
   ``comment_text``.
#. **Attach content text** by joining ``post_fbid`` → ``dim_instagram_media_caption``
   (fresh) and ``dim_ig_all_public_media_caption_hashtag`` (best-effort, paused).
#. **(Optional) impressions/dwell** — only if needed; single ``ds`` +
   ``event_name='vpvd_impression'``; treat as expensive.
#. **Get negatives correctly** — not from ``interaction_type`` (no native
   negatives); use AUS negative traits or NLP on ``comment_text``.

Checklist: partition-pruned ✔ · deterministic sample ✔ · caption on ``post_fbid``
✔ · impressions gated ✔ · retention-aware ✔.


Recipe B — Online per-user engagement sequence
==============================================

Goal: fetch a user's recent engagement sequence at serving time.

#. **Resolve FBID/IGID → RID** (``fbid_to_rid_sync``: Laser ``rid_mapping`` →
   ``fbid_to_rid`` → ``RidBackfillService``; avoid triggering the write-side
   backfill in bulk).
#. **Choose use case(s)** — 577 ``fb_public`` for FB, 658 ``ig_public`` for IG,
   or fan out across all seven as ARS does.
#. **Fetch** ``multi_fetch_datafm_feature(use_case_id, [rid], fetch_mode=BOTH,
   start_ts, end_ts)`` (``BOTH`` = full history + recent). Offload the blocking
   call (``run_in_executor``) if async.
#. **Decode** the columnar ``dict[trait → per-event array]`` against the
   ``SERVER_TIME`` spine (:doc:`event_taxonomy`); merge across use cases if
   fanning out.
#. **Summarize / feed the LLM** — e.g. ARS formats numeric traits + weekday split
   and produces a 100–200 word ``EngagementSummaryMemory``
   (:doc:`data_model_user_profile`).

Checklist: RID resolved ✔ · use case chosen ✔ · ``BOTH`` mode ✔ · trait decode
index-aligned ✔.


Recipe C — Assemble a full user profile (all four blocks)
=========================================================

Goal: a comprehensive per-user record = identity + authored history + engagement
history + content + NL layer (the schema in :doc:`data_model_user_profile`).

#. **Identity & metadata.** ``dim_ig_users`` (IG) / ``bi.dim_all_users`` (FB);
   resolve IGID/FBID/RID (``dim_ig_fbid_to_rid``, ``FB_FBID_TO_IGID_V2``);
   optional cross-app via ``ffdp.dim_family_fb_ig_user``.
#. **Authored history.**

   * IG posts: ``dim_instagram_media_v2_unrestricted`` (author ``user_id`` =
     IG_FBID_V2 → convert to IGID to match the cohort).
   * IG comments/replies: ``dim_instagram_comment_v2`` (tree via
     ``parent_comment_id``/``replied_to_comment_id``).
   * Threads: ``dim_threads_media`` (reply/quote/repost parents).
   * FB posts: ``measurementsystems.content_actions`` (``action_type='create'``,
     has ``text``).
   * Attach caption text via ``fbid`` → ``dim_instagram_media_caption``.
#. **Engagement history.** Recipe A (interactions + content text); optionally the
   online AUS sequence (Recipe B) for the pre-aggregated view.
#. **NL / derived layer.** Reuse Biography (Recipe D) *or* generate your own
   profile modeled on the ARS ``ProfileMemory`` schema; enrich events with
   InterestFM CU labels / AUS CU traits.
#. **Key everything by RID** for storage; record ``ds`` provenance.

.. warning::

   **Retention forces a forward-collection design.** Interactions live 790 days
   but captions ~5 days and comments ~3 days. You cannot reconstruct old content
   text — accumulate daily going forward, or accept text only for recent events
   (:doc:`privacy_and_retention`).


Recipe D — Reuse the Biography NL profile
=========================================

Goal: obtain a ready-made natural-language user profile cheaply.

#. Read ``instagram.biography_prompts_inc_archive`` for the ``llm_output``
   (generated profile) keyed by ``user_id`` (``FamilyUID`` = IGID or FBID), plus
   the ``uih_*`` arrays (a reference encoding of the user's history).
#. Or read ``feed.biography_interests_for_meta_ai`` for parsed
   ``interests_array``.
#. Join back to your cohort via the ``FamilyUID`` (branch on IGID vs FBID —
   :doc:`identifiers_and_joins`).

Use this when you need *a* profile; build your own (Recipe C) when you need schema
control. Either way, the ``uih_*`` arrays are the best in-house template for
serializing historical events into an LLM prompt.


Global checklists
=================

**Identifiers** — resolved all needed spaces (IGID/FBID/RID); caption joins on
``post_fbid``; author↔engagement bridged via ``FB_FBID_TO_IGID_V2``; carousels
noted.

**Cost** — partition keys filtered first (``ds`` + ``event_name`` for
impressions); deterministic sampling; impressions/``post_events`` opt-in +
entitlement.

**Privacy** — RID-keyed storage; retention-aware windows; UGC/UII minimized;
deletion honored; UDP-gated sources gated (:doc:`privacy_and_retention`).

**Reproducibility** — pinned ``ds``; hash (not ``RAND()``) sampling; recorded
query/notebook provenance and this doc's VERIFIED/UNVERIFIED tags.
