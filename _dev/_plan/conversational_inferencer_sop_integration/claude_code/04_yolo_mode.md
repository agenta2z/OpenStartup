# Chapter 4 -- F4: YOLO Mode

> **Author:** Claude Code
> **Implements:** F4 from `README.md`
> **Depends on:** F1 (input queue -- YOLO is an alternative to queue-based input)
> **Touches:** `ConversationalInferencer`, SOP parser in `RichPythonUtils`, conversation tool handlers

---

## 1. Goal

Add a `yolo_mode: bool` flag to `ConversationalInferencer` that:

1. **Suppresses user-facing chatter** -- the agent does not narrate, clarify,
   or confirm unless it has to.
2. **Auto-resolves all `conversation` tools** (clarification, confirmation,
   single_choice, multiple_choice, proposal_selection, tool_argument_form)
   using SOP-provided defaults or sensible automatic choices.
3. **EXCEPT** when the SOP author has marked a gate as `[__must__]`. Those
   gates are absolute and must surface a user (or fork-parent) interaction
   even in YOLO mode.

YOLO mode is the execution mode the `/sop` subprocess runner (chapter 5)
uses by default -- a headless agent running an SOP end-to-end without a
human in the chair.

---

## 2. The Existing SOP Marker Vocabulary

From `code_optimization.md` and other SOPs:

| Marker | Semantic |
|--------|----------|
| `[__initial__]` | Entry-point phase |
| `[__depends on__ Phase N]` | Topological ordering |
| `[__branch__]` | Phase may run in parallel per selection |
| `[__requires confirmation__]` | Emit a confirmation tool before running |
| `**Tools**[__must__]:` | Listed tools are mandatory |
| `**Tools**[__optional__]:` | Listed tools are discretionary |

These are parsed by `SOPManager` in
`RichPythonUtils/src/rich_python_utils/string_utils/formatting/template_manager/sop_manager.py`
into a phase-state graph. The `StateGraphTracker` in
`rich_python_utils.common_objects.workflow.stategraph` tracks current phase,
completed states, and available next transitions.

### 2.1 New combined marker for YOLO gates

```
[__requires confirmation__; __must__]
```

Read as: "this phase requires confirmation, AND that confirmation MUST happen
(no YOLO bypass)."

This marker already exists in `code_optimization.md` Phase 3b:
```
### Phase 3b -- Proposal Review & Selection
[__depends on__ Phase 3]
[__requires confirmation__; __must__] After the research & proposal phase ...
```

Today the SOP parser ignores `__must__` after `__requires confirmation__`.
We just need to **start honoring it**.

### 2.2 SOP parser change

`sop_manager.py` parser update:

```python
_GATE_MARKER_RE = re.compile(
    r"\[__requires confirmation__(?:\s*;\s*__must__)?\]"
)
_MUST_RE = re.compile(r"\b__must__\b")

def parse_gate_markers(line: str) -> tuple[bool, bool]:
    """Returns (requires_confirmation, is_must).

    Examples:
      '[__requires confirmation__]' -> (True, False)
      '[__requires confirmation__; __must__]' -> (True, True)
      'no marker here' -> (False, False)
    """
    m = _GATE_MARKER_RE.search(line)
    if not m:
        return (False, False)
    return (True, bool(_MUST_RE.search(m.group(0))))
```

The parsed gate node grows a `must: bool` attribute. Default is `False`
(YOLO can bypass). This is a byte-additive change -- existing markers
without `__must__` parse identically to today.

---

## 3. Design

### 3.1 The `yolo_mode` attribute

Add to `ConversationalInferencer` (~line 81):

```python
@attrs(slots=False)
class ConversationalInferencer(InferencerBase):
    ...
    yolo_mode: bool = attrib(default=False, kw_only=True)
```

When constructed by the `/sop` subprocess runner (chapter 5), this is
explicitly set to `True`. When constructed by the normal server path, it
is `False` unless an admin enables it globally.

### 3.2 Extracting `_evaluate_sop()` from `_render_prompt()`

Today, SOP evaluation is inline in `_render_prompt()` (~lines 619-692).
This block:
1. Loads the SOP file via `SOPManager.load(sop_path)`
2. Stores the SOP on `self.prior_context["_sop"]`
3. Builds a `StateGraphTracker`
4. Generates `nextstep_guidance`

For YOLO mode, we need access to the tracker OUTSIDE of prompt rendering
(to check must-gates before handling conversation tools). Extract this
block into a dedicated method:

```python
def _evaluate_sop(self) -> tuple[str, Optional[StateGraphTracker]]:
    """Evaluate the active SOP and return (nextstep_guidance, tracker).

    Stores the tracker on self._sop_tracker for use by YOLO gate
    detection (Section 3.4).

    Extracted from _render_prompt() to allow pre-render gate checking.
    """
    sop_path = getattr(
        self.prompt_renderer, "find_sop_file", lambda: None
    )()
    if sop_path is None:
        self._sop_tracker = None
        return ("", None)

    try:
        sop = SOPManager.load(sop_path)
        self.prior_context["_sop"] = sop

        # Extract tool-to-phase mapping
        if hasattr(sop, "tool_to_phase_map"):
            tool_map = sop.tool_to_phase_map
            if tool_map:
                self.prior_context["tool_phase_map"] = tool_map

        # Build tracker from prior_context state
        completed = [
            r.phase if hasattr(r, "phase") else str(r)
            for r in self.prior_context.get("completed_phases", [])
        ]
        tracker = StateGraphTracker(
            graph=sop,
            current_state=self.prior_context.get("current_phase"),
            state_status=self.prior_context.get("phase_status", "idle"),
            completed_states=completed,
            state_outputs=self.prior_context.get("phase_outputs", {}),
            goto_counts=self.prior_context.get("goto_counts", {}),
        )

        # Auto-complete confirmation-gate phases (existing logic)
        if self.prior_context.pop("_confirmation_gate_passed", False):
            # ... (existing auto-complete logic, unchanged)
            pass

        nextstep_guidance = SOPManager.render_guidance(
            tracker, sop, context=dict(self.prior_context),
        )

        self._sop_tracker = tracker
        return (nextstep_guidance, tracker)
    except Exception as e:
        logger.warning("SOP evaluation failed: %s", e)
        self._sop_tracker = None
        return ("", None)
```

`_render_prompt()` then calls `self._evaluate_sop()` instead of the inline
block. No behavior change for non-YOLO paths.

### 3.3 Tool-handler dispatch with YOLO

In `_handle_conversation_tool` (~line 955):

```python
async def _handle_conversation_tool(
    self, tool, assistant_text, interactive_override=None
):
    # --- NEW: YOLO auto-resolution ---
    if self.yolo_mode and not self._gate_requires_user(tool):
        resolved = self._yolo_auto_resolve(tool)
        # Log the auto-resolution to audit trail
        self._log_yolo_decision(tool, resolved, must_gate=False)
        return resolved

    # --- Existing path (queue-backed or direct interactive) ---
    ...
```

### 3.4 `_gate_requires_user(tool)` -- must-gate detection

```python
def _gate_requires_user(self, tool: ConversationTool) -> bool:
    """Whether this tool must surface a user interaction even in YOLO mode.

    Rules:
      1. Tool's metadata.must = True -> yes.
      2. Active SOP gate for current phase has must=True AND tool type
         is one of (confirmation, proposal_selection, tool_argument_form)
         -> yes.
      3. Otherwise (clarification, single/multiple_choice, non-must
         confirmations) -> no, can be auto-resolved.
    """
    # Rule 1: explicit must on the tool
    if isinstance(tool, dict):
        meta = tool.get("metadata", {})
    else:
        meta = getattr(tool, "metadata", {}) or {}
    if meta.get("must") is True:
        return True

    # Rule 2: check the current SOP phase gate
    active_gate = self._current_phase_gate()
    if active_gate is not None and getattr(active_gate, "must", False):
        tool_type = (
            tool.tool_type if hasattr(tool, "tool_type")
            else tool.get("name", "")
        )
        if tool_type in (
            "confirmation",
            "proposal_selection",
            "tool_argument_form",
        ):
            return True

    return False


def _current_phase_gate(self):
    """Get the gate node for the current SOP phase (if any).

    Uses self._sop_tracker (populated by _evaluate_sop) to find
    the gate attached to the current phase node.
    """
    tracker = getattr(self, "_sop_tracker", None)
    if tracker is None:
        return None
    current = tracker.current_state
    if current is None:
        return None
    # Walk the SOP graph to find the gate for the current phase
    sop = self.prior_context.get("_sop")
    if sop is None:
        return None
    for phase in getattr(sop, "phases", []):
        if getattr(phase, "id", None) == current:
            for directive in getattr(phase, "directives", []):
                if "requires confirmation" in directive:
                    # Parse the must flag from the directive string
                    _, is_must = parse_gate_markers(
                        f"[{directive}]"
                    )
                    return _GateInfo(
                        requires_confirmation=True, must=is_must
                    )
    return None


@dataclass
class _GateInfo:
    requires_confirmation: bool = False
    must: bool = False
```

### 3.5 `_yolo_auto_resolve(tool)` -- per-type auto-resolution

```python
def _yolo_auto_resolve(self, tool: ConversationTool) -> Optional[str]:
    """Synthesize a default response for a non-must conversation tool.

    Returns the same shape that _handle_conversation_tool would return
    after a real user interaction.
    """
    t = tool.tool_type if hasattr(tool, "tool_type") else str(tool)

    if t == "clarification":
        # Pull from SOP-provided variable map (--var key=value at launch)
        var_name = (tool.output_vars or ["input"])[0]
        yolo_vars = self.prior_context.get("yolo_vars", {})
        if var_name in yolo_vars:
            return str(yolo_vars[var_name])
        logger.warning(
            "YOLO: clarification for var=%r has no pre-supplied value; "
            "returning empty.",
            var_name,
        )
        return ""

    if t == "confirmation":
        # Auto-yes unless tool metadata specifies a negative default
        default = (
            getattr(tool, "metadata", {}) or {}
        ).get("yolo_default", "yes")
        return default

    if t == "single_choice":
        # Pick first choice (deterministic) unless SOP overrides
        meta = getattr(tool, "metadata", {}) or {}
        if meta.get("yolo_choice_index") is not None:
            idx = int(meta["yolo_choice_index"])
            if 0 <= idx < len(tool.choices):
                return tool.choices[idx].value
        if tool.choices:
            return tool.choices[0].value
        return ""

    if t == "multiple_choice":
        # Pick all choices with yolo_pick=True; else first
        picked = [
            c for c in tool.choices
            if (getattr(c, "metadata", {}) or {}).get("yolo_pick")
        ]
        if not picked and tool.choices:
            picked = [tool.choices[0]]
        return "|".join(
            c.value if hasattr(c, "value") else str(c)
            for c in picked
        )

    if t == "tool_argument_form":
        # Use each field's default value
        return self._yolo_default_form_values(tool)

    if t == "proposal_selection":
        # Auto-select top-N proposals by rank
        n = int(self.prior_context.get("yolo_pre_select_top_n", 5))
        proposals = (
            getattr(tool, "metadata", {}) or {}
        ).get("proposals", {})
        ids = _top_n_globally_ranked(proposals, n)
        return {"selected_proposals": ids, "custom_queries": []}

    raise ValueError(f"YOLO auto-resolve: unsupported tool type {t!r}")


def _yolo_default_form_values(
    self, tool: ConversationTool
) -> dict[str, str]:
    """Best-effort fill of form fields using defaults.

    If a field lacks a default AND is required, log a warning.
    SOP authors should mark such gates [__must__].
    """
    form_data = {}
    fields = getattr(tool, "fields", []) or []
    for field in fields:
        name = field.get("name", "")
        default = field.get("default", "")
        required = field.get("required", False)
        if default:
            form_data[name] = str(default)
        elif required:
            logger.warning(
                "YOLO: form field %r is required but has no default. "
                "SOP should mark this gate [__must__].",
                name,
            )
            form_data[name] = ""
        else:
            form_data[name] = ""
    return form_data
```

`_top_n_globally_ranked` mirrors the React widget's `selectTopNGlobally`
algorithm:

```python
def _top_n_globally_ranked(
    proposals: dict[str, list[dict]], n: int
) -> list[str]:
    """Select top-N proposals by rank (ASC) then source_workers (DESC).

    Mirrors the frontend's selectTopNGlobally for consistent
    YOLO behavior vs. in-chat default selection.
    """
    flat = []
    for source, items in proposals.items():
        for item in items:
            flat.append({
                "id": item.get("id", ""),
                "rank": item.get("rank", 999),
                "source": source,
                "source_workers": len(items),
            })
    flat.sort(key=lambda x: (x["rank"], -x["source_workers"], x["id"]))
    return [x["id"] for x in flat[:n]]
```

### 3.6 Must-gate handling under YOLO

When `_gate_requires_user()` returns `True` while `yolo_mode=True`:

```python
async def _handle_conversation_tool(self, tool, assistant_text, ...):
    if self.yolo_mode and not self._gate_requires_user(tool):
        resolved = self._yolo_auto_resolve(tool)
        self._log_yolo_decision(tool, resolved, must_gate=False)
        return resolved

    if self.yolo_mode and self._gate_requires_user(tool):
        # Must-gate in YOLO mode with no human attached
        if isinstance(self.interactive, NullInteractive):
            # Subprocess context: halt with special exit status
            self._log_yolo_decision(
                tool, None, must_gate=True, blocked=True
            )
            raise MustGateBlockedError(
                f"Must-gate reached in YOLO mode at phase "
                f"{self.prior_context.get('current_phase', '?')}. "
                f"Tool type: {tool.tool_type}. "
                f"This gate requires human input."
            )
        # Server-attached YOLO: fall through to normal input path
        # (user sees the widget)

    # Normal path: read from queue or interactive
    ...


class MustGateBlockedError(Exception):
    """Raised when a must-gate is reached in YOLO mode without a human."""
    pass
```

In the `run_agentic_loop` exception handler:

```python
try:
    # ... main loop ...
except MustGateBlockedError as e:
    logger.info("YOLO must-gate blocked: %s", e)
    return AgenticResult(
        text=str(e),
        completed_actions=loop_actions,
        iterations_used=iteration + 1,
        raw_response=f"[BLOCKED ON MUST-GATE] {e}",
    )
```

The subprocess exits with code 2 (distinguishable from 0=success, 1=error).
JobManager reads this and includes `[BLOCKED ON MUST-GATE]` in the summary.

### 3.7 The `yolo_vars` mechanism

When `/sop` launches a YOLO subprocess (chapter 5), users supply SOP-input
variables:

```
/sop code_optimization --var workflow_target_path=src/foo --var strategy="reduce hot loop"
```

Stored at session-construction time:

```python
prior_context["yolo_vars"] = {
    "workflow_target_path": "src/foo",
    "strategy": "reduce hot loop",
}
```

`_yolo_auto_resolve()` reads from this map for `clarification` tools.

### 3.8 YOLO prompt section

Add a conditional section to `initial.jinja2` (full template in chapter 6):

```jinja2
{% if yolo_mode is defined and yolo_mode %}

## Execution Mode: YOLO (Headless)

You are running headless without a human attendant. Adjust your style:
- DO NOT ask clarifying questions; do not propose alternatives.
- DO NOT use `confirmation`, `clarification`, `single_choice`, `multiple_choice`
  for non-mandatory gates. The system auto-resolves them on your behalf.
- DO use these conversation tools when a mandatory gate (`[__must__]`)
  is reached -- the system will surface them to a supervisor.
- Keep your `<Response>` blocks terse and factual; they are written to
  a log, not shown to a user.
- Prefer ACTION tools over CONVERSATION tools.
- On terminal SOP completion, emit a final `<Response>` containing a
  one-paragraph summary of what was done and any artifacts produced.
{% endif %}
```

This template variable is set by `_render_prompt()` from `self.yolo_mode`.

### 3.9 Audit log (`yolo_decisions.jsonl`)

Every YOLO auto-resolution writes a JSONL line to the workspace:

```python
def _log_yolo_decision(
    self, tool, resolved, *, must_gate: bool, blocked: bool = False
) -> None:
    """Append a YOLO decision record to yolo_decisions.jsonl."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "phase": self.prior_context.get("current_phase", "unknown"),
        "kind": "must_gate_blocked" if blocked else "yolo_auto_resolve",
        "tool_type": (
            tool.tool_type if hasattr(tool, "tool_type") else str(tool)
        ),
        "decision": str(resolved) if resolved is not None else None,
        "must_gate": must_gate,
    }
    # Also record as CompletedAction for in-context visibility
    self._dynamic_context.add_action(
        tool="__yolo_auto_resolve__",
        summary=json.dumps(record, default=str),
    )
    # Write to workspace file if available
    workspace = self.prior_context.get("session_root_path")
    if workspace:
        log_path = Path(workspace) / "yolo_decisions.jsonl"
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass
```

Sample `yolo_decisions.jsonl`:

```json
{"ts": "2026-05-19T15:58:01Z", "phase": "Phase 2", "kind": "yolo_auto_resolve", "tool_type": "confirmation", "decision": "yes", "must_gate": false}
{"ts": "2026-05-19T15:58:03Z", "phase": "Phase 2", "kind": "yolo_auto_resolve", "tool_type": "single_choice", "decision": "option_a", "must_gate": false}
{"ts": "2026-05-19T15:58:30Z", "phase": "Phase 3b", "kind": "must_gate_blocked", "tool_type": "confirmation", "decision": null, "must_gate": true}
```

---

## 4. Worked Example

SOP fragment:
```
## Phase 2 -- Investigation
[__requires confirmation__] Before investigating, get confirmation.
**Tools**[__must__]: /investigate-system

## Phase 3b -- Review
[__requires confirmation__; __must__] After investigation, present findings.
```

YOLO behavior:
- Phase 2's confirmation gate: `[__requires confirmation__]` without `__must__`
  -> auto-yes. The `/investigate-system` tool IS `__must__` for tool selection
  (it must be invoked), not for the confirmation gate.
- Phase 3b: gate IS `[__requires confirmation__; __must__]` -> YOLO does NOT
  auto-resolve. In subprocess mode with `NullInteractive`, agent halts with
  `MustGateBlockedError`; exit code 2; summary prefixed `[BLOCKED ON MUST-GATE]`.

---

## 5. Concrete Code-Change List

| File | Change |
|------|--------|
| `rich_python_utils/.../sop_manager.py` | Parser: recognize `__must__` after `__requires confirmation__`; attach `must: bool` to gate nodes. Add `parse_gate_markers()`. |
| `agent_foundation/.../conversational/conversational_inferencer.py` | Add `yolo_mode: bool` attrib. Add `_sop_tracker` internal attrib. Extract `_evaluate_sop()` from `_render_prompt()`. Add `_gate_requires_user()`, `_yolo_auto_resolve()`, `_current_phase_gate()`, `_yolo_default_form_values()`, `_log_yolo_decision()`. Modify `_handle_conversation_tool()` to check YOLO first. Add `MustGateBlockedError`. Handle in `run_agentic_loop()` exception path. |
| `agent_foundation/.../conversational/yolo_helpers.py` | NEW. `_top_n_globally_ranked()` (mirrors React widget). |
| `agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2` | Add YOLO-mode section conditional (full template in chapter 6). |
| `tests/agent_foundation/.../conversational/test_yolo_mode.py` | NEW. See Section 6. |

---

## 6. Test Plan

| # | Test | Type |
|---|------|------|
| T4.1 | SOP parser: `[__requires confirmation__]` -> must=False | Unit |
| T4.2 | SOP parser: `[__requires confirmation__; __must__]` -> must=True | Unit |
| T4.3 | SOP parser: existing markers without `__must__` parse identically to before | Unit |
| T4.4 | `_yolo_auto_resolve(clarification)` reads from `yolo_vars` map | Unit |
| T4.5 | `_yolo_auto_resolve(clarification)` with missing var -> returns empty, logs warning | Unit |
| T4.6 | `_yolo_auto_resolve(confirmation)` returns "yes" by default | Unit |
| T4.7 | `_yolo_auto_resolve(confirmation)` with `yolo_default: "no"` returns "no" | Unit |
| T4.8 | `_yolo_auto_resolve(single_choice)` returns first choice | Unit |
| T4.9 | `_yolo_auto_resolve(single_choice)` with `yolo_choice_index: 2` returns third choice | Unit |
| T4.10 | `_yolo_auto_resolve(multiple_choice)` picks `yolo_pick`-marked subset | Unit |
| T4.11 | `_yolo_auto_resolve(proposal_selection)` returns top-N by rank | Unit |
| T4.12 | `_yolo_auto_resolve(tool_argument_form)` fills defaults; logs warning for required fields without defaults | Unit |
| T4.13 | `_gate_requires_user` returns True iff phase gate has must=True for confirmation/proposal_selection | Unit |
| T4.14 | `_gate_requires_user` returns False for clarification even when gate has must=True | Unit |
| T4.15 | YOLO run of 3-phase SOP with one must-gate -> halt with `MustGateBlockedError`, exit code 2 | Integration |
| T4.16 | YOLO run with no must-gates -> completes, writes `yolo_decisions.jsonl` | Integration |
| T4.17 | Prompt template renders YOLO instructions only when `yolo_mode=True` | Unit |
| T4.18 | `yolo_decisions.jsonl` contains one record per auto-resolution | Unit |
| T4.19 | `_evaluate_sop()` stores tracker on `self._sop_tracker` | Unit |
| T4.20 | `_render_prompt()` produces identical output after `_evaluate_sop()` extraction (no behavior change) | Unit |

---

## 7. Cross-References

- **Chapter 1 (Input Queue):** YOLO mode short-circuits before the queue-based input path. When auto-resolution is not possible (must-gate), the queue path is used (or `MustGateBlockedError` raised).
- **Chapter 5 (SOP Lifecycle):** `/sop` subprocess runner sets `yolo_mode=True` on the ConversationalInferencer it constructs.
- **Chapter 6 (Prompt Integration):** The YOLO prompt section is conditional on `yolo_mode`.
- **Chapter 7 (Scenarios):** Scenario 4 exercises the full YOLO+must-gate flow.
- **Chapter 8 (Roadmap):** Phase E covers this chapter (PRs E.1, E.2).

---

## 8. Open Questions

1. **Confirmation tools with `on_yes_action="open_experiment_hub"`?** In YOLO
   this would still trigger the hub creation. If the SOP author does not want
   YOLO to trigger the hub, they mark the gate `__must__`.

2. **Negative-default confirmations ("type yes to delete")?** Add
   `yolo_default: "no"` to such tools in SOP metadata. Default remains "yes"
   for forward compatibility.

3. **YOLO + interactive transports (server-attached)?** Widget IS rendered
   (user can observe), but with a "(auto-resolved)" badge and locked controls.
   Implementation detail for React layer; does not change backend.

4. **Should auto-resolved decisions count toward SOP phase completion?** Yes.
   A YOLO-auto-resolved confirmation gate advances the phase exactly as a
   user-confirmed one would. The audit log distinguishes the two.

---

*Continued in `05_sop_lifecycle.md`.*
