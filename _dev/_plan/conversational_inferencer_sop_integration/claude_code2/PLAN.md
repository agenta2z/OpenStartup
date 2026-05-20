# Conversational Inferencer × SOP Integration — Plan

> **Author:** Claude (Opus 4.7) under Tony Chen's direction
> **Date:** 2026-05-19
> **Status:** Proposal — Design + Phased Implementation
> **Scope:** Five interlocking features that turn the conversational inferencer
> into a multi-channel orchestrator capable of running SOPs autonomously, queueing
> user input, dispatching background jobs (scheduled / recurring), forking
> conversations from job completion, and shelling out to short-cycle "simple"
> task runs that bypass plan/review consensus.
>
> **Related work / hard dependency:**
> - `OpenStartup/_dev/_plan/workflow-as-first-class-citizen.md` (Rovo Dev, 2026‑05‑08)
>   — the workflow-as-tool catalog and `enter_workflow / exit_workflow / resume_workflow`
>   tool design. We extend it with user-facing slash aliases (`/enter-sop`,
>   `/exit-sop`, `/sop`) and add YOLO-mode-aware execution semantics.
> - `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/`
>   — the existing `ConversationalInferencer` (with `run_agentic_loop`,
>   `_execute_tool_call` already supporting `asynchronous=True` fire-and-forget).
> - `OpenStartup/src/openteam/server/services/conversation_service.py`
>   — `run_conversation_turn`, `_compute_session_context`, per-session JSONL
>   logging, the `_get_session_inferencer` cache.
> - `OpenStartup/src/openteam/server/resources/tools/task/` — the existing
>   `/task` tool, topology YAMLs (`single.yaml`, `pti-simple.yaml`, …).

---

## 0. TL;DR — Mental Model Shift

**Today** the conversational inferencer is a synchronous one-message-in /
one-message-out loop. Tools run inline; the only "async" path is fire-and-forget
notification to the frontend's task panel. The agent has no awareness of
background work, no queue of pending user input, no way to launch an
unsupervised SOP run, and no notion of "I am running in autonomous mode".

**Proposed** — five orthogonal capabilities, each independently shippable:

```
                ┌─────────────────────────────────────────────────────────┐
                │                ConversationalInferencer                 │
                │                                                         │
                │   ┌──────────────────────┐    ┌─────────────────────┐  │
   user msg ───►│   │   UserInputQueue     │───►│  run_agentic_loop   │  │
   bg-job done ►│   │  (FIFO + priority,   │    │  (existing)         │  │
   sop-result ─►│   │   per-session)       │    └──────────┬──────────┘  │
                │   └──────────────────────┘               │              │
                │                                          ▼              │
                │   ┌──────────────────────┐    ┌─────────────────────┐  │
                │   │   JobManager         │◄───┤  conversation tools │  │
                │   │  (per-session, on    │    │  + action tools     │  │
                │   │   disk; pid/sched)   │    └─────────────────────┘  │
                │   └──────┬───────────────┘                              │
                │          │  injects completion msgs                     │
                │          └──────────► back into UserInputQueue          │
                │                                                         │
                │   yolo: bool                                            │
                │   active_workflow_id (from workflow-first-class plan)   │
                └─────────────────────────────────────────────────────────┘

   /background-job task --simple "fix lint"            (queue a tool job)
   /background-job find ~ -name "*.py" --every 5m      (recurring command)
   /background-job /task ... --fork-on-completion      (job result spawns new session)
   /sop code_optimization                               (run SOP unsupervised in subprocess)
   /enter-sop code_optimization                         (active SOP in THIS conversation)
   /exit-sop                                            (drop back to free-form)
```

The **`task --simple` mode** becomes the cheapest possible code-execution
primitive (one RovoDevCLI/ClaudeCodeCLI leaf, implementation prompt only, no
plan/review), which makes "fire a task into the background" actually viable —
a full PTI + Dual run is too expensive and stateful to chain on every
background trigger.

---

## 1. Goals & Non-Goals

### 1.1 Goals

| #  | Goal | Why |
|----|------|-----|
| G1 | `/task --simple` (the new default) finishes in one inferencer round-trip with implementation-only prompt; workspace contains only streaming cache, args/input/response logs, and parsed output. | Today `/task` defaults to PTI+Dual consensus (minutes per call, two YAML hops). 90% of casual tasks don't need that. A cheap default unblocks G3/G4 below. |
| G2 | Conversational inferencer has a **user-input queue** so messages arriving while a turn is running are processed in order (FIFO). | Avoids today's race: every `process_message` competes for the same `_get_session_inferencer` and the second message can clobber the first's mid-turn state. |
| G3 | **Background jobs** can be launched via `/background-job <spec>`, where `<spec>` is either a registered tool (`task`, `create_role`, ...) or a free command line. Jobs run out-of-band; their completion injects a system message into the input queue. | Async parallelism (e.g., "while we keep chatting, run `grep` over the repo and tell me when it's done"). |
| G4 | Jobs support **scheduling** (`--at <ISO>`) and **recurrence** (`--every <duration>`). A `JobManager` records command, PID, start time, workspace path, and status. | First-class cron-in-the-agent; recurring jobs become "monitors" (e.g., "run the test suite every 5 minutes"). |
| G5 | `--fork-on-completion` causes the completion injection to be tagged `fork`; the queue runner spawns a **new session** forked from the current state at the fork point. | Lets the agent enqueue exploratory side-quests without polluting the main conversation history. |
| G6 | The conversational template gains a `## Running Background Jobs` section listing all in-flight jobs (auto-removed on completion). | Keeps the agent aware of its pending side-work; prevents duplicate launches. |
| G7 | A **YOLO mode** flag (`yolo: bool`) suppresses interactive confirmation/clarification tools. SOP phases that carry the `[__requires confirmation__; __must__]` directive pair **override** YOLO and DO prompt. | Lets SOPs run unsupervised when the author has not marked a step `__must__`. |
| G8 | A `/sop <name>` tool launches a **new conversational inferencer in a subprocess** in YOLO mode pre-loaded with the named SOP. | This is the agent equivalent of "fire-and-forget run the playbook in another window." Pairs naturally with G3 (`/background-job /sop …`). |
| G9 | `/enter-sop <name>` and `/exit-sop` switch the SOP **in the current conversation**. The conversational template lists available SOPs in a catalog block and active SOP in a status block. | Maps to the `enter_workflow / exit_workflow` tools designed in `workflow-as-first-class-citizen.md`; this plan adds the user-facing slash forms. |
| G10 | All of the above persist across server restarts via session-store JSON + a new per-session `jobs.json`. | The dev-server hot-reloads constantly; loss of background-job state on restart is unacceptable. |

### 1.2 Non-Goals

| #  | Non-Goal | Rationale |
|----|----------|-----------|
| N1 | Cross-session job sharing (job spawned in session A visible from session B). | Jobs are session-scoped (same lifetime as the conversation). Cross-session orchestration is a separate "team-level scheduler" feature. |
| N2 | Distributed execution (Sandcastle, Slurm, Kubernetes). | All jobs run as local subprocesses on the same host as the server. The shape of `JobManager` does leave room for a future `Executor` abstraction, but we don't implement it. |
| N3 | Multiple **active** SOPs in one conversation. | Same constraint as the workflow-first-class plan — at most one active workflow run per session. |
| N4 | Replacing the existing async-tool fire-and-forget path (the in-process `_run_async` in `_execute_tool_call`). | Background jobs are a SUPERSET — same shape, but persisted, scheduled, and result-injecting. The legacy path stays for trivial UI-status notifications (e.g., `create_role` showing in the task panel). |
| N5 | YOLO mode bypassing safety policies (e.g. `bypassPermissions`). | YOLO is a UX policy ("don't ask me"), not a permission policy. The underlying tools still honor their `permission_mode` settings. |

---

## 2. Investigation Findings (Today's Reality)

### 2.1 How a message flows today

```
WebSocket message ─► manager_websocket_routes.process_message
                       │
                       ├── slash? ─► _try_dev_slash_command ─► ToolDispatcher
                       │                                        │
                       │                                        └─► tools/<name>/executor.py
                       │
                       └── no slash ─► ConversationService.run_conversation_turn
                                          │
                                          ├── _get_session_inferencer  (cached)
                                          ├── _compute_session_context (workflow_context, …)
                                          ├── set_prior_context / set_messages
                                          └── inferencer.run_agentic_loop(message, ...)
                                                │
                                                └── for iteration in max_iterations:
                                                      _render_prompt
                                                      base_inferencer.ainfer / ainfer_streaming
                                                      parse <Response> + ToolsToInvoke
                                                      _execute_tool_call  (loops; if async, fire-and-forget)
```

**Key data points** (verified by file inspection):

| Concern | Location | Note |
|---------|----------|------|
| Single-turn-at-a-time | `conversation_service.py:464` | One coroutine per `process_message`; no queue. A second message arriving mid-turn races on the cached inferencer's mutable `_messages`. |
| Async tool dispatch | `conversational_inferencer.py:762-816` | `tool_def.asynchronous=True` ⇒ `asyncio.create_task(_run_async)` ⇒ returns the placeholder string and stores the task in `self._active_async_task`. No persistence; no completion callback. |
| Active task panel | (frontend) | Driven by `task_status` messages sent over WS independently of the conversation reply. |
| Tool registry | `resources/tools/<name>/tool.json` + `executor.py` | Loaded once at startup; manifest declares `asynchronous`, `agent_enabled`, `slash_enabled`. |
| Slash router | `manager_websocket_routes.py:104` | Resolves `/<cmd>` to a tool, calls executor directly (bypasses `run_conversation_turn`). |
| Conversation template | `prompt_templates/conversation/main/initial.jinja2` | Renders `action_tools`, `conversation_tools`, optional `<WorkflowDescription/Status/Guidance>`. |
| Session state on disk | `_runtime/servers/<…>/sessions/<sid>_<…>/session_state.json` | Single JSON blob; turn artifacts live in `turn_NNN/` subdirs. |
| SOP catalog | (none) | Currently a single hardcoded `find_sop_file()` returning `_variables/workflow/sop.{ext}`. `workflow-as-first-class-citizen.md` redesigns this. |

### 2.2 The `/task` topology landscape

```
resources/tools/task/topologies/
  ├── single.yaml                                ◄── ONE ClaudeCodeCLI leaf (no PTI, no Dual)
  ├── pti-simple.yaml                            ◄── PTI with one CLI per phase (no Dual)
  ├── pti.yaml                                   ◄── PTI + Dual consensus (current default)
  ├── breakdown-multiflow-plan-then-implement.yaml ◄── BTA + MultiFlow + PTI + Dual (heaviest)
  ├── breakdown-multiflow-plan.yaml              ◄── plan-only variant
  ├── multi-flow.yaml / multi-flow-dual.yaml
  └── bta.yaml / bta-dual.yaml
```

Critical observation: **`single.yaml` already exists** and is a single
`ClaudeCodeCLI` leaf. But it uses ClaudeCodeCLI, not RovoDevCLI, and it has
**no prompt-template wiring** — it just runs the raw user request through the
inferencer. The `--simple` design below adds a new `simple-leaf.yaml` that
threads the request through `implementation/main/initial.jinja2` (so the
deliverable goes to a defined `output_path` with structured `<Response>`
parsing) and selects RovoDevCLI by default while remaining swappable via
`--base-inferencer`.

### 2.3 The async-tool execution path (the seed of background jobs)

```python
# conversational_inferencer.py:803-816  (excerpt — current)
async def _run_async() -> None:
    try:
        result = await executor(canonical, tool_call.arguments)
        if hasattr(result, "context_updates") and result.context_updates:
            self.update_prior_context(**result.context_updates)
    except Exception as e:
        logger.error("Async tool %s failed: %s", canonical, e)

self._active_async_task = asyncio.create_task(_run_async())
self._async_tool_dispatched = True
return f"Tool '{canonical}' launched asynchronously. …"
```

This is the design seed for background jobs:

- ✅ Already non-blocking
- ❌ Stored in `self._active_async_task` (single slot, overwritten)
- ❌ No persistence (server restart drops the running coroutine)
- ❌ No completion notification back to the agent (the agent learns nothing further)
- ❌ No scheduling / recurrence
- ❌ Out-of-process commands (e.g., `find ~`) not supported — only Python tools

**This plan supersedes that path** with a real `JobManager`. The legacy
fire-and-forget remains for "show in task panel and forget" cases like
`create_role` which already have their own progress notifications.

### 2.4 SOP directive parsing (already supports `[__requires confirmation__; __must__]`)

`SOPManager.parse_markdown` (RichPythonUtils) splits the bracketed directives
by `;` and lowercases each part, producing `phase.directives = ["requires
confirmation", "must"]` (the `__…__` underscores are stripped earlier by the
regex; verified at `rich_python_utils/string_utils/formatting/template_manager/sop_manager.py:245-285`).

**This means the YOLO override semantics are implementable today**: when
about to emit a confirmation tool inside an active SOP phase, we inspect
`active_phase.directives`. If `"requires confirmation"` AND `"must"` are both
present, YOLO does NOT auto-confirm; otherwise it does.

### 2.5 What `workflow-as-first-class-citizen.md` already designs

That plan (6 phases, A→F) introduces:
- `WorkflowDefinition` on-disk at `resources/workflows/<name>/{workflow.json, sop.jinja2, description.jinja2, .sop.config.yaml}`
- `WorkflowRegistry` (in-memory, loaded at startup)
- `WorkflowRun` (per-execution instance with `workflow_id`)
- `WorkflowSessionState` (`active_workflow_id` + `runs: dict[str, WorkflowRun]`)
- Tools `enter_workflow`, `exit_workflow`, `resume_workflow` (action tools, agent-callable)
- Two new prompt sections: `## Available Workflows`, `## Ongoing Workflows`
- Backward-compatible migration shim in `session_store`

**This plan takes that as foundation** and adds:
- User-facing slash aliases `/enter-sop`, `/exit-sop`, `/sop`
- The `/sop` variant that spawns a **subprocess** (rather than mutating the
  current session) — needed because the user wants "launches a new
  conversational inferencer in a subprocess"
- The YOLO-mode flag passed to subprocess SOP runs
- An additional "SOP directory convention" that accepts the user's mentioned
  layout (`prompt_templates/conversation/main/_variables/workflow_sop/<name>.md`)
  as a **secondary catalog source** in addition to the canonical
  `resources/workflows/<name>/` layout

---

## 3. Feature 1 — `task --simple` Mode (and the New Default)

### 3.1 Why this is the keystone

Every other feature in this plan benefits from a cheap, deterministic task
execution primitive:

- `/background-job` jobs that take >5 minutes are operationally painful
- `/sop` subprocesses that re-invoke `/task --plan` recursively will explode runtimes
- The user just wants "ChatGPT-style: run this once, give me the answer"

Today there is no clean default for "I want a task done in one shot." The
existing `single.yaml` is the closest, but it has rough edges (no prompt
template, no parsed output, no structured workspace contents).

### 3.2 Design — the `simple-leaf` topology

**New topology file** `resources/tools/task/topologies/simple-leaf.yaml`:

```yaml
# Simple-leaf — one inferencer call, implementation prompt only.
# Default for `/task` when no mode/topology flag is provided.
# Workspace contents:
#   - stream_*.txt        (streaming cache; from cache_folder)
#   - inferencer_args.json (resolved attrs of the leaf inferencer)
#   - input.md            (rendered prompt from implementation/main/initial.jinja2)
#   - response.md         (raw response text)
#   - output.md           (parsed <Response>…</Response> body, or response.md if no tag)
#   - meta.json           (start/end times, model, base_inferencer kind, exit_code)
_target_: agent_foundation.common.inferencers.simple_leaf_inferencer.SimpleLeafInferencer
base_inferencer:
  _target_: ${_params.base_inferencer_target}    # resolved at runtime from --base-inferencer
  model_name: ${_params.base_inferencer_model}
  permission_mode: bypassPermissions
  idle_timeout_seconds: 300
  cache_folder: ${_params.workspace_root}
template_root_space: implementation       # uses implementation/main/initial.jinja2
output_filename: output.md
```

**Why a tiny new `SimpleLeafInferencer` class instead of reusing a leaf
directly?** The leaf inferencer (`ClaudeCodeCLI`, `RovoDevCLI`) has no
knowledge of `template_root_space` or `output_filename` — those are
flow-inferencer concerns. `SimpleLeafInferencer` is a 50-line shim that:

1. Renders `implementation/main/initial.jinja2` with `{input: <request>,
   output_path: <workspace>/output.md, …}` (mirrors what
   `PlanThenImplementInferencer` does for the executor phase).
2. Writes `input.md` to the workspace.
3. Calls `base_inferencer.ainfer(rendered_prompt)`.
4. Writes `response.md` (raw) and `output.md` (parsed via
   `extract_response_text`).
5. Writes `inferencer_args.json` (attrs of `base_inferencer` after
   construction) and `meta.json`.
6. Returns the parsed output as the tool result.

**Default base inferencer**: `RovoDevCLI` (per the user's spec). Overridable via
`--base-inferencer claude_cli|rovodev|metamate_sdk`.

### 3.3 Wiring `--simple` and making it the default

**Changes to `tools/task/tool.json`**:

```jsonc
{
  ...,
  "parameters": [
    {"name": "request", "type": "string", "required": true, "positional": true, ...},
    {"name": "--simple", "type": "flag", "default": true,
     "description": "Single inferencer call, implementation prompt only — the new default. Mutually exclusive with --plan/--full/--execute/--confirm."},
    {"name": "--plan", "type": "flag", "description": "Plan-only PTI (forces --no-simple)"},
    {"name": "--full", "type": "flag", "description": "Full PTI + Dual (forces --no-simple)"},
    ...,
    {"name": "--base-inferencer", "type": "string", "popular": true,
     "choices": ["rovodev", "claude_cli", "metamate_sdk"],
     "description": "Leaf inferencer kind. Default: rovodev for --simple, claude_cli for others."},
    ...
  ]
}
```

**Changes to `tools/task/executor.py`**:

1. **Stage 0** (new) — *before* `_resolve_agent_config`:
   ```python
   # Mode resolution. --simple wins by default unless any explicit mode flag is set.
   explicit_modes = [m for m in ("plan", "full", "execute", "confirm") if arguments.get(m)]
   simple_requested = arguments.get("simple", True) and not explicit_modes
   if simple_requested and arguments.get("agent_config") is None:
       arguments["agent_config"] = "simple-leaf"
       arguments["_mode_simple"] = True
   ```

2. **Stage 3 (existing)** — extend the "PTI-only flag" validator to also reject
   `--analysis / --multi-iter / --confirm / --no-implementation / --no-planning`
   when in simple mode.

3. **Stage 6 — overrides**: when `_mode_simple`, also set:
   ```python
   overrides["_params.base_inferencer_target"] = _resolve_inferencer_target(
       arguments.get("base_inferencer") or "rovodev"
   )
   overrides["_params.base_inferencer_model"] = arguments.get("model") or "opus[1m]"
   ```

4. **Stage 8** — `simple-leaf` topology has no `interactive` wiring, no
   `graph_reporter`. Skip those branches when topology is `simple-leaf`.

### 3.4 Workspace layout for simple mode

```
<workspace_root>/
  ├── input.md                    # rendered implementation prompt
  ├── inferencer_args.json        # resolved kw args of the leaf inferencer
  ├── response.md                 # raw response text (full <Thinking>+<Response>)
  ├── output.md                   # parsed <Response> body only (or response.md if no tag)
  ├── meta.json                   # start_ts, end_ts, model, base_inferencer kind, exit_code, parsed_ok
  └── stream_*.txt                # written by leaf's cache_folder (existing behavior)
```

The first 5 files are emitted by `SimpleLeafInferencer`. The streaming cache
files are emitted by the leaf via the existing `cache_folder` mechanism
(`streaming_inferencer_base.py:155`).

### 3.5 Acceptance criteria for Feature 1

- `/task "fix the failing test in foo.py"` (no flags) takes <30 s on a small
  task with `--simple` as the default; workspace has the 5 expected files +
  streaming cache.
- `/task --plan "build auth"` still routes to PTI (mode flag wins).
- `/task --simple --base-inferencer claude_cli "…"` swaps the leaf without
  touching the topology YAML.
- Existing `/task --full` invocations behave identically (no regression).

### 3.6 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 3-R1 | Users who had `/task` as muscle-memory-for-PTI get surprised by simple mode. | Surface `--simple (default)` in the agent panel's help; emit a one-line preamble in the response: "Used simple mode (single RovoDevCLI call). Use `--plan` or `--full` for consensus quality." |
| 3-R2 | `RovoDevCLI` isn't installed in some envs. | Fall back to `claude_cli` automatically when `acli` is missing on PATH; log a notice. |
| 3-R3 | Parsing of `<Response>` is fragile if the leaf doesn't emit the tags. | `SimpleLeafInferencer` falls back to the raw response and sets `meta.json::parsed_ok = false`. Downstream callers see the raw text. |

---

## 4. Feature 2 — User Input Queue

### 4.1 Why

Currently, `process_message` calls `run_conversation_turn` directly. If the
user sends a second message while the first is still in flight (or worse, a
background-job completion fires asynchronously), the two coroutines race on
the inferencer's cached `_messages` and `prior_context`.

The user input queue makes message processing strictly serial per session,
introduces a clean injection point for non-user message sources, and provides
the foundation for `--fork-on-completion` and YOLO autonomous SOP runs.

### 4.2 Design

```python
# server/services/user_input_queue.py    (new)

@dataclass
class QueueItem:
    content: str                    # text that becomes the next turn's user message
    source: Literal["user", "background-job", "sop", "system", "internal"] = "user"
    priority: int = 1               # 1 = user (highest), 2 = bg-job, 3 = system
    tag: str = ""                   # optional label (e.g., "bg-job:<id>", "fork-trigger")
    fork: bool = False              # if True, queue runner forks a new session and replays
    fork_metadata: dict = field(default_factory=dict)   # carried through to the new session
    enqueued_at: float = field(default_factory=time.time)


class UserInputQueue:
    """Per-session FIFO with priority groups.

    Strict ordering inside the same priority. Higher priority drains first
    (so a fresh user message preempts a pending background-job injection).
    """
    def __init__(self) -> None:
        self._buckets: dict[int, deque[QueueItem]] = defaultdict(deque)
        self._waiters: list[asyncio.Future] = []   # for await-on-empty
        self._lock = asyncio.Lock()

    async def push(self, item: QueueItem) -> None: ...
    async def pop(self) -> QueueItem: ...
    def snapshot(self) -> list[QueueItem]: ...
    def __len__(self) -> int: ...
```

Stored under `ConversationService._session_queues: dict[str, UserInputQueue]`,
created lazily per session in `_get_session_queue(session_id)`.

### 4.3 The `QueueRunner` — one coroutine per session

```python
# server/services/queue_runner.py    (new)

class QueueRunner:
    """Per-session coroutine that drains UserInputQueue serially."""

    def __init__(self, session_id: str, conversation_service: ConversationService):
        self.session_id = session_id
        self._svc = conversation_service
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name=f"qrun-{self.session_id}")

    async def _loop(self) -> None:
        queue = self._svc._get_session_queue(self.session_id)
        while not self._stop_event.is_set():
            item = await queue.pop()      # blocks until item available
            try:
                if item.fork:
                    await self._handle_fork(item)
                else:
                    await self._svc.run_conversation_turn_for_queue_item(
                        self.session_id, item,
                    )
            except Exception as e:
                logger.exception("queue runner failed on %s: %s", item.tag, e)

    async def stop(self) -> None: ...
    async def _handle_fork(self, item: QueueItem) -> None: ...   # see §6
```

### 4.4 Changes to `process_message` and `run_conversation_turn`

```python
# manager_websocket_routes.py — process_message  (sketch)
if user_typed_message:
    queue = conversation_service.ensure_queue(session_id)
    await queue.push(QueueItem(content=user_message, source="user", priority=1))
    conversation_service.ensure_queue_runner(session_id)
```

```python
# conversation_service.py — new shim
async def run_conversation_turn_for_queue_item(self, sid: str, item: QueueItem) -> AgenticResult:
    session = self.data_service.get_session(sid)
    if item.source != "user":
        # Annotate the prior_context so the prompt template can show source/tag.
        self._pending_input_meta = {"source": item.source, "tag": item.tag, ...}
    return await self.run_conversation_turn(session, item.content, ...)
```

### 4.5 Interaction with the inferencer's own `run_agentic_loop`

`run_agentic_loop` already iterates multiple times within a single turn (e.g.,
ask user via clarification tool → wait → continue). The queue is at the
**turn boundary**, not the iteration boundary. Inside a turn the inferencer
still owns the loop. The queue feeds it one user input at a time.

### 4.6 Persistence

The queue is in-memory **only** (matches today's behavior — pending messages
are lost on server crash). Background-job completion injections, however,
*are* persisted (see Feature 3) so they re-inject on restart if the job had
already completed before crash. To handle "queued user input lost on restart",
we add a one-line warning in the next session start: "N messages were in
queue when the server stopped and were not delivered."

### 4.7 Acceptance criteria

- Two messages sent within 1 s of each other on the same session are
  processed strictly in order; the second's prompt sees the first's reply
  in `<PreviousTurns>`.
- A background job completing mid-turn enqueues; its injection is consumed
  only after the current turn finishes.
- `len(queue) > 0` is exposed as a session metric in the WS protocol so the
  UI can show "1 pending message" indicators.

### 4.8 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 4-R1 | Slow `run_agentic_loop` blocks the queue. | Queue depth becomes a UX signal; UI shows pending counter. Per-turn `total_timeout_seconds` already exists in the inferencer base. |
| 4-R2 | A user sends 10 messages rapidly; the agent answers stale messages. | Coalesce: when popping, peek at the queue — if 3+ items from the same `source="user"` are buffered, concatenate them with `\n---\n` separators and process as one turn. Optional via `queue.coalesce_user=True`. |
| 4-R3 | Runner crashes leave items orphaned. | `QueueRunner._loop` wraps `pop`/dispatch in try/except; on uncaught exception, it logs and continues. A dead-letter list (`queue._failed: list[QueueItem]`) collects items that errored 3 times. |
| 4-R4 | Two queue runners (e.g. duplicate `ensure_queue_runner` from race) consume the same queue. | `ensure_queue_runner` is idempotent and guards with `self._runner_locks[sid]`. |

---

## 5. Feature 3 — Background Jobs & JobManager

### 5.1 Domain model

```python
# server/services/jobs/types.py    (new)

class JobKind(str, Enum):
    TOOL    = "tool"        # spec resolves to a registered tool
    COMMAND = "command"     # spec is a shell command

class JobStatus(str, Enum):
    PENDING    = "pending"      # scheduled, not started
    RUNNING    = "running"      # PID alive
    COMPLETED  = "completed"
    FAILED     = "failed"
    KILLED     = "killed"
    TERMINATED = "terminated"   # server-restart sweep

@dataclass
class JobSchedule:
    at: float | None = None           # one-shot run at unix ts
    every: float | None = None        # seconds; None ⇒ not recurring
    max_runs: int | None = None       # cap for recurring
    last_run_at: float | None = None
    next_run_at: float | None = None
    runs_completed: int = 0

@dataclass
class JobRecord:
    job_id: str                       # "job-<8 hex>"
    session_id: str
    name: str                         # user-friendly label
    kind: JobKind
    spec: str                         # original spec (tool name or first command word)
    args: list[str]                   # remaining argv
    cmdline: str                      # the actual cmd (for COMMAND) or "tool:<name>" (for TOOL)
    workspace_dir: Path               # absolute path
    status: JobStatus
    pid: int | None
    fork_on_completion: bool
    created_at: float
    started_at: float | None
    completed_at: float | None
    exit_code: int | None             # 0/non-zero for COMMAND; mirrored from ToolExecutionResult for TOOL
    result_summary: str               # ≤ 500 chars, first lines of stdout / tool result
    schedule: JobSchedule
    completion_injected_at: float | None
    error: str = ""
```

Stored per session at `<session_dir>/jobs.json` as a dict of `job_id → JobRecord`.

### 5.2 `JobManager`

```python
# server/services/jobs/manager.py    (new)

class JobManager:
    """Per-server registry of background jobs across all sessions.

    Multi-session because the scheduler runs as a single asyncio task
    polling all sessions' due jobs. Storage is per-session though, so
    each session can be loaded/persisted independently.
    """

    def __init__(self, server_dir: Path, data_service, tool_dispatcher, conversation_service):
        self._server_dir = server_dir
        self._data_service = data_service
        self._tool_dispatcher = tool_dispatcher
        self._svc = conversation_service     # to inject completion items into queues
        self._records: dict[str, JobRecord] = {}     # job_id → record
        self._procs: dict[str, asyncio.subprocess.Process | asyncio.Task] = {}
        self._scheduler_task: asyncio.Task | None = None

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    # Session lifecycle hooks
    async def load_for_session(self, session_id: str) -> None: ...
    async def save_for_session(self, session_id: str) -> None: ...

    # Creation
    async def create_job(
        self, session_id: str, spec: str, args: list[str], *,
        name: str | None = None,
        fork_on_completion: bool = False,
        schedule: JobSchedule | None = None,
    ) -> JobRecord: ...

    # Lifecycle
    async def start_job(self, job_id: str) -> None: ...        # actually launch
    async def kill_job(self, job_id: str) -> None: ...
    async def list_for_session(self, session_id: str, *, status: JobStatus | None = None) -> list[JobRecord]: ...
    def get(self, job_id: str) -> JobRecord | None: ...

    # Internal
    async def _scheduler_loop(self) -> None: ...               # polls every 5s
    async def _run_tool_job(self, rec: JobRecord) -> None: ...
    async def _run_command_job(self, rec: JobRecord) -> None: ...
    async def _on_job_complete(self, rec: JobRecord) -> None: ...
    async def _inject_completion(self, rec: JobRecord) -> None: ...
```

### 5.3 Job workspaces

Root: `<session_dir>/jobs/<job_id>/`

For **tool jobs**, the tool's own executor decides its workspace; for tools
like `/task`, the executor already does its own workspace allocation, so the
job workspace dir becomes the *outer* container, with the tool's nested
workspace under it. JobManager passes `working_dir=<jobs/<id>>` via
`session_context` so `_resolve_workspace` honors it.

For **command jobs**, the workspace contains:

```
jobs/<job_id>/
  ├── command.txt        # the resolved argv (one per line)
  ├── meta.json          # JobRecord.to_dict() at launch time
  ├── stdout.log         # streamed stdout
  ├── stderr.log         # streamed stderr
  └── result_summary.md  # written by _on_job_complete (head of stdout)
```

### 5.4 The `/background-job` tool

**`resources/tools/background_job/tool.json`** (sketch):

```jsonc
{
  "name": "background_job",
  "aliases": ["background-job", "bgjob", "bg"],
  "tool_type": "Action",
  "agent_enabled": true,
  "slash_enabled": true,
  "asynchronous": true,         // returns immediately
  "description": "Launch a background job: a registered tool or a shell command. Result is injected into the user-input queue on completion.",
  "parameters": [
    {"name": "spec", "type": "string", "required": true, "positional": true,
     "description": "Either a tool name (e.g., `task`, `create_role`, `find`) or the first word of a shell command. If a registered tool name, the remaining args are the tool arguments. Otherwise the entire argv is run as a subprocess via /bin/sh -c."},
    {"name": "args", "type": "string", "variadic": true,
     "description": "Remaining argv for the spec."},
    {"name": "--fork-on-completion", "type": "flag",
     "description": "On completion, inject a `fork` item into the queue, spawning a new session that begins with the job's result."},
    {"name": "--at", "type": "string",
     "description": "One-shot ISO 8601 timestamp (e.g., 2026-05-19T18:00:00). Defaults to immediate."},
    {"name": "--every", "type": "string",
     "description": "Recurrence interval (e.g., `5m`, `1h30m`, `1d`). Re-creates a JobRecord run at every interval."},
    {"name": "--max-runs", "type": "int",
     "description": "Cap recurrence at N runs. Unbounded by default."},
    {"name": "--name", "type": "string",
     "description": "Human-friendly label for status display."}
  ]
}
```

**`resources/tools/background_job/executor.py`** dispatches:

```python
async def execute(arguments: dict, session_context: dict) -> ToolExecutionResult:
    svc           = session_context["conversation_service"]
    job_manager   = svc.job_manager
    sid           = session_context["session_id"]
    spec          = arguments["spec"]
    args          = arguments.get("args", [])
    fork          = arguments.get("fork_on_completion", False)
    sched_args    = {"at": _parse_iso(arguments.get("at")), "every": _parse_dur(arguments.get("every")), "max_runs": arguments.get("max_runs")}
    name          = arguments.get("name") or spec
    rec = await job_manager.create_job(
        sid, spec, args, name=name, fork_on_completion=fork,
        schedule=JobSchedule(**sched_args),
    )
    if rec.schedule.at is None and rec.schedule.every is None:
        await job_manager.start_job(rec.job_id)
    return ToolExecutionResult(
        result=f"Queued background job `{rec.job_id}` ({rec.name}). Status will be reported when it completes.",
        context_updates={"_background_jobs_changed": True},
    )
```

### 5.5 Spec resolution (tool vs. command)

```python
def _resolve_spec(spec: str, tool_dispatcher) -> tuple[JobKind, str, list[str]]:
    """If `spec` matches a tool name (or alias) → TOOL; else COMMAND."""
    tool = tool_dispatcher.resolve(spec)
    if tool is not None:
        return JobKind.TOOL, spec, []     # caller appends args separately
    return JobKind.COMMAND, spec, []
```

`tool_dispatcher.resolve` already exists (uses tool aliases / canonical names).

### 5.6 Tool-job execution

```python
async def _run_tool_job(self, rec: JobRecord) -> None:
    rec.status = JobStatus.RUNNING
    rec.started_at = time.time()
    rec.pid = None                # tool jobs are in-process coroutines
    await self.save_for_session(rec.session_id)

    tool_name = rec.spec
    # Build dict from positional args + flags using the tool's manifest spec
    parsed_args = _argv_to_tool_args(rec.args, self._tool_dispatcher.get_manifest(tool_name))
    session_ctx = self._build_session_context_for_job(rec)

    try:
        result = await self._tool_dispatcher.execute(tool_name, parsed_args, session_ctx)
        rec.exit_code = 0
        rec.result_summary = _summarize_tool_result(result, max_chars=500)
        rec.status = JobStatus.COMPLETED
    except Exception as e:
        rec.exit_code = -1
        rec.error = str(e)
        rec.status = JobStatus.FAILED
    finally:
        rec.completed_at = time.time()
        await self._on_job_complete(rec)
```

### 5.7 Command-job execution

```python
async def _run_command_job(self, rec: JobRecord) -> None:
    rec.status = JobStatus.RUNNING
    rec.started_at = time.time()
    ws = rec.workspace_dir
    ws.mkdir(parents=True, exist_ok=True)
    cmdline = " ".join(shlex.quote(p) for p in [rec.spec, *rec.args])
    (ws / "command.txt").write_text(cmdline + "\n")
    proc = await asyncio.create_subprocess_shell(
        cmdline,
        stdout=(ws / "stdout.log").open("ab"),
        stderr=(ws / "stderr.log").open("ab"),
        cwd=str(self._working_dir_for(rec.session_id)),
    )
    rec.pid = proc.pid
    self._procs[rec.job_id] = proc
    await self.save_for_session(rec.session_id)

    rc = await proc.wait()
    rec.exit_code = rc
    rec.completed_at = time.time()
    rec.status = JobStatus.COMPLETED if rc == 0 else JobStatus.FAILED
    rec.result_summary = _head_of_file(ws / "stdout.log", 500)
    await self._on_job_complete(rec)
```

### 5.8 Completion injection

```python
async def _on_job_complete(self, rec: JobRecord) -> None:
    await self.save_for_session(rec.session_id)
    if rec.schedule.every and (rec.schedule.max_runs is None or rec.schedule.runs_completed + 1 < rec.schedule.max_runs):
        # Re-queue next run
        rec.schedule.runs_completed += 1
        rec.schedule.last_run_at = rec.completed_at
        rec.schedule.next_run_at = (rec.schedule.last_run_at or time.time()) + rec.schedule.every
        rec.status = JobStatus.PENDING
        await self.save_for_session(rec.session_id)
    await self._inject_completion(rec)

async def _inject_completion(self, rec: JobRecord) -> None:
    queue = self._svc._get_session_queue(rec.session_id)
    msg = self._format_completion_message(rec)
    item = QueueItem(
        content=msg,
        source="background-job",
        priority=2,
        tag=f"bg-job:{rec.job_id}",
        fork=rec.fork_on_completion,
        fork_metadata={"job_id": rec.job_id, "workspace": str(rec.workspace_dir)},
    )
    await queue.push(item)
    rec.completion_injected_at = time.time()
    self._svc.ensure_queue_runner(rec.session_id)
    await self.save_for_session(rec.session_id)
```

**Template of the injection message** (`_format_completion_message`):

```text
[background-job completed: {rec.job_id} — {rec.name}]
Exit: {rec.exit_code}    Duration: {duration_human(rec)}
Workspace: {rec.workspace_dir}
Logs: {rec.workspace_dir}/stdout.log, {rec.workspace_dir}/stderr.log
Summary (first {N} chars):
{rec.result_summary}
{ "(this is a fork trigger — the agent will see this in a fresh session)" if rec.fork_on_completion else "" }
```

### 5.9 Scheduler loop

A single per-server task polls every 5 s. Wakeup logic is sloppy on purpose
(no fine-grained `asyncio.sleep_until`); jobs scheduled <5 s apart are still
ordered correctly because the scheduler iterates by `next_run_at`.

```python
async def _scheduler_loop(self) -> None:
    while not self._stopping.is_set():
        await asyncio.sleep(5)
        now = time.time()
        due = [r for r in self._records.values() if r.status == JobStatus.PENDING
               and ((r.schedule.at and r.schedule.at <= now) or (r.schedule.next_run_at and r.schedule.next_run_at <= now))]
        for rec in due:
            asyncio.create_task(self.start_job(rec.job_id))
```

### 5.10 Persistence + server-restart sweep

On `JobManager.start()`:

1. Walk every session dir; read `jobs.json`; rebuild `self._records`.
2. Any record with status `RUNNING` and a `pid` that is not alive → mark
   `TERMINATED`; inject a system message into the session's queue:
   `[background-job <id> terminated by server restart]`.
3. Any record with status `PENDING` is left for the scheduler loop to pick
   up (its `at` / `next_run_at` may already be in the past — fires
   immediately).

### 5.11 Template surface — `## Running Background Jobs`

Add to `prompt_templates/conversation/main/initial.jinja2` (after
`## Available Tools`, before `## Conversation`):

```jinja2
{% if background_jobs is defined and background_jobs %}
## Running Background Jobs
{% for j in background_jobs %}
- **{{ j.job_id }}** — {{ j.name }} ({{ j.kind }})
  Started: {{ j.started_at_human }}    Elapsed: {{ j.elapsed_human }}
  {% if j.schedule_human %}Schedule: {{ j.schedule_human }}{% endif %}
  Workspace: `{{ j.workspace_dir }}`
{% endfor %}
{% endif %}
```

`_compute_session_context` adds:

```python
ctx["background_jobs"] = [
    {
        "job_id": j.job_id, "name": j.name, "kind": j.kind.value,
        "started_at_human": _human_ts(j.started_at),
        "elapsed_human": _human_dur(time.time() - (j.started_at or time.time())),
        "schedule_human": _human_schedule(j.schedule),
        "workspace_dir": str(j.workspace_dir),
    }
    for j in self.job_manager.list_for_session(sid, status=JobStatus.RUNNING)
]
```

### 5.12 Acceptance criteria

- `/background-job task --simple "ls -la"` returns within 1 s and shows in the
  job list; on completion, the next turn's prompt has the injection and the
  job is gone from `Running Background Jobs`.
- `/background-job find / -name "*.foo"` (command path) runs as subprocess;
  `stdout.log` accumulates; `result_summary` shows first 500 chars.
- `/background-job <…> --every 5m` runs forever; running list shows
  recurrence next-run timestamp.
- After `kill -9` of the server and restart, all `RUNNING` jobs become
  `TERMINATED` and produce a `[…terminated…]` injection.
- `--fork-on-completion` causes a NEW session to spawn at injection time (see
  §6).

### 5.13 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 5-R1 | Shell injection via free-form spec. | Always invoke via `asyncio.create_subprocess_shell`, but quote args via `shlex.quote`. Never `eval`/`exec`. Document that `spec args` are subject to shell quoting; the tool description says so. |
| 5-R2 | Runaway job spawns hundreds of subprocesses. | `JobManager.max_concurrent_per_session = 8` (configurable); when at cap, new jobs go to `PENDING` queue and are started as slots free. |
| 5-R3 | Recurring job's workspace fills disk. | Each recurrence gets a sub-folder `runs/<NNN>/`; only the last 10 retained; older directories auto-pruned. |
| 5-R4 | Tool-job's `working_dir` collides with the session's normal tool runs. | JobManager passes a dedicated `session_context["job_id"]`; `_resolve_workspace` in `task/executor.py` uses that for path prefix. |
| 5-R5 | Completion injection arrives while user is mid-typing → confusing. | Frontend treats `source="background-job"` items as system messages with a distinct visual style; queue depth metric exposes them to the user. |
| 5-R6 | Manager's `_scheduler_loop` polls too often or too rarely. | 5 s default; tunable via `OPENTEAM_JOB_SCHEDULER_INTERVAL`. |

---

## 6. Feature 4 — `--fork-on-completion` (Session Fork)

### 6.1 Semantics

When a background job is launched with `--fork-on-completion`, the completion
message is not injected into the *current* session's queue; instead, a new
session is created (forked from the current state at the time of fork), and
the new session's first turn is the injection message.

### 6.2 Fork procedure (`QueueRunner._handle_fork`)

```python
async def _handle_fork(self, item: QueueItem) -> None:
    parent_sid = self.session_id
    parent = self._svc.data_service.get_session(parent_sid)
    # 1. Copy session state. Messages copied verbatim. New session_id.
    new_sid = self._svc.data_service.fork_session(parent_sid, label=f"fork-{item.tag}")
    new_session = self._svc.data_service.get_session(new_sid)
    # 2. Push the trigger as the first user input on the new session.
    queue = self._svc.ensure_queue(new_sid)
    await queue.push(QueueItem(
        content=item.content,
        source=item.source,
        priority=item.priority,
        tag=f"fork-trigger:{item.tag}",
        fork=False,
        fork_metadata={**item.fork_metadata, "parent_session_id": parent_sid},
    ))
    self._svc.ensure_queue_runner(new_sid)
    # 3. Notify parent session.
    parent_queue = self._svc.ensure_queue(parent_sid)
    await parent_queue.push(QueueItem(
        content=f"[forked to new session `{new_sid}` triggered by {item.tag}; this session continues unaffected]",
        source="system",
        priority=3,
        tag=f"fork-emitted:{item.tag}",
    ))
```

### 6.3 Required `data_service.fork_session(parent_sid, label) → new_sid`

This API does not exist yet in `OpenStartup`'s session store. Implementation:

```python
# server/services/session_store.py    (new method)
def fork_session(self, parent_sid: str, *, label: str = "") -> str:
    parent = self.get_session(parent_sid)
    if parent is None: raise KeyError(parent_sid)
    new_sid = self._mint_session_id()
    self._sessions[new_sid] = deepcopy(parent)
    self._sessions[new_sid]["id"] = new_sid
    self._sessions[new_sid]["parent_id"] = parent_sid
    self._sessions[new_sid]["fork_label"] = label
    self._sessions[new_sid]["created_at"] = time.time()
    self._persist(new_sid)
    return new_sid
```

`workflow_state` (per the workflow-as-first-class-citizen plan) is also
deep-copied, so the fork retains the parent's catalog/ongoing/active workflow
runs.

### 6.4 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 6-R1 | Recursive fork explosion (forked session's job also has `--fork-on-completion`). | Add `fork_depth` to session meta; cap at 3 by default; reject `--fork-on-completion` when over the cap. |
| 6-R2 | Frontend doesn't know about new session. | Server emits a `session_forked` WS event to all clients on the parent; the UI offers to switch / open in a new tab. |
| 6-R3 | Parent and child diverge on shared workflow state but write back into the same storage. | `WorkflowSessionState` is copied by value at fork time; each session owns its own snapshot afterward. |

---

## 7. Feature 5 — YOLO Mode

### 7.1 Semantics

`yolo: bool = False` on `ConversationalInferencer`. When True:

1. Conversation tools (`clarification`, `single_choice`, `multiple_choice`,
   `confirmation`, `tool_argument_form`) are **intercepted** by the
   inferencer and auto-resolved with default selections, UNLESS the
   currently active SOP phase carries the directive pair `[__requires
   confirmation__; __must__]`.
2. The prompt template injects a YOLO preamble that tells the LLM to skip
   user-facing chitchat: "Do not ask the user to confirm choices. Do not
   greet. Make the most reasonable decision and proceed."
3. The agentic loop's `max_iterations` is bumped (configurable; default
   doubled) because there's no human in the loop to break runaway loops.
4. Final response still goes back through the normal channel (the queue
   runner's caller receives `AgenticResult`).

### 7.2 Auto-resolution defaults (when YOLO bypasses a conversation tool)

| Conversation tool | Auto-default |
|-------------------|--------------|
| `clarification` | Auto-respond `""` and append a synthetic user message "[YOLO: no clarification provided — proceed with best judgment]". |
| `single_choice` | Pick the first choice. If `allow_custom=True`, do NOT use a custom value (defaults are deterministic). |
| `multiple_choice` | Pick the first choice only. (Avoid the "select all" risk of doing destructive batch work.) |
| `confirmation` | Respond `True` (yes). Logged with `[YOLO auto-confirmed]`. |
| `tool_argument_form` | Use each field's `default` if present, else `""` / `None`. |

### 7.3 The `__must__` override

`workflow_context.py`'s next-pending-phase detection already inspects
`directives`. We add a per-turn precondition:

```python
# conversational_inferencer.py — inside _execute_tool_call for conversation tools
if self.yolo and not self._is_must_confirmation_active():
    return self._yolo_auto_resolve(tool_call)
```

```python
def _is_must_confirmation_active(self) -> bool:
    """True if the active SOP phase has both `requires confirmation` and `must`."""
    sop = self.prior_context.get("_sop")          # already cached by render
    phase_id = self.prior_context.get("current_phase")
    if sop is None or phase_id in (None, "idle"):
        return False
    phase = sop.get_phase(phase_id)               # SOPManager helper
    if phase is None:
        return False
    d = {p.lower() for p in (phase.directives or [])}
    return ("requires confirmation" in d) and ("must" in d)
```

### 7.4 Prompt template addition

In `initial.jinja2`, near the top of `## Decision Procedure`:

```jinja2
{% if yolo is defined and yolo %}
> **YOLO MODE — autonomous execution.** Do not greet the user. Do not ask
> for confirmation unless the active SOP phase carries `[__requires
> confirmation__; __must__]`. Make best-judgment decisions and proceed.
> Keep responses concise; the user is not actively watching.
{% endif %}
```

`_compute_session_context` propagates `yolo` from the per-session inferencer
attr or session metadata.

### 7.5 Activation paths

| How YOLO becomes True | Notes |
|----------------------|-------|
| `/sop <name>` (Feature 6) — subprocess inferencer always YOLO | The whole point. |
| `--yolo` on `/enter-sop` (Feature 7) | Opt-in for in-place SOP runs. |
| `session.metadata["yolo"] = True` (manual) | Power-user toggle. |
| `--yolo` on `/background-job <toolname>` when toolname spawns a conversational inferencer | Pass-through. |

### 7.6 Acceptance criteria

- A YOLO conversation never emits any `<tool_type="confirmation">` block to
  the user (except when active SOP phase requires `__must__`).
- A YOLO conversation hitting a `[__requires confirmation__; __must__]`
  phase DOES emit the confirmation and pauses (this is fine in an in-place
  YOLO; for subprocess SOP runs, see §8.4 for the deadlock mitigation).
- `yolo=False` (default) behavior is byte-identical to today (no template
  change, no interception).

### 7.7 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 7-R1 | YOLO loops infinitely on a buggy SOP. | `max_iterations` is bumped only 2× (configurable). Per-turn timeout still applies. |
| 7-R2 | YOLO + destructive tool ⇒ data loss. | YOLO does NOT bypass tool `permission_mode`; tools that need acceptance still get it from the inferencer config. |
| 7-R3 | YOLO subprocess SOP hits `__must__` and deadlocks. | See §8.4 — subprocess transitions to `awaiting_user_confirmation`; the parent receives a job-status update with the question; user answers via a follow-up tool. |
| 7-R4 | YOLO auto-confirms a destructive choice. | The auto-defaults are conservative (first choice for single_choice; never "select all"). The auto-confirm for `confirmation` is the riskiest — SOP authors who don't mark `__must__` on truly destructive steps are accepting that risk. Document this loudly in the SOP guide. |

---

## 8. Feature 6 — `/sop` Tool (Subprocess SOP Runs)

### 8.1 Semantics

`/sop <sop_spec> [--input "..."] [--background-job] [--label "..."]`

Launches a NEW conversational inferencer in a **subprocess**, in YOLO mode,
pre-loaded with the given SOP. The subprocess is a thin Python entry point
that:

1. Constructs a fresh `ConversationalInferencer` with the same `base_inferencer`
   factory the server uses (`backends/factories.py`).
2. Calls `_handle_sop_entry(sop_spec)` which is the same code path as
   `enter_workflow` from the workflow-first-class plan, but bound to a
   fresh session.
3. Optionally takes `--input` as the first user message; otherwise the SOP's
   Phase 0 entry kicks off automatically (most SOPs already have an
   "IMMEDIATELY invoke …" Phase 0 instruction; YOLO mode auto-fills the
   resulting conversation tool).
4. Streams output to a workspace; final result is the workspace path.

### 8.2 Why a subprocess (not just a forked session)?

| Concern | Subprocess wins | Forked session wins |
|---------|-----------------|---------------------|
| Memory isolation | ✅ separate process; OOM doesn't kill server | ❌ same process |
| CPU isolation | ✅ separate OS-scheduled process | ❌ same event loop |
| Lifecycle | ✅ kill via PID | ⚠️ requires cooperative cancel |
| Cost (startup) | ❌ ~1-2 s Python startup | ✅ ~0 ms |
| Sharing model context | ❌ none (writes a result file) | ✅ shares tool registry etc. |

Both are fine for different use cases; the user explicitly asked for
subprocess for `/sop`, so we deliver subprocess. (`enter_workflow` from the
first-class plan covers the in-process case.)

### 8.3 SOP spec resolution

`<sop_spec>` can be:

1. **An absolute or repo-relative file path** ending in `.md`, `.jinja2`, `.j2`,
   `.yaml`, `.yml`. Direct load.
2. **A registered workflow name** — looked up in `WorkflowRegistry` (per the
   workflow-first-class plan). Resolves to its `sop_path`.
3. **A bare name** — searched in this order:
   - `resources/workflows/<name>/sop.{md,jinja2,j2,yaml,yml}` (canonical)
   - `prompt_templates/conversation/main/_variables/workflow_sop/<name>.md`
     (user's mentioned convention — kept for compatibility)
   - `_dev/sops/<name>.md` (developer convention)

### 8.4 Subprocess entry point

**New file** `src/openteam/server/cli/sop_runner.py`:

```python
"""Standalone entry: launch a ConversationalInferencer in YOLO mode for an SOP.

Usage: python -m openteam.server.cli.sop_runner \
    --sop <path> \
    --workspace <dir> \
    --backend rovodev \
    [--input "first user message"] \
    [--parent-session <sid>] \
    [--max-turns 40]

Writes:
    <workspace>/session.jsonl     (turn log, JSONL)
    <workspace>/output.md         (final response or last_phase summary)
    <workspace>/status.json       (status / awaiting_user_confirmation / ...)
    <workspace>/streaming/        (streaming cache files)
"""
```

The subprocess writes `status.json` after every turn:

```jsonc
{
  "status": "running" | "completed" | "failed" | "awaiting_user_confirmation",
  "current_phase": "1",
  "last_response_path": "/.../turn_003/Response.json",
  "pending_confirmation": null | {
      "prompt": "Approve the role document?",
      "view": "/.../role_doc.md",
      "yes_label": "Approve",
      "no_label": "Decline"
  },
  "updated_at": 1747000000.0
}
```

The parent `JobManager` (when `/sop` is run via `/background-job /sop`) tails
this file. When `awaiting_user_confirmation` appears, it injects a special
queue item into the parent session asking the user to answer. The user's
answer is written back to a `decisions/<turn>.json` file that the subprocess
polls and consumes to unblock.

### 8.5 The `/sop` tool wrapper

**`resources/tools/sop/tool.json`** (sketch):

```jsonc
{
  "name": "sop",
  "aliases": ["run-sop"],
  "tool_type": "Action",
  "agent_enabled": true,
  "slash_enabled": true,
  "asynchronous": false,
  "description": "Launch an SOP run in a YOLO subprocess. Returns the workspace path; pair with `/background-job /sop ...` for unsupervised execution.",
  "parameters": [
    {"name": "sop", "type": "string", "required": true, "positional": true,
     "description": "SOP name or path. See plan §8.3."},
    {"name": "--input", "type": "string", "description": "First user message; if omitted, Phase 0 auto-fires."},
    {"name": "--label", "type": "string", "description": "Human label for this run."},
    {"name": "--backend", "type": "string", "choices": ["rovodev", "claude_cli", "metamate_sdk"],
     "description": "Backend for the YOLO subprocess; defaults to current session's backend."},
    {"name": "--background", "type": "flag",
     "description": "Shorthand for `/background-job /sop ...` (creates a job record so completion injects into queue)."}
  ]
}
```

When `--background` is set, the executor delegates to the
`/background-job` machinery rather than launching the subprocess directly.

### 8.6 Lifecycle & cleanup

- Each `/sop` run creates `<session_dir>/sop_runs/<run_id>/` (independent of
  any `/background-job` workspace).
- The subprocess is launched via `asyncio.create_subprocess_exec`; PID
  recorded.
- On parent session deletion, all child sop_runs are SIGTERM'd then SIGKILL'd
  after a 5 s grace.
- The subprocess installs its own signal handler to write `status=killed` to
  `status.json` before exiting.

### 8.7 Acceptance criteria

- `/sop code_optimization` launches a subprocess, returns workspace path
  within 2 s. The subprocess runs YOLO and writes `output.md` on completion.
- `/sop code_optimization --background` returns immediately; the next turn's
  prompt shows the job in `Running Background Jobs`; on completion the
  injection contains a head of `output.md`.
- A SOP with a `[__requires confirmation__; __must__]` phase causes the
  subprocess to write `status=awaiting_user_confirmation`; parent shows the
  question to the user; answer written to `decisions/`; subprocess proceeds.

### 8.8 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 8-R1 | Subprocess Python startup (~1-2 s) on every `/sop` call is annoying. | Acceptable for one-shot; for high-rate use the user can fall back to `/enter-sop` (in-process, Feature 7). |
| 8-R2 | `awaiting_user_confirmation` blocks indefinitely. | Subprocess has its own `total_timeout_seconds` (default 24 h) after which it self-terminates with `status=timeout`. |
| 8-R3 | Subprocess writes corrupt JSON. | All file writes use atomic-rename (write to `.tmp`, then `os.replace`). |
| 8-R4 | A buggy SOP makes the subprocess loop forever. | `--max-turns` defaults to 40; configurable via SOP frontmatter `max_turns`. |

---

## 9. Feature 7 — `/enter-sop` and `/exit-sop` (In-Conversation Switching)

### 9.1 Relation to `workflow-as-first-class-citizen.md`

That plan introduces three agent-callable action tools:

- `enter_workflow(name, entry_reason)`
- `exit_workflow(workflow_id, exit_reason)`
- `resume_workflow(workflow_id, resume_reason)`

This plan adds **user-facing slash aliases** (and lighter `--yolo` flag),
both as separate tool manifests and as alias entries on the existing
manifests:

| Slash command | Maps to | Notes |
|---------------|---------|-------|
| `/enter-sop <name> [--reason "..."] [--yolo]` | `enter_workflow(name, reason)` + sets `inferencer.yolo=True` if `--yolo` | `--yolo` is per-session and persists until `/exit-sop` or explicit `/no-yolo`. |
| `/exit-sop [--reason "..."]` | `exit_workflow(active_workflow_id, reason)` + clears YOLO | Default reason: "user-initiated exit". |
| `/list-sops` | View `available_workflows` + `ongoing_workflows` registers (read-only) | Useful when the catalog grows. |

### 9.2 Catalog visibility for the agent

`initial.jinja2` already gets the `## Available Workflows` and `## Ongoing
Workflows` sections from the first-class plan. This plan adds NOTHING to
the template — the agent already sees the catalog. What's new is the user
slash surface that lets the user (not just the agent) drive switching.

### 9.3 The "agent may enter on user ask" prompt rule

`initial.jinja2` § "Workflow Decision" already says:

> 2. If the user's request fits a **different** Available Workflow, exit the
>    active one (if any) then `enter_workflow`.

We strengthen this with a new rule under the same heading:

```text
3a. If the user's message is literally `/enter-sop <name>` or
    `/exit-sop`, ALWAYS invoke the corresponding tool. Treat slash commands
    as deterministic instructions, not suggestions.
3b. If the user asks in natural language to "switch workflow", "load SOP",
    "do task X using the foo procedure", consider entering the matching
    workflow if one exists.
```

### 9.4 Acceptance criteria

- `/enter-sop code_optimization` immediately switches the session into the
  code_optimization SOP; next turn renders `## Active Workflow
  (wf-…)`.
- `/exit-sop` ends the active SOP; the workflow is moved to `Ongoing
  Workflows` (status: paused).
- `/list-sops` (read-only) outputs a markdown listing.
- The agent autonomously emits `enter_workflow` when the user says "let's
  run the code optimization SOP for foo.py" without typing the slash form.

### 9.5 Risks

| # | Risk | Mitigation |
|---|------|------------|
| 9-R1 | Slash form bypasses the LLM (deterministic, no reasoning). | This is desired UX. The slash router (existing) already supports this for `/task`, etc. |
| 9-R2 | `--yolo` lingers after `/exit-sop`. | Clear `inferencer.yolo` in the slash handler on `/exit-sop`. |
| 9-R3 | Available SOPs include in-progress drafts the user shouldn't see. | `WorkflowDefinition.draft: bool` field; `available_workflows` filters by `draft=False` for catalog rendering. |

---

## 10. Cross-Feature Integration

### 10.1 Compatibility matrix

```
                       │ Feature 2 (queue) │ Feature 3 (jobs) │ Feature 4 (fork) │ Feature 5 (YOLO) │ Feature 6 (/sop) │ Feature 7 (/enter-sop)
───────────────────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┼───────────────────────
Feature 1 (--simple)   │  ✅ identical to  │  ✅ used as the   │  N/A             │  ✅ leaf doesn't  │  N/A (sop wraps  │  N/A
                       │  any user msg     │  default tool    │                  │  prompt user     │  conversational) │
                       │                   │  for bg jobs     │                  │                  │                  │
Feature 2 (queue)      │  -                │  ✅ injection    │  ✅ runner       │  ✅ no change    │  ✅ injection    │  ✅ slash → queue
                       │                   │  goes to queue   │  handles fork    │                  │  for /sop        │  for /enter-sop
                       │                   │                  │                  │                  │  --background    │
Feature 3 (jobs)       │  -                │  -                │  ✅ via flag    │  ✅ jobs running │  ✅ /sop uses    │  N/A
                       │                   │                   │  on bg-job      │  YOLO subproc.   │  /background-job │
                       │                   │                   │                  │  inherit         │  internally       │
Feature 4 (fork)       │  -                │  -                │  -                │  ✅ forked       │  ✅ a /sop run   │  N/A
                       │                   │                   │                   │  session keeps   │  can fork on     │
                       │                   │                   │                   │  YOLO setting    │  completion      │
Feature 5 (YOLO)       │  -                │  -                │  -                │  -               │  ✅ /sop is      │  ✅ /enter-sop   │
                       │                   │                   │                   │                  │  always YOLO     │  --yolo opt-in   │
Feature 6 (/sop)       │  -                │  -                │  -                │  -               │  -               │  ✅ /sop is a    │
                       │                   │                   │                   │                  │                  │  shortcut to     │
                       │                   │                   │                   │                  │                  │  spawn-then-     │
                       │                   │                   │                   │                  │                  │  enter; /enter-  │
                       │                   │                   │                   │                  │                  │  sop is in-proc  │
Feature 7 (/enter-sop) │  -                │  -                │  -                │  -               │  -               │  -                │
```

### 10.2 Shared infrastructure

All seven features depend on:

1. **The conversational template** gains 2 new sections (`## Running
   Background Jobs`, plus the 2 workflow sections from the first-class plan
   if not already merged).
2. **`_compute_session_context`** gains 3 new keys (`background_jobs`,
   `yolo`, `pending_input_meta`); workflow-first-class adds another 3
   (`available_workflows`, `ongoing_workflows`, `active_workflow_id`).
3. **`ConversationalInferencer`** gains 2 new attrs (`yolo: bool`, optional
   `job_manager_ref: Any` for tools to consult).
4. **`ConversationService`** gains 4 helpers: `ensure_queue`,
   `ensure_queue_runner`, `_get_session_queue`, `job_manager`.
5. **`session_store`** gains `fork_session(parent_sid, label)`.
6. **Slash router** gains 4 entries: `/background-job`, `/sop`, `/enter-sop`,
   `/exit-sop` (plus `/list-sops`).
7. **`resources/tools/` adds 4 new tools**: `background_job/`, `sop/`,
   `enter_sop/` (alias of `enter_workflow`), `exit_sop/` (alias of
   `exit_workflow`).

---

## 11. Implementation Plan — Phased

Each phase is independently shippable. Phases A-B-C are sequential
prerequisites; the rest can be interleaved or skipped per priority.

### Phase A — `task --simple` (Feature 1) — **week 1**

- A.1 Add `SimpleLeafInferencer` in `agent_foundation/common/inferencers/simple_leaf_inferencer.py`.
- A.2 Add `topologies/simple-leaf.yaml`.
- A.3 Patch `tools/task/tool.json`: add `--simple` flag with `default: true`.
- A.4 Patch `tools/task/executor.py`: Stage-0 mode resolution sets
  `agent_config="simple-leaf"` when no explicit mode flag.
- A.5 Add `_resolve_inferencer_target("rovodev"|"claude_cli"|"metamate_sdk")`
  helper.
- A.6 Tests:
  - Unit: `SimpleLeafInferencer` writes the 5 workspace files.
  - Integration: `/task "what is 2+2"` finishes <30 s and produces
    `output.md` containing "4".

**Acceptance**: existing `/task --plan` and `/task --full` tests still pass;
new default tested.

### Phase B — User Input Queue (Feature 2) — **week 1-2**

- B.1 Create `server/services/user_input_queue.py` (`QueueItem`,
  `UserInputQueue`).
- B.2 Create `server/services/queue_runner.py` (`QueueRunner`).
- B.3 Patch `ConversationService` to add `ensure_queue`,
  `ensure_queue_runner`, `_get_session_queue`,
  `run_conversation_turn_for_queue_item`.
- B.4 Patch `manager_websocket_routes.process_message` to enqueue + ensure
  runner instead of calling `run_conversation_turn` directly.
- B.5 Tests:
  - Two rapid `process_message` calls; assert second's prompt sees first's
    response in history.
  - Mock a `background-job` injection into a queue with a `user` message
    already queued → assert FIFO order respects priority.

**Acceptance**: no behavior change for single-message flows; queue depth
metric visible.

### Phase C — Background Jobs + JobManager (Feature 3) — **week 2-3**

- C.1 Create `server/services/jobs/{types,manager}.py`.
- C.2 Create `resources/tools/background_job/{tool.json,executor.py}`.
- C.3 Patch slash router to wire `/background-job` (existing alias
  mechanism — manifest's `slash_enabled: true` suffices).
- C.4 Patch `_compute_session_context` to add `background_jobs`.
- C.5 Patch `initial.jinja2` to render `## Running Background Jobs`.
- C.6 Persistence: `jobs.json` per session; load/save hooks.
- C.7 Scheduler loop (5 s polling).
- C.8 Server-restart sweep.
- C.9 Tests:
  - Unit: `JobRecord` round-trip serialization.
  - Integration: `/background-job task --simple "echo hi"` → completion
    injection into queue → next turn prompt has the system message.
  - Integration: `/background-job find / -name foo --every 30s` runs twice,
    inspected via job list.
  - Integration: kill -9 server, restart, observe `TERMINATED` injections.

**Acceptance**: jobs survive restart in the right state; recurring jobs fire
on schedule.

### Phase D — Fork on Completion (Feature 4) — **week 3**

- D.1 Add `session_store.fork_session(parent_sid, label)`.
- D.2 Extend `QueueRunner._handle_fork` per §6.2.
- D.3 Add `fork_depth` to session metadata; enforce cap.
- D.4 WS event `session_forked` for UI to surface.
- D.5 Tests:
  - `/background-job task --simple "..." --fork-on-completion` → new
    session created on completion; parent receives `fork-emitted` system
    message; child receives `fork-trigger`.

**Acceptance**: fork creates an isolated session with parent's snapshot.

### Phase E — YOLO Mode (Feature 5) — **week 3-4**

- E.1 Add `yolo: bool = False` attr on `ConversationalInferencer`.
- E.2 Implement `_is_must_confirmation_active` and `_yolo_auto_resolve`.
- E.3 Patch `_execute_tool_call` for conversation tools to consult them.
- E.4 Patch `initial.jinja2` with the YOLO preamble (guarded by `{% if
  yolo %}`).
- E.5 Propagate `yolo` from session metadata in `_compute_session_context`.
- E.6 Tests:
  - YOLO on, plain phase → `confirmation` tool intercepted; sees auto-True.
  - YOLO on, `[__requires confirmation__; __must__]` phase →
    confirmation NOT intercepted; emitted to UI.
  - YOLO off → identical to current behavior.

**Acceptance**: no regression for `yolo=False`; YOLO behavior matches spec.

### Phase F — `/sop` (Feature 6) — **week 4-5**

- F.1 Create `cli/sop_runner.py` standalone entry.
- F.2 Create `resources/tools/sop/{tool.json,executor.py}`.
- F.3 Implement `status.json` polling in `JobManager` when job's spec is
  `/sop` (sub-special-cased completion handler).
- F.4 Implement the `awaiting_user_confirmation` round-trip via
  `decisions/<turn>.json`.
- F.5 Tests:
  - `/sop code_optimization` (assuming the SOP file exists) → subprocess
    runs to completion within reasonable time; `output.md` populated.
  - `/sop --background` path → JobManager owns the lifecycle; completion
    injects into queue.
  - A SOP with `[__requires confirmation__; __must__]` → parent gets
    confirmation injection; user answer file written; subprocess advances.

**Acceptance**: subprocess SOPs work end-to-end and integrate with the
queue.

### Phase G — `/enter-sop`, `/exit-sop` (Feature 7) — **week 5**

- G.1 Verify `workflow-as-first-class-citizen.md` Phases A-D landed (this
  phase depends on them).
- G.2 Add tool aliases `enter-sop`, `exit-sop` on the workflow-control
  tools, OR add thin wrapper tool manifests under
  `resources/tools/enter_sop/` and `resources/tools/exit_sop/`.
- G.3 Add `--yolo` flag on `/enter-sop`; clear on `/exit-sop`.
- G.4 Add `/list-sops` (read-only).
- G.5 Tests:
  - `/enter-sop code_optimization` → active SOP set; next turn renders the
    active section.
  - `/enter-sop code_optimization --yolo` → also flips YOLO.

**Acceptance**: slash aliases mirror agent-tool behavior.

### Phase H — Polish, Telemetry, Docs — **week 6**

- H.1 Per-session metrics: queue depth, running jobs count, active SOP id,
  yolo flag — exposed via `GET /api/sessions/{id}/status`.
- H.2 Frontend: badge on session list for running jobs / queued messages.
- H.3 SOP authoring guide update: `__must__` directive semantics; YOLO
  implications.
- H.4 `_dev/_docs/` updated: this PLAN.md becomes a Living Reference.

---

## 12. Critical-Thinking Risk Register (Cross-Feature)

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| X-R1 | YOLO subprocess SOP launched via `/background-job /sop` hits a `__must__` confirmation; user is offline; subprocess waits 24 h then times out. | 🟡 Medium | `total_timeout_seconds` (24 h default) is configurable per SOP frontmatter; emit a Slack/email notification at the halfway point (out of scope here but documented). |
| X-R2 | `--fork-on-completion` from a recurring `--every` job spawns N forks per cycle. | 🔴 High | Recurring jobs disallow `--fork-on-completion` at executor-validation time (reject the spec). |
| X-R3 | The queue runner deadlocks because a tool call awaits an interactive answer the user never sent (no YOLO). | 🟡 Medium | The existing per-turn timeout still applies; on timeout, runner moves to the next queue item with a `[turn timed out]` history note. |
| X-R4 | Multiple `/sop --background` runs share the same workspace dir naming → collision. | 🟠 Low-Med | `<session_dir>/sop_runs/<run_id>/` where `run_id = f"sop-{uuid4().hex[:8]}"`. |
| X-R5 | `simple-leaf` topology lacks `--analysis`, `--multi-iter`, `--confirm` — users expect them. | 🟠 Low | Stage-3 validator emits a clear error: "`--analysis / --multi-iter / --confirm` require a PTI topology. Use `--plan` or `--full`." |
| X-R6 | Slash router precedence change (default `/task` is now simple, not PTI). | 🟡 Medium | One-time migration note in CHANGELOG; surface the active mode in the response preamble. |
| X-R7 | YOLO + auto-resolution of `single_choice` always picks first → systematic bias. | 🟠 Low | Documented; SOP authors who care should order options accordingly. |
| X-R8 | `JobManager` not initialized in test fixtures → tools fail. | 🟠 Low | `ConversationService` lazy-instantiates `JobManager` with a no-op scheduler in tests. |
| X-R9 | The `## Running Background Jobs` section grows unbounded for a long-running session. | 🟠 Low | Cap rendering to top 10 (sorted by most-recent start); collapse rest into "(+ N more …)". |
| X-R10 | Slash router can't tell `/sop` from `/background-job /sop` (regex collision). | 🟠 Low | Existing slash router uses first-word match — both are distinct first-words. No collision. |
| X-R11 | `sop_runner.py` subprocess's import path. | 🟠 Low | Same `conftest.py` trick (add `src/` to `sys.path`) plus `OPENSTARTUP_PYTHON` env var (already used by the launcher script). |
| X-R12 | The `--simple` default change breaks the "no surprise" Plan Mode of `/task`. | 🟡 Medium | Wrap the change in a `OPENTEAM_TASK_DEFAULT_MODE` env var with default `simple`; legacy users can set it to `full` if needed. |

---

## 13. Open Design Questions

1. **Should `--fork-on-completion` accept a custom session label**? Probably
   yes: `--fork-as "explore-sde-perf"`. Stored in `session.fork_label`.

2. **YOLO mode and `_execute_tool_call`'s auto-resolution: do we still log
   the auto-decisions to JSONL**? Yes — `type: AutoResolved` records with
   the tool kind and chosen default. Necessary for SOP authors to debug.

3. **Background command jobs and current working directory**: today the
   server's `cwd` is process-launch dir. Should command jobs use that? The
   user's `OPENTEAM_WORKING_DIR` (default `~/MyProjects`)? The session's
   `working_dir`?
   **Recommendation:** session's `working_dir` if set, else
   `OPENTEAM_WORKING_DIR`, else process cwd. Documented.

4. **Subprocess SOP runs and tool registry**: the subprocess loads its own
   tool registry; tools that mutate the parent session (e.g.,
   `create_role`) must NOT execute (they'd write to disk under the parent's
   path silently). Mitigation: subprocess loads the tool registry filtered
   to a `subprocess_safe: true` allow-list (declared in `tool.json`).

5. **Job result truncation**: 500 chars is short for `task` outputs.
   Recommendation: keep at 500 in the injection (so prompts stay small)
   but the full result lives in `output.md` and the injection points to it
   with a clickable path.

6. **Backward compatibility timeline**: how long do we keep the
   `_active_async_task` fire-and-forget path? At least 6 months; eventually
   migrate `create_role` and `role_setup` to use `JobManager` (they get
   restart-recovery for free).

---

## 14. Implementation Checklist (per file)

**New files (~12)**

| Path | Purpose |
|------|---------|
| `agent_foundation/common/inferencers/simple_leaf_inferencer.py` | F1 |
| `OpenStartup/src/openteam/server/resources/tools/task/topologies/simple-leaf.yaml` | F1 |
| `OpenStartup/src/openteam/server/services/user_input_queue.py` | F2 |
| `OpenStartup/src/openteam/server/services/queue_runner.py` | F2 |
| `OpenStartup/src/openteam/server/services/jobs/__init__.py` | F3 |
| `OpenStartup/src/openteam/server/services/jobs/types.py` | F3 |
| `OpenStartup/src/openteam/server/services/jobs/manager.py` | F3 |
| `OpenStartup/src/openteam/server/resources/tools/background_job/{tool.json,executor.py}` | F3 |
| `OpenStartup/src/openteam/server/cli/sop_runner.py` | F6 |
| `OpenStartup/src/openteam/server/resources/tools/sop/{tool.json,executor.py}` | F6 |
| `OpenStartup/src/openteam/server/resources/tools/enter_sop/{tool.json,executor.py}` | F7 (or alias of enter_workflow) |
| `OpenStartup/src/openteam/server/resources/tools/exit_sop/{tool.json,executor.py}` | F7 (or alias of exit_workflow) |

**Modified files (~10)**

| Path | What changes |
|------|--------------|
| `OpenStartup/src/openteam/server/resources/tools/task/tool.json` | F1: `--simple` flag, default true |
| `OpenStartup/src/openteam/server/resources/tools/task/executor.py` | F1: Stage 0 mode resolution, Stage 6 overrides for simple |
| `OpenStartup/src/openteam/server/routes/manager_websocket_routes.py` | F2: process_message enqueues |
| `OpenStartup/src/openteam/server/services/conversation_service.py` | F2/F3/F5/F6/F7: queue + job hooks; YOLO propagation; `_compute_session_context` populates 3 new keys |
| `OpenStartup/src/openteam/server/services/session_store.py` | F4: `fork_session`; F3: job persistence helpers |
| `OpenStartup/src/openteam/server/resources/prompt_templates/conversation/main/initial.jinja2` | F3: `## Running Background Jobs`; F5: YOLO preamble |
| `AgentFoundation/.../conversational/conversational_inferencer.py` | F5: `yolo` attr; conversation-tool interception; `_is_must_confirmation_active`; `_yolo_auto_resolve` |
| `AgentFoundation/.../conversational/conversational_inferencer.py` | F3: optional `job_manager_ref` attr (used by `/background-job` executor when invoked as tool) |
| `OpenStartup/src/openteam/server/main.py` | Start/stop `JobManager`, queue runners on shutdown |
| `OpenStartup/conftest.py` | Stub job manager for tests |

---

## 15. Testing Strategy

| Layer | Tests |
|-------|-------|
| **Unit** | `JobRecord` round-trip; `UserInputQueue` ordering/priority; `_yolo_auto_resolve` matrix; `_is_must_confirmation_active` decision table; `SimpleLeafInferencer` workspace I/O. |
| **Integration (in-process)** | Two-message ordering via queue; `/background-job` (tool path); `/background-job` (command path); YOLO autonomous run of a tiny SOP; `--fork-on-completion` creates new session. |
| **Integration (subprocess)** | `/sop` runs to completion; status.json polled; awaiting-confirmation round-trip; subprocess timeout. |
| **Restart sim** | Snapshot `jobs.json` with running PIDs; restart manager; verify TERMINATED injections fire on next pop. |
| **E2E (web UI)** | Manual checklist: `/task` w/o flags is fast and simple; `/background-job task --simple "ls"` shows in panel; completion notification surfaces in chat; `/sop` opens a new background-run row. |

---

## 16. Quick Reference — Slash Commands Added

```
/task <request> [--simple|--plan|--full|--execute|--confirm] [--base-inferencer rovodev|claude_cli|metamate_sdk] [--model ...]
    --simple is now the default. See §3.

/background-job <spec> [<args>...] [--fork-on-completion] [--at <ISO>] [--every <duration>] [--max-runs N] [--name <label>]
    <spec> = tool name (`task`, `find`, `grep`, ...) or any shell command first word. See §5.

/sop <sop_spec> [--input "..."] [--label "..."] [--backend rovodev|claude_cli|metamate_sdk] [--background]
    Launches YOLO subprocess. See §8.

/enter-sop <name> [--reason "..."] [--yolo]
    Switch active SOP in this conversation. See §9.

/exit-sop [--reason "..."]
    Exit active SOP; reset YOLO. See §9.

/list-sops
    Read-only catalog dump. See §9.
```

---

## 17. Out-of-Scope / Future Work

- **Cross-session orchestration** (job in session A triggers session B
  enter_workflow). Belongs to a future team-level scheduler.
- **Distributed job execution** (Sandcastle / k8s). The `JobManager` design
  has room for an `Executor` abstraction; adding it later is a one-class
  refactor.
- **Per-user / per-role YOLO policies** (e.g., a "junior agent" never YOLOs;
  a "senior agent" YOLOs by default). Add when role-config plumbing exists.
- **Real-time event stream from subprocess SOP runs** (instead of polling
  `status.json`). Acceptable today; revisit when polling overhead matters.
- **SOP authoring DSL** beyond markdown directives. The current `[__requires
  confirmation__; __must__]` parser handles the spec; richer DSL is future
  work.

---

*End of plan.*
