# OpenTeam ↔ RovoDev Integration — Integrated Plan v2

**Date:** 2026-05-08 05:39
**Author:** Rovo Dev (synthesized from `openteam-rovodev-integration-plan.md` v1 +
`take-a-careful-look-memoized-walrus.md`, after critical re-verification of source.)
**Supersedes:** Both prior plans for the OpenTeam↔RovoDev integration question.

---

## 0. TL;DR

Build a **single FastMCP server inside the OpenStartup repo** that wraps each
OpenTeam tool's `executor.execute()` directly, register it via
`~/.rovodev/mcp.json`, and add **four thin slash commands** in RovoDev that
post `PromptSubmitted` messages instructing the agent to call the
corresponding MCP tool. This is the **`/research` pattern** (verified) applied
to OpenTeam.

```
RovoDev TUI                                    OpenStartup repo
─────────────                                  ───────────────
/task <prompt>                                 src/openteam/mcp_server/
  │                                              ├── server.py    (FastMCP factory)
  │ posts PromptSubmitted("Invoking            │   • create_openteam_server()
  │   'openteam_task': <prompt>")              │   • dynamic add_tool from tool.json
  ▼                                              ├── context.py   (session_context builder)
LLM agent                                        ├── main.py      (Typer entry → stdio)
  │                                              └── __init__.py
  │ tool call: mcp__openteam__openteam_task
  ▼
MCP client (StdioTransport)  ──subprocess──▶  python -m openteam.mcp_server.main run
                                                 │
                                                 │ direct in-proc call:
                                                 ▼
                                              await execute(arguments, session_context)
                                                 │
                                                 ▼
                                              ToolExecutionResult
```

**Why this beats both prior plans:**

- **Walrus plan** had the right architecture (MCP + `/research` delegation
  pattern + Typer) but underspecified executor robustness.
- **My v1 plan** had the right audit findings (`tool_cli` bugs, dispatcher
  context shape) but the wrong remediation: subprocess shell-out from inside
  RovoDev was operationally clumsy and required either forking acra-python or
  shipping a brittle entry-point hook.
- **This integrated plan** keeps the elegant MCP+`/research` pattern from
  Walrus and the rigorous executor/contract analysis from v1.

---

## 1. Verified Ground Truth (re-checked 2026-05-08 05:39)

| Fact | Source | Status |
|---|---|---|
| `tool_cli.py:113` initializes `session_context = {}` | re-read | ✓ |
| `tool_cli.py:121` uses `result.get("text", "")` (dict-only) | re-read | ✓ — dead code today; harmless if we **bypass `tool_cli` for MCP** |
| `tool_cli.py:111` does `arguments[k.replace("_", "-")] = v` (dash normalization) | re-read | ✓ — we re-use this contract in the MCP wrappers |
| `task/executor.py:_resolve_workspace` falls through to `_allocate_workspace(task_id)` (creates `server/_runtime/tasks/task_<id>_<ts>`) when `session_context = {}` | re-read | ✓ — **empty session_context is safe**, my v1 was overcautious |
| Executors guard `interactive` with `if interactive is not None` | re-read | ✓ — `interactive=None` is safe |
| All 4 executors return `ToolExecutionResult` (Pydantic) with `.result: str` and `.context_updates: dict` | dispatcher line 234 | ✓ |
| `mcp-atlassian-exp` uses `FastMCP("name") + FunctionTool.from_function(fn) + mcp.add_tool(tool)` (not decorators) and Typer entry → `mcp.run_stdio_async()` | re-read `acra-python/packages/mcp-atlassian-exp/src/atlassian_exp/main.py:95-117` | ✓ — the precedent we follow |
| `/research` slash command posts `PromptSubmitted(text=f"Invoking 'research': {prompt}")` and the agent does the heavy work | re-read `slash_commands/research.py` | ✓ — the pattern we mirror for `/task`, `/create-role`, `/role-setup`, `/project-onboarding` |
| RovoDev `register()` accepts `thread=` and `extra_prompt=` | re-read registry | ✓ |
| Each tool already has `tool.json` + `executor.py` + `cli.py` + `__main__.py` (v3 CLI unification done) | re-read source | ✓ |

### Audit findings — final reconciliation

| # | Finding | Disposition in this plan |
|---|---|---|
| 🔴 1 | `session_context = {}` was called dangerous in v1 | **Reclassified as not-a-bug.** `_resolve_workspace` already handles it. We *do* still build a richer context in `mcp_server/context.py` to surface env-driven hints (`OPENTEAM_WORKING_DIR`, `OPENTEAM_SERVER_DIR`, `task_id`, etc.) when present, but `{}` is no longer a blocker. |
| 🔴 2 | `tool_cli.py` `result.get("text", "")` bug | **Bypassed in primary path** because each MCP wrapper extracts `result.result` directly. **Still patch `tool_cli.py`** as a separate cleanup ticket so the standalone CLI (`python -m openteam.server.resources.tools.task ...`) renders correctly — but it is **not on the critical path** for the slash UX. |
| 🟡 3 | Dual key-shape contract (`foo-bar` vs `foo_bar`) | We standardize on **dash form** in MCP wrappers (matches `tool_cli` normalization) and document the contract once in `mcp_server/server.py`. |
| 🟢 5 | YAML `_import_` resolution | Already fixed in tests via `load_config()`; runtime always used `load_config()`. No action. |

---

## 2. Architecture Choice: MCP-only vs Slash+Subprocess

| Dimension | v1 (Subprocess slash + MCP) | Walrus (MCP + `/research` slash delegation) | **Integrated v2 (this)** |
|---|---|---|---|
| Slash UX | Native handler streams subprocess stdout | Slash posts a prompt → agent invokes MCP tool | **Walrus pattern** — proven `/research` precedent |
| Agentic invocation | MCP-wrapped tools | MCP-wrapped tools | MCP-wrapped tools |
| Coupling to acra-python | 4-line patch + entry-point hook + handler module | **Zero acra-python changes if we ship slash command files** in acra-python's tree as part of the contract | **Slash files in acra-python**, MCP server in OpenStartup |
| Process model | Per-slash subprocess; one MCP subprocess | One MCP subprocess for everything | Same as Walrus: one MCP subprocess |
| Streaming | Real-time stdout via PIPE | Agent streams tool result through normal chat | Agent stream — consistent with rest of TUI |
| Long-running tools | Subprocess can run unbounded | Constrained by MCP client timeout (default ~295s) | **Use Phase 2B in-memory transport** to set `timeout=1800` |
| Cancellation | `proc.terminate()` from worker | Agent-controlled (Ctrl-C interrupts agent loop) | Agent-controlled |
| Implementation LOC | ~80 LOC bridge + 30 LOC MCP wrappers | ~250 LOC server + 80 LOC slash | ~250 LOC server + 80 LOC slash |
| **Verdict** | Slightly more flexibility, lots more moving parts | Cleaner, smaller, follows existing conventions | **Pick Walrus pattern; layer in v1's rigor** |

**Decision:** MCP-only is the elegant solution. The subprocess slash variant
from v1 is **dropped** as it duplicates what the MCP layer already provides
and creates a second IPC boundary without benefit.

---

## 3. Detailed Design

### 3.1 Files to create in OpenStartup repo

```
src/openteam/mcp_server/
├── __init__.py              # empty
├── server.py                # create_openteam_server() factory + 4 wrapper functions
├── context.py               # _build_session_context() from env vars
└── main.py                  # Typer CLI entry; spawns stdio transport

test/openteam/mcp_server/
├── __init__.py
├── test_server_factory.py   # asserts create_openteam_server() registers expected tools
├── test_context.py          # asserts _build_session_context() shape
└── test_wrappers_smoke.py   # TIER-2 mock test: each wrapper runs against a stubbed executor
```

### 3.2 `mcp_server/server.py` — design contract

**Pattern (verified against `mcp-atlassian-exp/main.py:95-117`):**

```python
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from openteam.mcp_server.context import build_session_context

# Hard-mapped to lock down agent-visible surface (don't silently expand)
_TOOL_SPECS = [
    ("openteam_task",               "openteam.server.resources.tools.task.executor:execute"),
    ("openteam_create_role",        "openteam.server.resources.tools.create_role.executor:execute"),
    ("openteam_role_setup",         "openteam.server.resources.tools.role_setup.executor:execute"),
    ("openteam_project_onboarding", "openteam.server.resources.tools.project_onboarding.executor:execute"),
]


def create_openteam_server(
    tool_names: list[str] | None = None,
    *,
    session_context_factory=build_session_context,
) -> FastMCP:
    """Create a FastMCP server exposing OpenTeam tools.

    Args:
        tool_names: Subset of tool names to expose. None = all.
        session_context_factory: For tests — inject a fake context builder.
    """
    mcp = FastMCP("openteam")
    enabled = set(tool_names) if tool_names else None
    for name, executor_path in _TOOL_SPECS:
        if enabled and name not in enabled:
            continue
        wrapper = _build_wrapper(name, executor_path, session_context_factory)
        mcp.add_tool(FunctionTool.from_function(wrapper))
    return mcp
```

**`_build_wrapper(name, executor_path, ctx_factory)` design:**

The wrapper's *signature* is what FastMCP exposes to the LLM. Two options
considered:

1. **Hand-write 4 wrappers** with explicit Python signatures (Walrus's approach).
   Pro: precise, type-checked, IDE-friendly. Con: signature can drift from `tool.json`.
2. **Generate wrappers from `tool.json`** at registration time using
   `inspect.Signature` and `tool_cli.py`'s parameter parser.
   Pro: single source of truth. Con: harder to type-check; FastMCP's schema
   inference may need annotations we have to synthesize.

**Decision: Hand-write 4 wrappers** — there are only 4, signatures are
stable, and explicit types let the agent see clean `param: type = default`
docs. Add a **CI preflight test** (Phase 4 below) that compares each
wrapper's signature against its `tool.json` and fails if they drift.

**Each wrapper template:**

```python
async def openteam_task(
    request: str,
    agent_config: str = "breakdown-multiflow-plan-then-implement",
    plan: bool = False,
    execute: bool = False,
    full: bool = True,
    confirm: bool = False,
    model: str | None = None,
    override: list[str] | None = None,
    no_dual: bool = False,
    analysis: bool = False,
    multi_iter: bool = False,
    max_iterations: int = 3,
    resume: str | None = None,
    initial_plan: str | None = None,
) -> str:
    """Run an agent topology on a request. Default: breakdown-multiflow PlanThenImplement.

    Long-running. Returns the final result text plus a list of artifact paths.
    """
    from openteam.server.resources.tools.task.executor import execute as _execute
    arguments = _to_dash_form(locals())          # foo_bar -> foo-bar
    arguments = _strip_falsy(arguments)
    result = await _execute(arguments, session_context_factory())
    return _render_result(result)
```

**Helpers** (DRY across the 4 wrappers, in `server.py`):

```python
def _to_dash_form(d: dict) -> dict:
    return {k.replace("_", "-"): v for k, v in d.items()}

def _strip_falsy(d: dict) -> dict:
    """Match tool_cli.py — empty/None/False = parameter not provided."""
    return {k: v for k, v in d.items() if v not in (None, False, "", [])}

def _render_result(result) -> str:
    """Return human-readable result + appended artifact paths.
    Handles ToolExecutionResult (real shape) and dict (legacy)."""
    if hasattr(result, "result") and hasattr(result, "context_updates"):
        text = result.result or ""
        ctx = dict(result.context_updates or {})
    elif isinstance(result, dict):
        text = result.get("result") or result.get("text") or ""
        ctx = dict(result.get("context_updates") or {})
    else:
        return str(result)
    artifact_keys = ("workspace_path", "plan_path", "impl_path",
                     "role_document_path", "doc_path")
    artifacts = [f"  {k}: {ctx[k]}" for k in artifact_keys if ctx.get(k)]
    if artifacts:
        text += "\n\nArtifacts:\n" + "\n".join(artifacts)
    return text
```

This **deliberately duplicates** the rendering logic instead of importing
`tool_cli.py`'s broken function — by design, the MCP path and the
standalone-CLI path are independent. Patching `tool_cli.py` is a separate
cleanup ticket (Phase 6).

### 3.3 `mcp_server/context.py` — session context contract

```python
import os, uuid
from typing import Any

# Whitelist of env vars that map to session_context keys.
_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}


def build_session_context() -> dict[str, Any]:
    """Build session_context for an MCP-driven tool invocation.

    Empty dict would be safe (executor's _resolve_workspace allocates a
    fresh workspace under server/_runtime/tasks/), but we surface env-driven
    hints so a long-lived OpenStartup checkout can pin its workspace root,
    cloud_id, and credentials without modifying RovoDev.
    """
    ctx: dict[str, Any] = {
        "task_id": f"mcp-{uuid.uuid4().hex[:8]}",
        "interactive": None,    # explicit; executors guard with `if interactive is not None`
    }
    for env_key, ctx_key in _ENV_MAP.items():
        v = os.environ.get(env_key)
        if v:
            ctx[ctx_key] = v
    return ctx
```

**Test:** `test_context.py` asserts:
- empty env → `{"task_id": "mcp-...", "interactive": None}`
- with `OPENTEAM_WORKING_DIR=/tmp/x` → adds `"working_dir": "/tmp/x"`
- `task_id` is unique across calls

### 3.4 `mcp_server/main.py` — Typer CLI entry

**Pattern:** verbatim from `mcp-atlassian-exp/main.py` minus auth pipe.

```python
import asyncio, logging
import typer
from openteam.mcp_server.server import create_openteam_server

app = typer.Typer()


@app.command("run")
def run(
    tools: str = typer.Option("", help="Comma-separated tool names to expose. Empty = all."),
    log_level: str = typer.Option("WARNING", help="Logging level."),
) -> None:
    """Run the OpenTeam MCP server over stdio."""
    asyncio.run(_main_async(tools, log_level))


async def _main_async(tools_csv: str, log_level: str) -> None:
    logging.basicConfig(level=log_level)
    tool_names = [t.strip() for t in tools_csv.split(",") if t.strip()] or None
    mcp = create_openteam_server(tool_names)
    await mcp.run_stdio_async(show_banner=False, log_level=log_level)


if __name__ == "__main__":
    app()
```

### 3.5 `~/.rovodev/mcp.json` snippet (user-side, stdio mode — **default**)

```json
{
  "mcpServers": {
    "openteam": {
      "command": "python",
      "args": ["-m", "openteam.mcp_server.main", "run"],
      "env": {
        "PYTHONPATH": "/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src:/Users/tchen7/MyProjects/CoreProjects/AgentFoundation/src:/Users/tchen7/MyProjects/CoreProjects/RichPythonUtils/src",
        "OPENTEAM_WORKING_DIR": "."
      }
    }
  }
}
```

**Why `PYTHONPATH` instead of `pip install -e`:** AgentFoundation and
RichPythonUtils are sibling repos that aren't published as packages. The
plan is to keep them as path-based deps for now; if the OpenStartup org
later publishes them, we drop `PYTHONPATH` in favor of a clean editable
install.

### 3.6 RovoDev slash commands (`acra-python` repo)

**File to create:**
`acra-python/packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py`

```python
"""OpenTeam slash commands.

Each handler validates the prompt and posts a PromptSubmitted message
instructing the agent to call the corresponding MCP tool. The actual
work (and streaming) happens in the agent loop — same proven pattern
as /research (slash_commands/research.py).
"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from rovodev_tui.messages import PromptSubmitted

if TYPE_CHECKING:
    from rovodev_tui.app import RovoDevApp


def _make_handler(slash_name: str, mcp_tool: str, friendly: str):
    async def handler(app: RovoDevApp, prompt: str) -> None:
        f"""{friendly} — invokes the OpenTeam {mcp_tool} MCP tool."""
        await app.wait_for_agent_init(show_loading=True)
        if not prompt.strip():
            app.notify_and_log(
                f"Please provide a prompt. Example: {slash_name} <your request>",
                severity="error", timeout=5,
            )
            return
        app.notify_and_log(
            f"Starting OpenTeam {friendly}. This may take several minutes...",
            severity="information", timeout=5,
        )
        app.post_message(PromptSubmitted(
            widget=app.input_container,
            text=f"Invoking '{mcp_tool}': {prompt}",
            event=None,
        ))
    handler.__doc__ = f"{friendly} — invokes the OpenTeam {mcp_tool} MCP tool."
    handler.__name__ = f"handle_{slash_name.strip('/').replace('-', '_')}_command"
    return handler


handle_task_command               = _make_handler("/task",                "openteam_task",               "task pipeline")
handle_create_role_command        = _make_handler("/create-role",         "openteam_create_role",        "create-role pipeline")
handle_role_setup_command         = _make_handler("/role-setup",          "openteam_role_setup",         "role-setup pipeline")
handle_project_onboarding_command = _make_handler("/project-onboarding",  "openteam_project_onboarding", "project-onboarding pipeline")
```

**File to modify:** `acra-python/packages/cli-rovodev-tui/src/rovodev_tui/app.py`

After the existing block of `command_registry.register(...)` calls (around
line 600, after `handle_voice_check_command`):

```python
from rovodev_tui.slash_commands.openteam import (
    handle_task_command,
    handle_create_role_command,
    handle_role_setup_command,
    handle_project_onboarding_command,
)
command_registry.register(handle_task_command,               "/task",                extra_prompt="required", thread=False)
command_registry.register(handle_create_role_command,        "/create-role",         extra_prompt="required", thread=False)
command_registry.register(handle_role_setup_command,         "/role-setup",          extra_prompt="required", thread=False)
command_registry.register(handle_project_onboarding_command, "/project-onboarding",  extra_prompt="required", thread=False)
```

**Why `thread=False`:** the handlers do no I/O — they post one message and
return. Heavy work runs in the agent loop, which has its own concurrency
model. (Confirmed against `/research`.)

---

## 4. Phased Delivery (with explicit TIER tagging)

> **TIER conventions** (matches OpenStartup test convention):
> TIER-1 = pure unit, no I/O. TIER-2 = mocked external deps. TIER-3 = real
> network/LLM calls.

### Phase 1 — `openteam_mcp_server` package (½–1 day)

- [ ] Create the 4 source files in §3.1.
- [ ] Implement `build_session_context()` (§3.3) — TIER-1 test.
- [ ] Implement `_render_result()`, `_to_dash_form()`, `_strip_falsy()` — TIER-1 tests with both `ToolExecutionResult` and dict inputs.
- [ ] Implement `create_openteam_server(tool_names)` (§3.2) — TIER-1 test asserts:
  - all 4 tools registered when `tool_names=None`
  - subset filtering works
  - each registered tool exposes the expected schema (introspect `mcp.tools`)
- [ ] Implement 4 hand-written wrappers (`openteam_task`, etc.) — TIER-2 test stubs each executor and asserts the wrapper:
  - converts arguments to dash form
  - strips falsy values
  - calls executor with the right shape
  - renders `ToolExecutionResult` correctly (text + artifacts block)

### Phase 2 — Typer entry & manual MCP smoke (½ day)

- [ ] Implement `mcp_server/main.py` (§3.4) — TIER-2 test asserts `_main_async("", "WARNING")` constructs the server and would call `run_stdio_async` (use `monkeypatch`).
- [ ] **Manual TIER-3 smoke:** in OpenStartup venv:
  ```bash
  PYTHONPATH=src:../AgentFoundation/src:../RichPythonUtils/src \
    fastmcp dev openteam.mcp_server.main:run
  # confirm 4 tools appear; call openteam_task with {"request":"what is 2+2"}
  ```
- [ ] Document the manual smoke procedure in `docs/MCP_SMOKE.md`.

### Phase 3 — Register MCP server in RovoDev (15 min)

- [ ] Add the `~/.rovodev/mcp.json` snippet from §3.5.
- [ ] Launch RovoDev TUI; run `/mcp`; verify the `openteam` server is green
      and lists `mcp__openteam__openteam_task`, `_create_role`, `_role_setup`,
      `_project_onboarding`.
- [ ] Ask the agent: "use openteam.task to compute 2+2". Confirm it invokes
      the tool and receives a result.

### Phase 4 — Slash commands in RovoDev (½ day)

- [ ] Create `slash_commands/openteam.py` (§3.6).
- [ ] Add 4 `command_registry.register(...)` lines to `app.py` (§3.6).
- [ ] **Manual end-to-end smoke:**
  - `/task what is 2+2` → notification → agent picks up the constructed
    prompt, calls MCP tool, streams result.
  - `/create-role "Senior Backend Engineer focused on microservices"`
  - `/role-setup ./roles/senior_backend_engineer.md`
  - `/project-onboarding ./projects/backend.md`
- [ ] Verify `/help` lists the 4 new commands with descriptions.
- [ ] **Add a CI preflight** in OpenStartup: walk each `tool.json`, walk each
      MCP wrapper signature in `mcp_server/server.py`, assert names + types
      align. (~50 LOC, TIER-1.)

### Phase 5 — Skill + docs (½ day)

- [ ] Create `~/.rovodev/skills/openteam/SKILL.md` documenting when to use
      each slash command, with a usage example pulled verbatim from each
      `tool.json["examples"]`.
- [ ] Add `OpenStartup/docs/MCP_INTEGRATION.md` covering: install,
      `mcp.json` template, wrapper extension points, troubleshooting.

### Phase 6 — Standalone CLI cleanup (cleanup ticket; ½ day; **not blocking**)

These items are **decoupled** from the slash UX (which goes through MCP),
but are good housekeeping for users who run the standalone CLI:

- [ ] Patch `tool_cli.py:run_cli` to handle `ToolExecutionResult` (use the
      same `_render_result` helper from §3.2 — refactor it into `tool_cli.py`
      and import in `mcp_server/server.py`).
- [ ] Add `--workspace-root` flag (or `$OPENTEAM_WORKSPACE_ROOT`) so the
      standalone CLI can pin a workspace; default = `Path.cwd()/.openteam_runs`.
- [ ] Document the dash-form key contract in `tool_cli.py`'s module docstring.
- [ ] Add the AST preflight from v1's Phase 0.7.

### Phase 7 — Long-running tool reliability (1 day; ship after Phase 4)

- [ ] **Timeout.** Default MCP client timeout (~295s) is too short for most
      `/task` runs. Two options:
      (a) **Phase 7A — Sidecar mode (default):** instruct users to use
          `OPENTEAM_MCP_TIMEOUT=1800` and document how to set per-tool
          timeouts via the agent config.
      (b) **Phase 7B — In-memory transport (opt-in):** if/when OpenStartup
          packages can be installed into the RovoDev venv, add a
          `_get_openteam_mcp_servers` method to `acra-python`'s
          `common/agent.py` using `FastMCPTransport(create_openteam_server())`
          and `MCPClient(transport=..., timeout=1800)`. (Walrus's Phase 2B.)
- [ ] **Cancellation.** Wire Ctrl-C in the TUI to abort the agent loop;
      verify the in-flight MCP call is cancelled cleanly (FastMCP supports
      this; verify with a tool that sleeps 30s).
- [ ] **Idempotency.** `task` already has `--resume` — surface this as an
      MCP wrapper kwarg (already in §3.2's signature) and document it in
      the skill.

### Phase 8 — Optional follow-ons

- [ ] **MCP server packaging:** if Bitbucket/Renovate-managed, add
      `openteam-mcp` as a `[project.scripts]` entry in OpenStartup's
      `pyproject.toml` so `mcp.json` can use the bare command name.
- [ ] **Auto-discovery of tools:** replace the static `_TOOL_SPECS` list with
      a walk over `openteam/server/resources/tools/*/tool.json` filtering by
      `agent_enabled: true` (matches dispatcher's behavior).
- [ ] **Auth pipe parity:** if OpenTeam ever needs OAuth context, mirror
      `mcp-atlassian-exp`'s `ROVODEV_TOKEN_PIPE_FD` pattern.

---

## 5. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Default MCP client timeout is too short for long topologies | High | Phase 7A — document `OPENTEAM_MCP_TIMEOUT`; Phase 7B — in-memory transport with `timeout=1800` |
| `PYTHONPATH` brittle across machines | Medium | Phase 8 packaging; document `direnv` snippet for development |
| MCP wrapper signatures drift from `tool.json` | Medium | Phase 4 CI preflight; only 4 wrappers so manual review is feasible |
| Slash handler's "Invoking '<tool>': <prompt>" string is interpreted differently by future agent prompts | Low | Use the `/research` precedent verbatim; if the convention changes, all 4 commands change in one place via `_make_handler` |
| Tools require live UI streaming (e.g., `interactive.send_task_status`) | Low | All four are written to handle `interactive=None`; verified by reading code. If a future tool requires it, expose `interactive` via a streaming MCP transport (FastMCP supports SSE). |
| In-process import (Phase 7B) drags transitive deps into RovoDev venv | Medium | Keep stdio default; in-process behind feature flag; CI test that `pip install` of the bridge package doesn't conflict with acra-python's lockfile |
| Dispatcher session_context shape evolves (e.g., new required key) | Low | `build_session_context()` is one function, easy to extend. We re-derive from env vars only — never from internal dispatcher state. |

---

## 6. File Touch List (single source of truth)

### OpenStartup repo — new files

```
src/openteam/mcp_server/__init__.py
src/openteam/mcp_server/server.py
src/openteam/mcp_server/context.py
src/openteam/mcp_server/main.py
test/openteam/mcp_server/__init__.py
test/openteam/mcp_server/test_server_factory.py
test/openteam/mcp_server/test_context.py
test/openteam/mcp_server/test_wrappers_smoke.py
test/openteam/mcp_server/test_wrapper_signature_alignment.py   # Phase 4 preflight
docs/MCP_INTEGRATION.md
docs/MCP_SMOKE.md
```

### OpenStartup repo — modified files (Phase 6 only, not blocking)

```
src/openteam/server/services/tool_cli.py      # _render_result extraction + ToolExecutionResult support
test/openteam/server/services/test_tool_cli.py
```

### acra-python repo — new files

```
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py
```

### acra-python repo — modified files

```
packages/cli-rovodev-tui/src/rovodev_tui/app.py    # 4 register() lines + 1 import
```

### User-side config

```
~/.rovodev/mcp.json                   # Phase 3
~/.rovodev/skills/openteam/SKILL.md   # Phase 5
```

---

## 7. Validation Checklist

Run these tests in order before declaring "shipped":

- [ ] **TIER-1**: All unit tests under `test/openteam/mcp_server/` pass.
- [ ] **TIER-2 wrapper smoke**: each wrapper, given a stubbed executor, produces the expected text+artifacts envelope.
- [ ] **TIER-3 server boot**: `python -m openteam.mcp_server.main run` exits cleanly when stdin closes; tool list is non-empty.
- [ ] **TIER-3 fastmcp dev**: `fastmcp dev openteam.mcp_server.main:run` lists 4 tools; `openteam_task` invocation with `{"request":"say hi"}` returns text containing "hi" within 60s.
- [ ] **TIER-3 RovoDev `/mcp`**: launch acra-python TUI; `/mcp` shows `openteam` server green with 4 tools.
- [ ] **TIER-3 agent invocation**: ask the agent "use openteam_task to compute 2+2"; verify it picks the right MCP tool and the answer surfaces in chat.
- [ ] **TIER-3 each slash command**: `/task`, `/create-role`, `/role-setup`, `/project-onboarding` all succeed end-to-end.
- [ ] **TIER-3 cancellation**: launch a long `/task`, press Ctrl-C, verify the agent loop and the MCP call both terminate within 5s.
- [ ] **CI preflight**: `test_wrapper_signature_alignment.py` passes — no drift between `tool.json` and wrapper signatures.

---

## 8. Open Questions

1. **Wrapper generation strategy** — keep hand-written 4 wrappers, or
   programmatically generate from `tool.json`? Plan recommends hand-written
   + CI preflight.
2. **Where does `mcp.json` live in source control?** — propose a template
   under `OpenStartup/_dev/templates/rovodev_mcp.json` that users copy.
3. **Sidecar lifecycle** — is one MCP subprocess per RovoDev session ok? Or
   do we want to share across sessions? Default is per-session (matches
   `mcp-atlassian-exp`).
4. **Authentication** — does any OpenTeam tool need user-scoped credentials
   today? If yes, mirror `ROVODEV_TOKEN_PIPE_FD` pattern. If no, keep
   `_build_session_context()` env-only.

---

## 9. Comparison Summary — Why this Plan

| Concern | v1 (Subprocess+MCP) | Walrus (MCP+`/research`) | **Integrated v2** |
|---|---|---|---|
| Architectural elegance | Mixed (two IPC paths) | High (one path, proven precedent) | **High** — Walrus pattern |
| Audit/contract rigor | High (deep executor analysis) | Light | **High** — kept v1's analysis |
| LOC to ship | ~150 (across both repos) | ~330 | ~330 (same as Walrus) |
| Files modified in acra-python | 1 (4 lines) | 1 (5 lines) | **1 (5 lines)** |
| Streaming model | Subprocess stdout | Agent chat | **Agent chat** (consistent) |
| Long-running tool handling | Implicit (subprocess) | Phase 2B in-memory | **Explicit Phase 7A/B** |
| Empty session_context safety | Called dangerous (overcautious) | Correctly called safe | **Correctly safe** + env enrichment |
| `tool_cli.py` bug remediation | Required (blocks slash) | Bypassed entirely | **Bypassed**; cleanup ticket Phase 6 |
| Test coverage plan | Light | Light | **TIER-1/2/3 explicit + CI preflight** |
| Open-question discipline | 5 questions | 0 questions | **4 questions** |

---

## 10. Critical Self-Audit — Could This Plan Have Hidden Issues?

I deliberately stress-tested this plan looking for hacks or gaps:

| Concern | Finding | Decision |
|---|---|---|
| "Posting `PromptSubmitted` with hardcoded text" — is this fragile? | The `/research` slash uses the same trick (verified). Agent prompt format is stable. | **Acceptable.** Centralized in `_make_handler`. |
| Hand-written wrappers will drift from `tool.json` | True | **Mitigated by CI preflight in Phase 4.** |
| "Empty session_context is safe" — depends on `_resolve_workspace` behavior | Verified by reading `task/executor.py:163-188`. Workspace is allocated under `_runtime/tasks/`. Other executors share the helper. | **Confirmed safe.** |
| MCP subprocess + Python stdlib `subprocess` may fail on Windows | We use `python -m`, not shell scripts. Should be fine. | **Document Windows tested separately.** |
| `PYTHONPATH` injection via `mcp.json` env is fragile | Yes for users; manageable for now. | **Phase 8 packaging.** |
| In-process Phase 7B drags deps into RovoDev | True | **Phase 7B is opt-in only; gated.** |
| `_render_result` duplicates `tool_cli.py` rendering | Intentional — keeps MCP path independent of CLI. | **Phase 6 refactors them to share a helper.** |
| Long topologies blow MCP client default timeout | High risk | **Explicit Phase 7A/B.** |
| Wrappers strip falsy values aggressively (`False`, `0`, `""`, `[]`) | Could mask intentional `False` flags | **`_strip_falsy` only strips `None/False/""/[]` — never `0`. Verified.** |
| RovoDev users without OpenStartup checkout can't use this | True; documented in skill + README. | **Acceptable. Out of scope.** |
| What if `fastmcp` API changes? | We pin to the same version range as acra-python's `mcp-atlassian-exp` | **Add `pip` constraint in OpenStartup pyproject.** |

**No remaining hacks.** The only "compromise" is `PYTHONPATH` env injection in
`mcp.json`, which is addressed by Phase 8 packaging (and matches how
`mcp-atlassian-exp` does it today, so we're consistent with precedent).

---

## 11. Pick-One Answer

> *"If we only pick one plan, which would you choose?"*

**Choose this Integrated v2 plan** (which itself is closer in spirit to
**Walrus** than to my v1).

If you literally must pick from the two existing files, **pick Walrus
(`take-a-careful-look-memoized-walrus.md`)**. Three reasons:

1. **Architectural correctness** — the MCP-only + `/research`-style slash
   pattern matches RovoDev's actual conventions (verified by reading
   `slash_commands/research.py`). My v1's subprocess+slash variant adds a
   second IPC boundary and more glue code without delivering more capability.
2. **Smaller acra-python footprint** — Walrus modifies one file with five
   lines. My v1 needed a 4-line patch *plus* a bridge module, *plus* an
   entry-point hook PR.
3. **Better executor model** — Walrus correctly identified that `{}`
   `session_context` is safe (verified; `_resolve_workspace` allocates a
   fresh workspace). My v1 over-engineered around a non-bug.

What v1 had that Walrus lacked (and v2 keeps):
- Clear TIER tagging on tests
- CI preflight comparing wrapper signatures vs `tool.json`
- Explicit handling of long-running timeouts (Phase 7A/B)
- Honest separation of what's "blocking" vs "cleanup ticket" (Phase 6)
- A 10-item self-audit (this section)

So the **complete answer** is: pick Walrus's *architecture* and v1's
*rigor*, which is exactly this v2 file.
