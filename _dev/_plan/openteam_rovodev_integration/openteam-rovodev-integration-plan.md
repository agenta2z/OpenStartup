# Integrating OpenTeam as a RovoDev Plugin/Sidecar

**Date:** 2026-05-08 (updated 2026-05-08 04:45 — second reconciliation against the user's "Critical Audit Complete" findings + re-read source)
**Author:** Rovo Dev (investigation + plan)
**Goal:** Make OpenTeam (`/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam`) usable from inside the RovoDev TUI (`/Users/tchen7/MyProjects/atlassian_packages/acra-python`) so that backslash/slash commands such as `/task`, `/create-role`, `/role-setup` invoke OpenTeam's framework and stream results back into the Rovo Dev chat.

---

## ⚡ 2026-05-08 UPDATE — v3 CLI Unification Plan Has Shipped

`task-cli-unification-INTEGRATED-v3.md` has been **substantially executed**. This changes the
recommended integration strategy: a major chunk of the work this plan
originally proposed (a `tool.json`-driven argument parser, a uniform
in-process invocation surface, standalone CLI binaries) is **already in main**.
This update incorporates the new reality.

### What now exists in OpenTeam (verified by reading source 2026-05-08)

| Artifact | Path | Purpose |
|---|---|---|
| **Generic CLI scaffold** | `src/openteam/server/services/tool_cli.py` (129 LOC) | `build_parser(tool_json_path, mutually_exclusive_groups)` and `run_cli(tool_json, execute_fn, argv, mutex_groups)`. Fully tool.json-driven (positional, `--flag`, `--int`, `--path`, `repeatable`, `choices`, `default`). |
| **`task` standalone CLI** | `src/openteam/server/resources/tools/task/cli.py` + `__main__.py` | Runnable as `python -m openteam.server.resources.tools.task ...`. Uses `_MODE_MUTEX = [{"--plan","--execute","--full","--confirm"}]`. |
| **`role_setup` standalone CLI** | `src/openteam/server/resources/tools/role_setup/cli.py` + `__main__.py` | Runnable as `python -m openteam.server.resources.tools.role_setup ...`. |
| **`create_role` standalone CLI** | `src/openteam/server/resources/tools/create_role/cli.py` + `__main__.py` | Runnable as `python -m openteam.server.resources.tools.create_role ...`. |
| **Production topologies dir** | `src/openteam/server/resources/tools/task/topologies/` | 10 YAMLs incl. `breakdown_multiflow_plan.yaml`, `pti.yaml`, `bta.yaml`, `dual.yaml`, etc. Promoted out of `test/`. |

### Implications for the integration plan

1. ✅ **Argument parser is solved.** My original plan §3.4 had a hand-rolled
   `_parse_args(extra: str, tool_def: dict)`. **Drop it.** Reuse
   `openteam.server.services.tool_cli.build_parser(...)` directly — both the
   slash handler and the MCP wrapper now share OpenTeam's own parser, so they
   can never drift from the slash command's surface.

2. ✅ **Invocation surface is uniform.** Each tool has a `cli.main(argv)` entry
   point. The slash handler can shell out (`python -m openteam.server.resources.tools.<name> ...`)
   for true process isolation, **or** call `cli.main(argv_list)` in-process,
   **or** call `executor.execute(arguments, session_context)` directly. We get
   three integration tiers for free.

3. ⚠️ **Bug spotted in `tool_cli.run_cli`** (will affect any direct CLI use,
   so worth filing now): line 121 reads `result.get("text", "")` but the real
   executors return `ToolExecutionResult` (a Pydantic-like object with `.result`
   and `.context_updates`, see `task/executor.py:467`, `role_setup/executor.py:1278`,
   `create_role/executor.py:585`). On a real run this prints an empty line and
   silently drops `.result`. Fix: render via `getattr(result, "result", None) or
   (result.get("text") if isinstance(result, dict) else str(result))`. Trivial
   patch; we should land it before the slash UX depends on it.

4. ⚠️ **`slash_enabled` flag still only set on `task`.** `role_setup` and
   `create_role` `tool.json` files do **not** carry `"slash_enabled": true`
   (verified). For Phase 3 we still need the two-line edit to flip those flags
   (or the slash registrar can lazily ignore the flag and register all
   `is_bridge`-flagged tools — see §3.4-revised below).

5. ✅ **Topologies are now first-class production assets** at
   `task/topologies/*.yaml` — the MCP server / slash handler can advertise them
   as `--agent-config` choices automatically (`os.listdir`-style discovery),
   replacing the static `choices` list in `tool.json`.

6. 🆕 **New first-class integration option ("Mechanism D"):** because
   `python -m openteam.server.resources.tools.task` now works, the simplest
   slash handler is just a thin wrapper around `asyncio.create_subprocess_exec(...)`
   that streams stdout — no in-process import of OpenTeam needed at all. This
   makes the integration **dependency-free for acra-python** (no `openteam`
   package required in the RovoDev venv).

The detailed plan below is updated in-place to reflect these changes. Sections
that are now obsolete are marked **~~strikethrough~~** with a forward pointer.
The **Phased Delivery Plan in §4 is fully revised**.

---

## 🔬 2026-05-08 04:45 SECOND UPDATE — Critical Audit Reconciliation

A critical audit of the v3 implementation surfaced multiple correctness issues
that weren't fixed despite the implementer's "all phases complete ✓" report.
Re-reading the actual source confirms **all the audit's CRITICAL findings are
still present in `tool_cli.py` as of 2026-05-08 04:45**:

### Audit findings — verified status

| # | Finding (from user's audit) | Verified by re-reading source? | Where | Severity |
|---|---|---|---|---|
| 🔴 **1** | `session_context = {}` is empty; will crash inside executor | ✅ **CONFIRMED unfixed** at `tool_cli.py:110` | Real executors *call* `session_context.get(...)` (e.g. `task/executor.py:174`, dispatcher constructs it with `server_dir`, `working_dir`, `interactive`, `task_id`). An empty dict is technically defensible (every reader uses `.get(...)`) **but** loses critical capabilities (UI streaming, working dir, server-managed task workspace). | High |
| 🔴 **2** | `result.get("text", "")` reads the wrong key | ✅ **CONFIRMED unfixed** at `tool_cli.py:121` | All three executors return `await _run_topology(...)` which ultimately produces a `ToolExecutionResult` (Pydantic model with `.result` and `.context_updates`, see dispatcher line 234). On a real run `tool_cli` will reach the `else: print(result)` branch and dump the whole repr — ugly but at least visible. The `if isinstance(result, dict)` branch is **dead code** today. | High |
| 🟡 **3** | Argument key normalization (`_` → `-`) silently inverts argparse's behavior | ✅ **CONFIRMED at `tool_cli.py:114-116`** | `executor.execute()` actually reads **both** shapes (`arguments.get("agent-config") or arguments.get("agent_config")`, line 481), so this works *by accident*. Document it; do not rely on it for new tools. | Medium |
| 🟡 **4** | `_MODE_MUTEX` enforced at parser level but executor *also* re-checks (line 493) | ✅ Confirmed. Defense-in-depth, no bug. | Acceptable. | Low |
| 🟢 **5** | `yaml.safe_load()` doesn't resolve `_import_` directives → preflight test reports "no `output_is_deliverable: true` found" because the planner subtree is in the imported `breakdown_multiflow_plan.yaml` | ✅ **FIXED** in `test_yaml_deliverable_flags_set.py` — now uses `load_config(...)` from `rich_python_utils.config_utils` with explicit overrides for `_target_path`, `templates_dir`, `_params.workspace_root`. | This is a **TEST-side fix**. The runtime YAML loader (`task/executor.py:390`) already used `load_config()` so the runtime was fine. | Resolved |

### Implications for the integration plan

The previously-merged Phase 0.5 (rendering bug) is **still required**, and we
now add **Phase 0.6** (session_context construction) and **Phase 0.7**
(argument-key contract documentation):

- **Phase 0.5** — must handle `ToolExecutionResult` (the real return type),
  not assume dict.
- **Phase 0.6 (NEW)** — `tool_cli.run_cli` must construct a *minimal viable*
  `session_context` with at least `working_dir` (cwd or `--workspace-root`
  override) so `_resolve_workspace` doesn't fall back to the temp-dir path
  that loses provenance, **and** must set `interactive=None` defensively (the
  executors and `_run_topology` all `.get()` it). Without this the standalone
  CLI is technically running but with degraded artifact paths.
- **Phase 0.7 (NEW)** — document the dual key-shape contract and add a
  preflight assertion that *new* tools use either the dash-form (`--agent-config`
  → `agent-config`) **or** the underscore-form, not silently rely on the
  executor reading both.

These are **5–10 LOC each**, but they convert the CLI from "works for `--help`"
to "works for a real run". They are now wired into §4 below.

### What this means for slash-command UX

Variant D (subprocess shell-out, recommended in the previous update) is
**still the right default** because it isolates RovoDev from these
correctness issues — RovoDev just streams stdout/stderr. But: until Phases
0.5–0.7 land, *any* invocation of `python -m openteam.server.resources.tools.<tool>`
on a non-trivial input will (a) print mangled output and (b) lose UI affordances
like streaming task status. **Do not ship Phase 3 (the slash-command UX) until
Phases 0.5/0.6/0.7 are merged.**

---

## 0. TL;DR — Recommended Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Rovo Dev TUI (acra-python)                                      │
│                                                                  │
│   user types:  /task <request>                                   │
│        │                                                         │
│   SlashCommandRegistry.dispatch  ──┐                             │
│                                    ▼                             │
│   handle_openteam_command(app,extra_prompt)  ◄── thin shim       │
│        │                                                         │
│        │  (1) in-process import (default)                        │
│        │      from openteam.server.services.tool_dispatcher      │
│        │           import ToolDispatcher                         │
│        │      await dispatcher("task", arguments)                │
│        │                                                         │
│        │  (2) sidecar mode (optional)                            │
│        │      POST http://127.0.0.1:<port>/tools/<name>          │
│        │      (uvicorn child started by openteam-bridge skill)   │
│        ▼                                                         │
│   stream stdout / SSE → CommandHelp / TaskCard widgets           │
└──────────────────────────────────────────────────────────────────┘
```

Two complementary layers:

1. **`openteam-bridge` Skill** (lives in `~/.rovodev/skills/openteam-bridge/`)
   – discoverable, opt-in, no fork of acra-python required to start prototyping.
2. **`rovodev-openteam-tui-ext` Python package** that ships a
   `SlashCommandRegistry`-aware extension. Loaded via a small one-line patch
   in `rovodev_tui/app.py` *or* through a future "user slash commands" hook
   we propose adding upstream.

Same backend (`OpenTeamBridge`) is reused by both layers, so a user can adopt
the integration immediately via the skill route, and we upstream the hard
slash-command wiring later.

---

## 1. Investigation Findings (verified by reading source)

### 1.1 RovoDev (acra-python) — what already exists

| Concern | Where | Notes |
|---|---|---|
| TUI app | `packages/cli-rovodev-tui/src/rovodev_tui/app.py` (`RovoDevApp`) | hosts `command_registry = SlashCommandRegistry()` (line 515). |
| Slash command registry | `packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/registry.py` | `register(handler, command, help, short_help, show, extra_prompt, thread)` and `dispatch(prompt, app)` (longest-prefix match). |
| Slash handler signature | `async def handler(app: RovoDevApp, extra_prompt: str) -> None` | example: `handle_shell_command` in `slash_commands/shell.py`. `thread=True` runs in a Textual worker thread (use `app.call_from_thread(...)` for UI). |
| Skills system | `packages/cli-rovodev/src/rovodev/modules/skills.py` (delegates to `nemo.core.load_skills_from_dirs`) | discovery roots: built-in, `~/.rovodev/skills/`, `~/.agents/skills/`, `~/.claude/skills/`, `~/.codex/skills/`, project `.rovodev/skills/`, `.agents/skills/`. SKILL.md = YAML frontmatter + Markdown body, cross-tool open standard. |
| MCP system | `packages/cli-rovodev/src/rovodev/modules/mcp_utils.py` + `~/.rovodev/mcp.json` | supports `stdio`, `http`, `stateless-http`, `sse` transports. `app.agent_def.all_mcp_servers` is the runtime list shown by `/mcp`. |
| Custom prompts (closest *user-defined* slash UX today) | `.rovodev/prompts.yml` with `content_file: foo.md`; invoked as `/prompts <name> <args>` or shorthand `!<name>` | does **not** call native Python — only injects prompt text. Insufficient for invoking OpenTeam's executors directly. |
| Sub-agents | `.rovodev/subagents/*.md` | markdown-defined delegated agents — can be invoked via the existing `invoke_subagents` tool, not via slash command. |

**Key insight #1:** RovoDev does **not** today have a *user-extensible slash-command directory*. Slash commands are all wired in code at `app.py:515-580`. To get true `/task`, `/create-role`, `/role-setup` slash commands without forking, we either (a) ship a tiny acra-python patch, or (b) lean on MCP + skill so the model invokes the same OpenTeam tools through the agentic loop.

**Key insight #2:** RovoDev already runs MCP servers as sidecar processes via `mcp.json`. OpenTeam already exposes a clean dispatcher (see 1.2). Wrapping OpenTeam in a tiny FastMCP server is the lowest-friction path to *agentic* invocation; the slash-command shim is the additional UX we want.

### 1.2 OpenTeam — what already exists

| Concern | Where | Notes |
|---|---|---|
| Tool registry | `src/openteam/server/resources/tools/*/tool.json` (one per tool) | declarative; key fields: `name`, `executor`, `parameters`, `asynchronous`, `slash_enabled`, `agent_enabled`. Already lists 27 tools (task, create_role, role_setup, project_onboarding, slack_*, twg_*, mock_task). |
| Dispatcher | `src/openteam/server/services/tool_dispatcher.py` | `class ToolDispatcher`. `__call__(tool_name, arguments) -> ToolExecutionResult`. Imports `module:callable` from each `tool.json["executor"]`. Supports async tasks with `_dispatch_as_task` that streams via a `WebSocketInteractive`. |
| Server entry | `src/openteam/server/main.py` | FastAPI + lifespan + SPA. Tool dispatch is exposed both via REST routes and via the dispatcher class directly. |
| Tool I/O contract | `async def execute(arguments: dict, session_context: dict) -> ToolExecutionResult` where `result.result: str`, `result.context_updates: dict`, optional artifacts (workspace_path, plan_path, impl_path, role_document_path). | Same shape across all tools — perfect for a uniform bridge. |
| Already-`slash_enabled` tool | `task` (`tool.json` line: `"slash_enabled": true`). | Other tools (create_role, role_setup) are agent_enabled but not slash_enabled — this plan extends slash exposure. |

### 1.3 Both projects are Python ✓

- acra-python: Python 3.13 (`uv` managed), Textual TUI.
- OpenTeam: Python (FastAPI, asyncio); `agent_foundation` is the shared protocol package importing `ToolExecutionResult`.

So **direct in-process import is feasible** if we install OpenTeam (and its deps, notably `agent_foundation`) into the acra-python venv, **or** we keep them isolated by running OpenTeam as a sidecar.

---

## 2. Four Integration Mechanisms — Comparison (updated)

| # | Mechanism | What it gets us | Cost | Verdict |
|---|---|---|---|---|
| **A** | **MCP server wrapping OpenTeam** (`openteam-mcp` FastMCP server registered via `~/.rovodev/mcp.json`) | All OpenTeam tools become *agentic* tools — model can call them. Listed in `/mcp`. Zero changes to acra-python. | Build a thin FastMCP shim that calls each tool's `cli.main(argv)` (or `executor.execute(...)`); runs as stdio subprocess. | **Ship first**. Lowest risk. Cleanest cross-process boundary. Now even simpler thanks to `tool_cli.py`. |
| **B** | **Skill (`openteam-bridge`) + agentic invocation** | Skill instructs model on when/how to call openteam tools (loaded via A). Optional Python helpers in skill provide convenience. | One SKILL.md file. | **Ship with A.** Together A+B make OpenTeam first-class through the agentic loop, no code changes to RovoDev. |
| **C** | **Native slash commands** (`/task`, `/create-role`, `/role-setup`) wired into `SlashCommandRegistry` | Users type the slash and it runs in-process or via the bridge. Mirrors OpenTeam's `slash_enabled: true` flag exactly. | (a) 4-line patch to `rovodev_tui/app.py`, or (b) entry-point hook upstream. | **Ship as Phase 3.** Provides the UX the user explicitly asked for. |
| **D 🆕** | **Subprocess-only slash** — `asyncio.create_subprocess_exec("python","-m","openteam.server.resources.tools.task", ...)` from a thin RovoDev slash handler. **No `openteam` import in acra-python venv at all.** | True process isolation. Zero coupling. Streaming stdout flows into chat naturally. Works as long as `OPENTEAM_HOME` env points at an installed checkout. | One small handler per tool (≈30 LOC each, or one generic handler that takes the tool name as a parameter). | **Default Phase-3 path.** Avoids the dependency-conflict risk of in-process import; uses the CLI work that v3 already shipped. |

We do **all four**. A+B unblock immediately via MCP; D delivers the explicit
slash UX with maximum isolation; C is the in-process variant if/when it's
worth the venv coupling for a richer streaming experience.

---

## 3. Architecture in Detail

### 3.1 `openteam-bridge` package (new)

A small Python package living at `CoreProjects/OpenStartup/src/openteam_bridge/` with the following responsibilities:

```
openteam_bridge/
├── __init__.py
├── bridge.py           # OpenTeamBridge — sole gateway to OpenTeam
├── mcp_server.py       # FastMCP server exposing tools (mechanism A)
├── tui_extension.py    # Slash command handlers + register() (mechanism C)
├── streaming.py        # Streaming adapters: WebSocketInteractive ↔ Textual widgets
└── skill/
    └── SKILL.md        # symlinked to ~/.rovodev/skills/openteam-bridge/SKILL.md
```

**`OpenTeamBridge`** is a singleton wrapper around `ToolDispatcher` that:

1. Locates the OpenTeam `tool.json` registry (env var `OPENTEAM_HOME`, default
   `~/MyProjects/CoreProjects/OpenStartup`).
2. Builds a `dict[str, ToolDefinition]` by walking
   `src/openteam/server/resources/tools/*/tool.json`.
3. Lazily constructs `ToolDispatcher(tool_registry, integration_executor=NullExec(), session_context={...})`.
4. Provides:
   - `list_tools() -> list[dict]` (filtered by `slash_enabled` / `agent_enabled`).
   - `async invoke(name, arguments, *, on_event=None) -> ToolExecutionResult`.
   - `async stream(name, arguments) -> AsyncIterator[Event]` (wraps `WebSocketInteractive` with an in-memory event bus).

This is the **single point of contact** with OpenTeam — both A and C share it.

### 3.2 Mechanism A — FastMCP server (`openteam_bridge.mcp_server`)

```python
# openteam_bridge/mcp_server.py
from fastmcp import FastMCP
from openteam_bridge.bridge import OpenTeamBridge

bridge = OpenTeamBridge.get()
mcp = FastMCP("openteam")

for tool_def in bridge.list_tools(filter_=("agent_enabled",)):
    @mcp.tool(name=tool_def["name"], description=tool_def["description"])
    async def _tool(**arguments):  # closure on tool_def via factory
        result = await bridge.invoke(tool_def["name"], arguments)
        return {"result": result.result, "artifacts": result.context_updates}

if __name__ == "__main__":
    mcp.run()  # stdio transport
```

User config in `~/.rovodev/mcp.json`:

```json
{
  "mcpServers": {
    "openteam": {
      "command": "uv",
      "args": ["run", "--project", "/Users/tchen7/MyProjects/CoreProjects/OpenStartup",
               "python", "-m", "openteam_bridge.mcp_server"],
      "env": {
        "OPENTEAM_HOME": "/Users/tchen7/MyProjects/CoreProjects/OpenStartup"
      },
      "transport": "stdio"
    }
  }
}
```

Once this is in place every OpenTeam tool shows up in `/mcp`, and the agentic
loop can call it directly — confirming the "is this possible?" question is **yes**.

### 3.3 Mechanism C — Native Slash Commands

Three sub-options for wiring slash commands into RovoDev:

#### Option C1 — Local user patch (fastest)

Add at end of `rovodev_tui/app.py` (just after the existing block of
`command_registry.register(...)` calls, ~line 580):

```python
try:
    from openteam_bridge.tui_extension import register_openteam_commands
    register_openteam_commands(command_registry)
except ImportError:
    pass  # OpenTeam bridge not installed — that's fine
```

This is a 4-line, backward-compatible change. Users opt in by `pip install -e .`
of `openteam-bridge` into the acra-python venv.

#### Option C2 — Entry-point auto-discovery (preferred upstream PR)

Propose to acra-python team: after the in-tree `command_registry.register(...)`
block, scan setuptools entry points:

```python
# new in app.py
from importlib.metadata import entry_points
for ep in entry_points(group="rovodev.slash_commands"):
    ep.load()(command_registry)  # signature: (registry: SlashCommandRegistry) -> None
```

`openteam-bridge`'s `pyproject.toml` then declares:

```toml
[project.entry-points."rovodev.slash_commands"]
openteam = "openteam_bridge.tui_extension:register_openteam_commands"
```

This generalizes to *any* third-party plugin (not just OpenTeam) and is the
canonical Python pattern. We submit this as an upstream PR (~30 LOC).

#### Option C3 — Config-driven slash commands

Mirror `~/.rovodev/prompts.yml` with `~/.rovodev/slash_commands.yml`:

```yaml
slash_commands:
  - command: /task
    handler: openteam_bridge.tui_extension:handle_task
    extra_prompt: required
    thread: true
    short_help: Run an agent topology on a request via OpenTeam.
```

Loaded by a new helper in `rovodev_tui/app.py`. Marginally less type-safe than
C2 but gives non-Python users a way to register commands.

> **Recommendation:** Ship **C1** in this repo immediately to unblock; submit
> **C2** as the upstream PR; treat C3 as a follow-on once we know which user
> personas actually need YAML registration.

### 3.4 Slash handler skeleton (revised — uses v3's `tool_cli.build_parser`)

The hand-rolled `_parse_args` from the original draft is **deleted**. We now
call OpenTeam's own `build_parser` so slash + standalone CLI cannot drift.

There are two variants depending on whether we run in-process (Mechanism C) or
out-of-process (Mechanism D).

#### Variant D (recommended default — subprocess, no openteam import)

```python
# openteam_bridge/tui_extension_subproc.py  (lives in OpenStartup repo)
from __future__ import annotations
import asyncio
import json
import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from rovodev_tui.widgets import CommandHelp, ShellOutput, ThinkingSpinner

if TYPE_CHECKING:
    from rovodev_tui.app import RovoDevApp
    from rovodev_tui.slash_commands.registry import SlashCommandRegistry


# Path discovered once at register time. Honors $OPENTEAM_HOME,
# else falls back to the repo this module ships in.
def _openteam_home() -> Path:
    return Path(os.environ.get("OPENTEAM_HOME") or
                Path(__file__).resolve().parents[3])  # …/OpenStartup


def _tool_modules() -> dict[str, str]:
    """Map slash command → python -m module path. Drives auto-registration."""
    base = "openteam.server.resources.tools"
    return {
        "/task":        f"{base}.task",
        "/create-role": f"{base}.create_role",
        "/role-setup":  f"{base}.role_setup",
    }


def _make_handler(slash: str, module: str):
    async def handler(app: "RovoDevApp", extra_prompt: str) -> None:
        # extra_prompt is the verbatim text after the slash command.
        # OpenTeam's CLI parser already understands it — no local parsing.
        argv = shlex.split(extra_prompt)
        out = ShellOutput()
        spinner = ThinkingSpinner(f"Running OpenTeam {slash}")
        app.call_from_thread(app.chat_container.mount, out)
        app.call_from_thread(app.chat_container.mount, spinner)

        # Use the user's preferred python; fall back to current sys.executable
        # via "uv run" for venv hygiene if the OpenStartup project is uv-managed.
        cmd = ["uv", "run", "--project", str(_openteam_home()),
               "python", "-m", module, *argv]
        env = {**os.environ, "OPENTEAM_HOME": str(_openteam_home())}

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, env=env,
            cwd=str(_openteam_home()),
        )
        try:
            assert proc.stdout
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                app.call_from_thread(out.append, line.decode("utf-8", "replace"))
            await proc.wait()
        finally:
            app.call_from_thread(spinner.remove)
            if proc.returncode:
                app.notify(f"{slash} exited with code {proc.returncode}",
                           severity="error", timeout=8)

    handler.__doc__ = f"Run OpenTeam's {slash[1:]} tool. " \
                      f"Args after the slash are forwarded to the tool's CLI."
    return handler


def register_openteam_commands(registry: "SlashCommandRegistry") -> None:
    for slash, module in _tool_modules().items():
        registry.register(
            _make_handler(slash, module),
            slash,
            extra_prompt="required" if slash != "/task" else "allowed",
            thread=True,  # subprocess + I/O → worker thread
        )
```

#### Variant C (in-process, when you want richer streaming)

Same shape, but instead of `create_subprocess_exec` we call:

```python
from openteam.server.resources.tools.task.cli import main as task_main
# task_main(argv) blocks until the task finishes; runs through the same
# tool_cli.build_parser path, so flag handling is identical to the subprocess
# variant. Wrap in an executor or asyncio.to_thread() to keep the UI loop free.
result_code = await asyncio.to_thread(task_main, shlex.split(extra_prompt))
```

For richer streaming we capture the executor's `interactive` events through an
`InMemoryInteractive` shim (still defined in `streaming.py`, §3.5).

#### Auto-discovery (alternative to the static `_tool_modules` map)

Once we trust the `slash_enabled` flag, we can replace the static dict with a
walk over `openteam/server/resources/tools/*/tool.json`, registering every
tool whose `slash_enabled` is `true`. This is the same pattern OpenTeam's own
dispatcher already uses (`tool_dispatcher.py:_load_executors`).

> **Required follow-on edit:** flip `"slash_enabled": true` in
> `role_setup/tool.json` and `create_role/tool.json` (currently absent).
> Two-line PR; or accept the static map above as the source of truth.

### 3.5 Streaming bridge (`streaming.py`)

OpenTeam's async dispatcher streams progress through a `WebSocketInteractive`
sink. We provide an `InMemoryInteractive` shim:

```python
class InMemoryInteractive:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
    async def send_task_status(self, task_id, status, **kw):
        await self.queue.put({"type": "task_status", "task_id": task_id, "status": status, **kw})
    async def _send(self, payload: dict):
        await self.queue.put(payload)
```

`OpenTeamBridge.stream(...)` injects this shim into `session_context["interactive"]`
and yields from `queue.get()` until a `task_completed` event arrives.

---

## 4. Phased Delivery Plan (REVISED 2026-05-08 to reflect v3 shipped work)

### ✅ Phase 0 — Spike (DONE by v3 plan)
- [x] OpenTeam tools have working CLI entry points (`python -m openteam.server.resources.tools.task --help` etc.).
- [x] `tool_cli.build_parser` proves `tool.json` is the single source of truth for parser surface.
- [x] Topologies promoted out of `test/` into production `task/topologies/`.
- [ ] **NEW pre-flight** (5 min): from inside the `OpenStartup` venv run
      `python -m openteam.server.resources.tools.task --help`.
      Expect a help message listing all `task` flags. If it fails with
      `ModuleNotFoundError: openteam`, install editable: `uv pip install -e .` first.

### Phase 0.5 — `tool_cli.run_cli` result-rendering bug fix *(20 min, MUST do before Phase 3)*

The current `tool_cli.py:121` uses `result.get("text", "")` which is a guaranteed
no-op because executors return `ToolExecutionResult` (Pydantic), not a dict.
Verified by reading `task/executor.py:533` (`return await _run_topology(...)`)
and dispatcher line 234 (`result.context_updates`, `result.result`).

- [ ] Patch `src/openteam/server/services/tool_cli.py:run_cli`:
      ```python
      # Replace the entire result-rendering block (current lines 119–127)
      from agent_foundation.resources.tools.models import ToolExecutionResult  # type: ignore
      result_text = ""
      ctx: dict = {}
      if isinstance(result, ToolExecutionResult):
          result_text = result.result or ""
          ctx = dict(result.context_updates or {})
      elif isinstance(result, dict):
          # legacy / future dict-shaped tools
          result_text = result.get("result") or result.get("text") or ""
          ctx = dict(result.get("context_updates") or {})
      else:
          result_text = str(result)
      print(result_text)
      # Surface artifact paths on stderr so subprocess wrappers can grep them
      for k in ("workspace_path", "plan_path", "impl_path",
                "role_document_path", "doc_path"):
          if ctx.get(k):
              print(f"[{k}] {ctx[k]}", file=sys.stderr)
      ```
- [ ] If the `agent_foundation` import is fragile in some venv, fall back to
      duck-typing: `if hasattr(result, "result") and hasattr(result, "context_updates")`.
- [ ] Add a unit test at `OpenStartup/test/openteam/server/services/test_tool_cli.py`:
      - Stubs an `execute_fn` that returns a `ToolExecutionResult(result="hi", context_updates={"workspace_path": "/tmp/x"})`.
      - Captures stdout/stderr.
      - Asserts stdout is `"hi\n"` and stderr contains `"[workspace_path] /tmp/x"`.
      - Repeat with a dict-returning stub to assert the legacy path.

### Phase 0.6 — `session_context` minimum viable construction *(15 min, MUST before Phase 3)*

Current code: `session_context: dict[str, Any] = {}`. Executors *do* tolerate
this (every read uses `.get(...)`), but `_resolve_workspace(session_context, task_id)`
falls through to its temp-dir branch when neither `working_dir` nor server-managed
state is present, losing artifact provenance. The dispatcher canonically constructs:

```python
{
  "server_dir": <project root>,
  "working_dir": <task-scoped subdir>,
  "interactive": <WebSocketInteractive>,   # we'll set None for CLI
  "task_id": <uuid>,
  # plus whatever the FastAPI lifespan injects
}
```

- [ ] Add a `--workspace-root <path>` flag to `tool_cli.build_parser` (or honor an
      `$OPENTEAM_WORKSPACE_ROOT` env var) and surface it as `session_context["working_dir"]`.
      Default: `Path.cwd() / ".openteam_runs" / <tool>_<timestamp>`.
- [ ] Generate a `task_id` (`uuid4().hex[:12]`) and inject it.
- [ ] Set `session_context["interactive"] = None` *explicitly* so any naive
      `if session_context["interactive"]:` checks short-circuit cleanly.
- [ ] Document this minimal contract in `tool_cli.py`'s module docstring.
- [ ] Add a regression test that asserts the standalone CLI can complete a
      `task --plan "say hi"` invocation and the workspace dir actually exists
      after the run (TIER-2 mocked test, not TIER-3).

### Phase 0.7 — Argument key-shape contract *(10 min, can ship later)*

`tool_cli.py:114-116` rewrites `_` → `-` in every key. Executors today
defensively read both shapes (`arguments.get("agent-config") or arguments.get("agent_config")`)
so this works *by accident*. To prevent silent breakage in future tools:

- [ ] Add a comment to `tool_cli.py` documenting the contract: "All keys
      passed to `execute()` use dash-separated form. Executors should read
      `arguments['my-key']` (not `arguments['my_key']`)."
- [ ] Add a preflight test under `test/openteam/server/services/` that walks
      every executor and asserts it doesn't read `arguments[<some_underscore_key>]`
      for any key declared in `tool.json`. (AST scan is fine; ~30 LOC.)
- [ ] Optional: if/when migrating executors, drop the OR-fallback to make
      the contract enforceable.

### Phase 1 — `openteam_bridge` package skeleton (½ day, **scope shrunk** — `tool_cli` already does the heavy lifting)
- [ ] Create `CoreProjects/OpenStartup/src/openteam_bridge/` with
      `__init__.py`, `tui_extension_subproc.py` (Variant D handler factory),
      basic `pyproject.toml`. **No `bridge.py` / `streaming.py` needed in the subprocess variant.**
- [ ] Variant C (in-process) `bridge.py` and `streaming.py` are now **optional Phase 6 work**, only if we want richer streaming widgets.
- [ ] Smoke-test: `python -c "from openteam_bridge.tui_extension_subproc import _make_handler; print(_make_handler('/task', 'openteam.server.resources.tools.task'))"` returns a callable.

### Phase 2 — Mechanism A (MCP server) (½–1 day)
- [ ] Implement `openteam_bridge.mcp_server` using `fastmcp` (already in
      acra-python's venv).
  - Discover tools by walking `openteam/server/resources/tools/*/tool.json` and
    filtering on `agent_enabled`.
  - For each tool, build the schema by re-running `build_parser(tool.json).format_help()`
    parsing — or, simpler, iterate `parameters[]` straight into a `mcp.tool` schema.
  - Implementation body of each `@mcp.tool` is just
    `await asyncio.create_subprocess_exec("python","-m", module_path, *argv)` and
    return captured stdout; no in-process import of OpenTeam needed.
- [ ] Add example `~/.rovodev/mcp.json` snippet to README.
- [ ] Manual test: launch RovoDev TUI, run `/mcp`, confirm `openteam` server
      shows up green with N tools, then ask the model "use openteam.task to
      compute 2+2".

### Phase 3 — Mechanism D (default — subprocess slash commands) (½ day)
- [ ] Implement `openteam_bridge.tui_extension_subproc.register_openteam_commands`
      (already drafted in §3.4 above; ~80 LOC including helpers).
- [ ] Add the 4-line opt-in block to acra-python `rovodev_tui/app.py`:
      ```python
      try:
          from openteam_bridge.tui_extension_subproc import register_openteam_commands
          register_openteam_commands(command_registry)
      except ImportError:
          pass
      ```
- [ ] Manual test:
  - `/task what is 2+2` → spinner, stdout streams into chat, exit 0.
  - `/create-role "Senior Backend Engineer focused on microservices"` → role
    markdown produced under `./roles/`, path printed to stderr → notify.
  - `/role-setup ./roles/foo.md` → `role_setup_report.md` produced.
- [ ] Cancellation test: Ctrl-C during a long task should `proc.terminate()`.

### Phase 4 — Mechanism C2 (upstream entry-point hook) (1–2 days)
- [ ] Open PR against `acra-python` adding the `entry_points("rovodev.slash_commands")`
      loop in `rovodev_tui/app.py`.
- [ ] PR includes: docs page in
      `packages/cli-rovodev/docs/rovodev-cli/content/platform/rovodev-cli/extensions.md`
      describing the contract `(registry: SlashCommandRegistry) -> None`.
- [ ] Update `openteam_bridge`'s `pyproject.toml` with the entry-point so the
      4-line patch in Phase 3 disappears.

### Phase 5 — Skill (`openteam-bridge` SKILL.md) (½ day)
- [ ] Create `~/.rovodev/skills/openteam-bridge/SKILL.md` describing when to
      reach for `/task`, `/create-role`, `/role-setup`, with usage examples
      verbatim from each `tool.json["examples"]`.
- [ ] Symlink it from the package so versioning lives next to the code.

### Phase 6 — Hardening (1–2 days)
- [ ] Optional Variant C (`bridge.py` + `streaming.py` + `InMemoryInteractive`)
      for in-process invocation when richer event streaming is desired.
- [ ] Schema-driven `--help` rendering inside RovoDev (call `build_parser(tool.json).format_help()` and surface in `CommandHelp` widget when user runs `/task help`).
- [ ] Auto-flip slash commands based on `slash_enabled`: drop the static
      `_tool_modules()` map and walk the registry instead. Requires §6
      "follow-on edits" first.
- [ ] Robust error surfacing (parse `ToolExecutionResult.result` for tracebacks
      and render with red `CommandHelp`).
- [ ] Cancellation: cooperate with `Worker.is_cancelled`; SIGTERM the subprocess.
- [ ] Integration test under `OpenStartup/test/openteam_bridge/`.

### Phase 7 — Optional Sidecar mode (deprioritized — Variant D already gives us isolation)
- The original Phase 7 (HTTP sidecar via `openteam.server.main`) is now mostly
  redundant with Variant D. Keep on the backlog for the case where a *long-lived*
  OpenTeam server is desirable (UI sharing, GPU warm-up, cached state). Skip
  unless that need materializes.

---

## 5. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| OpenTeam imports require FastAPI lifespan-only state | Medium | Phase 0 spike validates. Fallback: build a `MinimalAppState` shim or pivot to sidecar (Phase 7). |
| Dependency conflicts between acra-python venv and OpenTeam | Medium | Default in-process integration uses `uv pip install -e ./src/openteam`. If conflicts arise, run as MCP **subprocess** (mechanism A) — already isolated by stdio boundary. |
| `_dispatch_as_task` requires a real WebSocket | Low | We provide `InMemoryInteractive` that quacks like one (`send_task_status`, `_send`). The dispatcher only checks for `interactive` truthiness, not its type. |
| `SlashCommandRegistry` does not currently allow plugin loading | Confirmed | Phase 3 uses a 4-line local patch; Phase 4 upstreams the entry-point hook (~30 LOC PR). |
| User has neither `agent_foundation` nor `nemo` packages installed | Low | Both are in the acra-python venv already (visible under `.venv/lib/python3.13/site-packages/`); for OpenTeam users we add them to `openteam-bridge`'s `pyproject.toml` deps. |
| Slash command name collisions (e.g. `/task` may conflict with future built-in) | Low | Skip registration if `command in registry.commands`; surface a notice. |
| Threading: OpenTeam tools spawn their own asyncio tasks | Medium | Run handlers with `thread=True` so we get a fresh event loop per worker; bridge runs inside that loop. Validate with the long-running `task` tool. |
| Streaming UI back-pressure | Low | `asyncio.Queue` already provides natural back-pressure; widgets mounted via `app.call_from_thread`. |

---

## 6. Concrete File Touch List (REVISED — much smaller now)

### New files (in OpenStartup repo)

```
CoreProjects/OpenStartup/_dev/_plan/openteam-rovodev-integration-plan.md   ← this file
CoreProjects/OpenStartup/src/openteam_bridge/__init__.py
CoreProjects/OpenStartup/src/openteam_bridge/tui_extension_subproc.py      ← Phase 3 (Variant D, ~80 LOC)
CoreProjects/OpenStartup/src/openteam_bridge/mcp_server.py                 ← Phase 2
CoreProjects/OpenStartup/src/openteam_bridge/skill/SKILL.md                ← Phase 5
CoreProjects/OpenStartup/src/openteam_bridge/pyproject.toml
CoreProjects/OpenStartup/test/openteam_bridge/test_handlers.py             ← Phase 6
CoreProjects/OpenStartup/test/openteam/server/services/test_tool_cli.py    ← Phase 0.5 bug fix
```

**Optional (Phase 6, in-process Variant C only):**

```
CoreProjects/OpenStartup/src/openteam_bridge/bridge.py
CoreProjects/OpenStartup/src/openteam_bridge/streaming.py
CoreProjects/OpenStartup/src/openteam_bridge/tui_extension_inproc.py
```

### Modified files (in OpenStartup repo)

```
src/openteam/server/services/tool_cli.py                    # Phase 0.5: result-rendering fix (~10 LOC)
src/openteam/server/resources/tools/create_role/tool.json   # Phase 6: add "slash_enabled": true (optional)
src/openteam/server/resources/tools/role_setup/tool.json    # Phase 6: add "slash_enabled": true (optional)
```

### Modified files (in acra-python repo)

```
packages/cli-rovodev-tui/src/rovodev_tui/app.py             # Phase 3: 4-line opt-in import block
                                                            # OR Phase 4: ~30-line entry-point loop
packages/cli-rovodev/docs/rovodev-cli/content/platform/rovodev-cli/extensions.md   # Phase 4: new doc
```

### User-side config

```
~/.rovodev/mcp.json                  # Phase 2: register openteam MCP server
~/.rovodev/skills/openteam-bridge/   # Phase 5: symlink to the SKILL.md
```

### Files we no longer need to write (thanks to v3 plan shipping)

- ~~`openteam_bridge/argparse_from_tooljson.py`~~ — done by `tool_cli.build_parser`
- ~~`openteam_bridge/runners/task_runner.py`~~ — done by `task/cli.py:main`
- ~~`openteam_bridge/runners/role_setup_runner.py`~~ — done by `role_setup/cli.py:main`
- ~~`openteam_bridge/runners/create_role_runner.py`~~ — done by `create_role/cli.py:main`

---

## 7. Validation Checklist

Run end-to-end after Phase 3 to answer the user's literal question
("can we type /task, /create-role, /role-setup in Rovo Dev and have OpenTeam run them?"):

- [ ] `/task what is 2+2` → spinner → result widget with stdout from PTI topology.
- [ ] `/task --agent-config bta --model sonnet "list 3 ways to learn python"` → flags parsed correctly.
- [ ] `/create-role "Senior Backend Engineer focused on microservices"` → role markdown written under `./roles/`, path surfaced as artifact link in chat.
- [ ] `/role-setup ./roles/senior_backend_engineer.md` → `role_setup_report.md` produced; chat shows progress for inner subtasks.
- [ ] `/help` lists all three commands with descriptions taken from `tool.json["description"]`.
- [ ] `/help /task` shows full parameter list.
- [ ] Cancelling with Ctrl-C terminates the in-flight OpenTeam task within 2s.
- [ ] `/mcp` shows `openteam` server (Phase 2 path) with all `agent_enabled` tools.
- [ ] Model can autonomously call `openteam.task` from agentic loop and see results.

---

## 8. Open Questions for User

1. **Install location for `openteam-bridge`** — package it inside
   `CoreProjects/OpenStartup/src/openteam_bridge/` (sibling to `openteam`)
   or as a separate top-level repo? (Plan assumes the former.)
2. **Default integration mode** — in-process (faster, shared venv) or sidecar
   (process isolation, slightly slower)? Plan defaults to in-process with
   `OPENTEAM_BRIDGE_MODE=sidecar` escape hatch.
3. **Upstream PR appetite** — are we comfortable submitting the
   `entry_points("rovodev.slash_commands")` hook to acra-python? If not, we
   stick with the 4-line opt-in patch indefinitely.
4. **Slash command naming** — `/task` collides with potential future RovoDev
   built-ins. Should we namespace as `/openteam:task`, `/ot task`, etc.?
   (Plan currently uses bare names; trivially renameable in `_make_handler`.)
5. **Which OpenTeam tools should be slash-exposed besides task/create_role/
   role_setup?** Slack tools? TWG tools? `project_onboarding`? — easy to flip
   `slash_enabled: true` per tool.

---

## 9. Answer to the User's Headline Question (REVISED — even more "yes")

> *"Is this possible? both rovodev and openteam are python based right? let's
> first achieve in rovo dev we can use backslash command like /task,
> /create-role, /role-setup, etc. to invoke those tools on the openteam
> framework, let's check if this possible."*

**Yes — and now substantially easier than originally estimated**, because the
v3 CLI-unification plan has already done ~⅓ of the integration work for us:

1. ✅ Both projects are Python.
2. ✅ OpenTeam now has **standalone CLI binaries** (`python -m openteam.server.resources.tools.{task,role_setup,create_role}`) with a `tool.json`-driven argparse parser (`tool_cli.build_parser`). This means we can drive them from any subprocess without importing OpenTeam at all.
3. ✅ Every flag a slash command ever needs is already in `tool.json` (single source of truth) — flag drift is impossible by construction.
4. ✅ RovoDev's `SlashCommandRegistry.register(...)` API is public, stable, and accepts arbitrary async handlers — exactly what we need.
5. ✅ For zero-fork adoption today, register an MCP server (Mechanism A) in `~/.rovodev/mcp.json`; tools become agentic immediately.
6. ✅ For the requested *slash-command* UX, the **simplest viable path** is now Variant **D** (subprocess shell-out): a 4-line opt-in patch in `app.py` plus an ~80-LOC `openteam_bridge/tui_extension_subproc.py` file. **No `openteam` import needed in the RovoDev venv at all** — total dependency isolation.

The revised estimate is **2.5–3 days of focused work** (was 3–4 days; the
audit-driven phases 0.5/0.6/0.7 add ~½ day back):

| Day | Phase | Deliverable |
|---|---|---|
| ¼ | 0.5 | `tool_cli.run_cli` `ToolExecutionResult` rendering fix + test. |
| ¼ | 0.6 | `tool_cli.run_cli` minimum-viable `session_context` (working_dir, task_id, interactive=None) + test. |
| ¼ | 0.7 | Argument key-shape contract docs + AST preflight (can defer). |
| ½ | 1 | `openteam_bridge` package skeleton + Variant D handlers. |
| 1 | 2 | FastMCP server + `mcp.json` snippet (Mechanism A). |
| ½ | 3 | 4-line acra-python opt-in patch + manual end-to-end smoke test of `/task`, `/create-role`, `/role-setup`. |
| ½ | 5 | `SKILL.md` for the agent to know when to use the new commands. |

**Critical sequencing:** Phase 3 must NOT ship before Phases 0.5 and 0.6 are
merged. Otherwise the slash UX will appear to work (spinner + exit code 0)
while silently dropping all real output and leaking artifacts to a temp dir.

After Phase 3 the user's exact requested workflow works end-to-end:

```
> /task what is 2+2
> /create-role "Senior Backend Engineer focused on microservices"
> /role-setup ./roles/senior_backend_engineer.md
```

Phase 4 (entry-point hook upstream PR) and Phase 6 (Variant C in-process
streaming + `slash_enabled` auto-discovery) are nice-to-haves to schedule
later, not blockers.
