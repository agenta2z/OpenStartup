# Conversational Inferencer: Background Jobs, SOPs, and Autonomous Execution

> **Author:** Claude Code  
> **Date:** 2026-05-19  
> **Status:** Design proposal  
> **Codebases:**  
> - `AgentFoundation/src/agent_foundation/` (primary — inferencer, jobs, SOP registry)  
> - `OpenStartup/src/openteam/` (server integration — session store, conversation service, tool dispatch)  
> - `RichPythonUtils/src/rich_python_utils/` (SOP parser)

---

## The Problem

The conversational inferencer today is **synchronous and single-threaded in its interaction model**: one user message in, one agent response out, blocking until the human types again. This makes three important workflows impossible:

1. **Long-running work in the background.** The agent can't start a task and come back to the user later. Every tool call blocks the conversation.

2. **Autonomous SOP execution.** SOPs like `code_optimization.md` define multi-phase workflows with confirmation gates. There's no way to run one headlessly (skipping non-critical confirmations) in a subprocess while the user continues other work.

3. **Cheap, fast task execution.** Every `/task` invocation triggers the full dual-agent consensus topology (4–8 subprocesses, 100k+ tokens, 5–15 minutes). Most single-shot requests need one LLM call, not a committee.

These three problems are **coupled**: background jobs need an input queue to deliver completion events; SOP subprocesses need YOLO mode to run unattended; and simple-mode tasks are what make background task fan-out practical (5× a 30-second leaf call vs. 5× a 10-minute consensus pipeline).

---

## What We're Building

Six capabilities, delivered as one coherent change:

| # | Capability | What it does |
|---|-----------|-------------|
| **F1** | **Input queue** | Replace the single-slot `aget_input()` with an `asyncio.Queue`. Background completions, fork triggers, and scheduled ticks enter the same queue as user messages. The loop drains them FIFO. |
| **F2** | **Task simple mode** | `/task` defaults to a single leaf inferencer call (RovoDevCLI). The heavy PTI topology requires explicit `--full`. Workspace: streaming cache + logs + parsed output. |
| **F3** | **Background jobs** | `/background-job` tool spawns tools or shell commands in the background. `JobManager` tracks PID, workspace, schedule, status. Completions inject into the input queue. |
| **F4** | **YOLO mode** | `yolo_mode=True` on the inferencer auto-resolves confirmation/clarification gates — unless the SOP marks them `[__requires confirmation__; __must__]`. For headless subprocess execution. |
| **F5** | **SOP lifecycle** | `/enter-sop` loads an SOP into the current conversation. `/exit-sop` pauses it. `/sop` launches one in a subprocess (YOLO mode). `SOPRegistry` discovers available SOPs. |
| **F6** | **Prompt integration** | Template gains `## Available SOPs`, `## Active SOP`, `## Running Background Jobs`, and `## YOLO Mode` sections. All conditional on state presence. |

### How they compose

```
User: /background-job task "implement caching" --fork-on-completion

  1. /background-job parser → JobKind.TOOL, tool="task"
  2. JobManager.submit() → allocate workspace, spawn subprocess
  3. Subprocess runs task in simple mode (one RovoDevCLI call, ~60s)
  4. JobManager detects completion → pushes BackgroundJobComplete to input queue
  5. --fork-on-completion → ForkRouter creates new conversation with output as seed
  6. User sees new conversation tab with the caching implementation ready

User: /sop code_optimization --var workflow_target_path=src/api/

  1. /sop executor → JobKind.SOP
  2. Spawns: python -m agent_foundation.scripts.sop_runner code_optimization --yolo
  3. Subprocess runs code_optimization.md phases 0→3 unattended (YOLO)
  4. Phase 3b has [__requires confirmation__; __must__] → subprocess halts
  5. Completion with status=BLOCKED_ON_MUST_GATE injected into parent queue
  6. Parent agent tells user: "SOP paused at proposal review — needs your input"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              ConversationalInferencer (enhanced)                 │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  run_agentic_loop(content)                                 │  │
│  │    1. compress context if needed                           │  │
│  │    2. render prompt (SOPs, jobs, tools, conversation)      │  │
│  │    3. call LLM                                             │  │
│  │    4. parse response → tool calls                          │  │
│  │    5. execute tools (sync or async)                        │  │
│  │    6. if conversation tool:                                │  │
│  │       - YOLO + non-must gate? → auto-resolve               │  │
│  │       - else → await input_queue.get()                     │  │
│  │    7. drain input_queue (bg completions, forks, ticks)     │  │
│  │    8. inject drained items into dynamic context            │  │
│  │    9. loop                                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  New state:                                                     │
│    input_queue: ConversationalInputQueue                        │
│    yolo_mode: bool                                              │
│    sop_registry: SOPRegistry                                    │
│    sop_state: WorkflowSessionState                              │
│    _sop_tracker: StateGraphTracker | None                       │
│                                                                 │
└────────────┬────────────────────────┬───────────────────────────┘
             │                        │
    inject   │               spawn    │
             ▼                        ▼
┌────────────────────┐    ┌──────────────────────────┐
│    JobManager      │    │   Subprocess SOP Runner  │
│    (per-process)   │    │                          │
│                    │    │  ConversationalInferencer │
│  jobs: {id: Job}   │    │  (yolo_mode=True)        │
│  poll loop         │    │  + leaf inferencer       │
│  schedule engine   │    │  + loaded SOP            │
│  completion → queue│    │                          │
└────────────────────┘    └──────────────────────────┘
```

---

## Design Principles

1. **Background completions are CompletedActions, not messages.** Injecting `system`-role messages into `_messages` bypasses the existing compression pipeline. Instead, background completions enter `_dynamic_context` as `CompletedAction(tool="__background__", summary="...")`. This means the existing `_compress_context_if_needed()` handles them automatically — no new compression pathway needed.

2. **The queue adapter is session-scoped, not turn-scoped.** `run_agentic_loop` is called per-turn by the server. The adapter that pumps `interactive.aget_input()` into the queue must live at session level (started once in `ConversationService._get_or_create_inferencer`) to avoid racing on the same transport.

3. **YOLO uses the existing handler protocol.** Rather than a parallel code path, YOLO injects a `YoloInteractive` that auto-responds to conversation tools. The handler doesn't know it's in YOLO mode — it just gets a response from the interactive layer. This keeps the handler protocol clean and testable.

4. **SOP state is a formal state machine.** `WorkflowSessionState` tracks runs with explicit status transitions: `enter → running`, `exit → paused`, `resume → running`, `complete → completed`. Invalid transitions raise errors. At most one active run per inferencer.

5. **Simple mode is not a separate code path — it's a trivial topology.** Instead of branching in the executor, simple mode is a single-node YAML topology (`simple.yaml`) that instantiates one leaf inferencer. This reuses the entire existing config loading pipeline without special-casing.

6. **Process isolation for subprocess SOPs.** `/sop` always spawns a new process (not an asyncio task). A bad SOP can't crash the parent agent. The subprocess gets its own `ConversationalInferencer` instance with `yolo_mode=True` and a `NullInteractive`.

---

## Plan Structure

| # | File | Topic |
|---|------|-------|
| 0 | `README.md` (this file) | Overview, architecture, principles |
| 1 | `01_input_queue.md` | F1 — asyncio.Queue integration, drain step, adapter lifecycle |
| 2 | `02_task_simple_mode.md` | F2 — simple.yaml topology, workspace layout, leaf factory |
| 3 | `03_background_jobs.md` | F3 — JobManager, /background-job tool, scheduling, fork |
| 4 | `04_yolo_mode.md` | F4 — YOLO execution policy, must-gate honoring, auto-resolve |
| 5 | `05_sop_lifecycle.md` | F5 — SOPRegistry, /enter-sop, /exit-sop, /sop, subprocess runner |
| 6 | `06_prompt_integration.md` | F6 — Template sections, variable plumbing, decision procedure |
| 7 | `07_scenarios_and_verification.md` | End-to-end walkthroughs, error scenarios, test plan |
| 8 | `08_implementation_roadmap.md` | Dependency DAG, phased rollout, risks, definition of done |

---

## Glossary

| Term | Definition |
|------|-----------|
| **Leaf inferencer** | An inferencer that calls an LLM directly: `RovoDevCliInferencer`, `ClaudeCodeCliInferencer`, `ClaudeApiInferencer`. No orchestration. |
| **SOP** | Standard Operating Procedure — a Markdown/Jinja2 file defining a phased workflow with gates and tool requirements. Lives in `_variables/workflow_sop/`. |
| **YOLO mode** | `yolo_mode=True` on the inferencer. Auto-resolves non-`[__must__]` confirmation gates. For headless subprocess execution. |
| **Must-gate** | `[__requires confirmation__; __must__]` in an SOP. Cannot be auto-resolved even in YOLO. Forces human interaction or subprocess halt. |
| **Input queue** | `asyncio.Queue[QueueItem]` — the single FIFO source of events the agent reacts to: user messages, background completions, fork triggers. |
| **Job workspace** | Per-job directory under `<session_root>/_jobs/<job_id>/` with meta.json, stdout.log, stderr.log, and tool-specific artifacts. |
| **Fork** | Creating a new conversation session seeded with a background job's output. Triggered by `--fork-on-completion`. |
| **Simple mode** | `/task` default: one prompt through one leaf inferencer. No PTI, no dual consensus. |
