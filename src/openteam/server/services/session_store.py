"""SessionStore — file-based persistent session store with runtime server structure.

Runtime hierarchy (adapted from rankevolve):
    <runtime_root>/
    ├── servers/
    │   ├── server_<YYYYMMDD_HHMMSS>_<uuid8>/       ← current server
    │   │   ├── server_info.json                     ← server metadata
    │   │   └── sessions/
    │   │       ├── sessions_index.json              ← fast listing cache
    │   │       ├── <session_id>_<timestamp>/
    │   │       │   └── session_state.json
    │   │       └── ...
    │   └── server_<older>/                          ← resumable historical servers
    │       └── sessions/
    │           └── ...

Supports:
- Creating new server folders on startup
- Resuming sessions from the latest (or specified) historical server
- Directory-based sessions with session_state.json
- Atomic writes via tmp + os.replace
- sessions_index.json for fast listing

Self-contained — no imports from data_service.py.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from openteam.server.services.json_io import primary_val_from_args, write_json_atomic

logger = logging.getLogger(__name__)


# ── Unified frontend session protocol (v6) ──────────────────────────────────
#
# Frontends supply prefix-validated external session ids (e.g. "rovodev-<uuid4>",
# "webui-<unix>-<hex6>"). Prefixes are whitelisted so a frontend cannot impersonate
# another frontend; the remainder is constrained to a safe character set so the
# id can safely become a directory name.
#
# The whitelist is immutable except via the CI preflight
# `test_frontend_prefix_whitelist_immutable.py`; any addition requires explicit
# review.
_VALID_FRONTEND_PREFIXES: frozenset[str] = frozenset(
    {
        "rovodev",  # RovoDev TUI (v6 primary user)
        "webui",  # React WebUI (POST-1 migration target)
        "mcp",  # MCP wrapper (POST-4)
        "session",  # Legacy server-minted ids (backward compat)
        "slack",  # Reserved for future Slack bot
        "vscode",  # Reserved for future VS Code extension
    }
)

_EXTERNAL_ID_REMAINDER_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")


def validate_external_id(external_id: str) -> tuple[str, str]:
    """Split and validate an external session id.

    Returns ``(prefix, remainder)`` on success. Raises ``ValueError`` if the id
    is malformed: missing prefix, prefix not in whitelist, or remainder fails
    the character / length check.

    The remainder regex (``^[A-Za-z0-9_.\\-]{1,128}$``) rejects path-traversal
    sequences (``/``, ``..``-as-first-char is fine because the regex itself
    allows ``.`` but the id can never escape its containing directory due to
    the leading ``<prefix>-`` segment), shell metacharacters, and overly long
    ids. The id is intended to be safely usable as a filesystem directory name.
    """
    if not isinstance(external_id, str) or not external_id:
        raise ValueError("external_id must be a non-empty string")
    if "-" not in external_id:
        raise ValueError(
            f"external_id {external_id!r} is missing the `<prefix>-<id>` separator"
        )
    prefix, _, remainder = external_id.partition("-")
    if prefix not in _VALID_FRONTEND_PREFIXES:
        raise ValueError(
            f"external_id prefix {prefix!r} is not in the whitelist "
            f"{sorted(_VALID_FRONTEND_PREFIXES)!r}"
        )
    if not _EXTERNAL_ID_REMAINDER_RE.match(remainder):
        raise ValueError(
            f"external_id remainder {remainder!r} fails validation regex "
            "(allowed: alphanumerics, underscore, dot, hyphen; 1-128 chars)"
        )
    return prefix, remainder


class SessionStore:
    """File-based persistent session store with runtime server structure."""

    def __init__(
        self,
        runtime_root: str | Path,
        *,
        resume_server: str | None = None,
    ) -> None:
        """Initialize the session store.

        Args:
            runtime_root: Root directory for runtime data (e.g., <project>/_runtime)
            resume_server: Which server directory to use.
                          - "latest": resume the most recent server.
                          - "<name>": resume that specific server (e.g.
                            "server_20260406_083000_a1b2c3d4").
                          - None or "new": always create a fresh server.
                          (run_server.py defaults --real-sessions to "latest";
                          None here still means create-new.)
        """
        self._runtime_root = Path(runtime_root)
        self._servers_dir = self._runtime_root / "servers"
        self._servers_dir.mkdir(parents=True, exist_ok=True)

        # Determine server directory.
        # Default (resume_server is None or "new"): always create a new server.
        # --resume-latest-server → resume_server="latest" → resume most recent
        # --resume-server <name> → resume_server="<name>" → resume specific server
        if resume_server is None or resume_server == "new":
            self._server_dir = self._create_server_dir()
        elif resume_server == "latest":
            latest = self._find_latest_server()
            if latest:
                self._server_dir = latest
                logger.info("Resuming latest server: %s", latest.name)
            else:
                logger.info("No existing server found, creating new")
                self._server_dir = self._create_server_dir()
        else:
            candidate = self._servers_dir / resume_server
            if candidate.is_dir():
                self._server_dir = candidate
                logger.info("Resuming server: %s", resume_server)
            else:
                logger.warning("Server %s not found, creating new", resume_server)
                self._server_dir = self._create_server_dir()

        # Sessions directory under the server
        self._dir = self._server_dir / "sessions"
        self._dir.mkdir(parents=True, exist_ok=True)

        # Check for existing sessions
        has_sessions = any(
            d.is_dir() and (d / "session_state.json").exists()
            for d in self._dir.iterdir()
            if d.is_dir()
        )
        if not has_sessions:
            self._create_default_session()

        logger.info(
            "SessionStore initialized: %s (server: %s)",
            self._dir,
            self._server_dir.name,
        )

    # ── Public API ───────────────────────────────────────────────────

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return session summaries. Prefers sessions_index.json, falls back to scan.

        Returns summaries sorted by updated_at descending (newest first).
        """
        # Fast path: sessions_index.json (for external writers / future optimization)
        index_path = self._dir / "sessions_index.json"
        if index_path.is_file():
            try:
                data = json.loads(index_path.read_text(encoding="utf-8"))
                sessions = data.get("sessions", [])
                if sessions:
                    return sessions
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read sessions_index.json: %s", e)

        # Fallback: scan all session files + directories
        sessions = self._scan_sessions()
        # Sort by updated_at descending (newest first)
        sessions.sort(
            key=lambda s: s.get("updated_at") or s.get("created_at") or "", reverse=True
        )
        return sessions

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Read full session data for a given session_id.

        Checks flat file first, then directory structure.
        Backfills workflow_context for sessions created before workflow support.
        """
        # Try flat file: <sessions_dir>/<session_id>.json
        flat_file = self._session_path(session_id)
        if flat_file.is_file():
            try:
                session = json.loads(flat_file.read_text(encoding="utf-8"))
                self._backfill_workflow_context(session)
                return session
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read %s: %s", flat_file, e)
                return None

        # Try directory structure: <sessions_dir>/<session_id>_<timestamp>/session_state.json
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return None

        state_file = session_dir / "session_state.json"
        if not state_file.is_file():
            return None

        try:
            session = json.loads(state_file.read_text(encoding="utf-8"))
            self._backfill_workflow_context(session)
            return session
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to read session_state.json for %s: %s", session_id, e
            )
            return None

    def create_session(
        self,
        title: str | None = None,
        *,
        _explicit_id: str | None = None,
        _frontend_id: str | None = None,
        _frontend_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new session directory and return the full session object.

        - ID format (default): ``session-<unix_timestamp>-<6_hex_chars>``
        - ID format (frontend-supplied): ``<prefix>-<remainder>`` where prefix
          ∈ ``_VALID_FRONTEND_PREFIXES`` (validated via ``_explicit_id``)
        - Directory: ``<session_id>_<YYYYMMDD_HHMMSS>/session_state.json``
        - Primary agent: always Orchestrator
        - Initial message: welcome message from Orchestrator

        The underscore-prefixed kwargs are part of the unified frontend session
        protocol (v6). Public callers use :meth:`attach_or_create_session`; the
        legacy ``create_session(title=...)`` form continues to mint server-side
        ids for the React UI.
        """
        if _explicit_id is not None:
            # Validate explicit id against the prefix whitelist. Bypassing
            # validation here would let a frontend create sessions outside
            # its assigned prefix space.
            validate_external_id(_explicit_id)
            session_id = _explicit_id
        else:
            now = time.time()
            session_id = f"session-{int(now)}-{uuid4().hex[:6]}"

        timestamp = _iso_now()
        dir_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        session: dict[str, Any] = {
            "id": session_id,
            "title": title or "Orchestrator Session",
            "created_at": timestamp,
            "updated_at": timestamp,
            "server": self._server_dir.name,
            "workflow_context": self._default_workflow_context(),
            "messages": [
                {
                    "id": f"{session_id}-msg-001",
                    "role": "assistant",
                    "agent_name": "Orchestrator",
                    "agent_id": "orchestrator",
                    "content": (
                        "Welcome to OpenTeam. I'm the Orchestrator — your AI team coordinator. "
                        "I can help you hire and onboard new AI employees, delegate tasks, manage projects, "
                        "review team status, and make decisions across your organization.\n\n"
                        "What would you like to work on?"
                    ),
                    "timestamp": timestamp,
                    # Stamp the seeded welcome message with turn 0 so UI fallbacks
                    # can exclude it from turn counting.
                    "turn_number": 0,
                },
            ],
        }
        # Persist frontend provenance so list/detail views can attribute the
        # session to the originating frontend. Optional — legacy server-minted
        # sessions don't carry these fields.
        if _frontend_id is not None:
            session["frontend_id"] = _frontend_id
        if _frontend_metadata:
            session["frontend_metadata"] = dict(_frontend_metadata)
        if _explicit_id is not None:
            session["external_id"] = _explicit_id

        # Create session directory
        session_dir = self._dir / f"{session_id}_{dir_timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write(session_dir / "session_state.json", session)
        self._update_index()
        logger.info(
            "Created session: %s (%s) in %s",
            session_id,
            title or "Orchestrator Session",
            session_dir.name,
        )
        return session

    def attach_or_create_session(
        self,
        *,
        external_id: str,
        frontend_id: str | None = None,
        frontend_metadata: dict[str, Any] | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Idempotently return the session identified by ``external_id``.

        If a session with the given id already exists on disk, return it as-is
        (frontend_metadata + frontend_id are NOT overwritten on attach; clients
        should treat attach as read-or-create, never read-and-modify).

        Otherwise create a new session with the explicit external id, validating
        the prefix against ``_VALID_FRONTEND_PREFIXES`` (Invariant I2).

        This is the single entry point used by the ``POST /api/sessions/attach``
        HTTP endpoint (Invariant I9: server-as-single-writer in Server Mode)
        and the Subprocess-Mode fallback path in
        ``openteam.mcp_server.context.build_session_context`` (Invariant I15).

        Idempotency is established by ``get_session(external_id)`` — same id
        called twice returns the same session dict without re-creating the dir.
        """
        # validate_external_id raises ValueError on prefix-whitelist failures;
        # callers (the HTTP route) translate that into HTTP 400.
        parsed_prefix, _ = validate_external_id(external_id)
        # Default frontend_id to the parsed prefix so list views always have an
        # attributable frontend without forcing the client to repeat the prefix.
        effective_frontend_id = frontend_id or parsed_prefix

        existing = self.get_session(external_id)
        if existing is not None:
            return existing

        return self.create_session(
            title=title,
            _explicit_id=external_id,
            _frontend_id=effective_frontend_id,
            _frontend_metadata=frontend_metadata,
        )

    def append_message(
        self, session_id: str, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Append a message to a session and persist. Returns updated session or None."""
        session = self.get_session(session_id)
        if session is None:
            return None

        # Defensive id-dedup guard: if a message with the same 'id' already
        # exists, treat the append as idempotent and skip it. Protects against
        # double-delivery (e.g. retried WS frames) duplicating history.
        new_id = message.get("id")
        if new_id is not None and any(
            m.get("id") == new_id for m in session["messages"]
        ):
            logger.debug(
                "append_message: skipping duplicate message id %s for session %s",
                new_id,
                session_id,
            )
            return session

        session["messages"].append(message)
        session["updated_at"] = _iso_now()
        self._persist_session(session_id, session)
        self._update_index()
        return session

    def update_session(
        self, session_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update session fields (title, etc.) and persist. Returns updated session or None."""
        session = self.get_session(session_id)
        if session is None:
            return None

        for key, value in updates.items():
            if key != "id":  # Never overwrite ID
                session[key] = value
        session["updated_at"] = _iso_now()
        self._persist_session(session_id, session)
        self._update_index()
        return session

    def update_workflow_context(
        self, session_id: str, wc_dict: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Persist updated WorkflowContext dict back into session."""
        return self.update_session(session_id, {"workflow_context": wc_dict})

    def save_turn_data(
        self,
        session_id: str,
        turn_number: int,
        turn_data: dict[str, Any],
        round: int | None = None,
    ) -> None:
        """Persist per-turn data to <session_dir>/turn_NNN/ directory (RankEvolve style).

        Creates a directory with separate files for each data section:
        - rendered_prompt.txt, template_source.txt, inference_response.txt, user_input.txt
        - template_feed.json, template_config.json, api_payload.json
        - metadata.json (catch-all for other keys)
        - turn.json (combined, backward compat for get_turn_data)

        When ``round`` is not None, the per-key files + combined ``turn.json`` are
        written under the per-round subdir ``turn_NNN/round_MMM/`` instead of the
        turn root. The turn root ``turn_NNN/turn.json`` remains the assembled
        round-summary (written via :meth:`update_turn_root_summary`). When
        ``round`` is None, behavior is unchanged: writes go to the turn root.

        NOTE: We unified the layout to `<session_dir>/turn_NNN/` (no `turns/` parent)
        to match RankEvolve's structure and to co-locate per-turn JsonLogger output
        and streaming cache files in the same directory.
        """
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            logger.debug("save_turn_data: no session dir found for %s", session_id)
            return
        turn_dir = session_dir / f"turn_{turn_number:03d}"
        if round is not None:
            turn_dir = turn_dir / f"round_{round:03d}"
        turn_dir.mkdir(parents=True, exist_ok=True)

        _TEXT_KEYS = {
            "rendered_prompt",
            "template_source",
            "inference_response",
            "user_input",
        }
        _JSON_KEYS = {"template_feed", "template_config", "api_payload"}
        other_meta: dict[str, Any] = {}

        for key, value in turn_data.items():
            if not value:
                continue
            if key in _TEXT_KEYS:
                (turn_dir / f"{key}.txt").write_text(str(value), encoding="utf-8")
            elif key in _JSON_KEYS:
                self._atomic_write(turn_dir / f"{key}.json", value)
            else:
                other_meta[key] = value

        if other_meta:
            self._atomic_write(turn_dir / "metadata.json", other_meta)

        # Combined turn.json for backward compat with get_turn_data
        self._atomic_write(turn_dir / "turn.json", turn_data)

        # Clean up old flat file at the legacy location if it exists. Only
        # relevant for the turn root (the legacy layout never had per-round
        # subdirs), so skip when writing a per-round dir.
        if round is None:
            old_flat = session_dir / "turns" / f"turn_{turn_number:03d}.json"
            if old_flat.is_file():
                old_flat.unlink()

        logger.debug(
            "Saved turn %d data for session %s → %s", turn_number, session_id, turn_dir
        )

    def get_turn_data(
        self, session_id: str, turn_number: int, round: int | None = None
    ) -> dict[str, Any] | None:
        """Load per-turn data from directory (new) or flat file (old format).

        When ``round`` is not None, reads the per-round combined file
        ``turn_NNN/round_MMM/turn.json``. When ``round`` is None, reads the turn
        root ``turn_NNN/turn.json`` (with the legacy flat-file fallbacks).
        """
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return None

        # Per-round read: turn_NNN/round_MMM/turn.json only (no legacy fallback —
        # the round layout is new and never had flat/nested variants).
        if round is not None:
            round_combined = (
                session_dir
                / f"turn_{turn_number:03d}"
                / f"round_{round:03d}"
                / "turn.json"
            )
            if not round_combined.is_file():
                return None
            try:
                return json.loads(round_combined.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read turn data %s: %s", round_combined, e)
                return None

        # Try new layout: <session_dir>/turn_NNN/turn.json (RankEvolve style)
        for combined in (
            session_dir / f"turn_{turn_number:03d}" / "turn.json",
            session_dir
            / "turns"
            / f"turn_{turn_number:03d}"
            / "turn.json",  # legacy nested
        ):
            if combined.is_file():
                try:
                    return json.loads(combined.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to read turn data %s: %s", combined, e)
                    return None

        # Fallback to flat file (oldest format)
        turn_file = session_dir / "turns" / f"turn_{turn_number:03d}.json"
        if not turn_file.is_file():
            return None
        try:
            return json.loads(turn_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read turn data %s: %s", turn_file, e)
            return None

    def update_turn_root_summary(
        self, session_id: str, turn_number: int, summary: dict[str, Any]
    ) -> None:
        """Write/merge the ROOT turn_NNN/turn.json (assembled turn summary).

        The turn root ``turn.json`` is the per-turn summary document: it carries
        the user_input, the assembled cross-round summary, a pointer to the
        latest round, and session metadata. Per-round artifacts live under
        ``turn_NNN/round_MMM/`` (written by :meth:`save_turn_data` with a
        ``round``); this method maintains the single root document that stitches
        them together.

        The provided ``summary`` keys are merged on top of any existing root
        ``turn.json`` (shallow merge — top-level keys in ``summary`` overwrite),
        so repeated calls across rounds accumulate rather than clobber. Reuses
        the existing atomic-write helper.
        """
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            logger.debug(
                "update_turn_root_summary: no session dir found for %s", session_id
            )
            return
        turn_dir = session_dir / f"turn_{turn_number:03d}"
        turn_dir.mkdir(parents=True, exist_ok=True)
        root_file = turn_dir / "turn.json"

        merged: dict[str, Any] = {}
        if root_file.is_file():
            try:
                existing = json.loads(root_file.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    merged = existing
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "update_turn_root_summary: failed to read existing %s: %s",
                    root_file,
                    e,
                )
        merged.update(summary)
        self._atomic_write(root_file, merged)
        logger.debug(
            "Updated turn %d root summary for session %s → %s",
            turn_number,
            session_id,
            root_file,
        )

    def find_session_dir(self, session_id: str) -> Path | None:
        """Return the session directory if it exists, or None.

        Read-only accessor for callers that need None-on-missing semantics
        (e.g., data_service, conversation_service caching/JsonLogger wiring).
        """
        return self._find_session_dir(session_id)

    def get_session_dir(self, session_id: str) -> Path:
        """Return the per-session directory, creating it if absent.

        Ensure-create: always returns a Path (never None). Should rarely
        need to create because create_session() eagerly creates the dir.
        Handles edge cases: flat-file-only sessions from prior runs, or
        directories manually deleted between create and tool dispatch.
        """
        existing = self._find_session_dir(session_id)
        if existing is not None:
            return existing
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        new_dir = self._dir / f"{session_id}_{ts}"
        new_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Ensure-created session dir for %s: %s", session_id, new_dir.name)
        return new_dir

    def get_session_tasks_dir(self, session_id: str) -> Path:
        """Return <session_dir>/tasks/, creating it if absent.

        Single source of truth for where per-session task workspaces live.
        Used by allocate_tool_workspace(base_dir=...) callers.
        """
        session_dir = self.get_session_dir(session_id)
        tasks_dir = session_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        return tasks_dir

    # ── Dashboard (hub) state: subtab sidecars + active pointer ──────

    def get_session_hubs_dir(self, session_id: str) -> Path:
        """Return ``<session_dir>/hubs/``, creating it if absent.

        Single source of truth for where per-session Dashboard (hub) state
        sidecars live (mirror of :meth:`get_session_tasks_dir`)."""
        session_dir = self.get_session_dir(session_id)
        hubs_dir = session_dir / "hubs"
        hubs_dir.mkdir(parents=True, exist_ok=True)
        return hubs_dir

    def save_dashboard_state(
        self, session_id: str, dashboard_state: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Persist the session's dashboard pointer (e.g. ``active_hub_id``).

        Stored as a top-level ``dashboard_state`` field on the session so a
        resume can re-activate the right subtab (mirror of ``sop_state``)."""
        return self.update_session(session_id, {"dashboard_state": dashboard_state})

    def load_dashboard_state(self, session_id: str) -> dict[str, Any]:
        """Return the session's persisted ``dashboard_state`` (or ``{}``)."""
        session = self.get_session(session_id)
        if session is None:
            return {}
        return dict(session.get("dashboard_state", {}) or {})

    def reconcile_dashboard_ref_statuses(self, session_id: str) -> None:
        """Repair stale ``dashboard_ref`` statuses from disk on resume.

        Mirror of :meth:`reconcile_task_ref_statuses`: a hub whose state sidecar
        is gone is marked ``closed`` so the UI does not offer a dead subtab.
        (Local in-flight runs are marked interrupted by the hub controller's own
        reconcile, #18 — this only heals the subtab marker.)"""
        session = self.get_session(session_id)
        if session is None:
            return
        changed = False
        for m in session.get("messages", []):
            if m.get("role") != "dashboard_ref":
                continue
            hub_id = m.get("hubId")
            if not hub_id:
                continue
            state_path = (
                self.get_session_dir(session_id) / "hubs" / hub_id / "hub_state.json"
            )
            if not state_path.is_file() and m.get("status") != "closed":
                m["status"] = "closed"
                changed = True
        if changed:
            session["updated_at"] = _iso_now()
            self._persist_session(session_id, session)
            self._update_index()

    def reconcile_hub_queues(self, session_id: str) -> int:
        """On resume, heal a hub's task queue from disk (#18): mark phantom
        ``running`` entries (whose local subprocess was orphaned by a server
        restart) as interrupted so the queue runner doesn't wedge forever.
        Delegates to ``experiment_hub.hub_state``; best-effort, returns the count
        of entries healed. No-op when the experiment_hub backend is unavailable
        or the session has no active hub / queue."""
        session = self.get_session(session_id)
        if session is None:
            return 0
        wc_dict = session.get("workflow_context") or {}
        if not wc_dict.get("active_multi_task_id") and not wc_dict.get("task_queue"):
            return 0
        try:
            from agent_foundation.experiment_hub import hub_state
            from agent_foundation.server.workflow_context import WorkflowContext
        except Exception:
            return 0
        session_dir = self.get_session_dir(session_id)
        try:
            wc = WorkflowContext.from_dict(wc_dict)
            healed = hub_state.reconcile_task_queue_with_disk(wc, session_dir / "tasks")
        except Exception as exc:
            logger.warning("reconcile_hub_queues failed for %s: %s", session_id, exc)
            return 0
        if healed:
            self.update_workflow_context(session_id, wc.to_dict())
            logger.info(
                "reconcile_hub_queues: healed %d phantom-running entr%s for %s",
                healed,
                "y" if healed == 1 else "ies",
                session_id,
            )
        # Heal stuck submission rows too (submitted/running whose training-run
        # workspace has actually finished — the launcher subprocess was orphaned
        # on restart, #18). Idempotent + cheap on the happy path.
        mid = wc_dict.get("active_multi_task_id")
        if mid:
            try:
                from agent_foundation.experiment_hub.submissions_service import (
                    load_hub_submissions,
                    reconcile_stuck_submissions,
                )

                subs = load_hub_submissions(session_dir, str(mid))
                reconcile_stuck_submissions(session_dir, str(mid), subs)
            except Exception as exc:
                logger.warning(
                    "reconcile_hub_queues: submission heal failed for %s: %s",
                    session_id,
                    exc,
                )
        return healed

    # ── Resumability: turn linkage + message patching ───────────────

    def next_turn_number(self, session_id: str) -> int:
        """Return the turn number the NEXT turn will receive (1-based).

        Mirrors ``ConversationService.run_conversation_turn``'s ``user_turn``:
        count existing ``turn_NNN/`` dirs (+1). Used by the WS route to stamp
        the upcoming turn onto a human message BEFORE it is appended (the message
        is appended before that turn's dir is created, so the count is the
        turn-to-be — the dispatcher uses the injected live ``user_turn`` instead,
        since by dispatch time the dir already exists).
        """
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return 1
        count = sum(
            1
            for p in session_dir.iterdir()
            if p.is_dir() and p.name.startswith("turn_") and p.name != "turns"
        )
        if count == 0:
            legacy = session_dir / "turns"
            if legacy.is_dir():
                count = sum(
                    1
                    for p in legacy.iterdir()
                    if p.is_dir() and p.name.startswith("turn_")
                )
        return count + 1

    def update_message(
        self, session_id: str, message_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Shallow-merge ``updates`` into the message with ``id == message_id``.

        Returns the updated session, or None if the session/message is absent.
        Mirror of :meth:`append_message`'s persist path.
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        for m in session.get("messages", []):
            if m.get("id") == message_id:
                m.update(updates)
                session["updated_at"] = _iso_now()
                self._persist_session(session_id, session)
                self._update_index()
                return session
        return None

    # ── Task sidecars (task_meta.json, lives INSIDE each workspace) ──

    @staticmethod
    def write_task_meta(workspace: str | Path, meta: dict[str, Any]) -> None:
        """Write ``task_meta.json`` into a task workspace (atomic)."""
        write_json_atomic(Path(workspace) / "task_meta.json", meta)

    @staticmethod
    def read_task_meta(workspace: str | Path) -> dict[str, Any] | None:
        """Read ``task_meta.json`` from a workspace, or None if absent/corrupt."""
        path = Path(workspace) / "task_meta.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def update_task_meta(
        self, workspace: str | Path, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Read-merge-write ``task_meta.json`` (preserves existing fields)."""
        meta = self.read_task_meta(workspace) or {}
        meta.update(updates)
        self.write_task_meta(workspace, meta)
        return meta

    # ── Pending-widget persistence (the conversation widget awaiting a human) ──
    # Survives WS reconnect + server restart. The small ``marker`` (widget spec +
    # ToolsToInvoke + output_vars + turn/round/pending_input_id) lives in
    # session_state.json for a cheap read on (re)connect; the large emit-point
    # continuation ``blob`` (full _messages etc.) lives in a per-session sidecar
    # ``pending_input.json`` so the main file doesn't bloat. Single-slot: at most
    # one conversation widget awaits a human at a time (dev-tool/task widgets
    # never write here — see WebSocketInteractive, gated on _round_ctx).

    def _pending_input_sidecar(self, session_id: str) -> Path | None:
        session_dir = self._find_session_dir(session_id)
        return None if session_dir is None else session_dir / "pending_input.json"

    def set_pending_input(
        self, session_id: str, marker: dict[str, Any], blob: dict[str, Any]
    ) -> None:
        """Persist the currently-awaited widget. Writes the sidecar blob FIRST,
        then the marker, so a partial write never leaves a marker without its blob
        (recovery treats a missing blob as re-display-only)."""
        write_json_atomic(self.get_session_dir(session_id) / "pending_input.json", blob)
        self.update_session(session_id, {"pending_input": marker})

    def get_pending_input(self, session_id: str) -> dict[str, Any] | None:
        """Return the pending-widget marker, or None if nothing awaits a human."""
        session = self.get_session(session_id)
        return (session or {}).get("pending_input") or None

    def read_pending_input_blob(self, session_id: str) -> dict[str, Any] | None:
        """Read the emit-point continuation blob, or None if absent/corrupt
        (⟹ re-display-only recovery)."""
        path = self._pending_input_sidecar(session_id)
        if path is None or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def clear_pending_input(self, session_id: str) -> None:
        """Clear the marker + delete the sidecar (idempotent). Call when the
        widget is resolved (answer), superseded (new message), or its turn is
        abandoned (cancel / error / resume-rewind) — NOT on a plain disconnect
        (that is the persistence case)."""
        self.update_session(session_id, {"pending_input": None})
        path = self._pending_input_sidecar(session_id)
        if path is not None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.warning(
                    "clear_pending_input unlink failed (%s): %s", session_id, e
                )

    @staticmethod
    def is_workspace_complete(workspace: str | Path) -> bool:
        """Canonical "this task workspace is fully complete" predicate.

        Primary signal: ``checkpoints/final_result.json`` (the LinearWorkflow
        inferencer writes it only at FULL completion — all phases + iterations).
        Fallback: the AgentFoundation per-phase markers ``.plan_completed`` +
        ``.impl_completed`` (``artifacts/`` canonical, legacy ``outputs/``). We
        prefer ``final_result.json`` over markers-alone because the markers are
        per-phase and would mislabel an analysis-pending workspace as complete.

        Drives the cosmetic subtab status (reconcile) only — reuse-eligibility
        does NOT depend on it (see :meth:`find_reusable_workspace`).
        """
        ws = Path(workspace)
        if (ws / "checkpoints" / "final_result.json").is_file():
            return True
        for sub in ("artifacts", "outputs"):
            if (ws / sub / ".plan_completed").is_file() and (
                ws / sub / ".impl_completed"
            ).is_file():
                return True
        return False

    def reconcile_task_ref_statuses(
        self,
        session_id: str,
        *,
        live_task_ids: set[str] | None = None,
    ) -> None:
        """Repair stale ``starting``/``running`` ``task_ref`` statuses from disk.

        For each ``task_ref`` message in ``starting``/``running``:
          * if its ``taskId`` is in ``live_task_ids`` — SKIP (bg task is
            still alive; its own success/exception branch will terminalize);
          * else if its workspace :meth:`is_workspace_complete` — heal to
            ``completed``;
          * else — heal to ``error`` with ``errorType="interrupted"`` and a
            canonical explanatory ``error`` message (distinguishes an
            interruption from a real runtime exception, whose ``errorType``
            carries the exception class name).

        When ``live_task_ids is None`` (legacy callers), falls back to the
        pre-fix behavior: heal every not-complete chip to ``error``. Modern
        callers pass the set from ``ConversationService.get_live_task_ids``,
        captured BEFORE any ``evict_session_inferencer`` (which pops the
        registry without cancelling tasks — a post-evict fetch would return
        an empty set and cause false-positive healing of alive tasks).

        Persists only if changed. Called before ``session_init`` so restored
        subtabs reflect reality.
        """
        live = live_task_ids if live_task_ids is not None else set()
        session = self.get_session(session_id)
        if session is None:
            return
        changed = False
        for m in session.get("messages", []):
            if m.get("role") != "task_ref":
                continue
            if m.get("status") not in ("starting", "running"):
                continue
            # Resolve the task_id. Canonical field is `taskId`; fall back to
            # deriving from the message id in case a legacy record lacks it.
            tid = m.get("taskId")
            if not tid:
                _mid = m.get("id", "")
                if isinstance(_mid, str) and _mid.startswith("task-ref-"):
                    tid = _mid[len("task-ref-") :]
            if tid and tid in live:
                continue  # bg task still alive — do not touch its status
            ws = m.get("workspace")
            if ws and self.is_workspace_complete(ws):
                if m.get("status") != "completed":
                    m["status"] = "completed"
                    # Clear any prior stale error metadata (defense-in-depth).
                    m.pop("errorType", None)
                    m.pop("error", None)
                    changed = True
            else:
                if m.get("status") != "error" or m.get("errorType") != "interrupted":
                    m["status"] = "error"
                    m["errorType"] = "interrupted"
                    m["error"] = (
                        "Task was interrupted (server crashed or restarted "
                        "before it finished)."
                    )
                    changed = True
        if changed:
            session["updated_at"] = _iso_now()
            self._persist_session(session_id, session)
            self._update_index()

    def find_reusable_workspace(
        self,
        session_id: str,
        tool_name: str,
        sop_name: str,
        phase_index: str,
        primary_val: str,
    ) -> Path | None:
        """Find the reusable task workspace matching the SOP-scoped key.

        Matches a workspace's ``task_meta.json`` on the full key ``(tool_name,
        sop_name, phase_index, primary_arg_value)`` when the workspace is NOT
        referenced by any current ``task_ref`` message (i.e. it is an orphan left
        by a keep-truncate). Returns None for an ad-hoc call (empty
        ``sop_name``/``phase_index``).

        Preference: a COMPLETE match (AF resumes it instantly) over a PARTIAL one
        (AF CONTINUES it from its markers); oldest-first within each so a looped
        phase replays orphans in order.

        Precise-only by design: every workspace has a ``task_meta.json`` — new
        runs write it at dispatch, and pre-feature workspaces are adopted by
        :meth:`backfill_task_sidecars` (which reconstructs the full key from the
        session) BEFORE this runs. A workspace with no sidecar is simply not
        matched (→ the task runs fresh — never a loose/wrong reuse).
        """
        if not sop_name or not phase_index:
            return None
        session = self.get_session(session_id)
        if session is None:
            return None
        referenced_names = {
            Path(m["workspace"]).name
            for m in session.get("messages", [])
            if m.get("role") == "task_ref" and m.get("workspace")
        }
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return None
        tasks_dir = session_dir / "tasks"
        if not tasks_dir.is_dir():
            return None
        # Prefer a COMPLETE key-match (instant reuse) over a PARTIAL one (continue).
        complete: list[tuple[str, Path]] = []
        partial: list[tuple[str, Path]] = []
        for child in tasks_dir.iterdir():
            if not child.is_dir() or child.name in referenced_names:
                continue
            meta = self.read_task_meta(child)
            if not meta:
                continue  # no sidecar → not matched (backfill adopts these first)
            if (
                meta.get("tool_name") == tool_name
                and meta.get("sop_name") == sop_name
                and str(meta.get("phase_index")) == str(phase_index)
                and meta.get("primary_arg_value") == primary_val
            ):
                target = complete if self.is_workspace_complete(child) else partial
                target.append((str(meta.get("created_at") or ""), child))
        for bucket in (complete, partial):
            if bucket:
                bucket.sort(key=lambda c: c[0])  # oldest first (chronological)
                return bucket[0][1]
        return None

    @staticmethod
    def _dir_tool_name(dirname: str) -> str:
        """Tool name from a workspace dir ``<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>``.

        Strips the trailing ``_<8 digits>_<6 digits>_<8 hex>`` allocator suffix
        (``allocate_tool_workspace`` naming), leaving the (possibly
        underscore-containing) tool name. Returns the input unchanged when it
        doesn't match the pattern, so non-workspace dirs never match a tool.
        """
        return re.sub(r"_\d{8}_\d{6}_[0-9a-f]{8}$", "", dirname)

    @staticmethod
    def _dir_created_at(dirname: str) -> str:
        """ISO timestamp parsed from a workspace dir's ``_<YYYYMMDD>_<HHMMSS>_``
        allocator stamp, or ``""`` if the name doesn't match."""
        m = re.search(
            r"_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_[0-9a-f]{8}$", dirname
        )
        if not m:
            return ""
        y, mo, da, h, mi, s = m.groups()
        return f"{y}-{mo}-{da}T{h}:{mi}:{s}Z"

    def _recover_action_targets(
        self,
        session_dir: Path,
        tools: set[str],
        primary_arg_map: dict[str, str | bool],
        primary_arg_type_map: dict[str, str],
    ) -> dict[str, list[str]]:
        """Recover, per tool, the ordered normalized primary-arg values from the
        session's recorded tool actions (turn artifacts).

        Reuses the engine's OWN action parser (``parse_conversation_response``) on
        each ``turn_NNN/round_MMM/inference_response.txt`` and the same
        ``coerce_tool_arguments`` + primary-arg resolution the dispatcher uses — so
        a recovered value is byte-identical to what the live dispatch computes.
        Returns ``{tool_name: [value, ...]}`` in turn→round order. Best-effort:
        any import/parse failure yields an empty result (caller degrades to "").
        """
        out: dict[str, list[str]] = {}
        turn_dirs = sorted(
            (
                p
                for p in session_dir.iterdir()
                if p.is_dir() and p.name.startswith("turn_") and p.name != "turns"
            ),
            key=lambda p: p.name,
        )
        for td in turn_dirs:
            round_dirs = sorted(
                (p for p in td.iterdir() if p.is_dir() and p.name.startswith("round_")),
                key=lambda p: p.name,
            ) or [td]  # fall back to the turn root when there are no round subdirs
            for rd in round_dirs:
                resp = rd / "inference_response.txt"
                if not resp.is_file():
                    continue
                for tool, val in self._targets_from_response(
                    resp, tools, primary_arg_map, primary_arg_type_map
                ):
                    out.setdefault(tool, []).append(val)
        return out

    @staticmethod
    def _targets_from_response(
        resp_path: Path,
        tools: set[str],
        primary_arg_map: dict[str, str | bool],
        primary_arg_type_map: dict[str, str],
    ) -> list[tuple[str, str]]:
        """Parse one ``inference_response.txt`` into ``(tool, normalized_value)``
        pairs for the requested ``tools`` — reusing the engine's action parser +
        the dispatcher's arg coercion so values match the live dispatch exactly.
        Best-effort: returns ``[]`` on any import/read/parse failure.
        """
        try:
            from agent_foundation.common.inferencers.agentic_inferencers.conversational.conversation_response_parser import (  # noqa: E501
                parse_conversation_response,
            )
            from openteam.server.services.cli_args import coerce_tool_arguments

            parsed = parse_conversation_response(resp_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        pairs: list[tuple[str, str]] = []
        for action in getattr(parsed, "action_tools", []) or []:
            canonical = str(action.get("name", "")).lstrip("-").replace("-", "_")
            if canonical not in tools:
                continue
            try:
                args = coerce_tool_arguments(action.get("arguments", {}), None)
            except Exception:
                continue
            primary_arg = primary_arg_map.get(canonical)
            ptype = primary_arg_type_map.get(canonical, "string")
            # Shared with dispatch (ToolDispatcher._dispatch_as_task) so a
            # backfilled key equals what the live dispatch computes — honors the
            # ``False`` opt-out (no volatile ``request`` fallback) identically.
            val = primary_val_from_args(args, primary_arg, ptype)
            if val:
                pairs.append((canonical, val))
        return pairs

    def backfill_task_sidecars(
        self,
        session_id: str,
        primary_arg_map: dict[str, str | bool],
        primary_arg_type_map: dict[str, str],
    ) -> int:
        """Adopt pre-feature task workspaces that have no ``task_meta.json``.

        Reconstructs a REAL full-key sidecar (tool/sop/phase/primary_arg/status)
        for each sidecar-less workspace, so the precise reuse matcher can match
        them with no loose fallback. Idempotent — workspaces that already have a
        sidecar are skipped. Returns the number of sidecars written.

        Sources (all chosen so a backfilled key equals what the live dispatch
        computes): ``tool_name`` from the dir name; ``status`` from on-disk
        completion markers; ``sop_name`` + ``phase_index`` from the session's
        persisted ``sop_state`` (the same state the rebuilt inferencer restores);
        ``primary_arg_value`` from the session's recorded action for that tool
        (:meth:`_recover_action_targets`), attributed to orphan workspaces by
        creation order (single recovered target → applied to all orphans of that
        tool). When the value can't be recovered it is left ``""`` so the sidecar
        simply won't match (the task runs fresh — never a wrong reuse).
        """
        session = self.get_session(session_id)
        if session is None:
            return 0
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return 0
        tasks_dir = session_dir / "tasks"
        if not tasks_dir.is_dir():
            return 0

        # Orphan workspaces (no sidecar), grouped by tool, in creation order.
        orphans_by_tool: dict[str, list[Path]] = {}
        for child in sorted(tasks_dir.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or self.read_task_meta(child) is not None:
                continue
            orphans_by_tool.setdefault(self._dir_tool_name(child.name), []).append(
                child
            )
        if not orphans_by_tool:
            return 0

        targets_by_tool = self._recover_action_targets(
            session_dir, set(orphans_by_tool), primary_arg_map, primary_arg_type_map
        )
        sop = session.get("sop_state") or {}
        sop_name = sop.get("sop_name", "") or ""
        tool_phase_map = sop.get("tool_phase_map", {}) or {}

        written = 0
        for tool, orphans in orphans_by_tool.items():
            targets = targets_by_tool.get(tool, [])
            phase_index = tool_phase_map.get(tool)
            for i, ws in enumerate(orphans):
                if len(targets) == 1:
                    primary_val = targets[0]  # one target → applies to all orphans
                elif i < len(targets):
                    primary_val = targets[i]  # by-order attribution
                else:
                    primary_val = ""
                # Mirror the dispatch gate exactly (registered = SOP + phase,
                # NOT primary_val): an opt-out tool's key is content-free, so an
                # empty primary_val is correct and must still yield a task_key.
                task_key = (
                    f"{sop_name}/{phase_index}/{tool}/{primary_val}"
                    if (sop_name and phase_index is not None)
                    else None
                )
                self.write_task_meta(
                    ws,
                    {
                        "task_id": f"backfill-{ws.name}",
                        "tool_name": tool,
                        "label": primary_val or tool,
                        "status": (
                            "completed" if self.is_workspace_complete(ws) else "error"
                        ),
                        "workspace": str(ws),
                        "primary_arg": primary_arg_map.get(tool),
                        "primary_arg_value": primary_val,
                        "sop_name": sop_name,
                        "phase_index": phase_index,
                        "task_key": task_key,
                        "turn_number": None,
                        "created_at": self._dir_created_at(ws.name),
                        "backfilled": True,
                    },
                )
                written += 1
        if written:
            logger.info(
                "Backfilled %d task sidecar(s) for session %s", written, session_id
            )
        return written

    # ── Checkpoint / truncate (resume-from-turn + checkpoint UI) ─────

    def get_session_checkpoints_dir(self, session_id: str) -> Path:
        """Return ``<session_dir>/checkpoints/``, creating it if absent."""
        cp = self.get_session_dir(session_id) / "checkpoints"
        cp.mkdir(parents=True, exist_ok=True)
        return cp

    def checkpoint_session(self, session_id: str) -> str:
        """Snapshot the whole session dir into ``checkpoints/<ts>_<hex6>/``.

        Copies every top-level child EXCEPT the ``checkpoints/`` dir itself (a
        global ``ignore_patterns('checkpoints')`` would wrongly strip each task
        workspace's own nested ``checkpoints/``). Uses ``copy2`` (independent
        inodes) — NOT hardlinks: ``session.jsonl`` is append-mode, so a hardlink
        would let later live appends mutate the snapshot. Returns the snapshot
        name.
        """
        import shutil

        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            raise FileNotFoundError(f"Session dir not found for {session_id}")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = f"{ts}_{uuid4().hex[:6]}"
        dest = session_dir / "checkpoints" / name
        dest.mkdir(parents=True, exist_ok=False)
        for child in session_dir.iterdir():
            if child.name == "checkpoints":
                continue
            target = dest / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
        logger.info("Checkpointed session %s → %s", session_id, dest.name)
        return name

    def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        """List a session's checkpoints (newest first) with ts + message count."""
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return []
        cp_root = session_dir / "checkpoints"
        if not cp_root.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for child in sorted(cp_root.iterdir(), reverse=True):
            if not child.is_dir():
                continue
            message_count = 0
            created_at = None
            state = child / "session_state.json"
            if state.is_file():
                try:
                    data = json.loads(state.read_text(encoding="utf-8"))
                    message_count = len(data.get("messages", []))
                    created_at = data.get("updated_at") or data.get("created_at")
                except (json.JSONDecodeError, OSError):
                    pass
            out.append(
                {
                    "name": child.name,
                    "created_at": created_at,
                    "message_count": message_count,
                }
            )
        return out

    def restore_checkpoint(self, session_id: str, name: str) -> dict[str, Any] | None:
        """Restore a session to checkpoint ``name`` (reversibly).

        Snapshots the CURRENT state first (so a restore is itself undoable), then
        replaces every live top-level child (except ``checkpoints/``) with the
        snapshot's. Returns the restored session, or None if not found. Caller
        MUST quiesce in-flight background tasks first.
        """
        import shutil

        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return None
        cp = session_dir / "checkpoints" / name
        if not cp.is_dir():
            return None
        # 1. snapshot current state first (reversible)
        self.checkpoint_session(session_id)
        # 2. clear live top-level children except checkpoints/
        for child in session_dir.iterdir():
            if child.name == "checkpoints":
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
        # 3. copy the snapshot's children back into the live dir
        for child in cp.iterdir():
            target = session_dir / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
        self._update_index()
        # Clear-point (e): a checkpoint restore replaces the live turn state with a
        # past snapshot — no agentic loop is running against it, so any restored
        # pending-widget marker is a ghost. Drop it (idempotent).
        self.clear_pending_input(session_id)
        logger.info("Restored session %s from checkpoint %s", session_id, name)
        return self.get_session(session_id)

    def truncate_session_at_message(
        self, session_id: str, message_id: str, *, drop_tasks: bool
    ) -> dict[str, Any]:
        """Truncate a session AFTER the message with ``message_id`` (EXCLUSIVE).

        Keeps the clicked human turn (``messages[:idx+1]``) so it stays visible
        (no clear-then-reflash) and can be re-run server-side; removes everything
        AFTER it — its assistant response + later turns — plus the ``turn_NNN/``
        dirs with ``N >= cut_turn`` and ``run_state/store.json`` (so the rebuilt
        inferencer re-syncs from the truncated history; the re-run regenerates the
        clicked turn's own ``turn_<cut>/``). Restores
        ``session["sop_state"]``/``["suspended_sops"]`` from the pre-turn boundary
        snapshot ``turn_<cut>/sop_state_in.json`` (null → replay re-enters the SOP
        fresh). With ``drop_tasks``, ``rmtree``s every task workspace whose sidecar
        ``turn_number >= cut_turn`` (catches chip-bearing AND ghost orphans).

        Returns ``{messages, cut_turn, dropped_workspaces, resumed_message}``
        where ``resumed_message`` is the KEPT clicked turn (the caller re-runs it
        through the normal turn pipeline). The caller MUST quiesce in-flight
        background tasks BEFORE calling this (see
        ``ConversationService.drain_session_background_tasks``).
        """
        session = self.get_session(session_id)
        if session is None:
            return {}
        messages = session.get("messages", [])
        idx = next(
            (i for i, m in enumerate(messages) if m.get("id") == message_id), None
        )
        if idx is None:
            return {}
        cut_turn = self._resolve_cut_turn(messages, idx)
        session_dir = self._find_session_dir(session_id)

        # Read the pre-turn SOP boundary BEFORE deleting turn dirs.
        boundary = self._read_sop_boundary(session_dir, cut_turn)
        session["sop_state"] = (boundary or {}).get("sop_state")
        session["suspended_sops"] = (boundary or {}).get("suspended_sops", [])

        # Truncate the conversation — EXCLUSIVE of the clicked turn: keep it
        # (``messages[:idx+1]``) so it stays visible and can be re-run; drop its
        # assistant response + all later turns.
        resumed_message = messages[idx]
        session["messages"] = messages[: idx + 1]
        session["updated_at"] = _iso_now()
        self._persist_session(session_id, session)
        self._update_index()

        # Clear-point (e): a turn-level rewind drops the clicked turn's assistant
        # response + all later turns — any widget awaiting a human there is now
        # stale. Drop the marker so the re-run starts clean (idempotent).
        self.clear_pending_input(session_id)

        dropped_workspaces: list[str] = []
        if session_dir is not None:
            self._remove_turn_artifacts_at_or_after(session_dir, cut_turn)
            if drop_tasks:
                dropped_workspaces = self._drop_task_workspaces_at_or_after(
                    session_dir, cut_turn
                )

        return {
            "messages": session["messages"],
            "cut_turn": cut_turn,
            "dropped_workspaces": dropped_workspaces,
            "resumed_message": resumed_message,
        }

    @staticmethod
    def _resolve_cut_turn(messages: list[dict[str, Any]], idx: int) -> int:
        """The turn to cut at: the clicked message's stamped ``turn_number``, else a
        count-of-prior-human-messages fallback for un-stamped legacy sessions."""
        cut = messages[idx].get("turn_number")
        if cut is None:
            cut = (
                sum(1 for m in messages[:idx] if m.get("role") in ("manager", "user"))
                + 1
            )
        return int(cut)

    @staticmethod
    def _read_sop_boundary(
        session_dir: Path | None, cut_turn: int
    ) -> dict[str, Any] | None:
        """Pre-turn SOP snapshot (state ENTERING ``cut_turn``), or None."""
        if session_dir is None:
            return None
        snap = session_dir / f"turn_{cut_turn:03d}" / "sop_state_in.json"
        if not snap.is_file():
            return None
        try:
            return json.loads(snap.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _remove_turn_artifacts_at_or_after(session_dir: Path, cut_turn: int) -> None:
        """Remove ``turn_NNN/`` dirs with ``N >= cut_turn`` + the run-state store."""
        import shutil

        for child in session_dir.iterdir():
            if not (
                child.is_dir()
                and child.name.startswith("turn_")
                and child.name != "turns"
            ):
                continue
            try:
                n = int(child.name[len("turn_") :])
            except ValueError:
                continue
            if n >= cut_turn:
                shutil.rmtree(child, ignore_errors=True)
        run_state = session_dir / "run_state" / "store.json"
        if run_state.is_file():
            try:
                run_state.unlink()
            except OSError:
                pass

    def _drop_task_workspaces_at_or_after(
        self, session_dir: Path, cut_turn: int
    ) -> list[str]:
        """``rmtree`` every task workspace whose sidecar ``turn_number >= cut_turn``."""
        import shutil

        dropped: list[str] = []
        tasks_dir = session_dir / "tasks"
        if not tasks_dir.is_dir():
            return dropped
        for child in tasks_dir.iterdir():
            if not child.is_dir():
                continue
            meta = self.read_task_meta(child)
            tn = meta.get("turn_number") if meta else None
            if tn is not None and int(tn) >= cut_turn:
                shutil.rmtree(child, ignore_errors=True)
                dropped.append(str(child))
        return dropped

    def read_round_resume_state(
        self, session_id: str, message_id: str
    ) -> dict[str, Any] | None:
        """Resolve ``(turn, round)`` from a clicked assistant-bubble ``message_id``
        and read that round's entry snapshot ``turn_T/round_Y/resume_state.json``.

        Returns ``{"blob", "turn", "round"}`` or ``None`` when the message, its
        ``turn_number``/``round_index`` stamp, or the snapshot file is absent
        (mock backend, legacy pre-feature rounds, or an empty/no-bubble round) —
        the caller then rejects round-resume gracefully. Call this BEFORE
        ``truncate_session_at_round`` (the ordering invariant): truncate deletes
        the ``round_Y/`` dir, so the blob must be read into memory first.
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        msg = next(
            (m for m in session.get("messages", []) if m.get("id") == message_id),
            None,
        )
        if msg is None:
            return None
        turn = msg.get("turn_number")
        rnd = msg.get("round_index")
        if turn is None or rnd is None:
            return None
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return None
        snap = (
            session_dir
            / f"turn_{int(turn):03d}"
            / f"round_{int(rnd):03d}"
            / "resume_state.json"
        )
        if not snap.is_file():
            return None
        try:
            blob = json.loads(snap.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return {"blob": blob, "turn": int(turn), "round": int(rnd)}

    def truncate_session_at_round(
        self, session_id: str, message_id: str, *, drop_tasks: bool, resume_blob: dict
    ) -> dict[str, Any]:
        """Truncate a session to REDO assistant round Y of turn T (EXCLUSIVE of the
        clicked bubble). Mirrors :meth:`truncate_session_at_message` at round
        granularity: keeps ``messages[:idx]`` (drops the clicked assistant round +
        everything after — the loop regenerates round Y onward), removes
        ``turn_T/round_MMM`` dirs with ``MMM >= Y`` (keeping ``1..Y-1``) and whole
        ``turn_N`` dirs with ``N > T`` plus ``run_state/store.json``, and restores
        ``session["sop_state"]``/``["suspended_sops"]`` from ``resume_blob`` (the
        round-entry snapshot the caller already read — feeds the extra-dirs-aware
        factory restore on CI rebuild).

        Unlike turn-resume, round-resume KEEPS ``turn_T/``, so it also RESETS
        ``turn_T/turn.json`` (``assembled_summary``/``latest_round``) to reflect
        only the kept rounds — else the regenerated first round would append to the
        discarded rounds' summary.

        Returns ``{messages, cut_turn, cut_round, dropped_workspaces}``. The caller
        MUST quiesce in-flight background tasks BEFORE calling this.
        """
        session = self.get_session(session_id)
        if session is None:
            return {}
        messages = session.get("messages", [])
        idx = next(
            (i for i, m in enumerate(messages) if m.get("id") == message_id), None
        )
        if idx is None:
            return {}
        msg = messages[idx]
        cut_turn = msg.get("turn_number")
        cut_round = msg.get("round_index")
        if cut_turn is None or cut_round is None:
            # Unstamped/legacy assistant bubble — caller guards this via
            # read_round_resume_state (returns None → reject); defensive no-op.
            return {}
        cut_turn = int(cut_turn)
        cut_round = int(cut_round)
        session_dir = self._find_session_dir(session_id)

        # Restore the round-entry SOP boundary from the blob (feeds the factory
        # _restore_sop_state on the next CI rebuild). Set BOTH keys.
        session["sop_state"] = resume_blob.get("sop_state")
        session["suspended_sops"] = resume_blob.get("suspended_sops", [])

        # EXCLUSIVE of the clicked assistant bubble — we redo round Y.
        session["messages"] = messages[:idx]
        session["updated_at"] = _iso_now()
        self._persist_session(session_id, session)
        self._update_index()

        # Clear-point (e): a resume-rewind discards every round at/after the cut,
        # including any widget that was awaiting a human there — its marker is now
        # stale. Drop it so the rewound turn's re-run starts clean (idempotent).
        self.clear_pending_input(session_id)

        # Reset turn_T/turn.json to the kept-rounds state (round-resume keeps
        # turn_T; a shallow-merge overwrite of these two keys is sufficient).
        kept_bubbles = [
            m
            for m in session["messages"]
            if m.get("role") == "assistant"
            and int(m.get("turn_number") or -1) == cut_turn
            and m.get("content")
        ]
        assembled = "\n\n".join(m["content"] for m in kept_bubbles)
        # Last KEPT round index is cut_round-1 (rounds 1..cut_round-1 are kept),
        # regardless of whether that round produced a display bubble.
        latest_round = cut_round - 1
        try:
            self.update_turn_root_summary(
                session_id,
                cut_turn,
                {"assembled_summary": assembled, "latest_round": latest_round},
            )
        except Exception as e:
            logger.debug("truncate_session_at_round: turn.json reset failed: %s", e)

        dropped_workspaces: list[str] = []
        if session_dir is not None:
            self._remove_round_artifacts_at_or_after(session_dir, cut_turn, cut_round)
            if drop_tasks:
                dropped_workspaces = self._drop_task_workspaces_at_or_after_round(
                    session_dir, cut_turn, cut_round
                )

        return {
            "messages": session["messages"],
            "cut_turn": cut_turn,
            "cut_round": cut_round,
            "dropped_workspaces": dropped_workspaces,
        }

    @staticmethod
    def _remove_round_artifacts_at_or_after(
        session_dir: Path, cut_turn: int, cut_round: int
    ) -> None:
        """Remove ``turn_cut_turn/round_MMM`` dirs with ``MMM >= cut_round`` (keep
        ``1..cut_round-1`` + ``turn.json``), whole ``turn_N`` dirs with
        ``N > cut_turn``, and ``run_state/store.json``."""
        import shutil

        for child in session_dir.iterdir():
            if not (
                child.is_dir()
                and child.name.startswith("turn_")
                and child.name != "turns"
            ):
                continue
            try:
                n = int(child.name[len("turn_") :])
            except ValueError:
                continue
            if n > cut_turn:
                shutil.rmtree(child, ignore_errors=True)
            elif n == cut_turn:
                for rd in child.iterdir():
                    if not (rd.is_dir() and rd.name.startswith("round_")):
                        continue
                    try:
                        r = int(rd.name[len("round_") :])
                    except ValueError:
                        continue
                    if r >= cut_round:
                        shutil.rmtree(rd, ignore_errors=True)
        run_state = session_dir / "run_state" / "store.json"
        if run_state.is_file():
            try:
                run_state.unlink()
            except OSError:
                pass

    def _drop_task_workspaces_at_or_after_round(
        self, session_dir: Path, cut_turn: int, cut_round: int
    ) -> list[str]:
        """``rmtree`` every task workspace created AT/AFTER round ``cut_round`` of
        turn ``cut_turn``: ``turn_number > cut_turn`` OR (``turn_number == cut_turn``
        AND ``round_number >= cut_round``). A missing ``round_number`` defaults to 1
        (legacy) so a whole-turn redo (cut_round == 1) still drops same-turn tasks;
        a missing ``turn_number`` is never dropped."""
        import shutil

        dropped: list[str] = []
        tasks_dir = session_dir / "tasks"
        if not tasks_dir.is_dir():
            return dropped
        for child in tasks_dir.iterdir():
            if not child.is_dir():
                continue
            meta = self.read_task_meta(child)
            tn = meta.get("turn_number") if meta else None
            if tn is None:
                continue
            tn = int(tn)
            rn = int(meta.get("round_number") or 1)
            if tn > cut_turn or (tn == cut_turn and rn >= cut_round):
                shutil.rmtree(child, ignore_errors=True)
                dropped.append(str(child))
        return dropped

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file or directory. Returns True if deleted, False if not found."""
        # Try flat file first
        flat_file = self._session_path(session_id)
        if flat_file.is_file():
            flat_file.unlink()
            logger.info("Deleted session file: %s", flat_file)
            return True

        # Try directory structure
        session_dir = self._find_session_dir(session_id)
        if session_dir is not None and session_dir.is_dir():
            import shutil

            shutil.rmtree(session_dir)
            logger.info("Deleted session directory: %s", session_dir)
            return True

        return False

    # ── Summary helper ───────────────────────────────────────────────

    @staticmethod
    def _to_summary(session: dict[str, Any]) -> dict[str, Any]:
        """Convert full session dict into list-view summary.

        Self-contained — duplicates the ~7 lines of primary_agent extraction
        logic rather than importing _primary_agent_from_messages from data_service.
        This avoids cross-module coupling for trivial logic.
        """
        messages = session.get("messages", [])
        primary_agent: dict[str, Any] = {"id": None, "name": "New conversation"}
        for msg in messages:
            if msg.get("role") == "assistant":
                agent_id = msg.get("agent_id")
                agent_name = msg.get("agent_name")
                if agent_id is not None or agent_name is not None:
                    primary_agent = {
                        "id": agent_id,
                        "name": agent_name
                        or (str(agent_id) if agent_id else "Assistant"),
                    }
                    break

        return {
            "id": session["id"],
            "title": session.get("title", "Untitled"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "message_count": len(messages),
            "primary_agent": primary_agent,
        }

    # ── Server management ────────────────────────────────────────────

    @property
    def server_name(self) -> str:
        """Return the current server directory name."""
        return self._server_dir.name

    @property
    def server_dir(self) -> Path:
        """Return the current server directory path."""
        return self._server_dir

    @property
    def runtime_root(self) -> Path:
        """Return the runtime root directory path."""
        return self._runtime_root

    def list_servers(self) -> list[dict[str, Any]]:
        """List all server directories with metadata, newest first."""
        servers = []
        for d in sorted(self._servers_dir.iterdir(), reverse=True):
            if not d.is_dir() or not d.name.startswith("server_"):
                continue
            info_file = d / "server_info.json"
            info = {}
            if info_file.is_file():
                try:
                    info = json.loads(info_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            # Count sessions
            sessions_dir = d / "sessions"
            session_count = 0
            if sessions_dir.is_dir():
                session_count = sum(
                    1
                    for sd in sessions_dir.iterdir()
                    if sd.is_dir() and (sd / "session_state.json").exists()
                )
            servers.append(
                {
                    "name": d.name,
                    "created_at": info.get("created_at"),
                    "session_count": session_count,
                    "is_current": d == self._server_dir,
                }
            )
        return servers

    def _create_server_dir(self) -> Path:
        """Create a new timestamped server directory."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        uid = uuid4().hex[:8]
        name = f"server_{ts}_{uid}"
        server_dir = self._servers_dir / name
        server_dir.mkdir(parents=True, exist_ok=True)

        # Write server_info.json
        info = {
            "name": name,
            "created_at": _iso_now(),
            "pid": os.getpid(),
        }
        self._atomic_write(server_dir / "server_info.json", info)
        logger.info("Created new server: %s", name)
        return server_dir

    def _find_latest_server(self) -> Path | None:
        """Find the most recent server directory (by name sort)."""
        candidates = [
            d
            for d in self._servers_dir.iterdir()
            if d.is_dir() and d.name.startswith("server_")
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda d: d.name, reverse=True)
        return candidates[0]

    # ── Private helpers ──────────────────────────────────────────────

    def _create_default_session(self) -> dict[str, Any]:
        """Create the initial default Orchestrator session."""
        return self.create_session(title="Orchestrator Session")

    def _default_workflow_context(self) -> dict[str, Any]:
        """Build a fresh WorkflowContext dict — no workflow_description by default.

        The SOP executor populates workflow_description when entering a SOP.
        Generic sessions have an empty workflow_description so the template
        guard hides the workflow sections from the prompt.
        """
        return {
            "strategy": "default",
            "workflow_description": "",
            "current_phase": "idle",
            "phase_status": "idle",
            "completed_phases": [],
            "active_task_summary": "",
            "active_workspace": "",
            "iteration_count": 0,
            "phase_outputs": {},
        }

    def _backfill_workflow_context(self, session: dict[str, Any]) -> None:
        """Add workflow_context to sessions created before workflow support.

        Mutates the in-memory dict AND persists to disk so the backfill
        only happens once per session.
        """
        if "workflow_context" not in session:
            session["workflow_context"] = self._default_workflow_context()
            self._persist_session(session["id"], session)

    def _load_workflow_description(self) -> str:
        """Load the default workflow description from prompt templates."""
        desc_file = (
            Path(__file__).parent.parent
            / "resources"
            / "prompt_templates"
            / "conversation"
            / "main"
            / "_variables"
            / "workflow_description"
            / "default.jinja2"
        )
        if desc_file.is_file():
            return desc_file.read_text(encoding="utf-8")
        logger.warning("Workflow description not found: %s", desc_file)
        return ""

    def _persist_session(self, session_id: str, session: dict[str, Any]) -> None:
        """Persist session to disk — prefers directory, falls back to flat file."""
        # Try flat file first (legacy compat)
        flat_file = self._session_path(session_id)
        if flat_file.is_file():
            self._atomic_write(flat_file, session)
            return

        # Try directory
        session_dir = self._find_session_dir(session_id)
        if session_dir:
            self._atomic_write(session_dir / "session_state.json", session)
        else:
            # Create new session directory
            dir_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            session_dir = self._dir / f"{session_id}_{dir_timestamp}"
            session_dir.mkdir(parents=True, exist_ok=True)
            self._atomic_write(session_dir / "session_state.json", session)

    def _update_index(self) -> None:
        """Update sessions_index.json for fast listing."""
        sessions = self._scan_sessions()
        sessions.sort(
            key=lambda s: s.get("updated_at") or s.get("created_at") or "", reverse=True
        )
        index = {"sessions": sessions, "updated_at": _iso_now()}
        self._atomic_write(self._dir / "sessions_index.json", index)

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically via tmp file + os.replace.

        Thin wrapper over the shared :func:`json_io.write_json_atomic` so the
        same durable-write primitive backs both ``session_state.json`` and the
        per-workspace ``task_meta.json`` sidecars.
        """
        write_json_atomic(path, data)

    def _find_session_dir(self, session_id: str) -> Path | None:
        """Find the session directory for a session_id.

        Directories are named <session_id>_<YYYYMMDD_HHMMSS>.
        Returns the most recent if multiple match.
        Also checks for exact-name directory (no timestamp suffix).
        """
        if not self._dir.is_dir():
            return None

        # Exact match first
        exact = self._dir / session_id
        if exact.is_dir():
            return exact

        # Prefix match with timestamp suffix
        prefix = f"{session_id}_"
        candidates = [
            d for d in self._dir.iterdir() if d.is_dir() and d.name.startswith(prefix)
        ]
        if not candidates:
            return None

        # Return the most recent (sorted lexicographically by name)
        candidates.sort(key=lambda d: d.name, reverse=True)
        return candidates[0]

    def _scan_sessions(self) -> list[dict[str, Any]]:
        """Scan for sessions — supports both flat files and directory structures."""
        if not self._dir.is_dir():
            return []

        sessions: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        # Scan .json files directly in sessions_dir (excluding sessions_index.json)
        for json_file in sorted(self._dir.glob("*.json")):
            if json_file.name == "sessions_index.json":
                continue
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data:
                    sid = data["id"]
                    if sid not in seen_ids:
                        sessions.append(self._to_summary(data))
                        seen_ids.add(sid)
            except (json.JSONDecodeError, OSError):
                continue

        # Scan subdirectories for session_state.json
        for subdir in sorted(self._dir.iterdir()):
            if not subdir.is_dir():
                continue
            state_file = subdir / "session_state.json"
            if not state_file.is_file():
                continue
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data:
                    sid = data["id"]
                    if sid not in seen_ids:
                        sessions.append(self._to_summary(data))
                        seen_ids.add(sid)
            except (json.JSONDecodeError, OSError):
                continue

        return sessions

    def _session_path(self, session_id: str) -> Path:
        """Return the flat-file path for a session."""
        return self._dir / f"{session_id}.json"


def _iso_now() -> str:
    """Return the current time as an ISO 8601 UTC string."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
