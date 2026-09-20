# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST routes backing the ``AccumulatedLearningsDrawer`` React drawer
(``useArchiveCount``, drawer's inline fetches).

Ported from RankEvolve ``learnings_routes.py`` — thin transport adapter over
the AF ``learnings_routes_service`` (session-dir signatures; real method
names: ``get_learnings``, ``regenerate_learnings``, ``list_learnings_archives``,
``get_learnings_archive``, ``restore_learnings_archive``).

Mount prefix: ``/api/sessions`` — every route below prefixed with
``/{session_id}/learnings``.

**G9 restore semantics**: ``restore_learnings_archive`` raises ``RuntimeError``
when the env flag ``RANKEVOLVE_LEARNINGS_RESTORE_ENABLED`` is unset (RankEvolve
feature gate). The router propagates that as HTTP 501 so the drawer's
``handleRestoreFromArchive`` handler surfaces a "feature-gated" message to the
user. Setting the env var flips the endpoint to a real restore.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_foundation.experiment_hub import learnings_routes_service
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from openteam.server.routes._hub_routes_common import resolve_session_dir

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{session_id}/learnings")
async def get_learnings(request: Request, session_id: str) -> dict[str, Any]:
    """Return the accumulated_learnings.md split into body + actions.
    ``exists: False`` when no doc has been generated yet."""
    session_dir = resolve_session_dir(request, session_id)
    return await learnings_routes_service.get_learnings(session_dir)


@router.post("/{session_id}/learnings/regenerate")
async def regenerate_learnings(request: Request, session_id: str) -> dict[str, Any]:
    """Recompute the doc + JSON action fence (heavy I/O; runs in thread)."""
    session_dir = resolve_session_dir(request, session_id)
    return await learnings_routes_service.regenerate_learnings(
        session_id=session_id, session_dir=session_dir
    )


@router.get("/{session_id}/learnings/archives")
async def list_learnings_archives(request: Request, session_id: str) -> dict[str, Any]:
    """Return the versioned archive index (newest first, committed only)."""
    session_dir = resolve_session_dir(request, session_id)
    return await learnings_routes_service.list_learnings_archives(session_dir)


@router.get(
    "/{session_id}/learnings/archives/{archive_id}", response_class=PlainTextResponse
)
async def get_learnings_archive(
    request: Request, session_id: str, archive_id: str
) -> str:
    """Return one archived accumulated_learnings.md verbatim as text/markdown."""
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await learnings_routes_service.get_learnings_archive(
            session_dir, archive_id
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{session_id}/learnings/restore/{archive_id}")
async def restore_learnings_archive(
    request: Request, session_id: str, archive_id: str
) -> dict[str, Any]:
    """Restore an archive into LIVE. Feature-gated — returns 501 unless
    ``RANKEVOLVE_LEARNINGS_RESTORE_ENABLED=1``."""
    session_dir = resolve_session_dir(request, session_id)
    try:
        return await learnings_routes_service.restore_learnings_archive(
            session_id=session_id,
            session_dir=session_dir,
            archive_id=archive_id,
        )
    except RuntimeError as exc:
        # Env-gate off — FE handleRestoreFromArchive surfaces this to the user.
        raise HTTPException(501, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, f"Archive not found: {archive_id}") from exc
