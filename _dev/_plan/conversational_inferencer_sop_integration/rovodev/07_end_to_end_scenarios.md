# Chapter 7 — End-to-End Scenarios

> **Purpose:** Show how F1–F6 compose by walking through five concrete user
> flows from chat input to final outcome. Useful as the "definition of done"
> for QA and as a sanity-check that the design holds together.

---

## Scenario 1 — Simple Task (F1 alone)

**User:** `/task "rename _temp_var to scratch_buf in src/foo/bar.py"`

**Backend timeline:**

1. ConversationService receives the chat message.
2. Slash dispatcher matches `/task`, parses args against `task/tool.json`,
   constructs `arguments = {"request": "rename ...", "simple": True}` (default).
3. `task/executor.py::execute()` resolves mode → `"simple"`.
4. `_run_simple_mode()`:
   - Allocates `<runtime_root>/tasks/task/task_20260519_170712_a1b2c3d4/`
     via the shared `allocate_task_node_workspace(task_name="task",
     create_children_dir=False)` (reuses the existing convention; chapter 1 §3.4).
   - Renders `simple_initial.jinja2` → writes `artifacts/input_prompt.md`
   - Constructs `RovoDevCliInferencer(target_path=..., model_id="claude-opus-4-7",
     cache_folder="<ws>/_runtime/inferencer_cache/RovoDevCliInferencer",
     session_log_dir="<ws>/logs/session")`
   - Writes `artifacts/inferencer_args.json`
   - Streams `inf.ainfer_streaming(prompt)` chunks → accumulates into
     `outputs/raw_response.txt`. The inferencer ALSO writes its session log
     to `logs/session/RovoDevCliInferencer-<id>.jsonl(.parts)` and streaming
     cache to `_runtime/inferencer_cache/RovoDevCliInferencer/` — same as
     when it's a child of any topology.
   - Calls `inf.parse_output(raw_response)` → writes `outputs/parsed_output.json`
   - Writes `artifacts/meta.json` with status=`completed`
5. `ToolExecutionResult` returned to the conversational inferencer with the
   parsed response text as `output`.
6. Conversational inferencer's next iteration sees the tool result in
   `_dynamic_context` and emits a final `<Response>` summarizing the change.

**Time:** ~30–90 s (one Rovo Dev CLI call).  
**Process count:** 1 (parent server) + 1 (`acli rovodev legacy`).  
**Token cost:** ~5–15k input + ~2–5k output.

**Workspace artifacts** (same convention as today's heavy task runs, just
no `children/`):
```
<runtime_root>/tasks/task/task_20260519_170712_a1b2c3d4/
├── artifacts/
│   ├── meta.json                                    # {status: completed, duration_seconds: 47.2, ...}
│   ├── inferencer_args.json
│   └── input_prompt.md
├── checkpoints/                                     # empty (one-step run)
├── logs/
│   └── session/
│       └── RovoDevCliInferencer-3ce9a020.jsonl(.parts)   # session log (same format as topology-child runs)
├── _runtime/
│   └── inferencer_cache/
│       └── RovoDevCliInferencer/                    # raw acli output stream + cache
└── outputs/
    ├── raw_response.txt
    └── parsed_output.json                           # {"response": "Renamed _temp_var → scratch_buf in 3 sites; tests pass."}
# NO children/ — single-node task.
```

**Contrast with today (`--full`):** same outcome but ~5–15 minutes, 4–8 child
processes (proposer + reviewer + breakdown agents), 100k+ tokens.

---

## Scenario 2 — Background Task + Follow-Up (F1 + F2 + F3 + F6)

**User:** `/background-job task "implement caching for the recommendations service"`

**Backend timeline:**

1. `/background-job` parser sees `task` is a registered tool → `JobKind.TOOL`.
   Cmdline becomes `["task", "implement caching for ...", "--simple"]`
   (simple appended because no mode flag was supplied — F1 §3.6).
2. `JobManager.submit()`:
   - Allocates `_jobs/bg-7f2c3a/`
   - Spawns `python -m openteam.server.resources.tools.task.cli implement caching for ... --simple`
   - PID recorded; `meta.json` written; status=`RUNNING`
3. Tool returns immediately: `"Background job bg-7f2c3a submitted (tool). Workspace: ..."`
4. Conversational inferencer's next render:
   - `## Running Background Jobs` now shows `bg-7f2c3a — tool: task implement ...`
   - Agent may respond to user or wait for further input

5. **5 minutes later** — the background CLI finishes:
   - `JobManager._poll_loop` detects `waitpid` returns; exit=0
   - `build_summary` reads stdout tail → builds the system message text
   - `BackgroundJobComplete` pushed into the parent session's
     `user_input_queue` (via `register_session`)
6. **On the next user message OR on the next inferencer turn's drain step (F2 §3.4):**
   - The synthetic `[Background job completed]` system message appears in
     conversation history
   - The agent's prompt no longer lists `bg-7f2c3a` in Running Background
     Jobs (it's done)
   - The agent's `<Response>` references the new result: "The caching task
     completed successfully. Summary: …"

**User experience:** They sent one message, got an immediate ack, came back
later and saw the completion announced + acted-on. No blocking, no polling.

---

## Scenario 3 — Scheduled Monitor (F3 + F2 + F6)

**User:** `/background-job /monitor --type pull_request --every 30m --label "PR watchdog"`

**Backend timeline:**

1. Parser: `monitor` is a registered tool → `JobKind.TOOL`. Schedule:
   `every: 1800s`.
2. JobManager submits with `JobSchedule(mode="every", every_seconds=1800)`.
3. First run starts immediately; subsequent runs scheduled via
   `_schedule_every`.
4. Each run writes a fresh `_jobs/bg-9d1e/run-{n}/` subdirectory (the
   workspace path is suffixed `/run-1`, `/run-2`, ... so each invocation
   has clean isolated artifacts).
5. After each completion:
   - `BackgroundJobComplete` pushed to queue with summary
   - If any PR has new comments / failed pipeline → summary text triggers
     the agent to call `/task --simple "address PR comment X"` on next turn

**Cancellation:** User types `/background-job-cancel bg-9d1e`. JobManager
sends SIGTERM to current run; sets `schedule.max_runs = runs_completed`
so no future runs scheduled; status → CANCELLED.

---

## Scenario 4 — Autonomous SOP via `/sop` (F1+F3+F4+F5+F6)

**User:** `/sop code_optimization --var workflow_target_path=src/foo --fork-on-completion`

**Backend timeline:**

1. `/sop` executor finds `code_optimization` in registry, validates vars.
2. Submits as `JobKind.SOP` background job with cmdline
   `["sop", "code_optimization", "--var", "workflow_target_path=src/foo",
     "--inferencer", "rovodev_cli"]` and `fork_on_completion=True`.
3. JobManager.runner._spawn_sop_subprocess →
   `python -m agent_foundation.scripts.sop_runner code_optimization
     --var workflow_target_path=src/foo --inferencer rovodev_cli
     --workspace _jobs/bg-aa12/`
4. **Subprocess executes:**
   - Builds `RovoDevCliInferencer` as leaf
   - Builds `ConversationalInferencer(yolo_mode=True, sop_registry=...,
     prior_context={"active_sop_id": "code_optimization", "yolo_vars": {...}},
     interactive=NullInteractive())`
   - Seeds the loop with `"Begin SOP execution: code_optimization. Variables: ..."`
   - The agent's loop:
     - Renders prompt with `## Available SOPs`, `## Active SOP:
       code_optimization`, YOLO contract.
     - Reads `<WorkflowNextStepGuidance>` → Phase 0 (Setup) requires
       `clarification` for `workflow_target_path` → YOLO reads `yolo_vars`,
       auto-resolves → write completed action.
     - Phase 1 has `[__requires confirmation__]` (NOT `__must__`) → YOLO
       auto-yes → invokes `/understand-codebase src/foo`.
     - Phase 2 same (auto-yes) → `/investigate-system src/foo --docs ...`.
     - Phase 3 → `/research-propose ...` → produces unified plan.
     - **Phase 3b has `[__requires confirmation__; __must__]`** → YOLO
       cannot bypass. Agent emits `proposal_selection` tool. NullInteractive
       returns immediately with no input. Agent detects this via
       `_handle_conversation_tool`'s queue-empty timeout, logs
       `must_gate_unattended`, exits with status 1.
     - **OR (alternative path):** `must_gate_unattended` could be configured
       to **auto-select top-N** via YOLO's `_top_n_globally_ranked` and
       continue. This is configurable via SOP-level
       `<!-- sop-meta yolo_top_n_on_must: 5 -->` annotation (v2 feature).
       For v1, must-gate → halt.
5. **Subprocess exits.** JobManager sees `waitpid` → exit=1 → status=FAILED.
6. **fork_on_completion=True → ForkRouter fires:**
   - New session created with seed message:
     ```
     A background job you started has completed.
     job_id: bg-aa12
     cmdline: sop code_optimization --var workflow_target_path=src/foo ...
     status: failed
     workspace: <path>
     summary: [BLOCKED ON MUST-GATE] Phase 3b proposal_selection requires user input.
       Last yolo_decisions.jsonl entry: ...
       Top-ranked proposals (10): H1, H17, H3, ...
     ```
   - User sees a new conversation tab/branch where they can review the
     proposals and select interactively (the SOP's Phase 3b survives the
     fork: the user is now the parent, the run is in `failed` state but
     `phase_outputs.research_proposals_data` is intact).

**Outcome:** The user submitted ONE command, walked away, and came back
to a forked conversation pre-loaded with the autonomous run's output,
asking them to make the proposal selection that the autonomous run
couldn't.

---

## Scenario 5 — Interactive SOP Entry/Exit (F2+F5+F6)

**User:** "I want to optimize the hot loop in src/foo."

**Agent reasoning:**

- Read `## Available SOPs` → `code_optimization` matches.
- Read Decision Procedure → case (a)+(3): suggest `/enter-sop` directly.

**Agent response:**
```
This looks like a fit for our "code_optimization" SOP. Entering it now.

```json ToolsToInvoke
{"type":"action","name":"enter_sop","arguments":{"name":"code_optimization","var":["workflow_target_path=src/foo"],"reason":"user wants to optimize hot loop"}}
```
```

**Backend:** `enter_sop` executor mutates `prior_context["active_sop_id"]
= "code_optimization"`, creates `WorkflowRun(run_id="wf-3f9c2a")`.

**Next turn:**

- Prompt now has `## Active SOP: code_optimization` block with
  Phase 0 guidance.
- Agent renders Phase 0 `clarification` for `workflow_target_path`
  (already set via --var → optional; agent skips, advances to Phase 1).
- Phase 1 has `[__requires confirmation__]` → agent emits
  `confirmation` tool. User clicks Approve.
- Agent invokes `/understand-codebase src/foo`. Tool runs synchronously
  (in the foreground; it's not a `/background-job`).
- Phases 2 → 3 → 3b proceed similarly, with the `__must__` gate at 3b
  surfacing as the `proposal_selection` widget for the user to choose.

**Mid-flow:** User types `/exit-sop --reason "let me run a quick check
elsewhere"`.

- Executor calls `workflow_state.exit()`: run wf-3f9c2a status →
  `paused`; `active_sop_id` cleared.
- Next prompt: `## Active SOP` section gone; `## Available SOPs` still
  there.
- User runs `/task "check usage of foo() in tests/"` for 30 seconds.
- Then `/enter-sop code_optimization` to resume.
- `enter_sop` executor sees a paused run with same name → resumes it
  (status → `running`; restores `phase`, `phase_outputs`).
- Prompt now shows the SOP picking up where it left off (Phase 3b).

---

## Cross-Scenario Invariants

These hold across all five scenarios:

1. **`/task` always defaults to simple mode** (F1) — only `--full`/`--plan`/
   `--confirm` switch to heavy topology.
2. **`/background-job` returns immediately** (F3) — never blocks the agent.
3. **Completion is push-based** (F2) — the agent doesn't poll; the queue
   delivers `BackgroundJobComplete` items at well-defined points.
4. **YOLO is opt-in via subprocess `/sop`** (F4) — never on in the user's
   chat session unless explicitly enabled by the admin.
5. **`[__must__]` gates are absolute** (F4) — YOLO cannot bypass; subprocess
   halts; forked conversation surfaces the gate.
6. **SOPs are discoverable, named, versioned, resumable** (F5) — agent
   sees them in every prompt; user can enter/exit/resume freely.
7. **Running jobs are always visible in-prompt** (F6) — completed jobs
   move from the running list to a synthetic `[Background job completed]`
   chat message.
8. **Workspaces are session-rooted, structured, persistent** — every job
   lives at `<session_root>/_jobs/<id>/` with `meta.json` for rehydration.

---

## Anti-Scenarios (What This Plan Does NOT Solve)

| Anti-scenario | Why out of scope | Tracked where |
|--------------|------------------|---------------|
| Concurrent active SOPs in one session | Single-attention agent; design assumes at most 1 | chapter 5 §7 Q3 |
| Cross-session workflow hand-off | Sessions are isolated by design | predecessor plan §1.2 N2 |
| Multi-server / distributed JobManager | Single-process v1 | chapter 3 §7 Q1 |
| Auto-recovery from leaf inferencer auth blockers (e.g., MFA) | Out of band | chapter 1 §7 Q3 |
| UI for managing background jobs | Backend-only here | chapter 6 §6 |
| Token-cost accounting & budgets per job | Field present, no enforcement | chapter 3 §7 Q3 |

---

*Continued in `08_phased_rollout_and_risks.md`.*
