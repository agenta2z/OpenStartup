# Integrated Plan — Task Simple Mode (Design + Implementation)

> Continuation of `INTEGRATED_TASK_SIMPLE_MODE.md` (which covers the
> comparison, ground-truth facts, and motivation). This file is the
> design + implementation details.

---

## 3. Workspace layout (NO new helper needed)

### 3.1 The path

Simple-mode workspaces use the **existing convention**:

```
<runtime_root>/tasks/task/task_<YYYYMMDD>_<HHMMSS>_<8hex>/
├── artifacts/
│   ├── meta.json                       # task lifecycle metadata
│   ├── inferencer_args.json            # leaf ctor + call args (REDACTED)
│   └── input_prompt.md                 # rendered prompt (verbatim)
├── checkpoints/                        # empty for single-step
├── logs/
│   └── session/
│       └── <InferencerClass>-<id>.jsonl(.parts)
├── _runtime/
│   └── inferencer_cache/
│       └── <InferencerClass>/          # leaf inferencer's own cache
└── outputs/
    ├── raw_response.txt                # full assembled raw response (incl. <Response> tags)
    ├── parsed_output.json              # extracted <Response> body + metadata
    └── implementation_report.md        # the detailed report the LLM wrote per output_path
```

`<runtime_root>` resolution: identical to today (`find_runtime_root()` in
`_shared/workspace_allocator.py`, 4-tier fallback).

**No `children/` directory** — simple mode is a single-node task. Tools
that walk `<runtime_root>/tasks/*/*/` MUST handle the absent `children/`
gracefully; verified by reading `children/` only when present.

### 3.2 Allocation — REUSE the existing helper, do NOT write a new one

This is where **both predecessor plans had a gap**: they both proposed
extracting a new `task/workspace.py` with `allocate_task_node_workspace`.
But the existing
`OpenStartup/src/openteam/server/resources/tools/_shared/workspace_allocator.py::allocate_tool_workspace("task", base_dir=...)`
already produces the **exact path pattern** simple mode needs.

Simple-mode executor calls **the same `_resolve_workspace(session_context, task_id)` function the heavy path uses today**, which in turn delegates to `allocate_tool_workspace`. Concretely:

```python
# In executor.py, simple-mode path:
workspace = _resolve_workspace(session_context, task_id=_new_task_id())
# This routes through:
#   - dispatcher-supplied working_dir if present (--resume / pre-allocated)
#   - <session_root>/tasks/task_<TS>_<uuid8>/ if session_root in context (server)
#   - <runtime_root>/tasks/task/task_<TS>_<uuid8>/ otherwise (CLI)
_init_node_subdirs(workspace, create_children_dir=False)
```

### 3.3 New helper — `_init_node_subdirs(workspace, *, create_children_dir)`

The ONE small new helper (10 lines), placed inline at the top of
`executor.py` (or in `_shared/workspace_allocator.py` if we want it to
be reusable across tools), creates the 5 standard subdirs after
`_resolve_workspace` returns:

```python
def _init_node_subdirs(workspace: Path, *, create_children_dir: bool = True) -> None:
    """Create the standard 5-folder node layout inside an allocated workspace.

    Idempotent; safe to call when subdirs already exist.

    Args:
        workspace: the allocated workspace root (from _resolve_workspace).
        create_children_dir: True for heavy/topology runs; False for simple.
    """
    for sub in ("artifacts", "checkpoints", "outputs"):
        (workspace / sub).mkdir(exist_ok=True)
    (workspace / "logs" / "session").mkdir(parents=True, exist_ok=True)
    (workspace / "_runtime" / "inferencer_cache").mkdir(parents=True, exist_ok=True)
    if create_children_dir:
        (workspace / "children").mkdir(exist_ok=True)
```

The heavy/topology path is updated to call the same helper with
`create_children_dir=True` (a one-line addition; the heavy path already
creates these dirs ad-hoc as it spins up children, but centralizing the
root-level pre-creation removes a class of race conditions).

### 3.4 Leaf inferencer factory (corrected ctor kwargs)

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
    target_path: Optional[str] = None,
) -> InferencerBase:
    """Construct a leaf inferencer by canonical name.

    NOTE on signature: we deliberately do NOT accept a `session_log_dir`
    parameter — verified by direct file read, neither ClaudeCodeCliInferencer
    nor RovoDevCliInferencer expose such a ctor kwarg. Their session log
    location is derived from cache_folder (or the base class's session
    manager). Passing cache_dir is sufficient.

    Args:
        leaf_name: one of LEAF_CLASS_NAME_MAP keys.
        model: model override (inferencer-specific name; resolved to
            model_id or model_name at the right kwarg per inferencer).
        cache_dir: typically <node_dir>/_runtime/inferencer_cache/<InferencerClass>/
            The leaf inferencer writes its streaming cache + (for CLI
            inferencers) derives the session log path from here.
        target_path: codebase path the inferencer operates on (subprocess cwd
            for CLI inferencers; no-op for API inferencers).
    """
    if leaf_name == "claude_code_cli":
        from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code import (
            ClaudeCodeCliInferencer,
        )
        return ClaudeCodeCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_name=model or "sonnet",       # NOTE: model_name, not model_id
            cache_folder=str(cache_dir) if cache_dir else None,
        )
    if leaf_name == "rovodev_cli":
        from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev import (
            RovoDevCliInferencer,
        )
        return RovoDevCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_id=model or "",                # NOTE: model_id, not model_name
            yolo=True,
            cache_folder=str(cache_dir) if cache_dir else None,
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

**Critical correction vs. both predecessor plans:**
- `ClaudeCodeCliInferencer` uses `model_name=` (not `model_id=`).
- Neither CLI inferencer takes `session_log_dir=`.
- API inferencers ignore `cache_dir` and `target_path` (no-op).

---

## 4. Tool.json changes

### 4.1 Two new parameters added to `tool.json`

```json
{
  "name": "--simple",
  "type": "flag",
  "default": false,
  "description": "Run as a single prompt against a leaf inferencer. Fast, cheap, transparent. (Phase 2: this becomes the default; pass --full to opt INTO the heavyweight topology.)"
},
{
  "name": "--leaf-inferencer",
  "type": "string",
  "default": "auto",
  "choices": ["auto", "claude_code_cli", "rovodev_cli", "claude_api", "openai_api"],
  "description": "Leaf inferencer to use in --simple mode. 'auto' = use the conversational inferencer's own base inferencer when invoked from chat; else fall back to claude_code_cli."
}
```

`--full`'s `"default": true` flips to `"default": false` in Phase 2 (one
release later). See §6 migration plan.

### 4.2 `--simple` precedence semantics

Even though `--simple` becomes the default in Phase 2, the explicit-flag
precedence is:

```
1.  --plan / --execute / --confirm explicitly set → that mode wins (overrides --simple).
2.  --full explicitly set + --simple explicitly set → ValueError (conflict).
3.  --full explicitly set → heavy mode.
4.  --simple explicitly set OR no mode flag → simple mode.
```

Rationale: the existing `--plan` / `--execute` / `--confirm` flags select
specialized planning topologies. They are categorically different from
`--simple` (single leaf) vs `--full` (consensus topology); they're
**phase selectors** within heavy mode. So they override `--simple`.

### 4.3 The new `_derive_mode_from_flags`

Replace the current 5-line function with:

```python
def _derive_mode_from_flags(
    arguments: dict,
    *,
    explicit_simple: bool = False,
    explicit_full: bool = False,
) -> str:
    """Map mutually-exclusive mode flags to a mode string.

    Precedence:
      1. --plan / --execute / --confirm (phase selectors) override everything.
      2. If --simple and --full both explicitly set → ValueError.
      3. If --full explicitly set → "full".
      4. Otherwise → "simple" (the new default in Phase 2; controlled by a
         feature flag in Phase 1 — see §6).

    `explicit_simple` / `explicit_full` are set by the CLI/tool dispatcher
    when the user typed the flag explicitly (vs. it being the schema's
    default). The dispatcher is responsible for distinguishing the two.
    """
    # Phase selectors win
    for flag, mode in (("plan", "plan"), ("execute", "execute"), ("confirm", "confirm")):
        if arguments.get(flag):
            return mode

    if explicit_simple and explicit_full:
        raise ValueError(
            "Cannot combine --simple and --full. "
            "Use --simple for a single leaf inferencer call, "
            "or --full for the heavyweight consensus topology."
        )

    if explicit_full or arguments.get("full"):
        return "full"

    # Default: simple in Phase 2; gated by feature flag in Phase 1
    if _default_mode_is_simple() or arguments.get("simple"):
        return "simple"

    return "full"  # Phase 1 fallback
```

Where `_default_mode_is_simple()` reads the feature flag (env var or
config) — Phase 1 returns False (current behavior preserved); Phase 2
returns True; Phase 3 the function and flag are removed and the default
is permanent.

### 4.4 How `explicit_simple` / `explicit_full` is determined

The tool-call dispatcher (in
`OpenStartup/src/openteam/server/services/tool_dispatcher.py` or
equivalent) compares the parsed argv against the tool.json defaults.
A flag is "explicit" iff the user's input string contained it. This
information is already passed to many tools via `arguments["_explicit"]`
or similar; if not, add a thin wrapper.

For the standalone CLI (`cli.py`), `argparse`'s
`store_const` + `default=NOT_SET` pattern produces the same
distinction.

### 4.5 The `--leaf-inferencer auto` policy

When `--leaf-inferencer` is `"auto"` (default), the simple-mode executor
picks a leaf via this 3-tier policy:

```python
def _resolve_auto_leaf(session_context: dict) -> str:
    # 1. If invoked from a conversational inferencer, prefer its own base
    #    inferencer's class name (most user-aligned). Pass-through via
    #    session_context["calling_inferencer_class"].
    caller = session_context.get("calling_inferencer_class")
    if caller in _CALLER_TO_LEAF_NAME:
        return _CALLER_TO_LEAF_NAME[caller]
    # 2. If env says so (ops override).
    env = os.environ.get("OPENTEAM_TASK_DEFAULT_LEAF")
    if env in LEAF_CLASS_NAME_MAP:
        return env
    # 3. Hardcoded last resort — claude_code_cli (most-tested + file tools).
    return "claude_code_cli"


_CALLER_TO_LEAF_NAME = {
    "ClaudeCodeCliInferencer": "claude_code_cli",
    "RovoDevCliInferencer":    "rovodev_cli",
    "ClaudeApiInferencer":     "claude_api",
    "OpenAIApiInferencer":     "openai_api",
}
```

**Rationale (resolves the predecessor-plan disagreement):** neither plan
should hardcode its author's favorite leaf. The runtime-correct choice
is: use what the parent agent uses (continuity); else what ops configured;
else a sensible default.

---

## 5. The simple-mode executor

### 5.1 Wiring into `executor.execute()`

```python
async def execute(arguments: dict, session_context: Optional[dict] = None) -> ToolExecutionResult:
    """Top-level entry. Resolves mode, dispatches."""
    explicit_simple = bool(session_context and session_context.get("_explicit_simple"))
    explicit_full   = bool(session_context and session_context.get("_explicit_full"))
    mode = _derive_mode_from_flags(arguments, explicit_simple=explicit_simple, explicit_full=explicit_full)

    if mode == "simple":
        return await _run_simple_mode(arguments, session_context or {})
    # else fall through to existing heavy/plan/execute/confirm dispatch
    return await _run_topology(arguments, session_context or {}, mode=mode)
```

`_run_topology` is the existing topology runner code (refactored into a
function for clarity, but functionally identical to today's behavior
when mode in {"full","plan","execute","confirm"}).

### 5.2 `_run_simple_mode` (full)

```python
async def _run_simple_mode(arguments: dict, session_context: dict) -> ToolExecutionResult:
    """Run a one-shot prompt through a leaf inferencer.

    Workspace: <runtime_root>/tasks/task/task_<ts>_<8hex>/ (no children/).
    """
    task_id = _new_task_id()                              # existing helper in executor.py
    workspace = _resolve_workspace(session_context, task_id)   # existing helper
    _init_node_subdirs(workspace, create_children_dir=False)   # new (§3.3)

    leaf_name = arguments.get("leaf_inferencer", "auto")
    if leaf_name == "auto":
        leaf_name = _resolve_auto_leaf(session_context)
    leaf_class_name = LEAF_CLASS_NAME_MAP[leaf_name]

    # Pre-create the leaf's own cache dir so inferencer_args.json captures
    # the correct absolute path BEFORE construction.
    cache_dir = workspace / "_runtime" / "inferencer_cache" / leaf_class_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Build the prompt by rendering the EXISTING implementation template.
    prompt = _render_simple_prompt(
        request=arguments["request"],
        session_context=session_context,
        workspace=workspace,
    )
    (workspace / "artifacts" / "input_prompt.md").write_text(prompt, encoding="utf-8")

    # Construct the leaf
    inferencer = make_leaf_inferencer(
        leaf_name=leaf_name,
        model=arguments.get("model"),
        cache_dir=cache_dir,
        target_path=session_context.get("workflow_target_path") or session_context.get("working_dir"),
    )

    # Persist (REDACTED) ctor + call args for replay/debugging
    _persist_inferencer_args(
        target_path=workspace / "artifacts" / "inferencer_args.json",
        inferencer=inferencer,
        prompt_file=workspace / "artifacts" / "input_prompt.md",
    )

    # Run inference with try/finally so we always write outputs and meta
    raw_response = ""
    status = "failed"
    started_at = _now_iso()
    error_message: Optional[str] = None
    try:
        async for chunk in inferencer.ainfer_streaming(prompt):
            raw_response += chunk
        status = "completed"
    except asyncio.CancelledError:
        status = "cancelled"
        raise  # propagate cancellation
    except Exception as e:
        status = "failed"
        error_message = repr(e)
        logger.exception("Simple-mode inference failed (task_id=%s): %s", task_id, e)
    finally:
        completed_at = _now_iso()
        # Always write raw_response (even partial on failure)
        (workspace / "outputs" / "raw_response.txt").write_text(raw_response, encoding="utf-8")
        parsed = _safe_parse_output(inferencer, raw_response, status)
        (workspace / "outputs" / "parsed_output.json").write_text(
            json.dumps(parsed, indent=2, default=str), encoding="utf-8",
        )
        _ensure_implementation_report(workspace, parsed)   # §5.4 fallback
        _write_meta(
            target_path=workspace / "artifacts" / "meta.json",
            task_id=task_id,
            mode="simple",
            leaf=leaf_name,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            error=error_message,
        )

    return ToolExecutionResult(
        success=(status == "completed"),
        output=parsed.get("response") or raw_response or (error_message or ""),
        artifacts={
            "workspace": str(workspace),
            "parsed_output": str(workspace / "outputs" / "parsed_output.json"),
            "implementation_report": str(workspace / "outputs" / "implementation_report.md"),
            "raw_response": str(workspace / "outputs" / "raw_response.txt"),
            "meta": str(workspace / "artifacts" / "meta.json"),
        },
        error=error_message,
    )
```

### 5.3 Prompt rendering (`_render_simple_prompt`)

Reuses `implementation/main/initial.jinja2`. Passes the verified-required
variables only.

```python
def _render_simple_prompt(
    request: str,
    session_context: dict,
    workspace: Path,
) -> str:
    """Render the EXISTING implementation/main/initial.jinja2 with simple-mode context.

    Variables passed:
      Required (per template ground truth, §2.5):
        input, task_preamble, output_path, instructions, notes, round_index
      Optional (already guarded in template):
        employee, task_instructions
      Simple-mode signal (NEW, added by §7 template edit):
        has_approved_plan = False (omitted → "no plan" branch)
    """
    template_vars = {
        # Required
        "input":                 request,
        "task_preamble":         _load_variable("task_preamble", "default", session_context, workspace),
        "task_instructions":     _load_variable("task_instructions", "default", session_context, workspace),
        "output_path":           str(workspace / "outputs" / "implementation_report.md"),
        "instructions":          _load_shared_namespace("instructions"),
        "notes":                 _load_shared_namespace("notes"),
        "round_index":           0,                       # collapsed by §7 template edit
        # Optional (template-guarded)
        "employee":              session_context.get("employee"),
        # Simple-mode signal (template defaults to no-plan branch when absent)
        # — we OMIT has_approved_plan rather than setting False, so the
        # template's `{% if has_approved_plan is defined and has_approved_plan %}`
        # falls into the else branch deterministically.
    }
    return render_template("implementation/main/initial.jinja2", template_vars)
```

### 5.4 Implementation-report fallback (`_ensure_implementation_report`)

```python
def _ensure_implementation_report(workspace: Path, parsed: dict) -> None:
    """Guarantee outputs/implementation_report.md exists.

    The template instructs the LLM to write to output_path. CLI leaves
    (Claude Code, Rovo Dev) honor this via their file-write tools. API
    leaves (claude_api, openai_api) cannot write files — for those, we
    persist the <Response> body to the same path so the artifact contract
    is uniform.
    """
    report = workspace / "outputs" / "implementation_report.md"
    if report.exists():
        return
    body = parsed.get("response") or parsed.get("output") or ""
    if body:
        report.write_text(body, encoding="utf-8")
    else:
        # Last-resort: write a stub so the file is always present.
        report.write_text("(no report generated)\n", encoding="utf-8")
```

### 5.5 `_persist_inferencer_args` (with secret redaction)

```python
_REDACT_FIELDS = {"api_key", "token", "secret", "password", "auth_token"}


def _persist_inferencer_args(
    target_path: Path,
    inferencer,
    prompt_file: Path,
) -> None:
    """Capture inferencer ctor kwargs + call metadata, redacting secrets."""
    if hasattr(inferencer, "__attrs_attrs__"):
        # attrs-based class
        ctor_kwargs = {
            a.name: getattr(inferencer, a.name)
            for a in inferencer.__attrs_attrs__
            if not a.name.startswith("_")
        }
    else:
        ctor_kwargs = {
            k: v for k, v in vars(inferencer).items()
            if not k.startswith("_") and not callable(v)
        }

    # Redact secrets (substring match, case-insensitive)
    redacted = {}
    for k, v in ctor_kwargs.items():
        if any(s in k.lower() for s in _REDACT_FIELDS):
            redacted[k] = "<REDACTED>"
        else:
            redacted[k] = _json_safe(v)

    payload = {
        "inferencer_class": type(inferencer).__name__,
        "ctor_kwargs": redacted,
        "inference_call": {
            "method": "ainfer_streaming",
            "prompt_file": str(prompt_file),
            "prompt_length_chars": prompt_file.stat().st_size if prompt_file.exists() else 0,
            "started_at": _now_iso(),
        },
    }
    target_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
```

### 5.6 `_safe_parse_output`

```python
def _safe_parse_output(inferencer, raw_response: str, status: str) -> dict:
    """Inferencer-specific parse with universal fallback.

    On success path: prefer inferencer.parse_output if available, else
    extract <Response>…</Response> body, else use the raw response.
    On failure: never call parse_output (it may itself raise); always
    return a stub dict.
    """
    if status != "completed":
        return {"response": raw_response, "status": status}

    if hasattr(inferencer, "parse_output"):
        try:
            return inferencer.parse_output(raw_response)
        except Exception as e:
            logger.warning("parse_output raised; falling back to <Response> extraction: %s", e)

    # Universal <Response> extraction
    m = re.search(r"<Response>(.*?)</Response>", raw_response, re.DOTALL)
    if m:
        return {"response": m.group(1).strip(), "status": status}
    return {"response": raw_response, "status": status}
```

### 5.7 `_write_meta`

```python
def _write_meta(*, target_path: Path, **fields) -> None:
    """Atomic write of meta.json via tempfile + rename."""
    payload = {k: v for k, v in fields.items() if v is not None}
    payload["schema_version"] = 1
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="meta.json.", suffix=".tmp", dir=str(target_path.parent))
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp_path, target_path)
    except Exception:
        try: os.unlink(tmp_path)
        except OSError: pass
        raise
```

---

*Continued in `INTEGRATED_TASK_SIMPLE_MODE_TEMPLATE.md` (template edit + migration + tests).*
