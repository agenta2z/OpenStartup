# Chapter 4 — F4: YOLO Mode

> **Implements:** F4 from `README.md`
> **Depends on:** F2 (input queue)
> **Touches:** `ConversationalInferencer`, SOP parsing helpers, conversation tool handlers

---

## 1. Goal

Add a `yolo_mode: bool` flag to `ConversationalInferencer` that:

1. **Suppresses user-facing chatter** — the agent does not narrate, clarify, or
   confirm unless it has to.
2. **Auto-resolves all `conversation` tools** (clarification / confirmation /
   single_choice / multiple_choice / proposal_selection / tool_argument_form)
   using SOP-provided defaults or sensible automatic choices.
3. **EXCEPT** when the SOP author has marked a gate as `[__must__]`. Those
   gates are absolute and must surface a user (or fork-parent) interaction
   even in YOLO mode.

YOLO mode is the mode the `/sop` subprocess SOP runner (chapter 5) uses by
default — it's a headless agent running an SOP end-to-end without a human in
the chair.

---

## 2. The Existing SOP Marker Vocabulary

From `code_optimization.md` (and other SOPs):

| Marker | Used in today | Semantic |
|--------|---------------|----------|
| `[__initial__]` | Phase headers | This phase has no dependency; it's the entry point. |
| `[__depends on__ Phase N]` | Phase headers | Topological ordering constraint. |
| `[__branch__]` | Phase 4 header | This phase may run multiple times in parallel (one per selected proposal). |
| `[__requires confirmation__]` | Inline within phase descriptions | Before running the phase's tools, emit a `confirmation` conversation tool. |
| `**Tools**[__must__]:` | List header | The listed tools are mandatory for this phase (cannot be skipped). |
| `**Tools**[__optional__]:` | List header | The listed tools may be invoked at the agent's discretion. |

These are parsed by the existing `SOPManager` (in `rich_python_utils.string_utils
.formatting.template_manager.sop_manager`) into a phase-state graph. The
parser already understands `[__...__]` markers.

### 2.1 New combined marker

Introduce the explicit two-marker form for YOLO gates:

```
[__requires confirmation__; __must__]
```

Read as: "this phase requires confirmation, AND that confirmation MUST happen
(no YOLO bypass)."

The SOP parser needs ONE small change: when scanning for the
`[__requires confirmation__]` marker, ALSO scan for a follow-on `__must__`
within the same bracket group. If present, attach `must=True` to the parsed
gate node.

**Already in `code_optimization.md`:**
```
### Phase 3b -- Proposal Review & Selection
[__depends on__ Phase 3]

[__requires confirmation__; __must__] After the research & proposal phase ...
```

So the syntax pre-exists. Today the SOP parser ignores `__must__` after
`__requires confirmation__`. We just need to **start honoring it**.

### 2.2 Parser change

`sop_manager.py` parser update (sketch):

```python
_GATE_MARKER_RE = re.compile(
    r"\[__requires confirmation__(?:\s*;\s*__must__)?\]"
)
_MUST_RE = re.compile(r"\b__must__\b")

def parse_gate_markers(line: str) -> tuple[bool, bool]:
    """Returns (requires_confirmation, is_must)."""
    m = _GATE_MARKER_RE.match(line)
    if not m: return (False, False)
    return (True, bool(_MUST_RE.search(m.group(0))))
```

The parsed gate node grows a `must: bool` attribute. Default is `False`
(YOLO can bypass).

---

## 3. Design

### 3.1 The `yolo_mode` attribute

```python
@attrs(slots=False)
class ConversationalInferencer(InferencerBase):
    ...
    yolo_mode: bool = attrib(default=False, kw_only=True)
```

When constructed by the `/sop` subprocess runner (chapter 5), this is
explicitly set to `True`. When constructed by the normal server path, it's
`False` unless the server admin enables it globally.

### 3.2 Tool-handler dispatch with YOLO

In `_handle_conversation_tool` (and the rich-group variant):

```python
async def _handle_conversation_tool(self, tool, assistant_text, interactive_override=None):
    if self.yolo_mode and not self._gate_requires_user(tool):
        return self._yolo_auto_resolve(tool)
    # ... existing user-input flow (now backed by user_input_queue)
```

### 3.3 `_gate_requires_user(tool)`

```python
def _gate_requires_user(self, tool: ConversationTool) -> bool:
    """Whether this tool must surface a user interaction even in YOLO mode.

    Rules:
      1. Tool's metadata.must = True → yes.
      2. Tool type is `proposal_selection` AND
         active SOP gate for current phase has must=True → yes.
      3. Tool type is `confirmation` AND active SOP gate has must=True → yes.
      4. Otherwise (clarification, single/multiple_choice, non-must
         confirmations) → no, can be auto-resolved.
    """
    if tool.metadata.get("must") is True:
        return True
    active_gate = self._current_phase_gate()
    if active_gate is not None and active_gate.must:
        if tool.tool_type in (ConversationToolType.PROPOSAL_SELECTION,
                               ConversationToolType.CONFIRMATION,
                               ConversationToolType.TOOL_ARGUMENT_FORM):
            return True
    return False
```

The `_current_phase_gate()` method consults the SOP tracker (already
maintained by `SOPManager` / `StateGraphTracker`) to find the gate node
attached to the current phase.

### 3.4 `_yolo_auto_resolve(tool)`

Per-tool-type auto-resolution:

```python
def _yolo_auto_resolve(self, tool: ConversationTool) -> Optional[str]:
    """Synthesize a default response for a non-must conversation tool.

    Returns the same shape that `_handle_conversation_tool` would return
    after a real user interaction.
    """
    t = tool.tool_type

    if t == ConversationToolType.CLARIFICATION:
        # Free-text input. Pull from a SOP-provided variable map.
        # The /sop subprocess provides --var key=value at launch; those
        # populate `self.prior_context["yolo_vars"]`.
        var_name = (tool.output_vars or ["input"])[0]
        yolo_vars = self.prior_context.get("yolo_vars", {})
        if var_name in yolo_vars:
            return str(yolo_vars[var_name])
        # If no var provided, treat as empty (the SOP must handle this)
        logger.warning("YOLO: clarification for var=%r has no pre-supplied value; returning empty.", var_name)
        return ""

    if t == ConversationToolType.CONFIRMATION:
        # Auto-yes unless metadata says otherwise (e.g. negative-default)
        default = tool.metadata.get("yolo_default", "yes")
        return default

    if t == ConversationToolType.SINGLE_CHOICE:
        # Pick first choice (deterministic) unless SOP override
        if tool.metadata.get("yolo_choice_index") is not None:
            idx = int(tool.metadata["yolo_choice_index"])
            if 0 <= idx < len(tool.choices):
                return tool.choices[idx].value
        if tool.choices:
            return tool.choices[0].value
        return ""

    if t == ConversationToolType.MULTIPLE_CHOICE:
        # Pick all choices marked yolo_pick=True; or default to none if any
        # such marker exists; else pick the first.
        picked = [c for c in tool.choices if c.metadata.get("yolo_pick")]
        if not picked and tool.choices:
            picked = [tool.choices[0]]
        return "|".join(c.value for c in picked)

    if t == ConversationToolType.TOOL_ARGUMENT_FORM:
        # Best-effort: use each field's default value. If a field lacks a
        # default AND is required, log and return empty (tool execution
        # may fail; SOP author should mark such gates [__must__]).
        return self._yolo_default_form_values(tool)

    if t == ConversationToolType.PROPOSAL_SELECTION:
        # Auto-select top-N proposals (default 5, configurable via
        # SOP variable `yolo_pre_select_top_n`).
        n = int(self.prior_context.get("yolo_pre_select_top_n", 5))
        proposals = tool.metadata.get("proposals", {})
        ids = _top_n_globally_ranked(proposals, n)
        return {"selected_proposals": ids, "custom_queries": []}

    raise ValueError(f"YOLO auto-resolve: unsupported tool type {t!r}")
```

`_top_n_globally_ranked` mirrors the React widget's `selectTopNGlobally`
algorithm (rank ASC → source_workers DESC → id ASC) so YOLO results match
the in-chat default-selection UX.

### 3.5 Suppressing user-facing chatter

YOLO mode also affects the rendered prompt to discourage the LLM from
narrating to a nonexistent user:

Add a section to `initial.jinja2`:

```jinja2
{% if yolo_mode is defined and yolo_mode %}

## Execution Mode: YOLO (Headless)

You are running headless without a human attendant. Adjust your style:
- DO NOT ask clarifying questions; do not propose alternatives.
- DO NOT use `confirmation`, `clarification`, `single_choice`, `multiple_choice`
  for non-mandatory gates. The system auto-resolves them on your behalf.
- DO use these conversation tools when a mandatory gate (`[__must__]`)
  is reached — the system will surface them to a supervisor.
- Keep your `<Response>` blocks terse and factual; they are written to
  a log, not shown to a user.
- Prefer ACTION tools over CONVERSATION tools.
- On terminal SOP completion, emit a final `<Response>` containing a one-paragraph
  summary of what was done and any artifacts produced.
{% endif %}
```

This template variable is set by `_render_prompt` from `self.yolo_mode`.

### 3.6 The `yolo_vars` mechanism

When `/sop` launches a YOLO subprocess (chapter 5), the user can supply
SOP-input variables on the command line:

```
/sop code_optimization --var workflow_target_path=src/foo --var strategy="reduce hot loop"
```

These are stored at session-construction time:

```python
prior_context["yolo_vars"] = {
    "workflow_target_path": "src/foo",
    "strategy": "reduce hot loop",
}
```

`_yolo_auto_resolve` reads from this map for `clarification` tools.

### 3.7 Audit log for auto-resolutions

Every YOLO auto-resolution gets a `CompletedAction` entry in
`_dynamic_context` tagged `auto_resolved_by_yolo=True`:

```python
CompletedAction(
    tool_type="conversation",
    tool_name=tool.tool_type.value,
    arguments=tool.to_dict(),
    result=resolved_response,
    metadata={"auto_resolved_by_yolo": True, "must_gate": False},
)
```

This makes YOLO runs fully replayable / auditable. The artifact
`yolo_decisions.jsonl` (written to the SOP run's workspace) accumulates
these entries for post-hoc review.

### 3.8 Must-gate handling under YOLO

When `[__must__]` triggers and YOLO is on, what happens?

- **In a `/sop` subprocess context with NO parent connection** (e.g., direct
  CLI invocation): the inferencer logs an error and exits with status
  `must_gate_unattended`. The job is marked FAILED. The summary string is
  prefixed `[BLOCKED ON MUST-GATE]` so the parent SOP/inferencer (if any) can
  react.
- **In a `/sop` subprocess WITH a parent connection** (the spawning
  conversational inferencer registered a callback): the gate is forwarded to
  the parent's input queue as a `MustGateBlocked` queue item (extension of
  `BackgroundJobComplete`). The parent inferencer's LLM sees a message like
  "subprocess sop hit must-gate: please answer X / Y". The parent's response
  is shipped back to the child via the existing IPC.
- **In a normal server-attached YOLO mode** (an admin enabled YOLO globally):
  must-gates fall through to the normal user-input path (queue.get). The
  user sees the widget and answers it.

For v1, only the first case is fully implemented (subprocess YOLO). The
second case is designed but deferred to a follow-up (see chapter 8 §6
"Deferred").

---

## 4. Concrete Code-Change List

| File | Change |
|------|--------|
| `rich_python_utils/string_utils/formatting/template_manager/sop_manager.py` | Parser: recognize `__must__` after `__requires confirmation__`; attach `must: bool` to gate nodes. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py` | Add `yolo_mode` attrib. Add `_gate_requires_user`, `_yolo_auto_resolve`, `_current_phase_gate`, `_yolo_default_form_values`. Modify `_handle_conversation_tool` + `_handle_rich_group` to consult YOLO first. Audit-log auto-resolutions. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/yolo_helpers.py` | NEW. `_top_n_globally_ranked` (mirrors React widget). |
| `agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` | Add YOLO-mode section conditional. |
| `agent_foundation/common/inferencers/agentic_inferencers/conversational/protocols.py` | Optional: add `MustGateBlocked` QueueItem subclass (for chapter 5 future parent routing). |
| `tests/agent_foundation/.../conversational/test_yolo_mode.py` | NEW. See §6. |

---

## 5. Worked Example

SOP fragment:
```
## Phase 2 -- Investigation
[__requires confirmation__] Before investigating, get confirmation.

**Tools**[__must__]: /investigate-system

## Phase 3b -- Review
[__requires confirmation__; __must__] After investigation, present findings.
```

YOLO behavior:
- Phase 2's confirmation gate: NOT `__must__` → auto-yes; investigate-system
  runs (it's `__must__` for tool selection, not for confirmation gate).
- Phase 3b: gate IS `__must__` → YOLO does NOT auto-resolve. In subprocess
  mode, agent halts with `must_gate_unattended`; in server-attached mode,
  user sees the widget.

---

## 6. Test Plan

| # | Test | Type |
|---|------|------|
| T4.1 | SOP parser: `[__requires confirmation__]` → must=False | Unit |
| T4.2 | SOP parser: `[__requires confirmation__; __must__]` → must=True | Unit |
| T4.3 | `_yolo_auto_resolve(clarification)` reads from `yolo_vars` | Unit |
| T4.4 | `_yolo_auto_resolve(confirmation)` returns "yes" | Unit |
| T4.5 | `_yolo_auto_resolve(single_choice)` returns first choice | Unit |
| T4.6 | `_yolo_auto_resolve(multiple_choice)` picks first or yolo_pick subset | Unit |
| T4.7 | `_yolo_auto_resolve(proposal_selection)` returns top-N by rank | Unit |
| T4.8 | `_gate_requires_user` returns True iff phase gate has must=True | Unit |
| T4.9 | End-to-end yolo run of a 3-phase SOP with one must-gate → halt with status="must_gate_unattended" | Integration |
| T4.10 | End-to-end yolo run with no must-gates → completes, writes yolo_decisions.jsonl | Integration |
| T4.11 | Prompt template renders YOLO instructions only when yolo_mode=True | Unit |
| T4.12 | CompletedAction with auto_resolved_by_yolo=True visible in dynamic context | Unit |

---

## 7. Open Questions

1. **What about confirmation tools with `on_yes_action="open_experiment_hub"`?**
   In YOLO this would still trigger the experiment hub creation. Do we want
   to suppress server-side side effects in YOLO too? **Decision:** No —
   side effects are part of what "yes" means. If the SOP author doesn't want
   YOLO to trigger the hub, they mark the gate `__must__`.
2. **Negative-default confirmations?** Some SOPs have "type yes to delete".
   A YOLO auto-yes is dangerous. **Decision:** Add `yolo_default: "no"` to
   such confirmation tools in their SOP-level metadata; `_yolo_auto_resolve`
   reads it. Default remains "yes" for forward compatibility (existing SOPs
   don't have the marker).
3. **YOLO + interactive transports**: should a server-attached YOLO mode
   show widgets at all? **Decision:** Widget IS rendered (so the user can
   observe what's being auto-resolved), but with a "(auto-resolved)" badge
   and locked input controls. Implementation detail for the React layer;
   doesn't change backend.

---

*Continued in `05_sop_tools.md`.*
