# Chapter 8 — Implementation Roadmap

> **Purpose:** Dependency DAG, phased rollout plan, risk register, and
> definition of done.

---

## 1. Dependency DAG

```
                ┌────────────────────────────────────┐
                │  F1: Input Queue (ch. 01)           │
                │  - QueueItem tagged union            │
                │  - ConversationalInputQueue          │
                │  - interactive → queue adapter       │
                │  - drain step in agentic loop        │
                └───────────────┬────────────────────┘
                                │ unlocks async event injection
          ┌─────────────────────┼────────────────────────┐
          │                     │                        │
          ▼                     ▼                        ▼
┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐
│ F2: Task Simple  │  │ F3: Background   │  │ F4: YOLO Mode     │
│ Mode (ch. 02)    │  │ Jobs (ch. 03)    │  │ (ch. 04)          │
│                  │  │                  │  │                   │
│ - simple.yaml    │  │ - JobManager     │  │ - YoloInteractive │
│ - leaf factory   │  │ - /background-job│  │ - must-gate detect│
│ - workspace      │  │ - runner, fork   │  │ - SOP parser ext  │
│ - _run_simple    │  │ - scheduler      │  │ - _evaluate_sop   │
└────────┬─────────┘  └────────┬─────────┘  └────────┬──────────┘
         │                     │                      │
         │   shared: leaf_factory.py                   │
         │                     │                      │
         └────────┬────────────┴──────────┬───────────┘
                  │                       │
                  ▼                       ▼
         ┌──────────────────────────────────────┐
         │  F5: SOP Lifecycle (ch. 05)           │
         │  - SOPRegistry                        │
         │  - WorkflowSessionState               │
         │  - /enter-sop, /exit-sop              │
         │  - /sop (subprocess runner)           │
         │  - sop_runner.py                      │
         │    (needs F3 for job tracking,        │
         │     F4 for YOLO mode,                 │
         │     F2 for leaf factory)              │
         └────────────────┬─────────────────────┘
                          │
                          ▼
         ┌──────────────────────────────────────┐
         │  F6: Prompt Integration (ch. 06)      │
         │  - ## Available SOPs                  │
         │  - ## Active SOP                      │
         │  - ## Running Background Jobs         │
         │  - ## YOLO Mode                       │
         │  - Decision Procedure update          │
         │    (needs all features for vars)      │
         └──────────────────────────────────────┘
```

**Critical path:** F1 (input queue) → F3 (background jobs) → F5 (SOP lifecycle) → F6 (prompt)

**Parallelizable:** F2 (task simple) and F4 (YOLO) have no mutual dependency and can be built in parallel with F3.

---

## 2. Phased Rollout

Each phase is one PR or a tightly-scoped PR series. All phases include
unit + integration tests per the respective chapter's test plan.

### Phase 0 — Test Infrastructure (~2 days)

**No behavior change. Unblocks all subsequent phases.**

- Mock leaf inferencer for subprocess tests (returns canned output, no LLM call)
- `QueueTestHarness`: wraps `ConversationalInputQueue` with helpers for asserting drain behavior
- `SessionStoreTestHelper`: creates/reads/writes test sessions with both legacy and new schemas
- `NullInteractive`: already exists, but verify it satisfies the `InteractiveBase` protocol for YOLO use

### Phase A — Input Queue (F1, ~1 week)

**PR A.1: Core queue types + drain step**
- Ship `input_queue.py` (QueueItem, ConversationalInputQueue)
- Add `user_input_queue` attribute to ConversationalInferencer
- Add drain step after tool execution in `run_agentic_loop()` (step 7 in README architecture)
- Background completions → `CompletedAction(tool="__background__")` in `_dynamic_context`
- Feature flag: `AGENT_INPUT_QUEUE_ENABLED` (default ON; OFF restores `aget_input` path)

**PR A.2: Adapter task**
- `_interactive_to_queue_adapter()` coroutine
- Session-level lifecycle: started in `ConversationService._get_or_create_inferencer()`, not per-turn
- Guard: `_adapter_started: bool` on inferencer prevents double-start
- Backward compat test: T1.7 (single-user-input flows produce byte-identical prompts)

### Phase B — Shared Utilities (~3 days)

**PR B.1: Leaf factory + workspace helpers**
- `agent_foundation/common/jobs/leaf_factory.py` — maps name to inferencer class
- `agent_foundation/common/jobs/workspace.py` — job workspace allocation, meta.json helpers
- Used by Phase C (task simple) AND Phase E (SOP subprocess)

### Phase C — Task Simple Mode (F2, ~1 week)

**PR C.1: Simple topology + executor changes**
- Add `simple.yaml` to `task/topologies/`
- Add `--simple` (default true), `--leaf-inferencer` to `tool.json`
- `_run_simple_mode()` in executor with try/finally error handling
- Simple prompt template (inline or `simple_initial.jinja2`)

**PR C.2: Migration**
- Phase C.2a: `TASK_DEFAULT_MODE_SIMPLE` flag OFF (no behavior change)
- Phase C.2b (next release): flag ON, deprecation warning for implicit `--full`
- Phase C.2c (following release): remove flag, simple is permanent default

### Phase D — Background Jobs Core (F3, ~1.5 weeks)

**PR D.1: Job models + manager scaffolding**
- `agent_foundation/common/jobs/models.py` (BackgroundJob, JobStatus, JobKind, JobSchedule)
- `agent_foundation/common/jobs/manager.py` (JobManager singleton, submit, cancel, list)
- `agent_foundation/common/jobs/runner.py` (spawn per kind, fd management)
- `agent_foundation/common/jobs/persistence.py` (atomic meta.json, rehydrate)
- No tool yet — JobManager API only

**PR D.2: /background-job tool + scheduling**
- `resources/tools/background_job/tool.json` + `executor.py`
- Parser: tool detection, flag parsing
- Wire `register_session`/`unregister_session` into ConversationService lifecycle
- Schedule engine: `_schedule_every`, `_schedule_at`
- `ForkRouter` abstract + server-side concrete (OpenStartup)
- Reject `--fork-on-completion` + `--every`

**PR D.3: /background-job-cancel**
- Minimal tool: send SIGTERM to process group, mark CANCELLED
- `resources/tools/background_job_cancel/tool.json` + `executor.py`

### Phase E — YOLO Mode (F4, ~1 week)

**PR E.1: YOLO foundation**
- `yolo_mode: bool` attribute on ConversationalInferencer
- `YoloInteractive` class implementing `InteractiveBase`
- Auto-resolution logic per tool type
- `_evaluate_sop()` refactor: extract from `_render_prompt`, store tracker on `self._sop_tracker`
- Must-gate detection: `_current_phase_has_must_gate()`
- SOP parser enhancement: `__must__` regex in `sop_manager.py`
- `yolo_decisions.jsonl` audit log

**PR E.2: YOLO prompt section**
- `## Execution Mode: YOLO (Headless)` conditional section in template
- LLM behavior contract text

### Phase F — SOP Lifecycle (F5, ~1.5 weeks)

**PR F.1: SOPRegistry + WorkflowSessionState**
- `agent_foundation/common/sop/registry.py` (discovery, SOPDefinition, caching)
- `agent_foundation/common/sop/state.py` (WorkflowSessionState, WorkflowRun, state machine)
- Session persistence schema migration: `_backfill_from_legacy()` in session_store.py
- Schema version field on session_state.json

**PR F.2: /enter-sop + /exit-sop tools**
- `resources/tools/enter_sop/tool.json` + `executor.py`
- `resources/tools/exit_sop/tool.json` + `executor.py`
- Resume-if-paused logic in `/enter-sop`
- `find_sop_file()` enhancement to consult registry

**PR F.3: /sop subprocess tool + sop_runner.py**
- `agent_foundation/scripts/sop_runner.py` entry point
- `resources/tools/sop/tool.json` + `executor.py`
- `JobKind.SOP` in runner.py
- PYTHONPATH propagation in `_clean_env()`
- E2E test: tiny 3-phase SOP with no must-gates completes in YOLO

### Phase G — Prompt Integration (F6, ~1 week)

**PR G.1: Template rewrite**
- New `initial.jinja2` with all four conditional sections
- Legacy fallback for Workflow Context when `active_sop` absent
- Template variable plumbing in `_render_prompt()`
- Snapshot tests for each section combination

**PR G.2: Decision Procedure + running jobs formatting**
- Updated Decision Procedure with SOP and background job awareness
- `_format_running_jobs()` with sensitive arg redaction
- Token budget cap: 10 jobs max in prompt
- Audit existing SOPs: add `## Description` paragraphs for registry extraction

### Phase H — Polish & Hardening (~1 week)

- Token-cost accounting field (no enforcement)
- Job pruning policy (auto-delete completed jobs older than 7 days)
- Telemetry events for job lifecycle
- Documentation:
  - `_dev/_docs/background_jobs.md` (user guide)
  - `_dev/_docs/sop_authoring.md` (how to write SOPs, migration guide)
  - `_dev/_docs/yolo_mode.md` (when/why/how)

---

## 3. Calendar Estimate

| Phase | Effort | Calendar (with review) |
|-------|--------|------------------------|
| 0 (Test infra) | 0.5 week | 0.5 week |
| A (Input queue) | 1 week | 1.5 weeks |
| B (Shared utils) | 0.5 week | 0.5 week |
| C (Task simple) | 1 week | 1.5 weeks |
| D (Background jobs) | 1.5 weeks | 2 weeks |
| E (YOLO mode) | 1 week | 1.5 weeks |
| F (SOP lifecycle) | 1.5 weeks | 2 weeks |
| G (Prompt integration) | 1 week | 1.5 weeks |
| H (Polish) | 1 week | 1.5 weeks |
| **Total** | **9 weeks** | **~12.5 weeks** (1 engineer) |

**With 2 engineers:** B+C can parallel with D; E can parallel with D.2+D.3; calendar reduces to ~7 weeks.

---

## 4. Risk Register

### High Priority

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Input queue breaks existing single-user flows | Med | High | Feature flag + T1.7 backward-compat test + staged rollout (internal first) |
| R2 | YOLO auto-yes on destructive confirmation | Low | High | `__must__` is the SOP author's gate for destructive ops. Audit log (`yolo_decisions.jsonl`) makes every auto-resolution reviewable. Document in SOP authoring guide. |
| R3 | Background job process leaks (orphans, fd leaks) | Med | Med | `start_new_session=True` for process group isolation. Context-managed file handles. `max_wallclock` default of 24h. Periodic orphan sweep in `_poll_loop`. |
| R4 | Task default-mode change breaks existing SOP callsites | Med | Med | 3-phase migration: OFF → ON+warning → permanent. Audit all SOPs for `/task` usage. |

### Medium Priority

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R5 | meta.json corruption on concurrent writes | Med | Med | Single-writer per job (only JobManager mutates). Atomic tempfile+rename. |
| R6 | Queue drain too aggressive — events missed during long tool calls | Low | Med | Drain happens between iterations (after tool result, before next render). Tool calls don't block drain. |
| R7 | Token budget blown by running-jobs entries | Low | Med | Cap at 10 jobs in prompt. "+N more" suffix. |
| R8 | SOP subprocess can't import `agent_foundation` in dev | Med | Med | Propagate `PYTHONPATH` explicitly in `_clean_env()`. |
| R9 | Fork explosion: `--fork-on-completion` + `--every` | High | Med | Parser rejects this combination with clear error message. |
| R10 | Sensitive args leak into LLM prompt via `cmdline_short` | Med | Med | Redact values for keys matching `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`. |

### Low Priority

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R11 | Schedule loop drift over long uptime | Low | Low | Use `monotonic()` clock. `every_seconds` is interval-from-previous-completion. |
| R12 | Two `/enter-sop` calls in same turn (LLM mistake) | Low | Low | Second one sees active run → returns error. LLM self-corrects. |
| R13 | SOP registry misses new files until restart | Low | Low | Rescan on SIGHUP or explicit API call. Acceptable for v1. |

---

## 5. Feature Flag Matrix

| Flag | Default | Effect when OFF |
|------|---------|----------------|
| `AGENT_INPUT_QUEUE_ENABLED` | ON | Restores direct `aget_input()` path. Background completions dropped. |
| `TASK_DEFAULT_MODE_SIMPLE` | OFF → ON → permanent | OFF: `/task` uses full topology. ON: `/task` defaults to simple. |
| `BG_JOB_MANAGER_ENABLED` | OFF → ON | OFF: `/background-job` returns "feature not available". JobManager not started. |

**Valid combinations:**
- All OFF: pre-change behavior exactly
- Queue ON + Jobs OFF: queue exists, nothing pushes to it besides user — safe
- Queue ON + Jobs ON + Task Simple OFF: background jobs work, but `/background-job task` uses full topology (slow but correct)
- All ON: full feature set

---

## 6. Migration Audit Checklist (per existing SOP)

For each SOP file in `_variables/workflow_sop/`:

- [ ] Has a top-of-file `## Description` paragraph (for SOPRegistry title/description extraction)
- [ ] All confirmation gates that MUST happen in YOLO are marked `[__requires confirmation__; __must__]`
- [ ] All variables referenced via `{{ var }}` are documented in a `<!-- sop-meta required_vars: ... -->` comment
- [ ] Any `/task <request>` callsite is reviewed: if PTI is genuinely needed, explicitly says `/task --full <request>`
- [ ] Validated end-to-end via `/sop <name>` in YOLO mode on a sandbox session

**Audit targets:**
- `code_optimization.md` — Phase 3b has `__must__` ✓; needs `## Description` block
- `model_optimization.jinja2` — needs `__must__` audit + `## Description`
- `role_creation.jinja2` — needs `__must__` audit + `## Description`

---

## 7. Decision Log

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|---------------------|
| DL1 | Background completions enter `_dynamic_context` as `CompletedAction`, not `_messages` | Reuses existing compression pipeline. Adding a `system` role to `_messages` would bypass compression and require template changes for `<system>` tags. | `system`-role messages — no compression, template changes needed |
| DL2 | Queue adapter is session-scoped, not per-turn | `run_agentic_loop` is called per-turn. Per-turn adapter would race on `interactive.aget_input()`. | Per-turn adapter — race condition |
| DL3 | Simple mode uses a `simple.yaml` topology, not a code branch | Reuses entire config loading pipeline (load, walk-replace-model, instantiate). No special-case code in executor. | Code branch in `execute()` — duplicates config loading logic |
| DL4 | `/sop` spawns subprocess, not asyncio task | Process isolation: bad SOP can't crash parent. Resource accounting via OS. Clean SIGKILL semantics. | In-process asyncio task — crash safety concerns |
| DL5 | YOLO via `YoloInteractive`, not handler-level branching | Handler protocol stays clean. YOLO is an interactive-layer concern, not a handler concern. Easier to test. | if-YOLO checks inside each handler — protocol pollution |
| DL6 | `__must__` is byte-additive SOP parser change | Existing `[__requires confirmation__]` without `__must__` parses identically. Zero backward-compat risk. | New marker syntax — breaking change |
| DL7 | `proc.returncode` for job completion, not `os.waitpid` | `os.waitpid` conflicts with asyncio's child watcher (may get `ChildProcessError`). `proc.returncode` is the asyncio-native API. | `os.waitpid(WNOHANG)` — platform-specific, asyncio conflict |
| DL8 | All template additions conditional on variable presence | Sessions without SOPs/jobs see zero extra tokens. No wasted prompt space. | Always-render with "(none)" — wastes tokens |
| DL9 | JobManager is per-process singleton, not per-session | Sessions share the poll loop. One schedule engine, not N. Lower overhead. | Per-session JobManager — multiplied poll loops |
| DL10 | `/enter-sop` auto-resumes paused run of same SOP | Users expect "enter X" to continue where they left off, not create a duplicate. | Always create new run — confusing UX |

---

## 8. Definition of Done

This plan is complete when, on a clean checkout at post-Phase-H:

1. **`/task "hello world"`** completes in <60s via RovoDevCLI simple mode. Workspace has: `meta.json`, `input_prompt.md`, `raw_response.txt`, `parsed_output.json`.

2. **`/background-job task "say hi" --fork-on-completion`** returns immediately. Within 90s, a new conversation session appears seeded with the task output.

3. **`/enter-sop code_optimization`** updates prompt to show `## Active SOP: code_optimization`. Agent invokes Phase 0 clarification.

4. **`/exit-sop`** removes Active SOP section. Re-entering with `/enter-sop code_optimization` recovers exact state.

5. **`/sop code_optimization --var workflow_target_path=tests/fixtures/tiny_repo`** launches subprocess, completes Phases 0–3 in YOLO, halts at Phase 3b must-gate, returns `BLOCKED_ON_MUST_GATE` completion.

6. **All test plans** (T1.*, T2.*, T3.*, T4.*, T5.*, T6.*) pass. Coverage on new code ≥ 80%.

7. **Backward compatibility:** A session created before any of these changes produces a byte-identical prompt after upgrading. T1.7 enforces this.

8. **Template snapshot test** (T6.10) passes across runs.

9. **SOP audit checklist** (§6) is green for all 3 existing SOPs.

10. **Documentation:** `background_jobs.md`, `sop_authoring.md`, `yolo_mode.md` exist in `_dev/_docs/`.
