"""Mock task executor — drives a real BTA with mock inferencers.

Exercises the full graph event pipeline (topology, status, streaming)
without LLM calls. Used by the ``/mock_task`` developer slash command.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)
_PROFILES_DIR = Path(__file__).parent / "profiles"


def _apply_speed(cfg: dict, speed: float) -> dict:
    """Recursively multiply all ``delay_s`` / ``duration_s`` values by speed."""
    if isinstance(cfg, dict):
        out = {}
        for k, v in cfg.items():
            if k in ("delay_s", "duration_s") and isinstance(v, (int, float)):
                out[k] = v * speed
            else:
                out[k] = _apply_speed(v, speed)
        return out
    if isinstance(cfg, list):
        return [_apply_speed(item, speed) for item in cfg]
    return cfg


async def execute(arguments: dict, session_context: dict) -> Any:
    """Entry point called by ToolDispatcher for /mock_task."""
    profile = arguments.get("profile", arguments.get("--profile", "default"))
    speed = float(arguments.get("speed", arguments.get("--speed", 1.0)))
    seed = int(arguments.get("seed", arguments.get("--seed", 0)))

    cfg_path = _PROFILES_DIR / f"{profile}.yaml"
    if not cfg_path.exists():
        available = [p.stem for p in _PROFILES_DIR.glob("*.yaml")]
        return {"success": False, "output": f"Unknown profile '{profile}'. Available: {available}"}

    _logger.info("[mock_task] profile=%s speed=%s seed=%s", profile, speed, seed)

    import agent_foundation.common.configs.registered_targets  # noqa: register aliases
    from rich_python_utils.config_utils import load_config, instantiate

    cfg = load_config(str(cfg_path))
    if speed != 1.0:
        cfg = _apply_speed(cfg, speed)
    if seed:
        random.seed(seed)

    bta = instantiate(cfg)

    interactive = session_context.get("interactive")
    task_id = session_context.get("task_id", "")
    if interactive is not None and task_id:
        from agent_foundation.ui.graph_interactive_adapter import WebSocketGraphReporter
        bta.graph_reporter = WebSocketGraphReporter(interactive, task_id)
        _logger.info("[mock_task] WebSocketGraphReporter attached (task_id=%s)", task_id)

    result = await bta.ainfer("__mock_input__")
    result_text = str(result) if result else "[mock_task completed]"
    return {"success": True, "output": result_text[:2000]}
