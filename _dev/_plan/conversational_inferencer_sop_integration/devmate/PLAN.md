# Conversational Inferencer × SOP × Background Jobs — Integration Plan (Devmate v1)

> **Author:** Devmate (Claude Opus 4.7) with Tony Chen
> **Date:** 2026-05-20
> **Status:** Proposal — Design + Phased Implementation
> **Companion plan:** `OpenStartup/_dev/_plan/workflow-as-first-class-citizen.md` (workflow registry / multi-workflow / enter/exit/resume). This plan **stacks on top** of that one and assumes its data model (`WorkflowRegistry`, `WorkflowRun`, `WorkflowSessionState`) lands first OR is implemented concurrently. The `WorkflowDefinition` ⇄ `SOPDefinition` correspondence is made explicit in §10.
> **Codebases:**
> - Framework primitives → `CoreProjects/AgentFoundation/src/agent_foundation/`
> - Task tool wiring + topology YAMLs → `CoreProjects/OpenStartup/src/openteam/server/resources/tools/task/`
> - Conversational template + new tools → `CoreProjects/AgentFoundation/src/agent_foundation/resources/`

---

## 0. Context — Why This Plan Exists

The user's rough idea has six distinct strands that must work together coherently:

1. **`task --simple` mode.** Today the `task` tool is a heavyweight dual-agent BTA orchestrator (8+ LLM calls in the propose phase alone). For most agent-initiated subtasks we want a lightweight leaf — just one RovoDev-CLI-style inferencer fed the implementation's initial prompt — producing a tiny workspace (streaming cache + structured log + parsed output). **Simple becomes the new default**; full BTA is opt-in.
2. **User input queue on the conversational inferencer.** Today `run_agentic_loop()` takes a single `content` string per server turn. Background jobs and inter-turn message arrival need a way to *enqueue* further user messages while the loop is running or between turns, and have the inferencer drain them one at a time.
3. **Background job manager.** Generic launcher for (a) tool invocations (especially `task` in simple mode) and (b) direct shell commands, with optional one-shot scheduling and fixed-interval repetition. Each job has its own workspace, PID, command line, launch time. Job completion injects a templated message back into the user input queue. A `--fork-on-completion` flag marks the queued completion message so that, when drained, the inferencer spawns a *forked* child conversation instead of consuming it inline.
4. **`/background-job` tool.** Slash command for user; mirrored as an agent-callable action tool (`background_job`) so SOPs can schedule autonomous follow-ups.
5. **Yolo mode + SOP `__must__` markers.** A conversational-inferencer mode that suppresses confirmation widgets and pretty-prints to logs instead of users, intended for headless SOP execution. Overridden per-phase by `[__requires confirmation__; __must__]` markers, which we extend the SOP DSL to recognise (along with `__optional__`).
6. **`/sop`, `/enter-sop`, `/exit-sop`.** `/sop <path>` launches a fresh, headless, yolo-mode conversational inferencer in a subprocess against the given SOP file. `/enter-sop` and `/exit-sop` operate **inside the current conversation**, mapping 1:1 to the `enter_workflow` / `exit_workflow` action tools from the companion plan (SOP files are the SOP-shaped subset of `WorkflowDefinition`s).

The integration is non-trivial because:
- The conversational inferencer's main loop today is **per-turn synchronous** (`set_messages` → `run_agentic_loop(content)` → return). Pre/post turn hooks (`on_new_turn`, `on_turn_complete`) exist but there is no inter-turn queue.
- The only existing concurrency primitive is the `asynchronous=True` tool flag, which fires an in-process `asyncio.create_task` and returns immediately (`conversational_inferencer.py:776-816`). It does not survive process restart, has no scheduling, no workspace, no PID, and no queue-back semantics.
- The current `task` tool is fundamentally a **BTA dual orchestrator** (`task/tool.json` line 13). Adding `--simple` is more than a flag — it requires bypassing `_resolve_agent_config` and constructing a leaf inferencer with only the implementation/initial prompt, then writing its `(args, input, raw_response, parsed_output)` quartet to a flat workspace.
- The SOPManager (`rich_python_utils.string_utils.formatting.template_manager.sop_manager.SOPManager`) parses `[__depends on__ X; __requires confirmation__]` today; the directive list is consumed in `conversational_inferencer.py:678-685` and in `agent_foundation/server/workflow_context.py:431`. We need to extend both **without** breaking back-compat.

The plan below is deliberately phase-decomposed so each phase is independently shippable and testable. Phases A–C are *foundations* that touch no behavior; D adds the first observable feature (simple-mode task); E onward layer in the queue, jobs, yolo, and sops.

---

## 1. Goals & Non-Goals

### 1.1 Goals

| # | Goal | Why |
|---|------|-----|
| G1 | Replace the `task` tool's default with `--simple` mode that runs **one leaf inferencer with the initial prompt only**, writing `(args / input / raw_response / parsed_output)` to a flat workspace. | The user's request: "by default let's use simple mode … workspace might only have the streaming cache, the logs with inferencer args, input and response, and the output parsed from raw response". |
| G2 | Give the conversational inferencer a **user input queue** so multiple messages (human-typed, background-job completions, forked-conversation seeds) can be appended and drained one-by-one across turns. | Today `run_agentic_loop` consumes exactly one `content` string per turn. Background jobs need a place to *deliver* their completion notice without racing the current turn. |
| G3 | Introduce a **generic `BackgroundJobManager`** that launches tool invocations and direct shell commands as OS subprocesses, tracks `(cmdline, pid, launched_at, schedule, repeat)`, allocates a per-job workspace, and posts a templated completion message back to the user input queue. Optional **`--fork-on-completion`** marker tells the conversational inferencer to *fork a child conversation* on drain instead of consuming inline. | The user's exact spec: "background jobs are supported through tool /background-job … put back ground task output into user input queue with template like maybe …". |
| G4 | Add **`/background-job` slash command + `background_job` action tool**: `/background-job <tool-name-or-cmd> [args…] [--schedule …] [--every …] [--fork-on-completion]`. | User wants both surfaces ("Both: slash + agent tool"). |
| G5 | Add **yolo mode** to the conversational inferencer that auto-skips confirmation widgets and routes their would-be prompts to logs. Overridden per-phase by `[__requires confirmation__; __must__]` markers in the SOP. Also recognise `__optional__` as the explicit yolo-bypass. | User's exact spec: "If there is `[__requires confirmation__; __must__]` then the `__must__` means this confirmation must happen and overrides the yolo mode." |
| G6 | Add **`/sop <path>` tool** that subprocess-launches a fresh, headless, yolo-mode conversational inferencer loaded with that SOP file. Also add **`/enter-sop`** and **`/exit-sop`** which delegate, **inside the current conversation**, to the `enter_workflow` / `exit_workflow` action tools from the companion plan. Render an **Available SOPs** catalog section in the prompt. | User's exact spec. SOPs and workflows are the *same* shape — `/enter-sop` is just a more domain-friendly synonym for `enter_workflow` when the workflow is a literal SOP file (no JSON manifest). |
| G7 | Add a **"Background Jobs in Flight"** section to the conversational prompt that lists running jobs; remove on completion. | User's exact spec: "Conversational inferencer template need to have a section holding current running background jobs and their status, once completes, remove the job from the section." |
| G8 | Keep every change **incremental and reversible**. New defaults can be flipped back via a config flag; legacy code paths remain for one release. | Risk control. |

### 1.2 Non-Goals

| # | Non-Goal | Rationale |
|---|----------|-----------|
| N1 | A persistent cross-process scheduler (cron-like daemon). | Phase 1 keeps jobs in-process to the conversation; persistence is recovered on session reload via on-disk job state. A real daemon is a future option. |
| N2 | A general inter-conversation message bus. | Background-job → queue is scoped to one session. Forked conversations get a one-shot seed; thereafter they're independent. |
| N3 | Replacing the `task` tool's BTA paths. | We add `--simple` as a peer and flip the default; existing topologies stay verbatim and remain accessible via `--full` and `--agent-config`. |
| N4 | A new YAML schema for SOPs. | SOPs keep today's markdown + `[__directives__]` syntax. We only add two qualifier tokens. |
| N5 | Workflow registry / manifest. | Already designed in the companion plan; this plan integrates with that registry but does not duplicate its definition. We add an `sop_only` flag to surface SOP files that have no `workflow.json`. |
| N6 | A new transport for the conversational inferencer (e.g., HTTP per-tab). | The subprocess `/sop` launcher uses stdin/stdout JSONL — same shape as the existing `terminal_inferencer_base` family. |

---

## 2. Investigation Findings (Today's Reality)

### 2.1 The Conversational Inferencer's Per-Turn Surface

`AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py`:

| Symbol | Line | Note |
|---|---|---|
| `ConversationalInferencer.run_agentic_loop(content, *, interactive, session_id, turn_number, on_new_turn, on_prompt_rendered, on_turn_complete)` | L133 | Per-turn driver. Iterates up to `max_iterations`. Mid-loop a conversation tool may trigger a new turn via `on_new_turn(turn_number, user_input)` callback. |
| `set_prior_context(ctx)` / `update_prior_context(**kwargs)` | L521 / L524 | The only persistent state surface across turns (workflow status, completed phases, etc.). |
| `set_messages(messages)` / `add_message(role, content)` / `get_messages()` | L527-541 | Conversation history. |
| `_render_prompt(current_message)` | L568 | Builds the Jinja feed. Currently merges `prior_context`, `completed_actions`, `conversation_history`, `current_turn`, `conversation_tools` and the SOP-derived `workflow_nextstep_guidance`. **This is the chokepoint for adding `available_sops`, `ongoing_workflows`, and `background_jobs` sections.** |
| `_execute_tool_call(tool_call)` | L762 | Tool dispatch. Already special-cases `asynchronous=True` tools (`L778-816`) — fire-and-forget `asyncio.create_task`. This is the existing template we'll generalise into a real `BackgroundJobManager`. |
| `_handle_conversation_tools(...)` | L1084 | Renders confirmation / single-choice / etc. widgets. **This is where yolo mode hooks in** — when active and the tool is *not* a `__must__`-marked confirmation, short-circuit with the default acceptance. |
| `_confirmation_gate_passed` sentinel | L669-685 | Already drives SOP phase auto-completion when a confirmation widget says yes. Yolo will set this same sentinel. |

### 2.2 The Task Tool Today

| File | Role |
|---|---|
| `AgentFoundation/src/agent_foundation/resources/tools/task/tool.json` | Tool manifest (the "front" registered with the conversational inferencer). 16 parameters, all aimed at the BTA dual orchestrator. |
| `OpenStartup/src/openteam/server/resources/tools/task/executor.py` | Real implementation. `_resolve_agent_config()` (lines 51-94) picks a topology YAML; `_run_topology()` instantiates and runs the chosen nested inferencer graph; writes `outputs/` and `outputs/final_deliverables/`. |
| `OpenStartup/src/openteam/server/resources/tools/task/cli.py` | tool.json-driven argparse (per `task-cli-unification-INTEGRATED-v3.md`). |
| `OpenStartup/src/openteam/server/resources/tools/task/topologies/*.yaml` | All preset topologies. |

Workspace today is `<resolve_tool_workspace("task", session_context)>/` containing `outputs/`, `outputs/final_deliverables/`, `_runtime/inferencer_cache/`, JSONL parts files, manifest. **Simple mode wants a flatter, much smaller layout.**

### 2.3 Existing "Background-ish" Surfaces We Can Reuse / Generalise

- `asynchronous=True` tool flag → fire-and-forget `asyncio.create_task` in-process (`conversational_inferencer.py:776-816`). **In-process only**, no PID, no workspace, no queue-back. Generalise to BackgroundJobManager.
- `task` tool already returns a workspace path with `_runtime/` subtree (`unified_workspace_allocation_INTEGRATED_v5_FINAL_plan.md`). `BackgroundJobManager` reuses `resolve_tool_workspace("background_job", session_context)` for direct-command jobs.
- The `--resume` flag on task (`tool.json` line 98) already accepts a workspace; we leverage the same resume contract for repeat-interval jobs (the second tick can `--resume` the first's workspace).

### 2.4 SOP Marker Parsing

- `RichPythonUtils/.../template_manager/sop_manager.py::SOPPhase.directives` is a `list[str]` parsed from `[__a__; __b__; …]`.
- Consumed in two places:
  - `conversational_inferencer.py:678` — `"requires confirmation" in " ".join(directives)` (string-contains, fragile but tolerant).
  - `agent_foundation/server/workflow_context.py:431` — `requires_confirmation = "requires confirmation" in (…)`.
- **We will keep both call sites string-tolerant** (`"requires confirmation" in directive_text` still True for `__requires confirmation__; __must__`). Then we add a small helper `confirmation_strength(directives) -> Literal["must","optional","default"]` consumed only by the yolo gate.

### 2.5 The Workflow-as-First-Class-Citizen Plan's Surfaces (companion)

We assume the following from that plan land first (or get implemented as Phase A.5 of this one):

- `WorkflowDefinition` (frozen dataclass) with `sop_path`, `short_description`, etc.
- `WorkflowRegistry` discovering `resources/workflows/<name>/workflow.json`.
- `WorkflowSessionState` in session JSON: `{active_workflow_id, runs: {wf_id: WorkflowRun}}`.
- Three action tools `enter_workflow`, `exit_workflow`, `resume_workflow` whose executors mutate `prior_context["workflow_state"]` and emit the `_active_workflow_changed` sentinel so `_render_prompt` discards `_sop` / `tool_phase_map` cache.
- `_compute_session_context` provides `available_workflows`, `ongoing_workflows`, `active_workflow_id`, `active_definition_name` keys.

If the companion plan has not yet landed when we ship Phase F (SOP tools), we ship a **minimal facade** in this plan: `SopRegistry` and a thin `SopRun` that satisfies the same contract for SOP-only definitions (no `workflow.json`, just a markdown file). The facade is a 100-LoC stand-in that the companion plan's full registry can later subsume.

### 2.6 Prompt Template

`AgentFoundation/src/agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` is the entry template. `.initial.config.yaml` whitelists `enabled_action_tools`. All new tools must be added there to be agent-visible.

`_variables/workflow_sop/code_optimization.md` (cited by the user) **does not yet exist on disk**. We treat it as illustrative of the intended folder structure: SOP-only definitions (no manifest) live under `_variables/workflow_sop/<name>.md`. The new `SopRegistry` (and later the unified `WorkflowRegistry`) discovers them.

---

## 3. Proposed Architecture

### 3.1 Layered View

```
┌────────────────────────────────────────────────────────────────────────┐
│ User / Slash Commands (/background-job, /sop, /enter-sop, /exit-sop)   │
│ Agent Action Tools  (background_job, enter_workflow, exit_workflow,   │
│                      sop_launch — same names, both surfaces)           │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │ mutates prior_context["jobs"], "sops",
                               │ "workflow_state" via context_updates
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ConversationalInferencer                                               │
│   - UserInputQueue (NEW)                                               │
│   - run_agentic_loop(): drains queue between iterations               │
│   - _render_prompt(): adds Available SOPs, Ongoing Workflows,         │
│                       Background Jobs in Flight sections              │
│   - yolo_mode flag short-circuits non-__must__ confirmations          │
└──────────┬─────────────────────────┬────────────────────────────┬──────┘
           │                         │                            │
           ▼                         ▼                            ▼
┌──────────────────┐    ┌───────────────────────┐    ┌──────────────────────┐
│ SOP / Workflow   │    │ BackgroundJobManager  │    │ Task-Simple Runner   │
│  Registry        │    │  (NEW)                │    │  (NEW)               │
│  (companion plan │    │  - launches subprocs  │    │  - in-process leaf   │
│   + sop_only)    │    │  - tracks PID/state   │    │    inferencer        │
│                  │    │  - scheduler          │    │  - flat workspace    │
│                  │    │  - queue-back hook    │    │  - args/input/raw/   │
│                  │    │  - fork-on-completion │    │    parsed_output     │
└──────────────────┘    └───────────────────────┘    └──────────────────────┘
                                  │ on completion
                                  ▼ enqueue templated message
                          UserInputQueue
```

### 3.2 Core New Types

```python
# agent_foundation/common/inferencers/agentic_inferencers/conversational/user_input_queue.py

@dataclass
class QueuedUserInput:
    content: str
    label: Literal["user", "background_job_completion", "fork_seed"] = "user"
    source_job_id: str | None = None          # if from a background job
    fork_label: bool = False                  # if True, drain by forking a child conversation
    enqueued_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

class UserInputQueue:
    """Thread/async-safe FIFO queue of pending user inputs."""
    def __init__(self) -> None:
        self._items: deque[QueuedUserInput] = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, item: QueuedUserInput) -> None: ...
    async def get_nowait(self) -> QueuedUserInput | None: ...   # used between iterations
    async def get_blocking(self) -> QueuedUserInput: ...         # used at idle
    def peek_all(self) -> list[QueuedUserInput]: ...             # for prompt rendering
    def size(self) -> int: ...
```

```python
# agent_foundation/common/jobs/background_job_manager.py

JobStatus = Literal["scheduled", "running", "completed", "failed", "cancelled"]

@dataclass
class JobSpec:
    job_id: str                                  # "bg-<8hex>"
    cmdline: list[str]                           # argv. For tool jobs, derived; for direct, verbatim.
    job_kind: Literal["tool", "command"]
    tool_name: str | None = None                 # if job_kind == "tool"
    workspace: Path                              # always allocated
    schedule_at: float | None = None             # Unix epoch; None = immediate
    repeat_every: float | None = None            # seconds; None = one-shot
    repeat_count_limit: int | None = None        # None = unbounded
    fork_on_completion: bool = False
    completion_template: str = "[background_job:{job_id}] {tool_name_or_cmd} completed at {finished_at}. Output: {workspace}/output. Logs: {workspace}/job.log"
    created_by: Literal["user", "agent"] = "agent"
    created_at: float = field(default_factory=time.time)

@dataclass
class JobState:
    spec: JobSpec
    status: JobStatus = "scheduled"
    pid: int | None = None
    launched_at: float | None = None
    finished_at: float | None = None
    last_exit_code: int | None = None
    iterations_completed: int = 0
    last_completion_summary: str = ""

class BackgroundJobManager:
    """Owns process lifecycle and persists job state to disk.

    Lifecycle methods are async; the manager runs a small bookkeeping coroutine
    (`_supervisor`) that polls child processes, posts completion to the queue,
    and reschedules repeat jobs.
    """

    def __init__(self, *, jobs_root: Path, queue: UserInputQueue,
                 tool_invoker: Callable[..., Awaitable[Path]] | None = None) -> None: ...

    async def schedule(self, spec: JobSpec) -> JobState: ...
    async def cancel(self, job_id: str) -> bool: ...
    def list_in_flight(self) -> list[JobState]: ...        # for prompt section
    def list_all(self) -> list[JobState]: ...               # includes completed/failed
    def get(self, job_id: str) -> JobState | None: ...
    async def shutdown(self) -> None: ...                   # called on session evict
    # Persistence
    def snapshot(self) -> dict: ...                         # serializable for session_store
    @classmethod
    def restore(cls, snapshot: dict, *, jobs_root: Path,
                queue: UserInputQueue, tool_invoker=...) -> BackgroundJobManager: ...
```

The manager runs subprocesses via `asyncio.create_subprocess_exec`, redirects stdout/stderr to `<workspace>/job.log`, and on completion posts a `QueuedUserInput(label="background_job_completion", source_job_id=spec.job_id, fork_label=spec.fork_on_completion, content=spec.completion_template.format(...))` to the queue.

### 3.3 Conversational Loop Changes (UserInputQueue)

The new shape of the loop driver is roughly:

```python
async def run_agentic_loop(self, content: str | None = None, *, ...):
    # 1. If content is None (idle awakening), block on queue. Otherwise enqueue
    #    `content` as the head item so existing single-content callers still work.
    if content is not None:
        await self.user_input_queue.put(QueuedUserInput(content=content, label="user"))
    # 2. Loop until queue is empty AND no in-flight tool. Each outer iteration
    #    drains one queue item and runs an inner agentic mini-loop (= today's
    #    `for iteration in range(self.max_iterations)`).
    while True:
        item = await self.user_input_queue.get_nowait()
        if item is None:
            break  # idle; let the server decide when to wake us
        if item.fork_label:
            # Hand off to the server-supplied on_fork_requested callback.
            # The forked child gets `item.content` as its first user message
            # AND a copy of the current `prior_context` (sans transient keys).
            await self._on_fork_requested(item)
            continue
        # Otherwise: drain inline. Today's body of run_agentic_loop, parameterised
        # by `item.content`.
        result = await self._run_single_agentic_turn(item.content, ...)
        if result.should_yield():  # e.g. PendingInput
            return result
```

Three subtleties:

1. **Backward compatibility.** All current callers pass `content` as a string and expect one turn. We preserve this: when `content` is non-None we enqueue it, *then* the while-loop drains until empty. Net effect is unchanged for the single-message case because the queue then has exactly one item.
2. **Pending-input return.** When an inner mini-loop yields with `PendingInput` (confirmation widget), we return immediately — leaving any further queued items in place for the next turn. The frontend's response delivery still becomes a separate `run_agentic_loop` call as today.
3. **Server-supplied fork callback.** `ConversationalInferencer` does not own conversation forking; the server (or the subprocess host) does. The inferencer just calls `await self._on_fork_requested(item)` if set. Default behavior when no callback is registered: log a warning, append a synthetic `"[Fork requested but no fork handler registered]"` message to the conversation, and continue.

### 3.4 Prompt Sections

Extend `_render_prompt`'s `feed` with three new keys (also added to `_compute_session_context` in OpenStartup's server when running there):

| Key | When set | Renders | Source |
|---|---|---|---|
| `available_sops` | always when registry non-empty | `## Available SOPs` listing each `WorkflowDefinition` / `SopDefinition`. | SOP/Workflow registry (`registry.list(include_sop_only=True)`) |
| `ongoing_workflows` | always when ≥1 paused run exists | `## Ongoing Workflows` (from companion plan). | `WorkflowSessionState.paused_runs()` |
| `background_jobs_in_flight` | always when ≥1 job in `scheduled`/`running` | `## Background Jobs in Flight` table. | `BackgroundJobManager.list_in_flight()` |
| `yolo_mode_active` | bool | Adds `## Mode: YOLO` warning + reminder that `__must__` confirmations still gate. | inferencer flag |

The "Active Workflow" trio (`<WorkflowDescription>` / `<WorkflowStatus>` / `<WorkflowNextStepGuidance>`) is unchanged from today and from the companion plan.

### 3.5 SOP Marker Extension

Today the directive list per phase contains literal strings like `"depends on Phase 1"`, `"requires confirmation"`. We add **two qualifier tokens** that may appear in the same `[…]` bracket alongside `__requires confirmation__`:

| Marker | Meaning |
|---|---|
| `[__requires confirmation__]` (today) | Default: confirm in interactive mode; in yolo mode, **skip** (treat as auto-accept). |
| `[__requires confirmation__; __must__]` | Confirm **always**, including under yolo. The yolo mode flag is overridden for this phase. |
| `[__requires confirmation__; __optional__]` | Confirm in interactive mode; in yolo mode, **skip**. Explicit version of the default; useful for SOPs that want to be self-documenting. |

A pure helper goes in `agent_foundation.common.sop_directives`:

```python
ConfirmationStrength = Literal["must", "optional", "default"]

def confirmation_strength(directives: Iterable[str]) -> ConfirmationStrength | None:
    """Return None if no confirmation requested, otherwise the strength."""
    text = " ".join(directives).lower()
    if "requires confirmation" not in text:
        return None
    if "__must__" in text or "; must" in text:
        return "must"
    if "__optional__" in text or "; optional" in text:
        return "optional"
    return "default"
```

`_handle_conversation_tools` in yolo mode short-circuits when strength is `"default"` or `"optional"`; honours the widget when `"must"`.

### 3.6 `/sop`, `/enter-sop`, `/exit-sop`

| Surface | Implementation | Inside or outside current conversation? |
|---|---|---|
| `/sop <path-or-name>` | Slash + agent tool `sop_launch`. Launches a **new subprocess**: `python -m agent_foundation.cli.run_conversation --sop <path> --yolo --workspace <bg-job-workspace>`. Subprocess is itself a `BackgroundJobManager`-managed job (re-uses the job lifecycle, logs, completion queue-back). Default `fork_on_completion=False`. | Outside (new process). |
| `/enter-sop <name>` | Slash + agent tool. Thin wrapper that calls the companion plan's `enter_workflow(name=<name>, entry_reason=…)` action tool. If `<name>` is a SOP-only definition (no `workflow.json`), it still works because the `SopRegistry` facade fills in the gaps (default `entry_phase="0"`, no `required_tools`). | Inside (mutates `workflow_state` of current session). |
| `/exit-sop` | Slash + agent tool. Thin wrapper that calls `exit_workflow(workflow_id=<active>, exit_reason=…)`. | Inside. |

The user-typed slash command is parsed by a thin pre-processor in the inferencer's input path (see §4). Agent-invoked variants go through the normal `ToolsToInvoke` dispatch.

### 3.7 Task `--simple` Mode

```
task --simple "<request>"
```

Becomes the default when no other mode flag is present. It runs **one** leaf inferencer (default: `claude_code` CLI variant, which matches the user's "RovoDevCLI inferencer" description). The simple-mode executor:

1. Allocates a flat workspace via `resolve_tool_workspace("task", session_context)`.
2. Builds the implementation's initial prompt by rendering `prompt_templates/task/simple/initial.jinja2` (NEW; minimal — system role + user request).
3. Constructs the leaf inferencer with `cache_folder=<workspace>/stream_cache/` (this is the "streaming cache" the user referenced).
4. Writes `<workspace>/args.json` (the resolved inferencer args), `<workspace>/input.md` (the rendered prompt), `<workspace>/raw_response.txt` (the LLM stream), `<workspace>/output/<parsed_output_files>` (whatever the response parser extracted).
5. Returns `{workspace_path, output_dir, last_response_preview}` as `context_updates`.

The simple mode does NOT invoke BTA, breakdown, aggregation, dual, planner/executor, deliverable boundaries, or any of the heavyweight orchestration. It's roughly 80 LoC of executor code (vs. the current ~500-line BTA orchestrator path).

`--full` and `--agent-config <preset>` reach the existing topology dispatcher unchanged. The `--simple` flag is mutually exclusive with `--full`, `--execute`, `--confirm`, and `--agent-config`.

### 3.8 Yolo Mode End-to-End

`ConversationalInferencer.yolo_mode: bool = attrib(default=False, kw_only=True)`. When True:

- Confirmation widgets short-circuit (default-accept) unless the SOP phase carries `__must__`.
- Other conversation tools (single_choice, multiple_choice, clarification, tool_argument_form) also short-circuit: they pick the **default choice** if declared in the tool spec, else log a warning and pick the **first option**, else for clarification/tool_argument_form they synthesize a placeholder response `[YOLO: no answer provided]` and continue.
- `interactive` is *still allowed* to be a real terminal/web interactive — yolo only short-circuits *blocking* prompts. Streaming text continues to flow to the configured interactive (so the user can watch even in yolo if they want).
- A new `yolo_log_file: Path | None` attrib, if set, captures every short-circuited interaction as a JSONL record `{ts, tool_type, prompt, chosen_value, reason}`.

The headless `/sop` subprocess defaults to `yolo_mode=True` and `interactive=NullInteractive()` (a no-op terminal-style that just discards streaming).

### 3.9 BackgroundJobManager × Forking

When a job has `fork_on_completion=True`, the queued completion message carries `fork_label=True`. On drain, `run_agentic_loop` invokes the server's `on_fork_requested(item)` callback. The OpenStartup server's implementation (when integrated) creates a *new* `session_id`, copies the parent session's `workflow_state`, prior context, and the seed message into it, then resumes the parent conversation **without** consuming the seed inline.

Inside an `/sop` subprocess (no server), the default fork handler instead spawns *another* sibling subprocess via the same `BackgroundJobManager.schedule(...)` with a new SOP entry point — useful for fan-out patterns inside SOPs.

---

## 4. Slash Command Pre-Processor

User-typed slash commands need to bypass the LLM. Today the conversational inferencer has no slash dispatcher (`process_message` in OpenStartup's `manager_websocket_routes.py` notes "no slash commands today; everything is LLM-routed"). We add a tiny pre-processor:

`agent_foundation/common/inferencers/agentic_inferencers/conversational/slash_dispatcher.py`

```python
@dataclass
class SlashCommand:
    name: str                    # "background-job", "sop", "enter-sop", "exit-sop"
    args: list[str]
    raw: str

def try_parse_slash(text: str) -> SlashCommand | None: ...

SlashHandler = Callable[[SlashCommand, ConversationalInferencer], Awaitable[Optional[QueuedUserInput]]]

class SlashRegistry:
    def register(self, name: str, handler: SlashHandler) -> None: ...
    async def dispatch(self, cmd: SlashCommand, inferencer: ConversationalInferencer) -> QueuedUserInput | None:
        """Handler returns either None (consumed silently — e.g. a job was scheduled
        and we don't want to feed anything to the LLM this turn) or a QueuedUserInput
        to inject as the synthesized user message (e.g. /enter-sop synthesizes
        '[slash] Entering SOP code_optimization' which becomes the user content).
        """
```

`run_agentic_loop` (after content is enqueued or queue is drained) checks each `QueuedUserInput`: if its content starts with `/` and matches a registered slash command, the dispatcher handles it; otherwise it feeds the LLM normally. Slash handlers run synchronously and may enqueue further items (the typical pattern for `/background-job` — schedule, then enqueue a confirmation message visible to the user but not the LLM).

Built-in handlers shipped in Phase F:

| Slash | Handler effect |
|---|---|
| `/background-job <spec…>` | Parse args (argparse style); call `BackgroundJobManager.schedule(...)`; enqueue `[Job bg-abc12 scheduled]` user message tagged `metadata={"hide_from_llm": False}` so LLM sees it. |
| `/sop <path-or-name> [--no-yolo]` | Build a JobSpec for `python -m agent_foundation.cli.run_conversation --sop <…> --yolo`. Schedule via job manager. Returns synthesized user message. |
| `/enter-sop <name>` | Emit synthetic `ToolsToInvoke` for `enter_workflow(name=<name>, entry_reason="user /enter-sop")`. Re-enter the agentic mini-loop with this synthetic. |
| `/exit-sop [<workflow_id>]` | Symmetric. |

Both inside the conversation and the subprocess, this pre-processor is identical.

---

## 5. On-Disk Layout

```
<jobs_root>/                                          (NEW; default: <session_root>/jobs/ or _runtime/jobs/)
├── jobs.json                                         # snapshot of all JobStates
└── bg-abc12345/                                      # one per job
    ├── job.json                                      # JobSpec + JobState
    ├── job.log                                       # merged stdout+stderr
    ├── stdin.txt                                     # if any
    └── (per-tool subdir if job_kind=="tool")
        └── (tool's own workspace, e.g. task simple workspace)
```

Task-simple workspace (under `<jobs_root>/bg-abc12345/task/` or `<resolve_tool_workspace("task", session_context)>`):

```
task_<TS>_<uuid8>/
├── args.json                # resolved inferencer args + topology = "simple"
├── input.md                 # rendered initial prompt
├── stream_cache/            # cache_folder of the leaf inferencer
│   └── (provider-specific streamed JSONL)
├── raw_response.txt         # the raw LLM output (or final-output if available)
├── output/                  # parsed_output (whatever the response parser extracted)
│   └── (zero or more files)
└── log.jsonl                # one record per phase: prompt_built, sent, received, parsed, written
```

SOP-only registry directory (Phase F):

```
AgentFoundation/src/agent_foundation/resources/prompt_templates/conversation/main/_variables/workflow_sop/
├── code_optimization.md                # the SOP file (markdown with directives)
├── code_optimization.config.yaml       # OPTIONAL: same shape as today's .sop.config.yaml
├── code_optimization.short.md          # OPTIONAL: short_description for catalog
└── README.md                           # tells humans "drop SOP markdown files here"
```

If the companion plan's `resources/workflows/<name>/` exists, registry surfaces both directories; SOP-only entries get auto-synthesized `WorkflowDefinition`s.

---

## 6. Phased Implementation Plan

Each phase is independently shippable and has its own acceptance tests. Phases A-D do not require the companion workflow-as-first-class-citizen plan; E-G integrate progressively.

### Phase A — UserInputQueue (no behavior change)

**Objective:** Introduce queue plumbing without flipping any existing call site.

**Files (create):**
- `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/user_input_queue.py`
- `AgentFoundation/test/agent_foundation/common/inferencers/agentic_inferencers/conversational/test_user_input_queue.py`

**Files (modify):**
- `conversational_inferencer.py`:
  - Add `user_input_queue: UserInputQueue = attrib(factory=UserInputQueue, kw_only=True)`.
  - Refactor `run_agentic_loop` body into `_run_single_agentic_turn(content, ...)` (mechanical extraction).
  - Public `run_agentic_loop(content, ...)` now: if `content is not None` push to queue; loop while queue non-empty draining one item per iteration; return aggregate `AgenticResult`.
  - Default behavior identical to today when callers pass exactly one `content` and no producer pushes additional items.

**Tests:**
- Single content (legacy path) round-trips identically.
- Two queue items drain in order in one `run_agentic_loop` call.
- Empty queue + content=None returns immediately with empty AgenticResult.

**Acceptance:** all existing conversational inferencer tests pass unchanged.

### Phase B — Slash Pre-Processor (no slash commands yet registered)

**Objective:** Add the dispatcher mechanism with zero registered commands; verify it's a no-op for all current content.

**Files (create):**
- `…/conversational/slash_dispatcher.py`
- `test/…/test_slash_dispatcher.py`

**Files (modify):**
- `conversational_inferencer.py`: in the drain loop, call `slash_registry.dispatch(...)` for any item whose content starts with `/`. With an empty registry the call returns the item unchanged.

**Tests:** content starting with `/` but no registered handler flows to the LLM verbatim.

### Phase C — Yolo Mode + SOP Marker Extension

**Objective:** Implement the gate and the directive helper. Default is `yolo_mode=False` so behaviour unchanged.

**Files (create):**
- `AgentFoundation/src/agent_foundation/common/sop_directives.py` (`confirmation_strength(directives)`)
- `test/agent_foundation/common/test_sop_directives.py`

**Files (modify):**
- `conversational_inferencer.py`:
  - Add `yolo_mode: bool` and `yolo_log_file: Path | None` attribs.
  - In `_handle_conversation_tools`, before dispatching to the interactive: if `self.yolo_mode and _should_short_circuit(tool, current_sop_phase)`, log + return synthesized acceptance.
  - `_should_short_circuit` consults `confirmation_strength(prior_context.get("_sop_current_phase_directives", []))` for confirmation tools.
  - When `_sop` is loaded in `_render_prompt` (line 628), also stash the active phase's directives under `prior_context["_sop_current_phase_directives"]`.
- `agent_foundation/server/workflow_context.py:431` — switch the `requires_confirmation` check to call the new helper (still resolves to a truthy value for back-compat in non-yolo flows).

**Tests:**
- Yolo off → confirmation widget still fires (regression).
- Yolo on + `__requires confirmation__` → auto-accepted.
- Yolo on + `__requires confirmation__; __must__` → widget fires.
- Yolo on + `__requires confirmation__; __optional__` → auto-accepted (same as default).
- Yolo log file is created and one JSONL record written per short-circuit.

**Acceptance:** existing SOP runs unchanged; an explicit yolo-mode test SOP passes end-to-end.

### Phase D — Task `--simple` Mode (new default)

**Objective:** Make `task --simple` the new default; produce the flat workspace.

**Files (create):**
- `OpenStartup/src/openteam/server/resources/tools/task/topologies/simple.yaml` — declarative single-leaf inferencer; `_target_` defaults to `ClaudeCodeCLI` (matches "RovoDevCLI inferencer" semantics).
- `AgentFoundation/src/agent_foundation/resources/prompt_templates/task/simple/initial.jinja2` — minimal prompt.
- `OpenStartup/src/openteam/server/resources/tools/task/_simple_runner.py` — the 80-LoC executor.
- `OpenStartup/test/openteam/resources/tools/task/test_task_simple_mode.py`.

**Files (modify):**
- `task/tool.json`:
  - Add `{"name": "--simple", "type": "flag", "popular": true, "default": true, "description": "Run as a single leaf inferencer with the initial prompt only (default)."}`.
  - Mark `--full`, `--plan`, `--execute`, `--confirm` mutually exclusive with `--simple`.
- `task/executor.py::_resolve_agent_config` (lines 51-94):
  - If `simple is True` (or no other mode flag set), route to `_simple_runner.run(...)` and skip topology resolution entirely.
  - Pass `session_context` through unchanged so workspace allocation honours Path A/B (per the `unified_workspace_allocation` plan).
- `task/cli.py` — no change; argparse picks up the new flag automatically (per `task-cli-unification` contract).

**Tests:**
- Default invocation (`task "hello"`) produces a simple-mode workspace with the expected four artefacts.
- `task --full "hello"` still runs the BTA path.
- `task --simple --full "hello"` raises a CLI validation error.

**Risk:** flipping the default may surprise existing callers. Mitigation: a single global env-var `OPENTEAM_TASK_DEFAULT_MODE=full` restores prior behavior for one release; remove in the release after.

### Phase E — BackgroundJobManager (without queue-back yet)

**Objective:** Generic process launcher with workspace, PID tracking, scheduling, repeat; queue-back happens in F.

**Files (create):**
- `AgentFoundation/src/agent_foundation/common/jobs/__init__.py`
- `AgentFoundation/src/agent_foundation/common/jobs/background_job_manager.py`
- `AgentFoundation/src/agent_foundation/common/jobs/job_spec.py`
- `AgentFoundation/src/agent_foundation/common/jobs/snapshots.py`
- `test/agent_foundation/common/jobs/test_background_job_manager.py`

**Behavior:**
- Tool-kind jobs: in-process execution (call the tool executor directly with the same session_context the parent has). The "subprocess" framing applies only when explicitly needed (e.g. `/sop` launcher). Tool jobs still get their own workspace and `job.log` (captured via a logging handler), so the surface looks uniform.
- Command-kind jobs: `asyncio.create_subprocess_exec(*cmdline, stdout=log, stderr=STDOUT, stdin=DEVNULL, cwd=<workspace>)`.
- Scheduler: a single `_supervisor` coroutine, started lazily on first `schedule()`, drives `await asyncio.sleep(seconds_until_next_event)` loops.
- Repeat: a completed job with `repeat_every` re-schedules a new run (fresh `bg-<8hex>` ID) with `--resume <prev workspace>` if `job_kind=="tool"` and the tool declares `supports_resume=True` in `tool.json`.
- Persistence: `snapshot()` writes `jobs.json` after each state change.

**Tests:**
- One-shot tool job runs and reports completion.
- One-shot command job (`echo hello`) runs; `job.log` contains "hello".
- Scheduled job (3s in the future) does not run early.
- Repeat job runs N times then stops after `repeat_count_limit`.
- Cancel transitions running→cancelled and kills PID.
- snapshot/restore round-trip recovers in-flight jobs.

### Phase F — Wire BackgroundJobManager Into ConversationalInferencer (queue-back + prompt section + slash + tool)

**Objective:** End-to-end background jobs visible in the prompt, postable to the queue, and launchable via slash and agent tool.

**Files (create):**
- `AgentFoundation/src/agent_foundation/resources/tools/background_job/tool.json`
- `AgentFoundation/src/agent_foundation/resources/tools/background_job/executor.py`
- `…/conversational/slash_handlers/background_job_handler.py`
- `test/…/test_background_job_flow.py`

**Files (modify):**
- `conversational_inferencer.py`:
  - New attrib `background_job_manager: BackgroundJobManager | None`.
  - In `_render_prompt`'s `feed`, add `background_jobs_in_flight = bg_mgr.list_in_flight()` formatted for the template.
  - In the drain loop, when a `QueuedUserInput` arrives with `label="background_job_completion"` and `fork_label=False`, feed it to the LLM verbatim (it carries the templated message).
  - When `fork_label=True`, invoke `on_fork_requested` callback (default: log + warn).
- `initial.jinja2` — add `{% if background_jobs_in_flight %}## Background Jobs in Flight\n…{% endif %}` block.
- `.initial.config.yaml` — add `background_job` to `enabled_action_tools`.
- The OpenStartup `ConversationService` (if/when integrated there too) instantiates one `BackgroundJobManager(jobs_root=<session_root>/jobs)` per session and threads `queue=inferencer.user_input_queue`.

**Slash handler:** uses the same `BackgroundJobManager` to schedule. Slash arg parser is generated from `background_job/tool.json` (same convention as `task-cli-unification`).

**Tests:**
- Agent emits `background_job(...)` action tool → manager schedules → job runs → completion message appears in the *next* turn's prompt.
- User types `/background-job find . -name '*.py'` → schedule → on drain the user sees a `[Job bg-… scheduled]` system message.
- Job with `--fork-on-completion` triggers the registered fork callback; without a callback, the warning fires and the conversation continues.
- Prompt's `## Background Jobs in Flight` lists running jobs and disappears when all complete.

### Phase G — SOP/Workflow Registry (SOP-only facade) + `/sop`, `/enter-sop`, `/exit-sop`

**Objective:** Make SOP files first-class catalog items even without `workflow.json`. Enable the three SOP slash/tool surfaces.

**Files (create):**
- `AgentFoundation/src/agent_foundation/common/workflows/sop_registry.py` — minimal `SopRegistry`. If the companion `WorkflowRegistry` already exists, `SopRegistry` is a thin adapter that emits `WorkflowDefinition`s.
- `AgentFoundation/src/agent_foundation/resources/tools/sop/tool.json`
- `AgentFoundation/src/agent_foundation/resources/tools/sop/executor.py`  (=> `sop_launch` action tool that schedules a /sop subprocess)
- `AgentFoundation/src/agent_foundation/resources/tools/enter_sop/tool.json`
- `AgentFoundation/src/agent_foundation/resources/tools/enter_sop/executor.py` (thin shim over `enter_workflow`)
- `AgentFoundation/src/agent_foundation/resources/tools/exit_sop/tool.json`
- `AgentFoundation/src/agent_foundation/resources/tools/exit_sop/executor.py`
- `AgentFoundation/src/agent_foundation/cli/run_conversation.py` — the subprocess entry point (`python -m agent_foundation.cli.run_conversation --sop <path> --yolo [--workspace <dir>]`). Uses `terminal_inferencer_base` for I/O.
- `AgentFoundation/src/agent_foundation/resources/prompt_templates/conversation/main/_variables/workflow_sop/README.md`

**Files (modify):**
- `initial.jinja2` — add `## Available SOPs` section (or a unified `## Available Workflows` when the companion plan has landed).
- `.initial.config.yaml` — add `sop_launch`, `enter_sop`, `exit_sop`.
- `slash_dispatcher`: register `/sop`, `/enter-sop`, `/exit-sop` handlers.
- `conversational_inferencer._render_prompt`: include `available_sops` and `ongoing_workflows` keys (if not yet provided by the companion plan).

**Tests:**
- `/sop path/to/code_optimization.md` schedules a job whose cmdline runs the subprocess; the subprocess's stdout streams to `job.log`; on completion, the queue-back message appears in parent's next turn.
- `/enter-sop code_optimization` makes the SOP active in the current session; `## Active Workflow` block renders the SOP's first phase guidance.
- `/exit-sop` pauses the active SOP; `## Ongoing Workflows` shows it; parent prompt no longer carries the SOP-specific blocks.
- `Available SOPs` catalog lists `code_optimization` once `workflow_sop/code_optimization.md` exists.

### Phase H — Polish & Docs

- Cap `BackgroundJobManager.list_all()` to keep prompt size bounded (default 20 most-recent, configurable).
- Add `meta-cli`-style help text to each new tool's `tool.json`.
- Update CLAUDE.md / README.md to document the new surfaces.
- Add an example SOP (`workflow_sop/code_optimization.md`) so the user has a working reference; treat the user's path as canonical.

---

## 7. Critical-Thinking Risk Register

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Flipping `task` default to `--simple` breaks downstream scripts that assumed BTA quality. | 🔴 High | Phase D ships the `OPENTEAM_TASK_DEFAULT_MODE=full` env-var escape for one release; CHANGELOG + Workplace post. |
| R2 | UserInputQueue inversion: a slow turn lets a flood of background completions accumulate; on next turn the LLM is faced with N messages and goes off-rails. | 🟡 Medium | Cap queue depth (default 8); coalesce identical-job completions; on overflow, write to a sidecar `pending_inputs.jsonl` and inject a summary `[N background jobs completed, see <path>]`. |
| R3 | Yolo mode silently drops important user signals if SOP authors forget to mark `__must__`. | 🟡 Medium | (a) New `lint-sops` CLI that flags every `__requires confirmation__` with no qualifier when found in an SOP destined for headless runs; (b) yolo-mode log file is mandatory; (c) startup banner reminds operators what gets bypassed. |
| R4 | A `fork_on_completion` job whose conversation has no fork handler vanishes silently. | 🟠 Low-Med | Default handler logs an error AND appends the seed text as a normal user message (preserves the data); strict mode raises. |
| R5 | Subprocess `/sop` runners orphan if the parent session dies. | 🟠 Low-Med | `BackgroundJobManager._supervisor` writes a heartbeat; on restore, dead PIDs are marked `failed` with a clear reason. |
| R6 | The leaf inferencer used by `task --simple` differs across operators (some have `claude_code` CLI, some don't). | 🟡 Medium | `simple.yaml` accepts `_target_` override; document that operators may pin via `--override leaf._target_=…`. CI tests both `claude_code` and a `MockApiInferencer` path. |
| R7 | The `_active_workflow_changed` sentinel from the companion plan also needs to invalidate the SOP cache when `/enter-sop` runs. | 🟠 Low | `enter_sop` and `exit_sop` executors must emit `_active_workflow_changed=True` in their `context_updates` (one-line). Covered by the companion plan's pattern. |
| R8 | Slash dispatcher swallows legitimate user text that happens to start with `/` (e.g. "/path/to/file"). | 🟠 Low | Restrict slash parser to `^/[a-z][a-z0-9-]*(\s|$)` and require the matched name to be in the registry; otherwise pass through verbatim. |
| R9 | Conversation forking duplicates session state non-trivially (workflow runs, jobs, …) — risk of cross-talk. | 🟡 Medium | Fork handler deep-copies `prior_context` minus transient keys; new session gets a fresh `BackgroundJobManager` (does NOT inherit parent's jobs). Documented in §3.9. |
| R10 | Repeat-interval jobs accumulate workspaces forever. | 🟠 Low | `repeat_count_limit` enforced; an `--gc-after-days` flag on the manager prunes finished workspaces. |
| R11 | Yolo mode + a confirmation widget that *also* drives `_confirmation_gate_passed` (SOP auto-completion of empty phases). | 🟡 Medium | Yolo short-circuit must still set `_confirmation_gate_passed=True` when the SOP phase carries `__requires confirmation__` (default or optional), so the SOP keeps advancing. Covered by Phase C tests. |
| R12 | Race: background job completes *during* a turn that is itself emitting many tool calls. | 🟠 Low | Queue is async-safe; we only drain *between* iterations, never mid-iteration. Existing per-session inferencer dict already serialises turn boundaries. |

---

## 8. Open Design Questions (need user confirmation before Phase F)

1. **Default `completion_template`.** The plan's default is `"[background_job:{job_id}] {tool_name_or_cmd} completed at {finished_at}. Output: {workspace}/output. Logs: {workspace}/job.log"`. Acceptable, or should it be terser/richer (include exit code, runtime, last 5 stdout lines)?
2. **Forked conversation seed semantics.** Currently the fork inherits `workflow_state` and `prior_context`. Does the user want it to instead start clean (purely a new conversation seeded with the job's output text)?
3. **Queue depth cap.** Default 8. Reasonable, or higher?
4. **Yolo mode log location.** Default: `<session_root>/yolo.log`. Reasonable?
5. **`/sop` workspace.** Defaults to `<session_root>/sops/<sop-name>_<TS>_<uuid8>/`. Acceptable, or should every `/sop` launch share `<session_root>/jobs/`?
6. **Repeat jobs and SOP phases.** If a repeat-interval job is launched while inside an active SOP, should completion messages also try to auto-advance the SOP, or stay neutral? Plan defaults to neutral — completion is just feed to the LLM, which decides.
7. **`/sop <name-or-path>` resolution order.** Plan: try path first (file exists), else look up by name in `SopRegistry`. Acceptable?
8. **Action tool naming.** Plan uses `background_job`, `sop_launch`, `enter_sop`, `exit_sop` (snake_case). The slash mirrors are kebab-case. Both follow existing conventions in the codebase. Acceptable?

---

## 9. Critical Files

**Already exist (will be modified):**
- `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` — main loop refactor (Phase A), slash dispatch (B), yolo (C), background jobs section + queue-back (F), available_sops section (G).
- `AgentFoundation/src/agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` — new sections (F, G).
- `AgentFoundation/src/agent_foundation/resources/prompt_templates/conversation/main/.initial.config.yaml` — enable new tools (F, G).
- `AgentFoundation/src/agent_foundation/server/workflow_context.py:431` — switch to `confirmation_strength` helper (C).
- `OpenStartup/src/openteam/server/resources/tools/task/executor.py` — route to `_simple_runner` (D).
- `OpenStartup/src/openteam/server/resources/tools/task/tool.json` — add `--simple` flag and mutex group (D).
- `AgentFoundation/src/agent_foundation/resources/tools/task/tool.json` (if it diverges from the OpenStartup one — they currently look like two copies; align with the OpenStartup-authoritative version).

**New files:**
- `AgentFoundation/.../conversational/user_input_queue.py` (A)
- `AgentFoundation/.../conversational/slash_dispatcher.py` (B)
- `AgentFoundation/.../conversational/slash_handlers/{background_job,sop,enter_sop,exit_sop}_handler.py` (F, G)
- `AgentFoundation/src/agent_foundation/common/sop_directives.py` (C)
- `AgentFoundation/src/agent_foundation/common/jobs/{background_job_manager,job_spec,snapshots,__init__}.py` (E)
- `AgentFoundation/src/agent_foundation/common/workflows/sop_registry.py` (G)
- `AgentFoundation/src/agent_foundation/cli/run_conversation.py` (G)
- `AgentFoundation/src/agent_foundation/resources/tools/{background_job,sop,enter_sop,exit_sop}/{tool.json,executor.py}` (F, G)
- `OpenStartup/src/openteam/server/resources/tools/task/topologies/simple.yaml` (D)
- `OpenStartup/src/openteam/server/resources/tools/task/_simple_runner.py` (D)
- `AgentFoundation/src/agent_foundation/resources/prompt_templates/task/simple/initial.jinja2` (D)

**Existing utilities to reuse:**
- `resolve_tool_workspace(tool_name, session_context)` from `OpenStartup/src/openteam/server/resources/tools/_shared/workspace_allocator.py` (per `unified_workspace_allocation_INTEGRATED_v5_FINAL_plan.md`). Reuse for `task --simple` workspace AND for `BackgroundJobManager` direct-command job workspaces.
- `SOPManager.load(path)` and `SOPManager.render_guidance(tracker, sop, context)` from `rich_python_utils.string_utils.formatting.template_manager.sop_manager` — unchanged; the new `confirmation_strength` helper reads the same directives the manager already parses.
- `StateGraphTracker` from `rich_python_utils.common_objects.workflow.stategraph` — unchanged.
- `tool_cli.run_cli(tool_json_path, execute_fn, …)` from `OpenStartup/src/openteam/server/services/tool_cli.py` — reuse for every new tool's CLI shim (background_job, sop, enter_sop, exit_sop).
- `asynchronous=True` flag pattern in `conversational_inferencer._execute_tool_call` (L778-816) — generalised by `BackgroundJobManager`; the existing flag handlers are kept as a thin shim that delegates to `bg_mgr.schedule(JobSpec(job_kind="tool", …))`.
- `TerminalInferencerBase` (in `agent_foundation/common/inferencers/terminal_inferencers/`) for the subprocess `cli/run_conversation.py` I/O loop.
- Token/event-streaming primitives in `agent_foundation/common/streaming/markers.py` — reused unchanged by simple-mode workspace's `stream_cache/`.

**Companion plan to integrate with:**
- `OpenStartup/_dev/_plan/workflow-as-first-class-citizen.md` — when its `WorkflowRegistry` lands, the SopRegistry facade collapses into a `sop_only=True` adapter rendering `WorkflowDefinition`s. Both plans deliberately use the same `_active_workflow_changed` sentinel, the same `prior_context["workflow_state"]` shape, and the same `enter_workflow`/`exit_workflow` executor contract. `/enter-sop` and `/exit-sop` are 30-line shims over those tools.

---

## 10. Verification

End-to-end smoke (Phase H):

```bash
# 1. Default behavior unchanged for legacy conversational sessions.
pytest AgentFoundation/test/agent_foundation/common/inferencers/agentic_inferencers/conversational/ -q

# 2. Task simple mode is default.
openteam-task "list the python files in this repo"          # produces flat workspace
ls _runtime/tasks/task/task_*/{args.json,input.md,raw_response.txt,output,stream_cache}
openteam-task --full "list the python files in this repo"   # full BTA still works
OPENTEAM_TASK_DEFAULT_MODE=full openteam-task "…"           # one-release escape works

# 3. Yolo mode + SOP markers.
pytest AgentFoundation/test/agent_foundation/common/test_sop_directives.py -q
python -m agent_foundation.cli.run_conversation \
    --sop AgentFoundation/.../workflow_sop/code_optimization.md --yolo \
    --workspace /tmp/sop_smoke
grep -c "auto-accepted (yolo)" /tmp/sop_smoke/yolo.log     # > 0
grep -c "must-confirm fired"  /tmp/sop_smoke/yolo.log     # > 0 if SOP has __must__ markers

# 4. Background jobs flow.
pytest AgentFoundation/test/agent_foundation/common/jobs/ -q
pytest AgentFoundation/test/.../test_background_job_flow.py -q
# Manual: in a live session, ask agent "schedule a 5s timer that pings me", inspect:
#   - prompt's "## Background Jobs in Flight" section
#   - <session_root>/jobs/bg-*/job.log
#   - next turn's prompt contains the templated completion message

# 5. SOP slash commands.
# In a live session:
#   /sop AgentFoundation/.../workflow_sop/code_optimization.md
#   → background job spawned; "Available SOPs" lists it.
#   /enter-sop code_optimization
#   → "Active Workflow (wf-<id>)" block appears; SOP phases drive the agent.
#   /exit-sop
#   → SOP moves to "Ongoing Workflows" pause list.

# 6. Snapshot/restore.
# Kill the server mid-conversation with an in-flight repeat job + a paused SOP.
# Restart; verify the job resumes (or is marked failed with a clear reason) and the
# paused SOP is still in "Ongoing Workflows".
```

Specific regression tests (Phase A onward):
- Existing `conversational_inferencer` tests (~currently ~30 tests under `agentic_inferencers/conversational/`) must remain green for every phase.
- Existing `task` tests (under `OpenStartup/test/openteam/resources/tools/task/`) must remain green; `--full` is added to any test that asserted on the old default's BTA artefacts.
- Existing SOP-bearing conversation E2Es (e.g. role-creation flow) must remain green — they use the default-confirmation marker, and yolo mode is OFF by default.

---

## 11. Mapping the User's Request → This Plan

| User's intent (paraphrased) | Where addressed |
|---|---|
| "Task tool support `--simple` mode … workspace might only have streaming cache, logs with inferencer args/input/response, output parsed from raw response. By default let's use simple mode." | §3.7, Phase D. New default; flat workspace; OPENTEAM_TASK_DEFAULT_MODE escape hatch. |
| "Conversational inferencer needs to support user input queue." | §3.3, Phase A. UserInputQueue + refactored drain loop. |
| "Enhance conversational inferencer to support background jobs … put background task output into user input queue with template …" | §3.2, §3.3, §3.4 (G7), Phases E + F. BackgroundJobManager + queue-back + templated completion + prompt section. |
| "Background jobs can be scheduled at some time, and can repeat at a schedule." | §3.2 (`JobSpec.schedule_at`, `repeat_every`, `repeat_count_limit`), Phase E. |
| "Generic job manager class record the launching command line, the process id, launching time etc." | §3.2 (`JobState.pid`, `launched_at`, `cmdline` on spec), Phase E. |
| "Root folder path for job workspaces, for tool-based jobs each job typically manages its own workspace … for direct command execution we create a workspace folder for it and redirect its stdout and stderr to files." | §3.2, §5 (on-disk layout). `jobs_root` + `<job_id>/job.log`. |
| "Background jobs are supported through tool `/background-job`." | §3.6, Phase F. Slash command + agent action tool. |
| "`/background-job task …` …`/background-job find …`" | §4 (slash handler dispatches by first token: matches tool registry → tool-job; else → command-job), Phase F. |
| "`--fork-on-completion` … creates a new conversation and forks from there." | §3.9, Phase F. `fork_label=True` queued items invoke `on_fork_requested` callback. |
| "Conversational inferencer template need to have a section holding current running background jobs and their status." | §3.4 (G7), Phase F. `## Background Jobs in Flight` section. |
| "Conversational inferencer support yolo mode … typically won't confirm with users …" | §3.8, Phase C. |
| "If there is `[__requires confirmation__; __must__]` … `__must__` means this confirmation must happen and overrides the yolo mode." | §3.5, Phase C. `confirmation_strength` helper. |
| "Create a sop tool, `/sop`, which can launch a new conversational inferencer in a subprocess in yolo mode loading a sop …" | §3.6, Phase G. `sop_launch` action tool + `/sop` slash + `cli/run_conversation.py` entry point. |
| "Create `/enter-sop` and `/exit-sop` tools … loading/exiting an sop in the current conversation." | §3.6, Phase G. Thin shims over `enter_workflow`/`exit_workflow`. |
| "Available sops present in the conversational inferencer context, agent can decide to enter or exit an sop based on user ask." | §3.4, Phase G. `## Available SOPs` section + decision guidance prose in `initial.jinja2`. |
| "Some reference `OpenStartup/_dev/_plan/workflow-as-first-class-citizen.md`." | §2.5, §9, §10. Companion plan integration explicit; SOPs as the SOP-only subset of WorkflowDefinitions. |

---

## 12. Quick-Glance Summary for the Reviewer

> We make `task --simple` the new default (one leaf inferencer, flat workspace with args/input/raw_response/parsed_output + stream cache). We add a `UserInputQueue` to the conversational inferencer so the per-turn driver drains multiple inputs in order. We add a `BackgroundJobManager` that launches tools (default: simple-mode `task`) and direct commands as scheduled or repeating subprocesses, each with its own workspace and `job.log`; completions enqueue templated messages back into the inferencer, with an optional `--fork-on-completion` that delegates to a server-supplied fork callback. We add yolo mode that auto-accepts confirmation widgets except when the SOP phase carries an extended `[__requires confirmation__; __must__]` marker. We add `/background-job`, `/sop`, `/enter-sop`, `/exit-sop` as both slash commands (parsed by a new pre-processor) and agent action tools, where `/sop` schedules a subprocess `cli/run_conversation` in yolo mode and `/enter-sop`/`/exit-sop` are thin shims over the companion plan's `enter_workflow`/`exit_workflow` tools. Prompt template gains `## Available SOPs`, `## Ongoing Workflows`, and `## Background Jobs in Flight` sections. Eight independently shippable phases; phases A–C are pure plumbing with no behavior change; D flips the task default; E–G layer in the new behaviors; H polishes. The chokepoint changes are all in `conversational_inferencer.py` (loop refactor, yolo gate, prompt feed) and `task/executor.py` (simple-mode short-circuit).
