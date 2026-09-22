"""Preflight test: the outer Dual's workspace uses the two-axis contract.

Part 2 retired the ``final_deliverables/`` subfolder and the
``use_final_deliverables_folder`` workspace attrib. ``outputs/`` IS the
deliverable set now, so the topology no longer needs (and must not carry) the
retired flag.

This file used to assert the outer Dual's workspace had
``use_final_deliverables_folder=True`` and a ``deliverables_dir`` ending in
``outputs/final_deliverables``. That contract is inverted: the attrib/property
are DELETED, and deliverables resolve straight to ``outputs/``.

It still verifies the YAML instantiates and that the outer Dual owns a real
``InferencerWorkspace`` whose ``outputs_dir`` resolves under ``outputs/``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Resolve the YAML config — same convention as the legacy
# `test_yaml_smoke_instantiate`. preflight/ lives one level below task/.
_HERE = Path(__file__).resolve().parent
YAML_PATH = (
    _HERE.parents[5]
    / "src"
    / "openteam"
    / "server"
    / "resources"
    / "tools"
    / "task"
    / "topologies"
    / "breakdown-multiflow-plan-then-implement.yaml"
)
# OpenStartup root: preflight/<this> → task/ → tools/ → resources/ → openteam/
# → test/ → OpenStartup/.
OPENSTARTUP_PATH = _HERE.parents[5]
# Templates dir colocated with the test resources (same as legacy smoke test).
TEMPLATES_DIR = _HERE.parents[1] / "task" / "configs" / "prompt_templates"
if not TEMPLATES_DIR.exists():
    # Legacy smoke test points templates_dir at OpenStartup's prompt_templates.
    TEMPLATES_DIR = (
        OPENSTARTUP_PATH
        / "src"
        / "openteam"
        / "server"
        / "resources"
        / "prompt_templates"
    )


def _load_topology(monkeypatch, tmp_path):
    """Bind required env vars + load + instantiate the YAML config.

    Mirrors the bootstrap done in `test_yaml_smoke_instantiate` so this
    preflight is self-contained.
    """
    monkeypatch.setenv("PROMPT_TEMPLATES_DIR", "prompt_templates")

    # Side-effect import to register Hydra targets (ClaudeCodeCLI, Dual, etc.)
    import agent_foundation.common.configs.registered_targets  # noqa: F401
    from rich_python_utils.config_utils import instantiate, load_config

    cfg = load_config(
        str(YAML_PATH),
        overrides={
            "_target_path": str(OPENSTARTUP_PATH),
            "templates_dir": str(TEMPLATES_DIR),
            "_params.workspace_root": str(tmp_path / "ws"),
        },
    )
    return instantiate(cfg)


def test_yaml_loads(tmp_path, monkeypatch):
    """Sanity: the YAML still parses + instantiates."""
    topology = _load_topology(monkeypatch, tmp_path)
    assert topology is not None
    # Outer Dual is the root.
    assert type(topology).__name__ == "DualInferencer"


def test_outer_workspace_has_no_retired_flag(tmp_path, monkeypatch):
    """The outer Dual's workspace must NOT carry the retired
    ``use_final_deliverables_folder`` attrib (Part 2 deleted it)."""
    topology = _load_topology(monkeypatch, tmp_path)

    ws = topology._workspace
    assert ws is not None, (
        "Outer Dual has no _workspace; expected an InferencerWorkspace "
        "constructed from the ``workspace:`` / ``workspace_root`` in the YAML."
    )
    assert not hasattr(ws, "use_final_deliverables_folder"), (
        "InferencerWorkspace.use_final_deliverables_folder is RETIRED (Part 2). "
        "The attrib should no longer exist on the workspace."
    )
    assert not hasattr(ws, "deliverables_dir"), (
        "InferencerWorkspace.deliverables_dir is RETIRED (Part 2). "
        "Callers use outputs_dir / output_path(...) instead."
    )


def test_outer_workspace_outputs_dir_resolves(tmp_path, monkeypatch):
    """Deliverables resolve straight to ``outputs/`` (no final_deliverables/)."""
    topology = _load_topology(monkeypatch, tmp_path)

    ws = topology._workspace
    outputs_dir = ws.outputs_dir
    assert outputs_dir is not None, (
        "outputs_dir is None; the workspace block was not actually "
        "instantiated as an InferencerWorkspace."
    )
    # Path convention: <root>/outputs (final_deliverables/ retired)
    assert (
        outputs_dir.endswith("outputs")
        or outputs_dir.endswith("outputs" + "\\")
        or outputs_dir.rstrip("/\\").endswith("outputs")
    ), f"outputs_dir={outputs_dir!r} does not end with the expected 'outputs' suffix."


def test_inferencer_workspace_class_is_used(tmp_path, monkeypatch):
    """Defensive: ensure the topology really uses InferencerWorkspace (not a
    surprise subclass), so the two-axis semantics described in the comments
    hold."""
    topology = _load_topology(monkeypatch, tmp_path)
    from agent_foundation.common.inferencers.inferencer_workspace import (
        InferencerWorkspace,
    )

    assert isinstance(topology._workspace, InferencerWorkspace)
