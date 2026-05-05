"""Real-CLI integration test for `/task --agent-config <yaml>`.

Topology: outer Dual (review-and-fix) wrapping two distinct BTA instances,
each with PTI workers whose planner is MultiFlowDual and whose executor
is a Dual. Five inferencer types in their natural roles.

YAML lives at: configs/breakdown_multiflow_plan_then_implement.yaml.
The test goes through `_run_topology()` -- the same path `/task` slash
uses -- exercising the full real loader (alias resolution, `_-prefix`
cascade, OmegaConf interpolation, `_partial_` auto-injection).

Two test functions:

  * ``test_yaml_smoke_instantiate`` -- unit-level (no LLM), ~5s. Catches
    alias / interpolation / cascade-injection regressions.
  * ``test_real_dual_outside_bta_pti_mfdual_dual`` -- @pytest.mark.integration
    real-CLI. Profile-parametrized via ``BMP_REAL_PROFILE`` env var
    (shallow / medium / deep). Default ``shallow``, ~30-60min, $30-60.

Cost gate: real-CLI test is skipped without ``-m integration`` and
without claude CLI on PATH.
"""

from __future__ import annotations

import functools
import os
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Paths and discovery
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
YAML_PATH = _HERE / "configs" / "breakdown_multiflow_plan_then_implement.yaml"

# OpenStartup repo (the target_path for ClaudeCodeCli leaves to investigate)
OPENSTARTUP_PATH = Path(
    os.environ.get(
        "OPENSTARTUP_PATH",
        # default: this file at OpenStartup/test/openteam/resources/tools/task/
        # parents[0]=task, [1]=tools, [2]=resources, [3]=openteam,
        # [4]=test, [5]=OpenStartup
        str(_HERE.parents[4]),
    )
)
TEMPLATES_DIR = OPENSTARTUP_PATH / "src" / "openteam" / "server" / "resources" / "prompt_templates"


# ---------------------------------------------------------------------------
# Skip markers (inlined; this dir has no shared conftest yet)
# ---------------------------------------------------------------------------

def _cli_available(command: str) -> bool:
    try:
        result = subprocess.run(
            f"{command} --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


CLAUDE_AVAILABLE = _cli_available("claude")

skip_claude = pytest.mark.skipif(
    not CLAUDE_AVAILABLE,
    reason="claude CLI not available (not in PATH or non-zero exit)",
)
skip_openstartup = pytest.mark.skipif(
    not OPENSTARTUP_PATH.exists(),
    reason=f"OpenStartup repo not found at {OPENSTARTUP_PATH}",
)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

PROFILES = {
    "shallow": {
        "outer_dual_iter": 1,
        "bta_workers": 2,
        "mfdual_iter": 1,
        "inner_dual_iter": 1,
        "min_response_len": 200,
    },
    "medium": {
        "outer_dual_iter": 1,
        "bta_workers": 2,
        "mfdual_iter": 2,
        "inner_dual_iter": 2,
        "min_response_len": 400,
    },
    "deep": {
        "outer_dual_iter": 3,
        "bta_workers": 3,
        "mfdual_iter": 2,
        "inner_dual_iter": 2,
        "min_response_len": 600,
    },
}
_PROFILE = os.environ.get("BMP_REAL_PROFILE", "shallow")


# ---------------------------------------------------------------------------
# Default inferencer (overridable via env var BMP_DEFAULT_INFERENCER).
# Drives the YAML's `${_params.default_inferencer}` interpolations through the
# `_params.default_inferencer` override. Examples: "ClaudeCodeCLI" (default),
# "RovoDevCLI". Any value listed in registered_targets.py works.
# ---------------------------------------------------------------------------
_DEFAULT_INFERENCER = os.environ.get("BMP_DEFAULT_INFERENCER", "ClaudeCodeCLI")


# ---------------------------------------------------------------------------
# Proactive AI Platform — codebase-understanding task fixtures
# ---------------------------------------------------------------------------
# Target codebase to analyze + output location for the generated docs. Both
# overridable via env vars so the same test can point at different codebases.
PAI_CODEBASE_PATH = Path(
    os.environ.get(
        "PAI_CODEBASE_PATH",
        "/Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform",
    )
)
PAI_DOCS_OUTPUT_PATH = Path(
    os.environ.get(
        "PAI_DOCS_OUTPUT_PATH",
        str(_HERE.parents[5] / "_dev" / "pai_hack" / "codebase_understanding"),
    )
)


# ---------------------------------------------------------------------------
# Task prompt
# ---------------------------------------------------------------------------

DOC_TASK = r"""Create detailed, comprehensive documentation for the codebase at:

  C:\Users\yxinl\OneDrive\Projects\PythonProjects\CoreProjects\_dev\responsible-ai-api

The documentation must be:
- Comprehensive: cover the codebase's purpose, architecture, public API, key
  modules, and any operational concerns
- Structured: organized into clearly-named sections with consistent depth
- Both human-readable and machine-friendly: use proper headings, code blocks,
  cross-references, and a glossary; emit content that downstream tools (Sphinx,
  search indexers) can parse
- Accurate, informative, insightful, and reflective of critical thinking:
  verify claims against the source code, do not speculate; flag ambiguities
  rather than paper over them; bring out non-obvious design decisions
- Cross-referenced: where relevant, link sections together using Sphinx
  `:ref:` references and a shared anchor map, with sufficient citations

Output format: reStructuredText source files placed under `docs/source/`
(one .rst file per major section). Then build HTML output via Sphinx:
  - Place `conf.py` under `docs/source/` (alabaster or sphinx-rtd-theme)
  - Place `index.rst` under `docs/source/` with a toctree referencing each
    section in a sensible reading order
  - Run `sphinx-build -b html docs/source docs/build/html` and report any
    warnings or errors

The deliverable is the documentation itself, NOT a documentation plan or
outline. Produce the actual prose, code excerpts, and reference material
that a reader can consume directly.

Tool-use constraints (IMPORTANT — failure to honor these will cause the run to
hang for hours):
- Confine ALL filesystem operations to the target codebase directory shown
  above. Do NOT run `find /`, `find C:\`, `grep -r` over `c:/Users`,
  `OneDrive`, `Desktop`, `Projects`, or any other drive-root or large parent
  directory. On this Windows host, recursive scans rooted at `/` or
  `c:/Users/...` traverse hundreds of GB and take hours; they will exceed
  the per-tool idle timeout and stall the workflow.
- Use the target codebase path explicitly when listing or searching files:
  e.g., `find <repo_root>/src -name '*.py'`, NOT `find / -name '*.py'`.
- Prefer the `Read`/`Glob`/`Grep` tools scoped to a known subdirectory over
  shell `find`/`grep -r` whenever possible.
- If you cannot locate a file with a bounded search, ASK or report the
  ambiguity rather than escalating to a drive-wide scan.
"""


# ===========================================================================
# Smoke test (no LLM)
# ===========================================================================

def test_yaml_smoke_instantiate(tmp_path, monkeypatch):
    """Validate the YAML loads and instantiates the new Topology B-extended
    shape without LLM calls.

    Topology B-extended:
        Outer Dual { base = PTI { planner = Dual{base=BTA{workers=MFDual},
        review}, executor = BTA{workers=Dual} }, review, fixer = PTI }

    Catches alias-registration regressions, `_-prefix` cascade bugs (incl.
    `_logger: auto`, `_debug_mode: true`), OmegaConf interpolation bugs,
    type mismatches, and template_variables resolution in seconds --
    before the real-CLI test burns money.
    """
    import agent_foundation.common.configs.registered_targets  # noqa: F401
    from rich_python_utils.config_utils import load_config, instantiate

    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.dual_inferencer import (
        DualInferencer,
    )
    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.breakdown_then_aggregate_inferencer import (
        BreakdownThenAggregateInferencer,
    )
    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.plan_then_implement_inferencer import (
        PlanThenImplementInferencer,
    )
    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.multi_flow_dual_inferencer import (
        MultiFlowDualInferencer,
    )
    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.multi_flow_inferencer import (
        MultiFlowInferencer,
    )
    from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code.claude_code_cli_inferencer import (
        ClaudeCodeCliInferencer,
    )
    from agent_foundation.common.inferencers.flow_parsers import (
        parse_winner_tag, parse_decision_stop, parse_finalplan_tag,
    )

    monkeypatch.setenv("DUAL_WS", str(tmp_path / "ws"))
    cfg = load_config(
        str(YAML_PATH),
        overrides={
            "_target_path": str(OPENSTARTUP_PATH),
            "templates_dir": str(TEMPLATES_DIR),
        },
    )
    inferencer = instantiate(cfg)

    # ----- Top-level: outer Dual wrapping PTI base + PTI fixer -----
    assert isinstance(inferencer, DualInferencer), type(inferencer).__name__
    assert isinstance(inferencer.base_inferencer, PlanThenImplementInferencer), (
        f"base must be PTI (Topology B-extended); got {type(inferencer.base_inferencer).__name__}"
    )
    assert isinstance(inferencer.fixer_inferencer, PlanThenImplementInferencer), (
        f"fixer must be PTI (mirror of base); got {type(inferencer.fixer_inferencer).__name__}"
    )
    assert inferencer.base_inferencer is not inferencer.fixer_inferencer, (
        "base and fixer must be distinct PTI instances"
    )
    assert isinstance(inferencer.review_inferencer, ClaudeCodeCliInferencer)
    # Outer reviewer judges the deliverable, not a plan — uses implementation/review
    assert inferencer.review_inferencer.template_root_space == "implementation", (
        f"outer reviewer must judge deliverable, not plan; got "
        f"template_root_space={inferencer.review_inferencer.template_root_space!r}"
    )
    assert inferencer.review_inferencer.template_key == "review"

    # ----- PTI's plan stage: Dual{base=BTA{workers=MFDual}, review} -----
    base_pti = inferencer.base_inferencer
    plan_dual = base_pti.planner_inferencer
    assert isinstance(plan_dual, DualInferencer), (
        f"plan stage must be Dual (review-and-fix the integrated plan); got {type(plan_dual).__name__}"
    )
    plan_bta = plan_dual.base_inferencer
    assert isinstance(plan_bta, BreakdownThenAggregateInferencer), (
        f"plan Dual.base must be BTA (decompose planning); got {type(plan_bta).__name__}"
    )
    assert plan_bta.name == "plan_bta"
    assert isinstance(plan_dual.review_inferencer, ClaudeCodeCliInferencer)

    # plan BTA worker_factory yields MFDual instances (multi-perspective per sub-plan)
    plan_factory = plan_bta.worker_factory["__default__"]
    assert isinstance(plan_factory, functools.partial), (
        "plan BTA worker_factory.__default__ should be functools.partial"
    )
    sample_mfdual = plan_factory()
    assert isinstance(sample_mfdual, MultiFlowDualInferencer), (
        f"plan BTA worker must be MFDual; got {type(sample_mfdual).__name__}"
    )
    assert sample_mfdual.propagate_runtime_input is True, (
        "MFDual planner MUST have propagate_runtime_input=true so runtime "
        "subtask description reaches the flows (architectural fix)"
    )
    assert sample_mfdual.inject_upstream_artifacts is True, (
        "MFDual planner MUST have inject_upstream_artifacts=true so "
        "{{ upstream_artifacts }} slot in target wrappers is populated"
    )
    # MFDual auto-constructs an internal MultiFlow as base_inferencer
    assert isinstance(sample_mfdual.base_inferencer, MultiFlowInferencer)
    assert sample_mfdual.base_inferencer.propagate_runtime_input is True, (
        "MultiFlow inside MFDual must also have propagate_runtime_input=true (forwarded)"
    )
    assert sample_mfdual.base_inferencer.inject_upstream_artifacts is True, (
        "MultiFlow inside MFDual must also have inject_upstream_artifacts=true (forwarded)"
    )
    assert len(sample_mfdual.flow_configs) == 2, (
        f"expected 2 parallel flows by default; got {len(sample_mfdual.flow_configs)}"
    )
    # Parsers wired correctly
    assert sample_mfdual.multi_flow_winner_parser is parse_winner_tag, (
        "winner parser alias not resolved correctly"
    )
    assert sample_mfdual.multi_flow_response_parser is parse_finalplan_tag, (
        "response parser alias (FinalPlanParser) not resolved correctly"
    )
    # Per-flow end_condition is the decision-stop parser
    assert sample_mfdual.flow_configs[0]["end_condition"] is parse_decision_stop, (
        "flow end_condition alias (DecisionStopParser) not resolved correctly"
    )

    # plan BTA aggregator uses the SHARED `aggregation` task_* variants for
    # pure prose integration. Under Option A, NO structured-output addenda
    # fire here — the exec BTA's breakdown_inferencer is responsible for
    # decomposing the prose plan into per-section subtasks. The aggregator's
    # only job is faithful integration of upstream sub-plans.
    plan_agg = plan_bta.aggregator_inferencer
    assert isinstance(plan_agg, ClaudeCodeCliInferencer)
    assert plan_agg.template_root_space == "plan"
    # Refactor 12+13: BTA.SLOT_DEFAULTS now injects the full aggregation
    # triplet via template_version + None-keyed template_variables.
    # task_response_format will be present (None) but renders to the empty
    # string at feed time because the wrapper template never references
    # {{ task_response_format }} for the plan BTA aggregator. The structured-
    # output addenda (winner_pick / iteration_judgment) live on MFDual via
    # template_extra_feed flags, not on the plan BTA aggregator slot itself.
    assert plan_agg.template_version == "aggregation"
    assert "task_preamble" in plan_agg.template_variables
    assert "task_instructions" in plan_agg.template_variables
    assert "task_response_format" in plan_agg.template_variables
    # Plan BTA aggregator must NOT have any output-schema addendum flag set.
    # If any of these fire, decomposition logic has leaked back into the
    # plan stage (Option A violation).
    plan_agg_flags = plan_agg.template_extra_feed or {}
    for _flag in ("include_iteration_judgment", "include_winner_pick", "include_execution_subtasks"):
        assert not plan_agg_flags.get(_flag, False), (
            f"Plan BTA aggregator must not set {_flag!r} (Option A: aggregator "
            f"does pure prose integration; per-section structuring is the exec "
            f"BTA breakdown_inferencer's job)"
        )

    # Plan BTA opts into modern slot semantics via the class-level flag
    # (replaces the old aggregator_prompt_builder factory wiring). When True,
    # BTA's _build_agg_input internally pushes formatted worker outputs into
    # template_extra_feed["upstream_artifacts"], forwards the breakdown's
    # aggregation_guidance, and returns original_query as inference_input.
    assert plan_bta.inject_upstream_artifacts_to_aggregator is True, (
        "Plan BTA must set inject_upstream_artifacts_to_aggregator=True to "
        "wire the {{ upstream_artifacts }} slot (replaces the old "
        "UpstreamInjectingAggregatorPromptBuilder factory pattern)"
    )
    # Custom prompt_builder should NOT be set when the flag is used (the flag
    # IS the modern path; the factory was the legacy escape hatch).
    assert plan_bta.aggregator_prompt_builder is None, (
        "Plan BTA must not set both aggregator_prompt_builder AND the flag — "
        "the flag is the canonical pattern, the factory the deprecated one"
    )

    # Option B (breakdown → aggregator handoff): the new internal path
    # must plumb the breakdown's aggregation_guidance into the aggregator's
    # template_extra_feed. Verify by directly calling the helper that
    # _build_agg_input uses.
    plan_bta._last_aggregation_guidance = (
        "Treat subtask 1 as backbone; layer subtasks 2-3 onto it; preserve glossary."
    )
    plan_bta._inject_aggregator_extra_feed(
        worker_results=["worker 1 output", "worker 2 output"],
    )
    assert plan_bta.aggregator_inferencer.template_extra_feed.get(
        "aggregation_guidance"
    ) == (
        "Treat subtask 1 as backbone; layer subtasks 2-3 onto it; preserve glossary."
    ), (
        "_inject_aggregator_extra_feed must forward _last_aggregation_guidance "
        "into the aggregator's template_extra_feed['aggregation_guidance']"
    )
    # And the upstream_artifacts slot must be populated with formatted
    # worker outputs (matches the ### Result N format used by both the
    # legacy default and the new injection path).
    upstream = plan_bta.aggregator_inferencer.template_extra_feed.get("upstream_artifacts")
    assert upstream is not None and "### Result 1" in upstream and "### Result 2" in upstream, (
        f"upstream_artifacts must contain formatted ### Result N entries; got {upstream!r}"
    )
    # Stale aggregation_guidance must be dropped when the next breakdown
    # produces no guidance (else previous-call guidance leaks into the
    # current aggregator prompt).
    plan_bta._last_aggregation_guidance = None
    plan_bta._inject_aggregator_extra_feed(
        worker_results=["worker 1 output"],
    )
    assert "aggregation_guidance" not in plan_bta.aggregator_inferencer.template_extra_feed, (
        "Stale aggregation_guidance must be dropped when the next breakdown "
        "does not produce one"
    )

    # MFDual's final aggregator uses the SHARED structured-aggregation triplet.
    # Refactor 13: template_version drives expansion; per-key values are None.
    mfdual_agg = sample_mfdual.multi_flow_aggregator_inferencer
    assert isinstance(mfdual_agg, ClaudeCodeCliInferencer)
    assert mfdual_agg.template_version == "aggregation"
    assert "task_instructions" in mfdual_agg.template_variables
    assert mfdual_agg.template_extra_feed.get("include_winner_pick") is True

    # MFDual's per-flow followup_inferencer uses SHARED template with
    # include_iteration_judgment flag (asks the model to judge whether further
    # iteration adds value; the response-format addendum then specifies emit a
    # JSON `iteration_judgment` block with `decision: continue|stop`).
    flow_followup = sample_mfdual.flow_configs[0]["followup_inferencer"]
    assert isinstance(flow_followup, ClaudeCodeCliInferencer)
    assert flow_followup.template_version == "aggregation"
    assert "task_instructions" in flow_followup.template_variables
    assert flow_followup.template_extra_feed.get("include_iteration_judgment") is True

    # ----- PTI's exec stage: bare BTA{workers=Dual{base+review}} -----
    exec_bta = base_pti.executor_inferencer
    assert isinstance(exec_bta, BreakdownThenAggregateInferencer), (
        f"exec stage must be bare BTA (no surrounding Dual); got {type(exec_bta).__name__}"
    )
    assert exec_bta.name == "exec_bta"
    # Exec BTA also opts into modern slot semantics. Closes the historical
    # gap where exec_bta lacked a prompt_builder and worker outputs ended up
    # in the wrapper's {{ input }} slot (mislabeled as "Original User Request").
    assert exec_bta.inject_upstream_artifacts_to_aggregator is True, (
        "exec_bta must set inject_upstream_artifacts_to_aggregator=True so the "
        "exec aggregator receives upstream_artifacts + aggregation_guidance "
        "via template_extra_feed, with original BTA query in {{ input }}"
    )
    assert exec_bta.aggregator_prompt_builder is None
    # Exec breakdown uses the generic task_breakdown wrapper — no use-case-specific
    # task_instructions variant. Same generic-wrapper philosophy applies to the
    # exec workers and aggregator below.
    exec_breakdown = exec_bta.breakdown_inferencer
    assert exec_breakdown.template_root_space == "task_breakdown"
    assert not exec_breakdown.template_variables.get("task_instructions"), (
        "exec_breakdown must NOT set a task_instructions variant — the generic "
        "wrapper carries the cognitive load"
    )
    # Exec workers are Duals (per-section write+review+fix). They use ONLY the
    # generic implementation/main/initial.jinja2 wrapper — no task_instructions
    # variant. The LLM infers the deliverable shape from the subtask description.
    exec_factory = exec_bta.worker_factory["__default__"]
    sample_exec_dual = exec_factory()
    assert isinstance(sample_exec_dual, DualInferencer), (
        f"exec BTA worker must be Dual (per-section write+review+fix); got {type(sample_exec_dual).__name__}"
    )
    assert isinstance(sample_exec_dual.base_inferencer, ClaudeCodeCliInferencer)
    assert sample_exec_dual.base_inferencer.template_root_space == "implementation"
    assert not (sample_exec_dual.base_inferencer.template_variables or {}).get("task_instructions"), (
        "exec worker base must NOT set a task_instructions variant — the generic "
        "wrapper plus the subtask description carry all needed context"
    )
    # Exec aggregator: uses the implementation-namespace aggregation preamble
    # to consume {{ upstream_artifacts }} and {{ aggregation_guidance }}
    # (populated by BTA's inject_upstream_artifacts_to_aggregator path).
    # Refactor 12+13: BTA now defaults the full triplet via SLOT_DEFAULTS.
    # The newly-authored implementation/.../task_instructions/aggregation.jinja2
    # provides aggregator-role framing (NOT the worker-style default.jinja2),
    # so prompt content stays role-correct. Task-specific instructions still
    # ride in the breakdown's aggregation_guidance via the wrapper template's
    # {{ aggregation_guidance }} slot.
    exec_agg = exec_bta.aggregator_inferencer
    assert exec_agg.template_root_space == "implementation"
    assert exec_agg.template_version == "aggregation"
    assert "task_preamble" in exec_agg.template_variables
    assert "task_instructions" in exec_agg.template_variables
    # Verify the implementation-namespace aggregation task_instructions file
    # exists (authored to make the BTA flip semantically safe). load_variable
    # must return real aggregator framing, NOT the worker-style default.jinja2.
    _impl_vars = exec_agg.template_manager.load_variables(
        {"task_instructions": "aggregation", "task_preamble": "aggregation"},
        root_space="implementation",
    )
    impl_agg_instructions_text = _impl_vars["task_instructions"]
    assert "aggregating" in impl_agg_instructions_text.lower(), (
        "implementation/main/_variables/task_instructions/aggregation.jinja2 "
        "must contain aggregator-role framing, not worker-style instructions "
        "(which would be the default.jinja2 fallback)"
    )
    impl_agg_preamble_text = _impl_vars["task_preamble"]
    assert "upstream_artifacts" in impl_agg_preamble_text
    assert "aggregation_guidance" in impl_agg_preamble_text
    # Implementation aggregation is intentionally simpler than plan's:
    # no MFDual-specific addendum branches (workflows are non-overlapping
    # at execution time; no parallel exploration to judge or winner to pick).
    assert "include_iteration_judgment" not in impl_agg_preamble_text, (
        "implementation aggregation preamble must NOT include MFDual-specific "
        "branches — execution stage has no MFDual"
    )
    assert "include_winner_pick" not in impl_agg_preamble_text

    # ----- _-prefix cascade reached every leaf -----
    # _logger: auto → JsonLogger per leaf workspace; _debug_mode: true cascaded
    # too. Pick a deep leaf and verify all the cascade fields landed.
    deep_leaf = sample_mfdual.flow_configs[0]["initial_inferencer"]
    assert isinstance(deep_leaf, ClaudeCodeCliInferencer)
    # Model alias resolved
    assert deep_leaf.model_name in ("opus[1m]", "opus", "claude-opus-4-7[1m]"), (
        f"unexpected model_name on deep leaf: {deep_leaf.model_name!r}"
    )
    # _target_path cascade reached deep leaves
    assert deep_leaf.target_path == str(OPENSTARTUP_PATH), (
        f"_target_path cascade failed for deep leaf; got {deep_leaf.target_path!r}"
    )
    # _idle_timeout_seconds + _output_path cascades
    assert deep_leaf.idle_timeout_seconds == 600
    assert deep_leaf.output_path == "output.md"
    # _logger: auto either reached the leaf as the literal "auto" sentinel (still
    # deferred — workspace assignment hasn't happened for this fresh-from-factory
    # leaf), OR has already resolved to a concrete logger dict (if workspace
    # propagated). Both are acceptable; the cascade itself MUST have hit:
    assert deep_leaf.logger is not None, "_logger cascade missed deep leaf entirely"
    assert deep_leaf.logger == "auto" or not isinstance(deep_leaf.logger, str), (
        f"_logger value should be 'auto' or a resolved logger; got {deep_leaf.logger!r}"
    )
    # _debug_mode cascade reached deep leaf
    assert deep_leaf.debug_mode is True, "_debug_mode: true cascade did not reach deep leaf"

    # Verify per-leaf logger DID resolve where workspace was already assigned —
    # the plan BTA's aggregator (constructed at YAML instantiation, gets workspace
    # via _propagate_workspace_to_children before the test inspects it).
    assert plan_agg.logger is not None and not isinstance(plan_agg.logger, str), (
        f"plan BTA aggregator's _logger: auto should have resolved to a JsonLogger; "
        f"got {plan_agg.logger!r}"
    )

    # ----- Workspace propagation: outer Dual → PTI children → BTAs -----
    # After Refactor 1, the YAML carries only the top-level `workspace_root`.
    # The outer Dual creates its `_workspace` from that, then propagation
    # cascades through the inferencer tree via each `_workspace` setter.
    # Each child gets `parent_workspace.child("<attr_name>")`.
    assert base_pti._workspace is not None, "base PTI didn't receive propagated workspace"
    assert base_pti._workspace.root.replace("\\", "/").endswith(
        "/children/base_inferencer"
    ), f"base PTI workspace root: {base_pti._workspace.root!r}"
    fixer_pti = inferencer.fixer_inferencer
    assert fixer_pti._workspace is not None, "fixer PTI didn't receive propagated workspace"
    assert fixer_pti._workspace.root.replace("\\", "/").endswith(
        "/children/fixer_inferencer"
    ), f"fixer PTI workspace root: {fixer_pti._workspace.root!r}"
    # Plan BTA: under planner_inferencer (Dual) under base_inferencer (PTI)
    # under outer Dual. Path mirrors the topology.
    assert plan_bta._workspace is not None, (
        "plan_bta should receive a workspace via the propagation cascade"
    )
    assert plan_bta._workspace.root.replace("\\", "/").endswith(
        "/children/planner_inferencer/children/base_inferencer"
    ), f"plan_bta workspace root: {plan_bta._workspace.root!r}"
    # Exec BTA: directly under base_inferencer (PTI) under outer Dual,
    # via the executor_inferencer slot.
    assert exec_bta._workspace is not None, (
        "exec_bta should receive a workspace via the propagation cascade"
    )
    assert exec_bta._workspace.root.replace("\\", "/").endswith(
        "/children/executor_inferencer"
    ), f"exec_bta workspace root: {exec_bta._workspace.root!r}"

    # ----- Template rendering smoke checks -----
    # Generic task_breakdown wrapper (no use-case-specific task_instructions).
    # The breakdown LLM gets the integrated plan as `input` plus the wrapper's
    # universal decomposition guidance and produces subtasks; downstream
    # workers are self-sufficient (no args contract).
    rendered_breakdown = exec_breakdown.template_manager(
        "initial",
        active_template_root_space="task_breakdown",
        input="(integrated documentation plan in free-form prose here)",
        task_preamble="",
    )
    # The wrapper must carry the four-criteria self-check (Comprehensive,
    # Independent, Non-conflicting, Actionable) — the conflict-handling
    # criterion is what lets the LLM encode unavoidable conflicts as
    # subtask_dependencies rather than producing parallel-unsafe siblings.
    for _criterion in ("Comprehensive", "Independent", "Non-conflicting", "Actionable"):
        assert _criterion in rendered_breakdown, (
            f"task_breakdown wrapper must include the '{_criterion}' decomposition criterion"
        )
    assert "subtask_dependencies" in rendered_breakdown, (
        "task_breakdown wrapper must instruct the LLM how to encode "
        "subtask_dependencies (used both for logical ordering and conflict "
        "serialization)"
    )

    # The breakdown wrapper must instruct the LLM to also fill an
    # `aggregation_guidance` field. Without this, the breakdown's reasoning
    # about how to reconstruct the integrated artifact is lost between
    # breakdown and aggregator stages.
    assert "aggregation_guidance" in rendered_breakdown, (
        "task_breakdown wrapper must instruct the breakdown LLM to emit an "
        "`aggregation_guidance` field — that field carries reconstruction "
        "guidance forward to the aggregator (Option B for breakdown→aggregator "
        "handoff)"
    )
    assert "Aggregation Guidance" in rendered_breakdown, (
        "task_breakdown wrapper must include the 'Aggregation Guidance' "
        "instructional section that explains what the LLM should put in the "
        "`aggregation_guidance` field"
    )

    # task_preamble: aggregation must consume the breakdown's aggregation_guidance
    # via {% if aggregation_guidance %} so plan BTA aggregators see Option B
    # plumbing (the breakdown's reconstruction strategy reaches the aggregator).
    _plan_vars = plan_agg.template_manager.load_variables(
        {"task_preamble": "aggregation", "task_instructions": "aggregation",
         "task_response_format": "aggregation"},
        root_space="plan",
    )
    agg_preamble_text = _plan_vars["task_preamble"]
    assert "aggregation_guidance" in agg_preamble_text, (
        "task_preamble/aggregation.jinja2 must reference {{ aggregation_guidance }} "
        "so the breakdown's reconstruction guidance reaches the aggregator"
    )
    assert "{%- if aggregation_guidance %}" in agg_preamble_text or \
           "{% if aggregation_guidance %}" in agg_preamble_text, (
        "task_preamble must gate aggregation_guidance behind an `{% if %}` so "
        "breakdowns that don't emit guidance render cleanly"
    )

    # aggregation task_instructions: terse cognitive guidance (compare inputs,
    # integrate faithfully, maintain structure consistency, avoid hacky/ad-hoc).
    # NO structured-output addenda — those moved to task_response_format.
    int_agg_text = _plan_vars["task_instructions"]
    assert "consolidated artifact" in int_agg_text, (
        "aggregation task_instructions should mention 'consolidated artifact' (the integration goal)"
    )
    assert "DO NOT be hacky" in int_agg_text, (
        "aggregation task_instructions should include the rigor reminder"
    )
    # The {% if %} addenda for output schema have moved to task_response_format
    assert "include_execution_subtasks" not in int_agg_text, (
        "aggregation task_instructions should NOT contain output-schema addenda — "
        "those belong in task_response_format/aggregation.jinja2"
    )

    # Structured-output schema lives in task_response_format/aggregation.jinja2
    response_format_text = _plan_vars["task_response_format"]
    # Two surviving addenda under Option A: iteration_judgment (per-flow followup)
    # and winner_pick (MFDual final aggregator). No execution_breakdown — the
    # plan aggregator emits prose, exec BTA breakdown does decomposition.
    assert "include_iteration_judgment" in response_format_text
    assert "include_winner_pick" in response_format_text
    assert "include_execution_subtasks" not in response_format_text, (
        "Option A: include_execution_subtasks must be removed from "
        "task_response_format/aggregation.jinja2 — decomposition belongs "
        "to the exec BTA breakdown_inferencer, not the plan aggregator"
    )
    # JSON-fenced output schema for the surviving addenda.
    assert "```json iteration_judgment" in response_format_text
    assert "```json winner_pick" in response_format_text
    assert "```json execution_breakdown" not in response_format_text
    assert "winner_index" in response_format_text
    # Structured execution-subtask schema must NOT appear in plan response format
    assert "execution_subtasks" not in response_format_text
    assert "shared_context" not in response_format_text

    # Verify the per-step followup formatter produces clean text.
    # The formatter is now an inlined Python method on MultiFlowInferencer
    # (no longer a Jinja template under prompt_templates/). The original task
    # is intentionally NOT included — under inject_upstream_artifacts=True,
    # the wrapper template's {{ input }} slot carries it separately.
    formatted_followup = sample_mfdual.base_inferencer._format_followup_input(
        your_prev="prev draft",
        flow_idx=0,
        step_idx=2,
        visible_plans={1: "peer 1"},
    )
    assert "prev draft" in formatted_followup
    assert "peer 1" in formatted_followup
    assert "flow 0" in formatted_followup
    assert "step 1" in formatted_followup  # prev_step_idx = step_idx - 1
    # Critical: data formatter carries NO cognitive instructions (those live in
    # the followup_inferencer's task_instructions:aggregation wrapper).
    assert "Decision" not in formatted_followup, (
        "_format_followup_input should be a thin DATA FORMATTER only — "
        "cognitive instructions (incl. Decision tag) belong in the followup_inferencer's "
        "task_instructions (aggregation), not in this formatter"
    )
    # Original task must NOT be embedded (avoids duplication with wrapper's
    # {{ input }} slot that already carries it under inject_upstream_artifacts).
    assert "Original task" not in formatted_followup, (
        "_format_followup_input must not include the original task — "
        "the wrapper's {{ input }} slot supplies it separately under "
        "inject_upstream_artifacts=True (avoids prompt-level duplication)"
    )

    # Empty-peers branch: when the flow has no peer visibility, the formatter
    # emits a sensible placeholder instead of crashing.
    formatted_no_peers = sample_mfdual.base_inferencer._format_followup_input(
        your_prev="prev draft",
        flow_idx=0,
        step_idx=2,
        visible_plans={},
    )
    assert "No peer outputs visible yet" in formatted_no_peers


# ===========================================================================
# Real-CLI integration test
# ===========================================================================

@pytest.mark.integration
@skip_claude
@skip_openstartup
@pytest.mark.asyncio
@pytest.mark.timeout(60 * 60 * 6)  # 6h cap; covers deep profile worst-case
async def test_real_dual_outside_bta_pti_mfdual_dual(tmp_path, capfd):
    """Real-CLI run of the full composition through `_run_topology()`.

    Matches the canonical `/task` invocation path. Asserts wire-level
    correctness: topology completes, both BTA workspaces are populated
    (or at least the base; fixer is populated iff reviewer triggered fix),
    and the response is non-trivially long.

    Profile via ``BMP_REAL_PROFILE`` env var. See PROFILES dict above.
    """
    p = PROFILES[_PROFILE]
    print(f"\n[bmp-real] profile={_PROFILE!r}: {p}")

    # _run_topology is the exact path /task slash and agent dispatch use
    from openteam.server.resources.tools.task.executor import _run_topology

    overrides = {
        "_target_path": str(OPENSTARTUP_PATH),
        "templates_dir": str(TEMPLATES_DIR),
        "consensus_config.max_iterations": p["outer_dual_iter"],
        "base_inferencer.max_breakdown": p["bta_workers"],
        "fixer_inferencer.max_breakdown": p["bta_workers"],
        "base_inferencer.worker_factory.__default__.planner_inferencer.consensus_config.max_iterations": p["mfdual_iter"],
        "base_inferencer.worker_factory.__default__.executor_inferencer.consensus_config.max_iterations": p["inner_dual_iter"],
        "fixer_inferencer.worker_factory.__default__.planner_inferencer.consensus_config.max_iterations": p["mfdual_iter"],
        "fixer_inferencer.worker_factory.__default__.executor_inferencer.consensus_config.max_iterations": p["inner_dual_iter"],
    }

    # Let `_run_topology` allocate its own working_dir (server/_runtime/tasks/
    # task_<id>_<ts>) and inject it as `workspace_root` via setdefault. The
    # YAML's `${workspace_root}/base_bta` interpolation resolves against that
    # path, so context_updates["workspace_path"] aligns with the actual
    # workspace where artifacts land. (Passing our own workspace_root override
    # would create a path mismatch since _run_topology returns its allocated
    # path, not our override, in context_updates.)
    result = await _run_topology(
        source=("file", str(YAML_PATH)),
        request=DOC_TASK,
        overrides=overrides,
        session_context={"working_dir": str(tmp_path / "task_ws")},
    )

    # ----- Topology completion -----
    assert result is not None, "_run_topology returned None"
    success = result.context_updates.get("success") is True
    assert success, f"topology reported failure: {result.result!r}"

    response_text = (result.result or "").strip()
    assert len(response_text) >= p["min_response_len"], (
        f"profile={_PROFILE!r}: expected >={p['min_response_len']} chars, "
        f"got {len(response_text)}"
    )

    # ----- Workspace artifacts -----
    workspace_path = result.context_updates.get("workspace_path")
    assert workspace_path, "context_updates missing workspace_path"
    workspace = Path(workspace_path)
    assert workspace.exists(), f"workspace dir missing: {workspace}"

    base_dir = workspace / "base_bta"
    fixer_dir = workspace / "fixer_bta"
    assert base_dir.exists(), (
        f"base BTA workspace missing under {workspace}; "
        f"contents: {list(workspace.iterdir())}"
    )

    # base BTA's children/ must have artifacts (the workers ran)
    base_children = list((base_dir / "children").rglob("*")) \
        if (base_dir / "children").exists() else []
    base_artifact_count = sum(1 for f in base_children if f.is_file())
    assert base_artifact_count > 0, (
        f"base BTA produced no children/ artifacts under {base_dir}"
    )

    # fixer BTA may or may not have run depending on reviewer's verdict.
    # NOTE: workspace propagation (InferencerBase._propagate_workspace_to_children)
    # creates SKELETON subdirs (artifacts/, checkpoints/, children/, etc.) at
    # construction time, so directory existence alone doesn't indicate the
    # fixer fired. Check for FILES specifically — if reviewer approved on first
    # pass, fixer has skeleton dirs but zero files.
    fixer_files = (
        [f for f in fixer_dir.rglob("*") if f.is_file()]
        if fixer_dir.exists() else []
    )
    fixer_fired = bool(fixer_files)
    if fixer_fired:
        fixer_children = list((fixer_dir / "children").rglob("*")) \
            if (fixer_dir / "children").exists() else []
        fixer_artifact_count = sum(1 for f in fixer_children if f.is_file())
        assert fixer_artifact_count > 0, (
            f"fixer BTA fired but produced no children/ artifacts under {fixer_dir}"
        )

    # ----- Observability summary (visible with -s) -----
    print(
        f"\n[bmp-real] outer_dual_iter={p['outer_dual_iter']} "
        f"fixer_fired={fixer_fired} "
        f"base_artifacts={base_artifact_count} "
        f"response_chars={len(response_text)}"
    )
