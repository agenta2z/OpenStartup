# Chapter 2 — F2: User Input Queue

> **Implements:** F2 from `README.md`
> **Depends on:** none (foundation for F3, F5, F6)
> **Touches:** `ConversationalInferencer`, `InteractiveBase` adapters

---

## 1. Goal

Replace `ConversationalInferencer`'s single-slot blocking
`interactive.aget_input()` call with a unified `asyncio.Queue[QueueItem]`
that the loop pulls from one item at a time. Items can arrive from:

- **User messages** (WebSocket, CLI, etc.) — wrapped as `UserMessage`
- **Background job completions** — wrapped as `BackgroundJobComplete`
- **Fork triggers** — wrapped as `ForkTrigger`
- **Scheduled ticks** (rare; used for periodic SOP re-evaluation) — `ScheduledTick`

This is the **foundation** that unlocks F3 (background jobs), F5 (SOP runs),
and F6 (running-jobs prompt block). Without an injectable queue, none of those
features can deliver async events back to the running agent.

---

## 2. Current State

### 2.1 Where input is consumed today

In `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py`:

```python
# Single conversation tool path (~line 1100):
async def _handle_conversation_tool(self, tool, assistant_text, interactive_override=None):
    ...
    await active_interactive.asend_response(text, flag=PendingInput, input_mode=mode)
    user_input = await active_interactive.aget_input()   # ← single-slot await
    ...
```

The agent **blocks here** until exactly one input arrives. If a background
event happens (job completes) while the agent is awaiting, the event has
nowhere to land — `aget_input()` returns ONE thing.

### 2.2 InteractiveBase contract

`AgentFoundation/src/agent_foundation/ui/interactive_base.py`:

```python
class InteractiveBase:
    def get_input(self) -> Any: ...
    async def aget_input(self) -> Any: ...
    def send_response(self, response, flag): ...
    async def asend_response(self, response, flag): ...
```

Concrete subclasses (`WebUIInteractive`, `QueueInteractive`, `CLIInteractive`):
- have their own internal asyncio.Queue or buffer
- `aget_input()` does `await self._input_queue.get()`

But this `_input_queue` is **private to the transport** — there's no way for
the inferencer to inject things into it, and no way to differentiate item
types (everything's a raw string or dict).

### 2.3 Why "compound widget" doesn't solve this

Today's "compound widget" / `GroupedWidget` lets the LLM emit multiple
conversation tools in one turn. The resolution is still ONE await: the user
fills all widgets, hits Submit, the queue gets one composite response. That's
fine for synchronous multi-input collection but doesn't help with **async
inbound events** during a single turn.

---

## 3. Design

### 3.1 The `QueueItem` tagged union

`AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/input_queue.py` (new):

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
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ForkTrigger:
    """Request to fork the current conversation into a new branch."""
    kind: Literal["fork_trigger"] = "fork_trigger"
    parent_session_id: str = ""
    seed_message: str = ""              # initial user message in the fork
    inherited_context: dict[str, Any] = field(default_factory=dict)
    reason: str = ""                    # why we're forking (job completion / explicit /fork)


@dataclass
class ScheduledTick:
    """Periodic wake-up so the agent can re-evaluate its SOP next step."""
    kind: Literal["scheduled_tick"] = "scheduled_tick"
    note: str = ""


QueueItem = Union[UserMessage, BackgroundJobComplete, ForkTrigger, ScheduledTick]
```

### 3.2 The `ConversationalInputQueue` wrapper

```python
import asyncio
from typing import Optional


class ConversationalInputQueue:
    """A FIFO queue of QueueItem with priority hooks.

    All public methods are coroutines (or thread-safe sync where labeled)
    so background tasks running in arbitrary executors can push safely.
    """

    def __init__(self, *, maxsize: int = 0):
        self._q: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=maxsize)
        self._closed = False
        # Used to signal "drain everything that's already enqueued without
        # blocking" in the loop's drain-step (§3.4 step 6).
        self._drain_event = asyncio.Event()

    async def push(self, item: QueueItem) -> None:
        if self._closed:
            raise RuntimeError("queue is closed")
        await self._q.put(item)

    def push_threadsafe(self, item: QueueItem, loop: asyncio.AbstractEventLoop) -> None:
        """Push from a non-asyncio thread (used by JobManager schedule loop)."""
        loop.call_soon_threadsafe(self._q.put_nowait, item)

    async def get(self) -> QueueItem:
        return await self._q.get()

    def get_nowait(self) -> Optional[QueueItem]:
        try:
            return self._q.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def qsize(self) -> int:
        return self._q.qsize()

    def close(self) -> None:
        self._closed = True
```

### 3.3 Wiring into `ConversationalInferencer`

Add an attribute and a getter:

```python
@attrs(slots=False)
class ConversationalInferencer(InferencerBase):
    ...
    user_input_queue: ConversationalInputQueue = attrib(
        factory=ConversationalInputQueue, kw_only=True,
    )
```

For backward compat, the existing `interactive.aget_input()` path is preserved
as the **default source** that feeds the queue. We add an adapter:

```python
async def _interactive_to_queue_adapter(self) -> None:
    """Pumps inputs from self.interactive into self.user_input_queue.

    Runs as a background task started by run_agentic_loop.
    """
    if self.interactive is None:
        return
    try:
        while True:
            raw = await self.interactive.aget_input()
            if raw is None:
                continue
            # Lift raw payload to a UserMessage. The transport may have already
            # given us a structured dict (widget response); preserve as metadata.
            if isinstance(raw, dict):
                content = raw.get("content") or raw.get("text") or ""
                meta = {k: v for k, v in raw.items() if k not in {"content", "text"}}
            else:
                content = str(raw)
                meta = {}
            await self.user_input_queue.push(UserMessage(content=content, metadata=meta))
    except asyncio.CancelledError:
        pass
```

This adapter is **the only consumer of `interactive.aget_input()`** going
forward. All other code reads from `user_input_queue` exclusively.

### 3.4 The new agentic loop step structure

In `run_agentic_loop`, the **per-iteration block** changes:

```python
# Start the input adapter (idempotent)
if self._adapter_task is None or self._adapter_task.done():
    self._adapter_task = asyncio.create_task(self._interactive_to_queue_adapter())

# Each iteration:
for iteration in range(self.max_iterations):
    # (Steps 1-4 unchanged: compress, render prompt, call LLM, parse)
    ...

    if conv_response.has_conversation_tool and self.user_input_queue is not None:
        collected = await self._handle_conversation_tools(...)
        # _handle_conversation_tools internally awaits self.user_input_queue.get()
        # instead of interactive.aget_input()
        ...

    # NEW Step 6: drain any background-event items that arrived during this turn
    drained: list[QueueItem] = []
    while True:
        item = self.user_input_queue.get_nowait()
        if item is None: break
        drained.append(item)

    # Process drained items: append BackgroundJobComplete / ForkTrigger as
    # synthetic [System] messages to conversation history so the next turn's
    # rendered prompt includes them.
    for item in drained:
        self._inject_queue_item_into_history(item)
```

### 3.5 `_inject_queue_item_into_history`

```python
def _inject_queue_item_into_history(self, item: QueueItem) -> None:
    """Convert a QueueItem into a synthetic 'system' message for the LLM."""
    if isinstance(item, BackgroundJobComplete):
        text = (
            f"[Background job completed]\n"
            f"job_id: {item.job_id}\n"
            f"kind: {item.job_kind}\n"
            f"cmdline: {item.cmdline}\n"
            f"status: {item.exit_status}\n"
            f"workspace: {item.workspace}\n"
            f"summary: {item.summary}\n"
            f"You can view full output at: {item.workspace}/stdout.log "
            f"(stderr at {item.workspace}/stderr.log)."
        )
        self.add_message("system", text)
    elif isinstance(item, ForkTrigger):
        # Fork triggers are handled separately (chapter 3 §3.7) — they don't
        # get injected into THIS inferencer's history; they create a new
        # session. If we see one here, log a warning (it should have been
        # routed by JobManager).
        logger.warning("ForkTrigger received in inferencer's drain; expected JobManager routing.")
    elif isinstance(item, ScheduledTick):
        self.add_message("system", f"[Scheduled tick] {item.note}")
    elif isinstance(item, UserMessage):
        # Shouldn't appear in drain (consumed by tool collection step)
        # but if it does (e.g., user typed while waiting for non-input action),
        # treat as a follow-up turn.
        self.add_message("user", item.content)
```

### 3.6 Updating `_handle_conversation_tool` to read the queue

```python
async def _handle_conversation_tool(self, tool, assistant_text, interactive_override=None):
    ...
    await active_interactive.asend_response(text, flag=PendingInput, input_mode=mode)

    # NEW: read from queue, filter to UserMessage. Non-user items get
    # buffered for the post-tool drain step.
    while True:
        item = await self.user_input_queue.get()
        if isinstance(item, UserMessage):
            user_input = item.content if not item.metadata else {**item.metadata, "content": item.content}
            break
        else:
            # Buffer non-user items; the drain step will process them after the
            # tool resolution completes.
            self._pending_async_items.append(item)
    ...
```

Where `self._pending_async_items: list[QueueItem]` is a new `init=False`
attrib initialized to `[]`. The drain step (§3.4 Step 6) prepends these to
its `drained` list.

### 3.7 YOLO mode interaction (preview)

When `self.yolo_mode=True` (defined in chapter 4):

```python
async def _handle_conversation_tool(self, tool, assistant_text, ...):
    if self.yolo_mode and not self._gate_is_must(tool):
        # Skip widget rendering; auto-resolve with the SOP-provided default
        return self._yolo_auto_resolve(tool)
    # ... otherwise normal queue-based path
```

Full YOLO logic is in chapter 4. Mentioned here so the input queue change
is forward-compatible.

---

## 4. Concurrency Safety

### 4.1 Push concurrency

`asyncio.Queue.put()` is coroutine-safe within one event loop. For pushes
from **threads** (e.g., `JobManager`'s schedule loop running in a thread for
`time.sleep` between scheduled ticks), use `push_threadsafe(item, loop)`
which goes through `loop.call_soon_threadsafe(q.put_nowait, item)`.

For pushes from **other processes** (e.g., subprocess SOP runner's
completion), the JobManager (process-wide singleton) translates the
completion message (received via a Unix socket or pipe) into a queue push
on the parent process's event loop.

### 4.2 Loop ordering invariants

| Source | Order guarantee |
|--------|-----------------|
| Same coroutine pushing N items | Preserved (asyncio.Queue is FIFO) |
| Different coroutines | Best-effort FIFO by `put()` call time |
| Background thread via `push_threadsafe` | FIFO with same-event-loop pushes that happen-after the scheduling tick |
| Across process boundary | FIFO of arrival at the JobManager's IPC socket; small skew possible |

For agent-correctness, only **within-session FIFO** matters. The LLM sees
items in arrival order through the synthetic `[Background job completed]`
messages.

### 4.3 What about starvation?

If 100 background jobs all complete in 1 second while the agent is mid-turn,
the drain step (§3.4 Step 6) processes all of them BEFORE the next render.
The result is ONE big batch of `[System]` messages prepended to the next
prompt. This is intentional: the LLM sees the full picture each turn rather
than a slow trickle. Context compression (existing) handles the volume.

If even one batch overflows the prompt budget: §5 below.

---

## 5. Context-Budget Interaction

Today, `_compress_context_if_needed()` is called at the top of each
iteration. After §3.4 Step 6 adds N system messages, the next iteration's
compression may need to be more aggressive. Mitigation:

- Tag the synthetic `[Background job completed]` messages with a special
  `system_subtype="bg_completion"` field.
- `AgenticDynamicContext.compress()` (existing) gains a rule: when budget
  pressure is high, collapse all `bg_completion` messages older than 3 turns
  into a single "(N earlier background jobs completed — workspaces at: …)"
  summary line.

Implementation: existing context.py needs a small hook (1 file, ~30 lines).

---

## 6. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/input_queue.py` | NEW. `QueueItem` types + `ConversationalInputQueue` wrapper. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` | Add `user_input_queue` attrib, `_pending_async_items`, `_adapter_task` attribs. Add `_interactive_to_queue_adapter`. Update `_handle_conversation_tool` to read from queue. Add `_inject_queue_item_into_history`. Modify `run_agentic_loop` to start adapter + drain queue per iteration. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/context.py` | Optional: `bg_completion` summary rule in `compress()`. |
| `tests/agent_foundation/.../conversational/test_input_queue.py` | NEW. See §7. |

**No changes to `InteractiveBase` subclasses** — the adapter pumps existing
`aget_input()` into the queue. Old transports keep working unchanged.

---

## 7. Test Plan

| # | Test | Type |
|---|------|------|
| T2.1 | `ConversationalInputQueue` FIFO order for sync pushes | Unit |
| T2.2 | `push_threadsafe` from worker thread → queue receives correct item | Unit |
| T2.3 | `_interactive_to_queue_adapter` lifts dict & str inputs to UserMessage | Unit |
| T2.4 | `_inject_queue_item_into_history` produces expected system text for each variant | Unit |
| T2.5 | run_agentic_loop with 2 jobs completing mid-turn → next render contains both `[System]` messages | Integration |
| T2.6 | run_agentic_loop with conversation tool: only UserMessage consumed at await; non-user items buffered to drain | Integration |
| T2.7 | Backward compat: existing single-user-input flow works unchanged when no background events fire | Integration |
| T2.8 | Adapter task is cancelled on inferencer shutdown | Unit |

---

## 8. Open Questions

1. **Maxsize for the queue?** Default `0` (unbounded). If we ever fear
   runaway background jobs flooding memory, set a per-session limit.
2. **Should `UserMessage` arriving during a non-input action (i.e., between
   turns) interrupt the LLM?** No — the queue is consumed at well-defined
   points (turn start + tool-input await). The user just sees their message
   processed at the next safe boundary. UI can render "typing → waiting →
   sent" states.
3. **Persistence across process restart?** Queue is in-memory. On restart,
   the JobManager re-emits pending `BackgroundJobComplete` items by reading
   each job's `meta.json` (chapter 3 §4.3 covers rehydration).

---

*Continued in `03_background_jobs.md`.*
