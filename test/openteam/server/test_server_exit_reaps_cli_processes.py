"""A server that dies with a background tool run in flight takes the run's CLI
process tree with it, however it was stopped.

The CLI leaves start each CLI in its own session (so a cancellation ends the
whole tree), out of reach of the signals the server gets. A graceful stop
cancels the runs in the lifespan shutdown (``aclose_all``); a forced one — a
SIGINT during the graceful shutdown — skips it, and uvicorn then re-raises the
SIGTERM it caught, which kills the process before ``atexit`` runs. The CLI
groups still registered are ended by AgentFoundation's ``process_groups``
reaper: its SIGTERM/SIGHUP handler (installed when ``openteam.server.main`` is
imported, before ``uvicorn.run``) or ``atexit``.

A real ``run_server.py --real-sessions`` with the ``claude_cli`` backend; only
``claude`` is a fake: as the conversation it calls the asynchronous ``task``
tool (the dispatcher's background run), as that task's CLI it streams forever
and keeps a grandchild writing into the task workspace.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import requests
import websockets

_HERE = Path(__file__).resolve()
_OPENSTARTUP = _HERE.parents[3]
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

_TOOL_CALL = (
    "Starting it.\n"
    "```json ToolsToInvoke\n"
    '{"type": "action", "name": "task", "arguments": '
    '{"request": "Document the module."}}\n'
    "```"
)
_FAKE_CLAUDE = """#!{python}
import json, os, subprocess, sys, time

if sys.argv[1:2] == ["--version"]:
    print("fake 0.0")
    sys.exit(0)
if "/tasks/" in os.getcwd():
    writer = subprocess.Popen(
        ["bash", "-c", "while true; do echo grandchild >> writes.log; sleep 0.05; done"]
    )
    with open(os.environ["FAKE_CLAUDE_PIDS"], "a") as f:
        f.write(f"{{os.getpgid(0)}} {{os.getpid()}} {{writer.pid}}\\n")
    while True:
        print(json.dumps({{"type": "stream_event", "event": {{"type": "ping"}}}}), flush=True)
        time.sleep(0.05)
sys.stdin.read()
state = os.environ["FAKE_CLAUDE_STATE"]
calls = int(open(state).read()) if os.path.exists(state) else 0
open(state, "w").write(str(calls + 1))
text = {tool_call!r} if calls == 0 else "The task is running."
delta = {{"type": "text_delta", "text": text}}
event = {{"type": "content_block_delta", "delta": delta}}
print(json.dumps({{"type": "stream_event", "event": event}}), flush=True)
print(json.dumps({{"type": "result", "subtype": "success", "result": text}}), flush=True)
"""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _group_members(pgid: int) -> list[int]:
    """The live (non-zombie) processes in process group ``pgid``."""
    members = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if int(fields[2]) == pgid and fields[0] != "Z":
            members.append(int(entry))
    return members


class _Server:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.port = _free_port()
        self.log = tmp / "server.log"
        self.pids = tmp / "cli.pids"
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(
            _FAKE_CLAUDE.format(python=sys.executable, tool_call=_TOOL_CALL)
        )
        fake.chmod(0o755)
        (tmp / "work").mkdir()
        (tmp / "home").mkdir()
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": os.pathsep.join(p for p in sys.path if p),
                "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
                "HOME": str(tmp / "home"),
                "CLAUDE_CODE_COMMAND": str(fake),
                "FAKE_CLAUDE_PIDS": str(self.pids),
                "FAKE_CLAUDE_STATE": str(tmp / "conversation_calls"),
                "OPENTEAM_WORKING_DIR": str(tmp / "work"),
            }
        )
        with open(self.log, "w") as log:
            self.proc = subprocess.Popen(
                [
                    sys.executable,
                    "run_server.py",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                    "--real-sessions",
                    str(tmp / "runtime"),
                    "--llm-backend",
                    "claude_cli",
                    "--llm-model",
                    "sonnet",
                ],
                cwd=str(Path(openteam_server.__file__).parent),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def wait_healthy(self, timeout: float = 90.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise AssertionError(f"the server exited: {self.log.read_text()}")
            with contextlib.suppress(requests.RequestException):
                if requests.get(self.url("/api/health"), timeout=1).ok:
                    return
            time.sleep(0.3)
        raise AssertionError("the server never became healthy")

    def cli_groups(self) -> list[tuple[int, int, int]]:
        """(pgid, pid, writer pid) of every background CLI started so far."""
        if not self.pids.exists():
            return []
        return [
            tuple(int(n) for n in line.split())
            for line in self.pids.read_text().splitlines()
            if line.strip()
        ]

    async def start_background_run(self) -> None:
        """One chat message; the agent starts the ``task`` tool in the
        background; returns once that task's CLI runs."""
        r = requests.post(self.url("/api/sessions"), json={"title": "bg"}, timeout=10)
        r.raise_for_status()
        sid = (r.json().get("data") or r.json())["id"]
        async with websockets.connect(
            f"ws://127.0.0.1:{self.port}/ws/manager", ping_interval=None
        ) as ws:
            await ws.send(json.dumps({"type": "init", "session_id": sid}))
            await ws.send(json.dumps({"type": "message", "content": "Document it."}))
            deadline = time.monotonic() + 90
            while not self.cli_groups():
                if time.monotonic() > deadline:
                    raise AssertionError(
                        f"no background CLI started: {self.log.read_text()[-3000:]}"
                    )
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(ws.recv(), 0.2)
        await asyncio.sleep(0.5)

    def wait_logged(self, text: str, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while text not in self.log.read_text():
            if time.monotonic() > deadline:
                raise AssertionError(f"{text!r} never logged")
            time.sleep(0.01)

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        for pgid, pid, writer in self.cli_groups():
            for target in (pid, writer):
                with contextlib.suppress(ProcessLookupError):
                    os.kill(target, signal.SIGKILL)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pgid, signal.SIGKILL)


@unittest.skipUnless(sys.platform.startswith("linux"), "reads /proc")
class ServerExitReapsCliProcessesTest(unittest.TestCase):
    def _stop(self, *signals: int, forced: bool = False) -> tuple[_Server, int]:
        """Start a server with a background CLI run, deliver ``signals`` (each
        after the server acted on the one before it), and return the server
        and its exit status."""
        tmp = Path(tempfile.mkdtemp(prefix="os_reap_"))
        server = _Server(tmp)
        self.addCleanup(server.kill)
        server.wait_healthy()
        asyncio.run(server.start_background_run())
        (pgid, _pid, _writer), *_ = server.cli_groups()
        self.assertTrue(_group_members(pgid), "the background CLI is not running")

        first, *rest = signals
        server.proc.send_signal(first)
        if rest:
            server.wait_logged("Shutting down")
        for sig in rest:
            server.proc.send_signal(sig)
        returncode = server.proc.wait(timeout=60)
        log = server.log.read_text()
        self.assertEqual(
            "Waiting for application shutdown." not in log,
            forced,
            "the lifespan shutdown ran" if forced else "the lifespan shutdown skipped",
        )
        return server, returncode

    def _assert_no_cli_process_survived(self, server: _Server) -> None:
        # The CLI's writer is in its group.
        for pgid, _pid, _writer in server.cli_groups():
            deadline = time.monotonic() + 10
            while _group_members(pgid) and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual(_group_members(pgid), [], f"CLI group {pgid} survived")

    def test_double_sigterm(self) -> None:
        server, returncode = self._stop(signal.SIGTERM, signal.SIGTERM)
        self.assertEqual(returncode, -signal.SIGTERM)
        self._assert_no_cli_process_survived(server)

    def test_sigint_during_the_graceful_shutdown_of_a_sigterm(self) -> None:
        server, returncode = self._stop(signal.SIGTERM, signal.SIGINT, forced=True)
        self.assertEqual(returncode, -signal.SIGTERM)
        self._assert_no_cli_process_survived(server)

    def test_double_sigint(self) -> None:
        server, _returncode = self._stop(signal.SIGINT, signal.SIGINT, forced=True)
        self._assert_no_cli_process_survived(server)

    def test_sighup(self) -> None:
        server, returncode = self._stop(signal.SIGHUP, forced=True)
        self.assertEqual(returncode, -signal.SIGHUP)
        self._assert_no_cli_process_survived(server)


if __name__ == "__main__":
    unittest.main()
