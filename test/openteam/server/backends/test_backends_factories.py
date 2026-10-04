"""Factory smoke tests — mostly contract-level, mock the underlying CLIs.

We avoid spawning real claude/acli processes — testing here is about the
factory wiring, not the inferencer's runtime.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import time
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

from openteam.server.backends import factories as factories_mod
from openteam.server.backends.registry import BackendBuildContext


def _real_templates_dir() -> Path:
    """Use the actual templates dir so JinjaPromptRenderer wiring works."""
    return (
        _OPENSTARTUP / "src" / "openteam" / "server" / "resources" / "prompt_templates"
    )


class MockGuardTests(unittest.TestCase):
    def test_mock_factory_raises_if_invoked(self):
        """The mock entry exists for descriptor listing but must never be invoked."""
        ctx = BackendBuildContext(templates_dir=Path("/tmp"), working_dir="/tmp")
        with self.assertRaises(RuntimeError) as cm:
            factories_mod._mock_guard_factory(ctx)
        self.assertIn("mock is service-handled", str(cm.exception))


class RovodevModelWarningTests(unittest.TestCase):
    def setUp(self):
        # Reset the module-level "warned once" flag between tests.
        factories_mod._rovodev_model_warning_logged = False

    def test_rovodev_factory_logs_when_model_provided(self):
        """rovodev has no model_name attr — operator should know it's a no-op."""
        ctx = BackendBuildContext(
            templates_dir=_real_templates_dir(),
            working_dir=str(Path.cwd()),
            model_name="opus[1m]",
        )
        # Mock RovoDevCliInferencer + the conversational wrap so we don't spawn acli.
        with (
            patch.object(
                factories_mod, "_wrap_in_conversational", return_value="WRAPPED"
            ),
            patch(
                "agent_foundation.common.inferencers.agentic_inferencers.external.rovodev.RovoDevCliInferencer"
            ) as fake_base,
        ):
            fake_base.return_value.acli_path = "/fake/acli"
            with self.assertLogs(factories_mod.logger, level="INFO") as cap:
                result = factories_mod._rovodev_factory(ctx)
        self.assertEqual(result, "WRAPPED")
        # First call emits the warning; second call should NOT (warned-once guard).
        self.assertTrue(any("ignores model_name" in m for m in cap.output))

        with (
            patch.object(
                factories_mod, "_wrap_in_conversational", return_value="WRAPPED"
            ),
            patch(
                "agent_foundation.common.inferencers.agentic_inferencers.external.rovodev.RovoDevCliInferencer"
            ) as fake_base,
        ):
            fake_base.return_value.acli_path = "/fake/acli"
            with self.assertLogs(factories_mod.logger, level="INFO") as cap2:
                factories_mod._rovodev_factory(ctx)
        # Second call: only the "RovoDev initialized" log, no "ignores model_name".
        self.assertFalse(any("ignores model_name" in m for m in cap2.output))


class ClaudeCliFactoryTests(unittest.TestCase):
    def test_claude_cli_factory_constructs_inferencer(self):
        """Factory wires ClaudeCodeCliInferencer with the expected kwargs."""
        ctx = BackendBuildContext(
            templates_dir=_real_templates_dir(),
            working_dir=str(Path.cwd()),
            cache_dir="/tmp/cache",
            model_name="haiku",
        )
        with (
            patch.object(
                factories_mod, "_wrap_in_conversational", return_value="WRAPPED"
            ),
            patch(
                "agent_foundation.common.inferencers.agentic_inferencers.external."
                "claude_code.claude_code_cli_inferencer.ClaudeCodeCliInferencer"
            ) as fake_base,
        ):
            fake_base.return_value.model_name = "haiku"
            result = factories_mod._claude_cli_factory(ctx)
        self.assertEqual(result, "WRAPPED")
        kwargs = fake_base.call_args.kwargs
        self.assertEqual(kwargs["target_path"], str(Path.cwd()))
        self.assertEqual(kwargs["model_name"], "haiku")
        self.assertEqual(kwargs["idle_timeout_seconds"], 1800)
        self.assertEqual(kwargs["permission_mode"], "bypassPermissions")
        self.assertEqual(kwargs["cache_folder"], "/tmp/cache")
        self.assertEqual(kwargs["concurrency_pool"], "openstartup_chat")
        self.assertEqual(kwargs["concurrency_pool_cap"], 2)

    def test_claude_cli_factory_default_model(self):
        """When ctx.model_name is None, falls back to the descriptor default 'opus[1m]'."""
        ctx = BackendBuildContext(
            templates_dir=_real_templates_dir(),
            working_dir=str(Path.cwd()),
        )
        with (
            patch.object(factories_mod, "_wrap_in_conversational", return_value="W"),
            patch(
                "agent_foundation.common.inferencers.agentic_inferencers.external."
                "claude_code.claude_code_cli_inferencer.ClaudeCodeCliInferencer"
            ) as fake_base,
        ):
            factories_mod._claude_cli_factory(ctx)
        self.assertEqual(fake_base.call_args.kwargs["model_name"], "opus[1m]")


_STAND_IN_CLAUDE = r"""
import json, sys, time

prompt = sys.stdin.read()
with open(__LOG__, "a") as f:
    f.write(prompt.replace("\n", " ") + "\n")
while "hold" in prompt:
    print(json.dumps({"type": "stream_event", "event": {"type": "ping"}}), flush=True)
    time.sleep(0.05)
reply = "reply to " + prompt.strip()
delta = {"type": "text_delta", "text": reply}
print(json.dumps({"type": "stream_event",
                  "event": {"type": "content_block_delta", "delta": delta}}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "result": reply, "session_id": "sess-1"}))
"""


class ClaudeCliChatCapacityTests(unittest.TestCase):
    """The classic chat leaf never waits for claude slots held by background
    runs: their leaves fill the default pool (four processes, each holding its
    slot until it exits) and the chat reply still comes back at once.

    A stand-in ``claude`` streams until cancelled when its prompt says ``hold``
    and answers any other prompt immediately."""

    def test_a_chat_reply_runs_while_background_runs_fill_the_default_pool(self):
        from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code.claude_code_cli_inferencer import (
            ClaudeCodeCliInferencer,
        )

        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            started = tmp / "started.log"
            script = tmp / "claude.py"
            script.write_text(_STAND_IN_CLAUDE.replace("__LOG__", repr(str(started))))
            env = {
                k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_")
            }
            env["CLAUDE_CODE_COMMAND"] = f"{sys.executable} {script}"
            ctx = BackendBuildContext(
                templates_dir=_real_templates_dir(), working_dir=str(tmp)
            )

            def started_prompts() -> list[str]:
                if not started.exists():
                    return []
                return started.read_text().split()

            async def scenario() -> None:
                background = [
                    asyncio.create_task(
                        ClaudeCodeCliInferencer(target_path=str(tmp)).ainfer(
                            f"hold-{i}"
                        )
                    )
                    for i in range(5)
                ]
                try:
                    deadline = time.monotonic() + 30
                    while len(started_prompts()) < 4:
                        self.assertLess(time.monotonic(), deadline)
                        await asyncio.sleep(0.05)
                    with patch.object(
                        factories_mod,
                        "_wrap_in_conversational",
                        side_effect=lambda base, _ctx: base,
                    ):
                        chat = factories_mod._claude_cli_factory(ctx)

                    reply = await asyncio.wait_for(chat.ainfer("chat"), timeout=30)

                    self.assertEqual(reply.output, "reply to chat")
                    self.assertEqual(len(started_prompts()), 5, started_prompts())
                    self.assertNotIn("hold-4", started_prompts())
                finally:
                    for run in background:
                        run.cancel()
                    await asyncio.gather(*background, return_exceptions=True)

            with patch.dict(os.environ, env, clear=True):
                asyncio.run(scenario())


class AvailabilityProbeTests(unittest.TestCase):
    def test_claude_cli_available_when_which_returns_path(self):
        with patch(
            "openteam.server.backends.factories.shutil.which",
            return_value="/path/to/claude",
        ):
            self.assertIn(
                "claude found at /path/to/claude",
                factories_mod._claude_cli_status_message(),
            )

    def test_claude_cli_unavailable_when_which_returns_none(self):
        with patch(
            "openteam.server.backends.factories.shutil.which", return_value=None
        ):
            self.assertIn(
                "claude binary not found",
                factories_mod._claude_cli_status_message(),
            )

    def test_rovodev_unavailable_when_which_returns_none(self):
        with patch(
            "openteam.server.backends.factories.shutil.which", return_value=None
        ):
            self.assertIn(
                "acli binary not found",
                factories_mod._rovodev_status_message(),
            )


if __name__ == "__main__":
    unittest.main()
