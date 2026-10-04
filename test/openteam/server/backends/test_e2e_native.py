"""End-to-end host checklist for the native backends (real vendor agent).

Boots ``run_server.py --real-sessions`` with a native backend, then drives
``/ws/manager`` the way the React UI does and checks the host behaviors the
native orchestrator must preserve (plan §12.3): one bubble per reply with the
session instructions' persona, the SOP catalog, cancel mid-stream (and the
interrupted notice next turn), the "View Prompt" manifest, server restart
(same vendor session), resume-from-turn (the vendor forgets the dropped
turns), ``/compact``, ``/new``, ``/clear``, ``/model``, cancelling a waiting
widget (and the cancelled-widget notice next turn), the Experiment Hub
handoff, an SOP's compound widget answered after a page refresh (durable
widget recovery), an async tool whose completion auto-advances the SOP, yolo
mode, backend switch (SOP kept, recap on return), session delete and graceful
shutdown. Tool-less backends (Metamate) skip the tool-driven checks and are
checked for slash-command SOP control instead.

Checks assert on evidence beyond the reply text: the record and the "View
Prompt" manifest the host keeps (turn context, origin, notices), the vendor's
own session files (Claude Code transcripts: the exact fork's turns, the
``/compact`` boundary, the model after ``/model``; Codex rollouts: the model)
and live processes (a backend switch ends the old vendor process; nothing
keeps running in the run's directories after shutdown).

Run directly (pytest collects nothing here; the vendor costs real money):
    python -m test.openteam.server.backends.test_e2e_native \\
        --backend native_claude_sdk --model sonnet

Exit code 0 = every check passed; 1 = a check failed; 77 = skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import requests
import websockets

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

_TURN_TIMEOUT_S = 420.0
# C15 (understand_codebase completes and auto-advances the SOP) is opt-in:
# even docs-only on haiku, understand_codebase of the one-file toy model runs
# the executor's propose/breakdown/worker/review rounds — 1,495 s measured
# (2026-10-03, 14 CLI sessions). Opt in with --sop-async-timeout 2400.
_SOP_ASYNC_TIMEOUT_S = 0.0
_FREE_TEXT_ANSWER = "Use the defaults."
# Codewords test the vendor session's own memory of the conversation; one the
# agent saves to its persistent memory (e.g. Claude Code's auto-memory) would
# outlive the session.
_IN_CONVERSATION_ONLY = (
    "Keep it in this conversation only: do not save it to memory or any file. "
    "Just acknowledge briefly."
)
_CLAUDE_BACKENDS = frozenset({"native_claude_sdk", "native_claude_cli"})
# Backends whose vendor agent gets no AgentFoundation tools.
_TOOL_LESS_BACKENDS = frozenset({"native_metamate"})
# Two models each backend accepts; the ``/model`` check switches to the one
# that is not ``--model`` and back. Other backends need ``--other-model``.
_MODEL_PAIRS = {
    "native_claude_sdk": ("haiku", "sonnet"),
    "native_claude_cli": ("haiku", "sonnet"),
    "native_codex": ("gpt-5.6-luna", "gpt-5.6-sol"),
}
# Warnings the server logs when closing a session's resources goes wrong.
_CLOSE_FAILURES = (
    "Closing conversation sessions failed",
    "Closing the evicted inferencer",
    "Closing the vendor sessions of session",
    "its turn did not stop within",
)

Action = Callable[[], Awaitable[None]]


@dataclass
class TurnLog:
    bubbles: list[str] = field(default_factory=list)
    widgets: list[dict] = field(default_factory=list)
    status: str = ""
    errors: list[str] = field(default_factory=list)
    frames: list[dict] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.bubbles)

    def of_type(self, kind: str) -> list[dict]:
        return [f for f in self.frames if f.get("type") == kind]


class Checks:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []
        self.skipped: list[tuple[str, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""), flush=True)
        return ok

    def skip(self, name: str, reason: str) -> None:
        self.skipped.append((name, reason))
        print(f"[SKIP] {name} — {reason}", flush=True)

    def summary(self) -> int:
        failed = [r for r in self.results if not r[1]]
        print(
            f"\n{len(self.results) - len(failed)}/{len(self.results)} checks passed"
            + (f", {len(self.skipped)} skipped" if self.skipped else "")
        )
        for name, _ok, detail in failed:
            print(f"  FAILED: {name} — {detail}")
        for name, reason in self.skipped:
            print(f"  SKIPPED: {name} — {reason}")
        return 1 if failed else 0


class Server:
    def __init__(
        self, runtime_dir: Path, work_dir: Path, backend: str, model: str
    ) -> None:
        self.runtime_dir = runtime_dir
        self.work_dir = work_dir
        self.backend = backend
        self.model = model
        self.port = 0
        self.proc: Optional[subprocess.Popen] = None
        self.log_path = runtime_dir / "server.log"

    def start(self, *, resume: bool = False) -> None:
        self.port = _free_port()
        env = os.environ.copy()
        # The server imports exactly what this process can: a launcher may have
        # consumed PYTHONPATH from the environment at startup.
        env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
        env["OPENTEAM_WORKING_DIR"] = str(self.work_dir)
        cmd = [
            sys.executable,
            "run_server.py",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--real-sessions",
            str(self.runtime_dir),
            "--llm-backend",
            self.backend,
            "--llm-model",
            self.model,
        ]
        if resume:
            cmd.append("--resume-latest-server")
        log = open(self.log_path, "a")
        log.write(f"\n===== start {cmd} =====\n")
        log.flush()
        self.proc = subprocess.Popen(
            cmd,
            cwd=str(Path(openteam_server.__file__).parent),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        _wait_for_health(self.port)

    def stop(self, timeout: float = 60.0) -> Optional[int]:
        """Graceful stop (SIGINT → lifespan shutdown); returns the exit code,
        or None when it had to be killed."""
        if self.proc is None:
            return None
        self.proc.send_signal(signal.SIGINT)
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
            return None
        finally:
            self.proc = None

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def session(self, sid: str) -> dict:
        r = requests.get(self.url(f"/api/sessions/{sid}"), timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    def create_session(self, title: str) -> str:
        r = requests.post(self.url("/api/sessions"), json={"title": title}, timeout=10)
        r.raise_for_status()
        return (r.json().get("data") or r.json())["id"]

    def select_backend(self, sid: str, backend: str, model: str) -> requests.Response:
        return requests.post(
            self.url(f"/api/sessions/{sid}/backend"),
            json={"backend": backend, "model": model},
            timeout=180,
        )

    def turn_data(self, sid: str, turn: int, round_: int) -> dict:
        """What the UI's "View Prompt" shows for a round of a turn."""
        r = requests.get(
            self.url(f"/api/sessions/{sid}/turns/{turn}"),
            params={"round": round_},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["data"]


class Chat:
    """One ``/ws/manager`` connection (one browser tab)."""

    def __init__(self, port: int, sid: str) -> None:
        self.url = f"ws://127.0.0.1:{port}/ws/manager"
        self.sid = sid
        self.ws: Any = None
        self.on_connect: list[dict] = []

    async def __aenter__(self) -> "Chat":
        # No client keepalive: the server's loop can stall for a while when a
        # heavy tool starts, and this client is not what is under test.
        self.ws = await websockets.connect(
            self.url, max_size=16 * 1024 * 1024, ping_interval=None
        )
        await self.send({"type": "init", "session_id": self.sid})
        while True:
            frame = await self.recv(15)
            if frame.get("type") == "session_init":
                break
        # A re-displayed pending widget / graph replay follows session_init.
        self.on_connect = await self.drain(2.0)
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.ws.close()

    async def send(self, obj: dict) -> None:
        await self.ws.send(json.dumps(obj))

    async def recv(self, timeout: float) -> dict:
        while True:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue

    async def drain(self, seconds: float) -> list[dict]:
        frames = []
        deadline = time.monotonic() + seconds
        while (left := deadline - time.monotonic()) > 0:
            try:
                frames.append(await self.recv(left))
            except asyncio.TimeoutError:
                break
        return frames

    async def wait_for(
        self, matches: Callable[[dict], bool], timeout: float
    ) -> Optional[dict]:
        """The first frame ``matches`` accepts within ``timeout`` (others are
        dropped), or None."""
        deadline = time.monotonic() + timeout
        while (left := deadline - time.monotonic()) > 0:
            try:
                frame = await self.recv(left)
            except asyncio.TimeoutError:
                return None
            if matches(frame):
                return frame
        return None

    async def collect(
        self,
        *,
        answer: Optional[Callable[[dict], Any]] = None,
        stop_on_widget: bool = False,
        interrupt: Optional[Action] = None,
        interrupt_after_s: float = 0.0,
        continuing: bool = False,
        timeout: float = _TURN_TIMEOUT_S,
    ) -> TurnLog:
        """Frames of one turn until its terminal ``status``. Statuses before
        the turn's ``message_start`` belong to an earlier turn, unless the
        turn is ``continuing`` (a live widget answer continues it without a
        new ``message_start``). ``interrupt`` runs once: at the first token,
        or ``interrupt_after_s`` after the turn started if that comes first."""
        log = TurnLog()
        reader = _TurnReader(self, log, answer, stop_on_widget, interrupt)
        reader.started = continuing
        deadline = time.monotonic() + timeout
        try:
            while not log.status:
                left = deadline - time.monotonic()
                try:
                    frame = await self.recv(left) if left > 0 else None
                except asyncio.TimeoutError:
                    frame = None
                if frame is None:
                    log.status = "timeout"
                else:
                    await reader.on_frame(frame, interrupt_after_s)
        finally:
            reader.cancel_timer()
        return log

    async def turn(self, content: str, **kw: Any) -> TurnLog:
        print(f"\n>>> {content}", flush=True)
        await self.send({"type": "message", "content": content})
        log = await self.collect(**kw)
        print(f"<<< [{log.status}] {log.text[:400]!r}", flush=True)
        return log

    async def answer(self, frame: dict, value: Any) -> None:
        print(f"    [widget] answering {json.dumps(value)[:200]}", flush=True)
        await self.send(
            {
                "type": "pending_input_response",
                "pending_input_id": frame.get("pending_input_id"),
                "content": json.dumps(value),
            }
        )


class _TurnReader:
    """Folds one turn's frames into a ``TurnLog``."""

    def __init__(
        self,
        chat: Chat,
        log: TurnLog,
        answer: Optional[Callable[[dict], Any]],
        stop_on_widget: bool,
        interrupt: Optional[Action],
    ) -> None:
        self.chat = chat
        self.log = log
        self.answer = answer
        self.stop_on_widget = stop_on_widget
        self.interrupt = interrupt
        self.started = False
        self._timer: Optional[asyncio.Task] = None

    async def on_frame(self, frame: dict, interrupt_after_s: float) -> None:
        self.log.frames.append(frame)
        kind = frame.get("type")
        if kind == "message_start":
            self.started = True
            if self.interrupt is not None and interrupt_after_s > 0:
                self._timer = asyncio.create_task(
                    self._interrupt_later(interrupt_after_s)
                )
        elif kind == "token":
            await self._fire_interrupt()
        elif kind == "message_end":
            self._message_end(frame)
        elif kind == "pending_input":
            await self._widget(frame)
        elif kind == "error":
            self.log.errors.append(frame.get("message") or "")
        elif (
            kind == "status"
            and frame.get("status") in ("complete", "error")
            and self.started
        ):
            self.log.status = frame.get("detail") or frame["status"]

    async def _interrupt_later(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
        await self._fire_interrupt()

    async def _fire_interrupt(self) -> None:
        action, self.interrupt = self.interrupt, None
        if action is not None:
            await action()

    def cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()

    def _message_end(self, frame: dict) -> None:
        if frame.get("error"):
            self.log.errors.append(frame.get("final_content") or "")
        elif frame.get("final_content"):
            self.log.bubbles.append(frame["final_content"])

    async def _widget(self, frame: dict) -> None:
        self.log.widgets.append(frame)
        if self.stop_on_widget:
            self.log.status = "widget"
        elif self.answer is not None:
            await self.chat.answer(frame, self.answer(frame))


def answer_widget(frame: dict) -> Any:
    """What a user clicking through the widget would submit."""
    mode = frame.get("input_mode") or {}
    meta = mode.get("metadata") or {}
    if meta.get("compound"):
        return {
            "values": {
                tool["output_var"]: _answer_one(tool.get("input_mode") or {})
                for tool in meta.get("tools", [])
            }
        }
    return _answer_one(mode)


def _answer_one(mode: dict) -> Any:
    options = mode.get("options") or []
    if mode.get("mode") == "single_choice" and options:
        return options[0]["value"]
    if mode.get("mode") == "multiple_choice" and options:
        return [options[0]["value"]]
    if mode.get("expected_input_type") == "path" and mode.get("prefix"):
        return str(Path(mode["prefix"]) / "toy_model")
    return _FREE_TEXT_ANSWER


def _widget_tool_types(frame: dict) -> list[str]:
    meta = (frame.get("input_mode") or {}).get("metadata") or {}
    if meta.get("compound"):
        return [t.get("tool_type", "?") for t in meta.get("tools", [])]
    return [meta.get("widget_type") or (frame.get("input_mode") or {}).get("mode", "?")]


def _widget_metadata(frame: dict) -> dict:
    return (frame.get("input_mode") or {}).get("metadata") or {}


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for_health(port: int, timeout: float = 60.0) -> None:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=1.0).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Server on :{port} never became healthy within {timeout}s")


def _user_message(session: dict, content: str) -> dict:
    for m in reversed(session.get("messages", [])):
        if m.get("role") in ("user", "manager") and m.get("content") == content:
            return m
    raise KeyError(content)


def _user_message_id(session: dict, content: str) -> str:
    return _user_message(session, content)["id"]


def _turn_of(server: Server, sid: str, content: str) -> int:
    """The turn the latest user message ``content`` started."""
    return int(_user_message(server.session(sid), content)["turn_number"])


def _assistant_messages(server: Server, sid: str, turn: int) -> list[dict]:
    return [
        m
        for m in server.session(sid).get("messages", [])
        if m.get("role") == "assistant" and m.get("turn_number") == turn
    ]


def _record(server: Server, sid: str) -> dict:
    return server.session(sid).get("native_session") or {}


# ── Vendor evidence: transcripts, rollouts, processes ────────────────────


def _claude_transcript(session_id: str) -> list[dict]:
    """The entries of Claude Code session ``session_id``'s transcript
    (``$CLAUDE_CONFIG_DIR/projects/<cwd slug>/<id>.jsonl``); [] if absent."""
    if not session_id:
        return []
    root = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return _newest_jsonl((root / "projects").glob(f"*/{session_id}.jsonl"))


def _codex_rollout(thread_id: str) -> list[dict]:
    """The entries of Codex thread ``thread_id``'s rollout
    (``$CODEX_HOME/sessions/YYYY/MM/DD/rollout-*-<id>.jsonl``); [] if absent."""
    if not thread_id:
        return []
    root = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return _newest_jsonl((root / "sessions").glob(f"*/*/*/rollout-*-{thread_id}.jsonl"))


def _newest_jsonl(paths: Any) -> list[dict]:
    """The entries of the most recently written of ``paths``; [] if none."""
    newest = max(paths, key=lambda p: p.stat().st_mtime, default=None)
    return _jsonl(newest) if newest is not None else []


def _jsonl(path: Path) -> list[dict]:
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _transcript_user_texts(entries: list[dict]) -> list[str]:
    """Text of the main thread's user messages (not tool results, not hook
    attachments): what the user lane delivered."""
    texts = []
    for e in entries:
        if e.get("type") != "user" or e.get("isSidechain"):
            continue
        content = (e.get("message") or {}).get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            texts.extend(
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
    return texts


def _compact_boundaries(entries: list[dict]) -> int:
    return sum(
        1
        for e in entries
        if e.get("type") == "system" and e.get("subtype") == "compact_boundary"
    )


def _vendor_model(backend: str, session_id: str) -> Optional[str]:
    """The model the vendor answered the session's latest turn with, read
    from its own session files; None where the backend keeps none here."""
    if backend in _CLAUDE_BACKENDS:
        models = [
            (e.get("message") or {}).get("model")
            for e in _claude_transcript(session_id)
            if e.get("type") == "assistant" and not e.get("isSidechain")
        ]
        models = [m for m in models if m and not m.startswith("<")]
        return models[-1] if models else ""
    if backend == "native_codex":
        models = [
            (e.get("payload") or {}).get("model")
            for e in _codex_rollout(session_id)
            if e.get("type") == "turn_context"
        ]
        return next((m for m in reversed(models) if m), "")
    return None


def _model_matches(backend: str, requested: str, used: str) -> bool:
    # Claude aliases (haiku, sonnet, …) resolve to dated model ids.
    if backend in _CLAUDE_BACKENDS:
        return requested.lower() in used.lower()
    return used == requested


def _processes(matches: Callable[[int, str, str], bool]) -> list[str]:
    """``"<pid> <cmdline>"`` of each live process (but this one) for which
    ``matches(pid, cmdline, cwd)`` holds."""
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            raw = (proc / "cmdline").read_bytes()
            cwd = os.readlink(proc / "cwd")
        except OSError:
            continue
        cmd = raw.replace(b"\0", b" ").decode(errors="replace").strip()
        if cmd and matches(int(proc.name), cmd, cwd):
            found.append(f"{proc.name} {cmd[:160]}")
    return found


def _processes_mentioning(token: str) -> list[str]:
    """Live processes whose command line names ``token`` (a vendor session
    id: ``--session-id``/``--resume <id>``, ``exec resume <id>``)."""
    if not token:
        return []
    return _processes(lambda _pid, cmd, _cwd: token in cmd)


# Claude Code's guardrail daemon detaches by design and outlives its client.
_VENDOR_DAEMONS = ("guardrails_srv",)


def _vendor_processes_under(root: Path) -> list[str]:
    """Live processes running in ``root`` or below (vendor CLIs and the tools
    they started), Claude Code's detached guardrail daemon excepted."""
    prefix = str(root.resolve())
    return _processes(
        lambda _pid, cmd, cwd: (cwd == prefix or cwd.startswith(prefix + os.sep))
        and not any(d in cmd.split(" ", 1)[0] for d in _VENDOR_DAEMONS)
    )


async def _wait_until_none(probe: Callable[[], list[str]], seconds: float) -> list[str]:
    """``probe()`` once it returns nothing, or its last result after
    ``seconds``."""
    deadline = time.monotonic() + seconds
    while (left := probe()) and time.monotonic() < deadline:
        await asyncio.sleep(1.0)
    return left


def _notice(l2: str, kind: str) -> Optional[str]:
    """The text of the ``<notice type="kind">`` in an L2, or None."""
    m = re.search(rf'<notice type="{re.escape(kind)}">(.*?)</notice>', l2, re.S)
    return m.group(1) if m else None


@dataclass
class Manifest:
    """A native turn's prompt manifest, as "View Prompt" shows it: each lane
    under a header naming the route the turn's prompt data records."""

    feed: dict
    headers: bool = False  # every lane header found, in order
    l1: str = ""
    l2: str = ""
    user: str = ""
    l3: str = ""


# (Manifest field, header title, prompt-data key of the lane's route), in order.
_MANIFEST_LANES = (
    ("l1", "Session instructions", "l1_route"),
    ("l2", "Turn context", "l2_route"),
    ("user", "User message", "user_route"),
    ("l3", "State updates", "l3_route"),
)


def _manifest_header(title: str, route: str) -> str:
    return f"## {title} — {route}\n"


def _manifest(server: Server, sid: str, turn: int, round_: int = 1) -> Manifest:
    data = server.turn_data(sid, turn, round_)
    return _parse_manifest(
        data.get("rendered_prompt") or "", data.get("template_feed") or {}
    )


def _parse_manifest(rendered: str, feed: dict) -> Manifest:
    manifest = Manifest(feed=feed)
    headers = [
        _manifest_header(t, str(feed.get(k, ""))) for _f, t, k in _MANIFEST_LANES
    ]
    spans, end = [], 0
    for i, header in enumerate(headers):
        # The last header is searched from the end: the user's text precedes it.
        at = (
            rendered.rfind(header)
            if i == len(headers) - 1
            else rendered.find(header, end)
        )
        if at < end:
            return manifest
        spans.append((at, at + len(header)))
        end = at + len(header)
    for i, (field_name, _title, _key) in enumerate(_MANIFEST_LANES):
        stop = spans[i + 1][0] if i + 1 < len(spans) else len(rendered)
        setattr(manifest, field_name, rendered[spans[i][1] : stop].removesuffix("\n"))
    manifest.headers = True
    return manifest


def _declared_routes(backend: str, l2_channel: str) -> dict[str, str]:
    """The lane routes ``backend`` declares (AgentFoundation's capability
    record), keyed like the prompt data."""
    from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.backend import (
        L2Channel,
    )
    from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.factory import (
        backend_class,
    )

    routes = backend_class(_native_kind(backend)).capabilities.prompt_routes(
        L2Channel(l2_channel)
    )
    return {
        "l1_route": routes.l1,
        "l2_route": routes.l2,
        "user_route": routes.user,
        "l3_route": routes.l3,
    }


def _persistent_process(backend: str) -> bool:
    """Whether ``backend`` keeps a vendor process between turns."""
    from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.factory import (
        backend_class,
    )

    return bool(backend_class(_native_kind(backend)).capabilities.persistent_process)


def _native_kind(backend: str) -> str:
    """The AgentFoundation backend kind of OpenStartup backend ``backend``."""
    from openteam.server.backends import factories

    return next(b.kind for b in factories._NATIVE_BACKENDS if b.name == backend)


def _make_toy_model(session_root: Path) -> None:
    toy = session_root / "toy_model"
    toy.mkdir(parents=True, exist_ok=True)
    (toy / "model.py").write_text(
        "import torch\n\n\nclass Ranker(torch.nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n"
        "        self.mlp = torch.nn.Linear(16, 1)\n\n"
        "    def forward(self, x):\n        return self.mlp(x)\n"
    )


def _write_proposals(session_root: Path) -> Path:
    """A research_propose-style ``proposals.json`` with two proposals."""
    path = session_root / "research" / "proposals.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    proposals = [
        {
            "id": "P1",
            "rank": 1,
            "title": "Add a hidden layer",
            "summary": "Replace the single linear layer with a two-layer MLP.",
            "impact": "high",
            "complexity": "low",
        },
        {
            "id": "P2",
            "rank": 2,
            "title": "Normalize inputs",
            "summary": "Add a LayerNorm before the MLP.",
            "impact": "medium",
            "complexity": "low",
        },
    ]
    index = {
        "version": "1",
        "total_count": len(proposals),
        "groups": [{"phase": 1, "label": "Quick Wins", "proposals": proposals}],
    }
    path.write_text(json.dumps(index, indent=2))
    return path


def _auto_advance_message(frame: dict) -> str:
    """The message the UI sends when a background task completes."""
    parts = [
        f"[System notification: Task '{frame.get('tool_name') or frame.get('task_id')}' "
        f"({frame.get('task_id')}) completed successfully.",
        f"Workspace: {frame['workspace']}." if frame.get("workspace") else "",
        f"Generated document: {frame['document_path']}."
        if frame.get("document_path")
        else "",
        f"Summary: {str(frame['result_summary'])[:300]}."
        if frame.get("result_summary")
        else "",
        f"Invoke the required `{frame['next_step_tool']}` conversation tool as "
        "specified in <SOPNextStepGuidance> above; do not default to a "
        "confirmation tool."
        if frame.get("next_step_tool")
        else "Refer to <SOPNextStepGuidance> above for the required next tool "
        "call; do not default to a confirmation tool.",
        "]",
    ]
    return " ".join(p for p in parts if p)


# ── Checks ───────────────────────────────────────────────────────────────


async def _chat_checks(c: Checks, server: Server, sid: str) -> None:
    async with Chat(server.port, sid) as chat:
        hello = (
            "Hi! In one sentence: who are you, and which host application are you "
            "working inside?"
        )
        log = await chat.turn(hello)
        turn = _turn_of(server, sid, hello)
        stored = _assistant_messages(server, sid, turn)
        c.check(
            "C1 'hi' → exactly one assistant bubble",
            log.status == "complete" and len(log.bubbles) == 1 and len(stored) == 1,
            f"{log.status} bubbles={len(log.bubbles)} stored={len(stored)}",
        )
        c.check(
            "C1 persona from the session instructions (names the host)",
            "agentfoundation" in log.text.lower().replace(" ", ""),
            log.text[:200],
        )
        record = _record(server, sid)
        c.check(
            "C1 native record persisted",
            bool(record.get("vendor_session_id")),
            str(record.get("backend")),
        )
        _view_prompt_checks(c, server, sid, turn, hello, record)

        log = await chat.turn(
            f"Remember this codeword for later: PELICAN-42. {_IN_CONVERSATION_ONLY}"
        )
        c.check(
            "C2 canary acknowledged",
            log.status == "complete" and bool(log.bubbles),
            f"{log.status} {log.text[:120]}",
        )

        log = await chat.turn("Which SOPs can you run? List their names only.")
        c.check(
            "C3 SOP catalog visible", "optimization" in log.text.lower(), log.text[:200]
        )

        await _cancel_checks(c, server, sid, chat)


def _view_prompt_checks(
    c: Checks, server: Server, sid: str, turn: int, user_text: str, record: dict
) -> None:
    """Plan §12.3 item 14: the turn's "View Prompt" shows the manifest."""
    manifest = _manifest(server, sid, turn)
    for name, ok, detail in _view_prompt_results(
        manifest, server.backend, user_text, record
    ):
        c.check(name, ok, detail)


def _view_prompt_results(
    manifest: Manifest, backend: str, user_text: str, record: dict
) -> list[tuple[str, bool, str]]:
    """C17 on a first turn's manifest: ``(check, passed, detail)`` each."""
    feed = manifest.feed
    declared = _declared_routes(backend, str(feed.get("l2_channel", "")))
    routes = {key: feed.get(key) for key in declared}
    return [
        (
            "C17 View Prompt names the backend and labels each lane with its route",
            feed.get("backend") == _native_kind(backend) and routes == declared,
            f"backend={feed.get('backend')!r} routes={routes!r}",
        ),
        (
            "C17 View Prompt shows every lane under its route header",
            manifest.headers,
            " | ".join(
                _manifest_header(t, str(feed.get(k))).strip()
                for _f, t, k in _MANIFEST_LANES
            )[:300],
        ),
        (
            "C17 View Prompt shows the session-instructions hash",
            bool(record.get("l1_core_hash"))
            and feed.get("l1_core_hash") == record.get("l1_core_hash"),
            f"{str(feed.get('l1_core_hash'))[:12]} vs {str(record.get('l1_core_hash'))[:12]}",
        ),
        (
            "C17 View Prompt shows the session instructions",
            "AgentFoundation host application" in manifest.l1,
            manifest.l1[:160],
        ),
        (
            "C17 View Prompt shows the turn context",
            manifest.l2.lstrip().startswith("<af_context"),
            repr(manifest.l2[:80]),
        ),
        (
            "C17 View Prompt shows the user's text verbatim",
            manifest.user == user_text,
            repr(manifest.user[:160]),
        ),
    ]


async def _cancel_checks(c: Checks, server: Server, sid: str, chat: Chat) -> None:
    async def cancel() -> None:
        await chat.send({"type": "cancel"})

    essay = "Write a detailed 800-word essay about the history of rivers."
    log = await chat.turn(essay, interrupt=cancel, interrupt_after_s=8.0)
    cancelled_turn = _turn_of(server, sid, essay)
    stored = _assistant_messages(server, sid, cancelled_turn)
    c.check(
        "C4 cancel mid-stream cancels the turn (no reply kept)",
        log.status == "Cancelled" and not log.bubbles and not stored,
        f"{log.status} bubbles={len(log.bubbles)} stored={len(stored)}",
    )
    await chat.drain(3.0)
    ok = "Reply with exactly the word OK and nothing else."
    log = await chat.turn(ok)
    c.check(
        "C4 next turn after cancel is clean",
        log.status == "complete"
        and "OK" in log.text.upper()
        and "river" not in log.text.lower()
        and len(log.text) < 80,
        log.text[:200],
    )
    l2 = _manifest(server, sid, _turn_of(server, sid, ok)).l2
    c.check(
        "C4 next turn's context carries the interrupted notice",
        '<notice type="interrupted">' in l2,
        l2[-300:],
    )


async def _restart_checks(c: Checks, server: Server, sid: str) -> None:
    before = _record(server, sid)
    code = server.stop()
    c.check("C5 graceful shutdown", code is not None, f"exit={code}")
    server.start(resume=True)
    async with Chat(server.port, sid) as chat:
        log = await chat.turn(
            "What codeword did I ask you to remember? Reply with just the codeword."
        )
        c.check(
            "C5 same vendor session remembers the codeword",
            "PELICAN-42" in log.text,
            log.text[:200],
        )
    after = _record(server, sid)
    c.check(
        "C5 vendor session resumed, not replaced",
        (after.get("vendor_session_id"), after.get("generation"))
        == (before.get("vendor_session_id"), before.get("generation")),
        f"{before.get('generation')}→{after.get('generation')}",
    )


async def _rewind_checks(c: Checks, server: Server, sid: str, claude: bool) -> None:
    list_prompt = (
        "List every codeword I asked you to remember, comma-separated, nothing else."
    )
    async with Chat(server.port, sid) as chat:
        await chat.turn(f"Remember a second codeword: OTTER-7. {_IN_CONVERSATION_ONLY}")
        log = await chat.turn(list_prompt)
        c.check(
            "C6 both codewords known",
            "OTTER-7" in log.text and "PELICAN-42" in log.text,
            log.text[:200],
        )
        await chat.turn(f"Remember a third codeword: FALCON-9. {_IN_CONVERSATION_ONLY}")
        before = _record(server, sid)
        mid = _user_message_id(server.session(sid), list_prompt)
        await chat.send({"type": "resume_from_turn", "message_id": mid})
        log = await chat.collect()
        print(f"<<< [resume {log.status}] {log.text[:300]!r}", flush=True)
        c.check(
            "C6 resume-from-turn re-runs the turn",
            log.status == "complete",
            f"{log.status} {log.errors}",
        )
        c.check(
            "C6 vendor forgot the dropped turns",
            "OTTER-7" in log.text and "FALCON-9" not in log.text,
            log.text[:200],
        )
        after = _record(server, sid)
        c.check(
            "C6 vendor session rewound (new generation)",
            after.get("generation", 0) > before.get("generation", 0),
            f"{before.get('generation')}→{after.get('generation')}",
        )
        old, new = (
            before.get("vendor_session_id", ""),
            after.get("vendor_session_id", ""),
        )
        c.check(
            "C6 the re-run turn runs in another vendor session",
            bool(old) and bool(new) and new != old,
            f"{old[:8]}→{new[:8]}",
        )
        l2 = _manifest(server, sid, _turn_of(server, sid, list_prompt)).l2
        if not claude:
            # No exact fork: a fresh session gets a recap of the kept turns.
            recap = _notice(l2, "recap") or ""
            c.check(
                "C6 recap rewind: the re-run turn's context recaps the kept turns only",
                "OTTER-7" in recap and "FALCON-9" not in recap,
                recap[-240:] or l2[-240:],
            )
            return
        c.check(*_exact_fork_result(old, new))
        log_text = server.log_path.read_text(errors="replace")
        c.check(
            "C6 rewound by an exact fork (no recap fallback)",
            "forking failed" not in log_text and _notice(l2, "recap") is None,
            l2[-200:],
        )
        await _compact_checks(c, server, sid, chat, list_prompt)


def _exact_fork_result(old: str, new: str) -> tuple[str, bool, str]:
    """Plan §12.3 item 9 on a Claude backend: the forked vendor session's
    transcript holds the turns before the rewound one, not the dropped ones
    (which the original session's transcript still holds)."""
    forked = _transcript_user_texts(_claude_transcript(new))
    original = _transcript_user_texts(_claude_transcript(old))

    def has(texts: list[str], word: str) -> bool:
        return any(word in t for t in texts)

    return (
        "C6 exact fork: the forked transcript keeps turn 'OTTER-7', not turn 'FALCON-9'",
        has(forked, "OTTER-7")
        and not has(forked, "FALCON-9")
        and has(original, "FALCON-9"),
        f"forked: {len(forked)} user texts, OTTER-7={has(forked, 'OTTER-7')} "
        f"FALCON-9={has(forked, 'FALCON-9')}; original FALCON-9={has(original, 'FALCON-9')}",
    )


async def _compact_checks(
    c: Checks, server: Server, sid: str, chat: Chat, list_prompt: str
) -> None:
    """Plan §12.3 item 12, ``/compact`` on a Claude backend: it compacts the
    vendor session and the next turn re-sends the turn context."""
    before = _record(server, sid)
    vsid = before.get("vendor_session_id", "")
    boundaries = _compact_boundaries(_claude_transcript(vsid))
    log = await chat.turn("/compact")
    c.check(
        "C6b vendor /compact passes through",
        log.status == "complete",
        f"{log.status} {log.errors}",
    )
    after = _record(server, sid)
    now = _compact_boundaries(_claude_transcript(vsid))
    c.check(
        "C6b /compact compacted the vendor session (new compact_boundary, same session)",
        after.get("vendor_session_id") == vsid and now > boundaries,
        f"compact_boundary {boundaries}→{now}",
    )
    c.check(
        "C6b /compact cleared the record's delivered turn-context hash",
        bool(before.get("l2_hash")) and not after.get("l2_hash"),
        f"{str(before.get('l2_hash'))[:16]!r}→{str(after.get('l2_hash'))[:16]!r}",
    )
    log = await chat.turn(list_prompt)
    c.check(
        "C6b codewords survive compaction",
        "OTTER-7" in log.text and "FALCON-9" not in log.text,
        log.text[:200],
    )
    l2 = _manifest(server, sid, _turn_of(server, sid, list_prompt)).l2
    c.check(
        "C6b the turn after /compact re-sends the turn context",
        l2.lstrip().startswith("<af_context"),
        repr(l2[:80]),
    )


async def _new_session_checks(c: Checks, server: Server, sid: str) -> None:
    async with Chat(server.port, sid) as chat:
        before = _record(server, sid)
        log = await chat.turn("/new")
        c.check(
            "C7 /new handled",
            log.status == "complete" and "new agent session" in log.text,
            f"{log.status} {log.text[:120]} {log.errors}",
        )
        log = await chat.turn(
            "What codeword did I ask you to remember? If you don't know, reply UNKNOWN."
        )
        after = _record(server, sid)
        c.check(
            "C7 /new starts a fresh vendor session",
            after.get("generation", 0) > before.get("generation", 0),
        )
        c.check(
            "C7 fresh session has no memory of the codeword",
            "PELICAN-42" not in log.text,
            log.text[:200],
        )


async def _clear_and_model_checks(
    c: Checks, server: Server, sid: str, model: str, other_model: Optional[str]
) -> None:
    """Plan §12.3 item 12: ``/clear`` and ``/model``."""
    async with Chat(server.port, sid) as chat:
        await chat.turn(f"Remember a new codeword: HERON-3. {_IN_CONVERSATION_ONLY}")
        before = _record(server, sid)
        log = await chat.turn("/clear")
        c.check(
            "C12 /clear handled",
            log.status == "complete" and "cleared" in log.text.lower(),
            f"{log.status} {log.text[:120]} {log.errors}",
        )
        ask = "What codeword did I just ask you to remember? If you don't know, reply UNKNOWN."
        log = await chat.turn(ask)
        after = _record(server, sid)
        c.check(
            "C12 /clear starts a new vendor session",
            after.get("generation", 0) > before.get("generation", 0)
            and bool(after.get("vendor_session_id"))
            and after.get("vendor_session_id") != before.get("vendor_session_id"),
            f"{before.get('generation')}→{after.get('generation')}",
        )
        l2 = _manifest(server, sid, _turn_of(server, sid, ask)).l2
        c.check(
            "C12 the new session gets no history (no recap, codeword unknown)",
            "HERON-3" not in log.text and 'type="recap"' not in l2,
            log.text[:200],
        )

        if not other_model:
            c.skip("C12 /model", "no --other-model for this backend")
            return
        for target, probe in ((other_model, "PING"), (model, "PONG")):
            log = await chat.turn(f"/model {target}")
            c.check(
                f"C12 /model {target} handled",
                log.status == "complete" and target in log.text,
                f"{log.status} {log.text[:120]} {log.errors}",
            )
            log = await chat.turn(
                f"Reply with exactly the word {probe} and nothing else."
            )
            record = _record(server, sid)
            applied = record.get("model")
            c.check(
                f"C12 /model {target} recorded for the vendor session",
                log.status == "complete" and applied == target,
                f"{log.status} record.model={applied!r}",
            )
            used = _vendor_model(server.backend, record.get("vendor_session_id", ""))
            if used is None:
                c.skip(
                    f"C12 /model {target} used by the vendor",
                    "no vendor session file to read the model from",
                )
                continue
            c.check(
                f"C12 /model {target} used by the vendor (its session file)",
                _model_matches(server.backend, target, used),
                f"latest turn's model={used!r}",
            )


async def _widget_cancel_checks(c: Checks, server: Server, sid: str) -> None:
    """Plan §12.3 item 6: cancel while a widget waits."""
    async with Chat(server.port, sid) as chat:
        ask = (
            "Ask me for my favorite color with the clarification question tool, then "
            "wait for my answer."
        )
        log = await chat.turn(ask, stop_on_widget=True)
        c.check(
            "C13 the question is shown as a widget",
            log.status == "widget",
            f"{log.status} {log.text[:120]}",
        )
        if log.status != "widget":
            return
        await chat.send({"type": "cancel"})
        log = await chat.collect(continuing=True)
        c.check(
            "C13 cancel while the widget waits cancels the turn",
            log.status == "Cancelled",
            log.status,
        )
        await chat.drain(2.0)
        follow_up = (
            "Never mind the color. Reply with exactly the word FINE and nothing else."
        )
        log = await chat.turn(follow_up)
        l2 = _manifest(server, sid, _turn_of(server, sid, follow_up)).l2
        c.check(
            "C13 next turn's context says the question was cancelled",
            log.status == "complete" and '<notice type="widget_cancelled">' in l2,
            f"{log.status} {l2[-300:]}",
        )


async def _hub_handoff_checks(
    c: Checks, server: Server, sid: str, session_root: Path
) -> None:
    """Plan §12.3 item 11: proposal selection hands off to the Experiment Hub."""
    proposals = _write_proposals(session_root)
    async with Chat(server.port, sid) as chat:
        ask = (
            f"The research proposals for my model are in {proposals}. Let me pick "
            "which to pursue: show them with the proposal selection question tool, "
            "with the Experiment Hub enabled (experiment_hub true) and proposals_path "
            "set to that file. Do nothing else."
        )
        log = await chat.turn(ask, stop_on_widget=True)
        widget = log.widgets[-1] if log.widgets else {}
        meta = _widget_metadata(widget)
        c.check(
            "C14 proposal_selection widget routed to the Experiment Hub",
            log.status == "widget"
            and meta.get("widget_type") == "proposal_selection"
            and meta.get("open_dashboard") == "experiment_hub",
            f"{log.status} widget_type={meta.get('widget_type')} "
            f"open_dashboard={meta.get('open_dashboard')}",
        )
        if log.status != "widget":
            return
        # Exactly what the hub's in-hub confirm resolves the widget with.
        await chat.answer(widget, {"selected_proposals": ["P1"]})
        log = await chat.collect(continuing=True)
        opened = log.of_type("dashboard_open")
        c.check(
            "C14 the answer opens the Experiment Hub (dashboard directive)",
            bool(opened),
            f"{[f.get('hub_id') for f in opened]}",
        )
        c.check(
            "C14 quiet handoff: the turn ends with no further bubble",
            log.status == "complete" and not log.bubbles,
            f"{log.status} {log.text[:200]}",
        )


async def _sop_widget_checks(
    c: Checks, server: Server, sid: str, session_root: Path, async_timeout: float
) -> None:
    # The fast investigation keeps C15 (understand_codebase completes and
    # auto-advances the SOP) within --sop-async-timeout.
    request = (
        f"Start the model optimization SOP for the model codebase at "
        f"{session_root / 'toy_model'}. It is a one-file toy model: when the "
        "SOP runs understand_codebase, pass docs_only true and model haiku."
    )
    async with Chat(server.port, sid) as chat:
        log = await chat.turn(request, stop_on_widget=True)
        c.check(
            "C8 SOP entry presents a widget",
            log.status == "widget",
            f"{log.status} {log.text[:200]}",
        )
        if log.status != "widget":
            return
        first = log.widgets[0]
        types = _widget_tool_types(first)
        c.check(
            "C8 Phase 0a asks clarification and single_choice together",
            {"clarification", "single_choice"} <= set(types),
            ",".join(types),
        )
        widget_turn = first.get("turn_number")
    # Page refresh while the widget waits: the server re-displays it from the
    # durable marker and the answer is applied without re-inference.
    async with Chat(server.port, sid) as chat:
        shown = [f for f in chat.on_connect if f.get("type") == "pending_input"]
        c.check(
            "C9 widget re-displayed after refresh",
            bool(shown) and shown[-1].get("turn_number") == widget_turn,
            f"{len(chat.on_connect)} frames",
        )
        if not shown:
            return
        await chat.answer(shown[-1], answer_widget(shown[-1]))
        log = await chat.collect(answer=answer_widget, timeout=_TURN_TIMEOUT_S)
        print(f"<<< [recovered {log.status}] {log.text[:300]!r}", flush=True)
        c.check(
            "C9 recovered turn completes",
            log.status == "complete",
            f"{log.status} {log.errors}",
        )
        if isinstance(widget_turn, int):
            c.check(*_continuation_in_widget_turn(server, sid, widget_turn))
            c.check(*_phase_0b_after_answer(server, sid, widget_turn))
        sop = server.session(sid).get("sop_state") or {}
        c.check(
            "C9 SOP advanced past setup",
            sop.get("sop_name") == "model_optimization"
            and bool(sop.get("completed_phases")),
            f"phase={sop.get('current_phase')} done={sop.get('completed_phases')}",
        )
        await _async_auto_advance_checks(c, server, sid, chat, log, async_timeout)


def _continuation_in_widget_turn(
    server: Server, sid: str, turn: int
) -> tuple[str, bool, str]:
    """The recovered answer continues the widget's turn in new rounds; no
    new turn is allocated."""

    def summary(n: int) -> dict:
        r = requests.get(server.url(f"/api/sessions/{sid}/turns/{n}"), timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    current, following = summary(turn), summary(turn + 1)
    ok = (current.get("latest_round") or 0) >= 2 and "note" in following
    return (
        "C9 continuation stays in the widget's turn, in new rounds",
        ok,
        f"turn {turn} latest_round={current.get('latest_round')}; next={following.get('note', 'exists')}",
    )


def _phase_0b_after_answer(
    server: Server, sid: str, turn: int
) -> tuple[str, bool, str]:
    """Plan §12.3 item 3: the vendor turn that delivers the Phase 0a answers
    (the first round of the widget's turn with another manifest than round
    1's) tells the agent, in its turn context, that Phase 0b is now active."""
    first = _manifest(server, sid, turn, 1)
    r = requests.get(server.url(f"/api/sessions/{sid}/turns/{turn}"), timeout=10)
    latest = int(r.json()["data"].get("latest_round") or 0)
    answer = next(
        (
            m
            for m in (_manifest(server, sid, turn, n) for n in range(2, latest + 1))
            if m.headers and m.user != first.user
        ),
        None,
    )
    l2 = answer.l2 if answer else ""
    status = re.findall(r"Current Phase \([^)]*\)", l2)
    ok = (
        "Current Phase (0b " in l2
        and re.search(r"^0a .*✓ \(done\)$", l2, re.M) is not None
    )
    return (
        "C8 after the Phase 0a answers the next vendor turn's context has Phase 0b active",
        ok,
        f"rounds 2..{latest}: answer manifest {'found' if answer else 'missing'}; "
        f"status={status} {l2[:120]!r}",
    )


def _host_event_result(
    server: Server, sid: str, advance: str, label: str
) -> tuple[str, bool, str]:
    """The auto-advance turn is persisted as a host notification and the
    vendor is told so: ``origin="host_event"`` in its turn context."""
    name = (
        f"{label}: the auto-advance turn is a host event (origin in its turn context)"
    )
    try:
        message = _user_message(server.session(sid), advance)
    except KeyError:
        return (name, False, "the auto-advance message is not in the session")
    l2 = _manifest(server, sid, int(message["turn_number"])).l2
    origin = re.search(r'<af_context [^>]*origin="([^"]*)"', l2)
    flagged = (message.get("metadata") or {}).get("is_auto_advance") is True
    return (
        name,
        flagged and origin is not None and origin.group(1) == "host_event",
        f"is_auto_advance={flagged} origin={origin.group(1) if origin else None!r}",
    )


async def _async_auto_advance_checks(
    c: Checks,
    server: Server,
    sid: str,
    chat: Chat,
    sop_turn: TurnLog,
    async_timeout: float,
) -> None:
    """Plan §12.3 item 10 within the SOP: its async ``understand_codebase``
    ends the turn; its completion auto-advances the SOP."""

    def is_uc(frame: dict) -> bool:
        return frame.get("tool_name") == "understand_codebase"

    started = [f for f in sop_turn.of_type("task_status") if is_uc(f)]
    finished = [f for f in sop_turn.of_type("task_completed") if is_uc(f)]
    c.check(
        "C15 async understand_codebase started; the turn ended before it finished",
        sop_turn.status == "complete" and bool(started) and not finished,
        f"{sop_turn.status} started={[f.get('status') for f in started]} "
        f"finished={len(finished)} request={started[0].get('request') if started else ''!r}",
    )
    if not started:
        return
    if async_timeout <= 0:
        c.skip(
            "C15 understand_codebase completion auto-advances the SOP",
            "opt-in (~25 min even docs-only on haiku); pass --sop-async-timeout 2400",
        )
        return
    print(f"    [async] waiting up to {async_timeout:.0f}s for understand_codebase")
    waited = time.monotonic()
    done = await chat.wait_for(
        lambda f: f.get("type") == "task_completed" and is_uc(f), async_timeout
    )
    c.check(
        "C15 understand_codebase completed",
        done is not None,
        f"after {time.monotonic() - waited:.0f}s",
    )
    if done is None:
        return
    advance = _auto_advance_message(done)
    print(f"\n>>> (auto-advance) {advance[:200]}", flush=True)
    await chat.send({"type": "message", "content": advance, "is_auto_advance": True})
    log = await chat.collect(stop_on_widget=True)
    types = [t for w in log.widgets for t in _widget_tool_types(w)]
    c.check(
        "C15 the auto-advance turn continues the SOP (Phase 1b confirmation)",
        log.status == "widget" and "confirmation" in types,
        f"{log.status} widgets={types} {log.text[:160]}",
    )
    c.check(*_host_event_result(server, sid, advance, "C15"))


async def _async_task_checks(
    c: Checks, server: Server, sid: str, work_dir: Path, timeout: float
) -> None:
    """Plan §12.3 item 10: an async AF tool ends the turn; its completion
    auto-advances the conversation (as the UI does on ``task_completed``)."""
    target = work_dir / "async_hello.txt"
    async with Chat(server.port, sid) as chat:
        log = await chat.turn(
            f"Use the AF task tool in execute mode (skip planning) with model haiku "
            f"to create the file {target} containing exactly the word hello. Do "
            "nothing else."
        )
        started = [
            f for f in log.of_type("task_status") if f.get("tool_name") == "task"
        ]
        done_in_turn = [
            f for f in log.of_type("task_completed") if f.get("tool_name") == "task"
        ]
        c.check(
            "C19 async task started; the turn ended before it finished",
            log.status == "complete" and bool(started) and not done_in_turn,
            f"{log.status} started={[f.get('status') for f in started]} "
            f"finished={len(done_in_turn)}",
        )
        if not started:
            return
        print(f"    [async] waiting up to {timeout:.0f}s for the task", flush=True)
        done = await chat.wait_for(
            lambda f: f.get("type") == "task_completed"
            and f.get("tool_name") == "task",
            timeout,
        )
        c.check(
            "C19 the task completed and did its work",
            done is not None and target.is_file() and "hello" in target.read_text(),
            f"completed={done is not None} file={target.is_file()}",
        )
        if done is None:
            return
        advance = _auto_advance_message(done)
        print(f"\n>>> (auto-advance) {advance[:200]}", flush=True)
        await chat.send(
            {"type": "message", "content": advance, "is_auto_advance": True}
        )
        log = await chat.collect()
        c.check(
            "C19 the auto-advance turn continues the conversation",
            log.status == "complete" and bool(log.bubbles) and not log.widgets,
            f"{log.status} {log.text[:200]!r} {log.errors}",
        )
        c.check(*_host_event_result(server, sid, advance, "C19"))


async def _yolo_checks(
    c: Checks, server: Server, backend: str, model: str, session_root: Path
) -> None:
    """Plan §12.3 item 4: in yolo mode widgets are answered inline."""
    sid = server.create_session("native-e2e-yolo")
    r = server.select_backend(sid, backend, model)
    if not c.check("C16 yolo session ready", r.ok, r.text[:200]):
        return
    try:
        async with Chat(server.port, sid) as chat:
            log = await chat.turn(
                "/sop model_optimization --yolo Optimize the model codebase at "
                f"{session_root / 'toy_model'}."
            )
            ask = "Which path is this SOP working on? Reply with the path only."
            await chat.turn(ask)
        sop = server.session(sid).get("sop_state") or {}
        done = set(sop.get("completed_phases") or [])
        c.check(
            "C16 yolo answers the widgets inline (no pending input)",
            log.status == "complete" and not log.widgets,
            f"{log.status} widgets={len(log.widgets)} {log.errors}",
        )
        c.check(
            "C16 yolo SOP advanced past its input phases",
            sop.get("yolo_mode") is True and {"0a", "0b"} <= done,
            f"yolo={sop.get('yolo_mode')} done={sorted(done)} phase={sop.get('current_phase')}",
        )
        # The SOP context names the target path the yolo answer set.
        l2 = _manifest(server, sid, _turn_of(server, sid, ask)).l2
        target = re.search(r"You operate on (\S+) under repository", l2)
        c.check(
            "C16 yolo answers keep the path the user gave",
            target is not None and target.group(1).rstrip("/").endswith("toy_model"),
            f"SOP target={target.group(1) if target else None!r}",
        )
    finally:
        _delete_checks(c, server, sid, "C16 yolo session")


async def _sop_slash_checks(c: Checks, server: Server, sid: str) -> None:
    """Tool-less backends: SOPs are entered with slash commands."""
    async with Chat(server.port, sid) as chat:
        log = await chat.turn("/sop model_optimization")
        c.check(
            "C18 /sop enters the SOP",
            log.status == "complete" and "model_optimization" in log.text,
            f"{log.status} {log.text[:160]} {log.errors}",
        )
        ask = "Which SOP is active right now? Answer with its name only."
        log = await chat.turn(ask)
        l2 = _manifest(server, sid, _turn_of(server, sid, ask)).l2
        c.check(
            "C18 next turn's context shows the active SOP",
            "## Active SOP Context" in l2 and "No SOP is active." not in l2,
            l2[:200],
        )
        c.check(
            "C18 the agent sees the active SOP",
            "optimization" in log.text.lower(),
            log.text[:200],
        )


async def _switch_checks(
    c: Checks,
    server: Server,
    sid: str,
    *,
    backend: str,
    model: str,
    switch_backend: str,
    switch_model: str,
) -> None:
    if _persistent_process(backend):
        # A turn first, so an idle-closed session process is running again.
        async with Chat(server.port, sid) as chat:
            await chat.turn(
                "Without using any tools, reply with exactly the word HERE and "
                "nothing else."
            )
    before = _record(server, sid)
    old = before.get("vendor_session_id", "")
    if _persistent_process(backend):
        live = _processes_mentioning(old)
        c.check(
            "C10 before the switch the backend's vendor process is running",
            bool(old) and bool(live),
            f"session {old[:8]}: {live[:2]}",
        )
    r = server.select_backend(sid, switch_backend, switch_model)
    c.check(f"C10 switched to {switch_backend}", r.ok, r.text[:200])
    left = await _wait_until_none(lambda: _processes_mentioning(old), 30.0)
    c.check(
        "C10 leaving the backend left no process of its vendor session",
        bool(old) and not left,
        f"session {old[:8]}: {left[:2]}",
    )
    ready = (
        "Without using any tools, reply with exactly the word READY and nothing else."
    )
    async with Chat(server.port, sid) as chat:
        log = await chat.turn(ready)
    c.check(
        f"C10 {switch_backend} answers",
        log.status == "complete" and "READY" in log.text.upper(),
        f"{log.status} {log.text[:120]!r} {log.errors}",
    )
    record = _record(server, sid)
    if switch_backend in _native_backends():
        c.check(
            "C10 leaving the backend ended its vendor session",
            bool(record.get("vendor_session_id"))
            and record.get("vendor_session_id") != before.get("vendor_session_id"),
            f"{record.get('backend')} generation={record.get('generation')}",
        )
    else:
        c.check(
            "C10 leaving native ended the vendor session",
            not record.get("vendor_session_id"),
            str(record.get("generation")),
        )
    r = server.select_backend(sid, backend, model)
    c.check(f"C10 switched back to {backend}", r.ok, r.text[:200])
    async with Chat(server.port, sid) as chat:
        which = "Which SOP is active right now? Answer with its name only."
        log = await chat.turn(which)
        c.check(
            "C10 SOP state kept across switches",
            "optimization" in log.text.lower(),
            log.text[:200],
        )
        recap = _notice(
            _manifest(server, sid, _turn_of(server, sid, which)).l2, "recap"
        )
        c.check(
            "C10 the first turn back carries a recap with the other backend's turn",
            recap is not None and ready in recap,
            (recap or "no recap notice")[-240:],
        )
        log = await chat.turn(
            "What was the last thing I asked the other assistant to reply with? One word."
        )
        c.check(
            "C10 recap carries the other backend's turn",
            "READY" in log.text.upper(),
            log.text[:200],
        )


def _delete_checks(c: Checks, server: Server, sid: str, label: str) -> None:
    """Deleting a session stops its work and leaves nothing on disk."""
    r = requests.delete(server.url(f"/api/sessions/{sid}"), timeout=180)
    c.check(f"{label} deleted", r.ok, r.text[:120])
    leftovers = sorted(
        str(p.relative_to(server.runtime_dir))
        for p in server.runtime_dir.glob(f"servers/*/sessions/{sid}_*")
    )
    c.check(f"{label}: no session directory left", not leftovers, str(leftovers))
    stuck = f"Background tasks of session {sid} did not stop"
    c.check(
        f"{label}: its background tasks stopped when it was deleted",
        stuck not in server.log_path.read_text(errors="replace"),
    )


def _native_backends() -> set[str]:
    from openteam.server.backends import get_registry

    return {n for n, d in get_registry().list_backends().items() if d.native}


async def _run(args: argparse.Namespace, c: Checks) -> None:
    runtime_dir = Path(tempfile.mkdtemp(prefix="os_native_e2e_"))
    work_dir = runtime_dir / "work"
    work_dir.mkdir()
    print(f"[runtime] {runtime_dir}", flush=True)
    server = Server(runtime_dir, work_dir, args.backend, args.model)
    server.start()
    try:
        sid = server.create_session("native-e2e")
        r = server.select_backend(sid, args.backend, args.model)
        c.check("C0 backend selected", r.ok, r.text[:200])
        session_root = Path(server.session(sid).get("session_root_path") or work_dir)
        _make_toy_model(session_root)

        await _chat_checks(c, server, sid)
        await _restart_checks(c, server, sid)
        await _rewind_checks(c, server, sid, claude=args.backend in _CLAUDE_BACKENDS)
        await _new_session_checks(c, server, sid)
        await _clear_and_model_checks(c, server, sid, args.model, args.other_model)
        if args.tool_less:
            for name in (
                "C13 cancel while a widget waits",
                "C14 Experiment Hub handoff",
            ):
                c.skip(name, "needs AgentFoundation tools")
            for name in ("C8/C9/C15/C19 SOP widgets + async tools", "C16 yolo"):
                c.skip(name, "needs AgentFoundation tools")
            await _sop_slash_checks(c, server, sid)
        else:
            await _widget_cancel_checks(c, server, sid)
            await _hub_handoff_checks(c, server, sid, session_root)
            await _async_task_checks(c, server, sid, work_dir, args.task_timeout)
            await _yolo_checks(c, server, args.backend, args.model, session_root)
            await _sop_widget_checks(
                c, server, sid, session_root, args.sop_async_timeout
            )
        if not args.skip_switch:
            await _switch_checks(
                c,
                server,
                sid,
                backend=args.backend,
                model=args.model,
                switch_backend=args.switch_backend,
                switch_model=args.switch_model,
            )

        _delete_checks(c, server, sid, "C11 session")
    finally:
        code = server.stop()
        c.check("C11 graceful shutdown at the end", code is not None, f"exit={code}")
        leftover = await _wait_until_none(
            lambda: _vendor_processes_under(runtime_dir), 15.0
        )
        c.check(
            "C11 no process left running in the run's directories after shutdown",
            not leftover,
            f"{len(leftover)}: {leftover[:3]}",
        )
        log = server.log_path.read_text(errors="replace")
        failures = [m for m in _CLOSE_FAILURES if m in log]
        c.check("C11 no session-close failures logged", not failures, str(failures))
        print(f"[log] {server.log_path}", flush=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="native_claude_sdk")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument(
        "--other-model",
        default=None,
        help="A second model for the /model check (default: per backend).",
    )
    parser.add_argument(
        "--tool-less",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Skip the tool-driven checks (default: on for Metamate).",
    )
    parser.add_argument(
        "--switch-backend",
        default=None,
        help="Backend for the switch check (default: claude_cli, or "
        "native_claude_sdk for tool-less backends).",
    )
    parser.add_argument(
        "--switch-model",
        default=None,
        help="Its model (default: haiku for claude_cli — the classic prompt is "
        "refused by some Claude models — else --model).",
    )
    parser.add_argument("--skip-switch", action="store_true")
    parser.add_argument(
        "--task-timeout",
        type=float,
        default=5400.0,
        help="Seconds to wait for the async task (C19); even a one-file task "
        "runs the full implement/review topology (45+ min).",
    )
    parser.add_argument(
        "--sop-async-timeout",
        type=float,
        default=_SOP_ASYNC_TIMEOUT_S,
        help="Seconds to wait for the SOP's async understand_codebase (asked "
        "to run docs-only on haiku: ~25 min) before checking the "
        "auto-advanced SOP (default 0 = skip that check).",
    )
    args = parser.parse_args()
    if args.other_model is None:
        pair = _MODEL_PAIRS.get(args.backend, ())
        args.other_model = next((m for m in pair if m != args.model), None)
    if args.tool_less is None:
        args.tool_less = args.backend in _TOOL_LESS_BACKENDS
    if args.switch_backend is None:
        args.switch_backend = "native_claude_sdk" if args.tool_less else "claude_cli"
    if args.switch_model is None:
        args.switch_model = "haiku" if args.switch_backend == "claude_cli" else "sonnet"
    return args


def main() -> int:
    args = _parse_args()

    from openteam.server.backends import get_registry

    descriptor = get_registry().list_backends().get(args.backend)
    if descriptor is None or not descriptor.native:
        print(f"SKIP: {args.backend} is not a native backend")
        return 77
    if not descriptor.is_available():
        print(f"SKIP: {descriptor.status_message()}")
        return 77
    checks = Checks()
    asyncio.run(_run(args, checks))
    return checks.summary()


if __name__ == "__main__":
    sys.exit(main())
