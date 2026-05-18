# Unified Frontend Session Protocol — INTEGRATED v3

**File:** `openteam-unified-frontend-session-INTEGRATED-v3.md`
**Status:** v3 — second-round integration; ready for review then implementation
**Date:** 2026-05-17 (post second-round cross-audit)

**Integrates (in priority order):**
1. **`openteam-unified-frontend-session-protocol-v2.md`** (RovoDev v2, 815 LOC) — the most empirically grounded; fixes a critical `SessionStore` signature bug present in my INTEGRATED-v2 and adopts the right minimal protocol surface.
2. **`openteam-unified-frontend-session-INTEGRATED-v2.md`** (my prior integration, 1057 LOC) — contributes the WS init handshake extension and per-entry-point server-dir resolution documentation; otherwise superseded.
3. **`~/.claude/plans/eager-roaming-clock.md`** (Claude integrated, 139 LOC) — contributes nothing new in this round; aligned with my v2 (and inherits the same `SessionStore` bug).

**Supersedes:** all three above. Use this file as the single source of truth.

---

## 0. TL;DR

v3 is the **union of correctness**, not a union of features. The biggest change vs my prior INTEGRATED-v2 is **simplification driven by RovoDev v2's correctness audit**:

| What v2 (mine) had | What v3 does | Why |
|---|---|---|
| `SessionStore(server_dir=...)` | `SessionStore(runtime_root, *, resume_server=...)` | v2 used a fake kwarg → would `TypeError` at runtime. Verified at `session_store.py:45-50`. |
| `:` delimiter + Windows `%3A` encoding | `-` delimiter (POSIX-safe; legacy `session-` back-compat for free) | RovoDev v2 empirically verified `:` is POSIX-safe but unnecessary; `-` removes a whole class of cross-platform encoding logic. |
| Per-workspace synthetic server `server_rovodev_<wsuuid>/` | One shared `server_rovodev_default/` for all RovoDev TUI sessions | Less FS clutter; single React UI listing; cleanup is one `rm -rf`. `_atomic_write` in `SessionStore` (verified at `session_store.py:554-572`) handles concurrent `sessions_index.json` writes safely. |
| 4 env vars (`FRONTEND_ID` + `FRONTEND_SESSION_ID` + `FRONTEND_METADATA` + `SERVER_DIR`) | 2 env vars (`SERVER_DIR` + `SESSION_ID`); `frontend_id` derived from prefix | Smaller protocol surface; less to break; less to validate. `frontend_metadata` is reserved for v2-of-this-plan (genuine v2; not needed for v1 workspace-bucket use). |
| `_shared/session_resolver.py` helper called per-executor | Zero executor changes | v5.3 already reads `session_context["session_root"]` and routes to Path B. Once the env bridge in `tool_cli.run_cli` populates that key, executors do the right thing automatically. This is the elegance dividend of v5.3. |
| Separate `build_session_context()` rewrite + `tool_cli` env read | One shared `mcp_server/_frontend_session.py` helper used by BOTH `tool_cli` AND MCP | DRY; one source of truth for env→session_context translation. |

What v3 **keeps** from my prior INTEGRATED-v2 that RovoDev v2 lacked:

1. **WS init handshake extension** — optional `frontend_id`/`frontend_session_id` in the WebSocket init JSON, for the eventual React UI migration to `webui-` prefix.
2. **Server-dir resolution rule per entry point** — explicit documentation of how each entry point (WS / TUI subprocess / MCP standalone / direct CLI) resolves its server directory. v1 implements only TUI; the document anticipates the future MCP-direct and other-frontend pathways.

**Net effort:** ~10 hours focused work for ship-ready v1 (8 phases, 2 PRs).

---

## 1. The gap (verified file:line — independently re-confirmed in v3)

| Layer | Today | Evidence |
|---|---|---|
| React UI → WS slash | ✅ Workspace lands at `<runtime>/servers/<srv>/sessions/<sid>/tasks/<tool>_*/` | `manager_websocket_routes.py:221-226` builds full `session_context = {interactive, task_id, session_id, session_root}` |
| **RovoDev TUI → subprocess** | ❌ Workspace lands at `<runtime>/tasks/<tool>/<tool>_*/` (Path A, standalone) | **`tool_cli.py:114`** literally `session_context: dict[str, Any] = {}` — verified by direct grep this session |
| RovoDev MCP wrapper | ❌ Same as above (no `session_id`, no `session_root`) | `mcp_server/context.py:17-23` — `build_session_context()` returns `{"task_id": "mcp-<uuid8>", "interactive": None}` |
| Direct CLI (`openteam-task` typed by hand) | ❌ Same (acceptable: no frontend identity to attach to) | same as TUI path |

**Concrete losses (verified by tracing the v5.3 workspace allocation plan):**
1. RovoDev runs scatter across `_runtime/tasks/<tool>/` instead of co-locating under a session.
2. UI cannot see RovoDev sessions in `GET /sessions`.
3. No conversation-bucket continuity across consecutive `/task` invocations from the same TUI.
4. No session-export / archive boundary for RovoDev runs.
5. Future frontends (VS Code extension, Slack bot, direct MCP callers) have no contract to follow.

---

## 2. Architectural invariants

1. **Two env vars carry the protocol** across a process boundary: `OPENTEAM_SERVER_DIR` (absolute path to `<runtime>/servers/<server>/`) + `OPENTEAM_SESSION_ID` (prefix-validated external id). **Both must be set together**; partial = warning + fallback to today's Path A.
2. **External session IDs are prefix-validated** against `_VALID_FRONTEND_PREFIXES = {"rovodev", "webui", "slack", "mcp", "session"}` ("session" is legacy back-compat for server-minted `session-<unix>-<hex6>`). CI preflight prevents drift.
3. **`SessionStore.attach_or_create_session(external_id)`** is the single attach point — idempotent: returns existing session if `external_id` already on disk, else creates with `id=external_id` via the new `create_session(_explicit_id=...)` kwarg path.
4. **`mcp_server/_frontend_session.py:resolve_frontend_session_context()`** is the **single shared helper** used by BOTH `tool_cli.run_cli` AND `mcp_server.context.build_session_context()`. One translation rule, two callers.
5. **Zero executor changes.** v5.3 already reads `session_context["session_root"]` and routes to Path B (`allocate_tool_workspace(tool_name, base_dir=session_root/"tasks")`). Once the env bridge populates the key, everything downstream just works.
6. **Per-workspace TUI persistence:** `.rovodev/openteam_session_id` + `.rovodev/openteam_server_dir` next to the user's workspace; survives TUI restarts; reset via `--new-openteam-session` CLI flag or `rm -rf .rovodev/`.
7. **One shared server for RovoDev:** single `<runtime>/servers/server_rovodev_default/` for ALL TUI workspaces, regardless of which directory launched the TUI. Sessions inside it disambiguate by `rovodev-<uuid>` id.
8. **`-` delimiter (NOT `:`).** POSIX-safe AND Windows-safe AND back-compat with legacy `session-<unix>-<hex6>` ids. Whitelist makes `partition("-")` deterministic even when remainder contains hyphens (RovoDev UUID4 case).
9. **No conversation-turn coupling in v1.** OpenTeam session is a workspace bucket only.
10. **No new dependencies in either repo.**
11. **Total backward compatibility.** WS path unchanged; bare CLI unchanged; legacy `session-<unix>-<hex6>` ids continue to work.
12. **Forward-compat hook:** WS init handshake accepts optional `frontend_id`/`frontend_session_id` (absent → today's `ui` + bare-`sid` semantics) so the React UI can migrate to `webui-` prefix in a follow-up PR without breaking changes.

---

## 3. Architecture

### 3.1 Flow diagram

```
┌────────────────────────────────────────┐         ┌─────────────────────────────────────────────────┐
│  RovoDev TUI                           │         │  OpenTeam (single backend, multi-frontend)      │
│                                        │         │                                                 │
│  /task <prompt>                        │         │  subprocess: openteam-task ...                  │
│   └─ slash handler:                    │         │    tool_cli.run_cli():                          │
│      workspace = _get_workspace_path() │         │      session_context =                          │
│      sd, sid = openteam_session.       │         │        resolve_frontend_session_context()       │
│                get_or_create_session(  │ ──env──▶│        ↓ (reads env vars)                       │
│                  workspace)            │         │        OPENTEAM_SERVER_DIR =                    │
│      env["OPENTEAM_SERVER_DIR"] = sd   │         │          .../servers/server_rovodev_default     │
│      env["OPENTEAM_SESSION_ID"] = sid  │         │        OPENTEAM_SESSION_ID = rovodev-550e...    │
│      spawn(openteam-task, env=env)     │         │        ↓                                        │
│                                        │         │        SessionStore(                            │
│                                        │         │          runtime_root=server.parent.parent,     │
│                                        │         │          resume_server=server.name)             │
│                                        │         │        ↓                                        │
│                                        │         │        .attach_or_create_session(sid)  ← idempo │
│                                        │         │        ↓                                        │
│                                        │         │        session_context = {                      │
│                                        │         │          session_id: sid,                       │
│                                        │         │          session_root: store.get_session_dir(...│
│                                        │         │          task_id: f"{sid}-<uuid8>",             │
│                                        │         │          interactive: None,                     │
│                                        │         │        }                                        │
│                                        │         │      ↓                                          │
│                                        │         │      executor.execute(args, ctx)  ← UNCHANGED   │
│                                        │         │      ↓                                          │
│                                        │         │      workspace allocator (v5.3 Path B):         │
│                                        │         │        base_dir = ctx["session_root"]/"tasks"   │
│                                        │         │        → <session_root>/tasks/<tool>_<TS>_<u8>/ │
│                                        │         │                                                 │
│  Second /task in same TUI →            │         │  Same env → attach_or_create returns same       │
│  same env values →                     │         │  session → second task workspace lands UNDER    │
│                                        │         │  the same session directory ✅                  │
└────────────────────────────────────────┘         └─────────────────────────────────────────────────┘
```

### 3.2 On-disk layout (post-implementation)

```
_runtime/
├── tasks/                                          ← legacy Path A (bare CLI, no env)
│   └── task/
│       └── task_<TS>_<uuid8>/
├── servers/
│   ├── server_rovodev_default/                    ← NEW: shared by all RovoDev TUI workspaces
│   │   ├── server_info.json                       ← {"frontend":"rovodev","shared":true,...}
│   │   └── sessions/
│   │       ├── rovodev-550e8400_<TS>/             ← one per (workspace × launch-or-explicit-reset)
│   │       │   ├── session_state.json
│   │       │   └── tasks/
│   │       │       ├── task_<TS>_<uuid8>/
│   │       │       └── create_role_<TS>_<uuid8>/
│   │       └── rovodev-6f7a9b2c_<TS>/
│   │           └── ...
│   └── server_<TS>_<uuid8>/                       ← existing React UI server (unchanged)
│       └── sessions/
│           └── session-<unix>-<hex6>_<TS>/
│               └── tasks/...
```

### 3.3 Server-dir resolution rule per entry point (v1 implements path 2; paths 3-4 are documented for future)

| Entry point | Server-dir resolution | v1 status |
|---|---|---|
| 1. **WS server** | The WS server's own dir, minted at boot by `SessionStore.__init__` (today's behavior) | unchanged |
| 2. **RovoDev TUI subprocess** | Shared `<runtime>/servers/server_rovodev_default/`. Path persisted in `<workspace>/.rovodev/openteam_server_dir` (idempotency / explicit). Passed via `OPENTEAM_SERVER_DIR` env. | **shipping in v1** |
| 3. **MCP standalone** (future MCP-direct clients, e.g. Claude Desktop with non-RovoDev config) | MCP client SHOULD set `OPENTEAM_SERVER_DIR` to its preferred location. If absent, fall back to per-host `<runtime>/servers/server_mcp_default/` (synthetic; lazy-created). | documented; v1 wires but doesn't actively populate |
| 4. **Direct CLI** (`openteam-task` typed by hand, no frontend) | Both env vars unset → `resolve_frontend_session_context()` returns `{}` → today's Path A behavior preserved. No regression. | unchanged |

**Rationale for the per-entry-point rule:** one shared server per frontend prevents N-server-dir proliferation (the over-engineering my INTEGRATED-v2 suffered from) while still isolating frontends from each other (Slack sessions shouldn't appear in MCP server's session list, etc.). v1 only needs path 2; paths 3-4 are reserved by the design.

### 3.4 The six touch points (and their line budgets)

| # | File | Owner repo | Change | LOC |
|---|---|---|---|---|
| **1a** | `src/openteam/server/services/session_store.py` | OpenStartup | Add `_VALID_FRONTEND_PREFIXES`, `_validate_external_id`, `attach_or_create_session`; refactor `create_session(_explicit_id=None)` | ~55 |
| **1b** | `src/openteam/mcp_server/_frontend_session.py` (NEW) | OpenStartup | `resolve_frontend_session_context()` — shared env-bridge helper | ~60 |
| **1c** | `src/openteam/server/services/tool_cli.py` | OpenStartup | Replace line 114 `session_context = {}` with `session_context = resolve_frontend_session_context()` | ~5 |
| **1d** | `src/openteam/mcp_server/context.py` | OpenStartup | Layered use of shared helper (preserve ephemeral fallback for back-compat) | ~15 |
| **1e** | `src/openteam/server/routes/manager_websocket_routes.py` | OpenStartup | WS init: accept optional `frontend_id` / `frontend_session_id` from init JSON; back-compat defaults to `"ui"` + bare `sid` | ~15 |
| **2** | `packages/cli-rovodev-tui/src/rovodev_tui/openteam_session.py` (NEW) | cli-rovodev-tui | Per-workspace persistence helper | ~70 |
| **3** | `packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py` | cli-rovodev-tui | Handler wiring: 2 env vars + task_id derivation | ~12 |
| **4** | `packages/cli-rovodev-tui/src/rovodev_tui/app.py` | cli-rovodev-tui | `--new-openteam-session` flag (one-shot) | ~10 |

**Total: ~240 LOC net code across 8 files (3 new behaviour, 5 surgical edits).**

---

## 4. Implementation

### 4.1 `session_store.py` — prefix whitelist + `attach_or_create_session` (Phase 1a)

**Add at module top** (after existing imports):

```python
# Frontend identity prefixes. Immutable contract — guarded by CI preflight
# test_frontend_prefix_whitelist_immutable.py. Adding a new frontend? Update
# the test in the same PR. See openteam-unified-frontend-session-INTEGRATED-v3.md
# §2 invariant 2.
_VALID_FRONTEND_PREFIXES: frozenset[str] = frozenset({
    "rovodev",   # cli-rovodev-tui (inaugural client) + RovoDev MCP wrapper
    "webui",     # reserved for React UI's post-migration prefix (v3 §1e)
    "slack",     # reserved for hypothetical Slack bot
    "mcp",       # reserved for direct MCP callers (non-RovoDev)
    "session",   # LEGACY: today's server-minted `session-<unix>-<hex6>` ids
})

# Reject path-traversal and filesystem-hostile chars in the remainder. The
# prefix is whitelisted; the remainder is user-supplied (e.g., a UUID4 or
# a legacy server-minted id), so it gets scrubbed at the boundary.
_REMAINDER_BAD_TOKENS: frozenset[str] = frozenset({"/", "\\", "..", "\x00"})


def _validate_external_id(external_id: str) -> tuple[str, str]:
    """Validate an external session id and return (prefix, remainder).

    Format: <prefix>-<remainder>
    - prefix MUST be in _VALID_FRONTEND_PREFIXES
    - remainder MUST be non-empty and contain no path-traversal chars

    Raises ValueError on any violation. After successful return, the tuple
    is safe to use in POSIX filesystem paths. Hyphens inside the remainder
    are fine because partition("-") returns only the FIRST segment as
    prefix; whitelist closure makes the parse deterministic even for
    UUID4 remainders like 550e8400-e29b-41d4-a716-446655440000.
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

**Modify `create_session()`** (today at session_store.py:158-201) to accept an `_explicit_id` kwarg:

```python
def create_session(
    self,
    title: str | None = None,
    *,
    _explicit_id: str | None = None,   # NEW: bypass server-minting
) -> dict[str, Any]:
    """Create a new session directory and return the full session object.

    - ID format (default):           session-<unix_timestamp>-<6_hex_chars>
    - ID format (_explicit_id set):  use the supplied id verbatim. Caller
                                     is responsible for validation (use
                                     attach_or_create_session for the
                                     validated path).
    - Directory: <session_id>_<YYYYMMDD_HHMMSS>/session_state.json
    """
    now = time.time()
    session_id = _explicit_id if _explicit_id is not None else (
        f"session-{int(now)}-{uuid4().hex[:6]}"
    )
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
    every frontend (RovoDev TUI today; MCP and future frontends per §3.3)
    to attach a stable session id that survives subprocess boundaries.

    Two calls with the same external_id return the SAME session dict and
    the SAME on-disk session directory (file-system idempotent).
    """
    _validate_external_id(external_id)
    existing = self.get_session(external_id)
    if existing is not None:
        return existing
    return self.create_session(title=title, _explicit_id=external_id)
```

### 4.2 `mcp_server/_frontend_session.py` (NEW) — the shared env-bridge helper (Phase 1b)

```python
"""Shared env-var → session_context bridge for tool_cli + MCP server.

Both the subprocess CLI path (tool_cli.run_cli) and the in-process MCP
wrappers (mcp_server.server.openteam_*) need to translate the two env
vars (OPENTEAM_SERVER_DIR + OPENTEAM_SESSION_ID) into a populated
session_context dict. This module is the single source of truth.

Locating this helper under mcp_server/ is a small layering asymmetry
(a CLI module importing from mcp_server) but the alternative is
duplicating ~60 LOC in two places. The dependency direction is one-way
(tool_cli → mcp_server._frontend_session), and the helper is leaf-level
(it only imports SessionStore lazily inside the function body, so no
import cycle is possible).
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

    Resolution table:
      - Both env vars set + valid       → attach (or create) the named session,
                                          return fully-populated session_context
                                          (session_id, session_root, task_id,
                                           interactive=None).
      - Neither set                     → return {} (today's bare-CLI behavior;
                                          no warning — this is the no-frontend
                                          path).
      - Partial set OR validation fail  → log WARNING, return {} (degrade
                                          gracefully; the tool still runs, but
                                          lands in Path A — same as if the env
                                          vars weren't there).

    The "degrade gracefully on failure" rule means a misconfigured frontend
    never crashes a tool invocation — at worst, the user loses session
    affiliation for that one run.
    """
    server_dir = os.environ.get("OPENTEAM_SERVER_DIR", "").strip()
    session_id = os.environ.get("OPENTEAM_SESSION_ID", "").strip()

    if not server_dir and not session_id:
        return {}  # bare-CLI fast path (no frontend)

    if not (server_dir and session_id):
        _logger.warning(
            "[_frontend_session] partial env (OPENTEAM_SERVER_DIR=%r, "
            "OPENTEAM_SESSION_ID=%r); both must be set; falling back to "
            "empty context (Path A workspace).",
            server_dir, session_id,
        )
        return {}

    try:
        # Lazy import: keeps this module leaf-level (no cycle with tool_cli).
        from openteam.server.services.session_store import SessionStore

        # SessionStore's real signature (verified at session_store.py:45-50):
        #   SessionStore(runtime_root, *, resume_server=None)
        # OPENTEAM_SERVER_DIR is the absolute server directory
        # (.../runtime/servers/<srv>/); runtime_root is its grandparent
        # (.../runtime/).
        server_path = Path(server_dir).resolve()
        if not server_path.is_dir():
            raise FileNotFoundError(
                f"OPENTEAM_SERVER_DIR not a directory: {server_path}"
            )
        store = SessionStore(
            runtime_root=server_path.parent.parent,
            resume_server=server_path.name,
        )
        store.attach_or_create_session(session_id)
        session_root = str(store.get_session_dir(session_id))

        ctx: dict[str, Any] = {
            "session_id":   session_id,
            "session_root": session_root,
            # task_id includes session_id for traceability (graph-view-v4 NDJSON
            # envelopes carry this in their `task_id` field). uuid8 suffix
            # disambiguates concurrent /task calls within one session.
            "task_id":      f"{session_id}-{uuid.uuid4().hex[:8]}",
            # interactive=None is the only sane default; subprocess path can't
            # accept a WebSocketInteractive from the parent. Graph-view-v4
            # wires a separate NDJSON channel via ROVODEV_TUI_GRAPH_FD;
            # orthogonal to this plan.
            "interactive": None,
        }
        _logger.info(
            "[_frontend_session] attached: id=%s root=%s",
            session_id, session_root,
        )
        return ctx
    except Exception as exc:
        _logger.warning(
            "[_frontend_session] failed to attach OPENTEAM_SESSION_ID=%s "
            "under OPENTEAM_SERVER_DIR=%s (%s); falling back to empty context.",
            session_id, server_dir, exc,
        )
        return {}
```

### 4.3 `tool_cli.py` — line 114 replacement (Phase 1c)

```python
# Replace line 114:
# OLD:  session_context: dict[str, Any] = {}
# NEW:
from openteam.mcp_server._frontend_session import resolve_frontend_session_context
session_context: dict[str, Any] = resolve_frontend_session_context()
```

One line. The helper does all the work.

### 4.4 `mcp_server/context.py` — layered use of shared helper (Phase 1d)

```python
"""Build session_context for in-process executor calls."""
from __future__ import annotations
import os
import uuid
from typing import Any

from openteam.mcp_server._frontend_session import resolve_frontend_session_context

_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",   # preserved for back-compat consumers
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}


def build_session_context() -> dict[str, Any]:
    """Build the per-invocation context dict for executor.execute(args, ctx).

    Two paths through this function:
      1. Env vars set → attach to the named frontend session (canonical v1 path).
      2. Env vars NOT set → ephemeral session (pre-protocol back-compat).
    """
    # Try the unified-frontend-session bridge first.
    ctx = resolve_frontend_session_context()

    # If the bridge returned empty, seed an ephemeral context so the executor
    # still gets a sensible task_id (back-compat with pre-protocol MCP callers).
    if not ctx:
        ctx = {"task_id": f"mcp-{uuid.uuid4().hex[:8]}", "interactive": None}

    # Layer the supplementary OpenTeam env vars on top (working dir, cloud id, ...).
    for env_key, ctx_key in _ENV_MAP.items():
        if (v := os.environ.get(env_key, "").strip()):
            ctx[ctx_key] = v
    return ctx
```

### 4.5 WS init handshake extension (Phase 1e) — *kept from my INTEGRATED-v2*

In `src/openteam/server/routes/manager_websocket_routes.py` around line 510:

```python
first_msg = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)

if first_msg.get("type") != "init":
    await send_safe({"type": "error", "message": "Expected init message"})
    return

sid = first_msg.get("session_id", "").strip()
if not sid:
    await send_safe({"type": "error", "message": "Expected session_id"})
    return

# v3 forward-compat: extract optional frontend identity. Today's React UI
# sends only {"session_id": "..."}; tomorrow's UI can opt-in by also sending
# {"frontend_id": "webui", "frontend_session_id": "<uuid>"}. Absent fields
# default to "ui" + bare-sid (today's semantics; ZERO behavior change for
# pre-migration clients).
frontend_id = first_msg.get("frontend_id", "ui").strip() or "ui"
frontend_session_id = first_msg.get("frontend_session_id", "").strip() or sid

# session_context built from these for the slash dispatcher path; executor
# path is unchanged (session_id is already populated by today's WS code; we
# just enrich the context dict).
```

**This is purely forward-compat.** v1 ships the hook; the React UI migration to `webui-<uuid>` is a separate POST-1 PR (the protocol doesn't break the UI today).

### 4.6 `cli-rovodev-tui/.../openteam_session.py` (NEW) (Phase 2)

```python
"""Per-workspace OpenTeam session persistence for the RovoDev TUI.

Each TUI workspace gets ONE OpenTeam session id, persisted under
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

_ROVODEV_DIR_NAME   = ".rovodev"
_SESSION_ID_FILE    = "openteam_session_id"
_SERVER_DIR_FILE    = "openteam_server_dir"
_SHARED_SERVER_NAME = "server_rovodev_default"

# Prefix MUST match _VALID_FRONTEND_PREFIXES in OpenTeam's session_store.py.
# CI preflight test_frontend_prefix_whitelist_immutable.py + the cross-helper
# test_runtime_root_helpers_agree.py guard against drift across the boundary.
_FRONTEND_PREFIX = "rovodev"


def _find_runtime_root() -> Path:
    """Locate <runtime>/ via the same 4-tier fallback OpenTeam uses.

    Mirrors openteam.server.resources.tools._shared.workspace_allocator.
    find_runtime_root so TUI-spawned subprocesses converge on the same
    directory the OpenTeam server would. Drift is caught by the regression
    test test_runtime_root_helpers_agree.py.
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
        (server_dir, session_id) — both ready to be passed via env vars to
        the subprocess. session_id has the form "rovodev-<32-hex-chars>".

    Persistence files written:
        <workspace>/.rovodev/openteam_session_id    (e.g. "rovodev-550e84...")
        <workspace>/.rovodev/openteam_server_dir    (absolute path)
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
        # Self-heal: only reuse if the persisted id is well-formed AND the
        # persisted server still exists (handles `cp -r`'d workspaces).
        if sid.startswith(f"{_FRONTEND_PREFIX}-") and persisted_server.exists():
            return persisted_server, sid

    # Mint fresh
    sid = f"{_FRONTEND_PREFIX}-{uuid.uuid4().hex}"
    sid_file.write_text(sid)
    server_file.write_text(str(server_dir))
    return server_dir, sid
```

### 4.7 `slash_commands/openteam.py` — handler wiring (Phase 3)

Inside `_make_handler` (today around lines 134-143 of the file), **just before** the existing `argv, env = _build_argv_and_env(...)` call:

```python
# v3 unified-frontend protocol: derive (server_dir, session_id) for the
# current TUI workspace, and pass both into the subprocess via env.
from pathlib import Path
from rovodev_tui.openteam_session import get_or_create_session

workspace = Path(_get_workspace_path(app))
new_session_flag = bool(getattr(app, "_force_new_openteam_session", False))
server_dir, session_id = get_or_create_session(workspace, new_session=new_session_flag)
# --new-openteam-session is one-shot: consume the flag after first use.
if new_session_flag:
    app._force_new_openteam_session = False

argv, env = _build_argv_and_env(binary, module_name, user_args)
env["OPENTEAM_SERVER_DIR"] = str(server_dir)
env["OPENTEAM_SESSION_ID"] = session_id
# Note: ROVODEV_TUI_GRAPH_FD (graph-view-v4) is set elsewhere; additive.
```

### 4.8 `app.py` — `--new-openteam-session` CLI flag (Phase 4)

Add to `RovoDevApp` (near existing reactive declarations around `app.py:403`):

```python
# v3 unified-frontend protocol: when True, the NEXT /task-class slash command
# will mint a fresh OpenTeam session id (and persist it, overwriting whatever
# was in .rovodev/openteam_session_id). The handler resets this to False
# after consuming it (one-shot).
_force_new_openteam_session: bool = False
```

And in the CLI argparse setup (in `app.py`'s `main()`):

```python
parser.add_argument(
    "--new-openteam-session", action="store_true",
    help="Mint a fresh OpenTeam session id for the next /task in this TUI launch. "
         "Overwrites .rovodev/openteam_session_id in this workspace. The shared "
         "OpenTeam server dir is preserved; only the session id rotates.",
)
# ...
if args.new_openteam_session:
    app._force_new_openteam_session = True
```

**Naming note:** `--new-openteam-session` (not just `--new-session`) disambiguates from any TUI-internal session concept (RovoDev has its own `current_session_id`).

### 4.9 Executors — zero changes required

**The elegance dividend of workspace-allocation v5.3.** Verified by direct read: the v5.3 implementation already reads `session_context["session_root"]` and calls `allocate_tool_workspace(tool_name, base_dir=Path(session_root) / "tasks")`. Once the env bridge populates that key, the existing executors do the right thing automatically. **No `_shared/session_resolver.py` helper needed; no per-executor patch needed.**

This is the single biggest correctness/simplicity win in this plan vs my INTEGRATED-v2.

---

## 5. Tests

### 5.1 OpenStartup — `test/openteam/services/test_session_store_attach.py` (TIER-1, 8 tests)

| Test | Assertion |
|---|---|
| `test_attach_or_create_idempotent` | Two calls with same `rovodev-abc123` return same session dict; on-disk dir exists once |
| `test_attach_or_create_rejects_unknown_prefix` | `foobar-xyz` raises `ValueError("unknown frontend prefix")` |
| `test_attach_or_create_rejects_unsafe_remainder_path_traversal` | `rovodev-../etc/passwd` raises `ValueError` |
| `test_attach_or_create_rejects_unsafe_remainder_nullbyte` | `rovodev-x\x00y` raises `ValueError` |
| `test_attach_or_create_rejects_unsafe_remainder_backslash` | `rovodev-x\\y` raises `ValueError` (Windows path-traversal) |
| `test_attach_or_create_session_dir_format` | After attach, `get_session_dir("rovodev-abc")` returns `<server>/sessions/rovodev-abc_<TS>/` |
| `test_attach_or_create_accepts_legacy_session_prefix` | `session-1737130000-deadbe` accepted (legacy back-compat); no exception |
| `test_attach_or_create_propagates_title` | `attach_or_create_session("rovodev-x", title="Foo")` → session["title"] == "Foo" |

### 5.2 OpenStartup — `test/openteam/mcp_server/test_frontend_session_resolver.py` (TIER-1, 7 tests)

| Test | Assertion |
|---|---|
| `test_no_env_returns_empty` | Neither env var set → returns `{}` (no warning logged) |
| `test_partial_env_warns_and_returns_empty` | Only `OPENTEAM_SESSION_ID` set → WARNING logged via caplog, returns `{}` |
| `test_both_env_attaches_and_returns_context` | Both env vars valid → ctx has `session_id`, `session_root` matching `<server>/sessions/rovodev-x_<TS>/`, `task_id`, `interactive=None` |
| `test_invalid_prefix_warns_and_falls_back` | `OPENTEAM_SESSION_ID=foobar-x` → WARNING logged, returns `{}` (no `ValueError` propagates) |
| `test_nonexistent_server_dir_warns_and_falls_back` | `OPENTEAM_SERVER_DIR=/nonexistent` → WARNING logged, returns `{}` |
| `test_task_id_uniqueness` | Two calls with same env → different `task_id` values (uuid suffix differs); same `session_id` |
| `test_idempotent_attach` | Two consecutive calls with same env → both return the same session_root pointing at the SAME on-disk directory |

### 5.3 OpenStartup — `test/openteam/services/test_tool_cli_env_bridge.py` (TIER-2 integration, 4 tests)

| Test | Assertion |
|---|---|
| `test_subprocess_no_env_keeps_empty_context` | Spawn `openteam-mock-task` with NO env vars; assert workspace lands at Path A (`<runtime>/tasks/mock_task/...`) |
| `test_subprocess_both_env_attaches_session` | Spawn with both env vars; assert workspace lands under `<server>/sessions/rovodev-x_<TS>/tasks/mock_task_*` |
| `test_subprocess_partial_env_warns_and_falls_back` | Spawn with only `OPENTEAM_SESSION_ID`; assert Path A + warning on stderr |
| `test_subprocess_invalid_prefix_falls_back` | Spawn with `OPENTEAM_SESSION_ID=foobar-x`; assert Path A + warning |

### 5.4 OpenStartup — `test/openteam/services/test_frontend_prefix_whitelist_immutable.py` (TIER-1 CI preflight)

```python
"""Guard against accidental whitelist expansion (or contraction).

Any change to the frontend prefix whitelist is an API decision and MUST
be discussed in a PR. This test reflects the contract; updating the
expected set without updating §2 invariant 2 of the unified-frontend
plan is itself a bug.
"""
def test_known_frontend_prefixes_only():
    from openteam.server.services.session_store import _VALID_FRONTEND_PREFIXES
    expected = frozenset({"rovodev", "webui", "slack", "mcp", "session"})
    assert _VALID_FRONTEND_PREFIXES == expected, (
        f"prefix whitelist drifted from spec.\n"
        f"  added: {sorted(_VALID_FRONTEND_PREFIXES - expected)}\n"
        f"  removed: {sorted(expected - _VALID_FRONTEND_PREFIXES)}\n"
        f"If intentional, update §2 invariant 2 of "
        f"openteam-unified-frontend-session-INTEGRATED-v3.md in the same PR."
    )
```

### 5.5 OpenStartup — WS init handshake regression test (TIER-1, 3 tests)

```python
# test/openteam/routes/test_ws_init_handshake_frontend_optional.py
def test_init_without_frontend_fields_defaults_to_ui_and_bare_sid():
    """Today's React UI sends only {session_id}. Must continue to work."""
    # ... assert frontend_id == "ui", frontend_session_id == sid ...

def test_init_with_frontend_fields_propagates():
    """Forward-compat: init JSON can include frontend_id + frontend_session_id."""
    # ... assert both threaded through session_context correctly ...

def test_init_with_frontend_fields_validates_prefix():
    """Malformed frontend_id rejected — does NOT crash; falls back to defaults."""
    # ... send {frontend_id: "../etc"}; assert defaults applied + warning ...
```

### 5.6 cli-rovodev-tui — `tests/test_openteam_session.py` (TIER-1, 6 tests)

| Test | Assertion |
|---|---|
| `test_first_call_mints_and_persists` | Fresh workspace → `get_or_create_session(ws)` returns `(server, sid)` where `sid` matches `^rovodev-[a-f0-9]{32}$`; `.rovodev/openteam_session_id` exists with that value |
| `test_second_call_reuses_persisted` | Two calls in same workspace → identical `sid` |
| `test_new_session_flag_overwrites_persistence` | `new_session=True` → fresh `sid`; `.rovodev/openteam_session_id` overwritten |
| `test_corrupted_persistence_self_heals` | Manually write garbage to `.rovodev/openteam_session_id` → next call mints fresh, does NOT crash |
| `test_shared_server_dir_is_singleton` | Two different workspaces → both point at `<runtime>/servers/server_rovodev_default/` (NOT per-workspace) |
| `test_workspace_move_invalidates_persistence` | Mutate persisted server_dir to non-existent path → next call mints fresh (NOT crash) |

### 5.7 cli-rovodev-tui — `tests/test_slash_openteam_env_propagation.py` (TIER-2, 2 tests)

| Test | Assertion |
|---|---|
| `test_handler_sets_server_dir_and_session_id_env` | Monkeypatch `create_subprocess_exec`; invoke handler; capture the `env` arg; assert both `OPENTEAM_SERVER_DIR` and `OPENTEAM_SESSION_ID` are present and consistent |
| `test_handler_one_shot_new_session_flag` | Set `app._force_new_openteam_session = True`; invoke handler twice; first call mints fresh, second reuses (flag consumed and reset) |

### 5.8 Cross-package — `test_runtime_root_helpers_agree.py` (TIER-1)

```python
"""Regression: ensure the TUI's _find_runtime_root() and OpenTeam's
find_runtime_root() return the same Path for the same env / cwd.

Drift between these two helpers would cause TUI-spawned subprocesses
to write to a DIFFERENT runtime than the OpenTeam server would, breaking
session visibility.
"""
def test_helpers_agree_on_env_override():
    # ... set OPENTEAM_RUNTIME_DIR=/tmp/foo; call both helpers; assert equal ...

def test_helpers_agree_on_src_walk():
    # ... mock filesystem with src/ + pyproject.toml; assert both find it ...

def test_helpers_agree_on_home_fallback():
    # ... clear env + cwd; assert both fall back to ~/.openteam/_runtime ...
```

### 5.9 E2E smoke (TIER-3, manual checklist; convert to xfailed pytest later)

| Step | Pass criterion |
|---|---|
| Launch TUI in fresh dir | `.rovodev/openteam_session_id` created; matches `^rovodev-[a-f0-9]{32}$` |
| Run `/task "what is 2+2"` | Task workspace at `<runtime>/servers/server_rovodev_default/sessions/rovodev-*_<TS>/tasks/task_*/` |
| Run `/task "another"` in same TUI | Second task workspace under the SAME session dir |
| Ctrl-C, restart TUI in same dir, `/task "third"` | Lands under the SAME session dir (resume worked) |
| Launch with `rovodev --new-openteam-session` | Fresh `sid` in `.rovodev/openteam_session_id`; previous session dir on disk unchanged |
| Run `/task` in a SECOND workspace | New `sid`; lives under the SAME `server_rovodev_default/` as the first |
| Open React UI's `/sessions` listing | All `rovodev-*` sessions appear alongside `session-*` |
| Run `/task` from React UI WS path | Still uses today's `session-<unix>-<hex6>` (WS path unchanged) |

**Total test count: 8 + 7 + 4 + 1 + 3 + 6 + 2 + 3 = 34 tests.**

---

## 6. Phased delivery

| # | Phase | Effort | Depends on | Blocks |
|---|---|---|---|---|
| **0**  | Verify workspace-allocation v5.3 is merged + graph-view-v4 round-9 syntax is fixed | 10min | — | all |
| **1a** | `session_store.py`: `_VALID_FRONTEND_PREFIXES`, `_validate_external_id`, `attach_or_create_session`, `create_session(_explicit_id=)` | 1h | 0 | 1b, 5.1, 5.4 |
| **1b** | `mcp_server/_frontend_session.py`: `resolve_frontend_session_context()` shared helper | 1h | 1a | 1c, 1d, 5.2 |
| **1c** | `tool_cli.py`: line-114 replacement (use shared helper) | 15min | 1b | 5.3 |
| **1d** | `mcp_server/context.py`: layered use of shared helper | 30min | 1b | 5.2 |
| **1e** | `manager_websocket_routes.py`: optional frontend fields in WS init | 1h | 1a | 5.5 |
| **2**  | `cli-rovodev-tui/openteam_session.py` (new file) | 2h | 0 | 3, 5.6 |
| **3**  | `slash_commands/openteam.py`: handler wiring (~12 LOC) | 30min | 2, 1c | 5.7 |
| **4**  | `app.py`: `--new-openteam-session` flag (~10 LOC) | 30min | 3 | 5.7 |
| **5**  | All tests in §5 (8+7+4+1+3+6+2+3 = 34 tests) | 4h | 1a-4 | DoD |
| **6**  | E2E smoke checklist (§5.9) | 30min | 5 | DoD |
| **7**  | Docs: `MCP_INTEGRATION.md`, `DEVELOPING.md`, `README.md`, `openteam-integration.md` | 1h | 6 | DoD |
| **POST-1** | React UI migration to `webui-` prefix (uses §1e's WS init extension) | 0.5d | — | n/a |
| **POST-2** | Conversation-turn coupling (option II from design questionnaire) | TBD | POST-1 | n/a |
| **POST-3** | `OPENTEAM_FRONTEND_METADATA` env var for audit provenance | 1h | — | n/a |

**Critical path:** 0 → 1a → 1b → (1c parallel 1d parallel 1e) → 2 → 3 → 4 → 5 → 6 → 7.
**Total effort to ship-ready v1: ~10 hours focused work.** With two engineers (one OpenStartup, one cli-rovodev-tui), parallelisable to ~6 hours.

**Recommended PR split:**
- **PR #1 (OpenStartup):** Phases 1a-1e + tests 5.1/5.2/5.3/5.4/5.5. Ships behind the env-var contract — a no-op unless env vars are set; safe to merge first; React UI unaffected.
- **PR #2 (cli-rovodev-tui):** Phases 2/3/4 + tests 5.6/5.7. Depends on PR #1 being released.
- **PR #3 (both repos):** Cross-package test 5.8 + Phase 6 E2E + Phase 7 docs.

---

## 7. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Colon-in-dirname Windows hazard (my prior v2 invented Windows encoding for it) | None | None | **Avoided entirely**: v3 uses `-` delimiter (POSIX + Windows safe; back-compat with legacy `session-<unix>-<hex6>`). |
| R2 | Two TUI invocations in same workspace race on `.rovodev/openteam_session_id` | Medium | Low | First-writer-wins; both write the same UUID4 space (collision negligible); on conflict the loser self-heals on next call. |
| R3 | `session_state.json` writes race across concurrent `/task` calls in the same session | Medium | Low | `SessionStore._atomic_write()` uses `tempfile.mkstemp + os.replace` (verified at `session_store.py:554-572`) — atomic on POSIX. Each `/task` writes to its own `tasks/<tool>_*/` subdir, so only session metadata contends. |
| R4 | Stale `.rovodev/openteam_server_dir` after `cp -r` workspace move | Medium | Low | Self-healed: §4.6's `get_or_create_session` checks `persisted_server.exists()`; if not, mints fresh. |
| R5 | Malicious shell sets `OPENTEAM_SESSION_ID=<victim-id>` from another user | Low | Low | OpenStartup is single-user; filesystem permissions are the only boundary. Prefix-whitelist + remainder-sanitization are the protocol boundary; deeper auth out of scope. |
| R6 | Sessions accumulate forever under `server_rovodev_default/sessions/` | High | Low | GC out of scope (inherited from v5.3). `rm -rf .rovodev/` resets a workspace; `rm -rf <runtime>/servers/server_rovodev_default/sessions/rovodev-*` nukes all RovoDev sessions in one command. |
| R7 | `task_id = f"{session_id}-{uuid8}"` (e.g. `rovodev-550e8400-...-deadbeef`) is longer than today's `task-<uuid8>` | Low | Low | Phase 7 doc note: React UI's task_id display should be truncated for visual length only; routing uses the full id. |
| R8 | Prefix whitelist drift (someone adds `"frontend99"` without updating spec) | Medium | Low | CI preflight `test_frontend_prefix_whitelist_immutable.py` (§5.4) blocks merge. |
| R9 | Shared-helper import cycle: `tool_cli` imports from `mcp_server._frontend_session` | Low | None | The helper imports `SessionStore` **lazily** inside the function body; no module-load-time cycle. Verified by `python -c "import openteam.server.services.tool_cli, openteam.mcp_server.context"`. |
| R10 | User confused by `--new-openteam-session` vs TUI's own session reset | Medium | Low | Help text + docs explicit; flag name is intentionally long (no `--new-session` shadow). |
| R11 | `OPENTEAM_RUNTIME_DIR` set differently between TUI and subprocess → they write to different runtimes | Low | High | Subprocess inherits env unless overridden; TUI's `_find_runtime_root()` mirrors OpenTeam's. CI preflight `test_runtime_root_helpers_agree.py` (§5.8) guards. |
| R12 | Concurrent TUI processes from DIFFERENT workspaces share the one `server_rovodev_default/` server → race on `sessions_index.json` | Medium | Low | `_atomic_write` mitigates (R3 above). Plus: cross-workspace `/task` invocations are rare in practice (one TUI per terminal per workspace). If this becomes a real bottleneck, post-ship enhancement: switch to per-host shard `server_rovodev_<host-uuid>/` (no protocol change; just helper change). |
| R13 | RovoDev TUI version inconsistent with OpenTeam version (e.g., TUI sends new env var, old OpenTeam doesn't read it) | Medium | None | Additive protocol; old OpenTeam ignores the env vars, lands in Path A — degraded but functional. No crash. |

---

## 8. Out of scope (deliberate v1 boundaries)

- **Conversation-turn coupling.** Each `/task` is conversationally isolated. The OpenTeam session is a workspace-bucket only. POST-2.
- **React UI migration to `webui-` prefix.** Legacy `session-<unix>-<hex6>` ids keep working via the whitelist entry. POST-1.
- **MCP-direct callers in production.** The `mcp` prefix is reserved; no client wiring in v1.
- **Slack / VS Code extension / other frontends.** Reserved prefixes; per-frontend wiring is future work.
- **Session cleanup / GC.** Inherited from `tool_workspace_allocation` plan: deferred.
- **Typed `SessionContext` dataclass.** Keep `session_context` as dict (today's pattern). TypedDict refactor is separate.
- **Cross-machine session continuity.** A `rovodev-X` on machine A vs same on machine B would conceptually be the same OpenTeam session — surprising. Recommended convention if it ever matters: prefix with hostname (`rovodev-<host>-<uuid>`); out of scope today.
- **`OPENTEAM_FRONTEND_METADATA` audit env var.** Reserved for POST-3 (v2 of this plan). Not needed for v1 workspace-bucket use case.
- **Separate `frontend_id` and `frontend_session_id` fields.** v1 derives `frontend_id` from the prefix (deterministic via whitelist). If a future use case wants to attach a session WITHOUT prefix (internal sessions), add the explicit field then.
- **Multiple OpenTeam sessions per TUI workspace.** v1 is 1:1; `rm -rf .rovodev/` to reset; `rovodev --new-openteam-session` to rotate session id only.

---

## 9. Three-plan comparison and pick-one answer

### 9.1 Comparison table

| Concern | Claude (139L) | rovodev v2 (815L) | INTEGRATED-v2 (1057L, mine prior) | **INTEGRATED-v3 (this)** |
|---|---|---|---|---|
| `SessionStore` constructor signature | ❌ WRONG (inherited Cursor's `server_dir=` bug) | ✅ CORRECT (`runtime_root, *, resume_server=`) | ❌ WRONG (would TypeError at runtime) | ✅ CORRECT (adopted from rovodev v2) |
| Delimiter | `-` | `-` | `:` (over-engineered Windows encoding) | `-` (adopted from rovodev v2; POSIX+Windows safe + legacy back-compat) |
| Number of env vars | 2 (`SERVER_DIR` + `SESSION_ID`) | 2 | 4 (`FRONTEND_ID`+`SESSION_ID`+`METADATA`+`SERVER_DIR`) | 2 (adopted from rovodev v2; smaller protocol surface) |
| Executor changes | per-workspace synth server | **zero** (uses v5.3's session_root) | `_shared/session_resolver.py` + 1 line per executor | **zero** (adopted from rovodev v2; elegance dividend) |
| MCP path coverage | Phase 8 post-ship (deferred) | ✅ via shared `_frontend_session.py` helper | rewrite `build_session_context` | ✅ shared helper (adopted from rovodev v2) |
| Server-dir model | per-workspace synth | **shared** `server_rovodev_default/` | per-workspace synth | **shared** (adopted from rovodev v2; less FS clutter, React UI visibility) |
| WS init handshake forward-compat | ❌ | ❌ | ✅ optional frontend fields | ✅ **kept from my INTEGRATED-v2** (forward-compat for webui migration) |
| Per-entry-point server-dir rule documented | ❌ | partial (RovoDev only) | ✅ TUI/MCP/WS rules | ✅ **kept from my INTEGRATED-v2** (anticipates future MCP-direct) |
| Per-workspace `.rovodev/` persistence | ✅ | ✅ | ✅ | ✅ |
| `--new-(openteam-)session` flag | ✅ `--new-session` | ✅ `--new-openteam-session` (disambiguated) | ✅ `--new-session` | ✅ `--new-openteam-session` (adopted from rovodev v2; clearer name) |
| Prefix whitelist + CI preflight | ✅ | ✅ | ✅ | ✅ |
| `frontend_metadata` audit field | ✅ | reserved for v2 | ✅ | **reserved for POST-3** (rovodev v2 stance; v1 doesn't need it) |
| Separate `frontend_id` field | ✅ | derived from prefix | ✅ | **derived from prefix** (rovodev v2 stance; simpler v1) |
| Test count | 16 + CI preflight | 26 | 22 | 34 (largest; superset) |
| Self-audit / glossary / risks / comparison | minimal | thorough | thorough | thorough (merged) |
| Total LOC | 139 | 815 | 1057 | ~1050 (this plan) |

### 9.2 Pick-one answer

**If forced to pick exactly one of the three precursors (Claude / rovodev v2 / INTEGRATED-v2): pick rovodev v2.**

Reasons:
1. **Only one that has the correct `SessionStore` constructor signature.** My INTEGRATED-v2 would have `TypeError`d at runtime; Claude inherits the same bug. rovodev v2 verified the real signature against the source.
2. **The simplest protocol surface that works.** 2 env vars (not 4). Prefix-only frontend identity (no separate `frontend_id` field). Shared server (not per-workspace fragmentation). All choices that REDUCE complexity while preserving correctness.
3. **Zero executor changes** — the true elegance dividend of v5.3's session_root consumption. My INTEGRATED-v2 added a `_shared/session_resolver.py` helper that did unnecessary work.
4. **Shared `_frontend_session.py` helper for both `tool_cli` AND MCP.** DRY. My INTEGRATED-v2 duplicated the env-bridge logic in two places.
5. **Empirically grounded.** rovodev v2 cites file:line for every load-bearing claim and verified them in a session. My INTEGRATED-v2 had at least one citation wrong (`SessionStore` signature) and one off-by-one (line 113 vs 114 — minor).

**rovodev v2's two real gaps** (both filled by this INTEGRATED-v3):
- No WS init handshake extension for forward-compat React UI migration → v3 adds it (§4.5).
- Per-entry-point server-dir rule covers RovoDev only → v3 documents the full table (§3.3).

### 9.3 Strict ordering (without integration)

**rovodev v2 > INTEGRATED-v2 (mine prior) > Claude.**

With v3 in play, **this v3 strictly dominates all three** (correctness from rovodev v2 + forward-compat hooks from my v2 + concise framing from Claude). v3 is what each of us would have written if we'd cross-audited before publishing.

### 9.4 What v3 explicitly REJECTS from each

| Source | Rejected | Why |
|---|---|---|
| rovodev v2 | nothing of substance | architecturally correct end-to-end |
| INTEGRATED-v2 (mine) | `:` delimiter + Windows encoding | unnecessary; `-` works on both platforms and is legacy-back-compat |
| INTEGRATED-v2 (mine) | `frontend_metadata` env var | over-engineered for v1; reserved for POST-3 |
| INTEGRATED-v2 (mine) | separate `frontend_id` field | prefix-only is sufficient when whitelist is finite; saves ~10 LOC and one env var |
| INTEGRATED-v2 (mine) | `_shared/session_resolver.py` per-executor helper | unnecessary; v5.3 already does the routing in `allocate_tool_workspace` |
| INTEGRATED-v2 (mine) | per-workspace synth server `server_rovodev_<wsuuid>/` | over-engineered; shared `server_rovodev_default/` is cleaner |
| Claude | per-workspace synth server | same as above |
| Claude | inherited Cursor's `SessionStore(server_dir=)` bug | wrong API; would TypeError |

---

## 10. Self-audit + glossary

### 10.1 Self-audit (stress-tests against hacks)

| Question | Answer |
|---|---|
| Is anything in v3 ad-hoc or hacky? | The shared `mcp_server/_frontend_session.py` is the only "shared helper across packages" — a slight layering oddity (`tool_cli` imports from `mcp_server`). Acceptable because the alternative is duplicating ~60 LOC; and the dependency is one-way + leaf-level. |
| Does v3 commit OpenTeam to a specific RovoDev TUI version? | No. The env contract (`OPENTEAM_SERVER_DIR` + `OPENTEAM_SESSION_ID`) is the whole API surface. RovoDev can change everything else without breaking OpenTeam. |
| Does v3 commit RovoDev to a specific OpenTeam version? | Only that `attach_or_create_session` exists. If OpenTeam removes/renames it, RovoDev's subprocess will fall back to empty `session_context` with a WARNING — degraded but functional. |
| Could a malicious user attach to someone else's `rovodev-X` session? | Only if they already have filesystem read access to that user's `.rovodev/`. Same threat surface as any dotfile-based persistence (`.git`, `.cursor`, etc.). |
| What if `OPENTEAM_RUNTIME_DIR` differs between TUI and subprocess? | Subprocess inherits env unless explicitly overridden. TUI's `_find_runtime_root()` mirrors the subprocess's. Cross-helper regression test (§5.8) catches drift. |
| What if `OPENTEAM_FRONTEND_METADATA` is needed later? | Reserved (POST-3). Adding it is purely additive — ~3 lines in `resolve_frontend_session_context()`. |
| Could two `/task`s in the same TUI write to the same task workspace? | No — workspace allocator uses `uuid8` suffix; collision probability ~2^-32, recovered via 3-retry loop in allocator. |
| What if user runs OpenTeam WS server AND RovoDev TUI from the same workspace? | OpenTeam WS server uses its own `server_<unix>_<uuid>/` directory. RovoDev TUI uses `server_rovodev_default/`. No collision. Both visible in WS UI's `/sessions` list. |
| Will v3 break `rovodev-tui-graph-view-v4`? | No. Graph-view adds `ROVODEV_TUI_GRAPH_FD` env; v3 adds two MORE env vars. Both additive. The graph reader runs in the same subprocess that now also reads the session env vars. |
| Will v3 break `tool_workspace_allocation v5.3`? | No. v5.3 reads `session_context["session_root"]`; v3 populates that key when the env contract is satisfied. v5.3's three pending audit fixes (CRIT-3 / R5 DRY / v5.2 sharding) remain independent. |
| Why prefix-only and not separate `frontend_id` field (rovodev v2 stance)? | YAGNI for v1. With finite whitelist + `partition("-")`, the prefix IS deterministic provenance. Adding a separate field is ~10 LOC + new env var; the value lands in POST-3 when other concerns (audit, multi-tenant) actually require it. |
| Why one shared server and not per-workspace? | (a) Less FS clutter (one server dir per OpenTeam install, not one per workspace); (b) React UI's session list naturally aggregates all RovoDev sessions across workspaces; (c) cleanup is a single `rm -rf`; (d) `_atomic_write` mitigates concurrent-write race. If the cross-workspace race ever becomes an issue, switching to per-host sharding is a one-helper change with no protocol impact. |
| Why hyphen and not colon delimiter? | Hyphen is POSIX-safe AND Windows-safe AND back-compat with legacy `session-<unix>-<hex6>` ids. Colon is also POSIX-safe but Windows-reserved, requiring encoding. Hyphen's only theoretical downside (UUID4 contains hyphens) is moot because `partition("-")` extracts only the first segment, and the whitelist makes the parse deterministic. |
| Does the WS init handshake extension break today's React UI? | No — `frontend_id`/`frontend_session_id` are OPTIONAL; absent → defaults to `"ui"` + bare `sid`, which IS today's behavior. POST-1 will enable React UI to opt-in. |
| If a future frontend (say VS Code) wants to attach without going through subprocess/MCP/WS, what does v3 require of it? | Add its prefix to the whitelist (and CI preflight test); choose its entry point (subprocess via `OPENTEAM_*` env vars OR in-process via `attach_or_create_session`); follow the §3.3 server-dir resolution rule for its model. The protocol is documented and uniform. |

### 10.2 Glossary

| Term | Meaning |
|---|---|
| **External session ID** | A session ID supplied by a frontend (e.g., `rovodev-abc123`), as opposed to a server-minted internal ID (today's `session-<unix>-<hex6>`). |
| **Frontend prefix** | The substring before the first `-` in an external session ID. Must be in `_VALID_FRONTEND_PREFIXES`. |
| **`attach_or_create_session`** | NEW `SessionStore` method; idempotently maps an external session ID to a session dict. |
| **`OPENTEAM_SERVER_DIR`** | NEW env var; absolute path to `<runtime>/servers/<server>/`; tells the subprocess WHICH `SessionStore` to construct (its `runtime_root` is the grandparent; `resume_server` is the leaf name). |
| **`OPENTEAM_SESSION_ID`** | NEW env var; prefix-validated external session ID; tells the subprocess WHICH session to attach to. Both env vars must be set together. |
| **`resolve_frontend_session_context`** | NEW shared helper in `mcp_server/_frontend_session.py`; the single source of truth for env→session_context translation; called by both `tool_cli.run_cli` and `mcp_server.context.build_session_context`. |
| **`.rovodev/`** | Per-TUI-workspace persistence directory; contains `openteam_session_id` + `openteam_server_dir` files. Convention matches `.git/`, `.cursor/`, etc. |
| **`server_rovodev_default/`** | Shared OpenTeam server directory for ALL RovoDev TUI sessions. One per OpenTeam install, not per workspace. |
| **`--new-openteam-session`** | NEW TUI CLI flag; forces a fresh session ID even if `.rovodev/openteam_session_id` exists. One-shot (consumed on first `/task`). Disambiguated from any TUI-internal "session" concept. |
| **Path A / Path B** | Workspace-allocation terms from v5.3; A = standalone `<runtime>/tasks/<tool>/`; B = session-affiliated `<session_root>/tasks/<tool>_*/`. Both still supported; v3 makes Path B the default for RovoDev. |
| **Elegance dividend** | The property that no executor changes are needed: v5.3's `allocate_tool_workspace(base_dir=session_root/"tasks")` already does the right thing once `session_root` is populated. v3 just populates the key. |

---

## 11. Definition of Done

### OpenStartup repo (PR #1)
- [ ] `_VALID_FRONTEND_PREFIXES`, `_validate_external_id`, `attach_or_create_session`, `create_session(_explicit_id=)` landed in `session_store.py`
- [ ] `resolve_frontend_session_context()` landed in `mcp_server/_frontend_session.py`
- [ ] `tool_cli.py` line 114 replaced; `mcp_server/context.py` updated
- [ ] `manager_websocket_routes.py` WS init handshake accepts optional frontend fields
- [ ] All 8 `test_session_store_attach.py` (TIER-1) pass
- [ ] All 7 `test_frontend_session_resolver.py` (TIER-1) pass
- [ ] All 4 `test_tool_cli_env_bridge.py` (TIER-2) pass
- [ ] All 3 `test_ws_init_handshake_frontend_optional.py` (TIER-1) pass
- [ ] CI preflight `test_frontend_prefix_whitelist_immutable.py` passes
- [ ] `docs/MCP_INTEGRATION.md` documents the env-var protocol + WS init forward-compat

### cli-rovodev-tui repo (PR #2)
- [ ] `openteam_session.py` ships with `get_or_create_session`
- [ ] `slash_commands/openteam.py` wires `OPENTEAM_SERVER_DIR` + `OPENTEAM_SESSION_ID` on the subprocess env
- [ ] `app.py` accepts `--new-openteam-session`, threads `_force_new_openteam_session` through the handler
- [ ] All 6 `test_openteam_session.py` (TIER-1) pass
- [ ] Both `test_slash_openteam_env_propagation.py` (TIER-2) pass
- [ ] `docs/openteam-integration.md` documents `.rovodev/` persistence + `--new-openteam-session`

### Cross-package (PR #3)
- [ ] All 3 `test_runtime_root_helpers_agree.py` (TIER-1) pass
- [ ] All 8 §5.9 manual E2E smoke steps pass

### Documentation
- [ ] OpenStartup `README.md` (or `DEVELOPING.md`) mentions the unified-frontend protocol
- [ ] cli-rovodev-tui `README.md` mentions the new ergonomic (no manual setup; just launch)

---

## 12. Acknowledgements

- **RovoDev v2** (`openteam-unified-frontend-session-protocol-v2.md`): the correct `SessionStore(runtime_root, *, resume_server=)` signature, the hyphen-delimiter empirical argument, the shared-server design, the `_frontend_session.py` shared helper, the "zero executor changes" elegance, the `--new-openteam-session` disambiguated naming. **The base of this integration.**
- **My INTEGRATED-v2** (`openteam-unified-frontend-session-INTEGRATED-v2.md`): the WS init handshake extension (forward-compat for webui migration), the per-entry-point server-dir resolution rule, the comparison table structure.
- **Claude integrated** (`eager-roaming-clock.md`): concise problem framing; the original `OPENTEAM_SESSION_ID` env-var name that everyone converged on.
- **Empirical verification this session**: direct `grep`/`read` of `session_store.py:45-50` (SessionStore signature), `tool_cli.py:114` (empty context), `session_store.py:554-572` (atomic writes), `mcp_server/context.py:17-23` (today's MCP context build), `manager_websocket_routes.py:213-226` (today's WS slash session_context build).

---

## 13. Pick-one answer (one-liner)

**Pick rovodev v2 of the three precursors.** It's the only one with the correct `SessionStore` API signature, the simplest protocol surface (2 env vars, prefix-only, shared server, zero executor changes), and a verified empirical foundation. v3 strictly dominates it by adding two forward-compat hooks (WS init extension + per-entry-point server-dir rule) without sacrificing anything.

---

**End of plan. Saved at:** `CoreProjects/OpenStartup/_dev/_plan/openteam_rovodev_integration/openteam-unified-frontend-session-INTEGRATED-v3.md`
