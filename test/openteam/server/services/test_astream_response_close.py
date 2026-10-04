"""Closing ``astream_response`` closes the backend stream it consumes.

``async for`` never closes the generator it iterates, so without an explicit
close the backend stream stays suspended until asyncio's GC hook finalizes it
from another task. The backend's ``finally`` must instead run synchronously,
in the consumer's task, when the consumer closes the response stream.
"""

from __future__ import annotations

import asyncio

import pytest
from openteam.server.services.conversation_service import ConversationService


class _RecordingInferencer:
    """Backend stand-in: streams two chunks and records where it was closed."""

    def __init__(self):
        self.closed_in_task = None
        self.messages = []

    def set_messages(self, messages):
        self.messages = list(messages)

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    async def ainfer_streaming(self, inp, run_context=None):
        try:
            yield "first "
            yield "second"
        finally:
            self.closed_in_task = asyncio.current_task()


def _service_with(inferencer, sid):
    svc = ConversationService.__new__(ConversationService)
    svc._llm_backend = "recording"
    svc._llm_model = None
    svc._inferencers = {sid: inferencer}
    return svc


@pytest.mark.asyncio
async def test_closing_response_stream_closes_backend_stream_in_consumer_task():
    backend = _RecordingInferencer()
    svc = _service_with(backend, "s1")

    stream = svc.astream_response({"id": "s1", "messages": []}, "hi")
    assert await stream.__anext__() == "first "
    await stream.aclose()

    assert backend.closed_in_task is asyncio.current_task()


@pytest.mark.asyncio
async def test_exhausted_response_stream_records_the_turn():
    backend = _RecordingInferencer()
    svc = _service_with(backend, "s1")

    chunks = [c async for c in svc.astream_response({"id": "s1", "messages": []}, "hi")]

    assert chunks == ["first ", "second"]
    assert backend.closed_in_task is asyncio.current_task()
    assert backend.messages[-2:] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "first second"},
    ]
