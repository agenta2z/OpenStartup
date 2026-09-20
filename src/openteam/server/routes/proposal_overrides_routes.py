# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST routes backing the ``useProposalOverrides`` React hook + the
``postRerankApply`` helper (from ``HUB/utils/applyHelpers.js``).

Ported from RankEvolve ``proposal_overrides_routes.py`` — thin transport
adapter over the AF ``proposal_overrides_service`` (session-dir signatures).

Mount prefix: ``/api/sessions`` — every route path below is prefixed with
``/{session_id}/proposal_overrides``.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_foundation.experiment_hub import proposal_overrides_service
from fastapi import APIRouter, HTTPException, Request
from openteam.server.routes._hub_routes_common import resolve_session_dir

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{session_id}/proposal_overrides")
async def get_proposal_overrides(request: Request, session_id: str) -> dict[str, Any]:
    """Return the per-session proposal-overrides sidecar (empty if absent)."""
    session_dir = resolve_session_dir(request, session_id)
    return await proposal_overrides_service.get_overrides(session_dir)


@router.post("/{session_id}/proposal_overrides")
async def upsert_proposal_overrides(
    request: Request, session_id: str
) -> dict[str, Any]:
    """Merge caller-supplied rerank + deprioritize into the sidecar. Body:
    ``{"rankings": [...], "deprioritize": [...]}``."""
    body = await request.json()
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await proposal_overrides_service.upsert_overrides(
            session_id=session_id, session_dir=session_dir, body=body
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{session_id}/proposal_overrides/revert_last")
async def revert_last_proposal_apply(
    request: Request, session_id: str
) -> dict[str, Any]:
    """Undo the most recent apply_rerank. Idempotent-safe: returns
    ``{"ok": False, "reason": "no overrides on disk"}`` when nothing to revert."""
    session_dir = resolve_session_dir(request, session_id)
    return await proposal_overrides_service.revert_last_apply(
        session_id=session_id, session_dir=session_dir
    )
