"""Regression: the agent may emit an action tool's `arguments` as a CLI-style
string instead of a dict.

Bug: the orchestrator inside the model_optimization SOP emitted
``{"name": "understand_codebase", "arguments": "/path --template-version modeling"}``
(a CLI string, mirroring the tool's rendered usage examples). The dispatcher
passed it straight to ``_dispatch_as_task``, which did ``arguments.get(...)`` →
``'str' object has no attribute 'get'``. The async task died in the background
(only logged), so NO task card / task panel ever appeared in the UI.

Fix: ``cli_args.coerce_tool_arguments`` normalizes any shape (dict / str / list)
into the canonical underscored dict at the single dispatch boundary
(``ToolDispatcher.__call__``), reusing the same parser the user slash-command
path uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from openteam.server.services.cli_args import (  # noqa: E402
    bool_flags_for_tool,
    coerce_tool_arguments,
    parse_cli_args,
)


class _Param:
    def __init__(self, name, ptype):
        self.name = name
        self.type = ptype


class _ToolDef:
    """Minimal stand-in for ToolDefinition with a parameters list."""

    def __init__(self, parameters):
        self.parameters = parameters


# understand_codebase: positional `target` + value flags + bool flags
_UC = _ToolDef([
    _Param("target", "path"),
    _Param("--docs-only", "flag"),
    _Param("--investigation-only", "flag"),
])


class TestParseCliArgs:
    def test_positional_becomes_request(self):
        assert parse_cli_args("/repo/model.py") == {"request": "/repo/model.py"}

    def test_value_flag_normalized_to_underscore(self):
        out = parse_cli_args("/repo --template-version modeling")
        assert out == {"request": "/repo", "template_version": "modeling"}

    def test_bare_bool_flag(self):
        out = parse_cli_args("/repo --docs-only", bool_flags={"docs_only"})
        assert out == {"request": "/repo", "docs_only": True}

    def test_quoted_request(self):
        out = parse_cli_args('--plan "build auth system"', bool_flags={"plan"})
        assert out == {"plan": True, "request": "build auth system"}

    def test_repeatable_override_accumulates(self):
        out = parse_cli_args("--override a=1 --override b=2")
        assert out["override"] == ["a=1", "b=2"]


class TestBoolFlagsForTool:
    def test_derives_flag_params(self):
        assert bool_flags_for_tool(_UC) == frozenset({"docs_only", "investigation_only"})

    def test_handles_none_and_empty(self):
        assert bool_flags_for_tool(None) == frozenset()
        assert bool_flags_for_tool(_ToolDef([])) == frozenset()


class TestCoerceToolArguments:
    def test_the_exact_bug_string(self):
        """The exact arguments string the LLM emitted must coerce to a dict."""
        s = "/Users/zgchen/PycharmProjects/MyProjects/generative_recommenders --template-version modeling"
        out = coerce_tool_arguments(s, _UC)
        assert isinstance(out, dict)
        assert out["request"].endswith("generative_recommenders")
        assert out["template_version"] == "modeling"
        # The line that previously crashed (_dispatch_as_task request_label):
        label = out.get("role_description") or out.get("request") or "understand_codebase"
        assert label.endswith("generative_recommenders")

    def test_dict_passes_through_unchanged(self):
        d = {"target": "/x", "template_version": "modeling"}
        assert coerce_tool_arguments(d, _UC) is d

    def test_list_wrapped_string(self):
        out = coerce_tool_arguments(["/repo --docs-only"], _UC)
        assert out == {"request": "/repo", "docs_only": True}

    def test_none_and_junk(self):
        assert coerce_tool_arguments(None, _UC) == {}
        assert coerce_tool_arguments(123, _UC) == {}
        assert coerce_tool_arguments([], _UC) == {}

    def test_bool_flag_not_swallowing_next_token(self):
        """With tool-derived bool flags, a bare flag must not eat the positional."""
        out = coerce_tool_arguments("--docs-only /repo", _UC)
        assert out == {"docs_only": True, "request": "/repo"}
