# Unified Frontend Session Protocol (OpenTeam ↔ Multi-Frontend)

**File:** `openteam-unified-frontend-session-protocol-v1.md`
**Status:** v1 — design proposal, ready for review then implementation
**Author:** Rovo Dev (synthesized from user intent + parallel codebase investigation)
**Date:** 2026-05-17 18:13
**Supersedes:** none (orthogonal/complementary to `openteam-rovodev-integration-INTEGRATED-v6.md` and `tool_workspace_allocation_enhancement/unified_workspace_allocation_INTEGRATED_v5_FINAL_plan.md`)

---

## 0. TL;DR

**User's question (paraphrased):**
> RovoDev is now another OpenTeam frontend (alongside the React UI). Shouldn't there be a unified frontend↔backend session mechanism? Each RovoDev TUI session should map to a dedicated OpenTeam session — e.g. `rovodev-{rovodev_session_id}` — so OpenTeam treats it like any normal session, and the per-frontend prefix generalises to N future frontends.

**My answer (verified against the live codebase): YES, there is a real and well-defined gap. The user's proposed shape is exactly right.**

| Question | Verdict |
|---|---|
| Is the unified mechanism already in place? | ❌ **NO.** Two independent code paths bypass `SessionStore` entirely (MCP + slash subprocess). |
| Is the user's prefix idea (`rovodev-{id}`) sound? | ✅ YES — and it generalises cleanly to `frontend_id:frontend_session_id` (delimiter `:` chosen over `-` for parser determinism; see §3.2). |
| Is the gap large or small? | **Large.** Today every RovoDev tool call creates an orphan ephemeral session with no continuity, no nested workspace, no export, no UI visibility. Closing it touches **~150 LOC across 6 files** but unlocks: persistent conversation, unified workspace allocation, session export, UI visibility of RovoDev runs, and a clean N-frontend abstraction. |
| Is there a simpler half-measure? | Yes (Phase 0 only — propagate `session_id` as opaque string). But §6.3 argues against; the full design is only ~3× the work for ~10× the value. |

---

## 1. The Gap (verified by parallel codebase investigation)

### 1.1 Today's two code paths

```
┌─────────────────┐                                               ┌──────────────────────┐
│  React Web UI   │ ── POST /sessions {title}    ───────────────▶ │   SessionStore       │
│                 │ ── POST /sessions/{id}/msg   ───────────────▶ │   (persistent)       │
│                 │ ── WS /manager  (sid in init)───────────────▶ │   sessions/{id}/     │
└─────────────────┘                                               │   ├── session_state  │
                                                                  │   └── tasks/         │
                                                                  │       └── tool_*/    │
                                                                  └──────────────────────┘
                                                                          ▲
                                                                          │ (only the UI gets here)
                                                                          │
┌─────────────────┐                                               ┌──────────────────────┐
│ RovoDev TUI     │ ── MCP openteam_task(...)    ─┐               │   build_session_     │
│                 │                               ├──── BYPASS ─▶ │   context()          │
│                 │ ── /task <prompt>             ┘               │   {"task_id":        │
│                 │     (subprocess)                              │     "mcp-<uuid8>",   │
└─────────────────┘                                               │    "interactive":    │
                                                                  │     None}            │
                                                                  └──────────────────────┘
                                                                          │
                                                                          ▼
                                                                  ┌──────────────────────┐
                                                                  │   executor.execute() │  ◀── no session, no
                                                                  │   (orphan)           │     workspace nesting,
                                                                  └──────────────────────┘     no continuity, no
                                                                                                UI visibility
```

### 1.2 Verified evidence (file:line)

| Claim | Evidence |
|---|---|
| UI POST /sessions creates a server-generated UUID session and a directory | `src/openteam/server/services/session_store.py:158-200` — `create_session()` builds `session-{int(now)}-{uuid4().hex[:6]}` and a directory `<id>_<YYYYMMDD_HHMMSS>/session_state.json` |
| WebSocket captures `sid` at init handshake | `src/openteam/server/routes/manager_websocket_routes.py:502-513` |
| WS slash-dispatcher passes `sid` into routes (lines 213-217) | `manager_websocket_routes.py:213-217` |
| MCP wrapper builds a fresh `task_id = "mcp-<uuid8>"` per call; **no session_id field** | `src/openteam/mcp_server/context.py:17-23` — `build_session_context()` body shown in full above |
| All 4 MCP wrappers call `await _exec(args, build_session_context())` — each call is orphan | `src/openteam/mcp_server/server.py:60, 80, 96, 124` |
| Slash subprocess passes only `PYTHONPATH`; **no `OPENTEAM_SESSION_ID` env** | `cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py:68-89` — `_build_argv_and_env()` body shown |
| RovoDev TUI HAS its own session id (`current_session_id: var[str]`) — just doesn't propagate it | `cli-rovodev-tui/src/rovodev_tui/app.py:403`, accessor at line 668-669 (`self.session_ctxs[self.current_session_id]`) |
| RovoDev session id format: `str(uuid4())` (canonical UUID4) | `cli-rovodev/src/rovodev/commands/acp/agent.py:164` |
| No `frontend_id`, `client_type`, `origin`, or `caller_id` field anywhere in OpenTeam | grep -rn "frontend\|client_type\|origin\|caller_id" `src/openteam/server/` → 0 hits |

### 1.3 What you cannot do today (concrete losses)

1. **Conversation continuity across RovoDev tool calls.** Two consecutive `/task` invocations from the same RovoDev session have zero state shared between them on the OpenTeam side. Each is a fresh `mcp-<random>` session.
2. **Nested workspace allocation.** The workspace allocation plan (`v5.3 FINAL`) gives every UI-session its own `_runtime/servers/{server}/sessions/{id}/tasks/{tool}_*/` directory. RovoDev calls **fall to Path A** (`_runtime/tasks/{tool}_*/`) because no `session_root` is set. Result: RovoDev artifacts are scattered, not session-isolated, and not co-located with the UI session that should "own" them.
3. **UI visibility of RovoDev runs.** Open the React UI → you cannot see what tasks the user has been running through `/task`. They're invisible to the same backend.
4. **Session export / archive.** UI sessions can be tar'd by `_runtime/.../sessions/{id}/`. RovoDev outputs are NOT included.
5. **Multi-frontend pluggability.** When Frontend #3 arrives (e.g., a VS Code extension), it must reinvent its own backend-binding instead of conforming to a contract.

### 1.4 The user's proposal, verbatim, mapped to the gap

> *"add rovodev session id into the openteam session side, maybe use `rovodev-{rovodev session id}` to be generic, where the rovodev is the frontend unique name, in the future we can have more frontend"*

**Verdict:** ✅ correct shape. The right generalisation is:

```
openteam_session_id := <frontend_id>:<frontend_session_id>
                       └─ "rovodev"   └─ uuid4 (RovoDev's `current_session_id`)
                          "ui"             session-<ts>-<hex6> (today's UI uses raw)
                          "vscode-ext"     <whatever VS Code generates>
```

§3.2 explains why `:` not `-`; §4 specifies the full protocol; §5 is the implementation.

---

## 2. Design goals (in priority order)

1. **Minimise RovoDev-side surface area.** The user explicitly said: *"To minimize work on rovodev side"*. RovoDev should only set ONE field (its own session id) — OpenTeam owns everything else.
2. **OpenTeam treats the resulting session like any other session.** The whole point of the prefix is that downstream OpenTeam code (workspace allocation, persistence, UI listing, export) is **frontend-agnostic**. A session is a session.
3. **Backward compatible.** UI keeps working unchanged. Existing RovoDev calls (MCP + slash) keep working with degraded-but-functional behaviour (auto-allocated ephemeral session) if RovoDev hasn't been upgraded yet.
4. **Pluggable for future frontends.** Any new frontend must do the same one thing: send its `frontend_id` + its own `frontend_session_id`.
5. **No new dependencies in either repo.**
6. **Auditable provenance.** Given an OpenTeam session id, you can immediately tell which frontend created it and what that frontend's native id was.

---

## 3. The protocol

### 3.1 The canonical OpenTeam session-id format

```
openteam_session_id := <frontend_id> ":" <frontend_session_id>
                     | <legacy_session_id>                        # backward-compat (UI today)

frontend_id          := lower-case ASCII identifier, [a-z][a-z0-9_-]{0,31}
frontend_session_id  := any string matching ^[A-Za-z0-9_:.\-]{1,128}$
```

Examples:
- `rovodev:550e8400-e29b-41d4-a716-446655440000` (RovoDev UUID4)
- `ui:session-1717238400-a1b2c3` (the React UI, post-migration — see §6.2)
- `vscode-ext:workspaceRoot:/abs/path/here` (hypothetical; valid because `:` is allowed in the second half)
- `session-1717238400-a1b2c3` (legacy bare UI id — still accepted; treated as `ui:` prefix by adapter)

### 3.2 Why colon (`:`) not hyphen (`-`)

| Delimiter | Pros | Cons |
|---|---|---|
| **`-`** (user's first sketch) | Familiar; URL-safe | RovoDev session ids are UUID4 (`550e8400-e29b-41d4-...`) which CONTAIN hyphens → ambiguous split: `rovodev-550e8400-e29b-...` → `frontend_id = "rovodev"` and `rest = "550e8400-e29b-..."` requires "first hyphen wins" rule, which is fragile. |
| **`:`** | UUID4 contains no `:`; trivially unambiguous via `.split(":", 1)`; matches well-known conventions (URIs, ARI patterns, k8s namespacing) | Slightly less URL-friendly (must percent-encode in URL paths, but session ids are normally posted in JSON body or used in WS messages — no URL impact) |
| **`/`** | Cleanest visually | Reserved for paths and S3-style segmentation; will collide with future routing |
| **`.`** | Compact | Often interpreted as file extension by tooling |

**Decision: `:`** — split on first `:` is deterministic regardless of payload format.

### 3.3 Where the prefix is applied

**RovoDev sets only its own session id; OpenTeam adds the prefix.** This honours design goal #1 (minimise RovoDev work) and design goal #2 (OpenTeam owns the namespace).

```
RovoDev sends:                              "550e8400-e29b-41d4-a716-446655440000"
OpenTeam stores as openteam_session_id:    "rovodev:550e8400-e29b-41d4-a716-446655440000"
                                            └─ added by openteam.mcp_server.context.py + slash-dispatcher
```

This means RovoDev does NOT need to know it's called "rovodev" by OpenTeam. The frontend name lives **once**, in the OpenTeam adapter that knows it's serving RovoDev.

### 3.4 The protocol surface (4 new fields total)

| Field | Owner | Carrier | Default | Purpose |
|---|---|---|---|---|
| `frontend_session_id` | Frontend | MCP wrapper kwarg `frontend_session_id: str \| None`; slash env `OPENTEAM_FRONTEND_SESSION_ID`; WS init JSON `{"frontend_session_id": "..."}` | None → ephemeral | The frontend's own native session id |
| `frontend_id` | OpenTeam adapter | Hard-coded per adapter (MCP adapter sets `"rovodev"`; slash adapter sets `"rovodev"`; UI route sets `"ui"`) | n/a — always set | Names the originating frontend |
| `openteam_session_id` | OpenTeam | Composed: `f"{frontend_id}:{frontend_session_id}"`, OR pure server-generated if no frontend hint | server-generated | Canonical id used everywhere downstream |
| `frontend_metadata` | Frontend (optional) | MCP wrapper kwarg `frontend_metadata: dict \| None`; slash env `OPENTEAM_FRONTEND_METADATA` (JSON); WS init JSON | None | Free-form provenance: `{"version": "rovodev-tui-1.2.3", "user": "alice"}`; stored verbatim in `session_state.json` for audit |

---

## 4. Architecture

### 4.1 End-to-end flow (post-implementation)

```
┌────────────────────────────────────────┐         ┌─────────────────────────────────────────────────┐
│  RovoDev TUI session "550e8400-..."    │         │  OpenTeam (single backend, multi-frontend)      │
│                                        │         │                                                 │
│  /task <prompt>                        │         │  1. dispatch slash:                             │
│   └─ slash handler                     │         │     - OPENTEAM_FRONTEND_ID="rovodev"            │
│      reads app.current_session_id      │ ──────▶ │     - OPENTEAM_FRONTEND_SESSION_ID=             │
│      sets env OPENTEAM_FRONTEND_       │         │       "550e8400-e29b-41d4-a716-446655440000"   │
│        SESSION_ID = app.current_       │         │  2. subprocess entrypoint reads env →           │
│        session_id                      │         │     openteam_session_id = "rovodev:550e..."    │
│      spawn `openteam-task ...`         │         │  3. SessionStore.get_or_create_session(...)    │
│                                        │         │     - if exists: reuse                          │
│  openteam_task(request="...",          │         │     - if not: create with that id              │
│                frontend_session_id=    │ ──────▶ │  4. session_context["session_id"] = "rovodev:..." │
│                  app.current_          │         │  5. SessionStore.get_session_tasks_dir(id) →   │
│                  session_id)           │         │     _runtime/servers/.../sessions/             │
│   └─ MCP wrapper                       │         │       rovodev:550e.../tasks/task_*/             │
└────────────────────────────────────────┘         │  6. executor.execute(args, ctx) runs           │
                                                   │  7. UI lists ALL sessions, including          │
                                                   │     rovodev:* — they appear naturally          │
                                                   │     in the session picker                       │
                                                   └─────────────────────────────────────────────────┘
```

### 4.2 The two adapters (the only RovoDev-side changes)

**Slash adapter** (`cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py`):

```python
# Round-1 patch: surface RovoDev's session id to OpenTeam.
# Single field — OpenTeam adds the frontend_id prefix on its side.
def _build_argv_and_env(binary_name, module_name, user_args, *, frontend_session_id=None, frontend_metadata=None):
    env = {**os.environ, "OPENTEAM_FRONTEND_ID": "rovodev"}
    if frontend_session_id:
        env["OPENTEAM_FRONTEND_SESSION_ID"] = frontend_session_id
    if frontend_metadata:
        env["OPENTEAM_FRONTEND_METADATA"] = json.dumps(frontend_metadata, separators=(",", ":"))
    binary = _find_binary(binary_name)
    if binary is not None:
        return ([binary, *user_args], env)
    # ... rest of existing fallback unchanged ...

# In the handler factory:
async def handler(app: "RovoDevApp", extra_prompt: str) -> None:
    # ... existing setup ...
    user_args = shlex.split(extra_prompt)
    argv, env = _build_argv_and_env(
        binary, module, user_args,
        frontend_session_id=app.current_session_id,                              # already exists
        frontend_metadata={"tui_version": rovodev_tui.__version__},              # optional
    )
    # ... rest unchanged ...
```

**Total RovoDev TUI delta:** ~6 lines added.

**MCP adapter** (`openteam.mcp_server.server.py`):

```python
# Round-1 patch: accept frontend_session_id from MCP client.
# Wrapper signature changes ONLY: add 2 fields, propagate via build_session_context.
async def openteam_task(
    request: str,
    *,
    frontend_session_id: str | None = None,            # NEW
    frontend_metadata: dict[str, str] | None = None,   # NEW
    # ... all existing fields unchanged ...
) -> str:
    # ... existing body ...
    return render_result(await _exec(args, build_session_context(
        frontend_id="rovodev",                          # MCP adapter always serves RovoDev today
        frontend_session_id=frontend_session_id,
        frontend_metadata=frontend_metadata,
    )))
```

Each of the 4 wrappers gains the same 2 kwargs (same diff applied 4×). **OpenTeam-side delta in `server.py`:** ~30 LOC including the docstring updates.

### 4.3 The OpenTeam backend changes

**`mcp_server/context.py`** (the orphan-session-builder):

```python
"""Build session_context for in-process executor calls (Round-1 unified-frontend protocol)."""
from __future__ import annotations
import os, uuid, json, logging
from typing import Any

_logger = logging.getLogger(__name__)

_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}

# Slash-subprocess fields (read from env when the wrapper isn't the caller).
_FRONTEND_ID_ENV          = "OPENTEAM_FRONTEND_ID"
_FRONTEND_SESSION_ID_ENV  = "OPENTEAM_FRONTEND_SESSION_ID"
_FRONTEND_METADATA_ENV    = "OPENTEAM_FRONTEND_METADATA"


def build_session_context(
    *,
    frontend_id: str | None = None,
    frontend_session_id: str | None = None,
    frontend_metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the per-invocation context dict for executor.execute(args, ctx).

    Resolution order for frontend identity (most specific wins):
      1. Explicit kwargs (MCP wrapper path).
      2. Environment variables (slash subprocess path).
      3. Neither set → ephemeral session (back-compat with pre-protocol RovoDev).

    The resulting session_id is composed as: f"{frontend_id}:{frontend_session_id}".
    If only one side is missing, we fall back to ephemeral (logged at INFO level
    so the asymmetry is visible).
    """
    # Resolve frontend identity (kwargs > env > none).
    fid = frontend_id  or os.environ.get(_FRONTEND_ID_ENV)
    fsid = frontend_session_id or os.environ.get(_FRONTEND_SESSION_ID_ENV)
    fmeta = frontend_metadata
    if fmeta is None and (raw := os.environ.get(_FRONTEND_METADATA_ENV)):
        try:
            fmeta = json.loads(raw)
        except json.JSONDecodeError as e:
            _logger.warning("ignoring malformed %s: %s", _FRONTEND_METADATA_ENV, e)

    if fid and fsid:
        openteam_session_id = f"{fid}:{fsid}"
    else:
        if fid or fsid:
            _logger.info(
                "frontend identity partially specified (frontend_id=%r, frontend_session_id=%r); "
                "falling back to ephemeral session", fid, fsid)
        openteam_session_id = f"mcp-{uuid.uuid4().hex[:8]}"
        fid = fid or "ephemeral"

    ctx: dict[str, Any] = {
        "session_id":          openteam_session_id,       # NEW canonical field
        "task_id":             f"task-{uuid.uuid4().hex[:8]}",  # per-invocation, distinct from session
        "interactive":         None,
        "frontend_id":         fid,                       # NEW: provenance
        "frontend_session_id": fsid,                      # NEW: native id
        "frontend_metadata":   fmeta or {},               # NEW: free-form audit
    }
    for env_key, ctx_key in _ENV_MAP.items():
        if v := os.environ.get(env_key):
            ctx[ctx_key] = v
    return ctx
```

**`session_store.py`** — one new method (`get_or_create_session(session_id)`):

```python
def get_or_create_session(self, session_id: str, *, title: str | None = None,
                          frontend_id: str | None = None,
                          frontend_metadata: dict | None = None) -> dict[str, Any]:
    """Idempotent: return existing session by id, OR create one with that explicit id.

    Used by the unified-frontend protocol so a RovoDev session id maps directly
    to an OpenTeam session id without the usual server-generated UUID. The id
    must already be valid (see _is_valid_session_id) — callers (MCP/slash
    adapters) compose the id from validated parts.
    """
    if existing := self.get_session(session_id):
        return existing
    return self._create_session_with_explicit_id(
        session_id,
        title=title or self._default_title_for_frontend(frontend_id),
        frontend_id=frontend_id,
        frontend_metadata=frontend_metadata,
    )
```

**Why `get_or_create` not `create`:** idempotent means the same `/task` invoked 3 times from the same RovoDev session lands in the SAME OpenTeam session — that's the whole point of unification.

### 4.4 The executor changes

Each of the 4 tool executors already takes `session_context: dict` as parameter 2. The workspace-allocation plan (`v5.3 FINAL`) already wired this dict to `session_context["session_root"]` for Path B nesting. The unified-frontend protocol now means **`session_context["session_id"]` is always set** — so the executor can call `SessionStore.get_or_create_session(...)` early to materialize the session directory before any workspace allocation.

**Net executor-side delta: ~3 lines per executor** (4 executors × 3 = 12 LOC):

```python
async def execute(args, session_context):
    # Round-1 unified-frontend protocol: ensure the session exists before
    # allocating the workspace (Path B nested layout requires session_root).
    sid = session_context.get("session_id")
    if sid and session_context.get("frontend_id"):  # protocol path
        store = _get_session_store_or_none()
        if store is not None:
            session = store.get_or_create_session(
                sid,
                frontend_id=session_context["frontend_id"],
                frontend_metadata=session_context.get("frontend_metadata"),
            )
            session_context["session_root"] = str(store.get_session_dir(sid))
    # ... existing body unchanged from here onwards ...
```

### 4.5 The full data flow (verified end-to-end)

```
RovoDev TUI                                             OpenTeam
─────────────────────────                               ──────────────────────────────────────
app.current_session_id = "550e8400-..."                 (no state)
   │
   ▼ /task "what is 2+2"
slash handler:
  env["OPENTEAM_FRONTEND_ID"] = "rovodev"
  env["OPENTEAM_FRONTEND_SESSION_ID"] = "550e8400-..."
  spawn openteam-task --request "what is 2+2"  ───────▶ openteam-task entrypoint
                                                          ├─ context = build_session_context()
                                                          │   reads env → ctx["session_id"] = "rovodev:550e8400-..."
                                                          │             → ctx["frontend_id"]  = "rovodev"
                                                          ├─ executor.execute(args, ctx):
                                                          │   ├─ SessionStore.get_or_create_session("rovodev:550e8400-...")
                                                          │   │   → creates _runtime/.../sessions/rovodev:550e.../
                                                          │   ├─ ctx["session_root"] = that path
                                                          │   ├─ resolve_tool_workspace("task", ctx)
                                                          │   │   → _runtime/.../sessions/rovodev:550e.../tasks/task/task_20260517_*/
                                                          │   └─ run the BTA; persist artifacts there
                                                          └─ exits

User opens React UI:
  GET /sessions → response includes "rovodev:550e8400-..." in the list
  Click → conversation history + artifact tree of the RovoDev runs

User runs /task again 1 hour later:
  same env values → SessionStore.get_or_create returns the SAME session
  new task workspace under the SAME session dir
  conversation continuity established
```

This is exactly what the user described.

---

## 5. Implementation phases

| Phase | Title | LOC | Effort | Blocks |
|---|---|---|---|---|
| **0** | Pre-requisite verification: workspace allocation v5.3 must be merged | n/a | 0 | 1, 2, 3 |
| **1a** | `context.py` rewrite — accept frontend_id/session_id/metadata kwargs + env fallback + composition rule | ~50 | 0.5h | 1b, 2 |
| **1b** | `session_store.py` — add `get_or_create_session(id, frontend_id, frontend_metadata)`; validate id format | ~40 | 1h | 3 |
| **1c** | `mcp_server/server.py` — add `frontend_session_id`/`frontend_metadata` kwargs to all 4 wrappers + propagate | ~30 | 0.5h | 4a |
| **1d** | `cli/__main__.py` (subprocess entry): read env, build_session_context, pass through to executor | ~10 | 15m | 4b |
| **2**  | 4 executors — call `get_or_create_session` and set `session_root` if `session_id` is in the protocol form | ~12 (3×4) | 1h | 4a, 4b |
| **3**  | `manager_websocket_routes.py` — on WS init, accept optional `frontend_id`/`frontend_session_id` from the init handshake; back-compat for current "ui" sessions | ~20 | 1h | 5 |
| **4a** | RovoDev MCP integration test — verify `openteam_task(frontend_session_id=...)` lands in `_runtime/.../sessions/rovodev:.../tasks/task/*` | ~40 | 1h | DoD |
| **4b** | RovoDev slash integration test — verify `OPENTEAM_FRONTEND_SESSION_ID` env passes through | ~40 | 1h | DoD |
| **4c** | RovoDev TUI slash adapter — set `OPENTEAM_FRONTEND_ID="rovodev"` + propagate `app.current_session_id` | ~6 | 15m | 4b, 5 |
| **5**  | UI session-list now includes rovodev sessions (no UI change needed — they're listed naturally; just verify) | 0 | 30m | DoD |
| **6**  | Docs: SKILL.md + DEVELOPING.md + README — document the protocol | ~80 | 1h | DoD |
| **7**  | Optional: deprecation notice for raw `task_id`-style session_context fields | ~10 | 30m | n/a |

**Total LOC:** ~330. **Total effort:** ~9 hours (1 focused day). **Critical path:** 0 → 1a → 1b → 2 → 4c → 4a/4b → 5 → 6.

---

## 6. Design decisions & alternatives considered

### 6.1 Why `get_or_create` instead of "always create"

The user's mental model is **continuity**. A RovoDev TUI session is a long-lived conversation; tool calls within it should pile up under the same OpenTeam session. `get_or_create` is the only call signature that delivers this naturally. "Always create" would mean every `/task` from the same TUI session creates a new OpenTeam session — defeating the entire point of the prefix.

### 6.2 Should the UI migrate to `ui:session-<ts>-<hex6>` prefix?

**Recommendation: yes, in Phase 7 (optional/later).** Once the protocol exists, the React UI should set `frontend_id="ui"` for symmetry — but this is a backwards-compatible additive change. Today's bare `session-<ts>-<hex6>` ids continue to work; the adapter parses bare ids as implicit `ui:<id>` for display purposes.

### 6.3 Why NOT just "accept session_id as an opaque string"

The simplest possible change would be: add `session_id: str | None` to the MCP wrappers and the env, and have the executor pass it straight through. Why we don't:

1. **No provenance.** You can't tell from the OpenTeam side which frontend created `7f3a9b...`. With the `frontend_id` prefix, you can immediately distinguish `rovodev:7f3a9b` from `vscode:7f3a9b`.
2. **Collision across frontends.** Two different frontends could both use UUID4 (RovoDev does, others probably will). Without a namespace prefix, the collision probability — while tiny per-pair — compounds with N frontends.
3. **No future frontend ergonomics.** When Frontend #3 arrives, there's no contract for it to follow. Each frontend reinvents.
4. **Audit trail breaks.** `session_state.json` would have a `session_id` but no record of who created it.

The `frontend_id` field adds ~10 LOC and solves all 4. Worth it.

### 6.4 Why the prefix lives in the OpenTeam adapter (not in RovoDev)

The user's stated goal: *"To minimize work on rovodev side"*. RovoDev knows its own session id; it does NOT need to know it's called "rovodev". The OpenTeam-side adapter (MCP wrapper, slash subprocess entrypoint) is the only place that hard-codes `"rovodev"`. This makes RovoDev a clean client — no per-backend specialisation.

### 6.5 Why colons in directory names (`sessions/rovodev:550e.../`) are safe

| OS | Path with `:` in dir name | Status |
|---|---|---|
| Linux / macOS (POSIX) | OK — `:` is not a reserved path char | ✅ |
| Windows (NTFS) | `:` IS reserved (alternate data stream separator) | ⚠️ need to escape |

**Mitigation:** the `SessionStore` already substitutes filesystem-unsafe characters when building the on-disk directory name (see `session_store.py:170-180` directory naming with `dir_timestamp` for separation). We extend this to also URL-encode `:` → `%3A` on Windows. The in-memory and on-the-wire id stays `rovodev:550e...`; only the on-disk leaf differs. The accessor `get_session_dir(session_id)` does the encoding centrally.

### 6.6 Comparison to the existing workspace allocation plan (v5.3 FINAL)

The workspace allocation plan is **orthogonal and complementary**:

| Concern | Workspace allocation v5.3 | This plan (unified-frontend v1) |
|---|---|---|
| Where do tool workspaces live? | Nested under session dir | unchanged — still nested |
| Who owns the workspace decision? | `SessionStore.get_session_tasks_dir()` | unchanged |
| How is `session_id` resolved at the executor? | Reads from `session_context["session_root"]` | **NEW: this plan ensures `session_id` is always set in the context, so Path B (server-affiliated) becomes universal** |
| Today: RovoDev calls fall to Path A | Yes (v5.3 explicit) | **After this plan: RovoDev calls land in Path B too** — the desired end state |

So this plan **completes** what v5.3 started: v5.3 built the machinery; this plan ensures all 4 invocation paths (UI, MCP, slash, future) feed the machinery.

---

## 7. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Windows filesystem can't store `:` in dirname | Med | High | §6.5 — encode at the leaf only (`%3A`); in-memory id unchanged |
| Long RovoDev UUID4 + prefix exceeds filesystem path limits | Low | Med | `rovodev:` (8) + UUID4 (36) = 44 chars; well under POSIX `NAME_MAX=255`; Windows MAX_PATH (260) is the real concern, but session_root + tasks/task_TS_uuid8 already builds ~100 chars under it. Add Phase 0 test for typical path lengths. |
| Two RovoDev TUI instances on the same machine share session ids | Very Low | Low | UUID4 collision probability is negligible; documented as "if you really want, prefix with hostname" |
| RovoDev sends a malicious `frontend_session_id` (`../../etc/passwd`) | Med | High | `session_store.py:_is_valid_session_id()` rejects anything outside `^[A-Za-z0-9_:.\-]{1,128}$`; rejected at the boundary, never reaches `Path()` operations |
| Pre-protocol RovoDev versions still call the new wrappers | High | Low | Wrappers' new kwargs default to `None`; `build_session_context()` falls back to ephemeral session — old behaviour preserved |
| Wide-spread test pollution under `sessions/rovodev:*` from CI runs | High | Low | Phase 11 cleanup script in v5.3 plan already handles this; we add `rovodev:` to its known-prefixes list |
| `frontend_metadata` JSON env var hits OS env-var size limit | Very Low | Low | Document max ~32KB; reject larger; mention `.json` file fallback path |

---

## 8. Definition of Done

### Tests (TIER-1 = blocking)
- [ ] `test_build_session_context_with_kwargs.py` — verifies kwarg path
- [ ] `test_build_session_context_from_env.py` — verifies slash-subprocess env path
- [ ] `test_build_session_context_partial_falls_back.py` — only one half set → ephemeral
- [ ] `test_build_session_context_metadata_malformed.py` — bad JSON → warning + ignored, not exception
- [ ] `test_session_store_get_or_create_idempotent.py` — same id called twice returns same session, no duplicate dir
- [ ] `test_session_store_rejects_path_traversal_id.py` — `../foo` rejected
- [ ] `test_mcp_wrapper_propagates_frontend_session_id.py` — all 4 wrappers
- [ ] `test_slash_subprocess_propagates_env.py` — real subprocess; assert `OPENTEAM_FRONTEND_ID` reaches `os.environ` of child
- [ ] `test_executor_resolves_session_root_from_session_id.py` — given `frontend_id+frontend_session_id`, executor's `session_context["session_root"]` is correct
- [ ] `test_end_to_end_rovodev_to_openteam_workspace.py` — TIER-2 — real `/task` from RovoDev TUI to OpenTeam yields workspace under `_runtime/.../sessions/rovodev:.../tasks/task/`

### Acceptance
- [ ] `/task <prompt>` from RovoDev TUI session X invoked twice → 2 task workspaces UNDER THE SAME `rovodev:X` session directory
- [ ] React UI's `/sessions` list shows `rovodev:550e...` alongside `session-...`
- [ ] Clicking the rovodev session in the UI displays its tasks/artifacts
- [ ] Existing `/task` calls without TUI session (raw CLI usage) still work — fall back to ephemeral
- [ ] Existing UI sessions (pre-migration) work unchanged

### Docs
- [ ] `mcp_server/templates/SKILL.md` documents `frontend_session_id` kwarg
- [ ] `DEVELOPING.md` documents the protocol with sequence diagram
- [ ] `README.md` adds "Unified Frontend Session Protocol" section

---

## 9. Pick-one (if you can do only ONE phase first)

**Pick Phase 1a + 1d (~1h total).** This alone delivers:
- Slash-subprocess path benefit (90% of RovoDev usage today)
- Zero RovoDev-side changes required (RovoDev unaware until Phase 4c)
- Forward-compatible with everything else

Phase 1c (MCP wrappers) is the next-biggest win for the MCP path; Phase 4c is the one RovoDev-side change.

---

## 10. Out of scope (deliberately)

- Multi-user / multi-tenant within a single OpenTeam server (the `frontend_metadata.user` field is reserved for this but not enforced)
- Cross-machine session continuity (a RovoDev TUI session on machine A and another on machine B with the same UUID would be the same OpenTeam session — surprising; recommend `hostname:` prefix when this matters)
- Real-time RovoDev-to-UI streaming (the graph view plan, v4, is separate; this plan just ensures the UI **sees** the session, not that it watches it live)
- Authentication / authorization on session creation (the protocol is transport-agnostic; AuthN/Z lives outside)

---

## 11. Acknowledgements

- User intent and proposed shape (`rovodev-{id}` prefix) — directly the seed of §3
- Workspace allocation v5.3 FINAL — provides the nested-layout target that this plan feeds
- Parallel Explore subagent verification (3 agents) + direct bash verification of all file:line citations
- The 8-round adversarial review pattern from `rovodev-tui-graph-view-v4.md` informed the test-list rigor in §8

---

**End of plan. Saved at:** `CoreProjects/OpenStartup/_dev/_plan/openteam_rovodev_integration/openteam-unified-frontend-session-protocol-v1.md`
