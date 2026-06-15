"""Unit tests for WebSocketInteractive.for_background_task.

Covers the per-task child interactive used by agent-dispatched async tools:
registration in the per-connection routing table, task_id-stamped child type,
leaf semantics, prompt_data snapshot, response round-trip, cleanup, and the
no-registry RuntimeError contract.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Add src/ to path (mirror sibling tests)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from openteam.server.services.websocket_interactive import (  # noqa: E402
    TaskWebSocketInteractive,
    WebSocketInteractive,
)


async def _noop_send(msg: dict) -> None:  # pragma: no cover - trivial
    return None


class TestForBackgroundTask:

    def test_registers_and_returns_task_child(self):
        """Returns a TaskWebSocketInteractive with its own registered queue."""
        registry: dict = {}
        parent = WebSocketInteractive(
            _noop_send, asyncio.Queue(), task_input_queues=registry
        )

        child, cleanup = parent.for_background_task("task-x")

        assert isinstance(child, TaskWebSocketInteractive)
        assert child._task_id == "task-x"
        # Shares the parent's send callback (same WebSocket connection)...
        assert child._send is parent._send
        # ...but owns an independent input queue, registered under task_id.
        assert child._input_queue is not parent._input_queue
        assert registry["task-x"] is child._input_queue
        # Child is a leaf: it cannot spawn further children.
        assert child._task_input_queues is None

    def test_snapshots_last_prompt_data_not_synced(self):
        """Child gets a point-in-time snapshot; later parent reassignment does not propagate."""
        registry: dict = {}
        parent = WebSocketInteractive(
            _noop_send, asyncio.Queue(), task_input_queues=registry
        )
        snap = {"rendered_prompt": "dispatching-turn"}
        parent._last_prompt_data = snap

        child, _ = parent.for_background_task("t1")
        assert child._last_prompt_data is snap

        # _on_new_turn reassigns (not mutates) the parent's attribute — the
        # child keeps the dispatching turn's snapshot.
        parent._last_prompt_data = {"rendered_prompt": "later-turn"}
        assert child._last_prompt_data is snap

    @pytest.mark.asyncio
    async def test_response_round_trip_via_registry(self):
        """A value routed into the registered queue is delivered to the child's aget_input."""
        registry: dict = {}
        parent = WebSocketInteractive(
            _noop_send, asyncio.Queue(), task_input_queues=registry
        )
        child, _ = parent.for_background_task("t1")

        await registry["t1"].put("Approve")
        assert await child.aget_input() == "Approve"

    def test_cleanup_deregisters_idempotently(self):
        """cleanup() removes the task_id; calling it twice is safe."""
        registry: dict = {}
        parent = WebSocketInteractive(
            _noop_send, asyncio.Queue(), task_input_queues=registry
        )
        _, cleanup = parent.for_background_task("t1")
        assert "t1" in registry

        cleanup()
        assert "t1" not in registry
        cleanup()  # idempotent — no KeyError
        assert "t1" not in registry

    def test_raises_without_registry(self):
        """No routing table wired -> RuntimeError so callers fall back to yolo."""
        parent = WebSocketInteractive(_noop_send, asyncio.Queue())  # no task_input_queues
        with pytest.raises(RuntimeError):
            parent.for_background_task("t1")

    def test_concurrent_children_have_independent_queues(self):
        """Two background tasks register distinct queues under distinct keys."""
        registry: dict = {}
        parent = WebSocketInteractive(
            _noop_send, asyncio.Queue(), task_input_queues=registry
        )
        child_a, _ = parent.for_background_task("a")
        child_b, _ = parent.for_background_task("b")

        assert registry["a"] is child_a._input_queue
        assert registry["b"] is child_b._input_queue
        assert child_a._input_queue is not child_b._input_queue
