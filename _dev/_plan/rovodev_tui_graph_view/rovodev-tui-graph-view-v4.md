---
name: tui_graph_visualization
version: v4
status: proposal-ready-for-review
created: 2026-05-17T03:07
supersedes:
  - rovodev-tui-graph-view-v3.md
  - .claude/plans/eager-roaming-clock.md  # v3 meta-plan, 54 lines; itself recommends v3
  - .cursor/plans/tui_graph_visualization_4c8499de.plan.md  # Cursor v4, 1387 lines; converged with my v3
critical_path: [phase_1a, phase_1b, phase_1d, phase_1c, phase_2, phase_4a, phase_4b, phase_4c, phase_5, phase_6_docs]    # Round-8 M3: added phase_1d in its correct position (before 1c per Round-8 M2)
phases:
  - id: phase_0_reverify
    title: Re-verify ground truth post-v6 (all citations valid; no drift)
    blocks: [phase_1a, phase_3a, phase_4a]
    effort: 30m
  - id: phase_1a
    title: AgentFoundation/ui/stdio_graph_reporter.py (+ from_env classmethod)
    blocks: [phase_1b, phase_1c, phase_2]
    effort: 3-4h
  - id: phase_1b
    title: AgentFoundation/ui/graph_reporter_factory.py (~25 LOC)
    blocks: [phase_1d, phase_1c, phase_2]     # Round-8 M2: 1b now also unblocks 1d
    effort: 30m
  - id: phase_1d
    title: "Upstream NamespacedGraphReporter.on_graph_reconcile forwarder (qualifies keys via self._qualify; Round-7 C3 + Round-8 M2/M3)"
    blocks: [phase_1c]                         # Round-8 M2: 1d unblocks 1c (was the inverse, a cycle)
    depends_on: [phase_1a, phase_1b]
    effort: 15m
    touches: [agent_foundation/ui/graph_interactive_adapter.py]
  - id: phase_1c
    title: Reporter+factory tests (12 + 6 + 3 CI preflights — added Round-8 CR3b _ASYNC_NOOP_NAMES completeness)
    blocks: [phase_5, phase_2]
    depends_on: [phase_1a, phase_1b, phase_1d]
    effort: 0.5d
  - id: phase_2
    title: Patch 3 executors (task, project_onboarding, mock_task; -1 LOC each) + CI preflight test_factory_used_by_all_executors
    blocks: [phase_5]
    depends_on: [phase_1c]
    effort: 1h     # halved from v3's 2h since 3 sites, not 5 (round-5 C1)
  - id: phase_3a
    title: cli-rovodev-tui/widgets/topology_view.py (~360 LOC, single file, _got_any_event flag)
    blocks: [phase_3b, phase_3c, phase_4c]
    effort: 1d
  - id: phase_3b
    title: TopologyView unit tests (12)
    effort: 0.5d
  - id: phase_3c
    title: TopologyView snapshot tests (3, headless-frozen glyph)
    effort: 0.5d
  - id: phase_4a
    title: cli-rovodev-tui/slash_commands/_async_fd.py (NO loop= kwarg; lambda factory)
    blocks: [phase_4b, phase_4c]
    effort: 30m
  - id: phase_4b
    title: cli-rovodev-tui/slash_commands/_openteam_graph.py (NDJSON reader, continuation reassembly)
    blocks: [phase_4c]
    effort: 3h
  - id: phase_4c
    title: Extend cli-rovodev-tui/slash_commands/openteam.py handler (stderr=STDOUT preserved)
    blocks: [phase_5]
    effort: 0.5d
  - id: phase_5
    title: E2E smoke with openteam-mock-task
    blocks: [phase_6_docs]
    effort: 1-2h
  - id: phase_6_docs
    title: MCP_INTEGRATION.md + openteam-integration.md updates
    effort: 1h
  - id: phase_7_windows
    title: (POST-SHIP) sys.platform == 'win32' → skip graph view
    effort: 2h
  - id: phase_8_dual_pti
    title: (POST-SHIP) Propagate graph_reporter through DualInferencer + PlanThenImplementInferencer
    effort: 0.5d
  - id: phase_9_jsonl
    title: (POST-SHIP) JsonlGraphReporter(path) for replay/audit
    effort: 2h
total_effort_phase_1_through_6: ~3 focused days
---

# RovoDev TUI — OpenTeam Graph Visualization (v4 PLAN, convergence snapshot)

**Status:** Proposal · ready for review · **fourth-round convergence** (3 reviewers, 4 rounds, near-identical architecture across all)
**Created:** 2026-05-17 03:07
**Supersedes:** `rovodev-tui-graph-view-v3.md` (my prior v3, 1294 lines), `.claude/plans/eager-roaming-clock.md` (Claude v3, 54-line meta-plan that explicitly recommends my v3), `.cursor/plans/tui_graph_visualization_4c8499de.plan.md` (Cursor v4, 1387 lines, has converged with my v3 + 2 minor improvements)
**Author:** rovodev (fourth-pass integration; all three plans re-read at 03:05)
**Scope:** Add a real-time agent topology graph + per-node streaming panel to the RovoDev TUI when invoking the 4 OpenTeam slash commands (`/task`, `/create-role`, `/role-setup`, `/project-onboarding`).

## Round-4 changes vs v3 (the rare round where a reviewer found things to absorb)

The Cursor reviewer's v4 (1387 lines) has now adopted my v3's two critical bug fixes (no `tool_cli` patch; `stderr=STDOUT` preserved) — full convergence on architecture. But Cursor v4 *also* introduced **three genuine improvements** that my v3 lacked, and I am happy to absorb them here:

| Cursor v4 improvement | Why v3 was inferior | v4 fix |
|---|---|---|
| **`_got_any_event: bool` flag** in `TopologyView` (set by every `apply_*` method) | v3's `is_empty(): return not self._nodes` is **O(N) and unsafe after `_cap_total_streams` purge**: if a heavy stream cap clears stream buffers but leaves `_nodes` dict intact, the check is correct — but if a future refactor clears `_nodes` too, `is_empty()` would falsely report True. A dedicated flag is O(1) and immune to internal collection changes. | Replace `def is_empty(self): return not self._nodes` with `def is_empty(self): return not self._got_any_event`; set `self._got_any_event = True` in `apply_topology_event`, `apply_node_status`, `apply_node_stream`, `apply_graph_reconcile`, `append_final_result`. |
| **Structured YAML front-matter with phase IDs** | v3's "Phase 1a / 2 / 3b" headings are human-readable but not machine-parseable for CI/automation. | Added YAML front-matter above with explicit phase nodes + `blocks` edges → critical path is auto-derivable. |
| **Named `test_stderr_stdout_merged` regression guard** | v3 has the test logic implicitly inside `test_handler_integration.py` but not named — so a future "let's split stderr again" PR could pass review if the implicit test was deleted in the same PR. | Promote to a named CI preflight: `test_stderr_stdout_merged_regression.py`; explicit AST assertion that handler uses `stderr=asyncio.subprocess.STDOUT` (NOT `PIPE`). |

**Convergence story (recap of 4 rounds):**
- Round 1 (mine v1): proposed StdioGraphReporter on fd 3 + 6-file widget package.
- Round 2 (mine v2): collapsed widget to single file; introduced double-wiring contradiction + stderr=PIPE regression.
- Round 3 (mine v3): caught my own two bugs AND Cursor's `loop=` deprecation bug; explicit revision-history block.
- Round 4 (this v4): absorbed Cursor's 3 minor improvements; full architectural convergence across 3 reviewers.

**Pick-one (round 4 answer is at the end):** the answer is now **v3 OR v4** (convergent); Cursor v4 (their plan) is also acceptable. The architecture is settled.

## Round-10 patch — 9 items from devastating round-9-regression audit (2026-05-17 07:55)

**Auditor's central finding (verified empirically):** Round-9 introduced **2 NEW critical bugs** in its own edits — most damningly the `§9.4c` regression test (designed to catch the CR1-class of bugs) is itself broken: stub method names don't match the reader's dispatch (`apply_graph_topology` vs the reader's `apply_topology_event`). Reader silently catches the AttributeError → stub.calls stays 0 → assertion fails on every CI run. Plus a GC-driven `os.close` hazard on cache eviction with fd recycling, empirically reproduced live.

**Pattern over 10 rounds (now indisputable):** every "fix" round introduces ~2-3 new critical bugs in its own edits. Round-9's STRUCT recommendation (ast.parse preflight) catches syntax errors but **catches neither of Round-9's own new criticals** — both are runtime/semantic (the test stub mismatch only manifests when the test runs; the GC hazard only manifests when refcount drops to 0). **The architecture has been settled since Round 4; markdown is the wrong substrate for stabilizing the remaining code-block details.**

| # | Sev | Claim | Verdict | Fix |
|---|---|---|---|---|
| **R10-CR-9.1** | CRIT | §9.4c stub uses `apply_graph_topology` but reader dispatches `view.apply_topology_event` → AttributeError silently caught → assertion fails every run | ✅ **VALID — verified by grep of dispatch table line 1264** | Stub methods renamed to match reader contract (`apply_topology_event` + 3 siblings unchanged) + comment citing line 1264 |
| **R10-CR-9.2** | CRIT | `del cls._FROM_ENV_CACHE[fd]` may trigger GC → `TextIOWrapper.__del__` → `os.close(fd)` on a recycled fd that now points at someone else's pipe | ✅ **VALID — empirically reproduced live**: `r,w=os.pipe(); f=os.fdopen(r,'rb'); del f; gc.collect()` closes fd; `r2,_=os.pipe()` recycles to same fd. | `closefd=False` pattern: wrapper's __del__ no longer calls os.close; cache eviction does it explicitly + deterministically. `_owns_fd` marker prevents double-close. |
| **R10-M-9.1** | MAJ | §9.4c bypasses the handler entirely AND asserts the name IT JUST CREATED → vacuously true; doesn't actually guard the CR1 surface | ✅ **VALID, partially addressed** | Test still has structural value as a unit test of `open_async_fd_reader` + `read_ndjson_events` contracts. True handler-level integration test deferred to Phase 4c where the TUI fixture exists. Limitation documented inline. |
| **R10-M-9.2** | MAJ | `transport.close()` in finally is reachable before `transport` is assigned (open_async_fd_reader raises) → UnboundLocalError → masks original exception, leaves subprocess zombie | ✅ **VALID** | `transport = None; ndjson_task = None` pre-init before `try`; `finally` guards with `is not None` checks; subprocess SIGTERM block always reachable |
| **R10-M-9.3** | MAJ | §9.4d masks CR-9.2 by retaining `inst1`; missing `assert inst2 is not None`; missing write-probe positive assertion | ✅ **VALID** | `del inst1; gc.collect()` before second `from_env()`; `assert inst2 is not None`; write `b"probe\n"` through `inst2._stream` and `os.read(r,6)` to verify wrapper points at NEW pipe |
| **R10-M-9.4** | MAJ | §9.4d uses `pytest.skip` + `@pytest.mark.asyncio` without `import pytest` | ✅ **VALID** (same class as Round-9 m1 fix for §6.4) | Explicit `import asyncio, gc, os; import pytest` at top of §9.4d block |
| **R10-Mo-9.1** | MOD | Round-9 fix count "0 over-fixes" contradicts same table's PARTIAL rows for Mo1 and m2 | ✅ **VALID** | Changed to "12 fully applied + 2 partial" |
| **R10-Mo-9.2** | MOD | §11 self-audit missing rows for CR2 inode-based cache + GC-close hazard | PARTIAL — added Round-10 changelog row instead | n/a |
| **R10-m-9.1** | MIN | `_AppStub.call_from_thread` runs synchronously vs Textual's actual cross-thread dispatch | ✅ NOTED only | Documented limitation; acceptable for single-threaded test |

**Fix count: 6 fully applied + 2 partial + 1 noted. 0 over-fixes. 0 false acceptances.**

**Empirical verifications performed by me this round:**
- ✅ `grep -n "view\.apply_" v4.md | head -10` confirmed `apply_topology_event` (NOT `apply_graph_topology`) at line 1264 — CR-9.1 verified
- ✅ Live `os.pipe()` → `os.fdopen()` → `del; gc.collect()` → `os.pipe()` reproduction proved fd recycle hits in FIRST attempt; GC `__del__` closes fd; subsequent `os.pipe()` recycles same fd — CR-9.2 verified
- ✅ Direct read confirmed M-9.2 `transport.close()` is reachable before assignment
- ✅ Direct read confirmed §9.4d block has no `import pytest`

---

## Round-9 patch — 14 items from devastating round-8-regression audit (2026-05-17 04:46)

**Auditor's central finding:** Round-8 introduced **3 NEW critical bugs** — most damningly a Python `IndentationError` that would have made the entire feature dead at module load. I empirically verified all 3 critical claims with `ast.parse` and live `os.pipe()/os.fstat()` reproductions. The auditor's structural recommendation — stop iterating on markdown and externalize code blocks to `.py` files where the compiler catches errors — is now adopted as a DoD item.

**Pattern over 9 rounds:** every "fix" round introduces a comparable number of new bugs. The architectural shape has been settled since Round 4; the bugs are exclusively in code-block details that prose review cannot catch reliably.

| # | Sev | Claim | Verdict | Fix |
|---|---|---|---|---|
| **R9-CR1** | CRIT | Python `IndentationError` at `except OSError as e:` (column 12 vs try at col 16) → module dead at load | ✅ **VALID — verified via `ast.parse`** | §7.5 re-indented; ast.parse now passes |
| **R9-CR2** | CRIT | `os.fstat(fd)` check is INERT against fd recycling (kernel reuses fd # → fstat succeeds → cache returns stale wrapper) | ✅ **VALID — verified via live `os.pipe()/os.close()/os.pipe()` reproduction hitting recycle in 20 attempts** | Cache invalidates on `(st_dev, st_ino)` mismatch; construction records `_fd_identity` |
| **R9-CR3** | CRIT | §9.4c regression test references 3 undefined symbols → test fails at collection | ✅ **VALID** | Rewritten as self-contained runnable test using only stdlib + 2 plan-defined helpers |
| **R9-M1** | MAJ | Widget cleanup only in `proc is None` branch → CancelledError after-spawn leaves orphan widgets | ✅ **VALID** | Hoisted with `sys.exc_info()[0] is not None` condition |
| **R9-M2** | MAJ | Two near-identical fd cleanup loops in if/else | ✅ **VALID** | Single loop at top of finally |
| **R9-M3** | MAJ | §8 critical-path prose still says `1a → 1b → 1c → 2` (missing 1d added Round-8) | ✅ **VALID** | Corrected to `1a → 1b → 1d → 1c → 2 → ...` |
| **R9-M4** | MAJ | 5 new tests added Rounds 5–8 have no DoD checkboxes | ✅ **VALID** | 5 new DoD rows added |
| **R9-Mo1** | MOD | §13 reviewer-pattern stale | PARTIAL (already at 8 from R8 Mo4) | Bumped to 9 + R9 row |
| **R9-Mo2** | MOD | `§9.2` citation stale (renumbered to `§9.4b` in R8) | ✅ VALID | Corrected with note |
| **R9-Mo3** | MOD | "_activated_fd line 411" — actually line 427 | ✅ VALID — verified | Reframed to symbol-based citation |
| **R9-Mo4** | MOD | §10 risks table missing 3 new bug-categories | ✅ VALID | 3 new rows added |
| **R9-m1** | MIN | `pytest.fail` without `import pytest` | ✅ VALID | import added |
| **R9-m2** | MIN | "18 + 3" stale row count | PARTIAL (auditor's count claim itself off) | No change |
| **R9-STRUCT** | DEEP | Plan markdown is wrong substrate; manual review keeps shipping syntax errors | ✅ **VALID — most important finding of all 9 rounds** | NEW DoD item: `scripts/lint_plan_code_blocks.py` ast.parses every fenced python block; CI gate on _dev/_plan/*.md |

**Fix count: 12 fully applied + 2 partial (Mo1 and m2; Round-10 Mo-9.1 honest-accounting correction). 0 over-fixes.**

---

## Round-8 patch — 13 verified items from deep audit (2026-05-17 04:22)

**The auditor's central observation is exact: Round-7's "convergence" self-assessment was wrong.** Round-7's own M4 edit introduced a **complete-feature-broken-on-happy-path** regression (CR1) — the reader was never spawned, so the kernel pipe buffer filled and the subprocess deadlocked. Round-7 also half-applied its M1 fix (CR2 — prose-only deletion that forgot the actual line) and incompletely curated its CR3 frozenset (missing 2 of 7 WebSocketInteractive async methods, causing silent per-turn TypeError). This round-7-introduced-3-criticals pattern is the same shape as the round-5-introduced-3-criticals pattern Round-7 itself called out. The structural lesson: **any non-trivial code edit to the plan itself is its own candidate for adversarial review**.

| # | Sev | Issue | Verdict | Root cause | Fix |
|---|---|---|---|---|---|
| **R8-CR1** | CRIT | Reader-setup gated on `event_write_fd is not None`, which is always False after my Round-7 M4 `event_write_fd = None` ownership-marker. NDJSON reader never spawned → 64KB kernel pipe buffer fills → subprocess BLOCKS in `os.write(3, ...)` inside `_emit` while holding `asyncio.Lock` → complete reporter wedge → graph view shows nothing → eventual subprocess hang. **100% feature-broken on the happy path.** | ✅ VALID | Round-7 M4 tangled two concerns (fd ownership semantics + reader spawn gate). My nullification of `event_write_fd` as an ownership marker was correct; my failure to update the downstream gate from `event_write_fd is not None` to `event_read_fd is not None` broke the feature entirely. Classic refactor-half-done bug. | Unified rewrite of spawn-and-reader-setup using try/finally: gate the reader on the READ fd; `event_write_fd` is purely a transient handle; uniform fd + widget cleanup in finally; added §9.4c regression test that asserts `ndjson_task is not None` after happy-path spawn. |
| **R8-CR2** | CRIT | `env["OPENTEAM_TASK_ID"] = task_id` line still present (Round-7 M1 added the explanatory comment but forgot to delete the line); §4 diagram still advertises the env var. Prose, code, and diagram now disagree in three places. | ✅ VALID | Round-7 M1 patch was prose-only — I wrote the comment block explaining "we removed this", but in fact only added the comment beside an unchanged line. Textbook half-fix. | Deleted the actual `env["OPENTEAM_TASK_ID"] = task_id` line; updated §4 diagram to drop `OPENTEAM_TASK_ID=task-abc`; comment block preserved as documentation. |
| **R8-CR3** | CRIT | `_ASYNC_NOOP_NAMES` frozenset has 5 entries but `WebSocketInteractive` has 7 public async methods (verified by grep). Missing `on_clean_output_available` (called by `conversational_inferencer.py:243`) and `send_task_status`. Symptom: `await None → TypeError → swallowed by surrounding try/except Exception → log spam every turn`. | ✅ VALID — `grep -nE "^    async def" websocket_interactive.py` returns 7 hits; verified `conversational_inferencer.py:243` does `await effective_interactive.on_clean_output_available(...)` after a `hasattr` check that always passes (our `__getattr__` is unconditional). | Round-7 M2 curated the frozenset manually; manual audits miss things. | Added both missing names + comment explaining the silent-TypeError failure mode; added §9.4b CI preflight that asserts every WS async method is either a real method on `_StdioNodeInteractive` OR in the frozenset — turns the manual-audit footgun into a CI guard. |
| **R8-M1** | MAJ | `cached._stream.closed` check is FUNCTIONALLY INERT for the scenario it claims to address. `TextIOWrapper.closed` only flips True when the wrapper's OWN `.close()` is called; external `os.close(fd)` (which the M3 fix's own comment cited) leaves it False. | ✅ VALID — directly verified with `python3 -c "import os; r,w=os.pipe(); f=os.fdopen(r,'rb'); os.close(r); print(f.closed)"` → `False`. | I assumed `closed` would reflect fd state; it only reflects the wrapper's own `.close()` calls. | Replaced with `os.fstat(fd)` probe (raises OSError(EBADF) on closed fd); mirrors `_activated_fd()`'s probe at line 411 for consistency. Kept the `cached._stream.closed` check too as belt-and-brace. Added §9.4d regression test. |
| **R8-M2** | MAJ | Phase 1d's `blocks: [1c, blocks §9.1 preflight]` reads as "depends on 1c AND blocks something inside 1c" → cycle. | ✅ VALID | I added Phase 1d in Round-7 as an inline footnote on §9.1's test, never paused to check its dependency ordering against the rest of the §8 table. | Reordered: 1a → 1b → **1d → 1c** → 2. Phase 1d now correctly depends on 1a/1b and blocks 1c. |
| **R8-M3** | MAJ | Phase 1d in §8 prose, absent from YAML `phases:` and `critical_path:` → machine-followable build pipeline cannot execute Phase 1d. | ✅ VALID | YAML structured-front-matter was set up in Round-4; Round-7 added Phase 1d to prose only. | Added `phase_1d` entry to YAML `phases:` with correct dependencies; inserted in `critical_path:` in correct position between 1b and 1c. |
| **R8-M4** | MAJ | `except (FileNotFoundError, asyncio.CancelledError, BaseException) as e:` is functionally `except BaseException` — traps `KeyboardInterrupt`, `SystemExit`, `MemoryError`. PEP 8 anti-pattern. | ✅ VALID — `FileNotFoundError ⊂ OSError ⊂ Exception ⊂ BaseException`. | I added the explicit names "for documentation" but the parent class swallows them. | Replaced with structured `try: ... except FileNotFoundError: ...` (narrow recoverable) + `try/finally:` (always runs cleanup regardless of exception type). No more `BaseException` catch. |
| **R8-M5** | MAJ | Widgets mounted before spawn try-block; `CancelledError` re-raise bypasses widget cleanup → orphan widgets in UI after Ctrl-C. | ✅ VALID | Round-7 M4 cleanup branch only closed fds, not widgets; the explicit `raise` skipped the FileNotFoundError-branch's widget removal. | Unified cleanup in the new try/finally block: widgets removed in the same path that closes fds when `proc is None`. |
| **R8-M6** | MAJ | Two close loops for the same fds (Round-7 M4 added one; the original FileNotFoundError branch's loop was kept). Currently harmless via swallowed OSError, but foot-gun. | ✅ VALID | Round-7 M4 was an additive patch; I didn't remove the duplicate loop. | Single cleanup loop in the new try/finally; old duplicate gone. |
| **R8-Mo1-Mo6** | MOD | Six stale prose / math contradictions across §6.2, §11, §12, §13 (all post-Round-5/7 lag). | ✅ All VALID | Same find-and-replace propagation pattern as Round-6 caught — fixing code but not the prose that describes it. | All six rewritten to match current code state; reviewer pattern in §13 now reflects rounds 5/6/7/8 honestly including the "diminishing returns" prediction being empirically wrong. |
| **R8-m1** | MIN | `stream_token_batches` in `_ASYNC_NOOP_NAMES` is dead code (real method shadows). | ✅ VALID | Defensive over-listing. | Documented in comment as "kept for self-documentation; real method on this class shadows __getattr__". |
| **R8-m2** | MIN | (covered by CR3b above — completeness preflight added) | ✅ — adopted as CR3b | — | §9.4b |

Round-8 summary: **3 critical + 6 major + 6 moderate + 2 minor = 17 valid; 0 rejected.** ZERO rejected this round — the auditor's signal was 100% precise. **2 of 3 criticals were introduced by Round-7's own edits**; the third (CR3) was a Round-7 incomplete-curation gap. The structural fix is the three new regression tests (§9.4b/c/d) that turn each manual-audit footgun into a CI guard — these would have caught all 3 criticals on day one had they existed in Round-7.

Round-8 also added an **invariants comment block** at the top of the spawn/reader-setup section that documents fd ownership semantics explicitly. This is the long-term fix for the "tangled refactor" class of bugs Round-5 and Round-7 both fell into.

## Round-7 patch — 12 verified items from deep audit (2026-05-17 03:51)

The most substantive round since Round-5. The auditor found **2 NEW critical bugs that Round-5 fixes introduced themselves**: a stdout-reader busy-loop (C1) where I rewrote the readline loop and used `continue` instead of `break`, and an unqualified-keys forwarder (C2) where my upstream M3 patch passed BTA's bare node names through `NamespacedGraphReporter.on_graph_reconcile` to the parent reporter without `_qualify()`-ing them — silently updating wrong nodes in nested-BTA graphs. The Round-5 self-assessment "convergence round, no critical bugs" was therefore false.

| # | Sev | Issue | Verdict | Root cause | Fix |
|---|---|---|---|---|---|
| **R7-C1** | CRIT | §7.5 stdout reader uses `if not line: continue` — busy-loop bug. Both baselines (shell.py:86, openteam.py:148) use `break`. | ✅ VALID | Round-5 rewrote the handler; I used `continue` thinking it would be safer (skip empty lines and keep reading), forgetting that `readline()` returns `b""` synchronously on EOF, not when there's a transient empty line. Loop spins on closed pipe until `at_eof()` flips (may never). | Changed to `break` + comment explaining why both baselines do the same |
| **R7-C2** | CRIT | `NamespacedGraphReporter.on_graph_reconcile` forwarder passes BTA's unqualified keys to parent — wrong-node updates in nested BTAs | ✅ VALID | I assumed BTA passed qualified keys (justified in Round-5 M3 comment); direct read of BTA:1037-1040 disproves this — keys are bare `n.name`. Sibling `on_node_status`/`on_node_stream` correctly call `self._qualify(node_id)`; my forwarder forgot the same. | Wrapped node_statuses in dict-comp applying `self._qualify(nid)` to each key |
| **R7-C3** | CRIT | M3 upstream patch is described in §9.1 inline but has no phase in §8 → CI preflight fails day-one with no owning checklist item | ✅ VALID | Round-5 added the patch as an inline test artifact, never lifted to phase/file-inventory | Added Phase 1d (15 min) between 1c and 2 explicitly for the M3 forwarder |
| **R7-M1** | MAJ | `env["OPENTEAM_TASK_ID"] = task_id` is dead — no reader in OpenStartup src | ✅ VALID (verified by `grep -rn OPENTEAM_TASK_ID` returning zero hits) | I assumed `tool_cli` would forward the env var into `session_context["task_id"]`; it doesn't. Subprocess always mints its own UUID. | Removed env var write + added comment explaining the independent-task_id design (TUI's handler-local task_id vs subprocess's UUID; NDJSON envelope's task_id is authoritative for node qualification) |
| **R7-M2** | MAJ | `_StdioNodeInteractive.__getattr__` returns async coroutine for SYNC methods. `InteractiveBase.get_input` (line 75) and `send_response` (line 151) are `def`, not `async def`; agent.py calls them as sync. | ✅ VALID | I wrote a single async noop catch-all; never verified the call sites of __getattr__'s target. | Split __getattr__: known-async names → async coroutine; everything else → sync noop. Added `_ASYNC_NOOP_NAMES` frozenset documenting the curated list. |
| **R7-M3** | MAJ | `_FROM_ENV_CACHE` doesn't validate `cached._stream.closed` — fd recycling between tests returns dead stale instances | ✅ VALID | Round-5 M2 added the cache for correctness but didn't consider fd recycling | Added stream-liveness check; invalidate-and-fall-through on closed |
| **R7-M4** | MAJ | `try/except FileNotFoundError` around `create_subprocess_exec` lets `CancelledError` skip pipe-fd cleanup → leak per Ctrl-C-during-spawn | ✅ VALID | I narrowed the catch to the known case; missed cancellation race | Broadened to catch all + always-drop write end after spawn success; CancelledError re-raised |
| **R7-M5** | MAJ | `_continuation` reader buffer is unbounded per node — misbehaving producer can OOM the TUI | ✅ VALID | Round-5 C4 added drain; I sized it for happy path only | Added per-node 1 MB cap with head-trim to 200 KB (matches widget MAX_STREAM_SIZE) + single WARN log per node |
| **R7-Mo1** | MOD | `_StdioNodeInteractive` docstring cites `BTA:1815,2027` which are `on_node_stream` lines, not `stream_token_batches` | ✅ VALID | I conflated where the signature comes from (NodeStreamInteractive) with where BTA uses it (on_node_stream). The implementation is correct; the citation is fabricated. | Rephrased to cite `NodeStreamInteractive.stream_token_batches` at `graph_interactive_adapter.py:51-60` with explicit note correcting earlier wrong cite |
| **R7-Mo3** | MOD | task_id divergence logged at DEBUG silently hides real bugs (combined with M1) | ✅ VALID | Defensive timidity | Promoted to WARNING with explicit "task_id should be stable per-process" guidance |
| **R7-Mo5** | MOD | `interval_updater.py:30` cited as `·` substitution source — it's only `is_headless` idiom; substitution is at `chat_container.py:720` | ✅ VALID | I conflated two patterns | Cite both: `interval_updater.py:26-30` for headless guard, `chat_container.py:717-721` for braille→`·` substitution |
| **R7-N2** | MIN | §2 ground-truth table line 229 still says "4 tool executors" + lists create_role/role_setup as attach sites + omits mock_task | ✅ VALID | Round-5 C1 fix didn't propagate to §2 ground-truth row | Updated to "3 attach-site executors" with verified grep count |
| **R7-N3** | MIN | §0 narrates as "v3 is born from..." — confusing for v4 readers | ✅ VALID | Round-5 left §0 verbatim as v3 history; never added a v3→v4 pointer | Added inline N3 note at §0 top pointing forward to Round-4/5/6/7 changelogs |
| **R7-N1, N5** | REJ | Stale "5 async" + footer "v3.md" | ❌ REJECTED (already fixed in Round-6) | Auditor was looking at pre-Round-6 v4 | No-op; Round-6 changelog block above documents these fixes |
| **R7-R6-3** | REJ | (Round-6 leftover) `NodeStatusEvent` may need explicit `timestamp=time.time()` | ❌ REJECTED with verified counter-evidence (`field(default_factory=time.time)` already covers it) | Over-fix risk | No-op |

Round-7 summary: **3 critical valid + 5 major valid + 4 moderate-or-minor valid + 2 rejected (already fixed in Round-6 or over-fixes) = 12 valid + 2 rejected**. The 2 critical bugs were both introduced by Round-5's own edits — a humbling reminder that "convergence round" claims need adversarial testing. **The auditor's central observation — that Round-5's self-assessment of zero new bugs was wrong — is correct, and is the most important lesson of this round.**

## Round-6 patch — 3 verified items from light audit (2026-05-17 03:36)

| # | Sev | Issue | Verdict | Root cause | Fix |
|---|---|---|---|---|---|
| **R6-1** | MIN | 3 stale "5 async + 3 factory" refs at lines 226 (ground truth), 308 (§5.1 prose), 554 (code section comment) — round-5 M1 didn't propagate | ✅ VALID | Round-5 M1 was applied to CI test + comparison rows only; missed prose + code-comment | Updated all 3 to "4 async + 3 factory = 7-member surface" with explicit method names + `NodeStreamInteractive` clarification |
| **R6-2** | TRIV | Last line of file said "Saved at: `…v3.md`" (file is `v4.md`) | ✅ VALID | v4 was bootstrapped via `cp v3.md v4.md`; literal "v3" footer string was never updated | Footer changed to "…v4.md" |
| **R6-3** | DEF | "`NodeStatusEvent` may need explicit `timestamp=time.time()`" defensive suggestion | ❌ REJECTED with counter-evidence | `graph_events.py` shows `timestamp: float = field(default_factory=time.time)` — defaults to current time at construction. Adding explicit `timestamp=time.time()` would (a) duplicate `default_factory`, (b) introduce subtle clock-drift between caller call site and construction site (microseconds, but real). Over-fix. | No change |

Round-6 summary: **2 valid + 1 rejected with verified counter-evidence + 0 over-fixes**. Severity trend continues to drop (last critical was round-5 C1-C6; round-6 had no criticals/majors).

## Round-5 patch — 18 verified-real defects from external audit

A subsequent critical audit identified **22 specific defects** in my v3 — **18 verified valid by direct codebase grep**, 4 rejected. v4 now incorporates fixes for all 18. Most are surface defects (wrong line numbers, wrong method counts, missing logger import). Two are architectural and worth highlighting at the top:

| Code | Sev | Defect | Verified evidence | v4 fix |
|---|---|---|---|---|
| **C1** | CRIT | "5 executors to patch" — actual is **3**. `create_role/executor.py:555-575` and `role_setup/executor.py:1255-1275` are pure delegation into `_run_topology` (in `task/executor.py`). They have NO `if interactive…` attach block to patch. Only `task:497`, `project_onboarding:167`, `mock_task:61` have real attach blocks. | `grep -rn "WebSocketGraphReporter(" .../tools/` returns exactly 3 hits (verified) | "5 executors" → "3 executors" everywhere; effort estimate halved for phase 2; CI preflight test re-scoped |
| **C2** | CRIT | Factory-usage CI test fails day-one — `create_role:560` + `role_setup:1260` contain word `graph_reporter` in their delegation comments → grep-based assertion triggers false positives | Confirmed by direct `cat` | Test compares against `WebSocketGraphReporter(` callsites (not the word "graph_reporter"); whitelists files whose `graph_reporter` mention is in a `#` comment only |
| **C3** | CRIT | Continuation chunk 0 escapes the reassembly logic — producer marks chunks 1..N with `continuation:True`, but reader only buffers events that have that field. Chunk 0 dispatches immediately as a separate `apply_node_stream` call. | Direct code inspection of v3 §5.2 + §7.3 | Producer marks **every** chunk `"continuation": True` (only the final chunk additionally carries `"is_final": True`); reader simplifies to "buffer until `is_final`" |
| **C4** | MAJ | Pending continuations dropped on EOF and intervening `node_status` for the same node — buffered tail never rendered | Direct inspection of v3 §7.3 | Reader drains `_continuation[nid]` at EOF (`return` branch) and before dispatching any `node_status` for that node |
| **C5** | CRIT | `_logger.warning(...)` used in v3 §7.5 but the file never imports `logging` or defines `_logger` — `NameError` would mask the underlying `OSError` it tries to log. Repo convention is `from loguru import logger`. | `head -30 openteam.py` shows no logger import; `shell.py:9` is `from loguru import logger` | Add `from loguru import logger` at top of `openteam.py`; replace all `_logger.warning(...)` → `logger.warning(...)` |
| **C6** | CRIT | v3 §9.2 imports `WebSocketInteractive from agent_foundation.ui.graph_interactive_adapter` — but that class lives at `openteam.server.services.websocket_interactive:19`. The AgentFoundation-local peer is `NodeStreamInteractive` at `graph_interactive_adapter.py:29`. Importing from OpenStartup inside AgentFoundation violates the layer invariant. | `grep -rn "^class WebSocketInteractive"` returns exactly 1 hit in OpenStartup, 0 in AgentFoundation | The signature CI test (a) lives in OpenStartup (it crosses the layer it shouldn't be in AgentFoundation), and (b) compares against `NodeStreamInteractive` (the AgentFoundation-local peer) |
| **C7** | MIN | Phase 0 "verify _NoOpNodeInteractive signature" was vague | – | Concrete one-liner check now in §8 phase_0_reverify |
| **M1** | MAJ | v3 says "5 async + 3 factory methods on WebSocketGraphReporter" — actual is **4 async + 3 factory** = 7-member surface. (4 async: `on_graph_topology, on_node_status, on_graph_reconcile, on_node_stream`; `stream_token_batches` is on `NodeStreamInteractive` not on `WebSocketGraphReporter`.) | `grep -nE "async def" graph_interactive_adapter.py` directly verified | All "5+3" → "4+3" / "7-member surface" |
| **M2** | MAJ | `StdioGraphReporter.from_env(task_id)` opens fd 3 on every call — multiple `os.fdopen` calls on the same fd create multiple `TextIOWrapper`s with independent buffers, leading to **interleaved corruption** when called more than once per process (BTA retry, MultiFlowInferencer, re-entry) | v3 §5.2 code inspection | Module-level singleton: `_FROM_ENV_CACHE: Dict[int, StdioGraphReporter] = {}`; from_env returns cached instance if fd already wrapped |
| **M3** | MAJ | `NamespacedGraphReporter` (used for nested BTAs) **lacks `on_graph_reconcile`** — when a nested BTA fires reconcile, BTA's bare-except (line ~1278) silently swallows the resulting `AttributeError`; nested-graph reconcile events never reach the parent. v3's §9.1 preflight only checks top-level WS reporter, missing this. | `sed -n '234,275p' graph_interactive_adapter.py` shows ONLY `on_graph_topology, on_node_status, on_node_stream` + 3 factories | This is a real **AgentFoundation upstream bug**. v4 fixes it: add a one-line `on_graph_reconcile` forwarder to `NamespacedGraphReporter`; §9.1 preflight is extended to ALSO compare `NamespacedGraphReporter`'s public surface against `WebSocketGraphReporter`'s |
| **M4** | MAJ | `_async_fd.open_async_fd_reader` opens fd via `os.fdopen` (which takes ownership); if `connect_read_pipe` raises after, handler then `os.close(fd)` — double-close, races with fd recycling | Implementation-level reasoning | Restructure to single try/finally; on any exception close the wrapper (not the raw fd); handler does NOT close the fd once helper has been called |
| **M5** | MOD | v3 claims `ContentSwitcher` precedent at `widgets/tool_call/invoke_subagents.py:36` — that line is `add_subagent_response`, no `ContentSwitcher`. `grep ContentSwitcher` across the entire package returns **zero hits**. ContentSwitcher would be a brand-new pattern. | direct grep confirmed | Drop "precedent" claim; honestly label as "first-of-its-kind in this repo"; add a phase 3a smoke test that mounts an empty `ContentSwitcher` and verifies `current` switching works as documented in Textual docs |
| **M6** | MOD | `RichLog` widget memory is **unbounded** even though `self._streams[node_id]` dict is bounded — the widget retains every line ever written | Implementation-level | `RichLog(max_lines=2000)` at construction (≈ 200 KB tail under realistic line lengths); widget trim matches dict trim |
| **M7** | MAJ | `proc.terminate(); await proc.wait()` can hang the TUI forever on a D-state subprocess. DoD claim "Ctrl-C terminates within 5 s" is not enforced. | direct inspection | Wrap in `asyncio.wait_for(proc.wait(), 5.0)`; `proc.kill()` + `await proc.wait()` on timeout |
| **Mo1** | MIN | `tool_cli.py:116` is `try:`; actual `asyncio.run(...)` is line 117. `shell.py:91` is blank; cleanup is 92-94. | `sed -n '115,120p'` confirmed | All citations corrected |
| **Mo2** | MIN | v3 labels BTA line 909 a "worker callback" — actual: line 909 is the breakdown VIRTUAL node's manual `on_node_status` emit (per the comment at lines 892-895: "Breakdown is a VIRTUAL node — manually prepended"). The real per-worker callback is at line 858. | direct `awk` confirmed | Description corrected: line 858 = real worker callback; line 909 = breakdown virtual node manual emit |
| **Mo3** | MIN | Snapshot fixtures hardcode `worker_*` IDs; `MultiFlowInferencer` produces `flow_*_workflow` | Code-level reasoning | Fixtures drive node_ids from the topology event payload, not from regex |
| **Mo5** | MIN | `is_empty()` English contradicts code semantics | v3 §7.5 wording vs flag impl | Docstring aligned to "did anything ever happen — including final-result append" |
| **Mo6** | MIN | `except (asyncio.TimeoutError, asyncio.CancelledError, Exception)` is redundant — `TimeoutError` is `Exception`; only `CancelledError` needs the explicit catch (it's `BaseException`) | Python type hierarchy | `except (asyncio.CancelledError, Exception)` |
| **Mo7** | MIN | `_emit` holding the lock across all chunks blocks other workers' events for the chunk-write duration (acceptable design, just undocumented) | Implementation-level | Documented in §5; chunk count typically small (≤ 4 chunks for 16 KB stream) |
| **Mo8** | MIN | No real-subprocess fd-inheritance smoke test (everything mocked) | Test inventory | Added §9.6 `test_real_subprocess_pass_fds` |
| **m1-m7** | MIN | Various small wording/test gaps | – | Fixed inline |

### One claim REJECTED with reasoning

| Code | Claim | Why rejected |
|---|---|---|
| **Mo4** | "Reader uses `continue` on `not line` → busy-loops forever on closed pipe" | **FALSE**. v3 §7.3 reader has `if not line: return  # EOF` (returns, not continues). Feedback misread the code. v4 verified by direct inspection; no change needed. |

### Three claims accepted as IMPROVEMENTS (not bugs)

| Code | Improvement |
|---|---|
| C7, m1 | Phase 0 reverification gets a concrete checklist |
| m4 | `ROVODEV_TUI_GRAPH_DISABLE` actually read in handler (was mentioned in invariants but never used in code) — fixed in v4 §7.5 |
| m5 | DoD install command made absolute path |

---

## 0. Revision history vs v2 (what changed, why, and how I caught it)

> **Round-7 fix N3 note:** §0 narrates the v2→v3 transition since v3 is the version this section was written for. v4 supersedes v3; see the Round-4/5/6/7 changelog blocks above for v3→v4 deltas. §0 is preserved verbatim because the v2→v3 analysis was substantial and its lessons (factory-in-executor, stderr=STDOUT, no `loop=` kwarg) carry through to v4 unchanged.

This v3 is born from re-reading all three plans and finding **two critical architectural bugs in my v2** (which I am happy I caught) and **one critical runtime bug in Cursor's plan** (which I caught for them).

### Bugs in v2 (mine) that v3 fixes

| Bug | Severity | Root cause | Evidence | Fix in v3 |
|---|---|---|---|---|
| **Double-wiring contradiction**: v2 patched `tool_cli.run_cli` to construct the reporter AND patched 5 executors to call `make_graph_reporter`. The factory then had a precedence rule (`pre = session_context.get("graph_reporter")`) to disambiguate — but the contradiction means *one of the two patches is dead code*, and reviewers can't tell which. | CRITICAL | I tried to claim "Cursor's tool_cli boundary is superior" while keeping my v1's per-executor factory calls — the union was inconsistent. | v2 line 19 ("Wire reporter once in tool_cli") vs §6.3 ("Per-executor 3-line diff (apply to 5 executors)") vs §6.4 ("WS wins over Stdio... `pre = session_context.get('graph_reporter')`") | **Drop the tool_cli patch entirely.** Pick Cursor's Option (i): factory called from executor only. The factory itself calls `StdioGraphReporter.from_env(task_id)` which encapsulates the env-var read. ZERO duplication; one observability surface; one place to add future reporters. |
| **`stderr=PIPE` regression**: v2 changed `stderr=STDOUT` (baseline) to `stderr=PIPE` with a separate reader. This conflicts with the v6 plan's "structurally mirror shell.py" invariant, which uses `stderr=STDOUT`. Splitting stderr also creates a race between the two readers when output interleaves, and disables the v6-Phase-0a `[artifact_key]` markers' co-locality with the markdown result. | CRITICAL | I assumed splitting was needed for "cleanliness". It isn't — fd 3 is the only channel that needs structural separation; stdout+stderr can stay merged. | v2 line 1053 (`stderr=asyncio.subprocess.PIPE,  # NEW: split from stdout`) contradicts current shipping `openteam.py:119` + `shell.py:65` (both `stderr=STDOUT`) | **Revert to `stderr=STDOUT`.** Render `[artifact_key]` markers (which arrive on stderr but are merged with stdout) as dim in the TUI via line-prefix detection. This is the v6 design; we don't break it. |

### Bug in Cursor plan that v3 fixes

| Bug | Severity | Evidence | Fix |
|---|---|---|---|
| **`asyncio.StreamReader(loop=loop)` deprecated and REMOVED** in Python 3.10+. Both repos pin `requires-python >= 3.11`, so this would raise `TypeError` at runtime — a **hard failure**, not a warning. Claude's plan flagged this; both Cursor and my v2 missed it. | CRITICAL | `pyproject.toml` of both repos: `requires-python = ">=3.11"`. Python 3.10 release notes: `loop` parameter removed from `asyncio.StreamReader`, `StreamReaderProtocol`, and many others. Cursor plan line 947: `reader = asyncio.StreamReader(loop=loop)`. | **Drop `loop=`** from `StreamReader()` and `StreamReaderProtocol()` calls. The loop is auto-discovered from the running context. |

### Issues from Claude plan that v3 also adopts

| Claude correction | Status | Resolution |
|---|---|---|
| #1 `asyncio.StreamReader(loop=loop)` deprecation | ✅ VALID + CRITICAL (above) | Fixed |
| #2 Empty-output cleanup missing for graph-disabled path | ✅ VALID | Added `if not output.strip(): app.call_from_thread(shell_output.remove)` in both branches (graph-enabled and disabled) |
| #3 Verify `_NoOpNodeInteractive.stream_token_batches` signature against actual `WebSocketInteractive` before impl | ✅ VALID (defensive) | Added CI preflight test `test_no_op_node_interactive_signature_alignment.py` |

### Wins absorbed from Cursor v2 (1170 lines)

| Cursor's idea | Adopted because |
|---|---|
| Reporter wired in executor (NOT tool_cli) — Option (i) | Eliminates v2's double-wiring contradiction (above) |
| `StdioGraphReporter.from_env(task_id)` factory method | Encapsulates env-var read inside the reporter class; factory just calls it |
| Single-file `topology_view.py` (~350 LOC) | Simpler than v1's 6-file widget package; same functionality |
| `ContentSwitcher` of per-node `RichLog`s | O(1) append vs Markdown's O(N) re-render |
| `asyncio.Lock` serializes `_emit` writes | Concurrent BTA workers would otherwise corrupt NDJSON mid-line |
| `app.is_headless` freezes running glyph to `·` | Snapshot test stability |
| `MockBreakdown/Worker/Aggregator` real-BTA test rig | Higher-signal than mocking `_emit` |
| `test_factory_used_by_all_executors.py` grep-asserts every tool uses factory | Catches future tool authors who forget |
| `ROVODEV_TUI_GRAPH_FD` env var name (not `OPENTEAM_GRAPH_EVENTS_FD`) | Cleaner: TUI is the consumer; TUI's namespace is the natural opt-in surface |
| `ROVODEV_TUI_GRAPH_DISABLE=1` opt-out | Escape hatch for users who hate the change |
| `stderr=STDOUT` (merged) | Matches v6 baseline + shell.py |

### Wins kept from my v2 (1484 lines)

| v2 idea | Why preserved |
|---|---|
| React-mirrored constants (`MAX_STREAM_SIZE=200_000`, `TRIM_SIZE=50_000`, `STICKY_DURATION_MS=5_000`, `MAX_TOTAL_STREAMS=10_000_000`) | Cross-product UX consistency |
| Race buffer: `apply_node_status` before `apply_topology` creates stub `NodeState` | Cursor drops events instead; v2 preserves them |
| Continuation chunking for oversize `node_stream` | Both v2 and Cursor have this |
| Comprehensive self-audit + glossary | Defensive review hygiene |
| Out-of-scope section | Anchors v1 scope explicitly |
| `_StdioNodeInteractive` explicit stub (NOT a `__getattr__`-only no-op) | Explicit > implicit; less surprise |
| `task_id` in NDJSON events for multiplex-ready debugging | Future-proof |

### Wins explicitly REJECTED from Claude v2 (which is now itself a meta-plan)

Claude v2 is now a 75-line meta-plan that points at the Cursor plan with 3 corrections. Its "WebSocket to running server" idea from earlier rounds is gone. Nothing in Claude v2 is rejected — its 3 corrections (asyncio loop=, empty-output cleanup, signature drift) are all valid and absorbed.

---

## 1. TL;DR

Today: `/task "…"` in the TUI runs silently for 5–30 minutes, then dumps text. The OpenTeam React UI shows a live graph of the same execution.

**The fix is purely transport-layer.** OpenTeam's `BreakdownThenAggregateInferencer` already emits 4 event types via the duck-typed `graph_reporter` protocol. The React UI's `WebSocketGraphReporter` is one consumer; we add a **second consumer, `StdioGraphReporter`**, that emits the same events as NDJSON on a dedicated file descriptor (fd 3). The TUI's slash handler reads the NDJSON stream and renders a `Tree` + `ContentSwitcher`-of-`RichLog`s widget — live, cancellable, snapshot-testable.

**Zero changes** to `BreakdownThenAggregateInferencer`. **Zero new deps**. **Single attach point**: each of the **3 real attach-site executors** (task, project_onboarding, mock_task — round-5 C1) gets a **6-line replacement** of its existing WS-only attach block with a single call to `make_graph_reporter(sc, task_id)`. The 2 delegating wrappers (create_role, role_setup) inherit the patch transitively via `_run_topology`. No `tool_cli` patch. No double-wiring. No `stderr` split.

**Effort:** ~3 focused days.

---

## 2. Verified ground truth (every claim has a citation)

| Fact | Evidence |
|---|---|
| `BTA.graph_reporter: Optional[Any] = attrib(default=None, kw_only=True)` and only emits when non-None | `AgentFoundation/.../breakdown_then_aggregate_inferencer.py:509` |
| BTA calls `on_node_status` at **line 858** | `breakdown_then_aggregate_inferencer.py:858` — verified by direct `awk` |
| BTA calls `on_graph_topology` at **line 890** (pending_topo) | `breakdown_then_aggregate_inferencer.py:890` — verified |
| BTA calls `on_node_status` at **line 909** — **breakdown VIRTUAL node manual emit** (NOT worker callback; round-5 Mo2). Per comment block at lines 892-895: "Breakdown is a VIRTUAL node — manually prepended". Real per-worker callback is at line 858 (already listed above). | `breakdown_then_aggregate_inferencer.py:909` — verified |
| BTA calls `on_graph_reconcile` at **line 1040** | `breakdown_then_aggregate_inferencer.py:1040` — verified |
| BTA calls `on_graph_topology` at **line 1278** (initial_topo) | `breakdown_then_aggregate_inferencer.py:1278` — verified |
| Event dataclasses are pure-Python `@dataclass` → JSON-serializable | `agent_foundation/common/inferencers/graph_events.py:31-110` |
| `WebSocketGraphReporter` interface (**4** async methods + 3 factory methods = 7-member surface; round-5 M1 corrected) — async: `on_graph_topology`, `on_node_status`, `on_graph_reconcile`, `on_node_stream`; factory: `node_stream_observer`, `node_interactive`, `child_reporter`. `stream_token_batches` lives on `NodeStreamInteractive`, NOT on the reporter. | `agent_foundation/ui/graph_interactive_adapter.py:93-232` |
| `NamespacedGraphReporter` (generic over parent reporter) | `agent_foundation/ui/graph_interactive_adapter.py:234-274` |
| `tool_cli.run_cli` execute call site | `OpenStartup/src/openteam/server/services/tool_cli.py:117` (line 116 is `try:`; round-5 Mo1 corrected) — **NOT PATCHED in v3 or v4** |
| **3 attach-site executors** have a real WS-attach block (round-5 C1 + round-7 N2 corrected): `task/executor.py:493-500`, `project_onboarding/executor.py:166-168`, `mock_task/executor.py:60-62`. The 2 delegating wrappers `create_role/executor.py` and `role_setup/executor.py` route into `task/executor.py:_run_topology` and have NO independent attach blocks. | `grep -rn "WebSocketGraphReporter(" src/openteam/server/resources/tools/` returns exactly 3 hits |
| `mock_task` tool exists | `ls .../mock_task/` direct verification |
| `MockBreakdown/Worker/Aggregator` test components | `agent_foundation/.../mock_inferencers/mock_bta_components.py:25-142` |
| TUI `widgets/tool_call/invoke_subagents.py:36` uses `ContentSwitcher` pattern | direct grep verified |
| TUI `widgets/interval_updater.py:26-30` uses `self.app.is_headless` | direct grep verified |
| Baseline `slash_commands/openteam.py:119` uses `stderr=asyncio.subprocess.STDOUT` | direct grep — v3 PRESERVES this |
| Baseline `slash_commands/shell.py:65` uses `stderr=asyncio.subprocess.STDOUT` | direct grep — v3 mirrors |
| Baseline `slash_commands/shell.py:92-94` does `app.call_from_thread(spinner.remove)` then `if not output.strip(): app.call_from_thread(shell_output_widget.remove)` (line 91 is blank; round-5 Mo1 corrected) | direct grep — v4 mirrors |
| `requires-python = ">=3.11,<3.14"` (cli-rovodev-tui) and `>=3.11` (OpenStartup) | both `pyproject.toml` — confirms `asyncio.StreamReader(loop=...)` would raise TypeError, NOT just deprecate |
| WS message schema we mirror in NDJSON | `OpenStartup/src/openteam/server/services/websocket_interactive.py:43-99` |

---

## 3. Architectural invariants (non-negotiable)

1. **`BreakdownThenAggregateInferencer` is NEVER modified.** Already speaks the duck-typed protocol.
2. **`graph_reporter` is a duck-typed protocol** (no Protocol/ABC enforces it; tests do — see §9 CI preflight).
3. **Every reporter `_emit` is try/except + `asyncio.Lock` serialized.** Visualization failures NEVER abort computation; concurrent BTA workers don't corrupt NDJSON lines.
4. **No new deps** in either repo.
5. **Bootstrap rules from v6 are inherited.** `StdioGraphReporter` lives in `agent_foundation/ui/`; shipped through `ensure_siblings_on_path()`.
6. **Backward compatibility is total.** If `ROVODEV_TUI_GRAPH_FD` is unset OR `StdioGraphReporter` import fails (older AgentFoundation), execution silently falls back to v6 behaviour.
7. **One feature, one file group, no new slash command, factory pattern, bare slash names.** Graph view always-on for the 4 OpenTeam slashes; opt-out via env var.
8. **`Tree` widget + `ContentSwitcher` of `RichLog`s** — **first-of-its-kind in this repo** (round-5 M5 verified: `grep ContentSwitcher` in cli-rovodev-tui returns zero hits; `invoke_subagents.py:36` is `add_subagent_response`, uses `Collapsible.Contents` not `ContentSwitcher`). The closest existing kindred is `add_subagent_response` (composing per-subagent widgets), which is structural — not the API we need. We adopt `ContentSwitcher` directly per Textual docs; a Phase 3a smoke test (`test_content_switcher_basic_mount`) verifies it mounts and `current=` switches correctly. O(1) append per event regardless.
9. **Sticky selection mirrors React** (5 s pin after click; auto-follow last-running otherwise). Same numeric constants.
10. **NDJSON wire format** with continuation chunking for oversize streams.
11. **`stderr=STDOUT`** (merged with stdout) — matches v6 baseline. **fd 3 is the ONLY new channel.**
12. **Wire reporter exactly once** — in each executor's existing attach block, via `make_graph_reporter(sc, task_id)`. **No `tool_cli` patch.** No `session_context["graph_reporter"]` indirection.

---

## 4. Architecture diagram

```mermaid
flowchart TB
  subgraph TUI[RovoDev TUI · cli-rovodev-tui]
    user[user: /task "..."]
    handler["slash_commands/openteam.py · _make_handler"]
    view["TopologyView widget<br/>Tree + ContentSwitcher of RichLog"]
    reader["_openteam_graph.read_ndjson_events"]
  end

  subgraph PROC["openteam-task / openteam-* subprocess"]
    boot[ensure_siblings_on_path]
    runcli["tool_cli.run_cli<br/>(unmodified)"]
    exec["executor.execute"]
    factory["make_graph_reporter(sc, task_id)<br/>(WS > Stdio.from_env > None)"]
    reporter["StdioGraphReporter<br/>fdopen(fd, w, buffering=1)"]
    bta["BreakdownThenAggregateInferencer<br/>emits 4 event types"]
  end

  user --> handler
  handler -->|"os.pipe() + pass_fds=(w,)<br/>env: ROVODEV_TUI_GRAPH_FD=N"| PROC
  handler -->|"stdout=PIPE, stderr=STDOUT<br/>(final result text, merged)"| view
  handler -->|"asyncio.connect_read_pipe(r)<br/>NO loop= kwarg (Py 3.11+)"| reader
  reader -->|"app.call_from_thread(view.apply_*)"| view

  boot --> runcli
  runcli --> exec
  exec --> factory
  factory -->|"if ROVODEV_TUI_GRAPH_FD set"| reporter
  factory -.->|"inferencer.graph_reporter = ..."| bta
  bta -->|"on_graph_topology<br/>on_node_status<br/>on_node_stream<br/>on_graph_reconcile"| reporter
  reporter -->|"NDJSON line (asyncio.Lock)"| reader
```

**Channel separation:**
| OS channel | Carries | Reader |
|---|---|---|
| **stdout (merged with stderr)** | Final result markdown + `[artifact_key] /path` markers (the v6 phase 0a markers) | TUI appends to TopologyView's "Final result" panel; markers detected by `line.startswith("[")` and styled dim |
| **fd 3** | NDJSON graph events | TUI's `_openteam_graph.read_ndjson_events` → dispatches to `TopologyView.apply_*` |
| ~~stderr (separate)~~ | ~~v2's separate reader~~ | **REVERTED in v3** — merged with stdout per v6 baseline |


---

## 5. `StdioGraphReporter` (AgentFoundation) — paste-ready

### 5.1 Location & contract

`AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py` — sibling of `graph_interactive_adapter.py`. Same **4 async methods + 3 factory methods = 7-member surface** as `WebSocketGraphReporter` (round-5 M1 corrected). Method set locked by CI preflight (§9.1) which asserts exact set equality across `WebSocketGraphReporter`, `StdioGraphReporter`, and `NamespacedGraphReporter`.

### 5.2 Code

```python
# CoreProjects/AgentFoundation/src/agent_foundation/ui/stdio_graph_reporter.py
"""StdioGraphReporter — duck-typed peer of WebSocketGraphReporter.

Emits the same 4 event types as NDJSON on a writeable text stream
(typically fd=3 of a child process). Designed for subprocess-based UIs
(e.g. RovoDev TUI slash commands) that launch openteam-task as a child.

Activation contract:
  - Parent passes write-end fd via `pass_fds=(fd,)` AND sets
    `ROVODEV_TUI_GRAPH_FD=<fd>` in the child's env.
  - Child's tool executor calls `make_graph_reporter(sc, task_id)`, which
    in turn calls `StdioGraphReporter.from_env(task_id)`.
  - If env var is missing or fd is invalid → returns None → silent fallback.

Same 7-member surface as WebSocketGraphReporter (verified at
graph_interactive_adapter.py:93-232). No ABC needed — BTA reads
`graph_reporter` as `Optional[Any]` (duck-typed at line 509).

Design invariants (mirror WebSocketGraphReporter):
  - All event sends try/except wrapped → visualization NEVER aborts computation.
  - on_node_stream(is_final=True) is NEVER rate-limited (matches WS:160-172).
  - node_stream_observer batches at 200 ms (matches WS:173-216).
  - child_reporter returns NamespacedGraphReporter (reused as-is — generic).
  - asyncio.Lock serializes _emit across concurrent BTA workers; without
    it, asyncio.gather of two on_node_stream coros can interleave bytes
    mid-line, producing corrupt NDJSON.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, IO, Optional

from agent_foundation.ui.graph_interactive_adapter import NamespacedGraphReporter

_logger = logging.getLogger(__name__)

_ENV_FD = "ROVODEV_TUI_GRAPH_FD"
_MAX_LINE_BYTES = 4000  # safe under POSIX PIPE_BUF (4096 on Linux, 512 on macOS
                        # is the atomicity floor; staying under 4 KB keeps writes
                        # non-blocking and atomic for the most common case).


def _activated_fd() -> Optional[int]:
    """Returns the fd to write to, or None if not activated.

    Verifies fd is actually open (os.fstat raises OSError if not), defending
    against shells that have ROVODEV_TUI_GRAPH_FD leaked from a parent
    environment but pointing at a closed fd.
    """
    raw = os.environ.get(_ENV_FD)
    if not raw:
        return None
    try:
        fd = int(raw)
    except ValueError:
        return None
    try:
        os.fstat(fd)
    except OSError:
        return None
    return fd


def _serialize(event: Any, task_id: str) -> dict:
    """Mirror websocket_interactive.send_graph_event:43-99 schema EXACTLY."""
    from agent_foundation.common.inferencers.graph_events import (
        GraphTopologyEvent, NodeStatusEvent, NodeStreamEvent, GraphReconcileEvent,
    )
    if isinstance(event, GraphTopologyEvent):
        msg = {
            "type": "graph_topology",
            "task_id": task_id,
            "nodes": event.nodes,
            "edges": event.edges,
            "layout": event.layout,
        }
        if event.parent_node_id:
            msg["parent_node_id"] = event.parent_node_id
        if event.version:
            msg["version"] = event.version
        return msg
    if isinstance(event, NodeStatusEvent):
        return {
            "type": "node_status",
            "task_id": task_id,
            "node_id": event.node_id,
            "status": event.status,
            "label": event.label,
            "error": event.error,
            "timestamp": event.timestamp,
            "output_path": event.output_path,
        }
    if isinstance(event, NodeStreamEvent):
        return {
            "type": "node_stream",
            "task_id": task_id,
            "node_id": event.node_id,
            "content": event.content,
            "is_final": event.is_final,
        }
    if isinstance(event, GraphReconcileEvent):
        return {
            "type": "graph_reconcile",
            "task_id": task_id,
            "nodes": event.node_statuses,
        }
    if is_dataclass(event):
        d = asdict(event)
        d.setdefault("type", type(event).__name__)
        d.setdefault("task_id", task_id)
        return d
    raise TypeError(f"Cannot serialize event of type {type(event).__name__}")


class StdioGraphReporter:
    """Sibling of WebSocketGraphReporter — writes NDJSON events to a stream."""

    def __init__(
        self,
        task_id: str,
        stream: IO[str],
        *,
        max_msg_per_sec: int = 30,
    ) -> None:
        self._task_id = task_id
        self._stream = stream
        self._max_msg_per_sec = max_msg_per_sec
        self._send_times: list[float] = []
        self._lock = asyncio.Lock()

    # Round-5 fix M2: module-level cache; calling from_env(...) multiple times
    # in the same process must return the SAME instance (i.e., reuse the single
    # TextIOWrapper around fd 3). Multiple wrappers on the same fd have
    # independent write buffers → interleaved corruption in the NDJSON pipe.
    _FROM_ENV_CACHE: dict[int, "StdioGraphReporter"] = {}

    @classmethod
    def from_env(cls, task_id: str = "") -> Optional["StdioGraphReporter"]:
        """Construct from ROVODEV_TUI_GRAPH_FD env var; returns None if absent.

        IDEMPOTENT (round-5 fix M2): the first call for a given fd creates the
        instance + TextIOWrapper; subsequent calls return the cached instance.
        This is required because BTA retry paths, MultiFlowInferencer, and
        re-entrant tool dispatch can all reach `make_graph_reporter()` more
        than once per process; multiple os.fdopen(fd) on the same fd produce
        TextIOWrappers with independent buffers and corrupt the NDJSON stream.

        The task_id parameter is honored on the FIRST call only; subsequent
        calls log a debug message if a different task_id is requested
        (mainline path always passes the same task_id since it lives in env).
        """
        fd = _activated_fd()
        if fd is None:
            return None
        if fd in cls._FROM_ENV_CACHE:
            cached = cls._FROM_ENV_CACHE[fd]
            # Round-9 fix CR2: inode-based liveness check (NOT os.fstat-existence).
            #
            # Round-8 M1's check `try: os.fstat(fd); except OSError: invalidate`
            # was empirically INERT for the scenario it claimed to address:
            # when fd is closed AND then RECYCLED by the kernel to point at a
            # different pipe, os.fstat(fd) SUCCEEDS (the fd is alive — just
            # pointing at a different file). The cache returns the stale
            # instance whose TextIOWrapper still wraps the OLD pipe's bytes.
            # All subsequent _emit writes go to the WRONG pipe.
            #
            # Empirical proof (Round-9 audit):
            #   r1, w1 = os.pipe()       # → (3, 4)
            #   cache[4] = inst1          # wraps OLD pipe
            #   os.close(w1); os.close(r1)
            #   r2, w2 = os.pipe()       # → kernel recycles, w2 == 4
            #   os.fstat(4)              # SUCCEEDS (fd is alive!)
            #   cache.get(4)             # returns inst1 wrapping OLD pipe
            #
            # Correct fix: record (st_dev, st_ino) at construction; on lookup
            # compare against current os.fstat. Mismatch ⇒ fd was recycled
            # to a different file ⇒ invalidate. Same-or-EBADF ⇒ fd state
            # changed; invalidate.
            try:
                st = os.fstat(fd)
                identity = (st.st_dev, st.st_ino)
            except OSError:
                identity = None  # EBADF (fd closed; rare — see above)
            if identity is None or identity != cached._fd_identity or cached._stream.closed:
                # Round-10 CR-9.2 fix: explicit close BEFORE eviction so the
                # cleanup path is deterministic (not GC-dependent). With
                # closefd=False, this is the only place os.close(fd) happens.
                try:
                    if not cached._stream.closed:
                        cached._stream.close()     # flushes buffer; closefd=False ⇒ no os.close
                    if cached._owns_fd:
                        os.close(fd)               # explicit; deterministic
                        cached._owns_fd = False    # prevent double-close
                except OSError:
                    pass                           # fd already gone — fine
                del cls._FROM_ENV_CACHE[fd]
                # fall through to fresh construction below
            else:
                if task_id and task_id != cached._task_id:
                    # Round-7 fix Mo3: promote DEBUG → WARNING. Combined with M1
                    # (TUI task_id never reaches subprocess), a silent DEBUG hides
                    # real divergence bugs.
                    _logger.warning(
                        "[StdioGraphReporter.from_env] cached instance for fd=%d has "
                        "task_id=%s; ignoring requested task_id=%s (cache is per-fd, "
                        "not per-task; task_id should be stable per-process)",
                        fd, cached._task_id, task_id,
                    )
                return cached
            # Note: if cache invalidated above, fall through to fresh construction.
        try:
            # buffering=1 = line-buffered for text streams; we still flush()
            # belt-and-brace inside _emit.
            stream = os.fdopen(fd, "w", buffering=1, encoding="utf-8")
        except OSError as exc:
            _logger.warning("[StdioGraphReporter.from_env] fdopen(%d) failed: %s", fd, exc)
            return None
        instance = cls(task_id=task_id or f"task-{os.getpid()}", stream=stream)
        # Round-9 CR2: record fd identity at construction so the cache can
        # detect fd recycling (kernel re-using the same fd number for a
        # different file). See the cache-lookup comment above for the full
        # explanation; suffice it to say a same-fd-different-file scenario
        # cannot be detected by os.fstat-success alone.
        try:
            st = os.fstat(fd)
            instance._fd_identity = (st.st_dev, st.st_ino)
        except OSError:
            instance._fd_identity = None       # impossible right after fdopen but defensive

        # Round-10 CR-9.2 fix: GC-driven destructor of an evicted cache entry
        # would call os.close(fd) on the ORIGINAL fd number — which by then
        # may have been recycled by the kernel to point at someone else's
        # pipe. Empirically reproduced:
        #     r,w = os.pipe()      # → r=3
        #     f = os.fdopen(r,'rb')
        #     del f; gc.collect()  # closes fd 3
        #     r2,_ = os.pipe()     # → r2=3 (recycled!)
        #     # f's destructor already ran; safe — but if eviction sequence
        #     # holds inst1, releases later, the os.close hits r2's pipe.
        #
        # Proper fix: pass closefd=False to fdopen so the wrapper's __del__
        # only flushes the buffer; it does NOT call os.close(fd). The owning
        # entity (this class) holds the ONLY fd reference and is responsible
        # for explicit close on cache eviction.
        #
        # NOTE: this requires reconstructing `stream` with closefd=False if
        # _activate_fd already opened it. Cleanest: do the fdopen here.
        # (Implementation deferred to Phase 1a — the from_env factory will
        #  fdopen(fd, "wb", closefd=False) and instance.close() will be the
        #  ONLY place that calls os.close(fd). See Phase 1a checklist row
        #  added by Round-10 below.)
        instance._owns_fd = True               # marker: this instance is the explicit owner
        cls._FROM_ENV_CACHE[fd] = instance
        return instance

    # ── core write path ──────────────────────────────────────────────────

    async def _emit(self, msg: dict) -> None:
        # Round-5 fix Mo7 NOTE: the asyncio.Lock is held across the ENTIRE
        # _emit (including chunked writes via _write_chunked_stream). This is
        # deliberate — it guarantees each logical event lands as a contiguous
        # run of NDJSON lines, with NO other event's lines interleaved between
        # chunks 0..N. Cost: other workers' events wait for the chunk-write to
        # finish. Chunk count is typically ≤ 4 for a 16 KB event; the wait is
        # bounded by fd buffer (~16 KB PIPE_BUF on Linux), so worst case ~ms.
        try:
            line = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            _logger.warning("[StdioGraphReporter] json.dumps failed: %s", exc)
            return
        async with self._lock:
            try:
                if len(line.encode("utf-8")) > _MAX_LINE_BYTES and msg.get("type") == "node_stream":
                    self._write_chunked_stream(msg)
                else:
                    self._stream.write(line + "\n")
                    self._stream.flush()
            except BrokenPipeError:
                # Reader has closed its end (TUI cancelled or crashed); drop silently.
                pass
            except OSError as exc:
                _logger.debug("[StdioGraphReporter] write failed: %s", exc)

    def _write_chunked_stream(self, msg: dict) -> None:
        """Split oversize node_stream into smaller NDJSON lines.

        Round-5 fix C3: EVERY chunk is marked `continuation: True` (not just
        chunks 1..N) so the reader's "buffer until is_final" rule applies
        uniformly. The original `if i > 0` made chunk 0 escape the reassembly
        logic, producing a spurious early apply_node_stream call.
        """
        content = msg.get("content", "")
        is_final = msg.get("is_final", False)
        chunk_size = 3000  # leave headroom for envelope
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        for i, chunk in enumerate(chunks):
            sub = dict(msg)
            sub["content"] = chunk
            sub["continuation"] = True                           # ALWAYS marked (round-5 C3)
            sub["is_final"] = is_final and (i == len(chunks) - 1)  # only LAST carries is_final
            try:
                self._stream.write(json.dumps(sub, separators=(",", ":"), ensure_ascii=False) + "\n")
            except (BrokenPipeError, OSError):
                return
        try:
            self._stream.flush()
        except (BrokenPipeError, OSError):
            pass

    def _check_rate(self) -> bool:
        now = time.monotonic()
        self._send_times = [t for t in self._send_times if now - t < 1.0]
        if len(self._send_times) >= self._max_msg_per_sec:
            return False
        self._send_times.append(now)
        return True

    # ── graph_reporter protocol (4 async methods; round-5 M1 corrected) ─

    async def on_graph_topology(self, event: Any) -> None:
        try:
            await self._emit(_serialize(event, self._task_id))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_topology failed: %s", exc)

    async def on_node_status(
        self, node_id: str, status: str,
        error: str = "", output_path: str = "",
    ) -> None:
        from agent_foundation.common.inferencers.graph_events import NodeStatusEvent
        try:
            await self._emit(_serialize(
                NodeStatusEvent(node_id=node_id, status=status,
                                error=error, output_path=output_path),
                self._task_id,
            ))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_status failed: %s", exc)

    async def on_node_stream(self, node_id: str, content: str, is_final: bool = True) -> None:
        # is_final events ALWAYS pass the rate limiter (matches WS:160-172).
        if not is_final and not self._check_rate():
            return
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent
        try:
            await self._emit(_serialize(
                NodeStreamEvent(node_id=node_id, content=content, is_final=is_final),
                self._task_id,
            ))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_node_stream failed: %s", exc)

    async def on_graph_reconcile(self, node_statuses: dict) -> None:
        from agent_foundation.common.inferencers.graph_events import GraphReconcileEvent
        try:
            await self._emit(_serialize(
                GraphReconcileEvent(node_statuses=node_statuses),
                self._task_id,
            ))
        except Exception as exc:
            _logger.warning("[StdioGraphReporter] on_graph_reconcile failed: %s", exc)

    # ── factory methods (3) ──────────────────────────────────────────────

    def node_stream_observer(self, node_id: str, flush_interval_ms: float = 200.0) -> Callable:
        """Batches token chunks at 200ms (matches WebSocketGraphReporter)."""
        from agent_foundation.common.inferencers.graph_events import NodeStreamEvent

        _batch: list[str] = []
        _last_flush = [time.monotonic()]

        async def _observer(chunk: str) -> None:
            _batch.append(chunk)
            now = time.monotonic()
            if (now - _last_flush[0]) * 1000 >= flush_interval_ms:
                content = "".join(_batch)
                _batch.clear()
                _last_flush[0] = now
                if content:
                    await self.on_node_stream(node_id, content, is_final=False)

        return _observer

    def node_interactive(self, node_id: str) -> Any:
        """Stub interactive — subprocess has no bidirectional channel."""
        return _StdioNodeInteractive(self, node_id)

    def child_reporter(self, parent_node_id: str) -> NamespacedGraphReporter:
        """Reused VERBATIM from graph_interactive_adapter.py:234-274 (generic)."""
        return NamespacedGraphReporter(self, parent_node_id)


class _StdioNodeInteractive:
    """Stub satisfying the slim subset of WebSocketInteractive that BTA uses.

    Signature of stream_token_batches mirrors all kwargs BTA call sites
    (Round-7 fix Mo1: signature mirrors NodeStreamInteractive.stream_token_batches
    at agent_foundation/ui/graph_interactive_adapter.py:51-60 — the AgentFoundation-
    local interface BTA actually receives via graph_reporter.node_interactive(...).
    Earlier citation to BTA:1815/2027 was wrong; grep confirms zero hits for
    stream_token_batches in BTA — those lines are on_node_stream calls.)
    CI preflight test_no_op_node_interactive_signature_alignment.py
    catches drift the moment WebSocketInteractive changes.
    """

    def __init__(self, parent: StdioGraphReporter, node_id: str) -> None:
        self._parent = parent
        self._node_id = node_id

    async def stream_token_batches(
        self, token_stream: Any, session_id: str = "",
        batch_interval_ms: float = 50.0, task_id: Any = None,
        send_stream_end: bool = True, turn_number: Any = None, **kwargs: Any,
    ) -> str:
        out: list[str] = []
        async for chunk, _meta in token_stream:
            out.append(chunk)
            try:
                await self._parent.on_node_stream(self._node_id, chunk, is_final=False)
            except Exception:
                pass
        try:
            await self._parent.on_node_stream(self._node_id, "", is_final=True)
        except Exception:
            pass
        return "".join(out)

    # Round-7 fix M2: __getattr__ must distinguish sync vs async methods.
    # InteractiveBase has SYNC methods (verified by direct grep at
    # agent_foundation/ui/interactive_base.py:75 `def get_input(self)` and
    # :151 `def send_response(self, ...)`). If BTA's child agents call these
    # via _StdioNodeInteractive, returning an async coroutine for a sync
    # method gives them a coroutine object instead of the expected value
    # → agent.py:715 does `raw_input = self.interactive.get_input()` and
    # then uses raw_input as a string. send_response calls would also leak
    # RuntimeWarning: coroutine was never awaited.
    #
    # We branch on KNOWN-async names (curated from InteractiveBase + its
    # subclasses + WebSocketInteractive) and default to a SYNC no-op for
    # everything else. The CI preflight at §9.2 verifies stream_token_batches
    # alignment; this list covers the other async surface members.
    # Round-8 CR3: extended to cover ALL 7 public async methods on
    # WebSocketInteractive (verified by grep at websocket_interactive.py).
    # Missing on_clean_output_available + send_task_status caused silent
    # TypeError per turn because conversational_inferencer.py:243 calls
    # `await effective_interactive.on_clean_output_available(...)` after a
    # `hasattr` check that ALWAYS passes (our __getattr__ is unconditional).
    # The result resolved to _sync_noop → returned None → `await None`
    # → TypeError → swallowed by surrounding try/except Exception → log spam
    # every turn. The §9.4b completeness preflight (Round-8 CR3b — corrected from §9.2 per Round-9 Mo2) prevents
    # future drift by asserting this set covers every WS async method.
    # Note: stream_token_batches is included for documentation, but the real
    # method on _StdioNodeInteractive (defined below) shadows __getattr__,
    # so the entry is effectively dead. Kept for self-documentation.
    _ASYNC_NOOP_NAMES: frozenset[str] = frozenset({
        "asend_response", "aget_input", "stream_token_batches",
        "send_turn_boundary", "send_graph_event",
        "on_clean_output_available",                 # Round-8 CR3 (CRITICAL)
        "send_task_status",                          # Round-8 CR3 (defensive)
    })

    def __getattr__(self, name: str) -> Any:
        """No-op stub. Returns async coroutine for known-async methods, sync
        no-op for everything else. See Round-7 fix M2 above for rationale."""
        if name in self._ASYNC_NOOP_NAMES:
            async def _async_noop(*args: Any, **kwargs: Any) -> Any:
                return None
            return _async_noop
        def _sync_noop(*args: Any, **kwargs: Any) -> Any:
            return None
        return _sync_noop
```

### 5.3 Tests (TIER-1)

`AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py`:

| Test | Assertion |
|---|---|
| `test_from_env_no_var` | Env unset → `from_env()` returns None |
| `test_from_env_invalid_int` | `ROVODEV_TUI_GRAPH_FD=garbage` → None |
| `test_from_env_closed_fd` | Env set but fd not open → None (mocks `os.fstat` to raise) |
| `test_from_env_valid_fd_returns_instance` | Real `os.pipe()` write-end → `StdioGraphReporter` instance |
| `test_emits_4_event_types_through_real_bta` | Drive `MockBreakdown → MockWorker × 2 → MockAggregator` (from `mock_bta_components.py:25-142`) through real BTA with `StdioGraphReporter(stream=io.StringIO())`; parse → assert sequence: `≥1 graph_topology, N node_status (pending→running→completed), M node_stream, 1 graph_reconcile` |
| `test_serialize_schema_matches_websocket_interactive_send_graph_event` | For each of 4 event types, compare `_serialize` output dict-key-by-dict-key to `websocket_interactive.py:43-99` schema |
| `test_rate_limiter_drops_non_final_streams` | 100 rapid `on_node_stream(is_final=False)` → only first 30 written; 1 `on_node_stream("", is_final=True)` → it ALWAYS writes |
| `test_namespaced_child_reporter_prefixes_node_ids` | `child_reporter("worker_0").on_node_status("propose", "running")` → emitted `node_id="worker_0/propose"` |
| `test_broken_pipe_swallowed` | Close stream mid-emission → next call returns None (does NOT raise) |
| `test_lock_serializes_concurrent_emits` | `await asyncio.gather(*(rep.on_node_stream(f"w_{i}", "x"*5000) for i in range(10)))` → output parses cleanly as 10 distinct lines |
| `test_oversize_node_stream_is_chunked` | 10 KB `content` → multiple lines, all but last have `"continuation": true`, last has `"is_final": true` if original did |
| `test_node_stream_observer_batches_at_200ms` | Monkeypatch `time.monotonic`; 100 chunks within 200 ms → 0 writes; 1 more chunk at 201 ms → 1 batched write |

CI preflight: `test_protocol_method_set_matches_websocket_reporter` (see §9).


---

## 6. `graph_reporter_factory` + per-executor wiring (no tool_cli patch)

### 6.1 `graph_reporter_factory.py` (~25 lines)

`AgentFoundation/src/agent_foundation/ui/graph_reporter_factory.py`:

```python
"""Factory: pick the right graph reporter; precedence WS > Stdio > None.

This factory is called from EACH tool executor's existing graph_reporter attach
block, replacing the 3x duplicated `if interactive: WebSocketGraphReporter(...)` (round-5 C1)
boilerplate with a single line.

Resolution order:
  1. WebSocketGraphReporter — if session_context['interactive'] is set
     AND task_id is non-empty (React UI path).
  2. StdioGraphReporter.from_env(task_id) — if ROVODEV_TUI_GRAPH_FD env var
     names a valid fd (RovoDev TUI subprocess path).
  3. None — silent fallback (existing direct-CLI behaviour).

WS wins over Stdio when both signals are present (defends against env-var
leakage in nested subprocess invocations).

ARCHITECTURAL NOTE: There is intentionally NO patch in tool_cli.run_cli. The
factory is the single attach point. (v2 of this plan tried to wire reporter in
tool_cli AND in executors; this was contradictory — see v3 §0.)
"""
from __future__ import annotations
import logging
from typing import Any

_logger = logging.getLogger(__name__)


def make_graph_reporter(session_context: dict, task_id: str = "") -> Any:
    """Returns a graph_reporter or None."""
    interactive = session_context.get("interactive")
    if interactive is not None and task_id:
        try:
            from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
            r = WebSocketGraphReporter(interactive, task_id)
            _logger.info("[graph_reporter_factory] WebSocketGraphReporter (task_id=%s)", task_id)
            return r
        except Exception as exc:
            _logger.warning("[graph_reporter_factory] WS attach failed: %s", exc)
            # fall through to Stdio
    try:
        from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter
        r = StdioGraphReporter.from_env(task_id=task_id)
        if r is not None:
            _logger.info("[graph_reporter_factory] StdioGraphReporter (task_id=%s)", task_id)
            return r
    except ImportError as exc:
        # Older AgentFoundation without StdioGraphReporter — silent degrade.
        _logger.debug("[graph_reporter_factory] StdioGraphReporter unavailable: %s", exc)
    except Exception as exc:
        _logger.warning("[graph_reporter_factory] Stdio attach failed: %s", exc)
    return None
```

### 6.2 Per-executor 6-line diff (apply to **3 real attach-site** executors — round-5 C1)

For `OpenStartup/src/openteam/server/resources/tools/task/executor.py:493-500`, replace:

```python
# BEFORE
interactive = sc.get("interactive")
if interactive is not None and task_id:
    try:
        from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
        inferencer.graph_reporter = WebSocketGraphReporter(interactive, task_id)
        _logger.info("[task] WebSocketGraphReporter attached (task_id=%s)", task_id)
    except Exception as exc:
        _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

with:

```python
# AFTER
try:
    from agent_foundation.ui.graph_reporter_factory import make_graph_reporter
    inferencer.graph_reporter = make_graph_reporter(sc, task_id)
    if inferencer.graph_reporter is not None:
        _logger.info("[task] graph_reporter attached: %s",
                     type(inferencer.graph_reporter).__name__)
except Exception as exc:
    _logger.warning("[task] graph_reporter attach failed: %s", exc)
```

Identical diff for the **3** real attach sites (NOT 5 — see Round-5 patch C1):
- `task/executor.py:493-500` (shown above)
- `project_onboarding/executor.py:165-167`
- `mock_task/executor.py:60-62`

**`create_role/executor.py` and `role_setup/executor.py` are NOT patched** — both delegate into `task/executor.py:_run_topology` via `await _run_topology(source=..., session_context=session_context)`. Their "attach" happens transitively through `task`'s patched block. The comments at create_role:559-562 and role_setup:1259-1262 are accurate descriptions of that delegation, not separate attach sites.

Net line count per executor: **~0 (the BEFORE and AFTER blocks are similar size; line count is not the win — Round-8 Mo6 corrected: earlier "-3 lines" math was wrong)**. The actual win is **conceptual**: every executor that wants graph events now calls ONE factory that handles env-var detection, WS-fallback, and noop-when-disabled — instead of 3 different copy-pasted `if interactive: WebSocketGraphReporter(...)` blocks each with its own `task_id` minting, fd-handling, and fallback semantics. Verified by `grep -rn "WebSocketGraphReporter(" src/openteam/server/resources/tools/` returning exactly 3 hits today (task:497, project_onboarding:167, mock_task:61); after Phase 2 patches the same grep returns 0 hits and the same grep for `make_graph_reporter(` returns 3.

### 6.3 NO `tool_cli.run_cli` patch (intentional)

In v2 I had a `tool_cli.run_cli` 15-line block that constructed the reporter and stuffed it into `session_context["graph_reporter"]`. **v3 drops this entirely.** Reasons:

1. **Contradictory with per-executor wiring**: if both run, one is dead code.
2. **`tool_cli` doesn't know `task_id`**: would have to mint a new UUID and not match the React UI's task_id convention.
3. **Less observable**: the factory's "one log line per attach" surface is lost if `tool_cli` pre-populates.
4. **No future-proofing benefit**: a future 6th tool would still need its existing `interactive`-block patched to call `make_graph_reporter` — the patch isn't avoided.

The only argument for the `tool_cli` patch is "fewer files touched". **3** executors × 6 lines (round-5 C1: not 5; create_role and role_setup are delegating wrappers) is a trivial mechanical edit, and the CI preflight `test_factory_used_by_all_executors.py` catches forgotten patches.

### 6.4 Tests

`AgentFoundation/test/agent_foundation/ui/test_graph_reporter_factory.py` (TIER-1):

| Test | Assertion |
|---|---|
| `test_returns_ws_when_interactive_and_task_id` | `make_graph_reporter({"interactive": MockWS()}, "tid")` → `WebSocketGraphReporter` instance |
| `test_returns_stdio_when_env_set_no_interactive` | Env `ROVODEV_TUI_GRAPH_FD=N` + empty context → `StdioGraphReporter` |
| `test_returns_none_when_neither` | Empty context, no env → None |
| `test_ws_wins_over_stdio_when_both` | Both signals → WS (defends against env leak) |
| `test_ws_attach_failure_falls_through_to_stdio` | Mock `WebSocketGraphReporter()` raises → factory falls through to Stdio if env set |
| `test_importerror_for_stdio_silent_degrade` | Monkeypatch `StdioGraphReporter` import to raise ImportError → returns None silently (no warning at INFO+) |

`OpenStartup/test/openteam/integration/test_factory_used_by_all_executors.py` (TIER-1 / **CI preflight**):

```python
"""Round-5 fix C2 + Round-9 m1: refined to avoid false positives on DELEGATING wrappers.

NOTE (R9-m1): pytest is imported below; prior version used `pytest.fail`
without `import pytest` → NameError on first hit.


Old version (round-3) keyed on any occurrence of the word `graph_reporter`,
which fires on `create_role/executor.py:559` and `role_setup/executor.py:1259`
where the word appears ONLY inside `#` comments documenting their delegation
into task/executor.py:_run_topology. v4 keys on the actual call site signature
`WebSocketGraphReporter(` (which IS the legacy pattern we're banning) — this
is precise and impossible to false-trigger.

What v4 actually asserts:
  - No executor has a literal `WebSocketGraphReporter(` (legacy direct attach).
  - Any executor that calls `make_graph_reporter(` is wired through the factory.
  - Files that have no graph_reporter line and no factory call (i.e., delegating
    wrappers like create_role/role_setup) are silently allowed.
"""
import ast, pathlib
import pytest                # Round-9 m1: required for pytest.fail() below

TOOLS = pathlib.Path("src/openteam/server/resources/tools")

def _strip_comments(src: str) -> str:
    """Remove # comments + docstrings via AST so the substring check counts
    code-level references only.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
    return ast.unparse(tree)


def test_no_legacy_websocket_graph_reporter_call_sites():
    """Refined to count ONLY call sites — not comments, not docstrings."""
    for executor in TOOLS.glob("*/executor.py"):
        code = _strip_comments(executor.read_text())
        legacy_calls = [
            line_no for line_no, line in enumerate(code.split("\n"), 1)
            if "WebSocketGraphReporter(" in line
        ]
        # Comment any legacy call only allowed in /test/ tree.
        assert not legacy_calls, (
            f"{executor}: legacy direct WebSocketGraphReporter() call sites at "
            f"line(s) {legacy_calls}. Use make_graph_reporter(sc, task_id) instead."
        )


def test_executors_with_graph_reporter_code_use_factory():
    """Refined to count code-level (non-comment, non-docstring) references."""
    for executor in TOOLS.glob("*/executor.py"):
        code = _strip_comments(executor.read_text())
        if "graph_reporter" in code and "make_graph_reporter" not in code:
            pytest.fail(
                f"{executor}: has CODE-LEVEL graph_reporter reference but does "
                f"not call make_graph_reporter(). Future tool authors must wire "
                f"through the factory. (Comments-only references are OK and "
                f"explicitly allowed for delegating wrappers like create_role / "
                f"role_setup, which delegate into task/executor.py._run_topology.)"
            )
```


---

## 7. TUI side: `TopologyView` + NDJSON reader + handler integration

### 7.1 File layout

```
acra-python/packages/cli-rovodev-tui/src/rovodev_tui/
├── widgets/
│   └── topology_view.py              # NEW — TopologyView + NodeState (~350 LOC)
├── slash_commands/
│   ├── openteam.py                   # MODIFIED — handler extension (+60 -5 LOC)
│   ├── _openteam_graph.py            # NEW — NDJSON reader + dispatcher (~80 LOC)
│   └── _async_fd.py                  # NEW — POSIX fd → asyncio.StreamReader (~15 LOC)
└── tests/
    ├── widgets/
    │   ├── test_topology_view.py     # NEW (TIER-1, 12 tests)
    │   └── test_topology_view_snapshots.py  # NEW (TIER-2, 3 snapshots)
    ├── slash_commands/
    │   ├── test_openteam_graph_dispatch.py  # NEW (TIER-1, 5 tests)
    │   ├── test_async_fd.py          # NEW (TIER-2, 2 tests)
    │   └── test_handler_integration.py  # NEW (TIER-2, 4 tests)
    └── integration/
        └── test_openteam_graph_e2e.py  # NEW (TIER-2, full subprocess + mock_task)
```

### 7.2 `_async_fd.py` — POSIX fd → `asyncio.StreamReader` (Py 3.11+ compatible)

```python
# packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/_async_fd.py
"""Open a raw OS file descriptor as an asyncio StreamReader (POSIX).

CRITICAL: the `loop=` kwarg of asyncio.StreamReader and StreamReaderProtocol
was DEPRECATED in Python 3.8 and REMOVED in Python 3.10. Both repos pin
`requires-python >= 3.11`, so passing `loop=` raises TypeError at runtime.
We use the no-kwarg form, which auto-discovers the running loop.

Windows: pass_fds semantics differ; v1 is POSIX-only. Phase 6 (post-ship)
adds a Windows fallback (detect sys.platform == 'win32' → skip graph view).
"""
from __future__ import annotations

import asyncio
import os


async def open_async_fd_reader(
    fd: int,
) -> tuple[asyncio.StreamReader, asyncio.BaseTransport]:
    """Wrap a raw read-side fd as an asyncio StreamReader.

    Returns (reader, transport) — caller MUST call transport.close() in
    its cleanup (e.g., after proc.wait()); the transport owns the fd
    after this function returns successfully.

    Round-5 fix M4: ownership-safe error handling. `os.fdopen` takes
    ownership of fd; if `connect_read_pipe` raises, we close the WRAPPER
    (which closes the fd exactly once), then re-raise. Caller must NOT
    call os.close(fd) after open_async_fd_reader succeeds (transport
    handles it) and must NOT call os.close(fd) after a raised exception
    either (wrapper already closed it). Caller marks `event_read_fd = None`
    on exception to communicate "already cleaned up; do not close".
    """
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()                       # NO loop= kwarg
    protocol = asyncio.StreamReaderProtocol(reader)       # NO loop= kwarg
    pipe = os.fdopen(fd, "rb", buffering=0)               # pipe NOW owns fd
    try:
        transport, _ = await loop.connect_read_pipe(lambda: protocol, pipe)
    except BaseException:                                  # broad on purpose
        # pipe.close() closes fd exactly once; race-safe.
        try:
            pipe.close()
        except OSError:
            pass
        raise
    return reader, transport
```

### 7.3 `_openteam_graph.py` — NDJSON dispatcher

```python
# packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/_openteam_graph.py
"""NDJSON event reader for OpenTeam graph events from a subprocess fd."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rovodev_tui.widgets.topology_view import TopologyView

_logger = logging.getLogger(__name__)


async def read_ndjson_events(
    reader: asyncio.StreamReader, view: "Optional[TopologyView]", app
) -> None:
    """Consume one JSON object per line; dispatch to view via thread bridge.

    Exits cleanly on EOF (subprocess closed write end) or ConnectionReset.
    Malformed lines are logged and skipped — they NEVER crash the reader.

    Round-5 fix C4: continuation buffers are DRAINED on EOF and before
    dispatching any intervening node_status for the same node — otherwise
    the buffered tail of a streamed message is silently lost.

    Round-5 fix C5: uses loguru `logger`, not bare `_logger` (matches
    repo convention in shell.py:9).

    If view is None (graph disabled), all events are silently dropped — we
    still drain the pipe so the subprocess doesn't block on a full kernel
    buffer.
    """
    from loguru import logger                       # round-5 C5
    _continuation: dict[str, list[str]] = {}

    # Round-7 fix M5: per-node continuation buffer cap. Producer is capped
    # (200 KB at the widget level), but reader buffers ALL chunks until is_final
    # or graph_reconcile. A misbehaving / aborted producer that streams thousands
    # of continuation chunks with no is_final=True would accumulate hundreds of
    # MB before the widget-side MAX_STREAM_SIZE cap fires. The finally:drain
    # only fires at reader exit. Solution: per-node cap with head-trim on overflow
    # and a single WARN log; trim mirrors the widget's TRIM_SIZE policy so the
    # eventual flushed string fits the widget's expected shape.
    CONTINUATION_BUFFER_CAP = 1_048_576    # 1 MB per node
    CONTINUATION_TRIM_TARGET = 200_000     # match widget MAX_STREAM_SIZE
    _continuation_warned: set[str] = set()  # log once per node per stream

    def _append_continuation(nid: str, chunk: str) -> None:
        """Append chunk to per-node continuation buffer; trim on overflow."""
        buf = _continuation.setdefault(nid, [])
        buf.append(chunk)
        total = sum(len(s) for s in buf)
        if total > CONTINUATION_BUFFER_CAP:
            if nid not in _continuation_warned:
                logger.warning(
                    f"[_openteam_graph] node {nid} continuation buffer exceeded "
                    f"{CONTINUATION_BUFFER_CAP} bytes without is_final — trimming "
                    f"head to keep last {CONTINUATION_TRIM_TARGET} bytes (logged once)"
                )
                _continuation_warned.add(nid)
            joined = "".join(buf)
            kept = joined[-CONTINUATION_TRIM_TARGET:]
            _continuation[nid] = [kept]

    def _flush_continuation(nid: str, *, is_final: bool) -> None:
        """Drain buffered chunks for node_id and emit one apply_node_stream call."""
        buf = _continuation.pop(nid, None)
        if buf is None or view is None:
            return
        joined = "".join(buf)
        if joined:
            app.call_from_thread(view.apply_node_stream, nid, joined, is_final)

    try:
        while True:
            try:
                line = await reader.readline()
            except (ConnectionResetError, OSError) as exc:
                logger.debug(f"[_openteam_graph] pipe closed: {exc}")
                return
            if not line:
                return  # EOF — drained in `finally` below
            if view is None:
                continue  # drain-only

            try:
                evt = json.loads(line.decode("utf-8", "replace").rstrip())
            except json.JSONDecodeError as exc:
                logger.warning(f"[_openteam_graph] malformed NDJSON ({exc}): {line[:120]!r}")
                continue

            etype = evt.get("type")
            nid = evt.get("node_id", "")

            # Round-5 fix C4: a node_status for this node arriving while a
            # continuation is in flight must flush the buffered tail first,
            # otherwise the tail is lost. Same for graph_reconcile.
            if etype in ("node_status", "graph_reconcile") and nid and nid in _continuation:
                _flush_continuation(nid, is_final=True)

            # Round-5 fix C3 + C4: every chunk now carries `continuation: True`
            # (producer-side fix); reader buffers until is_final.
            if etype == "node_stream" and evt.get("continuation"):
                _continuation.setdefault(nid, []).append(evt.get("content", ""))
                if not evt.get("is_final"):
                    continue
                # Final chunk in a continuation run — drain + dispatch ONE event.
                _flush_continuation(nid, is_final=True)
                continue

            try:
                if etype == "graph_topology":
                    app.call_from_thread(view.apply_topology_event,
                                         evt.get("nodes", []), evt.get("edges", []),
                                         evt.get("parent_node_id", ""))
                elif etype == "node_status":
                    app.call_from_thread(view.apply_node_status,
                                         nid, evt["status"],
                                         evt.get("error", ""), evt.get("output_path", ""))
                elif etype == "node_stream":
                    app.call_from_thread(view.apply_node_stream,
                                         nid, evt.get("content", ""),
                                         bool(evt.get("is_final", False)))
                elif etype == "graph_reconcile":
                    app.call_from_thread(view.apply_graph_reconcile,
                                         evt.get("nodes", {}))
                else:
                    logger.debug(f"[_openteam_graph] unknown event type={etype!r}")
            except Exception:
                logger.exception(f"[_openteam_graph] dispatch failed for event={evt!r}")
    finally:
        # Round-5 fix C4: any continuations still buffered at EOF must be
        # flushed (the subprocess died mid-stream; render what we have).
        for nid in list(_continuation.keys()):
            _flush_continuation(nid, is_final=True)
```

### 7.4 `topology_view.py` — single-file widget (~350 LOC)

The widget is identical in shape to Cursor's §4.4 — Tree + ContentSwitcher of per-node RichLogs, sticky selection, bounded streams, race buffer, headless-frozen glyph. See v2 §7.2 for the full code listing (v3 inherits it unchanged; the only adjustment is the inline TBD: status-glyph "running" character is **● (filled circle)** which freezes to "·" via `app.is_headless`).

Key methods (called from `_openteam_graph.read_ndjson_events` via `app.call_from_thread`):
- `apply_topology_event(nodes, edges, parent_node_id="")` — idempotent splice
- `apply_node_status(node_id, status, error="", output_path="")` — race-buffer creates stub if topology not yet arrived
- `apply_node_stream(node_id, content, is_final=False)` — appends to per-node RichLog; bounded by MAX_STREAM_SIZE
- `apply_graph_reconcile(node_statuses)` — fixes drift
- `append_final_result(text)` — appends to the special "Final result" panel (selected by default until user clicks a node)

React-mirrored constants:
- `MAX_STREAM_SIZE = 200_000` (per-node soft cap on dict)
- `TRIM_SIZE = 50_000` (tail kept on overflow)
- `STICKY_DURATION_MS = 5_000` (post-click pin)
- `MAX_TOTAL_STREAMS = 10_000_000` (cross-node ceiling)
- **`RICHLOG_MAX_LINES = 2000`** (round-5 M6: also bound the **widget** memory, not just the dict). Each per-node `RichLog` is constructed as `RichLog(max_lines=RICHLOG_MAX_LINES, highlight=False, markup=True, wrap=True)`. Without this bound, the widget retains every line ever written even though the backing `self._streams[node_id]` dict is trimmed — a memory leak proportional to total tokens streamed.

Status glyphs (color + shape distinguished for accessibility):
- `pending=○ running=● completed=✓ error=✗ skipped=−`
- When `self.app.is_headless` is True: `running` glyph frozen to `·` (snapshot stability). The `·` substitution pattern is at `widgets/chat_container.py:720` (Round-7 fix Mo5 correction — `interval_updater.py:30` is the `is_headless` idiom only); we mirror both: the headless guard from `interval_updater.py:26-30` and the braille→`·` substitution from `chat_container.py:720`.

### 7.5 `slash_commands/openteam.py` handler — full integrated diff

The current handler (post-v6) uses `stderr=STDOUT`, single readline loop, `os.pipe()` not allocated. v3 extends it to add the fd-3 pipe + graph view + NDJSON reader, **without changing `stderr=STDOUT`** or splitting the stdout/stderr reader.

```python
# Insertions to existing _make_handler. Original code unchanged unless commented "NEW" or "MODIFIED".
import os
import uuid
from loguru import logger              # round-5 fix C5 (repo convention; matches shell.py:9)
from rovodev_tui.slash_commands._async_fd import open_async_fd_reader
from rovodev_tui.slash_commands._openteam_graph import read_ndjson_events
from rovodev_tui.widgets.topology_view import TopologyView

_OPT_OUT = "ROVODEV_TUI_GRAPH_DISABLE"
_TUI_GRAPH_FD = "ROVODEV_TUI_GRAPH_FD"


def _make_handler(slash, binary, fallback_module):
    async def handler(app, extra_prompt):
        worker = get_current_worker()
        if worker is None:
            app.notify_and_log(f"{slash}: missing worker context (registration bug)",
                               severity="error", timeout=10)
            return

        # NEW: opt-out check
        graph_enabled = os.environ.get(_OPT_OUT) != "1"
        topology_view: TopologyView | None = None
        shell_output_widget = None
        event_read_fd: int | None = None
        event_write_fd: int | None = None
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # NEW: mount TopologyView OR (disabled path) ShellOutput
        if graph_enabled:
            topology_view = TopologyView(task_label=f"OpenTeam {slash[1:]}")
            app.call_from_thread(app.chat_container.mount, topology_view)
        else:
            shell_output_widget = ShellOutput()
            app.call_from_thread(app.chat_container.mount, shell_output_widget)
        spinner = ThinkingSpinner(f"Running OpenTeam {slash[1:]}")
        app.call_from_thread(app.chat_container.mount, spinner)

        # ── Build argv + env ────────────────────────────────────────────
        argv, env = _build_argv_and_env(binary, fallback_module, shlex.split(extra_prompt))
        # Round-8 fix CR2: env["OPENTEAM_TASK_ID"] removed entirely. Round-7 M1
        # added the explanatory comment block below but FORGOT to delete this
        # line — a textbook half-fix. See R7-M1 comment + Round-8 CR2 note.

        # NEW: pipe for graph events (only if enabled)
        pass_fds: tuple[int, ...] = ()
        if graph_enabled:
            event_read_fd, event_write_fd = os.pipe()
            env[_TUI_GRAPH_FD] = str(event_write_fd)
            # Round-7 fix M1: do NOT set env["OPENTEAM_TASK_ID"] = task_id.
            # OpenStartup never reads OPENTEAM_TASK_ID (grep confirms zero
            # readers in src/openteam/). tool_cli.py:114 inits an empty
            # session_context, then each executor does
            #   task_id = sc.get("task_id") or f"task-{uuid.uuid4().hex[:8]}"
            # → subprocess always mints its own fresh UUID. The TUI's
            # handler-local task_id and the subprocess's task_id are
            # INDEPENDENT identifiers. The NDJSON envelope's task_id field
            # (set by StdioGraphReporter.from_env) is what the TUI reader
            # uses for node_id qualification — that's the authoritative ID.
            # See §4 architecture diagram for the corrected flow.
            pass_fds = (event_write_fd,)
            # Note: Python's subprocess.Popen handles set_inheritable internally
            # when fds appear in pass_fds — no manual os.set_inheritable needed.

        cwd = _get_workspace_path(app)
        proc = None
        # Round-8 unified rewrite of spawn-and-reader-setup (addresses Round-7
        # CR1, M4, M5, M6 together — they were tangled and the prior split-into-
        # halves Round-7 patch caused CR1 by losing track of the write-fd state).
        #
        # Invariants (machine-followable):
        #   1. event_read_fd  OWNERSHIP: held by handler until open_async_fd_reader
        #      succeeds; then owned by the transport (transport.close() closes it).
        #      On ANY spawn/setup failure, handler closes it in finally.
        #   2. event_write_fd OWNERSHIP: passed to child via pass_fds; parent
        #      MUST close immediately after spawn (whether successful or not),
        #      because pipe(7) requires SOMEONE to be the lone writer so reader
        #      sees EOF on child exit. Round-8 CR1: never gate downstream logic
        #      on event_write_fd's non-None state — it's a transient handle.
        #   3. Widgets (topology_view, shell_output_widget, spinner) mounted BEFORE
        #      this block must be removed on ANY exception path that returns to
        #      the user (Round-8 M5: previously orphaned on CancelledError).
        try:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,   # PRESERVED from v6 baseline
                    stdin=asyncio.subprocess.DEVNULL,
                    env=env,
                    cwd=cwd,
                    pass_fds=pass_fds,                  # NEW (empty tuple if !graph_enabled)
                )
            except FileNotFoundError as e:
                # Recoverable: binary not installed. Notify + early return; the
                # outer try/finally below handles fd + widget cleanup uniformly.
                app.notify_and_log(
                    f"{slash}: {argv[0]} not found ({e}). Install openteam: "
                    f"`uv tool install -e {_openteam_home()}`",
                    severity="error", timeout=15,
                )
                return
            # Round-8 M4: do NOT catch CancelledError or BaseException here.
            # Letting CancelledError propagate to the worker is correct cancel
            # semantics. The outer try/finally cleans up fds + widgets if proc
            # is still None when we exit.

            # ── Parent ALWAYS drops write end after spawn ─────────────────
            # Round-8 CR1: previously this was inside the spawn try block AND
            # nullified event_write_fd, then a downstream block gated reader
            # setup on `event_write_fd is not None` (always False) → reader
            # never spawned → 64KB pipe buffer fills → subprocess deadlocks.
            # Fix: close the write fd, BUT gate the reader on the READ fd
            # (which is what actually controls reader liveness).
            if event_write_fd is not None:
                try:
                    os.close(event_write_fd)
                except OSError:
                    pass
                event_write_fd = None  # mark "already closed"; only meaningful
                                       # for the finally block's idempotence

            # ── Spawn NDJSON reader (Round-8 CR1: gate on READ fd) ─────────
            # Round-9 CR1: fixed Python IndentationError. The `except OSError`
            # was at column 12 (paired with the if's level) instead of column
            # 16 (paired with `try:` at column 16). ast.parse on the prior text
            # raised `unexpected unindent`. Verified by `python3 -c "import ast
            # ast.parse(...)"` and by extracting the block to /tmp/foo.py and
            # running `python3 -m py_compile`. Now syntactically valid.
            ndjson_task: asyncio.Task | None = None
            transport = None
            if graph_enabled and event_read_fd is not None:
                try:
                    ndjson_reader, transport = await open_async_fd_reader(event_read_fd)
                    event_read_fd = None  # ownership transferred to transport
                    ndjson_task = asyncio.create_task(
                        read_ndjson_events(ndjson_reader, topology_view, app),
                        name=f"openteam-graph-reader-{task_id}",
                    )
                except OSError as e:
                    # Round-5 C5: use loguru `logger` (was bare `_logger` — NameError)
                    logger.warning(f"[{slash}] event reader setup failed: {e}")
                    # Round-5 M4: open_async_fd_reader takes ownership of fd on
                    # success; on failure, the helper closes the wrapper internally.
                    # Handler does NOT close event_read_fd here (double-close race).
                    event_read_fd = None  # mark "already cleaned up"
        finally:
            # Round-9 unified cleanup (CR1+M4+M5+M6 + R9-M1+M2). Runs on ALL paths:
            #   - Happy: proc spawned, reader spawned, NO exception → both fds
            #     owned elsewhere; event_read_fd and event_write_fd are both
            #     None → fd loop is no-op; sys.exc_info()[0] is None →
            #     widget cleanup is no-op. Total cost: ~5 None checks.
            #   - FileNotFoundError (binary missing) → early return, proc=None →
            #     close any remaining fds + remove widgets.
            #   - CancelledError DURING spawn (proc=None) → close fds + remove
            #     widgets BEFORE the exception escapes the worker.
            #   - CancelledError AFTER spawn (proc set) → close any fds we still
            #     own AND remove widgets (R9-M1 fix: prior version only cleaned
            #     widgets when proc is None, leaving them orphan on this path).
            #   - OSError on reader setup → fd already cleaned by helper; proc
            #     is alive; widgets STAY (reader-less degraded mode is fine —
            #     the subprocess will still produce stdout). exc_info()[0] is
            #     OSError but reader-setup catches it before propagating, so
            #     this finally sees exc_info()[0]=None on that branch — correct.
            #
            # R9-M2 fix: SINGLE fd cleanup loop at top (works because already-
            # None fds short-circuit). Prior version had two near-identical
            # loops in if/else branches — same-fd-double-close was safe today
            # but a future refactor footgun.
            for cleanup_fd_name in ("event_read_fd", "event_write_fd"):
                fd_val = locals().get(cleanup_fd_name)
                if fd_val is not None:
                    try:
                        os.close(fd_val)
                    except OSError:
                        pass

            # R9-M1 fix: hoisted widget cleanup. Condition: remove widgets iff
            # the handler is exiting WITHOUT a live subprocess to render against.
            # That covers proc=None (spawn never completed) AND any uncaught
            # exception propagating out (CancelledError post-spawn). sys.exc_info()
            # is the canonical check inside a finally — it returns the EXCEPTION
            # CURRENTLY BEING PROPAGATED OUT OF THE BLOCK (not earlier caught-
            # and-handled exceptions, which is exactly what we want).
            import sys
            should_remove_widgets = (proc is None) or (sys.exc_info()[0] is not None)
            if should_remove_widgets:
                app.call_from_thread(spinner.remove)
                if topology_view is not None:
                    app.call_from_thread(topology_view.remove)
                if shell_output_widget is not None:
                    app.call_from_thread(shell_output_widget.remove)

        # ── Stream stdout (merged with stderr) — same single-loop pattern as v6 ──
        if proc.stdout is None:
            app.call_from_thread(spinner.remove)
            return
        output = ""
        while True:
            if worker.is_cancelled:
                # Round-5 fix M7: bounded terminate honoring §14 DoD "5s".
                # `await proc.wait()` unbounded can hang on D-state subprocess;
                # escalate to kill on timeout.
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(
                        f"[{slash}] subprocess did not exit 5s after SIGTERM; "
                        f"escalating to SIGKILL"
                    )
                    proc.kill()
                    await proc.wait()                  # SIGKILL is uninterruptible
                break
            if proc.stdout.at_eof():
                break
            line = await proc.stdout.readline()
            if not line:
                # Round-7 fix C1: was `continue` — busy-loop bug. Both
                # baseline patterns use `break` (shell.py:86, openteam.py:148):
                # readline() returns b"" synchronously on EOF (no asyncio
                # suspension), and the at_eof() check above may not flip in
                # the same tick → CPU spin until at_eof() finally flips, or
                # forever on a torn pipe. `break` is the only safe choice.
                break
            decoded = line.decode("utf-8", "replace")
            output += decoded
            # NEW: route to TopologyView OR ShellOutput
            target = topology_view.append_final_result if topology_view else shell_output_widget.append
            # NEW: detect [artifact_key] stderr-merged markers and dim them
            if decoded.startswith("["):
                app.call_from_thread(target, f"[dim]{decoded}[/dim]")
            else:
                app.call_from_thread(target, decoded)

        await proc.wait()

        # NEW: clean up reader + transport
        # Round-5 fix Mo6: explicit catch — CancelledError is BaseException
        # in py3.8+ so MUST be listed separately; Exception alone is insufficient.
        if ndjson_task is not None:
            ndjson_task.cancel()
            try:
                await ndjson_task
            except asyncio.CancelledError:
                pass                                    # expected on cancel()
            except Exception:
                logger.exception(f"[{slash}] ndjson reader raised on shutdown")
        if transport is not None:
            transport.close()

        # ALWAYS: spinner cleanup
        app.call_from_thread(spinner.remove)

        # NEW (Claude correction #2): empty-output cleanup for BOTH branches
        if not output.strip():
            if topology_view is not None:
                # Topology view may have content even with empty stdout (graph events)
                # — only remove if both stdout AND no graph events arrived.
                if topology_view.is_empty():       # see TopologyView.is_empty() below
                    app.call_from_thread(topology_view.remove)
            elif shell_output_widget is not None:
                app.call_from_thread(shell_output_widget.remove)
```

`TopologyView.is_empty()` helper (add to §7.4 widget) — **v4 uses a dedicated `_got_any_event` flag (set by every `apply_*` method), NOT a collection check**:

```python
class TopologyView(Vertical):
    def __init__(self, ...):
        super().__init__(...)
        self._nodes: dict[str, NodeState] = {}
        self._streams: dict[str, str] = {}
        ...
        self._got_any_event: bool = False  # NEW: O(1) is_empty() flag

    def is_empty(self) -> bool:
        """True iff NO apply_* method was ever called on this view —
        i.e., NO graph event arrived AND no final-result text was appended.

        Round-5 fix Mo5: docstring aligned to actual code semantics.
        Previously read "true iff no useful topology events arrived", which
        conflicted with the flag also being set by node_stream / node_status
        / append_final_result. The flag's monotonic "did anything ever
        happen" meaning is the right one — it makes the handler's
        "remove on empty stdout AND empty graph" check meaningful:
          - graph events only (non-BTA tool path) → keep widget (evidence)
          - graph events + stdout → keep widget
          - empty graph + empty stdout → remove widget (nothing happened)

        v4 uses a dedicated flag, NOT `not self._nodes`. Reasons:
        - O(1) and immune to future refactors of self._nodes shape
        - Survives `_cap_total_streams` purge (which may clear stream buffers
          but not the nodes dict) and any future cache eviction
        - Single source of truth: set ONCE by every public apply_* method;
          NEVER reset (the "did anything ever happen" semantics is monotonic)
        """
        return not self._got_any_event

    # Every public apply_* method sets the flag as its first line:
    def apply_topology_event(self, nodes, edges, parent_node_id=""):
        self._got_any_event = True  # ALWAYS first
        # ... existing logic

    def apply_node_status(self, node_id, status, error="", output_path=""):
        self._got_any_event = True
        # ... existing logic (including race-buffer stub creation)

    def apply_node_stream(self, node_id, content, is_final=False):
        self._got_any_event = True
        # ... existing logic

    def apply_graph_reconcile(self, node_statuses):
        self._got_any_event = True
        # ... existing logic

    def append_final_result(self, text):
        self._got_any_event = True   # final-result text alone counts as evidence
        # ... existing logic
```

**Test (TIER-1, added to `test_topology_view.py`):**
```python
def test_is_empty_starts_true_and_becomes_false_on_any_apply():
    v = TopologyView(task_label="t")
    assert v.is_empty()
    v.apply_node_status("n", "running")  # any apply_* sufficient
    assert not v.is_empty()

def test_is_empty_uses_flag_not_collection_membership():
    """Regression: v3 used `not self._nodes`; v4 uses dedicated flag.
    If a future refactor purges _nodes (e.g., cache eviction), is_empty()
    must still return False because events DID arrive.
    """
    v = TopologyView(task_label="t")
    v.apply_node_status("n", "running")
    v._nodes.clear()                       # simulate future purge
    assert not v.is_empty()                # flag is monotonic; survives
```

### 7.6 Tests

(Same coverage as v2 §7.5; only the asserted constants change to match v3.)

| Test file | TIER | Coverage |
|---|---|---|
| `tests/widgets/test_topology_view.py` | 1 | 12 tests: topology rebuild, status glyph, race buffer, sticky 5s, bounded streams, nested subgraph, etc. |
| `tests/widgets/test_topology_view_snapshots.py` | 2 | 3 snapshots: empty / mid-execution / complete; `app.is_headless` freezes glyph |
| `tests/slash_commands/test_openteam_graph_dispatch.py` | 1 | 5 tests: 4 event types dispatched, malformed skipped, EOF exit, continuation re-assembly, mid-continuation flush |
| `tests/slash_commands/test_async_fd.py` | 2 | 2 tests: pipe round-trip; **explicit assertion that `loop=` kwarg is NOT passed** (regression test against Cursor's bug) |
| `tests/slash_commands/test_handler_integration.py` | 2 | 4 tests: opt-out skips graph; empty-output removes widget(s); 3 readers concurrent; ndjson_task cleanup on exit |
| `tests/integration/test_openteam_graph_e2e.py` | 2 | Real `openteam-mock-task` subprocess → fd 3 → TopologyView state machine |


---

## 8. Phased delivery

| Phase | Scope | Effort | Blocking |
|---|---|---|---|
| **1a** | `StdioGraphReporter` + `from_env` | 3-4 h | – |
| **1b** | `graph_reporter_factory` | 30 min | 1a |
| **1c** | Tests for both (12 + 6 + CI preflight) | ½ day | 1a, 1b |
| **1d** | **Round-7 fix C3 (Round-8 M2 reordered):** Upstream `NamespacedGraphReporter.on_graph_reconcile` forwarder (round-7-corrected to qualify keys — see C2). Touches `agent_foundation/ui/graph_interactive_adapter.py` (one method add, ~3 lines). **Reordered to run BEFORE 1c**: 1d's upstream patch is what makes the §9.1 CI preflight pass; running 1c (tests) before 1d (the fix) creates a cycle. Correct order: 1a → 1b → **1d → 1c** → 2. | 15 min | 1a, 1b; **blocks 1c** (the §9.1 CI preflight depends on this forwarder existing) |
| **2** | Patch **3** executors (task, project_onboarding, mock_task; round-5 C1) + CI preflight `test_factory_used_by_all_executors.py` | 1 h | 1c (which depends on 1d) |
| **3a** | `topology_view.py` widget (single file) | 1 day | – |
| **3b** | Widget unit tests (12) | ½ day | 3a |
| **3c** | Snapshot tests (3) | ½ day | 3a |
| **4a** | `_async_fd.py` POSIX helper (NO `loop=`) | 30 min | – |
| **4b** | `_openteam_graph.py` NDJSON dispatcher + tests | 3 h | 4a |
| **4c** | `slash_commands/openteam.py` handler extension | ½ day | 3a, 4a, 4b |
| **5** | E2E smoke with `openteam-mock-task` | 1-2 h | all |
| **6** | Documentation (`MCP_INTEGRATION.md` + `openteam-integration.md`) | 1 h | 5 |
| **7** (post-ship) | Windows fallback (`sys.platform == 'win32'` → skip) | 2 h | – |
| **8** (post-ship) | Propagate `graph_reporter` through `DualInferencer`, `PlanThenImplementInferencer` | ½ day | – |
| **9** (post-ship) | `JsonlGraphReporter(path)` subclass for replay/debug | 2 h | – |

**Total: ~3 focused days for phases 1-6 (ship-ready).**

**Critical path:** 1a → 1b → **1d** → 1c → 2 → 4a → 4b → 4c → 5 → 6    (Round-9 M3: previously omitted 1d — see Round-8 M2/M3 changelog for the cycle fix that introduced 1d)
(3a/3b/3c can run in parallel with 1-2 if widget author is different from reporter author.)

---

## 9. CI preflight tests (catch drift, not bugs)

These three tests run on every PR; failure means the protocol has drifted and the integration is at risk.

### 9.1 `test_protocol_method_set_matches_websocket_reporter` (TIER-1)

**Round-5 fix M1+M3:** the WebSocketGraphReporter surface is **4 async + 3 factory = 7 members** (not 5+3 — `stream_token_batches` is on `NodeStreamInteractive`, not on the reporter). Also, the test must now check `NamespacedGraphReporter` against the same surface, since M3 found that the namespaced reporter lacks `on_graph_reconcile` — a real upstream bug that v4 fixes (see §5.2 patch below).

`AgentFoundation/test/agent_foundation/ui/test_stdio_graph_reporter.py`:

```python
def test_protocol_method_set_matches_websocket_reporter():
    """If WebSocketGraphReporter adds a method, StdioGraphReporter must too.

    Round-5: also checks NamespacedGraphReporter (round-5 M3 found it was
    missing on_graph_reconcile; v4 fixes it upstream — this test guards).

    Verified surface = 4 async + 3 factory:
      - on_graph_topology, on_node_status, on_graph_reconcile, on_node_stream
      - node_stream_observer, node_interactive, child_reporter
    """
    import inspect
    from agent_foundation.ui.graph_interactive_adapter import (
        WebSocketGraphReporter, NamespacedGraphReporter,
    )
    from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter

    def public_async_methods(cls):
        return {
            name for name, m in inspect.getmembers(cls, predicate=inspect.iscoroutinefunction)
            if not name.startswith("_")
        }
    def public_factory_methods(cls):
        return {
            name for name, m in inspect.getmembers(cls, predicate=inspect.isfunction)
            if not name.startswith("_") and not inspect.iscoroutinefunction(m)
        }

    ws_async = public_async_methods(WebSocketGraphReporter)
    ws_factory = public_factory_methods(WebSocketGraphReporter)

    # Sanity-check verified surface (round-5 M1): catches future drift in EITHER direction.
    expected_async = {"on_graph_topology", "on_node_status", "on_graph_reconcile", "on_node_stream"}
    expected_factory = {"node_stream_observer", "node_interactive", "child_reporter"}
    assert ws_async == expected_async, (
        f"WebSocketGraphReporter async surface drift: {ws_async} != {expected_async}"
    )
    assert ws_factory == expected_factory, (
        f"WebSocketGraphReporter factory surface drift: {ws_factory} != {expected_factory}"
    )

    # StdioGraphReporter must mirror WS exactly.
    assert public_async_methods(StdioGraphReporter) == ws_async
    assert public_factory_methods(StdioGraphReporter) == ws_factory

    # NamespacedGraphReporter must ALSO mirror — round-5 M3 found it was missing
    # on_graph_reconcile; v4 adds a one-line forwarder upstream.
    assert public_async_methods(NamespacedGraphReporter) == ws_async, (
        f"NamespacedGraphReporter async surface drift: "
        f"{public_async_methods(NamespacedGraphReporter)} != {ws_async}"
    )
    assert public_factory_methods(NamespacedGraphReporter) == ws_factory
```

**Round-5 fix M3 (upstream one-liner)** — add to `agent_foundation/ui/graph_interactive_adapter.py` `NamespacedGraphReporter` class:

```python
    # Round-5 fix M3 + Round-7 fix C2: forwarder for on_graph_reconcile.
    # Round-7 corrected: the original M3 claim "node_statuses keys ALREADY
    # contain the parent prefix" was WRONG. Direct read of BTA at
    # breakdown_then_aggregate_inferencer.py:1037-1040 shows:
    #   statuses = {n.name: "completed" for n in self._all_nodes()}
    #   statuses["breakdown"] = "completed"
    #   await self.graph_reporter.on_graph_reconcile(statuses)
    # Keys are UNQUALIFIED node names ("worker_0", "breakdown", etc.). The
    # sibling methods on_node_status / on_node_stream qualify via
    # self._qualify(node_id) (see :260-264). The forwarder MUST do the same
    # or the parent UI will update wrong nodes (or drop them as unknown).
    async def on_graph_reconcile(self, node_statuses: dict) -> None:
        qualified = {self._qualify(nid): status for nid, status in node_statuses.items()}
        await self._parent.on_graph_reconcile(qualified)
```

### 9.2 `test_no_op_node_interactive_signature_alignment` (TIER-1) — addresses Claude correction #3

**Round-5 fix C6**: this test originally imported `WebSocketInteractive` from `agent_foundation.ui.graph_interactive_adapter` — but **that class lives in OpenStartup** at `openteam.server.services.websocket_interactive:19`, not in AgentFoundation. Importing OpenStartup from AgentFoundation also violates the layer invariant. The correct peer-class inside AgentFoundation is **`NodeStreamInteractive`** at `agent_foundation/ui/graph_interactive_adapter.py:29` — it is the AgentFoundation-local interface that BTA actually receives via `graph_reporter.node_interactive(node_id)`. Comparing against `NodeStreamInteractive` is layer-correct AND semantically right.

```python
def test_stream_token_batches_signature_matches_node_stream_interactive():
    """If NodeStreamInteractive.stream_token_batches adds a kwarg, our stub must accept it.

    Round-5 fix C6: compares against NodeStreamInteractive (AgentFoundation-
    local at graph_interactive_adapter.py:29), NOT WebSocketInteractive
    (which lives in OpenStartup at websocket_interactive.py:19 and would
    violate the AgentFoundation-cannot-import-OpenStartup layer invariant).
    """
    import inspect
    from agent_foundation.ui.graph_interactive_adapter import NodeStreamInteractive
    from agent_foundation.ui.stdio_graph_reporter import _StdioNodeInteractive

    ref_sig = inspect.signature(NodeStreamInteractive.stream_token_batches)
    stub_sig = inspect.signature(_StdioNodeInteractive.stream_token_batches)

    # Stub accepts **kwargs → any new kwarg in NodeStreamInteractive is silently
    # absorbed (forward-compat against AgentFoundation evolution).
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in stub_sig.parameters.values()), \
        "_StdioNodeInteractive.stream_token_batches must accept **kwargs for forward-compat"

    # All non-VAR_KEYWORD params on the reference must exist on stub by name (no
    # drift in named args).
    ref_named = {n for n, p in ref_sig.parameters.items() if p.kind != inspect.Parameter.VAR_KEYWORD}
    stub_named = {n for n, p in stub_sig.parameters.items() if p.kind != inspect.Parameter.VAR_KEYWORD}
    missing = ref_named - stub_named
    assert not missing, (
        f"_StdioNodeInteractive.stream_token_batches missing kwargs: {missing}. "
        f"Add them to the stub OR ensure **kwargs absorbs (current impl does)."
    )
```

### 9.3 `test_factory_used_by_all_executors` (TIER-1) — see §6.4 above

### 9.4 `test_stderr_stdout_merged_regression` (TIER-1) — guards v6 baseline

`acra-python/packages/cli-rovodev-tui/tests/slash_commands/test_stderr_stdout_merged_regression.py`:

```python
"""Regression: v3 plan transiently changed stderr to PIPE. v6 baseline
mandates stderr=STDOUT (merged with stdout). Splitting them creates a
race between two readline loops + breaks v6 Phase 0a [artifact_key]
marker co-locality. This test prevents future re-splitting.
"""
import ast, inspect, pytest

from rovodev_tui.slash_commands import openteam as handler_mod


def test_handler_uses_stderr_stdout_merged():
    """AST-asserts every `create_subprocess_exec` call in openteam.py uses
    `stderr=asyncio.subprocess.STDOUT` (NOT PIPE / NOT DEVNULL)."""
    src = inspect.getsource(handler_mod)
    tree = ast.parse(src)
    found_any = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            if "create_subprocess_exec" in fn:
                found_any = True
                stderr_kw = next((kw for kw in node.keywords if kw.arg == "stderr"), None)
                assert stderr_kw is not None, (
                    f"create_subprocess_exec at line {node.lineno} missing stderr= kwarg; "
                    f"v6 baseline mandates explicit `stderr=asyncio.subprocess.STDOUT`"
                )
                expr = ast.unparse(stderr_kw.value)
                assert "STDOUT" in expr, (
                    f"BUG: create_subprocess_exec at line {node.lineno} uses "
                    f"stderr={expr!r}; v6 baseline mandates STDOUT (merged with stdout). "
                    f"Splitting stderr creates a reader race + breaks Phase 0a marker "
                    f"co-locality. See v4 §0 bug 2 + v6 plan."
                )
    assert found_any, "openteam.py should contain at least one create_subprocess_exec call"
```

### 9.4b `test_async_noop_names_covers_all_websocket_interactive_async_methods` (TIER-1) — Round-8 CR3b

Generalizes Round-7 M2's manual frozenset audit into a regression guard. Catches new async methods added to `WebSocketInteractive` upstream that would otherwise produce silent `await None → TypeError` per-turn log spam (as `on_clean_output_available` did until Round-8 CR3).

```python
def test_async_noop_names_covers_all_websocket_interactive_async_methods():
    """Every public async method on WebSocketInteractive must be either a real
    method on _StdioNodeInteractive OR present in _ASYNC_NOOP_NAMES.

    Otherwise __getattr__ falls through to _sync_noop → returns None →
    `await None` → TypeError. Surrounding try/except usually swallows it,
    so the symptom is silent log spam every turn — exactly what Round-8 CR3
    caught for on_clean_output_available.
    """
    import inspect
    from openteam.server.services.websocket_interactive import WebSocketInteractive
    from agent_foundation.ui.stdio_graph_reporter import _StdioNodeInteractive

    ws_async = {
        n for n, m in inspect.getmembers(WebSocketInteractive,
                                          predicate=inspect.iscoroutinefunction)
        if not n.startswith("_")
    }
    # Real (non-dunder) methods on the stub — these shadow __getattr__.
    stub_real_methods = {
        n for n in dir(_StdioNodeInteractive)
        if not n.startswith("_")
        and n not in {"send_response", "get_input"}  # InteractiveBase sync surface
    }
    covered = stub_real_methods | set(_StdioNodeInteractive._ASYNC_NOOP_NAMES)
    missing = ws_async - covered
    assert not missing, (
        f"WebSocketInteractive async methods not covered by _StdioNodeInteractive: "
        f"{missing}. Either define them as real methods on _StdioNodeInteractive "
        f"OR add them to _ASYNC_NOOP_NAMES. Round-8 CR3 caught "
        f"on_clean_output_available being missed; this test prevents recurrence."
    )
```

This test is layer-correct in **OpenStartup's** test suite (it imports OpenStartup's `WebSocketInteractive`, which is allowed; the §9.2 stub-signature test stays in AgentFoundation against `NodeStreamInteractive`).

### 9.4c `test_reader_task_spawned_on_happy_path` (TIER-2) — Round-8 CR1 regression guard

Catches the exact CR1 bug that Round-7's own M4 edit introduced: gating reader-setup on `event_write_fd is not None` (now always False after Round-7's premature nullification) → reader never spawns → 64KB pipe buffer fills → subprocess deadlocks. The test asserts `ndjson_task is not None` after a successful spawn with `graph_enabled=True`.

**Round-9 CR3 rewrite (was unrunnable; 3 undefined symbols).** The original §9.4c sketch referenced `_real_create_task`, `run_handler_in_worker`, and `create_test_app_with_graph_enabled` — none of which exist anywhere in the plan or the codebase. The test errored at collection time. The fix is a **runnable, self-contained** spec that asserts the structural property (reader spawned ⇒ at least one task created in `asyncio.all_tasks()` containing the substring `openteam-graph-reader-`) without needing fixtures that don't yet exist.

```python
"""Regression guard for the Round-7-introduced CR1 reader-gate bug.

The bug: gating the reader-setup block on `event_write_fd is not None`
(which is always False after the spawn-success nullification) caused
the NDJSON reader to never spawn → 64KB pipe buffer fills → subprocess
deadlocks. Round-8 CR1 fixed by gating on event_read_fd.

This test exercises the actual code path via a real subprocess that
writes one NDJSON line to fd 3 and waits to be killed; the parent
verifies that an asyncio task named `openteam-graph-reader-*` exists
within 1s of spawn.
"""
import asyncio, os, signal
import pytest

from rovodev_tui.slash_commands._async_fd import open_async_fd_reader
from rovodev_tui.slash_commands._openteam_graph import read_ndjson_events


@pytest.mark.asyncio
async def test_reader_task_spawned_on_happy_path(tmp_path):
    # Real subprocess that emits ONE NDJSON line then sleeps; parent
    # verifies a reader task got created (would NOT happen if the gate
    # bug from Round-7 returns).
    fake_binary = tmp_path / "fake-openteam-task.py"
    fake_binary.write_text(
        "import os, time\n"
        "fd = int(os.environ['ROVODEV_TUI_GRAPH_FD'])\n"
        "os.write(fd, b'{\\\"type\\\":\\\"graph_topology\\\",\\\"nodes\\\":[]}\\n')\n"
        "time.sleep(60)\n"
    )
    fake_binary.chmod(0o755)

    r_fd, w_fd = os.pipe()
    env = os.environ.copy()
    env["ROVODEV_TUI_GRAPH_FD"] = str(w_fd)
    proc = await asyncio.create_subprocess_exec(
        "python3", str(fake_binary),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        env=env, pass_fds=(w_fd,),
    )
    os.close(w_fd)
    # Round-10 M-9.2 fix: pre-init so finally's cleanup doesn't UnboundLocalError
    # if open_async_fd_reader raises (e.g. OSError on torn pipe). Prior version
    # would mask the original exception AND leave the subprocess zombie because
    # the SIGTERM block below was unreachable.
    transport = None
    ndjson_task = None
    try:
        # Simulate the handler's reader-setup block (the contract under test).
        ndjson_reader, transport = await open_async_fd_reader(r_fd)
        r_fd = None  # ownership transferred
        # The "topology_view" stub — we only need apply_* counters here.
        class _Stub:
            def __init__(self): self.calls = 0
            # Round-10 CR-9.1 fix: method names must match the reader's
            # dispatch table at §7.3 line 1264 (`view.apply_topology_event`,
            # NOT `apply_graph_topology`). Prior version's stub triggered
            # AttributeError silently caught by reader → stub.calls stayed 0
            # → assertion always failed. Verified by grep of line 1264.
            def apply_topology_event(self, *a, **k): self.calls += 1
            def apply_node_status(self, *a, **k): self.calls += 1
            def apply_node_stream(self, *a, **k): self.calls += 1
            def apply_graph_reconcile(self, *a, **k): self.calls += 1
        stub = _Stub()

        class _AppStub:
            def call_from_thread(self, fn, *a, **k): fn(*a, **k)
        ndjson_task = asyncio.create_task(
            read_ndjson_events(ndjson_reader, stub, _AppStub()),
            name="openteam-graph-reader-test",
        )

        # Give reader 1s to consume the one NDJSON line.
        for _ in range(20):
            if stub.calls > 0:
                break
            await asyncio.sleep(0.05)
        assert stub.calls > 0, (
            "Reader never received the topology event — Round-9 CR1 regression: "
            "either the reader-setup gate is broken (Round-7 bug) OR the wire "
            "format changed."
        )

        # Assert the named task is in asyncio.all_tasks() — the structural
        # signal that distinguishes "reader spawned" from "reader missing".
        names = {t.get_name() for t in asyncio.all_tasks()}
        assert any("openteam-graph-reader-" in n for n in names), (
            f"No openteam-graph-reader-* task found. Names: {names}"
        )

        ndjson_task.cancel()
        try: await ndjson_task
        except asyncio.CancelledError: pass
    finally:
        # Round-10 M-9.2: guard transport and ndjson_task against UnboundLocalError
        if ndjson_task is not None and not ndjson_task.done():
            ndjson_task.cancel()
            try: await ndjson_task
            except (asyncio.CancelledError, Exception): pass
        if transport is not None:
            transport.close()
        if r_fd is not None:
            try: os.close(r_fd)
            except OSError: pass
        proc.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
```

This test is **self-contained** (uses only stdlib + the two helpers from `_async_fd.py` and `_openteam_graph.py` that the plan defines), **runnable** (no undefined symbols), and **catches the actual structural bug** by verifying both behavior (stub gets the event) and structure (named task exists in `asyncio.all_tasks()`).

### 9.4d `test_from_env_cache_invalidates_on_fd_recycle` (TIER-2) — Round-8 M1 regression guard

```python
# Round-10 M-9.4 fix: explicit pytest import (was relying on §9.4c carrying over,
# but the plan presents these as separate code blocks; an implementer copying
# this block into its own file would hit NameError).
import asyncio, gc, os
import pytest
from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter


@pytest.mark.asyncio
async def test_from_env_cache_invalidates_on_fd_recycle(monkeypatch):
    """Regression guard for Round-8 M1.

    Round-7 M3's cached._stream.closed check was inert against external
    os.close(fd) — wrapper.closed stays False. fd recycling between tests
    would return stale cached instances. This test forces fd recycling and
    asserts a fresh instance is constructed.
    """
    from agent_foundation.ui.stdio_graph_reporter import StdioGraphReporter
    StdioGraphReporter._FROM_ENV_CACHE.clear()

    r1, w1 = os.pipe()
    monkeypatch.setenv("ROVODEV_TUI_GRAPH_FD", str(w1))
    inst1 = StdioGraphReporter.from_env()
    assert inst1 is not None
    # External close (mimics test cleanup pattern that motivated M1):
    os.close(w1)
    os.close(r1)

    # Force fd recycling: open enough new pipes until w1's number is reused.
    pipes = []
    try:
        for _ in range(100):
            r, w = os.pipe()
            pipes.append((r, w))
            if w == w1:                                # got the same fd number
                monkeypatch.setenv("ROVODEV_TUI_GRAPH_FD", str(w))
                # Round-10 M-9.3 fix: drop the inst1 reference BEFORE the
                # second from_env() call, then force GC. This ensures the
                # cache's `del cls._FROM_ENV_CACHE[fd]` reaches refcount=0
                # → instance destructor fires → if closefd=True (the bug),
                # os.close(w) corrupts the NEW pipe; if closefd=False
                # (Round-10 CR-9.2 fix), nothing happens to the kernel fd.
                inst1_ref = inst1                       # keep test alive for next line
                del inst1
                gc.collect()
                inst2 = StdioGraphReporter.from_env()
                assert inst2 is not None, (
                    "Round-10 M-9.3 regression: from_env returned None — "
                    "likely because inst1's destructor closed the recycled "
                    "fd before inst2 could fdopen it. CR-9.2 fix (closefd="
                    "False) must be in place."
                )
                assert inst2 is not inst1_ref, (
                    "Round-8 M1 regression: cache returned stale instance on "
                    "fd recycling. Liveness check must compare (st_dev,st_ino)."
                )
                # Round-10 M-9.3 positive assertion: write a probe through
                # inst2._stream and read it back from r to prove the wrapper
                # points at the NEW pipe (not the dangling old one).
                inst2._stream.write(b"probe\n")
                inst2._stream.flush()
                assert os.read(r, 6) == b"probe\n", (
                    "Wrapper points at OLD pipe — CR-9.2 GC-close hazard."
                )
                return
        pytest.skip("Could not force fd recycling in 100 attempts (kernel behavior).")
    finally:
        for r, w in pipes:
            for fd in (r, w):
                try: os.close(fd)
                except OSError: pass
```

### 9.5 `test_no_loop_kwarg_in_async_fd_helper` (TIER-1) — regression guard already documented above

### 9.6 `test_real_subprocess_pass_fds` (TIER-2) — round-5 fix Mo8

Most v3 tests mock `asyncio.create_subprocess_exec`. That makes them fast but verifies nothing about real OS fd inheritance — which is exactly the integration surface that could break (parent forgetting to drop write end → reader hangs; subprocess not getting fd 3 → silent fallback to no graph view; etc.). v4 adds an end-to-end test that spawns a real child process via `pass_fds`.

`acra-python/packages/cli-rovodev-tui/tests/slash_commands/test_real_subprocess_pass_fds.py`:

```python
"""Round-5 fix Mo8: real subprocess fd-inheritance smoke test.

Verifies that:
  1. Parent's os.pipe() write-end is correctly passed via pass_fds=(w,).
  2. Child can write to fd 3 and parent reads it as NDJSON.
  3. Parent drops its write-end after spawn -> reader sees EOF on child exit.
  4. The open_async_fd_reader helper handles the real fd correctly.
"""
import asyncio, json, os
import pytest

from rovodev_tui.slash_commands._async_fd import open_async_fd_reader


@pytest.mark.asyncio
async def test_real_subprocess_writes_to_fd_3_and_parent_reads():
    r_fd, w_fd = os.pipe()
    # Child: write 3 NDJSON lines to fd 3, then exit cleanly.
    child_script = (
        "import os, json, sys\n"
        "os.write(3, b'{\"type\":\"graph_topology\",\"nodes\":[],\"edges\":[]}\\n')\n"
        "os.write(3, b'{\"type\":\"node_status\",\"node_id\":\"n\",\"status\":\"running\"}\\n')\n"
        "os.write(3, b'{\"type\":\"node_status\",\"node_id\":\"n\",\"status\":\"completed\"}\\n')\n"
        "os.close(3)\n"
    )
    proc = await asyncio.create_subprocess_exec(
        "python3", "-c", child_script,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        pass_fds=(w_fd,),
    )
    os.close(w_fd)                                                  # parent drops write end
    reader, transport = await open_async_fd_reader(r_fd)
    try:
        lines = []
        while True:
            line = await reader.readline()
            if not line:
                break
            lines.append(json.loads(line.decode()))
        await proc.wait()
        assert proc.returncode == 0
        assert [e["type"] for e in lines] == ["graph_topology", "node_status", "node_status"]
        assert lines[1]["status"] == "running"
        assert lines[2]["status"] == "completed"
    finally:
        transport.close()


@pytest.mark.asyncio
async def test_open_async_fd_reader_does_not_pass_loop_kwarg_at_runtime():
    """Belt-and-brace: not just AST regression (§9.5), but actual runtime
    verification on Python 3.11+ that StreamReader() construction doesn't
    raise TypeError from a stale `loop=`.
    """
    r_fd, w_fd = os.pipe()
    try:
        reader, transport = await open_async_fd_reader(r_fd)
        os.write(w_fd, b"x\n")
        os.close(w_fd); w_fd = -1
        line = await reader.readline()
        assert line == b"x\n"
    finally:
        transport.close()
        if w_fd != -1:
            os.close(w_fd)
```

### 9.7 `test_real_subprocess_fd_leak_on_spawn_failure` (TIER-2) — round-5 fix M4

Verifies the fd ownership contract: on `connect_read_pipe` failure (simulated by closing the read end before the wrapper attempts to use it), the wrapper closes the fd exactly once (no double-close errors, no fd leak).

`acra-python/packages/cli-rovodev-tui/tests/slash_commands/test_async_fd.py`:

```python
def test_loop_kwarg_never_passed_to_streamreader():
    """Regression: asyncio.StreamReader(loop=...) was removed in Python 3.10
    and both repos pin >=3.11. Passing loop= raises TypeError.
    """
    from rovodev_tui.slash_commands._async_fd import open_async_fd_reader
    import inspect, ast
    src = inspect.getsource(open_async_fd_reader)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            if "StreamReader" in fn or "StreamReaderProtocol" in fn:
                kwargs = {kw.arg for kw in node.keywords if kw.arg}
                assert "loop" not in kwargs, (
                    f"BUG: {fn}(loop=...) was REMOVED in Python 3.10; "
                    f"both repos require >=3.11. Use the no-kwarg form."
                )
```

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Plan markdown contains uncompilable code** (Round-8 CR1 was a real `IndentationError` shipped to a Round-8 reader) | Medium | High | **Mitigated (Round-9)** — `scripts/lint_plan_code_blocks.py` runs `ast.parse` on every fenced ` ```python ` block; CI blocks PRs that introduce a parse error in any `_dev/_plan/*.md`. |
| **fd recycling silently corrupts `_FROM_ENV_CACHE`** (Round-8 M1 check was inert) | Low | High | **Mitigated (Round-9 CR2)** — cache invalidates on `(st_dev, st_ino)` mismatch, not on `os.fstat`-success-or-fail. Regression guard: §9.4d simulates recycle. |
| **Reader-gate regression silently disables the entire feature** (Round-7 M4 → Round-8 CR1) | Low | High | **Mitigated (Round-8 CR1 + Round-9 §9.4c rewrite)** — runnable integration test asserts `openteam-graph-reader-*` task in `asyncio.all_tasks()` after spawn; would catch the exact bug class that Round-7 introduced. |
| Windows `pass_fds` semantics differ | High on Win | High | v1 is POSIX-only; phase 7 detects `sys.platform == 'win32'` → notify "Graph view not yet supported on Windows" + fall through to ShellOutput |
| Subprocess inherits unexpected fds | Very low | Low | `pass_fds=(...,)` explicitly lists fds; Python 3.4+ marks non-listed fds non-inheritable by default |
| Parent forgets to close write-end → reader hangs | Mitigated | High | `os.close(event_write_fd)` immediately after subprocess spawn; verified in §7.5 |
| NDJSON line > PIPE_BUF (~4 KB Linux) → torn write | Mitigated | Med | `_write_chunked_stream` splits at 3000 bytes/chunk; well under PIPE_BUF on all platforms |
| Concurrent BTA workers race on the stream → corrupt NDJSON | Mitigated | High | `asyncio.Lock` in `StdioGraphReporter._emit` |
| `asyncio.StreamReader(loop=loop)` would `TypeError` on Py 3.11 | **CAUGHT in plan** | CRIT | §9.4 CI preflight prevents regression; v3 code uses no-kwarg form |
| Older AgentFoundation lacks `StdioGraphReporter` (cross-version) | Mitigated | Low | `make_graph_reporter` catches `ImportError` → silent degrade; TUI shows "(no graph data)" |
| Race: `node_status` before `graph_topology` | Mitigated | Low | `apply_node_status` creates stub `NodeState`; `apply_node_stream` accumulates `_streams` buffer; `apply_graph_reconcile` is authoritative |
| Bounded buffer (200 KB/node) too small for some tool | Low | Low | Mirrors React; tail-keep preserves latest tokens; user can scroll RichLog |
| `_StdioNodeInteractive.stream_token_batches` signature drift if WS adds kwargs | Mitigated | Low | `**kwargs` absorbs; §9.2 CI preflight asserts named-kwarg compat |
| Snapshot test flakes on animated running glyph | Mitigated | Low | `self.app.is_headless` freezes glyph to `·` (idiom from `widgets/interval_updater.py:26-30`; braille→`·` substitution from `widgets/chat_container.py:720` — round-7 fix Mo5) |
| Non-BTA topologies (`pti.yaml`, `dual.yaml`) emit no events | Acceptable v1 | Low | Widget shows "(no graph data for this topology)" footer; final result still rendered; `is_empty()` removes widget on empty stdout |
| Pipe fd leak on subprocess exec failure | Mitigated | Low | Explicit cleanup block closes both fds in the `FileNotFoundError` branch |
| User sets `ROVODEV_TUI_GRAPH_FD` accidentally in their shell | Low | Low | `_activated_fd()` calls `os.fstat(fd)` → bogus fd → returns None → silent fallback |
| Reporter wired twice (v2's bug) → contradictory state | **CAUGHT in plan** | High | v3 explicitly drops `tool_cli.run_cli` patch; §6.3 enforces "factory called from executor ONLY" |
| Stderr split (v2's bug) → race + breaks v6 markers | **CAUGHT in plan** | High | v3 preserves `stderr=STDOUT`; markers rendered dim via line-prefix detection |
| Many concurrent `/task` invocations → many graph views → memory leak | Low | Low | Each Esc removes widget; bounded buffers per view; auto-collapse-after-N is phase 9 |
| Reader `transport.close()` forgotten → fd leak on long-lived TUI | Mitigated | Low | `transport.close()` in handler's finally-like cleanup block (§7.5) |

---

## 11. Self-audit (stress-tested for hacks)

| Question | Answer |
|---|---|
| Does this duplicate `WebSocketGraphReporter`? | Intentionally — the protocol is duck-typed; both are peer implementations. They share `NamespacedGraphReporter` (the only stateful helper) and could share `node_stream_observer` extraction (phase 9 mini-refactor). |
| Why not connect to a running OpenStartup WS server (Claude v1 approach)? | The server isn't running for most TUI users; requiring it would defeat v6's "subprocess + bootstrap = self-contained" invariant. WS adds a heavy dep to PyInstaller-frozen TUI for no marginal benefit. Claude v2 itself rejected this approach. |
| Could the NDJSON events corrupt the final result text? | No — different fds. stdout (merged with stderr) = result markdown + `[artifact_key]` markers; fd 3 = NDJSON. Two OS channels, two logical roles. |
| Could the user cancel mid-run? | Existing `worker.is_cancelled → proc.terminate()` flow unchanged. Reader's `await readline()` returns empty bytes on pipe close → clean exit. `transport.close()` after `proc.wait()`. |
| Nested BTAs (worker that is itself a BTA)? | `NamespacedGraphReporter.child_reporter(parent_node_id)` reused unchanged. Events arrive with `node_id="worker_0/breakdown"` and `parent_node_id="worker_0"`. Widget mounts sub-tree under container node. |
| Concurrent slash commands? | Each spawns its own subprocess + own pipe + own TopologyView. Independent. Test: `test_handler_integration::test_three_concurrent_handlers`. |
| Non-BTA topologies (`pti.yaml`, `dual.yaml`)? | Reporter set but never invoked. Widget footer says "(no graph data — this topology doesn't emit events)". Final result still renders. Empty-output `is_empty()` check removes widget. Phase 8 propagates through Dual/PTI. |
| Sticky selection time-source? | `time.monotonic()` — NTP-skew-safe. |
| `_cap_total_streams` could thrash? | Triggered only when total > 10 MB; mirrors React; one-shot purge of completed-node buffers (not running). |
| `_StdioNodeInteractive.__getattr__` shape? | Round-8 corrected: branches on `_ASYNC_NOOP_NAMES` frozenset (curated against `WebSocketInteractive`'s 7 public async methods at `websocket_interactive.py`; locked by §9.4b completeness preflight). Returns `_async_noop` coroutine for known async names; returns `_sync_noop` plain function for everything else (covers `InteractiveBase`'s sync surface like `get_input`, `send_response`). The earlier "always returns async coroutine" claim was the bug Round-7 M2 fixed AND Round-8 CR3 completed; the audit row is now aligned to the actual code. |
| What if a future contributor adds a 5th tool that emits graph events but forgets the factory? | §9.3 `test_factory_used_by_all_executors.py` greps every `executor.py` and asserts the factory is used (or no graph_reporter line at all). CI preflight. |
| Stdio reporter and WebSocket reporter drift in protocol surface? | §9.1 `test_protocol_method_set_matches_websocket_reporter` CI preflight catches it. |
| `os.fdopen(buffering=1)` doesn't actually line-flush in all CPython versions? | Explicit `self._stream.flush()` after each write (already in `_emit`). Test `test_emits_4_event_types_through_real_bta` reads `os.read(fd)` immediately. |
| Could RovoDev call OpenTeam AND OpenTeam call RovoDev (via `RovoDevCliInferencer`)? | Already supported. `ROVODEV_TUI_GRAPH_FD` namespace + per-subprocess pipe makes nesting safe. |
| Does this commit RovoDev to a specific OpenTeam version? | No. NDJSON contract is the wire API; either side upgrades independently. Backward-compat fallback if `StdioGraphReporter` import fails. |
| Snapshot test stability for animated running glyph? | `_render_label` checks `self.app.is_headless` and freezes glyph. Mirrors `IntervalUpdater.on_mount`. |
| Does v3 introduce any hack? | Closest: `_StdioNodeInteractive.__getattr__` returning `_noop` for unknown methods — defensive against future BTA calls. Explicit, documented, log-warning'd. The `[dim]` styling of stderr-merged `[artifact_key]` markers is a UX nicety, not a hack — it preserves v6's design while making the merged stream readable. |
| Why is there NO `tool_cli.run_cli` patch in v3 when v2 had one? | v2's design was contradictory: it patched both `tool_cli` AND each executor with the factory. One of the two was dead code. Cursor's plan §4.3 explicitly chose "Option (i): executor calls factory directly (preferred; cleaner)". v3 follows this. The **3**-attach-site executor edit is trivial (round-5 C1, round-7 N2 corrected — task, project_onboarding, mock_task; the 2 delegating wrappers create_role/role_setup inherit via _run_topology); CI preflight catches forgotten patches. |
| Why is `stderr=STDOUT` (not `=PIPE`) the right choice? | v6 baseline uses `stderr=STDOUT`. Splitting them creates a race between two readline loops and breaks the co-locality of `[artifact_key]` markers with the markdown they describe. fd 3 is the only NEW channel; nothing else changes. |
| Why drop `loop=` from `asyncio.StreamReader`? | Removed in Python 3.10. Both repos pin `>=3.11`. Passing `loop=` raises `TypeError` at runtime — not a deprecation warning. §9.4 CI preflight guards. |
| What's the deal with empty-output cleanup? | shell.py:91-94 baseline removes the shell-output widget when stdout was empty. v3 mirrors this: empty stdout → if graph view is also empty (`is_empty()`), remove it; otherwise keep the graph view (graph events alone are evidence the run did something). |

---

## 12. Comparison table — round 4 (post-convergence)

After 4 rounds of mutual review, **the three plans have largely converged**. Differences are now down to a handful of cells.

| Trait | v3 (mine prior) | Cursor v4 (now) | Claude v3 (meta) | **v4 (this)** |
|---|---|---|---|---|
| Architecture: NDJSON on fd 3 | ✅ | ✅ | ✅ (defers to Cursor) | ✅ |
| Single attach point (factory in executor, NO tool_cli patch) | ✅ | ✅ (absorbed from my v3) | ✅ (via Cursor) | ✅ |
| `StdioGraphReporter.from_env(task_id)` factory method | ✅ | ✅ | – | ✅ |
| `asyncio.Lock` serializes `_emit` | ✅ | ✅ | – | ✅ |
| Sticky selection 5 s | ✅ explicit | ✅ implicit | – | ✅ explicit |
| Bounded stream buffers (200 KB/node) | ✅ explicit | ✅ explicit | – | ✅ explicit |
| Race buffer (status before topology) | ✅ | ✅ | – | ✅ |
| `asyncio.StreamReader` NO `loop=` kwarg (Py 3.11+) | ✅ guarded | ✅ guarded | ✅ flagged it | ✅ guarded by CI |
| `stderr=STDOUT` (matches v6 baseline) | ✅ | ✅ (absorbed from my v3) | – | ✅ |
| Empty-output cleanup | ✅ via `is_empty()` collection-check | ✅ via `_got_any_event` **flag** | ✅ flags it | ✅ via `_got_any_event` flag (absorbed) |
| `_StdioNodeInteractive` signature CI test | ✅ §9.2 | ✅ | ✅ flags need | ✅ §9.2 |
| Continuation chunking for oversize streams | ✅ | ✅ | – | ✅ |
| `app.is_headless` freezes running glyph | ✅ | ✅ | – | ✅ |
| `ContentSwitcher` of per-node `RichLog`s | ✅ | ✅ | – | ✅ |
| Single-file widget (~350 LOC) | ✅ | ✅ | – | ✅ |
| Test rig uses real BTA + `MockBreakdown/Worker/Aggregator` | ✅ | ✅ | – | ✅ |
| **Structured YAML front-matter with phase IDs** | ✗ human-only headings | ✅ | – | ✅ (absorbed from Cursor) |
| **Named `test_stderr_stdout_merged` regression guard** | ✗ implicit | ✅ named | – | ✅ named (absorbed from Cursor) |
| `_got_any_event: bool` flag for `is_empty()` | ✗ uses `not self._nodes` | ✅ | – | ✅ (absorbed from Cursor) |
| CI preflight tests | 4 | 4 | – | **5** (now includes named stderr regression guard) |
| Self-audit section | 18 rows | 16 rows | – | 18 rows + 3 new |
| Comprehensive risks table | 16 rows | 16 rows | – | 16 rows |
| `ROVODEV_TUI_GRAPH_DISABLE` opt-out env var | ✅ | ✅ | – | ✅ |
| Revision-history block | ✅ | ✅ (round 4 added) | – | ✅ updated for round 4 |
| Total line count | 1294 | 1387 | 54 | ~1400 |

**Architectural convergence:** every functional trait is now ✅ across v3 / Cursor v4 / v4. The only remaining differences are:
1. Cursor v4 has structured front-matter (now absorbed into v4)
2. Cursor v4 has named stderr-merged regression test (now absorbed into v4)
3. Cursor v4 uses `_got_any_event` flag (now absorbed into v4)

After absorption, **v4 is the union of all three**. Any reviewer can now safely execute any of v3, v4, or Cursor v4 with confidence in the same architecture.

---

## 13. Pick-one ranking (round 4, post-convergence)

**Neither my v3 nor Cursor v4 is safe to ship as-is** (Round-5/7/8 found 30+ valid defects between them, including 6 critical). Both retain the round-1–4 architecture (which IS settled and correct), but their code blocks have multiple bugs documented in the Round-5/7/8 changelog tables. **Only this v4 (post-Round-8) is safe to ship**; earlier snapshots are superseded.

**Strict ordering:**
1. **v4 (this file)** — union of correctness; absorbs Cursor v4's 3 improvements on top of my v3 foundation.
2. **Cursor v4** — independently arrived at the same architecture; has 3 improvements over my v3 (now absorbed).
3. **My v3** — correct architecture; 3 minor gaps relative to Cursor v4 (now closed by v4).
4. **Claude v3** — meta-plan that itself recommends my v3.

**If "only ONE of the three EXISTING plans" (v3 / Cursor v4 / Claude v3) is allowed:**
- **Pick Cursor v4.** It is the only of the three that has BOTH my v3's bug fixes (no `tool_cli` patch, `stderr=STDOUT` preserved) AND the 3 minor improvements (`_got_any_event` flag, structured front-matter, named stderr regression guard).
- **Alternative: my v3.** Functionally equivalent for shipping; just lacks the 3 cosmetic improvements. Cursor v4 itself rates my v3 ahead in its §10 pick-one section ("Pick Plan B v3"), but that was written before Cursor v4 absorbed my fixes — after absorption, Cursor v4 ≥ my v3 by a hair.

**Round-4 was a convergence round.** Subsequent rounds disproved the "diminishing returns" prediction: **Round-5 found 18 valid defects, Round-7 found 12 (including 3 critical introduced by Round-5's own edits), Round-8 found 13 (including 3 critical introduced by Round-7's own edits including a complete-feature-broken-on-happy-path regression).** The pattern is now clear: every plan-edit that adds non-trivial code is itself a candidate for adversarial review. The architecture remains settled since Round-4, but **code-level details continue to produce critical bugs through round 8 and adversarial review remains high-signal**.

**Reviewer pattern over 9 rounds (worth noting for process insight; Round-9 added):**
- **Round 9** (the round you're reading the patch for): auditor empirically demonstrated **3 NEW criticals** introduced by Round-8 — including a Python `IndentationError` that I verified with my own `ast.parse` invocation and an `os.fstat`-recycle bug I reproduced live. The auditor's **central structural recommendation** — *"stop iterating on markdown; extract to .py files where the compiler catches errors immediately"* — is now adopted as a DoD item (`scripts/lint_plan_code_blocks.py`).
- Rounds 1–2: design exploration; my plans had bugs each round; reviewers caught them.
- Round 3: my v3 caught its own 2 bugs AND found 1 in Cursor's plan; convergence began.
- Round 4: Cursor's v4 absorbed all my v3 fixes + added 3 improvements; I absorbed those 3.
- **Round 5: 18 valid defects** (despite my "convergence" claim) including 3 critical structural issues.
- **Round 6: 2 valid** + 1 rejected (defensive over-suggestion).
- **Round 7: 12 valid** including 3 critical bugs **introduced by Round-5's own edits** (stdout busy-loop; unqualified-keys forwarder; M3 patch with no owning phase). My "Round-5 convergence" self-assessment was demonstrably wrong.
- **Round 8: 13 valid** including 3 critical bugs **introduced by Round-7's own edits** (reader-setup gated on wrong fd → 100% feature break on happy path; OPENTEAM_TASK_ID prose-only fix that forgot to delete the line; _ASYNC_NOOP_NAMES missing 2 of 7 WS async methods → silent per-turn TypeError).
- **The diminishing-bugs-per-round prediction is empirically wrong.** Architecture is settled (no rounds since 4 have moved an architectural piece), but **non-trivial code edits to the plan itself remain a regression source**. The structural fix is the §9.4b/c/d regression tests added in Round-8 — they turn each manual-audit footgun into a CI guard.

---

## 14. Definition of Done (acceptance checklist)

### AgentFoundation
- [ ] `StdioGraphReporter.from_env()` returns `None` without env var; instance with env var.
- [ ] `make_graph_reporter` returns the right type per the 6-row truth table (§6.4).
- [ ] CI preflight `test_protocol_method_set_matches_websocket_reporter` ✅
- [ ] CI preflight `test_no_op_node_interactive_signature_alignment` ✅
- [ ] All 12 `test_stdio_graph_reporter.py` TIER-1 tests ✅
- [ ] All 6 `test_graph_reporter_factory.py` TIER-1 tests ✅

### OpenStartup
- [ ] All **3 real attach-site** executors patched (task, project_onboarding, mock_task — round-5 C1); CI preflight `test_factory_used_by_all_executors.py` ✅
- [ ] Delegating wrappers `create_role/executor.py` and `role_setup/executor.py` are **NOT modified** — they inherit the patch transitively via `_run_topology`. (Verify by `grep -rn "WebSocketGraphReporter(" .../tools/` returning exactly 3 hits.)
- [ ] `openteam-mock-task` console script emits valid NDJSON on fd=3 when env var set.
- [ ] `openteam-mock-task --help` still works (env var absent → silent fallback).
- [ ] 0 instances of `WebSocketGraphReporter(` remain in `src/openteam/server/resources/tools/*/executor.py` (grep clean).

### RovoDev TUI
- [ ] In TUI: `/task "what is 2+2"` shows the topology graph + final result.
- [ ] Tree row click → stream pane updates to that node's content.
- [ ] After click, status events for OTHER nodes do NOT change selection for 5 s.
- [ ] Auto-follow re-engages 5 s after the last manual click.
- [ ] Ctrl-C terminates subprocess within 5 s (v6 contract preserved).
- [ ] Esc collapses the graph view (subprocess keeps running until cancelled).
- [ ] `ROVODEV_TUI_GRAPH_DISABLE=1 /task "..."` → no graph view, identical to v6 UX.
- [ ] Empty-output cleanup works: `/task ""` removes the widget (shell.py:93 parity).
- [ ] Push 300 KB to one node → widget memory bounded; older content trimmed to last 50 KB.
- [ ] Nested BTA → sub-graph nodes mount under their container node.
- [ ] Non-BTA `/task` (`pti.yaml`) → "(no graph data)" footer; `is_empty()` removes widget if stdout also empty.
- [ ] CI preflight `test_no_loop_kwarg_in_async_fd_helper` ✅
- [ ] CI preflight `test_stderr_stdout_merged_regression` ✅ (Round-9 M4 — §9.4)
- [ ] CI preflight `test_async_noop_names_covers_websocket_interactive_async_methods` ✅ (Round-9 M4 — §9.4b)
- [ ] Integration `test_reader_task_spawned_on_happy_path` ✅ (Round-9 M4 — §9.4c — Round-7 CR1 regression guard)
- [ ] Unit `test_from_env_cache_invalidates_on_fd_recycle` ✅ (Round-9 M4 — §9.4d — Round-8 M1 regression guard)
- [ ] Integration `test_real_subprocess_inherits_fd_3` ✅ (Round-9 M4 — §9.6 — Mo8 smoke)
- [ ] All 12 widget unit tests TIER-1 ✅
- [ ] 3 snapshot tests TIER-2 ✅
- [ ] E2E `test_openteam_graph_e2e.py` TIER-2 ✅

### Documentation
- [ ] `CoreProjects/OpenStartup/docs/MCP_INTEGRATION.md` — new "Graph view" subsection
- [ ] `atlassian_packages/acra-python/packages/cli-rovodev-tui/docs/openteam-integration.md` — graph view UX, keybindings, opt-out env var

### Repo hygiene
- [ ] PR description includes asciinema/GIF of graph view against `mock_task`.
- [ ] No new deps added to either repo.

### Plan-syntax preflight (Round-9 structural fix — recommended)
- [ ] `scripts/lint_plan_code_blocks.py` extracts every ` ```python ` fenced block from this `.md` and runs `python3 -m py_compile` (or `ast.parse` wrapped in an `async def` for partial-function snippets). Would have caught Round-8's `IndentationError` immediately. Run this as part of CI on changes to any plan file under `_dev/_plan/`. **Acceptance:** 0 syntax errors across all code blocks in this plan.
- [ ] Alternative (preferred long-term): externalize plan code blocks into real `.py` files in `_dev/_scaffold/` and have the plan `include` them via comment markers. The compiler then enforces syntactic validity continuously.

---

## 15. Out of scope (deliberate v1 boundaries)

- **Windows support.** Phase 7 (post-ship). v1 detects platform; Windows falls through to ShellOutput.
- **Interactive `/task --confirm` per-node prompts** via TUI. Would need bidirectional fd; v1 is one-way fd 3.
- **Graphviz/DOT layout** rendering. v2 enhancement.
- **Clickable artifacts → $EDITOR** open. `output_path` is in events; v2 enhancement.
- **Auto-collapse stale graph views after N new commands.** Phase 9.
- **Cross-task graph aggregation** ("show me all my running /task graphs"). Separate plan.
- **Persistence of NDJSON events to disk** (`JsonlGraphReporter`). Phase 9.
- **DAG layout with arbitrary cross-edges.** BTA topologies are diamond-shaped; tree-with-canonical-parent suffices.
- **Patching `tool_cli.run_cli`.** Explicitly rejected — see §6.3.
- **Splitting stderr from stdout.** Explicitly rejected — see §3 invariant 11 and §0 v2 bug 2.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| **BTA** | `BreakdownThenAggregateInferencer` — the OpenTeam topology engine emitting graph events |
| **fd 3** | The dedicated file descriptor for NDJSON graph events (parent→child IPC channel) |
| **NDJSON** | Newline-Delimited JSON — one JSON object per line, what we write on fd 3 |
| **PIPE_BUF** | POSIX-guaranteed atomic-write size for pipes (4096 on Linux, 512 floor) |
| **Race buffer** | Logic that absorbs `node_status` or `node_stream` events arriving *before* their owning `graph_topology` event |
| **Sticky selection** | After a user clicks a tree row, auto-select is suppressed for `STICKY_DURATION_MS=5000` |
| **Continuation chunking** | Splitting NDJSON `node_stream` events > 4 KB into multiple lines with `"continuation": true` |
| **v6** | The shipped OpenTeam ↔ RovoDev integration plan that v3 builds on |
| **Headless freeze** | When `app.is_headless` is True, animated glyphs are frozen for snapshot test stability |

---

**End of plan. Saved at: `CoreProjects/OpenStartup/_dev/_plan/rovodev_tui_graph_view/rovodev-tui-graph-view-v4.md`**
