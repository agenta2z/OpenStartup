# How RovoDev Works With Tools & Subagents — A Deep Dive

**Date:** 2026-05-08 09:25
**Author:** Rovo Dev (code-grounded investigation)
**Companion to:** `openteam-rovodev-integration-INTEGRATED-v4.md`
**Source of truth:** Read line-by-line from `acra-python` packages.

> **Headline answer (your question first):**
>
> > *"Subagents are just like spawning another rovodev, is that correct?"*
>
> **Almost — but the precise model is more elegant.** A subagent is **NOT a
> separate Python subprocess**. It's an **in-process `pydantic-ai` Agent
> instantiation** that runs on `nemo.core.agent_runner.run_agent(...)` —
> the same function the parent uses — but with:
> - Its own `AgentDefinition` (system prompt, tool list, model)
> - Its own *fresh* conversation history (no parent messages)
> - Its own `SessionContext(is_subagent=True)`
> - Concurrent execution (up to 4 in parallel via `asyncio.gather`)
> - A short `summary` string returned to the parent (not the full transcript)
>
> So conceptually: yes, "another rovodev". Implementation-wise: same Python
> process, same event loop, separate Agent + session.

---

## 1. The 5 Extension Mechanisms (the mental map)

RovoDev has exactly **five** ways to teach it new behavior. Knowing which one
to reach for is the most important skill for integrating anything new.

| # | Mechanism | Surface to LLM | Defined in | Loaded by | Lifecycle | Best for |
|---|---|---|---|---|---|---|
| 1 | **First-party tool** | JSON-schema function call | `code-nautilus/src/nautilus/tools/*.py` (e.g. `bash`, `open_files`, `grep`) | Imported at startup; `get_tool(workspace, fn)` binds workspace, strips it from sig | Per-call, in-process | Generic capabilities everyone needs (filesystem, shell, search) |
| 2 | **MCP tool** | JSON-schema function call (compressed: 2 functions per server, `get_tool_schema` + `invoke_tool`) | External process (any language); manifest in `~/.rovodev/mcp.json` | `mcp_utils.py` spawns the subprocess + connects via stdio/sse/http | Per-call, in-subprocess | Cross-language tools, tools with their own deps, third-party APIs |
| 3 | **Skill** | One generic tool (`get_skill`); LLM passes a name → returns markdown instructions | `~/.rovodev/skills/<name>/SKILL.md` (YAML frontmatter + body); also `.agents/`, `.codex/`, `.claude/` paths | `nemo.core.agent_definition.SkillDefinition.from_*` walkers | Per-call (LLM has to ask) | Reusable instruction sets / playbooks (research, jira workflows) |
| 4 | **Subagent** | One generic tool (`invoke_subagents`) that takes lists of `(name, task, task_name)` | `.rovodev/subagents/<name>.md` (YAML frontmatter: `name`, `description`, `model`, `tools`, body) | `cli-rovodev/modules/subagents.py` walks dirs → `SubagentDefinition` | Per-call, in-process Agent w/ fresh history | Decomposing a problem into 1–4 focused parallel sub-tasks |
| 5 | **Slash command** | **NOT visible to LLM** — purely client-side TUI input parser | `cli-rovodev-tui/src/rovodev_tui/slash_commands/*.py` | `command_registry.register(handler, "/name", ...)` in `app.py:541-604` | Per-keystroke, user-initiated | Deterministic UX shortcuts the user invokes, not the agent |

### Critical implication

- **Tools 1, 2, 3, 4 are LLM-visible** — they appear in the LLM's tool catalog
  and the model decides when/whether to call them.
- **Tool 5 (slash) is user-only** — pressing `/foo` runs Python directly; the
  LLM never sees `/foo` as a callable.

This is why our OpenTeam integration plan (v4) uses **two separate paths**:
- A **slash command** for users (Mechanism 5; deterministic; subprocess shell-out).
- An **MCP server** for the agent (Mechanism 2; same business logic, in-process executor calls).

---

## 2. First-party tool — concrete pattern

**Where:** `packages/code-nautilus/src/nautilus/tools/`

**Example** (`open_files.py`):

```python
@tool_annotations_registry.readonly        # ← decorator marks safety class
def open_files(
    workspace: Workspace,                  # ← injected; LLM never sees this
    file_paths: list[str],
    _intent: str,                          # ← injected at runtime by RovoDev
) -> list[str | ImageContent]:
    """Open one or more files in the workspace. Supports text, image, PDFs.
    """
    # body
```

**Schema generation:** automatic via `pydantic-ai`'s `Tool.from_function` — it
inspects the signature (after `get_tool` strips `workspace`), pulls the
docstring, generates JSON schema, hands the function to the LLM.

**Dispatch:** in `nemo/core/agent_runner.py`, `pydantic-ai` matches the LLM's
tool_use to the registered Python function and `await`s it.

**Lifecycle:**
1. LLM emits `tool_use(name="open_files", args={...})`.
2. `agent_runner` looks up the function, calls it with `await`.
3. Return value is JSON-serialized, sent back as `tool_result`.
4. LLM continues the loop.

---

## 3. MCP tool — concrete pattern

**Where they live:** **outside** acra-python — any language, any process.
RovoDev only needs the manifest.

**Manifest:** `~/.rovodev/mcp.json`:

```json
{ "mcpServers": { "openteam": {
    "command": "python", "args": ["-m", "openteam.mcp_server.main", "run"],
    "env": { "PYTHONPATH": "..." } }}}
```

**Spawn:** at startup, `mcp_utils.py` launches each server as a subprocess and
connects over the chosen transport (stdio/SSE/streamable-http). It then
discovers tools (FastMCP advertises a `list_tools` capability).

**Compression:** RovoDev presents *two* tools per server to the LLM:
- `mcp__<server>__get_tool_schema(tool_name)`
- `mcp__<server>__invoke_tool(tool_name, tool_input)`

This keeps the model's tool catalog small even when an MCP server has 100+
tools.

**Lifecycle:** identical to first-party at the LLM level (one tool call per
invocation), but I/O crosses a subprocess boundary.

---

## 4. Skill — concrete pattern

**Where:** `~/.rovodev/skills/<name>/SKILL.md` (and `.agents/`, `.claude/`,
`.codex/`, plus built-ins). **YAML frontmatter + markdown body.**

```yaml
---
name: research                             # 1-64 chars, [a-z0-9-]
description: Conducts deep research...     # 1-1024 chars
allowed-tools:                              # informational; expands schemas
  - mcp__atlassian__search_jira_using_jql
  - bash
license: MIT                                # optional
---
# Research skill
You are conducting research...
```

**Loaded by:** `SkillDefinition` (Pydantic model in
`nemo/core/agent_definition.py:953`) via the cli-rovodev skill walker.

**Surface to LLM:** ONE tool — `get_skill(skill_name_or_path)` — which the
model calls *on demand*. The system prompt only shows a short index of skill
names + 1-line descriptions. The skill body is loaded only when invoked. This
is why skills don't bloat the context window even if you have dozens.

**Lifecycle:** lazy. The skill body is markdown text; it's injected as a
*tool result* (not as a system prompt). Once received, the LLM treats the
text as guidance for the rest of the conversation.

---

## 5. Subagent — concrete pattern (the question you asked)

**Where:** `.rovodev/subagents/<safe-name>.md` (also `~/.rovodev/subagents/`).
Same frontmatter+body shape as skills.

```yaml
---
name: commit-summarizer
description: Analyzes git commits and generates conventional summaries
model: anthropic.claude-3-5-sonnet-20241022-v2:0   # OPTIONAL
tools:                                              # OPTIONAL — filter
  - bash
  - open_files
  - grep
---
You are a specialized agent that analyzes git commits...
```

**Pydantic shape** (`nemo/core/agent_definition.py:933`):

```python
class SubagentDefinition(BaseModel):
    name: str
    description: str
    agent_def: AgentDefinition[ArtifactDeps]   # ← FULL Agent, not a sub-Agent
    scope: str = "project"                     # built-in / project / user
    model_factory: Callable[[], Any] | None    # avoids event-loop binding bugs
```

So **a subagent IS a full `AgentDefinition`** (system prompt, model, tool
list) — the parent is just one of many.

### Dispatch — what *actually* happens when LLM calls `invoke_subagents`

Read carefully — this is the real model
(`nemo/core/agent_definition.py:521-680`):

```python
async def invoke_subagents(
    self, ctx: RunContext[ArtifactDepsT],
    subagent_names: list[str],
    task_descriptions: list[str],
    task_names: list[str],
) -> str:
    """Delegate tasks to specialized subagents.
    Up to 4 subagent tasks can be invoked at once.
    The delegated agents will only have the context you provide before
    it starts working on the task and cannot see the conversation history.
    """
    from nemo.core.agent_runner import run_agent       # ← SAME runner as parent

    async with self._get_subagent_lock():               # ← global lock (one batch at a time)
        # Validate (≤ 4 subagents, lengths match, names exist)…

        async def _run_single_subagent(name, task_desc, formatted_name):
            sub_agent_def = copy(self.subagents[name].agent_def)  # ← shallow copy
            sub_agent_def.agent = copy(sub_agent_def.agent)       # ← so name can differ per call
            sub_agent_def.agent.name = formatted_name

            # Refresh model to dodge event-loop binding bugs
            if self.subagents[name].model_factory is not None:
                sub_agent_def.model = self.subagents[name].model_factory()

            session_ctx = SessionContext(
                is_subagent=True,                             # ← flag distinguishes
                subagent_tool_call_id=ctx.tool_call_id,
            )
            session_ctx = await run_agent(                    # ← SAME runner!
                sub_agent_def,
                prompt=task_desc,                             # ← only the task; NO parent msgs
                streaming=ctx.deps.streaming,
                callbacks=callbacks,                          # ← inherits + SubagentCLICallback
                session_ctx=session_ctx,
            )

            # Persist subagent session under parent's log dir for analysis
            …

            summary = str(session_ctx.latest_result)
            note_entries = []                                  # ← ENTRY: lines you sometimes see
            for message in session_ctx.message_history:
                if isinstance(message, ModelResponse):
                    for resp_part in message.parts:
                        if isinstance(resp_part, TextPart) and resp_part.content != summary:
                            note_entries.append("ENTRY: " + resp_part.content)
            notes = "\n\n".join(note_entries)
            return SUBAGENT_RESPONSE_TEMPLATE.format(
                name=formatted_name, task=task_desc,
                notes=notes, summary=summary,
            )

        tasks = [_run_single_subagent(n, d, f) for n, d, f in zip(...)]
        results = await asyncio.gather(*tasks, return_exceptions=True)   # ← parallel up to 4
        # Combine, raise ModelRetry on errors, else return joined string
```

### Crisp answers to the 6 questions you'd want to ask

| Question | Answer |
|---|---|
| Spawned as subprocess? | **No.** Same Python process, same event loop, in-process pydantic-ai Agent via `run_agent(...)`. |
| Own conversation history? | **Yes** — fresh `SessionContext`; **no parent messages** ("cannot see the conversation history" — verbatim from the docstring). |
| Same tool registry as parent? | **Defaults to parent's tool list (inherited via `agent_def`)**, but a subagent's frontmatter `tools:` field declares an *informational* allowlist that the loader narrows the registered tool set down to. |
| Same model as parent? | **Optional** — the subagent's frontmatter can specify a `model:`; if omitted, it falls back to the parent's. The `model_factory` exists to recreate model objects per invocation (avoids stale HTTP clients across event loops). |
| Share parent's MCP servers? | **Yes** — MCP servers live at the agent_def level and are inherited (subject to the `tools` allowlist). |
| What does parent get back? | A **string** containing `summary + notes (ENTRY: lines)` per subagent, joined. Not the full transcript, not structured data. |
| Sequential or concurrent? | **Concurrent** — `asyncio.gather` over up to 4. There IS a global subagent lock (`_get_subagent_lock`) preventing two batches from overlapping. |

### So is a subagent "another rovodev"?

**Functionally yes; mechanically no:**

- ✅ **Yes**: it has its own system prompt, model, tool list, conversation,
  callbacks, session log, and runs the **same `run_agent` orchestrator**. From
  the LLM's vantage, "I called invoke_subagents → I got back a summary from a
  little colleague".
- ❌ **No**: it's not a separate process, separate venv, or separate CLI invocation.
  It's an in-process Agent instance. No `subprocess.Popen("rovodev …")` happens.
- 📝 **Where the metaphor breaks down**: a subagent has **no parent context by
  default** (it doesn't see the parent's conversation), no slash commands, no
  TUI; it returns a *summary* not a UX. So if the user pictures "popping open a
  new RovoDev terminal", that's wrong — there's no UI; just a callable Agent.

**Useful corrected mental model:**
> A subagent is *a `python-ai` Agent that the parent owns and can fork off
> tasks to in parallel*. Think of it as `asyncio.create_task(run_agent(child))`
> with a different system prompt, scoped tool list, and isolated history.

---

## 6. The full lifecycle of a single LLM tool call (any mechanism)

```
LLM streams tokens → produces a tool_use block
   │
   ▼
nemo/core/agent_runner detects tool_use
   │
   ▼
Look up the tool callable:
   • first-party? get_tool(workspace, fn) registered earlier
   • MCP? compressed; LLM picks server.tool, runtime forwards to subprocess
   • skill? one tool: get_skill(name) → returns markdown
   • subagent? one tool: invoke_subagents(...) → forks 1-4 child Agents
   │
   ▼
await tool(args)   (with permission check via PauseOnToolCallsCallback;
                    user may be prompted "Allow once / Always / Deny")
   │
   ▼
result → JSON-serialize → tool_result block
   │
   ▼
Send back to LLM. LLM continues with the augmented context.
```

Permission handling lives in `cli-rovodev/modules/tool_permissions.py`. By
default `invoke_subagents` is now subject to the same `allow/ask/deny` flow as
any other tool (per release notes; was previously always-allowed).

---

## 7. Implications for the OpenTeam ↔ RovoDev integration plan (v4)

This deep dive **confirms** the v4 plan's architecture and surfaces a few
optional refinements:

### Confirmed correct in v4

- **Slash command (Mechanism 5) for the user-facing UX.** Slash commands are
  invisible to the LLM and run deterministically — exactly what we want for
  `/task`, `/create-role`, `/role-setup`, `/project-onboarding`.
- **MCP server (Mechanism 2) for agentic invocation.** Agent-driven calls go
  through the LLM's normal tool catalog; the OpenTeam server is just another
  MCP entry. v4 wraps each of the 4 OpenTeam tools as a typed Python function
  in `mcp_server/server.py`.
- **Subprocess for the slash path** — avoids LLM nondeterminism and the 295 s
  MCP timeout. Verified.

### Optional refinements to consider for v5 (small, principled)

1. **Bundle a Subagent definition for OpenTeam.** Ship
   `~/.rovodev/subagents/openteam-orchestrator.md` so the *parent* RovoDev can
   delegate complex multi-step OpenTeam workflows to a focused subagent that
   knows when to call `mcp__openteam__openteam_task` vs `…create_role` vs
   `…role_setup`. Frontmatter restricts it to the 4 OpenTeam MCP tools so the
   subagent stays on-topic.

2. **Bundle a Skill (Mechanism 3) — already in v4 §3.9.** Confirmed: this is
   the right mechanism for "when should the agent reach for OpenTeam?" The
   skill's body becomes injected only when the LLM calls `get_skill("openteam")`.

3. **Think twice about advertising slash commands inside the SKILL.md.** Slash
   commands are user-only. If the SKILL.md tells the LLM "use /task", the LLM
   will try to *emit* `/task` as text, which won't trigger the slash handler
   (because that's TUI-only input parsing). The skill should tell the LLM to
   call the **MCP tool** (`mcp__openteam__openteam_task`), and tell the
   **user** to use the slash command. v4's SKILL.md correctly distinguishes
   these — leave as-is.

4. **MCP tool description should mention the 295s timeout** so the LLM knows
   to keep MCP-driven `task` calls short and to *suggest the user use /task*
   for long jobs. v4 does this in the `openteam_task` docstring — leave as-is.

5. **`invoke_subagents` permission default.** Per the release notes,
   `invoke_subagents` now respects the standard permissions config. If we ship
   `openteam-orchestrator`, document that it inherits the default permission
   bucket; users who want auto-approve can add it to their allowlist.

### What v4 does NOT need based on this dive

- ❌ A `code-nautilus`-style first-party tool registration. We are not
  introducing OpenTeam tools as built-ins; the MCP path is the right plane.
- ❌ A custom `pydantic-ai` agent. We do not need to author an `AgentDefinition`
  inside acra-python — the OpenTeam wrappers are just MCP tools the existing
  agent catalog absorbs.

---

## 8. The "single-page comparison matrix"

```
                    │ First-party │ MCP        │ Skill        │ Subagent      │ Slash
────────────────────┼─────────────┼────────────┼──────────────┼───────────────┼──────────────
Where defined       │ tools/*.py  │ MCP server │ SKILL.md     │ subagents/*.md│ slash_commands/*.py
Loaded by           │ get_tool()  │ mcp_utils  │ skill walker │ subagent      │ command_registry
                    │             │            │              │ walker        │ .register
Initiated by        │ LLM         │ LLM        │ LLM          │ LLM           │ USER (TUI)
Process boundary    │ in-proc     │ subprocess │ in-proc      │ in-proc       │ in-proc
                    │             │ (per srvr) │              │ (Agent fork)  │
Has its own Agent?  │ no          │ no         │ no           │ YES           │ no
Conversation        │ shared      │ shared     │ shared       │ FRESH         │ N/A
LLM tool catalog    │ 1 entry     │ 2 entries  │ 1 generic    │ 1 generic     │ 0 entries
                    │ per fn      │ per server │ (get_skill)  │ (invoke_      │ (invisible)
                    │             │            │              │  subagents)   │
Permission gate     │ PauseOn     │ PauseOn    │ none         │ PauseOn       │ none
                    │ ToolCalls   │ ToolCalls  │              │ ToolCalls     │
Concurrency         │ serial      │ serial     │ serial       │ ≤4 parallel   │ serial
Best for            │ filesystem, │ external   │ playbook /   │ decomposing   │ deterministic
                    │ shell,      │ APIs,      │ guide for a  │ a problem     │ user shortcuts
                    │ search      │ other-     │ class of     │ into focused  │
                    │             │ language   │ tasks        │ sub-tasks     │
                    │             │ tools      │              │               │
```

---

## 9. Suggested next reads

- `code-nemo/src/nemo/core/agent_definition.py` lines **521-680** (subagent
  dispatch) and **933-960** (`SubagentDefinition`) — the canonical
  implementation.
- `cli-rovodev/src/rovodev/modules/subagents.py` — the loader and the
  interactive TUI for creating/editing subagents.
- `cli-rovodev/docs/rovodev-cli/content/platform/rovodev-cli/subagents.md` —
  user-facing docs.
- `cli-rovodev/docs/rovodev-cli/content/platform/rovodev-cli/permissions.md` —
  how `invoke_subagents` is permission-gated.
- `cli-rovodev-tui/src/rovodev_tui/widgets/tool_call/invoke_subagents.py` —
  the TUI rendering of subagent results (the indented "ENTRY:" panels).
