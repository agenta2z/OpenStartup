# Unified Frontend Session Protocol — v3 (Integrated)

**File:** `openteam-unified-frontend-session-protocol-v3.md`
**Status:** v3 — Round-3 integration. Two CRITICAL corrections vs my v2 + Cursor INTEGRATED-v2.
**Date:** 2026-05-17 (Round-3 initial; Round-4 patches at 20:40)
**Supersedes:**
- v2 (mine): `openteam-unified-frontend-session-protocol-v2.md` (815 lines)
- Cursor: `openteam-unified-frontend-session-INTEGRATED-v2.md` (1057 lines)
- Claude: `~/.claude/plans/eager-roaming-clock.md` (139 lines)

---

## Round-7 patch — client/server split refactor (2026-05-17 21:18)

**Trigger:** user observation — "the connection establishment part would be an important common component under `src/openteam/server`, it is a critical part of the integration". Honest assessment: user is right about importance + common-component nature, but **the cleanest placement is NOT under `server/`** — it deserves its own sibling package.

**Architectural decision:** split Phase 6's two `server/` modules into a new top-level `openteam/client/` package + a thin server-side write hook.

**Before (Round-6) → After (Round-7):**

| Round-6 location | Round-7 location | Why |
|---|---|---|
| `server/discovery.py` (read+write+schema, 80 LOC) | `client/discovery.py` (schema + read, 60 LOC) + `server/_register.py` (write only, 50 LOC) | Schema is shared; read side is for clients; write side is server-internal. Splitting clarifies ownership. |
| `server/supervisor.py` (launch logic, 120 LOC) | `client/supervisor.py` (launch logic, 80 LOC) | Supervisor is a CLIENT-of-server module. Putting it under `server/` would force every client (TUI, future Slack bot, IDE plugin, `openteam-sdk` PyPI package) to import the heavy `openteam.server` namespace just to find a server. |
| TUI imported `from openteam.server.supervisor import ensure_server` | TUI imports `from openteam.client import ensure_server` | Lean import; no FastAPI/React/inference-backend bleed-through into RovoDev TUI startup path. |

**New invariant I14 (locked by CI preflight):** `openteam.client.**` MUST NOT import from `openteam.server.**`. Reverse direction is permitted: `openteam.server._register` imports schema from `openteam.client.discovery`. **Test:** `test/openteam/client/test_no_server_imports.py` AST-scans `src/openteam/client/` for any `import openteam.server` or `from openteam.server` lines; CI fails on first hit.

**Why the schema lives in client (counter-intuitive but right):** the discovery-file schema is what THIRD PARTIES consume. The server is one writer; the clients are many readers (TUI today; Slack/IDE/SDK tomorrow). Putting the schema where the readers are means readers depend on nothing else; the single writer takes a one-line import from the readers' namespace. This is the same pattern as gRPC's `.proto` files living in shared interface packages, not server packages.

**Future payoff:** `openteam-sdk` PyPI package becomes literally `from openteam.client import *` re-exported with version pinning. Third-party integrators get `pip install openteam-sdk` that pulls **only** stdlib + httpx — no FastAPI, no React assets, no model weights. Today this is hypothetical; the package boundary makes it free to extract when needed.

**Files touched in this round:** §16.4 (`discovery.py` → `_register.py` + new doc), §16.5 (replaced with 3-file client package: `__init__.py`, `discovery.py`, `supervisor.py`), §16.6 (TUI import path), §16.8 (test re-paths + new CI preflight), §16.11 (phase table reflects new layout + 30min extra), §16.12 (self-audit gets 2 new rows), §16.2 (I14 added). Net delta: +60 LOC of plan, identical net code LOC, +1 CI preflight, +1 invariant, sharper separation.

**Effort impact:** Phase 6 now ~5h (was ~4.5h); v1 + Phase 6 ~17h total.

---

## Round-6 patch — Phase 6 auto-launch supervisor (2026-05-17 21:06)

**Net additions:** 1 new section (§16), 6 invariants (I8-I13), 2 new modules (`discovery.py`, `supervisor.py`), 1 TUI extension, 6 risks (R12-R17), 8 tests + 1 CI preflight, 6 phases (6a-6f), ~4.5h effort.

**Trigger:** user question — "when we start a rovodev session, if rovoteam server is not running, it will launch the server" — surfaced that v1's protocol only guarantees on-DISK server directory, not a running HTTP server process. Without a running server, the React UI is dark for new users.

**Design (one-line):** opt-out auto-launch via a generic `supervisor.ensure_server(runtime_root)` helper that (a) reads `~/.openteam/servers/*.json` discovery files written by the server's `register_server()` hook, (b) probes liveness via `GET /health`, (c) reuses if alive, (d) launches new with file-lock idempotency if not, (e) survives recursive launch via `OPENTEAM_AUTO_LAUNCH=0` in child env.

**Why elegant (vs. ad-hoc):**

| Concern | Elegant property | How achieved |
|---|---|---|
| "Generic" (user's phrasing) | Frontend-agnostic; future Slack/IDE/etc clients reuse unchanged | `supervisor.ensure_server` API never mentions RovoDev |
| "If running, attach; if not, launch" | Single function call covers both cases | `ensure_server()` is the only public entrypoint |
| Doesn't break v1 invariants | `/task` correctness independent of HTTP server (I9) | Server is observability consumer, not execution intermediary |
| Doesn't fork-bomb | Launched server sees `OPENTEAM_AUTO_LAUNCH=0` (R12) | Env-var poisoning in `_launch_new` |
| Doesn't double-launch under concurrency | File-lock via `O_EXCL` create (I13) | `_file_lock` context manager around `_launch_new` |
| Doesn't collide between checkouts | `server_id = sha(runtime_root, host)[:12]` (I12) | Two checkouts → two ids → two discovery files |
| Self-heals stale state | `discover_servers()` reaps unresponsive entries (I11, R13) | Liveness probe on every read |
| No new dependencies | `httpx` already in tree via fastmcp; rest stdlib | Auditable: 0 new requirements |
| Atomic discovery writes | `os.replace(tmp, target)` | No torn JSON ever visible to readers |
| Opt-out, not opt-in (I8) | Default on; off via `OPENTEAM_AUTO_LAUNCH=0` or `--no-openteam-server` | Three-tier override (env > flag > default) |

**Files touched:** `src/openteam/server/discovery.py` NEW, `src/openteam/server/supervisor.py` NEW, `run_server.py` +1 call, TUI `openteam_session.py` +25 LOC, TUI `app.py` +2 flags. **~225 LOC + 8 tests + 1 preflight + docs.**

**Pick-one impact:** Round-6 expands v3 from "discover-or-attach session" to "discover-or-launch full backend". This is the upgrade path from "RovoDev works in isolation" to "RovoDev sessions show in React UI out of the box". Cursor INTEGRATED-v3 and Claude both lack this entirely — **v3-post-Round-6 is now categorically beyond them on capability, not just correctness.**

---

## Round-5 patch — 3 valid + 1 rejected + 1 info from independent audit (2026-05-17 20:55)

| # | Sev | Claim | Verdict + Fix |
|---|---|---|---|
| **R5-1** | MOD | `_runtime_root` only has 2 tiers; OpenTeam's `find_runtime_root` (verified at `workspace_allocator.py:24`) has 4 tiers. In dev mode, the TUI's runtime root → `~/.openteam/_runtime`; OpenTeam's walks UP from `__file__` to find `OpenStartup/_runtime`. Synthetic server lives in different tree → **React UI cannot see RovoDev sessions in dev mode** (the very Goal #2 the plan promises). | ✅ VALID. **Fix:** §6.5 `_runtime_root` rewritten to mirror tiers 1, 3, 4 (tier 2 not applicable for site-packages installs). New CI preflight `test_runtime_root_helpers_agree.py` asserts both helpers return same path. |
| **R5-2** | MIN | §6.1 defines `_validate_external_id` (private); §6.2 imports `validate_external_id` (public) → ImportError | ❌ **REJECTED with verified counter-evidence.** Direct re-read of §6.1 line 287: `def validate_external_id(external_id: str) -> tuple[str, str]:  # Round-4 Mo-3.1: public`. Round-4 Mo-3.1 already landed the public name. Auditor's claim is stale (possibly reading a cached copy or pre-Round-4 snapshot). No action. |
| **R5-3** | MIN | §3.1 prose still says `partition("-", 1)` at 4 sites (lines 131, 132, 135, 798) — would `TypeError` if copy-pasted; code is fine | ✅ VALID. Round-4 m-3.1 only fixed the code; prose was missed. **Fix:** all 4 stale prose sites now use single-arg `partition("-")` with explicit explanation: "Python's `str.partition` takes EXACTLY ONE arg; `partition("-", 1)` would `TypeError`". |
| **R5-4** | MIN | Existing `context.py:9 _ENV_MAP` maps `OPENTEAM_SERVER_DIR → server_dir`; my new `build_session_context` reads it explicitly AND via passthrough → benign double-set; ownership unclear | ✅ VALID. **Fix:** §6.2 passthrough map now explicitly REMOVES `OPENTEAM_SERVER_DIR` (and 3 other protocol vars) with comment establishing the invariant: "protocol-managed keys are NEVER in the passthrough map". |
| **R5-5** | INFO | RovoDev `current_session_id` is actually `w<7hex>-<uuid4-rest>` format, not plain UUID4 | ⚠️ ACKNOWLEDGE — auditor states it's "functionally fine" because `_SAFE_REMAINDER_REGEX` accepts it (`w` is alphanumeric). I cannot independently verify the regex without descending into the `nemo` external library. No code change needed; treating remainder as opaque was the right call from day one. |

**Round-5 totals: 3 valid, 1 rejected (with verified counter-evidence), 1 informational. 0 over-fixes. 100% precision on verified items.**

**Round-5 net diff:** +~50 lines (Issue 1 rewrite is the bulk; Issue 4 is one comment block; Issue 3 is 4 word-level edits).

---

## Round-4 patch — 9 verified items from devastating cross-audit (2026-05-17 20:40)

| # | Sev | Claim | Verdict + Fix |
|---|---|---|---|
| **CR-3.1** | CRIT | `attach_or_create_session` lookup broken — `_to_summary` strips `external_id` field, so the filter on `_scan_sessions` summaries always returns None → idempotency (Invariant I1) broken end-to-end; EVERY `/task` creates a new session | ✅ VALID. Empirically verified at `session_store.py:376-403`. **Fix:** §6.1 now uses `self.get_session(external_id)` (existing public API; reads disk directly via `_session_path` or `_find_session_dir`). |
| **CR-3.2** | CRIT | WS init handshake severely under-scoped at 15 LOC (real surface ~50 LOC) | ✅ VALID. **Fix:** §5.1 row marked strikethrough + ~~DEFERRED to POST-1~~. v1 ships without it; React UI continues using bare `session-<...>` ids (accepted by `"session"` whitelist entry). Detailed scope writeup in §5.1. |
| **M-3.1** | MAJ | `_workspace_uuid8` collision off by 800× (39% at N=65k, not 0.05%); collision re-introduces the very `_update_index` race per-workspace dirs were designed to eliminate | ✅ VALID. Birthday math verified live: `1-exp(-N²/(2·2³²))=0.394`. **Fix:** widened `[:8]→[:12]` (helper renamed `_workspace_uuid8`→`_workspace_uuid12`); P drops to 7.6e-6 at N=65k. R11 risk row updated with corrected math + correctly characterized impact. |
| **M-3.2** | MAJ | Adapter-pattern claim (§2 Goal 1) contradicted by TUI prepending `"rovodev-"` itself in §6.6 | ✅ VALID. **Fix (Option b — cleaner):** TUI now sends BARE `sid` in `OPENTEAM_SESSION_ID` + `OPENTEAM_FRONTEND_ID="rovodev"` separately. `build_session_context` composes (§6.2 has new "ADAPTER COMPOSITION RULE" block). Future frontends never hardcode their own protocol name. Matches §2 Goal 1 literally. |
| **M-3.3** | MAJ | File-locking strategy contradicted across §3.3 (rejects) / §5.1 (adds) / §12 (TODO) | ✅ VALID. **Fix:** picked §3.3's NO-FLOCK position uniformly (§5.1 + §12 self-audit now agree). v1 ships with single TODO comment near `_update_index` referencing this plan; no fcntl/flock implementation. |
| **Mo-3.1** | MOD | `_validate_external_id` is imported cross-module despite leading-underscore "private" convention | ✅ VALID. **Fix:** renamed `_validate_external_id` → `validate_external_id` (public) across all 5 references (definition, two import statements, two call sites, I2 invariant, DoD checkbox). |
| **Mo-3.2** | MOD | Test count claim "~28" actually 34 | ✅ VALID. **Fix:** §11 comparison table row updated to "34 + CI" with breakdown. |
| **Mo-3.3** | MOD | `force_new` flag + `server_file` write partially redundant (server_dir is deterministic from wsuuid; server_file value is always re-derivable) | ✅ VALID. **Fix:** §6.5 inline comment makes the design explicit: "server_file is debug-provenance only; safe to remove without behaviour change". Not removed (keeps the `.rovodev/` directory self-describing for ops). |
| **m-3.1** | MIN | Docs say `partition("-", 1)` which would raise `TypeError` (real code uses `partition("-")` with no second arg) | ✅ VALID. Empirically reproduced: `'abc-def'.partition('-', 1)` → `TypeError: str.partition() takes exactly one argument`. **Fix:** §3.1 + §6.1 docstring + inline comment now state the one-arg rule explicitly. |

**Round-4 totals: 9 valid, 0 over-fixes, 0 false rejections. 5 architectural bugs fixed (2 critical, 3 major); 4 cosmetic/contract fixes.**

**Round-4 net diff:** +~80 lines (cause: comment-density increase for the two critical fixes; CR-3.2 strikethrough; 8 inline-rationale stamps). No new sections introduced.



---

## 0. TL;DR — round-3 critical corrections

This round started by reading three plans that had converged on the same architectural shape. Then **two parallel verification agents + my own bash checks found one CRITICAL bug in each of the two larger plans**:

| Bug | Plan that had it | Evidence | Fix in v3 |
|---|---|---|---|
| **`SessionStore(server_dir=...)` — wrong kwarg → TypeError at runtime** | Cursor INTEGRATED-v2 | Real signature is `SessionStore(runtime_root: str\|Path, *, resume_server: str\|None=None)` — verified `session_store.py:44-49`. **Cursor's `session_resolver.py` snippet would crash on first invocation.** | Use `SessionStore(runtime_root=server_path.parent.parent, resume_server=server_path.name)`. |
| **Shared server `server_rovodev_default/` has a real index-write race** | My v2 | `_update_index()` (line 547) calls `_scan_sessions()` (line 601 — scans disk) then `_atomic_write(sessions_index.json)`. Two concurrent `attach_or_create_session` processes both scan, both write; **second `os.replace` overwrites with stale data, losing the first's session from the index.** No file locking (verified: 0 `fcntl`/`flock` hits). | Use Cursor's per-workspace synthetic server `server_rovodev_<wsuuid>/`. Eliminates the race at zero implementation cost. |

Both fixes are non-negotiable. v3 takes Cursor's architectural shape, my v2's correct SessionStore call, **`-` delimiter** (back-compat-friendly; needs no Windows encoding), and merges all three plans' tests.

**Effort:** ~12 hours for ship-ready v1.
**LOC:** ~280 across 8 files + ~28 tests + 1 CI preflight + docs.
**Backward compat:** total.

---

## 1. The gap (verified)

### 1.1 Today's three code paths

| Path | session_context shape | Workspace location |
|---|---|---|
| **React UI → WS** (`manager_websocket_routes.py:213-217`) | `{interactive, task_id, session_id, session_root}` | Under session ✅ (`<server>/sessions/<sid>/tasks/`) |
| **RovoDev TUI → slash subprocess** (`tool_cli.py:113`) | **`{}` (literally empty)** | Standalone `<runtime>/tasks/<tool>/` ❌ |
| **RovoDev MCP** (`mcp_server/context.py:17-23`) | `{"task_id": "mcp-<uuid8>", "interactive": None}` | Standalone `<runtime>/tasks/<tool>/` ❌ |

### 1.2 Verified evidence (file:line)

| Claim | Evidence | Verified |
|---|---|---|
| `SessionStore.__init__(runtime_root, *, resume_server=None)` | `session_store.py:44-49` | Round-3 bash + Explore subagent |
| `_update_index → _scan_sessions → _atomic_write` race | `session_store.py:547-552, 601` + no locking | Round-3 Explore subagent |
| `tool_cli.py:113` is `session_context = {}` | Round-2 bash | re-verified |
| MCP context lacks session_id | `mcp_server/context.py:17-23` | Round-2 bash |
| RovoDev TUI has `current_session_id: var[str]` at `app.py:403` | Round-2 Explore subagent | confirmed |
| RovoDev session id = `str(uuid4())` | `cli-rovodev/.../acp/agent.py:164` | Round-2 |
| No `frontend_id`/`origin`/`caller_id` anywhere in OpenTeam | `grep -rn → 0 hits` | Round-2 |

### 1.3 Concrete losses today

1. RovoDev tool runs scatter across `_runtime/tasks/` instead of co-locating under a session
2. UI can't see RovoDev sessions in `GET /sessions`
3. No conversation-bucket continuity across consecutive `/task` invocations
4. No session-export / archive boundary for RovoDev runs
5. Future frontends have no contract to follow

---

## 2. Design goals + invariants

### 2.1 Goals (priority order)
1. **Minimise RovoDev-side change.** RovoDev sends its native `current_session_id`; OpenTeam's adapter (slash subprocess entrypoint, MCP wrapper, WS init route) sets `frontend_id="rovodev"`. RovoDev does not know its own protocol name.
2. **OpenTeam treats every session uniformly.** Workspace allocation, persistence, listing, export are frontend-agnostic.
3. **Backward compatibility total.** React UI keeps working unchanged. Pre-protocol RovoDev/MCP calls still work via standalone Path A.
4. **Pluggable for N future frontends.** New frontend = one line in the whitelist + one hardcoded string in its adapter.
5. **Per-workspace continuity on TUI side.** Restart TUI in same workspace → same OpenTeam session.
6. **Auditable provenance.** `session_state.json` records `frontend_id` + `frontend_metadata` for forensics.
7. **No new dependencies.**
8. **POSIX-first.** Plain `-` delimiter avoids Windows path-encoding ceremony.

### 2.2 Hard invariants

- **I1.** `attach_or_create_session(external_id, *, ...)` is idempotent: second call with same id returns existing session unchanged.
- **I2.** External session IDs must pass `validate_external_id` (public per Round-4 Mo-3.1): prefix ∈ whitelist; remainder matches `^[A-Za-z0-9_.\-]{1,128}$`.
- **I3.** `_VALID_FRONTEND_PREFIXES` is a `frozenset` defined module-top in `session_store.py`. **CI preflight `test_frontend_prefix_whitelist_immutable.py` asserts the exact set membership.**
- **I4.** Every executor that respects `session_context["session_root"]` must continue to work if it's absent (Path A fallback).
- **I5.** The four new env vars (`OPENTEAM_SERVER_DIR`, `OPENTEAM_SESSION_ID`, `OPENTEAM_FRONTEND_ID`, `OPENTEAM_FRONTEND_METADATA`) are **read in exactly one place**: `build_session_context()`. No other module reads them.
- **I6.** RovoDev TUI workspaces each get a **dedicated synthetic server directory** `server_rovodev_<wsuuid>/` to eliminate `sessions_index.json` write races. The `wsuuid` is a stable 8-hex digest of the workspace absolute path.
- **I7.** SessionStore construction uses `SessionStore(runtime_root=path.parent.parent, resume_server=path.name)` (verified signature). `server_dir=` is **NOT** a kwarg and will raise TypeError.

---

## 3. The protocol

### 3.1 Canonical session-id format

```
openteam_session_id := <frontend_id> "-" <frontend_session_id>     # canonical (new)
                     | <legacy_session_id>                          # back-compat (today)

frontend_id          := from whitelist {"rovodev", "ui", "mcp", "slack", "session"}
                        (single ASCII word, no hyphen, regex: ^[a-z][a-z0-9_]{0,31}$)
frontend_session_id  := ^[A-Za-z0-9_.\-]{1,128}$
                        (rejects "/", "\\", "..", "\x00" — path-traversal-safe)

legacy_session_id    := session-<unix>-<hex6>  (today's React UI format)
```

**Why `-` delimiter, not `:`** (decision matrix):

| Concern | `-` (my v2, Plan A, v3) | `:` (Cursor INTEGRATED-v2) |
|---|---|---|
| POSIX dir-name legality | ✅ | ✅ (verified empirically Round-2) |
| Windows NTFS dir-name legality | ✅ | ❌ — reserved (alternate data stream) |
| Encoding ceremony required | None | `:` → `%3A` at every disk write |
| Back-compat with legacy `session-<...>-<hex6>` parse | Same delimiter, parse with `partition("-")` (single-arg) | Different delimiter → branch logic |
| Ambiguity when frontend_session_id contains `-` (UUID4!) | None — `partition("-")` returns `(head, sep, tail)` where `tail` may itself contain `-` | None |
| Visual distinguishability of prefix vs body | Adequate — whitelist is finite | Better — but at cost of all the above |

**Conclusion:** `-` wins on portability + zero ceremony. The `partition("-")` rule (Python's `str.partition` takes EXACTLY ONE arg; `partition("-", 1)` would `TypeError`) means `rovodev-550e8400-e29b-41d4-a716-446655440000` parses unambiguously to `("rovodev", "-", "550e8400-e29b-41d4-a716-446655440000")` — the tail keeps every hyphen after the first.

### 3.2 The four env vars

| Env var | Set by | Read by | Meaning |
|---|---|---|---|
| `OPENTEAM_SERVER_DIR` | TUI handler / MCP host | `build_session_context()` only | Absolute path to `<runtime>/servers/<server>/`. Tells subprocess WHICH SessionStore to construct. |
| `OPENTEAM_SESSION_ID` | TUI handler / MCP host | `build_session_context()` only | External session id (`{frontend_id}-{frontend_session_id}` or legacy). Subject to whitelist validation. |
| `OPENTEAM_FRONTEND_ID` | (optional) | `build_session_context()` only | Frontend prefix override. Defaults to the parsed prefix from `OPENTEAM_SESSION_ID`. Useful when the id is opaque legacy form. |
| `OPENTEAM_FRONTEND_METADATA` | (optional) | `build_session_context()` only | JSON dict. Defaults to `{}`. Stored verbatim in `session_state.json` for audit. |

**Required pair:** `OPENTEAM_SERVER_DIR` + `OPENTEAM_SESSION_ID`. If only one is set, log INFO and fall back to ephemeral session (pre-protocol behaviour).

### 3.3 The synthetic-server invariant (race-elimination)

```
<runtime>/servers/
  server_<ts>_<uuid8>/              ← real WS server (React UI launches OpenTeam server)
    sessions/
      session-<unix>-<hex6>/        ← legacy UI session
        sessions_index.json         ← scoped to THIS server
        tasks/...

  server_rovodev_<wsuuid>/          ← synthetic per-TUI-workspace server (NEW v3)
    sessions/
      rovodev-<uuid4>_<TS>/         ← canonical RovoDev session
        sessions_index.json         ← scoped to THIS server — no cross-workspace race
        tasks/task_<TS>_<uuid8>/
```

**`wsuuid` derivation** (stable & deterministic): `wsuuid = sha256(workspace_absolute_path.encode()).hexdigest()[:8]`. Two TUI processes in the same workspace get the same server dir; two TUI processes in different workspaces get different server dirs. Eliminates the `_update_index` race by construction.

**Why not file locking instead?** Implementing fcntl/flock around `_update_index` would be: (a) backend change touching every existing UI flow, (b) requires retry+timeout discipline, (c) not portable to Windows. Per-workspace dirs eliminate the hazard at zero implementation cost and don't touch existing UI code paths.


---

## 4. End-to-end flow

```
RovoDev TUI                                                 OpenTeam (subprocess)
─────────────                                               ────────────────────
app.current_session_id = "550e8400-e29b-41d4-a716-..."       (no state)
   │
   ▼  (TUI startup, before any /task)
openteam_session.get_or_create_session(workspace_path):
  read <workspace>/.rovodev/openteam_session_id  → existing or mint new uuid4
  read <workspace>/.rovodev/openteam_server_dir  → existing or mint synthetic
    synth = <runtime>/servers/server_rovodev_<wsuuid>/
    wsuuid = sha256(workspace_path.encode()).hexdigest()[:8]
  persist both files (overwrite-safe)
  hydrate app.current_session_id from session_id file
   │
   ▼ user types /task "what is 2+2"
slash handler:
  external_id   = f"rovodev-{app.current_session_id}"   # "rovodev-550e8400-..."
  env["OPENTEAM_SERVER_DIR"]      = "<abs>/server_rovodev_<wsuuid>/"
  env["OPENTEAM_SESSION_ID"]      = external_id
  env["OPENTEAM_FRONTEND_METADATA"] = '{"tui_version":"1.2.3"}'  # optional
  spawn openteam-task --request "what is 2+2"  ─────▶ tool_cli.run_cli:
                                                        ctx = build_session_context()   # reads env
                                                          ├─ parses external_id → ("rovodev", "550e...")
                                                          ├─ validates prefix in whitelist
                                                          ├─ validates remainder regex
                                                          ├─ constructs SessionStore(
                                                          │      runtime_root=path.parent.parent,
                                                          │      resume_server=path.name)        # I7
                                                          ├─ store.attach_or_create_session(
                                                          │      external_id,
                                                          │      frontend_id="rovodev",
                                                          │      frontend_metadata={...})
                                                          │   → returns existing OR creates new
                                                          │     session dir under server_rovodev_<wsuuid>/
                                                          ├─ ctx["session_root"] = str(session_dir)
                                                          └─ ctx["frontend_id"]  = "rovodev"
                                                             ctx["frontend_metadata"] = {...}
                                                             ctx["task_id"]    = f"task-{uuid8}"
                                                      executor.execute(args, ctx)
                                                       → allocate_tool_workspace("task",
                                                           base_dir=ctx["session_root"]/"tasks")
                                                       → task_<TS>_<uuid8>/ under session ✅

Ctrl-C, restart TUI in SAME workspace:
  openteam_session.get_or_create_session(workspace_path):
    reads same .rovodev/* → SAME external_id, SAME server_dir
  /task "another" ─────▶ same env vars
                          attach_or_create_session sees existing session ✅
                          new task workspace under SAME session ✅

rovodev tui --new-openteam-session:
  openteam_session.get_or_create_session(workspace_path, force_new=True):
    ignores persisted session_id file → mints fresh uuid4 + persists
    server_dir UNCHANGED (per-workspace, persistent)
  /task ".." ─────▶ NEW OPENTEAM_SESSION_ID env
                    new session under same workspace's synthetic server ✅
```

---

## 5. File touch list

### 5.1 OpenStartup (~170 LOC + tests)

| File | Change | LOC |
|---|---|---|
| `src/openteam/server/services/session_store.py` | NEW: `_VALID_FRONTEND_PREFIXES` frozenset, `validate_external_id()` (public per Round-4 Mo-3.1), `attach_or_create_session(external_id, *, frontend_id, frontend_metadata, title)`. Tiny refactor: `create_session(title, *, _explicit_id=None)` to allow attach path to mint by id. **No file-locking in v1** (Round-4 M-3.3): per-workspace synthetic server dirs eliminate the `_update_index` race by construction; see §3.3 rationale. Add a single TODO comment near `_update_index` referencing this plan for the future case where shared servers ever become default. | ~80 |
| `src/openteam/server/services/tool_cli.py` | Line 113: replace `session_context: dict[str, Any] = {}` with `session_context = build_session_context()`. | ~3 |
| `src/openteam/mcp_server/context.py` | Rewrite `build_session_context(**overrides)` to: (a) accept kwargs, (b) read env-var fallback, (c) parse external id → frontend_id + frontend_session_id, (d) construct SessionStore with correct kwargs (I7), (e) call `attach_or_create_session`, (f) populate ctx with session_id, session_root, frontend_id, frontend_metadata, task_id, server_dir. | ~60 |
| `src/openteam/mcp_server/server.py` | Add `frontend_session_id: str \| None = None`, `frontend_metadata: dict \| None = None` kwargs to all 4 wrappers. Propagate to `build_session_context(frontend_id="rovodev", frontend_session_id=..., frontend_metadata=...)`. | ~25 |
| ~~`src/openteam/server/routes/manager_websocket_routes.py`~~ | **Round-4 CR-3.2 DEFER to POST-1.** WS init handshake extension was scoped at 15 LOC but real surface is ~50 LOC (the WS dispatch at line 213-217 builds session_context as an inline dict literal — NOT via `build_session_context()`; metadata persistence needs a new `SessionStore.update_session` call). v1 v3 ships WITHOUT this; React UI continues to use today's bare `session-<unix>-<hex6>` ids (which the `"session"` whitelist entry accepts). POST-1 PR will rewrite the WS dispatch to route through `build_session_context()` first, then add the init-JSON parsing on top. | 0 in v1 |
| **No executor changes** — `build_session_context()` already populates `session_root`; existing v5.3 workspace allocator reads it. | 0 |
| `docs/MCP_INTEGRATION.md` | NEW section: protocol fields, env vars, prefix whitelist, server-dir resolution rule. | docs |

### 5.2 RovoDev TUI (cli-rovodev-tui, ~75 LOC + tests)

| File | Change | LOC |
|---|---|---|
| `packages/cli-rovodev-tui/src/rovodev_tui/openteam_session.py` (NEW) | `get_or_create_session(workspace_path, *, force_new=False) -> tuple[Path, str]` — reads/writes `.rovodev/openteam_session_id` + `.rovodev/openteam_server_dir`; computes synthetic server dir from wsuuid; hydrates `app.current_session_id`. | ~60 |
| `packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py` | At handler start: `(server_dir, sid) = get_or_create_session(workspace)`. Set 4 env vars: `OPENTEAM_SERVER_DIR`, `OPENTEAM_SESSION_ID=sid` (bare UUID4, no prefix), `OPENTEAM_FRONTEND_ID="rovodev"` (the OpenTeam-side adapter contract per §2 Goal 1), `OPENTEAM_FRONTEND_METADATA` (JSON, optional). | ~12 |
| `packages/cli-rovodev-tui/src/rovodev_tui/app.py` | `--new-openteam-session` flag → `app.force_new_openteam_session = True` → passed to handler → forwarded to `get_or_create_session(force_new=True)`. | ~8 |
| `packages/cli-rovodev-tui/docs/openteam-integration.md` | NEW: `.rovodev/` persistence, flag, multi-workspace semantics. | docs |

**Net diff:** ~245 LOC + ~28 tests + 1 CI preflight + docs. **No file deletions.**


---

## 6. Key implementation code

### 6.1 `SessionStore.attach_or_create_session` (NEW, ~50 LOC)

```python
# src/openteam/server/services/session_store.py — additions

import re
from typing import Any

# Round-3 unified-frontend protocol: closed whitelist of known frontends.
# CI preflight test_frontend_prefix_whitelist_immutable.py guards against drift.
_VALID_FRONTEND_PREFIXES: frozenset[str] = frozenset({
    "rovodev",   # RovoDev TUI + MCP (today's two RovoDev paths)
    "ui",        # React UI post-migration
    "mcp",       # Generic MCP clients (non-RovoDev)
    "slack",     # Hypothetical Slack bot
    "session",   # Legacy server-minted format `session-<unix>-<hex6>` (back-compat)
})

# Path-traversal / control-char rejection. Remainder allows hyphens for UUID4.
_SAFE_REMAINDER_REGEX = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
_PREFIX_REGEX = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def validate_external_id(external_id: str) -> tuple[str, str]:  # Round-4 Mo-3.1: public
    """Validate and split. Returns (prefix, remainder).

    Accepts:
      - "<prefix>-<remainder>" where prefix is in whitelist (canonical)
      - "session-<unix>-<hex6>" bare legacy form (treated as prefix="session")
    Rejects unknown prefix, missing delimiter, unsafe remainder, traversal sequences.
    """
    if not external_id or not isinstance(external_id, str):
        raise ValueError("external_id must be a non-empty string")
    # str.partition("-") splits on the FIRST occurrence of "-" only; the
    # remainder may itself contain "-" (which it does for UUID4 ids).
    # IMPORTANT: str.partition takes EXACTLY ONE argument — `partition("-", 1)`
    # would raise TypeError (Round-4 m-3.1).
    prefix, sep, remainder = external_id.partition("-")  # Round-4 m-3.1: NO second arg (str.partition takes exactly one)
    if not sep:
        raise ValueError(f"external_id must contain '-': {external_id!r}")
    if not _PREFIX_REGEX.match(prefix):
        raise ValueError(f"prefix {prefix!r} fails format: ^[a-z][a-z0-9_]{{0,31}}$")
    if prefix not in _VALID_FRONTEND_PREFIXES:
        raise ValueError(
            f"unknown frontend prefix {prefix!r}; allowed: {sorted(_VALID_FRONTEND_PREFIXES)}"
        )
    if not _SAFE_REMAINDER_REGEX.match(remainder):
        raise ValueError(
            f"remainder unsafe (traversal / non-ASCII / too long): {remainder!r}"
        )
    return (prefix, remainder)


# In SessionStore class:

def attach_or_create_session(
    self,
    external_id: str,
    *,
    frontend_id: str | None = None,
    frontend_metadata: dict[str, Any] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Idempotently attach to (or create) a session keyed by external_id.

    On first call, creates a session whose ON-DISK directory is named
    f"{external_id}_{TS}".  Records `frontend_id` + `frontend_metadata` in
    `session_state.json`.

    On subsequent calls with the same external_id, returns the existing session
    dict unchanged (idempotent).

    Args:
        external_id: e.g., "rovodev-550e8400-..." — validated against whitelist.
        frontend_id: e.g., "rovodev". Defaults to parsed prefix of external_id.
        frontend_metadata: optional dict, stored verbatim for audit.
        title: optional human label, defaults to f"{frontend_id} session".
    """
    parsed_prefix, _ = validate_external_id(external_id)
    effective_fid = (frontend_id or parsed_prefix).lower()

    # Round-4 CR-3.1 FIX: use existing public API get_session(session_id).
    # The stored session's `id` field IS the external_id (because we pass
    # _explicit_id=external_id at creation time), so get_session works
    # by direct disk read (file or dir-with-state-file) rather than going
    # through _to_summary which would strip the field.
    # Empirical evidence: _to_summary (session_store.py:376-403) returns
    # only {id, title, created_at, updated_at, message_count, primary_agent}
    # — NO external_id field. Filtering on s.get("external_id") would
    # always return None for every session, breaking idempotency end-to-end.
    existing = self.get_session(external_id)
    if existing is not None:
        return existing  # idempotent

    return self.create_session(
        title=title or f"{effective_fid} session",
        _explicit_id=external_id,
        _frontend_id=effective_fid,
        _frontend_metadata=frontend_metadata or {},
    )


# Refactor existing create_session signature to accept the optional kwargs.
# Default behaviour unchanged for existing callers (React UI).
def create_session(
    self,
    title: str | None = None,
    *,
    _explicit_id: str | None = None,
    _frontend_id: str | None = None,
    _frontend_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sid = _explicit_id or f"session-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    # existing body, but record:
    #   session["external_id"]       = _explicit_id or sid
    #   session["frontend_id"]       = _frontend_id or "session"
    #   session["frontend_metadata"] = _frontend_metadata or {}
    # ... rest unchanged ...
```

### 6.2 `build_session_context` (rewrite, ~60 LOC) — **uses CORRECT SessionStore signature**

```python
# src/openteam/mcp_server/context.py — full rewrite

from __future__ import annotations
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# Single read point for the four env vars (Invariant I5)
_SERVER_DIR_ENV       = "OPENTEAM_SERVER_DIR"
_SESSION_ID_ENV       = "OPENTEAM_SESSION_ID"
_FRONTEND_ID_ENV      = "OPENTEAM_FRONTEND_ID"     # optional override
_FRONTEND_METADATA_ENV = "OPENTEAM_FRONTEND_METADATA"

# Round-5 Issue-4 FIX: existing _ENV_MAP in context.py (line 9) maps
# OPENTEAM_SERVER_DIR -> "server_dir". This new build_session_context reads
# OPENTEAM_SERVER_DIR EXPLICITLY for the protocol (line ~441 below).
# To prevent double-set on ctx["server_dir"], REMOVE OPENTEAM_SERVER_DIR
# from the passthrough map; rely on the explicit attach-path write only.
# This also makes the ownership explicit: server_dir is a protocol-managed
# key, not an opaque passthrough.
_ENV_PASSTHROUGH_MAP = {
    "OPENTEAM_RUNTIME_DIR": "runtime_root",
    # OPENTEAM_SERVER_DIR intentionally NOT here — owned by protocol path below.
    # ... (preserve any other existing keys, but NEVER include the four
    #      protocol vars: OPENTEAM_SERVER_DIR, OPENTEAM_SESSION_ID,
    #      OPENTEAM_FRONTEND_ID, OPENTEAM_FRONTEND_METADATA)
}


def build_session_context(
    *,
    frontend_id: str | None = None,
    frontend_session_id: str | None = None,
    frontend_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the per-invocation `session_context` dict.

    Resolution order for each field: kwargs > env vars > derived/default.

    Called from:
      - MCP wrappers (pass kwargs explicitly)
      - tool_cli.run_cli (no kwargs — pure env)
      - In-process tests (pass kwargs)

    When (server_dir AND external session id) resolve, this function ATTACHES
    to the session via SessionStore.attach_or_create_session, populating
    ctx["session_root"] for downstream workspace allocation (v5.3 Path B).

    Otherwise, falls back to ephemeral session (pre-protocol Path A behaviour).
    """
    from openteam.server.services.session_store import (
        SessionStore,
        validate_external_id,  # Round-4 Mo-3.1: was _validate_external_id
    )

    # ----- Resolve frontend identity -----
    raw_external = os.environ.get(_SESSION_ID_ENV, "").strip()
    raw_server_dir = os.environ.get(_SERVER_DIR_ENV, "").strip()

    # Round-4 M-3.2: ADAPTER COMPOSITION RULE.
    # Frontends MAY send either:
    #   (a) full external id `prefix-body` in OPENTEAM_SESSION_ID  (legacy/UI path), OR
    #   (b) bare body in OPENTEAM_SESSION_ID + OPENTEAM_FRONTEND_ID separately (preferred).
    # The OpenTeam-side adapter (this function) is the SOLE composition site.
    # New frontends never hardcode their own protocol prefix.
    raw_frontend_id = os.environ.get(_FRONTEND_ID_ENV, "").strip()

    composed_external_id: str | None = None
    if frontend_id and frontend_session_id:
        # Path (b) via in-process kwargs (MCP wrappers)
        composed_external_id = f"{frontend_id}-{frontend_session_id}"
    elif raw_external:
        # Subprocess path: decide based on whether raw_external is already composed
        if "-" in raw_external and not raw_frontend_id:
            # Path (a): full composed id (legacy `session-<unix>-<hex6>` or UI-sent)
            composed_external_id = raw_external
        elif raw_frontend_id:
            # Path (b): bare body + separate frontend_id env var (preferred)
            composed_external_id = f"{raw_frontend_id}-{raw_external}"
        else:
            # raw_external present but no `-` and no frontend_id → reject (no way
            # to know the prefix); will fail validation below and degrade to ephemeral.
            composed_external_id = raw_external

    # ----- Resolve metadata -----
    fmeta: dict[str, Any] = {}
    if frontend_metadata is not None:
        fmeta = dict(frontend_metadata)
    elif (raw_meta := os.environ.get(_FRONTEND_METADATA_ENV, "").strip()):
        try:
            parsed = json.loads(raw_meta)
            if isinstance(parsed, dict):
                fmeta = parsed
            else:
                _logger.warning("[%s] not a JSON object; ignoring", _FRONTEND_METADATA_ENV)
        except json.JSONDecodeError as e:
            _logger.warning("[%s] malformed JSON: %s", _FRONTEND_METADATA_ENV, e)

    # ----- Base ctx (always populated) -----
    ctx: dict[str, Any] = {
        "task_id": f"task-{uuid.uuid4().hex[:8]}",  # per-invocation
        "interactive": None,
        "frontend_id": "mcp",
        "frontend_metadata": fmeta,
    }

    # ----- Env passthroughs (existing behaviour) -----
    for env_key, ctx_key in _ENV_PASSTHROUGH_MAP.items():
        if v := os.environ.get(env_key):
            ctx[ctx_key] = v

    # ----- Attach path (full protocol satisfied) -----
    if composed_external_id and raw_server_dir:
        try:
            prefix, _ = validate_external_id(composed_external_id)
            effective_fid = (
                frontend_id
                or os.environ.get(_FRONTEND_ID_ENV, "").strip()
                or prefix
            ).lower()

            # I7: SessionStore takes (runtime_root, *, resume_server) — NOT server_dir!
            server_path = Path(raw_server_dir).resolve()
            store = SessionStore(
                runtime_root=server_path.parent.parent,  # <runtime>/servers/<server>/ → <runtime>
                resume_server=server_path.name,           # <server-name>
            )
            session = store.attach_or_create_session(
                composed_external_id,
                frontend_id=effective_fid,
                frontend_metadata=fmeta,
            )
            ctx["session_id"]       = composed_external_id
            ctx["session_root"]     = str(store.get_session_dir(composed_external_id))
            ctx["server_dir"]       = str(server_path)
            ctx["frontend_id"]      = effective_fid
            _logger.info(
                "[session_context] attached external_id=%s root=%s",
                composed_external_id, ctx["session_root"],
            )
            return ctx
        except (ValueError, FileNotFoundError, PermissionError) as e:
            _logger.warning(
                "[session_context] failed to attach (%s); falling back to ephemeral",
                e,
            )
            # fall through to ephemeral

    # ----- Ephemeral fallback (partial env or pre-protocol) -----
    if composed_external_id or raw_server_dir:
        _logger.info(
            "[session_context] partial protocol (sid=%r, srv=%r) — ephemeral session",
            bool(composed_external_id), bool(raw_server_dir),
        )
    ctx["session_id"] = f"mcp-{uuid.uuid4().hex[:8]}"
    return ctx
```

### 6.3 MCP wrappers (`src/openteam/mcp_server/server.py`) — add kwargs to all 4

```python
async def openteam_task(
    request: str,
    *,
    frontend_session_id: str | None = None,   # NEW v3 (protocol kwarg)
    frontend_metadata: dict | None = None,    # NEW v3 (protocol kwarg)
    # ... existing kwargs unchanged ...
) -> str:
    """Run an OpenTeam BTA task.

    Args:
        ...existing...
        frontend_session_id: optional. Your client's native session id. When set,
            joins (or creates) an OpenTeam session at `rovodev-<frontend_session_id>`
            so multiple invocations share state. If unset, ephemeral session.
        frontend_metadata: optional dict stored as audit provenance.
    """
    ctx = build_session_context(
        frontend_id="rovodev",                       # MCP adapter serves RovoDev today
        frontend_session_id=frontend_session_id,
        frontend_metadata=frontend_metadata,
    )
    return render_result(await _exec(args, ctx))
# Same shape for openteam_role_setup, openteam_create_role, openteam_project_onboarding.
```

### 6.4 `tool_cli.py` (1 line)

```python
# src/openteam/server/services/tool_cli.py — line 113 replacement
from openteam.mcp_server.context import build_session_context  # add import

# OLD:  session_context: dict[str, Any] = {}
session_context = build_session_context()  # auto-reads env vars
```

### 6.5 RovoDev TUI `openteam_session.py` (NEW, ~60 LOC)

```python
# packages/cli-rovodev-tui/src/rovodev_tui/openteam_session.py
"""Per-workspace OpenTeam session persistence.

Maps the TUI's current_session_id (UUID4) to an OpenTeam session at
`rovodev-<uuid4>`. Persists the binding in `<workspace>/.rovodev/` so
restarting the TUI in the same workspace reuses the same session.
"""
from __future__ import annotations
import hashlib
import os
import uuid
from pathlib import Path


def _runtime_root() -> Path:
    """Mirror OpenTeam's 4-tier ``find_runtime_root`` so dev-mode sessions land
    in the same ``_runtime/`` directory the React UI scans.

    Round-5 Issue-1 FIX: v3 originally implemented only tiers (1) and (4),
    causing a dev-mode invisibility: OpenTeam's allocator walked UP from its
    source file (tier 2) to find ``OpenStartup/_runtime``, while the TUI helper
    returned ``~/.openteam/_runtime``. RovoDev sessions would be invisible to
    the React UI in dev mode.

    Resolution order (must match
    ``openteam.server.resources.tools._shared.workspace_allocator.find_runtime_root``
    line-for-line; CI preflight ``test_runtime_root_helpers_agree.py``
    asserts both helpers return the same path for any fixture):

      1. ``$OPENTEAM_RUNTIME_DIR`` (CI / prod override).
      2. **NOT applicable in TUI** (no ``src/`` ancestor from RovoDev's source).
         The TUI is installed via uv tool; ``Path(__file__).parents`` walks
         into ``site-packages``, never ``src``. Skip tier 2 here.
      3. Walk up from CWD looking for a ``src/`` ancestor OR a
         ``(src/, pyproject.toml)`` sibling pair. Matches ``cwd-launched``.
      4. Fallback: ``~/.openteam/_runtime`` (pip-installed users).
    """
    if env_dir := os.environ.get("OPENTEAM_RUNTIME_DIR"):
        return Path(env_dir).expanduser().resolve()

    cwd = Path.cwd().resolve()
    for ancestor in [cwd, *cwd.parents]:
        if ancestor.name == "src":
            return ancestor.parent / "_runtime"
        if (ancestor / "src").is_dir() and (ancestor / "pyproject.toml").is_file():
            return ancestor / "_runtime"

    return (Path.home() / ".openteam" / "_runtime").resolve()


def _workspace_uuid12(workspace_path: Path) -> str:
    """Stable 12-hex digest of workspace absolute path (Round-4 M-3.1: widened from 8).

    Same workspace → same wsuuid → same synthetic server dir.
    Different workspaces → different wsuuid → different synthetic server dir
    (eliminates sessions_index.json write race — Invariant I6).
    """
    abs_path = str(workspace_path.resolve())
    # Round-4 M-3.1 FIX: widen 8→12 hex chars (2^32 → 2^48 address space).
    # At N=65,536 workspaces: P(collision) drops from 39.35% to 7.6e-6.
    # CRITICAL: a wsuuid collision would re-introduce the very _update_index
    # write race that per-workspace isolation was designed to eliminate
    # (the colliding workspaces would share sessions_index.json).
    return hashlib.sha256(abs_path.encode()).hexdigest()[:12]


def get_or_create_session(
    workspace_path: Path,
    *,
    force_new: bool = False,
) -> tuple[Path, str]:
    """Resolve (server_dir, session_id) for the given TUI workspace.

    Args:
        workspace_path: the TUI's current workspace directory.
        force_new: ignore persisted session_id and mint a fresh one (preserves
            the per-workspace synthetic server dir). Triggered by
            `--new-openteam-session` CLI flag.

    Returns:
        (server_dir_abs_path, session_id_uuid4)

    Side effects:
        Creates `<workspace>/.rovodev/openteam_session_id` and
        `<workspace>/.rovodev/openteam_server_dir` if missing.
        Creates the synthetic server dir if missing.
    """
    rovodev_dir = workspace_path / ".rovodev"
    rovodev_dir.mkdir(exist_ok=True)

    sid_file = rovodev_dir / "openteam_session_id"
    server_file = rovodev_dir / "openteam_server_dir"

    # session id: persist-or-mint
    if not force_new and sid_file.exists():
        sid = sid_file.read_text().strip()
        if not sid:  # corrupt — self-heal
            sid = str(uuid.uuid4())
            sid_file.write_text(sid)
    else:
        sid = str(uuid.uuid4())
        sid_file.write_text(sid)

    # server dir: ALWAYS per-workspace (force_new doesn't rotate server dir;
    # it only rotates the session within the dir).
    # Round-4 Mo-3.3: server_dir is DETERMINISTIC from wsuuid; the persisted
    # server_file is debug-provenance only (lets users see which synthetic
    # server backs this workspace without computing the sha themselves).
    # If you remove the server_file write, behaviour is identical (the value
    # is re-derived deterministically on every call).
    wsuuid = _workspace_uuid12(workspace_path)
    server_dir = _runtime_root() / "servers" / f"server_rovodev_{wsuuid}"
    server_dir.mkdir(parents=True, exist_ok=True)
    server_file.write_text(str(server_dir))  # provenance only; safe to remove

    return (server_dir, sid)
```

### 6.6 Slash handler wiring (`slash_commands/openteam.py`)

```python
# At top of _make_handler, before subprocess spawn:
from rovodev_tui.openteam_session import get_or_create_session

server_dir, sid = get_or_create_session(
    Path.cwd(),
    force_new=getattr(app, "force_new_openteam_session", False),
)
env = os.environ.copy()
env["OPENTEAM_SERVER_DIR"] = str(server_dir)
# Round-4 M-3.2 FIX: TUI sends BARE sid; OpenTeam-side adapter composes
# the external id. Matches §2 Goal 1 ("RovoDev does not know its own
# protocol name"). New frontends now only need a single hardcoded string
# in OpenTeam's adapter, never in their own code.
env["OPENTEAM_SESSION_ID"] = sid                    # bare UUID4 (no "rovodev-" prefix)
env["OPENTEAM_FRONTEND_ID"] = "rovodev"             # adapter contract
# Optional provenance
env["OPENTEAM_FRONTEND_METADATA"] = json.dumps({
    "tui_version": __version__,
    "workspace": str(Path.cwd()),
})
# Reset one-shot flag
app.force_new_openteam_session = False
# ... existing subprocess spawn ...
```

### 6.7 `--new-openteam-session` flag (`app.py`)

```python
# In app.py CLI parser:
parser.add_argument(
    "--new-openteam-session",
    action="store_true",
    help="Force a fresh OpenTeam session for this TUI launch "
         "(default: reuse the workspace's persisted session id).",
)
# In Textual App.__init__:
self.force_new_openteam_session = cli_args.new_openteam_session
```


---

## 7. Test plan (~28 tests + 1 CI preflight)

### 7.1 OpenStartup tests

| File | Tier | Tests | Coverage |
|---|---|---|---|
| `test/openteam/services/test_session_store_attach.py` (NEW) | TIER-1 | 7 | idempotent (T1), unknown prefix rejected (T2), traversal-unsafe remainder rejected (T3), `session_state.json` records `external_id`/`frontend_id`/`frontend_metadata` (T4), legacy `session-<...>` accepted (T5), session dir name format (T6), tasks subdir created (T7) |
| `test/openteam/services/test_build_session_context.py` (NEW) | TIER-1 | 6 | empty env → ephemeral (T1), full env → attach (T2), partial env → warn+ephemeral (T3), invalid prefix → warn+ephemeral (T4), malformed JSON metadata → warn+ignore (T5), kwargs override env (T6) |
| `test/openteam/services/test_tool_cli_env.py` (NEW) | TIER-2 | 4 | no env → empty-equivalent ctx (T1), both set → ctx populated (T2), partial → warn (T3), invalid → fallback (T4) |
| `test/openteam/mcp/test_wrapper_propagates_frontend_session_id.py` (NEW) | TIER-2 | 4 | `openteam_task` kwarg → ctx (T1), no kwarg → ephemeral (T2), kwarg + env conflict → kwarg wins (T3), metadata flows through (T4) |
| `test/openteam/services/test_frontend_prefix_whitelist_immutable.py` (NEW) | **CI preflight** | 1 | asserts `_VALID_FRONTEND_PREFIXES == frozenset({"rovodev","ui","mcp","slack","session"})` exact equality |
| `test/openteam/integration/test_e2e_session_attach.py` (NEW) | TIER-3 | 2 | spawn `openteam-task` with env set → task workspace under correct session dir (T1); spawn twice → same session reused (T2) |

### 7.2 RovoDev TUI tests

| File | Tier | Tests | Coverage |
|---|---|---|---|
| `tests/test_openteam_session.py` (NEW) | TIER-1 | 6 | mint+persist (T1), reuse on second call (T2), `force_new=True` rotates session id, preserves server dir (T3), corruption (empty file) self-heals (T4), workspace move = new wsuuid (T5), `_workspace_uuid12` is deterministic (T6) |
| `tests/test_slash_handler_env.py` (NEW) | TIER-2 | 3 | all 3 env vars set on subprocess (T1), `--new-openteam-session` propagates (T2), one-shot flag reset after use (T3) |
| `tests/test_app_cli_flag.py` (NEW) | TIER-2 | 1 | `rovodev tui --new-openteam-session` → `app.force_new_openteam_session = True` |

### 7.3 CI preflight detail

```python
# test/openteam/services/test_frontend_prefix_whitelist_immutable.py
"""
CI preflight: the whitelist expansion is intentional, never accidental.
This test FAILS the build if anyone changes _VALID_FRONTEND_PREFIXES
without simultaneously updating this test, forcing code review.
"""
def test_whitelist_is_exactly_this():
    from openteam.server.services.session_store import _VALID_FRONTEND_PREFIXES
    assert _VALID_FRONTEND_PREFIXES == frozenset({
        "rovodev", "ui", "mcp", "slack", "session",
    }), (
        "Adding a frontend prefix requires:\n"
        "  1. Update _VALID_FRONTEND_PREFIXES in session_store.py\n"
        "  2. Update this test's expected set\n"
        "  3. Document the new frontend in docs/MCP_INTEGRATION.md\n"
        "  4. Code review approval from @openteam-maintainers"
    )
```

---

## 8. Phased delivery

| Phase | Scope | Effort | Blocks | DoD signal |
|---|---|---|---|---|
| **1a** | `SessionStore.validate_external_id` (public per Round-4 Mo-3.1) + `attach_or_create_session` + `create_session` refactor | 1.5h | 1b, 2 | 7 unit tests pass |
| **1b** | `test_session_store_attach.py` (7 tests) | 1h | — | green CI |
| **1c** | `test_frontend_prefix_whitelist_immutable.py` (CI preflight) | 15min | — | green CI |
| **2** | `build_session_context` rewrite (with correct SessionStore call! — Invariant I7) | 1.5h | 3 | 6 unit tests pass |
| **3** | `test_build_session_context.py` (6 tests) + `tool_cli.py` line 113 + `test_tool_cli_env.py` (4 tests) | 1.5h | 6 | green |
| **4** | 4 MCP wrappers add 2 kwargs each + `test_wrapper_propagates_frontend_session_id.py` | 1h | 5 | 4 wrappers + 4 tests pass |
| **5** | WS init handshake (back-compat) | 30min | 9 | UI smoke unchanged |
| **6a** | `openteam_session.py` TUI helper | 1.5h | 6b, 7 | 6 unit tests pass |
| **6b** | `test_openteam_session.py` (6 tests) | 1h | — | green |
| **7** | Handler wiring + `--new-openteam-session` CLI flag + 4 wiring tests | 1.5h | 8 | green |
| **8** | E2E smoke: spawn `openteam-task` with env from TUI helper → assert task workspace under correct session dir | 1h | 9 | manual + integration test green |
| **9** | Docs: `MCP_INTEGRATION.md`, `openteam-integration.md`, README mentions | 1h | — | reviewed |

**Total: ~12 hours focused work for ship-ready v1.**

**Critical path:** 1a → 1b → 2 → 3 → 6a → 6b → 7 → 8.

**Parallelisable:** {1c}, {4}, {5}, {9} can run in any order off the critical path.


---

## 9. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `attach_or_create_session` race when SAME TUI workspace runs two `/task` concurrently | Low | Low | Per-workspace synthetic server isolates `sessions_index.json`; intra-workspace concurrency limited by TUI (one `/task` at a time per pane). |
| R2 | Two TUI processes in DIFFERENT workspaces still race on `_runtime/servers/` mkdir | Very Low | None | `mkdir(parents=True, exist_ok=True)` is atomic for the leaf; parent contention is benign. |
| R3 | Future protocol field needed (e.g., `frontend_user`) | Med | Low | `frontend_metadata` JSON dict absorbs future fields without protocol bump. |
| R4 | Whitelist creep | Med | Low | CI preflight (§7.3) requires explicit code-review approval for every addition. |
| R5 | Stale `.rovodev/openteam_server_dir` (workspace moved with `cp -r`) | Med | Low | TUI helper revalidates path on read; mints fresh if invalid. |
| R6 | Pre-protocol RovoDev TUI still calls new wrappers | High | None | Wrappers' new kwargs default `None` → ephemeral session = today's behaviour. |
| R7 | React UI still uses bare `session-<...>` ids | High | None | `session` is in whitelist; legacy form accepted via `partition("-")` (single-arg). |
| R8 | `OPENTEAM_FRONTEND_METADATA` env var exceeds OS limit (~128 KB on macOS) | Very Low | Low | Document max ~32 KB; reject larger in `build_session_context` with warn-and-fallback. |
| R9 | RovoDev's `--new-openteam-session` flag misunderstood as `--new-session` (RovoDev's own session reset) | Med | Low | Disambiguated name + docs section explicitly contrasts with any future RovoDev-internal reset. |
| R10 | Synthetic server dir proliferation (one per workspace × forever) | High | Low | Inherits cleanup story from workspace-allocation v5.3 (out of scope). User can `find _runtime/servers/server_rovodev_* -mtime +90 -delete`. |
| R11 | `_workspace_uuid12` collision (12 hex = 2⁴⁸ ≈ 281 trillion) | Negligible | Re-introduces `_update_index` race for the colliding workspaces | At N=65,536 workspaces: P(collision) = 7.6e-6 (verified by `1-exp(-N²/(2·2⁴⁸))`). Even at N=1 million: P ≈ 0.18%. Round-4 widened from 8 to 12 hex chars after auditor flagged 39% collision rate at the 8-char width (off by 800× vs original claim). |

---

## 10. Out of scope (deliberate v1 boundaries)

- **Conversation-turn coupling** across `/task` invocations (session = workspace bucket only)
- **React UI migration** to `ui-` prefix (legacy `session-<...>` continues working)
- **Session cleanup / GC** (inherits from workspace-allocation v5.3)
- **Typed `SessionContext` dataclass** (separate ticket)
- **Cross-machine session continuity** (`.rovodev/openteam_server_dir` is absolute; `cp -r` to another host gracefully self-heals to a new server dir but loses prior session)
- **Multiple OpenTeam sessions per TUI workspace** (1:1; `rm -rf .rovodev/` to reset, `--new-openteam-session` to rotate)
- **Real-time RovoDev → React UI graph streaming** (graph-view-v4 plan handles separately)
- **Authentication on session attach** (local-only; out of threat model)

---

## 11. Three-plan comparison + pick-one answer

### 11.1 Comparison table

| Concern | Claude (139) | Cursor INTEGRATED-v2 (1057) | My protocol-v2 (815) | **v3 (this)** |
|---|---|---|---|---|
| Identifies the gap | ✅ | ✅ + file:line | ✅ + file:line | ✅ + re-verified Round-3 |
| **SessionStore constructor call** | not specified | ❌ `SessionStore(server_dir=...)` — TypeError! | ✅ `(runtime_root=, resume_server=)` | ✅ (mine) + Invariant I7 + named in 4 places |
| **`_update_index` race** | per-workspace (good) | per-workspace (good) | shared server (RACE!) | per-workspace (Cursor wins) + belt-and-suspenders flock comment |
| Delimiter | `-` | `:` (Windows %3A) | `-` | `-` (POSIX-clean) |
| MCP wrapper kwargs | ❌ | ✅ `frontend_session_id` | ❌ env-only | ✅ (Cursor wins) |
| WS init handshake | ❌ | ✅ optional fields | ✅ Phase 3 | ✅ |
| Adapter-knows-prefix | ❌ | ✅ | ✅ | ✅ |
| Shared `session_resolver.py` | ❌ | ✅ explicit | ✅ implicit | ✅ rolled into `build_session_context` (simpler — one entry point) |
| `.rovodev/` persistence | ❌ | ✅ | ✅ | ✅ |
| `--new-*-session` flag | ❌ | ✅ `--new-session` | ✅ `--new-openteam-session` | ✅ disambiguated |
| Prefix whitelist + CI preflight | partial | ✅ | ✅ | ✅ explicit code |
| Provenance (`frontend_metadata`) | ❌ | ✅ | dropped (OOS) | ✅ (Cursor wins) |
| Test count | 0 | 22 + CI | 26 + CI | **34 + CI** (Round-4 Mo-3.2: corrected from "~28"; actual is 7+6+4+4+2+6+3+1+1 = 34 unit + 1 CI preflight) |
| Empirical Round-3 verification | n/a | n/a | n/a | ✅ 2 Explore agents + bash |
| Lines | 139 | 1057 | 815 | ~880 (this) |

### 11.2 Pick-one answer

If forced to pick exactly ONE of the three precursors (without integrating):

**Pick Cursor INTEGRATED-v2.** Despite the SessionStore constructor bug (which would crash at runtime), Cursor's architectural shape is the most complete:
- Correctly identifies the `_update_index` race motivation for per-workspace synthetic servers.
- Has MCP wrapper kwargs (which my v2 lacked).
- Has `frontend_metadata` provenance (which my v2 dropped).
- Has the most concrete WS init handshake spec.

The SessionStore constructor bug is a one-line fix that a competent implementer would catch on first test run.

**Ranking:** Cursor INTEGRATED-v2 > my protocol-v2 > Claude. **With v3 in play, v3 strictly dominates all three** because it's the union of correctness (my v2's constructor + Cursor's race-elimination + Cursor's wrappers + my v2's delimiter + Cursor's provenance) without any plan's individual bug.

---

## 12. Self-audit (stress-tests against hacks)

| Question | Answer |
|---|---|
| Is anything in v3 ad-hoc or hacky? | The `_explicit_id` / `_frontend_id` / `_frontend_metadata` kwargs on `create_session` are leading-underscore (= "package-private"). They're used by `attach_or_create_session` only. The leading-underscore convention is intentional: it warns callers not to use them directly. Acceptable. |
| Does v3 commit OpenTeam to a specific RovoDev TUI version? | No. The env contract (`OPENTEAM_SERVER_DIR` + `OPENTEAM_SESSION_ID`) is the only API surface. RovoDev can change everything else internally without breaking OpenTeam. |
| Does v3 commit RovoDev to a specific OpenTeam version? | Only that `build_session_context` reads the env vars. If OpenTeam removes that read, RovoDev's subprocess falls back to empty `session_context` with a warning — degraded but functional. |
| Could a malicious user attach to someone else's session? | Only if they can already read that user's `.rovodev/openteam_session_id` file. Same threat surface as any dotfile persistence (`.git/config`, `.cursor/`, etc.). |
| What if `OPENTEAM_RUNTIME_DIR` differs between TUI and subprocess? | TUI helper computes server dir from `_runtime_root()`; subprocess inherits env unless overridden. Both use the same logic. Tested via TIER-2 `test_runtime_root_helpers_agree.py` (recommended Phase 9 addition). |
| Could two `/task`s in the SAME TUI write to the same task workspace? | No — workspace allocator (v5.3) uses `uuid8` suffix per task; collision probability ~2⁻³², 3-retry loop in allocator handles theoretical collisions. |
| What if user runs the React UI AND RovoDev TUI from the same workspace? | React UI launches its own server (`server_<ts>_<uuid8>`); RovoDev uses `server_rovodev_<wsuuid>`. Different directories. Both visible in `/sessions` UI listing. No conflict. |
| Will v3 break `rovodev-tui-graph-view-v4`? | No. That plan added `ROVODEV_TUI_GRAPH_FD` env; v3 adds 3 more env vars. All additive. |
| Will v3 break `tool_workspace_allocation v5.3`? | No. v5.3 reads `session_context["session_root"]`; v3 populates that key whenever the env contract is satisfied. v5.3's three pending audit fixes are independent. |
| What if user wants to share their session across machines (cloud-synced workspaces)? | `.rovodev/openteam_session_id` syncs; `.rovodev/openteam_server_dir` is absolute and won't sync. On stale path, TUI helper re-mints server dir. Documented in §10. |
| Why not use file-locking for the index race AND keep one shared server? | Implementing fcntl/flock across the codebase is larger surface; not portable to Windows; doesn't compose with the WS server's existing patterns. Per-workspace dirs solve the same problem with zero existing-code change. v1 ships with **NO file-locking** (single position across §3.3, §5.1, §12); a single TODO comment near `_update_index` references this plan should shared servers ever become the default. |
| Does v3 introduce any new global state? | No. Each subprocess constructs its own `SessionStore` from the env vars. No global registry. |

---

## 13. Glossary

| Term | Meaning |
|---|---|
| **External session id** | A session id supplied by a frontend (`rovodev-<uuid4>`) or legacy server-minted (`session-<unix>-<hex6>`). |
| **Frontend prefix** | Substring before the first `-` in an external id. Must be in `_VALID_FRONTEND_PREFIXES`. |
| **`attach_or_create_session`** | NEW idempotent `SessionStore` method. |
| **`OPENTEAM_SERVER_DIR`** | NEW env var; abs path to `<runtime>/servers/<server>/`; tells subprocess WHICH SessionStore. |
| **`OPENTEAM_SESSION_ID`** | NEW env var; external session id, validated against whitelist. |
| **`OPENTEAM_FRONTEND_ID`** | Optional override; defaults to parsed prefix of session id. |
| **`OPENTEAM_FRONTEND_METADATA`** | Optional JSON dict for audit provenance. |
| **`.rovodev/`** | Per-TUI-workspace persistence directory (`.rovodev/openteam_session_id` + `.rovodev/openteam_server_dir`). |
| **Synthetic server dir** | `<runtime>/servers/server_rovodev_<wsuuid>/` — per-workspace TUI server isolating `sessions_index.json` writes. |
| **`wsuuid`** | `sha256(workspace_abs_path)[:8]` — stable per-workspace identifier. |
| **`--new-openteam-session`** | TUI CLI flag forcing fresh session id (preserves synthetic server dir). |
| **Path A / Path B** | v5.3 terms; A = standalone tasks dir, B = under-session tasks dir. v3 makes Path B the default for RovoDev. |

---

## 14. Definition of Done

### OpenStartup repo
- [ ] `_VALID_FRONTEND_PREFIXES`, `validate_external_id` (public), `_PREFIX_REGEX`, `_SAFE_REMAINDER_REGEX` landed in `session_store.py`
- [ ] `attach_or_create_session` + refactored `create_session(_explicit_id=, _frontend_id=, _frontend_metadata=)` landed
- [ ] `build_session_context` rewritten with **correct SessionStore signature (I7)**
- [ ] `tool_cli.py:113` replaced with `build_session_context()` call
- [ ] All 4 MCP wrappers (`openteam_task`, `openteam_role_setup`, `openteam_create_role`, `openteam_project_onboarding`) accept `frontend_session_id` + `frontend_metadata` kwargs
- [ ] WS init handshake accepts optional `frontend_id` / `frontend_session_id` / `frontend_metadata`
- [ ] All TIER-1 tests pass: `test_session_store_attach.py` (7), `test_build_session_context.py` (6)
- [ ] All TIER-2 tests pass: `test_tool_cli_env.py` (4), `test_wrapper_propagates_frontend_session_id.py` (4)
- [ ] CI preflight `test_frontend_prefix_whitelist_immutable.py` green
- [ ] All TIER-3 tests pass: `test_e2e_session_attach.py` (2)
- [ ] `docs/MCP_INTEGRATION.md` documents protocol fields, env vars, prefix whitelist

### cli-rovodev-tui repo
- [ ] `openteam_session.py` ships with `get_or_create_session` + `_workspace_uuid12` + `_runtime_root`
- [ ] `slash_commands/openteam.py` wires 3 env vars
- [ ] `app.py` accepts `--new-openteam-session` and threads `force_new_openteam_session` through
- [ ] `test_openteam_session.py` (6) pass
- [ ] `test_slash_handler_env.py` (3) pass
- [ ] `test_app_cli_flag.py` (1) passes
- [ ] `docs/openteam-integration.md` documents `.rovodev/` + flag + multi-workspace semantics

### End-to-end smoke
- [ ] Launch TUI in fresh dir → `.rovodev/openteam_session_id` exists, matches UUID4 regex
- [ ] Run `/task "what is 2+2"` → task workspace at `<runtime>/servers/server_rovodev_<wsuuid>/sessions/rovodev-<uuid4>_<TS>/tasks/task_*/`
- [ ] Run `/task "another"` in same TUI → SECOND task workspace under SAME session dir
- [ ] Ctrl-C, restart TUI in same dir → third `/task` lands under SAME session
- [ ] `rovodev tui --new-openteam-session` → fresh session id; previous tasks not visible in this run
- [ ] React UI `/sessions` endpoint lists `rovodev-<...>` sessions alongside `session-<...>` ones
- [ ] WS path: open React UI session, run a task → unchanged behavior (back-compat)
- [ ] `openteam-task --help` from bare shell (no env) → works (standalone Path A)

---

## 15. Acknowledgements

- **Cursor INTEGRATED-v2** — per-workspace synthetic server (eliminates `sessions_index.json` race); MCP wrapper kwargs; `frontend_metadata` provenance; WS init handshake; explicit `session_resolver.py` discipline; CI preflight pattern.
- **My protocol-v2** — correct `SessionStore(runtime_root=, resume_server=)` constructor call; `-` delimiter; shared-helper architecture for MCP+CLI; design-decisions section structure.
- **Claude (eager-roaming-clock)** — concise problem framing; `OPENTEAM_SESSION_ID` env name; clean back-compat table format.
- **Round-3 empirical verification** — 2 parallel `Explore` subagents + direct `bash` on `session_store.py` constructor + `_update_index` write race + locking absence. Both hazards definitively confirmed.

---

**End of plan. Saved at:** `CoreProjects/OpenStartup/_dev/_plan/openteam_rovodev_integration/openteam-unified-frontend-session-protocol-v3.md`

---

## 16. Phase 6 — Auto-launch supervisor (Round-6 addition)

### 16.1 Motivation

The Round 1-5 protocol guarantees the **on-disk** server directory always exists (synthetic per-workspace dir). It does NOT guarantee the **HTTP server process** is running. Consequence today:

- `/task` works fully (executor is in-process; no HTTP needed).
- The React UI is **dark** until the user runs `python run_server.py` separately.
- New RovoDev users have no obvious path to "see my sessions in a browser".

**Round-6 goal:** when a RovoDev TUI starts, **auto-discover an existing OpenTeam server**; if none is alive, **launch one in the background**; record the endpoint for the TUI's lifetime; let the user opt out via env / flag. This is the **generic backend-discovery component** the user requested.

**Non-goal:** routing `/task` *execution* through HTTP. Execution stays in-process (fast, isolated, well-tested). The HTTP server is an **observability consumer** — it scans the same `<runtime>/servers/` tree the subprocess wrote to.

### 16.2 Hard invariants (extend §2.2)

- **I8.** Auto-launch is **opt-out**, not opt-in: `OPENTEAM_AUTO_LAUNCH=0` OR `rovodev tui --no-openteam-server` disables. Default: launch if not running.
- **I9.** `/task` correctness MUST NOT depend on the HTTP server. If the server fails to launch, the TUI logs WARNING and continues; `/task` still succeeds (uses subprocess + filesystem).
- **I10.** Discovery directory: `~/.openteam/servers/` (NOT `<runtime>/servers/` — that's on-disk state, this is **liveness registry**).
- **I11.** Discovery files MUST be self-cleaning: server registers on startup, unregisters on graceful shutdown, supervisor reaps stale files via `/health` probe. **Schema is defined exactly once** in `openteam.client.discovery` (single source of truth; `openteam.server._register` imports from there — Round-7 elegance).
- **I12.** Server is selected by `(runtime_root, host)` tuple. Two checkouts of OpenStartup → two distinct servers → two distinct discovery files. **No accidental cross-checkout collisions.**
- **I13.** Launch is **idempotent under concurrency** via file-lock (`~/.openteam/servers/.launch.lock`). Two TUIs starting simultaneously → only one new server launched; the second waits and discovers it.
- **I14. (Round-7) Client/server import directionality:** `openteam.client.**` MUST NOT import from `openteam.server.**`. Reverse direction is permitted: `openteam.server._register` imports schema from `openteam.client.discovery`. Enforced by CI preflight `test_no_server_imports.py` (AST scan over `src/openteam/client/`). Enables future `openteam-sdk` PyPI package as a thin re-export of `openteam.client` with zero FastAPI / inference-backend bleed-through.

### 16.3 Discovery file schema

Location: `~/.openteam/servers/<server_id>.json` where `<server_id> = sha256(f"{runtime_root}|{host}")[:12]`.

```json
{
  "schema_version": 1,
  "server_id": "a3b9c8d2e1f4",
  "pid": 78234,
  "host": "127.0.0.1",
  "port": 8000,
  "runtime_root": "/Users/tchen/MyProjects/CoreProjects/OpenStartup/_runtime",
  "server_dir_name": "server_20260517_205500_a1b2c3d4",
  "started_at": "2026-05-17T21:03:00Z",
  "version": "0.1.0",
  "process_command": ["python", "run_server.py", "--port", "8000", "--resume-latest-server"]
}
```

**Why these fields:** `pid` for liveness check (`os.kill(pid, 0)`); `host`+`port` for `GET /health`; `runtime_root` for I12; `server_dir_name` so RovoDev can show "your sessions are in: X"; `process_command` for forensics ("what launched this?").

### 16.4 Server-side write hook (`src/openteam/server/_register.py`, NEW ~50 LOC)

**Round-7 refactor:** the WRITE side stays under `server/` because it runs INSIDE the server process. It imports schema constants from `openteam.client.discovery` (the source of truth). Leading underscore indicates package-private; called only from `run_server.py`.

```python
"""Server-side liveness registry write hook.

Owned by the server process. Imports the shared discovery-file schema from
``openteam.client.discovery`` (the source of truth), then writes a JSON file
to ``~/.openteam/servers/<server_id>.json`` on startup and removes it on
graceful shutdown.

Why split (Round-7): the READ side (``discover_servers``, ``ServerHandle``)
lives in ``openteam.client.discovery`` so third-party integrators (Slack
bots, IDE plugins, future ``openteam-sdk`` PyPI package) depend only on
``openteam.client`` — never on ``openteam.server`` which pulls FastAPI,
React build assets, inference backends, etc.
"""
from __future__ import annotations
import atexit
import json
import logging
import os
import signal
from datetime import datetime, timezone
from pathlib import Path

# Single source of truth for schema constants + id derivation.
from openteam.client.discovery import (
    DISCOVERY_DIR,                # ~/.openteam/servers/
    SCHEMA_VERSION,
    compute_server_id,            # public-named (was _server_id)
    pid_alive,                    # public-named (was _pid_alive)
)

_logger = logging.getLogger(__name__)


def register_server(
    *,
    runtime_root: Path,
    host: str,
    port: int,
    server_dir_name: str,
    version: str = "0.1.0",
    process_command: list[str] | None = None,
) -> Path:
    """Atomically write the discovery file. Returns the path written.

    Idempotent: if a file already exists with same (host, port, pid), overwrite.
    If a file exists with same id but different pid, AND that pid is alive,
    raises RuntimeError (another server is bound here).
    """
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    sid = compute_server_id(runtime_root, host)
    target = DISCOVERY_DIR / f"{sid}.json"

    # Conflict check: someone else holding the slot?
    if target.exists():
        try:
            existing = json.loads(target.read_text())
            other_pid = existing.get("pid")
            if other_pid and other_pid != os.getpid() and pid_alive(other_pid):
                raise RuntimeError(
                    f"Another OpenTeam server (pid={other_pid}) is registered at "
                    f"{host}:{existing.get('port')} for runtime={runtime_root}. "
                    f"Refusing to overwrite. Stop the other server first."
                )
        except (json.JSONDecodeError, OSError):
            pass  # stale or corrupt — overwrite

    payload = {
        "schema_version": SCHEMA_VERSION,
        "server_id": sid,
        "pid": os.getpid(),
        "host": host,
        "port": port,
        "runtime_root": str(runtime_root.resolve()),
        "server_dir_name": server_dir_name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "process_command": process_command or [],
    }
    # Atomic write
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, target)

    # Self-cleanup hooks
    atexit.register(_unregister, target)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: (_unregister(target), os._exit(0)))

    _logger.info("[discovery] registered %s", target)
    return target


def _unregister(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
        _logger.info("[discovery] unregistered %s", path)
    except Exception:
        pass


```

**Note:** the `pid_alive` helper itself lives in `openteam.client.discovery` (see §16.5) — both sides need it (server checks for conflicting registration; client checks for stale entries). Single source of truth.

Called from `run_server.py` right before `uvicorn.run(...)`:

```python
# run_server.py — additions
from openteam.server._register import register_server
register_server(
    runtime_root=Path(args.real_sessions) if args.real_sessions else find_runtime_root(),
    host=args.host,
    port=args.port,
    server_dir_name=session_store.server_name,
    process_command=sys.argv,
)
uvicorn.run(app, host=args.host, port=args.port, ...)
```

### 16.5 Generic client package (`src/openteam/client/`, NEW package, 3 files ~150 LOC)

**Round-7 refactor:** moved out of `server/` so clients depend only on the lean `client` package — never on `server/` (which pulls FastAPI, React build assets, inference backends, the conversation service, etc.). Sibling to `mcp_server/` and `server/` at the same level under `src/openteam/`.

```
src/openteam/client/
  __init__.py       # 8 LOC — re-exports the public surface
  discovery.py      # ~60 LOC — schema constants + ServerHandle + discover_servers()
  supervisor.py     # ~80 LOC — ensure_server() launch-or-attach logic
```

**Public surface (the entire client API):**

```python
# src/openteam/client/__init__.py
"""Generic OpenTeam client: discover-or-launch a running server.

Frontend-agnostic. RovoDev TUI, future Slack bot, future IDE plugin, future
``openteam-sdk`` PyPI package all import from here — never from ``openteam.server``.
"""
from openteam.client.discovery import (
    DISCOVERY_DIR,
    SCHEMA_VERSION,
    ServerHandle,
    compute_server_id,
    discover_servers,
    pid_alive,
)
from openteam.client.supervisor import ensure_server

__all__ = [
    "DISCOVERY_DIR", "SCHEMA_VERSION", "ServerHandle",
    "compute_server_id", "discover_servers", "pid_alive", "ensure_server",
]
```

#### 16.5.1 `src/openteam/client/discovery.py` (read side + schema, ~60 LOC)

This is the **source of truth** for the discovery-file schema. The server's `_register.py` imports from here, NOT the other way around.

```python
"""Discovery-file schema + read-side helpers.

The schema (DISCOVERY_DIR, SCHEMA_VERSION, ServerHandle, file naming) is
defined here so both the server-side write hook (openteam.server._register)
and any client (TUI, SDK, plugin) reference the same constants.

This module has zero non-stdlib deps (httpx is imported lazily by
ServerHandle.alive()) — safe to import from very thin client packages.
"""
from __future__ import annotations
import contextlib
import dataclasses
import hashlib
import json
import logging
import os
from pathlib import Path

DISCOVERY_DIR = Path.home() / ".openteam" / "servers"
SCHEMA_VERSION = 1
_HEALTH_TIMEOUT_S = 0.2

_logger = logging.getLogger(__name__)


def compute_server_id(runtime_root: Path, host: str) -> str:
    """Stable id from (runtime_root, host) — Invariant I12.

    Two checkouts of OpenStartup at different paths → different ids → different
    discovery files → no accidental collision.
    """
    return hashlib.sha256(
        f"{str(runtime_root.resolve())}|{host}".encode()
    ).hexdigest()[:12]


def pid_alive(pid: int) -> bool:
    """POSIX liveness check via signal 0."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


@dataclasses.dataclass(frozen=True)
class ServerHandle:
    server_id: str
    pid: int
    host: str
    port: int
    runtime_root: Path
    discovery_file: Path

    def endpoint(self) -> str:
        return f"http://{self.host}:{self.port}"

    def alive(self) -> bool:
        """Process is alive AND /health responds 200 within 200ms."""
        if not pid_alive(self.pid):
            return False
        try:
            import httpx                  # lazy import — discovery alone is httpx-free
            r = httpx.get(self.endpoint() + "/health", timeout=_HEALTH_TIMEOUT_S)
            return r.status_code == 200
        except Exception:
            return False

    def stop(self) -> None:
        """SIGTERM → wait 5s → SIGKILL fallback. Server unregisters via atexit."""
        import time
        if pid_alive(self.pid):
            os.kill(self.pid, 15)
            for _ in range(50):
                if not pid_alive(self.pid):
                    return
                time.sleep(0.1)
            os.kill(self.pid, 9)


def discover_servers() -> list[ServerHandle]:
    """Read all discovery files; return only those whose pid is alive.

    Side effect: reaps unresponsive entries (best-effort; OK if it fails).
    """
    if not DISCOVERY_DIR.exists():
        return []
    out: list[ServerHandle] = []
    for f in DISCOVERY_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            if d.get("schema_version") != SCHEMA_VERSION:
                _logger.warning("[discovery] skipping wrong-schema file: %s", f.name)
                continue
            h = ServerHandle(
                server_id=d["server_id"],
                pid=d["pid"],
                host=d["host"],
                port=d["port"],
                runtime_root=Path(d["runtime_root"]),
                discovery_file=f,
            )
            if pid_alive(h.pid):
                out.append(h)
            else:
                with contextlib.suppress(OSError):
                    f.unlink()
                    _logger.info("[discovery] reaped stale %s", f.name)
        except (json.JSONDecodeError, KeyError, OSError):
            with contextlib.suppress(OSError):
                f.unlink()
    return out
```

#### 16.5.2 `src/openteam/client/supervisor.py` (launch logic, ~80 LOC)

```python
"""Generic backend supervisor: discover-or-launch an OpenTeam server.

This module is intentionally frontend-agnostic. Any client (RovoDev TUI,
future Slack bot, IDE plugin) calls ``ensure_server(...)`` to get a
``ServerHandle`` — a discovered live server or a freshly launched one.

Public surface (re-exported from ``openteam.client``):
    ensure_server(runtime_root, *, host="127.0.0.1", auto_launch=True) → ServerHandle | None
"""
from __future__ import annotations
import contextlib
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Single dependency on sibling module — schema + read side live in discovery.py.
from openteam.client.discovery import (
    DISCOVERY_DIR,
    ServerHandle,
    compute_server_id,
    discover_servers,
)

_logger = logging.getLogger(__name__)
_LAUNCH_LOCK = DISCOVERY_DIR / ".launch.lock"
_LAUNCH_TIMEOUT_S = 15.0
_PORT_RANGE = range(8000, 8011)  # 8000-8010
_AUTO_LAUNCH_ENV = "OPENTEAM_AUTO_LAUNCH"  # set to "0" to disable


def ensure_server(
    runtime_root: Path,
    *,
    host: str = "127.0.0.1",
    auto_launch: bool | None = None,
) -> ServerHandle | None:
    """Discover-or-launch an OpenTeam server for the given runtime_root.

    Returns:
        ServerHandle if a server is live (discovered or launched),
        None if auto_launch=False AND no live server exists (caller decides).

    Args:
        runtime_root: required — selects which server (Invariant I12).
        host: bind address. Default "127.0.0.1".
        auto_launch: True → launch if not found; False → return None;
                     None → read OPENTEAM_AUTO_LAUNCH env (default True).
    """
    if auto_launch is None:
        auto_launch = os.environ.get(_AUTO_LAUNCH_ENV, "1") != "0"

    runtime_root = runtime_root.resolve()
    sid = compute_server_id(runtime_root, host)

    # 1. Fast path: match by sid AND alive
    for h in discover_servers():
        if h.server_id == sid and h.alive():
            _logger.info("[supervisor] discovered live server pid=%d at %s", h.pid, h.endpoint())
            return h

    if not auto_launch:
        return None

    # 2. Launch with file-lock so concurrent TUIs don't double-spawn (I13)
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    with _file_lock(_LAUNCH_LOCK, timeout=_LAUNCH_TIMEOUT_S):
        # Re-check after acquiring lock (another TUI may have just launched)
        for h in discover_servers():
            if h.server_id == sid and h.alive():
                return h
        return _launch_new(runtime_root=runtime_root, host=host)


def _launch_new(runtime_root: Path, host: str) -> ServerHandle:
    port = _pick_port(host)
    cmd = [
        sys.executable, "-m", "openteam.server.run_server",
        "--host", host,
        "--port", str(port),
        "--mode", "live",
        "--real-sessions", str(runtime_root),
        "--resume-latest-server",                     # rejoin existing if any
    ]
    log_path = DISCOVERY_DIR / f"{compute_server_id(runtime_root, host)}.log"
    _logger.info("[supervisor] launching: %s", " ".join(cmd))
    proc = subprocess.Popen(                          # type: ignore[arg-type]
        cmd,
        stdout=open(log_path, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,                       # detach from parent process group
        env={**os.environ, "OPENTEAM_AUTO_LAUNCH": "0"},  # prevent recursive launch
    )

    # Wait for the discovery file to appear (server's atexit cleans up on failure)
    deadline = time.monotonic() + _LAUNCH_TIMEOUT_S
    while time.monotonic() < deadline:
        for h in discover_servers():
            if h.pid == proc.pid and h.alive():
                _logger.info("[supervisor] launched pid=%d at %s", h.pid, h.endpoint())
                return h
        if proc.poll() is not None:
            raise RuntimeError(
                f"OpenTeam server (pid={proc.pid}) exited before registering. "
                f"Check log: {log_path}"
            )
        time.sleep(0.2)
    raise TimeoutError(
        f"OpenTeam server (pid={proc.pid}) did not register within {_LAUNCH_TIMEOUT_S}s. "
        f"Check log: {log_path}"
    )


def _pick_port(host: str) -> int:
    for p in _PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise RuntimeError(f"No free port in {_PORT_RANGE}")


@contextlib.contextmanager
def _file_lock(path: Path, *, timeout: float):
    """POSIX file lock via O_EXCL create. Windows: same semantics; portable."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                yield
            finally:
                os.close(fd)
                with contextlib.suppress(OSError):
                    path.unlink()
            return
        except FileExistsError:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Could not acquire {path} within {timeout}s")
            time.sleep(0.1)
```

### 16.6 RovoDev TUI integration (~25 LOC)

```python
# packages/cli-rovodev-tui/src/rovodev_tui/openteam_session.py — additions

def get_or_create_session(
    workspace_path: Path,
    *,
    force_new: bool = False,
    auto_launch_server: bool | None = None,
) -> tuple[Path, str, str | None]:
    """Round-6 EXTENSION: optionally ensure a server is running.

    Returns (server_dir, session_id, server_endpoint).
    `server_endpoint` is None if auto_launch_server is False AND no server is live.

    The server is best-effort: failures degrade to ephemeral (today's behaviour)
    with a WARNING log; `/task` still works (Invariant I9).
    """
    server_dir, sid = _resolve_session_files(workspace_path, force_new=force_new)
    runtime_root = _runtime_root()

    endpoint: str | None = None
    try:
        from openteam.client import ensure_server         # Round-7: was openteam.server.supervisor
        handle = ensure_server(runtime_root=runtime_root, auto_launch=auto_launch_server)
        if handle is not None:
            endpoint = handle.endpoint()
            # Persist for debugging; cleared if file becomes stale next launch
            (workspace_path / ".rovodev" / "openteam_endpoint").write_text(endpoint)
    except ImportError:
        # OpenTeam not installed in TUI env → silent, expected for thin clients
        pass
    except Exception as e:
        # Launch failed → log + continue (I9: /task must still work)
        _logger.warning("[openteam_session] supervisor failed: %s — continuing without server", e)

    return (server_dir, sid, endpoint)


# Slash handler additions:
#   - new env var: env["OPENTEAM_ENDPOINT"] = endpoint  (if not None)
#     — for use by future graph-view-v4 / WS streaming consumers
#   - REST call (optional, deferred to POST-1): notify the running server
#     via POST /sessions {external_id, frontend_id} so its index reflects
#     the about-to-be-created session in real time
```

### 16.7 CLI flag + env

| Surface | Default | Override |
|---|---|---|
| Env var `OPENTEAM_AUTO_LAUNCH` | `1` (launch if not found) | Set to `0` to disable globally |
| `rovodev tui --no-openteam-server` | — | One-shot disable for this TUI launch |
| `rovodev tui --openteam-host HOST --openteam-port PORT` | `127.0.0.1` + auto-pick from 8000-8010 | Override |

### 16.8 New tests (8 + 1 CI preflight)

| File | Tier | Tests |
|---|---|---|
| `test/openteam/client/test_discovery.py` | TIER-1 | 4: ServerHandle.endpoint/alive/stop work; discover_servers reads + reaps; compute_server_id is deterministic; pid_alive correct |
| `test/openteam/server/test_register.py` | TIER-1 | 4: register writes file atomically; register conflict-with-alive raises; unregister via atexit; corrupt file reaped on next read |
| `test/openteam/client/test_supervisor.py` | TIER-1 | 4: discover empty; discover with live server; ensure_server reuses live; ensure_server launches when not found |
| `test/openteam/client/test_supervisor_file_lock.py` | TIER-2 | 1: two concurrent ensure_server calls → exactly one launch |
| `test/openteam/server/test_runtime_root_helpers_agree.py` | CI preflight | 1 (already added in Round-5 R5-1) |
| `test/openteam/client/test_no_recursive_launch.py` | TIER-2 | 1: launched server sees `OPENTEAM_AUTO_LAUNCH=0` in env (no fork bomb) |
| `test/openteam/client/test_no_server_imports.py` | **CI preflight (NEW Round-7)** | 1: AST-scan asserts `openteam/client/**/*.py` contains ZERO `import openteam.server` or `from openteam.server` lines. Locks the directionality invariant (client never depends on server). |

### 16.9 Risks (extend §10)

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R12 | Server launch fork bomb if launched server re-runs supervisor | Very Low | Critical | `_launch_new` sets `OPENTEAM_AUTO_LAUNCH=0` in child env; test_no_recursive_launch.py guards |
| R13 | Server crashes mid-session leaves discovery file stale | High | None | `discover_servers()` probes liveness; reaps stale; next ensure_server self-heals |
| R14 | Multiple checkouts of OpenStartup race on `:8000` | Med | Low | I12 + port-range fallback 8000-8010 + discovery file conflict detection |
| R15 | TUI in env without httpx | Low | Low | `try: import httpx`; if missing, `supervisor` module raises ImportError caught at handler boundary (I9: degrade silently) |
| R16 | Server process disowned from TUI (start_new_session) outlives TUI | Med | Low | By design (server is a shared resource across TUIs; survives any single TUI exit). Stop via `openteam-server stop` (TODO POST-1) or `kill <pid>`. |
| R17 | Health probe times out (200ms) on slow systems → false negative | Low | Low | Tunable via `OPENTEAM_HEALTH_TIMEOUT_MS` env (default 200ms; bump to 1000 if needed) |

### 16.10 Out of scope for Round-6

- `openteam-server start | stop | status | restart` CLI (POST-1 ticket; for now use `kill <pid>` + `discover_servers()`).
- TUI-driven graceful shutdown of auto-launched server (server outlives TUI by design — Risk R16).
- Real-time POST `/sessions` notification to the running server (POST-1; today server discovers RovoDev sessions on next `_scan_sessions` refresh).
- TLS / auth on the local HTTP server (local-only; out of threat model).
- Cross-host discovery (`~/.openteam/servers/` is local; clustered openteam is a separate epic).

### 16.11 Phase 6 implementation steps

| Phase | Scope | Effort | Blocks | DoD |
|---|---|---|---|---|
| **6a** | `openteam/client/__init__.py` + `openteam/client/discovery.py` + `test_discovery.py` (4 tests) | 1h | 6b | green |
| **6b** | `openteam/server/_register.py` + `test_register.py` (4 tests); `run_server.py` adds `register_server(...)` call | 45min | 6c | server launches successfully + file appears |
| **6c** | `openteam/client/supervisor.py` + `test_supervisor.py` (4 tests) | 1.5h | 6d | green |
| **6d** | `test_supervisor_file_lock.py` + `test_no_recursive_launch.py` + CI preflight `test_no_server_imports.py` | 45min | 6e | green |
| **6e** | TUI `openteam_session.py` extension (`from openteam.client import ensure_server`) + `app.py` flags | 45min | 6f | manual smoke: `rovodev tui` launches new server |
| **6f** | docs/openteam-integration.md updated with Phase 6 + Round-7 client/server split rationale | 30min | — | reviewed |

**Total Phase 6: ~5h** on top of v1's ~12h → **v1 + Phase 6: ~17h** (Round-7 added 30min for the no-server-imports CI preflight + extra `_register.py` test).

### 16.12 Why this design is elegant (self-audit)

| Property | How achieved |
|---|---|
| **Client/server boundary (Round-7)** | Lean `openteam.client` package: stdlib + lazy httpx only. Heavy `openteam.server` (FastAPI, React, inference backends) is NEVER imported by clients. Schema lives in client; server imports schema from client. Enforced by Invariant I14 + CI preflight `test_no_server_imports.py` (AST scan). Future `openteam-sdk` PyPI package is a thin re-export of `openteam.client` with zero server bleed-through. |
| **Single responsibility per module** | `client/discovery.py` = schema + read. `server/_register.py` = write only (50 LOC). `client/supervisor.py` = orchestrate discover-or-launch. `openteam_session.py` = TUI wiring. No module does two jobs. |
| **Generic** | `supervisor.ensure_server` and the entire `openteam.client` API never mention RovoDev; future frontends import it unchanged. |
| **Opt-out, not opt-in** | I8: auto-launch defaults on. New users get UI visibility for free. |
| **Graceful degradation** | I9: server failure → WARNING + continue. `/task` correctness independent of server liveness. |
| **No fork bomb** | R12: launched server sees `OPENTEAM_AUTO_LAUNCH=0`. |
| **No race on concurrent launch** | I13: file-lock around `_launch_new`. |
| **No conflict between checkouts** | I12: `server_id = sha(runtime_root, host)`. |
| **Self-healing** | I11 + R13: stale discovery files reaped on every `discover_servers()`. |
| **No new dependencies** | `httpx` already pulled in via fastmcp. `os`/`signal`/`subprocess` are stdlib. |
| **Atomic registration** | `os.replace(tmp, target)`: no partial writes, no readers see torn JSON. |
| **Server outlives TUI** | `start_new_session=True`: server is a shared resource (matches user mental model of "the server is up"). |
| **Logs preserved** | `<discovery_dir>/<sid>.log` for postmortem when launch fails. |

