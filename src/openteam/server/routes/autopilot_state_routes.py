# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST route backing the ``useAutopilot`` hook's write-through state mirror.

Ported from RankEvolve ``autopilot_state_routes.py`` — thin transport adapter
over the AF ``autopilot_state_service``. The autopilot state machine runs
client-side; this route is a best-effort mirror for cross-reload persistence
(client-only autopilot is functional without it — failures here are non-fatal).

Mount prefix: ``/api/sessions`` — route path prefixed with
``/{session_id}/_hub/autopilot/state``.

**Co-lands with G6** — without ``useAutopilot`` mounted in Selection footer
(the G6 change to ``HUB/views/SelectionView.js``), this endpoint has no live
caller. It's mounted anyway so G6 can land in a follow-up commit without
requiring a separate router-registration step.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_foundation.experiment_hub import autopilot_state_service
from fastapi import APIRouter, HTTPException, Request
from openteam.server.routes._hub_routes_common import resolve_session_dir

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{session_id}/_hub/autopilot/state")
async def get_autopilot_state(request: Request, session_id: str) -> dict[str, Any]:
    """Read the most-recent autopilot state mirror. Returns
    ``{multi_task_id: null, state: null, mirroredAt: null}`` if none exists yet."""
    session_dir = resolve_session_dir(request, session_id)
    return await autopilot_state_service.get_autopilot_state(session_dir)


@router.post("/{session_id}/_hub/autopilot/state")
async def upsert_autopilot_state(request: Request, session_id: str) -> dict[str, Any]:
    """Mirror the client-side autopilot state. Body:
    ``{multi_task_id: str | null, state: dict}``. Client owns the schema."""
    body = await request.json()
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await autopilot_state_service.upsert_autopilot_state(
            session_id=session_id, session_dir=session_dir, body=body
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
