# ---------------------------------------------------------------------------
# REFERENCE COPY — provenance artifact, not part of this project's runtime.
# Source: fbcode/mrs/rankevolve/ARS/memory_os/nodes/ingest/datafm_adapter.py
# URL:    https://www.internalfb.com/code/fbsource/fbcode/mrs/rankevolve/ARS/memory_os/nodes/ingest/datafm_adapter.py
# Captured verbatim 2026-07-15 via knowledge_load. Analyzed in
# ../online_collection_datafm_aus.rst. Re-fetch from source before relying on it.
# ---------------------------------------------------------------------------

# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.
# pyre-strict

"""DataFMPybindAdapter — production adapter using datafm_pybind C++ extension.

Reads user engagement data from ZippyDB via the datafm_pybind C++ pybind11
extension. Uses multi_fetch_datafm_feature with fetch_mode=BOTH (2) to read
the full historical AUS_LIST (compacted) + AUS_ROW (recent mutable) data,
merged into a single sequence. scan_aus_row_data only reads un-compacted
AUS_ROW entries (typically a handful of events since the last compaction
cycle), missing the bulk of the user's history.

Uses run_in_executor to avoid blocking the async event loop
(datafm_pybind internally uses folly::coro::blockingWait).
"""

from __future__ import annotations

import asyncio
import logging
import time

logger: logging.Logger = logging.getLogger(__name__)


class DataFMPybindAdapter:
    """Fetches raw AUS trait data via datafm_pybind."""

    def __init__(self, aus_use_case_id: int = 577) -> None:
        self._aus_use_case_id: int = aus_use_case_id

    async def fetch(self, viewer_rid: str, window_days: int) -> dict[str, list[int]]:
        """Fetch full AUS engagement data for a viewer.

        Uses multi_fetch_datafm_feature with fetch_mode=2 (BOTH) to read
        compacted AUS_LIST history merged with recent AUS_ROW events.

        viewer_rid: a DataFM Replacement ID as an integer-formatted string
            (e.g. "545114654589218"). NOT an FBID — callers must convert
            FBID → RID upstream. datafm_pybind requires int RIDs for
            ZippyDB lookups.
        """
        import multifeed.datafm.tools.datafm_pybind as datafm

        rid: int = int(viewer_rid)
        end_ts: int = int(time.time())
        start_ts: int = end_ts - (window_days * 86400)

        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            datafm.multi_fetch_datafm_feature,
            self._aus_use_case_id,
            [rid],
            2,  # fetch_mode: BOTH (AUS_LIST + AUS_ROW merged)
            start_ts,
            end_ts,
        )
        # pyre-ignore[7]: AusLists is structurally dict[str, list[int]]
        return result.get(rid, {})
