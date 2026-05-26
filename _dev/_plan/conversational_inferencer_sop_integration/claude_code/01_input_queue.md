# Chapter 1 -- F1: Input Queue

> **Author:** Claude Code
> **Implements:** F1 from `README.md`
> **Depends on:** none (foundation for F3, F4, F5, F6)
> **Touches:** `ConversationalInferencer`, `InteractiveBase` adapters, `AgenticDynamicContext`

---

## 1. Goal

Replace `ConversationalInferencer`'s single-slot blocking
`interactive.aget_input()` call with a unified `asyncio.Queue[QueueItem]`
that the loop pulls from one item at a time. Items can arrive from:

- **User messages** (WebSocket, CLI, etc.) -- wrapped as `UserMessage`
- **Background job completions** -- wrapped as `BackgroundJobComplete`
- **Fork triggers** -- wrapped as `ForkTrigger`
- **Scheduled ticks** (rare; for periodic SOP re-evaluation) -- `ScheduledTick`

This is the **foundation** that unlocks F3 (background jobs), F5 (SOP runs),
and F6 (running-jobs prompt block). Without an injectable queue, none of those
features can deliver async events back to the running agent.

---

## 2. Current State

### 2.1 Where input is consumed today

In `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py`:

```python
# ~line 1033:
async def _handle_conversation_tool(self, tool, assistant_text, interactive_override=None):
    ...
    await active_interactive.asend_response(
        assistant_text,
        flag=InteractionFlags.PendingInput,
        input_mode=input_mode,
        prompt_data=_prompt_data,
    )
    user_input = await active_interactive.aget_input()   # <-- single-slot await
    ...
```

The agent **blocks here** until exactly one input arrives. If a background
event happens (job completes) while the agent is awaiting, the event has
nowhere to land -- `aget_input()` returns ONE thing.

### 2.2 InteractiveBase contract

`AgentFoundation/src/agent_foundation/ui/interactive_base.py`:

```python
class InteractiveBase:
    def get_input(self) -> Any: ...
    async def aget_input(self) -> Any: ...
    def send_response(self, response, flag): ...
    async def asend_response(self, response, flag): ...
```

Concrete subclasses (`WebUIInteractive`, `QueueInteractive`, `CLIInteractive`)
have their own internal asyncio.Queue or buffer. But this internal queue is
**private to the transport** -- there is no way for the inferencer to inject
items into it, and no way to differentiate item types (everything is a raw
string or dict).

### 2.3 Current agentic loop structure

The loop in `run_agentic_loop()` (~line 133) iterates:

1. Compress dynamic context if needed
2. Render prompt via `_render_prompt(content)`
3. Call LLM (streaming or non-streaming)
4. Parse response -- extract tool calls
5. Execute tool calls via `_execute_tool_call()`
6. If conversation tool detected: `_handle_conversation_tool()` blocks on input
7. Update `_dynamic_context` with `CompletedAction`
8. Loop

Step 6 is the bottleneck. While waiting for user input, background events
(job completions, fork triggers) have no delivery path.

---

## 3. Design

### 3.1 The `QueueItem` tagged union

New file: `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/input_queue.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal, Union
from datetime import datetime, timezone


@dataclass
class UserMessage:
    """Input from a human user via any transport."""
    kind: Literal["user_message"] = "user_message"
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class BackgroundJobComplete:
    """A background job (tool / command / SOP) finished."""
    kind: Literal["bg_job_complete"] = "bg_job_complete"
    job_id: str = ""
    job_kind: str = ""           # "tool" | "command" | "sop"
    cmdline: str = ""
    workspace: str = ""
    exit_status: str = ""        # "success" | "failed" | "cancelled" | "timeout"
    summary: str = ""            # short LLM-readable summary
    fork_on_completion: bool = False
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ForkTrigger:
    """Request to fork the current conversation into a new branch."""
    kind: Literal["fork_trigger"] = "fork_trigger"
    parent_session_id: str = ""
    seed_message: str = ""
    inherited_context: dict[str, Any] = field(default_factory=dict)
    reason: str = ""             # why we're forking


@dataclass
class ScheduledTick:
    """Periodic wake-up so the agent can re-evaluate its SOP next step."""
    kind: Literal["scheduled_tick"] = "scheduled_tick"
    note: str = ""


QueueItem = Union[UserMessage, BackgroundJobComplete, ForkTrigger, ScheduledTick]
```

**Design rationale:** Using `@dataclass` with a `kind` literal discriminator
rather than class hierarchy. This keeps serialization trivial (each dataclass
has `kind` for dispatch), and the `Union` type lets static checkers verify
exhaustive matching.

### 3.2 The `ConversationalInputQueue` wrapper

```python
import asyncio
from typing import Optional


class ConversationalInputQueue:
    """A FIFO queue of QueueItem with priority hooks.

    All public methods are coroutines (or thread-safe sync where labeled)
    so background tasks running in arbitrary executors can push safely.

    Lifecycle:
      - Created once per session (NOT per-turn).
      - Passed to ConversationalInferencer at construction.
      - Closed when session is torn down.
    """

    def __init__(self, *, maxsize: int = 0):
        self._q: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=maxsize)
        self._closed = False

    async def push(self, item: QueueItem) -> None:
        """Push an item from within the event loop."""
        if self._closed:
            raise RuntimeError("queue is closed")
        await self._q.put(item)

    def push_threadsafe(
        self, item: QueueItem, loop: asyncio.AbstractEventLoop
    ) -> None:
        """Push from a non-asyncio thread (used by JobManager schedule loop).

        Uses loop.call_soon_threadsafe to safely enqueue from external threads
        (e.g., the schedule engine's time.sleep-based loop running in a
        ThreadPoolExecutor).
        """
        loop.call_soon_threadsafe(self._q.put_nowait, item)

    async def get(self) -> QueueItem:
        """Block until an item is available."""
        return await self._q.get()

    def get_nowait(self) -> Optional[QueueItem]:
        """Non-blocking get. Returns None if queue is empty.

        Used by the drain step (Section 3.4 Step 7) to pull all pending
        items without blocking.
        """
        try:
            return self._q.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def qsize(self) -> int:
        return self._q.qsize()

    def close(self) -> None:
        """Mark closed. Further pushes raise RuntimeError."""
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed
```

### 3.3 Wiring into `ConversationalInferencer`

Add to the class definition (~line 81):

```python
@attrs(slots=False)
class ConversationalInferencer(InferencerBase):
    ...
    # --- Input queue (NEW) ---
    user_input_queue: Optional[ConversationalInputQueue] = attrib(
        default=None, kw_only=True,
    )
    # Adapter task pumping interactive -> queue
    _adapter_task: Optional[asyncio.Task] = attrib(default=None, init=False)
    _adapter_started: bool = attrib(default=False, init=False)
    # Buffer for non-user items received while waiting for a UserMessage
    # in _handle_conversation_tool (Section 3.6)
    _pending_async_items: list = attrib(factory=list, init=False)
```

**Backward compatibility:** When `user_input_queue` is `None` (the default),
the inferencer uses the legacy `interactive.aget_input()` path directly.
No behavior change for existing callers that do not pass a queue.

### 3.4 The `_interactive_to_queue_adapter`

This coroutine is the **sole consumer** of `interactive.aget_input()` going
forward. All other inferencer code reads from `user_input_queue` exclusively.

```python
async def _interactive_to_queue_adapter(self) -> None:
    """Pump inputs from self.interactive into self.user_input_queue.

    Runs as a background task. Started once per session (idempotent).
    The adapter is session-scoped, NOT per-turn, because run_agentic_loop
    is called per-turn by the server. A per-turn adapter would race on
    interactive.aget_input().
    """
    if self.interactive is None or self.user_input_queue is None:
        return
    try:
        while not self.user_input_queue.closed:
            raw = await self.interactive.aget_input()
            if raw is None:
                continue
            # Lift raw payload to a UserMessage.
            if isinstance(raw, dict):
                content = raw.get("content") or raw.get("text") or ""
                meta = {k: v for k, v in raw.items()
                        if k not in {"content", "text"}}
            else:
                content = str(raw)
                meta = {}
            await self.user_input_queue.push(
                UserMessage(content=content, metadata=meta)
            )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning("Input adapter stopped: %s", e)
```

**Key constraint:** The adapter is **the only consumer** of
`interactive.aget_input()`. This prevents double-consumption races.

### 3.5 Modified agentic loop structure

In `run_agentic_loop()`, the per-iteration block gains two changes:

```python
async def run_agentic_loop(self, content, *, interactive=None, ...):
    effective_interactive = interactive or self.interactive

    # --- NEW: Start input adapter if queue is configured ---
    if (
        self.user_input_queue is not None
        and not self._adapter_started
        and effective_interactive is not None
    ):
        self._adapter_task = asyncio.create_task(
            self._interactive_to_queue_adapter()
        )
        self._adapter_started = True

    for iteration in range(self.max_iterations):
        # Steps 1-4 unchanged: compress, render, call LLM, parse
        ...

        # Step 5: Execute tool calls
        ...

        # Step 6: Handle conversation tools
        if conv_response.has_conversation_tool:
            # _handle_conversation_tool reads from queue (Section 3.6)
            ...

        # --- NEW Step 7: Drain async items ---
        if self.user_input_queue is not None:
            drained = list(self._pending_async_items)
            self._pending_async_items.clear()
            while True:
                item = self.user_input_queue.get_nowait()
                if item is None:
                    break
                drained.append(item)
            for item in drained:
                self._inject_queue_item(item)

        # Step 8: Update dynamic context with CompletedAction (existing)
        ...

    # --- NEW: Cleanup adapter on exit ---
    if self._adapter_task and not self._adapter_task.done():
        self._adapter_task.cancel()
        self._adapter_started = False
```

The drain step runs **after** tool execution and **before** the next
iteration's prompt render. This means background completions that arrived
during the current iteration are visible to the LLM on the very next render.

### 3.6 Modified `_handle_conversation_tool`

When the queue is available, the conversation tool handler reads from it
instead of directly from `interactive.aget_input()`:

```python
async def _handle_conversation_tool(
    self, tool, assistant_text, interactive_override=None
):
    active_interactive = interactive_override or self.interactive
    if active_interactive is None and self.user_input_queue is None:
        return None

    # Build input_mode, enrich with variable content (existing logic)
    input_mode = _build_input_mode(tool)
    ...

    # Send the widget/prompt to the user (existing)
    if active_interactive is not None:
        await active_interactive.asend_response(
            assistant_text,
            flag=InteractionFlags.PendingInput,
            input_mode=input_mode,
            prompt_data=_prompt_data,
        )

    # --- NEW: Read from queue if available ---
    if self.user_input_queue is not None:
        while True:
            item = await self.user_input_queue.get()
            if isinstance(item, UserMessage):
                user_input = (
                    item.content if not item.metadata
                    else {**item.metadata, "content": item.content}
                )
                break
            else:
                # Non-user items (BackgroundJobComplete, etc.) get buffered.
                # The drain step (Section 3.5 Step 7) processes them after
                # tool resolution completes.
                self._pending_async_items.append(item)
    else:
        # Legacy path: direct interactive read
        user_input = await active_interactive.aget_input()

    if user_input is None:
        return None

    # Process structured widget response (existing logic unchanged)
    ...
```

**Important:** Non-`UserMessage` items that arrive while waiting for user
input are NOT lost. They are buffered in `_pending_async_items` and consumed
by the drain step on the same iteration (before the next render).

### 3.7 `_inject_queue_item` -- converting items to context entries

```python
def _inject_queue_item(self, item: QueueItem) -> None:
    """Convert a drained QueueItem into a CompletedAction in _dynamic_context.

    Background completions enter _dynamic_context as CompletedAction
    (NOT as messages in _messages). This is a deliberate design choice:
    CompletedActions go through the existing compression pipeline
    (_compress_context_if_needed), avoiding the need for a parallel
    compression pathway for system messages.
    """
    if isinstance(item, BackgroundJobComplete):
        summary = (
            f"[Background job completed] "
            f"job_id={item.job_id}, kind={item.job_kind}, "
            f"status={item.exit_status}, "
            f"cmdline={item.cmdline}, "
            f"workspace={item.workspace}. "
            f"Summary: {item.summary}"
        )
        self._dynamic_context.add_action(
            tool="__background__",
            summary=summary,
        )

    elif isinstance(item, ForkTrigger):
        # Fork triggers are handled by ForkRouter (chapter 3 Section 3.7),
        # not by the inferencer. If one lands here, it was misrouted.
        logger.warning(
            "ForkTrigger in inferencer drain; expected JobManager routing. "
            "parent=%s reason=%s",
            item.parent_session_id, item.reason,
        )

    elif isinstance(item, ScheduledTick):
        self._dynamic_context.add_action(
            tool="__scheduled_tick__",
            summary=f"[Scheduled tick] {item.note}",
        )

    elif isinstance(item, UserMessage):
        # UserMessages should be consumed by _handle_conversation_tool,
        # not by the drain step. If one appears here, it means the user
        # typed while the agent was between turns (not waiting for input).
        # Append to _messages so the LLM sees it on next render.
        self._messages.append({
            "role": "user",
            "content": item.content,
        })
```

**Why CompletedAction, not _messages?**

The existing `AgenticDynamicContext` in
`AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/context.py`
supports incremental compression:

```python
class AgenticDynamicContext:
    completed_actions: list[CompletedAction]
    _compressed_history: str
    _uncompressed_actions: list[CompletedAction]

    def compress(self, compressed_text: str) -> None:
        self._compressed_history = compressed_text
        self._uncompressed_actions.clear()
```

By injecting background completions as `CompletedAction(tool="__background__")`,
they automatically participate in the compression pipeline. Injecting them as
`system`-role messages into `_messages` would bypass compression entirely and
require new template handling for `<system>` tags.

---

## 4. Concurrency Safety

### 4.1 Push concurrency

| Source | Mechanism |
|--------|-----------|
| Same event loop (adapter, inline push) | `asyncio.Queue.put()` -- coroutine-safe within one loop |
| External thread (JobManager schedule loop) | `push_threadsafe(item, loop)` via `loop.call_soon_threadsafe` |
| External process (SOP subprocess completion) | JobManager translates IPC signal into a queue push on the parent's loop |

### 4.2 Ordering guarantees

| Source | Order guarantee |
|--------|----------------|
| Same coroutine pushing N items | Preserved (asyncio.Queue is FIFO) |
| Different coroutines | Best-effort FIFO by `put()` call time |
| Background thread via `push_threadsafe` | FIFO with same-loop pushes that happen-after the scheduling tick |
| Across process boundary | FIFO of arrival at the JobManager IPC socket; small skew possible |

For agent-correctness, only **within-session FIFO** matters. The LLM sees
items in arrival order through the `CompletedAction` entries.

### 4.3 Starvation and batch draining

If 100 background jobs all complete in 1 second while the agent is mid-turn,
the drain step processes all of them BEFORE the next render. The result is
one batch of `CompletedAction` entries added to `_dynamic_context`. This is
intentional: the LLM sees the full picture each turn rather than a slow
trickle. The existing `_compress_context_if_needed()` handles the volume.

### 4.4 Adapter lifecycle

The adapter task is:
- **Started** once, on the first `run_agentic_loop()` call when
  `user_input_queue is not None` and `interactive is not None`.
- **Guarded** by `_adapter_started: bool` to prevent double-start across
  multiple `run_agentic_loop()` calls within the same session.
- **Cancelled** when `run_agentic_loop()` exits (either normally or on error).
- **Re-startable** if a new `run_agentic_loop()` call follows (the guard
  resets on cancel).

---

## 5. Context-Budget Interaction

Today, `_compress_context_if_needed()` is called at the top of each
iteration. After Step 7 adds N `CompletedAction` entries, the next
iteration's compression may need to be more aggressive. Two mitigations:

### 5.1 Background-completion summary rule

Add an optional rule to `AgenticDynamicContext.compress()`: when budget
pressure is high, collapse all `__background__` actions older than 3
iterations into a single summary line:

```
"(N earlier background jobs completed -- workspaces at: ..., ..., ...)"
```

This requires tagging `CompletedAction` entries with a `source` field
(or matching on `tool == "__background__"`). The existing compressor
already has a callback hook for custom summarization.

### 5.2 Hard cap on drain batch size

If `qsize() > 50` at drain time, process only the first 50 items and leave
the rest for next iteration. This prevents a pathological case where hundreds
of jobs complete simultaneously and blow the prompt budget in a single render.

---

## 6. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/input_queue.py` | NEW. `QueueItem` union types + `ConversationalInputQueue` wrapper. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` | Add `user_input_queue` attrib (Optional, default None). Add `_adapter_task`, `_adapter_started`, `_pending_async_items` internal attribs. Add `_interactive_to_queue_adapter()`. Add `_inject_queue_item()`. Update `_handle_conversation_tool()` to read from queue when available. Add drain step (Step 7) to `run_agentic_loop()`. Adapter lifecycle management. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/context.py` | Optional: add `source` field to `CompletedAction` for background-completion summary rule. |
| `tests/agent_foundation/.../conversational/test_input_queue.py` | NEW. See Section 7 test plan. |

**No changes to `InteractiveBase` subclasses.** The adapter pumps existing
`aget_input()` into the queue. Old transports keep working unchanged.

---

## 7. Test Plan

| # | Test | Type |
|---|------|------|
| T1.1 | `ConversationalInputQueue` FIFO order: push 5 items, get 5 items in same order | Unit |
| T1.2 | `push_threadsafe` from worker thread delivers correct item to queue within 100ms | Unit |
| T1.3 | `push()` on closed queue raises `RuntimeError` | Unit |
| T1.4 | `get_nowait()` returns `None` on empty queue (does not block) | Unit |
| T1.5 | `_interactive_to_queue_adapter` lifts `dict` inputs to `UserMessage` (preserves metadata keys not in `content`/`text`) | Unit |
| T1.6 | `_interactive_to_queue_adapter` lifts `str` inputs to `UserMessage(content=str_val, metadata={})` | Unit |
| T1.7 | `_inject_queue_item(BackgroundJobComplete)` creates `CompletedAction(tool="__background__")` in `_dynamic_context` | Unit |
| T1.8 | `_inject_queue_item(ScheduledTick)` creates `CompletedAction(tool="__scheduled_tick__")` in `_dynamic_context` | Unit |
| T1.9 | `_inject_queue_item(UserMessage)` appends to `_messages` with `role="user"` | Unit |
| T1.10 | `_inject_queue_item(ForkTrigger)` logs warning, does not modify `_dynamic_context` or `_messages` | Unit |
| T1.11 | Drain step: 2 `BackgroundJobComplete` items pushed during tool execution appear in `_dynamic_context` before next render | Integration |
| T1.12 | `_handle_conversation_tool` with queue: only `UserMessage` consumed at await; `BackgroundJobComplete` buffered to `_pending_async_items` | Integration |
| T1.13 | `_pending_async_items` are prepended to drain batch so they are processed in same iteration | Integration |
| T1.14 | Backward compat: existing single-user-input flow works identically when `user_input_queue is None` | Integration |
| T1.15 | Adapter task is cancelled when `run_agentic_loop()` exits normally | Unit |
| T1.16 | Adapter task is cancelled when `run_agentic_loop()` exits on exception | Unit |
| T1.17 | `_adapter_started` guard prevents double-start across sequential `run_agentic_loop()` calls | Unit |
| T1.18 | Batch drain cap: if 100 items queued, only first 50 processed per iteration (remainder on next) | Unit |

---

## 8. Cross-References

- **Chapter 3 (Background Jobs):** `JobManager` pushes `BackgroundJobComplete` into this queue on job completion (Section 3.3 `_on_completion`).
- **Chapter 4 (YOLO Mode):** When `yolo_mode=True`, conversation tools are auto-resolved before reaching the queue-based input path (Section 3.6).
- **Chapter 5 (SOP Lifecycle):** `/sop` subprocess completions flow through `JobManager` into this queue.
- **Chapter 6 (Prompt Integration):** The `## Running Background Jobs` template section reads live job state from `JobManager`, but the completion notifications come through this queue.
- **Chapter 7 (Scenarios):** Scenarios 2, 3, 6, and 7 exercise the drain step and background-completion injection.
- **Chapter 8 (Roadmap):** Phase A covers this chapter (PRs A.1 and A.2).

---

## 9. Open Questions

1. **Maxsize for the queue?** Default `0` (unbounded). If we ever fear
   runaway background jobs flooding memory, set a per-session configurable
   limit via env var `AGENT_INPUT_QUEUE_MAXSIZE`.

2. **Should `UserMessage` arriving between turns interrupt the LLM?** No.
   The queue is consumed at well-defined points (drain step + tool-input
   await). The user just sees their message processed at the next safe
   boundary. UI can render "typing -> waiting -> sent" states.

3. **Persistence across process restart?** Queue is in-memory only.
   On restart, JobManager re-emits pending `BackgroundJobComplete` items
   by reading each job's `meta.json` (chapter 3 Section 4.2 rehydration).

4. **Should we use `asyncio.PriorityQueue`?** Considered and rejected.
   Priority ordering adds complexity without clear benefit. The drain
   step processes all items in a batch anyway; the LLM sees them as a
   set, not a sequence. FIFO is sufficient.

5. **What about the `GroupedWidget` / compound widget path?** The existing
   compound-widget flow (multiple conversation tools in one turn resolved
   as one composite response) continues to work unchanged. The widget
   response arrives as a single `UserMessage` through the adapter. The
   queue does not decompose compound responses.

---

*Continued in `02_task_simple_mode.md`.*
