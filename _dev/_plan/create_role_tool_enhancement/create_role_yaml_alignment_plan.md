# Create-Role YAML Alignment Plan v1.0

> **Status**: DRAFT — pending human review
> **Author**: Rovo Dev
> **Date**: 2026-05-18
> **Scope**: YAML-only refactor of `create_role_bta.yaml`. No Python code changes.
> **Risk**: 🟢 LOW — declarative cascade additions; preserves all existing per-inferencer values

---

## §0 Executive Summary

`create_role_bta.yaml` is a 82-line BTA topology that pre-dates the modern conventions adopted by `breakdown-multiflow-plan.yaml` (168 lines). The two YAMLs share the same `_run_topology` backbone but diverge in 6 measurable ways. This plan aligns `create_role_bta.yaml` with the reference task topology to gain:

- ✅ **Observability**: clear `_params:` contract documenting required runtime injection
- ✅ **Consistency**: model + timeout values cascade from one place
- ✅ **Maintainability**: future contributors see a familiar structure
- ✅ **Safety**: `_params: workspace_root: ???` makes missing workspace fail loud, not silent
- ✅ **Reviewability**: 50-line header doc explains the topology tree

**No functional behavior change is intended.** The refactor is structural cleanup so create_role looks and behaves like its sibling task topologies.

---

## §1 Current State (Verified)

### File: `create_role_bta.yaml` (82 lines)

| Aspect | Current | Reference (`breakdown-multiflow-plan.yaml`) |
|---|---|---|
| Header doc | 5 lines (just a usage example) | 47 lines (topology tree + design rationale) |
| `_params:` block | ❌ Absent | ✅ Present with `workspace_root: ???` (REQUIRED sentinel) |
| `workspace:` block | ❌ Absent (injected via session_context) | ✅ Present with `${_params.workspace_root}` reference |
| `_model_name:` cascade | ❌ Absent | ✅ `opus[1m]` |
| `_idle_timeout_seconds:` cascade | ❌ Absent | ✅ 600 |
| `_tool_use_idle_timeout_seconds:` cascade | ❌ Absent | ✅ 5400 |
| `_consensus_config:` cascade | ❌ Absent | ✅ Present (N/A for BTA, but harmless) |
| `_output_path:` cascade | ❌ Absent (each inferencer sets own) | ✅ `"output.md"` (uniform across all) |
| `max_breakdown:` | Hardcoded `8` | Parameterized via `${_params.plan_max_breakdown}` |
| `_logger:` | `auto` | `auto` ✅ |
| `_debug_mode:` | `true` | `true` ✅ |
| `_template_manager:` | Present, correct | Present, correct ✅ |

### Runtime Behavior (Verified by reading `executor.py:535-588`)

The executor's `execute()` shim:
1. Pre-allocates workspace via `allocate_tool_workspace("create_role")` → standalone path
2. Injects `working_dir` into `session_context` (NOT via OmegaConf override)
3. Applies overrides: `max_breakdown` + `_template_manager.templates`
4. Delegates to `_run_topology(source=("file", yaml_path), ...)`
5. `_run_topology` → `_resolve_workspace(session_context)` returns the pre-allocated dir
6. That workspace is bound to the instantiated BTA after `instantiate()` returns

**Why this works without a `workspace:` block**: `_run_topology` post-processes the instantiated BTA and assigns its `_workspace` directly. The YAML doesn't need to declare it.

**Why we're still adding it**: For consistency, observability, fail-loud semantics, and CI smoke-test friendliness (running `instantiate()` standalone without the executor wrapper should still work).

---

## §2 Why The Gaps Are Real Issues (Not Just Cosmetic)

### Gap A — No `_params:` Contract → Hidden Coupling
Today the YAML compiles fine even without `workspace_root` injection. If someone runs `instantiate(load_config(...))` directly (no executor), the BTA gets `_workspace=None` and Fix #11/#12 work falls apart silently. Adding `_params: workspace_root: ???` makes this a loud failure.

### Gap B — Hardcoded `max_breakdown: 8` → Not Configurable Via `_params`
Task topology uses `${_params.plan_max_breakdown}`. The executor's override patches the literal value, but a parameterized version is more discoverable and overridable.

### Gap C — No Model/Timeout Cascade → Inconsistent Defaults
Each inferencer falls back to its class-level defaults. RovoChat defaults may differ from RovoDevCLI defaults. Some workers may time out at 300s (RovoChat default) while aggregator gets 5400s (explicit attrib). **Inconsistent reasoning depth across roles.**

### Gap D — No Header Documentation → High Cognitive Load
A new reader has no idea this is plan-only-mode, no idea about the BTA-of-RovoChat-workers-with-RovoDevCLI-aggregator pattern, no idea why aggregator differs from workers. Reference topology has 47 lines of clear ASCII tree + design notes.

### Gap E — `workspace: null` Convention Not Present
Reference topology uses `workspace: ${_params.workspace_root}` to declare the binding contract. Create_role has nothing → opaque magic via executor.

---

## §3 Proposed Changes (Diff Plan)

### Change 3.1 — Add Header Documentation (45-line block)

**Add at top** (before `_target_: BTA`):

```yaml
# ============================================================================
# Create-Role Topology: BTA (single-pass research synthesis)
# ============================================================================
#
# Tool-specific topology that researches a role across N facets and synthesizes
# them into a Role Responsibility Document. Used by the /create_role MCP tool
# and the standalone create_role CLI:
#   python -m openteam.server.resources.tools.create_role --max-facets N "<role>"
#
# Tree structure:
#   BTA                                       single-pass facet research+synth
#   ├── breakdown_inferencer = RovoChat       decompose role → N facets
#   ├── worker_factory = RovoChat (homogen.)  each facet researched independently
#   │                                         (Rovo knowledge-search grounded)
#   └── aggregator_inferencer = RovoDevCLI    synthesize all facets into one
#                                             coherent Role Responsibility Doc
#                                             (CLI agent for filesystem write)
#
# Why three different inferencer types?
#   - RovoChat for breakdown + workers: knowledge-search grounded (Rovo Search)
#     can access Confluence/Jira/Atlas org context for role research.
#   - RovoDevCLI for aggregator: needs to write large structured documents to
#     local files. RovoChat cannot write local files (its outputs route through
#     the response stream only). For ~5-20KB synthesized docs we want the
#     filesystem-write path.
#
# Why no review/fix loop (unlike task topology)?
#   Single-pass research → synthesis is the deliberate design. The agg uses
#   opus-4-6 (config_override below) for high-quality first-pass synthesis.
#   Adding a review/fix loop would 2-3x the LLM cost without proportional
#   quality gain for this fan-out-fan-in shape.

# ---------------------------------------------------------------------------
# HYPERPARAMETERS
# ---------------------------------------------------------------------------
# workspace_root: REQUIRED — injected by executor.execute() via session_context
#                 (see allocate_tool_workspace("create_role") in executor.py).
# max_facets:     overridable via --max-facets CLI arg.
# default_model:  applies to RovoChat workers + breakdown (NOT aggregator,
#                 which has its own opus-4-6 config_override).
_params:
  workspace_root: ???
  max_facets: 8
  default_model: opus[1m]
  default_idle_timeout: 600
  default_tool_use_idle_timeout: 5400
```

### Change 3.2 — Add `workspace:` Block

**Add immediately before `_target_: BTA`**:

```yaml
# Workspace contract: declared here for consistency with task topologies.
# The actual workspace is bound at runtime by _run_topology via session_context,
# but declaring it makes standalone `instantiate(load_config(...))` work too.
workspace:
  _target_: InferencerWorkspace
  root: ${_params.workspace_root}
```

### Change 3.3 — Add Cascades In Shared Config Block

**In the existing shared config section** (between `_debug_mode: true` and `_template_manager:`), insert:

```yaml
_model_name: ${_params.default_model}
_idle_timeout_seconds: ${_params.default_idle_timeout}
_tool_use_idle_timeout_seconds: ${_params.default_tool_use_idle_timeout}
```

### Change 3.4 — Parameterize `max_breakdown`

**Change** (in settings section at end):

```yaml
# Was:
max_breakdown: 8

# To:
max_breakdown: ${_params.max_facets}
```

### Change 3.5 — Document Why No `_output_path` Cascade

**Add a comment** above the inferencers section explaining why output_path is per-inferencer:

```yaml
# Why is `output_path` per-inferencer (not a `_output_path` cascade)?
#   Each role produces a different deliverable filename:
#     breakdown → breakdown_output.md
#     workers   → facet.md
#     aggregator → role_document.md
#   A `_output_path` cascade would overwrite these. The aggregator-input fix
#   (Fix A) correctly reads each worker's own `output_path`, so per-inferencer
#   values are the right design here.
```

### Change 3.6 — Keep Aggregator's `config_override` Untouched

**No change.** The `config_override: '{"agent": {"modelId": "anthropic:claude-opus-4-6"}}'` correctly overrides the `_model_name` cascade because `config_override` is applied later in the inferencer initialization (RovoDevCLI-specific behavior).

**Add a comment** to document this:

```yaml
# Note: config_override below overrides the _model_name cascade.
# RovoDevCLI applies config_override AFTER attrs initialization,
# so it has higher precedence than the cascaded _model_name value.
```

---

## §4 Result — Final YAML Structure (Preview)

```yaml
# [45-line header doc — Change 3.1]

_params:
  workspace_root: ???
  max_facets: 8
  default_model: opus[1m]
  default_idle_timeout: 600
  default_tool_use_idle_timeout: 5400

_target_: BTA

# Shared cascades
_logger: auto
_debug_mode: true
_model_name: ${_params.default_model}                          # NEW
_idle_timeout_seconds: ${_params.default_idle_timeout}         # NEW
_tool_use_idle_timeout_seconds: ${_params.default_tool_use_idle_timeout}  # NEW

_template_manager:
  # ... [unchanged] ...

workspace:                                                      # NEW
  _target_: InferencerWorkspace
  root: ${_params.workspace_root}

# [Comment about per-inferencer output_path — Change 3.5]

breakdown_inferencer:    # unchanged
worker_factory:           # unchanged
aggregator_inferencer:    # comment added (Change 3.6), no structural change

breakdown_format: json_subtasks
worker_query_fields: [description, todos]
max_breakdown: ${_params.max_facets}                            # CHANGED
debug_mode: true
output_path: "role_document.md"
```

**Line count**: 82 → ~145 (within reference topology's 168-line norm).

---

## §5 Acceptance Criteria

| AC | Description | Verification |
|---|---|---|
| **AC1** | `_params` block present with 5 documented keys | grep header |
| **AC2** | `workspace:` block references `${_params.workspace_root}` | grep |
| **AC3** | Three timeout/model cascades present | grep `\${_params\.` count = 5 |
| **AC4** | `max_breakdown` parameterized | grep |
| **AC5** | YAML loads cleanly via `load_config` (no schema errors) | Python smoke check |
| **AC6** | All per-inferencer `output_path` values preserved (`breakdown_output.md`, `facet.md`, `role_document.md`) | diff |
| **AC7** | Aggregator's `config_override` preserved | grep |
| **AC8** | `create_role` smoke run completes (workspace created, output written) | live run with `--max-facets 3` |
| **AC9** | All inferencers receive cascaded model in JSONL `InferenceArgs/` | manual log inspection |
| **AC10** | Standalone `instantiate(load_config(...))` works (must inject `workspace_root` override) | Python smoke check |

---

## §6 Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| `_model_name` cascade conflicts with aggregator's `config_override` | 🟡 MEDIUM | Verified: `config_override` is applied AFTER attrs init by RovoDevCLI, takes precedence. Comment added to YAML to document. |
| `_idle_timeout_seconds` cascade overrides per-inferencer settings that worked before | 🟢 LOW | Cascade only fires when inferencer doesn't set its own. Current values are class defaults (often shorter than 600s) → cascading 600s is a strict upgrade. |
| `_params: workspace_root: ???` breaks executor that doesn't pass it via OmegaConf override | 🟢 LOW | Verified: executor injects via session_context (not override). OmegaConf `???` sentinel only fires if YAML is evaluated standalone WITHOUT the executor. In production path, _run_topology resolves workspace via session_context FIRST and assigns directly to BTA. The `???` would only crash if someone tries `instantiate(load_config(...))` without `workspace_root=` override — which is what we WANT (fail loud). |
| Header doc references "RovoChat" + "RovoDevCLI" by name but actual classes are aliases (`RovoChat = RovoChatInferencer`) | 🟢 LOW | Document used names exactly match `_target_` values in YAML; readers can grep |
| Test scripts referencing old YAML structure break | 🟡 MEDIUM | Verified: only `test_create_role_through_yaml.py` touches the YAML directly. Will need to add `workspace_root` override in any standalone-instantiation test. Will update if found. |
| Standalone CLI test (Hybrid Option C) doesn't supply `workspace_root` override | 🟢 LOW | CLI test goes through `_run_topology` which injects via session_context. Not a standalone `instantiate()` call. |

---

## §7 Implementation Order

| Phase | Action | Duration | Risk |
|---|---|---|---|
| **P1** | Backup current YAML to `.bak` | 1 min | None |
| **P2** | Apply Changes 3.1–3.6 (single edit pass) | 10 min | LOW |
| **P3** | Schema check: `python -c "from rich_python_utils.config_utils import load_config; print(load_config('create_role_bta.yaml', overrides={'_params.workspace_root': '/tmp/x'}))"` | 2 min | LOW |
| **P4** | Verify all per-inferencer `output_path` values preserved (diff against `.bak`) | 1 min | None |
| **P5** | Quick standalone instantiate smoke test (no LLM cost): `python -c "instantiate(load_config('...', overrides={'_params.workspace_root': '/tmp/x'}))"` | 5 min | LOW |
| **P6** | (Optional) Smoke run: `create_role --max-facets 3` | 10-15 min | LOW |
| **Total** | | **~30 min** | |

---

## §8 Out Of Scope

| Item | Why |
|---|---|
| Adding review/fix loop to create_role | Design decision documented in header — single-pass is intentional |
| Refactoring `executor.py` shim logic | YAML-only refactor; Python code unchanged |
| Changing breakdown_format, worker_query_fields, max_continuations | Domain-specific to create_role; reference task topology doesn't have parallels |
| Adding `_consensus_config` | BTA has no review/fix loop; not applicable |
| Adding `_output_path` cascade | Would break per-inferencer filename strategy (see §3.5) |
| Touching `role_setup` YAML | Separate tool; separate enhancement plan if needed |
| Moving workspace allocation logic | Already done — uses shared `allocate_tool_workspace` helper |

---

## §9 Open Questions

| OQ | Question | Default Answer |
|---|---|---|
| **OQ1** | Should `_model_name` cascade default be `opus[1m]` (same as task) or RovoChat's natural default? | `opus[1m]` for consistency with task topology — yields uniform reasoning depth across all OpenTeam tools |
| **OQ2** | Should we use `_model_name: ${oc.env:CREATE_ROLE_MODEL,opus[1m]}` for env override? | NO — keep simple. Add later if needed. Task topology doesn't have env override either. |
| **OQ3** | Should `_consensus_config` be added as a harmless no-op cascade for future-proofing? | NO — BTA doesn't consume it; would be confusing |
| **OQ4** | Should aggregator switch from RovoDevCLI to a different model than opus-4-6? | NO — opus-4-6 selection was deliberate for high-quality first-pass synthesis (see header doc) |
| **OQ5** | Should we add a CHANGELOG-style provenance comment block at the bottom of the YAML? | OPTIONAL — task topology doesn't have one. Skip unless requested |

---

## §10 Comparison Table (Before vs After)

| Section | Before (82 lines) | After (~145 lines) |
|---|---|---|
| Header doc | 5 lines | 47 lines |
| `_params:` | 0 lines | 7 lines |
| Shared cascades | 3 lines (`_logger`, `_debug_mode`, `_template_manager`) | 6 lines (+3 model/timeout cascades) |
| `workspace:` block | 0 lines | 4 lines |
| Inferencers | 38 lines (`breakdown` + `worker_factory` + `aggregator`) | 38 lines (unchanged, +2 comment lines) |
| Settings | 7 lines | 7 lines (`max_breakdown` parameterized) |
| **Total** | **82** | **~145** |

---

## §11 Sample Verification Commands

```bash
# AC5: YAML loads cleanly
cd /Users/tchen7/MyProjects/CoreProjects/OpenStartup && \
PYTHONPATH=src:../AgentFoundation/src:../RichPythonUtils/src:../../rovoteam/OpenTeam/src \
/opt/homebrew/anaconda3/bin/python -c "
from rich_python_utils.config_utils import load_config
cfg = load_config(
    'src/openteam/server/resources/tools/create_role/create_role_bta.yaml',
    overrides={'_params.workspace_root': '/tmp/create_role_smoke_test'}
)
print('YAML loaded successfully')
print('max_breakdown:', cfg.max_breakdown)
print('workspace.root:', cfg.workspace.root)
"

# AC8: Smoke run with --max-facets 3
cd /Users/tchen7/MyProjects/CoreProjects/OpenStartup && \
PYTHONPATH=src:../AgentFoundation/src:../RichPythonUtils/src:../../rovoteam/OpenTeam/src \
/opt/homebrew/anaconda3/bin/python -m openteam.server.resources.tools.create_role \
  --max-facets 3 \
  "Senior Backend Engineer focused on microservices" \
  > tmp_create_role_smoke.log 2>&1 &
```

---

## §12 Provenance

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-18 01:23 | Rovo Dev | Initial plan after auditing `create_role_bta.yaml` vs `breakdown-multiflow-plan.yaml` reference. 6 changes proposed (3.1–3.6); ~63 lines net YAML growth. |

---

## §13 Decision Required From Human Reviewer

- [ ] **Approve plan as-is** → I execute Phases 1–6 sequentially
- [ ] **Approve subset** → Specify which changes (3.1, 3.2, 3.3, 3.4, 3.5, 3.6) to skip
- [ ] **Request refinement** → Specify what's missing or unclear
- [ ] **Reject** → Specify alternative direction

Send a short response indicating your choice, then I proceed.
