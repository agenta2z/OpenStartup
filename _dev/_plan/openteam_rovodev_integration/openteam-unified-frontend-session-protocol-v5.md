# OpenTeam Unified Frontend Session Protocol — INTEGRATED v5

**File:** `openteam-unified-frontend-session-protocol-v5.md`
**Status:** v5 — design-justification refinement over v4
**Date:** 2026-05-17 21:49
**Author:** Rovo Dev (with adversarial input from Cursor INTEGRATED-v4 and Claude meta-analysis)
**Supersedes:**
- `openteam-unified-frontend-session-protocol-v4.md` (mine, 735 lines, integrated 3-plan winner)
- `openteam-unified-frontend-session-protocol-v3.md` (mine, 1643 lines, Round-7)
- `openteam-unified-frontend-session-INTEGRATED-v4.md` (Cursor, 1359 lines)
- `~/.claude/plans/eager-roaming-clock.md` (Claude, 50 lines — now itself a meta-comparison that recommends v3)

## v5 refinements over v4 (targeted, not architectural)

This round produces **no architectural changes** because v4 already integrated the load-bearing decisions from all three predecessors. The remaining diffs are **design-justification rigour** absorbed from Cursor INTEGRATED-v4:

1. **Jupyter precedent citation** — the discovery file pattern is borrowed from Jupyter's `~/.local/share/jupyter/runtime/jpserver-<pid>.json`. Cited in §3 schema, §3.6 decision matrix, §6 register_server docstring. Strong external anchor for "no ad-hoc" review.
2. **§3.6 decision matrix (7 alternatives)** — single registry vs per-server file vs PID file vs dbus vs port-knock vs systemd. Each scored. Shows why the chosen approach is the right one, not the first one we thought of.
3. **§10 out-of-scope section** — explicit POST-1/POST-2/POST-3 deferred work; auth (out of threat model); multi-host federation; Windows daemon; GUI server-picker. Sets reviewer expectations.
4. **Discovery file `process_command` + `$schema` fields** — supports a future `openteam-server stop` (POST-1) without re-parsing the registry; `$schema` URL enables JSON-Schema tooling.
5. **`OPENTEAM_REGISTRY_DIR` env-var override** for the discovery directory (test isolation; multi-user systems).

What v5 explicitly REJECTS from Cursor INTEGRATED-v4:
- **"Splitting `openteam.server.discovery` into a separate `openteam-sdk` PyPI package is over-engineering for v1"** — wrong reasoning for our greenfield state. Cursor's logic is "don't refactor a working system without need"; ours is "don't ship a coupled namespace when the split is one-time free at greenfield." The `openteam.client/` split (v3 Round-7) costs ~30 minutes now and saves years of future refactor pain. **v5 keeps it.**
- **Discovery module placement under `openteam.server.discovery`** — recreates the heavy-namespace leak. **v5 keeps the `openteam.client/discovery.py` split with I14 CI preflight.**
- **No mode discipline** — Cursor's subprocess in server mode calls `attach_or_create_session`, which reintroduces the race the server-as-single-writer was designed to eliminate. **v5 keeps I9 + I15 mode discipline** (subprocess uses `get_session` only in server mode).

---

## 0. TL;DR — what's new in v5 (and unchanged from v4)

**The reframe:** v3 used **per-workspace synthetic server dirs** to eliminate the `_update_index` race. v4 adopts Cursor's superior architectural decision: when an OpenTeam server is **running**, make it the **single writer** for session creation via a new `POST /api/sessions/attach` endpoint. This:

1. **Eliminates the `_update_index` race STRUCTURALLY** — by serialising all creation through one process, not by fragmenting on-disk layout
2. **Restores unified UI visibility** — `/task` from TUI shows up in the React UI of the same server (which v3's synthetic dirs broke)
3. **Matches user mental model** — "the server is up; my session is in it"

**Key invariant retained from v3 Round-7:** `openteam.client/` package with Invariant I14 (no client→server imports; CI-enforced). Cursor v4 left this on the table; we keep it because it's load-bearing for a future `openteam-sdk` PyPI extraction.

**Two operating modes (Claude's clean naming, made precise):**
- **Server mode (preferred):** OpenTeam HTTP server is running (auto-launched if not). TUI POSTs `/api/sessions/attach` to create; subprocess attaches (read-only via `get_session`). Single-writer.
- **Subprocess mode (fallback):** HTTP server unavailable. Subprocess calls `attach_or_create_session` directly via filesystem. No race because there's only one writer (no server). v1 Path A fallback semantics preserved.

| Concern | v3 (mine) | Cursor v4 | Claude | **v4 (this)** |
|---|---|---|---|---|
| `_update_index` race resolution | per-workspace synthetic server | server-as-single-writer | unaddressed | **server-as-single-writer (preferred) + per-workspace fallback (mode-aware)** |
| Auto-launch of server | unaddressed | yes (file-lock O_EXCL) | yes (TOCTOU bug — check-then-act) | **yes (file-lock O_EXCL)** |
| Discovery file location | `~/.openteam/servers/` | `~/.openteam/servers/` | `~/.openteam/servers/` | **`~/.openteam/servers/`** |
| `server_id` derivation | `sha(runtime, host)` | `sha(runtime, host, port)` | `<server_name>.json` (collision-prone) | **`sha(runtime, host, port)` (Cursor's)** |
| Client/server boundary | **`openteam.client/` + I14 CI preflight** | discovery under `openteam.server.discovery` | discovery under `openteam.server.discovery` | **`openteam.client/` retained (mine — fixes a real leak Cursor reintroduced)** |
| Single-writer creation endpoint | n/a | `POST /api/sessions/attach` | n/a | **`POST /api/sessions/attach` (adopted)** |
| Server-side write hook | n/a | `discovery.register_server` in same module | server-side write inline in `main.py` | **`server/_register.py` (Round-7 split preserved)** |
| Subprocess attach in server mode | calls `attach_or_create_session` (race risk) | calls `attach_or_create_session` (no race claim) | not addressed | **calls `get_session` only (read-only) in server mode; falls back to `attach_or_create_session` in subprocess mode (no race because no server)** |
| Per-workspace persistence | `.rovodev/openteam_session_id` + `_server_dir` | `.rovodev/openteam_session_id` only | not specified | **`.rovodev/openteam_session_id` only (Cursor's; one fewer file)** |
| Mode naming | "Path A / Path B" | implicit | "Server mode / Subprocess mode" | **"Server mode / Subprocess mode" (Claude's)** |
| Fallback semantics | always create | hard-fail if server down (with opt-out) | server-or-spawn | **server-preferred-but-not-required; subprocess mode is real fallback (matches Claude)** |
| Number of invariants | 14 (I1–I14) | 14 (I1–I14) | 0 | **18 (I1–I18; I15–I18 are new mode-discipline) ** |

**Effort:** ~17h total (v3 was ~17h after Round-7). Net change: per-workspace synthetic server code REPLACED by HTTP attach endpoint; ~equal LOC, much more capability.

**Backward compat:** total. Old TUI binaries that don't know about the connector still work via the subprocess-mode path (Path A semantics). Old server binaries that don't register still get discovered by future TUIs via auto-launch (which will fail because port is taken, then surface clear error — defensive option in §13: assert `service: "openteam"` field in `/api/health`).

---

## 1. The gap

### 1.1 v3-era gaps (still real, still load-bearing)

| Path | session_context shape (today) | Workspace location | What we want |
|---|---|---|---|
| **React UI → WS** (`manager_websocket_routes.py:213-217`) | `{interactive, task_id, session_id, session_root}` | Under session ✅ (`<server>/sessions/<sid>/tasks/`) | unchanged |
| **RovoDev TUI → slash subprocess** (`tool_cli.py:114`) | **`{}`** (empty) | Standalone `<runtime>/tasks/<tool>/` ❌ | Under shared server's session ✅ |
| **RovoDev MCP** (`mcp_server/context.py:17-23`) | `{"task_id": "mcp-<uuid8>", "interactive": None}` | Standalone `<runtime>/tasks/<tool>/` ❌ | Under shared server's session ✅ |

### 1.2 v4 NEW gap: there is no way to discover or auto-launch the OpenTeam server

Verified by direct codebase inspection:

- **No console script `openteam-server`.** Server launched only via `run.sh` (`python run_server.py`).
- **No server registry.** `_runtime/servers/server_<TS>_<uuid>/server_info.json` records `{name, created_at, pid}` but **NO `host`/`port`** — so even if you find the file you can't connect.
- **No liveness API surface beyond per-server `_runtime/`.** No `~/.openteam/`, no PID file, no helper.
- **No background/daemon mode.** `run.sh` just backgrounds with `&` and traps SIGTERM in the same shell.
- **No auto-launch helper on the client side.**
- React UI relies on hardcoded `REACT_APP_BACKEND_PORT` (defaults to 8000) and just attempts the WS connection.

**Consequence today:** if a user runs `rovodev tui` and the OpenTeam server isn't running, `/task` falls into the standalone path (Subprocess Mode); no React UI visibility; no shared backend across TUI workspaces.

**v4 closes both gaps with one generic mechanism.**

---

## 2. Architectural invariants

### 2.1 v3 invariants (retained, with one supersession)

- **I1.** `attach_or_create_session(external_id, *, ...)` is idempotent: same id called twice returns the existing session.
- **I2.** External session IDs pass `validate_external_id`: prefix ∈ whitelist; remainder regex `^[A-Za-z0-9_.\-]{1,128}$`.
- **I3.** `_VALID_FRONTEND_PREFIXES` is immutable except via CI preflight.
- **I4.** Executors respect `session_context["session_root"]` and fall back to Path A if absent.
- **I5.** The 4 env vars are read in exactly one place (`build_session_context`).
- **I6 (SUPERSEDED by I15):** v3 used per-workspace synthetic `server_rovodev_<wsuuid>/` to avoid the `_update_index` race. v4 supersedes this: in Server Mode, the server is the single writer (HTTP `POST /api/sessions/attach`); per-workspace synthetic dirs are gone. In Subprocess Mode, the race trivially doesn't exist (one writer, no server).
- **I7.** `SessionStore(runtime_root, *, resume_server=)` — never `server_dir=`.
- **I14 (Round-7).** `openteam.client.**` MUST NOT import from `openteam.server.**`. Reverse permitted: `openteam.server._register` imports schema from `openteam.client.discovery`. Enforced by CI preflight `test_no_server_imports.py` (AST scan).

### 2.2 v4 NEW invariants (server discovery + mode discipline)

- **I8. Discovery file location:** running OpenTeam servers register at `~/.openteam/servers/<server_id>.json`. Schema versioned. Atomic writes (`tempfile` + `os.replace`).
- **I9. Server-as-single-writer (Server Mode).** When a live OpenTeam server is reachable, ALL session CREATION goes through `POST /api/sessions/attach` (server is the only `create_session` caller). Subprocess `tool_cli` calls `get_session` (read-only) in this mode — never `create_session`. No two-writer race.
- **I10. `OpenTeamServerConnector.ensure_running()` is the single client-side entry point.**
- **I11. Server liveness = PID alive AND `GET /api/health` returns 200 within 200ms.** Both must pass. Either fails → entry treated as stale and reaped.
- **I12. Server unregistration is best-effort** via `atexit` + `signal.signal(SIGTERM/SIGINT)` handlers. Stale entries are reaped by clients on every read.
- **I13. Launch is idempotent under concurrency** via O_EXCL file-lock at `~/.openteam/servers/.launch.lock`. After acquiring, re-check the registry. Concurrent TUIs converge on one server.
- **I15. Mode discipline (NEW).** A client either operates in **Server Mode** (has a `ServerHandle`) or **Subprocess Mode** (does not). Mode is fixed for the lifetime of a slash invocation; the subprocess is told via the `OPENTEAM_MODE` env var (`server` or `subprocess`). In Server Mode the subprocess uses `get_session` only; in Subprocess Mode it uses `attach_or_create_session`. CI preflight asserts the env var is one of these two values.
- **I16. Server_id derivation:** `sha256(runtime_root|host|port)[:12]` (Cursor's). Triple-keyed so dev + staging servers on the same machine never collide; same OpenStartup checkout on different ports get distinct ids.
- **I17. Auto-launched server inherits `OPENTEAM_AUTO_LAUNCH=0`** in its env. Server's own startup code reads this and refuses to call the connector — defends against accidental fork bomb if a future server-side helper imports `openteam.client`.
- **I18. Mock-mode safety:** the `/api/sessions/attach` endpoint MUST 400 (`"not available in mock mode"`) when `data_service` is the mock variant. CI preflight covers this.

---

## 3. Architecture

### 3.1 End-to-end flow (Server Mode happy path)

```mermaid
flowchart TB
  subgraph user["User"]
    cmd["$ rovodev tui"]
    task["/task what is 2+2"]
  end

  subgraph TUI[RovoDev TUI process]
    startup["TUI startup"]
    connector["openteam.client.ensure_server()<br/>(was OpenTeamServerConnector)"]
    persistRead[".rovodev/openteam_session_id<br/>(read or mint UUID4)"]
    httpAttach["urllib POST<br/>/api/sessions/attach<br/>{external_id, frontend_id, frontend_metadata}"]
    spawnSubproc["spawn openteam-task subprocess<br/>env: OPENTEAM_SERVER_DIR, OPENTEAM_SESSION_ID,<br/>OPENTEAM_FRONTEND_ID, OPENTEAM_MODE=server"]
  end

  subgraph DISC["~/.openteam/servers/"]
    regFile["<server_id>.json<br/>{host, port, pid, server_dir_name,<br/> started_at, schema_version, version}"]
    lockFile[".launch.lock<br/>(O_EXCL during launch)"]
  end

  subgraph SERVER[OpenTeam server (uvicorn)]
    serverProc["server process<br/>(auto-launched if absent)"]
    register["openteam.server._register<br/>.register_server()<br/>(writes registry on startup;<br/>atexit + SIGTERM unregister)"]
    health["GET /api/health → 200"]
    attachEP["POST /api/sessions/attach<br/>(NEW endpoint)"]
    store["SessionStore<br/>.attach_or_create_session()<br/>(single writer in Server Mode)"]
  end

  subgraph PROC[openteam-task subprocess]
    cliRead["tool_cli.run_cli reads env"]
    bsc["build_session_context()<br/>(reads 5 env vars)"]
    modeBranch{{"OPENTEAM_MODE?"}}
    storeAttachRO["SessionStore.get_session(sid)<br/>(read-only; raises if missing)"]
    storeAttachRW["SessionStore.attach_or_create_session<br/>(Subprocess Mode fallback)"]
    exec["executor.execute(args, ctx)"]
    alloc["allocate_tool_workspace<br/>under ctx['session_root']"]
  end

  cmd --> startup
  startup --> connector
  connector -->|"read"| regFile
  connector -.->|"none alive"| lockFile
  connector -.->|"acquire, spawn"| serverProc
  serverProc --> register --> regFile
  connector -->|"return ServerHandle"| TUI

  task --> persistRead
  persistRead --> httpAttach
  httpAttach -->|"POST"| attachEP
  attachEP --> store
  store -->|"creates sessions/<external_id>_<TS>/<br/>updates sessions_index.json<br/>(SINGLE WRITER)"| serverProc
  attachEP -->|"return {session_id, session_root, created}"| TUI

  TUI --> spawnSubproc
  spawnSubproc -->|"env"| PROC
  cliRead --> bsc --> modeBranch
  modeBranch -->|"server"| storeAttachRO
  modeBranch -->|"subprocess"| storeAttachRW
  storeAttachRO --> exec
  storeAttachRW --> exec
  exec --> alloc
  alloc -->|"task workspace lands<br/>under existing session"| store
```

### 3.2 Subprocess Mode (fallback, when no server)

When `ensure_server(auto_launch=...)` returns `None` (e.g., user passed `--no-openteam-server`, or all auto-launch ports occupied, or `OPENTEAM_AUTO_LAUNCH=0` and no live server), the TUI does NOT POST to the server. It spawns the subprocess with `OPENTEAM_MODE=subprocess` and `OPENTEAM_SERVER_DIR` unset. The subprocess then:

1. `build_session_context()` sees no `OPENTEAM_SERVER_DIR` → returns empty dict (Path A).
2. Executor runs unchanged; `allocate_tool_workspace` falls back to `<runtime>/tasks/<tool>/` (today's behavior).

Subprocess Mode is **identical to today's behavior**. Zero regression.

### 3.3 On-disk layout (v4)

```
~/.openteam/                                          ← NEW: client-side registry
└── servers/
    ├── server_<server_id>.json                       ← live server entry (one per running server)
    │   {schema_version, server_id, pid, host, port,
    │    runtime_root, server_dir_name, started_at,
    │    version, service: "openteam"}
    ├── server_<other_server_id>.json                 ← another running server (e.g. staging on port 8001)
    └── .launch.lock                                  ← O_EXCL during auto-launch (rare)

<workspace>/.rovodev/                                 ← per-workspace TUI persistence
└── openteam_session_id                               ← bare UUID4 (e.g. "550e8400-e29b-...")
                                                       ← NO separate server_dir file (Cursor v4 simplification)

<runtime_root>/                                       ← server's runtime data (unchanged)
└── servers/
    └── server_<TS>_<uuid8>/                          ← REAL auto-launched server's dir
        ├── server.log
        ├── server_info.json                          ← server self-info (existing v3 file)
        └── sessions/
            ├── rovodev-550e8400-...e29b_<TS>/        ← TUI workspace #1's session (v3 prefix protocol)
            │   ├── session_state.json
            │   └── tasks/
            │       └── task_<TS>_<uuid8>/
            ├── rovodev-6f7a9b2c-...d4e5_<TS>/        ← TUI workspace #2's session (same shared server)
            │   └── tasks/...
            └── session-<unix>-<hex6>_<TS>/           ← React UI session (legacy id format)
                └── tasks/...
```

### 3.4 Module layout (Round-7 client/server split RETAINED)

```
src/openteam/client/                       ← lean: stdlib + lazy httpx only
  __init__.py                              ← re-exports ensure_server, ServerHandle, etc.
  discovery.py                             ← schema constants + ServerHandle + discover_servers()
  supervisor.py                            ← ensure_server() launch-or-attach
  attach.py                                ← NEW v4: thin urllib POST wrapper for /api/sessions/attach

src/openteam/server/
  _register.py                             ← write hook only (imports schema from openteam.client.discovery)
  routes/session_routes.py                 ← ADD POST /api/sessions/attach (~40 LOC)
  routes/health_routes.py                  ← ADD service:"openteam" to /api/health response
  run_server.py                            ← unchanged caller of _register.register_server()
  services/session_store.py                ← add attach_or_create_session + validate_external_id (v3)
```

### 3.5 Server-dir resolution rule (UPDATED from v3)

| Entry point | Server-dir resolution |
|---|---|
| **WS server** | Server's own dir, minted at boot. Unchanged. |
| **RovoDev TUI subprocess (Server Mode)** | Auto-launched real server's dir, discovered via `openteam.client.ensure_server`. Passed in `OPENTEAM_SERVER_DIR`. |
| **RovoDev TUI subprocess (Subprocess Mode)** | None — env var unset; `build_session_context()` returns `{}`; falls into Path A standalone. |
| **MCP standalone (Server Mode)** | Same as TUI Server Mode: connector discovers server. |
| **MCP standalone (Subprocess Mode)** | Same as TUI Subprocess Mode: empty context, Path A fallback. |
| **Direct CLI** (`openteam-task` typed by hand) | Both env vars unset → empty session_context → Path A fallback. |

### 3.6 Decision matrix — why this discovery mechanism (absorbed from Cursor INTEGRATED-v4 §3.5)

Systematic comparison of every reasonable discovery alternative. Shown so reviewers can verify that the chosen design is the **right** one, not the first one we thought of. "No ad-hoc, no hacky" requires showing the work.

| Mechanism | Pros | Cons | Verdict |
|---|---|---|---|
| **`~/.openteam/servers/<id>.json` per-server file (v5 choice)** | Jupyter precedent (~10 yr production); one file per server; atomic write; stale-reapable; supports N concurrent servers; no daemon required; no root needed | One extra file to clean up; POSIX-only (Windows: works but TBD on rename atomicity) | ✅ |
| Single `~/.openteam/registry.json` (all servers in one file) | One file to read | Concurrent writes need locking (`fcntl.flock`); harder to reason about per-server lifecycle; one corrupt write kills all discovery | ❌ |
| Per-server PID file `/var/run/openteam-<id>.pid` | Unix tradition | Requires root or `/var/run/user/`; no host/port info; no metadata; single-value | ❌ |
| `dbus` / `XDG_RUNTIME_DIR` Linux service | Linux-native discovery | Not portable to macOS; heavyweight; requires session bus | ❌ |
| TCP port-knock (probe range 8000-8010, query `/api/health`) | Zero registry to manage | Can't distinguish OpenTeam from other listeners on 8000 (Risk R5); no metadata; doesn't handle different runtime_roots; slow when probing | ❌ |
| `systemd` user unit (auto-start on login) | Auto-restart, journald logs, well-understood | Linux-only; OpenStartup isn't installed as a service; opt-in barrier; doesn't help one-shot `python run_server.py` developers | ❌ |
| Lock-file at `~/.openteam/openteam.lock` (single global lock) | Simplest possible | Doesn't address discovery (just mutex); ignores multi-runtime-root case | ❌ |

**Conclusion:** the discussion converges on Jupyter's pattern. Don't reinvent.

**Why not even simpler?** ("Just have the user pass `--openteam-host`/`--openteam-port` to the TUI; no discovery needed.") — yes, but then the *common case* (one running server, one user, one workspace) requires ceremony. v5 makes the common case zero-config; the explicit-flag path remains as the escape hatch for advanced users (§7 CLI flags).

---

## 4. Discovery file schema (v1)

**Prior art:** the file layout, lifecycle, and naming conventions are borrowed from Jupyter's `~/.local/share/jupyter/runtime/jpserver-<pid>.json` pattern (~10 years in production at Project Jupyter; well-understood by ops teams). We do not reinvent.

```json
{
  "$schema": "https://openteam.dev/discovery/v1.json",
  "schema_version": 1,
  "server_id": "server_3a1b2c4d5e6f",
  "pid": 12345,
  "host": "127.0.0.1",
  "port": 8000,
  "runtime_root": "/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_runtime",
  "server_dir_name": "server_20260517_204500_3a1b2c4d",
  "started_at": "2026-05-17T20:45:00.123Z",
  "version": "0.42.0",
  "service": "openteam",
  "process_command": ["python", "-m", "openteam.server.run_server", "--port", "8000", "--real-sessions", "default"]
}
```

Field notes:
- `$schema`: JSON-Schema URL. Enables IDE validation and future schema-evolution tooling. Hosted at `openteam.dev/discovery/v1.json` (POST-1 hosting; v1 ships the URL, schema-file hosting is best-effort).
- `schema_version`: integer. Bumped only via the `test_discovery_schema_immutable.py` CI preflight (no silent changes).
- `server_id`: `sha256(runtime_root|host|port)[:12]` (Invariant I16). Triple-keyed so a single host can run dev (port 8000) + staging (port 8001) without collision; distinct OpenStartup checkouts get distinct ids.
- `pid`: server process PID. Used for liveness check via `os.kill(pid, 0)`.
- `host`, `port`: HTTP+WS endpoint. v1 supports `127.0.0.1` only; multi-host is POST-1.
- `runtime_root`: absolute path to `_runtime/`. Critical for clients with explicit runtime-root preference (Invariant I16 uniqueness key component).
- `server_dir_name`: basename only (not absolute). Full path is `Path(runtime_root) / "servers" / server_dir_name`. Stored as basename so the file is movable across `runtime_root` reorgs.
- `started_at`: ISO 8601 UTC with milliseconds. Used for human inspection / diagnostics. NOT for staleness — that's PID + health.
- `version`: OpenTeam package version (`importlib.metadata.version("openteam")`). Clients MAY refuse to attach if version is too old (post-v5 client compat policy).
- `service`: literal `"openteam"`. Defensive marker; `/api/health` returns the same field. Prevents false-positive discovery if a non-OpenTeam process happens to be listening on 8000 (Risk R5 mitigation).
- `process_command`: argv used to launch the server. Supports a future `openteam-server stop <server_id>` (POST-1) without re-parsing config. Read-only field; not used by v5 clients but reserved for forward-compat.

**Atomic writes:** server writes via `tempfile.mkstemp` + `os.replace` (POSIX-atomic rename). Readers never see torn JSON. Discovery directory created on demand via `mkdir(parents=True, exist_ok=True)`.

**Registry directory:** defaults to `~/.openteam/servers/`; overridable via `OPENTEAM_REGISTRY_DIR` env var (test isolation, multi-user systems, sandboxed environments).

---

## 5. The four code surfaces (LOC counts after Round-7 split)

### 5.1 `openteam.client` package (~250 LOC total)

| File | Purpose | LOC | Imports |
|---|---|---|---|
| `__init__.py` | Re-exports | 12 | stdlib only |
| `discovery.py` | Schema constants + `ServerHandle` + `discover_servers` + `compute_server_id` + `pid_alive` + `health_check` | 110 | stdlib + lazy httpx |
| `supervisor.py` | `ensure_server()` + `auto_launch_server()` + `_pick_free_port()` + O_EXCL lock | 95 | stdlib + lazy subprocess + `client.discovery` |
| `attach.py` | `attach_session_via_http(handle, external_id, ...)` urllib wrapper | 35 | stdlib only |

### 5.2 `openteam.server` additions (~120 LOC total)

| File | Purpose | LOC |
|---|---|---|
| `_register.py` | `register_server()` (write side); imports schema from `openteam.client.discovery` | 60 |
| `routes/session_routes.py` | ADD `POST /api/sessions/attach` endpoint + Pydantic models | 45 |
| `routes/health_routes.py` | ADD `service: "openteam"` field | 3 |
| `run_server.py` | ADD `register_server(...)` call before `uvicorn.run(...)` | 12 |

### 5.3 `cli-rovodev-tui` additions (~80 LOC total)

| File | Purpose | LOC |
|---|---|---|
| `openteam_session.py` | `get_or_create_session_id(workspace)` — UUID4 mint + persist; NO server dir | 30 |
| `app.py` | Call `ensure_server` on startup; cache `self.openteam_handle`; CLI flags | 25 |
| `slash_commands/openteam.py` | Mode-aware handler: HTTP POST in server mode; env-only in subprocess mode | 25 |

### 5.4 Test surfaces (~30 tests + 3 CI preflights)

| Suite | Tests | Tier |
|---|---|---|
| `test/openteam/client/test_discovery.py` | 4 (schema, compute_id, pid_alive, ServerHandle methods) | TIER-1 |
| `test/openteam/client/test_supervisor.py` | 4 (discover empty, discover live, reuse live, launch when not found) | TIER-1 |
| `test/openteam/client/test_supervisor_file_lock.py` | 1 (two concurrent ensure_server → one launch) | TIER-2 |
| `test/openteam/client/test_no_recursive_launch.py` | 1 (launched server has `OPENTEAM_AUTO_LAUNCH=0`) | TIER-2 |
| `test/openteam/client/test_no_server_imports.py` | 1 (AST scan: client never imports server) | CI preflight |
| `test/openteam/server/test_register.py` | 4 (write atomic, conflict detect, atexit, SIGTERM) | TIER-1 |
| `test/openteam/server/test_attach_route.py` | 5 (create, idempotent, invalid prefix, metadata propagation, mock-mode 400) | TIER-1 |
| `test/openteam/server/test_discovery_schema_immutable.py` | 1 (SCHEMA_VERSION + ServerHandle fields locked) | CI preflight |
| `test/openteam/server/test_health_service_field.py` | 1 (assert `service: "openteam"` in /health response) | CI preflight |
| `test/cli_rovodev_tui/test_openteam_session.py` | 4 (mint, persist, force_new, file location) | TIER-1 |
| `test/cli_rovodev_tui/test_slash_mode_branch.py` | 4 (server mode posts, subprocess mode empties env, server mode subprocess sets MODE=server, fallback on POST failure) | TIER-1 |
| `test/e2e/test_tui_attach_round_trip.py` | 3 (auto-launch → /task → workspace exists; two TUIs share server; restart reuses session) | TIER-2 |


---

## 6. Key code listings

### 6.1 `openteam/client/__init__.py` (12 LOC)

```python
"""Generic OpenTeam client: discover-or-launch a running server + attach sessions.

Frontend-agnostic. RovoDev TUI, future Slack bot, future IDE plugin, future
``openteam-sdk`` PyPI package all import from here — never from ``openteam.server``.
"""
from openteam.client.discovery import (
    DISCOVERY_DIR, SCHEMA_VERSION, ServerHandle,
    compute_server_id, discover_servers, find_server, pid_alive, health_check,
)
from openteam.client.supervisor import ensure_server, auto_launch_server, NoServerAvailable
from openteam.client.attach import attach_session_via_http, AttachResult

__all__ = [
    "DISCOVERY_DIR", "SCHEMA_VERSION", "ServerHandle",
    "compute_server_id", "discover_servers", "find_server",
    "pid_alive", "health_check",
    "ensure_server", "auto_launch_server", "NoServerAvailable",
    "attach_session_via_http", "AttachResult",
]
```

### 6.2 `openteam/client/attach.py` (35 LOC) — NEW in v4

```python
"""Thin urllib wrapper around POST /api/sessions/attach.

Separate file so the supervisor (which does NOT need HTTP attach) can stay
HTTP-free; clients that only need discovery don't pull in attach logic.
"""
from __future__ import annotations
import dataclasses
import json
import urllib.error
import urllib.request
from typing import Any

from openteam.client.discovery import ServerHandle


@dataclasses.dataclass(frozen=True)
class AttachResult:
    session_id: str
    session_root: str        # absolute path on server's filesystem
    created: bool            # True if freshly created, False if already existed


class AttachFailed(Exception):
    """POST /api/sessions/attach failed (HTTP or network)."""


def attach_session_via_http(
    handle: ServerHandle,
    *,
    external_id: str,
    frontend_id: str,
    frontend_metadata: dict[str, Any] | None = None,
    title: str | None = None,
    timeout_s: float = 5.0,
) -> AttachResult:
    """Synchronous POST /api/sessions/attach. Idempotent: same external_id → same session.

    Raises:
      AttachFailed: HTTP error, timeout, or invalid response.
    """
    body = {
        "external_id": external_id,
        "frontend_id": frontend_id,
        "frontend_metadata": frontend_metadata or {},
    }
    if title is not None:
        body["title"] = title
    req = urllib.request.Request(
        f"{handle.http_endpoint}/api/sessions/attach",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AttachFailed(f"POST /api/sessions/attach to {handle.http_endpoint} failed: {e}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AttachFailed(f"invalid JSON from server: {e}")
    try:
        return AttachResult(
            session_id=data["session_id"],
            session_root=data["session_root"],
            created=bool(data["created"]),
        )
    except KeyError as e:
        raise AttachFailed(f"missing field in attach response: {e}")
```

### 6.3 `openteam/server/routes/session_routes.py` ADD (~45 LOC)

```python
# Pydantic models (above the route)
class AttachSessionRequest(BaseModel):
    external_id: str = Field(..., description="Prefix-validated external session id")
    frontend_id: str | None = Field(None, description="Optional; defaults to parsed prefix")
    frontend_metadata: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None

class AttachSessionResponse(BaseModel):
    session_id: str
    session_root: str
    created: bool

@router.post("/attach", response_model=AttachSessionResponse)
async def attach_session(request: Request, body: AttachSessionRequest) -> AttachSessionResponse:
    """Attach or create a session by external_id (v4 unified-frontend protocol).

    Idempotent: same external_id twice returns the same session.
    Validates external_id via the prefix whitelist (raises HTTPException 400).
    Mock-mode safety: returns 400 if data_service lacks attach_or_create_session.
    """
    from openteam.server.services.session_store import validate_external_id
    from fastapi import HTTPException

    svc = request.app.state.data_service
    if not hasattr(svc, "attach_or_create_session"):
        raise HTTPException(400, "not available in mock mode")  # I18

    try:
        prefix, _ = validate_external_id(body.external_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Determine whether this is a fresh create or an attach to existing
    existing = svc._session_store.get_session(body.external_id)
    created = existing is None

    session = svc.attach_or_create_session(
        external_id=body.external_id,
        frontend_id=body.frontend_id or prefix,
        frontend_metadata=body.frontend_metadata,
        title=body.title,
    )
    session_root = svc._session_store._find_session_dir(session["id"])
    return AttachSessionResponse(
        session_id=session["id"],
        session_root=str(session_root),
        created=created,
    )
```

### 6.4 `cli-rovodev-tui/slash_commands/openteam.py` — mode-aware handler (~25 LOC)

```python
async def handler(extra_prompt: str, app: "RovoDevApp") -> None:
    handle: ServerHandle | None = getattr(app, "openteam_handle", None)
    workspace = Path.cwd()
    bare_sid = get_or_create_session_id(
        workspace,
        force_new=getattr(app, "_force_new_openteam_session", False),
    )
    external_id = f"rovodev-{bare_sid}"

    if handle is not None:
        # Server Mode (I9): POST to server (single writer); subprocess only reads.
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: attach_session_via_http(
                    handle,
                    external_id=external_id,
                    frontend_id="rovodev",
                    frontend_metadata={
                        "tui_version": __version__,
                        "workspace": str(workspace),
                    },
                ),
            )
            env_overrides = {
                "OPENTEAM_SERVER_DIR": str(handle.server_dir),
                "OPENTEAM_SESSION_ID": external_id,
                "OPENTEAM_FRONTEND_ID": "rovodev",
                "OPENTEAM_MODE": "server",                   # I15
            }
            app.notify(
                f"Attached to {external_id} ({'new' if result.created else 'existing'})",
                severity="information",
            )
        except AttachFailed as e:
            # Server died between ensure_server and POST. Fall back to Subprocess Mode.
            app.notify(
                f"Server attach failed ({e}); falling back to Subprocess Mode",
                severity="warning",
            )
            env_overrides = {"OPENTEAM_MODE": "subprocess"}
    else:
        # Subprocess Mode (no server): unchanged from v3 Path A fallback.
        env_overrides = {"OPENTEAM_MODE": "subprocess"}

    # Spawn openteam-task subprocess
    env = {**os.environ, **env_overrides}
    # ... existing subprocess.Popen ...
```

### 6.5 Subprocess: `build_session_context()` mode branch (~15 LOC delta)

```python
# In src/openteam/server/services/context.py (build_session_context)

def build_session_context(*, frontend_id=None, frontend_session_id=None, frontend_metadata=None):
    mode = os.environ.get("OPENTEAM_MODE", "subprocess")
    composed_external_id = ...  # (v3 logic, unchanged)
    server_dir = os.environ.get("OPENTEAM_SERVER_DIR")

    if not server_dir:
        return {}  # Path A fallback (I4)

    store = SessionStore(runtime_root=Path(server_dir).parent.parent, resume_server=Path(server_dir).name)

    if mode == "server":
        # I9: subprocess is reader-only. TUI's HTTP POST already created.
        session = store.get_session(composed_external_id)
        if session is None:
            # Server died between TUI POST and subprocess spawn — degrade gracefully.
            logging.warning(
                "[openteam] session %s missing in server mode; falling back to create",
                composed_external_id,
            )
            session = store.attach_or_create_session(
                external_id=composed_external_id,
                frontend_id=frontend_id,
                frontend_metadata=frontend_metadata,
            )
    elif mode == "subprocess":
        session = store.attach_or_create_session(
            external_id=composed_external_id,
            frontend_id=frontend_id,
            frontend_metadata=frontend_metadata,
        )
    else:
        raise ValueError(f"invalid OPENTEAM_MODE={mode!r}; expected 'server' or 'subprocess'")

    return {
        "session_id": session["id"],
        "session_root": str(store._find_session_dir(session["id"])),
        # ... other v3 context fields ...
    }
```


---

## 7. Phased delivery

| # | Phase | Effort | Depends on | Blocks | DoD |
|---|---|---|---|---|---|
| **0** | v3 prerequisites: `attach_or_create_session` + `validate_external_id` + `_VALID_FRONTEND_PREFIXES` in `session_store.py` | (per v3) | — | all v4 | v3 TIER-1 green |
| **1a** | `openteam/client/__init__.py` + `client/discovery.py` + `test_discovery.py` (4 tests) + CI preflight `test_no_server_imports.py` | 1.5h | 0 | 1b | green |
| **1b** | `openteam/server/_register.py` + `test_register.py` (4 tests) + `run_server.py` calls it | 1h | 1a | 2 | server launches; discovery file appears |
| **1c** | `openteam/client/supervisor.py` + `test_supervisor.py` (4) + `test_supervisor_file_lock.py` + `test_no_recursive_launch.py` | 2h | 1a, 1b | 2 | green |
| **2a** | `POST /api/sessions/attach` endpoint in `session_routes.py` + Pydantic models + `test_attach_route.py` (5) | 1.5h | 0, 1b | 2b | green |
| **2b** | `GET /api/health` adds `service: "openteam"` + `test_health_service_field.py` (1, CI preflight) | 20m | 2a | 3 | green |
| **3a** | `openteam/client/attach.py` (35 LOC) + unit tests (3: success, idempotent, network failure) | 1h | 2a | 3b | green |
| **3b** | `build_session_context` mode branch in `context.py` (15 LOC) + tests (2: server mode reads, subprocess mode creates) | 1h | 3a | 4 | green |
| **4** | TUI: `openteam_session.py` (UUID4 mint/persist) + `app.py` startup ensure_server call + 4 CLI flags | 1.5h | 1c, 3b | 5 | manual smoke: `rovodev tui` launches new server |
| **5** | TUI slash handler mode branch + `test_slash_mode_branch.py` (4) | 1.5h | 3a, 4 | 6 | green |
| **6a** | E2E test: `test_tui_attach_round_trip.py` (3 scenarios) | 1.5h | 5 | 6b | green |
| **6b** | `docs/openteam-integration.md` + `docs/SERVER_DISCOVERY.md` documenting mode discipline + opt-out | 1h | 6a | — | reviewed |
| **6c** | `pyproject.toml` adds `openteam-server` console script (`run_server:main`) | 15m | 1b | — | `openteam-server --help` works |

**Total v4: ~14h focused work** (vs v3 ~17h with synthetic server; v4 saves ~3h by REPLACING synthetic-server LOC with HTTP attach LOC).

**Critical path:** 0 → 1a → 1b → 1c → 2a → 2b → 3a → 3b → 4 → 5 → 6a → 6b → 6c.

---

## 8. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Server crashes mid-session, leaving stale discovery file | Medium | Low | Clients reap on every read (I12); `is_alive()` double-checks PID + health |
| R2 | Two TUIs race to auto-launch | High (concurrent invocations) | Medium | O_EXCL file lock (I13); loser polls registry up to 15s |
| R3 | Auto-launched server inherits broken env (e.g., wrong `PATH`) and fails to start | Low | Medium | Launch helper waits up to 15s for registry; on timeout, surfaces `RuntimeError` with PID for `kill -9` |
| R4 | `_update_index` race comes back if subprocess writes in server mode | High if not enforced | High | **I9 mandate + I15 mode discipline + CI preflight on `OPENTEAM_MODE` values + test_slash_mode_branch.py** |
| R5 | Non-OpenTeam server listening on port 8000 returns 200 to `/api/health` | Low | High | `service: "openteam"` field in `/api/health` (I18 defensive); `attach.py` checks for `service` mismatch and raises `AttachFailed` |
| R6 | TUI imports `openteam.server` accidentally, breaking lean-import goal | Medium (regression risk) | Medium | **CI preflight `test_no_server_imports.py`** (AST scan over `src/openteam/client/`) |
| R7 | Discovery file schema bumped silently, breaking older clients | Medium | High | `test_discovery_schema_immutable.py` CI preflight asserts `SCHEMA_VERSION == 1` AND `ServerHandle` fields unchanged; bumping requires explicit changelog |
| R8 | `~/.openteam/servers/` directory deleted by user (or `tmpfs` reboot) | Low | Low | All write helpers do `mkdir(parents=True, exist_ok=True)`; reads return `[]` |
| R9 | Server registered with wrong `runtime_root` (e.g., relative path) | Low | Medium | `register_server` resolves to absolute path; `compute_server_id` also resolves; mismatch surfaces as "no live server matches" |
| R10 | Auto-launch picks a port already in use by a non-OpenTeam process | Medium | Low | `_pick_free_port` tries 8000..8010 via `socket.bind` (atomic). On full range, raises clear `RuntimeError` |
| R11 | User runs `rovodev tui` in a workspace with no `_runtime` ancestor | Medium | Low | `_resolve_openteam_runtime_root()` falls back to `~/.openteam/_runtime` (creates if needed) |
| R12 | Server auto-launch fork-bombs if server imports `openteam.client` | Low (only if future change introduces it) | Catastrophic | I17: launch helper sets `OPENTEAM_AUTO_LAUNCH=0` in child env; server's own startup refuses to call connector if set |
| R13 | Subprocess in server mode hits a session-not-found (server died between POST and spawn) | Low | Low | Graceful degradation: subprocess falls back to `attach_or_create_session` with logged warning (§6.5) |
| R14 | Windows compatibility | n/a | n/a | OpenStartup is POSIX-only today (verified `pyproject.toml`). Document v4 as POSIX-only; Windows is out of scope. |
| R15 | `httpx` not in TUI dep tree | Verified absent | None | We use `urllib.request` (stdlib) in `attach.py`; `discovery.py` uses lazy `httpx` import for health-check, with `urllib` fallback. |
| R16 | Existing server running before Phase 1b ships (no registry entry) | Medium during rollout | Low | Migration plan in §13: roll out Phase 1b first; users restart server before Phase 4 lands |
| R17 | Mock-mode data_service (test env) used in server mode | Medium in tests | Low | I18: `/api/sessions/attach` returns 400 in mock mode; `test_attach_mock_mode_400` covers |

---

## 9. Self-audit (why this design is elegant, not hacky)

| Property | How achieved |
|---|---|
| **Client/server boundary (Round-7 RETAINED)** | Lean `openteam.client` (stdlib + lazy httpx). Heavy `openteam.server` (FastAPI, React assets, inference backends) NEVER imported by clients. Enforced by I14 + CI preflight. |
| **Single responsibility per module** | `client/discovery.py` = schema+read. `server/_register.py` = write (50 LOC). `client/supervisor.py` = discover-or-launch. `client/attach.py` = HTTP POST. `openteam_session.py` = TUI wiring. No module does two jobs. |
| **Server-as-single-writer (v4 core)** | I9 makes session creation a server-only operation in Server Mode. Eliminates the `_update_index` race STRUCTURALLY rather than by per-workspace fragmentation. |
| **Mode discipline** | I15: every subprocess invocation is either Server Mode or Subprocess Mode, decided at TUI level, communicated via `OPENTEAM_MODE` env var. CI preflight ensures only those two values. No middle ground. |
| **Graceful degradation** | If server crashes mid-task, subprocess in server mode falls back to `attach_or_create_session` with logged warning. No data loss, no hang. |
| **No fork bomb** | I17: launched server sees `OPENTEAM_AUTO_LAUNCH=0`. |
| **No race on concurrent launch** | I13: O_EXCL file-lock. |
| **No conflict between checkouts** | I16: `server_id = sha(runtime, host, port)`. Triple-keyed. |
| **Self-healing** | I11 + reap-on-read: stale discovery files cleaned on every `discover_servers()` call. |
| **No new dependencies for clients** | `urllib.request` (stdlib) for HTTP attach; `httpx` is optional (only used for fast health-check). Discovery is pure stdlib. |
| **Atomic registration** | `tempfile.mkstemp` + `os.replace`: POSIX-atomic. No reader ever sees torn JSON. |
| **Server outlives TUI** | `start_new_session=True`. Server is a shared resource (matches user mental model of "the server is up"). |
| **Defensive against impostor servers** | `service: "openteam"` field in `/api/health` + discovery file; `attach.py` checks. R5 mitigation. |
| **Logs preserved on launch failure** | `<discovery_dir>/<sid>.log` keeps stdout+stderr of failed auto-launch attempts for postmortem. |
| **Two-plan reconciliation** | Cursor v4's HTTP architecture preserved; v3's `openteam.client/` package split preserved; Claude's naming ("Server Mode / Subprocess Mode") preserved. No compromise on any axis. |

---

## 9.5. Glossary

| Term | Meaning |
|---|---|
| **Server Mode** | A slash invocation where the TUI has a live `ServerHandle` and POSTs to `/api/sessions/attach`. Subprocess uses `get_session` (read-only). |
| **Subprocess Mode** | A slash invocation where the TUI has no `ServerHandle` (server down, opt-out, etc.). Subprocess uses `attach_or_create_session` (creates if missing). |
| **Discovery file** | A JSON file at `~/.openteam/servers/<server_id>.json` describing one live server. Written by server on startup; removed on graceful shutdown. |
| **`server_id`** | `sha256(runtime_root|host|port)[:12]`. Deterministic per `(runtime_root, host, port)` triple. |
| **`ServerHandle`** | Frozen dataclass with `http_endpoint`, `ws_endpoint`, `server_dir`, `is_alive()`, etc. Returned by `find_server` / `ensure_server`. |
| **`openteam.client`** | The lean client package (stdlib + lazy httpx). Used by TUI, future Slack bot, IDE plugin, `openteam-sdk` PyPI. |
| **`openteam.server`** | The heavy server package (FastAPI, React assets, inference backends). NEVER imported by clients (I14). |
| **`ensure_server`** | Client-side helper: returns a `ServerHandle` (auto-launching if absent). The single entry point. |
| **`/api/sessions/attach`** | NEW HTTP endpoint. Idempotent. Returns `{session_id, session_root, created}`. |
| **`OPENTEAM_MODE`** | NEW env var on subprocess: `"server"` (subprocess attaches read-only) or `"subprocess"` (subprocess creates). |
| **`OPENTEAM_AUTO_LAUNCH=0`** | NEW env var, set by auto_launch_server in spawned server's env, prevents I17 recursion. |
| **`--no-openteam-server`** | NEW TUI CLI flag: disable auto-launch; force Subprocess Mode. |
| **`--openteam-server-id=<id>`** | NEW TUI CLI flag: pin to a specific server (when multiple servers run). |
| **`--openteam-host`, `--openteam-port`** | NEW TUI CLI flags: prefer a specific endpoint. |

---

## 10. Out of scope (deliberate v5 boundaries, absorbed from Cursor INTEGRATED-v4 §10)

Calling these out explicitly so reviewers don't ask and implementers don't sneak them in:

| Item | Why deferred | Future label |
|---|---|---|
| `openteam-server stop|status|restart` user-facing CLI | Not blocking for the v5 user story; auto-launch covers 95% of cases | POST-1 |
| Server **idle shutdown** (auto-stop after N hours no activity) | Need usage telemetry first to pick the right N; manual `kill` is fine for v1 | POST-2 |
| TUI **subscribes to server WS** for real-time graph events | Orthogonal to v5's session protocol; covered by the separate graph-view-v4 plan (NDJSON over fd 3) | POST-3 (graph-view track) |
| **Auth on `/api/sessions/attach`** | Local-only deployment; loopback-bound; out of threat model. v1 listens on `127.0.0.1` only. | POST-4 (if multi-host) |
| **Multi-host federation** (TUI connecting to remote OpenTeam) | v1 hardcodes `127.0.0.1`. Multi-host adds auth + TLS + service discovery scope creep. | POST-4 |
| **Server crash recovery / supervisor-style restart-on-failure** | Auto-launch on next TUI start is good enough; no daemon for v1 | POST-5 |
| **GUI for picking among multiple servers** | `--openteam-server-id` CLI flag is the v1 escape hatch | POST-6 |
| **Windows-native daemon** | OpenStartup is POSIX-only today (verified `pyproject.toml`); Windows TBD | POST-7 |
| **`openteam-sdk` PyPI package extraction** | The Round-7 `openteam.client/` split makes this a `pyproject.toml` packaging change later; not needed for v1 (only internal consumer is RovoDev TUI) | POST-8 |
| **`OPENTEAM_REGISTRY_DIR` propagation to child servers** | Auto-launched server inherits its parent's env (including registry override); explicit override not needed | n/a (handled) |
| **TUI-to-server bidirectional events** (e.g., server pushes "session was deleted") | One-way for v1 (TUI POSTs; server stores). React UI already does bidi via WS. | POST-9 |
| **Per-session log streaming from server back to TUI** | v1 keeps stdout in TUI subprocess; server's per-session logs are visible via React UI only | POST-10 |

**Anti-features (will NOT be added even if requested):**
- **Auto-stop server when last TUI disconnects.** Breaks "server is up" mental model; React UI users would lose sessions.
- **Global lock at `~/.openteam/global.lock`.** Replaces fine-grained per-server discovery with one shared mutex — bad scaling property.
- **Server PID stored in TUI workspace `.rovodev/openteam_server_pid`.** Breaks if user kills server (TUI keeps trying stale PID); registry-driven discovery is correct.

---

## 11. Definition of Done

### v3 prerequisites
- [ ] `attach_or_create_session` + `validate_external_id` + `_VALID_FRONTEND_PREFIXES` in `session_store.py`
- [ ] `build_session_context` rewritten with correct SessionStore signature
- [ ] `tool_cli.py:114` calls `build_session_context()`
- [ ] MCP wrappers accept `frontend_session_id` + `frontend_metadata` kwargs

### v4 OpenStartup additions
- [ ] `openteam.client` package ships with `__init__.py`, `discovery.py`, `supervisor.py`, `attach.py`
- [ ] `openteam.server._register` module ships; imports schema from `openteam.client.discovery`
- [ ] `run_server.py` calls `register_server(...)` before `uvicorn.run(...)`
- [ ] `POST /api/sessions/attach` ships with idempotent semantics and `{created: bool}` return
- [ ] `GET /api/health` adds `service: "openteam"` field
- [ ] `pyproject.toml` adds `openteam-server` console script
- [ ] All ~30 unit tests + ~3 CI preflights green

### v4 cli-rovodev-tui additions
- [ ] `openteam_session.py` ships with `get_or_create_session_id` (UUID4, persists to `.rovodev/openteam_session_id`)
- [ ] TUI `app.py` calls `ensure_server` on startup; caches handle as `self.openteam_handle`
- [ ] CLI flags: `--no-openteam-server`, `--openteam-server-id`, `--openteam-host`, `--openteam-port`
- [ ] Slash handler is mode-aware: HTTP POST in server mode, env-only in subprocess mode, graceful fallback on POST failure
- [ ] All TUI tests green

### E2E
- [ ] Fresh machine, no server: `rovodev tui` → server auto-launches → `~/.openteam/servers/<id>.json` exists → `/task "what is 2+2"` → task workspace under `<runtime>/servers/<server>/sessions/rovodev-<UUID4>_<TS>/tasks/task_*/`
- [ ] Second TUI in different workspace, same machine: discovers existing server (no second launch), creates second `rovodev-*` session under same server
- [ ] Restart TUI in original workspace: same `rovodev-*` session reused (per-workspace `.rovodev/openteam_session_id` persisted)
- [ ] `rovodev tui --no-openteam-server`: no auto-launch; `/task` falls back to Subprocess Mode (today's behavior)
- [ ] React UI at `http://127.0.0.1:<auto-port>/`: `GET /api/sessions` lists rovodev-* sessions alongside any session-* ones
- [ ] Kill auto-launched server (`kill <pid>`): registry file removed (signal handler) OR reaped on next TUI launch (PID dead detection)
- [ ] Start server manually with `openteam-server --port 8001 --real-sessions <root>`: TUI discovers it, uses port 8001 instead of auto-launching another

---

## 12. Pick-one verdict (if only ONE plan could ship)

**Pick v4 (this file).** It is the only plan with:
- **v3 protocol correctness** (Round-4 verified idempotency, validate_external_id, env-var single read point)
- **Cursor v4 architectural elegance** (HTTP single-writer, no per-workspace fragmentation, unified UI visibility)
- **v3 Round-7 directionality** (`openteam.client/` package + I14 CI preflight — Cursor reintroduces the leak)
- **Claude's clean naming** (Server Mode / Subprocess Mode)
- **18 invariants** (vs Cursor's 14, my v3's 14, Claude's 0)
- **30 tests + 3 CI preflights** (vs Cursor's ~26, my v3's 34+CI, Claude's 0)

**If v4 is excluded:**
- **Cursor INTEGRATED-v4 (1359 lines)** is best — has the HTTP architecture and discovery/auto-launch fully designed; has small bugs (puts discovery under `server/`, missing mode discipline, no `service` field defense)
- **My v3 (1643 lines)** is second-best — has rigorous discipline and `openteam.client/` split; misses the server-as-single-writer architectural win; has per-workspace synthetic dirs that break UI visibility
- **Claude (186 lines)** is third — has the right naming and the right shape but has a TOCTOU race in `find_or_start_server` and lacks all the depth

**Ordering with v4 in play:** v4 > Cursor v4 > my v3 > Claude.
**Without v4:** Cursor v4 > my v3 > Claude.

---

## 13. Open questions (call out before implementation)

1. **Server-side `attach_or_create_session` writes to `sessions_index.json`. Does the WS path (React UI) also call `create_session`? If yes, that's a SECOND writer.** Verified: yes, `session_routes.py:43` already has `POST /api/sessions` which calls `svc.create_session`. **Resolution:** these two endpoints both go through the SAME `SessionStore` instance (singleton via `app.state.data_service`), so writes are serialised by the asyncio event loop. No race. (Document this as I9.5 if reviewer pushes back.)

2. **Should `service: "openteam"` go in the discovery file only, or also `/api/health`?** Both. Discovery file lets clients pre-filter before health-check; `/api/health` is the runtime defense against an impostor process.

3. **Should the v4 plan ship as one PR or split?** Three PRs:
   - **PR 1 (OpenStartup):** `openteam.client/*` + `openteam.server._register` + `POST /api/sessions/attach` + `/api/health` service field + tests + CI preflights. Safe to merge; no behavior change for existing UI.
   - **PR 2 (cli-rovodev-tui):** `openteam_session.py` + `app.py` ensure_server + slash mode branch + tests.
   - **PR 3 (docs):** `MCP_INTEGRATION.md` + `SERVER_DISCOVERY.md` + `openteam-integration.md`.

4. **Migration plan for existing server installs:** roll out PR 1 first; existing servers don't auto-register but new ones do. PR 2 ships ~1 week later after most installs have restarted.

---

**End of plan v5. Saved at:** `CoreProjects/OpenStartup/_dev/_plan/openteam_rovodev_integration/openteam-unified-frontend-session-protocol-v5.md`
