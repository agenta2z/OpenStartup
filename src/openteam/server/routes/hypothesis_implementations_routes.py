# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST route backing the ``useHypothesisImplementations`` React hook
(mounted by the Selection tab's pre-selected banner + the autopilot gate).

Ported from RankEvolve ``hypothesis_implementations_routes.py`` — thin
transport adapter over the AF ``hypothesis_implementations_routes_service``.

Mount prefix: ``/api/hubs`` (NOTE: different from the other hub routers'
``/api/sessions/{session_id}/…`` prefix — matches the FE URL shape
``GET /api/hubs/{multi_task_id}/hypothesis_implementations?session_id=…``).
"""

from __future__ import annotations

import logging
from typing import Any

from agent_foundation.experiment_hub import hypothesis_implementations_routes_service
from fastapi import APIRouter, HTTPException, Query, Request
from openteam.server.routes._hub_routes_common import resolve_session_dir

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{multi_task_id}/hypothesis_implementations")
async def get_hypothesis_implementations(
    request: Request,
    multi_task_id: str,
    session_id: str = Query(...),
    ids: str | None = Query(None),
) -> dict[str, Any]:
    """Return per-hypothesis implementation status for a hub.

    When ``ids`` is supplied (comma-separated H-ids), the response includes
    explicit ``{implemented: false, basis: "no_evidence"}`` entries for any
    listed Hk lacking evidence — useful for side-panel badge rendering.
    """
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await hypothesis_implementations_routes_service.get_hypothesis_implementations(
            session_dir=session_dir,
            multi_task_id=multi_task_id,
            ids=ids,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
