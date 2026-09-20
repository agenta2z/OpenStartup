========================================
Online Collection: DataFM / AUS
========================================

.. contents::
   :local:
   :depth: 2

The **online** collection pattern reads a user's pre-aggregated engagement
*sequence* from ZippyDB via **DataFM / AUS**, in single-digit milliseconds,
keyed by **RID**. The canonical entry point is
``fbcode/mrs/rankevolve/ARS/memory_os/nodes/ingest/datafm_adapter.py``. Everything
here is VERIFIED against code unless marked otherwise.


The entry-point adapter
=======================

``DataFMPybindAdapter`` (the production ``DataFMAdapter`` implementation) reads
AUS traits from ZippyDB through the ``datafm_pybind`` C++/pybind11 extension:

.. code-block:: python

   class DataFMPybindAdapter:
       def __init__(self, aus_use_case_id: int = 577) -> None:
           self._aus_use_case_id = aus_use_case_id

       async def fetch(self, viewer_rid: str, window_days: int) -> dict[str, list[int]]:
           import multifeed.datafm.tools.datafm_pybind as datafm
           rid = int(viewer_rid)
           end_ts = int(time.time())
           start_ts = end_ts - (window_days * 86400)
           loop = asyncio.get_running_loop()
           result = await loop.run_in_executor(
               None,
               datafm.multi_fetch_datafm_feature,
               self._aus_use_case_id,
               [rid],
               2,            # fetch_mode: BOTH (AUS_LIST + AUS_ROW merged)
               start_ts, end_ts,
           )
           return result.get(rid, {})

Design choices, decoded:

* **``fetch_mode = BOTH (2)``** returns the full **AUS_LIST** (immutable,
  daily-compacted history) **merged with** recent **AUS_ROW** (mutable). It
  deliberately replaced ``scan_aus_row_data`` (AUS_ROW-only → "a handful of
  events since last compaction") so the LLM summarizer sees the *whole* history
  (diff **D104460408**).
* **``viewer_rid`` is a RID**, not an FBID; ZippyDB AUS is RID-keyed. Callers
  resolve FBID→RID upstream (:doc:`identifiers_and_joins`).
* **``run_in_executor``** offloads the blocking ``folly::coro::blockingWait``
  inside the pybind so the async event loop is not stalled.
* **Return** is a columnar ``dict[str, list[int]]``: ``XLogEventTraitID`` name →
  per-event array, index-aligned to the ``SERVER_TIME`` spine
  (:doc:`event_taxonomy`).


The AUS storage model
=====================

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Concept
     - Definition (VERIFIED)
   * - **AUS**
     - "Aggregated User Sequence(s)" — the ``multifeed/datafm`` implementation.
       (One IFR wiki says "Aggregated User *Storage*"; naming is inconsistent
       internally.)
   * - **DataFM**
     - The user-history infrastructure over AUS. Authoritative wiki expands it
       *"Data for Future Modeling"* — **not** "Data Feature Materialization"
       (a wrong guess to avoid).
   * - **AUS_ROW (0)**
     - Mutable, real-time rows written from the XLog tailer; entrepot-cached.
   * - **AUS_LIST (1)**
     - Immutable, daily-compacted columnar ``AusLists``; memcached. One row per
       Pacific day.
   * - **Compaction**
     - Daily (``kAusListCompactionWindow = 24h``); ``getCompactionWindowStartTS``
       snaps to start-of-day PT.

Fetch modes (``AusFetchMode``, ``configerator/structs/multifeed/aus/aus_reader.thrift``):

.. code-block:: thrift

   enum AusFetchMode {
     ONLY_MUTABLE = 0,             // recent AUS_ROW only
     ONLY_IMMUTABLE = 1,           // compacted AUS_LIST only
     BOTH = 2,                     // merged  ← the adapter uses this
     ONLY_CACHABLE_MUTABLE = 3,
     BOTH_WITH_CACHABLE_MUTABLE = 4,
   }

``BOTH`` merges immutable lists + mutable rows with **day-window dedup**
(``AusMerger``): mutable rows whose compaction-day ≤ the last immutable list's day
are skipped, keeping the immutable aggregate authoritative.

.. warning::

   Two known stubs/labels are wrong (do not be misled): the ``datafm_pybind.pyi``
   stub names the param ``viewer_rid`` but the real pybind kwarg is
   ``viewer_rids`` (and the real return is ``dict[int, dict[str, list[int]|str]]``,
   not ``dict[int, AusLists]``); and ``AusClientCLI.cpp`` mislabels
   ``fetch_mode=0`` as "immutable" — the thrift enum (``ONLY_MUTABLE=0``) is
   authoritative.


pybind API
==========

``multifeed/datafm/tools/DataFMPyBind.cpp`` (VERIFIED):

.. code-block:: python

   # kwargs: usecase_id, viewer_rids, fetch_mode, start_ts, end_ts
   multi_fetch_datafm_feature(usecase_id, viewer_rids, fetch_mode, start_ts=0, end_ts=2**63-1)
       -> dict[int, AusLists]   # runtime: {rid: {trait_name: [per-event values]}}

   scan_aus_row_data(usecase_id, viewer_rids, start_ts=0, end_ts=2**63-1)
       -> dict[int, dict[str, list[int]]]   # AUS_ROW only (the replaced path)

Use-case registry: ``configerator/.../entrepot/v2/entrepot_unique_ids.thrift``
maps ``hstu_v2_fb_public = 577`` (and the others in
:doc:`data_sources_catalog`). ``577 = fb_public`` is the ``datafm_adapter``
default.


End-to-end ARS ingest flow
==========================

The adapter is one step of the ARS "Memory OS" engagement-summary pipeline:

.. mermaid::

   sequenceDiagram
     participant WWW as WWW Watch Feed
     participant H as MemoryServiceHandler
     participant P as EngagementSummaryPipeline
     participant D as DataFM (ZippyDB AUS)
     participant L as LLM
     participant Z as ZippyDB (memory)
     participant PL as recsys planner → Laser
     WWW->>H: refreshEngagementSummary(viewer_rid, viewer_fbid, aus_use_case_id, data_window_days) [oneway]
     H->>P: run(viewer_rid), enrichers=[FeedObjectType, Group]
     P->>D: fetch() × 7 use cases (574/577/611/644/658/698/750) in parallel
     D-->>P: columnar trait dicts
     P->>P: merge + _format_engagement (NUM_LIKE/COMMENT/SHARE, weekday split)
     P->>L: ENGAGEMENT_SUMMARY_PROMPT (100-200w)
     L-->>P: NL summary
     P->>Z: store EngagementSummaryMemory ("{rid}:engagement_summary")
     H->>PL: plan_user(viewer_fbid) → per-user MezQL/Shots overrides

Notes: the handler receives the **RID already resolved**; the production factory
builds one ``DataFMPybindAdapter`` **per use case** and fans out all 7 in
parallel (the ``577`` ctor default is effectively dead on this path). The stored
``EngagementSummaryMemory.aus_use_case_id`` is a single scalar even though data is
merged across all 7 — true contributors are in
``summary_metadata["contributing_use_cases"]``.


When to use online collection
=============================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Use online (DataFM/AUS) when…
     - Use offline (Hive) instead when…
   * - You need per-user context at **serving time** (ms latency)
     - You are building a **training / eval dataset** over many users
   * - You want the **pre-aggregated, CU-enriched** sequence
     - You need **free text** (captions/comment bodies) and full fidelity
   * - You already have (or can cheaply resolve) the **RID**
     - You are working in **IGID/FBID** space and exploring
   * - You want infra-owned, low-cost reads
     - You can afford large partitioned scans

.. seealso::

   Reads are keyed by RID — see the FBID→RID chain (and the write-side
   ``RidBackfillService`` caveat) in :doc:`identifiers_and_joins`. The trait
   vocabulary returned is catalogued in :doc:`event_taxonomy`.
