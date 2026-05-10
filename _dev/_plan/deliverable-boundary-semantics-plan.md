# Deliverable Boundary Semantics — Design & Implementation Plan

> **Status:** Draft v1.2 (integrated), 2026-05-05
> **Scope:** AgentFoundation flow inferencers (PTI, BTA, MultiFlow, MFDual, Dual, LinearWorkflow)
> **Driver use case:** `OpenStartup/test/openteam/resources/tools/task/configs/breakdown_multiflow_plan_then_implement.yaml`. The actual topology (verified against the YAML, NOT a paraphrase): outer Dual → base PTI → {planner Dual → BTA → MFDual workers; **executor BTA (BARE — no Dual wrap) → Dual workers**; analyzer absent} + outer Dual's fixer = a separate PTI sibling.
> **Owner:** TBD
>
> ## Revision history
> - **v1.0** initial draft (Deliverable Boundary semantics)
> - **v1.1** removed `DeliverableBoundaryMixin`; layered: flag on `InferencerBase`, free helpers in `deliverable_boundary.py`, per-subclass policy attribs
> - **v1.2** integrated cross-plan analysis vs the sibling "outputs/ = deliverables" proposal:
>   - added **Phase 0** of foundational bug fixes from sibling plan (real bugs both plans must fix)
>   - added **§3.7a Response-vs-Deliverable disambiguation** (gap neither plan addressed originally)
>   - added **§6.5 Why we keep `outputs/final_deliverables/`** (explicit rejection of the conflated-folders proposal)
>   - added open question Q7 on the same topic
>   - added §16 explicit comparison-and-merge log so future readers can see what was integrated and why
> - **v1.3** the sibling plan was rewritten and converged on the boundary architecture. Integrated the genuine refinements they introduced and added the testing gap NEITHER plan originally addressed:
>   - **D3 (corrected):** Dual's `_active_proposer()` is a concrete heuristic — "fixer if fixer ran, else base_inferencer" — because Dual genuinely lacks winner-tracking. My earlier "consult `consensus_tracker`" was vague.
>   - **D4 (corrected):** PTI's extension method is `_finalize_outputs`, not `_finalize_response`.
>   - **D5 (corrected):** Outer `DualInferencer` in driver topology is **NOT** a boundary; it is a pass-through wrapping PTI. PTI is the outermost boundary.
>   - **D6 (refined):** `InferencerWorkspace.has_deliverables` checks `isdir AND non-empty`, not just `isdir`.
>   - **D7 (explicit reuse):** Per-file copy delegates to existing `safe_copy_per_file` + `find_conflicting_and_agreed_files` from `rich_python_utils.path_utils.path_listing`. No reimplementation.
>   - **NEW gap addressed:** §12.5 sophisticated mock topology test — wires up the full `breakdown_multiflow_plan_then_implement.yaml` with stub inferencers (no LLMs) and asserts deliverable surfacing semantically end-to-end. This gap existed in BOTH original plans.
>   - **AC9 added:** mock topology test passes as part of the acceptance criteria.
> - **v1.7** third-pass external review verified all v1.6 propagation fixes were applied (C1, C2, C3 from the review were already-fixed in v1.6 — flagged as stale-feedback and rejected). NEW genuinely-valid items applied:
>   - **M2:** §14 decision summary clarified — "one boundary HOP per collect-aggregate cycle" (not "one boundary upward"). Concrete 5-layer / 3-hop example added. Distinguishes pass-through layers (Dual, LWI) from boundary layers (BTA, PTI).
>   - **M3:** Added **AC0** for Phase 0 foundational bug fixes (was missing — all ACs started from Phase 1+).
>   - **M5:** §12.5.7 `_substitute_leaves` now uses each flow inferencer's existing `_iter_child_inferencers()` method (verified at `breakdown_then_aggregate_inferencer.py:1066`) rather than inventing `_enumerate_inferencer_child_attrs`. Falls back to `attrs.fields()` introspection for inferencers without that method.
>   - **M6:** §12.5.7 `test_real_yaml_topology_deliverable_surfacing` now documents env-var scaffolding (`BMP_DEFAULT_INFERENCER=ClaudeCodeCLI`, `ANTHROPIC_API_KEY` placeholder) and uses `monkeypatch` so `instantiate(cfg)` doesn't fail on missing LLM credentials.
>   - **§12.5.8 NEW (T1-T8):** 8 additional tests added closing gaps identified in second-pass review: concurrent completion (T1), `error` conflict strategy (T2), bypass-via-direct-write detection (T3), AC7 logging (T4), strengthened §12.4 assertions (T5), `AggregateReport` field validation (T6), grandchild flag propagation (T7), boundary-once invariant replacing fragile S18 (T8).
>   - **REJECTED as stale (already fixed in v1.6):** C1 (Phase 4 long names), C2 (Phase 4 includes fixer), C3 (mock topology contradicts §2.5). Verified by reading the current file.
>   - **REJECTED as design intent:** m1 (section 6.5 before 6 is intentional — §6.5 is a §6-prequel rejection-of-alternative section; renumbering would harm the document flow). m2-m6 are minor or praise. m1 also: changelog reverse-chronological order is standard convention.
>
> - **v1.6** second-pass external review found that v1.5 corrections didn't propagate to all downstream sections — the "fixer is outer Dual's sibling, not a PTI child" correction was applied to §2.5 and §3.7 but the same wrong text persisted in 11 other places. ALL valid propagation fixes applied:
>   - **§2.5 surfacing flow steps 4-5:** PTI runs planner+executor only (no fixer); outer Dual surfaces EITHER base OR fixer (never both); no `fixer/` subfolder at task root.
>   - **§4.2 PTI Collect/Aggregate:** Filter is `("planner", "executor", "analyzer")` (short names); PTI has no `fixer` child.
>   - **§6 Step 5/6:** PTI doesn't run fixer; outer Dual selects base OR fixer; documented both branches of task-root deliverables.
>   - **Phase 4 step 2/3:** Filter uses correct short names; drops fixer.
>   - **§11.5 E5:** Fixer is outer Dual's sibling; fixer REPLACES base; no `fixer/` subfolder.
>   - **AC4:** Two scenarios documented (review-passed vs fixer-ran); no `fixer/` subfolder.
>   - **§12.2:** PTI tests planner/executor only.
>   - **§12.5.2 mock topology:** Fixer at outer Dual sibling level; executor is bare BTA (matches §2.5).
>   - **S8 + S11 (rewritten):** Now correctly model fixer-replaces-base via `_active_proposer()` selection, not fixer-as-additional-subfolder. New assertions verify file content tag (base vs fixer) at task root for both scenarios.
>   - **§12.5.7 test code comment:** Updated to clarify no `fixer/` subfolder; fixer replaces via Dual pass-through.
>   - **Line 196 mixin rationale:** "Dual does winner-selection" → "Dual does pass-through-of-active-proposer".
>
>   **The semantic insight:** Dual's `_active_proposer()` returns EITHER base OR fixer (never both). Fixer is a complete PTI replica; when it runs, it REPLACES base at the task root, not adds alongside. This means the task-root tree shape is the same in both cases (`{planner/, executor/, implementation.md}`), but the CONTENTS differ. The mock test now verifies this via content-tag assertions.
>
> - **v1.5** external review caught factual errors that survived v1.4. ALL valid corrections applied; over-fix tendencies (e.g., dropping `publishes_response_as_deliverable`) explicitly rejected with reasoning. The valid corrections were:
>   - **Issue 1 (TOPOLOGY ERROR — major):** §2.5 + header described the executor as `Dual{base=BTA}`. The actual YAML (line 202-203) has the executor as a **bare BTA, NOT Dual-wrapped**. Driver topology in §2.5 fully corrected; executor and planner are now correctly described as asymmetric. Header summary corrected.
>   - **Issue 2 (PTI FILTER NAMES — major):** §3.7 PTI `deliverable_collect_filter` used long attribute names (`planner_inferencer`, etc.). PTI's workspace uses SHORT names (`planner`, `executor`, `analyzer`) per `_setup_iteration_children` calling `iter_ws.child(short_name)`. Filter corrected; also clarified that "fixer" is NOT a PTI child — it's outer Dual's sibling PTI.
>   - **Issue 3 (DOUBLE-BOUNDARY CLARIFICATION):** Made it explicit in §2.5 that collect stops at the worker boundary and never recurses into the worker's inner BTA (which would otherwise also be a boundary). Confirmed §12.5 S14 already covers this case but added explicit comment.
>   - **Issue 4 (BACKWARD COMPAT — major):** Setting `BTA.is_deliverable_boundary=True` as the new default would silently start promoting workers (changing the existing `promote_worker_deliverables=False` semantics). Resolved by relying on §11.5 E6: the boundary mechanism only ACTIVATES when `use_final_deliverables_folder=True`. Existing BTAs (which mostly don't have that flag) become a no-op. role_setup (which does have it) gets the new behavior. Made this explicit in §11.5 E6 + Phase 2 step 6.
>   - **Issue 5 (STALE TEXT):** §16.3 still referenced `consensus_tracker`. Removed.
>   - **Issue 6 (CONSISTENCY):** §7.2 still said "Rewrite". Changed to "EXTEND".
>   - **Issue 7 (UNDEFINED ATTRIB):** §5.3 referenced `deliverable_publish_self` which was never defined. Removed.
>   - **Issue 8 (API CLARITY):** `collect_child_boundary_deliverables` signature accepts BOTH a parent_workspace AND optional parent_inferencer (for in-process flag check), with on-disk fallback. Made explicit.
>   - **Issue 10/11/12 (WORDING):** Fixed imprecise "Dual selects" → "Dual surfaces active proposer's"; fixed "MFDual delegates to inner BTA" → "MFDual wraps base_inferencer (which is a MultiFlowInferencer/BTA) in Dual's propose step".
>   - **Issue 9 (REJECTED — already addressed in v1.4):** Reviewer suggested dropping `publishes_response_as_deliverable`. v1.4 already moved it to subclass-only on BTA/PTI, addressing the original "bloat on InferencerBase" concern. The reviewer didn't notice the v1.4 change. Dropping it entirely loses declarative semantics; kept as subclass-only.
> - **v1.4** the sibling plan was rewritten AGAIN with explicit corrections. Integrated:
>   - **C1 (refined further):** Dual's `_active_proposer()` uses `ConsensusIterationRecord.counter_feedback` (in-process, primary signal) with the on-disk fixer-workspace check as a resume-only fallback. v1.3's heuristic was "fixer if fixer workspace has outputs"; v1.4's is the more precise iteration-record check.
>   - **C2 (compromise):** `publishes_response_as_deliverable` survives, BUT moves from `InferencerBase` to subclass-only (BTA/PTI). The sibling argued "drop entirely" — partially correct: putting it on `InferencerBase` is universality bloat; but dropping it loses declarative semantics. The compromise keeps the flag where it's actually used.
>   - **C3 (corrected):** All BTA `_finalize_response` work is **EXTEND, not REWRITE**. Phase 2's wording corrected.
>   - **E1 (NEW — neither plan had it):** `direct_surface_single_worker` BTA optimization. When breakdown returns 1 subtask, skip the aggregator and surface the single worker's deliverables directly.
>   - **E2–E5 (explicit edge cases):** New §11.5 enumerates 4 edge cases (empty breakdown, empty workers, MFDual chain, fixer-as-PTI nesting) with explicit safety analysis.
>   - **§12.5 strengthened:** Mock topology test now uses **post-instantiation leaf substitution against the REAL YAML** (loads `breakdown_multiflow_plan_then_implement.yaml`, then walks the tree replacing leaves with `DeliverableStubInferencer`). This catches YAML wiring + Hydra interpolation bugs that pure in-process construction cannot.
>   - **AC10 added:** `direct_surface_single_worker` works correctly when enabled.

---

## 0. TL;DR

Today's flow inferencers track outputs at the **inferencer level** (`output.md`, `aggregation_report.md`, `outputs/final_deliverables/`), but they don't share a **clear orchestration contract** for *which* artifacts surface *where* in deeply nested topologies. The result is that meaningful artifacts (e.g. a worker's inner aggregator output) get **trapped** in deep child workspaces, and naïve recursive promotion would either dump everything at the top or collide on names.

This plan introduces a single, framework-level concept — **Deliverable Boundary** — and a small, predictable propagation contract:

> **Deliverables surface exactly one orchestration boundary upward; they only become visible to higher levels if the parent boundary republishes them.**

The plan keeps the existing 3-way directory split (`artifacts/`, `outputs/`, `outputs/final_deliverables/`), adds a small attribute (`is_deliverable_boundary`) per inferencer, and defines exactly four hooks: **Publish**, **Collect**, **Aggregate**, **Republish**. Existing primitives (`InferencerWorkspace.deliverables_dir`, BTA `_finalize_response`, `promote_worker_deliverables`) remain — they become the implementations of those hooks.

---

## 1. Goals & Non-goals

### 1.1 Goals
- **G1.** Surface meaningful artifacts up the orchestration tree without collapsing nested structure or naming.
- **G2.** Provide a uniform, predictable rule that applies to **any** depth and combination of `PTI / BTA / MultiFlow / MFDual / Dual / LinearWorkflow`.
- **G3.** Distinguish three artifact classes: **intermediate** (`artifacts/`), **response/report** (`outputs/`), **published deliverable** (`outputs/final_deliverables/`).
- **G4.** Compose cleanly with existing mechanisms: `use_final_deliverables_folder`, `_finalize_response`, `promote_worker_deliverables`, `resolve_output_path`.
- **G5.** Backward-compatible default: existing topologies must continue to behave exactly as today unless they explicitly opt in.
- **G6.** Be debuggable: every promotion event is logged; every artifact has a traceable provenance path.
- **G7.** Be testable in isolation: deliverable boundaries can be exercised in unit tests without spawning real LLMs.

### 1.2 Non-goals
- **NG1.** Redesign the workspace directory layout. We keep `artifacts/`, `outputs/`, `outputs/final_deliverables/`.
- **NG2.** Replace `output.md` / `aggregation_report.md` as the raw response/report channel.
- **NG3.** Build a content-aware merging system. Conflict resolution stays file-name based (existing `safe_copy_per_file` + `largest` fallback).
- **NG4.** Add a runtime artifact registry / manifest service. (Possible follow-up; out of scope for v1.)
- **NG5.** Support cross-workspace links (symlinks, hardlinks). v1 uses copies for portability and simplicity.
- **NG6.** Refactor `output.md` naming (separate concern; can follow this plan).

### 1.3 Anti-goals
- **AG1.** No magic deep-bubbling. Artifacts must NEVER skip a boundary.
- **AG2.** No silent drops. Skipped/missing/conflicting deliverables must be logged.

---

## 2. Concepts

### 2.1 Deliverable Boundary
A **Deliverable Boundary** is an inferencer that is the canonical published-artifact root for its subtree. Boundaries decide what becomes visible to their parent orchestrator.

> **Property:** `is_deliverable_boundary: bool` (default `False`).

When `True`, the inferencer guarantees:
1. After its execution, its `outputs/final_deliverables/` directory contains the **complete, named** set of artifacts it wishes to publish to its parent boundary.
2. Internal child workspaces (`children/.../outputs/...`) may be inspected for debugging but are **not** the canonical artifact source for the parent.

### 2.2 Boundary topology rules

| Inferencer kind | Default `is_deliverable_boundary` | Rationale |
|---|---|---|
| `LinearWorkflowInferencer` | `False` | A linear pipeline is a sequence of steps; its output is its last step's output. Not its own boundary unless wrapped. |
| `DualInferencer` | `False` | A propose-and-review pair; the proposer typically *is* the boundary. Dual just selects. |
| `BreakdownThenAggregateInferencer` (BTA) | **`True`** | BTA is the canonical aggregation point; its aggregator output is the natural deliverable set. |
| `MultiFlowInferencer` | `False` (acts as N parallel siblings of one BTA) | Its outputs are routed to the parent BTA's aggregator. |
| `MultiFlowDualInferencer` (MFDual) | `False` | Same — it's a parallel propose-and-review wrapper around BTA. |
| `PlanThenImplementInferencer` (PTI) | **`True`** | PTI's output is the implementer's final result; it owns the final published artifacts of its plan/exec/fix triplet. |
| **Worker inferencer** (a child created by BTA's `worker_factory`) | **`True`** at the **worker root** | A worker is one orchestration unit; its boundary is the worker root, not its internal sub-tree. |

> **Rule of thumb:** Boundaries are placed wherever a "finished thing" exists. PTI is a finished plan-execute-fix cycle. BTA is a finished aggregation. A worker is a finished delegated unit.

### 2.3 The Four Hooks

Every boundary participates in four hooks:

| Hook | Direction | When | What it does |
|---|---|---|---|
| **Publish** | Inward (self) | After own execution finishes | Write own artifacts into `self/outputs/final_deliverables/` (using the existing `deliverables_dir` API). |
| **Collect** | Inward (children) | Before aggregation/finalization | Walk child workspaces; identify each child boundary and read its `outputs/final_deliverables/`. NEVER recurse past a boundary. |
| **Aggregate** | Inward → self | During finalization | Merge collected child deliverables into self's deliverables space (with name-spaced subfolders by default to avoid collisions). |
| **Republish** | Outward (to parent) | At end of finalization | Ensure `self/outputs/final_deliverables/` is the canonical, parent-visible artifact set. (No upward write — parents pull, not children push.) |

### 2.4 The Surfacing Contract (the one rule)

> **A child boundary's `outputs/final_deliverables/` is visible to its immediate parent boundary, and only to its immediate parent. Anything deeper is NOT visible without explicit republication by intermediate boundaries.**

This is the elegance: deliverables propagate exactly **one boundary at a time**. No deep bubbling.

### 2.5 Concrete example — your driver topology (v1.5 — corrected from actual YAML)

**Boundary placement:** the outer `DualInferencer` is **NOT** a boundary itself; it is a pass-through that surfaces its active proposer's (= base PTI's) deliverables. The outermost boundary in this topology is the base PTI. The task root receives PTI's deliverables through outer Dual's pass-through finalize step.

**Critical correction from earlier drafts:** v1.0–v1.4 incorrectly described the executor side as `Dual{base=BTA}`. The actual YAML (line 202-203) has the executor as a **bare BTA**, NOT Dual-wrapped. The planner is `Dual{base=BTA}`; the executor is just `BTA`. They are NOT symmetric.

Also: the outer Dual's `fixer_inferencer` is a separate PTI **sibling** of base PTI (NOT a child of the base PTI). PTI itself has internal children named `planner_inferencer` / `executor_inferencer` / `analyzer_inferencer` (per `_CHILD_DEFAULTS`); the workspace child dirs are SHORT names `planner/` / `executor/` / `analyzer/` (per `_setup_iteration_children`).

```
TaskRoot
└── outer Dual                                          (boundary: False — pass-through)
    ├── base_inferencer = PTI                           (boundary: True — outermost)
    │   ├── planner_inferencer = Dual                   (boundary: False — pass-through)
    │   │   └── base_inferencer = BTA                   (boundary: True)
    │   │       ├── worker_0 = MFDual                   (boundary: True at worker root)
    │   │       │   └── inner BTA / aggregator          (NOT collected — collect stops at worker)
    │   │       ├── worker_1 = MFDual                   (boundary: True at worker root)
    │   │       └── worker_2 = MFDual                   (boundary: True at worker root)
    │   └── executor_inferencer = BTA                   (boundary: True — BARE, no Dual wrap)
    │       ├── worker_0 = Dual                         (boundary: True at worker root)
    │       └── worker_N = Dual                         (boundary: True at worker root)
    └── fixer_inferencer = PTI                          (boundary: True — sibling of base PTI)
```

Surfacing flow:
1. Each `worker_i` publishes to `worker_i/outputs/final_deliverables/`.
2. The plan-side BTA collects those into its own `final_deliverables/workers/worker_i/...`, then aggregator publishes its merged plan into `bta/outputs/final_deliverables/<plan files>`.
3. The planner Dual is a pass-through; it surfaces its active proposer's deliverables (the BTA's). It does not "select a winner" — there is no selection step in `DualInferencer`.
4. PTI consumes the planner's final deliverables, runs the executor BTA (same flow), and republishes its final implementation deliverables into `pti/outputs/final_deliverables/<implementation files>`. **PTI does NOT run the fixer** — the fixer is the outer Dual's `fixer_inferencer` sibling, not a PTI child.
5. The outer Dual is a pass-through. Its `_active_proposer()` returns EITHER base PTI OR fixer PTI (never both). **Task root sees whichever proposer ran**: base PTI's deliverables if review passed, or fixer PTI's deliverables if review triggered the fixer. There is no `fixer/` subfolder at the task root — the fixer REPLACES the base, it does not appear alongside.

No layer ever sees deeper than its immediate child boundaries.

---

## 3. Code & Data Model

### 3.1 The single new attribute on `InferencerBase`

The ONLY thing that goes on `InferencerBase` is a single boolean flag:

```python
# Whether this inferencer is a Deliverable Boundary (see deliverable
# boundary semantics in agent_foundation/_docs/deliverable_boundaries.md).
# When True, the inferencer guarantees that its outputs/final_deliverables/
# is the canonical artifact set visible to its immediate parent boundary.
# Subclasses set their own default; users may override via YAML or kwargs.
is_deliverable_boundary: bool = attrib(default=False)
```

**Rationale for putting only the flag here, not the policy fields:**

The flag is the only thing that needs to be **uniformly queryable across all
inferencers** — generic helpers (e.g. `collect_child_boundary_deliverables`)
must be able to ask `getattr(child, "is_deliverable_boundary", False)` on any
child reference without isinstance gymnastics or duck-typing fallbacks. That
is the clean justification for `InferencerBase`.

The per-boundary *policy* fields (namespace strategy, conflict strategy,
collect filter) are **only ever read inside the finalize logic of a specific
flow inferencer subclass** (BTA, PTI, etc.). They are not queried generically
across the framework. Putting them on `InferencerBase` would impose unused
attribs on every simple inferencer (`OpenAIInferencer`, `ClaudeCodeCli`, …)
for no benefit. So they live **directly on the subclasses that use them**
(see §3.7).

Mixins (e.g. `DeliverableBoundaryMixin`) were considered and explicitly
rejected: they would add MRO complexity and attrs ordering friction without
extracting any shared **behavior** — the surfacing logic in each flow
inferencer's `_finalize_response` is meaningfully different (BTA does
`by_child_name`, PTI does `by_role`, Dual does pass-through-of-active-proposer).
What is shared is the **helper-function call**, which already lives in
`deliverable_boundary.py` (§3.3) as free functions. There is no shared
behavior to extract into a mixin.

### 3.2 New convenience properties on `InferencerWorkspace`

```python
@property
def has_deliverables(self) -> bool:
    """True iff use_final_deliverables_folder is enabled AND deliverables_dir
    exists on disk AND is non-empty. The non-empty check (added v1.3) prevents
    spurious 'I have deliverables' signals from a directory that was created
    by ensure_dirs() but never written into."""
    d = self.deliverables_dir
    return bool(d and os.path.isdir(d) and os.listdir(d))

def deliverable_paths(self, *, recursive: bool = False) -> List[str]:
    """List of files (rel paths) under deliverables_dir."""
    ...
```

### 3.3 New module: `agent_foundation/common/inferencers/deliverable_boundary.py`

Contains the canonical helpers. The actual file-copy step is delegated to the lower-level `InferencerWorkspace.surface_outputs_from()` primitive (introduced in Phase 0; see §8). The helpers here add the boundary discovery + namespacing + conflict policy on top.

**Helper signatures (v1.5 — clarified per Issue 8):**

```python
def collect_child_boundary_deliverables(
    parent_workspace: InferencerWorkspace,
    parent_inferencer: Optional[InferencerBase] = None,
    *,
    boundary_filter: Callable[[str, InferencerWorkspace], bool] = lambda name, ws: True,
) -> List[ChildBoundaryDeliverables]:
    """Collect deliverables from immediate child boundaries.

    Boundary detection cascade:
      1. If parent_inferencer is provided, walk its direct child inferencer
         attribs and check each for `is_deliverable_boundary=True` (in-process,
         primary signal).
      2. Otherwise (or as fallback for resume scenarios), walk
         parent_workspace.children_dir on disk, treating any subdir whose
         outputs/final_deliverables/ exists AND is non-empty as a boundary.
      3. Either way, NEVER recurse past a boundary — the helper hard-stops
         at the first boundary in each branch (this is the one-boundary-up
         rule from §2.4).

    Returns a list of ChildBoundaryDeliverables, one per discovered boundary
    child that passes `boundary_filter(name, child_workspace)`.
    """

def aggregate_into_self_deliverables(
    parent_workspace: InferencerWorkspace,
    children: List[ChildBoundaryDeliverables],
    *,
    namespace_strategy: NamespaceStrategy = "by_child_name",
    conflict_strategy: ConflictStrategy = "skip_existing",
) -> AggregateReport:
    """Copy collected child deliverables into parent's deliverables_dir,
    namespaced by `namespace_strategy`, with collisions resolved by
    `conflict_strategy`. Delegates per-file copy to safe_copy_per_file."""
```

```python
@dataclass
class ChildBoundaryDeliverables:
    child_name: str               # e.g. "worker_0" or "planner"
    child_workspace_root: str
    deliverable_files: List[str]  # rel to child's deliverables_dir

@dataclass
class AggregateReport:
    copied: List[Tuple[str, str]]    # (src, dst)
    conflicted: List[str]
    skipped: List[str]
```

(Function signatures shown above in the v1.5 helper signatures box.)

### 3.4 Boundary detection on disk

Two equivalent signals (whichever is present):

1. **In-process:** `getattr(child_inferencer, "is_deliverable_boundary", False)` — preferred.
2. **On-disk fallback:** the presence of a `outputs/final_deliverables/` directory in the child's workspace. (For resume scenarios where the in-process object isn't available.)

A `boundary_filter` callable lets callers refine (e.g. only consider `child_name.startswith("worker_")`).

### 3.5 Namespacing strategies

| Strategy | Behavior | Use case |
|---|---|---|
| `by_child_name` (default) | `<deliverables>/<child_name>/<rel>` | Preserves provenance and avoids collisions. |
| `flat` | `<deliverables>/<rel>` | When child names don't matter and aggregator deliberately resolves conflicts. |
| `by_role` | `<deliverables>/<child_role>/<rel>` (e.g. `planner/`, `executor/`) | When children are role-typed (planner/executor). |

### 3.6 Conflict strategies

- `skip_existing` (default): never overwrite a file already published by self (e.g. by aggregator).
- `largest`: keep the largest of multiple candidates.
- `first_wins`: deterministic by sorted child name.
- `error`: raise on collision.

### 3.7a Response-vs-Deliverable disambiguation (the gap both plans missed)
*(Numbered 3.7a so it logically precedes the per-boundary policy details in 3.7 below.)*

> **v1.4 layering correction:** The `publishes_response_as_deliverable` flag introduced in v1.2 lives **only on the flow-inferencer subclasses (BTA, PTI)**, NOT on `InferencerBase`. The sibling plan correctly objected that putting it on `InferencerBase` adds an unused field to every simple inferencer. The compromise keeps the **declarative semantics** (which is the value of the flag) while keeping the field where it's actually used. The boundary helper reads it via `getattr(child, "publishes_response_as_deliverable", False)`.

A subtle but important point: the framework's generic `output.md` is **not always** a deliverable.

- For an **aggregator** that synthesizes a final document, `output.md` IS the deliverable.
- For a **worker** in a multi-flow setup, `output.md` is a per-flow scratch response that the wrapping aggregator then merges.
- For a **review step** (e.g., in Dual), `output.md` is a critique, not a deliverable.

Treating every `output.md` as a publishable deliverable (the sibling plan's implicit assumption) leads to:
- top-level pollution with intermediate scratch files
- name collisions across siblings (3 workers × `output.md` = 2 silently dropped via `skip_existing`)
- conflation of **report** (`aggregation_report.md`), **scratch response** (`output.md`), and **published artifact** (`plan.md`, `implementation.md`)

#### The disambiguation contract

Add a second small flag, declared **on each flow-inferencer subclass that needs it**, NOT on `InferencerBase`:

```python
# On BreakdownThenAggregateInferencer and PlanThenImplementInferencer only:
#
# When True (and is_deliverable_boundary is True), the generic output.md
# written by this inferencer is also auto-published into
# outputs/final_deliverables/<output_path>. When False, output.md stays in
# outputs/ as a report/response only and is NOT a published deliverable.
# Default True for BTA + PTI (their response IS the deliverable).
publishes_response_as_deliverable: bool = attrib(default=True)
```

The boundary helpers query this via `getattr(child, "publishes_response_as_deliverable", False)`. Subclasses that don't declare it (Dual, MFDual, MultiFlow, LWI, all simple API inferencers) get the safe default `False` from the `getattr` fallback.

Subclass defaults:

| Inferencer | `is_deliverable_boundary` | `publishes_response_as_deliverable` | Why |
|---|---|---|---|
| `BreakdownThenAggregateInferencer` | True | True | Aggregator's synthesis IS the deliverable. |
| `PlanThenImplementInferencer` | True | True | Implementer's final output IS the deliverable. |
| Worker (set by BTA's `worker_factory`) | True | False | Worker's `output.md` is per-flow scratch; the wrapping aggregator merges. The worker's own `final_deliverables/` (named files written by tools) is the canonical published set. |
| `DualInferencer` | False | False | Dual is a selector, not a producer. |
| `MFDual`, `MultiFlow`, `LWI` | False | False | Pass-through orchestrators. |

#### Why this matters

This single flag closes the gap that **neither original plan addressed**: it lets each inferencer declare whether its raw response is, in fact, the published artifact. Combined with `is_deliverable_boundary`, it gives the framework enough information to:

1. Auto-publish aggregator/implementer outputs without manual `_finalize_response` extensions
2. Avoid auto-publishing worker scratch outputs as if they were deliverables
3. Let users override per-instance via YAML when their workflow needs different semantics

#### Naming hygiene recommendation

Inferencers whose `publishes_response_as_deliverable=True` SHOULD set a meaningful `output_path` (e.g., `plan.md`, `implementation.md`, `worker_overview.md`) rather than relying on the default `output.md`. The boundary helpers will use `output_path` as the deliverable filename when auto-publishing, preserving identity in collected/aggregated layouts.

### 3.7 Per-boundary policy declaration (lives on each flow inferencer subclass)

Each flow inferencer that is a boundary declares its own policy attribs
**directly on its own class** — no mixin, no shared base. The helpers in
`deliverable_boundary.py` accept these as ordinary function arguments; they
do not depend on any shared base class beyond reading
`is_deliverable_boundary` on children.

`BreakdownThenAggregateInferencer`:

```python
# BTA is always a boundary by default.
is_deliverable_boundary: bool = attrib(default=True)
# Worker outputs are namespaced by child name to preserve provenance.
deliverable_namespace_strategy: str = attrib(default="by_child_name")
deliverable_conflict_strategy: str = attrib(default="skip_existing")
# Default filter: only direct children whose name matches "worker_*".
deliverable_collect_filter: Callable = attrib(
    default=lambda name, ws: name.startswith("worker_")
)
```

`PlanThenImplementInferencer`:

```python
# PTI is always a boundary by default — its implementation document is
# the canonical published artifact.
is_deliverable_boundary: bool = attrib(default=True)
# Children are role-typed; use role subfolders in the deliverables tree.
deliverable_namespace_strategy: str = attrib(default="by_role")
deliverable_conflict_strategy: str = attrib(default="skip_existing")
# Filter uses SHORT workspace names from _CHILD_DEFAULTS, NOT the long
# attrib names. Verified against `_setup_iteration_children` which calls
# `iter_ws.child(short_name)`. Workspace dirs are:
#   children/planner/   children/executor/   children/analyzer/
# NOT planner_inferencer/, etc.
#
# Note: in the driver YAML, the outer Dual has its own fixer_inferencer
# which is a separate PTI sibling — NOT a child of the base PTI. So PTI's
# filter does not include "fixer".
deliverable_collect_filter: Callable = attrib(
    default=lambda name, ws: name in ("planner", "executor", "analyzer")
)
```

`DualInferencer`, `MultiFlowInferencer`, `MultiFlowDualInferencer`,
`LinearWorkflowInferencer` — these are **not** boundaries by default and
declare no policy attribs; their finalize logic just consults the flag on
children when surfacing.

**Why this layering is simpler than a mixin:**

- Mixins are for shared *behavior*, not just shared *fields*. The fields
  above happen to have the same names, but their **defaults differ per
  subclass** (BTA → `by_child_name`, PTI → `by_role`). attrs already
  makes per-subclass defaults trivial.
- attrs + multiple inheritance has known friction (attrib ordering,
  `kw_only`, MRO collisions). Adding a mixin would buy theoretical elegance
  while costing real complexity.
- Free functions in `deliverable_boundary.py` provide all the genuine code
  reuse; the orchestrator-specific finalize logic stays where the rest of
  each orchestrator's logic lives.

---

## 4. Hook integration into existing inferencers

### 4.1 `BreakdownThenAggregateInferencer`

`_finalize_response` (already exists) is extended to:
1. **Publish self:** Copy `aggregator_inferencer/outputs/` → `self/outputs/final_deliverables/` (existing behavior, refined).
2. **Collect children:** Walk `children_dir` for boundary children using the boundary filter (default: `child_name.startswith("worker_")`).
3. **Aggregate:** Call `aggregate_into_self_deliverables` with `by_child_name` namespace.
4. **Republish:** Already done — `self/outputs/final_deliverables/` is now ready.

`promote_worker_deliverables` becomes the legacy alias for `is_deliverable_boundary=True + flat namespace`.

### 4.2 `PlanThenImplementInferencer`

PTI extends its existing `_finalize_outputs` method (NOT `_finalize_response`; correction in v1.3) to perform the boundary work:
1. **Collect:** Inspect planner / executor / analyzer child workspaces using the boundary filter (string-match the SHORT names from `_CHILD_DEFAULTS`: `planner`, `executor`, `analyzer`). PTI does NOT have a `fixer` child — fixer is outer Dual's sibling, not PTI's child.
2. **Aggregate:** Use namespace `by_role` so deliverables land under `pti/outputs/final_deliverables/{planner,executor[,analyzer]}/`. The driver YAML doesn't enable analyzer, so typically only `planner/` and `executor/` appear.
3. **Publish self:** PTI's own implementation document → `pti/outputs/final_deliverables/implementation.md` (auto-published when `publishes_response_as_deliverable=True`; see §3.7a).

### 4.3 `MultiFlowDualInferencer` (MFDual) — deliberately NOT a boundary

MFDual is a parallel propose-and-review wrapper. It extends `DualInferencer` and uses a `MultiFlowInferencer` (which is itself a BTA subclass) as its `base_inferencer`. So in Dual's propose step, the base_inferencer IS the MultiFlow/BTA — not a separate object MFDual "delegates to". When MFDual is itself a worker (boundary=True via BTA's worker_factory), Dual's pass-through finalize step (§4.4) surfaces its active proposer's (= MultiFlow/BTA's) deliverables into MFDual's own `final_deliverables/`, which the parent BTA then collects.

If a worker is implemented as a bare MFDual (not wrapped in another inferencer), then MFDual must be promoted to a boundary at construction time by BTA's worker_factory wiring (`worker.is_deliverable_boundary = True`).

### 4.4 `DualInferencer`

Dual is **not** a boundary by default. It is a pass-through that selects between proposers and forwards the active proposer's deliverables.

**Important correction (v1.4):** `DualInferencer` does NOT have built-in winner-tracking. The `consensus_tracker` reference in v1.0 was inaccurate. The correct primary signal is `ConsensusIterationRecord.counter_feedback`, which is `None` when the fixer did NOT run and populated when it did (verified at `dual_inferencer.py:891`). The on-disk fixer-workspace check is a resume-only fallback.

```python
def _active_proposer(self):
    """Return the inferencer whose deliverables represent Dual's effective output.

    Primary signal (in-process): the last ConsensusIterationRecord in
    self._pending_state's attempt_record. If counter_feedback is non-None,
    the fixer ran in that iteration and is authoritative.

    Fallback signal (resume / out-of-process): if no in-process state is
    available (e.g., resume from checkpoint), fall back to checking whether
    fixer's workspace has a non-empty outputs/ directory.

    Default: base_inferencer.
    """
    # Primary: in-process iteration records
    state = getattr(self, "_pending_state", None) or {}
    attempt_record = state.get("attempt_record", {})
    iterations = attempt_record.get("iterations", []) if attempt_record else []
    if iterations:
        last_iter = iterations[-1]
        if getattr(last_iter, "counter_feedback", None) is not None:
            return self.fixer_inferencer

    # Fallback: on-disk inspection (resume scenarios)
    fixer = self.fixer_inferencer
    if fixer is not None:
        fixer_ws = getattr(fixer, "_workspace", None)
        if fixer_ws and (
            fixer_ws.has_deliverables
            or (os.path.isdir(fixer_ws.outputs_dir) and os.listdir(fixer_ws.outputs_dir))
        ):
            return fixer

    return self.base_inferencer
```

Then Dual's `_finalize_response`:
- Calls `_active_proposer()`.
- If the active proposer `is_deliverable_boundary`, calls `surface_boundary_deliverables(parent_ws=self._workspace, child_ws=active._workspace)` to copy its `final_deliverables/` into Dual's own `final_deliverables/`.
- Dual itself remains `is_deliverable_boundary=False`. The pass-through is what makes its parent's `Collect` step see the right deliverables.

For v1.3, we copy. (Symlinks deferred.)

### 4.5 `LinearWorkflowInferencer`

Linear is **not** a boundary. Its output is its last step's output. If a step is itself a boundary, linear surfaces that step's deliverables.

---

## 5. Backward compatibility

### 5.1 Default behavior preservation

- All `is_deliverable_boundary` defaults are `False`, **except** for BTA, PTI, and worker roots created by BTA's worker_factory (which auto-set `True`).
- All existing tests continue to pass: they don't check boundary semantics.
- Existing `promote_worker_deliverables=True` callers continue to work; the new mechanism subsumes them.

### 5.2 Migration path

| Today | After v1 |
|---|---|
| `use_final_deliverables_folder: true` only | Same flag still required to enable the deliverables directory |
| `promote_worker_deliverables: true` | Becomes a thin shim — equivalent to the new default for BTA |
| Callers reading `child/outputs/final_deliverables/` | Same path, same semantics, but now with cleaner provenance subfolders |

### 5.3 Opt-out

Any inferencer can disable the new behavior with:
```yaml
# In YAML:
is_deliverable_boundary: false
# (no other flags needed; turning off the boundary makes the rest moot)
```

For workspace-level opt-out, just omit `use_final_deliverables_folder: true` (today's behavior; see §11.5 E6 for the graceful no-op contract).

---

## 6.5 Why we keep `outputs/final_deliverables/` (and reject "outputs/ = deliverables")

The sibling plan (`swirling-discovering-pnueli.md`) proposes a different model:

> "outputs/ IS the deliverables folder. artifacts/ holds everything intermediate. No outputs/final_deliverables/ subdirectory for new workflows. Keep use_final_deliverables_folder for backward compatibility."

This was carefully considered and **explicitly rejected** for v1.2 of this plan. Here is the reasoning, recorded so future readers can re-evaluate if circumstances change.

### Reasons to reject "outputs/ = deliverables"

#### R1 — It conflates three distinct artifact classes
A flow inferencer's `outputs/` already contains:
- **Reports** like `aggregation_report.md` — useful, but not the deliverable itself
- **Raw response scratch** like `output.md` — sometimes the deliverable, sometimes not (see §3.7a)
- **Published deliverables** like `plan.md`, `implementation.md` — the named artifacts users want

Treating `outputs/` as "the deliverables folder" forces these three classes to share a namespace, with no way to tell them apart from outside the inferencer.

#### R2 — It loses provenance under multi-worker fan-out
With 3 workers each writing `output.md`, the sibling plan's `surface_outputs_from(skip_existing=True)` keeps only **one** of them at the parent level — the other two are silently dropped. Inferencer-by-inferencer reasoning becomes lossy.

`outputs/final_deliverables/workers/worker_{0,1,2}/...` (this plan's `by_child_name` strategy) preserves all three with provenance intact.

#### R3 — It creates a two-convention codebase
`role_setup` and `create_role` already use `outputs/final_deliverables/` deliberately to separate published artifacts (skills, tools) from generic output files (intermediate reports). The sibling plan's "drop final_deliverables for new workflows" leaves the codebase with two coexisting conventions:
- old workflows: deliverables in `outputs/final_deliverables/`
- new workflows: deliverables in `outputs/`

That fragmentation is **worse than the status quo**: future readers must know which workflow they're inspecting before they can interpret the directory layout.

#### R4 — It defeats the point of `use_final_deliverables_folder`
The flag was added precisely so the framework could distinguish "this is the published artifact set" from "this is generic response/report output." Folding everything into `outputs/` undoes that distinction.

#### R5 — It encourages deep bubbling, which we explicitly want to avoid
Without a separate deliverables folder + the boundary mechanism, the natural impulse is to surface every child's `outputs/` upward at every layer. In a 6-deep topology like the driver, this means `output.md` from every intermediate layer ends up at the top, polluting the root. The boundary contract (§2.4) is what prevents this.

### Reasons to **adopt** parts of the sibling plan anyway

The sibling plan **caught two real bugs** in `InferencerWorkspace` that this plan originally missed. They are NOT philosophical disagreements — they are bugs that prevent the existing `use_final_deliverables_folder` mechanism from working end-to-end. They are integrated as **Phase 0** in §8 below.

The sibling plan also introduces a low-level utility `surface_outputs_from(child_ws)` that is **useful as a primitive** under the boundary helpers — it becomes the implementation of "copy this child boundary's deliverables into self's deliverables space." It is integrated into `deliverable_boundary.py` (§3.3).

### What we keep

- **`outputs/final_deliverables/`** — the published-artifact channel (kept).
- **`outputs/`** — reports + raw responses (kept; clarified in §3.7a).
- **`artifacts/`** — intermediates (kept).
- **One-boundary-up surfacing** (this plan's principle, kept).
- **Provenance-preserving namespace strategies** (kept).

### What we adopt from the sibling plan

- **Phase 0 bug fixes** for `InferencerWorkspace.child()` and `ensure_dirs()` (see §8 Phase 0).
- **`surface_outputs_from()`** as a low-level helper module function (see §3.3).

---

## 6. Driver topology end-to-end behavior (v1)

For `breakdown_multiflow_plan_then_implement.yaml` with `use_final_deliverables_folder: true` enabled at the outer Dual workspace:

### Step-by-step
1. **Worker_i (MFDual)** runs. Its inner BTA's aggregator writes to `worker_i/children/base_inferencer/children/aggregator/outputs/output.md`.
2. **Worker_i `_finalize_response`** copies the aggregator output to `worker_i/outputs/final_deliverables/<filename>` (filename derived from `output_path` or default `<worker_name>.md`).
3. **Plan BTA `_finalize_response`** runs:
   - Aggregator's own output → `plan_bta/outputs/final_deliverables/plan.md` (plus aggregation_report stays in `outputs/`).
   - Walk children: detects `worker_0/`, `worker_1/`, `worker_2/` are boundaries.
   - Collect & aggregate with `by_child_name` → `plan_bta/outputs/final_deliverables/workers/worker_{0,1,2}/<...>`.
4. **Planner Dual** is a pass-through; it surfaces its active proposer's (the BTA's) deliverables to `planner_dual/outputs/final_deliverables/...`.
5. **PTI** runs planner, then executor (it does NOT run fixer — fixer is outer Dual's sibling). PTI finalizes:
   - Aggregates planner / executor with `by_role` → `pti/outputs/final_deliverables/{planner,executor}/...`.
   - Publishes self's implementation summary at `pti/outputs/final_deliverables/implementation.md`.
6. **Outer Dual** is a pass-through. Its `_active_proposer()` returns either base PTI OR fixer PTI:
   - **If review passed → base PTI is active.** Task root sees:
     ```
     task/outputs/final_deliverables/
       implementation.md          (base PTI's own)
       planner/...                (from base PTI's planner BTA)
       executor/...               (from base PTI's executor BTA)
     ```
   - **If review triggered the fixer → fixer PTI is active (REPLACES base).** Task root sees:
     ```
     task/outputs/final_deliverables/
       implementation.md          (fixer PTI's own — REPLACES base's)
       planner/...                (from fixer PTI's planner BTA)
       executor/...               (from fixer PTI's executor BTA)
     ```
   - There is NEVER a `fixer/` subfolder at the task root. Fixer replaces base; it does not appear alongside.

Compared to today's situation (worker output trapped at `worker_0/children/base_inferencer/children/aggregator/outputs/output.md` and never reaching anywhere visible), this is dramatically clearer.

---

## 7. Detailed file-by-file changes

### 7.1 New files

| Path | Purpose |
|---|---|
| `AgentFoundation/src/agent_foundation/common/inferencers/deliverable_boundary.py` | New module with **helpers, dataclasses, and strategy enums only** — no class hierarchy, no mixin. Pure free functions. |
| `AgentFoundation/src/agent_foundation/_docs/deliverable_boundaries.md` | Reference doc for users. |
| `OpenStartup/test/openteam/resources/tools/task/preflight/test_deliverable_boundary_semantics.py` | Preflight test for the driver YAML — verifies boundary detection + planned namespacing structure. |
| `AgentFoundation/test/agent_foundation/common/inferencers/test_deliverable_boundary.py` | Unit tests for `collect_child_boundary_deliverables` + `aggregate_into_self_deliverables`. |

### 7.2 Modified files

| Path | Change |
|---|---|
| `AgentFoundation/src/agent_foundation/common/inferencers/inferencer_base.py` | Add **only** the `is_deliverable_boundary: bool = attrib(default=False)` attrib. No other changes here. |
| `AgentFoundation/src/agent_foundation/common/inferencers/inferencer_workspace.py` | Add `has_deliverables`, `deliverable_paths`. |
| `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/breakdown_then_aggregate_inferencer.py` | Subclass default `is_deliverable_boundary=True`; add subclass-local `deliverable_namespace_strategy` (default `by_child_name`), `deliverable_conflict_strategy`, `deliverable_collect_filter`, `direct_surface_single_worker` (default `False`), `publishes_response_as_deliverable` (default `True`). **EXTEND** (do NOT rewrite) `_finalize_response` with a post-step that collects worker boundaries via the new helpers. `promote_worker_deliverables` becomes a back-compat shim. |
| `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/plan_then_implement_inferencer.py` | Subclass default `is_deliverable_boundary=True`; add subclass-local `deliverable_namespace_strategy` (default `by_role`) + matching collect filter; add finalize step for role-based aggregation. |
| `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/multi_flow_dual_inferencer.py` | Constructor exposes `worker_is_boundary` (default True) so BTA's worker_factory marks workers as boundaries. **No new policy fields here** — MFDual itself is not a boundary. |
| `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/dual_inferencer.py` | Subclass default `is_deliverable_boundary=False`; finalize copies winning proposer's deliverables when proposer is a boundary. **No new policy fields.** |
| `OpenStartup/test/openteam/resources/tools/task/configs/breakdown_multiflow_plan_then_implement.yaml` | (Already has `use_final_deliverables_folder: true` at outer workspace.) Add inline comments documenting boundary placement. |

**No mixin class, no MRO changes, no shared base beyond `InferencerBase` for the flag.**

---

## 8. Implementation phases

### Phase 0 — Foundational bug fixes (adopted from sibling plan; ship before Phase 1)

These are **real bugs in the existing `InferencerWorkspace`** that prevent the current `use_final_deliverables_folder` mechanism from working end-to-end. They are independent of the boundary semantics and should land first as low-risk fixes that the rest of this plan builds on.

1. **`InferencerWorkspace.child()` propagates `use_final_deliverables_folder`.**
   Today, `child()` constructs a child workspace with **default flags**, dropping `use_final_deliverables_folder` from the parent. That means deeply-nested children silently lose the flag and their `deliverables_dir` is `None`. Fix:
   ```python
   def child(self, name: str) -> "InferencerWorkspace":
       self._validate_child_name(name)
       return InferencerWorkspace(
           root=os.path.join(self.children_dir, name),
           use_final_deliverables_folder=self.use_final_deliverables_folder,
       )
   ```
2. **`InferencerWorkspace.ensure_dirs()` creates `deliverables_dir` when the flag is set.**
   Today, `ensure_dirs()` creates `outputs/`, `artifacts/`, `children/`, etc., but NOT `outputs/final_deliverables/`. That means even with the flag on, the directory may not exist when the inferencer tries to write into it. Fix: append a single `os.makedirs(self.deliverables_dir, exist_ok=True)` at the end of `ensure_dirs()`.
3. **Add `surface_outputs_from(child_ws, *, skip_existing=True)`** as a low-level utility on `InferencerWorkspace`. This is the building block used inside the boundary helpers (§3.3) for the actual file-copy step. Pure utility; no boundary semantics by itself.
4. **Add focused unit tests** in `test_workspace_propagation.py`:
   - `test_child_propagates_use_final_deliverables_folder`
   - `test_ensure_dirs_creates_deliverables_dir`
   - `test_surface_outputs_from_copies_tree_with_skip_existing`
5. **Run the full test suite — 100% green** required (no behavior regression for existing callers).

These fixes are necessary but **not sufficient** for the deliverable-surfacing problem. They make the existing `final_deliverables/` directory actually work end-to-end; the boundary semantics in Phase 1+ then build the publication and propagation contract on top.

### Phase 1 — Foundation (no behavior change)
1. Add `is_deliverable_boundary: bool = attrib(default=False)` to `InferencerBase`. **Only the flag — no policy fields, no mixin.**
2. Add `has_deliverables`, `deliverable_paths` to `InferencerWorkspace`.
3. Create `deliverable_boundary.py` module with helpers + dataclasses + enums (free functions only — no class hierarchy).
4. Add unit tests for the helpers (no integration changes).
5. Run full test suite — should be 100% green (no behavior change).

### Phase 2 — BTA boundary wiring (EXTEND, NOT REWRITE)

**Critical correction (v1.4):** BTA's existing `_finalize_response` (lines 945-1052) has nuanced behavior that must be preserved:
- `shutil.copytree` for aggregator outputs (line 973)
- `find_conflicting_and_agreed_files` + `safe_copy_per_file` with `skip_existing=True, conflict_fallback="largest"` (lines 1000-1009)
- Pipeline report fallback with multi-format result extraction (lines 1027-1047)
- `_deliverables_copied` flag gating `_finalize_output` (line 1061-1064)

The boundary work must be **added as a post-step** AFTER existing logic, NOT a wholesale replacement.

1. On `BreakdownThenAggregateInferencer`, set subclass default `is_deliverable_boundary=True`.
2. Add subclass-local policy attribs to BTA: `deliverable_namespace_strategy="by_child_name"`, `deliverable_conflict_strategy="skip_existing"`, `deliverable_collect_filter=lambda name, ws: name.startswith("worker_")`, `publishes_response_as_deliverable=True` (subclass-only, see §3.7a).
3. Add subclass-local optimization flag: `direct_surface_single_worker: bool = attrib(default=False)` (see edge case E1 in §11.5).
4. **EXTEND** (do NOT rewrite) `_finalize_response` with a post-step that:
   - Collects child boundaries (`worker_*`)
   - Aggregates them with `by_child_name` namespace into `self._workspace.deliverables_dir`
   - Uses the existing `safe_copy_per_file` + `find_conflicting_and_agreed_files` for the file-copy step
   - Writes to the SAME `deliverables_dst` already used by existing logic
5. Set `worker.is_deliverable_boundary = True` in `_build_subgraph_spec` immediately after `worker._workspace = worker_ws` (line 1419).
6. **Backward-compat contract for `promote_worker_deliverables` (Issue 4 fix):** Setting `BTA.is_deliverable_boundary=True` as the new default would naively start promoting workers, changing existing semantics where most BTAs use `promote_worker_deliverables=False`. The mechanism is preserved by the §11.5 E6 graceful no-op rule: the boundary mechanism only ACTIVATES when `use_final_deliverables_folder=True` on the workspace. Existing BTAs without that flag get a no-op (back-compat preserved); `role_setup` and other consumers that DO set the flag get the new behavior. Map `promote_worker_deliverables` → equivalent to forcing boundary behavior even without the flag (for explicit opt-in).
7. Add focused unit test: BTA correctly publishes self + collects children + namespaces by child name + preserves existing aggregator/promote behavior.
8. Run all BTA-related tests (incl. role_setup, create_role) — must be 100% green.

### Phase 3 — Worker boundary wiring
1. In BTA's `_build_subgraph_spec`, after creating each worker, set `worker.is_deliverable_boundary = True`.
2. Add focused unit test: workers expose deliverables to parent BTA but their internal children don't leak.

### Phase 4 — PTI migration
1. On `PlanThenImplementInferencer`, set subclass default `is_deliverable_boundary=True`.
2. Add subclass-local policy attribs to PTI: `deliverable_namespace_strategy="by_role"`, `deliverable_conflict_strategy="skip_existing"`, `deliverable_collect_filter=lambda name, ws: name in ("planner", "executor", "analyzer")` (SHORT names from `_CHILD_DEFAULTS`; PTI has no `fixer` child — that's outer Dual's sibling).
3. Add PTI finalize step: collect planner/executor/analyzer with `by_role` namespace via the helpers.
4. Add focused unit test for PTI.

### Phase 5 — Dual + LWI surfacing
1. `Dual._finalize_response` copies winning proposer's deliverables (if proposer is a boundary).
2. `LinearWorkflowInferencer` surfaces last step's deliverables (if last step is a boundary).
3. Focused unit tests for both.

### Phase 6 — Driver topology integration
1. Run the preflight test for `breakdown_multiflow_plan_then_implement.yaml` — verify expected boundary structure.
2. Run the full PAI integration test — verify task root sees consolidated `outputs/final_deliverables/`.

### Phase 7 — Documentation & polish
1. Write `agent_foundation/_docs/deliverable_boundaries.md` with diagrams.
2. Update YAML driver config comments.
3. Add a worked example to AgentFoundation README pointing at the driver topology.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **R1.** Copy storms in deeply nested topologies (many small files copied at every boundary). | Use the existing `safe_copy_per_file` (skip-existing). Log per-boundary copy stats. Optionally support symlinks in v2. |
| **R2.** Name collisions between worker outputs. | `by_child_name` namespace strategy is the default. Conflict log + `skip_existing` fallback. |
| **R3.** Boundary at the wrong layer (e.g., MFDual marked boundary instead of worker root). | Tests assert: per-inferencer-class default + topology preflight. |
| **R4.** Backward compat regression for `promote_worker_deliverables` callers. | Phase 2 explicitly maps the old flag. CI runs the full role_setup / create_role test suite. |
| **R5.** Naïve recursion past a boundary. | The collect helper hard-stops at any child marked as a boundary; documented + tested. |
| **R6.** Workspace not configured (`use_final_deliverables_folder=False`). | Boundaries gracefully fall back to copying into `outputs/` (today's behavior); logged. |
| **R7.** Mid-run failure leaves partial deliverables. | The mechanism is idempotent (existing `_finalize_response` design). Reruns reproduce the same destination. |

---

## 10. Open questions

| # | Question | Proposed answer |
|---|---|---|
| Q1 | Should `Dual` ever be a boundary by itself? | No. It always selects from proposers; let the winning proposer be the boundary. Re-evaluate if a use case emerges. |
| Q2 | Should worker boundary status be set by BTA programmatically, or by user YAML? | BTA sets a default (True). YAML can override. |
| Q3 | What happens if two boundaries publish the same filename across siblings? | `by_child_name` namespacing avoids this for default cases. For `flat`, conflict strategy decides. |
| Q4 | Should the aggregator's own response (`aggregation_report.md`) be a deliverable too? | No — keep it in `outputs/` as a report. Promote only files in `outputs/final_deliverables/` of children. |
| Q5 | What about LinearWorkflow steps that are boundaries? | Surface only the **last** step's deliverables (the linear pipeline's product), unless explicitly configured otherwise. |
| Q6 | Should deliverable paths be tracked in a manifest file (e.g. `outputs/final_deliverables/MANIFEST.json`)? | Optional v2. Useful for downstream tooling but not required for correctness. |
| Q7 | Why not just use `outputs/` for everything (sibling plan's proposal)? | Rejected for v1.2 — see §6.5 for the full reasoning (5 reasons). Short version: it conflates report / scratch / deliverable into one namespace, loses provenance under fan-out, and creates a two-convention codebase (existing `role_setup` already uses `final_deliverables/`). |

---

## 11.5 Edge cases (NEW v1.4 — explicit safety analysis)

The sibling plan correctly enumerated several edge cases that v1.0–v1.3 covered only implicitly. Documenting them explicitly:

### E1 — Single-worker BTA → optional `direct_surface_single_worker` optimization

**Finding:** BTA has no fast-path for the single-worker case. When breakdown returns 1 subtask, the aggregator still runs. For 1 worker, this is wasteful and can transform/lose deliverables that the aggregator was never meant to mediate.

**Solution:** new BTA attrib `direct_surface_single_worker: bool = attrib(default=False)`. When `True` AND `len(sub_queries) == 1`:
- Skip aggregator construction in `_build_subgraph_spec`
- Mark `self._single_worker_mode = True`
- In `_finalize_response`, surface the single worker's `final_deliverables/` directly as BTA's deliverables (no aggregator merging)
- Write the worker's text response to `outputs/aggregation_report.md` for debugging

**Default `False` for back-compat.** Opt-in per BTA instance via YAML.

**Acceptance:** AC10 (added in v1.4 changelog).

### E2 — Empty breakdown (0 subtasks) → already safe

When breakdown returns 0 subtasks:
- `_build_subgraph_spec` is never called (BTA returns at line 1763-1764)
- `promote_worker_deliverables` safely skips (line 996 checks `os.listdir(src)`)
- `_finalize_response` writes empty pipeline report as fallback

**No code change needed.** Add a regression test asserting this behavior is preserved with the boundary mechanism enabled.

### E3 — Worker produces no deliverables → already safe

In existing `_finalize_response` (line 996): `if os.path.isdir(src) and os.listdir(src):` filters out empty directories. The boundary `collect_child_boundary_deliverables` MUST do the same — skip children with empty `deliverables_dir` (verified by unit test).

### E4 — MFDual as worker → inner deliverable chain

When MFDual is a worker (boundary=True via BTA's worker_factory):
1. Inner MultiFlowInferencer (which extends BTA) has its own aggregator
2. BTA's `_finalize_response` copies aggregator output → BTA's deliverables_dst
3. DualInferencer's `_finalize_response` copies last round artifact → MFDual's outputs/
4. **Without v1.4:** MFDual (as Dual) only copies the text artifact, not the inner BTA's deliverables tree
5. **With v1.4:** Dual's extended `_finalize_response` calls `_active_proposer()` → returns base_inferencer (the inner BTA) → calls `surface_boundary_deliverables` → MFDual's `final_deliverables/` now contains the inner BTA's full deliverables tree

This is a complete fix, no special MFDual handling needed.

### E5 — Fixer is a PTI (boundary within boundary)

In the driver topology, the **outer Dual's `fixer_inferencer`** is a PTI (boundary=True). It is a SIBLING of the base PTI, NOT a child of it. When the fixer runs:
1. Fixer PTI runs its own plan-then-execute cycle (it's a complete PTI replica of base)
2. Fixer PTI publishes to `fixer_inferencer/outputs/final_deliverables/{planner/, executor/, implementation.md}`
3. Outer Dual detects fixer ran (via `_active_proposer` checking `counter_feedback`)
4. Outer Dual's pass-through finalize calls `surface_boundary_deliverables(parent_ws=outer_dual_ws, child_ws=fixer_ws)`
5. **Result at task root:** the fixer PTI's deliverables tree REPLACES base PTI's. Task root sees `final_deliverables/{planner/, executor/, implementation.md}` — but the contents come from fixer, not base.

There is NEVER a `final_deliverables/fixer/` subfolder at the task root. Fixer replaces base via Dual's `_active_proposer()` selection — they don't coexist.

The boundary framework handles this naturally via the pass-through contract. **No special handling needed.**

### E6 — Workspace without `use_final_deliverables_folder` → graceful no-op

If the workspace is configured WITHOUT `use_final_deliverables_folder`:
- `deliverables_dir` is `None`
- `has_deliverables` returns `False`
- `collect_child_boundary_deliverables` returns empty list
- `aggregate_into_self_deliverables` is a no-op
- Existing `outputs/` behavior is preserved unchanged

**Critical:** The boundary mechanism MUST gracefully no-op in this case to preserve back-compat. A WARNING log is emitted: "boundary mechanism inactive — workspace not configured for final_deliverables".

---

## 11. Acceptance criteria

- [ ] **AC0.** *(v1.7 NEW — Phase 0)* `InferencerWorkspace.child()` correctly propagates `use_final_deliverables_folder` to child workspaces; `ensure_dirs()` creates `outputs/final_deliverables/` when the flag is set; `surface_outputs_from()` primitive exists and copies per-file safely. Verified by Phase 0 unit tests in `test_workspace_propagation.py` and `test_workspace_surface_outputs.py`.
- [ ] **AC1.** `is_deliverable_boundary` attrib exists on `InferencerBase`; default `False`.
- [ ] **AC2.** `BTA` and `PTI` default to `True`; workers wired by BTA default to `True`.
- [ ] **AC3.** `collect_child_boundary_deliverables` stops at every child boundary (verified by unit test with a 3-deep stub topology).
- [ ] **AC4.** Driver topology preflight test passes: simulating a run produces `task/outputs/final_deliverables/{planner,executor}/...` (when review passes) OR the same shape with fixer PTI's contents (when fixer runs — fixer REPLACES base via outer Dual's `_active_proposer`, so there is no `fixer/` subfolder); per-worker subfolders are present at each BTA layer.
- [ ] **AC5.** Existing `role_setup` and `create_role` tests pass unchanged.
- [ ] **AC6.** Backward compat: `promote_worker_deliverables: true` still works.
- [ ] **AC7.** Logs include one INFO line per boundary copy event with src/dst counts.
- [ ] **AC8.** `agent_foundation/_docs/deliverable_boundaries.md` exists with at least one worked example.
- [ ] **AC9.** *(v1.3 NEW — most important)* Sophisticated mock topology test (§12.5) wires up a faithful stub of `breakdown_multiflow_plan_then_implement.yaml` using real flow inferencers + `MockBoundaryInferencer` leaves, and asserts all 18 semantic propagation rules (S1–S18) PLUS the 4 negative-test anti-pattern assertions in §12.5.6. Test runtime < 5 seconds. **This test is the structural-correctness regression gate for the boundary mechanism.**
- [ ] **AC10.** *(v1.4 NEW)* `direct_surface_single_worker: bool = attrib(default=False)` on BTA, when enabled AND breakdown returns 1 subtask, skips aggregator construction and surfaces the single worker's `final_deliverables/` directly as BTA's deliverables. Verified by unit test.
- [ ] **AC11.** *(v1.4 NEW)* Dual's `_active_proposer()` correctly identifies fixer when `ConsensusIterationRecord.counter_feedback` is non-None in the last iteration; falls back to base when it's None. Verified by unit test using a stub iteration record.
- [ ] **AC12.** *(v1.4 NEW)* The §12.5 mock topology test ALSO supports the **YAML-loading variant** (§12.5.7) — loads the real `breakdown_multiflow_plan_then_implement.yaml`, applies post-instantiation leaf substitution with `DeliverableStubInferencer`, runs the full orchestration, and asserts the deliverable tree at the task root. This catches YAML wiring + Hydra interpolation bugs that pure in-process construction cannot.

---

## 12. Test plan (skeleton)

### 12.1 Helper-level unit tests (`test_deliverable_boundary.py`)
- Discover boundaries from a stub workspace tree (in-process attr + on-disk dir).
- Aggregate with `by_child_name` — preserves subfolders.
- Aggregate with `flat` — flattens, applies conflict strategy.
- Aggregate with `by_role` — uses role-name subfolders.
- Conflict strategies: `skip_existing`, `largest`, `first_wins`, `error`.
- `boundary_filter` correctly excludes non-matching children.
- Idempotent reruns.

### 12.2 Per-inferencer integration tests
- BTA: workers as boundaries; aggregator publishes; parent collects.
- PTI: by_role aggregation of planner/executor (PTI has no fixer child — fixer is outer Dual's sibling).
- Dual: winning proposer's deliverables surface.
- LWI: last-step boundary surfaces.

### 12.3 Topology preflight
- Mock a tiny version of `breakdown_multiflow_plan_then_implement.yaml` with single-step inferencers; assert:
  - boundary detection at every expected layer
  - `task/outputs/final_deliverables/` final layout matches the spec in §6
  - **no** files leak from inside a child boundary's `children/` tree to the task root

### 12.4 Real PAI integration (end-to-end)
- Re-run the PAI codebase-understanding integration test.
- Assert: `task/outputs/final_deliverables/` is non-empty.
- Assert: at least one worker's deliverable file is present under `final_deliverables/workers/worker_*/...` at the BTA layer.

### 12.5 Sophisticated mock topology test (NEW v1.3 — addresses gap in BOTH original plans)

> **Why this is the most important test in the plan.** It is the only test that exercises the *composition* of `is_deliverable_boundary` flags across a deeply nested, real topology — without burning hours on a real LLM run.
>
> Both the v1.0/v1.1/v1.2 plan and the sibling plan listed only:
> - per-helper unit tests
> - per-orchestrator integration tests
> - "rerun the real PAI integration"
>
> Neither plan provided a way to *prove* that the surfacing semantics work end-to-end **before** spending compute on a real run. The mock topology test fills that gap.

#### 12.5.1 Test fixture: `MockBoundaryInferencer`

A minimal stub inferencer that:
- Does no real LLM work
- Writes a single named file (`<name>.md`) into its own `outputs/final_deliverables/` if `is_deliverable_boundary=True` and `publishes_response_as_deliverable=True`
- Optionally writes a fixed list of "named tool artifacts" (e.g., `worker_<i>_overview.md`, `cross_cutting.md`) into its own `final_deliverables/` to simulate tool-call output
- Returns a deterministic `InferenceResponse`
- Records every method call into a per-instance `audit_log`

This is enough to drive every flow inferencer's finalize logic without touching a real LLM.

#### 12.5.2 Topology: a faithful stub of `breakdown_multiflow_plan_then_implement.yaml`

Wire up the real `PlanThenImplementInferencer`, `BreakdownThenAggregateInferencer`, `MultiFlowDualInferencer`, and `DualInferencer` with `MockBoundaryInferencer` leaves:

```python
def make_mock_topology(workspace_root: Path) -> DualInferencer:
    """Faithful stub of breakdown_multiflow_plan_then_implement.yaml.

    Topology (CORRECTED to match actual YAML):
      outer Dual (pass-through; sibling fixer)
        ├── base_inferencer = PTI (boundary)
        │   ├── planner Dual (pass-through)
        │   │   └── plan BTA (boundary)
        │   │       ├── worker_0 = MFDual (boundary; produces worker_0_plan.md + 2 named files)
        │   │       ├── worker_1 = MFDual (boundary; produces worker_1_plan.md + 2 named files)
        │   │       └── worker_2 = MFDual (boundary; produces worker_2_plan.md + 2 named files)
        │   └── executor BTA (boundary; BARE BTA, no Dual wrap)
        │       ├── worker_0 = Dual (boundary; produces exec_worker_0.md)
        │       └── worker_1 = Dual (boundary; produces exec_worker_1.md)
        └── fixer_inferencer = PTI (boundary; sibling of base PTI; produces fixer_implementation.md)
            └── (fixer PTI's own internal planner/executor BTAs)
    """
    ...
```

Key fixture properties:
- All inferencers configured with `workspace=InferencerWorkspace(root=..., use_final_deliverables_folder=True)`
- All real flow inferencers (PTI, BTA, MFDual, Dual) — these are the system under test
- All leaves are `MockBoundaryInferencer`
- Topology is built **in-process**, no YAML loading, no Hydra — direct Python construction so the test is fast (<3s) and stable

#### 12.5.3 Semantic assertions (the heart of the test)

After `await topology.ainfer(...)`, assert each of these end-to-end propagation rules:

| # | Assertion | What it proves |
|---|---|---|
| **S1** | `worker_0/outputs/final_deliverables/worker_0_plan.md` exists | Worker publishes its own deliverable |
| **S2** | `plan_bta/outputs/final_deliverables/workers/worker_0/worker_0_plan.md` exists | BTA collects worker deliverables with `by_child_name` namespacing |
| **S3** | `plan_bta/outputs/final_deliverables/workers/worker_{0,1,2}/` all exist | Provenance preserved across all 3 workers (no silent drops) |
| **S4** | `plan_bta/outputs/final_deliverables/plan.md` exists | BTA aggregator publishes its own synthesis |
| **S5** | `planner_dual/outputs/final_deliverables/workers/worker_0/worker_0_plan.md` exists | Planner Dual is a pass-through — surfaces BTA's deliverables intact |
| **S6** | `pti/outputs/final_deliverables/planner/workers/worker_0/worker_0_plan.md` exists | PTI uses `by_role` namespacing; planner subtree appears under `planner/` |
| **S7** | `pti/outputs/final_deliverables/executor/workers/worker_0/exec_worker_0.md` exists | Executor's deliverables also surfaced under `by_role` namespace |
| **S8** *(rewritten v1.6)* | When `_active_proposer` returns BASE: `fixer_inferencer/outputs/final_deliverables/fixer_implementation.md` exists in fixer's own workspace BUT does NOT propagate to task root (because Dual surfaces the active proposer only). When `_active_proposer` returns FIXER: `task/outputs/final_deliverables/implementation.md` content matches fixer's tag, NOT base's. | Fixer is outer Dual's sibling proposer — Dual REPLACES (not aggregates) base with fixer. There is NO `task/.../fixer/` subfolder. |
| **S9** | `pti/outputs/final_deliverables/implementation.md` exists | PTI publishes its own response as deliverable (`publishes_response_as_deliverable=True`) |
| **S10** | `task/outputs/final_deliverables/planner/workers/worker_2/worker_2_plan.md` exists | Outer Dual pass-through surfaces full PTI tree to task root |
| **S11** *(rewritten v1.6)* | After a fixer-triggered run: `task/outputs/final_deliverables/planner/workers/worker_0/...` exists with content from FIXER's planner BTA (NOT base PTI's). Verified by file content tag match. | Fixer REPLACES base; the planner subtree at task root comes from whichever proposer (`_active_proposer`) won. |
| **S12** | `task/outputs/final_deliverables/implementation.md` exists | PTI's published response reaches task root |
| **S13** | NO file `output.md` from any deep child appears under `task/outputs/final_deliverables/` (other than as namespaced) | One-boundary-up rule prevents pollution |
| **S14** | NO file from `worker_0/children/.../some_internal_file.md` appears at task root | Boundaries hard-stop the upward walk |
| **S15** | Three workers each writing different deliverables → all 3 sets present at BTA level (no skip_existing collisions on distinct names) | Naming hygiene works |
| **S16** | Re-running the topology produces idempotent output (same files, no duplicates) | Idempotency contract |
| **S17** | A worker that publishes a file named `output.md` does NOT collide with sibling workers' `output.md` due to `by_child_name` | Critical collision-prevention test |
| **S18** | Audit log shows `_finalize_response` called once per BTA, once per Dual, once per PTI; no double-finalize | Hooks fire at the right times |

#### 12.5.4 Test file

Create `OpenStartup/test/openteam/resources/tools/task/preflight/test_deliverable_boundary_topology_mock.py`. Estimated test runtime: < 5 seconds. **This test is the regression gate** — if it breaks, the boundary semantics broke.

#### 12.5.5 Why a mock test is sufficient (and necessary)

The mock topology covers **structural correctness**: are the boundary semantics composing right across PTI / BTA / MFDual / Dual nesting? That's a finite, testable property.

What the mock does NOT cover (and doesn't need to, because §12.4 covers it):
- Real LLM output content quality
- Real worker execution time
- Network/API failures
- Cache/streaming behaviors

Combining §12.5 (structural correctness, fast) + §12.4 (real-world content quality, slow) gives full confidence. Either alone is insufficient.

#### 12.5.6 Negative tests (anti-patterns we explicitly prevent)

Add a parallel `test_deliverable_boundary_topology_mock_negative.py` that asserts the boundary mechanism *prevents* known footguns:

| Anti-pattern test | Assertion |
|---|---|
| Worker's internal child writes random file → does NOT appear at task root | Boundary hard-stop |
| Two workers write `notes.md` → both survive (under namespace), neither silently dropped | No silent drops |
| BTA workspace WITHOUT `use_final_deliverables_folder` → boundary mechanism gracefully no-ops; existing `outputs/` behavior preserved | No regression in opt-out mode |
| `is_deliverable_boundary=False` on what would otherwise be a boundary → its children's deliverables do NOT propagate (parent treats it as opaque) | Flag is authoritative |

#### 12.5.7 Real-YAML variant (NEW v1.4 — strengthened from sibling plan)

**Why this matters:** §12.5.1–12.5.6 build the topology in-process. That tests structural correctness but NOT YAML wiring, Hydra interpolation, or `_target_` resolution. The real-YAML variant catches these bugs.

**Approach:** post-instantiation leaf substitution against the actual driver YAML.

```python
# OpenStartup/test/openteam/resources/tools/task/preflight/test_deliverable_boundary_e2e.py

from omegaconf import OmegaConf
from rich_python_utils.config_utils import instantiate

YAML_PATH = "OpenStartup/test/openteam/resources/tools/task/configs/breakdown_multiflow_plan_then_implement.yaml"


class DeliverableStubInferencer(InferencerBase):
    """Stub leaf inferencer that writes a tagged deliverable file.

    Used by post-instantiation leaf substitution to drive the entire
    boundary mechanism without touching real LLMs.
    """
    tag: str = attrib(default="stub")

    def _infer(self, inference_input, inference_config=None, **kwargs):
        if self._workspace:
            # Write to outputs/ (response/report channel)
            os.makedirs(self._workspace.outputs_dir, exist_ok=True)
            with open(self._workspace.output_path(f"{self.tag}_response.md"), "w") as f:
                f.write(f"# Response from {self.tag}\n{str(inference_input)[:200]}")

            # Write to final_deliverables/ (published artifact channel)
            if self._workspace.deliverables_dir:
                os.makedirs(self._workspace.deliverables_dir, exist_ok=True)
                with open(self._workspace.deliverable_path(f"{self.tag}_deliverable.md"), "w") as f:
                    f.write(f"# Deliverable from {self.tag}\n{str(inference_input)[:200]}")

        return f"Response from {self.tag}"


def _substitute_leaves(inferencer, path="root"):
    """Walk topology tree, replace leaf inferencers with DeliverableStubInferencer.

    A leaf is an inferencer with no inferencer-typed child attributes.

    v1.7 IMPLEMENTATION NOTE (M5 fix): Use each flow inferencer's existing
    `_iter_child_inferencers()` method (e.g., `BTA._iter_child_inferencers()`
    at breakdown_then_aggregate_inferencer.py:1066) rather than inventing a
    parallel attr-discovery mechanism. Falls back to walking attrs.fields()
    for inferencers without that method.
    """
    # Prefer the existing _iter_child_inferencers if defined; fall back to
    # attrs.fields() introspection for plain InferencerBase subclasses.
    if hasattr(inferencer, "_iter_child_inferencers"):
        children_iter = list(inferencer._iter_child_inferencers())
    else:
        from attr import fields
        children_iter = [
            (f.name, getattr(inferencer, f.name, None))
            for f in fields(type(inferencer))
            if isinstance(getattr(inferencer, f.name, None), InferencerBase)
        ]

    for attr_name, child in children_iter:
        if child is None:
            continue
        child_path = f"{path}.{attr_name}"
        if _is_leaf_inferencer(child):
            stub = DeliverableStubInferencer(tag=child_path.replace(".", "_"))
            setattr(inferencer, attr_name, stub)
        else:
            _substitute_leaves(child, child_path)


@pytest.mark.preflight
def test_real_yaml_topology_deliverable_surfacing(tmp_path, monkeypatch):
    """Load REAL YAML, stub leaves, verify deliverable tree at task root.

    v1.7 ENV NOTE (M6 fix): instantiate(cfg) resolves _target_ classes,
    which can cause leaf inferencer __init__ to fail if it requires LLM
    backends (API keys, subprocess paths). To prevent that:
      1. Set BMP_DEFAULT_INFERENCER=ClaudeCodeCLI (the cheapest leaf to construct)
      2. monkeypatch any subprocess.run / API-key checks the leaf inferencer
         performs at construction time (none expected for ClaudeCodeCLI but
         document any new requirements here as the YAML evolves).
      3. The leaf substitution happens AFTER instantiate but BEFORE infer,
         so the real LLM is never invoked.
    """
    # 0. Pre-flight env scaffolding (M6 fix)
    monkeypatch.setenv("BMP_DEFAULT_INFERENCER", "ClaudeCodeCLI")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-test-key-not-used")  # never invoked

    # 1. Load with reduced sizes for fast test
    cfg = OmegaConf.load(YAML_PATH)
    OmegaConf.update(cfg, "_params.plan_max_breakdown", 2)
    OmegaConf.update(cfg, "_params.exec_max_breakdown", 2)
    OmegaConf.update(cfg, "_params.flow_max_dynamic_steps", 1)
    OmegaConf.update(cfg, "_params.consensus_max_iterations", 0)  # No fixer round
    os.environ["DUAL_WS"] = str(tmp_path / "ws")

    topology = instantiate(cfg)

    # 2. Substitute leaves
    _substitute_leaves(topology)

    # 3. Run
    result = topology.infer("Write a small document about testing")

    # 4. Assert boundary structure at task root
    ws = topology._workspace
    assert ws.has_deliverables, "Task root should have deliverables"

    deliverables = ws.deliverable_paths()
    # PTI uses by_role → planner/, executor/ subfolders (NO fixer/ subfolder
    # at task root: fixer is outer Dual's sibling, not a PTI child; if fixer
    # ran, its deliverables REPLACE base's at task root via Dual pass-through)
    assert any("planner" in p for p in deliverables), \
        f"Should surface planner deliverables. Got: {deliverables}"
    assert any("executor" in p for p in deliverables), \
        f"Should surface executor deliverables. Got: {deliverables}"

    # No internal workspace paths should leak
    for p in deliverables:
        assert "children" not in p, f"Internal path leaked: {p}"


@pytest.mark.preflight
def test_real_yaml_fixer_surfaces_when_fix_runs(tmp_path):
    """When fixer runs, its deliverables (NOT base's) reach task root."""
    cfg = OmegaConf.load(YAML_PATH)
    OmegaConf.update(cfg, "_params.consensus_max_iterations", 1)  # Trigger fixer
    # ... force fixer to run ...
    # Assert: task_root/outputs/final_deliverables/ contains fixer's tagged file
```

**Why this is strictly stronger than §12.5.1–12.5.6 alone:**
- Catches Hydra interpolation bugs (e.g., `${_params.default_inferencer}` resolution)
- Catches `_target_` resolution bugs
- Catches workspace propagation bugs through the real construction path
- Catches policy-default override bugs in YAML
- Catches the case where a YAML-defined inferencer has unexpected boundary defaults

---

### 12.5.8 Additional test gaps closed (v1.7 — T1–T8 from second-pass review)

The v1.5 + v1.6 mock topology + YAML test caught most issues. Second-pass review identified 8 additional gaps. Tests added:

| ID | Test name | What it proves |
|---|---|---|
| **T1** | `test_concurrent_worker_completion_preserves_provenance` | Worker_0 finishes 5s after worker_1 — both deliverables still surface to plan BTA correctly. Uses staggered `asyncio.sleep` in mock leaves. |
| **T2** | `test_error_conflict_strategy_raises_on_collision` | BTA configured with `conflict_strategy="error"` + two workers writing same filename → raises `DeliverableConflictError`. |
| **T3** | `test_files_directly_written_to_parent_deliverables_are_detected` | Negative test: parent inferencer writes `unauthorized.md` straight into its own `deliverables_dir` (bypassing the boundary mechanism). The audit walk in §12.5 should detect this as an unauthorized write and fail the test. Prevents future maintainers from "shortcuts" that bypass the boundary contract. |
| **T4** | `test_boundary_copy_emits_info_log` (caplog) | Asserts AC7: every boundary copy event emits one INFO line with src/dst counts. |
| **T5** | `test_real_pai_integration_assertions_strengthened` | Tightens §12.4: assert minimum file count (>=10), assert `by_role` substructure exists, assert NO `children/` path component leaks into `final_deliverables/`. Replaces previous weak "non-empty" check. |
| **T6** | `test_aggregate_report_fields_populated` | Calls `aggregate_into_self_deliverables` with a controlled mix of new + conflicting + skipped files; asserts `report.copied`, `report.conflicted`, `report.skipped` all match expected. |
| **T7** | `test_use_final_deliverables_folder_propagates_to_grandchildren` | `ws.child("a").child("b")` — verify the flag propagates 2 levels deep. Strengthens Phase 0 AC0. |
| **T8** | `test_each_boundary_deliverables_dir_populated_exactly_once` | Replaces fragile S18 method-call-count assertion with a stronger filesystem invariant: every boundary's `deliverables_dir` has files written exactly once per topology run (no duplicate writes). |

These tests live in:
- T1, T7: `AgentFoundation/test/agent_foundation/common/inferencers/test_workspace_propagation.py`
- T2, T4, T6: `AgentFoundation/test/agent_foundation/common/inferencers/test_deliverable_boundary.py`
- T3, T8: `OpenStartup/test/openteam/resources/tools/task/preflight/test_deliverable_boundary_semantics.py`
- T5: `OpenStartup/test/openteam/resources/tools/task/test_pai_codebase_understanding.py` (existing integration test, strengthened assertions)

## 13. Estimated effort

| Phase | Effort |
|---|---|
| **Phase 0 (foundational bug fixes adopted from sibling plan)** | **0.5 day** |
| Phase 1 (foundation: boundary flag + helpers) | 0.5 day |
| Phase 2 (BTA migration) | 1 day |
| Phase 3 (worker boundary wiring) | 0.5 day |
| Phase 4 (PTI migration) | 1 day |
| Phase 5 (Dual + LWI) | 0.5 day |
| Phase 6 (driver topology integration + preflight) | 0.5 day |
| Phase 7 (docs + polish) | 0.5 day |
| **Total** | **~5 days** of focused engineering |

Phases 0 and 1 are very low risk and can land independently. Phase 0 alone makes role_setup-style workflows more robust (the `child()` propagation bug currently affects nested role_setup runs).

---

## 14. Decision summary (the elegant rule, restated)

> **Each orchestration boundary owns one canonical deliverables directory. Deliverables propagate exactly one boundary hop per collect-aggregate cycle: a child boundary's `outputs/final_deliverables/` is the only thing its immediate parent boundary sees and republishes. Non-boundary inferencers (Dual pass-through, LWI pass-through) forward their active child's deliverables transparently — they do NOT count as a hop. So a deeply nested deliverable still reaches the root, but only by being explicitly re-published at every boundary it passes through; non-boundary layers add no namespacing and trigger no aggregation logic.**

**Concrete example (clarification per M2 feedback v1.7):** A worker_0 deliverable in the driver topology traverses 5 layers (worker → plan BTA → planner Dual → PTI → outer Dual → task root) but only 3 boundary hops (worker → plan BTA, plan BTA → PTI, PTI → task root). The 2 Dual layers are pass-through and do not introduce new namespacing or aggregation — they simply surface their active proposer's deliverables intact.

That single sentence is the architectural contract. Everything else in this plan is the engineering required to make that contract uniformly honored across `PTI / BTA / MFDual / Dual / LinearWorkflow`.

### The minimal layering (revised v1.1)

- **`InferencerBase`** — owns ONE new thing: the boolean flag `is_deliverable_boundary` (default `False`). No policy fields, no mixin.
- **`deliverable_boundary.py`** — free functions + dataclasses + enums. No class hierarchy.
- **Each flow inferencer subclass** (BTA, PTI) — declares its OWN per-subclass defaults for `is_deliverable_boundary` (`True` for BTA/PTI) and its OWN policy attribs (namespace strategy, conflict strategy, collect filter). Calls the helpers from its own existing finalize method.

This keeps the surface area small, avoids attrs+mixin friction, and concentrates surfacing complexity where it naturally belongs (each orchestrator's finalize logic).

---

## 15. Appendix — Glossary

- **Boundary** — an inferencer with `is_deliverable_boundary=True`; the canonical artifact root for its subtree.
- **Publish** — write own artifacts into self's `outputs/final_deliverables/`.
- **Collect** — gather child boundaries' deliverables (one level only, no recursion past boundaries).
- **Aggregate** — merge collected deliverables into self's deliverables space (with namespace + conflict strategies).
- **Republish** — ensure self's `outputs/final_deliverables/` is the authoritative parent-visible artifact set.
- **Surfacing** — the upward propagation of deliverables exactly one boundary at a time.
- **Namespace strategy** — how to subfolder collected child deliverables (`by_child_name`, `flat`, `by_role`).
- **Conflict strategy** — how to resolve same-named files (`skip_existing`, `largest`, `first_wins`, `error`).
- **Sibling plan** — `swirling-discovering-pnueli.md`, the alternative "outputs/ = deliverables" proposal whose foundational bug fixes are integrated as Phase 0 (see §8) and whose `surface_outputs_from()` utility is integrated into `deliverable_boundary.py` (see §3.3), but whose folder-conflation philosophy is explicitly rejected (see §6.5).

---

## 16. Cross-plan comparison & merge log

This section records the integration analysis between this plan and the sibling plan (`/Users/tchen7/.claude/plans/swirling-discovering-pnueli.md`) so future readers can understand what was integrated, what was rejected, and why.

### 16.1 Plans compared

| Aspect | Sibling plan | This plan (v1.2) |
|---|---|---|
| **Length** | ~190 lines, focused | ~600 lines, comprehensive |
| **Philosophy** | "outputs/ IS deliverables; surface every child's outputs/ up the tree" | "Deliverable Boundary semantics; surface one boundary up at a time, with provenance" |
| **Folder model** | Drop `final_deliverables/` for new workflows | Keep `outputs/final_deliverables/` distinct from `outputs/` |
| **Mechanism** | One utility `surface_outputs_from()` + 2 hook insertions (Dual, PTI) | `is_deliverable_boundary` flag + free-function helpers + per-subclass policy |
| **Granularity** | Whole `outputs/` tree | Only `outputs/final_deliverables/` content + `output.md` if `publishes_response_as_deliverable=True` |
| **Provenance preservation** | Lost (flat overlay; collisions silently dropped via `skip_existing`) | Preserved (`by_child_name`, `by_role` namespacing) |
| **Conflict handling** | `skip_existing` only | `skip_existing` / `largest` / `first_wins` / `error` |
| **Stops at boundary?** | No (every parent surfaces every child) | Yes (one-boundary-up rule) |
| **Backward compat (role_setup)** | Keeps `use_final_deliverables_folder` for role_setup | Same; existing role_setup unchanged |
| **Implementation effort** | ~half day | ~5 days |
| **Real bugs caught** | 2 (`child()` propagation, `ensure_dirs()` deliverables_dir) | 0 originally; integrated those bugs as Phase 0 |

### 16.2 Sibling plan strengths integrated here

| Sibling plan element | Integrated as | Where |
|---|---|---|
| `child()` propagates `use_final_deliverables_folder` (real bug fix) | Phase 0 step 1 | §8 Phase 0 |
| `ensure_dirs()` creates `deliverables_dir` (real bug fix) | Phase 0 step 2 | §8 Phase 0 |
| `surface_outputs_from(child_ws)` low-level utility | Becomes the file-copy primitive under `aggregate_into_self_deliverables` | §3.3, §8 Phase 0 step 3 |

### 16.3 Sibling plan elements explicitly rejected

| Sibling plan element | Rejection reason | Where documented |
|---|---|---|
| "outputs/ IS deliverables" model | 5 reasons: conflates artifact classes; loses provenance; creates two-convention codebase; defeats the point of `use_final_deliverables_folder`; encourages deep bubbling | §6.5 + Q7 |
| `_last_active_proposer()` heuristic on Dual | Brittle (artifact-count heuristic); replaced in v1.4 by reading `ConsensusIterationRecord.counter_feedback` (in-process primary) with on-disk fixer-workspace check as resume-only fallback. Verified at `dual_inferencer.py:891`. | §4.4 + v1.4 changelog |
| Surfacing every child's full `outputs/` tree at every layer | Causes pollution: 6-deep topology means root receives `output.md` from every layer; replaced by one-boundary-up rule | §2.4 + §6.5 R5 |
| Single hard-coded `skip_existing` conflict policy | Silently drops files; replaced by 4 explicit conflict strategies + namespace strategies | §3.5, §3.6 |

### 16.4 Gaps NEITHER plan originally addressed (now addressed in v1.2)

| Gap | Resolution |
|---|---|
| What does `output.md` *mean* — deliverable or report or scratch? | New flag `publishes_response_as_deliverable` (§3.7a) lets each inferencer declare its own semantics. |
| Naming hygiene (multiple workers writing `output.md`) | Naming hygiene recommendation in §3.7a + `by_child_name` namespacing in §3.5. |
| Iteration-aware surfacing in Dual | §4.4 specifies consulting Dual's winner identity, not artifact-count heuristics. |
| Iteration-aware Dual proposer detection | Implemented in v1.4 §4.4 via `ConsensusIterationRecord.counter_feedback`. No deferred work — `_active_proposer()` is fully specified. |

### 16.5 Honest "if you only had hours" answer

If only half a day is available and the architectural cleanup must wait, the **right minimal action** is:

1. Ship Phase 0 only (the two `InferencerWorkspace` bug fixes + `surface_outputs_from`).
2. Defer Phase 1+ until time is available.

This delivers some immediate improvement (role_setup nested workflows become reliable) without committing to a half-finished surfacing model. The sibling plan's full proposal — wiring `surface_outputs_from()` into Dual and PTI — is **explicitly NOT recommended** as a standalone shippable change because it loses provenance and pollutes the top-level outputs in any non-trivial topology.

### 16.6 Final architectural choice

This plan (v1.2) is the canonical going-forward design. The sibling plan is preserved as a reference of an alternative model that was rejected, with its bug-fix contributions integrated. If circumstances change (e.g., the codebase evolves to favor flat surfacing for some reason), §6.5 records the original rejection reasoning so the decision can be re-evaluated with full context.
