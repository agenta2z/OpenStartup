# RankEvolve Proposal Selection — Deep Analysis Report

**Date:** 2026-05-19  
**Scope:** How RankEvolve performs proposal selection, including the SOP workflow, interactive UI widget components, and the full end-to-end backend↔frontend pipeline.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [SOP Workflow: Phase 2b — Proposal Review & Selection](#2-sop-workflow-phase-2b--proposal-review--selection)
3. [Data Models: What a "Proposal" Is](#3-data-models-what-a-proposal-is)
4. [Proposal Parsing: How Proposals Are Extracted](#4-proposal-parsing-how-proposals-are-extracted)
5. [Conversation Tool Architecture](#5-conversation-tool-architecture)
6. [Interactive Class Hierarchy](#6-interactive-class-hierarchy)
7. [Widget Protocol Layer](#7-widget-protocol-layer)
8. [Backend: ConversationalInferencer Dispatch](#8-backend-conversationalinferencer-dispatch)
9. [ProposalSelectionHandler — Server-Side Logic](#9-proposalselectionhandler--server-side-logic)
10. [ConfirmationHandler — The "Go To Experiment Hub" Path](#10-confirmationhandler--the-go-to-experiment-hub-path)
11. [Frontend: React Widget Components](#11-frontend-react-widget-components)
12. [ProposalSelectionWidget — The Main UI Component](#12-proposalselectionwidget--the-main-ui-component)
13. [GroupedWidget — Atomic Two-Path Decision](#13-groupedwidget--atomic-two-path-decision)
14. [WebSocket Bridge: AgentServiceBridge](#14-websocket-bridge-agentservicebridge)
15. [Full End-to-End Flow Diagram](#15-full-end-to-end-flow-diagram)
16. [Key Design Patterns & Critical Findings](#16-key-design-patterns--critical-findings)
17. [Accurate File Map](#17-accurate-file-map)

---

## 1. Executive Summary

RankEvolve's proposal selection is a **multi-layered, full-stack system** that spans:

- A **Jinja2 SOP template** that instructs the LLM agent how to emit the right conversation tools
- A **Python conversation tool architecture** (type enum → handler → enrichment → input mode)
- A **three-tier interactive/widget protocol** for transporting structured UI interactions
- A **React widget system** with a dedicated `ProposalSelectionWidget` (1,132 lines of JS) and `GroupedWidget` for atomic dual-path decisions
- A **WebSocket bridge** (`AgentServiceBridge`) that persists and replays pending widgets across reconnects

**The core UX contract of Phase 2b:** The LLM emits **two conversation tools with the same `group_id`** in a single response:
1. `proposal_selection` — a rich multi-phase, multi-batch hypothesis browser with checkboxes, rank badges, impact/complexity chips, expandable PROBLEM+APPROACH details, and a custom hypothesis input.
2. `confirmation` — a single-button "📊 Go To Experiment Hub" CTA that directly opens the Experiment Hub with top-5 globally-ranked hypotheses pre-selected.

Submitting either one resolves the whole group atomically. The `GroupedWidget` renders both stacked with an **OR divider** between them.

---

## 2. SOP Workflow: Phase 2b — Proposal Review & Selection

**Source:** `src/resources/prompt_templates/conversation/main/_variables/workflow/sop.jinja2`

The SOP defines 4 sequential phases with confirmation gates:

| Phase | Name | Requires Confirmation | Key Output |
|-------|------|-----------------------|------------|
| 0 | Setup | No (collects path + strategy via clarification/single_choice) | `workflow_target_path`, `strategy` |
| 1 | Codebase Investigation | ✅ Yes, before running | `codebase_understanding` |
| 1b | Documentation Review | ✅ Yes, after docs built | Sphinx HTML docs |
| 2 | Research & Proposal | ✅ Yes, before running | `research_proposals` |
| **2b** | **Proposal Review & Selection** | ✅ **Yes — dual-path** | Selected hypotheses → Experiment Hub |

### Phase 2b verbatim instruction from SOP:

```
After the research & proposal phase completes, give the user two parallel paths
to act on the proposals — emitted as a pair of conversation tools in the SAME
response so the user picks one path or the other:

1. A `proposal_selection` tool for in-chat review and multi-select across the unified plan.
2. A `confirmation` tool styled as a single-action "📊 Go To Experiment Hub" call-to-action
   that jumps straight to the Experiment Hub with the top globally-ranked proposals pre-selected.

Tie the two tools together as one atomic decision by giving them the same group ID
(e.g., `"phase2b_review"`) — submitting either one resolves the whole group.
The confirmation tool needs to set "📊 Go To Experiment Hub" as its "yes button"'s label,
trigger corresponding action, and also hide the "no button"

DO NOT chain any further tool calls.
```

### LLM Response Format (from `initial.jinja2`)

The agent emits tool invocations inside a fenced `json ToolsToInvoke` block:

```json
{"type": "conversation", "name": "proposal_selection", "arguments": {"prompt": "...", "group_id": "phase2b_review", "view": "/path/to/unified_plan.md", "view_label": "View Full Research"}, "output": ["selected_proposals"]}
{"type": "conversation", "name": "confirmation", "arguments": {"prompt": "...", "group_id": "phase2b_review", "yes_label": "📊 Go To Experiment Hub", "on_yes_action": "open_experiment_hub", "hide_no_button": true}, "output": ["hub_opened"]}
```

---

## 3. Data Models: What a "Proposal" Is

**Source:** `src/agentic_foundation/common/ui/proposal_models.py`

```
ProposalSelectionData
├── phases: list[ProposalPhase]
│   ├── phase: int              # 1, 2, 3
│   ├── label: str              # "Quick Wins", "Core Improvements", "Exploration"
│   ├── description: str
│   ├── proposals: list[StructuredProposal]
│   │   ├── id: str             # "H1", "H2", ...
│   │   ├── rank: int           # 1 = highest priority globally
│   │   ├── title: str
│   │   ├── theme: str          # "Multi-Task Architecture", etc.
│   │   ├── source_workers: list[str]   # ["W0", "W4"] — which research worker proposed this
│   │   ├── impact: str         # "Low", "Medium", "High", "Med-High"
│   │   ├── probability: str    # "75%", "High (>70%)"
│   │   ├── complexity: str     # "Low", "Medium", "High"
│   │   ├── one_line_summary: str
│   │   ├── problem: str        # Detailed problem statement
│   │   ├── approach: str       # Proposed approach description
│   │   ├── cross_refs: str     # "Synergistic with H2, H4"
│   │   ├── slots: list[str]    # Mutually-exclusive slot memberships
│   │   └── includes: list[str] # Hypothesis IDs this combo pre-bundles
│   └── batches: list[Batch]
│       ├── id: str             # "1A", "2B"
│       ├── label: str          # "Loss & Training, Independent"
│       ├── timeline: str       # "Week 1"
│       └── hypothesis_ids: list[str]  # ["H17", "H1", ...]
├── total_count: int
├── themes: list[str]
└── combo_constraints: list[ComboConstraint]
    ├── id: str
    ├── kind: str               # "mutually_exclusive", "requires", "recommends"
    ├── hypothesis_ids: list[str]
    ├── requires_ids: list[str]
    ├── requires_any_of: bool
    ├── label: str
    ├── reason: str
    └── severity: str           # "error" | "warning" | "info"
```

**Plan v7 A3.1 constraint:** A hypothesis must be **one atomic, independently flag-gated change**. Combo-disguised hypotheses (with non-empty `includes`) trigger a soft validator warning logged at `ProposalSelectionData.from_dict()`.

**Phase mapping:**
- Phase 1 = "Quick Wins" — Low-risk, high-confidence proposals
- Phase 2 = "Core Improvements" — Medium-risk, high-impact proposals
- Phase 3 = "Exploration" — High-risk/high-reward or long-term proposals

---

## 4. Proposal Parsing: How Proposals Are Extracted

**Source:** `src/agentic_foundation/common/ui/proposal_parser.py`

The parser reads from the **aggregator's `unified_plan.md`** — located at:
- `<workspace>/checkpoints/bta/aggregator/outputs/unified_plan.md` (primary)
- `<workspace>/outputs/unified_plan.md` (fallback)

Two parsing strategies are tried in order:

### Strategy A (Primary): JSON code fence
Looks for a ` ```json proposal_summary ``` ` code fence in unified_plan.md and parses it directly as `ProposalSelectionData.from_dict()`. This is the fast, structured path.

### Strategy B (Fallback): Markdown extraction
Uses regex patterns to extract from two sections of the markdown:
1. **Priority Ranking Table** — `| Rank | ID | Name | Source Workers | Impact | Probability | Complexity | Phase | Notes |`
   - Regex: `^\|\s*(\d+)\s*\|\s*(H\d+)\s*\|...`
2. **Consolidated Proposal List** — `### Theme N: ...` headers, `#### HN: ...` hypothesis headers, `- **Attribute**: value` attribute lines
3. **Implementation Roadmap** — `### Phase N:` and `#### Batch X:` sections with hypothesis tables

### Strategy C (Last resort): Table-only fallback
If both A and B fail, extracts rank-only data from just the Priority Ranking Table rows with no detail fields populated.

---

## 5. Conversation Tool Architecture

**Source:** `src/agentic_foundation/common/inferencers/agentic_inferencers/conversational/conversation_tools.py`

### ConversationToolType Enum

```python
class ConversationToolType(str, enum.Enum):
    CLARIFICATION = "clarification"        # Free-text input (path autocomplete supported)
    SINGLE_CHOICE = "single_choice"        # Radio-button style, one selection
    MULTIPLE_CHOICE = "multiple_choice"    # Checkbox style, multiple selections
    CONFIRMATION = "confirmation"          # Yes/No with optional tool config panel
    TOOL_ARGUMENT_FORM = "tool_argument_form"  # Form for tool parameters
    PROPOSAL_SELECTION = "proposal_selection"  # Rich hypothesis browser (THE main widget)
```

### ConversationTool Dataclass

Key fields relevant to Phase 2b:
- `tool_type: ConversationToolType`
- `prompt: str`
- `output_vars: list[str]` — variable names to capture result into (e.g., `["selected_proposals"]`)
- `metadata: dict[str, Any]` — extension point carrying:
  - `group_id` — ties tools into an atomic resolution group
  - `on_group_resolve` — `"flatten"` | `"hide"` | `"keep"` (persisted card behavior)
  - `on_yes_action` — server-side side effect: `"open_experiment_hub"`
  - `hide_no_button` — bool, for single-action CTA mode

### Handler Registry

Every `ConversationToolType` must have exactly one registered handler. The `ConversationalInferencer.__attrs_post_init__` validates completeness at construction time — missing handlers raise `ValueError`.

```python
# handlers/__init__.py → default_registry()
{
    CLARIFICATION      → ClarificationHandler
    SINGLE_CHOICE      → SingleChoiceHandler
    MULTIPLE_CHOICE    → MultipleChoiceHandler
    CONFIRMATION       → ConfirmationHandler
    TOOL_ARGUMENT_FORM → ToolArgumentFormHandler
    PROPOSAL_SELECTION → ProposalSelectionHandler
}
```

---

## 6. Interactive Class Hierarchy

**Sources:** `src/agentic_foundation/common/ui/interactive_base.py`, `rich_interactive_base.py`, `web_interactive.py`, `queue_interactive.py`

```
InteractiveBase (abstract)
├── get_input() → Any            # Synchronous input retrieval
├── aget_input() → Any           # Async wrapper (asyncio.to_thread)
├── send_response(response, flag) # Deliver response + reset input state
├── asend_response(...)           # Async wrapper
├── reset_input(flag)             # Abstract — reset input state
├── _get_input() → Any            # Abstract — transport-specific retrieval
└── _send_response(response, flag) # Abstract — transport-specific delivery

    InteractionFlags (enum):
    ├── PendingInput    — awaiting user input
    ├── MessageOnly     — display only, no input needed
    └── TurnCompleted   — turn is done

RichInteractiveBase(InteractiveBase)
├── _current_input_mode: InputModeConfig | None
├── _pending_input_mode: InputModeConfig | None
├── send_response(..., input_mode=...) — sets _current_input_mode
├── get_input() — calls _postprocess_input() to map structured UI → semantic value
├── _postprocess_input(raw, input_mode) → Any
├── _resolve_structured_input(user_input, input_mode) → str
├── _resolve_single_choice(data, input_mode) → str
└── _resolve_multiple_choices(data, input_mode) → str (pipe-delimited)

    WebUIInteractive(RichInteractiveBase)  [src/webui path]
    ├── supports_widgets → True
    ├── _input_queue: asyncio.Queue
    ├── _response_queue: asyncio.Queue
    ├── _pending_widget_id: str | None
    ├── push_input(data)           — WebSocket handler pushes received data
    ├── pull_response()            — WebSocket handler reads outbound messages
    ├── send_widget(widget_message) → WidgetResponse  [async, awaitable]
    ├── send_display_widget(widget_message)            [display only]
    └── _wait_for_widget_response(widget_id) → WidgetResponse

    QueueInteractive(RichInteractiveBase)  [file-queue path, production]
    ├── _get_input() — reads from file queue
    └── _send_response() — writes to file queue
```

**Critical note:** The `proposal_selection` and `confirmation` conversation tools do **NOT** use `WebUIInteractive.send_widget()` directly. Instead, they go through `asend_response(input_mode=grouped_mode)` which uses `InputModeConfig.metadata["widget_type"]` to signal the frontend which React component to render. The `send_widget()` path is reserved for a separate, lower-level widget protocol.

---

## 7. Widget Protocol Layer

**Source:** `src/agentic_foundation/common/ui/widget_protocol.py`, `input_modes.py`

### InputModeConfig (the primary channel for conversation tools)

```python
@dataclass
class InputModeConfig:
    mode: InputMode           # FREE_TEXT, SINGLE_CHOICE, MULTIPLE_CHOICES, etc.
    prompt: str
    options: List[ChoiceOption]  # For SINGLE_CHOICE / MULTIPLE_CHOICES
    allow_custom: bool
    metadata: Dict[str, Any]  # KEY field — carries widget_type, group_id, proposals, etc.
```

For Phase 2b, the `grouped_mode` that gets sent is:
```python
InputModeConfig(
    mode=InputMode.FREE_TEXT,
    prompt=assistant_text,
    metadata={
        "widget_type": "grouped",      # → triggers GroupedWidget in React
        "group_id": "phase2b_review",
        "tools": [
            {
                "child_id": "tool0",
                "tool_type": "proposal_selection",
                "prompt": "...",
                "input_mode": {        # proposal_selection's own InputModeConfig.to_dict()
                    "mode": "free_text",
                    "metadata": {
                        "widget_type": "proposal_selection",  # → ProposalSelectionWidget
                        "proposals": { "phases": [...], "total_count": N, ... },
                        "view": "/path/to/unified_plan.md",
                        "view_label": "View Full Research",
                    }
                },
                "metadata": { "group_id": "phase2b_review", "on_group_resolve": "flatten" }
            },
            {
                "child_id": "tool1",
                "tool_type": "confirmation",
                "prompt": "...",
                "input_mode": {
                    "mode": "free_text",
                    "metadata": {
                        "widget_type": "confirmation",
                        "yes_label": "📊 Go To Experiment Hub",
                        "hide_no_button": true,
                        "on_yes_action": "open_experiment_hub",
                    }
                },
                "metadata": { "group_id": "phase2b_review", "on_group_resolve": "flatten", ... }
            }
        ]
    }
)
```

### WidgetMessage / WidgetResponse (lower-level, tool_argument_form path)

```python
@dataclass
class WidgetMessage:
    widget_id: str
    widget_type: str    # WIDGET_TEXT_INPUT, WIDGET_SINGLE_CHOICE, etc.
    title: str
    description: str
    input_mode: InputModeConfig | None
    fields: list[WidgetField]   # For compound tool_argument_form
    metadata: dict[str, Any]

@dataclass
class WidgetResponse:
    widget_id: str
    values: dict[str, Any]
    action: str   # "submit" | "cancel" | "skip" | "timeout"
```

Widget type constants:
```python
WIDGET_TEXT_INPUT = "text_input"
WIDGET_SINGLE_CHOICE = "single_choice"
WIDGET_MULTIPLE_CHOICE = "multiple_choice"
WIDGET_DROPDOWN = "dropdown"
WIDGET_TOGGLE = "toggle"
WIDGET_TOOL_ARGUMENT_FORM = "tool_argument_form"
```

---

## 8. Backend: ConversationalInferencer Dispatch

**Source:** `src/agentic_foundation/common/inferencers/agentic_inferencers/conversational/conversational_inferencer.py`

### Agentic Loop (simplified)

```
run_agentic_loop(content, interactive, session_id)
  for iteration in range(max_iterations):
    1. _compress_context_if_needed()
    2. rendered = _render_prompt(content)   # Jinja2 with SOP, status, tools
    3. raw_response = ainfer_streaming(rendered) or ainfer(rendered)
    4. conv_response = parse_conversation_response(raw_response)
    5. if conv_response.has_conversation_tool:
         collected = await _handle_conversation_tools(
             conv_response.conversation_tools,
             conv_response.text,
             interactive_override=effective_interactive,
             action_tools=conv_response.action_tools,
         )
         → add collected to conversation history
         → continue loop
    6. elif action_tools:
         → execute action tools
         → continue loop
    7. else: return AgenticResult
```

### `_handle_conversation_tools` — The Dispatcher

```
_handle_conversation_tools(tools, assistant_text, interactive_override, action_tools)
  if len(tools) > 1:
    group_ids = [t.metadata.get("group_id") for t in tools]
    shared_gid = group_ids[0]
    if shared_gid AND all(g == shared_gid for g in group_ids):
      # ← Phase 2b enters here
      return await _handle_rich_group(tools, ..., group_id=shared_gid)
    elif mixed group_ids:
      # WARNING: LLM forgot to set group_id on a sibling
      # Fall through to scalar path

  # scalar-only bundle guard:
  for t in tools:
    if t.tool_type not in {CLARIFICATION, SINGLE_CHOICE, MULTIPLE_CHOICE, TOOL_ARGUMENT_FORM}:
      raise ValueError("Rich-response tool cannot be bundled")

  if len(tools) == 1:
    # Single-tool path: enrich_before_send → _handle_conversation_tool
    handler.enrich_before_send(tool, ctx)
    return {var_name: result}

  # Multi-tool scalar compound: MultiInputWidget
  ...
```

### `_handle_rich_group` — Phase 2b Path

```
_handle_rich_group(tools, assistant_text, interactive_override, action_tools, group_id)
  # 1. Enrich each child separately
  for idx, tool in enumerate(tools):
    handler = registry.require(tool.tool_type)
    await handler.enrich_before_send(tool, ctx)   # loads proposals, view, etc.
    mode = handler.build_input_mode(tool, ctx)    # creates child InputModeConfig
    child_configs.append({
        "child_id": f"tool{idx}",
        "tool_type": ...,
        "prompt": ...,
        "input_mode": mode.to_dict(),
        "output_var": ...,
        "metadata": dict(tool.metadata),
    })

  # 2. Bundle into a single grouped envelope
  grouped_mode = InputModeConfig(
      mode=InputMode.FREE_TEXT,
      prompt=assistant_text,
      metadata={"widget_type": "grouped", "group_id": group_id, "tools": child_configs}
  )

  # 3. Send to frontend (serialized as pending_input)
  await active_interactive.asend_response(
      assistant_text,
      flag=InteractionFlags.PendingInput,
      input_mode=grouped_mode,
  )

  # 4. Wait for user response
  user_input = await active_interactive.aget_input()

  # 5. Decode {submitted_child, payload}
  submitted_child_id = values["submitted_child"]
  payload = values["payload"]

  # 6. Route to the submitted child's handler ONLY
  submitted_tool = tools[submitted_idx]
  handler = registry.require(submitted_tool.tool_type)
  result = await handler.handle_response(submitted_tool, payload, ctx)

  # 7. Apply effects (ApplyContextUpdates, OverrideNextActionToolArgs, etc.)
  for effect in result.effects:
    await effect.apply(self)

  # 8. Return only the submitted child's output var
  return {var_name: result.text}
```

---

## 9. ProposalSelectionHandler — Server-Side Logic

**Source:** `src/agentic_foundation/common/inferencers/agentic_inferencers/conversational/handlers/proposal_selection.py`

### build_input_mode

Creates an `InputModeConfig` with `metadata["widget_type"] = "proposal_selection"`. This string is the key that the React `WidgetRegistry` uses to select `ProposalSelectionWidget`.

```python
def build_input_mode(self, tool, ctx) -> InputModeConfig:
    metadata = {"widget_type": "proposal_selection"}
    if tool.metadata:
        metadata.update(tool.metadata)  # merges proposals, view, etc.
    return InputModeConfig(mode=InputMode.FREE_TEXT, prompt=tool.prompt, metadata=metadata)
```

### enrich_before_send (proposal data injection — two paths)

**Path 1 (Primary):** Reads `phase_outputs["research_proposals_data"]` (stored as JSON string by `_exec_research_propose`), deserializes it, and sets `tool.metadata["proposals"]`.

**Path 2 (Fallback):** If `research_proposals_data` is absent, reads `phase_outputs["research_proposals"]` (workspace path), calls `parse_proposals(workspace)`, and sets `tool.metadata["proposals"] = data.to_dict()`.

**Path 3 (View button):** If `phase_outputs["unified_plan_path"]` exists, sets `tool.metadata["view"]` and `tool.metadata["view_label"] = "View Full Research"`.

### handle_response

Receives: `{"selected_proposals": ["H1", "H3"], "custom_queries": ["..."], "total_available": N}`

Processing:
1. Iterates `proposals_data["phases"]` to match selected IDs → `selected_details` (full dicts)
2. Groups by phase label → human-readable text summary
3. Emits `ApplyContextUpdates({"_selected_proposals": ..., "_custom_queries": ...})`
4. If `HubAwareToolExecutor` available AND `selected_details` non-empty → calls `create_hub()`:
   - `executor.create_experiment_hub(selected_details, proposals_data, custom_queries, group_by="batch")`
   - Appends Hub announcement to result text

### create_hub / format_hub_announcement

```python
HUB_ANNOUNCEMENT_TEMPLATE = (
    "Experiment Hub created. {n} hypotheses{group_suffix} queued. "
    "The system will execute them sequentially. Do NOT invoke /task manually."
)

async def create_hub(executor, selected_details, proposals_data, custom_queries, group_by="batch"):
    multi_task_id = await executor.create_experiment_hub(
        selected_details, proposals_data,
        custom_queries=custom_queries, group_by=group_by
    )
    summary = format_hub_announcement(len(selected_details), group_by=group_by)
    return multi_task_id, summary
```

---

## 10. ConfirmationHandler — The "Go To Experiment Hub" Path

**Source:** `src/agentic_foundation/common/inferencers/agentic_inferencers/conversational/handlers/confirmation.py`

### build_input_mode

Builds `InputModeConfig` with `metadata["widget_type"] = "confirmation"` and passes through all of:
- `yes_label`, `no_label`, `hide_no_button`
- `on_yes_action`, `on_group_resolve`
- `view`, `view_label`
- `tool_params` (populated from tool registry — shows inline config panel for associated action tool)

### handle_response

Receives: `{"choice": "yes" | "no"}` or a richer `{"choice": ..., "param_overrides": ..., "variables": ...}`

When `choice == "yes"` AND `on_yes_action == "open_experiment_hub"`:
- Calls `_dispatch_open_experiment_hub(ctx)`
- Reads `phase_outputs["research_proposals_data"]` (same JSON-string → dict deserialization)
- Calls `executor.open_experiment_hub(proposals_data, pre_select_top_n=5, initial_view="selection")`
- Returns a system sentinel message telling the LLM that the Hub is active and **NOT** to call `/experiment` or `/task` manually

**DEFAULT_TOP_N_GLOBAL = 5** — both the frontend `ProposalSelectionWidget` and the backend `open_experiment_hub` must agree on this value so both Phase 2b paths offer the same default pre-selection.

Effects applied on YES:
- `ApplyContextUpdates({"_confirmation_gate_passed": True})`
- `SetTurnVariables({"_grouped_action_multi_task_id": ..., "_grouped_action_name": "open_experiment_hub"})`

---

## 11. Frontend: React Widget Components

**Source:** `src/webui/react/src/components/widgets/`

### WidgetRegistry.js — Central Dispatch

```javascript
const WIDGET_REGISTRY = {
  'text_input':         TextInputWidget,
  'free_text':          TextInputWidget,
  'single_choice':      SingleChoiceWidget,
  'multiple_choice':    MultipleChoiceWidget,
  'multiple_choices':   MultipleChoiceWidget,
  'dropdown':           DropdownWidget,
  'toggle':             ToggleWidget,
  'confirmation':       ConfirmationWidget,
  'tool_argument_form': ToolArgumentFormWidget,
  'multi_input':        MultiInputWidget,     // scalar compound (tabbed)
  'grouped':            GroupedWidget,         // rich-group (stacked with OR divider)
  'proposal_selection': ProposalSelectionWidget, // ← Phase 2b primary widget
  'default':            DefaultWidget,
};

export function getWidget(type) {
  return WIDGET_REGISTRY[type] || WIDGET_REGISTRY['default'];
}
```

### Complete Widget Inventory

| Widget Component | Type String | Purpose |
|-----------------|-------------|---------|
| `TextInputWidget` | `text_input`, `free_text` | Free-text input, path autocomplete |
| `SingleChoiceWidget` | `single_choice` | Radio buttons + optional custom text + editable textarea |
| `MultipleChoiceWidget` | `multiple_choice` | Checkboxes + optional custom text |
| `DropdownWidget` | `dropdown` | Select dropdown |
| `ToggleWidget` | `toggle` | Boolean toggle |
| `ConfirmationWidget` | `confirmation` | Yes/No + optional tool config panel |
| `ToolArgumentFormWidget` | `tool_argument_form` | Parameterized tool config form |
| `MultiInputWidget` | `multi_input` | Tabbed compound scalar widgets |
| **`GroupedWidget`** | **`grouped`** | **Stacked rich widgets with OR divider — Phase 2b** |
| **`ProposalSelectionWidget`** | **`proposal_selection`** | **Main hypothesis browser — Phase 2b** |
| `DefaultWidget` | `default` | Generic fallback |

---

## 12. ProposalSelectionWidget — The Main UI Component

**Source:** `src/webui/react/src/components/widgets/ProposalSelectionWidget.js` (1,132 lines)

### Sub-components

```
ProposalSelectionWidget           ← top-level export
├── HypothesisCard                ← individual proposal card
│   ├── Checkbox (MUI)            ← selection toggle
│   ├── Rank badge (🥇🥈🥉 or number)
│   ├── Hypothesis ID chip (H1, H2...)
│   ├── Title
│   ├── Impact Chip (MUI Chip, color: error/warning/default)
│   ├── Complexity Chip (color: error/warning/success)
│   ├── Source workers chip
│   ├── _overrideMeta chip (if rank was overridden by learnings)
│   ├── deprioritized chip (if deprioritized by learnings)
│   └── Collapse → PROBLEM + APPROACH detail fields
└── BatchSection                  ← groups cards by batch
    ├── Batch-level Checkbox (indeterminate support)
    ├── Batch label + timeline
    ├── selected/total counter
    └── list of HypothesisCard
```

### Layout Structure

```
[Header: "N hypotheses across M phases"]
[Phase Tabs: Quick Wins | Core Improvements | Exploration]
  [per-phase content:]
  [BatchSection 1A]
    [HypothesisCard H1]  [HypothesisCard H3]  ...
  [BatchSection 1B]
    ...
  [Add Custom Hypothesis: TextField + Add button]
[Footer action bar:]
  [Show Top N toggle + N selector]
  [AutoMode switch (with first-toggle dialog)]
  [View Full Research button (if view set)]
  [N selected count badge]
  [▶ Start Autopilot / ⚙ Implement Selected button]

[AutoMode status pill (during run):]
  [phase label + iteration count + Stop button]
```

### Default Pre-Selection Algorithm

```javascript
const DEFAULT_TOP_N_GLOBAL = 5;

function selectTopNGlobally(phases, n) {
  const all = [];
  for (const ph of (phases || [])) {
    for (const p of (ph?.proposals || [])) {
      if (p && p.id) all.push(p);
    }
  }
  all.sort((a, b) => {
    // Primary: lower rank = higher priority
    const ra = Number.isFinite(a.rank) ? a.rank : 9999;
    const rb = Number.isFinite(b.rank) ? b.rank : 9999;
    if (ra !== rb) return ra - rb;
    // Tiebreaker 1: more source_workers = better validated → higher priority
    const wa = (a.source_workers || []).length;
    const wb = (b.source_workers || []).length;
    if (wa !== wb) return wb - wa;  // descending
    // Tiebreaker 2: lexical id for determinism
    return String(a.id).localeCompare(String(b.id));
  });
  const k = Math.max(1, Number.isFinite(n) ? n : DEFAULT_TOP_N_GLOBAL);
  return all.slice(0, k).map(p => p.id);
}
```

**Critical design requirement:** This sort order `(rank ASC, -source_workers_len DESC, id ASC)` **must match** `tool_executor.py:open_experiment_hub`'s `pre_select_top_n` tiebreaker chain so both Phase 2b paths (in-chat selection vs Hub direct-open) show the same default selection.

### Submission Payload (sent from ProposalSelectionWidget to backend)

```javascript
onSubmit({
  selected_proposals: [...selectedIds],  // list of "H1", "H3", ...
  custom_queries: [...customQueryStrings],
  total_available: allProposals.length,
})
```

### State & Hooks

- `useSession()` — access session context (session_id, etc.)
- `useProposalOverrides()` — rank/deprioritization overrides from accumulated learnings
- `useComboOverrides()` — combo constraint overrides
- `mergeOverrides(baseProposalsData, proposalOverrides, comboOverrides)` — applies overrides at READ time
- `useAutopilot(DEFAULT_AUTOPILOT_SETTINGS)` — manages autopilot chain state machine

### Autopilot Integration

The widget has an "Auto Mode" toggle (MUI Switch). When enabled:
1. Shows a first-toggle confirmation dialog
2. On confirm: runs "Implement Selected" → "Refresh Learnings" → "Apply eligible combos" in a chain
3. Status pill shows current phase + iteration count + Stop button
4. Uses `useAutopilot` hook's state machine with phases: `idle`, `awaiting_implement`, `awaiting_refresh`, `applying_combos`, `completed`, `stopped`

---

## 13. GroupedWidget — Atomic Two-Path Decision

**Source:** `src/webui/react/src/components/widgets/GroupedWidget.js`

### Layout

```
GroupedWidget (config.input_mode.metadata = {widget_type: "grouped", group_id: "...", tools: [...]})
├── ChildComponent[0]            ← ProposalSelectionWidget (tool0)
│   └── (rendered with childConfig, onSubmit=(resp) => handleChildSubmit("tool0", resp))
├── OrDivider()                  ← "—— OR ——" visual separator
└── ChildComponent[1]            ← ConfirmationWidget (tool1)
    └── (rendered with childConfig, onSubmit=(resp) => handleChildSubmit("tool1", resp))
```

### Child Widget Type Resolution

```javascript
const childWidgetType =
  child?.input_mode?.metadata?.widget_type   // "proposal_selection" or "confirmation"
  || child?.tool_type                         // fallback
  || child?.input_mode?.mode                 // second fallback
  || 'default';
const ChildComponent = getWidget(childWidgetType);
```

### Submit Routing

When either child submits:
```javascript
handleChildSubmit(childId, childResponse) {
  onSubmit({
    submitted_child: childId,   // "tool0" or "tool1"
    payload: childResponse,     // child's response dict
  });
}
```

The backend (`_handle_rich_group`) receives this envelope, routes to the submitted child's `handle_response`, and ignores the sibling — completing the atomic group resolution.

---

## 14. WebSocket Bridge: AgentServiceBridge

**Source:** `src/webui/backend/services/agent_service_bridge.py`

### Widget Persistence

The bridge persists the current pending widget to `<session_dir>/pending_widget.json` using `_atomic_write_pending_widget()` (tempfile + `os.replace`). On WebSocket reconnect, this file is replayed to the client so the user sees the same widget without needing to re-submit or re-trigger the LLM.

Widget ID is deterministically computed from content hash (SHA256[:16] of `{content, input_mode}`) so the React reducer can de-duplicate live-broadcast vs. replay-on-reconnect without re-rendering.

```python
def _compute_widget_id(payload: dict) -> str:
    canonical = json.dumps(
        {"content": payload.get("content", ""),
         "input_mode": payload.get("input_mode") or {}},
        sort_keys=True, default=str
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

### Response dispatch

```python
async def _dispatch_response(self, response: dict, send: SendCallback):
    flag = response.get("flag")
    if flag == InteractionFlags.PendingInput:
        # Contains widget config → persist + send to client
        _atomic_write_pending_widget(pending_widget_path, payload)
        await send({"type": "pending_input", "widget": widget_dict, ...})
    elif flag == InteractionFlags.MessageOnly:
        await send({"type": "widget_update", ...})
    elif flag == InteractionFlags.TurnCompleted:
        clear_pending_widget(session_dir)
        await send({"type": "message_end", ...})
```

---

## 15. Full End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 2b FLOW                                   │
│                                                                         │
│  SOP template → LLM emits ToolsToInvoke block with 2 tools:           │
│    {"name":"proposal_selection","arguments":{"group_id":"phase2b_review",...}}│
│    {"name":"confirmation","arguments":{"group_id":"phase2b_review",    │
│      "on_yes_action":"open_experiment_hub","hide_no_button":true,...}} │
│                              │                                          │
│                              ▼                                          │
│  parse_conversation_response() → [ConversationTool, ConversationTool]  │
│                              │                                          │
│                              ▼                                          │
│  _handle_conversation_tools()                                           │
│    ↳ detect shared group_id "phase2b_review"                           │
│    ↳ route to _handle_rich_group()                                     │
│                              │                                          │
│                              ▼                                          │
│  ProposalSelectionHandler.enrich_before_send()                        │
│    ↳ loads proposals from phase_outputs["research_proposals_data"]     │
│    ↳ sets tool.metadata["proposals"] = {phases:[...], total_count:N}  │
│    ↳ sets tool.metadata["view"] = "/path/to/unified_plan.md"          │
│                              │                                          │
│  ConfirmationHandler.enrich_before_send()                             │
│    ↳ resolves tool_params, view, view_label from tool_registry        │
│    ↳ sets metadata["yes_label"], "hide_no_button", "on_yes_action"    │
│                              │                                          │
│                              ▼                                          │
│  _handle_rich_group bundles into grouped InputModeConfig:              │
│    metadata = {                                                          │
│      "widget_type": "grouped",                                          │
│      "group_id": "phase2b_review",                                      │
│      "tools": [                                                          │
│        {child_id:"tool0", tool_type:"proposal_selection",              │
│         input_mode:{metadata:{widget_type:"proposal_selection",        │
│                               proposals:{phases:[...]}, ...}}},        │
│        {child_id:"tool1", tool_type:"confirmation",                    │
│         input_mode:{metadata:{widget_type:"confirmation",              │
│                               hide_no_button:true, ...}}},             │
│      ]                                                                  │
│    }                                                                    │
│                              │                                          │
│                              ▼                                          │
│  asend_response(text, flag=PendingInput, input_mode=grouped_mode)     │
│    → QueueInteractive / WebUIInteractive serializes + sends            │
│                              │                                          │
│                              ▼                                          │
│  AgentServiceBridge                                                     │
│    → _atomic_write_pending_widget("pending_widget.json")               │
│    → WebSocket send({type:"pending_input", widget:{...}})              │
│                              │                                          │
│                              ▼                                          │
│  ┌─── REACT FRONTEND ────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  getWidget("grouped") → GroupedWidget                             │ │
│  │  ├── getWidget("proposal_selection") → ProposalSelectionWidget    │ │
│  │  │   ├── Phase tabs (Quick Wins | Core | Exploration)             │ │
│  │  │   ├── BatchSections with HypothesisCards (checkboxes)         │ │
│  │  │   ├── Default: top-5 globally pre-selected                    │ │
│  │  │   ├── Impact/Complexity chips, rank badges                    │ │
│  │  │   ├── Expandable PROBLEM+APPROACH detail                      │ │
│  │  │   ├── Custom hypothesis text input                            │ │
│  │  │   └── "⚙ Implement Selected" button → onSubmit({             │ │
│  │  │         selected_proposals:[...], custom_queries:[...],       │ │
│  │  │         total_available:N})                                   │ │
│  │  ├── ── OR ──                                                     │ │
│  │  └── getWidget("confirmation") → ConfirmationWidget              │ │
│  │      └── "📊 Go To Experiment Hub" button (NO button hidden)     │ │
│  │          → onSubmit("yes")                                        │ │
│  │                                                                    │ │
│  │  User clicks ONE → GroupedWidget.handleChildSubmit(id, resp)     │ │
│  │  → onSubmit({submitted_child:"tool0"|"tool1", payload:{...}})    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              │                                          │
│                              ▼                                          │
│  AgentServiceBridge receives widget response                            │
│  → clear_pending_widget()                                               │
│  → pushes to QueueInteractive input queue                               │
│                              │                                          │
│                              ▼                                          │
│  _handle_rich_group decodes {submitted_child, payload}                  │
│                              │                                          │
│    PATH A: submitted_child="tool0" (proposal_selection)                 │
│    ProposalSelectionHandler.handle_response({                           │
│      selected_proposals:["H1","H3"], custom_queries:[], total:N})      │
│    ↳ match IDs to full proposal dicts                                   │
│    ↳ emit ApplyContextUpdates({_selected_proposals, _custom_queries})  │
│    ↳ if HubAwareToolExecutor: create_hub() → Experiment Hub created    │
│                              │                                          │
│    PATH B: submitted_child="tool1" (confirmation)                       │
│    ConfirmationHandler.handle_response({"choice":"yes"})                │
│    ↳ on_yes_action="open_experiment_hub"                                │
│    ↳ executor.open_experiment_hub(proposals_data, pre_select_top_n=5)  │
│    ↳ Hub tab opens in UI with top-5 pre-selected                       │
│    ↳ system sentinel: "Do NOT call /task manually"                      │
│                              │                                          │
│                              ▼                                          │
│  Experiment Hub active → user adjusts selections → Implement Selected  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 16. Key Design Patterns & Critical Findings

### 16.1 Group ID Atomic Resolution (Plan v3)

The Phase 2b dual-path UX is implemented as a **strict group_id equality gate**:
- ALL tools in one LLM response must share the **same non-empty** `group_id`
- Mixed group_ids → WARNING + falls through to scalar-only compound path
- The backend only runs `handle_response` on the **submitted child** — sibling cards are persisted as read-only via `_apply_group_resolution`

### 16.2 Rich vs. Scalar Bundling Guard

`proposal_selection` and `confirmation` are **rich-response tools** — their response payloads are structured dicts, not scalars. The code explicitly prevents them from being bundled via the scalar `MultiInputWidget` path:
```python
_bundle_scalar_allow = {CLARIFICATION, SINGLE_CHOICE, MULTIPLE_CHOICE, TOOL_ARGUMENT_FORM}
for t in tools:
    if t.tool_type not in _bundle_scalar_allow:
        raise ValueError("Rich-response tool cannot be bundled")
```
They can ONLY go through `_handle_rich_group`.

### 16.3 Two Proposal Data Injection Paths

The `enrich_before_send` tries two sources in order:
1. **Pre-parsed JSON string** in `phase_outputs["research_proposals_data"]` — stored by `_exec_research_propose` as `json.dumps(proposals_data.to_dict())`
2. **Workspace path** in `phase_outputs["research_proposals"]` — triggers `parse_proposals()` which tries Strategy A (JSON fence) → Strategy B (markdown) → Strategy C (table only)

This dual-path ensures the widget can render proposals even if the primary pre-parsed path fails.

### 16.4 DEFAULT_TOP_N_GLOBAL = 5 — Byte-Level Sync Requirement

Both frontend (`ProposalSelectionWidget.js:DEFAULT_TOP_N_GLOBAL = 5`) and backend (`tool_executor.py:open_experiment_hub(pre_select_top_n=5)`) must agree on this constant. The sort key `(rank ASC, -source_workers DESC, id ASC)` must also match byte-for-byte between the two paths.

### 16.5 Widget Persistence via AgentServiceBridge

The `pending_widget.json` file provides crash/reconnect resilience — the widget is re-delivered to the client on WebSocket reconnect WITHOUT needing the LLM to re-generate it. The content-hash widget_id prevents duplicate renders.

### 16.6 ClarificationHandler — Path Autocomplete

In Phase 0, the `clarification` tool is used with `expected_input_type: "path"` and `prefix: session_root_path`. This is what enables the path autocomplete in the UI — `ClarificationHandler.build_input_mode` sets `metadata["expected_input_type"] = "path"` and `metadata["prefix"] = tool.prefix`.

### 16.7 Plan v7 A3.1 — Combo-Disguised Hypothesis Detection

`ProposalSelectionData.from_dict()` has a soft validator that logs a WARNING if any proposal has a non-empty `includes` list (combo-disguised as hypothesis). This ensures the unified plan's atomic-hypothesis constraint is monitored without breaking existing sessions.

### 16.8 Override & Learning Integration

The widget integrates with two override hooks:
- `useProposalOverrides()` → applied rank changes + deprioritization from accumulated experiment learnings
- `useComboOverrides()` → combo constraint overrides from the Combo Hub
- `mergeOverrides()` → merges at READ time (does not mutate the canonical proposals data)

This allows the widget to reflect learning from prior experiment iterations.

---

## 17. Accurate File Map

```
src/
├── resources/
│   ├── prompt_templates/
│   │   └── conversation/main/_variables/workflow/
│   │       └── sop.jinja2                              # THE SOP definition (Phase 0–2b)
│   │   └── conversation/main/
│   │       └── initial.jinja2                          # Main conversation template + Decision Procedure
│   │   └── unified_proposal/main/
│   │       └── initial.jinja2                          # Unified proposal synthesis template
│   └── tools/
│       └── proposal_selection/
│           └── tool.json                               # Tool schema + documentation for LLM
│
├── agentic_foundation/common/
│   ├── ui/
│   │   ├── interactive_base.py                         # Abstract base + InteractionFlags
│   │   ├── rich_interactive_base.py                    # Adds InputMode postprocessing
│   │   ├── web_interactive.py                          # WebSocket transport (asyncio.Queue)
│   │   ├── queue_interactive.py                        # File-queue transport (production)
│   │   ├── input_modes.py                              # InputMode enum + InputModeConfig
│   │   ├── widget_protocol.py                          # WidgetMessage/WidgetResponse (lower-level)
│   │   ├── proposal_models.py                          # StructuredProposal, ProposalPhase, etc.
│   │   └── proposal_parser.py                          # Parse unified_plan.md → ProposalSelectionData
│   └── inferencers/agentic_inferencers/conversational/
│       ├── conversation_tools.py                       # ConversationToolType + ConversationTool
│       ├── conversational_inferencer.py                # Agentic loop + _handle_rich_group
│       ├── handler_protocol.py                         # ConversationToolHandler ABC
│       ├── handler_registry.py                         # Per-instance handler registry
│       └── handlers/
│           ├── proposal_selection.py                   # ProposalSelectionHandler (THE main handler)
│           ├── confirmation.py                         # ConfirmationHandler + open_experiment_hub
│           ├── clarification.py                        # ClarificationHandler (free-text/path)
│           ├── single_choice.py                        # SingleChoiceHandler
│           └── multiple_choice.py                      # MultipleChoiceHandler
│
└── webui/
    ├── backend/
    │   ├── main.py                                     # FastAPI app + route registration
    │   ├── routes/
    │   │   ├── agent_websocket_routes.py               # WebSocket endpoint + message loop
    │   │   ├── chat_routes.py                          # REST: /send, /action, /progress
    │   │   └── proposal_overrides_routes.py            # REST: proposal override CRUD
    │   └── services/
    │       ├── agent_service_bridge.py                 # WebSocket↔Queue bridge + widget persistence
    │       └── experiment_service.py                   # Experiment state management
    └── react/src/
        ├── components/widgets/
        │   ├── WidgetRegistry.js                       # type string → React component map
        │   ├── ProposalSelectionWidget.js              # THE main widget (1132 lines)
        │   ├── GroupedWidget.js                        # Atomic 2-path decision (OR divider)
        │   ├── ConfirmationWidget.js                   # Yes/No CTA widget
        │   ├── SingleChoiceWidget.js                   # Radio + editable textarea
        │   ├── MultipleChoiceWidget.js                 # Checkboxes
        │   ├── TextInputWidget.js                      # Free text + path autocomplete
        │   ├── DropdownWidget.js                       # Select dropdown
        │   ├── ToggleWidget.js                         # Boolean toggle
        │   └── MultiInputWidget.js                     # Tabbed scalar compound
        └── hooks/
            ├── useProposalOverrides.js                 # Proposal rank/deprio overrides
            ├── useComboOverrides.js                    # Combo constraint overrides
            └── useAutopilot.js                         # Autopilot chain state machine
```

---

*Analysis conducted by Rovo Dev — 2026-05-19. All findings are based on direct source code inspection across 30+ files spanning the SOP template, Python backend, and React frontend.*
