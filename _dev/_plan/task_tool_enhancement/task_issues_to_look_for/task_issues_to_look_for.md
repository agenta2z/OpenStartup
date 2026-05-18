# Task Tool — Issues To Look For (Audit Checklist)

**Purpose**: When auditing any new task tool test run, systematically verify that none of the previously-encountered issues have regressed AND that the new run produces the expected artifacts. Use this as the master checklist before declaring a run "successful".

**Status**: Living document — last updated 2026-05-17

**How to use**: For each new run workspace at `<runtime>/.../task_<TS>_<uuid>/`, walk through each section below and produce a pass/fail verdict. Investigate any failure with deep root-cause analysis.

---

## §1 Workspace Structure Anomalies (Historical Bugs)

These are bugs that have been previously diagnosed and fixed; check that they have NOT regressed.

### Anomaly 1 — Cross-MFDual Instance Sharing
- **Symptom**: A single inferencer instance is shared across multiple MFDual workers, causing workspace clobbering and cross-talk.
- **Detection**:
  - Grep run log for: `BTA[*] workers * and * share inferencer *`
  - Expect: **0 occurrences**.
- **Root cause if seen**: `LazyConfigFactory` cascade broken; workers receiving the SAME instance from `functools.partial` capture.
- **Fix reference**: Sister plan Fix #11 (path-based recomputation in `_instantiate.py`).

### Anomaly 2 — Double `final_deliverables/final_deliverables/` Nesting
- **Symptom**: Aggregator output ends up at `outputs/final_deliverables/final_deliverables/output.md` (double-nested).
- **Detection**:
  ```bash
  find <workspace> -type d -path "*/final_deliverables/final_deliverables*"
  ```
  Expect: **0 results**.
- **Root cause if seen**: `path_listing.py` doesn't prune `final_deliverables` during recursive walk; OR BTA `_finalize_response` falls back to outputs/ when `deliverables_dir` is missing.
- **Fix reference**: `path_listing.py:556` (`dirs[:] = [d for d in dirs if d != "final_deliverables"]`) + Fix #2 conditional source selection.

### Anomaly 3 — Empty `flow_X_round01/` Placeholder
- **Symptom**: Empty placeholder directories like `flow_0_round01/` exist alongside actual content directories.
- **Detection**:
  ```bash
  find <workspace> -type d -empty -name "flow_*_round*"
  ```
- **Root cause if seen**: LWI created round01 placeholder at construction but workspace propagation never filled it.
- **Fix reference**: v2.5.3 sibling restoration + v2.8 hierarchical layout migration.

### Anomaly 4 — Hierarchical Layout Naming
- **Symptom**: Old layout `flow_X_workflow/` or `flow_X_initial_round01/` instead of new layout `flow_X/children/initial/` + `flow_X/children/round01/`.
- **Detection**:
  ```bash
  find <workspace> -type d -name "flow_*_workflow" -o -name "flow_*_initial_round*"
  ```
  Expect: **0 results**.
- **Fix reference**: Anomaly 7+8 v2.8 hierarchical layout (Changes A+B in LWI `_propagate_workspace_to_children`).

### Anomaly 5 — Hollow MFDual Subtree (NO `output.md` Files Inside MFDual)
- **Symptom**: Worker MFDual subtrees have empty `outputs/` dirs; no `output.md` files at any level under `worker_X/children/`.
- **Detection**:
  ```bash
  # Should find substantive .md files in flow_X/outputs/, flow_X/children/initial/outputs/, etc.
  find <workspace>/.../worker_*/children/propose/children/flow_* -name "output.md" | xargs -I{} wc -l {} | grep -v "^0 "
  ```
  Expect: **substantial line counts** (not 0 bytes).
- **Root cause if seen**: LWI didn't propagate `output_path` to followup children OR `_finalize_output` framework hook didn't fire.
- **Fix reference**: Fix #13 hierarchical layout in LWI `_propagate_workspace_to_children`.

### Anomaly 6 — Cross-Worker / Role-Inverted Audit Symlinks
- **Symptom**: Symlinks like `worker_1/round_01/fix → worker_0/.../review_inferencer` (target is in a DIFFERENT worker's tree).
- **Detection**:
  ```bash
  find <workspace> -type l | while read l; do
    src="$l"; tgt=$(readlink "$l")
    # Extract worker N from both paths; flag if they differ
    if [[ "$src" =~ worker_([0-9]+) && "$tgt" =~ worker_([0-9]+) ]]; then
      [ "${BASH_REMATCH[1]}" != "${BASH_REMATCH[2]}" ] && echo "CROSS-WORKER: $l → $tgt"
    fi
  done
  ```
  Expect: **0 cross-worker symlinks**.
- **Root cause if seen**: `_record_round_audit` reading live workspace state instead of phase-time snapshot; flow_pool sharing across workers.
- **Fix reference**: Fix #7 audit symlink hardening + Fix #8 snapshot-at-phase-time semantics.

---

## §2 Inference Quality Bugs (Bug A/B/C)

### Bug A — Aggregator Inlines `<Response>` Text Instead Of File References
- **Symptom**: Aggregator's `InferenceInput` contains full inlined worker `<Response>` text (~hundreds of lines per worker), instead of compact `(See file: <path>)` references.
- **Detection**:
  ```bash
  # For each aggregator inference input:
  agg_dir="<workspace>/.../aggregator/logs/session/RovoDevCliInferencer-*.jsonl.parts/InferenceInput"
  for f in $agg_dir/*.txt; do
    inlined=$(grep -c '<Response>' "$f")
    refs=$(grep -c '(See file:' "$f")
    echo "$f: $inlined inlined, $refs file_refs"
  done
  ```
  Expect: **`(See file:` refs > 0** AND `<Response>` inlined ≤ small delimiter count (4 max for template structure).
- **Root cause if seen**:
  - (i) `_build_agg_input` uses BTA's own `output_path` (e.g., `aggregation_report.md`) to look for WORKER outputs (which are `output.md`) → filename mismatch → resolution returns None → inlining.
  - (ii) LWI doesn't propagate `output_path` to its sub-inferencers → workers don't know their own output filename.
  - (iii) `_format_worker_results_text` requires `has_local_access=True` on the aggregator; ClaudeCodeCLI defaults to False.
- **Fix reference**:
  - `_build_agg_input` reads `_w.output_path` from worker instance (not `_bta_self.output_path`).
  - LWI `_build_worker_factory` sets `output_path=getattr(_initial, "output_path", None)`.
  - `ClaudeCodeCliInferencer.has_local_access = attrib(default=True)`.
- **Verification**: Check ALL aggregators (worker_0 MFI, worker_1 MFI, outer BTA), not just one.

### Bug B — Aggregator Runs Many Times (Should Be Once)
- **Symptom**: Aggregator's `InferenceInput/` directory has 5+ files instead of 1, each progressively growing as workers iterate.
- **Detection**:
  ```bash
  ls <workspace>/.../aggregator/logs/session/*/InferenceInput/ | wc -l
  ```
  Expect: **1 per aggregator** (or at most 2-3 if there's a real retry).
- **Root cause if seen**: BTA `_finalize_response` raises `NameError: deliverables_dst is not defined` after refactor, causing retry loop. Each retry re-aggregates with progressively grown worker outputs.
- **Fix reference**: BTA line ~1072: `"Skipping pipeline report — aggregator deliverables handled by _finalize_output"` (removed stale `deliverables_dst` reference).
- **Verification**: Grep run log for `NameError`; expect **0 occurrences**.

### Bug C — `max_breakdown` Not Rendered In Breakdown Prompt
- **Symptom**: Breakdown InferenceInput says `"break it into 3-5 focused subtasks"` regardless of configured `max_breakdown`.
- **Detection**:
  ```bash
  grep "break it into.*focused subtasks" <workspace>/.../breakdown/logs/session/*/InferenceInput/*.txt
  ```
  Expect: Number matches configured value (e.g., `_params.plan_max_breakdown=2` → should say "**2**", not "3-5").
- **Root cause if seen**: BTA's `max_breakdown` attribute was never injected into breakdown_inferencer's `template_extra_feed`.
- **Fix reference**: BTA `__attrs_post_init__` injects `max_breakdown` into `breakdown_inferencer.template_extra_feed`.

---

## §3 Workspace Boundary / Target Path Issues

### Issue D — `target_path` Not Reaching Subagents
- **Symptom**: RovoDev banner shows wrong working directory; or run log/streams say "outside the current workspace".
- **Detection**:
  ```bash
  # RovoDev banner should match configured target_path
  grep "Working in" <workspace>/_runtime/inferencer_cache/RovoDevCliInferencer/*/stream_*.txt | head -3
  # Should match the --override _target_path=... value
  ```
- **Acceptable**: Subagents using `bash cat` to read files outside the cwd (workaround). Verify the agent didn't give up — look for "I can't access this. Let me list options for you." (the subagent gave up). The PARENT agent should self-correct using bash.
- **Root cause if true regression**: `_target_path` not cascading through YAML to inferencer factory.

### Issue E — Empty stdout / Crash With Silent Success
- **Symptom**: `output.md` empty (0 bytes), `.fix_completed` marker exists, no error in launcher log.
- **Detection**:
  ```bash
  find <workspace> -name "output.md" -size 0
  find <workspace> -name ".fix_completed"
  ```
- **Root cause if seen**: ClaudeCodeCli wrapper accepting empty output as success; OR `claude` CLI not installed/configured.
- **Verification**: Run a one-line `which claude && claude --help` smoke test.

### Issue R — `additional_allowed_paths` Not Propagated or Logged
- **Background**: As of 2026-05-17 `InferencerBase` carries a backend-neutral `additional_allowed_paths: List[AllowedPath]` field, surfaced via the `effective_allowed_paths` property (which auto-includes `workspace.root` with `PathAccess.ALL`). `RovoDevCliInferencer.construct_command` translates this list into acli's `toolPermissions.allowedExternalPaths` inside `--config-override`. The chain must be intact end-to-end AND the rendered JSON must be observable in run artifacts for audit.
- **Observability prerequisite (currently a gap)**: The composed `--config-override` JSON is passed as a CLI argument to `acli`, but `acli`'s captured stream/output files do NOT echo back the command-line arguments — verified on baseline run `task-7ae9058e` (zero matches for `"config-override"` or `"modelId"` across all 13 inferencer caches). Until we add explicit logging, post-mortem audits cannot directly verify whether paths were correctly composed. **First Issue R remediation**: add an INFO log in `RovoDevCliInferencer._compose_config_override_for_cli` (or in `construct_command`) emitting the final composed JSON, and route that log into a per-inference artifact (e.g., a `cli_invocation.json` next to `InferenceArgs/`). Without this, all detection below relies on indirect signals.
- **Symptom**:
  - Inference command's `--config-override` JSON is missing the expected paths in `toolPermissions.allowedExternalPaths` (workspace.root and/or paths the executor explicitly plumbed in).
  - Once observability logging is in place: the logged JSON shows an empty/wrong `allowedExternalPaths`.
  - Indirect signal: Issue S fires (whitelist rejections + regenerate-from-summary smoking gun) even though the relevant paths *should* be whitelisted — indicating they aren't actually reaching acli.
  - Worker inherits the field on construction but child orchestrators don't cascade it via `_propagate_workspace_to_children`, so leaves silently see an empty list.
- **Detection** (post-observability — until the cli_invocation log lands, use Issue S as the proxy):
  ```bash
  # 1. PREFERRED (once observability is added): every RovoDev leaf should emit a
  #    cli_invocation.json (or equivalent) whose --config-override JSON contains
  #    toolPermissions.allowedExternalPaths with the expected paths.
  configured=0
  missing_paths=0
  ws_missing=0
  for inv in $(find <workspace> -name "cli_invocation.json" 2>/dev/null); do
    configured=$((configured+1))
    if ! grep -qE 'allowedExternalPaths"\s*:\s*\[' "$inv"; then
      missing_paths=$((missing_paths+1))
    else
      leaf_ws=$(echo "$inv" | sed -E 's|/_runtime/inferencer_cache/.*||')
      grep -q "$leaf_ws" "$inv" || ws_missing=$((ws_missing+1))
    fi
  done
  echo "RovoDev sessions with cli_invocation log: $configured (expect = # of RovoDev leaves)"
  echo "  ...missing allowedExternalPaths list:  $missing_paths (expect 0)"
  echo "  ...missing own workspace.root entry:   $ws_missing (expect 0)"

  # 2. UNTIL observability lands — use the absence of Issue-S smoking-gun signals
  #    as a weak proxy. (See Issue S for the actual grep terms.)

  # 3. Top task root (when executor plumbs it explicitly) reaches every leaf.
  top_root=$(realpath <workspace>)
  missing=0
  for inv in $(find $top_root -name "cli_invocation.json" 2>/dev/null); do
    grep -q "$top_root" "$inv" || missing=$((missing+1))
  done
  echo "Leaves missing top root in whitelist: $missing"
  ```
- **Root cause if seen**:
  - **Logging not yet implemented**: most likely cause for the "no signal" case on runs prior to the observability commit. Fix is to add the cli_invocation log; until then, treat Issue R as un-auditable directly and rely on Issue S signals.
  - Field accidentally moved back to `TerminalInferencerBase` (orchestrators can't carry it; test `TestFieldLivesAtInferencerBase::test_attribute_is_defined_on_inferencer_base_itself` should have failed).
  - `_propagate_workspace_to_children` doesn't cascade `additional_allowed_paths` → user-set paths on parent BTA/Dual/MFI don't reach leaf RovoDev inferencers.
  - `RovoDevCliInferencer.construct_command` skips `_compose_config_override_for_cli` in one of the two CLI mode branches (legacy / non-legacy).
  - User's `config_override` had malformed JSON → `_compose_config_override_for_cli` fell back to `{}`, dropping their `modelId` along with their paths. Inspect that fallback path's warning log.
  - acli version regression: `--config-override` flag stopped honoring `toolPermissions.allowedExternalPaths`. Check `acli rovodev --help` against the version manifested in the run.
- **Fix reference**:
  - Field at `InferencerBase` + `effective_allowed_paths` property: 2026-05-17 commit.
  - `RovoDevCliInferencer._compose_config_override_for_cli`: 2026-05-17 commit.
  - Auto-include of `workspace.root` (with `PathAccess.ALL`): 2026-05-17 commit.
  - **Pending observability follow-up**: emit composed `--config-override` JSON to a per-inference artifact so audits can verify propagation directly.
  - **Pending propagation follow-up**: executor (`task/executor.py`) plumbs top task root into the top-level inferencer's `additional_allowed_paths` for cross-subtree reads. Until shipped, only the leaf's own `workspace.root` is auto-whitelisted — cross-subtree reads still rely on `bash cat` fallback (covered by Issue S).

### Issue S — Reading Errors Despite Paths Being Whitelisted
- **Background**: Even when `effective_allowed_paths` correctly includes a target path, agents may still fail to read it. Either the whitelist isn't reaching the subprocess (Issue R), or there's a path-canonicalization mismatch, or the path simply isn't whitelisted at all (the D-1 cross-subtree case until the executor plumbs the top task root).
- **Phrasing note** (verified on baseline run `task-7ae9058e`): the **literal acli error string** `"Path '...' is outside both the workspace directory and whitelisted paths"` is raised internally by `nautilus.tools._file_system.sanitize_paths` but **does NOT appear verbatim in our captured run artifacts** — what acli streams back is the LLM agent's natural-language paraphrase of the failure (e.g., `"is outside this workspace"`, `"outside the whitelisted paths I can access"`, `"file you're requesting is in a different location"`). Detection therefore greps for the agent's NL paraphrases AND the D-1 smoking-gun phrases, NOT the literal acli error.
- **Symptom**:
  - Agent narrates that a file is outside the workspace and is unreachable.
  - Agent admits in raw output that it cannot read the prior artifact and proceeds to reconstruct from the in-prompt summary (the regression-from-summary mode of D-1).
  - Symlink-resolved vs. raw path mismatch (macOS `/tmp` → `/private/tmp` is the canonical case; symlinks in user-supplied paths can cause similar drift).
- **Detection**:
  ```bash
  WS=<workspace>

  # 1. Count NL paraphrases of workspace-boundary failures.
  outside_ws_hits=$(grep -rln "outside this workspace\|outside the whitelisted\|outside the workspace" \
                    $WS 2>/dev/null | wc -l)
  echo "Files with outside-workspace narration: $outside_ws_hits"

  # 2. Smoking-gun for the regenerate-from-summary failure mode (the worker_1 D-1 case):
  #    agent admits inability to read AND does NOT recover via bash cat.
  reconstruct_hits=$(grep -rln "I need to reconstruct\|I can't read\|reconstruct it with all the fixes" \
                     $WS 2>/dev/null | wc -l)
  echo "Files with regenerate-from-summary smoking gun: $reconstruct_hits"
  # Expect: 0. Any match = the strengthened file_reading_fallback_for_followup.jinja2
  # guard was not honored by the LLM in that step. Inspect each match to confirm
  # whether the agent recovered via bash cat OR truly reconstructed.

  # 3. For each smoking-gun hit, verify whether the same session ALSO contains a
  #    successful bash cat workaround (which would mean the guard worked).
  for f in $(grep -rl "I need to reconstruct\|I can't read\|reconstruct it" $WS 2>/dev/null); do
    sess_dir=$(dirname "$f")
    if grep -q "Called bash" "$f" 2>/dev/null && grep -q "cat " "$f" 2>/dev/null; then
      echo "RECOVERED: $f (regen-mention + bash cat — likely benign)"
    else
      echo "REGRESSION: $f (regen-mention WITHOUT bash cat recovery)"
    fi
  done | head -20

  # 4. If observability for Issue R is in place (cli_invocation.json), correlate
  #    each REGRESSION above against whether the relevant path was actually
  #    whitelisted — that distinguishes Issue S (path was whitelisted but acli
  #    still rejected) from Issue R (path never made it into the whitelist).
  ```
- **Triage** (when Issue S fires):
  - Smoking-gun phrase appears AND a successful `bash cat` recovery is in the same session → **benign**. The agent narrated the failure but recovered via the prompted fallback. Note for tuning the prompt if needed, but no regression.
  - Smoking-gun phrase appears AND NO `bash cat` recovery in the same session → **REGRESSION of the strengthened fallback guard**. Verify `file_reading_fallback_for_followup.jinja2` still contains the markers pinned by `TestFollowupPriorArtifactReconstructionGuard` (in `test_behavior_variable_injection.py`). If the markers are there but the LLM still didn't follow them, the guard may need to be tightened (revisit the wording).
  - Path IS in whitelist but failure still occurs → **canonicalization mismatch**. Inspect symlink resolution; verify both sides use `Path.resolve(strict=False)` or equivalent. macOS `/tmp` → `/private/tmp` is the most common offender.
  - Path is NOT in whitelist → **Issue R** (whitelist propagation gap). Cross-reference with Issue R's detection commands.
  - Path is NOT in whitelist AND it's a sibling-subtree artifact (e.g., a fix step trying to read its sibling propose-aggregator output) → **D-1 cross-subtree case**: needs executor to plumb top task root. Until that ships, the strengthened followup prompt should drive the agent to `bash cat` instead — verify the recovery actually happened.
- **Mitigation hierarchy** (in increasing order of robustness):
  1. Prompt-level: strengthened followup fallback instruction (2026-05-17, in place). Tells the agent to fall back to shell tools when file tools reject the path.
  2. Workspace.root auto-include via `effective_allowed_paths` (2026-05-17, in place). Covers leaf-internal reads.
  3. Executor plumbs top task root into the field (pending follow-up). Covers cross-subtree reads — the D-1 case.
- **Baseline reference** (`task-7ae9058e_20260517_023947`, pre-strengthening run for calibration):
  - Smoking-gun phrase hits: **2** files (both under `worker_1/children/round_01/children/fix/.../InferenceResponse/` — the worker_1 fix step that triggered D-1).
  - Outside-workspace narration hits: **3+** files across breakdown / aggregator / worker_1 fix sessions (every one of these was the cwd-mismatch that this whole feature addresses).
  - Future runs (post-strengthening + post-observability) should show: regenerate-from-summary hits = 0 OR all matches accompanied by a `bash cat` recovery in the same session.

---

## §4 Subagent Behavior Issues

### Issue F — Subagent Declines External Paths Without Workaround
- **Symptom**: Subagent says "outside workspace, here are options" and gives up.
- **Detection**: Grep run log for `outside.*workspace.*options` or `I cannot interact with`.
- **Acceptable**: Subagent declines BUT parent agent uses `bash cat <path>` to read it instead.
- **Real bug**: If breakdown / aggregator gives up entirely and produces empty or vacuous output.

### Issue G — Workspace-Whitelist Restriction
- **Symptom**: Aggregator can't read upstream worker outputs because they're outside its own `cwd`.
- **Mitigation**: Aggregator should fall back to `bash cat <path>`. Verify in stream files.
- **Detection**:
  ```bash
  # Aggregator's response stream should show bash usage to read upstream artifacts:
  grep -c 'bash.*cat.*flow_._.*output.md' <workspace>/.../aggregator/_runtime/inferencer_cache/.../stream_*.txt
  ```
  Expect: **>0** (proves the workaround fired).

---

## §5 Deliverable Pipeline Integrity

### Check H — Deliverable Cascade Chain
- **Symptom**: Final top-level deliverable doesn't reflect content from inner aggregators.
- **Detection**:
  - **Inner MFI aggregator output** (e.g., `worker_0/.../aggregator/outputs/output.md`): substantive content
  - **Worker outer Dual output** (e.g., `worker_0/outputs/final_deliverables/output.md`): substantive content (symlinked from aggregator or reviewed/fixed version)
  - **Outer BTA aggregator output**: substantive content
  - **Top-level Dual deliverable**: substantive content (1000+ lines for plan-mode SOP-class requests)
- **Verification**: Trace a unique phrase from inner aggregator → up through outer aggregator → up to top-level deliverable. Line counts should grow or stay similar (not shrink dramatically).

### Check I — Symlink Chain Correctness
- **Detection**:
  ```bash
  # Each orchestrator level should have outputs/output.md (real file or symlink)
  for d in <workspace>/children/*/outputs/ \
           <workspace>/.../worker_*/outputs/ \
           <workspace>/.../worker_*/children/*/outputs/; do
    [ -e "$d/output.md" ] && echo "OK: $d/output.md" || echo "MISSING: $d/output.md"
  done
  ```
- **Expect**: Every orchestrator level has its `outputs/output.md` (Fix #12/Fix #4 symlink chain).

### Check J — Manifest Files Present
- **Detection**:
  ```bash
  find <workspace> -name "output_manifest.json" | wc -l
  ```
  Expect: One per leaf inferencer that wrote a deliverable.

---

## §6 Run Health Indicators

### Check K — Process Stability
- Run log shouldn't have any uncaught exceptions; specifically:
  - `NameError` (Bug B)
  - `WorkflowAborted` (could indicate review-fix abort)
  - `FileExistsError` (could indicate dangling symlink)
  - `ImportError` (could indicate broken refactor)

### Check L — Iteration Count Reasonability
- **Workers**: Usually 1-3 iterations per flow (initial + maybe round01); rarely >5.
- **Reviewers**: 1 iteration typically; >1 may indicate consensus loop issues.
- **Fixers**: Either 0 (if review accepts) OR 1-2 iterations. Asymmetric workers (one needs fix, one doesn't) is acceptable.
- **Aggregators**: Should be 1 invocation each (unless real retry triggered).

### Check M — Runtime Duration
- Baseline: SOP plan-only with shallow profile ≈ 60-90 minutes (~1 hour ± 30 min).
- **Red flag**: 4+ hours suggests infinite retry loop (Bug B class regression).

---

## §7 New Feature Verifications (Per-Run Variable)

These depend on what's being tested in a given run. Document expectations in the test request itself.

### Check N — target_path Cascade
- If `--override _target_path=...` is passed, every RovoDev subprocess should declare it as working directory.

### Check O — Risk Assessment Section
- If the breakdown template was enhanced with risk-assessment instruction, aggregator output should contain a "Risk Register" or "Risks" section.

### Check P — Reference Material Use
- If the request mentions reference files (e.g., `_dev/pai_hack/`), parent agent should at least attempt bash workaround.

### Check Q — External API Calls (PRs, Confluence, etc.)
- If the request asks for PR data or Confluence search, verify subagents executed those tool calls (grep `bitbucketPullRequest`, `searchConfluence`, etc.).

---

## §8 Quick-Audit Command Pack

Run this one-liner cluster at the top of every postmortem:

```bash
WS="<workspace_path>"

echo "=== Run Health ==="
grep -c "NameError\|WorkflowAborted\|ImportError" $WS/../../tmp_rovodev_*.log 2>/dev/null || echo "(no log)"
grep -c "share inferencer" $WS/../../tmp_rovodev_*.log 2>/dev/null

echo ""
echo "=== Anomalies 1-6 ==="
find $WS -type d -path "*/final_deliverables/final_deliverables*" | wc -l
find $WS -type d -empty -name "flow_*_round*" 2>/dev/null | wc -l
find $WS -type d -name "flow_*_workflow" 2>/dev/null | wc -l
find $WS -name "output.md" -size 0 2>/dev/null | wc -l

echo ""
echo "=== Aggregator Bug A Check (3 aggregators expected) ==="
for f in $(find $WS -path "*/aggregator/logs/session/*/InferenceInput/*.txt"); do
  inlined=$(grep -c '<Response>' "$f")
  refs=$(grep -c '(See file:' "$f")
  echo "$f: $inlined inlined / $refs file_refs"
done

echo ""
echo "=== Aggregator Bug B Check (1 input per aggregator expected) ==="
for d in $(find $WS -name "InferenceInput" -path "*/aggregator/*"); do
  echo "$d: $(ls $d | wc -l) inputs"
done

echo ""
echo "=== Bug C: max_breakdown rendered correctly ==="
grep -h "break it into.* focused subtasks" $WS/children/*/breakdown/logs/session/*/InferenceInput/*.txt 2>/dev/null | head -1

echo ""
echo "=== Deliverable presence ==="
find $WS -name "output.md" -not -empty | wc -l
ls -la $WS/outputs/output.md $WS/outputs/final_deliverables/output.md 2>/dev/null

echo ""
echo "=== Cross-worker symlinks (should be 0) ==="
find $WS -type l | while read l; do
  src="$l"; tgt=$(readlink "$l")
  if [[ "$src" =~ worker_([0-9]+) && "$tgt" =~ worker_([0-9]+) ]]; then
    [ "${BASH_REMATCH[1]}" != "${BASH_REMATCH[2]}" ] && echo "CROSS: $l → $tgt"
  fi
done | wc -l

echo ""
echo "=== Issue R: additional_allowed_paths propagation (observability-gated) ==="
# Direct check requires per-inference cli_invocation.json (pending observability
# commit). Once shipped, every RovoDev leaf should emit one whose --config-override
# JSON contains toolPermissions.allowedExternalPaths with the leaf's own
# workspace.root (and the top task root once the executor plumbs it).
configured=$(find $WS -name "cli_invocation.json" 2>/dev/null | wc -l)
echo "Sessions with cli_invocation.json: $configured (expect = # of RovoDev leaves; 0 = observability not yet in place)"
if [ "$configured" -gt 0 ]; then
  missing_paths=0
  ws_missing=0
  for inv in $(find $WS -name "cli_invocation.json" 2>/dev/null); do
    if ! grep -qE 'allowedExternalPaths"\s*:\s*\[' "$inv"; then
      missing_paths=$((missing_paths+1))
    else
      leaf_ws=$(echo "$inv" | sed -E 's|/_runtime/inferencer_cache/.*||')
      grep -q "$leaf_ws" "$inv" || ws_missing=$((ws_missing+1))
    fi
  done
  echo "  ...missing allowedExternalPaths list:  $missing_paths (expect 0)"
  echo "  ...missing own workspace.root entry:   $ws_missing (expect 0)"
else
  echo "  (Falling back to Issue S signals — see below — until observability lands.)"
fi

echo ""
echo "=== Issue S: outside-workspace narration + regenerate-from-summary smoking gun ==="
# Note: the literal acli error string "outside both the workspace directory and
# whitelisted paths" does NOT appear in captured run artifacts — acli's stream
# captures the LLM's NL paraphrase. Grep for the paraphrases and the D-1
# smoking-gun phrases instead.
outside_ws_hits=$(grep -rln "outside this workspace\|outside the whitelisted\|outside the workspace" \
                  $WS 2>/dev/null | wc -l)
echo "Files with outside-workspace narration: $outside_ws_hits"
echo "  (Baseline reference: task-7ae9058e had ~23 such files — pre-strengthening run."
echo "   Future runs after both 'workspace.root auto-include' AND 'top task root plumbing'"
echo "   ship should approach 0. Any non-zero count needs Issue S triage.)"

reconstruct_hits=$(grep -rln "I need to reconstruct\|I can't read\|reconstruct it with all the fixes" \
                   $WS 2>/dev/null | wc -l)
echo "Files with regenerate-from-summary smoking gun: $reconstruct_hits"
echo "  (Baseline reference: task-7ae9058e had 2 such files — both in worker_1 fix step,"
echo "   the D-1 case. Future runs should be 0. ANY hit needs MANUAL triage per Issue S"
echo "   detection step 3 — automated bash-cat-recovery heuristics produce false negatives"
echo "   because writes like 'cat > output.md <<EOF' also match 'cat ' patterns.)"
if [ "$reconstruct_hits" -gt 0 ]; then
  echo "  Files to triage:"
  grep -rl "I need to reconstruct\|I can't read\|reconstruct it" $WS 2>/dev/null \
    | sed 's|.*/_runtime/tasks/[^/]*/|  - .../|' | head -10
fi
```

---

## §9 Acceptance Criteria For "Successful Run"

A run is considered successful if ALL of the following are true:

| # | Check | Pass Criterion |
|---|---|---|
| AC1 | Anomaly 1 (sharing) | 0 warnings |
| AC2 | Anomaly 2 (double final_deliverables) | 0 nested dirs |
| AC3 | Anomaly 3 (empty placeholders) | 0 empty flow_*_round* dirs |
| AC4 | Anomaly 4 (naming) | 0 old-style flow_*_workflow dirs |
| AC5 | Anomaly 5 (hollow MFDual) | output.md files present at all flow_X/* levels |
| AC6 | Anomaly 6 (cross-worker symlinks) | 0 cross-worker links |
| AC7 | Bug A (aggregator inlining) | Every aggregator input has `(See file:` refs > 0 |
| AC8 | Bug B (aggregator retries) | ≤1 InferenceInput per aggregator (or justified retry) |
| AC9 | Bug C (max_breakdown) | Breakdown prompt shows actual configured value |
| AC10 | Issue D (target_path) | RovoDev banner matches configured target_path |
| AC11 | Issue E (empty outputs) | Top-level output.md has substantive content (>100 lines for plan-mode) |
| AC12 | Issue F (subagent give-up) | No "I cannot ... options" without bash workaround follow-up |
| AC13 | Check H (deliverable cascade) | Final deliverable reflects inner aggregator content |
| AC14 | Check I (symlinks) | Every orchestrator level has outputs/output.md |
| AC15 | Check K (process stability) | No uncaught exceptions in run log |
| AC16 | Check M (duration) | Run completes within 2× baseline (≤2.5h for SOP plan-mode shallow) |
| AC17 | Check N (target_path cascade) | Every RovoDev subprocess working dir matches configured target_path |
| AC18 | Check Q (external APIs) | If request asks for PRs/Confluence, subagent tool calls were made |
| AC19 | Issue R (additional_allowed_paths propagation) | Every RovoDev leaf's `--config-override` JSON contains `toolPermissions.allowedExternalPaths` with at least the leaf's own `workspace.root` (and the top task root if the executor plumbs it). 0 sessions with missing `allowedExternalPaths` list; 0 sessions missing own `workspace.root` entry. |
| AC20 | Issue S (whitelist rejections & regenerate-from-summary) | 0 unhandled `"outside both the workspace directory and whitelisted paths"` rejections. 0 occurrences of "I need to reconstruct" / "I can't read the prior" smoking-gun phrases in any inference raw output (any hit = prompt-following regression of the strengthened followup fallback). |

---

## §10 Historical Run Baselines (For Comparison)

| Task ID | Date | Duration | Status | Notable |
|---|---|---|---|---|
| `task-9960e483` | 2026-05-11 21:30 | 1h 6m | ✅ Working baseline | 1 aggregator input |
| `task-e3ae2732` | 2026-05-12 18:24 | 4+ h (stopped) | ❌ Bug B regression | 7 aggregator inputs |
| `task-064edb76` | 2026-05-13 01:01 | 1h 6m | ✅ FIXED Bug B | 3 aggregator inputs (1 each) |
| `task-3f837eee` | 2026-05-13 16:27 | ~1h | ✅ Working | Bug A still present (inner MFI) |
| `task-6f5db57d` | 2026-05-13 14:46 | ~40 min | 🟡 Diagnostic | Logs added; root cause filename mismatch found |
| `task-a755c721` | 2026-05-13 18:33 | ~1h | ✅ Bug A FIXED | All 3 aggregators with file refs |
| `task-b3d7ea5a` | 2026-05-14 01:04 | 1h 8m | ✅ Bug A confirmed across runs | 959-line final deliverable |
| `task-7ae9058e` | 2026-05-17 02:40 | 1h 4m | ✅ Comprehensive baseline | 710-line PAI analysis, all checks green |
| `task-dc1e2e21` | 2026-05-17 01:34 | ~10 min (stopped early) | 🟡 max_breakdown verified | Issue #2 surfaced |

---

## §11 Provenance

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-05-17 | Initial consolidated audit checklist — synthesized from all bugs/anomalies discovered between 2026-05-10 and 2026-05-17 (Anomalies 1-6, Bugs A/B/C, Issues D-G, integrity checks H-J, health checks K-M, feature checks N-Q). Includes quick-audit command pack, acceptance criteria, and historical baselines. |
| v1.1 | 2026-05-17 (eve) | Added Issue R (`additional_allowed_paths` propagation/logging) and Issue S (whitelist rejections + regenerate-from-summary smoking gun) under §3. Both flow from the 2026-05-17 changes that promoted `additional_allowed_paths: List[AllowedPath]` to `InferencerBase`, added the `effective_allowed_paths` property with `workspace.root` auto-include, taught `RovoDevCliInferencer` to merge it into `--config-override`, and strengthened `file_reading_fallback_for_followup.jinja2` to require shell-tool fallback before any other recourse. Updated §8 quick-audit pack with detection commands. Added AC19 + AC20 to §9 acceptance criteria. |
