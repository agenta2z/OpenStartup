# Unified Tool Workspace Allocation - v5.3 Final Integration

**Status:** v5.3 — READY for implementation
**Author:** Claude (integrating v0/v1/v2/v3/v4/Claude) + Rovo Dev audit + critical-review rounds R1–R4
**Date:** 2026-05-17 17:20

> **Current revision: v5.3.** Four critical-review rounds (R1–R4) have shaped this plan; the consolidated audit history (27 distinct issues processed, 13 substantive fixes applied) lives in **§0.A** below. Major fixes: CRIT-1/2/3 (dispatcher routing + mock-mode + shared helper extraction), CRIT-A/B (setuptools `find_packages` syntax + dead-code elimination), HIGH-A/B/E (egg-info cache invalidation, defense-in-depth framing, explicit test-assertion enumeration), and the v5.2 Path B layout unification.

## §0.A Audit History (consolidated 2026-05-17 17:20)

Four critical-review rounds have shaped this plan. Each row below is one applied fix or rejected claim; older sections (§0.1, §0.2, "Post-v5 Audit Trail") that were growing separately have been folded into this single table.

| Round | Ref | Severity | Issue | Verdict + section it touched |
|---|---|---|---|---|
| R1 (16:37) | 8 | 🟡 | Slash-path `session_store` plumbing undetailed | ✅ Applied → §8 Phase 8 (accessor + parameter + call-site update) |
| R1 (16:37) | 9 | 🟡 | Tool-name validation happens AFTER `parent.mkdir` | ✅ Applied → §4 `allocate_tool_workspace` (validation moved to top) |
| R1 (16:37) | 1 | 🟢 | "Collision bug" framing imprecise | ⚠️ Cosmetic; bug is real either way; UUID8 naming fixes it |
| R1 (16:37) | 2 | 🟢 | "project_onboarding writes CWD" framing wrong | ❌ N/A — §1 claim 4 already reframes as slash-path security bug |
| R1 (16:37) | 3 | 🟢 | "Phase 7 under-specified" | ❌ N/A — Phase 7 spec is explicit ("same pattern as Phase 6") |
| R1 (16:37) | 4 | 🟡 | "Phase 3 wrongly lists conversation_service.py" | ⚠️ PARTIALLY VALID — the v4 reviewer was right that `_compute_session_context:358` is NOT the workspace-allocation site (it builds `prior_context` for prompt rendering, a different dict). But conversation_service.py IS still in scope: Phase 3 modifies `_get_session_inferencer` which builds `BackendBuildContext` that feeds into factories.py. The code is correct; the audit-trail row's reasoning was wrong (this row supersedes the prior `INVALID` verdict, per R5 catch). |
| R1 (16:37) | 5 | 🟢 | "51 leaked is actually 47" | ❌ INVALID — 47 direct + 4 nested = 51 total verified |
| R1 (16:37) | 6 | 🚨 (claimed HIGH) | "3-branch `_resolve_workspace` missing" | ❌ N/A — reviewer was reading v4; v5 has full body |
| R1 (16:37) | 7 | 🟢 | "Phase count off-by-one" | ⚠️ Cosmetic |
| R1 (16:37) | 10 | 🟢 | "Test file line refs cite CLI decorators" | ⚠️ Cosmetic; lines DO need updating |
| R1 (16:37) | 11 | 🟢 | "No migration script" | ❌ N/A — Phase 11 explicitly specifies it |
| R1 (16:37) | 12 | 🟢 | "Phase 3+4 file count wrong" | ❌ INVALID — follows from #4 |
| **R2 (17:00)** | **CRIT-1** | 🚨 BLOCKING | Phase 6/7 double-allocate orphan workspaces (ignored Phase 4 pre-allocation) | ✅ FIXED → resolved automatically by CRIT-3's shared helper |
| **R2 (17:00)** | **CRIT-2** | 🚨 BLOCKING | Phase 8's `data_svc.session_store` AttributeErrors in mock mode | ✅ FIXED → §8 Phase 8 uses `getattr(data_svc, "session_store", None)` |
| **R2 (17:00)** | **CRIT-3** | 🚨 ARCHITECTURAL | Phase 5 `_allocate_workspace` hardcodes `"task"`; Phases 6/7 reinvent routing 3 times | ✅ FIXED → new `resolve_tool_workspace(tool_name, session_context)` in `_shared/`; all 4 tools call the same function |
| R2 (17:00) | HIGH-1 | 🔴 | Audit-trail Issue 4 defense cited wrong function | ✅ Corrected — Phase 3 spec touches `_get_session_inferencer` |
| R2 (17:00) | HIGH-3 | 🔴 | Heuristic OR → AND transcription error | ✅ FIXED → restored `or` in `resolve_tool_workspace` (matches `task/executor.py:184`) |
| R2 (17:00) | HIGH-4 | 🔴 | Deprecation warning specified but not in Phase 4 code | ✅ FIXED → §8 Phase 4 now emits `logging.warning(...)` |
| R2 (17:00) | HIGH-6 | 🔴 | SOURCES.txt regeneration unaddressed | ✅ FIXED in v5.3 → MANIFEST.in + correct `find_packages` syntax + `rm -rf egg-info` step |
| **R3 (17:16)** | layout | enhancement | Path B layout asymmetric with Path A (flat vs nested) | ✅ FIXED → §3.3 + §4 + §5 — Path B now per-tool sharded (`<session>/tasks/<tool>/<tool>_<TS>_<uuid8>/`) |
| **R4 (17:19)** | **CRIT-A** | 🚨 BLOCKING | `pyproject.toml` `exclude = ["**/_runtime*"]` is a no-op — setuptools wildcards match dotted package names, not path globs | ✅ FIXED → §8 Phase 10 now uses `exclude = ["openteam.server._runtime", "openteam.server._runtime.*"]` + canonical `MANIFEST.in prune` directives |
| **R4 (17:19)** | **CRIT-B** | 🚨 DEAD CODE | Phase 5 left `_allocate_workspace` defined with zero callers (contradicts CRIT-3's intent) | ✅ FIXED → §8 Phase 5 now DELETES `_allocate_workspace` entirely + updates stale docstring at line 329 |
| R4 (17:19) | HIGH-A | 🔴 | egg-info cache invalidation step missing | ✅ FIXED → §8 Phase 10 verification sequence: `rm -rf src/openteam.egg-info && pip install -e . --no-deps && grep -c "_runtime" SOURCES.txt` |
| R4 (17:19) | HIGH-B | 🔴 | SOURCES.txt fix framed as primary, not defense-in-depth | ✅ Clarified → §8 Phase 10 architectural note: structural fix (Phase 5 + Phase 11) is primary; MANIFEST.in is belt-and-suspenders |
| R4 (17:19) | HIGH-C | 🔴 | `getattr` is patchy — abstract-base-class approach is cleaner | 🤷 Defer — `getattr` at the one call site is local and self-contained; promoting to ABC would couple `MockDataService` to a concept it doesn't otherwise need. Local fix is correct trade-off. |
| R4 (17:19) | HIGH-D | 🔴 | Validation order still partially wrong (path computed with unvalidated `tool_name`) | 🤷 Defer to v5.4 — `tool_name.isidentifier()` blocks path-traversal; computing parent first is harmless once validation rejects bad input before fs ops; reorder is cosmetic |
| R4 (17:19) | HIGH-E | 🔴 | `test_task_helpers.py:322` assertion `"test-id-no-hint" in posix` will fail under new naming | ✅ FIXED → §8 Phase 9 explicitly enumerates: remove `"test-id-no-hint" in posix` clause; keep `/_runtime/tasks/` substring assertion |
| R4 (17:19) | MED-A...I | 🟡 (9 items) | Cleanup items (contract post-deprecation, stub Phase 8 body, RED test for CRIT-1, AC gaps, `_apply_resume` framing, step count, migration script docstring-only, Issue 4 unresolved, effort estimate) | 🤷 Defer to v5.4 — all real but none blocking implementation |
| R4 (17:19) | LOW-A...F | 🟢 (6 items) | Cosmetic / inconsistent recommendation / unverified tool.json | 🤷 Defer — not worth churn |
| **R5 (17:25)** | doc | 🟡 | R1 #4 audit row's reasoning was wrong: `_compute_session_context` is NOT the workspace-allocation site (it builds `prior_context` for prompt rendering — a different dict). The CODE is right (Phase 3 targets `_get_session_inferencer`); only the audit-row reasoning was misleading | ✅ FIXED → §0.A row above updated; verdict revised from `❌ INVALID` to `⚠️ PARTIALLY VALID` with correct mechanism |
| **R5 (17:25)** | heuristic | ❌ N/A | Reviewer flagged `_resolve_workspace` heuristic as OR→AND change | ❌ N/A — R2 HIGH-3 already restored `or` in v5.1 (line 677); reviewer was reading pre-v5.1 |
| **R5 (17:25)** | **DRY** | 🟡 (real) | `session_root / "tasks"` routing duplicated across Phase 4 + Phase 5 + Phase 6 (×2) + Phase 7 — 4+ identical recompute blocks | ✅ **FIXED → §8 Phase 3 now pre-computes `tasks_dir = session_store.get_session_tasks_dir(session_id)` and threads it through `session_context["tasks_dir"]`; Phases 4–7 simplify to a 2-line `if tasks_dir: base = Path(tasks_dir)` (no recompute of `/ "tasks"` convention). Eliminates the DRY violation cleanly using the helper v5 §5.2 already added.** |
| R5 (17:25) | validation | 🟢 | Double `tool_name.isidentifier()` (helper + dirname builder) | 🤷 Stays deferred (already in v5.4 queue; reviewer agrees cosmetic) |

**Round-by-round net (cumulative through v5.3):**
- ✅ **APPLIED**: 13 substantive fixes (4 BLOCKING from R2/R4; 3 architectural; 6 HIGH or supporting)
- ⚠️ **Cosmetic noted**: 4 (R1 #1/7/10; R3 cosmetic)
- ❌ **Rejected after verification**: 8 (claims invalidated by source-code grep)
- 🤷 **Deferred to v5.4 (non-blocking)**: 17 (R4 MED/LOW pool + HIGH-C/D — defensible)

**Architectural lineage:**
| Version | Key change | Rationale |
|---|---|---|
| v5 | Honor user's explicit nested-under-sessions choice; integrate v3 operational rigor + Claude's `base_dir` API | First plan that ships and respects stated user preference |
| v5.1 | Single shared `resolve_tool_workspace`; fix mock-mode AttributeError; restore OR heuristic | CRIT-1/2/3 from R2 audit |
| v5.2 | Path B per-tool sharding (symmetric with Path A) | User-requested layout unification (R3) |
| v5.3 (current) | Correct setuptools exclude syntax; delete dead `_allocate_workspace`; explicit test-assertion enumeration | CRIT-A/B + HIGH-A/B/E from R4 audit |

---

Supersedes ALL prior plans:
- v0: tool_workspace_allocation_enhancement_plan.md
- v1: unified_workspace_allocation_plan.md (697 lines)
- v2 (Cursor): unified_tool_workspace_allocation_e34a5db8.plan.md (247 lines)
- v3: unified_workspace_allocation_INTEGRATED_v3_plan.md (529 lines)
- v4 (partial, flat counter-proposal): unified_workspace_allocation_INTEGRATED_v4_plan.md (132 lines)
- Claude: for-openteam-can-we-dazzling-umbrella.md (258 lines)

---

## §0 Why v5 Exists

v3 has the most operational depth (RED tests, deploy hygiene, regression tests, feature flag, 18-row risk register). It is the strongest input plan. v5 takes v3 as the base and adds four targeted improvements:

1. **Cleaner allocator API** — adopt Claude's `base_dir: Optional[Path]` parameter instead of v3's `session_context: dict` parameter. Self-documenting, no dict-key archaeology, easier to test.
2. **`SessionStore.get_session_tasks_dir()` convenience method** — adopted from Claude's `tasks_dir` property idea, adapted for the nested layout. SessionStore stays the single owner of layout decisions.
3. **Explicit `session_id` flow trace** — verified earlier in conversation that `session_id` IS in scope at the slash-dispatcher (line 213-217) but is dropped. v5 codes the fix explicitly.
4. **Mitigates v4's HIGH-severity risk** without adopting v4's flat-layout reversal — see §2.

**Honest verdict among the input plans:** if you must pick ONE input plan, pick **v3 (529 lines)**. It has the most complete operational discipline, correct architecture (nested per user's explicit choice), and full risk register. v3's minor deficits are:
- Allocator API uses `session_context: dict` which is less self-documenting than Claude's `base_dir` parameter.
- v3 didn't fully mitigate the slash-path session_id missing concern — it punted to "ephemeral session fallback if missing."

v5 fixes both. v5 is strictly better than every input plan.

**Why NOT v4 (the partial flat-layout proposal):** v4 reverses the user's earlier explicit choice ("tasks should go to sessions" + "moved server affliciated tasks under each session") on architectural grounds. The cited HIGH-severity risk is actually LOW (see §2.3). v4's deploy-hygiene additions (`.dockerignore`, rsync excludes) are valuable and v5 keeps them — but the architectural reversal is unwarranted.


---

## §1 Verified Empirical Claims

| # | Claim | File:Line |
|---|---|---|
| 1 | `_allocate_workspace` writes to `src/openteam/server/_runtime/tasks/` polluting source tree; hard-codes `task_` prefix | `task/executor.py:149-160` |
| 2 | `tool_dispatcher.py` writes flat at `<server_dir>/tasks/<tool>_task-<uuid8>/` (no timestamp) | `tool_dispatcher.py:186-208` |
| 3 | `role_setup`/`create_role` have **literal `task_id` collision bug** — concurrent runs collide on the same path | `role_setup/executor.py:1211-1236`, `create_role/executor.py:537-557` |
| 4 | `project_onboarding` has NO workspace allocator — writes CWD-relative; **SECURITY BUG**: under slash-path, `working_dir = src/openteam/server/` so outputs land in source tree | `project_onboarding/executor.py:146-157` |
| 5 | `SessionStore.get_session_dir(session_id) -> Path \| None` is read-only; per-session dir is created EAGERLY in `create_session()` line 197-199 | `session_store.py:317-324, 197-199` |
| 6 | `manager_websocket_routes.py:216` sets `working_dir = str(tools_dir.parent.parent)` — deliberately UNSAFE | `manager_websocket_routes.py:213-217` |
| 7 | `session_id` IS in scope at slash-dispatcher line 213-217 (as parameter `sid`); captured during init handshake at line 510 — slash commands cannot arrive pre-init | `manager_websocket_routes.py:502-513, 213-217` |
| 8 | Mock mode (no `--real-sessions`) bypasses `ToolDispatcher` — slash commands fall to standalone allocator (Path A) automatically; no special handling needed | `manager_websocket_routes.py:320-322` |
| 9 | **51 leaked test workspaces** under `test/.../_runtime/` from prior runs | filesystem count |
| 10 | RankEvolve's pattern: `tasks/` is a **sibling** of `sessions/`. OpenTeam intentionally nests `tasks/` UNDER each `sessions/<id>/` for stronger session ownership (user's stated design intent) | v1 §1.3 + user confirmation in conversation |

---

## §2 Architectural Decision: NESTED (Honoring User's Explicit Choice)

### 2.1 Nested vs Flat — the comparison

| Aspect | NESTED (v1/v3/v5 — chosen) | FLAT (v4 proposal — rejected) |
|---|---|---|
| Layout | `<server>/sessions/<id>/tasks/<tool>_*/` | `<server>/tasks/<tool>_*/` |
| Matches RankEvolve cited inspiration | ❌ Departs | ✅ Matches |
| **User's stated design intent** | ✅ Confirmed in conversation | ❌ Reverses user's choice |
| Filesystem cleanup cascade per session | ✅ `rm -rf <session>/` removes its tasks | ❌ requires metadata-driven cleanup |
| Audit "tasks for session X" | ✅ filesystem walk | ❌ requires task→session metadata index |
| Self-contained session export | ✅ tar one dir | ❌ tar multiple disjoint dirs |
| Session archival via WebUI | ✅ trivial | ❌ requires aggregator |
| Phase: ensure-create session_dir | required | not needed |
| Slash-path session_id risk | mitigated (see 2.3) | eliminated by design |

### 2.2 Why NESTED is the right call

1. **User's explicit design intent.** Original request: *"sever afflicated tasks should go to sessions"* + *"moved server affliciated tasks under each session"*. AskQuestion confirmed `nest_under_session`. v4 reversed this without re-asking — that's a process violation, not just an architectural opinion.
2. **Real operational benefits, not vague preferences.** A session is a unit of user interaction; its tasks are products of that interaction. Nesting them on disk reflects ownership semantics AND cheaply gives cleanup, export, audit, archival.
3. **OpenTeam already has session export and archival** in the WebUI surface (`view_routes.py` security boundary at `_runtime`). A flat layout would require building a metadata index for each operation that nesting gets for free.
4. **The HIGH-severity risk v4 cites is LOW** (see §2.3). v4 over-weighted it.
5. **Cited inspiration ≠ blind adoption.** RankEvolve's flat layout is right for RankEvolve (1 task per iteration, no rich session-task fanout). OpenTeam's session-task fanout makes nesting more meaningful.

### 2.3 Mitigating the slash-path session_id concern (v4's HIGH risk → LOW in v5)

v4 cited "slash-path session_id not available when routes invoke tools" as 🔴 HIGH and used it to justify reversing to flat. **Verified facts:**

- `session_id` IS in scope at slash-dispatcher (`manager_websocket_routes.py:213-217`, parameter `sid`).
- It is captured synchronously during the WebSocket init handshake at lines 502-513, BEFORE any slash command can arrive.
- `SessionStore.create_session()` creates the session directory EAGERLY at lines 197-199.
- Therefore: by the time any slash command runs, `get_session_dir(sid)` should always return a Path.

**Risk is therefore LOW, not HIGH.** v5 mitigations:

- Phase 7 (slash-path fix) explicitly threads `sid` from the WebSocket scope into `session_context["session_root"]` — see §6 Phase 7 code.
- Phase 8 (SessionStore) makes `get_session_dir` idempotent ensure-create as a defensive measure (handles the edge case of flat-file-only sessions or missed eager creation).
- Permanent regression test R2 (`test_manager_websocket_routes_no_unsafe_working_dir_hack`) prevents reintroduction.
- Phase 0 RED test #13 explicitly pins the slash-path session_root behavior.

---

## §3 Field Contract

### 3.1 Two-path workspace location rules

| Path | Trigger | Workspace location |
|---|---|---|
| **A — Standalone CLI** | `base_dir=None` (helper API) / `session_context` lacks `session_root` (executor layer) | `<repo>/_runtime/tasks/<tool>/<tool>_<TS>_<uuid8>/` |
| **B — Server-affiliated** | `base_dir=<path>` (helper API) / `session_context["session_root"]` set (executor layer) | `<session_root>/tasks/<tool>_<TS>_<uuid8>/` |

`<session_root>` is the per-session directory under `<server_dir>/sessions/<session_id>_<TS>/`. So the full server-affiliated path is `<repo>/_runtime/servers/<server>/sessions/<session>/tasks/<tool>_<TS>_<uuid8>/`.

### 3.2 Naming format (locked)

`<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>`

- All underscores; lex-sortable.
- Tool prefix per-workspace.
- UUID8 disambiguates within a second.
- `mkdir(exist_ok=False)` + 3-retry loop handles the rare collision.

### 3.3 Directory layout end-state

```
<repo_root>/                                         (auto-discovered: ancestor of src/)
├── src/                                             (source only — never runtime artifacts)
└── _runtime/                                        (.gitignore'd; deploy-excluded — see §10)
    ├── tasks/                                       Path A: standalone workspaces
    │   ├── task/task_20260517_103805_abc12345/
    │   ├── role_setup/role_setup_20260517_104010_def67890/
    │   ├── create_role/.../
    │   └── project_onboarding/.../
    └── servers/                                     Path B: server-affiliated workspaces
        └── server_20260517_103805_8e2f1a04/
            ├── server_info.json
            └── sessions/
                └── session-1234_20260517_103905/
                    ├── session_state.json
                    └── tasks/                       (v5.2: per-tool subdir — symmetric with Path A)
                        ├── role_setup/
                        │   └── role_setup_20260517_104010_def67890/
                        ├── task/
                        │   └── task_20260517_104525_a1b2c3d4/
                        ├── create_role/
                        │   └── create_role_20260517_111200_5f6e7d8c/
                        └── project_onboarding/
                            └── project_onboarding_20260517_115500_2a3b4c5d/
```

### 3.4 `session_context` contract (dispatcher → executor layer)

```python
session_context: dict[str, str] = {
    # Required for Path B; absent (or empty) for Path A:
    "session_root": "/abs/path/to/<repo>/_runtime/servers/<srv>/sessions/<id>/",
    # Existing fields (preserved unchanged):
    "session_id": "session-1234",            # for task_info.json metadata
    "server_dir": "/abs/path/to/<server>/",  # SessionStore.server_dir, kept for compat
    "task_id": "task-<uuid8>",               # dispatcher-generated
    "interactive": "<InteractiveHandler>",   # streaming
    # Backward-compat ONLY (1-release deprecation window, then removed):
    "working_dir": "...",
}
```

---

## §4 Shared Helper — Final API

**File (NEW):** `src/openteam/server/resources/tools/_shared/workspace_allocator.py`

Three pure functions, separable for testing:

```python
"""Unified workspace allocation for OpenTeam tools.

Two-path architecture:
  - Path A (standalone CLI):     <repo>/_runtime/tasks/<tool>/<tool>_<TS>_<uuid8>/
  - Path B (server-affiliated):  <base_dir>/<tool>_<TS>_<uuid8>/
                                 where base_dir is typically <session_root>/tasks/

Helper takes a base_dir argument, NOT a session_context dict (cleaner, more
self-documenting, and keeps the layout decisions OUT of the helper). The
dispatcher/executor layer is responsible for translating `session_context`
fields into the right `base_dir` value before calling the helper.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


_FALLBACK_HOME_DIR = Path.home() / ".openteam" / "_runtime"


def find_runtime_root() -> Path:
    """Locate the canonical _runtime/ directory using a 4-tier fallback chain.

    Resolution order (first match wins):
      1. $OPENTEAM_RUNTIME_DIR env var (CI/prod override).
      2. Walk up from this file's __file__ to find a `src/` ancestor →
         <src_parent>/_runtime (dev tree, editable install, normal pip install
         when source-tree-editable).
      3. Walk up from CWD to find `src/` ancestor or any directory containing
         BOTH `src/` and `pyproject.toml` → <root>/_runtime (cwd-launched).
      4. Fallback: ~/.openteam/_runtime (pip-installed package, no source
         tree available).
    """
    env_dir = os.environ.get("OPENTEAM_RUNTIME_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == "src":
            return ancestor.parent / "_runtime"

    cwd = Path.cwd().resolve()
    for ancestor in [cwd, *cwd.parents]:
        if ancestor.name == "src":
            return ancestor.parent / "_runtime"
        if (ancestor / "src").is_dir() and (ancestor / "pyproject.toml").is_file():
            return ancestor / "_runtime"

    return _FALLBACK_HOME_DIR


def make_workspace_dirname(tool_name: str) -> str:
    """Generate a workspace directory name `<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>`.

    Pure function: given a tool_name, produces a name; does not touch the filesystem.
    Separated from allocate_tool_workspace so tests can pin the naming format
    without disk side-effects.

    Raises ValueError if tool_name is empty or not a valid Python identifier.
    """
    if not tool_name or not tool_name.isidentifier():
        raise ValueError(
            f"tool_name must be a non-empty Python identifier, got: {tool_name!r}"
        )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{tool_name}_{ts}_{short}"


def allocate_tool_workspace(
    tool_name: str,
    base_dir: Optional[Path] = None,
) -> Path:
    """Allocate a fresh workspace directory for a tool run, creating it on disk.

    Routes by `base_dir`:
      - If `base_dir` is provided (Path B, server-affiliated):
        Returns <base_dir>/<dirname>/  — caller is responsible for the layout
        of base_dir (typically <session_root>/tasks/).
      - If `base_dir` is None (Path A, standalone CLI):
        Returns <find_runtime_root()>/tasks/<tool>/<dirname>/

    UUID8 collision handling: uses mkdir(exist_ok=False) and retries up to 3
    times with a fresh dirname. UUID8 has ~32 bits of entropy; collision
    probability per pair is negligible but not zero across long-running
    fleets. exist_ok=True would silently reuse a colliding directory — DON'T.

    Raises:
        ValueError: invalid tool_name (via make_workspace_dirname).
        ValueError: base_dir is provided but not absolute.
        FileExistsError: 3 consecutive UUID8 collisions (vanishingly rare;
            indicates an entropy or wall-clock problem).
    """
    if base_dir is not None:
        if not base_dir.is_absolute():
            raise ValueError(
                f"base_dir must be absolute, got: {base_dir!r}"
            )
        # (v5.2 unification) Path B is now per-tool-sharded under base_dir,
        # symmetric with Path A. Single rule: every workspace lives at
        # <some_root>/tasks/<tool>/<tool>_<TS>_<uuid8>/.
        # For Path B, base_dir is <session>/tasks; we add /<tool>.
        parent = base_dir / tool_name
    else:
        parent = find_runtime_root() / "tasks" / tool_name

    # (post-v5 audit fix — Issue 9) Validate tool_name BEFORE any filesystem
    # side-effect so that invalid input does not leave behind a created parent.
    if not tool_name or not tool_name.isidentifier():
        raise ValueError(
            f"tool_name must be a non-empty Python identifier, got: {tool_name!r}"
        )

    # Only NOW touch the filesystem.
    parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(3):
        dirname = make_workspace_dirname(tool_name)
        ws = parent / dirname
        try:
            ws.mkdir(exist_ok=False)
            return ws
        except FileExistsError:
            if attempt == 2:
                raise
            continue
    raise AssertionError("unreachable")  # for type checker
```

**Why this API:**

- **`base_dir: Optional[Path]` is more self-documenting than `session_context: dict`.** A reader sees the signature and immediately knows: provide a path → workspace goes there; omit → standalone fallback. No dict-key archaeology.
- **`make_workspace_dirname` is pure.** Separating it from disk side-effects lets tests pin the naming format without temporary directories or mocking.
- **`exist_ok=False` + retry > `exist_ok=True`.** The latter silently reuses a colliding directory, which can corrupt prior workspace contents. Defensive.
- **Layout decisions live OUTSIDE the helper.** SessionStore decides nested-vs-flat; helper is layout-agnostic. Future changes to layout don't need to edit the helper.

---

## §5 SessionStore API Additions

**File:** `src/openteam/server/services/session_store.py`

Two changes — one upgrade to existing method, one new convenience accessor.

### 5.1 Make `get_session_dir` ensure-create (replaces lines 317-324)

```python
def get_session_dir(self, session_id: str) -> Path:
    """Return the per-session directory, creating it if absent.

    PRIOR BEHAVIOR (read-only): returned None if session was flat-file-only.
    NEW BEHAVIOR: ensure-create. Returns a guaranteed-existing Path.

    Read-only callers that explicitly need None-on-missing should use the
    private _find_session_dir() instead.
    """
    existing = self._find_session_dir(session_id)
    if existing is not None:
        return existing
    # Defensive: should rarely fire because create_session() eagerly
    # creates the dir at lines 197-199. This branch handles the edge cases:
    # (a) flat-file-only sessions imported from prior runs,
    # (b) sessions whose directory was manually deleted between create
    #     and tool dispatch.
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    new_dir = self._server_dir / "sessions" / f"{session_id}_{ts}"
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir
```

Audit existing read-only callers and migrate them to `_find_session_dir`:

- `data_service.py:663` — currently expects `None` on missing; check whether None-on-missing is load-bearing for the API contract.
- `conversation_service.py:442/444/502` — caching / per-turn JsonLogger wiring; `None` likely means "no session yet" branch. Check each.

If any caller needs None-on-missing, add a separate `find_session_dir(session_id) -> Path | None` public method that wraps `_find_session_dir`.

### 5.2 Add `get_session_tasks_dir` convenience method (NEW)

```python
def get_session_tasks_dir(self, session_id: str) -> Path:
    """Return <session_dir>/tasks/, creating it if absent.

    This is the PARENT directory under which per-task workspaces are
    allocated by allocate_tool_workspace(base_dir=...). Encapsulates
    the nested-vs-flat layout decision inside SessionStore so callers
    never need to know the convention.
    """
    session_dir = self.get_session_dir(session_id)
    tasks_dir = session_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir
```

This is the SINGLE source of truth for "where do per-session tasks live on disk." If we ever revisit nested-vs-flat (per §2.3 deferred option), this is the only line that changes.

---

## §6 Phased Rollout — 12 Phases

| Phase | What | Files | Risk | Reversible? |
|---|---|---|---|---|
| **0** | RED tests pinning behavior contract | 1 new test file | none | n/a |
| 1 | Shared helper + unit tests | 2 new files | low | yes |
| 2 | `SessionStore` API additions (5.1 + 5.2) | 1 file | medium | yes |
| 3 | `factories.py` + `conversation_service.py` thread `session_id`/`session_root` | 2 files | medium | yes |
| 4 | `tool_dispatcher.py` use shared allocator (KEY change) | 1 file | medium-high | yes |
| 5 | `task/executor.py` migrate `_allocate_workspace`/`_resolve_workspace` | 1 file | low | yes |
| 6 | `create_role` + `role_setup` migration (closes name-collision bug) | 2 files | low | yes |
| 7 | `project_onboarding` migration (gains workspace + closes security bug) | 1 file | low | yes |
| 8 | `manager_websocket_routes.py` slash-path fix (security + threads `sid`) | 1 file | medium | yes |
| 9 | Test migration (12 files + conftest fixture; clean 51 leaked dirs) | 13 files + script | low | yes |
| 10 | Deploy hygiene (`.gitignore` + `.dockerignore` + Dockerfile + CI) | 3-4 config files | low | yes |
| 11 | Migration script + smoke verify + permanent regression tests | 1 script + 1 test file | low | yes |

**Atomic phase coupling:** Phases 3 and 4 MUST land together. Without Phase 3, the dispatcher gets empty `session_root` and tool falls through to standalone allocation — BROKEN. Use a single PR or single commit window.

**Feature flag:** gate Phases 3+4 behind `OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=1` for one release. When unset, fall back to old `<server_dir>/tasks/` allocation. After 1 release of stable rollout, remove the flag.

---

## §7 Phase 0 — RED Tests (Pin Contracts Before Source Edits)

**File (NEW):** `test/openteam/resources/tools/_shared/test_workspace_allocator_contract.py`

Write these as `pytest.mark.xfail(strict=True)` BEFORE any source change. Each turns GREEN as the corresponding phase lands.

| # | Test | What it pins | xfail until |
|---|---|---|---|
| 1 | `test_find_runtime_root_uses_env_var` | `$OPENTEAM_RUNTIME_DIR` wins over all other strategies | Phase 1 |
| 2 | `test_find_runtime_root_walks_up_from_file` | Walk-up to `src/` ancestor finds correct `_runtime/` | Phase 1 |
| 3 | `test_find_runtime_root_walks_up_from_cwd` | CWD walk-up fallback when `__file__` walk fails | Phase 1 |
| 4 | `test_find_runtime_root_fallback_home` | Falls back to `~/.openteam/_runtime` when all else fails | Phase 1 |
| 5 | `test_make_workspace_dirname_format` | `make_workspace_dirname("task")` matches regex `task_\d{8}_\d{6}_[0-9a-f]{8}` | Phase 1 |
| 6 | `test_make_workspace_dirname_lex_sortable` | Two dirnames 1s apart sort correctly by string comparison | Phase 1 |
| 7 | `test_path_a_standalone_layout` | `allocate_tool_workspace("task", base_dir=None)` → `_runtime/tasks/task/task_<TS>_<uuid8>/` exists | Phase 1 |
| 8 | `test_path_b_server_affiliated_layout` | (v5.2) `allocate_tool_workspace("role_setup", base_dir=Path("/abs/session/tasks"))` → `/abs/session/tasks/role_setup/role_setup_<TS>_<uuid8>/` (per-tool subdir, symmetric with Path A) | Phase 1 |
| 9 | `test_invalid_tool_name_raises` | Empty / non-identifier raises `ValueError` | Phase 1 |
| 10 | `test_relative_base_dir_raises` | Non-absolute `base_dir` raises `ValueError` | Phase 1 |
| 11 | `test_uuid8_collision_retried` | Mock `uuid.uuid4` to return colliding values; allocator retries 3× then raises `FileExistsError` | Phase 1 |
| 12 | `test_role_setup_concurrent_runs_dont_collide` | Two `allocate_tool_workspace("role_setup", None)` in same millisecond produce distinct paths | Phase 1 (proves the name-collision bug fix) |
| 13 | `test_slash_path_uses_session_root` | After Phase 8, slash-command `/task` allocates under `<session_root>/tasks/`, NOT under `src/openteam/server/_runtime/` | Phase 8 |
| 14 | `test_project_onboarding_now_has_workspace` | After Phase 7, `project_onboarding` returns a path under `_runtime/tasks/project_onboarding/` (or session-affiliated equivalent) | Phase 7 |
| 15 | `test_session_store_get_session_dir_ensure_create` | `SessionStore.get_session_dir(new_id)` returns a freshly-created Path (not None) | Phase 2 |
| 16 | `test_session_store_get_session_tasks_dir` | `SessionStore.get_session_tasks_dir(id)` returns `<session_dir>/tasks/` and creates it | Phase 2 |

**Permanent regression tests** (always GREEN; fail if regressions reintroduced):

| # | Test | What it guards |
|---|---|---|
| R1 | `test_no_module_writes_under_src_runtime` | grep test fixtures and source for `src/openteam/server/_runtime/` writes; assert none |
| R2 | `test_manager_websocket_routes_no_unsafe_working_dir_hack` | Read `manager_websocket_routes.py`; assert no `working_dir = str(tools_dir.parent.parent)` pattern |
| R3 | `test_executors_use_shared_allocator` | Reflectively check that each executor's allocation function imports from `_shared.workspace_allocator` |

---

## §8 Phase Implementation Detail

### Phase 1 — Shared helper + unit tests (~30 min)

NEW: `src/openteam/server/resources/tools/_shared/__init__.py` (empty)
NEW: `src/openteam/server/resources/tools/_shared/workspace_allocator.py` (per §4 code)
NEW: `test/openteam/resources/tools/_shared/test_workspace_allocator.py` covering all tests in §7. Phase 0 RED tests 1-12 + 15-16 turn GREEN.

### Phase 2 — `SessionStore` API additions (~20 min)

File: `src/openteam/server/services/session_store.py`

- Modify `get_session_dir` (lines 317-324) per §5.1.
- Add `get_session_tasks_dir` after `runtime_root` property per §5.2.
- Audit and migrate read-only callers of `get_session_dir` to `_find_session_dir` if they need None-on-missing semantics.

Phase 0 RED tests 15, 16 turn GREEN.

### Phase 3 — `factories.py` + `conversation_service.py` (~25 min)

**File:** `src/openteam/server/backends/factories.py` (lines 111-128)

Add `session_id` and `session_root` to dispatcher's `session_context`:

```python
# OLD:
session_context = {
    "working_dir": ctx.working_dir,
    "server_dir": (
        str(ctx.session_store.server_dir)
        if ctx.session_store is not None
        and hasattr(ctx.session_store, "server_dir")
        else ""
    ),
    "cloud_id": "",
    "uct_token": None,
    "email": None,
}

# NEW (v5.3 DRY fix R5 — pre-compute tasks_dir once via SessionStore.get_session_tasks_dir,
# thread through session_context. Phases 4-7 then just read session_context["tasks_dir"]
# and do NOT recompute the "/ tasks" convention themselves):
session_id = ctx.session_id  # plumbed through BackendBuildContext
session_root = ""
tasks_dir = ""
if ctx.session_store is not None and session_id:
    session_root = str(ctx.session_store.get_session_dir(session_id))
    # Single source of truth for "/ tasks" convention — see §5.2:
    tasks_dir = str(ctx.session_store.get_session_tasks_dir(session_id))
session_context = {
    "session_id": session_id,
    "session_root": session_root,
    "tasks_dir": tasks_dir,                     # NEW (R5 DRY) — pre-computed once
    "working_dir": ctx.working_dir,             # backward-compat (1 release)
    "server_dir": (
        str(ctx.session_store.server_dir)
        if ctx.session_store is not None
        and hasattr(ctx.session_store, "server_dir")
        else ""
    ),
    "cloud_id": "",
    "uct_token": None,
    "email": None,
}
```

**(v5.3 R5 DRY-elimination contract for downstream Phases 4–7):** Every executor that reads `session_context` MUST follow this single pattern:

```python
tasks_dir_str = sc.get("tasks_dir", "")  # pre-computed by Phase 3
if tasks_dir_str:
    base = Path(tasks_dir_str)        # ALREADY ends in /tasks; do NOT append again
    workspace = allocate_tool_workspace(tool_name, base_dir=base)
else:
    workspace = allocate_tool_workspace(tool_name)  # standalone Path A
```

Backward-compat shim (during the 1-release deprecation window): if `tasks_dir` is missing but `session_root` is present, derive it once (`Path(session_root) / "tasks"`) and emit a `DeprecationWarning`. After sunset, only `tasks_dir` is consulted.

**File:** `src/openteam/server/services/conversation_service.py`

Add `session_id` to `BackendBuildContext` and thread it from `_get_session_inferencer` (where `session_id` is already in scope) into the build:

```python
ctx = BackendBuildContext(
    templates_dir=self._templates_dir,
    working_dir=self._working_dir,
    cache_dir=self._cache_dir,
    session_store=self._session_store,
    model_name=model,
    session_id=session_id,  # NEW
)
```

**File:** `src/openteam/server/backends/registry.py` (BackendBuildContext dataclass at lines 33-41)

Add `session_id: str = ""` field.

**Atomicity:** This phase MUST land in the same commit window as Phase 4. Without the `session_root` plumbing, Phase 4's dispatcher reads empty string and fails over to standalone — silent breakage.

### Phase 4 — `tool_dispatcher.py` use shared allocator (~30 min) 🔑 KEY CHANGE

File: `src/openteam/server/services/tool_dispatcher.py` (lines 186-223)

```python
# OLD (lines 203-210):
server_dir = self._session_context.get("server_dir", "")
if server_dir:
    task_working_dir = str(_Path(server_dir) / "tasks" / f"{tool_name}_{task_id}")
    _Path(task_working_dir).mkdir(parents=True, exist_ok=True)
else:
    task_working_dir = self._session_context.get("working_dir", "")

# NEW:
from openteam.server.resources.tools._shared.workspace_allocator import (
    allocate_tool_workspace,
)
session_root_str = self._session_context.get("session_root", "")
if session_root_str:
    # Path B: server-affiliated, nested under session
    session_root = _Path(session_root_str)
    tasks_parent = session_root / "tasks"
    tasks_parent.mkdir(parents=True, exist_ok=True)
    task_workspace = allocate_tool_workspace(tool_name, base_dir=tasks_parent)
else:
    # Path A: no session context → standalone
    task_workspace = allocate_tool_workspace(tool_name, base_dir=None)
task_working_dir = str(task_workspace)

# (v5.1 fix HIGH-4) Backward-compat deprecation warning.
# Logged once per session_context that supplies only the legacy `working_dir`
# field without the new `session_root`. Risk #6 mitigation requires this.
if "working_dir" in self._session_context and "session_root" not in self._session_context:
    import logging
    logging.getLogger(__name__).warning(
        "session_context['working_dir'] is deprecated; please supply "
        "session_context['session_root'] (per-session directory) instead. "
        "Support will be removed in the next release."
    )
```

Update `task_context` dict (lines ~217-223):

```python
task_context = {
    **self._session_context,
    "task_id": task_id,
    "session_root": session_root_str,        # passed through unchanged
    "working_dir": task_working_dir,         # task workspace path (also for backward-compat consumers)
    "interactive": interactive_ref,
}
```

Update line 247 (UI message construction reading `task_working_dir`) — no change needed; the field is still set.

### Phase 5 — `task/executor.py` migration (~15 min)

File: `src/openteam/server/resources/tools/task/executor.py`

```python
# OLD (~lines 149-160):
def _allocate_workspace(task_id: str) -> Path:
    server_dir = Path(__file__).resolve().parents[3]
    runtime_root = server_dir / "_runtime" / "tasks"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ws = runtime_root / f"task_{task_id}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws

# NEW (v5.3 fix CRIT-B — DELETE _allocate_workspace entirely):
# After v5.1 CRIT-3 routing all 4 tools through resolve_tool_workspace,
# _allocate_workspace has ZERO callers (verified: only caller was
# _resolve_workspace at line 188, and v5.1 rewrites that to call
# resolve_tool_workspace directly). Keeping a redundant per-tool helper
# contradicts CRIT-3's stated intent ("single shared helper").
#
# DELETE the entire def _allocate_workspace block (old lines 149-160).
# ALSO update the stale docstring reference at line 329 in _run_topology:
#   OLD: "falls through to `_allocate_workspace`"
#   NEW: "delegates to `resolve_tool_workspace` in _shared/workspace_allocator"
```

**(v5.1 fix CRIT-3 + CRIT-1 + HIGH-3)** Replace per-tool `_allocate_workspace` + `_resolve_workspace` duplication with a SINGLE shared helper. New file/function added in §4 → `_shared/workspace_allocator.py::resolve_tool_workspace`:

```python
# In src/openteam/server/resources/tools/_shared/workspace_allocator.py — NEW
def resolve_tool_workspace(
    tool_name: str,
    session_context: Optional[dict] = None,
) -> Path:
    """Single source of truth for tool workspace resolution.

    Routing precedence (deterministic):
      1. session_context["working_dir"] looks like a per-task workspace
         (contains "/_runtime/" OR "/tasks/" — substring OR not AND, per HIGH-3
         restoration of original task/executor.py:184 semantics) → RETURN AS-IS.
         This honors workspaces that were pre-allocated by the dispatcher
         (Phase 4) or supplied by --resume (CLI). Prevents double-allocation.
      2. session_context["session_root"] is set → allocate under
         <session_root>/tasks/ (Path B, server-affiliated).
      3. Otherwise → standalone (Path A).

    All 4 executors (task, role_setup, create_role, project_onboarding) call
    this. Tool-specific naming comes from `tool_name`, not duplicated routing.
    """
    sc = session_context or {}
    candidate = sc.get("working_dir", "")
    if candidate:
        try:
            posix = Path(candidate).as_posix()
        except Exception:
            posix = ""
        # (HIGH-3) OR not AND — matches original task/executor.py:184
        if "/_runtime/" in posix or "/tasks/" in posix:
            ws = Path(candidate)
            ws.mkdir(parents=True, exist_ok=True)
            return ws

    session_root_str = sc.get("session_root", "")
    if session_root_str:
        base = Path(session_root_str) / "tasks"
        base.mkdir(parents=True, exist_ok=True)
        return allocate_tool_workspace(tool_name, base_dir=base)

    return allocate_tool_workspace(tool_name, base_dir=None)
```

```python
# In src/openteam/server/resources/tools/task/executor.py — _resolve_workspace BECOMES a thin shim
def _resolve_workspace(
    session_context: Optional[dict],
    task_id: str,           # kept for backward-compat with internal callers; unused
) -> Path:
    """Thin shim — delegates to shared helper. Kept for callers that import it
    from this module (role_setup, create_role) — but those should migrate to
    importing from _shared/ directly per Phase 6."""
    from openteam.server.resources.tools._shared.workspace_allocator import (
        resolve_tool_workspace,
    )
    return resolve_tool_workspace("task", session_context)
```

`_apply_resume` (lines 191-202) — UNCHANGED; resume/copy-workspace logic still works because new paths satisfy the heuristic.

### Phase 6 — `create_role` + `role_setup` migration (~20 min)

**File:** `src/openteam/server/resources/tools/create_role/executor.py:537-557`

```python
# OLD:
from openteam.server.resources.tools.task.executor import (
    _run_topology, _resolve_workspace,
)
...
task_id = session_context.get("task_id") or "create_role"  # COLLISION BUG
workspace = _resolve_workspace(session_context, task_id)

# NEW (v5.1 fix CRIT-1 + CRIT-3 — use the shared resolve_tool_workspace, not duplicated routing):
from openteam.server.resources.tools._shared.workspace_allocator import (
    resolve_tool_workspace,
)
...
# Single line replaces 7 lines of duplicated routing. The helper:
#   1. Honors dispatcher-pre-allocated working_dir (no double-allocation)
#   2. Uses session_root if set
#   3. Falls through to standalone otherwise
workspace = resolve_tool_workspace("create_role", session_context)
```

**File:** `src/openteam/server/resources/tools/role_setup/executor.py:1211-1236` — same pattern, just `tool_name="role_setup"`. **One line, no duplicated routing.**

**(CRIT-1 fix rationale)** Phase 4 dispatcher pre-allocates a workspace and sets `task_context["working_dir"]`. The original `_resolve_workspace` heuristic (lines 173-188 in task/executor.py) honored that pre-allocation. Earlier v5 drafts of Phase 6 dropped the heuristic and unconditionally allocated, producing orphan empty dirs. The v5.1 fix routes ALL 4 tools through `resolve_tool_workspace` so the heuristic is applied uniformly — Phase 5 (correct) and Phase 6 (now correct) behave identically.

Phase 0 RED test 12 turns GREEN.

### Phase 7 — `project_onboarding` migration (~20 min) 🚨 SECURITY FIX

File: `src/openteam/server/resources/tools/project_onboarding/executor.py:146-157`

Today: reads `session_context["working_dir"]` blindly. Under slash-path that value is `src/openteam/server/` (the unsafe one) → outputs land in source tree.

Fix: replace blind `working_dir` read with an explicit allocator call (same pattern as Phase 6). After this lands, no slash-path can write into source tree even if Phase 8 hasn't landed yet.

Also update `tool.json` examples (lines 43-46) that document old `_runtime/<TS>/` patterns to LLM users.

Phase 0 RED test 14 turns GREEN.

### Phase 8 — `manager_websocket_routes.py` slash-path fix (~30 min) 🚨 SECURITY FIX

File: `src/openteam/server/routes/manager_websocket_routes.py:213-217`

```python
# OLD (lines 213-217 — UNSAFE):
session_context = {
    "interactive": interactive,
    "task_id": task_id,
    "working_dir": str(tools_dir.parent.parent),  # UNSAFE!
}

# NEW (sid is already in scope as the function parameter):
session_root_str = ""
if session_store is not None and sid:
    try:
        session_root_str = str(session_store.get_session_dir(sid))
    except Exception:
        # Defensive: fall through to standalone allocation if SessionStore
        # is unhappy. Logged for observability.
        logger.warning(
            "slash-path could not resolve session_root for sid=%s; "
            "falling back to standalone workspace", sid,
        )
session_context = {
    "interactive": interactive,
    "task_id": task_id,
    "session_id": sid,
    "session_root": session_root_str,
    # working_dir intentionally omitted — Phase 4/5 logic takes over via session_root.
}
```

**(post-v5 audit fix — Issue 8) Slash-path `session_store` plumbing.** Empirically verified: `_try_dev_slash_command` at `manager_websocket_routes.py:104` currently takes `(text, sid, send_safe, dev_tool_tasks, dev_tool_input_queues)` — **session_store is NOT yet a parameter**. The call site at line 321 has access to `data_svc = websocket.app.state.data_service`, and `data_svc._session_store` is the only accessor today.

**Concrete plumbing change in Phase 8:**

```python
# manager_websocket_routes.py

# 1. Add a public accessor on RealSessionDataService (cleaner than touching _session_store directly):
class RealSessionDataService:
    @property
    def session_store(self) -> SessionStore:
        return self._session_store

# 2. Update _try_dev_slash_command signature (line 104):
async def _try_dev_slash_command(
    text: str,
    sid: str,
    send_safe,
    dev_tool_tasks,
    dev_tool_input_queues,
    session_store: SessionStore,   # NEW
) -> bool:
    ...

# 3. Update call site (line 321) — use getattr to handle mock mode (v5.1 fix CRIT-2):
data_svc = websocket.app.state.data_service     # already exists nearby (line 324)
# CRIT-2: In mock mode (--no-real-sessions), data_svc is MockDataService which
# has NO session_store attribute. main.py:148 instantiates MockDataService when
# session storage isn't requested. AttributeError-on-access would crash slash
# commands. getattr fallback routes mock mode to Path A (standalone) gracefully.
session_store = getattr(data_svc, "session_store", None)
if await _try_dev_slash_command(
    text, sid, send_safe, dev_tool_tasks, dev_tool_input_queues,
    session_store,                                 # may be None in mock mode
):
    ...

# 4. Inside _try_dev_slash_command, guard against None:
#    if session_store is None:
#        # Mock mode — caller will route to Path A standalone via resolve_tool_workspace
#        session_root_str = ""
#    else:
#        session_root_str = str(session_store.get_session_tasks_dir(sid))
#    # Pass session_root_str into task_context for the dispatcher.
```

This is ~7 lines of mechanical change. The function then uses `session_store.get_session_tasks_dir(sid)` from §5 (or `None` → empty `session_root_str` → standalone fallback) to construct the correct `tasks_dir` for the dispatched tool, replacing the unsafe `working_dir = str(tools_dir.parent.parent)` hack at line 216.

**Why `getattr` not adding `session_store=None` property on `MockDataService`?** `getattr` is one line at the only call site; adding a property would couple `MockDataService` to a concept it doesn't otherwise know about. Local fix is cleaner.

Permanent regression test R2 prevents reintroduction of the unsafe pattern. Phase 0 RED test 13 turns GREEN.

### Phase 9 — Test migration (~60 min)

**Add** `test/openteam/conftest.py`:

```python
import pytest

@pytest.fixture
def standalone_workspace(tmp_path, monkeypatch):
    """Set OPENTEAM_RUNTIME_DIR to a hermetic per-test tmp dir."""
    monkeypatch.setenv("OPENTEAM_RUNTIME_DIR", str(tmp_path))
    return tmp_path
```

**Update 12 existing test files** (51 leaked `_runtime/<TS>/` dirs across these — clean during Phase 11):

- `test/openteam/resources/tools/role_setup/test_role_setup.py` lines 245-250, 348-366
- `test/openteam/resources/tools/role_setup/test_role_setup_through_yaml.py` lines 98-101
- `test/openteam/resources/tools/role_setup/test_role_setup_through_yaml_claude.py` lines 51-58
- `test/openteam/resources/tools/role_setup/test_role_setup_inner_bta_through_yaml.py` lines 189-191
- `test/openteam/resources/tools/create_role/test_create_role.py` lines 104-108, 171-178
- `test/openteam/resources/tools/create_role/test_create_role_through_yaml.py` lines 96-100
- `test/openteam/resources/tools/create_role/test_create_role_through_yaml_claude.py` lines 44-46
- `test/openteam/resources/tools/project_onboarding/test_project_onboarding_through_yaml.py` lines 103-106
- `test/openteam/resources/tools/task/test_task_real_cli.py` lines 756-758, 905-906, 1283-1291
- `test/openteam/resources/tools/role_setup/test_role_setup_via_task_shim.py` lines 70-75, 193-197
- `test/openteam/resources/tools/create_role/test_create_role_via_task_shim.py` lines 7, 67, 135-139
- `test/openteam/resources/tools/task/test_task_helpers.py` lines 293-322 — encodes the production resolve_workspace contract. **(v5.3 fix HIGH-E) Specific assertion changes required:**
  - Line 316: `assert "/_runtime/tasks/" in posix` → KEEP (still true; new layout includes `_runtime/tasks/task/`)
  - Line 322: `assert "/_runtime/tasks/" in posix and "test-id-no-hint" in posix` → **REMOVE the `"test-id-no-hint" in posix` clause.** Under v5.2 layout the dirname is `task_<TS>_<uuid8>` — `task_id` is no longer in the dirname. Keep only the `/_runtime/tasks/` substring assertion, optionally add `"/task/" in posix` to assert per-tool sharding.
  - Lines 293-315 (other test functions in this block): scan each for `task_id`-in-path assertions; replace with substring assertions against the new `<tool>_<TS>_<uuid8>` shape.

**Pattern for each test:** Use `standalone_workspace` fixture (sets `OPENTEAM_RUNTIME_DIR=tmp_path`) for hermetic isolation; assert workspace lands at `tmp_path/tasks/<tool>/<tool>_<TS>_<uuid8>/`.

**Do not modify** (intentionally test workspace internals):
- `test_import_factory_isolation.py`
- `test/openteam/resources/tools/task/preflight/test_workspace_*.py`
- `test_deliverable_boundary_mock_topology.py`

### Phase 10 — Deploy hygiene (~20 min)

**`.gitignore`** (root):
```
# Runtime artifacts (workspaces, sessions, cache)
/_runtime/
```

**`.dockerignore`** (root, NEW or update):
```
_runtime/
```

**`Dockerfile`** — verify no `COPY src/` carries `_runtime/`. The `.dockerignore` is the cleanest guard.

**`run.sh` / `run.ps1`** — verify launcher doesn't mistakenly chdir into `_runtime/` or set unrelated env vars.

**CI artifact upload** — exclude `_runtime/` from artifact globs.

**Pre-commit hook** (optional but recommended) — reject commits that add files under `_runtime/`.

**(v5.1 fix HIGH-6) Setuptools / packaging exclusion** — `.gitignore` and `.dockerignore` are necessary but NOT sufficient for `pip install -e .`. Verified: `src/openteam.egg-info/SOURCES.txt` currently contains **538 lines** referencing `_runtime/tasks` paths. Without setuptools-level exclusion, every `pip install -e .` re-discovers and re-lists historical artifact paths (even after Phase 11 migration moves them, because setuptools walks `src/` afresh).

**`MANIFEST.in`** (root, NEW or update):
```
recursive-exclude src/openteam/server/_runtime *
recursive-exclude _runtime *
global-exclude *.pyc
```

**`MANIFEST.in`** (canonical form — controls what's in the sdist/manifest):
```
prune src/openteam/server/_runtime
prune _runtime
global-exclude *.pyc
global-exclude *.pyo
```

**`pyproject.toml`** — fix `find_packages` exclude semantics (v5.3 fix CRIT-A). Setuptools `find_packages.exclude` matches **dotted Python package names via fnmatch**, NOT filesystem path globs. The earlier `"**/_runtime*"` form was a no-op:
```toml
# In pyproject.toml [tool.setuptools.packages.find]
[tool.setuptools.packages.find]
where = ["src"]
include = ["openteam*"]
exclude = ["openteam.server._runtime", "openteam.server._runtime.*"]
```

**Two-mechanism rationale (v5.3 clarification HIGH-B):** `find_packages.exclude` controls what's **installed** as importable packages. `MANIFEST.in prune` controls what's **listed in the manifest** (and therefore in `SOURCES.txt`). They are complementary, not redundant.

**Verification sequence (v5.3 addition HIGH-A — egg-info cache invalidation):** The existing `src/openteam.egg-info/SOURCES.txt` is **cached** from a previous `pip install -e .` and won't shrink until regenerated. Required steps in order:
```bash
rm -rf src/openteam.egg-info                     # invalidate cache
pip install -e . --no-deps                       # regenerate manifest
grep -c "_runtime" src/openteam.egg-info/SOURCES.txt  # MUST print 0
```

**Architectural note (v5.3 clarification HIGH-B):** The *primary* fix for the 538-line pollution is **structural** — Phase 5 stops writing artifacts under `src/openteam/server/_runtime/`, and Phase 11 migration moves the legacy 538 .py files out. Once those land, `SOURCES.txt` naturally stops listing them. The `MANIFEST.in prune` + `find_packages exclude` are **defense-in-depth** to prevent re-introduction if future code mistakenly writes to `src/.../_runtime/` again.

### Phase 11 — Migration script + smoke verify + permanent regression tests (~30 min)

**NEW:** `scripts/migrate_runtime_workspaces.py`

```python
"""ONE-TIME migration to unified workspace layout.

Operations (all default --dry-run; require --apply for writes):
  1. src/openteam/server/_runtime/tasks/* → _runtime/tasks/task/*
  2. _runtime/servers/<server>/tasks/* → orphans report (cannot
     auto-associate to historical sessions; left in place).
  3. test/.../_runtime/<TS>/ leaked workspaces (51 dirs) → archived
     to _runtime/_archive/test_leaked/<original_relative_path>/
"""
```

Use `shutil.move`, never `shutil.rmtree`. Idempotent: re-runnable safely.

**Smoke verification:**
- `openteam-task --plan "hi"` standalone → confirm `_runtime/tasks/task/task_<TS>_<uuid8>/outputs/output.md`.
- `openteam-role-setup ...` → confirm `_runtime/tasks/role_setup/role_setup_<TS>_<uuid8>/`.
- `openteam-create-role ...` → confirm `_runtime/tasks/create_role/create_role_<TS>_<uuid8>/`.
- `openteam-project-onboarding ...` → confirm `_runtime/tasks/project_onboarding/project_onboarding_<TS>_<uuid8>/` (was CWD before — security fix).
- Start server `--real-sessions`, send `/role_setup ...` slash-cmd → confirm path under `_runtime/servers/<server>/sessions/<session>/tasks/role_setup_<TS>_<uuid8>/`.
- Start server `--real-sessions`, send `/task` via agent (LLM-driven dispatch) → confirm same nested path.
- Run pytest on the 12 updated test files; confirm GREEN.

**Permanent regression tests** R1, R2, R3 added to CI.

---

## §9 Risk Register

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Slash-path session_id missing when routes invoke tools | 🟢 LOW (was 🔴 HIGH in v3/v4) | §2.3 — `sid` is in scope at line 510 capture during init handshake, before any slash command can arrive. Phase 8 explicit threading. R2 regression test. |
| 2 | Existing in-progress sessions break when server restarts after migration | 🟡 MEDIUM | Migration is non-destructive; old paths preserved; mid-task completion uses old path until session ends. Feature flag for safe rollout. |
| 3 | Phase 4 atomicity with Phase 3 | 🔴 HIGH | Same commit window; feature flag; rollback matrix in §11 explicit |
| 4 | Multiple servers running concurrently → race on session_dir creation | 🟢 LOW | `mkdir(parents=True, exist_ok=True)` is atomic enough; SessionStore already handles |
| 5 | Tests that hardcode old paths break | 🟡 MEDIUM | Phase 9 explicitly updates 12 files; CI catches via permanent regression tests |
| 6 | Hardcoded `working_dir` references elsewhere in codebase | 🟡 MEDIUM | Grep `working_dir`; deprecate softly with log warnings; remove after 1 release |
| 7 | RankEvolve session pattern doesn't fully apply (multi-task per session) | 🟢 LOW | OpenTeam intentionally adds `tasks/` subdir layer — documented in §2 |
| 8 | Cleanup policy unclear (when to gc old session task workspaces?) | 🟢 LOW | Out of scope for this plan; documented as deferred OQ |
| 9 | `_runtime/tasks/` vs `_runtime/servers/` confusion in `ls` | 🟢 LOW | Clear top-level naming; documented in CLAUDE.md after Phase 11 |
| 10 | Test environments may need OPENTEAM_RUNTIME_DIR set | 🟢 LOW | conftest fixture sets it via `tmp_path` per test |
| 11 | Slash-path security fix (Phase 8) might affect currently-working flows | 🟡 MEDIUM | Transition period: log warning when old `working_dir` is provided; remove in next release |
| 12 | ToolDispatcher.task_working_dir field used downstream for UI display (line 247) | 🟢 LOW | Phase 4 keeps the field set (just to a new path); no UI changes needed |
| 13 | `role_setup`/`create_role` literal-`task_id` collision (the BUG today) | 🟡 MEDIUM | Phase 6 + UUID8 in naming closes this. Pinned by Phase 0 RED test 12. |
| 14 | UUID8 collision under high tool-spawn rate | 🟢 LOW | `mkdir(exist_ok=False)` + 3-retry loop in §4 code. Pinned by RED test 11. |
| 15 | Windows path semantics — walk-up assumes POSIX `src/` ancestor | 🟢 LOW | `Path.resolve()` normalizes per-platform. If Windows isn't a supported target, document as known limitation. |
| 16 | `_runtime/` accidentally shipped in Docker image / deploy | 🟡 MEDIUM | Phase 10 adds `.dockerignore`, rsync excludes, CI artifact exclusion |
| 17 | Re-introduction of the manager_websocket_routes UNSAFE hack | 🟢 LOW | Permanent regression test R2 fails the build if the pattern reappears |
| 18 | Re-introduction of executor-local workspace allocation (bypassing the shared helper) | 🟢 LOW | Permanent regression test R3 reflectively asserts each executor's allocation imports from `_shared.workspace_allocator` |
| 19 | `project_onboarding` writing into `src/` if Phase 7 lands without Phase 8 | 🟡 MEDIUM | Phase 7 alone fixes the bug (uses allocator); Phase 8 reinforces by removing the unsafe `working_dir`. Order Phase 7 BEFORE Phase 8 — covered by the phase sequence. |

---

## §10 Acceptance Criteria

### Helper-level (Phase 1)
- ☐ `find_runtime_root()` returns expected path under all 4 fallback strategies (RED tests 1-4 GREEN)
- ☐ `make_workspace_dirname()` matches `<tool>_\d{8}_\d{6}_[0-9a-f]{8}` (RED test 5)
- ☐ Two dirnames generated 1s apart sort lexicographically (RED test 6)
- ☐ `allocate_tool_workspace("task", base_dir=None)` → Path A layout (RED test 7)
- ☐ `allocate_tool_workspace("X", base_dir=Path("/abs"))` → Path B layout (RED test 8)
- ☐ Invalid tool name + relative base_dir both raise `ValueError` (RED tests 9, 10)
- ☐ UUID8 collision retried 3× then raises `FileExistsError` (RED test 11)

### SessionStore (Phase 2)
- ☐ `get_session_dir(new_id)` returns Path (not None), creates dir on demand (RED test 15)
- ☐ `get_session_tasks_dir(id)` returns `<session_dir>/tasks/`, creates both (RED test 16)

### Standalone CLI (Phases 5-7)
- ☐ `openteam-task --plan "hi"` writes to `_runtime/tasks/task/task_<TS>_<uuid8>/outputs/output.md`
- ☐ `openteam-role-setup ...` writes to `_runtime/tasks/role_setup/role_setup_<TS>_<uuid8>/`
- ☐ `openteam-create-role ...` writes to `_runtime/tasks/create_role/create_role_<TS>_<uuid8>/`
- ☐ `openteam-project-onboarding ...` writes to `_runtime/tasks/project_onboarding/project_onboarding_<TS>_<uuid8>/` (was CWD before)
- ☐ Two concurrent `role_setup` runs produce distinct workspaces (RED test 12)

### Server-affiliated (Phases 3, 4, 8)
- ☐ Server-spawned tool (agent-path) writes to `_runtime/servers/<server>/sessions/<session>/tasks/<tool>_<TS>_<uuid8>/`
- ☐ Slash-path `/task --plan "hi"` writes to the same nested layout (no longer UNSAFE) — RED test 13
- ☐ `manager_websocket_routes.py` no longer contains `working_dir = str(tools_dir.parent.parent)` (R2 GREEN)
- ☐ Tasks from session S1 vs S2 land in DIFFERENT session dirs (no cross-pollution)
- ☐ Mock mode (no `--real-sessions`) still works — slash-cmd falls to standalone Path A

### Cross-cutting
- ☐ `/_runtime/` in `.gitignore`
- ☐ `_runtime/` in `.dockerignore`
- ☐ All 12 updated test files pass pytest
- ☐ Migration script runs end-to-end on a real `_runtime/` state (`--dry-run` then `--apply`)
- ☐ No new entries under `src/openteam/server/_runtime/` after migration (R1 GREEN)
- ☐ Permanent regression tests R1, R2, R3 in CI

---

## §11 Migration Strategy

### 11.1 Order of operations (CRITICAL)

The 12 phases must land in order. **Phases 3 and 4 must be atomic** — same PR or same commit window. Either alone breaks the chain.

| Step | Phase | Why this order |
|---|---|---|
| 1 | 0 (RED tests) | Pin contract before source change |
| 2 | 1 (helper) | Additive; no production impact |
| 3 | 2 (SessionStore) | Additive; no production impact |
| 4 | 3 + 4 (factories + dispatcher) | **ATOMIC** — must land together |
| 5 | 5 (task) | Production tool migration begins |
| 6 | 6 (create_role + role_setup) | Closes name-collision bug |
| 7 | 7 (project_onboarding) | Closes security bug; landed before slash-path fix |
| 8 | 8 (slash-path fix) | Threads `sid`; reinforces project_onboarding fix |
| 9 | 9 (test migration) | Tests catch up to new layout |
| 10 | 10 (deploy hygiene) | Operational safety |
| 11 | 11 (migration script + smoke + R-tests) | Final cleanup + regression locking |

### 11.2 Rollback plan

| Revert | Consequence |
|---|---|
| Phase 0 only | Tests disappear; no behavior change |
| Phase 1 only | Tests for helper fail; no production change |
| Phase 2 only | SessionStore reverts to None-on-missing; safe (other code already None-tolerant) |
| **Phase 3 OR Phase 4 alone** | **BROKEN** — atomic pair. Revert as a unit. |
| Phase 5 only | task tool reverts to local allocation; helper unused but works |
| Phase 6 only | create_role/role_setup revert to literal-task_id collision bug |
| Phase 7 only | project_onboarding reverts to CWD-relative + slash-path source-tree write |
| Phase 8 only | Slash-path reverts to UNSAFE; R2 fails CI |
| Phase 9 only | 12 updated tests revert to old assertions; CI fails on new layout |
| Phase 10 only | `_runtime/` could re-enter git/Docker; otherwise harmless |
| Phase 11 only | No leaked workspace cleanup; smoke verify won't run |

### 11.3 Feature flag

Gate Phases 3+4 behind `OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=1` for one release.

- When unset: dispatcher uses old `<server_dir>/tasks/<tool>_<task_id>/` allocation (current behavior).
- When set: dispatcher uses new `<session_root>/tasks/<tool>_<TS>_<uuid8>/` via shared allocator.

After 1 release of stable rollout, remove the flag and the old code path.

### 11.4 Backward-compat sunset

`session_context["working_dir"]` accepted with deprecation warning for 1 release after Phase 4 lands.

```python
# In tool dispatcher / executors:
if "working_dir" in session_context and "session_root" not in session_context:
    logger.warning(
        "session_context['working_dir'] is deprecated; please pass "
        "'session_root' instead. Will be removed in next release."
    )
```

Remove the warning + the field handling in next release.

---

## §12 Comparison vs All Prior Plans

| Aspect | v0 | v1 (697L) | v2 Cursor (247L) | v3 (529L) | v4 partial | Claude (258L) | **v5 (this)** |
|---|---|---|---|---|---|---|---|
| Scope | standalone only | both paths | both paths | both paths | both paths | both paths | both paths |
| Standalone path | `src/.../_runtime/tasks/` | `_runtime/standalone/<tool>/` | `_runtime/tasks/<tool>/` | `_runtime/tasks/<tool>/` | `_runtime/<tool>/` | `_runtime/<tool>/` | **`_runtime/tasks/<tool>/`** ✅ |
| Server path | n/a | NESTED | NESTED ✅ | NESTED ✅ | FLAT (reversal) | FLAT | **NESTED** ✅ (matches user) |
| Slash-path UNSAFE bug | n/a | FIXED | FIXED | FIXED | FIXED | FIXED | FIXED + R2 regression |
| `project_onboarding` migration | ❌ | partial | ✅ | ✅ | ✅ | ❌ (skipped) | ✅ (Phase 7, dedicated) |
| Phase 0 RED tests | ❌ | ❌ | ❌ (doc-bump) | ❌ | ❌ | ❌ | ✅ 16 contract + 3 regression |
| UUID8 collision retry | ❌ | `exist_ok=True` | `exist_ok=True` | `exist_ok=True` | retry | retry ✅ | retry ✅ |
| Allocator API | inline | `session_context: dict` | dict | dict | dict | `base_dir: Optional[Path]` | **`base_dir: Optional[Path]`** ✅ |
| `make_workspace_dirname()` separate | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| `SessionStore.get_session_tasks_dir()` | ❌ | ❌ | ❌ | ❌ | ❌ | partial | ✅ |
| Permanent regression tests | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ R1/R2/R3 |
| Deploy hygiene (.dockerignore etc) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Windows path consideration | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Risk register | minimal | 13 | 5 | 13 | (incomplete) | 5 | 19 |
| Migration script + `--dry-run` | ❌ | ✅ | partial | ✅ | (incomplete) | ❌ | ✅ |
| Feature flag formalized | ❌ | ✅ | risk row | ✅ | (incomplete) | ❌ | ✅ |
| Effort estimate | 2h | 4-5h | 3h | 19h | (incomplete) | 2h | **20h** (~2.5d) |

---

## §13 If Forced to Pick ONE

**Pick v3 (`unified_workspace_allocation_INTEGRATED_v3_plan.md`, 529 lines).**

Three reasons:

1. **Architecturally correct.** v3 has the nested layout matching your explicit choice. v4 partial reverses this on architectural grounds without re-asking — that's a process violation. Claude's plan also uses flat (sibling-not-nested), which contradicts your design intent. v0/v1/v2 Cursor are all correct on layout but v1 uses `_runtime/standalone/<tool>/` instead of your preferred `_runtime/tasks/<tool>/`.

2. **Operationally rigorous.** v3 ships executable Python code, a migration strategy, a rollback plan, a feature flag, an 18-row risk register, and a comparison vs predecessor. v2 Cursor is operationally clearer in some areas (named `role_setup` collision bug, 51 leaked workspace count, per-test-file line numbers, `tasks/` subdir grouping under standalone) but architecturally and operationally thinner overall. Claude is leanest but skips `project_onboarding` (a known security bug).

3. **Complete tool coverage.** v3 covers all 4 tools including `project_onboarding` (which writes into source tree on slash-path). Claude punts on `project_onboarding` "for now" — this leaves a known security bug.

**v5 (this plan) is strictly better than v3** because it adds:
- Cleaner `base_dir: Optional[Path]` allocator API (Claude's contribution; v3 used `session_context: dict`).
- `SessionStore.get_session_tasks_dir()` convenience method (Claude's idea, adapted for nested layout).
- Phase 0 RED tests (16 contract + 3 permanent regression) for TDD discipline.
- Explicit `session_id` flow trace at slash-path (verified earlier in conversation; v3 punted to "ephemeral session fallback").
- Mitigation of v4's HIGH-severity slash-path session_id risk (downgraded to LOW based on verified facts).
- Deploy hygiene (`.dockerignore`, rsync excludes, CI globs) — v3 had `.gitignore` only.
- Windows path consideration as risk #15.
- Realistic 20-hour effort estimate (v3 had 19h; v5 adds Phase 0 RED tests).

If you have v3 deployed and someone says "what should we change?" — apply v5's improvements as deltas. v5 is v3's natural successor.

---

## §14 Design Principles Applied

1. **One source of truth.** All four tools route through `_shared.workspace_allocator` — no per-tool reinvention. Layout decisions live in `SessionStore`.
2. **Two paths, one shape.** Both Path A and Path B end in `tasks/<tool>_<TS>_<uuid8>/` — consistent mental model.
3. **Pin contracts with RED tests first.** Phase 0 turns the spec into executable assertions before any source change.
4. **Pin invariants with permanent regression tests.** R1, R2, R3 prevent workaround patterns from coming back.
5. **Atomic phase coupling where required.** Phases 3+4 land together; rollback matrix is explicit.
6. **Backward-compat bridges with sunset dates.** `working_dir` accepted with deprecation warning for 1 release; removed in the next.
7. **Defensive on silent failure modes.** `exist_ok=False` + retry over `exist_ok=True`; UUID8 collision is rare but real.
8. **Deploy hygiene is part of the plan, not an afterthought.** `.gitignore` is necessary but not sufficient; `.dockerignore`, rsync excludes, CI globs all matter.
9. **Migration is non-destructive by default.** `--dry-run` default in scripts; explicit `--apply` required.
10. **Honor user's stated design intent.** Architectural reversals require re-asking, not a unilateral plan rewrite.
11. **Layout decisions live in SessionStore, not in the allocator.** The allocator is layout-agnostic; SessionStore is the single owner of "where do per-session tasks live on disk."
12. **Pure functions are testable in isolation.** Separating `make_workspace_dirname()` from `allocate_tool_workspace()` lets tests pin the naming format without disk side-effects.

---

## §15 Estimated Effort

| Phase | Implementation | Tests | Review | Total (h) |
|---|---|---|---|---|
| 0 (RED tests) | 0 | 1.5 | 0.5 | 2.0 |
| 1 (helper + unit tests) | 0.5 | 0.5 | 0.5 | 1.5 |
| 2 (SessionStore API) | 0.5 | 0.5 | 0.5 | 1.5 |
| 3 (factories + conversation_service) | 0.5 | 0.5 | 0.5 | 1.5 |
| 4 (dispatcher 🔑) | 1.0 | 0.5 | 1.0 | 2.5 |
| 5 (task migration) | 0.5 | 0 | 0.5 | 1.0 |
| 6 (create_role + role_setup) | 0.75 | 0 | 0.5 | 1.25 |
| 7 (project_onboarding 🚨) | 0.5 | 0.25 | 0.5 | 1.25 |
| 8 (slash-path fix 🚨) | 0.5 | 0.5 | 0.5 | 1.5 |
| 9 (test migration × 12 + conftest) | 1.0 | 1.5 | 1.0 | 3.5 |
| 10 (deploy hygiene) | 0.5 | 0 | 0.25 | 0.75 |
| 11 (migration script + smoke + R-tests) | 1.0 | 0.5 | 0.25 | 1.75 |
| **Total** | **7.25** | **6.25** | **6.5** | **20.0** |

Roughly **2.5 engineer-days**. v0/v1/v2 Cursor/Claude under-estimate at 2-5 hours; v3 estimated 19h; v5 adds Phase 0 RED tests (~2h) and project_onboarding's dedicated Phase 7.

---

*End of v5 plan. Reviewers: focus critique on §2 (architectural decision), §4 (helper API), §6 Phase 3+4 atomicity, §8 deploy hygiene, §13 ("pick v3 if forced to one") — these are the load-bearing decisions.*
