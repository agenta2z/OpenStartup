"""A background tool run ends with its session: deleting the session and
shutting the server down cancel and await it, its CLI process tree is gone and
nothing writes into the session afterwards. That holds for a run the dispatcher
started (an async ``task``), a slash command's run, an Experiment Hub run and
the jobs of an Experiment Hub's queue — an in-turn hub's queued ``task`` jobs
(the queue does not move on to the next one) and a REST-started submission run.
A backend switch leaves the dispatcher's run going — its completion reaches the
conversation through the host's auto-advance turn, whatever the backend.

Production code end to end: ``ToolDispatcher`` / the slash-command route / the
hub run supervisor / AgentFoundation's ``HubController`` → AgentFoundation's
``task`` executor (``default.yaml``) → ``ClaudeCodeCliInferencer``; only
``claude`` is a fake that streams forever and keeps a grandchild writing into
the task workspace. A submission run is a real ``SubmissionRunner`` run
(``local_mock`` launcher) of a script that behaves the same way.
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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
from agent_foundation.resources.tools import registry as tool_registry
from agent_foundation.resources.tools.registry import load_all_tools
from agent_foundation.resources.tools.task import executor as task_executor
from openteam.server import main as server_main
from openteam.server.routes.experiment_hub_routes import (
    cancel_submission_run,
    run_submission,
)
from openteam.server.routes.manager_websocket_routes import _try_dev_slash_command
from openteam.server.routes.session_routes import delete_session
from openteam.server.services.conversation_service import ConversationService
from openteam.server.services.dashboard_runtime import HubRunSupervisor
from openteam.server.services.data_service import RealSessionDataService
from openteam.server.services.session_store import SessionStore
from openteam.server.services.tool_dispatcher import ToolDispatcher

_TEMPLATES_DIR = (
    Path(openteam_server.__file__).parent / "resources" / "prompt_templates"
)
# A slash-command tool whose run is the ``task`` executor's.
_SLASH_TOOL = {
    "name": "document",
    "description": "Document the code.",
    "tool_type": "Action",
    "agent_enabled": False,
    "slash_enabled": True,
    "dev_mode_only": False,
    "asynchronous": True,
    "executor": "agent_foundation.resources.tools.task.executor:execute",
    "parameters": [{"name": "request", "type": "string", "positional": True}],
}
_FAKE_CLAUDE = """#!/bin/bash
[ "$1" = "--version" ] && { echo "fake 0.0"; exit 0; }
cat > /dev/null &
( while true; do echo grandchild >> "$PWD/writes.log"; sleep 0.05; done ) &
echo "$$ $!" >> "$FAKE_CLAUDE_PIDS"
while true; do
  echo '{"type":"stream_event","event":{"type":"ping"}}'
  echo child >> "$PWD/writes.log"
  sleep 0.05
done
"""
_SUBMIT_SCRIPT = """\
import os, subprocess, sys, time
writes, pids = sys.argv[1], sys.argv[2]
loop = 'while true; do echo grandchild >> "$0"; sleep 0.05; done'
child = subprocess.Popen(["bash", "-c", loop, writes])
with open(pids, "a") as f:
    f.write(f"{os.getpid()} {child.pid}\\n")
while True:
    with open(writes, "a") as f:
        f.write("child\\n")
    print("tick", flush=True)
    time.sleep(0.05)
"""


def _running(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().split()[2]
    except FileNotFoundError:
        return False
    return state != "Z"


def _files(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(p): (p.stat().st_mtime_ns, p.stat().st_size)
        for p in root.rglob("*")
        if p.is_file()
    }


class _Interactive:
    """The task-status transport the dispatcher reports to."""

    def __init__(self) -> None:
        self.statuses: list[tuple[str, str]] = []

    async def send_task_status(self, task_id: str, status: str, **_kw) -> None:
        self.statuses.append((task_id, status))

    async def _send(self, message: dict) -> None:
        pass

    async def send_graph_event(self, *_args, **_kw) -> None:
        pass


class _NoIntegrations:
    def handles(self, _tool_name: str) -> bool:
        return False


class _ConnectionRegistry:
    """The out-of-turn transport REST-started hub runs report to."""

    def __init__(self) -> None:
        self.frames: list[dict] = []

    async def emit(self, _session_id: str, message: dict) -> int:
        self.frames.append(message)
        return 0


class _Harness:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.store = SessionStore(tmp / "runtime", resume_server="new")
        self.data = RealSessionDataService(tmp / "no_fixtures", self.store)
        self.sid = self.store.create_session("bg")["id"]
        self.session_dir = self.store.get_session_dir(self.sid)
        self.svc = ConversationService(
            templates_dir=_TEMPLATES_DIR,
            llm_backend="mock",
            working_dir=str(tmp / "work"),
            session_store=self.store,
        )
        self.pids_file = tmp / "pids.txt"
        self.dispatcher = ToolDispatcher(
            tool_registry=load_all_tools(),
            integration_executor=_NoIntegrations(),
            session_context={
                "session_id": self.sid,
                "session_root": str(self.session_dir),
                "working_dir": str(tmp / "work"),
            },
            interactive=_Interactive(),
            session_store=self.store,
        )
        self.dispatcher._register_bg_task = (
            lambda task, task_id: self.svc._register_bg_task(self.sid, task_id, task)
        )
        self.hub_runs = HubRunSupervisor()
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                data_service=self.data,
                conversation_service=self.svc,
                hub_run_supervisor=self.hub_runs,
                connection_registry=_ConnectionRegistry(),
            )
        )
        self.slash_tools = tmp / "slash_tools"
        (self.slash_tools / "document").mkdir(parents=True)
        (self.slash_tools / "document" / "tool.json").write_text(
            json.dumps(_SLASH_TOOL)
        )
        self.frames: list[dict] = []

    def pids(self) -> list[int]:
        if not self.pids_file.exists():
            return []
        return [int(p) for p in self.pids_file.read_text().split()]

    async def _until_cli_runs(self, run: asyncio.Task) -> asyncio.Task:
        deadline = time.monotonic() + 60
        while not list(self.session_dir.glob("tasks/*/writes.log")):
            if run.done():
                raise AssertionError(f"the run ended before its CLI started: {run}")
            if time.monotonic() > deadline:
                raise AssertionError("the CLI never started")
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.3)
        return run

    async def start_background_task(self) -> asyncio.Task:
        result = await self.dispatcher("task", {"request": "Document the module."})
        task_id = result.context_updates["task_id"]
        return await self._until_cli_runs(self.svc._bg_tasks[self.sid][task_id])

    async def start_slash_command_run(self) -> asyncio.Task:
        """``/document …`` typed into the chat, as the manager socket runs it."""

        async def send(frame: dict) -> None:
            self.frames.append(frame)

        load_all = tool_registry.load_all_tools
        with mock.patch.object(
            tool_registry,
            "load_all_tools",
            lambda extra_dirs=None: load_all([*(extra_dirs or []), self.slash_tools]),
        ):
            handled = await _try_dev_slash_command(
                "/document Document the module.",
                self.sid,
                send,
                session_store=self.store,
                track_background_task=functools.partial(
                    self.svc.track_background_task, self.sid
                ),
            )
        if not handled:
            raise AssertionError(f"the route left /document alone: {self.frames}")
        (run,) = self.svc._bg_tasks[self.sid].values()
        return await self._until_cli_runs(run)

    async def start_hub_run(self) -> asyncio.Task:
        """An out-of-turn Experiment Hub run (e.g. a hub ``implement_hypothesis``
        command) on the hub run supervisor, running a ``task``."""
        context = {"session_id": self.sid, "session_root": str(self.session_dir)}
        run = await self.hub_runs.spawn(
            self.sid,
            "hubcmd-implement_hypothesis-hub-1",
            task_executor.execute({"request": "Document the module."}, context),
        )
        return await self._until_cli_runs(run)

    async def start_in_turn_hub_jobs(self) -> asyncio.Task:
        """The agent opens the Experiment Hub on two hypotheses to implement
        (the ``proposal-selection --experiment-hub`` handoff): the hub queues a
        ``task`` job per hypothesis and runs the first one."""
        await self.dispatcher.create_experiment_hub(
            selected_details=[
                {"id": "H1", "title": "First"},
                {"id": "H2", "title": "Second"},
            ],
            proposals_data={},
            group_by="hypothesis",
            auto_implement=True,
        )
        deadline = time.monotonic() + 60
        while not list(self.session_dir.glob("tasks/*/writes.log")):
            if time.monotonic() > deadline:
                raise AssertionError(f"no hub job started: {self.queue()}")
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.3)
        (run,) = [t for t in self.svc._bg_tasks[self.sid].values() if not t.done()]
        return run

    def queue(self) -> list[str]:
        """The statuses of the session's persisted hub job queue."""
        wc = self.store.get_session(self.sid).get("workflow_context") or {}
        return [e["status"] for e in wc.get("task_queue", [])]

    def _request(self, body: dict) -> SimpleNamespace:
        async def read_body() -> bytes:
            return json.dumps(body).encode()

        return SimpleNamespace(app=self.app, body=read_body)

    async def start_submission_run(self) -> str:
        """``POST …/submissions/{id}/run`` (the hub's Monitor view) of a
        ``local_mock`` launch whose script never finishes and keeps a
        grandchild writing into the session. Returns the run id."""
        setup = self.tmp / "setup"
        setup.mkdir()
        script = setup / "submit_v1.py"
        script.write_text(_SUBMIT_SCRIPT)
        launch = setup / "launch.json"
        writes = self.session_dir / "writes.log"
        launch.write_text(
            json.dumps(
                {
                    "launcher": "local_mock",
                    "script_args": [str(writes), str(self.pids_file)],
                }
            )
        )
        result = await run_submission(
            self._request({"scriptPath": str(script), "launchPath": str(launch)}),
            self.sid,
            "hub-1",
            "sub-1",
        )
        deadline = time.monotonic() + 60
        while len(self.pids()) < 2 or not writes.exists():
            if time.monotonic() > deadline:
                raise AssertionError("the submission run never started")
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.3)
        return result["data"]["run_id"]


class BackgroundTaskCancellationTest(unittest.TestCase):
    def _run(self, scenario) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            fake = tmp / "claude"
            fake.write_text(_FAKE_CLAUDE)
            fake.chmod(0o755)
            env = {
                "CLAUDE_CODE_COMMAND": str(fake),
                "FAKE_CLAUDE_PIDS": str(tmp / "pids.txt"),
            }
            h = None
            try:
                with mock.patch.dict(os.environ, env):
                    h = _Harness(tmp)
                    asyncio.run(asyncio.wait_for(scenario(h), 120))
            finally:
                for pid in h.pids() if h is not None else []:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def _assert_stopped(self, h: _Harness, run: asyncio.Task) -> None:
        self.assertTrue(run.done(), "the background run is still running")
        self.assertTrue(run.cancelled())
        self.assertEqual(len(h.pids()), 2)
        self.assertEqual([p for p in h.pids() if _running(p)], [])
        self.assertEqual(h.svc.get_live_task_ids(h.sid), set())

    def test_server_shutdown_cancels_and_awaits_background_runs(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_background_task()

            await h.svc.aclose_all()

            self._assert_stopped(h, run)
            before = _files(h.session_dir)
            await asyncio.sleep(0.5)
            self.assertEqual(_files(h.session_dir), before)

        self._run(scenario)

    def test_deleting_the_session_stops_its_background_run_before_its_folder_goes(
        self,
    ) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_background_task()

            result = await delete_session(SimpleNamespace(app=h.app), h.sid)

            self.assertEqual(result, {"data": {"deleted": True}})
            self._assert_stopped(h, run)
            self.assertFalse(h.session_dir.exists())
            await asyncio.sleep(0.5)
            self.assertFalse(h.session_dir.exists(), "a writer re-created the folder")

        self._run(scenario)

    def test_deleting_the_session_stops_its_slash_command_run(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_slash_command_run()

            result = await delete_session(SimpleNamespace(app=h.app), h.sid)

            self.assertEqual(result, {"data": {"deleted": True}})
            self._assert_stopped(h, run)
            self.assertIn("cancelled", [f.get("status") for f in h.frames])
            await asyncio.sleep(0.5)
            self.assertFalse(h.session_dir.exists(), "a writer re-created the folder")

        self._run(scenario)

    def test_server_shutdown_stops_slash_command_runs(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_slash_command_run()

            await server_main._close_conversation_sessions(h.app)

            self._assert_stopped(h, run)
            before = _files(h.session_dir)
            await asyncio.sleep(0.5)
            self.assertEqual(_files(h.session_dir), before)

        self._run(scenario)

    def test_deleting_the_session_stops_its_experiment_hub_runs(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_hub_run()

            await delete_session(SimpleNamespace(app=h.app), h.sid)

            self._assert_stopped(h, run)
            self.assertEqual(h.hub_runs.active_runs(h.sid), [])
            await asyncio.sleep(0.5)
            self.assertFalse(h.session_dir.exists(), "a writer re-created the folder")

        self._run(scenario)

    def test_server_shutdown_stops_experiment_hub_runs(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_hub_run()

            await server_main._cancel_hub_runs(h.app)

            self._assert_stopped(h, run)
            self.assertEqual(h.hub_runs.active_runs(h.sid), [])
            before = _files(h.session_dir)
            await asyncio.sleep(0.5)
            self.assertEqual(_files(h.session_dir), before)

        self._run(scenario)

    def test_deleting_the_session_stops_its_hub_jobs_and_their_queue(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_in_turn_hub_jobs()
            self.assertEqual(h.queue(), ["running", "queued"])

            await delete_session(SimpleNamespace(app=h.app), h.sid)

            self._assert_stopped(h, run)
            self.assertFalse(h.session_dir.exists())
            await asyncio.sleep(0.5)
            self.assertEqual(len(h.pids()), 2, "the queue started its next job")
            self.assertFalse(h.session_dir.exists(), "a writer re-created the folder")

        self._run(scenario)

    def test_server_shutdown_stops_hub_jobs_and_their_queue(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_in_turn_hub_jobs()

            await h.svc.aclose_all()

            self._assert_stopped(h, run)
            self.assertEqual(h.queue(), ["error", "queued"])
            before = _files(h.session_dir)
            await asyncio.sleep(0.5)
            self.assertEqual(_files(h.session_dir), before)
            self.assertEqual(len(h.pids()), 2, "the queue started its next job")

        self._run(scenario)

    def test_deleting_the_session_stops_its_submission_run(self) -> None:
        async def scenario(h: _Harness) -> None:
            await h.start_submission_run()

            await delete_session(SimpleNamespace(app=h.app), h.sid)

            self.assertEqual(h.hub_runs.active_runs(h.sid), [])
            self.assertEqual(len(h.pids()), 2)
            self.assertEqual([p for p in h.pids() if _running(p)], [])
            await asyncio.sleep(0.5)
            self.assertFalse(h.session_dir.exists(), "a writer re-created the folder")

        self._run(scenario)

    def test_server_shutdown_stops_submission_runs(self) -> None:
        async def scenario(h: _Harness) -> None:
            await h.start_submission_run()

            await server_main._cancel_hub_runs(h.app)

            self.assertEqual(h.hub_runs.active_runs(h.sid), [])
            self.assertEqual([p for p in h.pids() if _running(p)], [])
            self.assertEqual(h.queue(), ["error"])
            before = _files(h.session_dir)
            await asyncio.sleep(0.5)
            self.assertEqual(_files(h.session_dir), before)

        self._run(scenario)

    def test_cancelling_a_submission_run_stops_it(self) -> None:
        async def scenario(h: _Harness) -> None:
            run_id = await h.start_submission_run()

            result = await cancel_submission_run(
                h._request({"run_id": run_id}), h.sid, "hub-1", "sub-1"
            )

            self.assertTrue(result["data"]["cancelled"], result)
            self.assertEqual([p for p in h.pids() if _running(p)], [])
            self.assertEqual(h.queue(), ["error"])

        self._run(scenario)

    def test_a_backend_switch_keeps_the_background_run_until_shutdown(self) -> None:
        async def scenario(h: _Harness) -> None:
            run = await h.start_background_task()

            await h.svc.set_session_backend(h.sid, "claude_cli")

            self.assertFalse(run.done())
            self.assertEqual(len(h.svc.get_live_task_ids(h.sid)), 1)
            await h.svc.aclose_all()
            self._assert_stopped(h, run)

        self._run(scenario)


if __name__ == "__main__":
    unittest.main()
