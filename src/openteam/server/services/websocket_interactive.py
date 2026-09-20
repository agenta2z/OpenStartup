"""WebSocketInteractive — duck-typed adapter for ConversationalInferencer.run_agentic_loop().

Maps the 4 methods that run_agentic_loop() checks via hasattr() to WebSocket messages:
- stream_token_batches → batched {"type": "token"} messages
- send_turn_boundary → {"type": "turn_boundary"} message
- asend_response → {"type": "pending_input"} message (conversation tool prompts)
- aget_input → awaits from asyncio.Queue (fed by incoming WS messages)

Does NOT inherit from InteractiveBase — run_agentic_loop uses hasattr duck-typing.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, AsyncIterator, Callable, Coroutine


class WebSocketInteractive:
    """Adapts WebSocket transport for ConversationalInferencer.run_agentic_loop()."""

    def __init__(
        self,
        send_callback: Callable[[dict[str, Any]], Coroutine],
        input_queue: asyncio.Queue,
        *,
        task_input_queues: "dict[str, asyncio.Queue] | None" = None,
        pending_input_cache: "dict[str, Any] | None" = None,
        snapshot_store: "Any | None" = None,
        session_id: str = "",
        data_service: "Any | None" = None,
    ) -> None:
        self._send = send_callback
        self._input_queue = input_queue
        # Data-service handle for DURABLE pending-widget persistence (Layer 2).
        # Used by persist_pending_widget() to write the marker (session_state.json)
        # + emit-point blob (sidecar) so an unanswered widget survives a WS
        # reconnect / server restart. None on CLI/dev-tool paths (no persistence).
        self._data_service = data_service
        # The pending_input_id minted by the most recent asend_response — exposed
        # so the CI can key the durable marker+blob to the same id as the wire
        # frame + the connection-scoped cache entry.
        self._last_pending_input_id: str | None = None
        # v4 Phase 4.1 — TaskGraphSnapshotStore reference + session_id for the
        # per-task snapshot mirror. send_graph_event mutates the snapshot
        # BEFORE the wire send so manager_websocket_routes.session_init can
        # replay the state to a freshly-connected client. Optional — None on
        # the CLI/dev-tool path (no replay required there).
        self._snapshot_store = snapshot_store
        self._session_id = session_id
        # Per-connection routing table for background-task input queues. Shared
        # with the WebSocket handler's pending_input_response router so that a
        # child interactive created via for_background_task() can receive widget
        # responses keyed by task_id. None on CLI/standalone paths (no routing
        # table) — for_background_task() then raises and callers fall back to
        # non-interactive (yolo).
        self._task_input_queues = task_input_queues
        # Connection-scoped pending-input metadata cache (keyed by
        # pending_input_id), shared with the route's pending_input_response
        # handler so widget submissions can be persisted as widget_response
        # history messages. None on the dev-tool/CLI path (no round context).
        self._pending_input_cache = pending_input_cache
        self._clean_output: str | None = None  # set by on_clean_output_available()
        # Current RoundContext (set by AF via set_round_context). Carries
        # message_id + round_index that stamp every per-round WS event.
        self._round_ctx: dict[str, Any] | None = None
        # Latest rendered prompt data, kept in sync by ConversationService
        # on_round_complete so that intermediate widget interactions can carry
        # inline prompt_data. Used by asend_response to populate pending_input
        # messages without a REST round-trip.
        self._last_prompt_data: dict[str, Any] | None = None

    def set_round_context(self, ctx: dict[str, Any] | None) -> None:
        """Store the current RoundContext and reset per-round clean output.

        Called by AF's run_agentic_loop at the top of each round (via the
        server's on_round_start hook). The ctx carries ``message_id`` and
        ``round_index`` which are stamped onto every per-round WS event
        (token, stream_correction, pending_input, message_end).
        """
        self._round_ctx = ctx
        self._clean_output = None  # per-round reset

    @property
    def current_message_id(self) -> str | None:
        """The current round's message_id, or None when no round is active."""
        if self._round_ctx:
            return self._round_ctx.get("message_id")
        return None

    @property
    def clean_output(self) -> str | None:
        """Clean final output from --output-file, if available."""
        return self._clean_output

    def for_background_task(
        self, task_id: str
    ) -> "tuple[TaskWebSocketInteractive, Callable[[], None]]":
        """Create a leaf interactive for a background tool task.

        Returns ``(child, cleanup)``. The child shares this interactive's
        ``_send`` (same WebSocket connection) but owns a fresh input queue,
        registered under ``task_id`` in the per-connection routing table so
        ``pending_input_response`` messages route to it. The child is a
        ``TaskWebSocketInteractive`` so it stamps ``task_id`` onto streamed
        tokens (routing them to the task panel, not the main conversation).

        Raises ``RuntimeError`` when no routing table is wired (CLI/standalone):
        the caller must then fall back to non-interactive (yolo) rather than
        register an unreachable queue that would hang on ``aget_input()``. The
        child is deliberately NOT given the routing table — it is a leaf and
        cannot spawn further children (nested ``task`` calls run inline).
        """
        if self._task_input_queues is None:
            raise RuntimeError(
                "for_background_task requires task_input_queues "
                "(no routing table wired on this interactive)"
            )
        child_queue: asyncio.Queue = asyncio.Queue()
        # Propagate the snapshot store + session_id (from THIS interactive, which
        # is the store-bearing main-conversation interactive) so the child's
        # send_graph_event mirrors into the snapshot under the chip's task_id and
        # send_task_status fires mark_task_terminal. Keystone of graph durability
        # for async-dispatched (SOP) tasks. Routing table still intentionally NOT
        # passed — leaf tasks don't spawn children (that is unrelated to mirroring).
        child = TaskWebSocketInteractive(
            self._send,
            child_queue,
            task_id=task_id,
            snapshot_store=self._snapshot_store,
            session_id=self._session_id,
        )
        # Point-in-time snapshot of the dispatching turn's prompt_data so the
        # child's first asend_response can inline it. NOT kept in sync: the
        # parent's _last_prompt_data is later reassigned (not mutated) by
        # ConversationService._on_new_turn, which does not propagate here.
        child._last_prompt_data = self._last_prompt_data
        self._task_input_queues[task_id] = child_queue

        def _cleanup() -> None:
            self._task_input_queues.pop(task_id, None)

        return child, _cleanup

    _graph_send_failures: int = 0
    _graph_send_disabled: bool = False

    async def send_graph_event(self, event: Any, task_id: str = "") -> None:
        """Send a graph visualization event to the frontend.

        Dispatches GraphTopologyEvent, NodeStatusEvent, NodeStreamEvent to the
        appropriate WS message type. Wrapped in try/except with circuit breaker
        so visualization failures never abort computation.

        v4 Phase 4.1 — also mirrors the event into the per-task snapshot
        before serializing for the wire. The snapshot is the source of truth
        for replay on session_init / request_graph_replay; mutating here
        (the single emit point) keeps it in lock-step with whatever the
        client sees.
        """
        if self._graph_send_disabled:
            return
        import logging as _log

        _logger = _log.getLogger(__name__)
        from agent_foundation.common.inferencers.graph_events import (
            GraphReconcileEvent,
            GraphTopologyEvent,
            NodeStatusEvent,
            NodeStreamEvent,
        )

        # v4 Phase 4.1 — snapshot mutation BEFORE wire dispatch. Guarded so a
        # snapshot bug can never abort the live send (visualization parity is
        # nice-to-have; live correctness is load-bearing).
        if self._snapshot_store is not None and task_id and self._session_id:
            try:
                snap = self._snapshot_store.get_or_create(self._session_id, task_id)
                snap.apply_event(event)
            except Exception as _snap_exc:
                _logger.warning(
                    "[WS] snapshot apply failed (task_id=%s): %s",
                    task_id,
                    _snap_exc,
                )
        if isinstance(event, GraphTopologyEvent):
            msg: dict[str, Any] = {
                "type": "graph_topology",
                "task_id": task_id,
                "nodes": event.nodes,
                "edges": event.edges,
                "layout": event.layout,
            }
            if event.parent_node_id:
                msg["parent_node_id"] = event.parent_node_id
            if event.version:
                msg["version"] = event.version
            # v4 Phase 5.2 — only ship reset when it deviates from the default
            # True; this keeps the wire payload compact for the common case
            # (BTA full-diamond re-emit) and explicit-only for append cases
            # (LWI dynamic round add). Client treats absent === True.
            if getattr(event, "reset", True) is False:
                msg["reset"] = False
            # Root topology resets the circuit breaker
            if not event.parent_node_id:
                self._graph_send_disabled = False
                self._graph_send_failures = 0
        elif isinstance(event, NodeStatusEvent):
            msg = {
                "type": "node_status",
                "task_id": task_id,
                "node_id": event.node_id,
                "status": event.status,
                "label": event.label,
                "error": event.error,
                "timestamp": event.timestamp,
                "output_path": event.output_path,
            }
        elif isinstance(event, NodeStreamEvent):
            msg = {
                "type": "node_stream",
                "task_id": task_id,
                "node_id": event.node_id,
                "content": event.content,
                "is_final": event.is_final,
            }
        elif isinstance(event, GraphReconcileEvent):
            msg = {
                "type": "graph_reconcile",
                "task_id": task_id,
                "nodes": event.node_statuses,
            }
        else:
            return
        try:
            await self._send(msg)
            self._graph_send_failures = 0
        except Exception as exc:
            self._graph_send_failures += 1
            if self._graph_send_failures >= 3:
                self._graph_send_disabled = True
                _logger.warning(
                    "[WS] Graph events disabled after %d consecutive failures: %s",
                    self._graph_send_failures,
                    exc,
                )
            else:
                _logger.debug(
                    "[WS] send_graph_event failed (%d/3): %s",
                    self._graph_send_failures,
                    exc,
                )

    async def on_clean_output_available(self, clean_output: str) -> None:
        """Called after streaming completes when a cleaner final output is available.

        Stores the clean output and sends a 'stream_correction' WS event so the
        frontend can replace the noisy streamed display with the exact LLM text.
        This fires before message_end, giving the frontend time to update the
        streaming bubble before it's committed as a message.

        Args:
            clean_output: Clean LLM output from --output-file (no TUI noise,
                code fences intact, no terminal-width line wrapping).
        """
        self._clean_output = clean_output
        msg: dict[str, Any] = {
            "type": "stream_correction",
            "content": clean_output,
        }
        self._stamp_round(msg)
        await self._send(msg)

    async def stream_token_batches(
        self,
        token_stream: AsyncIterator[tuple[str, dict]],
        session_id: str,
        batch_interval_ms: float = 50.0,
        task_id: str | None = None,
        send_stream_end: bool = True,
        turn_number: int | None = None,
    ) -> str:
        """Accumulate tokens from an async generator, flush as batched WS messages.

        Returns the full concatenated response text.
        """
        full_text: list[str] = []
        batch: list[str] = []
        last_flush = time.monotonic()

        async for chunk, metadata in token_stream:
            batch.append(chunk)
            full_text.append(chunk)
            if (time.monotonic() - last_flush) * 1000 >= batch_interval_ms:
                combined = "".join(batch)
                msg = {
                    "type": "token",
                    "content": combined,
                    "metadata": {"agent_name": "Orchestrator"},
                }
                if task_id:
                    msg["task_id"] = task_id
                self._stamp_round(msg)
                await self._send(msg)
                batch = []
                last_flush = time.monotonic()

        if batch:
            combined = "".join(batch)
            msg = {
                "type": "token",
                "content": combined,
                "metadata": {"agent_name": "Orchestrator"},
            }
            if task_id:
                msg["task_id"] = task_id
            self._stamp_round(msg)
            await self._send(msg)

        return "".join(full_text)

    def _stamp_round(self, msg: dict[str, Any]) -> None:
        """Stamp {message_id, round_index} from the current RoundContext.

        No-op when no round context is set (e.g. dev-tool path), keeping
        background-task token messages unchanged.
        """
        if self._round_ctx:
            mid = self._round_ctx.get("message_id")
            ridx = self._round_ctx.get("round_index")
            if mid is not None:
                msg["message_id"] = mid
            if ridx is not None:
                msg["round_index"] = ridx

    async def send_task_status(
        self,
        task_id: str,
        status: str,
        request: str = "",
        tool_name: str = "",
        error: str = "",
        error_type: str = "",
    ) -> None:
        """Notify the frontend of task lifecycle events (starting/running/completed/error).

        Creates or updates a task subtab in the UI.

        v4 Phase 4.1 — on terminal status, stamp the per-task graph snapshot
        so the store's prune sweep can evict it after TTL. Active snapshots
        never expire; terminal snapshots get the 600s grace window
        (configurable in TaskGraphSnapshotStore) so an immediate refresh
        still hydrates.

        ``error_type`` (snake_case on the wire — matches ``task_id`` /
        ``tool_name``) carries the exception class name for a real error
        (e.g. ``"ValueError"``) or the sentinel ``"interrupted"`` for a
        reconcile-healed row so the UI can distinguish them.
        """
        msg: dict[str, Any] = {
            "type": "task_status",
            "task_id": task_id,
            "status": status,
        }
        if request:
            msg["request"] = request
        if tool_name:
            msg["tool_name"] = tool_name
        if error:
            msg["error"] = error
        if error_type:
            msg["error_type"] = error_type
        await self._send(msg)
        if (
            self._snapshot_store is not None
            and self._session_id
            and task_id
            and status in ("completed", "error")
        ):
            try:
                self._snapshot_store.mark_task_terminal(self._session_id, task_id)
            except Exception:
                # Never let TTL bookkeeping abort the WS notification path.
                pass

    async def send_dashboard_open(
        self,
        hub_id: str,
        manifest: dict[str, Any],
        seed: "dict[str, Any] | None" = None,
    ) -> None:
        """Notify the frontend to open/activate a Dashboard subtab.

        Mirror of :meth:`send_task_status` for the Dashboard ``tool_type``:
        creates a dashboard subtab in the UI seeded with ``manifest`` (the
        canonical tab structure from the tool's ``dashboard_config``) + ``seed``
        (initial state, e.g. the selected proposals for the Selection tab).
        """
        await self._send(
            {
                "type": "dashboard_open",
                "hub_id": hub_id,
                "manifest": manifest,
                "seed": seed or {},
            }
        )

    async def send_dashboard_status(
        self, hub_id: str, status: str, **extra: Any
    ) -> None:
        """Notify the frontend of a Dashboard subtab status change."""
        await self._send(
            {"type": "dashboard_status", "hub_id": hub_id, "status": status, **extra}
        )

    async def send_dashboard_event(
        self,
        hub_id: str,
        event_type: str,
        payload: "dict[str, Any] | None" = None,
    ) -> None:
        """Push a generic live-update event into a Dashboard's ``wsEvents$`` stream.

        ``event_type`` ∈ run_progress / run_completed / submission_state /
        setup_completed / combo_changed / verdict_ready / autopilot_tick.
        """
        await self._send(
            {
                "type": "dashboard_event",
                "hub_id": hub_id,
                "event_type": event_type,
                "payload": payload or {},
            }
        )

    async def send_turn_boundary(
        self,
        session_id: str,
        turn_number: int = 0,
        cache_folder: str = "",
    ) -> None:
        """Signal a turn boundary (agentic loop iteration boundary)."""
        await self._send(
            {
                "type": "turn_boundary",
                "turn_number": turn_number,
            }
        )

    async def send_round_message_end(
        self,
        *,
        message_id: str,
        round_index: int,
        turn_number: int,
        final_content: str,
    ) -> None:
        """Emit the per-round terminal message_end.

        Always emitted (balanced terminal) for every round. When
        ``final_content`` is "" the UI commits/persists nothing; otherwise it
        commits the round's assistant bubble carrying {message_id, round_index}.
        """
        await self._send(
            {
                "type": "message_end",
                "message_id": message_id,
                "round_index": round_index,
                "turn_number": turn_number,
                "final_content": final_content,
            }
        )

    @staticmethod
    def _sanitize_for_json(value: Any) -> Any:
        """Recursively make a value JSON-serializable.

        Mirrors `ConversationService._sanitize_feed` semantics but operates on
        any nested value (the top-level prompt_data dict contains both safe
        strings/dicts AND a `template_feed` dict that may contain workflow
        objects like SOP, SOPPhase, StateGraphTracker — those come from the
        Jinja2 template's prior_context spread).

        For each value:
          - Try `json.dumps(value)` — if it succeeds, keep as-is (preserves
            structure for the UI's prompt viewer).
          - Otherwise: if dict, recurse per key; if list/tuple, recurse per
            element; else fall back to `str(value)`.

        This is the same pattern used at multiple existing sites in the
        codebase (`_sanitize_feed`, `get_last_prompt_data`) — we centralize it
        here so the WS transport always produces serializable payloads
        regardless of what upstream code passes.
        """
        import json

        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            pass

        if isinstance(value, dict):
            return {
                k: WebSocketInteractive._sanitize_for_json(v)
                for k, v in value.items()
                if not (isinstance(k, str) and k.startswith("_"))  # drop private keys
            }
        if isinstance(value, (list, tuple)):
            return [WebSocketInteractive._sanitize_for_json(v) for v in value]
        try:
            return str(value)
        except Exception:
            return f"<non-serializable: {type(value).__name__}>"

    async def asend_response(
        self,
        response: Any,
        flag: Any = None,
        **kwargs: Any,
    ) -> None:
        """Send a conversation tool prompt (confirmation, clarification, etc.)."""
        import logging as _logging

        _log = _logging.getLogger(__name__)
        input_mode = kwargs.get("input_mode")
        msg: dict[str, Any] = {
            "type": "pending_input",
            "content": str(response),
        }
        if input_mode is not None:
            mode_dict = (
                input_mode.to_dict() if hasattr(input_mode, "to_dict") else input_mode
            )
            msg["input_mode"] = mode_dict
            _log.info(
                "[asend_response] input_mode.mode=%s metadata=%s",
                mode_dict.get("mode"),
                mode_dict.get("metadata"),
            )
        else:
            _log.info("[asend_response] no input_mode (free_text fallback)")

        # Inline prompt_data so the UI's "View Prompt" button on the preamble
        # widget message has the rendered prompt available without a REST fetch.
        # ConversationalInferencer._handle_conversation_tool passes prompt_data=
        # explicitly (carrying the raw _last_template_feed which may contain
        # non-JSON-serializable objects like SOP, SOPPhase, StateGraphTracker
        # from the workflow's prior_context); otherwise we fall back to the
        # last-known value cached on this interactive (kept fresh by
        # ConversationService._on_new_turn, which IS already sanitized via
        # _sanitize_feed).
        #
        # We must sanitize before serializing — without it, json.dumps() raises
        # "Object of type SOP is not JSON serializable", send_safe drops the
        # entire pending_input message, and the agentic loop hangs at
        # aget_input() waiting for a user response that can never arrive
        # because the UI never received the widget request.
        prompt_data = kwargs.get("prompt_data") or self._last_prompt_data
        sanitized_prompt_data = None
        if prompt_data:
            sanitized_prompt_data = self._sanitize_for_json(prompt_data)
            msg["prompt_data"] = sanitized_prompt_data

        # Per-round identity + a unique pending_input_id so the route's
        # pending_input_response handler can correlate the widget submission
        # back to this prompt (and persist it as a widget_response message).
        pending_input_id = uuid.uuid4().hex
        msg["pending_input_id"] = pending_input_id
        self._last_pending_input_id = pending_input_id
        if self._round_ctx:
            mid = self._round_ctx.get("message_id")
            ridx = self._round_ctx.get("round_index")
            turn_number = self._round_ctx.get("turn_number")
            if mid is not None:
                msg["message_id"] = mid
            if ridx is not None:
                msg["round_index"] = ridx
            if turn_number is not None:
                msg["turn_number"] = turn_number

            # Only the conversation path (round context present) writes a cache
            # entry. The dev-tool interactive has no round ctx → no entry.
            if self._pending_input_cache is not None:
                mode_dict = msg.get("input_mode")
                metadata = (
                    mode_dict.get("metadata", {}) if isinstance(mode_dict, dict) else {}
                ) or {}
                self._pending_input_cache[pending_input_id] = {
                    "scope": "conversation",
                    "session_id": self._round_ctx.get("session_id"),
                    "turn_number": turn_number,
                    "round_index": ridx,
                    "message_id": mid,
                    "pending_input_id": pending_input_id,
                    "prompt": str(response),
                    "input_mode": mode_dict,
                    "widget_type": kwargs.get("widget_type"),
                    "viewPath": metadata.get("view") or metadata.get("viewPath"),
                    "viewLabel": metadata.get("view_label")
                    or metadata.get("viewLabel"),
                    "viewType": metadata.get("view_type")
                    or metadata.get("viewType")
                    or "file",
                    "prompt_data": sanitized_prompt_data,
                }

        await self._send(msg)

    async def aget_input(self) -> Any:
        """Wait for user input from the WebSocket (fed by incoming messages)."""
        return await self._input_queue.get()

    def persist_pending_widget(
        self,
        *,
        tools: "list | None",
        action_tools: "list | None",
        blob: dict[str, Any],
    ) -> None:
        """Durably persist the widget just emitted by ``asend_response`` so an
        unanswered widget survives a WS reconnect / server restart (Layer 2,
        Piece 1). Assembles the marker from the connection-scoped cache entry
        (prompt / input_mode / turn / round / message_id / pending_input_id) plus
        the full ``ToolsToInvoke`` with a faithful ``ConversationTool`` round-trip
        (so recovery reconstructs the EXACT widget) + the CI-supplied emit-point
        continuation ``blob``; the store writes sidecar-first. No-op on CLI /
        dev-tool paths (no data_service / cache / round context). Best-effort —
        never breaks the live turn."""
        if self._data_service is None or self._pending_input_cache is None:
            return
        pid = self._last_pending_input_id
        if not pid:
            return
        entry = dict(self._pending_input_cache.get(pid) or {})
        if entry.get("scope") != "conversation":
            return
        entry["tools"] = [
            t.to_dict() if hasattr(t, "to_dict") else t for t in (tools or [])
        ]
        entry["action_tools"] = list(action_tools or [])
        store = getattr(self._data_service, "session_store", None)
        if store is None or not hasattr(store, "set_pending_input"):
            return
        try:
            store.set_pending_input(self._session_id, entry, blob)
        except Exception as e:  # best-effort — never break the live turn
            import logging

            logging.getLogger(__name__).warning(
                "persist_pending_widget failed (%s): %s", self._session_id, e
            )


class TaskWebSocketInteractive(WebSocketInteractive):
    """WebSocketInteractive subclass for background task streaming.

    Automatically injects `task_id` into all token messages, so the frontend
    routes them to the task panel instead of the conversation stream.
    The create_role/role_setup executors use BreakdownThenAggregateInferencer
    which doesn't call stream_token_batches directly — this subclass is provided
    for future executors that do stream through interactive.
    """

    def __init__(
        self,
        send_callback: Callable[[dict[str, Any]], Coroutine],
        input_queue: asyncio.Queue,
        *,
        task_id: str,
        snapshot_store: "Any | None" = None,
        session_id: str = "",
    ) -> None:
        # v4 Phase 4.1 / graph-persistence fix — forward the snapshot store +
        # session_id so this background-task child MIRRORS its graph events into
        # TaskGraphSnapshotStore (keyed by the same task_id as the sidebar chip)
        # and fires mark_task_terminal on completion. Without this the async SOP
        # task's graph renders live but is never captured → lost on reconnect.
        super().__init__(
            send_callback,
            input_queue,
            snapshot_store=snapshot_store,
            session_id=session_id,
        )
        self._task_id = task_id

    async def stream_token_batches(
        self,
        token_stream: AsyncIterator[tuple[str, dict]],
        session_id: str,
        **kwargs: Any,
    ) -> str:
        """Override to inject task_id into all token messages."""
        return await super().stream_token_batches(
            token_stream,
            session_id,
            task_id=self._task_id,
            **kwargs,
        )
