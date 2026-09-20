# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST routes backing the ``useComboOverrides`` React hook + the
``postCombosApply`` helper (from ``HUB/utils/applyHelpers.js``).

Ported from RankEvolve ``combo_overrides_routes.py`` — thin transport
adapter over the AF ``combo_overrides_service`` (session-dir signatures).

Mount prefix: ``/api/sessions`` — every route path below is prefixed with
``/{session_id}/combo_overrides/{multi_task_id}``.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_foundation.experiment_hub import combo_overrides_service
from fastapi import APIRouter, HTTPException, Request
from openteam.server.routes._hub_routes_common import resolve_session_dir

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{session_id}/combo_overrides/{multi_task_id}")
async def get_combo_overrides(
    request: Request, session_id: str, multi_task_id: str
) -> dict[str, Any]:
    """Return this hub's active_combos slice (with inflated applyState +
    flag-map legacy warning). Empty when nothing applied yet."""
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await combo_overrides_service.get_combo_overrides(
            session_dir, multi_task_id
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{session_id}/combo_overrides/{multi_task_id}/apply")
async def apply_combo_overrides(
    request: Request, session_id: str, multi_task_id: str
) -> dict[str, Any]:
    """Replace the active combos for this hub. Body:
    ``{"combos": [...], "source_archive_id"?: str, "applied_by"?: str}``.

    ``emit_event`` intentionally omitted — the FE listens on the
    ``combo_overrides_changed`` WS event via a separate broadcast path in
    the OT WS server (mirrors how proposal_overrides work today).
    """
    body = await request.json()
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await combo_overrides_service.apply_combo_overrides(
            session_id=session_id,
            session_dir=session_dir,
            multi_task_id=multi_task_id,
            body=body,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{session_id}/combo_overrides/{multi_task_id}/revert_last")
async def revert_last_combo_overrides(
    request: Request, session_id: str, multi_task_id: str
) -> dict[str, Any]:
    """Undo the most recent apply_combos for this hub. Submissions are
    NOT deleted (run history is an invariant); auto-added combos are
    marked ``inactive_since``."""
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await combo_overrides_service.revert_last_combo_apply(
            session_id=session_id,
            session_dir=session_dir,
            multi_task_id=multi_task_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
