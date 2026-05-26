# Integrated Plan — Task Simple Mode (Template · Migration · Tests · Risks)

> Continuation of `INTEGRATED_TASK_SIMPLE_MODE_DESIGN.md`.

---

## 6. Template edit (`implementation/main/initial.jinja2`)

### 6.1 Pre-flight grep (verified zero collisions)

| Pattern | Hits outside `_dev/_plan/` | Decision |
|---------|---------------------------|----------|
| `has_approved_plan` | **0** | Safe to introduce. |
| `task_posture` | **0** | Not used; we don't introduce it (avoided by §0.2). |
| `APPROVED PLAN` | **1** (line 47 of the template) | The single surgery site. |
| `round_index` | **3 hits in templates** (initial:55, followup:25, review:22) | We touch only `initial.jinja2`'s use. The other two stay as-is (they're rendered in heavy/topology contexts where `round_index ≥ 1`). |

### 6.2 The two surgical edits

**Edit A — line 47–49 ("APPROVED PLAN" block).** Wrap in a conditional so
simple-mode (which OMITS `has_approved_plan`) gets adhoc wording; heavy
mode (which sets `has_approved_plan=True`) gets today's behavior.

**BEFORE (verbatim from disk):**
```jinja2
## NOTES (on agent behavior):
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
```

**AFTER:**
```jinja2
## NOTES (on agent behavior):
{% if has_approved_plan is defined and has_approved_plan %}
- You have an APPROVED PLAN that has been reviewed and refined. Follow it and only make new investigation when in doubt.
  * DO NOT re-investigate the entire codebase from scratch.
{% else %}
- You are starting from a single user request without a pre-approved plan.
  * Read minimally to ground yourself in the relevant code (file headers, target functions, immediate call sites). DO NOT investigate the entire codebase.
  * Then act decisively on the request. If the request is ambiguous, pick the most plausible interpretation, state it briefly in your `<Response>`, and proceed.
{% endif %}
```

**Edit B — line 55 (the `round{{ round_index }}/` path components).** Collapse the round directory segment when `round_index` is falsy (0 or absent), so simple mode produces clean paths.

**BEFORE (verbatim from disk):**
```jinja2
- If the user request involves/requires testing/benchmarking that produces output artifacts (e.g., testing details, benchmark  metrics), save them alongside `{{ output_path }}` under `tests/round{{ round_index }}/` and `benchmarks/round{{ round_index }}/`,
```

**AFTER:**
```jinja2
- If the user request involves/requires testing/benchmarking that produces output artifacts (e.g., testing details, benchmark  metrics), save them alongside `{{ output_path }}` under `tests/{% if round_index %}round{{ round_index }}/{% endif %}` and `benchmarks/{% if round_index %}round{{ round_index }}/{% endif %}`,
```

### 6.3 Caller-side change to preserve byte-identical heavy-mode behavior

After Edit A, **existing topology callers must pass `has_approved_plan=True`** when they render `initial.jinja2` for an implementation-child node that follows a planning node — otherwise the heavy-mode prompt would silently change.

The change is **one line** added wherever the topology runner constructs the render context for an implementation-child node. Locations to update (verified by subagent grep + my read of `multi_flow_inferencer.py:485, 702, 806, 854, 1219`):

- `agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/multi_flow_inferencer.py`
  — wherever it renders `implementation/main/initial.jinja2`, add `"has_approved_plan": True` to the `feed` dict.

A safer approach: add `has_approved_plan: True` as a default in the `multi_flow_inferencer`'s feed-construction helper, so every call that doesn't explicitly override it gets the heavy-mode behavior. Single point of change.

### 6.4 Why this is elegant (not hacky)

| Concern | Resolution |
|---------|------------|
| Drift between simple and heavy templates | None — single source of truth. |
| Future template improvements | Both modes benefit automatically. |
| Discoverability | Both branches live in one file, side-by-side. |
| Test surface | One template, two branches; 2 unit tests pin each. |
| New variant slot directories | **Zero.** No `_variables/task_posture/`, no parallel folders. |
| New template files | **Zero.** |
| Pattern consistency | Mirrors the existing `{% if employee is defined %}` guard. |

---

## 7. Concrete code-change list (single canonical list)

| # | File | Change |
|---|------|--------|
| 1 | `OpenStartup/src/openteam/server/resources/tools/task/tool.json` | Add `--simple` (default `false` in Phase 1, `true` in Phase 2). Add `--leaf-inferencer` (default `"auto"`). Flip `--full`'s default `true→false` in Phase 2. Update description text to mention simple mode. |
| 2 | `AgentFoundation/src/agent_foundation/resources/tools/task/tool.json` | Add the **same two new parameters** (`--simple`, `--leaf-inferencer`) and flip `--full`'s default per the phase plan. Do NOT attempt to re-mirror the full OpenStartup schema — the two files already have legitimate divergence (different aliases, different dual-agent params, etc.). Scope of this change is strictly additive: the two new flags + the one default-value flip. |
| 3 | `OpenStartup/src/openteam/server/resources/tools/task/executor.py` | Rewrite `_derive_mode_from_flags` per §4.3. Add `_run_simple_mode`, `_render_simple_prompt`, `_init_node_subdirs`, `_resolve_auto_leaf`, `_persist_inferencer_args`, `_safe_parse_output`, `_ensure_implementation_report`, `_write_meta` (per §5). Update `execute()` to dispatch on mode (§5.1) and to emit the Phase-1 deprecation warning when no explicit mode flag was supplied. **Heavy-path `_init_node_subdirs` call is deferred:** in Phase 1, do NOT call `_init_node_subdirs(create_children_dir=True)` from heavy-mode code paths — leave today's lazy-create behavior intact (zero blast radius). In Phase 2 (after simple mode has burned in), consider hoisting the pre-create call into heavy mode for layout consistency; track as a follow-up issue. |
| 4 | `OpenStartup/src/openteam/server/resources/tools/task/cli.py` | Add `--simple` and `--leaf-inferencer` argparse entries that mirror tool.json. Wire `explicit_simple` / `explicit_full` detection through to executor's `session_context` for the conflict-detection path. |
| 5 | `AgentFoundation/src/agent_foundation/common/jobs/__init__.py` | NEW (empty for now; reused by future SOP chapter). |
| 6 | `AgentFoundation/src/agent_foundation/common/jobs/leaf_factory.py` | NEW per §3.4. |
| 7 | `AgentFoundation/src/agent_foundation/resources/prompt_templates/implementation/main/initial.jinja2` | Two surgical edits per §6.2 (Edit A + Edit B). **No new template file.** |
| 8 | `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/flow_inferencers/multi_flow_inferencer.py` | Add `"has_approved_plan": True` to the `feed` dict at every callsite that renders `implementation/main/initial.jinja2` — OR add it once as a default in the feed-construction helper (preferred). Preserves byte-identical heavy-mode output after edit #7. |
| 9 | `OpenStartup/src/openteam/server/services/tool_dispatcher.py` (or equiv) | **Surface `_explicit_<flag>` for each mode flag.** The dispatcher already parses the raw user input (slash command string or argparse tokens) before applying schema defaults. Concrete mechanism: before merging schema defaults, snapshot which flag names appeared in the raw token list; emit them as a set `session_context["_explicit_flags"] = {"simple", "full", ...}`. Executor reads `explicit_simple = "simple" in session_context.get("_explicit_flags", set())` (and similarly for `full`, `plan`, `confirm`, `execute`). Single ~15 LoC change; one new helper `_extract_explicit_flag_names(raw_args, tool_schema)`. If the dispatcher doesn't centralize argv parsing today (i.e., schema-defaults are applied inline during parsing with no retained raw form), Phase 0 of this task adds the retention. Integration test T40 enforces end-to-end. |
| 10 | `tests/openteam/tools/task/test_simple_mode.py` | NEW per §9. |
| 11 | `tests/agent_foundation/.../prompt_templates/test_implementation_initial.py` | NEW per §9 — pins both `has_approved_plan` branches and `round_index` collapse. |

**Total NEW files: 4** (leaf_factory + 3 test files).
**Total MODIFIED files: 7.**
**Total NEW template files: 0.** (Reuse `implementation/main/initial.jinja2`.)
**Total NEW workspace allocator helpers: 0.** (Reuse `_shared/workspace_allocator.py`.)

---

## 8. Migration (three phases, no flag day)

| Phase | Duration | `--simple` default | `--full` default | Behavior |
|-------|----------|--------------------|------------------|----------|
| **Phase 1** | One release | `false` | `true` | Identical to today. Both flags resolvable; conflict raises ValueError. Deprecation warning printed if `not (explicit_simple or explicit_full or explicit_plan or explicit_confirm or explicit_execute)` — i.e., the user typed NO mode flag and is silently relying on the implicit `--full` default: "task default mode will change from --full to --simple in release vX.Y; pass --full explicitly to suppress this warning." The check uses `explicit_*` (dispatcher-supplied) NOT `arguments.get("full")`, because `arguments["full"]` is always True in Phase 1 due to the schema default. |
| **Phase 2** | One release | `true` | `false` | New default. Users who relied on the old heavy default must add `--full` explicitly. Deprecation warning gone. |
| **Phase 3** | Steady state | `true` | `false` | Stable. Feature flag and `_default_mode_is_simple()` helper removed; defaults baked into tool.json. |

**Per-call escape hatch:** env `OPENTEAM_TASK_DEFAULT_MODE=simple|full` overrides
the schema default. Used by ops / CI to lock behavior independently of
release cadence.

**SOP audit:** any existing SOP file that says `/task <request>` and
genuinely needs the heavy path must be updated to `/task --full <request>`.
Audit checklist (chapter 8 §5 in the SOP plan) tracks this.

---

## 9. Test plan

| # | Test | Type | Why it matters |
|---|------|------|----------------|
| **Mode resolution** | | | |
| T1 | `_derive_mode_from_flags({"plan":True}, ...)` → `"plan"` | Unit | Phase-selector precedence (§4.2). |
| T2 | `_derive_mode_from_flags({"confirm":True}, ...)` → `"confirm"` | Unit | Same. |
| T3 | `_derive_mode_from_flags({"execute":True}, ...)` → `"execute"` | Unit | Same. |
| T4 | `_derive_mode_from_flags({}, explicit_simple=True, explicit_full=True)` → ValueError | Unit | Conflict detection. |
| T5 | `_derive_mode_from_flags({"full":True}, explicit_full=True)` → `"full"` | Unit | Explicit `--full` wins over default. |
| T6 | Phase 1: `_derive_mode_from_flags({}, ...)` → `"full"` (feature flag off) | Unit | Backward compat in Phase 1. |
| T7 | Phase 2: `_derive_mode_from_flags({}, ...)` → `"simple"` (feature flag on) | Unit | New default in Phase 2. |
| **Workspace** | | | |
| T8 | `_run_simple_mode` creates workspace at `<runtime_root>/tasks/task/task_<ts>_<8hex>/` with the 5 standard subdirs and NO `children/` | Integration | §3.1. |
| T9 | `_init_node_subdirs(ws, create_children_dir=True)` creates `children/`; with `False` does not | Unit | §3.3. |
| T10 | Path regex match: `tasks/task/task_\d{8}_\d{6}_[0-9a-f]{8}` | Unit | Naming convention. |
| T11 | `_resolve_workspace` honors `working_dir` in session_context for `--resume` | Unit | Preserves existing behavior (§2.4). |
| T12 | When `session_root` is set in context, workspace lands under `<session_root>/tasks/` (server-affiliated) | Unit | Path-B routing. |
| **Leaf factory** | | | |
| T13 | `make_leaf_inferencer("claude_code_cli", cache_dir=…)` returns `ClaudeCodeCliInferencer` with `model_name="sonnet"` and `cache_folder=str(cache_dir)` | Unit | §3.4. |
| T14 | `make_leaf_inferencer("rovodev_cli", cache_dir=…)` returns `RovoDevCliInferencer` with `model_id=""`, `yolo=True`, `cache_folder=str(cache_dir)` | Unit | §3.4. |
| T15 | `make_leaf_inferencer("claude_api")` returns `ClaudeApiInferencer` with `cache_dir`/`target_path` ignored | Unit | API leaves correctly no-op these. |
| T16 | `make_leaf_inferencer("unknown")` raises ValueError | Unit | Defensive. |
| T17 | `make_leaf_inferencer(...)` does NOT pass `session_log_dir` kwarg (would crash) | Unit | Corrects both predecessor plans' wrong assumption. |
| **Auto-leaf** | | | |
| T18 | `_resolve_auto_leaf({"calling_inferencer_class": "ClaudeCodeCliInferencer"})` → `"claude_code_cli"` | Unit | Tier 1 of §4.5. |
| T19 | `_resolve_auto_leaf({})` with env `OPENTEAM_TASK_DEFAULT_LEAF=rovodev_cli` → `"rovodev_cli"` | Unit | Tier 2. |
| T20 | `_resolve_auto_leaf({})` with no env → `"claude_code_cli"` | Unit | Tier 3 (hardcoded last resort). |
| **Template — required-variable contract** | | | |
| T21 | Render `initial.jinja2` with simple-mode kwargs (no `has_approved_plan`, `round_index=0`) → succeeds, no Jinja2 UndefinedError | Unit | All required vars supplied. |
| T22 | Output contains "starting from a single user request without a pre-approved plan" (adhoc branch chosen) | Unit | Edit A §6.2 simple-mode branch. |
| T23 | Output does NOT contain "APPROVED PLAN" in simple-mode render | Unit | Anti-regression. |
| T24 | Output contains "tests/" and "benchmarks/" (no `round0/` segment) | Unit | Edit B §6.2 collapse with falsy round_index. |
| T25 | Render with `has_approved_plan=True` → output contains "APPROVED PLAN", no adhoc wording | Unit | Heavy-mode branch preserved. |
| T26 | Render with `round_index=2` → output contains "tests/round2/" and "benchmarks/round2/" | Unit | Heavy-mode path preserved. |
| **Executor — success path** | | | |
| T27 | `/task --simple "hello"` (mock leaf) writes `outputs/raw_response.txt`, `outputs/parsed_output.json`, `outputs/implementation_report.md`, `artifacts/meta.json` (status=completed) | Integration | §5.2 success path. |
| T28 | `artifacts/inferencer_args.json` has REDACTED entries for any field whose name matches `_REDACT_FIELDS` | Unit | §5.5 redaction. |
| T29 | `artifacts/input_prompt.md` is byte-identical to what was passed to `ainfer_streaming` | Integration | §5.2 step "write input_prompt.md". |
| T30 | Streaming chunks accumulate into `outputs/raw_response.txt` (no chunk lost) | Integration | §5.2 streaming loop. |
| **Executor — failure path** | | | |
| T31 | Leaf raises `RuntimeError` mid-stream → `meta.json` status=`"failed"`, error message captured, partial `raw_response.txt` written, executor returns `success=False` | Integration | §5.2 try/finally. |
| T32 | `asyncio.CancelledError` mid-stream → re-raised; `meta.json` status=`"cancelled"`, partial outputs preserved | Integration | §5.2 cancellation handling. |
| T33 | `parse_output` raises → `_safe_parse_output` falls back to `<Response>` extraction | Unit | §5.6 fallback. |
| T34 | No `<Response>` tags in raw → `_safe_parse_output` returns `{"response": <raw>}` | Unit | Universal fallback. |
| **Fallback report** | | | |
| T35 | Claude Code leaf wrote `implementation_report.md` → `_ensure_implementation_report` is no-op | Unit | §5.4. |
| T36 | claude_api leaf (no file tools) → `_ensure_implementation_report` writes `<Response>` body to `implementation_report.md` | Unit | §5.4 fallback. |
| **Heavy mode preserved** | | | |
| T37 | `/task --full "fix"` still routes to existing topology runner; workspace contains `children/` | Integration | §5.1 dispatch + #3 in code-change list. |
| T38 | Heavy-mode prompt rendered via `multi_flow_inferencer` is byte-identical before/after edits #7+#8 | Snapshot test | Anti-regression. |
| **CLI parity** | | | |
| T39 | Standalone CLI `task --simple "hi"` produces same workspace pattern + artifacts as in-conversation `/task --simple "hi"` | Integration | cli.py parity. |
| T40 | Standalone CLI `task --simple --full "x"` exits with non-zero status and error message about conflict | Unit | Conflict surfaces at CLI layer too. |
| **End-to-end smoke** | | | |
| T41 | Real `/task "what does this repo do?"` against Claude Code CLI (model=sonnet) → all 4 expected files in `outputs/` and `artifacts/`, response sensible, duration < 90s | E2E (gated on `ENABLE_E2E_LLM_TESTS=1`) | Sanity. |

**Coverage target:** ≥ 85% on new code in `executor.py` simple-mode functions + `leaf_factory.py`.

---

## 10. Risks & mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Behavior change in Phase 2: existing scripts/SOPs that relied on implicit heavy mode silently get simple-mode | Med | High | One-release deprecation warning + env var escape hatch + SOP audit checklist. |
| R2 | The template edit changes heavy-mode prompt content for callers that don't pass `has_approved_plan=True` | Low | High | Default `has_approved_plan: True` in `multi_flow_inferencer`'s feed-construction helper (single-point change #8). Snapshot test T38 enforces byte-identical heavy-mode output. |
| R3 | Leaf inferencer ctor kwarg mismatch (`session_log_dir`) crashes simple mode | High if not corrected | High | Already corrected in §3.4: factory signature excludes `session_log_dir`. T17 enforces. |
| R4 | `claude_code_cli` default model `"sonnet"` may not match session model config | Low | Low | `--model` flag still works; auto-leaf can be overridden. |
| R5 | API leaf has no file tools → no `implementation_report.md` from LLM | Med | Low | `_ensure_implementation_report` fallback (§5.4). |
| R6 | Failure path leaves orphan workspace dirs cluttering `_runtime/tasks/task/` | Med | Low | `meta.json` always present (try/finally) so cleanup jobs can identify+purge by status & age. |
| R7 | Streaming inferencer never yields (hang) | Low | Med | `--timeout` flag deferred to chapter 3 (background-job); for foreground simple mode, the upstream caller's cancellation semantics apply (`asyncio.CancelledError` handled in T32). |
| R8 | Concurrent simple-mode runs collide on the same workspace path | Very low | Low | `uuid4().hex[:8]` collision probability is negligible; `mkdir(exist_ok=True)` is idempotent; the `_TS` component provides additional separation. |
| R9 | The `multi_flow_inferencer` feed-construction has multiple call sites for `implementation/main/initial.jinja2` and we miss one | Med | High | Step #8 in code-change list says "preferred: add default in feed-construction helper, single point". The dispatch-by-helper approach is the safe form. If multi_flow_inferencer doesn't have such a helper today, ADD one before flipping the template — single-PR refactor. |
| R10 | The `_explicit_simple` / `_explicit_full` plumbing required from the dispatcher is overlooked | Med | Med | Step #9 in code-change list. Add an integration test that injects both flags explicitly via the dispatcher and asserts ValueError surfaces. T40 covers the CLI side. |

---

## 11. Decision log (merged from both predecessor plans)

| # | Decision | Source | Rationale |
|---|----------|--------|-----------|
| DL1 | Reuse `implementation/main/initial.jinja2`; do NOT create a new template | rovodev plan §3.3 (correct direction) | Avoids template drift; inherits 8 production-grade contracts; minimal diff. |
| DL2 | Do NOT introduce a `_variables/task_posture/` variant slot | New | Variant slots are for content that differs substantively (e.g., aggregation vs default). For an on/off prose toggle, an inline `{% if %}` is the right level. |
| DL3 | Default leaf inferencer = `"auto"` resolving to caller's class, then env, then `claude_code_cli` | New (merging claude_code's `claude_code_cli` default + rovodev's `rovodev_cli` default) | Neither predecessor had a defensible rationale for hardcoding one over the other. Auto-pick respects the parent agent's choice. |
| DL4 | Reuse `_shared/workspace_allocator.allocate_tool_workspace("task", base_dir=...)`; do NOT write a new `task/workspace.py` | New (both predecessor plans missed this) | The existing helper produces the exact path pattern needed. Reuse > create. |
| DL5 | Add `_init_node_subdirs(workspace, create_children_dir=False)` as a tiny new helper (~10 lines) | New | The one thing the existing allocator doesn't do (it allocates the root dir only). Keep in `executor.py` or hoist to `_shared/workspace_allocator.py`. |
| DL6 | try/finally always writes outputs + meta with status; never lose partial work | claude_code plan §3.3 (correct) | Production resilience. |
| DL7 | `_REDACT_FIELDS = {"api_key","token","secret","password","auth_token"}` for `inferencer_args.json` | claude_code plan §3.7 (correct) | Security. |
| DL8 | Three-phase migration: deprecation warning → default flip → cleanup | Both plans | Standard staged rollout; users get one release to adjust. |
| DL9 | `--plan` / `--confirm` / `--execute` are phase selectors that override `--simple` | New (neither plan addressed) | These flags are categorically different from simple/full; they pick specialized planning sub-topologies. They should never silently disappear under the new default. |
| DL10 | `has_approved_plan=True` defaults at the multi_flow_inferencer's feed-construction helper (one-line single-source change) | New | Preserves byte-identical heavy-mode behavior with the smallest possible blast radius. |
| DL11 | Leaf factory does NOT accept `session_log_dir` kwarg | New (corrects both plans) | Verified by direct file read; passing it would crash on construction. |
| DL12 | Simple mode reuses `_resolve_workspace` (not `_allocate_workspace` directly) | New | Preserves `working_dir` honoring and `--resume` semantics. |

---

## 12. Open questions (the ones that genuinely remain)

1. **Should simple mode support multi-turn?** Both predecessor plans
   said no. Decision retained: simple mode is one-shot. Multi-turn is
   the conversational inferencer's job (it can call `/task` repeatedly
   with accumulating context).
2. **Where does `_init_node_subdirs` live — in `executor.py` or
   `_shared/workspace_allocator.py`?** Recommendation: start in
   `executor.py`; hoist to `_shared` when a second tool needs it.
   YAGNI applies.
3. **Should `--leaf-inferencer auto` ever pick API leaves?** No — API
   leaves cannot run file-tool workflows, and most task requests want
   filesystem access. Tier 1 (caller-class) is what surfaces API leaves
   if the parent agent is itself an API leaf (rare).
4. **What if the `multi_flow_inferencer` has no centralized feed-construction
   helper?** Then add one as part of step #8. Pre-PR investigation
   (Phase B owner) should `grep -rn 'implementation/main/initial' AgentFoundation/`
   and audit each call site.

---

## 13. Definition of done

This integrated plan is "done" when:

1. Test plan §9 fully passes (≥ 85% coverage on new code).
2. `/task "hello world"` completes in < 60s via the Phase-2 default
   simple mode, producing the expected 4 output files + 3 artifact files.
3. `/task --full "hello world"` still produces today's heavyweight
   topology workspace with `children/`, with snapshot-identical prompt
   rendering for the implementation-child node (T38).
4. Phase-1 deprecation warning fires when no explicit mode flag is set,
   and is silent when `--full` is passed explicitly.
5. SOP audit checklist has identified every `/task <…>` callsite in
   existing SOPs and explicitly tagged it `--simple` or `--full`.
6. Documentation:
   - `_dev/_docs/task_simple_mode.md` — user guide
   - Inline docstrings on all new functions in `executor.py` and
     `leaf_factory.py`
7. A changelog entry for each phase transition.

---

## 14. Cross-references

This integrated plan supersedes:
- `conversational_inferencer_sop_integration/claude_code/02_task_simple_mode.md`
- `conversational_inferencer_sop_integration/rovodev/01_task_simple_mode.md`

It is consumed by:
- The Background Jobs chapter (chapter 3 in both predecessor plans) —
  `/background-job task ...` will invoke simple mode by default.
- The SOP subprocess runner chapter (chapter 5 in both) — the SOP runner
  uses `make_leaf_inferencer` from `common/jobs/leaf_factory.py` (file #6
  in §7), exactly as both plans assume.

---

*End of integrated plan. Three files total:*
- *`INTEGRATED_TASK_SIMPLE_MODE.md` — comparison, motivation, ground-truth facts*
- *`INTEGRATED_TASK_SIMPLE_MODE_DESIGN.md` — workspace, factory, executor*
- *`INTEGRATED_TASK_SIMPLE_MODE_TEMPLATE.md` — template, migration, tests, risks (this file)*
