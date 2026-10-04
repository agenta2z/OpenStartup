# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""Shared dependency-resolution helpers for hub REST routers.

The AF `experiment_hub/*_service.py` modules were factored to take an
explicit ``session_dir: Path`` (plus a ``session_id: str`` for per-session
lock keys) so the router layer stays a thin adapter that resolves
``app.state.data_service.session_store`` first, then delegates.

Every hub-related router (proposal_overrides, combo_overrides, learnings,
hypothesis_implementations) must resolve id→dir the same way; this module
factors that out so the routers themselves stay purely transport.

Pattern (mirrors ``experiment_hub_routes._session_store``):
  1. Resolve SessionStore off ``app.state.data_service`` (503 if absent —
     mock mode has none).
  2. Ask it for ``get_session_dir(session_id)`` (404 if the id is unknown).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

logger: logging.Logger = logging.getLogger(__name__)


def session_store(request: Request) -> Any:
    """Return the SessionStore or raise 503 (mock mode)."""
    svc = getattr(request.app.state, "data_service", None)
    store = getattr(svc, "session_store", None)
    if store is None:
        raise HTTPException(503, "Session store not available (mock mode?)")
    return store


def resolve_session_dir(request: Request, session_id: str) -> Path:
    """Resolve ``session_id`` → on-disk ``session_dir`` (Path). 404 if unknown.

    All hub sidecars (proposal_overrides.json, combos/current.json,
    accumulated_learnings.md, hub_<mid>_*.json) live under this directory.
    """
    store = session_store(request)
    try:
        return Path(store.get_session_dir(session_id))
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(404, f"Unknown session: {session_id}") from exc
    except Exception as exc:  # noqa: BLE001 — surface unexpected as 503
        raise HTTPException(503, f"Session store error: {exc}") from exc
