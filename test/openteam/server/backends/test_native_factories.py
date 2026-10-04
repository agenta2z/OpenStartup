"""Native backends (AgentFoundation's NativeConversationalInferencer).

Covers registration + availability probes and the factory wiring: shared
host wiring with the classic stack, the session-state record store, the
service-owned runtime manager and the resume/rewind policies. Nothing here
starts a vendor process — a vendor session opens only on the first turn.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
from agent_foundation.common.inferencers.agentic_inferencers.conversational_native import (
    NativeConversationalInferencer,
    NativeRuntimeManager,
    NativeSessionRecord,
)
from openteam.server.backends import factories as factories_mod, get_registry
from openteam.server.backends.registry import BackendBuildContext
from openteam.server.services.native_session_store import (
    NATIVE_SESSION_DIR,
    SESSION_KEY,
    SessionStoreRecordAdapter,
)
from openteam.server.services.session_store import SessionStore

_NATIVE_NAMES = (
    "native_claude_sdk",
    "native_claude_cli",
    "native_devmate",
    "native_codex",
)
_ALL_NATIVE = _NATIVE_NAMES + ("native_metamate",)
_TEMPLATES_DIR = (
    Path(openteam_server.__file__).parent / "resources" / "prompt_templates"
)


def _context(**overrides) -> tuple[BackendBuildContext, SessionStore, str]:
    tmp = Path(tempfile.mkdtemp(prefix="os_native_factory_"))
    store = SessionStore(tmp, resume_server="new")
    sid = store.create_session("native")["id"]
    fields = {
        "templates_dir": _TEMPLATES_DIR,
        "working_dir": str(tmp / "work"),
        "cache_dir": str(tmp / "cache"),
        "session_store": store,
        "session_id": sid,
        "native_runtime": NativeRuntimeManager(),
    }
    fields.update(overrides)
    return BackendBuildContext(**fields), store, sid


class NativeRegistrationTests(unittest.TestCase):
    def test_native_backends_are_registered_as_native(self):
        backends = get_registry().list_backends()
        for name in _ALL_NATIVE:
            with self.subTest(name=name):
                self.assertTrue(backends[name].native)
        for name in ("mock", "rovodev", "claude_cli"):
            self.assertFalse(backends[name].native)

    def test_unavailable_without_the_vendor_binary(self):
        descriptor = get_registry().get_descriptor("native_codex")
        with patch.object(factories_mod.shutil, "which", return_value=None):
            self.assertFalse(descriptor.is_available())
            self.assertIn("`codex` on PATH", descriptor.status_message())

    def test_unavailable_without_a_required_python_package(self):
        descriptor = get_registry().get_descriptor("native_claude_sdk")
        with (
            patch.object(factories_mod.shutil, "which", return_value="/bin/claude"),
            patch.object(factories_mod.importlib.util, "find_spec", return_value=None),
        ):
            self.assertFalse(descriptor.is_available())
            self.assertIn("claude_agent_sdk", descriptor.status_message())

    def test_available_reports_the_binary(self):
        descriptor = get_registry().get_descriptor("native_codex")
        with (
            patch.object(factories_mod.shutil, "which", return_value="/bin/codex"),
            patch.object(
                factories_mod.importlib.util, "find_spec", return_value=object()
            ),
        ):
            self.assertTrue(descriptor.is_available())
            self.assertEqual(descriptor.status_message(), "codex found at /bin/codex")

    def test_metamate_needs_the_buck_only_sdk(self):
        descriptor = get_registry().get_descriptor("native_metamate")
        with patch.object(
            factories_mod.importlib.util, "find_spec", side_effect=ModuleNotFoundError
        ):
            self.assertFalse(descriptor.is_available())
            self.assertIn("msl.metamate.sdk", descriptor.status_message())
        with patch.object(
            factories_mod.importlib.util, "find_spec", return_value=object()
        ):
            self.assertTrue(descriptor.is_available())
            self.assertEqual(descriptor.status_message(), "Available")

    def _metamate_without(self, module: str) -> tuple[bool, str]:
        descriptor = get_registry().get_descriptor("native_metamate")
        with patch.object(
            factories_mod.importlib.util,
            "find_spec",
            side_effect=lambda name, *_a: None if name == module else object(),
        ):
            return descriptor.is_available(), descriptor.status_message()

    def test_metamate_without_the_sdk_names_the_server_target(self):
        available, message = self._metamate_without("msl.metamate.sdk")

        self.assertFalse(available)
        self.assertEqual(
            message,
            "Unavailable — missing Python package `msl.metamate.sdk`; run the "
            "server from the `//_tony_dev/CoreProjects/OpenStartup/src:server` "
            "Buck target, which carries both: buck2 run @fbcode//mode/dev "
            "//_tony_dev/CoreProjects/OpenStartup/src:server -- --real-sessions "
            "<dir> --llm-backend native_metamate",
        )

    def test_metamate_needs_agent_foundations_native_metamate_backend(self):
        module = (
            "agent_foundation.common.inferencers.agentic_inferencers."
            "conversational_native.session.metamate"
        )

        available, message = self._metamate_without(module)

        self.assertFalse(available)
        self.assertTrue(
            message.startswith(
                "Unavailable — missing AgentFoundation's native Metamate backend "
                f"(`{module}`); run the server from the "
                "`//_tony_dev/CoreProjects/OpenStartup/src:server` Buck target"
            ),
            message,
        )
        self.assertNotIn("msl.metamate.sdk", message)

    def test_devmate_needs_cat_credentials(self):
        descriptor = get_registry().get_descriptor("native_devmate")
        with (
            patch.object(factories_mod.shutil, "which", return_value="/bin/dm"),
            patch.object(
                factories_mod.importlib.util, "find_spec", return_value=object()
            ),
            patch(
                "agent_foundation.common.inferencers.agentic_inferencers."
                "conversational_native.session.devmate_dm.resolve_cats_file",
                return_value=None,
            ),
        ):
            self.assertFalse(descriptor.is_available())
            self.assertIn("DM_CATS_FILE", descriptor.status_message())
        with (
            patch.object(factories_mod.shutil, "which", return_value="/bin/dm"),
            patch.object(
                factories_mod.importlib.util, "find_spec", return_value=object()
            ),
            patch(
                "agent_foundation.common.inferencers.agentic_inferencers."
                "conversational_native.session.devmate_dm.resolve_cats_file",
                return_value="/tmp/cats.json",
            ),
        ):
            self.assertTrue(descriptor.is_available())


class NativeFactoryTests(unittest.TestCase):
    def test_builds_a_native_inferencer_per_backend_kind(self):
        ctx, _store, _sid = _context()
        kinds = {}
        for name in _ALL_NATIVE:
            native = get_registry().create(name, ctx)
            self.assertIsInstance(native, NativeConversationalInferencer)
            kinds[name] = native.backend.kind
        self.assertEqual(
            kinds,
            {
                "native_claude_sdk": "claude_sdk",
                "native_claude_cli": "claude_cli",
                "native_devmate": "devmate_dm",
                "native_codex": "codex_cli",
                "native_metamate": "metamate",
            },
        )

    def test_session_wiring_and_policies(self):
        ctx, store, sid = _context()
        native = get_registry().create("native_claude_sdk", ctx)
        self.assertEqual(native.conversation_key, sid)
        self.assertIsInstance(native.record_store, SessionStoreRecordAdapter)
        self.assertIs(native.runtime_manager, ctx.native_runtime)
        self.assertEqual(native.backend.cwd, ctx.working_dir)
        self.assertTrue(Path(ctx.working_dir).is_dir())
        self.assertEqual(native.backend.model, "opus[1m]")
        self.assertEqual(
            native.native_session_dir,
            str(store.get_session_dir(sid) / NATIVE_SESSION_DIR),
        )
        self.assertTrue(native.rewind_on_repeat_turn)
        self.assertEqual(native.on_rewind_unsupported, "recap")
        self.assertTrue(native.host_manages_async_results)
        self.assertFalse(native.supports_round_resume)
        self.assertTrue(native.supports_rewind)

    def test_dispatcher_is_the_tool_executor_with_a_back_reference(self):
        ctx, _store, _sid = _context()
        native = get_registry().create("native_claude_sdk", ctx)
        dispatcher = native.tool_dispatcher
        self.assertIs(native.tool_executor, dispatcher)
        self.assertIs(native.dashboard_coordinator.tool_dispatcher, dispatcher)
        self.assertIs(dispatcher._inferencer, native)

    def test_model_override(self):
        ctx, _store, _sid = _context(model_name="sonnet")
        self.assertEqual(
            get_registry().create("native_claude_cli", ctx).backend.model, "sonnet"
        )
        ctx, _store, _sid = _context()
        self.assertEqual(get_registry().create("native_codex", ctx).backend.model, "")

    def test_exposes_sop_widget_and_action_tools(self):
        ctx, _store, _sid = _context()
        names = {
            s.name
            for s in get_registry().create("native_claude_sdk", ctx).bridge.manifest()
        }
        for name in (
            "enter_sop",
            "resume_sop",
            "sop_status",
            "clarification",
            "single_choice",
            "task",
        ):
            self.assertIn(name, names)
        for name in ("sop", "view", "knowledge", "experiment_hub"):  # agent-disabled
            self.assertNotIn(name, names)

    def test_widget_tools_survive_an_action_allowlist(self):
        ctx, _store, _sid = _context()

        def only_task(registry, _renderer):
            return {k: v for k, v in registry.items() if k == "task"}

        with patch.object(
            factories_mod, "_filter_tools_by_config", side_effect=only_task
        ):
            native = get_registry().create("native_claude_sdk", ctx)
        names = {s.name for s in native.bridge.manifest()}
        self.assertIn("task", names)
        self.assertIn("clarification", names)
        self.assertNotIn("research_propose", names)

    def test_restores_the_persisted_sop_state(self):
        ctx, store, sid = _context()
        seed = get_registry().create("native_claude_sdk", ctx)
        seed.sop_controller.cmd_sop("model_optimization")
        store.update_session(sid, {"sop_state": seed.sop_state.to_dict()})
        native = get_registry().create("native_claude_sdk", ctx)
        self.assertEqual(native.sop_state.sop_name, "model_optimization")
        self.assertIsNotNone(native.sop_state.sop)

    def test_restores_the_persisted_suspended_sops(self):
        ctx, store, sid = _context()
        seed = get_registry().create("native_claude_sdk", ctx)
        seed.sop_controller.cmd_sop("model_optimization")
        store.update_session(sid, {"suspended_sops": [seed.sop_state.to_dict()]})
        native = get_registry().create("native_claude_sdk", ctx)
        self.assertIsNone(native.sop_state)
        [suspended] = native.suspended_sops
        self.assertEqual(suspended.sop_name, "model_optimization")
        self.assertIsNotNone(suspended.sop)

    def test_without_a_session_uses_private_defaults(self):
        tmp = Path(tempfile.mkdtemp(prefix="os_native_factory_"))
        ctx = BackendBuildContext(templates_dir=_TEMPLATES_DIR, working_dir=str(tmp))
        native = get_registry().create("native_claude_sdk", ctx)
        self.assertNotIsInstance(native.record_store, SessionStoreRecordAdapter)
        self.assertIsNone(native.native_session_dir)


class SessionStoreRecordAdapterTests(unittest.TestCase):
    def test_record_round_trips_through_the_session_state(self):
        _ctx, store, sid = _context()
        adapter = SessionStoreRecordAdapter(store, sid)
        record = NativeSessionRecord(conversation_key=sid, vendor_session_id="v1")
        adapter.save(record)
        self.assertEqual(store.get_session(sid)[SESSION_KEY]["vendor_session_id"], "v1")
        self.assertEqual(adapter.load(sid).vendor_session_id, "v1")

    def test_a_record_of_another_conversation_is_ignored(self):
        _ctx, store, sid = _context()
        store.update_session(sid, {SESSION_KEY: {"conversation_key": "other"}})
        self.assertIsNone(SessionStoreRecordAdapter(store, sid).load(sid))


if __name__ == "__main__":
    unittest.main()
