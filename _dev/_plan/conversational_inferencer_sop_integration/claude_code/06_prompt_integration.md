# Chapter 6 -- F6: Prompt Template Integration

> **Author:** Claude Code
> **Implements:** F6 from `README.md`
> **Depends on:** F3 (background jobs for running-jobs section), F4 (YOLO), F5 (SOP registry and state)
> **Touches:** `resources/prompt_templates/conversation/main/initial.jinja2`, `conversational_inferencer.py`

---

## 1. Goal

Augment the conversational inferencer's main Jinja2 template with FOUR
additive conditional sections, fully backward-compatible with existing
rendering:

| Section | When shown | What it contains |
|---------|------------|------------------|
| `## Execution Mode: YOLO (Headless)` | `yolo_mode == True` | Behavior contract for headless runs |
| `## Available SOPs` | `available_sops` non-empty | Catalog of SOP definitions |
| `## Active SOP` | `active_sop` is set | Active SOP + workflow description/status/guidance |
| `## Running Background Jobs` | `running_background_jobs` non-empty | Live job IDs, status, workspace hints |

The existing `## Workflow Context` block is repurposed under `## Active SOP`
with a legacy fallback for sessions that have `workflow_description` set but
no `active_sop`.

---

## 2. The Full New Template

Below is the complete rewritten `initial.jinja2`. Changes are marked with
`{# NEW #}` comments. Existing sections are preserved verbatim where
unchanged.

```jinja2
{# ================================================================= #}
{# 1. Employee identity (EXISTING -- unchanged)                       #}
{# ================================================================= #}
{% if employee is defined %}You are **{{ employee.name }}**, serving as **{{ employee.role }}**.

{{ employee.mindset }}
{% endif %}

{# ================================================================= #}
{# 2. YOLO mode contract (NEW -- chapter 4)                          #}
{# ================================================================= #}
{% if yolo_mode is defined and yolo_mode %}
## Execution Mode: YOLO (Headless)

You are running headless without a human attendant. Adjust your style:
- DO NOT ask clarifying questions; do not propose alternatives.
- DO NOT use `confirmation`, `clarification`, `single_choice`, `multiple_choice`
  for non-mandatory gates. The system auto-resolves them on your behalf.
- DO use these conversation tools when a mandatory gate (`[__must__]`)
  is reached -- the system will surface them to a supervisor.
- Keep your `<Response>` blocks terse and factual; they are written to a log.
- Prefer ACTION tools over CONVERSATION tools.
- On terminal SOP completion, emit a final `<Response>` containing a
  one-paragraph summary of what was done and any artifacts produced.
{% endif %}

{# ================================================================= #}
{# 3. Available SOPs catalog (NEW -- chapter 5)                       #}
{# ================================================================= #}
{% if available_sops is defined and available_sops %}
## Available SOPs

The following Standard Operating Procedures (SOPs) are available. You may
enter one when the user's request matches its purpose; you may exit the
active one at any time.

{% for sop in available_sops %}
- **{{ sop.name }}** -- {{ sop.title }}
{%- if sop.description %}
  - {{ sop.description }}
{%- endif %}
  - Phases: {{ sop.phases | join(' -> ') }}
{%- if sop.variables %}
  - Variables: {{ sop.variables | join(', ') }}
{%- endif %}
{%- if sop.required_variables %}
  - Required: {{ sop.required_variables | join(', ') }}
{%- endif %}
{%- if sop.has_must_gates %}
  - Warning: Contains `[__must__]` gates -- pauses for user input even in YOLO mode.
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

{# ================================================================= #}
{# 4. Active SOP block (NEW -- replaces Workflow Context when SOP     #}
{#    registry is active; chapter 5)                                  #}
{# ================================================================= #}
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
{{ workflow_nextstep_guidance | default("(no guidance -- respond to user request directly)") }}
</WorkflowNextStepGuidance>

{% if active_sop.has_must_gates %}
**Note:** This SOP contains mandatory user-input gates marked `[__must__]`.
{% if yolo_mode is defined and yolo_mode %}In YOLO mode, those gates will halt execution and surface to a supervisor.{% endif %}
{% endif %}

To exit this SOP without completing it: `/exit-sop --reason "<short reason>"`.
{% endif %}

{# ================================================================= #}
{# 4b. Legacy fallback: workflow_description set but no active_sop    #}
{#     (pre-SOP-registry sessions -- EXISTING behavior preserved)     #}
{# ================================================================= #}
{% if (active_sop is not defined or not active_sop) and workflow_description is defined and workflow_description %}
## Workflow Context
{% if workflow_target_path is defined and workflow_target_path %}
You operate on {{ workflow_target_path }} under repository `{{ session_root_path | default("(not set)") }}`.
{% endif %}

<WorkflowDescription>
{{ workflow_description | default("No active workflow.") }}
</WorkflowDescription>

<WorkflowStatus>
{{ workflow_status | default("No workflow active.") }}
</WorkflowStatus>

<WorkflowNextStepGuidance>
{{ workflow_nextstep_guidance | default("No specific guidance -- respond to the user's request directly.") }}
</WorkflowNextStepGuidance>
{% endif %}

{# ================================================================= #}
{# 5. Running Background Jobs (NEW -- chapter 3)                      #}
{# ================================================================= #}
{% if running_background_jobs is defined and running_background_jobs %}
## Running Background Jobs

The following jobs are running in the background. You will be notified via a
`[Background job completed]` system message when each one finishes -- do NOT
wait for them; continue handling the user's current request.

{% for job in running_background_jobs[:10] %}
- `{{ job.id }}` -- **{{ job.kind }}**: `{{ job.cmdline_short }}`
  - Status: {{ job.status }}{% if job.schedule_mode != 'once' %} (schedule: {{ job.schedule_mode }} every {{ job.schedule_every_seconds }}s, completed {{ job.schedule_runs_completed }} so far){% endif %}

  - Workspace: `{{ job.workspace }}`
{%- if job.last_output_tail %}
  - Last output: `{{ job.last_output_tail | truncate(120) }}`
{%- endif %}
{% if job.fork_on_completion %}
  - Will fork conversation on completion.
{% endif %}
{% endfor %}
{% if running_background_jobs | length > 10 %}
(+{{ running_background_jobs | length - 10 }} more jobs not shown)
{% endif %}

If a job appears stuck, you can:
- Inspect its workspace files for details.
- Cancel via `/background-job-cancel <job_id>`.
{% endif %}

{# ================================================================= #}
{# 6. Available Tools (EXISTING -- unchanged)                         #}
{# ================================================================= #}
## Available Tools

{% if action_tools is defined and action_tools %}
### Action Tools
{{ action_tools }}
{% endif %}

{% if conversation_tools is defined and conversation_tools %}
### Conversation Tools (structured input collection only)
{{ conversation_tools }}
{% endif %}

{# ================================================================= #}
{# 7. Conversation history (EXISTING -- unchanged)                    #}
{# ================================================================= #}
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

{# ================================================================= #}
{# 8. Decision Procedure (EXISTING -- extended for SOP awareness)     #}
{# ================================================================= #}
## Decision Procedure

Before responding, reason through these steps silently:
1. **Classify the user's latest message:**
   - (a) **SOP-aligned** -- the user's request matches the Active SOP's next step (if any) OR matches an Available SOP they should enter.
   - (b) **Workflow-aligned without SOP** -- request advances an active workflow but does not match an SOP.
   - (c) **Ad-hoc action** -- outside any workflow/SOP (e.g., "search for X", "run Y").
   - (d) **Conversational** -- greeting, conceptual question, chitchat.
2. **If (a) and Active SOP is set:** Diff `<WorkflowStatus>` against `<WorkflowNextStepGuidance>` carefully. Execute remaining sub-steps only. If complete, ask whether to proceed to next phase or exit SOP.
3. **If (a) and no Active SOP but a matching Available SOP exists:** Suggest `/enter-sop <name>` with a short rationale; OR enter it directly if the user clearly intended to.
4. **If (b)/(c):** Fulfill the request; if relevant, remind the user where any paused/active workflow left off.
5. **If (d):** Respond in natural language only.
6. **At all times:** Read `## Running Background Jobs` and acknowledge any completed/failed jobs in your reasoning (their `[Background job completed]` system messages also appear in conversation history).
7. **If a tool call fails:** Report the error clearly, suggest a fix, do not silently retry more than once.

{# ================================================================= #}
{# 9. Response Format (EXISTING -- unchanged)                         #}
{# ================================================================= #}
## Response Format

Your output has two parts: **Thinking** (optional) then **Response** (required).

### Part 1 -- Thinking (before `<Response>`)
For non-trivial requests, write your careful step-by-step reasoning BEFORE the `<Response>` tag:
1. Follow the Decision Procedure above (classify, diff status, identify remaining steps).
2. Do you need user input to proceed? If so, how many separate inputs are needed, and which conversation tool type (`clarification`, `single_choice`, `multiple_choice`, `confirmation`) fits each?
3. After user inputs are collected, are any additional tools (e.g. action tools) needed?

### Part 2 -- Response (inside `<Response>...</Response>`)
Your user-facing answer goes inside `<Response>` tags. This is what the user eventually sees.
- Write clear, helpful and user-friendly natural language addressing the CurrentTurn in Conversation.
  *  NEVER put reasoning/analysis inside `<Response>` tags. Keep it before the tag.
  *  Your natural language text MUST be a complete, self-contained message. Do NOT end with dangling lead-ins like "Let me collect both:" or "Here are the tools:" -- the ToolsToInvoke block will be hidden from the user in the chat visualization, so the text must read naturally on its own without it.
- If you need to invoke tools, add a fenced `json ToolsToInvoke` block at the end.
  * One JSON object per line. Each object is one tool invocation. If multiple tools are needed, list them in execution order -- top line runs first.
  * Each tool can optionally capture its result into one or more named variables via the `output` field. Later tools can reference that variable using `__variable_name__` syntax in their arguments.
  * An output variable can be a dictionary -- use `__var.key1.key2__` to retrieve a nested value.
  * If the tool description does not document output format, assume a single flat output variable.
- Omit the ToolsToInvoke block entirely when no tools are needed.
- When multiple user inputs are needed, You MUST separate conversation tool invocations -- one per input. Do NOT combine unrelated questions into a single tool call.

### Example structure:

[Your reasoning/analysis here -- classification, status diff, etc. This part is auto-collapsed in the UI.]

<Response>
[User-facing natural language -- concise, helpful, complete sentences that read naturally on their own. Do NOT end with a lead-in to the tool block.]

```json ToolsToInvoke
{"type": "conversation", "name": "clarification|single_choice|multiple_choice|confirmation", "arguments": {"prompt": "your question", ...}, "output": ["var1", "var2", ...]}
{"type": "conversation", "name": "single_choice", "arguments": {"prompt": "pick one", "choices": [...]}, "output": ["var3"]}
{"type": "action", "name": "tool_name", "arguments": {"param1": "value1", "param2": "value2", "param3": "__var1__", "param4": "__var3__"}, "output": [...]}
```
</Response>

NOTES:
- If a user's request requires an action (run a task, search knowledge, change settings), use the appropriate tool inside `<Response>`.
- If a user's request is chatting (greetings, questions about concepts), respond directly inside `<Response>` without tools.
- Use conversation tools only when you need critical user input. If the user's intent is clear, respond directly.
- Always wrap tool calls in a fenced ```json ToolsToInvoke block. Never output raw JSON inline.
```

---

## 3. Template Variable Contracts

`_render_prompt()` in `ConversationalInferencer` passes these NEW variables
in addition to today's:

```python
# In _render_prompt(), after existing feed construction:
feed = {
    # Existing (unchanged)
    "employee": ...,
    "workflow_description": ...,
    "workflow_status": ...,
    "workflow_nextstep_guidance": ...,
    "workflow_target_path": ...,
    "session_root_path": ...,
    "action_tools": ...,
    "conversation_tools": ...,
    "conversation_history": ...,
    "current_turn": ...,
    "completed_actions": ...,

    # NEW
    "yolo_mode": self.yolo_mode,
    "available_sops": (
        self.sop_registry.list() if self.sop_registry else []
    ),
    "active_sop": self._active_sop_definition(),
    "active_run_id": self.prior_context.get("active_run_id"),
    "running_background_jobs": _format_running_jobs(
        JobManager.instance().list_running(
            session_id=self._session_id
        )
    ),
}
```

### 3.1 `_active_sop_definition()`

```python
def _active_sop_definition(self) -> Optional[SOPDefinition]:
    """Get the SOPDefinition for the active SOP, if any."""
    sop_id = self.prior_context.get("active_sop_id")
    if not sop_id:
        return None
    if self.sop_registry:
        return self.sop_registry.get(sop_id)
    return None
```

### 3.2 `_format_running_jobs()`

Formats `BackgroundJob` instances into dicts suitable for the template.
Includes sensitive arg redaction and a 10-job display cap.

```python
def _format_running_jobs(
    jobs: list[BackgroundJob],
) -> list[dict[str, Any]]:
    """Convert BackgroundJob instances to template-friendly dicts.

    - Redacts sensitive args in cmdline_short
    - Limits to 10 entries (template also enforces [:10])
    - Excludes completed jobs (only RUNNING/SCHEDULED/PENDING)
    """
    result = []
    for j in jobs[:10]:
        cmdline_short = _redact_cmdline_short(j.cmdline)
        result.append({
            "id": j.id,
            "kind": j.kind.value,
            "cmdline_short": cmdline_short,
            "status": j.status.value,
            "workspace": str(j.workspace),
            "last_output_tail": j.last_output_tail,
            "schedule_mode": j.schedule.mode,
            "schedule_every_seconds": j.schedule.every_seconds,
            "schedule_runs_completed": j.schedule.runs_completed,
            "fork_on_completion": j.fork_on_completion,
        })
    return result


def _redact_cmdline_short(cmdline: list[str]) -> str:
    """Build a display-safe cmdline string.

    - Truncates to 100 chars
    - Redacts values for keys matching sensitive patterns
    """
    _SENSITIVE_RE = re.compile(
        r"(?:key|secret|token|password|credential|auth)",
        re.IGNORECASE,
    )
    parts = []
    skip_next = False
    for i, arg in enumerate(cmdline):
        if skip_next:
            parts.append("***")
            skip_next = False
            continue
        if "=" in arg:
            key, _, val = arg.partition("=")
            if _SENSITIVE_RE.search(key):
                parts.append(f"{key}=***")
                continue
        if _SENSITIVE_RE.search(arg) and i + 1 < len(cmdline):
            parts.append(arg)
            skip_next = True
            continue
        parts.append(arg)
    return " ".join(parts)[:100]
```

---

## 4. Backward Compatibility

### 4.1 Legacy fallback rule

| Variable | Existing behavior | New behavior |
|----------|-------------------|--------------|
| `workflow_description` | Always shown in `## Workflow Context` | Shown inside `## Active SOP` when `active_sop` is set. When `active_sop` absent but `workflow_description` present (legacy), the template falls back to the original `## Workflow Context` block (Section 4b in template). |
| `workflow_status`, `workflow_nextstep_guidance` | Same | Same fallback rule |
| All other existing vars | Unchanged | Unchanged |

The fallback block (Section 4b) ensures that sessions created before the
SOP registry feature produce a **byte-identical prompt** after upgrading.
This is enforced by test T6.1.

### 4.2 When new variables are absent

All four new sections are guarded by `{% if X is defined and X %}`. When
the new variables are not passed (e.g., the server has not been updated to
inject them), the template renders identically to the pre-change version.

---

## 5. Token Budget Considerations

Worst-case token addition from new sections:

| Section | Approx tokens |
|---------|---------------|
| YOLO contract | ~150 |
| Available SOPs (5 SOPs x 8 lines) | ~300 |
| Active SOP framing (excluding existing workflow blocks) | ~50 |
| Running Background Jobs (10 jobs x 5 lines) | ~500 |
| Decision Procedure extension (3 new steps) | ~100 |
| **Total worst case** | ~1100 tokens |

For a typical prompt budget of ~16k tokens, this is <7%. The existing
`_compress_context_if_needed()` handles overflow in dynamic context; static
prompt sections are not compressed (they are the agent's "operating system").

**10-job cap:** The template uses `running_background_jobs[:10]` plus a
"+N more" suffix. `_format_running_jobs` also caps at 10. This prevents
runaway token usage from many concurrent jobs.

---

## 6. `_render_prompt` Changes

The `_render_prompt()` method (~line 568 in `conversational_inferencer.py`)
needs these modifications:

### 6.1 SOP evaluation extraction

Replace the inline SOP evaluation block (~lines 619-692) with a call to
`self._evaluate_sop()` (extracted in chapter 4):

```python
# Replace:
#   nextstep_guidance = ""
#   sop_path = getattr(self.prompt_renderer, "find_sop_file", ...)()
#   if sop_path is not None:
#       ... (50+ lines of inline SOP evaluation)
# With:
nextstep_guidance, _ = self._evaluate_sop()
```

### 6.2 Feed augmentation

After the existing `feed` dict construction (~line 693), add the new vars:

```python
feed = {
    **template_vars,
    "workflow_nextstep_guidance": nextstep_guidance,
    "action_tools": available_tools,
    **self.prior_context,
    "completed_actions": all_actions,
    "conversation_history": messages,
    "current_turn": {"role": "user", "content": current_message},
    "conversation_tools": conversation_tools_text,
    # --- NEW ---
    "yolo_mode": self.yolo_mode,
    "available_sops": (
        self.sop_registry.list()
        if getattr(self, "sop_registry", None) else []
    ),
    "active_sop": self._active_sop_definition(),
    "active_run_id": self.prior_context.get("active_run_id"),
    "running_background_jobs": self._get_running_jobs_for_template(),
}
```

### 6.3 Helper for running jobs

```python
def _get_running_jobs_for_template(self) -> list[dict]:
    """Fetch running jobs from JobManager and format for template."""
    try:
        from agent_foundation.common.jobs.manager import JobManager
        session_id = self.prior_context.get("session_id", "")
        jobs = JobManager.instance().list_running(session_id=session_id)
        return _format_running_jobs(jobs)
    except Exception:
        return []
```

---

## 7. Decision Procedure Update

The Decision Procedure section (Section 8 in the template) is extended
from 6 steps to 7 steps:

| Step | Original | New |
|------|----------|-----|
| 1 | Classify: (a) Workflow-aligned, (b) Ad-hoc, (c) Conversational | Classify: (a) **SOP-aligned**, (b) Workflow-aligned without SOP, (c) Ad-hoc, (d) Conversational |
| 2 | If (a): Diff status vs guidance | If (a) + Active SOP: Diff status vs guidance. If complete, ask about next phase or exit. |
| 3 | If (b): Fulfill, remind workflow | **NEW**: If (a) + no Active SOP but matching Available SOP: Suggest `/enter-sop`. |
| 4 | If (c): NL only | If (b)/(c): Fulfill request; remind about paused/active workflows. |
| 5 | If complete: Summarize | If (d): NL only. |
| 6 | If error: Report clearly | **NEW**: At all times: Read `## Running Background Jobs`, acknowledge completions. |
| 7 | -- | If error: Report clearly. |

This makes the LLM SOP-aware: it can suggest entering an SOP when a user's
request matches, and it naturally acknowledges background job completions.

---

## 8. Migration Path for Existing SOPs

Existing SOP files in `_variables/workflow_sop/`:
- `code_optimization.md` -- Phase 3b has `__must__`; needs `## Description`
- `model_optimization.jinja2` -- needs `__must__` audit + `## Description`
- `role_creation.jinja2` -- needs `__must__` audit + `## Description`

Migration steps:
1. Add a `## Description` one-paragraph block at the top of each SOP file
   for the registry to extract via `_extract_title_desc()`.
2. (Optional) Add `<!-- sop-meta required_vars: x,y,z -->` HTML comment for
   precise `required_variables` declaration.
3. Audit all confirmation gates: any destructive operation should have
   `[__requires confirmation__; __must__]`.

---

## 9. Concrete Code-Change List

| File | Change |
|------|--------|
| `agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` | REWRITE per Section 2 above. |
| `agent_foundation/.../conversational/conversational_inferencer.py` | Augment `_render_prompt()` with new template vars (Section 6). Add `_active_sop_definition()`, `_get_running_jobs_for_template()`. Replace inline SOP eval with `_evaluate_sop()` call. |
| `agent_foundation/common/sop/registry.py` | Add `_extract_title_desc()` helper (used at SOP-load time). |
| Existing SOP files | Add `## Description` paragraphs. |
| `tests/agent_foundation/.../conversational/test_prompt_rendering.py` | NEW tests for each conditional section. |

---

## 10. Test Plan

| # | Test | Type |
|---|------|------|
| T6.1 | Template renders NOTHING of the new sections when all new vars absent (backward compat: byte-identical to pre-change template) | Unit (snapshot) |
| T6.2 | `available_sops` populated -> `## Available SOPs` block present, contains all entries with phases, variables, must-gate warnings | Unit |
| T6.3 | `active_sop` set -> `## Active SOP` block present, contains `<WorkflowDescription>` + `<WorkflowStatus>` + `<WorkflowNextStepGuidance>` | Unit |
| T6.4 | `active_sop` set + `active_sop.has_must_gates=True` -> must-gate warning note rendered | Unit |
| T6.5 | `running_background_jobs` non-empty -> `## Running Background Jobs` block present | Unit |
| T6.6 | `yolo_mode=True` -> YOLO contract block present | Unit |
| T6.7 | `yolo_mode=False` or absent -> YOLO block absent | Unit |
| T6.8 | Legacy `workflow_description` (no `active_sop`) -> fallback `## Workflow Context` renders identically to pre-change template | Unit (snapshot) |
| T6.9 | `cmdline_short` truncates to 100 chars | Unit |
| T6.10 | `cmdline_short` redacts `--api-key=SECRET` to `--api-key=***` | Unit |
| T6.11 | Completed job (`status=DONE`) does NOT appear in running list | Unit |
| T6.12 | More than 10 running jobs -> only first 10 shown, "+N more" suffix | Unit |
| T6.13 | Decision Procedure includes SOP-aligned classification (step 1a) and background-job awareness (step 6) | Unit |
| T6.14 | E2E: conversation with 1 active SOP + 2 running bg jobs -> prompt has all expected sections in canonical order | Integration |
| T6.15 | E2E: session without any SOP/job features -> prompt identical to current production template | Integration |
| T6.16 | Token budget: 15 running jobs + 5 available SOPs + active SOP -> prompt stays within 16k token budget | Unit |
| T6.17 | `_active_sop_definition()` returns None when no `active_sop_id` in `prior_context` | Unit |
| T6.18 | `_get_running_jobs_for_template()` returns empty list when JobManager has no running jobs | Unit |

---

## 11. Cross-References

- **Chapter 1 (Input Queue):** Background completions arrive as `CompletedAction(tool="__background__")` in `_dynamic_context`, visible in the `completed_actions` template variable. The `## Running Background Jobs` section shows LIVE jobs only.
- **Chapter 3 (Background Jobs):** `JobManager.list_running()` provides the data for the running-jobs template section.
- **Chapter 4 (YOLO Mode):** The YOLO prompt section instructs the LLM to avoid unnecessary conversation tools.
- **Chapter 5 (SOP Lifecycle):** `SOPRegistry.list()` provides `available_sops`; `/enter-sop` sets `active_sop_id`; `/exit-sop` clears it.
- **Chapter 7 (Scenarios):** All scenarios exercise the template rendering. Scenario 5 specifically tests Active SOP + Running Jobs coexistence.
- **Chapter 8 (Roadmap):** Phase G covers this chapter (PRs G.1 and G.2).

---

## 12. Open Questions

1. **Should `## Available SOPs` collapse past N entries?** Recommend: keep
   flat through 15 entries. Add a `/list-sops` tool only if registries grow
   past that.

2. **Per-team SOP scoping?** Out of scope. Add a `team_id` field on
   `SOPDefinition` in a follow-up; registry filters by current session's team.

3. **Should the running-jobs section include completed-recently jobs?** No.
   Completions are routed through the input queue and appear as
   `[Background job completed]` messages in conversation history. The
   `## Running Background Jobs` section is exclusively for live jobs.

4. **What about the existing `_variables/workflow/sop.jinja2` path?** The
   legacy fallback block (Section 4b) ensures backward compatibility. When
   `active_sop` is not set but `workflow_description` is (the legacy case),
   the template renders the existing `## Workflow Context` block unchanged.

---

*Continued in `07_scenarios_and_verification.md`.*
