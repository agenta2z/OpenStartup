# Chapter 3 — F3: Background Jobs (`BackgroundJob` + `JobManager` + `/background-job`)

> **Implements:** F3 from `README.md`
> **Depends on:** F1 (chapter 1, for the simple-mode invocation of `task`), F2 (chapter 2, for the input queue)
> **Touches:** new `common/jobs/` package; new `resources/tools/background_job/`; conversational inferencer prompt template (chapter 6)

---

## 1. Goal

> **Important workspace clarification (post-review with chapter 1):**
> The `<runtime_root>/_jobs/bg-<id>/` workspaces referenced throughout this
> chapter are **JobManager bookkeeping workspaces** — they hold the
> subprocess's stdout/stderr capture, the `meta.json` lifecycle record, and
> the schedule state. They are NOT where the inner work happens.
>
> When `/background-job task ...` is invoked, TWO independent workspaces
> are produced:
> - **`<runtime_root>/_jobs/bg-<id>/`** — JobManager's own dir (this chapter)
> - **`<runtime_root>/tasks/task/task_<ts>_<8hex>/`** — the inner `/task`
>   run's own workspace, following the existing convention (chapter 1).
>   This is created by the subprocess CLI when it executes; the JobManager
>   never touches it.
>
> For `JobKind.COMMAND` (raw shell command), there is NO inner workspace —
> only the JobManager's `_jobs/bg-<id>/` dir holds the stdout/stderr.
>
> For `JobKind.SOP` (chapter 5), the SOP runner subprocess writes to its
> own structured workspace (whatever conventions chapter 5 establishes); the
> JobManager's `_jobs/bg-<id>/` is again only for subprocess-level
> bookkeeping.

Introduce a unified background-job abstraction:

- **`BackgroundJob`** — a single dataclass capturing a launched process: kind,
  cmdline, PID, workspace (the JobManager bookkeeping dir, NOT the inner-tool
  workspace), status, schedule, completion callback.
- **`JobManager`** — a per-process singleton that owns the lifecycle of all
  background jobs: spawning, scheduling (one-shot / repeated / at), polling
  status, persisting metadata, routing completion events to the right
  parent inferencer's input queue.
- **`/background-job`** — a slash-command tool that submits a new job. Three
  forms:
  - `/background-job task <request>` — launch the `task` tool (in simple
    mode by default, per F1) in the background.
  - `/background-job <other-tool> <args>` — launch any registered tool.
  - `/background-job <shell-cmd> <args>` — first word doesn't match any
    tool ⇒ treat as a raw shell command. Stdout/stderr captured to files.
- **`--fork-on-completion`** — instead of injecting into the parent's input
  queue, on completion the job triggers a NEW conversation session forked
  from the parent's context.
- **Scheduling**: `--at <ISO>` for delayed start; `--every <duration>` for
  repeated runs.

---

## 2. Current State (recap)

- No formal background-job abstraction in AgentFoundation today.
- ~30 files use `subprocess.Popen` / `asyncio.create_task` ad-hoc.
- No PID tracking, no completion-routing, no schedule.
- "Fork" exists only as conversation-branching in
  `agent_foundation/agents/agent.py` and the rovodev bridge — NOT process
  fork; we'll repurpose the term for *session* fork.

---

## 3. Design

### 3.1 Package layout

New package: `AgentFoundation/src/agent_foundation/common/jobs/`

```
common/jobs/
├── __init__.py
├── models.py             # BackgroundJob + JobStatus + JobSchedule dataclasses
├── manager.py            # JobManager singleton
├── runner.py             # subprocess launcher (tool / command / sop)
├── workspace.py          # allocate_job_workspace (already from chapter 1)
├── leaf_factory.py       # make_leaf_inferencer (already from chapter 1)
├── schedule.py           # schedule loop (one-shot, repeat, at-time)
├── fork.py               # ForkRouter — turns BackgroundJobComplete into a new session
├── persistence.py        # meta.json atomic read/write
├── parser.py             # parse_background_job_args (slash-cmd → submission spec)
└── tests/                # unit tests
```

### 3.2 Dataclasses (`models.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional


class JobStatus(str, Enum):
    PENDING = "pending"           # submitted, not yet started
    SCHEDULED = "scheduled"       # awaiting --at time
    RUNNING = "running"           # currently executing
    DONE = "done"                 # finished successfully
    FAILED = "failed"             # exited non-zero or exception
    CANCELLED = "cancelled"       # killed by user/manager
    TIMEOUT = "timeout"           # exceeded max_wallclock


class JobKind(str, Enum):
    TOOL = "tool"                 # invoke a registered tool (e.g. /task)
    COMMAND = "command"           # raw shell command
    SOP = "sop"                   # subprocess SOP runner (chapter 5)


@dataclass
class JobSchedule:
    """When/how often to run."""
    mode: Literal["once", "at", "every"] = "once"
    at: Optional[str] = None              # ISO8601 for "at"
    every_seconds: Optional[int] = None   # interval for "every"
    max_runs: Optional[int] = None        # cap for "every" (None = unlimited)
    runs_completed: int = 0


@dataclass
class BackgroundJob:
    id: str                        # short uuid, e.g., "bg-7f2c3a"
    kind: JobKind
    cmdline: list[str]             # canonical argv, for display + logs
    workspace: Path                # <session_root>/_jobs/<id>/
    session_id: str                # parent session that owns this job
    status: JobStatus = JobStatus.PENDING
    pid: Optional[int] = None
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    exit_code: Optional[int] = None
    exit_status: str = ""          # "success" | "failed" | etc.
    schedule: JobSchedule = field(default_factory=JobSchedule)
    fork_on_completion: bool = False
    max_wallclock_seconds: Optional[int] = None
    # User-facing label for the prompt block (chapter 6)
    label: str = ""
    # Last N lines of output for the prompt block; refreshed every poll
    last_output_tail: str = ""
    # Inferencer-injectable summary (populated by post-completion hook)
    summary: str = ""

    def to_meta_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "cmdline": self.cmdline,
            "workspace": str(self.workspace),
            "session_id": self.session_id,
            "status": self.status.value,
            "pid": self.pid,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "exit_status": self.exit_status,
            "schedule": {
                "mode": self.schedule.mode,
                "at": self.schedule.at,
                "every_seconds": self.schedule.every_seconds,
                "max_runs": self.schedule.max_runs,
                "runs_completed": self.schedule.runs_completed,
            },
            "fork_on_completion": self.fork_on_completion,
            "max_wallclock_seconds": self.max_wallclock_seconds,
            "label": self.label,
            "summary": self.summary,
        }

    @classmethod
    def from_meta_dict(cls, d: dict[str, Any]) -> "BackgroundJob":
        sch = d.get("schedule", {})
        return cls(
            id=d["id"],
            kind=JobKind(d["kind"]),
            cmdline=d["cmdline"],
            workspace=Path(d["workspace"]),
            session_id=d["session_id"],
            status=JobStatus(d["status"]),
            pid=d.get("pid"),
            submitted_at=d.get("submitted_at", ""),
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            exit_code=d.get("exit_code"),
            exit_status=d.get("exit_status", ""),
            schedule=JobSchedule(
                mode=sch.get("mode", "once"),
                at=sch.get("at"),
                every_seconds=sch.get("every_seconds"),
                max_runs=sch.get("max_runs"),
                runs_completed=sch.get("runs_completed", 0),
            ),
            fork_on_completion=d.get("fork_on_completion", False),
            max_wallclock_seconds=d.get("max_wallclock_seconds"),
            label=d.get("label", ""),
            summary=d.get("summary", ""),
        )
```

### 3.3 `JobManager`

```python
class JobManager:
    """Process-wide singleton tracking all BackgroundJob instances.

    Responsibilities:
      - allocate workspace + meta.json on submission
      - spawn process via runner.spawn(job)
      - poll status (PID alive? exit code?) on a single background task
      - on completion: read summary, atomic-update meta.json, route to parent
      - rehydrate on process startup (scan _jobs/ for unresolved meta.json)
      - cancel(job_id) → SIGTERM with grace, then SIGKILL
    """

    _instance: "JobManager | None" = None

    def __init__(self):
        self._jobs: dict[str, BackgroundJob] = {}
        # session_id → ConversationalInputQueue (registered by inferencers
        # at construction time via register_session)
        self._session_queues: dict[str, "ConversationalInputQueue"] = {}
        self._poll_task: asyncio.Task | None = None
        self._poll_interval = 1.0   # seconds
        self._fork_router: "ForkRouter | None" = None  # set by server bootstrap

    @classmethod
    def instance(cls) -> "JobManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_session(self, session_id: str, queue: "ConversationalInputQueue") -> None:
        self._session_queues[session_id] = queue

    def unregister_session(self, session_id: str) -> None:
        self._session_queues.pop(session_id, None)

    def set_fork_router(self, router: "ForkRouter") -> None:
        self._fork_router = router

    async def submit(self, spec: "JobSubmissionSpec") -> BackgroundJob:
        """Create + persist + spawn a new job."""
        job_id = f"bg-{uuid.uuid4().hex[:6]}"
        workspace = allocate_job_workspace(job_id, spec.session_root, subdir="_jobs")
        job = BackgroundJob(
            id=job_id,
            kind=spec.kind,
            cmdline=spec.cmdline,
            workspace=workspace,
            session_id=spec.session_id,
            schedule=spec.schedule,
            fork_on_completion=spec.fork_on_completion,
            max_wallclock_seconds=spec.max_wallclock_seconds,
            label=spec.label or " ".join(spec.cmdline[:3]),
        )
        self._jobs[job_id] = job
        write_meta(workspace, job)

        if job.schedule.mode == "once":
            await self._spawn_now(job)
        elif job.schedule.mode == "at":
            asyncio.create_task(self._schedule_at(job))
        elif job.schedule.mode == "every":
            asyncio.create_task(self._schedule_every(job))

        self._ensure_poll_task()
        return job

    async def _spawn_now(self, job: BackgroundJob) -> None:
        from agent_foundation.common.jobs.runner import spawn
        proc_handle = await spawn(job)
        job.pid = proc_handle.pid
        job.started_at = datetime.now(timezone.utc).isoformat()
        job.status = JobStatus.RUNNING
        write_meta(job.workspace, job)

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval)
            for job in list(self._jobs.values()):
                if job.status != JobStatus.RUNNING:
                    continue
                ended = await self._check_done(job)
                if ended:
                    await self._on_completion(job)

    async def _check_done(self, job: BackgroundJob) -> bool:
        """Return True if process has ended (also sets exit_code/status)."""
        if job.pid is None: return False
        try:
            # Non-blocking waitpid
            done_pid, status = os.waitpid(job.pid, os.WNOHANG)
            if done_pid == 0:
                return False
            job.exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 1
            job.exit_status = "success" if job.exit_code == 0 else "failed"
            job.status = JobStatus.DONE if job.exit_code == 0 else JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc).isoformat()
            write_meta(job.workspace, job)
            return True
        except ChildProcessError:
            # Process already reaped (e.g., asyncio.create_subprocess_exec did the wait)
            # Fall back to checking if /proc/<pid> exists.
            return not _pid_alive(job.pid)

    async def _on_completion(self, job: BackgroundJob) -> None:
        # 1. Read tail of stdout / stderr for summary
        summary = build_summary(job)
        job.summary = summary
        write_meta(job.workspace, job)

        # 2. Repeat?
        if job.schedule.mode == "every":
            job.schedule.runs_completed += 1
            if job.schedule.max_runs is None or job.schedule.runs_completed < job.schedule.max_runs:
                asyncio.create_task(self._reschedule_every(job))

        # 3. Route to parent
        if job.fork_on_completion and self._fork_router is not None:
            await self._fork_router.fork_from_completion(job)
            return

        queue = self._session_queues.get(job.session_id)
        if queue is None:
            logger.warning("Job %s completed but session %s not registered; "
                           "completion will replay on session rehydrate.",
                           job.id, job.session_id)
            return
        await queue.push(BackgroundJobComplete(
            job_id=job.id,
            job_kind=job.kind.value,
            cmdline=" ".join(job.cmdline),
            workspace=str(job.workspace),
            exit_status=job.exit_status,
            summary=summary,
            fork_on_completion=False,
        ))

    async def cancel(self, job_id: str, grace_seconds: int = 5) -> bool:
        ...

    def list_running(self, session_id: Optional[str] = None) -> list[BackgroundJob]:
        jobs = list(self._jobs.values())
        if session_id:
            jobs = [j for j in jobs if j.session_id == session_id]
        return [j for j in jobs if j.status in (JobStatus.RUNNING, JobStatus.SCHEDULED, JobStatus.PENDING)]

    def rehydrate(self, session_root: Path) -> None:
        """On process startup, scan _jobs/ for unresolved meta.json files."""
        jobs_dir = session_root / "_jobs"
        if not jobs_dir.is_dir(): return
        for meta_path in jobs_dir.glob("*/meta.json"):
            try:
                d = json.loads(meta_path.read_text())
                job = BackgroundJob.from_meta_dict(d)
            except Exception as e:
                logger.warning("Failed to rehydrate %s: %s", meta_path, e)
                continue
            if job.status == JobStatus.RUNNING:
                # Process probably dead now (server restart). Mark FAILED.
                if not _pid_alive(job.pid):
                    job.status = JobStatus.FAILED
                    job.exit_status = "failed_orphaned"
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    write_meta(job.workspace, job)
                    # Will route on next session register
            self._jobs[job.id] = job
```

### 3.4 The runner (`runner.py`)

Dispatches by `JobKind`:

```python
async def spawn(job: BackgroundJob) -> ProcHandle:
    """Spawn the job's process, redirect stdout/stderr to workspace files."""
    stdout_path = job.workspace / "stdout.log"
    stderr_path = job.workspace / "stderr.log"

    if job.kind == JobKind.COMMAND:
        # Raw shell command. Use shell=True only when cmdline is a single
        # composite string; otherwise exec the argv directly.
        proc = await asyncio.create_subprocess_exec(
            *job.cmdline,
            stdout=open(stdout_path, "wb"),
            stderr=open(stderr_path, "wb"),
            cwd=str(job.workspace),
            env=_clean_env(),
            start_new_session=True,   # so we can SIGKILL the whole pgroup
        )
        return ProcHandle(pid=proc.pid, proc=proc)

    elif job.kind == JobKind.TOOL:
        # Invoke a tool via the standalone CLI bridge. For 'task' this is
        # `python -m openteam.server.resources.tools.task <args>`. The CLI
        # supports `--simple` (default) per F1; the runner does NOT need to
        # re-derive the simple flag.
        return await _spawn_tool_cli(job, stdout_path, stderr_path)

    elif job.kind == JobKind.SOP:
        # Subprocess conversational inferencer in YOLO mode (chapter 5)
        return await _spawn_sop_subprocess(job, stdout_path, stderr_path)
```

`_spawn_tool_cli`:

```python
async def _spawn_tool_cli(job, stdout_path, stderr_path):
    # job.cmdline[0] is the tool name, e.g., "task"
    tool_name = job.cmdline[0]
    cli_module = TOOL_CLI_MODULE.get(tool_name)
    if cli_module is None:
        raise ValueError(f"No standalone CLI bridge for tool: {tool_name}")
    args = [sys.executable, "-m", cli_module, *job.cmdline[1:]]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=open(stdout_path, "wb"),
        stderr=open(stderr_path, "wb"),
        cwd=str(job.workspace),
        env=_clean_env(),
        start_new_session=True,
    )
    return ProcHandle(pid=proc.pid, proc=proc)
```

`TOOL_CLI_MODULE` (e.g.,
`{"task": "openteam.server.resources.tools.task.cli"}`) is populated from
each tool's `tool.json` `"cli_module"` field (new optional field). Tools
without a CLI bridge cannot be backgrounded.

### 3.5 The `/background-job` tool

`AgentFoundation/src/agent_foundation/resources/tools/background_job/tool.json`:

```json
{
  "name": "background_job",
  "aliases": ["background-job", "bg"],
  "tool_type": "Action",
  "category": "system",
  "asynchronous": false,
  "description": "Submit a tool invocation or shell command as a background job. The job runs in a separate process; completion notifies this conversation via the input queue.",
  "parameters": [
    {
      "name": "command",
      "type": "string",
      "required": true,
      "positional": true,
      "description": "Tool name + args, or raw shell command. First whitespace token is matched against the tool registry; if no match, treated as a shell cmd."
    },
    {
      "name": "--fork-on-completion",
      "type": "flag",
      "description": "On completion, spawn a NEW conversation session forked from this one, with the job output as the seed message. The current session is NOT notified."
    },
    {
      "name": "--at",
      "type": "string",
      "description": "Delay first run until this ISO8601 timestamp."
    },
    {
      "name": "--every",
      "type": "string",
      "description": "Repeat every <duration>, e.g., '15m', '1h', '2d'. Combine with --max-runs to cap iterations."
    },
    {
      "name": "--max-runs",
      "type": "int",
      "description": "Cap number of repetitions (default: unlimited)."
    },
    {
      "name": "--timeout",
      "type": "string",
      "description": "Max wallclock per run, e.g., '30m'. SIGTERM then SIGKILL on expiry."
    },
    {
      "name": "--label",
      "type": "string",
      "description": "Short label shown in the Running Background Jobs prompt block."
    }
  ],
  "examples": [
    "/background-job task \"implement feature X\"",
    "/background-job task \"refactor module Y\" --fork-on-completion",
    "/background-job task \"add tests for service A\" --every 1h --max-runs 24",
    "/background-job 'rg --json TODO src/ > todos.json'",
    "/background-job /monitor --type pull_request --every 30m",
    "/background-job /sop code_optimization --at 2026-05-20T09:00:00Z"
  ],
  "executor_module": "agent_foundation.resources.tools.background_job.executor"
}
```

Executor (`executor.py`):

```python
async def execute(arguments: dict, session_context: dict) -> ToolExecutionResult:
    spec = parse_background_job_args(arguments, session_context)
    job = await JobManager.instance().submit(spec)
    return ToolExecutionResult(
        success=True,
        output=(f"Background job {job.id} submitted ({job.kind.value}). "
                f"Workspace: {job.workspace}. "
                f"You will be notified when it completes."),
        artifacts={"job_id": job.id, "workspace": str(job.workspace)},
    )
```

### 3.6 Slash-parser logic (`parser.py`)

```python
def parse_background_job_args(arguments: dict, session_context: dict) -> JobSubmissionSpec:
    raw = arguments["command"].strip()
    # Tokenize with shlex to respect quotes
    tokens = shlex.split(raw)
    if not tokens:
        raise ValueError("/background-job requires a command")

    first = tokens[0].lstrip("/")
    tool_registry = get_tool_registry()  # already populated process-wide

    if first in tool_registry:
        kind = JobKind.TOOL
        cmdline = [first] + tokens[1:]
        # Special-case `task` with no explicit mode flag: ensure --simple is set
        # (F1 default, but the standalone CLI inherits the same defaulting).
        if first == "task" and not any(
            t in tokens for t in ("--simple", "--full", "--plan", "--confirm", "--execute")
        ):
            cmdline.append("--simple")
    elif first in {"sop"} or first.startswith("sop-"):
        # /background-job sop <name> args... → SOP subprocess (chapter 5)
        kind = JobKind.SOP
        cmdline = tokens
    else:
        kind = JobKind.COMMAND
        cmdline = tokens

    schedule = JobSchedule()
    if "--at" in arguments:
        schedule = JobSchedule(mode="at", at=arguments["--at"])
    elif "--every" in arguments:
        schedule = JobSchedule(
            mode="every",
            every_seconds=parse_duration_seconds(arguments["--every"]),
            max_runs=arguments.get("--max-runs"),
        )

    return JobSubmissionSpec(
        kind=kind,
        cmdline=cmdline,
        session_id=session_context["session_id"],
        session_root=session_root_from_context(session_context),
        schedule=schedule,
        fork_on_completion=bool(arguments.get("--fork-on-completion")),
        max_wallclock_seconds=parse_duration_seconds(arguments.get("--timeout") or "") or None,
        label=arguments.get("--label", ""),
    )
```

### 3.7 Fork-on-completion (`fork.py`)

```python
class ForkRouter:
    """Bridge between JobManager and the session-spawning layer.

    The session layer (e.g., OpenTeam conversation_service) registers
    itself with the JobManager via set_fork_router(router) on bootstrap.
    """

    def __init__(self, session_factory: "Callable[[ForkSpec], Awaitable[str]]"):
        self._factory = session_factory

    async def fork_from_completion(self, job: BackgroundJob) -> str:
        seed = (
            f"A background job you started has completed.\n"
            f"job_id: {job.id}\n"
            f"cmdline: {' '.join(job.cmdline)}\n"
            f"status: {job.exit_status}\n"
            f"workspace: {job.workspace}\n"
            f"summary: {job.summary}\n\n"
            f"This conversation was FORKED from session {job.session_id} so "
            f"you can act on the result independently. Decide whether to "
            f"open a PR, file a follow-up, or report back."
        )
        fork_spec = ForkSpec(
            parent_session_id=job.session_id,
            seed_message=seed,
            inherited_context_snapshot=self._snapshot_parent(job.session_id),
            reason=f"bg_job_complete:{job.id}",
        )
        new_session_id = await self._factory(fork_spec)
        logger.info("Forked session %s from parent %s (job %s)",
                    new_session_id, job.session_id, job.id)
        return new_session_id
```

The `session_factory` is supplied by the server layer (e.g., OpenTeam's
`ConversationService.create_session(seed=...)` wrapped to accept a
`ForkSpec`). For pure AgentFoundation use (no server), the factory may
be a no-op that just logs.

### 3.8 Build summary

```python
def build_summary(job: BackgroundJob, *, max_lines: int = 30) -> str:
    """Produce a short LLM-readable summary of the job's outcome."""
    stdout_tail = tail_file(job.workspace / "stdout.log", max_lines)
    stderr_tail = tail_file(job.workspace / "stderr.log", max_lines=10)
    head = (
        f"Exit: {job.exit_status} (code {job.exit_code})\n"
        f"Duration: {_duration_str(job)}\n"
        f"Cmdline: {' '.join(job.cmdline)}\n"
    )
    if job.exit_status == "failed" and stderr_tail.strip():
        head += f"\n--- stderr (last 10) ---\n{stderr_tail}\n"
    head += f"\n--- stdout (last {max_lines}) ---\n{stdout_tail}"
    # Hard cap at 2000 chars; downstream context compression will further
    # trim if needed.
    return head[:2000]
```

---

## 4. Persistence & Rehydration

### 4.1 `meta.json` write/read

`persistence.py`:

```python
def write_meta(workspace: Path, job: BackgroundJob) -> None:
    """Atomic write of <workspace>/meta.json via tempfile + os.replace."""
    target = workspace / "meta.json"
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="meta.json.", suffix=".tmp", dir=str(workspace))
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(job.to_meta_dict(), f, indent=2, default=str)
        os.replace(tmp_path, target)
    except Exception:
        try: os.unlink(tmp_path)
        except OSError: pass
        raise
```

### 4.2 Rehydration on startup

`JobManager.rehydrate(session_root)` is called once at process startup
(server bootstrap) and **also** when a session is registered (in case the
session's `_jobs/` had pending jobs from a previous run).

Pending-but-orphaned (PID dead, status=RUNNING) jobs are marked
`failed_orphaned`. Their `BackgroundJobComplete` is queued normally so the
LLM gets a chance to react ("the build job died, retry?").

### 4.3 Per-session opt-in to rehydration replay

A session that just rehydrated may not want to be hit by a flood of
old completion events. JobManager has a `register_session(..., replay=True)`
default; pass `replay=False` to suppress replay (events still get persisted
but not pushed to the queue). UI can present them as a "Past Notifications"
panel.

---

## 5. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/common/jobs/__init__.py` | NEW. Public re-exports. |
| `agent_foundation/common/jobs/models.py` | NEW. BackgroundJob, JobStatus, JobKind, JobSchedule. |
| `agent_foundation/common/jobs/manager.py` | NEW. JobManager. |
| `agent_foundation/common/jobs/runner.py` | NEW. spawn() + per-kind launchers. |
| `agent_foundation/common/jobs/schedule.py` | NEW. parse_duration_seconds, scheduler hooks. |
| `agent_foundation/common/jobs/fork.py` | NEW. ForkRouter + ForkSpec. |
| `agent_foundation/common/jobs/persistence.py` | NEW. write_meta, tail_file. |
| `agent_foundation/common/jobs/parser.py` | NEW. parse_background_job_args. |
| `agent_foundation/resources/tools/background_job/tool.json` | NEW. Schema above. |
| `agent_foundation/resources/tools/background_job/executor.py` | NEW. Thin wrapper around JobManager.submit. |
| `agent_foundation/resources/tools/background_job/__init__.py` | NEW (empty). |
| All `tool.json` files | Add optional `cli_module` field (only for tools that have a standalone CLI; `task` is the first one). |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` | On `run_agentic_loop` entry: `JobManager.instance().register_session(session_id, user_input_queue)`. On exit/error: `unregister_session`. |
| `openteam/server/services/conversation_service.py` (or equiv) | On bootstrap: `JobManager.instance().set_fork_router(ForkRouter(create_session_with_seed))`. On session create: `JobManager.instance().rehydrate(session_root)`. |

---

## 6. Test Plan

| # | Test | Type |
|---|------|------|
| T3.1 | `JobManager.submit` with kind=COMMAND spawns subprocess, writes meta.json | Integration |
| T3.2 | Job completion within 2s → BackgroundJobComplete arrives on registered queue | Integration |
| T3.3 | `--fork-on-completion` → ForkRouter called instead of queue push | Unit |
| T3.4 | `--every 2s --max-runs 3` → exactly 3 runs, queue gets 3 completions | Integration |
| T3.5 | `--at 2s_future` → starts after delay | Integration |
| T3.6 | `--timeout 1s` on sleep 10 → process killed, status=TIMEOUT | Integration |
| T3.7 | Process killed externally (SIGKILL) → next poll marks FAILED | Integration |
| T3.8 | Rehydrate after sim. crash: orphaned RUNNING → FAILED, replay on register | Integration |
| T3.9 | Parser: 'task "foo"' → JobKind.TOOL, cmdline=['task','foo','--simple'] | Unit |
| T3.10 | Parser: 'rg TODO' (no such tool) → JobKind.COMMAND | Unit |
| T3.11 | Parser: `--every 15m` → 900s | Unit |
| T3.12 | atomic write of meta.json under concurrent updates: no torn writes | Integration |

---

## 7. Open Questions

1. **Cross-process IPC**: today's design assumes a single server process per
   session. For multi-worker servers, JobManager needs a Redis-or-equivalent
   shared store. Out of scope for v1; mark as future work.
2. **Resource limits**: should we cap concurrent background jobs per session?
   Default no cap; configurable via env `JOB_MANAGER_MAX_CONCURRENT`.
3. **Token cost accounting**: tool/SOP jobs consume LLM tokens. We don't
   propagate cost back to the parent session today. Add `cost_usd` field
   on `BackgroundJob` for future visibility.
4. **Cancellation UX**: how does the user cancel a job from chat?
   `/background-job-cancel <job_id>` as a sibling tool, OR a UI button.
   Recommend the slash tool for v1 (UI deferred).

---

*Continued in `04_yolo_mode.md`.*
