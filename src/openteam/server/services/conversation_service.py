"""ConversationService — renders conversation prompts and manages LLM interactions.

Responsibilities:
1. Render initial.jinja2 with session history + user input
2. Call LLM via configurable backend (ai-gateway, direct API, or mock)
3. Parse <Response> tags from LLM output
4. Return the assistant's response content

Does NOT manage session persistence — that's SessionStore's job.
The route handler orchestrates: append user msg → call service → append response.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import agent_foundation.resources as _af_res
from agent_foundation.common.inferencers.agentic_inferencers.conversational.conversational_inferencer import (
    _CONTINUE_AFTER_TOOLS,
)
from openteam.server.services.json_io import write_json_atomic

_AF_TEMPLATES_ROOT = Path(_af_res.__file__).parent / "prompt_templates"

logger = logging.getLogger(__name__)

# Roles that are UI-only chrome (chips/cards) and must be excluded from the LLM
# conversation feed. ``task_ref`` / ``dashboard_ref`` are purely-visual subtab
# markers; including them would inject junk empty assistant turns.
_UI_ONLY_ROLES = {"task_ref", "dashboard_ref"}


class _SimplePromptRenderer:
    """Minimal PromptRenderer conforming to ConversationalInferencer's protocol.

    Uses Jinja2 directly — a lightweight fallback when TemplateManagerPromptRenderer
    is not available.
    """

    def __init__(self, templates_dir: Path) -> None:
        from jinja2 import Environment, FileSystemLoader

        self._templates_dir = templates_dir
        self._template_path = "conversation/main/initial.jinja2"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=False,
        )
        self._variable_manager = None

    def render(self, variables: dict) -> str:
        template = self._env.get_template(self._template_path)
        return template.render(**variables)

    def render_string(self, template_str: str, context: dict) -> str:
        template = self._env.from_string(template_str)
        return template.render(**context)

    @property
    def template_source(self) -> str:
        source = self._env.loader.get_source(self._env, self._template_path)
        return source[0]

    @property
    def template_config(self) -> dict:
        """Load .initial.config.yaml sidecar config for the template.

        Resolution order (matching TemplateManagerPromptRenderer):
          1. .<basename>.config.yaml  (e.g. .initial.config.yaml)
          2. .config.yaml             (folder-level default)
        """
        if hasattr(self, "_cached_template_config"):
            return self._cached_template_config

        import yaml as _yaml

        template_dir = self._templates_dir / "conversation" / "main"
        for candidate in (
            template_dir / ".initial.config.yaml",
            template_dir / ".config.yaml",
        ):
            if candidate.is_file():
                try:
                    data = _yaml.safe_load(candidate.read_text(encoding="utf-8"))
                    self._cached_template_config = (
                        data if isinstance(data, dict) else {}
                    )
                    return self._cached_template_config
                except Exception:
                    pass

        self._cached_template_config = {}
        return self._cached_template_config

    @property
    def template_variables(self) -> dict:
        """Load .variables.yaml from the template directory."""
        template_dir = self._templates_dir / "conversation" / "main"
        variables_file = template_dir / ".variables.yaml"
        if variables_file.is_file():
            import yaml

            try:
                data = yaml.safe_load(variables_file.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

    @property
    def variable_manager(self):
        return self._variable_manager

    def find_sop_file(self) -> Path | None:
        template_dir = self._templates_dir / "conversation" / "main"
        variables_dir = template_dir / "_variables" / "workflow"
        if not variables_dir.is_dir():
            return None
        for ext in (".jinja2", ".j2", ".md", ".yaml", ".yml"):
            candidate = variables_dir / f"sop{ext}"
            if candidate.is_file():
                return candidate
        return None


def _build_prompt_renderer(templates_dir: Path) -> _SimplePromptRenderer:
    """Build a PromptRenderer for the ConversationalInferencer."""
    return _SimplePromptRenderer(templates_dir)


class ConversationService:
    """Renders conversation prompts and manages LLM interactions."""

    def __init__(
        self,
        templates_dir: Path,
        llm_backend: str = "mock",
        working_dir: str | None = None,
        cache_dir: str | None = None,
        session_store: object | None = None,
        llm_model: str | None = None,
    ) -> None:
        self._templates_dir = templates_dir
        self._llm_backend = llm_backend
        self._llm_model = llm_model
        self._working_dir = working_dir or str(Path.home())
        self._cache_dir = cache_dir
        self._session_store = session_store
        self._inferencers: dict[
            str, object
        ] = {}  # session_id → ConversationalInferencer
        # session_id → ONE session-scoped RunContext root, reused across all turns
        # (each turn derives child("turn_N")). Loaded once from run_state/store.json;
        # mirrors the _inferencers cache lifecycle (evicted in lock-step). §9.4.
        self._session_roots: dict[str, object] = {}
        self._mock_prompt_cache: dict[
            str, dict
        ] = {}  # session_id → last prompt data (mock mode)
        # Per-session JsonLogger cache for RankEvolve-style structured logging.
        # Created lazily on first run_conversation_turn call so that we have
        # a session_dir to bind to. Reused across turns so the JSONL file
        # accumulates and the parts/ subfolders persist across the session.
        self._session_loggers: dict[str, Any] = {}
        # Per-session registry of agent-invoked background tasks (asyncio.Task),
        # so a resume/restore can cancel + await them before mutating disk.
        # Inner dict is keyed by task_id so reconcile_task_ref_statuses can
        # ask "is this task_id still alive?" via get_live_task_ids() — the
        # authoritative liveness signal that distinguishes a WS reconnect
        # (registry has the task) from a crash/restart (registry is empty).
        self._bg_tasks: dict[str, dict[str, asyncio.Task]] = {}
        self._template_manager = self._build_template_manager()

    def _build_template_manager(self):
        """Create TemplateManager for conversation prompt rendering.

        Uses the same TemplateManager pattern as create_role/executor.py:
        - Root: prompt_templates/
        - active_template_type: "main"
        - predefined_variables: True (loads .variables.yaml for {{ employee }})

        Falls back to raw Jinja2 rendering if TemplateManager is not available.
        """
        try:
            from rich_python_utils.string_utils.formatting.template_manager import (
                TemplateManager,
            )

            return TemplateManager(
                templates=[str(self._templates_dir), str(_AF_TEMPLATES_ROOT)],
                active_template_type="main",
                predefined_variables=True,
                cross_root_variable_lookup=True,  # Refactor 17
            )
        except ImportError:
            logger.warning(
                "rich_python_utils not available — using fallback Jinja2 rendering"
            )
            return None

    def render_prompt(self, session: dict, user_message: str) -> str:
        """Render the conversation prompt with session history + current turn.

        Builds the template feed:
        - conversation_history: list of {role, content} from session.messages
        - current_turn: {role: "manager", content: user_message}
        - employee: auto-injected from .variables.yaml (via TemplateManager)
        """
        messages = session.get("messages", [])

        # Build conversation_history from existing messages
        conversation_history = []
        for msg in messages:
            role = msg.get("role", "manager")
            if role in _UI_ONLY_ROLES:
                continue  # task_ref chips are UI-only — never feed to the LLM
            # Map OpenStartup roles to prompt template roles
            prompt_role = "manager" if role in ("manager", "user") else "assistant"
            conversation_history.append(
                {
                    "role": prompt_role,
                    "content": msg.get("content", ""),
                }
            )

        current_turn = {"role": "manager", "content": user_message}

        if self._template_manager is not None:
            return self._template_manager(
                "initial",
                active_template_root_space="conversation",
                conversation_history=conversation_history,
                current_turn=current_turn,
                # Workflow variables not passed — template guards with {% if defined %}
            )

        # Fallback: raw Jinja2 rendering
        return self._render_fallback(conversation_history, current_turn)

    @classmethod
    def AVAILABLE_BACKENDS(cls) -> list[str]:
        """Names of all backends registered in the global registry.

        Used by run_server.py's --llm-backend choices and by the
        /api/server/backends meta route.
        """
        from openteam.server.backends import get_registry

        return list(get_registry().list_backends())

    # ── Workflow-controlled conversation ────────────────────────────

    def _get_session_inferencer(self, session_id: str, session: dict | None = None):
        """Get or create a per-session ConversationalInferencer.

        Effective backend/model precedence:
          1. ``session["llm_backend"]`` / ``session["llm_model"]`` (per-session)
          2. ``self._llm_backend`` / ``self._llm_model`` (server default)

        ``mock`` is fast-pathed: returns ``None`` so the caller streams
        canned responses via ``astream_response`` without consulting the
        registry. Any other backend dispatches through
        ``BackendRegistry.create()``.
        """
        from openteam.server.backends import BackendBuildContext, get_registry

        sess = session or {}
        backend = sess.get("llm_backend") or self._llm_backend
        model = sess.get("llm_model") or self._llm_model

        if backend == "mock":
            return None

        if session_id in self._inferencers:
            return self._inferencers[session_id]

        ctx = BackendBuildContext(
            templates_dir=self._templates_dir,
            working_dir=self._working_dir,
            cache_dir=self._cache_dir,
            session_store=self._session_store,
            model_name=model,
            session_id=session_id,
        )
        try:
            inferencer = get_registry().create(backend, ctx)
        except Exception as e:
            logger.error("Failed to build inferencer for backend %r: %s", backend, e)
            raise

        self._inferencers[session_id] = inferencer
        return inferencer

    def _get_session_root(
        self,
        session_id: str,
        *,
        session_dir: "Path | None" = None,
        cwd: str = "",
    ):
        """Get or create the ONE session-scoped RunContext root for a session.

        Cached per ``session_id`` and reused across every turn — each turn derives
        ``child(f"turn_N")`` from it (§9.4). The Tier-1 ``RunStateStore`` is loaded
        ONCE from ``session_dir/run_state/store.json`` (resume across restart) and
        then kept in memory, so we don't reload the whole store every turn.

        Sharing one root across turns is concurrency-safe: the conversational path
        never mutates Tier-2 bindings — ``interactive`` and cancellation are threaded
        per turn via kwargs (and direct dispatcher injection), not via ``ctx.runtime``
        — and concurrent same-session turns derive distinct ``turn_N`` child nodes off
        the one shared in-memory store (which also avoids the per-turn-reload
        lost-update race the previous per-turn-root code had).

        Best-effort: returns ``None`` on any failure (incl. an AgentFoundation build
        without RunContext) so the caller falls back to legacy ``run_context=None``.
        """
        existing = self._session_roots.get(session_id)
        if existing is not None:
            return existing
        try:
            from agent_foundation.common.inferencers.inferencer_workspace import (
                InferencerWorkspace,
            )
            from agent_foundation.common.inferencers.run_context import (
                RunContext,
                RunStateStore,
            )

            store = None
            if session_dir is not None:
                store_path = Path(session_dir) / "run_state" / "store.json"
                if store_path.exists():
                    try:
                        store = RunStateStore.load(str(store_path))
                    except Exception:  # pragma: no cover - corrupt snapshot -> fresh
                        store = None
            root = RunContext.root(
                workspace=InferencerWorkspace(root=str(cwd)) if cwd else None,
                store=store,
            )
            self._session_roots[session_id] = root
            return root
        except Exception:  # pragma: no cover - never block a turn on context setup
            return None

    def set_session_backend(
        self,
        session_id: str,
        backend: str,
        model: str | None = None,
    ) -> dict | None:
        """Set the per-session LLM backend (and optional model).

        Validates ``backend`` against the registry, persists via
        ``session_store.update_session``, and evicts any cached inferencer
        so the next turn rebuilds with the new choice.

        Returns the updated session dict, or ``None`` if the session is
        unknown or no session store is wired.
        """
        from openteam.server.backends import get_registry

        registered = get_registry().list_backends()
        if backend not in registered:
            available = ", ".join(sorted(registered)) or "(none)"
            raise KeyError(
                f"Unknown backend {backend!r}. Registered backends: {available}"
            )

        # Evict cached inferencer so the next turn rebuilds with the new backend
        self._inferencers.pop(session_id, None)
        self._session_roots.pop(session_id, None)  # lock-step with _inferencers

        if self._session_store is None or not hasattr(
            self._session_store, "update_session"
        ):
            logger.warning(
                "set_session_backend(%s, %s): no session_store wired — "
                "in-memory eviction only",
                session_id,
                backend,
            )
            return None

        updates = {"llm_backend": backend, "llm_model": model}
        return self._session_store.update_session(session_id, updates)

    def evict_session_inferencer(self, session_id: str) -> None:
        """Drop cached per-session state (on delete, or to force a resume rebuild).

        Removes the cached inferencer + session root so the next turn rebuilds
        the CI (which re-restores ``sop_state`` in the factory) and re-binds the
        per-session JsonLogger after a truncate/restore rewrites ``session.jsonl``.
        """
        self._inferencers.pop(session_id, None)
        self._session_roots.pop(session_id, None)  # lock-step with _inferencers
        self._session_loggers.pop(session_id, None)  # re-bind session.jsonl on reload
        self._bg_tasks.pop(session_id, None)  # drained explicitly by resume/restore

    def _register_bg_task(
        self, session_id: str, task_id: str, task: asyncio.Task
    ) -> None:
        """Record an agent-invoked background task for later draining.

        Wired into the dispatcher per turn (``_register_bg_task`` callback) so
        when an async tool spawns its background ``_run`` we keep a handle.
        ``add_done_callback`` self-evicts the task when it finishes.

        Keyed by ``task_id`` so :meth:`get_live_task_ids` can answer the
        "is this chip's task still alive?" question that reconcile needs to
        distinguish a WS reconnect from a crash/restart.
        """
        bucket = self._bg_tasks.setdefault(session_id, {})
        bucket[task_id] = task

        def _evict(
            _t: asyncio.Task, _sid: str = session_id, _tid: str = task_id
        ) -> None:
            b = self._bg_tasks.get(_sid)
            # Identity guard: a re-registered task_id (unlikely but possible on
            # rapid dispatch/retry) must not be evicted by a stale done-callback
            # from a prior Task object.
            if b is not None and b.get(_tid) is _t:
                b.pop(_tid, None)
                if not b:
                    self._bg_tasks.pop(_sid, None)

        task.add_done_callback(_evict)

    def get_live_task_ids(self, session_id: str) -> set[str]:
        """Return the ``task_id``s of this session's background tasks that are
        still alive (not ``done()``).

        Used by ``reconcile_task_ref_statuses`` to skip chips whose background
        ``_run()`` is still executing. Pure read; no locks needed (single-
        threaded asyncio event loop). Empty when the session has no bg tasks
        or all completed (and were evicted via ``add_done_callback``).

        Callers on the resume path MUST capture this BEFORE calling
        :meth:`evict_session_inferencer` — that method pops the registry
        without cancelling tasks, so a post-evict call would return an empty
        set even though tasks are still running (they'd be orphans, but alive).
        """
        bucket = self._bg_tasks.get(session_id, {})
        return {tid for tid, t in bucket.items() if not t.done()}

    async def drain_session_background_tasks(self, session_id: str) -> None:
        """Cancel + await all in-flight background tasks for a session.

        MUST be called before any resume/restore disk mutation (checkpoint copy,
        ``turn_NNN`` rmtree, task-workspace rmtree) so a live writer can't race
        the copy/delete. ``CancelledError`` is ``BaseException``-derived, so it
        skips the background ``_run``'s ``except Exception``, runs its ``finally``
        (per-task queue cleanup), and the task ends cancelled.
        """
        tasks = [t for t in self._bg_tasks.get(session_id, {}).values() if not t.done()]
        if not tasks:
            self._bg_tasks.pop(session_id, None)
            return
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._bg_tasks.pop(session_id, None)

    def get_last_prompt_data(self, session_id: str) -> dict:
        """Return cached prompt data from the last turn for a given session.

        Reads _last_template_source, _last_template_feed, _last_rendered_prompt,
        _last_template_config from the ConversationalInferencer after run_agentic_loop().
        Returns empty dict if session has no inferencer or no data yet.

        The template_feed is sanitized — non-JSON-serializable objects (e.g. SOP,
        StateGraphTracker) that get spread into the feed via **prior_context are
        converted to their string representation or omitted.
        """
        inf = self._inferencers.get(session_id)
        if inf is None:
            # Fall back to mock prompt cache (populated by astream_response in mock mode)
            return self._mock_prompt_cache.get(session_id, {})
        return {
            "template_source": getattr(inf, "_last_template_source", "") or "",
            "template_feed": self._sanitize_feed(
                getattr(inf, "_last_template_feed", {}) or {}
            ),
            "rendered_prompt": getattr(inf, "_last_rendered_prompt", "") or "",
            "template_config": getattr(inf, "_last_template_config", {}) or {},
        }

    @staticmethod
    def _sanitize_feed(feed: dict) -> dict:
        """Make template_feed JSON-serializable.

        The feed dict contains **prior_context spread, which includes non-JSON
        objects like SOP (from _sop key), StateGraphTracker, SOPPhase, etc.
        This method converts them to safe representations.
        """
        import json

        result = {}
        for key, value in feed.items():
            # Skip internal/private keys that are never useful for display
            if key.startswith("_"):
                continue
            try:
                # Test if value is JSON serializable
                json.dumps(value)
                result[key] = value
            except (TypeError, ValueError):
                # Convert non-serializable objects to string repr
                try:
                    result[key] = str(value)
                except Exception:
                    result[key] = f"<non-serializable: {type(value).__name__}>"
        return result

    def _compute_session_context(self, session: dict) -> dict:
        """Build prior_context dict from session workflow state — called once per turn."""
        from agent_foundation.server.workflow_context import WorkflowContext

        wc_dict = session.get("workflow_context", {})
        if wc_dict:
            wc = WorkflowContext.from_dict(wc_dict)
        else:
            wc = WorkflowContext()

        result: dict = {
            "session_root_path": session.get("session_root_path") or self._working_dir,
            "workflow_status": wc.to_status_text(),
            "workflow_description": wc.workflow_description,
            "strategy": wc.strategy,
            "current_phase": wc.current_phase,
            "phase_status": wc.phase_status,
            "completed_phases": wc.completed_phases,
            "phase_outputs": wc.phase_outputs,
        }
        # A4 (v3): hoist any `<tool>__<key>` entries persisted to
        # phase_outputs (by tool_dispatcher.py's A4 persist block) to
        # top-level prior_context so the SOP Jinja renderer finds
        # `{{ research_propose__proposals_path }}` after a server restart.
        # Pairs with the dispatcher-side A1 publish + A4 persist.
        for k, v in (wc.phase_outputs or {}).items():
            if isinstance(k, str) and "__" in k and k not in result:
                result[k] = v
        return result

    def _load_workflow_description(self) -> str:
        """Load the default workflow description from prompt templates."""
        desc_file = (
            self._templates_dir
            / "conversation"
            / "main"
            / "_variables"
            / "workflow_description"
            / "default.jinja2"
        )
        return desc_file.read_text(encoding="utf-8") if desc_file.is_file() else ""

    def _persist_workflow_updates(
        self, session: dict, prior_context: dict, data_service: object | None
    ) -> None:
        """Persist updated workflow state from the inferencer's prior_context."""
        from agent_foundation.server.workflow_context import (
            WorkflowContext,
            WorkflowPhaseRecord,
        )

        # Rebuild from prior_context (inferencer's live state, updated in-place
        # by context_updates during the turn) — NOT from the stale session dict.
        completed_raw = prior_context.get("completed_phases", [])
        completed = []
        for r in completed_raw:
            if isinstance(r, WorkflowPhaseRecord):
                completed.append(r)
            elif isinstance(r, dict):
                completed.append(WorkflowPhaseRecord.from_dict(r))

        wc = WorkflowContext(
            strategy=prior_context.get("strategy", "default"),
            workflow_description=prior_context.get("workflow_description", ""),
            current_phase=prior_context.get("current_phase", "idle"),
            phase_status=prior_context.get("phase_status", "idle"),
            completed_phases=completed,
            phase_outputs=prior_context.get("phase_outputs", {}),
        )

        if data_service and hasattr(data_service, "update_workflow_context"):
            data_service.update_workflow_context(session["id"], wc.to_dict())
        elif self._session_store and hasattr(
            self._session_store, "update_workflow_context"
        ):
            self._session_store.update_workflow_context(session["id"], wc.to_dict())

        root_path = prior_context.get("session_root_path", "")
        if root_path and root_path != session.get("session_root_path", ""):
            session["session_root_path"] = root_path
            if self._session_store and hasattr(self._session_store, "update_session"):
                try:
                    self._session_store.update_session(
                        session["id"], {"session_root_path": root_path}
                    )
                except Exception:
                    pass

    # ── SOP-state persistence (Piece F) ─────────────────────────────

    @staticmethod
    def _sop_snapshot(inferencer: Any) -> dict[str, Any]:
        """Serialize the inferencer's live SOP state (active + suspended stack).

        Returns ``{"sop_state": <dict|None>, "suspended_sops": [<dict>, ...]}``.
        ``SOPState.to_dict()`` drops the non-serializable ``.sop`` graph; it is
        reattached on restore (in ``factories._restore_sop_state``) via
        ``build_sop_state(extra_sop_dirs=...)``.
        """

        def _td(s: Any) -> dict[str, Any] | None:
            if s is None:
                return None
            try:
                return s.to_dict()
            except Exception:
                return None

        sop = getattr(inferencer, "sop_state", None)
        suspended = getattr(inferencer, "_suspended_sops", []) or []
        return {
            "sop_state": _td(sop),
            "suspended_sops": [d for d in (_td(s) for s in suspended) if d is not None],
        }

    def _write_sop_snapshot(self, path: Path, inferencer: Any) -> None:
        """Atomically write the pre-turn SOP snapshot to ``path``."""
        write_json_atomic(path, self._sop_snapshot(inferencer))

    def _get_or_create_session_logger(self, session_id: str, data_service):
        """Lazily create the per-session JsonLogger.

        Adapts RankEvolve's pattern (rich_python_utils.io_utils.json_io.JsonLogger
        configured with is_artifact + parts_min_size=0 + parts_file_namer) to
        OpenStartup's session layout, but bypasses RankEvolve's `SessionLogger`
        wrapper because it always creates a NEW nested subdirectory inside the
        passed `base_log_dir` — incompatible with our existing session dirs.
        """
        if session_id in self._session_loggers:
            return self._session_loggers[session_id]
        if data_service is None or not hasattr(data_service, "get_session_dir"):
            return None
        session_dir = data_service.get_session_dir(session_id)
        if session_dir is None:
            return None
        try:
            from rich_python_utils.io_utils.json_io import JsonLogger
        except ImportError:
            logger.debug(
                "JsonLogger not available; skipping structured session logging"
            )
            return None
        json_logger = JsonLogger(
            file_path=str(session_dir / "session.jsonl"),
            append=True,
            parts_min_size=0,  # all fields → parts/ files (matches RankEvolve)
            is_artifact=True,  # auto-sets parts_key_paths='*'
            parts_file_namer=lambda obj: obj.get("type", "")
            if isinstance(obj, dict)
            else "",
            # space_ext_mode omitted: only affects space= param, not group=/subfolder=
        )
        self._session_loggers[session_id] = json_logger
        return json_logger

    async def run_conversation_turn(
        self, session: dict, user_message: str, *, interactive, data_service=None
    ):
        """Run a full conversation turn (fresh USER turn) with the agentic loop.

        Allocates the next canonical user-turn number, seeds the turn-entry
        artifacts (user_input.txt + the pre-turn sop_state_in.json boundary +
        turn.json {rounds: []}), then delegates the loop to the shared
        ``_run_agentic_turn`` helper. Returns AgenticResult after
        run_agentic_loop() completes; streaming happens inside the loop via
        interactive.stream_token_batches().
        """
        sid = session["id"]
        session_dir = (
            data_service.get_session_dir(sid)
            if data_service is not None and hasattr(data_service, "get_session_dir")
            else None
        )

        # Count existing turn dirs → allocate EXACTLY ONE user-turn number for
        # this call. Prefer new-style (turn_NNN/ at root, RankEvolve layout); fall
        # back to legacy nested (turns/turn_NNN/).
        initial_turn = 0
        if session_dir is not None:
            new_style = sum(
                1
                for p in session_dir.iterdir()
                if p.is_dir() and p.name.startswith("turn_") and p.name != "turns"
            )
            if new_style > 0:
                initial_turn = new_style
            else:
                legacy_dir = session_dir / "turns"
                if legacy_dir.is_dir():
                    initial_turn = sum(
                        1
                        for p in legacy_dir.iterdir()
                        if p.is_dir() and p.name.startswith("turn_")
                    )
        user_turn = initial_turn + 1

        # At turn ENTRY, seed the turn root: turn_NNN/user_input.txt + the pre-turn
        # SOP boundary (sop_state_in.json, read by truncate_session_at_message /
        # _read_sop_boundary) + turn.json {rounds: []}. INTENTIONALLY only on the
        # fresh-turn path — resume_conversation_from_round must NOT re-run this or
        # it would clobber turn_T/sop_state_in.json (the turn-entry SOP boundary)
        # with round-Y inferencer state and corrupt a later turn-resume of turn T.
        if session_dir is not None:
            # Backend-aware fetch (honors a per-session llm_backend override); also
            # gives the live SOP state for the pre-turn boundary snapshot.
            _inf = self._get_session_inferencer(sid, session=session)
            try:
                turn_dir = session_dir / f"turn_{user_turn:03d}"
                turn_dir.mkdir(parents=True, exist_ok=True)
                (turn_dir / "user_input.txt").write_text(user_message, encoding="utf-8")
                if _inf is not None:
                    self._write_sop_snapshot(turn_dir / "sop_state_in.json", _inf)
            except Exception as e:
                logger.debug("Turn-entry artifact write failed: %s", e)
        if data_service is not None and hasattr(
            data_service, "update_turn_root_summary"
        ):
            try:
                data_service.update_turn_root_summary(
                    sid,
                    user_turn,
                    {
                        "user_input": user_message,
                        "turn_number": user_turn,
                        "session_id": sid,
                        "rounds": [],
                    },
                )
            except Exception as e:
                logger.debug("Turn-entry root summary write failed: %s", e)

        return await self._run_agentic_turn(
            session,
            user_turn=user_turn,
            user_message=user_message,
            interactive=interactive,
            data_service=data_service,
            resume_blob=None,
        )

    async def resume_conversation_from_round(
        self,
        session: dict,
        *,
        target_turn: int,
        target_round: int,
        resume_blob: dict,
        interactive,
        data_service=None,
    ):
        """Auto-forward re-entry: regenerate turn ``target_turn`` from assistant
        round ``target_round``. Rounds ``1..target_round-1`` are kept (the caller's
        truncate removed round >= target_round and read the round-entry blob into
        ``resume_blob``); the loop regenerates round ``target_round`` onward under
        the SAME turn, driven by a self-continuation — NO new user message.

        Does NOT allocate/seed a turn: turn ``target_turn`` already exists and its
        user_input.txt / sop_state_in.json MUST be preserved. SOP is reattached by
        the factory (_restore_sop_state) on the rebuilt CI; the blob restores
        messages/prior_context/dynamic_context via _restore_pause_state(
        reattach_sop=False) inside _run_agentic_turn.
        """
        sid = session["id"]
        session_dir = (
            data_service.get_session_dir(sid)
            if data_service is not None and hasattr(data_service, "get_session_dir")
            else None
        )
        # The turn's original user input (for per-round artifacts + round-1 content).
        user_message = ""
        if session_dir is not None:
            uin = session_dir / f"turn_{target_turn:03d}" / "user_input.txt"
            try:
                if uin.is_file():
                    user_message = uin.read_text(encoding="utf-8")
            except OSError as e:
                logger.debug("resume: user_input.txt read failed: %s", e)
        if not user_message:
            for _m in reversed(session.get("messages", [])):
                if _m.get("role") in ("manager", "user"):
                    user_message = _m.get("content", "") or ""
                    break

        # What round M renders with: the blob's captured content (authoritative);
        # fallback = the continuation sentinel (M>1) or the user input (M==1).
        content = resume_blob.get("content") or (
            _CONTINUE_AFTER_TOOLS if target_round > 1 else user_message
        )

        return await self._run_agentic_turn(
            session,
            user_turn=target_turn,
            user_message=user_message,
            interactive=interactive,
            data_service=data_service,
            resume_blob=resume_blob,
            content=content,
        )

    async def resume_conversation_from_widget(
        self,
        session: dict,
        *,
        marker: dict,
        blob: dict,
        raw_value,
        interactive,
        data_service=None,
    ):
        """Recover an unanswered conversation widget after a reconnect/restart:
        inject the user's answer into the loop at the widget's iteration (restored
        from ``blob``) so it applies to the EXACT persisted widget with NO LLM
        re-inference, then continue the SOP. Reconstructs the ConversationTool
        objects from the durable marker; clears the marker when done."""
        from agent_foundation.common.inferencers.agentic_inferencers.conversational.conversation_tools import (  # noqa: E501
            ConversationTool,
        )

        def _revive(t):
            if isinstance(t, ConversationTool):
                return t
            if isinstance(t, dict) and hasattr(ConversationTool, "from_dict"):
                return ConversationTool.from_dict(t)
            return t

        pending_widget = {
            "raw_value": raw_value,
            "tools": [_revive(t) for t in (marker.get("tools") or [])],
            "action_tools": marker.get("action_tools") or [],
        }
        target_turn = int(marker.get("turn_number") or blob.get("turn_number") or 1)
        try:
            return await self._run_agentic_turn(
                session,
                user_turn=target_turn,
                user_message="",
                interactive=interactive,
                data_service=data_service,
                resume_blob=blob,
                content=_CONTINUE_AFTER_TOOLS,
                pending_widget=pending_widget,
            )
        finally:
            # Clear-at-END (idempotency): the widget is resolved once the
            # continuation runs. Cleared in ``finally`` so an error can't leave a
            # stale marker that re-arms a ghost widget on the next connect
            # (at-most-once; full message-dedup idempotency is a follow-up).
            if data_service is not None and hasattr(data_service, "session_store"):
                try:
                    data_service.session_store.clear_pending_input(session["id"])
                except Exception as e:
                    logger.warning("clear_pending_input failed: %s", e)

    async def _run_agentic_turn(
        self,
        session: dict,
        *,
        user_turn: int,
        user_message: str,
        interactive,
        data_service=None,
        resume_blob: dict | None = None,
        content: str | None = None,
        pending_widget: dict | None = None,
    ):
        """Shared agentic-loop driver for a fresh turn (resume_blob=None) and a
        round-resume (resume_blob set). Owns the dispatcher per-turn injections,
        the per-round persistence closures, the run_agentic_loop call, and the
        turn-exit persistence. The caller owns turn-number allocation and (fresh
        turn only) turn-entry seeding.
        """
        sid = session["id"]
        # Backend-aware fetch so a per-session llm_backend override survives an
        # eviction+rebuild (the resume path evicts the CI before calling us).
        inferencer = self._get_session_inferencer(sid, session=session)
        if inferencer is None:
            raise RuntimeError("ConversationalInferencer not initialized")

        session_dir = (
            data_service.get_session_dir(sid)
            if data_service is not None and hasattr(data_service, "get_session_dir")
            else None
        )
        # Bind (or re-bind, after an eviction) the per-session structured logger.
        json_logger = self._get_or_create_session_logger(sid, data_service)

        # ── Dispatcher per-turn injections (BOTH paths — all load-bearing on
        # resume too, since regenerated rounds may dispatch async tools) ──
        #   _interactive: gates async-tool dispatch + task/dashboard WS emission
        #   _current_turn: stamps task_meta/task_ref/dashboard turn_number
        #   _register_bg_task: registers spawned bg tasks so a later resume/restore
        #     can drain (cancel+await) them before mutating the session on disk
        if hasattr(inferencer, "_tool_dispatcher"):
            inferencer._tool_dispatcher._interactive = interactive
            inferencer._tool_dispatcher._current_turn = user_turn
            inferencer._tool_dispatcher._register_bg_task = (
                lambda t, tid, _sid=sid: self._register_bg_task(_sid, tid, t)
            )

        # ── Prepare the inferencer's conversation state ──────────────────
        if resume_blob is None:
            # Fresh turn: seed prior_context + messages from the session.
            inferencer.set_prior_context(self._compute_session_context(session))
            conv_messages = [
                {
                    "role": (
                        "user" if m.get("role") in ("manager", "user") else "assistant"
                    ),
                    "content": m.get("content", ""),
                }
                for m in session.get("messages", [])
                if m.get("role") not in _UI_ONLY_ROLES
            ]
            inferencer.set_messages(conv_messages)
        else:
            # Round-resume: restore the round-ENTRY snapshot (full _messages incl.
            # tool-result / widget / synthetic turns + prior_context +
            # dynamic_context) and set the start_iteration marker. SOP is left to
            # the factory restore (already applied on this rebuilt CI);
            # reattach_sop=False avoids the CI's non-extra-dirs-aware
            # _reload_sop_definition raising SOPNotFound on OpenTeam SOPs.
            inferencer._restore_pause_state(resume_blob, reattach_sop=False)

        # Widget recovery: seed the injected answer so the loop's pending-widget
        # branch (fired at the widget's iteration, restored from resume_blob)
        # applies it deterministically — no re-inference, exact persisted widget.
        if pending_widget is not None:
            inferencer._pending_widget_result = pending_widget

        # The current RoundContext (minted in on_round_start, consumed in
        # on_round_complete). Kept on a 1-slot list so the closures share it.
        round_ctx_holder: list[dict[str, Any] | None] = [None]

        # Parent user-message id; used as parent_user_message_id on each round.
        parent_user_message_id = None
        for _m in reversed(session.get("messages", [])):
            if _m.get("role") in ("manager", "user"):
                parent_user_message_id = _m.get("id")
                break

        # ── on_new_turn: NEUTERED ────────────────────────────────────────
        # Returns the SAME fixed user_turn so the loop's turn_number stays
        # constant (send_turn_boundary won't spuriously fire) and the round hooks
        # own all per-turn/round artifacts.
        async def _on_new_turn(prev_turn: int, widget_response: Any) -> int:
            return user_turn

        # ── on_round_start: mint RoundContext, mkdir round dir, snapshot ──
        async def _on_round_start(
            iteration: int, turn_number: int
        ) -> dict[str, Any] | None:
            round_index = iteration + 1
            message_id = uuid.uuid4().hex[:12]
            round_dir = ""
            if session_dir is not None:
                rd = session_dir / f"turn_{user_turn:03d}" / f"round_{round_index:03d}"
                try:
                    rd.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.debug("[_on_round_start] round dir mkdir failed: %s", e)
                round_dir = str(rd)
                # Per-round resume snapshot (round-ENTRY state — this hook fires at
                # the TOP of the loop iteration, BEFORE render/infer, so
                # inferencer._messages is exactly the state entering this round).
                # PURE blob (no ctx-node mirror) so snapshotting every round never
                # pollutes run_state/store.json. Best-effort; never block a round.
                try:
                    write_json_atomic(
                        Path(round_dir) / "resume_state.json",
                        inferencer._conversation_blob(
                            turn_number=user_turn, iteration=iteration
                        ),
                    )
                except Exception as e:
                    logger.debug("[_on_round_start] resume snapshot failed: %s", e)
            # Stamp the current round on the dispatcher so async tasks dispatched
            # this round record round_number (round-granular keep/drop on resume).
            if hasattr(inferencer, "_tool_dispatcher"):
                inferencer._tool_dispatcher._current_round = round_index
            ctx: dict[str, Any] = {
                "message_id": message_id,
                "round_index": round_index,
                "turn_number": user_turn,
                "cache_folder": round_dir,
                "round_dir": round_dir,
                "parent_user_message_id": parent_user_message_id,
                "session_id": sid,
            }
            round_ctx_holder[0] = ctx
            return ctx

        # ── on_round_complete: SOLE turn-data writer + per-round persist ─
        async def _on_round_complete(
            inf: Any,
            iteration: int,
            turn_number: int,
            raw_response: str,
            clean_response: str,
            display_text: str,
            conv_response: Any,
        ) -> None:
            ctx = round_ctx_holder[0] or {}
            round_index = ctx.get("round_index", iteration + 1)
            message_id = ctx.get("message_id") or uuid.uuid4().hex[:12]

            # 1) Per-round artifact (turn_NNN/round_MMM/…)
            prompt_data = {
                "rendered_prompt": getattr(inf, "_last_rendered_prompt", "") or "",
                "template_source": getattr(inf, "_last_template_source", "") or "",
                "template_feed": self._sanitize_feed(
                    getattr(inf, "_last_template_feed", {}) or {}
                ),
                "template_config": getattr(inf, "_last_template_config", {}) or {},
                "inference_response": clean_response,
                "raw_response": raw_response,
                "user_input": user_message,
            }
            if data_service is not None and hasattr(data_service, "save_turn_data"):
                try:
                    data_service.save_turn_data(
                        sid, user_turn, prompt_data, round=round_index
                    )
                except Exception as e:
                    logger.debug("[_on_round_complete] save_turn_data failed: %s", e)

            # Keep the interactive's inline prompt_data cache fresh for any
            # subsequent widget preamble in this round.
            if hasattr(interactive, "_last_prompt_data"):
                interactive._last_prompt_data = prompt_data

            # 2) Commit the assistant bubble ONLY when there is displayable text.
            if (
                display_text
                and data_service is not None
                and hasattr(data_service, "append_message")
            ):
                try:
                    data_service.append_message(
                        sid,
                        {
                            "id": message_id,
                            "role": "assistant",
                            "content": display_text,
                            "turn_number": user_turn,
                            "round_index": round_index,
                            "parent_user_message_id": ctx.get("parent_user_message_id"),
                            "agent_name": "Orchestrator",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                except Exception as e:
                    logger.debug("[_on_round_complete] append_message failed: %s", e)

            # 3) ALWAYS emit the per-round message_end (balanced terminal). When
            # display_text is "" nothing is committed UI-side.
            if hasattr(interactive, "send_round_message_end"):
                try:
                    await interactive.send_round_message_end(
                        message_id=message_id,
                        round_index=round_index,
                        turn_number=user_turn,
                        final_content=display_text,
                    )
                except Exception as e:
                    logger.debug(
                        "[_on_round_complete] send_round_message_end failed: %s", e
                    )

            # 4) Update the root turn summary once per round (assemble display text).
            if data_service is not None and hasattr(
                data_service, "update_turn_root_summary"
            ):
                try:
                    prev = (
                        data_service.get_turn_data(sid, user_turn)
                        if hasattr(data_service, "get_turn_data")
                        else None
                    ) or {}
                    assembled = prev.get("assembled_summary", "") or ""
                    if display_text:
                        assembled = (
                            (assembled + "\n\n" + display_text)
                            if assembled
                            else display_text
                        )
                    data_service.update_turn_root_summary(
                        sid,
                        user_turn,
                        {
                            "user_input": user_message,
                            "turn_number": user_turn,
                            "latest_round": round_index,
                            "assembled_summary": assembled,
                            "session_id": sid,
                        },
                    )
                except Exception as e:
                    logger.debug(
                        "[_on_round_complete] root summary update failed: %s", e
                    )

        # §9.4: derive this turn's context from the ONE session-scoped root
        # (cached + reused across all turns; its run-state store is loaded ONCE in
        # _get_session_root, not reloaded per turn). Each turn is a child("turn_N")
        # off that root. Best-effort: a None root falls back to the legacy call
        # (run_context=None -> byte-identical). Never block a turn on this.
        _turn_store_path = (
            session_dir / "run_state" / "store.json"
            if session_dir is not None
            else None
        )
        _cwd = getattr(inferencer, "effective_cwd", "") or ""
        _session_root = self._get_session_root(sid, session_dir=session_dir, cwd=_cwd)
        _turn_root = (
            _session_root.child(f"turn_{user_turn}")
            if _session_root is not None
            else None
        )

        # Run the full agentic loop. `content` is what round `start_iteration`
        # renders with — user_message for a fresh turn, the blob's continuation
        # content on resume. Turn identity is the fixed user_turn; the round hooks
        # own per-round cache_folder placement + persistence.
        _content = content if content is not None else user_message
        try:
            result = await inferencer.run_agentic_loop(
                _content,
                interactive=interactive,
                session_id=sid,
                on_new_turn=_on_new_turn,
                on_round_start=_on_round_start,
                on_round_complete=_on_round_complete,
                turn_number=user_turn,
                run_context=_turn_root,
            )
        finally:
            # M9/§9.4: persist the session run-state store on EVERY exit (success/
            # error/cancel) so an interrupted turn can resume — parity with task/SOP.
            # Saving the session root persists all turns (the turn child shares its
            # store by reference).
            if _session_root is not None and _turn_store_path is not None:
                try:
                    _session_root._store.save(str(_turn_store_path))
                except Exception:  # pragma: no cover - best-effort
                    pass
            # Piece F: persist the live SOP state (active + suspended stack) at
            # turn exit so it survives restart/eviction. Stored as a top-level
            # session field (NOT inside workflow_context) so the turn-end
            # _persist_workflow_updates cannot clobber it. Restored on the next
            # CI build by factories._restore_sop_state.
            if self._session_store is not None:
                try:
                    _snap = self._sop_snapshot(inferencer)
                    self._session_store.update_session(
                        sid,
                        {
                            "sop_state": _snap["sop_state"],
                            "suspended_sops": _snap["suspended_sops"],
                        },
                    )
                except Exception as e:  # pragma: no cover - best-effort
                    logger.debug("sop_state persist failed: %s", e)

        # Stash the canonical turn number on the result for the route layer.
        try:
            result.turn_number = user_turn  # type: ignore[attr-defined]
        except Exception:
            pass

        # Persist updated workflow context (session-state, NOT a per-turn artifact).
        self._persist_workflow_updates(session, inferencer.prior_context, data_service)

        return result

    async def astream_response(self, session: dict, user_message: str):
        """Stream response tokens for the user's message.

        Yields individual text chunks. For mock backend, simulates streaming
        by yielding word-by-word. For rovodev backend, streams real LLM output
        line-by-line from ``acli rovodev run``.

        The caller is responsible for persisting messages — this method
        only renders the prompt, calls the LLM, and yields chunks.
        """
        if self._llm_backend == "mock":
            rendered_prompt = self.render_prompt(session, user_message)
            raw_response = self._mock_response(user_message)
            parsed = self._parse_response(raw_response)
            # Cache prompt data so get_last_prompt_data() works in mock mode
            sid = session.get("id", "")
            self._mock_prompt_cache[sid] = {
                "template_source": "(mock mode — no Jinja2 template rendered)",
                "template_feed": {"user_message": user_message},
                "rendered_prompt": rendered_prompt,
                "template_config": {"backend": "mock"},
            }
            # Simulate streaming: yield word-by-word with tiny delays
            words = parsed.split(" ")
            for i, word in enumerate(words):
                chunk = word if i == 0 else " " + word
                yield chunk
                await asyncio.sleep(0.03)  # 30ms per word — feels natural

        else:
            # Generic agentic-backend path: any registered non-mock backend.
            # Safety fallback only — the WS route prefers run_conversation_turn().
            inferencer = self._get_session_inferencer(session["id"], session=session)
            if inferencer is None:
                raise RuntimeError(
                    f"No inferencer registered for backend {self._llm_backend!r}. "
                    f"Available: {', '.join(sorted(self.AVAILABLE_BACKENDS()))}"
                )

            # Sync conversation history from session into the inferencer
            messages = session.get("messages", [])
            conv_messages = []
            for msg in messages:
                role = msg.get("role", "manager")
                if role in _UI_ONLY_ROLES:
                    continue  # task_ref chips are UI-only — never feed to the LLM
                prompt_role = "user" if role in ("manager", "user") else "assistant"
                conv_messages.append(
                    {"role": prompt_role, "content": msg.get("content", "")}
                )
            inferencer.set_messages(conv_messages)

            # §9.4: mint a best-effort EPHEMERAL per-stream root RunContext. Unlike
            # run_conversation_turn(), this fallback path is INTENTIONALLY not tied to
            # the cached session root: it doesn't drive run_agentic_loop and doesn't
            # persist a store, so a one-off stream context is correct here (sharing the
            # session root would wrongly persist non-loop state). Degrades to None ->
            # legacy, byte-identical, on any failure. Never block streaming on setup.
            _stream_root = None
            try:
                from agent_foundation.common.inferencers.inferencer_workspace import (
                    InferencerWorkspace,
                )
                from agent_foundation.common.inferencers.run_context import RunContext

                _cwd = getattr(inferencer, "effective_cwd", "") or ""
                _stream_root = RunContext.root(
                    workspace=InferencerWorkspace(root=str(_cwd)) if _cwd else None
                ).child("stream")
            except Exception:  # pragma: no cover - never block streaming on setup
                _stream_root = None

            # Stream via base ainfer_streaming() — NOTE: this bypasses run_agentic_loop(),
            # so workflow context, SOP, and tools are NOT active in this path.
            # Prefer run_conversation_turn() for full workflow-controlled streaming.
            full_response = ""
            async for chunk in inferencer.ainfer_streaming(
                user_message, run_context=_stream_root
            ):
                chunk_str = str(chunk) if not isinstance(chunk, str) else chunk
                if chunk_str:
                    full_response += chunk_str
                    yield chunk_str

            inferencer.add_message("user", user_message)
            inferencer.add_message("assistant", full_response)

    async def get_response(self, session: dict, user_message: str) -> str:
        """Get an AI response for the user's message.

        1. Render prompt with session history
        2. Call LLM backend
        3. Parse <Response> tags from output
        4. Return cleaned response text
        """
        rendered_prompt = self.render_prompt(session, user_message)

        if self._llm_backend == "mock":
            raw_response = self._mock_response(user_message)
        else:
            raw_response = await self._call_llm(rendered_prompt)

        return self._parse_response(raw_response)

    def _mock_response(self, user_message: str) -> str:
        """Generate a mock response for testing without an LLM."""
        return (
            f"<Response>\n"
            f'I received your message: "{user_message}"\n\n'
            f"As the Orchestrator, I can help you with team management, "
            f"project oversight, task coordination, and more. "
            f"This is currently running in mock mode — connect an LLM backend "
            f"to enable full AI conversations.\n"
            f"</Response>"
        )

    async def _call_llm(self, rendered_prompt: str) -> str:
        """Single-shot prompt path (legacy ``get_response``).

        Real backends are reached through ``_get_session_inferencer`` +
        ``run_conversation_turn`` / ``astream_response``. This single-shot
        path has no caller for non-mock backends and is intentionally not
        implemented.
        """
        raise RuntimeError(
            f"No single-shot inferencer for backend {self._llm_backend!r}. "
            f"Available backends: {', '.join(sorted(self.AVAILABLE_BACKENDS()))}. "
            f"Use astream_response() or run_conversation_turn() instead."
        )

    @staticmethod
    def _parse_response(raw_output: str) -> str:
        """Extract content from <Response>...</Response> tags.

        Uses the LAST match (not first), matching rankevolve's extract_delimited()
        behavior — handles cases where the LLM outputs multiple attempts.
        Falls back to full output if no tags found (graceful degradation).
        """
        matches = re.findall(r"<Response>(.*?)</Response>", raw_output, re.DOTALL)
        if matches:
            return matches[-1].strip()  # Last match — final attempt
        # No tags — return full output (may happen with some LLM backends)
        return raw_output.strip()

    def _render_fallback(self, conversation_history: list, current_turn: dict) -> str:
        """Fallback rendering when TemplateManager is not available.

        Uses raw Jinja2 to render the conversation template directly.
        """
        from jinja2 import Environment, FileSystemLoader

        template_dir = self._templates_dir / "conversation" / "main"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            undefined=__import__("jinja2").Undefined,  # silent undefined
        )
        template = env.get_template("initial.jinja2")
        return template.render(
            conversation_history=conversation_history,
            current_turn=current_turn,
        )
