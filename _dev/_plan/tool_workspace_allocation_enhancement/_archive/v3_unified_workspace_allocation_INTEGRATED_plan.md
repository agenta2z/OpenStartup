# Unified Tool Workspace Allocation — Integrated v3 Plan

**Author:** Tony Chen (integrating OpenStartup v1 + Cursor v2 + Rovo Dev critical review)
**Date drafted:** 2026-05-17 11:09
**Status:** Ready for review and implementation
**Supersedes:**
- `tool_workspace_allocation_enhancement_plan.md` (v0 — standalone CLI only)
- `unified_workspace_allocation_plan.md` (v1 — 697 lines)
- `/Users/tchen7/.cursor/plans/unified_tool_workspace_allocation_e34a5db8.plan.md` (Cursor v2 — 247 lines)

> **Why v3 exists.** v1 (OpenStartup) has the architectural depth, the actual implementation code (75 lines of `find_runtime_root` + `allocate_tool_workspace`), the migration/rollback strategy, the 13-row risk register, and explicit non-goals. Cursor's v2 has cleaner per-tool grouping, a Phase 0 doc-bump for provenance, the named `role_setup` concurrent-collision bug, the 51 leaked test workspace count, and per-test-file line numbers. Both miss: Phase 0 RED tests, permanent regression test, Windows path semantics, UUID8 collision handling, deploy-time `_runtime/` exclusion. v3 keeps all of v1's depth, adopts all of v2's precision, and adds the missing operational discipline.

> **If forced to pick ONE of the inputs today:** **v1 (OpenStartup, 697 lines)** — it ships the actual code, migration strategy, rollback plan, and feature flag that v2 lost in compression. v2 is operationally clearer in some phases but architecturally thinner. Full reasoning in §11.

---

## 1. Verified empirical claims (re-confirmed)

| # | Claim | Source |
|---|---|---|
| 1 | `_allocate_workspace` writes to `src/openteam/server/_runtime/tasks/` polluting source tree, hard-codes `task_` prefix breaking `role_setup`/`create_role` naming | `task/executor.py:149-160` |
| 2 | `tool_dispatcher.py` writes flat at `<server_dir>/tasks/<tool>_task-<uuid8>/` — NOT nested under session | `tool_dispatcher.py:186-208` |
| 3 | `role_setup`/`create_role` have a **name-based collision bug**: literal `task_id="role_setup"` causes 2 concurrent runs to collide on the same path | `role_setup/executor.py:1211-1236`, `create_role/executor.py:537-557` |
| 4 | `project_onboarding/executor.py` has NO workspace allocator — writes CWD-relative | `project_onboarding/executor.py:146-157` |
| 5 | `SessionStore.get_session_dir()` returns `None` for flat-file-only sessions; per-session dir layout exists in code but is UNUSED for tasks | `session_store.py:317-324` |
| 6 | `manager_websocket_routes.py:216` sets `working_dir = str(tools_dir.parent.parent)` — UNSAFE: deliberate to make executor fall back to its own allocator | `manager_websocket_routes.py:213-217` |
| 7 | **51 leaked test workspaces** exist on disk under `test/.../_runtime/` from prior runs | Cursor v2 (filesystem count) |
| 8 | RankEvolve makes `tasks/` a **sibling** of `sessions/`, not nested. OpenTeam's preferred design deliberately nests `tasks/` under `sessions/<id>/` for stronger session ownership | v1 §1.3 + Cursor v2 §"Honest Assessment" |

---

## 2. Target architecture

### 2.1 Two-path workspace contract

| Path | Trigger | Workspace location |
|---|---|---|
| **A — Standalone CLI** | `session_context` lacks `session_root` | `<repo>/_runtime/tasks/<tool>/<tool>_<TS>_<uuid8>/` |
| **B — Server-affiliated** | `session_context["session_root"]` set | `<session_root>/tasks/<tool>_<TS>_<uuid8>/` |

**Key insight (Cursor's framing):** both paths use `tasks/` as the immediate parent, so the mental model is consistent: a workspace is always at `<some_root>/tasks/<tool>_<TS>_<uuid8>/`. Only `<some_root>` differs.

### 2.2 Naming format (locked)

`<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>`

All underscores; lex-sortable; tool prefix per-workspace; UUID8 disambiguates within a second.

### 2.3 Directory layout end-state

```
<repo_root>/                                       (auto-discovered: ancestor of src/)
└── _runtime/                                       (.gitignore'd; deploy-excluded — see §7)
    ├── tasks/                                      Path A: standalone workspaces
    │   ├── task/task_20260517_103805_abc12345/
    │   ├── role_setup/role_setup_20260517_104010_def67890/
    │   ├── create_role/.../
    │   └── project_onboarding/.../
    └── servers/                                    Path B: server-affiliated workspaces
        └── server_20260517_103805_8e2f1a04/
            ├── server_info.json
            └── sessions/
                └── session-1234_20260517_103905/
                    ├── session_state.json
                    └── tasks/
                        ├── role_setup_20260517_104010_def67890/
                        └── task_20260517_104525_a1b2c3d4/
```

### 2.4 Session context contract

```python
session_context: dict[str, str] = {
    # Required for Path B; absent for Path A:
    "session_root": "/abs/path/to/<repo>/_runtime/servers/<srv>/sessions/<id>/",
    # Optional, kept for backward-compat for 2 releases (then deprecate):
    "working_dir": "/abs/path/to/...",  # if set with no session_root, treated as session_root parent if it ends in a session-id-shaped path
}
```

---

## 3. Shared helper — full implementation (from v1, verified)

**File:** `src/openteam/server/resources/tools/_shared/workspace_allocator.py` (NEW)

```python
"""Unified workspace allocation for OpenTeam tools.

Two-path architecture:
  - Path A (standalone CLI): <repo>/_runtime/tasks/<tool>/<tool>_<TS>_<uuid8>/
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
        Returns <runtime_root>/tasks/<tool>/<tool>_<TS>_<uuid8>/

    UUID8 collision handling: if mkdir reports the path already exists with
    non-empty content, retry up to 3 times with a fresh uuid. (UUID8 has ~32
    bits of entropy — collision probability is negligible per pair but not
    zero across 10^4+ tool runs. Defensive.)

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
        tasks_dir = find_runtime_root() / "tasks" / tool_name

    for attempt in range(3):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short = uuid.uuid4().hex[:8]
        ws = tasks_dir / f"{tool_name}_{ts}_{short}"
        try:
            ws.mkdir(parents=True, exist_ok=False)
            return ws
        except FileExistsError:
            if attempt == 2:
                raise
            continue
    raise AssertionError("unreachable")  # for type checker
```

> **v3 difference from v1:** uses `_runtime/tasks/<tool>/` (Cursor's grouping) instead of v1's `_runtime/standalone/<tool>/`. Both paths now use `tasks/` as the consistent immediate parent.
> **v3 difference from both v1 and v2:** explicit `mkdir(exist_ok=False)` + retry loop handles UUID8 collisions. v1 and v2 both used `exist_ok=True` which silently reuses a colliding directory.

---

## 4. Phased rollout — 11 phases

| Phase | What | Files | Risk | Reversible? |
|---|---|---|---|---|
| **0** | **RED tests pinning behavior contract** (NEW — neither input had this) | 1 new test file | none | n/a |
| 1 | Shared helper + unit tests | 2 new files | low | yes |
| 2 | `task` standalone migration (executor) | 1 file | low | yes |
| 3 | `create_role` migration (closes name-collision bug) | 1 file | low | yes |
| 4 | `role_setup` migration (closes name-collision bug) | 1 file | low | yes |
| 5 | `project_onboarding` migration (gains workspace it didn't have) | 1 file | low | yes |
| 6 | `SessionStore.get_session_dir` ensure-create + read-only split | 1 file | medium | yes |
| 7 | `tool_dispatcher.py` refactor (the key change) | 1 file | medium-high | yes |
| 8 | `factories.py` + `conversation_service.py` wire `session_id`/`session_root` | 2 files | medium | yes |
| 9 | `manager_websocket_routes.py` slash-path fix (security) | 1 file | medium | yes |
| 10 | Test migration (12 files; conftest fixture; clean 51 leaked dirs) | 13 files + 1 cleanup script | low | yes |
| 11 | `.gitignore` + Dockerfile exclusion + migration script + smoke verify | 2-3 config files + 1 script | low | yes |

**v3 difference:** v1 had 10 phases starting at 1; v2 had 11 starting at 0. v3 makes Phase 0 a **RED-tests phase** (not a doc-bump as Cursor proposed) — this is the discipline pattern from the inferencer-axes plans: pin the contract with failing tests before any source change.

---

## 5. Phase 0 — RED tests (NEW — pin contract before any source edit)

**File (NEW):** `test/openteam/resources/tools/_shared/test_workspace_allocator_contract.py`

12 tests, all `pytest.mark.xfail(strict=True)` before Phase 1 lands. Each turns GREEN as the corresponding phase lands.

| # | Test | What it pins | xfail until |
|---|---|---|---|
| 1 | `test_find_runtime_root_uses_env_var` | `$OPENTEAM_RUNTIME_DIR` wins over all other strategies | Phase 1 |
| 2 | `test_find_runtime_root_walks_up_from_file` | Walk-up to `src/` ancestor finds correct `_runtime/` | Phase 1 |
| 3 | `test_find_runtime_root_walks_up_from_cwd` | CWD walk-up fallback when `__file__` walk fails | Phase 1 |
| 4 | `test_find_runtime_root_fallback_home` | Falls back to `~/.openteam/_runtime` when all else fails | Phase 1 |
| 5 | `test_path_a_standalone_layout` | `allocate_tool_workspace("task", None)` → `_runtime/tasks/task/task_<TS>_<uuid8>/` exists | Phase 1 |
| 6 | `test_path_b_server_affiliated_layout` | `allocate_tool_workspace("role_setup", {"session_root": "/abs"})` → `/abs/tasks/role_setup_<TS>_<uuid8>/` exists | Phase 1 |
| 7 | `test_naming_format_lex_sortable` | Two allocations 1s apart sort correctly by string comparison | Phase 1 |
| 8 | `test_invalid_tool_name_raises` | Empty / non-identifier raises `ValueError` | Phase 1 |
| 9 | `test_relative_session_root_raises` | Non-absolute `session_root` raises `ValueError` | Phase 1 |
| 10 | `test_uuid8_collision_retried` | Mock `uuid.uuid4` to return colliding values; allocator retries 3× then raises | Phase 1 |
| 11 | `test_role_setup_concurrent_runs_dont_collide` | Two `allocate_tool_workspace("role_setup", None)` in same millisecond produce distinct paths | Phase 1 (proves the name-collision bug is fixed) |
| 12 | `test_project_onboarding_now_has_workspace` | After Phase 5, `project_onboarding` returns a path under `_runtime/tasks/project_onboarding/` | Phase 5 |

Also add **permanent regression tests** (always green, fail if regressions re-introduced):

| # | Test | What it guards |
|---|---|---|
| R1 | `test_no_module_writes_under_src_runtime` | grep `src/openteam/server/_runtime/` in test fixtures; assert no test creates paths there |
| R2 | `test_manager_websocket_routes_no_unsafe_working_dir_hack` | Read `manager_websocket_routes.py`; assert no `working_dir = str(tools_dir.parent.parent)` pattern (regression on §9 slash-path fix) |
| R3 | `test_executors_use_shared_allocator` | Reflectively check that each executor's workspace-allocation function imports from `_shared.workspace_allocator` |

---

## 6. Phases 1–11 — implementation detail

### Phase 1 — Shared helper + unit tests (~25 min)
- NEW: `src/openteam/server/resources/tools/_shared/__init__.py` (empty)
- NEW: `src/openteam/server/resources/tools/_shared/workspace_allocator.py` (§3 code)
- NEW: `test/openteam/resources/tools/_shared/test_workspace_allocator.py` covering all 4 fallback strategies, both paths, naming format, idempotency, error cases. (Phase 0's contract tests + these phase-1 unit tests together GREEN at end of Phase 1.)

### Phase 2 — `task` standalone migration (~15 min)
File: `src/openteam/server/resources/tools/task/executor.py`
- Rewrite `_allocate_workspace` (lines 149-160) and `_resolve_workspace` (lines 163-188) as thin wrappers around `allocate_tool_workspace("task", session_context)`.
- Backward-compat bridge: when `session_context` carries `working_dir` whose parent is a session dir, derive `session_root` from it (1 release).

### Phase 3 — `create_role` migration (~15 min)
File: `src/openteam/server/resources/tools/create_role/executor.py:537-557`
- Replace `_resolve_workspace` import; pass `session_context` directly to allocator.
- **Closes the literal-`task_id` collision bug** (test #11 turns GREEN).

### Phase 4 — `role_setup` migration (~10 min)
File: `src/openteam/server/resources/tools/role_setup/executor.py:1211-1236`
- Same migration as Phase 3.
- **Closes the literal-`task_id` collision bug** for `role_setup` (test #11 covers this leaf too).

### Phase 5 — `project_onboarding` migration (~15 min)
File: `src/openteam/server/resources/tools/project_onboarding/executor.py:146-157`
- Currently has NO allocator (writes CWD-relative). Add `allocate_tool_workspace("project_onboarding", session_context)`.
- Test #12 turns GREEN.

### Phase 6 — `SessionStore.get_session_dir` ensure-create (~15 min)
File: `src/openteam/server/services/session_store.py:317-324`
- Today: returns `None` if session is flat-file only.
- Change: when called from the dispatcher path, materialize a session directory if absent (lazy creation under `<server_dir>/sessions/<session_id>_<TS>/`).
- Keep the read-only behavior available via a separate `_find_session_dir` (private, already exists).

### Phase 7 — `tool_dispatcher.py` refactor (~45 min) 🔑 KEY CHANGE
File: `src/openteam/server/services/tool_dispatcher.py:186-223`
- Replace `<server_dir>/tasks/<tool>_<task_id>/` allocation with: ask SessionStore for `session_dir` → call `allocate_tool_workspace(tool_name, {"session_root": str(session_dir)})`.
- Update `task_context` dict to carry `session_root` (new) alongside `working_dir` (kept for backward-compat for 1 release; tools may ignore).
- Update UI message construction (line 247 — `task_working_dir` field used for UI display) to use `session_root` or task workspace path.

### Phase 8 — `factories.py` + `conversation_service.py` (~15 min)
- `factories.py:111-128`: add `session_id` and `session_root` to the dispatcher's `session_context` (today only `working_dir` and `server_dir`).
- `conversation_service.py`: wire `session_id` through to backend factory build.
- **CRITICAL atomicity:** must land together with Phase 7. Without it, dispatcher falls back to `""` and tool re-allocates → broken.

### Phase 9 — Slash-path fix (~30 min) 🚨 SECURITY FIX
File: `src/openteam/server/routes/manager_websocket_routes.py:213-217`
- Today line 216 sets `working_dir = str(tools_dir.parent.parent)` (= server source dir, deliberately UNSAFE so executor falls back to its own allocator).
- Replace with `session_root = SessionStore.get_session_dir(session_id)` so slash-path goes through the same Path B as agent-path.
- Phase 0 R2 regression test guards this permanently.

### Phase 10 — Test migration (~45 min)

**Add** `test/openteam/conftest.py` with a fixture/helper:
```python
@pytest.fixture
def standalone_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENTEAM_RUNTIME_DIR", str(tmp_path))
    return tmp_path
```

**Update these 12 test files** (all currently default `--output-dir` to `Path(__file__).parent / "_runtime"` with bare `<TS>` subdirs — 51 leaked dirs already on disk):
- `test/openteam/resources/tools/role_setup/test_role_setup.py` lines 245-250, 348-366
- `test/openteam/resources/tools/role_setup/test_role_setup_through_yaml.py` lines 98-101
- `test_role_setup_through_yaml_claude.py` lines 51-58
- `test_role_setup_inner_bta_through_yaml.py` lines 189-191
- `test/openteam/resources/tools/create_role/test_create_role.py` lines 104-108, 171-178
- `test_create_role_through_yaml.py` lines 96-100
- `test_create_role_through_yaml_claude.py` lines 44-46
- `test/openteam/resources/tools/project_onboarding/test_project_onboarding_through_yaml.py` lines 103-106
- `test/openteam/resources/tools/task/test_task_agent_config_brta_with_multiflow_pti.py` lines 756-758, 905-906, 1283-1291 (subprocess test asserts on the old `src/openteam/server/_runtime/tasks/` path)
- `test/openteam/resources/tools/role_setup/test_role_setup_via_task_shim.py` lines 70-75, 193-197
- `test/openteam/resources/tools/create_role/test_create_role_via_task_shim.py` lines 7, 67, 135-139

**Update** `test/openteam/resources/tools/task/test_task_helpers.py:293-318` — encodes the production `_resolve_workspace` contract; assertions need updating to expect the new `_runtime/tasks/<tool>/...` Path A and `<session_root>/tasks/...` Path B.

**Do not modify** (intentionally test workspace internals):
- `test_import_factory_isolation.py`
- `test/openteam/resources/tools/task/preflight/test_workspace_*.py`
- `test_deliverable_boundary_mock_topology.py`

**Clean** 51 leaked test workspaces under `test/.../_runtime/` via Phase 11 migration script.

### Phase 11 — `.gitignore` + Dockerfile + migration script + smoke (~30 min)

**`.gitignore`:** add `/_runtime/` at repo root.

**`Dockerfile` / build scripts:** add `--exclude='_runtime/'` to any `rsync`/`cp -r` of `src/`; explicit `.dockerignore` entry for `_runtime/`. (v3 addition — neither v1 nor v2 covered deploy-time exclusion.)

**Migration script `scripts/migrate_runtime_workspaces.py`** (NEW, non-destructive `shutil.move`):
- `src/openteam/server/_runtime/tasks/* → _runtime/tasks/task/*` (legacy task workspaces)
- `_runtime/servers/<server>/tasks/* → orphans report` (cannot auto-associate to historical sessions; safe to leave alone)
- Clean 51 leaked test workspaces under `test/.../_runtime/`.
- All operations: `--dry-run` flag default; require `--apply` for actual moves; log every action.

**Smoke verification:**
- Run `openteam-task --plan "hi"` standalone → confirm `_runtime/tasks/task/task_<TS>_<uuid8>/outputs/output.md`.
- Start server with `--real-sessions`, send `/role_setup ...` slash command → confirm path under `_runtime/servers/<server>/sessions/<session>/tasks/role_setup_<TS>_<uuid8>/`.
- Run pytest on the 12 updated test files.

---

## 7. Deploy hygiene (v3 addition — neither v1 nor v2 covered)

`.gitignore` only protects git. The following must ALSO exclude `_runtime/`:

| Path | What to add |
|---|---|
| `.dockerignore` | `_runtime/` |
| `Dockerfile` | `COPY src/ /app/src/` should NOT carry `_runtime/`; explicit `.dockerignore` is the cleanest guard |
| Any deploy script with `rsync` of `src/` | `--exclude='_runtime/'` |
| CI artifact upload steps | exclude `_runtime/` from artifact globs |
| Pre-commit hooks (if any) | reject commits that add files under `_runtime/` |

**Rationale:** `_runtime/` contains generated workspaces with potentially-large outputs (deliverables, intermediate state). If accidentally bundled in a deploy/Docker image:
- Image size bloats unboundedly over time.
- Stale session state ships to production and can confuse `SessionStore` on startup.
- Sensitive deliverables may leak into immutable artifacts.

Each guard is one line of config but the failure mode without them is silent. Phase 11 lands these.

---

## 8. Risk register — 13 risks from v1 + 5 v3 additions

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Slash-path session_id not available when routes invoke tools | 🔴 HIGH | Phase 9 must verify websocket session has session_id by the time slash-cmd dispatches; add a fallback to allocate an ephemeral session if missing |
| 2 | Existing in-progress sessions break when server restarts after migration | 🟡 MEDIUM | Migration is non-destructive; old paths preserved; if a session is mid-task, completion still uses old path until session ends |
| 3 | ConversationService doesn't pass session_root to dispatcher today | 🔴 HIGH | Phase 8 includes the change; without it, dispatcher falls back to `""` and tool re-allocates → BROKEN. Must be done atomically with Phase 7 |
| 4 | Multiple servers running concurrently → race on session_dir creation | 🟢 LOW | `mkdir(parents=True, exist_ok=True)` is atomic enough; SessionStore already handles this |
| 5 | Tests that hardcode old paths break | 🟡 MEDIUM | Phase 10 explicitly updates them; CI catches via AC9 |
| 6 | Hardcoded `working_dir` references elsewhere | 🟡 MEDIUM | Grep `working_dir` across codebase; deprecate softly (keep accepting, log warning) |
| 7 | RankEvolve session pattern doesn't fully apply (multi-task per session) | 🟢 LOW | OpenTeam intentionally adds `tasks/` subdir layer that RankEvolve doesn't have |
| 8 | Cleanup policy unclear (when to gc old session task workspaces?) | 🟢 LOW | Out of scope; document as OQ |
| 9 | `_runtime/tasks/` vs `_runtime/servers/` confusion in `ls` | 🟢 LOW | Clear top-level naming; documented in README |
| 10 | Test environments may need OPENTEAM_RUNTIME_DIR set | 🟢 LOW | Phase 10 sets it via pytest fixtures (`tmp_path`); document in test READMEs |
| 11 | Slash-path security fix (Phase 9) might affect currently-working flows | 🟡 MEDIUM | Add transition period: log warning when old `working_dir` is provided; remove in next release |
| 12 | ToolDispatcher.task_working_dir field used downstream for UI display | 🟢 LOW | Phase 7 updates UI message construction (line 247) to use `session_root` or task workspace |
| 13 | `role_setup`/`create_role` name-collision when two concurrent runs (the BUG today) | 🟡 MEDIUM | Phase 3/4 + UUID8 in naming closes this. Pinned by RED test #11. |
| **14** | **(v3) UUID8 collision under high tool-spawn rate** | 🟢 LOW | `mkdir(exist_ok=False)` + 3-retry loop in §3 code closes the silent-reuse failure mode that `exist_ok=True` would mask. Pinned by RED test #10. |
| **15** | **(v3) Windows path semantics — walk-up assumes POSIX `src/` ancestor** | 🟢 LOW | `Path.resolve()` normalizes per-platform; explicit OS-conditional test fixture in Phase 1 covers Windows-like paths. If Windows isn't a supported target today, document as known limitation. |
| **16** | **(v3) `_runtime/` accidentally shipped in Docker image / deploy** | 🟡 MEDIUM | Phase 11 deploy-hygiene section adds `.dockerignore` + rsync `--exclude` + CI artifact exclusion |
| **17** | **(v3) Re-introduction of the manager_websocket_routes UNSAFE hack** | 🟢 LOW | Permanent regression test R2 fails the build if any code re-introduces the pattern |
| **18** | **(v3) Re-introduction of executor-local workspace allocation** (bypassing the shared helper) | 🟢 LOW | Permanent regression test R3 reflectively asserts each executor's allocation path imports from `_shared.workspace_allocator` |

---

## 9. Acceptance criteria (from v1, extended)

### Helper-level (Phase 1)
- ☐ `find_runtime_root()` returns expected path under all 4 fallback strategies (RED tests 1-4 GREEN)
- ☐ `allocate_tool_workspace()` returns Path A for `session_context=None` (RED #5)
- ☐ `allocate_tool_workspace()` returns Path B when `session_root` set (RED #6)
- ☐ Naming format `<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>` is lex-sortable (RED #7)
- ☐ Invalid tool name + relative session_root both raise `ValueError` (RED #8, #9)
- ☐ UUID8 collision is retried up to 3 times then raises (RED #10)

### Standalone CLI (Phases 2-5)
- ☐ `openteam-task --plan "hi"` writes to `_runtime/tasks/task/task_<TS>_<uuid8>/outputs/output.md`
- ☐ `openteam-role-setup ...` writes to `_runtime/tasks/role_setup/role_setup_<TS>_<uuid8>/`
- ☐ `openteam-create-role ...` writes to `_runtime/tasks/create_role/create_role_<TS>_<uuid8>/`
- ☐ `openteam-project-onboarding ...` writes to `_runtime/tasks/project_onboarding/project_onboarding_<TS>_<uuid8>/` (was CWD before)
- ☐ Two concurrent `role_setup` runs produce distinct workspaces (RED #11 GREEN)

### Server-affiliated (Phases 6-9) 🔑 KEY
- ☐ Server-spawned tool writes to `_runtime/servers/<server>/sessions/<session>/tasks/<tool>_<TS>_<uuid8>/`
- ☐ `manager_websocket_routes.py` no longer contains the UNSAFE `working_dir = str(tools_dir.parent.parent)` line (R2 GREEN)
- ☐ Slash-path and agent-path produce the same workspace shape

### Cross-cutting
- ☐ `/_runtime/` in `.gitignore`
- ☐ `_runtime/` in `.dockerignore`
- ☐ All 12 updated test files pass pytest
- ☐ Migration script runs end-to-end on a real `_runtime/` state (`--dry-run` then `--apply`)
- ☐ Smoke run produces expected paths for all 4 tools (standalone + slash + agent)
- ☐ Permanent regression tests R1, R2, R3 in CI

---

## 10. Migration strategy

### Order of operations (CRITICAL)

The 11 phases must land in order. **Phases 7 and 8 must land atomically** (in the same PR or same commit window) — Phase 7 changes the dispatcher to call SessionStore, Phase 8 wires the session_root through factories. Either alone breaks the chain.

### Rollback plan

| Revert | Consequence |
|---|---|
| Phase 0 (RED tests) only | Tests disappear; no behavior change |
| Phase 1 (helper) only | Tests for the helper fail; no production change |
| Phases 2-5 (executor migrations) | Executors revert to local allocation; works because helper is unused |
| Phase 6 (SessionStore ensure-create) | Slash path falls back to old allocation; agent path unaffected |
| **Phase 7 (dispatcher) WITHOUT Phase 8 reverted** | **BROKEN** — dispatcher expects `session_root` from factories that no longer provides it. Atomic revert required. |
| Phase 9 (slash-path fix) only | Slash path returns to UNSAFE working_dir; permanent regression test R2 fails |
| Phase 10 (tests) only | 12 updated tests revert to old assertions; CI fails on the new layout |
| Phase 11 (gitignore/Dockerfile) only | `_runtime/` could re-enter git/Docker; otherwise harmless |

### Feature flag suggestion

Gate new Path B behavior in dispatcher behind `OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=1` for one release. When unset, fall back to old `<server_dir>/tasks/` allocation. After 1 release of stable rollout, remove the flag and the old code path.

---

## 11. Comparison + "if forced to pick one"

| Aspect | v0 (predecessor) | v1 (OpenStartup, 697L) | v2 (Cursor, 247L) | **v3 (this plan)** |
|---|---|---|---|---|
| Scope | Standalone CLI only | Both paths | Both paths | Both paths |
| Slash-path UNSAFE bug | Out of scope | FIXED in Phase 6 | FIXED in Phase 7 | FIXED in Phase 9 + permanent regression test R2 |
| Per-session task attribution | N/A | YES | YES | YES |
| Full helper source code | partial | ✅ 75 lines pasteable | description only | ✅ 75 lines + UUID8-collision retry |
| **Phase 0 RED tests** | ❌ | ❌ | ❌ (doc-bump instead) | ✅ 12 RED + 3 permanent regression |
| **UUID8 collision handling** | ❌ | `exist_ok=True` (silent reuse) | `exist_ok=True` (silent reuse) | ✅ `exist_ok=False` + retry |
| **Per-tool subdir under standalone** | flat | `_runtime/standalone/<tool>/` | `_runtime/tasks/<tool>/` | `_runtime/tasks/<tool>/` (v2's grouping; both paths use `tasks/`) |
| **`role_setup` collision bug named** | ❌ | ❌ | ✅ | ✅ (RED test #11) |
| **51 leaked test workspaces counted** | ❌ | ❌ | ✅ | ✅ (cleaned in Phase 11) |
| **`project_onboarding` no-allocator gap** | ❌ | partial | ✅ | ✅ (RED test #12) |
| **Per-test-file line numbers** | ❌ | ❌ | ✅ | ✅ |
| **Migration script + rollback** | ❌ | ✅ | partial | ✅ + `--dry-run` default |
| **Feature flag** | ❌ | ✅ | mentioned in 1 risk row | ✅ |
| **Risk register** | minimal | ✅ 13 risks | 5 risks | ✅ 13 + 5 = 18 |
| **Acceptance criteria** | minimal | ✅ per category | smoke only | ✅ per category |
| **Permanent regression tests** | ❌ | ❌ | ❌ | ✅ R1, R2, R3 |
| **Deploy hygiene** (.dockerignore, rsync exclude) | ❌ | ❌ | ❌ | ✅ §7 |
| **Windows path semantics** | ❌ | ❌ | ❌ | ✅ risk #15 + Phase 1 fixture |
| Length | shorter | 697 | 247 | ~580 (denser; less duplication) |

### 11.1 If forced to pick ONE input plan today

**Pick v1 (OpenStartup, 697 lines)**, not v2.

Three reasons:
1. **v1 ships the actual implementation code.** v2 describes WHAT to do; v1 also tells you HOW with pasteable Python. For a plan you'll execute from, the code matters.
2. **v1 has the migration strategy + rollback plan + feature flag**, which are load-bearing for landing this without breaking running sessions. v2 lost these in compression.
3. **v1 has 13 risks vs v2's 5.** The lost risks (multi-server race, ConversationService atomicity with Phase 7, ToolDispatcher.task_working_dir UI usage) are exactly the kind of cross-cutting concerns that bite during implementation.

v2 is **operationally clearer in some areas** (named `role_setup` bug, 51-leaked count, per-test-file line numbers, per-tool subdir under `tasks/`) but **architecturally and operationally thinner**. If you only have one plan to execute from, depth + safety > clarity.

**But you don't have to pick.** v3 = v1's depth + code + risks + migration + rollback + AC + v2's precision (Cursor's findings about `role_setup`, 51-leaked, `project_onboarding`, per-test-file lines, `tasks/` grouping) + v3 additions (RED tests, UUID8 collision retry, deploy hygiene, permanent regression tests, Windows risk).

---

## 12. Design principles applied

1. **One source of truth.** All four tools route through `_shared.workspace_allocator` — no per-tool reinvention.
2. **Two paths, one shape.** Both Path A and Path B end in `tasks/<tool>_<TS>_<uuid8>/` — consistent mental model.
3. **Pin contracts with RED tests first.** Phase 0 turns the spec into executable assertions before any source change.
4. **Pin invariants with permanent regression tests.** R1, R2, R3 prevent the workaround patterns from coming back.
5. **Atomic phase coupling where required.** Phases 7+8 land together; rollback matrix makes this explicit.
6. **Backward-compat bridges with sunset dates.** `working_dir` accepted with deprecation warning for 1 release; removed in the next.
7. **Defensive on silent failure modes.** `exist_ok=False` + retry over `exist_ok=True`; UUID8 collision is rare but real.
8. **Deploy hygiene is part of the plan, not an afterthought.** `.gitignore` is necessary but not sufficient; `.dockerignore`, rsync excludes, CI globs all matter.
9. **Migration is non-destructive by default.** `--dry-run` default in scripts; explicit `--apply` required.
10. **Documentation deduplicates code.** Phases reference §3 code instead of re-stating it; comparison table replaces narrative.

---

## 13. Estimated effort

| Phase | Implementation | Tests | Review | Total (h) |
|---|---|---|---|---|
| 0 (RED tests) | 0 | 1.5 | 0.5 | 2 |
| 1 (helper + unit tests) | 0.5 | 0.5 | 0.5 | 1.5 |
| 2-5 (executor migrations × 4) | 1.5 | 0 | 1 | 2.5 |
| 6 (SessionStore) | 0.5 | 0.5 | 0.5 | 1.5 |
| 7 (dispatcher 🔑) | 1 | 0.5 | 1 | 2.5 |
| 8 (factories + conversation_service) | 0.5 | 0.5 | 0.5 | 1.5 |
| 9 (slash-path fix) | 0.5 | 0.5 | 0.5 | 1.5 |
| 10 (test migration × 12 + conftest) | 1 | 1.5 | 1 | 3.5 |
| 11 (gitignore + dockerfile + migration script + smoke) | 1 | 1 | 0.5 | 2.5 |
| **Total** | **6.5** | **6.5** | **6** | **19** |

Roughly **2.5 engineer-days**. v1 estimated 4-5 hours; v2 estimated similar. Both under-estimated test work, deploy hygiene, and per-tool migration overhead. v3's 2.5 days is more honest.

---

*End of v3 integrated plan. Reviewers: please challenge §3 (the helper code — especially the UUID8 retry), §6 Phase 7+8 atomicity, §7 deploy hygiene completeness, §8 risk #15 (Windows), and §11.1 ("pick v1 if forced to one") most carefully.*

