# Runtime Workspace Relocation Plan

**Status**: DRAFT v1.0 — ready for review
**Owner**: tchen7
**Created**: 2026-05-17
**Estimated effort**: ~1h 45min (focused dev) / ~2h 30min (with tests)

---

## §0 Executive Summary

Move the per-run workspace root for **standalone CLI invocations** from `<repo>/src/openteam/server/_runtime/tasks/` to **`<repo>/_runtime/<toolname>/`**, and standardize naming as **`<toolname>_<YYYYMMDD>_<HHMMSS>_<uuid8>`**. This:

1. Removes runtime artifacts from the source tree (cleaner git status, simpler `.gitignore`)
2. Groups workspaces by tool (`task/`, `create_role/`, `role_setup/`) for clear attribution
3. Uses fully-`_` delimited timestamps + hashes for uniform sorting
4. Provides a **single shared helper** (`workspace_allocator.py`) used by all three tools — single source of truth

### ⚠️ SCOPE BOUNDARY — Standalone CLI Only

This plan affects **ONLY the standalone CLI path** (no session context). Session-affiliated runs (agent-path via `tool_dispatcher.py` and slash-path via `manager_websocket_routes.py`) have their OWN workspace allocation mechanism — the dispatcher pre-allocates a workspace under server-managed directories and passes it via `session_context["working_dir"]`. **That session-bound path is intentionally separate** (server controls lifecycle, isolation, cleanup) and is OUT OF SCOPE for this plan.

The two-path architecture already exists in `_resolve_workspace()`:

```python
def _resolve_workspace(session_context, task_id):
    if session_context.get("working_dir"):  # Path A: server session
        return Path(session_context["working_dir"])  # UNCHANGED
    # Path B: standalone CLI ← THIS PLAN MODIFIES ONLY THIS BRANCH
    return allocate_tool_workspace("task")  # NEW shared helper
```

---

## §1 Current State (Verified)

### Tool workspace conventions today

| Tool | Default workspace root | Naming pattern | Issue |
|---|---|---|---|
| `task` | `src/openteam/server/_runtime/tasks/` | `task_task-<8hash>_<YYYYMMDD_HHMMSS>` (hash-first) | Inside `src/`; mixed sort order |
| `create_role` | No auto-allocated workspace (just `--output-path`) | n/a | No workspace at all → reduced observability |
| `role_setup` | Similar to create_role | n/a | Same |

### Hard evidence

- `task/executor.py` line 1: `runtime_root = server_dir / "_runtime" / "tasks"` (server_dir = `src/openteam/server/`)
- `create_role/executor.py`: uses `workspace_root` parameter that defaults to `--output-path`'s parent
- 23+ existing workspaces visible under `src/openteam/server/_runtime/tasks/` — already polluting source tree

---

## §2 Target State

### New directory layout

```
/Users/tchen7/MyProjects/CoreProjects/OpenStartup/    ← repo root
├── src/                                              ← source code only (no runtime)
│   └── openteam/...
├── _runtime/                                         ← NEW location, .gitignore'd
│   ├── task/
│   │   ├── task_20260517_100000_abc12345/
│   │   ├── task_20260517_113422_def67890/
│   │   └── ...
│   ├── create_role/
│   │   ├── create_role_20260517_120500_3a7b9c11/
│   │   └── ...
│   └── role_setup/
│       └── role_setup_20260517_124500_8e2f1a04/
└── _dev/, test/, ...
```

### Naming format (verbatim)

```
<toolname>_<YYYYMMDD>_<HHMMSS>_<uuid8>
```

Example: `task_20260517_100000_abc12345`

Rationale:
- **`_` everywhere** → fully lexicographically sortable
- **tool prefix first** → easy `ls task_*` filtering even when grouped
- **YYYYMMDD_HHMMSS** → natural chronological ordering
- **uuid8** → enough entropy to disambiguate same-second launches (16M values)

---

## §3 Shared Helper Design

### Location
`src/openteam/server/resources/tools/_shared/workspace_allocator.py` (NEW)

### Full implementation

```python
"""Shared workspace allocation for OpenTeam CLI tools.

Provides a single source of truth for:
  1. Locating the canonical _runtime/ root via a robust fallback chain
  2. Allocating per-tool workspaces with a uniform, sortable naming scheme
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path


_FALLBACK_HOME_DIR = Path.home() / ".openteam" / "_runtime"


def find_runtime_root() -> Path:
    """Locate the canonical _runtime/ directory using a fallback chain.

    Resolution order (first match wins):

    1. ``$OPENTEAM_RUNTIME_DIR`` env var — explicit override (CI / prod)
    2. Walk up from this file's location to find a ``src`` ancestor
       → use ``<src_parent>/_runtime`` (dev tree)
    3. Walk up from ``Path.cwd()`` to find a ``src`` ancestor or any dir
       containing both ``src/`` and ``pyproject.toml``
       → use ``<repo_root>/_runtime`` (editable install / cwd-launched)
    4. Fallback to ``~/.openteam/_runtime`` (pip-installed package)
    """
    # Strategy 1: explicit env var
    env_dir = os.environ.get("OPENTEAM_RUNTIME_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    # Strategy 2: walk up from this file
    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == "src":
            return ancestor.parent / "_runtime"

    # Strategy 3: walk up from CWD
    cwd = Path.cwd().resolve()
    for ancestor in [cwd, *cwd.parents]:
        if ancestor.name == "src":
            return ancestor.parent / "_runtime"
        if (ancestor / "src").is_dir() and (ancestor / "pyproject.toml").is_file():
            return ancestor / "_runtime"

    # Strategy 4: user-home fallback
    return _FALLBACK_HOME_DIR


def allocate_tool_workspace(tool_name: str) -> Path:
    """Allocate a fresh workspace for a tool run.

    Returns a Path object at:
        <runtime_root>/<tool_name>/<tool_name>_<YYYYMMDD>_<HHMMSS>_<uuid8>/

    The directory is created (with parents) before return.
    """
    if not tool_name or not tool_name.isidentifier():
        raise ValueError(
            f"tool_name must be a valid identifier, got: {tool_name!r}"
        )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    ws = find_runtime_root() / tool_name / f"{tool_name}_{ts}_{short}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws
```

### Why fallback chain (vs single strategy)

| Scenario | Strategy | Resulting path |
|---|---|---|
| Dev (current) | 2 | `OpenStartup/_runtime/task/task_<...>/` ✅ |
| Dev with `cd src && python -m ...` | 2 | Same ✅ (walk-up from `__file__`) |
| Editable install (`pip install -e .`) | 3 | Same ✅ |
| CI with custom path | 1 | `$OPENTEAM_RUNTIME_DIR/...` ✅ |
| Production pip install | 4 | `~/.openteam/_runtime/...` ✅ |

---

## §4 Implementation Phases

### Phase 1 — Shared helper (~20 min)
**Files**:
- NEW: `src/openteam/server/resources/tools/_shared/__init__.py` (empty)
- NEW: `src/openteam/server/resources/tools/_shared/workspace_allocator.py` (per §3)

**Tests**:
- NEW: `test/openteam/resources/tools/_shared/test_workspace_allocator.py`
  - Test Strategy 1 (env var) wins
  - Test Strategy 2 (walks up to `src/`) under dev tree
  - Test Strategy 3 (cwd-based) when `__file__` is moved (mock)
  - Test Strategy 4 (~/.openteam/_runtime) when nothing else applies (mock)
  - Test `allocate_tool_workspace("task")` creates dir with correct naming
  - Test rejects non-identifier tool names

### Phase 2 — Migrate `task` (~15 min)
**File**: `src/openteam/server/resources/tools/task/executor.py`

**KEY**: Modify ONLY the standalone fallback in `_resolve_workspace()` (Path B). Leave Path A (session-context) untouched — it correctly accepts dispatcher-pre-allocated paths under server-managed directories.

Replace `_allocate_workspace(task_id)` body:
```python
def _allocate_workspace(task_id: str) -> Path:
    # OLD: server_dir / "_runtime" / "tasks" / f"task_{task_id}_{ts}"
    # NEW: <repo_root>/_runtime/task/task_<YYYYMMDD>_<HHMMSS>_<uuid8>/
    from openteam.server.resources.tools._shared.workspace_allocator import allocate_tool_workspace
    return allocate_tool_workspace("task")
```

The `_resolve_workspace()` wrapper REMAINS UNCHANGED — it correctly:
1. Honors `session_context["working_dir"]` when set (server session path) ✅
2. Falls through to `_allocate_workspace()` when standalone (new path) ✅

The per-task subdir heuristic (line: `if "/tasks/" in posix or "/_runtime/" in posix:`) still works since the new path STILL contains `/_runtime/`.

**Test verification**: Run BOTH paths:
- Standalone CLI (no session) → new `_runtime/task/...` location
- Mock session with `working_dir` set → UNCHANGED path

### Phase 3 — Migrate `create_role` (~20 min)
**File**: `src/openteam/server/resources/tools/create_role/executor.py`

Currently `create_role` has no auto-allocated workspace. Add one:

```python
from openteam.server.resources.tools._shared.workspace_allocator import allocate_tool_workspace

def run_create_role(role_description: str, ...):
    workspace_root = allocate_tool_workspace("create_role")
    # ... use workspace_root for streaming cache, tmp_output_files, etc.
    # Final output_path still respected if user passed --output-path
```

If `--output-path` is provided, use it for the final doc. Either way, the workspace is allocated for observability (logs, manifests, session JSONLs).

### Phase 4 — Migrate `role_setup` (~10 min)
**File**: `src/openteam/server/resources/tools/role_setup/executor.py`

Same pattern as `create_role`.

### Phase 5 — Update test scripts (~25 min)
**Files**:
- `test/openteam/resources/tools/task/test_task_agent_config_brta_with_multiflow_pti.py`
  - `test_real_cli_subprocess_plan_mode` — update path expectations
  - Other tests that read workspace artifacts post-run
- NEW: `test/openteam/resources/tools/create_role/test_create_role_cli_smoke.py` (skeleton)
- NEW: `test/openteam/resources/tools/role_setup/test_role_setup_cli_smoke.py` (skeleton)

Each subprocess-test sets `OPENTEAM_RUNTIME_DIR` to a `tmp_path` fixture for hermetic isolation, then verifies workspace was created under that path.

### Phase 6 — Update `.gitignore` (~5 min)
Add to root `.gitignore`:
```
/_runtime/
~/.openteam/
```

### Phase 7 — Migrate / clean old workspaces (~10 min, ONE-TIME)
Create `scripts/migrate_runtime_workspaces.py`:
```python
# Move existing runs from src/openteam/server/_runtime/tasks/* to _runtime/task/*
# Apply new naming (toolname_YYYYMMDD_HHMMSS_uuid8) to old folders
# Document old → new mapping in _runtime/.migration_log.txt
```

Optional: archive instead of delete (preserves test postmortems).

---

## §5 Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| AC1 | `allocate_tool_workspace("task")` creates `<repo>/_runtime/task/task_<ts>_<uuid8>/` | unit test |
| AC2 | Walk-up-to-`src` works from any file under `src/openteam/...` | unit test |
| AC3 | `OPENTEAM_RUNTIME_DIR` env var overrides all other strategies | unit test |
| AC4 | `task` CLI launches with no errors at new location | smoke test |
| AC5 | `create_role` CLI now has a `_runtime/create_role/...` workspace | smoke test |
| AC6 | `role_setup` CLI same | smoke test |
| AC7 | Existing `test_real_cli_subprocess_plan_mode` still passes | regression test |
| AC8 | No new `src/openteam/server/_runtime/` entries created after migration | post-test grep |
| AC9 | `.gitignore` excludes `_runtime/` | git status clean check |
| AC10 | Sorting `ls _runtime/task/` is chronological | `ls` output check |

---

## §6 Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Hardcoded paths in existing code break | MEDIUM | Grep `src/openteam/server/_runtime` → fix all callers in Phase 5 |
| Checkpoint/Resumable resume breaks for in-progress runs | LOW | Migration script preserves old workspaces; new runs use new path |
| Per-task subdir heuristic (`/tasks/` substring check) breaks | LOW | New path contains `/_runtime/` (already covered by `or` clause) |
| Tests that hardcode `_runtime/tasks/` fail | MEDIUM | Phase 5 explicitly updates them |
| Some launcher scripts (tmp_rovodev_*) reference old path | LOW | One-off scripts, fix if encountered |
| Pip-install scenario | LOW | Strategy 4 (~/.openteam) handles it |
| Concurrent allocations collide | NEGLIGIBLE | uuid8 has 16M values per second |

---

## §7 Open Questions

| # | Question | Default Answer |
|---|---|---|
| OQ1 | Move old `_runtime/tasks/` workspaces or leave them? | **Leave them** — useful for postmortem comparison; add `.deprecated` marker |
| OQ2 | Should `create_role`/`role_setup` ALWAYS allocate a workspace, even when `--output-path` is given? | **YES** — workspace is for logs/manifests, --output-path is for the deliverable |
| OQ3 | Should the helper be in `openteam.server.resources.tools._shared` or `openteam.server.utils`? | **`_shared`** under tools/ — proximity to consumers, clear ownership |
| OQ4 | Add `--runtime-dir` flag to each tool CLI for ad-hoc override? | **Defer** — `OPENTEAM_RUNTIME_DIR` env var covers the use case |

---

## §8 Provenance

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-05-17 | Initial plan — adopt fully-`_` delimited naming `<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>`, walk-up-to-`src` strategy with 4-tier fallback chain |
