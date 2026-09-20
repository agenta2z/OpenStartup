# Workflow-as-First-Class-Citizen — Multi-Workflow Conversational Inference

> **Author:** Rovo Dev (with Tony Chen)
> **Date:** 2026-05-08
> **Status:** Proposal (Design + Phased Implementation)
> **Predecessor:** `OpenTeam/src/openteam/server/resources/docs/_plan/conversation_workflow_control/PLAN.md`
>   (single-workflow per session, already partially implemented in `conversation_service.py`)
> **Codebase under change:** `/Users/tchen7/MyProjects/rovoteam/OpenTeam/src/openteam`
> **Hard dependency:** `/Users/tchen7/MyProjects/CoreProjects/AgentFoundation/src/agent_foundation`
>   (specifically `server/workflow_context.py` and `common/inferencers/agentic_inferencers/conversational/`)

---

## 0. TL;DR — The Mental Model Shift

**Today (single-workflow, fixed):**

```
Session  ──owns──►  ONE WorkflowContext  ──templates──►  ONE sop.jinja2
                    (current_phase, completed_phases, …)
```

The agent is *fixated* on one SOP from session creation; the SOP is loaded once
via `find_sop_file()` which hard-codes the path
`prompt_templates/conversation/main/_variables/workflow/sop.{ext}`. There is no
notion of "available workflows" vs. "active workflows", and no way to enter or
exit a workflow mid-conversation.

**Proposed (workflow-as-tool, multi-workflow, resumable):**

```
Session  ──owns──►  WorkflowRegistry           (catalog of definitions, like Tools/Skills)
              └──►  WorkflowSessionState       (zero-or-more live workflow runs)
                    ├── WorkflowRun #wf-abc12  (state machine on SOP A, status=running, paused)
                    ├── WorkflowRun #wf-xyz98  (state machine on SOP B, status=completed)
                    └── …                       (others, including aborted/snapshotted)
                    (active_workflow_id is at most ONE; agent decides via tool calls)
```

The Jinja2 prompt rendering keeps **two complementary sections**:

1. **Always-shown** "Workflow Catalog" block — like `## Available Tools`. Lists
   every workflow definition the agent may *enter*, plus every workflow run
   currently in progress that it may *resume*. (Same lifecycle pattern as
   tools/skills: discovery is constant, invocation is dynamic.)
2. **Conditionally-shown** "Active Workflow" block — only present when
   `active_workflow_id` is set. This is the existing `<WorkflowDescription>`,
   `<WorkflowStatus>`, `<WorkflowNextStepGuidance>` block, but bound to the
   currently active run (one of many).

Entering/exiting/resuming is done via three new **first-class action tools**
(`enter_workflow`, `exit_workflow`, `resume_workflow`), invoked through the same
`ToolsToInvoke` JSON channel the LLM already uses for `create_role`,
`role_setup`, etc. There is no new transport layer; the existing dispatcher
mutates `prior_context` via `context_updates` exactly as today.

---

## 1. Goals & Non-Goals

### 1.1 Goals

| # | Goal | Why it matters |
|---|------|----------------|
| G1 | Workflow becomes a **discoverable, named, versioned definition** alongside tools and skills, not a hidden Jinja2 file. | Lets us add new SOPs (`onboard_new_employee.jinja2`, `conduct_review.jinja2`, …) without touching server code. |
| G2 | A conversation can have **0..N inactive workflow runs** and **0..1 active workflow run** at any turn. | Matches the user's intent: agent "decides on its own when to enter and when to exit." |
| G3 | Workflow runs are **stateful and resumable**. Each has a stable `workflow_id`. Pausing keeps phase/output state; resuming reconstructs `<WorkflowStatus>` exactly. | The user explicitly called out: "you can exit half way and re-enter; every running workflow needs a workflow id." |
| G4 | The prompt always lists **available workflows** (definitions) and **ongoing workflows** (paused runs) — even when none is active. | Mirrors how `## Available Tools` works today. Maintains agent autonomy. |
| G5 | Backward compatible: existing single-workflow OpenStartup orchestrator SOP continues to work without UX regression. | Don't break the demo. The default behavior of a fresh session can still be "auto-enter the OpenStartup SOP". |

### 1.2 Non-Goals

| # | Non-Goal | Rationale |
|---|----------|-----------|
| N1 | Concurrent execution of *two* active workflows in the same session. | Agent attention is single-threaded; concurrency would need a coordinator that doesn't exist yet. We model "at most one active". Users can spawn separate sessions for parallel runs (out of scope here). |
| N2 | Cross-session workflow handoff (move run from session A to session B). | Adds storage/auth complexity without a near-term use case. Workflow IDs are session-local. |
| N3 | Workflow inheritance / composition (workflow embeds another). | A workflow may *invoke action tools that themselves spawn child sessions* (already works today via `role_setup`'s nested breakdown). Direct nested workflows are an extension; design leaves a hook but doesn't implement. |
| N4 | Replacing tools & skills with workflows. | Workflows are a **third** orthogonal axis. Tools = atomic actions, Skills = grouped domain knowledge + tool bundles, Workflows = stateful multi-step procedures over tools/skills. |

---

## 2. Investigation Findings (Today's Reality)

### 2.1 The Conversation Inference Pipeline (file-by-file)

| Step | File | Function | Note |
|------|------|----------|------|
| HTTP/WS in | `server/routes/manager_websocket_routes.py` | `process_message` | Detects no slash commands today; everything is LLM-routed. |
| Service entry | `server/services/conversation_service.py` | `ConversationService.run_conversation_turn` (L457) | Per-turn driver. Calls `_compute_session_context`, `inferencer.set_prior_context`, `set_messages`, `run_agentic_loop`, then `_persist_workflow_updates`. |
| Per-session inferencer | same | `_get_session_inferencer` (L220) | Cached per `session["id"]`. |
| Prior context build | same | `_compute_session_context` (L352) | Reads `session["workflow_context"]` → `WorkflowContext.from_dict` → `to_status_text()`. |
| Persistence | same | `_persist_workflow_updates` (L392) | After loop, rebuilds WC from `inferencer.prior_context` and writes via `data_service.update_workflow_context(session_id, dict)`. |
| Inferencer | `agent_foundation/.../conversational/conversational_inferencer.py` | `run_agentic_loop`, `_render_prompt` (L568), `_execute_tool_call` (L762) | Loads SOP via `prompt_renderer.find_sop_file()`. Stores `_sop`, `tool_phase_map` into `prior_context`. Tools' `context_updates` mutate `prior_context` mid-loop. |
| Prompt render helper | `_SimplePromptRenderer.find_sop_file` (`conversation_service.py` L101) | Single hard-coded path → `_variables/workflow/sop.{ext}`. **This is the chokepoint.** |
| State container | `agent_foundation/server/workflow_context.py` | `WorkflowContext` (L86), `WorkflowPhaseRecord` (L60) | Phase lifecycle: `start_phase`, `complete_phase`, `fail_phase`. Serializable via `to_dict`/`from_dict`. |
| Storage | `server/services/session_store.py` | `update_workflow_context` (L232), `_default_workflow_context` (L459), `_backfill_workflow_context` (L474) | Atomically writes one `workflow_context` blob per session. |

### 2.2 The `_variables/<slot>/<choice>.jinja2` Mechanism

- `prompt_templates/conversation/main/initial.jinja2` is the entry point. It
  references three workflow-related variables: `workflow_description`,
  `workflow_status`, `workflow_nextstep_guidance` (all guarded by
  `{% if workflow_description is defined and workflow_description %}`).
- Two slot directories exist:
  - `_variables/workflow_description/default.jinja2` — purely *static* description.
  - `_variables/workflow/sop.jinja2` — the *active* SOP machine-readable phases.
- The slot resolver (`python_utils.string_utils.formatting.template_manager`)
  picks `<choice>.jinja2` based on a `strategy` key in `prior_context` (see
  `WorkflowContext.set_strategy`). Today only one choice (`sop` for `workflow`,
  `default` for `workflow_description`) exists, so strategy switching has
  effectively never been exercised.
- Files like `.sop.config.yaml` give per-choice metadata (subsection
  directives, etc.). These are read by `SOPManager`.

### 2.3 The Tools & Skills Surfaces (the model we'll mirror)

| Surface | On-disk schema | Discovered by | Listed in prompt |
|---------|----------------|---------------|------------------|
| **Tool** | `tools/<name>/tool.json` (manifest) + Python `executor.py` | `tool_dispatcher.py` registry; `_load_executors` does dynamic import | Rendered into `{{ action_tools }}` (whitelisted via `.initial.config.yaml → enabled_action_tools`). |
| **Skill** | `skills/<name>/SKILL.md` (frontmatter YAML + markdown) declaring `tools:` array | `role_skill_routes.py` for role-pool discovery (in agent role definition flow) | Skills are not currently injected into the conversation prompt; they're a **role assembly** primitive. |
| **Conversation tool** | Built into `ConversationalInferencer` (clarification, single_choice, multiple_choice, confirmation, tool_argument_form) | Hard-coded handlers under `conversational/handlers/` | Always present, rendered into `{{ conversation_tools }}`. |

The **invocation** model is uniform: LLM emits a JSON line in a fenced
`json ToolsToInvoke` block. The dispatcher resolves the name, runs the executor
(possibly async), captures `ToolExecutionResult.context_updates` (a dict), and
merges it into `prior_context`. **This is exactly the channel we will reuse for
workflow control.** No new transport.

### 2.4 What is Already Coupled to "Single Workflow"

| Coupling site | Symptom |
|---------------|---------|
| `_SimplePromptRenderer.find_sop_file()` | Returns at most one path (`sop.{ext}`). Cannot enumerate or pick. |
| `prior_context["_sop"]`, `prior_context["tool_phase_map"]` | Single value, overwritten every turn. |
| `session["workflow_context"]` is a single `WorkflowContext` dict | No notion of multiple runs. |
| `WorkflowContext.set_strategy(strategy)` reloads `workflow_description` from importlib only | Can switch *which* SOP is canonically active by `strategy`, but loses all in-flight state on switch — not resumable. |
| `initial.jinja2` lines 6–23 | Hard-codes the *single* `<WorkflowDescription>`/`<WorkflowStatus>`/`<WorkflowNextStepGuidance>` block. No "available workflows" listing. |
| `.initial.config.yaml → enabled_action_tools` | Whitelists `create_role`, `role_setup` only. Workflow-control tools must be added here too. |

---

## 3. Proposed Architecture

### 3.1 Three-Layer Concept Model

```
                       ┌───────────────────────────────────────────┐
                       │          WorkflowDefinition (catalog)     │
                       │  on-disk, like Tools and Skills           │
                       │  resources/workflows/<name>/              │
                       │     ├── workflow.json   (manifest)        │
                       │     ├── description.jinja2 (the static    │
                       │     │   "what does this workflow do" blurb│
                       │     │   that shows in the catalog list)   │
                       │     ├── sop.jinja2     (machine SOP)      │
                       │     └── .sop.config.yaml (subsection      │
                       │         directives — same as today)       │
                       └────────────────┬──────────────────────────┘
                                        │ load+register at startup
                                        ▼
                       ┌───────────────────────────────────────────┐
                       │          WorkflowRegistry (in-mem)        │
                       │   .get(name) → WorkflowDefinition         │
                       │   .list()    → [WorkflowDefinition]       │
                       └────────────────┬──────────────────────────┘
                                        │
       per-session, in session_store    │ instantiated on enter_workflow
                                        ▼
                       ┌───────────────────────────────────────────┐
                       │  WorkflowRun  (instance, has unique ID)   │
                       │  -- workflow_id: "wf-<8 hex>"             │
                       │  -- definition_name: "openstartup_orch"   │
                       │  -- status: enum {running, paused,        │
                       │       completed, aborted}                 │
                       │  -- workflow_context: WorkflowContext     │
                       │       (the existing AF dataclass; one     │
                       │        per run, not one per session)      │
                       │  -- created_at / updated_at               │
                       │  -- entry_reason: str (why agent entered) │
                       │  -- exit_reason : str (why exited/paused) │
                       └────────────────┬──────────────────────────┘
                                        │
                                        ▼
                       ┌───────────────────────────────────────────┐
                       │  WorkflowSessionState (per session dict)  │
                       │  session["workflow_state"] =              │
                       │    { "active_workflow_id": str | None,    │
                       │      "runs": { wf_id: WorkflowRun.dict,   │
                       │                  ... } }                  │
                       └───────────────────────────────────────────┘
```

### 3.2 Catalog vs. Active Distinction in the Prompt

The `initial.jinja2` template gains **two new variables** alongside the
existing workflow trio:

| Variable | When set | Rendered as | Source |
|----------|----------|-------------|--------|
| `available_workflows` | Always (when registry non-empty) | `## Available Workflows` listing one bullet per `WorkflowDefinition` (name, short description, "enter via `enter_workflow(name=…)`"). | `WorkflowRegistry.list()` |
| `ongoing_workflows` | Always (when ≥1 paused run exists) | `## Ongoing Workflows` listing each paused `WorkflowRun` with its `workflow_id`, current phase, % complete, "resume via `resume_workflow(workflow_id=…)`". | `WorkflowSessionState.runs` filtered by `status == "paused"`. |
| `workflow_description` | Only when an active run exists | unchanged — the active run's static description | Active run's `WorkflowDefinition.description` |
| `workflow_status` | Only when active | unchanged — the active run's `WorkflowContext.to_status_text()` | Active `WorkflowRun.workflow_context` |
| `workflow_nextstep_guidance` | Only when active | unchanged — derived by AF inferencer from active SOP | Active SOP via `SOPManager.render_guidance` |

This achieves the user's exact request: **"once it exits, those things are
gone, but prompt still shows available workflows … and ongoing workflows."**

### 3.3 Lifecycle (state machine for one WorkflowRun)

```
                 ┌────────────────────────────────────────────┐
                 │                                            │
       enter_workflow                                         │
   (creates new run, ID=wf-abc12, status=running) ────────────┼─────► running ──► (LLM advances phases via SOP-defined tools; phase_outputs accumulate)
                                                              │
   exit_workflow(workflow_id=wf-abc12)                        │
   (status=running → paused; clears active_workflow_id) ──────┼─────► paused ──► resume_workflow(workflow_id=wf-abc12) ──► running
                                                              │                                                       (also implicitly fails if active_workflow_id != None
                                                              │                                                        — agent must exit current first)
   complete_workflow                                          │
   (terminal phase reached → status=completed) ───────────────┼─────► completed
                                                              │
   abort_workflow / agent gives up                            │
   (status=aborted) ─────────────────────────────────────────►│─────► aborted
                                                              │
                                                              └─►  Notes:
                                                                   - At most ONE run can be in status=running per session.
                                                                   - paused runs persist in session_store; they survive
                                                                     server restart because session JSON is the SoT.
                                                                   - completed/aborted runs are kept (read-only) for the
                                                                     agent to reference, but not re-enterable.
```

### 3.4 The Three New Workflow-Control Tools

Each is a normal **action tool** with a `tool.json`. They are auto-registered
and added to `enabled_action_tools` in `.initial.config.yaml`. Their job is to
mutate `prior_context["workflow_state"]`; the dispatcher then propagates that
into the session via the existing `_persist_workflow_updates` path.

| Tool | Args | What it does | Returned `context_updates` |
|------|------|--------------|-----------------------------|
| `enter_workflow` | `name: str` (definition name), `entry_reason: str` (LLM's free-text rationale, ≤ 200 chars) | If `active_workflow_id` is set → return error result asking to exit first. Else: create a new `WorkflowRun(workflow_id=new_id(), definition_name=name, status="running", workflow_context=WorkflowContext(workflow_description=def.description, strategy=name))`, append to `workflow_state.runs`, set `active_workflow_id`. | `workflow_state` (full updated dict), `_active_workflow_changed: True` (sentinel for downstream re-render of SOP cache). |
| `exit_workflow` | `workflow_id: str` (defaults to active), `exit_reason: str` | If `workflow_id` matches active: set its status to `paused`, store `exit_reason`, clear `active_workflow_id`. If matches a non-active run: noop with warning. | `workflow_state`, `_active_workflow_changed: True`. |
| `resume_workflow` | `workflow_id: str`, `resume_reason: str` | If `active_workflow_id` is set → error "exit first". Else find run with `workflow_id`. If status not `paused` → error. Else flip status to `running`, set `active_workflow_id = workflow_id`. | `workflow_state`, `_active_workflow_changed: True`. |

The `_active_workflow_changed` sentinel is used by the inferencer (one-line
hook in `_render_prompt`) to discard the cached `_sop` / `tool_phase_map` so
the *next* turn loads the new run's SOP.

> **Important nuance — the LLM's perspective of these tools.** They appear in
> `## Available Tools` exactly like `create_role`. The orchestrator SOP guidance
> already encourages the agent to inspect `<WorkflowStatus>` and `<WorkflowNextStepGuidance>`
> before deciding what to do; the new prompt section `## Workflow Decision`
> (see §3.6 below) tells it *when* to use these three tools.

### 3.5 Mapping: Single SOP File → Per-Run SOP

Today: `find_sop_file()` returns one fixed path.
Proposed: `find_sop_file(definition_name=None)` returns the SOP file for the
named `WorkflowDefinition`, or for the currently active run if `None`.

Concretely (in `_SimplePromptRenderer`):

```python
def find_sop_file(self, definition_name: str | None = None) -> Path | None:
    if definition_name is not None:
        wf_dir = self._templates_dir / "workflows" / definition_name
        for ext in (".jinja2", ".j2", ".md", ".yaml", ".yml"):
            candidate = wf_dir / f"sop{ext}"
            if candidate.is_file():
                return candidate
        return None
    # Legacy fallback: look in conversation/main/_variables/workflow/sop.*
    # (used when workflow_state isn't populated — backward compat)
    template_dir = self._templates_dir / "conversation" / "main"
    variables_dir = template_dir / "_variables" / "workflow"
    if not variables_dir.is_dir():
        return None
    for ext in (".jinja2", ".j2", ".md", ".yaml", ".yml"):
        candidate = variables_dir / f"sop{ext}"
        if candidate.is_file():
            return candidate
    return None
```

The CI's `_render_prompt` (AF, line ~622) consumes
`prior_context["active_definition_name"]` (new key supplied by
`_compute_session_context`):

```python
active_def = self.prior_context.get("active_definition_name")
sop_path = getattr(self.prompt_renderer, "find_sop_file", lambda *_: None)(active_def)
```

This is a **single-line, backward-compatible change** because the existing
zero-arg call still works (the legacy path is the fallback inside
`find_sop_file`). The same pattern is mirrored for `description` lookups.

### 3.6 Prompt Template Skeleton (after change)

```jinja2
{# initial.jinja2 — only the workflow-relevant slice shown #}

## Workflow Catalog
{% if available_workflows is defined and available_workflows %}
### Available Workflows (you may enter)
{% for w in available_workflows %}
- **{{ w.name }}** — {{ w.short_description }}
  *Enter via `enter_workflow(name="{{ w.name }}", entry_reason="…")`*
{% endfor %}
{% endif %}

{% if ongoing_workflows is defined and ongoing_workflows %}
### Ongoing Workflows (paused — you may resume)
{% for r in ongoing_workflows %}
- **{{ r.workflow_id }}** ({{ r.definition_name }}) — phase {{ r.current_phase }}, {{ r.completed_count }}/{{ r.total_phases }} done
  Last paused: *"{{ r.exit_reason }}"*
  *Resume via `resume_workflow(workflow_id="{{ r.workflow_id }}", resume_reason="…")`*
{% endfor %}
{% endif %}

{% if workflow_description is defined and workflow_description %}
## Active Workflow ({{ active_workflow_id }})
<WorkflowDescription>
{{ workflow_description }}
</WorkflowDescription>
<WorkflowStatus>
{{ workflow_status | default("Just entered.") }}
</WorkflowStatus>
<WorkflowNextStepGuidance>
{{ workflow_nextstep_guidance | default("Take the first action defined by Phase 0.") }}
</WorkflowNextStepGuidance>

*To pause this workflow, call `exit_workflow(exit_reason="…")`.*
{% endif %}

## Workflow Decision (read every turn)
1. If the user's request fits the **Active Workflow**, follow `<WorkflowNextStepGuidance>`.
2. If the user's request fits a **different** Available Workflow, exit the active
   one (if any) then `enter_workflow`.
3. If the user wants to continue a previously paused workflow listed under
   **Ongoing Workflows**, exit current (if any) then `resume_workflow`.
4. If the request is ad-hoc/conversational, answer directly without entering a
   workflow.
5. Never have two workflows running at once.
```

(The `## Available Tools` block is unchanged.)

### 3.7 Why Not Make Workflow a "Skill"?

Skills today are **declarative metadata bundles** of tools — they have no state
machine, no phase tracker, no entry/exit lifecycle. Forcing workflows into
SKILL.md would:

- conflate two orthogonal concerns (knowledge vs. procedure),
- bloat SKILL.md frontmatter with phase definitions,
- break the `role_skill_routes.py` contract that skills are role-assembly
  primitives, not session-runtime primitives.

Workflows therefore get their **own resource directory** (`resources/workflows/`)
and **own registry**, parallel to tools and skills. (A future skill *can*
declare in its frontmatter that it "owns" a workflow, the same way it declares
tools — that's the integration point if we ever want skill-defined workflows.)

---

## 4. On-Disk Schema (Concrete)

### 4.1 `resources/workflows/<name>/workflow.json`

```jsonc
{
  "name": "openstartup_orchestrator",
  "version": "1.0.0",
  "short_description": "Create, set up, and onboard an AI employee role end-to-end (4 phases).",
  "long_description_file": "description.jinja2",
  "sop_file": "sop.jinja2",
  "sop_config_file": ".sop.config.yaml",
  "entry_phase": "0",
  "terminal_phases": ["3"],
  "category": "orchestration",
  "tags": ["onboarding", "role-design"],
  "required_tools": ["create_role", "role_setup"],
  "default_strategy": "default"
}
```

`required_tools` is a SOFT precondition: at workflow registration time we
verify these exist in the tool registry; missing tools downgrade the workflow
to a `degraded` listing in `available_workflows` (rendered with a warning
suffix `(unavailable: missing tools …)`). The agent will not be presented with
unavailable workflows in the catalog by default.

### 4.2 `resources/workflows/<name>/description.jinja2`

A short blurb for the catalog listing (≤ 200 words). Renders with the
existing template variables (employee, etc.) so it can adapt to the role.

### 4.3 `resources/workflows/<name>/sop.jinja2`

The same SOP format used today (markdown + structured Phase headers with
`__depends on__`, `__requires confirmation__`, `Tools[__must__]:`). **No format
change** — we keep `SOPManager` intact.

### 4.4 `resources/workflows/<name>/.sop.config.yaml`

Same as today; per-SOP subsection directives.

### 4.5 Migration of the Existing OpenStartup SOP

| Today | After |
|-------|-------|
| `prompt_templates/conversation/main/_variables/workflow_description/default.jinja2` | `resources/workflows/openstartup_orchestrator/description.jinja2` (verbatim move) |
| `prompt_templates/conversation/main/_variables/workflow/sop.jinja2` | `resources/workflows/openstartup_orchestrator/sop.jinja2` (verbatim move) |
| `prompt_templates/conversation/main/_variables/workflow/.sop.config.yaml` | `resources/workflows/openstartup_orchestrator/.sop.config.yaml` (verbatim move) |
| (no manifest) | `resources/workflows/openstartup_orchestrator/workflow.json` (new) |

The `_variables/workflow*/` directories are **kept empty** but not deleted, to
preserve the variable_manager's slot resolver as a fallback.

---

## 5. Data Model — Python Types

A new module `server/workflows/__init__.py` houses:

```python
# server/workflows/definition.py
@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: str
    short_description: str
    long_description: str          # rendered description.jinja2
    sop_path: Path                  # absolute path to sop.{ext}
    sop_config_path: Path | None
    entry_phase: str
    terminal_phases: list[str]
    required_tools: list[str]
    default_strategy: str
    available: bool = True          # False if required_tools missing
    unavailability_reason: str = ""

# server/workflows/registry.py
class WorkflowRegistry:
    def __init__(self, workflows_dir: Path, tool_registry: dict): ...
    def reload(self) -> None: ...
    def get(self, name: str) -> WorkflowDefinition | None: ...
    def list(self, *, include_unavailable: bool = False) -> list[WorkflowDefinition]: ...

# server/workflows/run.py
@dataclass
class WorkflowRun:
    workflow_id: str                # "wf-<8 hex>"
    definition_name: str
    status: str                     # "running" | "paused" | "completed" | "aborted"
    workflow_context: WorkflowContext   # AF dataclass; ONE per run
    created_at: float
    updated_at: float
    entry_reason: str = ""
    exit_reason: str = ""

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowRun": ...

# server/workflows/state.py
@dataclass
class WorkflowSessionState:
    active_workflow_id: str | None = None
    runs: dict[str, WorkflowRun] = field(default_factory=dict)

    def active_run(self) -> WorkflowRun | None: ...
    def paused_runs(self) -> list[WorkflowRun]: ...
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowSessionState": ...
```

The session JSON shape changes from:

```jsonc
// BEFORE
{
  "id": "...",
  "workflow_context": { /* WorkflowContext.to_dict() */ }
}
```

to:

```jsonc
// AFTER
{
  "id": "...",
  "workflow_state": {
    "active_workflow_id": "wf-abc12",
    "runs": {
      "wf-abc12": {
        "workflow_id": "wf-abc12",
        "definition_name": "openstartup_orchestrator",
        "status": "running",
        "workflow_context": { /* WorkflowContext.to_dict() */ },
        "created_at": 1746704000.0, "updated_at": 1746704321.0,
        "entry_reason": "User asked to create a Program Manager role.",
        "exit_reason": ""
      },
      "wf-xyz98": {
        "workflow_id": "wf-xyz98",
        "definition_name": "team_onboarding",
        "status": "paused",
        ...,
        "exit_reason": "User wanted to first finalize the role document."
      }
    }
  },
  // legacy field kept readable but no longer written:
  "workflow_context": null
}
```

A migration shim in `session_store._backfill_workflow_context` upconverts old
sessions: if `workflow_context` exists and `workflow_state` is missing, wrap
the old WC into a single `WorkflowRun` with `workflow_id="wf-legacy"`,
`definition_name="openstartup_orchestrator"`, `status="running"`.

---

## 6. Implementation Plan — Phased

Dependency-ordered. Each phase is independently testable and shippable.

### Phase A — Foundations (no behavior change)

**Objective:** introduce the new types + registry + on-disk layout without
flipping any runtime behavior. The system still uses the legacy single-SOP
path; new code is dormant.

**Files (create):**
- `src/openteam/server/workflows/__init__.py`
- `src/openteam/server/workflows/definition.py` (`WorkflowDefinition`)
- `src/openteam/server/workflows/registry.py` (`WorkflowRegistry`)
- `src/openteam/server/workflows/run.py` (`WorkflowRun`)
- `src/openteam/server/workflows/state.py` (`WorkflowSessionState`)
- `src/openteam/server/resources/workflows/openstartup_orchestrator/workflow.json`
- `src/openteam/server/resources/workflows/openstartup_orchestrator/description.jinja2` (copy)
- `src/openteam/server/resources/workflows/openstartup_orchestrator/sop.jinja2` (copy)
- `src/openteam/server/resources/workflows/openstartup_orchestrator/.sop.config.yaml` (copy)
- `test/openteam/server/workflows/test_registry.py`
- `test/openteam/server/workflows/test_run_state.py`

**Files (modify):**
- `src/openteam/server/main.py` — instantiate `WorkflowRegistry` at startup,
  pass to `ConversationService` constructor (new optional kwarg).
- `src/openteam/server/services/conversation_service.py` — accept
  `workflow_registry` kwarg, store but don't use yet.

**Tests:** registration round-trip, manifest validation, missing-tool
degradation, run state machine transitions in isolation.

**Acceptance criteria:**
- Existing conversation tests still pass (Phase A is invisible to runtime).
- `pytest test/openteam/server/workflows/` is green.

---

### Phase B — Per-Run Workflow State in Sessions (no UX change yet)

**Objective:** start storing `workflow_state` in sessions; keep prompt rendering
behaviorally identical (we render the `active` run's state into the same
variables as before).

**Files (modify):**
- `src/openteam/server/services/session_store.py`
  - `_default_workflow_state()` returns `WorkflowSessionState` with one run
    auto-created for `openstartup_orchestrator` (matches today's UX).
  - `_backfill_workflow_state()` migrates old `workflow_context` sessions.
  - New API: `update_workflow_state(session_id, dict)`.
  - Legacy `update_workflow_context(...)` becomes a thin shim that finds the
    active run and updates its embedded `workflow_context`.

- `src/openteam/server/services/conversation_service.py`
  - `_compute_session_context(session)` reads `session["workflow_state"]`,
    pulls the **active run's** `workflow_context`, returns the same keys as
    today (`workflow_description`, `workflow_status`, `current_phase`, …) +
    one new key: `active_definition_name` (used by `find_sop_file` change).
  - `_persist_workflow_updates(session, prior_context, …)` writes back into
    the active run's `workflow_context`, then through `update_workflow_state`.

- `src/openteam/server/services/conversation_service.py::_SimplePromptRenderer.find_sop_file`
  - Accept optional `definition_name`; if given, look in
    `resources/workflows/<name>/sop.{ext}`; else legacy fallback.

- `agent_foundation/.../conversational/prompt_rendering.py` (or local override
  via subclass to avoid forking AF):
  - `sop_path = self.prompt_renderer.find_sop_file(self.prior_context.get("active_definition_name"))`

**Tests:**
- Backward-compat: a freshly created session ends up with one running
  `openstartup_orchestrator` run, prompt looks identical to today.
- Migration: an old session JSON with only `workflow_context` is read,
  upconverted, re-saved with `workflow_state`.

**Acceptance criteria:**
- All existing E2E conversation tests pass without prompt content diffs (modulo
  the new `active_workflow_id` line in `## Active Workflow (...)` header which
  we can choose to suppress in this phase).

---

### Phase C — Catalog & Ongoing Workflows in Prompt

**Objective:** add the two new prompt sections; agent can SEE the catalog but
not yet *control* it.

**Files (modify):**
- `src/openteam/server/resources/prompt_templates/conversation/main/initial.jinja2`
  - Insert "Workflow Catalog" / "Available Workflows" / "Ongoing Workflows"
    blocks per §3.6.
  - Move the existing `<WorkflowDescription>/Status/Guidance>` trio under a new
    `## Active Workflow ({{ active_workflow_id }})` heading, guarded the same way.

- `src/openteam/server/services/conversation_service.py::_compute_session_context`
  - Compute `available_workflows`, `ongoing_workflows`, `active_workflow_id`
    keys from `WorkflowSessionState` + `WorkflowRegistry`.
  - For each ongoing run, also compute display fields (`current_phase`,
    `completed_count`, `total_phases`, `exit_reason`) — derived but cached
    once per turn.

**Tests:**
- Render snapshot test with 0 paused runs + 1 active = matches "Workflow
  Catalog" + "Active Workflow" sections.
- Render snapshot test with 2 paused runs + 0 active = matches catalog +
  ongoing section but NO active section.

**Acceptance criteria:**
- Manual smoke: a fresh session starts with 1 running run; prompt shows
  catalog (1 entry), active (1 entry), ongoing (empty).

---

### Phase D — Workflow Control Tools (`enter_workflow`, `exit_workflow`, `resume_workflow`)

**Objective:** make the agent able to switch workflows.

**Files (create):**
- `src/openteam/server/resources/tools/enter_workflow/tool.json`
- `src/openteam/server/resources/tools/enter_workflow/executor.py`
- `src/openteam/server/resources/tools/exit_workflow/tool.json`
- `src/openteam/server/resources/tools/exit_workflow/executor.py`
- `src/openteam/server/resources/tools/resume_workflow/tool.json`
- `src/openteam/server/resources/tools/resume_workflow/executor.py`
- `test/openteam/server/resources/tools/test_workflow_control_tools.py`

**Files (modify):**
- `src/openteam/server/resources/prompt_templates/conversation/main/.initial.config.yaml`
  - Add `enter_workflow`, `exit_workflow`, `resume_workflow` to
    `enabled_action_tools`.

- `src/openteam/server/services/tool_dispatcher.py`
  - The dispatcher needs access to (a) the `WorkflowRegistry` and
    (b) the current session's `workflow_state` to validate calls. Option:
    inject `workflow_registry` and `session` accessor at dispatcher init,
    similar to how `_interactive` is injected per-turn.

- `src/openteam/server/services/conversation_service.py`
  - When applying `context_updates`, special-case `workflow_state` and
    `_active_workflow_changed`. The latter triggers
    `inferencer.prior_context.pop("_sop", None); pop("tool_phase_map", None)`
    so the next turn re-derives them from the new active run's SOP.

**Executor sketch (enter_workflow):**

```python
# tools/enter_workflow/executor.py
async def execute(name: str, entry_reason: str, *,
                  _workflow_registry, _workflow_state) -> ToolExecutionResult:
    if _workflow_state.active_workflow_id is not None:
        return ToolExecutionResult.error(
            f"Cannot enter '{name}': workflow {_workflow_state.active_workflow_id} "
            "is already active. Call exit_workflow first."
        )
    defn = _workflow_registry.get(name)
    if defn is None or not defn.available:
        return ToolExecutionResult.error(f"Workflow '{name}' is not available.")
    run = WorkflowRun(
        workflow_id=_new_workflow_id(),
        definition_name=name,
        status="running",
        workflow_context=WorkflowContext(
            workflow_description=defn.long_description,
            strategy=defn.default_strategy,
        ),
        created_at=time.time(), updated_at=time.time(),
        entry_reason=entry_reason[:200],
    )
    _workflow_state.runs[run.workflow_id] = run
    _workflow_state.active_workflow_id = run.workflow_id
    return ToolExecutionResult.ok(
        summary=f"Entered workflow '{name}' (id={run.workflow_id}).",
        context_updates={
            "workflow_state": _workflow_state.to_dict(),
            "_active_workflow_changed": True,
        },
    )
```

**Tests:**
- Enter when no active → success, active_workflow_id set.
- Enter when active exists → error.
- Exit active → status=paused, active=None, run still in registry.
- Resume paused → status=running, active=workflow_id.
- Resume non-existent → error.
- Resume completed → error.
- Two-step enter → exit → enter different workflow → both runs persisted, only
  second one active.

**Acceptance criteria:**
- Manual scenario: agent in `openstartup_orchestrator` Phase 1 → user asks
  "actually pause this and let's onboard the new team first" → agent emits
  `exit_workflow` then `enter_workflow(name="team_onboarding")` → next turn
  catalog shows `team_onboarding` as active and `openstartup_orchestrator` as
  paused with correct phase preserved.

---

### Phase E — Persistence, Backward-Compat & Cleanup

**Objective:** make the changes durable across restarts; remove dead code.

**Files (modify):**
- `src/openteam/server/services/session_store.py`
  - Drop write of legacy `workflow_context` field (keep read for backfill).
  - `delete_session` cleans up workflow runs.

- `src/openteam/server/services/conversation_service.py::evict_session_inferencer`
  - Also drop any cached SOP for this session.

- `src/openteam/server/resources/prompt_templates/conversation/main/.initial.config.yaml`
  - Update `structural_xml_tags` if we add new XML wrappers.

- `src/openteam/server/resources/prompt_templates/conversation/main/_variables/workflow*/`
  - Empty out (keep dirs for compat fallback). Add a `README.md` noting
    "kept for fallback only — new workflows live in resources/workflows/".

**Tests:**
- Restart sim: persist a session with 2 runs (1 active, 1 paused), reload
  ConversationService, verify `_compute_session_context` rebuilds identical
  prior_context.

**Acceptance criteria:**
- Old sessions continue to work (backfill).
- New sessions have only `workflow_state` field.
- `pytest test/openteam` is green; no flaky regression.

---

### Phase F (stretch) — Multiple Workflow Definitions

**Objective:** prove value by adding a second workflow.

**Files (create):**
- `src/openteam/server/resources/workflows/team_onboarding/{workflow.json,description.jinja2,sop.jinja2,.sop.config.yaml}`
  - Implements the Phase 3 / `/team-onboard` content currently embedded in the
    big SOP. Promotes it to a standalone workflow that can be entered without
    going through Phases 0–2.

**Tests:**
- Catalog now lists 2 workflows.
- Agent can enter `team_onboarding` directly from a fresh session.

---

## 7. Critical-Thinking Risk Register

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | LLM "thrashes" between workflows (enters/exits repeatedly within a turn). | 🔴 High | (a) Add prompt rule: "do not switch workflows more than once per turn"; (b) tool dispatcher counts switch calls per turn and rejects 3rd+; (c) put `_active_workflow_changed` rate-limiting in `ConversationService`. |
| R2 | Persisting `_sop` (the parsed SOP object) into `prior_context` is not JSON-serializable, but `_persist_workflow_updates` reads `prior_context`. | 🔴 High | Already a problem today. Mitigated by: (a) keys starting with `_` are excluded from persistence in `_persist_workflow_updates` (add a one-line filter); (b) `find_sop_file` re-runs every turn anyway, so caching is per-inferencer-instance, not per-session-on-disk. |
| R3 | Race: a second turn arrives before persistence of the first. WorkflowContext divergence. | 🟡 Medium | The per-session inferencer dict (already implemented) serializes turns. If we add concurrent turn support later, wrap turn processing in an asyncio Lock per session_id. |
| R4 | Agent enters a workflow whose SOP requires tools that aren't enabled for this user/role. | 🟡 Medium | `WorkflowDefinition.required_tools` validated at registry load AND at enter time (executor double-checks against current tool whitelist). |
| R5 | Old sessions on disk break after migration. | 🟡 Medium | `_backfill_workflow_state` covers the upconvert; cover with a unit test fixture matching the *exact* old shape. Snapshot test across at least 3 vintage shapes (pre-workflow_context, with workflow_context but no strategy, with all fields). |
| R6 | The SOP cache invalidation via `_active_workflow_changed` leaks if a tool returns the sentinel but no actual change happens (false positive). | 🟠 Low-Med | Make `_active_workflow_changed` strictly produced by the three workflow-control tools. Other tools cannot set it; we add an assertion in the dispatcher's `apply_context_updates` effect. |
| R7 | `WorkflowContext` field semantics drift between AF and OpenStartup uses (e.g., `task_queue` is rankevolve-only but present in AF). | 🟠 Low-Med | Use AF's leaner version; never write into `task_queue` from OpenStartup. Add a docstring note. |
| R8 | Render snapshot tests become brittle as catalog grows. | 🟠 Low | Use template fragment snapshots, not full-prompt snapshots; assert structural presence/absence rather than exact text. |
| R9 | UX surprise: user expects the OpenStartup orchestrator to "just run" but sees a catalog they have to choose from. | 🟡 Medium | Phase B keeps auto-entry of `openstartup_orchestrator` for fresh sessions. Catalog still appears in the prompt but UI can hide it from users initially; the agent uses it. |
| R10 | Unbounded growth of paused/completed runs in `workflow_state.runs`. | 🟠 Low | Cap at 10 runs per session; oldest aborted/completed evicted first. |

## 8. Open Design Questions (To Resolve Before Coding)

1. **Run identity scope.** `workflow_id` is session-local per current design. Do
   we need globally unique IDs (across sessions) for cross-session reporting?
   *Recommendation:* keep session-local for now; UUIDs available later via
   `f"{session_id}:{workflow_id}"` composite if needed.

2. **Where does `tool_dispatcher` get `_workflow_state` from?** Two options:
   (a) inject reference to a mutable `WorkflowSessionState` per-turn (mirrors
   `_interactive` injection); (b) have the executor read it from
   `prior_context["workflow_state"]` and write back via `context_updates`.
   *Recommendation:* option (b) — keeps tools pure, no new injection plumbing,
   reuses the `context_updates` channel. The executor reconstructs
   `WorkflowSessionState.from_dict(prior_context["workflow_state"])`.

3. **Default behavior of fresh session.** Auto-enter `openstartup_orchestrator`
   (current UX) vs. start with empty active and let agent choose?
   *Recommendation:* keep auto-enter for backward compat in Phase B; add a
   server config flag `default_workflow` (default = `"openstartup_orchestrator"`,
   `None` = no auto-enter) for future.

4. **Should `enter_workflow` accept arbitrary `initial_context`?** E.g., the
   agent may want to pass a `role_description` already collected before
   entering. *Recommendation:* yes, optional `initial_context: dict` arg that
   seeds the new run's `WorkflowContext.phase_outputs`.

5. **UI surface.** Does the chat UI need a "Workflow" tab showing runs and
   allowing manual enter/exit? *Recommendation:* out of scope for this plan;
   this is a server-side change. UI work is a follow-up.

6. **Telemetry.** How do we measure workflow switching behavior in production?
   *Recommendation:* emit JSONL events from each control tool execution
   (`workflow_entered`, `workflow_exited`, `workflow_resumed`) into the existing
   per-turn `JsonLogger`.

7. **Should completed workflows be visible to the agent?** Today they're
   stored. *Recommendation:* hide by default in `ongoing_workflows`; expose
   via a separate `completed_workflows` variable that the prompt only renders
   on user demand (e.g., via a `list_workflow_history` read-only tool).

## 9. Mapping the User's Request → This Plan

| User's intent (verbatim or paraphrased) | Where addressed |
|---|---|
| "Investigate how conversational inferencer currently supports SOP flow." | §2 (Investigation Findings — files, classes, line refs) |
| "We want the conversation not fixated to one workflow, it can enter/exit a workflow." | §3.3 (Lifecycle), §3.4 (3 control tools) |
| "Workflow maybe just like a tool or skill." | §3.7 (peer concept rationale) + §4 (on-disk schema mirroring tool/skill) |
| "It has its place in the prompt, so the agent decides on its own when to enter and when to exit." | §3.4 (tools surfaced in `## Available Tools`), §3.6 (`## Workflow Decision` block guides decisioning) |
| "The workflow is stateful, so you can exit half way and you can re-enter." | §3.3 (paused state preserves `WorkflowContext`); §5 (per-run `WorkflowContext`) |
| "Every running workflow needs to have a workflow id." | §3.1 (`WorkflowRun.workflow_id`); §5 (`wf-<8 hex>`) |
| "Variable mechanism is not sufficient — workflow is parallel things to skills and tools." | §2.4 (showing why slot-fill is the chokepoint), §3.1 (own registry, own resource directory), §4 (own schema). |
| "When we enter a workflow, the prompt will have all its current support of workflow things." | §3.2 (active block keeps existing `<WorkflowDescription>/Status/Guidance>` trio) |
| "Once it exits, those things are gone, but prompt still shows available workflows and ongoing workflows." | §3.2 (catalog vars always shown), §3.6 (template skeleton). |
| "Help think it through." | §7 (risks), §8 (open questions). |

## 10. Out-of-Scope (Explicit Defer List)

- UI for workflow management (chat-side tab, badges, manual control buttons).
- Cross-session workflow handoff and workflow IDs that are globally unique.
- Workflow composition / nested workflows.
- Workflow versioning (running the same definition at version 1.0 and 2.0
  side-by-side). Today: latest version wins; runs reference name only.
- A/B testing of SOPs via routing rules.

## 11. Quick-Glance Summary for the Reviewer

> We add a third resource type `Workflow` to peer with `Tool` and `Skill`. A
> session can have multiple workflow runs (each with its own ID and
> `WorkflowContext`); the prompt always lists the catalog of available
> workflows and any paused ongoing runs, plus the active workflow's
> description/status/guidance trio when one is active. The agent enters,
> exits, and resumes via three new ordinary action tools, going through the
> same `ToolsToInvoke` channel it already uses for `create_role` and
> `role_setup`. Backward-compat is preserved by auto-entering the existing
> `openstartup_orchestrator` workflow on fresh sessions and by an upconvert
> shim for old `workflow_context` session JSON. Implementation is six phases,
> each independently shippable; the chokepoint is the single-line change to
> `find_sop_file()` to accept a `definition_name`.

