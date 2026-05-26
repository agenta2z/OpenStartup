# Chapter 5 — F5: `/sop`, `/enter-sop`, `/exit-sop` Tools

> **Implements:** F5 from `README.md`
> **Depends on:** F2 (input queue), F3 (background jobs — for `/sop` subprocess launch), F4 (YOLO mode)
> **Predecessor reference:** `workflow-as-first-class-citizen.md` (OpenTeam-side design)

---

## 1. Goal

Three new first-class tools for SOP lifecycle:

| Tool | Behavior |
|------|----------|
| `/enter-sop <name>` | Load SOP `<name>` into the CURRENT conversational inferencer as the **active SOP**. Sets `active_sop_id`, populates `<WorkflowDescription>` + `<WorkflowStatus>` + `<WorkflowNextStepGuidance>` for the next render. |
| `/exit-sop` | Unload the active SOP. Clears `active_sop_id`; the SOP run is saved as **paused** in the session's `WorkflowSessionState` so it can be re-entered later. |
| `/sop <name> [--var k=v]* [other flags]` | Launch a NEW conversational inferencer in a SUBPROCESS, in YOLO mode, with `<name>` as the active SOP. Returns a `BackgroundJob` (kind=SOP) — completion routes via JobManager. |

Combined with F3, `/sop` is most useful inside `/background-job`:
```
/background-job /sop code_optimization --var workflow_target_path=src/foo
```
spawns a fully autonomous SOP run in the background.

---

## 2. Design

### 2.1 SOP Registry

New module: `AgentFoundation/src/agent_foundation/common/sop/registry.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SOPDefinition:
    name: str                       # canonical id, e.g., "code_optimization"
    title: str                      # human-readable
    description: str                # short blurb (one paragraph)
    sop_path: Path                  # absolute path to the .md / .jinja2
    variables: list[str]            # declared variable names (for /sop --var validation)
    required_variables: list[str]
    phases: list[str]               # ordered phase names (parsed from SOP)
    has_must_gates: bool            # for UX: "this SOP can pause for input"


class SOPRegistry:
    """Discovers SOP definitions on disk and exposes a lookup API."""

    _SOP_DIRS = [
        "resources/prompt_templates/conversation/main/_variables/workflow_sop",
    ]

    def __init__(self, package_root: Path):
        self._package_root = Path(package_root)
        self._definitions: dict[str, SOPDefinition] = {}
        self._scan()

    def _scan(self) -> None:
        for rel in self._SOP_DIRS:
            base = self._package_root / rel
            if not base.is_dir(): continue
            for sop_file in sorted(base.iterdir()):
                if sop_file.suffix not in {".md", ".jinja2", ".j2", ".yaml", ".yml"}:
                    continue
                name = sop_file.stem  # e.g., "code_optimization"
                definition = self._parse_sop(name, sop_file)
                self._definitions[name] = definition

    def _parse_sop(self, name: str, path: Path) -> SOPDefinition:
        text = path.read_text(encoding="utf-8")
        # Use SOPManager to parse phases + gates
        sop = SOPManager.load(path)
        phases = [phase.name for phase in sop.phases]
        has_must_gates = any(getattr(g, "must", False) for g in sop.all_gates())
        # Variables: scan for `{{ var_name }}` Jinja2 references
        variables = sorted(set(re.findall(r"{{\s*(\w+)", text)))
        # required vs optional: assume all are required (SOP author can refine
        # via a future declaration block)
        required = variables
        # Title + description: first H1 / paragraph of the file
        title, description = _extract_title_desc(text, fallback=name)
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

    def get(self, name: str) -> Optional[SOPDefinition]:
        return self._definitions.get(name)

    def list(self) -> list[SOPDefinition]:
        return sorted(self._definitions.values(), key=lambda d: d.name)
```

The registry is built once at server startup and re-scanned on a SIGHUP (or
process restart). It's exposed to the conversational inferencer as
`self.sop_registry: SOPRegistry`.

### 2.2 The `WorkflowSessionState` mini-model

Lifted from the predecessor `workflow-as-first-class-citizen.md` and
simplified for AgentFoundation:

```python
@dataclass
class WorkflowRun:
    sop_id: str                    # the active sop name
    run_id: str                    # unique per-run, e.g., "wf-3f9c2a"
    status: str                    # "running" | "paused" | "completed" | "aborted"
    phase: str                     # current phase name
    phase_outputs: dict[str, Any]  # accumulated outputs
    variables: dict[str, Any]      # bound variable values
    started_at: str
    last_active_at: str


@dataclass
class WorkflowSessionState:
    runs: list[WorkflowRun] = field(default_factory=list)
    active_run_id: Optional[str] = None

    def active_run(self) -> Optional[WorkflowRun]:
        if not self.active_run_id: return None
        for r in self.runs:
            if r.run_id == self.active_run_id: return r
        return None

    def enter(self, sop_id: str, *, variables: dict | None = None) -> WorkflowRun:
        # Refuse second active
        if self.active_run_id is not None:
            raise WorkflowConflictError("Another SOP is active; exit first.")
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
        run = self.active_run()
        if run is None: return None
        run.status = "paused"
        self.active_run_id = None
        return run

    def resume(self, run_id: str) -> WorkflowRun:
        if self.active_run_id is not None:
            raise WorkflowConflictError("Another SOP is active; exit first.")
        for r in self.runs:
            if r.run_id == run_id:
                if r.status != "paused":
                    raise WorkflowConflictError(f"Run {run_id} status is {r.status}, not paused.")
                r.status = "running"
                r.last_active_at = _now()
                self.active_run_id = r.run_id
                return r
        raise KeyError(run_id)
```

Persistence: serialized as part of the session JSON; lives at
`<session_root>/.workflow_state.json` for AgentFoundation-local sessions.
For OpenTeam server sessions, persisted via existing `data_service.update_workflow_context`.

### 2.3 The `/enter-sop` tool

`AgentFoundation/src/agent_foundation/resources/tools/enter_sop/tool.json`:

```json
{
  "name": "enter_sop",
  "aliases": ["enter-sop"],
  "tool_type": "Action",
  "category": "workflow",
  "description": "Load a Standard Operating Procedure (SOP) into the current conversation as the active workflow. The SOP's phases, confirmation gates, and tools will guide subsequent turns.",
  "parameters": [
    {
      "name": "name",
      "type": "string",
      "required": true,
      "positional": true,
      "description": "Canonical SOP name (e.g., 'code_optimization', 'model_optimization'). Available SOPs are listed in the 'Available SOPs' prompt section."
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
    "/enter-sop code_optimization --var workflow_target_path=src/foo --reason 'user wants to optimize the hot loop'"
  ],
  "executor_module": "agent_foundation.resources.tools.enter_sop.executor"
}
```

Executor (`executor.py`):

```python
async def execute(arguments: dict, session_context: dict) -> ToolExecutionResult:
    name = arguments["name"]
    registry = get_sop_registry()
    definition = registry.get(name)
    if definition is None:
        available = ", ".join(d.name for d in registry.list())
        return ToolExecutionResult(success=False, output=f"Unknown SOP '{name}'. Available: {available}")

    variables = _parse_kv(arguments.get("var") or [])

    # Validate required vars
    missing = [v for v in definition.required_variables if v not in variables]
    # Soft-warn (LLM can still collect them via clarification later); don't fail

    workflow_state = _get_workflow_state(session_context)
    try:
        run = workflow_state.enter(name, variables=variables)
    except WorkflowConflictError as e:
        return ToolExecutionResult(success=False, output=str(e))
    _persist_workflow_state(session_context, workflow_state)

    # Inject signal for inferencer to discard cached SOP / re-render
    context_updates = {
        "active_sop_id": name,
        "active_run_id": run.run_id,
        "_active_workflow_changed": True,
        "workflow_description": definition.description,
        "workflow_target_path": variables.get("workflow_target_path"),
    }

    summary = (
        f"Entered SOP '{name}' as run {run.run_id}. "
        f"Phases: {' → '.join(definition.phases)}. "
        + (f"Bound variables: {variables}." if variables else "")
        + (f" Missing required variables: {missing}." if missing else "")
    )
    return ToolExecutionResult(
        success=True,
        output=summary,
        context_updates=context_updates,
    )
```

### 2.4 The `/exit-sop` tool

`AgentFoundation/src/agent_foundation/resources/tools/exit_sop/tool.json`:

```json
{
  "name": "exit_sop",
  "aliases": ["exit-sop"],
  "tool_type": "Action",
  "category": "workflow",
  "description": "Exit the currently active SOP. The run is paused (state preserved) and may be resumed later via /enter-sop with the same name OR a dedicated resume mechanism (future).",
  "parameters": [
    {
      "name": "--reason",
      "type": "string",
      "description": "Free-text rationale for exiting. Logged for audit."
    }
  ],
  "examples": [
    "/exit-sop --reason 'user wants to switch to ad-hoc Q&A'"
  ],
  "executor_module": "agent_foundation.resources.tools.exit_sop.executor"
}
```

Executor: mirrors `enter_sop.executor` but calls `workflow_state.exit()`.
`context_updates = {"active_sop_id": None, "active_run_id": None, "_active_workflow_changed": True}`.

### 2.5 The `/sop` tool (subprocess launcher)

`AgentFoundation/src/agent_foundation/resources/tools/sop/tool.json`:

```json
{
  "name": "sop",
  "tool_type": "Action",
  "category": "workflow",
  "asynchronous": true,
  "description": "Launch a Standard Operating Procedure as an autonomous background process. A separate conversational inferencer runs the SOP in YOLO mode (no user prompts unless [__must__] gates require). Use --background to non-block; default is fire-and-forget.",
  "parameters": [
    {
      "name": "name",
      "type": "string",
      "required": true,
      "positional": true,
      "description": "Canonical SOP name (see 'Available SOPs')."
    },
    {
      "name": "--var",
      "type": "list",
      "description": "SOP variable bindings: --var key=value. Repeat for multiple."
    },
    {
      "name": "--inferencer",
      "type": "string",
      "default": "rovodev_cli",
      "description": "Leaf inferencer for the subprocess (defaults to rovodev_cli)."
    },
    {
      "name": "--model",
      "type": "string",
      "description": "Override the leaf inferencer's model."
    },
    {
      "name": "--fork-on-completion",
      "type": "flag",
      "description": "On completion, fork the calling conversation into a new session with the SOP's final output as seed."
    },
    {
      "name": "--no-background",
      "type": "flag",
      "description": "Run synchronously inline (rare; mostly for tests). Default is background via JobManager."
    }
  ],
  "examples": [
    "/sop code_optimization --var workflow_target_path=src/foo",
    "/sop role_creation --var role_name=sre",
    "/sop code_optimization --var workflow_target_path=src/foo --fork-on-completion"
  ],
  "executor_module": "agent_foundation.resources.tools.sop.executor"
}
```

Executor:

```python
async def execute(arguments: dict, session_context: dict) -> ToolExecutionResult:
    name = arguments["name"]
    registry = get_sop_registry()
    definition = registry.get(name)
    if definition is None:
        return ToolExecutionResult(success=False, output=f"Unknown SOP '{name}'.")

    variables = _parse_kv(arguments.get("var") or [])
    inferencer_name = arguments.get("inferencer", "rovodev_cli")
    model = arguments.get("model")
    fork = bool(arguments.get("fork_on_completion"))
    background = not bool(arguments.get("no_background"))

    if background:
        # Submit as a JobKind.SOP background job. JobManager.runner._spawn_sop_subprocess
        # builds the actual python -m argv (see §2.6 below).
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
            session_root=session_root_from_context(session_context),
            fork_on_completion=fork,
            label=f"SOP: {name}",
        )
        job = await JobManager.instance().submit(spec)
        return ToolExecutionResult(
            success=True,
            output=f"SOP '{name}' launched as background job {job.id}. Workspace: {job.workspace}.",
            artifacts={"job_id": job.id, "workspace": str(job.workspace)},
        )

    # Synchronous inline path (--no-background); used in tests/dev only
    result_text = await _run_sop_inline(definition, variables, inferencer_name, model)
    return ToolExecutionResult(success=True, output=result_text)
```

### 2.6 The subprocess SOP runner entry point

New module: `AgentFoundation/src/agent_foundation/scripts/sop_runner.py`
(runnable via `python -m agent_foundation.scripts.sop_runner ...`)

```python
"""Subprocess entry point launched by JobManager.runner._spawn_sop_subprocess.

Usage:
    python -m agent_foundation.scripts.sop_runner <sop_name> \
        [--var key=value]* \
        --inferencer <name> \
        [--model <id>] \
        --workspace <path>
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sop_name")
    parser.add_argument("--var", action="append", default=[])
    parser.add_argument("--inferencer", default="rovodev_cli")
    parser.add_argument("--model", default=None)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    variables = _parse_kv(args.var)
    workspace = Path(args.workspace)

    registry = SOPRegistry(package_root=_find_agent_foundation_root())
    definition = registry.get(args.sop_name)
    if definition is None:
        print(f"Unknown SOP '{args.sop_name}'", file=sys.stderr)
        sys.exit(2)

    # Build the leaf inferencer
    leaf = make_leaf_inferencer(args.inferencer, model=args.model, workspace=workspace)

    # Build the conversational inferencer in YOLO mode
    inferencer = ConversationalInferencer(
        base_inferencer=leaf,
        prior_context={
            "session_id": f"sop-{args.sop_name}-{uuid.uuid4().hex[:6]}",
            "session_root_path": str(workspace),
            "yolo_vars": variables,
            "active_sop_id": args.sop_name,
        },
        yolo_mode=True,
        sop_registry=registry,
        interactive=NullInteractive(),  # no human attached
        tool_registry=load_all_tools(),
        # ... other ctor args
    )

    # Seed the conversation with a single "begin" message and run the loop
    seed = f"Begin SOP execution: {args.sop_name}. Variables: {variables}."
    result = asyncio.run(inferencer.run_agentic_loop(seed, session_id=inferencer.prior_context["session_id"]))

    # Write final summary
    (workspace / "final_summary.md").write_text(result.text or "", encoding="utf-8")
    # Audit log accumulates throughout the loop (yolo_decisions.jsonl)
    sys.exit(0 if result.terminated_cleanly else 1)


if __name__ == "__main__":
    main()
```

Key invariants:
- The subprocess uses `NullInteractive` — any conversation tool not auto-resolved
  by YOLO (i.e., must-gates) causes the inferencer to detect "no human" and
  exit with status `must_gate_unattended`. JobManager marks the job FAILED
  with summary including `[BLOCKED ON MUST-GATE]`.
- The subprocess writes `yolo_decisions.jsonl` (every auto-resolution), and
  any tool outputs land in the workspace (each action tool's `_jobs/<...>/`).
- On completion, the parent JobManager polls process exit and posts a
  `BackgroundJobComplete` to the spawning session's queue (or forks if
  `--fork-on-completion`).

### 2.7 Available-SOPs prompt block (preview)

Full spec in chapter 6. Two new prompt sections:

```jinja2
{% if available_sops is defined and available_sops %}
## Available SOPs

{% for sop in available_sops %}
- **{{ sop.name }}** — {{ sop.title }}
  - Phases: {{ sop.phases | join(" → ") }}
  - Variables: {{ sop.variables | join(", ") }}
  - {% if sop.has_must_gates %}⚠ has mandatory user-input gates{% endif %}
  - Enter: `/enter-sop {{ sop.name }}` or `/sop {{ sop.name }}` (background)
{% endfor %}
{% endif %}

{% if active_sop is defined and active_sop %}
## Active SOP: {{ active_sop.name }}

Run ID: `{{ active_run_id }}`
{# Existing <WorkflowDescription> / <WorkflowStatus> / <WorkflowNextStepGuidance> follow #}
{% endif %}
```

---

## 3. End-to-End Wiring

### 3.1 Constructor injection chain

```
server bootstrap
  └─ SOPRegistry(package_root)
       └─ injected into each new ConversationalInferencer as self.sop_registry
            └─ /enter-sop executor reads via get_sop_registry() (module-global accessor)
            └─ /sop executor too
            └─ sop_runner subprocess constructs its own via the same call
```

For non-server (CLI) use, there's a module-global lazy singleton:
```python
_global_registry: SOPRegistry | None = None
def get_sop_registry() -> SOPRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SOPRegistry(package_root=_find_agent_foundation_root())
    return _global_registry
```

### 3.2 Tool routing diff

The conversational inferencer's `_execute_tool_call` doesn't change. Tool
registry auto-discovers `resources/tools/{enter_sop,exit_sop,sop,background_job}/`
on startup via the existing `load_all_tools()`.

### 3.3 Prompt template variable plumbing

`_render_prompt` already passes `prior_context` into the template. Add:

```python
template_vars = {
    ...
    "available_sops": self.sop_registry.list() if self.sop_registry else [],
    "active_sop": self._active_sop_definition(),
    "active_run_id": self.prior_context.get("active_run_id"),
    "yolo_mode": self.yolo_mode,
    "running_background_jobs": JobManager.instance().list_running(session_id=self._session_id),
}
```

`_active_sop_definition()` reads `prior_context["active_sop_id"]` and returns
the corresponding `SOPDefinition` (or None).

### 3.4 SOP file discovery — find_sop_file change

Today `find_sop_file()` returns one hardcoded path. Replace with:

```python
def find_sop_file(self, sop_name: Optional[str] = None) -> Optional[Path]:
    """If sop_name given, return that SOP file. Else fall back to active_sop_id."""
    name = sop_name or self._active_sop_id
    if not name: return None
    registry = get_sop_registry()
    definition = registry.get(name)
    return definition.sop_path if definition else None
```

The legacy path `_variables/workflow/sop.{ext}` keeps working IF a SOP named
`sop` exists (rename it to `default` and add an alias) — OR we keep the
existing flat path as a fallback inside `find_sop_file` when registry lookup
fails (per predecessor plan §3.5).

---

## 4. Audit Trail (`yolo_decisions.jsonl`)

Every YOLO auto-resolution AND every tool call in a `/sop` subprocess writes
one JSONL line:

```json
{"ts": "2026-05-19T15:58:01Z", "phase": "Phase 2", "kind": "yolo_auto_resolve", "tool_type": "confirmation", "decision": "yes", "must_gate": false, "tool_args": {...}}
{"ts": "2026-05-19T15:58:03Z", "phase": "Phase 2", "kind": "tool_call", "tool_name": "investigate-system", "args": {...}, "result_summary": "..."}
{"ts": "2026-05-19T15:58:30Z", "phase": "Phase 3b", "kind": "must_gate_blocked", "tool_type": "confirmation", "reason": "no human attached"}
```

The post-SOP-completion `summary` (built by `build_summary` in chapter 3 §3.8)
prefers the tail of this file over generic stdout tail because it's
LLM-readable.

---

## 5. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/common/sop/__init__.py` | NEW. Re-exports. |
| `agent_foundation/common/sop/registry.py` | NEW. `SOPRegistry`, `SOPDefinition`. |
| `agent_foundation/common/sop/state.py` | NEW. `WorkflowRun`, `WorkflowSessionState`, `WorkflowConflictError`. |
| `agent_foundation/resources/tools/enter_sop/tool.json` | NEW. Schema above. |
| `agent_foundation/resources/tools/enter_sop/executor.py` | NEW. |
| `agent_foundation/resources/tools/exit_sop/tool.json` | NEW. |
| `agent_foundation/resources/tools/exit_sop/executor.py` | NEW. |
| `agent_foundation/resources/tools/sop/tool.json` | NEW. |
| `agent_foundation/resources/tools/sop/executor.py` | NEW. |
| `agent_foundation/scripts/sop_runner.py` | NEW. Subprocess entry point. |
| `agent_foundation/scripts/__init__.py` | NEW (empty). |
| `agent_foundation/common/jobs/runner.py` | Add `_spawn_sop_subprocess` (uses `python -m agent_foundation.scripts.sop_runner`). |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` | Add `sop_registry` attrib. Plumb `available_sops`, `active_sop`, `yolo_mode` template vars. Update `find_sop_file` to consult registry. Cache invalidation on `_active_workflow_changed` signal. |
| `agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` | Add `## Available SOPs` and `## Active SOP` sections (full spec in chapter 6). |
| `tests/agent_foundation/.../sop/test_registry.py` | NEW. |
| `tests/agent_foundation/.../sop/test_enter_exit_sop.py` | NEW. |
| `tests/agent_foundation/scripts/test_sop_runner.py` | NEW. |

---

## 6. Test Plan

| # | Test | Type |
|---|------|------|
| T5.1 | `SOPRegistry._scan` discovers `code_optimization.md` + `model_optimization.jinja2` + `role_creation.jinja2` | Unit |
| T5.2 | `SOPDefinition.has_must_gates == True` for code_optimization (it has `__must__`) | Unit |
| T5.3 | `/enter-sop code_optimization` → context_updates set correctly | Unit |
| T5.4 | `/enter-sop` twice without `/exit-sop` → WorkflowConflictError | Unit |
| T5.5 | `/exit-sop` followed by `/enter-sop same` → status transitions paused→running | Unit |
| T5.6 | `/sop foo --no-background` → inline execution returns | Integration |
| T5.7 | `/sop code_optimization --var workflow_target_path=...` (background) → JobKind.SOP job submitted | Integration |
| T5.8 | `sop_runner.py` with a SOP containing no must-gates → completes, writes final_summary.md + yolo_decisions.jsonl | E2E |
| T5.9 | `sop_runner.py` with must-gate → exit status 1, summary prefixed `[BLOCKED ON MUST-GATE]` | E2E |
| T5.10 | `/sop foo --fork-on-completion` → ForkRouter triggered on completion | Integration |
| T5.11 | Prompt template renders `## Available SOPs` when registry non-empty | Unit |
| T5.12 | Prompt template renders `## Active SOP` only when active_sop is set | Unit |
| T5.13 | `find_sop_file("code_optimization")` returns registry-resolved path | Unit |

---

## 7. Open Questions

1. **Resumable runs across server restart?** WorkflowSessionState is JSON-persisted,
   but a paused SOP doesn't have a process to revive — it's just metadata.
   Re-entering via `/enter-sop` re-loads the SOP and the LLM picks up from
   `phase` + `phase_outputs`. This works because SOPs are inherently
   stateless prompts. ✓ no special handling needed.
2. **Should `/sop` and `/enter-sop` accept the same SOP name simultaneously?**
   `/enter-sop foo` (in-conversation) + `/sop foo` (background subprocess)
   are independent runs with different `run_id`s. Allowed. The agent's
   prompt shows the in-conversation one as Active and the background one
   in Running Background Jobs.
3. **Can a `/sop` subprocess inferencer launch its own `/sop`?** Yes —
   JobManager is process-singleton, but the subprocess has its OWN
   JobManager instance. Nested SOPs spawn nested processes; the tree is
   acyclic by construction (each subprocess writes to its own workspace).
   Token cost and process count grow linearly; users should monitor.
4. **What about the predecessor's `resume_workflow` tool?** Subsumed by
   `/enter-sop <name>` because we don't track per-name resume IDs at the
   tool surface (workflow_state can hold multiple paused runs with the
   same name; latest paused-of-name resumes by default; explicit
   `--run-id <id>` flag added in a follow-up if needed).

---

*Continued in `06_prompt_template_changes.md`.*
