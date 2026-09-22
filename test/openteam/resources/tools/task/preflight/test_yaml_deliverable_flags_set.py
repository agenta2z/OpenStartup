"""Preflight tests for YAML config — deliverable flags are RETIRED.

Part 2 (two-axis contract) retired the ``final_deliverables/`` folder and the
four deliverable flags. ``outputs/`` IS the deliverable set now; promotion is
role-based via ``_symlink_child_output`` and does not depend on any per-node
flag. Consequently the configured topology
(``breakdown-multiflow-plan-then-implement.yaml``) must NOT set the retired
``output_is_deliverable`` / ``use_final_deliverables_folder`` keys anywhere.

This file used to assert those keys were PRESENT (cached-hennessy plan, Step 6);
that contract is now inverted — it guards against someone re-adding a retired
key (which would produce a silent "Removing YAML key" framework warning and
imply a mechanism that no longer exists).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml


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
OPENSTARTUP_PATH = _HERE.parents[5]
TEMPLATES_DIR = (
    OPENSTARTUP_PATH / "src" / "openteam" / "server" / "resources" / "prompt_templates"
)


def _load_raw_yaml():
    """Load the YAML with _import_ resolution (but without full instantiation).

    Uses load_config() so _import_ directives are resolved — the planner
    subtree (extracted to breakdown_multiflow_plan.yaml) is merged in.
    """
    import agent_foundation.common.configs.registered_targets  # noqa: F401
    from omegaconf import OmegaConf
    from rich_python_utils.config_utils import load_config

    cfg = load_config(
        str(YAML_PATH),
        overrides={
            "_target_path": str(OPENSTARTUP_PATH),
            "templates_dir": str(TEMPLATES_DIR),
            "_params.workspace_root": "/tmp/_test_deliverable_flags",
        },
    )
    return OmegaConf.to_container(cfg, resolve=True)


def _walk_for_key(node, key):
    """Yield every (path, value) where key appears in the nested config."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield (k, v)
            yield from _walk_for_key(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_for_key(item, key)


# -------------------------------------------------------------------------
# Sanity: file exists and parses
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_YD1_yaml_file_exists():
    """YD1: The configured topology YAML exists at the expected path."""
    assert YAML_PATH.is_file(), (
        f"Topology YAML missing: {YAML_PATH}. "
        "This is the contract anchor — moving it requires updating tests "
        "and any callers."
    )


@pytest.mark.preflight
def test_YD2_yaml_parses_as_valid_yaml():
    """YD2: The topology YAML is well-formed YAML."""
    cfg = _load_raw_yaml()
    assert isinstance(cfg, dict), "Top-level YAML must be a mapping"


# -------------------------------------------------------------------------
# Retired-flag absence (Part 2: the flags no longer exist)
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_YD3_no_output_is_deliverable_key_anywhere():
    """YD3: No inferencer in the YAML sets ``output_is_deliverable``.

    The attrib was deleted in Part 2 — deliverables live directly in
    ``outputs/`` and promotion is role-based (via ``_symlink_child_output``),
    not flag-driven. A lingering key would be silently dropped by the config
    framework and mislead readers into thinking the mechanism still exists.
    """
    cfg = _load_raw_yaml()
    matches = list(_walk_for_key(cfg, "output_is_deliverable"))
    assert not matches, (
        "`output_is_deliverable` is a RETIRED key (Part 2) and must not "
        "appear in the topology YAML. Remove it — deliverables now surface "
        f"from ``outputs/`` unconditionally. Found: {matches}"
    )


@pytest.mark.preflight
def test_YD4_no_use_final_deliverables_folder_key_anywhere():
    """YD4: No workspace block sets ``use_final_deliverables_folder``.

    The ``final_deliverables/`` subfolder was retired — deliverables land
    directly in ``outputs/``. The workspace attrib was deleted, so any
    lingering key here is a no-op that should be removed.
    """
    cfg = _load_raw_yaml()
    matches = list(_walk_for_key(cfg, "use_final_deliverables_folder"))
    assert not matches, (
        "`use_final_deliverables_folder` is a RETIRED workspace key (Part 2) "
        "and must not appear in the topology YAML. Remove it — ``outputs/`` "
        f"IS the deliverable set now. Found: {matches}"
    )
