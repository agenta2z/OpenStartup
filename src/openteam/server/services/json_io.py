"""Shared JSON I/O + argument-normalization helpers.

Factored out of :mod:`openteam.server.services.session_store` so the same
durable-write primitive backs both ``session_state.json`` (SessionStore) and
the per-workspace ``task_meta.json`` sidecars (ToolDispatcher), and so the
task-key value normalization is defined once and shared between the dispatcher
(key construction) and the reuse matcher.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_atomic(path: str | Path, data: Any) -> None:
    """Write ``data`` as JSON to ``path`` atomically (tmp file + ``os.replace``).

    The temp file is created in the target's parent directory so ``os.replace``
    is a same-filesystem rename (atomic). On any failure the temp file is
    removed and the exception re-raised; the destination is never left
    half-written. Output is ``indent=2, ensure_ascii=False`` with a trailing
    newline — matching ``SessionStore._atomic_write``.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=".json_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def normalize_arg_value(value: Any, arg_type: str = "string") -> str:
    """Normalize a tool primary-arg value for stable task-key comparison.

    - ``arg_type == "path"``: ``str(Path(v).expanduser().resolve())`` — collapses
      the ``~/fbsource/...`` vs ``/home/<user>/fbsource/...`` divergence and any
      relative/symlinked form to one canonical absolute path.
    - otherwise: ``str(v).strip()``.

    ``None`` / empty → ``""`` so an absent primary arg yields no key component.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if arg_type == "path":
        try:
            return str(Path(text).expanduser().resolve())
        except (OSError, RuntimeError, ValueError):
            return text
    return text


def primary_val_from_args(
    args: dict[str, Any],
    primary_arg: str | bool | None,
    arg_type: str = "string",
) -> str:
    """Compute the normalized primary-arg VALUE for a tool's SOP-scoped task key.

    One canonical 3-way rule, shared by the dispatcher (live key construction in
    ``ToolDispatcher._dispatch_as_task``) and the backfill/recovery path
    (``SessionStore._targets_from_response``, reconstructing keys for pre-feature
    workspaces) so the two can NEVER diverge — a divergence here silently breaks
    task reuse (a freshly-backfilled sidecar keying differently from the live
    dispatch → no match → a duplicate run):

    - ``primary_arg is False`` (the ``"primary_arg": null`` opt-out) → ``raw =
      None``, with **NO ``request`` fallback**: key on ``sop/phase/tool`` only.
      The ``request`` is orchestrator-generated and volatile (different wording
      every replay), so keying on it could never match a prior run — opt-out is
      the intended design (e.g. ``research_propose``).
    - ``primary_arg`` is a non-empty ``str`` → ``raw = args[primary_arg]`` when
      present, else ``args["request"]`` (e.g. ``understand_codebase`` → its
      stable ``target`` path).
    - ``primary_arg is None`` (unresolved) → ``raw = args["request"]``.

    then :func:`normalize_arg_value` (maps ``None`` / empty → ``""``).
    """
    if primary_arg is False:
        raw: Any = None
    elif primary_arg:
        raw = args.get(primary_arg)
        if raw is None:
            raw = args.get("request")
    else:
        raw = args.get("request")
    return normalize_arg_value(raw, arg_type)
