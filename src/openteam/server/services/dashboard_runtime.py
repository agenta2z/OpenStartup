"""Out-of-turn dashboard runtime: connection registry + run supervisor.

REST-triggered hub actions (e.g. ``POST .../submissions/{id}/run``) fire OUTSIDE
an agentic turn, so (a) they have no in-scope ``WebSocketInteractive`` to push
``dashboard_event`` / ``dashboard_status`` through, and (b) the long-lived run
must not block the FastAPI worker and must be cancellable + restart-reconcilable.

This module supplies the two pieces (plan findings #12 + #20):

* :class:`ConnectionRegistry` — ``session_id`` → the live WebSocket send-callbacks
  (one per connected browser tab). ``emit(session_id, message)`` looks them up and
  broadcasts; dead connections are pruned. The injected ``emit_event`` that hub
  services use to push live updates is just ``registry.emit``.
* :class:`HubRunSupervisor` — per-``(session_id, run_id)`` tracked
  ``asyncio.Task``s for out-of-turn hub runs: spawned without blocking the worker,
  cancellable individually / per-session (on a ``cancel`` REST call, WS
  disconnect, or session close). The in-turn path keeps using the dispatcher's
  ``_dispatch_as_task``; this is its out-of-turn equivalent.

Both live on ``app.state`` (created in ``main.lifespan``). Pure stdlib asyncio —
no FastAPI import, so the transport layer can reuse them freely.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# A WebSocket send-callback: ``async def send(message: dict) -> None``.
SendCallback = Callable[[dict[str, Any]], Awaitable[None]]


class ConnectionRegistry:
    """``session_id`` → set of live WS send-callbacks (one per connected tab)."""

    def __init__(self) -> None:
        self._conns: dict[str, set[SendCallback]] = {}
        self._lock = asyncio.Lock()

    async def register(self, session_id: str, send: SendCallback) -> None:
        """Register a connection's send-callback under a session (idempotent)."""
        if not session_id:
            return
        async with self._lock:
            self._conns.setdefault(session_id, set()).add(send)
            count = len(self._conns[session_id])
        logger.debug("[conn] registered %s (connections=%d)", session_id, count)

    async def deregister(self, session_id: str, send: SendCallback) -> None:
        """Remove a connection's send-callback (on WebSocketDisconnect)."""
        if not session_id:
            return
        async with self._lock:
            conns = self._conns.get(session_id)
            if conns:
                conns.discard(send)
                if not conns:
                    self._conns.pop(session_id, None)

    def has(self, session_id: str) -> bool:
        """True if at least one live connection exists for the session."""
        return bool(self._conns.get(session_id))

    async def emit(self, session_id: str, message: dict[str, Any]) -> int:
        """Broadcast ``message`` to all live connections for ``session_id``.

        Returns the number of connections reached. Connections whose send raises
        are pruned. Best-effort: never raises (a dead socket must not abort a hub
        run). This is the ``emit_event`` hub services are injected with."""
        async with self._lock:
            targets = list(self._conns.get(session_id, ()))
        if not targets:
            logger.debug("[conn] emit to %s: no live connections", session_id)
            return 0
        sent = 0
        dead: list[SendCallback] = []
        for cb in targets:
            try:
                await cb(message)
                sent += 1
            except Exception as exc:  # noqa: BLE001 — never let one dead socket abort
                logger.warning(
                    "[conn] send failed for %s; pruning connection: %s",
                    session_id,
                    exc,
                )
                dead.append(cb)
        if dead:
            async with self._lock:
                conns = self._conns.get(session_id)
                if conns:
                    for cb in dead:
                        conns.discard(cb)
                    if not conns:
                        self._conns.pop(session_id, None)
        return sent

    def make_emitter(
        self, session_id: str
    ) -> Callable[[dict[str, Any]], Awaitable[int]]:
        """Return a session-bound ``emit(message)`` for callers that prefer a
        no-session-arg closure (e.g. a hub controller scoped to one session)."""

        async def _emit(message: dict[str, Any]) -> int:
            return await self.emit(session_id, message)

        return _emit


class HubRunSupervisor:
    """Per-``(session_id, run_id)`` tracked ``asyncio.Task``s for out-of-turn runs."""

    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def spawn(
        self, session_id: str, run_id: str, coro: Awaitable[Any]
    ) -> asyncio.Task:
        """Spawn + track a run as a background task.

        Replaces any existing run with the same ``(session_id, run_id)`` key
        (cancels the old one first) so a re-issued run can't double-execute. The
        task self-cleans from the registry on completion."""
        await self.cancel(session_id, run_id)
        task: asyncio.Task = asyncio.ensure_future(coro)
        key = (session_id, run_id)
        async with self._lock:
            self._runs[key] = task

        def _done(finished: asyncio.Task, _key: tuple[str, str] = key) -> None:
            # Self-cleanup only if we still own this slot (a replacement may have
            # taken it). Synchronous callback — no lock; dict ops are atomic.
            if self._runs.get(_key) is finished:
                self._runs.pop(_key, None)

        task.add_done_callback(_done)
        logger.info("[hub-run] spawned %s/%s", session_id, run_id)
        return task

    async def cancel(self, session_id: str, run_id: str) -> bool:
        """Cancel + await a single tracked run. Returns True if one was cancelled."""
        key = (session_id, run_id)
        async with self._lock:
            task = self._runs.get(key)
        if task is None or task.done():
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001 — surfacing the run's own error here is noise
            logger.debug(
                "[hub-run] %s/%s ended with %s during cancel", session_id, run_id, exc
            )
        async with self._lock:
            if self._runs.get(key) is task:
                self._runs.pop(key, None)
        return True

    async def cancel_session(self, session_id: str) -> int:
        """Cancel all tracked runs for a session (on WS disconnect / close)."""
        async with self._lock:
            run_ids = [rid for (sid, rid) in self._runs if sid == session_id]
        cancelled = 0
        for run_id in run_ids:
            if await self.cancel(session_id, run_id):
                cancelled += 1
        if cancelled:
            logger.info("[hub-run] cancelled %d run(s) for %s", cancelled, session_id)
        return cancelled

    def active_runs(self, session_id: str) -> list[str]:
        """Return the run_ids currently live for a session."""
        return [
            rid
            for (sid, rid), task in self._runs.items()
            if sid == session_id and not task.done()
        ]
