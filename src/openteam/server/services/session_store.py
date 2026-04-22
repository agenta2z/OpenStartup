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
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


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
            resume_server: Server directory name to resume from (e.g., "server_20260406_083000_a1b2c3d4").
                          If None, resumes from the latest server automatically.
                          If "new", always creates a fresh server.
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

        logger.info("SessionStore initialized: %s (server: %s)", self._dir, self._server_dir.name)

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
        sessions.sort(key=lambda s: s.get("updated_at") or s.get("created_at") or "", reverse=True)
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
            logger.warning("Failed to read session_state.json for %s: %s", session_id, e)
            return None

    def create_session(self, title: str | None = None) -> dict[str, Any]:
        """Create a new session directory and return the full session object.

        - ID format: session-<unix_timestamp>-<6_hex_chars>
        - Directory: <session_id>_<YYYYMMDD_HHMMSS>/session_state.json
        - Primary agent: always Orchestrator
        - Initial message: welcome message from Orchestrator
        """
        now = time.time()
        session_id = f"session-{int(now)}-{uuid4().hex[:6]}"
        timestamp = _iso_now()
        dir_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        session = {
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
                },
            ],
        }

        # Create session directory
        session_dir = self._dir / f"{session_id}_{dir_timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write(session_dir / "session_state.json", session)
        self._update_index()
        logger.info("Created session: %s (%s) in %s", session_id, title or "Orchestrator Session", session_dir.name)
        return session

    def append_message(
        self, session_id: str, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Append a message to a session and persist. Returns updated session or None."""
        session = self.get_session(session_id)
        if session is None:
            return None

        session["messages"].append(message)
        session["updated_at"] = _iso_now()
        self._persist_session(session_id, session)
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
        return session

    def update_workflow_context(
        self, session_id: str, wc_dict: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Persist updated WorkflowContext dict back into session."""
        return self.update_session(session_id, {"workflow_context": wc_dict})

    def save_turn_data(
        self, session_id: str, turn_number: int, turn_data: dict[str, Any]
    ) -> None:
        """Persist per-turn data to <session_dir>/turn_NNN/ directory (RankEvolve style).

        Creates a directory with separate files for each data section:
        - rendered_prompt.txt, template_source.txt, inference_response.txt, user_input.txt
        - template_feed.json, template_config.json, api_payload.json
        - metadata.json (catch-all for other keys)
        - turn.json (combined, backward compat for get_turn_data)

        NOTE: We unified the layout to `<session_dir>/turn_NNN/` (no `turns/` parent)
        to match RankEvolve's structure and to co-locate per-turn JsonLogger output
        and streaming cache files in the same directory.
        """
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            logger.debug("save_turn_data: no session dir found for %s", session_id)
            return
        turn_dir = session_dir / f"turn_{turn_number:03d}"
        turn_dir.mkdir(parents=True, exist_ok=True)

        _TEXT_KEYS = {"rendered_prompt", "template_source", "inference_response", "user_input"}
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

        # Clean up old flat file at the legacy location if it exists.
        old_flat = session_dir / "turns" / f"turn_{turn_number:03d}.json"
        if old_flat.is_file():
            old_flat.unlink()

        logger.debug("Saved turn %d data for session %s → %s", turn_number, session_id, turn_dir)

    def get_turn_data(
        self, session_id: str, turn_number: int
    ) -> dict[str, Any] | None:
        """Load per-turn data from directory (new) or flat file (old format)."""
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            return None

        # Try new layout: <session_dir>/turn_NNN/turn.json (RankEvolve style)
        for combined in (
            session_dir / f"turn_{turn_number:03d}" / "turn.json",
            session_dir / "turns" / f"turn_{turn_number:03d}" / "turn.json",  # legacy nested
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

    def get_session_dir(self, session_id: str) -> Path | None:
        """Public accessor for the session's on-disk directory.

        Wraps the private `_find_session_dir` so that callers (e.g.,
        `data_service.get_session_dir`) don't need to depend on a private API.
        Used for per-turn JsonLogger wiring and streaming cache placement.
        """
        return self._find_session_dir(session_id)

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
                        "name": agent_name or (str(agent_id) if agent_id else "Assistant"),
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
                    1 for sd in sessions_dir.iterdir()
                    if sd.is_dir() and (sd / "session_state.json").exists()
                )
            servers.append({
                "name": d.name,
                "created_at": info.get("created_at"),
                "session_count": session_count,
                "is_current": d == self._server_dir,
            })
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
            d for d in self._servers_dir.iterdir()
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
        """Build a fresh WorkflowContext dict with the default workflow description."""
        desc = self._load_workflow_description()
        return {
            "strategy": "default",
            "workflow_description": desc,
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
        sessions.sort(key=lambda s: s.get("updated_at") or s.get("created_at") or "", reverse=True)
        index = {"sessions": sessions, "updated_at": _iso_now()}
        self._atomic_write(self._dir / "sessions_index.json", index)

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically via tmp file + os.replace."""
        # Use the target file's parent directory for the temp file
        tmp_dir = str(path.parent)
        fd, tmp_path = tempfile.mkstemp(
            dir=tmp_dir, suffix=".tmp", prefix=".session_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, str(path))
        except Exception:
            # Clean up tmp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

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
