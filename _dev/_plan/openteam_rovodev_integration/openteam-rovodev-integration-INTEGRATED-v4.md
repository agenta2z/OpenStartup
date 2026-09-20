# OpenTeam ↔ RovoDev Integration — Integrated Plan v4 (FINAL — converged)

**Date:** 2026-05-08 06:28
**Author:** Rovo Dev (fourth-pass synthesis; the architecture is now stable)
**Inputs:**
- `openteam-rovodev-integration-INTEGRATED-v3.md` (mine — Walrus architecture + v2 rigor)
- `take-a-careful-look-memoized-walrus.md` (Walrus — leaner, identifies 2 v3 omissions)
**Supersedes:** Both prior plans for the OpenTeam↔RovoDev question.

> **Pick-one headline answer:** **Walrus and v3 now converge on the same architecture.**
> If forced to pick ONE existing file, **pick Walrus** — it's leaner, has the
> proven `shell.py`-mirrored cancellation, and identifies two real omissions
> in v3 (cancellation pattern + merged stderr). v4 keeps Walrus's empirical
> fidelity to `shell.py` and adds back v3's CI-preflight rigour and the new
> `pyproject.toml` groundwork.

---

## 0. New ground-truth (verified 2026-05-08 06:28)

Three things were checked since v3 was written:

| Check | Verified result | Implication |
|---|---|---|
| Does `_strip_unset` in v3 §3.3 have the `0 == False` bug Walrus alleged? | **No** — v3 used inequality (`v != ""`) not membership (`v in (..., "", [])`). `0 != ""` is True (different types) so 0 is preserved. **`v is not False` is also necessary** because `False != ""` and `False != []` are both True (different types) — without it, `False` would slip through. v3's logic is correct. | Walrus's bug claim doesn't apply to v3, but the comment was useful: keep `v is not False` and document *why*. |
| Does `ShellOutput` actually have `.append()`? | **Yes** — at `widgets/shell_output.py` it inherits from Textual's `Markdown` and uses inherited `Markdown.append()`. Currently used by `slash_commands/shell.py:89` (verified in production). | v3's plan to call `shell_output.append(line)` is sound. |
| How is cancellation actually wired in production `shell.py`? | `from textual.worker import get_current_worker` at top of file; inside the handler: `worker = get_current_worker()` and `if worker.is_cancelled: process.terminate(); await process.wait(); break`. The handler signature is unchanged (`async def handler(app, prompt)`); the worker is fetched via the thread-local `get_current_worker()`. | v3 mentioned `worker.is_cancelled` but didn't show the import. Walrus shows it correctly. v4 adopts Walrus's exact wiring. |
| Does v3 stream stderr separately or merged? | v3 uses `stderr=PIPE` separately, then `proc.stderr.read()` only after the stdout loop ends. Walrus uses `stderr=STDOUT` (merged). | Walrus's merged-stderr pattern is correct: any stderr-emitted artifact paths interleave naturally with stdout, and the cancellation-checking read loop covers both streams. Adopt. |
| Does `project_onboarding/tool.json` already have `slash_enabled: true`? | **No** — verified absent. | Phase 0 must include the flag flip. |

**Net effect**: Walrus has caught up to (and in 2 places, surpassed) v3.
The architecture is stable; the remaining plan delta is small and surgical.

---

## 1. Architecture (final, unchanged from v3)

```
┌──────────────────────── RovoDev TUI ────────────────────────┐
│                                                             │
│  /task <args>          ──→  subprocess: python -m openteam. │
│  /create-role <args>          server.resources.tools.<tool> │
│  /role-setup <args>           ───→ ShellOutput widget       │
│  /project-onboarding <args>         (streaming stdout)      │
│                                                             │
│        (deterministic; no LLM round-trip; no 295s timeout)  │
│                                                             │
│  LLM agent             ──→  MCP call: mcp__openteam__<tool> │
│      (programmatic           ───→  in-process executor      │
│       agentic use)                  call (subject to 295s)  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼   ~/.rovodev/mcp.json
                       │
                       ▼
   python -m openteam.mcp_server.main run        (stdio)
                       │
                       ▼
        ┌─── openteam/mcp_server/ ────────────────────┐
        │  server.py   create_openteam_server()       │
        │              FastMCP("openteam")            │
        │              + add_tool × 4                 │
        │  context.py  build_session_context()        │
        │  main.py     Typer entry                    │
        └─────────────────────────────────────────────┘
                       │
                       ▼   in-process call
        executor.execute(args, ctx) → ToolExecutionResult
```

**Key invariants:**
- Slash commands shell out to the standalone CLIs (deterministic, no LLM, no MCP timeout).
- MCP wrappers call executors **in-process** within the MCP server subprocess (no nested subprocess).
- `shell.py`'s widget+spinner+`get_current_worker()`+`proc.terminate()` pattern is the spec for cancellation. We **mirror it line-for-line** for the four OpenTeam handlers.

---

## 2. What changes from v3 → v4

| Δ | Source | Detail |
|---|---|---|
| Cancellation: explicit `from textual.worker import get_current_worker` and `worker = get_current_worker()` inside each handler | **Walrus** | v3 mentioned but didn't show; Walrus mirrors `shell.py:48` exactly |
| Subprocess: `stderr=asyncio.subprocess.STDOUT` (merged) | **Walrus** | Cleaner; one read loop covers both streams; matches `shell.py:71` |
| Stream loop also calls `proc.stdout.at_eof()` and breaks if true | **Walrus** | Mirrors `shell.py:80`; safer against partial buffers |
| Empty-output cleanup: `if not output.strip(): app.call_from_thread(shell_output.remove)` | **Walrus** | v3 leaves an empty Markdown widget; Walrus removes it |
| Add comment to `_strip_unset` explaining why each clause is needed | new in v4 | prevents future regressions to `in (None, False, "", [])` (which would be the buggy form) |
| Promote Phase 0 (`tool_cli.py` rendering) to "blocking" only if subprocess slash UX needs it; otherwise mark as "polish" | **Walrus** | v3 still tagged it blocking; Walrus correctly notes that the MCP path bypasses `tool_cli` (it calls `executor.execute` directly), and the slash path does the result rendering inside `tool_cli.run_cli` (so YES, blocking — verified). Net: keep blocking. |
| Phase 0 must also include `slash_enabled: true` flips on 3 `tool.json` files | both | v3 lists this; Walrus confirms it's still needed (verified `project_onboarding/tool.json` lacks it) |
| Keep all of v3's: TIER tagging, CI preflight, self-audit section, OpenStartup root `pyproject.toml`, mounted `ShellOutput` (not toast notifications), idempotent registration | **v3** | Walrus does not regress on these; v4 retains |
| Drop v3's misleading "Pydantic" reference for `ToolExecutionResult` | new in v4 | Verified: it's a `@dataclass` at `agent_foundation/.../protocols.py`. Update wording in 2 places. |

---

## 3. Detailed Design (consolidated)

### 3.1 Files

#### OpenStartup repo — new

```
pyproject.toml                                                # NEW root (3.7)
src/openteam/mcp_server/__init__.py
src/openteam/mcp_server/server.py
src/openteam/mcp_server/context.py
src/openteam/mcp_server/main.py
test/openteam/mcp_server/test_server_factory.py               # TIER-1
test/openteam/mcp_server/test_context.py                      # TIER-1
test/openteam/mcp_server/test_wrappers_smoke.py               # TIER-2
test/openteam/mcp_server/test_wrapper_signature_alignment.py  # TIER-1 (CI preflight)
test/openteam/server/services/test_tool_cli_rendering.py      # TIER-1 (Phase 0)
docs/MCP_INTEGRATION.md
docs/MCP_SMOKE.md
```

#### OpenStartup repo — modified

```
src/openteam/server/services/tool_cli.py                      # Phase 0 rendering fix
src/openteam/server/resources/tools/create_role/tool.json      # add slash_enabled: true
src/openteam/server/resources/tools/role_setup/tool.json       # add slash_enabled: true
src/openteam/server/resources/tools/project_onboarding/tool.json  # add slash_enabled: true
```

#### acra-python repo — new

```
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py
```

#### acra-python repo — modified

```
packages/cli-rovodev-tui/src/rovodev_tui/app.py               # 4-line opt-in import block
```

#### User-side config

```
~/.rovodev/mcp.json
~/.rovodev/skills/openteam/SKILL.md
```

### 3.2 Phase 0 — `tool_cli.py` rendering fix (BLOCKING for slash, ~20 min)

Replace lines 121-127 of `tool_cli.py`:

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

Use **`hasattr` duck-typing** to avoid fragile cross-package import of
`ToolExecutionResult`.

**Tests** (`test_tool_cli_rendering.py`):
- `test_renders_tool_execution_result()` — Mock with `.result` + `.context_updates`.
- `test_renders_dict_result()` — `{"result": "yo"}`.
- `test_renders_str_result()` — bare string.
- `test_falsy_result_is_empty_line()` — `.result=""` → stdout = `"\n"`.
- `test_artifact_paths_on_stderr()` — assert each artifact key on its own stderr line.

### 3.3 `mcp_server/server.py` (consolidated)

```python
"""FastMCP server exposing OpenTeam tools as in-process executor calls."""
from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from openteam.mcp_server.context import build_session_context

# Hard-mapped surface; explicit > implicit
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
        mcp.add_tool(FunctionTool.from_function(_get_wrapper(name)))
    return mcp


def _to_dash_form(d: dict) -> dict:
    """foo_bar → foo-bar (matches tool_cli.py:111 dispatcher convention)."""
    return {k.replace("_", "-"): v for k, v in d.items()}


def _strip_unset(d: dict) -> dict:
    """Drop unset parameters. Each clause is intentional:

    - `v is not None`     : drops genuinely-unset args (None default)
    - `v is not False`    : drops boolean flags whose default is False
                           (because `False != ""` is True, and `False != []`
                           is True, so without this clause `False` would slip
                           through the != tests below)
    - `v != ""`           : drops empty-string defaults (must be `!=`, not
                            `is not`, because string interning isn't guaranteed)
    - `v != []`           : drops empty-list defaults (similar reason)

    Crucially, `0` is preserved: `0 != ""` and `0 != []` are both True
    (cross-type `!=`), and `0 is not False` is True (different objects).
    DO NOT rewrite this as `v in (None, False, "", [])` — that would drop
    `0` because `0 == False` is True in Python's int/bool overload.
    """
    return {k: v for k, v in d.items()
            if v is not None and v is not False and v != "" and v != []}


def _render_result(result: Any) -> str:
    """Duck-typed against ToolExecutionResult (a dataclass at
    agent_foundation/.../protocols.py). Falls back to dict / str."""
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


# ── Wrappers (one per tool, hand-written for type-checked signatures) ─────

async def openteam_task(
    request: str,
    agent_config: str = "breakdown-multiflow-plan-then-implement",
    plan: bool = False, execute: bool = False,
    full: bool = True, confirm: bool = False,
    model: str | None = None,
    override: list[str] | None = None,
    no_dual: bool = False, analysis: bool = False,
    multi_iter: bool = False, max_iterations: int = 3,
    resume: str | None = None, initial_plan: str | None = None,
) -> str:
    """Run an agent topology. Default: PlanThenImplement breakdown-multiflow.

    Long-running (typically 5–30 min). Subject to MCP client timeout
    (default 295s). For long jobs prefer the /task slash command (subprocess,
    no timeout).
    """
    from openteam.server.resources.tools.task.executor import execute as _exec
    args = _strip_unset(_to_dash_form({
        "request": request, "agent_config": agent_config,
        "plan": plan, "execute": execute, "full": full, "confirm": confirm,
        "model": model, "override": override, "no_dual": no_dual,
        "analysis": analysis, "multi_iter": multi_iter,
        "max_iterations": max_iterations, "resume": resume,
        "initial_plan": initial_plan,
    }))
    return _render_result(await _exec(args, build_session_context()))


# ... openteam_create_role, openteam_role_setup, openteam_project_onboarding
#     follow the same template; signatures derived from each tool.json.

_WRAPPERS = {
    "openteam_task": openteam_task,
    "openteam_create_role": openteam_create_role,
    "openteam_role_setup": openteam_role_setup,
    "openteam_project_onboarding": openteam_project_onboarding,
}


def _get_wrapper(name: str):
    return _WRAPPERS[name]
```

### 3.4 `mcp_server/context.py`

```python
"""Build session_context for in-process executor calls.

`{}` is also safe (verified: executor's `_resolve_workspace` allocates a
fresh workspace under `server/_runtime/tasks/` when keys are absent), but
we surface env-driven hints so a long-lived OpenStartup checkout can pin
its workspace root, cloud_id, and credentials without modifying RovoDev.
"""
from __future__ import annotations
import os, uuid
from typing import Any

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
import asyncio, logging
import typer

from openteam.mcp_server.server import create_openteam_server

app = typer.Typer()


@app.command("run")
def run(
    tools: str = typer.Option("", help="CSV of tool names; empty = all."),
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

### 3.6 `slash_commands/openteam.py` (FINAL — mirrors `shell.py` exactly)

```python
"""Subprocess slash commands for OpenTeam tools.

Mirrors slash_commands/shell.py:
- ShellOutput widget + ThinkingSpinner (mounted on app.chat_container)
- get_current_worker() + worker.is_cancelled → proc.terminate()
- stderr=STDOUT (merged read loop)
- per-line shell_output.append() via app.call_from_thread

Why subprocess (not PromptSubmitted): RovoDev's format_input_prompt()
(prompts.py:294-300) only rewrites two hardcoded prefixes (full-context,
research). Anything else goes to the LLM as raw text — unreliable for
deterministic pipelines. Subprocess gives deterministic execution,
real-time streaming, proper exit codes, and SIGTERM cancellation.
"""
from __future__ import annotations
import asyncio
import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from textual.worker import get_current_worker

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
_TOOL_MODULES: dict[str, str] = {
    "/task":               "openteam.server.resources.tools.task",
    "/create-role":        "openteam.server.resources.tools.create_role",
    "/role-setup":         "openteam.server.resources.tools.role_setup",
    "/project-onboarding": "openteam.server.resources.tools.project_onboarding",
}


def _make_handler(slash: str, module: str):
    async def handler(app: "RovoDevApp", extra_prompt: str) -> None:
        from rovodev_tui.widgets import ShellOutput, ThinkingSpinner

        if not extra_prompt.strip():
            app.notify_and_log(
                f"Usage: {slash} <args>. Try: {slash} --help",
                severity="error", timeout=5,
            )
            return

        worker = get_current_worker()  # threadlocal — works because thread=True

        # Mount widget + spinner (mirrors shell.py:52-55)
        shell_output = ShellOutput()
        spinner = ThinkingSpinner(f"Running OpenTeam {slash[1:]}")
        app.call_from_thread(app.chat_container.mount, shell_output)
        app.call_from_thread(app.chat_container.mount, spinner)

        argv = shlex.split(extra_prompt)
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                str(p) for p in _PYTHONPATH_DIRS if p.is_dir()),
        }

        proc = await asyncio.create_subprocess_exec(
            os.environ.get("OPENTEAM_PYTHON", "python"), "-m", module, *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,   # merged, mirrors shell.py:71
            env=env, cwd=str(_OPENTEAM_HOME),
        )
        if proc.stdout is None:
            app.call_from_thread(spinner.remove)
            return

        # Stream loop — mirrors shell.py:76-90
        output = ""
        while True:
            if worker.is_cancelled:
                proc.terminate()
                await proc.wait()
                break
            if proc.stdout.at_eof():
                break
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", "replace")
            output += decoded
            app.call_from_thread(shell_output.append, decoded)

        await proc.wait()
        app.call_from_thread(spinner.remove)

        if not output.strip():
            app.call_from_thread(shell_output.remove)

        if proc.returncode and proc.returncode != 0:
            app.notify(
                f"{slash} exited with code {proc.returncode}",
                severity="error", timeout=8,
            )

    handler.__doc__ = (
        f"Run OpenTeam's {slash[1:]} tool via subprocess.\n\n"
        f"All arguments after {slash} are forwarded to the tool's CLI.\n"
        f"Run `{slash} --help` for available options."
    )
    handler.__name__ = f"handle_{slash[1:].replace('-', '_')}_command"
    return handler


def register_openteam_commands(registry: "SlashCommandRegistry") -> None:
    """Idempotent: skips slash names already registered."""
    for slash, module in _TOOL_MODULES.items():
        if slash in getattr(registry, "commands", {}):
            continue
        registry.register(
            _make_handler(slash, module),
            slash,
            extra_prompt="required",
            thread=True,  # subprocess I/O → worker thread (matches shell.py)
        )
```

**`app.py` patch** (after the existing `command_registry.register(...)` block, ~line 604):

```python
# OpenTeam commands — opt-in; no-op if module not installed
try:
    from rovodev_tui.slash_commands.openteam import register_openteam_commands
    register_openteam_commands(command_registry)
except ImportError:
    pass
```

### 3.7 OpenStartup root `pyproject.toml` (NEW)

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openteam"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp==3.2.4",     # pinned to match acra-python's mcp-atlassian-exp
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

Unlocks `pip install -e .`, removes `PYTHONPATH` hacks long-term, and ships a clean `openteam-mcp run` entry point.

### 3.8 `~/.rovodev/mcp.json`

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

### 3.9 Skill (`~/.rovodev/skills/openteam/SKILL.md`)

```markdown
---
name: openteam
description: OpenTeam multi-agent workflow tools (task pipelines, role lifecycle, project onboarding)
allowed-tools:
  - mcp__openteam__openteam_task
  - mcp__openteam__openteam_create_role
  - mcp__openteam__openteam_role_setup
  - mcp__openteam__openteam_project_onboarding
---
# OpenTeam Tools

Two ways to use these:

1. **Slash commands** (deterministic; recommended for users):
   - `/task <request>`               — agent topology
   - `/create-role <description>`    — synthesize a role document
   - `/role-setup <role.md>`         — decompose & onboard a role
   - `/project-onboarding <doc.md>`  — onboard an AI employee to a project

2. **MCP tools** (for agent self-orchestration):
   - `mcp__openteam__openteam_task(request=…, agent_config=…)`
   - …

⚠️  MCP tools are subject to the **295 s default client timeout**. For runs
expected to take >5 min, prefer the slash command (subprocess, no timeout).
```

---

## 4. Phased Delivery (consolidated)

| Phase | Scope | LOC | Time | Blocking? |
|---|---|---|---|---|
| **0** | `tool_cli.py` rendering fix + 5 tests; flip `slash_enabled: true` on 3 `tool.json`s | ~50 | 30 min | **blocks Phase 2B** |
| **1** | `openteam/mcp_server/` package + 4 wrappers + tests + root `pyproject.toml` | ~280 | ½–1 day | blocks Phase 2A |
| **2A** | `~/.rovodev/mcp.json` + manual MCP smoke (`fastmcp dev`) | — | 15 min | parallel with 2B |
| **2B** | `slash_commands/openteam.py` + 4-line `app.py` patch | ~140 | ½ day | parallel with 2A |
| **3** | TIER-1/2 tests + CI preflight (signature alignment) | ~100 | ½ day | nice-to-have |
| **4** | `SKILL.md` + `MCP_INTEGRATION.md` + `MCP_SMOKE.md` | — | ½ day | nice-to-have |
| **7A** | Document `OPENTEAM_MCP_TIMEOUT`; PR acra-python for per-server timeout override | small | 1 day | post-ship |
| **7B** | (Optional) In-memory `FastMCPTransport` for higher MCP timeout — gated | medium | 1 day | future |
| **8** | (Optional) Publish `openteam` to internal pip; switch `mcp.json` to bare `openteam-mcp run` | small | future | future |

**Critical path:** Phase 0 → Phase 1 → (2A ‖ 2B) → 3 ‖ 4.
**Time to working `/task <prompt>` end-to-end:** **~1–1.5 days.**

---

## 5. Test Plan (TIER-tagged)

| Test | TIER | Purpose |
|---|---|---|
| `test_tool_cli_rendering.py` | 1 | Phase 0 fix; ToolExecutionResult / dict / str / falsy / artifact paths |
| `test_context.py` | 1 | env-var pickup; task_id uniqueness |
| `test_server_factory.py` | 1 | `create_openteam_server` filtering, default = all |
| `test_wrappers_smoke.py` | 2 | each wrapper: stub executor, assert dash-form keys + `_render_result` |
| `test_wrapper_signature_alignment.py` | 1 | walk `_TOOL_SPECS` & wrappers; assert no drift vs `tool.json` |
| Manual MCP smoke | 3 | `fastmcp dev openteam.mcp_server.main:run` → call `openteam_task` |
| Manual `/task` E2E | 3 | `/task what is 2+2` → streamed output, exit 0 |
| Manual `/task --help` | 3 | parser help printed |
| Manual cancellation | 3 | Ctrl-C during long `/task` → SIGTERM in <5 s |
| `/mcp` listing | 3 | `openteam` server green; 4 tools shown |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| MCP 295 s timeout for long agentic invocation | High | Slash UX is primary; doc'd in SKILL.md; Phase 7A env override; Phase 7B in-memory transport |
| `fastmcp` not in OpenStartup venv | High → Mitigated | Phase 1 root `pyproject.toml` pins `fastmcp==3.2.4` |
| `PYTHONPATH` brittle across users | Medium | `OPENTEAM_HOME` env override; Phase 8 console_scripts |
| Wrapper signatures drift from `tool.json` | Medium | Phase 3 CI preflight (`test_wrapper_signature_alignment.py`) |
| Per-line `notify_and_log` floods UI (Walrus's earlier draft) | Mitigated | We mount one `ShellOutput` widget and `.append()` per line |
| `format_input_prompt` rewrites collide with `/task` | None | We don't use the `Invoking '…':` prefix at all in the slash path |
| Subprocess on Windows | Low | We invoke `python -m`, not shell; doc'd as Linux/macOS tested |
| Default `OPENTEAM_HOME` is `tchen7`-specific | Medium | Honest contract; doc'd in `MCP_INTEGRATION.md`; ship a `.env.example` |
| `_strip_unset` future regression to `in (..., False, "", [])` form | Low | Inline comment in §3.3 explains exactly why each clause is needed |

---

## 7. Self-Audit (stress-tested for hacks)

| Question | Answer |
|---|---|
| Are slash + MCP duplicate implementations? | **No.** Both reach `executor.execute()`. Slash goes file→CLI→executor; MCP goes executor directly. Same business logic. |
| Does `_render_result` duplicate `tool_cli.py`? | Intentionally — to keep the MCP path independent of the CLI path. Phase 8-ish refactor: lift into a shared helper if both drift. |
| Does `_strip_unset` accidentally drop `0`? | **No** — `0 != ""` and `0 != []` are True (cross-type `!=`). Verified inline in code comment. |
| Default `OPENTEAM_HOME` exposes `tchen7` to upstream? | Documented as a personal default; ship `.env.example`; honest contract. |
| Both stdio-MCP AND slash work side-by-side? | **Yes** — independent paths, no shared state. |
| `python` on PATH may be wrong interpreter? | `OPENTEAM_PYTHON` env override. |
| MCP 295 s timeout — is it really "won't fix" for v1? | Mostly yes. Phase 7A documents env override; Phase 7B is the structural fix (gated). Slash doesn't have the problem — that's the point. |
| Could Phase 0 fix break existing callers? | `tool_cli.run_cli` currently always prints `""` on real runs (the broken `result.get("text","")` path). Anyone relying on emptiness was already broken; the fix is unambiguously an improvement. |
| Would `register_openteam_commands` double-register if app.py is reloaded? | **No** — the `if slash in registry.commands: continue` guard makes it idempotent. |
| Is `get_current_worker()` safe outside a worker context? | If `thread=False` accidentally, it returns `None` and `worker.is_cancelled` would `AttributeError`. We pin `thread=True` at registration. Add a defensive `if worker is not None:` guard if we want belt+suspenders. |

---

## 8. Plan Comparison: v3 vs Walrus vs **v4**

| Concern | v3 | Walrus | **v4 (this)** |
|---|---|---|---|
| Slash architecture | Subprocess ✅ | Subprocess ✅ | **Subprocess** ✅ |
| MCP architecture | In-process ✅ | In-process ✅ | **In-process** ✅ |
| Cancellation: `get_current_worker()` shown | Mentioned, not shown | Shown, line-for-line `shell.py` | **Shown, line-for-line** ✅ |
| `stderr=STDOUT` (merged) | No (PIPE separate) | Yes ✅ | **Yes** ✅ |
| Empty-output cleanup | No | Yes ✅ | **Yes** ✅ |
| `_strip_unset` correctness comment | Brief | Brief | **Detailed inline (§3.3)** ✅ |
| `ToolExecutionResult` accurately typed | "Pydantic" (wrong) | "dataclass" ✅ | **dataclass** ✅ |
| TIER-tagged tests | ✅ | Mentions, no list | **✅** |
| CI preflight (signature alignment) | ✅ | ✅ | **✅** |
| Self-audit section | ✅ | None | **✅** |
| OpenStartup root `pyproject.toml` | ✅ | None | **✅** |
| `slash_enabled: true` on 3 tool.jsons | Listed | Listed (Phase 3) | **Listed in Phase 0 (correct sequencing)** |
| Streaming UX (no toast flood) | Mounted widget ✅ | Mounted widget ✅ | **Mounted widget** ✅ |
| Long-running tool plan | Phase 7A/B explicit | Mentions in Risks | **Phase 7A/B explicit** ✅ |
| Phase count | 8 | 4 | **6 + 3 future** |
| LOC estimate | ~400 | ~150 | **~480 (more rigour, fewer phases)** |
| Days to ship | 1–1.5 | "small" | **1–1.5** |

---

## 9. The pick-one answer

> *"If we only pick one plan, which would you choose?"*

**Pick `take-a-careful-look-memoized-walrus.md`.** Walrus has converged onto the same architecture as v3 and is *leaner* and *more empirically faithful* to the production `shell.py` pattern. Specifically:

1. **Cancellation is shown correctly.** Walrus imports `get_current_worker` and mirrors `shell.py:48,76` line-for-line. v3 mentioned `worker.is_cancelled` but never showed the import — a reader implementing v3 verbatim would silently fail.
2. **Merged `stderr=STDOUT`.** Walrus reads stderr into the same loop that checks for cancellation. v3 read stderr separately *after* the stdout loop — meaning a stuck stderr could keep a cancelled subprocess running indefinitely.
3. **Smaller surface.** Walrus is ~150 LOC of plan; v3 is ~400. For an integration this contained, Walrus's brevity is a feature.

**What v3 has that Walrus lacks** (and why v4 — this file — is the actual best answer):
- TIER-1/2/3 test tagging
- CI preflight comparing wrapper signatures vs `tool.json` (drift detection)
- Self-audit section (§7) stress-testing for hacks
- OpenStartup root `pyproject.toml` (the missing groundwork both v2 and Walrus skipped)
- Detailed inline comment on `_strip_unset` (prevents future regression to the buggy `in (..., False, "", [])` form)
- Explicit Phase 7A/B for long-running tools + `OPENTEAM_MCP_TIMEOUT` escape hatch

**Complete answer:** **Walrus's empirical fidelity to `shell.py` + v3's testing/packaging rigour = this v4 file.** If you must pick one of the existing two files, **pick Walrus** — and treat the items above as your adoption checklist.

---

## 10. Open Questions

1. **Wrapper generation strategy** — keep 4 hand-written wrappers (current plan) or generate from `tool.json` at startup? Plan: hand-written + CI preflight.
2. **`OPENTEAM_HOME` default** — `~/MyProjects/CoreProjects/OpenStartup` is `tchen7`-specific. Ship `.env.example`?
3. **Phase 7A appetite** — open a PR to acra-python adding a per-server timeout override in `mcp.json`?
4. **Phase 8 publish target** — internal pip / Bitbucket release / left as `pip install -e .` forever?
5. **Defensive `get_current_worker()` guard** — should `_make_handler` `if worker is None: return early`? Not strictly needed if we pin `thread=True`, but cheap.
