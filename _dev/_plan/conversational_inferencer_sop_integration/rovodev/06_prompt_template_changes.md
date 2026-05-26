# Chapter 6 — F6: Prompt Template Changes (Available SOPs · Active SOP · Running Background Jobs · YOLO)

> **Implements:** F6 from `README.md`
> **Depends on:** F3 (background jobs for the running-jobs section), F4 (YOLO), F5 (SOP registry & state)
> **Touches:** `resources/prompt_templates/conversation/main/initial.jinja2` and its `_variables/`

---

## 1. Goal

Augment the conversational inferencer's main Jinja2 template with FOUR
additive sections, fully backward-compatible with existing rendering:

| Section | When shown | What it contains |
|---------|------------|------------------|
| `## Available SOPs` | Always, when `available_sops` non-empty | List of SOP definitions with phases, vars, must-gate warning, entry commands. |
| `## Active SOP` | Only when `active_sop` is set | Active SOP name + run_id; existing `<WorkflowDescription>` / `<WorkflowStatus>` / `<WorkflowNextStepGuidance>` blocks scoped to it. |
| `## Running Background Jobs` | Only when `running_background_jobs` non-empty | Live job IDs, status, ETA, last output tail, "view at" hints. |
| `## Execution Mode: YOLO (Headless)` | Only when `yolo_mode == True` | Behavior contract for headless runs (chapter 4 §3.5). |

The existing `## Workflow Context` block (which already wraps the active SOP's
description/status/guidance) is repurposed under `## Active SOP`.

---

## 2. The Final Template Layout

```jinja2
{# 1. Employee identity (existing) #}
{% if employee is defined %}
You are **{{ employee.name }}**, serving as **{{ employee.role }}**.
{{ employee.mindset }}
{% endif %}

{# 2. YOLO mode contract (NEW — chapter 4) #}
{% if yolo_mode is defined and yolo_mode %}
## Execution Mode: YOLO (Headless)
You are running headless without a human attendant. Adjust your style:
- DO NOT ask clarifying questions; do not propose alternatives.
- DO NOT use `confirmation`, `clarification`, `single_choice`, `multiple_choice`
  for non-mandatory gates. The system auto-resolves them on your behalf.
- DO use these conversation tools when a mandatory gate (`[__must__]`)
  is reached — the system will surface them to a supervisor.
- Keep your `<Response>` blocks terse and factual; they are written to a log.
- Prefer ACTION tools over CONVERSATION tools.
- On terminal SOP completion, emit a final `<Response>` containing a
  one-paragraph summary of what was done and any artifacts produced.
{% endif %}

{# 3. Available SOPs catalog (NEW — chapter 5) #}
{% if available_sops is defined and available_sops %}
## Available SOPs

The following Standard Operating Procedures (SOPs) are available. You may
enter one when the user's request matches its purpose; you may exit the
active one at any time.

{% for sop in available_sops %}
- **{{ sop.name }}** — {{ sop.title }}
{%- if sop.description %}
  - {{ sop.description }}
{%- endif %}
  - Phases: {{ sop.phases | join(' → ') }}
{%- if sop.variables %}
  - Variables: {{ sop.variables | join(', ') }}
{%- endif %}
{%- if sop.required_variables %}
  - Required: {{ sop.required_variables | join(', ') }}
{%- endif %}
{%- if sop.has_must_gates %}
  - ⚠ Contains `[__must__]` gates — pauses for user input even in YOLO mode.
{%- endif %}
  - Enter in this conversation: `/enter-sop {{ sop.name }}`
  - Launch as autonomous background subprocess: `/sop {{ sop.name }}`
{% endfor %}

### How to choose an SOP
- If the user describes a goal that matches one of the above, suggest `/enter-sop <name>` and explain why.
- If multiple SOPs match, present a `single_choice` to the user.
- If no SOP matches, proceed without entering one (ad-hoc mode).
- An SOP can be exited via `/exit-sop`; its state is preserved and can be re-entered later.
{% endif %}

{# 4. Active SOP block (existing Workflow Context, scoped — chapter 5) #}
{% if active_sop is defined and active_sop %}
## Active SOP: {{ active_sop.name }}

Run ID: `{{ active_run_id | default('?') }}`
{% if workflow_target_path is defined and workflow_target_path %}
You operate on `{{ workflow_target_path }}` under repository `{{ session_root_path | default("(not set)") }}`.
{% endif %}

<WorkflowDescription>
{{ workflow_description | default("(no description)") }}
</WorkflowDescription>

<WorkflowStatus>
{{ workflow_status | default("(no status)") }}
</WorkflowStatus>

<WorkflowNextStepGuidance>
{{ workflow_nextstep_guidance | default("(no guidance — respond to user request directly)") }}
</WorkflowNextStepGuidance>

{% if active_sop.has_must_gates %}
**Note:** This SOP contains mandatory user-input gates marked `[__must__]`.
{% if yolo_mode %}In YOLO mode, those gates will halt execution and surface to a supervisor.{% endif %}
{% endif %}

To exit this SOP without completing it: `/exit-sop --reason "<short reason>"`.
{% endif %}

{# 5. Running Background Jobs (NEW — chapter 3) #}
{% if running_background_jobs is defined and running_background_jobs %}
## Running Background Jobs

The following jobs are running in the background. You will be notified via a
`[Background job completed]` system message when each one finishes — do NOT
wait for them; continue handling the user's current request.

{% for job in running_background_jobs %}
- `{{ job.id }}` — **{{ job.kind }}**: `{{ job.cmdline_short }}`
  - Status: {{ job.status }}{% if job.schedule.mode != 'once' %} (schedule: {{ job.schedule.mode }} every {{ job.schedule.every_seconds }}s, completed {{ job.schedule.runs_completed }} so far){% endif %}
  - Workspace: `{{ job.workspace }}`
{%- if job.last_output_tail %}
  - Last output: `{{ job.last_output_tail | truncate(120) }}`
{%- endif %}
{% if job.fork_on_completion %}
  - ⚙ Will fork conversation on completion.
{% endif %}
{% endfor %}

If a job appears stuck, you can:
- Inspect its workspace files for details.
- Cancel via `/background-job-cancel {{ running_background_jobs[0].id }}` (replace ID).
{% endif %}

{# 6. Available Tools (existing) #}
## Available Tools
{% if action_tools is defined and action_tools %}
### Action Tools
{{ action_tools }}
{% endif %}
{% if conversation_tools is defined and conversation_tools %}
### Conversation Tools (structured input collection only)
{{ conversation_tools }}
{% endif %}

{# 7. Conversation history (existing) #}
## Conversation
<Conversation>
 <PreviousTurns>
{% for history_turn in conversation_history %}
  <{{ history_turn.role }}>{{ history_turn.content }}</{{ history_turn.role }}>
{% endfor %}
 </PreviousTurns>
 <CurrentTurn>
  <{{ current_turn.role }}>{{ current_turn.content }}</{{ current_turn.role }}>
 </CurrentTurn>
</Conversation>

{# 8. Decision Procedure (existing — extended slightly for SOP awareness) #}
## Decision Procedure

Before responding, reason through these steps silently:
1. **Classify the user's latest message:**
   - (a) **SOP-aligned** — the user's request matches the Active SOP's next step (if any) OR matches an Available SOP they should enter.
   - (b) **Workflow-aligned without SOP** — request advances an active workflow but doesn't match an SOP.
   - (c) **Ad-hoc action** — outside any workflow/SOP (e.g., "search for X", "run Y").
   - (d) **Conversational** — greeting, conceptual question, chitchat.
2. **If (a) and Active SOP is set:** Diff `<WorkflowStatus>` against `<WorkflowNextStepGuidance>` carefully. Execute remaining sub-steps only. If complete, ask whether to proceed to next phase or exit SOP.
3. **If (a) and no Active SOP but a matching Available SOP exists:** Suggest `/enter-sop <name>` with a short rationale; OR enter it directly if the user clearly intended to.
4. **If (b)/(c):** Fulfill the request; if relevant, remind the user where any paused/active workflow left off.
5. **If (d):** Respond in natural language only.
6. **At all times:** Read `## Running Background Jobs` and acknowledge any completed/failed jobs in your reasoning (their `[Background job completed]` system messages also appear in conversation history).
7. **If a tool call fails:** Report the error clearly, suggest a fix, do not silently retry more than once.

{# 9. Response Format (existing) #}
## Response Format
{# ...unchanged from current template... #}
```

---

## 3. Template Variable Contracts

`_render_prompt` in `ConversationalInferencer` passes the template these
NEW variables in addition to today's:

```python
template_vars = {
    # Existing
    "employee": ...,
    "workflow_description": ...,           # (now sourced from active_sop)
    "workflow_status": ...,
    "workflow_nextstep_guidance": ...,
    "workflow_target_path": ...,
    "session_root_path": ...,
    "action_tools": ...,
    "conversation_tools": ...,
    "conversation_history": ...,
    "current_turn": ...,

    # NEW
    "yolo_mode": self.yolo_mode,
    "available_sops": self.sop_registry.list() if self.sop_registry else [],
    "active_sop": self._active_sop_definition(),
    "active_run_id": self.prior_context.get("active_run_id"),
    "running_background_jobs": _format_running_jobs(
        JobManager.instance().list_running(session_id=self._session_id)
    ),
}
```

`_format_running_jobs` produces dicts shaped for the template:

```python
def _format_running_jobs(jobs: list[BackgroundJob]) -> list[dict]:
    return [
        {
            "id": j.id,
            "kind": j.kind.value,
            "cmdline_short": " ".join(j.cmdline)[:100],
            "status": j.status.value,
            "workspace": str(j.workspace),
            "last_output_tail": j.last_output_tail,
            "schedule": {
                "mode": j.schedule.mode,
                "every_seconds": j.schedule.every_seconds,
                "runs_completed": j.schedule.runs_completed,
            },
            "fork_on_completion": j.fork_on_completion,
        }
        for j in jobs
    ]
```

Crucially, **completed jobs do NOT appear in this list** — they have already
been routed via input-queue `BackgroundJobComplete` items, which become
`[Background job completed]` synthetic messages in `conversation_history`.
The Running list is "live only".

---

## 4. Backward Compatibility

| Variable | Existing template behavior | New template behavior |
|----------|---------------------------|------------------------|
| `workflow_description` | Always shown wrapped in `## Workflow Context` | Now shown ONLY inside `## Active SOP` (which requires `active_sop` set). If `active_sop` is unset but `workflow_description` is set (legacy), template falls back to today's layout. |
| `workflow_status`, `workflow_nextstep_guidance` | Same | Same fallback rule. |
| Everything else | Unchanged | Unchanged |

Fallback block (appended after the `## Active SOP` block) to preserve
legacy behavior:

```jinja2
{# Legacy fallback: workflow_description set but no active_sop (pre-SOP-registry sessions) #}
{% if (active_sop is not defined or not active_sop)
      and workflow_description is defined and workflow_description %}
## Workflow Context (legacy)
<WorkflowDescription>{{ workflow_description }}</WorkflowDescription>
<WorkflowStatus>{{ workflow_status | default("") }}</WorkflowStatus>
<WorkflowNextStepGuidance>{{ workflow_nextstep_guidance | default("") }}</WorkflowNextStepGuidance>
{% endif %}
```

This keeps the existing OpenStartup orchestrator SOP working unchanged
until it's migrated to use the SOP registry.

---

## 5. Token Budget Considerations

The new sections add (worst case):

| Section | Approx tokens |
|---------|---------------|
| Available SOPs (5 SOPs × 8 lines each) | ~300 |
| Active SOP framing (excluding the existing description blocks) | ~50 |
| Running Background Jobs (5 jobs × 5 lines each) | ~250 |
| YOLO contract | ~150 |
| **Total worst case** | ~750 tokens |

For a typical conversation with prompt budget ~16k tokens, this is <5%.
Acceptable. The existing `_compress_context_if_needed` handles overflow
in dynamic context; static prompt sections aren't compressed (intentionally
— they're the agent's "operating system").

If the SOP registry grows beyond ~10 entries, switch to a paginated /
categorized rendering. For now, a flat list is fine.

---

## 6. UI Implications

The chat frontend (React widgets — already analyzed in
`/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/_plan/review_proposal_implementation/analysis/`)
gains complementary surface area:

| UI change | Trigger | Renders |
|-----------|---------|---------|
| Background-jobs panel | `running_background_jobs` non-empty on any turn | Sidebar with live job cards (poll JobManager API every 2s for status refresh). |
| Job completion toast | `BackgroundJobComplete` queue item arrives | Pill notification + optional auto-scroll to the synthetic `[Background job completed]` chat message. |
| SOP selector in chat input | `available_sops` non-empty | Slash-command autocompletion suggests `/enter-sop <name>` and `/sop <name>` when the user types `/`. |
| Active-SOP breadcrumb | `active_sop` set | Header chip showing SOP name + phase; click to view full guidance. |
| YOLO indicator | `yolo_mode=True` (subprocess view) | Red "HEADLESS" banner. |

UI work is **out of scope** for this plan (covered separately in a future
`review_proposal_implementation` follow-up), but the backend exposes the
needed signals.

---

## 7. Migration Path for Existing SOPs

Existing SOP files in `_variables/workflow_sop/`:
- `code_optimization.md` ✓ already uses `__must__` markers
- `model_optimization.jinja2` — audit for must-gate annotations
- `role_creation.jinja2` — audit

Migration steps:
1. Rename SOP files to match canonical IDs (already done).
2. Add a one-paragraph `## Description` block at the top of each SOP file
   for the registry to extract (`SOPRegistry._extract_title_desc`).
3. (Optional) Add a `<!-- sop-meta required_vars: x,y,z -->` HTML comment
   that the registry parses to populate `required_variables` more precisely.

---

## 8. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` | REWRITE per §2 above. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` | Augment `_render_prompt` to pass new template vars. Add `_format_running_jobs`, `_active_sop_definition` helpers. |
| `agent_foundation/common/sop/registry.py` | Add `_extract_title_desc` helper (used at SOP-load time). |
| Existing SOP files (`code_optimization.md`, etc.) | Add `## Description` paragraphs (one-line each). |
| `tests/agent_foundation/.../conversational/test_prompt_rendering.py` | NEW tests for each conditional section. |

---

## 9. Test Plan

| # | Test | Type |
|---|------|------|
| T6.1 | Template renders nothing of the new sections when all vars absent (backward compat) | Unit (snapshot) |
| T6.2 | `available_sops` populated → `## Available SOPs` block present, contains all entries | Unit |
| T6.3 | `active_sop` set → `## Active SOP` block present, contains workflow framing | Unit |
| T6.4 | `running_background_jobs` non-empty → `## Running Background Jobs` block present | Unit |
| T6.5 | `yolo_mode=True` → YOLO contract block present | Unit |
| T6.6 | Legacy `workflow_description` (no active_sop) → fallback block renders | Unit |
| T6.7 | `cmdline_short` truncates to 100 chars | Unit |
| T6.8 | Completed job (status=DONE) does NOT appear in running list | Unit |
| T6.9 | Active SOP `has_must_gates=True` → ⚠ note appears | Unit |
| T6.10 | E2E: conversation with 1 active SOP + 2 running bg jobs → prompt has all expected sections in canonical order | Integration |

---

## 10. Open Questions

1. **Should `## Available SOPs` collapse to "see /list-sops" once it exceeds
   N entries?** Recommend: keep flat through 15; introduce a `/list-sops`
   tool only if registries grow past that.
2. **What about per-team SOP scoping?** Out of scope. Add a `team_id` field
   on `SOPDefinition` in a follow-up; registry filters by current session's
   team.
3. **Localization?** All template strings are English. If we add l10n,
   wrap each user-facing string in `_(...)` — non-blocking.

---

*Continued in `07_end_to_end_scenarios.md`.*
