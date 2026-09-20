"""Workspace path-completion endpoint for the OpenStartup server.

Mounts ``GET /api/workspace/path-complete`` so the React UI can drive a path
autocomplete widget. Delegates the filesystem listing to the shared
:func:`agent_foundation.common.workspace.path_completion.complete_path` helper,
which is the single source of truth for containment and listing logic.

Security: autocomplete is convenience, not authorization. The ``prefix`` is
constrained to live under the session working directory / allowed root
(``ConversationService._working_dir``, else ``OPENTEAM_WORKING_DIR``, else
``~/MyProjects``). Prefixes outside that root are rejected with HTTP 403 using
``Path.resolve().relative_to(...)`` containment (no string ``startswith``).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from agent_foundation.common.workspace.path_completion import (
    complete_path,
    PathContainmentError,
    PrefixNotADirectory,
)
from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


def _allowed_root(request: Request) -> Path:
    """Resolve the allowed root the ``prefix`` must stay within.

    Prefers the live ConversationService working dir (its ``session_root_path``
    source), falling back to the ``OPENTEAM_WORKING_DIR`` env var, then
    ``~/MyProjects`` — matching ``server/main.py``'s default.
    """
    svc = getattr(request.app.state, "conversation_service", None)
    working_dir = getattr(svc, "_working_dir", None) if svc is not None else None
    if not working_dir:
        working_dir = os.environ.get(
            "OPENTEAM_WORKING_DIR", str(Path.home() / "MyProjects")
        )
    return Path(working_dir).resolve()


@router.get("/path-complete")
async def path_complete(
    request: Request,
    prefix: str = Query(..., description="Base directory path"),
    partial: str = Query("", description="User's partial path input"),
    dirs_only: bool = Query(True, description="Only return directories"),
    limit: int = Query(50, description="Max suggestions"),
) -> dict[str, Any]:
    """List subdirectories/files for path autocomplete within the session root.

    Joins prefix + partial to find the deepest valid directory, then lists its
    children that match the remaining partial name fragment.
    """
    # Constrain the prefix to the allowed root before touching the filesystem.
    root = _allowed_root(request)
    try:
        Path(prefix).resolve().relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Access denied — prefix is outside the session root",
        )
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid path")

    try:
        return complete_path(prefix, partial, dirs_only=dirs_only, limit=limit)
    except PrefixNotADirectory:
        raise HTTPException(
            status_code=404, detail=f"Prefix directory not found: {prefix}"
        )
    except PathContainmentError:
        raise HTTPException(status_code=403, detail="Path traversal blocked")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")


@router.get("/file")
async def get_workspace_file(
    request: Request,
    workspace: str = Query(..., description="Absolute workspace directory path"),
    path: str = Query(..., description="Relative path within the workspace"),
) -> dict[str, Any]:
    """Read a single file under a workspace directory as UTF-8 text.

    Backs ``QueueProgressView``'s ``LazyWorkspaceMarkdown`` accordions
    (summary.md, outputs/round0_plan.md, outputs/round0_implementation.md).

    Security: reuses the same allowed-root containment guard as
    ``/path-complete``. Two enforcement layers:
      (1) ``workspace`` must resolve within the allowed root.
      (2) ``workspace + path`` must resolve within ``workspace`` (blocks
          ``../`` traversal out of the intended workspace subtree).

    Only ``/tree``, ``/outputs``, ``/results`` remain unmounted (YAGNI —
    no live component consumer today; add when one lands).
    """
    root = _allowed_root(request)
    try:
        abs_ws = Path(workspace).resolve()
        abs_ws.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="workspace outside allowed root")
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid workspace path")

    try:
        target = (abs_ws / path).resolve()
        target.relative_to(abs_ws)
    except ValueError:
        raise HTTPException(status_code=403, detail="path escapes workspace")
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"{path} not found")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Read failed: {exc}") from exc

    return {"content": content}
