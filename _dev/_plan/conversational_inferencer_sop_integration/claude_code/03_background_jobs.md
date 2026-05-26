# Chapter 3 -- F3: Background Jobs (`BackgroundJob` + `JobManager` + `/background-job`)

> **Author:** Claude Code
> **Implements:** F3 from `README.md`
> **Depends on:** F1 (input queue for completion delivery), F2 (simple mode for task invocations)
> **Touches:** new `common/jobs/` package, new `resources/tools/background_job/`, prompt template (chapter 6)

---

## 1. Goal

Introduce a unified background-job abstraction:

- **`BackgroundJob`** -- dataclass capturing a launched process: kind,
  cmdline, PID, workspace, status, schedule, completion callback.
- **`JobManager`** -- per-process singleton owning lifecycle: spawn,
  schedule, poll, persist, route completions to input queues.
- **`/background-job`** -- slash-command tool that submits a new job.
- **`--fork-on-completion`** -- on completion, create a NEW conversation
  session forked from the parent's context.
- **Scheduling** -- `--at <ISO>` for delayed start; `--every <duration>` for
  repeated runs.

> **Workspace clarification:** The `<runtime_root>/_jobs/bg-<id>/` workspaces
> are **JobManager bookkeeping workspaces**. They hold subprocess stdout/stderr
> capture, `meta.json`, and schedule state. They are NOT where the inner work
> happens. When `/background-job task ...` is invoked, TWO independent
> workspaces are produced:
> - `<runtime_root>/_jobs/bg-<id>/` -- JobManager's own dir (this chapter)
> - `<runtime_root>/tasks/task/task_<ts>_<8hex>/` -- the inner `/task` run
>   (chapter 2), created by the subprocess CLI.

---

## 2. Design

### 2.1 Package layout

New package: `AgentFoundation/src/agent_foundation/common/jobs/`

```
common/jobs/
    __init__.py
    models.py             # BackgroundJob + enums + JobSchedule
    manager.py            # JobManager singleton
    runner.py             # subprocess launcher per kind
    workspace.py          # allocate_job_workspace
    leaf_factory.py       # (from chapter 2)
    schedule.py           # schedule loop, parse_duration_seconds
    fork.py               # ForkRouter
    persistence.py        # meta.json atomic read/write
    parser.py             # parse_background_job_args
```

### 2.2 Data models (`models.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobKind(str, Enum):
    TOOL = "tool"            # registered tool (e.g., /task)
    COMMAND = "command"      # raw shell command
    SOP = "sop"              # subprocess SOP runner (chapter 5)


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
    """A single background process tracked by JobManager."""
    id: str                        # short uuid, e.g., "bg-7f2c3a"
    kind: JobKind
    cmdline: list[str]             # canonical argv for display + logs
    workspace: Path                # <runtime_root>/_jobs/<id>/
    session_id: str                # parent session that owns this job
    status: JobStatus = JobStatus.PENDING
    pid: Optional[int] = None
    submitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    exit_code: Optional[int] = None
    exit_status: str = ""          # "success" | "failed" | etc.
    schedule: JobSchedule = field(default_factory=JobSchedule)
    fork_on_completion: bool = False
    max_wallclock_seconds: Optional[int] = None
    label: str = ""                # user-facing label for prompt block
    last_output_tail: str = ""     # last N lines for prompt block
    summary: str = ""              # post-completion summary

    def to_meta_dict(self) -> dict[str, Any]:
        """Serialize for meta.json persistence."""
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
    def from_meta_dict(cls, d: dict[str, Any]) -> BackgroundJob:
        """Deserialize from meta.json for rehydration."""
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


@dataclass
class JobSubmissionSpec:
    """Input to JobManager.submit()."""
    kind: JobKind
    cmdline: list[str]
    session_id: str
    session_root: Path
    schedule: JobSchedule = field(default_factory=JobSchedule)
    fork_on_completion: bool = False
    max_wallclock_seconds: Optional[int] = None
    label: str = ""
```

### 2.3 `JobManager` singleton (`manager.py`)

```python
class JobManager:
    """Process-wide singleton tracking all BackgroundJob instances.

    Responsibilities:
      - Allocate workspace + meta.json on submission
      - Spawn process via runner.spawn(job)
      - Poll status via proc.returncode (NOT os.waitpid -- see DL7)
      - On completion: build summary, atomic-update meta.json, route to queue
      - Rehydrate on startup (scan _jobs/ for unresolved meta.json)
      - Cancel: SIGTERM with grace, then SIGKILL
    """

    _instance: Optional[JobManager] = None

    def __init__(self):
        self._jobs: dict[str, BackgroundJob] = {}
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._session_queues: dict[str, ConversationalInputQueue] = {}
        self._poll_task: Optional[asyncio.Task] = None
        self._poll_interval = 1.0
        self._fork_router: Optional[ForkRouter] = None

    @classmethod
    def instance(cls) -> JobManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_session(
        self, session_id: str, queue: ConversationalInputQueue
    ) -> None:
        self._session_queues[session_id] = queue

    def unregister_session(self, session_id: str) -> None:
        self._session_queues.pop(session_id, None)

    def set_fork_router(self, router: ForkRouter) -> None:
        self._fork_router = router

    async def submit(self, spec: JobSubmissionSpec) -> BackgroundJob:
        """Create, persist, and spawn a new job."""
        job_id = f"bg-{uuid.uuid4().hex[:6]}"
        workspace = allocate_job_workspace(
            job_id, spec.session_root, subdir="_jobs"
        )
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
        proc = await spawn(job)
        self._procs[job.id] = proc
        job.pid = proc.pid
        job.started_at = datetime.now(timezone.utc).isoformat()
        job.status = JobStatus.RUNNING
        write_meta(job.workspace, job)

    async def _poll_loop(self) -> None:
        """Background task polling all RUNNING jobs for completion.

        Uses proc.returncode (asyncio-native) instead of os.waitpid
        to avoid conflicts with asyncio's child watcher.
        """
        while True:
            await asyncio.sleep(self._poll_interval)
            for job in list(self._jobs.values()):
                if job.status != JobStatus.RUNNING:
                    continue
                proc = self._procs.get(job.id)
                if proc is None:
                    continue
                # Non-blocking check via returncode
                if proc.returncode is not None:
                    job.exit_code = proc.returncode
                    job.exit_status = (
                        "success" if proc.returncode == 0 else "failed"
                    )
                    job.status = (
                        JobStatus.DONE if proc.returncode == 0
                        else JobStatus.FAILED
                    )
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    write_meta(job.workspace, job)
                    await self._on_completion(job)
                # Check wallclock timeout
                elif job.max_wallclock_seconds and job.started_at:
                    elapsed = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(job.started_at)
                    ).total_seconds()
                    if elapsed > job.max_wallclock_seconds:
                        await self._kill_job(job, JobStatus.TIMEOUT)

    async def _on_completion(self, job: BackgroundJob) -> None:
        """Handle job completion: build summary, route to parent."""
        summary = build_summary(job)
        job.summary = summary
        write_meta(job.workspace, job)

        # Reschedule if repeating
        if job.schedule.mode == "every":
            job.schedule.runs_completed += 1
            if (
                job.schedule.max_runs is None
                or job.schedule.runs_completed < job.schedule.max_runs
            ):
                asyncio.create_task(self._reschedule_every(job))
                return  # don't route yet; only route final completion

        # Route to parent
        if job.fork_on_completion and self._fork_router is not None:
            await self._fork_router.fork_from_completion(job)
            return

        queue = self._session_queues.get(job.session_id)
        if queue is None:
            logger.warning(
                "Job %s completed but session %s not registered; "
                "completion will replay on rehydrate.",
                job.id, job.session_id,
            )
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
        """Cancel a running job. SIGTERM then SIGKILL after grace period."""
        job = self._jobs.get(job_id)
        if job is None or job.status != JobStatus.RUNNING:
            return False
        await self._kill_job(job, JobStatus.CANCELLED, grace_seconds)
        return True

    def list_running(
        self, session_id: Optional[str] = None
    ) -> list[BackgroundJob]:
        jobs = list(self._jobs.values())
        if session_id:
            jobs = [j for j in jobs if j.session_id == session_id]
        return [
            j for j in jobs
            if j.status in (
                JobStatus.RUNNING, JobStatus.SCHEDULED, JobStatus.PENDING
            )
        ]

    def rehydrate(self, session_root: Path) -> None:
        """On process startup, scan _jobs/ for unresolved meta.json files."""
        jobs_dir = session_root / "_jobs"
        if not jobs_dir.is_dir():
            return
        for meta_path in jobs_dir.glob("*/meta.json"):
            try:
                d = json.loads(meta_path.read_text())
                job = BackgroundJob.from_meta_dict(d)
            except Exception as e:
                logger.warning("Rehydrate failed for %s: %s", meta_path, e)
                continue
            if job.status == JobStatus.RUNNING:
                if not _pid_alive(job.pid):
                    job.status = JobStatus.FAILED
                    job.exit_status = "failed_orphaned"
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    write_meta(job.workspace, job)
            self._jobs[job.id] = job
```

### 2.4 The runner (`runner.py`)

```python
async def spawn(job: BackgroundJob) -> asyncio.subprocess.Process:
    """Spawn the job's process, redirect stdout/stderr to workspace files."""
    stdout_path = job.workspace / "stdout.log"
    stderr_path = job.workspace / "stderr.log"

    if job.kind == JobKind.COMMAND:
        proc = await asyncio.create_subprocess_exec(
            *job.cmdline,
            stdout=open(stdout_path, "wb"),
            stderr=open(stderr_path, "wb"),
            cwd=str(job.workspace),
            env=_clean_env(),
            start_new_session=True,
        )
        return proc

    elif job.kind == JobKind.TOOL:
        return await _spawn_tool_cli(job, stdout_path, stderr_path)

    elif job.kind == JobKind.SOP:
        return await _spawn_sop_subprocess(job, stdout_path, stderr_path)

    raise ValueError(f"Unknown job kind: {job.kind}")


async def _spawn_tool_cli(job, stdout_path, stderr_path):
    """Invoke a tool via its standalone CLI bridge module."""
    tool_name = job.cmdline[0]
    cli_module = TOOL_CLI_MODULE.get(tool_name)
    if cli_module is None:
        raise ValueError(f"No CLI bridge for tool: {tool_name}")
    args = [sys.executable, "-m", cli_module, *job.cmdline[1:]]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=open(stdout_path, "wb"),
        stderr=open(stderr_path, "wb"),
        cwd=str(job.workspace),
        env=_clean_env(),
        start_new_session=True,
    )
    return proc


# TOOL_CLI_MODULE populated from each tool's tool.json "cli_module" field:
TOOL_CLI_MODULE = {
    "task": "openteam.server.resources.tools.task.cli",
}
```

### 2.5 The `/background-job` tool

`AgentFoundation/src/agent_foundation/resources/tools/background_job/tool.json`:

```json
{
  "name": "background_job",
  "aliases": ["background-job", "bg"],
  "tool_type": "Action",
  "category": "system",
  "asynchronous": false,
  "description": "Submit a tool invocation or shell command as a background job.",
  "parameters": [
    {
      "name": "command",
      "type": "string",
      "required": true,
      "positional": true,
      "description": "Tool name + args, or raw shell command. First token matched against tool registry; if no match, treated as shell cmd."
    },
    {
      "name": "--fork-on-completion",
      "type": "flag",
      "description": "On completion, fork into a NEW conversation session."
    },
    {
      "name": "--at",
      "type": "string",
      "description": "Delay first run until ISO8601 timestamp."
    },
    {
      "name": "--every",
      "type": "string",
      "description": "Repeat every <duration>, e.g., '15m', '1h', '2d'."
    },
    {
      "name": "--max-runs",
      "type": "int",
      "description": "Cap repetitions (default: unlimited)."
    },
    {
      "name": "--timeout",
      "type": "string",
      "description": "Max wallclock per run, e.g., '30m'. SIGTERM then SIGKILL."
    },
    {
      "name": "--label",
      "type": "string",
      "description": "Short label for the Running Background Jobs prompt block."
    }
  ],
  "examples": [
    "/background-job task \"implement feature X\"",
    "/background-job task \"refactor Y\" --fork-on-completion",
    "/background-job task \"add tests\" --every 1h --max-runs 24",
    "/background-job 'rg --json TODO src/ > todos.json'",
    "/background-job /sop code_optimization --at 2026-05-20T09:00:00Z"
  ],
  "executor_module": "agent_foundation.resources.tools.background_job.executor"
}
```

**Executor:**

```python
async def execute(arguments: dict, session_context: dict) -> ToolExecutionResult:
    spec = parse_background_job_args(arguments, session_context)
    job = await JobManager.instance().submit(spec)
    return ToolExecutionResult(
        success=True,
        output=(
            f"Background job {job.id} submitted ({job.kind.value}). "
            f"Workspace: {job.workspace}. "
            f"You will be notified when it completes."
        ),
        artifacts={"job_id": job.id, "workspace": str(job.workspace)},
    )
```

### 2.6 Slash-parser logic (`parser.py`)

```python
def parse_background_job_args(
    arguments: dict, session_context: dict
) -> JobSubmissionSpec:
    """Parse /background-job arguments into a JobSubmissionSpec.

    Tool detection: first whitespace-delimited token (after stripping /)
    is matched against the tool registry. If found -> JobKind.TOOL.
    If the token is "sop" -> JobKind.SOP. Otherwise -> JobKind.COMMAND.

    Rejects --fork-on-completion + --every (fork explosion prevention).
    """
    raw = arguments["command"].strip()
    tokens = shlex.split(raw)
    if not tokens:
        raise ValueError("/background-job requires a command")

    first = tokens[0].lstrip("/")
    tool_registry = get_tool_registry()

    if first in tool_registry:
        kind = JobKind.TOOL
        cmdline = [first] + tokens[1:]
    elif first in {"sop"} or first.startswith("sop-"):
        kind = JobKind.SOP
        cmdline = tokens
    else:
        kind = JobKind.COMMAND
        cmdline = tokens

    # Schedule parsing
    schedule = JobSchedule()
    fork = bool(arguments.get("fork_on_completion"))
    if arguments.get("at"):
        schedule = JobSchedule(mode="at", at=arguments["at"])
    elif arguments.get("every"):
        if fork:
            raise ValueError(
                "--fork-on-completion cannot be combined with --every. "
                "Each repetition would spawn a new session -- use "
                "--max-runs 1 for a single delayed-then-fork run."
            )
        schedule = JobSchedule(
            mode="every",
            every_seconds=parse_duration_seconds(arguments["every"]),
            max_runs=arguments.get("max_runs"),
        )

    # Sensitive arg redaction for display
    _redact_sensitive_args(cmdline)

    return JobSubmissionSpec(
        kind=kind,
        cmdline=cmdline,
        session_id=session_context["session_id"],
        session_root=_session_root_from_context(session_context),
        schedule=schedule,
        fork_on_completion=fork,
        max_wallclock_seconds=(
            parse_duration_seconds(arguments.get("timeout") or "")
            or None
        ),
        label=arguments.get("label", ""),
    )


# --- Sensitive arg redaction ---

_SENSITIVE_KEYS = re.compile(
    r"(?:key|secret|token|password|credential|auth)",
    re.IGNORECASE,
)

def _redact_sensitive_args(cmdline: list[str]) -> None:
    """In-place redact values for keys matching sensitive patterns.

    Handles --key=VALUE and --key VALUE forms. Redacts VALUE to '***'.
    """
    for i, arg in enumerate(cmdline):
        if "=" in arg:
            key, _, val = arg.partition("=")
            if _SENSITIVE_KEYS.search(key):
                cmdline[i] = f"{key}=***"
        elif _SENSITIVE_KEYS.search(arg) and i + 1 < len(cmdline):
            cmdline[i + 1] = "***"
```

### 2.7 Fork-on-completion (`fork.py`)

```python
@dataclass
class ForkSpec:
    parent_session_id: str
    seed_message: str
    inherited_context_snapshot: dict[str, Any]
    reason: str


class ForkRouter:
    """Bridge between JobManager and the session-spawning layer.

    The session layer (e.g., OpenTeam ConversationService) registers
    itself via JobManager.set_fork_router(router) on bootstrap.
    """

    def __init__(
        self, session_factory: Callable[[ForkSpec], Awaitable[str]]
    ):
        self._factory = session_factory

    async def fork_from_completion(self, job: BackgroundJob) -> str:
        seed = (
            f"A background job you started has completed.\n"
            f"job_id: {job.id}\n"
            f"cmdline: {' '.join(job.cmdline)}\n"
            f"status: {job.exit_status}\n"
            f"workspace: {job.workspace}\n"
            f"summary: {job.summary}\n\n"
            f"This conversation was FORKED from session {job.session_id}."
        )
        fork_spec = ForkSpec(
            parent_session_id=job.session_id,
            seed_message=seed,
            inherited_context_snapshot={},
            reason=f"bg_job_complete:{job.id}",
        )
        new_session_id = await self._factory(fork_spec)
        logger.info(
            "Forked session %s from parent %s (job %s)",
            new_session_id, job.session_id, job.id,
        )
        return new_session_id
```

### 2.8 Persistence (`persistence.py`)

```python
def write_meta(workspace: Path, job: BackgroundJob) -> None:
    """Atomic write of <workspace>/meta.json via tempfile + os.replace.

    Guarantees no torn writes even under concurrent poll-loop updates.
    """
    target = workspace / "meta.json"
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix="meta.json.", suffix=".tmp", dir=str(workspace)
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(job.to_meta_dict(), f, indent=2, default=str)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def build_summary(
    job: BackgroundJob, *, max_lines: int = 30
) -> str:
    """Produce a short LLM-readable summary of the job outcome."""
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
    return head[:2000]
```

### 2.9 Job workspace layout

```
<runtime_root>/_jobs/bg-7f2c3a/
    meta.json                # BackgroundJob.to_meta_dict()
    stdout.log               # subprocess stdout capture
    stderr.log               # subprocess stderr capture
```

For `JobKind.TOOL` jobs (e.g., task): the subprocess creates its OWN
workspace under `<runtime_root>/tasks/task/task_<ts>_<8hex>/` (per chapter 2).
The JobManager workspace `_jobs/bg-<id>/` is solely for the subprocess
wrapper metadata.

---

## 3. Scheduling Engine (`schedule.py`)

```python
def parse_duration_seconds(s: str) -> int:
    """Parse human-readable duration: '15m' -> 900, '1h' -> 3600, '2d' -> 172800."""
    if not s:
        return 0
    match = re.match(r"^(\d+)\s*(s|m|h|d)$", s.strip())
    if not match:
        raise ValueError(f"Invalid duration: {s!r}. Use Ns, Nm, Nh, or Nd.")
    val, unit = int(match.group(1)), match.group(2)
    return val * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
```

Schedule modes on `JobManager`:

```python
async def _schedule_at(self, job: BackgroundJob) -> None:
    """Wait until the specified ISO8601 time, then spawn."""
    target = datetime.fromisoformat(job.schedule.at)
    now = datetime.now(timezone.utc)
    delay = max(0, (target - now).total_seconds())
    job.status = JobStatus.SCHEDULED
    write_meta(job.workspace, job)
    await asyncio.sleep(delay)
    await self._spawn_now(job)

async def _schedule_every(self, job: BackgroundJob) -> None:
    """Spawn immediately, then reschedule on completion."""
    await self._spawn_now(job)

async def _reschedule_every(self, job: BackgroundJob) -> None:
    """After a repeated job completes, reset and spawn again."""
    await asyncio.sleep(job.schedule.every_seconds)
    job.status = JobStatus.PENDING
    job.exit_code = None
    job.exit_status = ""
    job.completed_at = None
    job.pid = None
    write_meta(job.workspace, job)
    await self._spawn_now(job)
```

---

## 4. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/common/jobs/__init__.py` | NEW. Public re-exports. |
| `agent_foundation/common/jobs/models.py` | NEW. BackgroundJob, JobStatus, JobKind, JobSchedule, JobSubmissionSpec. |
| `agent_foundation/common/jobs/manager.py` | NEW. JobManager singleton. |
| `agent_foundation/common/jobs/runner.py` | NEW. spawn() + per-kind launchers. |
| `agent_foundation/common/jobs/schedule.py` | NEW. parse_duration_seconds, scheduler hooks. |
| `agent_foundation/common/jobs/fork.py` | NEW. ForkRouter + ForkSpec. |
| `agent_foundation/common/jobs/persistence.py` | NEW. write_meta, build_summary, tail_file. |
| `agent_foundation/common/jobs/parser.py` | NEW. parse_background_job_args. |
| `agent_foundation/resources/tools/background_job/tool.json` | NEW. Schema above. |
| `agent_foundation/resources/tools/background_job/executor.py` | NEW. Wrapper around JobManager.submit. |
| `agent_foundation/resources/tools/background_job/__init__.py` | NEW. |
| All `tool.json` files | Add optional `cli_module` field (for tools with standalone CLIs). |
| `conversational_inferencer.py` | On `run_agentic_loop` entry: `JobManager.instance().register_session(...)`. On exit: `unregister_session`. |
| `openteam/.../conversation_service.py` | On bootstrap: `JobManager.set_fork_router(...)`. On session create: `JobManager.rehydrate(...)`. |

---

## 5. Test Plan

| # | Test | Type |
|---|------|------|
| T3.1 | `JobManager.submit` with kind=COMMAND spawns subprocess, writes meta.json | Integration |
| T3.2 | Job completion within 5s -> `BackgroundJobComplete` arrives on registered queue | Integration |
| T3.3 | `--fork-on-completion` -> ForkRouter called instead of queue push | Unit |
| T3.4 | `--every 2s --max-runs 3` -> exactly 3 runs, queue gets completion after final | Integration |
| T3.5 | `--at <2s_future>` -> starts after delay, not immediately | Integration |
| T3.6 | `--timeout 1s` on `sleep 10` -> process killed, status=TIMEOUT | Integration |
| T3.7 | Process killed externally (SIGKILL) -> next poll marks FAILED | Integration |
| T3.8 | Rehydrate after simulated crash: orphaned RUNNING -> FAILED | Integration |
| T3.9 | Parser: `'task "foo"'` -> `JobKind.TOOL`, cmdline includes task args | Unit |
| T3.10 | Parser: `'rg TODO'` (no such tool) -> `JobKind.COMMAND` | Unit |
| T3.11 | Parser: `--every 15m` -> `every_seconds=900` | Unit |
| T3.12 | Parser: `--fork-on-completion --every 5m` -> `ValueError` (rejected) | Unit |
| T3.13 | Atomic write of meta.json: concurrent updates produce valid JSON | Integration |
| T3.14 | `build_summary` truncates to 2000 chars | Unit |
| T3.15 | Sensitive arg redaction: `--api-key=SECRET` -> `--api-key=***` in cmdline | Unit |
| T3.16 | `proc.returncode` used for completion detection (NOT `os.waitpid`) | Unit |
| T3.17 | `parse_duration_seconds` parses s/m/h/d; rejects invalid input | Unit |

---

## 6. Cross-References

- **Chapter 1 (Input Queue):** `BackgroundJobComplete` is pushed into the `ConversationalInputQueue` on job completion.
- **Chapter 2 (Task Simple Mode):** `/background-job task ...` spawns a simple-mode task subprocess.
- **Chapter 5 (SOP Lifecycle):** `JobKind.SOP` runner is `_spawn_sop_subprocess()` (chapter 5 defines the entry point).
- **Chapter 6 (Prompt Integration):** `## Running Background Jobs` template section reads from `JobManager.list_running()`.
- **Chapter 7 (Scenarios):** Scenarios 2, 3, 6, and 7 exercise background job lifecycle.
- **Chapter 8 (Roadmap):** Phase D covers this chapter (PRs D.1, D.2, D.3).

---

## 7. Open Questions

1. **Cross-process IPC:** Today's design assumes a single server process per
   session. For multi-worker servers, JobManager needs a shared store (Redis
   or equivalent). Out of scope for v1.

2. **Resource limits:** Should we cap concurrent jobs per session? Default no
   cap; configurable via env `JOB_MANAGER_MAX_CONCURRENT`.

3. **Token cost accounting:** Tool/SOP jobs consume LLM tokens. Add a
   `cost_usd` field on `BackgroundJob` for future visibility. Not enforced.

4. **Cancellation UX:** `/background-job-cancel <job_id>` as a sibling tool.
   UI button deferred.

5. **File descriptor management:** The `open(stdout_path, "wb")` calls in
   `spawn()` must be context-managed to avoid fd leaks on spawn failure. Use
   `contextlib.ExitStack` or explicit try/finally.

---

*Continued in `04_yolo_mode.md`.*
