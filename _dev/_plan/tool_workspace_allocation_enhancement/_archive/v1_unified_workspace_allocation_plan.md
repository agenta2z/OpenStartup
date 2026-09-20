# Unified Tool Workspace Allocation Plan

**Status**: DRAFT v1.0 — ready for review
**Owner**: tchen7
**Created**: 2026-05-17
**Supersedes**: `tool_workspace_allocation_enhancement_plan.md` (which was scoped to standalone CLI only)
**Reference**: `atlassian-packages/rankevolve` session/workspace pattern
**Estimated effort**: ~4-5 hours (focused dev) / ~6-8 hours (with full tests + migration)

---

## §0 Executive Summary

Unify ALL workspace allocation for OpenTeam tools (`task`, `create_role`, `role_setup`) under ONE coherent two-path architecture:

| Path | When | Workspace Location |
|---|---|---|
| **Path A: Standalone CLI** | No session context (direct `python -m ...`) | `<repo>/_runtime/standalone/<tool>/<tool>_<TS>_<uuid8>/` |
| **Path B: Server-Affiliated** | Within a server session (agent-path OR slash-path) | `<repo>/_runtime/servers/<server>/sessions/<session_id>/tasks/<tool>_<TS>_<uuid8>/` |

### Why Unify Now

1. **Today's gap (per investigation)**: OpenTeam already has `SessionStore` (adapted from RankEvolve) that owns `<runtime_root>/servers/<server>/sessions/<session_id>/`. But `tool_dispatcher.py` allocates task workspaces under `<server_dir>/tasks/<tool>_<task_id>/` — a **flat directory disconnected from per-session layout**. Tasks from session A and session B all pile up in the same `tasks/` directory with no per-session attribution.

2. **`manager_websocket_routes.py` slash-path is UNSAFE today**: passes `working_dir = server source dir` (line 216), which `_resolve_workspace`'s safety heuristic rejects, forcing re-allocation to a path totally outside the session — workspace continuity is broken.

3. **`create_role` and `role_setup` have NO workspace today** (slash-path only), so their inference logs/manifests aren't preserved at all.

4. **No common helper** — each entry point reinvents the path convention independently → drift, inconsistency, and the SessionStore-vs-dispatcher disconnect above.

### What Changes

| Aspect | Today | After |
|---|---|---|
| **Standalone CLI for `task`** | `src/.../server/_runtime/tasks/task_<hash>_<ts>/` | `<repo>/_runtime/standalone/task/task_<ts>_<uuid8>/` |
| **Standalone CLI for `create_role`/`role_setup`** | NONE | `<repo>/_runtime/standalone/<tool>/<tool>_<ts>_<uuid8>/` |
| **Agent-path workspace** | `<server>/tasks/<tool>_<task_id>/` (flat) | `<server>/sessions/<session_id>/tasks/<tool>_<ts>_<uuid8>/` (per-session) |
| **Slash-path workspace** | UNSAFE (server source dir → fallback re-allocation) | `<server>/sessions/<session_id>/tasks/<tool>_<ts>_<uuid8>/` (same as agent-path) |
| **Naming** | `task_<hash>_<ts>` (hash-first, hard to sort) | `<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>` (uniform, sortable) |
| **Common helper** | None (each tool has its own `_allocate_workspace`) | `_shared/workspace_allocator.py` (single source of truth) |

### Inspiration: RankEvolve Pattern

```
<runtime_root>/
└── <session_id>/                  ← per-session root
    ├── session.jsonl              ← chat log
    ├── manifest.json              ← session metadata
    └── <iteration_N>/             ← per-task workspace nested INSIDE session
        ├── _runtime/
        ├── outputs/
        ├── results/
        └── logs/
```

OpenTeam's adaptation:

```
<runtime_root>/
├── servers/                       ← MULTI-SERVER (adapted from RankEvolve single root)
│   └── server_<TS>_<uuid8>/       ← per-server (already exists in SessionStore!)
│       ├── server_info.json
│       └── sessions/              ← per-session (already exists!)
│           ├── sessions_index.json
│           └── <session_id>_<TS>/
│               ├── session_state.json
│               └── tasks/         ← NEW: per-session task workspaces
│                   ├── task_20260517_100000_abc12345/
│                   ├── create_role_20260517_113422_def67890/
│                   └── role_setup_20260517_124500_8e2f1a04/
└── standalone/                    ← NEW: standalone CLI (no session)
    ├── task/
    ├── create_role/
    └── role_setup/
```

---

## §1 Current State (Verified)

### 1.1 Three Entry Points Today

| Entry | File:Line | Workspace Path | Status |
|---|---|---|---|
| Standalone CLI | `task/executor.py:148` | `src/.../server/_runtime/tasks/task_<hash>_<ts>/` | ⚠️ Pollutes `src/`, hash-first naming |
| Agent-path | `tool_dispatcher.py:207-208` | `<server_dir>/tasks/<tool>_<task_id>/` | ⚠️ Flat, no per-session attribution |
| Slash-path | `manager_websocket_routes.py:216` | `<server>` (rejected → re-allocated) | 🚨 UNSAFE |

### 1.2 SessionStore Already Has Per-Session Layout (UNUSED For Tasks)

**File**: `src/openteam/server/services/session_store.py:1-25` (verbatim docstring):
```
<runtime_root>/
├── servers/
│   ├── server_<YYYYMMDD_HHMMSS>_<uuid8>/       ← current server
│   │   ├── server_info.json
│   │   └── sessions/
│   │       ├── sessions_index.json
│   │       ├── <session_id>_<timestamp>/
│   │       │   └── session_state.json
│   │       └── ...
```

**The session directory already exists. We just need to put task workspaces UNDER each session_id dir** (the "✗ but no tasks/ subdir today" gap).

### 1.3 RankEvolve Pattern (Reference)

From `atlassian-packages/rankevolve` investigation:
- Session manager: `src/utils/service_utils/session_management/session_manager.py`
- Session manifest: `src/utils/service_utils/session_management/session_manifest.py:82`
- Pattern: `<session_root>/<session_id>/<iteration_N>/` with `_runtime`, `outputs`, `results`, `logs`

OpenTeam's deviation from RankEvolve (BY DESIGN):
- Multi-server tier added (OpenTeam supports resumable historical servers)
- Tasks separated from sessions (a session has 1+ tasks; RankEvolve sessions are 1:1 with iteration sequences)

---

## §2 Target Architecture

### 2.1 Unified Two-Path Allocator

```python
def allocate_tool_workspace(
    tool_name: str,
    session_context: Optional[dict] = None,
) -> Path:
    """Allocate a workspace for a tool run, routed by session context.

    Path A (standalone):
        <repo>/_runtime/standalone/<tool>/<tool>_<TS>_<uuid8>/

    Path B (server-affiliated):
        <session_root>/tasks/<tool>_<TS>_<uuid8>/
        where session_root comes from session_context["session_root"]
    """
    if session_context and session_context.get("session_root"):
        # Path B: server-affiliated
        session_root = Path(session_context["session_root"])
        tasks_dir = session_root / "tasks"
    else:
        # Path A: standalone
        tasks_dir = find_runtime_root() / "standalone" / tool_name

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    ws = tasks_dir / f"{tool_name}_{ts}_{short}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws
```

### 2.2 Session Context Contract (Standardized)

ALL session-affiliated paths MUST pass:

| Field | Type | Source | Required? |
|---|---|---|---|
| `session_root` | str (abs path) | SessionStore.get_session_dir(session_id) | YES (for Path B) |
| `session_id` | str | server's session manager | YES |
| `task_id` | str | dispatcher-generated | YES |
| `interactive` | InteractiveHandler | server | YES |
| `working_dir` | str | DEPRECATED — replaced by `session_root` + per-task allocation | NO (kept for backward compat, ignored by new code) |

### 2.3 Per-Task Workspace Layout (Unchanged)

Inside `<tasks_dir>/<tool>_<TS>_<uuid8>/`:
```
├── outputs/
│   ├── output.md                  ← canonical output
│   ├── final_deliverables/        ← promoted deliverable
│   └── output_manifest.json
├── _runtime/                      ← inferencer cache, tmp files
│   ├── inferencer_cache/
│   └── tmp_output_files/
├── logs/
│   └── session/                   ← inferencer session JSONLs
└── children/                      ← orchestrator sub-workspaces (BTA/MFI/Dual)
```

### 2.4 Directory Layout End-State

```
/Users/tchen7/MyProjects/CoreProjects/OpenStartup/
├── src/                                                          ← source only
│   └── openteam/server/resources/tools/
│       ├── _shared/
│       │   ├── __init__.py
│       │   └── workspace_allocator.py                            ← unified helper
│       ├── task/executor.py                                      ← modified
│       ├── create_role/executor.py                               ← modified
│       └── role_setup/executor.py                                ← modified
├── _runtime/                                                     ← .gitignore'd
│   ├── servers/                                                  ← server-affiliated
│   │   └── server_20260517_100000_abc12345/
│   │       ├── server_info.json
│   │       └── sessions/
│   │           └── <session_id>_<timestamp>/
│   │               ├── session_state.json
│   │               └── tasks/                                    ← NEW: nested under session
│   │                   ├── task_20260517_113422_def67890/
│   │                   ├── create_role_20260517_120500_3a7b9c11/
│   │                   └── role_setup_20260517_124500_8e2f1a04/
│   └── standalone/                                               ← standalone CLI
│       ├── task/
│       │   └── task_20260517_100000_abc12345/
│       ├── create_role/
│       │   └── create_role_20260517_113422_def67890/
│       └── role_setup/
│           └── role_setup_20260517_124500_8e2f1a04/
└── .gitignore                                                    ← excludes /_runtime/
```

---

## §3 Shared Helper Design

### Location & Implementation

**File**: `src/openteam/server/resources/tools/_shared/workspace_allocator.py`

```python
"""Unified workspace allocation for OpenTeam tools.

Two-path architecture:
  - Path A (standalone CLI): <repo>/_runtime/standalone/<tool>/<tool>_<TS>_<uuid8>/
  - Path B (server-affiliated): <session_root>/tasks/<tool>_<TS>_<uuid8>/

Session-affiliated callers MUST provide session_context with 'session_root' key
pointing to the per-session directory (typically allocated by SessionStore).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


_FALLBACK_HOME_DIR = Path.home() / ".openteam" / "_runtime"


def find_runtime_root() -> Path:
    """Locate the canonical _runtime/ directory using a fallback chain.

    1. $OPENTEAM_RUNTIME_DIR env var
    2. Walk up from __file__ to find src/ ancestor → <parent>/_runtime
    3. Walk up from CWD to find src/ or pyproject.toml → <root>/_runtime
    4. Fallback: ~/.openteam/_runtime
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


def allocate_tool_workspace(
    tool_name: str,
    session_context: Optional[dict] = None,
) -> Path:
    """Allocate a fresh workspace for a tool run.

    Routes by session_context:
      - If session_context["session_root"] is set → Path B (server-affiliated)
        Returns <session_root>/tasks/<tool>_<TS>_<uuid8>/
      - Otherwise → Path A (standalone)
        Returns <runtime_root>/standalone/<tool>/<tool>_<TS>_<uuid8>/

    Args:
        tool_name: Must be a valid Python identifier
        session_context: Optional dict; if it contains 'session_root' (absolute
            path to per-session directory), workspace is created under it.

    Returns:
        Path to newly-created workspace directory (parents created with parents=True).

    Raises:
        ValueError: if tool_name is empty or not a valid identifier
        ValueError: if session_context["session_root"] is set but not absolute
    """
    if not tool_name or not tool_name.isidentifier():
        raise ValueError(f"tool_name must be a valid identifier, got: {tool_name!r}")

    sc = session_context or {}
    session_root = sc.get("session_root")

    if session_root:
        sr = Path(session_root)
        if not sr.is_absolute():
            raise ValueError(
                f"session_context['session_root'] must be absolute, got: {sr}"
            )
        tasks_dir = sr / "tasks"
    else:
        tasks_dir = find_runtime_root() / "standalone" / tool_name

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    ws = tasks_dir / f"{tool_name}_{ts}_{short}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws
```

---

## §4 Implementation Phases

### Phase 1 — Shared Helper + Tests (~25 min)

**Files**:
- NEW: `src/openteam/server/resources/tools/_shared/__init__.py` (empty)
- NEW: `src/openteam/server/resources/tools/_shared/workspace_allocator.py` (per §3)
- NEW: `test/openteam/resources/tools/_shared/test_workspace_allocator.py`

**Test cases**:
- Path A: standalone with no session_context → `<root>/standalone/<tool>/...`
- Path A: env var override (`OPENTEAM_RUNTIME_DIR`) honored
- Path A: walk-up-to-src strategy
- Path A: cwd-based strategy when __file__ isn't under src
- Path A: ~/.openteam fallback
- Path B: with session_context["session_root"] → `<session_root>/tasks/...`
- Path B: relative `session_root` raises ValueError
- Naming: pattern matches `<tool>_<YYYYMMDD>_<HHMMSS>_<8hex>`
- Idempotency: two calls produce distinct dirs

### Phase 2 — `task` Standalone CLI Migration (~15 min)

**File**: `src/openteam/server/resources/tools/task/executor.py`

```python
# OLD (~line 148):
def _allocate_workspace(task_id: str) -> Path:
    server_dir = Path(__file__).resolve().parents[3]
    runtime_root = server_dir / "_runtime" / "tasks"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ws = runtime_root / f"task_{task_id}_{ts}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws

# NEW:
def _allocate_workspace(task_id: str, session_context: Optional[dict] = None) -> Path:
    """Allocate workspace; routes Path A (standalone) vs Path B (server-affiliated)."""
    from openteam.server.resources.tools._shared.workspace_allocator import (
        allocate_tool_workspace,
    )
    return allocate_tool_workspace("task", session_context)
```

Update `_resolve_workspace` to:
1. **REMOVE** the legacy `working_dir` heuristic (the UNSAFE check) — it's superseded by the new `session_root` contract
2. Call `_allocate_workspace(task_id, session_context)` directly

```python
def _resolve_workspace(session_context, task_id):
    return _allocate_workspace(task_id, session_context)
```

### Phase 3 — `create_role` Migration (~15 min)

**File**: `src/openteam/server/resources/tools/create_role/executor.py`

Add `_allocate_workspace` (mirrors Phase 2), update executor to allocate workspace at entry.

### Phase 4 — `role_setup` Migration (~10 min)

Same as Phase 3.

### Phase 5 — Tool Dispatcher Refactor (~45 min) 🔑 KEY CHANGE

**File**: `src/openteam/server/services/tool_dispatcher.py`

**Replace lines 205-210**:
```python
# OLD:
server_dir = self._session_context.get("server_dir", "")
if server_dir:
    task_working_dir = str(_Path(server_dir) / "tasks" / f"{tool_name}_{task_id}")
    _Path(task_working_dir).mkdir(parents=True, exist_ok=True)
else:
    task_working_dir = self._session_context.get("working_dir", "")

# NEW:
session_root = self._session_context.get("session_root", "")
if session_root:
    # Path B: server-affiliated; let executor's _allocate_workspace handle it
    # by passing session_root through session_context. NO pre-allocation here.
    task_working_dir = ""  # executor will allocate
else:
    # Edge case: no session_root → fall back to standalone (rare in dispatcher path)
    task_working_dir = ""
```

Then in `task_context` (line ~217-221):
```python
task_context = {
    **self._session_context,
    "task_id": task_id,
    "session_root": session_root,    # NEW: explicit session_root
    # "working_dir": task_working_dir,  # REMOVED: superseded
    "interactive": interactive_ref,
}
```

**File**: `src/openteam/server/services/conversation_service.py` (caller of dispatcher)

When constructing `session_context` to pass to ToolDispatcher, ensure `session_root` is populated from SessionStore:
```python
session_dir = self._session_store.get_session_dir(session_id)
session_context = {
    "session_id": session_id,
    "session_root": str(session_dir),  # NEW
    # ... rest
}
```

### Phase 6 — Slash-Path Fix (~30 min) 🚨 SECURITY FIX

**File**: `src/openteam/server/routes/manager_websocket_routes.py`

**Replace line 216** (the UNSAFE `working_dir = server source dir`):
```python
# OLD (line 216):
"working_dir": str(tools_dir.parent.parent),  # UNSAFE!

# NEW (in session_context construction):
"session_id": session_id,                     # from active websocket session
"session_root": str(session_store.get_session_dir(session_id)),  # SAFE
# REMOVED: "working_dir": ...
```

The slash-path now provides EXACTLY the same `session_context` contract as the agent-path. Executor's `_allocate_workspace` handles both uniformly.

### Phase 7 — SessionStore Expose API (~15 min)

**File**: `src/openteam/server/services/session_store.py`

Add method:
```python
def get_session_dir(self, session_id: str) -> Path:
    """Return the per-session directory for a given session_id.

    Returns: <runtime_root>/servers/<current>/sessions/<session_id>_<TS>/
    Creates the directory if it doesn't exist yet.
    """
    sessions_dir = self._server_dir / "sessions"
    # Find existing session dir (matches "<session_id>_*") or create new
    for d in sessions_dir.iterdir():
        if d.is_dir() and d.name.startswith(f"{session_id}_"):
            return d
    # Create new session dir
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    new_dir = sessions_dir / f"{session_id}_{ts}"
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir
```

This method already exists in spirit (session_state.json path resolution); just ensure it's a public callable that returns the dir path.

### Phase 8 — Update Test Scripts (~30 min)

**Files**:
- `test/openteam/resources/tools/task/test_task_agent_config_brta_with_multiflow_pti.py`
  - `test_real_cli_subprocess_plan_mode` → expect new path `_runtime/standalone/task/task_<TS>_<uuid>/`
  - Use `OPENTEAM_RUNTIME_DIR` env var to isolate test workspace
- NEW: `test/openteam/resources/tools/_shared/test_workspace_allocator.py` (Phase 1)
- NEW: `test/openteam/server/services/test_tool_dispatcher_session_paths.py` (verifies Path B routing)
- NEW: `test/openteam/server/routes/test_manager_websocket_routes_session_paths.py` (verifies slash-path uses session_root)
- NEW: `test/openteam/resources/tools/create_role/test_create_role_cli_smoke.py`
- NEW: `test/openteam/resources/tools/role_setup/test_role_setup_cli_smoke.py`

### Phase 9 — `.gitignore` + Documentation (~10 min)

```
# Runtime artifacts (workspaces, sessions, cache)
/_runtime/
```

Add `README.md` note: "Standalone CLI runs go to `_runtime/standalone/<tool>/`; server-affiliated runs go to `_runtime/servers/<server>/sessions/<session>/tasks/`."

### Phase 10 — Migration Script (~20 min, ONE-TIME)

`scripts/migrate_unified_workspace_layout.py`:

```python
"""ONE-TIME migration to unified workspace layout.

Migrates:
  1. src/openteam/server/_runtime/tasks/* → _runtime/standalone/task/*
  2. _runtime/servers/<server>/tasks/* → orphans report (NO auto-migration; these
     should be associated with sessions but we lack that mapping for historical data)
"""
import shutil
import sys
from pathlib import Path

def main():
    repo_root = Path(__file__).parent.parent

    # Migration 1: standalone CLI tasks
    old_standalone = repo_root / "src" / "openteam" / "server" / "_runtime" / "tasks"
    new_standalone = repo_root / "_runtime" / "standalone" / "task"
    if old_standalone.exists():
        new_standalone.mkdir(parents=True, exist_ok=True)
        moved = 0
        for old in old_standalone.iterdir():
            if not old.is_dir(): continue
            new = new_standalone / old.name
            if new.exists():
                print(f"  SKIP (exists): {old.name}")
                continue
            shutil.move(str(old), str(new))
            moved += 1
            print(f"  MOVED: {old.name}")
        print(f"Standalone migration: moved {moved} workspaces.")
        if old_standalone.exists() and not any(old_standalone.iterdir()):
            old_standalone.rmdir()

    # Migration 2: report orphans
    old_server_tasks = list((repo_root / "_runtime" / "servers").glob("*/tasks"))
    if old_server_tasks:
        print(f"\nWARNING: Found {len(old_server_tasks)} orphan server-task dirs:")
        for o in old_server_tasks:
            print(f"  {o}")
        print("These need manual review (cannot auto-associate with sessions).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## §5 Acceptance Criteria

### Helper-Level (Phase 1)
| # | Criterion |
|---|---|
| AC1 | `allocate_tool_workspace("task")` → `<root>/standalone/task/task_<TS>_<uuid8>/` |
| AC2 | `allocate_tool_workspace("task", {"session_root": "/abs/path"})` → `/abs/path/tasks/task_<TS>_<uuid8>/` |
| AC3 | `OPENTEAM_RUNTIME_DIR` env var overrides all other strategies |
| AC4 | Relative `session_root` raises ValueError |
| AC5 | Invalid `tool_name` raises ValueError |

### Standalone CLI (Phases 2-4)
| # | Criterion |
|---|---|
| AC6 | `task --plan "hi"` standalone → `_runtime/standalone/task/task_<TS>_<uuid8>/outputs/output.md` |
| AC7 | `create_role` standalone → `_runtime/standalone/create_role/create_role_<TS>_<uuid8>/...` |
| AC8 | `role_setup` standalone → `_runtime/standalone/role_setup/role_setup_<TS>_<uuid8>/...` |
| AC9 | Existing `test_real_cli_subprocess_plan_mode` still passes after path update |

### Server-Affiliated (Phases 5-7) 🔑 KEY
| # | Criterion |
|---|---|
| AC10 | Agent-path: tool spawned in session S1 → `_runtime/servers/<server>/sessions/<S1>_<TS>/tasks/<tool>_<TS>_<uuid8>/` |
| AC11 | Agent-path: tools from session S1 vs S2 land in DIFFERENT session dirs (no cross-pollution) |
| AC12 | Slash-path `/task --plan "hi"` → same per-session layout (no longer UNSAFE) |
| AC13 | No new workspaces created under `<server_dir>/tasks/` (the flat legacy location) |
| AC14 | `SessionStore.get_session_dir(session_id)` returns a stable absolute path |

### Cross-Cutting
| # | Criterion |
|---|---|
| AC15 | No new entries under `src/openteam/server/_runtime/` after migration |
| AC16 | `.gitignore` excludes `_runtime/` |
| AC17 | `ls _runtime/standalone/task/` is chronologically sortable |
| AC18 | Per-task subdir heuristic in `task/executor.py` still works for both Path A and Path B |
| AC19 | Migration script preserves old workspaces (no data loss) |

---

## §6 Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Slash-path session_id not available when routes invoke tools | HIGH | Phase 6 must verify websocket session has session_id by the time slash-cmd dispatches; add a fallback to allocate an ephemeral session if missing |
| Existing in-progress sessions break when server restarts after migration | MEDIUM | Migration is non-destructive; old paths preserved; if a session is mid-task, completion still uses old path until session ends |
| ConversationService doesn't pass session_root to dispatcher today | HIGH | Phase 5 includes the change; without it, dispatcher falls back to "" and tool re-allocates → BROKEN. Must be done atomically with Phase 5 |
| Multiple servers running concurrently → race on session_dir creation | LOW | `mkdir(parents=True, exist_ok=True)` is atomic enough; SessionStore already handles this |
| Tests that hardcode old paths break | MEDIUM | Phase 8 explicitly updates them; CI catches via AC9 |
| Hardcoded `working_dir` references elsewhere | MEDIUM | Grep `working_dir` across codebase; deprecate softly (keep accepting it but log warning) |
| RankEvolve session pattern doesn't fully apply (multi-task per session) | LOW | OpenTeam intentionally adds `tasks/` subdir layer that RankEvolve doesn't have |
| Cleanup policy unclear (when to gc old session task workspaces?) | LOW | Out of scope; document as OQ |
| `_runtime/standalone/` vs `_runtime/servers/` confusion in `ls` | LOW | Clear top-level naming; documented in README |
| Test environments may need OPENTEAM_RUNTIME_DIR set | LOW | Phase 8 sets it via pytest fixtures (`tmp_path`); document in test READMEs |
| Slash-path security fix (Phase 6) might affect currently-working flows | MEDIUM | Add transition period: log warning when old `working_dir` is provided; remove in next release |
| ToolDispatcher.task_working_dir field used downstream for UI display | LOW | Update UI message construction (line 247) to use `session_root` or task workspace |

---

## §7 Open Questions

| # | Question | Default Answer |
|---|---|---|
| OQ1 | Should `<session_id>` in path include the session creation timestamp suffix or just the bare ID? | Use full SessionStore directory name (`<session_id>_<TS>`) — already what SessionStore uses |
| OQ2 | What if `create_role`/`role_setup` are invoked from agent-path (not just slash-path)? | Phase 3/4 covers both — they accept session_context and route same as task |
| OQ3 | When a session ends, should its `tasks/` subdir be archived/deleted? | DEFER — separate cleanup policy plan |
| OQ4 | Should standalone CLI also write a session-like manifest at `_runtime/standalone/<tool>/index.jsonl`? | DEFER — nice-to-have |
| OQ5 | Should the `--runtime-dir` flag be added to all 3 CLIs for ad-hoc override? | DEFER — env var covers this |
| OQ6 | Should slash-path always create a new session if session_id is missing? | Phase 6 risk mitigation: yes, allocate ephemeral session |
| OQ7 | Should we use `os.makedirs(exist_ok=True)` or `Path.mkdir(parents=True, exist_ok=True)`? | Latter — more modern |
| OQ8 | Should `working_dir` backward compat be kept indefinitely or removed in N releases? | Keep for 1 release with deprecation warning, then remove |
| OQ9 | Should `OPENTEAM_RUNTIME_DIR` env var affect BOTH Path A and Path B? | YES — Path B uses it via SessionStore's `runtime_root` config |
| OQ10 | What if SessionStore.get_session_dir() needs to migrate to per-session task dir creation? | Lazy: dispatcher creates `tasks/` subdir on first allocation |

---

## §8 Out of Scope (Explicit Non-Goals)

| Item | Why Not |
|---|---|
| Cross-session workspace sharing / linking | Per-session isolation is a feature |
| Per-task GC / cleanup policy | Allocation only; cleanup is separate concern (OQ3) |
| Session archival / export tools | Separate plan |
| Multi-process workspace locking | Filesystem semantics sufficient |
| Database-backed workspace registry | Filesystem is fine for now |
| Per-session resource quotas | Out of scope |
| Workspace encryption / access control | Out of scope |
| Cross-server workspace sharing | Out of scope |
| Cleanup of old `_runtime/standalone/` workspaces | Manual or separate cron |
| `--runtime-dir` CLI flag per tool | Deferred (OQ5) |

---

## §9 Migration Strategy

### Order of Operations (CRITICAL)

Phases MUST be applied in this order to avoid breakage:

1. **Phase 1**: Helper (no impact on running code) — SAFE
2. **Phase 7**: SessionStore.get_session_dir() (additive method) — SAFE
3. **Phase 5 + ConversationService changes**: Wire session_root through dispatcher — REQUIRED before Phases 2-4 or session-bound paths break
4. **Phase 2**: task standalone migration — SAFE (only affects standalone CLI)
5. **Phase 3**: create_role migration — SAFE
6. **Phase 4**: role_setup migration — SAFE
7. **Phase 6**: Slash-path fix — REQUIRES Phase 5 to be done first (uses same session_root contract)
8. **Phase 8**: Test updates — REQUIRES Phases 2-6 done
9. **Phase 9**: .gitignore + README — last
10. **Phase 10**: Migration script — last, ONE-TIME

### Rollback Plan

Each phase is rollback-safe:
- Phases 1, 7 are additive (just delete new files)
- Phases 2-6 modify existing functions; keep old code as `_OLD_<name>` for 1 release
- Phase 8 changes are tests only
- Phase 9 is config
- Phase 10 is non-destructive (moves, not deletes)

### Feature Flag Suggestion

For extra safety, gate Phase 5 + Phase 6 behind env var `OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=1` for first release. Then default to ON in next release.

---

## §10 Comparison vs Predecessor Plan

| Aspect | Old Plan (`tool_workspace_allocation_enhancement_plan.md`) | New Plan (this doc) |
|---|---|---|
| Scope | Standalone CLI only | Both standalone AND server-affiliated |
| Server-affiliated path | Out of scope (intentionally) | Unified under same helper, routed by session_context |
| Slash-path UNSAFE bug | Acknowledged but out of scope | **FIXED** in Phase 6 |
| Per-session task attribution | N/A | **YES** — tasks nested under session dirs |
| SessionStore integration | None | **YES** — Phase 7 |
| ConversationService changes | None | **YES** — Phase 5 (wire session_root) |
| Tool dispatcher refactor | None | **YES** — Phase 5 |
| Phases | 7 | 10 |
| Effort | ~2 hours | ~4-5 hours |
| Files touched | 3 tool executors + tests | 3 tool executors + dispatcher + slash routes + SessionStore + ConversationService + tests |

### Migration From Old Plan

If you started implementing the predecessor plan (which only covered Path A):
- Phases 1-4 of OLD = Phases 1-4 of THIS (compatible)
- Phases 5-10 of THIS are ADDITIVE on top of OLD
- Re-use the helper from OLD Phase 1 (just add the `session_context` param)

---

## §11 Provenance

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-05-17 | Initial unified plan — covers BOTH standalone CLI (Path A) AND server-affiliated (Path B) workspaces. Adopts RankEvolve pattern (sessions own tasks). Integrates with existing OpenTeam SessionStore. Fixes slash-path UNSAFE bug. 10 phases, ~4-5 hours total effort. Supersedes the standalone-only predecessor plan. |
