# How RovoDev Works With Plugins & Extensions — A Deep Dive

**Date:** 2026-05-08 09:31
**Author:** Rovo Dev (code-grounded investigation)
**Companion to:** `rovodev-tools-and-subagents-deep-dive.md` and
`openteam-rovodev-integration-INTEGRATED-v4.md`
**Source of truth:** Read line-by-line from `acra-python` packages and `~/.rovodev/`.

---

## 0. The headline answer

**RovoDev has 7 distinct extension mechanisms, but no traditional setuptools-plugin system.**
Of those 7, **two are unambiguously "plugin-like" and were missing from our prior dives:**

| Mechanism | Status | Helps OpenTeam integration? |
|---|---|---|
| 1. First-party tool      | covered before | No — internal only |
| 2. MCP server (subprocess) | covered before | **YES — primary path for v4** |
| 3. Skill (`SKILL.md`)    | covered before | **YES — already in v4 §3.9** |
| 4. Subagent (`*.md`)     | covered before | Optional v5 (`openteam-orchestrator`) |
| 5. Slash command (Python) | covered before | **YES — primary user UX in v4** |
| **6. Event Hook** (config.yml + shell cmds) | **NEW — major find** | **YES — opt-in for users; no acra-python changes** |
| **7. Global Callback** (Python class) | **NEW** | Internal-only; not for cross-org integration |

**No setuptools entry-points anywhere.** Verified: zero `[project.entry-points]` blocks in any `pyproject.toml`, zero `importlib.metadata.entry_points()` calls. RovoDev's loaders are **all hardcoded path-walks** of well-known directories (`~/.rovodev/skills/`, `.rovodev/subagents/`, `.rovodev/mcp.json`, etc.).

This is consequential for the v4 plan: **we cannot ship `openteam-bridge` as a `pip install`-able plugin** that auto-registers itself. v4 already correctly relies on a 4-line opt-in patch in `app.py`. The new finding is that the **Event Hooks** mechanism gives us *additional* user-side extensibility that doesn't require any patch to acra-python at all.

---

## 1. The 7 extension mechanisms (full picture)

### Mechanism 1 — First-party tool
*Covered in the prior dive.* `code-nautilus/src/nautilus/tools/*.py`. Internal to RovoDev. **Not relevant to OpenTeam.**

### Mechanism 2 — MCP server
*Covered.* `~/.rovodev/mcp.json` registers a subprocess. **Primary path** for OpenTeam → agent.

### Mechanism 3 — Skill
*Covered.* `~/.rovodev/skills/<name>/SKILL.md`. v4 already includes `~/.rovodev/skills/openteam/SKILL.md`.

### Mechanism 4 — Subagent
*Covered.* `~/.rovodev/subagents/<name>.md`. v4 mentions `openteam-orchestrator` as optional v5.

### Mechanism 5 — Slash command
*Covered.* `slash_commands/openteam.py` + 4-line `app.py` opt-in. **Primary user UX** in v4.

### Mechanism 6 — Event Hooks (**NEW finding**)

Officially documented at `cli-rovodev/docs/.../event-hooks.md` (gated feature, dated 2026-04-04). This is the closest thing to a *user-facing plugin system* that RovoDev has.

**What it is:** declarative shell commands wired to agent-lifecycle events. Configured in `~/.rovodev/config.yml`:

```yaml
eventHooks:
  logFile: "~/.rovodev/event_hooks.log"
  events:
    - name: "on_complete"
      commands:
        - command: "echo 'Agent run finished'"
    - name: "on_user_prompt"
      commands:
        - command: "/path/to/script.sh"
    - name: "on_session_end"
      commands:
        - command: "notify-send 'Session ended'"
```

**Available events** (verified at `event_hooks/types.py`):

| Event | When it fires |
|---|---|
| `on_session_start` | Once per new agent session |
| `on_session_end` | Session switch, fork, or CLI/TUI exit |
| `on_user_prompt` | User submits a prompt |
| `on_tool_start` | Before agent executes tool calls |
| `on_tool_end` | After agent completes tool calls |
| `on_tool_permission` | Agent requires tool permissions |
| `on_complete` | Agent run successfully completes |
| `on_error` | Agent fails to generate an LLM response |

**How it actually works** (verified at `event_hooks/callback.py`):
- An `EventHooksCallback(Callback[ArtifactDepsT])` is registered automatically when `eventHooks` is non-empty in the config (`common/agent.py:276`).
- Each `on_*` lifecycle method on the callback shells out to user-configured commands via `asyncio.create_subprocess_exec`, with a **600 s default timeout**.
- **JSON payload on stdin** — every command receives a structured JSON envelope:

```json
{
  "session_id": "abc-123",
  "transcript_path": "/tmp/.../message_history.json",
  "cwd": "/home/user/my-project",
  "timestamp": "2026-03-20T12:00:00+00:00",
  "hook_event_name": "on_tool_start",
  "attributes": {
    "tool_calls": [
      {"tool_name": "bash", "tool_call_id": "call_001"}
    ]
  }
}
```

- **Hooks can BLOCK execution** — a hook command can return exit code `2` (`BLOCK_EXIT_CODE` at `callback.py:30`) with an output payload that says "stop", and RovoDev will halt the in-flight tool call. Powerful — and dangerous; documented as "only use hooks from trusted sources".
- **Multiple commands per event run in parallel.**
- **Output goes to `~/.rovodev/event_hooks.log`.**
- **Managed via `/hooks` slash command** (`event_hooks/command.py:handle_hooks_command`).

**Why this is important for OpenTeam:**
This is **the** mechanism for users who want OpenTeam to react to *RovoDev events* without modifying acra-python. Examples:
- `on_session_end` → `python -m openteam.server.resources.tools.task --resume <id>` to keep a long topology alive across sessions.
- `on_complete` → trigger an OpenTeam `role-setup` to onboard the next role.
- `on_tool_start` (filtered for OpenTeam tool calls) → record telemetry into OpenTeam's session log.

### Mechanism 7 — Global Callback (in-process Python)

Verified at `code-nemo/src/nemo/core/__init__.py:27` (`def add_global_callback(callback: Callback) -> None`).

**What it is:** a Python-level extension point for *anyone running inside the same venv as acra-python* to register a `Callback` subclass that hooks into 16 agent-lifecycle methods (`on_session_start`, `on_user_prompt_start`, `on_model_request_start`, `on_stream_part_*`, `on_call_tools_*`, `on_agent_run_*`, `on_error`, `on_mcp_servers_start`).

**How it's used today** (`code-nemo/src/nemo/callbacks/__init__.py:11-15`):

```python
add_global_callback(LoggingCallback())
add_global_callback(response_header_capture_callback)
```

**For third-party use:**
- Pro: full Python access; can mutate agent state, observe streams, modify outgoing requests.
- Con: requires `import nemo.core; nemo.core.add_global_callback(...)` at startup. **No plugin discovery** — someone has to call it. So practically: only callable from inside acra-python or from a package the user installs into the same venv that hooks `import` events… i.e. **not viable for cross-org integration**.

This mechanism is the *engine* under Event Hooks (Mechanism 6) — `EventHooksCallback` is just a `Callback` subclass that's registered when `config.yml` has `eventHooks:` populated.

---

## 2. What we ruled out (so we don't waste time)

| Idea | Why it's not viable for OpenTeam |
|---|---|
| **Setuptools entry-points** (`[project.entry-points."rovodev.plugins"]`) | RovoDev does not call `importlib.metadata.entry_points()` anywhere. Adding this would be an upstream change to acra-python (we floated it as Phase 4 in v1; v3/v4 dropped it for a reason). |
| **Namespace packages** (`pkgutil.iter_modules`) | Same — no callsite. |
| **`~/.rovodev/extensions.yaml`** that lists Python module paths | Doesn't exist. There's `config.yml` (typed Pydantic schema, no arbitrary `import:` field), `mcp.json` (MCP-only), `prompts.yml` (string templates with `content_file`, no Python imports). |
| **`prompts.yml` as a plugin loader** | Verified at `cli-rovodev/src/rovodev/modules/prompts.py:100` (`load_prompt_config`). Schema only supports name+description+content/content_file. No Python evaluation. |
| **`dynamic_config.py` for user code** | Verified — `DynamicConfiguration` fetches *server-side* config (feature flags etc.) from a remote endpoint. It does not import user code. |
| **Middleware / on-message hooks** | None exist. The base `Callback` (Mechanism 7) is the closest, and it's pre/post lifecycle, not request-mutating. |

---

## 3. The "5 vs 7" reconciliation

Our prior `rovodev-tools-and-subagents-deep-dive.md` listed 5 mechanisms (Tools, MCP, Skill, Subagent, Slash). That was **correct for what's LLM-visible or user-typed**. The 2 *additional* mechanisms (Event Hooks, Global Callback) operate **out-of-band** from the LLM's tool catalog — they hook the agent runtime around the model rather than feeding it new abilities.

```
                     What it adds to the LLM      Activated by    Process
  1 First-party       a tool (function call)      LLM             in-proc
  2 MCP               a tool (compressed)         LLM             subprocess
  3 Skill             instructions (on demand)    LLM (get_skill) in-proc
  4 Subagent          a delegated agent           LLM (invoke_…)  in-proc Agent fork
  5 Slash             nothing                     USER keystroke  in-proc
  ─── Out-of-band wrt the LLM: ─────────────────────────────────────────
  6 Event Hook        nothing                     RovoDev event   subprocess (per cmd)
  7 Global Callback   nothing                     RovoDev event   in-proc Python
```

Rephrased: **Mechanisms 1–4 grow the LLM's catalog; Mechanism 5 grows the user's; Mechanisms 6–7 grow the runtime's response to lifecycle events.**

---

## 4. Implications for the OpenTeam ↔ RovoDev integration plan (v4)

### v4 already uses the 3 right mechanisms

- ✅ **Mechanism 2 (MCP)** — `openteam/mcp_server/` exposes 4 tools to the agent.
- ✅ **Mechanism 3 (Skill)** — `~/.rovodev/skills/openteam/SKILL.md` tells the agent when to reach for OpenTeam.
- ✅ **Mechanism 5 (Slash)** — `slash_commands/openteam.py` + 4-line `app.py` patch gives users `/task`, etc.

### v4 should ADD an optional Mechanism 6 layer

A new **Phase 5.5 — Event Hook templates** is added below. This is purely additive and ships as **documentation + sample config** in OpenStartup; no code in acra-python.

**Sample event hooks for OpenTeam users** (ship as `OpenStartup/_dev/templates/rovodev_event_hooks.yaml`):

```yaml
# Example ~/.rovodev/config.yml additions for OpenTeam users
eventHooks:
  events:
    # Auto-resume long topologies if a session ends mid-run
    - name: on_session_end
      commands:
        - command: |
            if [ -n "$OPENTEAM_RESUME_TASK_ID" ]; then
              python -m openteam.server.resources.tools.task --resume "$OPENTEAM_RESUME_TASK_ID" >> ~/.rovodev/openteam_resume.log 2>&1 &
            fi

    # Notify when a /task pipeline finishes
    - name: on_complete
      commands:
        - command: 'osascript -e ''display notification "Rovo Dev /task finished" with title "OpenTeam"'' || true'

    # Block harmful tools by inspecting the JSON-on-stdin payload
    - name: on_tool_start
      commands:
        - command: |
            python -c "
            import sys, json
            payload = json.load(sys.stdin)
            for tc in payload['attributes'].get('tool_calls', []):
                if tc['tool_name'].startswith('mcp__openteam__') and 'destroy' in str(tc.get('args', '')):
                    print('BLOCK: openteam destructive op detected', file=sys.stderr)
                    sys.exit(2)   # exit 2 = block
            sys.exit(0)
            "
```

Three concrete user wins:
1. **Recovery** — auto-resume long pipelines if RovoDev/the user closes the session.
2. **Notifications** — OS-level notifications when long jobs finish (no need to babysit the TUI).
3. **Safety** — pre-flight inspect MCP tool calls and *block* (exit 2) if criteria match.

### v4 should NOT add a Mechanism 7 layer

`add_global_callback(...)` is in-process Python and would require shipping an `openteam-bridge` Python package that runs at acra-python startup. We already considered this in v1 and rejected it for the same reason: **there's no auto-discovery; someone has to import the package**, which means either (a) modifying acra-python or (b) requiring users to install OpenTeam into the acra-python venv — both worse than the current MCP/slash split.

---

## 5. Comparison matrix (extended to 7)

```
                  │ 1.First   │ 2.MCP     │ 3.Skill   │ 4.Sub-     │ 5.Slash   │ 6.Event    │ 7.Global
                  │   party   │           │           │   agent    │           │   Hook     │   Callback
──────────────────┼───────────┼───────────┼───────────┼────────────┼───────────┼────────────┼──────────
Defined in        │ tools/    │ MCP       │ SKILL.md  │ subagent   │ slash_    │ config.yml │ Python
                  │ *.py      │ server    │           │ *.md       │ commands/ │ eventHooks │ Callback
                  │           │ (any lang)│           │            │ *.py      │            │ subclass
Loaded by         │ get_tool  │ mcp_      │ skill     │ subagent   │ command_  │ config     │ add_
                  │           │ utils.py  │ walker    │ walker     │ registry  │ loader     │ global_
                  │           │           │           │            │ .register │            │ callback
Initiated by      │ LLM       │ LLM       │ LLM       │ LLM        │ USER      │ Lifecycle  │ Lifecycle
                  │           │           │           │            │           │ event      │ event
Process boundary  │ in-proc   │ subproc   │ in-proc   │ in-proc    │ in-proc   │ subproc    │ in-proc
                  │           │ (per srv) │           │ (Agent fk) │           │ (per cmd)  │
LLM-visible       │ ✅         │ ✅         │ ✅         │ ✅          │ ❌         │ ❌          │ ❌
User-visible      │ ❌         │ ❌         │ ❌         │ ❌          │ ✅         │ ✅          │ ❌
Auto-discovery    │ NA         │ NA        │ ✅ dir     │ ✅ dir      │ ❌         │ ✅ config  │ ❌
Can BLOCK tool    │ N/A       │ N/A       │ N/A       │ N/A        │ N/A       │ ✅ exit 2  │ ✅ raise
Receives JSON     │ N/A       │ N/A       │ N/A       │ N/A        │ N/A       │ ✅ stdin   │ N/A
Officially named  │ "tool"    │ "MCP      │ "skill"   │ "subagent" │ "slash    │ "event     │ "callback"
                  │           │ server"   │           │            │ command"  │ hook"      │
OpenTeam role     │ —         │ ✅ primary│ ✅ skill   │ ⚠️ optional│ ✅ primary│ 🆕 add Ph5.5│ —
                  │           │ agent path│ for guide │ orchestrator│ user UX  │ recovery+  │ in-proc only
                  │           │           │           │            │           │ notify     │
```

---

## 6. Updated v4 phase plan (with Phase 5.5)

| Phase | Scope | LOC | Time | Blocking? |
|---|---|---|---|---|
| 0 | `tool_cli.py` rendering fix + slash_enabled flips | ~50 | 30 min | blocks Phase 2B |
| 1 | `openteam/mcp_server/` package + tests + root `pyproject.toml` | ~280 | ½–1 day | blocks Phase 2A |
| 2A | `~/.rovodev/mcp.json` + manual MCP smoke | — | 15 min | parallel with 2B |
| 2B | `slash_commands/openteam.py` + 4-line `app.py` patch | ~140 | ½ day | parallel with 2A |
| 3 | TIER tests + CI preflight | ~100 | ½ day | nice-to-have |
| 4 | `SKILL.md` + `MCP_INTEGRATION.md` + `MCP_SMOKE.md` | — | ½ day | nice-to-have |
| **5.5 NEW** | **Sample `eventHooks` templates + docs** | ~100 LOC YAML+MD | ½ day | post-ship |
| 7A | Document MCP timeout override | small | 1 day | post-ship |
| 7B | Optional in-memory `FastMCPTransport` | medium | 1 day | future |
| 8 | Internal pip publish; bare `openteam-mcp` | small | future | future |

---

## 7. Self-audit (stress-tested)

| Question | Answer |
|---|---|
| Did the previous deep-dive miss Mechanism 6 (Event Hooks) and 7 (Global Callback)? | Yes — both. The previous dive listed Skill/Subagent/Slash as the "3 LLM-extending" mechanisms, but Event Hooks and Global Callbacks live *outside* the LLM catalog and were therefore not hit by tool/skill/subagent searches. |
| Is Event Hook a "real" plugin system or a half-feature? | Real and shipped. Officially documented (`event-hooks.md`), gated by feature flag, has a slash command (`/hooks`), Pydantic schema (`EventHooksConfig`), 600 s timeout per command, JSON-on-stdin payloads, exit-code-2 blocking, in-parallel multi-command execution per event, log file, and was discussed in an Atlassian blog post. |
| Could OpenTeam be shipped purely as Event Hooks? | No — Event Hooks fire on RovoDev events, not from agent-initiated tool calls. They observe + react; they don't grow the LLM's capabilities. So Hooks alone don't replace the MCP path. |
| Does Mechanism 7 give us anything Mechanism 6 doesn't? | Yes for in-process state mutation (e.g. modify model requests pre-send), but no for cross-org integration because there's no discovery. Skip for OpenTeam. |
| Could the v4 plan recommend the user *replace* the slash command with an Event Hook? | No — Event Hooks fire on already-emitted events; they can't *initiate* a tool call. The slash command initiates; the hook observes. Keep slash. |
| Is the "no setuptools entry-points" finding firm? | Yes. Multi-agent grep across all `pyproject.toml` files in acra-python found zero `[project.entry-points]` blocks for any RovoDev group. Zero `importlib.metadata.entry_points()` callsites. Zero `pkgutil.iter_modules`. Confirmed. |
| Are there other extension points hidden in callback registration we missed? | One worth noting: `inline_system_prompts` on `AgentDefinition` lets a callback inject system prompts mid-conversation (`agent_definition.py` near line 916). Not relevant to OpenTeam but useful to know exists. |

---

## 8. The single most useful summary

If you remember nothing else: **RovoDev has 7 extension mechanisms, organized along two axes:**

1. **What it grows:** the LLM's catalog (1–4), the user's UX (5), or the runtime's reactivity (6–7).
2. **Where the discovery happens:** filesystem walks of well-known dirs (3, 4), explicit registration in code (1, 5, 7), config files (2, 6).

For OpenTeam, the elegant integration uses **2 + 3 + 5** (already in v4) and **optionally 6** (added as Phase 5.5). It avoids **1** (would be a fork), **4** (only useful for orchestrating multi-step OpenTeam workflows), and **7** (no discovery; venv-coupled).

That 3-of-7 selection is exactly what v4 ships, with Phase 5.5 as a clean opt-in extension users can adopt without any acra-python or OpenStartup changes.
