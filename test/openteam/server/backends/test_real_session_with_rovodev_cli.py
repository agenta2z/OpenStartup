"""Real-CLI integration test: production CI factory + rovodev + 'hello'.

Mirrors the OpenStartup session path that failed in production
(server_20260615_194631_8e0863a8, turn_002, "hello") AS CLOSELY as the
in-process test boundary allows:

  * Uses the EXACT production factory ``_rovodev_factory`` (not a hand-rolled
    construction), which transitively invokes ``_wrap_in_conversational`` —
    the same path the running server uses for every /chat turn.
  * Builds a real ``BackendBuildContext`` with a real templates_dir, real
    working_dir, real cache_dir — the same shape the server passes.
  * Calls ``await ci.run_agentic_loop("hello", interactive=...)`` — the
    same call ``ConversationService.run_conversation_turn`` makes.

Assertions verify the same documented contract the test
``test/agent_foundation/.../test_real_hello_rovodecli.py`` covers, but
through the OpenStartup factory layer instead of bypassing it:

  1. ``base.get_final_output()`` is non-empty (rovodev wrote --output-file
     successfully when invoked through the OpenStartup factory chain).
  2. ``base.get_final_output()`` is NOT the rovodev TUI startup banner.
  3. ``base._last_clean_output`` mirrors ``get_final_output()``.
  4. The CI returned a non-empty ``AgenticResult.raw_response`` (even if
     noisy — the UI uses ``stream_correction`` to overwrite with clean).

Skipped if ``acli`` is not on PATH (CI-safe).

Run:
    pytest test/openteam/server/backends/test_real_session_with_rovodev_cli.py -v -s
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Path setup — make src/openteam importable + RichPythonUtils + AgentFoundation
# This mirrors the same import resolution the real server uses (uv install).
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
# parents: [0]=backends, [1]=server, [2]=openteam, [3]=test, [4]=OpenStartup
_OPENSTARTUP_ROOT = _HERE.parents[4]
_CORE_PROJECTS = _OPENSTARTUP_ROOT.parent

for _candidate in (
    _OPENSTARTUP_ROOT / "src",
    _CORE_PROJECTS / "AgentFoundation" / "src",
    _CORE_PROJECTS / "RichPythonUtils" / "src",
):
    p = str(_candidate)
    if _candidate.is_dir() and p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Skip gate
# ---------------------------------------------------------------------------
ACLI_PATH = shutil.which("acli")
SKIP_REASON = None
if not ACLI_PATH:
    SKIP_REASON = "acli not on PATH; rovodev backend unavailable in this environment"


# ---------------------------------------------------------------------------
# Banner detection — must match the production-failure classification
# ---------------------------------------------------------------------------
_BANNER_MARKERS = (
    "Working in",
    "Creating agent...",
    "Started ",
    "MCP servers",
    "Turn off prompt collection",
    "Jira projects:",
    "Using model:",
    "Session context:",
    "\u2517",   # box-drawing
    "\u2501",
)


def _is_banner_only(text: str) -> bool:
    """True iff every non-empty line of ``text`` is a known TUI banner marker."""
    if not text:
        return False
    return all(
        not line.strip() or any(m in line for m in _BANNER_MARKERS)
        for line in text.splitlines()
    )


# ---------------------------------------------------------------------------
# Minimal recording interactive — same contract the test on the
# AgentFoundation side uses; production uses ``WebSocketInteractive``
# which adds the WS plumbing on top of the same duck-typed surface.
# ---------------------------------------------------------------------------
class _RecordingInteractive:
    """Records stream chunks + widgets for post-run assertion."""

    def __init__(self) -> None:
        self.stream_chunks: list[str] = []
        self.emitted_widgets: list[dict[str, Any]] = []
        self.clean_corrections: list[str] = []

    async def aget_input(self) -> Any:  # pragma: no cover — defensive
        raise RuntimeError("aget_input must not be called for a 'hello' turn")

    async def asend_response(self, *args, **kwargs) -> None:  # pragma: no cover
        self.emitted_widgets.append({"args": args, "kwargs": kwargs})

    async def stream_token_batches(self, token_stream, *args, **kwargs) -> str:
        chunks: list[str] = []
        async for chunk in token_stream:
            if chunk is None:
                continue
            text = chunk if isinstance(chunk, str) else str(chunk)
            chunks.append(text)
            self.stream_chunks.append(text)
        return "".join(chunks)

    # The CI's clean-output substitution hook — production's
    # WebSocketInteractive uses this to send a ``stream_correction`` WS
    # event so the UI can overwrite the noisy in-progress display.
    # We record it so the test can assert it actually fired.
    async def on_clean_output_available(self, clean_output: str) -> None:
        self.clean_corrections.append(clean_output)


# ---------------------------------------------------------------------------
# _build_production_like_ci — uses the EXACT production factory
# ---------------------------------------------------------------------------
def _build_production_like_ci(
    target_path: str, cache_dir: str, templates_dir: Path
):
    """Build a CI by calling the production factory ``_rovodev_factory``.

    This is the LITERAL production code path: ``_rovodev_factory(ctx)`` →
    constructs ``RovoDevCliInferencer`` → ``_wrap_in_conversational(base, ctx)``
    → returns a fully-wired ``ConversationalInferencer`` that the running
    server uses for every chat turn.

    Returns the CI; the caller can reach the wrapped backend via
    ``ci.base_inferencer``.
    """
    from openteam.server.backends.factories import _rovodev_factory
    from openteam.server.backends.registry import BackendBuildContext

    ctx = BackendBuildContext(
        templates_dir=templates_dir,
        working_dir=target_path,
        cache_dir=cache_dir,
        session_store=None,
        model_name=None,
        session_id="test_real_session_with_rovodev_cli",
    )
    return _rovodev_factory(ctx)


# ---------------------------------------------------------------------------
# Resolve templates_dir
# ---------------------------------------------------------------------------
_TEMPLATES_DIR = _OPENSTARTUP_ROOT / "src" / "openteam" / "server" / "resources" / "prompt_templates"


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
@unittest.skipIf(SKIP_REASON is not None, SKIP_REASON or "")
class TestRealSessionWithRovoDevCli(unittest.IsolatedAsyncioTestCase):
    """End-to-end real-LLM test through the production factory chain."""

    async def test_hello_through_production_factory_produces_clean_answer(self) -> None:
        # ── Setup (production-like sandbox) ─────────────────────────────
        target_path = tempfile.mkdtemp(prefix="prodfac_hello_target_")
        cache_dir = tempfile.mkdtemp(prefix="prodfac_hello_cache_")

        # ── Production-faithful logging setup ──────────────────────────
        # Mirrors openteam/server/main.py:92-100 exactly:
        #   * basicConfig at DEBUG (test-only; production uses INFO unless
        #     --debug is passed, but for diagnosis we always want DEBUG)
        #   * sibling FileHandler at DEBUG capturing the same lines, so we
        #     have a post-mortem log even if pytest swallows stdout.
        # This is the same pair of handlers production uses; the only
        # difference is the destination directory.
        test_log_dir = Path(tempfile.mkdtemp(prefix="prodfac_hello_logs_"))
        test_log_file = test_log_dir / "server.log"
        # Force level even if another test already configured root logger
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)
        root_logger.setLevel(logging.DEBUG)
        _fmt = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        _stream_handler = logging.StreamHandler()
        _stream_handler.setLevel(logging.DEBUG)
        _stream_handler.setFormatter(_fmt)
        root_logger.addHandler(_stream_handler)
        _file_handler = logging.FileHandler(str(test_log_file), encoding="utf-8")
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(_fmt)
        root_logger.addHandler(_file_handler)
        # Explicitly enable DEBUG on the rovodev logger so the new
        # ``rendered prompt to rovodev`` DEBUG line is captured.
        logging.getLogger(
            "agent_foundation.common.inferencers.agentic_inferencers."
            "external.rovodev.rovodev_cli_inferencer"
        ).setLevel(logging.DEBUG)

        print(f"\n[test] log file (post-mortem): {test_log_file}")

        # Sanity: templates_dir exists (the real renderer will need it)
        if not _TEMPLATES_DIR.is_dir():
            self.skipTest(
                f"templates_dir not present at {_TEMPLATES_DIR}; check "
                f"OpenStartup checkout layout"
            )

        # Build CI via the EXACT production factory
        ci = _build_production_like_ci(target_path, cache_dir, _TEMPLATES_DIR)
        base = getattr(ci, "base_inferencer", None)
        self.assertIsNotNone(
            base,
            "ConversationalInferencer.base_inferencer is None — production "
            "factory chain returned an unwrapped object.",
        )

        interactive = _RecordingInteractive()

        # ── Act: send "hello" exactly as the production WS handler does
        result = await ci.run_agentic_loop(
            "hello",
            interactive=interactive,
            session_id="test_real_session_with_rovodev_cli",
            turn_number=0,
        )

        # ── Diagnostic dump (always print for human readability) ────────
        raw = getattr(result, "raw_response", "") or ""
        final = base.get_final_output() or ""
        last_clean = getattr(base, "_last_clean_output", "") or ""

        print()
        print("=" * 78)
        print("  TEST: hello through production _rovodev_factory chain")
        print("=" * 78)
        print(f"  CI type:                  {type(ci).__name__}")
        print(f"  base_inferencer type:     {type(base).__name__}")
        print(f"  AgenticResult type:       {type(result).__name__}")
        print(f"  raw_response (len={len(raw)}): {raw[:200]!r}")
        print(f"  base.get_final_output() (len={len(final)}): {final[:300]!r}")
        print(f"  base._last_clean_output (len={len(last_clean)}): {last_clean[:300]!r}")
        print(f"  recorded stream chunks:   {len(interactive.stream_chunks)}")
        print(f"  recorded widgets:         {len(interactive.emitted_widgets)}")
        print(f"  clean_corrections fired:  {len(interactive.clean_corrections)}")
        if interactive.clean_corrections:
            corr = interactive.clean_corrections[0]
            print(f"  first clean correction (len={len(corr)}): {corr[:200]!r}")
        print()

        # ── Assertions ──────────────────────────────────────────────────
        # 1. PRIMARY: rovodev wrote its --output-file successfully when
        #    invoked through the OpenStartup factory chain. The accessor
        #    is documented at rovodev_cli_inferencer.py:606-612 — its
        #    ONLY population path is reading the auto-injected output
        #    file before that file is cleaned up.
        self.assertTrue(
            final.strip(),
            "PRIMARY: ``base.get_final_output()`` is empty after "
            "_rovodev_factory(...) → run_agentic_loop('hello'). This "
            "reproduces the production failure mode "
            "(server_20260615_194631_8e0863a8, turn_002): rovodev did "
            "NOT write its --output-file when invoked through the "
            "OpenStartup factory.",
        )

        # 2. Clean output is not the rovodev TUI banner
        self.assertFalse(
            _is_banner_only(final),
            f"``base.get_final_output()`` is banner-only — file got banner "
            f"instead of LLM answer: {final[:300]!r}",
        )

        # 3. Internal consistency — both accessors should hold the same
        #    documented value (line 606-612).
        self.assertEqual(
            last_clean.strip(), final.strip(),
            f"``_last_clean_output`` ({len(last_clean)} chars) does not "
            f"match ``get_final_output()`` ({len(final)} chars).",
        )

        # 4. CI returned SOMETHING in raw_response
        self.assertTrue(
            raw.strip(),
            "CI.run_agentic_loop returned empty ``raw_response``.",
        )

        # 5. The CI fired on_clean_output_available — this is the UI
        #    display path (production WS interactive sends
        #    ``stream_correction`` from this callback). If this didn't
        #    fire, the UI would display the noisy banner instead of the
        #    clean answer.
        self.assertGreaterEqual(
            len(interactive.clean_corrections), 1,
            "``on_clean_output_available`` was NEVER called — the UI "
            "display path is broken (no ``stream_correction`` event would "
            "be sent in production). Verified at "
            "conversational_inferencer.py:416-419.",
        )

        # 6. The clean correction the CI emitted matches the final output
        if interactive.clean_corrections:
            self.assertEqual(
                interactive.clean_corrections[-1].strip(),
                final.strip(),
                "``on_clean_output_available`` was called with text that "
                "does not match ``get_final_output()``. Production UI "
                "would display a different string than the saved final "
                "output.",
            )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
