"""Integration tests for the prompt-template split (Task 8).

Verifies that the 2-root TemplateManager wiring (OpenStartup first,
AgentFoundation second) correctly:
  - Resolves wrapper templates from AgentFoundation with variables from
    OpenStartup's ``_variables/`` (fallback path).
  - Resolves specialized variable variants (e.g., ``role_setup_report``)
    when the wrapper template comes from AgentFoundation.
  - Returns the OpenStartup (higher-priority) version when a template
    exists in BOTH roots.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rich_python_utils.string_utils.formatting.template_manager import (
    TemplateManager,
)
from rich_python_utils.string_utils.formatting.template_manager.template_manager import (
    _OriginTaggedStr,
)

# ---------------------------------------------------------------------------
# Resolve the two template roots from installed packages
# ---------------------------------------------------------------------------

import agent_foundation.resources as _af_res
import openteam.server.resources as _os_res

OS_TEMPLATES_ROOT = str(Path(_os_res.__file__).parent / "prompt_templates")
AF_TEMPLATES_ROOT = str(Path(_af_res.__file__).parent / "prompt_templates")


def _make_2root_tm(**kwargs) -> TemplateManager:
    """Construct a TemplateManager with the canonical 2-root list.

    OpenStartup first (override + all ``_variables/``),
    AgentFoundation second (fallback wrappers only, no ``_variables/``).
    """
    defaults = dict(
        templates=[OS_TEMPLATES_ROOT, AF_TEMPLATES_ROOT],
        active_template_type="main",
        predefined_variables=True,
        default_template_key="initial",
        enable_templated_feed=True,
    )
    defaults.update(kwargs)
    return TemplateManager(**defaults)


# ===========================================================================
# 8.1 — Wrapper template in AgentFoundation resolves variables from
#        OpenStartup's _variables/ (fallback path)
# ===========================================================================


class TestWrapperResolvesVariablesFromOpenStartup:
    """AgentFoundation has NO ``_variables/``, so ``_variable_loader`` falls
    back to OpenStartup's loader.  Wrapper templates that reference
    ``{{ task_preamble }}`` or ``{{ task_instructions }}`` must still render
    with real variable content."""

    def test_plan_initial_resolves_task_preamble(self):
        """plan/main/initial.jinja2 lives in AgentFoundation.
        Its ``{{ task_preamble }}`` must resolve from OpenStartup's
        ``plan/main/_variables/task_preamble/default.jinja2``."""
        tm = _make_2root_tm()

        # The raw template should come from AgentFoundation (it was moved there)
        raw = tm.get_raw_template(
            "initial",
            active_template_root_space="plan",
            active_template_type="main",
        )
        assert raw is not None, "plan/main/initial template not found"
        # Verify it's the wrapper (contains the characteristic markers)
        assert "task_preamble" in raw, "wrapper template must reference task_preamble"

        # Verify the origin is AgentFoundation (template was moved there)
        origin = getattr(raw, "_origin_root", None)
        assert origin == AF_TEMPLATES_ROOT, (
            f"plan/main/initial should come from AgentFoundation; got origin={origin!r}"
        )

    def test_plan_initial_variable_resolution_produces_content(self):
        """Render plan/main/initial with the 2-root TM and verify that
        predefined variables (task_preamble, task_instructions) are resolved
        to non-empty content from OpenStartup's _variables/."""
        tm = _make_2root_tm()

        # load_variable should find the default task_preamble from OpenStartup
        preamble = tm.load_variable(
            "task_preamble", "default", root_space="plan"
        )
        assert preamble is not None, (
            "task_preamble/default should resolve from OpenStartup's _variables/"
        )
        assert len(preamble.strip()) > 0, "task_preamble/default should not be empty"

    def test_implementation_initial_resolves_variables(self):
        """implementation/main/initial.jinja2 lives in AgentFoundation.
        Variables must resolve from OpenStartup."""
        tm = _make_2root_tm()

        raw = tm.get_raw_template(
            "initial",
            active_template_root_space="implementation",
            active_template_type="main",
        )
        assert raw is not None
        origin = getattr(raw, "_origin_root", None)
        assert origin == AF_TEMPLATES_ROOT, (
            f"implementation/main/initial should come from AgentFoundation; "
            f"got origin={origin!r}"
        )

        # Verify variable resolution works
        preamble = tm.load_variable(
            "task_preamble", "default", root_space="implementation"
        )
        assert preamble is not None, (
            "implementation task_preamble/default should resolve from OpenStartup"
        )

    def test_af_root_has_no_variable_loader(self):
        """AgentFoundation root must NOT have its own VariableLoader
        (no ``_variables/`` directory), confirming the fallback path."""
        tm = _make_2root_tm()
        assert AF_TEMPLATES_ROOT not in tm._variable_loaders_by_root, (
            "AgentFoundation root should NOT have a VariableLoader "
            "(it has no _variables/ directory)"
        )
        # OpenStartup root SHOULD have a loader
        assert OS_TEMPLATES_ROOT in tm._variable_loaders_by_root, (
            "OpenStartup root should have a VariableLoader"
        )

    def test_variable_loader_fallback_is_openstartup(self):
        """The backward-compat ``_variable_loader`` should point to
        OpenStartup's loader (the first root with ``_variables/``)."""
        tm = _make_2root_tm()
        assert tm._variable_loader is not None, (
            "_variable_loader should be set (backward compat)"
        )
        assert tm._variable_loader is tm._variable_loaders_by_root[OS_TEMPLATES_ROOT], (
            "_variable_loader should be OpenStartup's loader"
        )


# ===========================================================================
# 8.2 — Specialized variable variant resolved for AgentFoundation templates
# ===========================================================================


class TestSpecializedVariantResolution:
    """Specialized variable variants (e.g., ``role_setup_report``,
    ``aggregation``) must resolve correctly even when the wrapper template
    comes from AgentFoundation."""

    def test_role_setup_report_task_instructions(self):
        """``task_instructions/role_setup_report`` variant must resolve
        from OpenStartup's ``plan/main/_variables/``."""
        tm = _make_2root_tm()

        content = tm.load_variable(
            "task_instructions", "role_setup_report", root_space="plan"
        )
        assert content is not None, (
            "task_instructions/role_setup_report should resolve from OpenStartup"
        )
        # The role_setup_report variant has characteristic content
        assert "Role Setup Report" in content, (
            "role_setup_report variant should contain 'Role Setup Report'"
        )

    def test_aggregation_task_preamble(self):
        """``task_preamble/aggregation`` variant must resolve from
        OpenStartup's ``plan/main/_variables/``."""
        tm = _make_2root_tm()

        content = tm.load_variable(
            "task_preamble", "aggregation", root_space="plan"
        )
        assert content is not None, (
            "task_preamble/aggregation should resolve from OpenStartup"
        )

    def test_skill_tool_creation_task_instructions(self):
        """``task_instructions/skill_tool_creation`` variant must resolve
        from OpenStartup's ``plan/main/_variables/``."""
        tm = _make_2root_tm()

        content = tm.load_variable(
            "task_instructions", "skill_tool_creation", root_space="plan"
        )
        assert content is not None, (
            "task_instructions/skill_tool_creation should resolve from OpenStartup"
        )

    def test_implementation_aggregation_task_instructions(self):
        """``task_instructions/aggregation`` variant must resolve from
        OpenStartup's ``implementation/main/_variables/``."""
        tm = _make_2root_tm()

        content = tm.load_variable(
            "task_instructions", "aggregation", root_space="implementation"
        )
        assert content is not None, (
            "implementation task_instructions/aggregation should resolve"
        )
        assert "aggregat" in content.lower(), (
            "aggregation variant should contain aggregation-related content"
        )


# ===========================================================================
# 8.3 — Template in BOTH roots returns OpenStartup (higher-priority) version
# ===========================================================================


class TestHigherPriorityRootWins:
    """When a template exists in both OpenStartup and AgentFoundation,
    the OpenStartup version (first in the list) must win."""

    def test_override_with_synthetic_duplicate(self, tmp_path):
        """Create a synthetic scenario where both roots have the same
        template key, and verify the first root wins."""
        # Create two roots with the same template
        override = tmp_path / "override"
        base = tmp_path / "base"

        # Write the same template key in both roots
        (override / "plan" / "main").mkdir(parents=True)
        (override / "plan" / "main" / "initial.jinja2").write_text(
            "OVERRIDE: {{ input }}", encoding="utf-8"
        )
        (base / "plan" / "main").mkdir(parents=True)
        (base / "plan" / "main" / "initial.jinja2").write_text(
            "BASE: {{ input }}", encoding="utf-8"
        )

        tm = TemplateManager(
            templates=[str(override), str(base)],
            active_template_type="main",
            default_template_key="initial",
        )

        raw = tm.get_raw_template(
            "initial",
            active_template_root_space="plan",
            active_template_type="main",
        )
        assert raw is not None
        assert "OVERRIDE" in raw, (
            "First root (override) should win over second root (base)"
        )
        assert "BASE" not in raw

    def test_real_roots_plan_initial_comes_from_af(self):
        """With the real 2-root setup, plan/main/initial.jinja2 should come
        from AgentFoundation (since it was MOVED there — it no longer exists
        in OpenStartup)."""
        tm = _make_2root_tm()

        raw = tm.get_raw_template(
            "initial",
            active_template_root_space="plan",
            active_template_type="main",
        )
        origin = getattr(raw, "_origin_root", None)
        # After the split, the wrapper template only exists in AgentFoundation
        assert origin == AF_TEMPLATES_ROOT, (
            f"plan/main/initial should come from AgentFoundation after the split; "
            f"got origin={origin!r}"
        )

    def test_variables_yaml_persona_comes_from_openstartup(self):
        """The ``.variables.yaml`` persona (employee) should come from
        OpenStartup (it was NOT moved to AgentFoundation)."""
        tm = _make_2root_tm()

        # The .variables.yaml sidecar is loaded by the VariableLoader
        # for the OpenStartup root. Verify the employee persona is available.
        loader = tm._variable_loaders_by_root.get(OS_TEMPLATES_ROOT)
        assert loader is not None

        # The YAML sidecar variables should include the employee persona
        yaml_vars = loader.get_all_variables(
            variable_root_space="plan",
            variable_type="main",
        )
        assert "employee" in yaml_vars, (
            ".variables.yaml persona (employee) should be available from OpenStartup"
        )
        employee = yaml_vars["employee"]
        assert "name" in employee, "employee should have a name field"
        assert employee["name"] == "OpenStartup", (
            "employee.name should be 'OpenStartup' from the .variables.yaml"
        )
