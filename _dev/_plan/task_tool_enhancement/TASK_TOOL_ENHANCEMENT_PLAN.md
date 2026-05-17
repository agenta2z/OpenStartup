# Task Tool Enhancement Plan — derived from Plan B run (task_task-7ae9058e_20260517_023947)

> **Owner:** Tony Chen (tchen7) · **Drafted:** 2026-05-17
> **Source run analyzed:** `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/server/_runtime/tasks/task_task-7ae9058e_20260517_023947`
> **Topology used:** `bta-dual.yaml` (BTA → Dual breakdown/workers/aggregator → review→fix round)
> **Goal:** identify concrete, generic, no-overengineering improvements to the **task tool framework** (Python orchestrator + prompt templates + logging) so any future run is faster, cheaper, and produces higher-quality artifacts.

---

## 0. TL;DR — what we found and what to do

The Plan B run took **~28 min wall-time** to produce a 710-line artifact through 9 LLM phases:
`breakdown → worker_0 → worker_1 → (both internally recurse: propose→review→fix) → aggregator(Dual) → root review → root fix`.

It worked, but it has clear, fixable inefficiencies and quality gaps:

| Bucket | Top finding | Suggested fix | Effort |
|---|---|---|---|
| **Framework / topology** | Workers redundantly re-run the full **Dual (review→fix) consensus loop** inside *each* worker even though there is already an outer round_01 review→fix. Result: ~3× the inferences. | Make `consensus_config.max_iterations` configurable per slot and default workers to `1` (no inner consensus); keep Dual only for breakdown + aggregator + root. | S |
| **Framework / parallelism** | Workers ran on overlapping time windows but the *aggregator* didn't start for **9+ min** after both workers finished (look at round_log: workers done ~10:13, aggregator first inference at 10:13:52 but parts directory shows 9-min gap before completion). | Add explicit "worker-done barrier" timestamp; alert / log if `aggregator_start - max(worker_end) > 60s`. | XS |
| **Framework / logging** | **367 of 457 files** in the run (80 %) are inside `*.jsonl.parts/` — one file per JSON field per event. Filesystem inode pressure + slow `find`/`ls`. | Inline values ≤ 4 KiB; offload only large blobs (prompt / response). | S |
| **Prompts / review** | Review prompt has **no rubric, no severity ladder, no JSON-output schema**. The reviewer freelances → fix phase gets prose feedback that must be re-parsed. | Add a 6-criterion rubric + machine-readable `{accepted, severity, rationale}` JSON contract. | S |
| **Prompts / aggregator** | Aggregator is told to "make clean integration" with **no de-dup heuristic**, no provenance instruction → final artifact is 95 % superset of worker_0 (just appends some worker_1 doc-update content). | Add "de-dup by claim signature, cite contributing worker(s) per section" + an explicit conflict-resolution rule. | S |
| **Prompts / breakdown** | Breakdown produces sensible decomposition but **doesn't constrain subtask boundaries** (workers internally re-do propose→review→fix). | Add explicit "subtasks MUST be terminal (no further breakdown)" + "subtasks MUST be on disjoint output surfaces". | XS |
| **Quality / verification** | Review caught real issues (OPP-02/03 severity overstatement) but no **automatic re-prioritization** of the artifact — fix phase had to do it manually. | Define a `re_rank` action verb in the review JSON contract; let fix obey it mechanically. | S |
| **Cost / dedupe** | Both workers re-read the same ~10 source files; no shared cache across siblings. | Sibling-shared `_runtime/inferencer_cache` (it already exists per-worker — just hoist to parent). | S |
| **Reliability** | No retry/timeout/token-budget guard surfaced anywhere in the run; one stalled inference would have hung the entire 28-min job. | Per-inference timeout (already partially present as `idle_timeout_seconds: 300`); add max wall + token budget at topology level. | M |
| **Low-hanging UX** | `output_manifest.json` at task root has **73 contributors** but no `total_inferences`, `total_tokens`, `wall_time_seconds`, `cost_estimate_usd` — hard to audit cost. | Roll up a `stats` section with run KPIs. | XS |

Total estimated effort for all 10 boosts: **~2 sprints (1 engineer)**, no architectural rewrite required.

---

## 1. What was investigated (so future readers don't re-do it)

### 1.1 Run topology (read from `bta-dual.yaml`)
```yaml
_target_: BTA
breakdown_inferencer: Dual { base + review (opus[1m]), max_iterations: 2 }
worker_factory.__default__: Dual { base + review (opus[1m]), max_iterations: 2 }
aggregator_inferencer: Dual { base + review (opus[1m]), max_iterations: 2 }
breakdown_format: json_subtasks
max_breakdown: 4
```
**Implication:** every BTA slot (breakdown, each worker, aggregator) is itself a Dual = at least 2 LLM calls (base + review). With 2 workers, the propose phase alone is up to `2 (breakdown) + 2×2 (workers) + 2 (aggregator) = 8 LLM calls`, before the outer `round_01` review→fix adds another 2. **Round_log + manifest confirms 9 distinct phases producing artifacts.**

### 1.2 Actual phases observed (from `outputs/round_log.jsonl` + sub-task manifests)
| # | Phase | Wall-time | Output size |
|---|---|---|---|
| 1 | breakdown (Dual) | ~6 min (02:39 → started, finished before 03:00) | 120 lines decomp |
| 2 | worker_0 (Dual; internally propose→review→fix) | ~3m 40s for own propose | 688 lines |
| 3 | worker_1 (Dual; internally propose→review→fix) | ~3m 43s, finished 10:13 | 607 lines |
| 4 | aggregator (Dual) | started 10:13:52, finished 10:22:48 (~9 min) | 685 lines |
| 5 | round_01 review (RovoDevCli) | 10:22:49 → 10:26:22 (3m 33s) | 100+ lines criticism |
| 6 | round_01 fix (RovoDevCli) | 10:26:22 → 10:31:57 (5m 35s) | 710 lines (final) |

**Total wall ≈ 28 min** for one user prompt.

### 1.3 Prompt templates (from `**/InferenceInput/*.txt` files)

Three distinct templates rendered into the run:
- **Breakdown prompt** (in `children/propose/children/breakdown/...InferenceInput/`): asks for "decomposed_subtasks" JSON, includes the original user prompt verbatim + reasoning request.
- **Aggregator prompt** (`children/propose/children/aggregator/...InferenceInput/.../31352_69783cc6.txt`): tells aggregator "first double check each input for any issues or problems, then carefully and holistically compare … Make clean, proper, elegant integration". Quality guidelines section. **No rubric, no de-dup spec, no provenance requirement.**
- **Review prompt** (`children/round_01/children/review/...InferenceInput/.../32249_124ba244.txt`): "You are tasked with carefully and thoroughly reviewing artifacts…" — pastes the artifact verbatim into the prompt. **No rubric, no severity ladder, no JSON output schema.**
- **Fix prompt** (`children/round_01/children/fix/...InferenceInput/.../32622_91302cf0.txt`): packs Original User Request + Prior Artifact + Reviewer Feedback. ~24 KB input. **No "address-each-issue" checklist; relies on model good behavior.**

### 1.4 Quality of artifacts produced
- **Workers diverged usefully**: worker_0 = code opportunities (688 lines); worker_1 = RST doc plan (607 lines). Decomposition was reasonable.
- **Aggregator output (685 lines) is essentially worker_0 with worker_1's §4 appended.** No real consolidation of overlapping claims.
- **Review caught 7 real issues** (2 reclassifications, 2 cross-PR-overlap notes, effort underestimation, missing pai_hack reference). All 7 were accepted in the fix phase → tangible quality gain from the review→fix loop.
- **Fix phase produced a final 710-line artifact** (within +25 lines of aggregator) — i.e., review→fix added value mostly via reclassification, not bulk content.

### 1.5 Logging shape (from `find ... | wc -l`)
- `457 total files` in the run directory.
- `367 of them (80 %)` live under `*.jsonl.parts/`, where every JSON field of every event is **dumped as its own file** (`*_id_*.txt`, `*_name_*.txt`, `*_type_*.txt`, `*_level_*.json`, `*_time_*.txt`, etc.).
- Per-event "shell" JSONL points at the parts files with `{"__parts_file__": "...", "__value_type__": "..."}` stubs.
- This explodes inode counts and makes naïve `ls`/`grep` slow.

### 1.6 Inferencer cache (from `find inferencer_cache`)
- Per-phase `_runtime/inferencer_cache` directories exist at **breakdown, aggregator, worker_1/.../aggregator**, but **NOT shared between sibling workers**. A worker re-doing the same code-search will not hit the breakdown's cache.

---

## 2. Detailed enhancement opportunities (E-01 … E-10)

### 🟢 E-01 — Make Dual consensus optional per BTA slot (biggest cost win)

**Problem.** Every slot in `bta-dual.yaml` is Dual with `max_iterations: 2`. That means each slot does **≥ 2 LLM calls** (base + reviewer). For a single user request with 2 workers, this is 8 LLM calls in propose + 2 in root review/fix = **10 large LLM calls**. The outer `round_01` review→fix is the actual quality gate; the inner Dual on each worker is mostly duplication.

**Evidence.**
- `bta-dual.yaml` lines 16–22 (worker_factory) and 23–37 (aggregator) — both wrap a Dual.
- Worker subdirs each contain `propose/`, `review_inferencer/`, `fixer_inferencer/`, `round_01/` — confirming each worker ran the full loop.

**Fix.** Add a new preset `bta-dual-light.yaml` (or a config flag `inner_dual: false`) where:
- Workers use a plain `ClaudeCodeCLI` (no review/fix loop), OR
- `consensus_config.max_iterations: 1` so reviewer runs only once and fix is skipped if review passes.

**Expected impact.** −30–50 % LLM calls and −30–40 % wall-time on bta-dual. No quality loss because root round_01 already reviews.

**Files to change.**
- New: `src/openteam/server/resources/tools/task/topologies/bta-dual-light.yaml`
- Modify: `executor.py` — already supports `--agent-config` preset selection (lines 51–94); no code change needed.

**Effort.** S (1 day to add yaml + smoke test).

---

### 🟢 E-02 — Add per-slot `inner_dual` knob & cost-aware topology selection

**Problem.** Today the user must hand-pick the topology (`bta-dual`, `bta`, `dual`, `single`). There is no way to say "Dual on the aggregator and root, single on the workers."

**Fix.** In `executor.py` `_resolve_agent_config`, support an override syntax:
```
--agent-config bta-dual --override worker_factory.__default__._target_=ClaudeCodeCLI
```
(executor.py already builds an "override map" per its docstring step 6 — just expose it on the CLI.)

**Expected impact.** Lets users dial cost/quality without hand-editing topologies.

**Effort.** XS (extend existing override hook).

---

### 🟢 E-03 — Add a Review-phase rubric + JSON output schema

**Problem.** The review prompt (`32249_124ba244.txt`) says "carefully and thoroughly review artifacts" but provides **no rubric**. Result: review output is free prose that the fix phase must re-parse. Severity classifications drifted (the reviewer downgraded P0→P2 in OPP-02/03 — correct call, but the framework cannot enforce that downstream).

**Fix.** Update the review template (likely in the inferencer's prompt-template source) to:
1. List **6 evaluation criteria**: (a) factual correctness vs source code/docs, (b) completeness vs original ask, (c) priority/severity calibration, (d) duplication of in-flight work, (e) feasibility of recommendations, (f) cross-reference integrity.
2. Require output in this shape:
```json
{
  "issues": [
    {"id": "0-1", "criterion": "priority_calibration", "severity": "high|med|low",
     "section_ref": "OPP-02", "evidence": "...", "action": "reclassify|reword|drop|add"}
  ],
  "verdict": "accept|fix_required|reject",
  "summary": "<= 200 words"
}
```

**Expected impact.** Fix phase can mechanically iterate over issues; review→fix becomes deterministic.

**Files to change.** The review prompt template (search for the `"You are tasked with carefully and thoroughly reviewing"` string in `src/openteam/server/` and replace).

**Effort.** S (template edit + 1 worked example).

---

### 🟢 E-04 — Tighten the Aggregator prompt (de-dup + provenance)

**Problem.** Aggregator output is 685 lines vs `worker_0 (688) + worker_1 (607) = 1295` — i.e., the aggregator achieved **47 % size reduction** but the qualitative inspection shows it largely concatenated worker_0 + worker_1's §4. Sections are not tagged with which worker contributed them.

**Fix.** Add to the aggregator prompt (in `31352_69783cc6.txt`'s template source):
- "For each output section, prepend an HTML comment `<!-- from: worker_0 -->` or `<!-- from: worker_0+worker_1 (merged) -->`."
- "If two inputs claim the same finding, keep one and add a `concordance: 2/2` tag."
- "If inputs disagree, surface both under a `### Disagreements` subsection with your adjudication."

**Expected impact.** Provenance + adjudication transparency; reviewer can spot uncritical pass-through.

**Effort.** S.

---

### 🟢 E-05 — Tighten the Breakdown prompt (terminal subtasks + disjoint surfaces)

**Problem.** The breakdown produced 2 sensible subtasks, but each worker still ran its own internal `propose→review→fix` because the BTA factory is Dual. The breakdown prompt does not specify "subtasks should be terminal."

**Fix.** Add to breakdown prompt:
- "Decomposed subtasks MUST be **leaf-level**: each subtask is small enough that the assigned worker can complete it in a single propose pass."
- "Each subtask MUST write to a **disjoint output surface** (different file path or different artifact section). Specify the surface in `output_surface` field."
- Add `output_surface` field to the `decomposed_subtasks` JSON contract.

**Expected impact.** Pairs with E-01 to safely drop inner Duals.

**Effort.** XS.

---

### 🟢 E-06 — Hoist the `inferencer_cache` to parent task (sibling sharing)

**Problem.** Each child has its own `_runtime/inferencer_cache`. When worker_0 and worker_1 both `cat` the same `application.yml`, the cache hit can't be reused.

**Fix.** In the inferencer base class (search for `inferencer_cache` directory creation in `src/openteam/server/`):
- Default cache_dir = `parent_task_workspace / "_runtime/inferencer_cache"` instead of `current_workspace / "_runtime/inferencer_cache"`.
- Add config flag `cache_scope: parent|task|sibling-share` (default `parent`).

**Expected impact.** Lowest-risk cost cut — typically 10–20 % on multi-worker runs where workers explore overlapping files.

**Effort.** S.

---

### 🟢 E-07 — Compact the JSONL `.parts/` logging shape

**Problem.** 367 / 457 files are part-files. Most are < 30 bytes (`id_*.txt` holds an inferencer id; `level_*.json` holds `{}`). Filesystem and tooling pay an inode tax for nothing.

**Fix.** In the JSONL writer (search for `__parts_file__` in src):
- Inline values **≤ 4 KiB** directly in the parent JSONL line.
- Only offload values > 4 KiB to part files (prompts, responses).
- Keep the `__parts_file__` reference shape for backward compatibility.

**Expected impact.** ~80 % fewer files per run; faster `find`/`ls`, smaller tar archives, easier diffing.

**Effort.** S (one writer file + a unit test).

---

### 🟡 E-08 — Add per-inference reliability guards (timeout, retry, token-budget)

**Problem.** `bta-dual.yaml` sets only `idle_timeout_seconds: 300` on `ClaudeCodeCLI`. No wall-time cap, no retry on transient failure, no token-budget circuit breaker. A stalled aggregator would hang the entire 28-min job.

**Fix.** Add three optional fields to `ConsensusConfig` / `Inferencer` base:
- `max_wall_seconds: 1800` (per slot)
- `max_retries: 1` on transient errors (5xx, network)
- `token_budget: 200_000` per slot; if exceeded → abort with structured error.

Surface these in topology yaml + executor.py override map (E-02).

**Expected impact.** Bounded blast radius for any single bad LLM call.

**Effort.** M (touches `Inferencer` base + each subclass's run loop).

---

### 🟡 E-09 — Action-verb contract in review JSON, enforced by Fix phase

**Problem.** Review issues today are textual ("severity overstated"). The fix phase has to read the prose and decide what to do. Concrete observation: the review correctly downgraded OPP-02 P0→P2 but did so via paragraph commentary; fix had to manually re-categorize and re-author OPP-02 in §3.2.

**Fix.** Extend the review JSON (E-03) with an `action` enum:
```
add | drop | reword | reclassify(from,to) | cross_link(target) | re_rank
```
The fix prompt then renders a checklist:
```
- [ ] Apply action: reclassify(P0, P2) on OPP-02 — rationale: <reviewer text>
```
Fix phase output must include the same `issue_id` with `applied: true/false + diff_summary`.

**Expected impact.** Fix becomes mechanical & auditable; reviewer ↔ fix correspondence is provable.

**Effort.** S (template change + small parsing helper).

---

### 🟢 E-10 — Add run KPI rollup to `output_manifest.json`

**Problem.** The root manifest has `stats: {total: 73}` (just file count). To audit a run you'd manually sum every `*_token*` and timestamp.

**Fix.** Extend the manifest builder to emit:
```json
"run_stats": {
  "wall_time_seconds": 1690,
  "phases": 6,
  "llm_calls": 10,
  "tokens_input_total": ...,
  "tokens_output_total": ...,
  "cost_usd_estimate": ...,
  "phase_breakdown": {"breakdown": {...}, "worker_0": {...}, ...}
}
```

**Expected impact.** Instant per-run cost/perf visibility; enables regression tests on cost.

**Effort.** XS.

---

## 3. Sequencing & roadmap

```text
Sprint 1 (low-risk wins, no behavior change):
  E-07 (compact JSONL)  ── 2 d
  E-10 (manifest stats) ── 1 d
  E-04 (aggregator prompt) ── 1 d
  E-05 (breakdown prompt) ── 1 d
  E-03 (review rubric)  ── 2 d

Sprint 2 (behavior-changing, gated by tests):
  E-01 (bta-dual-light preset) ── 2 d
  E-06 (parent-scoped cache)   ── 2 d
  E-09 (action-verb contract)  ── 2 d
  E-02 (CLI override surface)  ── 1 d
  E-08 (timeout/retry/budget)  ── 3 d
```

Run order rationale:
- E-07, E-10, E-04, E-05, E-03 are pure prompt / observability tweaks → safe to ship first, immediate ROI.
- E-01 + E-06 + E-09 + E-08 together yield the cost & reliability boost; gate behind a smoke-test run of bta-dual-light on this very task.

---

## 4. Success metrics

| Metric | Today (this run) | Target after Sprint 1 | Target after Sprint 2 |
|---|---|---|---|
| Wall time end-to-end | 28 min | 28 min (no behavior change) | **≤ 18 min** (−35 %) |
| LLM calls | ~10 | ~10 | **≤ 6** |
| Files written per run | 457 | **≤ 100** (E-07) | ≤ 100 |
| Aggregator self-overlap | ~95 % pass-through | **traceable** via provenance comments | n/a |
| Review→fix correspondence | textual only | **structured JSON** (E-03/E-09) | machine-checked |
| Cost visibility | manual sum | `run_stats` in manifest | live during run |

---

## 5. Risks & mitigations

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Removing inner Dual (E-01) drops quality | Smoke test on this same Plan B prompt; compare 24-OPP catalog completeness; keep `bta-dual` as fallback preset |
| R2 | JSONL compaction (E-07) breaks log consumers | Keep `__parts_file__` reference shape for >4 KiB blobs; add unit test verifying parse round-trip |
| R3 | Stricter review rubric over-rejects | Default `verdict: accept` if no issues with severity ≥ med |
| R4 | Sibling cache (E-06) leaks dirty data across workers | Cache key already includes prompt hash; no new collision surface |
| R5 | Action-verb (E-09) too rigid | Allow `action: other` with free-text fallback |

---

## 6. Out of scope (explicitly not addressed here)

- Replacing `ClaudeCodeCLI` with a different model — orthogonal.
- Rewriting the BTA orchestrator into a DAG engine — over-engineering for current scale.
- Multi-tenant cost accounting / billing — not needed for internal tool.
- Adding RAG over prior runs — defer until E-06 + E-10 are in place.

---

## 7. Appendix A — Files & lines worth touching

| Area | File / glob | What |
|---|---|---|
| Topology | `src/openteam/server/resources/tools/task/topologies/bta-dual.yaml` | Add `bta-dual-light.yaml` sibling (E-01) |
| Executor | `src/openteam/server/resources/tools/task/executor.py` lines 51–94 (`_resolve_agent_config`) | Surface override map on CLI (E-02) |
| Inferencer base | search `src/openteam/server/**/*.py` for `inferencer_cache` directory creation | Hoist cache scope (E-06) + add timeout/retry/budget (E-08) |
| JSONL writer | search for `__parts_file__` in src | Inline ≤ 4 KiB values (E-07) |
| Prompt templates | search for `"You are tasked with carefully and thoroughly reviewing"` | Review rubric (E-03) + action verbs (E-09) |
| Prompt templates | search for `"You are aggregating the following upstream artifacts"` | Aggregator de-dup + provenance (E-04) |
| Prompt templates | search for `"decomposed_subtasks"` | Breakdown terminal-subtask rule + `output_surface` field (E-05) |
| Manifest | search for `output_manifest.json` writer | Add `run_stats` rollup (E-10) |

## 8. Appendix B — Evidence pointers (so any future reader can audit)

- Run root: `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/src/openteam/server/_runtime/tasks/task_task-7ae9058e_20260517_023947`
- Round log: `outputs/round_log.jsonl` (3 entries; one per phase boundary)
- Breakdown decision: `children/propose/children/breakdown/outputs/output.md`
- Worker_0 artifact: `children/propose/children/worker_0/outputs/final_deliverables/output.md` (688 lines)
- Worker_1 artifact: `children/propose/children/worker_1/outputs/final_deliverables/output.md` (607 lines)
- Aggregator artifact: `children/propose/children/aggregator/outputs/final_deliverables/output.md` (685 lines)
- Aggregator prompt: `…/aggregator/logs/session/RovoDevCliInferencer-a3c9a996.jsonl.parts/InferenceInput/20260517_031352_69783cc6.txt`
- Review prompt: `…/round_01/children/review/logs/session/RovoDevCliInferencer-db9c1410.jsonl.parts/InferenceInput/20260517_032249_124ba244.txt`
- Fix prompt: `…/round_01/children/fix/logs/session/RovoDevCliInferencer-336b4c52.jsonl.parts/InferenceInput/20260517_032622_91302cf0.txt`
- Final artifact: `children/round_01/children/fix/outputs/final_deliverables/output.md` (710 lines)
- Topology yaml: `src/openteam/server/resources/tools/task/topologies/bta-dual.yaml`
