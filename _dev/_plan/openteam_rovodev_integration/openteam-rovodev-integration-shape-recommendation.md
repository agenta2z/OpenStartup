# Should OpenTeam Be a Plugin, Subagent, Tool, Sidecar, or Service?
## Systematic Recommendation Brief

**Date:** 2026-05-08 10:04
**Author:** Rovo Dev (code-grounded analysis)
**Companion to:** `openteam-rovodev-integration-INTEGRATED-v4.md`,
`rovodev-tools-and-subagents-deep-dive.md`,
`rovodev-plugins-and-extensions-deep-dive.md`
**Question being answered:** *"OpenTeam has its own orchestration (PTI / BTA / Multiflow / Dual / prompt rendering / variable manager / template spaces). Given that, do we let OpenTeam be a plugin, an extension, a subagent, just expose its tools, or something else? How do we integrate the orchestration features without losing them?"*

---

## 0. The headline answer

> **Recommendation: Tool-exposure (MCP) + thin user UX (Slash) + opt-in observability (Event Hooks) — exactly the v4 plan. Do NOT try to make OpenTeam "a plugin", "a subagent", or "an extension" of RovoDev.**
>
> **Why:** OpenTeam is a *peer orchestration runtime* with five non-trivial subsystems (inferencer tree, prompt-template hierarchy, variable manager, workspace lifecycle, dual/review consensus loops) that **cannot be cleanly absorbed into RovoDev's pydantic-ai-based agent loop**. The two systems are best modelled as **two equal orchestrators**: RovoDev orchestrates conversational LLM workflows; OpenTeam orchestrates structured multi-stage agent topologies. They communicate via a **narrow, well-typed interface** — MCP tool calls — and *neither's internal model leaks into the other*.
>
> **The "subagent" idea is tempting but wrong:** RovoDev subagents are in-process pydantic-ai Agent forks; OpenTeam topologies are not pydantic-ai Agents at all. Forcing OpenTeam through that lens would either (a) reimplement its inferencer stack as pydantic-ai callbacks (months of work, no benefit), or (b) reduce OpenTeam to a single tool call (which is what MCP already does, much more elegantly).

---

## 1. The two orchestration models, side by side

### 1.1 RovoDev's orchestration model

```
                       ┌───────────── RovoDev ─────────────┐
                       │                                   │
  user prompt ───▶ pydantic-ai Agent loop                  │
                       │  ↓                                │
                       │  LLM stream (token-by-token)      │
                       │  ↓                                │
                       │  tool_use detected                │
                       │  ↓                                │
                       │  dispatch: first-party / MCP /    │
                       │            skill / subagent       │
                       │            └─ subagent = forked   │
                       │               in-proc Agent w/    │
                       │               fresh history       │
                       │                                   │
                       └───────────────────────────────────┘
```

**Hallmarks:**
- One LLM stream → one tool decision → one tool result → continue.
- Single conversation history; everything is a turn.
- pydantic-ai is the runtime substrate.
- Extension points are *narrow and uniform*: anything you add is a tool the LLM calls or a skill it consults.

### 1.2 OpenTeam's orchestration model

```
                  ┌────────────── OpenTeam topology ──────────────┐
                  │                                               │
  task (request)──▶ Outer Dual                                    │
                  │  ├── base: PTI (Plan-then-Implement)          │
                  │  │   ├── planner: Dual                        │
                  │  │   │   ├── base: BTA (Breakdown-then-Agg)   │
                  │  │   │   │   ├── breakdown: leaf inferencer   │
                  │  │   │   │   ├── workers: MultiFlowDual       │
                  │  │   │   │   │   └── 2 flows × N subtasks     │
                  │  │   │   │   │       (each flow sees peers)   │
                  │  │   │   │   └── aggregator: leaf             │
                  │  │   │   ├── reviewer: leaf                   │
                  │  │   │   └── fixer: leaf                      │
                  │  │   └── executor: BTA{Dual workers}          │
                  │  ├── reviewer: leaf                           │
                  │  └── fixer: PTI deep-copy of base             │
                  │                                               │
                  │   Each leaf delegates to:                     │
                  │     • ConversationalInferencer (own LLM loop) │
                  │     • RovoChatInferencer (HTTP)               │
                  │     • RovoDevCliInferencer (subprocess)       │
                  │                                               │
                  └───────────────────────────────────────────────┘
                       ↓
                  Workspace artifacts (final_deliverables/, plan.md, impl.md, …)
```

**Hallmarks:**
- A *tree of inferencers* (composed declaratively in YAML topologies).
- Each non-leaf node has its own role (plan / implement / breakdown / aggregate / review / fix).
- Each node has its own template space (`plan/`, `implementation/`, `breakdown/`) with Jinja2 templates rendered against a `FileBasedVariableManager` from RichPythonUtils.
- Workspace lifecycle: each invocation creates `.openteam_runs/<id>/` with `children/`, `artifacts/`, `final_deliverables/`.
- Multi-LLM, multi-prompt, multi-pass — "review and fix" loops, "propose and consensus" loops.
- Concurrency via WorkGraph; checkpoint/resume.

### 1.3 Why these don't merge cleanly

| Dimension | RovoDev | OpenTeam | Merge cost |
|---|---|---|---|
| Substrate | pydantic-ai | bespoke `InferencerBase` + `WorkGraph` | Reimplement OpenTeam against pydantic-ai → months |
| Conversation model | one history per session | one fresh conversation per leaf inferencer × N leaves | Conceptual mismatch |
| Prompt rendering | string interpolation in tool defs | Jinja2 + variable manager + template spaces + alias resolution | RovoDev would need to import `FileBasedVariableManager` from RichPythonUtils |
| Tool model | pydantic-ai `Tool` (function w/ JSON schema) | dataclass `ConversationTool` + topology nodes | Disjoint |
| Concurrency | sequential turns + ≤4 subagent fan-out | DAG via WorkGraph | Disjoint |
| Workspace | session log + artifact dir per session | nested per-node workspace tree | Disjoint |
| Failure model | tool error → ModelRetry; subagent error → ModelRetry | per-node review/fix loops with severity thresholds | Disjoint |

**Bottom line: these are two coherent orchestration systems. Joining them at the substrate level is a bad bet. Joining them at the *tool boundary* is correct.**

---

## 2. The 5 candidate integration shapes — evaluated

### Shape A — *"OpenTeam as a plugin"* (e.g., setuptools entry-point that registers itself with RovoDev)

**Verdict: ❌ Not viable.**

- **Hard fact:** RovoDev has no plugin discovery mechanism. Verified in the previous deep dive: zero `[project.entry-points]` blocks, zero `importlib.metadata.entry_points()` calls, zero `pkgutil.iter_modules`.
- Even if we built one (4-line PR to acra-python), OpenTeam wouldn't gain anything — its inferencer tree would still need to either run in-process (Shape D) or out-of-process (Shape E).
- "Plugin" only buys you discovery; it doesn't solve the orchestration-model mismatch.

### Shape B — *"OpenTeam as a subagent"* (`~/.rovodev/subagents/openteam.md`)

**Verdict: ❌ Wrong abstraction.**

- A RovoDev subagent IS a forked in-process pydantic-ai Agent. OpenTeam topologies are not pydantic-ai Agents — they are a tree of inferencers driven by a `WorkGraph`. Shoehorning OpenTeam into a subagent file would mean: write a subagent system prompt that tells the LLM "call `mcp__openteam__openteam_task`" — which is just a more verbose version of Shape C with extra LLM round-trips.
- *However*, a subagent named `openteam-orchestrator` whose JOB is to *decide which* OpenTeam tool to call is genuinely useful as a **complement** to Shape C, not a replacement (see §4 "Optional refinements").

### Shape C — *"OpenTeam tools exposed via MCP + slash + skill"* (the v4 plan)

**Verdict: ✅ Correct architecture.**

- Each top-level OpenTeam capability (`task`, `create_role`, `role_setup`, `project_onboarding`) becomes one MCP tool.
- The MCP wrapper calls `executor.execute(args, ctx)` directly. **The full inferencer tree, prompt rendering, variable manager, workspace lifecycle — all of it runs unchanged inside the MCP server subprocess.** RovoDev sees only "I called a tool, I got a string back".
- Slash command (`/task`) gives users deterministic UX without LLM round-trip.
- Skill (`SKILL.md`) tells the agent when to reach for which tool.
- **Critically: nothing about OpenTeam's orchestration is lost.** The agent calling `mcp__openteam__openteam_task("design a microservice")` triggers the *full* `breakdown_multiflow_plan_then_implement` topology — Plan/Dual/BTA/MultiFlow/Implement/Review/Fix all run inside OpenTeam's runtime.

This is precisely what v4 ships. The deep-dives only **confirm** it.

### Shape D — *"OpenTeam orchestration as an in-process library RovoDev calls directly"*

**Verdict: ❌ Infeasible without major refactor.**

Verified blockers from the agent investigation:

1. **`JinjaPromptRenderer` requires `rich_python_utils.FileBasedVariableManager`** — imported at `prompt_rendering.py:120`. RovoDev would need to install RichPythonUtils into its venv (drag-in transitive deps).
2. **Topology YAML loading requires `OmegaConf` + custom `_import_` resolver** — OpenTeam's bespoke config layer.
3. **Workspace lifecycle assumes OpenTeam directory conventions** (`server/_runtime/tasks/<id>/...`).
4. **Inferencer tree assumes `WorkGraph` runtime** for DAG execution.
5. **Some inferencers are themselves `RovoDevCliInferencer` / `RovoChatInferencer`** that subprocess-out to other services — so even "in-process" would still spawn subprocesses.

The cost is real (weeks of plumbing) and the benefit is illusory — once you've installed RichPythonUtils + AgentFoundation + OpenTeam into RovoDev's venv, you've effectively built Shape C minus the clean process boundary. Process isolation is a *feature* here, not a cost.

### Shape E — *"OpenTeam as a long-lived sidecar service (HTTP/WebSocket)"*

**Verdict: ⚠️ Acceptable but worse than Shape C for our use case.**

- Run `python -m openteam.server.main` (the FastAPI app) as a long-lived sidecar; RovoDev calls REST endpoints.
- **Wins:** state preserved across calls, OpenTeam's existing UI works, real-time SSE streaming.
- **Losses:** more moving parts (port management, lifecycle, auth), slower cold-start than Shape C (we'd want it *always* running), opaque to MCP `/mcp` listing (RovoDev wouldn't know what tools the sidecar offers).
- **Use case:** users who already run OpenTeam's UI for other reasons. Add as a Phase 7B-style optional in v4; do not make it the default.

---

## 3. Mapping each OpenTeam capability to the right RovoDev mechanism

| OpenTeam capability | Best RovoDev mechanism | Rationale |
|---|---|---|
| Run a `task` topology (the whole BTA/MultiFlow/PTI/Dual cascade) | **MCP tool** (`mcp__openteam__openteam_task`) | Agent-initiated, single tool call → entire topology runs inside MCP subprocess |
| User wants to manually fire a task without LLM round-trip | **Slash command** (`/task`) → subprocess to standalone CLI | Deterministic, real-time stdout streaming, no 295s MCP timeout |
| Agent needs to know "when should I use OpenTeam?" | **Skill** (`~/.rovodev/skills/openteam/SKILL.md`) | Lazy guidance loaded only when LLM calls `get_skill("openteam")` |
| Decompose a complex multi-step OpenTeam workflow into focused sub-tasks | **Subagent** (`~/.rovodev/subagents/openteam-orchestrator.md`) — *optional v5* | One "OpenTeam-savvy" subagent that knows which OpenTeam tool to call when |
| React to RovoDev session events (e.g. auto-resume long task on session end) | **Event Hook** (`~/.rovodev/config.yml` `eventHooks:`) — *optional Phase 5.5* | Shell command driven; no acra-python changes |
| OpenTeam's inferencers themselves call RovoDev as a leaf | **`RovoDevCliInferencer` (existing)** spawns RovoDev subprocess | Already works; no integration needed |
| Long-running task progress streamed to TUI | **Slash command** stream + opt-in **Event Hook** notify | MCP timeout precludes this for agentic; slash works perfectly |
| Cross-product orchestration: RovoDev decides → OpenTeam executes → result fed back | **MCP tool call return** | Already what Shape C delivers |
| OpenTeam UI for visualizing topology runs | **Sidecar (Shape E) — optional** | Run `openteam.server.main` if user wants the UI; orthogonal to MCP/slash |

**Key insight:** every OpenTeam capability has a clean, idiomatic RovoDev mechanism. The mapping is bijective and lossless.

---

## 4. Recommended integration architecture (final)

```
┌─────────────────────────────── RovoDev TUI ──────────────────────────────┐
│                                                                          │
│   user types /task "design X"                                            │
│         │                                                                │
│         ▼                                                                │
│   slash handler ── subprocess ──▶ python -m openteam.server.resources    │
│                                              .tools.task                 │
│                                                                          │
│   LLM agent decides "I need OpenTeam"                                    │
│         │                                                                │
│         ▼                                                                │
│   MCP call: mcp__openteam__openteam_task                                 │
│         │                                                                │
│         ▼                                                                │
│   ──▶ stdio MCP subprocess: openteam-mcp run ──▶ executor.execute()      │
│                                                       │                  │
│                                                       ▼                  │
│   (optional) subagent "openteam-orchestrator"     ┌──────────────────┐   │
│              decides which OpenTeam tool to call  │ OpenTeam runtime │   │
│                                                   │  • inferencer    │   │
│   (optional) Event Hooks observe lifecycle:       │    tree (PTI/BTA)│   │
│              on_complete → notify                 │  • prompt        │   │
│              on_session_end → save resume token   │    rendering     │   │
│                                                   │  • variable mgr  │   │
│                                                   │  • workspace     │   │
│                                                   │  • Dual/Review   │   │
│                                                   └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Composition:**
- **Mandatory (v4 ships these):**
  - Mechanism 2 (MCP) — `openteam/mcp_server/` exposing 4 tools
  - Mechanism 5 (Slash) — `slash_commands/openteam.py` with subprocess dispatch
  - Mechanism 3 (Skill) — `SKILL.md` with usage guidance
  - Phase 0 (`tool_cli.py` rendering fix) prerequisite
- **Optional refinements (post-v4, additive):**
  - Mechanism 4 (Subagent) — `openteam-orchestrator.md` for multi-step OpenTeam choreography
  - Mechanism 6 (Event Hooks) — `eventHooks:` YAML templates for lifecycle reactivity
  - Shape E (Sidecar) — only for users who want the OpenTeam UI

**Rejected:**
- Shape A (Plugin) — no discovery in RovoDev
- Shape B (OpenTeam-as-subagent) — wrong abstraction
- Shape D (in-process library) — drags transitive deps; loses isolation
- Mechanism 1 (first-party tool) — would require forking acra-python

---

## 5. Critical principle: "tool boundary, not substrate boundary"

Two systems with their own orchestration models should communicate **through tool calls**, not by embedding one inside the other. This is the same reason:
- VSCode talks to language servers via LSP, not by importing them as Python modules.
- A web browser talks to a JS engine via the DOM API, not by linking V8 into the renderer.
- An IDE talks to a compiler via stdin/stdout, not by linking GCC.

In our case:
- **RovoDev** = the editor / shell that drives a conversation and chooses tools.
- **OpenTeam** = the compiler / engine that executes structured multi-stage workflows.

The MCP protocol (FastMCP, JSON-RPC over stdio) is exactly LSP-shaped: typed tool surface, narrow contract, language-agnostic, process-isolated.

**Concrete benefits of this discipline:**

1. **Either side can be rewritten.** OpenTeam could swap pydantic-ai for LangGraph; RovoDev could swap pydantic-ai for nothing-of-the-sort. Neither breaks the other.
2. **Independent dependency graphs.** RovoDev's pinned `pydantic-ai==X.Y` can't conflict with OpenTeam's pinned `omegaconf==Z`.
3. **Independent failure domains.** An OpenTeam crash doesn't kill RovoDev's session; a RovoDev TUI bug doesn't lose an OpenTeam workspace.
4. **Independent upgrade cadences.** v4 doesn't pin OpenTeam to a specific RovoDev version.
5. **Same boundary works for both directions.** Tomorrow, if OpenTeam wants to invoke RovoDev (it already does via `RovoDevCliInferencer` subprocess), the mechanism is symmetrical.

This is *the* principled answer to "how to integrate two orchestrators".

---

## 6. What about losing OpenTeam's "magic" inside RovoDev?

A reasonable concern: *"if RovoDev only sees `openteam_task` as one tool that returns a string, doesn't it lose visibility into the cool BTA/MultiFlow/Dual stuff happening inside?"*

**Answer: it doesn't have to.** Several existing OpenTeam features make the orchestration *visible* without leaking it:

1. **`ToolExecutionResult.context_updates`** carries `workspace_path`, `plan_path`, `impl_path`, `role_document_path`, `report_path` etc. v4's `_render_result` surfaces these to RovoDev as a footer like:
   ```
   Artifacts:
     workspace_path: .openteam_runs/task_a3f2/
     plan_path: .openteam_runs/task_a3f2/plan.md
     impl_path: .openteam_runs/task_a3f2/impl.md
   ```
   The user (and the agent) can then `open_files(...)` to inspect each stage's output.

2. **OpenTeam's workspace tree** (`children/`, `final_deliverables/`) is fully browsable post-hoc — same as `git log` for a long branch operation.

3. **`task --plan` mode** runs only the planning stages, returns an editable plan, and lets the user feed it back via `task --execute --resume <id>`. This is OpenTeam's native solution to "I want to see what BTA/Multi-Flow proposed before committing to implementation".

4. **Sidecar (Shape E) UI** is the high-touch option for users who want real-time topology visualization. Orthogonal to the MCP tool surface.

5. **Event Hooks (Mechanism 6)** can stream OpenTeam stage transitions into RovoDev's event log if OpenTeam emits structured events (it already does via its `WebSocketInteractive` channel; we'd ship a hook that subscribes).

**So: nothing is hidden, nothing is lost. The orchestration runs at full fidelity inside OpenTeam; RovoDev gets a clean tool result + a paper trail of artifacts.**

---

## 7. Self-audit (stress-tested)

| Question | Answer |
|---|---|
| Does the MCP path expose the full BTA/MultiFlow/Dual cascade? | **Yes.** The MCP wrapper calls `executor.execute(args, ctx)` which calls `_run_topology(...)` which loads the YAML topology and runs the full inferencer tree. Verified by reading the test `test_real_dual_outside_bta_pti_mfdual_dual`. |
| Could the agent get stuck waiting on a 30-min task via MCP? | **Yes** — that's why the slash command exists. Documented in v4 SKILL.md: "for long jobs, prefer the slash command". |
| Can the agent compose multiple OpenTeam tool calls in a conversation? | **Yes.** `create_role` → then `role_setup` → then `task --request "implement role X"` is just three tool calls in one agent loop. The optional `openteam-orchestrator` subagent makes this idiomatic. |
| Does this approach scale to OpenTeam adding new tools? | **Yes.** Each new `tool.json` adds a corresponding wrapper to `_TOOL_SPECS` in `mcp_server/server.py`. The CI preflight ensures wrappers stay aligned with `tool.json`. |
| What if OpenTeam wants to call RovoDev *inside* a topology? | **Already works.** `RovoDevCliInferencer` subprocesses out to RovoDev. The tool boundary is symmetrical. |
| What if we later want a single unified UI? | **Sidecar (Shape E) covers this.** Run `openteam.server.main` as a long-lived sidecar; OpenTeam's React SPA + RovoDev TUI side-by-side. Phase 8-style optional. |
| Does this commit us to a specific OpenTeam version? | **No.** The MCP tool contract is the only API surface; OpenTeam internals can change freely. |
| Is there a "leaky abstraction" risk where OpenTeam internals show up in RovoDev errors? | **Mostly no.** `_render_result` catches exceptions inside `executor.execute` and surfaces them as text. Topology-internal errors (e.g. a Dual reviewer rejecting 3 times) become part of the returned string. We could add an explicit error-class wrapping in v5 if it matters. |
| Could we ever need Shape D (in-process library)? | **Unlikely.** The only scenario is "we want OpenTeam to share memory with RovoDev's pydantic-ai context" — which doesn't help because pydantic-ai context is conversational and OpenTeam's context is per-stage. There's nothing meaningful to share. |
| What if the user wants `/task` to delegate to a *specific* topology? | **Already supported.** `/task --agent-config <yaml-name> "request"`. The CLI parses and forwards. |

---

## 8. The 1-page comparison: 5 integration shapes

```
                  │ A. Plugin   │ B. Subagent │ C. MCP+Slash │ D. In-proc   │ E. Sidecar
                  │ (entry-pts) │ (.md file)  │   +Skill     │   library    │  (HTTP)
──────────────────┼─────────────┼─────────────┼──────────────┼──────────────┼─────────────
Discovery cost    │ HIGH (PR    │ ZERO        │ ZERO         │ ZERO         │ MEDIUM
                  │  acra-pyth.)│             │              │              │ (port mgmt)
Process model     │ in-proc     │ in-proc     │ subprocess   │ in-proc      │ subprocess
                  │ (somehow)   │ Agent fork  │              │              │ (long-lived)
Reuses OpenTeam   │ YES         │ NO (must    │ YES (full    │ YES (must    │ YES
orchestration?    │             │  reimpl as  │  fidelity)   │  install     │
                  │             │  prompts)   │              │  RPU+AF)     │
Dep coupling      │ NONE        │ NONE        │ NONE         │ HIGH         │ NONE
                  │             │             │              │ (drags RPU,  │
                  │             │             │              │  AF, etc.)   │
Failure isolation │ low         │ medium      │ HIGH         │ low          │ HIGH
LLM-visible       │ depends     │ generic     │ 4 named MCP  │ 4 named MCP  │ via MCP
                  │             │ subagent    │ tools        │ tools        │
User-visible      │ depends     │ no          │ /slash + UI  │ /slash       │ webapp
Agentic tool calls│ depends     │ via 1 tool  │ ✅ direct    │ ✅ direct    │ via REST
Streaming         │ depends     │ summary     │ MCP partial  │ partial      │ ✅ SSE
                  │             │ string      │ + slash full │              │
Long-running OK   │ depends     │ no (295s)   │ ✅ slash     │ ✅           │ ✅
Status            │ ❌ rejected │ ❌ wrong    │ ✅ RECOMMEND │ ❌ rejected  │ ⚠️ optional
                  │ (no infra)  │ abstraction │              │ (cost>>      │ (Phase 8)
                  │             │             │              │  benefit)    │
```

---

## 9. The pick-one answer

> *"If we only pick one integration shape, which would you choose?"*

**Shape C — MCP tool exposure + thin slash UX + skill — i.e., the v4 plan.**

Three independently-verified reasons:

1. **It is the only shape that preserves OpenTeam's orchestration at full fidelity** while keeping the RovoDev-facing surface narrow and typed. Every other shape either (a) loses OpenTeam features (B, partial-A), (b) demands large up-front infrastructure work (A, D), or (c) is overkill for the use case (E).

2. **It is the only shape that respects both systems' substrates.** RovoDev keeps its pydantic-ai-based agent loop unchanged. OpenTeam keeps its bespoke inferencer tree + WorkGraph + variable manager unchanged. The boundary is a typed tool call — the same boundary we'd use to integrate any peer system.

3. **It composes with the others.** v4-Shape-C does not preclude later adding Shape B as an `openteam-orchestrator` subagent (Mechanism 4), Mechanism 6 Event Hooks for lifecycle reactivity, or Shape E sidecar for the OpenTeam UI. It is the *foundation* on which optional refinements stack.

**The optional add-ons (in priority order, post-v4):**
- Phase 5.5 — Event Hook templates (½ day; user-facing config; zero code changes)
- Optional v5 — `openteam-orchestrator` subagent (½ day; one .md file; gives the agent a "router" persona that knows when to call which OpenTeam tool)
- Phase 7B — In-memory `FastMCPTransport` (raises MCP timeout from 295s → 1800s for agentic invocation of long tasks)
- Phase 8 — Sidecar HTTP mode for users who want OpenTeam's React UI side-by-side

---

## 10. Concrete next steps (no new plans needed; v4 stands)

1. **Land Phase 0** of v4: `tool_cli.py` rendering fix + tests + flip 3 `slash_enabled: true` flags. (~30 min)
2. **Scaffold Phase 1**: `src/openteam/mcp_server/` with the 4 hand-written wrappers + root `pyproject.toml`. (~½–1 day)
3. **Phases 2A/2B in parallel**: register MCP in `~/.rovodev/mcp.json`; ship `slash_commands/openteam.py` + 4-line app.py patch. (~½ day each)
4. **Phase 4**: write `SKILL.md` distinguishing slash (user) from MCP (agent). (~½ day)
5. **Phase 5.5** (optional, post-ship): `OpenStartup/_dev/templates/rovodev_event_hooks.yaml` with the 3 hook examples (recovery, notify, safety).
6. **Optional v5** (post-ship): `~/.rovodev/subagents/openteam-orchestrator.md`.

Total time to a working `/task <prompt>` in RovoDev with full OpenTeam orchestration behind it: **~1.5 days** of focused work.

---

## 11. Summary in one paragraph

OpenTeam is not a plugin, not a subagent, not an extension — it's a **peer orchestrator** with its own coherent runtime (inferencer tree, prompt rendering, variable manager, workspace lifecycle, dual/review consensus). The right integration is to expose its top-level capabilities as **typed MCP tools** (so the agent can call them like any other tool), wrap each with a **slash command** (so the user gets deterministic UX without LLM round-trip), and ship a **skill** that teaches the agent when to reach for them. This is exactly the v4 plan; it preserves 100% of OpenTeam's orchestration fidelity while keeping RovoDev's pydantic-ai loop completely untouched. Optional refinements (Event Hooks for lifecycle reactivity, an `openteam-orchestrator` subagent for choreography, a sidecar mode for the OpenTeam UI) stack additively on top of this foundation. The principle is the same as VSCode↔language-server, browser↔JS-engine, IDE↔compiler: **two systems with their own orchestration models communicate through a narrow typed tool boundary, not by embedding one inside the other.**
