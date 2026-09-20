# RovoDev TUI — OpenTeam Graph Visualization (v1 PLAN)

**Status:** Proposal · ready for review
**Created:** 2026-05-17
**Author:** rovodev (follow-up to `openteam-rovodev-integration-INTEGRATED-v6`)
**Supersedes:** N/A (first plan)
**Scope:** Add a real-time agent topology graph visualization + per-node streaming pane to the RovoDev TUI when invoking OpenTeam tools via slash commands (`/task`, `/create-role`, `/role-setup`, `/project-onboarding`).

---

## 0. TL;DR

Today, when a user types `/task "..."` in the RovoDev TUI, the subprocess runs **silently** for 5–30 minutes (only a spinner spins), then dumps the full result at the end. Meanwhile, the OpenTeam React UI shows a live graph (BreakdownThenAggregate workers, status colors, per-node token streaming) for the *exact same execution path*.

The asymmetry is purely transport-layer: OpenTeam's `BreakdownThenAggregateInferencer` already emits structured events via the `graph_reporter` **protocol** (`on_graph_topology`, `on_node_status`, `on_node_stream`, `on_graph_reconcile`). The React UI's `WebSocketGraphReporter` is one of two existing implementations. We add a **third implementation, `StdioGraphReporter`**, that emits the same events as **NDJSON on stderr**. The TUI's slash handler parses the NDJSON stream and renders a `Tree`-based graph widget plus a `Markdown`-based per-node stream pane — both updated live via Textual's thread-safe `post_message()`.

**Zero changes** to `BreakdownThenAggregateInferencer`. **Zero new deps** on either side. **One narrow change** to each tool's `executor.py` (5 lines: detect TUI mode → instantiate `StdioGraphReporter`). The TUI work is one new file + one helper widget set.

**Effort:** ~3 days of focused work (1 day OpenStartup, 1.5 days TUI, 0.5 day polish + tests).

---

## 1. Verified ground truth (the load-bearing facts)

Every claim below has been verified by direct file inspection in this session:

| Fact | Evidence |
|---|---|
| `BreakdownThenAggregateInferencer` declares `graph_reporter: Optional[Any] = attrib(default=None, kw_only=True)` and only emits events when non-None | `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/breakdown_then_aggregate_inferencer.py:509` (`# Protocol: must implement on_graph_topology(event), on_node_status(node_id, status, error).`) |
| `graph_reporter` protocol surface (4 async methods + 3 factory methods) | `WebSocketGraphReporter` at `AgentFoundation/src/agent_foundation/ui/graph_interactive_adapter.py:93-232` is the canonical implementation. Methods: `on_graph_topology(event)`, `on_node_status(node_id, status, error="", output_path="")`, `on_node_stream(node_id, content, is_final=True)`, `on_graph_reconcile(node_statuses)`, plus `node_stream_observer(node_id, flush_interval_ms=200.0)`, `node_interactive(node_id)`, `child_reporter(parent_node_id)`. |
| Event dataclasses are pure-Python `@dataclass` (NOT Pydantic) → trivially JSON-serializable | `AgentFoundation/src/agent_foundation/common/inferencers/graph_events.py:31-110` defines `GraphTopologyEvent`, `NodeStatusEvent`, `NodeStreamEvent`, `GraphReconcileEvent`. All fields are `str`/`float`/`list[dict]`/`dict`. |
| `NodeStatus` enum values: `pending`, `running`, `completed`, `error`, `skipped` | `graph_events.py:22-28` |
| Slash subprocess **currently has `graph_reporter = None`** | `executor.py:493-498` in each tool — `WebSocketGraphReporter` only attached if `session_context.get("interactive")` is non-None. `build_session_context()` in the TUI handler path returns an empty dict. |
| TUI handler today uses `stderr=STDOUT` (merged) | `slash_commands/openteam.py:117` verified |
| `ShellOutput` extends `Markdown` and supports incremental `.append()` | `widgets/shell_output.py:3-13` |
| Textual 8.2.3 is installed; provides `Tree`, `Markdown`, `Static`, `RichLog`, `VerticalScroll`, `Horizontal`, `Vertical`, `ContentSwitcher`, `TabbedContent`, message-passing model | `cli-rovodev-tui/pyproject.toml:25` |
| `app.call_from_thread(...)` is the documented thread→main bridge | Used throughout existing slash commands (e.g., `shell.py`, `openteam.py:109,110,150`) |
| WS message schema we will mirror in NDJSON | `OpenStartup/src/openteam/server/services/websocket_interactive.py:43-110` — `send_graph_event` body builds `{"type": "graph_topology" \| "node_status" \| "node_stream" \| "graph_reconcile", "task_id": ..., ...}` |
| React reference for sticky selection, RAF batching, sub-graph splicing, bounded stream buffers | `OpenStartup/src/openteam/ui/src/hooks/useGraphState.js` — `MAX_STREAM_SIZE=200_000`, `TRIM_SIZE=50_000`, `STICKY_DURATION_MS=5_000`, `MAX_TOTAL_STREAMS=10_000_000` |
| `NamespacedGraphReporter` prefixes node IDs with `parent_node_id/` for nested BTAs | `graph_interactive_adapter.py:234-274` |
| All 4 tool executors (`task`, `create_role`, `role_setup`, `project_onboarding`) already have the wiring boilerplate | grep results: `task/executor.py:493-498`, `create_role/executor.py:560+`, `role_setup/executor.py:1260+`, `project_onboarding/executor.py:166-168` |
| Existing `mock_task` tool with `__mock_input__` exists for cheap testing | `OpenStartup/src/openteam/server/resources/tools/mock_task/` — already shows the wiring pattern at lines 60-62 |

---

## 2. Architectural invariants (non-negotiable)

1. **`BreakdownThenAggregateInferencer` is NEVER modified.** It already speaks the protocol — we only add a new concrete implementation. Any plan that touches BTA is wrong.
2. **`graph_reporter` is a duck-typed protocol** — no `Protocol` base class exists in code; the contract is the *method set*. We document the contract in a docstring + tests, not via inheritance.
3. **Reporter sends MUST be try/except wrapped** — every existing implementation does this (`graph_interactive_adapter.py:118,140,151,170,212`). Reason: visualization failures must never abort computation. We honor the same rule.
4. **No new deps** in either repo. Only stdlib + already-imported textual/asyncio. (FastMCP, websockets, rich are all already present.)
5. **Bootstrap rules from v6 are inherited.** `StdioGraphReporter` lives in `agent_foundation/ui/` (sibling of `WebSocketGraphReporter`), so it ships via the same `ensure_siblings_on_path()` boundary; the 4 cli.py shims already call bootstrap (v6 Phase 0d).
6. **Backward compatibility is total.** If the subprocess detects no `ROVODEV_TUI_GRAPH_FD` env var (or fails to attach), execution falls back to the v6 silent-then-dump UX. Old subscribers (React UI) are untouched.
7. **One feature, one file, factory pattern, bare slash names.** Following v6 §2 invariant 3. The graph view is *not* a new slash command — it's an enhancement of the existing 4. No `/graph` command. No `/openteam-graph`. The widget is **always-on for the 4 OpenTeam slashes** (opt-out via env var).
8. **Tree widget for graph; Markdown widget for stream.** No custom rich-render gymnastics. No ASCII art. The Tree's hierarchical layout naturally encodes the `parent/child/grandchild` namespacing the BTA emits.
9. **Sticky selection mirrors the React UI's contract exactly** (5 s pin after manual click; auto-follow last-running otherwise). Same numeric constants. Same semantics. Cross-product UX consistency.

---

## 3. The big picture (architecture diagram)

```
                  ┌── OpenTeam tool subprocess ────────────────────────┐
                  │   openteam-task / openteam-create-role / …          │
                  │                                                     │
   /task "…" ────►│   ensure_siblings_on_path()                        │
                  │   tool_cli.run_cli() → executor.execute(args, ctx) │
                  │     ┌─────────────────────────────────────────┐    │
                  │     │ build_session_context()                 │    │
                  │     │   + (NEW) attach StdioGraphReporter if  │    │
                  │     │     ROVODEV_TUI_GRAPH_FD env present    │    │
                  │     │   → ctx["graph_reporter"] = <reporter>  │    │
                  │     └────────────────┬────────────────────────┘    │
                  │     bta.graph_reporter = ctx["graph_reporter"]     │
                  │     await bta.ainfer(...)                          │
                  │       ├── on_graph_topology(GraphTopologyEvent)    │
                  │       ├── on_node_status(node_id, "running", …)    │ ─┐
                  │       ├── on_node_stream(node_id, "tok", final=F)  │  │
                  │       ├── on_node_stream(node_id, "ens", final=T)  │  │
                  │       ├── on_node_status(node_id, "completed",…)  │  │
                  │       └── on_graph_reconcile(node_statuses)       │  │
                  │                                                    │  │
                  │   ToolExecutionResult → tool_cli prints text →     │  │
                  │   stdout (markdown, as today)                      │  │
                  └────────────────────────┬───────────────────────────┘  │
                                           │                               │
                  stdout (markdown) ◄──────┘                               │
                                                                           │
                  fd=3 (NDJSON events) ◄────────────────────────────────── ┘
                  one JSON object per line, e.g.:
                  {"type":"graph_topology","nodes":[…],"edges":[…]}
                  {"type":"node_status","node_id":"worker_0","status":"running"}
                  {"type":"node_stream","node_id":"worker_0","content":"Let me …"}
                                           │
                                           ▼
                  ┌── RovoDev TUI (cli-rovodev-tui) ────────────────────┐
                  │   slash_commands/openteam.py                        │
                  │                                                     │
                  │   create_subprocess_exec(                           │
                  │     argv,                                           │
                  │     stdout=PIPE,        # markdown                  │
                  │     stderr=PIPE,        # ALL stderr (logs+events)  │
                  │     pass_fds=(3,),      # graph events channel      │
                  │     env=ROVODEV_TUI_GRAPH_FD=3, …                   │
                  │   )                                                 │
                  │                                                     │
                  │   ┌── 3 concurrent readers, each in get_event_loop()│
                  │   │  ▸ stdout reader → ShellOutput.append           │
                  │   │  ▸ stderr reader → ShellOutput.append (dim)     │
                  │   │  ▸ fd=3 reader   → GraphEventMessage → post     │
                  │   └─────────────────────────────────────────────────┘
                  │                                                     │
                  │   Custom widgets (widgets/openteam_graph/*.py):     │
                  │   ┌─ OpenteamGraphView (Container) ───────────────┐ │
                  │   │ ┌─ TopologyTree (Tree[NodeInfo]) ────────────┐│ │
                  │   │ │ ▸ root                                     ││ │
                  │   │ │   ├─ [●] breakdown    (done, 12s)          ││ │
                  │   │ │   ├─ [⏵] worker_0    (running, 8s)         ││ │ ◄── selected (yellow)
                  │   │ │   │   └─ [○] propose  (pending)            ││ │
                  │   │ │   ├─ [⏵] worker_1    (running, 5s)         ││ │
                  │   │ │   ├─ [○] worker_2    (pending)             ││ │
                  │   │ │   └─ [○] aggregator  (pending)             ││ │
                  │   │ └────────────────────────────────────────────┘│ │
                  │   │ ┌─ StreamPane (Markdown) ────────────────────┐│ │
                  │   │ │ ## worker_0 — running (8s)                 ││ │
                  │   │ │ Let me analyze the requirements…           ││ │
                  │   │ │ ▸ Step 1: identify the core capabilities…  ││ │
                  │   │ │ (200 KB rolling buffer, auto-scroll)       ││ │
                  │   │ └────────────────────────────────────────────┘│ │
                  │   └───────────────────────────────────────────────┘│
                  │                                                     │
                  │   On stream end (proc.wait): widget remains visible │
                  │   so the user can browse final state. Esc collapses.│
                  └─────────────────────────────────────────────────────┘
```


---

## 4. Transport decision (NDJSON on fd=3) — and why not the alternatives

### Three alternatives evaluated

| Transport | Pros | Cons | Verdict |
|---|---|---|---|
| **(A) NDJSON on a dedicated fd (fd=3)** | Zero new deps. Synchronous file I/O. Naturally separated from stdout markdown AND stderr logs. Survives merging if a debug user pipes (`2>&1`). Trivially mockable in tests. Cross-platform (POSIX `pass_fds`; on Windows Python `subprocess` supports `pass_fds` only via `STARTUPINFO` and is more involved — see Phase 7 risks). Atomic per line. Loss-on-overflow bounded by 200 ms batching. | Requires `pass_fds=(3,)` on the parent + opening fd=3 explicitly in the child. Windows requires a port-based fallback (Phase 7B). | ✅ **Chosen** |
| (B) NDJSON on stderr (merged with stderr logs) | Even simpler than (A). | stderr is already used by `tool_cli.py:125-131` for `[artifact_key] /path` markers. Mixing event JSON with human stderr makes parsing brittle (we'd need a sentinel prefix; future libraries logging to stderr could collide). | ❌ Rejected — fragile separation |
| (C) Embedded WebSocket (re-use `WebSocketGraphReporter` as-is) | Zero changes to AgentFoundation. | The TUI is PyInstaller-frozen; embedding `websockets` server requires shipping the lib, finding a free port (and surviving "address already in use"), startup/teardown race, firewall prompts on macOS. Solves a problem we don't have. | ❌ Rejected — over-engineering |
| (D) Unix domain socket / Windows named pipe | Bidirectional (we don't need that). | Per-task socket lifecycle, platform divergence, cleanup on crash. | ❌ Rejected — complexity > benefit |

### Why fd=3 specifically (not fd=4 or arbitrary)

- POSIX convention: fd=0 (stdin), fd=1 (stdout), fd=2 (stderr), **fd=3 is the canonical first "extra" fd**. Tools like `git`, `gpg`, `ssh-askpass` use fd=3 for sideband channels.
- The env var `ROVODEV_TUI_GRAPH_FD=3` tells the child reporter which fd to write to. The reporter falls back to no-op if the env var is absent or the fd is closed — exactly the graceful-degradation path.
- The env var is **opt-in from the TUI side**: only set when the slash handler is the entry point. If the user runs `openteam-task` from a plain shell, no `ROVODEV_TUI_GRAPH_FD` → silent → identical to today's CLI UX. Zero impact on existing users.

### Why NDJSON (not msgpack / protobuf / binary framing)

- Human-readable when piped to a log file (`2>&1` or `3>&1`); reviewers can diff event streams in PR descriptions.
- One line = one event = one atomic write (`sys.stdout.write(json.dumps(...) + "\n")` + `flush=True`). Partial-line reads are impossible because line buffering is OS-guaranteed for `os.write()` when payload < `PIPE_BUF` (4096 on Linux, 512 on macOS — both well above our event sizes).
- Events are bounded: typical `node_stream` is ~200 chars after 200 ms batching. Topology event with N=20 nodes is ~2 KB. All well under `PIPE_BUF`.
- For the rare oversized event (a giant single token batch), we split at 4000 chars and tag continuation lines with `"continuation": true` — a 6-line addition to the writer.

### Why this is NOT "JSON-RPC over stdio" (MCP-style)

MCP uses stdio for **bidirectional RPC** (request/response/notification with IDs). We have a **one-way event stream** (writer → reader, no replies). Reusing MCP machinery would mean shipping `mcp` in the TUI just to ignore 90% of the protocol. The NDJSON-on-fd-3 design is the right-sized solution.

---

## 5. New file in `agent_foundation`: `StdioGraphReporter`

### 5.1 Location

`AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py` — sibling of `graph_interactive_adapter.py` so it ships through the same `ensure_siblings_on_path()` boundary the v6 plan established.

### 5.2 Interface contract

The class implements the **same 7-method protocol** as `WebSocketGraphReporter` (verified at `graph_interactive_adapter.py:93-232`):

| Method | Signature | Semantics |
|---|---|---|
| `on_graph_topology(event)` | `async (GraphTopologyEvent) -> None` | Serialize event to NDJSON dict, write to fd |
| `on_node_status(node_id, status, error="", output_path="")` | `async (...) -> None` | Same |
| `on_node_stream(node_id, content, is_final=True)` | `async (...) -> None` | Same; rate-limited at 30 msg/s (mirrors `WebSocketGraphReporter._max_msg_per_sec`); `is_final=True` always passes |
| `on_graph_reconcile(node_statuses)` | `async (dict) -> None` | Same |
| `node_stream_observer(node_id, flush_interval_ms=200.0)` | sync → `async callable` | **Reused verbatim** from `WebSocketGraphReporter` — same batching closure; we'll factor it to a free function `_make_batching_observer(send_fn, node_id, flush_interval_ms)` in this module and have both reporters use it (mini-refactor, see Phase 1c). |
| `node_interactive(node_id)` | sync → `Any` | Returns a `NodeStreamInteractive`-equivalent that emits node-tagged stream events via the fd. For the TUI we can return a no-op stub since the slash subprocess doesn't have a parent WS interactive — but a future "interactive `/task --confirm` in TUI" plan will need it (Phase 7C). |
| `child_reporter(parent_node_id)` | sync → `NamespacedGraphReporter` | **Reused verbatim** — `NamespacedGraphReporter` is generic and works with ANY parent reporter that satisfies the protocol (verified by reading the class: it calls `self._parent.on_graph_topology(...)`, `self._parent.on_node_status(...)`, etc. — no WebSocket-specific calls). |

### 5.3 Implementation (full code — paste-ready)

```python
# AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py
"""StdioGraphReporter — sibling of WebSocketGraphReporter for non-web frontends.

Emits the same `graph_reporter` protocol events as WebSocketGraphReporter, but
over a dedicated file descriptor as newline-delimited JSON (NDJSON), instead of
a WebSocket connection. Designed for the RovoDev TUI's subprocess invocation of
the four OpenTeam slash commands.

Design invariants (matches WebSocketGraphReporter):
  - All event sends wrapped in try/except — visualization failures NEVER
    abort the underlying computation.
  - `on_node_stream(is_final=True)` events are NEVER rate-limited.
  - `node_stream_observer` batches at 200 ms (same default).
  - `child_reporter` returns a NamespacedGraphReporter (reused as-is — it's
    generic over the parent reporter's protocol, not WebSocket-specific).

Activation contract:
  - Env var `ROVODEV_TUI_GRAPH_FD` must be set to the integer fd to write to.
  - If unset or fd is closed, the reporter no-ops (the rate-limit & try/except
    machinery still keeps the BTA from crashing).

This file is the ONLY new file in AgentFoundation for the graph-view plan.
"""
from __future__ import annotations

import json
import logging
import os
import time as _time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from agent_foundation.ui.graph_interactive_adapter import NamespacedGraphReporter

_logger = logging.getLogger(__name__)

_ENV_FD = "ROVODEV_TUI_GRAPH_FD"
_MAX_LINE_BYTES = 4000  # safe under PIPE_BUF on macOS (512 is per-write atomicity
                        # for tiny writes; we don't need atomicity for the multi-line
                        # continuation case but we DO want to stay under pipe buffer
                        # caps to avoid blocking the writer).


def _activated() -> int | None:
    """Return the fd to write to, or None if not activated."""
    raw = os.environ.get(_ENV_FD)
    if not raw:
        return None
    try:
        fd = int(raw)
    except ValueError:
        return None
    # Verify fd is actually open. os.fstat raises OSError if not.
    try:
        os.fstat(fd)
    except OSError:
        return None
    return fd


def _serialize(event: Any) -> dict:
    """Convert dataclass event to a JSON-safe dict with a discriminating 'type'.

    The 'type' tag matches the React WS schema exactly so the TUI's
    consumer can share parsing logic if we ever extract a common library.
    """
    from agent_foundation.common.inferencers.graph_events import (
        GraphTopologyEvent, NodeStatusEvent, NodeStreamEvent, GraphReconcileEvent,
    )
    if isinstance(event, GraphTopologyEvent):
        # Mirror websocket_interactive.send_graph_event:43-110 schema EXACTLY.
        msg = {
            "type": "graph_topology",
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
            "node_id": event.node_id,
            "content": event.content,
            "is_final": event.is_final,
        }
    if isinstance(event, GraphReconcileEvent):
        return {
            "type": "graph_reconcile",
            "nodes": event.node_statuses,
        }
    # Defensive: future event types we don't know about — serialize generically.
    if is_dataclass(event):
        d = asdict(event)
        d.setdefault("type", type(event).__name__)
        return d
    raise TypeError(f"Cannot serialize event of type {type(event).__name__}")


class StdioGraphReporter:
    """Sibling of WebSocketGraphReporter — writes NDJSON events to a fd.

    Implements the same 7-method protocol; events are framed as one JSON
    object per line on the fd named by env var ROVODEV_TUI_GRAPH_FD.
    """

    def __init__(self, fd: int, max_msg_per_sec: int = 30) -> None:
        self._fd = fd
        self._max_msg_per_sec = max_msg_per_sec
        self._send_times: list[float] = []
        # Cache: dedicated FILE object on the fd so we get buffered writes
        # + a single flush per line. Using os.write() directly would lose
        # the line-atomicity guarantee for long payloads.
        try:
            self._fp = os.fdopen(fd, "w", encoding="utf-8", buffering=1)
        except OSError as exc:
            _logger.warning("[StdioGraphReporter] fdopen(%d) failed: %s", fd, exc)
            self._fp = None

    @classmethod
    def from_env(cls) -> "StdioGraphReporter | None":
        """Factory used by tool executors. Returns None if not activated."""
        fd = _activated()
        if fd is None:
            return None
        return cls(fd)

    def _write(self, msg: dict) -> None:
        if self._fp is None:
            return
        try:
            line = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            _logger.warning("[StdioGraphReporter] json.dumps failed: %s", exc)
            return
        # Split oversized lines into chunks with continuation marker.
        if len(line.encode("utf-8")) > _MAX_LINE_BYTES and msg.get("type") == "node_stream":
            self._write_chunked_stream(msg)
            return
        try:
            self._fp.write(line + "\n")
        except OSError as exc:
            _logger.warning("[StdioGraphReporter] write failed: %s", exc)

    def _write_chunked_stream(self, msg: dict) -> None:
        """Split oversized node_stream content into multiple lines."""
        content = msg.get("content", "")
        is_final = msg.get("is_final", False)
        # Reserve ~200 bytes for the envelope; chunk by characters not bytes
        # for safety (we'd need a UTF-8-aware splitter for perfect bytes; the
        # 4000-char cap is conservative enough).
        chunk_size = 3000
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        for i, chunk in enumerate(chunks):
            sub = dict(msg)
            sub["content"] = chunk
            sub["is_final"] = is_final and (i == len(chunks) - 1)
            if i > 0:
                sub["continuation"] = True
            try:
                line = json.dumps(sub, separators=(",", ":"), ensure_ascii=False)
                self._fp.write(line + "\n")
            except OSError as exc:
                _logger.warning("[StdioGraphReporter] chunked write failed: %s", exc)
                return

    def _check_rate(self) -> bool:
        now = _time.monotonic()
        self._send_times = [t for t in self._send_times if now - t < 1.0]
        if len(self._send_times) >= self._max_msg_per_sec:
            return False
        self._send_times.append(now)
        return True

    # ── graph_reporter protocol ─────────────────────────────────────────

    async def on_graph_topology(self, event: Any) -> None:
        try:
            self._write(_serialize(event))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_topology failed: %s", exc)

    async def on_node_status(
        self, node_id: str, status: str, error: str = "", output_path: str = "",
    ) -> None:
        from agent_foundation.common.inferencers.graph_events import NodeStatusEvent
        try:
            self._write(_serialize(NodeStatusEvent(
                node_id=node_id, status=status, error=error, output_path=output_path,
            )))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_status failed: %s", exc)

    async def on_graph_reconcile(self, node_statuses: dict) -> None:
        from agent_foundation.common.inferencers.graph_events import GraphReconcileEvent
        try:
            self._write(_serialize(GraphReconcileEvent(node_statuses=node_statuses)))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_reconcile failed: %s", exc)

    async def on_node_stream(self, node_id: str, content: str, is_final: bool = True) -> None:
        # Mirror WebSocketGraphReporter.on_node_stream:160-172 EXACTLY.
        # is_final events always pass (never throttled).
        if not is_final and not self._check_rate():
            return
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent
        try:
            self._write(_serialize(NodeStreamEvent(
                node_id=node_id, content=content, is_final=is_final,
            )))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_stream failed: %s", exc)

    # ── observer + nesting helpers (mirror WebSocketGraphReporter) ──────

    def node_stream_observer(self, node_id: str, flush_interval_ms: float = 200.0
                             ) -> Callable:
        """Returns an async callable that batches chunks before sending.

        Identical batching contract to WebSocketGraphReporter.node_stream_observer
        (graph_interactive_adapter.py:173-216). The closure is the same shape;
        only the `_send` is swapped for our `_write` path.
        """
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent

        _batch: list[str] = []
        _last_flush = [_time.monotonic()]
        _send = self._write

        async def _observer(chunk: str) -> None:
            _batch.append(chunk)
            now = _time.monotonic()
            if (now - _last_flush[0]) * 1000 >= flush_interval_ms:
                content = "".join(_batch)
                _batch.clear()
                _last_flush[0] = now
                try:
                    _send(_serialize(NodeStreamEvent(node_id=node_id, content=content)))
                except Exception as exc:
                    _logger.warning(
                        "[StdioGraphReporter] node_stream_observer flush failed: %s", exc
                    )

        return _observer

    def node_interactive(self, node_id: str) -> Any:
        """Returns a stub interactive — the TUI subprocess doesn't have a
        bidirectional channel for per-node interactive prompts. If the future
        `/task --confirm` in the TUI needs this, see Phase 7C.
        """
        return _NoOpNodeInteractive(self, node_id)

    def child_reporter(self, parent_node_id: str) -> NamespacedGraphReporter:
        """Reuses NamespacedGraphReporter verbatim — verified at
        graph_interactive_adapter.py:234-274 to be generic over any parent
        that satisfies the protocol.
        """
        return NamespacedGraphReporter(self, parent_node_id)


class _NoOpNodeInteractive:
    """Stub for node_interactive() when no parent WS interactive exists.

    Token streams pass through unchanged but get tagged via on_node_stream
    so the TUI graph view still shows them. No prompt-style methods (asend_response,
    aget_input) are needed for non-interactive tools (task, create_role, etc.).
    """
    def __init__(self, parent: StdioGraphReporter, node_id: str) -> None:
        self._parent = parent
        self._node_id = node_id

    async def stream_token_batches(
        self, token_stream: Any, session_id: str = "",
        batch_interval_ms: float = 50.0, task_id: Any = None,
        send_stream_end: bool = True, turn_number: Any = None, **kwargs: Any,
    ) -> str:
        out: list[str] = []
        async for chunk, _metadata in token_stream:
            out.append(chunk)
            try:
                await self._parent.on_node_stream(self._node_id, chunk, is_final=False)
            except Exception as exc:
                _logger.debug("[_NoOpNodeInteractive] node_stream failed: %s", exc)
        try:
            await self._parent.on_node_stream(self._node_id, "", is_final=True)
        except Exception:
            pass
        return "".join(out)

    def __getattr__(self, name: str) -> Any:
        # Any other method called on us is a no-op coroutine — keeps
        # downstream code that expects e.g. asend_response from crashing.
        async def _noop(*args: Any, **kwargs: Any) -> None:
            return None
        return _noop
```

### 5.4 Tests for `StdioGraphReporter`

New file: `AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py`

| Test | TIER | What it asserts |
|---|---|---|
| `test_from_env_no_var` | 1 | `from_env()` returns None when `ROVODEV_TUI_GRAPH_FD` is unset |
| `test_from_env_invalid_int` | 1 | Returns None on garbage env value |
| `test_from_env_closed_fd` | 1 | Returns None when fd is closed (mock `os.fstat` raise) |
| `test_serialize_all_event_types` | 1 | Each of the 4 event dataclasses serializes to the schema in §5.3 verbatim — parameterized; compares dict equality |
| `test_on_node_stream_is_final_always_passes` | 1 | After exhausting rate (30 sends), `is_final=True` still writes; `is_final=False` does not |
| `test_oversize_node_stream_chunked` | 2 | 10 KB `content` → multiple lines, all but last have `"continuation": true`, last has `"is_final": true` if original did |
| `test_node_stream_observer_batches_at_200ms` | 2 | Use `freezegun` or `monotonic` monkeypatch; assert 100 calls produce 1 write at 200 ms boundary |
| `test_child_reporter_namespaces_node_ids` | 1 | `child_reporter("worker_0").on_node_status("propose", "running")` writes a line with `node_id="worker_0/propose"` — proves `NamespacedGraphReporter` reuse works |
| `test_send_exception_swallowed` | 1 | Make `_write` raise → `on_node_status(...)` returns None (does NOT raise) — proves the "visualization never aborts computation" invariant |
| `test_protocol_method_set_matches_websocket_reporter` | 1 / **CI preflight** | Use `inspect.getmembers(WebSocketGraphReporter, predicate=inspect.iscoroutinefunction)` and assert the set equals the same for `StdioGraphReporter`. Catches future drift if WebSocketGraphReporter adds a new method that we forget to implement here. |


---

## 6. Executor wiring (5-line diff per tool)

Each of the 4 tool executors already has the `WebSocketGraphReporter` attachment pattern (verified at `task/executor.py:493-498`, `create_role/executor.py:560+`, `role_setup/executor.py:1260+`, `project_onboarding/executor.py:166-168`).

The fix is to **add a fallback to `StdioGraphReporter.from_env()`** when no WebSocket interactive is present. The cleanest refactor:

### 6.1 New helper in `agent_foundation`

`AgentFoundation/src/agent_foundation/ui/graph_reporter_factory.py` (new file, ~25 lines):

```python
"""Factory: pick the right graph reporter based on runtime context.

Resolution order:
  1. WebSocketGraphReporter — if session_context has a non-None 'interactive'
     AND a non-empty task_id. This is the React UI path.
  2. StdioGraphReporter — if ROVODEV_TUI_GRAPH_FD env var is set. This is
     the RovoDev TUI subprocess path.
  3. None — silent fallback (the existing CLI behaviour).

Reporters are independent and never combined: if a tool is invoked from the
React UI (interactive present), the WS reporter wins even if the TUI env var
happens to be set (defense against env leakage in nested invocations).
"""
from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger(__name__)


def make_graph_reporter(session_context: dict, task_id: str = "") -> Any:
    """Returns a graph_reporter or None."""
    interactive = session_context.get("interactive")
    if interactive is not None and task_id:
        try:
            from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
            r = WebSocketGraphReporter(interactive, task_id)
            _logger.info("[graph_reporter_factory] WebSocketGraphReporter (task_id=%s)", task_id)
            return r
        except Exception as exc:
            _logger.warning("[graph_reporter_factory] WS reporter attach failed: %s", exc)
            # fall through to stdio
    try:
        from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter
        r = StdioGraphReporter.from_env()
        if r is not None:
            _logger.info("[graph_reporter_factory] StdioGraphReporter (fd from env)")
            return r
    except Exception as exc:
        _logger.warning("[graph_reporter_factory] Stdio reporter attach failed: %s", exc)
    return None
```

### 6.2 Per-tool executor diff (apply to all 4)

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
        _logger.info("[task] graph_reporter attached (%s)",
                     type(inferencer.graph_reporter).__name__)
except Exception as exc:
    _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

Apply the identical diff to `create_role/executor.py:560+`, `role_setup/executor.py:1260+`, `project_onboarding/executor.py:166-168`, `mock_task/executor.py:60-62`. The factory function makes the diff identical across all 5 tools (5 places × ~6 lines = 30 lines of code change total).

### 6.3 Why a factory not "try WS, except → Stdio"

The factory is explicit about precedence and gives a single observability surface (one log line per attachment site naming the reporter type). Inlining the fallback in each executor would duplicate the precedence rule 5 times and make future additions (e.g., `FileGraphReporter` for replay tests) painful. This is a textbook "extract method" — the same logic was already duplicated 5× before this plan.

### 6.4 What about `task_id` for the stdio path?

The stdio reporter does **NOT** use `task_id` (the WS reporter uses it as a routing key for multi-task WebSocket connections; the stdio reporter has exactly one consumer = the TUI handler that spawned it). For cleanliness we still pass `task_id` through `make_graph_reporter`, but `StdioGraphReporter.__init__` ignores it. Documented in §5.3.

### 6.5 Tests for the factory

`AgentFoundation/test/agent_foundation/ui/test_graph_reporter_factory.py`:

| Test | TIER | Assertion |
|---|---|---|
| `test_returns_ws_when_interactive_present` | 1 | `make_graph_reporter({"interactive": MockWS()}, "tid")` → `WebSocketGraphReporter` instance |
| `test_returns_stdio_when_env_var_set` | 1 | Env `ROVODEV_TUI_GRAPH_FD=3`, no interactive → `StdioGraphReporter` |
| `test_returns_none_when_neither` | 1 | Empty context, no env var → None |
| `test_ws_wins_over_stdio_when_both` | 1 | Both interactive AND env var set → WS reporter (defense against env leak) |
| `test_ws_attach_failure_falls_through_to_stdio` | 2 | Mock `WebSocketGraphReporter()` to raise → factory falls through to Stdio if env var present |

---

## 7. TUI side: fd-3 subprocess + Graph widget

### 7.1 Subprocess plumbing change (modify `slash_commands/openteam.py`)

Today the handler does:

```python
proc = await asyncio.create_subprocess_exec(
    *argv,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,      # merged
    stdin=asyncio.subprocess.DEVNULL,
    env=env,
    cwd=cwd,
)
```

The graph-view diff:

```python
import os as _os

# Create an OS-level pipe for graph events. The child writes; we read.
_event_read_fd, _event_write_fd = _os.pipe()

# Tell the child where to write.
env["ROVODEV_TUI_GRAPH_FD"] = str(_event_write_fd)

# Inheritability: on POSIX, fds are inheritable by default for fork+exec,
# but Python 3.4+ marks them non-inheritable. We must explicitly opt in.
_os.set_inheritable(_event_write_fd, True)

try:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,    # markdown
        stderr=asyncio.subprocess.PIPE,    # logs (split — see below)
        stdin=asyncio.subprocess.DEVNULL,
        pass_fds=(_event_write_fd,),       # graph events
        env=env,
        cwd=cwd,
    )
finally:
    # CRITICAL: close our copy of the write end. Without this, when the
    # child exits, the read end never sees EOF and the reader hangs forever.
    _os.close(_event_write_fd)

# Open the read end as a non-blocking async stream.
import asyncio as _asyncio
_event_reader = await _open_async_fd_reader(_event_read_fd)
```

We then run **three concurrent reader tasks** (instead of one):

```python
async def _read_stdout():
    while not worker.is_cancelled:
        line = await proc.stdout.readline()
        if not line: break
        app.call_from_thread(shell_output.append, line.decode("utf-8", "replace"))

async def _read_stderr():
    while not worker.is_cancelled:
        line = await proc.stderr.readline()
        if not line: break
        # stderr is for logs + [artifact_key] markers; render dimmed
        decoded = line.decode("utf-8", "replace")
        app.call_from_thread(shell_output.append, f"[dim]{decoded}[/dim]")

async def _read_events():
    while not worker.is_cancelled:
        line = await _event_reader.readline()
        if not line: break
        try:
            evt = json.loads(line)
        except json.JSONDecodeError as exc:
            _logger.debug("[openteam graph reader] bad NDJSON line: %s", exc)
            continue
        # Route to the graph view widget via a Textual message.
        app.call_from_thread(graph_view.handle_event, evt)

await asyncio.gather(_read_stdout(), _read_stderr(), _read_events(),
                     return_exceptions=True)
```

### 7.2 Helper for non-blocking fd reader

`cli-rovodev-tui/src/rovodev_tui/slash_commands/_async_fd.py` (new file, ~15 lines):

```python
"""Open a raw OS file descriptor as an asyncio StreamReader."""
from __future__ import annotations

import asyncio
import os


async def open_async_fd_reader(fd: int) -> asyncio.StreamReader:
    """Wrap a raw read-side fd as an asyncio StreamReader (POSIX only).

    On Windows we'd use a thread + queue (Phase 7B). For v1 we POSIX-only and
    fall back to "no graph view" on Windows (Phase 7B documents the path).
    """
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    # Wrap the raw fd into a Python file-like object.
    transport, _ = await loop.connect_read_pipe(lambda: protocol, os.fdopen(fd, "rb", 0))
    return reader
```

### 7.3 The `OpenteamGraphView` widget

`cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/` (new directory):

```
widgets/openteam_graph/
├── __init__.py           # exports OpenteamGraphView
├── view.py               # OpenteamGraphView container widget
├── topology_tree.py      # TopologyTree (Tree[NodeInfo]) with status icons
├── stream_pane.py        # StreamPane (Markdown subclass, per-node text)
├── state.py              # GraphState (dataclasses for node + edge + buffers)
└── events.py             # Textual messages: GraphEventMessage, NodeSelectedMessage
```

#### 7.3.1 `state.py` — pure data model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeInfo:
    id: str
    label: str
    group: Optional[str] = None
    status: str = "pending"
    is_container: bool = False
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""
    output_path: str = ""
    parent_id: str = ""       # the prefix before the last "/" in id, or ""


@dataclass
class GraphState:
    """Mirrors the React useGraphState contract; same numeric constants."""
    MAX_STREAM_SIZE: int = 200_000
    TRIM_SIZE: int = 50_000
    STICKY_DURATION_MS: int = 5_000
    MAX_TOTAL_STREAMS: int = 10_000_000

    nodes: dict[str, NodeInfo] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (source, target)
    node_streams: dict[str, str] = field(default_factory=dict)  # node_id → accumulated text
    selected_node_id: Optional[str] = None
    sticky_until: float = 0.0     # monotonic timestamp; auto-follow re-enables after this
    layout: str = "horizontal"

    def apply_topology(self, evt: dict) -> None:
        """Idempotent topology replacement (or sub-graph splice on parent_node_id)."""
        parent = evt.get("parent_node_id", "")
        prefix = f"{parent}/" if parent else ""
        for n in evt["nodes"]:
            nid = f"{prefix}{n['id']}" if not n['id'].startswith(prefix) else n['id']
            existing = self.nodes.get(nid)
            self.nodes[nid] = NodeInfo(
                id=nid, label=n.get("label", n["id"]),
                group=n.get("group"), status=n.get("status", "pending"),
                is_container=n.get("is_container", False),
                parent_id=parent,
            ) if existing is None else existing  # keep runtime state if we've seen it
        for e in evt["edges"]:
            src = f"{prefix}{e['source']}" if not e['source'].startswith(prefix) else e['source']
            tgt = f"{prefix}{e['target']}" if not e['target'].startswith(prefix) else e['target']
            if (src, tgt) not in self.edges:
                self.edges.append((src, tgt))

    def apply_status(self, evt: dict) -> None:
        n = self.nodes.get(evt["node_id"])
        if n is None:
            # Race buffer: status arrived before topology — recreate minimal
            n = NodeInfo(id=evt["node_id"], label=evt["node_id"])
            self.nodes[evt["node_id"]] = n
        n.status = evt["status"]
        if evt.get("label"):
            n.label = evt["label"]
        if evt["status"] == "running" and not n.started_at:
            n.started_at = evt["timestamp"]
        if evt["status"] in ("completed", "error") and not n.completed_at:
            n.completed_at = evt["timestamp"]
        if evt.get("error"):
            n.error = evt["error"]
        if evt.get("output_path"):
            n.output_path = evt["output_path"]

    def apply_stream(self, evt: dict) -> None:
        nid = evt["node_id"]
        content = self.node_streams.get(nid, "") + evt["content"]
        if len(content) > self.MAX_STREAM_SIZE:
            content = content[-self.TRIM_SIZE:]  # keep tail (latest tokens)
        self.node_streams[nid] = content
        self._cap_total_streams()

    def apply_reconcile(self, evt: dict) -> None:
        for nid, status in evt["nodes"].items():
            n = self.nodes.get(nid)
            if n is not None and n.status != status:
                n.status = status

    def _cap_total_streams(self) -> None:
        total = sum(len(v) for v in self.node_streams.values())
        if total <= self.MAX_TOTAL_STREAMS:
            return
        # Purge completed nodes first (largest first), keep 2 KB of each
        purgeable = sorted(
            (nid for nid, n in self.nodes.items()
             if n.status in ("completed", "error", "skipped")),
            key=lambda nid: -len(self.node_streams.get(nid, "")),
        )
        for nid in purgeable:
            if total <= self.MAX_TOTAL_STREAMS:
                return
            old_len = len(self.node_streams.get(nid, ""))
            self.node_streams[nid] = self.node_streams.get(nid, "")[-2_000:]
            total -= (old_len - len(self.node_streams[nid]))
```

#### 7.3.2 `topology_tree.py` — Tree[NodeInfo] subclass

```python
from __future__ import annotations
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from rich.text import Text
from .state import GraphState, NodeInfo


_STATUS_ICON = {
    "pending":   "[dim]○[/dim]",
    "running":   "[yellow]⏵[/yellow]",
    "completed": "[green]●[/green]",
    "error":     "[red]✗[/red]",
    "skipped":   "[dim]◌[/dim]",
}


class TopologyTree(Tree[NodeInfo]):
    """Renders the graph as a hierarchical tree.

    Nesting comes free from the `parent/child/grandchild` node id convention
    that NamespacedGraphReporter establishes (verified at
    graph_interactive_adapter.py:248-269). Edges within a level are implied
    by sibling order — for DAGs we choose a topological sort to make the
    visual order match execution order.

    For nested graphs (sub-BTAs), the parent container node becomes the parent
    tree node and the sub-graph nodes become its children — this matches the
    React UI's containerView semantics (useGraphState.js subGraphs).
    """

    DEFAULT_CSS = """
    TopologyTree {
        height: 1fr;
        width: 1fr;
        border: solid $accent;
    }
    """

    def __init__(self, state: GraphState, **kw):
        super().__init__("OpenTeam Run", **kw)
        self._state = state
        self.show_root = False
        self.show_guides = True
        self._node_to_tree: dict[str, TreeNode] = {}

    def rebuild(self) -> None:
        """Idempotent: incrementally adds new nodes, updates labels for existing ones."""
        self.clear()
        self._node_to_tree.clear()
        # Topo-sort: nodes whose parent_id is "" first; then BFS by edges.
        roots = [n for n in self._state.nodes.values() if not n.parent_id]
        for root in self._sorted(roots):
            self._add_recursive(root, parent=self.root)

    def _sorted(self, nodes):
        # Preserve insertion order of the underlying dict (topology event order)
        return sorted(nodes, key=lambda n: list(self._state.nodes).index(n.id))

    def _add_recursive(self, node: NodeInfo, parent: TreeNode) -> None:
        tn = parent.add(self._render_label(node), data=node, expand=True)
        self._node_to_tree[node.id] = tn
        children = [n for n in self._state.nodes.values()
                    if n.parent_id == node.id or n.id.startswith(node.id + "/")]
        for child in self._sorted(children):
            # Only direct children (one level of "/")
            tail = child.id[len(node.id) + 1:]
            if "/" not in tail:
                self._add_recursive(child, tn)

    def _render_label(self, n: NodeInfo) -> Text:
        icon = _STATUS_ICON.get(n.status, "?")
        elapsed = ""
        if n.started_at:
            end = n.completed_at or _time.time()
            elapsed = f" ({int(end - n.started_at)}s)"
        return Text.from_markup(f"{icon} {n.label}{elapsed}")
```

#### 7.3.3 `stream_pane.py` — Markdown subclass

```python
from textual.widgets import Markdown

class StreamPane(Markdown):
    """Renders the currently-selected node's accumulated stream as Markdown."""
    DEFAULT_CSS = """
    StreamPane {
        height: 1fr;
        border: solid $accent;
        padding: 0 1;
    }
    """
```

#### 7.3.4 `view.py` — composing container

```python
from __future__ import annotations
import time
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.message import Message
from .state import GraphState
from .topology_tree import TopologyTree
from .stream_pane import StreamPane


class OpenteamGraphView(Widget):
    """The composite graph view mounted by the slash handler.

    Layout: horizontal split (40% tree | 60% stream pane).
    """

    DEFAULT_CSS = """
    OpenteamGraphView {
        height: 30;       /* ~30 rows; user can resize via Textual focus shortcuts */
        margin: 1 0;
    }
    OpenteamGraphView Horizontal {
        height: 100%;
    }
    OpenteamGraphView TopologyTree {
        width: 40%;
    }
    OpenteamGraphView StreamPane {
        width: 60%;
    }
    """

    BINDINGS = [
        ("escape", "collapse", "Collapse graph view"),
        ("ctrl+r", "rebuild", "Force rebuild"),
    ]

    def __init__(self, **kw):
        super().__init__(**kw)
        self.state = GraphState()
        self._tree: TopologyTree | None = None
        self._stream: StreamPane | None = None

    def compose(self):
        with Horizontal():
            self._tree = TopologyTree(self.state)
            yield self._tree
            self._stream = StreamPane()
            yield self._stream

    # ── event ingestion (called from the slash handler via app.call_from_thread) ──

    def handle_event(self, evt: dict) -> None:
        """Apply an NDJSON event to state and re-render the affected widget(s)."""
        t = evt.get("type")
        if t == "graph_topology":
            self.state.apply_topology(evt)
            if self._tree: self._tree.rebuild()
        elif t == "node_status":
            self.state.apply_status(evt)
            self._maybe_auto_select(evt)
            if self._tree: self._tree.rebuild()
            self._refresh_stream()
        elif t == "node_stream":
            self.state.apply_stream(evt)
            self._refresh_stream(only_if_selected=evt["node_id"])
        elif t == "graph_reconcile":
            self.state.apply_reconcile(evt)
            if self._tree: self._tree.rebuild()

    # ── auto-follow with sticky selection (mirrors useGraphState.js) ──

    def _maybe_auto_select(self, evt: dict) -> None:
        if evt.get("status") != "running":
            return
        if time.monotonic() < self.state.sticky_until:
            return  # user clicked recently — don't override
        self.state.selected_node_id = evt["node_id"]
        if self._tree:
            tn = self._tree._node_to_tree.get(evt["node_id"])
            if tn is not None:
                self._tree.select_node(tn)

    def _refresh_stream(self, only_if_selected: str | None = None) -> None:
        if only_if_selected and only_if_selected != self.state.selected_node_id:
            return
        if not self._stream or not self.state.selected_node_id:
            return
        nid = self.state.selected_node_id
        n = self.state.nodes.get(nid)
        header = f"## {nid} — {n.status if n else '?'}"
        body = self.state.node_streams.get(nid, "")
        self._stream.update(f"{header}\n\n```\n{body}\n```")

    # ── user interaction ──

    def on_tree_node_selected(self, ev: Tree.NodeSelected) -> None:
        node_info = ev.node.data
        if node_info is not None:
            self.state.selected_node_id = node_info.id
            self.state.sticky_until = time.monotonic() + (self.state.STICKY_DURATION_MS / 1000)
            self._refresh_stream()

    def action_collapse(self) -> None:
        self.remove()

    def action_rebuild(self) -> None:
        if self._tree: self._tree.rebuild()
```


### 7.4 Integration into `slash_commands/openteam.py`

The handler grows from ~85 lines to ~140 lines. Key insertions, in order:

1. Top of file: import `OpenteamGraphView`, `open_async_fd_reader`, `json`.
2. Inside `_make_handler`, before `create_subprocess_exec`:
   - `_event_read_fd, _event_write_fd = os.pipe()`
   - `env["ROVODEV_TUI_GRAPH_FD"] = str(_event_write_fd)`
   - `os.set_inheritable(_event_write_fd, True)`
3. Mount the graph view BEFORE the spinner (so its initial empty state is visible while the topology event arrives):
   - `graph_view = OpenteamGraphView()`
   - `app.call_from_thread(app.chat_container.mount, graph_view)`
4. Replace `stderr=STDOUT` with `stderr=PIPE` + `pass_fds=(_event_write_fd,)`.
5. Immediately after subprocess creation: `os.close(_event_write_fd)`. **Critical** — otherwise EOF never propagates.
6. Open the event reader: `event_reader = await open_async_fd_reader(_event_read_fd)`.
7. Replace the single `while ... readline()` loop with `await asyncio.gather(_read_stdout(), _read_stderr(), _read_events())`.
8. After `proc.wait()`: do NOT remove the graph view — leave it visible for browse-after-completion. Add Esc binding to dismiss (handled by `OpenteamGraphView.BINDINGS`).

### 7.5 Opt-out

Two opt-out paths, in priority order:
1. **Env var:** `ROVODEV_TUI_GRAPH_DISABLE=1` — handler skips graph view creation, runs old code path. For users who hate the change.
2. **Tool unsupported:** for tools that don't emit graph events (mock_task with `__mock_input__` is fine but a hypothetical future single-LLM-call tool wouldn't), the topology event simply never arrives → graph view shows "Waiting for topology…" message → user can press Esc to dismiss. Auto-collapse-after-Nsec is **Phase 8** (not v1).

---

## 8. Phased delivery

| Phase | What | LoC | Time | Dep |
|---|---|---|---|---|
| **0** | Re-verify ground truth still holds (run grep against AgentFoundation/OpenStartup post-v6) | 0 | 15 min | — |
| **1a** | `agent_foundation/ui/stdio_graph_reporter.py` + 9 tests | ~280 + 200 | 4 h | — |
| **1b** | `agent_foundation/ui/graph_reporter_factory.py` + 5 tests | ~35 + 100 | 1 h | 1a |
| **2** | Patch 5 executors (`task`, `create_role`, `role_setup`, `project_onboarding`, `mock_task`) to use factory — identical 6-line replacement | ~30 (-50 old) | 1.5 h | 1b |
| **3a** | `cli-rovodev-tui/widgets/openteam_graph/{state,topology_tree,stream_pane,events,view,__init__}.py` | ~400 | 1 day | 1a |
| **3b** | `cli-rovodev-tui/slash_commands/_async_fd.py` | ~15 | 15 min | — |
| **3c** | Modify `cli-rovodev-tui/slash_commands/openteam.py` (3 reader tasks + graph view mount) | +60 -10 | 4 h | 3a, 3b |
| **4a** | TUI tests: graph view state transitions, sticky selection, race buffer, oversized stream | ~250 | 4 h | 3a |
| **4b** | TUI snapshot test: render a fixture GraphState; assert rich-text output matches recorded snapshot | ~80 | 2 h | 3a |
| **4c** | Integration test: real subprocess (using `mock_task`) → NDJSON → graph state | ~120 | 3 h | 2, 3c |
| **5** | Docs: update `OpenStartup/docs/MCP_INTEGRATION.md` (rename to RUNTIME_INTEGRATION.md?) with a "Graph view" section + screencast GIF; update SKILL.md hint | — | 1 h | 3c |

**Critical path:** 0 → 1a → 1b → 2 → 3a/b/c → 4a/b/c → 5
**Total:** ~3 days of focused work.

---

## 9. Test plan

| File | TIER | Coverage |
|---|---|---|
| `test_stdio_graph_reporter.py` | 1 | 9 tests; see §5.4 |
| `test_graph_reporter_factory.py` | 1 | 5 tests; see §6.5 |
| `test_executor_graph_reporter_attach.py` (each tool) | 2 | Mock `make_graph_reporter` to return a sentinel; assert `inferencer.graph_reporter` is set on it; one test per tool (4 tests) |
| `test_graph_state.py` | 1 | `apply_topology` (with + without parent_node_id), `apply_status` (race buffer when topology not yet arrived), `apply_stream` (under cap, exactly at cap with tail kept, exceeded with `_cap_total_streams` triggering), `apply_reconcile` |
| `test_topology_tree.py` | 1 | Rebuild idempotent; status icons correct; nested via `parent/child` id splits to tree children; topological sort stable |
| `test_openteam_graph_view.py` | 1 | `handle_event` dispatches to right `apply_*`; sticky selection: post-click, status events do NOT change selection for 5 s; auto-select: status=running while NOT sticky moves selection |
| `test_async_fd_reader.py` | 2 | Write 3 lines to a `os.pipe()` → reader yields 3 `readline()` results; close write end → reader sees EOF |
| `test_handler_three_readers_concurrent.py` | 2 | Mock proc with stdout=PIPE/stderr=PIPE/fd=3-pipe; write to each; assert all 3 routed to right widget (ShellOutput appends + GraphView.handle_event) |
| `test_handler_graph_view_persists_after_exit.py` | 2 | proc exits → ShellOutput remains, ThinkingSpinner removed, GraphView still mounted |
| `test_handler_disable_env_skips_graph.py` | 2 | `ROVODEV_TUI_GRAPH_DISABLE=1` → graph view NOT mounted, behaviour matches v6 baseline |
| `test_integration_mock_task_graph.py` | 2 | Spawn real `openteam-mock-task` (if console script exists; else `python -m openteam.server.resources.tools.mock_task`); read fd=3 stream; assert ≥1 topology + N status + N stream + 1 reconcile event |
| `test_openteam_graph_snapshot.py` | 2 | Use `pytest-textual-snapshot` headless rendering; one snapshot per state (initial empty, mid-execution with 2 running workers, complete with selected aggregator) |
| `test_protocol_method_set_matches_websocket_reporter.py` | 1 / **CI preflight** | `inspect.getmembers(WebSocketGraphReporter, …)` ≡ same for `StdioGraphReporter` (within the documented allow-list). Locks the contract; any future method added to WS must also be added to Stdio. |

---

## 10. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Windows: `pass_fds` semantics differ → graph view doesn't work | High on Windows | Medium | Phase 7B fallback: on Windows, fall back to "no graph view" with one-time notify "Graph view not yet supported on Windows; track GH#…". v1 is POSIX-only by design. |
| Subprocess crashes mid-stream with partial NDJSON line | Low | Low | `json.JSONDecodeError` caught in `_read_events` → log + continue. Reader sees EOF from pipe → exits cleanly. |
| Topology event > `PIPE_BUF` (4 KB) on a giant graph | Very low | Low | Topology events for typical BTAs (<50 nodes) are <4 KB. For nested BTAs sending multiple topology events, each is bounded. The `_write` path uses `fp.write` (buffered + line-flushed by `buffering=1` in `os.fdopen`) → Python handles the framing. |
| User invokes the slash command, then closes the TUI before subprocess exits → orphaned subprocess + leaked fd | Medium | Low | Existing `worker.is_cancelled → proc.terminate()` pattern already handles this. The fd is closed by Python's GC when the StreamReader is collected. |
| `pytest-textual-snapshot` dep is heavy / breaks CI | Low | Low | Snapshot tests are TIER-2 (`@pytest.mark.snapshot`); CI matrix can skip them. Manual review via screencast GIF in the PR description. |
| Future contributor adds a 5th tool that emits graph events but forgets to apply the factory diff | Medium | Medium | The factory is so small that copying the 6-line block is easy to forget. Mitigation: add `test_factory_used_by_all_tool_executors.py` that grep-asserts every `executor.py` calls `make_graph_reporter` (TIER-1 / CI preflight). |
| Stdio reporter and WebSocket reporter drift in the protocol surface | Medium over time | High | `test_protocol_method_set_matches_websocket_reporter.py` (CI preflight, see §9). Catches the drift the moment a new method is added to WS without being added to Stdio. |
| `os.fdopen(buffering=1)` doesn't actually do per-line flush in all CPython versions | Low | Low | Add an explicit `self._fp.flush()` after each `write` for paranoia (it's a no-op for already-flushed line-buffered streams). Verify in test_stdio_graph_reporter.py via `os.read(fd)` immediately after a write. |
| User has rendered too many graph views (one per /task) → memory leak | Low (transient widgets) | Low | `OpenteamGraphView.action_collapse` removes the widget. Document that "Esc collapses the graph view." Future enhancement: auto-collapse old views after N new commands (Phase 8). |
| Subprocess inherits unexpected fds beyond fd=3 → security/privacy issue | Very low | Low | `asyncio.create_subprocess_exec(pass_fds=(_event_write_fd,))` only passes the explicit set; Python 3.4+ marks all other fds non-inheritable by default. |
| Existing CI doesn't have a TTY → Textual snapshot tests fail | Low | Low | `pytest-textual-snapshot` uses headless rendering (`SVGScreenshot`); works in CI without TTY. Verified in cli-rovodev-tui's existing snapshot tests. |
| Graph view CSS conflicts with existing chat theme | Low | Low | All new CSS scoped under `OpenteamGraphView` / `TopologyTree` / `StreamPane`. Uses theme variables (`$accent`, `$dim`) not hardcoded colors. Mirrors cli-rovodev-tui's `constants.py` Atlassian palette. |

---

## 11. Self-audit (stress questions, answered honestly)

| Question | Answer |
|---|---|
| **Why not just add color/status to the existing ShellOutput stream?** | That would only solve the "spinner spins silently" problem, not the "user can't see which of 5 parallel workers is running" problem. The graph view is fundamentally a *tree-structured* concern, not a *flat-stream* one. |
| **Why not embed the React UI in Textual via a webview?** | Textual has no webview. Even if it did, the React UI requires the OpenStartup FastAPI server running on localhost — which defeats the whole "subprocess invocation" elegance the v6 plan established. |
| **Could we just point the TUI's browser at the OpenStartup web UI when /task runs?** | That'd require starting a FastAPI server inside the subprocess, allocating a port, opening a browser tab, and breaking the user out of their TUI flow. Hard reject — the whole point of slash commands is to keep the user in the TUI. |
| **Why is the graph view always-on instead of opt-in (`/task --graph`)?** | Two reasons. (1) Most users will want it most of the time; making it opt-in means most users miss out on the best feature. (2) An opt-out env var (`ROVODEV_TUI_GRAPH_DISABLE=1`) is more discoverable than an opt-in flag because it appears in startup banner / docs. (3) For tools that don't emit graph events, the view shows "Waiting for topology…" briefly and the user dismisses — minor cost. |
| **What happens if BTA is wrapped by a non-BTA inferencer that doesn't propagate `graph_reporter`?** | The non-BTA inferencer would set `graph_reporter` on itself but never call it. Topology event never arrives. View shows "Waiting for topology…". User dismisses with Esc. Documented limitation; not v1 scope to fix all non-BTA inferencers. |
| **Won't the duplicated batching closure in `WebSocketGraphReporter` and `StdioGraphReporter` drift?** | Yes — that's why Phase 1c (mini-refactor) extracts `_make_batching_observer(send_fn, node_id, flush_interval_ms)` to a free function in `graph_interactive_adapter.py` and has both reporters use it. Out-of-scope for v1 if we want to ship fast; in-scope as Phase 9 cleanup. |
| **Why a Textual `Widget` not a `ModalScreen`?** | The graph view should coexist with the chat container (the user might want to type a follow-up message while looking at the graph). Modal blocks all other interaction. Inline widget is the cli-rovodev-tui convention — verified at `chat_container.mount()` pattern. |
| **What if two `/task` commands are running concurrently?** | Two `OpenteamGraphView` instances are mounted, each owning its own `GraphState`. Each subprocess has its own fd-3 pipe; no cross-talk. The TUI's `chat_container` stacks them in chronological order — same as multiple shell commands today. |
| **Does this commit RovoDev to a specific AgentFoundation version?** | Yes — to one that includes `StdioGraphReporter` (new) AND `WebSocketGraphReporter` (existing). The slash subprocess imports AgentFoundation already; if AgentFoundation lacks `StdioGraphReporter`, the factory's import fails, the reporter stays None, graph view shows "Waiting for topology…" — graceful degradation. |
| **What if a user pipes `openteam-task ... 3>&1` to debug?** | fd=3 gets duplexed onto stdout. NDJSON lines mix with markdown. The user sees the raw events — exactly what they wanted for debugging. Documented behaviour. |
| **What if the user's shell sets `ROVODEV_TUI_GRAPH_FD` accidentally?** | `_activated()` checks `os.fstat(fd)` — if fd 3 isn't actually open, returns None. Bogus env var → silent fallback. |
| **What about non-BTA inferencers that DO emit graph events (e.g., LinearWorkflow)?** | Same flow — they call the same `graph_reporter` protocol. The factory + reporter are inferencer-agnostic. |
| **Should we render the graph as an actual node-and-edge diagram (DOT-style ASCII art)?** | No — DAG layout in pure text is a research problem (graphviz spends thousands of CPU seconds on it). Tree representation is lossy (edges from non-tree-parent nodes are dropped) but visually intelligible at terminal sizes. v1 ships Tree; v2 could add a `--layout=dot` flag using `graphviz` lib. |
| **Could we surface artifact paths from `node_status.output_path` as clickable in the TUI?** | Yes — `output_path` is in the NodeStatusEvent (verified at graph_events.py:96-99). v1 displays the path as plain text in the stream pane header. v2 enhancement: bind Enter on a selected node to open the file in the user's `$EDITOR` (mirrors `shell.py`'s `/edit` pattern). |
| **What's the security model for `pass_fds`?** | We pass exactly one fd (the write end of an OS pipe we created). The child can only write to that fd; it has no access to the read end. Standard Unix capability passing. |

---

## 12. Definition of Done

- [ ] All new files created (see §8 for the list); all `__init__.py` updated.
- [ ] `agent_foundation.ui.stdio_graph_reporter:StdioGraphReporter` importable; `from_env()` returns None without env var, instance with env var.
- [ ] `agent_foundation.ui.graph_reporter_factory:make_graph_reporter` returns the right type per §6.5 truth table.
- [ ] All 5 executors patched; `inferencer.graph_reporter is not None` when invoked from TUI subprocess.
- [ ] `openteam-mock-task` console script (or `python -m openteam.server.resources.tools.mock_task`) emits valid NDJSON on fd=3 when env var is set.
- [ ] `openteam-mock-task --help` still works (env var absent → silent fallback).
- [ ] In RovoDev TUI: `/task "what is 2+2"` shows the graph view above the streaming markdown.
- [ ] In RovoDev TUI: Tree row selection → stream pane updates to show that node's accumulated content.
- [ ] In RovoDev TUI: after click, status events for OTHER nodes do NOT change selection for 5 s (sticky).
- [ ] In RovoDev TUI: Ctrl-C terminates subprocess within 5 s (existing v6 contract preserved).
- [ ] In RovoDev TUI: Esc collapses the graph view (subprocess keeps running if still alive).
- [ ] In RovoDev TUI: `ROVODEV_TUI_GRAPH_DISABLE=1 /task "…"` → no graph view, identical to v6 UX.
- [ ] All TIER-1 tests pass; TIER-2 tests pass in CI.
- [ ] CI preflight `test_protocol_method_set_matches_websocket_reporter` passes.
- [ ] `docs/MCP_INTEGRATION.md` updated with "Graph view" subsection.
- [ ] PR description includes a screencast / GIF (or asciinema) showing the graph view in action against `mock_task`.

---

## 13. Out of scope (deliberate non-goals for v1)

- Windows support — Phase 7B follow-up.
- Interactive `/task --confirm` per-node prompts via TUI — Phase 7C follow-up (requires bidirectional fd channel; current design is one-way).
- Graphviz/DOT layout — v2 enhancement.
- Clickable artifacts (Enter on node → `$EDITOR`) — v2 enhancement.
- Auto-collapse stale graph views — Phase 8 enhancement.
- Cross-task graph aggregation ("show me all my running /task graphs") — separate plan.
- Persisting graph state across TUI restarts — out-of-scope; live execution only.

---

## 14. Open questions for the user

1. **Where in the chat container should the graph view appear?** Above the markdown (so user reads top-to-bottom: graph then result)? Below? Side-by-side via Textual `Horizontal`? — v1 PROPOSAL: ABOVE the markdown.
2. **Should `/task` opt-out via env var (`ROVODEV_TUI_GRAPH_DISABLE=1`) OR via a slash flag (`/task --no-graph "…"`)?** — v1 PROPOSAL: env var only (slash flag would require argv parsing in the handler, adding complexity).
3. **How tall should the graph view be?** Fixed 30 rows? 50% of screen? Dynamic based on number of nodes? — v1 PROPOSAL: fixed `height: 30` (Textual rows); user can resize via Textual's focus shortcut (TBD if Textual supports widget-level resize today).
4. **Should the stream pane scroll the latest content into view automatically?** Yes by default; toggle with a key? — v1 PROPOSAL: yes auto-scroll; no toggle.
5. **What about color-blindness?** Status icons (`○`, `⏵`, `●`, `✗`, `◌`) are intentionally shape-distinguished (not color-only). Color is supplementary. — v1: ship with shape+color; verify with macOS Accessibility palette inspector before merging.

---

## 15. Comparison to alternatives explicitly considered and rejected

| Alternative | Why rejected |
|---|---|
| **Re-use the WebSocket reporter by launching an embedded server in the subprocess + websocket client in the TUI** | Adds the `websockets` lib to both sides; port allocation; firewall prompts on macOS; teardown races. Solves a problem (bidirectional RPC) we don't have. |
| **MCP-style JSON-RPC over stdio** | Bidirectional protocol overhead for a one-way stream. Would mean shipping `mcp` lib for no marginal benefit. |
| **gRPC over a Unix socket** | New transitive deps (`grpcio`, `protobuf`); per-task socket lifecycle; Windows incompatible without named-pipe equivalent. |
| **Tail a JSONL file written by the subprocess** | Disk I/O; cleanup of stale files; race between writer flush and reader poll. The pipe-on-fd approach is the same model without the disk hop. |
| **Use OpenTelemetry spans + a local OTLP collector + a Textual viewer** | Massive surface for a feature that needs 4 event types. |
| **Render the graph in the chat-container's Markdown widget (no custom widget)** | Markdown can't represent selectable interactive elements; can't update sub-regions in place; would re-render the entire blob on every event. |
| **Just add a status bar showing "N/M workers complete"** | Loses the per-node streaming view, which is the *whole point* of having a graph view (otherwise the spinner already conveys "something is happening"). |

---

## 16. Comparison to similar features in other tools

- **`gh run watch`** (GitHub CLI): live job tree with status icons; closest precedent. Not a DAG (jobs are flat) but the UX (Tree + per-job log expansion on click) is exactly what we're building.
- **`docker compose up`** with multi-service output: interleaved log lines colored per service. Doesn't show topology — proves that "just colored streams" is insufficient when N > 3.
- **`bazel build` with `--curses`**: live status grid for parallel build actions. Inspirational for the icon+elapsed-time format.
- **OpenTeam React UI** (`ui/src/hooks/useGraphState.js`): the canonical reference. Our `GraphState` mirrors its data model field-for-field with the same numeric constants — so a user switching between web and TUI gets the *same* mental model.

---

## 17. Round-1 critical-thinking self-review

Before requesting external review, here are the issues I myself identified while writing this plan, with the fixes already applied:

| Issue I caught | Fix |
|---|---|
| `pass_fds` requires `set_inheritable(fd, True)` on Python 3.4+ — without it the child sees a closed fd | Added §7.1 step 3 |
| Parent must close its copy of the write end after spawn, else reader never sees EOF | Added §7.1 step 5 with "CRITICAL" note |
| `_serialize` would crash on unknown event types if a new event class is added in AgentFoundation | Added defensive `isinstance` chain + dataclass fallback + named `TypeError` (§5.3) |
| `os.fdopen(buffering=1)` for line buffering is correct but worth explicit testing | Added §10 risk row + paranoia `flush()` in tests |
| The `node_stream_observer` batching closure is duplicated between WS and Stdio reporters | Acknowledged in §11 self-audit (Phase 1c mini-refactor to a shared helper) |
| Race: status event for a node whose topology hasn't arrived yet (sub-graph splice) | `apply_status` creates a minimal `NodeInfo` defensively (§7.3.1) |
| Sticky selection clock must use `monotonic()` not `time.time()` to be NTP-skew-safe | Used `time.monotonic()` (§7.3.4) |
| `_cap_total_streams` could thrash if MAX is set too low for the running graph | Set `MAX_TOTAL_STREAMS = 10_000_000` matching React; if user reports thrash, add Phase 8 dynamic cap |
| `_node_to_tree` map grows unbounded as graph events arrive — leak? | Cleared in `rebuild()` (§7.3.2); incremental updates rebuild from `self._state.nodes`, no leak |
| What if `worker.is_cancelled` flips mid-event-read and we drop a partial line? | `_read_events` checks at top of loop; partial reads from `StreamReader.readline()` are atomic (returns full line or empty); no corruption |
| Tests would lock in current React UI numeric constants — what if React changes them? | The constants are documented in `state.py` as "mirrors React useGraphState.js" — drift is a documentation issue, not a test failure. If React ever changes them, we can re-align. |
| `from_env()` reads env var at instantiation — if a test sets the var after import, the reporter sees stale state | `from_env()` re-reads on every call; not cached. Verified in §5.3 code. |

---

## 18. Touch list (every file)

### NEW
```
AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py
AgentFoundation/src/agent_foundation/ui/graph_reporter_factory.py
AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py
AgentFoundation/test/agent_foundation/ui/test_graph_reporter_factory.py

cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/__init__.py
cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/state.py
cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/topology_tree.py
cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/stream_pane.py
cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/events.py
cli-rovodev-tui/src/rovodev_tui/widgets/openteam_graph/view.py
cli-rovodev-tui/src/rovodev_tui/slash_commands/_async_fd.py
cli-rovodev-tui/tests/widgets/openteam_graph/test_state.py
cli-rovodev-tui/tests/widgets/openteam_graph/test_topology_tree.py
cli-rovodev-tui/tests/widgets/openteam_graph/test_view.py
cli-rovodev-tui/tests/slash_commands/test_async_fd.py
cli-rovodev-tui/tests/slash_commands/test_openteam_graph_integration.py
cli-rovodev-tui/tests/widgets/openteam_graph/test_snapshot.py
```

### MODIFIED
```
OpenStartup/src/openteam/server/resources/tools/task/executor.py            # 6-line factory diff
OpenStartup/src/openteam/server/resources/tools/create_role/executor.py     # 6-line factory diff
OpenStartup/src/openteam/server/resources/tools/role_setup/executor.py      # 6-line factory diff
OpenStartup/src/openteam/server/resources/tools/project_onboarding/executor.py  # 6-line factory diff
OpenStartup/src/openteam/server/resources/tools/mock_task/executor.py       # 6-line factory diff (for integration test)
cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py                  # +60 -10 (3 readers, graph view mount)
cli-rovodev-tui/src/rovodev_tui/widgets/__init__.py                         # re-export OpenteamGraphView
OpenStartup/docs/MCP_INTEGRATION.md                                         # "Graph view" subsection
```

**Total:** 17 new files + 8 modified.

---

## 19. Glossary

- **BTA** — `BreakdownThenAggregateInferencer`. The agent topology that the 4 OpenTeam tools use.
- **graph_reporter** — Duck-typed protocol exposed by BTA for emitting topology / status / stream / reconcile events.
- **NDJSON** — Newline-Delimited JSON: one JSON object per line; the wire format for fd=3.
- **fd=3** — The dedicated OS file descriptor we pass to the subprocess for graph events (POSIX convention; first "extra" fd).
- **Sticky selection** — UX behaviour where a manually-clicked node stays selected for 5 s, overriding auto-follow.
- **Race buffer** — Storage for events that arrive before the topology event that explains their node IDs (e.g., a worker node's status event arrives before its sub-graph topology).
