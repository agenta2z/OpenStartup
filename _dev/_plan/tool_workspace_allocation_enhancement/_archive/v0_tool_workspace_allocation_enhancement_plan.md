# Tool Workspace Allocation Enhancement Plan

**Status**: DRAFT v1.0 — ready for review
**Owner**: tchen7
**Created**: 2026-05-17
**Estimated effort**: ~1h 45min (focused dev) / ~2h 30min (with full tests)
**Scope**: Standalone CLI invocations ONLY (server-session paths untouched)

---

## §0 Executive Summary

Move per-run workspace allocation for **standalone CLI invocations** of `task`, `create_role`, and `role_setup` tools from `<repo>/src/openteam/server/_runtime/tasks/` to **`<repo>/_runtime/<toolname>/`**, with uniform naming **`<toolname>_<YYYYMMDD>_<HHMMSS>_<uuid8>`**.

### Why

1. **Remove runtime artifacts from `src/`** — `src/` should hold source code, not run outputs (cleaner git status, simpler `.gitignore`, fewer accidental commits)
2. **Group workspaces by tool** — `task/`, `create_role/`, `role_setup/` subdirs make attribution and cleanup easier
3. **Uniform sortable naming** — `_`-delimited fields produce natural chronological + tool-attribution sort order via plain `ls`
4. **Single source of truth** — one shared helper `workspace_allocator.py` ensures all 3 tools use the identical convention
5. **Self-locating, no hardcoded paths** — 4-tier fallback chain handles dev/editable/CI/install scenarios
6. **Add observability to `create_role` and `role_setup`** — currently they have NO workspace at all; gaining one gives the same logs/manifests/JSONLs that `task` has

### What

| Aspect | Today | After |
|---|---|---|
| **Root** | `<repo>/src/openteam/server/_runtime/tasks/` | **`<repo>/_runtime/<toolname>/`** |
| **Naming (task)** | `task_task-<8hash>_<YYYYMMDD_HHMMSS>` (hash-first) | **`task_<YYYYMMDD>_<HHMMSS>_<uuid8>`** (ts-first) |
| **create_role / role_setup workspace** | None (only `--output-path` for deliverable) | **Auto-allocated workspace** for logs + manifests |
| **Per-tool grouping** | All under `tasks/` regardless of tool | **`task/`, `create_role/`, `role_setup/`** subdirs |
| **Source of truth** | Inline `_allocate_workspace` per tool | **Shared `workspace_allocator.py`** helper |

### ⚠️ SCOPE BOUNDARY — Standalone CLI Only

This plan affects **ONLY the standalone CLI path** (no session context). Session-affiliated runs have their **own workspace allocation mechanism** — the dispatcher (`tool_dispatcher.py` for agent-path, `manager_websocket_routes.py` for slash-path) pre-allocates a workspace under **server-managed directories** and passes it via `session_context["working_dir"]`.

**That session-bound path is intentionally separate** because:
- The **server** controls lifecycle (session start → end, timeout, cleanup)
- The server needs isolation policy across concurrent sessions
- Server-side audit logs reference these paths
- Server-side admin/policy code may need to scan/manage these directories

That mechanism is **OUT OF SCOPE** for this plan.

### The Two-Path Architecture (Already Exists)

```python
# task/executor.py — _resolve_workspace() — UNCHANGED LOGIC
def _resolve_workspace(session_context, task_id):
    sc = session_context or {}
    candidate = sc.get("working_dir", "")
    if candidate:  # Path A: session-bound (dispatcher pre-allocated)
        # ...validation
        return Path(candidate)  # ← UNCHANGED
    # Path B: standalone CLI ← THIS PLAN MODIFIES ONLY THIS BRANCH
    return _allocate_workspace(task_id)  # ← swapped to shared helper
```

---

## §1 Current State (Verified)

### Tool workspace conventions today

| Tool | Default workspace root (standalone) | Naming pattern | Session-bound path |
|---|---|---|---|
| `task` | `src/openteam/server/_runtime/tasks/` | `task_task-<8hash>_<YYYYMMDD_HHMMSS>` (hash-first) | Dispatcher-provided via `working_dir` ✅ already separated |
| `create_role` | **None** — just `--output-path` for deliverable | n/a | n/a (no equivalent path in dispatcher today) |
| `role_setup` | **None** — same as create_role | n/a | n/a |

### Hard evidence

- **`task/executor.py:155-159`** — `runtime_root = server_dir / "_runtime" / "tasks"` and `ws = runtime_root / f"task_{task_id}_{ts}"`
- **`task/executor.py:166-178`** — `_resolve_workspace()` correctly routes session-bound vs standalone via `session_context.get("working_dir")` check
- **`create_role/executor.py`** — uses `workspace_root` parameter that defaults to `--output-path`'s parent
- **`role_setup/executor.py`** — same pattern as create_role
- 23+ existing workspaces under `src/openteam/server/_runtime/tasks/` — polluting source tree

### What's "wrong" today

1. `src/` is for source code; runtime artifacts pollute it
2. Naming starts with `task_task-<hash>`, making chronological sort impossible without reordering
3. `create_role` and `role_setup` have no workspace at all → reduced observability
4. Each tool defines its own allocation logic → drift over time

---

## §2 Target State

### Directory layout (after Phase 7 migration)

```
/Users/tchen7/MyProjects/CoreProjects/OpenStartup/
├── src/                                                  ← source code only
│   └── openteam/server/resources/tools/
│       ├── _shared/                                       ← NEW
│       │   ├── __init__.py
│       │   └── workspace_allocator.py                     ← NEW
│       ├── task/executor.py                               ← MODIFIED
│       ├── create_role/executor.py                        ← MODIFIED
│       └── role_setup/executor.py                         ← MODIFIED
├── _runtime/                                             ← NEW location, .gitignore'd
│   ├── task/
│   │   ├── task_20260517_100000_abc12345/
│   │   ├── task_20260517_113422_def67890/
│   │   └── ...
│   ├── create_role/
│   │   ├── create_role_20260517_120500_3a7b9c11/
│   │   └── ...
│   └── role_setup/
│       └── role_setup_20260517_124500_8e2f1a04/
├── _dev/, test/, ...
└── .gitignore                                            ← MODIFIED (add /_runtime/)
```

### Naming format (verbatim)

```
<toolname>_<YYYYMMDD>_<HHMMSS>_<uuid8>
```

| Field | Example | Rationale |
|---|---|---|
| `<toolname>` | `task`, `create_role`, `role_setup` | Easy `ls task_*` filtering; tool attribution |
| `<YYYYMMDD>` | `20260517` | Sorts correctly |
| `<HHMMSS>` | `100000` | Disambiguates intra-day runs |
| `<uuid8>` | `abc12345` | 16M values — handles concurrent same-second launches |

**Why all `_` separators**: Uniform delimitation → fully lexicographically sortable. Mixed delimiters (e.g., `task_20260517_100000-abc12345`) break clean sort assumptions.

---

## §3 Shared Helper Design

### Location

```
src/openteam/server/resources/tools/_shared/
├── __init__.py                      ← empty
└── workspace_allocator.py           ← NEW (~80 lines)
```

### Full implementation

```python
"""Shared workspace allocation for OpenTeam CLI tools.

Provides a single source of truth for:
  1. Locating the canonical _runtime/ root via a robust fallback chain
  2. Allocating per-tool workspaces with a uniform, sortable naming scheme

Scope: This module is for STANDALONE CLI invocations only.
Server-session-bound workspaces are allocated separately by the dispatcher
(tool_dispatcher.py / manager_websocket_routes.py) and passed via
session_context["working_dir"].
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

    Args:
        tool_name: Must be a valid Python identifier (no slashes, dots, etc.).

    Raises:
        ValueError: if tool_name is empty or not a valid identifier.
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

### Fallback chain coverage matrix

| Scenario | Strategy fired | Resulting path |
|---|---|---|
| Dev (current dev tree) | 2 | `OpenStartup/_runtime/task/task_<...>/` ✅ |
| Dev with `cd src && python -m ...` | 2 | Same ✅ (walk-up from `__file__`) |
| Editable install (`pip install -e .`) | 3 | Same ✅ |
| CI with custom path | 1 | `$OPENTEAM_RUNTIME_DIR/<tool>/...` ✅ |
| Production pip install | 4 | `~/.openteam/_runtime/<tool>/...` ✅ |

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
  - Test rejects non-identifier tool names (e.g., `"task/foo"`, `""`, `"123abc"`)
  - Test idempotency: two calls produce distinct dirs (uuid8 differs)

### Phase 2 — Migrate `task` (~15 min)
**File**: `src/openteam/server/resources/tools/task/executor.py`

**KEY**: Modify ONLY the standalone fallback. Leave `_resolve_workspace()` wrapper untouched — its conditional logic correctly routes session vs standalone:

```python
# OLD (~line 148-159):
def _allocate_workspace(task_id: str) -> Path:
    server_dir = Path(__file__).resolve().parents[3]
    runtime_root = server_dir / "_runtime" / "tasks"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ws = runtime_root / f"task_{task_id}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws

# NEW:
def _allocate_workspace(task_id: str) -> Path:
    """Allocate workspace for STANDALONE CLI invocations of the task tool.

    NOTE: task_id is no longer used in the directory name (uuid8 replaces it).
    It remains a parameter for backward-compatibility with callers.
    """
    from openteam.server.resources.tools._shared.workspace_allocator import (
        allocate_tool_workspace,
    )
    return allocate_tool_workspace("task")
```

The `_resolve_workspace()` wrapper REMAINS UNCHANGED — it correctly:
1. Honors `session_context["working_dir"]` when set (Path A — server session) ✅
2. Falls through to `_allocate_workspace()` when standalone (Path B — new behavior) ✅

The per-task subdir heuristic (`if "/tasks/" in posix or "/_runtime/" in posix:`) still works since the new path STILL contains `/_runtime/`.

**Test verification**: Run BOTH paths:
- Standalone CLI (no session) → new `_runtime/task/...` location ✅
- Mock session with `working_dir` set → UNCHANGED path ✅

### Phase 3 — Migrate `create_role` (~20 min)
**File**: `src/openteam/server/resources/tools/create_role/executor.py`

Currently `create_role` has no auto-allocated workspace. Add one for observability (logs, manifests, session JSONLs are valuable even if `--output-path` is used for the final deliverable):

```python
from openteam.server.resources.tools._shared.workspace_allocator import (
    allocate_tool_workspace,
)

def run_create_role(role_description: str, output_path: Optional[str], ...):
    # NEW: always allocate a workspace for observability
    workspace_root = allocate_tool_workspace("create_role")
    
    # Final deliverable still respects --output-path if provided
    final_output = output_path or str(workspace_root / "role.md")
    
    # Streaming cache, tmp_output_files, etc. all under workspace_root
    streaming_cache_dir = os.path.join(str(workspace_root), "_runtime", "inferencer_cache")
    os.makedirs(os.path.join(str(workspace_root), "_runtime", "tmp_output_files"), exist_ok=True)
    # ... rest of run logic
```

**Behavior change**: `create_role` now ALWAYS creates a workspace. `--output-path` controls only where the final `.md` ends up (or defaults to `<workspace>/role.md`).

### Phase 4 — Migrate `role_setup` (~10 min)
**File**: `src/openteam/server/resources/tools/role_setup/executor.py`

Same pattern as `create_role`.

### Phase 5 — Update test scripts (~25 min)

**Files**:
- `test/openteam/resources/tools/task/test_task_agent_config_brta_with_multiflow_pti.py`
  - `test_real_cli_subprocess_plan_mode` — update path expectations
  - Any other tests that read workspace artifacts post-run
- NEW: `test/openteam/resources/tools/create_role/test_create_role_cli_smoke.py` (skeleton)
- NEW: `test/openteam/resources/tools/role_setup/test_role_setup_cli_smoke.py` (skeleton)

**Pattern for subprocess tests**: Set `OPENTEAM_RUNTIME_DIR` to a `tmp_path` fixture for hermetic isolation, then verify workspace was created under that path:

```python
def test_real_cli_subprocess_plan_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENTEAM_RUNTIME_DIR", str(tmp_path))
    result = subprocess.run(
        ["python", "-m", "openteam.server.resources.tools.task", "--plan", "Hello"],
        capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0
    # Verify workspace was created under tmp_path
    task_dirs = list((tmp_path / "task").glob("task_*"))
    assert len(task_dirs) == 1
    assert (task_dirs[0] / "outputs" / "output.md").exists()
```

### Phase 6 — Update `.gitignore` (~5 min)

Add to root `.gitignore`:
```
# Runtime artifacts (standalone CLI workspaces)
/_runtime/
```

Also document `~/.openteam/_runtime/` in `README.md` so users know to clean it manually if they hit the pip-install fallback path.

### Phase 7 — Migrate / archive old workspaces (~10 min, ONE-TIME)

Create `scripts/migrate_runtime_workspaces.py`:
```python
"""ONE-TIME migration: move src/openteam/server/_runtime/tasks/* → _runtime/task/

Per OQ1 in plan: ARCHIVE old workspaces (don't delete) — preserves postmortem data.
"""
import shutil
import sys
from pathlib import Path

OLD = Path("src/openteam/server/_runtime/tasks")
NEW = Path("_runtime/task")

def main():
    if not OLD.exists():
        print("No old workspaces to migrate.")
        return 0
    NEW.mkdir(parents=True, exist_ok=True)
    moved = 0
    for old_ws in OLD.iterdir():
        if not old_ws.is_dir():
            continue
        # Keep old folder name to preserve postmortem references
        new_ws = NEW / old_ws.name
        if new_ws.exists():
            print(f"  SKIP (exists): {old_ws.name}")
            continue
        shutil.move(str(old_ws), str(new_ws))
        moved += 1
        print(f"  MOVED: {old_ws.name}")
    print(f"\nMigrated {moved} workspace(s).")
    if OLD.exists() and not any(OLD.iterdir()):
        OLD.rmdir()
        print(f"Removed empty {OLD}.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

User runs ONCE: `python scripts/migrate_runtime_workspaces.py`

---

## §5 Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| AC1 | `allocate_tool_workspace("task")` creates `<repo>/_runtime/task/task_<YYYYMMDD>_<HHMMSS>_<uuid8>/` | unit test |
| AC2 | Walk-up-to-`src` works from any file under `src/openteam/...` | unit test |
| AC3 | `OPENTEAM_RUNTIME_DIR` env var overrides all other strategies | unit test |
| AC4 | `task` standalone CLI launches with no errors at new location | smoke test |
| AC5 | `task` session-bound path (with `working_dir`) UNCHANGED from before | regression test (mock session) |
| AC6 | `create_role` CLI now has a `_runtime/create_role/...` workspace | smoke test |
| AC7 | `role_setup` CLI same | smoke test |
| AC8 | Existing `test_real_cli_subprocess_plan_mode` still passes after update | regression test |
| AC9 | No new `src/openteam/server/_runtime/` entries created after migration | post-test grep |
| AC10 | `.gitignore` excludes `_runtime/` | git status clean check |
| AC11 | Sorting `ls _runtime/task/` is chronological | `ls` output check |
| AC12 | Per-task subdir heuristic in `task/executor.py` still recognizes new paths | unit test (mock `_resolve_workspace` with new path) |
| AC13 | `pyproject.toml` registers `_shared` as a package (no import errors) | `pip install -e .` succeeds |

---

## §6 Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Hardcoded paths in existing code break | MEDIUM | Grep `_runtime/tasks` → fix all callers in Phase 5 |
| Checkpoint/Resumable resume breaks for in-progress runs | LOW | Migration script preserves old workspaces; new runs use new path |
| Per-task subdir heuristic (`/tasks/` substring check) breaks | LOW | New path contains `/_runtime/` (already covered by `or` clause); AC12 verifies |
| Tests that hardcode `_runtime/tasks/` fail | MEDIUM | Phase 5 explicitly updates them; CI catches via AC8 |
| Some launcher scripts (`tmp_rovodev_*.sh`) reference old path | LOW | One-off scripts, fix if encountered |
| Pip-install scenario falls back to `~/.openteam/` | LOW | Strategy 4 (~/.openteam/_runtime/) handles it gracefully |
| Concurrent allocations collide | NEGLIGIBLE | uuid8 has 16M values per second |
| Session-bound runs accidentally affected | **NONE** | Plan explicitly scoped to standalone path only; `_resolve_workspace()` wrapper untouched |
| `create_role`/`role_setup` behavior change (always allocates workspace) | LOW | Documented in Phase 3/4; `--output-path` still respected for deliverable |
| New `_shared` package not picked up by setuptools | LOW | AC13 verifies `pip install -e .` succeeds with new package |
| Migration script destroys data | LOW | Uses `shutil.move` (not delete); preserves folder names; idempotent (SKIP if exists) |

---

## §7 Open Questions

| # | Question | Default Answer |
|---|---|---|
| OQ1 | Move old `_runtime/tasks/` workspaces or leave them? | **MIGRATE** via Phase 7 script (preserves data, cleans source tree) |
| OQ2 | Should `create_role`/`role_setup` ALWAYS allocate a workspace, even when `--output-path` is given? | **YES** — workspace is for logs/manifests; `--output-path` is only for the final deliverable file |
| OQ3 | Should the helper be in `openteam.server.resources.tools._shared` or `openteam.server.utils`? | **`_shared` under tools/** — proximity to consumers, clear ownership boundary, "_" prefix hides from public API |
| OQ4 | Add `--runtime-dir` CLI flag to each tool for ad-hoc override? | **DEFER** — `OPENTEAM_RUNTIME_DIR` env var covers the use case for now |
| OQ5 | Should standalone runs also write a manifest at `<runtime_root>/_index.jsonl` for cross-run discovery? | **DEFER** — nice-to-have, separate plan |
| OQ6 | Cleanup policy: auto-delete workspaces older than N days? | **DEFER** — separate maintenance script, not part of allocation logic |
| OQ7 | Should `find_runtime_root()` cache its result (singleton)? | **NO** — env var changes mid-process should be respected; cheap to compute (~µs) |

---

## §8 Out of Scope (Explicit Non-Goals)

| Item | Why Not |
|---|---|
| Session-bound (Path A) workspace allocation refactor | Server-owned mechanism; intentionally separate; would require coordination with session lifecycle |
| Slash-path `manager_websocket_routes.py` UNSAFE behavior | Known issue but separate concern; needs its own plan |
| `tool_dispatcher.py` agent-path workspace pre-allocation | Working correctly; out of scope |
| Workspace cleanup / GC policy | Allocation only; cleanup is a separate concern (OQ6) |
| Cross-workspace artifact discovery / indexing | Future enhancement (OQ5) |
| `--runtime-dir` CLI flag per tool | Deferred (OQ4) |
| Migration to a database-backed workspace registry | Out of scope; filesystem is sufficient |

---

## §9 Provenance

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-05-17 | Initial plan — adopt fully-`_` delimited naming `<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>`, walk-up-to-`src` strategy with 4-tier fallback chain, shared helper `workspace_allocator.py`, explicit scope to standalone CLI only (session-bound path untouched), all 3 tools (`task`, `create_role`, `role_setup`) covered |
