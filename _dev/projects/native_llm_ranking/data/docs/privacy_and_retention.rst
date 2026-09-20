========================
Privacy & Retention
========================

.. contents::
   :local:
   :depth: 2

Data collection here touches user-identifying and user-generated content. This
chapter is the guardrail reference: the **RID** de-identification model,
per-table **retention** windows (which bound how far back you can collect), and
access/UGC handling. Treat it as mandatory reading before any collection run.


RID — the de-identification model
=================================

A **RID ("Replacement ID")** is a pseudo-anonymous stand-in for an FBID, used so
that data kept beyond 90 days can be retained without user-identifying ids
(VERIFIED — Privacy wiki "Mapping User-Identifying IDs to RIDs"):

* RIDs are FBIDs (own numeric range), **assigned at account/object creation** and
  **deleted at deletion time** — the FBID↔RID mapping is *severed* on deletion.
* Because the mapping is severed, RIDs are treated as **"No UII"** and can be used
  beyond the 90-day window that raw ids cannot.
* **Source of truth:** ``dim_fbid_to_rid`` (served via Laser); for IG,
  ``privacy.dim_ig_fbid_to_rid``.
* **Online AUS is RID-keyed** — ``datafm_pybind`` requires int RIDs
  (:doc:`online_collection_datafm_aus`).

Implications for collection:

* Prefer **RID** for any stored/long-lived dataset; resolve FBID/IGID→RID early
  (:doc:`identifiers_and_joins`).
* Deletion propagates: a dataset keyed by raw id must honor deletion; a
  RID-keyed dataset inherits the severed-mapping guarantee.
* The online FBID→RID tier-3 fallback (``RidBackfillService.backfill``) is
  **write-side** (allocates a RID) — don't trigger it during bulk collection.


Retention windows (plan your lookback around these)
===================================================

Collection windows are bounded by the **shortest-retention** table you touch.
VERIFIED windows (re-check before relying):

.. list-table::
   :header-rows: 1
   :widths: 46 16 38

   * - Table
     - Retention
     - Consequence for collection
   * - ``instagram.dim_instagram_media_caption``
     - ~5d
     - **Collect caption text promptly**; older engaged media lose captions
   * - ``instagram.threads_author_biography_prompt``
     - 7d
     - short Threads NL-profile window
   * - ``instagram.dim_instagram_media_v2_unrestricted(_partitioned)``
     - 7d
     - authored-media dim is short-lived; snapshot early
   * - ``instagram.dim_threads_media``
     - 7d
     - Threads authored content is short-lived
   * - ``instagram.dim_instagram_comment_v2``
     - 3d
     - **very short** — comment bodies must be collected quickly
   * - ``instagram.dim_instagram_media_igid_to_fbid``
     - 16d
     - media id-bridge window
   * - ``instagram.dim_instagram_follow_graph_partitioned``
     - 21d
     - follow-graph snapshot window
   * - ``instagram.dim_ig_all_public_media_caption_hashtag``
     - ~25–45d *(disagree)* + **PAUSED**
     - stale; do not rely on for fresh hashtags
   * - ``instagram.ig_impression_events_inc_archive``
     - 30d
     - impressions only ~1 month back; also huge
   * - ``ffdp.dim_family_fb_ig_user``
     - 30d
     - cross-app mapping window
   * - ``privacy.dim_ig_fbid_to_rid``
     - 45d
     - FBID↔RID map window
   * - ``feed.biography_interests_for_meta_ai``
     - 45d
     - NL interests window
   * - ``instagram.fct_ig_all_interactions``
     - **790d**
     - long interaction history available (~2.1y)
   * - ``measurementsystems.post_events_unsessionized``
     - **5475d (~15y)**
     - long FB authored-post history (UDP-gated)
   * - ``instagram.dim_ig_users`` / ``bi.dim_all_users``
     - ∞
     - profile dims retained indefinitely
   * - AUS offline (``aus_fb_public_compaction_30m_enriched_map``)
     - 60d
     - offline sequence window (online ZippyDB lookback differs)

.. important::

   **Design the collection cadence to the tightest window in your join.** If you
   need interactions (790d) *with* their captions (5d) *and* comment bodies (3d),
   you cannot backfill historically — you must **collect forward daily** and
   accumulate, or accept that content text is only available for recent events.


Access, UII & UGC
=================

* Many text columns are **user-generated content** and carry UII/UGC handling
  annotations (e.g. ``dim_instagram_media_caption.text``,
  ``dim_instagram_comment_v2.text``, ``content_actions.text``,
  Biography ``prompt``/``llm_output`` are ``UII_REMOVE``). Handle per policy.
* **``measurementsystems.post_events_unsessionized`` is UDP-gated**
  (``key_user_interaction_data``) — you need the entitlement to read it.
* AUS/DataFM data itself is owned by oncall ``datafm``; tooling by
  ``mrs_sequence_infra``.

Collection principles
=====================

#. **RID-first** for stored datasets; resolve early, avoid backfill writes.
#. **Respect the tightest retention** in every join; collect short-lived text
   (captions 5d, comments 3d, media dims 7d) forward, daily.
#. **Minimize UII surface** — keep only the fields the model needs; separate
   text (UGC) from ids where possible.
#. **Honor deletion** — prefer RID-keyed storage so severed mappings do the work.
#. **Gate expensive/gated sources** (impressions, ``post_events``) behind
   explicit opt-in + entitlement checks.
