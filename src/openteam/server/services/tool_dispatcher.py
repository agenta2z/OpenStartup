"""Registry-driven generic tool dispatcher.

Reads the 'executor' field from each tool's tool.json (via source_path on
ToolDefinition) and imports the callable at construction time. Conforms to
the ToolExecutorCallable protocol: async (tool_name, arguments) → ToolExecutionResult.

Usage::

    dispatcher = ToolDispatcher(
        tool_registry=tool_registry,          # {name: ToolDefinition}
        integration_executor=integration_executor,
        session_context={
            "working_dir": "/path/to/working_dir",
            "cloud_id": "...",
            "uct_token": "...",
        },
    )

    # In tool_executor closure:
    result = await dispatcher(tool_name, arguments)

Adding a new tool:
    1. Add "executor": "module.path:execute" to tool.json
    2. Implement execute(arguments, session_context) -> ToolExecutionResult in executor.py
    No changes needed to dispatch.py or conversation_service.py.
"""

from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agent_foundation.resources.tools.models import ToolDefinition
from openteam.server.services.json_io import primary_val_from_args, write_json_atomic

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    """ISO 8601 UTC timestamp (matches SessionStore message timestamps)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ToolDispatcher:
    """Registry-driven generic tool dispatcher.

    Reads 'executor' field from each tool's tool.json (via source_path on
    ToolDefinition). Falls back to IntegrationToolExecutor for integration
    tools (Slack, TWG). Session context is captured at construction —
    __call__ conforms to ToolExecutorCallable protocol.
    """

    def __init__(
        self,
        tool_registry: dict[str, ToolDefinition],
        integration_executor: Any,
        session_context: dict[str, Any],
        interactive: Any = None,
        session_store: Any = None,
    ) -> None:
        self._integration_executor = integration_executor
        self._session_context = session_context
        self._interactive = interactive  # WebSocketInteractive — injected per-turn
        self._tool_registry = tool_registry  # kept for asynchronous flag check
        self._executor_map: dict[str, Callable] = {}
        # Resumability wiring:
        #   _session_store     — SessionStore (sidecars, task_ref, reuse matcher); set by factory
        #   _inferencer        — back-ref to the ConversationalInferencer for live sop_state; set by factory
        #   _current_turn      — current user_turn; injected per-turn by ConversationService
        #   _current_round     — current round_index; injected per-round by ConversationService._on_round_start
        #   _register_bg_task  — callback(task, task_id) → per-session bg-task registry; injected per-turn
        #   _primary_arg_map   — tool_name → primary-arg key (for SOP-scoped task keys)
        self._session_store = session_store
        self._inferencer: Any = None
        self._current_turn = 0
        # Callback signature: (task, task_id) — task_id is threaded through so
        # ConversationService's registry can key by it (needed by
        # get_live_task_ids for liveness-aware reconcile).
        self._register_bg_task: Callable[[Any, str], None] | None = None
        # Values are the resolved primary-arg NAME (str), or the sentinel ``False``
        # for a tool that declares ``"primary_arg": null`` (an explicit opt-out —
        # key on sop/phase/tool only). ``None`` (unresolved) is never stored.
        self._primary_arg_map: dict[str, str | bool] = {}
        self._primary_arg_type_map: dict[str, str] = {}
        # Adopt pre-feature (sidecar-less) task workspaces once per dispatcher,
        # before the first reuse lookup (see _dispatch_as_task).
        self._backfill_done = False
        self._load_executors(tool_registry)
        logger.info(
            "[ToolDispatcher] Loaded %d registry executors: %s",
            len(self._executor_map),
            list(self._executor_map.keys()),
        )

    def _load_executors(self, tool_registry: dict[str, ToolDefinition]) -> None:
        """Read 'executor' from each tool's source tool.json, import the callable."""
        for name, tool_def in tool_registry.items():
            if not tool_def.source_path:  # guard: skip tools without source_path
                continue
            tool_json_path = Path(tool_def.source_path)
            if not tool_json_path.exists():
                logger.warning(
                    "[ToolDispatcher] tool.json not found for %s at %s",
                    name,
                    tool_json_path,
                )
                continue
            try:
                data = json.loads(tool_json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "[ToolDispatcher] Failed to read tool.json for %s: %s", name, e
                )
                continue
            # Resolve the tool's primary arg (for SOP-scoped task keying). Read
            # from the raw tool.json so no AgentFoundation schema change is needed.
            primary, ptype = self._resolve_primary_arg(data)
            # ``is not None`` (NOT truthiness): the opt-out sentinel ``False`` MUST
            # be stored so dispatch keys on sop/phase/tool only. ``if primary:``
            # silently dropped it → the key fell back to the volatile ``request``
            # → reuse never matched (research_propose spawned a fresh run every
            # approve). Only genuinely-unresolved ``None`` is skipped.
            if primary is not None:
                self._primary_arg_map[name] = primary
                self._primary_arg_type_map[name] = ptype
            executor_ref = data.get("executor")
            derived_from = data.get("derived_from")
            if executor_ref:
                try:
                    self._executor_map[name] = self._import_callable(executor_ref)
                    logger.debug(
                        "[ToolDispatcher] Loaded executor for %s: %s",
                        name,
                        executor_ref,
                    )
                except (ImportError, AttributeError, ValueError) as e:
                    logger.warning(
                        "[ToolDispatcher] Failed to load executor for %s (%s): %s",
                        name,
                        executor_ref,
                        e,
                    )
            elif isinstance(derived_from, dict) and derived_from.get("tool"):
                # Derived tools (e.g. understand_codebase, research_propose,
                # understand_data) declare NO `executor` — they map their args to a
                # parent tool (task) via `derived_from`. Without this branch they
                # never enter _executor_map, so a SOP phase that invokes one raises
                # KeyError. Wire them to AgentFoundation's canonical generic
                # resolver so they actually run.
                self._executor_map[name] = self._make_derived_executor(
                    name, derived_from
                )
                logger.debug(
                    "[ToolDispatcher] Loaded derived executor for %s (-> %s)",
                    name,
                    derived_from.get("tool"),
                )

    @staticmethod
    def _resolve_primary_arg(data: dict[str, Any]) -> tuple[str | bool | None, str]:
        """Resolve a tool's primary-arg name + type from its raw tool.json.

        Fallback chain (the registration the SOP-scoped task key needs):
          1. explicit top-level ``"primary_arg"`` (preferred)
          2. ``derived_from.target_path_arg`` (derived tools, e.g.
             understand_codebase → ``target``)
          3. the single required positional parameter (e.g. task → ``request``)

        Type is ``"primary_arg_type"`` or the matching parameter's ``"type"``;
        ``"path"`` triggers path normalization, everything else is a string.
        Returns ``(None, "string")`` when no primary arg can be resolved.
        ``"primary_arg": null`` in tool.json is an explicit opt-out — the
        workspace key is SOP+phase+tool only, with no argument component.
        Returns ``(False, "string")`` for the opt-out case so the dispatch
        path can skip the ``request`` fallback.
        """
        if "primary_arg" in data and data["primary_arg"] is None:
            return False, "string"
        derived = data.get("derived_from") or {}
        primary = data.get("primary_arg") or derived.get("target_path_arg")
        if not primary:
            positional = [
                p.get("name")
                for p in data.get("parameters", [])
                if p.get("required") and p.get("positional") and p.get("name")
            ]
            if len(positional) == 1:
                primary = positional[0]
        if not primary:
            return None, "string"
        # Normalize a CLI-style "--foo-bar" name to the underscored arg key.
        primary = str(primary).lstrip("-").replace("-", "_")
        arg_type = data.get("primary_arg_type")
        if not arg_type:
            for p in data.get("parameters", []):
                pname = str(p.get("name", "")).lstrip("-").replace("-", "_")
                if pname == primary:
                    arg_type = p.get("type")
                    break
        return primary, ("path" if arg_type == "path" else "string")

    @staticmethod
    def _import_callable(ref: str) -> Callable:
        """Import 'module.path:callable_name' → callable.

        Args:
            ref: Entry-point style reference, e.g.
                 'openteam.server.resources.tools.create_role.executor:execute'

        Raises:
            ValueError: If ref doesn't contain ':'.
            ImportError: If module cannot be imported.
            AttributeError: If callable not found in module.
        """
        if ":" not in ref:
            raise ValueError(
                f"Invalid executor reference '{ref}' — expected 'module.path:callable'"
            )
        module_path, _, callable_name = ref.rpartition(":")
        module = importlib.import_module(module_path)
        return getattr(module, callable_name)

    @staticmethod
    def _make_derived_executor(name: str, derived_from: dict[str, Any]) -> Callable:
        """Build an executor for a ``derived_from`` tool.

        Delegates to AgentFoundation's canonical generic resolver
        (``derived_tool_execute``), which maps the tool's args to its parent
        (``task``) per ``arg_mappings``/``defaults``/``target_path_arg`` and runs
        the task executor. Conforms to the registry executor shape:
        async (arguments, session_context) -> ToolExecutionResult.
        """
        from agent_foundation.resources.tools.registry import derived_tool_execute

        async def _execute(
            arguments: dict[str, Any], session_context: dict[str, Any]
        ) -> Any:
            return await derived_tool_execute(
                arguments,
                session_context,
                derived_from=derived_from,
                tool_name=name,
            )

        return _execute

    def handles(self, tool_name: str) -> bool:
        """Check if this dispatcher can handle the given tool name."""
        return tool_name in self._executor_map or self._integration_executor.handles(
            tool_name
        )

    async def __call__(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:  # ToolExecutionResult
        """Dispatch tool_name to the appropriate executor.

        Priority:
        1. Async (background) registry tools — spawn task, return immediately
        2. Sync registry-declared executors (create_role, role_setup, future tools)
        3. Integration tools fallback (Slack, TWG)
        4. Unknown tool fallback
        """
        from agent_foundation.common.inferencers.agentic_inferencers.conversational.protocols import (
            ToolExecutionResult,
        )
        from openteam.server.services.cli_args import coerce_tool_arguments

        # 1. Async tools → background task with subtab
        tool_def = self._tool_registry.get(tool_name)

        # The LLM may emit an action's `arguments` as a CLI-style string (it
        # mirrors the tool's own usage examples, e.g. "<path> --template-version
        # modeling") instead of the documented dict. Downstream executors index
        # args by key (`_dispatch_as_task` does `arguments.get(...)`,
        # `derived_tool_execute` does `arguments.items()`), so a bare string
        # raised `'str' object has no attribute 'get'` and silently killed the
        # task in the background. Coerce any shape to the canonical dict here —
        # the single boundary every agent action tool passes through.
        arguments = coerce_tool_arguments(arguments, tool_def)

        # #15 hub-routing guard: a `task --use-proposal` whose proposal-ids are
        # owned by the active Experiment Hub is the hub's responsibility (the hub
        # is the single implementation owner) — route it INTO the hub's queue
        # rather than spawning a parallel task-subtab. Narrow + fail-safe: only
        # `task` + proposal-ids + an active hub that owns them; any error or
        # non-match falls through to normal dispatch below.
        if tool_name == "task" and self._interactive is not None:
            routed = await self._maybe_route_task_to_hub(arguments)
            if routed is not None:
                return routed

        if tool_def and tool_def.asynchronous and self._interactive:
            return await self._dispatch_as_task(tool_name, arguments, tool_def)

        # 1b. Dashboard tools (tool_type:"Dashboard") open a subtab directly via
        # the capability methods — no _executor_map entry, not agent-invoked. This
        # is the /<dashboard> slash path (e.g. `/experiment-hub <proposals_path>`);
        # the proposal-selection handoff calls the typed methods (create_experiment_hub)
        # instead, via the ConversationalInferencer's post-fork opener.
        if tool_def is not None and getattr(tool_def, "tool_type", "") == "Dashboard":
            seed = self._seed_from_dashboard_args(tool_name, arguments)
            hub_id = await self._open_dashboard_impl(tool_name, seed)
            return ToolExecutionResult(
                result=f"[Opened {tool_name} dashboard subtab (hub_id={hub_id}).]",
                context_updates={"hub_id": hub_id, "dashboard_id": tool_name},
            )

        # 2. Registry-declared executors (sync)
        if tool_name in self._executor_map:
            logger.info(
                "[ToolDispatcher] Dispatching '%s' to registry executor", tool_name
            )
            return await self._executor_map[tool_name](arguments, self._session_context)

        # 2. Integration tools fallback (Slack, TWG)
        if self._integration_executor.handles(tool_name):
            logger.info(
                "[ToolDispatcher] Dispatching '%s' to integration executor", tool_name
            )
            return await self._integration_executor(tool_name, arguments)

        # 4. Unknown
        logger.warning("[ToolDispatcher] Unknown tool: %s", tool_name)
        return ToolExecutionResult(result=f"Unknown tool: {tool_name}")

    def _resolve_reused_document(
        self, workspace: Path, meta: dict[str, Any]
    ) -> str | None:
        """Resolve a reused COMPLETE workspace's primary artifact path (R2b).

        Robust to a relocated session dir (resume could move a session under a
        new server, staling the sidecar's ABSOLUTE ``document_path``): rebase the
        recorded doc onto the CURRENT workspace, then fall back to the recorded
        absolute path, then to the canonical research/plan output filenames.
        Returns None when nothing is found on disk.
        """
        doc = meta.get("document_path")
        ws_at_completion = meta.get("workspace")
        if doc:
            if ws_at_completion:
                try:
                    cand = workspace / Path(doc).relative_to(ws_at_completion)
                    if cand.is_file():
                        return str(cand)
                except (ValueError, TypeError):
                    pass
            if Path(doc).is_file():
                return str(doc)
        for rel in ("outputs/plan.md", "outputs/proposals.json"):
            cand = workspace / rel
            if cand.is_file():
                return str(cand)
        return None

    def _reused_completion_result(self, workspace: str) -> Any:
        """Build a completed-task result for a REUSED complete workspace from its
        persisted sidecar + on-disk outputs — WITHOUT invoking AgentFoundation
        (R2b). The returned ``context_updates`` feed the SAME completion pipeline
        as a fresh run (``plan_path`` → ``_doc`` → ``viewable_artifact_path`` and
        the ``task_completed`` event), so the SOP advances to proposal_selection
        reading ``outputs/proposals.json`` exactly as after a fresh completion.
        Zero LLM calls; sidesteps AF's Dual-resume limitation.
        """
        from agent_foundation.common.inferencers.agentic_inferencers.conversational.protocols import (
            ToolExecutionResult,
        )

        ws = Path(workspace)
        meta = (
            self._session_store.read_task_meta(ws)
            if self._session_store is not None
            else None
        ) or {}
        doc = self._resolve_reused_document(ws, meta)
        summary = str(meta.get("result_summary") or "").strip()
        if not summary:
            _tool = meta.get("tool_name") or ws.name
            summary = f"Reused completed {_tool} result from a prior run (no re-run)."
        ctx: dict[str, Any] = {"workspace_path": workspace}
        if doc:
            ctx["plan_path"] = doc
        return ToolExecutionResult(result=summary, context_updates=ctx)

    async def _dispatch_as_task(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_def: Any,
    ) -> Any:
        """Spawn a background asyncio task for long-running tools.

        Immediately sends task_status "starting", spawns the executor via
        asyncio.create_task(), and returns a brief ToolExecutionResult so the
        agentic loop continues. The task panel in the UI streams progress.
        When the task completes, a task_completed WS event triggers the
        client-side auto-advance mechanism for the next SOP phase.
        """
        import asyncio
        import uuid

        from agent_foundation.common.inferencers.agentic_inferencers.conversational.protocols import (
            ToolExecutionResult,
        )

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        request_label = (
            arguments.get("role_description")
            or arguments.get("role_document_path")
            or arguments.get("request")
            or tool_name
        )
        if isinstance(request_label, str):
            request_label = request_label[:80]

        # Notify UI: task starting — creates task_ref card in conversation
        await self._interactive.send_task_status(
            task_id,
            "starting",
            request=request_label,
            tool_name=tool_name,
        )

        # Per-task child interactive with its own registered receive queue, so
        # the background task can block on aget_input() and receive
        # pending_input_response routed by task_id (same mechanism as the
        # dev-slash path). Fall back to the parent (-> non-interactive yolo)
        # when the transport cannot register a queue. interactive_safe MUST
        # track real registration: we never claim safety without a queue behind
        # it, or the router would hang on a torn-down queue.
        interactive_ref = self._interactive  # capture for closure
        cleanup_interactive: Callable[[], None] = lambda: None
        interactive_safe = False
        if hasattr(self._interactive, "for_background_task"):
            try:
                interactive_ref, cleanup_interactive = (
                    self._interactive.for_background_task(task_id)
                )
                interactive_safe = True
            except Exception as exc:  # RuntimeError (no registry) or unexpected
                logger.warning(
                    "[ToolDispatcher] for_background_task failed for %s: %s; "
                    "falling back to non-interactive (yolo)",
                    task_id,
                    exc,
                )
                interactive_ref = self._interactive

        # ── SOP-scoped task key (captured SYNCHRONOUSLY here, before _run) ──
        # The dispatcher is shared and mutated per-turn, and the background _run
        # can outlive this turn, so everything that depends on live state is read
        # NOW and closed over as locals / written to the on-disk sidecar.
        sid = self._session_context.get("session_id", "")
        sop = getattr(self._inferencer, "sop_state", None)
        sop_name = getattr(sop, "sop_name", "") if sop else ""
        tool_phase_map = getattr(sop, "tool_phase_map", {}) if sop else {}
        phase_index = tool_phase_map.get(tool_name) if sop else None
        primary_arg = self._primary_arg_map.get(tool_name)
        primary_arg_type = self._primary_arg_type_map.get(tool_name, "string")
        # Shared with backfill (SessionStore._targets_from_response) so dispatch
        # and backfill compute the identical key — see primary_val_from_args.
        primary_val = primary_val_from_args(arguments, primary_arg, primary_arg_type)
        # GATE: keyed only inside an active SOP AND when the tool is registered to
        # a phase (phase_index is not None) — i.e. "inside an SOP, registered for
        # the current phase". Ad-hoc / unregistered calls get no key → always fresh.
        registered = sop is not None and phase_index is not None
        task_key = (
            f"{sop_name}/{phase_index}/{tool_name}/{primary_val}"
            if registered
            else None
        )
        turn_number = int(getattr(self, "_current_turn", 0) or 0)
        # Round that dispatched this task (stamped on the dispatcher per round by
        # ConversationService._on_round_start). Enables round-granular keep/drop on
        # resume-from-round; 0 when not in a round-tracked loop.
        round_number = int(getattr(self, "_current_round", 0) or 0)
        force_fresh = bool(arguments.get("no_resume") or arguments.get("fresh"))

        # ── Reuse decision (keyed, non-forced calls only) ──────────────────
        reused_dir = None
        if task_key is not None and not force_fresh and self._session_store is not None:
            # Adopt any pre-feature workspaces (no task_meta.json) into the precise
            # scheme BEFORE matching — runs once per dispatcher (idempotent), so a
            # server resumed with old task runs can still be matched precisely.
            if not getattr(self, "_backfill_done", False) and hasattr(
                self._session_store, "backfill_task_sidecars"
            ):
                try:
                    self._session_store.backfill_task_sidecars(
                        sid, self._primary_arg_map, self._primary_arg_type_map
                    )
                except Exception as exc:
                    logger.warning(
                        "[ToolDispatcher] backfill_task_sidecars failed: %s", exc
                    )
                self._backfill_done = True
            try:
                reused_dir = self._session_store.find_reusable_workspace(
                    sid, tool_name, sop_name, str(phase_index), primary_val
                )
            except Exception as exc:
                logger.warning(
                    "[ToolDispatcher] find_reusable_workspace failed: %s", exc
                )
                reused_dir = None

        # ── R2b: classify the match. A COMPLETE workspace is emitted straight
        # from its persisted sidecar/outputs (no AF); only a PARTIAL/crashed one
        # is resumed via AF. Injecting AF ``resume=`` into a COMPLETE Dual-rooted
        # workspace (research_propose) does NOT short-circuit — DualInferencer
        # overrides the LinearWorkflow ``final_result.json`` fast-path and
        # re-enters its consensus loop, re-running the workers → re-triggering the
        # guardrail cascade. The result is already on disk, so reuse it as-is.
        reused_complete = (
            reused_dir is not None
            and self._session_store is not None
            and self._session_store.is_workspace_complete(reused_dir)
        )

        # ── Workspace: reuse-in-place (inject AF resume) OR allocate fresh ──
        # Path B (server-affiliated): session_root → <session>/tasks/<tool>_<TS>_<uuid8>/
        # Path A (standalone): no session_root → _runtime/tasks/<tool>/<tool>_<TS>_<uuid8>/
        from agent_foundation.common.workspace.allocator import allocate_tool_workspace

        session_root_str = self._session_context.get("session_root", "")
        if reused_dir is not None:
            task_working_dir = str(reused_dir)
            if reused_complete:
                # R2b: complete → do NOT inject resume=; _run() emits the
                # persisted result from disk without invoking AF (zero LLM
                # calls, no worker re-run, no cascade).
                logger.info(
                    "[ToolDispatcher] Reusing COMPLETE workspace for %s (key=%s) "
                    "— emitting persisted result, no AF run: %s",
                    tool_name,
                    task_key,
                    task_working_dir,
                )
            else:
                # Partial/crashed → inject AF resume; leave copy_workspace unset
                # (default False) so AF resumes IN PLACE, continuing from its
                # phase markers. (_apply_resume ignores in_place.)
                arguments = {**arguments, "resume": task_working_dir}
                logger.info(
                    "[ToolDispatcher] Resuming PARTIAL workspace for %s (key=%s): %s",
                    tool_name,
                    task_key,
                    task_working_dir,
                )
        else:
            if session_root_str:
                from pathlib import Path as _Path

                tasks_parent = _Path(session_root_str) / "tasks"
                tasks_parent.mkdir(parents=True, exist_ok=True)
                task_workspace = allocate_tool_workspace(
                    tool_name, base_dir=tasks_parent
                )
            else:
                task_workspace = allocate_tool_workspace(tool_name, base_dir=None)
            task_working_dir = str(task_workspace)

        # ── Persist the task sidecar (survives truncation) + task_ref chip ──
        if self._session_store is not None:
            _now = _iso_now()
            _meta = {
                "task_id": task_id,
                "tool_name": tool_name,
                "label": request_label,
                "status": "starting",
                "workspace": task_working_dir,
                "primary_arg": primary_arg,
                "primary_arg_value": primary_val,
                "sop_name": sop_name,
                "phase_index": phase_index,
                "registered": registered,
                "task_key": task_key,
                "turn_number": turn_number,
                "round_number": round_number,
                "created_at": _now,
            }
            # On reuse, preserve the orphan's original created_at so oldest-first
            # ordering of any remaining orphans stays stable; turn_number refreshes
            # to this dispatch (keeps drop_tasks semantics consistent).
            if reused_dir is not None:
                _existing = self._session_store.read_task_meta(task_working_dir) or {}
                if _existing.get("created_at"):
                    _meta["created_at"] = _existing["created_at"]
                # R2b: this write OVERWRITES the sidecar. For a COMPLETE reuse
                # _run() emits the persisted result from this same sidecar, so
                # carry the completed artifact fields through the overwrite (else
                # document_path/result_summary would be lost before _run() reads
                # them, degrading the emitted result to a generic stub).
                if reused_complete:
                    for _k in ("document_path", "result_summary"):
                        if _existing.get(_k) is not None:
                            _meta[_k] = _existing[_k]
            try:
                self._session_store.write_task_meta(task_working_dir, _meta)
            except Exception as exc:
                logger.warning("[ToolDispatcher] write_task_meta failed: %s", exc)
            if sid:
                try:
                    self._session_store.append_message(
                        sid,
                        {
                            "id": f"task-ref-{task_id}",
                            "role": "task_ref",
                            "taskId": task_id,
                            "toolName": tool_name,
                            "label": request_label,
                            "status": "starting",
                            "workspace": task_working_dir,
                            "documentPath": None,
                            "resultSummary": None,
                            "sopName": sop_name,
                            "phaseIndex": phase_index,
                            "taskKey": task_key,
                            "turn_number": turn_number,
                            "round_number": round_number,
                            "timestamp": _now,
                        },
                    )
                except Exception as exc:
                    logger.warning("[ToolDispatcher] task_ref persist failed: %s", exc)

        async def _run() -> None:
            try:
                await interactive_ref.send_task_status(
                    task_id,
                    "running",
                    tool_name=tool_name,
                )
                # Persist the "running" transition so the on-disk state is
                # symmetric with dispatch ("starting") and completion
                # ("completed"/"error"). Without this, a reload during a
                # live task shows the stale "starting" chip forever.
                # Guarded like the sibling persists below; a sidecar-write
                # failure must never abort the task.
                if self._session_store is not None:
                    try:
                        self._session_store.update_task_meta(
                            task_working_dir,
                            {"status": "running", "started_at": _iso_now()},
                        )
                    except Exception:
                        pass
                    if sid:
                        try:
                            self._session_store.update_message(
                                sid,
                                f"task-ref-{task_id}",
                                {"status": "running"},
                            )
                        except Exception:
                            pass
                task_context = {
                    **self._session_context,
                    "task_id": task_id,
                    "session_root": session_root_str,
                    "working_dir": task_working_dir,
                    "interactive": interactive_ref,
                    # Coupled to successful registration above — never True
                    # without a real registered queue behind interactive_ref.
                    "router_interactive_safe": interactive_safe,
                }
                if reused_complete:
                    # R2b: complete workspace — synthesize the result from the
                    # persisted sidecar + on-disk outputs instead of invoking AF.
                    # Everything downstream (result_summary, _doc,
                    # task_completed, viewable_artifact_path) runs UNCHANGED, so
                    # the SOP advances to proposal_selection reading
                    # outputs/proposals.json exactly as after a fresh completion.
                    result = self._reused_completion_result(task_working_dir)
                else:
                    result = await self._executor_map[tool_name](
                        arguments, task_context
                    )

                result_summary = (
                    str(result.result)[:500] if result and result.result else ""
                )
                # A1 (v3 merged): generalized tool-first namespaced publish
                # for the tool-output convention `<producing_tool>__<output>`.
                # See /home/zgchen/.claude/plans/elegant-mapping-hopper.md.
                #
                # Runs BEFORE the phase_outputs persist block below so A4 sees
                # the namespaced keys in `result.context_updates`. AF's
                # `update_prior_context(**result.context_updates)` at
                # conversational_inferencer.py:2053-2055 then picks them up
                # for free — single site of truth for action-tool outputs.
                #
                # Setdefault semantics: preserve any explicit value already
                # written by the AF registry bridge or an executor. Skip
                # already-namespaced keys (contain "__") and internal control
                # keys.
                if tool_name and result is not None:
                    if result.context_updates is None:
                        result.context_updates = {}
                    safe = tool_name.replace("-", "_")
                    workspace = (
                        result.context_updates.get("workspace_path") or task_working_dir
                    )
                    if workspace:
                        # Legacy alias (Fix 1) — kept for existing SOPs that
                        # reference `{{ workspace_path__<tool> }}`. Harmlessly
                        # dual-publishes with the generalized loop below.
                        result.context_updates.setdefault(
                            f"workspace_path__{safe}", workspace
                        )
                        # For research-propose: derive proposals_path from the
                        # invariant `<workspace>/outputs/proposals.json` (BTA
                        # docstring breakdown_then_aggregate_inferencer.py:1353-1363).
                        # Added as a BARE key so the generalized loop below
                        # namespaces it to `research_propose__proposals_path`.
                        if safe == "research_propose":
                            sidecar = Path(workspace) / "outputs" / "proposals.json"
                            if sidecar.is_file():
                                result.context_updates.setdefault(
                                    "proposals_path", str(sidecar)
                                )
                    for k in list(result.context_updates.keys()):
                        if "__" in k or k in (
                            "current_phase",
                            "phase_status",
                            "routed_to_hub",
                        ):
                            continue
                        result.context_updates.setdefault(
                            f"{safe}__{k}", result.context_updates[k]
                        )
                # Patch 3.6 — generalized document_path fallback chain so /task's
                # workspace_path / plan_path / impl_path artifacts surface in the UI
                # via the same hook /create_role uses. role_document_path stays first
                # so /create_role's existing UI behavior is unchanged.
                _ctx = (
                    result.context_updates
                    if (result and result.context_updates)
                    else {}
                )
                _doc = (
                    _ctx.get("role_document_path")
                    or _ctx.get("plan_path")
                    or _ctx.get("impl_path")
                    or _ctx.get("doc_index_path")
                    or _ctx.get("doc_path")
                    or _ctx.get("workspace_path")
                )
                # Fix 3 (v5): compute SOP-derived `next_step_tool` for the FE
                # auto-advance directive. Conversation-tool-only guard — if the
                # next required tool is an action tool (e.g. after a spuriously
                # premature phase completion), return None and let the FE's
                # generic "refer to <SOPNextStepGuidance>" branch fire. See
                # /home/zgchen/.claude/plans/elegant-mapping-hopper.md Fix 3.
                _next_step_tool = None
                try:
                    _inf = getattr(self, "_inferencer", None)
                    if _inf is not None and hasattr(_inf, "next_required_tools"):
                        _required = _inf.next_required_tools()
                        _conv_tools: set[str] = set()
                        for _tname in _required:
                            _tdef = self._tool_registry.get(_tname)
                            # Registry entries are ToolDefinition OBJECTS; use
                            # `getattr(..., "tool_type", "")` (precedent :305).
                            if (
                                _tdef is not None
                                and getattr(_tdef, "tool_type", "") == "Conversation"
                            ):
                                _conv_tools.add(_tname)
                        # No action-tool fallback — return None on empty set so
                        # the FE defers to <SOPNextStepGuidance> generically.
                        _next_step_tool = next(iter(_conv_tools), None)
                except Exception:  # noqa: BLE001 — best-effort; Fix 1 works without this
                    pass

                await interactive_ref._send(
                    {
                        "type": "task_completed",
                        "task_id": task_id,
                        "tool_name": tool_name,
                        "result_summary": result_summary,
                        "workspace": task_working_dir,
                        "document_path": _doc,
                        "context_updates": dict(_ctx),
                        "next_step_tool": _next_step_tool,
                    }
                )
                await interactive_ref.send_task_status(
                    task_id,
                    "completed",
                    tool_name=tool_name,
                )
                # Persist completion onto the sidecar + task_ref (restart-safe).
                if self._session_store is not None:
                    try:
                        self._session_store.update_task_meta(
                            task_working_dir,
                            {
                                "status": "completed",
                                "document_path": _doc,
                                "result_summary": result_summary,
                                "completed_at": _iso_now(),
                                # Clear any prior error metadata for symmetry
                                # with the task_ref clear below and reconcile's
                                # completed-heal branch.
                                "error_type": None,
                                "error": None,
                            },
                        )
                    except Exception:
                        pass
                    if sid:
                        try:
                            self._session_store.update_message(
                                sid,
                                f"task-ref-{task_id}",
                                {
                                    "status": "completed",
                                    "documentPath": _doc,
                                    "resultSummary": result_summary,
                                    # Clear any prior error metadata (e.g. from
                                    # an earlier reconcile-interrupted heal that
                                    # the task later recovered from). Mirrors
                                    # reconcile_task_ref_statuses' behavior on
                                    # the completed branch and keeps disk/UI
                                    # state in sync with the frontend live
                                    # handler's clean-terminal reset in
                                    # useManagerChat.js.
                                    "errorType": None,
                                    "error": None,
                                },
                            )
                        except Exception:
                            pass
                        # A4 (v3): persist both the viewable-artifact path AND
                        # every namespaced `<tool>__<key>` from A1 upstream to
                        # `phase_outputs`. Split gate so namespaced keys land
                        # even for tools that don't produce a file artifact.
                        _doc_is_file = bool(_doc and Path(_doc).is_file())
                        _namespaced = {
                            _k: _v
                            for _k, _v in (result.context_updates or {}).items()
                            if isinstance(_k, str) and "__" in _k
                        }
                        if _doc_is_file or _namespaced:
                            try:
                                sess = self._session_store.get_session(sid)
                                if sess:
                                    wc = dict(sess.get("workflow_context", {}))
                                    po = dict(wc.get("phase_outputs", {}))
                                    if _doc_is_file:
                                        po["viewable_artifact_path"] = _doc
                                    if _namespaced:
                                        po.update(_namespaced)
                                    wc["phase_outputs"] = po
                                    self._session_store.update_workflow_context(sid, wc)
                            except Exception:
                                pass
            except Exception as e:
                logger.error(
                    "[ToolDispatcher] Background task %s (%s) error: %s",
                    task_id,
                    tool_name,
                    e,
                    exc_info=True,
                )
                # Persist error status (CancelledError is BaseException-derived,
                # so a resume-triggered cancel does NOT land here — its workspace
                # is being truncated/kept by the resume flow anyway).
                # Persist the error TYPE + MESSAGE alongside the status so a
                # reload can surface them in the UI (bounded to 500 chars — the
                # full traceback stays in server.log via logger.error above).
                _error_type = type(e).__name__
                _error_msg = str(e)[:500]
                if self._session_store is not None:
                    try:
                        self._session_store.update_task_meta(
                            task_working_dir,
                            {
                                "status": "error",
                                "error_type": _error_type,  # snake_case in task_meta.json
                                "error": _error_msg,
                                "completed_at": _iso_now(),
                            },
                        )
                    except Exception:
                        pass
                    if sid:
                        try:
                            self._session_store.update_message(
                                sid,
                                f"task-ref-{task_id}",
                                {
                                    "status": "error",
                                    "errorType": _error_type,  # camelCase in session_state.messages
                                    "error": _error_msg,
                                },
                            )
                        except Exception:
                            pass
                try:
                    await interactive_ref.send_task_status(
                        task_id,
                        "error",
                        tool_name=tool_name,
                        error=_error_msg,
                        error_type=_error_type,
                    )
                except Exception:
                    pass
            finally:
                # Deregister the per-task input queue (mirror of the dev-slash
                # cleanup). finally also covers asyncio.CancelledError.
                cleanup_interactive()

        _bg = asyncio.create_task(_run())
        # Register in the per-session background-task registry so a resume/restore
        # can cancel + await in-flight tasks BEFORE mutating the session on disk
        # (otherwise checkpoint-copy / turn_NNN rmtree / workspace rmtree could
        # race a live writer).
        if self._register_bg_task is not None:
            try:
                self._register_bg_task(_bg, task_id)
            except Exception as exc:
                logger.warning("[ToolDispatcher] bg-task register failed: %s", exc)

        return ToolExecutionResult(
            result=(
                f"[Task {task_id} started — running '{tool_name}' in background. "
                "See task panel for progress.]"
            ),
            context_updates={"task_id": task_id, "is_background_task": True},
        )

    # ── Dashboard handoff (HubAwareToolExecutor / DashboardAwareToolExecutor) ──
    # These make the dispatcher satisfy the AF capability Protocols so the
    # ConversationalInferencer's post-fork opener (resolved via
    # ``conv_inferencer._tool_dispatcher``) can open a Dashboard subtab. Transport
    # + persistence live HERE (OpenTeam concern); the ML-specific hub init is
    # delegated to ``agent_foundation.experiment_hub`` when present (#13). The
    # task-subtab persist+emit pattern (``_dispatch_as_task``) is the template.

    async def open_dashboard(
        self, dashboard_id: str, seed: dict[str, Any] | None = None
    ) -> str:
        """Generic ``DashboardAwareToolExecutor`` entry point."""
        return await self._open_dashboard_impl(dashboard_id, seed)

    async def create_experiment_hub(
        self,
        selected_details: list[dict[str, Any]],
        proposals_data: dict[str, Any],
        custom_queries: list[str] | None = None,
        group_by: str = "batch",
        auto_implement: bool = True,
    ) -> str:
        """``HubAwareToolExecutor`` — open the Experiment Hub seeded with a
        detailed selection (the ``proposal-selection --experiment-hub`` handoff).
        Delegates ML hub creation to ``HubController`` (the id authority), then
        opens + persists the dashboard subtab keyed by the returned
        ``multi_task_id``. The hub is the single implementation owner (#15);
        ``auto_implement`` defaults to NOT auto-running on the handoff path.

        Boundary canonicalization: the hub subsystem (AF ``HubController``,
        ``open_experiment_hub`` validation, FE ``MultiChoiceComboView``,
        widget's rich path) speaks the hub dialect (``phases`` /
        ``hypothesis_ids`` / ``combo_constraints``). The in-chat handoff
        forwards AF-native ``ProposalIndex.to_dict()`` (``groups`` /
        ``proposal_ids`` / ``constraints``). We canonicalise once here so every
        downstream consumer sees hub-canonical data. See
        `common/data_models/proposal/parser.py::canonicalize_proposal_index_to_hub_dict`
        for the details (idempotent on already-hub payloads).
        """
        from agent_foundation.common.data_models.proposal.parser import (
            canonicalize_proposal_index_to_hub_dict,
        )

        hub_proposals = canonicalize_proposal_index_to_hub_dict(proposals_data or {})
        selected_ids = [
            d.get("id")
            for d in (selected_details or [])
            if isinstance(d, dict) and d.get("id")
        ]
        # G13 — when auto_implement is on (Path A), derive `seed["runQueue"]`
        # from the same batch_queue HubController.create_experiment_hub will
        # emit. Critical: the multi:starting WS event fires BEFORE the
        # dashboard_open WS event, and the FE per-hub event bus
        # (`makeWsEvents()`) has no replay buffer — so events fired before
        # DashboardPanel's post-mount subscribe are LOST. The seed IS the
        # only path that reliably reaches the reducer.
        #
        # FIELD MAPPING (verified against reducer.js:mapResumeQueueEntry:64+):
        # the reducer reads `e.hypothesis_id` (SINGULAR, comma-joined string),
        # not `e.hypothesis_ids` (PLURAL list) that batch_queue emits. Direct
        # passthrough → empty labels + no hypothesis chips. So convert here.
        run_queue_seed: list[dict[str, Any]] = []
        active_view_seed = 0  # Selection (default)
        unlocked_views_seed = [0]
        if auto_implement:
            # Import inside the function to avoid pulling the AF hub_controller
            # onto module-load hot path (dispatcher module loads on every server
            # startup; the grouper is only needed on this specific handoff).
            from agent_foundation.experiment_hub.proposal_grouping import (
                group_selected_by_batch,
            )

            if group_by == "all":
                groups = [
                    {
                        "batch_id": "all",
                        "batch_label": "All Selected",
                        "hypotheses": list(selected_details or []),
                    }
                ]
            elif group_by == "hypothesis":
                groups = [
                    {
                        "batch_id": h.get("id", ""),
                        "batch_label": (h.get("title") or "")[:40],
                        "hypotheses": [h],
                    }
                    for h in (selected_details or [])
                ]
            else:
                groups = group_selected_by_batch(
                    list(selected_details or []), hub_proposals
                )
            for bg in groups:
                hyp_ids_list = [h.get("id", "") for h in bg["hypotheses"]]
                run_queue_seed.append(
                    {
                        # `title` is what mapResumeQueueEntry displays in the list.
                        "title": f"B{bg['batch_id']}: {bg['batch_label']}"
                        if group_by == "batch"
                        else ",".join(hyp_ids_list),
                        "batch_id": bg["batch_id"],
                        "batch_label": bg["batch_label"],
                        # SINGULAR comma-joined — mapResumeQueueEntry reads
                        # `e.hypothesis_id` (singular), splits on ',', filters.
                        "hypothesis_id": ",".join(hyp_ids_list),
                        "status": "queued",
                        # task_id fills in via task_status events once the /task
                        # runs start — this is the reducer's `subTaskId`.
                    }
                )
            # G24 — land the user on the Implementation tab (index 1) so they
            # see the batches immediately rather than an empty Selection tab
            # flash. DashboardPanel.js:59-65 honors seed.activeView and
            # force-adds it to unlockedViewIds.
            active_view_seed = 1
            unlocked_views_seed = [0, 1]
        seed = {
            "selected_details": list(selected_details or []),
            "selected_proposal_ids": selected_ids,
            "proposals_data": hub_proposals,
            "custom_queries": custom_queries,
            "group_by": group_by,
            "auto_implement": auto_implement,
            "initial_view": "selection",
            # G13 — pre-populate runQueue so Impl tab fills IMMEDIATELY on
            # dashboard_open. Empty when auto_implement is False (Path B).
            "runQueue": run_queue_seed,
            # G24 — force activeView=1 (Implementation) when auto_implement,
            # else default to Selection (activeView=0).
            "activeView": active_view_seed,
            "unlockedViewIds": unlocked_views_seed,
            # Phase 5c: frontend seed — MUST match what
            # WidgetHostView.buildWidgetConfig / MultiChoiceComboView expect.
            "scenarioState": {
                "selectionSnapshot": {
                    # Nested inside `proposals`: matches
                    # ProposalSelectionWidget's `metadata.proposals` read AND
                    # MultiChoiceComboView's `snap.proposals.combo_constraints`
                    # read (verified — no top-level combo_constraints needed).
                    "proposals": hub_proposals,
                    "selectedProposals": list(selected_ids),
                    "customQueries": list(custom_queries or []),
                }
            },
        }
        hub_id_holder: dict[str, str] = {"hub_id": ""}
        built = self._build_hub_controller(
            self._make_hub_emit(hub_id_holder), hub_id_holder
        )
        if built is not None:
            controller, wc = built
            try:
                mid = await controller.create_experiment_hub(
                    selected_details=selected_details or [],
                    proposals_data=hub_proposals,
                    custom_queries=custom_queries,
                    group_by=group_by,
                    auto_implement=auto_implement,
                )
                self._persist_wc(wc)
                return await self._open_dashboard_impl(
                    "experiment_hub", seed, hub_id=str(mid), skip_init=True
                )
            except Exception as exc:
                logger.warning(
                    "[dashboard] HubController.create_experiment_hub failed (%s); "
                    "falling back to seed-sidecar open",
                    exc,
                )
        return await self._open_dashboard_impl("experiment_hub", seed)

    async def open_experiment_hub(
        self,
        proposals_data: dict[str, Any],
        selected_proposal_ids: list[str] | None = None,
        pre_select_top_n: int = 5,
        initial_view: str = "selection",
    ) -> str:
        """``HubAwareToolExecutor`` — open the Hub as a shell seeded with proposals
        ("skip detailed selection, go straight to the hub"); idempotent for the
        singleton experiment_hub. ML open is delegated to ``HubController``.

        Applies the same AF→hub boundary canonicalization as
        ``create_experiment_hub`` (see that method's docstring for rationale).
        """
        from agent_foundation.common.data_models.proposal.parser import (
            canonicalize_proposal_index_to_hub_dict,
        )

        hub_proposals = canonicalize_proposal_index_to_hub_dict(proposals_data or {})
        ids = list(selected_proposal_ids or [])
        seed = {
            "selected_proposal_ids": ids,
            "selected_details": [{"id": pid} for pid in ids],
            "proposals_data": hub_proposals,
            "pre_select_top_n": pre_select_top_n,
            "initial_view": initial_view,
            "group_by": "batch",
            "scenarioState": {
                "selectionSnapshot": {
                    "proposals": hub_proposals,
                    "selectedProposals": list(ids),
                    "customQueries": [],
                }
            },
        }
        hub_id_holder: dict[str, str] = {"hub_id": ""}
        built = self._build_hub_controller(
            self._make_hub_emit(hub_id_holder), hub_id_holder
        )
        if built is not None:
            controller, wc = built
            try:
                mid = await controller.open_experiment_hub(
                    proposals_data=hub_proposals,
                    pre_select_top_n=pre_select_top_n,
                    initial_view=initial_view,
                )
                self._persist_wc(wc)
                if mid:
                    return await self._open_dashboard_impl(
                        "experiment_hub", seed, hub_id=str(mid), skip_init=True
                    )
            except Exception as exc:
                logger.warning(
                    "[dashboard] HubController.open_experiment_hub failed (%s); "
                    "falling back to seed-sidecar open",
                    exc,
                )
        return await self._open_dashboard_impl("experiment_hub", seed)

    async def _open_dashboard_impl(
        self,
        dashboard_id: str,
        seed: dict[str, Any] | None = None,
        *,
        hub_id: str = "",
        skip_init: bool = False,
    ) -> str:
        """Open (or idempotently focus) a Dashboard subtab for this session.

        1. Resolve the Dashboard tool's manifest (canonical tab structure).
        2. Mint/reuse a ``hub_id`` (singleton dashboards reuse the session's open one).
        3. Initialize hub state on disk (AF ``hub_controller`` if available, else a
           minimal seed sidecar so the FE Selection tab renders on restore).
        4. Persist a ``dashboard_ref`` (restore marker) + ``dashboard_state`` pointer.
        5. Emit ``dashboard_open`` over the in-turn interactive (best-effort — the
           ``dashboard_ref`` guarantees restore even with no socket attached).
        """
        import uuid

        from agent_foundation.server.dashboard.dashboard_protocol import (
            DashboardManifest,
        )

        seed = dict(seed or {})
        sid = self._session_context.get("session_id", "")
        tool_def = self._tool_registry.get(dashboard_id)
        dashboard_config = getattr(tool_def, "dashboard_config", None) or {}
        manifest = DashboardManifest.from_dashboard_config(
            dashboard_id, dashboard_config
        )
        singleton = bool(dashboard_config.get("singleton"))

        if not hub_id and singleton and sid and self._session_store is not None:
            try:
                hub_id = self._find_open_dashboard(sid, dashboard_id)
            except Exception as exc:
                logger.warning("[dashboard] open-hub lookup failed: %s", exc)
        if not hub_id:
            hub_id = f"{dashboard_id}-{uuid.uuid4().hex[:8]}"

        # skip_init: the HubController path already wrote the hub's ML state to
        # disk; only the generic seed-sidecar path needs _init_dashboard_state.
        if not skip_init:
            self._init_dashboard_state(dashboard_id, hub_id, seed)

        now = _iso_now()
        if sid and self._session_store is not None:
            label = dashboard_config.get("label") or dashboard_id
            icon = dashboard_config.get("icon") or ""
            try:
                self._session_store.append_message(
                    sid,
                    {
                        "id": f"dashboard-ref-{hub_id}",
                        "role": "dashboard_ref",
                        "hubId": hub_id,
                        "dashboardId": dashboard_id,
                        "label": label,
                        "icon": icon,
                        "status": "open",
                        "timestamp": now,
                        "turn_number": int(getattr(self, "_current_turn", 0) or 0),
                    },
                )
            except Exception as exc:
                logger.warning("[dashboard] dashboard_ref persist failed: %s", exc)
            if hasattr(self._session_store, "save_dashboard_state"):
                try:
                    self._session_store.save_dashboard_state(
                        sid, {"active_hub_id": hub_id, "dashboard_id": dashboard_id}
                    )
                except Exception as exc:
                    logger.warning(
                        "[dashboard] dashboard_state persist failed: %s", exc
                    )

        if self._interactive is not None and hasattr(
            self._interactive, "send_dashboard_open"
        ):
            try:
                await self._interactive.send_dashboard_open(
                    hub_id, manifest.to_dict(), seed
                )
            except Exception as exc:
                logger.warning("[dashboard] send_dashboard_open failed: %s", exc)

        logger.info(
            "[dashboard] opened %s (hub_id=%s, singleton=%s) for session %s",
            dashboard_id,
            hub_id,
            singleton,
            sid,
        )
        return hub_id

    def _find_open_dashboard(self, sid: str, dashboard_id: str) -> str:
        """Return the ``hub_id`` of an existing OPEN ``dashboard_ref`` for this
        dashboard in the session (singleton idempotency), or ``""`` if none."""
        session = self._session_store.get_session(sid)
        if not session:
            return ""
        for m in session.get("messages", []):
            if (
                m.get("role") == "dashboard_ref"
                and m.get("dashboardId") == dashboard_id
                and m.get("status") != "closed"
            ):
                return str(m.get("hubId") or "")
        return ""

    def _init_dashboard_state(
        self, dashboard_id: str, hub_id: str, seed: dict[str, Any]
    ) -> None:
        """Prepare the hub directory under ``<session_dir>/hubs/<hub_id>/``.

        **G7 (post-audit): NO ``hub_state.json`` is written.** RankEvolve
        intentionally has no such file — state is derivable from the
        ``WorkflowContext.task_queue`` + on-disk task workspaces via
        ``agent_foundation.experiment_hub.hub_state.reconcile_task_queue_with_disk``
        (called on session restore, not here). The prior "seed sidecar fallback"
        was a divergence from RankEvolve introduced when ``initialize_hub_state``
        wasn't yet ported — now that ``hub_state.py`` is ported and correct,
        the fallback is deleted. Hub-creation state comes from
        ``HubController.create_experiment_hub`` (WS emission +
        ``workflow_context`` persistence via ``_persist_wc``); this method just
        ensures the hub-scoped directory exists so downstream sidecars
        (combos/current.json, hub_<mid>_submissions.json, etc.) have a place
        to write.
        """
        sid = self._session_context.get("session_id", "")
        if not sid or self._session_store is None:
            return
        try:
            hubs_dir = self._session_store.get_session_hubs_dir(sid)
        except Exception as exc:
            logger.warning("[dashboard] hubs dir resolve failed: %s", exc)
            return
        hub_dir = Path(hubs_dir) / hub_id
        hub_dir.mkdir(parents=True, exist_ok=True)
        # NOTE: no hub_state.json write — state is derived, not seeded.

    def _seed_from_dashboard_args(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a dashboard seed from raw slash-command arguments (the
        ``/<dashboard> <proposals_path>`` path). Loads ``proposals_data`` from
        ``proposals_path`` when present so the Selection tab renders immediately."""
        ids = arguments.get("selected_proposal_ids") or ""
        if isinstance(ids, str):
            ids = [s.strip() for s in ids.split(",") if s.strip()]
        elif isinstance(ids, (list, tuple)):
            ids = [str(x).strip() for x in ids if str(x).strip()]
        else:
            ids = []
        seed: dict[str, Any] = {
            "initial_view": arguments.get("initial_view", "selection"),
            "group_by": arguments.get("group_by", "batch"),
            "selected_proposal_ids": ids,
            "selected_details": [{"id": p} for p in ids],
            "proposals_data": {},
        }
        ppath = arguments.get("proposals_path") or ""
        if ppath:
            p = Path(ppath)
            if p.is_dir():
                p = p / "proposals.json"
            if p.is_file():
                try:
                    seed["proposals_data"] = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning(
                        "[dashboard] proposals load failed (%s): %s", ppath, exc
                    )
        return seed

    def _persist_wc(self, wc: Any) -> None:
        """Persist a mutated ``WorkflowContext`` back into the session (the hub
        controller mutates ``active_multi_task_id`` + ``phase_outputs``)."""
        sid = self._session_context.get("session_id", "")
        if not sid or self._session_store is None:
            return
        try:
            self._session_store.update_workflow_context(sid, wc.to_dict())
        except Exception as exc:
            logger.warning("[dashboard] workflow_context persist failed: %s", exc)

    def _make_hub_emit(self, hub_id_holder: dict[str, str]) -> Callable:
        """Build the ``EmitEvent`` adapter the ``HubController`` is injected with.

        It translates RankEvolve-shaped hub payloads into the generic
        ``dashboard_*`` WS protocol the OpenTeam FE consumes, routing every event
        to the hub's bus by ``hub_id`` (captured from the multi-task lifecycle
        event). The hub-level lifecycle becomes ``dashboard_status`` (opening +
        seeding is owned by the dispatcher's ``dashboard_open``); every other
        event is forwarded RAW inside ``dashboard_event`` (the FE reducer switches
        on ``payload.type``)."""
        interactive = self._interactive

        async def _emit(session_id: str, payload: dict[str, Any]) -> None:
            if interactive is None:
                return
            if payload.get("task_type") == "multi" and payload.get("task_id"):
                hub_id_holder["hub_id"] = str(payload["task_id"])
            hub_id = (
                hub_id_holder.get("hub_id")
                or str(payload.get("multi_task_id") or "")
                or str(payload.get("task_id") or "")
            )
            ptype = payload.get("type")
            try:
                if ptype == "task_status" and payload.get("task_type") == "multi":
                    if hasattr(interactive, "send_dashboard_status"):
                        await interactive.send_dashboard_status(
                            hub_id, str(payload.get("status") or "open")
                        )
                elif hasattr(interactive, "send_dashboard_event"):
                    await interactive.send_dashboard_event(
                        hub_id,
                        str(ptype or payload.get("status") or "update"),
                        payload,
                    )
            except Exception as exc:  # noqa: BLE001 — emit is best-effort
                logger.warning("[dashboard] hub emit adapter failed: %s", exc)

        return _emit

    def _build_hub_controller(
        self, emit_event: Callable, hub_id_holder: dict[str, str]
    ) -> Any:
        """Construct a ``HubController`` wired to OpenTeam's session machinery, or
        ``None`` if the experiment_hub backend / session is unavailable. Transport
        + persistence deps are injected here (OpenTeam concern); the ML logic
        lives in ``agent_foundation.experiment_hub`` (#13). Returns
        ``(controller, workflow_context)``."""
        sid = self._session_context.get("session_id", "")
        if not sid or self._session_store is None:
            return None
        try:
            from agent_foundation.experiment_hub.hub_controller import HubController
            from agent_foundation.server.workflow_context import WorkflowContext
        except Exception as exc:
            logger.warning("[dashboard] experiment_hub backend unavailable: %s", exc)
            return None
        session = self._session_store.get_session(sid) or {}
        try:
            wc = WorkflowContext.from_dict(session.get("workflow_context") or {})
        except Exception:
            wc = WorkflowContext()

        async def _persist() -> None:
            self._persist_wc(wc)

        async def _add_task_ref(**kwargs: Any) -> None:
            # Subtask chips only; the hub-level subtab IS the dashboard_ref.
            task_id = kwargs.get("task_id")
            if not task_id:
                return
            try:
                self._session_store.append_message(
                    sid,
                    {
                        "id": f"task-ref-{task_id}",
                        "role": "task_ref",
                        "taskId": task_id,
                        "timestamp": _iso_now(),
                        **kwargs,
                    },
                )
            except Exception as exc:
                logger.warning("[dashboard] hub add_task_ref failed: %s", exc)

        async def _update_task_ref_status(task_id: str, status: str) -> bool:
            try:
                return (
                    self._session_store.update_message(
                        sid, f"task-ref-{task_id}", {"status": status}
                    )
                    is not None
                )
            except Exception:
                return False

        try:
            controller = HubController(
                session_id=sid,
                session_dir=self._session_store.get_session_dir(sid),
                session_tasks_dir=self._session_store.get_session_tasks_dir(sid),
                workflow_context=wc,
                emit_event=emit_event,
                persist=_persist,
                stream_sink=self._interactive,
                # In-hub queued /task runner: runs the task to completion + streams
                # into the hub bus, returning the result the HubController queue
                # runner awaits (#15 routing + any auto_implement path). hub_id
                # resolves at call time from the shared holder (set by the
                # create/guard path + the emit adapter's multi-event capture).
                exec_task=self._make_hub_exec_task(hub_id_holder),
                workflow_target_path=str(
                    self._session_context.get("working_dir", "") or ""
                ),
                session_context=self._session_context,
                add_task_ref=_add_task_ref,
                update_task_ref_status=_update_task_ref_status,
            )
        except Exception as exc:
            logger.warning("[dashboard] HubController construction failed: %s", exc)
            return None
        return controller, wc

    def _make_hub_exec_task(self, hub_id_holder: dict[str, str]) -> Callable:
        """Return the ``exec_task(args, task_id)`` the HubController queue runner
        awaits for queued ``/task`` entries — runs the task to completion with a
        hub-routing interactive so its streaming lands in the hub bus."""

        async def _exec(args: dict[str, Any], task_id: str) -> Any:
            return await self._run_hub_task(
                args, task_id, hub_id_holder.get("hub_id", "")
            )

        return _exec

    async def _run_hub_task(
        self, args: dict[str, Any], task_id: str, hub_id: str
    ) -> Any:
        """Run a queued ``/task`` to completion in its own workspace, streaming
        into the hub's bus, returning the ``ToolExecutionResult`` the hub queue
        runner awaits. Additive — does NOT touch the in-turn fire-and-forget
        ``_dispatch_as_task`` path."""
        from agent_foundation.common.inferencers.agentic_inferencers.conversational.protocols import (
            ToolExecutionResult,
        )

        task_executor = self._executor_map.get("task")
        if task_executor is None:
            return ToolExecutionResult(
                result="[hub exec_task: 'task' executor unavailable]"
            )
        from agent_foundation.common.workspace.allocator import allocate_tool_workspace

        session_root = self._session_context.get("session_root", "")
        base_dir = None
        if session_root:
            base_dir = Path(session_root) / "tasks"
            base_dir.mkdir(parents=True, exist_ok=True)
        workspace = allocate_tool_workspace("task", base_dir=base_dir)
        task_ctx = {
            **self._session_context,
            "task_id": task_id,
            "session_root": session_root,
            "working_dir": str(workspace),
            "interactive": self._build_hub_task_interactive(task_id, hub_id),
        }
        return await task_executor(args, task_ctx)

    def _build_hub_task_interactive(self, task_id: str, hub_id: str) -> Any:
        """A ``TaskWebSocketInteractive`` whose every wire message is wrapped as a
        hub ``dashboard_event`` (event_type = the message's own ``type``), so a
        queued task's token/stream output lands in the hub's live bus and the FE
        reducer translates it. No-op send when no socket / no dashboard transport
        is attached."""
        import asyncio

        from openteam.server.services.websocket_interactive import (
            TaskWebSocketInteractive,
        )

        parent = self._interactive

        async def _wrapping_send(msg: dict[str, Any]) -> None:
            if parent is None or not hasattr(parent, "send_dashboard_event"):
                return
            try:
                await parent.send_dashboard_event(
                    hub_id, str(msg.get("type") or "update"), msg
                )
            except Exception as exc:  # noqa: BLE001 — streaming is best-effort
                logger.warning("[dashboard] hub task stream wrap failed: %s", exc)

        return TaskWebSocketInteractive(
            _wrapping_send, asyncio.Queue(), task_id=task_id
        )

    async def _maybe_route_task_to_hub(self, arguments: dict[str, Any]) -> Any:
        """Route a ``task`` call into the active Experiment Hub in either of
        two modes:

        - **Explicit** (B2, v3): user set ``--experiment-hub``. The user has
          opted in; skip the ownership-overlap gate.
        - **Implicit** (auto-route, #15): ``--use-proposal``/``--proposals-path``
          + ``--proposal-ids`` where the ids overlap the active hub's owned
          proposals (``phase_outputs["research_proposals"]``).

        Returns a routed ``ToolExecutionResult`` or ``None`` (fall through).
        Fail-safe: any exception falls through to a normal task run."""
        proposal_ids_raw = (
            arguments.get("proposal_ids") or arguments.get("proposal_id") or ""
        )
        explicit_hub = bool(arguments.get("experiment_hub"))
        uses_proposal = bool(
            arguments.get("use_proposal")
            or arguments.get("proposals_path")  # B1 alias
            or arguments.get("proposals")
            or arguments.get("proposal_path")
            or proposal_ids_raw
        )
        # Fire on explicit --experiment-hub (user opt-in) OR the pre-existing
        # implicit auto-route trigger (uses_proposal + proposal_ids_raw).
        if not (explicit_hub or (uses_proposal and proposal_ids_raw)):
            return None
        sid = self._session_context.get("session_id", "")
        if not sid or self._session_store is None:
            return None
        try:
            session = self._session_store.get_session(sid) or {}
        except Exception:
            return None
        wc_dict = session.get("workflow_context") or {}
        active_mid = wc_dict.get("active_multi_task_id")
        if not active_mid:
            # Even for explicit --experiment-hub we require an already-open
            # hub: `open_experiment_hub` needs proposals_data to seed the
            # Selection tab and we don't have it in this arguments-only
            # context. The SOP is responsible for calling
            # `proposal-selection --experiment-hub` FIRST to open the hub.
            if explicit_hub:
                logger.info(
                    "[dashboard] task --experiment-hub with no active hub; "
                    "falling through to normal task run (SOP should open "
                    "the hub via proposal-selection --experiment-hub first)"
                )
            return None
        proposal_ids = [
            s.strip() for s in str(proposal_ids_raw).split(",") if s.strip()
        ]
        # For implicit auto-route (no --experiment-hub flag), the ownership
        # overlap check absorbs ONLY hub-owned ids (#15). Explicit
        # --experiment-hub bypasses this — user opt-in.
        if not explicit_hub:
            if not proposal_ids:
                return None
            owned: set[str] = set()
            for d in (wc_dict.get("phase_outputs") or {}).get(
                "research_proposals"
            ) or []:
                if isinstance(d, dict) and d.get("id"):
                    owned.add(str(d["id"]))
            if owned and not (set(proposal_ids) & owned):
                return None  # not hub-owned → run as a normal task
        hub_id_holder: dict[str, str] = {"hub_id": str(active_mid)}
        built = self._build_hub_controller(
            self._make_hub_emit(hub_id_holder), hub_id_holder
        )
        if built is None:
            return None
        controller, wc = built
        try:
            from agent_foundation.common.inferencers.agentic_inferencers.conversational.protocols import (
                ToolExecutionResult,
            )

            ids_label = ",".join(proposal_ids) if proposal_ids else "task"
            request = arguments.get("request") or f"Implement proposals {ids_label}"
            await controller.add_to_experiment_hub(
                multi_task_id=str(active_mid),
                request=str(request),
                title=f"Implement {ids_label}"[:80],
                hypothesis_id=ids_label,
            )
            self._persist_wc(wc)
            logger.info(
                "[dashboard] routed task %s %s into hub %s",
                "--experiment-hub" if explicit_hub else "--use-proposal",
                ids_label,
                active_mid,
            )
            return ToolExecutionResult(
                result=(
                    f"[Implementation of {ids_label} routed to the active "
                    f"Experiment Hub (hub={active_mid}); see the hub's "
                    f"Implementation tab.]"
                ),
                context_updates={"routed_to_hub": str(active_mid)},
            )
        except Exception as exc:  # noqa: BLE001 — fall through to normal dispatch
            logger.warning(
                "[dashboard] hub routing failed (%s); running as a normal task",
                exc,
            )
            return None
