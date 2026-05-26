# Integrated Plan — Task Simple Mode (Default for `/task`)

> **Date:** 2026-05-19
> **Status:** Integrated single-file consolidation (supersedes the 3-file
> split: `INTEGRATED_TASK_SIMPLE_MODE.md`,
> `INTEGRATED_TASK_SIMPLE_MODE_DESIGN.md`,
> `INTEGRATED_TASK_SIMPLE_MODE_TEMPLATE.md`).
> **Scope:** Ship `/task --simple` and make it the default, integrating
> the best of both predecessor plans, grounded in direct codebase
> inspection.
> **Primary codebases:**
>  - `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/server/resources/tools/task/` (executor + tool.json + cli.py + topologies/)
>  - `/Users/tchen7/MyProjects/CoreProjects/AgentFoundation/src/agent_foundation/` (leaf inferencers + prompt templates)

---

## Table of contents

- [0. Source plans summary](#0-source-plans-summary)
- [1. Goal](#1-goal)
- [2. Verified facts about the current state](#2-verified-facts-about-the-current-state-ground-truth-from-disk)
- [3. Workspace layout](#3-workspace-layout-no-new-helper-needed)
- [4. Tool.json changes](#4-tooljson-changes)
- [5. The simple-mode executor](#5-the-simple-mode-executor)
- [6. Template edit](#6-template-edit-implementationmaininitialjinja2)
- [7. Concrete code-change list](#7-concrete-code-change-list-single-canonical-list)
- [8. Migration (three phases, no flag day)](#8-migration-three-phases-no-flag-day)
- [9. Test plan](#9-test-plan)
- [10. Risks & mitigations](#10-risks--mitigations)
- [11. Decision log](#11-decision-log-merged-from-both-predecessor-plans)
- [12. Open questions](#12-open-questions-the-ones-that-genuinely-remain)
- [13. Definition of done](#13-definition-of-done)
- [14. Cross-references](#14-cross-references)

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

## 6. Template edit (`implementation/main/initial.jinja2`)

### 6.1 Pre-flight grep (verified zero collisions)

| Pattern | Hits outside `_dev/_plan/` | Decision |
|---------|---------------------------|----------|
| `has_approved_plan` | **0** | Safe to introduce. |
| `task_posture` | **0** | Not used; we don't introduce it (avoided by §0.2). |
| `APPROVED PLAN` | **1** (line 47 of the template) | The single surgery site. |
| `round_index` | **3 hits in templates** (initial:55, followup:25, review:22) | We touch only `initial.jinja2`'s use. The other two stay as-is (they're rendered in heavy/topology contexts where `round_index ≥ 1`). |

### 6.2 The two surgical edits

**Edit A — line 47–49 ("APPROVED PLAN" block).** Wrap in a conditional so
simple-mode (which OMITS `has_approved_plan`) gets adhoc wording; heavy
mode (which sets `has_approved_plan=True`) gets today's behavior.

**BEFORE (verbatim from disk):**
```jinja2
## NOTES (on agent behavior):
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
```

**AFTER:**
```jinja2
## NOTES (on agent behavior):
{% if has_approved_plan is defined and has_approved_plan %}
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
{% else %}
- You are starting from a single user request without a pre-approved plan.
  * Read minimally to ground yourself in the relevant code (file headers, target functions, immediate call sites). DO NOT investigate the entire codebase.
  * Then act decisively on the request. If the request is ambiguous, pick the most plausible interpretation, state it briefly in your `<Response>`, and proceed.
{% endif %}
```

**Edit B — line 55 (the `round{{ round_index }}/` path components).** Collapse the round directory segment when `round_index` is falsy (0 or absent), so simple mode produces clean paths.

**BEFORE (verbatim from disk):**
```jinja2
- If the user request involves/requires testing/benchmarking that produces output artifacts (e.g., testing details, benchmark  metrics), save them alongside `{{ output_path }}` under `tests/round{{ round_index }}/` and `benchmarks/round{{ round_index }}/`,
```

**AFTER:**
```jinja2
- If the user request involves/requires testing/benchmarking that produces output artifacts (e.g., testing details, benchmark  metrics), save them alongside `{{ output_path }}` under `tests/{% if round_index %}round{{ round_index }}/{% endif %}` and `benchmarks/{% if round_index %}round{{ round_index }}/{% endif %}`,
```

### 6.3 Caller-side change to preserve byte-identical heavy-mode behavior

After Edit A, **existing topology callers must pass `has_approved_plan=True`** when they render `initial.jinja2` for an implementation-child node that follows a planning node — otherwise the heavy-mode prompt would silently change.

The change is **one line** added wherever the topology runner constructs the render context for an implementation-child node. Locations to update (verified by subagent grep + my read of `multi_flow_inferencer.py:485, 702, 806, 854, 1219`):

- `agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/multi_flow_inferencer.py`
  — wherever it renders `implementation/main/initial.jinja2`, add `"has_approved_plan": True` to the `feed` dict.

A safer approach: add `has_approved_plan: True` as a default in the `multi_flow_inferencer`'s feed-construction helper, so every call that doesn't explicitly override it gets the heavy-mode behavior. Single point of change.

### 6.4 Why this is elegant (not hacky)

| Concern | Resolution |
|---------|------------|
| Drift between simple and heavy templates | None — single source of truth. |
| Future template improvements | Both modes benefit automatically. |
| Discoverability | Both branches live in one file, side-by-side. |
| Test surface | One template, two branches; 2 unit tests pin each. |
| New variant slot directories | **Zero.** No `_variables/task_posture/`, no parallel folders. |
| New template files | **Zero.** |
| Pattern consistency | Mirrors the existing `{% if employee is defined %}` guard. |

---

## 7. Concrete code-change list (single canonical list)

| # | File | Change |
|---|------|--------|
| 1 | `OpenStartup/src/openteam/server/resources/tools/task/tool.json` | Add `--simple` (default `false` in Phase 1, `true` in Phase 2). Add `--leaf-inferencer` (default `"auto"`). Flip `--full`'s default `true→false` in Phase 2. Update description text to mention simple mode. |
| 2 | `AgentFoundation/src/agent_foundation/resources/tools/task/tool.json` | Add the **same two new parameters** (`--simple`, `--leaf-inferencer`) and flip `--full`'s default per the phase plan. Do NOT attempt to re-mirror the full OpenStartup schema — the two files already have legitimate divergence (different aliases, different dual-agent params, etc.). Scope of this change is strictly additive: the two new flags + the one default-value flip. |
| 3 | `OpenStartup/src/openteam/server/resources/tools/task/executor.py` | Rewrite `_derive_mode_from_flags` per §4.3. Add `_run_simple_mode`, `_render_simple_prompt`, `_init_node_subdirs`, `_resolve_auto_leaf`, `_persist_inferencer_args`, `_safe_parse_output`, `_ensure_implementation_report`, `_write_meta` (per §5). Update `execute()` to dispatch on mode (§5.1) and to emit the Phase-1 deprecation warning when no explicit mode flag was supplied. **Heavy-path `_init_node_subdirs` call is deferred:** in Phase 1, do NOT call `_init_node_subdirs(create_children_dir=True)` from heavy-mode code paths — leave today's lazy-create behavior intact (zero blast radius). In Phase 2 (after simple mode has burned in), consider hoisting the pre-create call into heavy mode for layout consistency; track as a follow-up issue. |
| 4 | `OpenStartup/src/openteam/server/resources/tools/task/cli.py` | Add `--simple` and `--leaf-inferencer` argparse entries that mirror tool.json. Wire `explicit_simple` / `explicit_full` detection through to executor's `session_context` for the conflict-detection path. |
| 5 | `AgentFoundation/src/agent_foundation/common/jobs/__init__.py` | NEW (empty for now; reused by future SOP chapter). |
| 6 | `AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py` | NEW per §3.4. |
| 7 | `AgentFoundation/src/agent_foundation/resources/prompt_templates/implementation/main/initial.jinja2` | Two surgical edits per §6.2 (Edit A + Edit B). **No new template file.** |
| 8 | `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/multi_flow_inferencer.py` | Add `"has_approved_plan": True` to the `feed` dict at every callsite that renders `implementation/main/initial.jinja2` — OR add it once as a default in the feed-construction helper (preferred). Preserves byte-identical heavy-mode output after edit #7. |
| 9 | `OpenStartup/src/openteam/server/services/tool_dispatcher.py` (or equiv) | **Surface `_explicit_<flag>` for each mode flag.** The dispatcher already parses the raw user input (slash command string or argparse tokens) before applying schema defaults. Concrete mechanism: before merging schema defaults, snapshot which flag names appeared in the raw token list; emit them as a set `session_context["_explicit_flags"] = {"simple", "full", ...}`. Executor reads `explicit_simple = "simple" in session_context.get("_explicit_flags", set())` (and similarly for `full`, `plan`, `confirm`, `execute`). Single ~15 LoC change; one new helper `_extract_explicit_flag_names(raw_args, tool_schema)`. If the dispatcher doesn't centralize argv parsing today (i.e., schema-defaults are applied inline during parsing with no retained raw form), Phase 0 of this task adds the retention. Integration test T40 enforces end-to-end. |
| 10 | `tests/openteam/tools/task/test_simple_mode.py` | NEW per §9. |
| 11 | `tests/agent_foundation/.../prompt_templates/test_implementation_initial.py` | NEW per §9 — pins both `has_approved_plan` branches and `round_index` collapse. |

**Total NEW files: 4** (leaf_factory + 3 test files).
**Total MODIFIED files: 7.**
**Total NEW template files: 0.** (Reuse `implementation/main/initial.jinja2`.)
**Total NEW workspace allocator helpers: 0.** (Reuse `_shared/workspace_allocator.py`.)

---

## 8. Migration (three phases, no flag day)

| Phase | Duration | `--simple` default | `--full` default | Behavior |
|-------|----------|--------------------|------------------|----------|
| **Phase 1** | One release | `false` | `true` | Identical to today. Both flags resolvable; conflict raises ValueError. Deprecation warning printed if `not (explicit_simple or explicit_full or explicit_plan or explicit_confirm or explicit_execute)` — i.e., the user typed NO mode flag and is silently relying on the implicit `--full` default: "task default mode will change from --full to --simple in release vX.Y; pass --full explicitly to suppress this warning." The check uses `explicit_*` (dispatcher-supplied) NOT `arguments.get("full")`, because `arguments["full"]` is always True in Phase 1 due to the schema default. |
| **Phase 2** | One release | `true` | `false` | New default. Users who relied on the old heavy default must add `--full` explicitly. Deprecation warning gone. |
| **Phase 3** | Steady state | `true` | `false` | Stable. Feature flag and `_default_mode_is_simple()` helper removed; defaults baked into tool.json. |

**Per-call escape hatch:** env `OPENTEAM_TASK_DEFAULT_MODE=simple|full` overrides
the schema default. Used by ops / CI to lock behavior independently of
release cadence.

**SOP audit:** any existing SOP file that says `/task <request>` and
genuinely needs the heavy path must be updated to `/task --full <request>`.
Audit checklist (chapter 8 §5 in the SOP plan) tracks this.

---

## 9. Test plan

| # | Test | Type | Why it matters |
|---|------|------|----------------|
| **Mode resolution** | | | |
| T1 | `_derive_mode_from_flags({"plan":True}, ...)` → `"plan"` | Unit | Phase-selector precedence (§4.2). |
| T2 | `_derive_mode_from_flags({"confirm":True}, ...)` → `"confirm"` | Unit | Same. |
| T3 | `_derive_mode_from_flags({"execute":True}, ...)` → `"execute"` | Unit | Same. |
| T4 | `_derive_mode_from_flags({}, explicit_simple=True, explicit_full=True)` → ValueError | Unit | Conflict detection. |
| T5 | `_derive_mode_from_flags({"full":True}, explicit_full=True)` → `"full"` | Unit | Explicit `--full` wins over default. |
| T6 | Phase 1: `_derive_mode_from_flags({}, ...)` → `"full"` (feature flag off) | Unit | Backward compat in Phase 1. |
| T7 | Phase 2: `_derive_mode_from_flags({}, ...)` → `"simple"` (feature flag on) | Unit | New default in Phase 2. |
| **Workspace** | | | |
| T8 | `_run_simple_mode` creates workspace at `<runtime_root>/tasks/task/task_<ts>_<8hex>/` with the 5 standard subdirs and NO `children/` | Integration | §3.1. |
| T9 | `_init_node_subdirs(ws, create_children_dir=True)` creates `children/`; with `False` does not | Unit | §3.3. |
| T10 | Path regex match: `tasks/task/task_\d{8}_\d{6}_[0-9a-f]{8}` | Unit | Naming convention. |
| T11 | `_resolve_workspace` honors `working_dir` in session_context for `--resume` | Unit | Preserves existing behavior (§2.4). |
| T12 | When `session_root` is set in context, workspace lands under `<session_root>/tasks/` (server-affiliated) | Unit | Path-B routing. |
| **Leaf factory** | | | |
| T13 | `make_leaf_inferencer("claude_code_cli", cache_dir=…)` returns `ClaudeCodeCliInferencer` with `model_name="sonnet"` and `cache_folder=str(cache_dir)` | Unit | §3.4. |
| T14 | `make_leaf_inferencer("rovodev_cli", cache_dir=…)` returns `RovoDevCliInferencer` with `model_id=""`, `yolo=True`, `cache_folder=str(cache_dir)` | Unit | §3.4. |
| T15 | `make_leaf_inferencer("claude_api")` returns `ClaudeApiInferencer` with `cache_dir`/`target_path` ignored | Unit | API leaves correctly no-op these. |
| T16 | `make_leaf_inferencer("unknown")` raises ValueError | Unit | Defensive. |
| T17 | `make_leaf_inferencer(...)` does NOT pass `session_log_dir` kwarg (would crash) | Unit | Corrects both predecessor plans' wrong assumption. |
| **Auto-leaf** | | | |
| T18 | `_resolve_auto_leaf({"calling_inferencer_class": "ClaudeCodeCliInferencer"})` → `"claude_code_cli"` | Unit | Tier 1 of §4.5. |
| T19 | `_resolve_auto_leaf({})` with env `OPENTEAM_TASK_DEFAULT_LEAF=rovodev_cli` → `"rovodev_cli"` | Unit | Tier 2. |
| T20 | `_resolve_auto_leaf({})` with no env → `"claude_code_cli"` | Unit | Tier 3 (hardcoded last resort). |
| **Template — required-variable contract** | | | |
| T21 | Render `initial.jinja2` with simple-mode kwargs (no `has_approved_plan`, `round_index=0`) → succeeds, no Jinja2 UndefinedError | Unit | All required vars supplied. |
| T22 | Output contains "starting from a single user request without a pre-approved plan" (adhoc branch chosen) | Unit | Edit A §6.2 simple-mode branch. |
| T23 | Output does NOT contain "APPROVED PLAN" in simple-mode render | Unit | Anti-regression. |
| T24 | Output contains "tests/" and "benchmarks/" (no `round0/` segment) | Unit | Edit B §6.2 collapse with falsy round_index. |
| T25 | Render with `has_approved_plan=True` → output contains "APPROVED PLAN", no adhoc wording | Unit | Heavy-mode branch preserved. |
| T26 | Render with `round_index=2` → output contains "tests/round2/" and "benchmarks/round2/" | Unit | Heavy-mode path preserved. |
| **Executor — success path** | | | |
| T27 | `/task --simple "hello"` (mock leaf) writes `outputs/raw_response.txt`, `outputs/parsed_output.json`, `outputs/implementation_report.md`, `artifacts/meta.json` (status=completed) | Integration | §5.2 success path. |
| T28 | `artifacts/inferencer_args.json` has REDACTED entries for any field whose name matches `_REDACT_FIELDS` | Unit | §5.5 redaction. |
| T29 | `artifacts/input_prompt.md` is byte-identical to what was passed to `ainfer_streaming` | Integration | §5.2 step "write input_prompt.md". |
| T30 | Streaming chunks accumulate into `outputs/raw_response.txt` (no chunk lost) | Integration | §5.2 streaming loop. |
| **Executor — failure path** | | | |
| T31 | Leaf raises `RuntimeError` mid-stream → `meta.json` status=`"failed"`, error message captured, partial `raw_response.txt` written, executor returns `success=False` | Integration | §5.2 try/finally. |
| T32 | `asyncio.CancelledError` mid-stream → re-raised; `meta.json` status=`"cancelled"`, partial outputs preserved | Integration | §5.2 cancellation handling. |
| T33 | `parse_output` raises → `_safe_parse_output` falls back to `<Response>` extraction | Unit | §5.6 fallback. |
| T34 | No `<Response>` tags in raw → `_safe_parse_output` returns `{"response": <raw>}` | Unit | Universal fallback. |
| **Fallback report** | | | |
| T35 | Claude Code leaf wrote `implementation_report.md` → `_ensure_implementation_report` is no-op | Unit | §5.4. |
| T36 | claude_api leaf (no file tools) → `_ensure_implementation_report` writes `<Response>` body to `implementation_report.md` | Unit | §5.4 fallback. |
| **Heavy mode preserved** | | | |
| T37 | `/task --full "fix"` still routes to existing topology runner; workspace contains `children/` | Integration | §5.1 dispatch + #3 in code-change list. |
| T38 | Heavy-mode prompt rendered via `multi_flow_inferencer` is byte-identical before/after edits #7+#8 | Snapshot test | Anti-regression. |
| **CLI parity** | | | |
| T39 | Standalone CLI `task --simple "hi"` produces same workspace pattern + artifacts as in-conversation `/task --simple "hi"` | Integration | cli.py parity. |
| T40 | Standalone CLI `task --simple --full "x"` exits with non-zero status and error message about conflict | Unit | Conflict surfaces at CLI layer too. |
| **End-to-end smoke** | | | |
| T41 | Real `/task "what does this repo do?"` against Claude Code CLI (model=sonnet) → all 4 expected files in `outputs/` and `artifacts/`, response sensible, duration < 90s | E2E (gated on `ENABLE_E2E_LLM_TESTS=1`) | Sanity. |

**Coverage target:** ≥ 85% on new code in `executor.py` simple-mode functions + `leaf_factory.py`.

---

## 10. Risks & mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Behavior change in Phase 2: existing scripts/SOPs that relied on implicit heavy mode silently get simple-mode | Med | High | One-release deprecation warning + env var escape hatch + SOP audit checklist. |
| R2 | The template edit changes heavy-mode prompt content for callers that don't pass `has_approved_plan=True` | Low | High | Default `has_approved_plan: True` in `multi_flow_inferencer`'s feed-construction helper (single-point change #8). Snapshot test T38 enforces byte-identical heavy-mode output. |
| R3 | Leaf inferencer ctor kwarg mismatch (`session_log_dir`) crashes simple mode | High if not corrected | High | Already corrected in §3.4: factory signature excludes `session_log_dir`. T17 enforces. |
| R4 | `claude_code_cli` default model `"sonnet"` may not match session model config | Low | Low | `--model` flag still works; auto-leaf can be overridden. |
| R5 | API leaf has no file tools → no `implementation_report.md` from LLM | Med | Low | `_ensure_implementation_report` fallback (§5.4). |
| R6 | Failure path leaves orphan workspace dirs cluttering `_runtime/tasks/task/` | Med | Low | `meta.json` always present (try/finally) so cleanup jobs can identify+purge by status & age. |
| R7 | Streaming inferencer never yields (hang) | Low | Med | `--timeout` flag deferred to chapter 3 (background-job); for foreground simple mode, the upstream caller's cancellation semantics apply (`asyncio.CancelledError` handled in T32). |
| R8 | Concurrent simple-mode runs collide on the same workspace path | Very low | Low | `uuid4().hex[:8]` collision probability is negligible; `mkdir(exist_ok=True)` is idempotent; the `_TS` component provides additional separation. |
| R9 | The `multi_flow_inferencer` feed-construction has multiple call sites for `implementation/main/initial.jinja2` and we miss one | Med | High | Step #8 in code-change list says "preferred: add default in feed-construction helper, single point". The dispatch-by-helper approach is the safe form. If multi_flow_inferencer doesn't have such a helper today, ADD one before flipping the template — single-PR refactor. |
| R10 | The `_explicit_simple` / `_explicit_full` plumbing required from the dispatcher is overlooked | Med | Med | Step #9 in code-change list. Add an integration test that injects both flags explicitly via the dispatcher and asserts ValueError surfaces. T40 covers the CLI side. |

---

## 11. Decision log (merged from both predecessor plans)

| # | Decision | Source | Rationale |
|---|----------|--------|-----------|
| DL1 | Reuse `implementation/main/initial.jinja2`; do NOT create a new template | rovodev plan §3.3 (correct direction) | Avoids template drift; inherits 8 production-grade contracts; minimal diff. |
| DL2 | Do NOT introduce a `_variables/task_posture/` variant slot | New | Variant slots are for content that differs substantively (e.g., aggregation vs default). For an on/off prose toggle, an inline `{% if %}` is the right level. |
| DL3 | Default leaf inferencer = `"auto"` resolving to caller's class, then env, then `claude_code_cli` | New (merging claude_code's `claude_code_cli` default + rovodev's `rovodev_cli` default) | Neither predecessor had a defensible rationale for hardcoding one over the other. Auto-pick respects the parent agent's choice. |
| DL4 | Reuse `_shared/workspace_allocator.allocate_tool_workspace("task", base_dir=...)`; do NOT write a new `task/workspace.py` | New (both predecessor plans missed this) | The existing helper produces the exact path pattern needed. Reuse > create. |
| DL5 | Add `_init_node_subdirs(workspace, create_children_dir=False)` as a tiny new helper (~10 lines) | New | The one thing the existing allocator doesn't do (it allocates the root dir only). Keep in `executor.py` or hoist to `_shared/workspace_allocator.py`. |
| DL6 | try/finally always writes outputs + meta with status; never lose partial work | claude_code plan §3.3 (correct) | Production resilience. |
| DL7 | `_REDACT_FIELDS = {"api_key","token","secret","password","auth_token"}` for `inferencer_args.json` | claude_code plan §3.7 (correct) | Security. |
| DL8 | Three-phase migration: deprecation warning → default flip → cleanup | Both plans | Standard staged rollout; users get one release to adjust. |
| DL9 | `--plan` / `--confirm` / `--execute` are phase selectors that override `--simple` | New (neither plan addressed) | These flags are categorically different from simple/full; they pick specialized planning sub-topologies. They should never silently disappear under the new default. |
| DL10 | `has_approved_plan=True` defaults at the multi_flow_inferencer's feed-construction helper (one-line single-source change) | New | Preserves byte-identical heavy-mode behavior with the smallest possible blast radius. |
| DL11 | Leaf factory does NOT accept `session_log_dir` kwarg | New (corrects both plans) | Verified by direct file read; passing it would crash on construction. |
| DL12 | Simple mode reuses `_resolve_workspace` (not `_allocate_workspace` directly) | New | Preserves `working_dir` honoring and `--resume` semantics. |

---

## 12. Open questions (the ones that genuinely remain)

1. **Should simple mode support multi-turn?** Both predecessor plans
   said no. Decision retained: simple mode is one-shot. Multi-turn is
   the conversational inferencer's job (it can call `/task` repeatedly
   with accumulating context).
2. **Where does `_init_node_subdirs` live — in `executor.py` or
   `_shared/workspace_allocator.py`?** Recommendation: start in
   `executor.py`; hoist to `_shared` when a second tool needs it.
   YAGNI applies.
3. **Should `--leaf-inferencer auto` ever pick API leaves?** No — API
   leaves cannot run file-tool workflows, and most task requests want
   filesystem access. Tier 1 (caller-class) is what surfaces API leaves
   if the parent agent is itself an API leaf (rare).
4. **What if the `multi_flow_inferencer` has no centralized feed-construction
   helper?** Then add one as part of step #8. Pre-PR investigation
   (Phase B owner) should `grep -rn 'implementation/main/initial' AgentFoundation/`
   and audit each call site.

---

## 13. Definition of done

This integrated plan is "done" when:

1. Test plan §9 fully passes (≥ 85% coverage on new code).
2. `/task "hello world"` completes in < 60s via the Phase-2 default
   simple mode, producing the expected 4 output files + 3 artifact files.
3. `/task --full "hello world"` still produces today's heavyweight
   topology workspace with `children/`, with snapshot-identical prompt
   rendering for the implementation-child node (T38).
4. Phase-1 deprecation warning fires when no explicit mode flag is set,
   and is silent when `--full` is passed explicitly.
5. SOP audit checklist has identified every `/task <…>` callsite in
   existing SOPs and explicitly tagged it `--simple` or `--full`.
6. Documentation:
   - `_dev/_docs/task_simple_mode.md` — user guide
   - Inline docstrings on all new functions in `executor.py` and
     `leaf_factory.py`
7. A changelog entry for each phase transition.

---

## 14. Cross-references

This integrated plan supersedes:
- `conversational_inferencer_sop_integration/claude_code/02_task_simple_mode.md`
- `conversational_inferencer_sop_integration/rovodev/01_task_simple_mode.md`
- The three-file split that previously lived alongside this file:
  `INTEGRATED_TASK_SIMPLE_MODE.md`, `INTEGRATED_TASK_SIMPLE_MODE_DESIGN.md`,
  `INTEGRATED_TASK_SIMPLE_MODE_TEMPLATE.md` (now consolidated into this
  single file for easier review and reduced indirection).

It is consumed by:
- The Background Jobs chapter (chapter 3 in both predecessor plans) —
  `/background-job task ...` will invoke simple mode by default.
- The SOP subprocess runner chapter (chapter 5 in both) — the SOP runner
  uses `make_leaf_inferencer` from `common/jobs/leaf_factory.py` (file #6
  in §7), exactly as both plans assume.

---

*End of consolidated integrated plan.*
