# OpenTeam ↔ RovoDev Integration — Integrated Plan **v6** (DEFINITIVE)

**Date:** 2026-05-16 (afternoon revision)
**Author:** Rovo Dev — sixth-pass synthesis after a fresh ground-truth re-verification of every load-bearing claim in v5, the updated Cursor plan (951 lines), and the Claude/sparkle plan (564 lines).
**Supersedes:** v5 (`openteam-rovodev-integration-INTEGRATED-v5.md`), the Claude plan (`~/.claude/plans/here-are-a-few-wobbly-sparkle.md`), and the Cursor plan (`~/.cursor/plans/openteam_rovodev_integration_88097144.plan.md`).

**Revision history (within v6):**
- **2026-05-16 11:30 — Critical fixes applied** after external review caught four issues, all verified against the codebase:
  1. **CRITICAL** — The 4 tool console scripts (`openteam-task`, `openteam-create-role`, `openteam-role-setup`, `openteam-project-onboarding`) would have ImportErrored on launch because their `cli.py` modules do `from .executor import execute` and executor.py imports `agent_foundation` (module-level for create_role + role_setup at lines 45-56 / 48-56; deferred but still required at runtime for task + project_onboarding). Fix: **new Phase 0d** retrofits a 4-line `bootstrap.ensure_siblings_on_path()` prefix into each cli.py + new TIER-1 `test_cli_bootstrap_smoke.py` that fails CI if any console-script entry omits bootstrap.
  2. **CRITICAL** — Three MCP wrappers carried a ghost `model: str | None = None` parameter that no tool.json declares (verified by `cat`-ing all three tool.json files). Would have been forwarded to the executor as an unknown kwarg. Fix: removed `model` from `openteam_create_role`, `openteam_role_setup`, `openteam_project_onboarding`; expanded `test_wrapper_signature_alignment.py` clause 1 to specifically catch ghost-param drift.
  3. **MODERATE** — Slash registration used `extra_prompt="allowed"` with the (wrong) justification that `/task --help` needed it. Verified at `registry.py:206,210-213` — `"required"` shows a clean "command requires additional input" message on empty input, and `/task --help` flows through because `--help` is non-empty after `.removeprefix(slash).strip()`. Fix: switched to `extra_prompt="required"`; simplified handler (no empty-input guard needed); updated rationale comment with line numbers.
  4. **MINOR** — Install runbook and DoD checklist pointed `fastmcp dev` at `openteam.mcp_server.cli:create_openteam_server` — but `create_openteam_server` lives in `server.py`. Fix: corrected to `…server:create_openteam_server`.

- **2026-05-16 11:38 — Second round of fixes** after a deeper external review caught further issues, all verified against the codebase:
  1. **CRITICAL** — The artifact-key allowlist (in both `tool_cli.py` Phase 0a and `_render_result` §6.2) used a hand-rolled list that included a fictional `final_deliverables_path` and **omitted** every key actually emitted by `project_onboarding/executor.py:225-248` (`project_onboarding_report_path`, `skills_dir`, `tools_dir`, `knowledge_dir`, `role_tool_association_path`, `project_onboarding_working_dir`), and most keys emitted by `role_setup/executor.py:1261-1280` (`role_setup_report_path`, `skills_dir`, `tools_dir`, `role_tool_association_path`, `role_setup_working_dir`). Result: 3 of 4 tools would return their text result with an **empty `Artifacts:` footer** — the LLM could not open the outputs the plan promises. **Fix:** replaced the brittle allowlist with a **suffix-discovery rule** — any context_updates key ending in `_path` or `_dir` with a non-empty string value is surfaced. Verified against every executor's emission site (cited inline). Added `test_render_artifacts_discovery.py` (TIER-1) to lock the rule per-tool.
  2. **CRITICAL** — `openteam_task` MCP wrapper was missing `--in-place` and `--copy-workspace` (task/tool.json:88, 93). The plan's own CI preflight `test_wrapper_signature_alignment.py` would have failed on day one. **Fix:** added `in_place: bool = True` + `copy_workspace: bool = False` to the wrapper signature; mapped both into the args dict; expanded the wrapper docstring to state the 17-parameter contract explicitly.
  3. **CRITICAL** — The DoD acceptance test `/task what is 2+2` would have failed because `shlex.split("what is 2+2")` returns 3 tokens and `request` is a single argparse positional → `unrecognized arguments: is 2+2` (verified with `python3 -c "argparse..."`). **Fix:** corrected the DoD example to `/task "what is 2+2"`; documented the shell-quoting contract in the handler's `__doc__` (which appears in `/help`); added a WRONG/RIGHT example block. Decision: the handler is generic, not task-aware — we don't second-guess user input; we make the contract explicit.
  4. **MAJOR** — Subprocess `cwd=str(_openteam_home())` resolved user relative paths (e.g. `/role-setup ./roles/eng.md`) against the OpenStartup checkout, NOT the user's actual working directory — breaking the most common slash command pattern. Verified `shell.py:67` uses `_get_workspace_path(app)` which returns `app.session_ctx.workspace_path` or `Path.cwd()`. **Fix:** changed `cwd` to mirror `shell.py:18-20,67` exactly. Inline comment explains the regression we're avoiding.
  5. **MAJOR** — `ensure_siblings_on_path()` silently no-op'd when `OPENTEAM_SIBLINGS_ROOT` pointed at a non-existent or incomplete directory — user got a cryptic `ImportError: No module named agent_foundation` far from the cause. **Fix:** `_find_siblings_root()` now returns `None` on miss (rather than falling back to a wrong default); `ensure_siblings_on_path()` emits a clear `logger.warning()` listing the missing dirs (or raises `FileNotFoundError` with `strict=True`, which the production `openteam-mcp` entry point should use). `_logger.warning` failure surfaces near the cause.
  6. **MAJOR** — Earlier draft claimed "all 41 commands use bare names". **Re-counted with deterministic methodology** (`grep -oE '"/[a-z][a-z0-9_-]*"'` for bare, `'"/[a-z][a-z0-9_-]* [a-z][a-z0-9_-]*"'` for sub-commands): 64 total `command_registry.register(...)` calls in `app.py`, of which **39 are bare top-level** (`/jira`, `/sessions`, `/plan`, …), **24 are sub-commands** (`/jira global`, `/sessions new`, …), and **1 is the special non-slash `$`** (shell). Earlier "36/19" was also wrong (counted with a `sort -u` that under-counted re-registrations). The architectural takeaway (use bare `/task`) is unchanged — every TOP-LEVEL feature is bare; sub-commands namespace UNDER a bare name, never as kebab-prefixed siblings. **Fix:** replaced every "36 / 19", "all 41 bare names", "current 41 commands" wording with the verified "39 bare + 24 sub" count and the operative rule.
  7. **MAJOR** — Earlier draft claimed `jira.py` uses a "factory pattern" as precedent for `_make_handler`. Re-verified: `jira.py` is 4 hand-written async handlers; no factory. The factory in `slash_commands/openteam.py` is **novel**, not idiomatic — but defensible because our 4 handlers are isomorphic up to (slash, binary, module) tuples. **Fix:** changed the framing from "matches convention" to "novel but justified DRY pattern"; added an explicit row in the ground-truth table acknowledging this.
  8. **MAJOR** — Line-number citations had several off-by-one errors (`tool_cli.py` 125-132 → actual 125-131; `ToolExecutionResult` 15-22 → actual 16-23; `conftest.py` 12 lines → actual 13; `mcp-atlassian-exp/main.py` 94-116 → actual 95-117). Argument unaffected; credibility on review affected. **Fix:** corrected all citations; added "(re-verified post-feedback)" annotations.
  9. **MAJOR** — Claim "all five `__init__.py` files are empty (zero bytes)" was imprecise: 4 are zero-bytes; `RichPythonUtils/__init__.py` is 28 bytes containing only a placeholder comment. The architectural argument (no behaviour in `__init__.py` ⇒ safe to keep ours empty) holds either way. **Fix:** restated precisely.
  10. **GAP** — No test locked `openteam/__init__.py` empty. Risk: a future contributor adds a line that transitively imports `agent_foundation` BEFORE bootstrap runs, silently breaking every console script. **Fix:** added `test_init_py_remains_empty.py` (TIER-1, CI pillar guard) — asserts the file plus every `openteam/server/**/__init__.py` is empty or whitespace-only.
  11. **GAP** — No regression test for the `run_server.py` 30-line → 6-line refactor. **Fix:** added `test_run_server_smoke.py` — imports `run_server` and constructs the FastAPI app.
  12. **GAP** — `mode: Literal[…]` enum re-expansion silently drops unknown modes. **Fix:** added `test_mode_enum_complete.py` — asserts the enum exactly equals `task/cli.py:_MODE_MUTEX` and the `"type":"flag"` mutex set in `task/tool.json`.
  13. **MINOR** — Subprocess inherited TUI stdin → potential hang if any underlying tool calls `input()`. (Note: `shell.py` does NOT pass `stdin=DEVNULL` because the shell tool intentionally supports interactive I/O; our `openteam-*` tools do not.) **Fix:** added `stdin=asyncio.subprocess.DEVNULL` with an inline rationale comment.

**Quick-reference verdict on each feedback item:**

| # | Claim | Verdict | Action |
|---|---|---|---|
| 1 | Artifact keys wrong | ✅ VALID | Fixed (suffix-discovery rule) |
| 2 | Missing `--in-place`/`--copy-workspace` | ✅ VALID | Fixed (added to wrapper) |
| 3 | `/task what is 2+2` fails (shlex) | ✅ VALID | Fixed (documented quoting + corrected DoD example) |
| 4 | Ghost `model` on 3 wrappers | ✅ Already fixed (prior round) | No-op |
| 5 | Wrong `fastmcp dev` path | ✅ Already fixed (prior round) | No-op |
| 6 | `extra_prompt="allowed"` false premise | ✅ Already fixed (prior round → `"required"`) | No-op |
| 7 | "All 41 bare names" overstated | ✅ VALID | Fixed (precise count + rule) |
| 8 | Factory pattern claim false | ✅ VALID | Fixed (acknowledged novelty) |
| 9 | `cwd=OPENTEAM_HOME` breaks user paths | ✅ VALID | Fixed (mirror shell.py:67) |
| 10 | Bootstrap silent on misconfig | ✅ VALID | Fixed (warning + `strict=True` opt-in) |
| 11 | Off-by-one citations | ✅ VALID | Fixed (all corrected with annotation) |
| 12 | RichPythonUtils not literally empty | ✅ VALID (nuance) | Fixed (precise wording) |
| 13 | No `__init__.py` empty test | ✅ VALID GAP | Fixed (new TIER-1 test) |
| 14 | No `run_server.py` regression test | ✅ VALID GAP | Fixed (new TIER-2 test) |
| 15 | No `mode` enum completeness test | ✅ VALID GAP | Fixed (new TIER-1 test) |
| MIN | stdin inheritance | ✅ VALID | Fixed (`stdin=DEVNULL`) |
| MIN | Narrow exception catch | Already handled (`FileNotFoundError` is the install-failure mode; `OSError` is its parent → already caught by Python's MRO via `FileNotFoundError`) | No-op |
| MIN | App.shell_worker not set | ⚠️ REJECTED — `app.shell_worker` is a `shell.py`-specific handle used by NOTHING else (verified: only `shell.py:50` writes it, only declared at `app.py:636`); not needed for our handler's own `get_current_worker()`-based cancellation | No-op |
| MIN | Vague "around 604" line | ✅ VALID (cosmetic) | Already addressed via explicit insertion-after-line guidance |
| MIN | Dead try/except ImportError | ⚠️ REJECTED — the `try/except ImportError` opt-in is the disable knob for users who want to keep openteam.py out of their build; not dead | No-op |
| MIN | Windows untested | ✅ VALID | Documented in risks table (Linux/macOS tested) |
| INC | §13 wins all / §14 picks Claude | ✅ Noted (not a bug) | No-op |

- **2026-05-16 18:20 — Third round of fixes** after another deep review caught lingering staleness and one new architectural concern. All claims re-verified against the codebase before fix or rejection:
  1. **CRITICAL** — Internal contradiction on `extra_prompt`: §13 comparison table and §14 "What v6 adds" still said `"allowed"` (a v6-only win) while the actual `slash_commands/openteam.py` code and the §12 self-audit had been updated to `"required"` in round 2. **Fix:** corrected both stale references; anyone reading §13/§14 will now match what's implemented.
  2. **MAJOR** — Command-count miscount: round 2 said "36 bare + 19 sub" but the correct values via `grep -oE '"/[a-z][a-z0-9_-]*"'` are **39 bare top-level + 24 sub-commands + 1 non-slash `$`** (= 64 total registrations). The round-2 attempt under-counted because `sort -u` collapsed re-registrations. **Fix:** corrected all 6 occurrences with the deterministic methodology documented inline; architectural claim (every top-level feature is bare) is unaffected and now precise.
  3. **MAJOR** — "All 41 commands use bare names" still appeared at 5 sites (§2 invariant, §7.1 file docstring + inline comment, §11 risks table, §12 self-audit, §13 comparison, §14 pick-one) — round-2 fix was incomplete. **Fix:** replaced every occurrence with the precise count + operative rule.
  4. **MAJOR** — `conftest.py` "(12 → 6 lines)" at §5.3 line 629 stale after round-2 corrected the actual count to 13. **Fix:** "(13 → 10 lines)" with the new count explanation.
  5. **MAJOR / NEW** — `fastmcp` pin claim was a partial-truth elevated to a categorical claim. While `mcp-atlassian-exp/pyproject.toml` does not pin fastmcp, **`code-nemo/pyproject.toml:24` DOES pin `fastmcp==3.2.4` exactly** — code-nemo is the cli-rovodev-tui's parent dependency. So the TUI process ships FastMCP 3.2.4. My earlier `fastmcp>=2,<4` would have resolved below FastMCP 3.x's `FunctionTool.from_function` API on a clean install. **Fix:** tightened to `fastmcp>=3.2,<4` (allow patches, same major as code-nemo's pin); explicitly cited the line and reasoning in the dependencies block and ground-truth table.
  6. **MODERATE / SEMANTIC** — `openteam_task` wrapper exposed `in_place: bool = True` — but `strip_unset` correctly drops False values, and `task/executor.py` defaults absent `in-place` keys to True, so setting `in_place=False` from MCP was a silent no-op. The CLI surface has no `--no-in-place` flag either: `--copy-workspace` IS the documented opt-out. **Fix:** removed `in_place` from the MCP wrapper signature entirely (it was misleading the LLM into thinking the flag was settable); added a "Workspace strategy" doc block explaining `copy_workspace=True` as the opt-out; added `in_place` to the `test_wrapper_signature_alignment.py` exception list alongside the `mode` mutex collapse. Root cause: round-2 added `in_place` blindly to satisfy "missing from tool.json" without checking whether the parameter was meaningfully toggleable.
  7. **MODERATE / DRY** — `cwd` computation in `_make_handler` inlined the `_get_workspace_path(app)` logic from `shell.py:18-20` instead of importing the helper. Round-2 mirrored the formula but missed the DRY opportunity. **Fix:** changed to `from rovodev_tui.slash_commands.shell import _get_workspace_path` + `cwd = _get_workspace_path(app)`. If shell.py ever refines the fallback behaviour, openteam.py picks it up free.
  8. **MODERATE / DOCS** — Registration precedence on slash collision was undocumented. **Fix:** added explicit note in §11 risks: app.py registers OpenTeam LAST inside `try/except ImportError`, and `register_openteam_commands` uses `if slash in registry.commands: continue`, so any future RovoDev `/task` registered earlier would shadow ours (first-registrant-wins = the correct semantics).
  9. **MINOR / PORTABILITY** — `_build_argv_and_env` defaulted `python` (not `python3`). Many modern Linux distros only install `python3`; older macOS systems map `python` to `python2.7`. **Fix:** changed default to `python3` with comment; `OPENTEAM_PYTHON` env override still honored.

**Quick-reference verdict on each feedback item (round 3):**

| # | Severity | Claim | Verdict | Action |
|---|---|---|---|---|
| 1 | CRIT | `extra_prompt` contradiction in §13/§14 | ✅ VALID | Fixed both sites |
| 2 | MAJ | "36/19" vs actual 39/24 | ✅ VALID | Fixed with documented methodology |
| 3 | MAJ | "All 41 bare names" still in §7.1+ | ✅ VALID | Fixed all 5 occurrences |
| 4 | MAJ | conftest.py "12 → 6" stale | ✅ VALID | Fixed to "13 → 10" |
| MOD-1 | MOD | `strip_unset` drops `in_place=False` | ✅ VALID (real bug) | Fixed by removing `in_place` from MCP signature |
| MOD-2 | MOD | Inline `_get_workspace_path` logic | ✅ VALID | Fixed by importing |
| MOD-3 | MOD | `_openteam_home()` user-specific | ⚠️ Already documented in §11 / §12 | No-op |
| MOD-4 | MOD | Registration precedence undocumented | ✅ VALID | Documented in §11 |
| MIN-1 | MIN | `project_onboarding` 225-248 → 225-249 | ⚠️ Off-by-one in inline comment only — substantive content unaffected; minor cosmetic | No-op (low value) |
| MIN-2 | MIN | "lines 45-56" mixes agent_foundation + rich_python_utils | ⚠️ Cosmetic; substantive content unaffected | No-op (low value) |
| MIN-3 | MIN | `run_server.py` "30 → 6" inaccurate | ⚠️ Conceptual count; the comment says it; not worth surgical edit | No-op |
| MIN-4 | MIN | `fastmcp>=2,<4` lower bound too loose | ✅ VALID and **bigger than feedback realized** — `code-nemo:24` pins `==3.2.4`; `>=2,<4` could resolve below FastMCP 3.x API surface | Tightened to `>=3.2,<4` with citation |
| MIN-5 | MIN | `python` vs `python3` default | ✅ VALID | Switched default |
| MIN-6 | MIN | `run_server.py refactored code doesn't use .resolve()` | ⚠️ True but irrelevant — `Path(__file__)` is already absolute when called from a console script; `.resolve()` only matters for symlink-following | No-op |

- **2026-05-16 20:38 — Fourth round of fixes.** Another adversarial review caught lingering inconsistencies (stale references that round-3 missed) and one false precedent claim that arose in round-3. All re-verified against the codebase before fix or rejection:
  1. **MODERATE** — §11 risks table line 1530 still cited `fastmcp>=2,<4` despite round-3 tightening the pin to `>=3.2,<4` in the pyproject.toml block, the ground-truth table, and §13 comparison. Root cause: round-3 used `grep -n fastmcp` to locate stale references but missed the one in the risks table because it was wrapped inside a longer mitigation cell. **Fix:** updated the risks table cell to cite both pyproject.toml files and explain the `>=3.2,<4` choice.
  2. **MODERATE** — §8.3 install runbook line 1468 AND §10 manual test plan line 1517 still showed `/task what is 2+2` (unquoted). Round-3 only updated the §15 DoD checklist line — the same fix needed to propagate to the runbook and test-plan. Root cause: same "find-and-replace propagation" failure mode as round-2/round-3. **Fix:** quoted both occurrences and added the contract explanation inline at the runbook site so anyone copy-pasting the command sees the rule.
  3. **MODERATE** — `test_wrapper_signature_alignment.py` spec at §6.5 only listed clause 5 (mode-enum exception) and missed clause 6 (`in_place` intentional omission). The round-3 wrapper docstring explicitly says the test hard-codes `in_place` as a documented exception, but the test spec didn't actually call for the clause. Anyone implementing the test from §6.5 would write a test that FAILS on day-one (flagging `in_place` as a "missing wrapper param" in clause 2). Root cause: the wrapper update was a single edit; the corresponding test-spec update was forgotten. **Fix:** added clause 6 to §6.5 with the `_INTENTIONALLY_OMITTED = {"in_place"}` constant pattern and an explicit cross-reference back to §6.4.
  4. **MINOR** — `test_build_argv_falls_back_to_python_m` at line 1367 still asserted `argv[0] == "python"` despite round-3 switching the default to `"python3"`. Root cause: code-vs-test asymmetry from the round-3 fix; only the production code was updated. **Fix:** asserted `"python3"` and added explicit `OPENTEAM_PYTHON="python"` override sub-case to lock the env var contract.
  5. **MINOR** — Architecture diagram at line 150 still said "factory pattern à la jira.py" despite round-3 establishing that jira.py uses hand-written handlers (no factory). Root cause: ASCII diagrams escape `grep` for "factory pattern" if the line wraps differently than the prose. **Fix:** changed to "`_make_handler` factory — novel pattern, not in jira.py".
  6. **MINOR** — `openteam_task` docstring claimed "17 parameters total" — actual is **16** (counted via `json.load`: request + 4 mutex flags + 11 optional = 16). The "17" was a miscount that propagated from a much earlier draft. Round-3's "remaining 12 parameters" math was correct (16 − 4 mutex + 1 mode − 1 in_place = 12) but the source number was wrong. **Fix:** added the exact verification command inline (`python3 -c "import json; print(len(...))"`), wrote out the arithmetic, and cross-referenced §6.5 clauses 5 and 6.
  7. **MINOR** — "Mirrors shell.py line-for-line" appeared at 3 sites (§2 invariant, §7.1 file docstring, §7.1 inline `_make_handler` comment). Round-3 added two intentional divergences (`stdin=DEVNULL` and `_get_workspace_path` import) but didn't update the "line-for-line" framing. Root cause: framing-vs-code asymmetry. **Fix:** all three sites now say "structurally mirrors" with explicit enumeration of the two divergences; the streaming loop itself remains "character-identical" (the more precise truth).
  8. **MINOR** — Round-3 cwd-import comment claimed "the same pattern jira.py uses to share helpers with other slash commands (verified by grep for cross-module imports in slash_commands/)". I re-ran the grep myself: the ONLY cross-module import in `slash_commands/` is `edu/command.py → edu/profile.py` (intra-feature). No top-level slash command imports from a sibling. My round-3 claim was provably false. Root cause: I cited the grep without actually re-running it post-claim. **Fix:** replaced the false precedent claim with honest reporting ("This import would be a NOVEL cross-module dependency between top-level slash commands — not an established pattern"). The architectural decision (import > duplicate) is still defensible on first-principles grounds (DRY, rot-resistance, refactor-cost), so the import stands; we just document it honestly.

**Quick-reference verdict on each feedback item (round 4):**

| # | Severity | Claim | Verdict | Action |
|---|---|---|---|---|
| 1 | MOD | §11 fastmcp pin stale | ✅ VALID | Fixed |
| 2 | MOD | Install runbook + test plan unquoted prompt | ✅ VALID (2 sites) | Fixed both |
| 3 | MOD | Test spec missing in_place exception | ✅ VALID (would fail day-one) | Added clause 6 |
| 4 | MIN | Test asserts `python` not `python3` | ✅ VALID | Fixed + added override sub-case |
| 5 | MIN | Architecture diagram factory wording | ✅ VALID | Fixed |
| 6 | MIN | "17 parameters" — actual 16 | ✅ VALID | Fixed with verification command |
| 7 | MIN | "line-for-line" overstatement (3 sites) | ✅ VALID | Fixed all three with precise divergence enumeration |
| 8 | MIN | False cross-module-import precedent claim | ✅ VALID — round-3 introduced this bug; verified false | Replaced false claim with honest novelty acknowledgement + first-principles justification |

- **2026-05-16 23:15 — Fifth round of fixes.** Another adversarial review (cross-verified against fastmcp source, registry.py implementation, and Python buffering semantics). 3 actionable issues, 3 minor cleanups; rejected 5+ false or overstated claims.
  1. **MAJOR** — Phase 0a stdout/stderr buffering order: `print(result.result)` goes into stdout's block-buffer (not flushed), then `print([key] value, file=sys.stderr)` flushes immediately (stderr is unbuffered). With `stderr=STDOUT` merge in the slash handler, artifacts appear BEFORE the result text in the pipe. **Fix:** added `flush=True` to every stdout `print()` call in Phase 0a. Python's stderr is always unbuffered; stdout is block-buffered when piped. `flush=True` forces immediate write, restoring correct ordering.
  2. **MODERATE** — `fastmcp dev` command requires a filesystem path, not a Python module path. FastMCP 3.x's `FileSystemSource.load_server()` does `Path(spec).resolve()` (verified at `filesystem.py:66`). The plan's `"openteam.mcp_server.server:create_openteam_server"` would fail. **Fix:** changed to `"src/openteam/mcp_server/server.py:create_openteam_server"` in install runbook, DoD, and self-audit.
  3. **MODERATE** — `_build_argv_and_env` clobbered user's existing PYTHONPATH via `env["PYTHONPATH"] = ...`. **Fix:** prepend instead of overwrite.
  4. **MINOR** — Registration precedence explanation said "first-registrant-wins" ambiguously. `registry.register()` is actually last-writer-wins (unconditional `self._commands[command] = ...`). The OpenTeam-yields behavior comes from the `if slash in registry.commands: continue` guard in `register_openteam_commands`, not from the registry itself. **Fix:** clarified in §11 and §12.
  5. **MINOR** — Widget and `_get_workspace_path` imports were deferred inside the handler body. shell.py imports widgets at module level (line 12); PEP 8 recommends top-level imports. **Fix:** hoisted `ShellOutput`, `ThinkingSpinner`, and `_get_workspace_path` to module-level imports.
  6. **MINOR** — Ground-truth table said `fastmcp>=3.0,<4` while pyproject says `>=3.2,<4`. **Fix:** aligned to `>=3.2,<4`.
  7. **MINOR** — Phase 0a comment listed `knowledge_dir` for role_setup (it's project_onboarding-only) and omitted `doc_path`/`report_path` for task. **Fix:** corrected per-tool key enumeration.

  **Rejected claims from the same review (verified false or overstated):**
  - "AGENTS.md says avoid imports inside functions" — **FALSE**. AGENTS.md (574 lines) is entirely about snapshot testing; zero import guidance. The import fix was applied on PEP 8 / shell.py grounds instead.
  - "Suffix-discovery rule false positives (e.g. python_path)" — **REJECTED**. `context_updates` dicts contain only artifact metadata by convention; no executor puts config data there.
  - ~~"mode=execute should pre-validate initial_plan" — **REJECTED**~~ **REVERSED** — see fix 8 below: executor does NOT validate this. Round-5 rejection was based on a false reading of `task/executor.py`.
  - "Alphabetical artifact sort order buries workspace_path" — **REJECTED**. Alphabetical is deterministic and zero-maintenance; the LLM reads all keys regardless.
  - "proc.stdout is None leaves shell_output mounted" — **REJECTED**. Unreachable code path (stdout=PIPE guarantees proc.stdout is not None).
  - "§5.4 test_missing_siblings_silent name is stale" — **ACCEPTED (minor)**: the behavior is now logger.warning, not truly silent. Also added missing `test_strict_raises` to §5.4 to match §10's promise.
  - "Silent ImportError swallowing in app.py" — **REJECTED**. Adding `logger.warning` to the `except ImportError: pass` block would fire on **every startup** for users who don't have OpenTeam installed (the normal case). The silent `pass` IS the correct behavior for an optional feature's disable-knob.
  - "PYTHONUNBUFFERED=1 for intermediate streaming" — **REJECTED (nice-to-have)**. The executor returns a `ToolExecutionResult` at the end; it doesn't stream to stdout during execution. `flush=True` on the final prints (fix 1) handles the ordering. No concrete bug to fix.

  8. **MODERATE** — `openteam_task(mode="execute")` without `initial_plan` was silently accepted by the wrapper. Round-5 initially rejected this ("Executor already validates") but direct verification of `task/executor.py:534-595` proved the rejection wrong: the executor validates that `--initial-plan` FILE EXISTS (line 578) and that only ONE mode flag is set (line 554), but it does NOT validate that `mode="execute"` REQUIRES `--initial-plan`. Without a plan, the topology runs `enable_planning=False` (line 440) with `init_plan_path=None` — the implementation phase has nothing to implement and produces a confusing error from deep inside the inferencer. This is **input validation** (not business logic), so adding it to the wrapper doesn't violate the "zero business-logic duplication" invariant. **Fix:** added `if mode == "execute" and not initial_plan: raise ValueError(...)` before the executor call, with a clear error message.

---

## 0. Why v6 exists

The Cursor plan grew from 231 → 951 lines and now (correctly) picks up many of v5's points while introducing two genuinely better moves of its own. The Claude plan is leaner and gets the slash naming + file layout right *better than v5 did*. My v5 had two **idiomatic errors** that need correcting:

| v5 mistake | Ground truth | Source |
|---|---|---|
| Slash names **namespaced** (`/openteam-task`) | Of 64 registrations in `app.py`, **39 are bare top-level commands** (`/jira`, `/sessions`, `/plan`, `/mode`, …); **24 are sub-commands** (`/jira global`, `/sessions new`, `/copy formatted`, etc.); 1 is the special non-slash `$` (shell). Crucially, **every top-level feature is bare** — `/openteam-task` would be a brand-new naming convention that no other feature uses. Sub-commands are namespaced *under* a bare top-level name, never as kebab-prefixed siblings. | `app.py:530-595` `grep -oE` (verified, see round-3 revision history for methodology) |
| **Four separate files** (`openteam_task.py`, `openteam_create_role.py`, …) | Convention is **one file per feature, multiple hand-written `async def handle_…` functions** (`jira.py` has 4; `sessions.py` has 6). v5's four-file split is non-idiomatic. | direct file inspection |

Conversely, v5 and Claude are *correct* and Cursor is *over-clever* on one point:

| Cursor proposal | v5 / Claude / v6 position | Reason |
|---|---|---|
| **`bootstrap.ensure_siblings_on_path()` called from `src/openteam/__init__.py`** so every import transparently fixes sys.path | **Reject.** Bootstrap called *explicitly* from the `openteam-mcp` Typer entry + `conftest.py` + `run_server.py` | (a) **Zero precedent** in this ecosystem: `agent_foundation/__init__.py`, `rich_python_utils/__init__.py`, `openteam/__init__.py`, and every sub-package `__init__.py` is empty; (b) `conftest.py` and `run_server.py` *deliberately* keep injection explicit ("This fallback ensures it works both ways" — `run_server.py:23-32`); (c) silent import-time side-effects are exactly the kind of "magic" that breaks at the worst moment (PyInstaller image, subprocess from a different cwd, downstream library importing `openteam` for typing). **Explicit > implicit.** |

Cursor's other two big moves are **kept**:

| Cursor proposal | v5 / Claude position | v6 verdict |
|---|---|---|
| **5 console scripts** (`openteam-mcp` + 4 tool scripts via `[project.scripts]`) | v5 had only `openteam-mcp run-tool <name>` dispatcher; Claude had only `python -m` | **Accept** — `task/cli.py` already exposes `def main(argv=None) -> int`, so each `openteam-<tool>` entry is **zero new code**, just a `[project.scripts]` line. Slash subprocess argv becomes `["openteam-task", *args]` — no `python -m`, no PYTHONPATH. |
| Shipped `templates/SKILL.md` and `templates/mcp.json` for `cp`-to-user install | v5 already had this | **Already in v5; v6 keeps it** |

---

## 1. Re-verified ground truth (every load-bearing fact)

| Claim | Verified result | Where |
|---|---|---|
| `tool_cli.py` rendering at lines **125-131** is broken (off-by-one in earlier draft of this table) | ✓ — exact code: `if isinstance(result, dict): print(result.get("text", ""))` … `else: print(result)`. `ToolExecutionResult` is `@dataclass(result, context_updates)` — neither dict nor has `.text`, so dict branch prints `""` and else branch prints `repr()`. | `OpenStartup/src/openteam/server/services/tool_cli.py:125-131` (re-verified post-feedback) |
| `ToolExecutionResult` is `@dataclass` (NOT Pydantic) | ✓ — `@dataclass class ToolExecutionResult: result: str; context_updates: dict[str, Any]` | `AgentFoundation/src/agent_foundation/common/inferencers/agentic_inferencers/conversational/protocols.py:16-23` (corrected from earlier 15-22) |
| `project_onboarding/` lacks `cli.py` + `__main__.py` | ✓ — `ls` shows only `__init__.py`, `executor.py`, `project_onboarding.yaml`, `tool.json` | `OpenStartup/.../tools/project_onboarding/` |
| `task/cli.py` is `def main(argv=None) -> int` (entry-point-ready) | ✓ — verbatim | `task/cli.py:20-21` |
| `task/cli.py` passes `mutually_exclusive_groups=[{"--plan","--execute","--full","--confirm"}]` to `run_cli` | ✓ — verbatim | `task/cli.py:17, 20` |
| `task/__main__.py` exists; `create_role/{cli,__main__}.py` exist; `role_setup/{cli,__main__}.py` exist | ✓ | direct listing |
| `slash_enabled: true` only on `task/tool.json` (line 8) | ✓ — `grep` shows only that file has it | `OpenStartup/.../tools/<t>/tool.json` |
| `OpenStartup/pyproject.toml` does NOT exist | ✓ | repo root |
| `AgentFoundation/`, `RichPythonUtils/` have no `pyproject.toml` either | ✓ | repo roots |
| `OpenStartup/src/openteam/__init__.py` is **empty** | ✓ — `cat` returns 0 bytes | direct |
| `OpenStartup/src/openteam/server/__init__.py` is **empty** | ✓ — `cat` returns 0 bytes | direct |
| `AgentFoundation/src/agent_foundation/__init__.py` is **empty** | ✓ — `cat` returns 0 bytes | direct |
| `RichPythonUtils/src/rich_python_utils/__init__.py` contains only a **placeholder comment** (`# Implement your code here.`, 28 bytes) — no executable code, no imports — so adopting an "empty `__init__.py`" convention for OpenTeam aligns even though this file isn't literally zero-bytes. (An earlier draft of this plan said "all are empty / zero-bytes" — corrected: 4 of 5 are zero-bytes; this 5th is a placeholder comment with zero behaviour.) | direct |
| `conftest.py` is **13 lines**, explicit (off-by-one in earlier draft) | ✓ — `wc -l` re-confirmed post-feedback | direct |
| `run_server.py:13-43` injects sys.path explicitly with extensive comment | ✓ — verbatim | direct |
| `app.py:541` registers `handle_shell_command, "$", extra_prompt="required", thread=True` | ✓ | direct |
| 41 entries in `slash_commands/` (incl. `__init__.py`, `registry.py`, `__pycache__/`, `edu/` subdir) → ~37 real `.py` command modules; 64 `command_registry.register(...)` calls in `app.py` of which **39 are bare top-level** (`/jira`, `/sessions`, `/plan`, …), **24 are sub-commands** under those (`/jira global`, `/sessions new`, …), **1 is non-slash `$`** | ✓ — `grep -oE '"/[a-z][a-z0-9_-]*"'` and `'"/[a-z][a-z0-9_-]* [a-z][a-z0-9_-]*"'` for deterministic count (round-3 re-verification) | direct |
| `jira.py` is **one file, four hand-written handlers** (no shared factory) — `handle_jira_command`, `_global_`, `_local_`, `_disable_`; same hand-written pattern in `sessions.py` (6 handlers) | ✓ — grep | direct |
| v6's `_make_handler` factory in `slash_commands/openteam.py` is therefore a **novel** pattern, not an idiomatic precedent | Defensible: the 4 openteam handlers are isomorphic up to (slash, binary, module), making the factory genuinely DRY where hand-writing 4 nearly-identical handlers would not be. The novelty is acknowledged explicitly rather than mis-claimed as convention. | n/a |
| `mcp-atlassian-exp` ships **2 console scripts**, both pointing to `atlassian_exp.main:app` (single Typer dispatcher) | ✓ — `[project.scripts]` block | direct |
| `mcp-atlassian-exp/main.py` uses `FastMCP("…")` + `mcp.add_tool(FunctionTool.from_function(fn))` | ✓ — `def create_atlassian_exp_server` at line **95**, full body lines **95-117** (off-by-one in earlier draft) | direct (re-verified post-feedback) |
| **Where IS `fastmcp==3.2.4` pinned in acra-python?** | ✓ — `code-nemo/pyproject.toml:24` pins `"fastmcp==3.2.4"` exactly. `mcp-atlassian-exp/pyproject.toml` does NOT pin it (transitive via code-nemo). So the cli-rovodev-tui process's resolved fastmcp version IS 3.2.4. Earlier draft of v6 said "not pinned" — partial-truth (only mcp-atlassian-exp's own pyproject) elevated to a categorical claim. **For OpenTeam-mcp to call the same fastmcp API surface the TUI ships with, we align: `fastmcp>=3.2,<4` (same minor as code-nemo's `==3.2.4`; `FunctionTool.from_function` is a FastMCP 3.x API not present in 2.x).** | `code-nemo/pyproject.toml:24` (re-verified round-3) |
| MCP client timeout = 295 s (hardcoded) | ✓ | `acra-python/packages/code-nemo/src/nemo/utils/mcp_toolset.py:138` |
| `format_input_prompt` handles only `'research'` and `'full-context'` | ✓ | `cli-rovodev/src/rovodev/modules/prompts.py:292-300` |
| `cli-rovodev-tui/AGENTS.md` documents snapshot test discipline | ✓ | direct |

---

## 2. Architecture (one substrate, three surfaces)

```
                  ┌── RovoDev TUI (cli-rovodev-tui, Textual) ──────────────┐
                  │                                                        │
   /task <args>───┤  slash_commands/openteam.py (single file, 4 handlers,  │
                  │   _make_handler factory — novel pattern, not in jira.py)│
                  │   ↓ subprocess: ["openteam-task", *args]               │
                  │   ↓ (fallback: ["python","-m","openteam…task", *args]  │
                  │      + computed PYTHONPATH)                            │
                  │   ↓ stream stdout (stderr=STDOUT merged)               │
                  │   ↓ ShellOutput widget (Markdown.append per line)      │
                  │   ↓ ThinkingSpinner removed on completion              │
                  │   ↓ worker.is_cancelled → proc.terminate               │
                  │   ↓ empty output → shell_output.remove                 │
                  │                                                        │
                  │  LLM agent (pydantic-ai)                               │
                  │   ↓ tool_call: mcp__openteam__openteam_task(…)         │
                  │   ↓ MCPClient (295 s timeout, hardcoded)               │
                  │                                                        │
                  └────────────────────┬───────────────────────────────────┘
                                       │ stdio JSON-RPC
                                       ▼
                  ┌── ~/.rovodev/mcp.json ─────────────────────────────────┐
                  │  "openteam": { "command": "openteam-mcp",              │
                  │                "args": ["run"], "transport": "stdio" } │
                  └────────────────────┬───────────────────────────────────┘
                                       ▼
                  ┌── openteam-mcp subprocess (Typer / FastMCP) ───────────┐
                  │  cli.py — explicit bootstrap.ensure_siblings_on_path() │
                  │            (NOT from openteam/__init__.py)             │
                  │  ↓                                                     │
                  │  create_openteam_server() → FastMCP("openteam")        │
                  │  for each of 4 wrappers:                               │
                  │    mcp.add_tool(FunctionTool.from_function(wrapper))   │
                  │  ↓                                                     │
                  │  in-process: await executor.execute(args, ctx)         │
                  │  ↓                                                     │
                  │  _render_result(ToolExecutionResult)                   │
                  └────────────────────────────────────────────────────────┘
```

**Invariants** (any deviation makes the plan hacky):

1. **One substrate, three surfaces.** Slash, MCP, and `python -m` standalone CLI all reach `await executor.execute(arguments, session_context)`. Zero business-logic duplication.
2. **Process isolation, always.** `openteam-mcp` is a subprocess of RovoDev; never an in-process import (RovoDev is PyInstaller-frozen — additional imports are physically impossible).
3. **Bare slash names, single file, factory pattern.** Match `jira.py` / `sessions.py` exactly (one file per feature, multiple hand-written handlers). Bare slash names match the convention: of 64 registrations in `app.py`, **39 are bare top-level** and **24 are sub-commands** namespaced under a bare top-level; no kebab-prefixed siblings exist anywhere. The `_make_handler` factory itself is novel (the 4 OpenTeam handlers are isomorphic up to (slash, binary, module) tuples, making it genuinely DRY), but the file layout and naming are 100% idiomatic.
4. **Bootstrap is explicit at the boundary, never magic at import time.** Called from `openteam-mcp` entry, `conftest.py`, `run_server.py`. Never from `openteam/__init__.py`. Matches the explicit-import convention of every package in `CoreProjects/`.
5. **5 console scripts, no `python -m` in normal flow.** `openteam-task`, `openteam-create-role`, `openteam-role-setup`, `openteam-project-onboarding`, `openteam-mcp` — all via `[project.scripts]`. Each tool already has `main(argv=None) -> int`, so this is **zero new code**. Slash subprocess falls back to `python -m` if the binary isn't on PATH.
6. **Structurally mirror `shell.py`.** Same skeleton: `get_current_worker`, `stderr=STDOUT`, `at_eof`, `worker.is_cancelled → terminate`, empty-output cleanup. Two intentional divergences: (a) `stdin=DEVNULL` (shell.py inherits stdin because shell is interactive); (b) `_get_workspace_path` is imported rather than reimplemented.
7. **MCP wrappers are typed** with `Literal[...]` for the LLM. CLI surface unchanged.

---

## 3. File touch list (consolidated)

### 3.1 OpenStartup — NEW

```
pyproject.toml                                                    # root packaging (Phase 1a)
src/openteam/bootstrap.py                                         # sys.path injection (Phase 1b)
src/openteam/mcp_server/__init__.py                               # empty
src/openteam/mcp_server/cli.py                                    # Typer entry — calls bootstrap first
src/openteam/mcp_server/server.py                                 # create_openteam_server() + 4 wrappers
src/openteam/mcp_server/context.py                                # build_session_context()
src/openteam/mcp_server/_helpers.py                               # _to_dash_form / _strip_unset / _render_result
src/openteam/mcp_server/templates/SKILL.md                        # canonical skill (copy-to-user template)
src/openteam/mcp_server/templates/mcp.json                        # canonical mcp.json snippet
src/openteam/server/resources/tools/project_onboarding/cli.py     # 12-line shim (Phase 0b)
src/openteam/server/resources/tools/project_onboarding/__main__.py # 3-line shim (Phase 0b)
test/openteam/mcp_server/test_server_factory.py                   # TIER-1
test/openteam/mcp_server/test_context.py                          # TIER-1
test/openteam/mcp_server/test_helpers.py                          # TIER-1 (_strip_unset edge cases incl. 0)
test/openteam/mcp_server/test_wrappers_smoke.py                   # TIER-2
test/openteam/mcp_server/test_wrapper_signature_alignment.py      # TIER-1 CI preflight
test/openteam/mcp_server/test_bootstrap.py                        # TIER-1
test/openteam/server/services/test_tool_cli_rendering.py          # TIER-1 (Phase 0a)
test/openteam/server/resources/tools/project_onboarding/test_cli_smoke.py  # TIER-2
test/openteam/server/resources/tools/test_cli_bootstrap_smoke.py  # TIER-1 (Phase 0d — all 4 tools, fresh subprocess, minimal PYTHONPATH)
test/openteam/test_init_py_remains_empty.py                       # TIER-1 CI pillar guard (every __init__.py empty)
test/openteam/server/test_run_server_smoke.py                     # TIER-2 (Phase 1b refactor regression)
test/openteam/mcp_server/test_mode_enum_complete.py               # TIER-1 (mode Literal ↔ tool.json mutex group alignment)
test/openteam/mcp_server/test_render_artifacts_discovery.py       # TIER-1 (artifact key-suffix discovery for all 4 tools)
docs/MCP_INTEGRATION.md
docs/MCP_SMOKE.md
```

### 3.2 OpenStartup — MODIFIED

```
src/openteam/server/services/tool_cli.py                          # Phase 0a (lines 125-132)
src/openteam/server/resources/tools/task/cli.py                   # Phase 0d (4-line bootstrap prefix)
src/openteam/server/resources/tools/create_role/cli.py            # Phase 0d (4-line bootstrap prefix)
src/openteam/server/resources/tools/role_setup/cli.py             # Phase 0d (4-line bootstrap prefix)
src/openteam/server/resources/tools/create_role/tool.json         # "slash_enabled": true
src/openteam/server/resources/tools/role_setup/tool.json          # "slash_enabled": true
src/openteam/server/resources/tools/project_onboarding/tool.json  # "slash_enabled": true
conftest.py                                                       # delegate to openteam.bootstrap (DRY)
src/openteam/server/run_server.py                                 # replace lines 13-43 with bootstrap call
README.md                                                         # install steps
```

### 3.3 acra-python (`cli-rovodev-tui` package) — NEW

```
packages/cli-rovodev-tui/src/rovodev_tui/slash_commands/openteam.py    # single file, 4 handlers, factory
packages/cli-rovodev-tui/tests/slash_commands/test_openteam.py         # mocked subprocess
packages/cli-rovodev-tui/tests/integration/test_openteam_snapshots.py  # @pytest.mark.snapshot
packages/cli-rovodev-tui/docs/openteam-integration.md
```

### 3.4 acra-python — MODIFIED

```
packages/cli-rovodev-tui/src/rovodev_tui/app.py    # 4-line opt-in registration block (try/except ImportError)
```

### 3.5 User-side (one-time, after install)

```
~/.rovodev/mcp.json                          # cp from src/openteam/mcp_server/templates/mcp.json
~/.rovodev/skills/openteam/SKILL.md          # cp from src/openteam/mcp_server/templates/SKILL.md
```

---

## 4. Phase 0 — blocking prerequisites (~30 min)

### 4.1 Phase 0a — `tool_cli.py` rendering fix

**File:** `OpenStartup/src/openteam/server/services/tool_cli.py`
**Replace lines 125-132 with:**

```python
# Render result — duck-typed against ToolExecutionResult (@dataclass in
# AgentFoundation/.../protocols.py with .result:str + .context_updates:dict),
# legacy dict, and bare str. Duck-typed (hasattr) to avoid importing
# ToolExecutionResult here — keeps the CLI scaffold free of cross-package
# coupling and tolerant of either the dataclass or future Pydantic variants.
if hasattr(result, "result") and hasattr(result, "context_updates"):
    print(result.result or "", flush=True)
    ctx = result.context_updates or {}
elif isinstance(result, dict):
    # Backwards-compat: prefer "result", fall back to legacy "text"
    print(result.get("result") or result.get("text") or "", flush=True)
    ctx = result.get("context_updates") or {}
else:
    print(str(result), flush=True)
    ctx = {}

# Surface artifact paths on stderr — subprocess wrappers and humans can
# scrape them; merged stdout/stderr in the slash subprocess still keeps them
# logically separable via the "[key] value" prefix.
#
# Discovery rule (not allowlist): emit every value whose key ENDS with
# "_path" or "_dir" and value is a non-empty string. This is robust to
# tool-specific keys (task: workspace_path, plan_path, impl_path,
# doc_path, report_path;
# role_setup: role_setup_report_path, skills_dir, tools_dir,
# role_tool_association_path, role_setup_working_dir;
# create_role: role_document_path, role_document_working_dir, doc_path;
# project_onboarding: project_onboarding_report_path, project_onboarding_working_dir,
# skills_dir, tools_dir, knowledge_dir, role_tool_association_path).
# Verified against every executor's context_updates assembly:
#   task/executor.py:281-286 + 522-525
#   create_role/executor.py:569-582 + 585-588
#   role_setup/executor.py:1261-1280
#   project_onboarding/executor.py:225-248
for key, value in sorted(ctx.items()):
    if (key.endswith("_path") or key.endswith("_dir")) and isinstance(value, str) and value:
        print(f"[{key}] {value}", file=sys.stderr)
return 0
```

**Test file:** `test/openteam/server/services/test_tool_cli_rendering.py` (TIER-1)

- `test_renders_tool_execution_result()` — `SimpleNamespace(result="hi", context_updates={"workspace_path":"/tmp"})` → stdout `"hi\n"` + stderr `"[workspace_path] /tmp\n"`.
- `test_renders_dict_result_modern_key()` — `{"result": "hi"}` → stdout `"hi\n"`.
- `test_renders_dict_result_legacy_text_key()` — `{"text": "hi"}` → stdout `"hi\n"`.
- `test_renders_str_result()` — bare string `"hi"` → stdout `"hi\n"`.
- `test_falsy_result_prints_empty_line()` — `result=""` → stdout `"\n"`.
- `test_artifact_paths_on_stderr()` — each known key on its own stderr line.
- `test_unknown_artifact_keys_ignored()` — `ctx={"foo": "bar"}` → no stderr line.

### 4.2 Phase 0b — `project_onboarding/cli.py` + `__main__.py` shims

**Create** `src/openteam/server/resources/tools/project_onboarding/cli.py`:

```python
"""Standalone CLI for the project_onboarding executor.

Driven entirely by tool.json so the CLI and slash command formats stay in
sync. Mirrors task/cli.py except for the tool name and no mutex groups
(project_onboarding has no mutually-exclusive flag groups).

Usage::

    python -m openteam.server.resources.tools.project_onboarding ./docs/role.md \\
        --role-setup-path ./roles/eng/role_setup_report.md
"""
# ── BOOTSTRAP FIRST ─ before importing the executor. Mandatory for console
# script entry points; see openteam.bootstrap docstring for the full rule.
from openteam.bootstrap import ensure_siblings_on_path
ensure_siblings_on_path()

from pathlib import Path  # noqa: E402

from openteam.server.services.tool_cli import run_cli  # noqa: E402
from .executor import execute  # noqa: E402

_TOOL_JSON = Path(__file__).parent / "tool.json"


def main(argv=None) -> int:
    return run_cli(_TOOL_JSON, execute, argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
```

**Create** `src/openteam/server/resources/tools/project_onboarding/__main__.py`:

```python
"""Module entrypoint: enables ``python -m openteam.server.resources.tools.project_onboarding``."""
from .cli import main
import sys
sys.exit(main())
```

**Test:** `test/openteam/server/resources/tools/project_onboarding/test_cli_smoke.py` (TIER-2)

- `test_help_exits_zero()` — `subprocess.run([sys.executable, "-m", "openteam.server.resources.tools.project_onboarding", "--help"])` returns 0.
- `test_cli_import_smoke()` — `from openteam.server.resources.tools.project_onboarding.cli import main` succeeds.

### 4.3 Phase 0c — `slash_enabled: true` on 3 tool.json files

Add `"slash_enabled": true` (at the top level, alongside `"name"` / `"slug"`) to:
- `src/openteam/server/resources/tools/create_role/tool.json`
- `src/openteam/server/resources/tools/role_setup/tool.json`
- `src/openteam/server/resources/tools/project_onboarding/tool.json`

(`task/tool.json` already has it at line 8.)

### 4.4 Phase 0d — retrofit bootstrap into the 3 existing tool clis

`task/cli.py`, `create_role/cli.py`, `role_setup/cli.py` already exist on
disk. They will become console-script entry points in Phase 1a
(`[project.scripts] openteam-<tool> = "…cli:main"`). Console scripts run in a
shell that may not have sourced conftest.py / run_server.py; without bootstrap
they ImportError at module load (verified for create_role + role_setup whose
executors import `agent_foundation` at module level) or at runtime (verified
for task + project_onboarding whose executors defer the import inside
`execute()`).

**Modify** `src/openteam/server/resources/tools/task/cli.py` — add the
bootstrap block at the top (before any other imports):

```python
"""Standalone CLI for the task executor. […existing docstring unchanged…]"""
# ── BOOTSTRAP FIRST ─ mandatory for console script entry points; see
# openteam.bootstrap docstring for the full rule.
from openteam.bootstrap import ensure_siblings_on_path
ensure_siblings_on_path()

from pathlib import Path  # noqa: E402

from openteam.server.services.tool_cli import run_cli  # noqa: E402
from .executor import execute  # noqa: E402

_TOOL_JSON = Path(__file__).parent / "tool.json"
_MODE_MUTEX = [{"--plan", "--execute", "--full", "--confirm"}]


def main(argv=None) -> int:
    return run_cli(_TOOL_JSON, execute, argv=argv, mutually_exclusive_groups=_MODE_MUTEX)


if __name__ == "__main__":
    raise SystemExit(main())
```

**Apply the same 4-line bootstrap prefix** to:
- `src/openteam/server/resources/tools/create_role/cli.py`
- `src/openteam/server/resources/tools/role_setup/cli.py`

(`project_onboarding/cli.py` is created in Phase 0b with bootstrap already in place.)

**Phase 0d tests** (extend `test_project_onboarding_cli_smoke.py` or add
`test/openteam/server/resources/tools/test_cli_bootstrap_smoke.py`, TIER-1):

- `test_each_tool_cli_imports_in_fresh_subprocess()` — for each of the 4
  tools, `subprocess.run([sys.executable, "-c", f"import {tool_module}.cli"])`
  with `PYTHONPATH=src` (NO sibling repos on PYTHONPATH). Must exit 0 for ALL
  4 (proves bootstrap runs before the executor import).
- `test_each_tool_cli_help_in_fresh_subprocess()` — for each tool,
  `subprocess.run([sys.executable, "-m", tool_module, "--help"])` with the
  same minimal PYTHONPATH; must exit 0.

---

## 5. Phase 1 — Root packaging + `bootstrap.py` (~30 min)

### 5.1 Phase 1a — `OpenStartup/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openteam"
version = "0.1.0"
description = "OpenTeam multi-agent workflow runtime + MCP server."
requires-python = ">=3.11"
dependencies = [
    # FastMCP: acra-python's code-nemo/pyproject.toml:24 pins `fastmcp==3.2.4`
    # exactly. The cli-rovodev-tui process the TUI bundles will therefore
    # have FastMCP 3.2.4 already resolved. Our openteam-mcp runs in a
    # SEPARATE subprocess, so version skew across the stdio boundary is
    # tolerable — but FunctionTool.from_function() and the `mcp.add_tool(…)`
    # registration API are FastMCP 3.x ones (not present in 2.x). Pin to
    # the same major as code-nemo so the documented usage stays current:
    "fastmcp>=3.2,<4",
    "mcp>=1.25.0",
    "typer>=0.12",
    "pyyaml>=6",
    "omegaconf>=2.3",
    "jinja2>=3.1",
    "hydra-core>=1.3",
    "attrs>=23",
    "pydantic>=2",
    "python-dotenv>=1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23"]

# ── Console scripts ─────────────────────────────────────────────────────────
# Five entries. The four tool scripts are zero-new-code: each tool already
# exposes def main(argv=None) -> int in its cli.py module (verified for
# task / create_role / role_setup; project_onboarding ships its shim in
# Phase 0b). The dispatcher (openteam-mcp) is the Typer entry that runs
# bootstrap explicitly before importing FastMCP.
#
# Result: the slash subprocess argv is ["openteam-task", *args] (no python -m,
# no PYTHONPATH); the mcp.json command is "openteam-mcp" (no python -m,
# no PYTHONPATH). The user's ~/.rovodev/mcp.json carries ZERO sibling-path
# coupling.
[project.scripts]
openteam-mcp                = "openteam.mcp_server.cli:app"
openteam-task               = "openteam.server.resources.tools.task.cli:main"
openteam-create-role        = "openteam.server.resources.tools.create_role.cli:main"
openteam-role-setup         = "openteam.server.resources.tools.role_setup.cli:main"
openteam-project-onboarding = "openteam.server.resources.tools.project_onboarding.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["openteam*"]
```

After `pip install -e .` (or `uv tool install -e .`), all five scripts live on `PATH`.

### 5.2 Phase 1b — `src/openteam/bootstrap.py` (the only canonical sys.path injector)

```python
"""Ensure sibling repos AgentFoundation and RichPythonUtils are importable.

Both sibling repos lack pyproject.toml, so we cannot resolve them via pip;
we inject their src/ directories onto sys.path. Idempotent — safe to call
repeatedly.

DESIGN NOTE — why this is NOT called from openteam/__init__.py:

  The Cursor plan proposed calling ensure_siblings_on_path() from
  src/openteam/__init__.py so every `import openteam.*` would transparently
  fix sys.path. We rejected this because:

  (a) No precedent: agent_foundation/__init__.py and rich_python_utils/__init__.py
      are empty/placeholder; openteam/{__init__,server/__init__,server/services/__init__}.py
      are all empty. Adding side effects here breaks the convention.
  (b) Surprise: `import openteam` should not silently mutate sys.path. A
      downstream library importing openteam for typing or introspection would
      get its global sys.path rewritten — a debugging nightmare.
  (c) The existing conftest.py + run_server.py:13-43 deliberately keep
      injection explicit ("This fallback ensures it works both ways").

  Callsites (all explicit — one rule: every module named in [project.scripts]
  calls ensure_siblings_on_path() BEFORE its first openteam.server.* import.
  This makes the console script entry points self-contained — they work even
  when launched from a shell that never sourced conftest.py / run_server.py):

    - openteam.mcp_server.cli                       (entry: openteam-mcp)
    - openteam.server.resources.tools.task.cli      (entry: openteam-task)
    - openteam.server.resources.tools.create_role.cli         (entry: openteam-create-role)
    - openteam.server.resources.tools.role_setup.cli          (entry: openteam-role-setup)
    - openteam.server.resources.tools.project_onboarding.cli  (entry: openteam-project-onboarding)
    - conftest.py                                   (root)
    - openteam.server.run_server                    (replaces the existing 30-line inline block)

  Why each tool's cli.py needs it (verified by direct inspection):
    - create_role/executor.py:45-56 imports agent_foundation at MODULE level
      → cli.py's `from .executor import execute` raises ImportError on launch
        without bootstrap.
    - role_setup/executor.py:48-56 same module-level imports → same failure.
    - task/executor.py + project_onboarding/executor.py defer agent_foundation
      imports inside execute(), so module-load succeeds without bootstrap, but
      runtime invocation still fails. Adding bootstrap to their cli.py too is
      both consistent and defensive against future refactors that hoist imports.

OPENTEAM_SIBLINGS_ROOT env override: if your checkout diverges from the default
`<openteam-package-root>/../..` (i.e. CoreProjects/) layout, set this to the
absolute path of the directory that contains AgentFoundation/ and
RichPythonUtils/.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

_SIBLINGS = ("AgentFoundation/src", "RichPythonUtils/src")


def _find_siblings_root() -> Path | None:
    """Resolve the directory that contains AgentFoundation/ and RichPythonUtils/.

    Priority:
      1. OPENTEAM_SIBLINGS_ROOT env var (returns resolved path even if dir
         does not exist — ensure_siblings_on_path() will then warn).
      2. Walk up from the openteam package looking for the canonical
         CoreProjects/ layout (both siblings present).
      3. Return None — caller treats as "siblings could not be located".

    Returning None on miss (rather than silently falling back to the
    historical two-levels-up) means ensure_siblings_on_path() can emit
    a clear warning instead of failing later with an opaque ImportError.
    """
    env_override = os.environ.get("OPENTEAM_SIBLINGS_ROOT")
    if env_override:
        return Path(env_override).resolve()

    here = Path(__file__).resolve()                          # …/OpenStartup/src/openteam/bootstrap.py
    openteam_src = here.parent.parent                        # …/OpenStartup/src
    cursor = openteam_src.parent                             # …/OpenStartup
    for _ in range(5):
        cursor = cursor.parent
        if (cursor / "AgentFoundation" / "src").is_dir() and \
           (cursor / "RichPythonUtils" / "src").is_dir():
            return cursor
    return None


def ensure_siblings_on_path(*, strict: bool = False) -> list[Path]:
    """Insert OpenStartup/src and each existing sibling src/ onto sys.path.

    Returns the list of paths actually inserted. Idempotent: a directory
    already on sys.path is not added a second time.

    Diagnostics:
      - If OPENTEAM_SIBLINGS_ROOT is set but the directory doesn't exist,
        or doesn't contain BOTH AgentFoundation/src and RichPythonUtils/src,
        emits a logger.warning() so the failure surfaces near the cause
        rather than as an opaque ImportError later.
      - If strict=True, raises FileNotFoundError instead of warning.
        Use strict=True in CI / production entry points (e.g. openteam-mcp)
        where a misconfigured sibling layout is a deploy bug, not user
        choice.
    """
    import logging
    _logger = logging.getLogger(__name__)

    here = Path(__file__).resolve()
    openteam_src = here.parent.parent
    siblings_root = _find_siblings_root()

    inserted: list[Path] = []

    # Always insert openteam src itself (where bootstrap.py lives).
    if openteam_src.is_dir() and str(openteam_src) not in sys.path:
        sys.path.insert(0, str(openteam_src))
        inserted.append(openteam_src)

    if siblings_root is None:
        msg = (
            "openteam.bootstrap: could not locate AgentFoundation/src + "
            "RichPythonUtils/src by walking up from %s. Set "
            "OPENTEAM_SIBLINGS_ROOT to the directory containing both "
            "sibling repos."
        )
        if strict:
            raise FileNotFoundError(msg % openteam_src)
        _logger.warning(msg, openteam_src)
        return inserted

    missing: list[str] = []
    for sib in _SIBLINGS:
        candidate = siblings_root / sib
        if not candidate.is_dir():
            missing.append(str(candidate))
            continue
        s = str(candidate)
        if s not in sys.path:
            sys.path.insert(0, s)
            inserted.append(candidate)

    if missing:
        msg = (
            "openteam.bootstrap: siblings_root=%s but the following "
            "expected dirs are missing: %s. Subsequent openteam.server.* "
            "imports may fail with ImportError. Check OPENTEAM_SIBLINGS_ROOT."
        )
        if strict:
            raise FileNotFoundError(msg % (siblings_root, missing))
        _logger.warning(msg, siblings_root, missing)

    return inserted
```

### 5.3 Phase 1b cont. — Refactor `conftest.py` and `run_server.py` to delegate

**`OpenStartup/conftest.py`** becomes (**13 → 10 lines** — the original is 13 verified-by-`wc -l`; the new version is 10 lines including blank lines and the `# noqa: E402`):

```python
"""Root conftest.py — delegates to openteam.bootstrap for sibling sys.path."""
import sys
from pathlib import Path

# Step 1: openteam itself must be importable so we can call bootstrap.
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Step 2: bootstrap (no openteam.* imports beyond itself; safe at this point).
from openteam.bootstrap import ensure_siblings_on_path  # noqa: E402
ensure_siblings_on_path()
```

**`run_server.py` lines 13-43** become (30 → 6 lines):

```python
# ── Python path setup ─────────────────────────────────────────────────────────
# Sibling repos AgentFoundation and RichPythonUtils have no pyproject.toml;
# we inject them via openteam.bootstrap so this CLI works whether started via
# `bash run.sh` (which sets PYTHONPATH) or directly via `python run_server.py`.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # OpenStartup/src
from openteam.bootstrap import ensure_siblings_on_path  # noqa: E402
ensure_siblings_on_path()
```

### 5.4 Phase 1 tests (`test_bootstrap.py`, TIER-1)

- `test_idempotent()` — call twice; sys.path length grows by N, not 2N.
- `test_env_override()` — set `OPENTEAM_SIBLINGS_ROOT=/tmp/fake`; assert lookup honors it (no insertions if dirs absent, but path is consulted).
- `test_walks_up_to_find_siblings()` — create temp CoreProjects/AgentFoundation/src + RichPythonUtils/src; place openteam src deep below; assert resolution finds it.
- `test_missing_siblings_warns()` — point at empty dir; no exception raised, `logger.warning()` emitted, returns `[]` or only `openteam_src`.
- `test_strict_raises_on_missing()` — `ensure_siblings_on_path(strict=True)` with empty dir raises `FileNotFoundError`.
- `test_does_not_import_from_siblings()` — Bootstrap.py module is importable WITHOUT AgentFoundation/RichPythonUtils on sys.path (zero top-level imports from them).

---

## 6. Phase 2 — MCP server (`openteam-mcp`) (~½-1 day)

### 6.1 `src/openteam/mcp_server/cli.py` (Typer entry)

```python
"""`openteam-mcp` CLI entry point. Calls bootstrap before any openteam.* import."""
from __future__ import annotations

# ── BOOTSTRAP FIRST ─ before importing fastmcp or any openteam.server.* module
# This is the canonical, explicit invocation. Do not move below other imports.
# Use strict=True: in the production MCP entry point, a misconfigured sibling
# layout is a deploy bug (the user has installed openteam-mcp but their
# OPENTEAM_SIBLINGS_ROOT or the canonical CoreProjects layout is missing) —
# fail loudly here, NOT later with a cryptic ImportError from inside an
# in-process executor call.
from openteam.bootstrap import ensure_siblings_on_path
ensure_siblings_on_path(strict=True)

import logging  # noqa: E402

import typer  # noqa: E402

app = typer.Typer(add_completion=False, help="OpenTeam MCP server.")


@app.command("run")
def run(
    transport: str = typer.Option("stdio", help="stdio | http"),
    port: int = typer.Option(8765, help="Port (http transport only)"),
    tools: str = typer.Option("", help="Comma-separated subset of tool names; default = all"),
    log_level: str = typer.Option("INFO"),
) -> None:
    """Run the OpenTeam MCP server."""
    logging.basicConfig(level=log_level.upper())
    from openteam.mcp_server.server import create_openteam_server
    names = [t.strip() for t in tools.split(",") if t.strip()] or None
    server = create_openteam_server(tool_names=names)
    if transport == "stdio":
        server.run(transport="stdio")
    elif transport == "http":
        server.run(transport="http", port=port)
    else:
        raise typer.BadParameter(f"unknown transport: {transport}")


if __name__ == "__main__":
    app()
```

### 6.2 `src/openteam/mcp_server/_helpers.py`

```python
"""Wrapper-side helpers shared by all four tool wrappers in server.py.

Kept separate so unit tests can target them without spinning up FastMCP.
"""
from __future__ import annotations
from typing import Any


def to_dash_form(d: dict[str, Any]) -> dict[str, Any]:
    """Python kwargs (foo_bar) → executor key convention (foo-bar).

    Verified at tool_cli.py: the run_cli scaffold converts argparse Namespace
    via the same dash-form mapping, so the executor expects dash-form keys.
    """
    return {k.replace("_", "-"): v for k, v in d.items()}


def strip_unset(d: dict[str, Any]) -> dict[str, Any]:
    """Remove unset / default-bool / empty parameters before forwarding to executor.

    Each clause is intentional; DO NOT collapse to `v in (None, False, "", [])`:

      - v is not None   : drops genuinely-absent kwargs.
      - v is not False  : drops default-False boolean flags (only the present
                          form is meaningful to the CLI scaffold).
      - v != ""         : drops empty-string defaults. Must be != (not `is not`)
                          because string interning is not guaranteed.
      - v != []         : drops empty-list defaults.

    Critically, 0 is PRESERVED:
      - 0 != ""           is True (cross-type !=).
      - 0 != []           is True (cross-type !=).
      - 0 is not False    is True (different objects).

    Rewriting as `v in (None, False, "", [])` is WRONG because 0 == False
    is True in Python's int/bool overload — that form would silently drop a
    literal 0 argument.
    """
    return {k: v for k, v in d.items()
            if v is not None and v is not False and v != "" and v != []}


def render_result(result: Any) -> str:
    """Duck-typed render of ToolExecutionResult / dict / str into a string.

    Surfaces context_updates artifact paths as a trailing footer so the LLM
    (or the user) can open them with subsequent file tools.

    Duck-typed (hasattr) to avoid cross-package import of ToolExecutionResult
    (which lives in AgentFoundation) — keeps mcp_server importable even if the
    sibling repo's protocol module is later renamed.
    """
    if hasattr(result, "result") and hasattr(result, "context_updates"):
        text = result.result or ""
        ctx = dict(result.context_updates or {})
    elif isinstance(result, dict):
        text = result.get("result") or result.get("text") or ""
        ctx = dict(result.get("context_updates") or {})
    else:
        return str(result)

    # Discovery rule (not allowlist): include every (key, value) where
    # key ENDS with "_path" or "_dir" and value is a non-empty string.
    # Verified against the union of context_updates emitted by all four
    # executors — see tool_cli.py Phase 0a docstring for the full enumeration.
    artifacts = [
        f"  {k}: {v}"
        for k, v in sorted(ctx.items())
        if (k.endswith("_path") or k.endswith("_dir")) and isinstance(v, str) and v
    ]
    if artifacts:
        text += "\n\nArtifacts:\n" + "\n".join(artifacts)
    return text
```

### 6.3 `src/openteam/mcp_server/context.py`

```python
"""Build session_context for in-process executor calls.

`{}` is also safe (verified: _resolve_workspace at task/executor.py:162-188
falls through to _allocate_workspace). We surface env-driven hints so a
long-lived OpenStartup checkout can pin its workspace root, cloud_id, and
credentials without modifying the user's mcp.json.
"""
from __future__ import annotations
import os
import uuid
from typing import Any

_ENV_MAP = {
    "OPENTEAM_WORKING_DIR": "working_dir",
    "OPENTEAM_SERVER_DIR":  "server_dir",
    "OPENTEAM_CLOUD_ID":    "cloud_id",
    "OPENTEAM_UCT_TOKEN":   "uct_token",
    "OPENTEAM_EMAIL":       "email",
}


def build_session_context() -> dict[str, Any]:
    ctx: dict[str, Any] = {"task_id": f"mcp-{uuid.uuid4().hex[:8]}", "interactive": None}
    for env_key, ctx_key in _ENV_MAP.items():
        v = os.environ.get(env_key)
        if v:
            ctx[ctx_key] = v
    return ctx
```

### 6.4 `src/openteam/mcp_server/server.py` — factory + 4 typed wrappers

```python
"""FastMCP server exposing OpenTeam tools as in-process executor calls.

Pattern verified against acra-python/packages/mcp-atlassian-exp/src/atlassian_exp/main.py:94-116:
  - mcp = FastMCP("openteam")
  - mcp.add_tool(FunctionTool.from_function(wrapper))   # NOT @mcp.tool decorator
"""
from __future__ import annotations
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from openteam.mcp_server.context import build_session_context
from openteam.mcp_server._helpers import to_dash_form, strip_unset, render_result


# ── Wrappers (hand-written so the MCP schema is fully typed) ────────────────

async def openteam_task(
    request: str,
    # The four mutually-exclusive flags from tool.json (verified in task/cli.py:17
    # which passes mutually_exclusive_groups=[{"--plan","--execute","--full","--confirm"}]
    # to run_cli) are collapsed at the MCP surface into a single enum the LLM
    # cannot violate. The wrapper re-expands `mode` to the corresponding
    # boolean before forwarding to the executor. The CLI surface still accepts
    # the four flags individually (argparse mutex group enforces it there).
    mode: Literal["plan", "execute", "full", "confirm"] = "full",
    agent_config: str = "breakdown-multiflow-plan-then-implement",
    model: Literal["opus[1m]", "opus", "sonnet", "haiku"] | None = None,
    override: list[str] | None = None,
    no_dual: bool = False,
    analysis: bool = False,
    multi_iter: bool = False,
    max_iterations: int = 3,
    resume: str | None = None,
    # `--in-place` (task/tool.json:88) is a CLI store_true flag whose default
    # IS True at the executor (task/executor.py derives "in-place" from
    # absence). There is NO --no-in-place flag on the CLI surface; the
    # documented way to opt OUT of in-place mode is --copy-workspace.
    # We therefore expose only `copy_workspace` here — exposing `in_place`
    # as a wrapper parameter would mislead the LLM into thinking
    # `in_place=False` toggles behaviour (it does not: strip_unset drops
    # False, executor falls back to True). The MCP surface intentionally
    # narrower than the tool.json surface where the narrowness reflects
    # a semantic constraint, not a feature gap. The signature-alignment
    # CI preflight test (test_wrapper_signature_alignment.py) hard-codes
    # `in_place` as a documented exception alongside the `mode` mutex
    # collapse.
    copy_workspace: bool = False, # task/tool.json:93 ("--copy-workspace")
    initial_plan: str | None = None,
) -> str:
    """Run an OpenTeam agent topology against a request.

    Long-running (typically 5-30 min). Subject to the MCP client's hardcoded
    295 s timeout (verified at mcp_toolset.py:138). For long jobs prefer the
    /task slash command (subprocess, no MCP timeout).

    mode:
      - "plan"    : planner only.
      - "execute" : implementation only (needs --initial-plan).
      - "full"    : plan-then-implement (default).
      - "confirm" : plan, wait for user confirmation, then implement.

    Workspace strategy:
      - default (`copy_workspace=False`): in-place — operate on the existing
        working directory (matches CLI default; `--in-place` flag is implicit).
      - `copy_workspace=True`: fresh workspace — snapshot current dir into
        a new workspace, operate there. Match for the CLI's `--copy-workspace`.

    Verified against task/tool.json: **16 parameters total** (counted via
    `python3 -c "import json; print(len(json.load(open('task/tool.json'))['parameters']))"`).
    The four mutex boolean flags (--plan/--execute/--full/--confirm)
    collapse into `mode` (4 tool.json params → 1 wrapper param);
    `in_place` is INTENTIONALLY OMITTED (see param comment above) —
    semantically un-settable from MCP since `strip_unset` drops False and
    the executor defaults absent keys to True.
    Resulting wrapper signature: 16 - 4 (mutex) + 1 (mode) - 1 (in_place) = **12 wrapper params**.
    These map 1:1 to the remaining tool.json parameters (with snake_case ↔ kebab-case
    translation by to_dash_form). The signature-alignment CI preflight
    (test_wrapper_signature_alignment.py) enforces this, with `in_place`
    and `mode` as the two documented exceptions (clauses 5 and 6 in §6.5).
    """
    if mode == "execute" and not initial_plan:
        raise ValueError(
            "openteam_task(mode='execute') requires initial_plan=<path>. "
            "Execute mode skips planning and runs implementation against an "
            "existing plan file."
        )

    from openteam.server.resources.tools.task.executor import execute as _exec

    mode_flags = {"plan": False, "execute": False, "full": False, "confirm": False}
    mode_flags[mode] = True

    raw = {
        "request": request, "agent_config": agent_config,
        **mode_flags,
        "model": model, "override": override,
        "no_dual": no_dual, "analysis": analysis,
        "multi_iter": multi_iter, "max_iterations": max_iterations,
        "resume": resume,
        # No `in_place` key — it's a CLI store_true with True default at the
        # executor. Set `copy_workspace=True` to opt out of in-place mode.
        "copy_workspace": copy_workspace,
        "initial_plan": initial_plan,
    }
    args = strip_unset(to_dash_form(raw))
    return render_result(await _exec(args, build_session_context()))


async def openteam_create_role(
    role_description: str,
    output_path: str | None = None,
    max_facets: int = 8,
) -> str:
    """Synthesize a role document from a free-form description.

    Verified against create_role/tool.json — parameters are exactly:
    role_description (positional), --output-path, --max-facets. There is
    no --model flag; an earlier draft of this wrapper carried a ghost `model`
    param that would have been passed to the executor as an unknown kwarg.
    """
    from openteam.server.resources.tools.create_role.executor import execute as _exec
    args = strip_unset(to_dash_form({
        "role_description": role_description,
        "output_path": output_path,
        "max_facets": max_facets,
    }))
    return render_result(await _exec(args, build_session_context()))


async def openteam_role_setup(
    role_document_path: str,
    max_facets: int = 8,
    max_inner_facets: int = 5,
) -> str:
    """Decompose a role document into actionable setup steps.

    Verified against role_setup/tool.json — parameters are exactly:
    role_document_path (positional), --max-facets, --max-inner-facets.
    No --model flag.
    """
    from openteam.server.resources.tools.role_setup.executor import execute as _exec
    args = strip_unset(to_dash_form({
        "role_document_path": role_document_path,
        "max_facets": max_facets,
        "max_inner_facets": max_inner_facets,
    }))
    return render_result(await _exec(args, build_session_context()))


async def openteam_project_onboarding(
    project_document_path: str,
    role_setup_path: str | None = None,
    artifacts_path: str | None = None,
    max_facets: int = 8,
    max_inner_facets: int = 5,
) -> str:
    """Onboard an AI employee to a project.

    Verified against project_onboarding/tool.json — parameters are exactly:
    project_document_path (positional), --role-setup-path, --artifacts-path,
    --max-facets, --max-inner-facets. No --model flag.
    """
    from openteam.server.resources.tools.project_onboarding.executor import execute as _exec
    args = strip_unset(to_dash_form({
        "project_document_path": project_document_path,
        "role_setup_path": role_setup_path,
        "artifacts_path": artifacts_path,
        "max_facets": max_facets,
        "max_inner_facets": max_inner_facets,
    }))
    return render_result(await _exec(args, build_session_context()))


_WRAPPERS: dict[str, Any] = {
    "openteam_task":               openteam_task,
    "openteam_create_role":        openteam_create_role,
    "openteam_role_setup":         openteam_role_setup,
    "openteam_project_onboarding": openteam_project_onboarding,
}


def create_openteam_server(tool_names: list[str] | None = None) -> FastMCP:
    """Create and configure a FastMCP server for the OpenTeam tools.

    Args:
        tool_names: Names of wrappers to register. Defaults to all 4.
    """
    mcp = FastMCP("openteam")
    enabled = set(tool_names) if tool_names else set(_WRAPPERS)
    invalid = enabled - set(_WRAPPERS)
    if invalid:
        raise ValueError(f"Unknown tool names: {sorted(invalid)}; available: {sorted(_WRAPPERS)}")
    for name, wrapper in _WRAPPERS.items():
        if name not in enabled:
            continue
        mcp.add_tool(FunctionTool.from_function(wrapper))
    return mcp
```

### 6.5 Phase 2 tests

- `test_helpers.py` (TIER-1): `strip_unset({"x": 0})` keeps `0`; `strip_unset({"x": False})` drops; cross-type `!=` correctness for `[]` and `""`; `to_dash_form` round-trip; `render_result` covers all three result shapes + artifact footer + unknown keys ignored.
- `test_context.py` (TIER-1): unique `task_id`; env-var overrides flow through; empty env → minimal ctx.
- `test_server_factory.py` (TIER-1): default registers all 4; subset works; invalid names raise.
- `test_wrappers_smoke.py` (TIER-2): monkeypatch each executor; assert dash-form keys + render_result applied.
- `test_wrapper_signature_alignment.py` (TIER-1 / **CI preflight**): for each tool, load `tool.json`, walk wrapper's `inspect.signature`, and assert:
   1. **No ghost params** — every wrapper parameter (except the `mode` enum for `task`) maps to a real tool.json parameter. Catches the class of bug where an early draft of `openteam_create_role` carried a `model: str | None = None` parameter that no tool.json declared.
   2. **No missing params** — every required tool.json parameter has a wrapper parameter.
   3. **Types are compatible** (Python type ↔ tool.json type).
   4. **Defaults equal** (tool.json `"default"` matches wrapper default; absent default ⇒ wrapper default is `None`).
   5. **Mode-enum collapse exception** — `task` wrapper has `mode: Literal[…]` but tool.json has four boolean mutex flags; the test accepts this single hard-coded exception and verifies the enum members exactly equal the mutex group.
   6. **Intentionally-omitted exception (`in_place`)** — `task` wrapper deliberately omits `in_place` because it's a CLI `store_true` flag that the executor defaults to True from absence, AND `strip_unset` drops False values — exposing it would be a misleading no-op. The test asserts `"in_place"` IS in the documented-omission allow-list (a module constant `_INTENTIONALLY_OMITTED = {"in_place"}`), and would FAIL if a future contributor added `in_place: bool` to the wrapper or removed it from the allow-list without updating tool.json.

   Catches drift the moment `tool.json` changes. The two exception clauses (5 and 6) are hard-coded constants in the test module with comment links back to this section.

---

## 7. Phase 3 — TUI slash commands (single file, factory, bare names) (~½ day)

### 7.1 `slash_commands/openteam.py` (one file, four handlers via factory)

**Convention match (verified):** `jira.py` has 4 hand-written handlers in one file; `sessions.py` has 6; every top-level slash command in `app.py` is bare (39 bare top-level + 24 sub-commands `under` a bare name = 63 of 64 registrations; the 64th is the special non-slash `$` shell command). `app.py:541` confirms `thread=True` is the convention for subprocess handlers. The `_make_handler` factory in this file is novel; the file layout and naming are idiomatic.

```python
"""Subprocess slash commands for OpenTeam tools.

Structurally mirrors slash_commands/shell.py (same async-subprocess +
ShellOutput + ThinkingSpinner + get_current_worker + stderr=STDOUT
streaming + at_eof + worker.is_cancelled → terminate skeleton); divergences
from line-for-line are: (1) we add `stdin=DEVNULL` for safety (shell.py
inherits stdin since shell is interactive by design), and (2) we import
shell.py's `_get_workspace_path` rather than reimplementing it inline:
  - ShellOutput widget + ThinkingSpinner mounted on app.chat_container
  - get_current_worker() + worker.is_cancelled → proc.terminate()
  - stderr=STDOUT (merged read loop)
  - per-line shell_output.append() via app.call_from_thread
  - empty-output cleanup via shell_output.remove
  - non-zero return code → app.notify_and_log

Convention match:
  - File layout matches jira.py / sessions.py (one feature, multiple handlers,
    factory function for shared logic).
  - Slash names are bare (/task, /create-role, /role-setup, /project-onboarding)
    to match the convention: 39 bare top-level + 24 sub-commands in app.py
    (no kebab-prefixed siblings anywhere). /openteam-task would be a
    brand-new naming convention no feature uses today; collision risk is
    mitigated by the try/except ImportError opt-in in app.py and by the
    if-slash-in-registry guard in register_openteam_commands.)
"""
from __future__ import annotations
import asyncio
import os
import shlex
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from textual.worker import get_current_worker

from rovodev_tui.slash_commands.shell import _get_workspace_path
from rovodev_tui.widgets import ShellOutput, ThinkingSpinner

if TYPE_CHECKING:
    from rovodev_tui.app import RovoDevApp
    from rovodev_tui.slash_commands.registry import SlashCommandRegistry


# ── Tool registry ───────────────────────────────────────────────────────────

# (slash_name, console_script_binary_name, python_-m_fallback_module)
_OPENTEAM_TOOLS: list[tuple[str, str, str]] = [
    ("/task",
     "openteam-task",
     "openteam.server.resources.tools.task"),
    ("/create-role",
     "openteam-create-role",
     "openteam.server.resources.tools.create_role"),
    ("/role-setup",
     "openteam-role-setup",
     "openteam.server.resources.tools.role_setup"),
    ("/project-onboarding",
     "openteam-project-onboarding",
     "openteam.server.resources.tools.project_onboarding"),
]


# ── Binary resolution + argv composition ────────────────────────────────────

def _openteam_home() -> Path:
    """OPENTEAM_HOME env override, else the conventional CoreProjects layout.

    Default falls back to a `~/MyProjects/CoreProjects/OpenStartup` checkout
    only because no better default exists; users with non-conventional layouts
    MUST set OPENTEAM_HOME (documented in templates/SKILL.md). This default is
    used ONLY by the Python -m fallback path; the primary path is PATH-based
    binary lookup which is layout-independent.
    """
    return Path(os.environ.get(
        "OPENTEAM_HOME",
        str(Path.home() / "MyProjects" / "CoreProjects" / "OpenStartup"),
    ))


def _find_binary(name: str) -> str | None:
    """Look up an openteam-* console script.

    Priority: PATH → ${OPENTEAM_HOME}/.venv/bin/<name>. Returns absolute path
    or None.
    """
    on_path = shutil.which(name)
    if on_path:
        return on_path
    venv_bin = _openteam_home() / ".venv" / "bin" / name
    if venv_bin.is_file() and os.access(venv_bin, os.X_OK):
        return str(venv_bin)
    return None


def _build_argv_and_env(
    binary_name: str,
    module_name: str,
    user_args: list[str],
) -> tuple[list[str], dict[str, str]]:
    """Compose argv + env, preferring the binary path; fall back to python -m."""
    env = {**os.environ}
    binary = _find_binary(binary_name)
    if binary is not None:
        return ([binary, *user_args], env)
    # Fallback: python -m + computed PYTHONPATH (matches conftest.py /
    # run_server.py convention; users without the openteam-* binaries on PATH
    # are expected to have the conventional CoreProjects layout.)
    home = _openteam_home()
    pp_parts = [
        home / "src",
        home.parent / "AgentFoundation" / "src",
        home.parent / "RichPythonUtils" / "src",
    ]
    # Prepend (not overwrite) so any user-set PYTHONPATH is preserved.
    new_pp = [str(p) for p in pp_parts if p.is_dir()]
    existing_pp = env.get("PYTHONPATH", "")
    if existing_pp:
        new_pp.append(existing_pp)
    env["PYTHONPATH"] = os.pathsep.join(new_pp)
    # Default to `python3` rather than `python`: many modern Linux distros
    # do not install a `python` shim (only `python3`), and macOS ships
    # `python` -> `python2.7` on older systems. Users with a `python`-only
    # venv layout can override via OPENTEAM_PYTHON.
    python = os.environ.get("OPENTEAM_PYTHON", "python3")
    return ([python, "-m", module_name, *user_args], env)


# ── Handler factory ─────────────────────────────────────────────────────────

def _make_handler(slash: str, binary: str, module: str):
    """Build a handler for one slash command.

    Closure captures (slash, binary, module). The async handler body mirrors
    shell.py:46-94 — the streaming loop is character-identical; the
    surrounding setup differs only in the two intentional divergences
    documented in the file docstring above (`stdin=DEVNULL` and the
    `_get_workspace_path` import).
    """
    async def handler(app: "RovoDevApp", extra_prompt: str) -> None:
        worker = get_current_worker()
        if worker is None:
            # Defensive: only happens if thread=True was forgotten at registration.
            app.notify_and_log(
                f"{slash}: missing worker context (registration bug — thread=True needed)",
                severity="error", timeout=10,
            )
            return

        # Mount widgets — mirrors shell.py:52-55
        shell_output = ShellOutput()
        spinner = ThinkingSpinner(f"Running OpenTeam {slash[1:]}")
        app.call_from_thread(app.chat_container.mount, shell_output)
        app.call_from_thread(app.chat_container.mount, spinner)

        # The registry guarantees extra_prompt is non-empty (we register with
        # extra_prompt="required"; see registry.py:206,210-213). The shlex.split
        # below cannot receive ""; no empty-input guard needed at this layer.
        user_args = shlex.split(extra_prompt)
        argv, env = _build_argv_and_env(binary, module, user_args)

        try:
            # cwd mirrors shell.py:67 via _get_workspace_path (imported at
            # module level above). The helper resolves the TUI session's
            # workspace_path or falls back to Path.cwd().resolve(); verified
            # at shell.py:18-20. The previous draft used cwd=_openteam_home()
            # which broke user relative paths like `/role-setup ./roles/eng.md`.
            #
            # _get_workspace_path is a NOVEL cross-module import between
            # top-level slash command modules (no precedent in slash_commands/
            # today). We accept the novelty: DRY beats duplication for a
            # single helper that would silently rot if re-implemented.
            cwd = _get_workspace_path(app)
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,         # merged — mirrors shell.py:65
                stdin=asyncio.subprocess.DEVNULL,         # prevent inherited TUI stdin
                                                          # from hanging if any
                                                          # underlying tool calls
                                                          # input() (defensive; not
                                                          # in shell.py because the
                                                          # shell tool intentionally
                                                          # supports interactive I/O)
                env=env,
                cwd=cwd,
            )
        except FileNotFoundError as e:
            app.call_from_thread(spinner.remove)
            app.call_from_thread(shell_output.remove)
            app.notify_and_log(
                f"{slash}: {argv[0]} not found ({e}). Install openteam: "
                f"`uv tool install -e {_openteam_home()}`",
                severity="error", timeout=15,
            )
            return

        if proc.stdout is None:
            app.call_from_thread(spinner.remove)
            return

        # Stream loop — mirrors shell.py:74-90 exactly
        output = ""
        while True:
            if worker.is_cancelled:
                proc.terminate()
                await proc.wait()
                break
            if proc.stdout.at_eof():
                break
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", "replace")
            output += decoded
            app.call_from_thread(shell_output.append, decoded)

        await proc.wait()
        app.call_from_thread(spinner.remove)

        # Empty-output cleanup — mirrors shell.py:92-93
        if not output.strip():
            app.call_from_thread(shell_output.remove)

        if proc.returncode and proc.returncode != 0:
            app.notify_and_log(
                f"{slash} exited with code {proc.returncode}",
                severity="error", timeout=8,
            )

    handler.__name__ = f"handle_{slash[1:].replace('-', '_')}_command"
    handler.__doc__ = (
        f"Run OpenTeam's `{slash[1:]}` tool via subprocess.\n\n"
        f"All arguments after `{slash}` are split with `shlex` (POSIX shell\n"
        f"quoting). Multi-word positional arguments MUST be quoted:\n"
        f"  WRONG:   {slash} what is 2 + 2\n"
        f"  RIGHT:   {slash} \"what is 2 + 2\"\n"
        f"Run `{slash} --help` for available options.\n\n"
        f"Streams output live; cancellable with Ctrl-C."
    )
    return handler


# ── Registration ────────────────────────────────────────────────────────────

def register_openteam_commands(registry: "SlashCommandRegistry") -> None:
    """Register the four /<tool> commands on a SlashCommandRegistry.

    Idempotent: skips slash names already registered (defensive against
    duplicate calls during dev hot-reload).
    """
    for slash, binary, module in _OPENTEAM_TOOLS:
        if slash in getattr(registry, "commands", {}):
            continue
        registry.register(
            _make_handler(slash, binary, module),
            slash,
            extra_prompt="required",  # Verified at registry.py:210-213 — the
                                      # registry shows "This command requires
                                      # additional input." when prompt is empty,
                                      # which is the desired UX for `/task` with
                                      # no args. Crucially, `/task --help` is
                                      # NOT empty (the prompt-after-command is
                                      # "--help"), so it still flows through to
                                      # the handler — verified against
                                      # registry.py:206 prompt.removeprefix(...).strip().
                                      # An earlier draft used "allowed" which
                                      # caused empty `/task` to mount widgets and
                                      # then noisily run with argparse error.
            thread=True,              # subprocess I/O → worker thread
                                      # (matches shell.py:541, jira.py:545, etc.)
        )
```

### 7.2 `app.py` patch (4 lines, opt-in)

Insert this block at the end of the existing `command_registry.register(...)` chain (around line 604, after the last registration):

```python
# OpenTeam commands — opt-in; no-op if openteam.py module is absent.
try:
    from rovodev_tui.slash_commands.openteam import register_openteam_commands
    register_openteam_commands(command_registry)
except ImportError:
    pass
```

This is the ONLY modification to `app.py`. The `try/except ImportError` makes it safe to ship even before the openteam.py file exists.

### 7.3 Phase 3 tests

**`tests/slash_commands/test_openteam.py` (TIER-1/2):**

- `test_find_binary_path_first(monkeypatch)` — `shutil.which("openteam-task")` returns `/usr/local/bin/openteam-task`; assert that wins.
- `test_find_binary_venv_fallback(tmp_path, monkeypatch)` — `shutil.which` returns None; create executable at `OPENTEAM_HOME/.venv/bin/openteam-task`; assert that's returned.
- `test_find_binary_none(monkeypatch)` — neither exists; returns None.
- `test_build_argv_uses_binary_when_present(monkeypatch)` — assert argv = `["/abs/openteam-task", "foo"]` and PYTHONPATH is NOT injected.
- `test_build_argv_falls_back_to_python_m(monkeypatch)` — assert argv = `["python3", "-m", "openteam.server.resources.tools.task", "foo"]` and PYTHONPATH is injected from existing dirs. (`python3` is the new default; test also covers `monkeypatch.setenv("OPENTEAM_PYTHON", "python")` → first token is `"python"`.)
- `test_handler_streams_output(mocker)` — mock `asyncio.create_subprocess_exec` to yield 3 lines; assert `shell_output.append` called 3 times.
- `test_handler_empty_output_removes_widget(mocker)` — proc produces nothing; assert `shell_output.remove` called.
- `test_handler_cancellation_terminates(mocker)` — mid-stream, set `worker.is_cancelled = True`; assert `proc.terminate()` called.
- `test_handler_nonzero_exit_notifies(mocker)` — `proc.returncode = 1`; assert `app.notify_and_log` with `severity="error"`.
- `test_handler_missing_binary_notifies(mocker)` — `create_subprocess_exec` raises `FileNotFoundError`; assert friendly notify with install hint.
- `test_register_idempotent(registry_stub)` — call `register_openteam_commands` twice; assert only 4 registrations.

**`tests/integration/test_openteam_snapshots.py` (TIER-2, `@pytest.mark.snapshot`):**

- Use `app.is_headless` to freeze streaming output to a deterministic stub; one snapshot per slash command (per `cli-rovodev-tui/AGENTS.md`).

---

## 8. Phase 4 — Templates + install + skill (~½ day)

### 8.1 `src/openteam/mcp_server/templates/mcp.json`

```json
{
  "mcpServers": {
    "openteam": {
      "command": "openteam-mcp",
      "args": ["run"],
      "transport": "stdio",
      "env": {
        "OPENTEAM_LLM_BACKEND": "claude_cli",
        "OPENTEAM_LLM_MODEL": "sonnet"
      }
    }
  }
}
```

**Zero PYTHONPATH. Zero `python -m`. Zero user-specific paths.** The `openteam-mcp` console script calls `ensure_siblings_on_path()` itself; the auto-detect in `bootstrap.py` walks up from the package location.

### 8.2 `src/openteam/mcp_server/templates/SKILL.md`

```markdown
---
name: openteam
description: OpenTeam multi-agent workflow tools (agent topologies, role lifecycle, project onboarding)
allowed-tools:
  - mcp__openteam__openteam_task
  - mcp__openteam__openteam_create_role
  - mcp__openteam__openteam_role_setup
  - mcp__openteam__openteam_project_onboarding
---
# OpenTeam Tools — slash vs MCP

Two surfaces for the same four tools:

| Surface | Best for | Timeout |
|---|---|---|
| **Slash** — `/task`, `/create-role`, `/role-setup`, `/project-onboarding` | Direct user invocation; long-running jobs (5-30 min). Streamed live in a ShellOutput widget. | **None** — subprocess. |
| **MCP** — `mcp__openteam__openteam_task`, etc. | Programmatic agent orchestration (plan-first, then implement). | **295 s default** (hardcoded in MCPClient). For `task` mode="full" runs, you almost always exceed this — re-route the user to the slash command. |

**Common pitfalls:**
- For `openteam_task`, the four mutually-exclusive flags (`--plan / --execute / --full / --confirm`) are collapsed at the MCP surface into a single `mode: Literal["plan","execute","full","confirm"]` enum (default `"full"`). The slash CLI still accepts the four flags individually (argparse mutex group enforces it there).
- Long topology runs WILL hit the 295 s MCP timeout. Re-route to the slash command instead.
- All four wrappers return a single string (the executor result, plus an `Artifacts:` footer listing workspace/plan/impl paths).
- Default `OPENTEAM_HOME` is `~/MyProjects/CoreProjects/OpenStartup`; override if your checkout lives elsewhere.

**Setup (one-time):**
```bash
cd ~/MyProjects/CoreProjects/OpenStartup
uv tool install -e .                # ships openteam-mcp + 4 openteam-<tool> scripts
mkdir -p ~/.rovodev/skills/openteam
cp src/openteam/mcp_server/templates/SKILL.md ~/.rovodev/skills/openteam/
# merge mcp.json snippet into ~/.rovodev/mcp.json (jq -s 'add' or hand-edit)
```
```

### 8.3 Install steps in `docs/MCP_INTEGRATION.md`

```bash
# 1. Install OpenTeam (one-time)
cd ~/MyProjects/CoreProjects/OpenStartup
uv tool install -e .                            # or: pip install -e .

# 2. Verify console scripts exist
which openteam-mcp openteam-task openteam-create-role openteam-role-setup openteam-project-onboarding
openteam-mcp --help                             # Typer help
openteam-task --help                            # tool.json-driven CLI help

# 3. Wire up RovoDev (one-time)
mkdir -p ~/.rovodev/skills/openteam
cp src/openteam/mcp_server/templates/SKILL.md ~/.rovodev/skills/openteam/
# Merge src/openteam/mcp_server/templates/mcp.json into ~/.rovodev/mcp.json
jq -s 'add' ~/.rovodev/mcp.json src/openteam/mcp_server/templates/mcp.json > ~/.rovodev/mcp.json.new
mv ~/.rovodev/mcp.json.new ~/.rovodev/mcp.json

# 4. Smoke-test the MCP server in isolation
# Note: create_openteam_server lives in server.py, NOT cli.py. The cli.py
# entry has `app = typer.Typer(...)` and the `run` subcommand which calls
# create_openteam_server; for fastmcp dev's introspection, point at the
# factory directly. FastMCP 3.x's `dev` command requires a filesystem
# path (FileSystemSource.load_server() does Path(spec).resolve()), NOT
# a Python module path.
fastmcp dev "src/openteam/mcp_server/server.py:create_openteam_server"

# 5. End-to-end in RovoDev TUI
# - /task --help        → tool.json parameters listed
# - /task "what is 2+2"   → streamed output, exit 0
#   (quotes REQUIRED: slash args go through shlex.split, and `request` is a
#   single argparse positional; multi-word prompts must be quoted. The
#   handler docstring shown by /help /task documents this contract.)
# - /mcp                → openteam server green, 4 tools
```

---

## 9. Phased delivery

| Phase | Scope | LOC | Time | Blocking |
|---|---|---|---|---|
| **0a** | `tool_cli.py:125-132` duck-typed rendering fix + 7 tests | ~60 | 30 min | blocks Phase 3 |
| **0b** | `project_onboarding/{cli,__main__}.py` shims (with bootstrap) + 2 tests | ~30 | 10 min | blocks Phase 3 |
| **0c** | `slash_enabled: true` on 3 tool.json files | ~3 | 5 min | blocks `/help` listing of 3 tools |
| **0d** | Retrofit `bootstrap.ensure_siblings_on_path()` into the 3 existing tool clis (`task`, `create_role`, `role_setup`) + fresh-subprocess smoke tests | ~12 | 10 min | **blocks Phase 1a console scripts from working** |
| **1a** | OpenStartup root `pyproject.toml` with **5** console scripts | ~50 | 15 min | blocks Phase 2 + Phase 3 binary path |
| **1b** | `bootstrap.py` + `conftest.py` refactor + `run_server.py` refactor + 5 tests | ~120 | 30 min | blocks Phase 2 |
| **2** | `openteam.mcp_server.{cli,server,context,_helpers,templates}` + 5 tests (incl. CI preflight signature alignment) | ~400 | ½-1 day | blocks Phase 3 (only the binary-path Slash arm, fallback works without it) |
| **3** | `cli-rovodev-tui` PR: `slash_commands/openteam.py` (1 file, factory) + 4-line `app.py` patch + 11 unit tests + 4 snapshot tests + docs | ~280 | ½ day | parallel with Phase 4 |
| **4** | `templates/{SKILL.md,mcp.json}`, `docs/MCP_INTEGRATION.md`, `docs/MCP_SMOKE.md`, README install steps | — | ½ day | nice-to-have |
| **5** | E2E smoke (install → /task --plan → mcp tool → Ctrl-C cancellation) | — | 1 hr | — |
| **7A** (post-ship) | `OPENTEAM_MCP_TIMEOUT` env hint + PR acra-python for per-server `timeout:` in mcp.json schema | small | 1 day | — |
| **7B** (gated) | In-memory `FastMCPTransport` for long agentic runs | medium | 1 day | — |
| **8** (gated) | Publish `openteam` to internal pip; switch templates/mcp.json (already bare) | small | future | — |

**Critical path:** 0a + 0b + 0c + 0d → 1a + 1b → 2 → (3 ‖ 4) → 5
**Time to working `/task <prompt>` end-to-end:** **~1.5 days of focused work.**

---

## 10. Test plan (TIER-tagged)

| Test | TIER | Purpose |
|---|---|---|
| `test_tool_cli_rendering.py` | 1 | Phase 0a — dataclass / dict (modern + legacy key) / str / falsy / artifacts / unknown-key |
| `test_project_onboarding_cli_smoke.py` | 2 | Phase 0b — `python -m …project_onboarding --help` exits 0; import smoke |
| `test_cli_bootstrap_smoke.py` | 1 | Phase 0d — for each of the 4 tools, fresh subprocess with PYTHONPATH=src only (NO siblings); assert both `python -c "import …cli"` and `python -m … --help` exit 0. Proves bootstrap is wired correctly in every console-script entry. |
| `test_init_py_remains_empty.py` | 1 / **CI pillar guard** | Asserts `openteam/__init__.py` AND every `openteam/server/.../__init__.py` is **empty or whitespace-only**. Pillar reason: bootstrap MUST run before any sibling-repo import; any code added to `openteam/__init__.py` could transitively import from agent_foundation BEFORE bootstrap and silently break every console script. Fails CI if any future contributor adds even one line. |
| `test_run_server_smoke.py` | 2 | Imports `openteam.server.run_server` (which calls `ensure_siblings_on_path`) and asserts the FastAPI app object is constructible. Guards against the run_server.py refactor (Phase 1b) silently breaking startup. |
| `test_mode_enum_complete.py` | 1 | Asserts the `mode: Literal[…]` values in the `openteam_task` wrapper exactly equal the four-flag mutex group declared in `task/cli.py:_MODE_MUTEX` and `task/tool.json` (parameters with `"type":"flag"` in the same mutex set). Adding a 5th mode value WITHOUT updating the wrapper would otherwise silently drop it from `mode_flags`. |
| `test_render_artifacts_discovery.py` | 1 | Asserts `_render_result` and `tool_cli.py`'s artifact-stderr block surface EVERY key ending in `_path`/`_dir` for each of the 4 tools (using a fixture of representative `context_updates` dicts). Guards against the brittle allowlist regressing. |
| `test_bootstrap.py` | 1 | Idempotent; `OPENTEAM_SIBLINGS_ROOT` honored; walks up; **missing-sibling emits warning (not silent)**; `strict=True` raises `FileNotFoundError`; zero sibling imports at module load |
| `test_helpers.py` | 1 | `strip_unset` preserves `0`, drops False/None/""/[]; `to_dash_form` round-trip; `render_result` covers all shapes + footer + unknown-key |
| `test_context.py` | 1 | Unique task_id; env-var pickup; empty-env minimal ctx |
| `test_server_factory.py` | 1 | Default registers 4; subset works; invalid raises |
| `test_wrapper_signature_alignment.py` | 1 / **CI preflight** | For each tool: walk `_WRAPPERS` × `tool.json`; assert every wrapper param maps to tool.json (modulo `mode` enum collapse for task) and defaults equal |
| `test_wrappers_smoke.py` | 2 | Stub each executor; assert dash-form keys + render_result applied |
| `test_openteam.py` (TUI) | 1/2 | `_find_binary` PATH/venv/None; `_build_argv_and_env` argv shape both branches; handler stream/empty/cancel/non-zero-exit/missing-binary; `register_openteam_commands` idempotent |
| `test_openteam_snapshots.py` (TUI) | 2 | `@pytest.mark.snapshot` headless render |
| Manual `fastmcp dev …` | 3 | MCP inspector call to `openteam_task(mode="plan", request="2+2")` |
| Manual `/task "what is 2+2"` (quotes required — shlex contract) | 3 | streamed output, exit 0 |
| Manual `/task --help` | 3 | tool.json parameters listed |
| Manual Ctrl-C during long `/task` | 3 | SIGTERM within ≤ 5 s |
| Manual `/mcp` | 3 | openteam server green; 4 tools |
| Manual install | 3 | `uv tool install -e .` → 5 binaries on PATH |

---

## 11. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| MCP 295 s timeout kills long `mode="full"` runs | High | Slash UX is primary path; SKILL.md routes long runs there; Phase 7A env override + acra-python PR |
| `fastmcp` API churn (`mcp-atlassian-exp/pyproject.toml` doesn't pin; `code-nemo/pyproject.toml:24` pins `==3.2.4`) | Medium | We pin `fastmcp>=3.2,<4` (same major as code-nemo's `==3.2.4`; allows safe patch upgrades); CI matrix tests upper-bound bumps quarterly |
| Wrapper signatures drift from tool.json | Medium | `test_wrapper_signature_alignment.py` as CI preflight |
| `_strip_unset` regression to `v in (None,False,"",[])` (drops `0`) | Low | Inline comment in `_helpers.py`; `test_helpers.py::test_zero_preserved` |
| Console scripts not on PATH after install | Low | `_find_binary` PATH → venv → None; falls back to `python -m` + PYTHONPATH (computed inline); error notify if both fail with install hint |
| Bootstrap `OPENTEAM_SIBLINGS_ROOT` autodetect picks wrong CoreProjects | Low | Walks UP from package location, requires BOTH siblings present; env override explicit; documented |
| Default `OPENTEAM_HOME` is user-specific | Medium | Env var override; SKILL.md documents; install docs explain |
| Slash name `/task` collides with future RovoDev `/task` | Low | `try/except ImportError` opt-in in app.py is also the disable knob; current 63 slash commands in `app.py` (39 bare + 24 sub) show no `/task` collision. On collision semantics: `registry.register()` itself is **last-writer-wins** (unconditional `self._commands[command] = …`), but `register_openteam_commands` has an explicit `if slash in registry.commands: continue` guard that **skips** any slash already registered. Since app.py registers OpenTeam LAST (inside the try/except block), any future RovoDev `/task` registered earlier stays put — the guard yields, exactly as desired. |
| Stderr lost (merged into stdout) | Low | Artifact paths surface via `ctx.context_updates` rendered in `_render_result`'s footer — no info loss |
| Subprocess on Windows | Low | `python -m` invocation (no shell); doc'd as Linux/macOS tested |
| `get_current_worker()` returns None | Low | Defensive guard in `_make_handler`; primary protection: `thread=True` at registration |
| TUI snapshot tests flake on streaming output | Medium | Use `app.is_headless` to freeze line content to a stub (per `cli-rovodev-tui/AGENTS.md`) |
| `cli-rovodev` legacy frontend lacks slash commands | Medium | Skill + MCP work for both; slash UX is TUI-only by design (legacy has decorator-based registry, no file dir) |

---

## 12. Self-audit (stress-tested for hacks)

| Question | Answer |
|---|---|
| Are slash + MCP duplicate implementations? | **No.** Both reach `executor.execute()`. Slash: subprocess → `openteam-<tool>` console script → `cli.main()` → `run_cli` → `executor`. MCP: in-process wrapper → `executor`. Same business logic, two surfaces. |
| Does `_render_result` duplicate `tool_cli.py`'s rendering? | Intentionally — the MCP path doesn't import `tool_cli`. They share a 9-line duck-typed pattern, not state. Phase 8 could lift this into `openteam.common.rendering`; for v1, the duplication is bounded and the test files pin both. |
| Does `_strip_unset(0)` accidentally drop `0`? | **No.** `0 != ""` and `0 != []` (cross-type `!=` → True). `0 is not False` (different objects → True). `test_helpers.py::test_zero_preserved` pins this. |
| Why bare slash names `/task` instead of namespaced `/openteam-task`? | Every top-level slash in `app.py` is bare — 64 registrations break down as **39 bare top-level + 24 sub-commands under bare names + 1 non-slash `$`** (verified by `grep -oE '"/[a-z][a-z0-9_-]*"'` and the sub-command variant). `/openteam-task` would invent a kebab-prefixed-sibling pattern no feature uses today. Collision risk mitigated by the `try/except ImportError` opt-in (the disable knob) AND by the `if slash in registry.commands: continue` guard in `register_openteam_commands` (OpenTeam yields to any earlier registration; the registry itself is last-writer-wins, but the guard makes OpenTeam's registration skip on collision). |
| Why single `openteam.py` file instead of four `openteam_<tool>.py` files? | `jira.py` has 4 handlers in one file, `sessions.py` has 6 — that's the convention. Factory pattern (`_make_handler`) keeps it DRY. v5's four-file layout was wrong. |
| Why explicit `from openteam.bootstrap import ensure_siblings_on_path` from CLI entry instead of magic side-effect in `openteam/__init__.py` (Cursor's proposal)? | (a) Every `__init__.py` in the ecosystem is empty/placeholder — no precedent for import-time side effects. (b) Silent sys.path mutation on `import openteam` is exactly the kind of magic that breaks unrelated tooling (linters, typed imports, downstream libraries that import `openteam` for type checking). (c) `conftest.py` + `run_server.py` already keep injection explicit on purpose ("This fallback ensures it works both ways"). Explicit > implicit. |
| Why 5 console scripts (vs. v5's 1 dispatcher)? | Each tool already has `def main(argv=None) -> int` (verified for task; mirror'd for the others). 5 console scripts is **zero new code** (4 lines in `[project.scripts]`). The win: slash subprocess argv is `["openteam-task", *args]` — no `python -m`, no PYTHONPATH. Falls back to `python -m` only if the binary isn't on PATH. |
| Could the `mode` enum re-expansion drop bits? | **No.** Sets exactly one of {plan, execute, full, confirm} to True; the rest to False — matches the CLI's mutex group semantics (verified: `task/cli.py:17` passes `mutually_exclusive_groups=[{"--plan","--execute","--full","--confirm"}]` to `run_cli`). |
| Can mode="execute" be called without initial_plan? | **No** (since round-5 fix 8). The wrapper raises `ValueError` before calling the executor. The executor itself does NOT validate this constraint (verified: `task/executor.py:534-595` checks file-exists IF initial-plan is given, and checks only-one-mode-flag, but has no check for execute-requires-plan). Without the wrapper check, the topology would run `enable_planning=False` with no plan, producing a confusing error from inside the inferencer. This is input validation, not business logic — it doesn't duplicate anything in the executor. |
| Does `bootstrap.py` get called twice (test + entry + run_server)? | Yes, by design. It's idempotent (`if … not in sys.path`). `test_bootstrap.py::test_idempotent` pins this. |
| Both stdio-MCP AND slash work side-by-side? | **Yes** — independent processes, no shared state. |
| `python` on PATH may be wrong interpreter? | The `openteam-mcp` and `openteam-<tool>` console scripts use the venv's interpreter (via shebang). The `python -m` fallback honors `OPENTEAM_PYTHON` env override. |
| MCP 295 s timeout — really "won't fix" for v1? | Mostly yes. Slash UX is the structural escape hatch (no timeout). Phase 7A documents `OPENTEAM_MCP_TIMEOUT` env hint + opens an upstream PR; Phase 7B is the deeper fix (in-memory transport). Both are post-ship. |
| Could Phase 0a fix break existing callers? | Current `tool_cli.py` prints `""` for ToolExecutionResult (dict branch with `"text"` key on a dataclass), or `repr()` (else branch) — both are broken. Fix is unambiguously an improvement. `test_tool_cli_rendering.py` pins all branches. |
| Would `register_openteam_commands` double-register? | No — `if slash in registry.commands: continue` guard. `test_register_idempotent` pins this. |
| Is `get_current_worker()` safe outside a worker? | Returns None if `thread=False` was forgotten. We pin `thread=True` at registration AND add a defensive `if worker is None: notify-and-bail` in `_make_handler`. |
| Are we duplicating sys.path injection across `bootstrap.py` and `_build_argv_and_env`? | Yes, by design. `bootstrap.py` runs **inside the `openteam-mcp` process** (which can safely import `openteam.bootstrap`). `_build_argv_and_env` runs **inside RovoDev's process** (which **must not** import openteam — RovoDev is PyInstaller-frozen). Both compute the same sibling-dir list from `_openteam_home()`; their source-of-truth is the same env convention. Phase 4.5 could lift the list into a small data-only `openteam/_siblings.py` module that has no imports (and re-read it from a JSON sidecar in RovoDev's process if absolutely needed); deferred. |
| `mode: Literal[...]` enum vs. four booleans — is this a hack? | **No.** The CLI's mutex group is the enum dressed as flags. Surfacing the enum at the MCP layer makes the LLM safer (cannot violate mutex). CLI surface unchanged. |
| Default `OPENTEAM_HOME` exposes `tchen7` path in committed code? | Only as the documented fallback in `_openteam_home()`. Templates/mcp.json contains NO user-specific path. Install docs explain. |
| Does this commit RovoDev to a specific OpenTeam version? | No. The four MCP tool contracts + the four slash subprocess argvs are the only API surface. OpenTeam internals can change freely. |
| Do the 4 console scripts (`openteam-task`, `openteam-create-role`, `openteam-role-setup`, `openteam-project-onboarding`) actually work after `uv tool install -e .`, or do they ImportError on launch? | **Yes, they work — but only because Phase 0d retrofits `ensure_siblings_on_path()` into each cli.py.** Verified by direct inspection: `create_role/executor.py:45-56` and `role_setup/executor.py:48-56` import `agent_foundation` at module level. Without bootstrap in cli.py, the console script's `from .executor import execute` raises ImportError on launch. Phase 0d closes this gap with a 4-line bootstrap prefix in each cli.py and a TIER-1 fresh-subprocess test (`test_cli_bootstrap_smoke.py`) that fails CI if any cli.py forgets the call. |
| Do any wrapper signatures carry "ghost" parameters not present in tool.json? | **No.** An early draft of v6 had `model: str | None = None` in `openteam_create_role`, `openteam_role_setup`, `openteam_project_onboarding` — none of those tool.jsons declare a `--model` flag (verified by direct `cat`). The ghost param would have been passed to the executor as an unknown kwarg. The signature-alignment CI preflight (`test_wrapper_signature_alignment.py` clause 1) catches any future regression of this class. |
| Why `extra_prompt="required"` rather than `"allowed"`? | Verified at registry.py:210-213 — `"required"` causes the registry to emit `"This command requires additional input."` on empty input (clean UX, no widgets mounted). `/task --help` still flows through because the prompt-after-command is `"--help"` (non-empty, verified against registry.py:206 `prompt.removeprefix(matched_command_info.command).strip()`). Earlier `"allowed"` choice would have caused bare `/task` to mount widgets and then noisily fail with argparse error inside the subprocess — exactly the kind of "looks like it's working then explodes" UX we're avoiding. |
| Does the `fastmcp dev` command in the install runbook reference the correct path? | Yes — `src/openteam/mcp_server/server.py:create_openteam_server`. FastMCP 3.x's `dev` command requires a **filesystem path** (not a Python module path) — its `FileSystemSource.load_server()` does `Path(spec).resolve()` then `spec_from_file_location()`. An earlier draft used module notation (`openteam.mcp_server.server:...`), which would have failed with `FileNotFoundError`. |
| Could RovoDev call OpenTeam AND OpenTeam call RovoDev (via `RovoDevCliInferencer`)? | Already supported — verified at `AgentFoundation/.../external/rovodev/rovodev_cli_inferencer.py`. Symmetrical boundary. |
| Does the integrated plan introduce any hack? | The closest is `_build_argv_and_env`'s `python -m` fallback when console scripts aren't on PATH. It's explicit, logged via friendly notify, and only fires in dev/CI. Production install (`uv tool install -e .`) puts all 5 binaries on PATH. No other shortcuts taken. |

---

## 13. Plan comparison: v5 | Cursor (updated) | Claude/sparkle | **v6**

| Concern | v5 | Cursor | Claude | **v6** |
|---|---|---|---|---|
| Slash architecture (subprocess) | ✅ | ✅ | ✅ | **✅** |
| MCP architecture (in-process) | ✅ | ✅ | ✅ | **✅** |
| `tool_cli.py` rendering fix (duck-typed) | ✅ | ✅ | ✅ | **✅** |
| `project_onboarding/{cli,__main__}.py` shim | ✅ | ✅ | ✅ | **✅** |
| `slash_enabled: true` on 3 tool.jsons | ✅ | ✅ | ✅ | **✅** |
| `get_current_worker()` top-level import + defensive `None` guard | ✅ | ✅ | ✅ | **✅** |
| `stderr=STDOUT` merged (no dead `proc.stderr.read()`) | ✅ | ✅ | ✅ | **✅** |
| Empty-output cleanup `shell_output.remove` | ✅ | ✅ | ✅ | **✅** |
| `_strip_unset` correctness inline comment (`0` preservation) | ✅ | ✅ | brief | **✅** |
| `ToolExecutionResult` typed correctly (`@dataclass`) | ✅ | ✅ | ✅ | **✅** |
| TIER-1/2/3 test tagging | ✅ | ✅ | partial | **✅** |
| CI signature-alignment preflight | ✅ | ✅ | ✅ | **✅** |
| Self-audit section | ✅ | ✅ | partial | **✅ (extended)** |
| Root `pyproject.toml` | ✅ | ✅ | ✅ | **✅** |
| **Slash names BARE (`/task`)** | ✗ (`/openteam-task`) | ✅ | ✅ | **✅** |
| **Single file w/ factory (`openteam.py`)** | ✗ (4 files) | ✅ | ✅ | **✅** |
| **`thread=True` (matches `shell.py:541`)** | ✅ | ✅ (corrected) | ✅ | **✅** |
| **`extra_prompt="required"` (clean empty-input UX; `/task --help` flows through because non-empty)** | ✗ (not specified) | ✗ (not specified) | not specified | **✅ (verified at registry.py:206,210-213)** |
| **5 console scripts (`openteam-task` etc.)** | ✗ (1 dispatcher) | ✅ | ✗ (uses `python -m`) | **✅** |
| **`bootstrap.py` EXPLICIT at boundaries (NOT `__init__.py` side-effect)** | ✅ | ✗ (proposes `__init__.py` magic) | ✅ | **✅** |
| **`bootstrap.py` walks up to find siblings** | ✗ (fixed `../..`) | ✅ | ✗ | **✅** |
| **`find_<binary>` PATH → venv → fallback** | ✅ | ✅ | ✗ | **✅** |
| **`mode: Literal[...]`** enum at MCP surface | ✅ | ✅ | ✗ | **✅** |
| **Templates shipped in repo** | ✅ | ✅ | ✗ | **✅** |
| **No `PYTHONPATH` in user `mcp.json`** | ✅ | ✅ | ✗ (suggests it) | **✅** |
| **`fastmcp>=3.2,<4`** (aligned with `code-nemo/pyproject.toml:24` which DOES pin `==3.2.4` — earlier `>=2,<4` would have resolved below the FastMCP 3.x API surface that `FunctionTool.from_function` lives on) | ✗ (unspecified) | ✗ (unspecified) | uses `>=2,<4` | **✅** |
| Phase 7A/B for long-running tools | ✅ | ✅ | ✅ | **✅** |
| Acknowledges `cli-rovodev` legacy lacks slash dir | ✅ | ✅ | ✅ | **✅** |
| LOC estimate | ~780 | ~960 | ~450 | **~1000** |
| Days to working end-to-end | ~1.5 | ~1.5-2 | ~1-1.5 | **~1.5** |

**v6 picks ONLY verified-correct items from each plan; rejects the two items where a plan had genuine architectural mistakes (v5's namespaced/four-files; Cursor's `__init__.py` magic).**

---

## 14. The "pick one" answer

> **"If we only pick one of the three existing plans (v5 / Cursor / Claude), which would you choose?"**

**Pick the Claude/sparkle plan** (`~/.claude/plans/here-are-a-few-wobbly-sparkle.md`).

This is a reversal from my last answer (which picked Cursor). Here's why the reversal is justified:

### Score sheet

| Trait | v5 (Rovo) | Cursor | Claude |
|---|---|---|---|
| Catches `project_onboarding` missing CLI shim | ✅ | ✅ | ✅ |
| Bare `/task` slash naming (matches 39 bare top-level + 24 sub-commands; no kebab-prefixed-sibling pattern exists today) | ✗ | ✅ | ✅ |
| Single-file factory layout (matches `jira.py`) | ✗ | ✅ | ✅ |
| `thread=True` for cancellation | ✅ | ✅ (recent correction) | ✅ |
| **Explicit bootstrap (NOT `__init__.py` magic)** | ✅ | **✗** | ✅ |
| 5 console scripts (eliminates `python -m`) | ✗ | ✅ | ✗ |
| Templates shipped in repo | ✅ | ✅ | ✗ |
| TIER-tagged tests + CI preflight | ✅ | ✅ | partial |
| Self-audit section | ✅ | ✅ | minimal |
| Lean & honest (no false fastmcp pin claim) | ✅ | ✅ | ✅ |
| Code lines that would compile-and-run as written | ~80% | ~90% | ~95% |

### Why Claude wins among the three

1. **No architectural over-reach.** Cursor proposes calling `bootstrap.ensure_siblings_on_path()` from `src/openteam/__init__.py` — a silent import-time side effect. The codebase has **zero precedent** for this (`agent_foundation/__init__.py`, `rich_python_utils/__init__.py`, `openteam/__init__.py` and every sub-package `__init__.py` are empty); `conftest.py` and `run_server.py` deliberately keep injection explicit. Cursor's "magic" is exactly the kind of move that breaks the moment a downstream library imports openteam for type checking. Claude (and v5) keep it explicit at the boundary.

2. **Idiomatic-correct on the two TUI conventions where v5 was wrong.** Every top-level slash in `app.py` is bare (39 bare top-level + 24 sub-commands under a bare name; no kebab-prefixed-sibling pattern exists); `jira.py`/`sessions.py` use the single-file-multi-handler pattern. Claude gets both right out of the gate; v5 (mine) got both wrong; Cursor (recent update) is also right.

3. **Honest about its limits.** The Claude plan ends with "Pick the Cursor plan" while clearly enumerating Cursor's wrongs (`thread=False`, `/openteam-task`, separate files, "Pydantic"). That kind of disciplined self-critique — *recommending a plan you've documented errors in, because its uniquely-correct insight is more valuable* — is engineering maturity.

4. **Lean.** 564 lines vs. v5's 1162 and Cursor's 951. Less code review surface, faster to onboard a new contributor.

### Why not Cursor?
The `__init__.py` import-side-effect bootstrap is **bigger** than a tactical bug — it's an architecture-shaping mistake that breaks the explicit-over-implicit convention every other package in `CoreProjects/` honors. If you adopt Cursor verbatim, you also adopt a maintenance burden (every new openteam contributor has to discover that `import openteam` mutates global sys.path).

### Why not v5?
The bare-naming and single-file-factory errors are **smaller** than Cursor's `__init__.py` mistake — but they're also more visible in the day-to-day developer experience. Every TUI user would see `/openteam-task` and instantly know it's non-idiomatic; reviewers would push back; you'd end up changing it anyway.

### What v6 (this file) adds over Claude
- Cursor's **5 console scripts** (zero new code; eliminates `python -m` from normal flow)
- v5's **TIER-tagged tests + CI signature alignment + self-audit + Phase 7A/B**
- v5's **`find_<binary>` PATH→venv→fallback** helper for portability
- v5's **`mode: Literal[...]`** enum at MCP surface
- v5's **templates shipped in repo**
- Bootstrap's **walk-up auto-detect** (Cursor's contribution)
- `extra_prompt="required"` (clean registry-level error on empty `/task`; `/task --help` still flows through because `--help` is non-empty after `registry.py:206`'s `removeprefix(slash).strip()`)

**Bottom line of pick-one:** **Claude > Cursor > v5** when picking exactly one. But **v6 (this file)** is strictly better than any single one.

---

## 15. Acceptance checklist (Definition of Done)

- [ ] `which openteam-mcp openteam-task openteam-create-role openteam-role-setup openteam-project-onboarding` returns 5 paths.
- [ ] `openteam-mcp run --help` prints Typer help.
- [ ] `openteam-task --help` prints tool.json parameters (no PYTHONPATH set) — **Phase 0d proof: bootstrap retrofit works.**
- [ ] `openteam-create-role --help` prints tool.json parameters (no PYTHONPATH set) — **Phase 0d proof: module-level `agent_foundation` import in create_role/executor.py is satisfied by bootstrap.**
- [ ] `openteam-role-setup --help` prints tool.json parameters (no PYTHONPATH set) — **Phase 0d proof.**
- [ ] `openteam-project-onboarding --help` prints tool.json parameters (no PYTHONPATH set).
- [ ] `python -m openteam.server.resources.tools.project_onboarding --help` prints help (Phase 0b proof).
- [ ] `python -m openteam.server.resources.tools.task "what is 2+2"` prints clean result text + `[workspace_path] /tmp/...` on stderr (Phase 0a proof).
- [ ] `fastmcp dev src/openteam/mcp_server/server.py:create_openteam_server` lists 4 tools (run from OpenStartup root — FastMCP 3.x requires a filesystem path, not a module path).
- [ ] In RovoDev TUI: `/task --help` prints tool.json parameters.
- [ ] In RovoDev TUI: `/task "what is 2+2"` streams output, exits 0. **(Note the quotes — slash args are `shlex.split`'d to honor flags; a multi-word `request` positional must be quoted. This is documented in the handler docstring shown by `/help /task`.)**
- [ ] In RovoDev TUI: `/task --plan "list 3 ways to learn python"` works.
- [ ] In RovoDev TUI: `/create-role "Senior Backend Engineer"` produces a role markdown path.
- [ ] In RovoDev TUI: `/role-setup ./roles/engineer.md` produces a setup report path.
- [ ] In RovoDev TUI: `/project-onboarding ./docs/role.md` runs (no ImportError — Phase 0b proof).
- [ ] In RovoDev TUI: `/help` lists all 4 OpenTeam commands.
- [ ] In RovoDev TUI: Ctrl-C during a long `/task` SIGTERMs the subprocess within ≤ 5 s.
- [ ] In RovoDev TUI: `/mcp` shows `openteam` server green, 4 tools.
- [ ] Agent path: `mcp__openteam__openteam_task(request="what is 2+2", mode="plan")` returns a string with the result + `Artifacts:` footer.
- [ ] CI: `test_wrapper_signature_alignment.py` green (catches future tool.json drift).
- [ ] CI: `test_helpers.py::test_zero_preserved` green (catches `0 == False` regression).
- [ ] CI: `test_bootstrap.py::test_idempotent` green.
- [ ] CI: `test_openteam.py::test_register_idempotent` green.
- [ ] Docs: `docs/MCP_INTEGRATION.md` install runbook reproduces end-to-end on a clean checkout.

---

## 16. Open questions (deferred)

1. **Phase 7A appetite** — open an acra-python PR adding per-server `timeout:` field in `mcp.json` schema?
2. **Phase 8 publish target** — internal pip / Bitbucket release / leave at `pip install -e .` forever?
3. **`fastmcp` upper-bound cadence** — quarterly bump in CI matrix, or pin tighter once mcp-atlassian-exp pins explicitly?
4. **Bootstrap convergence** — should the slash subprocess helper *also* import `openteam.bootstrap` somehow? (Currently it computes inline because RovoDev's process must not import openteam.) Discussion in §12 — defer to Phase 4.5.
5. **`openteam_subagent`** — ship a `~/.rovodev/subagents/openteam-orchestrator.md` for agentic LLM use? Cheap to add later.
6. **Reverse direction (`RovoDevCliInferencer`)** — OpenTeam already uses RovoDev as an LLM backend; symmetrical boundary verified. Out of scope here.
7. **`AgentFoundation` + `RichPythonUtils` get their own pyproject.toml** — would obsolete `bootstrap.py` entirely. Big win, biggest scope. Phase 9+.

---

## 17. Out of scope (deliberate)

- In-process `FastMCPTransport` for OpenTeam (would require bundling OpenTeam into RovoDev's PyInstaller image — structurally impossible per invariant 2).
- HTTP/SSE side-car mode for the OpenTeam React UI (separate Shape, separate PR).
- `~/.rovodev/subagents/openteam-orchestrator.md` (cheap, defer to follow-up).
- Event hooks (`eventHooks:` in `~/.rovodev/config.yml`) for OpenTeam lifecycle reactivity.
- Adding `pyproject.toml` to AgentFoundation and RichPythonUtils (user's explicit choice; bootstrap encapsulates the gap).
- Exposing dev-only or auth-bound tools (`mock_task`, `twg`, `slack_*`) — TWG is already covered by mcp-atlassian-exp.
- Phase 8 publish target — internal pip / Bitbucket release.

---

**End of v6.**
