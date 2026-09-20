# OpenTeam ↔ RovoDev Integration — Integrated Plan **v5** (TRULY CONVERGED)

**Date:** 2026-05-16
**Author:** Rovo Dev (fifth-pass synthesis after ground-truth verification of all three predecessor plans)
**Supersedes:** v4 (`openteam-rovodev-integration-INTEGRATED-v4.md`), the Walrus / Claude plan (`take-a-careful-look-memoized-walrus.md`), and the Cursor plan (`openteam_rovodev_integration_88097144.plan.md`).

---

## 0. Why v5 exists (and what was wrong with v4, Walrus, and Cursor)

Each predecessor plan made claims that the other two also made; many claims agreed; **but each plan independently got several facts wrong**. v5 is grounded in a fresh re-verification of every load-bearing claim. Below is the audit; every "✓" / "✗" was checked by reading the actual file.

### 0.1 Verified ground truth

| Claim | Verified result | Where |
|---|---|---|
| `tool_cli.py` rendering is broken | ✓ **YES** — lines 124-130 do `print(result.get("text", ""))` for dicts and bare `print(result)` for objects. `ToolExecutionResult` has `.result` (not `.text`), so dict branch is dead and object branch prints the dataclass `repr()`. | `OpenStartup/src/openteam/server/services/tool_cli.py:124-130` |
| `ToolExecutionResult` is a `@dataclass` (not Pydantic) | ✓ **YES** — `@dataclass` with `result: str` + `context_updates: dict[str, Any]` | `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/protocols.py:15-22` |
| `task/cli.py` + `task/__main__.py` exist (working slash shim) | ✓ YES (11-line + 3-line shims) | `OpenStartup/src/openteam/server/resources/tools/task/{cli,__main__}.py` |
| `create_role/cli.py` + `__main__.py` exist | ✓ YES | `…/create_role/{cli,__main__}.py` |
| `role_setup/cli.py` + `__main__.py` exist | ✓ YES | `…/role_setup/{cli,__main__}.py` |
| `project_onboarding/cli.py` + `__main__.py` exist | ✗ **NO — MISSING** (only `executor.py`, `tool.json`, `project_onboarding.yaml`) | `…/project_onboarding/` |
| `slash_enabled: true` set in tool.json | Only `task` has it (line 8). `create_role`, `role_setup`, `project_onboarding` lack the key entirely. | `…/<tool>/tool.json` |
| `OpenStartup/pyproject.toml` exists | ✗ **NO** | repo root |
| AgentFoundation / RichPythonUtils have `pyproject.toml` | ✗ NO (both sys.path-only) | their repo roots |
| `OpenStartup/conftest.py` already injects sibling repos onto sys.path | ✓ YES (12 lines) — inserts `src/`, `../AgentFoundation/src`, `../RichPythonUtils/src` | `OpenStartup/conftest.py` |
| MCP client timeout is 295 s | ✓ YES — `timeout: int \| None = 295` | `acra-python/packages/code-nemo/src/nemo/utils/mcp_toolset.py:138` |
| `format_input_prompt` only rewrites `'research'` and `'full-context'` | ✓ YES (lines 292-300 — confirmed) | `acra-python/packages/cli-rovodev/src/rovodev/modules/prompts.py:292-300` |
| `cli-rovodev-tui/slash_commands/` is a real file-per-command registry | ✓ YES (~40 command files) | `…/cli-rovodev-tui/src/rovodev_tui/slash_commands/` |
| **Registration convention** — does `__init__.py` self-register, or does `app.py` do it centrally? | **`app.py` does it centrally.** `__init__.py` only re-exports `handle_*_command` symbols (no `registry.register(...)` calls). `app.py` at lines 530-573 calls `command_registry.register(handler, "/slash", extra_prompt=..., thread=...)`. | `app.py:530-573` |
| `shell.py` cancellation pattern | Top-level `from textual.worker import get_current_worker` (line 9). Inside handler: `worker = get_current_worker()` (line 48); `if worker.is_cancelled: process.terminate(); await process.wait(); break` (lines 76-78); `stderr=asyncio.subprocess.STDOUT` (merged, line 65); `if process.stdout.at_eof(): break` (line 81); `if not output.strip(): shell_output_widget.remove()` (lines 92-93). | `…/slash_commands/shell.py` |
| `mcp-atlassian-exp` uses `mcp.add_tool(FunctionTool.from_function(wrapper))` | ✓ YES (lines 94-116) | `…/mcp-atlassian-exp/src/atlassian_exp/main.py` |
| `fastmcp==3.2.4` pinned in mcp-atlassian-exp's `pyproject.toml` | ✗ **NO** — mcp-atlassian-exp declares `mcp>=1.25.0` and `pydantic-ai-slim[mcp]==1.49.0`; FastMCP is transitive. v4 and Walrus both claim "pinned to 3.2.4" — **unverifiable / wrong**. | `…/mcp-atlassian-exp/pyproject.toml` |
| `cli-rovodev` (legacy) has `slash_commands/` | ✗ NO — decorator-only in `commands/run/command.py`. v4/Walrus/Cursor all correct on this. | `cli-rovodev/src/rovodev/commands/run/command.py` |

### 0.2 Plan-by-plan error / contribution ledger

**v4 (`INTEGRATED-v4.md`):**
- ✗ Implies `project_onboarding/cli.py` exists (it does not) — Phase 2B `/project-onboarding` would `ImportError` at runtime.
- ✗ Claims `fastmcp==3.2.4` is "pinned to match acra-python's mcp-atlassian-exp" — actually only transitive in acra-python.
- ✗ Internal contradiction: Phase 2B says "stderr=STDOUT (merged)" but the handler code still calls `proc.stderr.read()` later — only one of those can be right. With STDOUT merging, `proc.stderr` is `None`.
- ✗ Hard-codes `tchen7`-specific `PYTHONPATH` in `~/.rovodev/mcp.json`.
- ✓ TIER-tagged tests, signature-alignment CI preflight, self-audit section, root `pyproject.toml`, idempotent registration guard, OPENTEAM_HOME env override, `_strip_unset` correctness comment, Phase 7A/B for long-running tools.

**Walrus (`take-a-careful-look-memoized-walrus.md`):**
- ✗ Same `project_onboarding/cli.py` omission as v4.
- ✗ Same `fastmcp==3.2.4` pin claim.
- ✗ Internal contradiction in Phase 2B subprocess block: declares "merged stderr" but its later handler version still does `await proc.stderr.read()`. Cannot have both.
- ✗ Doesn't centralize sys.path injection (leaves `conftest.py` + `mcp.json` `env:` duplicated).
- ✓ Leaner than v4. ✓ Correct `get_current_worker` top-level import. ✓ Mounted `ShellOutput` widget pattern. ✓ `if slash in registry.commands` idempotency.

**Cursor (`openteam_rovodev_integration_88097144.plan.md`):**
- ✗ Says "registration via import-side-effects in `__init__.py`" — wrong; `__init__.py` only re-exports. Real registrations are central in `app.py:530-573`.
- ✗ Claims `create_role/cli.py` and `role_setup/cli.py` are missing — wrong, they exist.
- ✓ **Correctly identifies** `project_onboarding/cli.py` + `__main__.py` are MISSING — a real blocker the other two plans missed.
- ✓ **`bootstrap.py`** to centralize sibling sys.path injection (DRY: `conftest.py`, MCP entry point, slash handler env all converge on it).
- ✓ **`[project.scripts] openteam-mcp`** console script ⇒ `mcp.json` reduces to `"command": "openteam-mcp"` (no PYTHONPATH hack).
- ✓ **`mode: Literal[...]` enum** at the MCP surface, collapsing mutually-exclusive `--plan/--execute/--full/--confirm` flags so the LLM cannot violate them.
- ✓ **Ships `templates/SKILL.md` and `templates/mcp.json`** inside the repo for reproducible install.
- ✓ **`find_openteam_mcp_binary()`** PATH→venv→`python -m` fallback chain in the TUI helper for portable execution.
- ✓ Splits four slash commands into four files (`openteam_task.py`, `openteam_create_role.py`, …) consistent with the rest of `slash_commands/` — but a shared factory keeps it DRY.

### 0.3 The synthesis

v5 = (v4's testing/packaging rigour) ∪ (Walrus's empirical fidelity to `shell.py`) ∪ (Cursor's `project_onboarding` shim, `bootstrap.py`, console script, `Literal[mode]`, templates, `find_openteam_mcp_binary()`) — **minus** the contradictions, the unverified `fastmcp==3.2.4` pin, and the hard-coded `tchen7` paths.

---

## 1. Architecture (one substrate, three surfaces)

```
┌────────────────────────── RovoDev TUI ──────────────────────────┐
│                                                                 │
│ /openteam-task <args>          subprocess: openteam-mcp run-tool│
│ /openteam-create-role <args>   --tool task -- <args>            │
│ /openteam-role-setup <args>    (fallback: python -m openteam.   │
│ /openteam-project-onboarding   server.resources.tools.<t>)      │
│                                  ↓ streamed stdout              │
│                                  ShellOutput widget             │
│  (deterministic; no LLM round-trip; NO 295 s timeout)           │
│                                                                 │
│  LLM agent          MCP call: mcp__openteam__openteam_<tool>    │
│  (agentic)          ──→ stdio JSON-RPC to openteam-mcp          │
│                          ──→ in-process executor.execute()      │
│                          (subject to 295 s MCP client timeout)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼   ~/.rovodev/mcp.json
                          │   { "command": "openteam-mcp", … }
                          ▼
   openteam-mcp run   (Typer entry — console_script)
              ↓
        bootstrap.ensure_siblings_on_path()       ← idempotent
              ↓
        create_openteam_server() → FastMCP("openteam")
              ↓
        for each of {task, create_role, role_setup,
                     project_onboarding}:
            mcp.add_tool(FunctionTool.from_function(wrapper))
              ↓
        in-process call → executor.execute(args, ctx)
              ↓
        ToolExecutionResult(result=str, context_updates=dict)
              ↓
        _render_result(result) → str  (returned to MCP client)
```

**Three invariant principles:**

1. **One substrate, three surfaces.** Standalone CLI (`python -m openteam.server.resources.tools.<t>`), MCP wrapper, and TUI slash subprocess all reach the **same** `await execute(arguments, session_context)`. No duplicate business logic.
2. **Process isolation, always.** `openteam-mcp` is a subprocess of RovoDev; never an in-process import. (RovoDev's end-user distribution is PyInstaller-frozen — additional Python imports are physically impossible.)
3. **Mirror `shell.py` line-for-line** for the slash handler. The cancellation, streaming, and cleanup patterns are *already* in production; we do not innovate on TUI ergonomics.

---

## 2. What v5 changes vs. each predecessor

| Δ | Source | Detail |
|---|---|---|
| Add `project_onboarding/cli.py` + `__main__.py` (12-line shim mirroring `task/`) | **Cursor** | Without this, `/openteam-project-onboarding` ImportError. v4 and Walrus both missed this. |
| Add `slash_enabled: true` to **3** tool.jsons (`create_role`, `role_setup`, `project_onboarding`) — task already has it | all three | Verified missing on disk |
| Phase 0 rendering fix for `tool_cli.py:124-130` (duck-typed) | all three | Real bug — verified |
| **Add `src/openteam/bootstrap.py`** with `ensure_siblings_on_path()`; refactor `conftest.py` to call it; call it at top of `openteam-mcp` entry point | **Cursor** | Removes PYTHONPATH duplication; one canonical place. v4 and Walrus leave it duplicated. |
| Add **root `pyproject.toml`** with `[project.scripts] openteam-mcp = "openteam.mcp_server.cli:app"` | **v4 (+ Cursor)** | `mcp.json` reduces to `"command": "openteam-mcp"` — no PYTHONPATH hack in user config. |
| Do **not** pin `fastmcp==3.2.4` (the v4/Walrus claim is unverified). Instead pin `fastmcp>=2.0,<4` and `mcp>=1.25.0` to match acra-python's transitive surface; CI matrix tests one upper-bound bump per quarter. | **v5 new** | Honest dependency declaration |
| Cancellation: top-level `from textual.worker import get_current_worker`; `worker = get_current_worker()` inside handler; explicit defensive `if worker is None: …` guard | **Walrus + v5** | `worker is None` only happens if `thread=True` was forgotten; defensive code is cheap. |
| Subprocess: `stderr=asyncio.subprocess.STDOUT` (merged). **Remove** the contradictory `proc.stderr.read()` block both Walrus and v4 still have. | **Walrus** + **v5** corrects | When merged, `proc.stderr` is `None`. Reading it is dead code (and would crash if we forgot the merge). |
| Empty-output cleanup: `app.call_from_thread(shell_output.remove)` when output is empty | **Walrus** | Mirrors `shell.py:92-93` |
| Idempotent registration guard `if slash in registry.commands: continue` | **v4 / Walrus** | Survives module reload in dev |
| **Slash names: `/openteam-task`, `/openteam-create-role`, …** (NOT bare `/task`) | **Cursor** + **v5** | Avoids collision risk if RovoDev later adds a generic `/task`; namespaces all four under `openteam-`. Verified: no `/task` exists today, but namespacing is the elegant choice. |
| **`mode: Literal["plan","execute","full","confirm"]`** enum at the MCP wrapper for the `task` tool, internally re-expanded into `plan`/`execute`/`full`/`confirm` booleans | **Cursor** | LLM cannot violate mutual exclusion; CLI surface unchanged. |
| **Ship `src/openteam/mcp_server/templates/SKILL.md`** and **`templates/mcp.json`** inside the repo; install docs `cp` them to `~/.rovodev/` | **Cursor** | Reproducible install; no hand-edited paths leak `tchen7`. |
| **`_openteam_shared.find_openteam_mcp_binary()`** in the TUI: PATH → `${OPENTEAM_HOME}/.venv/bin/openteam-mcp` → `python -m openteam.server.resources.tools.<t>` fallback | **Cursor** | Portable across user environments |
| Drop "Pydantic" wording for `ToolExecutionResult` (it's a `@dataclass`) | **Walrus + v5** | Verified |
| `_strip_unset` correctness inline comment explaining `0 != ""` & `0 is not False` clauses | **v4** | Prevents future regression to the buggy `in (None, False, "", [])` form |
| TIER-1/2/3 test tagging + CI preflight signature-alignment test | **v4** | Catches `tool.json` ↔ wrapper drift the moment it appears |
| Self-audit section (stress-test for hacks) | **v4** | Retain |
| Phase 7A: document `OPENTEAM_MCP_TIMEOUT` env override; open acra-python PR for per-server `timeout` in `mcp.json` schema | **v4** | Post-ship enhancement |
| Phase 7B: in-memory `FastMCPTransport` (gated) | **v4** | Future; non-blocking |
| Four slash command files (`openteam_task.py`, `openteam_create_role.py`, …) consistent with rest of `slash_commands/`, **all instantiated via one shared factory** in `_openteam_shared.py` | **Cursor + v5** | Consistent file layout + DRY |

---

## 3. Detailed design

### 3.1 File touch list

#### `CoreProjects/OpenStartup/` — NEW
```
pyproject.toml                                                # root packaging (Phase 1)
src/openteam/bootstrap.py                                     # sys.path injection (Phase 1)
src/openteam/mcp_server/__init__.py
src/openteam/mcp_server/cli.py                                # Typer entry; calls bootstrap then runs server
src/openteam/mcp_server/server.py                             # create_openteam_server() + 4 wrappers
src/openteam/mcp_server/context.py                            # build_session_context() from env vars
src/openteam/mcp_server/_helpers.py                           # _to_dash_form / _strip_unset / _render_result
src/openteam/mcp_server/templates/SKILL.md                    # canonical skill, copy-to-user template
src/openteam/mcp_server/templates/mcp.json                    # canonical MCP snippet, copy-to-user template
src/openteam/server/resources/tools/project_onboarding/cli.py # 11-line shim (Phase 0)
src/openteam/server/resources/tools/project_onboarding/__main__.py  # 3-line shim
test/openteam/mcp_server/test_server_factory.py               # TIER-1
test/openteam/mcp_server/test_context.py                      # TIER-1
test/openteam/mcp_server/test_helpers.py                      # TIER-1 (_strip_unset edge cases incl. `0`)
test/openteam/mcp_server/test_wrappers_smoke.py               # TIER-2
test/openteam/mcp_server/test_wrapper_signature_alignment.py  # TIER-1 CI preflight
test/openteam/mcp_server/test_bootstrap.py                    # TIER-1
test/openteam/server/services/test_tool_cli_rendering.py      # TIER-1 (Phase 0)
test/openteam/server/resources/tools/project_onboarding/test_cli_smoke.py  # TIER-2
docs/MCP_INTEGRATION.md
docs/MCP_SMOKE.md
```

#### `CoreProjects/OpenStartup/` — MODIFIED
```
src/openteam/server/services/tool_cli.py                      # Phase 0 rendering fix (lines 124-130)
src/openteam/server/resources/tools/create_role/tool.json     # add "slash_enabled": true
src/openteam/server/resources/tools/role_setup/tool.json      # add "slash_enabled": true
src/openteam/server/resources/tools/project_onboarding/tool.json  # add "slash_enabled": true
conftest.py                                                   # delegate to openteam.bootstrap (DRY)
```

#### `atlassian_packages/acra-python/` — NEW (PR target = `cli-rovodev-tui`)
```
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/_openteam_shared.py
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam_task.py
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam_create_role.py
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam_role_setup.py
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam_project_onboarding.py
packages/cli-rovodev-tui/docs/openteam-integration.md
packages/cli-rovodev-tui/tests/slash_commands/test_openteam_shared.py
packages/cli-rovodev-tui/tests/slash_commands/test_openteam_task.py
…(one test per command; snapshot variants behind @pytest.mark.snapshot)
```

#### `atlassian_packages/acra-python/` — MODIFIED
```
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/__init__.py
    # add four `from .openteam_<t> import handle_openteam_<t>_command` re-exports
packages/cli-rovodev-tui/src/rovodev_tui/app.py
    # near line 573, in the central command_registry.register block:
    #   command_registry.register(handle_openteam_task_command, "/openteam-task",
    #       extra_prompt="required", thread=True)
    #   … three more lines …
```

#### User-side config (one-time, after install)
```
~/.rovodev/mcp.json                                           # cp from templates/mcp.json
~/.rovodev/skills/openteam/SKILL.md                           # cp from templates/SKILL.md
```

---

### 3.2 Phase 0 — `tool_cli.py` rendering fix + missing `project_onboarding` shim + `slash_enabled` flips

**Phase 0a: rendering fix** — replace `tool_cli.py:124-130` with:

```python
# Render result — duck-typed against ToolExecutionResult (a @dataclass at
# AgentFoundation/.../protocols.py with fields .result:str and .context_updates:dict),
# legacy dict, and bare str. Avoid importing ToolExecutionResult here — keeps the
# CLI scaffold free of cross-package coupling.
if hasattr(result, "result") and hasattr(result, "context_updates"):
    print(result.result or "")
    ctx = result.context_updates or {}
elif isinstance(result, dict):
    # Backwards-compat: prefer "result", fall back to legacy "text"
    print(result.get("result") or result.get("text") or "")
    ctx = result.get("context_updates") or {}
else:
    print(str(result))
    ctx = {}

# Surface artifact paths on stderr so subprocess wrappers (and humans) can scrape them.
for key in ("workspace_path", "plan_path", "impl_path",
            "role_document_path", "doc_path", "report_path"):
    if ctx.get(key):
        print(f"[{key}] {ctx[key]}", file=sys.stderr)
return 0
```

**Phase 0b: `project_onboarding/cli.py`** (mirror `task/cli.py` verbatim, only changing the docstring and importing this tool's executor):

```python
"""Standalone CLI for the project_onboarding executor.

Driven entirely by tool.json. Usage::

    python -m openteam.server.resources.tools.project_onboarding ./docs/role.md \
        --role-setup-path ./roles/eng/role_setup_report.md
"""
from pathlib import Path
from openteam.server.services.tool_cli import run_cli
from .executor import execute

_TOOL_JSON = Path(__file__).parent / "tool.json"


def main(argv=None) -> int:
    return run_cli(_TOOL_JSON, execute, argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
```

And the 3-line `__main__.py`:

```python
"""Module entrypoint: enables `python -m openteam.server.resources.tools.project_onboarding`."""
from .cli import main
import sys
sys.exit(main())
```

**Phase 0c: `slash_enabled: true`** added to `create_role/tool.json`, `role_setup/tool.json`, and `project_onboarding/tool.json` (top-level key, next to `"name"`).

**Phase 0 tests** (`test_tool_cli_rendering.py`):
- `test_renders_tool_execution_result()` — Mock with `.result="hi"` + `.context_updates={"workspace_path":"/tmp"}`.
- `test_renders_dict_result_modern_key()` — `{"result": "hi"}`.
- `test_renders_dict_result_legacy_text_key()` — `{"text": "hi"}`.
- `test_renders_str_result()` — bare string.
- `test_falsy_result_prints_empty_line()` — `.result=""` → stdout = `"\n"`.
- `test_artifact_paths_on_stderr()` — assert each artifact key on its own stderr line.
- `test_project_onboarding_cli_imports()` — smoke: `import openteam.server.resources.tools.project_onboarding.cli` succeeds and `main(["--help"])` exits with code 0.

### 3.3 Phase 1 — Root packaging + `bootstrap.py`

**`CoreProjects/OpenStartup/pyproject.toml`** (NEW):

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openteam"
version = "0.1.0"
description = "OpenTeam multi-agent workflow runtime + MCP server."
requires-python = ">=3.11"
dependencies = [
    # FastMCP is transitively pinned by acra-python via pydantic-ai-slim[mcp];
    # we declare it explicitly with a wide-but-bounded range. CI matrix bumps
    # the upper bound one minor per quarter (see docs/MCP_INTEGRATION.md).
    "fastmcp>=2.0,<4",
    "mcp>=1.25.0",
    "typer>=0.12",
    "pyyaml>=6",
    "omegaconf>=2.3",
    "jinja2>=3.1",
    "hydra-core>=1.3",
    "attrs>=23",
    "pydantic>=2",
    "python-dotenv>=1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23"]

[project.scripts]
openteam-mcp = "openteam.mcp_server.cli:app"

[tool.setuptools.packages.find]
where = ["src"]
include = ["openteam*"]
```

After `pip install -e .` (or `uv tool install -e .`), `openteam-mcp` lives on `PATH` and `~/.rovodev/mcp.json` collapses to a one-line `"command": "openteam-mcp"` — **no PYTHONPATH leakage into user config**.

**`src/openteam/bootstrap.py`** (NEW) — the **single canonical** sibling sys.path injection:

```python
"""Ensure sibling repos AgentFoundation and RichPythonUtils are importable.

Both repos lack a pyproject.toml, so we cannot rely on pip resolution. We inject
their src/ directories onto sys.path. Idempotent — safe to call repeatedly.

Call this:
  - From `conftest.py` (tests).
  - From the top of `openteam.mcp_server.cli:app` before any `openteam.*` import.
  - From a slash command handler's environment (we set PYTHONPATH there too;
    see `_openteam_shared.py`).

Override the root via the `OPENTEAM_SIBLINGS_ROOT` env var if your checkout
diverges from the default `<repo_root>/..` layout.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

_SIBLINGS = ("AgentFoundation/src", "RichPythonUtils/src")


def ensure_siblings_on_path() -> list[Path]:
    """Insert OpenStartup/src and each sibling src/ onto sys.path[0:]. Returns inserted paths."""
    here = Path(__file__).resolve()                         # …/OpenStartup/src/openteam/bootstrap.py
    openteam_src = here.parent.parent                       # …/OpenStartup/src
    root_env = os.environ.get("OPENTEAM_SIBLINGS_ROOT")
    siblings_root = Path(root_env).resolve() if root_env else openteam_src.parent.parent

    inserted: list[Path] = []
    for candidate in (openteam_src, *(siblings_root / s for s in _SIBLINGS)):
        s = str(candidate)
        if candidate.is_dir() and s not in sys.path:
            sys.path.insert(0, s)
            inserted.append(candidate)
    return inserted
```

**Refactor `conftest.py`** (DRY):

```python
"""Root conftest.py — delegates to openteam.bootstrap for sibling sys.path."""
import sys
from pathlib import Path

# Bootstrap can be imported without the rest of openteam: it depends on nothing.
sys.path.insert(0, str(Path(__file__).parent / "src"))
from openteam.bootstrap import ensure_siblings_on_path  # noqa: E402
ensure_siblings_on_path()
```

**Tests (`test_bootstrap.py`, TIER-1):**
- `test_idempotent()` — call twice; sys.path length grows by N, not 2N.
- `test_override_env_var()` — set `OPENTEAM_SIBLINGS_ROOT=/tmp`; assert only existing dirs are inserted.
- `test_missing_siblings_silent()` — point at empty dir; no error raised, returns `[]` (or only `openteam_src`).

### 3.4 Phase 2 — MCP server (`openteam-mcp`)

#### 3.4.1 `src/openteam/mcp_server/cli.py` (Typer entry; runs bootstrap first)

```python
"""`openteam-mcp` CLI entry point. Always calls bootstrap before importing the server."""
from __future__ import annotations
import logging
from openteam.bootstrap import ensure_siblings_on_path

ensure_siblings_on_path()  # MUST run before any other openteam.* import

import typer  # noqa: E402

app = typer.Typer(add_completion=False, help="OpenTeam MCP server.")


@app.command("run")
def run(
    transport: str = typer.Option("stdio", help="stdio | http"),
    port: int = typer.Option(8765, help="Port (http transport only)"),
    tools: str = typer.Option("", help="Comma-separated subset of tool names; default = all"),
    log_level: str = typer.Option("INFO"),
) -> None:
    """Run the OpenTeam MCP server."""
    logging.basicConfig(level=log_level.upper())
    from openteam.mcp_server.server import create_openteam_server
    names = [t.strip() for t in tools.split(",") if t.strip()] or None
    server = create_openteam_server(tool_names=names)
    if transport == "stdio":
        server.run(transport="stdio")
    elif transport == "http":
        server.run(transport="http", port=port)
    else:
        raise typer.BadParameter(f"unknown transport: {transport}")


@app.command("run-tool")
def run_tool(
    tool: str = typer.Argument(..., help="Tool name without the `openteam_` prefix"),
    ctx: typer.Context = typer.Context,
) -> None:
    """Forward to the standalone CLI shim of one tool — for use by the slash command's PATH binary.

    `openteam-mcp run-tool task -- "build auth" --plan` is equivalent to
    `python -m openteam.server.resources.tools.task "build auth" --plan`.
    """
    import sys
    from importlib import import_module
    mod = import_module(f"openteam.server.resources.tools.{tool}.cli")
    sys.exit(mod.main(ctx.args))


if __name__ == "__main__":
    app()
```

#### 3.4.2 `src/openteam/mcp_server/_helpers.py`

```python
"""Wrapper-side helpers — shared by all four tool wrappers in server.py.

Kept separate so unit tests can target them without spinning up FastMCP.
"""
from __future__ import annotations
from typing import Any


def to_dash_form(d: dict[str, Any]) -> dict[str, Any]:
    """Python kwargs (`foo_bar`) → executor key convention (`foo-bar`).

    Verified at `tool_cli.py:112` — `arguments[k.replace("_", "-")] = v`.
    """
    return {k.replace("_", "-"): v for k, v in d.items()}


def strip_unset(d: dict[str, Any]) -> dict[str, Any]:
    """Remove unset / default-bool / empty parameters before forwarding to executor.

    Each clause is necessary; rewriting as `v in (None, False, "", [])` is WRONG
    because `0 == False` in Python's int/bool overload — that form would silently
    drop a literal `0` argument.

    - `v is not None`   : drops absent kwargs.
    - `v is not False`  : drops default `False` boolean flags (only present-flag is meaningful).
    - `v != ""`         : drops empty-string defaults.
    - `v != []`         : drops empty-list defaults.

    `0` is preserved because `0 != ""`, `0 != []`, and `0 is not False` are all True.
    """
    return {k: v for k, v in d.items()
            if v is not None and v is not False and v != "" and v != []}


def render_result(result: Any) -> str:
    """Duck-typed render of ToolExecutionResult / dict / str into a human-readable string.

    Surfaces context_updates artifact paths as a trailing footer so the LLM
    (or the user) can open them with the file tools.
    """
    if hasattr(result, "result") and hasattr(result, "context_updates"):
        text = result.result or ""
        ctx = dict(result.context_updates or {})
    elif isinstance(result, dict):
        text = result.get("result") or result.get("text") or ""
        ctx = dict(result.get("context_updates") or {})
    else:
        return str(result)
    artifact_keys = ("workspace_path", "plan_path", "impl_path",
                     "role_document_path", "doc_path", "report_path")
    artifacts = [f"  {k}: {ctx[k]}" for k in artifact_keys if ctx.get(k)]
    if artifacts:
        text += "\n\nArtifacts:\n" + "\n".join(artifacts)
    return text
```

#### 3.4.3 `src/openteam/mcp_server/context.py`

```python
"""Build session_context for in-process executor calls.

`{}` is also safe (verified: `_resolve_workspace` at executor.py:162-188 falls
through to `_allocate_workspace`). We surface env-driven hints so a long-lived
OpenStartup checkout can pin its workspace root, cloud_id, and credentials
without modifying user config.
"""
from __future__ import annotations
import os
import uuid
from typing import Any

_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}


def build_session_context() -> dict[str, Any]:
    ctx: dict[str, Any] = {"task_id": f"mcp-{uuid.uuid4().hex[:8]}", "interactive": None}
    for env_key, ctx_key in _ENV_MAP.items():
        v = os.environ.get(env_key)
        if v:
            ctx[ctx_key] = v
    return ctx
```

#### 3.4.4 `src/openteam/mcp_server/server.py` — factory + 4 typed wrappers

```python
"""FastMCP server exposing OpenTeam tools as in-process executor calls.

Pattern verified against `acra-python/packages/mcp-atlassian-exp/src/atlassian_exp/main.py:94-116`:
  - `mcp = FastMCP("openteam")`
  - `mcp.add_tool(FunctionTool.from_function(wrapper))` (NOT @mcp.tool decorator).
"""
from __future__ import annotations
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from openteam.mcp_server.context import build_session_context
from openteam.mcp_server._helpers import to_dash_form, strip_unset, render_result


# Hard-mapped surface; explicit > implicit. The CI preflight signature-alignment
# test (test_wrapper_signature_alignment.py) walks this list and compares each
# wrapper's typed signature against the corresponding tool.json.
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


# ─── Wrappers (one per tool — hand-written so the MCP schema is typed) ────────

async def openteam_task(
    request: str,
    # Collapsed mutually-exclusive flags from tool.json into a single enum.
    # The CLI surface still accepts --plan/--execute/--full/--confirm individually;
    # the wrapper re-expands `mode` to the corresponding boolean before forwarding.
    mode: Literal["plan", "execute", "full", "confirm"] = "full",
    agent_config: str = "breakdown-multiflow-plan-then-implement",
    model: Literal["opus[1m]", "opus", "sonnet", "haiku"] | None = None,
    override: list[str] | None = None,
    no_dual: bool = False,
    analysis: bool = False,
    multi_iter: bool = False,
    max_iterations: int = 3,
    resume: str | None = None,
    initial_plan: str | None = None,
) -> str:
    """Run an OpenTeam agent topology against a request.

    Long-running (typically 5-30 min). Subject to the MCP client's 295 s default
    timeout. For long jobs, prefer the `/openteam-task` slash command (subprocess,
    no timeout).
    """
    from openteam.server.resources.tools.task.executor import execute as _exec

    # Re-expand `mode` enum to the four mutually-exclusive booleans
    mode_flags = {"plan": False, "execute": False, "full": False, "confirm": False}
    mode_flags[mode] = True

    args = strip_unset(to_dash_form({
        "request": request,
        "agent_config": agent_config,
        **mode_flags,
        "model": model, "override": override,
        "no_dual": no_dual, "analysis": analysis,
        "multi_iter": multi_iter, "max_iterations": max_iterations,
        "resume": resume, "initial_plan": initial_plan,
    }))
    return render_result(await _exec(args, build_session_context()))


async def openteam_create_role(
    role_description: str,
    output_path: str | None = None,
    max_facets: int = 5,
    model: str | None = None,
) -> str:
    """Synthesize a role document from a free-form description."""
    from openteam.server.resources.tools.create_role.executor import execute as _exec
    args = strip_unset(to_dash_form({
        "role_description": role_description,
        "output_path": output_path,
        "max_facets": max_facets,
        "model": model,
    }))
    return render_result(await _exec(args, build_session_context()))


async def openteam_role_setup(
    role_document_path: str,
    max_facets: int = 5,
    max_inner_facets: int = 3,
    model: str | None = None,
) -> str:
    """Decompose a role document into actionable setup steps."""
    from openteam.server.resources.tools.role_setup.executor import execute as _exec
    args = strip_unset(to_dash_form({
        "role_document_path": role_document_path,
        "max_facets": max_facets,
        "max_inner_facets": max_inner_facets,
        "model": model,
    }))
    return render_result(await _exec(args, build_session_context()))


async def openteam_project_onboarding(
    project_document_path: str,
    role_setup_path: str | None = None,
    artifacts_path: str | None = None,
    max_facets: int = 5,
    model: str | None = None,
) -> str:
    """Onboard an AI employee to a project."""
    from openteam.server.resources.tools.project_onboarding.executor import execute as _exec
    args = strip_unset(to_dash_form({
        "project_document_path": project_document_path,
        "role_setup_path": role_setup_path,
        "artifacts_path": artifacts_path,
        "max_facets": max_facets,
        "model": model,
    }))
    return render_result(await _exec(args, build_session_context()))


_WRAPPERS: dict[str, Any] = {
    "openteam_task":               openteam_task,
    "openteam_create_role":        openteam_create_role,
    "openteam_role_setup":         openteam_role_setup,
    "openteam_project_onboarding": openteam_project_onboarding,
}


def create_openteam_server(tool_names: list[str] | None = None) -> FastMCP:
    """Create and configure a FastMCP server for the OpenTeam tools."""
    mcp = FastMCP("openteam")
    enabled = set(tool_names) if tool_names else {name for name, _ in _TOOL_SPECS}
    for name, _executor_path in _TOOL_SPECS:
        if name not in enabled:
            continue
        wrapper = _WRAPPERS[name]
        mcp.add_tool(FunctionTool.from_function(wrapper))
    return mcp
```

#### 3.4.5 Phase 2 tests (TIER-1 / TIER-2)

- `test_server_factory.py` (TIER-1): `create_openteam_server()` registers all 4 tools by default; `create_openteam_server(tool_names=["openteam_task"])` registers only one.
- `test_context.py` (TIER-1): `build_session_context()` includes a unique `task_id`; env-var overrides flow through (`OPENTEAM_WORKING_DIR=/x` → `ctx["working_dir"] == "/x"`).
- `test_helpers.py` (TIER-1): `strip_unset({"x": 0})` keeps `0`; `strip_unset({"x": False})` drops it; `to_dash_form` round-trips; `render_result` handles all three result shapes including the artifact footer.
- `test_wrappers_smoke.py` (TIER-2): for each wrapper, monkeypatch the executor to return a known `ToolExecutionResult`, call the wrapper, assert dash-form keys in the args dict and that `render_result` was applied.
- `test_wrapper_signature_alignment.py` (TIER-1 / **CI preflight**): for each tool, load `tool.json`, walk the wrapper's `inspect.signature`, and assert (a) every wrapper parameter maps to a tool.json parameter name (modulo the `mode` enum collapse), (b) types are compatible, (c) defaults are equal. Catches drift the moment `tool.json` changes.

### 3.5 Phase 3 — TUI slash commands (`/openteam-*`)

#### 3.5.1 `slash_commands/_openteam_shared.py` (shared factory + binary lookup)

```python
"""Shared helpers for the four /openteam-* slash commands.

Mirrors the streaming-subprocess + cancellation pattern from
`packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/shell.py` line-for-line.
"""
from __future__ import annotations
import asyncio
import os
import shlex
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from textual.worker import get_current_worker

from rovodev_tui.widgets import ShellOutput, ThinkingSpinner

if TYPE_CHECKING:
    from rovodev_tui.app import RovoDevApp


# Tool name -> Python module path. Used as the fallback when openteam-mcp is not on PATH.
TOOL_MODULES: dict[str, str] = {
    "task":               "openteam.server.resources.tools.task",
    "create_role":        "openteam.server.resources.tools.create_role",
    "role_setup":         "openteam.server.resources.tools.role_setup",
    "project_onboarding": "openteam.server.resources.tools.project_onboarding",
}


def _openteam_home() -> Path:
    """OPENTEAM_HOME if set, else the conventional CoreProjects/OpenStartup checkout."""
    return Path(os.environ.get(
        "OPENTEAM_HOME",
        str(Path.home() / "MyProjects" / "CoreProjects" / "OpenStartup"),
    ))


def find_openteam_mcp_binary() -> list[str] | None:
    """Locate `openteam-mcp` via PATH first, then ${OPENTEAM_HOME}/.venv/bin.

    Returns argv prefix (e.g. `["openteam-mcp"]` or `["/abs/.venv/bin/openteam-mcp"]`)
    or None if no binary is found. The caller can then fall back to `python -m`.
    """
    on_path = shutil.which("openteam-mcp")
    if on_path:
        return [on_path]
    venv_bin = _openteam_home() / ".venv" / "bin" / "openteam-mcp"
    if venv_bin.is_file() and os.access(venv_bin, os.X_OK):
        return [str(venv_bin)]
    return None


def _python_m_argv(tool_name: str) -> tuple[list[str], dict[str, str]]:
    """Return (argv_prefix, extra_env) for the `python -m openteam…` fallback path."""
    home = _openteam_home()
    pp_parts = [
        home / "src",
        home.parent / "AgentFoundation" / "src",
        home.parent / "RichPythonUtils" / "src",
    ]
    pythonpath = os.pathsep.join(str(p) for p in pp_parts if p.is_dir())
    python = os.environ.get("OPENTEAM_PYTHON", "python")
    return ([python, "-m", TOOL_MODULES[tool_name]], {"PYTHONPATH": pythonpath})


def build_argv_and_env(tool_name: str, user_args: list[str]) -> tuple[list[str], dict[str, str]]:
    """Compose the subprocess argv + env for a given tool, preferring the binary path."""
    binary = find_openteam_mcp_binary()
    env = {**os.environ}
    if binary is not None:
        # `openteam-mcp run-tool <tool> -- <args>` -- delegates to the same cli.main
        argv = [*binary, "run-tool", tool_name, "--", *user_args]
    else:
        # Fallback: `python -m openteam.server.resources.tools.<tool> <args>` + PYTHONPATH
        prefix, extra_env = _python_m_argv(tool_name)
        argv = [*prefix, *user_args]
        env.update(extra_env)
    return argv, env


async def run_openteam_subprocess(
    app: "RovoDevApp",
    slash: str,
    tool_name: str,
    extra_prompt: str,
) -> None:
    """The actual streaming handler — mirrors shell.py:46-94 line-for-line."""
    if not extra_prompt.strip():
        app.notify_and_log(
            f"Usage: {slash} <args>. Try: {slash} --help",
            severity="error", timeout=5,
        )
        return

    # `thread=True` was set at registration; this fetches the right worker.
    worker = get_current_worker()
    if worker is None:
        # Defensive: would only happen if thread=True was forgotten at registration.
        app.notify_and_log(
            f"{slash} cannot run: worker context missing (registration bug)",
            severity="error", timeout=10,
        )
        return

    # Mount widget + spinner (mirrors shell.py:52-55)
    shell_output = ShellOutput()
    spinner = ThinkingSpinner(f"Running OpenTeam {tool_name}")
    app.call_from_thread(app.chat_container.mount, shell_output)
    app.call_from_thread(app.chat_container.mount, spinner)

    user_args = shlex.split(extra_prompt)
    argv, env = build_argv_and_env(tool_name, user_args)

    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,   # merged — mirrors shell.py:65
        env=env,
        cwd=str(_openteam_home()),
    )
    if proc.stdout is None:
        app.call_from_thread(spinner.remove)
        return

    # Stream loop — mirrors shell.py:74-90 exactly
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
```

#### 3.5.2 The four slash command files (one per tool — each ~12 lines)

`slash_commands/openteam_task.py`:

```python
"""/openteam-task — run the OpenTeam `task` topology via subprocess."""
from __future__ import annotations
from typing import TYPE_CHECKING
from rovodev_tui.slash_commands._openteam_shared import run_openteam_subprocess

if TYPE_CHECKING:
    from rovodev_tui.app import RovoDevApp


async def handle_openteam_task_command(app: "RovoDevApp", extra_prompt: str) -> None:
    """Run an OpenTeam agent topology. All args after `/openteam-task` are
    forwarded to the underlying tool CLI. Run `/openteam-task --help` for options."""
    await run_openteam_subprocess(app, "/openteam-task", "task", extra_prompt)
```

`slash_commands/openteam_create_role.py`, `…_role_setup.py`, `…_project_onboarding.py` are isomorphic — only the slash string and tool name change.

#### 3.5.3 `slash_commands/__init__.py` patch (re-export only — NOT self-register)

```python
# Add to the existing import block:
from .openteam_task import handle_openteam_task_command
from .openteam_create_role import handle_openteam_create_role_command
from .openteam_role_setup import handle_openteam_role_setup_command
from .openteam_project_onboarding import handle_openteam_project_onboarding_command
```

#### 3.5.4 `app.py` patch — central registration (mirrors lines 530-573)

Inside the existing `command_registry.register(...)` block (after the `handle_shell_command` line at 541), insert:

```python
# OpenTeam slash commands — subprocess-based, mirror shell.py
command_registry.register(handle_openteam_task_command,
    "/openteam-task", extra_prompt="required", thread=True)
command_registry.register(handle_openteam_create_role_command,
    "/openteam-create-role", extra_prompt="required", thread=True)
command_registry.register(handle_openteam_role_setup_command,
    "/openteam-role-setup", extra_prompt="required", thread=True)
command_registry.register(handle_openteam_project_onboarding_command,
    "/openteam-project-onboarding", extra_prompt="required", thread=True)
```

(No `if slash in registry.commands: continue` guard needed at the call site — the central registration runs exactly once per `RovoDevApp.__init__`. The guard *would* be needed only if we used import-side-effects registration; we don't.)

#### 3.5.5 Phase 3 tests

- `test_openteam_shared.py` (TIER-1):
  - `find_openteam_mcp_binary()` PATH → venv → None fallback chain (monkeypatch `shutil.which`).
  - `build_argv_and_env()` produces the correct argv for both paths and includes `PYTHONPATH` only in the fallback path.
- `test_openteam_task.py` … `test_openteam_project_onboarding.py` (TIER-2):
  - Mock `asyncio.create_subprocess_exec`; assert correct argv, env, that streamed lines reach `shell_output.append`, and that cancellation calls `proc.terminate()`.
- Snapshot variants behind `@pytest.mark.snapshot` per `cli-rovodev-tui/AGENTS.md`: render a frozen-output frame in headless mode.

### 3.6 Phase 4 — Templates + install + skill

#### 3.6.1 `src/openteam/mcp_server/templates/mcp.json`

```json
{
  "mcpServers": {
    "openteam": {
      "command": "openteam-mcp",
      "args": ["run"],
      "transport": "stdio",
      "env": {
        "OPENTEAM_WORKING_DIR": ".",
        "OPENTEAM_LLM_BACKEND": "claude_cli",
        "OPENTEAM_LLM_MODEL": "sonnet"
      }
    }
  }
}
```

No `PYTHONPATH` in user config — the `openteam-mcp` console script calls `bootstrap.ensure_siblings_on_path()` itself. If a user's checkout is not the conventional `~/MyProjects/CoreProjects/OpenStartup` layout, they set `OPENTEAM_SIBLINGS_ROOT=/path/to/CoreProjects` in the `env:` block.

#### 3.6.2 `src/openteam/mcp_server/templates/SKILL.md`

```markdown
---
name: openteam
description: OpenTeam multi-agent workflow tools (agent topologies, role lifecycle, project onboarding)
allowed-tools:
  - mcp__openteam__openteam_task
  - mcp__openteam__openteam_create_role
  - mcp__openteam__openteam_role_setup
  - mcp__openteam__openteam_project_onboarding
---
# OpenTeam Tools — Slash vs MCP

Two surfaces for the same four tools:

| Surface | Best for | Timeout |
|---|---|---|
| **Slash** (`/openteam-task`, `/openteam-create-role`, `/openteam-role-setup`, `/openteam-project-onboarding`) | Direct user invocation; long-running jobs (5-30 min). Streamed live in a ShellOutput widget. | None — subprocess. |
| **MCP** (`mcp__openteam__openteam_task`, …) | Programmatic agent orchestration ("plan first, then implement"). | **295 s default**. Use `mode="plan"` for fast runs; switch the user to the slash command for `mode="full"`. |

**Common pitfalls:**
- For `openteam_task`, the four mutually-exclusive flags (`--plan` / `--execute` / `--full` / `--confirm`) are collapsed at the MCP surface into a single `mode: Literal["plan","execute","full","confirm"]` enum. The slash command's CLI still accepts the four flags individually.
- Long topology runs exceeding 295 s WILL hit the MCP timeout. Re-route to the slash command in that case.
```

#### 3.6.3 Install steps (`docs/MCP_INTEGRATION.md`)

```bash
# 1. Install OpenTeam (one-time)
cd ~/MyProjects/CoreProjects/OpenStartup
uv tool install -e .        # or: pip install -e .

# 2. Wire up RovoDev (one-time)
mkdir -p ~/.rovodev/skills/openteam
cp src/openteam/mcp_server/templates/SKILL.md ~/.rovodev/skills/openteam/
# Merge src/openteam/mcp_server/templates/mcp.json into ~/.rovodev/mcp.json
# (use `jq -s 'add' templates/mcp.json ~/.rovodev/mcp.json` or your editor)

# 3. Verify
openteam-mcp run --help                                            # should print Typer help
fastmcp dev "openteam.mcp_server.cli:create_openteam_server"       # MCP smoke
# In rovodev TUI: /openteam-task --help     → tool.json parameters listed
# In rovodev TUI: /openteam-task what is 2+2 → streamed ShellOutput, exit 0
# In rovodev TUI: /mcp                       → openteam server green; 4 tools
```

---

## 4. Phased delivery

| Phase | Scope | LOC | Time | Blocking? |
|---|---|---|---|---|
| **0** | `tool_cli.py` render fix + `project_onboarding/{cli,__main__}.py` shim + `slash_enabled: true` flips on 3 tool.jsons + tests | ~80 | 30 min | **blocks Phase 3** (slash subprocess fallback path) |
| **1** | Root `pyproject.toml` + `bootstrap.py` + refactored `conftest.py` + bootstrap tests | ~100 | 30 min | blocks Phase 2 |
| **2** | `openteam.mcp_server` package: `cli.py`, `server.py`, `_helpers.py`, `context.py`, templates + 5 test files (incl. CI signature-alignment preflight) | ~350 | ½-1 day | blocks Phase 3 binary path |
| **3** | `cli-rovodev-tui` PR: `_openteam_shared.py` + 4 slash command files + `__init__.py` re-exports + `app.py` 4-line registration block + tests + docs | ~250 | ½ day | parallel with Phase 4 once Phase 0/1/2 land |
| **4** | `templates/SKILL.md`, `templates/mcp.json`, `docs/MCP_INTEGRATION.md`, `docs/MCP_SMOKE.md` | — | ½ day | nice-to-have |
| **7A** (post-ship) | Document `OPENTEAM_MCP_TIMEOUT`; PR acra-python for per-server `timeout:` in mcp.json schema | small | 1 day | future |
| **7B** (gated) | In-memory `FastMCPTransport` for long agentic runs | medium | 1 day | future |
| **8** (gated) | Publish `openteam` to internal pip; switch templates/mcp.json to bare `openteam-mcp` (already does that) | small | future | future |

**Critical path:** Phase 0 → Phase 1 → Phase 2 → Phase 3 ‖ Phase 4.
**Time to working `/openteam-task <prompt>` end-to-end:** **~1.5 days.**

---

## 5. Test plan (TIER-tagged)

| Test | TIER | Purpose |
|---|---|---|
| `test_tool_cli_rendering.py` | 1 | Phase 0 fix — ToolExecutionResult / dict (modern + legacy key) / str / falsy / artifact stderr paths |
| `test_bootstrap.py` | 1 | `ensure_siblings_on_path()` idempotency, env override, missing-sibling tolerance |
| `test_context.py` | 1 | env-var pickup; task_id uniqueness; empty-ctx safety |
| `test_helpers.py` | 1 | `strip_unset` preserves `0`, drops False/None/""/[]; `render_result` covers all three shapes including artifact footer |
| `test_server_factory.py` | 1 | `create_openteam_server` registers all 4 tools by default; filtering works |
| `test_wrapper_signature_alignment.py` | 1 / **CI preflight** | walk `_TOOL_SPECS` × `tool.json` × `inspect.signature(wrapper)`; assert no drift (modulo `mode` enum collapse for `task`) |
| `test_wrappers_smoke.py` | 2 | each wrapper: stub executor, assert dash-form keys + render_result applied |
| `test_project_onboarding_cli_smoke.py` | 2 | `python -m openteam.server.resources.tools.project_onboarding --help` exits 0 |
| `test_openteam_shared.py` | 1 | `find_openteam_mcp_binary` PATH/venv/None fallback; `build_argv_and_env` argv shape |
| `test_openteam_<task,create_role,role_setup,project_onboarding>.py` | 2 | mock subprocess; assert argv, env, stream→widget, cancellation→terminate |
| Snapshot tests (TUI) | 2 | `@pytest.mark.snapshot` headless render of frozen output |
| Manual: `fastmcp dev …` | 3 | call `openteam_task` via MCP inspector |
| Manual: `/openteam-task what is 2+2` | 3 | streamed output, exit 0 |
| Manual: `/openteam-task --help` | 3 | parser help printed |
| Manual: Ctrl-C during long `/openteam-task` | 3 | SIGTERM to subprocess within ≤ 5 s |
| Manual: `/mcp` listing | 3 | openteam server green; 4 tools shown |

---

## 6. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| MCP 295 s timeout kills long agentic invocations | High | Slash UX is the primary path; SKILL.md documents the switch; Phase 7A env override; Phase 7B in-memory transport. |
| `fastmcp` API churns (no version pin in mcp-atlassian-exp) | Medium | We pin `fastmcp>=2,<4` ourselves; CI matrix tests one upper-bound bump per quarter; docs/MCP_INTEGRATION.md documents the policy. |
| `OPENTEAM_HOME` default path leaks `tchen7` | Medium → Mitigated | Bootstrap uses `OPENTEAM_SIBLINGS_ROOT` override; templates/mcp.json contains no hard-coded user path; install docs explain layout. |
| Wrapper signatures drift from `tool.json` | Medium | `test_wrapper_signature_alignment.py` as CI preflight. |
| `_strip_unset` regression to buggy `in (None, False, "", [])` form (would drop `0`) | Low | Inline comment in `_helpers.py` explaining why each clause is necessary; `test_helpers.py::test_zero_preserved`. |
| `project_onboarding/cli.py` missing → slash command ImportError | **was real**, mitigated by Phase 0 | Phase 0b ships the shim. Cursor caught this; v4 and Walrus did not. |
| User has neither `claude` nor `acli` on PATH (LLM backend) | Medium | `openteam-mcp` reports the missing backend cleanly; templates/mcp.json sets `OPENTEAM_LLM_BACKEND=claude_cli` as default; SKILL.md documents requirement. |
| `openteam-mcp` not on PATH (PyInstaller-frozen RovoDev) | Medium | `find_openteam_mcp_binary()` falls back to `${OPENTEAM_HOME}/.venv/bin/openteam-mcp`, then `python -m openteam.server.resources.tools.<t>` with bootstrap-discovered PYTHONPATH. |
| `get_current_worker()` returns None | Low | Defensive `if worker is None: notify-and-bail` guard in `_openteam_shared.py`; primary protection is `thread=True` at registration. |
| Stderr lost (we merge into stdout) | Low | All artifact paths *also* end up in `ctx.context_updates`, surfaced by `render_result()` as a trailing footer in the same stream. No information loss. |
| Subprocess on Windows | Low | `python -m` invocation (no shell); doc'd as Linux/macOS tested. |

---

## 7. Self-audit (stress-tested for hacks)

| Question | Answer |
|---|---|
| Are slash + MCP duplicate implementations? | **No.** Both reach `executor.execute()`. Slash goes `subprocess → cli.py → run_cli → executor`; MCP goes wrapper-direct to `executor`. Same business logic, two entry surfaces. |
| Does `_render_result` duplicate `tool_cli.py`'s rendering? | **Intentionally** — to keep the MCP path independent of the CLI scaffold (no cross-import). Phase 0 fixes the CLI scaffold to use the same duck-typing shape; the *two implementations are identical by convention*, not by code-share. A future refactor (Phase 8-ish) could lift `render_result` into a shared `openteam.common.rendering` module. |
| Does `_strip_unset` accidentally drop `0`? | **No.** `0 != ""`, `0 != []`, and `0 is not False` are all True. `test_helpers.py::test_zero_preserved` pins this. |
| Could the `mode` enum re-expansion drop bits? | **No.** It sets exactly one of the four booleans True and the rest False, matching the CLI's mutually-exclusive group semantics. The CLI surface still accepts the four flags individually. |
| Does `bootstrap.py` get called twice (test + entry)? | Yes — and it's idempotent (`if … not in sys.path`). `test_bootstrap.py::test_idempotent` pins this. |
| Both stdio-MCP AND slash work side-by-side? | **Yes** — independent paths, no shared state. |
| `python` on PATH may be wrong interpreter? | The `openteam-mcp` console script uses the venv's interpreter (`shebang`). The `python -m` fallback honors `OPENTEAM_PYTHON` env override. |
| MCP 295 s timeout — really "won't fix" for v1? | Mostly yes. Phase 7A documents the env override; Phase 7B is the structural fix (gated). Slash doesn't have the problem — that's the point. |
| Could Phase 0 fix break existing callers? | `tool_cli.py` currently prints `""` or a dataclass repr — anyone relying on either was already broken. The fix is unambiguously an improvement. The test suite at `test_tool_cli_rendering.py` pins all branches. |
| Would `register_openteam_commands` double-register if app.py is reloaded? | We register **centrally in `app.py`** (mirroring lines 530-573), which runs exactly once per `RovoDevApp.__init__`. No guard required. (If we ever switch to import-side-effects registration, add `if slash in registry.commands: continue`.) |
| Is `get_current_worker()` safe outside a worker context? | If `thread=False` was accidentally set, it returns `None` → defensive `if worker is None: notify-and-bail` in `_openteam_shared.py`. Primary protection: pin `thread=True` at registration. |
| Are we duplicating sys.path injection? | **No.** `bootstrap.ensure_siblings_on_path()` is the *only* place. `conftest.py` delegates to it. `openteam-mcp` calls it. The slash command's fallback path sets PYTHONPATH from the same set of dirs *but does not import bootstrap* (it's running in RovoDev's process, which must not import openteam) — it computes the dirs inline from `_openteam_home()` so the source-of-truth (CoreProjects layout) is shared. |
| `mode: Literal[...]` enum vs. four booleans — is this a hack? | **No.** The CLI's mutually-exclusive group is *itself* an enum dressed as flags. We surface it as the enum it actually is at the MCP layer (where LLM-friendliness matters); the underlying CLI surface is unchanged. |
| Default `OPENTEAM_HOME` exposes `tchen7` path? | Only as the *fallback* if `OPENTEAM_HOME` and `OPENTEAM_SIBLINGS_ROOT` are both unset. Honest, documented contract; install docs explain it. |
| `find_openteam_mcp_binary()` — does it leak across users? | No — it checks PATH (user-resolved) and `${OPENTEAM_HOME}/.venv/bin` (user-owned). Final fallback to `python -m` is fully relative to env. |

---

## 8. Plan comparison: v3 | v4 | Walrus | Cursor | **v5**

| Concern | v3 | v4 | Walrus | Cursor | **v5** |
|---|---|---|---|---|---|
| Slash architecture | subprocess | subprocess | subprocess | subprocess | **subprocess** ✅ |
| MCP architecture | in-process | in-process | in-process | in-process | **in-process** ✅ |
| `get_current_worker()` shown top-level | mentioned only | partial | ✅ | ✅ | **✅** |
| `stderr=STDOUT` (merged) — consistently | ✗ | ✗ (contradicts self) | ✗ (contradicts self) | ✅ | **✅ (no contradiction)** |
| Empty-output cleanup | ✗ | ✅ | ✅ | ✅ | **✅** |
| `_strip_unset` correctness inline comment | brief | detailed | brief | n/a | **detailed** |
| `ToolExecutionResult` typed correctly (`@dataclass`) | ✗ ("Pydantic") | ✅ | ✅ | ✅ | **✅** |
| TIER-tagged tests | ✅ | ✅ | mentioned | partial | **✅** |
| CI signature-alignment preflight | ✅ | ✅ | ✅ | ✅ | **✅** |
| Self-audit section | ✅ | ✅ | ✗ | ✗ | **✅ (extended)** |
| Root `pyproject.toml` | ✅ | ✅ | ✅ | ✅ | **✅** |
| **`[project.scripts] openteam-mcp`** | ✗ | ✗ | ✗ | ✅ | **✅** |
| `slash_enabled: true` on 3 tool.jsons | listed | listed | listed | listed | **listed (Phase 0c)** |
| Streaming UX (mounted widget, not toast) | ✅ | ✅ | ✅ | ✅ | **✅** |
| Phase 7A/B for long-running tools | ✅ | ✅ | risk-only | risk-only | **✅** |
| **`project_onboarding/cli.py` shim** | ✗ | ✗ | ✗ | ✅ | **✅** |
| **`src/openteam/bootstrap.py`** (centralized sys.path) | ✗ | ✗ | ✗ | ✅ | **✅** |
| **`mode: Literal[...]`** enum at MCP surface | ✗ | ✗ | ✗ | ✅ | **✅** |
| **`templates/SKILL.md` + `templates/mcp.json`** shipped in repo | ✗ | ✗ | ✗ | ✅ | **✅** |
| **`find_openteam_mcp_binary()`** PATH→venv→fallback | ✗ | ✗ | ✗ | ✅ | **✅** |
| **No `tchen7` PYTHONPATH hard-coded in user config** | ✗ | ✗ | ✗ | ✅ | **✅** |
| **`fastmcp==3.2.4` pin claim** | unverified | unverified | unverified | n/a | **honestly: `fastmcp>=2,<4`** |
| **Slash names namespaced (`/openteam-*`)** | bare `/task` | bare `/task` | bare `/task` | `/openteam-task` | **`/openteam-task`** (namespaced) |
| Removed dead `proc.stderr.read()` after merge | n/a | ✗ (contradicts) | ✗ (contradicts) | ✅ | **✅** |
| Phase count | 8 | 6+3 | 4 | 5 | **5+3 future** |
| LOC estimate | ~400 | ~480 | ~150 | ~350 | **~780 total** |
| Days to working `/openteam-task` end-to-end | 1-1.5 | 1-1.5 | "small" | ~1.5 | **~1.5** |

---

## 9. The "pick one" answer

> *"If we only pick one of the three existing plans (v4 / Walrus / Cursor), which would you choose?"*

**Pick `openteam_rovodev_integration_88097144.plan.md` (the Cursor plan).**

Three reasons, in order of weight:

1. **It catches a real blocker the other two missed.** `project_onboarding/cli.py` and `__main__.py` do **not** exist on disk (verified). v4 and Walrus both wire `/task`-style slash commands that include `/project-onboarding`, then forward to `python -m openteam.server.resources.tools.project_onboarding` — which would `ImportError` at runtime. Cursor not only spots this but ships the 11-line fix.

2. **It removes the brittle PYTHONPATH-in-mcp.json hack.** Both v4 and Walrus put `"PYTHONPATH": "/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src:…"` directly in the user-facing `~/.rovodev/mcp.json`. That's both `tchen7`-specific and gross. Cursor introduces (a) a root `pyproject.toml` with `[project.scripts] openteam-mcp = "openteam.mcp_server.cli:app"`, (b) a `bootstrap.py` module the entry point calls before any `openteam.*` import. Result: the user config collapses to `"command": "openteam-mcp"`, and sys.path injection has exactly one canonical home (verified-needed: `conftest.py` already duplicates this — bootstrap centralizes it).

3. **It's elegant on three smaller axes the other two missed:**
   - `mode: Literal["plan","execute","full","confirm"]` at the MCP surface, collapsing four mutually-exclusive boolean flags into the enum they actually are. The LLM cannot violate mutex.
   - `find_openteam_mcp_binary()` — a portable PATH → venv → `python -m` fallback chain in the TUI helper, with a friendly missing-binary panel.
   - Templates (`SKILL.md`, `mcp.json`) shipped *inside the repo* so install steps are `cp` not hand-edit.

**Caveats — what v5 (this file) recovers from v4/Walrus that Cursor lacks:**

- v4's TIER-1/2/3 test tagging + CI preflight signature-alignment test.
- v4's self-audit section (extended in §7).
- v4's `_strip_unset` correctness inline comment (Cursor doesn't surface this code at this level of detail).
- v4's Phase 7A/B for long-running tool reliability.
- Walrus's empirical fidelity to `shell.py` — Cursor describes "mirrors shell.py" but doesn't show the line-for-line `get_current_worker` + `at_eof` + `terminate` block.
- Cursor's wrong claim that the TUI registers via `__init__.py` import-side-effects — verified false. v5 uses the central `app.py:530-573` style.
- Cursor's wrong claim that `create_role/cli.py` and `role_setup/cli.py` are missing — verified false (only `project_onboarding`'s is).

**Bottom line:** Walrus has converged onto the same architecture as v3/v4 and is slightly leaner; Cursor has converged onto the same architecture AND catches the most real bugs of the three. v4 is the rigorous parent but contains an internal contradiction (merged stderr but reads `proc.stderr` anyway) and misses two of Cursor's bugs. **Cursor > Walrus > v4** — but v5 (this file) makes the choice moot.

---

## 10. Open questions (for follow-up)

1. **Phase 7A appetite** — open a PR to `acra-python` adding a per-server `timeout:` field in `mcp.json` config schema?
2. **Phase 8 publish target** — internal pip / Bitbucket release / leave at `pip install -e .` forever?
3. **`fastmcp` upper-bound cadence** — quarterly bump in CI matrix, or pin tighter (`fastmcp~=3.2` once mcp-atlassian-exp pins explicitly)?
4. **Bootstrap convergence** — should the slash command helper *also* import `openteam.bootstrap` (currently it computes sibling dirs inline because importing openteam into RovoDev's process is forbidden)? Discussion: keeping them in sync is achievable by re-reading the same constants from a small `openteam/_siblings.py` data-only module that has no openteam imports. Defer to Phase 4.5.
5. **`openteam_subagent`** — ship a `~/.rovodev/subagents/openteam-orchestrator.md` for agentic LLM use? Cheap (deferred to Cursor's §5).
6. **Reverse direction (`RovoDevCliInferencer`)** — OpenTeam already uses RovoDev as an LLM backend; out of scope here but worth a follow-up doc.

---

## 11. Acceptance checklist (DoD)

- [ ] `openteam-mcp run --help` prints Typer help.
- [ ] `fastmcp dev openteam.mcp_server.cli:create_openteam_server` lists 4 tools.
- [ ] In RovoDev: `/openteam-task --help` prints tool.json parameters.
- [ ] In RovoDev: `/openteam-task what is 2+2` streams output, exits 0.
- [ ] In RovoDev: `/openteam-create-role "Senior Backend Engineer"` produces a role markdown path on stderr.
- [ ] In RovoDev: `/openteam-role-setup ./roles/engineer.md` produces a setup report path.
- [ ] In RovoDev: `/openteam-project-onboarding ./docs/role.md` runs (this is the path that ImportErrored without Phase 0b).
- [ ] In RovoDev: `/help` lists all 4 `/openteam-*` commands.
- [ ] In RovoDev: Ctrl-C during a long `/openteam-task` SIGTERMs the subprocess within ≤ 5 s.
- [ ] In RovoDev: `/mcp` shows `openteam` server green, 4 tools listed.
- [ ] Agent path: `mcp__openteam__openteam_task(request="what is 2+2", mode="plan")` returns a string with `result:` text + `Artifacts:` footer.
- [ ] CI: `test_wrapper_signature_alignment.py` is green (catches future tool.json drift).
- [ ] CI: `test_helpers.py::test_zero_preserved` is green (catches `0 == False` regression).
- [ ] Docs: `docs/MCP_INTEGRATION.md` install runbook reproduces end-to-end on a clean checkout.

---

**End of v5.**
