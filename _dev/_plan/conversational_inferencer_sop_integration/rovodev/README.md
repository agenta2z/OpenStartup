# Conversational Inferencer SOP Integration — Master Plan

> **Author:** Rovo Dev (with Tony Chen)
> **Date:** 2026-05-19
> **Status:** Proposal (Design + Phased Implementation)
> **Predecessor:** `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/_plan/workflow-as-first-class-citizen.md`
> **Related work:** `task-cli-unification-and-plan-only-mode.md`, `task_tool_enhancement/`
> **Codebases under change:**
>  - `/Users/tchen7/MyProjects/CoreProjects/AgentFoundation/src/agent_foundation/` (primary)
>  - `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/` (server integration only)

---

## 0. TL;DR — What We Are Building

Five tightly-coupled capabilities, delivered as **one coherent architecture
change** to the conversational inferencer:

| # | Capability | One-line description |
|---|------------|----------------------|
| **F1** | **Task simple-mode (default)** | `/task` runs as a thin one-shot prompt against a leaf inferencer (e.g. `RovoDevCliInferencer`) with workspace = streaming-cache + logs + parsed output. No PTI consensus, no nested topology. Engage the heavy path only with explicit `--full`/`--confirm`/`--plan`. |
| **F2** | **User input queue** | The conversational inferencer reads user input from an `asyncio.Queue` instead of a single blocking `aget_input()`. Items can arrive from the user, from a background-job completion callback, or from a fork-trigger. The loop picks them up one-by-one in FIFO order. |
| **F3** | **Background jobs (`BackgroundJob` + `JobManager`)** | A new `/background-job` tool spawns either a registered tool (any tool, defaulting to simple-mode for `task`) or a raw shell command in the background. Each job has a workspace, PID, schedule, repeat policy, status. Completion injects a templated message into the input queue (with optional `--fork-on-completion` to start a new conversation branch). |
| **F4** | **YOLO mode** | A `yolo_mode: bool` on `ConversationalInferencer` suppresses confirmation/clarification widgets and skips user-facing chatter — UNLESS the SOP marks a gate as `[__requires confirmation__; __must__]`, in which case the gate is always honored. Used for SOP execution in headless subprocesses. |
| **F5** | **SOP-as-first-class-citizen tools** | Three new tools: `/sop <name>` (launch standalone subprocess inferencer in YOLO mode), `/enter-sop <name>` (load SOP into current conversation), `/exit-sop` (unload SOP). The conversational inferencer prompt grows a `## Available SOPs` and `## Active SOP` block. Builds on the workflow-as-first-class-citizen design. |

Plus a **sixth supporting capability**:

| # | Capability | One-line description |
|---|------------|----------------------|
| **F6** | **Running-jobs prompt block** | The conversational inferencer template grows a `## Running Background Jobs` section listing live job IDs, status, ETA, output path. Completed jobs are removed from the block (their notification lives in the input queue instead). |

These six features compose. Examples:

- **YOLO subprocess SOP**: `/sop code_optimization --path src/foo/` → spawns a child
  `ConversationalInferencer(yolo_mode=True)` in a subprocess, loaded with the
  `code_optimization.md` SOP, target path pre-set; runs autonomously, posts
  status to a workspace dir, returns when complete.
- **Background task fan-out**: `/background-job task "implement feature X" --fork-on-completion`
  → spawns the task tool (simple mode by default), and on completion the
  input queue receives a `fork` item that creates a new conversation branch
  pre-loaded with the task output.
- **Scheduled monitor**: `/background-job /monitor --type pull_request --every 1h`
  → schedules repeated runs; each completion adds an item to the input queue
  (the LLM sees them on its next turn and reacts naturally via the SOP it's
  in).

---

## 1. Why Now — Forcing Functions

### 1.1 Task tool friction (forces F1)

The current `/task` always invokes the dual-agent consensus topology (proposer +
reviewer + breakdown/aggregate). This is heavyweight, multi-process, opaque,
and slow even for trivial one-shot prompts. The SOP `code_optimization.md`
already calls `/task <request>` per Phase 4 hypothesis — for typical 1–5
hypothesis runs, that's 5× the heavyweight pipeline when 5× a single Rovo Dev
CLI call would suffice.

**Today the task tool has no minimum-viable mode.** Add `--simple` (default ON
under the new contract) and reserve the heavy path for the cases that genuinely
need consensus.

### 1.2 Input queue (forces F2)

Today `ConversationalInferencer._handle_conversation_tool()` calls
`interactive.aget_input()` directly — a single-slot await. There is no way for
a *second* source (background job, scheduled job, fork trigger) to inject
input. The agentic loop can only ever react to *one* fresh user message per
turn. This blocks F3 and F5 entirely.

### 1.3 Background jobs (forces F3)

No `BackgroundJob` / `JobManager` abstraction exists anywhere in
AgentFoundation today. `subprocess.Popen` / `asyncio.create_task` are used
ad-hoc in ~30 inferencer files but there's no unified job lifecycle (PID
tracking, workspace allocation, completion callback, schedule, repeat).
Long-running tasks today block the conversation; the agent cannot multi-task.

### 1.4 YOLO mode (forces F4)

The SOP `code_optimization.md` is full of `[__requires confirmation__]` gates.
A subprocess SOP runner (`/sop` tool) must NOT prompt — there is no user
attached. But the SOP author still wants a way to mark certain gates as
non-skippable (e.g., production-impacting changes). The `[__must__]` marker
already exists in the SOP DSL; YOLO mode must honor it.

### 1.5 SOP first-class tools (forces F5 + F6)

The predecessor plan `workflow-as-first-class-citizen.md` already designs
`enter_workflow` / `exit_workflow` / `resume_workflow` action tools. **This
plan implements them** for the AgentFoundation `ConversationalInferencer`
(predecessor was scoped to `OpenTeam/openteam`), under the names `/enter-sop`,
`/exit-sop`, `/sop` (latter = launch standalone subprocess). Naming aligned
with user request.

---

## 2. Plan Structure

This plan is split into **eight numbered chapter files** for reviewability:

| # | File | Topic |
|---|------|-------|
| 0 | `README.md` (this file) | TL;DR, motivation, plan map, glossary |
| 1 | `01_task_simple_mode.md` | F1 — `/task --simple` (default) with leaf inferencer |
| 2 | `02_input_queue.md` | F2 — `asyncio.Queue` integration in conversational inferencer |
| 3 | `03_background_jobs.md` | F3 — `BackgroundJob`, `JobManager`, `/background-job` tool |
| 4 | `04_yolo_mode.md` | F4 — YOLO mode + `[__must__]` gate honoring |
| 5 | `05_sop_tools.md` | F5 — `/sop`, `/enter-sop`, `/exit-sop` tools |
| 6 | `06_prompt_template_changes.md` | F6 — `## Available SOPs`, `## Active SOP`, `## Running Background Jobs` sections |
| 7 | `07_end_to_end_scenarios.md` | Concrete user-flow walkthroughs |
| 8 | `08_phased_rollout_and_risks.md` | Implementation order, migration, risk register |

Read in order. Each chapter is self-contained but later chapters assume
earlier ones.

---

## 3. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  ConversationalInferencer (enhanced)                    │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  run_agentic_loop(content)                                       │   │
│   │   while True:                                                    │   │
│   │     1. compress context                                          │   │
│   │     2. render prompt:                                            │   │
│   │        - Available SOPs (always)                                 │   │
│   │        - Active SOP block (if any)                               │   │
│   │        - Running Background Jobs (if any)                        │   │
│   │        - Available Tools                                         │   │
│   │        - Conversation                                            │   │
│   │     3. call LLM → ConversationResponse                           │   │
│   │     4. dispatch tools (incl. /sop, /enter-sop, /exit-sop,        │   │
│   │        /background-job)                                          │   │
│   │     5. handle conversation tools                                 │   │
│   │        - if YOLO + gate NOT [__must__] → auto-resolve            │   │
│   │        - else → await user_input_queue.get()                     │   │
│   │     6. drain user_input_queue (background completions, forks)    │   │
│   │     7. add results to dynamic context                            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   State:                                                                │
│     - yolo_mode: bool                                                   │
│     - user_input_queue: asyncio.Queue[QueueItem]                        │
│     - active_sop_id: str | None                                         │
│     - sop_registry: SOPRegistry                                         │
│     - job_manager: JobManager (handle to shared instance)               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
            │                          ▲                          │
            │ inject QueueItem         │ status update            │ spawn
            ▼                          │                          ▼
┌─────────────────────────┐  ┌─────────────────┐  ┌────────────────────────┐
│  JobManager (singleton  │  │   SOPRegistry   │  │  Subprocess SOP runner │
│  per session/process)   │  │                 │  │  /sop tool             │
│                         │  │ - definitions   │  │                        │
│  - jobs: dict[id,Job]   │  │ - per-template  │  │  spawns                │
│  - schedule loop        │  │   YAML metadata │  │   python -m            │
│  - completion callback  │  │ - find_sop()    │  │   agent_foundation     │
│  - workspace allocator  │  │                 │  │   .conversational      │
└─────────────────────────┘  └─────────────────┘  │   --sop NAME           │
            │                                     │   --yolo               │
            │                                     │   --workspace DIR      │
            │                                     └────────────────────────┘
            │ launches
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BackgroundJob (one per /background-job invocation)                     │
│                                                                         │
│  - id: str (uuid4 short)                                                │
│  - kind: "tool" | "command" | "sop" | "subprocess_conv"                 │
│  - cmdline: list[str]                                                   │
│  - pid: int | None                                                      │
│  - workspace: Path                                                      │
│  - stdout_log: Path                                                     │
│  - stderr_log: Path                                                     │
│  - status: PENDING|RUNNING|DONE|FAILED|CANCELLED                        │
│  - schedule: "once" | {"every": "1h"} | {"at": ISO8601}                 │
│  - fork_on_completion: bool                                             │
│  - on_complete: callback that pushes QueueItem to parent inferencer     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Glossary

| Term | Meaning |
|------|---------|
| **Leaf inferencer** | An inferencer that calls an LLM directly without orchestrating other inferencers. `RovoDevCliInferencer`, `ClaudeCodeCliInferencer`, `ClaudeApiInferencer`. Used in F1 task simple-mode. |
| **SOP** | Standard Operating Procedure — a structured Markdown/Jinja2 file (e.g. `code_optimization.md`) describing a multi-phase workflow with confirmation gates. Lives under `prompt_templates/conversation/main/_variables/workflow_sop/`. |
| **Active SOP** | The SOP currently driving the agent's `<WorkflowNextStepGuidance>` rendering. At most one per inferencer instance. |
| **SOP slot** | The directory `_variables/workflow_sop/` where SOP definitions live. One file per SOP. |
| **YOLO mode** | `yolo_mode=True` on the inferencer. Suppresses confirmation/clarification gates that are NOT marked `[__must__]`. |
| **`[__must__]` gate** | An SOP gate marker (e.g. `[__requires confirmation__; __must__]`) that survives YOLO mode and forces user (or fork-parent) interaction. |
| **Input queue** | `asyncio.Queue[QueueItem]` owned by the inferencer; FIFO source of "things the agent needs to react to". Replaces direct `aget_input()` for the main loop. |
| **QueueItem** | Tagged-union: `UserMessage`, `BackgroundJobComplete`, `ForkTrigger`, `ScheduledTick`. |
| **Task workspace** (chapter 1) | Per-task-run filesystem directory under `<runtime_root>/tasks/<task_name>/<task_name>_<ts>_<8hex>/`, with the standard 5-folder node layout (`artifacts/`, `checkpoints/`, `logs/session/`, `_runtime/inferencer_cache/`, `outputs/`). This is where the leaf inferencer's session log + streaming cache + outputs live. Simple mode (F1) creates this with no `children/`; heavy mode creates this WITH `children/`. Same convention either way. |
| **JobManager bookkeeping workspace** (chapter 3) | Per-background-job directory under `<runtime_root>/_jobs/bg-<id>/`. Holds the SUBPROCESS-level `stdout.log`, `stderr.log`, `meta.json`, schedule state. **Distinct from the inner task workspace** — when `/background-job task ...` runs, the inner `/task` creates its own task workspace under `tasks/task/task_<ts>_<8hex>/`. |
| **Fork** | Creating a NEW conversation session pre-loaded with a parent context snapshot + a completion event. The fork has its own input queue and inferencer instance. |
| **JobManager** | Process-wide singleton (per agent server) that tracks all `BackgroundJob` instances, drives the schedule loop, and routes completions to the correct parent inferencer. |
| **Simple mode (task)** | `/task --simple` → run the request as ONE prompt against a single leaf inferencer; workspace contains only streaming-cache + inferencer-args log + raw response + parsed output. No PTI, no consensus. |

---

## 5. Cross-Cutting Concerns

These apply to ALL eight chapters:

| Concern | Decision |
|---------|----------|
| **Backward compatibility** | All new features OPT-IN by default for existing code paths. Old `/task` invocations without `--simple` still trigger PTI ONLY IF the user passes `--full`/`--confirm`/`--plan`. **NEW default is `--simple`** — this IS a behavior change documented in §1.1 of chapter 1, gated behind a feature flag for one release cycle. |
| **Persistence** | Background-job lifecycle state lives in `<runtime_root>/_jobs/bg-<id>/meta.json` (atomic write via tempfile+rename). Survives server restart. JobManager rehydrates on startup. Inner-tool (task/SOP) workspaces persist on their own under `<runtime_root>/tasks/...` (chapter 1) or whatever convention chapter 5 establishes — independent of JobManager state. |
| **Process boundary** | JobManager is **per-process**, not per-session. One JobManager instance per agent server / CLI invocation. Session ID is carried as `Job.session_id` for routing completions back to the correct queue. |
| **Telemetry** | Every job gets a structured event log: `JOB_SUBMITTED`, `JOB_STARTED`, `JOB_OUTPUT_LINE`, `JOB_COMPLETED`, `JOB_FAILED`, `JOB_INJECTED`. Same logging pattern as existing `CompletedAction` records. |
| **Auth / secrets** | Subprocess SOP runners inherit env from parent (`os.environ.copy()` minus secrets explicitly nominated to strip). Documented in §3 of chapter 5. |
| **Testing** | Each chapter ends with a "Test Plan" section enumerating concrete pytest cases (unit + integration + end-to-end smoke). |
| **Migration path** | All YAML/Jinja2 changes are ADDITIVE (new sections, new variables). No existing template variable is repurposed. New tool files in `resources/tools/<tool>/` are independent. |

---

## 6. Reading Order for Reviewers

If you have **15 min**: read this README + chapter 7 (`07_end_to_end_scenarios.md`).

If you have **45 min**: also read chapters 1 (F1) and 2 (F2) — they unlock everything else.

If you have **2 hr** (full review): read in order 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.

If you are the **implementer**: read chapter 8 first for the dependency DAG, then chapters in implementation order from chapter 8's §2.

---

*Continued in `01_task_simple_mode.md`.*
