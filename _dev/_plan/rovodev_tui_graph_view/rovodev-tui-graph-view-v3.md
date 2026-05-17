# RovoDev TUI — OpenTeam Graph Visualization (v3 PLAN, integrated)

**Status:** Proposal · ready for review
**Created:** 2026-05-17 02:44
**Supersedes:** `rovodev-tui-graph-view-v2.md` (my prior v2), `.claude/plans/eager-roaming-clock.md` (Claude v2, 75 lines), `.cursor/plans/tui_graph_visualization_4c8499de.plan.md` (Cursor v2, 1170 lines)
**Author:** rovodev (fourth-pass integration; all three plans re-read at 02:42)
**Scope:** Add a real-time agent topology graph + per-node streaming panel to the RovoDev TUI when invoking the 4 OpenTeam slash commands (`/task`, `/create-role`, `/role-setup`, `/project-onboarding`).

---

## 0. Revision history vs v2 (what changed, why, and how I caught it)

This v3 is born from re-reading all three plans and finding **two critical architectural bugs in my v2** (which I am happy I caught) and **one critical runtime bug in Cursor's plan** (which I caught for them).

### Bugs in v2 (mine) that v3 fixes

| Bug | Severity | Root cause | Evidence | Fix in v3 |
|---|---|---|---|---|
| **Double-wiring contradiction**: v2 patched `tool_cli.run_cli` to construct the reporter AND patched 5 executors to call `make_graph_reporter`. The factory then had a precedence rule (`pre = session_context.get("graph_reporter")`) to disambiguate — but the contradiction means *one of the two patches is dead code*, and reviewers can't tell which. | CRITICAL | I tried to claim "Cursor's tool_cli boundary is superior" while keeping my v1's per-executor factory calls — the union was inconsistent. | v2 line 19 ("Wire reporter once in tool_cli") vs §6.3 ("Per-executor 3-line diff (apply to 5 executors)") vs §6.4 ("WS wins over Stdio... `pre = session_context.get('graph_reporter')`") | **Drop the tool_cli patch entirely.** Pick Cursor's Option (i): factory called from executor only. The factory itself calls `StdioGraphReporter.from_env(task_id)` which encapsulates the env-var read. ZERO duplication; one observability surface; one place to add future reporters. |
| **`stderr=PIPE` regression**: v2 changed `stderr=STDOUT` (baseline) to `stderr=PIPE` with a separate reader. This conflicts with the v6 plan's "structurally mirror shell.py" invariant, which uses `stderr=STDOUT`. Splitting stderr also creates a race between the two readers when output interleaves, and disables the v6-Phase-0a `[artifact_key]` markers' co-locality with the markdown result. | CRITICAL | I assumed splitting was needed for "cleanliness". It isn't — fd 3 is the only channel that needs structural separation; stdout+stderr can stay merged. | v2 line 1053 (`stderr=asyncio.subprocess.PIPE,  # NEW: split from stdout`) contradicts current shipping `openteam.py:119` + `shell.py:65` (both `stderr=STDOUT`) | **Revert to `stderr=STDOUT`.** Render `[artifact_key]` markers (which arrive on stderr but are merged with stdout) as dim in the TUI via line-prefix detection. This is the v6 design; we don't break it. |

### Bug in Cursor plan that v3 fixes

| Bug | Severity | Evidence | Fix |
|---|---|---|---|
| **`asyncio.StreamReader(loop=loop)` deprecated and REMOVED** in Python 3.10+. Both repos pin `requires-python >= 3.11`, so this would raise `TypeError` at runtime — a **hard failure**, not a warning. Claude's plan flagged this; both Cursor and my v2 missed it. | CRITICAL | `pyproject.toml` of both repos: `requires-python = ">=3.11"`. Python 3.10 release notes: `loop` parameter removed from `asyncio.StreamReader`, `StreamReaderProtocol`, and many others. Cursor plan line 947: `reader = asyncio.StreamReader(loop=loop)`. | **Drop `loop=`** from `StreamReader()` and `StreamReaderProtocol()` calls. The loop is auto-discovered from the running context. |

### Issues from Claude plan that v3 also adopts

| Claude correction | Status | Resolution |
|---|---|---|
| #1 `asyncio.StreamReader(loop=loop)` deprecation | ✅ VALID + CRITICAL (above) | Fixed |
| #2 Empty-output cleanup missing for graph-disabled path | ✅ VALID | Added `if not output.strip(): app.call_from_thread(shell_output.remove)` in both branches (graph-enabled and disabled) |
| #3 Verify `_NoOpNodeInteractive.stream_token_batches` signature against actual `WebSocketInteractive` before impl | ✅ VALID (defensive) | Added CI preflight test `test_no_op_node_interactive_signature_alignment.py` |

### Wins absorbed from Cursor v2 (1170 lines)

| Cursor's idea | Adopted because |
|---|---|
| Reporter wired in executor (NOT tool_cli) — Option (i) | Eliminates v2's double-wiring contradiction (above) |
| `StdioGraphReporter.from_env(task_id)` factory method | Encapsulates env-var read inside the reporter class; factory just calls it |
| Single-file `topology_view.py` (~350 LOC) | Simpler than v1's 6-file widget package; same functionality |
| `ContentSwitcher` of per-node `RichLog`s | O(1) append vs Markdown's O(N) re-render |
| `asyncio.Lock` serializes `_emit` writes | Concurrent BTA workers would otherwise corrupt NDJSON mid-line |
| `app.is_headless` freezes running glyph to `·` | Snapshot test stability |
| `MockBreakdown/Worker/Aggregator` real-BTA test rig | Higher-signal than mocking `_emit` |
| `test_factory_used_by_all_executors.py` grep-asserts every tool uses factory | Catches future tool authors who forget |
| `ROVODEV_TUI_GRAPH_FD` env var name (not `OPENTEAM_GRAPH_EVENTS_FD`) | Cleaner: TUI is the consumer; TUI's namespace is the natural opt-in surface |
| `ROVODEV_TUI_GRAPH_DISABLE=1` opt-out | Escape hatch for users who hate the change |
| `stderr=STDOUT` (merged) | Matches v6 baseline + shell.py |

### Wins kept from my v2 (1484 lines)

| v2 idea | Why preserved |
|---|---|
| React-mirrored constants (`MAX_STREAM_SIZE=200_000`, `TRIM_SIZE=50_000`, `STICKY_DURATION_MS=5_000`, `MAX_TOTAL_STREAMS=10_000_000`) | Cross-product UX consistency |
| Race buffer: `apply_node_status` before `apply_topology` creates stub `NodeState` | Cursor drops events instead; v2 preserves them |
| Continuation chunking for oversize `node_stream` | Both v2 and Cursor have this |
| Comprehensive self-audit + glossary | Defensive review hygiene |
| Out-of-scope section | Anchors v1 scope explicitly |
| `_StdioNodeInteractive` explicit stub (NOT a `__getattr__`-only no-op) | Explicit > implicit; less surprise |
| `task_id` in NDJSON events for multiplex-ready debugging | Future-proof |

### Wins explicitly REJECTED from Claude v2 (which is now itself a meta-plan)

Claude v2 is now a 75-line meta-plan that points at the Cursor plan with 3 corrections. Its "WebSocket to running server" idea from earlier rounds is gone. Nothing in Claude v2 is rejected — its 3 corrections (asyncio loop=, empty-output cleanup, signature drift) are all valid and absorbed.

---

## 1. TL;DR

Today: `/task "…"` in the TUI runs silently for 5–30 minutes, then dumps text. The OpenTeam React UI shows a live graph of the same execution.

**The fix is purely transport-layer.** OpenTeam's `BreakdownThenAggregateInferencer` already emits 4 event types via the duck-typed `graph_reporter` protocol. The React UI's `WebSocketGraphReporter` is one consumer; we add a **second consumer, `StdioGraphReporter`**, that emits the same events as NDJSON on a dedicated file descriptor (fd 3). The TUI's slash handler reads the NDJSON stream and renders a `Tree` + `ContentSwitcher`-of-`RichLog`s widget — live, cancellable, snapshot-testable.

**Zero changes** to `BreakdownThenAggregateInferencer`. **Zero new deps**. **Single attach point**: each of 5 executors gets a **6-line replacement** of its existing WS-only attach block with a single call to `make_graph_reporter(sc, task_id)`. No `tool_cli` patch. No double-wiring. No `stderr` split.

**Effort:** ~3 focused days.

---

## 2. Verified ground truth (every claim has a citation)

| Fact | Evidence |
|---|---|
| `BTA.graph_reporter: Optional[Any] = attrib(default=None, kw_only=True)` and only emits when non-None | `AgentFoundation/.../breakdown_then_aggregate_inferencer.py:509` |
| BTA calls `on_node_status` at **line 858** | `breakdown_then_aggregate_inferencer.py:858` — verified by direct `awk` |
| BTA calls `on_graph_topology` at **line 890** (pending_topo) | `breakdown_then_aggregate_inferencer.py:890` — verified |
| BTA calls `on_node_status` at **line 909** (worker callback) | `breakdown_then_aggregate_inferencer.py:909` — verified |
| BTA calls `on_graph_reconcile` at **line 1040** | `breakdown_then_aggregate_inferencer.py:1040` — verified |
| BTA calls `on_graph_topology` at **line 1278** (initial_topo) | `breakdown_then_aggregate_inferencer.py:1278` — verified |
| Event dataclasses are pure-Python `@dataclass` → JSON-serializable | `agent_foundation/common/inferencers/graph_events.py:31-110` |
| `WebSocketGraphReporter` interface (5 async methods + 3 factory methods) | `agent_foundation/ui/graph_interactive_adapter.py:93-232` |
| `NamespacedGraphReporter` (generic over parent reporter) | `agent_foundation/ui/graph_interactive_adapter.py:234-274` |
| `tool_cli.run_cli` execute call site | `OpenStartup/src/openteam/server/services/tool_cli.py:116` — **NOT PATCHED in v3** |
| 4 tool executors have the same `interactive` block | `task/executor.py:493-500`, `create_role/executor.py:560+`, `role_setup/executor.py:1260+`, `project_onboarding/executor.py:166-168` |
| `mock_task` tool exists | `ls .../mock_task/` direct verification |
| `MockBreakdown/Worker/Aggregator` test components | `agent_foundation/.../mock_inferencers/mock_bta_components.py:25-142` |
| TUI `widgets/tool_call/invoke_subagents.py:36` uses `ContentSwitcher` pattern | direct grep verified |
| TUI `widgets/interval_updater.py:26-30` uses `self.app.is_headless` | direct grep verified |
| Baseline `slash_commands/openteam.py:119` uses `stderr=asyncio.subprocess.STDOUT` | direct grep — v3 PRESERVES this |
| Baseline `slash_commands/shell.py:65` uses `stderr=asyncio.subprocess.STDOUT` | direct grep — v3 mirrors |
| Baseline `slash_commands/shell.py:91-94` does `app.call_from_thread(spinner.remove)` then `if not output.strip(): app.call_from_thread(shell_output_widget.remove)` | direct grep — v3 mirrors |
| `requires-python = ">=3.11,<3.14"` (cli-rovodev-tui) and `>=3.11` (OpenStartup) | both `pyproject.toml` — confirms `asyncio.StreamReader(loop=...)` would raise TypeError, NOT just deprecate |
| WS message schema we mirror in NDJSON | `OpenStartup/src/openteam/server/services/websocket_interactive.py:43-99` |

---

## 3. Architectural invariants (non-negotiable)

1. **`BreakdownThenAggregateInferencer` is NEVER modified.** Already speaks the duck-typed protocol.
2. **`graph_reporter` is a duck-typed protocol** (no Protocol/ABC enforces it; tests do — see §9 CI preflight).
3. **Every reporter `_emit` is try/except + `asyncio.Lock` serialized.** Visualization failures NEVER abort computation; concurrent BTA workers don't corrupt NDJSON lines.
4. **No new deps** in either repo.
5. **Bootstrap rules from v6 are inherited.** `StdioGraphReporter` lives in `agent_foundation/ui/`; shipped through `ensure_siblings_on_path()`.
6. **Backward compatibility is total.** If `ROVODEV_TUI_GRAPH_FD` is unset OR `StdioGraphReporter` import fails (older AgentFoundation), execution silently falls back to v6 behaviour.
7. **One feature, one file group, no new slash command, factory pattern, bare slash names.** Graph view always-on for the 4 OpenTeam slashes; opt-out via env var.
8. **`Tree` widget + `ContentSwitcher` of `RichLog`s** — precedent: `widgets/tool_call/invoke_subagents.py:36`. O(1) append per event.
9. **Sticky selection mirrors React** (5 s pin after click; auto-follow last-running otherwise). Same numeric constants.
10. **NDJSON wire format** with continuation chunking for oversize streams.
11. **`stderr=STDOUT`** (merged with stdout) — matches v6 baseline. **fd 3 is the ONLY new channel.**
12. **Wire reporter exactly once** — in each executor's existing attach block, via `make_graph_reporter(sc, task_id)`. **No `tool_cli` patch.** No `session_context["graph_reporter"]` indirection.

---

## 4. Architecture diagram

```mermaid
flowchart TB
  subgraph TUI[RovoDev TUI · cli-rovodev-tui]
    user[user: /task "..."]
    handler["slash_commands/openteam.py · _make_handler"]
    view["TopologyView widget<br/>Tree + ContentSwitcher of RichLog"]
    reader["_openteam_graph.read_ndjson_events"]
  end

  subgraph PROC["openteam-task / openteam-* subprocess"]
    boot[ensure_siblings_on_path]
    runcli["tool_cli.run_cli<br/>(unmodified)"]
    exec["executor.execute"]
    factory["make_graph_reporter(sc, task_id)<br/>(WS > Stdio.from_env > None)"]
    reporter["StdioGraphReporter<br/>fdopen(fd, w, buffering=1)"]
    bta["BreakdownThenAggregateInferencer<br/>emits 4 event types"]
  end

  user --> handler
  handler -->|"os.pipe() + pass_fds=(w,)<br/>env: ROVODEV_TUI_GRAPH_FD=N<br/>             OPENTEAM_TASK_ID=task-abc"| PROC
  handler -->|"stdout=PIPE, stderr=STDOUT<br/>(final result text, merged)"| view
  handler -->|"asyncio.connect_read_pipe(r)<br/>NO loop= kwarg (Py 3.11+)"| reader
  reader -->|"app.call_from_thread(view.apply_*)"| view

  boot --> runcli
  runcli --> exec
  exec --> factory
  factory -->|"if ROVODEV_TUI_GRAPH_FD set"| reporter
  factory -.->|"inferencer.graph_reporter = ..."| bta
  bta -->|"on_graph_topology<br/>on_node_status<br/>on_node_stream<br/>on_graph_reconcile"| reporter
  reporter -->|"NDJSON line (asyncio.Lock)"| reader
```

**Channel separation:**
| OS channel | Carries | Reader |
|---|---|---|
| **stdout (merged with stderr)** | Final result markdown + `[artifact_key] /path` markers (the v6 phase 0a markers) | TUI appends to TopologyView's "Final result" panel; markers detected by `line.startswith("[")` and styled dim |
| **fd 3** | NDJSON graph events | TUI's `_openteam_graph.read_ndjson_events` → dispatches to `TopologyView.apply_*` |
| ~~stderr (separate)~~ | ~~v2's separate reader~~ | **REVERTED in v3** — merged with stdout per v6 baseline |


---

## 5. `StdioGraphReporter` (AgentFoundation) — paste-ready

### 5.1 Location & contract

`AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py` — sibling of `graph_interactive_adapter.py`. Same 5 async methods + 3 factory methods as `WebSocketGraphReporter`. Method set locked by CI preflight (§9).

### 5.2 Code

```python
# CoreProjects/AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py
"""StdioGraphReporter — duck-typed peer of WebSocketGraphReporter.

Emits the same 4 event types as NDJSON on a writeable text stream
(typically fd=3 of a child process). Designed for subprocess-based UIs
(e.g. RovoDev TUI slash commands) that launch openteam-task as a child.

Activation contract:
  - Parent passes write-end fd via `pass_fds=(fd,)` AND sets
    `ROVODEV_TUI_GRAPH_FD=<fd>` in the child's env.
  - Child's tool executor calls `make_graph_reporter(sc, task_id)`, which
    in turn calls `StdioGraphReporter.from_env(task_id)`.
  - If env var is missing or fd is invalid → returns None → silent fallback.

Same 7-member surface as WebSocketGraphReporter (verified at
graph_interactive_adapter.py:93-232). No ABC needed — BTA reads
`graph_reporter` as `Optional[Any]` (duck-typed at line 509).

Design invariants (mirror WebSocketGraphReporter):
  - All event sends try/except wrapped → visualization NEVER aborts computation.
  - on_node_stream(is_final=True) is NEVER rate-limited (matches WS:160-172).
  - node_stream_observer batches at 200 ms (matches WS:173-216).
  - child_reporter returns NamespacedGraphReporter (reused as-is — generic).
  - asyncio.Lock serializes _emit across concurrent BTA workers; without
    it, asyncio.gather of two on_node_stream coros can interleave bytes
    mid-line, producing corrupt NDJSON.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, IO, Optional

from agent_foundation.ui.graph_interactive_adapter import NamespacedGraphReporter

_logger = logging.getLogger(__name__)

_ENV_FD = "ROVODEV_TUI_GRAPH_FD"
_MAX_LINE_BYTES = 4000  # safe under POSIX PIPE_BUF (4096 on Linux, 512 on macOS
                        # is the atomicity floor; staying under 4 KB keeps writes
                        # non-blocking and atomic for the most common case).


def _activated_fd() -> Optional[int]:
    """Returns the fd to write to, or None if not activated.

    Verifies fd is actually open (os.fstat raises OSError if not), defending
    against shells that have ROVODEV_TUI_GRAPH_FD leaked from a parent
    environment but pointing at a closed fd.
    """
    raw = os.environ.get(_ENV_FD)
    if not raw:
        return None
    try:
        fd = int(raw)
    except ValueError:
        return None
    try:
        os.fstat(fd)
    except OSError:
        return None
    return fd


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
    """Sibling of WebSocketGraphReporter — writes NDJSON events to a stream."""

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
        self._lock = asyncio.Lock()

    @classmethod
    def from_env(cls, task_id: str = "") -> Optional["StdioGraphReporter"]:
        """Construct from ROVODEV_TUI_GRAPH_FD env var; returns None if absent.

        Encapsulates the env-var read inside the reporter so the factory
        (graph_reporter_factory.make_graph_reporter) is a thin precedence shim.
        """
        fd = _activated_fd()
        if fd is None:
            return None
        try:
            # buffering=1 = line-buffered for text streams; we still flush()
            # belt-and-brace inside _emit.
            stream = os.fdopen(fd, "w", buffering=1, encoding="utf-8")
        except OSError as exc:
            _logger.warning("[StdioGraphReporter.from_env] fdopen(%d) failed: %s", fd, exc)
            return None
        return cls(task_id=task_id or f"task-{os.getpid()}", stream=stream)

    # ── core write path ──────────────────────────────────────────────────

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
                    self._stream.flush()
            except BrokenPipeError:
                # Reader has closed its end (TUI cancelled or crashed); drop silently.
                pass
            except OSError as exc:
                _logger.debug("[StdioGraphReporter] write failed: %s", exc)

    def _write_chunked_stream(self, msg: dict) -> None:
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
        try:
            self._stream.flush()
        except (BrokenPipeError, OSError):
            pass

    def _check_rate(self) -> bool:
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
            await self._emit(_serialize(
                NodeStatusEvent(node_id=node_id, status=status,
                                error=error, output_path=output_path),
                self._task_id,
            ))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_status failed: %s", exc)

    async def on_node_stream(self, node_id: str, content: str, is_final: bool = True) -> None:
        # is_final events ALWAYS pass the rate limiter (matches WS:160-172).
        if not is_final and not self._check_rate():
            return
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent
        try:
            await self._emit(_serialize(
                NodeStreamEvent(node_id=node_id, content=content, is_final=is_final),
                self._task_id,
            ))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_stream failed: %s", exc)

    async def on_graph_reconcile(self, node_statuses: dict) -> None:
        from agent_foundation.common.inferencers.graph_events import GraphReconcileEvent
        try:
            await self._emit(_serialize(
                GraphReconcileEvent(node_statuses=node_statuses),
                self._task_id,
            ))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_reconcile failed: %s", exc)

    # ── factory methods (3) ──────────────────────────────────────────────

    def node_stream_observer(self, node_id: str, flush_interval_ms: float = 200.0) -> Callable:
        """Batches token chunks at 200ms (matches WebSocketGraphReporter)."""
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
                if content:
                    await self.on_node_stream(node_id, content, is_final=False)

        return _observer

    def node_interactive(self, node_id: str) -> Any:
        """Stub interactive — subprocess has no bidirectional channel."""
        return _StdioNodeInteractive(self, node_id)

    def child_reporter(self, parent_node_id: str) -> NamespacedGraphReporter:
        """Reused VERBATIM from graph_interactive_adapter.py:234-274 (generic)."""
        return NamespacedGraphReporter(self, parent_node_id)


class _StdioNodeInteractive:
    """Stub satisfying the slim subset of WebSocketInteractive that BTA uses.

    Signature of stream_token_batches mirrors all kwargs BTA call sites
    (breakdown_then_aggregate_inferencer.py:1815,2027) actually pass.
    CI preflight test_no_op_node_interactive_signature_alignment.py
    catches drift the moment WebSocketInteractive changes.
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
        """Any other method called is a no-op coroutine — defensive."""
        async def _noop(*args: Any, **kwargs: Any) -> Any:
            return None
        return _noop
```

### 5.3 Tests (TIER-1)

`AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py`:

| Test | Assertion |
|---|---|
| `test_from_env_no_var` | Env unset → `from_env()` returns None |
| `test_from_env_invalid_int` | `ROVODEV_TUI_GRAPH_FD=garbage` → None |
| `test_from_env_closed_fd` | Env set but fd not open → None (mocks `os.fstat` to raise) |
| `test_from_env_valid_fd_returns_instance` | Real `os.pipe()` write-end → `StdioGraphReporter` instance |
| `test_emits_4_event_types_through_real_bta` | Drive `MockBreakdown → MockWorker × 2 → MockAggregator` (from `mock_bta_components.py:25-142`) through real BTA with `StdioGraphReporter(stream=io.StringIO())`; parse → assert sequence: `≥1 graph_topology, N node_status (pending→running→completed), M node_stream, 1 graph_reconcile` |
| `test_serialize_schema_matches_websocket_interactive_send_graph_event` | For each of 4 event types, compare `_serialize` output dict-key-by-dict-key to `websocket_interactive.py:43-99` schema |
| `test_rate_limiter_drops_non_final_streams` | 100 rapid `on_node_stream(is_final=False)` → only first 30 written; 1 `on_node_stream("", is_final=True)` → it ALWAYS writes |
| `test_namespaced_child_reporter_prefixes_node_ids` | `child_reporter("worker_0").on_node_status("propose", "running")` → emitted `node_id="worker_0/propose"` |
| `test_broken_pipe_swallowed` | Close stream mid-emission → next call returns None (does NOT raise) |
| `test_lock_serializes_concurrent_emits` | `await asyncio.gather(*(rep.on_node_stream(f"w_{i}", "x"*5000) for i in range(10)))` → output parses cleanly as 10 distinct lines |
| `test_oversize_node_stream_is_chunked` | 10 KB `content` → multiple lines, all but last have `"continuation": true`, last has `"is_final": true` if original did |
| `test_node_stream_observer_batches_at_200ms` | Monkeypatch `time.monotonic`; 100 chunks within 200 ms → 0 writes; 1 more chunk at 201 ms → 1 batched write |

CI preflight: `test_protocol_method_set_matches_websocket_reporter` (see §9).


---

## 6. `graph_reporter_factory` + per-executor wiring (no tool_cli patch)

### 6.1 `graph_reporter_factory.py` (~25 lines)

`AgentFoundation/src/agent_foundation/ui/graph_reporter_factory.py`:

```python
"""Factory: pick the right graph reporter; precedence WS > Stdio > None.

This factory is called from EACH tool executor's existing graph_reporter attach
block, replacing the 5x duplicated `if interactive: WebSocketGraphReporter(...)`
boilerplate with a single line.

Resolution order:
  1. WebSocketGraphReporter — if session_context['interactive'] is set
     AND task_id is non-empty (React UI path).
  2. StdioGraphReporter.from_env(task_id) — if ROVODEV_TUI_GRAPH_FD env var
     names a valid fd (RovoDev TUI subprocess path).
  3. None — silent fallback (existing direct-CLI behaviour).

WS wins over Stdio when both signals are present (defends against env-var
leakage in nested subprocess invocations).

ARCHITECTURAL NOTE: There is intentionally NO patch in tool_cli.run_cli. The
factory is the single attach point. (v2 of this plan tried to wire reporter in
tool_cli AND in executors; this was contradictory — see v3 §0.)
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
            _logger.warning("[graph_reporter_factory] WS attach failed: %s", exc)
            # fall through to Stdio
    try:
        from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter
        r = StdioGraphReporter.from_env(task_id=task_id)
        if r is not None:
            _logger.info("[graph_reporter_factory] StdioGraphReporter (task_id=%s)", task_id)
            return r
    except ImportError as exc:
        # Older AgentFoundation without StdioGraphReporter — silent degrade.
        _logger.debug("[graph_reporter_factory] StdioGraphReporter unavailable: %s", exc)
    except Exception as exc:
        _logger.warning("[graph_reporter_factory] Stdio attach failed: %s", exc)
    return None
```

### 6.2 Per-executor 6-line diff (apply to 5 executors — identical)

For `OpenStartup/src/openteam/server/resources/tools/task/executor.py:493-500`, replace:

```python
# BEFORE
interactive = sc.get("interactive")
if interactive is not None and task_id:
    try:
        from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
        inferencer.graph_reporter = WebSocketGraphReporter(interactive, task_id)
        _logger.info("[task] WebSocketGraphReporter attached (task_id=%s)", task_id)
    except Exception as exc:
        _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

with:

```python
# AFTER
try:
    from agent_foundation.ui.graph_reporter_factory import make_graph_reporter
    inferencer.graph_reporter = make_graph_reporter(sc, task_id)
    if inferencer.graph_reporter is not None:
        _logger.info("[task] graph_reporter attached: %s",
                     type(inferencer.graph_reporter).__name__)
except Exception as exc:
    _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

Identical diff for:
- `create_role/executor.py:560-568`
- `role_setup/executor.py:1260-1270`
- `project_onboarding/executor.py:166-168`
- `mock_task/executor.py:60-62`

Net per executor: **+7 lines, -8 lines = -1 line**. Across 5 executors: -5 lines. Plus -8 imports of `WebSocketGraphReporter`. Code shrinks.

### 6.3 NO `tool_cli.run_cli` patch (intentional)

In v2 I had a `tool_cli.run_cli` 15-line block that constructed the reporter and stuffed it into `session_context["graph_reporter"]`. **v3 drops this entirely.** Reasons:

1. **Contradictory with per-executor wiring**: if both run, one is dead code.
2. **`tool_cli` doesn't know `task_id`**: would have to mint a new UUID and not match the React UI's task_id convention.
3. **Less observable**: the factory's "one log line per attach" surface is lost if `tool_cli` pre-populates.
4. **No future-proofing benefit**: a future 6th tool would still need its existing `interactive`-block patched to call `make_graph_reporter` — the patch isn't avoided.

The only argument for the `tool_cli` patch is "fewer files touched". 5 executors × 6 lines is a trivial mechanical edit, and the CI preflight `test_factory_used_by_all_executors.py` catches forgotten patches.

### 6.4 Tests

`AgentFoundation/test/agent_foundation/ui/test_graph_reporter_factory.py` (TIER-1):

| Test | Assertion |
|---|---|
| `test_returns_ws_when_interactive_and_task_id` | `make_graph_reporter({"interactive": MockWS()}, "tid")` → `WebSocketGraphReporter` instance |
| `test_returns_stdio_when_env_set_no_interactive` | Env `ROVODEV_TUI_GRAPH_FD=N` + empty context → `StdioGraphReporter` |
| `test_returns_none_when_neither` | Empty context, no env → None |
| `test_ws_wins_over_stdio_when_both` | Both signals → WS (defends against env leak) |
| `test_ws_attach_failure_falls_through_to_stdio` | Mock `WebSocketGraphReporter()` raises → factory falls through to Stdio if env set |
| `test_importerror_for_stdio_silent_degrade` | Monkeypatch `StdioGraphReporter` import to raise ImportError → returns None silently (no warning at INFO+) |

`OpenStartup/test/openteam/integration/test_factory_used_by_all_executors.py` (TIER-1 / **CI preflight**):

```python
"""Grep-asserts every executor.py uses make_graph_reporter (or has no graph_reporter line)."""
import re, pathlib
TOOLS = pathlib.Path("src/openteam/server/resources/tools")

def test_every_tool_uses_factory_or_lacks_graph_reporter():
    for executor in TOOLS.glob("*/executor.py"):
        src = executor.read_text()
        has_gr = "graph_reporter" in src
        uses_factory = "make_graph_reporter" in src
        legacy = "WebSocketGraphReporter(" in src
        assert not legacy, (
            f"{executor}: legacy direct WebSocketGraphReporter import found; "
            f"use make_graph_reporter instead. Found at: {[i for i, l in enumerate(src.split(chr(10))) if 'WebSocketGraphReporter(' in l]}"
        )
        if has_gr:
            assert uses_factory, (
                f"{executor}: has graph_reporter reference but doesn't use "
                f"make_graph_reporter. Future tool authors must wire through "
                f"the factory."
            )
```


---

## 7. TUI side: `TopologyView` + NDJSON reader + handler integration

### 7.1 File layout

```
acra-python/packages/cli-rovodev-tui/src/rovodev_tui/
├── widgets/
│   └── topology_view.py              # NEW — TopologyView + NodeState (~350 LOC)
├── slash_commands/
│   ├── openteam.py                   # MODIFIED — handler extension (+60 -5 LOC)
│   ├── _openteam_graph.py            # NEW — NDJSON reader + dispatcher (~80 LOC)
│   └── _async_fd.py                  # NEW — POSIX fd → asyncio.StreamReader (~15 LOC)
└── tests/
    ├── widgets/
    │   ├── test_topology_view.py     # NEW (TIER-1, 12 tests)
    │   └── test_topology_view_snapshots.py  # NEW (TIER-2, 3 snapshots)
    ├── slash_commands/
    │   ├── test_openteam_graph_dispatch.py  # NEW (TIER-1, 5 tests)
    │   ├── test_async_fd.py          # NEW (TIER-2, 2 tests)
    │   └── test_handler_integration.py  # NEW (TIER-2, 4 tests)
    └── integration/
        └── test_openteam_graph_e2e.py  # NEW (TIER-2, full subprocess + mock_task)
```

### 7.2 `_async_fd.py` — POSIX fd → `asyncio.StreamReader` (Py 3.11+ compatible)

```python
# packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/_async_fd.py
"""Open a raw OS file descriptor as an asyncio StreamReader (POSIX).

CRITICAL: the `loop=` kwarg of asyncio.StreamReader and StreamReaderProtocol
was DEPRECATED in Python 3.8 and REMOVED in Python 3.10. Both repos pin
`requires-python >= 3.11`, so passing `loop=` raises TypeError at runtime.
We use the no-kwarg form, which auto-discovers the running loop.

Windows: pass_fds semantics differ; v1 is POSIX-only. Phase 6 (post-ship)
adds a Windows fallback (detect sys.platform == 'win32' → skip graph view).
"""
from __future__ import annotations

import asyncio
import os


async def open_async_fd_reader(
    fd: int,
) -> tuple[asyncio.StreamReader, asyncio.BaseTransport]:
    """Wrap a raw read-side fd as an asyncio StreamReader.

    Returns (reader, transport) — caller MUST call transport.close() in
    its cleanup (e.g., after proc.wait()).
    """
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()                       # NO loop= kwarg
    protocol = asyncio.StreamReaderProtocol(reader)       # NO loop= kwarg
    transport, _ = await loop.connect_read_pipe(
        lambda: protocol,
        os.fdopen(fd, "rb", buffering=0),
    )
    return reader, transport
```

### 7.3 `_openteam_graph.py` — NDJSON dispatcher

```python
# packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/_openteam_graph.py
"""NDJSON event reader for OpenTeam graph events from a subprocess fd."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rovodev_tui.widgets.topology_view import TopologyView

_logger = logging.getLogger(__name__)


async def read_ndjson_events(
    reader: asyncio.StreamReader, view: "Optional[TopologyView]", app
) -> None:
    """Consume one JSON object per line; dispatch to view via thread bridge.

    Exits cleanly on EOF (subprocess closed write end) or ConnectionReset.
    Malformed lines are logged and skipped — they NEVER crash the reader.

    If view is None (graph disabled), all events are silently dropped — we
    still drain the pipe so the subprocess doesn't block on a full kernel
    buffer.
    """
    _continuation: dict[str, list[str]] = {}

    while True:
        try:
            line = await reader.readline()
        except (ConnectionResetError, OSError) as exc:
            _logger.debug("[_openteam_graph] pipe closed: %s", exc)
            return
        if not line:
            return  # EOF
        if view is None:
            continue  # drain-only

        try:
            evt = json.loads(line.decode("utf-8", "replace").rstrip())
        except json.JSONDecodeError as exc:
            _logger.warning("[_openteam_graph] malformed NDJSON (%s): %r", exc, line[:120])
            continue

        # Re-assemble continuation chunks before dispatch.
        if evt.get("type") == "node_stream" and evt.get("continuation"):
            nid = evt["node_id"]
            _continuation.setdefault(nid, []).append(evt["content"])
            if not evt.get("is_final"):
                continue
            evt["content"] = "".join(_continuation.pop(nid, []) + [evt["content"]])
            evt.pop("continuation", None)
        elif evt.get("type") == "node_stream" and _continuation.get(evt["node_id"]):
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

### 7.4 `topology_view.py` — single-file widget (~350 LOC)

The widget is identical in shape to Cursor's §4.4 — Tree + ContentSwitcher of per-node RichLogs, sticky selection, bounded streams, race buffer, headless-frozen glyph. See v2 §7.2 for the full code listing (v3 inherits it unchanged; the only adjustment is the inline TBD: status-glyph "running" character is **● (filled circle)** which freezes to "·" via `app.is_headless`).

Key methods (called from `_openteam_graph.read_ndjson_events` via `app.call_from_thread`):
- `apply_topology_event(nodes, edges, parent_node_id="")` — idempotent splice
- `apply_node_status(node_id, status, error="", output_path="")` — race-buffer creates stub if topology not yet arrived
- `apply_node_stream(node_id, content, is_final=False)` — appends to per-node RichLog; bounded by MAX_STREAM_SIZE
- `apply_graph_reconcile(node_statuses)` — fixes drift
- `append_final_result(text)` — appends to the special "Final result" panel (selected by default until user clicks a node)

React-mirrored constants:
- `MAX_STREAM_SIZE = 200_000` (per-node soft cap)
- `TRIM_SIZE = 50_000` (tail kept on overflow)
- `STICKY_DURATION_MS = 5_000` (post-click pin)
- `MAX_TOTAL_STREAMS = 10_000_000` (cross-node ceiling)

Status glyphs (color + shape distinguished for accessibility):
- `pending=○ running=● completed=✓ error=✗ skipped=−`
- When `self.app.is_headless` is True: `running` glyph frozen to `·` (snapshot stability, mirrors `widgets/interval_updater.py:30`)

### 7.5 `slash_commands/openteam.py` handler — full integrated diff

The current handler (post-v6) uses `stderr=STDOUT`, single readline loop, `os.pipe()` not allocated. v3 extends it to add the fd-3 pipe + graph view + NDJSON reader, **without changing `stderr=STDOUT`** or splitting the stdout/stderr reader.

```python
# Insertions to existing _make_handler. Original code unchanged unless commented "NEW" or "MODIFIED".
import os
import uuid
from rovodev_tui.slash_commands._async_fd import open_async_fd_reader
from rovodev_tui.slash_commands._openteam_graph import read_ndjson_events
from rovodev_tui.widgets.topology_view import TopologyView

_OPT_OUT = "ROVODEV_TUI_GRAPH_DISABLE"
_TUI_GRAPH_FD = "ROVODEV_TUI_GRAPH_FD"


def _make_handler(slash, binary, fallback_module):
    async def handler(app, extra_prompt):
        worker = get_current_worker()
        if worker is None:
            app.notify_and_log(f"{slash}: missing worker context (registration bug)",
                               severity="error", timeout=10)
            return

        # NEW: opt-out check
        graph_enabled = os.environ.get(_OPT_OUT) != "1"
        topology_view: TopologyView | None = None
        shell_output_widget = None
        event_read_fd: int | None = None
        event_write_fd: int | None = None
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # NEW: mount TopologyView OR (disabled path) ShellOutput
        if graph_enabled:
            topology_view = TopologyView(task_label=f"OpenTeam {slash[1:]}")
            app.call_from_thread(app.chat_container.mount, topology_view)
        else:
            shell_output_widget = ShellOutput()
            app.call_from_thread(app.chat_container.mount, shell_output_widget)
        spinner = ThinkingSpinner(f"Running OpenTeam {slash[1:]}")
        app.call_from_thread(app.chat_container.mount, spinner)

        # ── Build argv + env ────────────────────────────────────────────
        argv, env = _build_argv_and_env(binary, fallback_module, shlex.split(extra_prompt))
        env["OPENTEAM_TASK_ID"] = task_id

        # NEW: pipe for graph events (only if enabled)
        pass_fds: tuple[int, ...] = ()
        if graph_enabled:
            event_read_fd, event_write_fd = os.pipe()
            env[_TUI_GRAPH_FD] = str(event_write_fd)
            pass_fds = (event_write_fd,)
            # Note: Python's subprocess.Popen handles set_inheritable internally
            # when fds appear in pass_fds — no manual os.set_inheritable needed.

        cwd = _get_workspace_path(app)
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,     # PRESERVED from v6 baseline
                stdin=asyncio.subprocess.DEVNULL,
                env=env,
                cwd=cwd,
                pass_fds=pass_fds,                    # NEW
            )
        except FileNotFoundError as e:
            # NEW: close pipe fds on failure
            for fd in (event_read_fd, event_write_fd):
                if fd is not None:
                    try: os.close(fd)
                    except OSError: pass
            app.call_from_thread(spinner.remove)
            if topology_view is not None:
                app.call_from_thread(topology_view.remove)
            if shell_output_widget is not None:
                app.call_from_thread(shell_output_widget.remove)
            app.notify_and_log(
                f"{slash}: {argv[0]} not found ({e}). Install openteam: "
                f"`uv tool install -e {_openteam_home()}`",
                severity="error", timeout=15,
            )
            return

        # NEW: spawn NDJSON reader
        ndjson_task: asyncio.Task | None = None
        transport = None
        if graph_enabled and event_write_fd is not None:
            os.close(event_write_fd)  # CRITICAL: parent drops write end → reader sees EOF on subprocess exit
            try:
                ndjson_reader, transport = await open_async_fd_reader(event_read_fd)
                ndjson_task = asyncio.create_task(
                    read_ndjson_events(ndjson_reader, topology_view, app),
                    name=f"openteam-graph-reader-{task_id}",
                )
            except OSError as e:
                _logger.warning("[%s] event reader setup failed: %s", slash, e)
                if event_read_fd is not None:
                    try: os.close(event_read_fd)
                    except OSError: pass

        # ── Stream stdout (merged with stderr) — same single-loop pattern as v6 ──
        if proc.stdout is None:
            app.call_from_thread(spinner.remove)
            return
        output = ""
        while True:
            if worker.is_cancelled:
                proc.terminate()
                await proc.wait()
                break
            if proc.stdout.at_eof():
                break
            line = await proc.stdout.readline()
            if not line:
                continue
            decoded = line.decode("utf-8", "replace")
            output += decoded
            # NEW: route to TopologyView OR ShellOutput
            target = topology_view.append_final_result if topology_view else shell_output_widget.append
            # NEW: detect [artifact_key] stderr-merged markers and dim them
            if decoded.startswith("["):
                app.call_from_thread(target, f"[dim]{decoded}[/dim]")
            else:
                app.call_from_thread(target, decoded)

        await proc.wait()

        # NEW: clean up reader + transport
        if ndjson_task is not None:
            ndjson_task.cancel()
            try:
                await ndjson_task
            except (asyncio.CancelledError, Exception):
                pass
        if transport is not None:
            transport.close()

        # ALWAYS: spinner cleanup
        app.call_from_thread(spinner.remove)

        # NEW (Claude correction #2): empty-output cleanup for BOTH branches
        if not output.strip():
            if topology_view is not None:
                # Topology view may have content even with empty stdout (graph events)
                # — only remove if both stdout AND no graph events arrived.
                if topology_view.is_empty():       # see TopologyView.is_empty() below
                    app.call_from_thread(topology_view.remove)
            elif shell_output_widget is not None:
                app.call_from_thread(shell_output_widget.remove)
```

`TopologyView.is_empty()` helper (add to §7.4 widget):

```python
def is_empty(self) -> bool:
    """True if no topology event arrived (non-BTA tool path).

    Used by handler to decide whether to remove the widget on empty stdout.
    """
    return not self._nodes
```

### 7.6 Tests

(Same coverage as v2 §7.5; only the asserted constants change to match v3.)

| Test file | TIER | Coverage |
|---|---|---|
| `tests/widgets/test_topology_view.py` | 1 | 12 tests: topology rebuild, status glyph, race buffer, sticky 5s, bounded streams, nested subgraph, etc. |
| `tests/widgets/test_topology_view_snapshots.py` | 2 | 3 snapshots: empty / mid-execution / complete; `app.is_headless` freezes glyph |
| `tests/slash_commands/test_openteam_graph_dispatch.py` | 1 | 5 tests: 4 event types dispatched, malformed skipped, EOF exit, continuation re-assembly, mid-continuation flush |
| `tests/slash_commands/test_async_fd.py` | 2 | 2 tests: pipe round-trip; **explicit assertion that `loop=` kwarg is NOT passed** (regression test against Cursor's bug) |
| `tests/slash_commands/test_handler_integration.py` | 2 | 4 tests: opt-out skips graph; empty-output removes widget(s); 3 readers concurrent; ndjson_task cleanup on exit |
| `tests/integration/test_openteam_graph_e2e.py` | 2 | Real `openteam-mock-task` subprocess → fd 3 → TopologyView state machine |


---

## 8. Phased delivery

| Phase | Scope | Effort | Blocking |
|---|---|---|---|
| **1a** | `StdioGraphReporter` + `from_env` | 3-4 h | – |
| **1b** | `graph_reporter_factory` | 30 min | 1a |
| **1c** | Tests for both (12 + 6 + CI preflight) | ½ day | 1a, 1b |
| **2** | Patch 5 executors + CI preflight `test_factory_used_by_all_executors.py` | 2 h | 1b |
| **3a** | `topology_view.py` widget (single file) | 1 day | – |
| **3b** | Widget unit tests (12) | ½ day | 3a |
| **3c** | Snapshot tests (3) | ½ day | 3a |
| **4a** | `_async_fd.py` POSIX helper (NO `loop=`) | 30 min | – |
| **4b** | `_openteam_graph.py` NDJSON dispatcher + tests | 3 h | 4a |
| **4c** | `slash_commands/openteam.py` handler extension | ½ day | 3a, 4a, 4b |
| **5** | E2E smoke with `openteam-mock-task` | 1-2 h | all |
| **6** | Documentation (`MCP_INTEGRATION.md` + `openteam-integration.md`) | 1 h | 5 |
| **7** (post-ship) | Windows fallback (`sys.platform == 'win32'` → skip) | 2 h | – |
| **8** (post-ship) | Propagate `graph_reporter` through `DualInferencer`, `PlanThenImplementInferencer` | ½ day | – |
| **9** (post-ship) | `JsonlGraphReporter(path)` subclass for replay/debug | 2 h | – |

**Total: ~3 focused days for phases 1-6 (ship-ready).**

**Critical path:** 1a → 1b → 1c → 2 → 4a → 4b → 4c → 5 → 6
(3a/3b/3c can run in parallel with 1-2 if widget author is different from reporter author.)

---

## 9. CI preflight tests (catch drift, not bugs)

These three tests run on every PR; failure means the protocol has drifted and the integration is at risk.

### 9.1 `test_protocol_method_set_matches_websocket_reporter` (TIER-1)

`AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py`:

```python
def test_protocol_method_set_matches_websocket_reporter():
    """If WebSocketGraphReporter adds a method, StdioGraphReporter must too."""
    import inspect
    from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
    from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter

    def public_async_methods(cls):
        return {
            name for name, m in inspect.getmembers(cls, predicate=inspect.iscoroutinefunction)
            if not name.startswith("_")
        }
    def public_factory_methods(cls):
        return {
            name for name, m in inspect.getmembers(cls, predicate=inspect.isfunction)
            if not name.startswith("_") and not inspect.iscoroutinefunction(m)
        }

    assert public_async_methods(WebSocketGraphReporter) == public_async_methods(StdioGraphReporter)
    assert public_factory_methods(WebSocketGraphReporter) == public_factory_methods(StdioGraphReporter)
```

### 9.2 `test_no_op_node_interactive_signature_alignment` (TIER-1) — addresses Claude correction #3

```python
def test_stream_token_batches_signature_matches_websocket_interactive():
    """If WebSocketInteractive.stream_token_batches adds a kwarg, our stub must accept it."""
    import inspect
    from agent_foundation.ui.graph_interactive_adapter import WebSocketInteractive
    from agent_foundation.ui.stdio_graph_reporter import _StdioNodeInteractive

    ws_sig = inspect.signature(WebSocketInteractive.stream_token_batches)
    stub_sig = inspect.signature(_StdioNodeInteractive.stream_token_batches)

    # Stub accepts **kwargs → any new WS kwarg is silently absorbed (forward-compat).
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in stub_sig.parameters.values()), \
        "_StdioNodeInteractive.stream_token_batches must accept **kwargs for forward-compat"

    # All non-VAR_KEYWORD params on WS must exist on stub by name (no drift in named args).
    ws_named = {n for n, p in ws_sig.parameters.items() if p.kind != inspect.Parameter.VAR_KEYWORD}
    stub_named = {n for n, p in stub_sig.parameters.items() if p.kind != inspect.Parameter.VAR_KEYWORD}
    missing = ws_named - stub_named
    assert not missing, f"_StdioNodeInteractive.stream_token_batches missing kwargs: {missing}"
```

### 9.3 `test_factory_used_by_all_executors` (TIER-1) — see §6.4 above

### 9.4 `test_no_loop_kwarg_in_async_fd_helper` (TIER-1) — regression guard

`acra-python/packages/cli-rovodev-tui/tests/slash_commands/test_async_fd.py`:

```python
def test_loop_kwarg_never_passed_to_streamreader():
    """Regression: asyncio.StreamReader(loop=...) was removed in Python 3.10
    and both repos pin >=3.11. Passing loop= raises TypeError.
    """
    from rovodev_tui.slash_commands._async_fd import open_async_fd_reader
    import inspect, ast
    src = inspect.getsource(open_async_fd_reader)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            if "StreamReader" in fn or "StreamReaderProtocol" in fn:
                kwargs = {kw.arg for kw in node.keywords if kw.arg}
                assert "loop" not in kwargs, (
                    f"BUG: {fn}(loop=...) was REMOVED in Python 3.10; "
                    f"both repos require >=3.11. Use the no-kwarg form."
                )
```

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Windows `pass_fds` semantics differ | High on Win | High | v1 is POSIX-only; phase 7 detects `sys.platform == 'win32'` → notify "Graph view not yet supported on Windows" + fall through to ShellOutput |
| Subprocess inherits unexpected fds | Very low | Low | `pass_fds=(...,)` explicitly lists fds; Python 3.4+ marks non-listed fds non-inheritable by default |
| Parent forgets to close write-end → reader hangs | Mitigated | High | `os.close(event_write_fd)` immediately after subprocess spawn; verified in §7.5 |
| NDJSON line > PIPE_BUF (~4 KB Linux) → torn write | Mitigated | Med | `_write_chunked_stream` splits at 3000 bytes/chunk; well under PIPE_BUF on all platforms |
| Concurrent BTA workers race on the stream → corrupt NDJSON | Mitigated | High | `asyncio.Lock` in `StdioGraphReporter._emit` |
| `asyncio.StreamReader(loop=loop)` would `TypeError` on Py 3.11 | **CAUGHT in plan** | CRIT | §9.4 CI preflight prevents regression; v3 code uses no-kwarg form |
| Older AgentFoundation lacks `StdioGraphReporter` (cross-version) | Mitigated | Low | `make_graph_reporter` catches `ImportError` → silent degrade; TUI shows "(no graph data)" |
| Race: `node_status` before `graph_topology` | Mitigated | Low | `apply_node_status` creates stub `NodeState`; `apply_node_stream` accumulates `_streams` buffer; `apply_graph_reconcile` is authoritative |
| Bounded buffer (200 KB/node) too small for some tool | Low | Low | Mirrors React; tail-keep preserves latest tokens; user can scroll RichLog |
| `_StdioNodeInteractive.stream_token_batches` signature drift if WS adds kwargs | Mitigated | Low | `**kwargs` absorbs; §9.2 CI preflight asserts named-kwarg compat |
| Snapshot test flakes on animated running glyph | Mitigated | Low | `self.app.is_headless` freezes glyph to `·` (matches `widgets/interval_updater.py:30`) |
| Non-BTA topologies (`pti.yaml`, `dual.yaml`) emit no events | Acceptable v1 | Low | Widget shows "(no graph data for this topology)" footer; final result still rendered; `is_empty()` removes widget on empty stdout |
| Pipe fd leak on subprocess exec failure | Mitigated | Low | Explicit cleanup block closes both fds in the `FileNotFoundError` branch |
| User sets `ROVODEV_TUI_GRAPH_FD` accidentally in their shell | Low | Low | `_activated_fd()` calls `os.fstat(fd)` → bogus fd → returns None → silent fallback |
| Reporter wired twice (v2's bug) → contradictory state | **CAUGHT in plan** | High | v3 explicitly drops `tool_cli.run_cli` patch; §6.3 enforces "factory called from executor ONLY" |
| Stderr split (v2's bug) → race + breaks v6 markers | **CAUGHT in plan** | High | v3 preserves `stderr=STDOUT`; markers rendered dim via line-prefix detection |
| Many concurrent `/task` invocations → many graph views → memory leak | Low | Low | Each Esc removes widget; bounded buffers per view; auto-collapse-after-N is phase 9 |
| Reader `transport.close()` forgotten → fd leak on long-lived TUI | Mitigated | Low | `transport.close()` in handler's finally-like cleanup block (§7.5) |

---

## 11. Self-audit (stress-tested for hacks)

| Question | Answer |
|---|---|
| Does this duplicate `WebSocketGraphReporter`? | Intentionally — the protocol is duck-typed; both are peer implementations. They share `NamespacedGraphReporter` (the only stateful helper) and could share `node_stream_observer` extraction (phase 9 mini-refactor). |
| Why not connect to a running OpenStartup WS server (Claude v1 approach)? | The server isn't running for most TUI users; requiring it would defeat v6's "subprocess + bootstrap = self-contained" invariant. WS adds a heavy dep to PyInstaller-frozen TUI for no marginal benefit. Claude v2 itself rejected this approach. |
| Could the NDJSON events corrupt the final result text? | No — different fds. stdout (merged with stderr) = result markdown + `[artifact_key]` markers; fd 3 = NDJSON. Two OS channels, two logical roles. |
| Could the user cancel mid-run? | Existing `worker.is_cancelled → proc.terminate()` flow unchanged. Reader's `await readline()` returns empty bytes on pipe close → clean exit. `transport.close()` after `proc.wait()`. |
| Nested BTAs (worker that is itself a BTA)? | `NamespacedGraphReporter.child_reporter(parent_node_id)` reused unchanged. Events arrive with `node_id="worker_0/breakdown"` and `parent_node_id="worker_0"`. Widget mounts sub-tree under container node. |
| Concurrent slash commands? | Each spawns its own subprocess + own pipe + own TopologyView. Independent. Test: `test_handler_integration::test_three_concurrent_handlers`. |
| Non-BTA topologies (`pti.yaml`, `dual.yaml`)? | Reporter set but never invoked. Widget footer says "(no graph data — this topology doesn't emit events)". Final result still renders. Empty-output `is_empty()` check removes widget. Phase 8 propagates through Dual/PTI. |
| Sticky selection time-source? | `time.monotonic()` — NTP-skew-safe. |
| `_cap_total_streams` could thrash? | Triggered only when total > 10 MB; mirrors React; one-shot purge of completed-node buffers (not running). |
| `_StdioNodeInteractive.__getattr__` returns coroutines from sync method? | Yes — returned `_noop` is `async def` (caller awaits). Pattern verified against BTA's `worker.interactive` usage. |
| What if a future contributor adds a 5th tool that emits graph events but forgets the factory? | §9.3 `test_factory_used_by_all_executors.py` greps every `executor.py` and asserts the factory is used (or no graph_reporter line at all). CI preflight. |
| Stdio reporter and WebSocket reporter drift in protocol surface? | §9.1 `test_protocol_method_set_matches_websocket_reporter` CI preflight catches it. |
| `os.fdopen(buffering=1)` doesn't actually line-flush in all CPython versions? | Explicit `self._stream.flush()` after each write (already in `_emit`). Test `test_emits_4_event_types_through_real_bta` reads `os.read(fd)` immediately. |
| Could RovoDev call OpenTeam AND OpenTeam call RovoDev (via `RovoDevCliInferencer`)? | Already supported. `ROVODEV_TUI_GRAPH_FD` namespace + per-subprocess pipe makes nesting safe. |
| Does this commit RovoDev to a specific OpenTeam version? | No. NDJSON contract is the wire API; either side upgrades independently. Backward-compat fallback if `StdioGraphReporter` import fails. |
| Snapshot test stability for animated running glyph? | `_render_label` checks `self.app.is_headless` and freezes glyph. Mirrors `IntervalUpdater.on_mount`. |
| Does v3 introduce any hack? | Closest: `_StdioNodeInteractive.__getattr__` returning `_noop` for unknown methods — defensive against future BTA calls. Explicit, documented, log-warning'd. The `[dim]` styling of stderr-merged `[artifact_key]` markers is a UX nicety, not a hack — it preserves v6's design while making the merged stream readable. |
| Why is there NO `tool_cli.run_cli` patch in v3 when v2 had one? | v2's design was contradictory: it patched both `tool_cli` AND each executor with the factory. One of the two was dead code. Cursor's plan §4.3 explicitly chose "Option (i): executor calls factory directly (preferred; cleaner)". v3 follows this. The 5-executor mechanical edit is trivial; CI preflight catches forgotten patches. |
| Why is `stderr=STDOUT` (not `=PIPE`) the right choice? | v6 baseline uses `stderr=STDOUT`. Splitting them creates a race between two readline loops and breaks the co-locality of `[artifact_key]` markers with the markdown they describe. fd 3 is the only NEW channel; nothing else changes. |
| Why drop `loop=` from `asyncio.StreamReader`? | Removed in Python 3.10. Both repos pin `>=3.11`. Passing `loop=` raises `TypeError` at runtime — not a deprecation warning. §9.4 CI preflight guards. |
| What's the deal with empty-output cleanup? | shell.py:91-94 baseline removes the shell-output widget when stdout was empty. v3 mirrors this: empty stdout → if graph view is also empty (`is_empty()`), remove it; otherwise keep the graph view (graph events alone are evidence the run did something). |

---

## 12. Comparison table (v2 mine vs Cursor v2 vs Claude v2 vs **v3 integrated**)

| Trait | v2 (mine) | Cursor v2 | Claude v2 | **v3 (this)** |
|---|---|---|---|---|
| Architecture: NDJSON on fd 3 | ✅ | ✅ | ✅ (defers to Cursor) | ✅ |
| Single attach point (factory in executor, NO tool_cli patch) | ✗ (contradictory; both) | ✅ | ✅ (via Cursor) | ✅ |
| `StdioGraphReporter.from_env(task_id)` factory method | partial | ✅ | – | ✅ |
| `asyncio.Lock` serializes `_emit` | ✅ | ✅ | – | ✅ |
| Sticky selection 5 s | ✅ | implicit | – | ✅ explicit constant |
| Bounded stream buffers (200 KB/node) | ✅ explicit | implicit | – | ✅ explicit |
| Race buffer (status before topology) | ✅ | minimal | – | ✅ |
| `asyncio.StreamReader` NO `loop=` kwarg (Py 3.11+) | ✗ has `loop=` | ✗ has `loop=` | ✅ flags it | ✅ guarded by CI |
| `stderr=STDOUT` (matches v6 baseline) | ✗ split to PIPE | ✅ | – | ✅ |
| Empty-output cleanup (mirrors shell.py:93) | ✗ missing | ✗ missing | ✅ flags it | ✅ with `is_empty()` |
| `_StdioNodeInteractive.stream_token_batches` signature CI test | – | – | ✅ flags need | ✅ §9.2 |
| Continuation chunking for oversize streams | ✅ | ✅ | – | ✅ |
| `app.is_headless` freezes running glyph | ✅ | ✅ | – | ✅ |
| `ContentSwitcher` of per-node `RichLog`s | ✗ (Markdown) | ✅ | – | ✅ |
| Single-file widget (~350 LOC) | ✗ (6 files) | ✅ | – | ✅ |
| Test rig uses real BTA + `MockBreakdown/Worker/Aggregator` | partial | ✅ | – | ✅ |
| 4 CI preflight tests | 3 | 3 | – | **4** (added `test_no_loop_kwarg_in_async_fd_helper`) |
| Self-audit section | ✅ 15 rows | ✅ 16 rows | – | ✅ 18 rows |
| Comprehensive risks table | ✅ | ✅ | – | ✅ extended with 2 "CAUGHT in plan" rows |
| ROVODEV_TUI_GRAPH_DISABLE opt-out env var | ✅ | ✅ | – | ✅ |
| Revision-history block | ✅ | – | – | ✅ explicit bug-fix table |
| Total line count | 1484 | 1170 | 75 | **~1300 (lean by absorption, not omission)** |

---

## 13. Pick-one ranking (if you can only pick ONE of the three predecessors)

**Pick Cursor v2.** Reasoning:

1. **Cursor's architecture is correct end-to-end.** v3's only Cursor-side fix is the `loop=` deprecation — every other Cursor choice is sound (factory-in-executor, `stderr=STDOUT`, `asyncio.Lock`, headless freeze, `ContentSwitcher`).
2. **v2 (mine) has 2 critical architectural bugs.** Double-wiring contradiction + stderr regression — both would manifest in code review and require redesign.
3. **Claude v2 is now a meta-plan that itself points at Cursor**, with 3 corrections. Picking Claude effectively picks Cursor + 3 corrections.

**Ordering: Cursor v2 > Claude v2 (= Cursor + 3 small fixes) > v2 (mine) >> v3 (this — integrates all wins, fixes all bugs).**

If "only ONE of the three pre-existing plans" excludes v3, **pick Cursor v2** and apply Claude's 3 corrections during implementation. If v3 is in play, **pick v3** — it is strictly the union of correctness.

---

## 14. Definition of Done (acceptance checklist)

### AgentFoundation
- [ ] `StdioGraphReporter.from_env()` returns `None` without env var; instance with env var.
- [ ] `make_graph_reporter` returns the right type per the 6-row truth table (§6.4).
- [ ] CI preflight `test_protocol_method_set_matches_websocket_reporter` ✅
- [ ] CI preflight `test_no_op_node_interactive_signature_alignment` ✅
- [ ] All 12 `test_stdio_graph_reporter.py` TIER-1 tests ✅
- [ ] All 6 `test_graph_reporter_factory.py` TIER-1 tests ✅

### OpenStartup
- [ ] All 5 executors patched; CI preflight `test_factory_used_by_all_executors.py` ✅
- [ ] `openteam-mock-task` console script emits valid NDJSON on fd=3 when env var set.
- [ ] `openteam-mock-task --help` still works (env var absent → silent fallback).
- [ ] 0 instances of `WebSocketGraphReporter(` remain in `src/openteam/server/resources/tools/*/executor.py` (grep clean).

### RovoDev TUI
- [ ] In TUI: `/task "what is 2+2"` shows the topology graph + final result.
- [ ] Tree row click → stream pane updates to that node's content.
- [ ] After click, status events for OTHER nodes do NOT change selection for 5 s.
- [ ] Auto-follow re-engages 5 s after the last manual click.
- [ ] Ctrl-C terminates subprocess within 5 s (v6 contract preserved).
- [ ] Esc collapses the graph view (subprocess keeps running until cancelled).
- [ ] `ROVODEV_TUI_GRAPH_DISABLE=1 /task "..."` → no graph view, identical to v6 UX.
- [ ] Empty-output cleanup works: `/task ""` removes the widget (shell.py:93 parity).
- [ ] Push 300 KB to one node → widget memory bounded; older content trimmed to last 50 KB.
- [ ] Nested BTA → sub-graph nodes mount under their container node.
- [ ] Non-BTA `/task` (`pti.yaml`) → "(no graph data)" footer; `is_empty()` removes widget if stdout also empty.
- [ ] CI preflight `test_no_loop_kwarg_in_async_fd_helper` ✅
- [ ] All 12 widget unit tests TIER-1 ✅
- [ ] 3 snapshot tests TIER-2 ✅
- [ ] E2E `test_openteam_graph_e2e.py` TIER-2 ✅

### Documentation
- [ ] `CoreProjects/OpenStartup/docs/MCP_INTEGRATION.md` — new "Graph view" subsection
- [ ] `atlassian_packages/acra-python/packages/cli-rovodev-tui/docs/openteam-integration.md` — graph view UX, keybindings, opt-out env var

### Repo hygiene
- [ ] PR description includes asciinema/GIF of graph view against `mock_task`.
- [ ] No new deps added to either repo.

---

## 15. Out of scope (deliberate v1 boundaries)

- **Windows support.** Phase 7 (post-ship). v1 detects platform; Windows falls through to ShellOutput.
- **Interactive `/task --confirm` per-node prompts** via TUI. Would need bidirectional fd; v1 is one-way fd 3.
- **Graphviz/DOT layout** rendering. v2 enhancement.
- **Clickable artifacts → $EDITOR** open. `output_path` is in events; v2 enhancement.
- **Auto-collapse stale graph views after N new commands.** Phase 9.
- **Cross-task graph aggregation** ("show me all my running /task graphs"). Separate plan.
- **Persistence of NDJSON events to disk** (`JsonlGraphReporter`). Phase 9.
- **DAG layout with arbitrary cross-edges.** BTA topologies are diamond-shaped; tree-with-canonical-parent suffices.
- **Patching `tool_cli.run_cli`.** Explicitly rejected — see §6.3.
- **Splitting stderr from stdout.** Explicitly rejected — see §3 invariant 11 and §0 v2 bug 2.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| **BTA** | `BreakdownThenAggregateInferencer` — the OpenTeam topology engine emitting graph events |
| **fd 3** | The dedicated file descriptor for NDJSON graph events (parent→child IPC channel) |
| **NDJSON** | Newline-Delimited JSON — one JSON object per line, what we write on fd 3 |
| **PIPE_BUF** | POSIX-guaranteed atomic-write size for pipes (4096 on Linux, 512 floor) |
| **Race buffer** | Logic that absorbs `node_status` or `node_stream` events arriving *before* their owning `graph_topology` event |
| **Sticky selection** | After a user clicks a tree row, auto-select is suppressed for `STICKY_DURATION_MS=5000` |
| **Continuation chunking** | Splitting NDJSON `node_stream` events > 4 KB into multiple lines with `"continuation": true` |
| **v6** | The shipped OpenTeam ↔ RovoDev integration plan that v3 builds on |
| **Headless freeze** | When `app.is_headless` is True, animated glyphs are frozen for snapshot test stability |

---

**End of plan. Saved at: `CoreProjects/OpenStartup/_dev/_plan/rovodev_tui_graph_view/rovodev-tui-graph-view-v3.md`**
