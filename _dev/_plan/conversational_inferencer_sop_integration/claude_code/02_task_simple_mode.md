# Chapter 2 -- F2: Task Simple Mode (Default)

> **Author:** Claude Code
> **Implements:** F2 from `README.md`
> **Depends on:** none (shares `leaf_factory.py` with F5)
> **Touches:** Task tool (`tool.json`, `executor.py`), new `leaf_factory.py`, new `workspace.py`

---

## 1. Goal

Make `/task` **cheap, fast, and transparent by default**. A single `/task "<request>"`
runs as ONE prompt against ONE leaf inferencer (default: `ClaudeCodeCliInferencer`).

The heavyweight dual-agent consensus topology (PTI, breakdown-multiflow,
proposer+reviewer) becomes **opt-in** via explicit `--full`, `--confirm`, or
`--plan`. The default behavior changes from `--full` to `--simple`.

### 1.1 The existing task workspace convention

Two `<runtime_root>` locations observed in the codebase:
- `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_runtime/tasks/` (CLI)
- `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/server/_runtime/tasks/` (server)

Naming pattern: `<runtime_root>/tasks/<task_name>/<task_name>_<YYYYMMDD>_<HHMMSS>_<8hex>/`

Every node in this workspace tree has the **5-folder layout**:

```
<node_dir>/
    artifacts/                # node-level intermediate artifacts
    checkpoints/              # per-step checkpoint JSON files
    logs/
        session/
            <InferencerClass>-<8hex>.jsonl(.parts)
    _runtime/
        inferencer_cache/
            <InferencerClass>/
    outputs/                  # final deliverables
```

### 1.2 Simple mode = same workspace, single node, no children

Simple-mode `/task` runs land at the **same path** as today's heavyweight
runs, with the **same folder layout**, but with NO nested `children/`
directory:

```
<runtime_root>/tasks/task/task_<YYYYMMDD>_<HHMMSS>_<8hex>/
    artifacts/
        meta.json                        # task lifecycle metadata
        inferencer_args.json             # leaf inferencer ctor + call args
        input_prompt.md                  # rendered prompt (verbatim)
    checkpoints/                         # empty for single-step
    logs/
        session/
            ClaudeCodeCliInferencer-<8hex>.jsonl(.parts)
    _runtime/
        inferencer_cache/
            ClaudeCodeCliInferencer/
    outputs/
        raw_response.txt                 # full assembled raw response
        parsed_output.json               # parse_output(raw_response) result
```

---

## 2. Current State

### 2.1 Task tool today

- **Schema:** `OpenStartup/src/openteam/server/resources/tools/task/tool.json`
  (also mirrored in `AgentFoundation/.../resources/tools/task/tool.json`).
- **Executor:** `OpenStartup/src/openteam/server/resources/tools/task/executor.py`
  (the `executor.execute()` function, dispatched via tool registry).
- **CLI:** `OpenStartup/src/openteam/server/resources/tools/task/cli.py`
  (standalone CLI, derived from `tool.json`).
- **Topologies:** `task/topologies/*.yaml` -- `pti.yaml`, `bta-dual.yaml`,
  `breakdown-multiflow-plan-then-implement.yaml` (current default), etc.
- **Default mode flag:** `--full` (`tool.json`: `"default": true`).

### 2.2 The leaf inferencer we will use

`ClaudeCodeCliInferencer` at
`AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/external/claude_code/claude_code_cli_inferencer.py`:

- Wraps the `claude` CLI subprocess
- Single-turn: `inf("prompt")` -> str
- Streaming: `async for chunk in inf.ainfer_streaming(prompt)`
- Has `has_local_access=True` by default
- Supports model override via constructor args

Also available: `RovoDevCliInferencer` (wraps `acli rovodev`), `ClaudeApiInferencer`
(direct API), `OpenAIApiInferencer`. The `--leaf-inferencer` flag lets the user
choose.

### 2.3 What changes vs. what stays

| Aspect | Today | After F2 |
|--------|-------|----------|
| Default mode | `--full` (PTI consensus) | `--simple` (one leaf-inferencer prompt) |
| `--full` semantics | Default-on, runs PTI | Opt-in flag, runs PTI as today |
| `--plan` / `--confirm` | Runs planning topology | Unchanged |
| Workspace layout | Same path, full `children/` tree | Same path, NO `children/` |
| Inferencer choice (simple) | N/A | `--leaf-inferencer claude_code_cli` (default) |
| Output (simple) | N/A | `parsed_output.json` (response text + metadata) |

---

## 3. Design

### 3.1 New `--simple` flag in `tool.json`

```json
{
  "name": "--simple",
  "type": "flag",
  "default": true,
  "description": "Run as a single prompt against a leaf inferencer (default). Fast, cheap, transparent. Disable with --no-simple or by passing --full/--plan/--confirm."
},
{
  "name": "--leaf-inferencer",
  "type": "string",
  "default": "claude_code_cli",
  "choices": ["claude_code_cli", "rovodev_cli", "claude_api", "openai_api"],
  "description": "Leaf inferencer for --simple mode."
}
```

Flip `--full`'s `"default": true` to `"default": false`.

### 3.2 Mode resolution precedence

```python
def resolve_mode(args: dict) -> str:
    """Determine task execution mode from parsed arguments.

    Precedence:
      1. Explicit non-simple modes take priority (--plan, --confirm, --execute, --full)
      2. --simple is default (true unless explicitly disabled)
      3. Fallback to full (--no-simple without other mode)

    Raises ValueError if --simple and --full both explicitly set.
    """
    explicit_simple = args.get("_explicit_simple", False)
    explicit_full = args.get("_explicit_full", False)
    if explicit_simple and explicit_full:
        raise ValueError(
            "Cannot combine --simple and --full. "
            "Use --simple for a single leaf inferencer call, "
            "or --full for the heavyweight consensus topology."
        )

    for explicit in ("plan", "confirm", "execute", "full"):
        if args.get(explicit):
            return explicit

    if args.get("simple", True):
        return "simple"

    return "full"
```

### 3.3 The simple-mode executor

New function in `executor.py`:

```python
async def _run_simple_mode(
    arguments: dict,
    session_context: dict,
) -> ToolExecutionResult:
    """Run a one-shot prompt through a leaf inferencer.

    Workspace: <runtime_root>/tasks/task/task_<ts>_<8hex>/
    with standard 5-folder node layout, NO children/.
    """
    # 1. Allocate workspace
    workspace = allocate_task_node_workspace(
        task_name="task",
        session_context=session_context,
        create_children_dir=False,
    )

    # 2. Build the prompt
    prompt = _render_simple_prompt(
        request=arguments["request"],
        session_context=session_context,
    )
    (workspace / "artifacts" / "input_prompt.md").write_text(
        prompt, encoding="utf-8"
    )

    # 3. Construct the leaf inferencer
    leaf_name = arguments.get("leaf_inferencer", "claude_code_cli")
    leaf_class_name = LEAF_CLASS_NAME_MAP[leaf_name]
    inferencer = make_leaf_inferencer(
        leaf_name=leaf_name,
        model=arguments.get("model"),
        cache_dir=workspace / "_runtime" / "inferencer_cache" / leaf_class_name,
        session_log_dir=workspace / "logs" / "session",
        target_path=session_context.get("workflow_target_path"),
    )

    # 4. Persist inferencer args for replay/debugging
    _persist_inferencer_args(
        workspace / "artifacts" / "inferencer_args.json", inferencer
    )

    # 5. Run inference with try/finally for error resilience
    raw_response = ""
    meta_status = "failed"
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        async for chunk in inferencer.ainfer_streaming(prompt):
            raw_response += chunk
        meta_status = "completed"
    except Exception as e:
        meta_status = "failed"
        raw_response += f"\n\n[ERROR] Inference failed: {e}"
        logger.error("Simple mode inference failed: %s", e)
    finally:
        # Always write outputs, even partial on failure
        (workspace / "outputs" / "raw_response.txt").write_text(
            raw_response, encoding="utf-8"
        )
        parsed = {}
        if hasattr(inferencer, "parse_output") and meta_status == "completed":
            try:
                parsed = inferencer.parse_output(raw_response)
            except Exception:
                parsed = {"response": raw_response}
        else:
            parsed = {"response": raw_response}
        (workspace / "outputs" / "parsed_output.json").write_text(
            json.dumps(parsed, indent=2, default=str), encoding="utf-8",
        )
        _write_meta(
            workspace / "artifacts" / "meta.json",
            status=meta_status,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    return ToolExecutionResult(
        success=(meta_status == "completed"),
        output=parsed.get("response", raw_response),
        artifacts={
            "workspace": str(workspace),
            "parsed_output": str(workspace / "outputs" / "parsed_output.json"),
        },
    )
```

### 3.4 Simple-mode prompt template

New template file:
`AgentFoundation/src/agent_foundation/resources/tools/task/templates/simple_initial.jinja2`

```jinja2
You are working on a task as part of a larger workflow.

{% if workflow_target_path is defined and workflow_target_path %}
**Target codebase path**: {{ workflow_target_path }}
{% endif %}

{% if session_root_path is defined and session_root_path %}
**Session root**: {{ session_root_path }}
{% endif %}

## Task Request

{{ request }}

## Instructions

- Treat this as a single self-contained task. Do not assume conversational follow-up.
- Implement the change end-to-end: design, code, tests, local validation.
- If you cannot complete the task, explain the blocker concretely in your final response.
- For PR submission: if the codebase has a configured online build pipeline,
  prefer relying on it for heavy integration tests; run only fast local
  validation (unit tests for the changed module, lint/formatter auto-fix).
- Be concise in your final summary. Lead with WHAT changed and the
  verification status.
```

This is intentionally minimal. The leaf inferencer (e.g. Claude Code CLI)
brings its own system prompt + tool-use machinery. We add only the workflow
context plus the request.

### 3.5 Workspace allocation helper

Extract from `executor.py` into a shared module:
`OpenStartup/src/openteam/server/resources/tools/task/workspace.py`

```python
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


def allocate_task_node_workspace(
    task_name: str,
    session_context: dict,
    *,
    create_children_dir: bool = True,
    short_id: Optional[str] = None,
) -> Path:
    """Create <runtime_root>/tasks/<task_name>/<task_name>_<ts>_<8hex>/
    with the standard 5 subdirs.

    Args:
      task_name: outer grouping dir name (e.g., "task", "create_role").
      session_context: dict with session/runtime configuration.
      create_children_dir: if True, also create children/ (for topology
        roots). Simple mode passes False.
      short_id: optional override; default = uuid4().hex[:8].

    Returns the absolute workspace path.
    """
    runtime_root = resolve_runtime_root(session_context)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sid = short_id or uuid.uuid4().hex[:8]
    workspace = Path(runtime_root) / "tasks" / task_name / f"{task_name}_{ts}_{sid}"
    workspace.mkdir(parents=True, exist_ok=True)
    for subdir in ("artifacts", "checkpoints", "outputs"):
        (workspace / subdir).mkdir(exist_ok=True)
    (workspace / "logs" / "session").mkdir(parents=True, exist_ok=True)
    (workspace / "_runtime" / "inferencer_cache").mkdir(parents=True, exist_ok=True)
    if create_children_dir:
        (workspace / "children").mkdir(exist_ok=True)
    return workspace


def resolve_runtime_root(session_context: dict) -> Path:
    """Resolve the runtime root directory.

    Fallback chain:
      1) explicit session_context['runtime_root']
      2) env OPENTEAM_RUNTIME_ROOT
      3) env-derived server _runtime/ (if running under OpenTeam server)
      4) CWD/_runtime/
    """
    if "runtime_root" in session_context:
        return Path(session_context["runtime_root"])
    if env := os.environ.get("OPENTEAM_RUNTIME_ROOT"):
        return Path(env)
    if (server := _detect_openteam_server_root()) is not None:
        return server / "_runtime"
    return Path.cwd() / "_runtime"
```

### 3.6 Leaf inferencer factory

`AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py`:

```python
from pathlib import Path
from typing import Optional

from agent_foundation.common.inferencers.inferencer_base import InferencerBase


LEAF_CLASS_NAME_MAP = {
    "claude_code_cli":  "ClaudeCodeCliInferencer",
    "rovodev_cli":      "RovoDevCliInferencer",
    "claude_api":       "ClaudeApiInferencer",
    "openai_api":       "OpenAIApiInferencer",
}


def make_leaf_inferencer(
    leaf_name: str,
    *,
    model: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    session_log_dir: Optional[Path] = None,
    target_path: Optional[str] = None,
) -> InferencerBase:
    """Construct a leaf inferencer by canonical name.

    Args:
      leaf_name: one of LEAF_CLASS_NAME_MAP keys.
      model: model override (inferencer-specific).
      cache_dir: <node_dir>/_runtime/inferencer_cache/<InferencerClass>/
      session_log_dir: <node_dir>/logs/session/
      target_path: codebase path for the inferencer to operate on.

    Shared by simple mode (chapter 2) and SOP subprocess runner (chapter 5).
    """
    if leaf_name == "claude_code_cli":
        from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code import (
            ClaudeCodeCliInferencer,
        )
        return ClaudeCodeCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_id=model or "",
            cache_folder=str(cache_dir) if cache_dir else None,
            session_log_dir=str(session_log_dir) if session_log_dir else None,
        )
    if leaf_name == "rovodev_cli":
        from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev import (
            RovoDevCliInferencer,
        )
        return RovoDevCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_id=model or "",
            yolo=True,
            cache_folder=str(cache_dir) if cache_dir else None,
            session_log_dir=str(session_log_dir) if session_log_dir else None,
        )
    if leaf_name == "claude_api":
        from agent_foundation.common.inferencers.api_inferencers.claude_api_inferencer import (
            ClaudeApiInferencer,
        )
        return ClaudeApiInferencer(model_id=model or "claude-opus-4-7")
    if leaf_name == "openai_api":
        from agent_foundation.common.inferencers.api_inferencers.openai_api_inferencer import (
            OpenAIApiInferencer,
        )
        return OpenAIApiInferencer(model_id=model or "gpt-4.1")
    raise ValueError(f"Unknown leaf inferencer: {leaf_name!r}")
```

### 3.7 `inferencer_args.json` schema

For replay and debugging, capture:

```json
{
  "inferencer_class": "ClaudeCodeCliInferencer",
  "ctor_kwargs": {
    "target_path": "/Users/tchen7/repo/src",
    "model_id": "claude-opus-4-7",
    "cache_folder": ".../_runtime/inferencer_cache/ClaudeCodeCliInferencer",
    "session_log_dir": ".../logs/session"
  },
  "inference_call": {
    "method": "ainfer_streaming",
    "prompt_file": "input_prompt.md",
    "prompt_length_chars": 1843,
    "started_at": "2026-05-19T15:54:12.103Z"
  },
  "completed_at": "2026-05-19T16:01:33.892Z",
  "duration_seconds": 441.789,
  "exit_status": "success"
}
```

Implementation: `_persist_inferencer_args()` uses `attrs.asdict()` on the
inferencer with a `_REDACT_FIELDS` set to filter secrets (`api_key`,
`token`, `secret`, `password`).

---

## 4. Backward Compatibility & Migration

### 4.1 The behavior change

**Before:** `/task "fix bug"` -> runs `breakdown-multiflow-plan-then-implement.yaml`
(heavyweight 2-agent consensus).

**After:** `/task "fix bug"` -> runs single `ClaudeCodeCliInferencer` prompt.

### 4.2 Three-phase migration

1. **Phase 1 (one release):** Ship with `--simple` defaulting to `False`,
   `--full` defaulting to `True` (current behavior). Emit deprecation warning
   when `--full` is implicit: "task default mode will change to --simple in
   release X. Pass --full explicitly to suppress this warning."

2. **Phase 2 (next release):** Flip defaults. `--simple` defaults to `True`.
   Old callers must add `--full` explicitly.

3. **Phase 3:** Remove deprecation warning, defaults stable.

A `TASK_DEFAULT_MODE` env var lets ops force one or the other for batch
jobs / CI. Values: `simple` (default after Phase 2), `full`.

### 4.3 Workspace layout migration

**Zero migration needed.** Both heavy mode (today) and simple mode (new)
write into the **same parent directory** with the **same 5-folder node
layout**. The only structural difference is that simple-mode workspaces
have no `children/` subdir. Existing tools that walk `<runtime_root>/tasks/`
continue to work unchanged -- they may need a small tweak to handle the
absent `children/` gracefully (treat as "leaf node"), but no path-pattern
changes.

### 4.4 SOP callsites

The existing SOP `code_optimization.md` Phase 4 says `/task <request>`. With
the new default = simple, that becomes a single leaf call per hypothesis --
which is the desired behavior (much cheaper). If a particular SOP needs
the heavy path, it must be updated to `/task --full <request>`.

---

## 5. Concrete Code-Change List

| File | Change |
|------|--------|
| `OpenStartup/src/openteam/server/resources/tools/task/tool.json` | Add `--simple`, `--leaf-inferencer`. Flip `--full` default to `false` (Phase 2). |
| `AgentFoundation/src/agent_foundation/resources/tools/task/tool.json` | Mirror the above. |
| `OpenStartup/src/openteam/server/resources/tools/task/executor.py` | Add `_run_simple_mode()`. Update `_derive_mode_from_flags` for new precedence. Add conflict detection for `--simple` + `--full`. Refactor: extract workspace allocation into shared `workspace.py`. |
| `OpenStartup/src/openteam/server/resources/tools/task/workspace.py` | NEW (extracted). `allocate_task_node_workspace()` + `resolve_runtime_root()`. |
| `AgentFoundation/src/agent_foundation/resources/tools/task/templates/simple_initial.jinja2` | NEW. Simple-mode prompt template. |
| `AgentFoundation/src/agent_foundation/common/jobs/__init__.py` | NEW (empty; populated further in chapter 3). |
| `AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py` | NEW. `make_leaf_inferencer()` + `LEAF_CLASS_NAME_MAP`. |
| `OpenStartup/src/openteam/server/resources/tools/task/cli.py` | Add `--simple` / `--leaf-inferencer` to argparse mirror. |
| `tests/openteam/tools/task/test_simple_mode.py` | NEW. See Section 6 test plan. |

---

## 6. Test Plan

| # | Test | Type |
|---|------|------|
| T2.1 | `_run_simple_mode("fix typo")` creates workspace at `<runtime_root>/tasks/task/task_<ts>_<8hex>/` with 5 standard subdirs and NO `children/` | Unit |
| T2.2 | `artifacts/inferencer_args.json` contains ctor kwargs, no secrets, correct `cache_folder` and `session_log_dir` paths | Unit |
| T2.3 | `make_leaf_inferencer("claude_code_cli", cache_dir=..., session_log_dir=...)` returns `ClaudeCodeCliInferencer` with those dirs configured | Unit |
| T2.4 | `make_leaf_inferencer("rovodev_cli")` returns `RovoDevCliInferencer` with `yolo=True` | Unit |
| T2.5 | `make_leaf_inferencer("unknown")` raises `ValueError` | Unit |
| T2.6 | Mode resolution: `{simple: True, full: True}` (both explicit) -> `ValueError` | Unit |
| T2.7 | Mode resolution: `{plan: True}` overrides default simple | Unit |
| T2.8 | Mode resolution: empty args -> `"simple"` | Unit |
| T2.9 | Mode resolution: `{confirm: True}` overrides default simple | Unit |
| T2.10 | `/task --simple "list files"` via slash dispatcher -> response captured, workspace has expected files | Integration (mock leaf) |
| T2.11 | `/task --full "fix"` still routes to topology runner; produces workspace with `children/` populated | Integration |
| T2.12 | Streaming chunks accumulate into `outputs/raw_response.txt` | Integration |
| T2.13 | Workspace path regex matches existing convention: `tasks/task/task_\d{8}_\d{6}_[0-9a-f]{8}` | Unit |
| T2.14 | `allocate_task_node_workspace(create_children_dir=False)` does NOT create `children/`; `create_children_dir=True` DOES | Unit |
| T2.15 | `resolve_runtime_root` fallback chain: explicit -> env -> server-detected -> CWD | Unit |
| T2.16 | Inference failure (exception during streaming) -> `meta.json` has `status: "failed"`, partial `raw_response.txt` written | Unit |
| T2.17 | `_REDACT_FIELDS` filter removes `api_key`, `token`, `secret` from `inferencer_args.json` | Unit |
| T2.E2E | Real `/task "what does this repo do?"` against Claude Code CLI -> workspace artifacts present, response sensible | E2E smoke |

---

## 7. Cross-References

- **Chapter 1 (Input Queue):** Queue enables background task completion delivery, but simple mode works without it (foreground execution).
- **Chapter 3 (Background Jobs):** `/background-job task ...` spawns a simple-mode task in a subprocess. The inner task workspace is at `<runtime_root>/tasks/task/task_<ts>_<8hex>/`; the JobManager's own bookkeeping is at `<runtime_root>/_jobs/bg-<id>/`.
- **Chapter 5 (SOP Lifecycle):** SOP subprocess runner uses `make_leaf_inferencer()` from the shared `leaf_factory.py`.
- **Chapter 8 (Roadmap):** Phase B ships the shared utilities (leaf factory, workspace helper); Phase C ships the simple-mode executor changes.

---

## 8. Open Questions

1. **Should `--simple` support multi-turn?** `ClaudeCodeCliInferencer` supports
   multi-turn sessions. Simple mode is one-shot in this proposal. Multi-turn
   is left to the parent conversational inferencer (which can call `/task`
   repeatedly with accumulating context).

2. **Default model for leaf?** Inherit from session model config; fall back to
   the inferencer's hardcoded default.

3. **What if the leaf inferencer needs MFA or auth mid-run?** The leaf streams
   to stderr; we surface the last 50 lines of stderr in the failure summary.
   Out of scope to auto-recover; user re-runs after auth.

4. **Why not skip the 5-folder layout for simple runs?** Rejected. Reasons:
   (a) Existing log viewers and the OpenTeam UI walk
   `<runtime_root>/tasks/*/*/logs/session/*.jsonl` -- flat layout would hide
   simple runs. (b) The leaf inferencer classes already write into these
   standard dirs when used as topology children. (c) Future evolution
   (wrapping a simple run with a verify step) becomes trivial.

5. **Why not a `simple.yaml` topology file?** Considered but rejected for
   Claude Code's plan. A YAML topology implies instantiation through the
   topology runner machinery, which adds unnecessary overhead for what is
   literally one inferencer call. `_run_simple_mode()` is a thin function
   that directly constructs and calls the leaf. If we later need YAML-driven
   simple mode (for config-file-based selection), we add the YAML then.

---

*Continued in `03_background_jobs.md`.*
