# Multi-Workflow Conversational Inferencer — Architecture & Implementation Plan

> **Goal:** Evolve the conversational inferencer from a **single, fixed, always-on workflow** model into a **first-class multi-workflow** model where workflows are *parallel peers to skills and tools*: discoverable in the prompt, enterable/exitable on demand, individually stateful, identifiable by an instance ID, and resumable from where they were paused.

---

## 0. TL;DR — What This Plan Delivers

| Today | After This Plan |
|---|---|
| One implicit workflow per session, loaded from a single SOP file | A **WorkflowRegistry** of named workflow definitions, peer to tools/skills |
| `prior_context` carries the only workflow state | `prior_context.active_workflow_id` + `WorkflowInstance[]` collection |
| Workflow context always shown in prompt | Active workflow context shown only when one is **entered** |
| No way to pause / hand off / resume | Workflows are **stateful instances** with IDs that can suspend & resume |
| `workflow_description` injected via `_variables/workflow_description/default.jinja2` | Catalog of workflows + ongoing instances always shown; full SOP only when an instance is "in focus" |
| Tools and SOP phases tightly coupled (`tool_phase_map`) | Tools remain global; **workflow membership is a runtime fact** of the active instance |

---

## 1. Background & Investigation Findings (Concise)

### 1.1 What the SOP file is today

`_variables/workflow/sop.jinja2` is a **markdown SOP** template (loaded by `find_sop_file()` on the prompt renderer). At each prompt render, the conversational inferencer (`agent_foundation/.../conversational_inferencer.py:_render_prompt` lines 567–728) does:

1. Calls `prompt_renderer.find_sop_file()` → resolves the SOP path.
2. `SOPManager.load(sop_path)` parses the SOP markdown into a `SOP` object (a `StateGraph` subclass) with **phases**, **directives**, **subsections** (Tools, Outputs, etc.), and a **`tool_to_phase_map`**.
3. Stores `_sop` and `tool_phase_map` into `prior_context`.
4. Builds a `StateGraphTracker(graph=sop, current_state=…, completed_states=…, state_outputs=…, goto_counts=…)` from `prior_context`.
5. Calls `SOPManager.render_guidance(tracker, sop, context=prior_context)` → produces the string for `workflow_nextstep_guidance`.
6. Feeds these into the Jinja2 template (`initial.jinja2`):
   - `workflow_description` (from `_variables/workflow_description/default.jinja2`)
   - `workflow_status` (from `WorkflowContext.to_status_text()`, see `agent_foundation/server/workflow_context.py:355`)
   - `workflow_nextstep_guidance` (from `SOPManager.render_guidance`)

### 1.2 What `WorkflowContext` carries today

`agent_foundation/server/workflow_context.py:84` — single dataclass per session:
- `strategy`, `workflow_description`
- `current_phase`, `phase_status`, `completed_phases[]`, `phase_outputs{}`
- `task_queue[]`, `active_multi_task_id`, `closed_multi_task_ids{}`
- `tool_phase_map{}`, `state_tracker`

It is persisted in `session["workflow_context"]` (`session_store.py:231 update_workflow_context`) and converted to/from `prior_context` each turn (`conversation_service.py:_compute_session_context`, `_persist_workflow_updates`).

### 1.3 Hard-coded "one workflow" assumptions

| Location | Assumption |
|---|---|
| `session_store.py:158-201, 458-471` | Session has a single `workflow_context` dict |
| `conversation_service.py:352-378` | `_compute_session_context` reads `session["workflow_context"]` (scalar) |
| `conversation_service.py:392-423` | `_persist_workflow_updates` writes back to one slot |
| `conversation_service.py:220-258` | Inferencer cached by `session_id` only |
| `_render_prompt` (AgentFoundation) | One `find_sop_file()` call per render → one SOP, one tracker |
| `initial.jinja2:6-23` | Workflow block always shown if `workflow_description` is set |
| `_load_workflow_description()` | Hard-coded path to `default.jinja2` |
| Tool→phase map | One global map per inferencer (`prior_context["tool_phase_map"]`) |

### 1.4 Skills and Tools today (the analog model)

- **Tools**: `openteam/.../tools/<name>/tool.json` discovered by `ToolDispatcher`; rendered via `ToolMarkdownFormatter.format_all()` into `{{ action_tools }}` and `{{ conversation_tools }}`.
- **Skills**: `openteam/.../skills/<name>/SKILL.md` — markdown grouping doc with frontmatter; primarily metadata (no executor).
- They are surfaced in the prompt as **catalogs** and selected by the LLM at will.

This is the model we will mirror for **workflows**.

---

## 2. Conceptual Model — Workflows as Peers to Tools/Skills

### 2.1 Three resource families in the prompt

```
                ┌──────── Resources advertised in every prompt ────────┐
                │                                                       │
   Tools  ──►   Atomic, stateless, single-call units                    │
   Skills ──►   Reusable how-to docs / playbooks (no execution)         │
   Workflows ► Stateful, multi-step orchestrations (NEW peer)           │
```

A **workflow** is:
- **Defined** by a `workflow.yaml` + an `sop.md` (the existing SOP file format works).
- **Discoverable** via a `WorkflowRegistry`, exactly like tools.
- **Instantiable**: each entry creates a `WorkflowInstance(workflow_id=…, definition_name=…, state=…, …)`.
- **Stateful**: holds `current_phase`, `phase_status`, `phase_outputs`, `completed_phases`, `goto_counts`, custom data.
- **Suspendable / resumable** via its `workflow_id`.
- **Peer-callable**: the LLM "enters" or "exits" workflows like calling a tool — through new conversation control tools (`enter_workflow`, `exit_workflow`, `resume_workflow`, `complete_workflow`, `abort_workflow`).

### 2.2 Workflow lifecycle (state machine)

```
                          ┌──────────────────────┐
   list_workflows()       │                      │
   (always in prompt) ──► │     "available"      │  Definitions known by the registry
                          └──────────┬───────────┘
                                     │ enter_workflow(name=…, args=…)
                                     ▼
                          ┌──────────────────────┐
                          │      "active"        │  Has unique workflow_id, prompt shows
                          │  (in focus)          │  full SOP/status/guidance for THIS instance
                          └──────────┬───────────┘
                  exit_workflow()    │     complete_workflow()
                  (suspend)          │      (terminal)
                                     ▼
                          ┌──────────────────────┐         ┌────────────────┐
                          │     "suspended"      │ ──────► │   "completed"  │
                          │  (kept in           │         └────────────────┘
                          │   prompt as         │
                          │   "ongoing")         │            "aborted" similar terminal state
                          └──────────┬───────────┘
                                     │ resume_workflow(workflow_id=…)
                                     ▼
                                  "active"
```

Critical property: a session may have **at most one active workflow at a time** (single focus), but **multiple suspended workflows** that can be resumed.

> **Why single-active?** The current `workflow_status` / `workflow_nextstep_guidance` block is designed to nudge the model toward one focused state machine. Trying to render N concurrent state machines into the prompt is feasible but **destroys the "next step" focusing benefit**. Multi-instance is supported through suspend/resume, not concurrent in-prompt focus. (Open question: see §8.)

### 2.3 Prompt anatomy (after change)

```
## Workflow Catalog                  ← always present (NEW; analogous to ## Available Tools)
   - role_creation: Enterprise role research and synthesis
   - role_setup: Decompose role into skills/tools
   - team_onboard: Specialize a role for a team
   ...
## Ongoing Workflows                  ← always present when any suspended (NEW)
   - workflow_id=wf_a3f1 / role_setup
       paused at Phase 2 (research_plan complete; awaiting confirmation)
       resume with: resume_workflow(workflow_id="wf_a3f1")
   - workflow_id=wf_b912 / team_onboard ...
## Active Workflow                    ← present ONLY when one is active (CURRENT BEHAVIOR, scoped)
   <WorkflowDescription>...full SOP body...</WorkflowDescription>
   <WorkflowStatus>...phase tracker...</WorkflowStatus>
   <WorkflowNextStepGuidance>...</WorkflowNextStepGuidance>
## Available Tools                    ← unchanged (Action + Conversation)
## Conversation                       ← unchanged
## Decision Procedure                 ← extended: choose to enter/exit/resume workflow
## Response Format                    ← unchanged
```

When NO workflow is active, the entire `## Active Workflow` block disappears — the agent is free-form, and only sees the catalog + ongoing list.

---

## 3. New Data Model

### 3.1 `WorkflowDefinition` (registry entry — static)

```python
# agent_foundation/server/workflows/definition.py  (NEW)
@dataclass(frozen=True)
class WorkflowDefinition:
    name: str                       # unique key, e.g. "role_setup"
    display_name: str
    summary: str                    # one-line description shown in catalog
    description: str                # multi-line markdown (== old workflow_description)
    sop_path: Path                  # path to sop.md / sop.jinja2
    enter_args_schema: dict | None  # JSON-schema-like, for the LLM to know how to enter
    tags: list[str] = field(default_factory=list)
    version: str = "1"
    # Optional richer fields:
    initial_phase: str = "0"        # default starting phase id
    requires_target_path: bool = False
```

Loaded from disk:
```
openteam/server/resources/workflows/<name>/
    workflow.yaml          # WorkflowDefinition fields except description/sop
    description.md         # workflow description (replaces _variables/workflow_description/default.jinja2)
    sop.md                 # the SOP (replaces _variables/workflow/sop.jinja2)
```

### 3.2 `WorkflowInstance` (runtime — one per entry)

```python
# agent_foundation/server/workflows/instance.py  (NEW)
@dataclass
class WorkflowInstance:
    workflow_id: str                # uuid, e.g. "wf_a3f1c2"
    definition_name: str            # FK → WorkflowDefinition.name
    state: str = "active"           # "active" | "suspended" | "completed" | "aborted"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # The state machine slice (was inside WorkflowContext):
    current_phase: str = "0"
    phase_status: str = "idle"
    completed_phases: list[WorkflowPhaseRecord] = field(default_factory=list)
    phase_outputs: dict[str, Any] = field(default_factory=dict)
    goto_counts: dict[str, int] = field(default_factory=dict)
    # Per-instance scratch (target_path, model, anything declared by enter_args_schema):
    instance_args: dict[str, Any] = field(default_factory=dict)
    # Lifecycle bookkeeping:
    suspended_reason: str = ""
    last_active_turn: int = 0
    
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowInstance": ...
```

### 3.3 `WorkflowSet` (per-session collection — replaces single `WorkflowContext`)

```python
# agent_foundation/server/workflows/workflow_set.py  (NEW)
@dataclass
class WorkflowSet:
    instances: dict[str, WorkflowInstance] = field(default_factory=dict)
    active_workflow_id: str | None = None    # which one is "in focus" right now

    def enter(self, defn: WorkflowDefinition, args: dict) -> WorkflowInstance: ...
    def exit_active(self, reason: str = "") -> None:                # → suspended
    def resume(self, workflow_id: str) -> WorkflowInstance: ...     # suspended → active
    def complete(self, workflow_id: str, summary: str = "") -> None
    def abort(self, workflow_id: str, reason: str = "") -> None
    def active(self) -> WorkflowInstance | None: ...
    def suspended(self) -> list[WorkflowInstance]: ...

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowSet": ...
```

The session schema becomes:
```python
session = {
    "id": ...,
    "messages": [...],
    "workflows": {
        "active_workflow_id": "wf_a3f1" | None,
        "instances": {
            "wf_a3f1": {WorkflowInstance...},
            "wf_b912": {WorkflowInstance...},
        }
    },
    # back-compat: keep "workflow_context": {} populated as a projection of the active instance
    # for one release, then remove.
}
```

### 3.4 `WorkflowRegistry` (global, like ToolDispatcher)

```python
# openteam/server/services/workflow_registry.py  (NEW)
class WorkflowRegistry:
    def __init__(self, workflows_dir: Path) -> None: ...
    def list(self) -> list[WorkflowDefinition]: ...
    def get(self, name: str) -> WorkflowDefinition | None: ...
    def reload(self) -> None: ...
```

Discovery: walks `workflows_dir`, parses each `workflow.yaml` + `description.md` + `sop.md`.

---

## 4. Prompt-Rendering Changes

### 4.1 Inferencer's `_render_prompt` — refactored shape

```python
# Conceptual replacement of the SOP block at conversational_inferencer.py:618-690

# Pull workflow snapshot from prior_context (set fresh each turn by ConversationService).
catalog: list[WorkflowDefinition] = self.prior_context.get("workflow_catalog", [])
ws: WorkflowSet = self.prior_context.get("workflow_set")  # may be None
active = ws.active() if ws else None

# Always-on
feed["workflow_catalog_block"] = render_workflow_catalog(catalog)
feed["ongoing_workflows_block"] = render_ongoing_workflows(ws.suspended()) if ws else ""

if active is not None:
    defn = registry.get(active.definition_name)
    sop  = SOPManager.load(defn.sop_path)
    tracker = StateGraphTracker(
        graph=sop,
        current_state=active.current_phase,
        state_status=active.phase_status,
        completed_states=[r.phase for r in active.completed_phases],
        state_outputs=active.phase_outputs,
        goto_counts=active.goto_counts,
    )
    feed["active_workflow_id"]            = active.workflow_id
    feed["workflow_description"]          = defn.description
    feed["workflow_status"]               = render_status_text(active, sop)
    feed["workflow_nextstep_guidance"]    = SOPManager.render_guidance(tracker, sop, context=…)
    self.prior_context["_sop"]            = sop
    self.prior_context["tool_phase_map"]  = sop.tool_to_phase_map
else:
    # No active workflow: do NOT inject workflow_description / status / guidance.
    # The Jinja2 guard `{% if workflow_description is defined and workflow_description %}`
    # already collapses the block.
    feed["workflow_description"] = ""
    feed["workflow_status"]      = ""
    feed["workflow_nextstep_guidance"] = ""
```

### 4.2 New Jinja2 partials

`_partials/workflow_catalog.jinja2` (NEW):
```jinja2
{% if workflow_catalog and workflow_catalog | length > 0 %}
## Workflow Catalog
You can enter any of these stateful, multi-step workflows. Each instance is tracked by a `workflow_id` you can later resume.
{% for w in workflow_catalog %}
- **{{ w.name }}** — {{ w.summary }}
  Enter via `enter_workflow(name="{{ w.name }}", args={...})`.
{% endfor %}
{% endif %}
```

`_partials/ongoing_workflows.jinja2` (NEW):
```jinja2
{% if ongoing_workflows and ongoing_workflows | length > 0 %}
## Ongoing Workflows (suspended — resume any time)
{% for inst in ongoing_workflows %}
- **{{ inst.workflow_id }}** ({{ inst.definition_name }}) — paused at Phase {{ inst.current_phase }} ({{ inst.phase_status }})
  Last summary: {{ inst.suspended_reason or "—" }}
  Resume via `resume_workflow(workflow_id="{{ inst.workflow_id }}")`.
{% endfor %}
{% endif %}
```

### 4.3 `initial.jinja2` modifications (OpenTeam)

The existing workflow block (lines 6–23) becomes a **scoped "Active Workflow" block**:

```jinja2
{% include "_partials/workflow_catalog.jinja2" %}
{% include "_partials/ongoing_workflows.jinja2" %}

{% if active_workflow_id %}
## Active Workflow (id={{ active_workflow_id }})
{% if workflow_target_path %}
You operate on {{ workflow_target_path }} under repository `{{ session_root_path }}`.
{% endif %}
<WorkflowDescription>{{ workflow_description }}</WorkflowDescription>
<WorkflowStatus>{{ workflow_status }}</WorkflowStatus>
<WorkflowNextStepGuidance>{{ workflow_nextstep_guidance }}</WorkflowNextStepGuidance>
You may exit this workflow at any time via `exit_workflow()`. Doing so suspends it and you can resume later via the workflow_id shown above.
{% endif %}
```

### 4.4 Decision Procedure (extended)

```text
1. Classify user message:
   (a) Workflow-aligned with the ACTIVE workflow → continue per WorkflowNextStepGuidance.
   (b) Aligned with a SUSPENDED workflow → call `resume_workflow(workflow_id=…)` first, then continue.
   (c) Aligned with an AVAILABLE workflow not yet started → call `enter_workflow(name=…, args=…)`.
   (d) Out-of-scope but actionable → fulfil ad-hoc, optionally call `exit_workflow()` first if active workflow makes prompt noisy.
   (e) Conversational → reply directly.
2. Never silently start a workflow if one is already active. Either continue it, exit-then-enter, or refuse politely.
3. After the last phase completes, call `complete_workflow()` to mark it terminal.
```

---

## 5. Workflow Control Tools (the LLM-facing API)

These are **conversation-control tools** in the same family as `clarification` / `confirmation` — built into the inferencer, not user-defined.

| Tool | Args | Behavior |
|---|---|---|
| `enter_workflow` | `name: str`, `args: dict = {}`, `target_path?: str` | Validate `name` against registry, validate `args` against `enter_args_schema`, refuse if another workflow is active. Create a new `WorkflowInstance`, set as active. Returns the new `workflow_id`. |
| `exit_workflow` | `reason?: str` | Move the active instance to `"suspended"`, clear `active_workflow_id`. Persist a one-line `suspended_reason` so the prompt can summarize on resume. |
| `resume_workflow` | `workflow_id: str` | Refuse if another workflow is active (the LLM should `exit_workflow` first). Move target instance from `"suspended"` back to `"active"`. |
| `complete_workflow` | `summary?: str` | Mark active instance `"completed"`, record summary, clear `active_workflow_id`. |
| `abort_workflow` | `workflow_id?: str`, `reason?: str` | Mark instance `"aborted"`. If `workflow_id` is omitted, targets the active one. |
| `list_workflows` | — | Optional explicit "what's available + ongoing"; in normal use the prompt already shows this, but the LLM can call this if it needs a programmatic view. |

These tools are dispatched by the inferencer **before** the regular `tool_executor`. They mutate `prior_context["workflow_set"]` in-place; persistence happens at end of turn (see §6).

### 5.1 Why control tools, not magic strings

We considered making `/enter`, `/exit`, etc. slash-commands or relying on free-form intent classification. Tools are preferred because:
- The LLM already speaks the `ToolsToInvoke` JSON dialect — uniform mental model.
- Validation & schema checking are first-class (registry lookup, arg checks).
- The trace is easy to audit and replay.
- Backwards-compat: legacy slash-commands route through these tools.

---

## 6. ConversationService & Persistence Changes

### 6.1 `_compute_session_context` — refactor

Today (`conversation_service.py:352-378`) it builds `prior_context` from a single `WorkflowContext`. Replace with:

```python
def _compute_session_context(self, session: dict) -> dict:
    from agent_foundation.server.workflows.workflow_set import WorkflowSet

    raw = session.get("workflows") or {}
    ws  = WorkflowSet.from_dict(raw)
    return {
        "session_root_path": self._working_dir,
        "workflow_set": ws,                                # full collection (active+suspended)
        "workflow_catalog": self._workflow_registry.list(),# all definitions
        # Convenience flat keys for templates that already expect them:
        "active_workflow_id": (ws.active().workflow_id if ws.active() else ""),
    }
```

The active-workflow flat keys (`workflow_description`, `workflow_status`, `workflow_nextstep_guidance`) are NOT computed here — they are computed inside the inferencer's `_render_prompt` because they require the SOP/tracker (which lives in AgentFoundation, not OpenTeam).

### 6.2 `_persist_workflow_updates` — refactor

Replace single-slot save with full `WorkflowSet` save:

```python
def _persist_workflow_updates(self, session, prior_context, data_service):
    ws: WorkflowSet = prior_context.get("workflow_set")
    if ws is None:
        return
    # The inferencer also wrote phase/status/outputs into prior_context; mirror them
    # back into the active instance before persisting.
    active = ws.active()
    if active is not None:
        active.current_phase    = prior_context.get("current_phase", active.current_phase)
        active.phase_status     = prior_context.get("phase_status", active.phase_status)
        active.phase_outputs.update(prior_context.get("phase_outputs", {}))
        # completed_phases handled by enter/complete_phase or by _execute_tool_call.
        active.last_active_turn = session.get("turn_index", 0)
        active.updated_at       = time.time()

    self._session_store.update_workflows(session["id"], ws.to_dict())
```

### 6.3 `SessionStore` additions

- New: `update_workflows(session_id, ws_dict)` (replaces `update_workflow_context`).
- Keep `update_workflow_context` for one release as a thin wrapper that updates the active instance's slice (for back-compat with anything still using it).
- `_default_workflows()` returns `{"active_workflow_id": None, "instances": {}}`.
- `_backfill_workflows()`: if a session has only `workflow_context`, migrate it into `workflows.instances["wf_legacy"]` and mark it active.

### 6.4 Per-session inferencer cache

`_get_session_inferencer` (`conversation_service.py:220-258`) keys by `session_id` only — that's fine. The inferencer mutates `prior_context["workflow_set"]` during a turn; the service round-trips it via `_compute_session_context` / `_persist_workflow_updates`.

> **Why not key by `(session_id, workflow_id)`?** Because the inferencer is the *conversation* unit, and conversation lives at session granularity. Workflow instances move between active/suspended within the *same* conversation. Keying per-workflow would force re-creating the inferencer on every enter/exit — wasteful and would drop `_messages`.

---

## 7. Tool / Phase Coupling — How Tools Belong to Workflows

Today, `tool_phase_map` is a single global dict on `prior_context`. After the change:

- `tool_phase_map` is **derived from the active SOP per turn** (already done at `conversational_inferencer.py:632-635` — only need to confirm it is recomputed on every render so that switching workflows refreshes the map).
- A tool that touches the workflow state (e.g., `role_setup`) is still a normal tool. Its membership in a workflow is a property of the **active SOP**, not of the tool.
- Open question (§8.5): should tools declare `workflows: ["role_setup", "team_onboard"]` metadata so the catalog can hint which tools belong to which workflow? Recommended **yes** — purely a UX hint, no behavior change.

**`_execute_tool_call` impact**: lines 779–815 update `prior_context["current_phase"]` etc. directly. Replace with `ws.active().start_phase(sop_phase, summary=…)` so the per-instance state is updated. If no active workflow, do not touch any workflow state — the tool runs free-form.

---

## 8. Open Questions / Critical-Thinking Risks

| # | Question | Tentative answer |
|---|---|---|
| 8.1 | One active workflow at a time, or multiple in-prompt? | Start with one. Multi-active multiplies prompt size and confuses next-step focusing. Re-evaluate after telemetry. |
| 8.2 | Where does `ongoing_workflows` summary text come from on suspend? | `exit_workflow` should auto-generate from `active.to_status_text()` truncated to ≤ 200 chars. The LLM may also pass a `reason`. |
| 8.3 | What if the LLM calls `enter_workflow` while one is active? | The control-tool returns an error string and a hint: "Active workflow already exists. Call `exit_workflow()` first." The model self-corrects on the next pass. |
| 8.4 | What if a `workflow.yaml` is added at runtime? | `WorkflowRegistry.reload()` on a known signal (filesystem watcher OR explicit `/reload-workflows` admin endpoint). |
| 8.5 | Tools advertising workflow affinity in catalog | Optional — purely cosmetic in the prompt. Backed by an optional `workflows:` field in `tool.json`. |
| 8.6 | Backwards-compatibility for existing sessions on disk | `_backfill_workflows()` upgrades old sessions on load. Tested in §10. |
| 8.7 | What happens to `task_queue` / `multi_task_id` (currently per-`WorkflowContext`)? | Move INTO `WorkflowInstance` so each instance has its own queue. Multi-task hubs are per-instance. |
| 8.8 | Concurrency safety for shared `prior_context` mutations across async calls | Already a concern today; we keep the existing single-thread per-session assumption and document it. Any cross-instance mutation goes through `WorkflowSet` methods which we make idempotent. |
| 8.9 | What about `prior_context` keys outside the workflow? (e.g., `session_root_path`) | Stay top-level. The `WorkflowSet` lives at `prior_context["workflow_set"]` only. |
| 8.10 | Should `_messages` (conversation history) be split per workflow? | **No** — chat is shared. Workflows annotate the chat, they don't fork it. |
| 8.11 | Do we keep `workflow_target_path` in prompt? | Yes, but scoped to the active instance: `active.instance_args["target_path"]`. |
| 8.12 | The current `_load_workflow_description()` in OpenTeam reads a hard-coded path | Remove; description comes from `WorkflowDefinition.description`. |

---

## 9. Implementation Phases (dependency-sorted)

### Phase A — Data model and registry (no behavior change yet)
1. Add `WorkflowDefinition`, `WorkflowInstance`, `WorkflowSet`, `WorkflowRegistry` (4 new files in AgentFoundation + OpenTeam).
2. Migrate `task_queue`, `bypass_cap_tools`, `tool_phase_map`, `phase_outputs`, `state_tracker` fields from `WorkflowContext` into `WorkflowInstance`. Keep `WorkflowContext` as a thin shim that wraps a single `WorkflowInstance` for back-compat.
3. Unit tests for serialization round-trips, lifecycle methods, registry discovery.

### Phase B — Filesystem layout
1. Create `openteam/server/resources/workflows/` directory.
2. Move existing default content:
   - `_variables/workflow_description/default.jinja2` → `workflows/default/description.md`
   - `_variables/workflow/sop.jinja2` → `workflows/default/sop.md`
   - Add `workflows/default/workflow.yaml` (name=`default`, summary=…).
3. Keep old files as symlinks for one release for back-compat.

### Phase C — ConversationService wiring
1. Inject a `WorkflowRegistry` instance into `ConversationService.__init__`.
2. Replace `_compute_session_context` body (§6.1).
3. Replace `_persist_workflow_updates` body (§6.2).
4. Add `update_workflows` to `SessionStore`; add `_backfill_workflows` migration on load.
5. Tests: a session loaded from old format gets auto-upgraded.

### Phase D — Inferencer prompt rendering
1. Refactor `_render_prompt` (lines 567–728) per §4.1 — pull `workflow_set`, branch on active.
2. Add `render_workflow_catalog` and `render_ongoing_workflows` helpers (in AgentFoundation).
3. Update `_execute_tool_call` (lines 779–815) to mutate the active `WorkflowInstance` instead of bare `prior_context`.
4. Tests: render with no active, with one active, with one active + 2 suspended.

### Phase E — Control tools (`enter/exit/resume/complete/abort/list_workflow`)
1. Add to the built-in conversation-tool set in `conversation_tools.py`.
2. Wire dispatcher in `conversational_inferencer.py` (similar pattern to `clarification`/`confirmation`).
3. Validate args against `enter_args_schema`.
4. Tests: state transitions, refusal cases, schema mismatches.

### Phase F — Template updates (OpenTeam)
1. Add `_partials/workflow_catalog.jinja2` and `_partials/ongoing_workflows.jinja2`.
2. Modify `initial.jinja2` to scope the workflow block to the active instance and include the new partials.
3. Update `.initial.config.yaml` `structural_xml_tags` if any new XML wrappers are introduced.
4. Snapshot tests on rendered prompts.

### Phase G — Decision-procedure prompt edits
1. Extend `## Decision Procedure` text to cover (a)–(e) classification.
2. Add usage examples for `enter_workflow`/`exit_workflow`/`resume_workflow`.

### Phase H — Telemetry & observability
1. Emit a structured log event on every state transition (`workflow.entered`, `workflow.suspended`, `workflow.resumed`, `workflow.completed`, `workflow.aborted`).
2. Add metrics: count of concurrent suspended workflows per session, mean lifetime in suspended state, abort rate.
3. Add a `/sessions/{id}/workflows` REST endpoint for the UI.

### Phase I — Cleanup
1. Remove the `WorkflowContext` shim once all callers migrated.
2. Remove the symlinks added in Phase B.
3. Delete `_load_workflow_description()` from `ConversationService` and `SessionStore`.

---

## 10. Testing Strategy

### Unit tests
- `WorkflowDefinition` parsing from yaml/md.
- `WorkflowInstance` to/from dict; lifecycle transitions.
- `WorkflowSet` enter/exit/resume/complete/abort guards (refuse double-active, refuse resume-when-active).
- `WorkflowRegistry` discovery + reload.
- `_compute_session_context` / `_persist_workflow_updates` round-trip preserves fidelity.

### Integration tests
- A session with no workflow → prompt has Catalog only, no Active block.
- `enter_workflow` → next render has Active block; SOP/status/guidance scoped to that instance.
- `exit_workflow` → next render has Catalog + Ongoing, no Active block.
- `resume_workflow` → matches state of the suspended instance exactly (phase, outputs, completed phases).
- Two enter→exit cycles produce two suspended instances; both appear in Ongoing list.
- `_backfill_workflows`: a legacy session JSON loads and ends up with one suspended-or-active instance preserving its prior phase and outputs.

### End-to-end (mock LLM)
- Scripted: user says "let's start the role setup" → LLM emits `enter_workflow(name=role_setup)` → workflow runs → user says "wait, I want to onboard team X first" → LLM emits `exit_workflow()` then `enter_workflow(name=team_onboard)` → user resumes original by ID.
- Verify prompts at every turn match expected snapshots.

### Regression
- All current SOP-driven flows still pass when the legacy `default` workflow is the only one entered.

---

## 11. File-by-File Change Summary

### NEW files
- `agent_foundation/server/workflows/__init__.py`
- `agent_foundation/server/workflows/definition.py` — `WorkflowDefinition`
- `agent_foundation/server/workflows/instance.py` — `WorkflowInstance`
- `agent_foundation/server/workflows/workflow_set.py` — `WorkflowSet`
- `agent_foundation/server/workflows/render.py` — `render_workflow_catalog`, `render_ongoing_workflows`
- `openteam/server/services/workflow_registry.py` — `WorkflowRegistry`
- `openteam/server/resources/prompt_templates/conversation/main/_partials/workflow_catalog.jinja2`
- `openteam/server/resources/prompt_templates/conversation/main/_partials/ongoing_workflows.jinja2`
- `openteam/server/resources/workflows/default/{workflow.yaml,description.md,sop.md}`
- Tests under `OpenTeam/test/openteam/server/services/test_workflow_registry.py` etc.

### MODIFIED files
- `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py`
  - `_render_prompt` (lines 567–728)
  - `_execute_tool_call` (lines 779–815)
  - Add control-tool dispatch alongside `_handle_conversation_tool` family.
- `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversation_tools.py`
  - Add `enter_workflow`, `exit_workflow`, `resume_workflow`, `complete_workflow`, `abort_workflow`, `list_workflows`.
- `agent_foundation/server/workflow_context.py`
  - Reduce to a thin shim wrapping a single `WorkflowInstance`; deprecate.
- `openteam/server/services/conversation_service.py`
  - `__init__` accepts `workflow_registry`.
  - `_compute_session_context`, `_persist_workflow_updates` rewritten.
  - Drop `_load_workflow_description`.
- `openteam/server/services/session_store.py`
  - Add `update_workflows`, `_default_workflows`, `_backfill_workflows`.
  - Keep `update_workflow_context` as deprecated wrapper for one release.
- `openteam/server/resources/prompt_templates/conversation/main/initial.jinja2`
  - Scope the workflow block to active; add `{% include %}` for the two new partials.
- `openteam/server/resources/prompt_templates/conversation/main/.initial.config.yaml`
  - Update `structural_xml_tags` list if new tags added.

### DEPRECATED / TO REMOVE in cleanup phase
- `openteam/server/resources/prompt_templates/conversation/main/_variables/workflow/sop.jinja2`
- `openteam/server/resources/prompt_templates/conversation/main/_variables/workflow_description/default.jinja2`
- `openteam/server/resources/prompt_templates/conversation/main/_variables/workflow/.sop.config.yaml`

---

## 12. Backwards Compatibility Matrix

| Concern | Strategy |
|---|---|
| Existing sessions on disk | `_backfill_workflows` upgrades on first load. |
| Existing `WorkflowContext` consumers in code | `WorkflowContext` becomes a façade over the active `WorkflowInstance`; same fields, same methods. |
| Existing prompts saved in turn logs | Prompts are observational logs only; new sessions render new prompts. |
| Slash commands (e.g. `/create-role`) | Each maps to `enter_workflow(name=…)`. Routed in `command_router.py`. |
| Template variables `{{ workflow_description }}`, `{{ workflow_status }}`, `{{ workflow_nextstep_guidance }}` | Still produced when an active workflow exists; just empty when none. |

---

## 13. Critical-Thinking Double-Check (Self-Review)

| Concern | Resolution in this plan |
|---|---|
| "Workflows are just like tools/skills" — but tools are stateless, workflows are stateful. Doesn't this break the analogy? | The catalog discovery + LLM-callable interface is the analog. State is encapsulated in `WorkflowInstance`, surfaced explicitly in the "Ongoing Workflows" block. |
| "What is the workflow_id for?" | (a) Resume token after suspend. (b) Disambiguates multiple instances of same definition (e.g., two role_setup runs for different roles). (c) Used in telemetry & UI. |
| "Why not multiple-active?" | Prompt size + LLM focus. Suspend/resume gives the same expressive power without prompt blow-up. Open §8.1 tracks revisit. |
| "Will the LLM correctly use enter/exit?" | Decision Procedure + control-tool descriptions teach it; integration tests cover the major branches. Confidence: medium-high — same model already understands `clarification`/`confirmation`. |
| "Will renaming `WorkflowContext` break callers?" | Façade preserves the type for one release. Tests validate. |
| "Migration of old sessions" | `_backfill_workflows` covered + tested. |
| "Will `tool_phase_map` collisions happen if two workflows define overlapping tool phases?" | The map is per-active SOP — only one workflow's SOP is loaded at a time, so no collision. |
| "Are stateful workflows just LinearWorkflowInferencers in disguise?" | No — those are flow-graph inferencers that *replace* the conversational loop. We keep the conversational loop as the host, with workflow phases as a soft state machine the LLM voluntarily progresses through. |
| "Is suspend a real concept for an LLM?" | Yes, because the SOP/status/guidance disappear from the prompt — the LLM experiences "I am no longer in that workflow" — but the state survives in `WorkflowInstance` so we can re-inject on resume. |
| "Race condition if user sends two messages while a workflow is mid-step?" | Same as today — the conversation service serializes turns per session. No new exposure. |

---

## 14. Success Criteria

1. A session can `enter` a workflow → prompt shows full SOP & guidance for that workflow only.
2. A session can `exit` a workflow → prompt drops the active block and shows it under Ongoing with its `workflow_id`.
3. The session can `resume` by `workflow_id` → state (phase, outputs, completed phases) is fully restored.
4. Multiple workflows can be entered (sequentially), exited, and listed in Ongoing.
5. The LLM can autonomously decide to enter/exit based on user intent (verified in mock-LLM E2E).
6. No regression on the existing single-workflow flows (default `OpenStartup` workflow keeps working when entered).
7. Old sessions on disk auto-migrate without data loss.
8. Telemetry events fire on every transition.

---

## 15. Out of Scope (explicit)

- Concurrent **active** workflows (>1 in prompt at once) — see §8.1.
- Workflow composition / sub-workflows — defer.
- Workflow versioning at runtime (in-flight upgrade of a definition) — defer; for now, an instance is pinned to the registry's current version when entered.
- Cross-session workflow handoff — defer.
- A UI for browsing/curating workflow definitions — only a REST endpoint is in scope.

---





