"""Tests for WebSocketInteractive per-round event stamping + pending_input cache.

Covers:
- set_round_context / current_message_id
- stream_token_batches stamping token messages with {message_id, round_index}
- on_clean_output_available → stream_correction carries the same stamping
- asend_response minting pending_input_id, stamping {message_id, round_index,
  turn_number}, and writing a scope=="conversation" pending_input_cache entry
  with prompt/input_mode/view metadata
- send_round_message_end emitting the balanced terminal message_end
- the dev-tool path (NO round context) writes NO cache entry

Mirrors the construction style of the sibling test_websocket_interactive.py:
a fake async send callback that captures emitted messages.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import pytest

from agent_foundation.ui.input_modes import ChoiceOption, InputModeConfig, InputMode
from openteam.server.services.websocket_interactive import WebSocketInteractive


def _make_interactive(pending_input_cache: dict | None = None):
    """Build a WebSocketInteractive with a capturing send callback.

    Returns (interactive, sent) where ``sent`` is the list of emitted messages.
    """
    sent: list[dict[str, Any]] = []

    async def _capture(msg: dict) -> None:
        sent.append(msg)

    interactive = WebSocketInteractive(
        _capture,
        asyncio.Queue(),
        pending_input_cache=pending_input_cache,
    )
    return interactive, sent


async def _token_stream(chunks: list[str]) -> AsyncIterator[tuple[str, dict]]:
    for c in chunks:
        yield c, {}


_ROUND_CTX = {
    "message_id": "m1",
    "round_index": 1,
    "turn_number": 1,
    "session_id": "s",
}


def _compound_input_mode() -> InputModeConfig:
    """A clarification/compound single-choice mode carrying view metadata."""
    return InputModeConfig(
        mode=InputMode.SINGLE_CHOICE,
        prompt="Pick a plan",
        options=[
            ChoiceOption(label="Approve", value="approve"),
            ChoiceOption(label="Revise", value="revise"),
        ],
        metadata={
            "viewPath": "/plan/123",
            "viewLabel": "Plan 123",
            "viewType": "plan",
        },
    )


class TestSetRoundContext:
    def test_current_message_id(self):
        interactive, _ = _make_interactive()
        assert interactive.current_message_id is None
        interactive.set_round_context(dict(_ROUND_CTX))
        assert interactive.current_message_id == "m1"

    def test_set_round_context_resets_clean_output(self):
        interactive, _ = _make_interactive()
        interactive._clean_output = "stale"
        interactive.set_round_context(dict(_ROUND_CTX))
        assert interactive.clean_output is None

    def test_clear_round_context(self):
        interactive, _ = _make_interactive()
        interactive.set_round_context(dict(_ROUND_CTX))
        interactive.set_round_context(None)
        assert interactive.current_message_id is None


class TestTokenStamping:
    @pytest.mark.asyncio
    async def test_tokens_carry_message_id_and_round_index(self):
        interactive, sent = _make_interactive()
        interactive.set_round_context(dict(_ROUND_CTX))

        full = await interactive.stream_token_batches(
            _token_stream(["hel", "lo"]), session_id="s"
        )
        assert full == "hello"
        token_msgs = [m for m in sent if m["type"] == "token"]
        assert token_msgs, "expected at least one token message"
        for m in token_msgs:
            assert m["message_id"] == "m1"
            assert m["round_index"] == 1

    @pytest.mark.asyncio
    async def test_tokens_unstamped_without_round_context(self):
        interactive, sent = _make_interactive()
        await interactive.stream_token_batches(
            _token_stream(["hi"]), session_id="s"
        )
        token_msgs = [m for m in sent if m["type"] == "token"]
        assert token_msgs
        for m in token_msgs:
            assert "message_id" not in m
            assert "round_index" not in m


class TestStreamCorrectionStamping:
    @pytest.mark.asyncio
    async def test_clean_output_emits_stamped_stream_correction(self):
        interactive, sent = _make_interactive()
        interactive.set_round_context(dict(_ROUND_CTX))

        await interactive.on_clean_output_available("clean text")

        corr = [m for m in sent if m["type"] == "stream_correction"]
        assert len(corr) == 1
        assert corr[0]["content"] == "clean text"
        assert corr[0]["message_id"] == "m1"
        assert corr[0]["round_index"] == 1
        assert interactive.clean_output == "clean text"


class TestPendingInputMintingAndCache:
    @pytest.mark.asyncio
    async def test_pending_input_stamped_and_cached(self):
        cache: dict[str, Any] = {}
        interactive, sent = _make_interactive(pending_input_cache=cache)
        interactive.set_round_context(dict(_ROUND_CTX))

        mode = _compound_input_mode()
        await interactive.asend_response(
            "Need your decision", flag="PendingInput", input_mode=mode
        )

        pend = [m for m in sent if m["type"] == "pending_input"]
        assert len(pend) == 1
        msg = pend[0]

        # Per-round identity stamped onto the emitted message.
        assert msg["message_id"] == "m1"
        assert msg["round_index"] == 1
        assert msg["turn_number"] == 1
        # A fresh pending_input_id was minted.
        pid = msg["pending_input_id"]
        assert isinstance(pid, str) and pid
        # input_mode was serialized via to_dict().
        assert msg["input_mode"]["mode"] == "single_choice"

        # Cache entry keyed by pending_input_id, scope conversation, with the
        # prompt / input_mode / view metadata.
        assert pid in cache
        entry = cache[pid]
        assert entry["scope"] == "conversation"
        assert entry["session_id"] == "s"
        assert entry["turn_number"] == 1
        assert entry["round_index"] == 1
        assert entry["message_id"] == "m1"
        assert entry["pending_input_id"] == pid
        assert entry["prompt"] == "Need your decision"
        assert entry["input_mode"]["mode"] == "single_choice"
        assert entry["viewPath"] == "/plan/123"
        assert entry["viewLabel"] == "Plan 123"
        assert entry["viewType"] == "plan"

    @pytest.mark.asyncio
    async def test_pending_input_no_cache_entry_without_round_context(self):
        """Dev-tool path: no round context → mint id but write NO cache entry."""
        cache: dict[str, Any] = {}
        interactive, sent = _make_interactive(pending_input_cache=cache)
        # NOTE: set_round_context NOT called.

        mode = _compound_input_mode()
        await interactive.asend_response(
            "Need your decision", flag="PendingInput", input_mode=mode
        )

        pend = [m for m in sent if m["type"] == "pending_input"]
        assert len(pend) == 1
        msg = pend[0]
        # Still mints a pending_input_id...
        assert msg["pending_input_id"]
        # ...but carries no per-round identity.
        assert "message_id" not in msg
        assert "round_index" not in msg
        assert "turn_number" not in msg
        # And writes NO cache entry.
        assert cache == {}


class TestSendRoundMessageEnd:
    @pytest.mark.asyncio
    async def test_message_end_shape(self):
        interactive, sent = _make_interactive()
        await interactive.send_round_message_end(
            message_id="m1",
            round_index=1,
            turn_number=1,
            final_content="done",
        )
        assert len(sent) == 1
        msg = sent[0]
        assert msg["type"] == "message_end"
        assert msg["message_id"] == "m1"
        assert msg["round_index"] == 1
        assert msg["turn_number"] == 1
        assert msg["final_content"] == "done"
