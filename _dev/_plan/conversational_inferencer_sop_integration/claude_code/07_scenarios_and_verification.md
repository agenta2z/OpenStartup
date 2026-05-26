# Chapter 7 — End-to-End Scenarios & Verification

> **Purpose:** Prove the design holds together by walking through seven concrete
> user flows from chat input to final outcome. Includes error scenarios. Each
> scenario is a "definition of done" checkpoint.

---

## Scenario 1 — Simple Task (F2 alone)

**User:** `/task "rename _temp_var to scratch_buf in src/foo/bar.py"`

**Timeline:**

1. Slash dispatcher parses `/task`, constructs `arguments = {request: "rename ...", simple: true}` (default).
2. `executor.py::execute()` resolves mode → `"simple"` (no `--full`/`--plan`/`--confirm` flag).
3. `_run_simple_mode()`:
   - Allocates workspace: `<session_root>/_jobs/task-<uuid6>/`
   - Writes `input_prompt.md` (rendered from simple prompt template)
   - Constructs `RovoDevCliInferencer(model_id="claude-opus-4-7")`
   - Writes `inferencer_args.json` (leaf type, model, target_path)
   - Streams `inferencer.ainfer_streaming(prompt)` → accumulates `raw_response.txt`
   - Calls `inferencer.parse_output()` → writes `parsed_output.json`
   - Writes `meta.json` with `status: "completed"`, `duration_seconds: 47.2`
4. Returns `ToolExecutionResult(result=parsed_text, context_updates={workspace_path: ...})`
5. Conversational inferencer sees tool result, emits `<Response>` summarizing the change.

**Time:** ~30–90s (one RovoDevCLI call).  
**Processes:** 1 (parent) + 1 (`acli rovodev legacy`).  
**Token cost:** ~5–15k in + ~2–5k out.

**Workspace:**
```
_jobs/task-3f9c2a/
├── meta.json
├── inferencer_args.json
├── input_prompt.md
├── streaming_cache/
├── raw_response.txt
├── parsed_output.json
├── stdout.log
└── stderr.log
```

**Contrast:** Today (implicit `--full`): same outcome, 5–15 minutes, 4–8 subprocesses, 100k+ tokens.

---

## Scenario 2 — Background Task with Follow-Up (F1 + F2 + F3 + F6)

**User:** `/background-job task "implement caching for the recommendations service"`

**Timeline:**

1. `/background-job` parser: `task` matches tool registry → `JobKind.TOOL`.
   Resolved cmdline: `["task", "implement caching...", "--simple"]`.
2. `JobManager.submit()`:
   - Allocates `_jobs/bg-<uuid6>/`
   - Spawns subprocess via `asyncio.create_subprocess_exec`
   - Records PID, writes `meta.json` with `status: RUNNING`
3. Tool returns immediately: `"Background job bg-7f2c3a submitted. Workspace: _jobs/bg-7f2c3a/"`
4. Conversational inferencer's next render:
   - `## Running Background Jobs` shows: `bg-7f2c3a — tool: task implement caching... — RUNNING since 2m ago`
5. **5 minutes later** — subprocess finishes:
   - `JobManager._poll_loop()` detects `proc.returncode == 0`
   - Builds summary from stdout tail (last 20 lines)
   - Pushes `BackgroundJobComplete(job_id="bg-7f2c3a", status=DONE, summary="...")` into parent session's input queue
6. **On next iteration's drain step (or next user message):**
   - Drain step picks up `BackgroundJobComplete` from queue
   - Injects as `CompletedAction(tool="__background__", summary="Background job bg-7f2c3a completed. Summary: ...")` into `_dynamic_context`
   - Next render: `## Running Background Jobs` no longer lists bg-7f2c3a
   - LLM sees the completed action in context, responds: "The caching task completed. Summary: ..."

**User experience:** Send one message, get immediate ack, come back later and see completion announced.

---

## Scenario 3 — Scheduled Monitor (F1 + F3 + F6)

**User:** `/background-job /monitor --type pull_request --every 30m --label "PR watchdog"`

**Timeline:**

1. Parser: `monitor` matches tool registry → `JobKind.TOOL`. Schedule: `every: 1800s`.
2. `JobManager.submit()` creates job with `JobSchedule(mode="every", every_seconds=1800)`.
3. First run starts immediately. Spawns subprocess.
4. Prompt shows: `PR watchdog — tool: monitor --type pull_request — RUNNING since now`
5. After ~2 min, monitor completes. `BackgroundJobComplete` pushed.
6. Schedule engine sees `mode="every"` → spawns next run after 1800s.
7. Each completion injects a `CompletedAction` with monitor output.
8. Agent reacts naturally to each completion based on whatever SOP it's in.

**After 3 runs:** Three `CompletedAction` entries in dynamic context. Older ones get compressed by `_compress_context_if_needed()`.

---

## Scenario 4 — SOP Subprocess in YOLO Mode (F1 + F3 + F4 + F5)

**User:** `/sop code_optimization --var workflow_target_path=tests/fixtures/tiny_repo`

**Timeline:**

1. `/sop` executor creates BackgroundJob of `kind=SOP`.
2. Spawns: `python -m agent_foundation.scripts.sop_runner code_optimization --yolo --workspace _jobs/sop-<uuid6>/ --var workflow_target_path=tests/fixtures/tiny_repo`
3. Subprocess:
   - `sop_runner.py` creates `RovoDevCliInferencer` via leaf factory
   - Wraps in `ConversationalInferencer(yolo_mode=True, interactive=NullInteractive())`
   - Loads `code_optimization.md` SOP from SOPRegistry
   - **Phase 0 (Setup):** `[__initial__]` — auto-resolved. `workflow_target_path` pre-set via `--var`.
   - **Phase 1 (Investigation):** `[__requires confirmation__]` — YOLO auto-yes. Invokes `/understand-codebase`.
   - **Phase 1b (Review):** `[__requires confirmation__]` — YOLO auto-yes.
   - **Phase 2 (System Investigation):** `[__requires confirmation__]` — YOLO auto-yes. Invokes `/investigate-system`.
   - **Phase 2b (Review):** `[__requires confirmation__]` — YOLO auto-yes.
   - **Phase 3 (Research & Proposal):** Invokes `/research-propose`.
   - **Phase 3b (Review & Selection):** `[__requires confirmation__; __must__]` — **YOLO CANNOT AUTO-RESOLVE.**
     - `YoloInteractive.aget_input()` detects must-gate → raises `MustGateError`
     - Loop catches error, writes audit log entry to `yolo_decisions.jsonl`
     - Subprocess exits with code 2 (`BLOCKED_ON_MUST_GATE`)
4. `JobManager._poll_loop()` detects exit code 2:
   - Reads `yolo_decisions.jsonl` for blocking gate details
   - Pushes `BackgroundJobComplete(status=BLOCKED, summary="Blocked on Phase 3b must-gate: proposal review required")` into parent queue
5. Parent agent tells user: "SOP paused at proposal review — needs your input. See proposals at _jobs/sop-abc123/"

**Key verification:** Phases 0–3 complete autonomously. Phase 3b correctly blocks. No user interaction until the must-gate.

---

## Scenario 5 — Interactive SOP Enter/Exit/Resume (F5 + F6)

**User:** `/enter-sop code_optimization`

**Timeline:**

1. `/enter-sop` executor:
   - Checks SOPRegistry for `code_optimization` → found
   - Checks WorkflowSessionState for paused run with same name → none
   - Creates new `WorkflowRun(sop_name="code_optimization", status="running")`
   - Sets `active_run_id`
   - Returns `ToolExecutionResult(context_updates={active_sop_id: "code_optimization", ...})`
2. Next render:
   - `## Available SOPs` lists all SOPs (code_optimization now has "(active)" marker)
   - `## Active SOP: code_optimization` replaces `## Workflow Context`
   - Shows `<WorkflowDescription>`, `<WorkflowStatus>`, `<WorkflowNextStepGuidance>`
   - Agent invokes Phase 0 clarification (asks user for target path)

3. User works through Phases 0–2, then says: "I need to switch to something else."

4. **User:** `/exit-sop --reason "switching to urgent bug fix"`
   - Executor pauses run (preserves phase 2 state, all outputs)
   - Clears `active_run_id`
   - `## Active SOP` section disappears from prompt
   - Agent confirms: "Paused code_optimization at Phase 2. Re-enter anytime with `/enter-sop code_optimization`."

5. User does other work...

6. **User:** `/enter-sop code_optimization`
   - Executor finds paused run with same SOP name → **auto-resumes** (not duplicate)
   - Sets `active_run_id` to existing run
   - State restored: current_phase=2, all phase_outputs preserved
   - Agent picks up exactly where it left off: "Resuming code_optimization at Phase 2. Let me continue with system investigation..."

---

## Scenario 6 — Active SOP + Concurrent Background Job (F1 + F2 + F3 + F5 + F6)

**User is in `code_optimization` SOP at Phase 3 (Research & Proposal).**

**User:** `/background-job task "implement proposal #2 from the optimization report"`

**Timeline:**

1. Parser: `task` → `JobKind.TOOL`. Spawns in background with simple mode.
2. Tool returns immediately. Prompt now shows BOTH:
   - `## Active SOP: code_optimization` (Phase 3 status)
   - `## Running Background Jobs` (bg-xyz — task implement proposal #2...)
3. Agent acknowledges: "Started implementing proposal #2 in the background. Let's continue reviewing the other proposals."
4. User and agent continue Phase 3 review (discuss proposals #1, #3, #4).
5. **3 minutes later:** Background task completes.
   - `BackgroundJobComplete` injected into input queue
   - Next drain step adds `CompletedAction(tool="__background__", summary="proposal #2 implemented successfully")`
6. Agent (still in Phase 3): "By the way, proposal #2's implementation just finished in the background. The code is at _jobs/bg-xyz/. Shall we proceed to Phase 4 implementation for the remaining proposals?"

**Key verification:** SOP progress and background jobs coexist without interference. The agent manages both streams of work naturally.

---

## Scenario 7 — Background Job Failure and Recovery (F1 + F2 + F3)

**User:** `/background-job task "refactor the entire database layer to use SQLAlchemy"`

**Timeline:**

1. Job spawned, runs for 8 minutes.
2. Subprocess runs out of memory (OOM killed by OS → SIGKILL → exit code 137).
3. `JobManager._poll_loop()` detects `proc.returncode == 137` (non-zero):
   - Reads last 20 lines of stdout.log for context
   - Writes `meta.json` with `status: FAILED`, `exit_code: 137`
   - Pushes `BackgroundJobComplete(status=FAILED, summary="Process killed (exit 137, likely OOM). Last output: '...'")` into queue
4. Drain step injects as `CompletedAction(tool="__background__", summary="Background job bg-abc FAILED (exit 137). Output at _jobs/bg-abc/. Last output: ...")`
5. Agent responds: "The database refactoring task failed — it was killed by the OS (likely ran out of memory). The partial output is at _jobs/bg-abc/stdout.log. Would you like me to try again with a smaller scope, or review the partial output first?"

**Key verification:** Failures are first-class. The agent gets enough context to help the user recover.

---

## Verification Checklist

Each scenario maps to concrete test cases across chapters:

| Scenario | Features | Key Test Cases |
|----------|----------|----------------|
| 1. Simple task | F2 | T2.1 (mode resolution), T2.3 (workspace files), T2.5 (error handling) |
| 2. Background task | F1+F2+F3+F6 | T1.3 (drain step), T3.1 (submit), T3.5 (completion callback), T6.3 (running-jobs display) |
| 3. Scheduled monitor | F1+F3+F6 | T3.8 (schedule engine), T3.9 (max_runs), T1.4 (compression of repeated completions) |
| 4. SOP subprocess | F1+F3+F4+F5 | T4.3 (YOLO auto-resolve), T4.5 (must-gate block), T5.7 (sop_runner), T3.5 (completion routing) |
| 5. Interactive SOP | F5+F6 | T5.1 (enter), T5.3 (exit), T5.4 (resume-if-paused), T6.1 (available SOPs display) |
| 6. SOP + background | F1+F2+F3+F5+F6 | T1.3 (drain during active SOP), T6.2 (active SOP + running jobs coexist) |
| 7. Failure recovery | F1+F2+F3 | T3.6 (failure detection), T3.7 (non-zero exit handling), T1.3 (FAILED status in queue) |

---

## Integration Test Matrix

Beyond per-feature unit tests, the following integration tests validate cross-feature interactions:

| Test | Features | Validates |
|------|----------|-----------|
| `test_simple_task_e2e` | F2 | Task completes via leaf inferencer, workspace has all expected files |
| `test_background_task_completion_reaches_agent` | F1+F2+F3 | Background task → JobManager → queue → drain → CompletedAction visible in next prompt |
| `test_yolo_sop_runs_to_must_gate` | F4+F5 | Subprocess SOP auto-resolves non-must phases, halts at must-gate, exit code 2 |
| `test_enter_exit_resume_preserves_state` | F5 | Enter SOP, advance 2 phases, exit, re-enter → state intact |
| `test_concurrent_sop_and_background` | F1+F2+F3+F5+F6 | Active SOP + background job → both visible in prompt, completion handled correctly |
| `test_scheduled_job_respects_max_runs` | F3 | Job with `every_seconds=5, max_runs=3` fires exactly 3 times then stops |
| `test_fork_on_completion_creates_session` | F1+F3 | Background task with --fork-on-completion → ForkRouter called with correct context |
| `test_legacy_session_backward_compat` | F5+F6 | Session without any SOP features → prompt identical to pre-change template |
| `test_prompt_token_budget` | F6 | With 15 running jobs + 5 available SOPs + active SOP → prompt stays within token budget |
| `test_job_failure_and_agent_response` | F1+F2+F3 | OOM-killed job → FAILED in queue → agent has enough context to help user |
