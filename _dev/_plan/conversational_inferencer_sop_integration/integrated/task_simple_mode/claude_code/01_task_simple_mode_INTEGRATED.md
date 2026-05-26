# Task Simple Mode — Final Integrated Plan (v2)

## Context

**Problem:** `/task "fix bug"` runs a heavyweight dual-agent consensus topology by default.
We need a fast, cheap, transparent default: one prompt → one leaf inferencer → done.

## If only one plan: Choose Plan B (RovoDev)

**Plan B is the superior plan overall.** It has deeper analysis (41 tests vs 16, 10 risks,
12 decision log entries), correct auto-leaf selection (3-tier policy), proper migration
phasing with explicit-vs-implicit flag detection, and the correct template reuse strategy.

**However, Plan B has two critical bugs and one gap:**
1. **`ToolExecutionResult` crash** — uses `success`, `output`, `artifacts`, `error` kwargs that DON'T EXIST on the actual class (only `result: str` + `context_updates: dict`). Would crash at runtime.
2. **No WebSocket streaming** — `_run_simple_mode` does `async for chunk in inferencer.ainfer_streaming(prompt)` without wiring to `interactive.stream_token_batches()`. Tokens never reach the UI.
3. **Manual `cache_dir` wiring** — passes `cache_dir` explicitly instead of using `InferencerWorkspace._workspace` setter which auto-configures cache_folder + loggers.

**Plan A (Claude Code) gets these three things right** but has weaker analysis depth.

**This integrated plan: Plan B's analysis + Plan A's correct implementation patterns.**

---

## 1. Critical Corrections

| Issue | Plan A (Claude Code) | Plan B (RovoDev) | Integrated |
|-------|---------------------|-------------------|------------|
| `ToolExecutionResult` fields | ✅ Correct: `result` + `context_updates` | ❌ BUG: uses non-existent `success`, `output`, `artifacts`, `error` | Use Plan A's correct fields |
| WebSocket streaming | ✅ Has `interactive.stream_token_batches()` | ❌ Missing — tokens never reach UI | Use Plan A's streaming integration |
| Workspace wiring | ✅ `InferencerWorkspace` + `inferencer._workspace = ws` | Uses manual `_init_node_subdirs` + explicit `cache_dir` | Use Plan A's InferencerWorkspace (auto-configures cache + loggers) |
| Template strategy | ✅ Reuse existing | ✅ Reuse existing (more thorough analysis) | Both agree — reuse `implementation/main/initial.jinja2` |
| Auto-leaf selection | Hardcoded `claude_code_cli` | ✅ 3-tier auto-pick | Use Plan B's auto-leaf |
| Migration phases | Basic 3-phase | ✅ Detailed with explicit flag detection | Use Plan B's migration |
| `session_log_dir` | ✅ Excluded | ✅ Excluded | Both agree — doesn't exist |
| `model_name` vs `model_id` | ✅ Correct distinction | ✅ Correct distinction | Both agree |
| `_TASK_BOOL_FLAGS` | ✅ Adds `"simple"` | Not mentioned | Add `"simple"` |
| `_TASK_MODE_ALIASES` | ✅ Adds `"task_simple"` | Not mentioned | Add `"task_simple": "simple"` |
| Error handling | ✅ try/finally + CancelledError | ✅ try/finally + CancelledError | Both agree |
| Test depth | 16 tests | ✅ 41 tests | Use Plan B's test plan |
| Risk analysis | None | ✅ 10 risks with mitigations | Use Plan B's risk section |

---

## 2. Design

### 2.1 Mode resolution

Update `_derive_mode_from_flags()` (executor.py line 141):

```python
def _derive_mode_from_flags(arguments: dict) -> Optional[str]:
    for f, m in (("plan", "plan"), ("execute", "execute"),
                 ("full", "full"), ("confirm", "confirm"),
                 ("simple", "simple")):
        if arguments.get(f):
            return m
    return None
```

Update `execute()` (line 543) — change default from `"full"` to `"simple"`:

```python
mode = arguments.get("mode") or _derive_mode_from_flags(arguments) or "simple"
```

Extend conflict detection (line 556):

```python
if sum(bool(arguments.get(f)) for f in ("plan", "execute", "full", "confirm", "simple")) > 1:
    return _error("Multiple mode flags; use one of --simple/--plan/--execute/--full/--confirm.")
```

### 2.2 Simple-mode dispatch (in `execute()`, before line 584)

```python
if mode == "simple":
    return await _run_simple_mode(
        request=request,
        arguments=arguments,
        session_context=session_context,
    )

return await _run_topology(...)  # existing code unchanged
```

### 2.3 `_run_simple_mode()` — the core function

```python
async def _run_simple_mode(
    request: str,
    arguments: dict,
    session_context: dict,
) -> ToolExecutionResult:
    """One-shot prompt through a single leaf inferencer.

    Workspace: <runtime_root>/tasks/task/task_<ts>_<8hex>/
    Same 5-folder layout as heavyweight runs, NO children/.
    """
    from agent_foundation.common.inferencers.inferencer_workspace import InferencerWorkspace
    from agent_foundation.common.jobs.leaf_factory import make_leaf_inferencer

    sc = session_context or {}
    task_id = sc.get("task_id") or f"task-{uuid.uuid4().hex[:8]}"

    # 1. Allocate workspace (reuse existing helper — no new workspace module)
    workspace_dir = _resolve_workspace(sc, task_id)

    # 2. InferencerWorkspace — creates 5 standard dirs
    workspace = InferencerWorkspace(root=str(workspace_dir))
    workspace.ensure_dirs("_runtime")

    # 3. Resolve leaf inferencer
    leaf_name = arguments.get("leaf_inferencer", "auto")
    if leaf_name == "auto":
        leaf_name = _resolve_auto_leaf(sc)
    model = arguments.get("model")
    target_path = sc.get("workflow_target_path") or sc.get("working_dir")

    inferencer = make_leaf_inferencer(leaf_name, model=model, target_path=target_path)

    # 4. Assign workspace → auto-configures cache_folder + loggers
    inferencer._workspace = workspace

    # 5. Render prompt (reuse existing implementation/main/initial.jinja2)
    prompt = _render_simple_prompt(request, workspace, sc)
    Path(workspace.artifacts_dir, "input_prompt.md").write_text(prompt, encoding="utf-8")

    # 6. Persist inferencer args (secrets redacted)
    _persist_inferencer_args(Path(workspace.artifacts_dir, "inferencer_args.json"), inferencer)

    # 7. Run with streaming + error resilience
    raw_response = ""
    status = "failed"
    started_at = _now_iso()
    error_msg: Optional[str] = None
    try:
        interactive = sc.get("interactive")
        if (interactive
            and hasattr(interactive, "stream_token_batches")
            and hasattr(inferencer, "ainfer_streaming")):
            # Stream to WebSocket UI
            async def _token_gen():
                nonlocal raw_response
                async for chunk in inferencer.ainfer_streaming(prompt):
                    raw_response += chunk
                    yield chunk, {"task_id": task_id}
            raw_response = await interactive.stream_token_batches(
                _token_gen(),
                sc.get("session_id", ""),
                task_id=task_id,
            )
        else:
            async for chunk in inferencer.ainfer_streaming(prompt):
                raw_response += chunk
        status = "completed"
    except asyncio.CancelledError:
        status = "cancelled"
        raise
    except Exception as e:
        status = "failed"
        error_msg = repr(e)
        logger.exception("Simple-mode inference failed (task_id=%s)", task_id)
    finally:
        Path(workspace.outputs_dir, "raw_response.txt").write_text(
            raw_response, encoding="utf-8")
        parsed = _safe_parse_output(inferencer, raw_response, status)
        Path(workspace.outputs_dir, "parsed_output.json").write_text(
            json.dumps(parsed, indent=2, default=str), encoding="utf-8")
        _ensure_implementation_report(Path(workspace.outputs_dir), parsed)
        _write_meta(
            Path(workspace.artifacts_dir, "meta.json"),
            task_id=task_id, mode="simple", leaf=leaf_name,
            status=status, started_at=started_at,
            completed_at=_now_iso(), error=error_msg,
        )

    # CORRECT ToolExecutionResult fields (result + context_updates only)
    return ToolExecutionResult(
        result=parsed.get("response", raw_response),
        context_updates={
            "workspace_path": str(workspace_dir),
            "success": status == "completed",
        },
    )
```

### 2.4 Prompt rendering — reuse existing template

```python
def _render_simple_prompt(request: str, workspace, session_context: dict) -> str:
    """Render implementation/main/initial.jinja2 with simple-mode variables.

    Key difference from heavy mode: omits has_approved_plan (triggers "no plan"
    branch), sets round_index=0 (collapses roundN/ path segments).
    """
    template_vars = {
        "input":             request,
        "task_preamble":     "",
        "task_instructions": "",
        "output_path":       workspace.output_path("implementation_report.md"),
        "round_index":       0,
        "employee":          session_context.get("employee"),
        # Omit has_approved_plan → template renders "no plan" branch
    }
    return _render_template("implementation/main/initial.jinja2", template_vars)
```

### 2.5 Template changes — 2 surgical `{% if %}` guards

**File:** `implementation/main/initial.jinja2`

**Edit A (line 41):** Wrap "APPROVED PLAN" block:

```jinja2
{% if has_approved_plan is defined and has_approved_plan %}
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
{% else %}
- You are starting from a single user request without a pre-approved plan.
  * Read minimally to ground yourself in the relevant code. DO NOT investigate the entire codebase.
  * Act decisively. If ambiguous, pick the most plausible interpretation, state it in your `<Response>`, and proceed.
{% endif %}
```

**Edit B (lines 25-26):** Collapse `round_index` when falsy:

```jinja2
tests/{% if round_index %}round{{ round_index }}/{% endif %}
benchmarks/{% if round_index %}round{{ round_index }}/{% endif %}
```

**Topology runner:** Add `has_approved_plan=True` to feed dict when rendering
implementation-child nodes in `multi_flow_inferencer.py` (preserves byte-identical
heavy-mode behavior).

### 2.6 Auto-leaf selection (from Plan B)

```python
_CALLER_TO_LEAF = {
    "ClaudeCodeCliInferencer": "claude_code_cli",
    "RovoDevCliInferencer":    "rovodev_cli",
    "ClaudeApiInferencer":     "claude_api",
}

def _resolve_auto_leaf(session_context: dict) -> str:
    caller = session_context.get("calling_inferencer_class")
    if caller in _CALLER_TO_LEAF:
        return _CALLER_TO_LEAF[caller]
    env = os.environ.get("OPENTEAM_TASK_DEFAULT_LEAF")
    if env and env in LEAF_CLASS_NAME_MAP:
        return env
    return "claude_code_cli"
```

### 2.7 Leaf factory

New: `AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py`

```python
LEAF_CLASS_NAME_MAP = {
    "claude_code_cli": "ClaudeCodeCliInferencer",
    "rovodev_cli":     "RovoDevCliInferencer",
    "claude_api":      "ClaudeApiInferencer",
}

def make_leaf_inferencer(leaf_name, *, model=None, target_path=None):
    """Construct by name. Caller assigns workspace after construction."""
    if leaf_name == "claude_code_cli":
        from ...external.claude_code import ClaudeCodeCliInferencer
        return ClaudeCodeCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_name=model or "sonnet",  # model_name, NOT model_id
        )
    if leaf_name == "rovodev_cli":
        from ...external.rovodev import RovoDevCliInferencer
        return RovoDevCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_id=model or "",          # model_id, NOT model_name
            yolo=True,
        )
    if leaf_name == "claude_api":
        from ...api_inferencers.claude_api_inferencer import ClaudeApiInferencer
        return ClaudeApiInferencer(model_id=model or "claude-opus-4-7")
    raise ValueError(f"Unknown leaf: {leaf_name!r}")
```

Note: NO `session_log_dir` parameter (doesn't exist on any inferencer).
Note: NO `cache_folder` parameter — auto-configured via workspace assignment.

### 2.8 tool.json + WebSocket route changes

**tool.json:** Add `--simple` (default true), `--leaf-inferencer` (default "auto").
Flip `--full` default to false.

**manager_websocket_routes.py:**
- Add `"simple"` to `_TASK_BOOL_FLAGS`
- Add `"task_simple": "simple"` to `_TASK_MODE_ALIASES`

**cli.py:** Add `--simple`, `--leaf-inferencer` to argparse mutual-exclusion group.

---

## 3. Code-Change List

| # | File | Change |
|---|------|--------|
| 1 | `OpenStartup/.../tools/task/tool.json` | Add `--simple`, `--leaf-inferencer`. Flip `--full` default. |
| 2 | `OpenStartup/.../tools/task/executor.py` | Add `_run_simple_mode`, `_render_simple_prompt`, `_resolve_auto_leaf`, `_persist_inferencer_args`, `_safe_parse_output`, `_ensure_implementation_report`, `_write_meta`. Update `_derive_mode_from_flags`, `execute()`. |
| 3 | `OpenStartup/.../prompt_templates/implementation/main/initial.jinja2` | 2 `{% if %}` guards (§2.5) |
| 4 | `OpenStartup/.../routes/manager_websocket_routes.py` | Add to `_TASK_BOOL_FLAGS` + `_TASK_MODE_ALIASES` |
| 5 | `OpenStartup/.../tools/task/cli.py` | Add `--simple`, `--leaf-inferencer` to argparse |
| 6 | `AgentFoundation/.../common/jobs/__init__.py` | NEW (empty) |
| 7 | `AgentFoundation/.../common/jobs/leaf_factory.py` | NEW |
| 8 | `AgentFoundation/.../flow_inferencers/multi_flow_inferencer.py` | Add `has_approved_plan=True` to impl-child feed |
| 9 | `test/.../test_simple_mode.py` | NEW — tests per §4 |

**New files: 3.** Modified files: 6. **No new templates. No new workspace modules.**

---

## 4. Test Plan (from Plan B, extended)

| # | Test | Type |
|---|------|------|
| T1 | Mode: empty args → `"simple"` | Unit |
| T2 | Mode: `{plan: True}` → `"plan"` (overrides simple) | Unit |
| T3 | Mode: `{simple: True, full: True}` → error | Unit |
| T4 | Mode: `{full: True}` → `"full"` | Unit |
| T5 | Workspace: 5 dirs created, NO `children/` | Unit |
| T6 | `make_leaf_inferencer("claude_code_cli")` → `model_name="sonnet"` | Unit |
| T7 | `make_leaf_inferencer("rovodev_cli")` → `model_id`, `yolo=True` | Unit |
| T8 | `make_leaf_inferencer("unknown")` → ValueError | Unit |
| T9 | Template: no `has_approved_plan` → "no plan" wording | Unit |
| T10 | Template: `has_approved_plan=True` → "APPROVED PLAN" wording | Unit |
| T11 | Template: `round_index=0` → no `round0/`; `round_index=2` → `round2/` | Unit |
| T12 | Failure path → meta.json `status="failed"`, partial output saved | Integration |
| T13 | CancelledError → re-raised, `status="cancelled"` | Integration |
| T14 | `implementation_report.md` created (LLM or fallback) | Integration |
| T15 | Streaming via `interactive.stream_token_batches()` | Integration |
| T16 | `ToolExecutionResult` has `result` + `context_updates` (NOT `success`/`output`) | Unit |
| T17 | `--full` still routes to topology runner, `children/` present | Integration |
| T18 | Heavy-mode prompt byte-identical after template edits | Snapshot |
| T19 | `_resolve_auto_leaf` 3-tier: caller → env → default | Unit |
| T20 | `inferencer_args.json` secrets redacted | Unit |
| E2E | Real `/task "what does this repo do?"` — artifacts present, response sensible | Smoke |

---

## 5. Verification

```bash
pytest test/openteam/resources/tools/task/test_simple_mode.py -v
cd /Users/tchen7/MyProjects/CoreProjects/OpenStartup
python -m openteam.server.resources.tools.task "what does this repo do?" --simple
python -m openteam.server.resources.tools.task "what does this repo do?" --full
```
