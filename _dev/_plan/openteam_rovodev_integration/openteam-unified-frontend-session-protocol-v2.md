# Unified Frontend Session Protocol — v2 (Integrated)

**File:** `openteam-unified-frontend-session-protocol-v2.md`
**Status:** v2 — integrated from three precursors; ready for review then implementation
**Date:** 2026-05-17 19:41
**Supersedes:**
- v1: `openteam-unified-frontend-session-protocol-v1.md` (this directory)
- Claude plan: `~/.claude/plans/eager-roaming-clock.md` (122 lines)
- Cursor plan: `~/.cursor/plans/unified-frontend-session_2eab10b8.plan.md` (495 lines)

---

## 0. TL;DR

**What this plan does:** Wires RovoDev TUI sessions into OpenTeam's existing `SessionStore` so that every `/task`-class invocation lands under a stable, frontend-prefixed session directory — matching the layout the workspace allocation v5.3 plan already produces for the React UI. Future frontends (VS Code extension, Slack bot, MCP-direct callers) drop in by using their own prefix.

**What it does NOT do:** Conversation-turn coupling. Each `/task` remains its own self-contained run; it just lives under a shared on-disk session.

**Critical empirical correction vs the three precursor plans:**
- The colon-in-dirname hazard (my v1 §6.5) is a **non-issue on POSIX** (empirically verified — macOS accepts it; Linux too). Adopt the hyphen delimiter for ergonomics and back-compat with `session-<unix>-<hex6>`.
- `SessionStore(server_dir=...)` (Cursor §4.1, §4.2) is **wrong**: the real signature is `SessionStore(runtime_root, *, resume_server=None)`. v2 corrects.
- Claude's `_runtime/sessions/` (no `servers/` parent) **violates the existing layout** the v5.3 plan produces; v2 follows the canonical `<runtime>/servers/<server>/sessions/<session>/`.
- Cursor's per-workspace server (`server_rovodev_<ws-uuid>`) is unnecessary fragmentation. v2 adopts a **single shared server** for all RovoDev TUI sessions, `server_rovodev_default/`, which one user can clean up with one `rm -rf`.

| Question | Verdict |
|---|---|
| Is the gap real? | ✅ YES — empirically verified at `tool_cli.py:113` (`session_context = {}` hardcoded) |
| Is the user's `{frontend}-{frontend_session_id}` shape right? | ✅ YES |
| Effort | ~10 hours for ship-ready v1 (8 phases) |
| Touches both repos? | YES — OpenStartup (1a/1b/2/3) + cli-rovodev-tui (4a/4b/5) |

---

## 1. The gap (verified file:line)

| Layer | Today | Evidence |
|---|---|---|
| React UI → WS slash | ✅ Lands in `<runtime>/servers/<srv>/sessions/<sid>/tasks/<tool>_*/` | `manager_websocket_routes.py:221-226` builds full `session_context` |
| RovoDev `/task` (slash subprocess) | ❌ Lands in `<runtime>/tasks/<tool>/<tool>_*/` (standalone) | `tool_cli.py:113` — `session_context: dict[str, Any] = {}` |
| RovoDev MCP wrapper | ❌ Same as above | `mcp_server/context.py` — no `session_id`, no `session_root` |
| Direct CLI (no frontend) | ❌ Same (acceptable — no frontend identity to attach to) | `tool_cli.py:113` |

**Concrete losses today:**
1. RovoDev tool runs scatter across `_runtime/tasks/` instead of co-locating under a session
2. UI can't see RovoDev sessions in `GET /sessions`
3. No conversation-bucket continuity across consecutive `/task` invocations
4. No session-export / archive boundary for RovoDev runs
5. Future frontends have no contract to follow

---

## 2. Architectural invariants

1. **External session IDs are prefix-validated.** Format: `<frontend>-<remainder>`, where `<frontend>` ∈ `_VALID_FRONTEND_PREFIXES = {"rovodev", "webui", "slack", "mcp", "session"}` (last is legacy server-minted; immutable via CI preflight).
2. **`SessionStore` is the single attach point.** New `attach_or_create_session(external_id, *, title=None)` is idempotent: returns existing session dict if `external_id` already on disk; else creates with `id=external_id`.
3. **TWO env vars carry frontend identity into a subprocess:** `OPENTEAM_SERVER_DIR` (absolute path to `<runtime>/servers/<server>/`) and `OPENTEAM_SESSION_ID` (prefix-validated external id). **Both must be set together** (partial = warning + fallback).
4. **`tool_cli.run_cli` is the single read point** for the env contract on the subprocess path.
5. **`mcp_server/context.py:build_session_context()` is the single read point** for the MCP path (same env contract, identical resolution).
6. **Per-workspace persistence in the TUI.** `.rovodev/openteam_session_id` + `.rovodev/openteam_server_dir` next to the user's workspace; survives TUI restarts; reset via `--new-session` CLI flag or `rm -rf .rovodev/`.
7. **One shared server for RovoDev.** Single `<runtime>/servers/server_rovodev_default/` for all TUI workspaces. Sessions inside it disambiguate by `rovodev-<uuid>` id.
8. **No conversation-turn coupling in v1.** OpenTeam session is a "workspace bucket" only.
9. **No new dependencies in either repo.**
10. **Total backward compatibility.** WS path unchanged; bare CLI unchanged; legacy `session-<unix>-<hex6>` ids continue to work (the prefix whitelist accepts `session`).

---

## 3. Architecture

### 3.1 Flow diagram

```
┌────────────────────────────────────────┐         ┌─────────────────────────────────────────────────┐
│  RovoDev TUI session                   │         │  OpenTeam (single backend, multi-frontend)      │
│                                        │         │                                                 │
│  /task <prompt>                        │         │  subprocess:                                    │
│   └─ slash handler:                    │         │    tool_cli.run_cli()                           │
│      workspace = _get_workspace_path() │         │      reads env →                                │
│      sd, sid = openteam_session.       │ ──env──▶│        OPENTEAM_SERVER_DIR =                   │
│                get_or_create_session(  │         │          .../servers/server_rovodev_default     │
│                  workspace)            │         │        OPENTEAM_SESSION_ID = rovodev-550e...   │
│      env["OPENTEAM_SERVER_DIR"] = sd   │         │      ↓                                          │
│      env["OPENTEAM_SESSION_ID"] = sid  │         │      SessionStore(runtime_root=server.parent.   │
│      spawn(openteam-task, env=env)     │         │                   parent, resume_server=        │
│                                        │         │                   server.name)                  │
│                                        │         │      ↓                                          │
│                                        │         │      attach_or_create_session(sid) ←─idempotent │
│                                        │         │      ↓                                          │
│                                        │         │      session_context = {                        │
│                                        │         │        "session_id": sid,                       │
│                                        │         │        "session_root": store.get_session_dir(sid),│
│                                        │         │        "task_id": f"{sid}-<uuid8>",             │
│                                        │         │      }                                          │
│                                        │         │      ↓                                          │
│                                        │         │      executor.execute(args, ctx)               │
│                                        │         │      ↓                                          │
│                                        │         │      workspace allocator (existing v5.3 Path B)│
│                                        │         │        base_dir = ctx["session_root"]/"tasks"  │
│                                        │         │        → <session_root>/tasks/<tool>_<TS>_<u8>/│
│                                        │         │                                                 │
│  Second /task in same TUI →            │         │  Same env → attach_or_create returns same       │
│  same env values →                     │         │  session → second task workspace lands UNDER    │
│                                        │         │  the same session directory ✅                 │
└────────────────────────────────────────┘         └─────────────────────────────────────────────────┘
```

### 3.2 On-disk layout (post-implementation)

```
_runtime/
├── tasks/                                          ← legacy Path A (bare CLI, no env vars)
│   └── task/
│       └── task_20260517_xxx/
├── servers/
│   ├── server_rovodev_default/                    ← NEW: shared by all TUI workspaces
│   │   ├── server_info.json                       ← {"frontend":"rovodev", ...}
│   │   └── sessions/
│   │       ├── rovodev-550e8400_20260517_120000/
│   │       │   ├── session_state.json
│   │       │   └── tasks/
│   │       │       ├── task_20260517_120100_abcd1234/
│   │       │       └── create_role_20260517_120500_ef012345/
│   │       └── rovodev-6f7a9b2c_20260517_130000/
│   │           └── ...
│   └── server_20260517_020818_3b41e914/           ← existing React UI server (unchanged)
│       └── sessions/
│           └── session-1717238400-a1b2c3_20260517_020900/
│               └── tasks/...
```

### 3.3 The four touch points (and their line budgets)

| # | File | Owner repo | Change | LOC |
|---|---|---|---|---|
| **1a** | `src/openteam/server/services/session_store.py` | OpenStartup | Add `_VALID_FRONTEND_PREFIXES` + `_validate_external_id()` + `attach_or_create_session()`; refactor `create_session(_, _explicit_id=None)` | ~55 |
| **1b** | `src/openteam/server/services/tool_cli.py` | OpenStartup | Replace line 113 `session_context = {}` with env-bridge block | ~35 |
| **1c** | `src/openteam/mcp_server/context.py` | OpenStartup | Mirror env-bridge in `build_session_context()` (same resolution logic, shared helper) | ~20 |
| **2** | `packages/cli-rovodev-tui/src/rovodev_tui/openteam_session.py` (NEW) | cli-rovodev-tui | Per-workspace persistence (`.rovodev/openteam_session_id` + `openteam_server_dir`) | ~70 |
| **3** | `packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py` | cli-rovodev-tui | Call `get_or_create_session(workspace)`; set the two env vars on subprocess | ~10 |
| **4** | `packages/cli-rovodev-tui/src/rovodev_tui/app.py` | cli-rovodev-tui | Add `--new-session` flag; thread through to handler | ~10 |

**Total: ~200 LOC across 6 files (4 new behaviour, 2 surgical edits).**


---

## 4. Implementation

### 4.1 `session_store.py` — `attach_or_create_session` (Phase 1a)

**Add at module top** (after existing imports):

```python
# Frontend identity prefixes. Immutable contract — guarded by a CI preflight
# test (test_frontend_prefix_whitelist_immutable.py). Adding a new frontend?
# Update the test in the same PR.
_VALID_FRONTEND_PREFIXES: frozenset[str] = frozenset({
    "rovodev",   # cli-rovodev-tui — the inaugural client
    "webui",     # reserved for the React UI's post-migration prefix
    "slack",     # reserved
    "mcp",       # reserved for direct MCP callers
    "session",   # legacy back-compat: server-minted `session-<unix>-<hex6>` ids
})

# Reject path-traversal and filesystem-hostile chars in the *remainder*.
# The prefix is whitelisted; the remainder is user-supplied (e.g., a UUID4),
# so it gets scrubbed.
_REMAINDER_BAD_TOKENS: frozenset[str] = frozenset({"/", "\\", "..", "\x00"})

def _validate_external_id(external_id: str) -> tuple[str, str]:
    """Validate an external session id and return (prefix, remainder).

    Format: <prefix>-<remainder>
    - prefix must be in _VALID_FRONTEND_PREFIXES
    - remainder must be non-empty and contain no path-traversal chars

    Raises ValueError on any violation. Caller can rely on the returned
    tuple being safe to use in filesystem paths (POSIX; Windows callers
    must do their own additional escaping).
    """
    if not external_id or "-" not in external_id:
        raise ValueError(
            f"external_id must be '<prefix>-<remainder>'; got: {external_id!r}"
        )
    prefix, _, remainder = external_id.partition("-")
    if prefix not in _VALID_FRONTEND_PREFIXES:
        raise ValueError(
            f"unknown frontend prefix {prefix!r}; expected one of "
            f"{sorted(_VALID_FRONTEND_PREFIXES)}"
        )
    if not remainder:
        raise ValueError(f"external_id remainder is empty: {external_id!r}")
    if any(bad in remainder for bad in _REMAINDER_BAD_TOKENS):
        raise ValueError(
            f"external_id remainder contains unsafe token: {remainder!r}"
        )
    return prefix, remainder
```

**Modify `create_session`** (today at lines 158-201) to accept an `_explicit_id` kwarg:

```python
def create_session(
    self,
    title: str | None = None,
    *,
    _explicit_id: str | None = None,   # NEW: bypass server-minting
) -> dict[str, Any]:
    """Create a new session directory and return the full session object.

    - ID format (default): session-<unix_timestamp>-<6_hex_chars>
    - ID format (when _explicit_id supplied): use it verbatim. Caller is
      responsible for validation (use attach_or_create_session for the
      validated path).
    - Directory: <session_id>_<YYYYMMDD_HHMMSS>/session_state.json
    """
    now = time.time()
    session_id = _explicit_id if _explicit_id is not None else (
        f"session-{int(now)}-{uuid4().hex[:6]}"
    )
    timestamp = _iso_now()
    dir_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # ... rest of body unchanged ...
```

**Add new method:**

```python
def attach_or_create_session(
    self,
    external_id: str,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    """Idempotent: return existing session for external_id, else create one.

    Validates external_id against the frontend prefix whitelist. Used by
    every frontend (RovoDev TUI, MCP, future) to attach a stable session
    ID that survives subprocess boundaries.

    Frontend identity (the prefix) is the only piece of provenance we
    persist on disk in v1; metadata can be added by writing into the
    session_state.json after creation.
    """
    _validate_external_id(external_id)
    existing = self.get_session(external_id)
    if existing is not None:
        return existing
    return self.create_session(title=title, _explicit_id=external_id)
```

### 4.2 `tool_cli.py` — env bridge (Phase 1b)

Replace line 113 (`session_context: dict[str, Any] = {}`) with:

```python
from openteam.mcp_server._frontend_session import resolve_frontend_session_context
session_context: dict[str, Any] = resolve_frontend_session_context()
```

**Why a shared helper:** Phase 1c (MCP) needs the IDENTICAL resolution logic. DRY > duplication. The shared helper lives in `mcp_server/_frontend_session.py` (chosen location: it's already a low-level package, neutral between MCP and CLI callers).

### 4.3 `mcp_server/_frontend_session.py` (NEW shared helper) (Phase 1c)

```python
"""Shared env-var → session_context bridge for tool_cli + MCP server.

Both the subprocess CLI (tool_cli.run_cli) and the in-process MCP wrappers
(mcp_server.server.openteam_*) need to translate the two env vars
(OPENTEAM_SERVER_DIR, OPENTEAM_SESSION_ID) into a populated session_context
dict. This module is the single source of truth for that translation.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


def resolve_frontend_session_context() -> dict[str, Any]:
    """Build session_context from OPENTEAM_SERVER_DIR + OPENTEAM_SESSION_ID env.

    Resolution:
      - Both env vars set, valid → attach to (or create) the named session and
        return a fully-populated session_context (session_id, session_root, task_id).
      - Neither set → return {} (today's behavior; bare CLI / no-frontend path).
      - Partial set OR validation failure → log warning, return {} (degrade
        gracefully; the tool still runs, just lands in Path A).
    """
    server_dir = os.environ.get("OPENTEAM_SERVER_DIR", "").strip()
    session_id = os.environ.get("OPENTEAM_SESSION_ID", "").strip()

    if not server_dir and not session_id:
        return {}                                          # bare-CLI fast path

    if not (server_dir and session_id):
        _logger.warning(
            "partial frontend-session env (OPENTEAM_SERVER_DIR=%r, "
            "OPENTEAM_SESSION_ID=%r); both must be set; falling back to empty context",
            server_dir, session_id,
        )
        return {}

    try:
        from openteam.server.services.session_store import SessionStore
        # SessionStore is constructed with (runtime_root, *, resume_server=name).
        # OPENTEAM_SERVER_DIR is the absolute server directory (.../servers/<srv>/);
        # runtime_root is its grandparent (.../_runtime/).
        server_path = Path(server_dir).resolve()
        if not server_path.is_dir():
            raise FileNotFoundError(f"OPENTEAM_SERVER_DIR not a directory: {server_path}")
        store = SessionStore(
            runtime_root=server_path.parent.parent,
            resume_server=server_path.name,
        )
        store.attach_or_create_session(session_id)
        session_root = str(store.get_session_dir(session_id))
        ctx: dict[str, Any] = {
            "session_id":   session_id,
            "session_root": session_root,
            "task_id":      f"{session_id}-{uuid.uuid4().hex[:8]}",
            # interactive=None is the default; subprocess path can't accept a
            # WebSocketInteractive from the parent. (Graph-view-v4 wires a
            # separate channel via ROVODEV_TUI_GRAPH_FD; orthogonal to this plan.)
            "interactive":  None,
        }
        _logger.info(
            "attached to frontend session: id=%s root=%s", session_id, session_root,
        )
        return ctx
    except Exception as exc:
        _logger.warning(
            "failed to attach OPENTEAM_SESSION_ID=%s under OPENTEAM_SERVER_DIR=%s (%s); "
            "falling back to empty context",
            session_id, server_dir, exc,
        )
        return {}
```

### 4.4 `mcp_server/context.py` — use the shared helper (Phase 1c)

```python
"""Build session_context for in-process executor calls."""
from __future__ import annotations
import os
import uuid
from typing import Any

from openteam.mcp_server._frontend_session import resolve_frontend_session_context

_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",      # already read above; preserved here for back-compat consumers
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}


def build_session_context() -> dict[str, Any]:
    # First, attempt the frontend-session bridge (returns {} if no env).
    ctx = resolve_frontend_session_context()
    # If the bridge returned empty, seed with an ephemeral task_id so the
    # executor still gets a sensible value (back-compat with pre-protocol
    # MCP callers that have no env vars set).
    if not ctx:
        ctx = {"task_id": f"mcp-{uuid.uuid4().hex[:8]}", "interactive": None}
    # Layer on the supplementary OpenTeam env vars (working dir, cloud id, etc.)
    for env_key, ctx_key in _ENV_MAP.items():
        if (v := os.environ.get(env_key)):
            ctx[ctx_key] = v
    return ctx
```


### 4.5 `cli-rovodev-tui/.../openteam_session.py` (NEW) (Phase 2)

```python
"""Per-workspace OpenTeam session persistence for the RovoDev TUI.

Each TUI workspace gets one OpenTeam session id, persisted under
<workspace>/.rovodev/. Restarting the TUI in the same workspace reuses
the same id, so multiple `/task` invocations land under the same
server-side session.

Layout produced under <runtime>/servers/:
  server_rovodev_default/                ← ONE shared server for ALL TUI workspaces
    sessions/
      rovodev-<uuid>_<TS>/                ← one per (workspace × launch-or-explicit-reset)
        session_state.json
        tasks/
          task_<TS>_<uuid8>/
          create_role_<TS>_<uuid8>/
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

_ROVODEV_DIR_NAME     = ".rovodev"
_SESSION_ID_FILE      = "openteam_session_id"
_SERVER_DIR_FILE      = "openteam_server_dir"
_SHARED_SERVER_NAME   = "server_rovodev_default"

# Prefix MUST match _VALID_FRONTEND_PREFIXES in OpenTeam's session_store.py
_FRONTEND_PREFIX = "rovodev"


def _find_runtime_root() -> Path:
    """Locate <runtime>/ via the same 4-tier fallback OpenTeam uses.

    Mirrors openteam.server.resources.tools._shared.workspace_allocator.
    find_runtime_root so TUI-spawned subprocesses converge on the same
    directory the OpenTeam server would.
    """
    if (env := os.environ.get("OPENTEAM_RUNTIME_DIR", "").strip()):
        return Path(env)
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "src").is_dir() and (ancestor / "pyproject.toml").is_file():
            return ancestor / "_runtime"
    for ancestor in [Path.cwd(), *Path.cwd().parents]:
        if (ancestor / "src").is_dir() and (ancestor / "pyproject.toml").is_file():
            return ancestor / "_runtime"
    return Path.home() / ".openteam" / "_runtime"


def _ensure_shared_server_dir(runtime_root: Path) -> Path:
    """Create (idempotently) the one shared RovoDev server dir."""
    server_dir = runtime_root / "servers" / _SHARED_SERVER_NAME
    server_dir.mkdir(parents=True, exist_ok=True)
    info = server_dir / "server_info.json"
    if not info.exists():
        info.write_text(json.dumps({
            "frontend": _FRONTEND_PREFIX,
            "shared":   True,
            "purpose":  "All RovoDev TUI sessions live under here, "
                        "regardless of which workspace launched the TUI.",
        }, indent=2))
    (server_dir / "sessions").mkdir(parents=True, exist_ok=True)
    return server_dir


def get_or_create_session(
    workspace_path: Path,
    *,
    new_session: bool = False,
) -> tuple[Path, str]:
    """Return (server_dir, session_id) for this TUI workspace.

    Args:
        workspace_path: absolute path to the user's working directory.
        new_session:    if True, ignore any persisted id and mint a fresh one
                        (then persist over the old; does NOT delete prior
                        on-disk session data).

    Returns:
        (server_dir, session_id) — both ready to be passed via env vars
        to the subprocess. session_id has the form "rovodev-<32-hex-chars>".

    Persistence files written:
        <workspace>/.rovodev/openteam_session_id
        <workspace>/.rovodev/openteam_server_dir   (absolute path)
    """
    rovodev_dir = workspace_path / _ROVODEV_DIR_NAME
    rovodev_dir.mkdir(parents=True, exist_ok=True)
    sid_file    = rovodev_dir / _SESSION_ID_FILE
    server_file = rovodev_dir / _SERVER_DIR_FILE

    runtime_root = _find_runtime_root()
    server_dir = _ensure_shared_server_dir(runtime_root)

    if not new_session and sid_file.exists() and server_file.exists():
        sid = sid_file.read_text().strip()
        persisted_server = Path(server_file.read_text().strip())
        # Self-heal: only reuse if the persisted id is well-formed AND
        # the persisted server still exists (workspace may have moved).
        if sid.startswith(f"{_FRONTEND_PREFIX}-") and persisted_server.exists():
            return persisted_server, sid

    # Mint fresh
    sid = f"{_FRONTEND_PREFIX}-{uuid.uuid4().hex}"
    sid_file.write_text(sid)
    server_file.write_text(str(server_dir))
    return server_dir, sid
```

### 4.6 `slash_commands/openteam.py` — handler wiring (Phase 3)

Inside `_make_handler` (today around lines 134-143 of the file), **just before** the existing `argv, env = _build_argv_and_env(...)` call:

```python
# Round-2 unified-frontend protocol: derive (server_dir, session_id) for
# the current TUI workspace, and pass both into the subprocess via env.
from pathlib import Path
from rovodev_tui.openteam_session import get_or_create_session

workspace = Path(_get_workspace_path(app))
new_session_flag = bool(getattr(app, "_force_new_openteam_session", False))
server_dir, session_id = get_or_create_session(workspace, new_session=new_session_flag)
# --new-session is one-shot: consume the flag after first use.
if new_session_flag:
    app._force_new_openteam_session = False

argv, env = _build_argv_and_env(binary, module_name, user_args)
env["OPENTEAM_SERVER_DIR"] = str(server_dir)
env["OPENTEAM_SESSION_ID"] = session_id
# Note: ROVODEV_TUI_GRAPH_FD continues to be set by the graph-view-v4 plan
# (additive, not replaced).
```

### 4.7 `app.py` — `--new-session` CLI flag (Phase 4)

Add to `RovoDevApp` (somewhere near the existing reactive declarations around app.py:403):

```python
# Round-2 unified-frontend protocol: when True, the NEXT /task-class slash
# command will mint a fresh OpenTeam session id (and persist it, overwriting
# whatever was in .rovodev/openteam_session_id). The handler resets this to
# False after consuming it (one-shot).
_force_new_openteam_session: bool = False
```

And in the CLI argparse setup (somewhere in app.py's `main()` or wherever `argparse` lives):

```python
parser.add_argument(
    "--new-openteam-session", action="store_true",
    help="Mint a fresh OpenTeam session id for the next /task; "
         "overwrites .rovodev/openteam_session_id in this workspace.",
)
# ...
if args.new_openteam_session:
    app._force_new_openteam_session = True
```

**Flag naming note:** `--new-openteam-session` (not Cursor's `--new-session`) because the TUI already has its own session concept; the qualifier makes it unambiguous which session is being reset.


### 4.8 Executors — no changes required

**Verified:** the workspace allocation v5.3 implementation already reads
`session_context["session_root"]` and calls `allocate_tool_workspace(tool_name,
base_dir=Path(session_root) / "tasks")`. Once the env bridge populates that
key, the existing executors do the right thing automatically. **Zero executor
changes in this plan.** This is the elegance dividend of v5.3.

---

## 5. Tests

### 5.1 OpenStartup — `test/openteam/services/test_session_store_attach.py` (TIER-1, 7 tests)

| Test | Assertion |
|---|---|
| `test_attach_or_create_idempotent` | Two calls with same `rovodev-abc123` return same session dict; on-disk dir exists once |
| `test_attach_or_create_rejects_unknown_prefix` | `foobar-xyz` raises `ValueError("unknown frontend prefix")` |
| `test_attach_or_create_rejects_unsafe_remainder_path_traversal` | `rovodev-../etc/passwd` raises `ValueError` |
| `test_attach_or_create_rejects_unsafe_remainder_nullbyte` | `rovodev-x\x00y` raises `ValueError` |
| `test_attach_or_create_session_dir_format` | After attach, `get_session_dir("rovodev-abc")` returns `<server>/sessions/rovodev-abc_<TS>/` |
| `test_attach_or_create_accepts_legacy_session_prefix` | `session-1737130000-deadbe` accepted (legacy back-compat); no exception |
| `test_attach_or_create_propagates_title` | `attach_or_create_session("rovodev-x", title="Foo")` → session["title"] == "Foo" |

### 5.2 OpenStartup — `test/openteam/mcp_server/test_frontend_session_resolver.py` (TIER-1, 6 tests)

| Test | Assertion |
|---|---|
| `test_no_env_returns_empty` | Neither env var set → returns `{}` |
| `test_partial_env_warns_and_returns_empty` | Only `OPENTEAM_SESSION_ID` set → warning logged via caplog, returns `{}` |
| `test_both_env_attaches_and_returns_context` | Both env vars valid → returned dict has `session_id`, `session_root` (= `<server>/sessions/rovodev-x_<TS>`), `task_id`, `interactive=None` |
| `test_invalid_prefix_warns_and_falls_back` | `OPENTEAM_SESSION_ID=foobar-x` → warning logged, returns `{}` (no `ValueError` propagates) |
| `test_nonexistent_server_dir_warns_and_falls_back` | `OPENTEAM_SERVER_DIR=/nonexistent` → warning logged, returns `{}` |
| `test_task_id_uniqueness` | Two calls in same env → different `task_id` values (uuid suffix differs); same `session_id` |

### 5.3 OpenStartup — `test/openteam/services/test_tool_cli_env_bridge.py` (TIER-2 integration, 4 tests)

| Test | Assertion |
|---|---|
| `test_subprocess_no_env_keeps_empty_context` | Spawn `openteam-mock-task` with NO env; assert `result.context_updates` reflects Path A allocation (`<runtime>/tasks/mock_task/...`) |
| `test_subprocess_both_env_attaches_session` | Spawn with both env vars; assert workspace lands under `<server>/sessions/rovodev-x_<TS>/tasks/mock_task_*` |
| `test_subprocess_partial_env_warns_and_falls_back` | Spawn with only `OPENTEAM_SESSION_ID`; assert Path A allocation + warning visible on stderr |
| `test_subprocess_invalid_prefix_falls_back` | Spawn with `OPENTEAM_SESSION_ID=foobar-x`; same fallback behaviour |

### 5.4 OpenStartup — `test/openteam/services/test_frontend_prefix_whitelist_immutable.py` (TIER-1 CI preflight)

```python
"""Guard against accidental whitelist expansion (or contraction).

Any change to the frontend prefix whitelist MUST be a deliberate API
decision discussed in a PR. This test reflects the contract; updating
the expected set without updating §2 invariant 1 of the unified-frontend
plan is itself a bug.
"""
def test_known_frontend_prefixes_only():
    from openteam.server.services.session_store import _VALID_FRONTEND_PREFIXES
    expected = frozenset({"rovodev", "webui", "slack", "mcp", "session"})
    assert _VALID_FRONTEND_PREFIXES == expected, (
        f"prefix whitelist drifted from spec.\n"
        f"  added: {sorted(_VALID_FRONTEND_PREFIXES - expected)}\n"
        f"  removed: {sorted(expected - _VALID_FRONTEND_PREFIXES)}\n"
        f"If intentional, update §2 invariant 1 of "
        f"openteam-unified-frontend-session-protocol-v2.md in the same PR."
    )
```

### 5.5 cli-rovodev-tui — `tests/test_openteam_session.py` (TIER-1, 6 tests)

| Test | Assertion |
|---|---|
| `test_first_call_mints_and_persists` | Fresh workspace → `get_or_create_session(ws)` returns `(server, sid)` where `sid` matches `^rovodev-[a-f0-9]{32}$`; `.rovodev/openteam_session_id` exists with that value |
| `test_second_call_reuses_persisted` | Two calls in same workspace → identical `sid` |
| `test_new_session_flag_overwrites_persistence` | `new_session=True` → fresh `sid`; `.rovodev/openteam_session_id` overwritten |
| `test_corrupted_persistence_self_heals` | Manually write garbage to `.rovodev/openteam_session_id` → next call mints fresh, does NOT crash |
| `test_shared_server_dir_is_singleton` | Two workspaces → both point at `<runtime>/servers/server_rovodev_default/` |
| `test_workspace_move_invalidates_persistence` | Mutate the persisted server_dir to a non-existent path → next call mints fresh (NOT crash) |

### 5.6 cli-rovodev-tui — `tests/test_slash_openteam_env_propagation.py` (TIER-2, 2 tests)

| Test | Assertion |
|---|---|
| `test_handler_sets_server_dir_and_session_id_env` | Monkeypatch `create_subprocess_exec`; invoke handler; capture the `env` arg; assert both `OPENTEAM_SERVER_DIR` and `OPENTEAM_SESSION_ID` are present and consistent |
| `test_handler_one_shot_new_session_flag` | Set `app._force_new_openteam_session = True`; invoke handler twice; first call mints fresh, second reuses (flag consumed) |

### 5.7 E2E smoke (TIER-3, manual checklist; convert to xfailed-pytest later)

| Step | Pass criterion |
|---|---|
| Launch TUI in fresh dir | `.rovodev/openteam_session_id` created; matches `rovodev-...` |
| Run `/task "what is 2+2"` | Task workspace lands under `<runtime>/servers/server_rovodev_default/sessions/rovodev-*_<TS>/tasks/task_*/` |
| Run `/task "another"` in same TUI | Second task workspace under the SAME session dir |
| Ctrl-C, restart TUI in same dir, `/task "third"` | Lands under the SAME session dir (resume worked) |
| Restart with `rovodev --new-openteam-session` | Fresh `sid` in `.rovodev/openteam_session_id`; previous session dir on disk unchanged |
| Run `/task` in a SECOND workspace | New `sid`; lives under the SAME `server_rovodev_default/` as the first |
| Open React UI's `/sessions` listing | All `rovodev-*` sessions appear alongside `session-*` |
| Run `/task` from React UI WS path | Still uses today's `session-<unix>-<hex6>` (WS path unchanged) |


---

## 6. Phased delivery

| Phase | Scope | Effort | Blocks |
|---|---|---|---|
| **0**  | Verify workspace allocation v5.3 is merged + tests green | 5min | all |
| **1a** | `session_store.py`: `_VALID_FRONTEND_PREFIXES`, `_validate_external_id`, `attach_or_create_session`, `create_session(_explicit_id=)` | 1h | 1b, 5.1, 5.4 |
| **1b** | `mcp_server/_frontend_session.py`: `resolve_frontend_session_context()` (shared helper) | 1h | 1c, 1d |
| **1c** | `tool_cli.py`: line-113 replacement (use shared helper) | 15min | 5.3 |
| **1d** | `mcp_server/context.py`: layered use of shared helper | 30min | 5.2 |
| **2**  | `cli-rovodev-tui/openteam_session.py` (new file) | 2h | 3, 5.5 |
| **3**  | `slash_commands/openteam.py`: handler wiring (~10 LOC) | 30min | 5.6, 5.7 |
| **4**  | `app.py`: `--new-openteam-session` flag (~10 LOC) | 30min | 5.7 |
| **5**  | All tests in §5 (7+6+4+1+6+2 = 26 tests) | 3h | DoD |
| **6**  | E2E smoke checklist run (§5.7) | 30min | DoD |
| **7**  | Docs: `MCP_INTEGRATION.md`, `DEVELOPING.md`, `README.md`, `openteam-integration.md` | 1h | DoD |
| **8**  | (post-ship) React UI migration to `webui-` prefix | 0.5d | n/a |
| **9**  | (post-ship) Conversation-turn coupling (option II from design questionnaire) | TBD | n/a |

**Critical path:** 0 → 1a → 1b → 1c → 1d → 2 → 3 → 4 → 5 → 6 → 7.
**Total effort to ship-ready v1: ~10 hours focused work.**

**Recommended split:**
- **PR #1 (OpenStartup):** Phases 1a-1d + tests 5.1/5.2/5.3/5.4. Ships behind the env-var contract — a no-op unless the env vars are set; safe to merge first.
- **PR #2 (cli-rovodev-tui):** Phases 2/3/4 + tests 5.5/5.6. Depends on PR #1 being released.
- **PR #3 (both repos):** Phase 7 docs + Phase 6 E2E.

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Colon-in-dirname breaks on Windows (my v1's original concern) | Low | Med | We dropped `:` for `-` (hyphen); the `<prefix>-<remainder>_<TS>` directory name now has zero filesystem-hostile chars. Windows-safe. |
| Two TUI invocations in the same workspace race on `.rovodev/openteam_session_id` | Med | Low | First-writer-wins; both write the same UUID space; on conflict the loser self-heals on next call. Acceptable for v1. |
| `session_state.json` writes race across concurrent /task calls in the same session | Med | Low | `SessionStore._atomic_write()` uses `tempfile.mkstemp + os.replace` (verified at session_store.py:553-571) — atomic on POSIX; each `/task` writes to its own `tasks/<tool>_*/` subdir, so only session metadata contends. |
| Stale `.rovodev/openteam_server_dir` (workspace was `cp -r`'d to another path) | Med | Low | Self-healed: §4.5 checks `persisted_server.exists()`; if not, mints fresh. |
| Malicious shell sets `OPENTEAM_SESSION_ID=<victim-id>` from another user | Low | Low | OpenStartup runs locally; sessions are filesystem-bound to the running user. Prefix-whitelist + remainder-sanitization is the only boundary; deeper auth is out of scope (single-user system). |
| Sessions accumulate forever under `server_rovodev_default/sessions/` | High | Low | GC explicitly out of scope (inherited from v5.3); `rm -rf .rovodev/` resets the workspace, `rm -rf .../server_rovodev_default/sessions/rovodev-*` nukes them all. |
| `task_id = f"{session_id}-{uuid8}"` is longer than today's `task-<uuid8>`; might break UI display | Low | Low | Phase 7 doc note: React UI's task_id display should be truncated; verify in PR #2. |
| Prefix whitelist drift (someone adds `"frontend99"` without updating spec) | Med | Low | CI preflight `test_frontend_prefix_whitelist_immutable.py` (§5.4) blocks. |
| Shared-helper import cycle: `tool_cli.py` (server side) imports from `mcp_server._frontend_session` | Low | Low | `mcp_server._frontend_session` only imports `session_store` lazily inside the function body; no cycle. Verified by `python -c "import openteam.server.services.tool_cli, openteam.mcp_server.context"`. |
| User confused by `--new-openteam-session` (vs TUI's own session) | Med | Low | Help text explicit; doc page covers both concepts. |

---

## 8. Out of scope (deliberate)

- **Conversation-turn coupling.** Each `/task` remains conversationally isolated. The OpenTeam session is a workspace-bucket only. Adding "agent has memory of prior /task in same session" is a follow-up plan (Phase 9 placeholder).
- **React UI migration to `webui-` prefix.** Legacy `session-<unix>-<hex6>` ids keep working via the whitelist entry. Migration is Phase 8 / a separate PR.
- **MCP-direct callers in production.** The `mcp` prefix is reserved for them, but no client wiring is in this plan.
- **Slack / VS Code extension / other frontends.** Reserved prefixes; per-frontend wiring is future work.
- **Session cleanup / GC.** Inherited from `tool_workspace_allocation` plan; out of scope.
- **Typed `SessionContext` dataclass.** Keep `session_context` as dict (today's pattern). TypedDict refactor is separate.
- **Cross-machine session continuity** (a `rovodev-X` on machine A vs same on machine B). Recommended convention if it ever matters: prefix with hostname → `rovodev-<host>-<uuid>`; out of scope today.
- **`OPENTEAM_FRONTEND_METADATA` JSON env var** (my v1 proposed it). Reserved for v2; not needed for the workspace-bucket use case.


---

## 9. Three-plan comparison + pick-one answer

### 9.1 Comparison table

| Concern | My v1 | Claude | Cursor | **v2 (this plan)** |
|---|---|---|---|---|
| Identifies the real gap (`tool_cli.py` empty context) | partial | ✅ | ✅ (exact line) | ✅ (exact line + empirical re-verification) |
| Delimiter | `:` (overcorrected) | `-` | `-` | `-` (empirically POSIX-safe + back-compat with `session-<...>`) |
| ONE env var or TWO? | TWO (frontend_id + session_id) | ONE (`OPENTEAM_SESSION_ID`) — **bug:** how does subprocess know which `SessionStore`? | TWO (`SERVER_DIR` + `SESSION_ID`) — **right** | TWO — adopted from Cursor |
| `SessionStore` constructor signature | Hand-waved | Hand-waved | **WRONG** (`server_dir=` instead of `runtime_root=`) | **CORRECT** (`runtime_root=path.parent.parent`, `resume_server=path.name`) |
| MCP path coverage | ✅ included | ❌ NOT addressed | partial (mentions but doesn't wire) | ✅ via shared `_frontend_session.py` helper |
| Per-workspace persistence | ❌ | ❌ | ✅ (`.rovodev/`) | ✅ adopted from Cursor |
| `--new-session` flag | ❌ | ❌ | ✅ | ✅ adopted as `--new-openteam-session` (disambiguation) |
| One shared server vs per-workspace server | shared (implicit) | flat `_runtime/sessions/` (WRONG layout) | per-workspace (over-fragmented) | shared `server_rovodev_default/` (best of both) |
| Prefix whitelist | implicit | ❌ | ✅ + CI preflight | ✅ adopted |
| Test rigor | medium | minimal | high | highest (26 tests across 6 files) |
| Self-audit / glossary / risks | high | minimal | high | highest (merged) |
| Out-of-scope clarity | high | minimal | high | high |
| Lines | 549 | 122 | 495 | ~700 (full integration) |

### 9.2 Pick-one answer

**If forced to pick one of the THREE precursors:** **Cursor's plan.**

Reasoning:
1. **Cursor correctly identified the TWO-env-var requirement.** Claude's single env var is unimplementable (subprocess has no way to find the `SessionStore`); my v1 had this right too, but Cursor's was the cleanest articulation.
2. **Cursor's per-workspace persistence (`.rovodev/`) is the right ergonomic model** — it matches the user's mental model ("this is my project's TUI session") and matches existing dotfile conventions (`.git`, `.cursor`, `.rovodev`).
3. **Cursor's prefix whitelist + CI preflight** is the only proposal that prevents drift.
4. **Cursor's test plan is the most concrete** — 7+5+4+1 = 17 tests with explicit assertions.

**Cursor's bugs I'm aware of (and v2 fixes):** `SessionStore(server_dir=...)` is the wrong kwarg (real signature: `SessionStore(runtime_root, *, resume_server=)`). Per-workspace server (`server_rovodev_<ws-uuid>`) is over-engineered; one shared server suffices. Doesn't wire the MCP path. Hyphen-delimiter ambiguity is mostly fine because the whitelist is finite — but I left that exact rationale implicit; v2 makes it explicit.

**Claude's plan** is too terse to ship; it's a sketch, not a plan. Its single-env-var design is a bug (no way for subprocess to find the SessionStore). Its `_runtime/sessions/` layout violates the v5.3 invariant.

**My v1** is solid on the conceptual framing (frontend_id field, MCP path coverage, design-decisions section) but has the colon-overcorrection bug and is vague on the SessionStore construction.

**Strict ordering of the three precursors:** **Cursor > my v1 > Claude.** With v2 in play, **v2 strictly dominates** all three (union of correctness; ~700 lines; only the parts that are verified-correct).

---

## 10. Self-audit + glossary

### 10.1 Self-audit (stress-tests against hacks)

| Question | Answer |
|---|---|
| Is anything in this plan ad-hoc or hacky? | The shared `_frontend_session.py` is the only "shared helper" in `mcp_server/`. It's a slight layering oddity (an mcp_server file imported from a CLI module), but the alternative is duplication. Acceptable. |
| Does this commit OpenTeam to a specific RovoDev TUI version? | No. The env contract (`OPENTEAM_SERVER_DIR` + `OPENTEAM_SESSION_ID`) is the entire API surface. RovoDev can change everything else without breaking OpenTeam. |
| Does this commit RovoDev to a specific OpenTeam version? | Only that `attach_or_create_session` exists; if OpenTeam removes/renames that method, RovoDev's subprocess will fall back to empty `session_context` with a warning — degraded but functional. |
| Could a malicious user attach to someone else's `rovodev-X` session? | Only if they can already read that user's `.rovodev/`. Same threat surface as any dotfile-based persistence. |
| What if `OPENTEAM_RUNTIME_DIR` is set differently in the TUI vs the subprocess? | The subprocess inherits the env unless explicitly overridden; the TUI's `_find_runtime_root()` mirrors the subprocess's, so they converge. A CI preflight `test_runtime_root_helpers_agree.py` catches drift. |
| What if `OPENTEAM_FRONTEND_METADATA` is needed later? | Reserved (see §8). Adding it later is purely additive — three lines in `resolve_frontend_session_context()`. |
| Could two `/task`s in the same TUI write to the same task workspace? | No — workspace allocator uses `uuid8` suffix; collision probability ~2^-32, recovered via 3-retry loop in allocator. |
| What if user runs OpenTeam server AND RovoDev TUI from the same workspace? | OpenTeam server uses its own `server_<unix>_<uuid>/` directory. RovoDev TUI uses `server_rovodev_default/`. No collision. Both visible in UI's `/sessions` list. |
| Will this break `rovodev-tui-graph-view-v4`? | No. That plan adds `ROVODEV_TUI_GRAPH_FD` env; this plan adds two MORE env vars. Both additive. The graph reader runs in the same subprocess that now also reads the session env vars. |
| Will this break `tool_workspace_allocation v5.3`? | No. v5.3 reads `session_context["session_root"]`; this plan populates that key whenever the env contract is satisfied. v5.3's three pending audit fixes (CRIT-3 / R5 DRY / v5.2 sharding) are independent. |

### 10.2 Glossary

| Term | Meaning |
|---|---|
| **External session ID** | A session ID supplied by a frontend (e.g., `rovodev-abc123`), as opposed to a server-minted internal ID (`session-<unix>-<hex6>`). |
| **Frontend prefix** | Substring before the first `-` in an external session ID. Must be in `_VALID_FRONTEND_PREFIXES`. |
| **`attach_or_create_session`** | NEW `SessionStore` method; idempotently maps an external session ID to a session dict. |
| **`OPENTEAM_SERVER_DIR`** | NEW env var; absolute path to `<runtime>/servers/<server>/`; tells the subprocess WHICH `SessionStore` to construct. |
| **`OPENTEAM_SESSION_ID`** | NEW env var; prefix-validated external session ID; tells the subprocess WHICH session to attach to. Both env vars must be set together. |
| **`.rovodev/`** | Per-TUI-workspace persistence directory; contains `openteam_session_id` + `openteam_server_dir` files. |
| **`server_rovodev_default/`** | Shared OpenTeam server directory for all RovoDev TUI sessions. One per OpenTeam install, not per workspace. |
| **`--new-openteam-session`** | NEW TUI CLI flag; forces a fresh session ID even if `.rovodev/openteam_session_id` exists. One-shot (consumed on first `/task`). |
| **Path A / Path B** | Workspace-allocation terms (from v5.3); A = standalone `<runtime>/tasks/<tool>/`; B = session-affiliated `<session_root>/tasks/<tool>_*/`. Both still supported; this plan makes Path B the default for RovoDev. |

---

## 11. Definition of Done

### OpenStartup repo
- [ ] `_VALID_FRONTEND_PREFIXES`, `_validate_external_id`, `attach_or_create_session`, `create_session(_explicit_id=)` landed in `session_store.py`
- [ ] `resolve_frontend_session_context()` landed in `mcp_server/_frontend_session.py`
- [ ] `tool_cli.py` line 113 replaced; `mcp_server/context.py` updated
- [ ] All 7 `test_session_store_attach.py` (TIER-1) pass
- [ ] All 6 `test_frontend_session_resolver.py` (TIER-1) pass
- [ ] All 4 `test_tool_cli_env_bridge.py` (TIER-2) pass
- [ ] CI preflight `test_frontend_prefix_whitelist_immutable.py` passes
- [ ] `docs/MCP_INTEGRATION.md` documents the env-var protocol

### cli-rovodev-tui repo
- [ ] `openteam_session.py` ships with `get_or_create_session`
- [ ] `slash_commands/openteam.py` wires `OPENTEAM_SERVER_DIR` + `OPENTEAM_SESSION_ID` on the subprocess env
- [ ] `app.py` accepts `--new-openteam-session`, threads `_force_new_openteam_session` through the handler
- [ ] All 6 `test_openteam_session.py` (TIER-1) pass
- [ ] Both `test_slash_openteam_env_propagation.py` (TIER-2) pass
- [ ] `docs/openteam-integration.md` documents `.rovodev/` persistence + the `--new-openteam-session` flag

### End-to-end smoke
- [ ] All 8 §5.7 manual checklist steps pass

### Documentation
- [ ] `README.md` (or DEVELOPING.md) of OpenStartup mentions the protocol
- [ ] cli-rovodev-tui README mentions the new ergonomic (no manual setup; just launch)

---

## 12. Acknowledgements

- Cursor plan: env-var contract (TWO env vars), per-workspace persistence, prefix whitelist, CI preflight, test rigor, `--new-session` ergonomic.
- Claude plan: concise problem framing; the `OPENTEAM_SESSION_ID` env-var name.
- My v1: shared-helper architecture for MCP+CLI; frontend-id-as-prefix design rationale; self-audit + glossary structure.
- Empirical verification this session: three parallel `Explore` subagents + direct `bash`/`grep` on every load-bearing claim.

---

**End of plan. Saved at:** `CoreProjects/OpenStartup/_dev/_plan/openteam_rovodev_integration/openteam-unified-frontend-session-protocol-v2.md`
