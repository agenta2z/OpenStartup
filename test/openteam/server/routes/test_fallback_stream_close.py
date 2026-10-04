"""The websocket fallback turn closes ``astream_response`` when delivery stops.

A turn task is cancelled by a new message or a disconnect while it awaits a
send. The response stream it was iterating must unwind in that task, not later
from asyncio's GC hook in another task.
"""

from __future__ import annotations

import asyncio

import pytest
from openteam.server.routes.manager_websocket_routes import _stream_fallback_tokens


class _RecordingConversationService:
    def __init__(self):
        self.closed_in_task = None

    async def astream_response(self, session, text):
        try:
            yield "hello"
            yield " world"
        finally:
            self.closed_in_task = asyncio.current_task()


@pytest.mark.asyncio
async def test_cancelled_turn_closes_response_stream_in_turn_task():
    conv_svc = _RecordingConversationService()
    first_sent = asyncio.Event()

    async def blocking_send(msg):
        first_sent.set()
        await asyncio.Event().wait()

    async def turn():
        return await _stream_fallback_tokens(conv_svc, {}, "hi", blocking_send)

    turn_task = asyncio.create_task(turn())
    await first_sent.wait()
    turn_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await turn_task

    assert conv_svc.closed_in_task is turn_task


@pytest.mark.asyncio
async def test_fallback_sends_each_chunk_and_returns_the_text():
    conv_svc = _RecordingConversationService()
    sent = []

    async def capture(msg):
        sent.append(msg)

    text = await _stream_fallback_tokens(conv_svc, {}, "hi", capture)

    assert text == "hello world"
    assert sent == [
        {
            "type": "token",
            "content": chunk,
            "metadata": {"agent_name": "Orchestrator"},
        }
        for chunk in ("hello", " world")
    ]
    assert conv_svc.closed_in_task is asyncio.current_task()
