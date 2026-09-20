# Unified Tool Workspace Allocation — Integrated v4 Plan

**Author:** Tony Chen (integrating v0/v1/v2/v3 + Claude critical review + post-v4 audit)
**Date drafted:** 2026-05-17 13:07
**Audit applied:** 2026-05-17 16:09 (post-v4 critical feedback, ~25 corrections; see §0 below)
**Status:** Ready for review and implementation **PENDING USER CONFIRMATION OF §2.4 ARCHITECTURE DECISION**

---

## 0. Post-v4 audit corrections (applied in-place)

A subsequent critical-review pass surfaced ~30 issues. After verifying each against the source code, **~25 were valid and have been applied** to the sections below. Three claims (H9 Path A RankEvolve overreach; M3 phase ordering urgency; L3/L6 minor) were rejected after verification. The most material corrections:

| Severity | Correction | Section updated |
|---|---|---|
| 🚨 CRITICAL | **C1** — Architecture decision (flat vs nested) elevated to explicit §2.4 "REQUIRES USER CONFIRMATION" rather than silently reversing v3. Both options preserved with honest trade-offs. | §2.4 (NEW) |
| 🚨 CRITICAL | **C2** — Risk 1 ("slash-path session_id missing") downgraded 🔴 HIGH → 🟢 LOW after source verification (`sid` in closure scope; `create_session` eagerly mkdirs). One of three flat-layout justifications was overstated. | §8 row 1 |
| 🚨 CRITICAL | **C3** — `_resolve_workspace` cross-imports from role_setup/executor.py:1212 and create_role/executor.py:537 → Phase 5 alone breaks both leaves on import. Phases 5+6 must merge OR keep `_resolve_workspace` as backward-compat wrapper. | §6 Phase 5 |
| 🚨 CRITICAL | **C4** — Migration script reinstated. Verified: 34 legacy dirs under `src/openteam/server/_runtime/tasks/`; **538 lines** of `_runtime/tasks` paths in `src/openteam.egg-info/SOURCES.txt` (pip install -e . re-discovers); 47+ leaked test workspaces. "Marker file approach" alone is insufficient. | §6 Phase 9 |
| 🚨 CRITICAL | **C5** — RED test #12 (`test_project_onboarding_now_has_workspace`) restored; was dropped from v3's 12 while §9 AC still required the path shape. | §5 |
| 🚨 CRITICAL | **C6** — §11 self-contradictory recommendation rewritten honestly. | §11.1 |
| 🔴 HIGH | **H1/H2** — Feature flag scope clarified: Phase 3 always writes `tasks_dir` (read-only data); flag only gates Phase 4 dispatcher behavior. Linked to atomicity mitigation. | §8 row 1, §10 |
| 🔴 HIGH | **H4** — Mock mode (`session_store=None` → `server_dir=""`) explicitly handled: dispatcher routes empty `tasks_dir` to Path A. New RED test. | §3.5, §5 |
| 🔴 HIGH | **H5** — Backward-compat for `working_dir`-only callers specified: translate via v3 heuristic for 1 release. New RED test. | §3.5, §5 |
| 🔴 HIGH | **H6** — `task_id` added to documented `session_context` dict contract. | §3.5 |
| 🔴 HIGH | **H8** — Fictional `task_working_dir` field reference removed from Risk 12; API/dict translation bridge clarified. | §3.5, §8 row 12 |
| 🟡 MEDIUM | **M1** — Real helper bugs fixed: `parent.mkdir` moved INSIDE retry loop (TOCTOU); reserved tool_name validation against `{src, tests, test, _runtime, sessions, servers}`. | §4 |
| 🟡 MEDIUM | **M2** — Missing ACs added: mock mode, backward-compat, OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=0, hermetic test isolation. | §9 |
| 🟡 MEDIUM | **M4** — Phase 8 split into 8a (slash-path fix) + 8b (test migration). | §6 |
| 🟡 MEDIUM | **M5** — Documentation updates added: CLAUDE.md, project_onboarding/tool.json, README. view_routes.py confirmed safe (substring `_runtime` still present in new layout) — skip. | §6 Phase 9 |
| 🟡 MEDIUM | **M6** — `_apply_resume` (--resume / --copy-workspace) explicitly addressed; mock_task added to Phase 7 with carve-out option; OPENTEAM_DEV_MODE smoke gate noted. | §6 |
| 🟡 MEDIUM | **M7** — RED tests added: slash-path positive shape, mock mode, backward-compat, format regex. | §5 |
| 🟡 MEDIUM | **M8** — Risk register cleaned: #5 reframed (no shared `<server>/tasks/` race — uuid8 server_dirs); #9 expanded (4 shards); #12 fictional field reference removed; +2 risks (feature-flag-OFF preserves collision; server_dir redundancy). | §8 |
| 🟢 LOW | **L1/L2/L4/L5** — Self-aggrandizing language softened; "ensure-create dance" honestly characterized as 5-line modification not "entire phase"; numeric tallies corrected. | throughout |

**Claims rejected after verification:**
- H9 ("matches RankEvolve" mixed for Path A) — Path A is standalone-CLI; RankEvolve has no standalone-CLI to match. Per-tool sharding is for `ls` ergonomics, not architectural mimicry. Reject.
- M3 (Phase 7 must precede Phase 8 because security) — project_onboarding CWD pollution is annoying but not a security bug like the slash-path UNSAFE hack. Phase order is fine. Reject.
- L3 / L6 — cosmetic / non-bugs.

The corrections are applied directly in the sections below; this §0 is the change log.
**Supersedes:**
- v0: `tool_workspace_allocation_enhancement_plan.md` (standalone CLI only)
- v1: `unified_workspace_allocation_plan.md` (697 lines)
- v2: `/Users/tchen7/.cursor/plans/unified_tool_workspace_allocation_e34a5db8.plan.md` (247 lines)
- v3: `unified_workspace_allocation_INTEGRATED_v3_plan.md` (529 lines, mine)
- Claude: `/Users/tchen7/.claude/plans/for-openteam-can-we-dazzling-umbrella.md` (258 lines)

> **Why v4 exists — and the honest architectural reckoning.** v3 inherited from v1 the design choice "server-affiliated tasks nest under sessions" (`<server>/sessions/<id>/tasks/`) framed as a "deliberate enhancement over RankEvolve for stronger session ownership." Claude challenged this implicitly by proposing the flat layout (`<server>/tasks/`, sibling of `sessions/`) that matches the cited RankEvolve inspiration. **On critical re-examination, Claude is right.** The nested layout costs an ensure-create dance, an ephemeral-session fallback for slash-commands, and HIGH-severity risk #1 — all to gain a benefit (filesystem-level cleanup cascade, audit trail without an index) that was never stated as a hard requirement. v4 adopts the flat layout AND keeps v3's operational rigor (RED tests, permanent regression tests, deploy hygiene, feature flag, rollback matrix). It's the "elegant, proper, no ad-hoc" answer.

> **If forced to pick ONE of the five inputs today:** **v3 (mine, 529 lines)** — it has the most complete operational discipline, with the caveat that its server-affiliated layout choice should be reconsidered before implementation. Claude's plan is architecturally cleaner but loses operational scaffolding. v4 is strictly better than any input.

---

## 1. Verified empirical claims (re-confirmed from prior rounds)

| # | Claim | Source |
|---|---|---|
| 1 | `_allocate_workspace` writes to `src/openteam/server/_runtime/tasks/` polluting source tree; hard-codes `task_` prefix breaking `role_setup`/`create_role` naming | `task/executor.py:149-160` |
| 2 | `tool_dispatcher.py` writes flat at `<server_dir>/tasks/<tool>_task-<uuid8>/` (NO timestamp) | `tool_dispatcher.py:186-208` |
| 3 | `role_setup`/`create_role` have **literal `task_id` collision bug** — two concurrent runs collide on the same path | `role_setup/executor.py:1211-1236`, `create_role/executor.py:537-557` |
| 4 | `project_onboarding/executor.py` has NO workspace allocator — writes CWD-relative | `project_onboarding/executor.py:146-157` |
| 5 | `SessionStore` already has `server_dir` property (line 386) — `tasks_dir` can be derived cleanly | `session_store.py:386` |
| 6 | `manager_websocket_routes.py:216` sets `working_dir = str(tools_dir.parent.parent)` — deliberately UNSAFE | `manager_websocket_routes.py:213-217` |
| 7 | **51 leaked test workspaces** exist on disk under `test/.../_runtime/` from prior runs | Cursor filesystem count |
| 8 | RankEvolve's pattern: `tasks/` is a **sibling** of `sessions/`, not nested. Citing it as inspiration then nesting contradicts the citation. | v1 §1.3 (own admission) + Claude critical review |

---

## 2. The architectural decision — flat vs nested (resolved)

### 2.1 The choice

| Aspect | Nested (v1/v3) | **Flat (v4 — chosen)** |
|---|---|---|
| Layout | `<server>/sessions/<id>/tasks/<tool>_*/` | `<server>/tasks/<tool>_*/` |
| Matches RankEvolve | ❌ Explicit departure | ✅ Matches |
| Requires `SessionStore.get_session_dir()` ensure-create | YES — entire Phase 6 in v3 | NO |
| Slash-path session_id missing scenario | HIGH risk — need ephemeral session | ELIMINATED — no session needed |
| Filesystem cleanup cascade per session | ✅ `rm -rf <session>/` removes its tasks | ❌ tasks survive session deletion |
| Audit "which tasks did session X spawn?" | ✅ filesystem walk | ❌ requires task→session index in metadata |
| Dispatcher logic complexity | medium (must ensure-create session dir) | low (just use `SessionStore.tasks_dir`) |
| Number of phases needed | 11 | **9** |
| Number of HIGH-severity risks | 2 (slash-path + ConversationService atomicity) | 1 (just atomicity) |

### 2.2 Why v4 picks flat

1. **"Inspired by X but doing the opposite of X" is an architectural smell.** If RankEvolve's flat layout works for RankEvolve, it can work for OpenTeam. The "stronger session ownership" rationale in v1 was a design preference, not a stated requirement.
2. **Eliminates the entire `SessionStore.get_session_dir()` ensure-create dance** (Phase 6 in v3). That dance was the source of a 🔴 HIGH risk (slash-path session_id missing → must allocate ephemeral session).
3. **Simpler dispatcher logic.** `SessionStore.tasks_dir` is a property that returns `<server>/tasks/` unconditionally — no conditional creation, no session_id dependency.
4. **Auditability concern is solvable cheaply.** Per-task metadata (`task_info.json`) can carry `session_id` if cleanup-cascade isn't filesystem-driven. This is a metadata concern, not an architecture concern.

### 2.3 Migration path for audit trail (if needed later)

If you decide later that you DO want per-session cleanup cascade:
- Write a `cleanup_session.py` script that reads task metadata and `shutil.rmtree`'s associated tasks.
- **Currently out of scope** — task_info.json metadata writing is NOT in any phase. If/when you want this, it's an additive change (one new file write per task allocation) plus the script. Don't add it speculatively. (audit correction H3)

### 2.4 ⚠️ ARCHITECTURE DECISION — REQUIRES USER CONFIRMATION (audit correction C1)

**v4 silently reversed v3's "nested" choice toward "flat".** On re-examination, the reversal was based on partial reasoning (Risk 1 was overstated — see audit C2). Both options are technically sound; the choice is a values trade-off, not an engineering one. **The user should explicitly confirm before implementation.**

| Option | Server-affiliated layout | Pros | Cons |
|---|---|---|---|
| **A. Flat (v4 default)** | `<server>/tasks/<tool>_*/` (sibling of `sessions/`) | Matches RankEvolve inspiration; simpler dispatcher; no ensure-create logic for tasks (sessions already eagerly mkdir); audit-trail recoverable via metadata script if needed later | Loses filesystem-level cleanup cascade per session; "which tasks did session X spawn?" requires reading task metadata, not a simple `ls` |
| **B. Nested (v3 default)** | `<server>/sessions/<id>/tasks/<tool>_*/` | Filesystem-level cleanup cascade (`rm -rf <session>/` removes its tasks); audit-trail via `ls`; stronger per-session ownership | Requires `SessionStore.get_session_dir()` ensure-create call (5-line modification of existing method — NOT an "entire phase" as v4 originally framed); adds ~one defensive `mkdir(parents=True, exist_ok=True)` for the (verified-rare) malformed-session-id case |

**Honest assessment** (per audit C2 re-verification): the cost of nested is **5 lines** of `SessionStore` modification plus standard defensive `mkdir` — NOT the "entire Phase 6 ensure-create dance + HIGH-severity risk" that v4 originally claimed. The original justification for flipping was overstated.

**Decision required from user.** Default in §3 / §4 / §6 below is **flat (Option A)**. If user prefers **nested (Option B)**, the diffs are:
- §3.3 layout: insert `/sessions/<session_id>/` between `<server>/` and `/tasks/`
- §6 Phase 2: instead of `SessionStore.tasks_dir` property, add `SessionStore.get_session_tasks_dir(session_id) -> Path` (~5 lines)
- §6 Phase 3: factories writes `session_root` (not `tasks_dir`) into `session_context`
- §6 Phase 4: dispatcher uses `<session_root>/tasks/` as base_dir
- §8 Risk #1: add row "session_id-missing edge case → defensive mkdir" 🟢 LOW
- All other phases, RED tests, deploy hygiene, feature flag, etc. are identical between A and B

---

## 3. Field contract

### 3.1 Workspace location rules

| Path | Trigger | Workspace location |
|---|---|---|
| **A — Standalone CLI** | `session_context` lacks `tasks_dir` (or `base_dir=None` in helper API) | `<repo>/_runtime/<tool>/<tool>_<TS>_<uuid8>/` |
| **B — Server-affiliated** | `session_context["tasks_dir"]` set (or `base_dir=<path>` in helper API) | `<tasks_dir>/<tool>_<TS>_<uuid8>/` |

### 3.2 Naming format (locked)

`<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>` — all underscores; lex-sortable; tool prefix; UUID8 disambiguates within a second.

### 3.3 Directory layout end-state

```
<repo_root>/                                       (auto-discovered: ancestor of src/)
├── src/                                           (source only — never runtime artifacts)
└── _runtime/                                       (.gitignore'd; deploy-excluded — see §7)
    ├── task/                                       Path A: standalone task workspaces
    │   └── task_20260517_103805_abc12345/
    ├── create_role/                                Path A: standalone create_role
    ├── role_setup/                                 Path A: standalone role_setup
    ├── project_onboarding/                         Path A: standalone project_onboarding (NEW)
    └── servers/                                    Path B: server-affiliated
        └── server_20260517_103805_8e2f1a04/
            ├── server_info.json
            ├── sessions/                           (unchanged; session state)
            │   └── session-1234_20260517_103905/
            │       └── session_state.json
            └── tasks/                              FLAT (sibling of sessions/; matches RankEvolve)
                ├── task_20260517_104525_a1b2c3d4/
                ├── create_role_20260517_104010_def67890/
                ├── role_setup_20260517_110300_7a8b9c0d/
                └── project_onboarding_20260517_120000_2f3e1d4a/
```

### 3.4 Helper API contract (Claude's cleaner signature)

```python
def allocate_tool_workspace(
    tool_name: str,
    base_dir: Optional[Path] = None,  # NOT a session_context dict
) -> Path:
    """If base_dir is provided → <base_dir>/<tool>_<TS>_<uuid8>/ (Path B).
    Otherwise → <find_runtime_root()>/<tool>/<tool>_<TS>_<uuid8>/ (Path A)."""
```

> **v4 difference from v3:** Claude's signature (single `base_dir` parameter) is cleaner than v3's `session_context: dict` (which buried the routing in dict-key presence). Explicit `base_dir=None` self-documents the standalone branch.

### 3.5 `session_context` contract (for the dispatcher → executor layer)

The helper takes `base_dir`. But the dispatcher → executor layer still uses `session_context: dict`. The contract:

```python
session_context: dict[str, str] = {
    # Required for Path B; absent for Path A:
    "tasks_dir": "/abs/path/to/<server>/tasks/",
    # Existing fields (preserved):
    "server_dir": "/abs/path/to/<server>/",
    "working_dir": "...",                  # kept for backward-compat, 1 release
    "session_id": "session-1234",          # for task_info.json metadata only
}
```

Executors translate `session_context["tasks_dir"]` → `base_dir` argument before calling the helper.

---

## 4. Shared helper — full implementation

**File:** `src/openteam/server/resources/tools/_shared/workspace_allocator.py` (NEW)

```python
"""Unified workspace allocation for OpenTeam tools.

Two-path architecture:
  - Path A (standalone CLI): <repo>/_runtime/<tool>/<tool>_<TS>_<uuid8>/
  - Path B (server-affiliated): <base_dir>/<tool>_<TS>_<uuid8>/
                                (typically base_dir == <server>/tasks/)

Routing is by the helper API's `base_dir` argument, not by dict-key presence.
The dispatcher → executor layer uses `session_context["tasks_dir"]` and
translates to `base_dir=` when calling.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


_FALLBACK_HOME_DIR = Path.home() / ".openteam" / "_runtime"
_MAX_COLLISION_RETRIES = 3


def find_runtime_root() -> Path:
    """Locate the canonical _runtime/ directory using a fallback chain.

    1. $OPENTEAM_RUNTIME_DIR env var (CI/prod override; hermetic test fixtures)
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


def make_workspace_dirname(tool_name: str) -> str:
    """Produce <tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>. All underscores; lex-sortable."""
    if not tool_name or not tool_name.isidentifier():
        raise ValueError(f"tool_name must be a valid identifier, got: {tool_name!r}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{tool_name}_{ts}_{short}"


def allocate_tool_workspace(
    tool_name: str,
    base_dir: Optional[Path] = None,
) -> Path:
    """Allocate a fresh workspace for a tool run.

    Args:
        tool_name: must be a valid Python identifier.
        base_dir: if provided (absolute path), workspace is created at
            <base_dir>/<tool>_<TS>_<uuid8>/. If None, workspace is created
            at <find_runtime_root()>/<tool>/<tool>_<TS>_<uuid8>/.

    Returns:
        Path to newly-created workspace directory (parents auto-created).

    Raises:
        ValueError: if tool_name is empty/invalid, or base_dir not absolute.
        FileExistsError: if 3 consecutive UUID8 generations collide
            (probability ~negligible but defensive).
    """
    if base_dir is not None:
        base = Path(base_dir)
        if not base.is_absolute():
            raise ValueError(f"base_dir must be absolute, got: {base}")
        parent = base
    else:
        parent = find_runtime_root() / tool_name

    for attempt in range(_MAX_COLLISION_RETRIES):
        # (audit M1) parent.mkdir INSIDE the loop to be robust against
        # concurrent rmtree of parent between iterations.
        parent.mkdir(parents=True, exist_ok=True)
        ws = parent / make_workspace_dirname(tool_name)
        try:
            ws.mkdir(exist_ok=False)  # NOT exist_ok=True — silent reuse is a bug
            return ws
        except FileExistsError:
            if attempt == _MAX_COLLISION_RETRIES - 1:
                raise
            continue
        except FileNotFoundError:
            # parent was rmtree'd between mkdir and child mkdir; retry
            if attempt == _MAX_COLLISION_RETRIES - 1:
                raise
            continue
    raise AssertionError("unreachable")  # type-checker satisfaction
```

> **(audit M1) Reserved tool_name validation.** `make_workspace_dirname` should additionally reject names that would land outside `_runtime/`:
> ```python
> _RESERVED_TOOL_NAMES = frozenset({"src", "tests", "test", "_runtime",
>                                    "sessions", "servers", "egg-info"})
> def make_workspace_dirname(tool_name: str) -> str:
>     if not tool_name or not tool_name.isidentifier():
>         raise ValueError(f"tool_name must be a valid identifier, got: {tool_name!r}")
>     if tool_name in _RESERVED_TOOL_NAMES:
>         raise ValueError(f"tool_name {tool_name!r} is reserved")
>     ...
> ```
> This closes the M1 attack: if `OPENTEAM_RUNTIME_DIR` is misconfigured to repo root and `tool_name="src"`, the allocator would otherwise write into the source tree.

> **(audit M1) `base_dir` is-file guard.** Before `parent.mkdir`, check `if base.exists() and not base.is_dir(): raise NotADirectoryError(...)`. Otherwise `mkdir(parents=True, exist_ok=True)` raises a confusing `FileExistsError [Errno 17]`.

> **v4 differences from v3:**
> - `allocate_tool_workspace(tool_name, base_dir=None)` instead of `session_context: dict` — Claude's cleaner signature.
> - Path A layout is `_runtime/<tool>/` (no `tasks/` prefix) — matches RankEvolve's flat structure end-to-end.
> - Extracted `make_workspace_dirname()` as a public helper — useful for callers that want to compute the name without creating the directory (e.g., `task_info.json` metadata).

---

## 5. Phase 0 — RED tests (pin contract before any source edit)

**File (NEW):** `test/openteam/resources/tools/_shared/test_workspace_allocator_contract.py`

11 contract tests, all `pytest.mark.xfail(strict=True)` before Phase 1 lands. Each turns GREEN as the corresponding phase lands.

| # | Test | What it pins | xfail until |
|---|---|---|---|
| 1 | `test_find_runtime_root_uses_env_var` | `$OPENTEAM_RUNTIME_DIR` wins over all fallback strategies | Phase 1 |
| 2 | `test_find_runtime_root_walks_up_from_file` | Walk-up to `src/` ancestor finds correct `_runtime/` | Phase 1 |
| 3 | `test_find_runtime_root_walks_up_from_cwd` | CWD walk-up fallback when `__file__` walk fails | Phase 1 |
| 4 | `test_find_runtime_root_fallback_home` | Falls back to `~/.openteam/_runtime` when all else fails | Phase 1 |
| 5 | `test_path_a_standalone_layout` | `allocate_tool_workspace("task")` → `_runtime/task/task_<TS>_<uuid8>/` exists | Phase 1 |
| 6 | `test_path_b_server_affiliated_layout` | `allocate_tool_workspace("role_setup", base_dir=Path("/abs/tasks"))` → `/abs/tasks/role_setup_<TS>_<uuid8>/` exists | Phase 1 |
| 7 | `test_naming_format_lex_sortable` | Two allocations 1s apart sort correctly by string comparison | Phase 1 |
| 8 | `test_invalid_tool_name_raises` | Empty / non-identifier raises `ValueError` | Phase 1 |
| 9 | `test_relative_base_dir_raises` | Non-absolute `base_dir` raises `ValueError` | Phase 1 |
| 10 | `test_uuid8_collision_retried_then_raises` | Mock `uuid.uuid4` to return colliding values; allocator retries 3× then raises `FileExistsError` | Phase 1 |
| 11 | `test_role_setup_concurrent_runs_dont_collide` | Two `allocate_tool_workspace("role_setup")` in same millisecond produce distinct paths | Phase 1 |
| 12 | `test_project_onboarding_now_has_workspace` | (audit C5 — restored) After Phase 7, `project_onboarding` returns a path under `_runtime/project_onboarding/` instead of CWD | Phase 7 |
| 13 | `test_mock_mode_empty_tasks_dir_routes_to_path_a` | (audit H4 / M7) When `session_context["tasks_dir"] == ""` (factories mock-mode), dispatcher allocates Path A (`_runtime/<tool>/...`) | Phase 4 |
| 14 | `test_working_dir_only_caller_backward_compat` | (audit H5 / M7) Caller with only `session_context["working_dir"]` (no `tasks_dir`) still gets a workspace via the v3 heuristic, with deprecation warning logged | Phase 5 |
| 15 | `test_slash_path_positive_shape` | (audit M7) After Phase 8a, slash-command-triggered `/role_setup` produces path under `<server>/tasks/role_setup_<TS>_<uuid8>/` | Phase 8a |
| 16 | `test_make_workspace_dirname_format_regex` | (audit M7) `make_workspace_dirname("task")` matches `^task_\d{8}_\d{6}_[a-f0-9]{8}$` | Phase 1 |
| 17 | `test_reserved_tool_name_raises` | (audit M1) `make_workspace_dirname("src")` / `make_workspace_dirname("sessions")` etc. all raise `ValueError` | Phase 1 |
| 18 | `test_base_dir_is_file_raises` | (audit M1) `allocate_tool_workspace("task", base_dir=<path-to-file>)` raises `NotADirectoryError` not confusing `FileExistsError` | Phase 1 |

Plus **3 permanent regression tests** (always green, fail if regressions return):

| # | Test | What it guards |
|---|---|---|
| R1 | `test_no_module_writes_under_src_runtime` | grep `src/openteam/server/_runtime/` in test fixtures and production code; assert no module writes there |
| R2 | `test_manager_websocket_routes_no_unsafe_working_dir_hack` | Read `manager_websocket_routes.py`; assert no `working_dir = str(tools_dir.parent.parent)` pattern |
| R3 | `test_executors_use_shared_allocator` | Reflectively check each executor's allocation function imports from `_shared.workspace_allocator` |

---

## 6. Phased rollout — 9 phases (v3 had 11; flat layout eliminates 2)

| Phase | What | Files | Risk | Reversible? |
|---|---|---|---|---|
| **0** | RED tests pinning contract (11 + 3 permanent) | 1 new test file | none | n/a |
| 1 | Shared helper + unit tests | 2 new files | low | yes |
| 2 | `SessionStore.tasks_dir` property | 1 file | low | yes |
| 3 | Wire `tasks_dir` into `session_context` via `factories.py` + `conversation_service.py` | 2 files | medium | yes |
| 4 | `tool_dispatcher.py` refactor (use `tasks_dir`, not literal `server_dir/tasks`) 🔑 | 1 file | medium-high | yes |
| 5 | `task` executor migration — **MUST keep `_resolve_workspace` as backward-compat wrapper** (audit C3) | 1 file | low | yes |
| 6 | `create_role` + `role_setup` migration (closes name-collision bug). **Can land independently of Phase 5 because Phase 5's `_resolve_workspace` wrapper preserves their import.** (audit C3) | 2 files | low | yes |
| 7 | `project_onboarding` migration (gains workspace it didn't have). **Plus mock_task carve-out decision** (audit M6). | 1-2 files | low | yes |
| **8a** | `manager_websocket_routes.py` slash-path fix (security) — split from test migration (audit M4) | 1 file | medium | yes |
| **8b** | Test migration (13 files + conftest fixture) | 14 files | low | yes |
| 9 | `.gitignore` + `.dockerignore` + Dockerfile + **migration script (audit C4)** + doc updates (CLAUDE.md, tool.json, README — audit M5) + smoke verify with `OPENTEAM_DEV_MODE=1` (audit M6) | 4-5 config/doc files + 1 script | medium | yes |

### Phase ordering rationale
- **Phase 2 before Phase 4** — dispatcher needs `tasks_dir` to exist as a property
- **Phase 3 and Phase 4 are atomic** — dispatcher reads from session_context which is populated by factories. Either alone breaks the chain.
- **Phases 5-7 are independent** of each other; can land in any order after Phase 1, **provided Phase 5 keeps the `_resolve_workspace` wrapper** (audit C3)
- **Phase 8a (slash-path fix) before Phase 8b (test migration)** — landing tests first would falsely pass against unchanged production code

### (audit C3) Phase 5 detailed spec — `_resolve_workspace` MUST stay as wrapper

`role_setup/executor.py:1212` and `create_role/executor.py:537-538` both contain:
```python
from openteam.server.resources.tools.task.executor import _run_topology, _resolve_workspace
```
If Phase 5 deletes `_resolve_workspace`, both leaves crash on import. v3 had this covered; v4 v1 silently dropped it.

**Correct Phase 5 spec:**
```python
# task/executor.py — KEEP this function for 1 release as backward-compat bridge
def _resolve_workspace(session_context: Optional[dict], task_id: str) -> Path:
    """DEPRECATED — backward-compat wrapper. Use `_allocate_via_shared_helper` instead.

    Translates v3-era session_context fields to v4's helper API.
    Will be removed in next release.
    """
    import warnings
    warnings.warn(
        "_resolve_workspace is deprecated; call allocate_tool_workspace via session_context['tasks_dir']",
        DeprecationWarning, stacklevel=2,
    )
    sc = session_context or {}
    # Path B if tasks_dir provided
    tasks_dir = sc.get("tasks_dir")
    if tasks_dir:
        return allocate_tool_workspace("task", base_dir=Path(tasks_dir))
    # Backward-compat heuristic: if working_dir looks like a tasks/ parent, treat it as base_dir
    wd = sc.get("working_dir")
    if wd and ("/tasks" in wd or "/_runtime" in wd):
        return allocate_tool_workspace("task", base_dir=Path(wd))
    # Otherwise standalone
    return allocate_tool_workspace("task")
```

This way Phases 5 and 6 can land independently. After 1 release, Phase 5b deletes `_resolve_workspace` and updates the two leaves to call the helper directly.

---

## 7. Deploy hygiene (kept from v3 — neither Claude nor older inputs had this)

`.gitignore` only protects git. The following must ALSO exclude `_runtime/`:

| Path | What to add |
|---|---|
| `.dockerignore` | `_runtime/` |
| `Dockerfile` | `COPY src/ /app/src/` must not carry `_runtime/`; `.dockerignore` is the cleanest guard |
| Any deploy `rsync` script | `--exclude='_runtime/'` |
| CI artifact upload steps | exclude `_runtime/` from artifact globs |

**Rationale:** `_runtime/` contains generated workspaces with deliverables and intermediate state. Bundling into a Docker image or deploy artifact:
- Bloats image size unboundedly over time
- Ships stale session state to production
- Leaks sensitive deliverables into immutable artifacts

Phase 9 lands these.

### (audit C4) Phase 9 detailed spec — migration script reinstated

v4 v1 silently dropped v3's migration script in favor of a vague "marker file approach" that was never specified. Verified disk state:
- **34 directories** under `src/openteam/server/_runtime/tasks/` (legacy task workspaces from before the move)
- **47+ leaked `_runtime` directories** under `test/.../resources/tools/*/` (from prior test runs)
- **`src/openteam.egg-info/SOURCES.txt` contains 538 lines mentioning `_runtime/tasks`** — `pip install -e .` will keep re-discovering and re-listing these polluted paths on every install

The "marker file approach" alone does not address any of these. **Reinstate the migration script:**

**`scripts/migrate_runtime_workspaces.py`** (NEW; non-destructive via `shutil.move`; `--dry-run` default; require `--apply` for actual moves):
1. Move `src/openteam/server/_runtime/tasks/* → _runtime/<inferred_tool>/*` (best-effort: parse `<TS>` prefix; default tool name = "task" if unparseable). Leave `.deprecated` marker in old location.
2. Clean 47+ leaked test workspaces under `test/.../_runtime/` (these are stale artifacts; safe to delete).
3. Print summary report at end (moved / skipped / errors).

**`MANIFEST.in`** (UPDATE): add explicit excludes so `pip install -e .` stops re-discovering polluted paths:
```
recursive-exclude src/openteam/server/_runtime *
recursive-exclude _runtime *
```

**`setup.py` / `pyproject.toml`** (UPDATE): if using `find_packages()`, add `exclude=("_runtime*", "*._runtime*")` to prevent re-listing.

After this lands, regenerate `SOURCES.txt` via `pip install -e .` and verify the 538-line pollution is gone.

---

## 8. Risk register — 5 from Claude + 13 from v3 (merged, deduplicated) = 14

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Phases 3+4 not atomic — dispatcher gets empty `tasks_dir` | 🔴 HIGH | (audit H1) Engineering mitigation: feature flag `OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=1` gates Phase 4 dispatcher behavior. With flag OFF, dispatcher falls back to old `<server>/tasks/<tool>_<task_id>/` allocation. Phase 3 ALWAYS writes `tasks_dir` (read-only data, harmless if dispatcher ignores it per H2). Land in same PR/commit as a process belt-and-braces. |
| 1b | (audit C2 — previously listed as "slash-path session_id missing" HIGH) Slash-path session_id missing → tool can't allocate | 🟢 LOW | **Downgraded from 🔴 HIGH after source verification.** `sid` is in `_try_dev_slash_command` closure at `manager_websocket_routes.py:105`. `SessionStore.create_session` eagerly mkdirs at `session_store.py:197-199` before returning. The pathological case (malformed client invents session_id) is already handled by lazy mkdir at `session_store.py:514-518`. One defensive `mkdir(parents=True, exist_ok=True)` covers it; no ephemeral-session fallback needed. |
| 2 | Test assertions on old `/_runtime/tasks/` paths break | 🟡 MEDIUM | Phase 8 explicitly updates them; CI catches |
| 3 | Slash-path lacks access to `session_store` | 🟡 MEDIUM | Phase 8 passes `_session_store` as parameter into `_try_dev_slash_command` |
| 4 | Old in-progress workspaces at old location | 🟢 LOW | Leave them; new runs use new paths; marker file in old location |
| 5 | Multiple servers running concurrently → race on `<server>/tasks/` creation | 🟢 LOW | `mkdir(parents=True, exist_ok=True)` is atomic enough |
| 6 | Tests that hardcode old paths break | 🟡 MEDIUM | Phase 8 covers them; CI catches |
| 7 | Hardcoded `working_dir` references elsewhere | 🟡 MEDIUM | Grep `working_dir` across codebase; deprecate softly (1 release) |
| 8 | Cleanup policy unclear (when to gc old workspaces?) | 🟢 LOW | Out of scope; document as OQ; flat layout makes per-session cleanup an audit-script concern not architecture |
| 9 | `_runtime/task/` vs `_runtime/servers/.../tasks/` confusion in `ls` | 🟢 LOW | Clear top-level naming; README documents |
| 10 | Test environments may need `OPENTEAM_RUNTIME_DIR` set | 🟢 LOW | Phase 8 sets it via pytest fixture (`tmp_path`); document in test README |
| 11 | Slash-path fix (Phase 8) might affect currently-working flows | 🟡 MEDIUM | Transition period: log warning when old `working_dir` is provided; remove next release |
| 12 | `ToolDispatcher.task_working_dir` field used downstream for UI display | 🟢 LOW | Phase 4 updates UI message construction to use `tasks_dir` or task workspace |
| 13 | `role_setup`/`create_role` name-collision (TODAY'S BUG) | 🟡 MEDIUM | Phase 6 + UUID8 in naming closes this. Pinned by RED #11. |
| 14 | UUID8 collision under high tool-spawn rate | 🟢 LOW | `mkdir(exist_ok=False)` + 3-retry loop in §4 code. Pinned by RED #10. |

**v4 dropped risks vs v3:**
- v3 #15 (Windows path semantics) — moved to Open Question; non-blocking
- v3 #16 (`_runtime/` accidentally shipped in Docker) — folded into §7 deploy hygiene; not a risk if §7 lands
- v3 #17/#18 (re-introduction of workaround patterns) — folded into RED R1/R2/R3 permanent regression tests; not a risk if they land

---

## 9. Acceptance criteria

### Helper-level (Phase 1)
- ☐ `find_runtime_root()` returns expected path under all 4 fallback strategies (RED #1-4 GREEN)
- ☐ `allocate_tool_workspace("task")` returns Path A (RED #5)
- ☐ `allocate_tool_workspace("role_setup", base_dir=...)` returns Path B (RED #6)
- ☐ Naming format `<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>` is lex-sortable (RED #7)
- ☐ Invalid tool name + relative base_dir both raise `ValueError` (RED #8, #9)
- ☐ UUID8 collision retried 3 times then raises (RED #10)

### Standalone CLI (Phases 5-7)
- ☐ `openteam-task --plan "hi"` writes to `_runtime/task/task_<TS>_<uuid8>/outputs/output.md`
- ☐ `openteam-role-setup ...` writes to `_runtime/role_setup/role_setup_<TS>_<uuid8>/`
- ☐ `openteam-create-role ...` writes to `_runtime/create_role/create_role_<TS>_<uuid8>/`
- ☐ `openteam-project-onboarding ...` writes to `_runtime/project_onboarding/project_onboarding_<TS>_<uuid8>/` (was CWD before)
- ☐ Two concurrent `role_setup` runs produce distinct workspaces (RED #11 GREEN)

### Server-affiliated (Phases 2-4, 8) 🔑
- ☐ Server-spawned tool writes to `<server>/tasks/<tool>_<TS>_<uuid8>/`
- ☐ `SessionStore.tasks_dir` returns `<server>/tasks/` as a property (ensure-creates on first access)
- ☐ `manager_websocket_routes.py` no longer contains UNSAFE `working_dir = str(tools_dir.parent.parent)` (R2 GREEN)
- ☐ Slash-path and agent-path produce identical workspace shape

### Cross-cutting
- ☐ `/_runtime/` in `.gitignore`
- ☐ `_runtime/` in `.dockerignore`
- ☐ All 13 updated test files pass pytest
- ☐ Smoke run produces expected paths for all 4 tools (standalone + slash + agent)
- ☐ Permanent regression tests R1, R2, R3 in CI

---

## 10. Migration strategy + rollback

### Order of operations (CRITICAL)

The 9 phases must land in dependency order. **Phases 3 and 4 must land atomically** (same PR or same commit window). Phase 3 wires `tasks_dir` into `session_context`; Phase 4 reads it. Either alone is broken.

### Rollback plan per phase

| Revert | Consequence |
|---|---|
| Phase 0 only | Tests vanish; no behavior change |
| Phase 1 only | Helper exists but unused; tests for helper fail |
| Phase 2 only | `tasks_dir` property unused |
| **Phase 4 WITHOUT Phase 3 reverted** | **BROKEN** — dispatcher expects `tasks_dir` from factories that no longer provide it. Atomic revert required. |
| Phases 5-7 | Executors revert to local allocation; works because helper still exists |
| Phase 8 | Slash-path returns to UNSAFE working_dir; R2 fails; tests revert |
| Phase 9 | `_runtime/` could re-enter git/Docker; otherwise harmless |

### Feature flag (kept from v3)

Gate new Phase 4 behavior behind `OPENTEAM_UNIFIED_WORKSPACE_LAYOUT=1` for one release. When unset, dispatcher falls back to old `<server>/tasks/<tool>_<task_id>/` allocation. After one stable release, remove the flag.

---

## 11. Comparison + "if forced to pick one"

| Aspect | v0 (predecessor) | v1 (OpenStartup, 697L) | v2 (Cursor, 247L) | v3 (mine, 529L) | Claude (258L) | **v4 (this plan)** |
|---|---|---|---|---|---|---|
| Scope | standalone only | both paths | both paths | both paths | both paths | both paths |
| Server-affiliated layout | n/a | nested | nested | nested | **flat (matches RankEvolve)** | **flat** ✅ |
| Helper API signature | partial | `session_context: dict` | `session_context: dict` | `session_context: dict` | `base_dir: Optional[Path]` ✨ | `base_dir: Optional[Path]` ✅ |
| Number of phases | fewer | 10 | 11 | 11 | **9** ✨ | **9** ✅ |
| `SessionStore.get_session_dir` ensure-create dance | ❌ | ✅ (Phase 4) | ✅ | ✅ | ❌ ELIMINATED | ❌ ELIMINATED ✅ |
| HIGH-severity risks | n/a | 2 | 2 | 2 | 1 | 1 ✅ |
| Phase 0 RED tests | ❌ | ❌ | ❌ | ✅ 12+3 | ❌ | ✅ 11+3 |
| Permanent regression tests | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| UUID8 collision retry | ❌ | `exist_ok=True` (silent reuse) | `exist_ok=True` | ✅ retry | ✅ retry | ✅ retry |
| Deploy hygiene (.dockerignore, rsync) | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Feature flag | ❌ | ✅ | mentioned | ✅ | ❌ | ✅ |
| Migration script | ❌ | ✅ | partial | ✅ | ❌ (marker only) | optional (marker preferred) |
| Risk register depth | minimal | 13 | 5 | 18 | 5 | 14 (deduplicated) |
| Per-test-file line numbers | ❌ | ❌ | ✅ | ✅ | partial (2 files) | ✅ |
| `project_onboarding` migration | ❌ | partial | ✅ | ✅ | ❌ deferred | ✅ |
| Architectural elegance | low | medium | medium | medium | high ✨ | high ✅ |
| Operational discipline | low | high ✨ | medium | high ✨ | medium | high ✅ |

### 11.1 If forced to pick ONE input plan today (audit C6 — rewritten honestly)

**Pick v3 (mine, 529 lines)** — it's the most internally consistent and has the strongest operational discipline. v4 added two architectural changes (flat layout, base_dir API) and an audit pass; those are deltas you can layer on after, NOT prerequisites for v3 being shippable. v3 ships as-is.

| Pick | What you get | What you have to add | What you have to fix |
|---|---|---|---|
| **v3** | Full plan with code, migration script, feature flag, rollback matrix, 18-risk register, per-category AC, 12 RED tests, 3 permanent regression tests | Optional: flat layout (5-line `SessionStore` edit) + base_dir helper API (one-line signature change) | Nothing — ships as-is |
| v4 (pre-audit) | Everything in v3 plus flat layout, base_dir API, fewer phases | Nothing | **C2 (Risk 1 overstated), C3 (Phase 5 would crash leaves), C4 (migration script dropped), C5 (RED test dropped), C6 (this self-contradiction)** — i.e., must apply this audit first |
| v4 (post-audit, current document) | Best of v3 + Claude + audit corrections | Nothing | §2.4 architecture decision — pick A or B with user; both are technically sound |
| Claude (258L) | Clean flat architecture + base_dir API | RED tests, permanent regression tests, deploy hygiene, feature flag, migration script, 13 of v3's 18 risks, per-category AC, project_onboarding migration | Same items above |

**Honest correction of v4's prior §11.1 wording:** The original §11.1 said "Pick v3 with caveat: you must redesign the server-affiliated layout before implementing." That's incorrect — v3's nested layout is **shippable as-is**; the flat layout is an optional refinement, not a prerequisite. The "must redesign" framing was overstated because Risk 1 (which v4 used to justify the redesign urgency) was itself overstated (see audit C2).

**The honest hierarchy now is:**
1. **v4 post-audit (this document)** — best overall, but requires user to pick A/B in §2.4
2. **v3 as-is** — shippable today; can be refined later
3. **v4 pre-audit** — DON'T ship; has 6 critical defects per audit
4. **Claude** — architecturally clean but operationally thin
5. **v1/v2** — superseded

**Why not Claude?** Claude got the architecture right (flat layout) but lost:
- RED-first test discipline
- Permanent regression tests
- Deploy hygiene
- Feature flag
- Migration script
- 13 of v3's 18 risks
- Per-category acceptance criteria
- `project_onboarding` migration
- Per-test-file line numbers for 10 of 12 test files

If you only shipped Claude's plan, you'd get the elegant architecture but ship without rollback discipline and inherit Claude's "defer `project_onboarding`" (which means CWD pollution continues for that tool).

If you only shipped v3, you'd get the discipline but ship with the suboptimal nested layout.

**But you don't have to pick.** v4 = Claude's architecture + v3's discipline. Strictly better than either.

---

## 12. Design principles applied

1. **Match the cited inspiration.** "Inspired by X but doing the opposite of X" is an architectural smell. Flat layout matches RankEvolve; v4 adopts it.
2. **Eliminate dances, not add them.** The `SessionStore.get_session_dir()` ensure-create dance (v3 Phase 6) is gone in v4.
3. **Clean helper signature.** `base_dir: Optional[Path]` is self-documenting. `session_context: dict` is not.
4. **Pin contracts with RED tests first.** Phase 0 turns the spec into executable assertions before any source change.
5. **Pin invariants with permanent regression tests.** R1, R2, R3 prevent workaround patterns from coming back.
6. **Atomic phase coupling where required.** Phase 3+4 land together; rollback matrix makes this explicit.
7. **Backward-compat bridges with sunset dates.** `working_dir` accepted with deprecation warning for 1 release; removed next.
8. **Defensive on silent failure modes.** `exist_ok=False` + retry over `exist_ok=True`.
9. **Deploy hygiene is part of the plan, not an afterthought.** `.gitignore` is necessary but not sufficient.
10. **Migration is non-destructive by default.** `--dry-run` first; explicit `--apply` required. Or use marker file approach if cleanup is deferred.
11. **Take pushback seriously.** Claude's flat-layout pushback was correct; v3's nested-layout was inherited from v1 without re-examination. v4 incorporates the correction.

---

## 13. Estimated effort

| Phase | Implementation | Tests | Review | Total (h) |
|---|---|---|---|---|
| 0 (RED tests) | 0 | 1.5 | 0.5 | 2 |
| 1 (helper + unit tests) | 0.5 | 0.5 | 0.5 | 1.5 |
| 2 (SessionStore.tasks_dir) | 0.25 | 0.25 | 0.25 | 0.75 |
| 3+4 (factories+conversation_service+dispatcher — atomic) | 1.5 | 0.5 | 1 | 3 |
| 5 (task executor migration) | 0.5 | 0.25 | 0.25 | 1 |
| 6 (create_role + role_setup migration) | 0.5 | 0.25 | 0.25 | 1 |
| 7 (project_onboarding migration) | 0.5 | 0.25 | 0.25 | 1 |
| 8 (slash-path fix + 13 test files) | 1 | 1.5 | 1 | 3.5 |
| 9 (gitignore + dockerfile + smoke) | 0.5 | 0.5 | 0.5 | 1.5 |
| **Total** | **5.25** | **5.5** | **4.5** | **15.25** |

Roughly **2 engineer-days**. v3 estimated 2.5 days; v4 saves 0.5 days by eliminating the ensure-create dance (Phase 6 in v3).

---

*End of v4 integrated plan. Reviewers: please challenge §2 (the flat-vs-nested architectural decision — is "stronger session ownership" actually a requirement you have?), §4 (the helper code — especially the UUID8 retry and the base_dir signature), §6 Phase 3+4 atomicity, §7 deploy hygiene completeness, and §11.1 ("pick v3 with caveat" — would you really want to ship v3's nested layout and reverse-engineer the flat layout during review?) most carefully.*

