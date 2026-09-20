# Task Tool: Standalone CLI + Plan-Only Mode + YAML Modularization

**Status**: Proposal
**Author**: drafted in collaboration with rovo dev
**Date**: 2026-05-08
**Scope**: `OpenStartup/src/openteam/server/resources/tools/task/` and its YAML configs

---

## 1. Problem Statement

Today the task tool has three usability gaps:

1. **No standalone CLI.** The tool only runs through the slash-command dispatcher
   (`/task ...`) inside the chat REPL or the FastAPI server. There is no `python -m`
   or `task-cli` binary you can invoke from the terminal for one-shot runs, batch
   jobs, CI experiments, or quick smoke tests.

2. **Two CLIs would diverge.** The slash-command argument schema lives in
   `tool.json`. If we naïvely write a separate `argparse` CLI, we instantly have
   two definitions of the same command surface — guaranteed to drift.

3. **Plan-only mode is half-wired.** The `--plan` flag exists in `tool.json`
   (`"Run planning phase only (PTI only)"`), but the YAML's planner sub-tree is
   embedded inline inside the full plan-then-implement topology. There is no
   self-contained YAML you can point a "plan only" run at without dragging the
   executor sub-tree along (or hacking the topology in code at run time).

The goal of this proposal is to fix all three with one coherent change:

- Add a single CLI entry point that **derives its parser from `tool.json`** so the
  slash format and CLI format never diverge.
- Factor the planner sub-tree out into its own YAML and have the main YAML
  `_import_` it. Promote `breakdown_multiflow_plan_then_implement.yaml` to the
  default task topology. A `--plan` invocation can then load just the planner YAML.
- Wire `--plan` and `--execute` end-to-end so they are first-class supported modes,
  not aspirational TODOs in the parameter description.

---

## 2. Current State Audit

### 2.1 Task tool surface today

`OpenStartup/src/openteam/server/resources/tools/task/`:

```
__init__.py          (empty)
executor.py          (22 KB; entry: execute(arguments, session_context))
tool.json            (full slash-command schema — 17 parameters)
topologies/          (preset topology YAMLs)
```

Public entry point: `executor.execute(arguments: dict, session_context: dict)` (line 473).
Internal core: `_run_topology(...)` (line 304). This is the function the slash
dispatcher calls and the function any new CLI must also call.

### 2.2 Slash-command dispatch chain

```
FastAPI request → conversation_routes
                → ConversationService.run_conversation_turn()
                → detects "/task ..." in user message
                → ToolDispatcher.__call__("task", "/task <args>")
                → parses args against tool.json schema
                → imports executor via tool.json's "executor" field
                → executor.execute(parsed_kwargs, session_context)
```

`tool.json` already declares:
- `--plan` flag — *Run planning phase only (PTI only)*
- `--execute` flag — *Skip planning, execute directly*
- `--full` flag (default true) — *Plan then implement*
- `--confirm` flag — *Plan, wait for user approval, then implement*

These flags are **already advertised** in the tool schema and in the
example-line `/task-execute --initial-plan ./plan.md ""`. They are **not yet
fully wired** in the executor for non-PTI topologies and have no first-class
support in the YAML structure.

### 2.3 Sibling tools follow the same pattern

`role_setup/` and `create_role/` are structurally identical: just `executor.py`
+ `tool.json`. Whatever pattern we establish for the task tool here can be
re-used for them later (Phase 4 / out-of-scope).

### 2.4 YAML structure — `breakdown_multiflow_plan_then_implement.yaml`

| Section | Lines | Notes |
|---|---|---|
| `_params` (hyperparameters) | 95–100 | `workspace_root: ???`, `default_inferencer`, `plan_max_breakdown`, `exec_max_breakdown`, `flow_max_dynamic_steps`, `consensus_max_iterations` |
| `workspace` block | 137–140 | `root: ${_params.workspace_root}` (recently fixed) |
| Outer `Dual` (root) | 130–246 | wraps PTI as base, plus review + fixer |
| **Planner sub-tree** | 147–189 | `base_inferencer.planner_inferencer` — a Dual containing a BTA with MultiFlowDual workers. **This is the extractable node.** |
| Executor sub-tree | 191–211 | `base_inferencer.executor_inferencer` — a bare BTA with Dual workers |
| Outer Dual review/fixer | 212–246 | post-implementation reviewer + fixer for the whole task |

Interpolation surface: only `${_params.*}` and `${oc.env:PROMPT_TEMPLATES_DIR,...}`.
Max nesting depth: 5 levels.

### 2.5 YAML composition — what's already supported

`RichPythonUtils/.../config_utils/_instantiate.py::load_config()` supports two
custom directives:

```yaml
# Pattern A: factor out a self-contained subtree
parent_block:
  _import_: planner.yaml          # loads + deep-merges in
  override_field: 999              # sibling keys override imported values

# Pattern B: copy from elsewhere in the same tree
similar_block:
  _inherits_: parent.other_block
  override_field: 42
```

`_import_` resolves at load time, **before** OmegaConf interpolation. So a
factored-out planner YAML can still use `${_params.*}` placeholders that get
resolved against the main YAML's `_params` block. ✅

We do NOT have Hydra-style `defaults:` lists. We do NOT have `!include` tags.
Just `_import_` and `_inherits_`.

---

## 3. Proposal

Three changes, layered. Each is independently valuable.

### 3.1 Change A — YAML modularization

Factor the planner sub-tree out into its own file and import it back in.

**New layout:**
```
configs/
├── breakdown_multiflow_plan_then_implement.yaml   # DEFAULT (keeps name)
├── _planner.yaml                                  # NEW — extracted planner
└── _executor.yaml                                 # NEW — extracted executor
```

**`_planner.yaml`** — self-contained Dual that wraps a BTA with MultiFlowDual workers.
References `${_params.*}` for hyperparameters; the importing YAML must define
`_params` with at least `workspace_root`, `default_inferencer`,
`plan_max_breakdown`, `flow_max_dynamic_steps`, `consensus_max_iterations`.

```yaml
# _planner.yaml — extracted from lines 147-189 of the main YAML
_target_: DualInferencer
base_inferencer:
  _target_: BreakdownThenAggregateInferencer
  _template_root_space: plan
  max_breakdown: ${_params.plan_max_breakdown}
  breakdown_inferencer: ...
  worker_factory:
    __default__:
      _target_: MultiFlowDualInferencer
      ...
  aggregator_inferencer: ...
review_inferencer: ...
fixer_inferencer: ...
# (optional) workspace propagated by parent or set via override
```

**`_executor.yaml`** — same treatment for the executor sub-tree (lines 191–211).

**`breakdown_multiflow_plan_then_implement.yaml`** — replaces the inline blocks
with `_import_` references:

```yaml
# (existing _params, workspace, etc. unchanged)
_target_: DualInferencer
base_inferencer:
  _target_: PlanThenImplementInferencer
  planner_inferencer:
    _import_: _planner.yaml          # was lines 147-189
  executor_inferencer:
    _import_: _executor.yaml         # was lines 191-211
review_inferencer: ...               # outer reviewer/fixer unchanged
fixer_inferencer: ...
```

The user sees no behavior change for `/task` or `_run_topology`. Only the file
layout changes. **Test impact: re-run preflight (`-m preflight`) — should
still be 71 passed.**

### 3.2 Change B — Promote the modularized YAML to the default task topology

Today, `executor.py` line ~327 uses an alias / preset system (`_resolve_agent_config`)
to look up a topology. The default `--agent-config pti` resolves to a small inline
PTI definition. This change makes the modularized
`breakdown_multiflow_plan_then_implement.yaml` the canonical default for
`/task`-style invocations:

- Move the YAML from `test/openteam/.../task/configs/` into
  `src/openteam/server/.../task/topologies/` (so it ships as production code, not
  test fixture). Same for `_planner.yaml` and `_executor.yaml`.
- Register it as the default preset in `_resolve_agent_config()`.
- Update existing tests that load `test/openteam/.../task/configs/.../yaml`
  to import from the new production path.

**Why move it:** the YAML is no longer a test fixture — it's the production
default topology. Keeping it under `test/` is misleading.

### 3.3 Change C — Standalone CLI driven by `tool.json` (no parser duplication)

Add `task/cli.py` and `task/__main__.py`. Both derive their argparse parser
**at runtime from `tool.json`** so the CLI cannot drift from the slash schema.

**`task/cli.py`** — the single source of CLI logic:

```python
import argparse, asyncio, json, sys
from pathlib import Path
from .executor import execute as task_execute

_TOOL_JSON = Path(__file__).parent / "tool.json"

def _build_parser_from_tool_json() -> argparse.ArgumentParser:
    """Build argparse parser from tool.json's parameter schema.

    This guarantees CLI and slash-command formats stay in sync.
    """
    spec = json.loads(_TOOL_JSON.read_text())
    p = argparse.ArgumentParser(
        prog="task",
        description=spec["description"],
        epilog="Examples:\n  " + "\n  ".join(spec.get("examples", [])),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    for param in spec["parameters"]:
        name = param["name"]
        kwargs = {}
        if param.get("description"):
            kwargs["help"] = param["description"]
        if param.get("default") is not None:
            kwargs["default"] = param["default"]
        if param.get("choices"):
            kwargs["choices"] = param["choices"]

        if param["type"] == "flag":
            kwargs["action"] = "store_true"
            p.add_argument(name, **kwargs)
        elif param["type"] == "int":
            kwargs["type"] = int
            p.add_argument(name, **kwargs)
        elif param["type"] == "path":
            kwargs["type"] = Path
            p.add_argument(name, **kwargs)
        elif param.get("repeatable"):
            kwargs["action"] = "append"
            p.add_argument(name, **kwargs)
        elif param.get("positional"):
            p.add_argument(param["name"], **kwargs)
        else:  # plain string flag
            p.add_argument(name, **kwargs)
    return p


def _argparse_ns_to_arguments(ns: argparse.Namespace) -> dict:
    """Convert argparse Namespace into the dict shape that
    `executor.execute()` expects (matches what slash-dispatch passes)."""
    # argparse turns --foo-bar into foo_bar; tool.json keys are --foo-bar.
    # Strip leading "--" and convert to underscore-keyed dict.
    out = {}
    for k, v in vars(ns).items():
        if v is None:
            continue
        out[k] = v
    return out


def main(argv=None) -> int:
    parser = _build_parser_from_tool_json()
    ns = parser.parse_args(argv)
    arguments = _argparse_ns_to_arguments(ns)
    # session_context: minimal default for CLI runs
    session_context = {"working_dir": None}  # let executor allocate
    try:
        result = asyncio.run(task_execute(arguments, session_context))
    except KeyboardInterrupt:
        print("\n[task] cancelled", file=sys.stderr)
        return 130
    # Print result text, and (in JSON mode) the structured result
    print(result.get("text", "") if isinstance(result, dict) else result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**`task/__main__.py`** — one-liner so `python -m openteam.server.resources.tools.task` works:

```python
from .cli import main; raise SystemExit(main())
```

**Optional `pyproject.toml` entry-point** for a top-level `task-cli` binary
(can be added or skipped depending on your packaging story).

**Why this design is right:**
| Concern | How addressed |
|---|---|
| CLI / slash drift | Parser literally generated from the same JSON the dispatcher uses. |
| Maintenance | Add a flag to `tool.json` → it appears in BOTH surfaces automatically. |
| Tests can drive it | `cli.main(["--plan", "request"])` returns the same result as `/task --plan ...`. |
| Validation | `argparse` + `tool.json` choices give early validation; same as slash. |

### 3.4 Change D — First-class `--plan` / `--execute` modes

Today, `tool.json` declares the flags but the executor has only partial
support (mostly TODOs in the parameter description). With Change A's modular
YAMLs in place, the wiring becomes easy:

**`executor.py::_run_topology()` — mode-aware topology selection:**

```python
def _select_topology_yaml(arguments: dict) -> str:
    """Pick the right YAML based on mode flags."""
    if arguments.get("plan"):                 # --plan
        return "_planner.yaml"
    if arguments.get("execute"):              # --execute
        return "_executor.yaml"
    return "breakdown_multiflow_plan_then_implement.yaml"   # default --full
```

For `--plan`:
- Loads `_planner.yaml` (just the planner Dual).
- Workspace allocator + `_params.workspace_root` injection works the same way.
- Result is the plan output (markdown / structured plan).
- `context_updates["plan_path"]` gets populated; no `impl_path`.

For `--execute`:
- Requires `--initial-plan <path>`. Validate at parse time.
- Loads `_executor.yaml`.
- Reads the plan text and feeds it as the executor's `initial_plan`.
- No planner phase runs; topology is just the executor BTA.

For `--confirm`:
- Loads the full `breakdown_multiflow_plan_then_implement.yaml`.
- Sets PTI's existing `enable_checkpoint_plan_review=True`. Already supported by
  PTI's native field — just needs to be passed through.

Net new code in executor: ~40 lines (mode selection + flag→arg wiring +
`--execute` validation).

---

## 4. Detailed Step-by-Step Implementation

| # | File | Change | Effort |
|---|---|---|---|
| 1 | `task/topologies/_planner.yaml` (new) | Extract lines 147–189 of the main YAML; preserve `${_params.*}` references | 30 min |
| 2 | `task/topologies/_executor.yaml` (new) | Extract lines 191–211; preserve refs | 15 min |
| 3 | `task/topologies/breakdown_multiflow_plan_then_implement.yaml` (moved + edited) | Move from `test/...` to `src/...` and replace inline blocks with `_import_` references | 20 min |
| 4 | All test files referencing the old YAML path | Update path imports | 15 min |
| 5 | `task/cli.py` (new) | tool.json-driven argparse + main() | 60 min |
| 6 | `task/__main__.py` (new) | One-liner module entrypoint | 5 min |
| 7 | `task/executor.py` | Add `_select_topology_yaml()` + mode dispatch in `_run_topology` | 60 min |
| 8 | `task/executor.py` | Validate `--execute` requires `--initial-plan` | 15 min |
| 9 | `tool.json` | Refine descriptions for `--plan` / `--execute` / `--confirm` (drop "PTI only" caveat now that all three modes are first-class) | 10 min |
| 10 | New preflight tests | Tests A–D below | 60 min |
| 11 | (optional) `pyproject.toml` entry-point | `task-cli = openteam.server.resources.tools.task.cli:main` | 10 min |

**Total estimated effort:** ~5 hours.

---

## 5. New Preflight Tests (Regression Guards)

### Test A — CLI/slash format parity
Loads `tool.json`, builds the argparse parser, asserts every parameter in
`tool.json` is reachable via the parser. Catches drift between the two surfaces.

### Test B — `_planner.yaml` is self-contained and instantiates
Loads `_planner.yaml` with a minimal `_params` override and asserts it
instantiates a `DualInferencer` whose base is a `BreakdownThenAggregateInferencer`.

### Test C — Modularized full YAML produces same topology as the inlined version
Snapshot test: load both the pre-extraction and post-extraction full YAML, walk
the resulting topology trees, assert structural equality (class names, attrib
values). Guards against `_import_` accidentally drifting from the original.

### Test D — `--plan` mode runs only the planner
Drives `cli.main(["--plan", "test request"])` end-to-end (with mocks for the
LLM); asserts the resulting workspace contains `plan_*` artifacts but no
`impl_*` artifacts. Same for `--execute --initial-plan x.md`.

---

## 6. Migration / Risk Considerations

### Backwards compatibility
- All current `/task ...` invocations keep working — `--full` (the default)
  loads the modularized YAML which produces an identical topology.
- The slash-command dispatcher's contract with `executor.execute()` is unchanged.
- Existing presets (`pti`, `pti-simple`, `bta`, `dual`, etc.) are unaffected.

### Risks
1. **`_import_` not handling `${_params.*}` correctly.** Mitigation: subagent
   investigation already confirmed `_import_` resolves before interpolation.
   Test C will catch drift.
2. **Test fixtures still pointing at `test/.../yaml`.** Mitigation: grep + bulk
   update the ~7 known callers (we already enumerated them in the workspace_root
   investigation last session).
3. **CLI hangs on stdin in CI.** Mitigation: `argparse` parses `argv` only;
   CLI never reads stdin. `--plan` / `--execute` modes don't add interactivity.
4. **Argparse can't model every `tool.json` flag perfectly.** Mitigation: only
   `--repeatable` is unusual (use `action="append"`). Everything else is plain
   flags / positional / typed strings — argparse handles fine.

### Out-of-scope (deliberate)
- Doing the same for `role_setup/` and `create_role/`. Save for a follow-up.
- Building a TUI / interactive mode. Just argparse for now.
- Daemon mode (CLI talks to a long-running server). Not needed yet.
- Splitting out further sub-trees (e.g., the outer reviewer/fixer). Two YAMLs
  beyond the main are enough; more would harm readability.

---

## 7. Success Criteria

A run is successful if:

1. ✅ `python -m openteam.server.resources.tools.task --plan "test request"`
   completes and writes a plan-only workspace.
2. ✅ `/task --plan "test request"` (slash) produces the same result.
3. ✅ A new flag added to `tool.json` appears in both `--help` AND `/task --help`
   without code changes to `cli.py`.
4. ✅ Full preflight suite still passes (currently 71 tests; expect 75+ after
   adding Tests A–D).
5. ✅ No regression in existing slash-command invocations.
6. ✅ Re-running `test_real_pai_codebase_understanding_with_rovodev` end-to-end
   uses the new modularized YAML and surfaces deliverables identically.

---

## 8. Open Questions / Decisions Needed

| Q | Default proposal |
|---|---|
| Where exactly does the new top-level binary `task-cli` live? | `pyproject.toml` `[project.scripts]` (defer to packaging owner) |
| Should `_planner.yaml` have its own `_params` block or inherit from parent? | Inherit. Simpler, single source of truth. |
| Should `--plan` write to a different output dir than `--full`? | No. Same workspace; the absence of `impl_*` artifacts is the indicator. |
| What about `--analysis` and `--multi-iter`? | Out of scope for this proposal — leave as-is, they only meaningfully apply to `--full`. |
| Do we deprecate `breakdown_multiflow_plan_then_implement.yaml` as the file name (long, awkward) and rename to e.g. `default.yaml` after move? | Recommend yes — rename when moving from `test/` → `src/`. |

---

## 9. Phasing

**Phase 1 (this proposal):** Steps 1–4 — YAML modularization + move. Independently
shippable. No CLI yet. Existing flow preserved.

**Phase 2:** Steps 5–6 — Standalone CLI driven by `tool.json`. Independently
shippable.

**Phase 3:** Steps 7–9 — First-class `--plan` / `--execute` mode wiring.
Depends on Phase 1 (needs the extracted YAMLs).

**Phase 4 (out of scope):** Apply the same pattern to `role_setup` and `create_role`.

---

## 10. Appendix — Why NOT alternate designs

### Why not Hydra `defaults:` for composition?
Codebase uses custom `_import_` (already supported). Adding Hydra would add a
new dependency surface and idiom for marginal benefit.

### Why not a separate `argparse` parser independent of `tool.json`?
Drift is inevitable. Every flag added to slash would need a manual mirror.
We've all worked on codebases with this exact pain. Generating one from the
other is the only sustainable answer.

### Why not click / typer instead of argparse?
Both would work, but they encourage decorator-driven definitions that we'd
have to special-case generate from `tool.json`. Argparse's imperative
`add_argument` matches `tool.json`'s data shape one-to-one. Less magic.

### Why move YAML out of `test/`?
A test fixture that becomes the production default is a footgun. Anyone
editing the YAML for tests would change production behavior. Splitting the
two paths is hygiene.

---

**END**
