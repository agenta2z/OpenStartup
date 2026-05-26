# Task Tool: Standalone CLI + YAML Modularization (INTEGRATED PLAN v3)

**Status**: Proposal (integrates Plan A `cached-hennessy.md` + Plan B `task-cli-unification.md`)
**Date**: 2026-05-08 (extended 2026-05-08 to cover sibling tools)
**Scope**:
  - `OpenStartup/src/openteam/server/resources/tools/task/` (PRIMARY — engine + CLI)
  - `OpenStartup/src/openteam/server/resources/tools/role_setup/` (gets shared CLI scaffold)
  - `OpenStartup/src/openteam/server/resources/tools/create_role/` (gets shared CLI scaffold)
**Estimated effort**: ~4 hours (3 hr for `task` + 1 hr for the two shims)

## 0a. Three-Tool Architecture Recap (verified 2026-05-08)

The engine layer is ALREADY unified:

| Tool | Engine | Verified evidence |
|---|---|---|
| `task` | (itself — provides `_run_topology`) | executor.py:304 |
| `role_setup` | calls `task._run_topology` | role_setup/executor.py:1199 + 1250; docstring "thin shim over /task"; `tool.json` has `"is_bridge": true` |
| `create_role` | calls `task._run_topology` | create_role/executor.py:536 + delegate; docstring "thin shim over /task"; `tool.json` has `"is_bridge": true` |

**Note on `is_bridge: true`** (caught by Plan A): the dispatcher uses this flag to
recognize delegating tools. Our CLI scaffold respects this — each bridge tool
gets its OWN CLI surface (preserving its domain-specific tool.json semantics)
rather than being collapsed into `task --agent-config /path/to/sibling.yaml`
(which would lose type-aware help, bypass domain pre-processing, and require
ad-hoc `--override template_extra_feed.X=Y` hacks).

What is NOT unified is the **CLI surface**:
- All three have their own `tool.json` (correct — different parameter shapes)
- None of them has a standalone CLI binary (the gap this plan closes)

The CLI scaffold we build for `task` is **directly reusable** as a generic
`tool.json`-driven CLI module that the other two tools can call with one line each.

---

## 0. What Changed From the Earlier Plans

This plan replaces both `cached-hennessy.md` and `task-cli-unification-and-plan-only-mode.md`.
It folds in:

- **Plan A's critical insight** (verified directly in executor.py lines 375-381 and PTI lines 350/351/405/408):
  *All four task modes (`--plan`, `--execute`, `--full`, `--confirm`) ARE ALREADY fully wired today.*
  `--plan` sets `enable_implementation=False` on PTI; `--execute` sets `enable_planning=False`;
  `--confirm` sets `enable_checkpoint_plan_review=True`. They are not aspirational — they work now.
- **Plan A's pragmatic dual-path approach** for plan-only execution.
- **Plan B's `tool.json`-driven argparse** (the single most important architectural call — prevents drift).
- **Plan B's discipline**: phasing, risk register, test plan, success criteria.
- **Plan B's YAML factoring** (`_planner.yaml` only — defer `_executor.yaml` since `--execute` already works without it).
- **Plan B's hygiene move**: relocate the YAML out of `test/` into `src/.../topologies/`.

Drops:
- ❌ Plan B's "Phase 3 — wire --plan / --execute / --confirm" (already wired; verified).
- ❌ Plan B's `_executor.yaml` extraction (not needed — `--execute` works via `enable_planning=False`).
- ❌ Plan A's manual argparse parser (drift hazard; replaced with Plan B's `tool.json`-driven generator).

---

## 1. Problem Statement

The task tool today has two real gaps:

### Gap 1 — No standalone CLI
The tool only runs through the slash-command dispatcher (`/task ...`) inside the
chat REPL or the FastAPI server. There is no `python -m ...` or `task-cli` you
can invoke from the terminal for one-shot runs, batch jobs, CI experiments, or
quick smoke tests.

### Gap 2 — Planner sub-tree isn't reusable
The planning portion of the canonical topology lives inline inside
`breakdown_multiflow_plan_then_implement.yaml` (lines 147–189). Anyone who
wants a clean plan-only run today has two unsatisfying options:

1. Run the full topology with `--plan` (sets `enable_implementation=False`) —
   works, but loads the executor sub-tree into memory and complicates
   reasoning about the run shape.
2. Hand-craft an inline JSON spec via `--agent-config '{"_target_":...}'` —
   ad-hoc, not reproducible.

A clean third option (`--agent-config breakdown_multiflow_plan` → loads a
self-contained planner topology) doesn't exist yet but trivially can.

### Non-gaps
- **Mode flags ARE already wired**: `--plan`, `--execute`, `--confirm`, and
  `--initial-plan` all reach PTI's native fields today. No re-wiring needed.
- **`_import_` mechanism exists**: `RichPythonUtils/.../config_utils/_instantiate.py`
  lines 203-251. Composing YAMLs is supported.
- **`tool.json` schema is complete**: All flags we need are already declared.

---

## 2. Design Decisions

### Decision 1 — CLI parser is GENERATED from `tool.json`

This is the single most important call. **Manual argparse mirrors `tool.json`
on day 1, drifts by month 6, and silently breaks by year 1.** Generating the
parser at runtime from `tool.json` makes drift impossible by construction.

```python
# task/cli.py — single source of truth: tool.json
def _build_parser_from_tool_json() -> argparse.ArgumentParser:
    spec = json.loads(_TOOL_JSON.read_text())
    p = argparse.ArgumentParser(
        prog="task",
        description=spec["description"],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    for param in spec["parameters"]:
        ...   # add each flag based on its declared type
    return p
```

Adding a new slash flag → it appears in `--help` automatically. Same defaults,
same choices, same validation. Tests can drive both surfaces with the same
inputs.

### Decision 2 — Two paths for plan-only (intentional, not redundant)

| Path | Topology loaded | When to use |
|---|---|---|
| `/task --plan "request"` | Full PTI; `enable_implementation=False` | "Just suppress the implementer"; reuses default config |
| `/task --agent-config breakdown_multiflow_plan "request"` | Standalone planner Dual; no PTI wrapper | "I literally only want the planner"; lighter, more explicit |

Both are useful. The flag-path is the "casual" mode (already works, no
extraction needed). The preset-path is the "minimal-topology" mode (needs the
factored YAML). Users pick.

### Decision 3 — Factor `_planner.yaml` only, defer `_executor.yaml`

The planner is reused (full topology + standalone preset). The executor isn't —
`--execute` works today via `enable_planning=False` on the full topology. So
extracting `_executor.yaml` would add a new file with no caller. YAGNI.

### Decision 4 — Move the YAML from `test/` to `src/.../topologies/`

A test fixture that becomes the production default is a footgun (any test
edit changes prod). Move it to `src/openteam/server/resources/tools/task/topologies/`
where it belongs as production code.

### Decision 5 — Phased shipping

Each phase is independently shippable and independently valuable. You can stop
after Phase 1 if priorities shift.

---

## 3. The Plan

### Phase 1 — YAML Modularization & Move *(~45 min, low risk)*

**Step 1.1**: Create `src/openteam/server/resources/tools/task/topologies/breakdown_multiflow_plan.yaml`

(Filename adopted from Plan A — descriptive, matches existing topology naming convention,
no leading underscore since it IS a real preset, not a partial.)

Self-contained planner topology, extracted from lines 147–189 of the current main YAML.
Structure:

```yaml
# breakdown_multiflow_plan.yaml — PLAN-ONLY TOPOLOGY
# Standalone Dual{BTA{MFDual}} for multi-perspective planning.
# Use directly via --agent-config breakdown_multiflow_plan,
# or _import_-ed by the full topology.

_params:
  workspace_root: ???                # REQUIRED override (per workspace_root fix)
  default_inferencer: ClaudeCodeCLI
  plan_max_breakdown: 3
  flow_max_dynamic_steps: 3
  consensus_max_iterations: 3

# (Cascade fixtures: _logger, _debug_mode, _model_name etc. as in main YAML)

_target_: DualInferencer
workspace:
  _target_: InferencerWorkspace
  root: ${_params.workspace_root}
  use_final_deliverables_folder: true
templates_dir: "${oc.env:PROMPT_TEMPLATES_DIR,prompt_templates}"

base_inferencer:
  # (current planner_inferencer.base_inferencer block, lines 154-179)
  _target_: BreakdownThenAggregateInferencer
  _template_root_space: plan
  max_breakdown: ${_params.plan_max_breakdown}
  breakdown_inferencer: ...
  worker_factory:
    __default__:
      _target_: MultiFlowDualInferencer
      ...
  aggregator_inferencer: ...

review_inferencer:
  _target_: ${_params.default_inferencer}
fixer_inferencer:
  _inherits_: review_inferencer
```

**Verification**: Load the YAML directly with `load_config(YAML_PATH, overrides={"_params.workspace_root": str(tmp_path)})` — should instantiate cleanly.

**Step 1.2**: Move `breakdown_multiflow_plan_then_implement.yaml` from `test/.../task/configs/` to `src/.../task/topologies/`

Use `git mv` to preserve history.

**Step 1.3**: Modify the main YAML to `_import_` the planner sub-tree

```yaml
# Before (lines 147-189): inline planner block
planner_inferencer:
  _target_: DualInferencer
  base_inferencer: ...
  review_inferencer: ...
  fixer_inferencer: ...

# After:
planner_inferencer:
  _import_: ./breakdown_multiflow_plan.yaml
  # No overrides needed — _params cascades from the importing YAML
```

The `_import_` directive (verified at `_instantiate.py:203-251`) loads the
referenced file relative to the importing YAML's directory and deep-merges
sibling keys as overrides. Resolves at load time, before OmegaConf interpolation,
so `${_params.*}` references in the imported YAML resolve against the importing
YAML's `_params` block.

**Step 1.4**: Update all callers of the moved YAML

Known callers (from prior workspace_root investigation):
- `test_task_real_cli.py:39` — `YAML_PATH = ...`
- `test_yaml_deliverable_flags_set.py:25` — config-only check
- `test_workspace_final_deliverables.py:33`
- `test_topology_mock_render.py:20`
- `test_hyperparams_default_inferencer.py:20` (note: prior session flagged this file as broken; address separately)
- `tmp_rovodev_launch_pai_run.py` — our launcher (if still around)

Each gets a one-line path update. Preflight should pass.

---

### Phase 2 — Standalone CLI Driven by `tool.json` *(~75 min, medium risk)*

**Step 2.1**: Create `task/cli.py`

```python
"""Standalone CLI for the task executor.

Driven entirely by tool.json so the CLI and slash-command formats can never
drift. Run with `python -m openteam.server.resources.tools.task --help`.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from .executor import execute as task_execute

_TOOL_JSON = Path(__file__).parent / "tool.json"


def _build_parser_from_tool_json() -> argparse.ArgumentParser:
    spec = json.loads(_TOOL_JSON.read_text())
    p = argparse.ArgumentParser(
        prog="task",
        description=spec["description"],
        epilog="Examples:\n  " + "\n  ".join(spec.get("examples", [])),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Mode flags are mutually exclusive — declare in their own group
    mode_group = p.add_mutually_exclusive_group()
    mode_flags = {"--plan", "--execute", "--full", "--confirm"}

    for param in spec["parameters"]:
        name = param["name"]
        target = mode_group if name in mode_flags else p
        kwargs: dict[str, Any] = {}
        if param.get("description"):
            kwargs["help"] = param["description"]
        if param.get("default") is not None and param["type"] != "flag":
            kwargs["default"] = param["default"]
        if param.get("choices"):
            kwargs["choices"] = param["choices"]

        ptype = param["type"]
        if ptype == "flag":
            kwargs["action"] = "store_true"
            kwargs["default"] = False
            target.add_argument(name, **kwargs)
        elif ptype == "int":
            kwargs["type"] = int
            target.add_argument(name, **kwargs)
        elif ptype == "path":
            kwargs["type"] = str    # keep as string; executor validates
            target.add_argument(name, **kwargs)
        elif param.get("repeatable"):
            kwargs["action"] = "append"
            target.add_argument(name, **kwargs)
        elif param.get("positional"):
            target.add_argument(name, **kwargs)
        else:
            target.add_argument(name, **kwargs)
    return p


def _ns_to_arguments(ns: argparse.Namespace) -> dict:
    """Convert argparse Namespace to the dict shape execute() expects.

    argparse converts --foo-bar → ns.foo_bar (underscores). The executor's
    arguments dict already expects underscore-keyed dict (verified via
    _derive_mode_from_flags reading arguments.get('plan'), etc.).
    """
    out = {}
    for k, v in vars(ns).items():
        if v is None or v is False:
            continue   # skip unset flags / unset string flags
        out[k] = v
    return out


def main(argv=None) -> int:
    parser = _build_parser_from_tool_json()
    ns = parser.parse_args(argv)
    arguments = _ns_to_arguments(ns)

    # Minimal session_context — let executor allocate workspace.
    session_context: dict = {}

    try:
        result = asyncio.run(task_execute(arguments, session_context))
    except KeyboardInterrupt:
        print("\n[task] cancelled", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[task] error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # Print result text; structured fields go to stderr if present.
    if isinstance(result, dict):
        print(result.get("text", ""))
        if "context_updates" in result:
            print("\n[context_updates]", file=sys.stderr)
            print(json.dumps(result["context_updates"], indent=2), file=sys.stderr)
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2.2**: Create `task/__main__.py`

```python
"""Module entrypoint: enables `python -m openteam.server.resources.tools.task`."""
from .cli import main
import sys
sys.exit(main())
```

**Step 2.3**: (Optional — packaging owner's call) Add console-script entry-points

```toml
# pyproject.toml
[project.scripts]
task-cli        = "openteam.server.resources.tools.task.cli:main"
role-setup-cli  = "openteam.server.resources.tools.role_setup.cli:main"
create-role-cli = "openteam.server.resources.tools.create_role.cli:main"
```

So `task-cli "request" --plan`, `role-setup-cli ./role.md`, etc. become
possible after `pip install -e .`.

**Step 2.4 — Generalize the CLI builder into a reusable module**

After Step 2.1 builds `task/cli.py`, refactor `_build_parser_from_tool_json()`
into a shared helper at `openteam/server/services/tool_cli.py`:

```python
# openteam/server/services/tool_cli.py
"""Generic tool.json-driven CLI scaffold.

Used by tools/<name>/cli.py to build an argparse parser from the tool's
own tool.json, then invoke the tool's own execute() function. Identical
behavior across all tools that follow the (executor, tool.json) pattern
(task, role_setup, create_role today; future tools tomorrow).
"""
import argparse, asyncio, json, sys
from pathlib import Path
from typing import Any, Awaitable, Callable

ExecuteFn = Callable[[dict, dict], Awaitable[Any]]

def build_parser(tool_json_path: Path, *,
                 mutually_exclusive_groups: list[set[str]] | None = None) -> argparse.ArgumentParser:
    """Build an argparse parser from a tool.json file.

    `mutually_exclusive_groups` is a list of sets — each set names flags that
    can't appear together (e.g., {"--plan", "--execute", "--full", "--confirm"}).
    """
    ...

def run_cli(tool_json_path: Path, execute_fn: ExecuteFn,
            argv: list[str] | None = None,
            mutually_exclusive_groups: list[set[str]] | None = None) -> int:
    parser = build_parser(tool_json_path, mutually_exclusive_groups=mutually_exclusive_groups)
    ns = parser.parse_args(argv)
    arguments = {k: v for k, v in vars(ns).items() if v is not None and v is not False}
    try:
        result = asyncio.run(execute_fn(arguments, session_context={}))
    except KeyboardInterrupt:
        print("\n[cli] cancelled", file=sys.stderr); return 130
    except Exception as e:
        print(f"[cli] error: {type(e).__name__}: {e}", file=sys.stderr); return 1
    print(result.get("text", "") if isinstance(result, dict) else result)
    return 0
```

Then `task/cli.py` shrinks to ~10 lines:
```python
from pathlib import Path
from openteam.server.services.tool_cli import run_cli
from .executor import execute

_TOOL_JSON = Path(__file__).parent / "tool.json"
_MUTEX = [{"--plan", "--execute", "--full", "--confirm"}]

def main(argv=None) -> int:
    return run_cli(_TOOL_JSON, execute, argv=argv, mutually_exclusive_groups=_MUTEX)

if __name__ == "__main__":
    raise SystemExit(main())
```

This is the generic shape for all three tools.

---

### Phase 2.5 — Apply the same CLI scaffold to `role_setup` and `create_role` *(~30 min, low risk)*

Now that `tool_cli.run_cli()` is a reusable helper, both shim tools get a CLI
for free with ~10 lines each.

**Step 2.5.1 — `role_setup/cli.py` + `role_setup/__main__.py`**

```python
# role_setup/cli.py
from pathlib import Path
from openteam.server.services.tool_cli import run_cli
from .executor import execute

_TOOL_JSON = Path(__file__).parent / "tool.json"

def main(argv=None) -> int:
    return run_cli(_TOOL_JSON, execute, argv=argv)

if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# role_setup/__main__.py
from .cli import main; import sys; sys.exit(main())
```

After this, `python -m openteam.server.resources.tools.role_setup --help`
shows role_setup's `tool.json` parameter surface (`role_document_path`,
`--max-facets`, `--max-inner-facets`).

**Step 2.5.2 — `create_role/cli.py` + `create_role/__main__.py`**

Identical shape, swapping the import path. After this,
`python -m openteam.server.resources.tools.create_role "design a docs writer agent"`
runs end-to-end from the terminal.

**Why this is elegant**: the architectural unification (engine layer via
`_run_topology`) is now MIRRORED at the CLI layer (presentation layer via
`tool_cli.run_cli`). All three tools share the same engine AND the same CLI
scaffold. Each retains its own `tool.json` for surface-level customization,
which is exactly the right separation.

---

### ⚠️ Anti-pattern explicitly rejected: "task --agent-config sibling.yaml"

An earlier merger plan (`cached-hennessy.md` rev 2026-05-08T03:27) suggested
running sibling tools via:

```bash
# REJECTED — do NOT do this
python -m openteam.server.resources.tools.task "Create a data analyst role" \
    --agent-config /path/to/create_role_bta.yaml \
    --override template_extra_feed.role_doc_path=/path/to/role.md
```

This is rejected because:
1. **Loses domain semantics** — `role_setup` requires `role_document_path` (a file
   path with type validation), not a free-text `request` argument.
2. **Bypasses `tool.json`** — each bridge tool's `tool.json` declares unique typed
   parameters with descriptions. Stuffing them through `--agent-config` + raw
   `--override` skips all that.
3. **Bypasses domain pre-processing** — `role_setup/executor.py` reads the role
   document, extracts role_name, enumerates available tools/skills, and injects
   them into `template_extra_feed`. Bypassing `execute()` skips all of this and
   the run will fail or produce garbage.
4. **`--override template_extra_feed.X=Y` is the exact "ad-hoc, hacky" pattern
   we want to avoid.**

Phase 2.5's per-tool CLI (10 lines each via `tool_cli.run_cli()`) is the
elegant alternative.

---

### Phase 3 — Default Topology Selection *(~30 min, low risk)*

**Step 3.1**: Update `_resolve_agent_config()` in `executor.py`

Make the relocated `breakdown_multiflow_plan_then_implement.yaml` the default
preset for `--agent-config` (currently defaults to `pti`).

Add the new plan-only preset:
```python
PRESETS = {
    "default": "topologies/breakdown_multiflow_plan_then_implement.yaml",
    "breakdown_multiflow_plan_then_implement": "topologies/breakdown_multiflow_plan_then_implement.yaml",
    "breakdown_multiflow_plan": "topologies/breakdown_multiflow_plan.yaml",
    # … existing pti/bta/dual/etc. presets unchanged
}
```

Update `tool.json`'s `"--agent-config"` default from `"pti"` to
`"breakdown_multiflow_plan_then_implement"` (or alias `"default"`).

**Step 3.2**: Update `tool.json` description blocks

Refine descriptions for `--plan`, `--execute`, `--confirm` to drop the
"PTI only" caveat (since the default topology now wraps PTI, this is
implicit) and add the new preset name to `--agent-config`'s help.

---

## 4. New Preflight Tests

### Test A — CLI/slash format parity *(critical)*
```python
@pytest.mark.preflight
def test_cli_parser_covers_all_tool_json_params():
    """Every parameter in tool.json must be reachable via the CLI parser."""
    from openteam.server.resources.tools.task.cli import _build_parser_from_tool_json
    spec = json.loads(TOOL_JSON.read_text())
    parser = _build_parser_from_tool_json()
    parser_actions = {a.option_strings[0] if a.option_strings else a.dest
                      for a in parser._actions}
    for param in spec["parameters"]:
        assert param["name"] in parser_actions, \
            f"tool.json param {param['name']} missing from CLI parser"
```

### Test B — Standalone planner YAML instantiates cleanly
```python
@pytest.mark.preflight
def test_breakdown_multiflow_plan_instantiates(tmp_path):
    """Standalone planner topology can be loaded + instantiated alone."""
    from rich_python_utils.config_utils import load_config, instantiate
    cfg = load_config(
        str(NEW_PLANNER_YAML_PATH),
        overrides={
            "_target_path": str(OPENSTARTUP_PATH),
            "templates_dir": str(TEMPLATES_DIR),
            "_params.workspace_root": str(tmp_path / "ws"),
        },
    )
    inferencer = instantiate(cfg)
    assert isinstance(inferencer, DualInferencer)
    assert isinstance(inferencer.base_inferencer, BreakdownThenAggregateInferencer)
```

### Test C — `_import_`-ed full YAML matches old inlined version structurally
```python
@pytest.mark.preflight
def test_modular_topology_matches_inlined(tmp_path):
    """Topology built from _import_-ed planner must match the legacy inline structure."""
    # Snapshot the topology tree (class names + key attribs) and compare.
    # Catches drift between the extracted YAML and the importing YAML.
    ...
```

### Test D — `--plan` CLI flag drives PTI's `enable_implementation=False`
```python
@pytest.mark.preflight
def test_cli_plan_flag_sets_pti_enable_implementation(monkeypatch):
    """`task --plan req` must end up calling PTI with enable_implementation=False."""
    from openteam.server.resources.tools.task import cli, executor
    captured = {}
    async def fake_execute(arguments, session_context):
        captured["arguments"] = arguments
        return {"text": "ok"}
    monkeypatch.setattr(executor, "execute", fake_execute)
    monkeypatch.setattr(cli, "task_execute", fake_execute)
    cli.main(["test request", "--plan"])
    assert captured["arguments"].get("plan") is True
```

### Test E — Regression: `--agent-config breakdown_multiflow_plan` runs plan-only
```python
@pytest.mark.preflight
def test_cli_plan_only_preset_excludes_executor(...):
    """Loading the standalone plan preset must NOT instantiate any executor sub-tree."""
    ...
```

---

## 5. Risk Register

| # | Risk | Probability | Mitigation |
|---|---|---|---|
| 1 | `_import_` doesn't carry `${_params.*}` interpolation through correctly | Low (verified in subagent investigation) | Test C catches structural drift |
| 2 | Test fixtures point at moved YAML path → tests break | Medium | Phase 1.4 lists all known callers; bulk update + run preflight |
| 3 | argparse can't model some `tool.json` flag type | Low | We've enumerated all 17 params; only `repeatable` is unusual (`action="append"`) |
| 4 | Mutually-exclusive mode flags clash if user passes `--plan --execute` | Low | argparse `add_mutually_exclusive_group()` handles this with a clear error |
| 5 | Default topology change breaks existing `/task` users relying on the old "pti" preset | Medium | Keep `pti` as a preset alias; only change the default. Add migration note. |
| 6 | Existing test `test_real_pai_codebase_understanding_with_rovodev` uses old YAML path | Medium | Update path; re-run end-to-end |

---

## 6. Migration / Backwards Compatibility

| Caller | Impact | Action |
|---|---|---|
| `/task ...` slash command | Default topology changes (pti → breakdown_multiflow_plan_then_implement) | Document in changelog; pti preset still available explicitly |
| Existing test that loads `test/.../configs/.../yaml` | Path moves to `src/.../topologies/` | Update import paths (~6 files) |
| Anyone using `--plan` flag | No change — already worked | None |
| Anyone using `--execute` flag | No change — already worked | None |
| Anyone using `--confirm` flag | No change — already worked | None |

---

## 7. Out of Scope

- ~~Applying the same CLI pattern to `role_setup/` or `create_role/`~~ — **NOW IN SCOPE** (Phase 2.5).
- Extracting `_executor.yaml` (no caller needs it; defer until proven necessary).
- Building a TUI / interactive mode.
- Daemon mode (CLI talks to a long-running server).
- Splitting the outer reviewer/fixer into a separate YAML.
- Adding new flags to any `tool.json` (this plan is purely structural).
- Refactoring `role_setup` / `create_role` execute() bodies (engine delegation already in place).
- Sharing YAML configs across the three tools (each has domain-specific topology).

---

## 8. Success Criteria

1. ✅ `python -m openteam.server.resources.tools.task --help` shows all flags from `tool.json`.
2. ✅ `python -m openteam.server.resources.tools.task "test" --plan` runs to completion in plan-only mode.
3. ✅ `python -m openteam.server.resources.tools.task "test" --agent-config breakdown_multiflow_plan` runs the standalone plan-only topology.
4. ✅ `python -m openteam.server.resources.tools.role_setup --help` shows role_setup's flags from its tool.json.
5. ✅ `python -m openteam.server.resources.tools.create_role --help` shows create_role's flags from its tool.json.
6. ✅ Adding a new flag to ANY tool's `tool.json` makes it appear in `--help` AND `/<tool> --help` with zero code changes.
7. ✅ `/task --plan "test"` (slash) produces identical output to its CLI counterpart.
8. ✅ Full preflight suite passes (currently 71; expect 77+ after Tests A–E plus 2 sibling-CLI tests).
9. ✅ `test_real_pai_codebase_understanding_with_rovodev` runs end-to-end with the relocated YAML.

---

## 9. Phased Shipping

**Phase 1** (~45 min): YAML modularization + move. Zero behavior change. Self-contained ship.

**Phase 2** (~75 min): Standalone CLI for `task` driven by `tool.json` + extract reusable `tool_cli.run_cli()` helper.

**Phase 2.5** (~30 min): `role_setup` and `create_role` get their own CLIs via the shared helper (~10 lines each).

**Phase 3** (~30 min): Make modularized YAML the default + promote new preset name.

Each phase is independently shippable. Stopping after Phase 1 leaves you with cleaner YAMLs but no CLI. Stopping after Phase 2 gives you a `task` CLI but the sibling tools still slash-only. Phase 2.5 unifies the CLI surface across all three. Phase 3 closes the loop on the YAML default.

Total: **~3 hr** core work + ~30 min for new preflight tests + ~30 min for sibling CLIs = **~4 hours total**.

---

## 10. Why This Is Better Than Either Source Plan

(Updated 2026-05-08T03:36 after re-reading Plan A's revision)

### Critical issue Plan A still has after its rev

Plan A's "Step 7: mode-aware topology selection" REGRESSES working code. It
proposes:

```python
def _select_topology_yaml(mode, agent_config):
    if mode == "plan": return "_planner.yaml"      # would replace existing wiring
    if mode == "execute": return "_executor.yaml"  # would replace existing wiring
```

But executor.py lines 377/379/381 already wire `--plan`/`--execute`/`--confirm`
to PTI's native `enable_implementation`/`enable_planning`/`enable_checkpoint_plan_review`
attribs (verified). The `enable_*` toggle is the canonical PTI semantic; swapping
topologies would change workspace structure, break test parity between modes,
and rewrite working code for no benefit.

This plan keeps the existing wiring and only adds the standalone YAML preset
as a SECOND path (`--agent-config breakdown_multiflow_plan`), not a replacement.

### Comparison

| Concern | Plan A (rev2) | Plan B (mine, original) | Integrated v3 |
|---|---|---|---|
| CLI/slash drift | Inevitable (manual argparse) | Prevented (tool.json-driven) | ✅ Prevented |
| Recognized existing `--plan` wiring | ✅ Yes | ❌ No (would have re-built it) | ✅ Yes |
| Recognized `role_setup`/`create_role` already shim `task` | ❌ Both plans missed this | ❌ | ✅ Verified + leveraged |
| `_executor.yaml` extraction | Not done | Done unnecessarily | ✅ Skipped (YAGNI) |
| Sibling tools get CLIs too | Not addressed | "Out of scope" | ✅ ~30 min via shared helper |
| Risk register | Absent | Present | ✅ Present |
| Test plan | Manual checklist | 4 preflight tests | ✅ 5+ preflight tests |
| Phased shipping | Implicit | Explicit | ✅ Explicit (4 phases) |
| YAML location | Stays in test/ | Moved to src/ | ✅ Moved to src/ |
| Reusable `tool_cli.run_cli` helper | Not designed | Not designed | ✅ Yes |
| Total file changes | ~5 | ~11 | ~10 (3 of which are 10-line files) |
| Total effort | ~4 hr | ~5 hr | **~4 hr** |
| Number of YAML files added | 1 | 2 | 1 |

The integrated plan is **smarter than Plan A, more comprehensive than Plan B, and ships at roughly the same effort as either** because:
1. It correctly recognized that two of Plan B's "phases" were already done (mode wiring).
2. It correctly recognized that `role_setup`/`create_role` already share the engine, so giving them CLIs is a 30-min wrap, not a separate epic.
3. It introduces a generic `tool_cli` helper, so future tools get CLIs for free.

---

## 11. Open Questions (Defaults Proposed)

| Q | Default proposal |
|---|---|
| Where does the `task-cli` binary live? | `pyproject.toml` `[project.scripts]` (defer to packaging owner) |
| Should `_planner.yaml` filename be `breakdown_multiflow_plan.yaml` or `_planner.yaml`? | `breakdown_multiflow_plan.yaml` — matches Plan A, descriptive, no leading underscore (it's a real preset, not a partial) |
| Rename `breakdown_multiflow_plan_then_implement.yaml` → `default.yaml`? | No — descriptive names beat generic ones; preserve git history |
| Should we also add a slash-command alias `/plan` and `/execute`? | No — the existing `/task --plan` syntax is enough. Keep slash surface narrow. |
| Validate `--execute` requires `--initial-plan`? | Yes — `argparse` post-parse validation. Saves the user from a confusing PTI failure 30 minutes in. |

---

**END**
