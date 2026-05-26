# Integrated Plan — Task Simple Mode (Default for `/task`)

> **Date:** 2026-05-19
> **Status:** Integrated (replaces both `claude_code/02_task_simple_mode.md` and `rovodev/01_task_simple_mode.md`)
> **Scope:** Ship `/task --simple` and make it the default, integrating the best of both predecessor plans, grounded in direct codebase inspection.
> **Primary codebases:**
>  - `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/server/resources/tools/task/` (executor + tool.json + cli.py + topologies/)
>  - `/Users/tchen7/MyProjects/CoreProjects/AgentFoundation/src/agent_foundation/` (leaf inferencers + prompt templates)

---

## 0. Source plans summary

| Aspect | `claude_code/02_task_simple_mode.md` | `rovodev/01_task_simple_mode.md` | Winner / Notes |
|--------|--------------------------------------|----------------------------------|----------------|
| Default leaf inferencer | `claude_code_cli` | `rovodev_cli` | **No default — use a 3-tier auto-pick** (§4.5 below). Both plans had unsupported opinions. |
| Workspace convention | Reuse existing `tasks/task/task_<ts>_<8hex>/`, 5-folder, no `children/` | Same | Tie — both correct. |
| Prompt template | Brand-new minimal `simple_initial.jinja2` (in `resources/tools/task/templates/`) | Reuse `implementation/main/initial.jinja2` + add 2 `{% if %}` guards | **Rovodev wins on direction** (reuse > new), but its specifics need correction (see §0.1). |
| Workspace allocator | Propose new `task/workspace.py` with `allocate_task_node_workspace` | Same | **Both plans MISS that this is already implemented** — the existing `_shared/workspace_allocator.py::allocate_tool_workspace("task", base_dir=…)` produces the EXACT path pattern needed. Reuse it; don't write a new helper. (§3.2 below) |
| Leaf factory | `common/jobs/leaf_factory.py` with `LEAF_CLASS_NAME_MAP` + `make_leaf_inferencer` | Same | Tie — both correct. |
| `ctor kwarg` `session_log_dir` for CLI leaves | Both plans assume it exists | Both plans assume it exists | **Both WRONG** — verified by subagent: `ClaudeCodeCliInferencer` / `RovoDevCliInferencer` do NOT have a `session_log_dir=` kwarg. Their session log path is derived from `cache_folder` or the parent inferencer's wiring. We must NOT pass `session_log_dir=` to ctors (§3.4 below). |
| Error handling in executor | try/finally that always writes outputs + meta with status | Not present | **Claude_code wins** — robust failure handling is a real production requirement. Adopted. |
| Secrets filter | `_REDACT_FIELDS = {"api_key","token","secret","password"}` | Not present | **Claude_code wins** — adopt. |
| Three-phase migration (flag flip) | Yes | Yes | Tie — adopted. |
| Mode-resolution helper | Helper with conflict detection | Same | Tie — adopted. |
| Decision log + open questions | Decision-log Q4/Q5 (why not flat? why not YAML topology?) | Open questions Q4/Q5 (why not fork? what about Phase A.3 refactor?) | **Both contribute** — merged into §11. |
| `--full` conflict with new mode | Both plans: ValueError | Both plans: ValueError | Tie. |
| Refactor existing `_allocate_workspace` | Both plans say "extract into shared `task/workspace.py`" | Same | **Both plans MISS** that the existing executor's `_allocate_workspace` already delegates to `_shared/workspace_allocator.allocate_tool_workspace`. NO extraction needed — the shared helper already exists, lives at the right level, and produces the right paths. (§3.2) |
| `--leaf-inferencer` flag with `choices: [...]` | Yes | Yes | Adopted. |

### 0.1 Where the rovodev plan's `implementation/main/initial.jinja2` reuse direction needed correction

The rovodev plan proposed wrapping the line-48 "APPROVED PLAN" block in
`{% if has_approved_plan %}…{% else %}…{% endif %}` and collapsing the
line-56 `round{{ round_index }}/` path component. **Both edits remain in
the integrated plan.** But the rovodev plan was unaware of two things:

1. **The template references `{{ output_path }}` and `{{ round_index }}` as
   required (unguarded).** So the simple-mode executor MUST pass both,
   confirmed by subagent (Variable Slots investigation). The integrated plan
   makes this explicit.
2. **The template references `{{ input }}`, `{{ task_preamble }}`,
   `{{ task_instructions }}` and notes/instructions namespaces.** All required.
   The integrated executor populates them explicitly.

### 0.2 Where the claude_code plan's "new template" direction is wrong

Creating a parallel `simple_initial.jinja2` is **wrong** for the same reason
inventing a new `_jobs/` workspace was wrong: it synthesizes parallel
infrastructure when the codebase already has a battle-tested version, and
it drifts away from production over time. The claude_code plan **silently
drops** the eight production-grade contracts of `implementation/main/initial.jinja2`:

1. Mandatory `<Response>` tag contract (downstream parsers depend on it)
2. `{{ output_path }}` discipline (writes structured `implementation_report.md`)
3. `{{ employee }}` identity injection (existing optional guard)
4. `{{ task_preamble }}` / `{{ task_instructions }}` flavored slots
5. Shared `notes.local_search_efficiency`, `instructions.behavior.file_reading_fallback`
6. Numeric-metrics testing/benchmarking discipline
7. `tests/round{{ round_index }}/` artifact layout (future-proof for review/refine)
8. Production-tuned behavioral guardrails (validate_changes warnings, `<Response>`-fallback recovery)

→ **Integrated plan reuses the existing template** with the minimal additive guards from §0.1.

---

## 1. Goal

Make `/task` **cheap, fast, transparent, and predictable by default**. A
single `/task "<request>"` runs as ONE prompt against ONE leaf inferencer
(default: auto-picked per §4.5; today's preferred default is
`claude_code_cli` because it ships with file-system + tool-use access and
is the most-used Atlassian-side CLI in the conversational inferencer's
own loop).

**Heavy mode** (today's `breakdown-multiflow-plan-then-implement` topology)
becomes opt-in via existing `--full`, `--confirm`, `--plan`, `--execute`
flags. Behavior of those flags is **unchanged** — only the **default** flips.

---

## 2. Verified facts about the current state (ground truth from disk)

These are NOT plan assertions; these are direct file reads. Both
predecessor plans had drift; the integrated plan is rebuilt on these
facts.

### 2.1 The current `/task` tool.json (lines 1–80 verbatim, abridged)

```json
{
  "name": "task",
  "executor": "openteam.server.resources.tools.task.executor:execute",
  "parameters": [
    {"name": "request", "type": "string", "required": true, "positional": true, ...},
    {"name": "--plan",    "type": "flag", ...},
    {"name": "--execute", "type": "flag", "description": "Skip planning; requires --initial-plan."},
    {"name": "--full",    "type": "flag", "default": true, "description": "Plan then implement (default)."},
    {"name": "--confirm", "type": "flag", ...},
    {"name": "--agent-config", "type": "string", "default": "breakdown-multiflow-plan-then-implement", ...},
    {"name": "--override", "type": "string", "repeatable": true, ...},
    {"name": "--model", ...},
    {"name": "--no-dual", ...},
    {"name": "--analysis", ...},
    {"name": "--multi-iter", ...},
    {"name": "--max-iterations", "type": "int", "default": 3},
    {"name": "--resume", "type": "path", ...},
    {"name": "--in-place", "type": "flag", "default": true},
    {"name": "--copy-workspace", "type": "flag", ...},
    {"name": "--initial-plan", "type": "path", ...}
  ]
}
```

Note: `--full` is currently `default: true`. There is no `--simple`,
no `--leaf-inferencer`.

### 2.2 The current `_derive_mode_from_flags` (executor.py:140)

```python
def _derive_mode_from_flags(arguments: dict) -> Optional[str]:
    """Map mutually-exclusive --plan/--execute/--full/--confirm flags to a mode string."""
    for f, m in (("plan", "plan"), ("execute", "execute"), ("full", "full"), ("confirm", "confirm")):
        if arguments.get(f):
            return m
    return None
```

Returns `None` when none of the explicit mode flags are set — but
since `--full` is `default: true`, in practice the dispatcher sees
`{"full": True}` and `_derive_mode_from_flags` returns `"full"`.

### 2.3 The current `_allocate_workspace` (executor.py:148)

```python
def _allocate_workspace(task_id: str, session_context: Optional[dict] = None) -> Path:
    from openteam.server.resources.tools._shared.workspace_allocator import allocate_tool_workspace
    sc = session_context or {}
    session_root_str = sc.get("session_root", "")
    if session_root_str:
        base = Path(session_root_str) / "tasks"
        base.mkdir(parents=True, exist_ok=True)
        return allocate_tool_workspace("task", base_dir=base)
    return allocate_tool_workspace("task", base_dir=None)
```

And `allocate_tool_workspace("task", base_dir=None)` produces:
`<find_runtime_root()>/tasks/task/task_<TS>_<uuid8>/`

with `find_runtime_root()` doing a 4-tier fallback (env →
walk-up-from-src → walk-up-from-cwd → `~/.openteam/_runtime`).

**This is exactly the path pattern we want for simple mode. Zero
changes to the allocator. Zero new helper module.**

### 2.4 `_resolve_workspace` honors dispatcher-provided `working_dir`

```python
def _resolve_workspace(session_context: Optional[dict], task_id: str) -> Path:
    sc = session_context or {}
    candidate = sc.get("working_dir", "")
    if candidate:
        posix = Path(candidate).as_posix()
        if "/tasks/" in posix or "/_runtime/" in posix:
            ws = Path(candidate); ws.mkdir(parents=True, exist_ok=True); return ws
    return _allocate_workspace(task_id, session_context)
```

Simple mode **must** call `_resolve_workspace` (not `_allocate_workspace`
directly) so dispatcher pre-allocation and `--resume` still work.

### 2.5 `implementation/main/initial.jinja2` — variables it requires

Verified by subagent + my own direct read:

| Variable | Required? | Guarded today? | Notes |
|----------|-----------|----------------|-------|
| `employee` | Optional | `{% if employee is defined %}` | Already safe. |
| `task_preamble` | **Required** | No | Must pass. The slot loads `_variables/task_preamble/default.jinja2` (which itself optionally references `session_root_path`, `workflow_target_path`, `docs_path`). |
| `input` | **Required** | No | The user's request. |
| `task_instructions` | Optional | `{% if task_instructions %}` | Block omitted if falsy. |
| `output_path` | **Required** | No | Used in the "Output Requirements" section as the file the LLM writes its report to. |
| `instructions.behavior.file_reading_fallback` | **Required** | No | Shared instructions namespace. |
| `notes.local_search_efficiency` | **Required** | No | Shared notes namespace. |
| `round_index` | **Required (today)** | No | Used in path strings `tests/round{{ round_index }}/`. **The integrated plan adds the `{% if round_index %}` guard** so simple-mode can pass `0` (or omit) and the path collapses cleanly. |
| `has_approved_plan` | **DOES NOT EXIST today** | — | **The integrated plan adds it** as an optional flag that wraps the line-48 "APPROVED PLAN" prose block. |

### 2.6 Leaf inferencer constructor reality (corrected from both plans)

Both predecessor plans claimed `ClaudeCodeCliInferencer` /
`RovoDevCliInferencer` accept a `session_log_dir=` kwarg. **They do not**
(subagent verification). What they DO accept:

| Inferencer | Real ctor kwargs (relevant to us) | Default model | `has_local_access` |
|------------|-----------------------------------|---------------|--------------------|
| `ClaudeCodeCliInferencer` | `target_path`, `model_name` (default `"sonnet"`), `cache_folder` (from `TerminalSessionTemplatedInferencerBase`) | `"sonnet"` | True (default) |
| `RovoDevCliInferencer` | `target_path`, `model_id`, `yolo`, `cache_folder` | (inferencer-specific default) | True |
| `ClaudeApiInferencer` | `model_id` | inferencer-specific | (no filesystem access) |
| `OpenAIApiInferencer` | `model_id` | inferencer-specific | (no filesystem access) |

The session log location for CLI inferencers is **derived from `cache_folder`** (or from the base-class session manager) — we do not pass it directly.

Implication: the leaf factory signature in §3.4 takes `cache_dir` only (not `session_log_dir`). The session log lands at `<workspace>/logs/session/` automatically because the inferencer base writes there relative to its working/cache dirs.

---

*Continued in `INTEGRATED_TASK_SIMPLE_MODE_DESIGN.md` (the design + implementation details). Split for reviewability.*
