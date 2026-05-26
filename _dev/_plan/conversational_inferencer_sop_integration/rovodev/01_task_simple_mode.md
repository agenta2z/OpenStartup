# Chapter 1 — F1: Task Simple Mode (Default)

> **Predecessor:** `task-cli-unification-and-plan-only-mode.md`
> **Status:** Proposal
> **Implements:** F1 from `README.md`

---

## 1. Goal

Make `/task` **cheap, fast, and transparent by default**. A single `/task "<request>"`
runs as ONE prompt against ONE leaf inferencer (default: `RovoDevCliInferencer`).

> **CORRECTION (post-review):** Earlier drafts of this chapter proposed a new
> `<session_root>/_jobs/<job_id>/` layout for simple-mode workspaces.
> **That was wrong.** Simple mode reuses the **existing task workspace
> convention** at `<runtime_root>/tasks/task/task_<timestamp>_<8hex>/` — the
> SAME path/format that today's heavyweight task runs use. The only structural
> difference is that simple mode is a **single-node task** (no `children/`
> subdirectory; no topology runner; no nested per-role workspaces). The leaf
> inferencer writes into the same standard 5-folder node layout it always
> writes into when it's a child of a heavyweight topology — we just don't
> wrap it with a topology orchestrator.

### 1.1 The existing task workspace convention (verbatim from disk)

Two real-world `<runtime_root>` locations observed in the codebase today:
- `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_runtime/tasks/` (CLI / user-level)
- `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/server/_runtime/tasks/` (server-side, when run as part of OpenTeam server)

Naming pattern: `<runtime_root>/tasks/<task_or_topology_name>/<task_or_topology_name>_<YYYYMMDD>_<HHMMSS>_<8hex>/`

E.g.:
- `…/_runtime/tasks/create_role/create_role_20260518_163839_2aa53e58/`
- `…/_runtime/tasks/task/task_20260517_000152_task-e0b67640/`

Every NODE in this workspace tree (root OR any nested child like `propose`,
`review`, `breakdown`, `round_01/propose`, …) has the same **5-folder layout**:

```
<node_dir>/
├── artifacts/                                # node-level intermediate artifacts
├── checkpoints/                              # per-step checkpoint JSON files
├── logs/
│   └── session/
│       └── <InferencerClass>-<8hex>.jsonl(.parts)   # session log (streamed)
├── _runtime/
│   └── inferencer_cache/
│       └── <InferencerClass>/                # leaf inferencer's streaming cache
└── outputs/                                  # final deliverables of this node
```

Root nodes additionally have a `children/` subdirectory whose entries are
themselves full 5-folder node workspaces (recursive). Topology-level
artifacts also appear at the root (e.g., `artifacts/round00_output.md`,
`outputs/round_log.jsonl`).

### 1.2 Simple mode = the same workspace, with ONE node and NO children

Simple-mode `/task` runs land at the **same path** as today's heavyweight
runs, with the **same folder layout**, but with no nested `children/`
directory (because there are no children — the root IS the only node):

```
<runtime_root>/tasks/task/task_<YYYYMMDD>_<HHMMSS>_<8hex>/
├── artifacts/
│   ├── meta.json                             # task lifecycle metadata
│   ├── inferencer_args.json                  # leaf inferencer ctor + call args
│   └── input_prompt.md                       # rendered prompt (verbatim)
├── checkpoints/                              # OPTIONAL; simple has one step — may be empty or skipped
├── logs/
│   └── session/
│       └── RovoDevCliInferencer-<8hex>.jsonl(.parts)
├── _runtime/
│   └── inferencer_cache/
│       └── RovoDevCliInferencer/             # the leaf inferencer's own streaming cache
└── outputs/
    ├── raw_response.txt                      # full assembled raw response (incl. <Response> tags)
    ├── parsed_output.json                    # extracted <Response> body + metadata
    └── implementation_report.md              # the detailed report the LLM wrote per output_path (see §3.3)
```

What's **explicitly missing vs. heavy mode** (and why):
- **No `children/`** — single-node task; no propose/review/breakdown subnodes.
- **No topology-level artifacts** (e.g., `round00_output.md`, `round_log.jsonl`)
  — there is no topology runner running rounds.
- **No `stdout.log` / `stderr.log` at the workspace root** — the leaf
  inferencer runs IN-PROCESS for foreground `/task --simple`; its streaming
  output goes into `_runtime/inferencer_cache/<InferencerClass>/` (as
  always) plus the session log in `logs/session/`. Only when the task is
  shelled out via `/background-job task ...` (chapter 3) does the
  JobManager runner redirect a subprocess's stdout/stderr into separate
  files (and those land in the JobManager's own job workspace at
  `<runtime_root>/_jobs/bg-<id>/`, distinct from the inner task workspace —
  the task workspace stays under `tasks/task/...` regardless).

### 1.3 What this implies for design

The simple-mode executor is a **thin wrapper** that:
1. Resolves `<runtime_root>` (same env/config resolution today's heavyweight
   path uses — `OPENTEAM_RUNTIME_ROOT` / `_runtime/tasks/` defaulting).
2. Creates the workspace directory `tasks/task/task_<ts>_<8hex>/` with the
   standard 5 subdirs.
3. Constructs the leaf inferencer, **pointing its cache at
   `<node_dir>/_runtime/inferencer_cache/<InferencerClass>/`** — the
   same path-construction logic used by topology runners today when
   they spawn child node inferencers (so there's a single shared
   helper to extract).
4. Calls `await inferencer.ainfer_streaming(prompt)`; the inferencer
   handles its own session-log writing to `logs/session/<Class>-<id>.jsonl`
   (this is its existing behavior; no change needed).
5. Writes `outputs/raw_response.txt` and `outputs/parsed_output.json`; the leaf inferencer (if it has file-write tools) also writes `outputs/implementation_report.md` per the `output_path` instruction. If the leaf has no file tools, the executor's post-call fallback writes the `<Response>` body to `implementation_report.md` (see §3.3.5).
   from the final response.
6. Writes `artifacts/meta.json` with completion status.

The key insight: **we do not need a new "simple workspace" abstraction**.
We need to (a) reuse the existing `_runtime/tasks/task/` root path, (b)
reuse the existing node-workspace allocator helper (extracted out of
the topology runner if needed), and (c) skip the topology dispatch
entirely.

The heavyweight dual-agent consensus topology (PTI, breakdown-multiflow,
proposer+reviewer) becomes **opt-in** via existing flags `--full`, `--confirm`,
`--plan`. Backward compatible flag semantics preserved; only the **default
behavior** changes from `--full` to `--simple`.

---

## 2. Current State

### 2.1 Task tool today

- **Schema:** `OpenStartup/src/openteam/server/resources/tools/task/tool.json`
  (also published in `AgentFoundation/.../resources/tools/task/tool.json`).
- **Executor:** `OpenStartup/src/openteam/server/resources/tools/task/executor.py`
  (the 22 KB `executor.execute()` function, dispatched via tool registry).
- **CLI:** `OpenStartup/src/openteam/server/resources/tools/task/cli.py`
  (existing standalone CLI, derived from `tool.json`).
- **Topologies:** `task/topologies/*.yaml` — `pti.yaml`, `bta-dual.yaml`,
  `breakdown-multiflow-plan-then-implement.yaml` (current default), etc.
- **Default mode flag:** `--full` (`tool.json` line ~22: `"default": true`).
- **Default workspace:** `_rankevolve_workspace/task_<timestamp>/` — flat
  layout with many topology-level artifacts.

### 2.2 The "leaf inferencer" we'll use

`RovoDevCliInferencer` at
`AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/external/rovodev/rovodev_cli_inferencer.py`:

```python
class RovoDevCliInferencer(TerminalSessionTemplatedInferencerBase):
    # Wraps `acli rovodev legacy` or `acli rovodev`
    # Single-turn: inf("prompt") → str
    # Multi-turn (auto-resume): inf.new_session("first") then inf("second")
    # Streaming: async for chunk in inf.ainfer_streaming(prompt): ...
    # Async: result = await inf.ainfer(prompt)
    # has_local_access=True, yolo=True by default (skip CLI confirmation prompts)
```

It already:
- Spawns a subprocess (`acli rovodev legacy "<prompt>"` with `--output-file`
  for clean LLM output capture).
- Manages a streaming cache dir.
- Supports model override via `config_override.agent.modelId`.
- Has `--jira`, `--enable-deep-plan`, `--agent-mode`, `--config-override`
  options exposed as ctor kwargs.

**This is exactly the leaf we want for `--simple`.**

### 2.3 What changes vs. what stays

| Aspect | Today | After F1 |
|--------|-------|----------|
| Default mode | `--full` (PTI consensus) | **`--simple`** (one leaf-inferencer prompt) |
| `--full` semantics | Default-on, runs PTI | Opt-in flag, runs PTI as today |
| `--plan` / `--confirm` semantics | Run planning topology | Unchanged (run planning topology) |
| Workspace layout | `<runtime_root>/tasks/task/task_<ts>_<8hex>/` with full `children/` tree | **Same path** `<runtime_root>/tasks/task/task_<ts>_<8hex>/`, **same 5-folder node layout**, but **no `children/`** subdir (single-node). Heavy/plan/confirm modes unchanged. |
| Inferencer choice (simple) | N/A | `--leaf-inferencer rovodev_cli` (default) `\| claude_code_cli \| claude_api` |
| Output (simple) | N/A | `parsed_output.json` (the response text + metadata) |

---

## 3. Design

### 3.1 New `--simple` flag in `tool.json`

Add **one** new parameter to `tool.json`:

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
  "default": "rovodev_cli",
  "choices": ["rovodev_cli", "claude_code_cli", "claude_api", "openai_api"],
  "description": "Leaf inferencer for --simple mode."
}
```

Also flip `--full`'s `"default": true` to `"default": false` (with a note
in the description that it's now opt-in).

**Mode resolution precedence** (executor.py change):

```python
def resolve_mode(args: dict) -> str:
    # Explicit non-simple modes take precedence
    for explicit in ("plan", "confirm", "execute", "full"):
        if args.get(explicit):
            return explicit
    # --simple is default
    if args.get("simple", True):  # default True
        return "simple"
    # Last-resort fallback (preserves old behavior if user passes --no-simple
    # without specifying any other mode)
    return "full"
```

**Conflict detection**: explicit `--simple` + explicit `--full` → reject with
clear error. Existing conflict-detection block in `executor._derive_mode_from_flags`
already exists; extend it.

### 3.2 The simple-mode executor

New function `_run_simple_mode()` in `executor.py`:

```python
async def _run_simple_mode(
    arguments: dict,
    session_context: dict,
) -> ToolExecutionResult:
    """Run a one-shot prompt through a leaf inferencer.

    Workspace layout (reuses today's task workspace convention; single-node,
    no children/):
      <runtime_root>/tasks/task/task_<YYYYMMDD>_<HHMMSS>_<8hex>/
      ├── artifacts/
      │   ├── meta.json
      │   ├── inferencer_args.json
      │   └── input_prompt.md
      ├── checkpoints/                  # may be empty for a one-step run
      ├── logs/session/<InferencerClass>-<id>.jsonl(.parts)
      ├── _runtime/inferencer_cache/<InferencerClass>/  (managed by leaf inferencer)
      └── outputs/
          ├── raw_response.txt
          ├── parsed_output.json
          └── implementation_report.md     (written by the LLM per output_path, or by post-call fallback)
    """
    # 1. Allocate workspace using the existing task-workspace allocator —
    # SAME helper today's heavyweight path uses. We pass task_name="task"
    # so the path is <runtime_root>/tasks/task/task_<ts>_<8hex>/ exactly
    # like a heavyweight 'task' run, just without the children/ subtree.
    workspace = allocate_task_node_workspace(
        task_name="task",
        session_context=session_context,
        create_children_dir=False,   # simple mode → no children/
    )
    # 2. Build the prompt — use the simple-mode template
    prompt = _render_simple_prompt(
        request=arguments["request"],
        session_context=session_context,
    )
    (workspace / "artifacts" / "input_prompt.md").write_text(prompt, encoding="utf-8")
    # 3. Construct the leaf inferencer — point its cache & session-log dirs
    # at the standard locations within THIS node's workspace.
    leaf_name = arguments.get("leaf_inferencer", "rovodev_cli")
    leaf_class_name = LEAF_CLASS_NAME_MAP[leaf_name]   # e.g., "RovoDevCliInferencer"
    inferencer = _make_leaf_inferencer(
        leaf_name=leaf_name,
        model=arguments.get("model"),
        cache_dir=workspace / "_runtime" / "inferencer_cache" / leaf_class_name,
        session_log_dir=workspace / "logs" / "session",
        target_path=session_context.get("workflow_target_path"),
    )
    # 4. Persist inferencer args for replay/debugging
    _persist_inferencer_args(workspace / "artifacts" / "inferencer_args.json", inferencer)
    # 5. Run inference (streaming, captured)
    raw_response = ""
    async for chunk in inferencer.ainfer_streaming(prompt):
        raw_response += chunk
        # streaming cache + session log are written by the inferencer
        # itself into the dirs configured in step 3 — no change vs. when
        # the same inferencer runs as a topology child.
    (workspace / "outputs" / "raw_response.txt").write_text(raw_response, encoding="utf-8")
    # 6. Parse output (inferencer-specific)
    parsed = inferencer.parse_output(raw_response) if hasattr(inferencer, "parse_output") else {"response": raw_response}
    (workspace / "outputs" / "parsed_output.json").write_text(
        json.dumps(parsed, indent=2, default=str), encoding="utf-8",
    )
    # 7. Write meta, return result
    _write_meta(workspace / "artifacts" / "meta.json", status="completed", ...)
    return ToolExecutionResult(
        success=True,
        output=parsed.get("response", raw_response),
        artifacts={
            "workspace": str(workspace),
            "parsed_output": str(workspace / "outputs" / "parsed_output.json"),
        },
    )
```

### 3.3 Simple-mode prompt template — **reuse the existing `implementation/main/initial.jinja2`**

> **DECISION (post-review, replaces an earlier draft):** Do NOT create a new
> `simple_initial.jinja2` template, and do NOT introduce a new
> `_variables/task_posture/` slot. Instead, **reuse the existing
> `agent_foundation/resources/prompt_templates/implementation/main/initial.jinja2`**
> verbatim, with a small number of `{% if %}` guards added so the template
> gracefully adapts when optional context is missing. Simple mode and
> heavy-mode topology callers both render the **same template**; the
> rendering differs only by which variables they pass.

#### 3.3.1 Why reuse, not fork

The existing `implementation/main/initial.jinja2` already provides eight
production-grade contracts that a fresh minimal template would silently
drop, and that downstream code depends on:

1. **Mandatory `<Response>` tag wrapper** with the explicit "system depends
   on these tags" warning. Downstream response parsers expect `<Response>`
   tags universally; omitting them silently breaks summary extraction.
2. **`{{ output_path }}` contract** — the LLM is told to write a detailed
   implementation report to a specific file path; the executor can then
   read that file as the structured deliverable.
3. **`{{ employee }}` identity injection** (already optional via existing
   `{% if employee is defined %}` guard) — keeps simple-mode aligned with
   every other inferencer's persona model.
4. **`{{ task_preamble }}` and `{{ task_instructions }}` variable slots**
   (with `default.jinja2` and `aggregation.jinja2` choices) — lets the
   caller pick the flavor without forking the template.
5. **Shared notes** via `{{ notes.local_search_efficiency }}` and
   `{{ instructions.behavior.file_reading_fallback }}` — battle-tested
   guidance that stays in sync because every caller renders the same
   notes file.
6. **Numeric metrics discipline** for testing/benchmarking results
   (explicit "DO NOT just report 'tests passed'" guidance).
7. **`tests/round{{ round_index }}/` and `benchmarks/round{{ round_index }}/`
   artifact paths** — uniform layout across all task workspaces, future-proof
   for review/refine iterations should simple mode ever grow them.
8. **Behavioral guardrails** (file-reading fallback, validate_changes
   warnings, `<Response>`-fallback recovery instructions) that are already
   tuned from production usage.

Creating a parallel "minimal" template would (a) silently lose all of the
above and (b) drift away from production over time as the canonical
template gets refined.

#### 3.3.2 The mismatch — one truthful claim that must NOT be made in simple mode

The existing `initial.jinja2` line 48 contains an unconditional claim:

```
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
```

This is TRUE when the template is rendered by a topology's
implementation-child node (which receives an approved plan from the
preceding planning node). It is **FALSE for simple mode** — the user
typed one sentence, no plan exists, and telling the LLM "you have an
approved plan" is actively harmful: it discourages necessary investigation
and can cause the LLM to fabricate the contents of a non-existent plan.

A secondary mismatch: the path components `tests/round{{ round_index }}/`
and `benchmarks/round{{ round_index }}/` render literally as
`tests/round0/` when `round_index=0` in simple mode (where no review
iteration exists). Cosmetic, but worth a tiny tweak.

#### 3.3.3 The fix — additive `{% if %}` guards (no new files, no new variant slots)

Apply three small surgical changes to `implementation/main/initial.jinja2`,
following the **existing** `{% if employee is defined %}` pattern (so the
templating idiom is unchanged):

**Change 1 (line 48, the "APPROVED PLAN" block):**

Replace:
```jinja2
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
```

With:
```jinja2
{% if has_approved_plan is defined and has_approved_plan %}
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
{% else %}
- You are starting from a single user request without a pre-approved plan.
  * Read minimally to ground yourself in the relevant code (file headers, target functions, immediate call sites). DO NOT investigate the entire codebase.
  * Then act decisively on the request. If the request is ambiguous, pick the most plausible interpretation, state it briefly in your `<Response>`, and proceed.
{% endif %}
```

Rationale: pure additive — topology callers gain ONE optional kwarg
(`has_approved_plan=True`) to opt INTO the plan-based wording. Callers
that pass nothing (today, every external caller) get the new "no plan"
wording, which is more accurate for them too if they happen to be
invoking this template ad-hoc. **However, to preserve byte-identical
behavior for existing topology callers in phase A.3 (refactor)**, the
extraction also updates the topology runner's render-context construction
to set `has_approved_plan=True` whenever it spawns an implementation-child
of a planning node (one-line `template_vars["has_approved_plan"] = True`
in the topology runner, see §5 file change list). Net behavior: existing
topology runs unchanged; simple-mode renders the new "no plan" wording.

**Change 2 (line 56, the `round_index` path components):**

Replace:
```jinja2
{{ output_path }}` under `tests/round{{ round_index }}/` and `benchmarks/round{{ round_index }}/`,
```

With:
```jinja2
{{ output_path }}` under `tests/{% if round_index %}round{{ round_index }}/{% endif %}` and `benchmarks/{% if round_index %}round{{ round_index }}/{% endif %}`,
```

Rationale: in simple mode `round_index` is `0` (falsy in Jinja2), so the
`round0/` segment collapses, yielding clean `tests/` and `benchmarks/`
paths. Topology callers with `round_index=1,2,…` see no change.

**Change 3 (defensive — `prior_output_path` style guards verified
already present):**

No change needed — `initial.jinja2` does not reference `prior_output_path`
or any other review-iteration-only variable. Verified by `grep`. The
`followup.jinja2` and `review.jinja2` templates DO reference these and
already use `{%- if prior_output_path %}` guards, so the pattern is
consistent. (`followup.jinja2` and `review.jinja2` are NOT used by
simple mode — simple mode is one-shot.)

#### 3.3.4 What the simple-mode executor passes

The simple-mode executor (`_run_simple_mode` in §3.2) builds
`template_vars` exactly like a topology implementation-node would, with
two differences:

```python
template_vars = {
    # Same as today's topology callers:
    "input":                 arguments["request"],
    "task_preamble":         load_variable("task_preamble", "default"),     # existing slot
    "task_instructions":     load_variable("task_instructions", "default"), # existing slot
    "output_path":           str(workspace / "outputs" / "implementation_report.md"),
    "session_root_path":     session_context.get("session_root_path"),
    "workflow_target_path":  session_context.get("workflow_target_path"),
    "docs_path":             session_context.get("docs_path"),
    "employee":              session_context.get("employee"),               # existing optional guard
    "notes":                 load_shared_notes(),                           # existing
    "instructions":          load_shared_instructions(),                    # existing

    # Different in simple mode:
    # 1. Omit has_approved_plan entirely → template renders "no plan" branch
    # 2. round_index = 0 → template collapses round0/ segment
    "round_index":           0,
}
```

Then renders the **existing** template:

```python
prompt = render_template(
    "implementation/main/initial.jinja2",
    template_vars,
)
```

#### 3.3.5 Output artifact reconciliation

Because we now use the existing template, the LLM is instructed to write
an **implementation report** to `outputs/implementation_report.md` AND to
return a `<Response>`-wrapped summary. Simple mode workspace artifacts
become:

```
outputs/
├── raw_response.txt              # full assembled raw stream (incl. <Response> tags)
├── parsed_output.json            # extracted <Response> body + metadata
└── implementation_report.md      # the detailed report the LLM wrote per output_path
```

This is **strictly better** than the original §1.2 layout — we get a
structured detailed report PLUS the conversational summary, for free.
Update §1.2 to reflect this (one extra file in `outputs/`).

**Fallback for non-filesystem leaf inferencers:** If the leaf inferencer
is `claude_api` / `openai_api` (no file-write tools), the LLM cannot
honor the `output_path` instruction. The simple-mode executor detects
this after the call:

```python
report_path = workspace / "outputs" / "implementation_report.md"
if not report_path.exists():
    # Leaf had no file tools; persist <Response> body as the report
    response_body = parsed.get("response", raw_response)
    report_path.write_text(response_body, encoding="utf-8")
```

Single safety net; no template change required.

#### 3.3.6 Net diff summary

| Change | File | Lines | Risk |
|--------|------|-------|------|
| Wrap "APPROVED PLAN" block in `{% if has_approved_plan %}…{% else %}…{% endif %}` | `prompt_templates/implementation/main/initial.jinja2` | ~6 line change at line 48 | Low — pure additive; default branch matches today only when caller passes `has_approved_plan=True` |
| Collapse `round{{ round_index }}/` when `round_index` is falsy | same file | 1 line change at line 56 | Low — `0` is falsy in Jinja2; existing callers pass 1+ |
| Add `template_vars["has_approved_plan"] = True` in topology implementation-child render-context construction | topology runner (location TBD during Phase A.3 grep) | 1 line | Low — preserves existing behavior byte-identically |
| **Total new template files** | — | **0** | — |
| **Total new variant slot directories** | — | **0** | — |

**Test addition:** `test_initial_jinja2_renders_without_has_approved_plan`
— assert the rendered output contains the "no plan" wording and NOT the
"APPROVED PLAN" wording when `has_approved_plan` is absent/False.
Conversely, `test_initial_jinja2_renders_with_has_approved_plan` — assert
the inverse. These pin both branches.

#### 3.3.7 Pre-flight check (already done at planning time)

Before merging the template change, the following greps were run to
confirm zero collisions:

```
$ grep -rn 'task_posture\|has_approved_plan' AgentFoundation/ OpenStartup/
  (no hits outside _dev/_plan/ docs)

$ grep -n 'APPROVED PLAN' AgentFoundation/src/agent_foundation/resources/prompt_templates/implementation/main/initial.jinja2
  48: - You have an APPROVED PLAN that has been reviewed and refined. ...
  (exactly one occurrence — the surgery site)

$ grep -n 'round_index\|round[0-9]' .../implementation/main/initial.jinja2
  56: ... tests/round{{ round_index }}/ and benchmarks/round{{ round_index }}/ ...
  (exactly one occurrence)
```

Safe to apply.

---

**Bottom line:** reuse the existing template; the simple-mode executor
passes different (i.e., fewer) variables; the template adapts via two
`{% if %}` guards following the established `{% if employee is defined %}`
idiom. Zero new template files. Zero new variant directories. The
production-grade contracts of the existing template (`<Response>` tags,
`output_path`, employee, notes, numeric-metrics discipline) all carry
over to simple mode automatically.

### 3.4 Workspace allocation

**Reuse the existing task-workspace allocator.** Today's heavyweight task
executor already has a helper that:
1. Resolves `<runtime_root>` from env/config.
2. Builds the path `<runtime_root>/tasks/<task_name>/<task_name>_<YYYYMMDD>_<HHMMSS>_<8hex>/`.
3. Creates the 5 standard subdirs (`artifacts/`, `checkpoints/`, `logs/session/`,
   `_runtime/inferencer_cache/`, `outputs/`).
4. Optionally creates `children/` (only for multi-node topologies).

The helper today is embedded inside the topology runner. **Phase A.3 extracts
it** into a reusable function so both simple mode AND topology runs call the
same code:

`OpenStartup/src/openteam/server/resources/tools/task/workspace.py` (extracted):

```python
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
      create_children_dir: if True, also create children/ (for topology roots).
        Simple mode passes False.
      short_id: optional override; default = uuid4().hex[:8].

    Returns the absolute workspace path. Idempotent on the short_id.
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
    """Same fallback chain today's heavyweight executor uses:
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

**Naming note:** simple-mode uses `task_name="task"` so the outer
grouping dir matches today's convention for one-off `/task` calls. The
inner instance name follows the SAME `{task_name}_{ts}_{8hex}` format,
which is how today's `/task` runs are named (verified on disk:
`task_20260517_000152_task-e0b67640` is one example; we'll align future
runs to the `{name}_{ts}_{8hex}` form documented in the existing
allocator).

A **separate** `JobManager` workspace allocator (chapter 3 §3.2) lives at
`<runtime_root>/_jobs/bg-<id>/` and is ONLY for the JobManager's own
bookkeeping (the bg-job's stdout/stderr capture, schedule meta) — it is
**not** where the underlying task runs. When `/background-job task ...`
invokes a task in the background, the inner task workspace still lands
at `<runtime_root>/tasks/task/task_<ts>_<8hex>/` (per this chapter), and
the JobManager workspace `<runtime_root>/_jobs/bg-<id>/` just holds the
subprocess wrapper metadata + log redirects.

### 3.5 Leaf inferencer factory

`AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py`:

```python
LEAF_CLASS_NAME_MAP = {
    "rovodev_cli":      "RovoDevCliInferencer",
    "claude_code_cli":  "ClaudeCodeCliInferencer",
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
      cache_dir: <node_dir>/_runtime/inferencer_cache/<InferencerClass>/
        — the existing standard cache location used by topology runners.
      session_log_dir: <node_dir>/logs/session/ — the existing standard
        session-log directory used by topology runners.

    Supported names: rovodev_cli, claude_code_cli, claude_api, openai_api.
    """
    if leaf_name == "rovodev_cli":
        from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev import RovoDevCliInferencer
        return RovoDevCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_id=model or "",
            yolo=True,
            cache_folder=str(cache_dir) if cache_dir else None,
            session_log_dir=str(session_log_dir) if session_log_dir else None,
        )
    if leaf_name == "claude_code_cli":
        from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code import ClaudeCodeCliInferencer
        return ClaudeCodeCliInferencer(
            target_path=str(target_path) if target_path else None,
            model_id=model or "",
            cache_folder=str(cache_dir) if cache_dir else None,
            session_log_dir=str(session_log_dir) if session_log_dir else None,
        )
    if leaf_name == "claude_api":
        from agent_foundation.common.inferencers.api_inferencers.claude_api_inferencer import ClaudeApiInferencer
        return ClaudeApiInferencer(model_id=model or "claude-opus-4-7")
    if leaf_name == "openai_api":
        from agent_foundation.common.inferencers.api_inferencers.openai_api_inferencer import OpenAIApiInferencer
        return OpenAIApiInferencer(model_id=model or "gpt-4.1")
    raise ValueError(f"Unknown leaf inferencer: {leaf_name!r}")
```

### 3.6 `inferencer_args.json` schema

For replay and debugging, capture (written to
`<workspace>/artifacts/inferencer_args.json`):

```json
{
  "inferencer_class": "RovoDevCliInferencer",
  "ctor_kwargs": {
    "target_path": "/Users/tchen7/repo/src",
    "model_id": "claude-opus-4-7",
    "yolo": true,
    "cache_folder": "<runtime_root>/tasks/task/task_20260519_170712_a1b2c3d4/_runtime/inferencer_cache/RovoDevCliInferencer",
    "session_log_dir": "<runtime_root>/tasks/task/task_20260519_170712_a1b2c3d4/logs/session"
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

Use `attrs.asdict()` on the inferencer to get ctor_kwargs (with secrets
filtered via a `_REDACT_FIELDS` set).

---

## 4. Backward Compatibility & Migration

### 4.1 The behavior change

**Before:** `/task "fix bug"` → runs `breakdown-multiflow-plan-then-implement.yaml`
(heavyweight 2-agent consensus).

**After:** `/task "fix bug"` → runs single `RovoDevCliInferencer` prompt.

This is a **breaking behavior change** for any callsite that relied on the
implicit heavyweight default.

### 4.2 Migration plan

1. **Phase 1 (one release):** Ship with `--simple` defaulting to `False`,
   `--full` defaulting to `True` (current behavior). Add deprecation warning
   when `--full` is implicit: "task default mode will change to --simple in
   release X. Pass --full explicitly to suppress this warning."
2. **Phase 2 (one release later):** Flip defaults. `--simple` defaults to
   `True`. Old callers must add `--full` explicitly.
3. **Phase 3:** Remove deprecation warning, defaults stable.

A `RANKEVOLVE_TASK_DEFAULT_MODE` env var lets ops force one or the other for
batch jobs / CI.

### 4.3 Workspace layout migration

**Zero migration needed.** Both heavy mode (today) and simple mode (new)
write into the **same parent directory**
`<runtime_root>/tasks/task/task_<ts>_<8hex>/`, with the **same 5-folder
node layout**. The only structural difference is that simple-mode workspaces
have no `children/` subdir. Existing tools that walk
`<runtime_root>/tasks/` (e.g., session inspectors, log viewers, the OpenTeam
UI) continue to work unchanged — they may need a small tweak to gracefully
handle the absent `children/` (treat as "leaf"), but no path-pattern
changes.

The earlier-mentioned `<session_root>/_jobs/<job_id>/` layout exists ONLY
under the `JobManager` (chapter 3) for tracking background-job *subprocess
wrappers* — that's a separate concern from where a task's own workspace
lives. A `/background-job task ...` call produces TWO workspaces:
- `<runtime_root>/_jobs/bg-<id>/` — JobManager bookkeeping (subprocess
  stdout/stderr, schedule meta)
- `<runtime_root>/tasks/task/task_<ts>_<8hex>/` — the inner task itself
  (per this chapter), populated by the subprocess CLI

### 4.4 SOP callsites

The existing SOP `code_optimization.md` Phase 4 says `/task <request>`. With
the new default = simple, that becomes a single Rovo Dev call per hypothesis
— which is the desired behavior (much cheaper). If a particular SOP needs
the heavy path, it must be updated to `/task --full <request>`. We will
audit existing SOPs in chapter 8 (rollout).

---

## 5. Concrete Code-Change List

| File | Change |
|------|--------|
| `OpenStartup/src/openteam/server/resources/tools/task/tool.json` | Add `--simple`, `--leaf-inferencer`. Flip `--full` default to `false` (Phase 2). Update description. |
| `AgentFoundation/src/agent_foundation/resources/tools/task/tool.json` | Mirror the above. |
| `OpenStartup/src/openteam/server/resources/tools/task/executor.py` | Add `_run_simple_mode()`. Update `_derive_mode_from_flags` for new precedence. Add `_run_topology_or_simple()` dispatcher. Add conflict detection for `--simple` + `--full`. **Refactor**: extract the existing root-workspace allocation logic into the shared `task/workspace.py` helper below so simple mode and heavy mode call the same code. |
| `OpenStartup/src/openteam/server/resources/tools/task/workspace.py` | NEW (extracted from `executor.py`'s existing inline workspace allocation). `allocate_task_node_workspace(task_name, session_context, create_children_dir, short_id)` + `resolve_runtime_root(session_context)`. This is the canonical task-workspace allocator used by both heavy and simple modes (and by every topology runner child-node creation today, after extraction). |
| `AgentFoundation/src/agent_foundation/resources/prompt_templates/implementation/main/initial.jinja2` | EXISTING template, minor edits per §3.3.3: (1) wrap "APPROVED PLAN" block in `{% if has_approved_plan %}…{% else %}…{% endif %}` at line 48; (2) collapse `round{{ round_index }}/` path segment when `round_index` is falsy at line 56. **No new template file.** |
| Topology runner (location to be confirmed during Phase A.3 grep — likely `topology_executor.py` or similar in `OpenStartup/src/openteam/server/resources/tools/task/`) | Add `template_vars["has_approved_plan"] = True` when constructing the render context for implementation-child nodes that follow a planning node. Preserves byte-identical behavior for existing topology runs after the §3.3.3 Change 1 template edit. |
| `AgentFoundation/src/agent_foundation/common/jobs/__init__.py` | NEW (empty for now; populated in chapter 3). |
| `AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py` | NEW. `make_leaf_inferencer(leaf_name, *, model, cache_dir, session_log_dir, target_path)` + `LEAF_CLASS_NAME_MAP`. Used by simple mode (this chapter) and the SOP subprocess runner (chapter 5). Note the signature accepts `cache_dir` + `session_log_dir` directly (NOT a `workspace` root) so callers from either layout convention can pass the right dirs. |
| `OpenStartup/src/openteam/server/resources/tools/task/cli.py` | Add `--simple` / `--leaf-inferencer` to argparse mirror. |
| `tests/openteam/tools/task/test_simple_mode.py` | NEW. See §6 test plan. |

---

## 6. Test Plan

| # | Test | Type |
|---|------|------|
| T1.1 | `_run_simple_mode("fix typo")` creates expected workspace at `<runtime_root>/tasks/task/task_<ts>_<8hex>/` with 5 standard subdirs and NO `children/` | Unit |
| T1.2 | `artifacts/inferencer_args.json` contains ctor kwargs, no secrets, references `_runtime/inferencer_cache/RovoDevCliInferencer/` as cache_folder | Unit |
| T1.3 | `make_leaf_inferencer("rovodev_cli", cache_dir=…, session_log_dir=…)` returns `RovoDevCliInferencer` instance with those dirs configured | Unit |
| T1.4 | Mode resolution: `{simple: True, full: True}` → ValueError | Unit |
| T1.5 | Mode resolution: `{plan: True}` overrides default simple | Unit |
| T1.6 | Mode resolution: empty args → "simple" | Unit |
| T1.7 | `/task --simple "list files"` via slash dispatcher → response captured | Integration (mock leaf) |
| T1.8 | `/task --full "fix"` still routes to topology runner; produces SAME workspace path pattern with `children/` populated | Integration |
| T1.9 | Streaming chunks accumulate into `outputs/raw_response.txt`; leaf inferencer's session log lands at `logs/session/RovoDevCliInferencer-<id>.jsonl(.parts)`; `outputs/implementation_report.md` produced (either by leaf with file tools, or by post-call fallback writing the `<Response>` body) | Integration |
| T1.9b | `initial.jinja2` renders the "no plan" branch when `has_approved_plan` is absent/False; renders the "APPROVED PLAN" branch when True (covers §3.3.3 Change 1 both ways) | Unit |
| T1.9c | `initial.jinja2` with `round_index=0` produces `tests/` and `benchmarks/` (no `round0/` segment); with `round_index=2` produces `tests/round2/` and `benchmarks/round2/` (covers §3.3.3 Change 2 both ways) | Unit |
| T1.10 | Workspace path matches existing on-disk convention: regex `tasks/task/task_\d{8}_\d{6}_[0-9a-f]{8}` | Unit |
| T1.11 | `allocate_task_node_workspace(task_name="task", create_children_dir=False)` does NOT create `children/`; `create_children_dir=True` DOES create it | Unit |
| T1.12 | `resolve_runtime_root` fallback chain: explicit → env → server-detected → CWD | Unit |
| T1.13 | Existing tools that walk `<runtime_root>/tasks/` (session inspectors) handle simple-mode workspaces (no `children/`) without crashing | Integration |
| T1.14 | Simple-mode workspace survives parent process crash (no lockfile, all writes flushed) | Integration |
| T1.E2E | Real `/task "what does this repo do?"` against Rovo Dev CLI → file artifacts present at the expected paths, response sensible | E2E smoke |

---

## 7. Open Questions

1. **Should `--simple` support multi-turn?** Today `RovoDevCliInferencer` supports
   `inf.new_session(); inf(...); inf(...)` (auto-resume). Simple mode is
   one-shot in this proposal. **Decision:** Leave multi-turn to the parent
   conversational inferencer (which can call `/task` repeatedly with
   accumulating context); simple mode stays one-shot. Document this.
2. **Default model for leaf?** Inherit from session model config; fall back
   to inferencer's hardcoded default (`claude-opus-4-7` for Rovo Dev CLI).
3. **What if leaf inferencer needs MFA mid-run?** The leaf streams to stderr;
   we surface the last 50 lines of stderr in the failure summary. Out of
   scope to auto-recover; user re-runs after auth.
4. **Why not just write everything flat in the simple-mode workspace
   (skip the 5-folder layout)?** Considered and rejected. Reasons:
   (a) Existing log viewers, session inspectors, and the OpenTeam UI all
   walk `<runtime_root>/tasks/*/*/logs/session/*.jsonl` and
   `<runtime_root>/tasks/*/*/_runtime/inferencer_cache/*/` — flat layout
   would invisibly hide simple-mode runs from these tools. (b) The leaf
   inferencer classes ALREADY write into these standard dirs when used
   as topology children; reusing the convention means zero changes to
   the inferencer code itself. (c) Future evolution (e.g., wrapping a
   simple-mode run with a `verify` child) becomes "just add a
   `children/verify/` subdir" — no schema rewrite. The cost (3 extra
   empty dirs for a one-step run) is trivial.
5. **What about the existing inline workspace allocation in
   `task/executor.py` (the heavyweight path)?** Phase A.3 of the rollout
   (chapter 8) extracts that logic into the shared
   `task/workspace.py` helper. The heavyweight executor is updated to
   call the same helper with `create_children_dir=True`. This is a pure
   refactor with byte-identical behavior for existing runs.

---

*Continued in `02_input_queue.md`.*
