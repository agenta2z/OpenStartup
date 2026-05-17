# OpenTeam ↔ RovoDev Integration — Integrated Plan v3 (FINAL)

**Date:** 2026-05-08 06:06
**Author:** Rovo Dev (third-pass synthesis)
**Inputs:**
- `openteam-rovodev-integration-INTEGRATED-v2.md` (mine — MCP-only via PromptSubmitted, **architecturally wrong**)
- `take-a-careful-look-memoized-walrus.md` (Walrus — subprocess slash + in-process MCP, **architecturally correct**)
**Supersedes:** Both prior plans for the OpenTeam↔RovoDev question.

> **Pick-one answer (eager headline):** **Pick Walrus** (`take-a-careful-look-memoized-walrus.md`). It is right about the architecture; v2 was wrong. This v3 keeps Walrus's architecture and adds a few rigour items v2 had right.

---

## 0. Decisive ground-truth findings (verified 2026-05-08 06:06)

These three checks settled the disagreement between v2 and Walrus:

| Question | Verified answer | Implication |
|---|---|---|
| Does RovoDev rewrite `Invoking 'X':` prefixes generically? | **No.** `prompts.py:292-300` hardcodes only `full-context` and `research`. Anything else is sent to the LLM as literal text. | v2's plan to mirror `/research` for `/task` would *probably* work but is **fragile and undocumented** — the LLM has to *guess* it should call the MCP tool. **Walrus is right: don't go through the LLM for deterministic work.** |
| Default MCP client timeout? | **295 s** (`mcp_toolset.py:138`). | Most `task` runs are 5–30 minutes. **MCP path will time out for the typical case.** Subprocess path doesn't have this issue. |
| Is `fastmcp` already in OpenStartup? | **No.** No root `pyproject.toml`/`setup.py`; no `fastmcp` anywhere. (`fastmcp==3.2.4` is in acra-python's `code-nemo` and `code-nautilus`.) | Need an install step + version pin. v2 underspecified this. |
| Does OpenStartup have packaging metadata? | **No** root `pyproject.toml`. | Phase 8 of v2 (entry-point scripts) requires this groundwork first. |

These findings reframe the problem: the slash UX must be **subprocess-first**, with MCP as the *secondary* programmatic path (not the primary slash backend).

---

## 1. Architecture (final)

```
┌─────────────────────────── RovoDev TUI ───────────────────────────┐
│                                                                   │
│  /task <args>          ──→  subprocess: python -m openteam.       │
│  /create-role <args>            server.resources.tools.<tool>     │
│  /role-setup <args>             ───→  streaming stdout/stderr     │
│  /project-onboarding <args>     ───→  ShellOutput-style widget    │
│                                                                   │
│         (deterministic, no LLM round-trip, no 295s timeout)       │
│                                                                   │
│  LLM agent              ──→  MCP call: mcp__openteam__<tool>      │
│      (programmatic            ───→  in-process executor.execute() │
│       agentic use)            ───→  subject to 295s timeout       │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
            ~/.rovodev/mcp.json registers ↓
                              │
                              ▼
         python -m openteam.mcp_server.main run     (stdio)
                              │
                              ▼
        ┌─────────────── openteam/mcp_server/ ──────────────┐
        │  server.py   create_openteam_server()             │
        │              FastMCP("openteam") + add_tool×N     │
        │  context.py  build_session_context()              │
        │  main.py     Typer entry → run_stdio_async()      │
        └───────────────────────────────────────────────────┘
                              │
                              ▼
        in-process call → openteam.server.resources.tools
                            .<tool>.executor:execute(args, ctx)
                              │
                              ▼
                       ToolExecutionResult
```

**Key invariants:**
- **Slash commands are deterministic subprocess shell-outs** — no LLM, no MCP, no timeout cliff. Streaming via PIPE.
- **MCP tools are in-process within the MCP server subprocess** — *not* subprocess-within-subprocess. Cleanly avoids the "two boundaries" anti-pattern.
- **`tool_cli.py` is the single source of truth** for `tool.json` → CLI parser. Slash commands use it (via `python -m`); MCP wrappers re-use the same `tool.json` schema for typed signatures.
- **MCP path has known 295s timeout** — documented for users; not a slash-path concern.

---

## 2. Plan synthesis — what comes from where

| Element | Source | Why |
|---|---|---|
| Subprocess slash commands (deterministic, no LLM) | **Walrus** | Empirically validated: `format_input_prompt` only handles 2 hardcoded skills; deterministic pipelines should not go through LLM |
| In-process executor calls inside MCP server | **Walrus** | Avoids subprocess-within-subprocess; MCP server is itself the subprocess boundary |
| Package layout `openteam/mcp_server/` (no `openteam_bridge`) | **Walrus** | One layer of indirection; matches how OpenStartup's other packages are organized |
| FastMCP + Typer pattern from `mcp-atlassian-exp` | Both | Proven precedent in acra-python |
| `_render_result` duck-typed against `ToolExecutionResult` | Both | Avoids fragile cross-package import |
| Phase 0 `tool_cli.py` rendering fix as **prerequisite** | **Walrus** | Walrus correctly elevates this from "cleanup ticket" to "blocking" because subprocess slash *depends* on it |
| Drop Phase 0.6 (`session_context` construction) | **Walrus** | Verified safe: `_resolve_workspace` handles `{}` |
| TIER-1/2/3 test tagging | **v2** | Walrus is silent on this; we keep it |
| CI preflight: wrapper signatures vs `tool.json` | **v2** | Walrus doesn't address drift risk; we keep it |
| Self-audit section | **v2** | Walrus has a critique table, but no self-audit; we keep both |
| Long-running tool handling (Phase 7A/B) | **v2** | Walrus mentions risk but doesn't structure remediation |
| `slash_enabled: true` flag flip in 3 `tool.json`s | **Walrus** | v2 mentioned but didn't include in Phase plan |
| Skill (`SKILL.md`) for agent guidance | Both | Same |
| **NEW:** OpenStartup root `pyproject.toml` | This v3 | Pre-condition for `fastmcp` install + future packaging; both prior plans missed it |
| **NEW:** Replace per-line `notify_and_log` with proper streaming widget | This v3 | Walrus's draft floods the UI with toasts; we use a `ShellOutput`-style mounted widget |
| **NEW:** Argument forwarding via `extra_prompt` parsed with `shlex` (not free text) | Both implicitly; we make explicit | Honest contract: `/task --foo bar baz` ≡ `python -m … --foo bar baz` |

---

## 3. Detailed Design

### 3.1 Files

#### OpenStartup repo — new

```
pyproject.toml                                              # NEW (root) — see §3.7
src/openteam/mcp_server/__init__.py
src/openteam/mcp_server/server.py
src/openteam/mcp_server/context.py
src/openteam/mcp_server/main.py
test/openteam/mcp_server/__init__.py
test/openteam/mcp_server/test_server_factory.py
test/openteam/mcp_server/test_context.py
test/openteam/mcp_server/test_wrappers_smoke.py
test/openteam/mcp_server/test_wrapper_signature_alignment.py
test/openteam/server/services/test_tool_cli_rendering.py    # Phase 0
docs/MCP_INTEGRATION.md
docs/MCP_SMOKE.md
```

#### OpenStartup repo — modified

```
src/openteam/server/services/tool_cli.py                   # Phase 0 rendering fix
src/openteam/server/resources/tools/create_role/tool.json   # add slash_enabled: true
src/openteam/server/resources/tools/role_setup/tool.json    # add slash_enabled: true
src/openteam/server/resources/tools/project_onboarding/tool.json   # add slash_enabled: true
```

#### acra-python repo — new

```
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py
```

#### acra-python repo — modified

```
packages/cli-rovodev-tui/src/rovodev_tui/app.py            # 4-line opt-in import + 4 register() calls
```

#### User-side config

```
~/.rovodev/mcp.json                                         # Phase 2A
~/.rovodev/skills/openteam/SKILL.md                         # Phase 4
```

### 3.2 Phase 0 — `tool_cli.py` result rendering fix (BLOCKING, ~20 min)

**Bug** (`tool_cli.py:121-127`): `result.get("text", "")` is always wrong because executors return `ToolExecutionResult` (dataclass), not dict. The `isinstance(result, dict)` branch is dead code.

**Patch** — replace lines 121-127:

```python
# Render result — handle ToolExecutionResult (dataclass) and legacy dict
if hasattr(result, "result") and hasattr(result, "context_updates"):
    print(result.result or "")
    ctx = result.context_updates or {}
elif isinstance(result, dict):
    print(result.get("result") or result.get("text") or "")
    ctx = result.get("context_updates") or {}
else:
    print(str(result))
    ctx = {}

# Surface artifact paths on stderr so subprocess wrappers can capture them
for key in ("workspace_path", "plan_path", "impl_path",
            "role_document_path", "doc_path", "report_path"):
    if ctx.get(key):
        print(f"[{key}] {ctx[key]}", file=sys.stderr)
```

Use **`hasattr` duck-typing** instead of `from agent_foundation... import ToolExecutionResult` to avoid fragile cross-package import.

**Test** — `test/openteam/server/services/test_tool_cli_rendering.py`:
- `test_renders_tool_execution_result()`: stub `execute_fn` returns a Mock with `.result="hi"` and `.context_updates={"workspace_path":"/tmp/x"}`; assert stdout=="hi\n" and stderr contains "[workspace_path] /tmp/x".
- `test_renders_dict_result()`: stub returns `{"result": "yo"}`; assert stdout=="yo\n".
- `test_renders_str_result()`: stub returns "raw"; assert stdout=="raw\n".
- `test_falsy_result_is_empty_line()`: stub returns `ToolExecutionResult` with `.result=""`; assert stdout=="\n" (no traceback).

### 3.3 `mcp_server/server.py` — design

**Pattern** (verified against `acra-python/packages/mcp-atlassian-exp/src/atlassian_exp/main.py:95-117`):

```python
"""FastMCP server exposing OpenTeam tools as in-process executor calls."""
from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from openteam.mcp_server.context import build_session_context

# Hard-mapped: explicit tool surface, no silent expansion.
# Each entry is (mcp_tool_name, dotted_executor_path).
_TOOL_SPECS: list[tuple[str, str]] = [
    ("openteam_task",
     "openteam.server.resources.tools.task.executor:execute"),
    ("openteam_create_role",
     "openteam.server.resources.tools.create_role.executor:execute"),
    ("openteam_role_setup",
     "openteam.server.resources.tools.role_setup.executor:execute"),
    ("openteam_project_onboarding",
     "openteam.server.resources.tools.project_onboarding.executor:execute"),
]


def create_openteam_server(
    tool_names: list[str] | None = None,
    *,
    session_context_factory=build_session_context,
) -> FastMCP:
    """Create a FastMCP server. tool_names=None → expose all 4 tools."""
    mcp = FastMCP("openteam")
    enabled = set(tool_names) if tool_names else None
    for name, executor_path in _TOOL_SPECS:
        if enabled and name not in enabled:
            continue
        wrapper = _build_wrapper(name, executor_path, session_context_factory)
        mcp.add_tool(FunctionTool.from_function(wrapper))
    return mcp


def _to_dash_form(d: dict) -> dict:
    """Match tool_cli.py:111 — executors read dash-form keys."""
    return {k.replace("_", "-"): v for k, v in d.items()}


def _strip_unset(d: dict) -> dict:
    """Drop None / False / "" / [] (match argparse 'flag not provided').
    Preserves 0 and other meaningful zero-values."""
    return {k: v for k, v in d.items()
            if v is not None and v is not False and v != "" and v != []}


def _render_result(result: Any) -> str:
    """Duck-typed against ToolExecutionResult; safe for dict / str fallbacks."""
    if hasattr(result, "result") and hasattr(result, "context_updates"):
        text = result.result or ""
        ctx = dict(result.context_updates or {})
    elif isinstance(result, dict):
        text = result.get("result") or result.get("text") or ""
        ctx = dict(result.get("context_updates") or {})
    else:
        return str(result)
    artifacts = [f"  {k}: {ctx[k]}"
                 for k in ("workspace_path", "plan_path", "impl_path",
                           "role_document_path", "doc_path", "report_path")
                 if ctx.get(k)]
    if artifacts:
        text += "\n\nArtifacts:\n" + "\n".join(artifacts)
    return text
```

**Wrapper template** (one per tool, hand-written for type-checked signatures):

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
    """Run an agent topology on a request. Default: PlanThenImplement breakdown-multiflow.

    Long-running (typically 5–30 min). Returns final result text + artifact paths.
    NOTE: subject to MCP client timeout (default 295s). For long jobs, prefer the
    /task slash command which uses subprocess streaming.
    """
    from openteam.server.resources.tools.task.executor import execute as _execute
    args = _strip_unset(_to_dash_form({
        "request": request, "agent-config": agent_config,
        "plan": plan, "execute": execute, "full": full, "confirm": confirm,
        "model": model, "override": override, "no-dual": no_dual,
        "analysis": analysis, "multi-iter": multi_iter,
        "max-iterations": max_iterations, "resume": resume,
        "initial-plan": initial_plan,
    }))
    return _render_result(await _execute(args, build_session_context()))
```

**3 more wrappers** (`openteam_create_role`, `openteam_role_setup`, `openteam_project_onboarding`) follow the same pattern, with signatures derived from each `tool.json`.

### 3.4 `mcp_server/context.py`

```python
"""Build session_context for in-process executor calls.

Empty `{}` would also be safe (executor's _resolve_workspace allocates a
fresh workspace under server/_runtime/tasks/), but we surface env-driven
hints so a long-lived OpenStartup checkout can pin its workspace root,
cloud_id, and credentials without modifying RovoDev.
"""
from __future__ import annotations
import os
import uuid
from typing import Any

# Whitelist: env var → session_context key
_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}


def build_session_context() -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "task_id": f"mcp-{uuid.uuid4().hex[:8]}",
        "interactive": None,  # explicit; executors guard with `if interactive is not None`
    }
    for env_key, ctx_key in _ENV_MAP.items():
        v = os.environ.get(env_key)
        if v:
            ctx[ctx_key] = v
    return ctx
```

### 3.5 `mcp_server/main.py`

```python
"""Typer entry: `python -m openteam.mcp_server.main run`."""
from __future__ import annotations
import asyncio
import logging
import typer

from openteam.mcp_server.server import create_openteam_server

app = typer.Typer()


@app.command("run")
def run(
    tools: str = typer.Option("", help="CSV of tool names to expose. Empty = all."),
    log_level: str = typer.Option("WARNING"),
) -> None:
    asyncio.run(_main_async(tools, log_level))


async def _main_async(tools_csv: str, log_level: str) -> None:
    logging.basicConfig(level=log_level)
    tool_names = [t.strip() for t in tools_csv.split(",") if t.strip()] or None
    mcp = create_openteam_server(tool_names)
    await mcp.run_stdio_async(show_banner=False, log_level=log_level)


if __name__ == "__main__":
    app()
```

### 3.6 RovoDev slash commands (`slash_commands/openteam.py`)

**Design choices that improve on Walrus's draft:**

1. **Mount a single `ShellOutput`-style widget** for the run, then `.append(text)` for each line. **Do NOT** call `notify_and_log` on every line — that turns each line into a toast (UX disaster).
2. **Use `app.call_from_thread()`** for all UI mutations (handler runs in worker thread).
3. **Cancellation:** track the proc handle and `proc.terminate()` on Ctrl-C.
4. **Help passthrough:** `/task --help` shells out to the real CLI and returns the parser's help text — single source of truth, zero drift.

```python
"""Subprocess slash commands for OpenTeam tools.

Each handler shells out to `python -m openteam.server.resources.tools.<tool>`
and streams the subprocess's stdout into the chat as a single mounted widget.
Stderr (artifact paths) is appended at the end.

Why subprocess (not PromptSubmitted): /task etc. are deterministic pipelines.
RovoDev's format_input_prompt() only rewrites two hardcoded prefixes
(full-context, research) — anything else goes to the LLM as raw text, which is
unreliable. Subprocess gives deterministic execution, real-time streaming,
proper exit codes, and SIGTERM cancellation.
"""
from __future__ import annotations
import asyncio
import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rovodev_tui.app import RovoDevApp
    from rovodev_tui.slash_commands.registry import SlashCommandRegistry


_OPENTEAM_HOME = Path(os.environ.get(
    "OPENTEAM_HOME",
    str(Path.home() / "MyProjects" / "CoreProjects" / "OpenStartup"),
))
_PYTHONPATH_DIRS = [
    _OPENTEAM_HOME / "src",
    _OPENTEAM_HOME.parent / "AgentFoundation" / "src",
    _OPENTEAM_HOME.parent / "RichPythonUtils" / "src",
]
_TOOL_MODULES = {
    "/task":               "openteam.server.resources.tools.task",
    "/create-role":        "openteam.server.resources.tools.create_role",
    "/role-setup":         "openteam.server.resources.tools.role_setup",
    "/project-onboarding": "openteam.server.resources.tools.project_onboarding",
}


def _make_handler(slash: str, module: str):
    async def handler(app: "RovoDevApp", extra_prompt: str) -> None:
        if not extra_prompt.strip():
            app.notify_and_log(
                f"Usage: {slash} <args>. Try `{slash} --help`.",
                severity="error", timeout=5,
            )
            return

        # Lazy import to avoid hard dep at module load
        from rovodev_tui.widgets import ShellOutput, ThinkingSpinner

        argv = shlex.split(extra_prompt)
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(str(p) for p in _PYTHONPATH_DIRS
                                           if p.is_dir()),
        }

        out = ShellOutput()
        spinner = ThinkingSpinner(f"Running {slash}…")
        app.call_from_thread(app.chat_container.mount, out)
        app.call_from_thread(app.chat_container.mount, spinner)

        proc = await asyncio.create_subprocess_exec(
            os.environ.get("OPENTEAM_PYTHON", "python"), "-m", module, *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env, cwd=str(_OPENTEAM_HOME),
        )
        try:
            assert proc.stdout
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                app.call_from_thread(out.append,
                                     line.decode("utf-8", "replace"))
            stderr_data = await proc.stderr.read() if proc.stderr else b""
            await proc.wait()
            if stderr_data:
                app.call_from_thread(
                    out.append,
                    "\n--- artifacts (stderr) ---\n"
                    + stderr_data.decode("utf-8", "replace")
                )
        finally:
            app.call_from_thread(spinner.remove)
            if proc.returncode and proc.returncode != 0:
                app.call_from_thread(
                    app.notify_and_log,
                    f"{slash} exited with code {proc.returncode}",
                    severity="error", timeout=8,
                )

    handler.__doc__ = (
        f"Run OpenTeam's {slash[1:]} via subprocess. "
        f"Args after {slash} are forwarded to the tool's CLI. "
        f"Run `{slash} --help` for options."
    )
    handler.__name__ = f"handle_{slash[1:].replace('-', '_')}_command"
    return handler


def register_openteam_commands(registry: "SlashCommandRegistry") -> None:
    """Idempotent: skips slash names already registered."""
    for slash, module in _TOOL_MODULES.items():
        if slash in registry.commands:
            continue
        registry.register(
            _make_handler(slash, module),
            slash,
            extra_prompt="required",
            thread=True,  # subprocess I/O → worker thread
        )
```

**`app.py` patch** (after the existing `command_registry.register(...)` block, ~line 604):

```python
# OpenTeam commands — opt-in; silently no-op if module not installed
try:
    from rovodev_tui.slash_commands.openteam import register_openteam_commands
    register_openteam_commands(command_registry)
except ImportError:
    pass
```

### 3.7 OpenStartup `pyproject.toml` (NEW root file)

OpenStartup currently has **no root packaging**. Add a minimal `pyproject.toml`
so `fastmcp` and friends install cleanly, and the repo is `pip install -e`-able:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openteam"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp==3.2.4",   # pinned to match acra-python's mcp-atlassian-exp
    "typer>=0.12",
    "pyyaml>=6",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23"]

[project.scripts]
openteam-mcp = "openteam.mcp_server.main:app"

[tool.setuptools.packages.find]
where = ["src"]
include = ["openteam*"]
```

This unlocks:
- `pip install -e .` from the repo root.
- A clean `openteam-mcp run` console script (Phase 8 dependency).
- A pinned `fastmcp` version that matches what acra-python uses.

### 3.8 `~/.rovodev/mcp.json`

```json
{
  "mcpServers": {
    "openteam": {
      "command": "python",
      "args": ["-m", "openteam.mcp_server.main", "run"],
      "env": {
        "PYTHONPATH": "/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src:/Users/tchen7/MyProjects/CoreProjects/AgentFoundation/src:/Users/tchen7/MyProjects/CoreProjects/RichPythonUtils/src",
        "OPENTEAM_WORKING_DIR": ".",
        "OPENTEAM_MCP_TIMEOUT": "1800"
      }
    }
  }
}
```

(The `OPENTEAM_MCP_TIMEOUT` env is informational today; once acra-python honors per-server timeouts via env, it becomes load-bearing — see Phase 7.)

### 3.9 Skill (`~/.rovodev/skills/openteam/SKILL.md`)

```markdown
---
name: openteam
description: OpenTeam multi-agent workflow tools (task pipeline, role lifecycle, project onboarding)
allowed-tools:
  - mcp__openteam__openteam_task
  - mcp__openteam__openteam_create_role
  - mcp__openteam__openteam_role_setup
  - mcp__openteam__openteam_project_onboarding
---
# OpenTeam Tools

Two ways to use these:

1. **Slash commands** (deterministic, recommended for users):
   - `/task <request>` — run an agent topology
   - `/create-role <description>` — synthesize a role document
   - `/role-setup <role.md>` — decompose a role into skills/tools and create missing capabilities
   - `/project-onboarding <project.md>` — onboard an AI employee to a project

2. **MCP tools** (programmatic; for agent self-orchestration):
   - `mcp__openteam__openteam_task(request=…, agent_config=…, …)`
   - `mcp__openteam__openteam_create_role(role_name=…, description=…, …)`
   - …

⚠️ MCP tools are subject to a **295 s default timeout**. For long runs (>5 min),
prefer the slash command (subprocess; no timeout).
```

---

## 4. Phased Delivery

| Phase | Scope | LOC | Time | Blocking? |
|---|---|---|---|---|
| **0** | `tool_cli.py` rendering fix + test | ~30 | 20 min | ✅ blocks Phase 2 (slash) |
| **1** | `openteam/mcp_server/` package + 4 wrappers + tests + root `pyproject.toml` | ~250 | ½ day | blocks Phase 2A |
| **2A** | Register MCP server in `~/.rovodev/mcp.json`; manual smoke | — | 15 min | parallel with 2B |
| **2B** | `slash_commands/openteam.py` + 4-line `app.py` opt-in + flip 3 `tool.json` flags | ~120 | ½ day | parallel with 2A |
| **3** | TIER-1/2 tests + CI preflight (signature alignment) | ~100 | ½ day | nice-to-have for v1 |
| **4** | Skill + docs (`MCP_INTEGRATION.md`, `MCP_SMOKE.md`) | — | ½ day | nice-to-have for v1 |
| **7A** | Document `OPENTEAM_MCP_TIMEOUT`; add per-server timeout override (acra-python PR) | small | 1 day | ship after Phase 2 |
| **7B** | (Optional) In-memory `FastMCPTransport` for higher timeout — gated; only if acra-python is willing to import OpenTeam in-process | medium | 1 day | future |
| **8** | (Optional) Publish `openteam` to internal pip; switch `mcp.json` to bare `openteam-mcp run` | small | future | future |

**Critical sequencing:** Phase 0 → Phase 1 → Phases 2A & 2B (parallel) → Phases 3, 4 (parallel). Phases 7/8 are post-ship.

**Total time to working `/task <prompt>`:** **~1–1.5 days.**

---

## 5. Test plan (TIER-tagged)

| Test | TIER | Scope |
|---|---|---|
| `test_tool_cli_rendering.py` | 1 | Phase 0 fix; stub `execute_fn`, capture stdout/stderr |
| `test_context.py` | 1 | `build_session_context` env-var pickup, task_id uniqueness |
| `test_server_factory.py` | 1 | `create_openteam_server(tool_names=[…])` filtering |
| `test_wrappers_smoke.py` | 2 | each wrapper: stub executor, assert dash-form keys + `_render_result` |
| `test_wrapper_signature_alignment.py` | 1 | walk `_TOOL_SPECS` and each wrapper signature; assert no drift vs `tool.json` |
| Manual MCP smoke | 3 | `python -m openteam.mcp_server.main run` then call `openteam_task` via `fastmcp dev` |
| Manual `/task` E2E | 3 | `/task what is 2+2` → streamed output → exit 0 |
| Manual `/task --help` | 3 | parser help printed; exit 0 |
| Manual cancellation | 3 | Ctrl-C during long `/task`; subprocess SIGTERM in <5 s |
| `/mcp` listing | 3 | `openteam` server green; 4 tools listed |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| MCP 295 s timeout for long agentic invocation | High | Documented; slash UX is primary; Phase 7A adds env override |
| `fastmcp` not in OpenStartup venv | High | Phase 1 includes root `pyproject.toml` with pinned `fastmcp==3.2.4` |
| `PYTHONPATH` brittle across users | Medium | `OPENTEAM_HOME` env override; Phase 8 console_scripts removes need entirely |
| Wrapper signatures drift from `tool.json` | Medium | Phase 3 CI preflight (`test_wrapper_signature_alignment.py`) |
| `notify_and_log` per line floods UI (Walrus's draft bug) | Mitigated here | We mount one `ShellOutput` widget and `.append()` per line |
| `format_input_prompt` rewrites collide with `/task` text | Low | We don't use `Invoking '…':` prefix at all in the slash path |
| Subprocess on Windows | Low | We invoke `python -m`, not shell; documented as "Linux/macOS tested" |
| Cross-user `OPENTEAM_HOME` defaulting to my path | Medium | Default is `~/MyProjects/CoreProjects/OpenStartup`; ship docs to `direnv`/`.envrc` for per-machine override |

---

## 7. Self-Audit (stress-tested for hacks)

| Question I asked myself | Answer |
|---|---|
| Is the dual path (slash subprocess + MCP) actually two implementations? | **No.** Both end up in `executor.execute()`. The slash path goes through `tool_cli.run_cli` (file → CLI → executor). The MCP path goes directly executor. Same business logic. |
| Does `_render_result` duplicate `tool_cli.py`'s rendering? | Yes — *intentionally*. The MCP path doesn't import `tool_cli` because we don't want to depend on its CLI-shaped output. Phase 8-ish refactor: lift `_render_result` into a shared helper module if both paths drift. |
| Does `_strip_unset` accidentally drop `0`? | No. `0 is not None` and `0 is not False` are both True (verified by Python semantics; `bool` is a subclass of `int` but `0 is False` is False — they're different objects). |
| Is `OPENTEAM_HOME` defaulting to `tchen7`'s path acceptable for upstream? | Documented as a personal default; can be hoisted into a `.env.example` template. Honest contract: each user must set it. |
| What if a user installs both stdio MCP AND uses slash? | Both work side-by-side. No shared state; no conflict. |
| What happens if `python` on PATH is the wrong interpreter? | `OPENTEAM_PYTHON` env override; otherwise `python -m openteam.mcp_server.main` will `ModuleNotFoundError` cleanly. |
| Is the 295s MCP timeout actually a "won't fix" for now? | Mostly yes for v1. Phase 7A adds documented override. Phase 7B (in-memory transport) is a future, gated optimization. The slash UX **doesn't have this problem** — that's the point. |
| Could the Phase 0 fix break some existing caller? | `tool_cli.run_cli` is currently silent on real runs (the `print(result.get("text",""))` always prints `""`). Anyone relying on that emptiness was *already* broken; the fix is unambiguously an improvement. |

---

## 8. Comparison: v2 vs Walrus vs **v3**

| Concern | v2 (mine) | Walrus | **v3 (this)** |
|---|---|---|---|
| Slash architecture | PromptSubmitted (LLM) ❌ | Subprocess ✅ | **Subprocess** ✅ |
| MCP architecture | In-process ✅ | In-process ✅ | **In-process** ✅ |
| `format_input_prompt` analyzed? | No (assumed it would work) | Yes (correctly identified the only-2-hardcoded-prefixes problem) | **Yes — verified line-by-line** |
| MCP timeout addressed? | No | Yes (correctly identified 295 s) | **Yes — documented + Phase 7A** |
| `fastmcp` install path | Hand-waved with `PYTHONPATH` | Mentioned `pip install fastmcp` | **Phase 1 root `pyproject.toml`** ✅ |
| OpenStartup root packaging | Not addressed | Not addressed | **Added (3.7)** ✅ |
| TIER-tagged tests | Yes ✅ | No | **Yes** ✅ |
| Wrapper-signature drift CI | Yes ✅ | No | **Yes (3.3 + Phase 3)** ✅ |
| Self-audit section | Yes ✅ | No | **Yes (§7)** ✅ |
| Streaming UX (no toast flood) | N/A | Per-line `notify_and_log` ❌ | **Single `ShellOutput` widget** ✅ |
| Cancellation (SIGTERM) | N/A | Mentioned | **Implemented in §3.6** ✅ |
| Long-running tool plan | Phase 7A/B ✅ | Mentioned in Risks | **Phase 7A explicit** ✅ |
| Total LOC | ~330 | ~280 | **~400** (more rigour) |
| Days to ship | 2–3 | "small" | **1–1.5 to first slash; +1 to full polish** |

---

## 9. The pick-one answer

> *"If we only pick one plan, which would you choose?"*

**Pick `take-a-careful-look-memoized-walrus.md`.**

Three independently-verified reasons it beats my v2:

1. **Architectural correctness.** Walrus is right that `/task` should not go through the LLM. Verified: `format_input_prompt` (`prompts.py:294-300`) only rewrites `full-context` and `research` — there is **no generic mechanism** for slash → MCP-tool routing through PromptSubmitted. Sending `Invoking 'openteam_task': …` is a guess that the LLM will figure it out. For deterministic 10-stage pipelines that's an unacceptable nondeterminism.

2. **MCP timeout is real.** Verified: `mcp_toolset.py:138` defaults to **295 s**. Most `task` runs are 5–30 minutes. v2's "MCP-only" path would time out for the *typical* use case. Walrus's subprocess slash neatly sidesteps this.

3. **Phase 0 (`tool_cli.py` rendering)** is a real bug, correctly elevated to "blocking" by Walrus. v2 had it as "Phase 6 cleanup, not blocking" — that's wrong because the subprocess slash path *consumes* `tool_cli.py`'s stdout.

**What v2 had right and Walrus missed:**
- TIER-1/2/3 test tagging
- CI preflight for signature drift
- Self-audit section
- Explicit Phase 7A/B for long-running tools
- `OPENTEAM_MCP_TIMEOUT` env hint for users
- Mounted `ShellOutput` widget instead of per-line toast notifications
- OpenStartup root `pyproject.toml` (both prior plans missed this)

**The complete answer:** pick **Walrus's architecture** + **v2's rigor**. That synthesis = this v3 file.

If you literally must pick one of the two existing files, **Walrus**. v3 is what you'd want if you wanted both.

---

## 10. Open Questions

1. **Wrapper generation strategy** — keep 4 hand-written wrappers (current plan) or generate from `tool.json` at startup? Plan: hand-written + CI preflight.
2. **OPENTEAM_HOME default** — should it be configurable via a `.env` file in OpenStartup, or stay env-var-only?
3. **Phase 7A appetite** — open a PR to acra-python adding a per-server timeout override in `mcp.json`?
4. **Phase 8 publish target** — internal pip / Bitbucket release / left as `pip install -e .` forever?
