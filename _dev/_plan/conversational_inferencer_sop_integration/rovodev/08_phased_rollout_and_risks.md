# Chapter 8 — Phased Rollout & Risk Register

> **Purpose:** Implementation order, dependency DAG, migration steps,
> risks + mitigations, and decision log.

---

## 1. Dependency DAG

```
                ┌─────────────────────────────────┐
                │  F2: Input Queue (chapter 2)    │
                │  - asyncio.Queue wrapper        │
                │  - QueueItem tagged union       │
                │  - interactive → queue adapter  │
                └────────────┬────────────────────┘
                             │ (unlocks all async event sources)
       ┌─────────────────────┼─────────────────────┬───────────────────┐
       ▼                     ▼                     ▼                   ▼
┌──────────────┐    ┌─────────────────┐  ┌──────────────────┐ ┌────────────────┐
│ F1: Task     │    │ F4: YOLO mode   │  │ F3: Bg Jobs +    │ │ F5: SOP tools  │
│ Simple Mode  │    │ (chapter 4)     │  │ JobManager       │ │ /enter, /exit, │
│ (chapter 1)  │    │  - yolo flag    │  │ (chapter 3)      │ │ /sop           │
│              │    │  - must-gates   │  │  - models        │ │ (chapter 5)    │
│              │    │  - auto-resolve │  │  - manager       │ │  - registry    │
│              │    │  - SOP parser   │  │  - runner        │ │  - state       │
│              │    │   __must__      │  │  - persistence   │ │  - sop_runner  │
│              │    │                 │  │  - fork router   │ │   subprocess   │
└─────┬────────┘    └────────┬────────┘  └────────┬─────────┘ └────────┬───────┘
      │                      │                    │                     │
      │ (leaf factory shared)│                    │ (runner uses        │
      │                      │                    │  leaf factory       │
      │                      │                    │  + yolo for sop kind)
      └──────┬───────────────┴─────────┬──────────┴──────────┬──────────┘
             │                         │                      │
             ▼                         ▼                      ▼
         ┌────────────────────────────────────────────────────────┐
         │  F6: Prompt template changes (chapter 6)               │
         │  - ## Available SOPs                                   │
         │  - ## Active SOP                                       │
         │  - ## Running Background Jobs                          │
         │  - ## Execution Mode: YOLO                             │
         └────────────────────────────────────────────────────────┘
```

**Critical path:** F2 must ship first; everything else depends on it for
async-event delivery into the agent loop.

---

## 2. Phased Rollout Plan

Each phase is one PR (or one tightly-scoped PR series). All phases include
unit + integration tests per the respective chapter's Test Plan.

### Phase A — Foundation (3 PRs, ~1 week each)

**Phase A.1 — Input Queue (chapter 2, F2)**
- Ship `input_queue.py`
- Refactor `conversational_inferencer._handle_conversation_tool` to read
  via queue
- Add adapter task
- Add drain step
- Feature flag: `AGENT_USER_INPUT_QUEUE_ENABLED` (default ON; OFF restores
  the direct `aget_input` path for emergency rollback)
- **Backward compat:** existing single-input flows must be byte-identical
  in their LLM-visible behavior. Test T2.7 enforces this.

**Phase A.2 — Job Manager scaffolding (chapter 3 §3.1–3.4, F3 partial)**
- Ship `common/jobs/` package skeleton
- Models + manager + runner (COMMAND and TOOL kinds; SOP kind deferred to Phase B)
- Persistence + rehydration
- No `/background-job` tool yet (next phase) — JobManager API only
- Feature flag: `BG_JOB_MANAGER_ENABLED` (default OFF; turn on per session
  via env var)

**Phase A.3 — Leaf factory + workspace helpers (shared utility)**
- Ship `common/jobs/leaf_factory.py` and `common/jobs/workspace.py`
- Used by Phase B (task simple mode) AND Phase D (SOP subprocess runner)

### Phase B — Task Simple Mode (1 PR, ~1 week, F1)

- Ship `_run_simple_mode` + `simple_initial.jinja2`
- Add `--simple` + `--leaf-inferencer` to `task/tool.json` (default `--simple=true`,
  `--full=false` BEHIND a feature flag `TASK_DEFAULT_MODE_SIMPLE`)
- Phase B.1: flag default OFF (no behavior change)
- Phase B.2 (one release later): flag default ON, deprecation warning
  whenever heavy path is implicit
- Phase B.3 (two releases later): remove flag, simple is permanent default

**Backward compat:** Existing `/task "foo"` callers get either:
- (Phase B.1) no change
- (Phase B.2) warning + same behavior
- (Phase B.3) NEW behavior (simple mode); must add `--full` to restore old

### Phase C — Background Job Tool (1 PR, ~3 days, F3 user-facing)

- Ship `/background-job` tool (executor + tool.json + parser)
- Wire `JobManager.register_session` into conversational inferencer
  startup/shutdown
- Add `--every`, `--at`, `--fork-on-completion` flags
- ForkRouter abstract; concrete `ForkRouter` registered by server bootstrap
  (no-op stub for AgentFoundation standalone)

### Phase D — YOLO Mode + SOP Subprocess (2 PRs, ~1 week, F4 + F5 partial)

**Phase D.1 — YOLO mode (chapter 4)**
- Ship `yolo_mode` attrib + `_yolo_auto_resolve` + `_gate_requires_user`
- Update SOP parser (`sop_manager.py`) to recognize `__must__` after
  `__requires confirmation__`
- Add YOLO prompt section
- Test against `code_optimization.md` end-to-end (without subprocess)

**Phase D.2 — `/sop` subprocess (chapter 5 §2.5, §2.6)**
- Ship `agent_foundation/scripts/sop_runner.py`
- Add `JobKind.SOP` to runner.py
- Ship `/sop` tool
- E2E test: spawn a tiny SOP (3 phases, no must-gates), verify completion
  routes through JobManager

### Phase E — SOP Registry + Enter/Exit (1 PR, ~1 week, F5 main)

- Ship `common/sop/registry.py` + `state.py`
- Ship `/enter-sop` + `/exit-sop` tools
- Wire `find_sop_file()` to consult registry first, fall back to legacy
- Backward-compat fallback: if no SOP named `default` exists, keep using
  `_variables/workflow/sop.*` for sessions that don't set `active_sop_id`

### Phase F — Prompt Template (1 PR, ~3 days, F6)

- Ship new `initial.jinja2`
- Ship template-var plumbing in `_render_prompt`
- Snapshot tests for each conditional section
- Audit existing SOPs for missing `## Description` paragraphs; add them

### Phase G — Polish & Production Hardening (1 PR, ~1 week)

- Cancellation tool `/background-job-cancel`
- Token-cost accounting field (no enforcement yet)
- Job pruning policy (auto-delete `_jobs/<id>/` older than N days for
  completed jobs)
- Telemetry: emit JOB_* events to the existing telemetry pipeline
- Documentation: user-facing guides for `/task`, `/background-job`, `/sop`

---

## 3. Total Calendar Time

| Phase | Effort (engineer-weeks) | Calendar (with review) |
|-------|------------------------|-------------------------|
| A.1 (Input Queue) | 1 | 1.5 |
| A.2 (JobManager scaffolding) | 1 | 1.5 |
| A.3 (Shared utils) | 0.5 | 0.5 |
| B (Task simple) | 1 | 1.5 |
| C (`/background-job`) | 0.5 | 1 |
| D.1 (YOLO) | 1 | 1.5 |
| D.2 (`/sop` subprocess) | 1 | 1 |
| E (SOP registry + enter/exit) | 1 | 1.5 |
| F (Prompt template) | 0.5 | 1 |
| G (Polish) | 1 | 1.5 |
| **Total** | **8.5 human engineer-weeks** | **~13 calendar weeks** (single engineer) |

With **2 engineers in parallel** (A → split B+C from D+E from F), calendar
reduces to ~7 weeks.

---

## 4. Risk Register

### 4.1 High-priority risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Backward-compat regression: existing single-user-input flows break after Phase A.1 (input queue) | Med | High | Feature flag; Test T2.7 (byte-identical legacy flow); staged rollout starting with internal sessions. |
| R2 | `/task` default behavior change (Phase B.2) silently breaks SOPs that assumed heavyweight path | Med | Med | One-release deprecation warning; audit all SOPs for `/task` usage; add `--full` explicitly in any SOP that legitimately needs PTI. |
| R3 | YOLO auto-yes on a destructive confirmation (e.g. "delete this branch?") | Low | High | `__must__` is the SOP author's tool to gate destructive ops; document in SOP authoring guide; add audit log review step in code review for new SOPs. |
| R4 | Background job process leaks (orphans not reaped, fd leaks) | Med | Med | `start_new_session=True` so we can SIGKILL pgroups; periodic orphan-sweep; finite `max_wallclock` default of 24h. |
| R5 | meta.json corruption on concurrent writes (poll loop + completion + cancel) | Med | Med | Single-writer per job (only JobManager mutates); atomic tempfile+rename; test T3.12. |
| R6 | SOP registry rescan stale on filesystem changes | Low | Low | Rescan on SIGHUP or process restart; documented in admin guide. |

### 4.2 Medium-priority risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R7 | Input queue drained too aggressively → `BackgroundJobComplete` items missed across long-running tool calls | Low | Med | Drain happens at start of EVERY iteration; tool calls don't block drain (drain is between iterations, after tool result). |
| R8 | Token budget blown by many running-jobs entries | Low | Med | Cap running-jobs prompt section at top-10 by recency; "... +N more" suffix. |
| R9 | SOP files use markers not yet supported (`__optional__`, custom variants) | Med | Low | Parser logs warnings, ignores unknown markers; never crashes. |
| R10 | `/sop` subprocess inherits secrets via env | Med | Med | `_clean_env()` strips known-sensitive vars (`*_TOKEN`, `*_SECRET`, `*_KEY`) by default; admin can override. |
| R11 | Fork explosion: `--fork-on-completion` on `--every` creates a new session per run | High | Med | Detect this combination in parser → reject with clear error; document. |
| R12 | RovoDevCliInferencer's `acli` binary not installed on subprocess machine | Med | Med | `/sop` tool validates `make_leaf_inferencer` succeeds before submitting; surfaces error early. |

### 4.3 Low-priority risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R13 | Schedule loop drift over long uptime | Low | Low | Use `monotonic()` clock; `every_seconds` is interval-from-previous-completion, not wall-clock. |
| R14 | Two `/enter-sop` calls in same turn (LLM mistake) | Low | Low | Second one returns WorkflowConflictError; LLM should self-correct on next turn. |
| R15 | User's chat scrolls past completion announcement | Low | Low | Out of scope for backend; UI handles toast/highlight. |

---

## 5. Migration Audit Checklist (per SOP)

For each existing SOP file in `_variables/workflow_sop/`:

- [ ] Has a top-of-file one-paragraph description (for `SOPRegistry._extract_title_desc`)
- [ ] All confirmation gates that MUST happen even in YOLO are marked
      `[__requires confirmation__; __must__]`
- [ ] All variables referenced via `{{ var }}` are declared in a
      `<!-- sop-meta required_vars: ... -->` HTML comment (or accept that
      registry auto-extraction is approximate)
- [ ] Any `/task <request>` callsite is reviewed; if PTI is genuinely
      desired, explicitly says `/task --full <request>` (Phase B.2 onward)
- [ ] Validated end-to-end via `/sop <name>` in YOLO mode on a sandbox
      session (Phase D)

Initial audit list:
- `code_optimization.md` — has `__must__` in Phase 3b ✓; needs description block.
- `model_optimization.jinja2` — TBD.
- `role_creation.jinja2` — TBD.

---

## 6. Deferred / Future Work

These were considered and explicitly DEFERRED out of v1:

| # | Feature | Why deferred |
|---|---------|--------------|
| D1 | Distributed JobManager (Redis / message broker) | Single-process is sufficient for current scale. |
| D2 | Resume `/sop` subprocess after parent server restart with same PID | Complex; current model is "subprocess re-runs from scratch using `phase_outputs` snapshot". |
| D3 | Per-team SOP scoping in registry | No clear demand yet. |
| D4 | Token-cost enforcement (budget caps) | Field exists; enforcement needs cost-source plumbing. |
| D5 | Inter-process must-gate forwarding (subprocess SOP → parent agent) | Designed (chapter 4 §3.8 case 2) but not in v1; complex IPC. v1 halts; user re-enters in fork. |
| D6 | UI changes (running-jobs panel, SOP breadcrumb, YOLO banner) | Backend-only here; UI tracked in `review_proposal_implementation/` follow-up. |
| D7 | SOP versioning (multiple versions of `code_optimization`) | Registry would need `name@version`; not yet needed. |
| D8 | Nested SOPs (`/sop` calls inside an SOP) | Should "just work" via process tree, but explicit recursive design + token-cost tracking deferred. |
| D9 | `/background-job-cancel` UI integration | Backend tool ships in Phase G; UI later. |
| D10 | Cross-platform `start_new_session`/process-group semantics on Windows | macOS/Linux v1; Windows in a follow-up. |

---

## 7. Decision Log

| # | Decision | Rationale | Alternative considered |
|---|----------|-----------|------------------------|
| DL1 | Single `asyncio.Queue` for all input sources (vs. per-source queues) | Simpler dispatch; FIFO is desirable globally. | Per-source queues + select() loop — rejected as overengineered. |
| DL2 | `BackgroundJob` lives in `common/jobs/` (vs. `server/jobs/`) | `JobManager` is process-singleton, usable in CLI too. | Server-only — rejected because `/sop` subprocess uses it too. |
| DL3 | `/sop` always uses subprocess (vs. async task within parent process) | Process isolation for resource accounting + crash safety. | In-process — rejected; one bad SOP could break the parent agent. |
| DL4 | YOLO is a per-inferencer-instance flag (vs. per-session config) | Same session can have foreground (interactive) AND background (YOLO) inferencers. | Session-wide — rejected. |
| DL5 | `__must__` parser change is byte-additive (existing `__must__`-less gates still parsed as before) | Zero backward-compat risk for existing SOPs. | Hard breaking change — rejected. |
| DL6 | `/task --simple` becomes the eventual default after a deprecation window | Existing users get a release to adjust. | Hard flip on day one — rejected. |
| DL7 | Prompt template additions are conditional on var presence | Sessions without SOPs / jobs see no clutter. | Always render with "(none)" — rejected; wastes tokens. |
| DL8 | `BackgroundJobComplete` injected as `system` role message (not `assistant` or `user`) | Marks unambiguously as non-human, non-LLM event. | `[System]` prefix on user message — rejected; muddies role boundaries. |
| DL9 | ForkRouter is an abstract handle (concrete in server bootstrap) | AgentFoundation can use the framework without forcing OpenTeam session model. | Concrete fork impl in AgentFoundation — rejected; coupling. |
| DL10 | One `JobManager` singleton per process (not per session) | Sessions share the schedule loop; reduces overhead. | Per-session JobManager — rejected; would multiply poll loops. |

---

## 8. Definition of Done

This plan is "done" when, on a clean checkout of AgentFoundation +
OpenStartup at the post-Phase-G commit:

1. `/task "hello world"` → completes in <60s via Rovo Dev CLI; workspace
   has expected files.
2. `/background-job task "say hi" --fork-on-completion` → returns
   immediately; in 30s, a new conversation tab appears with the task
   output as the seed message.
3. `/enter-sop code_optimization` → prompt updates to show
   `## Active SOP: code_optimization`; agent invokes Phase 0
   clarification.
4. `/exit-sop --reason "test"` → prompt's Active SOP section disappears.
   Re-entering recovers state.
5. `/sop code_optimization --var workflow_target_path=tests/fixtures/tiny_repo --fork-on-completion`
   → launches subprocess, completes Phase 0-3 in YOLO, hits Phase 3b
   must-gate, halts, ForkRouter creates new session with proposal
   selection ready for user.
6. The conversational inferencer's prompt template snapshot test (chapter
   6 T6.10) passes byte-identically across runs.
7. All Test Plan T*.* tests pass; coverage on new code ≥ 80%.
8. The audit checklist (§5) is green for the 3 existing SOPs.
9. Documentation:
   - `_dev/_docs/background_jobs.md` (user guide)
   - `_dev/_docs/sop_authoring.md` (how to write/migrate an SOP)
   - `_dev/_docs/yolo_mode.md` (when/why/how)
10. A changelog entry for each feature flag flip.

---

## 9. Owners & Reviewers (placeholder)

| Phase | Suggested owner | Reviewers |
|-------|----------------|-----------|
| A.1 (Input Queue) | Backend platform | Conversational-inferencer maintainer |
| A.2 (JobManager) | Backend platform | Server-side infra reviewer |
| B (Task simple) | Task-tool maintainer | Backend platform |
| C (`/background-job`) | Tools maintainer | Backend platform |
| D (YOLO + `/sop`) | Conversational-inferencer maintainer | SOP author |
| E (SOP registry) | SOP author | Backend platform |
| F (Prompt) | Conversational-inferencer maintainer | UX |
| G (Polish) | Backend platform | All |

---

## 10. Final Notes for Reviewers

- **The single most important file to scrutinize is**
  `chapter 2 §3.3-3.5` — the change to `conversational_inferencer.py`'s
  run loop. Everything else builds on it; if the queue integration is
  wrong, all five other features inherit the bug.
- **The second most important is**
  `chapter 4 §2-3` — the `__must__` semantics and YOLO auto-resolution.
  This is where destructive behavior could leak through.
- **The third is** `chapter 3 §3.7` — fork routing. Spawning new
  sessions from completion events crosses a session-boundary that
  doesn't exist anywhere else in the codebase.

Everything else (chapters 1, 5, 6, 7) is plumbing on top of those three.

---

*End of plan.*
