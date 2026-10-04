"""OpenStartup drives conversational hosts (AgentFoundation's classic and
native orchestrators) only through their public host API.

An AST scan of the OpenStartup server source flags any access to a private
member (``_name``) of either orchestrator class — attribute syntax or a
``getattr``/``setattr``/``hasattr``/``delattr`` string — on an expression that
holds a host.
"""

from __future__ import annotations

import ast
import inspect
import sys
import textwrap
import unittest
from pathlib import Path

# Bootstrap sys.path
_HERE = Path(__file__).resolve()
_OPENSTARTUP = _HERE.parents[4]
_REPO_ROOT = _OPENSTARTUP.parent
for _dep in [
    _OPENSTARTUP / "src",
    _REPO_ROOT / "AgentFoundation" / "src",
    _REPO_ROOT / "RichPythonUtils" / "src",
]:
    p = str(_dep)
    if p not in sys.path:
        sys.path.insert(0, p)

import openteam.server as openteam_server
from agent_foundation.common.inferencers.agentic_inferencers.conversational.conversational_inferencer import (
    ConversationalInferencer,
)
from agent_foundation.common.inferencers.agentic_inferencers.conversational_native import (
    NativeConversationalInferencer,
)

# Names OpenStartup gives a host.
_HOST_NAMES = frozenset(
    {"inferencer", "conv_inferencer", "ci", "native", "host", "inf", "_inf"}
)
# Calls that return a host.
_HOST_FACTORIES = frozenset(
    {
        "_get_session_inferencer",
        "_build_inferencer",
        "_build_native",
        "_wrap_in_conversational",
        "build_ci_from_config",
        "build_native_from_config",
    }
)
# The dispatcher's back-reference to its host.
_HOST_BACKREF = "_inferencer"
_ATTR_BUILTINS = frozenset({"getattr", "setattr", "hasattr", "delattr"})


def _private(name: str) -> bool:
    return name.startswith("_") and not name.startswith("__")


def _host_private_members() -> frozenset[str]:
    """Private members of both orchestrators: class attributes and methods,
    attrs fields, and every ``self._name`` their AgentFoundation classes use."""
    names: set[str] = set()
    for host in (ConversationalInferencer, NativeConversationalInferencer):
        for cls in host.__mro__:
            if not cls.__module__.startswith("agent_foundation"):
                continue
            names.update(n for n in vars(cls) if _private(n))
            names.update(
                f.name for f in getattr(cls, "__attrs_attrs__", ()) if _private(f.name)
            )
            tree = ast.parse(textwrap.dedent(inspect.getsource(cls)))
            names.update(
                node.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and _private(node.attr)
            )
    return frozenset(names)


def _call_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _string_arg(call: ast.Call, index: int) -> str:
    if len(call.args) > index:
        arg = call.args[index]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return ""


def _is_backref(node: ast.AST) -> bool:
    """``x._inferencer`` or ``getattr(x, "_inferencer", ...)``."""
    if isinstance(node, ast.Attribute):
        return node.attr == _HOST_BACKREF
    return _call_name(node) == "getattr" and _string_arg(node, 1) == _HOST_BACKREF


def _assigned_hosts(tree: ast.AST) -> set[str]:
    """Names the module binds to a host (from a host factory or the
    dispatcher's back-reference)."""
    names = set(_HOST_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            if _call_name(node.value) in _HOST_FACTORIES or _is_backref(node.value):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                names.update(t.id for t in targets if isinstance(t, ast.Name))
    return names


def _is_host(node: ast.AST, hosts: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in hosts
    if isinstance(node, ast.Subscript):  # self._inferencers[session_id]
        value = node.value
        return isinstance(value, ast.Attribute) and value.attr == "_inferencers"
    return _call_name(node) in _HOST_FACTORIES or _is_backref(node)


def private_host_accesses(source: str, private: frozenset[str]) -> list[str]:
    """``line: expression`` for each private host member ``source`` touches."""
    tree = ast.parse(source)
    hosts = _assigned_hosts(tree)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            receiver, name = node.value, node.attr
        elif isinstance(node, ast.Call) and _call_name(node) in _ATTR_BUILTINS:
            if not node.args:
                continue
            receiver, name = node.args[0], _string_arg(node, 1)
        else:
            continue
        if name in private and name != _HOST_BACKREF and _is_host(receiver, hosts):
            found.append(f"{node.lineno}: {ast.unparse(node)}")
    return found


class HostPublicApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private = _host_private_members()

    def test_openstartup_uses_no_private_host_member(self) -> None:
        root = Path(openteam_server.__file__).parent
        violations = []
        for path in sorted(root.rglob("*.py")):
            for hit in private_host_accesses(
                path.read_text(encoding="utf-8"), self.private
            ):
                violations.append(f"{path.relative_to(root)}:{hit}")
        self.assertEqual(violations, [])

    def test_the_scan_flags_private_host_members(self) -> None:
        source = textwrap.dedent(
            """
            conv_inferencer._suspended_sops = []
            ci._check_phase_completion()
            getattr(native, "_tool_dispatcher", None)
            self._get_session_inferencer(sid)._tool_dispatcher
            self._inferencers[sid]._messages
            dispatcher._inferencer._suspended_sops
            built = build_native_from_config(path)
            built._tool_dispatcher = None
            """
        )
        self.assertEqual(len(private_host_accesses(source, self.private)), 7)

    def test_the_scan_ignores_public_members_and_other_objects(self) -> None:
        source = textwrap.dedent(
            """
            conv_inferencer.suspended_sops = []
            ci.check_phase_completion()
            native.tool_dispatcher = dispatcher
            dispatcher._inferencer = native
            dispatcher._interactive = interactive
            self._messages = []
            interactive._last_prompt_data = {}
            ci._not_a_host_member
            """
        )
        self.assertEqual(private_host_accesses(source, self.private), [])

    def test_known_private_members_are_collected(self) -> None:
        for name in (
            "_suspended_sops",
            "_tool_dispatcher",
            "_check_phase_completion",
            "_messages",
        ):
            self.assertIn(name, self.private)


if __name__ == "__main__":
    unittest.main()
