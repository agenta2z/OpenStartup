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
        "outer_dual_iter": 2,
        "bta_workers": 3,
        "mfdual_iter": 2,
        "inner_dual_iter": 2,
        "min_response_len": 600,
    },
}
_PROFILE = os.environ.get("BMP_REAL_PROFILE", "shallow")


# ---------------------------------------------------------------------------
# Task prompt
# ---------------------------------------------------------------------------

DOC_TASK = """\
You are creating a documentation plan for OpenStartup's `/task` slash
command and its YAML topology composition system. The codebase is at
the current working directory. Investigate first via file reads; do
not speculate.

Your output is the PLAN, not the documentation itself. Cover with
concrete file:line citations:
  1. Slash entry path -- `manager_websocket_routes._try_dev_slash_command`
     to `task/executor.execute`.
  2. Agent entry path -- ConversationalInferencer tool dispatch reaching
     the same `task/executor.execute`. Note where paths converge and
     diverge (workspace allocation heuristics).
  3. YAML composition -- `_target_:` alias registry, the 5-priority
     `--agent-config` resolver, `_-prefix` cascade injection, and
     post-instantiate mutations (`--model`, `--no-dual`).
  4. Workspace allocation -- per-task `_runtime/tasks/<id>` vs the
     slash-path's heuristic rejection of unsafe `working_dir` hints.
  5. WebSocket event surface -- events emitted to the UI during a task
     run and how `useGraphState` / `useManagerChat` consume them.

For each section: list specific files with line refs, key
functions/classes, recommended depth, and ambiguities worth flagging.
Be concrete; avoid generic boilerplate.
"""


# ===========================================================================
# Smoke test (no LLM)
# ===========================================================================

def test_yaml_smoke_instantiate(tmp_path, monkeypatch):
    """Validate the YAML loads and instantiates without LLM calls.

    Catches alias-registration regressions, `_-prefix` cascade bugs,
    OmegaConf interpolation bugs, and type mismatches in seconds --
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
    from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code.claude_code_cli_inferencer import (
        ClaudeCodeCliInferencer,
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

    # Outer Dual + two distinct BTAs
    assert isinstance(inferencer, DualInferencer), type(inferencer).__name__
    assert isinstance(inferencer.base_inferencer, BreakdownThenAggregateInferencer)
    assert isinstance(inferencer.fixer_inferencer, BreakdownThenAggregateInferencer)
    assert inferencer.base_inferencer is not inferencer.fixer_inferencer, (
        "base and fixer must be distinct BTA instances"
    )
    assert inferencer.base_inferencer.name == "base_bta"
    assert inferencer.fixer_inferencer.name == "fixer_bta"
    assert isinstance(inferencer.review_inferencer, ClaudeCodeCliInferencer)

    # worker_factory.__default__ is auto-partial'd to functools.partial
    base_factory = inferencer.base_inferencer.worker_factory["__default__"]
    fixer_factory = inferencer.fixer_inferencer.worker_factory["__default__"]
    assert isinstance(base_factory, functools.partial), (
        "base BTA worker_factory.__default__ should be a functools.partial "
        "(auto-injected by _filter_attrs_keys for *_factory fields)"
    )
    assert isinstance(fixer_factory, functools.partial)

    # Calling factory() produces a fresh PTI tree
    sample_pti = base_factory()
    assert isinstance(sample_pti, PlanThenImplementInferencer)
    # Planner is a single Dual (MFDual was dropped due to architectural
    # mismatch — see YAML comment on planner_inferencer for details).
    assert isinstance(sample_pti.planner_inferencer, DualInferencer)
    assert isinstance(sample_pti.executor_inferencer, DualInferencer)

    # _-prefix cascade injection reached every leaf ClaudeCodeCli
    # (planner is a Dual; its review_inferencer is a ClaudeCodeCli leaf)
    leaf_review = sample_pti.planner_inferencer.review_inferencer
    assert isinstance(leaf_review, ClaudeCodeCliInferencer)
    # model_name normalized via resolve_model_tag — accept either alias or resolved form
    assert leaf_review.model_name in ("opus[1m]", "opus", "claude-opus-4-7[1m]"), (
        f"unexpected model_name on leaf reviewer: {leaf_review.model_name!r}"
    )
    assert leaf_review.target_path == str(OPENSTARTUP_PATH), (
        f"_target_path cascade failed; got {leaf_review.target_path!r}"
    )
    assert leaf_review.idle_timeout_seconds == 600, (
        f"_idle_timeout_seconds cascade failed; got {leaf_review.idle_timeout_seconds}"
    )
    # _output_path cascade reached every leaf → resolve_output_path() returns
    # a leaf-workspace-namespaced path. Without this, templates render
    # `{{ output_path }}` as empty and models bail.
    assert leaf_review.output_path == "output.md", (
        f"_output_path cascade failed; got {leaf_review.output_path!r}"
    )

    # Workspace interpolation produced distinct subdirs
    base_ws = str(inferencer.base_inferencer.workspace_root or "")
    fixer_ws = str(inferencer.fixer_inferencer.workspace_root or "")
    assert "base_bta" in base_ws, f"base BTA workspace_root: {base_ws!r}"
    assert "fixer_bta" in fixer_ws, f"fixer BTA workspace_root: {fixer_ws!r}"
    assert base_ws != fixer_ws, "BTA workspaces must be distinct"

    # ----- Template wiring -----
    # _template_manager cascade-injected into every InferencerBase
    # descendant; specific inferencers have their template_root_space set.
    breakdown = inferencer.base_inferencer.breakdown_inferencer
    aggregator = inferencer.base_inferencer.aggregator_inferencer
    outer_reviewer = inferencer.review_inferencer

    for inf, name in [
        (breakdown, "base.breakdown"),
        (aggregator, "base.aggregator"),
        (outer_reviewer, "outer.review"),
    ]:
        assert inf.template_manager is not None, (
            f"{name} missing template_manager (cascade injection failed?)"
        )

    assert breakdown.template_root_space == "task_breakdown", (
        f"breakdown template_root_space: {breakdown.template_root_space!r}"
    )
    assert aggregator.template_root_space == "plan", (
        f"aggregator template_root_space: {aggregator.template_root_space!r}"
    )
    assert outer_reviewer.template_root_space == "plan"
    assert outer_reviewer.template_key == "review", (
        f"outer reviewer template_key: {outer_reviewer.template_key!r}"
    )

    # Template manager actually resolves the breakdown template that BTA
    # depends on (task_breakdown/main/initial.jinja2). This validates
    # `templates_dir` override propagated correctly and the Jinja file is
    # discoverable under {templates_dir}/{root_space}/{type}/{key}.jinja2.
    rendered = breakdown.template_manager(
        "initial",
        active_template_root_space="task_breakdown",
        input="DECOMPOSE THIS TASK",
        task_preamble="",
        task_instructions="",
    )
    assert "decomposed_subtasks" in rendered, (
        "task_breakdown template did not render the JSON-decomposition "
        "instruction; check templates_dir resolution"
    )
    assert "DECOMPOSE THIS TASK" in rendered, (
        "template did not interpolate {{ input }}"
    )

    # Same check for plan/main/initial.jinja2 (used by aggregator)
    rendered_plan = aggregator.template_manager(
        "initial",
        active_template_root_space="plan",
        input="SYNTHESIZE THIS",
        task_preamble="",
        task_instructions="",
        output_path="/tmp/out.md",
    )
    assert "<Response>" in rendered_plan, "plan/initial template missing <Response> tags"
    assert "SYNTHESIZE THIS" in rendered_plan

    # Critical: predefined_variables=false suppresses the OpenStartup AI HR
    # persona auto-load from prompt_templates/.variables.yaml. Verify no
    # persona contamination. Without this guard, every prompt would prefix
    # "You are OpenStartup, serving as an AI Human Resources agent..."
    assert "AI Human Resources agent" not in rendered, (
        "task_breakdown render leaked the AI HR persona "
        "(predefined_variables not actually disabled)"
    )
    assert "AI Human Resources agent" not in rendered_plan, (
        "plan render leaked the AI HR persona"
    )
    assert "OpenStartup" not in rendered.split("Original")[0], (
        "task_breakdown render leaked employee.name=OpenStartup as a persona prefix"
    )


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
