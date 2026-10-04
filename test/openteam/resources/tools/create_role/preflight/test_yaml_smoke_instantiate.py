"""Preflight: YAML smoke instantiate for ``create_role_bta.yaml``.

Loads ``create_role_bta.yaml`` via ``load_config + instantiate``. Catches
regressions in:
  * YAML schema (missing keys, wrong types)
  * ``_-prefix`` cascade (``_model_id``, ``_debug_mode``, etc.)
  * ``_params`` resolution (``${_params.default_research_inferencer}``)
  * OmegaConf interpolation
  * ``_partial_`` / ``_factory`` auto-injection
  * BTA + RovoChat + RovoDevCli construction
  * Option A MI fix: RovoChat inherits TemplatedInferencerBase

Runtime: ~5s, no LLM cost.
"""

from __future__ import annotations

from ._common import (  # noqa: F401  (used inside test body)
    COREPROJECTS_ROOT,
    OPENSTARTUP_ROOT,
    set_template_root_env,
    YAML_PATH,
)


def test_create_role_yaml_smoke_instantiate(tmp_path, monkeypatch):
    """Load + instantiate create_role_bta.yaml."""
    # Configure templates root (needed by aggregator's TemplateManager)
    set_template_root_env(monkeypatch)

    # Ensure registry imports run (registers @lazy_target classes)
    import agent_foundation.common.configs.registered_targets  # noqa: F401
    from rich_python_utils.config_utils import instantiate, load_config

    # Load YAML and instantiate (must supply workspace_root — mandatory key)
    cfg = load_config(
        str(YAML_PATH),
        overrides={
            "_params": {"workspace_root": str(tmp_path)},
        },
    )
    inst = instantiate(cfg)

    # Verify top-level is BTA
    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.breakdown_then_aggregate_inferencer import (
        BreakdownThenAggregateInferencer,
    )

    assert isinstance(inst, BreakdownThenAggregateInferencer), (
        f"Expected BTA, got {type(inst).__name__}"
    )

    # Verify breakdown_inferencer is RovoChat (default for research role)
    from agent_foundation.common.inferencers.agentic_inferencers.external.rovochat.rovochat_inferencer import (
        RovoChatInferencer,
    )

    assert isinstance(inst.breakdown_inferencer, RovoChatInferencer), (
        f"Expected breakdown=RovoChat, got {type(inst.breakdown_inferencer).__name__}"
    )

    # Verify aggregator is RovoDevCLI (default for aggregation role)
    from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev.rovodev_cli_inferencer import (
        RovoDevCliInferencer,
    )

    assert isinstance(inst.aggregator_inferencer, RovoDevCliInferencer), (
        f"Expected aggregator=RovoDevCLI, got "
        f"{type(inst.aggregator_inferencer).__name__}"
    )

    # Verify cascades reached children
    assert inst.debug_mode is True, "BTA.debug_mode should be cascaded from _debug_mode"
    assert inst.breakdown_inferencer.debug_mode is True, (
        "breakdown.debug_mode should be cascaded from _debug_mode"
    )
    assert inst.aggregator_inferencer.debug_mode is True, (
        "aggregator.debug_mode should be cascaded from _debug_mode"
    )

    # Verify Option A MI fix: RovoChat now has template_* attribs available
    assert hasattr(inst.breakdown_inferencer, "template_key"), (
        "RovoChatInferencer should have template_key attrib (MI fix). "
        "If missing, the TemplatedInferencerBase parent is not in MRO."
    )
    assert hasattr(inst.breakdown_inferencer, "template_root_space"), (
        "RovoChatInferencer should have template_root_space attrib (MI fix)"
    )
    assert hasattr(inst.breakdown_inferencer, "template_variables"), (
        "RovoChatInferencer should have template_variables attrib (MI fix)"
    )

    # Verify MI is in MRO
    from agent_foundation.common.inferencers.templated_inferencer_base import (
        TemplatedInferencerBase,
    )

    assert isinstance(inst.breakdown_inferencer, TemplatedInferencerBase), (
        "RovoChatInferencer must inherit from TemplatedInferencerBase (MI fix)"
    )

    # Verify worker_factory is set + callable
    assert inst.worker_factory is not None, "BTA.worker_factory must be set"
    assert callable(inst.worker_factory), (
        f"worker_factory should be callable; got {type(inst.worker_factory).__name__}"
    )

    # ------------------------------------------------------------------
    # Surfacing-mechanism contract (Part 2: two-axis model)
    # ------------------------------------------------------------------
    # The canonical role doc surfaces inside the workspace by living directly
    # in ``outputs/`` and being promoted up the BTA boundary. Part 2 retired
    # the ``final_deliverables/`` folder and the deliverable flags
    # (``use_final_deliverables_folder`` / ``output_is_deliverable``), so the
    # topology must NOT set them and the workspace/attribs must not exist.

    # 1) Workspace is bound and carries NO retired deliverable flags.
    assert inst._workspace is not None, (
        "BTA must have a workspace bound at construction time"
    )
    assert not hasattr(inst._workspace, "use_final_deliverables_folder"), (
        "workspace.use_final_deliverables_folder is RETIRED (Part 2) — "
        "``outputs/`` IS the deliverable set now."
    )
    assert not hasattr(inst._workspace, "deliverables_dir"), (
        "workspace.deliverables_dir is RETIRED (Part 2) — use outputs_dir."
    )

    # 2) The aggregator no longer carries the retired ``output_is_deliverable``
    #    flag (promotion is role-based via _symlink_child_output).
    assert not hasattr(inst.aggregator_inferencer, "output_is_deliverable"), (
        "aggregator.output_is_deliverable is RETIRED (Part 2). The aggregator's "
        "role_document.md is promoted because it lives in the canonical child's "
        "``outputs/``, not because of a flag."
    )

    # 3) BTA's own top-level output uses a NON-conflicting filename so the
    # summary text doesn't overwrite the real role_document.md that the
    # aggregator writes to ``outputs/``.
    assert inst.output_path == "run_summary.md", (
        f"BTA.output_path should be 'run_summary.md' (not 'role_document.md') "
        f"to avoid the summary text overwriting the canonical aggregator "
        f"deliverable at the top level. Got: {inst.output_path!r}"
    )
    assert inst.aggregator_inferencer.output_path == "role_document.md", (
        f"aggregator.output_path should be 'role_document.md' (the canonical "
        f"deliverable name). Got: {inst.aggregator_inferencer.output_path!r}"
    )
