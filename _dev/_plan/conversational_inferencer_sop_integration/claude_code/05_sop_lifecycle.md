# Chapter 5 -- F5: SOP Lifecycle (`/enter-sop`, `/exit-sop`, `/sop`, SOPRegistry)

> **Author:** Claude Code
> **Implements:** F5 from `README.md`
> **Depends on:** F1 (input queue), F3 (background jobs for `/sop` subprocess launch), F4 (YOLO mode)
> **Touches:** new `common/sop/` package, new tools, `sop_runner.py` entry point, prompt template, `conversational_inferencer.py`

---

## 1. Goal

Three new first-class tools for SOP lifecycle:

| Tool | Behavior |
|------|----------|
| `/enter-sop <name>` | Load SOP into the CURRENT conversation as the active workflow. Sets `active_sop_id`, populates `<WorkflowDescription>` + `<WorkflowStatus>` + `<WorkflowNextStepGuidance>`. |
| `/exit-sop` | Unload the active SOP. Pauses the run in `WorkflowSessionState` so it can be re-entered later. |
| `/sop <name> [--var k=v]*` | Launch a NEW subprocess with its own `ConversationalInferencer` in YOLO mode. Returns a `BackgroundJob` (kind=SOP) tracked by JobManager. |

Combined with F3, `/sop` is most useful inside `/background-job`:
```
/background-job /sop code_optimization --var workflow_target_path=src/foo
```

---

## 2. Design

### 2.1 SOPRegistry

New module: `AgentFoundation/src/agent_foundation/common/sop/registry.py`

```python
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SOPDefinition:
    """Metadata about a discovered SOP."""
    name: str                       # canonical id, e.g., "code_optimization"
    title: str                      # human-readable title
    description: str                # one-paragraph blurb
    sop_path: Path                  # absolute path to the .md / .jinja2
    variables: list[str]            # declared variable names
    required_variables: list[str]   # subset that must be provided
    phases: list[str]               # ordered phase names
    has_must_gates: bool            # True if any gate has [__must__]


class SOPRegistry:
    """Discovers SOP definitions on disk and exposes a lookup API.

    Scans the workflow_sop/ directory under the AgentFoundation
    prompt_templates root. Built once at server startup; re-scanned
    on SIGHUP or explicit refresh.
    """

    _SOP_DIRS = [
        "resources/prompt_templates/conversation/main/_variables/workflow_sop",
    ]

    def __init__(self, package_root: Path):
        self._package_root = Path(package_root)
        self._definitions: dict[str, SOPDefinition] = {}
        self._scan()

    def _scan(self) -> None:
        """Walk known SOP directories and parse each file."""
        for rel in self._SOP_DIRS:
            base = self._package_root / rel
            if not base.is_dir():
                continue
            for sop_file in sorted(base.iterdir()):
                if sop_file.suffix not in {".md", ".jinja2", ".j2", ".yaml", ".yml"}:
                    continue
                name = sop_file.stem
                definition = self._parse_sop(name, sop_file)
                self._definitions[name] = definition

    def _parse_sop(self, name: str, path: Path) -> SOPDefinition:
        """Parse a single SOP file into an SOPDefinition."""
        text = path.read_text(encoding="utf-8")

        # Use SOPManager to parse phases + gates
        from rich_python_utils.string_utils.formatting.template_manager.sop_manager import (
            SOPManager,
        )
        sop = SOPManager.load(path)
        phases = [phase.name for phase in sop.phases]
        has_must_gates = any(
            getattr(g, "must", False) for g in sop.all_gates()
        )

        # Variables: scan for {{ var_name }} Jinja2 references
        variables = sorted(set(re.findall(r"{{\s*(\w+)", text)))

        # Required vs optional: parse <!-- sop-meta required_vars: x,y -->
        required = self._parse_required_vars(text, variables)

        # Title + description from file header
        title, description = self._extract_title_desc(text, fallback=name)

        return SOPDefinition(
            name=name,
            title=title,
            description=description,
            sop_path=path,
            variables=variables,
            required_variables=required,
            phases=phases,
            has_must_gates=has_must_gates,
        )

    def _extract_title_desc(
        self, text: str, fallback: str
    ) -> tuple[str, str]:
        """Extract title from first H1/H2 and description from first paragraph."""
        title = fallback
        description = ""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not title:
                title = stripped.lstrip("# ").strip()
            elif stripped.startswith("## Description"):
                # Next non-empty line is the description
                idx = text.index(stripped)
                after = text[idx + len(stripped):]
                for desc_line in after.split("\n"):
                    desc_line = desc_line.strip()
                    if desc_line and not desc_line.startswith("#"):
                        description = desc_line
                        break
                break
            elif stripped and not stripped.startswith("#") and not description:
                description = stripped
        return (title, description)

    def _parse_required_vars(
        self, text: str, all_vars: list[str]
    ) -> list[str]:
        """Parse <!-- sop-meta required_vars: x,y,z --> if present."""
        m = re.search(
            r"<!--\s*sop-meta\s+required_vars:\s*([^>]+)-->", text
        )
        if m:
            return [v.strip() for v in m.group(1).split(",") if v.strip()]
        return list(all_vars)  # default: all are required

    def get(self, name: str) -> Optional[SOPDefinition]:
        return self._definitions.get(name)

    def list(self) -> list[SOPDefinition]:
        return sorted(self._definitions.values(), key=lambda d: d.name)

    def refresh(self) -> None:
        """Re-scan directories. Called on SIGHUP or explicit API."""
        self._definitions.clear()
        self._scan()


# Module-global lazy singleton
_global_registry: Optional[SOPRegistry] = None


def get_sop_registry() -> SOPRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SOPRegistry(
            package_root=_find_agent_foundation_root()
        )
    return _global_registry


def _find_agent_foundation_root() -> Path:
    """Locate the agent_foundation package root directory."""
    import agent_foundation
    return Path(agent_foundation.__file__).parent
```

### 2.2 `WorkflowSessionState` state machine

New module: `AgentFoundation/src/agent_foundation/common/sop/state.py`

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


class WorkflowConflictError(Exception):
    """Raised when a workflow state transition is invalid."""
    pass


@dataclass
class WorkflowRun:
    """A single SOP execution run."""
    sop_id: str                    # the SOP name
    run_id: str                    # unique per-run, e.g., "wf-3f9c2a"
    status: str                    # "running" | "paused" | "completed" | "aborted"
    phase: str                     # current phase name
    phase_outputs: dict[str, Any]  # accumulated outputs
    variables: dict[str, Any]      # bound variable values
    started_at: str
    last_active_at: str


@dataclass
class WorkflowSessionState:
    """Manages SOP runs within a session.

    State machine transitions:
      enter   -> running
      exit    -> paused
      resume  -> running  (via re-entering a paused SOP)
      complete -> completed

    At most one active run per session at any time.
    """
    runs: list[WorkflowRun] = field(default_factory=list)
    active_run_id: Optional[str] = None

    def active_run(self) -> Optional[WorkflowRun]:
        if not self.active_run_id:
            return None
        for r in self.runs:
            if r.run_id == self.active_run_id:
                return r
        return None

    def enter(
        self, sop_id: str, *, variables: Optional[dict] = None
    ) -> WorkflowRun:
        """Enter an SOP. If a paused run of the same SOP exists, resume it.

        Raises WorkflowConflictError if another SOP is already active.
        """
        if self.active_run_id is not None:
            raise WorkflowConflictError(
                "Another SOP is active; exit it first with /exit-sop."
            )

        # Check for a paused run of the same SOP -> auto-resume
        for r in reversed(self.runs):
            if r.sop_id == sop_id and r.status == "paused":
                r.status = "running"
                r.last_active_at = _now()
                if variables:
                    r.variables.update(variables)
                self.active_run_id = r.run_id
                return r

        # No paused run -> create new
        run = WorkflowRun(
            sop_id=sop_id,
            run_id=f"wf-{uuid.uuid4().hex[:6]}",
            status="running",
            phase="initial",
            phase_outputs={},
            variables=dict(variables or {}),
            started_at=_now(),
            last_active_at=_now(),
        )
        self.runs.append(run)
        self.active_run_id = run.run_id
        return run

    def exit(self) -> Optional[WorkflowRun]:
        """Exit (pause) the active SOP."""
        run = self.active_run()
        if run is None:
            return None
        run.status = "paused"
        run.last_active_at = _now()
        self.active_run_id = None
        return run

    def complete(self) -> Optional[WorkflowRun]:
        """Mark the active SOP as completed."""
        run = self.active_run()
        if run is None:
            return None
        run.status = "completed"
        run.last_active_at = _now()
        self.active_run_id = None
        return run

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs": [
                {
                    "sop_id": r.sop_id,
                    "run_id": r.run_id,
                    "status": r.status,
                    "phase": r.phase,
                    "phase_outputs": r.phase_outputs,
                    "variables": r.variables,
                    "started_at": r.started_at,
                    "last_active_at": r.last_active_at,
                }
                for r in self.runs
            ],
            "active_run_id": self.active_run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowSessionState:
        state = cls()
        for rd in data.get("runs", []):
            state.runs.append(WorkflowRun(**rd))
        state.active_run_id = data.get("active_run_id")
        return state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
```

Persistence: serialized as part of the session JSON at
`<session_root>/.workflow_state.json` for AgentFoundation-local sessions.
For OpenTeam server sessions, persisted via `data_service.update_workflow_context`.

### 2.3 The `/enter-sop` tool

`AgentFoundation/src/agent_foundation/resources/tools/enter_sop/tool.json`:

```json
{
  "name": "enter_sop",
  "aliases": ["enter-sop"],
  "tool_type": "Action",
  "category": "workflow",
  "description": "Load a Standard Operating Procedure (SOP) into the current conversation as the active workflow.",
  "parameters": [
    {
      "name": "name",
      "type": "string",
      "required": true,
      "positional": true,
      "description": "Canonical SOP name (e.g., 'code_optimization'). See 'Available SOPs' in prompt."
    },
    {
      "name": "--var",
      "type": "list",
      "description": "Initial variable bindings: --var key=value. Repeat for multiple."
    },
    {
      "name": "--reason",
      "type": "string",
      "description": "Free-text rationale for entering this SOP. Logged for audit."
    }
  ],
  "examples": [
    "/enter-sop code_optimization",
    "/enter-sop code_optimization --var workflow_target_path=src/foo"
  ],
  "executor_module": "agent_foundation.resources.tools.enter_sop.executor"
}
```

Executor:

```python
async def execute(
    arguments: dict, session_context: dict
) -> ToolExecutionResult:
    name = arguments["name"]
    registry = get_sop_registry()
    definition = registry.get(name)
    if definition is None:
        available = ", ".join(d.name for d in registry.list())
        return ToolExecutionResult(
            success=False,
            output=f"Unknown SOP '{name}'. Available: {available}",
        )

    variables = _parse_kv(arguments.get("var") or [])

    # Validate required vars (soft-warn, don't fail)
    missing = [
        v for v in definition.required_variables
        if v not in variables
    ]

    workflow_state = _get_workflow_state(session_context)
    try:
        run = workflow_state.enter(name, variables=variables)
    except WorkflowConflictError as e:
        return ToolExecutionResult(success=False, output=str(e))
    _persist_workflow_state(session_context, workflow_state)

    resumed = run.status == "running" and run.phase != "initial"

    context_updates = {
        "active_sop_id": name,
        "active_run_id": run.run_id,
        "_active_workflow_changed": True,
        "workflow_description": definition.description,
        "workflow_target_path": variables.get("workflow_target_path"),
    }

    summary = (
        f"{'Resumed' if resumed else 'Entered'} SOP '{name}' "
        f"as run {run.run_id}. "
        f"Phases: {' -> '.join(definition.phases)}."
    )
    if variables:
        summary += f" Bound variables: {variables}."
    if missing:
        summary += f" Missing required variables: {missing}."
    if resumed:
        summary += f" Resuming from phase: {run.phase}."

    return ToolExecutionResult(
        success=True,
        output=summary,
        context_updates=context_updates,
    )


def _parse_kv(items: list[str]) -> dict[str, str]:
    """Parse ['key=value', ...] into a dict."""
    result = {}
    for item in items:
        if "=" in item:
            k, _, v = item.partition("=")
            result[k.strip()] = v.strip()
    return result
```

### 2.4 The `/exit-sop` tool

`AgentFoundation/src/agent_foundation/resources/tools/exit_sop/tool.json`:

```json
{
  "name": "exit_sop",
  "aliases": ["exit-sop"],
  "tool_type": "Action",
  "category": "workflow",
  "description": "Exit the currently active SOP. The run is paused and can be resumed later.",
  "parameters": [
    {
      "name": "--reason",
      "type": "string",
      "description": "Free-text rationale for exiting."
    }
  ],
  "examples": [
    "/exit-sop --reason 'switching to urgent bug fix'"
  ],
  "executor_module": "agent_foundation.resources.tools.exit_sop.executor"
}
```

Executor:

```python
async def execute(
    arguments: dict, session_context: dict
) -> ToolExecutionResult:
    workflow_state = _get_workflow_state(session_context)
    run = workflow_state.exit()
    if run is None:
        return ToolExecutionResult(
            success=False,
            output="No active SOP to exit.",
        )
    _persist_workflow_state(session_context, workflow_state)

    context_updates = {
        "active_sop_id": None,
        "active_run_id": None,
        "_active_workflow_changed": True,
    }

    reason = arguments.get("reason", "")
    return ToolExecutionResult(
        success=True,
        output=(
            f"Paused SOP '{run.sop_id}' (run {run.run_id}) at phase "
            f"'{run.phase}'. Re-enter anytime with "
            f"`/enter-sop {run.sop_id}`."
            + (f" Reason: {reason}" if reason else "")
        ),
        context_updates=context_updates,
    )
```

### 2.5 The `/sop` tool (subprocess launcher)

`AgentFoundation/src/agent_foundation/resources/tools/sop/tool.json`:

```json
{
  "name": "sop",
  "tool_type": "Action",
  "category": "workflow",
  "asynchronous": true,
  "description": "Launch a Standard Operating Procedure as an autonomous background process in YOLO mode.",
  "parameters": [
    {
      "name": "name",
      "type": "string",
      "required": true,
      "positional": true,
      "description": "Canonical SOP name."
    },
    {
      "name": "--var",
      "type": "list",
      "description": "SOP variable bindings: --var key=value."
    },
    {
      "name": "--inferencer",
      "type": "string",
      "default": "claude_code_cli",
      "description": "Leaf inferencer for the subprocess."
    },
    {
      "name": "--model",
      "type": "string",
      "description": "Override the leaf inferencer's model."
    },
    {
      "name": "--fork-on-completion",
      "type": "flag",
      "description": "Fork calling conversation on completion."
    },
    {
      "name": "--no-background",
      "type": "flag",
      "description": "Run synchronously inline (for tests)."
    }
  ],
  "examples": [
    "/sop code_optimization --var workflow_target_path=src/foo",
    "/sop code_optimization --var workflow_target_path=src/foo --fork-on-completion"
  ],
  "executor_module": "agent_foundation.resources.tools.sop.executor"
}
```

Executor:

```python
async def execute(
    arguments: dict, session_context: dict
) -> ToolExecutionResult:
    name = arguments["name"]
    registry = get_sop_registry()
    definition = registry.get(name)
    if definition is None:
        return ToolExecutionResult(
            success=False,
            output=f"Unknown SOP '{name}'.",
        )

    variables = _parse_kv(arguments.get("var") or [])
    inferencer_name = arguments.get("inferencer", "claude_code_cli")
    model = arguments.get("model")
    fork = bool(arguments.get("fork_on_completion"))
    background = not bool(arguments.get("no_background"))

    if background:
        cmdline = [
            "sop", name,
            *_var_args(variables),
            "--inferencer", inferencer_name,
            *(["--model", model] if model else []),
        ]
        spec = JobSubmissionSpec(
            kind=JobKind.SOP,
            cmdline=cmdline,
            session_id=session_context["session_id"],
            session_root=_session_root_from_context(session_context),
            fork_on_completion=fork,
            label=f"SOP: {name}",
        )
        job = await JobManager.instance().submit(spec)
        return ToolExecutionResult(
            success=True,
            output=(
                f"SOP '{name}' launched as background job {job.id}. "
                f"Workspace: {job.workspace}."
            ),
            artifacts={"job_id": job.id, "workspace": str(job.workspace)},
        )

    # Synchronous inline path (--no-background)
    result_text = await _run_sop_inline(
        definition, variables, inferencer_name, model
    )
    return ToolExecutionResult(success=True, output=result_text)


def _var_args(variables: dict[str, str]) -> list[str]:
    """Convert {'k': 'v'} to ['--var', 'k=v', '--var', 'k2=v2']."""
    args = []
    for k, v in variables.items():
        args.extend(["--var", f"{k}={v}"])
    return args
```

### 2.6 The subprocess SOP runner entry point

New module: `AgentFoundation/src/agent_foundation/scripts/sop_runner.py`

```python
"""Subprocess entry point launched by JobManager.runner._spawn_sop_subprocess.

Usage:
    python -m agent_foundation.scripts.sop_runner <sop_name> \
        [--var key=value]* \
        --inferencer <name> \
        [--model <id>] \
        --workspace <path>

Exit codes:
    0  -- SOP completed successfully
    1  -- SOP failed (error)
    2  -- SOP blocked on a must-gate (BLOCKED_ON_MUST_GATE)
"""
import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Run an SOP in YOLO mode as a subprocess."
    )
    parser.add_argument("sop_name")
    parser.add_argument("--var", action="append", default=[])
    parser.add_argument("--inferencer", default="claude_code_cli")
    parser.add_argument("--model", default=None)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    variables = _parse_kv(args.var)
    workspace = Path(args.workspace)

    # Ensure PYTHONPATH includes AgentFoundation and sibling repos
    _propagate_pythonpath()

    from agent_foundation.common.sop.registry import SOPRegistry, get_sop_registry
    from agent_foundation.common.jobs.leaf_factory import make_leaf_inferencer
    from agent_foundation.common.inferencers.agentic_inferencers.conversational.conversational_inferencer import (
        ConversationalInferencer,
        MustGateBlockedError,
    )
    from agent_foundation.ui.null_interactive import NullInteractive

    registry = get_sop_registry()
    definition = registry.get(args.sop_name)
    if definition is None:
        print(f"Unknown SOP '{args.sop_name}'", file=sys.stderr)
        sys.exit(2)

    # Build leaf inferencer
    leaf = make_leaf_inferencer(
        args.inferencer,
        model=args.model,
        cache_dir=workspace / "_runtime" / "inferencer_cache",
        session_log_dir=workspace / "logs" / "session",
    )

    # Build conversational inferencer in YOLO mode
    session_id = f"sop-{args.sop_name}-{uuid.uuid4().hex[:6]}"
    inferencer = ConversationalInferencer(
        base_inferencer=leaf,
        prior_context={
            "session_id": session_id,
            "session_root_path": str(workspace),
            "yolo_vars": variables,
            "active_sop_id": args.sop_name,
        },
        yolo_mode=True,
        interactive=NullInteractive(),
    )

    # Seed the conversation and run
    seed = (
        f"Begin SOP execution: {args.sop_name}. "
        f"Variables: {json.dumps(variables)}."
    )

    exit_code = 0
    try:
        result = asyncio.run(
            inferencer.run_agentic_loop(
                seed, session_id=session_id
            )
        )
        # Write final summary
        (workspace / "final_summary.md").write_text(
            result.text or "", encoding="utf-8"
        )
    except MustGateBlockedError as e:
        (workspace / "final_summary.md").write_text(
            f"[BLOCKED ON MUST-GATE] {e}", encoding="utf-8"
        )
        exit_code = 2
    except Exception as e:
        (workspace / "final_summary.md").write_text(
            f"[ERROR] {e}", encoding="utf-8"
        )
        exit_code = 1

    sys.exit(exit_code)


def _parse_kv(items: list[str]) -> dict[str, str]:
    result = {}
    for item in items:
        if "=" in item:
            k, _, v = item.partition("=")
            result[k.strip()] = v.strip()
    return result


def _propagate_pythonpath():
    """Ensure sibling repos are importable in the subprocess.

    When running under the OpenTeam server, conftest.py adds
    AgentFoundation/src and RichPythonUtils/src to sys.path.
    The subprocess does not get conftest.py, so we propagate
    PYTHONPATH explicitly.
    """
    import os
    pythonpath = os.environ.get("PYTHONPATH", "")
    # The parent process's _clean_env() should have already set this.
    # As a fallback, try to locate sibling repos relative to
    # agent_foundation's install location.
    if "agent_foundation" not in pythonpath:
        try:
            import agent_foundation
            af_src = str(Path(agent_foundation.__file__).parent.parent)
            if af_src not in sys.path:
                sys.path.insert(0, af_src)
        except ImportError:
            pass


if __name__ == "__main__":
    main()
```

Key invariants:
- Subprocess uses `NullInteractive` -- any must-gate raises `MustGateBlockedError`.
- Exit code 0 = success, 1 = error, 2 = blocked on must-gate.
- Writes `final_summary.md` and `yolo_decisions.jsonl` (via chapter 4 audit log).
- JobManager polls exit code and routes completion.

### 2.7 `_spawn_sop_subprocess` in runner.py

Add to `agent_foundation/common/jobs/runner.py`:

```python
async def _spawn_sop_subprocess(
    job: BackgroundJob, stdout_path: Path, stderr_path: Path
) -> asyncio.subprocess.Process:
    """Launch sop_runner.py as a subprocess."""
    # job.cmdline = ["sop", "<name>", "--var", "k=v", ...]
    sop_name = job.cmdline[1]  # cmdline[0] is "sop"
    var_args = job.cmdline[2:]  # remaining args

    args = [
        sys.executable, "-m", "agent_foundation.scripts.sop_runner",
        sop_name,
        "--workspace", str(job.workspace),
        *var_args,
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=open(stdout_path, "wb"),
        stderr=open(stderr_path, "wb"),
        cwd=str(job.workspace),
        env=_clean_env(),
        start_new_session=True,
    )
    return proc


def _clean_env() -> dict[str, str]:
    """Build a clean environment for subprocess execution.

    Propagates PYTHONPATH to ensure agent_foundation and sibling
    repos are importable in the subprocess.
    """
    import os
    env = dict(os.environ)
    # Ensure PYTHONPATH includes the src directories
    paths = []
    for name in ("AgentFoundation", "RichPythonUtils", "OpenStartup"):
        candidate = Path(os.environ.get("OPENTEAM_WORKING_DIR", "~/MyProjects")) / "CoreProjects" / name / "src"
        if candidate.expanduser().is_dir():
            paths.append(str(candidate.expanduser()))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(paths + [existing]) if existing else os.pathsep.join(paths)
    return env
```

### 2.8 `find_sop_file` enhancement

In `conversational_inferencer.py`, update the SOP file discovery to
consult the registry:

```python
def _find_sop_file(self, sop_name: Optional[str] = None) -> Optional[Path]:
    """Find the SOP file by name or active_sop_id.

    Precedence:
      1. Explicit sop_name argument
      2. self.prior_context["active_sop_id"]
      3. Legacy: prompt_renderer.find_sop_file()
    """
    name = sop_name or self.prior_context.get("active_sop_id")
    if name:
        registry = get_sop_registry()
        definition = registry.get(name)
        if definition:
            return definition.sop_path

    # Legacy fallback: use prompt_renderer's built-in discovery
    if self.prompt_renderer and hasattr(self.prompt_renderer, "find_sop_file"):
        return self.prompt_renderer.find_sop_file()

    return None
```

---

## 3. End-to-End Wiring

### 3.1 Constructor injection chain

```
server bootstrap
  -> SOPRegistry(package_root)
       -> injected into ConversationalInferencer as self.sop_registry
            -> /enter-sop executor reads via get_sop_registry()
            -> /sop executor reads via get_sop_registry()
            -> sop_runner subprocess constructs its own via get_sop_registry()
```

### 3.2 Prompt template variable plumbing

`_render_prompt()` gains new variables:

```python
feed = {
    ...
    "available_sops": (
        self.sop_registry.list() if self.sop_registry else []
    ),
    "active_sop": self._active_sop_definition(),
    "active_run_id": self.prior_context.get("active_run_id"),
    "yolo_mode": self.yolo_mode,
    "running_background_jobs": _format_running_jobs(
        JobManager.instance().list_running(
            session_id=self._session_id
        )
    ),
}
```

---

## 4. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/common/sop/__init__.py` | NEW. Re-exports. |
| `agent_foundation/common/sop/registry.py` | NEW. `SOPRegistry`, `SOPDefinition`, `get_sop_registry()`. |
| `agent_foundation/common/sop/state.py` | NEW. `WorkflowRun`, `WorkflowSessionState`, `WorkflowConflictError`. |
| `agent_foundation/resources/tools/enter_sop/tool.json` | NEW. |
| `agent_foundation/resources/tools/enter_sop/executor.py` | NEW. |
| `agent_foundation/resources/tools/enter_sop/__init__.py` | NEW. |
| `agent_foundation/resources/tools/exit_sop/tool.json` | NEW. |
| `agent_foundation/resources/tools/exit_sop/executor.py` | NEW. |
| `agent_foundation/resources/tools/exit_sop/__init__.py` | NEW. |
| `agent_foundation/resources/tools/sop/tool.json` | NEW. |
| `agent_foundation/resources/tools/sop/executor.py` | NEW. |
| `agent_foundation/resources/tools/sop/__init__.py` | NEW. |
| `agent_foundation/scripts/sop_runner.py` | NEW. Subprocess entry point. |
| `agent_foundation/scripts/__init__.py` | NEW (empty). |
| `agent_foundation/common/jobs/runner.py` | Add `_spawn_sop_subprocess`, `_clean_env`. |
| `agent_foundation/.../conversational/conversational_inferencer.py` | Add `sop_registry` attrib. Add `_find_sop_file()` with registry lookup. Plumb new template vars. |
| `agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` | Add `## Available SOPs` and `## Active SOP` sections (full template in chapter 6). |

---

## 5. Test Plan

| # | Test | Type |
|---|------|------|
| T5.1 | `SOPRegistry._scan` discovers SOP files from `workflow_sop/` directory | Unit |
| T5.2 | `SOPDefinition.has_must_gates == True` for `code_optimization` (it has `[__must__]`) | Unit |
| T5.3 | `SOPDefinition.variables` extracted from Jinja2 `{{ var }}` references | Unit |
| T5.4 | `SOPDefinition.required_variables` parsed from `<!-- sop-meta -->` comment | Unit |
| T5.5 | `/enter-sop code_optimization` -> `context_updates` sets `active_sop_id` | Unit |
| T5.6 | `/enter-sop` twice without `/exit-sop` -> `WorkflowConflictError` | Unit |
| T5.7 | `/exit-sop` followed by `/enter-sop same` -> auto-resume, status transitions paused->running | Unit |
| T5.8 | `/exit-sop` with no active SOP -> error message | Unit |
| T5.9 | `/sop foo --no-background` -> inline execution returns result text | Integration |
| T5.10 | `/sop code_optimization --var workflow_target_path=...` (background) -> JobKind.SOP job submitted | Integration |
| T5.11 | `sop_runner.py` with a SOP containing no must-gates -> completes, exit code 0, writes `final_summary.md` | E2E |
| T5.12 | `sop_runner.py` with must-gate -> exit code 2, summary prefixed `[BLOCKED ON MUST-GATE]` | E2E |
| T5.13 | `/sop foo --fork-on-completion` -> `ForkRouter` triggered on completion | Integration |
| T5.14 | `_find_sop_file("code_optimization")` returns registry-resolved path | Unit |
| T5.15 | `_find_sop_file(None)` with `active_sop_id` set returns that SOP's path | Unit |
| T5.16 | `_find_sop_file(None)` with no `active_sop_id` falls back to `prompt_renderer.find_sop_file()` | Unit |
| T5.17 | `WorkflowSessionState.to_dict() / from_dict()` round-trip preserves all fields | Unit |
| T5.18 | `_clean_env()` propagates PYTHONPATH with sibling repo src dirs | Unit |
| T5.19 | `SOPRegistry.refresh()` re-scans and picks up newly added SOP files | Unit |

---

## 6. Cross-References

- **Chapter 1 (Input Queue):** SOP subprocess completions arrive as `BackgroundJobComplete` via JobManager -> queue.
- **Chapter 3 (Background Jobs):** `JobKind.SOP` is spawned by `_spawn_sop_subprocess` in runner.py.
- **Chapter 4 (YOLO Mode):** sop_runner.py constructs the inferencer with `yolo_mode=True`.
- **Chapter 6 (Prompt Integration):** `## Available SOPs` and `## Active SOP` template sections consume `SOPRegistry.list()` and `active_sop`.
- **Chapter 7 (Scenarios):** Scenarios 4 and 5 exercise the full SOP lifecycle.
- **Chapter 8 (Roadmap):** Phase F covers this chapter (PRs F.1, F.2, F.3).

---

## 7. Open Questions

1. **Resumable runs across server restart?** `WorkflowSessionState` is JSON-
   persisted, but a paused SOP has no process to revive. Re-entering via
   `/enter-sop` re-loads the SOP and the LLM picks up from `phase` +
   `phase_outputs`. This works because SOPs are inherently stateless prompts.

2. **Can `/enter-sop foo` and `/sop foo` run simultaneously?** Yes. They are
   independent runs with different `run_id`s. The in-conversation one shows
   as Active SOP; the background one shows in Running Background Jobs.

3. **Can a `/sop` subprocess launch its own `/sop`?** Yes -- nested SOPs
   spawn nested processes. The tree is acyclic by construction (each
   subprocess writes to its own workspace). Monitor process count.

4. **Why `NullInteractive` instead of a pipe-based interactive?** For v1,
   simplicity. Must-gates halt the process. A future iteration could add
   IPC-based gate forwarding to the parent session.

---

*Continued in `06_prompt_integration.md`.*
