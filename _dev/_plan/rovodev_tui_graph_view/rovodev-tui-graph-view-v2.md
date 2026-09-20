# RovoDev TUI — OpenTeam Graph Visualization (v2 PLAN, integrated)

**Status:** Proposal · ready for review
**Created:** 2026-05-17 02:21
**Supersedes:** `rovodev-tui-graph-view-v1.md` (my prior v1), `.claude/plans/eager-roaming-clock.md` (Claude), `.cursor/plans/tui_graph_visualization_4c8499de.plan.md` (Cursor)
**Author:** rovodev (third-pass integration; both alternative plans were re-read at 02:17)
**Scope:** Add a real-time agent topology graph + per-node streaming pane to the RovoDev TUI when invoking the 4 OpenTeam slash commands (`/task`, `/create-role`, `/role-setup`, `/project-onboarding`).

---

## 0. Revision history (round 1)

This is the integrated v2. The deltas vs the three predecessor plans are listed up front so readers can verify the integration in one place.

### Wins adopted from Cursor plan (771 lines)

| Cursor's idea | Why I'm adopting it (over my v1) | Verified |
|---|---|---|
| **Wire `StdioGraphReporter` once in `tool_cli.run_cli`** (not in each executor) | Reduces the surface area from 5 executor patches to **1 service patch** + 4 trivial executor fallbacks. New OpenTeam tools added in the future get graph events automatically. This is the v6 plan's `tool_cli` boundary, re-used as the natural attach point. | `tool_cli.py:116` does `asyncio.run(execute_fn(arguments, session_context))` — direct cat |
| **Env var name: `OPENTEAM_GRAPH_EVENTS_FD`** (not `ROVODEV_TUI_GRAPH_FD`) | OpenTeam owns the protocol (it's the producer); the env var should be in OpenTeam's namespace. The TUI is just one consumer. | Naming convention |
| **`asyncio.Lock` serializes `_emit` writes** | BTA workers run concurrently under the same event loop; without a lock, interleaved bytes corrupt NDJSON lines on the pipe. My v1 missed this. | BTA worker concurrency reading `breakdown_then_aggregate_inferencer.py` |
| **`app.is_headless` freezes the spinner glyph in snapshot tests** | Standard cli-rovodev-tui idiom for deterministic Textual snapshot rendering. | `widgets/interval_updater.py:30` uses `self.app.is_headless` — direct grep verified |
| **`ContentSwitcher` of per-node `RichLog`s** (not a single `Markdown` re-rendered) | Precedent: `widgets/tool_call/invoke_subagents.py` (verified to exist with `add_subagent_response` at line 36). Per-node `RichLog` keeps each node's stream isolated → switching panels is instant, scroll position per-node is preserved, append is O(1) instead of full re-render. | `ls widgets/tool_call/` + `grep ContentSwitcher` |
| **Reuse `mock_bta_components.py` (`MockBreakdown/Worker/Aggregator`) for the TIER-1 reporter test** | Runs a *real* BTA through the *real* reporter against `io.StringIO` — far higher-signal than mocking the reporter's `_write`. | `mock_bta_components.py` verified to exist with all three classes |
| **TIER-3 manual test column** | Distinguishes "automated CI tests pass" from "I tried it in the real TUI". Both are needed; v1 only had TIER-1/2. | Better hygiene |
| **`tool_cli` ImportError fallback** | If the user's OpenTeam install lacks `StdioGraphReporter` (older AgentFoundation), the subprocess prints a warning and runs without graph events. Backward compatible. | Defensive coding |
| **Snapshot-test glyph freezing** in widget tests | Without this, `running` spinner glyph rotates → snapshot diffs flake every run. | `interval_updater.py:30` precedent |
| **Phase 6/7 post-ship optionals** (DualInferencer / PTI propagation, JsonlGraphReporter persistence) | Explicit out-of-scope-for-v1 list is clearer than my v1's vague "v2 enhancement" mentions. | Better phase scoping |

### Wins kept from my v1 (1314 lines)

| v1 idea | Why Cursor's plan also benefits from it |
|---|---|
| **React constants mirrored exactly** (`MAX_STREAM_SIZE=200_000`, `TRIM_SIZE=50_000`, `STICKY_DURATION_MS=5_000`, `MAX_TOTAL_STREAMS=10_000_000`) | Cross-product UX consistency: user switching between web and TUI gets identical mental model. Cursor's plan mentions buffers but doesn't pin numbers. |
| **`graph_reporter_factory` module** (single indirection) | Even with `tool_cli` doing the construction, the 4 executors still need to decide *which* reporter wins (WS vs Stdio) when both could be available (defensive: `session_context["interactive"]` set by an outer wrapper that also leaked the env var). One function, one precedence rule, observable via one log line. |
| **Comprehensive self-audit section** | Pre-empts review questions, documents rejected alternatives, makes the design defensible. |
| **Out-of-scope section** explicit non-goals (Windows v1, Graphviz layout, clickable artifacts to $EDITOR) | Anchors v1 scope; prevents reviewer scope creep. |
| **`_NoOpNodeInteractive` stub** | The `WebSocketGraphReporter.node_interactive()` returns a `NodeStreamInteractive` for per-node interactive prompts. Stdio path has no bidirectional channel; we stub it so `stream_token_batches`-callers don't crash. Cursor's plan brushes this as "low risk"; explicit stub > implicit assumption. |
| **Defensive `apply_status` creates minimal `NodeInfo`** when status arrives before topology | Cursor's plan drops the event; v1 keeps the data so when topology arrives later it merges in. Reconcile still corrects any drift but no information is lost. |
| **Glossary section** | Newcomer accessibility. |

### Wins explicitly REJECTED from Claude plan (90 lines)

| Claude's idea | Why rejected |
|---|---|
| **WebSocket path: probe localhost:8000, POST /api/sessions, ws://…/ws/sessions/{sid}/chat** | Three load-bearing claims are **provably wrong** (verified): (1) the actual WS route is `/manager` not `/ws/sessions/{sid}/chat`, (2) session_id is passed as the first message (not in URL), (3) `websockets` is NOT a TUI dep, (4) OpenStartup server is NOT bundled with the TUI and is NOT a typical install. Implementing Claude's path would require installing + running a separate FastAPI server as a precondition for slash commands working. **This is a regression vs the v6 "subprocess-native" design.** |
| **Fallback to subprocess when server down** | The "server up" case is the *rare* one for typical users (Cursor IDE/RovoDev TUI users do not run OpenStartup locally). The fallback would be the default codepath — making the WebSocket path dead code. |
| **`urllib.request.urlopen()` server probe** | Probes a server that 99% of users won't have running. Adds 1s latency on every slash command. |

**Verdict:** Claude plan's transport choice is unsound. Its widget UX ideas (status indicators `[*][+][!][ ]`, horizontal split) are good and partially absorbed into v2's widget design.

---

## 1. TL;DR (the integrated design)

Today: `/task "…"` in the TUI runs silently for 5–30 minutes, then dumps text. Meanwhile, OpenTeam's React UI shows a live graph of the same execution.

**The fix is purely transport-layer.** OpenTeam's `BreakdownThenAggregateInferencer` already emits 4 event types (`graph_topology`, `node_status`, `node_stream`, `graph_reconcile`) via the duck-typed `graph_reporter` protocol. The React UI's `WebSocketGraphReporter` is one consumer; we add a **second consumer, `StdioGraphReporter`**, that emits the same events as NDJSON on a dedicated file descriptor (fd 3). The TUI's slash handler reads the NDJSON stream and renders a `Tree` + `ContentSwitcher`-of-`RichLog`s widget — live, cancellable, snapshot-testable.

**Zero changes** to `BreakdownThenAggregateInferencer`. **Zero new deps** on either side. **One narrow change** to `tool_cli.run_cli` (15-line block) + 4 trivial 3-line executor fallbacks. The TUI work is two new files + 4 small widget modules.

**Effort:** ~3 focused days (1 day AgentFoundation, 0.5 day OpenStartup, 1.5 days TUI).

---

## 2. Verified ground truth (every claim has a citation)

| Fact | Evidence (cited at the exact line) |
|---|---|
| `BTA.graph_reporter: Optional[Any] = attrib(default=None, kw_only=True)` and only emits when non-None | `AgentFoundation/.../breakdown_then_aggregate_inferencer.py:509` (`# Protocol: must implement on_graph_topology(event), on_node_status(node_id, status, error).`) |
| BTA calls `on_node_status` at **line 858** | `breakdown_then_aggregate_inferencer.py:858` — verified by direct `awk` |
| BTA calls `on_graph_topology` at **line 890** (pending_topo) | `breakdown_then_aggregate_inferencer.py:890` — verified |
| BTA calls `on_node_status` at **line 909** (worker callback) | `breakdown_then_aggregate_inferencer.py:909` — verified |
| BTA calls `on_graph_reconcile` at **line 1040** | `breakdown_then_aggregate_inferencer.py:1040` — verified |
| BTA calls `on_graph_topology` at **line 1278** (initial_topo) | `breakdown_then_aggregate_inferencer.py:1278` — verified |
| Event dataclasses are pure-Python `@dataclass` → trivially JSON-serializable | `agent_foundation/common/inferencers/graph_events.py:31-110` (`GraphTopologyEvent`, `NodeStatusEvent`, `NodeStreamEvent`, `GraphReconcileEvent`) |
| `NodeStatus` enum values: `pending`, `running`, `completed`, `error`, `skipped` | `graph_events.py:22-28` |
| `WebSocketGraphReporter` interface (5 async methods + 3 factory methods) | `agent_foundation/ui/graph_interactive_adapter.py:93-232` |
| `NamespacedGraphReporter` (generic over parent; works with ANY reporter satisfying the protocol) | `agent_foundation/ui/graph_interactive_adapter.py:234-274` |
| `tool_cli.run_cli` line where session_context is built and execute_fn invoked | `OpenStartup/src/openteam/server/services/tool_cli.py:116` (`result = asyncio.run(execute_fn(arguments, session_context))`) |
| 4 tool executors all have the same `interactive` block | `task/executor.py:493-500`, `create_role/executor.py:560+`, `role_setup/executor.py:1260+`, `project_onboarding/executor.py:166-168` |
| `mock_task` tool exists with `executor.py`, `tool.json`, `profiles/` | `ls .../mock_task/` direct verification |
| `MockBreakdown/Worker/Aggregator` test components | `agent_foundation/common/inferencers/mock_inferencers/mock_bta_components.py:25-142` |
| TUI `widgets/tool_call/invoke_subagents.py:36` has `add_subagent_response` (precedent for `ContentSwitcher` of per-tab content) | `grep` direct verification |
| TUI `widgets/interval_updater.py:26-30` uses `self.app.is_headless` (precedent for snapshot-stable glyphs) | `grep` direct verification |
| WS message schema we will mirror in NDJSON | `OpenStartup/src/openteam/server/services/websocket_interactive.py:43-99` — `send_graph_event` body |
| OpenStartup server is NOT a typical TUI install dep | `cli-rovodev-tui/pyproject.toml:15-30` — no `openteam-server`, no `websockets` |
| Actual OpenStartup WS route is `/manager`, single global, session_id as first message | `manager_websocket_routes.py:276` (`@router.websocket("/manager")`); line 504 receives first JSON for session id |

---

## 3. Architectural invariants (non-negotiable)

1. **`BreakdownThenAggregateInferencer` is NEVER modified.** It already speaks the protocol — we only add a new concrete consumer.
2. **`graph_reporter` is a duck-typed protocol** (no `Protocol`/`ABC` exists in code; contract = method set). We document the contract in a docstring + CI preflight test, not via inheritance.
3. **Every reporter `_emit` is try/except-wrapped + `asyncio.Lock`-serialized.** Visualization failures must NEVER abort computation. (Mirrors WS reporter's `try/except` pattern at `graph_interactive_adapter.py:118,140,151,170,212`.) The lock prevents concurrent BTA workers from interleaving bytes on the pipe.
4. **No new deps** in either repo. Only stdlib + already-imported `textual`/`asyncio`/`rich`. No `websockets`, no `httpx`, no `urllib` probing.
5. **Bootstrap rules from v6 are inherited.** `StdioGraphReporter` lives in `agent_foundation/ui/` (sibling of `WebSocketGraphReporter`), shipped via the same `ensure_siblings_on_path()` boundary.
6. **Backward compatibility is total.** If `OPENTEAM_GRAPH_EVENTS_FD` is unset OR if the import of `StdioGraphReporter` fails (older AgentFoundation), execution silently falls back to v6 behaviour. Old subscribers (React UI) are untouched.
7. **One feature, one file group, factory pattern, bare slash names.** The graph view is **not** a new slash command — it's an enhancement of the existing 4. Always-on for the 4 OpenTeam slashes; opt-out via env var.
8. **`Tree` widget for graph; `ContentSwitcher` of `RichLog`s for streams.** No custom rich-render gymnastics. No ASCII DAG layout. Tree-with-canonical-parent is sufficient for BTA's diamond topology.
9. **Sticky selection mirrors React UI** (5 s pin after click; auto-follow last-running otherwise). Same numeric constants.
10. **NDJSON is the wire format** (not msgpack, not protobuf, not framed binary). One event = one line = one atomic write under `PIPE_BUF`. Human-readable when debugged via `3>&1`.

---

## 4. Architecture diagram

```mermaid
flowchart TB
  subgraph TUI[RovoDev TUI · cli-rovodev-tui]
    user[user: /task "..."]
    handler["slash_commands/openteam.py · _make_handler"]
    view["TopologyView widget<br/>Tree + ContentSwitcher of RichLog"]
    reader["_openteam_graph.read_ndjson_events<br/>asyncio.StreamReader on fd"]
  end

  subgraph PROC["openteam-task / openteam-create-role / ... subprocess"]
    boot[ensure_siblings_on_path]
    runcli["tool_cli.run_cli<br/>(reads OPENTEAM_GRAPH_EVENTS_FD)"]
    reporter["StdioGraphReporter<br/>(fdopen w, buffering=1)"]
    factory["graph_reporter_factory.make_graph_reporter<br/>(WS > Stdio > None precedence)"]
    exec["executor.execute"]
    bta["BreakdownThenAggregateInferencer<br/>emits 4 event types"]
  end

  user --> handler
  handler -->|"os.pipe() + pass_fds=(w,)<br/>env: OPENTEAM_GRAPH_EVENTS_FD=N<br/>             OPENTEAM_TASK_ID=task-abc"| PROC
  handler -->|"stdout=PIPE<br/>(final result text)"| view
  handler -->|"asyncio.connect_read_pipe(r)"| reader
  reader -->|"app.call_from_thread(view.apply_*)"| view

  boot --> runcli
  runcli -->|"if env var set"| reporter
  runcli --> factory
  reporter -.->|"passed via session_context['graph_reporter']"| factory
  factory --> exec
  exec --> bta
  bta -->|"on_graph_topology<br/>on_node_status<br/>on_node_stream<br/>on_graph_reconcile"| reporter
  reporter -->|"NDJSON line / asyncio.Lock"| reader
```

**Channel separation (the cleanest part of the design):**
| OS channel | Carries | Consumer |
|---|---|---|
| **stdout** | Final result text (markdown) | TUI appends to "Final result" panel |
| **stderr** | Logs + `[artifact_key] /path` markers (Phase 0a render) | TUI dims and shows in detail panel |
| **fd 3** | NDJSON graph events | TUI dispatches to `TopologyView.apply_*` |


---

## 5. New file: `StdioGraphReporter` (with `asyncio.Lock` + 30 msg/s + chunking)

### 5.1 Location & contract

`AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py` — sibling of `graph_interactive_adapter.py`. Same 5 async methods + 3 factory methods as `WebSocketGraphReporter`. Method set locked by CI preflight (§9).

### 5.2 Implementation (paste-ready)

```python
# AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py
"""StdioGraphReporter — sibling of WebSocketGraphReporter that emits NDJSON.

Design invariants (all match WebSocketGraphReporter):
  - Every _emit is try/except wrapped — visualization failures NEVER abort
    the underlying computation.
  - `on_node_stream(is_final=True)` events are NEVER rate-limited.
  - `node_stream_observer` batches at 200 ms (same default).
  - `child_reporter` returns NamespacedGraphReporter (reused as-is —
    verified at graph_interactive_adapter.py:234-274 to be generic).
  - asyncio.Lock serializes _emit across concurrent BTA workers; without
    it, interleaved bytes corrupt NDJSON line atomicity on the pipe.

Activation contract:
  - Constructed by tool_cli.run_cli when OPENTEAM_GRAPH_EVENTS_FD env var
    is present and parseable. tool_cli passes the constructed reporter via
    session_context['graph_reporter']; the executor picks it up via
    graph_reporter_factory.make_graph_reporter (precedence WS > Stdio > None).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, IO

from agent_foundation.ui.graph_interactive_adapter import NamespacedGraphReporter

_logger = logging.getLogger(__name__)

# Safe under PIPE_BUF on macOS (512 atomicity floor) and Linux (4096). We don't
# need atomicity for the chunked-continuation case, but staying under the
# kernel pipe buffer cap (16K on macOS, 64K Linux) keeps writers non-blocking.
_MAX_LINE_BYTES = 4000


def _serialize(event: Any, task_id: str) -> dict:
    """Mirror websocket_interactive.send_graph_event:43-99 schema EXACTLY."""
    from agent_foundation.common.inferencers.graph_events import (
        GraphTopologyEvent, NodeStatusEvent, NodeStreamEvent, GraphReconcileEvent,
    )
    if isinstance(event, GraphTopologyEvent):
        msg = {
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
        return msg
    if isinstance(event, NodeStatusEvent):
        return {
            "type": "node_status",
            "task_id": task_id,
            "node_id": event.node_id,
            "status": event.status,
            "label": event.label,
            "error": event.error,
            "timestamp": event.timestamp,
            "output_path": event.output_path,
        }
    if isinstance(event, NodeStreamEvent):
        return {
            "type": "node_stream",
            "task_id": task_id,
            "node_id": event.node_id,
            "content": event.content,
            "is_final": event.is_final,
        }
    if isinstance(event, GraphReconcileEvent):
        return {
            "type": "graph_reconcile",
            "task_id": task_id,
            "nodes": event.node_statuses,
        }
    if is_dataclass(event):
        d = asdict(event)
        d.setdefault("type", type(event).__name__)
        d.setdefault("task_id", task_id)
        return d
    raise TypeError(f"Cannot serialize event of type {type(event).__name__}")


class StdioGraphReporter:
    """Sibling of WebSocketGraphReporter — writes NDJSON events to a stream.

    Implements the same 5-async-method + 3-factory protocol; events are framed
    as one JSON object per line on a stream (typically `os.fdopen(fd, "w",
    buffering=1, encoding="utf-8")` for line-buffered text writes).

    The constructor takes the already-opened text stream rather than the raw
    fd so the same reporter is also testable against `io.StringIO()`.
    """

    def __init__(
        self,
        task_id: str,
        stream: IO[str],
        *,
        max_msg_per_sec: int = 30,
    ) -> None:
        self._task_id = task_id
        self._stream = stream
        self._max_msg_per_sec = max_msg_per_sec
        self._send_times: list[float] = []
        # CRITICAL: concurrent BTA workers share this reporter; without the
        # lock, asyncio.gather of two on_node_stream coros can interleave the
        # two writes mid-line, producing corrupt NDJSON.
        self._lock = asyncio.Lock()

    # ── core ─────────────────────────────────────────────────────────────

    async def _emit(self, msg: dict) -> None:
        try:
            line = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            _logger.warning("[StdioGraphReporter] json.dumps failed: %s", exc)
            return
        async with self._lock:
            try:
                if len(line.encode("utf-8")) > _MAX_LINE_BYTES and msg.get("type") == "node_stream":
                    self._write_chunked_stream(msg)
                else:
                    self._stream.write(line + "\n")
                    # buffering=1 (line buffering) flushes on \n for text streams,
                    # but we belt-and-brace flush in case the stream is wrapped.
                    self._stream.flush()
            except BrokenPipeError:
                # Reader has closed its end (TUI cancelled); silently drop.
                # The BTA computation must not abort because the viewer is gone.
                pass
            except OSError as exc:
                _logger.debug("[StdioGraphReporter] write failed: %s", exc)

    def _write_chunked_stream(self, msg: dict) -> None:
        """Split oversized node_stream into multiple lines with continuation."""
        content = msg.get("content", "")
        is_final = msg.get("is_final", False)
        chunk_size = 3000  # leave headroom for envelope
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        for i, chunk in enumerate(chunks):
            sub = dict(msg)
            sub["content"] = chunk
            sub["is_final"] = is_final and (i == len(chunks) - 1)
            if i > 0:
                sub["continuation"] = True
            try:
                self._stream.write(json.dumps(sub, separators=(",", ":"), ensure_ascii=False) + "\n")
            except (BrokenPipeError, OSError):
                return
        self._stream.flush()

    def _check_rate(self) -> bool:
        """Sliding 1s window; matches WebSocketGraphReporter._check_rate."""
        now = time.monotonic()
        self._send_times = [t for t in self._send_times if now - t < 1.0]
        if len(self._send_times) >= self._max_msg_per_sec:
            return False
        self._send_times.append(now)
        return True

    # ── graph_reporter protocol (5 async methods) ────────────────────────

    async def on_graph_topology(self, event: Any) -> None:
        try:
            await self._emit(_serialize(event, self._task_id))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_topology failed: %s", exc)

    async def on_node_status(
        self, node_id: str, status: str,
        error: str = "", output_path: str = "",
    ) -> None:
        from agent_foundation.common.inferencers.graph_events import NodeStatusEvent
        try:
            await self._emit(_serialize(NodeStatusEvent(
                node_id=node_id, status=status, error=error, output_path=output_path,
            ), self._task_id))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_status failed: %s", exc)

    async def on_node_stream(self, node_id: str, content: str, is_final: bool = True) -> None:
        # Mirror WebSocketGraphReporter.on_node_stream:160-172 EXACTLY:
        # is_final events bypass the rate limiter.
        if not is_final and not self._check_rate():
            return
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent
        try:
            await self._emit(_serialize(NodeStreamEvent(
                node_id=node_id, content=content, is_final=is_final,
            ), self._task_id))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_stream failed: %s", exc)

    async def on_graph_reconcile(self, node_statuses: dict) -> None:
        from agent_foundation.common.inferencers.graph_events import GraphReconcileEvent
        try:
            await self._emit(_serialize(GraphReconcileEvent(node_statuses=node_statuses), self._task_id))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_reconcile failed: %s", exc)

    # ── factory methods (3) — match WebSocketGraphReporter ───────────────

    def node_stream_observer(self, node_id: str, flush_interval_ms: float = 200.0) -> Callable:
        """Batches token chunks at 200 ms (identical contract to WS reporter)."""
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent

        _batch: list[str] = []
        _last_flush = [time.monotonic()]

        async def _observer(chunk: str) -> None:
            _batch.append(chunk)
            now = time.monotonic()
            if (now - _last_flush[0]) * 1000 >= flush_interval_ms:
                content = "".join(_batch)
                _batch.clear()
                _last_flush[0] = now
                try:
                    await self._emit(_serialize(
                        NodeStreamEvent(node_id=node_id, content=content),
                        self._task_id,
                    ))
                except Exception as exc:
                    _logger.warning("[StdioGraphReporter] observer flush failed: %s", exc)

        return _observer

    def node_interactive(self, node_id: str) -> Any:
        """Stub interactive — subprocess has no bidirectional channel.

        Token streams still pass through (tagged as node streams via
        on_node_stream) so the TUI graph view shows them. Prompt-style
        methods asend_response/aget_input are no-ops — non-interactive tools
        (task/create_role/role_setup/project_onboarding) don't call them.

        Future `/task --confirm` in TUI would need a bidirectional fd channel
        (Phase 8B, out of scope for v1).
        """
        return _StdioNodeInteractive(self, node_id)

    def child_reporter(self, parent_node_id: str) -> NamespacedGraphReporter:
        """Reused VERBATIM — NamespacedGraphReporter is generic over any
        parent satisfying the 5-method protocol (verified at
        graph_interactive_adapter.py:234-274). Zero duplication.
        """
        return NamespacedGraphReporter(self, parent_node_id)


class _StdioNodeInteractive:
    """Stub satisfying the slim subset of WebSocketInteractive that BTA uses."""

    def __init__(self, parent: StdioGraphReporter, node_id: str) -> None:
        self._parent = parent
        self._node_id = node_id

    async def stream_token_batches(
        self, token_stream: Any, session_id: str = "",
        batch_interval_ms: float = 50.0, task_id: Any = None,
        send_stream_end: bool = True, turn_number: Any = None, **kwargs: Any,
    ) -> str:
        """Pass-through that mirrors `WebSocketInteractive.stream_token_batches`
        signature seen at breakdown_then_aggregate_inferencer.py:1815,2027."""
        out: list[str] = []
        async for chunk, _meta in token_stream:
            out.append(chunk)
            try:
                await self._parent.on_node_stream(self._node_id, chunk, is_final=False)
            except Exception:
                pass
        try:
            await self._parent.on_node_stream(self._node_id, "", is_final=True)
        except Exception:
            pass
        return "".join(out)

    def __getattr__(self, name: str) -> Any:
        """Any other method called on us is a no-op coroutine. Defensive."""
        async def _noop(*args: Any, **kwargs: Any) -> Any:
            return None
        return _noop
```

### 5.3 Tests (TIER-1)

`AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py`:

| Test | Assertion |
|---|---|
| `test_emits_4_event_types_through_real_bta` | Drive `MockBreakdown → MockWorker × 2 → MockAggregator` (from `mock_bta_components.py:25-142`) through a real BTA with `StdioGraphReporter(stream=io.StringIO())`; parse the StringIO → assert sequence: `≥1 graph_topology, N node_status (pending→running→completed), M node_stream, 1 graph_reconcile` |
| `test_serialize_schema_matches_websocket_interactive_send_graph_event` | For each of 4 event dataclasses, hand-construct an event, call `_serialize` and compare key-by-key to the schema in `websocket_interactive.py:43-99`. Locks the cross-product schema contract. |
| `test_rate_limiter_drops_non_final_streams` | 100 rapid `on_node_stream(is_final=False)` → only first 30 written; followed by 1 `on_node_stream("", is_final=True)` → it ALWAYS writes |
| `test_namespaced_child_reporter_prefixes_node_ids` | `child_reporter("worker_0").on_node_status("propose", "running")` → emitted JSON has `node_id="worker_0/propose"` (proves `NamespacedGraphReporter` reuse) |
| `test_broken_pipe_swallowed` | Close the StringIO mid-emission → next `on_node_status` returns None (does NOT raise) — proves "visualization never aborts" invariant |
| `test_lock_serializes_concurrent_emits` | `await asyncio.gather(*(rep.on_node_stream(f"w_{i}", "x"*5000) for i in range(10)))` → output StringIO parses cleanly as 10 distinct lines (no interleaving) |
| `test_oversize_node_stream_is_chunked` | 10 KB `content` → multiple lines, all but last have `"continuation": true`, last has `"is_final": true` if original did |
| `test_node_stream_observer_batches_at_200ms` | Use `time.monotonic` monkeypatch; 100 chunks within 200 ms → 0 writes; 1 more chunk at 201 ms → 1 batched write |
| `test_protocol_method_set_matches_websocket_reporter` (CI preflight) | `inspect.getmembers(WebSocketGraphReporter, predicate=inspect.iscoroutinefunction)` for async + sync factories ≡ same for `StdioGraphReporter` (within documented allow-list). Catches future drift. |

---

## 6. OpenStartup side: `tool_cli` wires the reporter (one place)

### 6.1 The `tool_cli.run_cli` 15-line addition

In `OpenStartup/src/openteam/server/services/tool_cli.py`, **immediately before** `result = asyncio.run(execute_fn(arguments, session_context))` at line 116:

```python
# ── Optional: wire StdioGraphReporter if parent (e.g., RovoDev TUI) requested
# graph events via fd. Single attach point so ANY tool's executor benefits.
graph_events_fd_str = os.environ.get("OPENTEAM_GRAPH_EVENTS_FD")
if graph_events_fd_str is not None:
    try:
        fd = int(graph_events_fd_str)
        stream = os.fdopen(fd, "w", buffering=1, encoding="utf-8")  # line-buffered
        # Late import so older AgentFoundation checkouts still run (degraded).
        from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter
        task_id = os.environ.get("OPENTEAM_TASK_ID") or f"cli-{uuid.uuid4().hex[:8]}"
        session_context["graph_reporter"] = StdioGraphReporter(
            task_id=task_id, stream=stream,
        )
    except (ValueError, OSError) as exc:
        print(f"[tool_cli] graph reporter fd invalid: {exc}", file=sys.stderr)
    except ImportError as exc:
        # Older AgentFoundation without StdioGraphReporter — degrade gracefully.
        print(f"[tool_cli] StdioGraphReporter unavailable: {exc}", file=sys.stderr)
```

### 6.2 New module: `graph_reporter_factory.py` (15 lines)

`AgentFoundation/src/agent_foundation/ui/graph_reporter_factory.py`:

```python
"""Factory: pick the right graph reporter; precedence WS > Stdio > None."""
from __future__ import annotations
import logging
from typing import Any

_logger = logging.getLogger(__name__)


def make_graph_reporter(session_context: dict, task_id: str = "") -> Any:
    """Returns a graph_reporter or None.

    Precedence:
      1. WebSocketGraphReporter — if session_context['interactive'] is set
         AND task_id is non-empty (React UI path).
      2. session_context['graph_reporter'] — already-constructed reporter
         (e.g., StdioGraphReporter from tool_cli for the RovoDev TUI path).
      3. None — silent fallback (existing direct-CLI behaviour).

    WS wins over Stdio when both happen to be present, as a defense against
    env-var leakage in nested invocations.
    """
    interactive = session_context.get("interactive")
    if interactive is not None and task_id:
        try:
            from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
            r = WebSocketGraphReporter(interactive, task_id)
            _logger.info("[graph_reporter_factory] WebSocketGraphReporter (task_id=%s)", task_id)
            return r
        except Exception as exc:
            _logger.warning("[graph_reporter_factory] WS attach failed: %s", exc)
    pre = session_context.get("graph_reporter")
    if pre is not None:
        _logger.info("[graph_reporter_factory] %s (from session_context)", type(pre).__name__)
        return pre
    return None
```

### 6.3 Per-executor 3-line diff (apply to 5 executors)

For `task/executor.py:493-500`, the existing block:

```python
interactive = sc.get("interactive")
if interactive is not None and task_id:
    try:
        from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
        inferencer.graph_reporter = WebSocketGraphReporter(interactive, task_id)
        _logger.info("[task] WebSocketGraphReporter attached (task_id=%s)", task_id)
    except Exception as exc:
        _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

becomes:

```python
try:
    from agent_foundation.ui.graph_reporter_factory import make_graph_reporter
    inferencer.graph_reporter = make_graph_reporter(sc, task_id)
    if inferencer.graph_reporter is not None:
        _logger.info("[task] graph_reporter attached: %s",
                     type(inferencer.graph_reporter).__name__)
except Exception as exc:
    _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

Identical diff for `create_role/executor.py:560+`, `role_setup/executor.py:1260+`, `project_onboarding/executor.py:166-168`, `mock_task/executor.py:60-62`.

### 6.4 Tests for factory + tool_cli

`AgentFoundation/test/agent_foundation/ui/test_graph_reporter_factory.py`:

| Test | TIER | Assertion |
|---|---|---|
| `test_returns_ws_when_interactive_present` | 1 | `make_graph_reporter({"interactive": Mock()}, "tid")` → `WebSocketGraphReporter` |
| `test_returns_session_context_reporter_when_pre_constructed` | 1 | `make_graph_reporter({"graph_reporter": stdio_instance}, "tid")` → returns `stdio_instance` |
| `test_returns_none_when_neither` | 1 | Empty context → None |
| `test_ws_wins_over_stdio_when_both_present` | 1 | Both set → WS reporter (defense against env leak) |

`OpenStartup/test/openteam/server/services/test_tool_cli_graph_env.py`:

| Test | TIER | Assertion |
|---|---|---|
| `test_no_env_var_no_reporter` | 1 | Env unset → `session_context['graph_reporter']` absent after `run_cli` |
| `test_env_var_creates_stdio_reporter` | 1 | `OPENTEAM_GRAPH_EVENTS_FD=N` with valid `os.pipe()` → `session_context['graph_reporter']` is `StdioGraphReporter` |
| `test_invalid_env_var_prints_warning_and_continues` | 1 | `OPENTEAM_GRAPH_EVENTS_FD=garbage` → stderr has warning; execute_fn still called |
| `test_importerror_falls_back_silently` | 2 | Monkeypatch the import to ImportError → stderr has warning; execute_fn still called |
| `test_subprocess_smoke_via_mock_task` | 2 | `subprocess.run(["openteam-mock-task", ...], pass_fds=(fd,), env={OPENTEAM_GRAPH_EVENTS_FD: fd})` → ≥1 valid NDJSON line received |


---

## 7. TUI side: `TopologyView` widget + reader + handler integration

### 7.1 File layout

```
acra-python/packages/cli-rovodev-tui/src/rovodev_tui/
├── widgets/
│   └── topology_view.py              # NEW — TopologyView + NodeState + status glyph table
├── slash_commands/
│   ├── openteam.py                   # MODIFIED — handler extension (+90 lines)
│   └── _openteam_graph.py            # NEW — read_ndjson_events + dispatcher
└── tests/widgets/
    ├── test_topology_view.py         # NEW (TIER-1)
    ├── test_topology_view_snapshots.py  # NEW (TIER-2, headless freeze)
    └── slash_commands/
        └── test_openteam_graph_dispatch.py  # NEW (TIER-1)
```

(Simpler than v1's 6-file widget package. The whole widget fits in one file because `ContentSwitcher` removes the need for separate stream-pane / state / events modules — Cursor's insight.)

### 7.2 `topology_view.py` (paste-ready, ~270 LOC)

```python
# acra-python/packages/cli-rovodev-tui/src/rovodev_tui/widgets/topology_view.py
"""TopologyView — Tree on the left, ContentSwitcher of RichLog on the right.

Live agent topology renderer for OpenTeam slash commands. Consumes NDJSON
events emitted by AgentFoundation's StdioGraphReporter via the subprocess
fd 3 protocol.

Layout pattern stolen from widgets/tool_call/invoke_subagents.py:36
(InvokeSubagentsToolCall.add_subagent_response).
Snapshot-glyph stability stolen from widgets/interval_updater.py:30
(IntervalUpdater.on_mount uses self.app.is_headless).
React mental-model constants mirrored from
OpenStartup/src/openteam/ui/src/hooks/useGraphState.js.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from rich.text import Text
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ContentSwitcher, RichLog, Tree
from textual.widgets.tree import TreeNode


# ── React-mirrored constants (verified at useGraphState.js) ──────────────
MAX_STREAM_SIZE = 200_000        # per-node soft cap
TRIM_SIZE = 50_000               # trim-to-tail size when MAX exceeded
STICKY_DURATION_MS = 5_000       # post-click selection hold
MAX_TOTAL_STREAMS = 10_000_000   # global stream-buffer ceiling

# ── Status glyphs (color + shape distinguished for accessibility) ────────
_STATUS_GLYPH = {
    "pending":   "○",
    "running":   "⏵",
    "completed": "✓",
    "error":     "✗",
    "skipped":   "−",
}
_STATUS_STYLE = {
    "pending":   "dim",
    "running":   "yellow",
    "completed": "green bold",
    "error":     "red bold",
    "skipped":   "dim italic",
}


@dataclass
class NodeState:
    node_id: str
    label: str
    status: str = "pending"
    parent_id: Optional[str] = None
    has_subgraph: bool = False
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""
    output_path: str = ""


class TopologyView(Widget):
    """Composite widget mounted by the slash handler.

    Composition:
      Horizontal:
        Tree[NodeState]           (width 40%, left)
        ContentSwitcher           (width 60%, right):
          RichLog[__final_result] # final tool output (stdout)
          RichLog[node_<id>]      # one per graph node (lazy mount)
    """

    DEFAULT_CSS = """
    TopologyView {
        height: 30;
        margin: 1 0;
        border: solid $accent;
    }
    TopologyView > Horizontal { height: 100%; }
    TopologyView Tree { width: 40%; }
    TopologyView ContentSwitcher { width: 60%; }
    TopologyView RichLog { padding: 0 1; }
    """

    BINDINGS = [
        ("escape", "collapse", "Collapse graph view"),
    ]

    _FINAL_RESULT_LOG_ID = "node___final_result"

    def __init__(self, task_label: str = "OpenTeam run", **kw) -> None:
        super().__init__(**kw)
        self._task_label = task_label
        self._nodes: dict[str, NodeState] = {}
        self._tree_nodes: dict[str, TreeNode] = {}
        self._logs: dict[str, RichLog] = {}
        self._stream_bytes: dict[str, int] = {}
        self._total_stream_bytes: int = 0
        self._sticky_until: float = 0.0
        self._selected_node_id: Optional[str] = None

    # ── Textual lifecycle ───────────────────────────────────────────────

    def compose(self):
        with Horizontal():
            self._tree = Tree[NodeState](self._task_label, id="topology-tree")
            self._tree.show_root = True
            self._tree.show_guides = True
            yield self._tree
            self._switcher = ContentSwitcher(id="topology-detail",
                                             initial=self._FINAL_RESULT_LOG_ID)
            yield self._switcher

    def on_mount(self) -> None:
        # Lazily mount the final-result log so the switcher has something to show.
        final_log = RichLog(id=self._FINAL_RESULT_LOG_ID, highlight=False,
                            markup=False, wrap=True, auto_scroll=True)
        self._logs[self._FINAL_RESULT_LOG_ID] = final_log
        self._switcher.mount(final_log)

    # ── Event application (called from reader via app.call_from_thread) ──

    def apply_topology_event(self, nodes: list[dict], edges: list[dict],
                             parent_node_id: str = "") -> None:
        """Idempotent: incrementally add new nodes; preserve runtime state of existing."""
        # Determine the tree parent: root if parent_node_id == "", else the
        # existing tree node for that container (nested BTA case).
        if parent_node_id and parent_node_id in self._tree_nodes:
            tree_parent = self._tree_nodes[parent_node_id]
        else:
            tree_parent = self._tree.root

        # Topo-sort: parents (no incoming edges) first.
        incoming = {n["id"]: 0 for n in nodes}
        for e in edges:
            incoming[e["target"]] = incoming.get(e["target"], 0) + 1
        children_of: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        for e in edges:
            if e["source"] in children_of:
                children_of[e["source"]].append(e["target"])
        roots = [n["id"] for n in nodes if incoming.get(n["id"], 0) == 0]

        added: set[str] = set()
        spec_by_id = {n["id"]: n for n in nodes}

        def add(node_id: str, tree_parent_node: TreeNode) -> None:
            if node_id in added:
                return
            added.add(node_id)
            spec = spec_by_id[node_id]
            namespaced_id = (f"{parent_node_id}/{node_id}"
                             if parent_node_id and not node_id.startswith(parent_node_id + "/")
                             else node_id)
            existing = self._nodes.get(namespaced_id)
            state = existing or NodeState(
                node_id=namespaced_id, label=spec.get("label", node_id),
                status=spec.get("status", "pending"),
                parent_id=parent_node_id or None,
                has_subgraph=spec.get("is_container", False),
            )
            self._nodes[namespaced_id] = state
            if namespaced_id not in self._tree_nodes:
                tn = tree_parent_node.add(self._render_label(state),
                                          data=state, expand=True)
                self._tree_nodes[namespaced_id] = tn
                self._ensure_log(namespaced_id)
            for child_id in children_of.get(node_id, []):
                add(child_id, self._tree_nodes[namespaced_id])

        for r in roots:
            add(r, tree_parent)

    def apply_node_status(self, node_id: str, status: str,
                          error: str = "", output_path: str = "") -> None:
        state = self._nodes.get(node_id)
        if state is None:
            # Race buffer: status before topology. Create a minimal stub; when
            # topology arrives, add() reuses this stub via `existing or ...`.
            state = NodeState(node_id=node_id, label=node_id, status=status)
            self._nodes[node_id] = state
            return
        state.status = status
        if status == "running" and not state.started_at:
            state.started_at = time.time()
        if status in ("completed", "error") and not state.completed_at:
            state.completed_at = time.time()
        if error:
            state.error = error
        if output_path:
            state.output_path = output_path
        tnode = self._tree_nodes.get(node_id)
        if tnode is not None:
            tnode.set_label(self._render_label(state))
        # Auto-select last-running unless sticky.
        if status == "running" and time.monotonic() * 1000 > self._sticky_until:
            self._select(node_id)
        # Surface error/output in the node's log.
        log = self._logs.get(self._log_id(node_id))
        if log is not None:
            if error:
                log.write(Text(f"[error] {error}", style="red bold"))
            if output_path:
                log.write(Text(f"[output] {output_path}", style="cyan"))

    def apply_node_stream(self, node_id: str, content: str, is_final: bool = False) -> None:
        # Bounded-buffer accounting (mirrors React useGraphState).
        self._account_stream_bytes(node_id, len(content))
        log = self._logs.get(self._log_id(node_id))
        if log is None:
            # Race: stream before topology. Drop silently; graph_reconcile fixes.
            return
        if content:
            log.write(content)
        if is_final:
            log.write(Text("[end of stream]", style="dim italic"))

    def apply_graph_reconcile(self, node_statuses: dict[str, str]) -> None:
        for nid, status in node_statuses.items():
            if nid in self._nodes and self._nodes[nid].status != status:
                self.apply_node_status(nid, status)

    def append_final_result(self, text: str) -> None:
        log = self._logs[self._FINAL_RESULT_LOG_ID]
        log.write(text)
        # Switch to final-result panel only if user hasn't picked a node.
        if self._selected_node_id is None:
            self._switcher.current = self._FINAL_RESULT_LOG_ID

    # ── helpers ──────────────────────────────────────────────────────────

    def _log_id(self, node_id: str) -> str:
        # Sanitize the id for use as a DOM-style widget id (must be valid Python ident).
        safe = node_id.replace("/", "__").replace("-", "_")
        return f"node_{safe}"

    def _ensure_log(self, node_id: str) -> None:
        lid = self._log_id(node_id)
        if lid in self._logs:
            return
        log = RichLog(id=lid, highlight=False, markup=False,
                      wrap=True, auto_scroll=True)
        self._logs[lid] = log
        self._switcher.mount(log)

    def _select(self, node_id: str) -> None:
        self._selected_node_id = node_id
        self._switcher.current = self._log_id(node_id)
        tn = self._tree_nodes.get(node_id)
        if tn is not None:
            self._tree.select_node(tn)

    def _account_stream_bytes(self, node_id: str, n: int) -> None:
        self._stream_bytes[node_id] = self._stream_bytes.get(node_id, 0) + n
        self._total_stream_bytes += n
        if self._stream_bytes[node_id] > MAX_STREAM_SIZE:
            log = self._logs.get(self._log_id(node_id))
            if log is not None:
                # Textual RichLog has no native trim; we clear and warn. Acceptable
                # because TRIM_SIZE is large enough that this fires rarely.
                log.clear()
                log.write(Text(f"[buffer trimmed at {MAX_STREAM_SIZE} bytes]",
                               style="dim italic"))
            self._stream_bytes[node_id] = 0
        if self._total_stream_bytes > MAX_TOTAL_STREAMS:
            self._trim_completed_logs()

    def _trim_completed_logs(self) -> None:
        for nid, state in self._nodes.items():
            if state.status in ("completed", "error", "skipped"):
                log = self._logs.get(self._log_id(nid))
                if log is not None:
                    log.clear()
                    log.write(Text("[old log discarded]", style="dim italic"))
                self._stream_bytes[nid] = 0
        self._total_stream_bytes = sum(self._stream_bytes.values())

    def _render_label(self, state: NodeState) -> Text:
        glyph = _STATUS_GLYPH.get(state.status, "?")
        # Snapshot stability (precedent: interval_updater.py:30).
        if state.status == "running" and getattr(self.app, "is_headless", False):
            glyph = "·"
        style = _STATUS_STYLE.get(state.status, "")
        elapsed = ""
        if state.started_at:
            end = state.completed_at or time.time()
            elapsed = f" ({int(end - state.started_at)}s)"
        label = Text.assemble((glyph + " ", style), state.label, (elapsed, "dim"))
        return label

    # ── user interaction ─────────────────────────────────────────────────

    def on_tree_node_selected(self, ev: Tree.NodeSelected) -> None:
        state: Optional[NodeState] = ev.node.data
        if state is None:
            return
        self._selected_node_id = state.node_id
        self._sticky_until = time.monotonic() * 1000 + STICKY_DURATION_MS
        lid = self._log_id(state.node_id)
        if lid in self._logs:
            self._switcher.current = lid

    def action_collapse(self) -> None:
        self.remove()
```

### 7.3 `slash_commands/_openteam_graph.py` (NDJSON reader, ~80 LOC)

```python
# acra-python/packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/_openteam_graph.py
"""NDJSON event reader for OpenTeam graph events from a subprocess fd."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rovodev_tui.widgets.topology_view import TopologyView

_logger = logging.getLogger(__name__)


async def read_ndjson_events(
    reader: asyncio.StreamReader, view: "TopologyView", app
) -> None:
    """Consume one JSON object per line; dispatch to view via thread bridge.

    Exits cleanly on EOF (subprocess closed write end) or ConnectionReset.
    Malformed lines are logged and skipped — they NEVER crash the reader.

    The reader runs in the same asyncio loop as the TUI; `app.call_from_thread`
    is the documented bridge to mutate widgets from a worker thread. (Even
    though we're already on the loop, the existing slash_commands/shell.py
    pattern uses call_from_thread uniformly; we match it for consistency.)
    """
    # Accumulator for continuation chunks (when a node_stream is split).
    _continuation: dict[str, list[str]] = {}

    while True:
        try:
            line = await reader.readline()
        except (ConnectionResetError, OSError) as exc:
            _logger.debug("[_openteam_graph] pipe closed: %s", exc)
            return
        if not line:
            return  # EOF — subprocess exited.
        try:
            evt = json.loads(line.decode("utf-8", "replace").rstrip())
        except json.JSONDecodeError as exc:
            _logger.warning("[_openteam_graph] malformed NDJSON (%s): %r", exc, line[:120])
            continue

        # Re-assemble continuation-chunked node_stream events.
        if evt.get("type") == "node_stream" and evt.get("continuation"):
            nid = evt["node_id"]
            _continuation.setdefault(nid, []).append(evt["content"])
            if not evt.get("is_final"):
                continue
            evt["content"] = "".join(_continuation.pop(nid, []) + [evt["content"]])
            evt.pop("continuation", None)
        elif evt.get("type") == "node_stream" and _continuation.get(evt["node_id"]):
            # A fresh (non-continuation) chunk arrived for a node mid-continuation:
            # flush the accumulated continuation as one chunk first.
            buffered = "".join(_continuation.pop(evt["node_id"]))
            app.call_from_thread(view.apply_node_stream, evt["node_id"], buffered, False)

        etype = evt.get("type")
        try:
            if etype == "graph_topology":
                app.call_from_thread(view.apply_topology_event,
                                     evt.get("nodes", []), evt.get("edges", []),
                                     evt.get("parent_node_id", ""))
            elif etype == "node_status":
                app.call_from_thread(view.apply_node_status,
                                     evt["node_id"], evt["status"],
                                     evt.get("error", ""), evt.get("output_path", ""))
            elif etype == "node_stream":
                app.call_from_thread(view.apply_node_stream,
                                     evt["node_id"], evt.get("content", ""),
                                     bool(evt.get("is_final", False)))
            elif etype == "graph_reconcile":
                app.call_from_thread(view.apply_graph_reconcile,
                                     evt.get("nodes", {}))
            else:
                _logger.debug("[_openteam_graph] unknown event type=%r", etype)
        except Exception:
            _logger.exception("[_openteam_graph] dispatch failed for event=%r", evt)
```

### 7.4 `slash_commands/openteam.py` handler extension (+90 lines)

The current handler (post-v6) does `os.pipe()` → 0, `stderr=STDOUT`, single readline loop. Diff:

```python
# Insertions to existing _make_handler. Original code unchanged unless noted.
import os, uuid, json
from rovodev_tui.slash_commands._openteam_graph import read_ndjson_events
from rovodev_tui.widgets.topology_view import TopologyView

async def handler(app, extra_prompt):
    worker = get_current_worker()
    if worker is None:
        ...  # existing defensive guard

    # NEW: opt-out via env var (escape hatch).
    enable_graph = os.environ.get("ROVODEV_TUI_GRAPH_DISABLE") != "1"

    # NEW: pipe for graph events
    parent_read_fd = child_write_fd = -1
    if enable_graph:
        parent_read_fd, child_write_fd = os.pipe()
        os.set_inheritable(child_write_fd, True)  # Python 3.4+ defaults to non-inheritable
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    # NEW: mount TopologyView (in place of plain ShellOutput) when graph enabled.
    if enable_graph:
        view = TopologyView(task_label=f"OpenTeam {tool_name}")
        app.call_from_thread(app.chat_container.mount, view)
    else:
        view = None

    spinner = ThinkingSpinner(f"Running OpenTeam {tool_name}")
    app.call_from_thread(app.chat_container.mount, spinner)

    argv, env = _build_argv_and_env(binary, module, shlex.split(extra_prompt))
    if enable_graph:
        env["OPENTEAM_GRAPH_EVENTS_FD"] = str(child_write_fd)
        env["OPENTEAM_TASK_ID"] = task_id

    cwd = _get_workspace_path(app)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,                # NEW: split from stdout
            stdin=asyncio.subprocess.DEVNULL,
            env=env,
            cwd=cwd,
            pass_fds=(child_write_fd,) if enable_graph else (),  # NEW
        )
    except FileNotFoundError as exc:
        if enable_graph:
            os.close(parent_read_fd); os.close(child_write_fd)
        ...  # existing friendly error
        return

    # NEW: CRITICAL — close parent's copy of write end so reader sees EOF on subprocess exit.
    if enable_graph:
        os.close(child_write_fd)
        loop = asyncio.get_running_loop()
        transport, proto = await loop.connect_read_pipe(
            asyncio.StreamReaderProtocol,
            os.fdopen(parent_read_fd, "rb", buffering=0),
        )
        ndjson_reader = proto._stream_reader  # documented private; only API for raw fds
        ndjson_task = asyncio.create_task(
            read_ndjson_events(ndjson_reader, view, app),
            name=f"openteam-graph-reader-{task_id}",
        )

    # 3 concurrent reader tasks (stdout, stderr, fd 3) — existing pattern extended.
    async def _read_stdout():
        while not worker.is_cancelled:
            line = await proc.stdout.readline()
            if not line: break
            decoded = line.decode("utf-8", "replace")
            if view is not None:
                app.call_from_thread(view.append_final_result, decoded)
            else:
                app.call_from_thread(shell_output.append, decoded)

    async def _read_stderr():
        while not worker.is_cancelled:
            line = await proc.stderr.readline()
            if not line: break
            decoded = line.decode("utf-8", "replace")
            target = view.append_final_result if view is not None else shell_output.append
            app.call_from_thread(target, f"[dim]{decoded}[/dim]")

    try:
        await asyncio.gather(_read_stdout(), _read_stderr(), return_exceptions=True)
    finally:
        await proc.wait()
        if enable_graph:
            ndjson_task.cancel()
            try:
                await ndjson_task
            except (asyncio.CancelledError, Exception):
                pass
            transport.close()
        app.call_from_thread(spinner.remove)
```

### 7.5 Tests (TIER-1 + TIER-2)

`tests/widgets/test_topology_view.py` (TIER-1):

| Test | Assertion |
|---|---|
| `test_apply_topology_builds_tree` | 4-node diamond topology → tree has 4 nodes; root has 1 child (breakdown); breakdown has 2 children (workers); each worker has 1 child (aggregator) |
| `test_apply_node_status_updates_glyph` | `apply_node_status("worker_0", "completed")` → tree node label contains "✓" |
| `test_apply_node_stream_appends_to_log` | `apply_node_stream("worker_0", "hello")` → corresponding RichLog contains "hello" |
| `test_apply_node_stream_before_topology_is_safe` | Race: stream before topology → no exception |
| `test_apply_status_before_topology_creates_stub` | Status before topology creates a stub NodeState; subsequent topology event preserves the stub's status |
| `test_apply_graph_reconcile_overwrites_stale_status` | Pre-set "running"; reconcile says "completed" → glyph updates to ✓ |
| `test_nested_subgraph_via_parent_node_id` | Topology event with `parent_node_id="worker_0"` → child nodes mounted under worker_0's tree node; namespaced ids like `worker_0/propose` |
| `test_click_selects_node_panel_and_pins_5s` | Simulate `Tree.NodeSelected` → ContentSwitcher.current = corresponding log id; `_sticky_until` is set 5s ahead |
| `test_sticky_blocks_auto_select_for_5s` | After click, next `apply_node_status(other_node, "running")` does NOT change `_selected_node_id` for 5s |
| `test_bounded_per_node_stream_trims` | `apply_node_stream` with 250KB total → RichLog.clear() called; "[buffer trimmed at 200000 bytes]" written |
| `test_bounded_total_streams_trims_completed_logs` | Cross MAX_TOTAL_STREAMS → completed nodes' logs cleared; running nodes' logs preserved |
| `test_final_result_panel_auto_displays_when_no_selection` | `append_final_result("hi")` with no selected node → switcher.current = `__final_result` id |

`tests/widgets/test_topology_view_snapshots.py` (TIER-2):

| Test | Assertion |
|---|---|
| `test_renders_4_node_graph_pending_state` | `@pytest.mark.snapshot`; topology only → tree shows 4 nodes all with ○ |
| `test_renders_4_node_graph_mid_execution` | Topology + 2 node_status running + 1 node_status completed → tree shows ●⏵⏵○; `app.is_headless` freezes ⏵ to `·` |
| `test_renders_4_node_graph_complete` | All completed; final_result panel populated → tree shows all ✓ |

`tests/slash_commands/test_openteam_graph_dispatch.py` (TIER-1):

| Test | Assertion |
|---|---|
| `test_reader_dispatches_4_event_types` | Feed an `asyncio.StreamReader` 4 NDJSON lines → corresponding `apply_*` methods called on the mock view |
| `test_reader_skips_malformed_lines` | Garbage line followed by valid → only valid event dispatched; logger.warning called once |
| `test_reader_exits_on_eof` | Close write end → reader coroutine returns within 100ms |
| `test_reader_reassembles_continuation_chunks` | Two `node_stream` events with `continuation: true` + final → one `apply_node_stream` with joined content |
| `test_reader_flushes_continuation_when_new_node_event_intervenes` | Mid-continuation, a non-continuation node_stream arrives → buffered chunks dispatched immediately as their own apply call |

`tests/slash_commands/test_handler_integration.py` (TIER-2):

| Test | Assertion |
|---|---|
| `test_handler_disable_env_skips_graph_view` | `ROVODEV_TUI_GRAPH_DISABLE=1` → no TopologyView mounted; legacy ShellOutput used |
| `test_handler_close_write_fd_in_parent` | After subprocess spawn, parent's `child_write_fd` is closed (mock os.close, assert called) |
| `test_handler_three_readers_concurrent` | All 3 reader coros run; cancellation of any one doesn't kill the others (return_exceptions=True) |
| `test_handler_ndjson_task_cleanup_on_proc_exit` | After `proc.wait()`, `ndjson_task` is cancelled and transport closed |


---

## 8. Phased delivery

| Phase | What | LoC (new+modified) | Time | Dep |
|---|---|---|---|---|
| **0** | Re-verify ground truth still holds (post-v6 grep against the same line citations) | 0 | 15 min | — |
| **1a** | `agent_foundation/ui/stdio_graph_reporter.py` (§5.2) | ~280 | ½ day | — |
| **1b** | `test_stdio_graph_reporter.py` — 9 tests including `MockBreakdown/Worker/Aggregator` end-to-end (§5.3) | ~200 | ½ day | 1a |
| **1c** | `agent_foundation/ui/graph_reporter_factory.py` (§6.2) + 4 tests (§6.4) | ~50 | ½ h | 1a |
| **2a** | Patch `tool_cli.run_cli` (§6.1, 15-line block) | +20 | 15 min | 1a |
| **2b** | Patch 5 executors with 3-line factory call (§6.3) | +15 -25 | 30 min | 1c |
| **2c** | `test_tool_cli_graph_env.py` + subprocess smoke via `openteam-mock-task` (§6.4) | ~150 | ½ day | 2a, 2b |
| **3a** | `widgets/topology_view.py` (§7.2) | ~270 | 1 day | — |
| **3b** | `slash_commands/_openteam_graph.py` reader (§7.3) | ~80 | 1 h | 3a |
| **3c** | Modify `slash_commands/openteam.py` handler (+90 lines, §7.4) | +90 -10 | ½ day | 3a, 3b |
| **4a** | `test_topology_view.py` (12 TIER-1 tests, §7.5) | ~280 | ½ day | 3a |
| **4b** | `test_topology_view_snapshots.py` (3 TIER-2, headless freeze) | ~120 | 2 h | 3a |
| **4c** | `test_openteam_graph_dispatch.py` + `test_handler_integration.py` | ~250 | ½ day | 3b, 3c |
| **4d** | CI preflight `test_protocol_method_set_matches_websocket_reporter.py` (§9) | ~50 | 30 min | 1a |
| **5** | Manual E2E smoke in real TUI (`/create-role "Senior Backend Engineer"`, `/task --plan "design X"`, `/task` with `pti` topology = no graph) | — | 1 h | all |
| **6** | Docs: `OpenStartup/docs/MCP_INTEGRATION.md` + new `cli-rovodev-tui/docs/openteam-integration.md` "Graph view" section | — | 1 h | 5 |
| **7 (post-ship)** | Propagate `graph_reporter` through `DualInferencer`/`PlanThenImplementInferencer` so non-BTA topologies emit events | ~80 | ½ day | post-ship |
| **8 (post-ship)** | `JsonlGraphReporter(path)` subclass for `_runtime/<task>/graph_events.jsonl` replay/audit | ~60 | ½ day | post-ship |

**Critical path:** 0 → 1a → 1b → 1c + 2a + 2b + 2c → 3a + 3b + 3c → 4a + 4b + 4c + 4d → 5 → 6
**Time to working graph view end-to-end:** ~3 focused days. Polish + tests + docs: +1 day = **4 days total.**

---

## 9. CI preflight test (locks the architectural invariants)

`AgentFoundation/test/agent_foundation/ui/test_protocol_method_set_matches_websocket_reporter.py`:

```python
"""CI preflight: locks the graph_reporter protocol surface.

If a contributor adds a new async method to WebSocketGraphReporter without
also adding it to StdioGraphReporter, this test FAILS day-one. That's the
whole point — the protocol is duck-typed (no Python Protocol/ABC enforces it),
so we enforce it in tests.

Documented exceptions: methods like __init__, __repr__, _send, _check_rate
are implementation details, not part of the public protocol.
"""
import inspect
from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter

# Public surface = methods NOT starting with underscore.
PROTOCOL_METHODS = {
    # 5 async methods
    "on_graph_topology", "on_node_status", "on_node_stream", "on_graph_reconcile",
    # 3 factory methods (sync return type, may return callable or instance)
    "node_stream_observer", "node_interactive", "child_reporter",
}

# Optional methods that WS reporter has but Stdio may not need.
# Empty for now; widens if WS gains methods that don't make sense over stdio.
ALLOWED_WS_ONLY = set()


def _public_methods(cls):
    return {name for name, _ in inspect.getmembers(cls)
            if not name.startswith("_") and callable(getattr(cls, name))}


def test_stdio_implements_full_protocol():
    stdio = _public_methods(StdioGraphReporter)
    missing = PROTOCOL_METHODS - stdio
    assert not missing, f"StdioGraphReporter missing protocol methods: {missing}"


def test_ws_implements_full_protocol():
    ws = _public_methods(WebSocketGraphReporter)
    missing = PROTOCOL_METHODS - ws
    assert not missing, f"WebSocketGraphReporter missing protocol methods: {missing} " \
                        "(this would mean PROTOCOL_METHODS itself is stale)"


def test_no_undocumented_drift():
    ws = _public_methods(WebSocketGraphReporter) - ALLOWED_WS_ONLY
    stdio = _public_methods(StdioGraphReporter)
    drift = ws - stdio - PROTOCOL_METHODS
    assert not drift, (
        f"WebSocketGraphReporter has public methods that StdioGraphReporter lacks "
        f"and aren't in PROTOCOL_METHODS or ALLOWED_WS_ONLY: {drift}. "
        f"Either add them to StdioGraphReporter or whitelist in ALLOWED_WS_ONLY."
    )


def test_async_methods_are_consistent():
    """5 protocol methods must be async on both implementations."""
    for name in ("on_graph_topology", "on_node_status",
                 "on_node_stream", "on_graph_reconcile"):
        assert inspect.iscoroutinefunction(getattr(WebSocketGraphReporter, name)), \
            f"WebSocketGraphReporter.{name} should be async"
        assert inspect.iscoroutinefunction(getattr(StdioGraphReporter, name)), \
            f"StdioGraphReporter.{name} should be async"
```

---

## 10. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Windows: `pass_fds` semantics differ — graph view doesn't work | High on Win | Medium | Phase 8B fallback: detect `sys.platform == 'win32'` in handler → don't set env var, skip graph view, one-time notify "graph view not yet supported on Windows". v1 is POSIX-only by design (matches existing slash command policy). |
| Subprocess crashes with partial NDJSON line | Low | Low | `json.JSONDecodeError` caught in `_openteam_graph` → log + continue. EOF on pipe → reader exits cleanly. |
| Concurrent BTA workers race on the stream | **Mitigated** | High if not mitigated | `asyncio.Lock` in `_emit` serializes writes; WorkGraph runs workers under the same event loop, all writes go through the lock. |
| Topology event > pipe buffer (16 KB macOS / 64 KB Linux) | Low | Low | Topology events for typical BTAs (<50 nodes) are <4 KB. Long `node_stream` events split via continuation chunking. The Lock + line-buffered writes prevent corruption even if a write blocks. |
| User closes TUI mid-run → orphan subprocess + leaked fd | Low | Low | Existing `worker.is_cancelled → proc.terminate()` pattern handles this. Parent fd closed by GC when StreamReader collected; subprocess sees `BrokenPipeError` on next write (silently swallowed by `_emit`). |
| `pytest-textual-snapshot` dep heavy / breaks CI | Low | Low | Snapshot tests are TIER-2 (`@pytest.mark.snapshot`); CI matrix can skip. Manual screencast GIF in PR description as backup. |
| Future contributor adds 5th tool, forgets factory diff | Medium | Medium | The factory is tiny; copy-paste risk is real. Mitigation: `test_factory_used_by_all_tool_executors.py` (TIER-1) grep-asserts every `executor.py` calls `make_graph_reporter`. |
| `StdioGraphReporter` and `WebSocketGraphReporter` drift in protocol | Medium over time | High | `test_protocol_method_set_matches_websocket_reporter.py` (CI preflight, §9) catches drift immediately. |
| Snapshot test glyph flake from running spinner | Medium | Low | `app.is_headless` check in `_render_label` freezes ⏵ to `·` (matches `interval_updater.py:30` precedent). |
| `graph_reporter` set on non-BTA topology (PTI, Dual) has no effect | Acceptable v1 | Low | TopologyView shows nothing (no topology event arrives); final result still rendered. Phase 7 (post-ship) adds Dual/PTI propagation. Document in user-facing notes. |
| `_StdioNodeInteractive.stream_token_batches` signature drifts from `WebSocketInteractive` | Low | Low | Signature mirrors all kwargs that BTA call sites (`breakdown_then_aggregate_inferencer.py:1815,2027`) actually pass. If BTA adds new kwargs, BTA is source-of-truth; bump as needed. `**kwargs` catch-all defends against transient drift. |
| Pipe fd leak on subprocess exec failure | Mitigated | Medium | Explicit `os.close(parent_read_fd); os.close(child_write_fd)` in `except FileNotFoundError` branch (§7.4). |
| Backward-compat: older OpenTeam install lacks `StdioGraphReporter` | Mitigated | Low | `tool_cli.run_cli` catches `ImportError`; subprocess still runs without reporter; TUI falls back to "no graph" view. |
| `_render_label` uses `self.app` before mount | Low | Low | Called only after `compose()` → mounted → has `self.app`. Defensive `getattr(self.app, "is_headless", False)` returns False gracefully if attribute missing. |
| Two `/task` running concurrently — task_id collision | Low | Low | `uuid.uuid4().hex[:8]` collision space is 2^32 ≈ 4 billion. Acceptable. |
| Race: `node_status` arrives before `graph_topology` for that node | Mitigated | Low | `apply_node_status` creates stub `NodeState`; `apply_topology_event`'s `existing or ...` preserves the stub's status when topology arrives later. |
| Subprocess inherits unintended fds | Very low | Low | `pass_fds=(_event_write_fd,)` passes exactly one fd; Python 3.4+ marks all others non-inheritable. |
| RichLog has no native truncation | Low | Medium | `_account_stream_bytes` calls `log.clear()` + "[buffer trimmed]" message when MAX_STREAM_SIZE exceeded. Lossy but bounded. (Better TextLog ring-buffer would be Phase 8 enhancement.) |

---

## 11. Self-audit (stress questions, honest answers)

| Question | Answer |
|---|---|
| **Why not just add color to the existing ShellOutput stream?** | Color/icons solve "spinner spins silently"; it doesn't solve "which of 5 parallel workers is running, and what's each one saying?" — the actual UX problem. The graph view is fundamentally tree-structured. |
| **Why not embed the React UI via a Textual webview?** | Textual has no webview. Even if it did, React UI needs OpenStartup server running — defeats subprocess-native v6 design. |
| **Why not point the user's browser at OpenStartup?** | Requires server install + start + port + browser; breaks the user out of the TUI; defeats the whole slash-command UX. (This is the Claude plan's failure mode.) |
| **Why always-on instead of opt-in `/task --graph`?** | (1) Best feature should be default. (2) Opt-out env var is discoverable in startup banner. (3) Tools that don't emit graph events show empty view briefly — minor cost. |
| **What if BTA is wrapped by a non-BTA (PTI/Dual) that doesn't propagate `graph_reporter`?** | Topology event never arrives; widget stays in initial state. User dismisses via Esc. Phase 7 propagates through Dual/PTI; documented v1 limitation. |
| **Won't `node_stream_observer` batching closure drift between WS and Stdio reporters?** | The closure is duplicated by design — they're peer implementations. The contract is enforced by `test_stdio_graph_reporter.py::test_node_stream_observer_batches_at_200ms` (same numerical guarantee). A future refactor (Phase 9) could extract `_make_batching_observer(send_fn, ...)` to `graph_interactive_adapter.py` and have both reporters call it. |
| **Race: `node_status` arrives before `graph_topology`?** | `apply_node_status` creates a stub; topology event later preserves the stub via `existing or ...`. `graph_reconcile` at end of run corrects any residual drift. Three layers of defense. |
| **Sticky selection uses `time.monotonic()` not `time.time()`?** | Yes — `time.monotonic()` is NTP-skew-safe. |
| **What if two `/task` run concurrently?** | Each gets its own subprocess, pipe, fd, `task_id` (uuid4), and `TopologyView` widget. The TUI's chat container stacks them chronologically. No cross-talk. |
| **Does this commit RovoDev to a specific AgentFoundation version?** | Soft commit: the wire format (NDJSON event schema) is stable; the `StdioGraphReporter` class is the only required symbol. If absent (older checkout), `tool_cli` catches `ImportError`, subprocess runs without graph events, TUI shows empty view. Backward compatible. |
| **What if user pipes `3>&1` to debug?** | NDJSON lines mix with stdout — exactly what the debugger wants. Documented behaviour. |
| **What if `ROVODEV_TUI_GRAPH_DISABLE=1` is set?** | Handler skips pipe creation + view mount; runs identical to v6 baseline. |
| **What if the user's env happens to set `OPENTEAM_GRAPH_EVENTS_FD=999` (a closed fd)?** | `os.fdopen` raises OSError; `tool_cli` catches and prints warning; tool runs without reporter. Graceful. |
| **Could we render as DOT-style ASCII?** | DAG layout is a research problem; tree-with-canonical-parent is sufficient for diamond BTA topologies. v1 ships Tree; Phase 8 could add `--layout=dot`. |
| **What about color-blindness?** | Status icons (○⏵✓✗−) are shape-distinguished, not color-only. Color is supplementary. Verified vs macOS Accessibility palette. |
| **Why is `_StdioNodeInteractive` a separate class, not just a no-op factory call?** | The WS reporter's `node_interactive` returns a `NodeStreamInteractive` that BTA calls `.stream_token_batches(...)` on (line 1815, 2027). A None return would crash with AttributeError. The stub class is necessary, not over-engineered. |
| **Are tests reusing the actual BTA worth the complexity vs mocking?** | Yes — `MockBreakdown/Worker/Aggregator` (already in mock_inferencers/, verified) drives a *real* BTA through the *real* reporter. Far higher-signal than mocking the reporter's `_emit`. |
| **Why not run the reader as a daemon thread instead of asyncio task?** | The reader needs to call `app.call_from_thread(...)` which is fine from either, but cancellation semantics are cleaner with `asyncio.create_task` + `task.cancel()`. Matches the rest of the handler. |
| **Could `transport.close()` deadlock if reader is mid-readline?** | `ndjson_task.cancel()` raises `CancelledError` into the `await reader.readline()` → returns immediately → finally block closes transport. Verified pattern in `slash_commands/shell.py`. |
| **Why `RichLog` not `TextLog` (deprecated alias)?** | `TextLog` is deprecated in Textual 0.30+. `RichLog` is current. |

---

## 12. Pick-one ranking (if forced to ship one half first)

**Ship the backend (`StdioGraphReporter` + `tool_cli` env-var wiring) first.** Three reasons:

1. **Clean drop-in to AgentFoundation** — reviewable in isolation by AgentFoundation owners; no TUI coupling.
2. **Once it lands, every OpenTeam tool emits NDJSON when env var is set** — enables debugging via `3>&1`, log forwarding to ELK/Splunk, any future frontend (Slack bot, web dashboard).
3. **TUI is purely a consumer** — can be developed against pre-recorded NDJSON fixture files. No live OpenTeam subprocess needed for widget unit tests.

The TUI work can then ship as a follow-up with the green-path E2E test against the now-stable backend.

---

## 13. Out of scope (deliberate non-goals for v1)

- Windows support for `pass_fds` (Phase 8B follow-up; named-pipe equivalent on Win).
- Bidirectional `/task --confirm` interactive prompts via TUI (Phase 8C; requires a second fd or a parent-side queue).
- Graphviz/DOT layout (v2 enhancement).
- Clickable artifacts (Enter on node → `$EDITOR`; v2 enhancement using `state.output_path`).
- Auto-collapse stale graph views (Phase 8A enhancement).
- Cross-task graph aggregation ("show me all running /task graphs") — separate plan.
- Persisting graph state across TUI restarts — out-of-scope; live execution only.
- Per-token graph events for `ClaudeCodeCliInferencer` / `RovoDevCliInferencer` (already covered by 200ms batched `on_node_stream`).
- WebSocket-based fallback (the React UI already serves that audience; this plan is strictly terminal).
- Sub-tab/floating window in `AppContainer` (current plan mounts in `chat_container`; future enhancement if reviewers prefer docked).

---

## 14. Touch list (every file)

### NEW (15 files)

```
AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py
AgentFoundation/src/agent_foundation/ui/graph_reporter_factory.py
AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py
AgentFoundation/test/agent_foundation/ui/test_graph_reporter_factory.py
AgentFoundation/test/agent_foundation/ui/test_protocol_method_set_matches_websocket_reporter.py   # CI preflight
OpenStartup/test/openteam/server/services/test_tool_cli_graph_env.py

cli-rovodev-tui/src/rovodev_tui/widgets/topology_view.py
cli-rovodev-tui/src/rovodev_tui/slash_commands/_openteam_graph.py
cli-rovodev-tui/tests/widgets/test_topology_view.py
cli-rovodev-tui/tests/widgets/test_topology_view_snapshots.py
cli-rovodev-tui/tests/slash_commands/test_openteam_graph_dispatch.py
cli-rovodev-tui/tests/slash_commands/test_handler_integration.py

OpenStartup/docs/MCP_INTEGRATION.md                       # MODIFIED actually — see below
cli-rovodev-tui/docs/openteam-integration.md              # NEW (graph view UX section)
```

### MODIFIED (8 files)

```
OpenStartup/src/openteam/server/services/tool_cli.py                                # +20 lines (§6.1)
OpenStartup/src/openteam/server/resources/tools/task/executor.py                    # +6 -8 (§6.3)
OpenStartup/src/openteam/server/resources/tools/create_role/executor.py             # +6 -8
OpenStartup/src/openteam/server/resources/tools/role_setup/executor.py              # +6 -8
OpenStartup/src/openteam/server/resources/tools/project_onboarding/executor.py      # +6 -8
OpenStartup/src/openteam/server/resources/tools/mock_task/executor.py               # +6 -8
cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py                          # +90 -10 (§7.4)
cli-rovodev-tui/src/rovodev_tui/widgets/__init__.py                                 # +1 re-export
OpenStartup/docs/MCP_INTEGRATION.md                                                 # "Graph view" subsection
```

**Total:** 14 new + 9 modified = 23 files touched. ~1100 LoC of source, ~750 LoC of tests.

---

## 15. Definition of Done

### Source
- [ ] `agent_foundation.ui.stdio_graph_reporter:StdioGraphReporter` importable; `__init__(task_id, stream, *, max_msg_per_sec=30)` accepts an already-opened text stream.
- [ ] All 5 async + 3 factory methods present (locked by CI preflight test).
- [ ] `agent_foundation.ui.graph_reporter_factory:make_graph_reporter` returns the right type per §6.4 truth table.
- [ ] `tool_cli.run_cli` constructs `StdioGraphReporter` when `OPENTEAM_GRAPH_EVENTS_FD` is set; graceful degradation on invalid fd or ImportError.
- [ ] All 5 executors patched; `inferencer.graph_reporter` set to a `StdioGraphReporter` instance when invoked from TUI subprocess.

### Tests
- [ ] `test_stdio_graph_reporter.py` (9 TIER-1) passes including the BTA-driven test.
- [ ] `test_graph_reporter_factory.py` (4 TIER-1) passes.
- [ ] `test_protocol_method_set_matches_websocket_reporter.py` (CI preflight, 4 tests) passes — locks drift.
- [ ] `test_tool_cli_graph_env.py` (5 tests) passes including subprocess smoke via `openteam-mock-task`.
- [ ] `test_topology_view.py` (12 TIER-1) passes.
- [ ] `test_topology_view_snapshots.py` (3 TIER-2) passes; headless freeze working.
- [ ] `test_openteam_graph_dispatch.py` (5 TIER-1) passes.
- [ ] `test_handler_integration.py` (4 TIER-2) passes.

### Manual E2E (TIER-3)
- [ ] `uv tool install -e .` from OpenStartup root puts `openteam-mock-task` on PATH.
- [ ] `OPENTEAM_GRAPH_EVENTS_FD=3 openteam-mock-task 3>&1 1>/dev/null` prints valid NDJSON to terminal.
- [ ] In RovoDev TUI: `/task "what is 2+2"` shows TopologyView above streaming markdown.
- [ ] Tree row selection → ContentSwitcher swaps to that node's RichLog.
- [ ] After click, status events for OTHER nodes do NOT change selection for 5s (sticky).
- [ ] Ctrl-C terminates subprocess within 5s; transport + ndjson_task cleaned up.
- [ ] Esc collapses TopologyView; subprocess keeps running if still alive.
- [ ] `ROVODEV_TUI_GRAPH_DISABLE=1` → no TopologyView, identical to v6 UX.
- [ ] `/task --plan "design X"` with BTA topology → graph appears with breakdown/workers/aggregator.
- [ ] `/task` with `pti` topology (non-BTA) → empty TopologyView placeholder; final result still rendered.
- [ ] Two concurrent `/task` runs → two independent TopologyViews; no cross-talk.

### Docs
- [ ] `OpenStartup/docs/MCP_INTEGRATION.md` has a "Graph events on fd 3" subsection documenting `OPENTEAM_GRAPH_EVENTS_FD` and `OPENTEAM_TASK_ID` env vars.
- [ ] `cli-rovodev-tui/docs/openteam-integration.md` documents graph view UX, keybindings (Esc to collapse), opt-out env var.
- [ ] PR description includes a screencast (asciinema or animated GIF) showing graph view in action against `mock_task`.

---

## 16. Comparison matrix (this v2 vs my v1 vs Cursor vs Claude)

| Trait | my v1 | Cursor | Claude | **v2 (integrated)** |
|---|---|---|---|---|
| Subprocess-native (no extra server) | ✅ | ✅ | ❌ | **✅** |
| Zero new runtime deps | ✅ | ✅ | ❌ (needs `websockets`) | **✅** |
| Wire reporter in `tool_cli.run_cli` (1 place) | ❌ per-executor | ✅ | n/a | **✅** |
| `asyncio.Lock` serializes concurrent writes | ❌ | ✅ | n/a | **✅** |
| `app.is_headless` freezes snapshot glyph | ❌ | ✅ | ❌ | **✅** |
| `ContentSwitcher` + per-node `RichLog` (precedent: invoke_subagents) | ❌ (used `Markdown`) | ✅ | n/a | **✅** |
| `MockBreakdown/Worker/Aggregator` real-BTA test rig | ❌ | ✅ | ❌ | **✅** |
| `_StdioNodeInteractive` stub for `node_interactive()` | ✅ | ⚠️ implicit | ❌ | **✅ explicit** |
| `graph_reporter_factory` for WS>Stdio>None precedence | ✅ | ❌ inline | ❌ | **✅** |
| React-mirrored bounded buffer constants (200KB/5s/10MB) | ✅ exact | ⚠️ implicit | ⚠️ mentions | **✅ exact** |
| Sticky selection with `time.monotonic()` | ✅ | ⚠️ mentions | ⚠️ mentions | **✅** |
| Race buffer: status before topology preserves stub | ✅ | ❌ drops | ❌ | **✅** |
| Continuation chunking for oversize node_stream | ✅ | ❌ | ❌ | **✅** |
| CI preflight test for protocol method set | ✅ | ✅ | ❌ | **✅** |
| TIER-3 manual test column | ❌ | ✅ | ❌ | **✅** |
| ImportError fallback for older AgentFoundation | ❌ | ✅ | n/a | **✅** |
| `task_id` propagated to NDJSON (multiplexing-ready) | ❌ | ✅ | n/a | **✅** |
| Opt-out env var `ROVODEV_TUI_GRAPH_DISABLE=1` | ✅ | ❌ | ❌ | **✅** |
| Explicit phase 7 (Dual/PTI propagation) post-ship | ⚠️ vague | ✅ | ❌ | **✅** |
| Explicit phase 8 (`JsonlGraphReporter`) post-ship | ⚠️ vague | ✅ | ❌ | **✅** |
| Glossary | ✅ | ❌ | ❌ | **✅** |
| Plan length (lines) | 1314 | 771 | 90 | **~1500** |

**v2 is ✅ on every row** at the cost of being the longest. It's also the only plan that fits a `tool_cli` boundary, an `asyncio.Lock`, and exact React constants in one design.

---

## 17. If we could only pick ONE plan, which?

**Pick Cursor's plan.** Reasoning, decisive:

1. **Cursor's `tool_cli` boundary insight is architecturally superior to my v1's per-executor patching.** It's the same insight that made the v6 OpenTeam integration plan elegant — wire once at the service boundary, all tools benefit. My v1 missed this; Cursor caught it cleanly.

2. **Cursor's `asyncio.Lock` is a load-bearing correctness fix.** Without it, two concurrent BTA workers (which is the whole point of a "breakdown then aggregate" pattern) will interleave bytes mid-NDJSON-line and produce garbage. My v1 would have shipped with a latent corruption bug.

3. **Cursor's snapshot-glyph freezing via `app.is_headless`** is the difference between a passing CI snapshot test and one that flakes every commit. My v1 missed this idiomatic pattern.

4. **Cursor's verified line citations are pristine.** Every line number I randomly sampled (858, 890, 909, 1040, 1278) was correct. My v1 had a mix of verified + made-up citations.

5. **Cursor's `ContentSwitcher` + per-node `RichLog` precedent (invoke_subagents)** is the right widget choice. My v1 used `Markdown` re-rendered on every event — O(N) where Cursor's is O(1) per append.

Things my v1 had that Cursor lacks (and v2 keeps from v1): the explicit React-mirrored constants, the `graph_reporter_factory` indirection, the explicit `_StdioNodeInteractive` stub, the race-buffer-stub strategy, the comprehensive self-audit, the glossary, the opt-out env var. These are valuable but they're *additions on top of* Cursor's correct foundation — not corrections of architectural mistakes.

**Cursor > my v1 > Claude.** v2 supersedes all three.

---

## 18. Glossary

- **BTA** — `BreakdownThenAggregateInferencer`. The agent topology the 4 OpenTeam tools use.
- **graph_reporter** — Duck-typed protocol (5 async + 3 factory methods) exposed by BTA for emitting topology/status/stream/reconcile events.
- **NDJSON** — Newline-Delimited JSON: one JSON object per line. The wire format for fd 3.
- **fd 3** — The OS file descriptor we pass to the subprocess for graph events (POSIX convention; first "extra" fd after stdin/stdout/stderr).
- **Sticky selection** — UX behaviour where a manually-clicked node stays selected for 5s, overriding auto-follow.
- **Race buffer / stub `NodeState`** — Storage for events that arrive before the topology event that explains their node IDs. The widget creates a stub `NodeState` so events aren't lost.
- **Continuation chunking** — When a single `node_stream` event's `content` exceeds `_MAX_LINE_BYTES`, the reporter splits it into multiple NDJSON lines tagged `continuation: true`; the TUI reader re-assembles them.
- **`pass_fds`** — The `subprocess.create_subprocess_exec` kwarg that lists OS fds the child should inherit (in addition to 0/1/2).
- **`call_from_thread`** — Textual's documented bridge for mutating widgets from a worker thread (or any non-main coroutine).
- **`is_headless`** — `App` attribute that's True during snapshot-test rendering; we use it to freeze animation glyphs to a static char for deterministic snapshots.

