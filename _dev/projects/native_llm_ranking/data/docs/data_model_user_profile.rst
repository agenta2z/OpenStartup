==================================
Data Model: The User Profile
==================================

.. contents::
   :local:
   :depth: 2

This chapter defines **what a "detailed user profile" is** for LLM-native
recommendation, grounded in the production ARS "Memory OS" model, and proposes a
concrete **collection schema** mapped to the sources in
:doc:`data_sources_catalog`.


Grounding: the ARS Memory OS model
==================================

ARS represents a user not as one object but as a small set of ``MemoryItem``
rows keyed by ``user_id``/``entity_id``, persisted to ZippyDB. The concrete
Pydantic models live in ``fbcode/mrs/rankevolve/ARS/core/models/`` with a Thrift
mirror in ``production/memory_os/if/memory_service.thrift``. All schemas below
are **VERIFIED** (quoted from those files).

.. important::

   The "L0/L1/L2" tier names are **ARS design-doc labels**, not production class
   names (``core/memory/tiers/`` is an empty ``__init__.py``). They map onto the
   real classes as: **L0 = EventMemory**, **L1 = PreferenceMemory**,
   **L2 = ProfileMemory**. ``EngagementSummaryMemory`` is a *separate* artifact
   (see :ref:`engagement summary vs. profile <profile-vs-summary>`).

Base type — every memory subclasses ``MemoryItem`` (``core/models/memory.py``):

.. code-block:: python

   memory_id: str = ""          # "{entity_id}:{uuid4}" (bare UUIDs rejected)
   entity_id: str
   memory_type: str = "base"
   content: str = ""
   created_at: float
   updated_at: float
   metadata: dict[str, Any]

L0 — ``EventMemory`` (raw engagement event)
-------------------------------------------

``core/models/event_memory.py`` — one row per interaction:

.. code-block:: python

   memory_type = "event"
   user_id: str
   session_id: str
   event_ts: int                 # epoch seconds
   event_weekday: int            # 0=Mon..6=Sun (auto from event_ts)
   event_type: str               # e.g. "click"/"view"/"like"/"ember_feed_*"
   event_description: str
   event_metadata: dict[str, Any]

L1 — ``PreferenceMemory`` (distilled preference)
------------------------------------------------

``core/models/preference_memory.py`` — LLM-distilled, one per preference:

.. code-block:: python

   memory_type = "preference"
   user_id: str
   preference_ts: int
   topic: str
   preference_type: str          # interest|content_type|creator|topic_query|general
   preference_description: str
   preference_metadata: dict     # polarity, strength(-1..1), confidence(0..1),
                                 # evidence_count, search_queries, prefer_weekday,
                                 # prefer_time, ttl_days, update_source, visible_to_user

L2 — ``ProfileMemory`` (synthesized profile)
--------------------------------------------

``core/models/profile_memory.py`` — the finished user representation:

.. code-block:: python

   memory_type = "profile"
   user_id: str
   profile_ts: int
   demographics: dict[str, Any]          # age/gender/loc/lang + user_interests
   profile_description: str              # the 150-300 word NL narrative
   profile_metadata: dict[str, Any]      # potential_interests, counters, ...
   top_interests: list[str]
   persona_tags: list[str]               # snake_case archetypes, e.g. "news_junkie"
   last_updated: int

The **structured profile schema** enforced at generation
(``core/memory/profile_updater.py::_PROFILE_SCHEMA``, VERIFIED) requires:
``profile_description`` (str), ``potential_interests`` (3–5 × ``{topic, reason,
confidence}``), ``persona_tags`` (3–5), ``top_interests`` (3–10), and
``user_interests`` (3–20 context-rich labels, e.g. *"Lacrosse in Philadelphia"*).
The narrative prompt (``PROFILE_UPDATE_PROMPT``) specifies *a single coherent
150–300 word third-person paragraph … actionable for content recommendation.*

``EngagementSummaryMemory`` (DataFM summary)
--------------------------------------------

``core/models/engagement_summary_memory.py`` — a singleton per user
(``memory_id = "{user_id}:engagement_summary"``), where **``user_id`` is a RID**:

.. code-block:: python

   memory_type = "engagement_summary"
   user_id: str                  # a DataFM RID, NOT an FBID
   summary: str                  # 100-200 word NL summary of numeric engagement
   summary_ts: int
   data_window_days: int = 30
   aus_use_case_id: int
   event_count: int
   summary_metadata: dict        # contributing_use_cases, ...

Event / action types
--------------------

There is **no formal enum**; ``event_type`` is validated by string rules
(``core/memory/updater_types.py::is_valid_event_type``, VERIFIED): any
``ember_feed_*`` prefix, ``ember_chat`` (fires an immediate preference update,
*not* persisted/counted), ``bio_interest``, ``ember_post_create``. Cold-start
adds ``STATIC_EVENT_TYPES = {"ember_feed_join", "bio_interest"}`` with synthetic
``event_ts=0``. Maintenance thresholds: ``PREF_UPDATE_INTERVAL=20`` events →
re-distill preferences; ``PROFILE_UPDATE_INTERVAL=100`` → re-synthesize profile;
``MAX_EVENT_QUEUE_SIZE=80`` → event eviction.


How the profile is built
========================

Two distinct pipelines feed the representation — keep them separate:

.. mermaid::

   flowchart TB
     subgraph P1["Pipeline 1: events → preferences → profile (FBID-keyed)"]
       EV["addEvent / addEventBatch"] --> EM["EventMemory (L0)"]
       EM -->|every 20 events| PM["PreferenceMemory (L1)"]
       PM -->|every 100 events| PR["ProfileMemory (L2)<br/>150-300w narrative + tags + interests"]
     end
     subgraph P2["Pipeline 2: DataFM → engagement summary (RID-keyed)"]
       AUS["AUS sequences (7 use cases)"] --> ES["EngagementSummaryMemory<br/>100-200w summary"]
       ES --> PLAN["recsys planner → Laser overrides"]
     end

.. _profile-vs-summary:

.. warning::

   **The engagement summary is NOT the profile.** ``EngagementSummaryMemory`` is
   DataFM-derived, **RID-keyed**, and feeds the *planner*.
   ``ProfileMemory`` is preference-derived, **FBID-keyed**, and feeds
   ranking/demographics. They are distinct rows built by distinct pipelines.
   (A common confusion — flagged here because it changes which id space and
   which source you collect from.)


Proposed collection schema
==========================

For this project, collect a user record with four blocks. Each field cites the
**source table** (from :doc:`data_sources_catalog`) so the schema is directly
buildable. Adapt per surface (IG/FB/Threads).

**1. Identity & profile metadata**

.. list-table::
   :header-rows: 1
   :widths: 34 30 36

   * - Field(s)
     - Source
     - Notes
   * - user id (IGID / FBID / RID)
     - ``dim_ig_users`` / ``bi.dim_all_users`` / ``dim_ig_fbid_to_rid``
     - resolve all three up front (:doc:`identifiers_and_joins`)
   * - tenure, activity (``reg_ds``, L28/L7)
     - ``dim_ig_users`` (IG), ``bi.dim_all_users`` (FB)
     - drives cohorting (cold/marginal/active)
   * - demographics (gender, age, country, locale)
     - ``dim_ig_users`` / ``bi.dim_all_users``
     - privacy-sensitive; see :doc:`privacy_and_retention`
   * - account flags (private, creator, business, AI-agent)
     - ``dim_ig_users``
     -
   * - follow graph (following / followers)
     - ``dim_instagram_follow_graph_partitioned``
     - optional; large

**2. Authored history (user as creator)**

.. list-table::
   :header-rows: 1
   :widths: 34 30 36

   * - Field(s)
     - Source
     - Notes
   * - posts / media authored
     - ``dim_instagram_media_v2_unrestricted(_partitioned)``
     - ``user_id`` (author, IG_FBID_V2) + ``fbid``/``ig_id`` + type + ts
   * - post caption text
     - ``dim_instagram_media_caption`` (join on ``media_id = fbid``)
     - ~5-day retention — collect promptly
   * - comments & replies authored
     - ``dim_instagram_comment_v2``
     - ``text`` + ``parent_comment_id``/``replied_to_comment_id`` (tree)
   * - Threads posts / replies
     - ``dim_threads_media``
     - reply/quote/repost parents via ``*_media_fbid``
   * - FB posts authored
     - ``measurementsystems.content_actions`` (``action_type='create'``)
     - ``text`` present; ``post_events_unsessionized`` for full detail (UDP-gated)

**3. Engagement history (user as consumer)**

.. list-table::
   :header-rows: 1
   :widths: 34 30 36

   * - Field(s)
     - Source
     - Notes
   * - interactions (like/comment/share/save/follow/hide…)
     - ``fct_ig_all_interactions`` (IG) / ``feed.fct_feed_interactions`` (FB)
     - carries ``is_passive``, ``delivery_class``, sentiment inputs
   * - impressions + dwell
     - ``ig_impression_events_inc_archive``
     - **expensive**; opt-in, single-day, partition-filtered
   * - engaged-content text
     - ``dim_instagram_media_caption`` / ``..._hashtag`` (join on ``post_fbid``)
     - the *content* the user engaged with
   * - aggregated online sequence
     - AUS use cases (577 fb / 658 ig / …)
     - pre-aggregated per-event traits; see :doc:`event_taxonomy`

**4. Derived / natural-language layer**

.. list-table::
   :header-rows: 1
   :widths: 34 30 36

   * - Field(s)
     - Source
     - Notes
   * - NL user profile / interests
     - ``biography_prompts_inc_archive`` / ``biography_interests_for_meta_ai``
     - reuse Biography rather than regenerate (:ref:`biography-as-profile`)
   * - content-understanding labels (topics/entities/sentiment)
     - InterestFM (``interest_fm_api_logs_inc_archive``) + AUS CU traits
     - enriches events with *what the content is about*
   * - profile narrative / preferences / persona tags
     - (generated) — model on ARS ``ProfileMemory`` schema above
     - your LLM step; the ARS schema is the reference target

.. tip::

   Whether you build blocks 1–3 raw and generate block 4, or shortcut block 4 by
   reading Biography, depends on how much schema control you need. The
   ``biography_prompts_inc_archive.uih_*`` arrays are an excellent reference for
   how to serialize block 3 (historical events) into an LLM prompt.
